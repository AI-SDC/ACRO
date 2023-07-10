"""This module contains unit tests for the stata interface."""

import os

import pandas as pd
import pytest

from acro import ACRO
from stata.acro_stata_parser import (
    apply_stata_expstmt,
    apply_stata_ifstmt,
    find_brace_contents,
    parse_and_run,
    parse_table_details,
)

# pylint: disable=redefined-outer-name


@pytest.fixture
def acro() -> ACRO:
    """Initialise ACRO."""
    return ACRO()


@pytest.fixture
def data() -> pd.DataFrame:
    """Load test data."""
    path = os.path.join("data", "test_data.dta")
    data = pd.read_stata(path)
    return data


# --- global object and dummy code to replace things in acro.ado
stata_acro = "empty"  # pylint:disable=invalid-name


def dummy_acrohandler(
    data, command, varlist, exclusion, exp, weights, options
):  # pylint:disable=too-many-arguments
    """
    Provides an alternative interface that mimics the code in acro.ado
    Most notably the presence of a global variable called stata_acro.
    """
    # global stata_acro
    acro_outstr = parse_and_run(
        data, command, varlist, exclusion, exp, weights, options
    )

    return acro_outstr


# --- Helper functions
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


def test_apply_stata_ifstmt(data):
    """Tests that if statements work for selection."""
    ifstring = "year!=2013"
    all_list = list(data["year"].unique())
    smaller = apply_stata_ifstmt(ifstring, data)
    all_list.remove(2013)
    assert list(smaller["year"].unique()) == all_list
    ifstring2 = "year != 2013 & year <2015"
    all_list.remove(2015)
    smaller2 = apply_stata_ifstmt(ifstring2, data)
    assert list(smaller2["year"].unique()) == all_list


def test_apply_stata_expstmt(data):
    """Tests that in statements work for row selection."""
    length = data.shape[0]
    # use of f/F and l/L for first and last with specified row range
    exp = "f/5"
    smaller = apply_stata_expstmt(exp, data)
    assert smaller.shape[0] == 5
    assert (smaller.iloc[-1].fillna(0).values == data.iloc[4].fillna(0).values).all()

    exp = "F/5"
    smaller = apply_stata_expstmt(exp, data)
    assert smaller.shape[0] == 5
    assert (smaller.iloc[-1].fillna(0).values == data.iloc[4].fillna(0).values).all()

    exp = "-6/l"
    smaller = apply_stata_expstmt(exp, data)
    assert smaller.shape[0] == 5
    assert (
        smaller.iloc[-1].fillna(0).values == data.iloc[length - 2].fillna(0).values
    ).all()

    exp = "-6/L"
    smaller = apply_stata_expstmt(exp, data)
    assert smaller.shape[0] == 5
    assert (
        smaller.iloc[-1].fillna(0).values == data.iloc[length - 2].fillna(0).values
    ).all()

    # invalid range should default to end of dataframe
    exp = "500/450"
    smaller = apply_stata_expstmt(exp, data)
    assert smaller.shape[0] == length - 1 - 500


# -----acro management
def test_stata_acro_init():
    """
    Tests creation of an acro object at the start of a session
    For stata this gets held in a variable stata_acro
    Which is initialsied to the string "empty" in the acro.ado file
    Then should be pointed at a new acro instance.
    """
    assert isinstance(stata_acro, str)
    ret = dummy_acrohandler(
        data, command="init", varlist="", exclusion="", exp="", weights="", options=""
    )
    assert (
        ret == "acro analysis session created\n"
    ), f"wrong string for acro init: {ret}\n"
    # assert isinstance(stata_acro,ACRO),f'wrong type for stata_acro:{type(stata_acro)}'


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


# ----main SDC functionality
def test_simple_table(data):
    """
    Checks that the simple table command works as expected
    Does via reference to direct call to pd.crosstab()
    To make sure table specification is parsed correctly
    acro SDC analysis is tested elsewhere.
    """
    correct = pd.crosstab(
        index=data["survivor"], columns=data["grant_type"]
    ).to_string()
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
    ret = ret.replace("\n", ",")
    tokens = ret.split(",")
    idx = tokens.index("  Df Residuals:      ")
    residuals = int(tokens[idx + 1])
    assert residuals == 806, f"{residuals} should be 806"
    idx = tokens.index("  Pseudo R-squ.:     ")
    rsquared = float(tokens[idx + 1])
    assert rsquared == pytest.approx(0.208, 0.01)


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
    ret = ret.replace("\n", ",")
    tokens = ret.split(",")
    idx = tokens.index("Df Residuals:    ")
    residuals = int(tokens[idx + 1])
    assert residuals == 807, f"{residuals} should be 807"
    idx = tokens.index("  R-squared:         ")
    rsquared = float(tokens[idx + 1])
    assert rsquared == pytest.approx(0.894, 0.001)


def test_unsupported_formatting_options(data):
    """Checks that user gets warning if they try to format table."""
    format_string = "acro does not currently support table formatting commands."
    correct = pd.crosstab(
        index=data["survivor"], columns=data["grant_type"]
    ).to_string()
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
        varlist="",
        exclusion="",
        exp="",
        weights="",
        options="",
    )
    correct = "outputs and stata_out.json written\n"
    assert ret == correct, f"returned string {ret} should be {correct}\n"
