import polars as pl
import logging

from tempoctrl.gradient_sports.possessions_transform import (
    transform_possessions
)
from tempoctrl.gradient_sports.ingest import scan_integrated

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

FINALIZE_ORDER = (
    "game_id",
    "game_event_id",
    "possession_event_id",
    "possession_event",
    "framenum",
    "formattedgameclock",
    "match_team_possession_id",
    "match_team_player_possession_id",
    "possession_event_type",
    "successful_pass_or_cross",
    "player_id",
    "effective_match_team_possession_id",
    "effective_match_team_player_possession_id",
    "player_possession_id_imputed",
    "possession_id_imputation_reason",
    "is_synthetic_deliver_end",
    # "delivery_"
    
)

def possessions_load(df_path : str,
                     output_name : str) -> pl.LazyFrame:
    """Lazily load and transform integrated possession data."""
    return (
        scan_integrated(
            df_path=df_path,
        )
        .pipe(transform_possessions)
        .select(FINALIZE_ORDER)
        .sink_parquet(f"data/model/{output_name}",
                      compression="zstd")
    )