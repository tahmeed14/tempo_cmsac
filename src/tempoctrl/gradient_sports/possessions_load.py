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
    "framenum"
)

def possessions_load(df_path : str,
                     output_name : str) -> pl.LazyFrame:
    """Lazily load and transform integrated possession data."""
    return (
        scan_integrated(
            df_path=df_path,
        )
        .pipe(transform_possessions)
        .sink_parquet(f"data/model/{output_name}",
                      compression="zstd")
    )