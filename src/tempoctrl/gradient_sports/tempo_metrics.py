from __future__ import annotations

from collections.abc import Sequence

import polars as pl

FPS = 29.97  # FIXME: Pull from game metadata.


def _resolve_group_columns(
    df: pl.LazyFrame,
    possession_groups: str | Sequence[str],
) -> tuple[str, ...]:
    """Normalize and validate ball-metric partition columns."""
    possession_columns = (
        (possession_groups,)
        if isinstance(possession_groups, str)
        else tuple(possession_groups)
    )
    if not possession_columns:
        raise ValueError("At least one possession group is required.")
    if not all(
        isinstance(column, str) for column in possession_columns
    ):
        raise TypeError("Possession group names must be strings.")
    if any(not column for column in possession_columns):
        raise ValueError("Possession group names cannot be empty.")
    if len(set(possession_columns)) != len(possession_columns):
        raise ValueError("Possession group names must be unique.")

    group_columns = ("game_id", *possession_columns)
    schema = df.collect_schema()
    missing_columns = [
        column for column in group_columns if column not in schema
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Missing ball metric group columns: {missing}.")

    return group_columns


def add_ball_displacement(
    df: pl.LazyFrame,
    possession_groups: str | Sequence[str],
) -> pl.LazyFrame:
    """Add frame-ordered 2D displacement within each possession."""
    group_columns = _resolve_group_columns(df, possession_groups)
    ball_struct = "balls_smooth"

    x = pl.col(ball_struct).struct.field("x")
    y = pl.col(ball_struct).struct.field("y")

    previous_x = x.shift().over(
        group_columns,
        order_by="framenum",
    )
    previous_y = y.shift().over(
        group_columns,
        order_by="framenum",
    )
    previous_frame = pl.col("framenum").shift().over(
        group_columns,
        order_by="framenum",
    )
    delta_x = x - previous_x
    delta_y = y - previous_y
    delta_frame = pl.col("framenum") - previous_frame

    return df.with_columns(
        delta_x.alias("delta_x"),
        delta_y.alias("delta_y"),
        delta_frame.alias("delta_frame"),
        (
            delta_x.pow(2) + delta_y.pow(2)
        ).sqrt().alias("ball_displacement"),
    ).pipe(add_ball_speed, FPS)


def add_ball_speed(
    df: pl.LazyFrame,
    frame_rate: float,
) -> pl.LazyFrame:
    """Add frame-level ball speed in meters per second."""
    if frame_rate <= 0:
        raise ValueError("frame_rate must be greater than 0.")

    ball_speed_expr = (
        pl.col("ball_displacement")
        * frame_rate
        / pl.col("delta_frame")
    )

    return df.with_columns(
        ball_speed_expr.alias("ball_speed")
    )


def add_tempo(df: pl.LazyFrame):
    pass
