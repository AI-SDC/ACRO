"""Sdc-specific aggregation functions for use in checks."""

import logging
import secrets
from typing import Any

import pandas as pd

NK_N = 10

logger = logging.getLogger("acro")


def agg_mode(values: pd.Series) -> float:
    """Calculate the mode or randomly selects one of the modes from a pandas Series.

    Parameters
    ----------
    values : Series
        A pandas Series for which to calculate the mode.

    Returns
    -------
    Series
        The mode. If multiple modes, randomly selects and returns one of the modes.
    """
    modes = values.mode()
    return secrets.choice(modes)


def agg_num_negative(vals: pd.Series) -> int:
    """Return whether any values are negative.

    Parameters
    ----------
    vals : Series
        Series to check for negative values.

    Returns
    -------
    bool
        Whether a negative value was found.
    """
    return sum(vals < 0)


def agg_missing(vals: pd.Series) -> bool:
    """Return whether any values are missing.

    Parameters
    ----------
    vals : Series
        Series to check for missing values.

    Returns
    -------
    bool
        Whether a missing value was found.
    """
    logger.info("checking for missing values in series")
    return vals.isna().sum() != 0


def agg_values_are_same(vals: pd.Series) -> bool:
    """Return whether all observations having the same value.

    Parameters
    ----------
    vals : Series
        Series to calculate if all the values are the same.

    Returns
    -------
    bool
        Whether the values are the same.
    """
    # the observations are not the same
    return vals.nunique(dropna=True) == 1


def agg_top_n_sum(vals: pd.Series) -> float:
    """Return the sum of the top n values in a pandas Series.

    Parameters
    ----------
    vals : Series
        A pandas Series for which to calculate the sum of the top n values.
    n : int, optional
        The number of top values to sum, by default 2.

    Returns
    -------
    float
        The sum of the top n values in the Series.
        0 if the series is not numeric
    """
    if vals.dtype.kind in ["i", "u", "f"]:
        return vals.nlargest(NK_N, keep="all")[0:NK_N].sum()
    return 0


def agg_top_2_sum(vals: pd.Series) -> float:
    """Return the sum of the top 2 values in a pandas Series.

    Parameters
    ----------
    vals : Series
        A pandas Series for which to calculate the sum of the top n values.

    Returns
    -------
    float
        The sum of the top n values in the Series.
        0 if the series is not numeric
    """
    if vals.dtype.kind in ["i", "u", "f"]:
        return vals.nlargest(2, keep="all")[0:2].sum()
    logger.info("wrong dtype for nlargest: %s", vals.dtype.kind)
    return 0  # vals.nlargest(n,keep='all')[0:n].sum()


def get_statsmodel_dof(model: Any) -> int:
    """Get model DOF.

    Parameters
    ----------
    model
        A statsmodels model.

    Returns
    -------
    bool
        whether the get action worked
    int
        the residual degrees of freedom.
    """
    if not hasattr(model, "df_resid"):
        raise AttributeError("model does not have df_resid attribute")
    return int(model.df_resid)
