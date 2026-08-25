import polars as pl

from tempoctrl.providers.gradient_sports.ingest import (
    scan_tracking,
    stage_tracking,
)


def run_pipeline(match_id: int) -> pl.LazyFrame:
    """Stage and lazily scan tracking data for one match."""
    staged_path = stage_tracking(match_id)
    return scan_tracking(staged_path)


def main() -> None:
    matches = range(10517, 10518)

    for match_id in matches:
        tracking = run_pipeline(match_id)
        print("\n")
        for column_name, dtype in tracking.collect_schema().items():
            print(f"{column_name}: {dtype}")

if __name__ == "__main__":
    main()
