import polars as pl

DEAD_BALL_SET_PIECE_TYPES = ("C", "D", "F", "G", "K", "P", "T")
TRANSITION_EVENTS = ("FIRSTKICKOFF", 
                     "SECONDKICKOFF", 
                     "THIRDKICKOFF", 
                     "FOURTHKICKOFF", 
                     "G", "OTB") # goals and out-of-bounds events

# GAME STATE FEATURES
def create_team_scores(df_in: pl.DataFrame) -> pl.DataFrame:
    """Compute cumulative home and away scores for each event.

    Find the final event of regulation or extra time, remove subsequent
    post-match penalty events, and calculate the running score for both
    teams.

    Args:
        df: Event data containing ``event_number``, ``ge_endtype``, and
            ``ge_outtype``.

    Returns:
        Events through the end of play with cumulative score columns for
        the home and away teams.

    Raises:
        ValueError: If the data does not contain an end-of-play event.
    """
    end_event_number = df_in.select(
        pl.col("event_number")
        .filter(pl.col("ge_endtype") == "G") # "G" end of half/quarter
        .max()
    ).item()

    if end_event_number is None:
        raise ValueError("No end-of-play event was found in the event data.")

    score_expressions = [
        pl.when(pl.col("ge_outtype") == team_code)
        .then(1)
        .otherwise(0)
        .cum_sum()
        .alias(score_column)
        for team_code, score_column in (
            ("H", "home_score"),
            ("A", "away_score"),
        )
    ]

    return df_in.filter(
        pl.col("event_number") <= end_event_number
    ).with_columns(score_expressions)


def create_match_scores(df_in: pl.DataFrame) -> pl.DataFrame:
    """Calculate the game state from the in-possession team's 
    perspective.

    Calculate the goal difference for the in-possession team, then label
    that team as winning, drawing, or losing. Rows without a home-team
    indicator retain null values for both game-state columns.

    Gradient Sports uses homeTeam to specify which team is associated 
    with the possession event. The game-state columns are computed from
    the perspective of the in-possession team, so the home-team 
    indicator is used to determine whether the home or away score should
    be used to calculate the goal difference.

    Args:
        df: Event data containing ``home_score``, ``away_score``, and
            ``ge_hometeam``.

    Returns:
        Event data with ``gamestate_goal_diff`` and ``gamestate``
        columns.
    """
    home_goal_difference = pl.col("home_score") - pl.col("away_score")
    goal_difference = (
        pl.when(pl.col("ge_hometeam"))
        .then(home_goal_difference)
        .when(~pl.col("ge_hometeam"))
        .then(-home_goal_difference)
        .otherwise(None)
    )

    return df_in.with_columns(
        goal_difference.alias("gamestate_goal_diff")
    ).with_columns(
        pl.when(pl.col("gamestate_goal_diff") > 0)
        .then(pl.lit("Winning"))
        .when(pl.col("gamestate_goal_diff") == 0)
        .then(pl.lit("Drawing"))
        .when(pl.col("gamestate_goal_diff") < 0)
        .then(pl.lit("Losing"))
        .otherwise(None)
        .alias("gamestate")
    )


def create_game_state(df_in: pl.DataFrame) -> pl.DataFrame:
    """Add team score and game-state context to an events DataFrame.

    Calls `create_team_scores` and then `create_match_scores` to attach
    running scores and game-state labels to each event.

    Args:
        df_in: Event data game state variables.

    Returns:
        Event data with game state variables added.
    """
    return create_match_scores(create_team_scores(df_in))

# POSSESSION FEATURES
def flag_possession_start(df_in: pl.DataFrame) -> pl.DataFrame:
    """Flag rows where a new team possession begins.

    Identify possession changes caused by a team change, a new game, or
    a dead-ball set piece. Null comparisons are treated as possession
    starts so the first row is always flagged.

    Args:
        df_in: Event data containing ``ge_teamId``, ``gameId``, and
            ``ge_setpieceType``.

    Returns:
        Event data with a Boolean ``team_possession_start`` column.
    """
    team_changed = pl.col("ge_teamId") != pl.col("ge_teamId").shift()
    game_changed = pl.col("gameId") != pl.col("gameId").shift()
    dead_ball_started = pl.col("ge_setpieceType").is_in(
        DEAD_BALL_SET_PIECE_TYPES
    )

    possession_started = team_changed | game_changed | dead_ball_started

    return df_in.with_columns(
        possession_started
        .fill_null(True)
        .alias("team_possession_start")
    )



def event_features(df_in: pl.DataFrame) -> pl.DataFrame:
    return create_game_state(df_in)