"""Federated-mode tests: flag configuration, evidence collection, and finalise."""

from __future__ import annotations

import json
import os
import pathlib
import shutil

import pandas as pd
import pytest

from acro import ACRO, add_constant

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


def test_federated_flag_set_via_constructor():
    """ACRO(federated=True) should set the federated attribute."""
    acro = ACRO(federated=True)
    assert acro.federated is True


def test_federated_flag_default_is_false():
    """ACRO() should default to federated=False."""
    acro = ACRO()
    assert acro.federated is False


def test_federated_flag_from_yaml(tmp_path):
    """Federated: true in yaml should set federated=True when no constructor override."""
    yaml_content = (
        "safe_threshold: 10\n"
        "safe_dof_threshold: 10\n"
        "safe_nk_n: 2\n"
        "safe_nk_k: 0.90\n"
        "safe_pratio_p: 0.10\n"
        "check_missing_values: false\n"
        "survival_safe_threshold: 10\n"
        "zeros_are_disclosive: true\n"
        "federated: true\n"
    )
    acro_pkg = pathlib.Path(__file__).parent.parent / "acro"
    cfg_dest = acro_pkg / "fed_test.yaml"
    cfg_dest.write_text(yaml_content)
    try:
        acro = ACRO(config="fed_test")
        assert acro.federated is True
    finally:
        cfg_dest.unlink(missing_ok=True)


def test_federated_constructor_overrides_yaml():
    """Constructor federated=False should override yaml federated: true."""
    yaml_content = (
        "safe_threshold: 10\n"
        "safe_dof_threshold: 10\n"
        "safe_nk_n: 2\n"
        "safe_nk_k: 0.90\n"
        "safe_pratio_p: 0.10\n"
        "check_missing_values: false\n"
        "survival_safe_threshold: 10\n"
        "zeros_are_disclosive: true\n"
        "federated: true\n"
    )
    acro_pkg = pathlib.Path(__file__).parent.parent / "acro"
    cfg_dest = acro_pkg / "fed_override_test.yaml"
    cfg_dest.write_text(yaml_content)
    try:
        acro = ACRO(config="fed_override_test", federated=False)
        assert acro.federated is False
    finally:
        cfg_dest.unlink(missing_ok=True)


def test_federated_crosstab_skips_checks_and_stores_evidence(data):
    """In federated mode, crosstab should store evidence and skip checks."""
    acro = ACRO(federated=True)
    table = acro.crosstab(data.year, data.grant_type)

    assert isinstance(table, pd.DataFrame)
    assert not table.empty
    assert acro.results.output_id == 1
    assert len(acro.results.results) == 0
    assert "output_0" in acro._federated_evidence
    entry = acro._federated_evidence["output_0"]
    assert "count_table" in entry["interim_tables"]
    assert entry["analysis_names"] == ["FrequencyTable"]


def test_federated_pivot_table_stores_evidence(data):
    """In federated mode, pivot_table should store evidence."""
    acro = ACRO(federated=True)
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean"]
    )
    assert "output_0" in acro._federated_evidence
    assert acro._federated_evidence["output_0"]["analysis_names"] == ["Mean"]


def test_federated_finalise_writes_evidence_json(data, cleanup_path):
    """Finalise() in federated mode should produce evidence.json and CSV files."""
    acro = ACRO(federated=True)
    _ = acro.crosstab(data.year, data.grant_type)
    result = acro.finalise(PATH)

    assert result is not None
    evidence_path = os.path.normpath(f"{PATH}/evidence.json")
    assert os.path.exists(evidence_path)

    with open(evidence_path, encoding="utf-8") as fh:
        evidence = json.load(fh)

    assert "version" in evidence
    assert "outputs" in evidence
    assert "output_0" in evidence["outputs"]

    entry = evidence["outputs"]["output_0"]
    count_table_file = entry["interim_tables"].get("count_table")
    assert count_table_file is not None
    assert os.path.exists(os.path.normpath(f"{PATH}/{count_table_file}"))
    assert os.path.exists(os.path.normpath(f"{PATH}/config.json"))
    assert not os.path.exists(os.path.normpath(f"{PATH}/results.json"))

    shutil.rmtree(PATH)


def test_federated_finalise_multiple_outputs(data, cleanup_path):
    """Federated finalise with multiple outputs produces one entry per output."""
    acro = ACRO(federated=True)
    _ = acro.crosstab(data.year, data.grant_type)
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean"]
    )
    result = acro.finalise(PATH)
    assert result is not None

    with open(os.path.normpath(f"{PATH}/evidence.json"), encoding="utf-8") as fh:
        evidence = json.load(fh)

    assert len(evidence["outputs"]) == 2
    assert "output_0" in evidence["outputs"]
    assert "output_1" in evidence["outputs"]
    shutil.rmtree(PATH)


def test_federated_finalise_regression(data, cleanup_path):
    """Federated finalise for a regression writes DoF evidence."""
    acro = ACRO(federated=True)
    new_df = data[
        ["inc_activity", "inc_grants", "inc_donations", "total_costs"]
    ].dropna()
    endog = new_df.inc_activity
    exog = new_df[["inc_grants", "inc_donations", "total_costs"]]
    exog = add_constant(exog)
    _ = acro.ols(endog, exog)

    result = acro.finalise(PATH)
    assert result is not None

    with open(os.path.normpath(f"{PATH}/evidence.json"), encoding="utf-8") as fh:
        evidence = json.load(fh)

    entry = evidence["outputs"]["output_0"]
    assert entry["dof"] == 807
    assert entry["analysis_names"] == ["GeneralLinearModel"]
    assert entry["interim_tables"] == {}
    shutil.rmtree(PATH)


def test_local_mode_unaffected_by_federated_flag(data, cleanup_path):
    """Non-federated ACRO should still produce results.json as before."""
    acro = ACRO(suppress=False)
    assert acro.federated is False
    _ = acro.crosstab(data.year, data.grant_type)
    acro.add_exception("output_0", "Let me have it")
    result = acro.finalise(PATH)

    assert result is not None
    assert os.path.exists(os.path.normpath(f"{PATH}/results.json"))
    assert not os.path.exists(os.path.normpath(f"{PATH}/evidence.json"))
    shutil.rmtree(PATH)
