import polars as pl


EVENT_MAIN_COLUMNS = (
    "event_number",
    "gameId",
    "gameEventId",
    "possessionEventId",
    "duration",
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

BODYPART_MAPPER = {
    # Hands/Arms
    "2H": "Hands/Arms", "CA": "Hands/Arms", "PA": "Hands/Arms", 
    "PU": "Hands/Arms", "LH": "Hands/Arms", "RH": "Hands/Arms", 
    "LA": "Hands/Arms", "RA": "Hands/Arms", "TWOHANDS": "Hands/Arms",

    # Header
    "HE": "Head",

    # Upper Body
    "CH": "Torso/Other", "BA": "Torso/Other",
    "BO": "Torso/Other", # BO refers to Bottom which is butt :O
    "LC": "Torso/Other", "RC": "Torso/Other",
    
    # Leg (not Foot)
    "LK": "Leg (not Foot)", "RK": "Leg (not Foot)", "LS": "Leg (not Foot)", 
    "RS": "Leg (not Foot)", "LT": "Leg (not Foot)", "RT": "Leg (not Foot)",
    
    # Foot
    "LF": "Foot", "RF": "Foot", "LB": "Foot", "RB": "Foot",
    "R" : "Foot", "L" : "Foot",
    
    # Not available
    "VM": "N/A"
}

PRESSURE_MAPPER = {
    "L" : "No Pressure",
    "P" : "Pressured (inc. Attempted Pressure)",
    "A" : "Pressured (inc. Attempted Pressure)",
    "N" : "No Pressure"
}

BALL_HEIGHT_MAPPER = {
    "A" : "Air",
    "H" : "Air",
    "L" : "Air",
    "V" : "Air",
    "G" : "Ground",
    "M" : "N/A"
}

def select_events_columns(df_in: pl.DataFrame) -> pl.DataFrame:
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
    return select_events_columns(df_in)

def reclassify_ballheight(df_in : pl.DataFrame) -> pl.DataFrame:
   return (df_in.with_columns(
        pl.col("it_initialheighttype")
        .replace_strict(BALL_HEIGHT_MAPPER, default="N/A")
        .alias("first_touch_ballheight")
        ).drop("it_initialheighttype")
   )

def reclassify_pressuretype(df_in : pl.DataFrame) -> pl.DataFrame:
    return df_in.with_columns(
        pl.col("pe_pressuretype")
        .replace_strict(PRESSURE_MAPPER, default="No Pressure")
        .alias("defender_pressure_type"),

        pl.col("it_initialpressuretype")
        .replace_strict(PRESSURE_MAPPER, default="No Pressure")
        .alias("first_touch_defender_pressure_type")
    )

def reclassify_linesbrokentype(df_in : pl.DataFrame) -> pl.DataFrame:
    return df_in.with_columns(
        pl.col("pe_linesbrokentype").fill_null("None")
    )

def reclassify_firsttouch(df_in : pl.DataFrame) -> pl.DataFrame:
    return df_in.with_columns(
        pl.col("it_initialbodytype")
        .replace_strict(BODYPART_MAPPER, default="N/A")
        .fill_null("Not available")
        .alias("first_touch_bodypart")
        )

def finalize_events(df_in : pl.DataFrame) -> pl.DataFrame:
    # return reclassify_categories_events(df_in)
    df_out = reclassify_ballheight(df_in = df_in)
    df_out = reclassify_pressuretype(df_in = df_out)
    df_out = reclassify_linesbrokentype(df_in = df_out)
    df_out = reclassify_firsttouch(df_in = df_out)
    return df_out