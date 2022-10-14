"""This module contains unit tests."""

import os

import pandas as pd
import pytest

from acro import ACRO, add_constant


def get_data() -> pd.DataFrame:
    """Load test data."""
    path = os.path.join("data", "test_data.dta")
    data = pd.read_stata(path)
    return data


def test_crosstab_threshold():
    """Crosstab threshold test."""
    data = get_data()
    acro = ACRO()
    _ = acro.crosstab(data.year, data.grant_type)
    output: dict = acro.finalise()
    correct_summary: str = "fail; threshold: 6 cells suppressed; "
    assert output["output_0"]["summary"] == correct_summary


def test_crosstab_multiple():
    """Crosstab multiple rule test."""
    data = get_data()
    acro = ACRO()
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mean"
    )
    output: dict = acro.finalise()
    correct_summary: str = (
        "fail; threshold: 6 cells suppressed; p-ratio: 1 cells suppressed; "
        "nk-rule: 1 cells suppressed; "
    )
    assert output["output_0"]["summary"] == correct_summary


def test_negatives():
    """Pivot table and Crosstab with negative values."""
    data = get_data()
    data.loc[0:10, "inc_grants"] = -10
    acro = ACRO()
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mean"
    )
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    output: dict = acro.finalise()
    correct_summary: str = "review; negative values found"
    assert output["output_0"]["summary"] == correct_summary
    assert output["output_1"]["summary"] == correct_summary


def test_pivot_table_pass():
    """Pivot table pass test."""
    data = get_data()
    acro = ACRO()
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    output: dict = acro.finalise()
    correct_summary: str = "pass"
    assert output["output_0"]["summary"] == correct_summary


def test_pivot_table_cols():
    """Pivot table with columns test."""
    data = get_data()
    acro = ACRO()
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
    assert output["output_0"]["summary"] == correct_summary


def test_ols():
    """Ordinary Least Squares test."""
    data = get_data()
    acro = ACRO()
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
    assert output["output_0"]["summary"] == correct_summary
    assert output["output_1"]["summary"] == correct_summary


def test_probit_logit():
    """Probit and Logit tests."""
    data = get_data()
    acro = ACRO()
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
    assert output["output_0"]["summary"] == correct_summary
    assert output["output_1"]["summary"] == correct_summary
    assert output["output_2"]["summary"] == correct_summary
    assert output["output_3"]["summary"] == correct_summary


def test_finalise_excel():
    """Finalise excel test."""
    data = get_data()
    acro = ACRO()
    path = os.path.join("data", "test_data.dta")
    data = pd.read_stata(path)
    _ = acro.crosstab(data.year, data.grant_type)
    _ = acro.finalise("test.xlsx")
    load_data = pd.read_excel("test.xlsx", sheet_name="output_0")
    correct_cell: str = "_ = acro.crosstab(data.year, data.grant_type)"
    assert load_data.iloc[0, 0] == "Command"
    assert load_data.iloc[0, 1] == correct_cell


def test_output_removal():
    """Output removal and print test."""
    data = get_data()
    acro = ACRO()
    _ = acro.crosstab(data.year, data.grant_type)
    _ = acro.crosstab(data.year, data.grant_type)
    _ = acro.crosstab(data.year, data.grant_type)
    acro.remove_output("output_0")
    output: dict = acro.finalise()
    correct_summary: str = "fail; threshold: 6 cells suppressed; "
    assert "output_0" not in output
    assert "output_1" in output
    assert output["output_1"]["summary"] == correct_summary
    acro.print_outputs()
