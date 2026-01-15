"""ACRO: Output storage and serialization."""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

import pandas as pd
from pandas import DataFrame

from .version import __version__

logger = logging.getLogger("acro:records")


def load_outcome(outcome: dict) -> DataFrame:
    """Return a DataFrame from an outcome dictionary.

    Parameters
    ----------
    outcome : dict
        The outcome to load as a DataFrame.
    """
    return pd.DataFrame.from_dict(outcome)


def load_output(path: str, output: list[str]) -> list[str] | list[DataFrame]:
    """Return a loaded output.

    Parameters
    ----------
    path : str
        The path to the output folder (with results.json).
    output : list[str]
        The output to load.

    Returns
    -------
    list[str] | list[DataFrame]
        The loaded output field.
    """
    if len(output) < 1:
        raise ValueError("error loading output")
    loaded: list[DataFrame] = []
    for filename in output:
        _, ext = os.path.splitext(filename)
        if ext == ".csv":
            filename = os.path.normpath(f"{path}/{filename}")
            loaded.append(pd.read_csv(filename))
    if len(loaded) < 1:  # output is path(s) to custom file(s)
        return output
    return loaded


class Record:  # pylint: disable=too-many-instance-attributes
    """Stores data related to a single output record.

    Attributes
    ----------
    uid : str
        Unique identifier.
    status : str
        SDC status: {"pass", "fail", "review"}
    output_type : str
        Type of output, e.g., "regression"
    properties : dict
        Dictionary containing structured output data.
    sdc : dict
        Dictionary containing SDC results.
    command : str
        String representation of the operation performed.
    summary : str
        String summarising the ACRO checks.
    outcome : DataFrame
        DataFrame describing the details of ACRO checks.
    output : Any
        List of output DataFrames.
    comments : list[str]
        List of strings entered by the user to add comments to the output.
    exception : str
        Description of why an exception to fail/review should be granted.
    timestamp : str
        Time the record was created in ISO format.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        uid: str,
        status: str,
        output_type: str,
        properties: dict,
        sdc: dict,
        command: str,
        summary: str,
        outcome: DataFrame,
        output: list[str] | list[DataFrame],
        comments: list[str] | None = None,
    ) -> None:
        """Construct a new output record.

        Parameters
        ----------
        uid : str
            Unique identifier.
        status : str
            SDC status: {"pass", "fail", "review"}
        output_type : str
            Type of output, e.g., "regression"
        properties : dict
            Dictionary containing structured output data.
        sdc : dict
            Dictionary containing SDC results.
        command : str
            String representation of the operation performed.
        summary : str
            String summarising the ACRO checks.
        outcome : DataFrame
            DataFrame describing the details of ACRO checks.
        output : list[str] | list[DataFrame]
            List of output DataFrames.
        comments : list[str] | None, default None
            List of strings entered by the user to add comments to the output.
        """
        self.uid: str = uid
        self.status: str = status
        self.output_type: str = output_type
        self.properties: dict = properties
        self.sdc: dict = sdc
        self.command: str = command
        self.summary: str = summary
        self.outcome: DataFrame = outcome
        self.output: Any = output
        self.comments: list[str] = [] if comments is None else comments
        self.exception: str = ""
        now = datetime.datetime.now()
        self.timestamp: str = now.isoformat()

    def serialize_output(self, path: str = "outputs") -> list[str]:
        """Serialize outputs.

        Parameters
        ----------
        path : str, default 'outputs'
            Name of the folder that outputs are to be written.

        Returns
        -------
        list[str]
            List of filepaths of the written outputs.
        """
        output: list[str] = []
        # check if the outputs directory was already created
        try:  # pragma: no cover
            os.makedirs(path)
            logger.debug("Directory %s created successfully", path)
        except FileExistsError:
            logger.debug("Directory %s already exists", path)
        # save each output DataFrame to a different csv
        if all(isinstance(obj, DataFrame) for obj in self.output):
            for i, data in enumerate(self.output):
                filename = f"{self.uid}_{i}.csv"
                output.append(filename)
                filename = os.path.normpath(f"{path}/{filename}")
                with open(filename, mode="w", newline="", encoding="utf-8") as file:
                    file.write(data.to_csv())
        # move custom files to the output folder
        if self.output_type == "custom":
            for filename in self.output:
                if os.path.exists(filename):
                    shutil.copy(filename, path)
                    output.append(Path(filename).name)
        if self.output_type in ["survival plot", "histogram"]:
            for filename in self.output:
                if os.path.exists(filename):
                    output.append(Path(filename).name)
                    shutil.copy(filename, path)
        return output

    def __str__(self) -> str:
        """Return a string representation of a record.

        Returns
        -------
        str
            The record.
        """
        return (
            f"uid: {self.uid}\n"
            f"status: {self.status}\n"
            f"type: {self.output_type}\n"
            f"properties: {self.properties}\n"
            f"sdc: {self.sdc}\n"
            f"command: {self.command}\n"
            f"summary: {self.summary}\n"
            f"outcome: {self.outcome}\n"
            f"output: {self.output}\n"
            f"timestamp: {self.timestamp}\n"
            f"comments: {self.comments}\n"
            f"exception: {self.exception}\n"
        )


class Records:
    """Stores data related to a collection of output records."""

    def __init__(self) -> None:
        """Construct a new object for storing multiple records."""
        self.results: dict[str, Record] = {}
        self.output_id: int = 0

    def add(  # pylint: disable=too-many-arguments
        self,
        status: str,
        output_type: str,
        properties: dict,
        sdc: dict,
        command: str,
        summary: str,
        outcome: DataFrame,
        output: list[str] | list[DataFrame],
        comments: list[str] | None = None,
    ) -> None:
        """Add an output to the results.

        Parameters
        ----------
        status : str
            SDC status: {"pass", "fail", "review"}
        output_type : str
            Type of output, e.g., "regression"
        properties : dict
            Dictionary containing structured output data.
        sdc : dict
            Dictionary containing SDC results.
        command : str
            String representation of the operation performed.
        summary : str
            String summarising the ACRO checks.
        outcome : DataFrame
            DataFrame describing the details of ACRO checks.
        output : list[str | list[DataFrame]
            List of output DataFrames.
        comments : list[str] | None, default None
            List of strings entered by the user to add comments to the output.
        """
        new = Record(
            uid=f"output_{self.output_id}",
            status=status,
            output_type=output_type,
            properties=properties,
            sdc=sdc,
            command=command,
            summary=summary,
            outcome=outcome,
            output=output,
            comments=comments,
        )
        self.results[new.uid] = new
        self.output_id += 1
        logger.info("add(): %s", new.uid)

    def remove(self, key: str) -> None:
        """Remove an output from the results.

        Parameters
        ----------
        key : str
            Key specifying which output to remove, e.g., 'output_0'.
        """
        if key not in self.results:
            raise ValueError(f"unable to remove {key}, key not found")
        del self.results[key]
        logger.info("remove(): %s removed", key)

    def get(self, key: str) -> Record:
        """Return a specified output from the results.

        Parameters
        ----------
        key : str
            Key specifying which output to return, e.g., 'output_0'.

        Returns
        -------
        Record
            The requested output.
        """
        logger.debug("get(): %s ", key)
        return self.results[key]

    def get_keys(self) -> list[str]:
        """Return the list of available output keys.

        Returns
        -------
        list[str]
            List of output names.
        """
        logger.debug("get_keys()")
        return list(self.results.keys())

    def get_index(self, index: int) -> Record:
        """Return the output at the specified position.

        Parameters
        ----------
        index : int
            Position of the output to return.

        Returns
        -------
        Record
            The requested output.
        """
        logger.debug("get_index(): %s", index)
        key = list(self.results.keys())[index]
        return self.results[key]

    def add_custom(self, filename: str, comment: str | None = None) -> None:
        """Add an unsupported output to the results dictionary.

        Parameters
        ----------
        filename : str
            The name of the file that will be added to the list of the outputs.
        comment : str | None, default None
            An optional comment.
        """
        if os.path.exists(filename):
            output = Record(
                uid=f"output_{self.output_id}",
                status="review",
                output_type="custom",
                properties={},
                sdc={},
                command="custom",
                summary="review",
                outcome=DataFrame(),
                output=[os.path.normpath(filename)],
                comments=None if comment is None else [comment],
            )
            self.results[output.uid] = output
            self.output_id += 1
            logger.info("add_custom(): %s", output.uid)
        else:
            logger.info(
                "WARNING: Unable to add %s because the file does not exist", filename
            )  # pragma: no cover

    def rename(self, old: str, new: str) -> None:
        """Rename an output.

        Parameters
        ----------
        old : str
            The old name of the output.
        new : str
            The new name of the output.
        """
        if old not in self.results:
            raise ValueError(f"unable to rename {old}, key not found")
        if new in self.results:
            raise ValueError(f"unable to rename, {new} already exists")
        self.results[new] = self.results[old]
        self.results[new].uid = new
        del self.results[old]
        logger.info("rename_output(): %s renamed to %s", old, new)

    def add_comments(self, output: str, comment: str) -> None:
        """Add a comment to an output.

        Parameters
        ----------
        output : str
            The name of the output.
        comment : str
            The comment.
        """
        if output not in self.results:
            raise ValueError(f"unable to find {output}, key not found")
        self.results[output].comments.append(comment)
        logger.info("a comment was added to %s", output)

    def add_exception(self, output: str, reason: str) -> None:
        """Add an exception request to an output.

        Parameters
        ----------
        output : str
            The name of the output.
        reason : str
            The reason the output should be released.
        """
        if output not in self.results:
            raise ValueError(f"unable to add exception: {output} not found")
        self.results[output].exception = reason
        logger.info("exception request was added to %s", output)

    def print(self) -> str:
        """Print the current results.

        Returns
        -------
        str
            String representation of all outputs.
        """
        logger.debug("print()")
        outputs: str = ""
        for _, record in self.results.items():
            outputs += str(record) + "\n"
        print(outputs)
        return outputs

    def validate_outputs(self) -> None:
        """Prompt researcher to complete any required fields."""
        for _, record in self.results.items():
            if record.status != "pass" and record.exception == "":
                logger.info(
                    "\n%s\n"
                    "The status of the record above is: %s.\n"
                    "Please explain why an exception should be granted.\n",
                    str(record),
                    record.status,
                )
                record.exception = input("")

    def finalise(self, path: str, ext: str) -> None:
        """Create a results file for checking.

        Parameters
        ----------
        path : str
            Name of a folder to save outputs.
        ext : str
            Extension of the results file. Valid extensions: {json, xlsx}.
        """
        logger.debug("finalise()")
        self.validate_outputs()
        if ext == "json":
            self.finalise_json(path)
        elif ext == "xlsx":
            self.finalise_excel(path)
        else:
            raise ValueError("Invalid file extension. Options: {json, xlsx}")
        self.write_checksums(path)
        # check if the directory acro_artifacts exists and delete it
        if os.path.exists("acro_artifacts"):
            shutil.rmtree("acro_artifacts")
        logger.info("outputs written to: %s", path)

    def finalise_json(self, path: str) -> None:
        """Write outputs to a JSON file.

        Parameters
        ----------
        path : str
            Name of a folder to save outputs.
        """
        outputs: dict = {}
        for key, val in self.results.items():
            outputs[key] = {
                "uid": val.uid,
                "status": val.status,
                "type": val.output_type,
                "properties": val.properties,
                "files": [],
                "outcome": json.loads(val.outcome.to_json()),
                "command": val.command,
                "summary": val.summary,
                "timestamp": val.timestamp,
                "comments": val.comments,
                "exception": val.exception,
            }
            files: list[str] = val.serialize_output(path)
            for file in files:
                outputs[key]["files"].append({"name": file, "sdc": val.sdc})

        results: dict = {"version": __version__, "results": outputs}
        filename: str = os.path.normpath(f"{path}/results.json")
        try:
            with open(filename, "w", newline="", encoding="utf-8") as handle:
                json.dump(results, handle, indent=4, sort_keys=False)
        except FileNotFoundError:  # pragma: no cover
            logger.info(
                "You don't have any output in the acro object. "
                "Directory %s will not be created.",
                path,
            )

    def finalise_excel(self, path: str) -> None:
        """Write outputs to an excel spreadsheet.

        Parameters
        ----------
        path : str
            Name of a folder to save outputs.
        """
        filename: str = os.path.normpath(f"{path}/results.xlsx")
        try:  # check if the directory was already created
            os.makedirs(path, exist_ok=True)
            logger.debug("Directory %s created successfully", path)
        except FileExistsError:  # pragma: no cover
            logger.debug("Directory %s already exists", path)
        with pd.ExcelWriter(  # pylint: disable=abstract-class-instantiated
            filename, engine="openpyxl"
        ) as writer:
            # description sheet
            sheet = []
            summary = []
            command = []
            for output_id, output in self.results.items():
                if output.output_type == "custom":
                    continue  # avoid writing custom outputs
                sheet.append(output_id)
                command.append(output.command)
                summary.append(output.summary)
            tmp_df = pd.DataFrame(
                {"Sheet": sheet, "Command": command, "Summary": summary}
            )
            tmp_df.to_excel(writer, sheet_name="description", index=False, startrow=0)
            # individual sheets
            for output_id, output in self.results.items():
                if output.output_type == "custom":
                    continue  # avoid writing custom outputs
                # command and summary
                start = 0
                tmp_df = pd.DataFrame(
                    [output.command, output.summary], index=["Command", "Summary"]
                )
                tmp_df.to_excel(writer, sheet_name=output_id, startrow=start)
                # outcome
                if output.outcome is not None:
                    output.outcome.to_excel(writer, sheet_name=output_id, startrow=4)
                # output
                for table in output.output:
                    start = 1 + writer.sheets[output_id].max_row
                    table.to_excel(writer, sheet_name=output_id, startrow=start)

    def write_checksums(self, path: str) -> None:
        """Write checksums for each file to checksums folder.

        Parameters
        ----------
        path : str
            Name of a folder to save outputs.
        """
        if os.path.exists(path):
            checksums: dict[str, str] = {}
            for name in os.listdir(path):
                filename = os.path.join(path, name)
                if os.path.isfile(filename):
                    with open(filename, "rb") as file:
                        read = file.read()
                        checksums[name] = hashlib.sha256(read).hexdigest()
            checksums_dir: str = os.path.normpath(f"{path}/checksums")
            os.makedirs(checksums_dir, exist_ok=True)
            for name, sha256 in checksums.items():
                filename = os.path.join(checksums_dir, name + ".txt")
                with open(filename, "w", encoding="utf-8") as file:
                    file.write(sha256)
        else:
            logger.debug("There is no file to do the checksums")  # pragma: no cover


def load_records(path: str) -> Records:
    """Load outputs from a JSON file.

    Parameters
    ----------
    path : str
        Name of an output folder containing results.json.

    Returns
    -------
    Records
        The loaded records.
    """
    records = Records()
    filename = os.path.normpath(f"{path}/results.json")
    with open(filename, newline="", encoding="utf-8") as handle:
        data = json.load(handle)
        if data["version"] != __version__:  # pragma: no cover
            raise ValueError("error loading output")
        for key, val in data["results"].items():
            files: list[dict] = val["files"]
            filenames: list = []
            sdcs: list = []
            for file in files:
                filenames.append(file["name"])
                sdcs.append(file["sdc"])
            records.results[key] = Record(
                uid=val["uid"],
                status=val["status"],
                output_type=val["type"],
                properties=val["properties"],
                sdc=sdcs[0],
                command=val["command"],
                summary=val["summary"],
                outcome=load_outcome(val["outcome"]),
                output=load_output(path, filenames),
                comments=val["comments"],
            )
            records.results[key].exception = val["exception"]
            records.results[key].timestamp = val["timestamp"]
    return records
