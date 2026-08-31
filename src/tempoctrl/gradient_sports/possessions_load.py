import logging

import polars as pl

from tempoctrl.gradient_sports.ingest import scan_processed_files
from tempoctrl.gradient_sports.possessions_transform import (
    transform_possessions,
)

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

FINALIZE_ORDER = (
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
    "away_players_smooth",
    "home_players_smooth"

    # "effective_match_team_possession_id",
    # "effective_match_team_player_possession_id",
    # "player_possession_id_imputed",
    # "possession_id_imputation_reason",
    # "is_synthetic_deliver_end",
    # "delivery_"
)


def possessions_load(
    df_path: str,
    output_name: str,
    *,
    frame_rate: float,
) -> None:
    """Lazily load and transform integrated possession data."""
    (
        scan_processed_files(
            df_path=df_path,
        )
        .pipe(transform_possessions, frame_rate=frame_rate)
        .select(FINALIZE_ORDER)
        .sink_parquet(
            f"data/model/{output_name}",
            compression="zstd",
        )
    )
