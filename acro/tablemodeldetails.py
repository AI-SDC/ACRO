"""Class to hold details of a table that can create crosstabs,pivot tables or plots."""

from __future__ import annotations

import logging
from collections.abc import Callable
from copy import deepcopy
from typing import Any

import numpy as np
import pandas as pd

from . import utils
from .constants import DIMENSION_URI, MEASURE_URI

logger = logging.getLogger("acro")


class TableModelDetails:
    """Class for details needed to create a table.

    FOR NOW this will effectively hold copies of all the data needed
    TODO refactor to hold pointers to reduce memory footprint and speed up
    TODO change init to support other types of data beyond pd.Series
    """

    model_type: str = "table"
    kwargs: dict = {}
    variable_data: dict = {}
    risk_appetite: dict = {}
    command: str = ""
    df_resid: int = 0

    def __init__(
        self,
        index: list | None = None,
        columns: list | None = None,
        values: pd.Series | None = None,
        command: str | None = None,
        thekwargs: dict | None = None,
        risk_appetite: dict | None = None,
    ) -> None:
        """Construct the TableModelDescriptor for a table/ array type analysis.  # noqa: D212,D213,D413.

        Parameters
        ----------
        index : list
            index series names
        columns : list
            columns series names
        values : pd.Series
            the values series (measure) for the table, if any
        thekwargs : dict
            specifiers for table and command
        risk_appetite : dict
            statement of TREs risk appetite
        command : str
            "crosstab" or "pivot_table"
        """
        self.model_type: str = "table"
        self.kwargs: dict = {} if thekwargs is None else thekwargs
        self.risk_appetite: dict = {} if risk_appetite is None else risk_appetite
        self.command: str = "" if command is None else command
        self.index: list = [] if index is None else index
        self.columns: list = [] if columns is None else columns
        self.values: pd.Series = pd.Series() if values is None else values
        # Histograms are array-type analyses, not table-type
        if self.command == "hist":
            self.model_type = "array"
        self.variable_metadata: dict = self._get_variable_metadata(
            self.index, self.columns, values
        )
        if not isinstance(self.kwargs, dict):
            raise TypeError(
                f"kwargs argument should be a dict but is a  {type(thekwargs)}"
            )
        if not isinstance(self.values, pd.Series):
            raise TypeError(
                f"Expected values argument to be a panda Series "
                f"but is a  {type(values)}."
            )

        for axis in (self.index, self.columns):
            if not isinstance(axis, list):
                raise TypeError(
                    f"axis argument should be a list but is a  {type(axis)}"
                )
            for item in axis:
                if not isinstance(item, pd.Series):
                    raise TypeError(
                        f"Expected {item} element of {axis} list to be a panda Series "
                        f"but is a  {type(item)}."
                    )

    def get_crosstab_args(self) -> tuple:
        """Get arguments for a call to crosstab.

        create dummy column if needed
        """
        if len(self.columns) == 0:
            numrows = len(self.index[0])
            columns = pd.Series(np.ones(numrows, dtype=np.int_))
            columns.name = "dummy"
        else:
            columns = self.columns
        return (self.index, columns)

    def get_crosstab_kwargs(self) -> dict[str, Any]:
        """Get kwargs in format for a crosstab call."""
        thiskwargs: dict = deepcopy(self.kwargs)
        thiskwargs["values"] = self.values

        for key in ["observed", "sort", "index", "columns", "fill_value", "bins"]:
            _ = thiskwargs.pop(key, "missing")
        return thiskwargs

    def get_dimension_names(self) -> list[str]:
        """Names from joint list of rows and columns."""
        names: list = []
        for dimension in self.index:
            names.append(dimension.name)
        for dimension in self.columns:
            names.append(dimension.name)
        return names

    def get_variable_type_dict(self) -> dict[str, Any]:
        """Get dict listing dependent and independent variables from metadata catalogue.

        Returns
        -------
        dict
            holding  name of dependent variable and list of independent (exogenous) variables
        """
        mydict: dict[str, Any] = {"dependent": "unknown", "independent": []}
        for varname in self.variable_metadata:
            if self.variable_metadata[varname]["dependent"]:
                mydict["dependent"] = varname
            else:
                mydict["independent"].append(varname)

        return mydict

    def _get_axis_metadata(self, axis: list[pd.Series], where: str) -> dict:
        """Get metadata for categorical variables describing an axis.

        Cycle through the categorical variables that define an axis
        and construct a meta data dictionary describing them

        Parameters
        ----------
        axis : list[pd.Series]
            list of series defining a dimension in an analysis
        where : str
            axis reference i.e. "rows" or "columns"

        Returns
        -------
        dict
            one entry for item in list provided
            key is name of series
            dict of values describe location, type, categories present
        """
        metadata: dict[str, dict] = {}
        for idx, dimension in enumerate(axis):
            if not isinstance(dimension, pd.Series):
                logger.info(
                    "unable to construct meta data for "
                    " component of %s that is not a pandas series",
                    where,
                )
            else:
                name = dimension.name
                cat_type = utils.get_catdtype(dimension)
                metadata[name] = {
                    "location": where,
                    "sequence_id": idx,
                    "dtype": str(cat_type.categories.dtype),
                    "type": DIMENSION_URI,
                    "dependent": False,
                    "categories": list(cat_type.categories),
                    "ordered": cat_type.ordered,
                }
        return metadata

    def _get_variable_metadata(
        self, index: list, columns: list, values: pd.Series | None
    ) -> dict[str, dict]:
        """Create data dictionary.

        Notes
        -----
        Expand docstring and handle arraylike as well as series.
        """
        # TODO handle arraylike as well as series
        # TODO handle rownames/colnames
        variable_metadata: dict[str, dict] = {}
        variable_metadata.update(self._get_axis_metadata(index, where="index"))
        variable_metadata.update(self._get_axis_metadata(columns, where="columns"))
        if isinstance(values, pd.Series) and len(values) > 0:
            name = values.name if isinstance(values, pd.Series) else "unknown_measure"
            variable_metadata[name] = {
                "location": "cells",
                "sequence_id": 0,
                "dtype": str(values.dtype),
                "type": MEASURE_URI,
                "dependent": True,
                "categories": [],
            }
        return variable_metadata

    def get_count_table(self) -> pd.DataFrame:
        """Make count table as specified by model."""
        args = self.get_crosstab_args()
        thiskwargs = self.get_crosstab_kwargs()
        thiskwargs["values"] = None
        thiskwargs["aggfunc"] = None
        return pd.crosstab(*args, **thiskwargs)

    def get_table_newagg(self, newaggfunc: Callable) -> pd.DataFrame:
        """Make  table as specified by model but with new agg func."""
        args = self.get_crosstab_args()
        thiskwargs = self.get_crosstab_kwargs()
        if len(thiskwargs["values"]) != len(self.index[0]):
            raise AttributeError("column used for values has incompatibe length")
        thiskwargs["aggfunc"] = newaggfunc
        return pd.crosstab(*args, **thiskwargs)

    def get_zeros_table(self) -> pd.DataFrame:
        """Create a data frame filled with zeros of same size as underlying table."""
        args: tuple = self.get_crosstab_args()
        kwargs: dict = self.get_crosstab_kwargs()
        kwargs["aggfunc"] = kwargs["values"] = None
        zeros_table = pd.crosstab(*args, **kwargs)
        zeros_table[:] = 0
        return zeros_table

    def get_allfalse_table(self) -> pd.DataFrame:
        """Create a data frame filled with false of same size as underlying table."""
        if self.model_type == "table":
            args = self.get_crosstab_args()
            thiskwargs = self.get_crosstab_kwargs()
            thiskwargs["aggfunc"] = thiskwargs["values"] = None
            mask = pd.crosstab(*args, **thiskwargs).astype(bool)
            mask[:] = False
            # logger.info(f'get_allfalse_mask for table, mask=:\n{mask}')

        else:  # array
            series_mask = self.index[0].value_counts()
            series_mask = pd.Series(False, index=series_mask.index, dtype=bool)
            mask = pd.DataFrame(series_mask, dtype=bool)
            # logger.info(f'get_allfalse_mask for other {model.model_type}, mask=:\n{mask}')

        return mask
