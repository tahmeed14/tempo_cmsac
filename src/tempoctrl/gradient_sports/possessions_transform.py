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

FRAME_PARTITION_KEYS = (
    "game_id",
    "period",
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
    and frame number. Each result includes the passer metadata needed for
    propagation and the synthetic delivery-end row.
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
            pl.col("player_id")
            .sort_by(event_order)
            .last()
            .alias("__passer_player_id"),
            pl.col("playername")
            .sort_by(event_order)
            .last()
            .alias("__passer_playername"),
            pl.col("team_id")
            .sort_by(event_order)
            .last()
            .alias("__passer_team_id"),
            pl.col("teamname")
            .sort_by(event_order)
            .last()
            .alias("__passer_teamname"),
            pl.col("hometeam")
            .sort_by(event_order)
            .last()
            .alias("__passer_hometeam"),
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
            "__passer_player_id",
            "__passer_playername",
            "__passer_team_id",
            "__passer_teamname",
            "__passer_hometeam",
        )
    )

    return terminal_events


def build_frame_possession_state(df_in: pl.LazyFrame) -> pl.LazyFrame:
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
            pl.col("balls_smooth")
            .drop_nulls()
            .first()
            .alias("__frame_ball"),
        )
        .sort(FRAME_KEYS)
    )


def impute_internal_possession_gaps(
    frame_state: pl.LazyFrame,
) -> pl.LazyFrame:
    """Fill null IDs enclosed by the same possession identifier.

    Team and player identifiers are evaluated independently. A null frame
    is filled only when its nearest preceding and following identifiers
    within the game period are equal and non-null.
    """
    surrounding_ids = frame_state.with_columns(
        pl.col("__original_team_id")
        .forward_fill()
        .over(FRAME_PARTITION_KEYS)
        .alias("__previous_team_id"),
        pl.col("__original_team_id")
        .backward_fill()
        .over(FRAME_PARTITION_KEYS)
        .alias("__next_team_id"),
        pl.col("__original_player_id")
        .forward_fill()
        .over(FRAME_PARTITION_KEYS)
        .alias("__previous_player_id"),
        pl.col("__original_player_id")
        .backward_fill()
        .over(FRAME_PARTITION_KEYS)
        .alias("__next_player_id"),
    )
    internal_team_gap = (
        pl.col("__original_team_id").is_null()
        & pl.col("__previous_team_id").is_not_null()
        & (
            pl.col("__previous_team_id")
            == pl.col("__next_team_id")
        )
    )
    internal_player_gap = (
        pl.col("__original_player_id").is_null()
        & pl.col("__previous_player_id").is_not_null()
        & (
            pl.col("__previous_player_id")
            == pl.col("__next_player_id")
        )
    )

    return surrounding_ids.with_columns(
        pl.when(internal_team_gap)
        .then(pl.col("__previous_team_id"))
        .otherwise(pl.col("__original_team_id"))
        .alias("__internal_team_id"),
        pl.when(internal_player_gap)
        .then(pl.col("__previous_player_id"))
        .otherwise(pl.col("__original_player_id"))
        .alias("__internal_player_id"),
        internal_team_gap.alias("__internal_team_gap"),
        internal_player_gap.alias("__internal_player_gap"),
    )


def propagate_successful_deliveries(
    frame_state: pl.LazyFrame,
    delivery_seeds: pl.LazyFrame,
) -> pl.LazyFrame:
    """Extend successful deliveries until the next player possession.

    Internal gaps are already filled. A terminal successful pass or cross
    seeds the remaining null frames before the next observed player
    possession in the same game period.
    """
    frame_seeds = delivery_seeds.group_by(FRAME_KEYS).agg(
        pl.col("__seed_team_id").first(),
        pl.col("__seed_player_id").first(),
    )
    seeded_frames = frame_state.join(
        frame_seeds,
        on=FRAME_KEYS,
        how="left",
        coalesce=True,
    )
    observed_frames = seeded_frames.with_columns(
        pl.col("__internal_player_id")
        .forward_fill()
        .shift(1)
        .over(FRAME_PARTITION_KEYS)
        .alias("__previous_observed_player_id")
    )
    starts_player_possession = (
        pl.col("__internal_player_id").is_not_null()
        & (
            pl.col("__previous_observed_player_id").is_null()
            | (
                pl.col("__internal_player_id")
                != pl.col("__previous_observed_player_id")
            )
        )
    )
    segmented_frames = observed_frames.with_columns(
        starts_player_possession
        .cast(pl.UInt32)
        .cum_sum()
        .over(FRAME_PARTITION_KEYS)
        .alias("__player_segment")
    )
    segment_keys = [*FRAME_PARTITION_KEYS, "__player_segment"]
    propagated_frames = segmented_frames.with_columns(
        pl.col("__seed_team_id")
        .forward_fill()
        .over(segment_keys)
        .alias("__delivery_team_id"),
        pl.col("__seed_player_id")
        .forward_fill()
        .over(segment_keys)
        .alias("__delivery_player_id"),
    )
    delivery_extension = (
        pl.col("__internal_player_id").is_null()
        & pl.col("__delivery_player_id").is_not_null()
    )

    return propagated_frames.with_columns(
        pl.coalesce(
            ["__internal_team_id", "__delivery_team_id"]
        ).alias("effective_match_team_possession_id"),
        pl.coalesce(
            ["__internal_player_id", "__delivery_player_id"]
        ).alias("effective_match_team_player_possession_id"),
        delivery_extension.alias("__delivery_extension"),
    )


def select_frame_possession_output(
    frame_state: pl.LazyFrame,
) -> pl.LazyFrame:
    """Select effective identifiers and auditable imputation metadata."""
    imputation_reason = (
        pl.when(pl.col("__delivery_extension"))
        .then(pl.lit("successful_delivery_extension"))
        .when(
            pl.col("__internal_team_gap")
            & pl.col("__internal_player_gap")
        )
        .then(pl.lit("internal_team_and_player_gap"))
        .when(pl.col("__internal_player_gap"))
        .then(pl.lit("internal_player_gap"))
        .when(pl.col("__internal_team_gap"))
        .then(pl.lit("internal_team_gap"))
        .otherwise(None)
    )

    return frame_state.select(
        *FRAME_KEYS,
        "effective_match_team_possession_id",
        "effective_match_team_player_possession_id",
        (
            pl.col("__internal_team_gap")
            | pl.col("__delivery_extension")
        ).alias("team_possession_id_imputed"),
        (
            pl.col("__internal_player_gap")
            | pl.col("__delivery_extension")
        ).alias("player_possession_id_imputed"),
        imputation_reason.alias("possession_id_imputation_reason"),
    )


def build_synthetic_delivery_rows(
    df_in: pl.LazyFrame,
    frame_state: pl.LazyFrame,
    delivery_seeds: pl.LazyFrame,
) -> pl.LazyFrame:
    """Create one passer-attributed row at the receiver's first frame.

    The synthetic row copies only the receiver frame's ball coordinates.
    Event-specific fields are null, while passer identity and effective
    possession IDs come from the terminal successful delivery.
    """
    next_player_frames = (
        frame_state.with_columns(
            pl.col("__internal_player_id")
            .forward_fill()
            .shift(1)
            .over(FRAME_PARTITION_KEYS)
            .alias("__previous_observed_player_id")
        )
        .filter(
            pl.col("__internal_player_id").is_not_null()
            & pl.col("__previous_observed_player_id").is_not_null()
            & (
                pl.col("__internal_player_id")
                != pl.col("__previous_observed_player_id")
            )
        )
        .select(
            *FRAME_PARTITION_KEYS,
            pl.col("framenum").alias("__next_player_frame"),
            pl.col("__internal_player_id").alias("__next_player_id"),
            pl.col("__frame_ball").alias("__receiver_frame_ball"),
        )
        .sort([*FRAME_PARTITION_KEYS, "__next_player_frame"])
    )
    delivery_boundaries = (
        delivery_seeds.rename({"framenum": "__delivery_frame"})
        .sort([*FRAME_PARTITION_KEYS, "__delivery_frame"])
        .join_asof(
            next_player_frames,
            left_on="__delivery_frame",
            right_on="__next_player_frame",
            by=FRAME_PARTITION_KEYS,
            strategy="forward",
            allow_exact_matches=False,
            check_sortedness=False,
        )
        .filter(
            pl.col("__next_player_frame").is_not_null()
            & (
                pl.col("__next_player_id")
                != pl.col("__seed_player_id")
            )
        )
    )

    source_schema = df_in.collect_schema()
    synthetic_values: dict[str, pl.Expr] = {
        "game_id": pl.col("game_id"),
        "period": pl.col("period"),
        "framenum": pl.col("__next_player_frame"),
        "balls_smooth": pl.col("__receiver_frame_ball"),
        "player_id": pl.col("__passer_player_id"),
        "playername": pl.col("__passer_playername"),
        "team_id": pl.col("__passer_team_id"),
        "teamname": pl.col("__passer_teamname"),
        "hometeam": pl.col("__passer_hometeam"),
    }
    source_columns = [
        synthetic_values.get(column, pl.lit(None, dtype=dtype))
        .cast(dtype)
        .alias(column)
        for column, dtype in source_schema.items()
    ]

    return delivery_boundaries.select(
        pl.lit(None, dtype=pl.UInt32).alias("__source_row"),
        *source_columns,
        pl.col("__seed_team_id").alias(
            "effective_match_team_possession_id"
        ),
        pl.col("__seed_player_id").alias(
            "effective_match_team_player_possession_id"
        ),
        pl.lit(True).alias("team_possession_id_imputed"),
        pl.lit(True).alias("player_possession_id_imputed"),
        pl.lit("successful_delivery_shared_frame").alias(
            "possession_id_imputation_reason"
        ),
        pl.lit(True).alias("is_synthetic_deliver_end"),
    )


def transform_possessions(df_in: pl.LazyFrame) -> pl.LazyFrame:
    """Add auditable frame-level possession identifiers.

    Fill internal ID gaps, extend terminal successful deliveries, restore
    every source row, and add a shared-frame synthetic delivery endpoint.
    """
    validated = validate_possession_columns(df_in)
    delivery_seeds = find_terminal_successful_deliveries(validated)
    frame_state = build_frame_possession_state(validated)
    internal_state = impute_internal_possession_gaps(frame_state)
    propagated_state = propagate_successful_deliveries(
        internal_state,
        delivery_seeds,
    )
    frame_output = select_frame_possession_output(propagated_state)
    team_value_added = (
        pl.col("match_team_possession_id").is_null()
        & pl.col("effective_match_team_possession_id").is_not_null()
    )
    player_value_added = (
        pl.col("match_team_player_possession_id").is_null()
        & pl.col(
            "effective_match_team_player_possession_id"
        ).is_not_null()
    )
    original_rows = (
        validated.with_row_index("__source_row")
        .join(
            frame_output,
            on=FRAME_KEYS,
            how="left",
            coalesce=True,
        )
        .with_columns(
            team_value_added.alias("team_possession_id_imputed"),
            player_value_added.alias("player_possession_id_imputed"),
            pl.when(
                pl.col("possession_id_imputation_reason").is_null()
                & (team_value_added | player_value_added)
            )
            .then(pl.lit("same_frame_annotation"))
            .otherwise(pl.col("possession_id_imputation_reason"))
            .alias("possession_id_imputation_reason"),
            pl.lit(False).alias("is_synthetic_deliver_end")
        )
    )
    synthetic_rows = build_synthetic_delivery_rows(
        validated,
        internal_state,
        delivery_seeds,
    )

    return (
        pl.concat([original_rows, synthetic_rows], how="vertical")
        .sort(
            [
                *FRAME_KEYS,
                "is_synthetic_deliver_end",
                "__source_row",
            ],
            descending=[False, False, False, True, False],
            nulls_last=True,
        )
        .drop("__source_row")
    )
