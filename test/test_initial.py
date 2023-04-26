"""This module contains unit tests."""

import json
import os

import numpy as np
import pandas as pd
import pytest

from acro import ACRO, add_constant, utils

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
    output: dict = acro.finalise()
    correct_summary: str = "fail; threshold: 6 cells suppressed; "
    output_0 = list(output.keys())[0]
    assert output[output_0]["summary"] == correct_summary


def test_crosstab_multiple(data, acro):
    """Crosstab multiple rule test."""
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mean"
    )
    output: dict = acro.finalise()
    correct_summary: str = (
        "fail; threshold: 6 cells suppressed; p-ratio: 1 cells suppressed; "
        "nk-rule: 1 cells suppressed; "
    )
    output_0 = list(output.keys())[0]
    assert output[output_0]["summary"] == correct_summary


def test_negatives(data, acro):
    """Pivot table and Crosstab with negative values."""
    data.loc[0:10, "inc_grants"] = -10
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mean"
    )
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    output: dict = acro.finalise()
    correct_summary: str = "review; negative values found"
    output_0 = list(output.keys())[0]
    output_1 = list(output.keys())[1]
    assert output[output_0]["summary"] == correct_summary
    assert output[output_1]["summary"] == correct_summary


def test_pivot_table_pass(data, acro):
    """Pivot table pass test."""
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    output: dict = acro.finalise()
    correct_summary: str = "pass"
    output_0 = list(output.keys())[0]
    assert output[output_0]["summary"] == correct_summary


def test_pivot_table_cols(data, acro):
    """Pivot table with columns test."""
    _ = acro.pivot_table(
        data,
        index=["grant_type"],
        columns=["year"],
        values=["inc_grants"],
        aggfunc=["mean", "std"],
    )
    output: dict = acro.finalise()
    correct_summary: str = (
        "fail; threshold: 14 cells suppressed; "
        "p-ratio: 2 cells suppressed; nk-rule: 2 cells suppressed; "
    )
    output_0 = list(output.keys())[0]
    assert output[output_0]["summary"] == correct_summary


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
    output: dict = acro.finalise()
    correct_summary: str = "pass; dof=807.0 >= 10"
    output_0 = list(output.keys())[0]
    output_1 = list(output.keys())[1]
    assert output[output_0]["summary"] == correct_summary
    assert output[output_1]["summary"] == correct_summary


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
    output: dict = acro.finalise()
    correct_summary: str = "pass; dof=806.0 >= 10"
    output_0 = list(output.keys())[0]
    output_1 = list(output.keys())[1]
    output_2 = list(output.keys())[2]
    output_3 = list(output.keys())[3]
    assert output[output_0]["summary"] == correct_summary
    assert output[output_1]["summary"] == correct_summary
    assert output[output_2]["summary"] == correct_summary
    assert output[output_3]["summary"] == correct_summary


def test_finalise_excel(data, acro):
    """Finalise excel test."""
    _ = acro.crosstab(data.year, data.grant_type)
    output: dict = acro.finalise("test.xlsx")
    output_0 = list(output.keys())[0]
    load_data = pd.read_excel("test.xlsx", sheet_name=output_0)
    correct_cell: str = "_ = acro.crosstab(data.year, data.grant_type)"
    assert load_data.iloc[0, 0] == "Command"
    assert load_data.iloc[0, 1] == correct_cell


def test_output_removal(data, acro):
    """Output removal and print test."""
    _ = acro.crosstab(data.year, data.grant_type)
    _ = acro.crosstab(data.year, data.grant_type)
    _ = acro.crosstab(data.year, data.grant_type)
    output: dict = acro.finalise()
    output_0 = list(output.keys())[0]
    output_1 = list(output.keys())[1]
    acro.remove_output(output_0)
    output: dict = acro.finalise()
    correct_summary: str = "fail; threshold: 6 cells suppressed; "
    assert output_0 not in output
    assert output_1 in output
    assert output[output_1]["summary"] == correct_summary
    acro.print_outputs()


def test_finalise_json(data, acro):
    """Finalise json test."""
    _ = acro.crosstab(data.year, data.grant_type)
    _ = acro.crosstab(data.year, data.grant_type)
    output: dict = acro.finalise("test.json")
    output_0_name = list(output.keys())[0]
    output_1_name = list(output.keys())[1]
    output_0 = pd.read_csv(f"outputs/{output_0_name}.csv")
    output_1 = pd.read_csv(f"outputs/{output_1_name}.csv")
    assert (output[output_0_name]["output"][0].reset_index()).equals(output_0)
    assert (output[output_1_name]["output"][0].reset_index()).equals(output_1)

    with open("./outputs/test.json", encoding="utf-8") as file:
        json_data = json.load(file)
    assert json_data[output_0_name]["output"] == os.path.abspath(
        f"outputs/{output_0_name}.csv"
    )
    assert json_data[output_1_name]["output"] == os.path.abspath(
        f"outputs/{output_1_name}.csv"
    )


def test_output_timestamp(data, acro):
    """Adding timestamp to the output name and meta data test."""
    _ = acro.crosstab(data.year, data.grant_type)
    _ = acro.pivot_table(
        data,
        index=["grant_type"],
        columns=["year"],
        values=["inc_grants"],
        aggfunc=["mean", "std"],
    )
    output: dict = acro.finalise("test.json")
    output_0_name = list(output.keys())[0]
    output_1_name = list(output.keys())[1]

    del acro

    acro = ACRO()
    _ = acro.crosstab(data.year, data.grant_type)
    output: dict = acro.finalise("test.json")
    output_2_name = list(output.keys())[0]

    with open("./outputs/test.json", encoding="utf-8") as file:
        json_data = json.load(file)
        assert output_0_name in json_data.keys()
        assert output_1_name in json_data.keys()
        assert output_2_name in json_data.keys()


def test_rename_output(data, acro):
    """Output renaming test."""
    _ = acro.crosstab(data.year, data.grant_type)
    output: dict = acro.finalise()
    output_0 = list(output.keys())[0]
    timestamp = output_0.split("_")[2]
    acro.rename_output(output_0, "cross_table")
    output: dict = acro.finalise()
    new_name = "cross_table" + "_" + timestamp
    assert output_0 not in output
    assert new_name in output

    assert os.path.exists(f"outputs/{new_name}.csv") == 1


def test_add_comments(data, acro):
    """Adding comments to output test"""
    _ = acro.crosstab(data.year, data.grant_type)
    output: dict = acro.finalise()
    output_0 = list(output.keys())[0]
    assert output[output_0]["comments"] == ""
    comment = "This is a cross table between year and grant_type"
    acro.add_comments(output_0, comment)
    assert output[output_0]["comments"] == comment
    comment_1 = "6 cells were suppressed"
    acro.add_comments(output_0, comment_1)
    assert output[output_0]["comments"] == comment + ", " + comment_1


def test_custom_output(acro):
    """Adding an unsupported output to the results dictionary test"""
    filename = "XandY.jfif"
    file_path = os.path.abspath(filename)
    acro.custom_output(filename)
    output: dict = acro.finalise()
    output_0 = list(output.keys())[0]
    assert output[output_0]["output"] == file_path


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
    output: dict = acro.finalise()
    correct_summary: str = "review; missing values found"
    output_0 = list(output.keys())[0]
    output_1 = list(output.keys())[1]
    assert output[output_0]["summary"] == correct_summary
    assert output[output_1]["summary"] == correct_summary


def test_suppression_error(caplog):
    """Apply suppression type error test."""
    table_data = {"col1": [1, 2], "col2": [3, 4]}
    mask_data = {"col1": [np.NaN, True], "col2": [True, True]}
    table = pd.DataFrame(data=table_data)
    masks = {"test": pd.DataFrame(data=mask_data)}
    utils.apply_suppression(table, masks)
    assert "problem mask test is not binary" in caplog.text
