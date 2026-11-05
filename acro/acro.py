"""ACRO: Automatic Checking of Research Outputs."""

from __future__ import annotations

import json
import logging
import os
import pathlib
import warnings
from typing import Any

import yaml

from . import acro_tables, sdcchecks
from .acro_regression import Regression
from .acro_tables import Tables
from .record import Records
from .version import __version__

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("acro")
warnings.simplefilter(action="ignore", category=FutureWarning)


class ACRO(Tables, Regression):
    """ACRO: Automatic Checking of Research Outputs.

    Attributes
    ----------
    config : dict
        Safe parameters and their values.
    results : Records
        The current outputs including the results of checks.
    mitigation : str
        The disclosure-control strategy applied to outputs, one of ``"none"``,
        ``"suppress"``, ``"round"``.
    round_base : int
        The base to round to when ``mitigation == "round"``.
    suppress : bool
        Backward-compatible alias. ``True`` is equivalent to
        ``mitigation == "suppress"``.

    Examples
    --------
    >>> acro = ACRO()
    >>> results = acro.ols(
    ...     y, x
    ... )
    >>> results.summary()
    >>> acro.finalise(
    ...     "MYFOLDER",
    ...     "json",
    ... )
    """

    def __init__(
        self,
        config: str = "default",
        suppress: bool = False,
        mitigation: str | None = None,
        round_base: int | None = None,
        federated: bool | None = None,
    ) -> None:
        """Construct a new ACRO object and reads parameters from config.

        Parameters
        ----------
        config : str
            Name of a yaml configuration file with safe parameters.
        suppress : bool, default False
            Whether to automatically apply suppression (back-compat alias for
            ``mitigation="suppress"``). Ignored when ``mitigation`` is set.
        mitigation : str, optional
            The disclosure-control strategy to apply, one of ``"none"``,
            ``"suppress"``, ``"round"``. When ``None``, derived from
            ``suppress``.
        round_base : int, optional
            The base to round to when ``mitigation="round"``. Defaults to the
            ``safe_round_base`` value from the yaml config.
        federated : bool, optional
            Whether to run in federated mode. When ``True``, no SDC checks
            are performed; instead, evidence is collected and written to
            ``evidence.json`` for a trusted aggregator to review. When
            ``None``, falls back to the yaml config value (default ``False``).
            In standalone mode (``False``), outputs are checked and a
            ``results.json`` file is created.

        Notes
        -----
        **Federated vs Standalone Mode**:

        - **Standalone (default)**: ACRO checks outputs locally and produces
          ``results.json`` with pass/fail/review statuses.
        - **Federated mode**: ACRO collects evidence in ``evidence.json``
          without performing checks, for later review by a trusted aggregator.

        Examples
        --------
        >>> import acro
        >>> # Standalone mode with suppression
        >>> acro_session = acro.ACRO(suppress=True)
        >>>
        >>> # Federated mode for TRE aggregator
        >>> acro_fed = acro.ACRO(federated=True)
        >>>
        >>> # Custom configuration
        >>> acro_custom = acro.ACRO(config="my_config", mitigation="round")
        """
        Tables.__init__(self, suppress=suppress, mitigation=mitigation)
        Regression.__init__(self, config)
        self._federated_override = federated  # applied after yaml is loaded
        self.config: dict[str, Any] = {}
        path: pathlib.Path = pathlib.Path(__file__).with_name(config + ".yaml")
        logger.debug("path: %s", path)
        with open(path, encoding="utf-8") as handle:
            self.config = yaml.load(handle, Loader=yaml.loader.SafeLoader)

        # Tables and Regression each construct their own ``self.results`` so
        # they can be used standalone; in the combined ACRO object we want a
        # single shared Records instance regardless of init order, so make
        # that explicit here.
        self.results: Records = Records(
            blocked_extensions=self.config.get("blocked_extensions", [])
        )

        # Preserve the user-requested suppress value alongside the yaml config.
        # Tables.suppress is now a property derived from the live mitigation, so
        # it can drift over a session (enable_rounding flips mitigation away from
        # 'suppress'). Recording the original ask here keeps it available for
        # callers that need to re-enforce suppression for disclosive outputs.
        self.config["suppress"] = suppress

        # set globals and instance state for the round mitigation strategy
        acro_tables.SAFE_ROUND_BASE = self.config.get(
            "safe_round_base", acro_tables.SAFE_ROUND_BASE
        )
        self.round_base = (
            round_base if round_base is not None else acro_tables.SAFE_ROUND_BASE
        )
        logger.info("version: %s", __version__)
        logger.info("config: %s", self.config)
        logger.info("mitigation: %s (round_base=%s)", self.mitigation, self.round_base)

        # make object to handle all the ontology-driven checking
        self.sdc_checks = sdcchecks.SDCChecks(self.config)

        if self._federated_override is not None:
            self.federated: bool = bool(self._federated_override)
        else:
            self.federated = bool(self.config.get("federated", False))
        self.config["federated"] = self.federated
        logger.info("federated: %s", self.federated)

    def describe_analysis_risks(self, analysis_name: str) -> str:
        """Describe the ontology risks and checks for an analysis type.

        Parameters
        ----------
        analysis_name : str
            Case-sensitive ontology analysis name, for example ``Mean``.

        Returns
        -------
        str
            Analysis and statbarn definitions, source URIs, risks and checks.
            This describes potential risks, not a risk assessment of an output.

        Raises
        ------
        ValueError
            If the analysis name is unknown.
        """
        analysis = self._description_entry(
            self.sdc_checks.analyses, analysis_name, "analysis"
        )
        statbarn_name = analysis["statbarn"]
        statbarn = self.sdc_checks.statbarns[statbarn_name]
        sections = [
            f"Analysis: {analysis_name}\n{analysis['definition']}\n{analysis['uri']}",
            f"Statbarn: {statbarn_name}\n{statbarn['definition']}\n{statbarn['uri']}",
        ]
        sections.extend(self.describe_risk(risk) for risk in statbarn["risks"])
        if not statbarn["risks"]:
            sections.append(
                "No risks listed in the ontology; this does not imply safety."
            )
        return "\n\n".join(sections)

    def describe_risk(self, risk_name: str) -> str:
        """Return a risk's definition, source URI and associated check descriptions.

        Parameters
        ----------
        risk_name : str
            Case-sensitive ontology risk name, for example ``Dominance``.

        Returns
        -------
        str
            Risk definition and associated checks.

        Raises
        ------
        ValueError
            If the risk name is unknown.
        """
        risk = self._description_entry(self.sdc_checks.risks, risk_name, "risk")
        sections = [f"Risk: {risk_name}\n{risk['definition']}\n{risk['uri']}"]
        sections.extend(self.describe_check(check) for check in risk["checks"])
        if not risk["checks"]:
            sections.append("No checks listed in the ontology.")
        return "\n\n".join(sections)

    def describe_check(self, check_name: str) -> str:
        """Return a check's definition, source URI and required evidence.

        Parameters
        ----------
        check_name : str
            Case-sensitive ontology check name, for example ``MinimumThresholdCheck``.

        Returns
        -------
        str
            Check definition and required evidence.

        Raises
        ------
        ValueError
            If the check name is unknown.
        """
        check = self._description_entry(self.sdc_checks.checks, check_name, "check")
        evidence = ", ".join(check["evidence"]) or "None listed"
        return (
            f"Check: {check_name}\n{check['definition']}\n{check['uri']}\n"
            f"Required evidence: {evidence}"
        )

    def describe_risk_appetite(self, parameter_name: str) -> str:
        """Explain a risk-appetite parameter and report its current session value.

        Parameters
        ----------
        parameter_name : str
            Configuration key, for example ``safe_threshold``.

        Returns
        -------
        str
            Parameter explanation and current session value.

        Raises
        ------
        ValueError
            If the name is not a supported parameter present in this session.
        """
        descriptions = {
            "safe_threshold": "Minimum number of records required in a group.",
            "safe_dof_threshold": "Minimum residual degrees of freedom required for a model.",
            "safe_nk_n": "Number of largest values used in the N-K dominance check.",
            "safe_nk_k": "Dominance limit for the largest N values, expressed as a proportion of the total.",
            "safe_pratio_p": "Minimum ratio of the sum of the smallest N-2 values to the largest value.",
            "check_missing_values": "Whether to check for missing values.",
            "survival_safe_threshold": "Minimum frequency used for survival tables and plots.",
            "zeros_are_disclosive": "Whether zero counts are considered potentially disclosive.",
            "safe_round_base": "Configured default rounding base for table mitigation.",
        }
        available = {
            name: description
            for name, description in descriptions.items()
            if name in self.sdc_checks.risk_appetite
        }
        description = self._description_entry(
            available, parameter_name, "risk-appetite parameter"
        )
        value = self.sdc_checks.risk_appetite[parameter_name]
        return f"Risk appetite: {parameter_name}\n{description}\nCurrent value: {value}"

    @staticmethod
    def _description_entry(entries: dict, name: str, kind: str) -> Any:
        """Look up an explanation entry, reporting available names on failure."""
        if name not in entries:
            raise ValueError(
                f"Unknown {kind} {name!r}. Available names: {', '.join(sorted(entries))}"
            )
        return entries[name]

    def finalise(
        self, path: str = "outputs", ext: str = "json", interactive: bool = False
    ) -> Records | None:
        """Create a results file for checking.

        Parameters
        ----------
        path : str
            Name of a folder to save outputs.
        ext : str
            Extension of the results file. Valid extensions: {json, xlsx}.
        interactive : bool
            Whether to prompt the user to request exceptions for failing outputs.

        Returns
        -------
        Records
            Object storing the outputs.
        """
        # check if the path exists
        if os.path.exists(path):
            logger.warning(
                "Results file can not be created. "
                "Directory %s already exists. "
                "Please choose a different directory name.",
                path,
            )
            return None

        if self.federated:
            os.makedirs(path, exist_ok=True)
            merged_evidence: dict = dict(getattr(self, "_federated_evidence", {}))
            evidence_data = self.results.finalise_evidence(path, merged_evidence)
            evidence_filename: str = os.path.normpath(f"{path}/evidence.json")
            with open(evidence_filename, "w", newline="", encoding="utf-8") as fh:
                json.dump(evidence_data, fh, indent=4, sort_keys=False)
            logger.info("federated evidence written to: %s", path)
        else:
            self.results.finalise(path, ext, interactive)

        config_filename: str = os.path.normpath(f"{path}/config.json")
        try:
            with open(config_filename, "w", newline="", encoding="utf-8") as file:
                json.dump(self.config, file, indent=4, sort_keys=False)
        except FileNotFoundError:  # pragma: no cover
            logger.debug(
                "The config file will not be created because the "
                "output folder was not created as the acro object was empty."
            )
        return self.results

    def remove_output(self, key: str) -> None:
        """Remove an output from the results.

        Parameters
        ----------
        key : str
            Key specifying which output to remove, e.g., 'output_0'.
        """
        self.results.remove(key)

    def print_outputs(self) -> str:
        """Print the current results dictionary.

        Returns
        -------
        str
            String representation of all outputs.
        """
        return self.results.print()

    def custom_output(self, filename: str, comment: str = "") -> bool:
        """Add an unsupported output to the results dictionary.

        Parameters
        ----------
        filename : str
            The name of the file that will be added to the list of the outputs.
        comment : str
            An optional comment.

        Returns
        -------
        bool
            False if the file extension is blocked, True otherwise.
        """
        return self.results.add_custom(filename, comment)

    def rename_output(self, old: str, new: str) -> None:
        """Rename an output.

        Parameters
        ----------
        old : str
            The old name of the output.
        new : str
            The new name of the output.
        """
        self.results.rename(old, new)

    def add_comments(self, output: str, comment: str) -> None:
        """Add a comment to an output.

        Parameters
        ----------
        output : str
            The name of the output.
        comment : str
            The comment.
        """
        self.results.add_comments(output, comment)

    def add_exception(self, output: str, reason: str) -> None:
        """Add an exception request to an output.

        Parameters
        ----------
        output : str
            The name of the output.
        reason : str
            The comment.
        """
        self.results.add_exception(output, reason)

    def enable_suppression(self) -> None:
        """Turn suppression on during a session."""
        self.suppress = True

    def disable_suppression(self) -> None:
        """Turn suppression off during a session."""
        self.suppress = False

    def enable_rounding(self, base: int | None = None) -> None:
        """Turn rounding on. Overwrites any prior suppress=True (not restored on disable_rounding)."""
        if base is not None:
            self.round_base = base
        self.mitigation = "round"

    def disable_rounding(self) -> None:
        """Turn rounding off. Always falls back to mitigation='none' (prior suppress not restored)."""
        if self.mitigation == "round":
            self.mitigation = "none"

    def show_fair_summaries(self) -> str:
        """Print IDs and FAIR summaries for all outputs in session.

        Returns a formatted string containing metadata about each output,
        including dependent and independent variables tracked during analysis.

        Returns
        -------
        str
            Formatted summary of all outputs with their FAIR dictionaries.

        Examples
        --------
        >>> import acro
        >>> session = acro.ACRO()
        >>> session.ols(y, X)  # doctest: +SKIP
        >>> print(session.show_fair_summaries())  # doctest: +SKIP
        output_0
        dependent : income
        independent : ['age', 'education']
        """
        thestr = ""
        for uid, value in self.results.results.items():
            thestr += uid + "\n"
            for key, val in value.fair.items():
                if isinstance(val, dict):
                    for key2, val2 in val.items():
                        thestr += f"{key2} : {val2}\n"
                else:
                    thestr += f"{key}:{val}\n"
        return thestr + "\n"


def add_to_acro(src_path: str, dest_path: str = "sdc_results") -> None:
    """Add outputs to an acro object and creates a results file for checking.

    Parameters
    ----------
    src_path : str
        Name of the folder with outputs produced without using acro.
    dest_path : str
        Name of the folder to save outputs.
    """
    acro: ACRO = ACRO()
    # add the files from the folder to an acro obj
    for output_id, file in enumerate(os.listdir(src_path)):
        filename: str = os.path.join(src_path, file)
        acro.custom_output(filename)
        acro.rename_output(f"output_{output_id}", file)
    acro.finalise(dest_path, "json")
