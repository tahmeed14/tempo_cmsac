from pathlib import Path
import polars as pl

from tempoctrl.model.transform import (
    transform_model_data,
)

def read_model_data(path: str | Path) -> pl.LazyFrame | pl.DataFrame:
    return pl.read_parquet(path, low_memory=True)


def load_curated_model_df(path: str | Path) -> pl.LazyFrame | pl.DataFrame:
    model_df = read_model_data(path)
    model_df = (model_df.pipe(transform_model_data))

    return model_df