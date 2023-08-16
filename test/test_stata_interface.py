"""This module contains unit tests for the stata interface."""

import os

import numpy as np
import pandas as pd
import pytest

import acro.stata_config as stata_config  # pylint: disable=consider-using-from-import
from acro import ACRO
from acro.acro_stata_parser import (
    apply_stata_expstmt,
    apply_stata_ifstmt,
    find_brace_contents,
    parse_and_run,
    parse_table_details,
)

# pylint: disable=redefined-outer-name


# @pytest.fixture
# def acro() -> ACRO:
#    """Initialise ACRO."""
#    return ACRO()


@pytest.fixture
def data() -> pd.DataFrame:
    """Load test data."""
    path = os.path.join("data", "test_data.dta")
    data = pd.read_stata(path)
    return data


def dummy_acrohandler(
    data, command, varlist, exclusion, exp, weights, options
):  # pylint:disable=too-many-arguments
    """
    Provides an alternative interface that mimics the code in acro.ado
    Most notably the presence of a global variable called stata_acro.
    """
    acro_outstr = parse_and_run(
        data, command, varlist, exclusion, exp, weights, options
    )

    return acro_outstr


# --- Helper functions-----------------------------------------------------
def test_find_brace_contents():
    """Tests helper function
    that extracts contents 'A B C'
    of something specified via X(A B C)
    on the stata command line.
    """
    options = "by(grant_type) contents(mean sd inc_activity) suppress nototals"
    res, substr = find_brace_contents("by", options)
    assert res
    assert substr == "grant_type"
    res, substr = find_brace_contents("contents", options)
    assert res
    assert substr == "mean sd inc_activity"
    res, substr = find_brace_contents("foo", options)
    assert not res
    assert substr == "foo not found"

    incomplete = "by(grant_type) contents(mean sd inc_activity suppress nototals"
    res, substr = find_brace_contents("contents", incomplete)
    assert not res
    assert substr == "phrase not completed"


def test_apply_stata_ifstmt(data):
    """Tests that if statements work for selection."""
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
    """Tests that in statements work for row selection."""
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
    """
    Series of checks that the varlist and options are parsed correctly
    by the helper function.
    """

    varlist = ["survivor", "grant_type", "year"]
    varnames = data.columns
    options = "by(grant_type) contents(mean sd inc_activity) suppress  nototals"
    details = parse_table_details(varlist, varnames, options)

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
    details = parse_table_details(varlist, varnames, options)
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
    Tests creation of an acro object at the start of a session
    For stata this gets held in a variable stata_acro
    Which is initialsied to the string "empty" in the acro.ado file
    Then should be pointed at a new acro instance.
    """
    # assert isinstance(stata_config.stata_acro, str)
    ret = dummy_acrohandler(
        data, command="init", varlist="", exclusion="", exp="", weights="", options=""
    )
    assert (
        ret == "acro analysis session created\n"
    ), f"wrong string for acro init: {ret}\n"
    errmsg = f"wrong type for stata_acro:{type(stata_config.stata_acro)}"
    assert isinstance(stata_config.stata_acro, ACRO), errmsg


def test_stata_print_outputs(data):
    """Checks print_outputs gets called."""
    ret = dummy_acrohandler(
        data,
        command="print_outputs",
        varlist=" inc_activity inc_grants inc_donations total_costs",
        exclusion="",
        exp="",
        weights="",
        options="",
    )
    assert len(ret) == 0, "return string should  be empty"


# ----main SDC functionality-------------------------------------
def test_simple_table(data):
    """
    Checks that the simple table command works as expected
    Does via reference to direct call to pd.crosstab()
    To make sure table specification is parsed correctly
    acro SDC analysis is tested elsewhere.
    """
    correct = (
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
    )
    ret = ret.replace("NaN", "0")
    ret = ret.replace(".0", "")
    assert ret.split() == correct.split(), f"got\n{ret}\n expected\n{correct}"


def test_stata_rename_outputs():
    """Tests renaming outputs
    assumes simple table has been created by earlier tests.
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
    )
    correct = f"output {the_output} renamed to {the_str}.\n"
    assert ret == correct, f"returned string:\n{ret}\nshould be:\n{correct}"
    value = stata_config.stata_acro.results.get_index(0).uid
    assert value == the_str, f"{value} should be\n{the_str}\n"


def test_stata_incomplete_output_commands():
    """Tests handling incomplete or wony outpu commands
    assumes simple table has been created by earlier tests.
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
    )
    correct = f"not enough arguments provided for command {command}.\n"
    assert ret == correct, f"returned string:\n{ret}\nshould be:\n{correct}"


def test_stata_add_comments():
    """
    Tests adding comments to  outputs
    assumes simple table has been created by earlier tests
    then renamed.
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
    )
    correct = f"Comments added to output {the_output}.\n"
    assert ret == correct, f"returned string:\n_{ret}_should be:\n_{correct}_"
    newcomments = "".join(stata_config.stata_acro.results.get(the_output).comments)
    assert newcomments == the_str, f"_{newcomments}_\nshould be:\n_{the_str}_"


def test_stata_add_exception():
    """
    Tests adding exception to  outputs
    assumes simple table has been created by earlier tests
    then renamed.
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
    )
    correct = f"Exception request added to output {the_output}.\n"
    assert ret == correct, f"returned string:\n{ret}\nshould be:\n{correct}"
    newcomments = "".join(stata_config.stata_acro.results.get(the_output).exception)
    assert newcomments == the_str, f"{newcomments} should be {the_str}"


def test_stata_remove_output():
    """
    Tests removing  outputs
    assumes simple table has been created and renamed by earlier tests.
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
    )
    correct = f"output {the_output} removed.\n"
    assert ret == correct, f"returned string:\n{ret}\nshould be:\n{correct}"
    errmsg = (
        "Should be no records left but results = "
        f"{stata_config.stata_acro.results.__dict__}\n"
    )
    assert not stata_config.stata_acro.results.results, errmsg


def test_stata_exclusion_in_context(data):
    """Tests that the subsetting code gets called properly from table handler."""
    # if condition
    correct1 = (
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
    )
    ret = ret.replace("NaN", "0")
    ret = ret.replace(".0", "")
    assert ret.split() == correct1.split(), f"got\n{ret}\n expected\n{correct1}"

    # in expression
    correct2 = (
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
    )
    correct3 = (
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
    """Weights are not currently supported."""
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
    )
    assert ret.split() == correct.split(), f"got\n{ret}\n expected\n{correct}"


# def test_table_aggcfn(data):
#     """
#     testing behaviour with aggregation function
#     """
#     correct = ""
#     ret = dummy_acrohandler(
#          data,
#          "table",
#          "survivor year",
#          exclusion="",
#          exp="",
#          weights="",
#          options=" contents(mean grant_type) suppress  nototals"
#      )
#     assert ret.split() == correct.split(), f"got\n{ret}\n expected\n{correct}"


def test_table_invalidvar(data):
    """Checking table deetails are valid."""

    correct = "Error: word foo in by-list is not a variables name"
    ret = dummy_acrohandler(
        data,
        "table",
        "survivor grant_type ",
        exclusion="",
        exp="",
        weights="",
        options="by(foo) ",
    )
    assert ret.split() == correct.split(), f"got\n{ret}\n expected\n{correct}"


def test_stata_probit(data):
    """Checks probit gets called correctly."""
    ret = dummy_acrohandler(
        data,
        command="probit",
        varlist=" survivor inc_activity inc_grants inc_donations total_costs",
        exclusion="",
        exp="",
        weights="",
        options="",
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
    """Checks linear regression called correctly."""
    ret = dummy_acrohandler(
        data,
        command="regress",
        varlist=" inc_activity inc_grants inc_donations total_costs",
        exclusion="",
        exp="",
        weights="",
        options="",
    )
    tokens = ret.split()
    idx = tokens.index("Residuals:")
    val = int(tokens[idx + 1])
    assert val == 807, f"{val} should be 807"
    idx = tokens.index("R-squared:")
    newval = float(tokens[idx + 1])
    assert newval == pytest.approx(0.894, 0.001)


def test_stata_logit(data):
    """Tests stata logit function."""
    ret = dummy_acrohandler(
        data,
        command="logit",
        varlist=" survivor inc_activity inc_grants inc_donations total_costs",
        exclusion="",
        exp="",
        weights="",
        options="",
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
    """Checks that user gets warning if they try to format table."""
    format_string = "acro does not currently support table formatting commands."
    correct = (
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
    """Checks finalise gets called correctly."""
    monkeypatch.setattr("builtins.input", lambda _: "Let me have it")
    ret = dummy_acrohandler(
        data,
        command="finalise",
        varlist="test_outputs xlsx",
        exclusion="",
        exp="",
        weights="",
        options="",
    )
    correct = "outputs and stata_outputs.json written\n"
    assert ret == correct, f"returned string {ret} should be {correct}\n"


def test_stata_finalise_default_filetype(monkeypatch):
    """Checks finalise gets called correctly."""
    monkeypatch.setattr("builtins.input", lambda _: "Let me have it")
    ret = dummy_acrohandler(
        data,
        command="finalise",
        varlist="test_outputs",
        exclusion="",
        exp="",
        weights="",
        options="",
    )
    correct = "outputs and stata_outputs.json written\n"
    assert ret == correct, f"returned string {ret} should be {correct}\n"


def test_stata_unknown(data):
    """Unknown acro command."""
    ret = dummy_acrohandler(
        data,
        command="foo",
        varlist=" survivor inc_activity inc_grants inc_donations total_costs",
        exclusion="",
        exp="",
        weights="",
        options="",
    )
    correct = "acro command not recognised: foo"
    assert ret == correct, f"got:\n{ret}\nexpected:\n{correct}\n"
