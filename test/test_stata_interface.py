"""Unit tests for the stata interface."""

import os
import shutil

import numpy as np
import pandas as pd
import pytest

import acro.stata_config as stata_config  # pylint: disable=consider-using-from-import
from acro import ACRO
from acro.acro_stata_parser import (
    apply_stata_expstmt,
    apply_stata_ifstmt,
    find_brace_word,
    parse_and_run,
    parse_table_details,
)

# pylint: disable=redefined-outer-name


# @pytest.fixture
# def acro() -> ACRO:
#    """Initialise ACRO."""
#    return ACRO()


@pytest.fixture()
def data() -> pd.DataFrame:
    """Load test data."""
    path = os.path.join("data", "test_data.dta")
    data = pd.read_stata(path)
    return data


def clean_up(name):
    """Remove unwanted files or directory."""
    if os.path.exists(name):
        if os.path.isfile(name):
            os.remove(name)
        elif os.path.isdir(name):
            shutil.rmtree(name)


def dummy_acrohandler(
    data, command, varlist, exclusion, exp, weights, options, stata_version
):  # pylint:disable=too-many-arguments
    """
    Provide an alternative interface that mimics the code in acro.ado.

    Most notably the presence of a global variable called stata_acro.
    """
    acro_outstr = parse_and_run(
        data, command, varlist, exclusion, exp, weights, options, stata_version
    )

    return acro_outstr


# --- Helper functions-----------------------------------------------------
def test_find_brace_word():
    """Extract contents 'A B C' specified as X(A B C) on the stata command line."""
    options = "by(grant_type) contents(mean sd inc_activity) suppress nototals"
    res, substr = find_brace_word("by", options)
    assert res
    assert substr == ["grant_type"]
    res, substr = find_brace_word("contents", options)
    assert res
    assert substr == ["mean sd inc_activity"]
    res, substr = find_brace_word("foo", options)
    assert not res
    assert substr == "foo not found"

    incomplete = "by(grant_type) contents(mean sd inc_activity suppress nototals"
    res, substr = find_brace_word("contents", incomplete)
    assert not res
    assert substr == "phrase not completed"


def test_apply_stata_ifstmt(data):
    """Test that if statements work for selection."""
    # empty ifstring
    ifstring = ""
    smaller = apply_stata_ifstmt(ifstring, data)
    assert smaller.equals(data), "should be same for empty ifstring"

    ifstring = "year!=2013"
    all_list = list(data["year"].unique())
    smaller = apply_stata_ifstmt(ifstring, data)
    all_list.remove(2013)
    assert list(smaller["year"].unique()) == all_list

    ifstring2 = "year != 2013 & year <2015"
    all_list.remove(2015)
    smaller2 = apply_stata_ifstmt(ifstring2, data)
    assert list(smaller2["year"].unique()) == all_list


def test_apply_stata_expstmt():
    """Test that in statements work for row selection."""
    data = np.zeros(100)
    for i in range(100):
        data[i] = i
    data = pd.DataFrame(data, columns=["vals"])
    length = 100
    # use of f/F and l/L for first and last with specified row range

    exp = "f/5"
    smaller = apply_stata_expstmt(exp, data)
    assert smaller.shape[0] == 5, data

    exp = "F/5"
    smaller = apply_stata_expstmt(exp, data)
    assert smaller.shape[0] == 5, data
    assert (smaller.iloc[-1].fillna(0).values == data.iloc[4].fillna(0).values).all()

    exp = "F/-5"
    smaller = apply_stata_expstmt(exp, data)
    assert smaller.shape[0] == length - 5, f"{smaller.shape[0]} != 95\n{data}"
    assert (
        smaller.iloc[-1].fillna(0).values == data.iloc[length - 6].fillna(0).values
    ).all()

    exp = "-6/l"
    smaller = apply_stata_expstmt(exp, data)
    assert smaller.shape[0] == 6, data
    assert (
        smaller.iloc[-1].fillna(0).values == data.iloc[length - 1].fillna(0).values
    ).all()

    exp = "-6/L"
    smaller = apply_stata_expstmt(exp, data)
    assert smaller.shape[0] == 6, data
    assert (
        smaller.iloc[-1].fillna(0).values == data.iloc[length - 1].fillna(0).values
    ).all()

    # invalid range should default to end of dataframe
    exp = "50/45"
    smaller = apply_stata_expstmt(exp, data)
    assert smaller.shape[0] == length - 49, f"smaller.shape[0] !=51,{smaller}"

    # missing / counts from front/back so same size but different
    exp = "40"
    smaller = apply_stata_expstmt(exp, data)
    assert smaller.shape[0] == 40, data

    exp = "-40"
    smaller2 = apply_stata_expstmt(exp, data)
    assert smaller2.shape[0] == 40
    assert not smaller2.equals(smaller), "counting from front/back should be different"

    exp = "gg"  # invalid exp returns empty dataframe
    smaller = apply_stata_expstmt(exp, data)
    assert smaller.shape[0] == 1, smaller


def test_parse_table_details(data):
    """Check that the varlist and options are parsed correctly by the helper function."""
    varlist = ["survivor", "grant_type", "year"]
    varnames = data.columns
    options = "by(grant_type) contents(mean sd inc_activity) suppress  nototals"
    details = parse_table_details(varlist, varnames, options, stata_version="16")

    errstring = f" rows {details['rowvars']} should be ['grant_type','survivor']"
    assert details["rowvars"] == ["grant_type", "survivor"], errstring

    errstring = f" cols {details['colvars']} should be ['year','grant_type']"
    assert details["colvars"] == ["year", "grant_type"], errstring

    errstring = f" aggfunctions {details['aggfuncs']} should be ['mean','sd']"
    assert details["aggfuncs"] == ["mean", "sd"], errstring

    errstring = f" values {details['values']} should be ['inc_activity']"
    assert details["values"] == ["inc_activity"], errstring

    assert not details["totals"], "totals should be False"
    assert details["suppress"], "suppress should be True"

    # invalid var in by list
    options = "by(football) contents(mean ) "
    details = parse_table_details(varlist, varnames, options, stata_version="16")
    correct = "Error: word football in by-list is not a variables name"
    errstring = f" rows {details['errmsg']} should be {correct}"
    assert details["errmsg"] == correct, errstring


# -----acro management----------------------------------------------------

# def test_stata_acro_notinit():
#     ''' should have to call init first'''
#     ret = dummy_acrohandler(
#         data, command="finalise", varlist="", exclusion="", exp="", weights="", options=""
#     )
#     assert (
#         ret == "You must run acro init before any other acro commands\n"
#     ), f"wrong string for acro command before init: {ret}\n"


def test_stata_acro_init():
    """
    Test creation of an acro object at the start of a session.

    For stata this gets held in a variable stata_acro
    Which is initialsied to the string "empty" in the acro.ado file
    Then should be pointed at a new acro instance.
    """
    # assert isinstance(stata_config.stata_acro, str)
    ret = dummy_acrohandler(
        data,
        command="init",
        varlist="",
        exclusion="",
        exp="",
        weights="",
        options="",
        stata_version="16",
    )
    assert (
        ret == "acro analysis session created\n"
    ), f"wrong string for acro init: {ret}\n"
    errmsg = f"wrong type for stata_acro:{type(stata_config.stata_acro)}"
    assert isinstance(stata_config.stata_acro, ACRO), errmsg


def test_stata_print_outputs(data):
    """Check print_outputs gets called."""
    ret = dummy_acrohandler(
        data,
        command="print_outputs",
        varlist=" inc_activity inc_grants inc_donations total_costs",
        exclusion="",
        exp="",
        weights="",
        options="",
        stata_version="16",
    )
    assert len(ret) == 0, "return string should  be empty"


# ----main SDC functionality-------------------------------------
def test_simple_table(data):
    """
    Check that the simple table command works as expected.

    Does via reference to direct call to pd.crosstab()
    To make sure table specification is parsed correctly
    acro SDC analysis is tested elsewhere.
    """
    correct = (
        "Total\n"
        "------------------------------------|\n"
        "grant_type     |G   |N    |R    |R/G|\n"
        "survivor       |    |     |     |   |\n"
        "------------------------------------|\n"
        "Dead in 2015   |18  |  0  |282  | 0 |\n"
        "Alive in 2015  |72  |354  |144  |48 |\n"
        "------------------------------------|\n"
    )
    ret = dummy_acrohandler(
        data,
        "table",
        "survivor grant_type",
        exclusion="",
        exp="",
        weights="",
        options="nototals",
        stata_version="16",
    )
    ret = ret.replace("NaN", "0")
    ret = ret.replace(".0", "")
    assert ret.split() == correct.split(), f"got\n{ret}\n expected\n{correct}"


def test_stata_rename_outputs():
    """Test renaming outputs.

    Assumes simple table has been created by earlier tests.
    """
    the_str = "renamed_output"
    the_output = "output_0"
    ret = dummy_acrohandler(
        data,
        "rename_output",
        the_output + " " + the_str,
        exclusion="",
        exp="",
        weights="",
        options="nototals",
        stata_version="16",
    )
    correct = f"output {the_output} renamed to {the_str}.\n"
    assert ret == correct, f"returned string:\n{ret}\nshould be:\n{correct}"
    value = stata_config.stata_acro.results.get_index(0).uid
    assert value == the_str, f"{value} should be\n{the_str}\n"


def test_stata_incomplete_output_commands():
    """Test handling incomplete or wrong output commands.

    Assumes simple table has been created by earlier tests.
    """
    # output to change not provided
    the_str = "renamed_output"
    the_output = ""
    command = "rename_output"
    ret = dummy_acrohandler(
        data,
        command,
        "",
        exclusion="",
        exp="",
        weights="",
        options="",
        stata_version="16",
    )
    correct = "syntax error: please pass the name of the output to be changed"
    assert ret == correct, f"returned string:\n{ret}\nshould be:\n{correct}"

    # ensure object is present
    # in our case we just renamed output 0 so it is not there
    the_str = "renamed_output"
    the_output = "output_0"
    ret = dummy_acrohandler(
        data,
        "rename_output",
        the_output,
        exclusion="",
        exp="",
        weights="",
        options="nototals",
        stata_version="16",
    )
    correct = f"no output with name  {the_output} in current acro session.\n"
    assert ret == correct, f"returned string:\n{ret}\nshould be:\n{correct}"

    # output present but not enough info provided to enact command
    the_str = ""
    the_output = "renamed_output"
    command = "rename_output"
    ret = dummy_acrohandler(
        data,
        command,
        the_output + " " + the_str,
        exclusion="",
        exp="",
        weights="",
        options="nototals",
        stata_version="16",
    )
    correct = f"not enough arguments provided for command {command}.\n"
    assert ret == correct, f"returned string:\n{ret}\nshould be:\n{correct}"


def test_stata_add_comments():
    """
    Test adding comments to outputs.

    Assumes simple table has been created by earlier tests then renamed.
    """
    the_str = "some comments"
    the_output = "renamed_output"
    ret = dummy_acrohandler(
        data,
        "add_comments",
        the_output + " " + the_str,
        exclusion="",
        exp="",
        weights="",
        options="nototals",
        stata_version="16",
    )
    correct = f"Comments added to output {the_output}.\n"
    assert ret == correct, f"returned string:\n_{ret}_should be:\n_{correct}_"
    newcomments = "".join(stata_config.stata_acro.results.get(the_output).comments)
    assert newcomments == the_str, f"_{newcomments}_\nshould be:\n_{the_str}_"


def test_stata_add_exception():
    """
    Test adding exception to outputs.

    Assumes simple table has been created by earlier tests then renamed.
    """
    the_str = "a reason"
    the_output = "renamed_output"
    ret = dummy_acrohandler(
        data,
        "add_exception",
        the_output + " " + the_str,
        exclusion="",
        exp="",
        weights="",
        options="nototals",
        stata_version="16",
    )
    correct = f"Exception request added to output {the_output}.\n"
    assert ret == correct, f"returned string:\n{ret}\nshould be:\n{correct}"
    newcomments = "".join(stata_config.stata_acro.results.get(the_output).exception)
    assert newcomments == the_str, f"{newcomments} should be {the_str}"


def test_stata_remove_output():
    """
    Test removing outputs.

    Assumes simple table has been created and renamed by earlier tests.
    """
    the_output = "renamed_output"
    ret = dummy_acrohandler(
        data,
        "remove_output",
        the_output,
        exclusion="",
        exp="",
        weights="",
        options="nototals",
        stata_version="16",
    )
    correct = f"output {the_output} removed.\n"
    assert ret == correct, f"returned string:\n{ret}\nshould be:\n{correct}"
    errmsg = (
        "Should be no records left but results = "
        f"{stata_config.stata_acro.results.__dict__}\n"
    )
    assert not stata_config.stata_acro.results.results, errmsg


def test_stata_exclusion_in_context(data):
    """Test that the subsetting code gets called properly from table handler."""
    # if condition
    correct1 = (
        "Total\n"
        "------------------|\n"
        "grant_type     |G |\n"
        "survivor       |  |\n"
        "------------------|\n"
        "Dead in 2015   |18|\n"
        "Alive in 2015  |72|\n"
        "------------------|\n"
    )
    ret = dummy_acrohandler(
        data,
        "table",
        "survivor grant_type",
        exclusion='grant_type == "G"',
        exp="",
        weights="",
        options="nototals",
        stata_version="16",
    )
    ret = ret.replace("NaN", "0")
    ret = ret.replace(".0", "")
    assert ret.split() == correct1.split(), f"got\n{ret}\n expected\n{correct1}"

    # in expression
    correct2 = (
        "Total\n"
        "------------------------------------|\n"
        "grant_type     |G   |N    |R    |R/G|\n"
        "survivor       |    |     |     |   |\n"
        "------------------------------------|\n"
        "Dead in 2015   |12  |  0  |158  | 0 |\n"
        "Alive in 2015  |30  |222  | 48  |30 |\n"
        "------------------------------------|\n"
    )
    ret2 = dummy_acrohandler(
        data,
        "table",
        "survivor grant_type",
        exclusion="",
        exp="1/500",
        weights="",
        options="nototals",
        stata_version="16",
    )
    ret2 = ret2.replace("NaN", "0")
    ret2 = ret2.replace(".0", "")
    assert ret2.split() == correct2.split(), f"got\n{ret2}\n expected\n{correct2}"

    # both
    rets3 = dummy_acrohandler(
        data,
        "table",
        "survivor grant_type",
        exclusion='grant_type == "G"',
        exp="1/500",
        weights="",
        options="nototals",
        stata_version="16",
    )
    correct3 = (
        "Total\n"
        "------------------|\n"
        "grant_type     |G |\n"
        "survivor       |  |\n"
        "------------------|\n"
        "Dead in 2015   |12|\n"
        "Alive in 2015  |30|\n"
        "------------------|\n"
    )
    rets3 = rets3.replace("NaN", "0")
    rets3 = rets3.replace(".0", "")
    assert rets3.split() == correct3.split(), f"got\n{rets3}\n expected\n{correct3}"


def test_table_weights(data):
    """Test weights are not currently supported."""
    weights = [0, 0, 0]
    correct = f"weights not currently implemented for _{weights}_\n"
    ret = dummy_acrohandler(
        data,
        "table",
        "survivor grant_type",
        exclusion="",
        exp="",
        weights=weights,
        options="nototals",
        stata_version="16",
    )
    assert ret.split() == correct.split(), f"got\n{ret}\n expected\n{correct}"


def test_table_aggcfn(data):
    """Test behaviour with aggregation function."""
    # ok
    correct = (
        "Total\n"
        "-----------------------------------------------------------------------------|\n"
        "year           |2010        |2011        |2012         |2013       |2014     |\n"
        "survivor       |            |            |             |           |         |\n"
        "-----------------------------------------------------------------------------|\n"
        "Dead in 2015   | 2056816.0  |1264158.00  |1625441.625  |1868730.5  |2182281.5|\n"
        "Alive in 2015  |10050917.0  |3468009.75  |2934010.750  |4579002.0  |3612917.5|\n"
        "-----------------------------------------------------------------------------|\n"
    )
    ret = dummy_acrohandler(
        data,
        "table",
        "survivor year",
        exclusion="year<2015",
        exp="1/100",
        weights="",
        options="contents(mean inc_activity) nototals",
        stata_version="16",
    )
    assert ret.split() == correct.split(), f"got:\n{ret}\naa\nexpected\n{correct}\nbb\n"

    # lists for index or columns
    # pylint: disable=duplicate-code
    correct = (
        "Total\n"
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
        "------------------------------------------------------------|\n\n"
    )
    ret = dummy_acrohandler(
        data,
        "table",
        " survivor grant_type",
        exclusion="grant_type != 'G'",
        exp="",
        weights="",
        options="by(year) contents(sum inc_activity) nototals",
        stata_version="16",
    )
    #    assert ret.split() == correct.split(), f"got\n{ret}\n expected\n{correct}"
    assert ret == correct, f"got\n{ret}\n expected\n{correct}"

    # pandas does not allows multiple arrays for values
    correct = (
        "pandas crosstab can  aggregate over multiple functions "
        "but only over one feature/attribute: provided as 'value'"
    )
    ret = dummy_acrohandler(
        data,
        "table",
        "year survivor ",
        exclusion="",
        exp="1/100",
        weights="",
        options="contents(mean inc_activity inc_grants) nototals",
        stata_version="16",
    )
    assert ret.split() == correct.split(), f"got\n{ret}\n expected\n{correct}"


def test_table_invalidvar(data):
    """Check table details are valid."""
    correct = "Error: word foo in by-list is not a variables name"
    ret = dummy_acrohandler(
        data,
        "table",
        "survivor grant_type ",
        exclusion="",
        exp="",
        weights="",
        options="by(foo) ",
        stata_version="16",
    )
    assert ret.split() == correct.split(), f"got\n{ret}\n expected\n{correct}"


def test_stata_probit(data):
    """Check probit gets called correctly."""
    ret = dummy_acrohandler(
        data,
        command="probit",
        varlist=" survivor inc_activity inc_grants inc_donations total_costs",
        exclusion="",
        exp="",
        weights="",
        options="",
        stata_version="16",
    )
    tokens = ret.split()
    idx = tokens.index("Residuals:")
    val = tokens[idx + 1]
    if val[-1] == "|":
        val = val[0:-1]
    assert float(val) == pytest.approx(806.0, 0.01), f"{val} should be 806"
    idx = tokens.index("R-squ.:")
    val = tokens[idx + 1]
    if val[-1] == "|":
        val = val[0:-1]
    val = float(val)
    assert val == pytest.approx(0.208, 0.01)


def test_stata_linregress(data):
    """Check linear regression called correctly."""
    ret = dummy_acrohandler(
        data,
        command="regress",
        varlist=" inc_activity inc_grants inc_donations total_costs",
        exclusion="",
        exp="",
        weights="",
        options="",
        stata_version="16",
    )
    tokens = ret.split()
    idx = tokens.index("Residuals:")
    val = int(tokens[idx + 1])
    assert val == 807, f"{val} should be 807"
    idx = tokens.index("R-squared:")
    newval = float(tokens[idx + 1])
    assert newval == pytest.approx(0.894, 0.001)


def test_stata_logit(data):
    """Test stata logit function."""
    ret = dummy_acrohandler(
        data,
        command="logit",
        varlist=" survivor inc_activity inc_grants inc_donations total_costs",
        exclusion="",
        exp="",
        weights="",
        options="",
        stata_version="16",
    )

    tokens = ret.split()
    idx = tokens.index("Residuals:")
    val = tokens[idx + 1]
    if val[-1] == "|":
        val = val[0:-1]
    assert float(val) == pytest.approx(806.0, 0.01), f"{val} should be 806"
    idx = tokens.index("R-squ.:")
    val = tokens[idx + 1]
    if val[-1] == "|":
        val = val[0:-1]
    val = float(val)
    assert val == pytest.approx(0.214, 0.01)


def test_unsupported_formatting_options(data):
    """Check that user gets warning if they try to format table."""
    format_string = "acro does not currently support table formatting commands."
    correct = (
        "Total\n"
        "------------------------------------|\n"
        "grant_type     |G   |N    |R    |R/G|\n"
        "survivor       |    |     |     |   |\n"
        "------------------------------------|\n"
        "Dead in 2015   |18  |  0  |282  | 0 |\n"
        "Alive in 2015  |72  |354  |144  |48 |\n"
        "------------------------------------|\n"
    )
    # pylint:disable=duplicate-code
    for bad_option in [
        "cellwidth",
        "csepwidth",
        "stubwidth",
        "scsepwidth",
        "center",
        "left",
    ]:
        ret = dummy_acrohandler(
            data,
            "table",
            "survivor grant_type",
            exclusion="",
            exp="",
            weights="",
            options=f"{bad_option} nototals",
            stata_version="16",
        )

        rets = ret.split("\n", 1)
        assert len(rets) == 2, "table should have warning prepended"
        errmsg = f"first line {rets[0]} should be {format_string}"
        assert rets[0] == format_string, errmsg
        ret = rets[1]
        ret = ret.replace("NaN", "0")
        ret = ret.replace(".0", "")
        assert ret.split() == correct.split(), f"got\n{ret}\n expected\n{correct}"


def test_stata_finalise(monkeypatch):
    """Check finalise gets called correctly."""
    monkeypatch.setattr("builtins.input", lambda _: "Let me have it")
    ret = dummy_acrohandler(
        data,
        command="finalise",
        varlist="test_outputs xlsx",
        exclusion="",
        exp="",
        weights="",
        options="",
        stata_version="16",
    )
    correct = "outputs and stata_outputs.json written\n"
    assert ret == correct, f"returned string {ret} should be {correct}\n"


def test_stata_finalise_default_filetype(monkeypatch):
    """Check finalise gets called correctly."""
    monkeypatch.setattr("builtins.input", lambda _: "Let me have it")
    ret = dummy_acrohandler(
        data,
        command="finalise",
        varlist="test_outputs",
        exclusion="",
        exp="",
        weights="",
        options="",
        stata_version="16",
    )
    correct = "outputs and stata_outputs.json written\n"
    assert ret == correct, f"returned string {ret} should be {correct}\n"


def test_stata_unknown(data):
    """Test unknown acro command."""
    ret = dummy_acrohandler(
        data,
        command="foo",
        varlist=" survivor inc_activity inc_grants inc_donations total_costs",
        exclusion="",
        exp="",
        weights="",
        options="",
        stata_version="16",
    )
    correct = "acro command not recognised: foo"
    assert ret == correct, f"got:\n{ret}\nexpected:\n{correct}\n"


def test_cleanup():
    """Remove files created during tests."""
    names = ["test_outputs", "test_add_to_acro", "sdc_results", "RES_PYTEST"]
    for name in names:
        clean_up(name)
