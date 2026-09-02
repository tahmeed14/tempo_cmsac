"""Build integrated event and tracking datasets."""

import logging
from pathlib import Path
from time import perf_counter

from tempoctrl.gradient_sports.join import possession_load
from tempoctrl.pipeline_runtime import format_pipeline_runtime

logger = logging.getLogger(__name__)
PIPELINE_DIVIDER = "=" * 72


def configure_logging() -> None:
    """Configure logging at the executable pipeline boundary."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


OVERWRITE = True


def run_pipeline(match_id: int) -> Path:
    """Build one integrated match dataset and log its output path."""
    output_path = possession_load(match_id, overwrite=OVERWRITE)
    logger.info("Integration pipeline output: %s", output_path)
    return output_path


def main() -> None:
    """Build integrated possession files for configured matches."""
    configure_logging()
    logger.info(PIPELINE_DIVIDER)
    logger.info("INTEGRATION PIPELINE")
    logger.info(PIPELINE_DIVIDER)
    started_at = perf_counter()
    try:
        for match_id in range(10514, 10518):
            run_pipeline(match_id)
    finally:
        logger.info(
            "Integration pipeline runtime: %s",
            format_pipeline_runtime(perf_counter() - started_at),
        )
        logger.info(PIPELINE_DIVIDER + "\n")


if __name__ == "__main__":
    main()
