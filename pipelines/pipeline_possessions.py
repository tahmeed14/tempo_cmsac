import logging

from tempoctrl.gradient_sports.possessions_load import possessions_load

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def run_pipeline(
    df_path: str,
    *,
    frame_rate: float,
) -> None:
    possessions_load(
        df_path=df_path,
        output_name="dev.parquet",
        frame_rate=frame_rate,
    )


def main() -> None:
    run_pipeline(
        df_path="data/integrated/gradient_sports",
        frame_rate=29.97,
    )


if __name__ == "__main__":
    main()
