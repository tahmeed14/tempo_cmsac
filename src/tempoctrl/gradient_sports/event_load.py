import logging
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)


def load_events(df_in: pl.DataFrame) -> None:
    """Write one match of cleaned event data to Parquet."""
    match_ids = (
        df_in.get_column("game_id")
        .drop_nulls()
        .unique()
        .to_list()
    )
    if len(match_ids) != 1:
        raise ValueError(
            "Event data must contain exactly one non-null game_id"
        )

    output_path = Path(
        f"data/processed/gradient_sports/events/{match_ids[0]}.parquet"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_in.write_parquet(output_path, compression="zstd")
    logger.info("Wrote event Parquet file: %s", output_path)
