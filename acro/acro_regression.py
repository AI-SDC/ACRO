"""ACRO: Regression functions."""

from __future__ import annotations

import logging
import re
import warnings
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
from .record import Records

logger = logging.getLogger("acro")


def _get_endog_exog_variables(endog: Any, exog: Any) -> list[str]:
    """Extract variable names from endog and exog arguments.

    Parameters
    ----------
    endog : array_like
        The dependent variable (Series or array).
    exog : array_like
        The independent variables (DataFrame, Series, or array).

    Returns
    -------
    list[str]
        List of variable names: [dependent, independent1, independent2, ...].
    """
    variables: list[str] = []

    if hasattr(endog, "name") and endog.name is not None:
        variables.append(str(endog.name))

    if hasattr(exog, "columns"):
        for col in exog.columns:
            if str(col) != "const":
                variables.append(str(col))
    elif hasattr(exog, "name") and exog.name is not None:
        variables.append(str(exog.name))
    return variables


def _split_formula_terms(text: str, delimiters: str = "+") -> list[str]:
    """Split a formula string on delimiters, but only outside parentheses.

    Parameters
    ----------
    text : str
        The string to split.
    delimiters : str
        Characters to split on (e.g., '+' or ':*').

    Returns
    -------
    list[str]
        The split terms.
    """
    terms: list[str] = []
    depth = 0
    current: list[str] = []
    for char in text:
        if char == "(":
            depth += 1
            current.append(char)
        elif char == ")":
            depth -= 1
            current.append(char)
        elif char in delimiters and depth == 0:
            terms.append("".join(current))
            current = []
        else:
            current.append(char)
    terms.append("".join(current))
    return terms


def _get_formula_variables(formula: str) -> list[str]:
    """Extract variable names from an R-style formula string.

    Parses formulas like 'y ~ x1 + x2 + x3' to extract variable names.
    Handles interaction terms (x1:x2), polynomial terms I(x^2), and
    categorical terms C(x), respecting parentheses nesting.

    Parameters
    ----------
    formula : str
        An R-style formula string, e.g., 'y ~ x1 + x2'.

    Returns
    -------
    list[str]
        List of variable names: [dependent, independent1, independent2, ...].
    """
    variables: list[str] = []
    parts = formula.split("~")
    if len(parts) != 2:
        return variables

    dep_var = parts[0].strip()
    if dep_var:
        variables.append(dep_var)

    rhs = parts[1].strip()
    terms = _split_formula_terms(rhs, "+")
    for raw_term in terms:
        term = raw_term.strip()
        if not term or term == "1":
            continue

        sub_terms = _split_formula_terms(term, ":*")
        for sub in sub_terms:
            for cleaned in _process_subterm(sub):
                if cleaned not in variables:
                    variables.append(cleaned)
    return variables


def _process_subterm(sub: str) -> list[str]:
    """Clean a formula subterm by stripping wrappers and handling recursion.

    Parameters
    ----------
    sub : str
        The subterm to clean.

    Returns
    -------
    list[str]
        List of cleaned variable names.
    """
    sub = sub.strip()
    if not sub or sub == "1":
        return []

    sub = re.sub(r"^[IC]\(", "", sub)
    sub = re.sub(r"\)$", "", sub)

    sub = re.sub(r"\^\d+$", "", sub)

    while sub.startswith("(") and sub.endswith(")"):
        sub = sub[1:-1]
    sub = sub.strip()
    # if sub still contains +, it was inside parens — recurse
    if "+" in sub:
        results = []
        for inner in _split_formula_terms(sub, "+"):
            results.extend(_process_subterm(inner))
        return results
    return [sub] if sub else []


class Regression:
    """Creates regression models."""

    def __init__(
        self, _config: str
    ) -> None:  # _config: unused; ACRO sets self.config (Ruff ARG002)
        self.config: dict[str, Any] = {}
        self.results: Records = Records()

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
        status, summary, dof = self.__check_model_dof("ols", model)
        tables: list[SimpleTable] = results.summary().tables
        vars_used = _get_endog_exog_variables(endog, exog)
        self.results.add(
            status=status,
            output_type="regression",
            properties={"method": "ols", "dof": dof, "variables": vars_used},
            sdc={},
            command=command,
            summary=summary,
            outcome=DataFrame(),
            output=get_summary_dataframes(tables),
        )
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
            *args,
            **kwargs,
        )
        results = model.fit()
        status, summary, dof = self.__check_model_dof("olsr", model)
        tables: list[SimpleTable] = results.summary().tables
        vars_used = _get_formula_variables(formula)
        self.results.add(
            status=status,
            output_type="regression",
            properties={"method": "olsr", "dof": dof, "variables": vars_used},
            sdc={},
            command=command,
            summary=summary,
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
        status, summary, dof = self.__check_model_dof("logit", model)
        tables: list[SimpleTable] = results.summary().tables
        vars_used = _get_endog_exog_variables(endog, exog)
        self.results.add(
            status=status,
            output_type="regression",
            properties={"method": "logit", "dof": dof, "variables": vars_used},
            sdc={},
            command=command,
            summary=summary,
            outcome=DataFrame(),
            output=get_summary_dataframes(tables),
        )
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
            *args,
            **kwargs,
        )
        results = model.fit()
        status, summary, dof = self.__check_model_dof("logitr", model)
        tables: list[SimpleTable] = results.summary().tables
        vars_used = _get_formula_variables(formula)
        self.results.add(
            status=status,
            output_type="regression",
            properties={"method": "logitr", "dof": dof, "variables": vars_used},
            sdc={},
            command=command,
            summary=summary,
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
        status, summary, dof = self.__check_model_dof("probit", model)
        tables: list[SimpleTable] = results.summary().tables
        vars_used = _get_endog_exog_variables(endog, exog)
        self.results.add(
            status=status,
            output_type="regression",
            properties={"method": "probit", "dof": dof, "variables": vars_used},
            sdc={},
            command=command,
            summary=summary,
            outcome=DataFrame(),
            output=get_summary_dataframes(tables),
        )
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
            *args,
            **kwargs,
        )
        results = model.fit()
        status, summary, dof = self.__check_model_dof("probitr", model)
        tables: list[SimpleTable] = results.summary().tables
        vars_used = _get_formula_variables(formula)
        self.results.add(
            status=status,
            output_type="regression",
            properties={"method": "probitr", "dof": dof, "variables": vars_used},
            sdc={},
            command=command,
            summary=summary,
            outcome=DataFrame(),
            output=get_summary_dataframes(tables),
        )
        return results

    def __check_model_dof(self, name: str, model: Any) -> tuple[str, str, float]:
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
