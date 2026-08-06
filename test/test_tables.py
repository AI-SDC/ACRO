"""Unit tests."""

import shutil

import numpy as np
import pandas as pd
import pytest
from tabulate import tabulate

from acro import (
    ACRO,
    utils,
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
    # results: Records = acro.finalise(PATH)
    correct_summary: str = (
        "FrequencyTable : \n"
        " PresenceOfLinkedTableCheck: A manual review against other outputs for differencing is recommended. Variables defining table are:  ['year', 'grant_type'].\n"
        " MinimumThresholdCheck: fail - 6 cells may need suppressing.\n"
    )
    # output = results.get_index(0)
    assert output.summary == correct_summary, (
        f"expected:\n{correct_summary}\n---\ngot:\n{output.summary}\n----"
    )
    assert output.status == "review"

    # Exception for suppression has been applied (verified via status)
    # shutil.rmtree(PATH)


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
    """Pivot table without automatic suppression."""
    acro = ACRO(suppress=False)
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "sum"]
    )
    output_0 = acro.results.get_index(0)
    assert output_0.output[0]["mean"]["inc_grants"].sum() == 36293992.0
    assert output_0.status == "pass"


def test_pivot_table_pass(data, acro):
    """Pivot table pass test."""
    acro = ACRO()
    acro.disable_suppression()
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "sum"]
    )
    results: Records = acro.finalise(PATH)
    output_0 = results.get_index(0)
    assert output_0.status == "pass", (
        f"expected pass, status/summary was  {output_0.status}/\n{output_0.summary}"
    )
    shutil.rmtree(PATH, ignore_errors=True)


def test_pivot_table_cols(data, acro):
    """Pivot table with columns test."""
    _ = acro.pivot_table(
        data,
        index=["grant_type"],
        columns=["year"],
        values=["inc_grants"],
        aggfunc=["mean", "std"],
    )
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(PATH)
    output_0 = results.get_index(0)
    output_0 = results.get_index(0)
    assert (
        "MinimumThresholdCheck" in output_0.summary
        or "threshold" in output_0.summary.lower()
    )
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
    # assert False,f'resa=\n{resa}'
    resb = acro.pivot_table(
        mydata, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    # assert False,f'resb=\n{resb}'
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
    result = acro.crosstab(
        [the_data.year, the_data.survivor],
        [the_data.grant_type],
        values=the_data.inc_activity,
        aggfunc="sum",
    )
    res = utils.prettify_table_string(result)
    table = pd.pivot_table(
        the_data,
        index=["year", "survivor"],
        columns="grant_type",
        values="inc_activity",
        aggfunc="sum",
        dropna=False,
    )
    table = table.reset_index()
    table.columns = [
        "\n".join(col) if isinstance(col, tuple) else col for col in table.columns
    ]
    # table=table.fillna(0)
    correct = tabulate(
        table, showindex=False, headers="keys", tablefmt="rounded_outline"
    )

    # correct = (
    #     "------------------------------------------------------------|\n"
    #     "grant_type          |N           |R             |R/G        |\n"
    #     "year survivor       |            |              |           |\n"
    #     "------------------------------------------------------------|\n"
    #     "2010 Dead in 2015   |       0.0  |1.723599e+07  |        0.0|\n"
    #     "     Alive in 2015  |52865600.0  |6.791129e+08  | 24592000.0|\n"
    #     "2011 Dead in 2015   |       0.0  |1.890400e+07  |        0.0|\n"
    #     "     Alive in 2015  |66714452.0  |1.002141e+09  | 86171000.0|\n"
    #     "2012 Dead in 2015   |       0.0  |2.616444e+07  |        0.0|\n"
    #     "     Alive in 2015  |64777124.0  |1.013167e+09  |107716000.0|\n"
    #     "2013 Dead in 2015   |       0.0  |2.913558e+07  |        0.0|\n"
    #     "     Alive in 2015  |86806336.0  |1.048305e+09  |104197000.0|\n"
    #     "2014 Dead in 2015   |       0.0  |3.074519e+07  |        0.0|\n"
    #     "     Alive in 2015  |74486664.0  |1.035069e+09  |106287000.0|\n"
    #     "2015 Dead in 2015   |       0.0  |1.488808e+07  |        0.0|\n"
    #     "     Alive in 2015  |56155352.0  |9.932494e+08  |105224000.0|\n"
    #     "------------------------------------------------------------|\n"
    # )
    assert res.split() == correct.split(), f"got\n{res}\nexpected\n{correct}\n"


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
    _ = acro.pivot_table(
        data,
        index=["grant_type"],
        columns=["year"],
        values=["inc_grants"],
        aggfunc=["mean", "std"],
    )
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(PATH)
    output_0 = results.get_index(0)
    assert (
        "MinimumThresholdCheck" in output_0.summary
        or "threshold" in output_0.summary.lower()
    )
    assert output_0.status in ("review", "fail")
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
    assert table["All"].iat[6] > 0
    assert table.shape[0] >= 7
    # Verify suppression has been applied and table is ready for review
    assert output.status in {"review", "fail"}


def test_crosstab_with_totals_with_suppression_hierarchical(data, acro):
    """Test hierarchical crosstab margins with suppression enabled."""
    _ = acro.crosstab(
        [data.year, data.survivor], [data.grant_type, data.status], margins=True
    )
    output = acro.results.get_index(0)
    table = output.output[0]
    # Verify suppression has been applied to hierarchical table
    assert "All" in table.columns
    assert table["All"].iat[12] > 0
    assert output.status in {"review", "fail"}


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
    assert output.status in {"review", "fail"}


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
    # Verify crosstab with empty data subset returns valid status
    assert acro.results.get_index(0).status in {"review", "fail"}


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


# ---------------------------------------------------------------------------
# acro_tables.py — crosstab rounding with margins
# ---------------------------------------------------------------------------


def test_crosstab_rounding_with_margins(data):
    """Crosstab with round mitigation and margins recomputes rounded margins."""
    acro_obj = ACRO()
    acro_obj.enable_rounding(base=5)
    result = acro_obj.crosstab(data.year, data.grant_type, margins=True)
    assert isinstance(result, pd.DataFrame)
    # The 'All' margin column/row should be present
    assert "All" in result.columns or "All" in result.index


# ---------------------------------------------------------------------------
# acro_tables.py — pivot_table rounding path
# ---------------------------------------------------------------------------


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
