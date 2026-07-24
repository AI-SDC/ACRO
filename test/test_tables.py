"""Unit tests."""

from asyncio.log import logger
import os
import shutil

import matplotlib as mpl

mpl.use("Agg")

import numpy as np
import pandas as pd
import scipy.stats as stats
import pytest

from acro import (
    ACRO,
    utils,
)
from acro.record import Records
from acro.sdcchecks import SDCChecks, SDCEvidence
from acro.table_utils import (
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
    acroversion= acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mode"
    )
    output = acro.results.get_index(0)
    correct_summary: str = ("ModeCalculation : \n"
                            "PresenceOfLinkedTableCheck:"
                            " A manual review is needed. Variables defining table are:  ['year', 'grant_type'].\n"
    )
    assert output.summary == correct_summary
    pandas_version= pd.crosstab(data.year, data.grant_type, values=data.inc_grants, aggfunc=pd.Series.mode)
    logger.info(f"output.output[0]is {output.output[0]}")
    #assert output.output[0].equals(pandas_version)
    assert acroversion.equals(pandas_version)
    
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

    #six cells should be suppressed
    total_nan: int = output.output[0]["R/G"].isnull().sum()
    assert total_nan == 6, f"output is\n{output.output[0]}"

    positions = output.sdc["cells"]["MinimumThresholdCheck"]
    for pos in positions:
        row, col = pos
        assert np.isnan(output.output[0].iloc[row, col])
    #results: Records = acro.finalise(PATH)
    correct_summary: str = (
        "FrequencyTable : \n"
        " PresenceOfLinkedTableCheck: A manual review is needed. Variables defining table are:  ['year', 'grant_type'].\n"
        " MinimumThresholdCheck: fail - 6 cells may need suppressing.\n"
    )
    #output = results.get_index(0)
    assert output.summary == correct_summary, (
        f"expected:\n{correct_summary}\n---\ngot:\n{output.summary}\n----"
    )
    assert output.status =="review"

    # TODO check appropriate exception added saying suppression has been applied
    #shutil.rmtree(PATH)


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


def test_tables_negatives(data, acro):
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
    correct_summary: str = "review; negative values found"
    assert output_0.summary == correct_summary
    assert output_1.summary == correct_summary
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
    assert output_0.status =="pass"


def test_pivot_table_pass(data, acro):
    """Pivot table pass test."""
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    results: Records = acro.finalise(PATH)
    output_0 = results.get_index(0)
    assert output_0.status =="pass"
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
    correct_summary: str = (
        "review; threshold: 14 cells suppressed; "
        "p-ratio: 4 cells suppressed; nk-rule: 2 cells suppressed; "
    )
    output_0 = results.get_index(0)
    assert output_0.summary == correct_summary
    #TODO check exeption status 
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
    assert output_0.status =='fail'
    assert output_1.status =='fail'
    shutil.rmtree(PATH)


def test_tables_missing(data, acro, monkeypatch):
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
    correct_summary: str = "review; missing values found"
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    assert output_0.summary == correct_summary
    assert output_1.summary == correct_summary
    assert output_0.exception == "I want it"
    assert output_1.exception == "Let me have it"
    shutil.rmtree(PATH)

def test_crosstab_multiple_aggregate_function_no_suppression(data, acro):
    """Crosstab with multiple agg funcs."""
    acro = ACRO(suppress=False)
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc=["mean", "std"]
    )
    output = acro.results.get_index(0)
    correct_summary: str = (
        "fail; threshold: 14 cells may need suppressing;"
        " p-ratio: 4 cells may need suppressing; "
        "nk-rule: 2 cells may need suppressing; "
    )
    assert output.summary == correct_summary, (
        f"\n{output.summary}\n should be \n{correct_summary}\n"
    )
    assert output.status == "fail"
    correctval = 97383496.0
    assert output.output[0]["mean"]["R/G"].sum() == correctval

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



@pytest.mark.skip(reason="Not yet implemented")
def test_suppression_error():
    """Apply suppression type error test."""


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
    correct_summary: str = (
        "review; threshold: 14 cells suppressed; "
        "p-ratio: 2 cells suppressed; nk-rule: 2 cells suppressed; "
    )
    assert output_0.summary == correct_summary
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


def test_crosstab_with_totals_and_empty_data(data, acro,caplog):
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
    assert (
        "All the cells in this data are disclosive. Thus suppression can not be applied"
        in caplog.text
    )
    assert acro.results.get_index(0).status in {"review", "fail"}


def REDO_test_crosstab_with_manual_totals_with_suppression(data, acro):
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

#don't think the below are needed as we no longer do manually recalculation of totals
# TODO rewrite once we have the redcted adta set available 
def REDO_test_crosstab_with_manual_totals_with_suppression_hierarchical(data, acro):
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


def REDO_test_crosstab_with_manual_totals_with_suppression_with_aggfunc_mean(data, acro):
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


def REDO_test_hierarchical_crosstab_with_manual_totals_with_mean(data, acro):
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


def REDO_test_crosstab_with_manual_totals_with_suppression_with_aggfunc_std(data, acro):
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


def REDO_test_pivot_table_with_totals_with_suppression(data, acro):
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




def REDO_test_crosstab_with_totals_with_suppression_with_two_aggfuncs(data, acro):
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


def REDO_test_crosstab_with_totals_with_suppression_with_two_aggfuncs_hierarchical(
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


def REDO_test_crosstab_with_manual_totals_with_suppression_with_two_aggfunc(data, acro):
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












def test_pivot_table_no_values_raises(data):
    """Pivot tables without values raise a helpful error."""
    acro_obj = ACRO(suppress=False)
    # TODO make match more specific about message
    with pytest.raises(ValueError, match="values column"):
        acro_obj.pivot_table(data, index=["grant_type"])


def test_pivot_table_multiple_values_raises(data):
    """Pivot tables with multiple values raise a helpful error."""
    acro_obj = ACRO(suppress=False)
    # TODO make tes more specific about message
    with pytest.raises(ValueError, match="multiple values"):
        acro_obj.pivot_table(
            data,
            index=["grant_type"],
            values=["inc_grants", "inc_activity"],
            aggfunc="mean",
        )


def test_pivot_table_aggfunc_mode(data):
    """Pivot_table() with aggfunc='mode' uses the agg_mode helper (lines 477-478)."""
    # TODO edit doctstring to remove references to line numbers which can change
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
    # TODO edit doctstring to remove references to line numbers which can change
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
    # TODO edit doctstring to remove references to line numbers which can change
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
    # TODO check that the values are rounded to nearest 5


















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
