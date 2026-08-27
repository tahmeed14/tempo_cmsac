# from tempoctrl.gradient_sports.possessions_transform import (
    
# )
from tempoctrl.gradient_sports.ingest import scan_integrated


def run_pipeline():
    integrated_df = scan_integrated(df_path="data/integrated/gradient_sports")

if __name__ == "__main__":
    run_pipeline