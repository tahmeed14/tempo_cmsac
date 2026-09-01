
import polars as pl

EVENT_FEATURES = (
    "event_number",
    "formattedgameclock",
    "player_id",
    "playername",
    "team_id",
    "teamname",
    "game_state_goal_diff",
    "setpiecetype",
    "first_touch_ballheight",
    "first_touch_bodypart",
    "first_touch_defender_pressure_type",
    # "defender_pressure_type",
    "defender_num_challenges",
    "game_id",
    "game_period",
    "match_team_possession_id",
    "match_team_player_possession_id")

POSSESSION_COLUMNS = (
    "game_id",
    "match_team_possession_id",
    "match_team_player_possession_id",
    "player_possession_sequence_number",
    "elapsed_seconds_team_possession",
    "ball_speed_tempo_player",
    "total_ball_displacement",
    "elapsed_frames",
    "starting_pitch_third",
)

JOIN_KEYS = (
    "game_id",
    "match_team_possession_id",
    "match_team_player_possession_id",
)

MODEL_ORDER = (
    "game_id",
    "player_id",
    "playername",
    "team_id",
    "teamname",
)

DROP_COLUMNS_LOOKUP = (
    "player_id",
    "playername",
    "teamname",
    "team_id",
)

def load_modeldata():
    dir_root = "data/processed/gradient_sports/"

    events_df = (
        pl.scan_parquet(f"{dir_root}events")
        .select(*EVENT_FEATURES)
        .sort(("game_id", "event_number"), nulls_last=True)
        .unique(
            subset=["match_team_player_possession_id"],
            keep="first",
            maintain_order=True,
        )
        )
    
    player_poss_df = (
        pl.scan_parquet(f"data/analysis/player_possessions.parquet")
        .select(*POSSESSION_COLUMNS))

    possession_lookup_df = (
        pl.scan_parquet(f"data/curated/gradient_sports/possession_lookup/match_possession_lookup.parquet")
        .drop(*DROP_COLUMNS_LOOKUP)
    )

    model_df = (
        player_poss_df
        .join(
            events_df,
            on=JOIN_KEYS,
            how="left",
            validate="1:1"
        )
        .join(possession_lookup_df,
              on = "match_team_player_possession_id",
              how = "left",
              validate = "1:1")
    )
    
    print(model_df.collect().shape)

    model_df.sink_parquet(
        "data/analysis/modeldata_v0.parquet",
        compression="zstd"
    )
