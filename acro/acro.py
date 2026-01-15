"""ACRO: Automatic Checking of Research Outputs."""

from __future__ import annotations

import json
import logging
import os
import pathlib
import warnings

import yaml

from . import acro_tables
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
    suppress : bool
        Whether to automatically apply suppression

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

    def __init__(self, config: str = "default", suppress: bool = False) -> None:
        """Construct a new ACRO object and reads parameters from config.

        Parameters
        ----------
        config : str
            Name of a yaml configuration file with safe parameters.
        suppress : bool, default False
            Whether to automatically apply suppression.
        """
        Tables.__init__(self, suppress)
        Regression.__init__(self, config)
        self.config: dict = {}
        self.results: Records = Records()
        self.suppress: bool = suppress
        path = pathlib.Path(__file__).with_name(config + ".yaml")
        logger.debug("path: %s", path)
        with open(path, encoding="utf-8") as handle:
            self.config = yaml.load(handle, Loader=yaml.loader.SafeLoader)
        logger.info("version: %s", __version__)
        logger.info("config: %s", self.config)
        logger.info("automatic suppression: %s", self.suppress)
        # set globals needed for aggregation functions
        acro_tables.THRESHOLD = self.config["safe_threshold"]
        acro_tables.SAFE_PRATIO_P = self.config["safe_pratio_p"]
        acro_tables.SAFE_NK_N = self.config["safe_nk_n"]
        acro_tables.SAFE_NK_K = self.config["safe_nk_k"]
        acro_tables.CHECK_MISSING_VALUES = self.config["check_missing_values"]
        acro_tables.ZEROS_ARE_DISCLOSIVE = self.config["zeros_are_disclosive"]
        # set globals for survival analysis
        acro_tables.SURVIVAL_THRESHOLD = self.config["survival_safe_threshold"]

    def finalise(self, path: str = "outputs", ext="json") -> Records | None:
        """Create a results file for checking.

        Parameters
        ----------
        path : str
            Name of a folder to save outputs.
        ext : str
            Extension of the results file. Valid extensions: {json, xlsx}.

        Returns
        -------
        Records
            Object storing the outputs.
        """
        # check if the path exists
        if os.path.exists(path):
            logger.warning(
                "Results file can not be created. "
                "Directory %s already exists. Please choose a different directory name.",
                path,
            )
            return None
        self.results.finalise(path, ext)
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

    def custom_output(self, filename: str, comment: str = "") -> None:
        """Add an unsupported output to the results dictionary.

        Parameters
        ----------
        filename : str
            The name of the file that will be added to the list of the outputs.
        comment : str
            An optional comment.
        """
        self.results.add_custom(filename, comment)

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


def add_to_acro(src_path: str, dest_path: str = "sdc_results") -> None:
    """Add outputs to an acro object and creates a results file for checking.

    Parameters
    ----------
    src_path : str
        Name of the folder with outputs produced without using acro.
    dest_path : str
        Name of the folder to save outputs.
    """
    acro = ACRO()
    output_id = 0
    # add the files from the folder to an acro obj
    for file in os.listdir(src_path):
        filename = os.path.join(src_path, file)
        acro.custom_output(filename)
        acro.rename_output(f"output_{output_id}", file)
        output_id += 1
    acro.finalise(dest_path, "json")
