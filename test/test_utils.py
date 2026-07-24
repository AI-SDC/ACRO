"""Unit tests for utils.py."""

import pandas as pd

from acro import utils


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
