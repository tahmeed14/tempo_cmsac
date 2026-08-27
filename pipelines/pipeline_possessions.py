import polars as pl

from tempoctrl.gradient_sports.ingest import scan_integrated


def run_pipeline() -> pl.LazyFrame:
    """Lazily load all integrated match-level possession data."""
    return scan_integrated(
        df_path="data/integrated/gradient_sports",
    )


def main() -> None:
    integrated_df = run_pipeline()
    print(integrated_df.collect_schema())


if __name__ == "__main__":
    main()
