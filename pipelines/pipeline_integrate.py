"""Build integrated event and tracking datasets."""

import logging

from tempoctrl.gradient_sports.join import possession_load
from tempoctrl.pipeline_runtime import log_pipeline_runtime

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

OVERWRITE = True


def main() -> None:
    """Build integrated possession files for configured matches."""
    with log_pipeline_runtime(logger, "Integration"):
        for match_id in range(10514, 10518):
            possession_load(match_id, overwrite=OVERWRITE)


if __name__ == "__main__":
    main()
