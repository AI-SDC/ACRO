"""ACRO: Risk Checking Functions."""

from __future__ import annotations

import json
import logging
import operator
import pathlib
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from . import aggregationfunctions
from .aggregationfunctions import (
    agg_missing,
    agg_nk,
    agg_p_percent,
    agg_values_are_same,
)
from .tablemodeldetails import TableModelDetails

warnings.simplefilter(action="ignore", category=FutureWarning)

logger = logging.getLogger("acro")


@dataclass
class ChecksResults:
    """Class for results of running checks for an analysis.

    overall_status : str
      'fail', 'review', or 'pass'
    summaries : string
        concatenation of summaries for each check run
    outcomes : dict[str,Any]
        dictionary of outcomes with keys for the check and values which might be:
         numbers (e.g. Dof), or masks (Dataframes),
        depending on the check and the type of model e.g. regression vs table
    fair_dict: details of the sdc processes
                dict with one key (for now) "check_status" where the value is itself a dict
    """

    overall_status: str
    summaries: str
    outcomes: dict[str, Any]
    fair_dict: dict


@dataclass
class ManyChecksResults:
    """Class for running checks on multiple analysis."""

    allchecksresults: dict[str, ChecksResults] = field(default_factory=dict)

    def get_overall_summary(self) -> str:
        """Get overall summary from multiple statistics.

        Don't include details for tests that pass
        """
        allsummary = ""
        for analysis, checksresults in self.allchecksresults.items():
            allsummary += f"\n{analysis} : "
            for checksummary in checksresults.summaries.split("\n"):
                if operator.contains(checksummary, "pass") or operator.contains(
                    checksummary, "RequiredZeroCheck"
                ):
                    pass
                else:
                    allsummary += f"\n {checksummary}"
        return allsummary

    def get_overall_status(self) -> str:
        """Get overall risk status for set of analyses."""
        overall_status = "pass"

        statuses: list[str] = []
        for _analysis, checksresults in self.allchecksresults.items():
            statuses.append(checksresults.overall_status)
        if "fail" in statuses:
            overall_status = "fail"
        elif "review" in statuses:
            overall_status = "review"

        return overall_status

    def get_overall_fair(self) -> dict[str, dict]:
        """Get overall FAIR analysis for set of analyses."""
        fairdict: dict[str, dict] = {}
        for _analysis, checksresults in self.allchecksresults.items():
            fairdict.update(checksresults.fair_dict)

        return fairdict

    def get_table_sdc(self) -> dict[str, Any]:
        """Return the SDC dictionary for a table using the suppression masks."""
        # summary of number of cells to be suppressed
        sdc: dict[str, Any] = {"summary": {}, "cells": {}}

        checks_seen: list[str] = []
        for _analysis, checksresults in self.allchecksresults.items():
            for name, mask in checksresults.outcomes.items():
                # logger.info(f' in get_table_sdc, name={name} mask= {mask}')
                if name in checks_seen:
                    continue
                checks_seen.append(name)
                sdc["cells"][name] = []
                if name == "MinimumDoFCheck":
                    sdc["summary"][name] = 0 if mask > 0 else 1
                else:
                    sdc["summary"][name] = int(np.nansum(mask.to_numpy()))
                    # positions of cells to be suppressed
                    true_positions = np.column_stack(np.where(mask.values))
                    for pos in true_positions:
                        row_index, col_index = pos
                        sdc["cells"][name].append([int(row_index), int(col_index)])

        return sdc


# Helper function that do not need to be in class
def mask_to_boolmask(mask: pd.DataFrame) -> pd.DataFrame:
    """Tidy up glitches in mask."""
    # pd.crosstab returns nan for an empty cell
    mask.fillna(value=1, inplace=True)
    mask = mask.astype(bool)
    return mask


def status_summary_from_mask(mask: pd.Dataframe) -> tuple[str, str]:
    """Get status and summary from mask.

    Parameters
    ----------
    mask : pd.Dataframe
        the output of running some condition over a table

    Returns
    -------
    str : status -one of 'pass','fail'
    str : summary string
    """
    mask = mask_to_boolmask(mask)
    truecount = int(np.nansum(mask.to_numpy()))
    status = "fail" if truecount > 0 else "pass"
    # name of check that related mask gets prepended to summary in run_checks()
    summary = f"{status} - {truecount} cells may need suppressing.\n"
    return status, summary


def get_empty_mask() -> pd.DataFrame:
    """Return an empty pandas dataftrame with nominal bool contents."""
    return pd.DataFrame(dtype=bool)


def get_zeros_mask(model: TableModelDetails) -> pd.DataFrame:
    """Create a data frame filled with zeros of same size as underlying table."""
    args: tuple = model.get_crosstab_args()
    kwargs: dict = model.get_crosstab_kwargs()
    kwargs["aggfunc"] = kwargs["values"] = None
    count_table = pd.crosstab(*args, **kwargs)
    for col in count_table.columns:
        count_table[col].values[:] = 0
    return count_table


def get_allfalse_mask(model: TableModelDetails) -> pd.DataFrame:
    """Create a data frame filled with false of same size as underlying table."""
    if model.model_type == "table":
        args = model.get_crosstab_args()
        thiskwargs = model.get_crosstab_kwargs()
        thiskwargs["aggfunc"] = thiskwargs["values"] = None
        mask = pd.crosstab(*args, **thiskwargs)
        for col in mask.columns:
            mask[col].values[:] = False
        # logger.info(f'get_allfalse_mask for table, mask=:\n{mask}')

    else:  # array
        series_mask = model.index[0].value_counts()
        series_mask.iloc[:] = False
        mask = pd.DataFrame(series_mask)
        # logger.info(f'get_allfalse_mask for other {model.model_type}, mask=:\n{mask}')

    return mask_to_boolmask(mask)


def get_count_table(model: TableModelDetails) -> pd.DataFrame:
    """Make count table as specified by model."""
    args = model.get_crosstab_args()
    thiskwargs = model.get_crosstab_kwargs()
    thiskwargs["values"] = None
    thiskwargs["aggfunc"] = None
    return pd.crosstab(*args, **thiskwargs)


def run_check_from_aggfunc(
    model: TableModelDetails, aggfunc: Callable
) -> tuple[str, str, pd.DataFrame]:
    """Run a check given a table model and an aggregation function."""
    args = model.get_crosstab_args()
    # logger.info(f'check from aggfunc args={args}')
    thiskwargs = model.get_crosstab_kwargs()
    thiskwargs["aggfunc"] = aggfunc
    mask = pd.crosstab(*args, **thiskwargs)
    # logger.info(f'run check from aggfunc mask={mask}')
    mask = mask_to_boolmask(mask)
    status, summary = status_summary_from_mask(mask)
    return status, summary, mask


###################################################################################
class SDCChecks:
    """Implements range of SDC checks.

    All the information is read from json files
    that are separately generated from the online ontology .ttl file
    (because they can't be read from inside the TRE).

    The constructor is fed the risk appetite for the session on creation.

    All methods implementing checks have common format:
        Parameters are
            name:str
                the 'family name' of the type of analysis
                determines what needs to be run
            model: Any
                can be statsmodel or the details
                (rows,columns,values) to create a table
        Returns: tuple
            string (status  for that check)
            string: summary of that check
            Any: check details as
                 single values (e.g. Dof) or
                 a mask showing cell-by cell results for a table
    """

    def __init__(self, risk_appetite: dict) -> None:
        """Construct object and load knowledge from json files.

        Parameters
        ----------
        risk_appetite : dict
            Dictionary of risk appetite values
        TODO
            move risk_appetite from construvtor to model class
            as it is in TableModelDetails class anyway
        """
        # load lookup tables from json
        self.risk_appetite = risk_appetite
        path1: pathlib.Path = pathlib.Path(__file__).with_name("statbarns.json")
        with open(path1, encoding="utf=8") as handle:
            self.statbarns = json.loads(handle.read())
        path2: pathlib.Path = pathlib.Path(__file__).with_name("analyses.json")
        with open(path2, encoding="utf=8") as handle:
            self.analyses = json.loads(handle.read())
        path3: pathlib.Path = pathlib.Path(__file__).with_name("risks.json")
        with open(path3, encoding="utf=8") as handle:
            self.risks = json.loads(handle.read())

        # map names of checks onto methods
        self.check_to_method: dict = {
            "MissingCheck": self.check_missing,
            "MinimumDoFCheck": self.check_model_dof,
            "AllSameValuesCheck": self.check_all_same,
            "MinimumThresholdCheck": self.check_min_threshold,
            "StatbarnDataCheck": self.manual_check,
            "NKCheck": self.check_nk_dominance,
            "PQCheck": self.check_pq_dominance,
            "PresenceOfLinkedTableCheck": self.check_linked_table,
            "RequiredZeroCheck": self.check_required_zero,
            "PresenceOfZeroCheck": self.check_presence_of_zero,
        }
        # set globals needed for aggregation functions
        if len(self.risk_appetite) > 0:
            aggregationfunctions.THRESHOLD = self.risk_appetite["safe_threshold"]
            aggregationfunctions.SAFE_PRATIO_P = self.risk_appetite["safe_pratio_p"]
            aggregationfunctions.SAFE_NK_N = self.risk_appetite["safe_nk_n"]
            aggregationfunctions.SAFE_NK_K = self.risk_appetite["safe_nk_k"]
            aggregationfunctions.CHECK_MISSING_VALUES = self.risk_appetite[
                "check_missing_values"
            ]
            aggregationfunctions.ZEROS_ARE_DISCLOSIVE = self.risk_appetite[
                "zeros_are_disclosive"
            ]
            # set globals for survival analysis
            aggregationfunctions.SURVIVAL_THRESHOLD = self.risk_appetite[
                "survival_safe_threshold"
            ]

    def get_sdctokens_for_analysis(self, statname: str) -> dict:
        """Get list of sdc tokens to run for a given analysis.

        Parameters
        ----------
        analysis | str
            prefix label for a statbarnsdc analysis type

        Returns
        -------
        dict of sdc terms to be saved
        """
        prefix = "https://www.w3id.org/statbarnsdc#"
        statbarn = self.analyses.get(statname)["statbarn"]
        logger.debug(f"{statname} is a form of {statbarn}")
        sdc_dict: dict = {
            "analysis_uri": self.analyses[statname]["uri"],
            "statbarn": self.analyses[statname]["statbarn"],
            "statbarn_uri": self.statbarns[statbarn]["uri"],
            "risks": self.statbarns[statbarn]["risks"],
            "checks_needed": [],
            "common_mitigations": [],
        }
        for risk in sdc_dict["risks"]:
            risk = risk.replace(prefix, "")
            checks = self.risks[risk]["checks"]
            sdc_dict["checks_needed"].extend(checks)
            mitigations = self.risks[risk]["mitigations"]
            sdc_dict["common_mitigations"].extend(mitigations)

        # TODOcommon mitigations - remove ones where count != len risks
        if False:
            print(
                "todo on mitigations ",
                np.unique(np.array(sdc_dict["common_mitigations"]), return_counts=True),
            )

        return sdc_dict

    def run_checks_for_analysis(self, analysis_name: str, model: Any) -> ChecksResults:
        """Run all the checks needed for a given type of analysis and report outcomes.

        Parameters
        ----------
        analysis_name : str
            name of the type of analysis
            should match a type of analysis from statbarnsdc ontology
        model : Any
            either the trained model (for regression etc)
            or sufficient details to recreate a table
            TODO restrict to either TableModelDetails (from table_utils)
            or appropriate statsmodels classes

        Returns
        -------
        overall_status : str
          'fail', 'review', or 'pass'
        summaries : string
            concatenation of summaries for each check run
        outcomes : dict[str,Any]
            dictionary of outcomes with keys for the check and values which might be:
             numbers (e.g. Dof), or masks (Dataframes),
            depending on the check and the type of model e.g. regression vs table
        sdc_dict : details of the sdc processes
                    dict with one key (for now) "check_status" where the value is itself a dict
                    of checkname (str): status (str)
        """
        if not analysis_name in self.analyses.keys():
            logger.info(f"keys are : {list(self.analyses.keys())}")
            return ChecksResults(
                "Review", "Name of analysis not recognised in ontology", {}, {}
            )

        sdc_dict = self.get_sdctokens_for_analysis(analysis_name)

        logger.debug(f"details for analysis {analysis_name} are:")
        for key, val in sdc_dict.items():
            logger.debug(f"{key} : {val}")

        statuses: list = []
        summaries: list = []
        outcomes: dict[str, Any] = {}
        sdc_dict["check_status"] = {}

        for check in sdc_dict["checks_needed"]:
            checkfunc = self.check_to_method[check]
            status, summary, outcome = checkfunc(analysis_name, model)
            # prepend name of check to summary
            statuses.append(status)
            summaries.append(check + ": " + summary)
            outcomes[check] = outcome
            sdc_dict["check_status"][check] = status
        logger.debug(
            f"statuses : {statuses}\nsummary: {summaries}\noutcomes: {outcomes}\n"
        )
        # logger.info(analysis_name +" : " + summaries)

        if "fail" in statuses:
            overall_status = "fail"
        elif "review" in statuses:
            overall_status = "review"
        else:
            overall_status = "pass"
        summary = " ".join(summaries)
        shortsummary: str = ""
        for summ in summaries:
            if operator.contains(summ, "review") or operator.contains(summ, "fail"):
                shortsummary += summ
        logger.info("%s : %s", overall_status, shortsummary)
        return ChecksResults(overall_status, summary, outcomes, sdc_dict)

    def check_model_dof(self, name: str, model: Any) -> tuple[str, str, int]:
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
            the residual degrees of freedom.
        """
        status = "fail"
        dof: int = -999
        if isinstance(model, TableModelDetails):
            dof = model.df_resid
        elif not hasattr(model, "df_resid"):
            return (
                "fail",
                "model does not have attribute df_resid so check could not run",
                -1,
            )

        else:
            dof = int(model.df_resid)
        threshold: int = int(self.risk_appetite["safe_dof_threshold"])
        if dof < threshold:
            status = "fail"
            comparator = "<"
        else:
            status = "pass"
            comparator = ">="

        summary = f"{status} dof={dof} {comparator} {threshold}"

        logger.debug("in checks.check_model_dof()")
        logger.debug(
            "%s(), status: %s(), summary: %s(), outcome: %s", name, status, summary, dof
        )
        return status, summary, dof

    def check_all_same(
        self, name: str, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """Check whether all values in cells are the same .

        Parameters
        ----------
        name : str
            The name of the model.
        model : TableModelDetails
            definition of a table

        Returns
        -------
        str
            Status: {"review", "fail", "pass"}.
        str
            Summary of the check.
        pandas DataFrame
            binary mask with same config as the underlying table.
        """
        _ = name

        return run_check_from_aggfunc(model, agg_values_are_same)

    def check_missing(
        self, name: str, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """Check whether any  cells have missing values .

        Parameters
        ----------
        name : str
            The name of the model.
        model : dict
            definition of a table

        Returns
        -------
        str
            Status: {"review", "fail", "pass"}.
        str
            Summary of the check.
        pandas DataFrame
            binary mask with same config as the underlying table.
        """
        _ = name

        return run_check_from_aggfunc(model, agg_missing)

    def check_min_threshold(
        self, name: str, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """Check for small numbers of respondents in cells.

        Parameters
        ----------
        name : str
            The name of the model.
        model : dict
            definition of a table

        Returns
        -------
        str
            Status: {"review", "fail", "pass"}.
        str
            Summary of the check.
        pandas DataFrame
            binary mask with same config as the underlying table.
        """
        _ = name

        model_type = model.model_type
        if model_type == "table":
            count_table = get_count_table(model)
            mask = count_table < self.risk_appetite["safe_threshold"]
        else:  # array
            data = model.index[0]
            if model.command == "hist":
                bins = model.kwargs.get("bins", 10)
                hist, bin_edges = np.histogram(data, bins)
                binids = np.digitize(data, bin_edges)
                # account for all possible bin ids
                possibles = list(range(1, len(bin_edges) - 1))
                cat_type = pd.CategoricalDtype(categories=possibles)
                the_array = pd.Series(binids, dtype=cat_type)
            else:
                the_array = data
            count_series = the_array.value_counts()
            mask_series = count_series < self.risk_appetite["safe_threshold"]
            mask = pd.DataFrame(mask_series)

        # print(f'mask in mintheshold= {mask}')
        mask = mask_to_boolmask(mask)
        # print(f'bool mask in mintheshold= {mask}')
        status, summary = status_summary_from_mask(mask)
        if model.command == "hist":
            summary += (
                " Review Notes: Please check extreme bin edges are not disclosive."
            )
        return status, summary, mask

    def manual_check(
        self, name: str, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """Report that a manual check is needed.

        Parameters
        ----------
        name : str
            The name of the model.
        model : TableModelDetails
            definition of a table

        Returns
        -------
        str
            Status: {"review", "fail", "pass"}.
        str
            Summary of the check.
        pandas DataFrame
            binary mask with same config as the underlying table.
        """
        _ = name

        model_type = model.model_type
        if model_type not in ["table", "array", "survival"]:
            logger.info("model type recognised or not present in model descriptor")
            return (
                "fail",
                "testing table: dict passed as model in insufficient",
                get_empty_mask(),
            )
        if model_type == "table":
            summary = (
                "review: a manual check is needed for possible linked tables"
                f" variables defining table are:  {model.get_dimension_names()}"
            )
        if model_type == "survival":
            summary = (
                "review: a manual check may be needed "
                "if related plots have been produced"
            )
        return "review", summary, get_allfalse_mask(model)

    def check_nk_dominance(
        self, name: str, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """Check for NK dominace within each cell.

        Parameters
        ----------
        name : str
            The name of the model.
        model : TableModelDetails
            definition of a table

        Returns
        -------
        str
            Status: {"review", "fail", "pass"}.
        str
            Summary of the check.
        pandas DataFrame
            binary mask with same config as the underlying table.
        """
        _ = name
        return run_check_from_aggfunc(model, agg_nk)

    def check_pq_dominance(
        self, name: str, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """Check for PQ dominance within each cell.

        Parameters
        ----------
        name : str
            The name of the model.
        model : TableModelDetails
            definition of a table

        Returns
        -------
        str
            Status: {"review", "fail", "pass"}.
        str
            Summary of the check.
        pandas DataFrame
            binary mask with same config as the underlying table.
        """
        _ = name
        return run_check_from_aggfunc(model, agg_p_percent)

    def check_linked_table(
        self, name: str, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """Check for presence of linked tables.

        Parameters
        ----------
        name : str
            The name of the model.
        model : TableModelDetails
            definition of a table

        Returns
        -------
        str
            Status: {"review", "fail", "pass"}.
        str
            Summary of the check.
        pandas DataFrame
            binary mask with same config as the underlying table.
        """
        _ = name

        summary = (
            "A manual review is needed."
            f" Variables defining table are:  {model.get_dimension_names()}.\n"
        )

        return "review", summary, get_allfalse_mask(model)

    def check_required_zero(
        self, name: str, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """Check for.

        Parameters
        ----------
        name : str
            The name of the model.
        model : TableModelDetails
            definition of a table

        Returns
        -------
        str
            Status: {"review", "fail", "pass"}.
        str
            Summary of the check.
        pandas DataFrame
            binary mask with same config as the underlying table.
        """
        _ = name
        mask = get_allfalse_mask(model)
        qualifier = ""
        if not self.risk_appetite["zeros_are_disclosive"]:
            qualifier = "not"

        return "pass", f"zeros are {qualifier} considered disclosive.\n", mask

    def check_presence_of_zero(
        self, name: str, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """Check for presence of cells with values zero.

        Parameters
        ----------
        name : str
            The name of the model.
        model : TableModelDetails
            definition of a table

        Returns
        -------
        str
            Status: {"review", "fail", "pass"}.
        str
            Summary of the check.
        pandas DataFrame
            binary mask with same config as the underlying table.
        """
        _ = name

        count_table = get_count_table(model)

        if self.risk_appetite["zeros_are_disclosive"]:
            # mask has true for disclosive cells where count==0
            mask = count_table == 0
            status, summary = status_summary_from_mask(mask)

        else:
            mask = get_allfalse_mask(model)
            status, summary = status_summary_from_mask(mask)
            summary = summary + " - risk appetite states zeros not disclosive.\n"
        return status, summary, mask

    def get_mask_sdc(self, name: str, mask: pd.DataFrame) -> dict:
        """Summarise the contents of a mask."""
        mask_sdc: dict[
            str, Any
        ] = {}  #  {"summary": {"suppressed": suppress}, "cells": {}}
        mask_sdc["vulnerable"][name] = int(np.nansum(mask.to_numpy()))
        # positions of cells to be suppressed
        mask_sdc["cells"][name] = []
        true_positions = np.column_stack(np.where(mask.values))
        for pos in true_positions:
            row_index, col_index = pos
            mask_sdc["cells"][name].append([int(row_index), int(col_index)])
        return mask_sdc
