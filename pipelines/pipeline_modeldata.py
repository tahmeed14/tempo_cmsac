"""Build processed model data for Bayesian modeling."""

import logging
from pathlib import Path
from time import perf_counter

from tempoctrl.gradient_sports.modeldata import load_modeldata
from tempoctrl.pipeline_runtime import format_pipeline_runtime

logger = logging.getLogger(__name__)
PIPELINE_DIVIDER = "=" * 72


def configure_logging() -> None:
    """Configure logging at the executable pipeline boundary."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def run_pipeline() -> Path:
    """Build model data and log its output path."""
    output_path = load_modeldata()
    logger.info("Model data pipeline output: %s", output_path)
    return output_path


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
        logger.info(PIPELINE_DIVIDER)


if __name__ == "__main__":
    main()
