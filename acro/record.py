"""ACRO: Output storage and serialization."""

import datetime
import json
import logging
import os
import shutil
import warnings
from pathlib import Path

import pandas as pd
from pandas import DataFrame

logger = logging.getLogger("acro::records")


def load_outcome(outcome: dict) -> DataFrame:
    """Returns a DataFrame from an outcome dictionary.

    Parameters
    ----------
    outcome : dict
        The outcome to load as a DataFrame.
    """
    return pd.DataFrame.from_dict(outcome)


def load_output(path: str, output: list[str]) -> str | list[DataFrame]:
    """Returns a loaded output.

    Parameters
    ----------
    path : str
        The path to the output folder (with results.json).
    output : str
        The output to load.
    """
    if len(output) < 1:
        raise ValueError("error loading output")
    loaded: str | list[DataFrame] = []
    for filename in output:
        _, ext = os.path.splitext(filename)
        if ext == ".csv":
            filename = os.path.normpath(f"{path}/{filename}")
            loaded.append(pd.read_csv(filename))
    if len(loaded) < 1:  # output was a path to custom file
        loaded = output[0]
    return loaded


class Record:  # pylint: disable=too-many-instance-attributes,too-few-public-methods
    """Stores data related to a single output record."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        uid: str,
        status: str,
        output_type: str,
        properties: dict,
        command: str,
        summary: str,
        outcome: DataFrame,
        output: str | list[DataFrame],
        comments: list[str] | None = None,
    ) -> None:
        """Constructs a new output record.

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
        command : str
            String representation of the operation performed.
        summary : str
            String summarising the ACRO checks.
        outcome : DataFrame
            DataFrame describing the details of ACRO checks.
        output : str | list[DataFrame]
            List of output DataFrames.
        comments : list[str] | None, default None
            List of strings entered by the user to add comments to the output.
        """
        self.uid: str = uid
        self.status: str = status
        self.output_type: str = output_type
        self.properties: dict = properties
        self.command: str = command
        self.summary: str = summary
        self.outcome: DataFrame = outcome
        self.output: str | list[DataFrame] = output
        self.comments: list[str] = [] if comments is None else comments
        now = datetime.datetime.now()
        self.timestamp: str = now.isoformat()

    def serialize_output(self, path: str = "outputs") -> list[str]:
        """Serializes outputs.

        Parameters
        ----------
        path : str
            Name of the folder that outputs are to be written.

        Returns
        -------
        list[str]
            List of filepaths of the written outputs.
        """
        # check if the outputs directory was already created
        try:  # pragma: no cover
            os.makedirs(path)
            logger.debug("Directory %s created successfully", path)
        except FileExistsError:
            logger.debug("Directory %s already exists", path)
        # save each output DataFrame to a different csv
        output = [self.output]
        if not isinstance(self.output, str):
            output = []
            for i, _ in enumerate(self.output):
                filename = f"{self.uid}_{i}.csv"
                output.append(filename)
                filename = os.path.normpath(f"{path}/{filename}")
                with open(filename, mode="w", newline="", encoding="utf-8") as file:
                    file.write(self.output[i].to_csv())
        # move custom files to the output folder
        if self.output_type == "custom" and os.path.exists(self.output):
            shutil.copy(self.output, path)
            output = [Path(self.output).name]
        return output

    def to_dict(self, path: str = "outputs", serialize: bool = True) -> dict:
        """Returns a dictionary representation of an output and serializes
        any DataFrame outputs as csv.

        Parameters
        ----------
        path : str
            Name of the folder that outputs are to be written.
        serialize : bool
            Whether to serialize individual output DataFrames.
        """
        output = self.output
        if serialize:
            output = self.serialize_output(path)
        # convert to dictionary
        output_dict = {
            "uid": self.uid,
            "status": self.status,
            "type": self.output_type,
            "properties": self.properties,
            "command": self.command,
            "summary": self.summary,
            "outcome": json.loads(self.outcome.to_json()),
            "output": output,
            "timestamp": self.timestamp,
            "comments": self.comments,
        }
        return output_dict


class Records:
    """Stores data related to a collection of output records."""

    def __init__(self) -> None:
        """Constructs a new object for storing multiple records."""
        self.results: dict[str, Record] = {}
        self.output_id: int = 0

    def add(  # pylint: disable=too-many-arguments
        self,
        status: str,
        output_type: str,
        properties: dict,
        command: str,
        summary: str,
        outcome: DataFrame,
        output: str | list[DataFrame],
        comments: list[str] | None = None,
    ) -> None:
        """Adds an output to the results.

        Parameters
        ----------
        status : str
            SDC status: {"pass", "fail", "review"}
        output_type : str
            Type of output, e.g., "regression"
        properties : dict
            Dictionary containing structured output data.
        command : str
            String representation of the operation performed.
        summary : str
            String summarising the ACRO checks.
        outcome : DataFrame
            DataFrame describing the details of ACRO checks.
        output : str | list[DataFrame]
            List of output DataFrames.
        comments : list[str], default None
            List of strings entered by the user to add comments to the output.
        """
        output = Record(
            uid=f"output_{self.output_id}",
            status=status,
            output_type=output_type,
            properties=properties,
            command=command,
            summary=summary,
            outcome=outcome,
            output=output,
            comments=comments,
        )
        self.results[output.uid] = output
        self.output_id += 1
        logger.info("add(): %s", output.uid)

    def remove(self, key: str) -> None:
        """Removes an output from the results.

        Parameters
        ----------
        key : str
            Key specifying which output to remove, e.g., 'output_0'.
        """
        if key in self.results:
            del self.results[key]
            logger.info("remove(): %s removed", key)
        else:
            warnings.warn(f"unable to remove {key}, key not found", stacklevel=8)

    def get(self, key: str) -> None:
        """Returns a specified output from the results.

        Parameters
        ----------
        key : str
            Key specifying which output to return, e.g., 'output_0'.
        """
        logger.debug("get(): %s ", key)
        return self.results[key]

    def get_keys(self) -> list[str]:
        """Returns the list of available output keys.

        Returns
        -------
        list[str]
            List of output names.
        """
        logger.debug("get_keys()")
        return list(self.results.keys())

    def get_index(self, index: int) -> Record:
        """Returns the output at the specified position.

        Parameters
        ----------
        index : int
            Position of the output to return.

        Returns
        -------
        Record
            The requested output.
        """
        logger.debug("get_keys()")
        key = list(self.results.keys())[index]
        return self.results[key]

    def add_custom(self, filename: str, comment: str | None = None) -> None:
        """Adds an unsupported output to the results dictionary.

        Parameters
        ----------
        filename : str
            The name of the file that will be added to the list of the outputs.
        comment : str | None, default None
            An optional comment.
        """
        if comment is not None:
            comment = [comment]
        output = Record(
            uid=f"output_{self.output_id}",
            status="review",
            output_type="custom",
            properties={},
            command="custom",
            summary="review",
            outcome=DataFrame(),
            output=os.path.normpath(filename),
            comments=comment,
        )
        self.results[output.uid] = output

    def rename(self, old: str, new: str) -> None:
        """Rename an output.

        Parameters
        ----------
        old : str
            The old name of the output.
        new : str
            The new name of the output.
        """
        if old in self.results:
            self.results[new] = self.results[old]
            self.results[new].uid = new
            del self.results[old]
            logger.info("rename_output(): %s renamed to %s", old, new)
        else:
            warnings.warn(f"unable to rename {old}, key not found", stacklevel=8)

    def add_comments(self, output: str, comment: str) -> None:
        """Adds a comment to an output.

        Parameters
        ----------
        output : str
            The name of the output.
        comment : str
            The comment.
        """
        if output in self.results:
            self.results[output].comments.append(comment)
            logger.info("a comment was added to %s", output)
        else:
            warnings.warn(f"unable to find {output}, key not found", stacklevel=8)

    def print(self) -> None:
        """Prints the current results."""
        logger.debug("print()")
        for name, output in self.results.items():
            print(f"{name}:")
            for key, item in output.to_dict(serialize=False).items():
                print(f"{key}: {item}")
            print("\n")

    def finalise(self, path: str, ext: str) -> None:
        """Creates a results file for checking.

        Parameters
        ----------
        path : str
            Name of a folder to save outputs.
        ext : str
            Extension of the results file. Valid extensions: {json, xlsx}.
        """
        logger.debug("finalise()")
        if ext == "json":
            self.finalise_json(path)
        elif ext == "xlsx":
            self.finalise_excel(path)
        else:
            raise ValueError("Invalid file extension. Options: {json, xlsx}")
        logger.info("outputs written to: %s", path)

    def finalise_json(self, path: str) -> None:
        """Writes outputs to a JSON file.

        Parameters
        ----------
        path : str
            Name of a folder to save outputs.
        """
        outputs: dict = {}
        for key, val in self.results.items():
            outputs[key] = val.to_dict(path)
        filename: str = os.path.normpath(f"{path}/results.json")
        with open(filename, "w", newline="", encoding="utf-8") as file:
            json.dump(outputs, file, indent=4, sort_keys=False)

    def finalise_excel(self, path: str) -> None:
        """Writes outputs to an excel spreadsheet.

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

    def load_json(self, path: str) -> None:
        """Loads outputs from a JSON file.

        Parameters
        ----------
        path : str
            Name of an output folder containing results.json.
        """
        self.results = {}
        filename = os.path.normpath(f"{path}/results.json")
        with open(filename, newline="", encoding="utf-8") as file:
            data = json.load(file)
            for key, val in data.items():
                self.results[key] = Record(
                    val["uid"],
                    val["status"],
                    val["type"],
                    val["properties"],
                    val["command"],
                    val["summary"],
                    load_outcome(val["outcome"]),
                    load_output(path, val["output"]),
                    val["comments"],
                )
                self.results[key].timestamp = val["timestamp"]
