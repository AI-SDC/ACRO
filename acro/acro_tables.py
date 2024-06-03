"""ACRO: Tables functions."""

# pylint: disable=too-many-lines
from __future__ import annotations

import logging
import os
import secrets
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


def mode_aggfunc(values) -> Series:
    """Calculate the mode or randomly selects one of the modes from a pandas Series.

    Parameters
    ----------
    values : Series
        A pandas Series for which to calculate the mode.

    Returns
    -------
    Series
        The mode. If multiple modes, randomly selects and returns one of the modes.
    """
    modes = values.mode()
    return secrets.choice(modes)


AGGFUNC: dict[str, str | Callable] = {
    "mean": "mean",
    "median": "median",
    "sum": "sum",
    "std": "std",
    "count": "count",
    "mode": mode_aggfunc,
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
        show_suppressed=False,
    ) -> DataFrame:
        """Compute a simple cross tabulation of two (or more) factors.

        By default, computes a frequency table of the factors unless an array of
        values and an aggregation function are passed.

        To provide consistent behaviour with different aggregation functions,
        'empty' rows or columns -i.e. that  are all NaN or 0 (count,sum) are removed.

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
        show_suppressed : bool. default False
            how the totals are being calculated when the suppression is true

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
        agg_func = get_aggfuncs(aggfunc)

        # requested table
        table: DataFrame = pd.crosstab(
            index,
            columns,
            values,
            rownames,
            colnames,
            agg_func,
            margins,
            margins_name,
            dropna,
            normalize,
        )
        comments: list[str] = []
        # do not delete empty rows and columns from table if the aggfunc is mode
        if agg_func is not mode_aggfunc:
            # delete empty rows and columns from table
            table, comments = delete_empty_rows_columns(table)
        masks = create_crosstab_masks(
            index,
            columns,
            values,
            rownames,
            colnames,
            agg_func,
            margins,
            margins_name,
            dropna,
            normalize,
        )
        # build the sdc dictionary
        sdc: dict = get_table_sdc(masks, self.suppress)
        # get the status and summary
        status, summary = get_summary(sdc)
        # apply the suppression
        safe_table, outcome = apply_suppression(table, masks)
        if self.suppress:
            table = safe_table
            if margins:
                if show_suppressed:
                    table = manual_crossstab_with_totals(
                        table,
                        aggfunc,
                        index,
                        columns,
                        values,
                        rownames,
                        colnames,
                        margins,
                        margins_name,
                        dropna,
                        normalize,
                    )
                else:
                    table = crosstab_with_totals(
                        masks=masks,
                        aggfunc=agg_func,
                        index=index,
                        columns=columns,
                        values=values,
                        margins=margins,
                        margins_name=margins_name,
                        dropna=dropna,
                        crosstab=True,
                        rownames=rownames,
                        colnames=colnames,
                        normalize=normalize,
                    )

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
            comments=comments,
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

        aggfunc = get_aggfuncs(aggfunc)  # convert string(s) to function(s)
        n_agg: int = 1 if not isinstance(aggfunc, list) else len(aggfunc)

        # requested table
        table: DataFrame = pd.pivot_table(
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

        # delete empty rows and columns from table
        table, comments = delete_empty_rows_columns(table)

        # suppression masks to apply based on the following checks
        masks: dict[str, DataFrame] = {}

        # threshold check
        agg = [agg_threshold] * n_agg if n_agg > 1 else agg_threshold
        t_values = pd.pivot_table(
            data, values, index, columns, aggfunc=agg, margins=margins
        )
        masks["threshold"] = t_values

        if aggfunc is not None:
            # check for negative values -- currently unsupported
            agg = [agg_negative] * n_agg if n_agg > 1 else agg_negative
            negative = pd.pivot_table(
                data, values, index, columns, aggfunc=agg, margins=margins
            )
            if negative.to_numpy().sum() > 0:
                masks["negative"] = negative
            # p-percent check
            agg = [agg_p_percent] * n_agg if n_agg > 1 else agg_p_percent
            masks["p-ratio"] = pd.pivot_table(
                data, values, index, columns, aggfunc=agg, margins=margins
            )
            # nk values check
            agg = [agg_nk] * n_agg if n_agg > 1 else agg_nk
            masks["nk-rule"] = pd.pivot_table(
                data, values, index, columns, aggfunc=agg, margins=margins
            )
            # check for missing values -- currently unsupported
            if CHECK_MISSING_VALUES:
                agg = [agg_missing] * n_agg if n_agg > 1 else agg_missing
                masks["missing"] = pd.pivot_table(
                    data, values, index, columns, aggfunc=agg, margins=margins
                )

        # pd.pivot_table returns nan for an empty cell
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
            if margins:
                logger.info(
                    "Disclosive cells were deleted from the dataframe "
                    "before calculating the pivot table"
                )
                table = crosstab_with_totals(
                    masks=masks,
                    aggfunc=aggfunc,
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
        self.results.add(
            status=status,
            output_type="table",
            properties={"method": "pivot_table"},
            sdc=sdc,
            command=command,
            summary=summary,
            outcome=outcome,
            output=[table],
            comments=comments,
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
        survival_func: DataFrame = sm.SurvfuncRight(
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
        sdc: dict = get_table_sdc(masks, self.suppress)
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
            plot, filename = self.survival_plot(
                survival_table, survival_func, filename, status, sdc, command, summary
            )
            return (plot, filename)
        return None

    def survival_table(  # pylint: disable=too-many-arguments
        self, survival_table, safe_table, status, sdc, command, summary, outcome
    ):
        """Create the survival table according to the status of suppressing."""
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

    def survival_plot(  # pylint: disable=too-many-arguments
        self, survival_table, survival_func, filename, status, sdc, command, summary
    ):
        """Create the survival plot according to the status of suppressing."""
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
        self.results.add(
            status=status,
            output_type="survival plot",
            properties={"method": "surv_func"},
            sdc=sdc,
            command=command,
            summary=summary,
            outcome=pd.DataFrame(),
            output=[os.path.normpath(unique_filename)],
        )
        return (plot, unique_filename)

    def hist(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        data,
        column,
        by_val=None,
        grid=True,
        xlabelsize=None,
        xrot=None,
        ylabelsize=None,
        yrot=None,
        axis=None,
        sharex=False,
        sharey=False,
        figsize=None,
        layout=None,
        bins=10,
        backend=None,
        legend=False,
        filename="histogram.png",
        **kwargs,
    ):
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
        self.results.add(
            status=status,
            output_type="histogram",
            properties={"method": "histogram"},
            sdc={},
            command=command,
            summary=summary,
            outcome=pd.DataFrame(),
            output=[os.path.normpath(unique_filename)],
        )
        return unique_filename


def create_crosstab_masks(  # pylint: disable=too-many-arguments,too-many-locals
    index,
    columns,
    values,
    rownames,
    colnames,
    agg_func,
    margins,
    margins_name,
    dropna,
    normalize,
):
    """Create masks to specify the cells to suppress."""
    # suppression masks to apply based on the following checks
    masks: dict[str, DataFrame] = {}

    if agg_func is not None:
        # create lists with single entry for when there is only one aggfunc
        count_funcs: list[str | Callable] = [AGGFUNC["count"]]
        neg_funcs: list[Callable] = [agg_negative]
        pperc_funcs: list[Callable] = [agg_p_percent]
        nk_funcs: list[Callable] = [agg_nk]
        missing_funcs: list[Callable] = [agg_missing]
        # then expand them to deal with extra columns as needed
        if isinstance(agg_func, list):
            num = len(agg_func)
            count_funcs.extend([AGGFUNC["count"] for i in range(1, num)])
            neg_funcs.extend([agg_negative for i in range(1, num)])
            pperc_funcs.extend([agg_p_percent for i in range(1, num)])
            nk_funcs.extend([agg_nk for i in range(1, num)])
            missing_funcs.extend([agg_missing for i in range(1, num)])
        # threshold check- doesn't matter what we pass for value
        if agg_func is mode_aggfunc:
            # check that all observations dont have the same value
            logger.info(
                "If there are multiple modes, one of them is randomly selected and displayed."
            )
            masks["all-values-are-same"] = pd.crosstab(
                index,
                columns,
                values,
                aggfunc=agg_values_are_same,
                margins=margins,
                dropna=dropna,
            )
        else:
            t_values = pd.crosstab(
                index,
                columns,
                values=values,
                rownames=rownames,
                colnames=colnames,
                aggfunc=count_funcs,
                margins=margins,
                margins_name=margins_name,
                dropna=dropna,
                normalize=normalize,
            )

            # drop empty columns and rows
            if dropna or margins:
                empty_cols_mask = t_values.sum(axis=0) == 0
                empty_rows_mask = t_values.sum(axis=1) == 0

                t_values = t_values.loc[:, ~empty_cols_mask]
                t_values = t_values.loc[~empty_rows_mask, :]

            t_values = t_values < THRESHOLD
            masks["threshold"] = t_values
            # check for negative values -- currently unsupported
            negative = pd.crosstab(
                index, columns, values, aggfunc=neg_funcs, margins=margins
            )
            if negative.to_numpy().sum() > 0:
                masks["negative"] = negative
            # p-percent check
            masks["p-ratio"] = pd.crosstab(
                index,
                columns,
                values,
                aggfunc=pperc_funcs,
                margins=margins,
                dropna=dropna,
            )
            # nk values check
            masks["nk-rule"] = pd.crosstab(
                index, columns, values, aggfunc=nk_funcs, margins=margins, dropna=dropna
            )
            # check for missing values -- currently unsupported
            if CHECK_MISSING_VALUES:
                masks["missing"] = pd.crosstab(
                    index, columns, values, aggfunc=missing_funcs, margins=margins
                )
    else:
        # threshold check- doesn't matter what we pass for value
        t_values = pd.crosstab(
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
    return masks


def delete_empty_rows_columns(table: DataFrame) -> tuple[DataFrame, list[str]]:
    """Delete empty rows and columns from table.

    Parameters
    ----------
    table : DataFrame
        The table where the empty rows and columns will be deleted from.

    Returns
    -------
    DataFrame
        The resulting table where the empty columns and rows were deleted.
    list[str]
        A comment showing information about the deleted columns and rows.
    """
    deleted_rows = []
    deleted_cols = []
    # define empty columns and rows using boolean masks
    empty_cols_mask = table.sum(axis=0) == 0
    empty_rows_mask = table.sum(axis=1) == 0

    deleted_cols = list(table.columns[empty_cols_mask])
    table = table.loc[:, ~empty_cols_mask]
    deleted_rows = list(table.index[empty_rows_mask])
    table = table.loc[~empty_rows_mask, :]

    # create a message with the deleted column's names
    comments = []
    if deleted_cols:
        msg_cols = ", ".join(str(col) for col in deleted_cols)
        comments.append(f"Empty columns: {msg_cols} were deleted.")
    if deleted_rows:
        msg_rows = ", ".join(str(row) for row in deleted_rows)
        comments.append(f"Empty rows: {msg_rows} were deleted.")
    if comments:
        logger.info(" ".join(comments))
    return (table, comments)


def rounded_survival_table(survival_table):
    """Calculate the rounded surival function."""
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
            rounded_survival_func.append(survival_table["Surv prob"].iloc[i])
            continue
        rounded_survival_func.insert(
            i,
            ((rounded_num_at_risk[i] - data) / rounded_num_at_risk[i])
            * rounded_survival_func[i - 1],
        )
    survival_table["rounded_survival_fun"] = rounded_survival_func
    return survival_table


def get_aggfunc(aggfunc: str | None) -> str | Callable | None:
    """Check whether an aggregation function is allowed and return the appropriate function.

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
) -> str | Callable | list[str | Callable] | None:
    """Check whether aggregation functions are allowed and return appropriate functions.

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
        functions: list[str | Callable] = []
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
    """Return whether any values are negative.

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
    """Return whether any values are missing.

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
    """Return whether the p percent rule is violated.

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
    assert isinstance(vals, Series), "vals is not a pandas series"
    sorted_vals = vals.sort_values(ascending=False)
    total: float = sorted_vals.sum()
    if total <= 0.0 or vals.size <= 1:
        logger.debug("not calculating ppercent due to small size")
        return bool(ZEROS_ARE_DISCLOSIVE)
    sub_total = total - sorted_vals.iloc[0] - sorted_vals.iloc[1]
    p_val: float = sub_total / sorted_vals.iloc[0] if total > 0 else 1
    return p_val < SAFE_PRATIO_P


def agg_nk(vals: Series) -> bool:
    """Return whether the top n items account for more than k percent of the total.

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
    """Return whether the number of contributors is below a threshold.

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


def agg_values_are_same(vals: Series) -> bool:
    """Return whether all observations having the same value.

    Parameters
    ----------
    vals : Series
        Series to calculate if all the values are the same.

    Returns
    -------
    bool
        Whether the values are the same.
    """
    # the observations are not the same
    return vals.nunique(dropna=True) == 1


def apply_suppression(
    table: DataFrame, masks: dict[str, DataFrame]
) -> tuple[DataFrame, DataFrame]:
    """Apply suppression to a table.

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
            except ValueError as error:  # pragma: no cover
                error_message = (
                    f"An error occurred with the following details"
                    f":\n Name: {name}\n Mask: {mask}\n Table: {table}"
                )
                raise ValueError(error_message) from error

        outcome_df = outcome_df.replace({"": "ok"})
    logger.info("outcome_df:\n%s", utils.prettify_table_string(outcome_df))
    return safe_df, outcome_df


def get_table_sdc(masks: dict[str, DataFrame], suppress: bool) -> dict:
    """Return the SDC dictionary using the suppression masks.

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
    sdc["summary"]["all-values-are-same"] = 0
    for name, mask in masks.items():
        sdc["summary"][name] = int(np.nansum(mask.to_numpy()))
    # positions of cells to be suppressed
    sdc["cells"]["negative"] = []
    sdc["cells"]["missing"] = []
    sdc["cells"]["threshold"] = []
    sdc["cells"]["p-ratio"] = []
    sdc["cells"]["nk-rule"] = []
    sdc["cells"]["all-values-are-same"] = []
    for name, mask in masks.items():
        true_positions = np.column_stack(np.where(mask.values))
        for pos in true_positions:
            row_index, col_index = pos
            sdc["cells"][name].append([int(row_index), int(col_index)])
    return sdc


def get_summary(sdc: dict) -> tuple[str, str]:
    """Return the status and summary of the suppression masks.

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
        if sdc_summary["all-values-are-same"] > 0:
            summary += (
                f"all-values-are-same: {sdc_summary['all-values-are-same']} "
                f"cells {sup}; "
            )
            status = "fail"
    if summary != "":
        summary = f"{status}; {summary}"
    else:
        summary = status
    logger.info("get_summary(): %s", summary)
    return status, summary


def get_queries(masks, aggfunc) -> list[str]:
    """Return a list of the boolean conditions for each true cell in the suppression masks.

    Parameters
    ----------
    masks : dict[str, DataFrame]
        Dictionary of tables specifying suppression masks for application.
    aggfunc : str | None
        The aggregation function

    Returns
    -------
    str
        The boolean conditions for each true cell in the suppression masks.
    """
    # initialize a list to store queries for true cells
    true_cell_queries = []
    for _, mask in masks.items():
        # drop the name of the mask
        if aggfunc is not None:
            if mask.columns.nlevels > 1:
                mask = mask.droplevel(0, axis=1)
        # identify level names for rows and columns
        index_level_names = mask.index.names
        column_level_names = mask.columns.names
        # iterate through the masks to identify the true cells and extract queries
        for col_index, col_label in enumerate(mask.columns):
            for row_index, row_label in enumerate(mask.index):
                if mask.iloc[row_index, col_index]:
                    if isinstance(row_label, tuple):
                        index_query = " & ".join(
                            [
                                (
                                    f"({level} == {val})"
                                    if isinstance(val, (int, float))
                                    else f'({level} == "{val}")'
                                )
                                for level, val in zip(index_level_names, row_label)
                            ]
                        )
                    else:
                        index_query = " & ".join(
                            [
                                (
                                    f"({index_level_names} == {row_label})"
                                    if isinstance(row_label, (int, float))
                                    else (f"({index_level_names}" f'== "{row_label}")')
                                )
                            ]
                        )
                    if isinstance(col_label, tuple):
                        column_query = " & ".join(
                            [
                                (
                                    f"({level} == {val})"
                                    if isinstance(val, (int, float))
                                    else f'({level} == "{val}")'
                                )
                                for level, val in zip(column_level_names, col_label)
                            ]
                        )
                    else:
                        column_query = " & ".join(
                            [
                                (
                                    f"({column_level_names} == {col_label})"
                                    if isinstance(col_label, (int, float))
                                    else (f"({column_level_names}" f'== "{col_label}")')
                                )
                            ]
                        )
                    query = f"{index_query} & {column_query}"
                    true_cell_queries.append(query)
    # delete the duplication
    true_cell_queries = list(set(true_cell_queries))
    return true_cell_queries


def create_dataframe(index, columns) -> DataFrame:
    """Combine the index and columns in a dataframe and return the dataframe.

    Parameters
    ----------
    index : array-like, Series, or list of arrays/Series
        Values to group by in the rows.
    columns : array-like, Series, or list of arrays/Series
        Values to group by in the columns.

    Returns
    -------
    Dataframe
        Table of the index and columns combined.
    """
    empty_dataframe = pd.DataFrame([])

    index_df = empty_dataframe
    try:
        if isinstance(index, list):
            index_df = pd.concat(index, axis=1)
        elif isinstance(index, pd.Series):
            index_df = pd.DataFrame({index.name: index})
    except ValueError:
        index_df = empty_dataframe

    columns_df = empty_dataframe
    try:
        if isinstance(columns, list):
            columns_df = pd.concat(columns, axis=1)
        elif isinstance(columns, pd.Series):
            columns_df = pd.DataFrame({columns.name: columns})
    except ValueError:
        columns_df = empty_dataframe

    try:
        data = pd.concat([index_df, columns_df], axis=1)
    except ValueError:
        data = empty_dataframe

    return data


def get_index_columns(index, columns, data) -> tuple[list | Series, list | Series]:
    """Get the index and columns from the data dataframe.

    Parameters
    ----------
    index : array-like, Series, or list of arrays/Series
        Values to group by in the rows.
    columns : array-like, Series, or list of arrays/Series
        Values to group by in the columns.
    data : dataframe
        Table of the index and columns combined.

    Returns
    -------
    List | Series
        The index extracted from the data.
    List | Series
        The columns extracted from the data.
    """
    shift = 1
    if isinstance(index, list):
        index_new = []
        for i in range(len(index)):
            index_new.append(data.iloc[:, i])
        shift = len(index)
    else:
        index_new = data[index.name]

    if isinstance(columns, list):
        columns_new = []
        for i in range(shift, shift + len(columns)):
            columns_new.append(data.iloc[:, i])
    else:
        columns_new = data[columns.name]
    return index_new, columns_new


def crosstab_with_totals(  # pylint: disable=too-many-arguments,too-many-locals
    masks,
    aggfunc,
    index,
    columns,
    values,
    margins,
    margins_name,
    dropna,
    crosstab,
    rownames=None,
    colnames=None,
    normalize=False,
    data=None,
    fill_value=None,
    observed=False,
    sort=False,
) -> DataFrame:
    """Recalculate the crosstab table when margins are true and suppression is true.

    Parameters
    ----------
    masks : dict[str, DataFrame]
        Dictionary of tables specifying suppression masks for application.
    aggfunc : str | None
        The aggregation function.
    index : array-like, Series, or list of arrays/Series
        Values to group by in the rows.
    columns : array-like, Series, or list of arrays/Series
        Values to group by in the columns.
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
        Crosstabulation of data
    """
    true_cell_queries = get_queries(masks, aggfunc)
    if crosstab:
        data = create_dataframe(index, columns)
    # apply the queries to the data
    for query in true_cell_queries:
        query = str(query).replace("['", "").replace("']", "")
        data = data.query(f"not ({query})")

    # get the index and columns from the data after the queries are applied
    try:
        if crosstab:
            index_new, columns_new = get_index_columns(index, columns, data)
            # apply the crosstab with the new index and columns
            table = pd.crosstab(
                index_new,
                columns_new,
                values=values,
                rownames=rownames,
                colnames=colnames,
                aggfunc=aggfunc,
                margins=margins,
                margins_name=margins_name,
                dropna=dropna,
                normalize=normalize,
            )

            table, _ = delete_empty_rows_columns(table)
            masks = create_crosstab_masks(
                index_new,
                columns_new,
                values,
                rownames,
                colnames,
                aggfunc,
                margins,
                margins_name,
                dropna,
                normalize,
            )

            # Force the apply_suppression not to display the outcome dataframe
            previous_level = logger.getEffectiveLevel()
            logger.setLevel(logging.WARNING)
            # apply the suppression
            table, _ = apply_suppression(table, masks)
            logger.setLevel(previous_level)

        else:
            table = pd.pivot_table(
                data=data,
                values=values,
                index=index,
                columns=columns,
                aggfunc=aggfunc,
                fill_value=fill_value,
                margins=margins,
                dropna=dropna,
                margins_name=margins_name,
                observed=observed,
                sort=sort,
            )

    except ValueError:
        logger.warning(
            "All the cells in this data are disclosive."
            " Thus suppression can not be applied"
        )
        return None
    return table


def manual_crossstab_with_totals(  # pylint: disable=too-many-arguments
    table,
    aggfunc,
    index,
    columns,
    values,
    rownames,
    colnames,
    margins,
    margins_name,
    dropna,
    normalize,
) -> DataFrame:
    """Recalculate the crosstab table when margins are true and suppression is true.

    Parameters
    ----------
    table : Dataframe
        The suppressed table.
    aggfunc : str | None
        The aggregation function.
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
        Crosstabulation of data
    """
    if isinstance(aggfunc, list):
        logger.warning(
            "We can not calculate the margins with a list of aggregation functions. "
            "Please create a table for each aggregation function"
        )
        return None
    if aggfunc is None or aggfunc == "sum" or aggfunc == "count":
        table = recalculate_margin(table, margins_name)

    elif aggfunc == "mean":
        count_table = pd.crosstab(
            index=index,
            columns=columns,
            values=values,
            rownames=rownames,
            colnames=colnames,
            aggfunc="count",
            margins=margins,
            margins_name=margins_name,
            dropna=dropna,
            normalize=normalize,
        )
        # suppress the cells in the count by mimicking the suppressed cells in the table
        count_table = count_table.where(table.notna(), other=np.nan)
        # delete any columns from the count_table that are not in the table
        columns_to_keep = table.columns
        count_table = count_table[columns_to_keep]
        if count_table.index.is_numeric():  # pragma: no cover
            count_table = count_table.sort_index(axis=1)
        # recalculate the margins considering the nan values
        count_table = recalculate_margin(count_table, margins_name)
        # multiply the table by the count table
        table[margins_name] = 1
        table.loc[margins_name, :] = 1
        multip_table = count_table * table
        if multip_table.index.is_numeric():  # pragma: no cover
            multip_table = multip_table.sort_index(axis=1)
        # calculate the margins columns
        table[margins_name] = (
            multip_table.drop(margins_name, axis=1).sum(axis=1)
            / multip_table[margins_name]
        )
        # calculate the margins row
        if not isinstance(count_table.index, pd.MultiIndex):  # single row
            table.loc[margins_name, :] = (
                multip_table.drop(margins_name, axis=0).sum()
                / multip_table.loc[margins_name, :]
            )
        else:  # multiple rows
            table.loc[(margins_name, ""), :] = (
                multip_table.drop(margins_name, axis=0).sum()
                / multip_table.loc[(margins_name, ""), :]
            )
        # calculate the grand margin
        if not isinstance(count_table.columns, pd.MultiIndex) and not isinstance(
            count_table.index, pd.MultiIndex
        ):  # single column, single row
            table.loc[margins_name, margins_name] = (
                multip_table.drop(index=margins_name, columns=margins_name).sum().sum()
            ) / multip_table.loc[margins_name, margins_name]
        else:  # multiple columns or multiple rows
            table.loc[margins_name, margins_name] = (
                multip_table.drop(index=margins_name, columns=margins_name).sum().sum()
            ) / multip_table.loc[margins_name, margins_name][0]

    elif aggfunc == "std":
        table = table.drop(margins_name, axis=1)
        table = table.drop(margins_name, axis=0)
        logger.warning(
            "The margins with the std agg func can not be calculated. "
            "Please set the show_suppressed to false to calculate it."
        )
        return table
    return table


def recalculate_margin(table, margins_name) -> DataFrame:
    """Recalculate the margins in a table.

    Parameters
    ----------
    table : Dataframe
        The suppressed table.
    margins_name : str, default 'All'
        Name of the row/column that will contain the totals

    Returns
    -------
    DataFrame
        Table with new calculated margins
    """
    table = table.drop(margins_name, axis=1)
    rows_total = table.sum(axis=1)
    table.loc[:, margins_name] = rows_total
    if isinstance(table.index, pd.MultiIndex):
        table = table.drop(margins_name, axis=0)
        cols_total = table.sum(axis=0)
        table.loc[(margins_name, ""), :] = cols_total
    else:
        table = table.drop(margins_name, axis=0)
        cols_total = table.sum(axis=0)
        table.loc[margins_name] = cols_total
    return table
