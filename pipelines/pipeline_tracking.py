import polars as pl

from tempoctrl.providers.gradient_sports.ingest import (
    scan_tracking,
    stage_tracking,
)
from tempoctrl.providers.gradient_sports.tracking_transform import (
    tracking_transform
)
from tempoctrl.providers.gradient_sports.tracking_load import (
    tracking_load
)


def run_pipeline(match_id: int) -> pl.LazyFrame:
    """Stage and lazily scan tracking data for one match."""
    staged_path = stage_tracking(match_id)

    df_out = scan_tracking(staged_path)

    df_out = tracking_transform(df_out)

    tracking_load(df_out, match_id, overwrite=True)

    return df_out


def main() -> None:
    matches = range(10517, 10518)

    for match_id in matches:
        tracking = run_pipeline(match_id)

if __name__ == "__main__":
    main()
