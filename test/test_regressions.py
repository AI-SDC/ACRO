"""Regression tests: ols, olsr, logit, logitr, probit, probitr (local and federated)."""

from __future__ import annotations

import shutil

import pytest

from acro import ACRO, add_constant
from acro.acro_stata_parser import stata_details_to_list

PATH: str = "RES_PYTEST"


@pytest.mark.usefixtures("cleanup_path")
def test_ols(data, acro):
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


@pytest.mark.usefixtures("cleanup_path")
def test_probit_logit(data, acro):
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
    assert acro_obj._federated_evidence["output_0"]["analysis_names"] == [
        "GeneralLinearModel"
    ]


@pytest.mark.parametrize(
    ("method_name", "expected_analysis"),
    [("logitr", "Logit"), ("probitr", "Probit")],
)
def test_logitr_probitr_federated(data, method_name, expected_analysis):
    """Logitr/Probitr in federated mode stores evidence and skips checks."""
    acro_obj = ACRO(federated=True)
    new_df = data[
        ["survivor", "inc_activity", "inc_grants", "inc_donations", "total_costs"]
    ].dropna()
    new_df = new_df.copy()
    new_df["survivor"] = new_df["survivor"].astype("category").cat.codes
    method = getattr(acro_obj, method_name)
    results = method(
        formula="survivor ~ inc_activity + inc_grants + inc_donations + total_costs",
        data=new_df,
    )
    assert results.df_resid == 806
    assert len(acro_obj.results.results) == 0
    assert acro_obj._federated_evidence["output_0"]["analysis_names"] == [
        expected_analysis
    ]


@pytest.mark.parametrize(
    ("method_name", "expected_analysis"),
    [("probit", "Probit"), ("logit", "Logit")],
)
def test_probit_logit_federated(data, method_name, expected_analysis):
    """Probit/Logit in federated mode stores evidence and skips checks."""
    acro_obj = ACRO(federated=True)
    new_df = data[
        ["survivor", "inc_activity", "inc_grants", "inc_donations", "total_costs"]
    ].dropna()
    endog = new_df["survivor"].astype("category").cat.codes
    endog.name = "survivor"
    exog = new_df[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
    exog = add_constant(exog)
    method = getattr(acro_obj, method_name)
    results = method(endog, exog)
    assert results.df_resid == 806
    assert len(acro_obj.results.results) == 0
    assert acro_obj._federated_evidence["output_0"]["analysis_names"] == [
        expected_analysis
    ]


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


@pytest.mark.usefixtures("cleanup_path")
def test_process_output_standalone_ols_via_refactoring(data):
    """Test _process_output in standalone mode with OLS (refactored method)."""
    acro = ACRO(suppress=True)
    new_df = data[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
    new_df = new_df.dropna()

    endog = new_df.inc_activity
    exog = new_df[["inc_grants", "inc_donations", "total_costs"]]
    exog = add_constant(exog)

    results = acro.ols(endog, exog)
    assert results.df_resid == 807

    res = acro.results.get_index(-1)
    assert res.status == "pass"
    assert res.output_type == "regression"
    assert res.properties["method"] == "ols"


@pytest.mark.usefixtures("cleanup_path")
@pytest.mark.parametrize("method_name", ["logit", "probit"])
def test_process_output_standalone_logit_probit_via_refactoring(data, method_name):
    """Test _process_output in standalone mode with Logit/Probit (refactored method)."""
    acro = ACRO(suppress=True)
    new_df = data[
        ["survivor", "inc_activity", "inc_grants", "inc_donations", "total_costs"]
    ]
    new_df = new_df.dropna()

    endog = (new_df["survivor"] == "Dead in 2015").astype(int)
    exog = new_df[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
    exog = add_constant(exog)

    getattr(acro, method_name)(endog, exog)
    res = acro.results.get_index(-1)
    assert res.output_type == "regression"
    assert res.properties["method"] == method_name


@pytest.mark.usefixtures("cleanup_path")
def test_process_output_federated_ols_via_refactoring(data):
    """Test _process_output in federated mode with OLS (refactored method)."""
    acro = ACRO(suppress=True, federated=True)
    new_df = data[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
    new_df = new_df.dropna()

    endog = new_df.inc_activity
    exog = new_df[["inc_grants", "inc_donations", "total_costs"]]
    exog = add_constant(exog)

    results = acro.ols(endog, exog)
    assert results.df_resid == 807
    assert acro.federated is True


@pytest.mark.usefixtures("cleanup_path")
@pytest.mark.parametrize("method_name", ["logit", "probit"])
def test_process_output_federated_logit_probit_via_refactoring(data, method_name):
    """Test _process_output in federated mode with Logit/Probit (refactored method)."""
    acro = ACRO(suppress=True, federated=True)
    new_df = data[
        ["survivor", "inc_activity", "inc_grants", "inc_donations", "total_costs"]
    ]
    new_df = new_df.dropna()

    endog = (new_df["survivor"] == "Dead in 2015").astype(int)
    exog = new_df[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
    exog = add_constant(exog)

    getattr(acro, method_name)(endog, exog)
    assert acro.federated is True


@pytest.mark.parametrize(
    "method_name",
    ["olsr", "logitr", "probitr"],
)
def test_formula_methods_accept_extra_args_kwargs(data, method_name):
    """Olsr/logitr/probitr silently ignore extra *args/**kwargs (branch coverage)."""
    acro_obj = ACRO(suppress=False)
    new_df = data[
        ["survivor", "inc_activity", "inc_grants", "inc_donations", "total_costs"]
    ].dropna()
    new_df = new_df.copy()
    new_df["survivor"] = new_df["survivor"].astype("category").cat.codes

    formula = "survivor ~ inc_activity + inc_grants + inc_donations + total_costs"
    if method_name == "olsr":
        formula = "inc_activity ~ inc_grants + inc_donations + total_costs"

    method = getattr(acro_obj, method_name)
    # passing a positional arg and a keyword arg exercises the `if args or kwargs` branch
    results = method(formula, data=new_df, extra_ignored_kwarg=True)
    assert results.df_resid > 0


def test_stata_details_to_list_accepts_list():
    """Stata_details_to_list returns a list when given a list input (coverage)."""
    input_list = ["var1", "var2", "var3"]
    result = stata_details_to_list(input_list)
    assert result == input_list
    assert isinstance(result, list)


def test_stata_details_to_list_accepts_string():
    """Stata_details_to_list splits a string when given string input."""
    input_str = "var1 var2 var3"
    result = stata_details_to_list(input_str)
    assert result == ["var1", "var2", "var3"]
