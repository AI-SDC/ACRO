"""Unit tests for session management commands."""

import json
import os
import shutil

import matplotlib as mpl

mpl.use("Agg")
from unittest.mock import patch

import pandas as pd
import pytest

from acro import (
    ACRO,
    add_to_acro,
    record,
)
from acro.record import Records, load_records

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
    """
    Test finalise_interactive.

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
    # check SDC outcome DataFrame
    orig_df = orig0.output[0].reset_index()
    read_df = read0.output[0]
    pd.testing.assert_frame_equal(
        orig_df, read_df, check_names=False, check_dtype=False
    )
    if os.path.isdir(mypath):
        shutil.rmtree(mypath)


def test_create_dataframe(data):
    """Test correct functionality of code to create data frame."""


def test_toggle_suppression():
    """Test toggling suppression on/off."""
    acro = ACRO(suppress=False)
    assert not acro.suppress
    acro.enable_suppression()
    assert acro.suppress
    acro.disable_suppression()
    assert not acro.suppress


def test_add_to_acro_function(data, monkeypatch):
    """Add_to_acro() exercises by scanning a directory and creating results."""
    src_path = "test_add_to_acro"
    dest_path = "sdc_results"
    shutil.rmtree(src_path, ignore_errors=True)
    shutil.rmtree(dest_path, ignore_errors=True)
    # Create a simple CSV file in the source directory
    os.makedirs(src_path, exist_ok=True)
    table = pd.crosstab(data.year, data.grant_type)
    csv_path = os.path.join(src_path, "crosstab.csv")
    table.to_csv(csv_path)
    # Intercept any interactive prompts
    monkeypatch.setattr("builtins.input", lambda _: "test exception")
    add_to_acro(src_path, dest_path)
    assert os.path.exists(dest_path)
    assert "results.json" in os.listdir(dest_path)
    shutil.rmtree(src_path, ignore_errors=True)
    shutil.rmtree(dest_path, ignore_errors=True)


def test_records_add_with_none_defaults():
    """Records.add() with all-None optional args uses defaults."""
    records = Records()
    records.add(
        status="pass",
        output_type="table",
        properties=None,
        sdc=None,
        fair=None,
        command="test",
        summary="ok",
        outcome=None,
        output=None,
    )
    rec = records.get_index(0)
    assert rec.properties == {}
    assert rec.sdc == {}
    assert rec.fair == {}
    assert isinstance(rec.outcome, pd.DataFrame)
    assert rec.output == []
