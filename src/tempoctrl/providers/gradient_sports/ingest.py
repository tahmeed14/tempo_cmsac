import polars as pl

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

def read_tracking(local_path : str) -> pl.DataFrame:
    # TODO: Implement tracking data reading logic
    pass