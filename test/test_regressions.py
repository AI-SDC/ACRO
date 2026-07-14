"""Regression tests: ols, olsr, logit, logitr, probit, probitr (local and federated)."""

from __future__ import annotations

import os
import shutil

import pandas as pd
import pytest

from acro import ACRO, add_constant
from acro.record import Records

PATH: str = "RES_PYTEST"


@pytest.fixture
def cleanup_path():
    """Clean up output directories before and after each test."""
    for d in ["RES_PYTEST", "outputs"]:
        shutil.rmtree(d, ignore_errors=True)
    yield
    for d in ["RES_PYTEST", "outputs"]:
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def data() -> pd.DataFrame:
    """Load test data."""
    path = os.path.join("data", "test_data.dta")
    return pd.read_stata(path)


@pytest.fixture
def acro() -> ACRO:
    """Initialise ACRO."""
    return ACRO(suppress=True)


def test_ols(data, acro, cleanup_path):
    """Ordinary Least Squares test."""
    new_df = data[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
    new_df = new_df.dropna()
    # OLS too few Dof
    endog = new_df.inc_activity.iloc[0:10]
    exog = new_df[["inc_grants", "inc_donations", "total_costs"]].iloc[0:10]
    exog = add_constant(exog)
    results = acro.ols(endog, exog)
    assert results.df_resid == 6
    res = acro.results.get_index(-1)
    assert res.status == "fail"
    acro.remove_output(res.uid)

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
    results = acro.finalise(PATH)
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    assert output_0.status == "pass"
    assert output_1.status == "pass"
    shutil.rmtree(PATH)


def test_probit_logit(data, acro, cleanup_path):
    """Probit and Logit tests."""
    new_df = data[
        ["survivor", "inc_activity", "inc_grants", "inc_donations", "total_costs"]
    ]
    new_df = new_df.dropna()
    endog = new_df["survivor"].astype("category").cat.codes
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
    results = acro.finalise(PATH)
    for i in range(4):
        assert results.get_index(i).status == "pass"
    shutil.rmtree(PATH)


def test_federated_ols_stores_evidence(data):
    """In federated mode, ols should store evidence (DoF) and skip checks."""
    acro_obj = ACRO(federated=True)
    new_df = data[
        ["inc_activity", "inc_grants", "inc_donations", "total_costs"]
    ].dropna()
    endog = new_df.inc_activity
    exog = new_df[["inc_grants", "inc_donations", "total_costs"]]
    exog = add_constant(exog)
    results = acro_obj.ols(endog, exog)

    assert results.df_resid == 807
    assert len(acro_obj.results.results) == 0
    assert "output_0" in acro_obj._federated_evidence
    entry = acro_obj._federated_evidence["output_0"]
    assert entry["analysis_names"] == ["GeneralLinearModel"]
    assert entry["dof"] == 807


def test_olsr_federated(data):
    """Olsr() in federated mode stores evidence and skips checks."""
    acro_obj = ACRO(federated=True)
    new_df = data[
        ["inc_activity", "inc_grants", "inc_donations", "total_costs"]
    ].dropna()
    results = acro_obj.olsr(
        formula="inc_activity ~ inc_grants + inc_donations + total_costs", data=new_df
    )
    assert results.df_resid == 807
    assert len(acro_obj.results.results) == 0
    assert "output_0" in acro_obj._federated_evidence
    assert acro_obj._federated_evidence["output_0"]["analysis_names"] == ["GeneralLinearModel"]


def test_logitr_federated(data):
    """Logitr() in federated mode stores evidence and skips checks."""
    acro_obj = ACRO(federated=True)
    new_df = data[
        ["survivor", "inc_activity", "inc_grants", "inc_donations", "total_costs"]
    ].dropna()
    new_df = new_df.copy()
    new_df["survivor"] = new_df["survivor"].astype("category").cat.codes
    results = acro_obj.logitr(
        formula="survivor ~ inc_activity + inc_grants + inc_donations + total_costs",
        data=new_df,
    )
    assert results.df_resid == 806
    assert len(acro_obj.results.results) == 0
    assert acro_obj._federated_evidence["output_0"]["analysis_names"] == ["Logit"]


def test_probitr_federated(data):
    """Probitr() in federated mode stores evidence and skips checks."""
    acro_obj = ACRO(federated=True)
    new_df = data[
        ["survivor", "inc_activity", "inc_grants", "inc_donations", "total_costs"]
    ].dropna()
    new_df = new_df.copy()
    new_df["survivor"] = new_df["survivor"].astype("category").cat.codes
    results = acro_obj.probitr(
        formula="survivor ~ inc_activity + inc_grants + inc_donations + total_costs",
        data=new_df,
    )
    assert results.df_resid == 806
    assert len(acro_obj.results.results) == 0
    assert acro_obj._federated_evidence["output_0"]["analysis_names"] == ["Probit"]


def test_probit_federated(data):
    """Probit() in federated mode stores evidence and skips checks."""
    acro_obj = ACRO(federated=True)
    new_df = data[
        ["survivor", "inc_activity", "inc_grants", "inc_donations", "total_costs"]
    ].dropna()
    endog = new_df["survivor"].astype("category").cat.codes
    endog.name = "survivor"
    exog = new_df[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
    exog = add_constant(exog)
    results = acro_obj.probit(endog, exog)
    assert results.df_resid == 806
    assert len(acro_obj.results.results) == 0
    assert acro_obj._federated_evidence["output_0"]["analysis_names"] == ["Probit"]


def test_logit_federated(data):
    """Logit() in federated mode stores evidence and skips checks."""
    acro_obj = ACRO(federated=True)
    new_df = data[
        ["survivor", "inc_activity", "inc_grants", "inc_donations", "total_costs"]
    ].dropna()
    endog = new_df["survivor"].astype("category").cat.codes
    endog.name = "survivor"
    exog = new_df[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
    exog = add_constant(exog)
    results = acro_obj.logit(endog, exog)
    assert results.df_resid == 806
    assert len(acro_obj.results.results) == 0
    assert acro_obj._federated_evidence["output_0"]["analysis_names"] == ["Logit"]


def test_show_fair_summaries_regression(data):
    """Show_fair_summaries() works when fair dict has nested dict values."""
    acro_obj = ACRO(suppress=False)
    new_df = data[
        ["inc_activity", "inc_grants", "inc_donations", "total_costs"]
    ].dropna()
    endog = new_df.inc_activity
    exog = new_df[["inc_grants", "inc_donations", "total_costs"]]
    exog = add_constant(exog)
    _ = acro_obj.ols(endog, exog)
    result = acro_obj.show_fair_summaries()
    assert isinstance(result, str)
    assert len(result) > 0
