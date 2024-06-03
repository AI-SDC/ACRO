"""ACRO: Utility Functions."""

from __future__ import annotations

import logging
from inspect import FrameInfo, getframeinfo

import pandas as pd

logger = logging.getLogger("acro")


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
        code = getframeinfo(stack_list[1][0]).code_context
        if code is not None:
            command = "\n".join(code).strip()
    logger.debug("command: %s", command)
    return command


def prettify_table_string(table: pd.DataFrame, separator: str | None = None) -> str:
    """
    Add delimiters to table.to_string() to improve readability for onscreen display.

    Splits fields on whitespace unless an optional separator is provided e.g. ',' for csv.
    """
    hdelim = "-"
    vdelim = "|"

    table.rename(columns=lambda x: str(x).replace(" ", "_"), inplace=True)
    output = table.to_string(justify="left")
    as_strings = output.split("\n")
    nheaders = len(as_strings) - table.shape[0]
    rowlen = len(as_strings[0])

    # get top level column labels and their positions
    if separator is not None:
        rowone_strings = as_strings[0].split(separator)
    else:
        rowone_strings = as_strings[0].split()

    vals = rowone_strings[1:]
    positions = []
    for val in vals:
        positions.append(as_strings[0].find(val))

    for row, _ in enumerate(as_strings):
        for pos in positions[::-1]:
            as_strings[row] = as_strings[row][0:pos] + vdelim + as_strings[row][pos:]

    rowlen += len(positions)  # add on space for v delimiters

    outstr = ""
    outstr += hdelim * rowlen + vdelim + "\n"
    for row in range(nheaders):
        outstr += as_strings[row] + vdelim + "\n"
    outstr += hdelim * rowlen + vdelim + "\n"
    for row in range(nheaders, len(as_strings)):
        outstr += as_strings[row] + vdelim + "\n"
    outstr += hdelim * rowlen + vdelim + "\n"
    return outstr
