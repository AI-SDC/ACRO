"""ACRO: Automatic Checking of Research Outputs."""

import json
import logging
import os
import pathlib
import warnings
from collections.abc import Callable
from inspect import getframeinfo, stack

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yaml
from pandas import DataFrame
from statsmodels.discrete.discrete_model import BinaryResultsWrapper
from statsmodels.iolib.table import SimpleTable
from statsmodels.regression.linear_model import RegressionResultsWrapper

logging.basicConfig(level=logging.DEBUG)
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


def _get_summary_json(results: list[SimpleTable]) -> str:
    """
    Returns a JSON encoded string of the results summary tables.

    Parameters
    ----------
    results : list[statsmodels.iolib.table.SimpleTable]
        Results from fitting statsmodel.

    Returns
    ----------
    str
        JSON encoded string representation of the results tables.
    """
    tables: dict[str, str] = {}
    for i, table in enumerate(results):
        name = f"table_{i}"
        table_df = pd.read_html(table.as_html(), header=0, index_col=0)[0]
        tables[name] = table_df.to_json()
    return json.dumps(tables, indent=4)


def _agg_threshold(vals: pd.Series) -> bool:
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
    return vals.count() < THRESHOLD


def _agg_p_percent(vals: pd.Series) -> bool:
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
    sorted_vals = vals.sort_values(ascending=False)
    total: float = sorted_vals.sum()
    sub_total = total - sorted_vals.iloc[0] - sorted_vals.iloc[1]
    p_val: float = sub_total / sorted_vals.iloc[0] if total > 0 else 1
    return p_val < SAFE_PRATIO_P


def _agg_nk(vals: pd.Series) -> bool:
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
    total: float = vals.sum()
    if total > 0:
        sorted_vals = vals.sort_values(ascending=False)
        n_total = sorted_vals.iloc[0:SAFE_NK_N].sum()
        return (n_total / total) > SAFE_NK_K
    return False


def _apply_suppression(
    table: pd.DataFrame, masks: dict[str, pd.DataFrame]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Applies suppression to a table.

    Parameters
    ----------
    table : pd.DataFrame
        Table to apply suppression.

    masks : dict[str, pd.DataFrame]
        Dictionary of tables specifying suppression masks for application.

    Returns
    ----------
    pd.DataFrame
        Table to output with any suppression applied.

    pd.DataFrame
        Table with outcomes of suppression checks.
    """
    logger.debug("_apply_suppression()")
    safe_df = table.copy()
    outcome_df = pd.DataFrame().reindex_like(table)
    outcome_df.fillna("", inplace=True)
    for name, mask in masks.items():
        safe_df[mask] = np.NaN
        outcome_df[mask] += name + "; "
    outcome_df = outcome_df.replace({"": "ok"})
    logger.debug("outcome_df:\n%s", outcome_df)
    return safe_df, outcome_df


def _get_summary(masks: dict[str, pd.DataFrame]) -> str:
    """
    Returns a string summarising the suppression masks.

    Parameters
    ----------
    masks : dict[str, pd.DataFrame]
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
    logger.debug("_get_summary(): %s", summary)
    return summary


def _get_aggfunc(aggfunc: str | None) -> Callable | None:
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
    logger.debug("_get_aggfunc()")
    func = None
    if aggfunc is not None:
        if not isinstance(aggfunc, str) or aggfunc not in AGGFUNC:
            raise ValueError(f"aggfunc must be: {', '.join(AGGFUNC.keys())}")
        func = AGGFUNC[aggfunc]
    logger.debug("aggfunc: %s", func)
    return func


def _get_aggfuncs(
    aggfuncs: str | list[str] | None,
) -> Callable | list[Callable] | None:
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
    logger.debug("_get_aggfuncs()")
    if aggfuncs is None:
        logger.debug("aggfuncs: None")
        return None
    if isinstance(aggfuncs, str):
        function = _get_aggfunc(aggfuncs)
        logger.debug("aggfuncs: %s", function)
        return function
    if isinstance(aggfuncs, list):
        functions: list[Callable] = []
        for function_name in aggfuncs:
            function = _get_aggfunc(function_name)
            if function is not None:
                functions.append(function)
        logger.debug("aggfuncs: %s", functions)
        if len(functions) < 1:
            raise ValueError(f"invalid aggfuncs: {aggfuncs}")
        return functions
    raise ValueError("aggfuncs must be: either str or list[str]")


class ACRO:
    """
    ACRO: Automatic Checking of Research Outputs.

    Attributes
    ----------

    config : dict
        Safe parameters and their values.

    results : dict
        The current outputs including the results of checks.

    output_id : int
        The next identifier to be assigned to an output.

    Examples
    --------
    >>> acro = ACRO()
    >>> results = acro.ols(y, x)
    >>> results.summary()
    >>> acro.finalise("my_results.json")
    """

    def __init__(self, config: str = "default") -> None:
        """
        Constructs a new ACRO object and reads parameters from config.

        Parameters
        ----------
        config : str
            Name of a yaml configuration file with safe parameters.
        """
        self.config: dict = {}
        self.results: dict = {}
        self.output_id: int = 0
        path = pathlib.Path(__file__).with_name(config + ".yaml")
        logger.debug("path: %s", path)
        with open(path, encoding="utf-8") as handle:
            self.config = yaml.load(handle, Loader=yaml.loader.SafeLoader)
        logger.debug("config: %s", self.config)
        # set globals needed for aggregation functions
        global THRESHOLD  # pylint: disable=global-statement
        global SAFE_PRATIO_P  # pylint: disable=global-statement
        global SAFE_NK_N  # pylint: disable=global-statement
        global SAFE_NK_K  # pylint: disable=global-statement
        THRESHOLD = self.config["safe_threshold"]
        SAFE_PRATIO_P = self.config["safe_pratio_p"]
        SAFE_NK_N = self.config["safe_nk_n"]
        SAFE_NK_K = self.config["safe_nk_k"]

    def finalise(self, filename: str = "results.json") -> dict:
        """
        Creates a results file for checking.

        Returns
        ----------
        dict
            Dictionary representation of the output.
        """
        logger.debug("finalise()")
        logger.debug("filename: %s", filename)
        output: str = ""
        _, extension = os.path.splitext(filename)
        print(extension)
        if extension == ".json":
            output = json.dumps(self.results, indent=4)
            logger.debug("JSON output: %s", output)
        else:
            raise ValueError("Invalid file extension. Options: {json}")
        with open(filename, "wt", encoding="utf-8") as file:
            file.write(output)
        return self.results

    def add_output(self, command: str, summary: str, outcome: str, output: str) -> None:
        """
        Adds an output to the results dictionary.

        Parameters
        ----------
        command : str
            String representation of the operation performed.

        summary : str
            String summarising the suppression checks.

        outcome : str
            JSON encoded string describing the outcome of ACRO checks.

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
            warnings.warn(f"unable to remove {key}, key not found")

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

        aggfunc = _get_aggfunc(aggfunc)  # convert string to function

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
        masks: dict[str, pd.DataFrame] = {}

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
        t_values = t_values < THRESHOLD
        masks["threshold"] = t_values

        if aggfunc is not None:
            # p-percent check
            p_values = pd.crosstab(index, columns, values, aggfunc=_agg_p_percent)
            masks["p-ratio"] = p_values
            # nk values check
            nk_values = pd.crosstab(index, columns, values, aggfunc=_agg_nk)
            masks["nk-rule"] = nk_values

        table, outcome = _apply_suppression(table, masks)
        summary = _get_summary(masks)
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

        aggfunc = _get_aggfuncs(aggfunc)  # convert string(s) to function(s)
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
        masks: dict[str, pd.DataFrame] = {}

        # threshold check
        agg_check = [_agg_threshold] * n_agg if n_agg > 1 else _agg_threshold
        t_values = pd.pivot_table(data, values, index, columns, aggfunc=agg_check)
        masks["threshold"] = t_values

        if aggfunc is not None:
            # p-percent check
            agg_check = [_agg_p_percent] * n_agg if n_agg > 1 else _agg_p_percent
            p_values = pd.pivot_table(data, values, index, columns, aggfunc=agg_check)
            masks["p-ratio"] = p_values
            # nk values check
            agg_check = [_agg_nk] * n_agg if n_agg > 1 else _agg_nk
            nk_values = pd.pivot_table(data, values, index, columns, aggfunc=agg_check)
            masks["nk-rule"] = nk_values

        table, outcome = _apply_suppression(table, masks)
        summary = _get_summary(masks)
        self.add_output(command, summary, outcome.to_json(), table.to_json())
        return table

    def __check_model_dof(self, name: str, model) -> tuple[str, str]:
        """
        Check model DOF.

        Parameters
        ----------
        name : str
            The name of the model.

        model
            A statsmodels model.

        Returns
        -------
        str
            Summary of the check.

        str
            Outcome of the check.
        """
        dof: int = model.df_resid
        threshold: int = self.config["safe_dof_threshold"]
        if dof < threshold:
            summary = "fail"
            outcome = f"fail; dof={dof} < {threshold}"
            warnings.warn(f"Unsafe {name}: {outcome}")
        else:
            summary = "pass"
            outcome = f"pass; dof={dof} >= {threshold}"
        logger.debug("%s() outcome: %s", name, outcome)
        return summary, outcome

    def ols(  # pylint: disable=too-many-locals
        self, endog, exog=None, missing="none", hasconst=None, **kwargs
    ) -> RegressionResultsWrapper:
        """
        Fits Ordinary Least Squares Regression.

        Parameters
        ----------
        endog : array_like
            A 1-d endogenous response variable. The dependent variable.

        exog : array_like
            A nobs x k array where `nobs` is the number of observations and `k`
            is the number of regressors. An intercept is not included by
            default and should be added by the user.

        missing : str
            Available options are 'none', 'drop', and 'raise'. If 'none', no
            nan checking is done. If 'drop', any observations with nans are
            dropped. If 'raise', an error is raised. Default is 'none'.

        hasconst : None or bool
            Indicates whether the RHS includes a user-supplied constant. If
            True, a constant is not checked for and k_constant is set to 1 and
            all result statistics are calculated as if a constant is present.
            If False, a constant is not checked for and k_constant is set to 0.

        **kwargs
            Extra arguments that are used to set model properties when using
            the formula interface.

        Returns
        -------
        statsmodels.regression.linear_model.RegressionResultsWrapper
            Results.
        """
        code = getframeinfo(stack()[1][0]).code_context
        command: str = "" if code is None else "\n".join(code).strip()
        model = sm.OLS(endog, exog=exog, missing=missing, hasconst=hasconst, **kwargs)
        results = model.fit()
        summary, outcome = self.__check_model_dof("ols", model)
        tables: list[SimpleTable] = results.summary().tables
        self.add_output(command, summary, outcome, _get_summary_json(tables))
        return results

    def logit(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        endog,
        exog,
        missing: str | None = None,
        check_rank: bool = True,
    ) -> BinaryResultsWrapper:
        """
        FIts Logit model.

        Parameters
        ----------
        endog : array_like
            A 1-d endogenous response variable. The dependent variable.

        exog : array_like
            A nobs x k array where nobs is the number of observations and k is
            the number of regressors. An intercept is not included by default
            and should be added by the user.

        missing : str | None
            Available options are ‘none’, ‘drop’, and ‘raise’. If ‘none’, no
            nan checking is done. If ‘drop’, any observations with nans are
            dropped. If ‘raise’, an error is raised. Default is ‘none’.

        check_rank : bool
            Check exog rank to determine model degrees of freedom. Default is
            True. Setting to False reduces model initialization time when
            exog.shape[1] is large.

        Returns
        -------
        statsmodels.discrete.discrete_model.BinaryResultsWrapper
            Results.
        """
        code = getframeinfo(stack()[1][0]).code_context
        command: str = "" if code is None else "\n".join(code).strip()
        model = sm.Logit(endog, exog, missing=missing, check_rank=check_rank)
        results = model.fit()
        summary, outcome = self.__check_model_dof("logit", model)
        tables: list[SimpleTable] = results.summary().tables
        self.add_output(command, summary, outcome, _get_summary_json(tables))
        return results

    def probit(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        endog,
        exog,
        missing: str | None = None,
        check_rank: bool = True,
    ) -> BinaryResultsWrapper:
        """
        Fits Probit model.

        Parameters
        ----------
        endog : array_like
            A 1-d endogenous response variable. The dependent variable.

        exog : array_like
            A nobs x k array where nobs is the number of observations and k is
            the number of regressors. An intercept is not included by default
            and should be added by the user.

        missing : str | None
            Available options are ‘none’, ‘drop’, and ‘raise’. If ‘none’, no
            nan checking is done. If ‘drop’, any observations with nans are
            dropped. If ‘raise’, an error is raised. Default is ‘none’.

        check_rank : bool
            Check exog rank to determine model degrees of freedom. Default is
            True. Setting to False reduces model initialization time when
            exog.shape[1] is large.

        Returns
        -------
        statsmodels.discrete.discrete_model.BinaryResultsWrapper
            Results.
        """
        code = getframeinfo(stack()[1][0]).code_context
        command: str = "" if code is None else "\n".join(code).strip()
        model = sm.Probit(endog, exog, missing=missing, check_rank=check_rank)
        results = model.fit()
        summary, outcome = self.__check_model_dof("probit", model)
        tables: list[SimpleTable] = results.summary().tables
        self.add_output(command, summary, outcome, _get_summary_json(tables))
        return results
