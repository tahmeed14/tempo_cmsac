import polars as pl

import polars as pl

KEEP_COLUMNS = (
    "game_id",
    "player_id",
    "away_players_smooth",
    "home_players_smooth",
    "pitch_third",

)

def calculate_ball_speed_tempo(
    df: pl.LazyFrame,
    type: str,
    frame_rate: float,
) -> pl.LazyFrame:
    """
    Aggregate ball displacement and frame count by team or player possession.

    Parameters
    ----------
    lf : pl.LazyFrame
        Input LazyFrame.

    type : {"team", "player"}
        Determines the possession ID used for grouping:
        - "team"   -> dev_match_team_possession_id
        - "player" -> dev_match_team_player_possession_id

    Returns
    -------
    pl.LazyFrame
        One row per possession with:
        - total_ball_displacement
        - num_frames
        - ball_speed_tempo_{type}
    """

    if type == "team":
        group_col = "dev_match_team_possession_id"
    elif type == "player":
        group_col = "dev_match_team_player_possession_id"
    else:
        raise ValueError("type must be either 'team' or 'player'")

    result = (
        df.group_by(group_col)
        .agg(
            [
                pl.col(col).first().alias(col)
                for col in KEEP_COLUMNS
            ]
            + [
                pl.col("ball_displacement")
                .sum()
                .alias("total_ball_displacement"),

                pl.len().alias("num_frames"),
            ]
        )
        .with_columns(
            (
                pl.col("total_ball_displacement")
                / pl.col("num_frames")
                * frame_rate
            ).alias(f"ball_speed_tempo_{type}")
        )
    )

    return result