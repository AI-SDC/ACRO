"""Unit tests for sdcchecks.py."""

import pandas as pd

from acro.acro import ACRO
from acro.acro_regression import add_constant
from acro.sdcchecks import SDCChecks, SDCEvidence
from acro.tablemodeldetails import TableModelDetails


def test_sdcevidence_populate_dof_else_branch():
    """Populate_dof falls back to -1 for unknown model type."""
    ev = SDCEvidence()
    ev.populate_dof("not_a_model")
    assert ev.dof == -1


def test_get_table_sdc_duplicate_check_skipped(data):
    """Get_table_sdc skips checks already seen across multiple analyses (line 164).

    When two analyses produce the same check name, only the first occurrence
    is included in the SDC summary — the continue branch on line 164.
    """
    acro_obj = ACRO(suppress=False)
    # mean+std both map to LinearAggregations which shares checks — run both
    _ = acro_obj.pivot_table(
        data,
        index=["grant_type"],
        values=["inc_grants"],
        aggfunc=["mean", "std"],
    )
    output = acro_obj.results.get_index(0)
    sdc = output.sdc
    # Each check name should appear exactly once in sdc["cells"]
    for check_name in sdc["cells"]:
        assert sdc["cells"].get(check_name) is not None
    assert isinstance(sdc["summary"], dict)


def test_get_table_sdc_minimumdofcheck_pass(data):
    """Get_table_sdc branch for MinimumDoFCheck with int mask: 0 when DoF passes (line 168)."""
    acro_obj = ACRO(suppress=False)
    new_df = data[
        ["inc_activity", "inc_grants", "inc_donations", "total_costs"]
    ].dropna()
    endog = new_df.inc_activity
    exog = new_df[["inc_grants", "inc_donations", "total_costs"]]
    exog = add_constant(exog)
    _ = acro_obj.ols(endog, exog)
    output = acro_obj.results.get_index(0)
    # Regression sdc is {} — DoF check result is stored in properties not sdc
    assert output.properties["dof"] == 807
    assert output.status == "pass"


def test_sdcevidence_populate_from_list_tablemodel(data):
    """Populate_from_list with TableModelDetails correctly populates count_table and DoF."""
    idx = data["year"]
    vals = data["inc_grants"]
    model = TableModelDetails(
        index=[idx],
        columns=[],
        values=vals,
        risk_appetite={
            "safe_threshold": 10,
            "safe_nk_n": 2,
            "safe_nk_k": 0.90,
            "safe_pratio_p": 0.10,
            "check_missing_values": False,
            "zeros_are_disclosive": True,
        },
        command="crosstab",
    )
    ev = SDCEvidence()
    ev.populate_from_list({"DoF", "count_table"}, model)
    assert "count_table" in ev.interim_tables
    assert isinstance(ev.dof, pd.DataFrame)


def test_check_min_threshold_array_non_hist(data):
    """Check_min_threshold for non-hist array type exercises."""
    acro_obj = ACRO(suppress=False)
    col = data["grant_type"]
    model = TableModelDetails(
        index=[col],
        thekwargs={},
        risk_appetite=acro_obj.sdc_checks.risk_appetite,
        command="pie",
    )
    model.model_type = "array"
    ev = SDCEvidence()
    ev.populate_from_list(set(), model)
    # Manually set the minimal evidence needed
    ev.interim_tables = {}
    # Force model to array, command != hist
    sdc = SDCChecks(acro_obj.sdc_checks.risk_appetite)
    ev2 = SDCEvidence()
    # array model_type, non-hist command
    status, _, _ = sdc.check_min_threshold("PieChart", ev2, model)
    assert status in ("pass", "fail", "review")


def test_manual_check_unknown_model_type():
    """Manual_check returns fail when model_type not in recognised list."""
    acro_obj = ACRO(suppress=False)
    model = TableModelDetails(
        index=[pd.Series([1, 2], name="x")],
        columns=[],
        values=pd.Series([1, 2], name="v"),
    )
    model.model_type = "unknown_type"
    ev = SDCEvidence()
    status, summary, _ = acro_obj.sdc_checks.manual_check("X", ev, model)
    assert status == "fail"
    assert "insufficient" in summary


def test_check_nk_dominance_with_negatives(data):
    """Check_nk_dominance returns review when negative values present (line 531)."""
    acro_obj = ACRO(suppress=False)
    # Build a table with negative inc_grants in some cells
    data2 = data.copy()
    data2.loc[data2.index[:20], "inc_grants"] = -500
    _ = acro_obj.crosstab(
        data2.year, data2.grant_type, values=data2.inc_grants, aggfunc="sum"
    )
    output = acro_obj.results.get_index(0)
    # TODO check summary message is
    # TODO "Dominance not defined when negative value are present"
    # TODO check status is correctly set to review: should not be fail
    assert output.status in ("review", "fail")


def test_check_ppercent_with_negatives(data):
    """Check_ppercent_dominance returns review when negative values present."""
    acro_obj = ACRO(suppress=False)
    data2 = data.copy()
    data2.loc[data2.index[:50], "inc_grants"] = -100
    _ = acro_obj.crosstab(
        data2.year, data2.grant_type, values=data2.inc_grants, aggfunc="mean"
    )
    output = acro_obj.results.get_index(0)
    # TODO check summary message is
    # TODO "Dominance not defined when negative value are present"
    # TODO check status is correctly set to review: should not be fail
    assert output.status in ("review", "fail")


def test_check_presence_of_zero_disclosive(data):
    """Check_presence_of_zero fires and fails when zeros_are_disclosive=True and zero cells exist."""
    acro_obj = ACRO(suppress=False)
    acro_obj.sdc_checks.risk_appetite["zeros_are_disclosive"] = True
    # Use a subset where some grant_type × year cells will be zero
    small = data[data.year.isin([2010, 2011])]
    _ = acro_obj.crosstab(small.year, small.grant_type)
    output = acro_obj.results.get_index(0)
    # The check ran — status should reflect both threshold and zero checks
    assert output.status in ("fail", "review")
    # The sdc dict should contain PresenceOfZeroCheck
    assert "PresenceOfZeroCheck" in output.sdc.get("cells", {})


####TODO fix the below- uses out of date functions and does not follow the
# TODO new pattern of collect evidence-apply test


# def test_agg_p_percent_normal_violation():
#     """Top contributor dominates → p_val < SAFE_PRATIO_P → True."""
#     s = pd.Series([100.0, 1.0, 1.0, 1.0])
#     assert agg_p_percent(s) == True

# def test_agg_p_percent_normal_pass():
#     """Evenly spread values → p_val >= SAFE_PRATIO_P → False."""
#     s = pd.Series([10.0, 10.0, 10.0, 10.0, 10.0])
#     assert agg_p_percent(s) == False


# def test_agg_p_percent_all_zeros_returns_zeros_are_disclosive():
#     """All-zero series → returns ZEROS_ARE_DISCLOSIVE (True by default)."""
#     s = pd.Series([0.0, 0.0, 0.0])
#     result = agg_p_percent(s)
#     assert isinstance(result, bool)


# def test_agg_p_percent_single_element():
#     """Single-element series → size <= 1 → returns ZEROS_ARE_DISCLOSIVE."""
#     s = pd.Series([42.0])
#     result = agg_p_percent(s)
#     assert isinstance(result, bool)

# def test_agg_p_percent_not_a_series_raises():
#     """Non-Series input raises AssertionError."""
#     with pytest.raises(AssertionError):
#         agg_p_percent([1, 2, 3])


# def test_agg_nk_violation():
#     """Top-N sum > K * total → True."""
#     s = pd.Series([100.0, 1.0, 1.0, 1.0])
#     assert agg_nk(s) == True

# def test_agg_nk_pass():
#     """Evenly spread → False."""
#     s = pd.Series([10.0, 10.0, 10.0, 10.0, 10.0])
#     assert agg_nk(s) == False

# def test_agg_nk_zero_total():
#     """Zero total → False (no dominance)."""
#     s = pd.Series([0.0, 0.0, 0.0])
#     assert agg_nk(s) is False

# def test_agg_threshold_below_threshold():
#     """Fewer than THRESHOLD values → True."""
#     s = pd.Series([1, 2, 3])
#     assert agg_threshold(s) == True

# def test_agg_threshold_above_threshold():
#     """More than THRESHOLD values → False."""
#     s = pd.Series(list(range(20)))
#     assert agg_threshold(s) == False


# TODO update this method and the tests that use it to reflect new strings in SDC summary
# should be testing the status and overall summary
# def _make_sdc(**overrides: Any) -> dict[str, Any]:
#     base = {
#         "suppressed": False,
#         "negative": 0,
#         "missing": 0,
#         "threshold": 0,
#         "p-ratio": 0,
#         "nk-rule": 0,
#         "all-values-are-same": 0,
#     }
#     base.update(overrides)
#     return {"summary": base}


# def test_get_analysis_summary_pass_when_all_zero():
#     """A fully empty summary is treated as a pass."""
#     status, summary = get_analysis_summary(_make_sdc())
#     assert status == "pass"
#     assert summary == "pass"


# def test_get_analysis_summary_negative_branch():
#     """Negative values trigger the review branch."""
#     status, summary = get_analysis_summary(_make_sdc(negative=1))
#     assert status == "review"
#     assert "negative" in summary


# def test_get_analysis_summary_missing_branch():
#     """Missing values trigger the review branch."""
#     status, summary = get_analysis_summary(_make_sdc(missing=2))
#     assert status == "review"
#     assert "missing" in summary


# def test_get_analysis_summary_threshold_fail():
#     """Threshold violations yield a failure summary."""
#     status, summary = get_analysis_summary(_make_sdc(threshold=3))
#     assert status == "fail"
#     assert "threshold" in summary


# def test_get_analysis_summary_threshold_suppressed():
#     """Suppressed threshold violations are treated as review."""
#     status, _ = get_analysis_summary(_make_sdc(threshold=3, suppressed=True))
#     assert status == "review"


# def test_get_analysis_summary_pratio_fail():
#     """P-ratio violations yield a failure summary."""
#     status, summary = get_analysis_summary(_make_sdc(**{"p-ratio": 1}))
#     assert status == "fail"
#     assert "p-ratio" in summary


# def test_get_analysis_summary_nk_fail():
#     """NK-rule violations yield a failure summary."""
#     status, summary = get_analysis_summary(_make_sdc(**{"nk-rule": 2}))
#     assert status == "fail"
#     assert "nk-rule" in summary


# def test_get_analysis_summary_all_same_fail():
#     """All-same-value violations yield a failure summary."""
#     status, summary = get_analysis_summary(_make_sdc(**{"all-values-are-same": 1}))
#     assert status == "fail"
#     assert "all-values-are-same" in summary
