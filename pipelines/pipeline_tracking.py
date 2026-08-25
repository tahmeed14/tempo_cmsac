from tempoctrl.providers.gradient_sports.ingest import read_tracking

def run_pipeline(match_id : int) -> None:
    local_path = f'''data/raw/gradient_sports/tracking/{match_id}.jsonl.bz2'''

    df = read_tracking(local_path)

def main():
    matches = [i for i in range(10517, 10518)]

    for match_i in matches:
        run_pipeline(match_i)
    
if __name__ == "__main__":
    main()