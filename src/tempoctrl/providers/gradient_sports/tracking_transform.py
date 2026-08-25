import polars as pl

RENAME_MAPPER = {
    "gameRefId" : "game_id"
}

RECAST_MAPPER = {
    "gameid" : pl.Int32,
    "possession_event_id" : pl.Int32,
    "game_event_id" : pl.Int32
}

def rename_columns(df_in : pl.LazyFrame) -> pl.LazyFrame:
    return (df_in
            .rename(RENAME_MAPPER)
            .rename(str.lower)
    )


def recast_columns(df_in: pl.LazyFrame) -> pl.LazyFrame:
    return df_in.cast(RECAST_MAPPER)


def fill_gameid(df_in : pl.LazyFrame) -> pl.LazyFrame:
    ''''''

    return df_in.with_columns(
        pl.col("")
    )