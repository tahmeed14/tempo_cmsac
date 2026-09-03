from pathlib import Path

from tempoctrl.visualize.possessions import (
    plot_dev_start_frame,
    plot_dev_players_to_pass,
    plot_dev_possession_movement
)

FIGSIZE_FULL = (7.0, 4.5)
FIGSIZE_WIDE = (7.0, 3.5)
FIGSIZE_SQUARE = (5.5, 5.5)
POSS_EXAMPLE = "src/tempoctrl/possession_example.parquet"
FIGURES_PATH = "paper/figures"

def save_quarto_figure(
    fig,
    filename: str,
    output_dir: str = FIGURES_PATH,
    dpi: int = 300,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = output_dir / filename

    fig.savefig(
        stem.with_suffix(".pdf"),
        bbox_inches="tight",
    )

    fig.savefig(
        stem.with_suffix(".png"),
        dpi=dpi,
        bbox_inches="tight",
    )


def possession_example():
    start_frame, start_ax = plot_dev_start_frame(
        data_path=POSS_EXAMPLE,
        game_id=10517,
        possession_ids="10517_Argentina_1531_403",
        frame_id=65972,
        home_team_name="Argentina",
        away_team_name="France",
        home_color="skyblue",
        away_color="darkblue",
        ball_color="white",
        title = "Argentina vs France | Player Possession Start",
        # figsize = FIGSIZE_SQUARE
    )

    pass_fig, pass_ax = plot_dev_players_to_pass(
        data_path=POSS_EXAMPLE,
        game_id=10517,
        possession_ids="10517_Argentina_1531_403",
        start_frame=65972,
        home_team_name="Argentina",
        away_team_name="France",
        home_color="skyblue",
        away_color="darkblue",
        ball_color="white",
        ball_start_color="white",
        ball_end_color="gray",
        start_player_size=55,
        title = "Argentina vs France | Player Attempts Pass"
        # figsize = FIGSIZE_SQUARE
    )

    possession_fig, possession_ax = plot_dev_possession_movement(
        data_path=POSS_EXAMPLE,
        game_id=10517,
        possession_ids="10517_Argentina_1531_403",
        home_team_name="Argentina",
        away_team_name="France",
        home_color="skyblue",
        away_color="darkblue",
        ball_start_color="white",
        ball_end_color="gray",
        ball_trajectory_color="darkorange",
        title = "Argentina vs France | Pass Successful to Teammate"
        # figsize = FIGSIZE_FULL
    )

    save_quarto_figure(start_frame, filename="player_possession_start")
    save_quarto_figure(pass_fig, filename="player_possession_pass_attempt")
    save_quarto_figure(possession_fig, filename="player_possession_pass_success")



def main():
    possession_example()

if __name__ == "__main__":
    main()
