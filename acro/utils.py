"""ACRO: Utility Functions."""

import logging
from collections.abc import Callable
from inspect import FrameInfo, getframeinfo

import numpy as np
import pandas as pd
from pandas import DataFrame, Series
from statsmodels.iolib.table import SimpleTable

logger = logging.getLogger("acro")


AGGFUNC: dict[str, Callable] = {
    "mean": np.mean,
    "median": np.median,
    "sum": np.sum,
    "std": np.std,
    "freq": np.size,
}

# aggregation function parameters
THRESHOLD: int = 10
SAFE_PRATIO_P: float = 0.1
SAFE_NK_N: int = 2
SAFE_NK_K: float = 0.9
CHECK_MISSING_VALUES: bool = False


def get_command(default: str, stack_list: list[FrameInfo]) -> str:
    """Returns the calling source line as a string.

    Parameters
    ----------
    default : str
        Default string to return if unable to extract the stack.
    stack_list : list[tuple]
         A list of frame records for the caller's stack. The first entry in the
         returned list represents the caller; the last entry represents the
         outermost call on the stack.

    Returns
    -------
    str
        The calling source line.
    """
    command: str = default
    if len(stack_list) > 1:
        code = getframeinfo(stack_list[1][0]).code_context
        if code is not None:
            command = "\n".join(code).strip()
    logger.debug("command: %s", command)
    return command


def get_summary_dataframes(results: list[SimpleTable]) -> list[DataFrame]:
    """Converts a list of SimpleTable objects to a list of DataFrame objects.

    Parameters
    ----------
    results : list[SimpleTable]
        Results from fitting statsmodel.

    Returns
    -------
    list[DataFrame]
        List of DataFrame objects.
    """
    tables: list[DataFrame] = []
    for table in results:
        table_df = pd.read_html(table.as_html(), header=0, index_col=0)[0]
        tables.append(table_df)
    return tables


def agg_threshold(vals: Series) -> bool:
    """Aggregation function that returns whether the number of contributors is
    below a threshold.

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


def agg_negative(vals: Series) -> bool:
    """Aggregation function that returns whether any values are negative.

    Parameters
    ----------
    vals : Series
        Series to check for negative values.

    Returns
    -------
    bool
        Whether a negative value was found.
    """
    return vals.min() < 0


def agg_missing(vals: Series) -> bool:
    """Aggregation function that returns whether any values are missing.

    Parameters
    ----------
    vals : Series
        Series to check for missing values.

    Returns
    -------
    bool
        Whether a missing value was found.
    """
    return vals.isna().sum() != 0


def agg_p_percent(vals: Series) -> bool:
    """Aggregation function that returns whether the p percent rule is violated.

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
    sorted_vals = vals.sort_values(ascending=False)
    total: float = sorted_vals.sum()
    sub_total = total - sorted_vals.iloc[0] - sorted_vals.iloc[1]
    p_val: float = sub_total / sorted_vals.iloc[0] if total > 0 else 1
    return p_val < SAFE_PRATIO_P


def agg_nk(vals: Series) -> bool:
    """Aggregation function that returns whether the top n items account for
    more than k percent of the total.

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


def apply_suppression(
    table: DataFrame, masks: dict[str, DataFrame]
) -> tuple[DataFrame, DataFrame]:
    """Applies suppression to a table.

    Parameters
    ----------
    table : DataFrame
        Table to apply suppression.
    masks : dict[str, DataFrame]
        Dictionary of tables specifying suppression masks for application.

    Returns
    -------
    DataFrame
        Table to output with any suppression applied.
    DataFrame
        Table with outcomes of suppression checks.
    """
    logger.debug("apply_suppression()")
    safe_df = table.copy()
    outcome_df = DataFrame().reindex_like(table)
    outcome_df.fillna("", inplace=True)
    # don't apply suppression if negatives are present
    if "negative" in masks:
        mask = masks["negative"]
        outcome_df[mask.values] = "negative"
    # don't apply suppression if missing values are present
    elif "missing" in masks:
        mask = masks["missing"]
        outcome_df[mask.values] = "missing"
    # apply suppression masks
    else:
        for name, mask in masks.items():
            try:
                safe_df[mask.values] = np.NaN
                tmp_df = DataFrame().reindex_like(outcome_df)
                tmp_df.fillna("", inplace=True)
                tmp_df[mask.values] = name + "; "
                outcome_df += tmp_df
            except TypeError:
                logger.warning("problem mask %s is not binary", name)
        outcome_df = outcome_df.replace({"": "ok"})
    logger.info("outcome_df:\n%s", outcome_df)
    return safe_df, outcome_df


def get_table_sdc(masks: dict[str, DataFrame], suppress: bool) -> dict:
    """Returns the SDC dictionary using the suppression masks.

    Parameters
    ----------
    masks : dict[str, DataFrame]
        Dictionary of tables specifying suppression masks for application.
    suppress : bool
        Whether suppression has been applied.
    """
    # summary of cells to be suppressed
    sdc: dict = {"summary": {"suppressed": suppress}, "cells": {}}
    sdc["summary"]["negative"] = 0
    sdc["summary"]["missing"] = 0
    sdc["summary"]["threshold"] = 0
    sdc["summary"]["p-ratio"] = 0
    sdc["summary"]["nk-rule"] = 0
    for name, mask in masks.items():
        sdc["summary"][name] = int(mask.to_numpy().sum())
    # positions of cells to be suppressed
    sdc["cells"]["negative"] = []
    sdc["cells"]["missing"] = []
    sdc["cells"]["threshold"] = []
    sdc["cells"]["p-ratio"] = []
    sdc["cells"]["nk-rule"] = []
    for name, mask in masks.items():
        true_positions = np.column_stack(np.where(mask.values))
        for pos in true_positions:
            row_index, col_index = pos
            sdc["cells"][name].append([int(row_index), int(col_index)])
    return sdc


def get_summary(sdc: dict) -> tuple[str, str]:
    """Returns the status and summary of the suppression masks.

    Parameters
    ----------
    sdc : dict
        Properties of the SDC checks.

    Returns
    -------
    str
        Status: {"review", "fail", "pass"}.
    str
        Summary of the suppression masks.
    """
    status: str = "pass"
    summary: str = ""
    sdc_summary = sdc["summary"]
    sup: str = "suppressed" if sdc_summary["suppressed"] else "may need suppressing"
    if sdc_summary["negative"] > 0:
        summary += "negative values found"
        status = "review"
    elif sdc_summary["missing"] > 0:
        summary += "missing values found"
        status = "review"
    else:
        if sdc_summary["threshold"] > 0:
            summary += f"threshold: {sdc_summary['threshold']} cells {sup}; "
            status = "fail"
        if sdc_summary["p-ratio"] > 0:
            summary += f"p-ratio: {sdc_summary['p-ratio']} cells {sup}; "
            status = "fail"
        if sdc_summary["nk-rule"] > 0:
            summary += f"nk-rule: {sdc_summary['nk-rule']} cells {sup}; "
            status = "fail"
    if summary != "":
        summary = f"{status}; {summary}"
    else:
        summary = status
    logger.info("get_summary(): %s", summary)
    return status, summary


def get_aggfunc(aggfunc: str | None) -> Callable | None:
    """Checks whether an aggregation function is allowed and returns the
    appropriate function.

    Parameters
    ----------
    aggfunc : str | None
        Name of the aggregation function to apply.

    Returns
    -------
    Callable | None
        The aggregation function to apply.
    """
    logger.debug("get_aggfunc()")
    func = None
    if aggfunc is not None:
        if not isinstance(aggfunc, str) or aggfunc not in AGGFUNC:
            raise ValueError(f"aggfunc {aggfunc} must be: {', '.join(AGGFUNC.keys())}")
        func = AGGFUNC[aggfunc]
    logger.debug("aggfunc: %s", func)
    return func


def get_aggfuncs(
    aggfuncs: str | list[str] | None,
) -> Callable | list[Callable] | None:
    """Checks whether a list of aggregation functions is allowed and returns
    the appropriate functions.

    Parameters
    ----------
    aggfuncs : str | list[str] | None
        List of names of the aggregation functions to apply.

    Returns
    -------
    Callable | list[Callable] | None
        The aggregation functions to apply.
    """
    logger.debug("get_aggfuncs()")
    if aggfuncs is None:
        logger.debug("aggfuncs: None")
        return None
    if isinstance(aggfuncs, str):
        function = get_aggfunc(aggfuncs)
        logger.debug("aggfuncs: %s", function)
        return function
    if isinstance(aggfuncs, list):
        functions: list[Callable] = []
        for function_name in aggfuncs:
            function = get_aggfunc(function_name)
            if function is not None:
                functions.append(function)
        logger.debug("aggfuncs: %s", functions)
        if len(functions) < 1:
            raise ValueError(f"invalid aggfuncs: {aggfuncs}")
        return functions
    raise ValueError("aggfuncs must be: either str or list[str]")
