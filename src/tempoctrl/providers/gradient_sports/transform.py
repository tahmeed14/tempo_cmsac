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
    "formattedGameClock",
    "linesBrokenType",
    "pressureType",
    "crossOutcomeType",
    "passOutcomeType",
    )

# For ge_setpiecetype
DEAD_BALL_SET_PIECE_TYPES = ("C", # corner 
                             "D", # drop ball
                             "F", # free kick
                             "G", # goal kick
                             "K", # kickoff
                             "P", # open play
                             "T") # throw in

# For ge_gameeventtype
PAUSE_EVENTS = ("SUB",
                "ON",
                "OFF",
                "OUT",
                "END"
)

TRANSITION_EVENTS = ("FIRSTKICKOFF", 
                     "SECONDKICKOFF", 
                     "THIRDKICKOFF", 
                     "FOURTHKICKOFF",
                     "G", "OTB") # goals and out-of-bounds events

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

# Identify possessions for teams & players
def create_team_possession_flag(df_in: pl.DataFrame) -> pl.DataFrame:
    """Flag rows where a new team possession begins.

    Identify possession changes caused by a team change, a new game, or
    a dead-ball set piece or game-pause event. Null values do not 
    trigger possession starts. The first row is always flagged 
    explicitly.

    Args:
        df_in: Event data containing ``ge_teamid``, ``gameid``,
            ``ge_setpiecetype``, and ``ge_gameeventtype``.

    Returns:
        Event data with a Boolean ``team_possession_start`` column.
        Never a null
    """
    team_changed = pl.col("ge_teamid") != pl.col("ge_teamid").shift()
    game_changed = pl.col("gameid") != pl.col("gameid").shift()
    dead_ball_started = pl.col("ge_setpiecetype").is_in(
        DEAD_BALL_SET_PIECE_TYPES
    )
    game_paused = pl.col("ge_gameeventtype").is_in(PAUSE_EVENTS)
    first_event = pl.int_range(0, pl.len()) == 0

    possession_started = first_event | (
        team_changed
        | game_changed
        | dead_ball_started
        | game_paused
    ).fill_null(False)

    return df_in.with_columns(
        possession_started
        .alias("team_possession_start")
    )

def create_team_possession_id(df_in: pl.DataFrame) -> pl.DataFrame:
    """Create match-level and team-level possession identifiers.

    Convert possession-start flags into a cumulative possession number,
    then combine the game, team, and possession values into a unique
    identifier. Remove the temporary start flag afterward.

    Args:
        df_in: Event data containing ``team_possession_start``,
            ``gameid``, and ``ge_teamname``.

    Returns:
        Event data with ``match_possession_id`` and
        ``match_team_possession_id`` columns.
    """
    possession_data = df_in.with_columns(
        pl.col("team_possession_start")
        .cum_sum()
        .over("gameid")
        .alias("match_possession_id")
    )

    # Intentionally did not place following code in one select() call
    # to avoid repeating the cum_sum() expression when constructing the
    # string identifier, potentially calculating it twice.
    return possession_data.select(
        pl.exclude("team_possession_start"),
        pl.concat_str(
            ["gameid", "ge_teamname", "match_possession_id"],
            separator="_",
        ).alias("match_team_possession_id"),
    )

def create_player_possession_id(df_in: pl.DataFrame) -> pl.DataFrame:
    """Create individual player-possession identifiers.

    Flag a new player possession when the player or team possession
    changes. Cumulatively number those possessions and combine the game,
    team, player, and possession values into a unique identifier.

    Args:
        df_in: Event data containing player and team-possession fields.

    Returns:
        Event data with an ``individual_possession_id`` column, without
        temporary player-possession columns.
    """
    player_changed = (
        pl.col("ge_playerid")
        != pl.col("ge_playerid").shift()
    )
    team_possession_changed = (
        pl.col("match_team_possession_id")
        != pl.col("match_team_possession_id").shift()
    )

    #TODO: Failing 1 test case
    # could try using .ne_missing(player.shift())?
    player_possession_index = (
        (player_changed | team_possession_changed)
        .fill_null(True) # first comparison is always null | null
        .cum_sum()
        .over("gameid")
    )

    possession_data = df_in.with_columns(
        player_possession_index.alias("player_possession_index")
    )

    return possession_data.select(
        pl.exclude(["player_possession_index", "match_possession_id"]),
        pl.concat_str(
            [
                "gameid",
                "ge_teamname",
                "ge_playerid",
                "player_possession_index",
            ],
            separator="_",
        ).alias("match_team_player_possession_id"),
    )

def add_possession_identifiers(df_in: pl.DataFrame) -> pl.DataFrame:
    """Filter for possession-starting events and compute possession IDs.

    Keeps only events that can start or reset possession, including
    kickoffs, OTB, and related types. It then flags possession starts.
    Team and player possession identifiers are assigned using helpers
    from `eventsPossession.py`.

    Args:
        df_in: pl.DataFrame containing event rows with 
        `ge_gameeventtype`.

    Returns:
        pl.DataFrame filtered to possession-relevant events, with
        possession identifiers added.
    """

    # TODO: Investigate why before and after changes the possession ids
    # df_out = df_in.filter(
    #     pl.col('ge_gameeventtype').
    #     is_in(TRANSITION_EVENTS))
    df_out = df_in

    return create_player_possession_id(
        create_team_possession_id(
            create_team_possession_flag(df_in=df_out)
            )
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

    df_out = select_events_columns(df_in = df_in)
    df_out = reclassify_ballheight(df_in = df_out)
    df_out = reclassify_pressuretype(df_in = df_out)
    df_out = reclassify_linesbrokentype(df_in = df_out)
    df_out = reclassify_firsttouch(df_in = df_out)
    df_out = add_possession_identifiers(df_in = df_out)

    return df_out


ORDER = ("match_team_possession_id",
         "match_team_player_possession_id",
         "pe_formattedgameclock",
         "event_number",
         "ge_playername",
         "ge_gameeventtype",
         "ge_outtype",
         "ge_endtype")

def finalize_events(df_in : pl.DataFrame) -> pl.DataFrame:

    df_out = df_in.select(*ORDER,
                          pl.exclude(ORDER))
    # return df_in.filter(
    #     pl.col("ge_gameeventtype").
    #     is_in(TRANSITION_EVENTS)
    # )

    return df_out