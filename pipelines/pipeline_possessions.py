"""Build frame- and possession-level model datasets."""

import logging
from pathlib import Path

from tempoctrl.gradient_sports.frame_rates import (
    GRADIENT_SPORTS_DEFAULT_FPS,
    FrameRateSpec,
    log_frame_rate_resolutions,
    resolve_gradient_sports_frame_rates,
)
from tempoctrl.gradient_sports.possessions_load import possessions_load
from tempoctrl.pipeline_runtime import log_pipeline_runtime

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

OUTPUT_DIRECTORY = Path("data/model")
METADATA_DIRECTORY = Path("data/raw/gradient_sports/metadata")


def run_pipeline(
    df_path: str,
    *,
    metadata_dir: str | Path,
    default_frame_rate: float = GRADIENT_SPORTS_DEFAULT_FPS,
) -> None:
    """Run possession processing with match-specific FPS metadata."""
    resolutions = resolve_gradient_sports_frame_rates(
        df_path,
        metadata_dir,
        default_frame_rate=default_frame_rate,
    )
    log_frame_rate_resolutions(resolutions, logger)

    frame_rates: FrameRateSpec = {
        resolution.game_id: resolution.frame_rate
        for resolution in resolutions
    }
    possessions_load(
        df_path=df_path,
        output_name="dev.parquet",
        output_dir=OUTPUT_DIRECTORY,
        frame_rate=frame_rates,
    )


def main() -> None:
    """Build possession outputs and log the complete pipeline runtime."""
    with log_pipeline_runtime(logger, "Possession"):
        run_pipeline(
            df_path="data/integrated/gradient_sports",
            metadata_dir=METADATA_DIRECTORY,
        )


if __name__ == "__main__":
    main()
