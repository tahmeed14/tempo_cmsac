"""Build processed tracking datasets for configured matches."""

import logging
from pathlib import Path
from time import perf_counter

from tempoctrl.gradient_sports.ingest import (
    scan_tracking,
    stage_tracking,
)
from tempoctrl.gradient_sports.tracking_load import load_tracking
from tempoctrl.gradient_sports.tracking_transform import transform_tracking
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


def run_pipeline(match_id: int) -> tuple[Path, Path]:
    """Build processed tracking data for one match."""
    staged_path = stage_tracking(match_id)
    df_out = scan_tracking(staged_path)
    df_out = transform_tracking(df_out)
    processed_path = load_tracking(
        df_out,
        match_id,
        overwrite=OVERWRITE,
    )
    output_paths = staged_path, processed_path
    for output_path in output_paths:
        logger.info("Tracking pipeline output: %s", output_path)
    return output_paths


def main() -> None:
    """Build tracking outputs and log the complete pipeline runtime."""
    configure_logging()
    logger.info(PIPELINE_DIVIDER)
    logger.info("TRACKING PIPELINE")
    logger.info(PIPELINE_DIVIDER)
    started_at = perf_counter()
    try:
        for match_id in range(10514, 10518):
            run_pipeline(match_id)
    finally:
        logger.info(
            "Tracking pipeline runtime: %s",
            format_pipeline_runtime(perf_counter() - started_at),
        )
        logger.info(PIPELINE_DIVIDER + "\n")


if __name__ == "__main__":
    main()
