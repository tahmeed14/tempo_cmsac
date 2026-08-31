from __future__ import annotations

from collections.abc import Sequence

import polars as pl

FPS = 29.97  # FIXME: Pull from game metadata.

SYNTHETIC_PASS_END_COLUMN = "is_synthetic_pass_end"

_IS_METRIC_FRAME_COLUMN = "__is_ball_metric_frame"
_METRIC_INPUT_ORDER_COLUMN = "__ball_metric_input_order"


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


def _add_metric_frame_marker(
    df: pl.LazyFrame,
    group_columns: tuple[str, ...],
) -> pl.LazyFrame:
    """Mark one metric row per frame, preferring a synthetic pass row."""
    schema = df.collect_schema()
    frame_columns = (*group_columns, "framenum")
    input_order = pl.col(_METRIC_INPUT_ORDER_COLUMN)
    is_synthetic = (
        pl.col(SYNTHETIC_PASS_END_COLUMN).fill_null(False)
        if SYNTHETIC_PASS_END_COLUMN in schema
        else pl.lit(False)
    )

    with_input_order = df.with_columns(
        pl.int_range(pl.len()).alias(_METRIC_INPUT_ORDER_COLUMN)
    )
    first_input_order = input_order.min().over(frame_columns)
    first_synthetic_order = (
        pl.when(is_synthetic)
        .then(input_order)
        .otherwise(None)
        .min()
        .over(frame_columns)
    )

    return with_input_order.with_columns(
        (
            input_order
            == pl.coalesce(first_synthetic_order, first_input_order)
        ).alias(_IS_METRIC_FRAME_COLUMN)
    )


def add_ball_displacement(
    df: pl.LazyFrame,
    possession_groups: str | Sequence[str],
) -> pl.LazyFrame:
    """Add frame-ordered 2D displacement within each possession."""
    group_columns = _resolve_group_columns(df, possession_groups)
    ball_struct = "balls_smooth"
    order_columns = ("framenum", _METRIC_INPUT_ORDER_COLUMN)

    x = pl.col(ball_struct).struct.field("x")
    y = pl.col(ball_struct).struct.field("y")
    is_metric_frame = pl.col(_IS_METRIC_FRAME_COLUMN)
    metric_x = pl.when(is_metric_frame).then(x)
    metric_y = pl.when(is_metric_frame).then(y)
    metric_frame = pl.when(is_metric_frame).then(pl.col("framenum"))

    previous_x = metric_x.forward_fill().shift().over(
        group_columns,
        order_by=order_columns,
    )
    previous_y = metric_y.forward_fill().shift().over(
        group_columns,
        order_by=order_columns,
    )
    previous_frame = metric_frame.forward_fill().shift().over(
        group_columns,
        order_by=order_columns,
    )
    delta_x = pl.when(is_metric_frame).then(x - previous_x)
    delta_y = pl.when(is_metric_frame).then(y - previous_y)
    delta_frame = pl.when(is_metric_frame).then(
        pl.col("framenum") - previous_frame
    )

    return (
        df.pipe(_add_metric_frame_marker, group_columns)
        .with_columns(
            delta_x.alias("delta_x"),
            delta_y.alias("delta_y"),
            delta_frame.alias("delta_frame"),
            (
                delta_x.pow(2) + delta_y.pow(2)
            ).sqrt().alias("ball_displacement"),
        )
        .drop(
            _IS_METRIC_FRAME_COLUMN,
            _METRIC_INPUT_ORDER_COLUMN,
        )
        .pipe(add_ball_speed, FPS)
    )


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
