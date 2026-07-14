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
import statsmodels

from . import sdc_agg_funcs
from .sdc_agg_funcs import (
    agg_missing,
    agg_num_negative,
    agg_top_2_sum,
    agg_top_n_sum,
    get_statsmodel_dof,
)
from .tablemodeldetails import TableModelDetails

warnings.simplefilter(action="ignore", category=FutureWarning)

logger = logging.getLogger("acro")

DETAIL_TO_AGG: dict[str, Callable] = {
    "sum": np.sum,
    "max": np.max,
    "missing": agg_missing,
    "top_2_sum": agg_top_2_sum,
    "top_n_sum": agg_top_n_sum,
    "num_negative": agg_num_negative,
}


@dataclass
class SDCEvidence:
    """Class for evidence needed to run risk assesSment checks for an analysis."""

    dof: Any = None
    interim_tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    other_evidence: dict[str, Any] = field(default_factory=dict)
    variable_type_dict: dict[str, Any] = field(default_factory=dict)

    def populate_dof(self, model: Any) -> None:
        """Populate dof for any sort of model."""
        if isinstance(model, statsmodels.base.model.Model):
            self.dof = get_statsmodel_dof(model)
        elif isinstance(model, TableModelDetails):
            self.dof = model.get_count_table() - 1
        else:
            self.dof = -1

    def populate_from_list(self, evidence_needed: set, model: Any) -> None:
        """Populate dataclass for a given model-analyses combination."""
        if "DoF" in evidence_needed:
            self.populate_dof(model)
        if isinstance(model, statsmodels.base.model.Model):
            deps = model.endog_names
            if isinstance(deps, str):
                self.variable_type_dict["dependent"] = deps
            indeps = model.exog_names.copy()
            if "const" in indeps:
                indeps.remove("const")
            if "Intercept" in indeps:
                indeps.remove("Intercept")
            self.variable_type_dict["independent"] = indeps

        if isinstance(model, TableModelDetails):
            sdc_agg_funcs.NK_N = model.risk_appetite["safe_nk_n"]
            if "count_table" in evidence_needed:
                self.interim_tables["count_table"] = model.get_count_table()
                logger.debug(f"count table:\n{self.interim_tables['count_table']}\n")
            for detail, value in DETAIL_TO_AGG.items():
                if detail in evidence_needed:
                    aggfunc = value
                    self.interim_tables[detail] = model.get_table_newagg(aggfunc)
                    logger.debug(f"{detail} table:\n{self.interim_tables[detail]}\n")
            self.variable_type_dict = model.get_variable_type_dict()


@dataclass
class ChecksResults:
    """Class holding results of running checks for an analysis.

    overall_status : str
        'fail', 'review', or 'pass'
    summaries : string
            concatenation of summaries for each check run.
    outcomes : dict[str,Any]
        dictionary of outcomes with keys for the check and values which might be:
        numbers (e.g. Dof), or masks (Dataframes),
        depending on the check and the type of model e.g. regression vs table
    fair_dict: details of the sdc processes
        dict with one key (for now) `check_status where the value is itself a dict
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
        """Get overall summary from multiple statistics.  # noqa: D212,D213,D413.

        Returns
        -------
        str
            Summary of checks, excluding those that pass.
        """
        allsummary = ""
        for analysis, checksresults in self.allchecksresults.items():
            allsummary += f"{analysis} : "
            for checksummary in checksresults.summaries.split("\n"):
                if operator.contains(checksummary, "pass") or operator.contains(
                    checksummary, "RequiredZeroCheck"
                ):
                    pass
                else:
                    allsummary += f"\n{checksummary}"
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
                if name in checks_seen:
                    continue
                checks_seen.append(name)
                sdc["cells"][name] = []
                if name == "MinimumDoFCheck" and isinstance(mask, int):
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
    mask = mask.fillna(value=1, inplace=False)
    mask = mask.astype(bool)
    return mask


def get_status_summary_from_mask(mask: pd.DataFrame) -> tuple[str, str]:
    """
    Get status and summary from mask.

    Parameters
    ----------
    mask : pd.DataFrame
        Binary mask indicating disclosive cells.

    Returns
    -------
    tuple
        Status and summary string.
    """
    mask = mask_to_boolmask(mask)
    truecount = int(np.nansum(mask.to_numpy()))
    status = "fail" if truecount > 0 else "pass"
    # name of check that related mask gets prepended to summary in run_checks()
    summary = f"{status} - {truecount} cells may need suppressing.\n"
    return status, summary


class SDCChecks:
    """
    Implements range of SDC checks.

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
        """
        Construct object and load knowledge from json files.

        Parameters
        ----------
        risk_appetite : dict
            Dictionary of risk appetite values
        TODO
            move risk_appetite from constructor to model class
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
        path4: pathlib.Path = pathlib.Path(__file__).with_name("checks.json")
        with open(path4, encoding="utf=8") as handle:
            self.checks = json.loads(handle.read())

        # map names of checks onto methods
        self.check_to_method: dict = {
            "MissingCheck": self.check_missing,
            "MinimumDoFCheck": self.check_model_dof,
            "AllSameValuesCheck": self.check_all_same,
            "MinimumThresholdCheck": self.check_min_threshold,
            "StatbarnDataCheck": self.manual_check,
            "NKCheck": self.check_nk_dominance,
            "PPercentCheck": self.check_ppercent_dominance,
            "PresenceOfLinkedTableCheck": self.check_linked_table,
            "RequiredZeroCheck": self.check_required_zero,
            "PresenceOfZeroCheck": self.check_presence_of_zero,
        }

    def get_sdctokens_for_analysis(self, statname: str) -> dict:
        """
        Get list of sdc tokens to run for a given analysis.

        Parameters
        ----------
        statname : str
            Analysis prefix label for a statbarnsdc analysis type.

        Returns
        -------
        dict
            SDC terms to be saved.
        """
        prefix = "https://www.w3id.org/statbarnsdc#"
        statbarn = self.analyses.get(statname)["statbarn"]
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
            print(  # noqa: T201
                "todo on mitigations ",
                np.unique(np.array(sdc_dict["common_mitigations"]), return_counts=True),
            )

        return sdc_dict

    def get_evidence_forall_analyses(
        self, analyses: list[str], model: Any
    ) -> SDCEvidence:
        """Collate the evidence needed to do SDC for all the analyses requested by a query."""
        evidence_needed: set = set()
        for analysis_name in analyses:
            checks_needed = self.get_sdctokens_for_analysis(analysis_name)[
                "checks_needed"
            ]
            for check in checks_needed:
                evidence_needed.update(self.checks[check]["evidence"])
        logger.debug(
            f"model has type {type(model)}, evidence needed for analyses {analyses} is {evidence_needed}"
        )
        thevidence = SDCEvidence()
        thevidence.populate_from_list(evidence_needed, model)
        return thevidence

    def run_checks_for_analysis(
        self, analysis_name: str, evidence: SDCEvidence, model: Any
    ) -> ChecksResults:
        """
        Given a set of evidence, run all the checks needed for a given type of analysis and report outcomes.

        Parameters
        ----------
        analysis_name : str
            name of the type of analysis
            should match a type of analysis from statbarnsdc ontology
        evidence : SDCEvidence
            evidence collected in previous stage
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
        if analysis_name not in self.analyses.keys():
            return ChecksResults(
                "Review", "Name of analysis not recognised in ontology", {}, {}
            )

        sdc_dict = self.get_sdctokens_for_analysis(analysis_name)

        statuses: list = []
        summaries: list = []
        outcomes: dict[str, Any] = {}
        sdc_dict["check_status"] = {}

        for check in sdc_dict["checks_needed"]:
            checkfunc = self.check_to_method[check]
            status, summary, outcome = checkfunc(analysis_name, evidence, model)
            # prepend name of check to summary
            statuses.append(status)
            summaries.append(check + ": " + summary)
            outcomes[check] = outcome
            sdc_dict["check_status"][check] = status
        logger.debug(
            f"statuses : {statuses}\nsummary: {summaries}\noutcomes: {outcomes}\n"
        )

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
        logger.debug("%s : %s", overall_status, shortsummary)
        return ChecksResults(overall_status, summary, outcomes, sdc_dict)

    def check_model_dof(
        self, name: str, evidence: SDCEvidence, model: Any
    ) -> tuple[str, str, int]:
        """
        Check model DOF.

        Parameters
        ----------
        name : str
            The name of the model.
        evidence : SDCEvidence
            The collected evidence object.
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
        _, _ = name, model
        threshold: int = int(self.risk_appetite["safe_dof_threshold"])

        status = "pass"
        comparator = ">="

        if isinstance(evidence.dof, int) and evidence.dof < threshold:
            status = "fail"
            comparator = "<"
        if isinstance(evidence.dof, pd.DataFrame):
            fail_table = evidence.dof < threshold
            if fail_table.any().any():
                status = "fail"
                comparator = "<"

        summary = f"{status} dof={evidence.dof} {comparator} {threshold}"
        return status, summary, evidence.dof

    def check_all_same(
        self, name: str, evidence: SDCEvidence, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """
        Check whether all values in cells are the same.

        Parameters
        ----------
        name : str
            The name of the model.
        evidence : SDCEvidence
            The collected evidence object.
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
        _, _ = name, model
        mask = evidence.interim_tables["values_are_same"]
        status, summary = get_status_summary_from_mask(mask)
        return status, summary, mask

    def check_missing(
        self, name: str, evidence: SDCEvidence, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """Check whether any cells have missing values.  # noqa: D212,D213,D413,D417.

        Parameters
        ----------
        name : str
            The name of the model.
        evidence : SDCEvidence
            The collected evidence object.
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
        _, _ = name, model
        mask = evidence.interim_tables["missing"]
        status, summary = get_status_summary_from_mask(mask)
        return status, summary, mask

    def check_min_threshold(
        self, name: str, evidence: SDCEvidence, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """
        Check for small numbers of respondents in cells.

        Parameters
        ----------
        name : str
            The name of the model.
        evidence : SDCEvidence
            The collected evidence object.
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
            mask = (
                evidence.interim_tables["count_table"]
                < self.risk_appetite["safe_threshold"]
            )
            status, summary = get_status_summary_from_mask(mask)
            return status, summary, mask
        # array
        data = model.index[0]
        if model.command == "hist":
            bins = model.kwargs.get("bins", 10)
            _, bin_edges = np.histogram(data.dropna(), bins)
            binids = np.digitize(data.dropna(), bin_edges)
            # account for all possible bin ids (1..num_bins inclusive)
            possibles = list(range(1, len(bin_edges)))
            cat_type = pd.CategoricalDtype(categories=possibles)
            the_array = pd.Series(binids, dtype=cat_type)
        else:
            the_array = data
        count_series = the_array.value_counts()
        mask_series = count_series < self.risk_appetite["safe_threshold"]
        mask = mask_to_boolmask(pd.DataFrame(mask_series))
        status, summary = get_status_summary_from_mask(mask)
        if model.command == "hist":
            summary += (
                " Review Notes: Please check extreme bin edges are not disclosive."
            )
        return status, summary, mask

    def manual_check(
        self, name: str, evidence: SDCEvidence, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """
        Report that a manual check is needed.

        Parameters
        ----------
        name : str
            The name of the model.
        evidence : SDCEvidence
            The collected evidence object.
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
        _, _ = name, evidence

        model_type = model.model_type
        if model_type not in ["table", "array", "survival"]:
            logger.info("model type recognised or not present in model descriptor")
            return (
                "fail",
                "testing table: dict passed as model in insufficient",
                pd.DataFrame(),
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
        return "review", summary, model.get_allfalse_table()

    def check_nk_dominance(
        self, name: str, evidence: SDCEvidence, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """
        Check for NK dominance within each cell.

        Parameters
        ----------
        name : str
            The name of the model.
        evidence : SDCEvidence
            The collected evidence object.
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
        _, _ = name, model
        if evidence.interim_tables["num_negative"].sum().sum() > 0:
            negs = evidence.interim_tables["num_negative"] > 0
            return (
                "review",
                "Dominance not defined when negative value are present",
                negs,
            )
        proportionmask = (
            evidence.interim_tables["top_n_sum"] / evidence.interim_tables["sum"]
        )
        logger.debug(f"NK proportionmask:\n{proportionmask}\n")
        mask = proportionmask >= self.risk_appetite["safe_nk_k"]
        status, summary = get_status_summary_from_mask(mask)
        return status, summary, mask

    def check_ppercent_dominance(
        self, name: str, evidence: SDCEvidence, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """
        Check for PQ dominance within each cell.

        Parameters
        ----------
        name : str
            The name of the model.
        evidence : SDCEvidence
            The collected evidence object.
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
        _, _ = name, model

        if evidence.interim_tables["num_negative"].sum().sum() > 0:
            negs = evidence.interim_tables["num_negative"] > 0
            return (
                "review",
                "Dominance not defined when negative value are present",
                negs,
            )

        # p-ratio rule: (sum - top1 - top2) / top1 < threshold
        # i.e. the remaining contributors are too small relative to the largest
        # Uses: sum, max (=top1), top_2_sum (=top1+top2)
        top1 = evidence.interim_tables["max"]
        sub_total = (
            evidence.interim_tables["sum"] - evidence.interim_tables["top_2_sum"]
        )
        # avoid division by zero; if top1==0, treat as non-disclosive
        p_val = sub_total.where(top1 == 0, sub_total / top1.replace(0, float("nan")))
        p_val = p_val.fillna(1.0)
        mask = p_val < self.risk_appetite["safe_pratio_p"]
        status, summary = get_status_summary_from_mask(mask)
        return status, summary, mask

    def check_linked_table(
        self, name: str, evidence: SDCEvidence, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """
        Check for presence of linked tables.

        Parameters
        ----------
        name : str
            The name of the model.
        evidence : SDCEvidence
            The collected evidence object.
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
        _, _ = name, evidence

        summary = (
            "A manual review is needed."
            f" Variables defining table are:  {model.get_dimension_names()}.\n"
        )

        return "review", summary, model.get_allfalse_table()

    def check_required_zero(
        self, name: str, evidence: SDCEvidence, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """
        Check for required-zero cells (zeros that should always be present).

        Parameters
        ----------
        name : str
            The name of the model.
        evidence : SDCEvidence
            The collected evidence object.
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
        _ = evidence
        mask = model.get_allfalse_table()
        qualifier = ""
        if not self.risk_appetite["zeros_are_disclosive"]:
            qualifier = "not"

        return "pass", f"zeros are {qualifier} considered disclosive.\n", mask

    def check_presence_of_zero(
        self, name: str, evidence: SDCEvidence, model: TableModelDetails
    ) -> tuple[str, str, pd.DataFrame]:
        """
        Check for presence of cells with values zero.

        Parameters
        ----------
        name : str
            The name of the model.
        evidence : SDCEvidence
            The collected evidence object.
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

        count_table = evidence.interim_tables["count_table"]

        if self.risk_appetite["zeros_are_disclosive"]:
            # mask has true for disclosive cells where count==0
            mask = count_table == 0
            status, summary = get_status_summary_from_mask(mask)

        else:
            mask = model.get_allfalse_table()
            status, summary = get_status_summary_from_mask(mask)
            summary = summary + " - risk appetite states zeros not disclosive."
        return status, summary, mask
