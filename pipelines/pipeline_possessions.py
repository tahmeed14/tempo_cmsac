import polars as pl
import logging

from tempoctrl.gradient_sports.ingest import scan_integrated
from tempoctrl.gradient_sports.possessions_transform import (
    transform_possessions,
)

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def run_pipeline() -> pl.LazyFrame:
    """Lazily load and transform integrated possession data."""
    return (
        scan_integrated(
            df_path="data/integrated/gradient_sports",
        )
        # .pipe(transform_possessions)
    )


def main() -> None:
    integrated_df = run_pipeline()
    print(integrated_df.collect_schema())


if __name__ == "__main__":
    main()
