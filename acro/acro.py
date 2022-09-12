"""ACRO."""

import json
import logging
import pathlib

import pandas as pd
import yaml
from pandas import DataFrame

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("acro")


def apply_threshold(data: DataFrame, threshold: int) -> DataFrame:
    """
    Suppresses numerical values below a given threshold.

    Parameters
    ----------
    data : DataFrame
        DataFrame to apply threshold suppression.
    threshold : int
        Values below this threshold are replaced with n/a.

    Returns
    ----------
    DataFrame
        DataFrame after threshold suppression has been applied.
    """
    cols: DataFrame = data.select_dtypes(include=["number"]).columns
    mask: DataFrame = data[cols] < threshold
    n_cells: int = mask.sum().sum()
    if n_cells > 0:
        logger.debug("suppressing %d cells where value < threshold", n_cells)
        data[cols] = data[cols].mask(mask, "n/a")
    return data


class ACRO:
    """ACRO."""

    def __init__(self, filename: str = "results") -> None:
        """
        Constructs a new ACRO object and reads parameters from config.

        Parameters
        ----------
        filename : str
            Name of the output file.
        """
        self.config: dict = {}
        self.results: dict = {}
        self.filename: str = filename
        path = pathlib.Path(__file__).with_name("default.yaml")
        logger.debug("path: %s", path)
        with open(path, encoding="utf-8") as handle:
            self.config = yaml.load(handle, Loader=yaml.loader.SafeLoader)
        logger.debug("config: %s", self.config)

    def finalise(self) -> None:
        """Creates a results file for checking."""
        logger.debug("finalise()")
        json_output: str = json.dumps(self.results, indent=4)
        logger.debug("filename: %s.json", self.filename)
        logger.debug("output: %s", json_output)
        with open(self.filename + ".json", "wt", encoding="utf-8") as file:
            file.write(json_output)

    def crosstab(  # pylint: disable=too-many-arguments
        self,
        index,
        columns,
        values=None,
        rownames=None,
        colnames=None,
        aggfunc=None,
        margins: bool = False,
        margins_name: str = "All",
        dropna: bool = True,
        normalize=False,
    ) -> DataFrame:
        """
        Compute a simple cross tabulation of two (or more) factors.
        By default, computes a frequency table of the factors unless an
        array of values and an aggregation function are passed.

        Parameters
        ----------
        index : array-like, Series, or list of arrays/Series
            Values to group by in the rows.
        columns : array-like, Series, or list of arrays/Series
            Values to group by in the columns.
        values : array-like, optional
            Array of values to aggregate according to the factors.
            Requires `aggfunc` be specified.
        rownames : sequence, default None
            If passed, must match number of row arrays passed.
        colnames : sequence, default None
            If passed, must match number of column arrays passed.
        aggfunc : function, optional
            If specified, requires `values` be specified as well.
        margins : bool, default False
            Add row/column margins (subtotals).
        margins_name : str, default 'All'
            Name of the row/column that will contain the totals
            when margins is True.
        dropna : bool, default True
            Do not include columns whose entries are all NaN.
        normalize : bool, {'all', 'index', 'columns'}, or {0,1}, default False
            Normalize by dividing all values by the sum of values.
            - If passed 'all' or `True`, will normalize over all values.
            - If passed 'index' will normalize over each row.
            - If passed 'columns' will normalize over each column.
            - If margins is `True`, will also normalize margin values.

        Returns
        -------
        DataFrame
            Cross tabulation of the data.
        """

        logger.debug("crosstab()")

        if aggfunc is not None:
            raise ValueError("aggfunc disallowed.")

        table = pd.crosstab(
            index,
            columns,
            values,
            rownames,
            colnames,
            aggfunc,
            margins,
            margins_name,
            dropna,
            normalize,
        )

        table = apply_threshold(table, self.config["safe_threshold"])

        name: str = f"output_{len(self.results)}"
        self.results[name] = table.to_dict()

        return table
