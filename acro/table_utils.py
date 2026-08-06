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
    to simplify code. Wraps input inside a list if it is a single series
    or leaves it unchanged if it is already a list of series.

    Parameters
    ----------
    axis : Series or list of Series
        Pandas series or list of series describing an axis.

    Returns
    -------
    list
        List of Series objects.
    """
    if not isinstance(axis, list):
        return [axis] if axis is not None else []
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

    outcome = outcome.fillna("")
    return outcome


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
    old = True
    if old:
        if isinstance(list(outcome_df)[0], tuple):
            # outcome_df = drop_duplicate_columns(outcome_df)
            pass
        outcome_df = outcome_df.fillna("")

    else:
        outcome_df = outcome_df.fillna("")

        # if isinstance(table.columns, pd.CategoricalIndex):
        #     logger.debug("categorical index, not dropping columns")
        #     pass
        # elif isinstance(table.columns, pd.MultiIndex):
        #     # logger.debug(f'start of collate_risk_assessments, outcome is\n{outcome_df}\nwhich is a {type(outcome_df)}')
        #     levels = outcome_df.columns.levels
        #     logger.debug(f"got a multiindex: {levels}")

        #     # numcols = len(table.columns) if isinstance(table.columns, list) else 1
        #     # numlevels = len(levels)
        #     # logger.debug(f'columns={table.columns}, numcols={numcols}, numlevels={numlevels}, levels[0]={levels[0]}')
        #     if isinstance(list(outcome_df)[0], tuple):
        #         #outcome_df = drop_duplicate_columns(outcome_df)
        #         pass
        #     outcome_df = outcome_df.fillna("")
        # else:
        #     logger.debug(f"unknown type for table.columns{type(table.columns)}")

    # logger.debug(f'after dropping duplicate columns, outcome is\n{outcome_df}')

    for _, checkresults in allcheckresults.items():
        masks = checkresults.outcomes
        # report if negatives are present
        if "negative" in masks:
            mask = masks["negative"]
            outcome_df[mask.to_numpy()] = "negative"
        #   report if missing values are present
        elif "missing" in masks:
            mask = masks["missing"]
            outcome_df[mask.to_numpy()] = "missing"
        # collate at-risk cells from individual risk masks
        else:
            for name, mask in masks.items():
                logger.debug(f"checks: {name}:\n{mask}")
                # Skip non-DataFrame masks (e.g., numpy arrays)
                if not isinstance(mask, DataFrame):
                    continue

                def string_in_frame(testname: str, df: pd.DataFrame) -> bool:
                    return (
                        df.astype(str)
                        .apply(lambda x: x.str.contains(testname))
                        .any()
                        .any()
                    )

                if string_in_frame(name, outcome_df):
                    logger.debug("found %s already so not repeating it", name)
                    continue
                tmp_df = DataFrame(index=outcome_df.index, columns=outcome_df.columns)
                tmp_df = tmp_df.fillna("")

                # Align mask to outcome_df structure
                mask_aligned = _align_mask_to_outcome(mask, outcome_df)
                logger.debug(f"aligned mask:\n{mask_aligned}")

                # Check for non-empty intersections
                shared_index = outcome_df.index.intersection(mask_aligned.index)
                shared_cols = outcome_df.columns.intersection(mask_aligned.columns)
                if shared_index.empty or shared_cols.empty:
                    logger.debug(
                        "no intersections shared_index=%s shared_cols=%s",
                        shared_index,
                        shared_cols,
                    )
                    logger.debug(
                        "outcome_df cols= %s mask_aligned cols = %s",
                        outcome_df.columns,
                        mask_aligned.columns,
                    )
                    continue

                # Apply mask to tmp_df
                mask_trimmed = mask_aligned.reindex(
                    index=shared_index, columns=shared_cols
                )
                mask_trimmed = mask_trimmed.fillna(value=1).astype(bool)
                tmp_df.loc[shared_index, shared_cols] = tmp_df.loc[
                    shared_index, shared_cols
                ].where(~mask_trimmed, other=name + "; ")
                outcome_df += tmp_df
                logger.debug(f"outcome with mask for {name} added:\n{outcome_df}")

        outcome_df = outcome_df.replace({"": "ok"})
    logger.info("outcome_df:\n%s", utils.prettify_table_string(outcome_df))
    return outcome_df


def _align_mask_to_outcome(mask: DataFrame, outcome_df: DataFrame) -> DataFrame:
    """Align a check outcome mask to the column structure of the outcome DataFrame.

    Parameters
    ----------
    mask : DataFrame
        Suppression mask to align.
    outcome_df : DataFrame
        The target outcome DataFrame whose column structure is used for alignment.

    Returns
    -------
    DataFrame
        Aligned mask with columns matching outcome_df structure.
    """
    n_diff = outcome_df.columns.nlevels - mask.columns.nlevels
    if n_diff > 0:
        # Outcome has more column levels than mask - extract relevant level(s) from outcome columns
        mask_cols_aligned = []
        for c in outcome_df.columns:
            if isinstance(c, tuple):
                sub_c = c[n_diff:]
                # Append single column name or tuple of remaining levels
                mask_cols_aligned.append(sub_c[0] if len(sub_c) == 1 else sub_c)
            else:
                mask_cols_aligned.append(c)

        # Create aligned mask with outcome's column structure
        mask_aligned = DataFrame(index=mask.index, columns=outcome_df.columns)
        for col_out, col_mask in zip(
            outcome_df.columns, mask_cols_aligned, strict=False
        ):
            if col_mask in mask.columns:
                mask_aligned[col_out] = mask[col_mask]
        return mask_aligned

    # Outcome has fewer or equal column levels than mask
    if n_diff < 0:
        return mask.droplevel(list(range(-n_diff)), axis=1)
    return mask


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
    summary = f"{status}; {summary}" if summary else status
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
    logger.debug(f"queries are {queries}")
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
        table = table.replace({0: np.nan})

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
    # logger.debug(f'newkwargs are {newkwargs}')
    # added for testing
    if newkwargs.get("index") is None:
        index_names = []
        for series in model.index:
            index_names.append(series.name)
        newkwargs["index"] = index_names
    if newkwargs.get("columns") is None:
        column_names = []
        if len(model.columns) > 0:
            for series in model.columns:
                column_names.append(series.name)
        newkwargs["columns"] = column_names
    # line below assumes only one values series which may get expanded later
    if newkwargs.get("values") is None:
        values_names = []
        values_names = (
            model.values[0].name
            if isinstance(model.values, list)
            else model.values.name
        )
        newkwargs["values"] = values_names
    table = pd.pivot_table(redacted_data, **newkwargs)
    if model.risk_appetite["zeros_are_disclosive"]:
        table = table.replace({0: np.nan})

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
        for orig_level_name, val in zip(level_names, label, strict=False):
            level_name = add_backticks(str(orig_level_name))
            if isinstance(val, int | float):
                parts.append(f"({level_name} == {val})")
            else:
                parts.append(f'({level_name} == "{val}")')
    else:
        level = add_backticks(str(level_names[0]))
        if isinstance(label, int | float):
            parts.append(f"({level} == {label})")
        else:
            parts.append(f'({level} == "{label}")')
    return parts


def get_relevant_dataframe(model: TableModelDetails) -> DataFrame:
    """Extract copy of data relevant to crosstab into new DataFrame.

    Assumes preprocessing has happened, so index and columns in model
    should both have been converted into lists of Series.

    Parameters
    ----------
    model : TableModelDetails
        The table model details object containing index, columns, and values.

    Returns
    -------
    DataFrame
        DataFrame containing copies of pandas series needed to calculate the crosstab.
    """
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
        msg = "list passed as positional args has wrong type or length"
        raise ValueError(msg)
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
    logger.debug(
        "type column_level_names =%s,len=%s type content=%s",
        type(column_level_names),
        len(column_level_names),
        type(column_level_names[0]),
    )

    parts.extend(_format_label_condition(index_level_names, row_label))
    if len(column_level_names) == 1 and column_level_names[0] is None:
        joined = "".join(parts)
        logger.debug("joined is %s", joined)
        return joined
    parts.extend(_format_label_condition(column_level_names, col_label))
    joined = " & ".join(parts)
    logger.debug("parts is %s", joined)
    return joined


def get_queries_from_collated_risk(
    collated_risk: DataFrame, aggfunc: str | None
) -> list[str]:
    """Return a list of the boolean conditions for each true (disclosive) cell in the suppression masks.

    Parameters
    ----------
    collated_risk : DataFrame
        DataFrame with collated risk assessment outcomes per cell.
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
    themask = themask.mask(themask != False, other=True)  # noqa: E712
    # get rid of top level of multIndexer for columns IF its just the agg func
    if aggfunc is not None and themask.columns.nlevels > 1:
        # delete the top level if it is just agg funcs
        level0names = set(themask.columns.get_level_values(0).copy())
        # logger.debug(f'l0names is a {type(level0names)} = {level0names}')
        level0names.discard("All")
        # logger.debug(f'l0names is a {type(level0names)} = {level0names}')
        # logger.debug(f'affunc is a {type(aggfunc)}={aggfunc}')
        if isinstance(aggfunc, str) and aggfunc in level0names:
            themask = themask.droplevel(0, axis=1)
        if isinstance(aggfunc, list) and set(aggfunc) == level0names:
            themask = themask.droplevel(0, axis=1)

    index_level_names = themask.index.names
    column_level_names = themask.columns.names
    for col_index, _ in enumerate(themask.columns):
        for row_index, _ in enumerate(themask.index):
            query = _get_cell_query(
                themask, row_index, col_index, index_level_names, column_level_names
            )
            if query is not None:
                logger.debug("new query %s", query)
                true_cell_queries.append(query)
            else:
                logger.debug("got None query")
    true_cell_queries = list(set(true_cell_queries))
    return true_cell_queries


def get_redacted_data(
    data: DataFrame, queries: list[str], dimensions: list[str]
) -> DataFrame:
    """Apply set of queries to remove sensitive data from DataFrame.

    Parameters
    ----------
    data : pandas DataFrame
        the raw data
    queries : list[str]
        a set of queries that define the data in cells marked as being disclosive
    dimensions : list[str]
        the names of the dimensional variablss - these  are the categorical entities in the queries

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
            # logger.debug(
            #    f"converting {dimension} from {redacted_data[dimension].dtype} to str"
            # )
            redacted_data[dimension] = redacted_data[dimension].astype(str)

    # logger.debug(f'now columns are {list(redacted_data)}')
    # for col in redacted_data:
    #     logger.debug(f'{col}: {redacted_data[col].unique()}')

    logger.debug(f"in get_redacted_data: queries are:\n{queries}")
    logger.debug(f"initially redacted  data has shape {redacted_data.shape}")

    for query in queries:
        logger.debug(f"applying query{query}")
        redacted_data = redacted_data.query(f"not ({query})")
        logger.debug(f"now redacted data has shape {redacted_data.shape}")

    # logger.debug(f'after querying, columns are {list(redacted_data)}')
    # for col in redacted_data:
    #    logger.debug(f'{col}: {redacted_data[col].dtype} ;  uniques {redacted_data[col].unique()}')
    # reconvert dimensions to original data types
    for dimension in dimensions:
        if dimension in list(redacted_data):
            ## be mindful of where str 'False' gets converted to bool True
            if oldtypes[dimension] == bool:  # noqa:E721
                # logger.debug('mapping true false  from string to bool')
                redacted_data[dimension] = redacted_data[dimension].map(
                    {"True": True, "False": False}
                )
            redacted_data[dimension] = redacted_data[dimension].astype(
                oldtypes[dimension]
            )
    # logger.debug(f'after astype() operation , columns are {list(redacted_data)}')
    # for col in redacted_data:
    #    logger.debug(f'{col}: {redacted_data[col].dtype} ; {redacted_data[col].unique()}')
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


def round_table(table: DataFrame, base: int | None) -> DataFrame:
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
