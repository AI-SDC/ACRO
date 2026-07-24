"""Unit tests for TableModeldetails class."""

import numpy as np
import pandas as pd
import pytest

from acro.tablemodeldetails import TableModelDetails


def test_tablemodeldetails_kwargs_not_dict():
    """Passing non-dict kwargs raises TypeError."""
    with pytest.raises(TypeError, match="kwargs argument should be a dict"):
        TableModelDetails(
            index=[pd.Series([1, 2])],
            columns=[],
            values=pd.Series([1, 2]),
            thekwargs="bad",  # type: ignore[arg-type]
        )


def test_tablemodeldetails_values_not_series():
    """Passing non-Series values raises TypeError (line 77)."""
    with pytest.raises(
        TypeError, match="Expected values argument to be a panda Series"
    ):
        TableModelDetails(
            index=[pd.Series([1, 2])],
            columns=[],
            values=[1, 2],
        )


def test_tablemodeldetails_axis_item_not_series():
    """Passing non-Series element in index list raises TypeError."""
    with pytest.raises(
        TypeError, match="Expected .* element of .* list to be a panda Series"
    ):
        TableModelDetails(
            index=[[1, 2]],
            columns=[],
            values=pd.Series([1, 2]),
        )


def test_tablemodeldetails_axis_not_a_list():
    """Passing non-list axis raises TypeError."""
    with pytest.raises(TypeError, match="axis argument should be a list"):
        TableModelDetails(
            index=pd.Series([1, 2]),
            columns=[],
            values=pd.Series([1, 2]),
        )


def test_get_axis_metadata_non_series_item():
    """_get_axis_metadata logs when a dimension is not a Series (line 165)."""
    model = TableModelDetails(
        index=[pd.Series([1, 2, 3], name="idx")],
        columns=[],
        values=pd.Series([10, 20, 30], name="val"),
    )
    # Call with a list containing a non-Series to exercise the else branch
    result = model._get_axis_metadata([42], "index")
    assert result == {}  # non-series items are skipped


def test_get_table_newagg_incompatible_length():
    """Get_table_newagg raises AttributeError when values length mismatches (line 222)."""
    idx = pd.Series([1, 2, 3], name="idx")
    vals = pd.Series([10, 20, 30], name="val")
    model = TableModelDetails(
        index=[idx],
        columns=[],
        values=vals,
    )
    # Replace values with longer series to trigger the incompatible-length check
    model.values = pd.Series(list(range(100)), name="val")
    with pytest.raises(AttributeError, match="incompatibe length"):
        model.get_table_newagg(np.sum)


def test_get_allfalse_table_array_type():
    """Get_allfalse_table for array model_type uses value_counts path."""
    s = pd.Series([1, 2, 2, 3, 3, 3], name="vals")
    model = TableModelDetails(
        index=[s],
        thekwargs={"bins": 3},
        command="hist",
    )
    assert model.model_type == "array"
    mask = model.get_allfalse_table()
    assert isinstance(mask, pd.DataFrame)
    assert mask.dtypes.iloc[0] is bool or mask.dtypes.iloc[0] == "bool"


def test_get_zeros_table_basic():
    """Get_zeros_table returns a DataFrame of zeros."""
    idx = pd.Series([1, 2, 3, 1, 2, 3], name="idx")
    cols = pd.Series(["a", "a", "a", "b", "b", "b"], name="col")
    vals = pd.Series([10, 20, 30, 40, 50, 60], name="val")
    model = TableModelDetails(
        index=[idx],
        columns=[cols],
        values=vals,
    )
    zt = model.get_zeros_table()
    assert isinstance(zt, pd.DataFrame)
    assert (zt.values == 0).all()
