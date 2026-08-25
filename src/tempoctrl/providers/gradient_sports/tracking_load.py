import logging
from pathlib import Path

import polars as pl

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

COLUMN_ORDER = (

)

def tracking_load(
    df_in: pl.LazyFrame,
    match_id: int | str,
    overwrite: bool = False) -> None:

    out_path = Path(
        f"data/processed/gradient_sports/tracking/{match_id}.parquet"
    )

    if out_path.exists() and not overwrite:
        logger.info("Processed tracking file already exists: %s\n" \
        "Note: Use overwrite to rewrite file", out_path)
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_in.sink_parquet(out_path, compression="zstd")
    logger.info("Wrote tracking parquet file: %s", out_path)
