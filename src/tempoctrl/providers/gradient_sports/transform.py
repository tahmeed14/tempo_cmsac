import polars as pl

EVENT_MAIN_COLUMNS = (
    "event_number",
    "gameId",
    "gameEventId",
    "possessionEventId",
    "startTime",
    "endTime",
    "duration",
    "eventTime",
    "sequence",
    )

INITIAL_TOUCH_COLUMNS = (
    "initialPressureType",
    "initialHeightType",
    "initialBodyType")

GAME_EVENTS_COLUMNS = (
    "gameEventType",
    "playerId",
    "playerName",
    "teamId",
    "teamName",
    "homeTeam",
    "setpieceType",
    "outType",
    "endType",
    "period",
    "touches",
    )

POSSESSION_EVENTS_COLUMNS = (
    "possessionEventType",
    "gameClock",
    "formattedGameClock",
    "linesBrokenType",
    "pressureType",
    "crossOutcomeType",
    "passOutcomeType",
    )

def select_relevant_events_columns(df_in: pl.DataFrame) -> pl.DataFrame:
    """Unnest selected event structs and return a flat DataFrame.

    Select the main event columns and configured fields from the nested
    event structs. Prefix extracted fields according to their source and
    include the attacking direction from ``stadiumMetadata``.

    Args:
        df_in: Event data containing the required identifier and nested
            struct columns.

    Returns:
        A flat Polars DataFrame containing the selected event fields.
    """

    struct_selections = (
        ("initialTouch", "it_", INITIAL_TOUCH_COLUMNS),
        ("gameEvents", "ge_", GAME_EVENTS_COLUMNS),
        ("possessionEvents", "pe_", POSSESSION_EVENTS_COLUMNS),
    )

    # loop through the struct selections then through the fields for
    # each struct, creating a list of fields to select from df
    nested_fields = [
        pl.col(struct_column)
        .struct.field(field)
        .alias(f"{prefix}{field}")
        for struct_column, prefix, fields in struct_selections
        for field in fields
    ]

    return df_in.select(
        *EVENT_MAIN_COLUMNS,
        pl.col("stadiumMetadata").struct.field(
            "teamAttackingDirection"
        ),
        *nested_fields,
        ).rename(
            str.lower
            )

def transform_events(df_in: pl.DataFrame) -> pl.DataFrame:
    """Transform the raw event data into a flat DataFrame with game 
    state.

    Args:
        df_in: Event data containing the required identifier and nested
            struct columns.

    Returns:
        A flat Polars DataFrame containing the selected event fields and
        game state variables.
    """
    return select_relevant_events_columns(df_in)
