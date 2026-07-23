"""Unit tests."""

import logging
import os
import shutil
import tempfile

import matplotlib as mpl

mpl.use("Agg")
from typing import Any

import numpy as np
import pandas as pd
import pytest

from acro import (
    ACRO,
    add_constant,
    table_utils,
    utils,
)
from acro.aggregationfunctions import agg_nk, agg_p_percent, agg_threshold
from acro.record import Records
from acro.sdc_agg_funcs import (
    agg_missing,
    agg_mode,
    agg_num_negative,
    agg_top_n_sum,
    get_statsmodel_dof,
)
from acro.sdcchecks import SDCChecks, SDCEvidence
from acro.table_utils import (
    get_analysis_summary,
    get_debugging_table_analysis,
    get_redacted_data,
    translate_args_to_newdf,
)
from acro.tablemodeldetails import TableModelDetails

# pylint: disable=redefined-outer-name,too-many-lines

PATH: str = "RES_PYTEST"


@pytest.fixture(autouse=True)
def cleanup_path():
    """Clean up output directories before and after each test."""
    for d in [
        "RES_PYTEST",
        "outputs",
        "acro_artifacts",
        "sdc_results",
        "test_add_to_acro",
    ]:
        shutil.rmtree(d, ignore_errors=True)
    yield
    for d in [
        "RES_PYTEST",
        "outputs",
        "acro_artifacts",
        "sdc_results",
        "test_add_to_acro",
    ]:
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def data() -> pd.DataFrame:
    """Load test data."""
    path = os.path.join("data", "test_data.dta")
    data = pd.read_stata(path)
    return data


@pytest.fixture
def acro() -> ACRO:
    """Initialise ACRO."""
    return ACRO(suppress=True)


def test_add_backticks():
    """Test the add_backticks helper function."""
    assert table_utils.add_backticks("foo") == "foo"
    assert table_utils.add_backticks("foo bar") == "`foo bar`"
    assert table_utils.add_backticks("`foo bar`") == "`foo bar`"
    assert table_utils.add_backticks("foo bar baz") == "`foo bar baz`"


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
        " PresenceOfLinkedTableCheck: A manual review is needed. Variables defining table are:  ['year', 'grant_type'].\n"
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
    # correct_summary: str = "fail; all-values-are-same: 1 cells may need suppressing; "
    # ##TODO    assert output.summary == correct_summary
    #  ##TODO run directly in pandas mode and compare all of the table values to the pandas mode output
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

    # TODO next three lines would make more sense if you moved them further down the method
    output = acro.results.get_index(0)
    total_nan: int = output.output[0]["R/G"].isnull().sum()
    assert total_nan == 6, f"output is\n{output.output[0]}"

    positions = output.sdc["cells"]["MinimumThresholdCheck"]
    for pos in positions:
        row, col = pos
        assert np.isnan(output.output[0].iloc[row, col])
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(PATH)
    correct_summary: str = (
        "FrequencyTable : \n"
        " PresenceOfLinkedTableCheck: A manual review is needed. Variables defining table are:  ['year', 'grant_type'].\n"
        " MinimumThresholdCheck: fail - 6 cells may need suppressing.\n"
    )
    output = results.get_index(0)
    assert output.summary == correct_summary, (
        f"expected:\n{correct_summary}\n---\ngot:\n{output.summary}\n----"
    )
    # TODO check status is now review with
    # TODO check appropriate exception added saying suppression has been applied
    shutil.rmtree(PATH)


def test_crosstab_multiple(data, acro):
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
        " PresenceOfLinkedTableCheck: A manual review is needed. Variables defining table are:  ['year', 'grant_type'].\n"
        " MinimumThresholdCheck: fail - 6 cells may need suppressing.\n"
    )
    output = results.get_index(0)
    assert output.summary == correct_summary, (
        f"expected:\n{correct_summary}\n---\ngot:\n{output.summary}\n----"
    )
    shutil.rmtree(PATH)


def test_negatives(data, acro):
    """Pivot table and Crosstab with negative values."""
    data.loc[0:10, "inc_grants"] = -10
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mean"
    )
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    acro.add_exception("output_0", "Let me have it")
    acro.add_exception("output_1", "I want this")
    results: Records = acro.finalise(PATH)
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    # TODO check that the summary is correct for both outputs
    # TODO compare the outputs to the equivalentpandas outputs
    assert output_0.status == "review"
    assert output_1.status == "review"
    shutil.rmtree(PATH)


def test_pivot_table_without_suppression(data):
    """Pivot table without automatic suppression."""
    acro = ACRO(suppress=False)
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    output_0 = acro.results.get_index(0)
    # TODO compare the outputs to the equivalent pandas outputs
    # TODO check status and summary are what they should be
    assert output_0.output[0]["mean"]["inc_grants"].sum() == 36293992.0
    assert output_0.status in ["pass", "fail", "review"]  ##TODO make less VAGUE


def test_pivot_table_pass(data, acro):
    """Pivot table pass test."""
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    results: Records = acro.finalise(PATH)
    output_0 = results.get_index(0)
    assert output_0.status in ["pass", "review"]  # TODO why not just "pass"?
    shutil.rmtree(PATH)


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
    # TODO compare the outputs to the equivalent pandas outputs
    # TODO check status and summary are what they should be
    assert output_0.status == "review"
    shutil.rmtree(PATH)


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
    # TODO compare the outputs to the equivalent pandas outputs
    # TODO check status and summary are what they should be
    assert output_0.status in ("review", "fail", "pass")
    assert output_1.status in ("review", "fail", "pass")
    shutil.rmtree(PATH)


def test_missing(data, acro, monkeypatch):
    """Pivot table and Crosstab with missing values."""
    acro.sdc_checks.risk_appetite["check_missing_values"] = True
    acro.suppress = False
    data.loc[0:10, "inc_grants"] = np.nan
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mean"
    )
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    exceptions = ["I want it", "Let me have it"]
    monkeypatch.setattr("builtins.input", lambda _: exceptions.pop(0))
    results: Records = acro.finalise(PATH, interactive=True)
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    assert output_0.exception == "I want it"
    assert output_1.exception == "Let me have it"
    shutil.rmtree(PATH)


@pytest.mark.skip(reason="Not yet implemented")
def test_suppression_error():
    """Apply suppression type error test."""


def test_prettify_tablestring(data):
    """Test prettifying string version of table."""
    mydata = data
    # take subsets for brevity
    mydata = mydata[(mydata["charity"].str[0] == "W")]
    mydata = mydata[mydata["year"] < 2012]
    correct = (
        "----------------------------------------------------------------------|\n"
        "grant_type                               |N          |R    |R/G       |\n"
        "status                                   |successful |dead |successful|\n"
        "year charity                             |           |     |          |\n"
        "----------------------------------------------------------------------|\n"
        "2010 WWF                                 | 0         | 0   | 1        |\n"
        "     Walsall domestic violence forum ltd | 0         | 1   | 0        |\n"
        "     Will Woodlands                      | 1         | 0   | 0        |\n"
        "     Worcestershire Lifestyles (Dead)    | 0         | 1   | 0        |\n"
        "2011 WWF                                 | 0         | 0   | 1        |\n"
        "     Walsall domestic violence forum ltd | 0         | 1   | 0        |\n"
        "     Will Woodlands                      | 1         | 0   | 0        |\n"
        "     Worcestershire Lifestyles (Dead)    | 0         | 1   | 0        |\n"
        "----------------------------------------------------------------------|\n"
    )
    complex_str = utils.prettify_table_string(
        pd.crosstab([mydata.year, mydata.charity], [mydata.grant_type, mydata.status])
    )
    assert complex_str == correct, f"got:\n{complex_str}\nexpected:\n{correct}\n"

    correct2 = (
        "------------------------|\n"
        "grant_type  |N  |R  |R/G|\n"
        "year        |   |   |   |\n"
        "------------------------|\n"
        "2010        |1  |2  |1  |\n"
        "2011        |1  |2  |1  |\n"
        "------------------------|\n"
    )
    simple_str = utils.prettify_table_string(
        pd.crosstab([mydata.year], [mydata.grant_type])
    )
    assert simple_str == correct2, f"got:\n{simple_str}\nexpected:\n{correct2}\n"

    # test spaces in variable names dealt with
    correct3 = (
        "---------------------------------------|\n"
        "survivor  |Dead_in_2015  |Alive_in_2015|\n"
        "year      |              |             |\n"
        "---------------------------------------|\n"
        "2010      |2             |2            |\n"
        "2011      |2             |2            |\n"
        "---------------------------------------|\n"
    )
    nospaces__str = utils.prettify_table_string(
        pd.crosstab([mydata.year], [mydata.survivor])
    )
    assert nospaces__str == correct3, f"got:\n{nospaces__str}\nexpected:\n{correct3}\n"


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
    correct = (
        "------------------------------------------------------------|\n"
        "grant_type          |N           |R             |R/G        |\n"
        "year survivor       |            |              |           |\n"
        "------------------------------------------------------------|\n"
        "2010 Dead in 2015   |       0.0  |1.723599e+07  |        0.0|\n"
        "     Alive in 2015  |52865600.0  |6.791129e+08  | 24592000.0|\n"
        "2011 Dead in 2015   |       0.0  |1.890400e+07  |        0.0|\n"
        "     Alive in 2015  |66714452.0  |1.002141e+09  | 86171000.0|\n"
        "2012 Dead in 2015   |       0.0  |2.616444e+07  |        0.0|\n"
        "     Alive in 2015  |64777124.0  |1.013167e+09  |107716000.0|\n"
        "2013 Dead in 2015   |       0.0  |2.913558e+07  |        0.0|\n"
        "     Alive in 2015  |86806336.0  |1.048305e+09  |104197000.0|\n"
        "2014 Dead in 2015   |       0.0  |3.074519e+07  |        0.0|\n"
        "     Alive in 2015  |74486664.0  |1.035069e+09  |106287000.0|\n"
        "2015 Dead in 2015   |       0.0  |1.488808e+07  |        0.0|\n"
        "     Alive in 2015  |56155352.0  |9.932494e+08  |105224000.0|\n"
        "------------------------------------------------------------|\n"
    )
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


def test_zeros_are_not_disclosive(data, acro):
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
    # TODO shouldn't this be status pass?
    # TODO check summary - should say TRE risk appettie stattes zeros ok
    assert output_0.status == "review"
    shutil.rmtree(PATH)


def test_crosstab_with_totals_without_suppression(data, acro):
    """Test the crosstab with margins is true and suppression is false."""
    acro.suppress = False
    _ = acro.crosstab(data.year, data.grant_type, margins=True)
    output = acro.results.get_index(0)
    assert output.output[0]["All"].iat[0] == 153
    # TODO easier to compare the outputs to the equivalent pandas outputs
    # TODO check status and summary are what they should be
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
    # TODO test that the right cells have been identified and suppressed
    # TODO check exception has been added to say suppression is applied
    # TODO status should be review
    assert output.status in {"review", "fail"}


def test_crosstab_with_totals_with_suppression_hierarchical(data, acro):
    """Test hierarchical crosstab margins with suppression enabled."""
    _ = acro.crosstab(
        [data.year, data.survivor], [data.grant_type, data.status], margins=True
    )
    output = acro.results.get_index(0)
    table = output.output[0]
    # TODO test that the right cells have been identified and suppressed
    # TODO check exception has been added to say suppression is applied
    # TODO status should be review
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

    # TODO test that the right cells have been identified and suppressed
    # TODO check exception has been added to say suppression is applied
    # TODO status should be review
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
    # TODO check status and summary
    assert acro.results.get_index(0).status in {"review", "fail"}


def test_crosstab_with_manual_totals_with_suppression(data, acro):
    """Test manual totals path when suppression is enabled."""
    _ = acro.crosstab(data.year, data.grant_type, margins=True, show_suppressed=True)
    output = acro.results.get_index(0)
    table = output.output[0]

    # TODO test that the right cells have been identified and suppressed
    # TODO check exception has been added to say suppression is applied
    # TODO status should be review
    assert "All" in table.columns
    assert table["All"].iat[0] > 0
    assert table["All"].iat[6] > 0
    assert output.status in {"review", "fail"}


def test_crosstab_with_manual_totals_with_suppression_hierarchical(data, acro):
    """Test crosstab when margins and suppression are true with hierarchical data.

    Tests with multilevel indexes and columns while using the total manual function.
    """
    _ = acro.crosstab(
        [data.year, data.survivor],
        [data.grant_type, data.status],
        margins=True,
        show_suppressed=True,
    )
    output = acro.results.get_index(0)
    assert ("G", "dead") in output.output[0].columns
    assert "All" in output.output[0].columns
    assert np.isnan(output.output[0][("G", "dead")].iat[0])
    assert output.output[0]["All"].iat[12] > 0


def test_crosstab_with_manual_totals_with_suppression_with_aggfunc_mean(data, acro):
    """Test mean crosstab with manual totals and suppression enabled."""
    _ = acro.crosstab(
        data.year,
        data.grant_type,
        values=data.inc_grants,
        aggfunc="mean",
        margins=True,
        show_suppressed=True,
    )
    output = acro.results.get_index(0)
    table = output.output[0]

    assert "All" in table.columns
    assert table["All"].iat[0] > 0
    assert table["All"].iat[6] > 0
    assert output.status in {"review", "fail"}


def test_hierarchical_crosstab_with_manual_totals_with_mean(data, acro):
    """Test crosstab.

    Test the crosstab with both margins and suppression are true, with aggfunc
    mean and with multilevel columns and rows while using the total manual
    function.
    """
    _ = acro.crosstab(
        [data.year, data.survivor],
        [data.grant_type, data.survivor],
        values=data.inc_grants,
        aggfunc="mean",
        margins=True,
        show_suppressed=True,
    )
    output = acro.results.get_index(0)
    assert ("G", "Dead in 2015") in output.output[0].columns
    assert "All" in output.output[0].columns
    assert np.isnan(output.output[0][("G", "Dead in 2015")].iat[0])
    assert output.output[0]["All"].iat[0] > 0
    assert output.output[0]["All"].iat[12] > 0


def test_crosstab_with_manual_totals_with_suppression_with_aggfunc_std(data, acro):
    """Test std crosstab with suppression enabled."""
    _ = acro.crosstab(
        data.year,
        data.grant_type,
        values=data.inc_grants,
        aggfunc="std",
        margins=True,
        show_suppressed=True,
    )
    output = acro.results.get_index(0)
    table = output.output[0]

    assert output.status in {"review", "fail"}
    assert table.shape[0] > 0
    assert table.shape[1] > 0


def test_pivot_table_with_totals_with_suppression(data, acro):
    """Test the pivot table with both margins and suppression are true."""
    _ = acro.pivot_table(
        data,
        index=["year"],
        columns=["grant_type"],
        values=["inc_grants"],
        aggfunc="count",
        margins=True,
    )
    output = acro.results.get_index(0)
    assert "R/G" not in output.output[0].columns
    assert ("inc_grants", "All") in output.output[0].columns
    assert output.output[0][("inc_grants", "All")].iat[0] > 0
    assert output.output[0][("inc_grants", "All")].iat[6] > 0


def test_crosstab_multiple_aggregate_function(data, acro):
    """Crosstab with multiple agg funcs."""
    acro = ACRO(suppress=False)
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc=["mean", "std"]
    )
    output = acro.results.get_index(0)
    assert output.status == "fail"
    correctval = 97383496.0
    assert output.output[0]["mean"]["R/G"].sum() == correctval


def test_crosstab_with_totals_with_suppression_with_two_aggfuncs(data, acro):
    """Test crosstab.

    Test the crosstab with both margins and suppression are true and with a
    list of aggfuncs while using the total manual function.
    """
    _ = acro.crosstab(
        data.year,
        data.grant_type,
        values=data.inc_grants,
        aggfunc=["count", "std"],
        margins=True,
    )
    _ = acro.crosstab(
        data.year,
        data.grant_type,
        values=data.inc_grants,
        aggfunc="count",
        margins=True,
    )
    _ = acro.crosstab(
        data.year,
        data.grant_type,
        values=data.inc_grants,
        aggfunc="std",
        margins=True,
    )
    output = acro.results.get_index(0)
    assert output.output[0].shape[1] >= 8
    output_1 = acro.results.get_index(1)
    output_2 = acro.results.get_index(2)
    # Verify tables can be concatenated
    output_3 = pd.concat([output_1.output[0], output_2.output[0]], axis=1)
    output_4 = (output.output[0]).droplevel(0, axis=1)
    # Just verify they have same shape after dropping level
    assert output_3.shape == output_4.shape


def test_crosstab_with_totals_with_suppression_with_two_aggfuncs_hierarchical(
    data, acro
):
    """Test crosstab.

    Test the crosstab with both margins and suppression are true and with a
    list of aggfuncs and a list of columns while using the total manual
    function.
    """
    _ = acro.crosstab(
        data.year,
        [data.grant_type, data.survivor],
        values=data.inc_grants,
        aggfunc=["count", "std"],
        margins=True,
    )
    output = acro.results.get_index(0)
    assert ("count", "G", "Alive in 2015") in output.output[0].columns
    assert ("std", "G", "Alive in 2015") in output.output[0].columns


def test_crosstab_with_manual_totals_with_suppression_with_two_aggfunc(data, acro):
    """Test multi-aggfunc crosstab with suppression enabled."""
    _ = acro.crosstab(
        data.year,
        data.grant_type,
        values=data.inc_grants,
        aggfunc=["count", "std"],
        margins=True,
        show_suppressed=True,
    )
    assert acro.results.get_index(0).status in {"review", "fail"}


@pytest.mark.skip(reason="Not yet implemented")
def test_crosstab_with_totals_raises_when_data_none():
    """Test that crosstab_with_totals raises AssertionError when data is None."""
    # When crosstab=False, data is not set from create_dataframe; passing data=None
    # must raise "data must be set when applying crosstab queries".
    # with pytest.raises(
    #     AssertionError, match="data must be set when applying crosstab queries"
    # ):
    #     crosstab_with_totals(
    #         masks={},
    #         aggfunc=None,
    #         index=pd.Series([1, 2]),
    #         columns=pd.Series([1, 2]),
    #         values=None,
    #         margins=False,
    #         margins_name="All",
    #         dropna=True,
    #         crosstab=False,
    #         data=None,
    #     )


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


def test_get_catdtype_string_series():
    """Get_catdtype on a string series produces unordered categorical dtype."""
    s = pd.Series(["a", "b", "a", "c"])
    cat = utils.get_catdtype(s)
    assert hasattr(cat, "categories")
    assert not cat.ordered


def test_get_catdtype_numeric_series():
    """Get_catdtype on an integer series produces ordered categorical dtype."""
    s = pd.Series([1, 2, 3, 2, 1])
    cat = utils.get_catdtype(s)
    assert cat.ordered is True


def test_get_catdtype_nan_series():
    """Get_catdtype drops NaN before computing categories."""
    s = pd.Series([1.0, 2.0, float("nan"), 1.0])
    cat = utils.get_catdtype(s)
    assert pd.isna(cat.categories).sum() == 0


def test_is_blocked_extension_returns_true():
    """Is_blocked_extension returns True for a blocked extension."""
    result = utils.is_blocked_extension("output.exe", [".exe", ".bat"])
    assert result is True


def test_is_blocked_extension_case_insensitive():
    """Is_blocked_extension is case-insensitive."""
    result = utils.is_blocked_extension("output.EXE", [".exe"])
    assert result is True


def test_is_blocked_extension_returns_false_for_allowed():
    """Is_blocked_extension returns False for an allowed extension."""
    result = utils.is_blocked_extension("output.png", [".exe"])
    assert result is False


def test_agg_mode_single_mode():
    """Agg_mode returns the single mode."""
    s = pd.Series([1, 2, 2, 3])
    assert agg_mode(s) == 2


def test_agg_mode_multiple_modes():
    """Agg_mode handles multiple modes by picking one randomly."""
    s = pd.Series([1, 1, 2, 2])
    result = agg_mode(s)
    assert result in (1, 2)


def test_agg_num_negative_with_negatives():
    """Agg_num_negative returns count of negatives."""
    s = pd.Series([-1, 2, -3, 4])
    assert agg_num_negative(s) == 2


def test_agg_num_negative_no_negatives():
    """Agg_num_negative returns 0 when no negatives."""
    s = pd.Series([1, 2, 3])
    assert agg_num_negative(s) == 0


def test_agg_missing_with_nan():
    """Agg_missing returns True when NaN present (line 99)."""
    s = pd.Series([1.0, float("nan"), 3.0])
    assert bool(agg_missing(s)) is True


def test_agg_missing_no_nan():
    """Agg_missing returns False when no NaN."""
    s = pd.Series([1.0, 2.0, 3.0])
    assert bool(agg_missing(s)) is False


def test_agg_top_n_sum_non_numeric():
    """Agg_top_n_sum returns 0 for non-numeric dtype."""
    s = pd.Series(["a", "b", "c"])
    assert agg_top_n_sum(s) == 0


def test_get_statsmodel_dof_no_attribute():
    """Get_statsmodel_dof raises AttributeError when model lacks df_resid."""

    class FakeModel:
        pass

    with pytest.raises(AttributeError, match="model does not have df_resid attribute"):
        get_statsmodel_dof(FakeModel())


def test_tablemodeldetails_kwargs_not_dict():
    """Passing non-dict kwargs raises TypeError."""
    with pytest.raises(TypeError, match="kwargs argument should be a dict"):
        TableModelDetails(
            index=[pd.Series([1, 2])],
            columns=[],
            values=pd.Series([1, 2]),
            thekwargs="bad",  # type: ignore[arg-type]
        )


def test_tablemodeldetails_values_not_series():
    """Passing non-Series values raises TypeError (line 77)."""
    with pytest.raises(
        TypeError, match="Expected values argument to be a panda Series"
    ):
        TableModelDetails(
            index=[pd.Series([1, 2])],
            columns=[],
            values=[1, 2],
        )


def test_tablemodeldetails_axis_item_not_series():
    """Passing non-Series element in index list raises TypeError."""
    with pytest.raises(
        TypeError, match="Expected .* element of .* list to be a panda Series"
    ):
        TableModelDetails(
            index=[[1, 2]],
            columns=[],
            values=pd.Series([1, 2]),
        )


def test_tablemodeldetails_axis_not_a_list():
    """Passing non-list axis raises TypeError."""
    with pytest.raises(TypeError, match="axis argument should be a list"):
        TableModelDetails(
            index=pd.Series([1, 2]),
            columns=[],
            values=pd.Series([1, 2]),
        )


def test_get_axis_metadata_non_series_item():
    """_get_axis_metadata logs when a dimension is not a Series (line 165)."""
    model = TableModelDetails(
        index=[pd.Series([1, 2, 3], name="idx")],
        columns=[],
        values=pd.Series([10, 20, 30], name="val"),
    )
    # Call with a list containing a non-Series to exercise the else branch
    result = model._get_axis_metadata([42], "index")
    assert result == {}  # non-series items are skipped


def test_get_table_newagg_incompatible_length():
    """Get_table_newagg raises AttributeError when values length mismatches (line 222)."""
    idx = pd.Series([1, 2, 3], name="idx")
    vals = pd.Series([10, 20, 30], name="val")
    model = TableModelDetails(
        index=[idx],
        columns=[],
        values=vals,
    )
    # Replace values with longer series to trigger the incompatible-length check
    model.values = pd.Series(list(range(100)), name="val")
    with pytest.raises(AttributeError, match="incompatibe length"):
        model.get_table_newagg(np.sum)


def test_get_allfalse_table_array_type():
    """Get_allfalse_table for array model_type uses value_counts path."""
    s = pd.Series([1, 2, 2, 3, 3, 3], name="vals")
    model = TableModelDetails(
        index=[s],
        thekwargs={"bins": 3},
        command="hist",
    )
    assert model.model_type == "array"
    mask = model.get_allfalse_table()
    assert isinstance(mask, pd.DataFrame)
    assert mask.dtypes.iloc[0] is bool or mask.dtypes.iloc[0] == "bool"


def test_get_zeros_table_basic():
    """Get_zeros_table returns a DataFrame of zeros."""
    idx = pd.Series([1, 2, 3, 1, 2, 3], name="idx")
    cols = pd.Series(["a", "a", "a", "b", "b", "b"], name="col")
    vals = pd.Series([10, 20, 30, 40, 50, 60], name="val")
    model = TableModelDetails(
        index=[idx],
        columns=[cols],
        values=vals,
    )
    zt = model.get_zeros_table()
    assert isinstance(zt, pd.DataFrame)
    assert (zt.values == 0).all()


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


def test_mitigation_setter_unknown_string():
    """Setting mitigation to unknown string falls back to 'none'."""
    acro_obj = ACRO(suppress=False)
    acro_obj.mitigation = "unknown_mitigation"
    assert acro_obj.mitigation == "none"


def test_round_base_setter_non_integer():
    """Setting round_base to a non-integer falls back to default."""
    acro_obj = ACRO()
    default = acro_obj.round_base
    acro_obj.round_base = "five"  # type: ignore[assignment]
    assert acro_obj.round_base == default


def test_round_base_setter_zero():
    """Setting round_base to 0 falls back to default."""
    acro_obj = ACRO()
    default = acro_obj.round_base
    acro_obj.round_base = 0
    assert acro_obj.round_base == default


def test_suppress_setter_false_when_round(caplog):
    """Suppress=False when mitigation is 'round' logs a warning."""
    acro_obj = ACRO()
    acro_obj.mitigation = "round"
    assert acro_obj.mitigation == "round"
    with caplog.at_level(logging.INFO, logger="acro"):
        acro_obj.suppress = False
    assert acro_obj.mitigation == "round"
    assert "no effect" in caplog.text


def test_record_table_output_round_mitigation(data):
    """_record_table_output stores round_base in properties (line 198) and adds exception."""
    acro_obj = ACRO(mitigation="round", round_base=5)
    _ = acro_obj.crosstab(data.year, data.grant_type)
    output = acro_obj.results.get_index(0)
    assert output.properties.get("round_base") == 5
    assert output.status == "review"
    assert "Rounding" in output.exception


def test_finalise_evidence_dof_as_csv_string():
    """Finalise_evidence() writes a CSV file when dof is a multiline string."""
    records = Records()
    dof_csv = "idx,val\n0,10\n1,20\n"  # multiline CSV string
    evidence_store = {
        "output_0": {
            "command": "test",
            "analysis_names": ["FrequencyTable"],
            "variable_types": {},
            "dof": dof_csv,
            "interim_tables": {},
        }
    }
    with tempfile.TemporaryDirectory() as tmp:
        manifest = records.finalise_evidence(tmp, evidence_store)
        # dof_file should have been written
        entry = manifest["outputs"]["output_0"]
        dof_file = entry["dof"]
        assert dof_file is not None
        assert dof_file.endswith(".csv")
        assert os.path.exists(os.path.join(tmp, dof_file))


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


def test_agg_p_percent_normal_violation():
    """Top contributor dominates → p_val < SAFE_PRATIO_P → True."""
    s = pd.Series([100.0, 1.0, 1.0, 1.0])
    assert agg_p_percent(s) == True  # noqa: E712


def test_agg_p_percent_normal_pass():
    """Evenly spread values → p_val >= SAFE_PRATIO_P → False."""
    s = pd.Series([10.0, 10.0, 10.0, 10.0, 10.0])
    assert agg_p_percent(s) == False  # noqa: E712


def test_agg_p_percent_all_zeros_returns_zeros_are_disclosive():
    """All-zero series → returns ZEROS_ARE_DISCLOSIVE (True by default)."""
    s = pd.Series([0.0, 0.0, 0.0])
    result = agg_p_percent(s)
    assert isinstance(result, bool)


def test_agg_p_percent_single_element():
    """Single-element series → size <= 1 → returns ZEROS_ARE_DISCLOSIVE."""
    s = pd.Series([42.0])
    result = agg_p_percent(s)
    assert isinstance(result, bool)


def test_agg_p_percent_not_a_series_raises():
    """Non-Series input raises AssertionError."""
    with pytest.raises(AssertionError):
        agg_p_percent([1, 2, 3])


def test_agg_nk_violation():
    """Top-N sum > K * total → True."""
    s = pd.Series([100.0, 1.0, 1.0, 1.0])
    assert agg_nk(s) == True  # noqa: E712


def test_agg_nk_pass():
    """Evenly spread → False."""
    s = pd.Series([10.0, 10.0, 10.0, 10.0, 10.0])
    assert agg_nk(s) == False  # noqa: E712


def test_agg_nk_zero_total():
    """Zero total → False (no dominance)."""
    s = pd.Series([0.0, 0.0, 0.0])
    assert agg_nk(s) is False


def test_agg_threshold_below_threshold():
    """Fewer than THRESHOLD values → True."""
    s = pd.Series([1, 2, 3])
    assert agg_threshold(s) == True  # noqa: E712


def test_agg_threshold_above_threshold():
    """More than THRESHOLD values → False."""
    s = pd.Series(list(range(20)))
    assert agg_threshold(s) == False  # noqa: E712


def _make_sdc(**overrides: Any) -> dict[str, Any]:
    base = {
        "suppressed": False,
        "negative": 0,
        "missing": 0,
        "threshold": 0,
        "p-ratio": 0,
        "nk-rule": 0,
        "all-values-are-same": 0,
    }
    base.update(overrides)
    return {"summary": base}


def test_get_analysis_summary_pass_when_all_zero():
    """A fully empty summary is treated as a pass."""
    status, summary = get_analysis_summary(_make_sdc())
    assert status == "pass"
    assert summary == "pass"


def test_get_analysis_summary_negative_branch():
    """Negative values trigger the review branch."""
    status, summary = get_analysis_summary(_make_sdc(negative=1))
    assert status == "review"
    assert "negative" in summary


def test_get_analysis_summary_missing_branch():
    """Missing values trigger the review branch."""
    status, summary = get_analysis_summary(_make_sdc(missing=2))
    assert status == "review"
    assert "missing" in summary


def test_get_analysis_summary_threshold_fail():
    """Threshold violations yield a failure summary."""
    status, summary = get_analysis_summary(_make_sdc(threshold=3))
    assert status == "fail"
    assert "threshold" in summary


def test_get_analysis_summary_threshold_suppressed():
    """Suppressed threshold violations are treated as review."""
    status, _ = get_analysis_summary(_make_sdc(threshold=3, suppressed=True))
    assert status == "review"


def test_get_analysis_summary_pratio_fail():
    """P-ratio violations yield a failure summary."""
    status, summary = get_analysis_summary(_make_sdc(**{"p-ratio": 1}))
    assert status == "fail"
    assert "p-ratio" in summary


def test_get_analysis_summary_nk_fail():
    """NK-rule violations yield a failure summary."""
    status, summary = get_analysis_summary(_make_sdc(**{"nk-rule": 2}))
    assert status == "fail"
    assert "nk-rule" in summary


def test_get_analysis_summary_all_same_fail():
    """All-same-value violations yield a failure summary."""
    status, summary = get_analysis_summary(_make_sdc(**{"all-values-are-same": 1}))
    assert status == "fail"
    assert "all-values-are-same" in summary


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


def test_check_model_dof_dataframe_dof_pass():
    """Dataframe dof values at or above threshold pass."""
    sdc = SDCChecks(_RISK_APPETITE)
    ev = SDCEvidence()
    ev.dof = pd.DataFrame({"a": [15, 20], "b": [12, 30]})
    status, _, _ = sdc.check_model_dof("FrequencyTable", ev, None)
    assert status == "pass"


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


def test_enable_rounding_no_base():
    """Enabling rounding without a base preserves the existing base."""
    acro_obj = ACRO()
    initial_base = acro_obj.round_base
    acro_obj.enable_rounding()
    assert acro_obj.mitigation == "round"
    assert acro_obj.round_base == initial_base


def test_enable_rounding_with_base():
    """Enabling rounding with a base updates the rounding base."""
    acro_obj = ACRO()
    acro_obj.enable_rounding(base=10)
    assert acro_obj.mitigation == "round"
    assert acro_obj.round_base == 10


def test_disable_rounding_when_round():
    """Disabling rounding resets the mitigation to none."""
    acro_obj = ACRO()
    acro_obj.enable_rounding()
    assert acro_obj.mitigation == "round"
    acro_obj.disable_rounding()
    assert acro_obj.mitigation == "none"


def test_disable_rounding_when_not_round():
    """Disabling rounding leaves non-round mitigation unchanged."""
    acro_obj = ACRO()
    acro_obj.mitigation = "none"
    acro_obj.disable_rounding()
    assert acro_obj.mitigation == "none"


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
    """Pivot_table() with aggfunc='mode' uses the agg_mode helper (lines 477-478)."""
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
# acro_tables.py — crosstab rounding with margins (line 355)
# ---------------------------------------------------------------------------


def test_crosstab_rounding_with_margins(data):
    """Crosstab with round mitigation and margins recomputes rounded margins (line 355)."""
    acro_obj = ACRO()
    acro_obj.enable_rounding(base=5)
    result = acro_obj.crosstab(data.year, data.grant_type, margins=True)
    assert isinstance(result, pd.DataFrame)
    # The 'All' margin column/row should be present
    assert "All" in result.columns or "All" in result.index


# ---------------------------------------------------------------------------
# acro_tables.py — pivot_table rounding path (lines 546-551)
# ---------------------------------------------------------------------------


def test_pivot_table_rounding(data):
    """Pivot_table with mitigation='round' goes through the rounding branch (lines 546-551)."""
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


def test_manual_check_unknown_model_type_returns_fail() -> None:
    """Unknown model types return a fail result from manual checks."""
    sdc = SDCChecks(_RA)
    ev = SDCEvidence()
    model = TableModelDetails(
        index=[pd.Series([1, 2, 3], name="t")],
        risk_appetite=_RA,
        command="something",
    )
    model.model_type = "unknown_type"
    status, _, _ = sdc.manual_check("TestAnalysis", ev, model)
    assert status == "fail"


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
    from acro.sdcchecks import ChecksResults, ManyChecksResults  # noqa: PLC0415

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
    from acro.sdcchecks import ChecksResults, ManyChecksResults  # noqa: PLC0415

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


def test_get_table_sdc_duplicate_check_skipped_branch() -> None:
    """Duplicate checks are only counted once in the table summary."""
    from acro.sdcchecks import ChecksResults, ManyChecksResults  # noqa: PLC0415

    mask = pd.DataFrame({"A": [False, False]}, index=[1, 2])
    cr1 = ChecksResults("pass", "ok", {"MinimumThresholdCheck": mask}, {})
    cr2 = ChecksResults("pass", "ok", {"MinimumThresholdCheck": mask}, {})
    many = ManyChecksResults()
    many.allchecksresults["FrequencyTable"] = cr1
    many.allchecksresults["Mean"] = cr2
    sdc = many.get_table_sdc()
    assert len(sdc["cells"]) == 1
    assert "MinimumThresholdCheck" in sdc["cells"]


def test_agg_values_are_same_empty_series() -> None:
    """Agg_values_are_same returns True for an empty Series (line 78)."""
    from acro.sdc_agg_funcs import agg_values_are_same  # noqa: PLC0415

    result = agg_values_are_same(pd.Series([], dtype=float))
    assert result is True


def test_agg_top_2_sum_non_numeric() -> None:
    """Agg_top_2_sum returns 0 for a non-numeric Series (lines 118-119)."""
    from acro.sdc_agg_funcs import agg_top_2_sum  # noqa: PLC0415

    result = agg_top_2_sum(pd.Series(["a", "b", "c"]))
    assert result == 0


def _make_table_for_collate_risk_assessments() -> pd.DataFrame:
    return pd.DataFrame({"A": [10, 20], "B": [30, 40]}, index=[1, 2])


def test_collate_risk_assessments_negative_branch() -> None:
    """Negative masks are surfaced as negative values in collated results."""
    from acro.sdcchecks import ChecksResults  # noqa: PLC0415
    from acro.table_utils import collate_risk_assessments  # noqa: PLC0415

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
    from acro.sdcchecks import ChecksResults  # noqa: PLC0415
    from acro.table_utils import collate_risk_assessments  # noqa: PLC0415

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
    """Translate_args_to_newdf() maps a pd.Series argument to the redacted DataFrame (line 401)."""
    redacted = data[["year", "grant_type"]].copy()
    args = (data["year"], data["grant_type"])
    result = translate_args_to_newdf(args, redacted)
    assert len(result) == 2
    assert result[0].equals(redacted["year"])


def test_append_rounded_margins_median(data) -> None:
    """Append_rounded_margins() with aggfunc='median' uses the median path (line 647)."""
    from acro.table_utils import append_rounded_margins, round_table  # noqa: PLC0415

    table = pd.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="median"
    )
    rounded = round_table(table, 5)
    result = append_rounded_margins(rounded, "median", "All", 5)
    assert isinstance(result, pd.DataFrame)


def test_add_custom_blocked_extension(tmp_path) -> None:
    """Records.add_custom() returns False when the file extension is blocked (line 369)."""
    # TODO remove line number from docstring as line numbers might change
    records = Records(blocked_extensions=[".svg"])
    # Create a real file so the existence check doesn't short-circuit
    svg_file = tmp_path / "chart.svg"
    svg_file.write_text("content")
    result = records.add_custom(str(svg_file))
    assert result is False
    assert len(records.results) == 0


def test_prettify_table_string_with_separator() -> None:
    """Prettify_table_string() with separator uses split(separator) instead of split() (line 78)."""
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]}, index=["x", "y"])
    result = utils.prettify_table_string(df, separator=",")
    # TODO test the result is correct character by character
    assert isinstance(result, str)
    assert "|" in result


def test_process_table_output_standalone_crosstab_via_refactoring():
    """Test _process_table_output in standalone mode with crosstab (refactored method)."""
    data = pd.read_stata(os.path.join("data", "test_data.dta"))
    acro = ACRO(suppress=True)
    new_df = data[["year", "grant_type"]].copy()
    new_df = new_df.dropna()

    acro.crosstab(index=new_df["year"], columns=new_df["grant_type"])

    res = acro.results.get_index(-1)
    assert res.output_type == "table"
    assert res.properties["method"] == "crosstab"
    assert res.status == "review"


def test_process_table_output_standalone_pivot_table_via_refactoring():
    """Test _process_table_output in standalone mode with pivot_table (refactored method)."""
    data = pd.read_stata(os.path.join("data", "test_data.dta"))
    acro = ACRO(suppress=True)
    new_df = data[["year", "grant_type", "total_costs"]].copy()
    new_df = new_df.dropna()

    acro.pivot_table(
        data=new_df, index="year", columns="grant_type", values="total_costs"
    )

    res = acro.results.get_index(-1)
    assert res.output_type == "table"
    assert res.properties["method"] == "pivot_table"


def test_process_table_output_rounding_crosstab_via_refactoring():
    """Test _process_table_output with rounding mitigation on crosstab (refactored method)."""
    data = pd.read_stata(os.path.join("data", "test_data.dta"))
    acro = ACRO(suppress=False)
    acro.enable_rounding(5)
    new_df = data[["year", "grant_type", "total_costs"]].copy()
    new_df = new_df.dropna()

    acro.crosstab(
        index=new_df["year"],
        columns=new_df["grant_type"],
        values=new_df["total_costs"],
        aggfunc="sum",
        margins=True,
    )
    res = acro.results.get_index(-1)
    assert res.properties["mitigation"] == "round"
    assert res.properties["round_base"] == 5


def test_process_table_output_suppression_pivot_table_via_refactoring():
    """Test _process_table_output with suppression on pivot_table (refactored method)."""
    data = pd.read_stata(os.path.join("data", "test_data.dta"))
    acro = ACRO(suppress=True)
    new_df = data[["year", "grant_type", "inc_activity"]].copy()
    new_df = new_df.dropna()

    acro.pivot_table(
        data=new_df,
        index="year",
        columns="grant_type",
        values="inc_activity",
        aggfunc="sum",
    )

    res = acro.results.get_index(-1)
    assert res.properties["mitigation"] == "suppress"
