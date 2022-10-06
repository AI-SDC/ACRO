"""This module contains unit tests."""

import os

import pandas as pd
import pytest

from acro import ACRO, add_constant


def test_crosstab_threshold():
    """Crosstab threshold test."""
    # instantiate ACRO
    acro = ACRO()
    # load test data
    path = os.path.join("data", "test_data.dta")
    data = pd.read_stata(path)
    # ACRO crosstab
    _ = acro.crosstab(data.year, data.grant_type)
    # finalise
    output: dict = acro.finalise()
    correct_summary: str = "fail; threshold: 6 cells suppressed; "
    assert output["output_0"]["summary"] == correct_summary


def test_crosstab_multiple():
    """Crosstab multiple rule test."""
    # instantiate ACRO
    acro = ACRO()
    # load test data
    path = os.path.join("data", "test_data.dta")
    data = pd.read_stata(path)
    # ACRO crosstab
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mean"
    )
    # finalise
    output: dict = acro.finalise()
    correct_summary: str = (
        "fail; threshold: 6 cells suppressed; p-ratio: 1 cells suppressed; "
        "nk-rule: 1 cells suppressed; "
    )
    assert output["output_0"]["summary"] == correct_summary


def test_pivot_table_pass():
    """Pivot table pass test."""
    # instantiate ACRO
    acro = ACRO()
    # load test data
    path = os.path.join("data", "test_data.dta")
    data = pd.read_stata(path)
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    # finalise
    output: dict = acro.finalise()
    correct_summary: str = "pass"
    assert output["output_0"]["summary"] == correct_summary


def test_ols():
    """Ordinary Least Squares test."""
    # instantiate ACRO
    acro = ACRO()
    # load test data
    path = os.path.join("data", "test_data.dta")
    data = pd.read_stata(path)
    new_df = data[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
    new_df = new_df.dropna()
    endog = new_df.inc_activity
    exog = new_df[["inc_grants", "inc_donations", "total_costs"]]
    exog = add_constant(exog)
    # ACRO OLS
    results = acro.ols(endog, exog)
    assert results.df_resid == 807
    assert results.rsquared == pytest.approx(0.894, 0.001)
