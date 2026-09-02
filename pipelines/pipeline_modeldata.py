"""Build processed model data for Bayesian modeling."""

import logging
from collections.abc import Sequence
from pathlib import Path
from time import perf_counter

from tempoctrl.gradient_sports.modeldata import (
    EVENTS_PATH,
    MODELDATA_PATH,
    PLAYER_POSSESSIONS_PATH,
    POSSESSION_LOOKUP_PATH,
    load_modeldata,
)
from tempoctrl.pipeline_runtime import format_pipeline_runtime

logger = logging.getLogger(__name__)
PIPELINE_DIVIDER = "=" * 72


def configure_logging() -> None:
    """Configure logging at the executable pipeline boundary."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def run_pipeline(
    events_path: str | Path | Sequence[str | Path] = EVENTS_PATH,
    player_possessions_path: str | Path = PLAYER_POSSESSIONS_PATH,
    possession_lookup_path: str | Path = POSSESSION_LOOKUP_PATH,
    output_path: str | Path = MODELDATA_PATH,
) -> Path:
    """Build model data and log its output path."""
    written_path = load_modeldata(
        events_path=events_path,
        player_possessions_path=player_possessions_path,
        possession_lookup_path=possession_lookup_path,
        output_path=output_path,
    )
    logger.info("Model data pipeline output: %s", written_path)
    return written_path


def main() -> None:
    """Build model data and log the complete pipeline runtime."""
    configure_logging()
    logger.info(PIPELINE_DIVIDER)
    logger.info("MODEL DATA PIPELINE")
    logger.info(PIPELINE_DIVIDER)
    started_at = perf_counter()
    try:
        run_pipeline()
    finally:
        logger.info(
            "Model data pipeline runtime: %s",
            format_pipeline_runtime(perf_counter() - started_at),
        )
        logger.info(PIPELINE_DIVIDER + "\n")


if __name__ == "__main__":
    main()
