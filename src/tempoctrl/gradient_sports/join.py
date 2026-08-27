import logging
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

JOIN_KEYS = ("game_id", "game_event_id")


def _scan_processed_match(
    match_id: int | str,
    dataset_name: str,
) -> pl.LazyFrame:
    """Validate and lazily scan one processed match file."""
    data_path = Path(
        f"data/processed/gradient_sports/{dataset_name}/"
        f"{match_id}.parquet"
    )

    if not data_path.is_file():
        logger.error(
            "Processed %s file does not exist: %s",
            dataset_name,
            data_path,
        )
        raise FileNotFoundError(
            f"Processed {dataset_name} file does not exist: {data_path}"
        )

    logger.info("Scanning processed %s file: %s", dataset_name, data_path)
    return pl.scan_parquet(data_path)


def scan_events(match_id: int | str) -> pl.LazyFrame:
    """Lazily scan processed event data for one match."""
    return _scan_processed_match(match_id, "events")


def scan_tracking(match_id: int | str) -> pl.LazyFrame:
    """Lazily scan processed tracking data for one match."""
    return _scan_processed_match(match_id, "tracking")


def merge(match_id: int | str) -> pl.LazyFrame:
    """Attach processed event data to every matching tracking frame.

    Keep all tracking rows and join events using ``game_id`` and
    ``game_event_id``. Event join keys are cast to the corresponding
    tracking dtypes because the event dataset is substantially smaller.
    """
    df_events = scan_events(match_id)
    df_tracking = scan_tracking(match_id)

    tracking_schema = df_tracking.collect_schema()
    event_key_casts = [
        pl.col(column_name).cast(tracking_schema[column_name])
        for column_name in JOIN_KEYS
    ]
    df_events = df_events.with_columns(event_key_casts)
    logger.debug(df_tracking.select(pl.len()).collect())

    #FIXME: return in one go
    temp = df_tracking.join(
        df_events.filter(pl.col("possessioneventtype") != "IT"),
        on=JOIN_KEYS,
        how="left",
        suffix="_event",
        coalesce=True,
    )
    logger.debug(temp.select(pl.len()).collect())

    return temp