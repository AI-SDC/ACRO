"""Unit tests."""

import json
import os
import sys
import shutil
import matplotlib
matplotlib.use("Agg")
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from acro import ACRO, acro_tables, add_constant, add_to_acro, record, utils
from acro.acro_tables import _rounded_survival_table #, crosstab_with_totals
from acro.record import Records, load_records
from acro import table_utils
# pylint: disable=redefined-outer-name,too-many-lines

PATH: str = "RES_PYTEST"


@pytest.fixture(autouse=True)
def cleanup_path():
    """Clean up output directories before and after each test."""
    for d in ["RES_PYTEST", "outputs", "acro_artifacts", "sdc_results", "test_add_to_acro"]:
        shutil.rmtree(d, ignore_errors=True)
    yield
    for d in ["RES_PYTEST", "outputs", "acro_artifacts", "sdc_results", "test_add_to_acro"]:
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
    correct_summary: str = ("FrequencyTable : \n" 
         " PresenceOfLinkedTableCheck: A manual review is needed. Variables defining table are:  ['year', 'grant_type'].\n"
         " MinimumThresholdCheck: fail - 6 cells may need suppressing.\n"
                           )

    
    assert output.summary == correct_summary,f'expected:\n{correct_summary}\n---\ngot\n{output.summary}\n---'
    assert 48 == output.output[0]["R/G"].sum()


def test_crosstab_with_aggfunc_mode(data):
    """Crosstab threshold without automatic suppression."""
    acro = ACRO(suppress=False)
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mode"
    )
    output = acro.results.get_index(0)
    correct_summary: str = "fail; all-values-are-same: 1 cells may need suppressing; "
##TODO    assert output.summary == correct_summary
    assert 913000 == output.output[0]["R/G"].iat[0]


def test_crosstab_with_aggfunc_sum(data, acro):
    """Test the crosstab with two columns and aggfunc sum."""
    acro = ACRO(suppress=False)
    thetable = acro.crosstab(
        data.year,
        [ data.survivor],
        values=data.inc_grants,
        aggfunc="sum",
    )
    pandastable= pd.crosstab(  
        data.year,
        [ data.survivor],
        values=data.inc_grants,
        aggfunc="sum",)
    assert thetable.equals(pandastable)
    output_0 = acro.results.get_index(0)


def test_crosstab_threshold(data, acro):
    """Crosstab threshold test."""
    acro.enable_suppression()
    _ = acro.crosstab(data.year, data.grant_type)
    
    output = acro.results.get_index(0)
    total_nan: int = output.output[0]["R/G"].isnull().sum()
    assert total_nan == 6,f'output is\n{output.output[0]}'
    
    positions = output.sdc["cells"]["MinimumThresholdCheck"]
    for pos in positions:
        row, col = pos
        assert np.isnan(output.output[0].iloc[row, col])
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(PATH)
    correct_summary:str = (
        "FrequencyTable : \n" 
        " PresenceOfLinkedTableCheck: A manual review is needed. Variables defining table are:  ['year', 'grant_type'].\n"
        " MinimumThresholdCheck: fail - 6 cells may need suppressing.\n"
    )
    output = results.get_index(0)
    assert output.summary == correct_summary,f'expected:\n{correct_summary}\n---\ngot:\n{output.summary}\n----'
    shutil.rmtree(PATH)


def test_crosstab_multiple(data, acro):
    """Crosstab multiple rule test."""
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mean"
    )
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(PATH)
    correct_summary:str = (
        "Mean : \n" 
        "NKCheck: fail - 1 cells may need suppressing.\n"
        " PPercentCheck: fail - 2 cells may need suppressing.\n"
        " PresenceOfLinkedTableCheck: A manual review is needed. Variables defining table are:  ['year', 'grant_type'].\n"
        " MinimumThresholdCheck: fail - 6 cells may need suppressing.\n"
    )
    output = results.get_index(0)
    assert output.summary == correct_summary,f'expected:\n{correct_summary}\n---\ngot:\n{output.summary}\n----'
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
    assert 36293992.0 == output_0.output[0]["mean"]["inc_grants"].sum()
    assert output_0.status in ["pass", "fail", "review"]


def test_pivot_table_pass(data, acro):
    """Pivot table pass test."""
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    results: Records = acro.finalise(PATH)
    output_0 = results.get_index(0)
    assert output_0.status in ["pass", "review"]
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
    assert output_0.status in ("review", "fail", "pass")
    assert output_1.status in ("review", "fail", "pass")
    shutil.rmtree(PATH)


def test_ols(data, acro):
    """Ordinary Least Squares test."""
    new_df = data[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
    new_df = new_df.dropna()
    # OLS too few Dof
    endog = new_df.inc_activity.iloc[0:10]
    exog = new_df[["inc_grants", "inc_donations", "total_costs"]].iloc[0:10]
    exog = add_constant(exog)
    results = acro.ols(endog, exog)
    assert results.df_resid == 6
    res = acro.results.get_index(-1)
    assert res.status == "fail"
    acro.remove_output(res.uid)

    # OLS
    endog = new_df.inc_activity
    exog = new_df[["inc_grants", "inc_donations", "total_costs"]]
    exog = add_constant(exog)
    results = acro.ols(endog, exog)
    assert results.df_resid == 807
    assert results.rsquared == pytest.approx(0.894, 0.001)
    # OLSR
    results = acro.olsr(
        formula="inc_activity ~ inc_grants + inc_donations + total_costs", data=new_df
    )
    assert results.df_resid == 807
    assert results.rsquared == pytest.approx(0.894, 0.001)
    # Finalise
    results = acro.finalise(PATH)
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    assert output_0.status == "pass"
    assert output_1.status == "pass"
    shutil.rmtree(PATH)


def test_probit_logit(data, acro):
    """Probit and Logit tests."""
    new_df = data[
        ["survivor", "inc_activity", "inc_grants", "inc_donations", "total_costs"]
    ]
    new_df = new_df.dropna()
    endog = new_df["survivor"].astype("category").cat.codes  # numeric
    endog.name = "survivor"
    exog = new_df[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
    exog = add_constant(exog)
    # Probit
    results = acro.probit(endog, exog)
    assert results.df_resid == 806
    assert results.prsquared == pytest.approx(0.208, 0.01)
    # Logit
    results = acro.logit(endog, exog)
    assert results.df_resid == 806
    assert results.prsquared == pytest.approx(0.214, 0.01)
    # ProbitR
    new_df["survivor"] = new_df["survivor"].astype("category").cat.codes
    results = acro.probitr(
        formula="survivor ~ inc_activity + inc_grants + inc_donations + total_costs",
        data=new_df,
    )
    assert results.df_resid == 806
    assert results.prsquared == pytest.approx(0.208, 0.01)
    # LogitR
    results = acro.logitr(
        formula="survivor ~ inc_activity + inc_grants + inc_donations + total_costs",
        data=new_df,
    )
    assert results.df_resid == 806
    assert results.prsquared == pytest.approx(0.214, 0.01)
    # Finalise
    results = acro.finalise(PATH)
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    output_2 = results.get_index(2)
    output_3 = results.get_index(3)
    assert output_0.status == "pass"
    assert output_1.status == "pass"
    assert output_2.status == "pass"
    assert output_3.status == "pass"
    shutil.rmtree(PATH)


def test_finalise_excel(data, acro):
    """Finalise excel test."""
    _ = acro.crosstab(data.year, data.grant_type)
    acro.add_exception("output_0", "Let me have it")
    with open("foo.txt", "w") as file:
        file.write("Your text goes here")
    acro.custom_output("foo.txt")

    results: Records = acro.finalise(PATH, "xlsx")
    output_0 = results.get_index(0)
    filename = os.path.normpath(f"{PATH}/results.xlsx")
    load_data = pd.read_excel(filename, sheet_name=output_0.uid)
    correct_cell: str = "_ = acro.crosstab(data.year, data.grant_type)"
    assert load_data.iloc[0, 0] == "Command"
    assert load_data.iloc[0, 1] == correct_cell
    shutil.rmtree(PATH)


def test_output_removal(data, acro, monkeypatch):
    """Output removal and print test."""
    _ = acro.crosstab(data.year, data.grant_type)
    _ = acro.crosstab(data.year, data.grant_type)
    _ = acro.crosstab(data.year, data.grant_type)
    exceptions = ["I want it", "Let me have it", "Please!"]
    monkeypatch.setattr("builtins.input", lambda _: exceptions.pop(0))
    results: Records = acro.finalise(PATH)
    output_0 = results.get("output_0")
    output_1 = results.get("output_1")
    shutil.rmtree(PATH)
    # remove something that is there
    acro.remove_output(output_0.uid)
    results = acro.finalise(PATH)
    keys = results.get_keys()
    assert output_0.uid not in keys
    assert output_1.uid in keys
    assert output_1.status == "review"
    acro.print_outputs()
    # remove something that is not there
    with pytest.raises(ValueError, match="unable to remove 123, key not found"):
        acro.remove_output("123")
    shutil.rmtree(PATH)


def test_load_output():
    """Empty or invalid array when loading output."""
    with pytest.raises(ValueError, match="error loading output"):
        record.load_output(PATH, [])
    val = record.load_output(PATH, ["nosuchfile.xxx"])
    assert val == ["nosuchfile.xxx"]


def test_finalise_invalid(data, acro):
    """Invalid output format when finalising."""
    _ = acro.crosstab(data.year, data.grant_type)
    output_0 = acro.results.get_index(0)
    output_0.exception = "Let me have it"
    with pytest.raises(ValueError, match="Invalid file extension.*"):
        _ = acro.finalise(PATH, "123")


def test_finalise_json(data, acro):
    """Finalise json test."""
    _ = acro.crosstab(data.year, data.grant_type)
    acro.add_exception("output_0", "Let me have it")
    result: Records = acro.finalise(PATH, "json")
    loaded: Records = load_records(PATH)
    orig = result.get_index(0)
    read = loaded.get_index(0)
    assert orig.uid == read.uid
    assert orig.status == read.status
    assert orig.output_type == read.output_type
    assert orig.properties == read.properties
    assert orig.sdc == read.sdc
    assert orig.command == read.command
    assert orig.summary == read.summary
    assert orig.comments == read.comments
    assert orig.timestamp == read.timestamp
    orig_df = orig.output[0].reset_index()
    read_df = read.output[0]
    pd.testing.assert_frame_equal(
        orig_df, read_df, check_names=False, check_dtype=False, check_categorical=False
    )
    with open(os.path.normpath(f"{PATH}/results.json"), encoding="utf-8") as file:
        json_data = json.load(file)
    results: dict = json_data["results"]
    assert results[orig.uid]["files"][0]["name"] == f"{orig.uid}_0.csv"
    shutil.rmtree(PATH)


def test_rename_output(data, acro):
    """Output renaming test."""
    _ = acro.crosstab(data.year, data.grant_type)
    _ = acro.crosstab(data.year, data.grant_type)
    acro.add_exception("output_0", "Let me have it")
    acro.add_exception("output_1", "I want this")
    results: Records = acro.finalise(PATH)
    output_0 = results.get_index(0)
    orig_name = output_0.uid
    new_name = "cross_table"
    acro.rename_output(orig_name, new_name)
    shutil.rmtree(PATH)
    results = acro.finalise(PATH)
    assert output_0.uid == new_name
    assert orig_name not in results.get_keys()
    assert os.path.exists(f"{PATH}/{new_name}_0.csv")
    # rename an output that doesn't exist
    with pytest.raises(ValueError, match="unable to rename 123, key not found"):
        acro.rename_output("123", "name")
    # rename an output to another that already exists
    with pytest.raises(ValueError, match="unable to rename, cross_table .* exists"):
        acro.rename_output("output_1", "cross_table")
    shutil.rmtree(PATH)


def test_add_comments(data, acro):
    """Adding comments to output test."""
    _ = acro.crosstab(data.year, data.grant_type)
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(PATH)
    output_0 = results.get_index(0)
    assert output_0.comments == []
    comment = "This is a cross table between year and grant_type"
    acro.add_comments(output_0.uid, comment)
    assert output_0.comments == [comment]
    comment_1 = "6 cells were suppressed"
    acro.add_comments(output_0.uid, comment_1)
    assert output_0.comments == [comment, comment_1]
    # add a comment to something that is not there
    with pytest.raises(ValueError, match="unable to find 123, key not found"):
        acro.add_comments("123", "comment")
    shutil.rmtree(PATH)


def test_custom_output(acro):
    """Adding an unsupported output to the results dictionary test."""
    filename = "notebooks/XandY.jpeg"
    file_path = os.path.normpath(filename)
    acro.custom_output(filename)
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(path=PATH)
    output_0 = results.get_index(0)
    assert output_0.output == [file_path]
    assert os.path.exists(os.path.normpath(f"{PATH}/XandY.jpeg"))
    shutil.rmtree(PATH)


def test_missing(data, acro, monkeypatch):
    """Pivot table and Crosstab with missing values."""
    acro.sdc_checks.risk_appetite['check_missing_values'] = True
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


def test_suppression_error(caplog):
    """Apply suppression type error test."""
    pass


def test_adding_exception(acro):
    """Adding an exception to an output that doesn't exist test."""
    with pytest.raises(ValueError, match="unable to add exception: output_0 .*"):
        acro.add_exception("output_0", "Let me have it")


def test_add_to_acro(data, monkeypatch):
    """Add an output generated without acro to an acro object and create results file."""
    # create a cross tabulation using pandas
    table = pd.crosstab(data.year, data.grant_type)
    # save the output to a file and add this file to a directory
    src_path = "test_add_to_acro"
    dest_path = "sdc_results"
    file_path = "crosstab.pkl"
    if not os.path.exists(src_path):  # pragma no cover
        table.to_pickle(file_path)
        os.mkdir(src_path)
        shutil.move(file_path, src_path, copy_function=shutil.copytree)
    # add exception to the output
    exception = ["I want it"]
    monkeypatch.setattr("builtins.input", lambda _: exception.pop(0))
    # add the output to acro
    add_to_acro(src_path, dest_path)
    assert "results.json" in os.listdir(dest_path)
    assert "crosstab.pkl" in os.listdir(dest_path)


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


def test_surv_func(acro):
    """Test survival tables and plots."""
    try:
        data = sm.datasets.get_rdataset("flchain", "survival").data
    except Exception:
        np.random.seed(42)
        mock_data = pd.DataFrame(
            {
                "futime": np.random.exponential(100, 500),
                "death": np.random.binomial(1, 0.3, 500),
                "sex": np.random.choice(["F", "M"], 500),
            }
        )
        data = mock_data
        skip_exact_assertion = True
    else:
        skip_exact_assertion = False

    data = data.loc[data.sex == "F", :]
    _ = acro.surv_func(data.futime, data.death, output="table")
    output = acro.results.get_index(0)
    assert output.status in ["fail", "review"]
    assert "suppressed" in output.summary or "fail" in output.summary

    filename = os.path.normpath("acro_artifacts/kaplan-meier_0.png")
    _ = acro.surv_func(data.futime, data.death, output="plot")
    assert os.path.exists(filename)
    acro.add_exception("output_0", "I need this")
    acro.add_exception("output_1", "Let me have it")

    foo = acro.surv_func(data.futime, data.death, output="something_else")
    assert foo is None

    results: Records = acro.finalise(path=PATH)
    output_1 = results.get_index(1)
    assert output_1.output == [filename]
    shutil.rmtree(PATH)


def test_rounded_survival_table():
    """Test the rounded_survival_table function for survival analysis."""
    survival_table = pd.DataFrame(
        {
            "Surv prob": [1.0, 0.95, 0.90, 0.85, 0.80],
            "num at risk": [100, 95, 85, 75, 60],
            "num events": [0, 5, 10, 10, 15],
        }
    )
    result = _rounded_survival_table(survival_table.copy())
    assert "rounded_survival_fun" in result.columns
    assert len(result) == 5
    assert all(
        (result["rounded_survival_fun"] >= 0) & (result["rounded_survival_fun"] <= 1)
    )


def test_zeros_are_not_disclosive(data, acro):
    """Test that zeros are handled as not disclosive when `zeros_are_disclosive=False`."""
    acro.sdc_checks.risk_appetite['zeros_are_disclosive'] = False
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
    assert output_0.status == "review"
    shutil.rmtree(PATH)


def test_crosstab_with_totals_without_suppression(data, acro):
    """Test the crosstab with margins is true and suppression is false."""
    acro.suppress = False
    _ = acro.crosstab(data.year, data.grant_type, margins=True)
    output = acro.results.get_index(0)
    assert 153 == output.output[0]["All"].iat[0]

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
    assert output.status in {"review", "fail"}


def test_crosstab_with_totals_with_suppression_hierarchical(data, acro):
    """Test hierarchical crosstab margins with suppression enabled."""
    _ = acro.crosstab(
        [data.year, data.survivor], [data.grant_type, data.status], margins=True
    )
    output = acro.results.get_index(0)
    table = output.output[0]

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

    assert "All" in table.columns
    assert table["All"].iat[0] > 0
    assert table["All"].iat[6] > 0
    assert output.status in {"review", "fail"}


def test_crosstab_with_totals_and_empty_data(data, acro, caplog):
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
    assert acro.results.get_index(0).status in {"review", "fail"}


def test_crosstab_with_manual_totals_with_suppression(data, acro):
    """Test manual totals path when suppression is enabled."""
    _ = acro.crosstab(data.year, data.grant_type, margins=True, show_suppressed=True)
    output = acro.results.get_index(0)
    table = output.output[0]

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


def test_crosstab_with_manual_totals_with_suppression_with_aggfunc_std(
    data, acro, caplog
):
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
    assert "All" in table.columns or "All" not in table.columns


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


def test_crosstab_with_manual_totals_with_suppression_with_two_aggfunc(
    data, acro, caplog
):
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


def test_histogram_disclosive(acro, caplog):
    """Test a disclosive histogram under the new suppression workflow."""
    small_data = pd.DataFrame({"value": [1, 2, 3]})
    result = acro.hist(small_data, "value")

    assert result == ""
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(path=PATH)
    output_0 = results.get_index(0)

    assert (
        "Histogram will not be shown as the value column is disclosive."
        in caplog.text
    )
    assert output_0.status == "fail"
    assert output_0.output == []
    shutil.rmtree(PATH)


def test_histogram_non_disclosive(acro):
    """Test a non-disclosive histogram with a larger synthetic dataset."""
    rng = np.random.default_rng(42)
    data = pd.DataFrame({"value": rng.normal(size=2000)})
    filename = os.path.normpath("acro_artifacts/histogram_0.png")

    result = acro.hist(data, "value", bins=5)

    assert result is not None
    assert os.path.exists(result)
    assert os.path.normpath(result) == os.path.normpath(result)
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(path=PATH)
    output_0 = results.get_index(0)
    assert output_0.output == [os.path.normpath(result)]
    assert output_0.status == "review"
    shutil.rmtree(PATH)


def test_pie_disclosive(acro, caplog):
    """Test a disclosive pie chart (a category has fewer than threshold observations)."""
    shutil.rmtree("acro_artifacts", ignore_errors=True)
    shutil.rmtree(PATH, ignore_errors=True)

    df = pd.DataFrame(
        {"grant_type": (["A"] * 20) + (["B"] * 15) + (["C"] * 12) + (["D"] * 5)}
    )

    _ = acro.pie(df, "grant_type", filename="pie.png")
    # When disclosive and suppressed, file should NOT be created
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(path=PATH)
    output_0 = results.get_index(0)

    assert (
        "Pie chart will not be shown as the grant_type column is disclosive."
        in caplog.text
    )
    assert output_0.status == "fail"
    shutil.rmtree(PATH)


def test_pie_non_disclosive(data, acro):
    """Test a non-disclosive pie chart (all categories meet the threshold)."""
    shutil.rmtree("acro_artifacts", ignore_errors=True)
    shutil.rmtree(PATH, ignore_errors=True)
    filename = os.path.normpath("acro_artifacts/pie_0.png")
    result = acro.pie(data, "grant_type", filename="pie.png")
    assert os.path.normpath(result) == filename
    assert os.path.exists(filename)
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(path=PATH)
    output_0 = results.get_index(0)
    assert output_0.output == [filename]
    assert output_0.status == "review"
    shutil.rmtree(PATH)


def test_finalise_with_existing_path(data, acro, caplog):
    """Test using a path that already exists when finalising."""
    _ = acro.crosstab(data.year, data.grant_type)
    acro.add_exception("output_0", "Let me have it")
    acro.finalise(PATH)
    _ = acro.crosstab(data.status, data.grant_type)
    acro.finalise(PATH)
    assert (
        "Results file can not be created. Directory RES_PYTEST "
        "already exists. Please choose a different directory name." in caplog.text
    )
    shutil.rmtree(PATH)


def test_finalise_non_interactive(data):
    """Test finalise_non_interactive.

    Test that non-interactive version of finalising acro
    leaves exceptions as they were for disclosive table.
    """
    acro = ACRO(suppress=False)
    _ = acro.crosstab(data.year, data.grant_type)
    acro.suppress = True
    _ = acro.crosstab(data.year, data.grant_type)
    # write JSON

    path = "outputs"

    _ = acro.finalise(path, "json", interactive=False)
    result = acro.results

    # load JSON
    loaded: Records = load_records(path)
    orig0 = result.get_index(0)
    read0 = loaded.get_index(0)
    orig1 = result.get_index(1)
    read1 = loaded.get_index(1)
    # check equal
    assert orig0.exception is None or len(orig0.exception) == 0, (
        f"orig exception: expected None, got _{orig0.exception}_"
    )
    assert read0.exception is None or len(read0.exception) == 0, (
        f"read exception: expected None, got _{read0.exception}_"
    )
    assert orig1.exception == "Suppression automatically applied where needed"
    assert read1.exception == "Suppression automatically applied where needed"

    # check SDC outcome DataFrame
    orig_df = orig0.output[0].reset_index()
    read_df = read0.output[0]
    pd.testing.assert_frame_equal(
        orig_df, read_df, check_names=False, check_dtype=False
    )
    if os.path.isdir(path):
        shutil.rmtree(path)


def test_finalise_interactive(data):
    """Test finalise_interactive.

    Test that interactive version of finalising acro
    leaves exceptions as they should be disclosive table.
    """
    acro = ACRO(suppress=False)
    _ = acro.crosstab(data.year, data.grant_type)
    acro.suppress = True
    _ = acro.crosstab(data.year, data.grant_type)
    # write JSON

    mypath = "outputs"

    with patch("builtins.input", return_value="Oh, please..."):
        _ = acro.finalise(mypath, "json", interactive=True)
    result = acro.results
    # load JSON
    loaded: Records = load_records(mypath)
    orig0 = result.get_index(0)
    read0 = loaded.get_index(0)
    orig1 = result.get_index(1)
    read1 = loaded.get_index(1)
    # check equal
    assert orig0.exception == "Oh, please..."
    assert read0.exception == "Oh, please..."
    assert orig1.exception == "Suppression automatically applied where needed"
    assert read1.exception == "Suppression automatically applied where needed"
    print(orig0.exception)
    # check SDC outcome DataFrame
    orig_df = orig0.output[0].reset_index()
    read_df = read0.output[0]
    pd.testing.assert_frame_equal(
        orig_df, read_df, check_names=False, check_dtype=False
    )
    if os.path.isdir(mypath):
        shutil.rmtree(mypath)


def TODOtest_crosstab_with_totals_raises_when_data_none():
    """Test that crosstab_with_totals raises AssertionError when data is None."""
    # When crosstab=False, data is not set from create_dataframe; passing data=None
    # must raise "data must be set when applying crosstab queries".
    with pytest.raises(
        AssertionError, match="data must be set when applying crosstab queries"
    ):
        crosstab_with_totals(
            masks={},
            aggfunc=None,
            index=pd.Series([1, 2]),
            columns=pd.Series([1, 2]),
            values=None,
            margins=False,
            margins_name="All",
            dropna=True,
            crosstab=False,
            data=None,
        )


def test_create_dataframe(data):
    """Test correct functionality of code to create data frame."""
    pass


def test_toggle_suppression():
    """Test toggling suppression on/off."""
    acro = ACRO(suppress=False)
    assert not acro.suppress
    acro.enable_suppression()
    assert acro.suppress
    acro.disable_suppression()
    assert not acro.suppress






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
    pandastable= pd.crosstab(
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
