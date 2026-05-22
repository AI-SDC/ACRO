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
from .checks import ChecksResults
from .constants import DIMENSION_URI, MEASURE_URI

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
        foo.append(axis)
        return foo
    return axis


def collate_risk_assessments(
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
    # drop column repetitions for multiple aggregation functions
    lowestlevelfound = []
    to_drops = []
    for thetuple in list(outcome_df):
        if thetuple[-1] in lowestlevelfound:
            to_drops.append(thetuple)
        else:
            lowestlevelfound.append(thetuple[-1])
    for drop in to_drops:
        outcome_df = outcome_df.drop(drop, axis="columns")

    outcome_df.fillna("", inplace=True)

    checks_seen: list[str] = []
    for analysis, checkresults in allcheckresults.items():
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
                try:
                    tmp_df = DataFrame(
                        index=outcome_df.index, columns=outcome_df.columns
                    )
                    tmp_df.fillna("", inplace=True)
                    tmp_df[mask.values] = name + "; "
                    outcome_df += tmp_df
                except TypeError:
                    logger.warning("problem mask %s is not binary", name)
                except ValueError as error:  # pragma: no cover
                    error_message = (
                        f"An error occurred with the following details"
                        f":\n Name: {name}\n "
                        f"Mask of size {mask.shape}"
                        f"table of shape {table.shape}"
                    )
                    raise ValueError(error_message) from error

        outcome_df = outcome_df.replace({"": "ok"})
    logger.info("outcome_df:\n%s", utils.prettify_table_string(outcome_df))
    return outcome_df


def get_axis_metadata(axis, where: str) -> dict:
    """Get  metadata for categorical variables describing an axis.

    Cycle through the categorical variables that define an axis
    and construct a meta data dictionary describing them

    Parameters
    ----------
    axis : list[pd.Series]
        list of series defining a dimension in an analysis
    where : str
        axis reference i.e. "rows" or "columns"

    Returns
    -------
    dict
        one entry for item in list provided
        key is name of series
        dict of values describe location, type, categories present
    """
    metadata: dict[str, dict] = {}
    for idx, dimension in enumerate(axis):
        entry: dict = {}
        if not isinstance(dimension, Series):
            logger.info(
                "unable to construct meta data for "
                " component of %s that is not a pandas series",
                where,
            )
        else:
            name = dimension.name
            cat_type = utils.get_catdtype(dimension)
            metadata[name] = {
                "location": where,
                "sequence_id": idx,
                "dtype": str(cat_type.categories.dtype),
                "type": DIMENSION_URI,
                "dependent": False,
                "categories": list(cat_type.categories),
                "ordered": cat_type.ordered,
            }
    return metadata


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


def get_redacted_table(model: dict, collated_assessment: DataFrame) -> DataFrame:
    """Redact table as needed then rereun the table query."""
    args = model["args"]
    kwargs = model["kwargs"]
    variable_metadata = model["variable_metadata"]
    queries: list[str] = get_queries_from_collated_risk(
        collated_assessment, kwargs["aggfunc"]
    )
    relevant_data: DataFrame = get_relevant_dataframe(args, kwargs, variable_metadata)
    redacted_data: DataFrame = get_redacted_data(relevant_data, queries)
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
    if "values" in kwargs.keys() and kwargs["values"] is not None:
        newkwargs["values"] = redacted_data[kwargs["values"].name]
    table = pd.crosstab(*newargs, **newkwargs)
    if model["risk_appetite"]["zeros_are_disclosive"]:
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


def get_relevant_dataframe(
    args: list, kwargs: dict[str, Any], metadata: dict
) -> DataFrame:
    """Extract copy of data relevant to crosstab into new DataFrame.

    Assumes preprocessing has happenededindex and columns in args should both have been converted into lists of Series

    Parameters
    ----------
    args : list[str|list]
        list of index, columns from call to crosstab function
        should have already been converted to lists
    kwargs : dict
        kwargs for crosstab function
    metadata : dict
        information for creating categorical datatypes so as to preserve possible values

    Returns
    -------
    dataframe containing copies of pandas series need to calculate the  crosstab
    """
    series_list: list = []
    if "values" in kwargs.keys() and kwargs["values"] is not None:
        series_list.append(kwargs["values"].copy())
    if not (isinstance(args, tuple) and len(args) == 2):
        print(f"args is of type {type(args)} and contents {args}\n")
        raise ValueError("list passed as positional args has wrong type or length")
    for contents in args:
        if not isinstance(contents, list):
            raise TypeError("index and columns should be lists")
        for series in contents:
            series_list.append(series.copy())

    relevant_data = DataFrame(series_list).T
    return relevant_data


def translate_args_to_newdf(arguments: list, redacted_data: DataFrame) -> list:
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


def get_redacted_data(data: DataFrame, queries: list[str]) -> DataFrame:
    """Apply set of queries to remove sensitive data from  DataFrame.

    Parameters
    ----------
    data : pandas DataFrame
        the raw data
    queries : list[str]
        a set of queries that define the data in cells marked as being disclosive

    Returns
    -------
    DataFrame
         the data after the sensitive data has been removed
    """
    redacted_data = data.copy()
    # logger.info(f'data has shape {data.shape}')
    for query in queries:
        # logger.info(f'applying query{query}')
        redacted_data.query(f"not ({query})", inplace=True)
        # logger.info(f'now redacted data has shape {redacted_data.shape}')

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


def get_variable_metadata(
    index: list, columns: list, values: Series | None
) -> dict[str, dict]:
    """Create data dictionary.

    TODO
    expand docstring
    """
    # TODO handle arraylike as well as series
    # TODO handle rownames/colnames
    variable_metadata: dict[str, dict] = {}
    variable_metadata.update(get_axis_metadata(index, where="rows"))
    variable_metadata.update(get_axis_metadata(columns, where="columns"))
    if values is not None:
        name = values.name if isinstance(values, Series) else "unknown_measure"
        variable_metadata[name] = {
            "location": "cells",
            "sequence_id": 0,
            "dtype": values[0].dtype,
            "type": MEASURE_URI,
            "dependent": True,
            "categories": [],
        }
    return variable_metadata


def get_variable_type_dict(variable_metadata: dict[str, dict]) -> dict[str, Any]:
    """Get dict listing dependent and independent variables from metadata catalogue.

    Parameters
    ----------
    variable_metadata : dict

    Returns
    -------
    dict
        holding  name of dependent variable and list of independent (exogenous) variables
    """
    mydict: dict[str, Any] = {"dependent": "unknown", "independent": []}
    for varname in variable_metadata.keys():
        if variable_metadata[varname]["dependent"]:
            mydict["dependent"] = varname
        else:
            mydict["independent"].append(varname)

    return mydict


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


def get_modeldict_for_array(thedata: pd.Series, risk_appetite: dict) -> dict:
    """Construct the model dict for an array type analysis.

    Parameters
    ----------
    thedata : pd.Series
        array of values to summarise as counts
    risk_appetite : dict
        statement of TREs risk appetite

    Returns
    -------
    dict in form to support running various checks
    """
    variable_metadata = {thedata.name: {"type": MEASURE_URI, "dependent": True}}
    modeldict: dict[str, Any] = {
        "model_type": "array",
        "data": thedata,
        "variable_metadata": variable_metadata,
        "risk_appetite": risk_appetite,
    }
    return modeldict


def get_modeldict_for_table(args: tuple, kwargs: dict, risk_appetite: dict) -> dict:
    """Construct the model dict for an array type analysis.

    Parameters
    ----------
    args : tuple
        tuple of length 2, contrtns are lists or rows and column series names
    kwargs : dict
        all the other info needed to specify a table
    risk_appetite : dict
        statement of TREs risk appetite

    Returns
    -------
    dict in form to support running various checks
    """
    variable_metadata = get_variable_metadata(args[0], args[1], kwargs["values"])
    # make object containing these that can easily be passed around
    modeldict: dict[str, Any] = {
        "model_type": "table",
        "args": args,
        "kwargs": kwargs,
        "variable_metadata": variable_metadata,
        "risk_appetite": risk_appetite,
    }
    return modeldict
