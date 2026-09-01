"""Build player lookup data from Gradient Sports roster files."""

from pathlib import Path

import polars as pl


POSITION_MAPPER = {
    # Goalkeepers
    "GK": "Goalkeeper",

    # Defenders
    "CB": "Centre Back",
    "RCB": "Centre Back",
    "LCB": "Centre Back",
    "MCB": "Centre Back",
    "LB": "Full Back",
    "RB": "Full Back",
    "LWB": "Full Back",
    "RWB": "Full Back",

    # Midfielders
    "DM": "Midfielder",
    "LDM": "Midfielder",
    "RDM": "Midfielder",
    "CM": "Midfielder",
    "LCM": "Midfielder",
    "RCM": "Midfielder",
    "AM": "Midfielder",
    "LAM": "Midfielder",
    "RAM": "Midfielder",

    # Attackers
    "LW": "Winger",
    "RW": "Winger",
    "LM": "Winger",
    "RM": "Winger",
    "ST": "Forward",
    "CF": "Forward",
    "SS": "Forward",
    "LS": "Forward",
    "RS": "Forward",
}

PLAYER_GAME_COLUMNS = (
    "game_id",
    "team_id",
    "player_id",
    "shirt_number",
    "position_group_type",
    "player_position_group",
    "player_name",
    "team_name",
    "started",
)

PLAYER_GAME_SCHEMA = {
    "game_id": pl.Int64,
    "team_id": pl.Int64,
    "player_id": pl.Int64,
    "shirt_number": pl.Int32,
    "position_group_type": pl.String,
    "player_position_group": pl.String,
    "player_name": pl.String,
    "team_name": pl.String,
    "started": pl.Boolean,
}


def _parse_game_id(roster_path: Path) -> int:
    """Parse a numeric game identifier from a roster filename."""
    try:
        return int(roster_path.stem)
    except ValueError as error:
        raise ValueError(
            "Roster filename must be a numeric game ID: "
            f"{roster_path.name}"
        ) from error


def _validate_position_groups(df_roster: pl.DataFrame) -> None:
    """Raise an error when a roster has an unmapped position code."""
    position_codes = set(
        df_roster.get_column("position_group_type")
        .drop_nulls()
        .to_list()
    )
    unmapped_codes = sorted(position_codes - POSITION_MAPPER.keys())
    if unmapped_codes:
        formatted_codes = ", ".join(unmapped_codes)
        raise ValueError(
            "Unmapped positionGroupType values: "
            f"{formatted_codes}"
        )


def read_roster_file(roster_path: str | Path) -> pl.DataFrame:
    """Read and normalize one Gradient Sports roster file.

    Args:
        roster_path: JSON roster path named with its numeric game ID.

    Returns:
        A typed player-game table with mapped position groups.

    Raises:
        ValueError: If the filename or a position code is invalid.
    """
    roster_path = Path(roster_path)
    game_id = _parse_game_id(roster_path)
    df_raw = pl.read_json(roster_path, infer_schema_length=None)

    df_roster = df_raw.select(
        pl.lit(game_id).cast(pl.Int64).alias("game_id"),
        pl.col("team").struct.field("id").cast(pl.Int64).alias("team_id"),
        pl.col("player")
        .struct.field("id")
        .cast(pl.Int64)
        .alias("player_id"),
        pl.col("shirtNumber").cast(pl.Int32).alias("shirt_number"),
        pl.col("positionGroupType")
        .cast(pl.String)
        .alias("position_group_type"),
        pl.col("player")
        .struct.field("nickname")
        .cast(pl.String)
        .alias("player_name"),
        pl.col("team")
        .struct.field("name")
        .cast(pl.String)
        .alias("team_name"),
        pl.col("started").cast(pl.Boolean),
    )
    _validate_position_groups(df_roster)

    return (
        df_roster.with_columns(
            pl.col("position_group_type")
            .replace_strict(
                POSITION_MAPPER,
                default=None,
                return_dtype=pl.String,
            )
            .alias("player_position_group")
        )
        .cast(PLAYER_GAME_SCHEMA)
        .select(PLAYER_GAME_COLUMNS)
    )
