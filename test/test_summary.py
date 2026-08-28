"""Tests for session summary report generation."""

from __future__ import annotations

import csv as csv_mod
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from acro import ACRO
from acro.constants import ARTIFACTS_DIR
from acro.record import Record, Records, _copy_output_file_if_needed
from acro.summary import (
    SUMMARY_CSV_FILENAME,
    SUMMARY_CSV_KEY,
    SUMMARY_FILENAME,
    SUMMARY_JSON_KEY,
    SUMMARY_OUTPUT_TYPE,
    SUMMARY_WARNING_COMMENT,
    MetadataExtractor,
    SummaryGenerator,
    VariableMatrixBuilder,
    _convert_numpy_types,
    generate_session_summary,
    load_session_summary,
    write_summary_csv,
)


def make_record(
    uid: str = "output_0",
    status: str = "pass",
    output_type: str = "table",
    properties: dict | None = None,
    sdc: dict | None = None,
    fair: dict | None = None,
    command: str = "crosstab()",
    summary: str = "pass",
    outcome: pd.DataFrame | None = None,
    output: list[Any] | None = None,
    comments: list[str] | None = None,
) -> Record:
    """Instantiate a valid Record object for tests."""
    return Record(
        uid=uid,
        status=status,
        output_type=output_type,
        properties=properties if properties is not None else {},
        sdc=sdc if sdc is not None else {},
        fair=fair if fair is not None else {},
        command=command,
        summary=summary,
        outcome=outcome
        if outcome is not None
        else pd.DataFrame({"col": ["ok"]}, index=["row"]),
        output=output if output is not None else [],
        comments=comments,
    )


def test_extract_session_metadata_empty_records():
    """Extract session metadata from empty Records object."""
    records = Records()
    timestamp = "2024-01-15T10:00:00"
    version = "0.5.0"

    metadata = MetadataExtractor.extract_session_metadata(records, timestamp, version)

    assert metadata["version"] == version
    assert metadata["timestamp"] == timestamp
    assert metadata["total_outputs"] == 0
    assert metadata["status_counts"] == {}
    assert metadata["type_counts"] == {}


def test_extract_session_metadata_single_output():
    """Extract session metadata with a single output record."""
    records = Records()
    record = make_record(uid="output_0", status="pass", output_type="table")
    records.results[record.uid] = record

    metadata = MetadataExtractor.extract_session_metadata(
        records, "2024-01-15T10:00:00", "0.5.0"
    )

    assert metadata["total_outputs"] == 1
    assert metadata["status_counts"] == {"pass": 1}  # nosec B105 - "pass" is an SDC status, not a password
    assert metadata["type_counts"] == {"table": 1}


def test_extract_session_metadata_multiple_outputs():
    """Extract session metadata with multiple outputs of various types and statuses."""
    records = Records()
    r1 = make_record(uid="output_0", status="pass", output_type="table")
    r2 = make_record(uid="output_1", status="fail", output_type="regression")
    r3 = make_record(uid="output_2", status="review", output_type="table")
    r4 = make_record(uid="output_3", status="pass", output_type="custom")

    for r in [r1, r2, r3, r4]:
        records.results[r.uid] = r

    metadata = MetadataExtractor.extract_session_metadata(
        records, "2024-01-15T10:00:00", "0.5.0"
    )

    assert metadata["total_outputs"] == 4
    assert metadata["status_counts"] == {"pass": 2, "fail": 1, "review": 1}  # nosec B105 - "pass" is an SDC status, not a password
    assert metadata["type_counts"] == {
        "table": 2,
        "regression": 1,
        "custom": 1,
    }


def test_extract_output_metadata_complete_fair():
    """Extract output metadata from record with complete FAIR metadata."""
    record = make_record(
        uid="output_0",
        status="pass",
        output_type="table",
        fair={
            "dependent": "income",
            "independent": ["age_group", "gender"],
            "analysis_name": "FrequencyTable",
        },
    )

    metadata = MetadataExtractor.extract_output_metadata(record)

    assert metadata["uid"] == "output_0"
    assert metadata["output_type"] == "table"
    assert metadata["dependent_variables"] == "income"
    assert metadata["independent_variables"] == ["age_group", "gender"]
    assert metadata["analysis_name"] == "FrequencyTable"


@pytest.mark.parametrize(
    (
        "fair_input",
        "properties",
        "command",
        "expected_dep",
        "expected_indep",
        "expected_analysis",
    ),
    [
        # Standard record with method property
        (
            {"dependent": "income", "independent": ["grant_type"]},
            {"method": "crosstab"},
            "crosstab()",
            "income",
            ["grant_type"],
            "crosstab",
        ),
        # Record with None values in fair dictionary
        (
            {"dependent": None, "independent": None},
            {"method": "crosstab"},
            "crosstab()",
            "unknown",
            [],
            "crosstab",
        ),
        # Record with missing dependent variable
        (
            {"dependent": "unknown", "independent": ["year"]},
            {"method": "ols"},
            "ols()",
            "unknown",
            ["year"],
            "ols",
        ),
        # Fallback to command name when method property is absent
        (
            {},
            {},
            "hist()",
            "unknown",
            [],
            "hist",
        ),
        # Fallback to output_type when both properties and command are absent
        (
            None,
            {},
            "",
            "unknown",
            [],
            "table",
        ),
    ],
)
def test_extract_output_metadata_variations(
    fair_input, properties, command, expected_dep, expected_indep, expected_analysis
):
    """Test resolution of variables and analysis names across different record configurations."""
    record = make_record(
        uid="output_x", fair=fair_input, properties=properties, command=command
    )
    metadata = MetadataExtractor.extract_output_metadata(record)

    assert metadata["dependent_variables"] == expected_dep
    assert metadata["independent_variables"] == expected_indep
    assert metadata["analysis_name"] == expected_analysis


@pytest.mark.parametrize(
    ("metadata", "expected_vars"),
    [
        (
            {
                "dependent_variables": "income",
                "independent_variables": ["age", "gender"],
            },
            {"income", "age", "gender"},
        ),
        (
            {
                "dependent_variables": ["income", "score"],
                "independent_variables": ["age"],
            },
            {"income", "score", "age"},
        ),
        (
            {"dependent_variables": "income", "independent_variables": []},
            {"income"},
        ),
        (
            {
                "dependent_variables": "unknown",
                "independent_variables": ["age", "gender"],
            },
            {"age", "gender"},
        ),
        (
            {"dependent_variables": "none", "independent_variables": ["age"]},
            {"age"},
        ),
        (
            {"dependent_variables": "", "independent_variables": ["age"]},
            {"age"},
        ),
        (
            {
                "dependent_variables": ["unknown", "score"],
                "independent_variables": ["age", "none", ""],
            },
            {"score", "age"},
        ),
        (
            {"dependent_variables": "income", "independent_variables": "region"},
            {"income", "region"},
        ),
        (
            {},
            set(),
        ),
    ],
)
def test_get_all_variables(metadata, expected_vars):
    """Extract all variables across different variations of metadata."""
    vars_set = VariableMatrixBuilder.get_all_variables(metadata)
    assert vars_set == expected_vars


def test_build_matrix_empty_list():
    """Build matrix with empty metadata list."""
    matrix = VariableMatrixBuilder.build_matrix([])
    assert matrix == {}


def test_build_matrix_single_output():
    """Build matrix for a single output."""
    metadata_list = [
        {
            "uid": "output_0",
            "dependent_variables": "y",
            "independent_variables": ["x1", "x2"],
        }
    ]
    matrix = VariableMatrixBuilder.build_matrix(metadata_list)

    assert "output_0" in matrix
    assert matrix["output_0"] == {"x1": 1, "x2": 1, "y": 1}


def test_build_matrix_shared_variables():
    """Build matrix with multiple outputs sharing some variables."""
    metadata_list = [
        {
            "uid": "output_0",
            "dependent_variables": "income",
            "independent_variables": ["age", "gender"],
        },
        {
            "uid": "output_1",
            "dependent_variables": "income",
            "independent_variables": ["education", "region"],
        },
    ]
    matrix = VariableMatrixBuilder.build_matrix(metadata_list)

    assert matrix["output_0"] == {
        "age": 1,
        "education": 0,
        "gender": 1,
        "income": 1,
        "region": 0,
    }
    assert matrix["output_1"] == {
        "age": 0,
        "education": 1,
        "gender": 0,
        "income": 1,
        "region": 1,
    }


def test_build_matrix_skips_entries_without_uid():
    """Entries missing a uid should be safely skipped."""
    metadata_list = [
        {"dependent_variables": "income", "independent_variables": ["age"]},
        {
            "uid": "output_0",
            "dependent_variables": "income",
            "independent_variables": ["gender"],
        },
    ]
    matrix = VariableMatrixBuilder.build_matrix(metadata_list)
    assert list(matrix.keys()) == ["output_0"]
    assert matrix["output_0"]["income"] == 1
    assert matrix["output_0"]["gender"] == 1
    assert matrix["output_0"]["age"] == 0


def test_generate_returns_complete_structure():
    """Generate returns complete summary structure."""
    records = Records()
    generator = SummaryGenerator(records, "0.5.0")
    summary = generator.generate()

    assert "metadata" in summary
    assert "outputs" in summary
    assert "variable_matrix" in summary


def test_generate_empty_records():
    """Generate with empty Records returns valid empty sections."""
    records = Records()
    generator = SummaryGenerator(records, "0.5.0")
    summary = generator.generate()

    assert summary["metadata"]["total_outputs"] == 0
    assert summary["outputs"] == []
    assert summary["variable_matrix"] == {}


def test_generate_with_multiple_records():
    """Generate with multiple output types."""
    records = Records()
    r1 = make_record(
        uid="output_0",
        status="pass",
        output_type="table",
        properties={"method": "crosstab"},
        fair={"dependent": "income", "independent": ["gender"]},
    )
    r2 = make_record(
        uid="output_1",
        status="review",
        output_type="regression",
        properties={"method": "ols"},
        fair={"dependent": "income", "independent": ["age"]},
    )
    records.results[r1.uid] = r1
    records.results[r2.uid] = r2

    generator = SummaryGenerator(records, "0.5.0")
    summary = generator.generate()

    assert summary["metadata"]["total_outputs"] == 2
    assert len(summary["outputs"]) == 2
    assert len(summary["variable_matrix"]) == 2
    assert summary["variable_matrix"]["output_0"]["gender"] == 1
    assert summary["variable_matrix"]["output_0"]["age"] == 0
    assert summary["variable_matrix"]["output_1"]["gender"] == 0
    assert summary["variable_matrix"]["output_1"]["age"] == 1


def test_convert_numpy_types_json_serializable():
    """Verify _convert_numpy_types enables JSON serialization of numpy structures."""
    data = {
        "int_val": np.int64(42),
        "float_val": np.float64(3.14),
        "array_val": np.array([1, 2, 3]),
        "nested": {
            "sub_int": np.int32(10),
            "sub_list": [np.float32(1.5), np.int64(7)],
        },
    }
    converted = _convert_numpy_types(data)
    serialized = json.dumps(converted)
    deserialized = json.loads(serialized)

    assert deserialized["int_val"] == 42
    assert deserialized["float_val"] == pytest.approx(3.14)
    assert deserialized["array_val"] == [1, 2, 3]
    assert deserialized["nested"]["sub_int"] == 10
    assert deserialized["nested"]["sub_list"] == [1.5, 7]


def test_generate_session_summary_creates_json_file(tmp_path):
    """Generate session summary creates correctly formatted JSON file."""
    records = Records()
    record = make_record(uid="output_0", status="pass", output_type="table")
    records.results[record.uid] = record

    output_path = str(tmp_path)
    generate_session_summary(records, output_path)

    summary_file = tmp_path / SUMMARY_FILENAME
    assert summary_file.exists()

    content = summary_file.read_text(encoding="utf-8")
    parsed = json.loads(content)
    assert parsed["metadata"]["total_outputs"] == 1
    # Check pretty printing indentation
    assert '\n    "metadata": {' in content


def test_generate_session_summary_adds_custom_output_with_warning(tmp_path):
    """Generate session summary adds JSON and CSV custom outputs to records with DO NOT RELEASE warning and meaningful names."""
    records = Records()
    output_path = str(tmp_path)

    generate_session_summary(records, output_path)

    assert len(records.results) == 2
    assert SUMMARY_JSON_KEY in records.results
    assert SUMMARY_CSV_KEY in records.results

    json_record = records.get(SUMMARY_JSON_KEY)
    assert json_record.uid == SUMMARY_JSON_KEY
    assert json_record.output_type == "custom"
    assert json_record.status == "review"
    assert json_record.comments == [SUMMARY_WARNING_COMMENT]
    assert json_record.output == [os.path.normpath(str(tmp_path / SUMMARY_FILENAME))]

    csv_record = records.get(SUMMARY_CSV_KEY)
    assert csv_record.uid == SUMMARY_CSV_KEY
    assert csv_record.output_type == "custom"
    assert csv_record.status == "review"
    assert csv_record.comments == [SUMMARY_WARNING_COMMENT]
    assert csv_record.output == [os.path.normpath(str(tmp_path / SUMMARY_CSV_FILENAME))]


def test_generate_session_summary_handles_write_failure(tmp_path, caplog):
    """File write errors should be logged as error without adding broken custom output."""
    records = Records()
    with patch("builtins.open", side_effect=PermissionError("Cannot write")):
        generate_session_summary(records, str(tmp_path))

    assert "Failed to write session summary" in caplog.text
    assert len(records.results) == 0


def test_generate_session_summary_handles_add_custom_failure(tmp_path, caplog):
    """Errors in records.add_custom should be logged without raising exceptions."""
    records = Records()
    with patch.object(
        records, "add_custom", side_effect=RuntimeError("Add custom failed")
    ):
        generate_session_summary(records, str(tmp_path))

    assert "Failed to add session summary as custom output" in caplog.text


def test_load_session_summary_valid(tmp_path):
    """Load session summary from valid JSON file."""
    summary_data = {
        "metadata": {"total_outputs": 1},
        "outputs": [{"uid": "output_0"}],
        "variable_matrix": {"output_0": {"age": 1}},
    }

    summary_file = tmp_path / SUMMARY_FILENAME
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f)

    loaded = load_session_summary(str(tmp_path))
    assert loaded == summary_data


def test_load_session_summary_missing_file(tmp_path):
    """Load session summary raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError, match="Session summary not found"):
        load_session_summary(str(tmp_path / "nonexistent"))


def test_load_session_summary_invalid_json(tmp_path):
    """Load session summary raises ValueError for malformed JSON."""
    summary_file = tmp_path / SUMMARY_FILENAME
    summary_file.write_text("invalid { json content", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON in session summary file"):
        load_session_summary(str(tmp_path))


def test_load_session_summary_io_error(tmp_path):
    """Load session summary raises ValueError when read fails."""
    summary_file = tmp_path / SUMMARY_FILENAME
    summary_file.write_text("{}", encoding="utf-8")

    with (
        patch("builtins.open", side_effect=OSError("Read error")),
        pytest.raises(ValueError, match="Failed to read session summary file"),
    ):
        load_session_summary(str(tmp_path))


def test_load_session_summary_missing_sections(tmp_path):
    """Load session summary raises ValueError when required sections are missing."""
    invalid_summary: dict[str, dict[str, int]] = {"metadata": {}}

    summary_file = tmp_path / SUMMARY_FILENAME
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(invalid_summary, f)

    with pytest.raises(ValueError, match="Session summary missing required sections"):
        load_session_summary(str(tmp_path))


def test_summary_constants():
    """Verify module constants."""
    assert SUMMARY_FILENAME == "session_summary.json"
    assert SUMMARY_CSV_FILENAME == "session_summary.csv"
    assert SUMMARY_OUTPUT_TYPE == "summary_report"
    assert "DO NOT RELEASE" in SUMMARY_WARNING_COMMENT
    assert SUMMARY_JSON_KEY == "2ndary_risk_summary_json-DONT_RELEASE"
    assert SUMMARY_CSV_KEY == "2ndary_risk_summary_csv-DONT_RELEASE"


def test_full_acro_session_summary_generation(tmp_path):
    """Test a complete ACRO session with crosstab, pivot_table, regression, and finalise."""
    acro = ACRO(suppress=False)
    sample_df = pd.DataFrame(
        {
            "year": [
                2010,
                2011,
                2012,
                2010,
                2011,
                2012,
                2010,
                2011,
                2012,
                2010,
                2011,
                2012,
            ],
            "grant_type": ["G", "G", "G", "R", "R", "R", "N", "N", "N", "G", "R", "N"],
            "inc_activity": [
                10.0,
                20.0,
                30.0,
                40.0,
                50.0,
                60.0,
                70.0,
                80.0,
                90.0,
                100.0,
                110.0,
                120.0,
            ],
        }
    )

    acro.crosstab(
        sample_df["year"],
        sample_df["grant_type"],
    )

    acro.pivot_table(
        data=sample_df,
        values="inc_activity",
        index="year",
        columns="grant_type",
        aggfunc="mean",
    )

    acro.ols(sample_df["inc_activity"], sample_df["year"])

    output_dir = str(tmp_path / "acro_results")
    acro.finalise(output_dir, ext="json")

    summary_file = Path(output_dir) / SUMMARY_FILENAME
    assert summary_file.exists()

    summary = load_session_summary(output_dir)

    assert summary["metadata"]["total_outputs"] == 3
    assert summary["metadata"]["type_counts"] == {"table": 2, "regression": 1}

    assert len(summary["outputs"]) == 3
    outputs_by_uid = {out["uid"]: out for out in summary["outputs"]}

    assert outputs_by_uid["output_0"]["analysis_name"] == "crosstab"
    assert set(outputs_by_uid["output_0"]["independent_variables"]) == {
        "year",
        "grant_type",
    }

    assert outputs_by_uid["output_1"]["analysis_name"] == "pivot_table"
    assert outputs_by_uid["output_1"]["dependent_variables"] == "inc_activity"
    assert set(outputs_by_uid["output_1"]["independent_variables"]) == {
        "year",
        "grant_type",
    }

    assert outputs_by_uid["output_2"]["analysis_name"] == "ols"
    assert outputs_by_uid["output_2"]["dependent_variables"] == "inc_activity"

    matrix = summary["variable_matrix"]
    assert "output_0" in matrix
    assert "output_1" in matrix
    assert "output_2" in matrix

    assert matrix["output_0"]["grant_type"] == 1
    assert matrix["output_0"]["year"] == 1
    assert matrix["output_0"]["inc_activity"] == 0

    assert matrix["output_1"]["inc_activity"] == 1
    assert matrix["output_1"]["year"] == 1
    assert matrix["output_1"]["grant_type"] == 1

    assert matrix["output_2"]["inc_activity"] == 1
    assert matrix["output_2"]["year"] == 1
    assert matrix["output_2"]["grant_type"] == 0

    results_file = Path(output_dir) / "results.json"
    assert results_file.exists()
    with open(results_file, encoding="utf-8") as f:
        results_data = json.load(f)

    assert SUMMARY_JSON_KEY in results_data["results"]
    summary_result = results_data["results"][SUMMARY_JSON_KEY]
    assert summary_result["uid"] == SUMMARY_JSON_KEY
    assert summary_result["type"] == "custom"
    assert summary_result["status"] == "review"
    assert SUMMARY_WARNING_COMMENT in summary_result["comments"]

    assert SUMMARY_CSV_KEY in results_data["results"]
    csv_summary_result = results_data["results"][SUMMARY_CSV_KEY]
    assert csv_summary_result["uid"] == SUMMARY_CSV_KEY
    assert csv_summary_result["type"] == "custom"
    assert csv_summary_result["status"] == "review"
    assert SUMMARY_WARNING_COMMENT in csv_summary_result["comments"]


def test_records_finalise_excel_generates_summary(tmp_path):
    """Test that finalise with Excel format generates a valid session summary."""
    records = Records()
    record = make_record(
        uid="output_0",
        status="pass",
        output_type="table",
        fair={"dependent": "y", "independent": ["x"]},
    )
    records.results[record.uid] = record

    output_path = str(tmp_path / "excel_results")
    records.finalise(output_path, ext="xlsx")

    summary = load_session_summary(output_path)
    assert summary["metadata"]["total_outputs"] == 1
    assert summary["metadata"]["type_counts"] == {"table": 1}
    assert "output_0" in summary["variable_matrix"]
    assert summary["variable_matrix"]["output_0"] == {"x": 1, "y": 1}


def test_finalise_continues_on_summary_failure(tmp_path, caplog):
    """Test that Records.finalise continues normally even if summary generation fails."""
    records = Records()
    record = make_record(uid="output_0", status="pass", output_type="table")
    records.results[record.uid] = record

    output_path = str(tmp_path / "fail_summary_results")

    with patch(
        "acro.record.generate_session_summary", side_effect=RuntimeError("Summary boom")
    ):
        records.finalise(output_path, ext="json")

    assert (Path(output_path) / "results.json").exists()
    assert "Failed to generate session summary: Summary boom" in caplog.text


def test_federated_mode_skips_summary(tmp_path):
    """Test that federated mode produces evidence.json and skips session summary."""
    acro_fed = ACRO(federated=True)
    sample_df = pd.DataFrame(
        {
            "year": [2010, 2011, 2012, 2010],
            "grant_type": ["G", "G", "R", "R"],
        }
    )
    _ = acro_fed.crosstab(sample_df["year"], sample_df["grant_type"])

    output_path = str(tmp_path / "fed_results")
    acro_fed.finalise(output_path)

    evidence_file = Path(output_path) / "evidence.json"
    summary_file = Path(output_path) / SUMMARY_FILENAME

    assert evidence_file.exists()
    assert not summary_file.exists()


def test_copy_output_file_missing_returns_none(tmp_path, caplog):
    """_copy_output_file_if_needed returns None when the source file does not exist."""
    result = _copy_output_file_if_needed(
        str(tmp_path / "nonexistent.csv"), str(tmp_path)
    )

    assert result is None
    assert "nonexistent.csv" in caplog.text


def test_copy_output_file_already_in_dest_does_not_copy(tmp_path):
    """_copy_output_file_if_needed returns the filename and skips copy when src == dest."""
    existing = tmp_path / "plot.png"
    existing.write_bytes(b"data")

    result = _copy_output_file_if_needed(str(existing), str(tmp_path))

    assert result == "plot.png"


def test_finalise_removes_artifacts_dir(tmp_path):
    """Records.finalise() deletes the ARTIFACTS_DIR directory when it exists."""
    records = Records()
    record = make_record(uid="output_0", status="pass", output_type="table")
    records.results[record.uid] = record

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    output_path = str(tmp_path / "results")
    records.finalise(output_path, ext="json")

    assert not os.path.exists(ARTIFACTS_DIR)


def test_write_summary_csv_creates_file(tmp_path):
    """Write_summary_csv creates a CSV file at the given path."""
    summary = {
        "outputs": [
            {
                "uid": "output_0",
                "output_type": "table",
                "analysis_name": "crosstab",
                "dependent_variables": "unknown",
                "independent_variables": ["year", "grant_type"],
            }
        ],
        "variable_matrix": {
            "output_0": {"grant_type": 1, "year": 1},
        },
    }
    csv_path = str(tmp_path / SUMMARY_CSV_FILENAME)
    write_summary_csv(summary, csv_path)

    assert Path(csv_path).exists()


def test_write_summary_csv_header_and_row(tmp_path):
    """Write_summary_csv produces the correct header and one row per output."""
    summary = {
        "outputs": [
            {
                "uid": "output_0",
                "output_type": "table",
                "analysis_name": "crosstab",
                "dependent_variables": "unknown",
                "independent_variables": ["grant_type", "year"],
            },
            {
                "uid": "output_1",
                "output_type": "regression",
                "analysis_name": "ols",
                "dependent_variables": "inc_activity",
                "independent_variables": ["year"],
            },
        ],
        "variable_matrix": {
            "output_0": {"grant_type": 1, "inc_activity": 0, "year": 1},
            "output_1": {"grant_type": 0, "inc_activity": 1, "year": 1},
        },
    }
    csv_path = str(tmp_path / SUMMARY_CSV_FILENAME)
    write_summary_csv(summary, csv_path)

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv_mod.DictReader(f))

    assert len(rows) == 2
    assert {
        "uid",
        "output_type",
        "analysis_name",
        "dependent_variables",
        "independent_variables",
        "grant_type",
        "inc_activity",
        "year",
    }.issubset(rows[0].keys())

    assert rows[0]["uid"] == "output_0"
    assert rows[0]["analysis_name"] == "crosstab"
    assert rows[0]["grant_type"] == "1"
    assert rows[0]["inc_activity"] == "0"
    assert "grant_type" in rows[0]["independent_variables"]
    assert "year" in rows[0]["independent_variables"]

    assert rows[1]["uid"] == "output_1"
    assert rows[1]["dependent_variables"] == "inc_activity"
    assert rows[1]["inc_activity"] == "1"
    assert rows[1]["grant_type"] == "0"


def test_write_summary_csv_empty_outputs(tmp_path):
    """Write_summary_csv handles a summary with no outputs gracefully."""
    summary: dict = {"outputs": [], "variable_matrix": {}}
    csv_path = str(tmp_path / SUMMARY_CSV_FILENAME)
    write_summary_csv(summary, csv_path)

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv_mod.DictReader(f))

    assert rows == []


def test_summary_csv_filename_constant():
    """SUMMARY_CSV_FILENAME has the expected value."""
    assert SUMMARY_CSV_FILENAME == "session_summary.csv"


def test_finalise_produces_csv(tmp_path):
    """After Records.finalise(), session_summary.csv exists alongside session_summary.json."""
    records = Records()
    r1 = make_record(
        uid="output_0",
        status="fail",
        output_type="table",
        fair={"dependent": "unknown", "independent": ["year", "grant_type"]},
        command="crosstab(year, grant_type)",
    )
    r2 = make_record(
        uid="output_1",
        status="pass",  # nosec B105 - SDC status, not a password
        output_type="regression",
        fair={"dependent": "inc_activity", "independent": ["year"]},
        command="ols(inc_activity, year)",
    )
    records.results[r1.uid] = r1
    records.results[r2.uid] = r2

    output_path = str(tmp_path / "csv_results")
    records.finalise(output_path, ext="json")

    csv_file = Path(output_path) / SUMMARY_CSV_FILENAME
    assert csv_file.exists(), "session_summary.csv was not created"

    with open(csv_file, newline="", encoding="utf-8") as f:
        rows = list(csv_mod.DictReader(f))

    assert len(rows) == 2
    row_by_uid = {r["uid"]: r for r in rows}
    assert set(row_by_uid.keys()) == {"output_0", "output_1"}
    assert row_by_uid["output_0"]["output_type"] == "table"
    assert row_by_uid["output_1"]["output_type"] == "regression"
    assert "year" in row_by_uid["output_0"]["independent_variables"]
    assert row_by_uid["output_1"]["dependent_variables"] == "inc_activity"


def test_generate_session_summary_csv_write_failure_continues(tmp_path, caplog):
    """If write_summary_csv raises, generate_session_summary still writes the JSON."""
    records = Records()
    record = make_record(uid="output_0", status="fail", output_type="table")
    records.results[record.uid] = record

    output_path = str(tmp_path / "csv_fail_results")

    with patch("acro.summary.write_summary_csv", side_effect=OSError("disk full")):
        generate_session_summary(records, output_path)

    assert (Path(output_path) / SUMMARY_FILENAME).exists()
    assert "Failed to write session summary CSV" in caplog.text


def test_generate_session_summary_meaningful_output_names(tmp_path):
    """Verify session summary custom outputs use meaningful names instead of generic output_x."""
    records = Records()
    records.add(status="pass", output_type="table")

    output_path = str(tmp_path)
    generate_session_summary(records, output_path)

    # Initial analysis record
    assert "output_0" in records.results

    # Summary outputs must have descriptive keys starting with 2ndary_risk_summary
    assert SUMMARY_JSON_KEY in records.results
    assert SUMMARY_CSV_KEY in records.results
    assert "output_1" not in records.results
    assert "output_2" not in records.results

    assert records.results[SUMMARY_JSON_KEY].uid == "2ndary_risk_summary_json-DONT_RELEASE"
    assert records.results[SUMMARY_CSV_KEY].uid == "2ndary_risk_summary_csv-DONT_RELEASE"