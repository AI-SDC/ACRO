"""ACRO: Tables functions."""

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

from . import utils
from .constants import ARTIFACTS_DIR
from .record import Records
from .utils import ALLOWED_MITIGATIONS

logger = logging.getLogger("acro")


def mode_aggfunc(values: Series) -> Series:
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

# default base for the 'round' mitigation strategy
SAFE_ROUND_BASE: int = 5

# Re-export so existing callers that imported from this module keep working.
_ALLOWED_MITIGATIONS = ALLOWED_MITIGATIONS


class Tables:
    """Creates tabular data.

    Attributes
    ----------
    mitigation : str
        The disclosure-control strategy applied to outputs, one of ``"none"``,
        ``"suppress"``, ``"round"``.
    round_base : int
        The base to round to when ``mitigation == "round"``. Must be a positive integer.
    suppress : bool
        Backward-compatible alias. ``True`` is equivalent to ``mitigation == "suppress"``.
    """

    def __init__(
        self,
        suppress: bool = False,
        mitigation: str | None = None,
    ) -> None:
        """Initialise a Tables instance with the chosen mitigation strategy."""
        self._mitigation: str = "none"
        self._round_base: int = SAFE_ROUND_BASE
        if mitigation is None:
            mitigation = "suppress" if suppress else "none"
        self.mitigation = mitigation
        self.results: Records = Records()

    @property
    def mitigation(self) -> str:
        """Return the current mitigation strategy."""
        return self._mitigation

    @mitigation.setter
    def mitigation(self, value: str) -> None:
        if value not in ALLOWED_MITIGATIONS:
            logger.info(
                "Sorry, I don't recognise the mitigation %r. "
                "It should be one of %s. You can turn them on later using "
                "enable_suppression() or enable_rounding(). "
                "For now I am proceeding with no mitigation.",
                value,
                sorted(ALLOWED_MITIGATIONS),
            )
            self._mitigation = "none"
            return
        self._mitigation = value

    @property
    def round_base(self) -> int:
        """Return the base used by the ``round`` mitigation strategy."""
        return self._round_base

    @round_base.setter
    def round_base(self, value: int) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            logger.info(
                "round_base must be a positive integer, got %r. "
                "Falling back to the default value of %d.",
                value,
                SAFE_ROUND_BASE,
            )
            self._round_base = SAFE_ROUND_BASE
            return
        self._round_base = value

    @property
    def suppress(self) -> bool:
        """Return True iff the active mitigation strategy is 'suppress'."""
        return self._mitigation == "suppress"

    @suppress.setter
    def suppress(self, value: bool) -> None:
        if value:
            self._mitigation = "suppress"
        elif self._mitigation == "suppress":
            self._mitigation = "none"
        elif self._mitigation == "round":
            logger.info(
                "Setting suppress=False had no effect because mitigation is "
                "currently 'round'. Use disable_rounding() to turn off rounding."
            )

    def _record_table_output(
        self,
        method: str,
        status: str,
        sdc: dict,
        command: str,
        summary: str,
        outcome: DataFrame,
        table: DataFrame,
        comments: list[str],
    ) -> None:
        """Record a table output and attach any mitigation exception note."""
        properties: dict[str, Any] = {
            "method": method,
            "mitigation": self._mitigation,
        }
        if self._mitigation == "round":
            properties["round_base"] = self._round_base
        self.results.add(
            status=status,
            output_type="table",
            properties=properties,
            sdc=sdc,
            command=command,
            summary=summary,
            outcome=outcome,
            output=[table],
            comments=comments,
        )
        if self._mitigation == "suppress":
            just_added = f"output_{self.results.output_id - 1}"
            self.results.add_exception(
                just_added, "Suppression automatically applied where needed"
            )
        elif self._mitigation == "round":
            just_added = f"output_{self.results.output_id - 1}"
            self.results.add_exception(
                just_added,
                f"Rounding automatically applied to nearest {self._round_base}",
            )

    def crosstab(
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
        # When rounding, compute the table without margins first and then
        # derive margins from the rounded cells (so the inner cells add up
        # to the displayed totals). See append_rounded_margins() / Jim
        # Smith's review on PR #381.
        recompute_margins = margins and self._mitigation == "round"
        pandas_margins = False if recompute_margins else margins

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
            pandas_margins,
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
        sdc: dict = get_table_sdc(
            masks,
            self.suppress,
            table,
            mitigation=self._mitigation,
            round_base=self._round_base,
        )
        # get the status and summary
        status, summary = get_summary(sdc)
        # apply the suppression
        safe_table, outcome = apply_suppression(table, masks)
        if self._mitigation == "suppress":
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
            sdc = get_table_sdc(
                masks,
                self.suppress,
                table,
                mitigation=self._mitigation,
                round_base=self._round_base,
            )
        elif self._mitigation == "round":
            table = round_table(table, self._round_base)
            if recompute_margins:
                table = append_rounded_margins(
                    table, agg_func, margins_name, self._round_base
                )

        self._record_table_output(
            method="crosstab",
            status=status,
            sdc=sdc,
            command=command,
            summary=summary,
            outcome=outcome,
            table=table,
            comments=comments,
        )
        return table

    def pivot_table(
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

        # When rounding, compute the table without pandas-managed margins
        # and re-derive them from the rounded cells; see append_rounded_margins()
        # / Jim Smith's review on PR #381.
        recompute_margins = margins and self._mitigation == "round"
        pandas_margins = False if recompute_margins else margins

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
            pandas_margins,
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
        sdc: dict = get_table_sdc(
            masks,
            self.suppress,
            table,
            mitigation=self._mitigation,
            round_base=self._round_base,
        )
        # get the status and summary
        status, summary = get_summary(sdc)
        # apply the suppression
        safe_table, outcome = apply_suppression(table, masks)
        if self._mitigation == "suppress":
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
            sdc = get_table_sdc(
                masks,
                self.suppress,
                table,
                mitigation=self._mitigation,
                round_base=self._round_base,
            )
        elif self._mitigation == "round":
            table = round_table(table, self._round_base)
            if recompute_margins:
                table = append_rounded_margins(
                    table, resolved_aggfunc, margins_name, self._round_base
                )
        self._record_table_output(
            method="pivot_table",
            status=status,
            sdc=sdc,
            command=command,
            summary=summary,
            outcome=outcome,
            table=table,
            comments=comments,
        )
        return table

    def surv_func(
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
        sdc: dict = get_table_sdc(masks, self.suppress, survival_table)
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

    def survival_table(
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

    def survival_plot(
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
        if utils.is_blocked_extension(filename, self.results.blocked_extensions):
            return None
        if self.suppress:
            survival_table = _rounded_survival_table(survival_table)
            plot = survival_table.plot(y="rounded_survival_fun", xlim=0, ylim=0)
        else:  # pragma: no cover
            plot = survival_func.plot()

        try:
            os.makedirs(ARTIFACTS_DIR)
            logger.debug("Directory %s created successfully", ARTIFACTS_DIR)
        except FileExistsError:  # pragma: no cover
            logger.debug("Directory %s already exists", ARTIFACTS_DIR)

        # create a unique filename with number to avoid overwrite
        filename, extension = os.path.splitext(filename)
        if not extension:  # pragma: no cover
            logger.info("Please provide a valid file extension")
            return None  # pragma: no cover
        increment_number = 0
        while os.path.exists(
            f"{ARTIFACTS_DIR}/{filename}_{increment_number}{extension}"
        ):  # pragma: no cover
            increment_number += 1
        unique_filename = f"{ARTIFACTS_DIR}/{filename}_{increment_number}{extension}"

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

    def hist(
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

        Notes
        -----
        When ``zeros_are_disclosive`` is set to ``False`` in the config, empty
        bins (count == 0) are excluded from the disclosure threshold check.
        This avoids flagging histograms as disclosive solely because outliers
        in a wide-spread column produced empty tail bins.
        """
        logger.debug("hist()")
        if utils.is_blocked_extension(filename, self.results.blocked_extensions):
            return None
        command: str = utils.get_command("hist()", stack())

        if isinstance(data, list):  # pragma: no cover
            logger.info(
                "Calculating histogram for more than one columns is "
                "not currently supported. Please do each column separately."
            )
            return None

        col_series = data[column].dropna()
        if col_series.empty:  # pragma: no cover
            logger.warning("Column %s is empty after dropping NaN.", column)
            self.results.add(
                status="fail",
                output_type="histogram",
                properties={"method": "histogram"},
                sdc={},
                command=command,
                summary="fail; empty column after dropping NaN",
                outcome=pd.DataFrame(),
                output=[],
            )
            return None

        col_min = float(col_series.min())
        col_max = float(col_series.max())
        masks, bin_edges, freq, left_count, right_count = _build_histogram_masks(
            col_series, bins, col_min, col_max
        )
        by_val, mismatch, sub_stats = _analyse_by_val_ranges(data, column, by_val)

        sdc = get_histogram_sdc(
            masks,
            self.suppress,
            bin_edges,
            freq,
            col_min,
            col_max,
            left_count,
            right_count,
            mismatch,
            sub_stats,
        )
        status, summary = get_histogram_summary(sdc, column, col_min, col_max)
        outcome = build_histogram_outcome(bin_edges, freq, masks)
        logger.info("status: %s", status)

        # plot the histogram (skip when suppressed and disclosive)
        if status == "fail" and self.suppress:
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

        # create the artifacts directory to save the plot in it
        try:
            os.makedirs(ARTIFACTS_DIR)
            logger.debug("Directory %s created successfully", ARTIFACTS_DIR)
        except FileExistsError:  # pragma: no cover
            logger.debug("Directory %s already exists", ARTIFACTS_DIR)

        # create a unique filename with number to avoid overwrite
        filename, extension = os.path.splitext(filename)
        if not extension:  # pragma: no cover
            logger.info("Please provide a valid file extension")
            return None
        increment_number = 0
        while os.path.exists(
            f"{ARTIFACTS_DIR}/{filename}_{increment_number}{extension}"
        ):  # pragma: no cover
            increment_number += 1
        unique_filename = f"{ARTIFACTS_DIR}/{filename}_{increment_number}{extension}"

        # save the plot to the acro artifacts directory
        plt.savefig(unique_filename)

        # record output
        self.results.add(
            status=status,
            output_type="histogram",
            properties={"method": "histogram"},
            sdc=sdc,
            command=command,
            summary=summary,
            outcome=outcome,
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

        The chart is saved to the artifacts directory with a unique incrementing
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
        if utils.is_blocked_extension(filename, self.results.blocked_extensions):
            return None
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

        # CREATE artifacts DIRECTORY to save plot in
        try:
            os.makedirs(ARTIFACTS_DIR)
            logger.debug("Directory %s created successfully", ARTIFACTS_DIR)
        except FileExistsError:  # pragma: no cover
            logger.debug("Directory %s already exists", ARTIFACTS_DIR)

        # CREATE UNIQUE FILENAME to avoid overwrite

        filename, extension = os.path.splitext(filename)
        if not extension:  # pragma: no cover
            logger.info("Please provide a valid file extension")
            return None
        increment_number = 0

        while os.path.exists(
            f"{ARTIFACTS_DIR}/{filename}_{increment_number}{extension}"
        ):  # pragma: no cover
            increment_number += 1
        unique_filename = f"{ARTIFACTS_DIR}/{filename}_{increment_number}{extension}"

        # SAVE PLOT to artifacts directory
        plt.savefig(unique_filename)

        # RECORD OUTPUT
        self.results.add(
            status=status,
            output_type="pie chart",
            properties={"method": "pie"},
            sdc={},
            command=command,
            summary=summary,
            outcome=pd.DataFrame(),
            output=[os.path.normpath(unique_filename)],
        )

        return unique_filename


def create_crosstab_masks(
    index: Any,
    columns: Any,
    values: Any,
    rownames: Any,
    colnames: Any,
    agg_func: str | Callable | list[str | Callable] | None,
    margins: bool,
    margins_name: str,
    dropna: bool,
    normalize: bool | str,
) -> dict[str, DataFrame]:
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
    deleted_rows: list[Any] = []
    deleted_cols: list[Any] = []
    # define empty columns and rows using boolean masks
    empty_cols_mask: Any = table.sum(axis=0) == 0
    empty_rows_mask: Any = table.sum(axis=1) == 0

    deleted_cols = list(table.columns[empty_cols_mask])
    table = table.loc[:, ~empty_cols_mask]
    deleted_rows = list(table.index[empty_rows_mask])
    table = table.loc[~empty_rows_mask, :]

    # create a message with the deleted column's names
    comments: list[str] = []
    if deleted_cols:
        msg_cols = ", ".join(str(col) for col in deleted_cols)
        comments.append(f"Empty columns: {msg_cols} were deleted.")
    if deleted_rows:
        msg_rows = ", ".join(str(row) for row in deleted_rows)
        comments.append(f"Empty rows: {msg_rows} were deleted.")
    if comments:
        logger.info(" ".join(comments))
    return (table, comments)


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
    func: str | Callable | None = None
    if aggfunc is not None:
        if not isinstance(aggfunc, str):  # pragma: no cover
            raise ValueError(f"aggfunc {aggfunc} must be:{', '.join(AGGFUNC.keys())}")
        if aggfunc not in AGGFUNC:  # pragma: no cover
            raise ValueError(f"aggfunc {aggfunc} must be: {', '.join(AGGFUNC.keys())}")
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


def _broadcast_mask_to_multiindex(
    m: DataFrame, table: DataFrame, top_levels: list
) -> DataFrame:
    """Replicate a flat (or single-group) mask across each aggfunc top-level group.

    Parameters
    ----------
    m : DataFrame
        Flat mask with base columns only.
    table : DataFrame
        MultiIndex table whose top-level groups define the replication targets.
    top_levels : list
        Ordered list of unique top-level values from the table's MultiIndex columns.

    Returns
    -------
    DataFrame
        A mask with MultiIndex columns matching the table's column structure.
    """
    frames = []
    for lvl in top_levels:
        sub_cols = table[lvl].columns
        sub_m = m.reindex(index=table.index, columns=sub_cols, fill_value=False)
        sub_m.columns = pd.MultiIndex.from_product([[lvl], sub_m.columns])
        frames.append(sub_m)
    return pd.concat(frames, axis=1)


def _align_mask_columns(m: DataFrame, table: DataFrame) -> DataFrame:
    """Align the columns of mask *m* to match those of *table*.

    Parameters
    ----------
    m : DataFrame
        A single suppression mask.
    table : DataFrame
        The output table the mask should match.

    Returns
    -------
    DataFrame
        The mask with columns aligned to the table.
    """
    table_nlevels = table.columns.nlevels
    mask_nlevels = m.columns.nlevels

    if table_nlevels == 2 and mask_nlevels == 2:
        table_top = table.columns.get_level_values(0).unique().tolist()
        mask_top = m.columns.get_level_values(0).unique().tolist()
        if len(mask_top) == 1 and len(table_top) > 1:
            n_base = len(table.columns.get_level_values(1).unique())
            base_mask = m.iloc[:, :n_base]
            flat_cols = base_mask.columns.get_level_values(1)
            base_mask = pd.DataFrame(base_mask.values, index=m.index, columns=flat_cols)
            m = _broadcast_mask_to_multiindex(base_mask, table, table_top)
    elif mask_nlevels < table_nlevels:
        top_levels = table.columns.get_level_values(0).unique().tolist()
        m = _broadcast_mask_to_multiindex(m, table, top_levels)
    elif mask_nlevels > table_nlevels:
        m = m.droplevel(0, axis=1)

    return m


def align_masks(table: DataFrame, masks: dict[str, DataFrame]) -> dict[str, DataFrame]:
    """Align masks to the table's index and columns.

    Parameters
    ----------
    table : DataFrame
        Table to align masks to.
    masks : dict[str, DataFrame]
        Dictionary of tables specifying suppression masks.

    Returns
    -------
    dict[str, DataFrame]
        The aligned masks.
    """
    aligned_masks = {}
    for name, mask in masks.items():
        m = mask

        # handle index level mismatch
        if m.index.nlevels > table.index.nlevels:
            m = m.droplevel(0, axis=0)

        m = _align_mask_columns(m, table)

        # reindex if still necessary
        if not m.index.equals(table.index) or not m.columns.equals(table.columns):
            try:
                m = m.reindex(
                    index=table.index, columns=table.columns, fill_value=False
                )
            except (ValueError, TypeError):  # pragma: no cover
                logger.warning("Could not reindex mask %s", name)
        aligned_masks[name] = m
    return aligned_masks


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
    # align masks
    masks = align_masks(table, masks)
    safe_df = table.copy()
    outcome_df = DataFrame(index=table.index, columns=table.columns)
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
                safe_df[mask.values] = np.nan
                tmp_df = DataFrame(index=outcome_df.index, columns=outcome_df.columns)
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


def round_table(table: DataFrame, base: int) -> DataFrame:
    """Round numeric cells to the nearest multiple of ``base`` (NaNs preserved)."""
    logger.debug("round_table(base=%s)", base)
    if base is None or base <= 0:
        return table.copy()
    numeric = table.select_dtypes(include=["number"])
    rounded = (numeric / base).round() * base
    result = table.copy()
    result[numeric.columns] = rounded
    return result


def _aggfunc_name(aggfunc: Any) -> str | None:
    """Return a string name for an aggfunc value, or None if not derivable."""
    if isinstance(aggfunc, str):
        return aggfunc
    if callable(aggfunc) and hasattr(aggfunc, "__name__"):
        return aggfunc.__name__
    return None


def append_rounded_margins(
    rounded_table: DataFrame,
    aggfunc: Any,
    margins_name: str,
    base: int,
) -> DataFrame:
    """Append row/column/grand-total margins to a pre-rounded table.

    Following Jim Smith's review on PR #381: once cells have been rounded,
    margins are computed by aggregating the rounded cells (so rounded inner
    cells add up to the displayed totals) and then rounded again to ``base``
    so the whole output respects the rounding base.

    Conceptually this is the same as the "synthetic-data" approach Jim
    described - exploding the rounded table into one record per cell and
    re-running ``pd.crosstab(margins=True)`` - but implemented directly on
    the rounded DataFrame to keep it simple. We currently support single-
    level row and column indices; multi-level or list-of-aggfunc tables fall
    back to returning the table without margins.
    """
    if isinstance(aggfunc, list):
        logger.info(
            "Cannot add margins to a rounded table when multiple aggregation "
            "functions were requested; returning the table without margins."
        )
        return rounded_table
    if rounded_table.index.nlevels > 1 or rounded_table.columns.nlevels > 1:
        logger.info(
            "Margin recomputation for hierarchical row/column indexes is not "
            "yet supported under rounding; returning the table without margins."
        )
        return rounded_table

    name = _aggfunc_name(aggfunc)
    if aggfunc is None or name in (None, "count", "sum", "mode_aggfunc"):
        agg_method = "sum"
    elif name == "mean":
        agg_method = "mean"
    elif name == "median":
        agg_method = "median"
    else:
        logger.info(
            "Margin recomputation for aggfunc %r is not supported under "
            "rounding; returning the table without margins.",
            name,
        )
        return rounded_table

    numeric = rounded_table.select_dtypes(include=["number"])
    row_margin = getattr(numeric, agg_method)(axis=1, skipna=True)
    col_margin = getattr(numeric, agg_method)(axis=0, skipna=True)
    grand = float(getattr(numeric.stack(), agg_method)())

    if base and base > 0:
        row_margin = (row_margin / base).round() * base
        col_margin = (col_margin / base).round() * base
        grand = round(grand / base) * base

    table = rounded_table.copy()
    table[margins_name] = row_margin
    new_row = col_margin.reindex(table.columns)
    new_row[margins_name] = grand
    table.loc[margins_name] = new_row
    return table


def get_table_sdc(
    masks: dict[str, DataFrame],
    suppress: bool,
    table: DataFrame | None = None,
    *,
    mitigation: str | None = None,
    round_base: int = 0,
) -> dict[str, Any]:
    """Return the SDC dictionary using the suppression masks.

    Parameters
    ----------
    masks : dict[str, DataFrame]
        Dictionary of tables specifying suppression masks for application.
    suppress : bool
        Whether suppression has been applied (legacy flag, kept for
        back-compat). When ``mitigation`` is provided it takes precedence.
    table : DataFrame, optional
        The table to align masks to.
    mitigation : str, optional
        The mitigation strategy applied to the output, one of ``"none"``,
        ``"suppress"``, ``"round"``. If ``None``, derived from ``suppress``.
    round_base : int, default 0
        The base used when ``mitigation == "round"``; ignored otherwise.
    """
    if mitigation is None:
        mitigation = "suppress" if suppress else "none"
    if table is not None:
        masks = align_masks(table, masks)
    # summary of cells to be suppressed
    sdc: dict[str, Any] = {
        "summary": {
            "suppressed": mitigation == "suppress",
            "mitigation": mitigation,
            "round_base": round_base if mitigation == "round" else 0,
        },
        "cells": {},
    }
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


def _rounded_summary(sdc_summary: dict[str, Any]) -> tuple[str, str]:
    """Build the status/summary for a rounded output."""
    status = "review"
    summary = f"rounded to nearest {sdc_summary.get('round_base', 0)}; "
    for name in ("threshold", "p-ratio", "nk-rule", "all-values-are-same"):
        count = sdc_summary.get(name, 0)
        if count > 0:
            summary += f"{name}: {count} cells rounded; "
    if sdc_summary.get("negative", 0) > 0:
        summary += "negative values found; "
    if sdc_summary.get("missing", 0) > 0:
        summary += "missing values found; "
    return status, f"{status}; {summary}"


def get_summary(sdc: dict[str, Any]) -> tuple[str, str]:
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
    mitigation: str = sdc_summary.get(
        "mitigation", "suppress" if sdc_summary.get("suppressed") else "none"
    )
    if mitigation == "round":
        status, summary = _rounded_summary(sdc_summary)
        logger.info("get_summary(): %s", summary)
        return status, summary
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
            status = "review" if sdc_summary["suppressed"] else "fail"
        if sdc_summary["p-ratio"] > 0:
            summary += f"p-ratio: {sdc_summary['p-ratio']} cells {sup}; "
            status = "review" if sdc_summary["suppressed"] else "fail"
        if sdc_summary["nk-rule"] > 0:
            summary += f"nk-rule: {sdc_summary['nk-rule']} cells {sup}; "
            status = "review" if sdc_summary["suppressed"] else "fail"
        if sdc_summary["all-values-are-same"] > 0:
            summary += (
                f"all-values-are-same: {sdc_summary['all-values-are-same']} "
                f"cells {sup}; "
            )
            status = "review" if sdc_summary["suppressed"] else "fail"
    if summary != "":
        summary = f"{status}; {summary}"
    else:
        summary = status
    logger.info("get_summary(): %s", summary)
    return status, summary


def _python_scalar(value: Any) -> Any:
    """Cast a numpy scalar to its Python equivalent for JSON serialisation."""
    return value.item() if hasattr(value, "item") else value


def _build_histogram_masks(
    col_series: Series,
    bins: int | Any,
    col_min: float,
    col_max: float,
) -> tuple[dict[str, np.ndarray], np.ndarray, np.ndarray, int, int]:
    """Compute histogram frequencies, edges, and the three per-bin risk masks."""
    if isinstance(bins, int):
        freq, bin_edges = np.histogram(col_series, bins, range=(col_min, col_max))
    else:
        freq, bin_edges = np.histogram(col_series, bins)

    threshold_mask = freq < THRESHOLD
    if not ZEROS_ARE_DISCLOSIVE:
        empty_bins = freq == 0
        threshold_mask &= ~empty_bins
        if np.any(empty_bins):
            logger.debug(
                "%d empty bin(s) excluded from threshold check",
                int(np.sum(empty_bins)),
            )
    masks: dict[str, np.ndarray] = {"threshold": threshold_mask}

    edge_mask = np.zeros_like(freq, dtype=bool)
    edge_mask[0] = freq[0] < THRESHOLD
    edge_mask[-1] = freq[-1] < THRESHOLD
    masks["edge-bin"] = edge_mask

    left_count = int((col_series == col_min).sum())
    right_count = int((col_series == col_max).sum())
    leak_mask = np.zeros_like(freq, dtype=bool)
    if bin_edges[0] == col_min and left_count < THRESHOLD:
        leak_mask[0] = True
    if bin_edges[-1] == col_max and right_count < THRESHOLD:
        leak_mask[-1] = True
    masks["extreme-value-leak"] = leak_mask

    return masks, bin_edges, freq, left_count, right_count


def _analyse_by_val_ranges(
    data: DataFrame, column: str, by_val: Any
) -> tuple[Any, bool, DataFrame | None]:
    """Compute per-subgroup min/max/count and whether ranges disagree."""
    if by_val is None:
        return by_val, False, None
    if isinstance(by_val, pd.Series) and by_val.name is None:
        by_val = by_val.rename("by_val")
    sub_stats = (
        data.groupby(by_val)[column]
        .agg(["min", "max", "count"])
        .dropna(subset=["min", "max"])
    )
    mismatch = bool(sub_stats["min"].nunique() > 1 or sub_stats["max"].nunique() > 1)
    return by_val, mismatch, sub_stats


def get_histogram_sdc(
    masks: dict[str, np.ndarray],
    suppress: bool,
    bin_edges: np.ndarray,
    freq: np.ndarray,
    col_min: float,
    col_max: float,
    left_count: int,
    right_count: int,
    mismatch: bool,
    sub_stats: DataFrame | None,
) -> dict[str, Any]:
    """Build the SDC dict for a histogram output.

    When ``by_val`` is set, ``bin_edges``, ``counts``, and bin-indexed masks
    describe the pooled aggregate across all subgroups; per-subgroup leak is
    captured in ``by-val-range-mismatch`` and ``by_val_detail``.
    """
    sdc: dict[str, Any] = {
        "summary": {
            "suppressed": bool(suppress),
            "threshold": int(masks["threshold"].sum()),
            "edge-bin": int(masks["edge-bin"].sum()),
            "extreme-value-leak": int(masks["extreme-value-leak"].sum()),
            "by-val-range-mismatch": bool(mismatch),
        },
        "bins": {
            "threshold": [int(i) for i in np.where(masks["threshold"])[0]],
            "edge-bin": [int(i) for i in np.where(masks["edge-bin"])[0]],
            "extreme-value-leak": [
                int(i) for i in np.where(masks["extreme-value-leak"])[0]
            ],
        },
        "bin_edges": [float(e) for e in bin_edges],
        "counts": [int(c) for c in freq],
        "column_min": float(col_min),
        "column_max": float(col_max),
        "min_count": int(left_count),
        "max_count": int(right_count),
        "by_val_detail": {},
    }
    if sub_stats is not None and not sub_stats.empty:
        raw = sub_stats.reset_index().to_dict(orient="list")
        sdc["by_val_detail"] = {
            str(key): [_python_scalar(v) for v in values] for key, values in raw.items()
        }
    return sdc


def get_histogram_summary(
    sdc: dict[str, Any], column: str, col_min: float, col_max: float
) -> tuple[str, str]:
    """Return status and summary for a histogram's SDC dict."""
    status = "review"
    summary = ""
    s = sdc["summary"]
    sup = "suppressed" if s["suppressed"] else "may need suppressing"

    if s["edge-bin"] > 0:
        summary += f"edge-bin: {s['edge-bin']} edge bin(s) below threshold {sup}; "
        status = "fail"
    if s["threshold"] > 0:
        summary += f"threshold: {s['threshold']} bins {sup}; "
        status = "fail"
    if s["extreme-value-leak"] > 0:
        summary += (
            f"extreme-value-leak: {s['extreme-value-leak']} edge(s) reveal exact "
            f"min/max (min count={sdc['min_count']}, max count={sdc['max_count']}); "
        )
        status = "fail"
    if s["by-val-range-mismatch"]:
        summary += (
            "by-val-range-mismatch: subgroup x-ranges differ "
            "(aggregate counts shown; per-subgroup ranges in by_val_detail); "
        )
        status = "fail"

    summary += f"min={col_min}, max={col_max} for column {column}"
    summary = f"{status}; {summary}"
    logger.info("get_histogram_summary(): %s", summary)
    return status, summary


def build_histogram_outcome(
    bin_edges: np.ndarray, freq: np.ndarray, masks: dict[str, np.ndarray]
) -> DataFrame:
    """Return a per-bin outcome DataFrame labelling each bin with the checks it failed."""
    order = ["threshold", "edge-bin", "extreme-value-leak"]
    rows = []
    for i, count in enumerate(freq):
        failed = [name for name in order if masks[name][i]]
        rows.append(
            {
                "bin_index": int(i),
                "bin_left": float(bin_edges[i]),
                "bin_right": float(bin_edges[i + 1]),
                "count": int(count),
                "checks_failed": "; ".join(failed) if failed else "ok",
            }
        )
    return DataFrame(rows)


def add_backticks(name: str) -> str:
    """Add backticks to a name if it contains spaces and doesn't have them.

    Parameters
    ----------
    name : str
        The name to add backticks to.

    Returns
    -------
    str
        The name with backticks if needed.
    """
    if isinstance(name, str) and " " in name and not name.startswith("`"):
        return f"`{name}`"
    return name  # pragma: no cover


def _format_label_condition(level_names: list[Any], label: Any) -> list[str]:
    """Format a label into a list of condition strings.

    Parameters
    ----------
    level_names : list
        The names of the levels.
    label : tuple or scalar
        The label value(s).

    Returns
    -------
    list[str]
        List of condition strings for this label.
    """
    parts = []
    if isinstance(label, tuple):
        for level, val in zip(level_names, label, strict=False):
            level = add_backticks(str(level))
            if isinstance(val, (int, float)):
                parts.append(f"({level} == {val})")
            else:
                parts.append(f'({level} == "{val}")')
    else:
        level = add_backticks(str(level_names[0]))
        if isinstance(label, (int, float)):
            parts.append(f"({level} == {label})")
        else:
            parts.append(f'({level} == "{label}")')
    return parts


def _get_cell_query(
    mask: DataFrame,
    row_index: int,
    col_index: int,
    index_level_names: list[Any],
    column_level_names: list[Any],
) -> str | None:
    """Generate a query string for a cell if it's marked as true in the mask.

    Parameters
    ----------
    mask : DataFrame
        The suppression mask.
    row_index : int
        Row index.
    col_index : int
        Column index.
    index_level_names : list
        Names of index levels.
    column_level_names : list
        Names of column levels.

    Returns
    -------
    str or None
        Query string if cell is true, None otherwise.
    """
    if not mask.iloc[row_index, col_index]:
        return None

    parts = []
    row_label = mask.index[row_index]
    col_label = mask.columns[col_index]

    parts.extend(_format_label_condition(index_level_names, row_label))
    parts.extend(_format_label_condition(column_level_names, col_label))

    return " & ".join(parts)


def get_queries(
    masks: dict[str, DataFrame],
    aggfunc: str | Callable | list[str | Callable] | None,
) -> list[str]:
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
    true_cell_queries = []
    for _, mask in masks.items():
        if aggfunc is not None:
            if mask.columns.nlevels > 1:
                mask = mask.droplevel(0, axis=1)
        index_level_names = mask.index.names
        column_level_names = mask.columns.names
        for col_index, _ in enumerate(mask.columns):
            for row_index, _ in enumerate(mask.index):
                query = _get_cell_query(
                    mask, row_index, col_index, index_level_names, column_level_names
                )
                if query is not None:
                    true_cell_queries.append(query)
    true_cell_queries = list(set(true_cell_queries))
    return true_cell_queries


def create_dataframe(index: Any, columns: Any) -> DataFrame:
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
    except (ValueError, TypeError):
        index_df = empty_dataframe

    columns_df = empty_dataframe
    try:
        if isinstance(columns, list):
            columns_df = pd.concat(columns, axis=1)
        elif isinstance(columns, pd.Series):
            columns_df = pd.DataFrame({columns.name: columns})
    except (ValueError, TypeError):
        columns_df = empty_dataframe

    try:
        data = pd.concat([index_df, columns_df], axis=1)
    except (ValueError, TypeError):  # pragma: no cover
        data = empty_dataframe

    return data


def get_index_columns(
    index: Any, columns: Any, data: DataFrame
) -> tuple[list[Any] | Series, list[Any] | Series]:
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


def crosstab_with_totals(
    masks: dict[str, DataFrame],
    aggfunc: Any,
    index: Any,
    columns: Any,
    values: Any,
    margins: bool,
    margins_name: str,
    dropna: bool,
    crosstab: bool,
    rownames: Any = None,
    colnames: Any = None,
    normalize: bool | str = False,
    data: DataFrame | None = None,
    fill_value: Any = None,
    observed: bool = False,
    sort: bool = False,
) -> DataFrame | None:
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
    if data is None:
        raise AssertionError("data must be set when applying crosstab queries")
    for query in true_cell_queries:
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

            if table.empty:
                raise ValueError("empty table")

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


def manual_crossstab_with_totals(
    table: DataFrame,
    aggfunc: str | list[str] | None,
    index: Any,
    columns: Any,
    values: Any,
    rownames: Any,
    colnames: Any,
    margins: bool,
    margins_name: str,
    dropna: bool,
    normalize: bool | str,
) -> DataFrame | None:
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


def recalculate_margin(table: DataFrame, margins_name: str) -> DataFrame:
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
