import logging

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

FRAME_KEYS = (
    "game_id",
    "period",
    "framenum",
)

REQUIRED_COLUMNS = (
    *POSSESSION_KEYS,
    "period",
    "framenum",
    "event_number",
    "possession_event_id",
    "possession_event_type",
    "successful_pass_or_cross",
)

SUCCESSFUL_DELIVERY_TYPES = ("PA", "CR")


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


def find_terminal_successful_deliveries(
    df_in: pl.LazyFrame,
) -> pl.LazyFrame:
    """Find player possessions ending in a successful pass or cross.

    The terminal event is selected by event number, possession-event ID,
    and frame number. The returned table contains one propagation seed
    for each eligible terminal tracking frame.
    """
    event_order = [
        "event_number",
        "possession_event_id",
        "framenum",
    ]
    terminal_events = (
        df_in.filter(
            pl.all_horizontal(
                [pl.col(column).is_not_null() for column in POSSESSION_KEYS]
            )
        )
        .group_by(POSSESSION_KEYS)
        .agg(
            pl.col("period")
            .sort_by(event_order)
            .last()
            .alias("period"),
            pl.col("framenum")
            .sort_by(event_order)
            .last()
            .alias("framenum"),
            pl.col("possession_event_type")
            .sort_by(event_order)
            .last()
            .alias("__terminal_event_type"),
            pl.col("successful_pass_or_cross")
            .sort_by(event_order)
            .last()
            .alias("__terminal_delivery_successful"),
        )
        .filter(
            pl.col("__terminal_event_type").is_in(
                SUCCESSFUL_DELIVERY_TYPES
            )
            & pl.col("__terminal_delivery_successful").fill_null(False)
        )
        .select(
            *FRAME_KEYS,
            pl.col("match_team_possession_id").alias("__seed_team_id"),
            pl.col("match_team_player_possession_id").alias(
                "__seed_player_id"
            ),
        )
    )

    return terminal_events.group_by(FRAME_KEYS).agg(
        pl.col("__seed_team_id").first(),
        pl.col("__seed_player_id").first(),
    )


def build_frame_possession_state(
    df_in: pl.LazyFrame,
    delivery_seeds: pl.LazyFrame,
) -> pl.LazyFrame:
    """Create one ordered possession-state record per tracking frame.

    Duplicate event annotations at a frame are collapsed for the state
    calculation. Original rows are restored after propagation.
    """
    return (
        df_in.group_by(FRAME_KEYS)
        .agg(
            pl.col("match_team_possession_id")
            .drop_nulls()
            .first()
            .alias("__original_team_id"),
            pl.col("match_team_player_possession_id")
            .drop_nulls()
            .first()
            .alias("__original_player_id"),
        )
        .join(
            delivery_seeds,
            on=FRAME_KEYS,
            how="left",
            coalesce=True,
        )
        .sort(FRAME_KEYS)
    )


def propagate_successful_deliveries(
    frame_state: pl.LazyFrame,
) -> pl.LazyFrame:
    """Propagate eligible terminal IDs until the next player possession.

    A non-null original player-possession ID begins a new segment. Only
    a segment containing a terminal successful pass or cross receives
    propagated identifiers.
    """
    segment_keys = ["game_id", "period", "__player_segment"]
    segmented_frames = frame_state.with_columns(
        pl.col("__original_player_id")
        .is_not_null()
        .cast(pl.UInt32)
        .cum_sum()
        .over(["game_id", "period"])
        .alias("__player_segment")
    )
    propagated_frames = segmented_frames.with_columns(
        pl.col("__seed_team_id")
        .forward_fill()
        .over(segment_keys)
        .alias("__propagated_team_id"),
        pl.col("__seed_player_id")
        .forward_fill()
        .over(segment_keys)
        .alias("__propagated_player_id"),
    )
    should_propagate = (
        pl.col("__original_player_id").is_null()
        & pl.col("__propagated_player_id").is_not_null()
    )

    return propagated_frames.select(
        *FRAME_KEYS,
        pl.coalesce(
            ["__original_team_id", "__propagated_team_id"]
        ).alias("effective_match_team_possession_id"),
        pl.coalesce(
            ["__original_player_id", "__propagated_player_id"]
        ).alias("effective_match_team_player_possession_id"),
        should_propagate.alias("possession_id_propagated"),
    )


def transform_possessions(df_in: pl.LazyFrame) -> pl.LazyFrame:
    """Add auditable frame-level possession identifiers.

    Validate the schema, identify terminal successful passes and crosses,
    calculate frame-level propagation, and restore the original rows.
    """
    validated = validate_possession_columns(df_in)
    delivery_seeds = find_terminal_successful_deliveries(validated)
    frame_state = build_frame_possession_state(validated, delivery_seeds)
    propagated_frames = propagate_successful_deliveries(frame_state)

    return (
        validated.with_row_index("__source_row")
        .join(
            propagated_frames,
            on=FRAME_KEYS,
            how="left",
            coalesce=True,
        )
        .sort("__source_row")
        .drop("__source_row")
    )
