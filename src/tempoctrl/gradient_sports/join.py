import logging
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

JOIN_KEYS = ("game_id", "game_event_id", "possession_event_id")
JOIN_ISSUES_DIR = Path("data/investigate/join_issues")
JOIN_KEY_COUNT_COLUMN = "join_key_count"

#FIXME:
DROP_COLUMNS = ("attacking_team_direction",)

def _save_duplicate_event_join_rows(
    df_events: pl.LazyFrame,
    match_id: int | str,
) -> Path | None:
    """Save event rows that violate the many-to-one join requirement."""
    duplicate_rows = (
        df_events.with_columns(
            pl.len().over(JOIN_KEYS).alias(JOIN_KEY_COUNT_COLUMN)
        )
        .filter(pl.col(JOIN_KEY_COUNT_COLUMN) > 1)
        .collect()
    )
    if duplicate_rows.is_empty():
        return None

    JOIN_ISSUES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = JOIN_ISSUES_DIR / f"{match_id}_duplicate_event_rows.parquet"
    duplicate_rows.write_parquet(output_path, compression="zstd")
    logger.error(
        "Saved %d duplicate event join rows to %s",
        duplicate_rows.height,
        output_path,
    )
    return output_path


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


def possession_join(match_id: int | str) -> pl.LazyFrame:
    """Attach processed event data to every matching tracking frame.

    Keep all tracking rows and join events using ``game_id`` and
    ``game_event_id``. Event join keys are cast to the corresponding
    tracking dtypes because the event dataset is substantially smaller.
    """
    df_events = scan_events(match_id)
    df_events = df_events.drop(
        *DROP_COLUMNS
    )

    df_tracking = scan_tracking(match_id)

    tracking_schema = df_tracking.collect_schema()
    event_key_casts = [
        pl.col(column_name).cast(tracking_schema[column_name])
        for column_name in JOIN_KEYS
    ]
    df_events = df_events.with_columns(event_key_casts)
    logger.debug(df_tracking.select(pl.len()).collect())

    df_out = df_tracking.join(
        df_events,
        on=JOIN_KEYS,
        how="left",
        suffix="_event",
        coalesce=True,
        nulls_equal=True,
        validate="m:1",
    )
    try:
        logger.debug(df_out.select(pl.len()).collect())
    except pl.exceptions.ComputeError:
        try:
            _save_duplicate_event_join_rows(df_events, match_id)
        except Exception:
            logger.exception(
                "Could not save join-validation diagnostics for match %s",
                match_id,
            )
        raise

    return df_out


def possession_load(
    match_id: int | str,
    overwrite: bool = False,
) -> None:
    """Join and save integrated possession data for one match."""
    output_path = Path(
        f"data/integrated/gradient_sports/{match_id}.parquet"
    )

    if output_path.is_file() and not overwrite:
        logger.info(
            "Integrated possession file already exists: %s",
            output_path,
        )
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    possession_join(match_id).sink_parquet(
        output_path,
        compression="zstd",
    )
    logger.info("Wrote integrated possession file: %s", output_path)
