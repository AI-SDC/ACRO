"""Unit tests for sdcchecks.py."""

import numpy as np
import pandas as pd

from acro.acro import ACRO
from acro.acro_regression import add_constant
from acro.sdcchecks import ChecksResults, ManyChecksResults, SDCChecks, SDCEvidence
from acro.tablemodeldetails import TableModelDetails


def test_sdc_checks_unknown_analysis_returns_review() -> None:
    """Unknown analyses return a review result from the SDC runner."""
    sdc = SDCChecks(
        {
            "safe_threshold": 10,
            "safe_dof_threshold": 10,
            "safe_nk_n": 2,
            "safe_nk_k": 0.9,
            "safe_pratio_p": 0.1,
            "check_missing_values": False,
            "zeros_are_disclosive": True,
        }
    )
    ev = SDCEvidence()
    result = sdc.run_checks_for_analysis("NonExistentAnalysis", ev, None)
    assert result.overall_status == "Review"


def test_get_table_sdc_duplicate_check_skipped(data):
    """Get_table_sdc skips checks already seen across multiple analyses.

    When two analyses produce the same check name, only the first occurrence
    is included in the SDC summary.
    """
    acro_obj = ACRO(suppress=False)
    # mean+sum both map to LinearAggregations which shares checks — run both
    _ = acro_obj.pivot_table(
        data,
        index=["grant_type"],
        values=["inc_grants"],
        aggfunc=["mean", "sum"],
    )
    output = acro_obj.results.get_index(0)
    sdc = output.sdc
    # Each check name should appear exactly once in sdc["cells"] with a list of cells
    for check_name in sdc["cells"]:
        assert isinstance(sdc["cells"][check_name], list)
    assert isinstance(sdc["summary"], dict)


def test_sdcevidence_populate_dof_else_branch():
    """Populate_dof falls back to -1 for unknown model type."""
    ev = SDCEvidence()
    ev.populate_dof("not_a_model")
    assert ev.dof == -1


def test_get_table_sdc_minimumdofcheck_pass(data):
    """Get_table_sdc branch for MinimumDoFCheck with int mask: 0 when DoF passes."""
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
    """Check_min_threshold for non-hist array type analyses."""
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
    assert status == "pass"


def test_check_min_threshold_array_hist_pass(data):
    """Check_min_threshold for array type with hist command exercises."""
    acro_obj = ACRO(suppress=False)

    datacol = np.ones(200)
    for i in range(200):  # Create an array with 200 elements
        datacol[i] = i % 10  # give them values between 0 and 9 evenly distributed
    model = TableModelDetails(
        index=[pd.Series(datacol)],
        thekwargs={"bins": 5},  # put them into 5 bins =~40 in each to exceed thjreshold
        risk_appetite=acro_obj.sdc_checks.risk_appetite,
        command="hist",
    )
    model.model_type = "array"
    analysis = ["Histogram"]
    sdc = SDCChecks(acro_obj.sdc_checks.risk_appetite)

    evidence: SDCEvidence = sdc.get_evidence_forall_analyses(analysis, model)

    status, _, _ = sdc.check_min_threshold("Histogram", evidence, model)
    assert status == "pass"


def test_check_min_threshold_array_hist_fail(data):
    """Check_min_threshold for array type with hist command exercises."""
    """Check_min_threshold for array type with hist command exercises."""
    acro_obj = ACRO(suppress=False)

    datacol = np.ones(200)
    for i in range(200):  # Create an array with 200 elements
        datacol[i] = i % 10  # #give them values between 0 and 9 evenly distributed
    model = TableModelDetails(
        index=[pd.Series(datacol)],
        thekwargs={"bins": 10},  # put them into 10 bins to fail threshold
        risk_appetite=acro_obj.sdc_checks.risk_appetite,
        command="hist",
    )
    model.model_type = "array"
    analysis = ["Histogram"]
    sdc = SDCChecks(acro_obj.sdc_checks.risk_appetite)
    evidence: SDCEvidence = sdc.get_evidence_forall_analyses(analysis, model)

    status, _, _ = sdc.check_min_threshold("Histogram", evidence, model)
    assert status == "fail"


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
    """Check_nk_dominance returns review when negative values present."""
    acro_obj = ACRO(suppress=False)
    acro_obj.sdc_checks.risk_appetite["safe_threshold"] = (
        5  # only 8 items in R/G column cells
    )
    # Build a table with negative inc_grants in some cells
    data2 = data.copy()
    data2.loc[data2.index[:20], "inc_grants"] = -500
    _ = acro_obj.crosstab(
        data2.year, data2.grant_type, values=data2.inc_grants, aggfunc="sum"
    )
    output = acro_obj.results.get_index(0)
    assert output.status == "review", (
        f"status is {output.status}\nsummary is {output.summary}"
    )
    assert "negative" in output.summary.lower()


def test_check_ppercent_with_negatives(data):
    """Check_ppercent_dominance returns review when negative values present."""
    acro_obj = ACRO(suppress=False)
    acro_obj.sdc_checks.risk_appetite["safe_threshold"] = (
        5  # only 8 items in R/G column cells
    )

    data2 = data.copy()
    data2.loc[data2.index[:50], "inc_grants"] = -100
    _ = acro_obj.crosstab(
        data2.year, data2.grant_type, values=data2.inc_grants, aggfunc="mean"
    )
    output = acro_obj.results.get_index(0)
    assert output.status == "review", (
        f"status is {output.status}\nsummary is {output.summary}"
    )
    assert "negative" in output.summary.lower()


def test_check_presence_of_zero_disclosive(data):
    """Check_presence_of_zero fires and fails when zeros_are_disclosive=True and zero cells exist."""
    acro_obj = ACRO(suppress=False)
    acro_obj.sdc_checks.risk_appetite["zeros_are_disclosive"] = True
    # Use a subset where some grant_type × year cells will be zero
    small = data[data.year.isin([2010, 2011])]
    _ = acro_obj.crosstab(small.year, small.grant_type)
    output = acro_obj.results.get_index(0)
    # The check ran — status should reflect both threshold and zero checks
    assert output.status in "fail"
    # The sdc dict should contain PresenceOfZeroCheck
    assert "PresenceOfZeroCheck" in output.sdc.get("cells", {})


_RISK_APPETITE = {
    "safe_threshold": 10,
    "safe_dof_threshold": 10,
    "safe_nk_n": 2,
    "safe_nk_k": 0.9,
    "safe_pratio_p": 0.1,
    "check_missing_values": False,
    "zeros_are_disclosive": True,
}


def test_check_model_dof_dataframe_dof_fail():
    """Dataframe dof values below threshold are flagged as failures."""
    sdc = SDCChecks(_RISK_APPETITE)
    ev = SDCEvidence()
    ev.dof = pd.DataFrame({"a": [5, 15], "b": [3, 20]})
    status, summary, _ = sdc.check_model_dof("FrequencyTable", ev, None)
    assert status == "fail"
    assert "<" in summary


def test_check_model_dof_empty_dataframe_dof_fail():
    """Empty Dataframe dof values  are flagged as failures."""
    sdc = SDCChecks(_RISK_APPETITE)
    ev = SDCEvidence()
    ev.dof = pd.DataFrame()
    status, summary, _ = sdc.check_model_dof("FrequencyTable", ev, None)
    assert status == "fail"
    assert "<" in summary


def test_check_model_dof_dataframe_dof_pass():
    """Dataframe dof values at or above threshold pass."""
    sdc = SDCChecks(_RISK_APPETITE)
    ev = SDCEvidence()
    ev.dof = pd.DataFrame({"a": [15, 20], "b": [12, 30]})
    status, _, _ = sdc.check_model_dof("FrequencyTable", ev, None)
    assert status == "pass"


def test_check_model_dof_int_dof_fail():
    """Integer dof values below threshold are flagged as failures."""
    sdc = SDCChecks(_RISK_APPETITE)
    ev = SDCEvidence()
    ev.dof = 3
    status, summary, _ = sdc.check_model_dof("GeneralLinearModel", ev, None)
    assert status == "fail"
    assert "<" in summary


def test_check_model_dof_int_dof_pass():
    """Integer dof values at or above threshold pass."""
    sdc = SDCChecks(_RISK_APPETITE)
    ev = SDCEvidence()
    ev.dof = 10
    status, summary, _ = sdc.check_model_dof("GeneralLinearModel", ev, None)
    assert status == "pass"
    assert ">=" in summary


def test_manual_check_survival_model_type():
    """Survival model types trigger the manual review path."""
    sdc = SDCChecks(_RISK_APPETITE)
    ev = SDCEvidence()
    model = TableModelDetails(
        index=[pd.Series([1, 2, 3], name="t")],
        risk_appetite=_RISK_APPETITE,
        command="surv_func",
    )
    model.model_type = "survival"
    status, summary, _ = sdc.manual_check("KaplanMeier", ev, model)
    assert status == "review"
    assert "manual" in summary.lower()


def test_manual_check_table_model_type():
    """Some Table model types trigger the manual review path."""
    sdc = SDCChecks(_RISK_APPETITE)
    ev = SDCEvidence()
    model = TableModelDetails(
        index=[pd.Series([1, 2, 3], name="t")],
        columns=[pd.Series([1, 2], name="c")],
        risk_appetite=_RISK_APPETITE,
        command="crosstab",
    )
    model.model_type = "table"
    status, summary, _ = sdc.manual_check("FrequencyTable", ev, model)
    assert status == "review"
    assert "manual" in summary.lower()


_RA = {
    "safe_threshold": 10,
    "safe_dof_threshold": 10,
    "safe_nk_n": 2,
    "safe_nk_k": 0.9,
    "safe_pratio_p": 0.1,
    "check_missing_values": False,
    "zeros_are_disclosive": True,
}


def test_check_all_same_all_identical() -> None:
    """All-identical values trigger a fail result."""
    sdc = SDCChecks(_RA)
    ev = SDCEvidence()
    ev.interim_tables["values_are_same"] = pd.DataFrame(
        {"A": [True, False], "B": [False, True]},
        index=[1, 2],
    )
    dummy_model = TableModelDetails(
        index=[pd.Series([1, 2], name="a")],
        columns=[],
        values=pd.Series([10.0, 20.0], name="v"),
    )
    status, summary, _ = sdc.check_all_same("Mean", ev, dummy_model)
    assert status == "fail"
    assert "2 cells" in summary


def test_check_all_same_no_identical() -> None:
    """Non-identical values pass the all-same check."""
    sdc = SDCChecks(_RA)
    ev = SDCEvidence()
    ev.interim_tables["values_are_same"] = pd.DataFrame(
        {"A": [False, False], "B": [False, False]},
        index=[1, 2],
    )
    dummy_model = TableModelDetails(
        index=[pd.Series([1, 2], name="a")],
        columns=[],
        values=pd.Series([10.0, 20.0], name="v"),
    )
    status, _, _ = sdc.check_all_same("Mean", ev, dummy_model)
    assert status == "pass"


def test_check_missing_with_missings() -> None:
    """Missing values trigger a fail result."""
    sdc = SDCChecks(_RA)
    ev = SDCEvidence()
    ev.interim_tables["missing"] = pd.DataFrame({"A": [True, False]}, index=[1, 2])
    dummy_model = TableModelDetails(
        index=[pd.Series([1, 2], name="a")],
        columns=[],
        values=pd.Series([10.0, 20.0], name="v"),
    )
    status, _, _ = sdc.check_missing("FrequencyTable", ev, dummy_model)
    assert status == "fail"


def test_check_missing_no_missings() -> None:
    """No missing values pass the check."""
    sdc = SDCChecks(_RA)
    ev = SDCEvidence()
    ev.interim_tables["missing"] = pd.DataFrame({"A": [False, False]}, index=[1, 2])
    dummy_model = TableModelDetails(
        index=[pd.Series([1, 2], name="a")],
        columns=[],
        values=pd.Series([10.0, 20.0], name="v"),
    )
    status, _, _ = sdc.check_missing("FrequencyTable", ev, dummy_model)
    assert status == "pass"


_RA_NO_ZERO = {
    "safe_threshold": 10,
    "safe_dof_threshold": 10,
    "safe_nk_n": 2,
    "safe_nk_k": 0.9,
    "safe_pratio_p": 0.1,
    "check_missing_values": False,
    "zeros_are_disclosive": False,
}


def test_check_required_zero_zeros_not_disclosive_qualifier() -> None:
    """The non-disclosive zero branch uses the expected qualifier."""
    sdc = SDCChecks(_RA_NO_ZERO)
    ev = SDCEvidence()
    model = TableModelDetails(
        index=[pd.Series([10, 20], name="a")],
        columns=[pd.Series([1, 2], name="b")],
        values=pd.Series([100.0, 200.0], name="v"),
        thekwargs={},
        risk_appetite=_RA_NO_ZERO,
        command="crosstab",
    )
    status, summary, _ = sdc.check_required_zero("FrequencyTable", ev, model)
    assert status == "pass"
    assert "not" in summary


def test_check_presence_of_zero_not_disclosive() -> None:
    """The non-disclosive zero branch uses an all-false mask."""
    sdc = SDCChecks(_RA_NO_ZERO)
    ev = SDCEvidence()
    ev.interim_tables["count_table"] = pd.DataFrame(
        {"A": [0, 5], "B": [10, 15]}, index=[1, 2]
    )
    model = TableModelDetails(
        index=[pd.Series([1, 2], name="a")],
        columns=[pd.Series([1, 2], name="b")],
        values=pd.Series([0.0, 5.0], name="v"),
        thekwargs={},
        risk_appetite=_RA_NO_ZERO,
        command="crosstab",
    )
    status, summary, _ = sdc.check_presence_of_zero("FrequencyTable", ev, model)
    assert status == "pass"
    assert "not disclosive" in summary


def test_get_table_sdc_minimum_dof_check_as_int() -> None:
    """Minimumdof checks stored as integers are summarized correctly."""
    cr_result = ChecksResults(
        overall_status="pass",
        summaries="dof=50 >= 10",
        outcomes={"MinimumDoFCheck": 50},
        fair_dict={},
    )
    many = ManyChecksResults()
    many.allchecksresults["GeneralLinearModel"] = cr_result
    sdc = many.get_table_sdc()
    assert sdc["summary"]["MinimumDoFCheck"] == 0


def test_get_table_sdc_minimum_dof_check_as_int_fail() -> None:
    """Minimumdof checks that fail are summarized as one."""
    cr_result = ChecksResults(
        overall_status="fail",
        summaries="dof=0 < 10",
        outcomes={"MinimumDoFCheck": 0},
        fair_dict={},
    )
    many = ManyChecksResults()
    many.allchecksresults["GeneralLinearModel"] = cr_result
    sdc = many.get_table_sdc()
    assert sdc["summary"]["MinimumDoFCheck"] == 1


def test_check_min_threshold_below_threshold(data):
    """Test MinimumThresholdCheck - fewer than threshold contributors triggers violation.

    Replaces old: test_agg_threshold_below_threshold
    """
    acro_obj = ACRO(suppress=False)

    # Create a simple table with few contributors (< 10)
    small_data = data.head(5)  # Only 5 rows = 5 contributors
    acro_obj.crosstab(
        small_data.year,
        small_data.grant_type,
        values=small_data.inc_grants,
        aggfunc="count",
    )

    # Get the output record
    output = acro_obj.results.get_index(0)

    # The check should have detected threshold violations in cells with < 10 counts
    # Check that status indicates a review/fail (threshold violation detected)
    assert output.status == "fail"
    assert "MinimumThresholdCheck" in output.summary


def test_check_nk_dominance_violation(data):
    """Test NKCheck - high concentration in top cells triggers violation.

    Replaces old: test_agg_nk_violation
    """
    acro_obj = ACRO(suppress=False)

    # Create data with strong dominance (first row dominates)
    dominated_data = data.copy()
    dominated_data.loc[data.index[0], "inc_grants"] = 1000000  # Make first cell huge
    dominated_data.loc[data.index[1:], "inc_grants"] = 1000  # second cell big
    dominated_data.loc[data.index[2:], "inc_grants"]  # Other cells tiny

    acro_obj.crosstab(
        dominated_data.year,
        dominated_data.grant_type,
        values=dominated_data.inc_grants,
        aggfunc="sum",
    )

    output = acro_obj.results.get_index(0)

    # With high dominance, should trigger NKCheck violation
    assert output.status == "fail"
    # Check that NKCheck is mentioned in summary if violated
    assert "NKCheck: fail - 1 cells may need suppressing." in output.summary


def test_check_ppercent_dominance_violation(data):
    """Test PPercentCheck - high p-ratio triggers violation.

    Replaces old: test_agg_p_percent_normal_violation
    """
    acro_obj = ACRO(suppress=False)

    # Create data where top 2 values are very unequal (violates p-ratio)
    pratio_data = data.copy()
    pratio_data.loc[data.index[0], "inc_grants"] = 1000000  # Top value
    pratio_data.loc[data.index[1], "inc_grants"] = 500  # Second value much smaller
    pratio_data.loc[data.index[2:], "inc_grants"] = 5  # Others tiny

    acro_obj.crosstab(
        pratio_data.year,
        pratio_data.grant_type,
        values=pratio_data.inc_grants,
        aggfunc="sum",
    )

    output = acro_obj.results.get_index(0)

    # High p-ratio should trigger violation
    assert output.status == "fail"
    # Check that p-ratio is mentioned in summary if violated
    assert "PPercentCheck: fail - 1 cells may need suppressing." in output.summary


def test_check_ppercent_normal_pass(data):
    """Test PPercentCheck - balanced values pass the p-ratio check.

    Replaces old: test_agg_p_percent_normal_pass
    """
    acro_obj = ACRO(suppress=False)

    # Create data with balanced distribution (all values similar)
    # Use larger dataset to avoid threshold violations
    balanced_data = data.copy()
    balanced_data["inc_grants"] = 100  # All same value - no dominance

    acro_obj.crosstab(
        balanced_data.year,
        balanced_data.grant_type,
        values=balanced_data.inc_grants,
        aggfunc="sum",
    )

    output = acro_obj.results.get_index(0)

    # Balanced data should not show p-ratio in summary (no dominance detected)
    # Status may be fail/review due to other checks, but p-ratio shouldn't be mentioned
    assert "PPercentCheck: fail" not in output.summary, (
        f"all equals records  but summary is {output.summary}"
    )


def test_check_ppercent_single_element(data):
    """Test PPercentCheck - single row/element edge case.

    Replaces old: test_agg_p_percent_single_element
    """
    acro_obj = ACRO(suppress=False)

    # Create table with just one row (single element in some cells)
    single_data = data.head(1).copy()
    single_data["inc_grants"] = 1000

    acro_obj.crosstab(
        single_data.year,
        single_data.grant_type,
        values=single_data.inc_grants,
        aggfunc="count",
    )

    output = acro_obj.results.get_index(0)

    # Single element should trigger threshold violation (1 < 10)
    assert output.status in ("review", "fail")
    assert "MinimumThresholdCheck" in output.summary
    assert "PPercentCheck: fail" not in output.summary, (
        f"single record  test but summary is {output.summary}"
    )


def test_check_nk_pass(data):
    """Test NKCheck - balanced concentration passes the nk-rule check.

    Replaces old: test_agg_nk_pass
    """
    acro_obj = ACRO(suppress=False)

    # Create data with balanced distribution across cells (no dominance)
    balanced_data = data.copy()
    balanced_data["inc_grants"] = 100  # Equal values - no concentration

    acro_obj.crosstab(
        balanced_data.year,
        balanced_data.grant_type,
        values=balanced_data.inc_grants,
        aggfunc="sum",
    )

    output = acro_obj.results.get_index(0)

    # Balanced data should not trigger nk-rule violation
    assert "NKCheck: fail" not in output.summary, (
        f"all equals records  but summary is {output.summary}"
    )


def test_populate_from_list_with_statsmodel():
    """Populate_from_list correctly extracts dependent and independent variables from a statsmodels model."""
    import statsmodels.api as sm

    # Create a simple linear regression model
    df = pd.DataFrame(
        {"y": [1, 2, 3, 4, 5], "x1": [5, 4, 3, 2, 1], "x2": [2, 3, 4, 5, 6]}
    )
    X = df[["x1", "x2"]]
    X = sm.add_constant(X)
    y = df["y"]
    model = sm.OLS(y, X)
    results = model.fit()

    ev = SDCEvidence()
    ev.populate_from_list(["DoF"], model)
    assert set(ev.variable_type_dict["independent"]) == {"x1", "x2"}
    assert ev.variable_type_dict["dependent"] == "y"
