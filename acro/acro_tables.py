"""ACRO: Tables functions."""

from __future__ import annotations

import logging
import os
from inspect import stack
from typing import Any

import pandas as pd
import statsmodels.api as sm
from matplotlib import pyplot as plt
from pandas import DataFrame

from . import utils
from .record import Records
from .sdc_agg_funcs import agg_mode
from .sdcchecks import ManyChecksResults, SDCChecks, SDCEvidence
from .table_utils import (
    AGGFUNC_TO_TYPE,
    aggfunc_to_strings,
    append_rounded_margins,
    axis_to_list,
    collate_risk_assessments,
    get_debugging_table_analysis,
    get_redacted_pivottable,
    get_redacted_table,
    round_table,
)
from .tablemodeldetails import TableModelDetails
from .utils import ALLOWED_MITIGATIONS

logger = logging.getLogger("acro")


# survival analysis parameters
SURVIVAL_THRESHOLD: int = 10

# default base for the 'round' mitigation strategy
SAFE_ROUND_BASE: int = 5

# Re-export so existing callers that imported from this module keep working.
_ALLOWED_MITIGATIONS = ALLOWED_MITIGATIONS
AGGFUNC = AGGFUNC_TO_TYPE  # Alias for backwards compatibility


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
        self.sdc_checks = SDCChecks({})
        self.federated: bool = False
        self._federated_evidence: dict = {}

    def _store_federated_evidence(
        self,
        uid: str,
        command: str,
        analysis_names: list,
        evidence: SDCEvidence,
    ) -> None:
        """Accumulate evidence for a single output when running in federated mode.

        Parameters
        ----------
        uid : str
            The output identifier that will be written to evidence.json
            (e.g. ``"output_0"``).
        command : str
            The researcher's original command string (for traceability).
        analysis_names : list[str]
            Names of the analyses performed (e.g. ``["FrequencyTable"]``).
        evidence : SDCEvidence
            The collected evidence object to serialise.
        """
        tables: dict[str, str] = {}
        for name, df in evidence.interim_tables.items():
            tables[name] = df.to_csv()

        dof_val = None
        if evidence.dof is not None:
            dof_val = (
                evidence.dof.to_csv()
                if isinstance(evidence.dof, pd.DataFrame)
                else evidence.dof
            )

        self._federated_evidence[uid] = {
            "command": command,
            "analysis_names": analysis_names,
            "variable_types": evidence.variable_type_dict,
            "dof": dof_val,
            "interim_tables": tables,
        }

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
        fair: dict,
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
            fair=fair,
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
            self.results.results[just_added].status = "review"

        elif self._mitigation == "round":
            just_added = f"output_{self.results.output_id - 1}"
            self.results.add_exception(
                just_added,
                f"Rounding automatically applied to nearest {self._round_base}",
            )
            self.results.results[just_added].status = "review"

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
            Deprecated in v.10, only present for backwards compatibility
            how the totals are being calculated when the suppression is true

        Returns
        -------
        DataFrame
            Cross tabulation of the data.
        """
        logger.debug("crosstab()")
        command: str = utils.get_command("crosstab()", stack())
        _ = show_suppressed  # hide complaint about unused legacy variable
        _ = dropna  # hide complaint about unused param

        #### Step 0 standardise syntax and capture all relevant information
        #### in a TableModelDetails instance
        #### this could be done in a separate function if the parameters
        #### to the call can be cleanly passed across
        #### resulting details are held in a TableModelDetails object
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

        # standardise format to simplify later code
        index = axis_to_list(index)
        columns = axis_to_list(columns)

        # When rounding, compute the table without margins first and then
        # derive margins from the rounded cells (so the inner cells add up
        # to the displayed totals). See append_rounded_margins() / Jim
        # Smith's review on PR #381.
        recompute_margins = margins and self._mitigation == "round"
        pandas_margins = False if recompute_margins else margins

        # save list and dict to reduce code clutter
        args = (index, columns)
        kwargs = {
            "values": values,
            "rownames": rownames,
            "colnames": colnames,
            "aggfunc": aggfunc,
            "margins": pandas_margins,
            "margins_name": margins_name,
            "dropna": False,  # enforced for SDC reasons
            "normalize": normalize,
        }
        if aggfunc == "mode":
            aggfunc = "agg_mode"
            kwargs["aggfunc"] = agg_mode

        model_details = TableModelDetails(
            index=index,
            columns=columns,
            values=kwargs["values"],
            thekwargs=kwargs,
            risk_appetite=self.sdc_checks.risk_appetite,
            command="crosstab",
        )

        #### Step 1  make the requested output
        table: DataFrame = pd.crosstab(*args, **kwargs)

        #### Step 2 run the checks and gather evidence
        analysis_names: list[str] = aggfunc_to_strings(aggfunc)
        evidence: SDCEvidence = self.sdc_checks.get_evidence_forall_analyses(
            analysis_names, model_details
        )

        if self.federated:
            uid = f"output_{self.results.output_id}"
            self._store_federated_evidence(uid, command, analysis_names, evidence)
            self.results.output_id += 1
            return table

        # extra layer of loops as requested tables may have more than one agg func
        collatedres = ManyChecksResults()
        for analysis in analysis_names:
            collatedres.allchecksresults[analysis] = (
                self.sdc_checks.run_checks_for_analysis(
                    analysis, evidence, model_details
                )
            )

        logging.debug(get_debugging_table_analysis(collatedres.allchecksresults))

        collated_assessment = collate_risk_assessments(
            table, collatedres.allchecksresults
        )

        fair_dict = collatedres.get_overall_fair()
        fair_dict.update(model_details.get_variable_type_dict())

        #### Step 3 apply mitigations
        if self.suppress:
            table = get_redacted_table(model_details, collated_assessment)
        elif self._mitigation == "round":
            table = round_table(table, self._round_base)
            if recompute_margins:
                table = append_rounded_margins(
                    table, aggfunc, margins_name, self._round_base
                )

        ##### Step 4: store evidence & output
        self._record_table_output(
            method="crosstab",
            status=collatedres.get_overall_status(),
            sdc=collatedres.get_table_sdc(),
            fair=fair_dict,
            command=command,
            summary=collatedres.get_overall_summary(),
            outcome=collated_assessment,
            table=table,
            comments=[],
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
        **kwargs: dict,
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
        **kwargs : dict|None default =None
            Optional keyword arguments to pass to aggfunc.

        Returns
        -------
        DataFrame
            Cross tabulation of the data.
        """
        _ = dropna  # hide complaint about unused param

        logger.debug("pivot_table()")
        command: str = utils.get_command("pivot_table()", stack())

        #### Step 0 standardise syntax and capture all relevant information
        # syntax checking
        if values is None:
            raise ValueError(
                "You must  specify at least one values column "
                "to report statistics about."
            )

        if isinstance(values, list) and len(values) > 1:
            raise ValueError(
                "Specifying multiple values columns is not currently supported."
            )

        # standardise format to simplify later code
        index = axis_to_list(index)
        columns = axis_to_list(columns)

        # When rounding, compute the table without pandas-managed margins
        # and re-derive them from the rounded cells; see append_rounded_margins()

        recompute_margins = margins and self._mitigation == "round"
        pandas_margins = False if recompute_margins else margins
        # save list and dict to reduce code clutter

        thiskwargs = {
            "values": values,
            "index": index,
            "columns": columns,
            "aggfunc": aggfunc,
            "fill_value": fill_value,
            "margins": pandas_margins,
            "dropna": False,  # forced for sdc reasons
            "margins_name": margins_name,
            "observed": observed,
            "sort": sort,
        }
        # use our mode function

        if aggfunc == "mode":
            aggfunc = "agg_mode"
            thiskwargs["aggfunc"] = agg_mode

        thiskwargs.update(kwargs)

        series_index, series_columns = [], []
        for name in index:
            series_index.append(data[name])
        if len(columns) > 0:
            for name in columns:
                series_columns.append(data[name])

        # Extract single series if values is a list with one element
        values_series = data[values[0]] if isinstance(values, list) else data[values]

        model_details = TableModelDetails(
            index=series_index,
            columns=series_columns,
            values=values_series,
            thekwargs=thiskwargs,
            risk_appetite=self.sdc_checks.risk_appetite,
            command="pivot_table",
        )

        # from previous version- if needed i suggesgt we move this code to
        # the function append_rounded_margins()?
        # Separate variable so param (str|list[str]) isn't reassigned to callable type (mypy)
        # resolved_aggfunc: (
        #     str | Callable[..., Any] | list[str | Callable[..., Any]] | None
        # ) = get_aggfuncs(aggfunc)
        # n_agg: int = (
        #     1 if not isinstance(resolved_aggfunc, list) else len(resolved_aggfunc)
        # )

        #### Step 1  make the requested output
        table: DataFrame = pd.pivot_table(data, **thiskwargs)

        #### Step 2 run the checks and gather evidence
        analysis_names: list[str] = aggfunc_to_strings(aggfunc)
        evidence: SDCEvidence = self.sdc_checks.get_evidence_forall_analyses(
            analysis_names, model_details
        )

        if self.federated:
            uid = f"output_{self.results.output_id}"
            self._store_federated_evidence(uid, command, analysis_names, evidence)
            self.results.output_id += 1
            return table

        collatedres = ManyChecksResults()
        for analysis in analysis_names:
            collatedres.allchecksresults[analysis] = (
                self.sdc_checks.run_checks_for_analysis(
                    analysis, evidence, model_details
                )
            )

        logging.debug(get_debugging_table_analysis(collatedres.allchecksresults))

        collated_assessment = collate_risk_assessments(
            table, collatedres.allchecksresults
        )

        fair_dict = collatedres.get_overall_fair()
        fair_dict.update(model_details.get_variable_type_dict())

        #### Step 3 apply mitigations
        if self.suppress:
            table = get_redacted_pivottable(model_details, collated_assessment)
        elif self._mitigation == "round":
            table = round_table(table, self._round_base)
            # if recompute_margins:
            #    table = append_rounded_margins(
            #        table, resolved_aggfunc, margins_name, self._round_base
            #    )    see comments  above
            table = append_rounded_margins(
                table, aggfunc, margins_name, self._round_base
            )
        ##### Step 4: store evidence & output
        self._record_table_output(
            method="pivot_table",
            status=collatedres.get_overall_status(),
            sdc=collatedres.get_table_sdc(),
            fair=fair_dict,
            command=command,
            summary=collatedres.get_overall_summary(),
            outcome=collated_assessment,
            table=table,
            comments=[],
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

        #### Step 1  make the requested output
        survival_func: Any = sm.SurvfuncRight(
            time,
            status,
            entry,
            title,
            freq_weights,
            exog,
            bw_factor,
        )
        survival_table: pd.DataFrame = survival_func.summary()

        #### Step 0 standardise syntax and capture all relevant information
        ##out of order because what we do SDC on is a by product of the analysis
        model_details = TableModelDetails(
            index=[survival_table["num at risk"]],
            risk_appetite=self.sdc_checks.risk_appetite,
            command="surv_func",
        )
        model_details.model_type = "survival"
        model_details.df_resid = len(status) - len(time.unique())

        #### Step 2 run the checks and gather evidence
        analysis = "KaplanMeier"
        evidence: SDCEvidence = self.sdc_checks.get_evidence_forall_analyses(
            [analysis], model_details
        )

        if self.federated:
            uid = f"output_{self.results.output_id}"
            self._store_federated_evidence(uid, command, [analysis], evidence)
            self.results.output_id += 1
            # return the unmodified survival table / plot path as in local mode
            if output == "table":
                return survival_table
            if output == "plot":
                if utils.is_blocked_extension(
                    filename, self.results.blocked_extensions
                ):
                    return None
                unique_filename = utils.get_unique_artefact_filename(filename)
                if unique_filename == "None":
                    return None
                survival_func.plot()  # pragma: no cover
                plt.savefig(unique_filename)
                return (None, unique_filename)
            return None

        collatedres = ManyChecksResults()
        collatedres.allchecksresults[analysis] = (
            self.sdc_checks.run_checks_for_analysis(analysis, evidence, model_details)
        )

        fair_dict = collatedres.get_overall_fair()
        fair_dict.update(model_details.get_variable_type_dict())

        #### Step 3 apply mitigations
        if self.suppress:
            survival_table = _rounded_survival_table(survival_table)

        ##### Step 4: store evidence & output
        if output == "table":
            # record output
            self.results.add(
                status=collatedres.get_overall_status(),
                output_type="table",
                properties={"method": "surv func"},
                sdc=collatedres.get_table_sdc(),
                fair=fair_dict,
                command=command,
                summary=collatedres.get_overall_summary(),
                outcome=pd.DataFrame(),
                output=[survival_table],
                comments=[],
            )
            if self.suppress:
                justadded = f"output_{self.results.output_id - 1}"
                self.results.add_exception(
                    justadded, "Events Reported when min_threshold accumulated"
                )
                self.results.results[justadded].status = "review"

            return survival_table

        if output == "plot":
            if utils.is_blocked_extension(filename, self.results.blocked_extensions):
                return None
            if self.suppress:
                plot = survival_table.plot(y="rounded_survival_fun", xlim=0, ylim=0)
            else:  # pragma: no cover
                plot = survival_func.plot()

            unique_filename = utils.get_unique_artefact_filename(filename)
            if unique_filename == "None":
                return None
            # save the plot to the acro artifacts directory
            plt.savefig(unique_filename)

            # record output
            self.results.add(
                status=collatedres.get_overall_status(),
                output_type="survival plot",
                properties={"method": "surv_func"},
                sdc=collatedres.get_table_sdc(),
                command=command,
                summary=collatedres.get_overall_summary(),
                outcome=pd.DataFrame(),
                output=[os.path.normpath(unique_filename)],
            )
            return (plot, unique_filename)
        return None

    #### end step 4

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
                fair={},
                command=command,
                summary="fail; empty column after dropping NaN",
                outcome=pd.DataFrame(),
                output=[],
            )
            return None

        oldway = False
        status: str = ""
        if oldway:
            # col_min = float(col_series.min())
            # col_max = float(col_series.max())
            # masks, bin_edges, freq, left_count, right_count = _build_histogram_masks(
            #     col_series, bins, col_min, col_max
            # )
            # by_val, mismatch, sub_stats = _analyse_by_val_ranges(data, column, by_val)

            # sdc = get_histogram_sdc(
            #     masks,
            #     self.suppress,
            #     bin_edges,
            #     freq,
            #     col_min,
            #     col_max,
            #     left_count,
            #     right_count,
            #     mismatch,
            #     sub_stats,
            # )
            # status, summary = get_histogram_summary(sdc, column, col_min, col_max)
            # outcome = build_histogram_outcome(bin_edges, freq, masks)
            status, summary = (
                "not ready-needs ontology change",
                "not ready-needs ontology change",
            )
            logger.info("status: %s", status)
            fair_dict = {}

        else:  # ontology-driven
            analysis = "Histogram"
            model_details = TableModelDetails(
                index=[data[column]],
                thekwargs={"bins": bins},
                risk_appetite=self.sdc_checks.risk_appetite,
                command="hist",
            )
            evidence: SDCEvidence = self.sdc_checks.get_evidence_forall_analyses(
                [analysis], model_details
            )

            if self.federated:
                uid = f"output_{self.results.output_id}"
                self._store_federated_evidence(uid, command, [analysis], evidence)
                self.results.output_id += 1
                return None

            collatedres = ManyChecksResults()
            collatedres.allchecksresults[analysis] = (
                self.sdc_checks.run_checks_for_analysis(
                    analysis, evidence, model_details
                )
            )

            sdc_details: dict = collatedres.get_table_sdc()
            status = collatedres.get_overall_status()
            fair_dict = collatedres.get_overall_fair()
            fair_dict.update(model_details.get_variable_type_dict())
            summary = collatedres.get_overall_summary()

        # plot the histogram (skip when suppressed and disclosive)
        #### Step 3 apply mitigations
        if status == "fail" and self.suppress:
            logger.warning(
                "Histogram will not be shown as the %s column is disclosive.",
                column,
            )
            summary = summary + "Disclosive Histogram Redacted."
            unique_filename = ""
            output = []
        else:  # pragma: no cover
            summary += "Please also check bin ends and empty bins are not disclosive."
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
            unique_filename = utils.get_unique_artefact_filename(filename)
            if unique_filename == "None":
                return None
            plt.savefig(unique_filename)
            output = [os.path.normpath(unique_filename)]

        # record output
        self.results.add(
            status=status,
            output_type="histogram",
            properties={"method": "histogram"},
            sdc=sdc_details,
            fair=fair_dict,
            command=command,
            summary=summary,
            outcome=pd.DataFrame(),
            output=output,
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
        #### Step 0 standardise syntax and capture all relevant information
        #### Step 1  make the requested output
        #### Step 3 apply mitigations
        ##### Step 4: store evidence & output

        ## run the checks and get the masks
        analysis = "PieChart"
        model_details = TableModelDetails(
            index=[data[column]],
            thekwargs=dict(kwargs),
            risk_appetite=self.sdc_checks.risk_appetite,
            command="pie",
        )

        #### Step 2 run the checks and gather evidence
        evidence: SDCEvidence = self.sdc_checks.get_evidence_forall_analyses(
            [analysis], model_details
        )

        if self.federated:
            uid = f"output_{self.results.output_id}"
            self._store_federated_evidence(uid, command, [analysis], evidence)
            self.results.output_id += 1
            return None

        collatedres = ManyChecksResults()
        collatedres.allchecksresults[analysis] = (
            self.sdc_checks.run_checks_for_analysis(analysis, evidence, model_details)
        )

        sdc_details: dict = collatedres.get_table_sdc()
        overall_status: str = collatedres.get_overall_status()
        fair_dict = collatedres.get_overall_fair()
        fair_dict.update(model_details.get_variable_type_dict())
        summary = collatedres.get_overall_summary()

        if self.suppress and overall_status == "fail":
            logger.warning(
                "Pie chart will not be shown as the %s column is disclosive.",
                column,
            )
            summary = summary + " Pie Chart Redacted."
            output = []
            unique_filename = ""

        else:
            summary += "Please also for missing categories."

            counts = data[column].value_counts()
            _, ax = plt.subplots()
            ax.pie(counts.values, labels=counts.index, **kwargs)

            unique_filename = utils.get_unique_artefact_filename(filename)
            if unique_filename == "None":
                return None

            plt.savefig(unique_filename)
            output = [os.path.normpath(unique_filename)]

        # RECORD OUTPUT
        self.results.add(
            status=overall_status,
            output_type="pie chart",
            properties={"method": "pie"},
            sdc=sdc_details,
            fair=fair_dict,
            command=command,
            summary=summary,
            outcome=pd.DataFrame(),
            output=output,
            comments=[],
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
