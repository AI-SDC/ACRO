"""ACRO: Automatic Checking of Research Outputs."""

import json
import logging
import os
import pathlib
import warnings
from collections.abc import Callable
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
from .record import Records

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("acro")
warnings.simplefilter(action="ignore", category=FutureWarning)


class ACRO:
    """ACRO: Automatic Checking of Research Outputs.

    Attributes
    ----------
    config : dict
        Safe parameters and their values.
    results : Records
        The current outputs including the results of checks.
    output_id : int
        The next identifier to be assigned to an output.

    Examples
    --------
    >>> acro = ACRO()
    >>> results = acro.ols(y, x)
    >>> results.summary()
    >>> acro.finalise("MYFOLDER", "json")
    """

    def __init__(self, config: str = "default", suppress: bool = False) -> None:
        """Constructs a new ACRO object and reads parameters from config.

        Parameters
        ----------
        config : str
            Name of a yaml configuration file with safe parameters.
        suppress : bool, default False
            Whether to automatically apply suppression.
        """
        self.config: dict = {}
        self.results: Records = Records()
        self.suppress: bool = suppress
        path = pathlib.Path(__file__).with_name(config + ".yaml")
        logger.debug("path: %s", path)
        with open(path, encoding="utf-8") as handle:
            self.config = yaml.load(handle, Loader=yaml.loader.SafeLoader)
        logger.info("config: %s", self.config)
        logger.info("automatic suppression: %s", self.suppress)
        # set globals needed for aggregation functions
        utils.THRESHOLD = self.config["safe_threshold"]
        utils.SAFE_PRATIO_P = self.config["safe_pratio_p"]
        utils.SAFE_NK_N = self.config["safe_nk_n"]
        utils.SAFE_NK_K = self.config["safe_nk_k"]
        utils.CHECK_MISSING_VALUES = self.config["check_missing_values"]

    def finalise(self, path: str = "outputs", ext="json") -> Records:
        """Creates a results file for checking.

        Parameters
        ----------
        path : str
            Name of a folder to save outputs.
        ext : str
            Extension of the results file. Valid extensions: {json, xlsx}.

        Returns
        -------
        Records
            Object storing the outputs.
        """
        self.results.finalise(path, ext)
        config_filename: str = os.path.normpath(f"{path}/config.json")
        with open(config_filename, "w", newline="", encoding="utf-8") as file:
            json.dump(self.config, file, indent=4, sort_keys=False)
        return self.results

    def remove_output(self, key: str) -> None:
        """Removes an output from the results.

        Parameters
        ----------
        key : str
            Key specifying which output to remove, e.g., 'output_0'.
        """
        self.results.remove(key)

    def print_outputs(self) -> str:
        """Prints the current results dictionary.

        Returns
        -------
        str
            String representation of all outputs.
        """
        return self.results.print()

    def custom_output(self, filename: str, comment: str = "") -> None:
        """Adds an unsupported output to the results dictionary.

        Parameters
        ----------
        filename : str
            The name of the file that will be added to the list of the outputs.
        comment : str
            An optional comment.
        """
        self.results.add_custom(filename, comment)

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

        # convert [list of] string to [list of] function
        aggfunc = utils.get_aggfuncs(aggfunc)

        # requested table
        table: DataFrame = pd.crosstab(  # type: ignore
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

        if aggfunc is not None:
            # create lists with single entry for when there is only one aggfunc
            freq_funcs: list[Callable] = [utils.AGGFUNC["freq"]]
            neg_funcs: list[Callable] = [utils.agg_negative]
            pperc_funcs: list[Callable] = [utils.agg_p_percent]
            nk_funcs: list[Callable] = [utils.agg_nk]
            missing_funcs: list[Callable] = [utils.agg_missing]
            # then expand them to deal with extra columns as needed
            if isinstance(aggfunc, list):
                num = len(aggfunc)
                freq_funcs.extend([utils.AGGFUNC["freq"] for i in range(1, num)])
                neg_funcs.extend([utils.agg_negative for i in range(1, num)])
                pperc_funcs.extend([utils.agg_p_percent for i in range(1, num)])
                nk_funcs.extend([utils.agg_nk for i in range(1, num)])
                missing_funcs.extend([utils.agg_missing for i in range(1, num)])
            # threshold check- doesn't matter what we pass for value
            t_values = pd.crosstab(  # type: ignore
                index,
                columns,
                values=index,
                rownames=rownames,
                colnames=colnames,
                aggfunc=freq_funcs,
                margins=margins,
                margins_name=margins_name,
                dropna=dropna,
                normalize=normalize,
            )
            t_values = t_values < utils.THRESHOLD
            masks["threshold"] = t_values
            # check for negative values -- currently unsupported
            negative = pd.crosstab(  # type: ignore
                index, columns, values, aggfunc=neg_funcs, margins=margins
            )
            if negative.to_numpy().sum() > 0:
                masks["negative"] = negative
            # p-percent check
            masks["p-ratio"] = pd.crosstab(  # type: ignore
                index, columns, values, aggfunc=pperc_funcs, margins=margins
            )
            # nk values check
            masks["nk-rule"] = pd.crosstab(  # type: ignore
                index, columns, values, aggfunc=nk_funcs, margins=margins
            )
            # check for missing values -- currently unsupported
            if utils.CHECK_MISSING_VALUES:
                masks["missing"] = pd.crosstab(  # type: ignore
                    index, columns, values, aggfunc=missing_funcs, margins=margins
                )
        else:
            # threshold check- doesn't matter what we pass for value
            t_values = pd.crosstab(  # type: ignore
                index,
                columns,
                values=None,
                rownames=rownames,
                colnames=colnames,
                aggfunc=None,
                margins=margins,
                margins_name=margins_name,
                dropna=dropna,
                normalize=normalize,
            )
            t_values = t_values < utils.THRESHOLD
            masks["threshold"] = t_values

        # pd.crosstab returns nan for an empty cell
        for name, mask in masks.items():
            mask.fillna(value=1, inplace=True)
            mask = mask.astype(int)
            mask.replace({0: False, 1: True}, inplace=True)
            masks[name] = mask

        # build the sdc dictionary
        sdc: dict = utils.get_table_sdc(masks, self.suppress)
        # get the status and summary
        status, summary = utils.get_summary(sdc)
        # apply the suppression
        safe_table, outcome = utils.apply_suppression(table, masks)
        if self.suppress:
            table = safe_table
        # record output
        self.results.add(
            status=status,
            output_type="table",
            properties={"method": "crosstab"},
            sdc=sdc,
            command=command,
            summary=summary,
            outcome=outcome,
            output=[table],
        )
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
        t_values = pd.pivot_table(  # type: ignore
            data, values, index, columns, aggfunc=agg
        )
        masks["threshold"] = t_values

        if aggfunc is not None:
            # check for negative values -- currently unsupported
            agg = [utils.agg_negative] * n_agg if n_agg > 1 else utils.agg_negative
            negative = pd.pivot_table(  # type: ignore
                data, values, index, columns, aggfunc=agg
            )
            if negative.to_numpy().sum() > 0:
                masks["negative"] = negative
            # p-percent check
            agg = [utils.agg_p_percent] * n_agg if n_agg > 1 else utils.agg_p_percent
            masks["p-ratio"] = pd.pivot_table(  # type: ignore
                data, values, index, columns, aggfunc=agg
            )
            # nk values check
            agg = [utils.agg_nk] * n_agg if n_agg > 1 else utils.agg_nk
            masks["nk-rule"] = pd.pivot_table(  # type: ignore
                data, values, index, columns, aggfunc=agg
            )
            # check for missing values -- currently unsupported
            if utils.CHECK_MISSING_VALUES:
                agg = [utils.agg_missing] * n_agg if n_agg > 1 else utils.agg_missing
                masks["missing"] = pd.pivot_table(  # type: ignore
                    data, values, index, columns, aggfunc=agg
                )

        # build the sdc dictionary
        sdc: dict = utils.get_table_sdc(masks, self.suppress)
        # get the status and summary
        status, summary = utils.get_summary(sdc)
        # apply the suppression
        safe_table, outcome = utils.apply_suppression(table, masks)
        if self.suppress:
            table = safe_table
        # record output
        self.results.add(
            status=status,
            output_type="table",
            properties={"method": "pivot_table"},
            sdc=sdc,
            command=command,
            summary=summary,
            outcome=outcome,
            output=[table],
        )
        return table

    def __check_model_dof(self, name: str, model) -> tuple[str, str, float]:
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
            Status: {"review", "fail", "pass"}.
        str
            Summary of the check.
        float
            The degrees of freedom.
        """
        status = "fail"
        dof: int = model.df_resid
        threshold: int = self.config["safe_dof_threshold"]
        if dof < threshold:
            summary = f"fail; dof={dof} < {threshold}"
            warnings.warn(f"Unsafe {name}: {summary}", stacklevel=8)
        else:
            status = "pass"
            summary = f"pass; dof={dof} >= {threshold}"
        logger.info("%s() outcome: %s", name, summary)
        return status, summary, float(dof)

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
        status, summary, dof = self.__check_model_dof("ols", model)
        tables: list[SimpleTable] = results.summary().tables
        self.results.add(
            status=status,
            output_type="regression",
            properties={"method": "ols", "dof": dof},
            sdc={},
            command=command,
            summary=summary,
            outcome=DataFrame(),
            output=utils.get_summary_dataframes(tables),
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
        status, summary, dof = self.__check_model_dof("olsr", model)
        tables: list[SimpleTable] = results.summary().tables
        self.results.add(
            status=status,
            output_type="regression",
            properties={"method": "olsr", "dof": dof},
            sdc={},
            command=command,
            summary=summary,
            outcome=DataFrame(),
            output=utils.get_summary_dataframes(tables),
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
        status, summary, dof = self.__check_model_dof("logit", model)
        tables: list[SimpleTable] = results.summary().tables
        self.results.add(
            status=status,
            output_type="regression",
            properties={"method": "logit", "dof": dof},
            sdc={},
            command=command,
            summary=summary,
            outcome=DataFrame(),
            output=utils.get_summary_dataframes(tables),
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
        status, summary, dof = self.__check_model_dof("logitr", model)
        tables: list[SimpleTable] = results.summary().tables
        self.results.add(
            status=status,
            output_type="regression",
            properties={"method": "logitr", "dof": dof},
            sdc={},
            command=command,
            summary=summary,
            outcome=DataFrame(),
            output=utils.get_summary_dataframes(tables),
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
        status, summary, dof = self.__check_model_dof("probit", model)
        tables: list[SimpleTable] = results.summary().tables
        self.results.add(
            status=status,
            output_type="regression",
            properties={"method": "probit", "dof": dof},
            sdc={},
            command=command,
            summary=summary,
            outcome=DataFrame(),
            output=utils.get_summary_dataframes(tables),
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
        status, summary, dof = self.__check_model_dof("probitr", model)
        tables: list[SimpleTable] = results.summary().tables
        self.results.add(
            status=status,
            output_type="regression",
            properties={"method": "probitr", "dof": dof},
            sdc={},
            command=command,
            summary=summary,
            outcome=DataFrame(),
            output=utils.get_summary_dataframes(tables),
        )
        return results

    def rename_output(self, old: str, new: str) -> None:
        """Rename an output.

        Parameters
        ----------
        old : str
            The old name of the output.
        new : str
            The new name of the output.
        """
        self.results.rename(old, new)

    def add_comments(self, output: str, comment: str) -> None:
        """Adds a comment to an output.

        Parameters
        ----------
        output : str
            The name of the output.
        comment : str
            The comment.
        """
        self.results.add_comments(output, comment)

    def add_exception(self, output: str, reason: str) -> None:
        """Adds an exception request to an output.

        Parameters
        ----------
        output : str
            The name of the output.
        reason : str
            The comment.
        """
        self.results.add_exception(output, reason)


def add_constant(data, prepend: bool = True, has_constant: str = "skip"):
    """Add a column of ones to an array.

    Parameters
    ----------
    data : array_like
        A column-ordered design matrix.
    prepend : bool
        If true, the constant is in the first column. Else the constant is
        appended (last column).
    has_constant : str {'raise', 'add', 'skip'}
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
