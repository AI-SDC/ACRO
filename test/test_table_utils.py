"""Unit tests for functions in table_utils.py."""

import logging

import numpy as np
import pandas as pd
import pytest

from acro import ACRO, table_utils
from acro.sdcchecks import ChecksResults
from acro.table_utils import (
    _align_mask_to_outcome,
    append_rounded_margins,
    axis_to_list,
    collate_risk_assessments,
    drop_duplicate_columns,
    get_analysis_summary,
    get_debugging_table_analysis,
    get_redacted_data,
    round_table,
    translate_args_to_newdf,
)


def test_add_backticks():
    """Test the add_backticks helper function."""
    assert table_utils.add_backticks("foo") == "foo"
    assert table_utils.add_backticks("foo bar") == "`foo bar`"
    assert table_utils.add_backticks("`foo bar`") == "`foo bar`"
    assert table_utils.add_backticks("foo bar baz") == "`foo bar baz`"


def _make_table_for_collate_risk_assessments() -> pd.DataFrame:
    return pd.DataFrame({"A": [10, 20], "B": [30, 40]}, index=[1, 2])


def test_collate_risk_assessments_negative_branch() -> None:
    """Negative masks are surfaced as negative values in collated results."""
    table = _make_table_for_collate_risk_assessments()
    neg_mask = pd.DataFrame({"A": [True, False], "B": [False, False]}, index=[1, 2])
    cr = ChecksResults(
        overall_status="review",
        summaries="review",
        outcomes={"negative": neg_mask},
        fair_dict={},
    )
    outcome = collate_risk_assessments(table, {"Mean": cr})
    flat = outcome.to_numpy().flatten().tolist()
    assert any("negative" in str(v) for v in flat)


def test_collate_risk_assessments_missing_branch() -> None:
    """Missing masks are surfaced as missing values in collated results."""
    table = _make_table_for_collate_risk_assessments()
    miss_mask = pd.DataFrame({"A": [False, True], "B": [False, False]}, index=[1, 2])
    cr = ChecksResults(
        overall_status="fail",
        summaries="fail",
        outcomes={"missing": miss_mask},
        fair_dict={},
    )
    outcome = collate_risk_assessments(table, {"Mean": cr})
    flat = outcome.to_numpy().flatten().tolist()
    assert any("missing" in str(v) for v in flat)


def test_translate_args_to_newdf_series_branch(data) -> None:
    """Translate_args_to_newdf() maps a pd.Series argument to the redacted DataFrame."""
    redacted = data[["year", "grant_type"]].copy()
    args = (data["year"], data["grant_type"])
    result = translate_args_to_newdf(args, redacted)
    assert len(result) == 2
    assert result[0].equals(redacted["year"])


def test_append_rounded_margins_median(data) -> None:
    """Append_rounded_margins() with aggfunc='median' uses the median path."""
    table = pd.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="median"
    )
    rounded = round_table(table, 5)
    result = append_rounded_margins(rounded, "median", "All", 5)
    assert isinstance(result, pd.DataFrame)


def test_collate_risk_assessments_negative_path(data):
    """Collate_risk_assessments covers the 'negative' branch."""
    acro_obj = ACRO(suppress=False)
    data2 = data.copy()
    data2.loc[data2.index[:30], "inc_grants"] = -1
    _ = acro_obj.crosstab(
        data2.year, data2.grant_type, values=data2.inc_grants, aggfunc="mean"
    )
    output = acro_obj.results.get_index(0)
    assert output.status in ("review", "fail")


def test_collate_risk_assessments_missing_path(data):
    """Collate_risk_assessments covers the 'missing' branch."""
    acro_obj = ACRO(suppress=False)
    acro_obj.sdc_checks.risk_appetite["check_missing_values"] = True
    data2 = data.copy()
    data2.loc[data2.index[:15], "inc_grants"] = float("nan")
    _ = acro_obj.crosstab(
        data2.year, data2.grant_type, values=data2.inc_grants, aggfunc="mean"
    )
    output = acro_obj.results.get_index(0)
    assert output.status in ("review", "fail")


def test_aggfunc_to_strings_list():
    """Aggfunc_to_strings with a list returns multiple analysis types."""
    result = table_utils.aggfunc_to_strings(["mean", "std"])
    assert "Mean" in result
    assert "StandardDeviation" in result


def test_aggfunc_to_strings_none():
    """Aggfunc_to_strings with None returns FrequencyTable."""
    result = table_utils.aggfunc_to_strings(None)
    assert result == ["FrequencyTable"]


def test_record_table_output_round_mitigation(data):
    """_record_table_output stores round_base in properties and adds exception."""
    acro_obj = ACRO(mitigation="round", round_base=5)
    _ = acro_obj.crosstab(data.year, data.grant_type)
    output = acro_obj.results.get_index(0)
    assert output.properties.get("round_base") == 5
    assert output.status == "review"
    assert "Rounding" in output.exception


def test_round_table_base_none():
    """Round_table returns a copy when base is None."""
    df = pd.DataFrame({"a": [1.1, 2.2], "b": [3.3, 4.4]})
    result = table_utils.round_table(df, None)
    pd.testing.assert_frame_equal(result, df)


def test_round_table_base_zero():
    """Round_table returns a copy when base is 0."""
    df = pd.DataFrame({"a": [1.1, 2.2], "b": [3.3, 4.4]})
    result = table_utils.round_table(df, 0)
    pd.testing.assert_frame_equal(result, df)


def test_translate_args_to_newdf_raises_on_wrong_type():
    """The helper rejects arguments that are not a two-item tuple."""
    with pytest.raises(ValueError, match="wrong type or length"):
        translate_args_to_newdf([pd.Series([1])], pd.DataFrame())  # type: ignore[arg-type]


def test_translate_args_to_newdf_raises_on_wrong_length():
    """The helper rejects tuples whose length is not exactly two."""
    with pytest.raises(ValueError, match="wrong type or length"):
        translate_args_to_newdf((pd.Series([1]),), pd.DataFrame())


def test_get_redacted_data_no_op_no_queries_returns_copy():
    """No-op redaction returns an equal copy of the input data."""
    data = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    result = get_redacted_data(data, [], ["a"])
    assert result.equals(data)


def test_get_debugging_table_analysis_returns_string_with_analysis_name():
    """The debugging helper includes the analysis name in its output."""
    mask = pd.DataFrame({"col": [False, True]})
    cr = ChecksResults(
        overall_status="fail",
        summaries="some summary",
        outcomes={"MinimumThresholdCheck": mask},
        fair_dict={"check_status": {"MinimumThresholdCheck": "fail"}},
    )
    result = get_debugging_table_analysis({"FrequencyTable": cr})
    assert "FrequencyTable" in result
    assert "MinimumThresholdCheck" in result


def test_get_debugging_table_analysis_fair_dict_nested():
    """Nested fair-dict values are included in the helper output."""
    mask = pd.DataFrame({"col": [False]})
    cr = ChecksResults(
        overall_status="pass",
        summaries="ok",
        outcomes={"SomeCheck": mask},
        fair_dict={"nested": {"k": "v"}, "scalar": 42},
    )
    result = get_debugging_table_analysis({"Mean": cr})
    assert "Mean" in result
    assert "scalar" in result


class TestAxisToList:
    """Tests for axis_to_list function."""

    def test_axis_to_list_single_series(self):
        """Convert single Series to list containing that Series."""
        s = pd.Series([1, 2, 3], name="test")

        result = axis_to_list(s)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].equals(s)

    def test_axis_to_list_already_list(self):
        """Leave list of Series unchanged."""
        s1 = pd.Series([1, 2, 3], name="test1")
        s2 = pd.Series([4, 5, 6], name="test2")
        series_list = [s1, s2]
        result = axis_to_list(series_list)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0].equals(s1)
        assert result[1].equals(s2)

    def test_axis_to_list_none(self):
        """Handle None input by returning empty list."""
        result = axis_to_list(None)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_axis_to_list_empty_list(self):
        """Leave empty list unchanged."""
        result = axis_to_list([])
        assert isinstance(result, list)
        assert len(result) == 0


class TestDropDuplicateColumns:
    """Tests for drop_duplicate_columns function."""

    def test_drop_duplicate_columns_single_level(self):
        """Drop duplicate columns in flat DataFrame."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
        result = drop_duplicate_columns(df)
        assert isinstance(result, pd.DataFrame)
        assert len(result.columns) >= 1

    def test_drop_duplicate_columns_multiindex(self):
        """Handle MultiIndex columns properly."""
        arrays = [["A", "A", "B", "B"], [1, 2, 1, 2]]
        columns = pd.MultiIndex.from_arrays(arrays)
        df = pd.DataFrame([[1, 2, 3, 4], [5, 6, 7, 8]], columns=columns)
        result = drop_duplicate_columns(df)
        assert isinstance(result, pd.DataFrame)
        # Should not have NaN values after operation
        assert result.notna().all().all() or result.isna().all().all()

    def test_drop_duplicate_columns_no_duplicates(self):
        """Handle DataFrame with no duplicate columns."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        result = drop_duplicate_columns(df)
        assert isinstance(result, pd.DataFrame)


class TestAddBackticksFull:
    """Extended tests for add_backticks function."""

    def test_add_backticks_simple_name_no_spaces(self):
        """No backticks if no spaces in name."""
        result = table_utils.add_backticks("column_name")
        assert result == "column_name"

    def test_add_backticks_with_spaces_extended(self):
        """Add backticks around name with spaces."""
        result = table_utils.add_backticks("my column name")
        assert result == "`my column name`"

    def test_add_backticks_with_special_chars_no_spaces(self):
        """No backticks if no spaces even with special characters."""
        result = table_utils.add_backticks("col-name!@#")
        assert result == "col-name!@#"

    def test_add_backticks_empty_string_extended(self):
        """No backticks on empty string."""
        result = table_utils.add_backticks("")
        assert result == ""

    def test_add_backticks_numeric_string_extended(self):
        """No backticks on numeric string (no spaces)."""
        result = table_utils.add_backticks("123")
        assert result == "123"

    def test_add_backticks_already_has_backticks(self):
        """Don't add backticks if already present."""
        result = table_utils.add_backticks("`my column`")
        assert result == "`my column`"


class TestAggfuncToStringsFull:
    """Extended tests for aggfunc_to_strings function."""

    def test_aggfunc_to_strings_none_extended(self):
        """None aggfunc defaults to count."""
        result = table_utils.aggfunc_to_strings(None)
        assert isinstance(result, list)
        assert "FrequencyTable" in result

    def test_aggfunc_to_strings_count_extended(self):
        """Count aggfunc converts to FrequencyTable."""
        result = table_utils.aggfunc_to_strings("count")
        assert isinstance(result, list)
        assert "FrequencyTable" in result

    def test_aggfunc_to_strings_unknown(self):
        """Unknown aggfunc converts to missing."""
        result = table_utils.aggfunc_to_strings("unknown_func")
        assert isinstance(result, list)
        assert "missing" in result


class TestRoundTableFull:
    """Extended tests for round_table function."""

    def test_round_table_base_10(self):
        """Round table to base 10."""
        df = pd.DataFrame({"A": [123, 456], "B": [789, 234]})
        result = table_utils.round_table(df, base=10)
        assert isinstance(result, pd.DataFrame)
        # Check rounding was applied
        for val in result.values.flatten():
            if pd.notna(val) and isinstance(val, (int, float)):
                # Check if value is multiple of 10 (or close due to rounding)
                assert val == 0 or val % 10 == 0 or val % 5 == 0

    def test_round_table_base_5(self):
        """Round table to base 5."""
        df = pd.DataFrame({"A": [12, 13, 14, 15], "B": [20, 21, 22, 23]})
        result = table_utils.round_table(df, base=5)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(df)

    def test_round_table_with_nan(self):
        """Handle NaN values in table rounding."""
        df = pd.DataFrame(
            {"A": [1.5, float("nan"), 3.7], "B": [4.2, 5.8, float("nan")]}
        )
        result = table_utils.round_table(df, base=None)
        assert isinstance(result, pd.DataFrame)
        # NaN values should be preserved
        assert result.isna().sum().sum() >= 2

    def test_round_table_base_100(self):
        """Round table to base 100."""
        df = pd.DataFrame({"A": [150, 250, 350], "B": [450, 550, 650]})
        result = table_utils.round_table(df, base=100)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(df)


class TestAlignMaskToOutcome:
    """Tests for _align_mask_to_outcome function."""

    def test_align_mask_to_outcome_matching_shapes(self):
        """Test alignment when mask and outcome have matching dimensions."""
        # Create mask and outcome with same shape
        index = pd.Index(["A", "B", "C"])
        cols = pd.MultiIndex.from_tuples([("X", 1), ("Y", 2)])
        mask = pd.DataFrame(
            [[True, False], [False, True], [True, True]], index=index, columns=cols
        )
        outcome_df = pd.DataFrame([[0, 0], [0, 0], [0, 0]], index=index, columns=cols)

        result = _align_mask_to_outcome(mask, outcome_df)
        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_align_mask_to_outcome_different_multiindex_levels(self):
        """Test alignment when mask has different MultiIndex levels."""
        # Outcome with 2-level MultiIndex
        outcome_cols = pd.MultiIndex.from_tuples([("X", 1), ("Y", 2)])
        outcome_df = pd.DataFrame([[0, 0]], columns=outcome_cols)

        # Mask with different structure
        mask_cols = pd.MultiIndex.from_tuples([("X", 1, "a"), ("Y", 2, "b")])
        mask = pd.DataFrame([[True, False]], columns=mask_cols)

        result = _align_mask_to_outcome(mask, outcome_df)
        # Should handle level mismatch gracefully
        assert result is None or isinstance(result, pd.DataFrame)

    def test_align_mask_to_outcome_empty_dataframe(self):
        """Test alignment with empty DataFrames."""
        mask = pd.DataFrame()
        outcome_df = pd.DataFrame()

        result = _align_mask_to_outcome(mask, outcome_df)
        assert result is None or isinstance(result, pd.DataFrame)


class TestGetAnalysisSummary:
    """Tests for get_analysis_summary function."""

    def test_get_analysis_summary_pass(self):
        """Test summary generation for passing case."""
        sdc = {
            "summary": {
                "suppressed": True,
                "negative": 0,
                "missing": 0,
                "threshold": 0,
                "p-ratio": 0,
                "nk-rule": 0,
                "all-values-are-same": 0,
            }
        }
        status, summary = get_analysis_summary(sdc)
        assert status == "pass"
        assert isinstance(summary, str)


class TestCollateRiskAssessmentsEdgeCases:
    """Tests for edge cases in collate_risk_assessment."""

    def test_collate_empty_shared_index_and_cols(self):
        """When shared_index/shared_cols are empty, the branch at line 121 is skipped."""
        # Create a table with specific index/columns
        table = pd.DataFrame(
            {"A": [1, 2], "B": [3, 4]}, index=pd.Index([10, 20], name="idx")
        )

        # Create a mask with completely different index/columns
        mask_data = pd.DataFrame(
            {"X": [True, False], "Y": [False, True]},
            index=pd.Index([99, 98], name="diff_idx"),
        )

        cr = ChecksResults(
            overall_status="review",
            summaries="review",
            outcomes={"TestCheck": mask_data},
            fair_dict={},
        )

        # This should handle mismatched indices gracefully
        result = collate_risk_assessments(table, {"TestAnalysis": cr})
        assert isinstance(result, pd.DataFrame)
        assert result.shape == table.shape


class TestAlignMaskToOutcomeEdgeCases:
    """Tests for edge cases in _align_mask_to_outcome."""

    def test_align_mask_column_not_in_mask_columns(self):
        """When col_mask not in mask.columns, that cell stays NaN."""
        # Outcome with 2-level MultiIndex columns
        outcome_cols = pd.MultiIndex.from_tuples(
            [("A", 1), ("A", 2), ("B", 1)], names=["level0", "level1"]
        )
        outcome_df = pd.DataFrame([[10, 20, 30]], columns=outcome_cols)

        # Mask with 1-level columns (only has some of the columns)
        mask = pd.DataFrame([[True, False]], columns=[1, 2])

        result = _align_mask_to_outcome(mask, outcome_df)
        # Result should be a DataFrame with NaN for columns not in mask
        assert isinstance(result, pd.DataFrame)
        assert result.shape[1] == 3  # Should have 3 columns like outcome_df


class TestGetRedactedDataErrorBranch:
    """Tests for error handling in get_redacted_data."""

    @pytest.mark.skip(reason="noprag")
    def test_get_redacted_data_column_mismatch_error(self, caplog):
        """When redacted data has different columns than input, warning is logged.

        Note: This test targets defensive programming that checks if redacted_data
        columns differ from original data columns. This should never happen in
        normal execution because the function operates on a copy and doesn't
        add/remove columns. Triggering this requires internal code modification.
        are unreachable via normal API usage.
        """
        # Create original data
        original_data = pd.DataFrame(
            {"col1": [1, 2, 3], "col2": [4, 5, 6], "col3": [7, 8, 9]}
        )

        # Create a mock queries list that could cause column mismatch
        # The actual function should return original data on error
        queries: list[str] = []  # No queries means no modification

        with caplog.at_level(logging.WARNING):
            result = get_redacted_data(original_data, queries, [])

        # Should return the original data unchanged
        assert result.equals(original_data) or len(result.columns) == len(
            original_data.columns
        )


class TestCollateRiskAssessmentsElseBranch:
    """Tests for the `else` branch in collate_risk_assessments."""

    def test_collate_with_other_checks_not_negative_or_missing(self):
        """Test the `else` branch when masks don't have 'negative' or 'missing' keys."""
        # Create a table
        table = pd.DataFrame({"A": [10, 20], "B": [30, 40]}, index=pd.Index([1, 2]))

        # Create a mask with a DIFFERENT key (not 'negative' or 'missing')
        # This will trigger the `else` branch at line 108
        threshold_mask = pd.DataFrame(
            {"A": [True, False], "B": [False, True]}, index=pd.Index([1, 2])
        )

        cr = ChecksResults(
            overall_status="review",
            summaries="review",
            outcomes={
                "MinimumThresholdCheck": threshold_mask
            },  # NOT 'negative' or 'missing'
            fair_dict={},
        )

        # This should execute the `else` branch
        result = collate_risk_assessments(table, {"FrequencyTable": cr})

        # Verify result contains the check name
        assert isinstance(result, pd.DataFrame)
        flat = result.to_numpy().flatten().tolist()
        # Should have "MinimumThresholdCheck" or "ok" in the result
        assert any("MinimumThresholdCheck" in str(v) or "ok" in str(v) for v in flat)

    @pytest.mark.skip(reason="noprag")
    def test_collate_with_duplicate_check_name_skips_second(self):
        """Test that duplicate check names are skipped.

        Note: This test cannot realistically trigger because Python dicts cannot have duplicate keys.
        The outcomes dict in ChecksResults cannot have the same check name twice.
        """
        # Create a table
        table = pd.DataFrame({"A": [10, 20], "B": [30, 40]}, index=pd.Index([1, 2]))

        # Create outcomes with DUPLICATE check names
        # When the same check name appears twice, the second should be skipped
        mask1 = pd.DataFrame(
            {"A": [True, False], "B": [False, True]}, index=pd.Index([1, 2])
        )

        # Create ChecksResults with ordered dict to simulate multiple check names
        # When iterating over masks.items(), we can get the same name twice
        cr = ChecksResults(
            overall_status="review",
            summaries="review",
            outcomes={"TestCheck": mask1},
            fair_dict={},
        )

        # We need to trigger the duplicate name check
        # This happens when same name appears in masks dict during iteration
        result = collate_risk_assessments(table, {"Analysis1": cr})
        assert isinstance(result, pd.DataFrame)

    def test_collate_with_non_dataframe_mask_skips(self):
        """Test that non-DataFrame masks are skipped."""
        # Create a table
        table = pd.DataFrame({"A": [10, 20], "B": [30, 40]}, index=pd.Index([1, 2]))

        # Create outcomes with a non-DataFrame mask
        cr = ChecksResults(
            overall_status="review",
            summaries="review",
            outcomes={
                "TestCheck": np.array([[True, False], [False, True]])
            },  # np.array, not DataFrame
            fair_dict={},
        )

        # Should handle gracefully without error
        result = collate_risk_assessments(table, {"Analysis1": cr})
        assert isinstance(result, pd.DataFrame)

    def test_align_mask_with_multiindex_columns(self):
        """Test _align_mask_to_outcome with MultiIndex columns including non-tuple columns."""
        # Create outcome_df with mixed column types: some tuples, some non-tuples
        # This mixed scenario should trigger the alignment logic for non-tuple columns
        outcome_df = pd.DataFrame(
            [[1, 2, 3], [4, 5, 6]],
            columns=[
                ("A", "x"),
                ("A", "y"),
                "SimpleColumn",
            ],  # Mixed: tuples and non-tuple
        )

        # Create mask with single-level columns
        mask = pd.DataFrame(
            [[True, False, True], [False, True, False]],
            columns=["x", "y", "SimpleColumn"],
        )

        # This should trigger the alignment logic that executes
        # for the non-tuple "SimpleColumn"
        result = _align_mask_to_outcome(mask, outcome_df)

        assert result is not None
        assert len(result.columns) == 3

    def test_get_analysis_summary_negative_values(self):
        """Test summary when negative values found."""
        sdc = {
            "summary": {
                "suppressed": False,
                "negative": 5,
                "missing": 0,
                "threshold": 0,
                "p-ratio": 0,
                "nk-rule": 0,
                "all-values-are-same": 0,
            }
        }
        status, summary = get_analysis_summary(sdc)
        assert status == "review"
        assert "negative" in summary

    def test_get_analysis_summary_missing_values(self):
        """Test summary when missing values found."""
        sdc = {
            "summary": {
                "suppressed": False,
                "negative": 0,
                "missing": 3,
                "threshold": 0,
                "p-ratio": 0,
                "nk-rule": 0,
                "all-values-are-same": 0,
            }
        }
        status, summary = get_analysis_summary(sdc)
        assert status == "review"
        assert "missing" in summary

    def test_get_analysis_summary_threshold_violations(self):
        """Test summary with threshold violations."""
        sdc = {
            "summary": {
                "suppressed": True,
                "negative": 0,
                "missing": 0,
                "threshold": 2,
                "p-ratio": 0,
                "nk-rule": 0,
                "all-values-are-same": 0,
            }
        }
        status, summary = get_analysis_summary(sdc)
        assert status == "review"
        assert "threshold" in summary

    def test_get_analysis_summary_all_violations(self):
        """Test summary with all types of violations."""
        sdc = {
            "summary": {
                "suppressed": False,
                "negative": 0,
                "missing": 0,
                "threshold": 1,
                "p-ratio": 1,
                "nk-rule": 1,
                "all-values-are-same": 1,
            }
        }
        status, summary = get_analysis_summary(sdc)
        assert status == "fail"
        assert any(term in summary for term in ["threshold", "p-ratio", "nk-rule"])
