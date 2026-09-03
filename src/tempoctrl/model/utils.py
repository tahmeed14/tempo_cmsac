"""Utilities for summarizing fitted model posteriors."""

from __future__ import annotations

from typing import Any, Literal

import arviz as az
import pandas as pd
import polars as pl
import xarray as xr

_SAMPLE_DIMS = ("chain", "draw")
_EFFECT_STATISTIC_COLUMNS = (
    "rank",
    "posterior_mean",
    "posterior_sd",
    "hdi_lower",
    "hdi_upper",
    "p_gt_zero",
)


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
        .sort(
            by=["posterior_mean", player_id_column],
            descending=[True, False],
        )
        .with_row_index("rank", offset=1)
    )


def discover_archetypes(
    mu_table: pl.DataFrame,
    shape_table: pl.DataFrame,
    *,
    mu_range: tuple[int, int] | tuple[float, float],
    shape_range: tuple[int, int] | tuple[float, float],
    option: Literal["rank", "value"] = "rank",
    player_id_column: str = "player_id",
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Filter mu and shape player tables independently and jointly.

    ``mu_table`` should be built for ``"1|player_id"`` and ``shape_table``
    for ``"alpha_1|player_id"``. Both range endpoints are inclusive.

    When ``option="rank"``, rank 1 represents the highest posterior mean.
    When ``option="value"``, ranges are applied to ``posterior_mean``.

    Returns the filtered mu table, filtered shape table, and a combined table
    containing only players that satisfy both filters. Posterior fields in the
    combined table are prefixed with ``mu_`` and ``shape_``.
    """
    if option not in {"rank", "value"}:
        raise ValueError("option must be either 'rank' or 'value'.")

    filter_column = "rank" if option == "rank" else "posterior_mean"
    _validate_archetype_table(
        mu_table,
        table_name="mu_table",
        player_id_column=player_id_column,
        filter_column=filter_column,
    )
    _validate_archetype_table(
        shape_table,
        table_name="shape_table",
        player_id_column=player_id_column,
        filter_column=filter_column,
    )
    _validate_archetype_range(mu_range, range_name="mu_range", option=option)
    _validate_archetype_range(
        shape_range,
        range_name="shape_range",
        option=option,
    )

    mu_matches = _filter_archetype_table(mu_table, mu_range, filter_column)
    shape_matches = _filter_archetype_table(
        shape_table,
        shape_range,
        filter_column,
    )

    mu_statistics = [
        column
        for column in _EFFECT_STATISTIC_COLUMNS
        if column in mu_matches.columns
    ]
    shape_statistics = [
        column
        for column in _EFFECT_STATISTIC_COLUMNS
        if column in shape_matches.columns
    ]

    mu_for_join = mu_matches.rename(
        {column: f"mu_{column}" for column in mu_statistics}
    )
    shape_for_join = shape_matches.select(
        player_id_column,
        *shape_statistics,
    ).rename(
        {column: f"shape_{column}" for column in shape_statistics}
    )
    both_matches = mu_for_join.join(
        shape_for_join,
        on=player_id_column,
        how="inner",
    )

    return mu_matches, shape_matches, both_matches


def _validate_archetype_table(
    table: pl.DataFrame,
    *,
    table_name: str,
    player_id_column: str,
    filter_column: str,
) -> None:
    if not isinstance(table, pl.DataFrame):
        raise TypeError(f"{table_name} must be a Polars DataFrame.")

    required_columns = [player_id_column, filter_column]
    missing_columns = [
        column for column in required_columns if column not in table.columns
    ]
    if missing_columns:
        raise KeyError(f"{table_name} is missing required columns: {missing_columns}.")


def _validate_archetype_range(
    value_range: tuple[int, int] | tuple[float, float],
    *,
    range_name: str,
    option: Literal["rank", "value"],
) -> None:
    if not isinstance(value_range, tuple) or len(value_range) != 2:
        raise TypeError(f"{range_name} must be a two-item tuple.")

    lower, upper = value_range
    if option == "rank":
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in value_range
        ):
            raise TypeError(
                f"{range_name} must contain integers when option='rank'."
            )
        if lower < 1:
            raise ValueError(f"{range_name} ranks must be greater than zero.")
    elif any(
        isinstance(value, bool) or not isinstance(value, (int, float))
        for value in value_range
    ):
        raise TypeError(
            f"{range_name} must contain numeric values when option='value'."
        )

    if lower > upper:
        raise ValueError(f"{range_name} lower bound cannot exceed its upper bound.")


def _filter_archetype_table(
    table: pl.DataFrame,
    value_range: tuple[int, int] | tuple[float, float],
    filter_column: str,
) -> pl.DataFrame:
    lower, upper = value_range
    return table.filter(
        pl.col(filter_column).is_between(lower, upper, closed="both")
    )
