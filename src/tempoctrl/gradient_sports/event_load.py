import polars as pl
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def remove_event_prefixes(df_in : pl.DataFrame) -> pl.DataFrame:
    return (
        df_in.rename(
            lambda column_name: (
                column_name[3:]
                if column_name.startswith(("ge_", "pe_"))
                else column_name
            )
        )
    )

# FIXME: Maybe add to the top of the pipeline
RENAME_MAPPER = {
    "gameid" : "game_id",
    "gameeventid" : "game_event_id",
    "possessioneventid" : "possession_event_id",
    "ge_gameeventtype" : "game_event_type",
    "pe_possessioneventtype" : "possession_event_type"

    }

def rename_columns(df_in : pl.DataFrame) -> pl.DataFrame:
    return df_in.rename(RENAME_MAPPER)

#TODO:
def validate_events(df_in : pl.DataFrame) -> pl.DataFrame:
    """"""

    return -1

FINALIZE_ORDER = (
        "game_id",
        "formattedgameclock",
        "gamestate",
        "playername",
        "playerid",
        "teamname",
        "teamid",
        "match_team_possession_id",
        "match_team_player_possession_id",
        "team_possession_start",
        "event_number",
        "game_event_type"
        )

FINALIZE_EXCLUDE = (
    *FINALIZE_ORDER,
    "outtype",
    "endtype",
)


def organize_event_columns(df_in: pl.DataFrame) -> pl.DataFrame:
    return (
        df_in.filter(pl.col("match_team_possession_id").is_not_null())
        .select(
            *FINALIZE_ORDER,
            pl.exclude(*FINALIZE_ORDER, *FINALIZE_EXCLUDE),
        )
    )

def load_events(df_in: pl.DataFrame,
                output_dir : str | Path,
                match_id : str | int) -> None:
    """
    """

    # polish
    events_df = (df_in
                 .pipe(rename_columns)
                 .pipe(remove_event_prefixes)
                 .pipe(organize_event_columns))

    logger.debug(events_df)

    # validate

    "data/processed/gradient_sports/events"

    # write
    events_df.write_parquet(file = f'''{output_dir}{match_id}.parquet''',
                    compression="zstd"
                    )
