"""ACRO: Utility Functions."""

from __future__ import annotations

import logging
import os
from inspect import FrameInfo, getframeinfo

import numpy as np
import pandas as pd

from .constants import ARTIFACTS_DIR

logger = logging.getLogger("acro")

# Allowed values for the disclosure-control ``mitigation`` field.
# Lives here so both :mod:`acro.acro_tables` and :mod:`acro.acro_stata_parser`
# can share a single source of truth.
ALLOWED_MITIGATIONS: frozenset[str] = frozenset({"none", "suppress", "round"})


def is_blocked_extension(filename: str, blocked_extensions: list[str]) -> bool:
    """Return True and log a warning if the file's extension is blocked."""
    _, ext = os.path.splitext(filename)
    if ext.lower() in blocked_extensions:
        logger.warning(
            "Blocked file extension %s. Files with extension %s are not allowed.",
            filename,
            ext,
        )
        return True
    return False


def get_command(default: str, stack_list: list[FrameInfo]) -> str:
    """Return the calling source line as a string.

    Parameters
    ----------
    default : str
        Default string to return if unable to extract the stack.
    stack_list : list[tuple]
         A list of frame records for the caller's stack. The first entry in the
         returned list represents the caller; the last entry represents the
         outermost call on the stack.

    Returns
    -------
    str
        The calling source line.
    """
    command: str = default
    if len(stack_list) > 1:
        code: list[str] | None = getframeinfo(stack_list[1][0]).code_context
        if code is not None:
            command = "\n".join(code).strip()
    logger.debug("command: %s", command)
    return command


def prettify_table_string(table: pd.DataFrame, separator: str | None = None) -> str:
    """
    Add delimiters to table.to_string() to improve readability for onscreen display.

    Splits fields on whitespace unless an optional separator is provided e.g. ',' for csv.
    """
    hdelim: str = "-"
    vdelim: str = "|"

    table.rename(columns=lambda x: str(x).replace(" ", "_"), inplace=True)
    output: str = table.to_string(justify="left")
    as_strings: list[str] = output.split("\n")
    nheaders = len(as_strings) - table.shape[0]
    rowlen = len(as_strings[0])

    # get top level column labels and their positions
    if separator is not None:
        rowone_strings: list[str] = as_strings[0].split(separator)
    else:
        rowone_strings = as_strings[0].split()

    vals: list[str] = rowone_strings[1:]
    positions: list[int] = []
    for val in vals:
        positions.append(as_strings[0].find(val))

    for row, _ in enumerate(as_strings):
        for pos in positions[::-1]:
            as_strings[row] = as_strings[row][0:pos] + vdelim + as_strings[row][pos:]

    rowlen += len(positions)  # add on space for v delimiters

    outstr: str = ""
    outstr += hdelim * rowlen + vdelim + "\n"
    for row in range(nheaders):
        outstr += as_strings[row] + vdelim + "\n"
    outstr += hdelim * rowlen + vdelim + "\n"
    for row in range(nheaders, len(as_strings)):
        outstr += as_strings[row] + vdelim + "\n"
    outstr += hdelim * rowlen + vdelim + "\n"
    return outstr


def get_unique_artefact_filename(filename: str) -> str:
    """Return a unique filename from a propsoed string."""
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
        return "None"
    increment_number = 0

    while os.path.exists(
        f"{ARTIFACTS_DIR}/{filename}_{increment_number}{extension}"
    ):  # pragma: no cover
        increment_number += 1
    unique_filename = f"{ARTIFACTS_DIR}/{filename}_{increment_number}{extension}"
    return unique_filename


def get_catdtype(series: pd.Series) -> pd.CategoricalDtype:
    """Get info for pandas datatype to convert series to CategoricalDtype."""
    ordered = True if series.astype(int, errors="ignore").dtype == "int64" else False
    categories = np.sort(series.dropna().unique())
    cat_type = pd.CategoricalDtype(categories, ordered)
    return cat_type
