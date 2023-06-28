"""This module contains unit tests."""

import json
import os

import numpy as np
import pandas as pd
import pytest

from acro import ACRO, add_constant, record, utils
from acro.record import Record, Records

# pylint: disable=redefined-outer-name


@pytest.fixture
def data() -> pd.DataFrame:
    """Load test data."""
    path = os.path.join("data", "test_data.dta")
    data = pd.read_stata(path)
    return data


@pytest.fixture
def acro() -> ACRO:
    """Initialise ACRO."""
    return ACRO()


def test_crosstab_threshold(data, acro):
    """Crosstab threshold test."""
    _ = acro.crosstab(data.year, data.grant_type)
    results: Records = acro.finalise()
    correct_summary: str = "fail; threshold: 6 cells suppressed; "
    output = results.get_index(0)
    assert output.summary == correct_summary


def test_crosstab_multiple(data, acro):
    """Crosstab multiple rule test."""
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mean"
    )
    results: Records = acro.finalise()
    correct_summary: str = (
        "fail; threshold: 6 cells suppressed; p-ratio: 1 cells suppressed; "
        "nk-rule: 1 cells suppressed; "
    )
    output = results.get_index(0)
    assert output.summary == correct_summary


def test_negatives(data, acro):
    """Pivot table and Crosstab with negative values."""
    data.loc[0:10, "inc_grants"] = -10
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mean"
    )
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    results: Records = acro.finalise()
    correct_summary: str = "review; negative values found"
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    assert output_0.summary == correct_summary
    assert output_1.summary == correct_summary


def test_pivot_table_pass(data, acro):
    """Pivot table pass test."""
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    results: Records = acro.finalise()
    correct_summary: str = "pass"
    output_0 = results.get_index(0)
    assert output_0.summary == correct_summary


def test_pivot_table_cols(data, acro):
    """Pivot table with columns test."""
    _ = acro.pivot_table(
        data,
        index=["grant_type"],
        columns=["year"],
        values=["inc_grants"],
        aggfunc=["mean", "std"],
    )
    results: Records = acro.finalise()
    correct_summary: str = (
        "fail; threshold: 14 cells suppressed; "
        "p-ratio: 2 cells suppressed; nk-rule: 2 cells suppressed; "
    )
    output_0 = results.get_index(0)
    assert output_0.summary == correct_summary


def test_ols(data, acro):
    """Ordinary Least Squares test."""
    new_df = data[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
    new_df = new_df.dropna()
    # OLS
    endog = new_df.inc_activity
    exog = new_df[["inc_grants", "inc_donations", "total_costs"]]
    exog = add_constant(exog)
    results = acro.ols(endog, exog)
    assert results.df_resid == 807
    assert results.rsquared == pytest.approx(0.894, 0.001)
    # OLSR
    results = acro.olsr(
        formula="inc_activity ~ inc_grants + inc_donations + total_costs", data=new_df
    )
    assert results.df_resid == 807
    assert results.rsquared == pytest.approx(0.894, 0.001)
    # Finalise
    results: dict = acro.finalise()
    correct_summary: str = "pass; dof=807.0 >= 10"
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    assert output_0.summary == correct_summary
    assert output_1.summary == correct_summary


def test_probit_logit(data, acro):
    """Probit and Logit tests."""
    new_df = data[
        ["survivor", "inc_activity", "inc_grants", "inc_donations", "total_costs"]
    ]
    new_df = new_df.dropna()
    endog = new_df["survivor"].astype("category").cat.codes  # numeric
    endog.name = "survivor"
    exog = new_df[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
    exog = add_constant(exog)
    # Probit
    results = acro.probit(endog, exog)
    assert results.df_resid == 806
    assert results.prsquared == pytest.approx(0.208, 0.01)
    # Logit
    results = acro.logit(endog, exog)
    assert results.df_resid == 806
    assert results.prsquared == pytest.approx(0.214, 0.01)
    # ProbitR
    new_df["survivor"] = new_df["survivor"].astype("category").cat.codes
    results = acro.probitr(
        formula="survivor ~ inc_activity + inc_grants + inc_donations + total_costs",
        data=new_df,
    )
    assert results.df_resid == 806
    assert results.prsquared == pytest.approx(0.208, 0.01)
    # LogitR
    results = acro.logitr(
        formula="survivor ~ inc_activity + inc_grants + inc_donations + total_costs",
        data=new_df,
    )
    assert results.df_resid == 806
    assert results.prsquared == pytest.approx(0.214, 0.01)
    # Finalise
    results: dict = acro.finalise()
    correct_summary: str = "pass; dof=806.0 >= 10"
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    output_2 = results.get_index(2)
    output_3 = results.get_index(3)
    assert output_0.summary == correct_summary
    assert output_1.summary == correct_summary
    assert output_2.summary == correct_summary
    assert output_3.summary == correct_summary


def test_finalise_excel(data, acro):
    """Finalise excel test."""
    _ = acro.crosstab(data.year, data.grant_type)
    path: str = "RES_PYTEST"
    results: Records = acro.finalise(path, "xlsx")
    output_0 = results.get_index(0)
    filename = os.path.normpath(f"{path}/results.xlsx")
    load_data = pd.read_excel(filename, sheet_name=output_0.uid)
    correct_cell: str = "_ = acro.crosstab(data.year, data.grant_type)"
    assert load_data.iloc[0, 0] == "Command"
    assert load_data.iloc[0, 1] == correct_cell


def test_output_removal(data, acro):
    """Output removal and print test."""
    _ = acro.crosstab(data.year, data.grant_type)
    _ = acro.crosstab(data.year, data.grant_type)
    _ = acro.crosstab(data.year, data.grant_type)
    results: Records = acro.finalise()
    output_0 = results.get("output_0")
    output_1 = results.get("output_1")
    # remove something that is there
    acro.remove_output(output_0.uid)
    results = acro.finalise()
    correct_summary: str = "fail; threshold: 6 cells suppressed; "
    keys = results.get_keys()
    assert output_0.uid not in keys
    assert output_1.uid in keys
    assert output_1.summary == correct_summary
    acro.print_outputs()
    # remove something that is not there
    with pytest.warns(UserWarning):
        acro.remove_output("123")


def test_load_output():
    """Empty array when loading output."""
    path: str = "RES_PYTEST"
    with pytest.raises(ValueError):
        record.load_output(path, [])


def test_finalise_invalid(data, acro):
    """Invalid output format when finalising."""
    _ = acro.crosstab(data.year, data.grant_type)
    path: str = "RES_PYTEST"
    with pytest.raises(ValueError):
        _ = acro.finalise(path, "123")


def test_finalise_json(data, acro):
    """Finalise json test."""
    _ = acro.crosstab(data.year, data.grant_type)
    # write JSON
    path: str = "RES_PYTEST"
    result: Records = acro.finalise(path, "json")
    # load JSON
    loaded: Records = Records()
    loaded.load_json(path)
    orig = result.get_index(0)
    read = loaded.get_index(0)
    # check equal
    assert orig.uid == read.uid
    assert orig.status == read.status
    assert orig.output_type == read.output_type
    assert orig.properties == read.properties
    assert orig.command == read.command
    assert orig.summary == read.summary
    assert orig.comments == read.comments
    assert orig.timestamp == read.timestamp
    assert (orig.output[0].reset_index()).equals(read.output[0])
    # test reading JSON
    with open(os.path.normpath(f"{path}/results.json"), encoding="utf-8") as file:
        json_data = json.load(file)
    assert json_data[orig.uid]["output"][0] == f"{orig.uid}_0.csv"
    # regression check: the outcome fields are dicts not strings
    assert json_data[orig.uid]["outcome"]["R/G"] == {
        "2010": "threshold; ",
        "2011": "threshold; ",
        "2012": "threshold; ",
        "2013": "threshold; ",
        "2014": "threshold; ",
        "2015": "threshold; ",
    }


def test_rename_output(data, acro):
    """Output renaming test."""
    _ = acro.crosstab(data.year, data.grant_type)
    results: Record = acro.finalise()
    output_0 = results.get_index(0)
    orig_name = output_0.uid
    new_name = "cross_table"
    acro.rename_output(orig_name, new_name)
    results = acro.finalise()
    assert output_0.uid == new_name
    assert orig_name not in results.get_keys()
    assert os.path.exists(f"outputs/{new_name}_0.csv")
    # rename an output that doesn't exist
    with pytest.warns(UserWarning):
        acro.rename_output("123", "name")


def test_add_comments(data, acro):
    """Adding comments to output test"""
    _ = acro.crosstab(data.year, data.grant_type)
    results: Record = acro.finalise()
    output_0 = results.get_index(0)
    assert output_0.comments == []
    comment = "This is a cross table between year and grant_type"
    acro.add_comments(output_0.uid, comment)
    assert output_0.comments == [comment]
    comment_1 = "6 cells were suppressed"
    acro.add_comments(output_0.uid, comment_1)
    assert output_0.comments == [comment, comment_1]
    # add a comment to something that is not there
    with pytest.warns(UserWarning):
        acro.add_comments("123", "comment")


def test_custom_output(acro):
    """Adding an unsupported output to the results dictionary test"""
    save_path = "RES_PYTEST"
    filename = "notebooks/XandY.jfif"
    file_path = os.path.normpath(filename)
    acro.custom_output(filename)
    results: Records = acro.finalise(path=save_path)
    output_0 = results.get_index(0)
    assert output_0.output == file_path
    assert os.path.exists(os.path.normpath(f"{save_path}/XandY.jfif"))


def test_missing(data, acro):
    """Pivot table and Crosstab with negative values."""
    utils.CHECK_MISSING_VALUES = True
    data.loc[0:10, "inc_grants"] = np.NaN
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mean"
    )
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    results: Records = acro.finalise()
    correct_summary: str = "review; missing values found"
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    assert output_0.summary == correct_summary
    assert output_1.summary == correct_summary


def test_suppression_error(caplog):
    """Apply suppression type error test."""
    table_data = {"col1": [1, 2], "col2": [3, 4]}
    mask_data = {"col1": [np.NaN, True], "col2": [True, True]}
    table = pd.DataFrame(data=table_data)
    masks = {"test": pd.DataFrame(data=mask_data)}
    utils.apply_suppression(table, masks)
    assert "problem mask test is not binary" in caplog.text
