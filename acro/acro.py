"""ACRO."""

import json
import logging
import pathlib
from collections.abc import Callable
from inspect import getframeinfo, stack

import numpy as np
import pandas as pd
import yaml
from pandas import DataFrame

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("acro")

AGGFUNC: dict = {
    "mean": np.mean,
    "median": np.median,
    "sum": np.sum,
    "std": np.std,
}


def agg_threshold(vals: pd.Series) -> bool:
    """
    Aggregation function that returns whether the number of contributors is
    below a threshold.

    Parameters
    ----------
    vals : pd.Series
        Series to calculate the p percent value.

    Returns
    ----------
    bool
        Whether the threshold rule is violated.
    """

    threshold: int = 10  # self.config["safe_threshold"]

    count: int = vals.count()
    return count < threshold


def agg_p_percent(vals: pd.Series) -> bool:
    """
    Aggregation function that returns whether the p percent rule is violated.

    That is, the uncertainty (as a fraction) of the estimate that the second
    highest respondent can make of the highest value. Assuming there are n
    items in the series, they are first sorted in descending order and then we
    calculate the value p = (sum - N-2 highest values)/highest value. If all
    values are 0, returns 1.

    Parameters
    ----------
    vals : pd.Series
        Series to calculate the p percent value.

    Returns
    ----------
    bool
        whether the p percent rule is violated.
    """

    safe_pratio_p: float = 0.1  # self.config["safe_pratio_p"]

    sorted_vals = vals.sort_values(ascending=False)
    total: float = sorted_vals.sum()
    sub_total = total - sorted_vals.iloc[0] - sorted_vals.iloc[1]
    p_val: float = sub_total / sorted_vals.iloc[0] if total > 0 else 1
    return p_val < safe_pratio_p


def agg_nk(vals: pd.Series) -> bool:
    """
    Aggregation function that returns whether the top n items account for more
    than k percent of the total.

    Parameters
    ----------
    vals : pd.Series
        Series to calculate the nk value.

    Returns
    ----------
    bool
        Whether the nk rule is violated.
    """

    safe_nk_n: int = 2  # self.config["safe_nk_n"]
    safe_nk_k: float = 0.9  # self.config["safe_nk_k"]

    total: float = vals.sum()
    if total > 0:
        sorted_vals = vals.sort_values(ascending=False)
        n_total = sorted_vals.iloc[0:safe_nk_n].sum()
        return (n_total / total) > safe_nk_k
    return False


def apply_suppression(
    table: pd.DataFrame, masks: dict[pd.DataFrame]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Applies suppression to a table.

    Parameters
    ----------
    table : pd.DataFrame
        Table to apply suppression.
    masks : dict[pd.DataFrame]
        Dictionary of tables specifying suppression masks for application.

    Returns
    ----------
    pd.DataFrame
        Table to output with any suppression applied.
    pd.DataFrame
        Table with outcomes of suppression checks.
    """
    logger.debug("apply_suppression()")
    safe_df = table.copy()
    outcome_df = pd.DataFrame().reindex_like(table)
    outcome_df.fillna("", inplace=True)
    for name, mask in masks.items():
        safe_df[mask] = np.NaN
        outcome_df[mask] += name + "; "
    outcome_df = outcome_df.replace({"": "ok"})
    logger.debug("outcome_df:\n%s", outcome_df)
    return safe_df, outcome_df


def get_summary(masks: dict[pd.DataFrame]) -> str:
    """
    Returns a string summarising the suppression masks.

    Parameters
    ----------
    masks : dict[pd.DataFrame]
        Dictionary of tables specifying suppression masks for application.

    Returns
    ----------
    str
        Summary of the suppression masks.
    """
    summary: str = ""
    for name, mask in masks.items():
        n_cells = mask.to_numpy().sum()
        if n_cells > 0:
            summary += f"{name}: {n_cells} cells suppressed; "
    if summary == "":
        summary = "pass"
    else:
        summary = "fail; " + summary
    logger.debug("get_summary(): %s", summary)
    return summary


def get_aggfunc(aggfunc: str | None) -> Callable | None:
    """
    Checks whether an aggregation function is allowed and returns the
    appropriate function.

    Parameters
    ----------
    aggfunc : str | None
        Name of the aggregation function to apply.

    Returns
    ----------
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


def get_aggfuncs(aggfuncs: str | list[str] | None) -> Callable | list[Callable] | None:
    """
    Checks whether a list of aggregation functions is allowed and returns the
    appropriate functions.

    Parameters
    ----------
    aggfuncs : str | list[str] | None
        List of names of the aggregation functions to apply.

    Returns
    ----------
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


class ACRO:
    """ACRO."""

    def __init__(self, filename: str = "results") -> None:
        """
        Constructs a new ACRO object and reads parameters from config.

        Parameters
        ----------
        filename : str
            Name of the output file.
        """
        self.config: dict = {}
        self.results: dict = {}
        self.filename: str = filename
        self.output_id: int = 0
        path = pathlib.Path(__file__).with_name("default.yaml")
        logger.debug("path: %s", path)
        with open(path, encoding="utf-8") as handle:
            self.config = yaml.load(handle, Loader=yaml.loader.SafeLoader)
        logger.debug("config: %s", self.config)

    def finalise(self) -> dict:
        """
        Creates a results file for checking.

        Returns
        ----------
        dict
            Dictionary representation of the output.
        """
        logger.debug("finalise()")
        json_output: str = json.dumps(self.results, indent=4)
        logger.debug("filename: %s.json", self.filename)
        logger.debug("output: %s", json_output)
        with open(self.filename + ".json", "wt", encoding="utf-8") as file:
            file.write(json_output)
        return self.results

    def add_output(
        self, command: str, summary: str, outcome: pd.DataFrame, output: str
    ) -> None:
        """
        Adds an output to the results dictionary.

        Parameters
        ----------
        command : str
            String representation of the operation performed.
        summary : str
            String summarising the suppression checks.
        outcome : pd.DataFrame
            DataFrame describing the outcome of ACRO checks.
        output : str
            JSON encoded string representation of the result of the operation.
        """
        name: str = f"output_{self.output_id}"
        self.output_id += 1
        self.results[name] = {
            "command": command,
            "summary": summary,
            "outcome": outcome,
            "output": json.loads(output),  # JSON to dict
        }
        logger.debug("add_output(): %s", name)

    def remove_output(self, key: str) -> None:
        """
        Removes an output from the results dictionary.

        Parameters
        ----------
        key : str
            Key specifying which output to remove, e.g., 'output_0'.
        """
        if key in self.results:
            del self.results[key]
            logger.debug("remove_output(): %s removed", key)
        else:
            logger.info("warning: unable to remove %s, key not found", key)

    def get_outputs(self) -> dict:
        """
        Returns the current results dictionary.

        Returns
        -------
        dict
            Dictionary of current outputs and their status.
        """
        logger.debug("get_outputs()")
        return self.results

    def crosstab(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        index,
        columns,
        values=None,
        rownames=None,
        colnames=None,
        aggfunc=None,
        margins: bool = False,
        margins_name: str = "All",
        dropna: bool = True,
        normalize=False,
    ) -> DataFrame:
        """
        Compute a simple cross tabulation of two (or more) factors.
        By default, computes a frequency table of the factors unless an
        array of values and an aggregation function are passed.

        Parameters
        ----------
        index : array-like, Series, or list of arrays/Series
            Values to group by in the rows.
        columns : array-like, Series, or list of arrays/Series
            Values to group by in the columns.
        values : array-like, optional
            Array of values to aggregate according to the factors.
            Requires `aggfunc` be specified.
        rownames : sequence, default None
            If passed, must match number of row arrays passed.
        colnames : sequence, default None
            If passed, must match number of column arrays passed.
        aggfunc : str, optional
            If specified, requires `values` be specified as well.
        margins : bool, default False
            Add row/column margins (subtotals).
        margins_name : str, default 'All'
            Name of the row/column that will contain the totals
            when margins is True.
        dropna : bool, default True
            Do not include columns whose entries are all NaN.
        normalize : bool, {'all', 'index', 'columns'}, or {0,1}, default False
            Normalize by dividing all values by the sum of values.
            - If passed 'all' or `True`, will normalize over all values.
            - If passed 'index' will normalize over each row.
            - If passed 'columns' will normalize over each column.
            - If margins is `True`, will also normalize margin values.

        Returns
        -------
        DataFrame
            Cross tabulation of the data.
        """

        code = getframeinfo(stack()[1][0]).code_context
        command: str = "" if code is None else "\n".join(code).strip()

        logger.debug("crosstab()")
        logger.debug("caller: %s", command)

        aggfunc = get_aggfunc(aggfunc)  # convert string to function

        # requested table
        table: DataFrame = pd.crosstab(
            index,
            columns,
            values,
            rownames,
            colnames,
            aggfunc,
            margins,
            margins_name,
            dropna,
            normalize,
        )

        # suppression masks to apply based on the following checks
        masks: dict[pd.DataFrame] = {}

        # threshold check
        t_values = pd.crosstab(
            index,
            columns,
            None,
            rownames,
            colnames,
            None,
            margins,
            margins_name,
            dropna,
            normalize,
        )
        t_values = t_values < self.config["safe_threshold"]
        masks["threshold"] = t_values

        if aggfunc is not None:
            # p-percent check
            p_values = pd.crosstab(index, columns, values, aggfunc=agg_p_percent)
            masks["p-ratio"] = p_values
            # nk values check
            nk_values = pd.crosstab(index, columns, values, aggfunc=agg_nk)
            masks["nk-rule"] = nk_values

        table, outcome = apply_suppression(table, masks)
        summary = get_summary(masks)
        self.add_output(command, summary, outcome.to_json(), table.to_json())
        return table

    def pivot_table(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        data: DataFrame,
        values=None,
        index=None,
        columns=None,
        aggfunc="mean",
        fill_value=None,
        margins: bool = False,
        dropna: bool = True,
        margins_name: str = "All",
        observed: bool = False,
        sort: bool = True,
    ) -> DataFrame:
        """
        Create a spreadsheet-style pivot table as a DataFrame.

        The levels in the pivot table will be stored in MultiIndex objects
        (hierarchical indexes) on the index and columns of the result
        DataFrame.

        Parameters
        ----------
        data : DataFrame
            The DataFrame to operate on.
        values : column, optional
            Column to aggregate, optional.
        index : column, Grouper, array, or list of the previous
            If an array is passed, it must be the same length as the data. The
            list can contain any of the other types (except list). Keys to
            group by on the pivot table index. If an array is passed, it is
            being used as the same manner as column values.
        columns : column, Grouper, array, or list of the previous
            If an array is passed, it must be the same length as the data. The
            list can contain any of the other types (except list). Keys to
            group by on the pivot table column. If an array is passed, it is
            being used as the same manner as column values.
        aggfunc : str | list[str], default 'mean'
            If list of strings passed, the resulting pivot table will have
            hierarchical columns whose top level are the function names
            (inferred from the function objects themselves).
        fill_value : scalar, default None
            Value to replace missing values with (in the resulting pivot table,
            after aggregation).
        margins : bool, default False
            Add all row / columns (e.g. for subtotal / grand totals).
        dropna : bool, default True
            Do not include columns whose entries are all NaN.
        margins_name : str, default 'All'
            Name of the row / column that will contain the totals when margins
            is True.
        observed : bool, default False
            This only applies if any of the groupers are Categoricals. If True:
            only show observed values for categorical groupers. If False: show
            all values for categorical groupers.
        sort : bool, default True
            Specifies if the result should be sorted.

        Returns
        -------
        DataFrame
            Cross tabulation of the data.
        """

        code = getframeinfo(stack()[1][0]).code_context
        command: str = "" if code is None else "\n".join(code).strip()

        logger.debug("pivot_table()")
        logger.debug("caller: %s", command)

        aggfunc = get_aggfuncs(aggfunc)  # convert string(s) to function(s)
        n_agg: int = 1 if not isinstance(aggfunc, list) else len(aggfunc)

        # requested table
        table: DataFrame = pd.pivot_table(  # pylint: disable=too-many-function-args
            data,
            values,
            index,
            columns,
            aggfunc,
            fill_value,
            margins,
            dropna,
            margins_name,
            observed,
            sort,
        )

        # suppression masks to apply based on the following checks
        masks: dict[pd.DataFrame] = {}

        # threshold check
        agg_check = [agg_threshold] * n_agg if n_agg > 1 else agg_threshold
        t_values = pd.pivot_table(data, values, index, columns, aggfunc=agg_check)
        masks["threshold"] = t_values

        if aggfunc is not None:
            # p-percent check
            agg_check = [agg_p_percent] * n_agg if n_agg > 1 else agg_p_percent
            p_values = pd.pivot_table(data, values, index, columns, aggfunc=agg_check)
            masks["p-ratio"] = p_values
            # nk values check
            agg_check = [agg_nk] * n_agg if n_agg > 1 else agg_nk
            nk_values = pd.pivot_table(data, values, index, columns, aggfunc=agg_check)
            masks["nk-rule"] = nk_values

        table, outcome = apply_suppression(table, masks)
        summary = get_summary(masks)
        self.add_output(command, summary, outcome.to_json(), table.to_json())
        return table
