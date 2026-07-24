"""Unit tests for functions in table_utils.py."""

import pandas as pd
import pytest

from acro import ACRO, table_utils
from acro.table_utils import (
    # get_analysis_summary,
    get_debugging_table_analysis,
    get_redacted_data,
    translate_args_to_newdf,
)


def test_add_backticks():
    """Test the add_backticks helper function."""
    assert table_utils.add_backticks("foo") == "foo"
    assert table_utils.add_backticks("foo bar") == "`foo bar`"
    assert table_utils.add_backticks("`foo bar`") == "`foo bar`"
    assert table_utils.add_backticks("foo bar baz") == "`foo bar baz`"


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
    """_record_table_output stores round_base in properties (line 198) and adds exception."""
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


def test_append_rounded_margins_multi_aggfunc():
    """Append_rounded_margins returns early when multiple aggfuncs."""
    df = pd.DataFrame({"a": [10, 20], "b": [30, 40]}, index=[1, 2])
    result = table_utils.append_rounded_margins(df, ["mean", "std"], "All", 5)
    pd.testing.assert_frame_equal(result, df)


def test_append_rounded_margins_hierarchical_index():
    """Append_rounded_margins returns early for hierarchical index."""
    arrays = [[1, 1, 2, 2], ["a", "b", "a", "b"]]
    idx = pd.MultiIndex.from_arrays(arrays)
    df = pd.DataFrame({"x": [1, 2, 3, 4], "y": [5, 6, 7, 8]}, index=idx)
    result = table_utils.append_rounded_margins(df, "mean", "All", 5)
    pd.testing.assert_frame_equal(result, df)


def test_append_rounded_margins_mean_aggfunc():
    """Append_rounded_margins works with mean aggfunc."""
    df = pd.DataFrame(
        {"a": [10.0, 20.0, 30.0], "b": [40.0, 50.0, 60.0]}, index=[1, 2, 3]
    )
    result = table_utils.append_rounded_margins(df, "mean", "All", 5)
    assert "All" in result.columns
    assert "All" in result.index


def test_append_rounded_margins_sum_aggfunc():
    """Append_rounded_margins works with None/count/sum aggfunc."""
    df = pd.DataFrame({"a": [10, 20, 30], "b": [40, 50, 60]}, index=[1, 2, 3])
    result = table_utils.append_rounded_margins(df, None, "All", 5)
    assert "All" in result.columns
    assert "All" in result.index
    # Grand total should be rounded to nearest 5
    grand = result.loc["All", "All"]
    assert grand % 5 == 0


def test_append_rounded_margins_unsupported_aggfunc():
    """Append_rounded_margins returns early for unsupported aggfunc."""
    df = pd.DataFrame({"a": [10, 20], "b": [30, 40]}, index=[1, 2])
    result = table_utils.append_rounded_margins(df, "max", "All", 5)
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
    from acro.sdcchecks import ChecksResults  # noqa: PLC0415

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
    from acro.sdcchecks import ChecksResults  # noqa: PLC0415

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
