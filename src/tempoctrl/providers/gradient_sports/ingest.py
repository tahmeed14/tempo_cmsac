from pathlib import Path
import polars as pl
import bz2

def read_events(local_path : str) -> pl.DataFrame:
    """read and unnest events JSON for a single match.

    Reads the raw events JSON for `local_path`, assigns a 1-based
    `event_number` index, and returns the DataFrame with selected
    columns unnested via `selectRelevantEventsColumns`.

    Parameters
    - local_path: string path to the events JSON file.

    Returns
    - pl.DataFrame: unnested events ready for downstream processing.
    """
    # TODO: Issue #3
    df = pl.read_json(local_path, infer_schema_length = None)
    return df.with_row_index("event_number", offset = 1)


def stage_tracking(match_id : str, 
                   overwrite : bool = False) -> Path:

    raw_path = f"data/raw/gradient_sports/tracking/{match_id}.jsonl.bz2"
    staged_path = f"data/staged/gradient_sports/tracking/{match_id}.parquet"

    raw_path = Path(raw_path)
    staged_path = Path(staged_path)

    stage_is_current = (
        staged_path.exists()
        and staged_path.stat().st_mtime >= raw_path.stat().st_mtime
        and not overwrite
    )

    if stage_is_current:
        return staged_path

    staged_path.parent.mkdir(parents=True, exist_ok=True)

    with bz2.open(raw_path, "rb") as file:
        (
            pl.scan_ndjson(
                file,
                infer_schema_length=10_000,
            )
            .sink_parquet(staged_path)
        )

    return staged_path