from tempoctrl.gradient_sports.merge import merge

def main():    
    match_id = 10517

    df = merge(match_id)
    df.sink_parquet(path=f"data/curated/gradient_sports/{match_id}.parquet",
                    compression="zstd")

if __name__ == "__main__":
    main()