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
        if not isinstance(aggfunc, str):
            raise ValueError("aggfunc must be a string.")
        if aggfunc not in AGGFUNC:
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


def apply_threshold(data: DataFrame, threshold: int) -> tuple[DataFrame, str]:
    """
    Suppresses numerical values below a given threshold.

    Parameters
    ----------
    data : DataFrame
        DataFrame to apply threshold suppression.
    threshold : int
        Values below this threshold are replaced with n/a.

    Returns
    ----------
    DataFrame
        DataFrame after threshold suppression has been applied.
    str
        Whether suppression has been applied.
    """
    outcome: str = "pass"
    cols: DataFrame = data.select_dtypes(include=["number"]).columns
    mask: DataFrame = data[cols] < threshold
    n_cells: int = mask.sum().sum()
    if n_cells > 0:
        logger.debug("suppressing %d cells where value < threshold", n_cells)
        data[cols] = data[cols].mask(mask, "n/a")
        outcome = "fail; suppression applied"
    return data, outcome


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

    def add_output(self, command: str, outcome: str, output: str) -> None:
        """
        Adds an output to the results dictionary.

        Parameters
        ----------
        command : str
            String representation of the operation performed.
        outcome : str
            Outcome of ACRO checks.
        output : str
            JSON encoded string representation of the result of the operation.
        """
        name: str = f"output_{self.output_id}"
        self.output_id += 1
        self.results[name] = {
            "command": command,
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

        aggfunc = get_aggfunc(aggfunc)

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

        outcome = "pass"
        if aggfunc is None:
            table, outcome = apply_threshold(table, self.config["safe_threshold"])
        self.add_output(command, outcome, table.to_json())
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

        aggfunc = get_aggfuncs(aggfunc)

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

        outcome = "pass"
        if aggfunc is None:
            table, outcome = apply_threshold(table, self.config["safe_threshold"])
        self.add_output(command, outcome, table.to_json())
        return table
