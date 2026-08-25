import polars as pl

from tempoctrl.providers.gradient_sports.ingest import read_events
from tempoctrl.providers.gradient_sports.event_transform import (
    transform_events
    )
from tempoctrl.providers.gradient_sports.event_features import (
    features_events
    )
from tempoctrl.providers.gradient_sports.event_load import load_events


def run_pipeline(match_id) -> None:

    local_path = f"data/raw/gradient_sports/events/{match_id}.json"
    out_path = "data/processed/gradient_sports/events/"

    df = read_events(local_path)

    df = transform_events(df)

    df = features_events(df)

    df = load_events(df, 
                    out_path,
                    match_id)


def main():
    matches = [i for i in range(10517, 10518)]

    for match_i in matches:
        run_pipeline(match_i)
    
if __name__ == "__main__":
    main()