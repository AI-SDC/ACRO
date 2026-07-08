"""ACRO Table-Specific Utility Functions."""

# pylint: disable=too-many-lines
from __future__ import annotations

import copy
import logging
from typing import Any

import numpy as np
import pandas as pd
from pandas import DataFrame, Series
from pandas.api.types import CategoricalDtype

from . import utils
from .constants import DIMENSION_URI
from .sdcchecks import ChecksResults
from .tablemodeldetails import TableModelDetails

logger = logging.getLogger("acro")

AGGFUNC_TO_TYPE: dict[str, str] = {
    "count": "FrequencyTable",
    "mode": "Mode",
    "median": "Median",
    "mean": "Mean",
    "std": "StandardDeviation",
    "sum": "Sum",
    "min": "Minimum",
    "max": "Maximum",
    "agg_mode": "ModeCalculation",
}


def axis_to_list(axis: Series | list[Series]) -> list[Series]:
    """Translate axis into standard format.

    Convert variables describing an axis (row/column) into a list
    to simplify code. Wraps the  input inside a list if it   is a single series
    or leaves it unchanged if it is already a list of series

    Parameters
    ----------
    axis : pandas series or list of series

    Returns
    -------
    list [Series]
    """
    if not isinstance(axis, list):
        foo: list = []
        if axis is not None:
            foo.append(axis)
        return foo
    return axis


def drop_duplicate_columns(outcome: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate columns arising from multiple aggregation functions."""
    lowestlevelfound: list[str] = []
    to_drops: list[str] = []
    for thetuple in list(outcome):
        if thetuple[-1] in lowestlevelfound:
            to_drops.append(thetuple)
        else:
            lowestlevelfound.append(thetuple[-1])
    for drop in to_drops:
        outcome = outcome.drop(drop, axis="columns")

    outcome.fillna("", inplace=True)
    return outcome


def collate_risk_assessments(  # noqa: C901
    table: DataFrame, allcheckresults: dict[str, ChecksResults]
) -> DataFrame:
    """Collate the Risk Assessment for a table.

    Parameters
    ----------
    table : DataFrame
        Table to be risk assessed.
    allcheckresults : dict[str, ChecksResults]
        Dictionary of dataclasses specifying individual risk assessments results.

    Returns
    -------
    DataFrame
        Table with collated outcomes of suppression checks.
    """
    outcome_df = DataFrame(index=table.index, columns=table.columns)
    if isinstance(list(outcome_df)[0], tuple):
        outcome_df = drop_duplicate_columns(outcome_df)
    outcome_df.fillna("", inplace=True)
    # logger.info(f"at start outcome_df:\n{outcome_df}")

    checks_seen: list[str] = []
    for _, checkresults in allcheckresults.items():
        masks = checkresults.outcomes
        # report if negatives are present
        if "negative" in masks:
            mask = masks["negative"]
            outcome_df[mask.values] = "negative"
        #   report if missing values are present
        elif "missing" in masks:
            mask = masks["missing"]
            outcome_df[mask.values] = "missing"
        # collate at-risk cells from individual risk masks
        else:
            for name, mask in masks.items():
                if name in checks_seen:
                    continue
                checks_seen.append(name)
                tmp_df = DataFrame(index=outcome_df.index, columns=outcome_df.columns)
                tmp_df.fillna("", inplace=True)
                if not isinstance(mask, DataFrame):
                    continue
                n_diff = outcome_df.columns.nlevels - mask.columns.nlevels
                if n_diff > 0:
                    mask_cols_aligned = []
                    for c in outcome_df.columns:
                        if isinstance(c, tuple):
                            sub_c = c[n_diff:]
                            if len(sub_c) == 1:
                                mask_cols_aligned.append(sub_c[0])
                            else:
                                mask_cols_aligned.append(sub_c)
                        else:
                            mask_cols_aligned.append(c)
                    mask_aligned = DataFrame(
                        index=mask.index, columns=outcome_df.columns
                    )
                    for col_out, col_mask in zip(
                        outcome_df.columns, mask_cols_aligned, strict=False
                    ):
                        if col_mask in mask.columns:
                            mask_aligned[col_out] = mask[col_mask]
                elif n_diff < 0:
                    mask_aligned = mask.droplevel(list(range(-n_diff)), axis=1)
                else:
                    mask_aligned = mask

                shared_index = outcome_df.index.intersection(mask_aligned.index)
                shared_cols = outcome_df.columns.intersection(mask_aligned.columns)
                if shared_index.empty or shared_cols.empty:
                    continue
                mask_trimmed = mask_aligned.reindex(
                    index=shared_index, columns=shared_cols
                )
                mask_trimmed = mask_trimmed.fillna(value=1).astype(bool)
                tmp_df.loc[shared_index, shared_cols] = tmp_df.loc[
                    shared_index, shared_cols
                ].where(~mask_trimmed, other=name + "; ")
                outcome_df += tmp_df

        outcome_df = outcome_df.replace({"": "ok"})
    logger.info("outcome_df:\n%s", utils.prettify_table_string(outcome_df))
    return outcome_df


def get_analysis_summary(sdc: dict[str, Any]) -> tuple[str, str]:
    """Return the status and summary of the suppression masks.

    Parameters
    ----------
    sdc : dict
        Properties of the SDC checks for an analysis.

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
            status = "review" if sdc_summary["suppressed"] else "fail"
        if sdc_summary["p-ratio"] > 0:
            summary += f"p-ratio: {sdc_summary['p-ratio']} cells {sup}; "
            status = "review" if sdc_summary["suppressed"] else "fail"
        if sdc_summary["nk-rule"] > 0:
            summary += f"nk-rule: {sdc_summary['nk-rule']} cells {sup}; "
            status = "review" if sdc_summary["suppressed"] else "fail"
        if sdc_summary["all-values-are-same"] > 0:
            summary += (
                f"all-values-are-same: {sdc_summary['all-values-are-same']} "
                f"cells {sup}; "
            )
            status = "review" if sdc_summary["suppressed"] else "fail"
    if summary != "":
        summary = f"{status}; {summary}"
    else:
        summary = status
    logger.info("get_summary(): %s", summary)
    return status, summary


def get_redacted_table(
    model: TableModelDetails, collated_assessment: DataFrame
) -> DataFrame:
    """Redact table as needed then rereun the table query."""
    args = model.get_crosstab_args()
    kwargs = model.get_crosstab_kwargs()
    variable_metadata = model.variable_metadata
    queries: list[str] = get_queries_from_collated_risk(
        collated_assessment, kwargs["aggfunc"]
    )
    dim_names = model.get_dimension_names()
    # logger.info(f'queries are {queries}')
    relevant_data: DataFrame = get_relevant_dataframe(model)

    redacted_data: DataFrame = get_redacted_data(relevant_data, queries, dim_names)

    # ensure missing categories are present
    for name in list(redacted_data):
        if variable_metadata[name]["type"] == DIMENSION_URI:
            cat_type = CategoricalDtype(
                categories=variable_metadata[name]["categories"],
                ordered=variable_metadata[name]["ordered"],
            )
            redacted_data[name] = redacted_data[name].astype(cat_type)

    newargs = translate_args_to_newdf(args, redacted_data)
    newkwargs: dict[str, Any] = copy.deepcopy(kwargs)
    newkwargs["dropna"] = False
    if isinstance(model.values, pd.Series) and len(model.values) > 0:
        newkwargs["values"] = redacted_data[kwargs["values"].name]
    else:
        newkwargs["values"] = None
    table = pd.crosstab(*newargs, **newkwargs)
    if model.risk_appetite["zeros_are_disclosive"]:
        table.replace({0: np.nan}, inplace=True)

    return table


def get_redacted_pivottable(
    model: TableModelDetails, collated_assessment: DataFrame
) -> DataFrame:
    """Redact table as needed then rereun the table query."""
    # args = model.get_crosstab_args()
    kwargs = model.get_crosstab_kwargs()
    variable_metadata = model.variable_metadata
    queries: list[str] = get_queries_from_collated_risk(
        collated_assessment, kwargs["aggfunc"]
    )
    dim_names = model.get_dimension_names()

    relevant_data: DataFrame = get_relevant_dataframe(model)
    redacted_data: DataFrame = get_redacted_data(relevant_data, queries, dim_names)
    # ensure missing categories are present
    for name in list(redacted_data):
        if variable_metadata[name]["type"] == DIMENSION_URI:
            cat_type = CategoricalDtype(
                categories=variable_metadata[name]["categories"],
                ordered=variable_metadata[name]["ordered"],
            )
            redacted_data[name] = redacted_data[name].astype(cat_type)

    newkwargs: dict[str, Any] = copy.deepcopy(model.kwargs)
    newkwargs["dropna"] = False

    table = pd.pivot_table(redacted_data, **newkwargs)
    if model.risk_appetite["zeros_are_disclosive"]:
        table.replace({0: np.nan}, inplace=True)

    return table


def add_backticks(name: str) -> str:
    """Add backticks to a name if it contains spaces and doesn't have them.

    Parameters
    ----------
    name : str
        The name to add backticks to.

    Returns
    -------
    str
        The name with backticks if needed.
    """
    if isinstance(name, str) and " " in name and not name.startswith("`"):
        return f"`{name}`"
    return name  # pragma: no cover


def _format_label_condition(level_names: list[Any], label: Any) -> list[str]:
    """Format a label into a list of condition strings.

    Parameters
    ----------
    level_names : list
        The names of the levels.
    label : tuple or scalar
        The label value(s).

    Returns
    -------
    list[str]
        List of condition strings for this label.
    """
    parts = []
    if isinstance(label, tuple):
        for level, val in zip(level_names, label, strict=False):
            level = add_backticks(str(level))
            if isinstance(val, (int, float)):
                parts.append(f"({level} == {val})")
            else:
                parts.append(f'({level} == "{val}")')
    else:
        level = add_backticks(str(level_names[0]))
        if isinstance(label, (int, float)):
            parts.append(f"({level} == {label})")
        else:
            parts.append(f'({level} == "{label}")')
    return parts


def get_relevant_dataframe(model: TableModelDetails) -> DataFrame:
    """Extract copy of data relevant to crosstab into new DataFrame.

    Assumes preprocessing has happeneded, so
    index and columns in args should both have been converted into lists of Series

    Parameters
    ----------
    args : list[str|list]
        list of index, columns from call to crosstab function
        should have already been converted to lists
    kwargs : dict
        kwargs for crosstab function

    Returns
    -------
    dataframe containing copies of pandas series need to calculate the  crosstab
    """
    # series_list: list = []
    # if "values" in kwargs.keys() and kwargs["values"] is not None:
    #     series_list.append(kwargs["values"].copy())
    # if not (isinstance(args, tuple) and len(args) == 2):
    #     print(f"args is of type {type(args)} and contents {args}\n")
    #     raise ValueError("list passed as positional args has wrong type or length")
    # for contents in args:
    #     if not isinstance(contents, list):
    #         raise TypeError("index and columns should be lists")
    #     for series in contents:
    #         series_list.append(series.copy())

    # relevant_data = DataFrame(series_list).T
    # relevant_data.reset_index(drop=True, inplace=True)
    # return relevant_data
    if isinstance(model.values, pd.Series) and len(model.values) > 0:
        relevant_data = pd.DataFrame(model.values)
    else:
        relevant_data = pd.DataFrame()
    for series in model.index:
        relevant_data[series.name] = series
    for series in model.columns:
        relevant_data[series.name] = series
    return relevant_data


def translate_args_to_newdf(arguments: tuple, redacted_data: DataFrame) -> list:
    """Translate arguments or keys from one data frame to another.

    Parameters
    ----------
    arguments : list
        list of positional arguments to be translated to a different dataframe
    redacted_data : Dataframe
        the name of the 'host' dataframe

    Returns
    -------
    list
         arguments  translate on to columns with the same name in the host DataFrame
    """
    # todo put in checks to make this robust
    # decide whether to return args i.e. don't do redaction/suppression
    # instead of raising valueerror
    newargs: list = []
    if not (isinstance(arguments, tuple) and len(arguments) == 2):
        raise ValueError("list passed as positional args has wrong type or length")
    for contents in arguments:
        if isinstance(contents, pd.Series):
            newargs.append(redacted_data[contents.name])
        elif isinstance(contents, list):
            newlist: list = []
            for series in contents:
                newlist.append(redacted_data[series.name])
            newargs.append(newlist)
    return newargs


def _get_cell_query(
    mask: DataFrame,
    row_index: int,
    col_index: int,
    index_level_names: list[Any],
    column_level_names: list[Any],
) -> str | None:
    """Generate a query string for a cell if it's marked as true in the mask.

    Parameters
    ----------
    mask : DataFrame
        The suppression mask.
    row_index : int
        Row index.
    col_index : int
        Column index.
    index_level_names : list
        Names of index levels.
    column_level_names : list
        Names of column levels.

    Returns
    -------
    str or None
        Query string if cell is true, None otherwise.
    """
    if not mask.iloc[row_index, col_index]:
        return None

    parts = []
    row_label = mask.index[row_index]
    col_label = mask.columns[col_index]

    parts.extend(_format_label_condition(index_level_names, row_label))
    parts.extend(_format_label_condition(column_level_names, col_label))

    return " & ".join(parts)


def get_queries_from_collated_risk(
    collated_risk: DataFrame, aggfunc: str | None
) -> list[str]:
    """Return a list of the boolean conditions for each true (disclosive) cell in the suppression masks.

    Parameters
    ----------
    masks : dict[str, DataFrame]
        Dictionary of tables specifying suppression masks for application.
    aggfunc : str | None
        The aggregation function

    Returns
    -------
    str
        The boolean conditions for each true (disclosive) cell in the suppression masks.
    """
    true_cell_queries = []
    themask = collated_risk.copy()

    themask = themask.replace({"ok": False})
    themask = themask.mask(themask != False, other=True)
    if aggfunc is not None:
        if themask.columns.nlevels > 1:
            themask = themask.droplevel(0, axis=1)
    index_level_names = themask.index.names
    column_level_names = themask.columns.names
    for col_index, _ in enumerate(themask.columns):
        for row_index, _ in enumerate(themask.index):
            query = _get_cell_query(
                themask, row_index, col_index, index_level_names, column_level_names
            )
            if query is not None:
                true_cell_queries.append(query)
    true_cell_queries = list(set(true_cell_queries))
    return true_cell_queries


def get_redacted_data(
    data: DataFrame, queries: list[str], dimensions: list[str]
) -> DataFrame:
    """Apply set of queries to remove sensitive data from  DataFrame.

    Parameters
    ----------
    data : pandas DataFrame
        the raw data
    queries : list[str]
        a set of queries that define the data in cells marked as being disclosive
    dimensions : list[str]
        the names of the dimensional varaibels - these  are the categorical entities in the queries

    Returns
    -------
    DataFrame
         the data after the sensitive data has been removed
    """
    redacted_data = data.copy()

    # queries are in string form
    oldtypes: dict = {}
    for dimension in dimensions:
        if dimension in list(redacted_data):
            oldtypes[dimension] = redacted_data[dimension].dtype
            # logger.info(f'converting {dimension} from {redacted_data[dimension].dtype} to str')
            redacted_data[dimension] = redacted_data[dimension].astype(str)

    # logger.info(f'now columns are {list(redacted_data)}')
    # for col in redacted_data:
    #     logger.info(f'{col}: {redacted_data[col].unique()}')

    # logger.info(f'queries are:\n{queries}')
    # logger.info(f'initially redacted  data has shape {redacted_data.shape}')

    for query in queries:
        # logger.info(f'applying query{query}')
        redacted_data.query(f"not ({query})", inplace=True)
        # logger.info(f'now redacted data has shape {redacted_data.shape}')

    # logger.info(f'after querying, columns are {list(redacted_data)}')
    # for col in redacted_data:
    #     logger.info(f'{col}: {redacted_data[col].unique()}')

    # reconvert
    for dimension in dimensions:
        if dimension in list(redacted_data):
            redacted_data[dimension] = redacted_data[dimension].astype(
                oldtypes[dimension]
            )

    if not set(data.columns) == set(redacted_data.columns):
        logger.warning("Error created redacted data - unable to apply suppression")
        return data
    return redacted_data


def get_debugging_table_analysis(allchecksresults: dict[str, ChecksResults]) -> str:
    """Get string of status/summary debugging info."""
    thestring = ""
    thestring += "\n====start acro.crosstab print statement====="

    for analysis, checksresults in allchecksresults.items():
        thestring += f"\n====findings for {analysis}====="

        thestring += "\n== statuses==\n"
        thestring += f" {checksresults.overall_status}\n"

        thestring += "\n== summaries==\n"
        thestring += f" {checksresults.summaries}\n"

        thestring += "\n== allmasks==\n"
        for name, mask in checksresults.outcomes.items():
            thestring += f"\nMask for {name}\n"
            thestring += f"{mask}\n"
            # for key, val in mask.items():
            # thestring +=  f"{key} \n{val}\n"

        thestring += "\n== fair_dicts==\n"
        for key, val in checksresults.fair_dict.items():
            if isinstance(val, dict):
                for key2, val2 in val.items():
                    thestring += f" {key2} : {val2}\n"
            else:
                thestring += f" {key} : {val}\n"

    # thestring +=  "\n=== collated masks ===\n"
    # thestring +=  f"{collated_assessment}\n"
    # thestring +=  "====end acro.crosstab print statement=====\n"
    return thestring


def aggfunc_to_strings(aggfunc: Any) -> list[str]:
    """Turn aggfunc into list of strings."""
    analysis_names: list[str] = []

    if aggfunc is None:
        analysis_names.append(AGGFUNC_TO_TYPE.get("count", "missing"))
    if isinstance(aggfunc, str):
        analysis_names.append(AGGFUNC_TO_TYPE.get(aggfunc, "missing"))
    if isinstance(aggfunc, list):
        for i in aggfunc:
            analysis_names.append(AGGFUNC_TO_TYPE.get(i, "missing"))
    return analysis_names


def round_table(table: DataFrame, base: int) -> DataFrame:
    """Round numeric cells to the nearest multiple of ``base`` (NaNs preserved)."""
    logger.debug("round_table(base=%s)", base)
    if base is None or base <= 0:
        return table.copy()
    numeric = table.select_dtypes(include=["number"])
    rounded = (numeric / base).round() * base
    result = table.copy()
    result[numeric.columns] = rounded
    return result


def append_rounded_margins(
    rounded_table: DataFrame,
    aggfunc: Any,
    margins_name: str,
    base: int,
) -> DataFrame:
    """Append row/column/grand-total margins to a pre-rounded table.

    Once cells have been rounded,
    margins are computed by aggregating the rounded cells (so rounded inner
    cells add up to the displayed totals) and then rounded again to ``base``
    so the whole output respects the rounding base.

    Conceptually this is the same as the "synthetic-data" approach Jim
    described - exploding the rounded table into one record per cell and
    re-running ``pd.crosstab(margins=True)`` - but implemented directly on
    the rounded DataFrame to keep it simple. We currently support single-
    level row and column indices; multi-level or list-of-aggfunc tables fall
    back to returning the table without margins.
    """
    aggnames: list = aggfunc_to_strings(aggfunc)
    if len(aggnames) > 1:
        logger.info(
            "Cannot add margins to a rounded table when multiple aggregation "
            "functions were requested; returning the table without margins."
        )
        return rounded_table
    if rounded_table.index.nlevels > 1 or rounded_table.columns.nlevels > 1:
        logger.info(
            "Margin recomputation for hierarchical row/column indexes is not "
            "yet supported under rounding; returning the table without margins."
        )
        return rounded_table

    name = aggnames[0]
    if aggfunc is None or name in (None, "FrequencyTable", "Sum", "ModeCalculation"):
        agg_method = "sum"
    elif name == "Mean":
        agg_method = "mean"
    elif name == "Median":
        agg_method = "median"
    else:
        logger.info(
            "Margin recomputation for aggfunc %r is not supported under "
            "rounding; returning the table without margins.",
            name,
        )
        return rounded_table

    numeric = rounded_table.select_dtypes(include=["number"])
    row_margin = getattr(numeric, agg_method)(axis=1, skipna=True)
    col_margin = getattr(numeric, agg_method)(axis=0, skipna=True)
    grand = float(getattr(numeric.stack(), agg_method)())

    if base and base > 0:
        row_margin = (row_margin / base).round() * base
        col_margin = (col_margin / base).round() * base
        grand = round(grand / base) * base

    table = rounded_table.copy()
    table[margins_name] = row_margin
    new_row = col_margin.reindex(table.columns)
    new_row[margins_name] = grand
    table.loc[margins_name] = new_row
    return table
