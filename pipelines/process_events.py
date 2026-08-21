import polars as pl

from tempoctrl.providers.gradient_sports.ingest import read_events
from tempoctrl.providers.gradient_sports.transform import (
    transform_events
    )
from tempoctrl.providers.gradient_sports.event_features import (
    event_features
    )

def main():
    matches = [i for i in range(10517, 10518)]
    local_path = f"data/raw/gradient_sports/events/{matches[0]}.json"

    df = read_events(local_path)
    df = transform_events(df)
    df = event_features(df)

    print(df.head(5))
    for i in df.columns:
        print(i)


if __name__ == "__main__":
    main()