"""ACRO: Risk Checking Functions."""

from __future__ import annotations

import json
import logging
import warnings
from typing import Any

import numpy as np
import pandas as pd

warnings.simplefilter(action="ignore", category=FutureWarning)

logger = logging.getLogger("acro")


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
        """
        # load lookup tables from json
        self.risk_appetite = risk_appetite
        with open("statbarns.json") as handle:
            self.statbarns = json.loads(handle.read())
        with open("analyses.json") as handle:
            self.analyses = json.loads(handle.read())
        with open("risks.json") as handle:
            self.risks = json.loads(handle.read())

        # map names of checks onto methods
        self.check_to_method: dict = {
            "MinimumDoFCheck": self.check_model_dof,
            # "all-values-are-same": self.check_all_same,
            # "MinimumThresholdCheck": self.check_min_threshold,
            # "StatbarnDataCheck": self.manual_check,
            # "NKCheck": self.check_nk_dominance,
            # "PQCheck": self.check_pq_dominance,
            # "PresenceOfLinkedTableCheck": self.check_linked_table,
            # "RequiredZeroCheck": self.check_required_zero,
            # "PresenceOfZeroCheck": self.check_presence_of_zero,
        }

    def get_sdc_for_analysis(self, statname: str) -> dict:
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
        print(
            "todo on mitigations ",
            np.unique(np.array(sdc_dict["common_mitigations"]), return_counts=True),
        )

        return sdc_dict

    def run_checks_for_analysis(
        self, analysis_name: str, model: Any
    ) -> tuple[str, str, list, dict]:
        """Run all the checks needed for a given type of analysis and report outcomes.

        Parameters
        ----------
        analysis_name : str
            name of the type of analysis
            should match a type of analysis from statbarnsdc ontology
        model : Any
            either the trained model (for regression etc)
            or sufficient details to recreate a table

        Returns
        -------
        overall_status : str
          'fail', 'review', or 'pass'
        summaries : string
            concatenation of summaries for each check run
        outcomes : list
            list of outcomes which might be numbers (e.g. Dof),
            or masks, depending on the check and the tytpe of model e.g. regression vs table
        """
        if not analysis_name in self.analyses.keys():
            return "Review", "Name of analysis not recognised in ontology", [], {}

        sdc_dict = self.get_sdc_for_analysis(analysis_name)

        logger.debug(f"details for analysis {analysis_name} are:")
        for key, val in sdc_dict.items():
            logger.debug(f"{key} : {val}")

        statuses: list = []
        summaries: list = []
        outcomes: list = []
        sdc_dict["check_status"] = {}
        for check in sdc_dict["checks_needed"]:
            checkfunc = self.check_to_method[check]
            status, summary, outcome = checkfunc(analysis_name, model)
            statuses.append(status)
            summaries.append(summary)
            outcomes.append(outcome)

            sdc_dict["check_status"][check] = status
        logger.info(
            f"statuses : {statuses}\nsummary: {summaries}\noutcomes: {outcomes}\n"
        )

        if "fail" in statuses:
            overall_status = "fail"
        elif "review" in statuses:
            overall_status = "review"
        else:
            overall_status = "pass"

        return overall_status, " ".join(summaries), outcomes, sdc_dict

    def check_model_validity_size(self, model: Any) -> tuple[bool, int]:
        """Check that model is a valid combination of args and kwargs to specify a table.

        Returns
        -------
        int : number of argfunctions called- determines size of masks needed

        Parameter
        ---------
        model:dict
        combination of args and kwargs to specify a table
        """
        if not (
            isinstance(model, dict)
            and isinstance(model["args"], list)
            and len(model["args"]) == 2
            and isinstance(model["kwargs"], dict)
        ):
            return False, 0
        aggfuncs = model["kwargs"]["aggfunc"]
        if isinstance(aggfuncs, str):
            return True, 1
        elif isinstance(aggfuncs, list):
            return True, len(aggfuncs)
        elif aggfuncs is None:
            return True, 1
        else:
            return False, 0

    def check_model_dof(self, name: str, model: Any) -> tuple[str, str, Any]:
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
        pandas DataFrame
            Single cell reporting the residual degrees of freedom.
        """
        status = "fail"
        if not hasattr(model, "df_resid"):
            return (
                "fail",
                "model does not have attribute df_resid so check could not run",
                None,
            )

        dof: int = model.df_resid
        threshold: int = self.risk_appetite["safe_dof_threshold"]
        if dof < threshold:
            summary = f"fail; dof={dof} < {threshold}"
            warnings.warn(f"Unsafe {name}: {summary}", stacklevel=8)
        else:
            status = "pass"
            summary = f"pass; dof={dof} >= {threshold}"

        logger.info("in checks.check_model_dof()")
        logger.info(
            "%s(), status: %s(), summary: %s(), outcome: %s", name, status, summary, dof
        )
        return status, summary, dof

    # def check_all_same(self, name: str, model: Any) -> tuple[str, str, pd.DataFrame]:
    #     """Check whether all values in cells are the same .

    #     Parameters
    #     ----------
    #     name : str
    #         The name of the model.
    #     model : dict
    #         definition of a table

    #     Returns
    #     -------
    #     str
    #         Status: {"review", "fail", "pass"}.
    #     str
    #         Summary of the check.
    #     pandas DataFrame
    #         binary mask with same config as the underlying table.
    #     """

    # def check_min_threshold(
    #     self, name: str, model: Any
    # ) -> tuple[str, str, pd.DataFrame]:
    #     """Check for small numbers of respondents in cells.

    #     Parameters
    #     ----------
    #     name : str
    #         The name of the model.
    #     model : dict
    #         definition of a table

    #     Returns
    #     -------
    #     str
    #         Status: {"review", "fail", "pass"}.
    #     str
    #         Summary of the check.
    #     pandas DataFrame
    #         binary mask with same config as the underlying table.
    #     """

    def manual_check(self, name: str, model: Any) -> tuple[str, str, Any]:
        """Report that a manual check is needed.

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
        return (
            "review",
            (
                f"Review: {name}: a manual check is needed for possible linked tables"
                f" variables defining table are:  {model['args']}"
            ),
            None,
        )

    # def check_nk_dominance(
    #     self, name: str, model: Any
    # ) -> tuple[str, str, pd.DataFrame]:
    #     """Check for NK dominace within each cell.

    #     Parameters
    #     ----------
    #     name : str
    #         The name of the model.
    #     model : dict
    #         definition of a table

    #     Returns
    #     -------
    #     str
    #         Status: {"review", "fail", "pass"}.
    #     str
    #         Summary of the check.
    #     pandas DataFrame
    #         binary mask with same config as the underlying table.
    #     """

    # def check_pq_dominance(
    #     self, name: str, model: Any
    # ) -> tuple[str, str, pd.DataFrame]:
    #     """Check for PQ dominance within each cell.

    #     Parameters
    #     ----------
    #     name : str
    #         The name of the model.
    #     model : dict
    #         definition of a table

    #     Returns
    #     -------
    #     str
    #         Status: {"review", "fail", "pass"}.
    #     str
    #         Summary of the check.
    #     pandas DataFrame
    #         binary mask with same config as the underlying table.
    #    """

    def check_linked_table(self, name: str, model: Any) -> tuple[str, str, Any]:
        """Check for presence of linked tables.

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
        if not (
            isinstance(model, dict)
            and "rows" in model.keys()
            and "cols" in model.keys()
        ):
            return (
                "fail",
                f"{name}:insufficient/inappropriate details passed to the check function",
                None,
            )
        return (
            "review",
            (
                "Review: a manual check is needed for possible linked tables"
                f" variables defining table are:  {model['args']}"
            ),
            None,
        )

    def check_required_zero(
        self, name: str, model: Any
    ) -> tuple[str, str, pd.DataFrame]:
        """Check for.

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
        if not (
            isinstance(model, dict)
            and "rows" in model.keys()
            and "cols" in model.keys()
        ):
            return (
                "fail",
                f"{name}: insufficient/inappropriate details passed to the check function",
                None,
            )
        # make any old table- so frequencies will do
        df = pd.crosstab(model["rows"], model["cols"], dropna=False)
        for col in df.columns:
            df[col].values[:] = 0

        if self.risk_appetite["zeros_are_disclosive"]:
            for col in df.columns:
                df[col].values[:] = 1
            return "pass", "zeros are considered disclosive", df

        return "pass", "zeros are not disclosive", df

    # def check_presence_of_zero(
    #     self, name: str, model: Any
    # ) -> tuple[str, str, pd.DataFrame]:
    #     """Check for presence of cells with values zero.

    #     Parameters
    #     ----------
    #     name : str
    #         The name of the model.
    #     model : dict
    #         definition of a table

    #     Returns
    #     -------
    #     str
    #         Status: {"review", "fail", "pass"}.
    #     str
    #         Summary of the check.
    #     pandas DataFrame
    #         binary mask with same config as the underlying table.
    #     """
    #     if not (
    #         isinstance(model, dict) and 'rows' in model.keys() and 'cols' in model.keys()
    #     ):
    #         return (
    #             "fail",
    #             "insufficient/inappropriate details passed to the check function",
    #             None,
    #         )
    #     # make any old table- so frequencies will do
    #     df = pd.crosstab(rows, cols, dropna=False)
    #       UNFINISHED
