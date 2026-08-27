"""ACRO: Session Summary Report Generation."""

from __future__ import annotations

import datetime
import json
import logging
import os
from typing import Any

import numpy as np

from .version import __version__

logger = logging.getLogger("acro:summary")

# Module-level constants
SUMMARY_OUTPUT_TYPE = "summary_report"
SUMMARY_FILENAME = "session_summary.json"
SUMMARY_WARNING_COMMENT = "DO NOT RELEASE - SUMMARY FOR OUTPUT CHECKER USE ONLY"


class MetadataExtractor:
    """Extracts metadata from Records for summary reporting."""

    @staticmethod
    def extract_session_metadata(
        records: Any, timestamp: str, acro_version: str
    ) -> dict[str, Any]:
        """Extract session-level metadata.

        Parameters
        ----------
        records : Records
            The Records object containing all session outputs.
        timestamp : str
            ISO format timestamp when finalise() was called.
        acro_version : str
            The ACRO version string.

        Returns
        -------
        dict[str, Any]
            Dictionary with keys: version, timestamp, total_outputs,
            status_counts, type_counts.
        """
        total_outputs = len(records.results)

        status_counts: dict[str, int] = {}
        for record in records.results.values():
            status = record.status
            status_counts[status] = status_counts.get(status, 0) + 1

        type_counts: dict[str, int] = {}
        for record in records.results.values():
            output_type = record.output_type
            type_counts[output_type] = type_counts.get(output_type, 0) + 1

        return {
            "version": acro_version,
            "timestamp": timestamp,
            "total_outputs": total_outputs,
            "status_counts": status_counts,
            "type_counts": type_counts,
        }

    @staticmethod
    def extract_output_metadata(record: Any) -> dict[str, Any]:
        """Extract metadata for a single output.

        Parameters
        ----------
        record : Record
            A single output record.

        Returns
        -------
        dict[str, Any]
            Dictionary with keys: uid, output_type, dependent_variables,
            independent_variables, analysis_name.
        """
        uid = record.uid
        output_type = record.output_type
        fair = record.fair if record.fair else {}
        properties = record.properties if record.properties else {}

        dependent_variables = fair.get("dependent", "unknown")
        if dependent_variables is None:
            dependent_variables = "unknown"

        independent_variables = fair.get("independent", [])
        if independent_variables is None:
            independent_variables = []

        # Determine analysis_name from fair, properties, command, or output_type
        analysis_name = fair.get("analysis_name")
        if not analysis_name:
            analysis_name = properties.get("method")
        if not analysis_name and hasattr(record, "command") and record.command:
            analysis_name = record.command.split("(")[0].strip()
        if not analysis_name:
            analysis_name = output_type if output_type else "unknown"

        return {
            "uid": uid,
            "output_type": output_type,
            "dependent_variables": dependent_variables,
            "independent_variables": independent_variables,
            "analysis_name": analysis_name,
        }


class VariableMatrixBuilder:
    """Builds variable usage matrix from output metadata."""

    @staticmethod
    def get_all_variables(metadata: dict[str, Any]) -> set[str]:
        """Get set of all unique variables from a single output metadata.

        Parameters
        ----------
        metadata : dict[str, Any]
            Output metadata dictionary with 'dependent_variables' and
            'independent_variables' keys.

        Returns
        -------
        set[str]
            All unique variable names (dependent and independent) from this output.
        """
        variables: set[str] = set()

        # Handle dependent_variables - can be string, list, tuple, or set
        dep = metadata.get("dependent_variables", "unknown")
        if isinstance(dep, str):
            if dep and dep not in ("unknown", "none"):
                variables.add(dep)
        elif isinstance(dep, (list, tuple, set)):
            for item in dep:
                if isinstance(item, str) and item and item not in ("unknown", "none"):
                    variables.add(item)

        # Handle independent_variables - can be list, tuple, set, or string
        indep = metadata.get("independent_variables", [])
        if isinstance(indep, (list, tuple, set)):
            for item in indep:
                if isinstance(item, str) and item and item not in ("unknown", "none"):
                    variables.add(item)
        elif isinstance(indep, str):
            if indep and indep not in ("unknown", "none"):
                variables.add(indep)

        return variables

    @staticmethod
    def build_matrix(
        output_metadata_list: list[dict[str, Any]],
    ) -> dict[str, dict[str, int]]:
        """Build variable usage matrix.

        Parameters
        ----------
        output_metadata_list : list[dict[str, Any]]
            List of output metadata dictionaries from MetadataExtractor.

        Returns
        -------
        dict[str, dict[str, int]]
            Nested dictionary structure:
            {
                output_uid: {
                    variable_name: 1 or 0
                }
            }
        """
        all_variables = sorted(
            {
                var
                for metadata in output_metadata_list
                for var in VariableMatrixBuilder.get_all_variables(metadata)
            }
        )

        matrix: dict[str, dict[str, int]] = {}
        for metadata in output_metadata_list:
            uid = metadata.get("uid")
            if uid is None:
                continue

            output_variables = VariableMatrixBuilder.get_all_variables(metadata)
            matrix[uid] = {
                var: 1 if var in output_variables else 0 for var in all_variables
            }

        return matrix


class SummaryGenerator:
    """Generates session summary reports from ACRO Records."""

    def __init__(self, records: Any, acro_version: str) -> None:
        """Initialize the summary generator.

        Parameters
        ----------
        records : Records
            The Records object containing all session outputs.
        acro_version : str
            The ACRO version string from __version__.
        """
        self.records = records
        self.acro_version = acro_version
        self.logger = logging.getLogger("acro:summary")

    def generate(self) -> dict[str, Any]:
        """Generate the complete summary report.

        Returns
        -------
        dict[str, Any]
            Complete summary report structure with metadata, outputs,
            and variable_matrix sections.
        """
        timestamp = datetime.datetime.now().isoformat()

        metadata = MetadataExtractor.extract_session_metadata(
            self.records, timestamp, self.acro_version
        )

        output_metadata_list = [
            MetadataExtractor.extract_output_metadata(record)
            for record in self.records.results.values()
        ]

        variable_matrix = VariableMatrixBuilder.build_matrix(output_metadata_list)

        return {
            "metadata": metadata,
            "outputs": output_metadata_list,
            "variable_matrix": variable_matrix,
        }


def generate_session_summary(records: Any, output_path: str) -> None:
    """Generate and save session summary report.

    This is the main entry point for summary generation, called from Records.finalise().
    It creates a SummaryGenerator instance, generates the summary, writes it to JSON,
    and adds it as a custom output to the Records object.

    Parameters
    ----------
    records : Records
        The Records object containing all session outputs.
    output_path : str
        Path to the outputs directory where session_summary.json will be written.
    """
    generator = SummaryGenerator(records, __version__)
    summary = generator.generate()
    summary = _convert_numpy_types(summary)

    summary_path = os.path.normpath(f"{output_path}/{SUMMARY_FILENAME}")

    try:
        os.makedirs(output_path, exist_ok=True)
        with open(summary_path, "w", encoding="utf-8") as file:
            json.dump(summary, file, indent=4)
        logger.info("Session summary written to: %s", summary_path)
    except Exception as e:
        logger.error("Failed to write session summary to %s: %s", summary_path, str(e))
        return

    try:
        records.add_custom(summary_path, comment=SUMMARY_WARNING_COMMENT)
        logger.info("Session summary added as custom output to Records")
    except Exception as e:
        logger.error("Failed to add session summary as custom output: %s", str(e))


def _convert_numpy_types(obj: Any) -> Any:
    """Recursively convert numpy types to Python native types for JSON serialization.

    Parameters
    ----------
    obj : Any
        Object to convert (can be dict, list, or primitive type).

    Returns
    -------
    Any
        Object with all numpy types converted to Python native types.
    """
    if isinstance(obj, dict):
        return {key: _convert_numpy_types(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert_numpy_types(item) for item in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def load_session_summary(path: str) -> dict[str, Any]:
    """Load and parse a previously generated session summary report.

    Parameters
    ----------
    path : str
        Path to the directory containing session_summary.json.

    Returns
    -------
    dict[str, Any]
        Parsed summary dictionary with metadata, outputs, and variable_matrix.

    Raises
    ------
    FileNotFoundError
        If session_summary.json does not exist in the specified path.
    ValueError
        If the JSON file is missing required sections or is invalid JSON.
    """
    summary_path = os.path.normpath(f"{path}/{SUMMARY_FILENAME}")

    if not os.path.exists(summary_path):
        raise FileNotFoundError(f"Session summary not found: {summary_path}")

    try:
        with open(summary_path, encoding="utf-8") as file:
            summary = json.load(file)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in session summary file: {str(e)}") from e
    except Exception as e:
        raise ValueError(f"Failed to read session summary file: {str(e)}") from e

    required_sections = ["metadata", "outputs", "variable_matrix"]
    missing_sections = [
        section for section in required_sections if section not in summary
    ]

    if missing_sections:
        raise ValueError(
            f"Session summary missing required sections: {', '.join(missing_sections)}"
        )

    return summary
