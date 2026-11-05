"""Tests for explanations of disclosure risks and checks."""

from copy import deepcopy

import pytest

from acro import ACRO


def test_describe_analysis_risks(acro: ACRO) -> None:
    """Explain the Mean analysis through its actual ontology relationships."""
    description = acro.describe_analysis_risks("Mean")
    analysis = acro.sdc_checks.analyses["Mean"]
    statbarn = acro.sdc_checks.statbarns[analysis["statbarn"]]
    assert "Analysis: Mean" in description
    assert analysis["definition"] in description
    assert analysis["uri"] in description
    assert statbarn["definition"] in description
    assert statbarn["uri"] in description
    assert statbarn["risks"]
    for risk_name in statbarn["risks"]:
        risk = acro.sdc_checks.risks[risk_name]
        assert f"Risk: {risk_name}" in description
        assert risk["definition"] in description
        assert risk["uri"] in description
        for check_name in risk["checks"]:
            check = acro.sdc_checks.checks[check_name]
            assert f"Check: {check_name}" in description
            assert check["definition"] in description
            assert check["uri"] in description
            assert f"Required evidence: {', '.join(check['evidence'])}" in description


def test_describe_risk_and_check(acro: ACRO) -> None:
    """Individual entry points describe only the requested risk or check."""
    risk = acro.describe_risk("Dominance")
    assert acro.sdc_checks.risks["Dominance"]["definition"] in risk
    assert "Check: NKCheck" in risk
    assert "Risk: ClassDisclosure" not in risk
    check = acro.describe_check("MinimumThresholdCheck")
    assert acro.sdc_checks.checks["MinimumThresholdCheck"]["definition"] in check
    assert "Required evidence: count_table" in check
    assert "Check: NKCheck" not in check


def test_describe_risk_appetite_uses_session_value(acro: ACRO) -> None:
    """Explain the active threshold rather than the packaged default."""
    acro.config["safe_threshold"] = 25
    assert acro.describe_risk_appetite("safe_threshold") == (
        "Risk appetite: safe_threshold\n"
        "Minimum number of records required in a group.\nCurrent value: 25"
    )
    assert "proportion" in acro.describe_risk_appetite("safe_nk_k")


@pytest.mark.parametrize(
    ("method", "valid_name"),
    [
        ("describe_analysis_risks", "Mean"),
        ("describe_risk", "Dominance"),
        ("describe_check", "MinimumThresholdCheck"),
        ("describe_risk_appetite", "safe_threshold"),
    ],
)
def test_unknown_description_name(acro: ACRO, method: str, valid_name: str) -> None:
    """Unknown names list the available options."""
    with pytest.raises(ValueError, match="Unknown .*Available names:") as exc:
        getattr(acro, method)("not_a_known_name")
    assert valid_name in str(exc.value)


def test_empty_ontology_relationships(acro: ACRO) -> None:
    """An empty relationship must not be presented as proof of safety."""
    statbarn = acro.sdc_checks.analyses["Mean"]["statbarn"]
    acro.sdc_checks.statbarns[statbarn]["risks"] = []
    assert "does not imply safety" in acro.describe_analysis_risks("Mean")
    acro.sdc_checks.risks["Dominance"]["checks"] = []
    assert "No checks listed" in acro.describe_risk("Dominance")
    acro.sdc_checks.checks["NKCheck"]["evidence"] = []
    assert "Required evidence: None listed" in acro.describe_check("NKCheck")


def test_descriptions_are_read_only(acro: ACRO, tmp_path, monkeypatch, capsys) -> None:
    """Descriptions return text without changing the session or creating files."""
    monkeypatch.chdir(tmp_path)
    before = deepcopy(
        (
            acro.config,
            acro.sdc_checks.analyses,
            acro.sdc_checks.statbarns,
            acro.sdc_checks.risks,
            acro.sdc_checks.checks,
            vars(acro.results),
        )
    )

    def unexpected_open(*args: object, **kwargs: object) -> None:
        pytest.fail("Descriptions must reuse the already loaded ontology")

    monkeypatch.setattr("builtins.open", unexpected_open)
    acro.describe_analysis_risks("Mean")
    acro.describe_risk("Dominance")
    acro.describe_check("NKCheck")
    acro.describe_risk_appetite("safe_threshold")
    after = (
        acro.config,
        acro.sdc_checks.analyses,
        acro.sdc_checks.statbarns,
        acro.sdc_checks.risks,
        acro.sdc_checks.checks,
        vars(acro.results),
    )
    assert before == after
    assert not list(tmp_path.iterdir())
    assert capsys.readouterr().out == ""


def test_absent_optional_risk_appetite(acro: ACRO) -> None:
    """Custom configurations may omit the optional rounding default."""
    del acro.config["safe_round_base"]
    with pytest.raises(ValueError, match="Unknown risk-appetite parameter"):
        acro.describe_risk_appetite("safe_round_base")
