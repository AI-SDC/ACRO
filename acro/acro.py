"""ACRO: Automatic Checking of Research Outputs."""  # pylint:disable=too-many-lines

import copy
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
import statsmodels.formula.api as smf
import yaml
from pandas import DataFrame, Series
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


def _get_command(stack_list: list[tuple]) -> str:
    """Returns the calling source line as a string.

    Parameters
    ----------
    stack_list : list[tuple]
         A list of frame records for the caller's stack. The first entry in the
         returned list represents the caller; the last entry represents the
         outermost call on the stack.

    Returns
    -------
    str
        The calling source line.
    """
    command: str = ""
    if len(stack_list) > 1:
        code = getframeinfo(stack_list[1][0]).code_context
        if code is not None:
            command = "\n".join(code).strip()
    logger.debug("command: %s", command)
    return command


def _finalise_json(filename: str, results: dict) -> None:
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


def _finalise_excel(filename: str, results: dict) -> None:
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


def _get_summary_dataframes(results: list[SimpleTable]) -> list[DataFrame]:
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


def _agg_threshold(vals: Series) -> bool:
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


def _agg_negative(vals: Series) -> bool:
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


def _agg_p_percent(vals: Series) -> bool:
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


def _agg_nk(vals: Series) -> bool:
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


def _apply_suppression(
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
    logger.debug("_apply_suppression()")
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
            outcome_df[mask.values] += name + "; "
        outcome_df = outcome_df.replace({"": "ok"})
    logger.debug("outcome_df:\n%s", outcome_df)
    return safe_df, outcome_df


def _get_summary(masks: dict[str, DataFrame]) -> str:
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
    logger.debug("_get_summary(): %s", summary)
    return summary


def _get_aggfunc(aggfunc: str | None) -> Callable | None:
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


def add_constant(data, prepend: bool = True, has_constant: str = "skip"):
    """Add a column of ones to an array.

    Parameters
    ----------
    data : array_like
        A column-ordered design matrix.
    prepend : bool
        If true, the constant is in the first column. Else the constant is
        appended (last column).
    has_constant: str {'raise', 'add', 'skip'}
        Behavior if data already has a constant. The default will return
        data without adding another constant. If 'raise', will raise an
        error if any column has a constant value. Using 'add' will add a
        column of 1s if a constant column is present.

    Returns
    -------
    array_like
        The original values with a constant (column of ones) as the first
        or last column. Returned value type depends on input type.

    Notes
    -----
    When the input is a pandas Series or DataFrame, the added column's name
    is 'const'.
    """
    return sm.add_constant(data, prepend=prepend, has_constant=has_constant)


class ACRO:
    """ACRO: Automatic Checking of Research Outputs.

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
        """Constructs a new ACRO object and reads parameters from config.

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
        """Creates a results file for checking.

        Parameters
        ----------
        filename : str
            Name of the output file. Valid extensions: {.json, .xlsx}.

        Returns
        -------
        dict
            Dictionary representation of the output.
        """
        logger.debug("finalise()")
        _, extension = os.path.splitext(filename)
        if extension == ".json":
            _finalise_json(filename, self.results)
        elif extension == ".xlsx":
            _finalise_excel(filename, self.results)
        else:
            raise ValueError("Invalid file extension. Options: {.json, .xlsx}")
        logger.debug("output written to: %s", filename)
        return self.results

    def __add_output(
        self, command: str, summary: str, outcome: DataFrame, output: list[DataFrame]
    ) -> None:
        """Adds an output to the results dictionary.

        Parameters
        ----------
        command : str
            String representation of the operation performed.
        summary : str
            String summarising the ACRO checks.
        outcome : DataFrame
            DataFrame describing the details of ACRO checks.
        output : list[DataFrame]
            List of output DataFrames.
        """
        name: str = f"output_{self.output_id}"
        self.output_id += 1
        self.results[name] = {
            "command": command,
            "summary": summary,
            "outcome": outcome,
            "output": output,  # json.loads(output),  # JSON to dict
        }
        logger.debug("__add_output(): %s", name)

    def remove_output(self, key: str) -> None:
        """Removes an output from the results dictionary.

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

    def print_outputs(self) -> None:
        """Prints the current results dictionary."""
        logger.debug("print_outputs()")
        for name, result in self.results.items():
            print(f"{name}:")
            for key, item in result.items():
                print(f"{key}: {item}")
            print("\n")

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
        """Compute a simple cross tabulation of two (or more) factors.  By
        default, computes a frequency table of the factors unless an array of
        values and an aggregation function are passed.

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
        logger.debug("crosstab()")
        command: str = _get_command(stack())

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
        masks: dict[str, DataFrame] = {}

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
            # check for negative values -- currently unsupported
            negative = pd.crosstab(index, columns, values, aggfunc=_agg_negative)
            if negative.to_numpy().sum() > 0:
                masks["negative"] = negative
            # p-percent check
            masks["p-ratio"] = pd.crosstab(
                index, columns, values, aggfunc=_agg_p_percent
            )
            # nk values check
            masks["nk-rule"] = pd.crosstab(index, columns, values, aggfunc=_agg_nk)

        table, outcome = _apply_suppression(table, masks)
        summary = _get_summary(masks)
        self.__add_output(command, summary, outcome, [table])
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
        """Create a spreadsheet-style pivot table as a DataFrame.

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
        logger.debug("pivot_table()")
        command: str = _get_command(stack())

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
        masks: dict[str, DataFrame] = {}

        # threshold check
        agg = [_agg_threshold] * n_agg if n_agg > 1 else _agg_threshold
        t_values = pd.pivot_table(data, values, index, columns, aggfunc=agg)
        masks["threshold"] = t_values

        if aggfunc is not None:
            # check for negative values -- currently unsupported
            agg = [_agg_negative] * n_agg if n_agg > 1 else _agg_negative
            negative = pd.pivot_table(data, values, index, columns, aggfunc=agg)
            if negative.to_numpy().sum() > 0:
                masks["negative"] = negative
            # p-percent check
            agg = [_agg_p_percent] * n_agg if n_agg > 1 else _agg_p_percent
            masks["p-ratio"] = pd.pivot_table(data, values, index, columns, aggfunc=agg)
            # nk values check
            agg = [_agg_nk] * n_agg if n_agg > 1 else _agg_nk
            masks["nk-rule"] = pd.pivot_table(data, values, index, columns, aggfunc=agg)

        table, outcome = _apply_suppression(table, masks)
        summary = _get_summary(masks)
        self.__add_output(command, summary, outcome, [table])
        return table

    def __check_model_dof(self, name: str, model) -> str:
        """Check model DOF.

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
        """
        dof: int = model.df_resid
        threshold: int = self.config["safe_dof_threshold"]
        if dof < threshold:
            summary = f"fail; dof={dof} < {threshold}"
            warnings.warn(f"Unsafe {name}: {summary}")
        else:
            summary = f"pass; dof={dof} >= {threshold}"
        logger.debug("%s() outcome: %s", name, summary)
        return summary

    def ols(  # pylint: disable=too-many-locals
        self, endog, exog=None, missing="none", hasconst=None, **kwargs
    ) -> RegressionResultsWrapper:
        """Fits Ordinary Least Squares Regression.

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
        RegressionResultsWrapper
            Results.
        """
        logger.debug("ols()")
        command: str = _get_command(stack())
        model = sm.OLS(endog, exog=exog, missing=missing, hasconst=hasconst, **kwargs)
        results = model.fit()
        summary = self.__check_model_dof("ols", model)
        tables: list[SimpleTable] = results.summary().tables
        self.__add_output(
            command, summary, DataFrame(), _get_summary_dataframes(tables)
        )
        return results

    def olsr(  # pylint: disable=too-many-locals,keyword-arg-before-vararg
        self, formula, data, subset=None, drop_cols=None, *args, **kwargs
    ) -> RegressionResultsWrapper:
        """Fits Ordinary Least Squares Regression from a formula and dataframe.

        Parameters
        ----------
        formula : str or generic Formula object
            The formula specifying the model.
        data : array_like
            The data for the model. See Notes.
        subset : array_like
            An array-like object of booleans, integers, or index values that
            indicate the subset of df to use in the model. Assumes df is a
            `pandas.DataFrame`.
        drop_cols : array_like
            Columns to drop from the design matrix.  Cannot be used to
            drop terms involving categoricals.
        *args
            Additional positional argument that are passed to the model.
        **kwargs
            These are passed to the model with one exception. The
            ``eval_env`` keyword is passed to patsy. It can be either a
            :class:`patsy:patsy.EvalEnvironment` object or an integer
            indicating the depth of the namespace to use. For example, the
            default ``eval_env=0`` uses the calling namespace. If you wish
            to use a "clean" environment set ``eval_env=-1``.

        Returns
        -------
        RegressionResultsWrapper
            Results.

        Notes
        -----
        data must define __getitem__ with the keys in the formula terms
        args and kwargs are passed on to the model instantiation. E.g.,
        a numpy structured or rec array, a dictionary, or a pandas DataFrame.
        """
        logger.debug("olsr()")
        command: str = _get_command(stack())
        model = smf.ols(
            formula=formula,
            data=data,
            subset=subset,
            drop_cols=drop_cols,
            *args,
            **kwargs,
        )
        results = model.fit()
        summary = self.__check_model_dof("olsr", model)
        tables: list[SimpleTable] = results.summary().tables
        self.__add_output(
            command, summary, DataFrame(), _get_summary_dataframes(tables)
        )
        return results

    def logit(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        endog,
        exog,
        missing: str | None = None,
        check_rank: bool = True,
    ) -> BinaryResultsWrapper:
        """Fits Logit model.

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
        BinaryResultsWrapper
            Results.
        """
        logger.debug("logit()")
        command: str = _get_command(stack())
        model = sm.Logit(endog, exog, missing=missing, check_rank=check_rank)
        results = model.fit()
        summary = self.__check_model_dof("logit", model)
        tables: list[SimpleTable] = results.summary().tables
        self.__add_output(
            command, summary, DataFrame(), _get_summary_dataframes(tables)
        )
        return results

    def logitr(  # pylint: disable=too-many-locals,keyword-arg-before-vararg
        self, formula, data, subset=None, drop_cols=None, *args, **kwargs
    ) -> RegressionResultsWrapper:
        """Fits Logit model from a formula and dataframe.

        Parameters
        ----------
        formula : str or generic Formula object
            The formula specifying the model.
        data : array_like
            The data for the model. See Notes.
        subset : array_like
            An array-like object of booleans, integers, or index values that
            indicate the subset of df to use in the model. Assumes df is a
            `pandas.DataFrame`.
        drop_cols : array_like
            Columns to drop from the design matrix.  Cannot be used to
            drop terms involving categoricals.
        *args
            Additional positional argument that are passed to the model.
        **kwargs
            These are passed to the model with one exception. The
            ``eval_env`` keyword is passed to patsy. It can be either a
            :class:`patsy:patsy.EvalEnvironment` object or an integer
            indicating the depth of the namespace to use. For example, the
            default ``eval_env=0`` uses the calling namespace. If you wish
            to use a "clean" environment set ``eval_env=-1``.

        Returns
        -------
        RegressionResultsWrapper
            Results.

        Notes
        -----
        data must define __getitem__ with the keys in the formula terms
        args and kwargs are passed on to the model instantiation. E.g.,
        a numpy structured or rec array, a dictionary, or a pandas DataFrame.
        """
        logger.debug("logitr()")
        command: str = _get_command(stack())
        model = smf.logit(
            formula=formula,
            data=data,
            subset=subset,
            drop_cols=drop_cols,
            *args,
            **kwargs,
        )
        results = model.fit()
        summary = self.__check_model_dof("logitr", model)
        tables: list[SimpleTable] = results.summary().tables
        self.__add_output(
            command, summary, DataFrame(), _get_summary_dataframes(tables)
        )
        return results

    def probit(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        endog,
        exog,
        missing: str | None = None,
        check_rank: bool = True,
    ) -> BinaryResultsWrapper:
        """Fits Probit model.

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
        BinaryResultsWrapper
            Results.
        """
        logger.debug("probit()")
        command: str = _get_command(stack())
        model = sm.Probit(endog, exog, missing=missing, check_rank=check_rank)
        results = model.fit()
        summary = self.__check_model_dof("probit", model)
        tables: list[SimpleTable] = results.summary().tables
        self.__add_output(
            command, summary, DataFrame(), _get_summary_dataframes(tables)
        )
        return results

    def probitr(  # pylint: disable=too-many-locals,keyword-arg-before-vararg
        self, formula, data, subset=None, drop_cols=None, *args, **kwargs
    ) -> RegressionResultsWrapper:
        """Fits Probit model from a formula and dataframe.

        Parameters
        ----------
        formula : str or generic Formula object
            The formula specifying the model.
        data : array_like
            The data for the model. See Notes.
        subset : array_like
            An array-like object of booleans, integers, or index values that
            indicate the subset of df to use in the model. Assumes df is a
            `pandas.DataFrame`.
        drop_cols : array_like
            Columns to drop from the design matrix.  Cannot be used to
            drop terms involving categoricals.
        *args
            Additional positional argument that are passed to the model.
        **kwargs
            These are passed to the model with one exception. The
            ``eval_env`` keyword is passed to patsy. It can be either a
            :class:`patsy:patsy.EvalEnvironment` object or an integer
            indicating the depth of the namespace to use. For example, the
            default ``eval_env=0`` uses the calling namespace. If you wish
            to use a "clean" environment set ``eval_env=-1``.

        Returns
        -------
        RegressionResultsWrapper
            Results.

        Notes
        -----
        data must define __getitem__ with the keys in the formula terms
        args and kwargs are passed on to the model instantiation. E.g.,
        a numpy structured or rec array, a dictionary, or a pandas DataFrame.
        """
        logger.debug("probitr()")
        command: str = _get_command(stack())
        model = smf.probit(
            formula=formula,
            data=data,
            subset=subset,
            drop_cols=drop_cols,
            *args,
            **kwargs,
        )
        results = model.fit()
        summary = self.__check_model_dof("probitr", model)
        tables: list[SimpleTable] = results.summary().tables
        self.__add_output(
            command, summary, DataFrame(), _get_summary_dataframes(tables)
        )
        return results
