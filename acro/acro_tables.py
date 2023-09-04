"""ACRO: Tables functions."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from inspect import stack

import numpy as np
import pandas as pd
import statsmodels.api as sm
from matplotlib import pyplot as plt
from pandas import DataFrame, Series

from . import utils
from .record import Records

logger = logging.getLogger("acro")


AGGFUNC: dict[str, Callable] = {
    "mean": np.mean,
    "median": np.median,
    "sum": np.sum,
    "std": np.std,
    "freq": np.size,
}

# aggregation function parameters
THRESHOLD: int = 10
SAFE_PRATIO_P: float = 0.1
SAFE_NK_N: int = 2
SAFE_NK_K: float = 0.9
CHECK_MISSING_VALUES: bool = False

# survival analysis parameters
SURVIVAL_THRESHOLD: int = 10


class Tables:
    """Creates tabular data.

    Attributes
    ----------
    suppress : bool
        Whether to automatically apply suppression.
    """

    def __init__(self, suppress):
        self.suppress = suppress
        self.results: Records = Records()

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
        # syntax checking
        if aggfunc is not None:
            if values is None or isinstance(values, list):
                raise ValueError(
                    "If you pass an aggregation function to crosstab "
                    "you must also specify a single values column "
                    "to aggregate over."
                )

        # convert [list of] string to [list of] function
        aggfunc = get_aggfuncs(aggfunc)

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
            freq_funcs: list[Callable] = [AGGFUNC["freq"]]
            neg_funcs: list[Callable] = [agg_negative]
            pperc_funcs: list[Callable] = [agg_p_percent]
            nk_funcs: list[Callable] = [agg_nk]
            missing_funcs: list[Callable] = [agg_missing]
            # then expand them to deal with extra columns as needed
            if isinstance(aggfunc, list):
                num = len(aggfunc)
                freq_funcs.extend([AGGFUNC["freq"] for i in range(1, num)])
                neg_funcs.extend([agg_negative for i in range(1, num)])
                pperc_funcs.extend([agg_p_percent for i in range(1, num)])
                nk_funcs.extend([agg_nk for i in range(1, num)])
                missing_funcs.extend([agg_missing for i in range(1, num)])
            # threshold check- doesn't matter what we pass for value

            t_values = pd.crosstab(  # type: ignore
                index,
                columns,
                values=values,
                rownames=rownames,
                colnames=colnames,
                aggfunc=freq_funcs,
                margins=margins,
                margins_name=margins_name,
                dropna=dropna,
                normalize=normalize,
            )
            t_values = t_values < THRESHOLD
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
            if CHECK_MISSING_VALUES:
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
            t_values = t_values < THRESHOLD
            masks["threshold"] = t_values

        # pd.crosstab returns nan for an empty cell
        for name, mask in masks.items():
            mask.fillna(value=1, inplace=True)
            mask = mask.astype(int)
            mask.replace({0: False, 1: True}, inplace=True)
            masks[name] = mask

        # build the sdc dictionary
        sdc: dict = get_table_sdc(masks, self.suppress)
        # get the status and summary
        status, summary = get_summary(sdc)
        # apply the suppression
        safe_table, outcome = apply_suppression(table, masks)
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
        masks: dict[str, DataFrame] = {}

        # threshold check
        agg = [agg_threshold] * n_agg if n_agg > 1 else agg_threshold
        t_values = pd.pivot_table(  # type: ignore
            data, values, index, columns, aggfunc=agg
        )
        masks["threshold"] = t_values

        if aggfunc is not None:
            # check for negative values -- currently unsupported
            agg = [agg_negative] * n_agg if n_agg > 1 else agg_negative
            negative = pd.pivot_table(  # type: ignore
                data, values, index, columns, aggfunc=agg
            )
            if negative.to_numpy().sum() > 0:
                masks["negative"] = negative
            # p-percent check
            agg = [agg_p_percent] * n_agg if n_agg > 1 else agg_p_percent
            masks["p-ratio"] = pd.pivot_table(  # type: ignore
                data, values, index, columns, aggfunc=agg
            )
            # nk values check
            agg = [agg_nk] * n_agg if n_agg > 1 else agg_nk
            masks["nk-rule"] = pd.pivot_table(  # type: ignore
                data, values, index, columns, aggfunc=agg
            )
            # check for missing values -- currently unsupported
            if CHECK_MISSING_VALUES:
                agg = [agg_missing] * n_agg if n_agg > 1 else agg_missing
                masks["missing"] = pd.pivot_table(  # type: ignore
                    data, values, index, columns, aggfunc=agg
                )

        # build the sdc dictionary
        sdc: dict = get_table_sdc(masks, self.suppress)
        # get the status and summary
        status, summary = get_summary(sdc)
        # apply the suppression
        safe_table, outcome = apply_suppression(table, masks)
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

    def surv_func(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        time,
        status,
        output,
        entry=None,
        title=None,
        freq_weights=None,
        exog=None,
        bw_factor=1.0,
        filename="kaplan-meier.png",
    ) -> DataFrame:
        """Estimates the survival function.

        Parameters
        ----------
        time : array_like
            An array of times (censoring times or event times)
        status : array_like
            Status at the event time, status==1 is the ‘event’ (e.g. death, failure), meaning
            that the event occurs at the given value in time; status==0 indicatesthat censoring
            has occurred, meaning that the event occurs after the given value in time.
        output : str
            A string determine the type of output. Available options are ‘table’, ‘plot’.
        entry : array_like, optional An array of entry times for handling
            left truncation (the subject is not in the risk set on or before the entry time)
        title : str
            Optional title used for plots and summary output.
        freq_weights : array_like
            Optional frequency weights
        exog : array_like
            Optional, if present used to account for violation of independent censoring.
        bw_factor : float
            Band-width multiplier for kernel-based estimation. Only used if exog is provided.
        filename : str
            The name of the file where the plot will be saved. Only used if the output
            is a plot.

        Returns
        -------
        DataFrame
            The survival table.
        """
        logger.debug("surv_func()")
        command: str = utils.get_command("surv_func()", stack())
        survival_func: DataFrame = (
            sm.SurvfuncRight(  # pylint: disable=too-many-function-args
                time,
                status,
                entry,
                title,
                freq_weights,
                exog,
                bw_factor,
            )
        )
        masks = {}
        survival_table = survival_func.summary()
        t_values = (
            survival_table["num at risk"].shift(periods=1)
            - survival_table["num at risk"]
        )
        t_values = t_values < SURVIVAL_THRESHOLD
        masks["threshold"] = t_values
        masks["threshold"] = masks["threshold"].to_frame()

        masks["threshold"].insert(0, "Surv prob", t_values, True)
        masks["threshold"].insert(1, "Surv prob SE", t_values, True)
        masks["threshold"].insert(3, "num events", t_values, True)

        # build the sdc dictionary
        sdc: dict = get_table_sdc(masks, self.suppress)
        # get the status and summary
        status, summary = get_summary(sdc)
        # apply the suppression
        safe_table, outcome = apply_suppression(survival_table, masks)

        # record output
        if output == "table":
            table = self.table(
                survival_table, safe_table, status, sdc, command, summary, outcome
            )
            return table
        if output == "plot":
            plot = self.plot(
                survival_table, survival_func, filename, status, sdc, command, summary
            )
            return plot
        return None

    def table(  # pylint: disable=too-many-arguments,too-many-locals
        self, survival_table, safe_table, status, sdc, command, summary, outcome
    ):
        """Creates the survival table according to the status of suppressing."""
        if self.suppress:
            survival_table = safe_table
        self.results.add(
            status=status,
            output_type="table",
            properties={"method": "surv_func"},
            sdc=sdc,
            command=command,
            summary=summary,
            outcome=outcome,
            output=[survival_table],
        )
        return survival_table

    def plot(  # pylint: disable=too-many-arguments,too-many-locals
        self, survival_table, survival_func, filename, status, sdc, command, summary
    ):
        """Creates the survival plot according to the status of suppressing."""
        if self.suppress:
            survival_table = rounded_survival_table(survival_table)
            plot = survival_table.plot(y="rounded_survival_fun", xlim=0, ylim=0)
        else:  # pragma: no cover
            plot = survival_func.plot()

        try:
            os.makedirs("acro_artifacts")
            logger.debug("Directory acro_artifacts created successfully")
        except FileExistsError:  # pragma: no cover
            logger.debug("Directory acro_artifacts already exists")
        plt.savefig(f"acro_artifacts/{filename}")
        # record output
        self.results.add(
            status=status,
            output_type="survival plot",
            properties={"method": "surv_func"},
            sdc=sdc,
            command=command,
            summary=summary,
            outcome=pd.DataFrame(),
            output=[os.path.normpath(filename)],
        )
        return plot


def rounded_survival_table(survival_table):
    """Calculates the rounded surival function."""
    death_censored = (
        survival_table["num at risk"].shift(periods=1) - survival_table["num at risk"]
    )
    death_censored = death_censored.tolist()
    survivor = survival_table["num at risk"].tolist()
    deaths = survival_table["num events"].tolist()
    rounded_num_of_deaths = []
    rounded_num_at_risk = []
    sub_total = 0
    total_death = 0

    for i, data in enumerate(survivor):
        if i == 0:
            rounded_num_at_risk.append(data)
            rounded_num_of_deaths.append(deaths[i])
            continue
        sub_total += death_censored[i]
        total_death += deaths[i]
        if sub_total < SURVIVAL_THRESHOLD:
            rounded_num_at_risk.append(rounded_num_at_risk[i - 1])
            rounded_num_of_deaths.append(0)
        else:
            rounded_num_at_risk.append(data)
            rounded_num_of_deaths.append(total_death)
            total_death = 0
            sub_total = 0

    # calculate the surv prob
    rounded_survival_func = []
    for i, data in enumerate(rounded_num_of_deaths):
        if i == 0:
            rounded_survival_func.append(survival_table["Surv prob"][i])
            continue
        rounded_survival_func.insert(
            i,
            ((rounded_num_at_risk[i] - data) / rounded_num_at_risk[i])
            * rounded_survival_func[i - 1],
        )
    survival_table["rounded_survival_fun"] = rounded_survival_func
    return survival_table


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
        if not isinstance(aggfunc, str):  # pragma: no cover
            raise ValueError(
                f"aggfunc {aggfunc} must be:" f"{', '.join(AGGFUNC.keys())}"
            )
        if aggfunc not in AGGFUNC:  # pragma: no cover
            raise ValueError(
                f"aggfunc {aggfunc} must be: " f"{', '.join(AGGFUNC.keys())}"
            )
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
        if len(functions) < 1:  # pragma: no cover
            raise ValueError(f"invalid aggfuncs: {aggfuncs}")
        return functions
    raise ValueError("aggfuncs must be: either str or list[str]")  # pragma: no cover


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


def agg_missing(vals: Series) -> bool:
    """Aggregation function that returns whether any values are missing.

    Parameters
    ----------
    vals : Series
        Series to check for missing values.

    Returns
    -------
    bool
        Whether a missing value was found.
    """
    return vals.isna().sum() != 0


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
    # don't apply suppression if missing values are present
    elif "missing" in masks:
        mask = masks["missing"]
        outcome_df[mask.values] = "missing"
    # apply suppression masks
    else:
        for name, mask in masks.items():
            try:
                safe_df[mask.values] = np.NaN
                tmp_df = DataFrame().reindex_like(outcome_df)
                tmp_df.fillna("", inplace=True)
                tmp_df[mask.values] = name + "; "
                outcome_df += tmp_df
            except TypeError:
                logger.warning("problem mask %s is not binary", name)
        outcome_df = outcome_df.replace({"": "ok"})
    logger.info("outcome_df:\n%s", utils.prettify_table_string(outcome_df))
    return safe_df, outcome_df


def get_table_sdc(masks: dict[str, DataFrame], suppress: bool) -> dict:
    """Returns the SDC dictionary using the suppression masks.

    Parameters
    ----------
    masks : dict[str, DataFrame]
        Dictionary of tables specifying suppression masks for application.
    suppress : bool
        Whether suppression has been applied.
    """
    # summary of cells to be suppressed
    sdc: dict = {"summary": {"suppressed": suppress}, "cells": {}}
    sdc["summary"]["negative"] = 0
    sdc["summary"]["missing"] = 0
    sdc["summary"]["threshold"] = 0
    sdc["summary"]["p-ratio"] = 0
    sdc["summary"]["nk-rule"] = 0
    for name, mask in masks.items():
        sdc["summary"][name] = int(mask.to_numpy().sum())
    # positions of cells to be suppressed
    sdc["cells"]["negative"] = []
    sdc["cells"]["missing"] = []
    sdc["cells"]["threshold"] = []
    sdc["cells"]["p-ratio"] = []
    sdc["cells"]["nk-rule"] = []
    for name, mask in masks.items():
        true_positions = np.column_stack(np.where(mask.values))
        for pos in true_positions:
            row_index, col_index = pos
            sdc["cells"][name].append([int(row_index), int(col_index)])
    return sdc


def get_summary(sdc: dict) -> tuple[str, str]:
    """Returns the status and summary of the suppression masks.

    Parameters
    ----------
    sdc : dict
        Properties of the SDC checks.

    Returns
    -------
    str
        Status: {"review", "fail", "pass"}.
    str
        Summary of the suppression masks.
    """
    status: str = "pass"
    summary: str = ""
    sdc_summary = sdc["summary"]
    sup: str = "suppressed" if sdc_summary["suppressed"] else "may need suppressing"
    if sdc_summary["negative"] > 0:
        summary += "negative values found"
        status = "review"
    elif sdc_summary["missing"] > 0:
        summary += "missing values found"
        status = "review"
    else:
        if sdc_summary["threshold"] > 0:
            summary += f"threshold: {sdc_summary['threshold']} cells {sup}; "
            status = "fail"
        if sdc_summary["p-ratio"] > 0:
            summary += f"p-ratio: {sdc_summary['p-ratio']} cells {sup}; "
            status = "fail"
        if sdc_summary["nk-rule"] > 0:
            summary += f"nk-rule: {sdc_summary['nk-rule']} cells {sup}; "
            status = "fail"
    if summary != "":
        summary = f"{status}; {summary}"
    else:
        summary = status
    logger.info("get_summary(): %s", summary)
    return status, summary
