from tempoctrl.providers.gradient_sports.ingest import read_events
from tempoctrl.providers.gradient_sports.event_transform import (
    transform_events
    )
from tempoctrl.providers.gradient_sports.event_features import (
    features_events
    )
from tempoctrl.providers.gradient_sports.event_load import load_events

def main():
    matches = [i for i in range(10517, 10518)]
    local_path = f"data/raw/gradient_sports/events/{matches[0]}.json"

    df = read_events(local_path)
    df = transform_events(df)
    df = features_events(df)
    df = load_events(df, None, None)
    
    # df.write_parquet(file="data/investigate/10517_filterafter.parquet",
    # df.write_parquet(file="data/investigate/10517_filterbefore.parquet",
    df.write_parquet(file="data/investigate/10517.parquet",              
                     compression="zstd")
    print(df.head(5))
    for i in df.columns:
        print(i)

if __name__ == "__main__":
    main()