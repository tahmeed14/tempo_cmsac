import logging
from collections.abc import Sequence

import polars as pl

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

POSSESSION_KEYS = (
    "game_id",
    "match_team_possession_id",
    "match_team_player_possession_id",
)

REQUIRED_COLUMNS = (
    *POSSESSION_KEYS,
    "period",
    "framenum",
    "event_number",
    "possession_event_id",
    "possession_event_type",
    "successful_pass_or_cross",
    "balls_smooth",
    "player_id",
    "playername",
    "team_id",
    "teamname",
    "hometeam",
)

SORT_COLUMNS = (
    "game_id",
    "framenum",
)


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


def fill_bounded_possessions_id(df: pl.LazyFrame,
                                poss_col: str | Sequence[str]) -> pl.LazyFrame:
    """Fill bounded null IDs in one or more possession columns.

    Leading nulls, trailing nulls, and gaps bounded by different IDs are
    left unchanged. The source column is preserved and the filled values
    are written to columns prefixed with ``dev_``. Multiple columns are
    accepted so callers can sort the input only once.
    """
    possession_columns = (
        (poss_col,) if isinstance(poss_col, str) else poss_col
    )
    return df.sort(SORT_COLUMNS).with_columns(
        *(
            _bounded_possession_id(column)
            for column in possession_columns
        )
    )


def transform_possessions(df_in: pl.LazyFrame) -> pl.LazyFrame:
    """Validate possession data and fill bounded possession ID gaps."""
    return (df_in
            .pipe(validate_possession_columns)
            .pipe(fill_bounded_possessions_id,
                  ("match_team_possession_id", 
                   "match_team_player_possession_id"
                   )
            )
    )
