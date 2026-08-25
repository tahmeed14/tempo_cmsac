from tempoctrl.providers.gradient_sports.ingest import stage_tracking

def run_pipeline(match_id : int) -> None:

    df = stage_tracking(match_id)
    print(df)

def main():
    matches = [i for i in range(10517, 10518)]

    for match_i in matches:
        run_pipeline(match_i)
    
if __name__ == "__main__":
    main()