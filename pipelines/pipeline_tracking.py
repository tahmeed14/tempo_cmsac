"""Build processed tracking datasets for configured matches."""

import logging

from tempoctrl.gradient_sports.ingest import (
    scan_tracking,
    stage_tracking,
)
from tempoctrl.gradient_sports.tracking_load import load_tracking
from tempoctrl.gradient_sports.tracking_transform import transform_tracking
from tempoctrl.pipeline_runtime import log_pipeline_runtime

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

OVERWRITE = True


def run_pipeline(match_id: int) -> None:
    """Build processed tracking data for one match."""
    staged_path = stage_tracking(match_id)
    df_out = scan_tracking(staged_path)
    df_out = transform_tracking(df_out)
    load_tracking(df_out, match_id, overwrite=OVERWRITE)


def main() -> None:
    """Build tracking outputs and log the complete pipeline runtime."""
    with log_pipeline_runtime(logger, "Tracking"):
        for match_id in range(10514, 10518):
            run_pipeline(match_id)


if __name__ == "__main__":
    main()
