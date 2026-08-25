"""Unit tests."""

import shutil

import numpy as np
import pandas as pd
import pytest
from scipy.stats import mode as statsmode

from acro import (
    ACRO,
)
from acro.record import Record, Records

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
                        numrepeats = 5 if (indvar1 == indvar3 == indvar4 == "C") else 11
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
        safe = unsafe[unsafe["indvar1"] != "C"].copy()
        return safe

    def get_unsafe_2d(self) -> pd.DataFrame:
        """Return a subset of the data that is unsafe for 2D pivot tables."""
        dropivar4 = self.alldata[self.alldata["indvar4"] == "C"]
        dropivar34 = dropivar4[dropivar4["indvar3"] == "C"]
        return dropivar34

    def get_safe_2d(self) -> pd.DataFrame:
        """Return a subset of the data that is safe for 2D pivot tables."""
        unsafe = self.get_unsafe_2d()
        safe = unsafe[unsafe["indvar1"] != "C"].copy()
        return safe

    def get_safe_2d_with_duplicates(self) -> pd.DataFrame:
        """Return a safe 2d dataset with duplicates so mode is deterministic."""
        safe_dups = self.get_safe_2d()
        safe_dups = safe_dups.replace({8: 9})
        return safe_dups

    def get_unsafe_3d(self) -> pd.DataFrame:
        """Return a subset of the data that is unsafe for 3D pivot tables."""
        dropivar4 = self.alldata[self.alldata["indvar4"] == "C"]
        return dropivar4

    def get_safe_3d(self) -> pd.DataFrame:
        """Return a subset of the data that is safe for 3D pivot tables."""
        unsafe = self.get_unsafe_3d()
        mask = unsafe[(unsafe["indvar1"] == "C") & (unsafe["indvar3"] == "C")].index
        safe = unsafe.drop(mask)
        return safe

    def get_unsafe_4d(self) -> pd.DataFrame:
        """Return a subset of the data that is unsafe for 4D pivot tables."""
        return self.alldata

    def get_safe_4d(self) -> pd.DataFrame:
        """Return a subset of the data that is safe for 4D pivot tables."""
        unsafe = self.get_unsafe_4d().copy()
        mask = unsafe[
            (unsafe["indvar1"] == "C")
            & (unsafe["indvar3"] == "C")
            & (unsafe["indvar4"] == "C")
        ].index
        safe = unsafe.drop(mask)
        return safe

    def get_unsafe_holes_2d(self) -> pd.DataFrame:
        """Return 2D data with a zero-sum cell for testing zero handling.

        Cell (A, A) has depvar values that sum to 0 but still has enough
        observations to pass the minimum threshold check.
        """
        data = self.get_safe_2d().copy()
        # Set depvar to 0 for cell (A, A) so the sum is 0
        mask = (data["indvar1"] == "A") & (data["indvar2"] == "A")
        data.loc[mask, "depvar"] = 0
        return data

    def get_unsafe_dominance_2d(self) -> pd.DataFrame:
        """Return 2D data with one cell having extreme dominance problem.

        The last record where indvar1==C, indvar2==C, indvar3==C, indvar4==C
        has depvar=10000 instead of its normal value, creating a dominance issue.
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
            # Set the last matching record's depvar to 10000 (extreme dominance)
            last_idx = matching_indices[-1]
            data.loc[last_idx, "depvar"] = 10000

        return data


@pytest.fixture
def synthetic_data() -> SyntheticData:
    """Fixture providing a SyntheticData instance."""
    return SyntheticData()


@pytest.fixture
def synthetic_1d_safe(synthetic_data: SyntheticData) -> pd.DataFrame:
    """Fixture providing 1D safe synthetic dataset."""
    return synthetic_data.get_safe_1d()


@pytest.fixture
def synthetic_1d_unsafe(synthetic_data: SyntheticData) -> pd.DataFrame:
    """Fixture providing 1D unsafe synthetic dataset."""
    return synthetic_data.get_unsafe_1d()


@pytest.fixture
def synthetic_2d_safe(synthetic_data: SyntheticData) -> pd.DataFrame:
    """Fixture providing 2D safe synthetic dataset."""
    return synthetic_data.get_safe_2d()


@pytest.fixture
def synthetic_2d_unsafe(synthetic_data: SyntheticData) -> pd.DataFrame:
    """Fixture providing 2D unsafe synthetic dataset."""
    return synthetic_data.get_unsafe_2d()


@pytest.fixture
def synthetic_2d_safe_duplicates(synthetic_data: SyntheticData) -> pd.DataFrame:
    """Fixture providing 2D safe synthetic dataset with duplicates."""
    return synthetic_data.get_safe_2d_with_duplicates()


@pytest.fixture
def synthetic_3d_safe(synthetic_data: SyntheticData) -> pd.DataFrame:
    """Fixture providing 3D safe synthetic dataset."""
    return synthetic_data.get_safe_3d()


@pytest.fixture
def synthetic_3d_unsafe(synthetic_data: SyntheticData) -> pd.DataFrame:
    """Fixture providing 3D unsafe synthetic dataset."""
    return synthetic_data.get_unsafe_3d()


@pytest.fixture
def synthetic_4d_safe(synthetic_data: SyntheticData) -> pd.DataFrame:
    """Fixture providing 4D safe synthetic dataset."""
    return synthetic_data.get_safe_4d()


@pytest.fixture
def synthetic_4d_unsafe(synthetic_data: SyntheticData) -> pd.DataFrame:
    """Fixture providing 4D unsafe synthetic dataset."""
    return synthetic_data.get_unsafe_4d()


@pytest.fixture
def synthetic_2d_unsafe_holes(synthetic_data: SyntheticData) -> pd.DataFrame:
    """Fixture providing 2D synthetic dataset with zero holes."""
    return synthetic_data.get_unsafe_holes_2d()


@pytest.fixture
def synthetic_2d_unsafe_dominance(synthetic_data: SyntheticData) -> pd.DataFrame:
    """Fixture providing 2D synthetic dataset with dominance issue."""
    return synthetic_data.get_unsafe_dominance_2d()


def _assert_table_cells_match(a: pd.DataFrame, b: pd.DataFrame) -> None:
    """Test whether two dataframes that may contain NaNs are the same elementwise."""
    assert np.array_equal(a.to_numpy(), b.to_numpy(), equal_nan=True), (
        f"no match\n{a}\nvs\n{b}"
    )


def _assert_safe_output(result: pd.DataFrame, output: Record) -> None:
    """Assert a safe ACRO output: pass status, no suppressed cells."""
    assert isinstance(result, pd.DataFrame)
    assert output.status == "pass", (
        f"Expected pass, got {output.status}\n{output.summary}"
    )
    assert not result.isna().any().any(), "Expected no suppressed cells in safe output"


def _assert_correctnum_flagged_cells(output: Record, expected: int) -> None:
    """Assert Acro has detected the correct number of disclosive cells."""
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
            assert isinstance(pos, (tuple, list)), f"Expected (row, col), got {pos}"
            assert len(pos) == 2, f"Expected (row, col), got {pos}"
            metadata_cells.add((pos[0], pos[1]))
    assert len(metadata_cells) == expected, (
        f"Expected {expected} flagged cells in metadata"
    )


def _assert_unsafe_output(output: Record, expected_unsafe: int = 0) -> None:
    """Assert a unsafe ACRO output: fail status, disclosive cells identified."""
    assert output.status == "fail", (
        f"Expected fail, got {output.status}\n{output.summary}"
    )
    if expected_unsafe > 0:
        _assert_correctnum_flagged_cells(output, expected_unsafe)
    assert "may need suppressing" in output.summary


def _assert_suppressed_output(output: Record, expected_unsafe: int = 0) -> None:
    """Assert an unsafe ACRO output: metadata recorded and status is review."""
    assert output.status == "review", (
        f"Expected review, got {output.status}\n{output.summary}"
    )
    if expected_unsafe > 0:
        _assert_correctnum_flagged_cells(output, expected_unsafe)
    assert "may need suppressing" in output.summary


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


## could be incorproated into one of the synthertic data tests (e.g. the dominance one)
## then delete this test
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


## not needed?
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


# not needed?
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


# not needed?
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
        unsuppressed = table.iloc[table.index.get_loc(idx), :-1].dropna()
        if len(unsuppressed) > 0:
            unsup_sum = unsuppressed.sum()
            row_total = table.loc[idx, "All"]
            if not pd.isna(row_total):
                assert row_total >= unsup_sum, (
                    f"Hierarchical row {idx}: total {row_total} < unsuppressed sum {unsup_sum}"
                )


# not needed?
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


# not needed?
def test_crosstab_with_totals_and_empty_data(data, acro):
    """Test crosstab with margins on a fully disclosive subset."""
    acro = ACRO(suppress=True)
    sub_data = data[
        (data.year == 2010)
        & (data.grant_type == "G")
        & (data.survivor == "Dead in 2015")
    ]
    result = acro.crosstab(
        sub_data.year,
        [sub_data.grant_type, sub_data.survivor],
        values=sub_data.inc_grants,
        aggfunc="mean",
        margins=True,
    )
    output = acro.results.get_index(0)
    assert isinstance(result, pd.DataFrame)
    assert not result.empty

    # can;t be suppressed because empty anyway
    assert output.status == "review"
    assert "All" in result.index
    assert ("All", "") in result.columns or "All" in result.columns.get_level_values(0)


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


# not needed?
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
    output = acro_obj.results.get_index(0)
    assert output.status == "pass"
    assert "ModeCalculation" in output.summary
    for grant_type_val, group in data.groupby("grant_type", observed=False):
        modes = group["inc_grants"].mode().values
        actual_mode = result.loc[grant_type_val, "inc_grants"]
        assert actual_mode in modes, (
            f"Expected actual mode {actual_mode} to be in modes {modes} for {grant_type_val}"
        )


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


# 1D
def test_1d_pivot_tables(synthetic_1d_safe, synthetic_1d_unsafe):
    """Check acro correctly identifies and removes records in disclosive cells in 1d table."""
    # 1d array of A,B,C so only C should be disclosive
    expected_unsafe = 1
    safe = synthetic_1d_safe
    unsafe = synthetic_1d_unsafe

    acro = ACRO()
    # unsafe outputs-no suppression
    acro.disable_suppression()
    unsafe_pivot = pd.pivot_table(
        data=unsafe,
        index="indvar1",
        columns=[],
        values="depvar",
        aggfunc="count",
        margins=True,
    )
    unsup_acro_pivot = acro.pivot_table(
        data=unsafe,
        index="indvar1",
        columns=[],
        values="depvar",
        aggfunc="count",
        margins=True,
    )
    output = acro.results.get_index(-1)

    assert unsafe_pivot.equals(unsup_acro_pivot)
    _assert_unsafe_output(output, expected_unsafe=expected_unsafe)

    # suppressed outputs on unsafedata
    acro.enable_suppression()
    safe_pivot = pd.pivot_table(
        data=safe,
        index="indvar1",
        columns=[],
        values="depvar",
        aggfunc="count",
        margins=True,
    )
    suppressed_pivot = acro.pivot_table(
        data=unsafe,
        index="indvar1",
        columns=[],
        values="depvar",
        aggfunc="count",
        margins=True,
    )
    output = acro.results.get_index(-1)

    _assert_table_cells_match(
        safe_pivot.replace({0: np.nan}), suppressed_pivot
    )  # native pandas will produce zeros
    assert (safe_pivot == 0).astype(int).sum().sum() == expected_unsafe
    _assert_suppressed_output(output, expected_unsafe=expected_unsafe)


# 2D
def test_2d_tables(synthetic_2d_unsafe, synthetic_2d_safe):
    """Check acro behaviour for 2d crosstab/pivot tables.

    Run  with margins==True so we know those are being correctly calculated.
    """
    # 2d array of A,B,C three cells fail min threshold check
    expected_unsafe = 3
    safe = synthetic_2d_safe
    unsafe = synthetic_2d_unsafe

    # pivot tables
    acro = ACRO()
    acro.disable_suppression()
    unsafe_pivot = pd.pivot_table(
        data=unsafe,
        index="indvar1",
        columns="indvar2",
        values="depvar",
        aggfunc="count",
        margins=True,
    )
    unsup_acro_pivot = acro.pivot_table(
        data=unsafe,
        index="indvar1",
        columns="indvar2",
        values="depvar",
        aggfunc="count",
        margins=True,
    )
    output = acro.results.get_index(-1)
    assert unsafe_pivot.equals(unsup_acro_pivot)
    _assert_unsafe_output(output, expected_unsafe=expected_unsafe)

    acro.enable_suppression()
    safe_pivot = pd.pivot_table(
        data=safe,
        index="indvar1",
        columns="indvar2",
        values="depvar",
        aggfunc="count",
        margins=True,
    )
    suppressed_pivot = acro.pivot_table(
        data=unsafe,
        index="indvar1",
        columns="indvar2",
        values="depvar",
        aggfunc="count",
        margins=True,
    )
    output = acro.results.get_index(-1)

    _assert_table_cells_match(
        safe_pivot.replace({0: np.nan}), suppressed_pivot
    )  # native pandas will produce zeros
    assert (safe_pivot == 0).sum().sum() == expected_unsafe
    _assert_suppressed_output(output, expected_unsafe=expected_unsafe)

    # crosstabs
    acro = ACRO()
    acro.disable_suppression()

    unsafe_crosstab = pd.crosstab(
        index=unsafe["indvar1"],
        columns=unsafe["indvar2"],
        values=unsafe["depvar"],
        aggfunc="count",
        margins=True,
    )
    unsup_acro_crosstab = acro.crosstab(
        index=unsafe["indvar1"],
        columns=unsafe["indvar2"],
        values=unsafe["depvar"],
        aggfunc="count",
        margins=True,
    )
    output = acro.results.get_index(-1)
    assert unsafe_crosstab.equals(unsup_acro_crosstab)
    _assert_unsafe_output(output, expected_unsafe=expected_unsafe)

    acro.enable_suppression()
    safe_crosstab = pd.crosstab(
        index=safe["indvar1"],
        columns=safe["indvar2"],
        values=safe["depvar"],
        aggfunc="count",
        margins=True,
    )
    suppressed_crosstab = acro.crosstab(
        index=unsafe["indvar1"],
        columns=unsafe["indvar2"],
        values=unsafe["depvar"],
        aggfunc="count",
        margins=True,
    )
    output = acro.results.get_index(-1)

    _assert_table_cells_match(
        safe_crosstab.replace({0: np.nan}), suppressed_crosstab
    )  # native pandas will produce zeros
    assert (safe_crosstab == 0).sum().sum() == expected_unsafe
    _assert_suppressed_output(output, expected_unsafe=expected_unsafe)


# 2D checking odd aspects of crosstab behaviour
def test_2d_crosstab_oddments(synthetic_2d_unsafe):
    """Check acro behaviour for different data formats."""
    unsafe = synthetic_2d_unsafe
    unsafe["myindvar1"] = unsafe["indvar1"]
    unsafe["myindvar2"] = unsafe["indvar2"]
    unsafe["mydepvar"] = unsafe["depvar"]

    acro = ACRO()
    acro.disable_suppression()

    series_crosstab = acro.crosstab(
        index=unsafe["myindvar1"],
        columns=unsafe["myindvar2"],
        values=unsafe["mydepvar"],
        aggfunc="count",
        margins=True,
    )
    rownames = ["myindvar1"]
    colnames = ["myindvar2"]
    # test datahandling if everything is in a numpy array
    numpy_crosstab = acro.crosstab(
        index=unsafe["indvar1"].copy().to_numpy(),
        columns=unsafe["indvar2"].copy().to_numpy(),
        values=unsafe["depvar"].copy().to_numpy(),
        rownames=rownames,
        colnames=colnames,
        aggfunc="count",
        margins=True,
    )
    assert series_crosstab.equals(numpy_crosstab)
    # test datahandling if everything is as lists
    list_crosstab = acro.crosstab(
        index=unsafe["indvar1"].tolist(),
        columns=unsafe["indvar2"].tolist(),
        values=unsafe["depvar"].tolist(),
        rownames=rownames,
        colnames=colnames,
        aggfunc="count",
        margins=True,
    )
    assert series_crosstab.equals(list_crosstab), (
        f"expected:\n{series_crosstab}\ngot\n{list_crosstab}"
    )


# 3D
def test_3d_tables(synthetic_3d_unsafe, synthetic_3d_safe):
    """Check acro behaviour for 3d crosstab/pivot tables.

    Run  with margins==True so we know those are being correctly calculated
    """
    # 3d array of A,B,C three cells fail min threshold check
    expected_unsafe = 3
    safe = synthetic_3d_safe
    unsafe = synthetic_3d_unsafe

    # pivot tables
    acro = ACRO()
    acro.disable_suppression()
    unsafe_pivot = pd.pivot_table(
        data=unsafe,
        index=["indvar1", "indvar2"],
        columns="indvar3",
        values="depvar",
        aggfunc="count",
        margins=True,
    )
    unsup_acro_pivot = acro.pivot_table(
        data=unsafe,
        index=["indvar1", "indvar2"],
        columns="indvar3",
        values="depvar",
        aggfunc="count",
        margins=True,
    )
    output = acro.results.get_index(-1)
    assert unsafe_pivot.equals(unsup_acro_pivot)
    _assert_unsafe_output(output, expected_unsafe=expected_unsafe)

    acro.enable_suppression()
    safe_pivot = pd.pivot_table(
        data=safe,
        index=["indvar1", "indvar2"],
        columns="indvar3",
        values="depvar",
        aggfunc="count",
        margins=True,
    )
    suppressed_pivot = acro.pivot_table(
        data=unsafe,
        index=["indvar1", "indvar2"],
        columns="indvar3",
        values="depvar",
        aggfunc="count",
        margins=True,
    )
    output = acro.results.get_index(-1)

    _assert_table_cells_match(
        safe_pivot.replace({0: np.nan}), suppressed_pivot
    )  # native pandas will produce zeros
    assert (safe_pivot == 0).sum().sum() == expected_unsafe
    _assert_suppressed_output(output, expected_unsafe=expected_unsafe)

    # crosstabs
    acro = ACRO()
    acro.disable_suppression()

    unsafe_crosstab = pd.crosstab(
        index=[unsafe["indvar1"], unsafe["indvar2"]],
        columns=unsafe["indvar3"],
        values=unsafe["depvar"],
        aggfunc="count",
        margins=True,
    )
    unsup_acro_crosstab = acro.crosstab(
        index=[unsafe["indvar1"], unsafe["indvar2"]],
        columns=unsafe["indvar3"],
        values=unsafe["depvar"],
        aggfunc="count",
        margins=True,
    )
    output = acro.results.get_index(-1)
    assert unsafe_crosstab.equals(unsup_acro_crosstab)
    _assert_unsafe_output(output, expected_unsafe=expected_unsafe)

    acro.enable_suppression()
    safe_crosstab = pd.crosstab(
        index=[safe["indvar1"], safe["indvar2"]],
        columns=safe["indvar3"],
        values=safe["depvar"],
        aggfunc="count",
        margins=True,
    )
    suppressed_crosstab = acro.crosstab(
        index=[unsafe["indvar1"], unsafe["indvar2"]],
        columns=unsafe["indvar3"],
        values=unsafe["depvar"],
        aggfunc="count",
        margins=True,
    )
    output = acro.results.get_index(-1)

    _assert_table_cells_match(
        safe_crosstab.replace({0: np.nan}), suppressed_crosstab
    )  # native pandas will produce zeros
    assert (safe_crosstab == 0).sum().sum() == expected_unsafe
    _assert_suppressed_output(output, expected_unsafe=expected_unsafe)


# 4D
def test_4d_tables(synthetic_4d_unsafe, synthetic_4d_safe):
    """Check acro behaviour for 4d crosstab/pivot tables.

    Run  with margins==True so we know those are being correctly calculated
    """
    # 4d array of A,B,C three cells fail min threshold check
    expected_unsafe = 3
    safe = synthetic_4d_safe
    unsafe = synthetic_4d_unsafe

    # pivot tables
    acro = ACRO()
    acro.disable_suppression()
    unsafe_pivot = pd.pivot_table(
        data=unsafe,
        index=["indvar1", "indvar2"],
        columns=["indvar3", "indvar4"],
        values="depvar",
        aggfunc="count",
        margins=True,
    )
    unsup_acro_pivot = acro.pivot_table(
        data=unsafe,
        index=["indvar1", "indvar2"],
        columns=["indvar3", "indvar4"],
        values="depvar",
        aggfunc="count",
        margins=True,
    )
    output = acro.results.get_index(-1)
    assert unsafe_pivot.equals(unsup_acro_pivot)
    _assert_unsafe_output(output, expected_unsafe=expected_unsafe)

    acro.enable_suppression()
    safe_pivot = pd.pivot_table(
        data=safe,
        index=["indvar1", "indvar2"],
        columns=["indvar3", "indvar4"],
        values="depvar",
        aggfunc="count",
        margins=True,
    )
    suppressed_pivot = acro.pivot_table(
        data=unsafe,
        index=["indvar1", "indvar2"],
        columns=["indvar3", "indvar4"],
        values="depvar",
        aggfunc="count",
        margins=True,
    )
    output = acro.results.get_index(-1)

    _assert_table_cells_match(
        safe_pivot.replace({0: np.nan}), suppressed_pivot
    )  # native pandas will produce zeros
    assert (safe_pivot == 0).sum().sum() == expected_unsafe
    _assert_suppressed_output(output, expected_unsafe=expected_unsafe)

    # crosstabs
    acro = ACRO()
    acro.disable_suppression()

    unsafe_crosstab = pd.crosstab(
        index=[unsafe["indvar1"], unsafe["indvar2"]],
        columns=[unsafe["indvar3"], unsafe["indvar4"]],
        values=unsafe["depvar"],
        aggfunc="count",
        margins=True,
    )
    unsup_acro_crosstab = acro.crosstab(
        index=[unsafe["indvar1"], unsafe["indvar2"]],
        columns=[unsafe["indvar3"], unsafe["indvar4"]],
        values=unsafe["depvar"],
        aggfunc="count",
        margins=True,
    )
    output = acro.results.get_index(-1)
    assert unsafe_crosstab.equals(unsup_acro_crosstab)
    _assert_unsafe_output(output, expected_unsafe=expected_unsafe)

    acro.enable_suppression()
    safe_crosstab = pd.crosstab(
        index=[safe["indvar1"], safe["indvar2"]],
        columns=[safe["indvar3"], safe["indvar4"]],
        values=safe["depvar"],
        aggfunc="count",
        margins=True,
    )
    suppressed_crosstab = acro.crosstab(
        index=[unsafe["indvar1"], unsafe["indvar2"]],
        columns=[unsafe["indvar3"], unsafe["indvar4"]],
        values=unsafe["depvar"],
        aggfunc="count",
        margins=True,
    )
    output = acro.results.get_index(-1)

    _assert_table_cells_match(
        safe_crosstab.replace({0: np.nan}), suppressed_crosstab
    )  # native pandas will produce zeros
    assert (safe_crosstab == 0).sum().sum() == expected_unsafe
    _assert_suppressed_output(output, expected_unsafe=expected_unsafe)


def test_3dtables_multiple_aggfuncs(synthetic_3d_unsafe, synthetic_3d_safe):
    """Check behaviour of tables with multiindex and multiple aggfuncs."""
    # 3d array of A,B,C 2 xthree cells fail min threshold check
    expected_unsafe = 6
    safe = synthetic_3d_safe
    unsafe = synthetic_3d_unsafe

    # pivot tables
    acro = ACRO()
    acro.disable_suppression()
    unsafe_pivot = pd.pivot_table(
        data=unsafe,
        index=["indvar1", "indvar2"],
        columns="indvar3",
        values="depvar",
        aggfunc=["count", "mean"],
        margins=True,
    )
    unsup_acro_pivot = acro.pivot_table(
        data=unsafe,
        index=["indvar1", "indvar2"],
        columns="indvar3",
        values="depvar",
        aggfunc=["count", "mean"],
        margins=True,
    )
    output = acro.results.get_index(-1)
    assert unsafe_pivot.equals(unsup_acro_pivot)
    _assert_unsafe_output(output)

    acro.enable_suppression()
    safe_pivot = pd.pivot_table(
        data=safe,
        index=["indvar1", "indvar2"],
        columns="indvar3",
        values="depvar",
        aggfunc=["count", "mean"],
        margins=True,
    )
    suppressed_pivot = acro.pivot_table(
        data=unsafe,
        index=["indvar1", "indvar2"],
        columns="indvar3",
        values="depvar",
        aggfunc=["count", "mean"],
        margins=True,
    )
    output = acro.results.get_index(-1)

    _assert_table_cells_match(
        safe_pivot.replace({0: np.nan}), suppressed_pivot
    )  # native pandas will produce zeros
    assert (safe_pivot == 0).sum().sum() + (
        safe_pivot.isna()
    ).sum().sum() == expected_unsafe
    _assert_suppressed_output(output)

    # crosstabs
    acro = ACRO()
    acro.disable_suppression()

    unsafe_crosstab = pd.crosstab(
        index=[unsafe["indvar1"], unsafe["indvar2"]],
        columns=unsafe["indvar3"],
        values=unsafe["depvar"],
        aggfunc=["count", "mean"],
        margins=False,
    )
    unsup_acro_crosstab = acro.crosstab(
        index=[unsafe["indvar1"], unsafe["indvar2"]],
        columns=unsafe["indvar3"],
        values=unsafe["depvar"],
        aggfunc=["count", "mean"],
        margins=False,
    )
    output = acro.results.get_index(-1)
    assert unsafe_crosstab.equals(unsup_acro_crosstab)
    _assert_unsafe_output(output)

    acro.enable_suppression()
    safe_crosstab = pd.crosstab(
        index=[safe["indvar1"], safe["indvar2"]],
        columns=safe["indvar3"],
        values=safe["depvar"],
        aggfunc=["count", "mean"],
        margins=False,
    )
    suppressed_crosstab = acro.crosstab(
        index=[unsafe["indvar1"], unsafe["indvar2"]],
        columns=unsafe["indvar3"],
        values=unsafe["depvar"],
        aggfunc=["count", "mean"],
        margins=False,
    )
    output = acro.results.get_index(-1)

    _assert_table_cells_match(
        safe_crosstab.replace({0: np.nan}), suppressed_crosstab
    )  # native pandas will produce zeros
    assert (safe_crosstab == 0).sum().sum() + (
        safe_crosstab.isna()
    ).sum().sum() == expected_unsafe
    _assert_suppressed_output(output)


def test_zeros_not_disclosive_synthetic_holes(synthetic_2d_unsafe_holes):
    """Test zeros handling with synthetic data containing zero-sum cells."""
    df = synthetic_2d_unsafe_holes
    acro = ACRO(suppress=False)
    acro.sdc_checks.risk_appetite["zeros_are_disclosive"] = False
    result = acro.crosstab(df.indvar1, df.indvar2, values=df.depvar, aggfunc="sum")
    output = acro.results.get_index(0)
    assert (result == 0).sum().sum() > 0, "Expected zero-sum cells in result"
    assert result.loc["A", "A"] == 0, "Expected cell (A, A) value to be 0"
    assert output.status == "fail"
    assert "cells" in output.sdc


@pytest.mark.parametrize("aggfunc", ["mean", "sum", "count", "std", "mode"])
def test_2d_all_aggfuncs_safe(aggfunc, synthetic_2d_safe_duplicates):
    """Should handle all aggfuncs on 2D crosstab with safe data."""
    df = synthetic_2d_safe_duplicates.copy()
    cat_type = pd.api.types.CategoricalDtype(categories=["A", "B"], ordered=True)
    df["indvar1"] = df["indvar1"].astype(cat_type)

    # crosstab
    acro = ACRO(suppress=False)
    acro_crosstab = acro.crosstab(
        df.indvar1, df.indvar2, values=df.depvar, aggfunc=aggfunc
    )

    def mymode(series: pd.Series) -> int:
        return statsmode(series)[0]

    if aggfunc == "mode":
        aggfunc = mymode
    pandas_crosstab = pd.crosstab(
        df.indvar1, df.indvar2, values=df.depvar, aggfunc=aggfunc
    )
    assert pandas_crosstab.equals(acro_crosstab)
    _assert_safe_output(acro_crosstab, acro.results.get_index(-1))

    # pivot table
    acro_pivot = acro.pivot_table(
        df, index=["indvar1"], columns=["indvar2"], values=["depvar"], aggfunc=aggfunc
    )
    pandas_pivot = pd.pivot_table(
        df, index=["indvar1"], columns=["indvar2"], values=["depvar"], aggfunc=aggfunc
    )
    assert pandas_pivot.equals(acro_pivot)
    _assert_safe_output(acro_pivot, acro.results.get_index(-1))


@pytest.mark.parametrize("aggfunc", ["mean", "sum", "count", "std"])
def test_2d_crosstab_all_aggfuncs_unsafe_with_suppression(aggfunc, synthetic_2d_unsafe):
    """Should suppress unsafe 2D crosstab with all aggfuncs."""
    df = synthetic_2d_unsafe
    acro = ACRO(suppress=True)
    _ = acro.crosstab(df.indvar1, df.indvar2, values=df.depvar, aggfunc=aggfunc)
    output = acro.results.get_index(-1)
    assert output.status == "review"


def test_dominance_problem_synthetic_crosstab(synthetic_2d_unsafe_dominance):
    """Dominance check should detect extreme values in crosstab."""
    df = synthetic_2d_unsafe_dominance
    acro = ACRO(suppress=False)
    acro.crosstab(df.indvar1, df.indvar2, values=df.depvar, aggfunc="sum")
    output = acro.results.get_index(0)
    assert output.status == "fail", f"Expected fail for dominance, got {output.status}"
    assert (
        "dominance" in output.summary.lower()
        or "concentration" in output.summary.lower()
        or "percent" in output.summary.lower()
    ), f"Expected dominance check in summary, got: {output.summary}"


def test_dominance_problem_synthetic_crosstab_with_suppression(
    synthetic_2d_unsafe_dominance,
):
    """Dominance-flagged cells should be suppressed when suppression is enabled."""
    df = synthetic_2d_unsafe_dominance
    acro = ACRO(suppress=True)
    result = acro.crosstab(df.indvar1, df.indvar2, values=df.depvar, aggfunc="sum")
    suppressed = result.isna().sum().sum()
    _assert_suppressed_output(acro.results.get_index(0), suppressed)


def test_dominance_problem_synthetic_pivot_no_suppression(
    synthetic_2d_unsafe_dominance,
):
    """Pivot table should detect dominance problem without suppression."""
    df = synthetic_2d_unsafe_dominance
    acro = ACRO(suppress=False)
    acro.pivot_table(
        df, index=["indvar1"], columns=["indvar2"], values=["depvar"], aggfunc="sum"
    )
    output = acro.results.get_index(0)
    assert output.status == "fail", (
        f"Pivot table should fail on dominance, got {output.status}"
    )


def test_dominance_problem_synthetic_pivot_with_suppression(
    synthetic_2d_unsafe_dominance,
):
    """Pivot table should suppress dominance-flagged cells when suppression enabled."""
    df = synthetic_2d_unsafe_dominance
    acro = ACRO(suppress=True)
    result = acro.pivot_table(
        df, index=["indvar1"], columns=["indvar2"], values=["depvar"], aggfunc="mean"
    )
    suppressed = result.isna().sum().sum()

    _assert_suppressed_output(acro.results.get_index(0), suppressed)
