from __future__ import annotations

from collections.abc import Sequence

import polars as pl

FPS = 29.97  # FIXME: Pull from game metadata.

SYNTHETIC_PASS_END_COLUMN = "is_synthetic_pass_end"

_IS_METRIC_FRAME_COLUMN = "__is_ball_metric_frame"
_METRIC_INPUT_ORDER_COLUMN = "__ball_metric_input_order"

_BALL_COLUMN = "balls_smooth"
_FRAME_COLUMN = "framenum"


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


def _validate_metric_schema(df: pl.LazyFrame) -> pl.LazyFrame:
    """Validate columns and dtypes required by ball movement metrics."""
    schema = df.collect_schema()
    required_columns = (_FRAME_COLUMN, _BALL_COLUMN)
    missing_columns = [
        column for column in required_columns if column not in schema
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Missing ball metric columns: {missing}.")

    if not schema[_FRAME_COLUMN].is_numeric():
        raise TypeError(f"{_FRAME_COLUMN} must be numeric.")

    ball_dtype = schema[_BALL_COLUMN]
    if not isinstance(ball_dtype, pl.Struct):
        raise TypeError(f"{_BALL_COLUMN} must be a struct column.")

    ball_fields = {
        field.name: field.dtype for field in ball_dtype.fields
    }
    missing_fields = [
        field for field in ("x", "y") if field not in ball_fields
    ]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"{_BALL_COLUMN} is missing fields: {missing}.")

    nonnumeric_fields = [
        field
        for field in ("x", "y")
        if not ball_fields[field].is_numeric()
    ]
    if nonnumeric_fields:
        invalid = ", ".join(nonnumeric_fields)
        raise TypeError(
            f"{_BALL_COLUMN} fields must be numeric: {invalid}."
        )

    if (
        SYNTHETIC_PASS_END_COLUMN in schema
        and schema[SYNTHETIC_PASS_END_COLUMN] != pl.Boolean
    ):
        raise TypeError(
            f"{SYNTHETIC_PASS_END_COLUMN} must be Boolean."
        )

    return df


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
    valid_partition = pl.all_horizontal(
        *(pl.col(column).is_not_null() for column in group_columns),
        pl.col(_FRAME_COLUMN).is_not_null(),
    )
    selected_order = pl.coalesce(
        first_synthetic_order,
        first_input_order,
    )

    return with_input_order.with_columns(
        (
            valid_partition
            & (input_order == selected_order)
        ).alias(_IS_METRIC_FRAME_COLUMN)
    )


def add_ball_displacement(
    df: pl.LazyFrame,
    possession_groups: str | Sequence[str],
) -> pl.LazyFrame:
    """Add frame-ordered 2D displacement within each possession."""
    group_columns = _resolve_group_columns(df, possession_groups)
    order_columns = (_FRAME_COLUMN, _METRIC_INPUT_ORDER_COLUMN)

    ball = pl.col(_BALL_COLUMN)
    x = ball.struct.field("x")
    y = ball.struct.field("y")
    is_metric_frame = pl.col(_IS_METRIC_FRAME_COLUMN)
    metric_state = pl.when(is_metric_frame).then(
        pl.struct(
            x.alias("x"),
            y.alias("y"),
            pl.col(_FRAME_COLUMN).alias("frame"),
        )
    )
    previous_state = metric_state.forward_fill().shift().over(
        group_columns,
        order_by=order_columns,
    )
    previous_x = previous_state.struct.field("x")
    previous_y = previous_state.struct.field("y")
    previous_frame = previous_state.struct.field("frame")
    delta_x = pl.when(is_metric_frame).then(x - previous_x)
    delta_y = pl.when(is_metric_frame).then(y - previous_y)
    delta_frame = pl.when(is_metric_frame).then(
        pl.col(_FRAME_COLUMN) - previous_frame
    )

    return (
        df.pipe(_validate_metric_schema)
        .pipe(_add_metric_frame_marker, group_columns)
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
