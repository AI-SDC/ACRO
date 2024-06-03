"""Unit tests."""

import json
import os
import shutil

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from acro import ACRO, acro_tables, add_constant, add_to_acro, record, utils
from acro.record import Records, load_records

# pylint: disable=redefined-outer-name,too-many-lines

PATH: str = "RES_PYTEST"


@pytest.fixture()
def data() -> pd.DataFrame:
    """Load test data."""
    path = os.path.join("data", "test_data.dta")
    data = pd.read_stata(path)
    return data


@pytest.fixture()
def acro() -> ACRO:
    """Initialise ACRO."""
    return ACRO(suppress=True)


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
    correct_summary: str = "fail; threshold: 6 cells suppressed; "
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
        "fail; threshold: 7 cells suppressed; p-ratio: 2 cells suppressed; "
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
        "fail; threshold: 14 cells suppressed; "
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
    correct_summary: str = "fail; threshold: 6 cells suppressed; "
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
    """Empty array when loading output."""
    with pytest.raises(ValueError, match="error loading output"):
        record.load_output(PATH, [])


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
    assert (orig.output[0].reset_index()).equals(read.output[0])
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


def test_missing(data, acro, monkeypatch):
    """Pivot table and Crosstab with negative values."""
    acro_tables.CHECK_MISSING_VALUES = True
    data.loc[0:10, "inc_grants"] = np.NaN
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mean"
    )
    _ = acro.pivot_table(
        data, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
    )
    exceptions = ["I want it", "Let me have it"]
    monkeypatch.setattr("builtins.input", lambda _: exceptions.pop(0))
    results: Records = acro.finalise(PATH)
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
    mask_data = {"col1": [np.NaN, True], "col2": [True, True]}
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
    data = sm.datasets.get_rdataset("flchain", "survival").data
    data = data.loc[data.sex == "F", :]
    _ = acro.surv_func(data.futime, data.death, output="table")
    output = acro.results.get_index(0)
    correct_summary: str = "fail; threshold: 3864 cells suppressed; "
    assert (
        output.summary == correct_summary
    ), f"\n{output.summary}\n should be \n{correct_summary}\n"

    filename = os.path.normpath("acro_artifacts/kaplan-meier_0.png")
    _ = acro.surv_func(data.futime, data.death, output="plot")
    assert os.path.exists(filename)
    acro.add_exception("output_0", "I need this")
    acro.add_exception("output_1", "Let me have it")
    results: Records = acro.finalise(path=PATH)
    output_1 = results.get_index(1)
    assert output_1.output == [filename]
    shutil.rmtree(PATH)


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
        "fail; threshold: 14 cells suppressed; "
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
    assert (
        output.summary == correct_summary
    ), f"\n{output.summary}\n should be \n{correct_summary}\n"
    print(f"{output.output[0]['mean']['R/G'].sum()}")
    correctval = 97383496.0
    errmsg = f"{output.output[0]['mean']['R/G'].sum()} should be {correctval}"
    assert correctval == output.output[0]["mean"]["R/G"].sum(), errmsg


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
    assert 8 == output.output[0].shape[1]
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


def test_histogram_discolsive(data, acro, caplog):
    """Test a discolsive histogram."""
    filename = os.path.normpath("acro_artifacts/histogram_0.png")
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
    """Test a non discolsive histogram."""
    filename = os.path.normpath("acro_artifacts/histogram_0.png")
    _ = acro.hist(data, "inc_grants", bins=1)
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
