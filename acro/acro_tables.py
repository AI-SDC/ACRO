"""ACRO: Tables functions."""

# pylint: disable=too-many-lines
from __future__ import annotations

import logging
import os
import secrets
from collections.abc import Callable
from inspect import stack
from typing import Any

import numpy as np
import pandas as pd

import statsmodels.api as sm
from matplotlib import pyplot as plt
from pandas import DataFrame, Series
from pandas.api.types import CategoricalDtype
import copy

from . import utils
from .checks import SDCChecks, ChecksResults, ManyChecksResults
from .record import Records
from .aggregationfunctions import agg_mode, agg_values_are_same
from .aggregationfunctions import agg_negative,agg_missing
from .aggregationfunctions import agg_p_percent, agg_nk, agg_threshold

from .constants import SDMX_DIMENSION, SDMX_MEASURE


from .table_utils import (
    aggfunc_to_strings,
    axis_to_list, 
    collate_risk_assessments,
    get_axis_metadata,
    get_redacted_table,
    get_debugging_table_analysis,
    get_variable_metadata,
    get_variable_type_dict

)

logger = logging.getLogger("acro")




AGGFUNC: dict[str, str | Callable] = {
    "mean": "mean",
    "median": "median",
    "sum": "sum",
    "std": "std",
    "count": "count",
    "mode": agg_mode,
}




# aggregation function parameters
THRESHOLD: int = 10
SAFE_PRATIO_P: float = 0.1
SAFE_NK_N: int = 2
SAFE_NK_K: float = 0.9
CHECK_MISSING_VALUES: bool = False
ZEROS_ARE_DISCLOSIVE: bool = True

# survival analysis parameters
SURVIVAL_THRESHOLD: int = 10


class Tables:
    """Creates tabular data.

    Attributes
    ----------
    suppress : bool
        Whether to automatically apply suppression.
    """

    def __init__(self, suppress: bool) -> None:
        self.suppress: bool = suppress
        self.results: Records = Records()
        self.sdc_checks = SDCChecks({})

    def crosstab(  # pylint: disable=too-many-arguments,too-many-locals,too-complex
        self,
        index: Any,
        columns: Any,
        values: Any = None,
        rownames: Any = None,
        colnames: Any = None,
        aggfunc: str | list[str] | None = None,
        margins: bool = False,
        margins_name: str = "All",
        dropna: bool = True,
        normalize: bool | str = False,
        show_suppressed: bool = False,
    ) -> DataFrame:
        """Compute a simple cross tabulation of two (or more) factors.

        By default, computes a frequency table of the factors unless an array of
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
            THIS IS FORCED TO BE FALSE for SDC reasons
        normalize : bool, {'all', 'index', 'columns'}, or {0,1}, default False
            Normalize by dividing all values by the sum of values.
            - If passed 'all' or `True`, will normalize over all values.
            - If passed 'index' will normalize over each row.
            - If passed 'columns' will normalize over each column.
            - If margins is `True`, will also normalize margin values.
        show_suppressed : bool. default False
            Deprecated in v.10, only present for backwards compatability
            how the totals are being calculated when the suppression is true

        Returns
        -------
        DataFrame
            Cross tabulation of the data.
        """
        logger.debug("crosstab()")
        command: str = utils.get_command("crosstab()", stack())
        _ = show_suppressed #hide complaint about unused legacy variable

        
        # syntax checking
        if aggfunc is not None:
            if values is None or isinstance(values, list):
                raise ValueError(
                    "If you pass an aggregation function to crosstab "
                    "you must also specify a single values column "
                    "to aggregate over."
                )

        #standardise format to simplify later code
        index = axis_to_list(index)
        columns= axis_to_list(columns)
        
        
        # save list and dict to reduce code clutter
        args = (index, columns)
        kwargs = {
            "values": values,
            "rownames": rownames,
            "colnames": colnames,
            "aggfunc": aggfunc,
            "margins": margins,
            "margins_name": margins_name,
            "dropna": dropna,
            "normalize": normalize,
        }
        # enforce dropna=False for SDC reasons
        kwargs["dropna"] = False
        variable_metadata = get_variable_metadata(index, columns,values)
        #make object containing these that can easily be passed around
        model: dict[str, Any] = {
            "args": args, 
            "kwargs": kwargs,
            "variable_metadata":variable_metadata,
            "risk_appetite":self.sdc_checks.risk_appetite
                                }

        ## requested table
        table: DataFrame = pd.crosstab(*args, **kwargs)
        analysis_names: list[str] = aggfunc_to_strings(aggfunc)

        ## run the checks and get the masks
        collatedres=ManyChecksResults()
        for analysis in analysis_names:
            collatedres.allchecksresults[analysis] = self.sdc_checks.run_checks_for_analysis(
                analysis, model
            )

        logging.debug(get_debugging_table_analysis(collatedres.allchecksresults))

        collated_assessment = collate_risk_assessments(table, collatedres.allchecksresults)
        sdc_details: dict = collatedres.get_table_sdc()
        overall_status:str = collatedres.get_overall_status()
        allsummary:str=collatedres.get_overall_summary()
        fair_dict = collatedres.get_overall_fair()
        fair_dict.update( get_variable_type_dict(variable_metadata ))



        if self.suppress:
            table=get_redacted_table(model, collated_assessment)

        # record output
        self.results.add(
            status=overall_status,
            output_type="table",
            properties={"method": "crosstab"},
            sdc=sdc_details,
            fair=fair_dict,
            command=command,
            summary=allsummary,
            outcome=collated_assessment,
            output=[table],
            comments=[],
        )
        if self.suppress:
            justadded = f"output_{self.results.output_id - 1}"
            self.results.add_exception(
                justadded, "Suppression automatically applied where needed"
                )

        return table

    def pivot_table(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        data: DataFrame,
        values: Any = None,
        index: Any = None,
        columns: Any = None,
        aggfunc: str | list[str] = "mean",
        fill_value: Any = None,
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

        To provide consistent behaviour with different aggregation functions,
        'empty' rows or columns -i.e. that  are all NaN or 0 (count,sum) are removed.

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

        # Separate variable so param (str|list[str]) isn't reassigned to callable type (mypy)
        resolved_aggfunc: (
            str | Callable[..., Any] | list[str | Callable[..., Any]] | None
        ) = get_aggfuncs(aggfunc)
        n_agg: int = (
            1 if not isinstance(resolved_aggfunc, list) else len(resolved_aggfunc)
        )

        # requested table
        table: DataFrame = pd.pivot_table(
            data,
            values,
            index,
            columns,
            resolved_aggfunc,
            fill_value,
            margins,
            dropna,
            margins_name,
            observed,
            sort,
        )

        # delete empty rows and columns from table
        table, comments = delete_empty_rows_columns(table)

        # suppression masks to apply based on the following checks
        masks: dict[str, DataFrame] = {}

        # threshold check
        agg = [agg_threshold] * n_agg if n_agg > 1 else agg_threshold
        t_values = pd.pivot_table(
            data, values, index, columns, aggfunc=agg, margins=margins, dropna=dropna
        )
        masks["threshold"] = t_values

        if resolved_aggfunc is not None:
            # check for negative values -- currently unsupported
            agg = [agg_negative] * n_agg if n_agg > 1 else agg_negative
            negative = pd.pivot_table(
                data,
                values,
                index,
                columns,
                aggfunc=agg,
                margins=margins,
                dropna=dropna,
            )
            if negative.to_numpy().sum() > 0:
                masks["negative"] = negative
            # p-percent check
            agg = [agg_p_percent] * n_agg if n_agg > 1 else agg_p_percent
            masks["p-ratio"] = pd.pivot_table(
                data,
                values,
                index,
                columns,
                aggfunc=agg,
                margins=margins,
                dropna=dropna,
            )
            # nk values check
            agg = [agg_nk] * n_agg if n_agg > 1 else agg_nk
            masks["nk-rule"] = pd.pivot_table(
                data,
                values,
                index,
                columns,
                aggfunc=agg,
                margins=margins,
                dropna=dropna,
            )
            # check for missing values -- currently unsupported
            if CHECK_MISSING_VALUES:
                agg = [agg_missing] * n_agg if n_agg > 1 else agg_missing
                masks["missing"] = pd.pivot_table(
                    data,
                    values,
                    index,
                    columns,
                    aggfunc=agg,
                    margins=margins,
                    dropna=dropna,
                )

        # pd.pivot_table returns nan for an empty cell
        for name, mask in masks.items():
            mask.fillna(value=1, inplace=True)
            mask = mask.astype(int)
            mask.replace({0: False, 1: True}, inplace=True)
            masks[name] = mask

        # build the sdc dictionary
        sdc: dict = get_table_sdc_old(masks, self.suppress, table)
        # get the status and summary
        status, summary = get_summary(sdc)
        # apply the suppression
        safe_table, outcome = apply_suppression(table, masks)
        if self.suppress:
            table = safe_table
            if margins:
                logger.info(
                    "Disclosive cells were deleted from the dataframe "
                    "before calculating the pivot table"
                )
                table = crosstab_with_totals(
                    masks=masks,
                    aggfunc=resolved_aggfunc,
                    index=index,
                    columns=columns,
                    values=values,
                    margins=margins,
                    margins_name=margins_name,
                    dropna=dropna,
                    crosstab=False,
                    data=data,
                    fill_value=fill_value,
                    observed=observed,
                    sort=sort,
                )
        # record output
        fair: dict = {}  # TODO

        self.results.add(
            status=status,
            output_type="table",
            properties={"method": "pivot_table"},
            sdc=sdc,
            fair=fair,
            command=command,
            summary=summary,
            outcome=outcome,
            output=[table],
            comments=comments,
        )
        if self.suppress:
            justadded = f"output_{self.results.output_id - 1}"
            self.results.add_exception(
                justadded, "Suppression automatically applied where needed"
            )
        return table

    def surv_func(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        time: Any,
        status: Any,
        output: str,
        entry: Any = None,
        title: Any = None,
        freq_weights: Any = None,
        exog: Any = None,
        bw_factor: float = 1.0,
        filename: str = "kaplan-meier.png",
    ) -> DataFrame | tuple[Any, str] | None:
        """Estimate the survival function.

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
        survival_func: Any = sm.SurvfuncRight(
            time,
            status,
            entry,
            title,
            freq_weights,
            exog,
            bw_factor,
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
        sdc: dict = get_table_sdc_old(masks, self.suppress, survival_table)
        # get the status and summary
        status, summary = get_summary(sdc)
        # apply the suppression
        safe_table, outcome = apply_suppression(survival_table, masks)

        # record output
        if output == "table":
            table = self.survival_table(
                survival_table, safe_table, status, sdc, command, summary, outcome
            )
            return table
        if output == "plot":
            plot_result = self.survival_plot(
                survival_table,
                survival_func,
                filename,
                status,
                sdc,
                command,
                summary,
            )
            if plot_result is None:
                raise AssertionError(
                    "plot_result must be set when applying survival plot queries"
                )
            plot, output_filename = plot_result
            return (plot, output_filename)
        return None

    def survival_table(  # pylint: disable=too-many-arguments
        self,
        survival_table: DataFrame,
        safe_table: DataFrame,
        status: str,
        sdc: dict,
        command: str,
        summary: str,
        outcome: DataFrame,
    ) -> DataFrame:
        """Create the survival table according to the status of suppressing."""
        if self.suppress:
            survival_table = safe_table

        fair: dict = {}  # TODO

        self.results.add(
            status=status,
            output_type="table",
            properties={"method": "surv_func"},
            sdc=sdc,
            fair=fair,
            command=command,
            summary=summary,
            outcome=outcome,
            output=[survival_table],
        )
        return survival_table

    def survival_plot(  # pylint: disable=too-many-arguments
        self,
        survival_table: DataFrame,
        survival_func: Any,
        filename: str,
        status: str,
        sdc: dict,
        command: str,
        summary: str,
    ) -> tuple[Any, str] | None:
        """Create the survival plot according to the status of suppressing."""
        if self.suppress:
            survival_table = _rounded_survival_table(survival_table)
            plot = survival_table.plot(y="rounded_survival_fun", xlim=0, ylim=0)
        else:  # pragma: no cover
            plot = survival_func.plot()

        try:
            os.makedirs("acro_artifacts")
            logger.debug("Directory acro_artifacts created successfully")
        except FileExistsError:  # pragma: no cover
            logger.debug("Directory acro_artifacts already exists")

        # create a unique filename with number to avoid overwrite
        filename, extension = os.path.splitext(filename)
        if not extension:  # pragma: no cover
            logger.info("Please provide a valid file extension")
            return None  # pragma: no cover
        increment_number = 0
        while os.path.exists(
            f"acro_artifacts/{filename}_{increment_number}{extension}"
        ):  # pragma: no cover
            increment_number += 1
        unique_filename = f"acro_artifacts/{filename}_{increment_number}{extension}"

        # save the plot to the acro artifacts directory
        plt.savefig(unique_filename)

        # record output
        fair: dict = {}  # TODO

        self.results.add(
            status=status,
            output_type="survival plot",
            properties={"method": "surv_func"},
            sdc=sdc,
            fair=fair,
            command=command,
            summary=summary,
            outcome=pd.DataFrame(),
            output=[os.path.normpath(unique_filename)],
        )
        return (plot, unique_filename)

    def hist(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        data: DataFrame,
        column: str,
        by_val: Any = None,
        grid: bool = True,
        xlabelsize: int | None = None,
        xrot: float | None = None,
        ylabelsize: int | None = None,
        yrot: float | None = None,
        axis: Any = None,
        sharex: bool = False,
        sharey: bool = False,
        figsize: tuple[float, float] | None = None,
        layout: tuple[int, int] | None = None,
        bins: int | Any = 10,
        backend: str | None = None,
        legend: bool = False,
        filename: str = "histogram.png",
        **kwargs: Any,
    ) -> str | None:
        """Create a histogram from a single column.

        The dataset and the column's name should be passed to the function as parameters.
        If more than one column is used the histogram will not be calculated.

        To save the histogram plot to a file, the user can specify a filename otherwise
        'histogram.png' will be used as the filename. A number will be appended automatically
        to the filename to avoid overwriting the files.

        Parameters
        ----------
        data : DataFrame
            The pandas object holding the data.
        column : str
            The column that will be used to plot the histogram.
        by_val : object, optional
            If passed, then used to form histograms for separate groups.
        grid : bool, default True
            Whether to show axis grid lines.
        xlabelsize : int, default None
            If specified changes the x-axis label size.
        xrot : float, default None
            Rotation of x axis labels. For example, a value of 90 displays
            the x labels rotated 90 degrees clockwise.
        ylabelsize : int, default None
            If specified changes the y-axis label size.
        yrot : float, default None
            Rotation of y axis labels. For example, a value of 90 displays
            the y labels rotated 90 degrees clockwise.
        axis : Matplotlib axes object, default None
            The axes to plot the histogram on.
        sharex : bool, default True if ax is None else False
            In case subplots=True, share x axis and set some x axis labels to invisible;
            defaults to True if ax is None otherwise False if an ax is passed in.
            Note that passing in both an ax and sharex=True will alter all x axis
            labels for all subplots in a figure.
        sharey : bool, default False
            In case subplots=True, share y axis and set some y axis labels to invisible.
        figsize : tuple, optional
            The size in inches of the figure to create.
            Uses the value in matplotlib.rcParams by default.
        layout : tuple, optional
            Tuple of (rows, columns) for the layout of the histograms.
        bins : int or sequence, default 10
            Number of histogram bins to be used. If an integer is given, bins + 1 bin edges are
            calculated and returned. If bins is a sequence, gives bin edges,
            including left edge of first bin and right edge of last bin.
        backend : str, default None
            Backend to use instead of the backend specified in the option plotting.backend.
            For instance, ‘matplotlib’. Alternatively, to specify the plotting.backend for the
            whole session, set pd.options.plotting.backend.
        legend : bool, default False
            Whether to show the legend.
        filename:
            The name of the file where the plot will be saved.

        Returns
        -------
        matplotlib.Axes
            The histogram.
        str
            The name of the file where the histogram is saved.
        """
        logger.debug("hist()")
        command: str = utils.get_command("hist()", stack())

        if isinstance(data, list):  # pragma: no cover
            logger.info(
                "Calculating histogram for more than one columns is "
                "not currently supported. Please do each column separately."
            )
            return None

        freq, _ = np.histogram(
            data[column], bins, range=(data[column].min(), data[column].max())
        )

        # threshold check
        threshold_mask = freq < THRESHOLD

        # plot the histogram
        if np.any(threshold_mask):  # the column is disclosive
            status = "fail"
            if self.suppress:
                logger.warning(
                    "Histogram will not be shown as the %s column is disclosive.",
                    column,
                )
            else:  # pragma: no cover
                data.hist(
                    column=column,
                    by=by_val,
                    grid=grid,
                    xlabelsize=xlabelsize,
                    xrot=xrot,
                    ylabelsize=ylabelsize,
                    yrot=yrot,
                    ax=axis,
                    sharex=sharex,
                    sharey=sharey,
                    figsize=figsize,
                    layout=layout,
                    bins=bins,
                    backend=backend,
                    legend=legend,
                    **kwargs,
                )
        else:
            status = "review"
            data.hist(
                column=column,
                by=by_val,
                grid=grid,
                xlabelsize=xlabelsize,
                xrot=xrot,
                ylabelsize=ylabelsize,
                yrot=yrot,
                ax=axis,
                sharex=sharex,
                sharey=sharey,
                figsize=figsize,
                layout=layout,
                bins=bins,
                backend=backend,
                legend=legend,
                **kwargs,
            )
        logger.info("status: %s", status)

        # create the summary
        min_value = data[column].min()
        max_value = data[column].max()
        summary = (
            f"Please check the minimum and the maximum values. "
            f"The minimum value of the {column} column is: {min_value}. "
            f"The maximum value of the {column} column is: {max_value}"
        )

        # create the acro_artifacts directory to save the plot in it
        try:
            os.makedirs("acro_artifacts")
            logger.debug("Directory acro_artifacts created successfully")
        except FileExistsError:  # pragma: no cover
            logger.debug("Directory acro_artifacts already exists")

        # create a unique filename with number to avoid overwrite
        filename, extension = os.path.splitext(filename)
        if not extension:  # pragma: no cover
            logger.info("Please provide a valid file extension")
            return None
        increment_number = 0
        while os.path.exists(
            f"acro_artifacts/{filename}_{increment_number}{extension}"
        ):  # pragma: no cover
            increment_number += 1
        unique_filename = f"acro_artifacts/{filename}_{increment_number}{extension}"

        # save the plot to the acro artifacts directory
        plt.savefig(unique_filename)

        # record output
        fair: dict = {}  # TODO

        self.results.add(
            status=status,
            output_type="histogram",
            properties={"method": "histogram"},
            sdc={},
            fair=fair,
            command=command,
            summary=summary,
            outcome=pd.DataFrame(),
            output=[os.path.normpath(unique_filename)],
        )
        return unique_filename

    def pie(
        self,
        data: pd.DataFrame,
        column: str,
        filename: str = "pie.png",
        **kwargs: Any,
    ) -> str | None:
        """Create a pie chart from a categorical column.

        Per-category counts are computed using value_counts(). If any
        category has fewer observations than THRESHOLD, the output is
        marked as "fail" and the chart is suppressed when
        suppress=True. Otherwise the chart is produced and marked as
        "review".

        The chart is saved to acro_artifacts/ with a unique incrementing
        number appended to avoid overwriting existing files.

        Parameters
        ----------
        data : DataFrame
            The pandas DataFrame holding the data.
        column : str
            The column whose category proportions will be plotted.
        filename : str, default 'pie.png'
            The name of the file where the chart will be saved.
        **kwargs
            Additional keyword arguments forwarded to
            matplotlib.axes.Axes.pie().

        Returns
        -------
        str
            The path to the saved pie chart file.
        """
        logger.debug("pie()")
        command: str = utils.get_command("pie()", stack())

        # COMPUTE PRE-CATEGORY COUNTS
        counts = data[column].value_counts()

        # THRESHOLD CHECK - same as hist() logic
        threshold_mask = counts < THRESHOLD

        if np.any(threshold_mask):
            status = "fail"
            if self.suppress:
                logger.warning(
                    "Pie chart will not be shown as the %s column is disclosive.",
                    column,
                )
            else:  # pragma: no cover
                _, ax = plt.subplots()
                ax.pie(counts.values, labels=counts.index, **kwargs)
        else:
            status = "review"
            _, ax = plt.subplots()
            ax.pie(counts.values, labels=counts.index, **kwargs)

        logger.info("status: %s", status)

        # CREATE SUMMARY
        summary = f"Pie chart of {column}. Categories and counts: {counts.to_dict()}."

        # CREATE acro_artifacts DIRECTORY to save plot in
        try:
            os.makedirs("acro_artifacts")
            logger.debug("Directory acro_artifacts created successfully")
        except FileExistsError:  # pragma: no cover
            logger.debug("Directory acro_artifacts already exists")

        # CREATE UNIQUE FILENAME to avoid overwrite

        filename, extension = os.path.splitext(filename)
        if not extension:  # pragma: no cover
            logger.info("Please provide a valid file extension")
            return None
        increment_number = 0

        while os.path.exists(
            f"acro_artifacts/{filename}_{increment_number}{extension}"
        ):  # pragma: no cover
            increment_number += 1
        unique_filename = f"acro_artifacts/{filename}_{increment_number}{extension}"

        # SAVE PLOT to acro_artifacts directory
        plt.savefig(unique_filename)

        # RECORD OUTPUT
        fair: dict = {}  # TODO
        self.results.add(
            status=status,
            output_type="pie chart",
            properties={"method": "pie"},
            sdc={},
            fair=fair,
            command=command,
            summary=summary,
            outcome=pd.DataFrame(),
            output=[os.path.normpath(unique_filename)],
        )

        return unique_filename




def _rounded_survival_table(
    survival_table: pd.DataFrame,
    num_at_risk_col: str = "num at risk",
    num_events_col: str = "num events",
) -> pd.DataFrame:
    """Calculate the rounded survival function.

    Internal helper function for survival analysis with disclosure control.
    Applies rounding to survival tables to prevent disclosure of small counts.

    Parameters
    ----------
    survival_table : pd.DataFrame
        The survival table containing survival analysis results.
    num_at_risk_col : str, default "num at risk"
        Name of the column containing number at risk values.
    num_events_col : str, default "num events"
        Name of the column containing number of events.

    Returns
    -------
    pd.DataFrame
        The survival table with rounded survival function added.
    """
    death_censored = (
        survival_table[num_at_risk_col].shift(periods=1)
        - survival_table[num_at_risk_col]
    )
    death_censored = death_censored.tolist()
    survivor = survival_table[num_at_risk_col].tolist()
    deaths = survival_table[num_events_col].tolist()
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
            rounded_survival_func.append(survival_table["Surv prob"].iloc[i])
            continue
        rounded_survival_func.insert(
            i,
            ((rounded_num_at_risk[i] - data) / rounded_num_at_risk[i])
            * rounded_survival_func[i - 1],
        )
    survival_table["rounded_survival_fun"] = rounded_survival_func
    return survival_table








