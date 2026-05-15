"""Unit tests."""

import json
import logging
import os
import shutil
from unittest.mock import patch

import matplotlib as mpl

mpl.use("Agg")

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from acro import ACRO, acro_tables, add_constant, add_to_acro, record, utils
from acro.acro_regression import (
    _get_endog_exog_variables,
    _get_formula_variables,
)
from acro.acro_tables import _rounded_survival_table, crosstab_with_totals
from acro.constants import ARTIFACTS_DIR
from acro.record import Records, load_records

PATH: str = "RES_PYTEST"


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
    # Test simple string without spaces (no backticks added)
    assert acro_tables.add_backticks("foo") == "foo"

    # Test string with spaces (backticks should be added)
    assert acro_tables.add_backticks("foo bar") == "`foo bar`"

    # Test string already with backticks (no change)
    assert acro_tables.add_backticks("`foo bar`") == "`foo bar`"

    # Test multiple spaces
    assert acro_tables.add_backticks("foo bar baz") == "`foo bar baz`"


def test_crosstab_with_spaces_in_variable_names(data, acro):
    """Test crosstab with spaces in column names (Issue #305)."""
    # Create a test dataframe with a column name containing spaces
    test_data = data.copy()
    test_data["grant type with spaces"] = test_data["grant_type"]
    test_data["year of study"] = test_data["year"]

    # This should handle spaces in variable names correctly
    # first check is that it behaves the same as pandas without suppression
    acro.suppress = False
    pandas_nospace_version = pd.crosstab(data["year"], data["grant_type"], margins=True)
    acro_with_spaces_version = acro.crosstab(
        test_data["year of study"], test_data["grant type with spaces"], margins=True
    )
    assert (
        acro_with_spaces_version.to_numpy() == pandas_nospace_version.to_numpy()
    ).all()
    # Verify that suppression was not applied in this case
    assert acro.results.get_index(-1).status == "fail"

    # Verify the crosstab was created successfully

    # turn suppression back on, run rest of checks
    acro.suppress = True
    result = acro.crosstab(
        test_data["year of study"], test_data["grant type with spaces"], margins=True
    )
    assert isinstance(result, pd.DataFrame)
    assert not result.empty

    # Verify that suppression was applied in second case
    assert acro.results.get_index(-1).status == "review"


def test_crosstab_without_suppression(data):
    """Crosstab threshold without automatic suppression."""
    acro = ACRO(suppress=False)
    _ = acro.crosstab(data.year, data.grant_type)
    output = acro.results.get_index(0)
    correct_summary: str = "fail; threshold: 6 cells may need suppressing; "
    assert output.summary == correct_summary
    assert 48 == output.output[0]["R/G"].sum()


def test_crosstab_with_aggfunc_mode(data):
    """Crosstab threshold without automatic suppression."""
    acro = ACRO(suppress=False)
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mode"
    )
    output = acro.results.get_index(0)
    correct_summary: str = "fail; all-values-are-same: 1 cells may need suppressing; "
    assert output.summary == correct_summary
    assert 913000 == output.output[0]["R/G"].iat[0]


def test_crosstab_with_aggfunc_sum(data, acro):
    """Test the crosstab with two columns and aggfunc sum."""
    acro = ACRO(suppress=False)
    _ = acro.crosstab(
        data.year,
        [data.grant_type, data.survivor],
        values=data.inc_grants,
        aggfunc="sum",
    )
    _ = acro.crosstab(
        [data.grant_type, data.survivor],
        data.year,
        values=data.inc_grants,
        aggfunc="sum",
    )
    acro.add_exception("output_0", "Let me have it")
    acro.add_exception("output_1", "I need this output")
    results: Records = acro.finalise(PATH)
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    comment_0 = (
        "Empty columns: ('N', 'Dead in 2015'), ('R/G', 'Dead in 2015') were deleted."
    )
    comment_1 = (
        "Empty rows: ('N', 'Dead in 2015'), ('R/G', 'Dead in 2015') were deleted."
    )
    assert output_0.comments == [comment_0]
    assert output_1.comments == [comment_1]
    shutil.rmtree(PATH)


def test_crosstab_threshold(data, acro):
    """Crosstab threshold test."""
    _ = acro.crosstab(data.year, data.grant_type)
    output = acro.results.get_index(0)
    total_nan: int = output.output[0]["R/G"].isnull().sum()
    assert total_nan == 6
    positions = output.sdc["cells"]["threshold"]
    for pos in positions:
        row, col = pos
        assert np.isnan(output.output[0].iloc[row, col])
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(PATH)
    correct_summary: str = "review; threshold: 6 cells suppressed; "
    output = results.get_index(0)
    assert output.summary == correct_summary
    shutil.rmtree(PATH)


def test_crosstab_multiple(data, acro):
    """Crosstab multiple rule test."""
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mean"
    )
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(PATH)
    correct_summary: str = (
        "review; threshold: 7 cells suppressed; p-ratio: 2 cells suppressed; "
        "nk-rule: 1 cells suppressed; "
    )
    output = results.get_index(0)
    assert output.summary == correct_summary
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
    correct_summary: str = "review; negative values found"
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    assert output_0.summary == correct_summary
    assert output_1.summary == correct_summary
    shutil.rmtree(PATH)


def test_pivot_table_without_suppression(data):
    """Pivot table without automatic suppression."""
    acro = ACRO(suppress=False)
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    output_0 = acro.results.get_index(0)
    assert 36293992.0 == output_0.output[0]["mean"]["inc_grants"].sum()
    assert "pass" == output_0.summary


def test_pivot_table_pass(data, acro):
    """Pivot table pass test."""
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    results: Records = acro.finalise(PATH)
    correct_summary: str = "pass"
    output_0 = results.get_index(0)
    assert output_0.summary == correct_summary
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
    correct_summary: str = (
        "review; threshold: 14 cells suppressed; "
        "p-ratio: 4 cells suppressed; nk-rule: 2 cells suppressed; "
    )
    output_0 = results.get_index(0)
    assert output_0.summary == correct_summary
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
    comment_0 = (
        "Empty columns: ('N', 'Dead in 2015'), ('R/G', 'Dead in 2015') were deleted."
    )
    comment_1 = (
        "Empty rows: ('N', 'Dead in 2015'), ('R/G', 'Dead in 2015') were deleted."
    )
    assert output_0.comments == [comment_0]
    assert output_1.comments == [comment_1]
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
    summary = res.summary.split(";")
    assert summary[0] == "fail"
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
    correct_summary: str = "pass; dof=807.0 >= 10"
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    assert output_0.summary == correct_summary
    assert output_1.summary == correct_summary
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
    correct_summary: str = "pass; dof=806.0 >= 10"
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    output_2 = results.get_index(2)
    output_3 = results.get_index(3)
    assert output_0.summary == correct_summary
    assert output_1.summary == correct_summary
    assert output_2.summary == correct_summary
    assert output_3.summary == correct_summary
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
    correct_summary: str = "review; threshold: 6 cells suppressed; "
    keys = results.get_keys()
    assert output_0.uid not in keys
    assert output_1.uid in keys
    assert output_1.summary == correct_summary
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
    # write JSON
    result: Records = acro.finalise(PATH, "json")
    # load JSON
    loaded: Records = load_records(PATH)
    orig = result.get_index(0)
    read = loaded.get_index(0)
    print("*****************************")
    print(orig)
    print("*****************************")
    print(read)
    print("*****************************")
    # check equal
    assert orig.uid == read.uid
    assert orig.status == read.status
    assert orig.output_type == read.output_type
    assert orig.properties == read.properties
    assert orig.sdc == read.sdc
    assert orig.command == read.command
    assert orig.summary == read.summary
    assert orig.comments == read.comments
    assert orig.timestamp == read.timestamp
    # check SDC outcome DataFrame
    orig_df = orig.output[0].reset_index()
    read_df = read.output[0]
    pd.testing.assert_frame_equal(
        orig_df, read_df, check_names=False, check_dtype=False
    )
    # test reading JSON
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


def test_blocked_extension(acro, tmp_path):
    """Test that blocked file extensions are rejected in custom output."""
    # create temporary files with blocked extensions
    svg_file = tmp_path / "test.svg"
    svg_file.write_text("<svg></svg>")
    gph_file = tmp_path / "test.gph"
    gph_file.write_text("data")

    # blocked extensions should be rejected
    acro.custom_output(str(svg_file))
    acro.custom_output(str(gph_file))
    assert len(acro.results.results) == 0

    # allowed extensions should be accepted
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("hello")
    acro.custom_output(str(txt_file))
    assert len(acro.results.results) == 1

    # case-insensitive check
    svg_upper = tmp_path / "test.SVG"
    svg_upper.write_text("<svg></svg>")
    acro.custom_output(str(svg_upper))
    assert len(acro.results.results) == 1


def test_blocked_extension_hist(data, acro):
    """Test that blocked file extensions are rejected for histograms."""
    result = acro.hist(data, "inc_grants", bins=1, filename="hist.svg")
    assert result is None
    assert len(acro.results.results) == 0


def test_blocked_extension_pie(data, acro):
    """Test that blocked file extensions are rejected for pie charts."""
    result = acro.pie(data, "grant_type", filename="pie.svg")
    assert result is None
    assert len(acro.results.results) == 0


def test_blocked_extension_survival(acro):
    """Test that blocked file extensions are rejected for survival plots."""
    result = acro.survival_plot(
        survival_table=pd.DataFrame(),
        survival_func=None,
        filename="surv.svg",
        status="pass",
        sdc={},
        command="test",
        summary="test",
    )
    assert result is None
    assert len(acro.results.results) == 0


def test_missing(data, acro, monkeypatch):
    """Pivot table and Crosstab with negative values."""
    acro_tables.CHECK_MISSING_VALUES = True
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


def test_suppression_error(caplog):
    """Apply suppression type error test."""
    table_data = {"col1": [1, 2], "col2": [3, 4]}
    mask_data = {"col1": [np.nan, True], "col2": [True, True]}
    table = pd.DataFrame(data=table_data)
    masks = {"test": pd.DataFrame(data=mask_data)}
    acro_tables.apply_suppression(table, masks)
    assert "problem mask test is not binary" in caplog.text


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
    if os.path.exists(src_path):
        shutil.rmtree(src_path)
    os.mkdir(src_path)
    table.to_pickle(os.path.join(src_path, file_path))
    if os.path.exists(dest_path):
        shutil.rmtree(dest_path)
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
    # Load real data but with fallback to mock if network fails
    try:
        data = sm.datasets.get_rdataset("flchain", "survival").data
    except Exception:
        # Fallback to mock data if network is unavailable
        np.random.seed(42)
        mock_data = pd.DataFrame(
            {
                "futime": np.random.exponential(100, 500),
                "death": np.random.binomial(1, 0.3, 500),
                "sex": np.random.choice(["F", "M"], 500),
            }
        )
        data = mock_data
        # Skip the exact assertion when using mock data
        skip_exact_assertion = True
    else:
        skip_exact_assertion = False

    data = data.loc[data.sex == "F", :]
    # table
    _ = acro.surv_func(data.futime, data.death, output="table")
    output = acro.results.get_index(0)
    correct_summary: str = "review; threshold: 3864 cells suppressed; "
    assert output.summary == correct_summary

    if not skip_exact_assertion:
        assert output.summary == correct_summary
    else:
        # Just verify the output contains "fail" and "cells suppressed"
        assert "fail" in output.summary
        assert "cells suppressed" in output.summary

    # plot
    filename = os.path.normpath(f"{ARTIFACTS_DIR}/kaplan-meier_0.png")
    _ = acro.surv_func(data.futime, data.death, output="plot")
    assert os.path.exists(filename)
    acro.add_exception("output_0", "I need this")
    acro.add_exception("output_1", "Let me have it")

    # neither table nor plot
    foo = acro.surv_func(data.futime, data.death, output="something_else")
    assert foo is None

    results: Records = acro.finalise(path=PATH)
    output_1 = results.get_index(1)
    assert output_1.output == [filename]
    shutil.rmtree(PATH)


def test_rounded_survival_table():
    """Test the rounded_survival_table function for survival analysis."""
    # Create a minimal survival table with required columns
    survival_table = pd.DataFrame(
        {
            "Surv prob": [1.0, 0.95, 0.90, 0.85, 0.80],
            "num at risk": [100, 95, 85, 75, 60],
            "num events": [0, 5, 10, 10, 15],
        }
    )

    # Apply rounded_survival_table
    result = _rounded_survival_table(survival_table.copy())

    # Check that it has the rounded_survival_fun column
    assert "rounded_survival_fun" in result.columns
    assert len(result) == 5

    # Check that values are reasonable (between 0 and 1)
    assert all(
        (result["rounded_survival_fun"] >= 0) & (result["rounded_survival_fun"] <= 1)
    )


def test_zeros_are_not_disclosive(data, acro):
    """Test that zeros are handled as not disclosive when `zeros_are_disclosive=False`."""
    acro_tables.ZEROS_ARE_DISCLOSIVE = False
    _ = acro.pivot_table(
        data,
        index=["grant_type"],
        columns=["year"],
        values=["inc_grants"],
        aggfunc=["mean", "std"],
    )
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(PATH)
    correct_summary: str = (
        "review; threshold: 14 cells suppressed; "
        "p-ratio: 2 cells suppressed; nk-rule: 2 cells suppressed; "
    )
    output_0 = results.get_index(0)
    assert output_0.summary == correct_summary
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
    """Test the crosstab with both margins and suppression are true."""
    _ = acro.crosstab(data.year, data.grant_type, margins=True)
    output = acro.results.get_index(0)
    assert 145 == output.output[0]["All"].iat[0]

    total_rows = output.output[0].iloc[-1, 0:3].sum()
    total_cols = output.output[0].loc[2010:2015, "All"].sum()
    assert 870 == total_cols == total_rows == output.output[0]["All"].iat[6]
    assert "R/G" not in output.output[0].columns


def test_crosstab_with_totals_with_suppression_hierarchical(data, acro):
    """Test the crosstab with both margins and suppression are true."""
    _ = acro.crosstab(
        [data.year, data.survivor], [data.grant_type, data.status], margins=True
    )
    output = acro.results.get_index(0)
    assert 47 == output.output[0]["All"].iat[0]

    total_rows = (output.output[0].loc[("All", ""), :].sum()) - output.output[0][
        "All"
    ].iat[12]
    total_cols = (output.output[0].loc[:, "All"].sum()) - output.output[0]["All"].iat[
        12
    ]
    assert total_cols == total_rows == output.output[0]["All"].iat[12] == 852
    assert ("G", "dead") not in output.output[0].columns


def test_crosstab_with_totals_with_suppression_with_mean(data, acro):
    """Test the crosstab with both margins and suppression are true and with aggfunc mean."""
    _ = acro.crosstab(
        data.year,
        data.grant_type,
        values=data.inc_grants,
        aggfunc="mean",
        margins=True,
    )
    output = acro.results.get_index(0)
    assert 8689781 == output.output[0]["All"].iat[0]
    assert 5425170.5 == output.output[0]["All"].iat[6]
    assert "R/G" not in output.output[0].columns


def test_crosstab_with_totals_and_empty_data(data, acro, caplog):
    """Test crosstab when both margins and suppression are true with a disclosive dataset."""
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
    assert (
        "All the cells in this data are disclosive. Thus suppression can not be applied"
        in caplog.text
    )


def test_crosstab_with_manual_totals_with_suppression(data, acro):
    """Test crosstab when margins and suppression are true with the total manual function."""
    _ = acro.crosstab(data.year, data.grant_type, margins=True, show_suppressed=True)
    output = acro.results.get_index(0)
    assert 145 == output.output[0]["All"].iat[0]

    total_rows = output.output[0].iloc[-1, 0:4].sum()
    total_cols = output.output[0].loc[2010:2015, "All"].sum()
    assert 870 == total_cols == total_rows == output.output[0]["All"].iat[6]
    assert "R/G" in output.output[0].columns
    assert np.isnan(output.output[0]["R/G"].iat[0])


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
    assert 47 == output.output[0]["All"].iat[0]

    total_rows = (output.output[0].loc[("All", ""), :].sum()) - output.output[0][
        "All"
    ].iat[12]
    total_cols = (output.output[0].loc[:, "All"].sum()) - output.output[0]["All"].iat[
        12
    ]
    assert total_cols == total_rows == output.output[0]["All"].iat[12] == 852
    assert ("G", "dead") in output.output[0].columns
    assert np.isnan(output.output[0][("G", "dead")].iat[0])


def test_crosstab_with_manual_totals_with_suppression_with_aggfunc_mean(data, acro):
    """Test crosstab.

    Tests the crosstab with both margins and suppression are true and with
    aggfunc mean while using the total manual function.
    """
    _ = acro.crosstab(
        data.year,
        data.grant_type,
        values=data.inc_grants,
        aggfunc="mean",
        margins=True,
        show_suppressed=True,
    )
    output = acro.results.get_index(0)
    assert 8689780 == round(output.output[0]["All"].iat[0])
    assert 5425170 == round(output.output[0]["All"].iat[6])
    assert "R/G" in output.output[0].columns
    assert np.isnan(output.output[0]["R/G"].iat[0])


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
    assert 1385162 == round(output.output[0]["All"].iat[0])
    assert 5434959 == round(output.output[0]["All"].iat[12])
    assert ("G", "Dead in 2015") in output.output[0].columns
    assert np.isnan(output.output[0][("G", "Dead in 2015")].iat[0])


def test_crosstab_with_manual_totals_with_suppression_with_aggfunc_std(
    data, acro, caplog
):
    """Test crosstab.

    Test the crosstab with both margins and suppression are true and with
    aggfunc std while using the total manual function.
    """
    _ = acro.crosstab(
        data.year,
        data.grant_type,
        values=data.inc_grants,
        aggfunc="std",
        margins=True,
        show_suppressed=True,
    )
    output = acro.results.get_index(0)
    assert "All" not in output.output[0].columns
    assert np.isnan(output.output[0]["R/G"].iat[0])
    assert (
        "The margins with the std agg func can not be calculated. "
        "Please set the show_suppressed to false to calculate it." in caplog.text
    )


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
    assert 74 == output.output[0][("inc_grants", "All")].iat[0]

    total_rows = output.output[0].iloc[-1, 0:3].sum()
    total_cols = output.output[0].loc[2010:2015, ("inc_grants", "All")].sum()
    assert (
        766
        == total_cols
        == total_rows
        == output.output[0][("inc_grants", "All")].iat[6]
    )
    assert "R/G" not in output.output[0].columns


def test_crosstab_multiple_aggregate_function(data, acro):
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
    print(f"{output.output[0]['mean']['R/G'].sum()}")
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
    assert output.output[0].shape[1] == 8
    output_1 = acro.results.get_index(1)
    output_2 = acro.results.get_index(2)
    output_3 = pd.concat([output_1.output[0], output_2.output[0]], axis=1)
    output_4 = (output.output[0]).droplevel(0, axis=1)
    assert output_3.equals(output_4)


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
        show_suppressed=True,
    )
    assert (
        "We can not calculate the margins with a list of aggregation functions. "
        "Please create a table for each aggregation function" in caplog.text
    )


def test_histogram_disclosive(data, acro, caplog):
    """Test a discolsive histogram."""
    filename = os.path.normpath(f"{ARTIFACTS_DIR}/histogram_0.png")
    _ = acro.hist(data, "inc_grants")
    assert os.path.exists(filename)
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(path=PATH)
    output_0 = results.get_index(0)
    assert output_0.output == [filename]
    assert (
        "Histogram will not be shown as the inc_grants column is disclosive."
        in caplog.text
    )
    assert output_0.status == "fail"
    shutil.rmtree(PATH)


def test_histogram_non_disclosive(data, acro):
    """Test a non disclosive histogram."""
    filename = os.path.normpath(f"{ARTIFACTS_DIR}/histogram_0.png")
    # Bracket explicit bin edges outside the data extremes so extreme-value-leak
    # cannot fire on the real-world min/max of inc_grants.
    low = float(data["inc_grants"].min()) - 1.0
    high = float(data["inc_grants"].max()) + 1.0
    _ = acro.hist(data, "inc_grants", bins=[low, high])
    assert os.path.exists(filename)
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(path=PATH)
    output_0 = results.get_index(0)
    assert output_0.output == [filename]
    assert output_0.status == "review"
    shutil.rmtree(PATH)


def _make_wage_df(extra_low_count: int = 0) -> pd.DataFrame:
    """Build a synthetic wage DataFrame with controllable low-end mass."""
    np.random.seed(0)
    low = np.random.uniform(0.0, 10.0, size=extra_low_count) if extra_low_count else []
    mid = np.random.uniform(10.0, 90.0, size=10)
    high = np.random.uniform(90.0, 100.0, size=15)
    return pd.DataFrame({"wage": np.concatenate([low, mid, high])})


def test_histogram_interior_threshold_only():
    """Interior bins fail threshold but edge bins meet it."""
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)
    shutil.rmtree(PATH, ignore_errors=True)
    np.random.seed(0)
    low = np.random.uniform(0.0, 10.0, size=15)
    high = np.random.uniform(90.0, 100.0, size=15)
    interior = np.linspace(15.0, 85.0, 10)
    df = pd.DataFrame({"val": np.concatenate([low, interior, high])})
    a = ACRO(suppress=False)
    _ = a.hist(df, "val", bins=10)
    output = a.results.get_index(0)
    assert output.status == "fail"
    assert output.sdc["summary"]["edge-bin"] == 0
    assert output.sdc["summary"]["threshold"] > 0
    assert "edge-bin" not in output.summary
    assert "threshold:" in output.summary
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)


def test_histogram_edge_bin_only():
    """First bin falls below threshold; interior + last bins pass."""
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)
    shutil.rmtree(PATH, ignore_errors=True)
    # First bin [0,10): 5 rows. Bins 1..9 each get 10 rows evenly.
    low = np.linspace(1.0, 9.0, 5)
    interior = np.repeat(np.arange(15.0, 100.0, 10.0), 10)
    df = pd.DataFrame({"val": np.concatenate([low, interior])})
    a = ACRO(suppress=False)
    _ = a.hist(df, "val", bins=10)
    output = a.results.get_index(0)
    assert output.status == "fail"
    assert output.sdc["summary"]["edge-bin"] == 1
    assert output.sdc["bins"]["edge-bin"] == [0]
    assert "edge-bin:" in output.summary
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)


def test_histogram_by_val_range_mismatch():
    """Stratified histogram where subgroups have different ranges."""
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)
    shutil.rmtree(PATH, ignore_errors=True)
    np.random.seed(2)
    male_wages = np.random.uniform(5.0, 10.0, size=30)
    female_wages = np.random.uniform(4.0, 10.0, size=30)
    df = pd.DataFrame(
        {
            "sex": ["M"] * 30 + ["F"] * 30,
            "wage": np.concatenate([male_wages, female_wages]),
        }
    )
    a = ACRO(suppress=False)
    _ = a.hist(df, "wage", by_val="sex", bins=6)
    output = a.results.get_index(0)
    assert output.status == "fail"
    assert output.sdc["summary"]["by-val-range-mismatch"] is True
    assert "by-val-range-mismatch:" in output.summary
    assert "sex" in output.sdc["by_val_detail"]
    assert set(output.sdc["by_val_detail"]["sex"]) == {"M", "F"}
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)


def test_histogram_extreme_value_leak():
    """A single individual holds the minimum; leftmost edge reveals them."""
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)
    shutil.rmtree(PATH, ignore_errors=True)
    np.random.seed(3)
    rest = np.random.uniform(5.0, 10.0, size=50)
    df = pd.DataFrame({"wage": np.concatenate([[1.0], rest])})
    a = ACRO(suppress=False)
    _ = a.hist(df, "wage", bins=10)
    output = a.results.get_index(0)
    assert output.status == "fail"
    assert output.sdc["summary"]["extreme-value-leak"] >= 1
    assert output.sdc["min_count"] == 1
    assert "extreme-value-leak:" in output.summary
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)


def test_histogram_explicit_bins_no_leak():
    """User-supplied bin edges that don't coincide with data extremes don't leak."""
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)
    shutil.rmtree(PATH, ignore_errors=True)
    # Data in [4.5, 10]; bin edges [4, 6, 8, 10.5] bracket away from the extremes.
    # Each bin gets at least 10 rows.
    values = np.concatenate(
        [
            np.linspace(4.5, 5.9, 10),
            np.linspace(6.0, 7.9, 15),
            np.linspace(8.0, 10.0, 12),
        ]
    )
    df = pd.DataFrame({"val": values})
    a = ACRO(suppress=False)
    _ = a.hist(df, "val", bins=[4.0, 6.0, 8.0, 10.5])
    output = a.results.get_index(0)
    assert output.status == "review"
    assert output.sdc["summary"]["extreme-value-leak"] == 0
    assert output.sdc["summary"]["edge-bin"] == 0
    assert output.sdc["summary"]["threshold"] == 0
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)


def test_histogram_nan_handling():
    """Drop NaNs before SDC math; all-NaN column returns None."""
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)
    shutil.rmtree(PATH, ignore_errors=True)
    np.random.seed(5)
    valid = np.random.uniform(0.0, 100.0, size=15)
    df = pd.DataFrame({"val": np.concatenate([valid, [np.nan] * 5])})
    a = ACRO(suppress=False)
    _ = a.hist(df, "val", bins=5)
    output = a.results.get_index(0)
    assert sum(output.sdc["counts"]) == 15
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)


def test_histogram_by_val_unnamed_series():
    """Accept an unnamed pd.Series as by_val without breaking by_val_detail keys."""
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)
    shutil.rmtree(PATH, ignore_errors=True)
    np.random.seed(6)
    wages = np.concatenate(
        [np.random.uniform(5.0, 10.0, size=30), np.random.uniform(4.0, 10.0, size=30)]
    )
    df = pd.DataFrame({"wage": wages})
    grouper = pd.Series(["M"] * 30 + ["F"] * 30)  # no .name set
    a = ACRO(suppress=False)
    _ = a.hist(df, "wage", by_val=grouper, bins=6)
    output = a.results.get_index(0)
    assert "by_val" in output.sdc["by_val_detail"]
    assert set(output.sdc["by_val_detail"]["by_val"]) == {"M", "F"}
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)


def test_histogram_integer_column_extreme_leak():
    """Integer-valued column with a single maximum trips extreme-value-leak."""
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)
    shutil.rmtree(PATH, ignore_errors=True)
    df = pd.DataFrame({"age": [20] * 30 + [65]})
    a = ACRO(suppress=False)
    _ = a.hist(df, "age", bins=10)
    output = a.results.get_index(0)
    assert output.status == "fail"
    assert output.sdc["summary"]["extreme-value-leak"] >= 1
    assert output.sdc["max_count"] == 1
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)


def test_histogram_zeros_not_disclosive(acro):
    """Empty tail bins do not flag a histogram when zeros_are_disclosive=False."""
    filename = os.path.normpath(f"{ARTIFACTS_DIR}/histogram_0.png")
    # 100 obs at each of 6 distinct values spanning [0, 10]; with bins=20, the
    # only sub-threshold bins are the empty ones between the populated values.
    df = pd.DataFrame({"x": np.repeat([0.0, 1.0, 2.0, 3.0, 5.0, 10.0], 100)})
    acro_tables.ZEROS_ARE_DISCLOSIVE = False
    try:
        _ = acro.hist(df, "x", bins=20)
    finally:
        acro_tables.ZEROS_ARE_DISCLOSIVE = True
    assert os.path.exists(filename)
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(path=PATH)
    output_0 = results.get_index(0)
    assert output_0.output == [filename]
    assert output_0.status == "review"
    shutil.rmtree(PATH)


def test_histogram_zeros_disclosive_default(acro, caplog):
    """Empty bins remain disclosive under the default zeros_are_disclosive=True."""
    filename = os.path.normpath(f"{ARTIFACTS_DIR}/histogram_0.png")
    df = pd.DataFrame({"x": np.repeat([0.0, 1.0, 2.0, 3.0, 5.0, 10.0], 100)})
    _ = acro.hist(df, "x", bins=20)
    assert os.path.exists(filename)
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(path=PATH)
    output_0 = results.get_index(0)
    assert output_0.output == [filename]
    assert output_0.status == "fail"
    assert "Histogram will not be shown as the x column is disclosive." in caplog.text
    shutil.rmtree(PATH)


def test_histogram_nonempty_below_threshold_still_disclosive(acro):
    """A non-empty bin below threshold remains disclosive even when zeros are not."""
    filename = os.path.normpath(f"{ARTIFACTS_DIR}/histogram_0.png")
    # bins=2 over [0, 5]: one bin has 100 obs, the other has 5 (non-empty, < THRESHOLD).
    df = pd.DataFrame({"x": np.r_[np.repeat(0.0, 100), np.repeat(5.0, 5)]})
    acro_tables.ZEROS_ARE_DISCLOSIVE = False
    try:
        _ = acro.hist(df, "x", bins=2)
    finally:
        acro_tables.ZEROS_ARE_DISCLOSIVE = True
    assert os.path.exists(filename)
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(path=PATH)
    output_0 = results.get_index(0)
    assert output_0.status == "fail"
    shutil.rmtree(PATH)


def test_pie_disclosive(acro, caplog):
    """Test a disclosive pie chart (a category has fewer than threshold observations)."""
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)
    shutil.rmtree(PATH, ignore_errors=True)

    df = pd.DataFrame(
        {"grant_type": (["A"] * 20) + (["B"] * 15) + (["C"] * 12) + (["D"] * 5)}
    )

    filename = os.path.normpath(f"{ARTIFACTS_DIR}/pie_0.png")
    _ = acro.pie(df, "grant_type", filename="pie.png")

    assert os.path.exists(filename)
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise(path=PATH)
    output_0 = results.get_index(0)

    assert output_0.output == [filename]
    assert (
        "Pie chart will not be shown as the grant_type column is disclosive."
        in caplog.text
    )
    assert output_0.status == "fail"
    shutil.rmtree(PATH)


def test_pie_non_disclosive(data, acro):
    """Test a non-disclosive pie chart (all categories meet the threshold)."""
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)
    shutil.rmtree(PATH, ignore_errors=True)
    filename = os.path.normpath(f"{ARTIFACTS_DIR}/pie_0.png")
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
    """Test interactive version of finalising acro.

    Leaves exceptions as they should be disclosive table.
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


def test_crosstab_with_totals_raises_when_data_none():
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
    # correct
    rows = [data.year, data.grant_type]
    cols = [data.survivor, data.status]
    mydataframe = acro_tables.create_dataframe(rows, cols)
    assert mydataframe.shape == (918, 4)

    # no rows
    mydataframe2 = acro_tables.create_dataframe(None, cols)
    assert list(mydataframe2.columns.values) == ["survivor", "status"]

    # invalid rows
    mydataframe2a = acro_tables.create_dataframe(["year", "grant_type"], cols)
    assert list(mydataframe2a.columns.values) == ["survivor", "status"]

    # no cols
    mydataframe3 = acro_tables.create_dataframe(rows, None)
    assert list(mydataframe3.columns.values) == ["year", "grant_type"]

    # invalid cols
    mydataframe3a = acro_tables.create_dataframe(rows, ["survivor", "status"])
    assert list(mydataframe3a.columns.values) == ["year", "grant_type"]

    # neither
    mydataframe4 = acro_tables.create_dataframe(None, None)
    assert mydataframe4.empty, (
        "dataframe created with no rows or cols should be empty "
        f"but got shape{mydataframe4.shape}"
    )

    # both invalid
    mydataframe4a = acro_tables.create_dataframe(
        ["year", "grant_type"], ["survivor", "status"]
    )
    assert mydataframe4a.empty, (
        "dataframe created with invalid rows  and columns should be empty"
        f"but got shape{mydataframe4a.shape}"
    )


def test_toggle_suppression():
    """Test toggling suppression on/off."""
    acro = ACRO(suppress=False)
    assert not acro.suppress
    acro.enable_suppression()
    assert acro.suppress
    acro.disable_suppression()
    assert not acro.suppress


def test_crosstab_std_dropna(data, acro):
    """Test acro crosstab process error when reporting std in some cases."""
    table = acro.crosstab(
        data["year"], data["grant_type"], values=data["inc_grants"], aggfunc="std"
    )
    assert isinstance(table, pd.DataFrame)


def test_pivot_table_std_dropna():
    """Test pivot_table with std and dropna=True."""
    data = pd.DataFrame(
        {
            "A": ["x", "x", "y", "z"],
            "B": ["c1", "c1", "c2", "c2"],
            "V": [1, 2, 3, 4],
        }
    )
    acro = ACRO()
    table = acro.pivot_table(data, values="V", index="A", columns="B", aggfunc="std")
    assert isinstance(table, pd.DataFrame)
    assert "y" not in table.index
    assert "z" not in table.index
    assert "c2" not in table.columns


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
    assert isinstance(table, pd.DataFrame)
    assert table.columns.nlevels == 2
    top_levels = table.columns.get_level_values(0).unique().tolist()
    assert "mean" in top_levels
    assert "std" in top_levels

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


def test_align_masks_droplevel():
    """Test align_masks drops extra index/column levels to match table shape."""
    # table with single-level columns and index
    table = pd.DataFrame(
        {"c1": [1.0, 2.0], "c2": [3.0, 4.0]},
        index=pd.Index(["r1", "r2"]),
    )
    # mask with MultiIndex columns (extra level)
    multi_cols = pd.MultiIndex.from_tuples([("agg", "c1"), ("agg", "c2")])
    mask_multi_col = pd.DataFrame(
        [[False, False], [False, True]],
        index=pd.Index(["r1", "r2"]),
        columns=multi_cols,
    )
    # mask with MultiIndex index (extra level)
    multi_idx = pd.MultiIndex.from_tuples([("g1", "r1"), ("g1", "r2")])
    mask_multi_idx = pd.DataFrame(
        [[False, False], [False, True]],
        index=multi_idx,
        columns=pd.Index(["c1", "c2"]),
    )
    masks = {"multi_col": mask_multi_col, "multi_idx": mask_multi_idx}
    aligned = acro_tables.align_masks(table, masks)
    # both masks should now match table shape exactly
    assert aligned["multi_col"].columns.tolist() == ["c1", "c2"]
    assert aligned["multi_col"].index.tolist() == ["r1", "r2"]
    assert aligned["multi_idx"].index.tolist() == ["r1", "r2"]
    assert aligned["multi_idx"].columns.tolist() == ["c1", "c2"]


def test_cell_id_alignment_with_margins_and_suppression(data):
    """Verify cell IDs in results.json are valid table indices.

    The key issue in bug was that when pandas removes empty rows/columns,
    cell positions stored in the mask become invalid.
    """
    acro = ACRO(suppress=True)
    table = acro.crosstab(
        data.year, data.grant_type, margins=True, show_suppressed=True
    )
    output = acro.results.get_index(0)

    for cell_type in output.sdc["cells"]:
        cells = output.sdc["cells"][cell_type]
        for row, col in cells:
            assert row < table.shape[0], (
                f"Row {row} out of bounds for {cell_type} cell in table shape {table.shape}"
            )
            assert col < table.shape[1], (
                f"Column {col} out of bounds for {cell_type} cell in table shape {table.shape}"
            )

            value = table.iloc[row, col]
            if cell_type in ["threshold", "p-ratio", "nk-rule"]:
                assert pd.isna(value), (
                    f"Cell at ({row}, {col}) in {cell_type} should be NaN but is {value}"
                )

    # margins=False
    acro2 = ACRO(suppress=True)
    table2 = acro2.crosstab(data.year, data.grant_type, margins=False)
    output2 = acro2.results.get_index(0)

    for cell_type in output2.sdc["cells"]:
        cells = output2.sdc["cells"][cell_type]
        for row, col in cells:
            assert row < table2.shape[0], (
                f"Row {row} out of bounds for {cell_type} cell in table shape {table2.shape}"
            )
            assert col < table2.shape[1], (
                f"Column {col} out of bounds for {cell_type} cell in table shape {table2.shape}"
            )

            value = table2.iloc[row, col]
            if cell_type in ["threshold", "p-ratio", "nk-rule"]:
                assert pd.isna(value), (
                    f"Cell at ({row}, {col}) in {cell_type} should be NaN but is {value}"
                )


def _rounded_cells(table: pd.DataFrame) -> np.ndarray:
    """Return the non-NaN numeric values of a table as a flat numpy array."""
    numeric = table.select_dtypes(include=["number"]).to_numpy().ravel()
    return numeric[~np.isnan(numeric)]


def _assert_rounded_margins_consistent(
    table: pd.DataFrame, base: int, margins_name: str = "All"
) -> None:
    """Assert margins equal rounded sums of inner cells across both axes."""
    inner_cols = [c for c in table.columns if c != margins_name]
    inner_rows = [r for r in table.index if r != margins_name]
    # row margins: sum across inner columns, re-rounded
    for row in inner_rows:
        expected = (table.loc[row, inner_cols].sum() / base).round() * base
        assert table.loc[row, margins_name] == expected
    # column margins: sum across inner rows, re-rounded
    for col in inner_cols:
        expected = (table.loc[inner_rows, col].sum() / base).round() * base
        assert table.loc[margins_name, col] == expected
    # grand total: rounded sum of the column margins == rounded sum of the row margins
    grand_from_cols = (table.loc[margins_name, inner_cols].sum() / base).round() * base
    grand_from_rows = (table.loc[inner_rows, margins_name].sum() / base).round() * base
    assert table.loc[margins_name, margins_name] == grand_from_cols
    assert table.loc[margins_name, margins_name] == grand_from_rows


def test_crosstab_with_rounding_base_5(data):
    """Crosstab with mitigation='round' rounds every cell to nearest 5."""
    acro = ACRO(mitigation="round")
    table = acro.crosstab(data.year, data.grant_type)
    values = _rounded_cells(table)
    assert values.size > 0
    assert np.all(values % 5 == 0)
    output = acro.results.get_index(0)
    assert output.status == "review"
    assert "rounded to nearest 5" in output.summary
    assert output.properties["mitigation"] == "round"
    assert output.properties["round_base"] == 5


def test_crosstab_with_rounding_base_10(data):
    """Crosstab with round_base=10 rounds every cell to nearest 10."""
    acro = ACRO(mitigation="round", round_base=10)
    table = acro.crosstab(data.year, data.grant_type)
    values = _rounded_cells(table)
    assert values.size > 0
    assert np.all(values % 10 == 0)
    output = acro.results.get_index(0)
    assert "rounded to nearest 10" in output.summary


def test_pivot_table_with_rounding(data):
    """Pivot_table with mitigation='round' rounds every cell."""
    acro = ACRO(mitigation="round", round_base=5)
    table = acro.pivot_table(
        data, index="year", columns="grant_type", values="inc_grants", aggfunc="count"
    )
    values = _rounded_cells(table)
    assert values.size > 0
    assert np.all(values % 5 == 0)
    output = acro.results.get_index(0)
    assert output.properties["mitigation"] == "round"
    assert output.properties["round_base"] == 5


def test_rounding_with_margins_crosstab_recomputes_totals(data):
    """Crosstab with margins=True under rounding recomputes margins from rounded cells."""
    acro = ACRO(mitigation="round", round_base=5)
    table = acro.crosstab(data.year, data.grant_type, margins=True)
    # margins row/column are present and named "All"
    assert "All" in table.columns
    assert "All" in table.index
    # every cell (including margins) is a multiple of the round base
    values = _rounded_cells(table)
    assert values.size > 0
    assert np.all(values % 5 == 0)
    # row totals, column totals, and the grand total are all consistent
    _assert_rounded_margins_consistent(table, base=5)


def test_rounding_with_margins_pivot_table_recomputes_totals(data):
    """Pivot_table with margins=True under rounding recomputes margins from rounded cells."""
    acro = ACRO(mitigation="round", round_base=5)
    table = acro.pivot_table(
        data,
        index="year",
        columns="grant_type",
        values="inc_grants",
        aggfunc="count",
        margins=True,
    )
    assert "All" in table.columns
    assert "All" in table.index
    values = _rounded_cells(table)
    assert values.size > 0
    assert np.all(values % 5 == 0)
    # row totals, column totals, and the grand total are all consistent
    _assert_rounded_margins_consistent(table, base=5)


def test_suppress_backward_compat():
    """The suppress property stays in sync with mitigation."""
    acro = ACRO(suppress=True)
    assert acro.mitigation == "suppress"
    assert acro.suppress is True
    acro.suppress = False
    assert acro.mitigation == "none"
    assert acro.suppress is False
    acro.suppress = True
    assert acro.mitigation == "suppress"


def test_enable_rounding_disable_rounding():
    """Enable_rounding / disable_rounding toggle the mitigation field."""
    acro = ACRO()
    assert acro.mitigation == "none"
    acro.enable_rounding(base=10)
    assert acro.mitigation == "round"
    assert acro.round_base == 10
    acro.disable_rounding()
    assert acro.mitigation == "none"


def test_disable_rounding_does_not_restore_prior_suppress():
    """Disable_rounding always falls back to 'none', not to prior suppress=True."""
    acro = ACRO(suppress=True)
    assert acro.mitigation == "suppress"
    acro.enable_rounding()
    assert acro.mitigation == "round"
    acro.disable_rounding()
    # documented behaviour: prior suppress state is not restored
    assert acro.mitigation == "none"
    assert acro.suppress is False


def test_round_base_loaded_from_config():
    """Round_base is picked up from the yaml config by default."""
    acro = ACRO()
    assert acro.round_base == 5


def test_round_preserves_nan():
    """Rounding a table with NaN cells preserves the NaN."""
    table = pd.DataFrame({"a": [3.0, np.nan, 11.0], "b": [7.0, 2.0, np.nan]})
    rounded = acro_tables.round_table(table, base=5)
    assert pd.isna(rounded.loc[1, "a"])
    assert pd.isna(rounded.loc[2, "b"])
    assert rounded.loc[0, "a"] == 5
    assert rounded.loc[2, "a"] == 10
    assert rounded.loc[0, "b"] == 5
    assert rounded.loc[1, "b"] == 0


def test_round_base_rejects_non_positive(caplog):
    """Setting round_base to zero or negative logs a message and falls back to default."""
    acro = ACRO()
    default = acro.round_base
    with caplog.at_level(logging.INFO, logger="acro"):
        acro.round_base = 0
    assert acro.round_base == default
    assert "positive integer" in caplog.text
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="acro"):
        acro.round_base = -3
    assert acro.round_base == default
    assert "positive integer" in caplog.text


def test_suppress_false_while_rounding_is_noop(caplog):
    """Setting suppress=False while rounding is active logs a message and is a no-op."""
    acro = ACRO(mitigation="round")
    with caplog.at_level(logging.INFO, logger="acro"):
        acro.suppress = False
    assert acro.mitigation == "round"
    assert "disable_rounding" in caplog.text
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="acro"):
        acro.disable_suppression()
    assert acro.mitigation == "round"
    assert "disable_rounding" in caplog.text


def test_rounding_records_underlying_disclosure_risk(data):
    """The sdc audit record still flags threshold violations when rounding."""
    acro = ACRO(mitigation="round", round_base=5)
    acro.crosstab(data.year, data.grant_type)
    output = acro.results.get_index(0)
    assert output.sdc["summary"]["threshold"] > 0
    assert output.sdc["summary"]["mitigation"] == "round"
    assert output.sdc["summary"]["round_base"] == 5
    assert "rounded to nearest 5" in output.summary
    assert "threshold:" in output.summary
    values = _rounded_cells(output.output[0])
    assert np.all(values % 5 == 0)


def test_round_base_passed_to_constructor():
    """ACRO(round_base=...) overrides the yaml default."""
    acro = ACRO(round_base=7)
    assert acro.round_base == 7


def test_mitigation_setter_rejects_invalid_value(caplog):
    """Setting mitigation to an unknown value logs a message and falls back to 'none'."""
    acro = ACRO()
    with caplog.at_level(logging.INFO, logger="acro"):
        acro.mitigation = "obfuscate"
    assert acro.mitigation == "none"
    assert "obfuscate" in caplog.text


def test_round_table_noop_when_base_non_positive():
    """Round_table returns an unchanged copy when base is 0 or negative."""
    table = pd.DataFrame({"a": [3.2, 4.7], "b": [11.0, 9.0]})
    zero = acro_tables.round_table(table, base=0)
    assert (zero.to_numpy() == table.to_numpy()).all()
    negative = acro_tables.round_table(table, base=-5)
    assert (negative.to_numpy() == table.to_numpy()).all()


def test_rounded_summary_reports_negative_values(data):
    """The rounded summary surfaces negative and missing check results."""
    data.loc[0:10, "inc_grants"] = -10
    acro = ACRO(mitigation="round", round_base=5)
    acro.crosstab(data.year, data.grant_type, values=data.inc_grants, aggfunc="mean")
    output = acro.results.get_index(0)
    assert "negative values found" in output.summary


def test_rounded_summary_reports_missing_values():
    """_rounded_summary emits a missing-values note when the check fires."""
    sdc_summary = {
        "mitigation": "round",
        "round_base": 5,
        "threshold": 0,
        "p-ratio": 0,
        "nk-rule": 0,
        "all-values-are-same": 0,
        "negative": 0,
        "missing": 2,
    }
    status, summary = acro_tables._rounded_summary(sdc_summary)
    assert status == "review"
    assert "missing values found" in summary


def _simple_rounded_table() -> pd.DataFrame:
    """Return a small pre-rounded numeric table for margin tests."""
    return pd.DataFrame(
        {"a": [5.0, 10.0, 15.0], "b": [10.0, 5.0, 20.0]},
        index=["r1", "r2", "r3"],
    )


def test_aggfunc_name_extracts_callable_name():
    """_aggfunc_name returns __name__ for callables and None for opaque values."""
    assert acro_tables._aggfunc_name("mean") == "mean"
    assert acro_tables._aggfunc_name(acro_tables.mode_aggfunc) == "mode_aggfunc"
    assert acro_tables._aggfunc_name(object()) is None


def test_append_rounded_margins_list_aggfunc_skips_margins(caplog):
    """A list of aggfuncs falls back to no margins with a log message."""
    table = _simple_rounded_table()
    with caplog.at_level(logging.INFO, logger="acro"):
        result = acro_tables.append_rounded_margins(table, ["sum", "mean"], "All", 5)
    pd.testing.assert_frame_equal(result, table)
    assert "multiple aggregation" in caplog.text


def test_append_rounded_margins_multilevel_index_skips_margins(caplog):
    """A hierarchical row index falls back to no margins."""
    idx = pd.MultiIndex.from_tuples([("a", 1), ("a", 2), ("b", 1)])
    table = pd.DataFrame({"x": [5.0, 10.0, 15.0], "y": [10.0, 5.0, 20.0]}, index=idx)
    with caplog.at_level(logging.INFO, logger="acro"):
        result = acro_tables.append_rounded_margins(table, None, "All", 5)
    pd.testing.assert_frame_equal(result, table)
    assert "hierarchical" in caplog.text


def test_append_rounded_margins_multilevel_columns_skips_margins(caplog):
    """A hierarchical column index falls back to no margins."""
    cols = pd.MultiIndex.from_tuples([("g", "x"), ("g", "y")])
    table = pd.DataFrame([[5.0, 10.0], [10.0, 5.0]], columns=cols)
    with caplog.at_level(logging.INFO, logger="acro"):
        result = acro_tables.append_rounded_margins(table, None, "All", 5)
    pd.testing.assert_frame_equal(result, table)
    assert "hierarchical" in caplog.text


def test_append_rounded_margins_unsupported_aggfunc_skips_margins(caplog):
    """An aggfunc we don't know how to recompute margins for is skipped."""
    table = _simple_rounded_table()
    with caplog.at_level(logging.INFO, logger="acro"):
        result = acro_tables.append_rounded_margins(table, "std", "All", 5)
    pd.testing.assert_frame_equal(result, table)
    assert "'std'" in caplog.text


def test_append_rounded_margins_mean_uses_mean_of_rounded_cells():
    """Mean aggfunc derives margins from the mean of rounded cells, then rounds them."""
    table = _simple_rounded_table()
    result = acro_tables.append_rounded_margins(table, "mean", "All", 5)
    # mean of row r1 = mean(5, 10) = 7.5; pandas Series.round uses banker's
    # rounding so 7.5/5=1.5 -> 2 -> 10.
    assert result.loc["r1", "All"] == 10
    # mean of column a = mean(5, 10, 15) = 10
    assert result.loc["All", "a"] == 10
    values = _rounded_cells(result)
    assert np.all(values % 5 == 0)


def test_append_rounded_margins_median_uses_median_of_rounded_cells():
    """Median aggfunc derives margins from the median of rounded cells."""
    table = _simple_rounded_table()
    result = acro_tables.append_rounded_margins(table, "median", "All", 5)
    # median of column a = median(5, 10, 15) = 10
    assert result.loc["All", "a"] == 10
    values = _rounded_cells(result)
    assert np.all(values % 5 == 0)


def test_summary_csv_created_with_json(data, acro):
    """Test that DO_NOT_RELEASE_session_summary.csv is created when finalising to JSON."""
    path = "RES_SUMMARY_JSON"
    shutil.rmtree(path, ignore_errors=True)
    _ = acro.crosstab(data.year, data.grant_type)
    acro.add_exception("output_0", "Let me have it")
    acro.finalise(path, "json")
    summary_path = os.path.normpath(f"{path}/DO_NOT_RELEASE_session_summary.csv")
    assert os.path.exists(summary_path), (
        "DO_NOT_RELEASE_session_summary.csv was not created"
    )
    summary_df = pd.read_csv(summary_path)
    assert len(summary_df) == 1
    assert "id" in summary_df.columns
    assert "method" in summary_df.columns
    assert "variables" in summary_df.columns
    assert "total_records" in summary_df.columns
    assert "suppression" in summary_df.columns
    assert "diff_risk" in summary_df.columns
    # check values
    assert summary_df.iloc[0]["id"] == "output_0"
    assert summary_df.iloc[0]["method"] == "crosstab"
    assert summary_df.iloc[0]["total_records"] > 0
    shutil.rmtree(path, ignore_errors=True)


def test_summary_sheet_in_excel(data, acro):
    """Test that a 'summary' sheet is created in results.xlsx."""
    path = "RES_SUMMARY_XLSX"
    shutil.rmtree(path, ignore_errors=True)
    _ = acro.crosstab(data.year, data.grant_type)
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    acro.add_exception("output_0", "Let me have it")
    acro.add_exception("output_1", "I need this")
    acro.finalise(path, "xlsx")
    filename = os.path.normpath(f"{path}/results.xlsx")
    xl = pd.ExcelFile(filename)
    assert "summary" in xl.sheet_names, "'summary' sheet not found in Excel"
    summary_df = pd.read_excel(filename, sheet_name="summary")
    xl.close()
    assert len(summary_df) == 2
    methods = summary_df["method"].tolist()
    assert "crosstab" in methods
    assert "pivot_table" in methods
    shutil.rmtree(path, ignore_errors=True)


def test_summary_variables_extracted(data):
    """Test that variable names are correctly extracted into the summary."""
    path = "RES_SUMMARY_VARS"
    shutil.rmtree(path, ignore_errors=True)
    acro_obj = ACRO(suppress=False)
    _ = acro_obj.crosstab(data.year, data.grant_type)
    acro_obj.add_exception("output_0", "Let me have it")
    acro_obj.finalise(path, "json")
    summary_path = os.path.normpath(f"{path}/DO_NOT_RELEASE_session_summary.csv")
    summary_df = pd.read_csv(summary_path)
    variables = summary_df.iloc[0]["variables"]
    assert "year" in variables
    assert "grant_type" in variables
    shutil.rmtree(path, ignore_errors=True)


def test_summary_differencing_risk(data):
    """Test that differencing risk is flagged when tables share variables but have different suppression settings."""
    acro_obj = ACRO(suppress=True)
    _ = acro_obj.crosstab(data.year, data.grant_type)
    acro_obj.suppress = False
    _ = acro_obj.crosstab(data.year, data.grant_type)
    acro_obj.add_exception("output_0", "Let me have it")
    acro_obj.add_exception("output_1", "I need this")

    summary_df = acro_obj.results.generate_summary()

    assert summary_df.iloc[0]["variables"] == summary_df.iloc[1]["variables"]

    assert summary_df.iloc[0]["suppression"]
    assert not summary_df.iloc[1]["suppression"]

    assert summary_df.iloc[0]["diff_risk"]
    assert summary_df.iloc[1]["diff_risk"]


def test_summary_regression_metadata(data, acro):
    """Test that regression outputs are correctly captured in the summary."""
    new_df = data[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
    new_df = new_df.dropna()
    endog = new_df.inc_activity
    exog = new_df[["inc_grants", "inc_donations", "total_costs"]]
    exog = add_constant(exog)
    _ = acro.ols(endog, exog)
    summary_df = acro.results.generate_summary()
    assert len(summary_df) == 1
    row = summary_df.iloc[0]
    assert row["method"] == "ols"
    assert row["type"] == "regression"
    assert row["total_records"] > 0
    variables = row["variables"]
    assert "inc_activity" in variables
    assert "inc_grants" in variables
    assert "inc_donations" in variables
    assert "total_costs" in variables


def test_summary_empty_session():
    """Test that summary handles an empty session gracefully."""
    acro_obj = ACRO(suppress=False)
    summary_df = acro_obj.results.generate_summary()
    assert summary_df.empty
    assert "diff_risk" in summary_df.columns


def test_extract_table_info(data, acro):
    """Test the _extract_table_info helper method."""
    acro.crosstab(data.year, data.grant_type)
    output = acro.results.get_index(0)

    variables, total_records = acro.results._extract_table_info(output.output)
    assert len(variables) > 0
    assert total_records > 0
    assert "year" in variables or "grant_type" in variables


def test_extract_regression_info():
    """Test the _extract_regression_info helper method with sample data."""
    records = Records()

    reg_output = pd.DataFrame(
        {
            "coef": [1.0, 2.0],
            "std err": [0.1, 0.2],
            "t": [10.0, 10.0],
            "P>|t|": [0.0, 0.0],
        },
        index=["const", "x1"],
    )

    obs_output = pd.DataFrame({"Value": [100]}, index=["no. observations"])

    output = [reg_output, obs_output]
    total_records = records._extract_regression_info(output)

    assert total_records == 100


def test_extract_regression_info_column_search():
    """Test _extract_regression_info column-based search path."""
    records = Records()

    df = pd.DataFrame(columns=["no. observations", "500"])
    assert records._extract_regression_info([df]) == 500


def test_extract_regression_variables():
    """Test _extract_regression_variables extracts dep and indep variable names."""
    records = Records()

    table0 = pd.DataFrame(
        {"inc_activity": ["OLS", "2024-01-01"]}, index=["Model", "Date"]
    )

    table1 = pd.DataFrame(
        {"coef": [0.5, 1.2, 3.4, 0.8], "std err": [0.1, 0.2, 0.3, 0.4]},
        index=["const", "inc_grants", "inc_donations", "total_costs"],
    )

    result = records._extract_regression_variables([table0, table1])
    assert result[0] == "inc_activity"
    assert "inc_grants" in result
    assert "inc_donations" in result
    assert "total_costs" in result
    assert "const" not in result

    table1_intercept = pd.DataFrame(
        {"coef": [0.5, 1.0]},
        index=["Intercept", "x1"],
    )
    result2 = records._extract_regression_variables([table0, table1_intercept])
    assert "Intercept" not in result2
    assert "x1" in result2

    assert records._extract_regression_variables([]) == []

    assert records._extract_regression_variables([table0]) == []

    result3 = records._extract_regression_variables(["not a df", "also not a df"])
    assert result3 == []


def test_mark_diff_risk(data, acro):
    """Test the _mark_diff_risk helper method."""
    # Create two crosstabs with same variables but different data
    acro.crosstab(data.year, data.grant_type)
    acro.crosstab(data.year, data.grant_type)

    summary_df = acro.results.generate_summary()

    assert "diff_risk" in summary_df.columns

    assert all(isinstance(x, (bool, type(pd.NA))) for x in summary_df["diff_risk"])


def test_extract_table_info_with_zero_cell_sum():
    """Test _extract_table_info when cell_sum equals 0."""
    records = Records()

    table = pd.DataFrame(
        [[np.nan, np.nan], [np.nan, np.nan]],
        index=["row1", "row2"],
        columns=["col1", "col2"],
    )
    table.index.name = "idx"
    table.columns.name = "cols"

    output = [table]
    variables, total_records = records._extract_table_info(output)

    assert "idx" in variables
    assert "cols" in variables
    assert total_records > 0


def test_extract_regression_info_with_missing_observations():
    """Test _extract_regression_info when observation value is NaN."""
    records = Records()

    # Create regression output with no. observations but NaN value
    obs_output = pd.DataFrame({"Value": [np.nan]}, index=["no. observations"])

    output = [obs_output]
    total_records = records._extract_regression_info(output)

    assert total_records == 0


def test_extract_regression_info_with_invalid_value():
    """Test _extract_regression_info when observation value is non-numeric."""
    records = Records()

    obs_output = pd.DataFrame({"Value": ["not_a_number"]}, index=["no. observations"])

    output = [obs_output]
    total_records = records._extract_regression_info(output)

    assert total_records == 0


def test_extract_table_info_with_numeric_data():
    """Test _extract_table_info with numeric data."""
    records = Records()

    table = pd.DataFrame(
        [[10, 20], [30, 40]],
        index=["row1", "row2"],
        columns=["col1", "col2"],
    )
    table.index.name = "idx"
    table.columns.name = "cols"

    output = [table]
    variables, total_records = records._extract_table_info(output)

    assert "idx" in variables
    assert "cols" in variables
    assert total_records == 100


def test_extract_table_info_with_mixed_data():
    """Test _extract_table_info with mixed NaN and numeric data."""
    records = Records()

    # Create a table with some NaN and some numeric values
    table = pd.DataFrame(
        [[10, np.nan], [np.nan, 40]],
        index=["row1", "row2"],
        columns=["col1", "col2"],
    )
    table.index.name = "idx"

    output = [table]
    variables, total_records = records._extract_table_info(output)

    assert "idx" in variables
    assert total_records == 50


def test_generate_variable_matrix_table():
    """Test the variable matrix table.

    Should have one row per output and one column per variable,
    with binary values indicating variable presence.
    """
    acro_obj = ACRO(suppress=False)

    data = pd.DataFrame(
        {
            "year": [2010] * 10 + [2011] * 10,
            "grant_type": ["A"] * 5 + ["B"] * 5 + ["A"] * 5 + ["B"] * 5,
            "region": ["North"] * 5 + ["South"] * 5 + ["North"] * 5 + ["South"] * 5,
        }
    )

    # Create three outputs with different variable combinations
    _ = acro_obj.crosstab(data.year, data.grant_type)
    _ = acro_obj.crosstab(data.year, data.region)
    _ = acro_obj.crosstab(data.grant_type, data.region)

    var_matrix = acro_obj.results.generate_variable_matrix_table()

    assert "output_id" in var_matrix.columns
    assert "output_type" in var_matrix.columns
    assert len(var_matrix) == 3

    assert "year" in var_matrix.columns
    assert "grant_type" in var_matrix.columns
    assert "region" in var_matrix.columns

    for row in var_matrix.itertuples():
        assert row.year in [0, 1]
        assert row.grant_type in [0, 1]
        assert row.region in [0, 1]

    assert var_matrix.iloc[0]["year"] == 1
    assert var_matrix.iloc[0]["grant_type"] == 1
    assert var_matrix.iloc[0]["region"] == 0

    assert var_matrix.iloc[1]["year"] == 1
    assert var_matrix.iloc[1]["grant_type"] == 0
    assert var_matrix.iloc[1]["region"] == 1

    assert var_matrix.iloc[2]["year"] == 0
    assert var_matrix.iloc[2]["grant_type"] == 1
    assert var_matrix.iloc[2]["region"] == 1


def test_get_endog_exog_variables():
    """Test extracting variables from endog and exog arguments."""
    # Use pandas objects with names
    endog = pd.Series([1, 2, 3], name="y")
    exog = pd.DataFrame({"const": [1, 1, 1], "x1": [4, 5, 6], "x2": [7, 8, 9]})

    variables = _get_endog_exog_variables(endog, exog)
    assert variables == ["y", "x1", "x2"]

    # Use single series for exog
    exog_series = pd.Series([4, 5, 6], name="x1")
    variables = _get_endog_exog_variables(endog, exog_series)
    assert variables == ["y", "x1"]

    # Missing names
    endog_noname = pd.Series([1, 2, 3])
    exog_noname = pd.Series([4, 5, 6])
    variables = _get_endog_exog_variables(endog_noname, exog_noname)
    assert variables == []


def test_get_endog_exog_variables_edge_cases():
    """Additional edge cases for endog/exog variable extraction."""
    # DataFrame with only constant column
    endog = pd.Series([1, 2, 3], name="y")
    exog = pd.DataFrame({"const": [1, 1, 1]})

    variables = _get_endog_exog_variables(endog, exog)
    assert variables == ["y"]

    exog = pd.DataFrame({"x1": [4, 5, 6], "x2": [7, 8, 9]})
    variables = _get_endog_exog_variables(endog, exog)
    assert variables == ["y", "x1", "x2"]

    exog_noname = pd.Series([4, 5, 6])
    variables = _get_endog_exog_variables(endog, exog_noname)
    assert variables == ["y"]

    exog_empty = pd.DataFrame()
    variables = _get_endog_exog_variables(endog, exog_empty)
    assert variables == ["y"]


def test_get_formula_variables():
    """Test extracting variables from R-style formula string."""
    formula = "y ~ x1 + x2"
    assert _get_formula_variables(formula) == ["y", "x1", "x2"]

    # Complex formula with interactions and transformations
    formula_complex = "y ~ x1 + x2:x3 + x4*x5 + I(x6^2) + C(x7)"
    expected = ["y", "x1", "x2", "x3", "x4", "x5", "x6", "x7"]
    assert _get_formula_variables(formula_complex) == expected

    # Invalid missing parts
    assert _get_formula_variables("y") == []
    assert _get_formula_variables("~ x1") == ["x1"]


def test_get_formula_variables_edge_cases():
    """Edge cases for formula parsing."""
    # Duplicate variables should not appear twice
    formula = "y ~ x1 + x1 + x2"
    assert _get_formula_variables(formula) == ["y", "x1", "x2"]

    # Constant term should be ignored
    formula = "y ~ 1 + x1"
    assert _get_formula_variables(formula) == ["y", "x1"]

    # Extra whitespace
    formula = "  y   ~   x1   +   x2   "
    assert _get_formula_variables(formula) == ["y", "x1", "x2"]

    # Interaction only
    formula = "y ~ x1:x2"
    assert _get_formula_variables(formula) == ["y", "x1", "x2"]

    # Multiplicative interaction
    formula = "y ~ x1*x2"
    assert _get_formula_variables(formula) == ["y", "x1", "x2"]

    # Polynomial term
    formula = "y ~ I(x1^2)"
    assert _get_formula_variables(formula) == ["y", "x1"]

    # Categorical term
    formula = "y ~ C(x1)"
    assert _get_formula_variables(formula) == ["y", "x1"]

    # Nested transformations
    formula = "y ~ I((x1 + x2)^2)"
    result = _get_formula_variables(formula)

    # Depending on parser limitations, at least x1 and x2 should appear
    assert "y" in result
    assert "x1" in result
    assert "x2" in result

    # Empty RHS
    formula = "y ~ "
    assert _get_formula_variables(formula) == ["y"]

    # No dependent variable
    formula = "~ x1 + x2"
    assert _get_formula_variables(formula) == ["x1", "x2"]


def test_formula_parsing_empty_subterm():
    """Test that _get_formula_variables handles '1' and empty subterms correctly."""
    assert _get_formula_variables("y ~ 1") == ["y"]
    assert _get_formula_variables("y ~ ") == ["y"]


def test_extract_regression_info_invalid_val():
    """Trigger the except block in _extract_regression_info."""
    records = Records()
    # Create a table where the value next to "no. observations" is not a number
    df = pd.DataFrame({"Value": ["not_a_float"]}, index=["no. observations"])
    assert records._extract_regression_info([df]) == 0


def test_get_output_variables_regression_fallback():
    """Test fallback regression variable extraction."""
    records = Records()
    # Create a regression record manually WITHOUT 'variables' in properties
    table0 = pd.DataFrame({"y": [1]}, index=["Model"])
    table1 = pd.DataFrame({"coef": [1]}, index=["x1"])
    records.add(
        status="pass",
        output_type="regression",
        properties={"method": "ols"},  # no variables here
        sdc={},
        command="test",
        summary="test",
        outcome=pd.DataFrame(),
        output=[table0, table1],
    )
    rec = records.get_index(0)
    vars = records._get_output_variables(rec)
    assert vars == ["y", "x1"]


def test_build_variable_matrix_no_vars():
    """Trigger return early if no variables found."""
    records = Records()
    records.add(
        status="pass",
        output_type="table",
        properties={"method": "test"},
        sdc={},
        command="test",
        summary="test",
        outcome=pd.DataFrame(),
        output=[pd.DataFrame([[1]])],
    )
    summary_df = records.generate_summary()
    assert "variables" in summary_df.columns
    assert len(summary_df.columns) == 11


def test_build_variable_matrix_with_vars():
    """Ensure build variable matrix."""
    records = Records()
    records.add(
        status="pass",
        output_type="table",
        properties={"method": "test", "variables": ["v1", "v2"]},
        sdc={},
        command="test",
        summary="test",
        outcome=pd.DataFrame(),
        output=[pd.DataFrame([[1]])],
    )
    summary_df = records.generate_summary()
    assert "v1" in summary_df.columns
    assert "v2" in summary_df.columns
    assert summary_df.iloc[0]["v1"] == 1
    assert summary_df.iloc[0]["v2"] == 1
