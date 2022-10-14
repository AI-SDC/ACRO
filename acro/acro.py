"""ACRO: Automatic Checking of Research Outputs."""

import logging
import os
import pathlib
import warnings
from inspect import stack

import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
import yaml
from pandas import DataFrame
from statsmodels.discrete.discrete_model import BinaryResultsWrapper
from statsmodels.iolib.table import SimpleTable
from statsmodels.regression.linear_model import RegressionResultsWrapper

from . import utils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("acro")


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
        logger.info("config: %s", self.config)
        # set globals needed for aggregation functions
        utils.THRESHOLD = self.config["safe_threshold"]
        utils.SAFE_PRATIO_P = self.config["safe_pratio_p"]
        utils.SAFE_NK_N = self.config["safe_nk_n"]
        utils.SAFE_NK_K = self.config["safe_nk_k"]

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
            utils.finalise_json(filename, self.results)
        elif extension == ".xlsx":
            utils.finalise_excel(filename, self.results)
        else:
            raise ValueError("Invalid file extension. Options: {.json, .xlsx}")
        logger.info("output written to: %s", filename)
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
        logger.info("add_output(): %s", name)

    def remove_output(self, key: str) -> None:
        """Removes an output from the results dictionary.

        Parameters
        ----------
        key : str
            Key specifying which output to remove, e.g., 'output_0'.
        """
        if key in self.results:
            del self.results[key]
            logger.info("remove_output(): %s removed", key)
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
        command: str = utils.get_command("crosstab()", stack())

        aggfunc = utils.get_aggfunc(aggfunc)  # convert string to function

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
        t_values = t_values < utils.THRESHOLD
        masks["threshold"] = t_values

        if aggfunc is not None:
            # check for negative values -- currently unsupported
            negative = pd.crosstab(index, columns, values, aggfunc=utils.agg_negative)
            if negative.to_numpy().sum() > 0:
                masks["negative"] = negative
            # p-percent check
            masks["p-ratio"] = pd.crosstab(
                index, columns, values, aggfunc=utils.agg_p_percent
            )
            # nk values check
            masks["nk-rule"] = pd.crosstab(index, columns, values, aggfunc=utils.agg_nk)

        table, outcome = utils.apply_suppression(table, masks)
        summary = utils.get_summary(masks)
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
        command: str = utils.get_command("pivot_table()", stack())

        aggfunc = utils.get_aggfuncs(aggfunc)  # convert string(s) to function(s)
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
        agg = [utils.agg_threshold] * n_agg if n_agg > 1 else utils.agg_threshold
        t_values = pd.pivot_table(data, values, index, columns, aggfunc=agg)
        masks["threshold"] = t_values

        if aggfunc is not None:
            # check for negative values -- currently unsupported
            agg = [utils.agg_negative] * n_agg if n_agg > 1 else utils.agg_negative
            negative = pd.pivot_table(data, values, index, columns, aggfunc=agg)
            if negative.to_numpy().sum() > 0:
                masks["negative"] = negative
            # p-percent check
            agg = [utils.agg_p_percent] * n_agg if n_agg > 1 else utils.agg_p_percent
            masks["p-ratio"] = pd.pivot_table(data, values, index, columns, aggfunc=agg)
            # nk values check
            agg = [utils.agg_nk] * n_agg if n_agg > 1 else utils.agg_nk
            masks["nk-rule"] = pd.pivot_table(data, values, index, columns, aggfunc=agg)

        table, outcome = utils.apply_suppression(table, masks)
        summary = utils.get_summary(masks)
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
        logger.info("%s() outcome: %s", name, summary)
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
        command: str = utils.get_command("ols()", stack())
        model = sm.OLS(endog, exog=exog, missing=missing, hasconst=hasconst, **kwargs)
        results = model.fit()
        summary = self.__check_model_dof("ols", model)
        tables: list[SimpleTable] = results.summary().tables
        self.__add_output(
            command, summary, DataFrame(), utils.get_summary_dataframes(tables)
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
        command: str = utils.get_command("olsr()", stack())
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
            command, summary, DataFrame(), utils.get_summary_dataframes(tables)
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
        command: str = utils.get_command("logit()", stack())
        model = sm.Logit(endog, exog, missing=missing, check_rank=check_rank)
        results = model.fit()
        summary = self.__check_model_dof("logit", model)
        tables: list[SimpleTable] = results.summary().tables
        self.__add_output(
            command, summary, DataFrame(), utils.get_summary_dataframes(tables)
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
        command: str = utils.get_command("logitr()", stack())
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
            command, summary, DataFrame(), utils.get_summary_dataframes(tables)
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
        command: str = utils.get_command("probit()", stack())
        model = sm.Probit(endog, exog, missing=missing, check_rank=check_rank)
        results = model.fit()
        summary = self.__check_model_dof("probit", model)
        tables: list[SimpleTable] = results.summary().tables
        self.__add_output(
            command, summary, DataFrame(), utils.get_summary_dataframes(tables)
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
        command: str = utils.get_command("probitr()", stack())
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
            command, summary, DataFrame(), utils.get_summary_dataframes(tables)
        )
        return results


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
