import logging
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

MATCH_POSSESSION_LOOKUP_PATH = Path(
    "data/curated/gradient_sports/possession_lookup/"
    "match_possession_lookup.parquet"
)

MATCH_POSSESSION_LOOKUP_COLUMNS = (
    "game_id",
    "match_team_player_possession_id",
    "player_id",
    "playername",
    "team_id",
    "teamname",
)


def write_match_possession_lookup(
    df_in: pl.DataFrame,
    output_path: str | Path = MATCH_POSSESSION_LOOKUP_PATH,
) -> Path:
    """Upsert one match's player-possession metadata into a lookup."""
    output_path = Path(output_path)
    game_ids = df_in.get_column("game_id").drop_nulls().unique()
    df_lookup = (
        df_in.select(MATCH_POSSESSION_LOOKUP_COLUMNS)
        .filter(pl.col("match_team_player_possession_id").is_not_null())
        .unique()
    )

    if output_path.is_file():
        df_existing = pl.read_parquet(output_path).filter(
            ~pl.col("game_id").is_in(game_ids)
        )
        df_lookup = pl.concat(
            (df_existing, df_lookup),
            how="vertical_relaxed",
        )

    df_lookup = df_lookup.sort(
        ("game_id", "match_team_player_possession_id")
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_lookup.write_parquet(output_path, compression="zstd")
    logger.info("Wrote match possession lookup: %s", output_path)
    return output_path


def load_events(df_in: pl.DataFrame) -> None:
    """Write one match of cleaned event data to Parquet."""
    match_ids = (
        df_in.get_column("game_id")
        .drop_nulls()
        .unique()
        .to_list()
    )
    if len(match_ids) != 1:
        raise ValueError(
            "Event data must contain exactly one non-null game_id"
        )

    output_path = Path(
        f"data/processed/gradient_sports/events/{match_ids[0]}.parquet"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_match_possession_lookup(df_in)
    df_in.write_parquet(output_path, compression="zstd")
    logger.info("Wrote event Parquet file: %s", output_path)
