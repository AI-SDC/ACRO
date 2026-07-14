"""Plot tests: surv_func, histogram, pie chart (local and federated)."""

from __future__ import annotations

import os
import shutil

import matplotlib as mpl

mpl.use("Agg")

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from acro import ACRO
from acro.acro_tables import _rounded_survival_table
from acro.record import Records

PATH: str = "RES_PYTEST"


@pytest.fixture
def cleanup_path():
    """Clean up output directories before and after each test."""
    for d in ["RES_PYTEST", "outputs", "acro_artifacts"]:
        shutil.rmtree(d, ignore_errors=True)
    yield
    for d in ["RES_PYTEST", "outputs", "acro_artifacts"]:
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


def test_surv_func(acro, cleanup_path):
    """Test survival tables and plots."""
    try:
        data = sm.datasets.get_rdataset("flchain", "survival").data
    except Exception:
        np.random.seed(42)
        data = pd.DataFrame(
            {
                "futime": np.random.exponential(100, 500),
                "death": np.random.binomial(1, 0.3, 500),
                "sex": np.random.choice(["F", "M"], 500),
            }
        )

    data = data.loc[data.sex == "F", :]
    _ = acro.surv_func(data.futime, data.death, output="table")
    output = acro.results.get_index(0)
    assert output.status in ["fail", "review"]
    assert "KaplanMeier" in output.summary

    filename = os.path.normpath("acro_artifacts/kaplan-meier_0.png")
    _ = acro.surv_func(data.futime, data.death, output="plot")
    assert os.path.exists(filename)
    acro.add_exception("output_0", "I need this")
    acro.add_exception("output_1", "Let me have it")

    foo = acro.surv_func(data.futime, data.death, output="something_else")
    assert foo is None

    results: Records = acro.finalise(path=PATH)
    output_1 = results.get_index(1)
    assert output_1.output == [filename]
    shutil.rmtree(PATH)


def test_rounded_survival_table():
    """Test the rounded_survival_table function for survival analysis."""
    survival_table = pd.DataFrame(
        {
            "Surv prob": [1.0, 0.95, 0.90, 0.85, 0.80],
            "num at risk": [100, 95, 85, 75, 60],
            "num events": [0, 5, 10, 10, 15],
        }
    )
    result = _rounded_survival_table(survival_table.copy())
    assert "rounded_survival_fun" in result.columns
    assert len(result) == 5
    assert all(
        (result["rounded_survival_fun"] >= 0) & (result["rounded_survival_fun"] <= 1)
    )


def test_histogram_disclosive(acro, caplog, cleanup_path):
    """Test a disclosive histogram under the new suppression workflow."""
    small_data = pd.DataFrame({"value": [1, 2, 3]})
    result = acro.hist(small_data, "value")

    assert result == ""
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(path=PATH)
    output_0 = results.get_index(0)

    assert (
        "Histogram will not be shown as the value column is disclosive." in caplog.text
    )
    assert output_0.status == "fail"
    assert output_0.output == []
    shutil.rmtree(PATH)


def test_histogram_non_disclosive(acro, cleanup_path):
    """Test a non-disclosive histogram with a larger synthetic dataset."""
    rng = np.random.default_rng(42)
    data = pd.DataFrame({"value": rng.normal(size=2000)})

    result = acro.hist(data, "value", bins=5)

    assert result is not None
    assert os.path.exists(result)
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(path=PATH)
    output_0 = results.get_index(0)
    assert output_0.output == [os.path.normpath(result)]
    assert output_0.status == "review"
    shutil.rmtree(PATH)


def test_pie_disclosive(acro, caplog, cleanup_path):
    """Test a disclosive pie chart."""
    df = pd.DataFrame(
        {"grant_type": (["A"] * 20) + (["B"] * 15) + (["C"] * 12) + (["D"] * 5)}
    )
    _ = acro.pie(df, "grant_type", filename="pie.png")
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(path=PATH)
    output_0 = results.get_index(0)

    assert (
        "Pie chart will not be shown as the grant_type column is disclosive."
        in caplog.text
    )
    assert output_0.status == "fail"
    shutil.rmtree(PATH)


def test_pie_non_disclosive(data, acro, cleanup_path):
    """Test a non-disclosive pie chart."""
    filename = os.path.normpath("acro_artifacts/pie_0.png")
    result = acro.pie(data, "grant_type", filename="pie.png")
    assert os.path.normpath(result) == filename
    assert os.path.exists(filename)
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(path=PATH)
    output_0 = results.get_index(0)
    assert output_0.output == [filename]
    assert output_0.status == "review"
    shutil.rmtree(PATH)


def test_store_federated_evidence_with_dataframe_dof():
    """_store_federated_evidence serialises DataFrame DoF to CSV string."""
    acro_obj = ACRO(federated=True)
    np.random.seed(42)
    mock_data = pd.DataFrame(
        {
            "futime": np.random.exponential(100, 300),
            "death": np.random.binomial(1, 0.3, 300),
            "sex": np.random.choice(["F", "M"], 300),
        }
    )
    mock_data = mock_data.loc[mock_data.sex == "F"]
    _ = acro_obj.surv_func(mock_data.futime, mock_data.death, output="table")
    entry = acro_obj._federated_evidence.get("output_0", {})
    dof_val = entry.get("dof")
    assert dof_val is not None
    assert isinstance(dof_val, str)
    assert "\n" in dof_val


def test_surv_func_federated_table():
    """Surv_func in federated mode with output='table' returns survival table."""
    acro_obj = ACRO(federated=True)
    np.random.seed(42)
    mock_data = pd.DataFrame(
        {
            "futime": np.random.exponential(100, 500),
            "death": np.random.binomial(1, 0.3, 500),
        }
    )
    result = acro_obj.surv_func(mock_data.futime, mock_data.death, output="table")
    assert isinstance(result, pd.DataFrame)
    assert acro_obj.results.output_id == 1
    assert len(acro_obj.results.results) == 0


def test_surv_func_federated_plot_blocked_extension():
    """Surv_func federated with blocked extension returns None."""
    acro_obj = ACRO(federated=True)
    acro_obj.results.blocked_extensions = [".png"]
    np.random.seed(42)
    mock_data = pd.DataFrame(
        {
            "futime": np.random.exponential(100, 500),
            "death": np.random.binomial(1, 0.3, 500),
        }
    )
    result = acro_obj.surv_func(
        mock_data.futime, mock_data.death, output="plot", filename="km.png"
    )
    assert result is None


def test_surv_func_federated_returns_none_for_unknown_output():
    """Surv_func federated with unknown output type returns None."""
    acro_obj = ACRO(federated=True)
    np.random.seed(42)
    mock_data = pd.DataFrame(
        {
            "futime": np.random.exponential(100, 500),
            "death": np.random.binomial(1, 0.3, 500),
        }
    )
    result = acro_obj.surv_func(
        mock_data.futime, mock_data.death, output="something_unknown"
    )
    assert result is None


def test_surv_func_returns_none_for_unknown_output():
    """Surv_func local mode with unknown output type returns None."""
    acro_obj = ACRO(suppress=True)
    np.random.seed(42)
    mock_data = pd.DataFrame(
        {
            "futime": np.random.exponential(100, 500),
            "death": np.random.binomial(1, 0.3, 500),
        }
    )
    result = acro_obj.surv_func(mock_data.futime, mock_data.death, output="invalid")
    assert result is None


def test_surv_func_suppress_plot_blocked_extension():
    """Surv_func with suppress=True, blocked extension returns None."""
    acro_obj = ACRO(suppress=True)
    acro_obj.results.blocked_extensions = [".png"]
    np.random.seed(7)
    mock_data = pd.DataFrame(
        {
            "futime": np.random.exponential(100, 500),
            "death": np.random.binomial(1, 0.3, 500),
        }
    )
    result = acro_obj.surv_func(
        mock_data.futime, mock_data.death, output="plot", filename="km.png"
    )
    assert result is None


def test_hist_federated_returns_none():
    """Hist() in federated mode stores evidence and returns None."""
    acro_obj = ACRO(federated=True)
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"val": rng.normal(size=500)})
    result = acro_obj.hist(df, "val")
    assert result is None
    assert "output_0" in acro_obj._federated_evidence
    assert len(acro_obj.results.results) == 0


def test_hist_blocked_extension():
    """Hist() with a blocked extension returns None."""
    acro_obj = ACRO(suppress=True)
    acro_obj.results.blocked_extensions = [".png"]
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"val": rng.normal(size=500)})
    result = acro_obj.hist(df, "val", filename="histogram.png")
    assert result is None
    assert len(acro_obj.results.results) == 0


def test_hist_non_disclosive_no_suppress(data):
    """Hist() with suppress=False always records output."""
    acro_obj = ACRO(suppress=False)
    result = acro_obj.hist(data, "inc_grants", bins=10)
    output = acro_obj.results.get_index(0)
    assert output.output_type == "histogram"
    assert result is not None
    assert result != ""
    assert output.output == [os.path.normpath(result)]


def test_pie_federated_returns_none(data):
    """Pie() in federated mode stores evidence and returns None."""
    acro_obj = ACRO(federated=True)
    result = acro_obj.pie(data, "grant_type")
    assert result is None
    assert "output_0" in acro_obj._federated_evidence
    assert len(acro_obj.results.results) == 0


def test_pie_blocked_extension(data):
    """Pie() with a blocked extension returns None."""
    acro_obj = ACRO(suppress=True)
    acro_obj.results.blocked_extensions = [".png"]
    result = acro_obj.pie(data, "grant_type", filename="pie.png")
    assert result is None
    assert len(acro_obj.results.results) == 0


def test_pie_records_output_non_disclosive(data):
    """Pie() on non-disclosive data records output with correct type."""
    acro_obj = ACRO(suppress=False)
    acro_obj.pie(data, "grant_type")
    output = acro_obj.results.get_index(0)
    assert output.output_type == "pie chart"
    assert output.status in ("pass", "review")


def test_hist_federated_no_output_recorded(data):
    """Hist() federated gate: no result is added to results."""
    acro_obj = ACRO(federated=True)
    result = acro_obj.hist(data, "inc_grants", bins=5)
    assert result is None
    assert acro_obj.results.output_id == 1
    assert len(acro_obj.results.results) == 0


def test_surv_func_suppress_true_table_records_exception():
    """Surv_func with suppress=True and output='table' adds exception."""
    acro_obj = ACRO(suppress=True)
    np.random.seed(42)
    mock_data = pd.DataFrame(
        {
            "futime": np.random.exponential(100, 500),
            "death": np.random.binomial(1, 0.3, 500),
        }
    )
    result = acro_obj.surv_func(mock_data.futime, mock_data.death, output="table")
    assert isinstance(result, pd.DataFrame)
    output = acro_obj.results.get_index(0)
    assert output.status == "review"
    assert "Events Reported" in output.exception
