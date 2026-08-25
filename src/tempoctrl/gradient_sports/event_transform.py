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



TRANSITION_EVENTS = (
                    #WARNING: changing this will impact
                    # create_team_possession_flag() 
                    "FIRSTKICKOFF", 
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

SETPIECE_MAPPER = {
    "O" : "Open Play",
    "D" : "Drop Kick",
    "F" : "Free Kick",
    "G" : "Goal Kick",
    "K" : "Kickoff",
    "P" : "Penalty",
    "T" : "Throw In",
    "C" : "Corner"
}

LINESBROKEN_MAPPER = {
    "A" : "Attack",
    "AD" : "Attack & Defense (Midfield Bypassed)",
    "AM" : "Attack & Midfield",
    "AMD" : "Attack, Midfield, & Defense",
    "D" : "Defense",
    "M" : "Midfield",
    "MD" : "Midfield & Defense"
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


def drop_pen_shootouts(df_in: pl.DataFrame) -> pl.DataFrame:
    """Remove shootout events occurring after the end of normal play.

    Find the last event in each match where ``ge_gameeventtype`` is
    ``"END"`` and ``ge_endtype`` is ``"G"``. Keep that event and every
    earlier event in the match. If a match has no qualifying end event,
    retain all of its rows.

    Args:
        df_in: Event data containing ``gameid``, ``event_number``,
            ``ge_gameeventtype``, and ``ge_endtype``.

    Returns:
        Event data through the end of normal play for each match.
    """
    normal_time_ended = (
        (pl.col("ge_gameeventtype") == "END")
        & (pl.col("ge_endtype") == "G")
    )
    normal_time_end_event = (
        pl.when(normal_time_ended)
        .then(pl.col("event_number"))
        .max()
        .over("gameid")
    )

    return df_in.filter(
        normal_time_end_event.is_null()
        | (pl.col("event_number") <= normal_time_end_event)
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
        ).drop(["it_initialpressuretype", 
                "pe_pressuretype"]
    )


def reclassify_firsttouch(df_in : pl.DataFrame) -> pl.DataFrame:
    return df_in.with_columns(
        pl.col("it_initialbodytype")
        .replace_strict(BODYPART_MAPPER, default="N/A")
        .fill_null("Not available")
        .alias("first_touch_bodypart")
        ).drop("it_initialbodytype")


def reclassify_linesbrokentype(df_in : pl.DataFrame) -> pl.DataFrame:
    return df_in.with_columns(
        pl.col("pe_linesbrokentype")
        .replace_strict(LINESBROKEN_MAPPER, default = "None")
        .fill_null("None")
    )


def rename_classes_setpieces(df_in : pl.DataFrame) -> pl.DataFrame:
    return df_in.with_columns(
        pl.col("ge_setpiecetype")
        .replace_strict(SETPIECE_MAPPER, default="N/A")
        .fill_null("Not available")
    )

# Identify possessions for teams & players
def create_team_possession_flag(df_in: pl.DataFrame) -> pl.DataFrame:
    """Flag rows where a new team possession begins.

    Identify possession changes independently within each game. A team
    change, dead-ball set piece, or game-pause event starts a possession.
    Null values do not trigger possession starts. The first row of every
    game is always flagged explicitly.

    Args:
        df_in: Event data containing ``ge_teamid``, ``gameid``,
            ``ge_setpiecetype``, and ``ge_gameeventtype``.

    Returns:
        Event data with a Boolean ``team_possession_start`` column.
        Never a null
    """
    team_changed = (
        pl.col("ge_teamid")
        != pl.col("ge_teamid").shift().over("gameid")
    )
    dead_ball_started = pl.col("ge_setpiecetype").is_in(
        DEAD_BALL_SET_PIECE_TYPES
    )
    game_paused = pl.col("ge_gameeventtype").is_in(PAUSE_EVENTS)
    first_event = (pl.col("ge_gameeventtype")
                   .is_in(TRANSITION_EVENTS[0:4])
    )
    
    possession_started = first_event | (
        team_changed
        | dead_ball_started
        | game_paused
    ).fill_null(False)

    return df_in.with_columns(
        possession_started.alias("team_possession_start")
    ).filter(
        ~pl.col("ge_gameeventtype").is_in(PAUSE_EVENTS)
    )


def create_team_possession_id(df_in: pl.DataFrame) -> pl.DataFrame:
    """Create match-level and team-level possession identifiers.

    Convert possession-start flags into a cumulative possession number,
    then combine the game, team, and possession values into a unique
    identifier.

    Args:
        df_in: Event data containing ``team_possession_start``,
            ``gameid``, and ``ge_teamname``.

    Returns:
        Event data with ``match_possession_id`` and
        ``match_team_possession_id`` columns.
    """
    possession_data = df_in.with_columns(
        pl.col("team_possession_start")
        .fill_null(False)
        .cum_sum()
        .over("gameid")
        .alias("match_possession_id")
    )

    #FIXME: Exlcude the team_possession_start flag
    # return possession_data.select(
    #     pl.exclude("team_possession_start"),
    #     pl.concat_str(
    #         ["gameid", "ge_teamname", "match_possession_id"],
    #         separator="_",
    #     ).alias("match_team_possession_id"),
    # )

    return possession_data.with_columns(
        pl.concat_str(
           ["gameid", "ge_teamname", "match_possession_id"],
            separator="_",
        ).alias("match_team_possession_id") 
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
    previous_known_player = (
        pl.col("ge_playerid")
        # Uncomment the following line only if you want to make the 
        # assumption that a missing id between the ids of the same 
        # player does not break possession between events
        # .forward_fill() 
        .shift()
        .over("gameid")
    )
    player_changed = (
        pl.col("ge_playerid").is_not_null()
        & pl.col("ge_playerid").ne_missing(previous_known_player)
    )
    team_possession_changed = (
        pl.col("match_team_possession_id")
        .ne_missing(
            pl.col("match_team_possession_id").shift().over("gameid")
        )
    )

    player_possession_index = (
        (player_changed | team_possession_changed)
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

    return create_player_possession_id(
        create_team_possession_id(
            create_team_possession_flag(df_in=df_in)
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

    return (
        df_in.pipe(select_events_columns)
        .pipe(drop_pen_shootouts)
        .pipe(reclassify_ballheight)
        .pipe(reclassify_pressuretype)
        .pipe(reclassify_linesbrokentype)
        .pipe(reclassify_firsttouch)
        .pipe(rename_classes_setpieces)
        .pipe(add_possession_identifiers)
    )


