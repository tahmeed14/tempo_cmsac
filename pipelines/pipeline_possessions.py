import polars as pl
import logging

from tempoctrl.gradient_sports.ingest import scan_integrated
from tempoctrl.gradient_sports.possessions_transform import (
    transform_possessions,
)
from tempoctrl.gradient_sports.possessions_load import possessions_load

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def run_pipeline(df_path : str,) -> None:
    possessions_load(df_path=df_path,
                     output_name="dev.parquet")    


def main() -> None:
    run_pipeline(df_path="data/integrated/gradient_sports")

if __name__ == "__main__":
    main()
