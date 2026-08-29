from collections.abc import Sequence

import polars as pl

POSSESSION_COLUMNS = (
    "match_team_possession_id",
    "match_team_player_possession_id",
)

REQUIRED_COLUMNS = (
    "game_id",
    "framenum",
    *POSSESSION_COLUMNS,
    "successful_pass_or_cross",
)

SORT_COLUMNS = (
    "game_id",
    "framenum",
)

_CURRENT_POSSESSION_COLUMN = "__current_player_possession_id"
_SUCCESSFUL_DELIVERY_COLUMN = "__successful_delivery_possession_id"


def validate_possession_columns(df_in: pl.LazyFrame) -> pl.LazyFrame:
    """Require the columns used by possession propagation.

    Schema validation reads only Parquet metadata and does not collect
    the tracking rows.
    """
    schema = df_in.collect_schema()
    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in schema
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Missing possession columns: {missing}")

    return df_in


def _bounded_possession_id(poss_col: str) -> pl.Expr:
    """Build an expression that fills bounded IDs within each game."""
    possession_id = pl.col(poss_col)
    previous_id = possession_id.forward_fill().over("game_id")
    next_id = possession_id.backward_fill().over("game_id")
    return (
        pl.when(previous_id == next_id)
        .then(previous_id)
        .otherwise(possession_id)
        .alias(f"dev_{poss_col}")
    )


def fill_bounded_possessions_id(
    df: pl.LazyFrame,
    poss_col: str | Sequence[str],
) -> pl.LazyFrame:
    """Fill bounded null IDs in one or more possession columns.

    Leading nulls, trailing nulls, and gaps bounded by different IDs are
    left unchanged. The source column is preserved and the filled values
    are written to columns prefixed with ``dev_``. Multiple columns are
    accepted so callers can sort the input only once. Duplicate rows for
    a frame share their single non-null possession annotation.
    """
    possession_columns = (
        (poss_col,) if isinstance(poss_col, str) else poss_col
    )
    frame_columns = {
        column: f"__frame_{column}"
        for column in possession_columns
    }
    return (
        df.sort(SORT_COLUMNS)
        .with_columns(
            *(
                pl.col(column)
                .drop_nulls()
                .first()
                .over(SORT_COLUMNS)
                .alias(frame_column)
                for column, frame_column in frame_columns.items()
            )
        )
        .with_columns(
            *(
                _bounded_possession_id(frame_column).alias(
                    f"dev_{column}"
                )
                for column, frame_column in frame_columns.items()
            )
        )
        .drop(*frame_columns.values())
    )


def _successful_delivery_id(poss_col: str) -> pl.Expr:
    """Track the latest successful delivery possession in each game."""
    possession_id = pl.col(poss_col)
    return (
        pl.when(
            possession_id.is_not_null()
            & pl.col("successful_pass_or_cross").fill_null(False)
        )
        .then(possession_id)
        .forward_fill()
        .over("game_id")
        .alias(_SUCCESSFUL_DELIVERY_COLUMN)
    )


def propagate_successful_delivery_possession(
    df_in: pl.LazyFrame,
) -> pl.LazyFrame:
    """Propagate a successful delivery until another possession starts.

    Existing bounded-gap fills are retained. An unbounded null receives
    the successful player's possession ID only while that ID remains the
    latest observed player possession in the game.
    """
    possession_column = "match_team_player_possession_id"
    development_column = f"dev_{possession_column}"
    possession_id = pl.col(possession_column)
    delivery_is_active = (
        pl.col(_CURRENT_POSSESSION_COLUMN)
        == pl.col(_SUCCESSFUL_DELIVERY_COLUMN)
    )
    propagated_id = pl.when(delivery_is_active).then(
        pl.col(_SUCCESSFUL_DELIVERY_COLUMN)
    )

    return (
        df_in.with_columns(
            possession_id.forward_fill()
            .over("game_id")
            .alias(_CURRENT_POSSESSION_COLUMN),
            _successful_delivery_id(possession_column),
        )
        .with_columns(
            pl.coalesce(
                pl.col(development_column),
                propagated_id,
            ).alias(development_column)
        )
        .drop(
            _CURRENT_POSSESSION_COLUMN,
            _SUCCESSFUL_DELIVERY_COLUMN,
        )
    )


def transform_possessions(df_in: pl.LazyFrame) -> pl.LazyFrame:
    """Fill bounded gaps and extend successful player deliveries."""
    return (
        df_in.pipe(validate_possession_columns)
        .pipe(fill_bounded_possessions_id, POSSESSION_COLUMNS)
        .pipe(propagate_successful_delivery_possession)
    )
