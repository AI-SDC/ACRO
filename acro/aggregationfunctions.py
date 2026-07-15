"""ACRO: Aggregation functions."""

# pylint: disable=too-many-lines
from __future__ import annotations

import logging

from pandas import Series

logger = logging.getLogger("acro")
# aggregation function parameters
THRESHOLD: int = 10
SAFE_PRATIO_P: float = 0.1
SAFE_NK_N: int = 2
SAFE_NK_K: float = 0.9
CHECK_MISSING_VALUES: bool = False
ZEROS_ARE_DISCLOSIVE: bool = True

# survival analysis parameters
SURVIVAL_THRESHOLD: int = 10

# def agg_mode(values: Series) -> Series:
#     """Calculate the mode or randomly selects one of the modes from a pandas Series.

#     Parameters
#     ----------
#     values : Series
#         A pandas Series for which to calculate the mode.

#     Returns
#     -------
#     Series
#         The mode. If multiple modes, randomly selects and returns one of the modes.
#     """
#     modes = values.mode()
#     return secrets.choice(modes)

# def agg_negative(vals: Series) -> bool:
#     """Return whether any values are negative.

#     Parameters
#     ----------
#     vals : Series
#         Series to check for negative values.

#     Returns
#     -------
#     bool
#         Whether a negative value was found.
#     """
#     return vals.min() < 0


# def agg_missing(vals: Series) -> bool:
#     """Return whether any values are missing.

#     Parameters
#     ----------
#     vals : Series
#         Series to check for missing values.

#     Returns
#     -------
#     bool
#         Whether a missing value was found.
#     """
#     return vals.isna().sum() != 0


def agg_p_percent(vals: Series) -> bool:
    """Return whether the p percent rule is violated.  # noqa: D212,D213,D413.

    That is, the uncertainty (as a fraction) of the estimate that the second
    highest respondent can make of the highest value. Assuming there are n
    items in the series, they are first sorted in descending order and then we
    calculate the value p = (sum - N-2 highest values)/highest value. If all
    values are 0, returns 1.

    Parameters
    ----------
    vals : Series
        Series to calculate the p percent value.

    Returns
    -------
    bool
        whether the p percent rule is violated.
    """
    assert isinstance(vals, Series), "vals is not a pandas series"
    sorted_vals = vals.sort_values(ascending=False)
    total: float = sorted_vals.sum()
    if total <= 0.0 or vals.size <= 1:
        logger.debug("not calculating ppercent due to small size")
        return bool(ZEROS_ARE_DISCLOSIVE)
    sub_total = total - sorted_vals.iloc[0] - sorted_vals.iloc[1]
    p_val: float = sub_total / sorted_vals.iloc[0] if total > 0 else 1
    return p_val < SAFE_PRATIO_P


def agg_nk(vals: Series) -> bool:
    """
    Return whether the top n items account for more than k percent of the total.

    Parameters
    ----------
    vals : Series
        Series to calculate the nk value.

    Returns
    -------
    bool
        Whether the nk rule is violated.
        
    """
    total: float = vals.sum()
    if total > 0:
        sorted_vals = vals.sort_values(ascending=False)
        n_total = sorted_vals.iloc[0:SAFE_NK_N].sum()
        return (n_total / total) > SAFE_NK_K
    return False


def agg_threshold(vals: Series) -> bool:
    """Return whether the number of contributors is below a threshold.

    Parameters
    ----------
    vals : Series
        Series to calculate the p percent value.

    Returns
    -------
    bool
        Whether the threshold rule is violated.

    """
    return vals.count() < THRESHOLD


# def agg_values_are_same(vals: Series) -> bool:
#     """Return whether all observations having the same value.

#     Parameters
#     ----------
#     vals : Series
#         Series to calculate if all the values are the same.

#     Returns
#     -------
#     bool
#         Whether the values are the same.
#     """
#     # the observations are not the same
#     return vals.nunique(dropna=True) == 1

# def agg_top_n_sum(vals: Series, n: int = 2) -> float:
#     """Return the sum of the top n values in a pandas Series.

#     Parameters
#     ----------
#     vals : Series
#         A pandas Series for which to calculate the sum of the top n values.
#     n : int, optional
#         The number of top values to sum, by default 2.

#     Returns
#     -------
#     float
#         The sum of the top n values in the Series.
#     """
#     return vals.nlargest(n,keep='all')[0:n].sum()
