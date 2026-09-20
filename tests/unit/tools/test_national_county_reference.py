"""County reference boundaries: geography, source uncertainty and distinct units."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

import make_national_county_reference as builder  # type: ignore[import-not-found]  # noqa: E402


def county(geoid: str) -> builder.County:
    return builder.County(geoid, geoid[:2], geoid[2:], "Example", "1", "0", "+1.0", "-1.0")


def test_duplicate_and_missing_geographies_are_refused() -> None:
    rows = [county("09110"), county("09120")]
    assert len(builder.validate_counties(rows, {"09": 2})) == 2
    with pytest.raises(builder.ReferenceBuildError, match="duplicate_county"):
        builder.validate_counties([rows[0], rows[0]], {"09": 2})
    with pytest.raises(builder.ReferenceBuildError, match="county_coverage"):
        builder.validate_counties(rows[:1], {"09": 2})
    with pytest.raises(builder.ReferenceBuildError, match="county_coverage"):
        builder.validate_counties(rows + [county("72001")], {"09": 2})


def test_controlled_moe_is_not_missing_population_or_observed_zero() -> None:
    value = builder.parse_acs_cell("59109", margin=False)
    moe = builder.parse_acs_cell("-555555555", margin=True)
    assert value.value == 59109 and value.status == "published"
    assert moe.value is None
    assert moe.raw == "-555555555"
    assert moe.status == "controlled_estimate"
    assert builder.parse_acs_cell("0", margin=True).value == 0
    assert builder.parse_acs_cell("", margin=False).status == "missing"
    with pytest.raises(builder.ReferenceBuildError, match="acs_sentinel_role"):
        builder.parse_acs_cell("-555555555", margin=False)


@pytest.mark.parametrize("raw", ["NaN", "1.5", "-42", str(2**63), "+2", " 2"])
def test_acs_invalid_counts_fail_instead_of_coercing(raw: str) -> None:
    with pytest.raises(builder.ReferenceBuildError, match="acs_value"):
        builder.parse_acs_cell(raw, margin=False)


def test_acs_missing_and_duplicate_county_rows_fail(tmp_path: Path) -> None:
    path = tmp_path / "table.dat"
    path.write_text("GEO_ID|B01003_E001|B01003_M001\n0500000US09110|10|2\n")
    with pytest.raises(builder.ReferenceBuildError, match="acs_coverage"):
        builder.read_acs_table(path, "B01003", {"09110", "09120"})
    path.write_text(path.read_text() + "0500000US09110|20|3\n")
    with pytest.raises(builder.ReferenceBuildError, match="duplicate_acs_county"):
        builder.read_acs_table(path, "B01003", {"09110"})


def test_suppressed_jobs_keep_raw_evidence_without_becoming_persons() -> None:
    source = {
        "area_fips": "09110",
        "own_code": "0",
        "industry_code": "10",
        "agglvl_code": "70",
        "size_code": "0",
        "year": "2024",
        "qtr": "A",
        "disclosure_code": "N",
        "annual_avg_estabs": "7",
        "annual_avg_emplvl": "0",
        "total_annual_wages": "0",
        "annual_avg_wkly_wage": "0",
    }
    observed = builder.parse_qcew_row(source)
    assert observed.status == "suppressed"
    assert observed.establishments.value == 7
    assert observed.jobs.value is None and observed.jobs.raw == "0"
    assert observed.jobs.status == "suppressed"
    source["disclosure_code"] = ""
    assert builder.parse_qcew_row(source).jobs.value == 0
    source["disclosure_code"] = "?"
    with pytest.raises(builder.ReferenceBuildError, match="qcew_disclosure"):
        builder.parse_qcew_row(source)


def test_missing_resident_estimate_is_not_replaced_with_qcew_jobs() -> None:
    cells = {
        series.name: (
            builder.parse_acs_cell("", margin=False),
            builder.parse_acs_cell("", margin=True),
        )
        for series in builder.ACS_SERIES
    }
    observed = builder.Cell(999, "999", "published")
    jobs = builder.QcewRow("published", "", observed, observed, observed, observed)
    row = builder.assemble_row(county("09110"), cells, jobs)
    mapped = dict(zip(builder.COLUMNS, row, strict=True))
    assert mapped["acs_population_persons_estimate"] == ""
    assert mapped["acs_population_persons_estimate_status"] == "missing"
    assert mapped["qcew_status"] == "published"
    assert mapped["qcew_jobs"] == "999"
    assert builder.METADATA["acs_series"][0]["unit"] == "persons"
    assert builder.METADATA["qcew_measures"]["qcew_jobs"]["unit"] == "jobs"


def test_committed_artifact_has_current_counties_and_pinned_observations() -> None:
    metadata = json.loads(builder.METADATA_OUT.read_text())
    blob = builder.ARTIFACT_OUT.read_bytes()
    assert hashlib.sha256(blob).hexdigest() == metadata["artifact"]["sha256"]
    with gzip.open(builder.ARTIFACT_OUT, "rt", newline="") as stream:
        rows = list(csv.DictReader(stream))
    ids = [row["county_geoid"] for row in rows]
    assert len(ids) == len(set(ids)) == 3144
    assert ids == sorted(ids)
    assert sum(key.startswith("09") for key in ids) == 9
    assert sum(key.startswith("02") for key in ids) == 30
    assert sum(key.startswith("15") for key in ids) == 5
    assert not {"09001", "02261", "02270", "46113", "51515", "72001"}.intersection(ids)
    by_id = {row["county_geoid"]: row for row in rows}
    assert by_id["15005"]["acs_population_persons_estimate"] == "67"
    assert by_id["15005"]["acs_households_estimate"] == "40"
    assert by_id["15005"]["acs_civilian_employed_persons_estimate"] == "49"
    assert by_id["15005"]["qcew_status"] == "not_published"
    assert by_id["15005"]["qcew_jobs"] == ""
    assert by_id["26163"]["qcew_jobs"] == "725504"
    assert metadata["coverage"]["controlled_population_moes"] == 3014
    assert metadata["coverage"]["qcew_missing_counties"] == ["15005"]
    assert metadata["semantics"]["acs_annotation_fields"] == "unavailable_in_bulk_source"


def test_registry_source_lineage_and_person_partitions() -> None:
    import yaml

    metadata = json.loads(builder.METADATA_OUT.read_text())
    assert (
        metadata["source_manifest"]["sha256"]
        == hashlib.sha256(builder.SOURCE_MANIFEST.read_bytes()).hexdigest()
    )
    registry = yaml.safe_load((ROOT / "data-artifacts.yaml").read_text())
    entries = [
        entry
        for entry in registry["artifacts"]
        if entry["name"] == "national_county_reference_2024"
    ]
    assert len(entries) == 1
    assert entries[0]["sha256"] == metadata["artifact"]["sha256"]
    assert entries[0]["rows"] == 3144
    assert metadata["acs_source_definitions"]["B11001_001"]["universe"] == "Households"
    with gzip.open(builder.ARTIFACT_OUT, "rt", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert sum(int(row["acs_population_persons_estimate"]) for row in rows) == 334922499
    for row in rows:
        assert int(row["acs_labor_force_persons_estimate"]) == int(
            row["acs_civilian_labor_force_persons_estimate"]
        ) + int(row["acs_armed_forces_persons_estimate"])
        assert int(row["acs_civilian_labor_force_persons_estimate"]) == int(
            row["acs_civilian_employed_persons_estimate"]
        ) + int(row["acs_civilian_unemployed_persons_estimate"])
        assert int(row["acs_age_16_plus_persons_estimate"]) == int(
            row["acs_labor_force_persons_estimate"]
        ) + int(row["acs_not_in_labor_force_persons_estimate"])


def test_source_hash_drift_refused_before_any_parsing(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    source.write_text("original")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "contract": "NationalCountyReference2024SourcesV1",
                "sources": [
                    {
                        "id": "qcew",
                        "path": "source.csv",
                        "bytes": 8,
                        "sha256": hashlib.sha256(b"original").hexdigest(),
                    }
                ],
            }
        )
    )
    source.write_text("tampered")
    with pytest.raises(builder.ReferenceBuildError, match="source_digest"):
        builder.verify_sources(tmp_path, manifest)


def test_qcew_duplicate_county_refused(tmp_path: Path) -> None:
    path = tmp_path / "qcew.csv"
    columns = [
        "area_fips",
        "own_code",
        "industry_code",
        "agglvl_code",
        "size_code",
        "year",
        "qtr",
        "disclosure_code",
        "annual_avg_estabs",
        "annual_avg_emplvl",
        "total_annual_wages",
        "annual_avg_wkly_wage",
    ]
    row = ["09110", "0", "10", "70", "0", "2024", "A", "", "7", "99", "1000", "10"]
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows([row, row])
    with pytest.raises(builder.ReferenceBuildError, match="duplicate_qcew_county"):
        builder.read_qcew(path, {"09110"})
