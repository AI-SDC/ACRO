"""This module contains unit tests."""

import json
import os
import shutil

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from acro import ACRO, acro_tables, add_constant, add_to_acro, record, utils
from acro.record import Records, load_records

# pylint: disable=redefined-outer-name

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


def test_crosstab_without_suppression(data):
    """Crosstab threshold without automatic suppression."""
    acro = ACRO(suppress=False)
    _ = acro.crosstab(data.year, data.grant_type)
    output = acro.results.get_index(0)
    correct_summary: str = "fail; threshold: 6 cells may need suppressing; "
    assert output.summary == correct_summary
    assert 48 == output.output[0]["R/G"].sum()


def test_crosstab_multiple_aggregate_function(data, acro):
    """Crosstab with multiple agg funcs."""
    acro = ACRO(suppress=False)

    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc=["mean", "std"]
    )
    output = acro.results.get_index(0)
    correct_summary: str = (
        "fail; threshold: 12 cells may need suppressing;"
        " p-ratio: 2 cells may need suppressing; "
        "nk-rule: 2 cells may need suppressing; "
    )
    assert (
        output.summary == correct_summary
    ), f"\n{output.summary}\n should be \n{correct_summary}\n"
    print(f"{output.output[0]['mean'][ 'R/G'].sum()}")
    correctval = 97383496.0
    errmsg = f"{output.output[0]['mean']['R/G'].sum()} should be {correctval}"
    assert correctval == output.output[0]["mean"]["R/G"].sum(), errmsg


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
    results: Records = acro.finalise()
    correct_summary: str = "fail; threshold: 6 cells suppressed; "
    output = results.get_index(0)
    assert output.summary == correct_summary


def test_crosstab_multiple(data, acro):
    """Crosstab multiple rule test."""
    _ = acro.crosstab(
        data.year, data.grant_type, values=data.inc_grants, aggfunc="mean"
    )
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise()
    correct_summary: str = (
        "fail; threshold: 6 cells suppressed; p-ratio: 1 cells suppressed; "
        "nk-rule: 1 cells suppressed; "
    )
    output = results.get_index(0)
    assert output.summary == correct_summary


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
    results: Records = acro.finalise()
    correct_summary: str = "review; negative values found"
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    assert output_0.summary == correct_summary
    assert output_1.summary == correct_summary


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
    results: Records = acro.finalise()
    correct_summary: str = "pass"
    output_0 = results.get_index(0)
    assert output_0.summary == correct_summary


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
    results: Records = acro.finalise()
    correct_summary: str = (
        "fail; threshold: 14 cells suppressed; "
        "p-ratio: 2 cells suppressed; nk-rule: 2 cells suppressed; "
    )
    output_0 = results.get_index(0)
    assert output_0.summary == correct_summary


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
    results = acro.finalise()
    correct_summary: str = "pass; dof=807.0 >= 10"
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    assert output_0.summary == correct_summary
    assert output_1.summary == correct_summary


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
    results = acro.finalise()
    correct_summary: str = "pass; dof=806.0 >= 10"
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    output_2 = results.get_index(2)
    output_3 = results.get_index(3)
    assert output_0.summary == correct_summary
    assert output_1.summary == correct_summary
    assert output_2.summary == correct_summary
    assert output_3.summary == correct_summary


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


def test_output_removal(data, acro, monkeypatch):
    """Output removal and print test."""
    _ = acro.crosstab(data.year, data.grant_type)
    _ = acro.crosstab(data.year, data.grant_type)
    _ = acro.crosstab(data.year, data.grant_type)
    exceptions = ["I want it", "Let me have it", "Please!"]
    monkeypatch.setattr("builtins.input", lambda _: exceptions.pop(0))
    results: Records = acro.finalise()
    output_0 = results.get("output_0")
    output_1 = results.get("output_1")
    # remove something that is there
    acro.remove_output(output_0.uid)
    results = acro.finalise()
    correct_summary: str = "fail; threshold: 6 cells suppressed; "
    keys = results.get_keys()
    assert output_0.uid not in keys
    assert output_1.uid in keys
    assert output_1.summary == correct_summary
    acro.print_outputs()
    # remove something that is not there
    with pytest.raises(ValueError):
        acro.remove_output("123")


def test_load_output():
    """Empty array when loading output."""
    with pytest.raises(ValueError):
        record.load_output(PATH, [])


def test_finalise_invalid(data, acro):
    """Invalid output format when finalising."""
    _ = acro.crosstab(data.year, data.grant_type)
    output_0 = acro.results.get_index(0)
    output_0.exception = "Let me have it"
    with pytest.raises(ValueError):
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


def test_rename_output(data, acro):
    """Output renaming test."""
    _ = acro.crosstab(data.year, data.grant_type)
    _ = acro.crosstab(data.year, data.grant_type)
    acro.add_exception("output_0", "Let me have it")
    acro.add_exception("output_1", "I want this")
    results: Records = acro.finalise()
    output_0 = results.get_index(0)
    orig_name = output_0.uid
    new_name = "cross_table"
    acro.rename_output(orig_name, new_name)
    results = acro.finalise()
    assert output_0.uid == new_name
    assert orig_name not in results.get_keys()
    assert os.path.exists(f"outputs/{new_name}_0.csv")
    # rename an output that doesn't exist
    with pytest.raises(ValueError):
        acro.rename_output("123", "name")
    # rename an output to another that already exists
    with pytest.raises(ValueError):
        acro.rename_output("output_1", "cross_table")


def test_add_comments(data, acro):
    """Adding comments to output test."""
    _ = acro.crosstab(data.year, data.grant_type)
    acro.add_exception("output_0", "Let me have it")
    results: Records = acro.finalise()
    output_0 = results.get_index(0)
    assert output_0.comments == []
    comment = "This is a cross table between year and grant_type"
    acro.add_comments(output_0.uid, comment)
    assert output_0.comments == [comment]
    comment_1 = "6 cells were suppressed"
    acro.add_comments(output_0.uid, comment_1)
    assert output_0.comments == [comment, comment_1]
    # add a comment to something that is not there
    with pytest.raises(ValueError):
        acro.add_comments("123", "comment")


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
    results: Records = acro.finalise()
    correct_summary: str = "review; missing values found"
    output_0 = results.get_index(0)
    output_1 = results.get_index(1)
    assert output_0.summary == correct_summary
    assert output_1.summary == correct_summary
    assert output_0.exception == "I want it"
    assert output_1.exception == "Let me have it"


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
    with pytest.raises(ValueError):
        acro.add_exception("output_0", "Let me have it")


def test_add_to_acro(data, monkeypatch):
    """Adding an output that was generated without using acro to an acro object and
    creates a results file for checking.
    """
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

    with pytest.raises(ValueError):
        _ = acro.crosstab(
            data.year,
            data.grant_type,
            values=[data.inc_activity, data.inc_activity],
            aggfunc="mean",
        )
    with pytest.raises(ValueError):
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

    filename = "kaplan-mier.png"
    _ = acro.surv_func(data.futime, data.death, output="plot", filename=filename)
    assert os.path.exists(f"acro_artifacts/{filename}")
    acro.add_exception("output_0", "I need this")
    acro.add_exception("output_1", "Let me have it")
    results: Records = acro.finalise(path=PATH)
    output_1 = results.get_index(1)
    assert output_1.output == [filename]
