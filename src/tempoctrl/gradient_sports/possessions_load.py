"""Build frame-, team-, and player-level possession datasets."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from tempoctrl.gradient_sports.frame_rates import FrameRateSpec
from tempoctrl.gradient_sports.ingest import scan_processed_files
from tempoctrl.gradient_sports.possessions_transform import (
    transform_possessions,
)
from tempoctrl.gradient_sports.tempo_metrics import (
    PossessionLevel,
    aggregate_possession_tempo,
)

FRAME_LEVEL_ORDER = (
    "match_team_possession_id",
    "match_team_player_possession_id",
    "dev_match_team_player_possession_id",
    "dev_match_team_possession_id",
    "game_id",
    "game_event_id",
    "possession_event_id",
    "possession_event_type",
    "successful_pass_or_cross",
    "player_id",
    "attacking_team_direction",
    "game_event_type",
    "framenum",
    "formattedgameclock",
    "is_synthetic_pass_end",
    "pitch_third",
    "balls_smooth",
    "delta_x",
    "delta_y",
    "delta_frame",
    "ball_displacement",
    "ball_speed",
    "frame_rate",
    "away_players_smooth",
    "home_players_smooth",
)


_TEMPO_INPUT_COLUMNS = (
    "game_id",
    "dev_match_team_possession_id",
    "dev_match_team_player_possession_id",
    "framenum",
    "ball_displacement",
    "delta_frame",
    "frame_rate",
)
_POSSESSION_LEVELS: tuple[PossessionLevel, ...] = ("team", "player")


def write_possession_outputs(
    frame_df: pl.LazyFrame,
    output_name: str,
    *,
    output_dir: str | Path,
) -> None:
    """Write frame data once, then derive possession-level outputs.

    The frame parquet is a materialization boundary. Team and player
    aggregations scan only their required columns from that file, so the
    upstream transformation graph executes once rather than once per
    output.

    Args:
        frame_df: Fully transformed frame-level possession rows.
        output_name: File name for the frame-level parquet.
        output_dir: Directory receiving all three parquet files.
    """
    output_directory = Path(output_dir)
    output_directory.mkdir(parents=True, exist_ok=True)
    frame_path = output_directory / output_name

    frame_df.sink_parquet(frame_path, compression="zstd")

    tempo_input = pl.scan_parquet(frame_path).select(
        _TEMPO_INPUT_COLUMNS
    )
    for level in _POSSESSION_LEVELS:
        output_path = output_directory / f"{level}_{output_name}"
        (
            tempo_input.pipe(
                aggregate_possession_tempo,
                level,
            ).sink_parquet(output_path, compression="zstd")
        )


def possessions_load(
    df_path: str,
    output_name: str,
    *,
    output_dir: str | Path,
    frame_rate: FrameRateSpec,
) -> None:
    """Load, transform, and write possession datasets."""
    frame_df = (
        scan_processed_files(df_path=df_path)
        .pipe(transform_possessions, frame_rate=frame_rate)
        .select(FRAME_LEVEL_ORDER)
    )

    write_possession_outputs(
        frame_df,
        output_name,
        output_dir=output_dir,
    )
