"""Resident class counts stay a disjoint source partition, never new workers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import make_national_resident_workforce as builder  # type: ignore[import-not-found]  # noqa: E402


def source_row() -> dict[str, str]:
    values = [10, 6, 4, 3, 1, 0, 1, 0, 0, 1, 0, 4, 2, 2, 0, 1, 0, 0, 0, 0, 1]
    row = {"GEO_ID": "0500000US01001"}
    for index, value in enumerate(values, 1):
        row[f"B24080_E{index:03}"] = str(value)
        row[f"B24080_M{index:03}"] = "2"
    return row


def test_leaf_partition_does_not_add_nested_sex_or_private_totals() -> None:
    (row,) = builder.capture((source_row(),), {"01001": 10})
    assert row.class_total(4) == 5
    assert row.class_total(5) == 1
    assert row.class_total(10) == 1
    assert row.class_total(11) == 1
    assert sum(row.class_total(i) for i in range(4, 12)) == 10
    assert row.cells[0][0].value == 10


def test_resident_control_disagreement_is_not_repaired_or_renormalized() -> None:
    with pytest.raises(builder.ReferenceBuildError, match="resident_control"):
        builder.capture((source_row(),), {"01001": 11})


def test_nested_source_partition_disagreement_refuses() -> None:
    row = source_row()
    row["B24080_E003"] = "5"
    with pytest.raises(builder.ReferenceBuildError, match="class_partition"):
        builder.capture((row,), {"01001": 10})


def test_missing_estimate_and_moe_sentinel_remain_distinct_from_zero() -> None:
    row = source_row()
    row["B24080_E010"] = "-999999999"
    row["B24080_M010"] = "-555555555"
    (result,) = builder.capture((row,), {"01001": 10})
    estimate, moe = result.cells[9]
    assert estimate.value is None and estimate.raw == "-999999999"
    assert estimate.status == "insufficient_sample_cases"
    assert moe.value is None and moe.status == "controlled_estimate"
    assert result.class_total(10) is None


def test_duplicate_unknown_and_missing_counties_refuse() -> None:
    row = source_row()
    with pytest.raises(builder.ReferenceBuildError, match="duplicate"):
        builder.capture((row, row), {"01001": 10})
    with pytest.raises(builder.ReferenceBuildError, match="unexpected_county"):
        builder.capture((row,), {"01003": 10})
    with pytest.raises(builder.ReferenceBuildError, match="county_coverage"):
        builder.capture((), {"01001": 10})


def test_malformed_columns_and_wrong_sentinel_role_refuse() -> None:
    row = source_row()
    del row["B24080_M021"]
    with pytest.raises(builder.ReferenceBuildError, match="source_schema"):
        builder.capture((row,), {"01001": 10})
    row = source_row()
    row["B24080_E010"] = "-555555555"
    with pytest.raises(builder.ReferenceBuildError, match="sentinel_role"):
        builder.capture((row,), {"01001": 10})


def test_captured_counties_preserve_exact_source_controls_and_class_totals() -> None:
    import csv
    import gzip
    import json

    with gzip.open(builder.ARTIFACT_OUT, "rt", newline="") as stream:
        reader = csv.DictReader(stream)
        assert tuple(reader.fieldnames or ()) == builder.COLUMNS
        rows = list(reader)
    assert len(rows) == len({row["county_geoid"] for row in rows}) == 3144
    assert sum(int(row["B24080_E001_value"]) for row in rows) == 161297155
    for row in rows:
        assert all(
            row[f"{column}_value"] == row[f"{column}_raw"] for column in builder.SOURCE_COLUMNS[1:]
        )
        assert all(row[f"{column}_status"] == "published" for column in builder.SOURCE_COLUMNS[1:])
    metadata = json.loads(builder.METADATA_OUT.read_text())
    assert metadata["county_control"]["mismatches"] == 0
    assert metadata["coverage"]["classes"]["unpaid_family_worker"]["known_persons"] == 301690
    assert metadata["artifact"]["sha256"] == builder.sha256(builder.ARTIFACT_OUT)


def test_output_alias_refuses_before_reading_or_overwriting_source(tmp_path: Path) -> None:
    import json

    source = tmp_path / "table.dat"
    source.write_text("unique source bytes")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "contract": "NationalResidentWorkforce2024SourcesV1",
                "sources": [
                    {"id": "B24080", "path": "table.dat"},
                    {"id": "acs_table_shells", "path": "shells.txt"},
                ],
            }
        )
    )
    with pytest.raises(builder.ReferenceBuildError, match="output_overlap"):
        builder.build(
            tmp_path,
            manifest_path=manifest,
            artifact_out=source,
            metadata_out=tmp_path / "metadata.json",
        )
    assert source.read_text() == "unique source bytes"
