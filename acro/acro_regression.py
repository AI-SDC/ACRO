"""ACRO: Regression functions."""

from __future__ import annotations

import logging
from inspect import stack
from io import StringIO
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
from .record import Records
from .sdcchecks import ChecksResults, SDCChecks, SDCEvidence

logger = logging.getLogger("acro")


class Regression:
    """Creates regression models."""

    def __init__(
        self, _config: str
    ) -> None:  # _config: unused; ACRO sets self.config (Ruff ARG002)
        self.config: dict[str, Any] = {}
        self.results: Records = Records()
        self.sdc_checks = SDCChecks({})
        self.federated: bool = False
        self._federated_evidence: dict = {}

    # ------------------------------------------------------------------
    # Private helpers shared by all regression commands
    # ------------------------------------------------------------------

    def _process_output(
        self,
        method: str,
        command: str,
        analysis_name: str,
        evidence: SDCEvidence,
        model: Any,
        results: Any,
    ) -> None:
        """Process regression output in federated or standalone mode.

        Consolidates the logic for both _add_federated_output and
        _add_standalone_output to eliminate code duplication.

        Parameters
        ----------
        method : str
            Short method name stored in ``properties``, e.g. ``"ols"``.
        command : str
            The command string captured from the call stack.
        analysis_name : str
            The SDC analysis name, e.g. ``"GeneralLinearModel"``.
        evidence : SDCEvidence
            Evidence object returned by ``get_evidence_forall_analyses``.
        model : Any
            Fitted statsmodels model instance.
        results : Any
            Fitted results wrapper (used to extract summary tables and variable
            type metadata).
            
        """
        if self.federated:
            uid = f"output_{self.results.output_id}"
            self._federated_evidence[uid] = {
                "command": command,
                "analysis_names": [analysis_name],
                "variable_types": evidence.variable_type_dict,
                "dof": evidence.dof,
                "interim_tables": {},
            }
            self.results.output_id += 1
        else:
            checkresults: ChecksResults = self.sdc_checks.run_checks_for_analysis(
                analysis_name, evidence, model
            )
            checkresults.fair_dict.update(get_variable_type_dict(results))

            tables: list[SimpleTable] = results.summary().tables
            self.results.add(
                status=checkresults.overall_status,
                output_type="regression",
                properties={
                    "method": method,
                    "dof": checkresults.outcomes["MinimumDoFCheck"],
                },
                sdc={},
                fair=checkresults.fair_dict,
                command=command,
                summary=checkresults.summaries,
                outcome=DataFrame(),
                output=get_summary_dataframes(tables),
            )

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
        evidence: SDCEvidence = self.sdc_checks.get_evidence_forall_analyses(
            [analysis_name], model
        )

        self._process_output("ols", command, analysis_name, evidence, model, results)
        return results

    def olsr(
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
        )
        if args or kwargs:
            # Note: args and kwargs are documented but not directly used
            # as statsmodels OLS doesn't accept *args, **kwargs
            pass
        results = model.fit()

        analysis_name = "GeneralLinearModel"
        evidence: SDCEvidence = self.sdc_checks.get_evidence_forall_analyses(
            [analysis_name], model
        )

        self._process_output("olsr", command, analysis_name, evidence, model, results)
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
        evidence: SDCEvidence = self.sdc_checks.get_evidence_forall_analyses(
            [analysis_name], model
        )

        self._process_output("logit", command, analysis_name, evidence, model, results)
        return results

    def logitr(
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
        )
        if args or kwargs:
            # Note: args and kwargs are documented but not directly used
            pass
        results = model.fit()

        analysis_name = "Logit"
        evidence: SDCEvidence = self.sdc_checks.get_evidence_forall_analyses(
            [analysis_name], model
        )

        self._process_output("logitr", command, analysis_name, evidence, model, results)
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
        evidence: SDCEvidence = self.sdc_checks.get_evidence_forall_analyses(
            [analysis_name], model
        )

        self._process_output("probit", command, analysis_name, evidence, model, results)
        return results

    def probitr(
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
        )
        if args or kwargs:
            # Note: args and kwargs are documented but not directly used
            pass
        results = model.fit()

        analysis_name = "Probit"
        evidence: SDCEvidence = self.sdc_checks.get_evidence_forall_analyses(
            [analysis_name], model
        )

        self._process_output(
            "probitr", command, analysis_name, evidence, model, results
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
        table_html = table.as_html()
        table_df = pd.read_html(StringIO(table_html), header=0, index_col=0)[0]
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


def get_variable_type_dict(results: RegressionResultsWrapper) -> dict[str, Any]:
    """Get dict of independent and independent variable ids for regression models)."""
    thedict: dict[str, Any] = {"dependent": "unknown", "independent": ["unknown"]}
    deps = results.model.endog_names
    if isinstance(deps, str):
        thedict["dependent"] = deps
    indeps = results.model.exog_names.copy()
    if "const" in indeps:
        indeps.remove("const")
    if "Intercept" in indeps:
        indeps.remove("Intercept")
    thedict["independent"] = indeps
    return thedict
