"""ACRO: Regression functions."""

from __future__ import annotations

import logging
from inspect import stack
from typing import Any

import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from numpy.typing import ArrayLike
from pandas import DataFrame
from statsmodels.discrete.discrete_model import BinaryResultsWrapper
from statsmodels.iolib.table import SimpleTable
from statsmodels.regression.linear_model import RegressionResultsWrapper

from . import utils
from .checks import SDCChecks,ChecksResults
from .record import Records
from .constants import SDMX_DIMENSION, SDMX_MEASURE

logger = logging.getLogger("acro")


class Regression:
    """Creates regression models."""

    def __init__(
        self, _config: str
    ) -> None:  # _config: unused; ACRO sets self.config (Ruff ARG002)
        self.config: dict[str, Any] = {}
        self.results: Records = Records()
        self.sdc_checks = SDCChecks({})

    def ols(
        self,
        endog: ArrayLike,
        exog: ArrayLike | None = None,
        missing: str = "none",
        hasconst: bool | None = None,
        **kwargs: Any,
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

        analysis_name = "GeneralLinearModel"
        checkresults:ChecksResults = self.sdc_checks.run_checks_for_analysis(
            analysis_name, model
        )

        checkresults.fair_dict.update(get_variable_type_dict(results))

        tables: list[SimpleTable] = results.summary().tables
        self.results.add(
            status=checkresults.overall_status,
            output_type="regression",
            properties={"method": "ols", "dof": 
                        checkresults.outcomes["MinimumDoFCheck"]},
            sdc={},
            fair=checkresults.fair_dict,
            command=command,
            summary=checkresults.summaries,
            outcome=DataFrame(),
            output=get_summary_dataframes(tables),
 
        )
        return results

    def olsr(  # pylint: disable=keyword-arg-before-vararg
        self,
        formula: str,
        data: Any,
        subset: Any = None,
        drop_cols: Any = None,
        *args: Any,
        **kwargs: Any,
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
        Arguments are passed in the same order as statsmodels.
        """
        logger.debug("olsr()")
        command: str = utils.get_command("olsr()", stack())
        model = smf.ols(
            formula=formula,
            data=data,
            subset=subset,
            drop_cols=drop_cols,
            *args,  # noqa: B026
            **kwargs,
        )
        results = model.fit()

        analysis_name = "GeneralLinearModel"
        checkresults:ChecksResults = self.sdc_checks.run_checks_for_analysis(
            analysis_name, model
        )
        checkresults.fair_dict.update(get_variable_type_dict(results))

        tables: list[SimpleTable] = results.summary().tables
        self.results.add(
            status=checkresults.overall_status,
            output_type="regression",
            properties={"method": "olsr", 
                        "dof": checkresults.outcomes["MinimumDoFCheck"]},
            sdc={},
            fair=checkresults.fair_dict,
            command=command,
            summary=checkresults.summaries,
            outcome=DataFrame(),
            output=get_summary_dataframes(tables),

        )
        return results

    def logit(
        self,
        endog: ArrayLike,
        exog: ArrayLike,
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

        analysis_name = "Logit"
        checkresults:ChecksResults = self.sdc_checks.run_checks_for_analysis(
            analysis_name, model
        )
        checkresults.fair_dict.update(get_variable_type_dict(results))

        tables: list[SimpleTable] = results.summary().tables
        self.results.add(
            status=checkresults.overall_status,
            output_type="regression",
            properties={"method": "logit", 
                        "dof": checkresults.outcomes["MinimumDoFCheck"]},
            sdc={},
            fair=checkresults.fair_dict,
            command=command,
            summary=checkresults.summaries,
            outcome=DataFrame(),
            output=get_summary_dataframes(tables),

        )
        return results

    def logitr(  # pylint: disable=keyword-arg-before-vararg
        self,
        formula: str,
        data: Any,
        subset: Any = None,
        drop_cols: Any = None,
        *args: Any,
        **kwargs: Any,
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
        Arguments are passed in the same order as statsmodels.
        """
        logger.debug("logitr()")
        command: str = utils.get_command("logitr()", stack())
        model = smf.logit(
            formula=formula,
            data=data,
            subset=subset,
            drop_cols=drop_cols,
            *args,  # noqa: B026
            **kwargs,
        )
        results = model.fit()

        analysis_name = "Logit"
        checkresults:ChecksResults = self.sdc_checks.run_checks_for_analysis(
            analysis_name, model
        )
        checkresults.fair_dict.update(get_variable_type_dict(results))

        tables: list[SimpleTable] = results.summary().tables
        self.results.add(
            status=checkresults.overall_status,
            output_type="regression",
            properties={"method": "logitr", 
                        "dof": checkresults.outcomes["MinimumDoFCheck"]},
            sdc={},
            fair=checkresults.fair_dict,
            command=command,
            summary=checkresults.summaries,
            outcome=DataFrame(),
            output=get_summary_dataframes(tables),

        )
        return results

    def probit(
        self,
        endog: ArrayLike,
        exog: ArrayLike,
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

        analysis_name = "Probit"
        checkresults:ChecksResults = self.sdc_checks.run_checks_for_analysis(
            analysis_name, model
        )
        checkresults.fair_dict.update(get_variable_type_dict(results))
        

        tables: list[SimpleTable] = results.summary().tables
        self.results.add(
            status=checkresults.overall_status,
            output_type="regression",
            properties={"method": "probit",
                        "dof": checkresults.outcomes["MinimumDoFCheck"]},
            sdc={},
            fair=checkresults.fair_dict,
            command=command,
            summary=checkresults.summaries,
            outcome=DataFrame(),
            output=get_summary_dataframes(tables),

        )
        return results

    def probitr(  # pylint: disable=keyword-arg-before-vararg
        self,
        formula: str,
        data: Any,
        subset: Any = None,
        drop_cols: Any = None,
        *args: Any,
        **kwargs: Any,
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
        Arguments are passed in the same order as statsmodels.
        """
        logger.debug("probitr()")
        command: str = utils.get_command("probitr()", stack())
        model = smf.probit(
            formula=formula,
            data=data,
            subset=subset,
            drop_cols=drop_cols,
            *args,  # noqa: B026
            **kwargs,
        )
        results = model.fit()

        analysis_name = "Probit"
        checkresults:ChecksResults = self.sdc_checks.run_checks_for_analysis(
            analysis_name, model
        )
        checkresults.fair_dict.update(get_variable_type_dict(results))

        tables: list[SimpleTable] = results.summary().tables
        self.results.add(
            status=checkresults.overall_status,
            output_type="regression",
            properties={"method": "probitr", 
                        "dof": checkresults.outcomes["MinimumDoFCheck"]},
            sdc={},
            fair=checkresults.fair_dict,
            command=command,
            summary=checkresults.summaries,
            outcome=DataFrame(),
            output=get_summary_dataframes(tables),

        )
        return results


def get_summary_dataframes(results: list[SimpleTable]) -> list[DataFrame]:
    """Convert a list of SimpleTable objects to a list of DataFrame objects.

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


def add_constant(data: Any, prepend: bool = True, has_constant: str = "skip") -> Any:
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

def get_variable_metadata(endog:list,exog:list,values:Series|None)->dict[str,dict]:
    """ create data dictionary 

    TODO 
    expand
    
    """
    #TODO handle arraylike as well as series
    #TODO handle rownames/colnames
    variable_metadata:dict[str,dict] = {}
    variable_metadata.update(get_axis_metadata(index,where="rows"))
    variable_metadata.update(get_axis_metadata(columns,where="columns"))
    if values is not None:
        name= values.name if isinstance(values,Series) else "unknown_measure"
        variable_metadata[name]= {"location": "cells",
                              "sequence_id": 0,
                              "dtype": values[0].dtype,
                              "type" : SDMX_MEASURE,
                              "dependent":True,
                              "categories":[]
                             }
    return variable_metadata


def get_variable_type_dict(results:RegressionResultsWrapper)->dict[str,Any]:
    """get dict of idependent and independent variable ids for regression models)"""
    thedict:dict[str,Any]={
        "dependent":"unknown",
        "independent":["unknown"]
    }
    deps=results.model.endog_names
    if isinstance(deps,str):
        thedict["dependent"]=deps
    indeps=results.model.exog_names.copy()
    if 'const' in indeps: indeps.remove('const')
    if 'Intercept' in indeps: indeps.remove('Intercept')
    thedict["independent"]= indeps    
    return thedict
    