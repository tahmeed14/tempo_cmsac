import logging

from tempoctrl.gradient_sports.ingest import read_events
from tempoctrl.gradient_sports.event_transform import (
    cleanup_events,
    transform_events,
)
from tempoctrl.gradient_sports.event_features import features_events
from tempoctrl.gradient_sports.event_load import load_events


logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

def run_pipeline(match_id : int) -> None:

    local_path = f"data/raw/gradient_sports/events/{match_id}.json"
    df = read_events(local_path)

    df = transform_events(df)

    df = features_events(df)

    df = cleanup_events(df)

    logger.debug(df.head(5))

    load_events(df)
    

def main():
    matches = [i for i in range(10517, 10518)]

    for match_i in matches:
        run_pipeline(match_i)
    
if __name__ == "__main__":
    main()
