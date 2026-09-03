"""Utilities for summarizing fitted model posteriors."""

from __future__ import annotations

from typing import Any

import arviz as az
import pandas as pd
import polars as pl
import xarray as xr

_SAMPLE_DIMS = ("chain", "draw")


def summarize_player_effects(
    idata: Any,
    *,
    variable: str = "alpha_1|player_id",
    hdi_prob: float = 0.94,
    id_column: str = "player_id",
) -> pd.DataFrame:
    """Summarize and rank a player-level posterior effect.

    Parameters
    ----------
    idata
        Inference data returned by ``bambi.Model.fit``.
    variable
        Name of the player-level variable in the posterior group.
    hdi_prob
        Probability mass contained in the highest-density interval.
    id_column
        Name assigned to the player coordinate in the returned table.

    Returns
    -------
    pandas.DataFrame
        One row per player, ordered from the lowest to highest posterior
        mean. The table contains the player identifier, posterior mean,
        posterior standard deviation, HDI bounds, and the posterior
        probability that the effect is greater than zero.
    """
    if not 0 < hdi_prob < 1:
        raise ValueError("hdi_prob must be between 0 and 1.")

    posterior = getattr(idata, "posterior", None)
    if posterior is None:
        raise ValueError("idata must contain a posterior group.")
    if variable not in posterior:
        raise KeyError(f"Posterior variable {variable!r} was not found.")

    player_effect = posterior[variable]
    missing_sample_dims = [
        dim for dim in _SAMPLE_DIMS if dim not in player_effect.dims
    ]
    if missing_sample_dims:
        raise ValueError(
            f"Posterior variable {variable!r} is missing sample dimensions: "
            f"{missing_sample_dims}."
        )

    player_dims = [dim for dim in player_effect.dims if dim not in _SAMPLE_DIMS]
    if len(player_dims) != 1:
        raise ValueError(
            f"Posterior variable {variable!r} must have exactly one player "
            f"dimension; found {player_dims}."
        )
    player_dim = player_dims[0]

    # A stable internal name also makes Dataset-returning ArviZ versions easy
    # to handle without depending on Bambi's variable naming convention.
    player_effect = player_effect.rename("player_effect")
    posterior_mean = player_effect.mean(dim=_SAMPLE_DIMS)
    posterior_sd = player_effect.std(dim=_SAMPLE_DIMS)
    p_gt_zero = (player_effect > 0).mean(dim=_SAMPLE_DIMS)

    interval = az.hdi(
        player_effect,
        prob=hdi_prob,
        dim=_SAMPLE_DIMS,
    )
    if isinstance(interval, xr.Dataset):
        interval = interval["player_effect"]

    bound_dim = next(
        (dim for dim in ("ci_bound", "hdi") if dim in interval.dims),
        None,
    )
    if bound_dim is None or interval.sizes[bound_dim] != 2:
        raise ValueError("ArviZ returned an HDI without two recognizable bounds.")

    ranking = (
        xr.Dataset(
            {
                "posterior_mean": posterior_mean,
                "posterior_sd": posterior_sd,
                "hdi_lower": interval.isel({bound_dim: 0}, drop=True),
                "hdi_upper": interval.isel({bound_dim: 1}, drop=True),
                "p_gt_zero": p_gt_zero,
            }
        )
        .to_dataframe()
        .reset_index()
        .rename(columns={player_dim: id_column})
        .sort_values("posterior_mean", ignore_index=True)
    )

    return ranking


def build_player_effects_table(
    idata: Any,
    model_df: pl.DataFrame | pl.LazyFrame,
    *,
    variable: str = "alpha_1|player_id",
    hdi_prob: float = 0.94,
    player_id_column: str = "player_id",
    player_name_column: str = "playername",
    team_name_column: str = "teamname",
) -> pl.DataFrame:
    """Build a player-level posterior table for downstream exploration.

    The posterior summaries are enriched with the player name, team name,
    and number of rows contributed by that player to the curated model data.
    All posterior players are retained, even if their metadata is missing.

    Parameters
    ----------
    idata
        Inference data returned by ``bambi.Model.fit``.
    model_df
        Curated Polars data frame used to fit the Bambi model.
    variable
        Name of the player-level variable in the posterior group.
    hdi_prob
        Probability mass contained in the highest-density interval.
    player_id_column, player_name_column, team_name_column
        Column names used for player metadata in ``model_df``.

    Returns
    -------
    polars.DataFrame
        Player posterior statistics, metadata, and model-row counts, ordered
        from the lowest to highest posterior mean.
    """
    if isinstance(model_df, pl.LazyFrame):
        model_df = model_df.collect()
    if not isinstance(model_df, pl.DataFrame):
        raise TypeError("model_df must be a Polars DataFrame or LazyFrame.")

    metadata_columns = [
        player_id_column,
        player_name_column,
        team_name_column,
    ]
    missing_columns = [
        column for column in metadata_columns if column not in model_df.columns
    ]
    if missing_columns:
        raise KeyError(f"model_df is missing required columns: {missing_columns}.")

    ranking = pl.from_pandas(
        summarize_player_effects(
            idata,
            variable=variable,
            hdi_prob=hdi_prob,
            id_column=player_id_column,
        )
    )
    player_counts = model_df.group_by(metadata_columns).len(name="count")

    # Bambi/xarray coordinates and curated Polars columns can use different
    # integer widths. Match the curated data before joining.
    player_id_dtype = player_counts.schema[player_id_column]
    ranking = ranking.with_columns(
        pl.col(player_id_column).cast(player_id_dtype)
    )

    return (
        ranking.join(
            player_counts,
            on=player_id_column,
            how="left",
        )
        .sort("posterior_mean")
    )
