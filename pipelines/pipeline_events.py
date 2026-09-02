"""Build processed event datasets for configured matches."""

import logging
from pathlib import Path
from time import perf_counter

from tempoctrl.gradient_sports.event_features import features_events
from tempoctrl.gradient_sports.event_load import load_events
from tempoctrl.gradient_sports.event_transform import (
    cleanup_events,
    transform_events,
)
from tempoctrl.gradient_sports.ingest import read_events
from tempoctrl.pipeline_runtime import format_pipeline_runtime

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """Configure logging at the executable pipeline boundary."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def run_pipeline(match_id: int) -> tuple[Path, Path]:
    """Build processed event data for one match."""
    local_path = f"data/raw/gradient_sports/events/{match_id}.json"
    df = read_events(local_path)
    df = transform_events(df)
    df = features_events(df)
    df = cleanup_events(df)
    output_paths = load_events(df)
    for output_path in output_paths:
        logger.info("Event pipeline output: %s", output_path)
    return output_paths


def main() -> None:
    """Build event outputs and log the complete pipeline runtime."""
    configure_logging()
    started_at = perf_counter()
    try:
        for match_id in range(10514, 10518):
            run_pipeline(match_id)
    finally:
        logger.info(
            "Event pipeline runtime: %s",
            format_pipeline_runtime(perf_counter() - started_at),
        )


if __name__ == "__main__":
    main()
