"""ACRO: Utility Functions."""

import copy
import json
import logging
from collections.abc import Callable
from inspect import getframeinfo

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
}

# aggregation function parameters
THRESHOLD: int = 10
SAFE_PRATIO_P: float = 0.1
SAFE_NK_N: int = 2
SAFE_NK_K: float = 0.9


def get_command(default: str, stack_list: list[tuple]) -> str:
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


def finalise_json(filename: str, results: dict) -> None:
    """Writes outputs to a JSON file.

    Parameters
    ----------
    filename : str
        Name of the output file.
    results : dict
        Outputs to write.
    """
    # convert dataframes to json
    outputs: dict = copy.deepcopy(results)
    for _, output in outputs.items():
        if output["outcome"] is not None:
            output["outcome"] = output["outcome"].to_json()
        for i, _ in enumerate(output["output"]):
            output["output"][i] = output["output"][i].to_json()
    # write to disk
    with open(filename, "wt", encoding="utf-8") as file:
        json.dump(outputs, file, indent=4, sort_keys=False)


def finalise_excel(filename: str, results: dict) -> None:
    """Writes outputs to an excel spreadsheet.

    Parameters
    ----------
    filename : str
        Name of the output file.
    results : dict
        Outputs to write.
    """
    with pd.ExcelWriter(  # pylint: disable=abstract-class-instantiated
        filename, engine="openpyxl"
    ) as writer:
        # description sheet
        sheet = []
        summary = []
        command = []
        for output_id, output in results.items():
            sheet.append(output_id)
            command.append(output["command"])
            summary.append(output["summary"])
        tmp_df = pd.DataFrame({"Sheet": sheet, "Command": command, "Summary": summary})
        tmp_df.to_excel(writer, sheet_name="description", index=False, startrow=0)
        # individual sheets
        for output_id, output in results.items():
            # command and summary
            start = 0
            tmp_df = pd.DataFrame(
                [output["command"], output["summary"]], index=["Command", "Summary"]
            )
            tmp_df.to_excel(writer, sheet_name=output_id, startrow=start)
            # outcome
            if output["outcome"] is not None:
                output["outcome"].to_excel(writer, sheet_name=output_id, startrow=4)
            # output
            for table in output["output"]:
                start = 1 + writer.sheets[output_id].max_row
                table.to_excel(writer, sheet_name=output_id, startrow=start)


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
    # apply suppression masks
    else:
        for name, mask in masks.items():
            safe_df[mask.values] = np.NaN
            tmp_df = DataFrame().reindex_like(outcome_df)
            tmp_df.fillna("", inplace=True)
            tmp_df[mask.values] = name + "; "
            outcome_df += tmp_df
        outcome_df = outcome_df.replace({"": "ok"})
    logger.info("outcome_df:\n%s", outcome_df)
    return safe_df, outcome_df


def get_summary(masks: dict[str, DataFrame]) -> str:
    """Returns a string summarising the suppression masks.

    Parameters
    ----------
    masks : dict[str, DataFrame]
        Dictionary of tables specifying suppression masks for application.

    Returns
    -------
    str
        Summary of the suppression masks.
    """
    summary: str = ""
    if "negative" in masks:
        summary = "review; negative values found"
    else:
        for name, mask in masks.items():
            n_cells = mask.to_numpy().sum()
            if n_cells > 0:
                summary += f"{name}: {n_cells} cells suppressed; "
        if summary == "":
            summary = "pass"
        else:
            summary = "fail; " + summary
    logger.info("get_summary(): %s", summary)
    return summary


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
            raise ValueError(f"aggfunc must be: {', '.join(AGGFUNC.keys())}")
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
