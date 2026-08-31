"""Possession-level tempo metrics derived from ball movement."""

from __future__ import annotations

import math
from typing import Literal

import polars as pl

PossessionLevel = Literal["team", "player"]

_GAME_COLUMN = "game_id"
_FRAME_COLUMN = "framenum"
_DISPLACEMENT_COLUMN = "ball_displacement"
_DELTA_FRAME_COLUMN = "delta_frame"
_POSSESSION_COLUMNS: dict[PossessionLevel, str] = {
    "team": "dev_match_team_possession_id",
    "player": "dev_match_team_player_possession_id",
}


def _validate_tempo_inputs(
    df: pl.LazyFrame,
    level: PossessionLevel,
    frame_rate: float,
) -> str:
    """Validate tempo inputs and return the possession ID column."""
    if level not in _POSSESSION_COLUMNS:
        raise ValueError("level must be either 'team' or 'player'.")
    if not math.isfinite(frame_rate) or frame_rate <= 0:
        raise ValueError(
            "frame_rate must be finite and greater than 0."
        )

    possession_column = _POSSESSION_COLUMNS[level]
    required_columns = (
        _GAME_COLUMN,
        possession_column,
        _FRAME_COLUMN,
        _DISPLACEMENT_COLUMN,
        _DELTA_FRAME_COLUMN,
    )
    schema = df.collect_schema()
    missing_columns = [
        column for column in required_columns if column not in schema
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Missing possession tempo columns: {missing}.")

    numeric_columns = (
        _FRAME_COLUMN,
        _DISPLACEMENT_COLUMN,
        _DELTA_FRAME_COLUMN,
    )
    nonnumeric_columns = [
        column
        for column in numeric_columns
        if not schema[column].is_numeric()
    ]
    if nonnumeric_columns:
        invalid = ", ".join(nonnumeric_columns)
        raise TypeError(
            f"Possession tempo columns must be numeric: {invalid}."
        )

    return possession_column


def aggregate_possession_tempo(
    df: pl.LazyFrame,
    level: PossessionLevel,
    *,
    frame_rate: float,
) -> pl.LazyFrame:
    """Summarize observed ball movement for each possession.

    A valid movement segment has a non-null displacement and a positive
    frame interval. Tempo is total valid displacement divided by the
    observed time represented by those segments. This avoids counting
    leading rows, duplicate frames, or missing-coordinate intervals as
    though they were measured movement.

    Possessions are isolated by both game and possession ID. Rows with
    a null key are excluded instead of being combined into an artificial
    null possession. Output is sorted by those keys for deterministic
    downstream files.

    Args:
        df: Lazy frame-level rows with ball movement metrics.
        level: Team or player possession granularity.
        frame_rate: Finite, positive tracking samples per second.

    Returns:
        One row per possession with frame bounds, valid segment count,
        total displacement, elapsed frames, and ball tempo. Metrics are
        null when a possession has no valid movement segment.
    """
    possession_column = _validate_tempo_inputs(
        df,
        level,
        frame_rate,
    )
    group_columns = (_GAME_COLUMN, possession_column)
    valid_key = pl.all_horizontal(
        *(pl.col(column).is_not_null() for column in group_columns)
    )
    valid_segment = (
        pl.col(_DISPLACEMENT_COLUMN).is_not_null()
        & (pl.col(_DELTA_FRAME_COLUMN) > 0).fill_null(False)
    )
    has_valid_segment = pl.col("valid_segment_count") > 0
    tempo_column = f"ball_speed_tempo_{level}"

    aggregated = (
        df.filter(valid_key)
        .group_by(group_columns)
        .agg(
            pl.col(_FRAME_COLUMN).min().alias("start_frame"),
            pl.col(_FRAME_COLUMN).max().alias("end_frame"),
            valid_segment.sum()
            .cast(pl.UInt32)
            .alias("valid_segment_count"),
            pl.when(valid_segment)
            .then(pl.col(_DISPLACEMENT_COLUMN))
            .sum()
            .cast(pl.Float64)
            .alias("__total_ball_displacement"),
            pl.when(valid_segment)
            .then(pl.col(_DELTA_FRAME_COLUMN))
            .sum()
            .cast(pl.Float64)
            .alias("__elapsed_frames"),
        )
        .with_columns(
            pl.when(has_valid_segment)
            .then(pl.col("__total_ball_displacement"))
            .alias("total_ball_displacement"),
            pl.when(has_valid_segment)
            .then(pl.col("__elapsed_frames"))
            .alias("elapsed_frames"),
        )
        .with_columns(
            (
                pl.col("total_ball_displacement")
                * frame_rate
                / pl.col("elapsed_frames")
            ).alias(tempo_column)
        )
        .drop("__total_ball_displacement", "__elapsed_frames")
        .sort(group_columns)
    )

    return aggregated
