from tempoctrl.gradient_sports.join import possession_join

def main():    
    match_id = 10517

    df = possession_join(match_id)
    df.sink_parquet(path=f"data/curated/gradient_sports/{match_id}.parquet",
                    compression="zstd")

if __name__ == "__main__":
    main()