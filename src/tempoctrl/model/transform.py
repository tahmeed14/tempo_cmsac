import polars as pl

PITCH_THIRD_ORDER = pl.Enum([
    "Middle",
    "Defensive",
    "Attacking",
])

SETPIECE_TYPE_ORDER = pl.Enum([
    "Open Play",
    "Dead Ball",
])

BALL_HEIGHT_ORDER = pl.Enum([
    "Ground",
    "Air"
])

PRESSURE_ORDER = pl.Enum([
    "No Pressure",
    "Pressured (inc. Attempted Pressure)"
])

DEFENDER_CHALLENGES_ORDER = pl.Enum([
    "None",
    "1",
    "2+",
])

POSITION_GROUP_ORDER = pl.Enum([
    "Midfielder",
    "Goalkeeper",
    "Centre Back",
    "Full Back",
    "Winger",
    "Forward",

])

PERIOD_ORDER = pl.Enum(
    ["1", "2", "AET"]
)

#FIXME:
def filter_model_data(df : pl.LazyFrame):
    return df.filter(
        pl.col("ball_speed_tempo_player").is_not_null(),
        pl.col("starting_pitch_third").is_not_null(),
        pl.col("ball_speed_tempo_player") > 0,
        pl.col("ball_speed_tempo_player") < 25,
        pl.col("setpiecetype") != "Drop Kick",
        pl.col("first_touch_ballheight") != "N/A",
    )

def reclassify_setpiece_type(df: pl.LazyFrame | pl.DataFrame
                             ) -> pl.LazyFrame | pl.DataFrame:
    """
    Reclassify setpiece types into broader categories.

    Args:
        df (pl.LazyFrame | pl.DataFrame): Input DataFrame containing the
        'setpiecetype' column.

    Returns:
        pl.LazyFrame | pl.DataFrame: DataFrame with the 'setpiecetype' 
        column reclassified.
    """
    return df.with_columns(
        pl.when(pl.col("setpiecetype") == "Open Play")
        .then(pl.lit("Open Play"))
        .otherwise(pl.lit("Dead Ball"))
        .alias("setpiecetype")
    )

def categorize_defender_num_challenges(
    df: pl.LazyFrame | pl.DataFrame,
) -> pl.LazyFrame | pl.DataFrame:
    return df.with_columns(
        pl.when(pl.col("defender_num_challenges") == 0)
        .then(pl.lit("None"))
        .when(pl.col("defender_num_challenges") == 1)
        .then(pl.lit("1"))
        .when(pl.col("defender_num_challenges") >= 2)
        .then(pl.lit("2+"))
        .otherwise(None)
        .cast(DEFENDER_CHALLENGES_ORDER)
        .alias("defender_num_challenges")
    )

def lock_period_order(df: pl.LazyFrame) -> pl.LazyFrame:
    return df.with_columns(
        pl.col("game_period").cast(PERIOD_ORDER)
    )

def lock_setpiece_type_levels(df: pl.LazyFrame) -> pl.LazyFrame:
    return df.with_columns(
        pl.col("setpiecetype").cast(SETPIECE_TYPE_ORDER)
    )

def lock_ball_height_levels(df: pl.LazyFrame) -> pl.LazyFrame:
    return df.with_columns(
        pl.col("first_touch_ballheight").cast(BALL_HEIGHT_ORDER)
    )

#FIXME: need to rename upstream
def lock_position_group_levels(df: pl.LazyFrame) -> pl.LazyFrame:

    fixme = df.rename({"player_possession_group": "player_position_group"})

    return fixme.with_columns(
        pl.col("player_position_group").cast(POSITION_GROUP_ORDER)
    )

def lock_pitch_third_levels(df: pl.LazyFrame) -> pl.LazyFrame:
    return df.with_columns(
        pl.col("starting_pitch_third").cast(PITCH_THIRD_ORDER)
    )

def lock_pressure_levels(df: pl.LazyFrame) -> pl.LazyFrame:
    return df.with_columns(
        pl.col("first_touch_defender_pressure_type").cast(PRESSURE_ORDER)
    )

def lock_reference_levels(df: pl.LazyFrame) -> pl.LazyFrame:
    return (df
            .pipe(lock_setpiece_type_levels)
            .pipe(lock_pitch_third_levels)
            .pipe(lock_position_group_levels)
            .pipe(lock_ball_height_levels)
            .pipe(lock_pressure_levels)
            )

def transform_model_data(df: pl.LazyFrame) -> pl.LazyFrame:
    return (df
            .pipe(filter_model_data) #FIXME:
            .pipe(reclassify_setpiece_type)
            .pipe(categorize_defender_num_challenges)
            .pipe(lock_reference_levels)
            )
