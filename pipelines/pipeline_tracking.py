import polars as pl

from tempoctrl.gradient_sports.ingest import (
    scan_tracking,
    stage_tracking,
)
from tempoctrl.gradient_sports.tracking_transform import transform_tracking
from tempoctrl.gradient_sports.tracking_load import load_tracking


def run_pipeline(match_id: int) -> pl.LazyFrame:

    staged_path = stage_tracking(match_id)

    df_out = scan_tracking(staged_path)
    df_out = transform_tracking(df_out)

    load_tracking(df_out, match_id, overwrite=True)

    return df_out


def main() -> None:
    matches = range(10517, 10518)

    for match_id in matches:
        tracking = run_pipeline(match_id)

if __name__ == "__main__":
    main()
