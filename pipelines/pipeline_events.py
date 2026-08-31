"""Build processed event datasets for configured matches."""

import logging

from tempoctrl.gradient_sports.event_features import features_events
from tempoctrl.gradient_sports.event_load import load_events
from tempoctrl.gradient_sports.event_transform import (
    cleanup_events,
    transform_events,
)
from tempoctrl.gradient_sports.ingest import read_events
from tempoctrl.pipeline_runtime import log_pipeline_runtime

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def run_pipeline(match_id: int) -> None:
    """Build processed event data for one match."""
    local_path = f"data/raw/gradient_sports/events/{match_id}.json"
    df = read_events(local_path)
    df = transform_events(df)
    df = features_events(df)
    df = cleanup_events(df)
    load_events(df)


def main() -> None:
    """Build event outputs and log the complete pipeline runtime."""
    with log_pipeline_runtime(logger, "Event"):
        for match_id in range(10514, 10518):
            run_pipeline(match_id)


if __name__ == "__main__":
    main()
