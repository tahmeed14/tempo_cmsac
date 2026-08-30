from __future__ import annotations

import polars as pl

FPS = 29.97 # pulled from metadata #FIXME:

def add_ball_displacement(
    df: pl.LazyFrame, 
    possession_groups: str | tuple[str, ...]) -> pl.LazyFrame:
    """Add 2D ball displacement between consecutive possession frames."""
    ball_struct = "balls_smooth"
    group_cols = ["game_id", possession_groups]

    x = pl.col(ball_struct).struct.field("x")
    y = pl.col(ball_struct).struct.field("y")

    dx = x - x.shift().over(group_cols)
    dy = y - y.shift().over(group_cols)

    return df.with_columns(
        dx.alias("dx"),
        dy.alias("dy"),
        (dx.pow(2) + dy.pow(2)).sqrt().alias("ball_displacement")
    ).pipe(add_ball_speed, FPS)

def add_ball_speed(
    df: pl.LazyFrame,
    frame_rate: float) -> pl.DataFrame:
    """Add frame-level ball speed in meters per second."""
    if frame_rate <= 0:
        raise ValueError("frame_rate must be greater than 0.")

    return df.with_columns(
        (pl.col("ball_displacement") * frame_rate).alias("ball_speed")
    )

def add_tempo(df: pl.LazyFrame):
    pass