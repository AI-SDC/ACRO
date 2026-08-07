"""Unit tests."""

import shutil

import numpy as np
import pandas as pd
import pytest

from acro import (
    ACRO,
)
from acro.record import Records

# pylint: disable=redefined-outer-name,too-many-lines

PATH: str = "RES_PYTEST"


class SyntheticData:
    """Class for making and manipulating small synthetic data set."""

    def __init__(self) -> None:
        """Make (and save) synthetic data.

        Create a dataset with 4 independent variables and 1 dependent variable.
        The independent variables are categorical with 3 levels each.
        The distribution of these is such that it is easy to identify which subsets will have fewest records
        """
        alldata = []
        labels: list = ["A", "B", "C"]
        numrepeats: int
        for indvar1 in labels:
            for indvar2 in labels:
                for indvar3 in labels:
                    for indvar4 in labels:
                        numrepeats = 5 if (indvar1 == indvar3 == indvar4 == "C") else 10
                        for repeat in range(numrepeats):
                            alldata.append([indvar1, indvar2, indvar3, indvar4, repeat])

        self.alldata = pd.DataFrame(
            alldata, columns=["indvar1", "indvar2", "indvar3", "indvar4", "depvar"]
        )
        cat_type = pd.api.types.CategoricalDtype(categories=labels, ordered=True)
        for col in ["indvar1", "indvar2", "indvar3", "indvar4"]:
            self.alldata[col] = self.alldata[col].astype(cat_type)

    def get_all_data(self) -> pd.DataFrame:
        """Return the full dataset."""
        return self.alldata

    def get_unsafe_1d(self) -> pd.DataFrame:
        """Return a subset of the data that is unsafe for 1D pivot tables."""
        dropivar4 = self.alldata[self.alldata["indvar4"] == "C"]
        dropivar34 = dropivar4[dropivar4["indvar3"] == "C"]
        dropivar234 = dropivar34[dropivar34["indvar2"] == "C"]
        return dropivar234

    def get_safe_1d(self) -> pd.DataFrame:
        """Return a subset of the data that is safe for 1D pivot tables."""
        unsafe = self.get_unsafe_1d()
        return unsafe[unsafe["indvar1"] != "C"]

    def get_unsafe_2d(self) -> pd.DataFrame:
        """Return a subset of the data that is unsafe for 2D pivot tables."""
        dropivar4 = self.alldata[self.alldata["indvar4"] == "C"]
        dropivar34 = dropivar4[dropivar4["indvar3"] == "C"]
        return dropivar34

    def get_safe_2d(self) -> pd.DataFrame:
        """Return a subset of the data that is safe for 2D pivot tables."""
        unsafe = self.get_unsafe_2d()
        return unsafe[unsafe["indvar1"] != "C"]

    def get_unsafe_3d(self) -> pd.DataFrame:
        """Return a subset of the data that is unsafe for 3D pivot tables."""
        dropivar4 = self.alldata[self.alldata["indvar4"] == "C"]
        return dropivar4

    def get_safe_3d(self) -> pd.DataFrame:
        """Return a subset of the data that is safe for 3D pivot tables."""
        unsafe = self.get_unsafe_3d()
        return unsafe[unsafe["indvar1"] != "C"]

    def get_unsafe_4d(self) -> pd.DataFrame:
        """Return a subset of the data that is unsafe for 4D pivot tables."""
        return self.alldata

    def get_safe_4d(self) -> pd.DataFrame:
        """Return a subset of the data that is safe for 4D pivot tables."""
        return self.alldata[self.alldata["indvar1"] != "C"]

    def get_unsafe_holes_2d(self) -> pd.DataFrame:
        """Return 2D data with a zero-count cell (hole) for testing zero handling."""
        # Start with safe 2D data
        data = self.get_safe_2d()
        # Drop records where indvar1=='C' and indvar3=='C' to create a hole
        # This creates a cell that will have count=0 in crosstabs
        mask = (data["indvar1"] == "C") & (data["indvar3"] == "C")
        data = data[~mask]
        return data

    def get_unsafe_dominance_2d(self) -> pd.DataFrame:
        """Return 2D data with one cell having extreme dominance problem.

        The last record where indvar1==C, indvar2==C, indvar3==C, indvar4==C
        has depvar=1000 instead of its normal value, creating a dominance issue.
        """
        data = self.get_all_data().copy()

        # Find and modify the last record matching the pattern
        mask = (
            (data["indvar1"] == "C")
            & (data["indvar2"] == "C")
            & (data["indvar3"] == "C")
            & (data["indvar4"] == "C")
        )

        matching_indices = data[mask].index
        if len(matching_indices) > 0:
            # Set the last matching record's depvar to 1000 (extreme dominance)
            last_idx = matching_indices[-1]
            data.loc[last_idx, "depvar"] = 1000

        return data


def _assert_safe_output(result: pd.DataFrame, output) -> None:
    """Assert a safe ACRO output: pass status, no suppressed cells."""
    assert isinstance(result, pd.DataFrame)
    assert output.status == "pass", (
        f"Expected pass, got {output.status}\n{output.summary}"
    )
    assert not result.isna().any().any(), "Expected no suppressed cells in safe output"


def _assert_suppressed_output(result: pd.DataFrame, output) -> None:
    """Assert an unsafe ACRO output: cells suppressed, metadata recorded and consistent."""
    suppressed_cells = {
        (r, c)
        for r in range(result.shape[0])
        for c in range(result.shape[1])
        if pd.isna(result.iloc[r, c])
    }
    assert suppressed_cells, "Expected at least one suppressed cell"
    assert output.status == "review", (
        f"Expected review, got {output.status}\n{output.summary}"
    )
    assert "cells" in output.sdc, (
        "Expected suppression metadata under output.sdc['cells']"
    )
    cell_metadata = output.sdc["cells"]
    assert isinstance(cell_metadata, dict), (
        f"Expected output.sdc['cells'] to be a dict, got {type(cell_metadata)}"
    )
    assert cell_metadata, "Expected output.sdc['cells'] to be a non-empty dict"
    metadata_cells = set()
    for check_name, positions in cell_metadata.items():
        assert isinstance(positions, list), (
            f"Expected list for {check_name}, got {type(positions)}"
        )
        for pos in positions:
            assert isinstance(pos, tuple), f"Expected (row, col) tuple, got {pos}"
            assert len(pos) == 2, f"Expected (row, col) tuple, got {pos}"
            metadata_cells.add(pos)
    assert suppressed_cells <= metadata_cells, (
        "Suppressed cells in output not fully reflected in sdc metadata"
    )


def test_crosstab_with_spaces_in_variable_names(data, acro):
    """Test crosstab with spaces in column names (Issue #305)."""
    test_data = data.copy()
    test_data["grant type with spaces"] = test_data["grant_type"]
    test_data["year of study"] = test_data["year"]

    acro.suppress = False
    pandas_nospace_version = pd.crosstab(data["year"], data["grant_type"], margins=True)
    acro_with_spaces_version = acro.crosstab(
        test_data["year of study"], test_data["grant type with spaces"], margins=True
    )
    assert (
        acro_with_spaces_version.to_numpy() == pandas_nospace_version.to_numpy()
    ).all()
    assert acro.results.get_index(-1).status == "fail"

    acro.suppress = True
    result = acro.crosstab(
        test_data["year of study"], test_data["grant type with spaces"], margins=True
    )
    assert isinstance(result, pd.DataFrame)
    assert not result.empty
    assert acro.results.get_index(-1).status == "review"


def test_crosstab_without_suppression(data):
    """Crosstab threshold without automatic suppression."""
    acro = ACRO(suppress=False)
    _ = acro.crosstab(data.year, data.grant_type)
    output = acro.results.get_index(0)
    correct_summary: str = (
        "FrequencyTable : \n"
        " PresenceOfLinkedTableCheck: A manual review against other outputs for differencing is recommended. Variables defining table are:  ['year', 'grant_type'].\n"
        " MinimumThresholdCheck: fail - 6 cells may need suppressing.\n"
    )

    assert output.summary == correct_summary, (
        f"expected:\n{correct_summary}\n---\ngot\n{output.summary}\n---"
    )
    assert output.output[0]["R/G"].sum() == 48


def test_crosstab_with_aggfunc_mode(data):
    """Crosstab threshold without automatic suppression."""
    acro = ACRO(suppress=False)
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mode"
    )
    output = acro.results.get_index(0)
    correct_summary: str = (
        "ModeCalculation : \n"
        "PresenceOfLinkedTableCheck: A manual review against other outputs for differencing is recommended. Variables defining table are:  ['year', 'grant_type'].\n"
    )
    assert output.summary == correct_summary
    assert output.output[0]["R/G"].iat[0] == 913000


def test_crosstab_with_aggfunc_sum(data, acro):
    """Test the crosstab with two columns and aggfunc sum."""
    acro = ACRO(suppress=False)
    thetable = acro.crosstab(
        data.year,
        [data.survivor],
        values=data.inc_grants,
        aggfunc="sum",
    )
    pandastable = pd.crosstab(
        data.year,
        [data.survivor],
        values=data.inc_grants,
        aggfunc="sum",
    )
    assert thetable.equals(pandastable)


def test_crosstab_threshold(data, acro):
    """Crosstab threshold test."""
    acro.enable_suppression()
    _ = acro.crosstab(data.year, data.grant_type)

    output = acro.results.get_index(-1)

    # six cells should be suppressed
    total_nan: int = output.output[0]["R/G"].isnull().sum()
    assert total_nan == 6, f"output is\n{output.output[0]}"

    positions = output.sdc["cells"]["MinimumThresholdCheck"]
    for pos in positions:
        row, col = pos
        assert np.isnan(output.output[0].iloc[row, col])
    correct_summary: str = (
        "FrequencyTable : \n"
        " PresenceOfLinkedTableCheck: A manual review against other outputs for differencing is recommended. Variables defining table are:  ['year', 'grant_type'].\n"
        " MinimumThresholdCheck: fail - 6 cells may need suppressing.\n"
    )
    assert output.summary == correct_summary, (
        f"expected:\n{correct_summary}\n---\ngot:\n{output.summary}\n----"
    )
    assert output.status == "review"


def test_crosstab_multiple(data, acro, cleanup_path):
    """Crosstab multiple rule test."""
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mean"
    )
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(PATH)
    correct_summary: str = (
        "Mean : \n"
        "NKCheck: fail - 1 cells may need suppressing.\n"
        " PPercentCheck: fail - 2 cells may need suppressing.\n"
        " PresenceOfLinkedTableCheck: A manual review against other outputs for differencing is recommended. Variables defining table are:  ['year', 'grant_type'].\n"
        " MinimumThresholdCheck: fail - 6 cells may need suppressing.\n"
    )
    output = results.get_index(0)
    assert output.summary == correct_summary, (
        f"expected:\n{correct_summary}\n---\ngot:\n{output.summary}\n----"
    )
    shutil.rmtree(PATH)


def test_tables_negatives(data, acro, cleanup_path):
    """Pivot table and Crosstab with negative values."""
    mydata = data.copy()
    mydata.loc[0:10, "inc_grants"] = -10
    _ = acro.crosstab(
        mydata.year, mydata.grant_type, values=mydata.inc_grants, aggfunc="mean"
    )
    _ = acro.pivot_table(
        mydata, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    acro.add_exception("output_0", "Let me have it")
    acro.add_exception("output_1", "I want this")
    results: Records = acro.finalise(PATH)
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    assert output_0.status == "review"
    assert output_1.status == "review"
    assert "negative" in output_0.summary.lower()
    assert "negative" in output_1.summary.lower()
    shutil.rmtree(PATH)


def test_pivot_table_without_suppression(data):
    """Pivot table pass: correct aggregated values and no suppression."""
    acro = ACRO(suppress=False)
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "sum"]
    )
    output_0 = acro.results.get_index(0)
    assert output_0.output[0]["mean"]["inc_grants"].sum() == 36293992.0
    assert output_0.status == "pass"


def test_pivot_table_cols(data, acro):
    """Pivot table with columns test - verify actual suppression."""
    acro.pivot_table(
        data,
        index=["grant_type"],
        columns=["year"],
        values=["inc_grants"],
        aggfunc=["mean", "std"],
    )
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(PATH)
    output_0 = results.get_index(0)
    table = output_0.output[0]

    # Verify actual cells were suppressed (NaN values in result)
    suppressed_count = table.isna().sum().sum()
    assert suppressed_count > 0, (
        f"Expected cells to be suppressed, but got {suppressed_count} NaNs"
    )

    # Verify suppression reasons are documented
    assert len(output_0.sdc["cells"]) > 0, "Expected suppression reasons in SDC report"

    assert output_0.status == "review"
    shutil.rmtree(PATH, ignore_errors=True)


def test_pivot_table_with_aggfunc_sum(data, acro):
    """Test the pivot table with two columns and aggfunc sum."""
    acro = ACRO(suppress=False)
    _ = acro.pivot_table(
        data,
        index="year",
        columns=["grant_type", "survivor"],
        values="inc_grants",
        aggfunc="sum",
    )
    _ = acro.pivot_table(
        data,
        index=["grant_type", "survivor"],
        columns="year",
        values="inc_grants",
        aggfunc="sum",
    )
    acro.add_exception("output_0", "Let me have it")
    acro.add_exception("output_1", "I need this output")
    results: Records = acro.finalise(PATH)
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    # Verify both outputs have failed status (suppression applied)
    assert output_0.status == "fail"
    assert output_1.status == "fail"
    shutil.rmtree(PATH, ignore_errors=True)


def test_tables_missing(data, acro):
    """Pivot table and Crosstab with missing values."""
    acro.sdc_checks.risk_appetite["check_missing_values"] = True
    acro.suppress = False
    # lose things that create issues for low values and dominance
    mydata = data[data.grant_type != "R/G"].copy()
    mydata = mydata[mydata.year != 2010]
    mydata.loc[0:50, "inc_grants"] = np.nan

    resa = acro.crosstab(
        mydata.year, mydata.grant_type, values=mydata.inc_grants, aggfunc="mean"
    )
    resb = acro.pivot_table(
        mydata, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    results: Records = acro.finalise(PATH, interactive=False)
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    assert output_0.status == "review", (
        f"expected pass, status/summary was  {output_0.status}/\n{output_0.summary}\nres was {resa}"
    )
    assert output_1.status == "review", (
        f"expected pass, status/summary was  {output_1.status}/\n{output_1.summary}\nres was {resb}"
    )

    assert "missing" in output_0.summary, (
        f"summary is {output_0.summary} despite missing values in the data"
    )
    assert "missing" in output_1.summary, (
        f"summary is {output_1.summary} despite missing values in the data"
    )
    shutil.rmtree(PATH, ignore_errors=True)


def test_crosstab_multiple_aggregate_function_no_suppression(data, acro):
    """Crosstab with multiple agg funcs."""
    acro = ACRO(suppress=False)
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc=["mean", "std"]
    )
    output = acro.results.get_index(0)
    assert (
        "MinimumThresholdCheck" in output.summary
        or "threshold" in output.summary.lower()
    )
    assert output.status == "fail"
    assert output.output[0]["mean"]["R/G"].sum() == 97383496.0


def test_crosstab_multi_aggfunc(data):
    """Test acro crosstab with multi-aggfunc list e.g. ['mean', 'std']."""
    acro = ACRO(suppress=False)
    table = acro.crosstab(
        data["survivor"],
        data["grant_type"],
        values=data["inc_grants"],
        aggfunc=["mean", "std"],
        margins=False,
    )
    pandastable = pd.crosstab(
        data["survivor"],
        data["grant_type"],
        values=data["inc_grants"],
        aggfunc=["mean", "std"],
        margins=False,
    )
    assert isinstance(table, pd.DataFrame)
    assert table.equals(pandastable)

    acro2 = ACRO(suppress=True)
    table2 = acro2.crosstab(
        data["survivor"],
        data["grant_type"],
        values=data["inc_grants"],
        aggfunc=["mean", "std"],
        margins=True,
    )
    assert isinstance(table2, pd.DataFrame)
    assert table2.columns.nlevels == 2


def test_hierachical_aggregation(data, acro):
    """Should work with hierarchies in rows/columns."""
    acro.suppress = False
    the_data = data[data.grant_type != "G"]

    # ACRO result
    result = acro.crosstab(
        [the_data.year, the_data.survivor],
        [the_data.grant_type],
        values=the_data.inc_activity,
        aggfunc="sum",
    )

    # Pandas baseline
    expected = pd.pivot_table(
        the_data,
        index=["year", "survivor"],
        columns="grant_type",
        values="inc_activity",
        aggfunc="sum",
        dropna=False,
    )

    # Compare actual DataFrame values instead of string formatting
    pd.testing.assert_frame_equal(
        result,
        expected,
        check_dtype=False,
    )


def test_single_values_column(data, acro):
    """Pandas does not allows multiple arrays for values."""
    with pytest.raises(ValueError, match=".*specify a single values column.*"):
        _ = acro.crosstab(
            data.year,
            data.grant_type,
            values=[data.inc_activity, data.inc_activity],
            aggfunc="mean",
        )
    with pytest.raises(ValueError, match=".*specify a single values column.*"):
        _ = acro.crosstab(data.year, data.grant_type, values=None, aggfunc="mean")


def test_zeros_are_not_disclosive(data, acro, cleanup_path):
    """Test that zeros are handled as not disclosive when `zeros_are_disclosive=False`."""
    acro.sdc_checks.risk_appetite["zeros_are_disclosive"] = False
    acro.pivot_table(
        data,
        index=["grant_type"],
        columns=["year"],
        values=["inc_grants"],
        aggfunc=["mean", "std"],
    )
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(PATH)
    output_0 = results.get_index(0)
    table = output_0.output[0]

    # Verify zeros were NOT suppressed (should remain as 0, not become NaN)
    zero_count = (table == 0).sum().sum()
    assert zero_count > 0, (
        "Expected zero values to remain in output when zeros_are_disclosive=False"
    )

    assert output_0.status == "review"
    shutil.rmtree(PATH)


def test_crosstab_with_totals_without_suppression(data, acro):
    """Test the crosstab with margins is true and suppression is false."""
    acro.suppress = False
    _ = acro.crosstab(data.year, data.grant_type, margins=True)
    output = acro.results.get_index(0)
    assert output.output[0]["All"].iat[0] == 153
    # Verify table totals are computed correctly with margins
    total_rows = output.output[0].iloc[-1, 0:4].sum()
    total_cols = output.output[0].loc[2010:2015, "All"].sum()
    assert 918 == total_rows == total_cols == output.output[0]["All"].iat[6]


def test_crosstab_with_totals_with_suppression(data, acro):
    """Test the crosstab with both margins and suppression enabled."""
    _ = acro.crosstab(data.year, data.grant_type, margins=True)
    output = acro.results.get_index(0)
    table = output.output[0]

    assert "All" in table.columns
    assert output.status == "review"

    for idx in table.index[:-1]:  # Exclude 'All' row
        unsuppressed = table.loc[idx, table.columns[:-1]].dropna()
        if len(unsuppressed) > 0:
            unsup_sum = unsuppressed.sum()
            row_total = table.loc[idx, "All"]
            if not pd.isna(row_total):
                assert row_total >= unsup_sum, (
                    f"Row {idx}: total {row_total} < unsuppressed sum {unsup_sum}"
                )


def test_crosstab_with_totals_with_suppression_hierarchical(data, acro):
    """Test hierarchical crosstab margins with suppression enabled."""
    _ = acro.crosstab(
        [data.year, data.survivor], [data.grant_type, data.status], margins=True
    )
    output = acro.results.get_index(0)
    table = output.output[0]
    assert "All" in table.columns
    assert output.status == "review"

    for idx in table.index[:-1]:
        unsuppressed = table.loc[idx, table.columns[:-1]].dropna()
        if len(unsuppressed) > 0:
            unsup_sum = unsuppressed.sum()
            row_total = table.loc[idx, "All"]
            if not pd.isna(row_total):
                assert row_total >= unsup_sum, (
                    f"Hierarchical row {idx}: total {row_total} < unsuppressed sum {unsup_sum}"
                )


def test_crosstab_with_totals_with_suppression_with_mean(data, acro):
    """Test mean crosstab margins with suppression enabled."""
    _ = acro.crosstab(
        data.year,
        data.grant_type,
        values=data.inc_grants,
        aggfunc="mean",
        margins=True,
    )
    output = acro.results.get_index(0)
    table = output.output[0]

    # Verify suppression has been applied to mean aggregation table
    assert "All" in table.columns
    assert table["All"].iat[0] > 0
    assert table["All"].iat[6] > 0
    assert output.status == "review"


def test_crosstab_with_totals_and_empty_data(data, acro):
    """Test crosstab with margins on a fully disclosive subset."""
    data = data[
        (data.year == 2010)
        & (data.grant_type == "G")
        & (data.survivor == "Dead in 2015")
    ]
    _ = acro.crosstab(
        data.year,
        [data.grant_type, data.survivor],
        values=data.inc_grants,
        aggfunc="mean",
        margins=True,
    )
    assert acro.results.get_index(0).status == "review"


def test_pivot_table_no_values_raises(data):
    """Pivot tables without values raise a helpful error."""
    acro_obj = ACRO(suppress=False)
    with pytest.raises(ValueError, match="values column"):
        acro_obj.pivot_table(data, index=["grant_type"])


def test_pivot_table_multiple_values_raises(data):
    """Pivot tables with multiple values raise a helpful error."""
    acro_obj = ACRO(suppress=False)
    with pytest.raises(ValueError, match="multiple values"):
        acro_obj.pivot_table(
            data,
            index=["grant_type"],
            values=["inc_grants", "inc_activity"],
            aggfunc="mean",
        )


def test_pivot_table_aggfunc_mode(data):
    """Test pivot_table() with aggfunc='mode' using the agg_mode helper."""
    acro_obj = ACRO(suppress=False)
    result = acro_obj.pivot_table(
        data,
        index=["grant_type"],
        values=["inc_grants"],
        aggfunc="mode",
    )
    assert isinstance(result, pd.DataFrame)
    assert not result.empty


def test_crosstab_rounding_with_margins(data):
    """Crosstab with round mitigation and margins recomputes rounded margins."""
    acro_obj = ACRO()
    acro_obj.enable_rounding(base=5)
    result = acro_obj.crosstab(data.year, data.grant_type, margins=True)
    assert isinstance(result, pd.DataFrame)
    # The 'All' margin column/row should be present
    assert "All" in result.columns or "All" in result.index

    # Verify all numeric values are rounded to base 5
    numeric_data = result.select_dtypes(include=[np.number])
    for col in numeric_data.columns:
        for val in numeric_data[col].dropna():
            assert val % 5 == 0, f"Value {val} not rounded to base 5"


def test_pivot_table_rounding(data):
    """Pivot_table with mitigation='round' goes through the rounding branch."""
    acro_obj = ACRO()
    acro_obj.enable_rounding(base=5)
    result = acro_obj.pivot_table(
        data,
        index=["grant_type"],
        values=["inc_grants"],
        aggfunc=["mean"],
    )
    assert isinstance(result, pd.DataFrame)
    assert not result.empty
    # Verify that numeric values are rounded to nearest 5
    numeric_cols = result.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        for val in result[col].dropna():
            assert val % 5 == 0, f"Value {val} is not a multiple of 5"


def test_1d_crosstab_safe_no_suppression():
    """Should handle 1D crosstab with safe data."""
    syn = SyntheticData()
    df = syn.get_safe_1d()
    acro = ACRO(suppress=False)
    result = acro.crosstab(df.indvar1, df.depvar)
    _assert_safe_output(result, acro.results.get_index(0))
    assert result.ndim == 2


def test_1d_crosstab_unsafe_with_suppression():
    """Should suppress unsafe cells in 1D crosstab."""
    syn = SyntheticData()
    df = syn.get_unsafe_1d()
    acro = ACRO(suppress=True)
    result = acro.crosstab(df.indvar1, df.depvar)
    _assert_suppressed_output(result, acro.results.get_index(0))


def test_1d_pivot_table_safe_no_suppression():
    """Should handle 1D pivot table with safe data."""
    syn = SyntheticData()
    df = syn.get_safe_1d()
    acro = ACRO(suppress=False)
    result = acro.pivot_table(df, index=["indvar1"], values=["depvar"], aggfunc="mean")
    _assert_safe_output(result, acro.results.get_index(0))


def test_1d_pivot_table_unsafe_with_suppression():
    """Should suppress unsafe cells in 1D pivot table."""
    syn = SyntheticData()
    df = syn.get_unsafe_1d()
    acro = ACRO(suppress=True)
    result = acro.pivot_table(df, index=["indvar1"], values=["depvar"], aggfunc="mean")
    _assert_suppressed_output(result, acro.results.get_index(0))


def test_2d_crosstab_safe_no_suppression():
    """Should handle 2D crosstab with safe data."""
    syn = SyntheticData()
    df = syn.get_safe_2d()
    acro = ACRO(suppress=False)
    result = acro.crosstab(df.indvar1, df.indvar2, values=df.depvar, aggfunc="sum")
    _assert_safe_output(result, acro.results.get_index(0))
    assert result.shape[0] > 1, f"Expected more than one row, got {result.shape[0]}"
    assert result.shape[1] > 1, f"Expected more than one column, got {result.shape[1]}"


def test_2d_crosstab_unsafe_with_suppression():
    """Should suppress unsafe cells in 2D crosstab."""
    syn = SyntheticData()
    df = syn.get_unsafe_2d()
    acro = ACRO(suppress=True)
    result = acro.crosstab(df.indvar1, df.indvar2, values=df.depvar, aggfunc="sum")
    _assert_suppressed_output(result, acro.results.get_index(0))


def test_2d_crosstab_with_margins_safe():
    """Should compute margins correctly on 2D crosstab with safe data."""
    syn = SyntheticData()
    df = syn.get_safe_2d()
    acro = ACRO(suppress=False)
    result = acro.crosstab(df.indvar1, df.indvar2, margins=True)
    output = acro.results.get_index(0)
    assert "All" in result.columns or "All" in result.index
    assert output.status == "pass"
    for idx in result.index[:-1]:
        row_sum = result.loc[idx, result.columns[:-1]].sum()
        row_total = result.loc[idx, "All"]
        assert abs(row_sum - row_total) < 1, (
            f"Row {idx}: sum {row_sum} != total {row_total}"
        )


def test_2d_crosstab_with_margins_unsafe():
    """Should apply suppression and maintain correct margins on 2D crosstab."""
    syn = SyntheticData()
    df = syn.get_unsafe_2d()
    acro = ACRO(suppress=True)
    result = acro.crosstab(df.indvar1, df.indvar2, margins=True)
    output = acro.results.get_index(0)
    assert "All" in result.columns
    assert output.status == "review"
    for idx in result.index[:-1]:
        unsuppressed = result.loc[idx, result.columns[:-1]].dropna()
        if len(unsuppressed) > 0:
            row_total = result.loc[idx, "All"]
            if not pd.isna(row_total):
                assert row_total >= unsuppressed.sum(), (
                    f"Row {idx}: total {row_total} < unsuppressed sum {unsuppressed.sum()}"
                )


def test_2d_pivot_table_safe_no_suppression():
    """Should handle 2D pivot table with safe data."""
    syn = SyntheticData()
    df = syn.get_safe_2d()
    acro = ACRO(suppress=False)
    result = acro.pivot_table(
        df, index=["indvar1"], columns=["indvar2"], values=["depvar"], aggfunc="mean"
    )
    _assert_safe_output(result, acro.results.get_index(0))
    assert result.shape[0] > 1, f"Expected more than one row, got {result.shape[0]}"
    assert result.shape[1] > 1, f"Expected more than one column, got {result.shape[1]}"


def test_2d_pivot_table_unsafe_with_suppression():
    """Should suppress unsafe cells in 2D pivot table."""
    syn = SyntheticData()
    df = syn.get_unsafe_2d()
    acro = ACRO(suppress=True)
    result = acro.pivot_table(
        df, index=["indvar1"], columns=["indvar2"], values=["depvar"], aggfunc="mean"
    )
    _assert_suppressed_output(result, acro.results.get_index(0))


def test_3d_crosstab_safe_no_suppression():
    """Should handle 3D crosstab with safe data."""
    syn = SyntheticData()
    df = syn.get_safe_3d()
    acro = ACRO(suppress=False)
    result = acro.crosstab(
        [df.indvar1, df.indvar2], df.indvar3, values=df.depvar, aggfunc="sum"
    )
    _assert_safe_output(result, acro.results.get_index(0))
    assert isinstance(result.index, pd.MultiIndex)


def test_3d_crosstab_unsafe_with_suppression():
    """Should suppress unsafe cells in 3D crosstab."""
    syn = SyntheticData()
    df = syn.get_unsafe_3d()
    acro = ACRO(suppress=True)
    result = acro.crosstab(
        [df.indvar1, df.indvar2], df.indvar3, values=df.depvar, aggfunc="sum"
    )
    _assert_suppressed_output(result, acro.results.get_index(0))


def test_3d_pivot_table_safe_no_suppression():
    """Should handle 3D pivot table with safe data."""
    syn = SyntheticData()
    df = syn.get_safe_3d()
    acro = ACRO(suppress=False)
    result = acro.pivot_table(
        df,
        index=["indvar1", "indvar2"],
        columns=["indvar3"],
        values=["depvar"],
        aggfunc="mean",
    )
    _assert_safe_output(result, acro.results.get_index(0))
    assert isinstance(result.index, pd.MultiIndex)


def test_3d_pivot_table_unsafe_with_suppression():
    """Should suppress unsafe cells in 3D pivot table."""
    syn = SyntheticData()
    df = syn.get_unsafe_3d()
    acro = ACRO(suppress=True)
    result = acro.pivot_table(
        df,
        index=["indvar1", "indvar2"],
        columns=["indvar3"],
        values=["depvar"],
        aggfunc="mean",
    )
    _assert_suppressed_output(result, acro.results.get_index(0))


def test_4d_crosstab_safe_no_suppression():
    """Should handle 4D crosstab with safe data."""
    syn = SyntheticData()
    df = syn.get_safe_4d()
    acro = ACRO(suppress=False)
    result = acro.crosstab(
        [df.indvar1, df.indvar2],
        [df.indvar3, df.indvar4],
        values=df.depvar,
        aggfunc="sum",
    )
    _assert_safe_output(result, acro.results.get_index(0))
    assert isinstance(result.index, pd.MultiIndex)
    assert isinstance(result.columns, pd.MultiIndex)


def test_4d_crosstab_unsafe_with_suppression():
    """Should suppress the expected cells in 4D crosstab and record matching metadata."""
    syn = SyntheticData()
    df = syn.get_unsafe_4d()
    acro = ACRO(suppress=True)
    result = acro.crosstab(
        [df.indvar1, df.indvar2],
        [df.indvar3, df.indvar4],
        values=df.depvar,
        aggfunc="sum",
    )
    _assert_suppressed_output(result, acro.results.get_index(0))
    assert isinstance(result.index, pd.MultiIndex)
    assert isinstance(result.columns, pd.MultiIndex)


def test_4d_pivot_table_safe_no_suppression():
    """Should handle 4D pivot table with safe data."""
    syn = SyntheticData()
    df = syn.get_safe_4d()
    acro = ACRO(suppress=False)
    result = acro.pivot_table(
        df,
        index=["indvar1", "indvar2"],
        columns=["indvar3", "indvar4"],
        values=["depvar"],
        aggfunc="mean",
    )
    _assert_safe_output(result, acro.results.get_index(0))
    assert isinstance(result.index, pd.MultiIndex)
    assert isinstance(result.columns, pd.MultiIndex)


def test_4d_pivot_table_unsafe_with_suppression():
    """Should suppress unsafe cells in 4D pivot table."""
    syn = SyntheticData()
    df = syn.get_unsafe_4d()
    acro = ACRO(suppress=True)
    result = acro.pivot_table(
        df,
        index=["indvar1", "indvar2"],
        columns=["indvar3", "indvar4"],
        values=["depvar"],
        aggfunc="mean",
    )
    _assert_suppressed_output(result, acro.results.get_index(0))


def test_crosstab_multiindex_columns_with_tuples():
    """Should handle MultiIndex columns created by multi-aggfunc."""
    syn = SyntheticData()
    df = syn.get_safe_2d()
    acro = ACRO(suppress=False)
    result = acro.crosstab(
        df.indvar1, df.indvar2, values=df.depvar, aggfunc=["sum", "mean"]
    )
    output = acro.results.get_index(0)
    assert isinstance(result.columns, pd.MultiIndex)
    assert all(isinstance(col, tuple) for col in result.columns)
    assert len(result.columns) == len(set(result.columns))
    assert output.status == "pass"


def test_pivot_table_categorical_index():
    """Should handle CategoricalIndex in pivot table results."""
    syn = SyntheticData()
    df = syn.get_safe_2d()
    acro = ACRO(suppress=False)
    result = acro.pivot_table(
        df, index=["indvar1"], columns=["indvar2"], values=["depvar"], aggfunc="mean"
    )
    output = acro.results.get_index(0)
    assert isinstance(result, pd.DataFrame)
    assert result.shape[0] > 0
    assert output.status == "pass"


def test_pivot_table_multiindex_fillna():
    """Should handle MultiIndex columns fillna correctly."""
    syn = SyntheticData()
    df = syn.get_safe_2d()
    acro = ACRO(suppress=False)
    result = acro.pivot_table(
        df,
        index=["indvar1", "indvar2"],
        columns=["indvar2"],
        values=["depvar"],
        aggfunc=["mean", "sum"],
    )
    output = acro.results.get_index(0)
    assert isinstance(result.columns, pd.MultiIndex)
    assert isinstance(result, pd.DataFrame)
    assert output.status == "pass"


def test_zeros_not_disclosive_synthetic_holes():
    """Test zeros handling with synthetic data containing zero-count cells."""
    syn = SyntheticData()
    df = syn.get_unsafe_holes_2d()
    acro = ACRO(suppress=False)
    acro.sdc_checks.risk_appetite["zeros_are_disclosive"] = False
    result = acro.crosstab(df.indvar1, df.indvar2, values=df.depvar, aggfunc="count")
    output = acro.results.get_index(0)
    assert (result == 0).sum().sum() > 0, "Expected zero-count cells in result"
    assert output.status == "pass", (
        "Zeros should not trigger suppression when zeros_are_disclosive=False"
    )


@pytest.mark.parametrize("aggfunc", ["mean", "sum", "count", "std", "mode"])
def test_2d_crosstab_all_aggfuncs_safe(aggfunc):
    """Should handle all aggfuncs on 2D crosstab with safe data."""
    syn = SyntheticData()
    df = syn.get_safe_2d()
    acro = ACRO(suppress=False)
    result = acro.crosstab(df.indvar1, df.indvar2, values=df.depvar, aggfunc=aggfunc)
    _assert_safe_output(result, acro.results.get_index(0))


@pytest.mark.parametrize("aggfunc", ["mean", "sum", "count", "std", "mode"])
def test_2d_pivot_table_all_aggfuncs_safe(aggfunc):
    """Should handle all aggfuncs on 2D pivot table with safe data."""
    syn = SyntheticData()
    df = syn.get_safe_2d()
    acro = ACRO(suppress=False)
    result = acro.pivot_table(
        df, index=["indvar1"], columns=["indvar2"], values=["depvar"], aggfunc=aggfunc
    )
    _assert_safe_output(result, acro.results.get_index(0))


@pytest.mark.parametrize("aggfunc", ["mean", "sum", "count", "std"])
def test_2d_crosstab_all_aggfuncs_unsafe_with_suppression(aggfunc):
    """Should suppress unsafe 2D crosstab with all aggfuncs."""
    syn = SyntheticData()
    df = syn.get_unsafe_2d()
    acro = ACRO(suppress=True)
    result = acro.crosstab(df.indvar1, df.indvar2, values=df.depvar, aggfunc=aggfunc)
    _assert_suppressed_output(result, acro.results.get_index(0))


def test_dominance_problem_synthetic_crosstab():
    """Dominance check should detect extreme values in crosstab."""
    syn = SyntheticData()
    df = syn.get_unsafe_dominance_2d()
    acro = ACRO(suppress=False)
    acro.crosstab(df.indvar1, df.indvar2, values=df.depvar, aggfunc="sum")
    output = acro.results.get_index(0)
    assert output.status == "fail", f"Expected fail for dominance, got {output.status}"
    assert (
        "dominance" in output.summary.lower()
        or "concentration" in output.summary.lower()
        or "percent" in output.summary.lower()
    ), f"Expected dominance check in summary, got: {output.summary}"


def test_dominance_problem_synthetic_crosstab_with_suppression():
    """Dominance-flagged cells should be suppressed when suppression is enabled."""
    syn = SyntheticData()
    df = syn.get_unsafe_dominance_2d()
    acro = ACRO(suppress=True)
    result = acro.crosstab(df.indvar1, df.indvar2, values=df.depvar, aggfunc="sum")
    _assert_suppressed_output(result, acro.results.get_index(0))


def test_dominance_problem_synthetic_pivot_no_suppression():
    """Pivot table should detect dominance problem without suppression."""
    syn = SyntheticData()
    df = syn.get_unsafe_dominance_2d()
    acro = ACRO(suppress=False)
    acro.pivot_table(
        df, index=["indvar1"], columns=["indvar2"], values=["depvar"], aggfunc="sum"
    )
    output = acro.results.get_index(0)
    assert output.status == "fail", (
        f"Pivot table should fail on dominance, got {output.status}"
    )


def test_dominance_problem_synthetic_pivot_with_suppression():
    """Pivot table should suppress dominance-flagged cells when suppression enabled."""
    syn = SyntheticData()
    df = syn.get_unsafe_dominance_2d()
    acro = ACRO(suppress=True)
    result = acro.pivot_table(
        df, index=["indvar1"], columns=["indvar2"], values=["depvar"], aggfunc="sum"
    )
    _assert_suppressed_output(result, acro.results.get_index(0))
