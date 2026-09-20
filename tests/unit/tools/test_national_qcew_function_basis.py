"""National source cut must preserve sparse evidence before Designed assignment."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import make_national_qcew_function_basis as builder  # type: ignore[import-not-found]  # noqa: E402


def source(
    *,
    county: str = "01017",
    ownership: str = "5",
    naics: str = "99",
    establishments: str = "0",
    jobs: str = "1",
    payroll: str = "24812",
    disclosure: str = "",
) -> dict[str, str]:
    return {
        "area_fips": county,
        "own_code": ownership,
        "industry_code": naics,
        "agglvl_code": str(builder.aggregation_level(naics)),
        "size_code": "0",
        "year": "2024",
        "qtr": "A",
        "disclosure_code": disclosure,
        "annual_avg_estabs": establishments,
        "annual_avg_emplvl": jobs,
        "total_annual_wages": payroll,
        "annual_avg_wkly_wage": "0",
    }


def test_rounded_zero_establishments_remain_a_source_row() -> None:
    row = builder.parse_observation(source())
    assert row.annual_avg_establishments == 0
    assert row.annual_avg_jobs == 1
    assert row.annual_payroll_usd == 24812


def test_zero_annual_jobs_can_have_positive_annual_payroll() -> None:
    row = builder.parse_observation(source(jobs="0", payroll="100"))
    assert row.annual_avg_jobs == 0 and row.annual_payroll_usd == 100


def test_suppression_keeps_establishments_and_nulls_only_withheld_measures() -> None:
    row = builder.parse_observation(
        source(establishments="7", jobs="0", payroll="0", disclosure="N")
    )
    assert row.annual_avg_establishments == 7
    assert row.annual_avg_jobs is None and row.annual_payroll_usd is None
    with pytest.raises(builder.ReferenceBuildError, match="suppressed_nonzero"):
        builder.parse_observation(source(disclosure="N"))


def test_mapping_is_a_disjoint_designed_assignment_with_unclassified_residual() -> None:
    mapping = builder.load_mapping()
    assert mapping.document["evidence_class"] == "Designed"
    assert mapping.function_for("333") == "capital_goods"
    assert mapping.function_for("61") == "household_services"
    assert mapping.function_for("92") == "public_provisioning"
    assert mapping.function_for("99") is None
    assert set(mapping.code_to_function) == set(mapping.source_codes) - {"99"}
    altered = copy.deepcopy(mapping.document)
    altered["functions"][0]["naics_codes"].append("11")
    with pytest.raises(builder.ReferenceBuildError, match="overlapping_naics"):
        builder.validate_mapping(altered)
    altered = copy.deepcopy(mapping.document)
    altered["functions"][0]["naics_codes"].append("333")
    with pytest.raises(builder.ReferenceBuildError, match="duplicate_naics"):
        builder.validate_mapping(altered)


def test_capture_is_sparse_and_preserves_each_ownership() -> None:
    mapping = builder.load_mapping()
    rows = [source(ownership=ownership, naics="61") for ownership in ("1", "2", "3", "5")]
    capture = builder.capture(rows, {"01017", "15005"}, mapping)
    assert len(capture.observations) == 4
    assert {row.ownership_code for row in capture.observations} == {"1", "2", "3", "5"}
    assert all(row.county_geoid == "01017" for row in capture.observations)
    assert capture.diagnostics["counties_without_selected_rows"] == ["15005"]
    with pytest.raises(builder.ReferenceBuildError, match="duplicate_source_cell"):
        builder.capture(rows + rows[:1], {"01017", "15005"}, mapping)


def test_source_aggregation_and_period_are_checked() -> None:
    row = source(naics="333")
    row["agglvl_code"] = "74"
    with pytest.raises(builder.ReferenceBuildError, match="aggregation_identity"):
        builder.parse_observation(row)
    row = source()
    row["year"] = "2023"
    with pytest.raises(builder.ReferenceBuildError, match="period_identity"):
        builder.parse_observation(row)


def test_committed_cut_covers_reviewed_source_cells_without_parent_duplication() -> None:
    rows = pq.read_table(builder.ARTIFACT_OUT).to_pylist()
    assert len(rows) == 144881
    assert sum(row["disclosure_code"] == "N" for row in rows) == 57984
    assert sum(row["annual_avg_establishments"] == 0 for row in rows) == 1393
    assert all(row["annual_avg_jobs"] is None for row in rows if row["disclosure_code"] == "N")
    keys = [(row["county_geoid"], row["ownership_code"], row["naics_code"]) for row in rows]
    assert keys == sorted(set(keys))
    assert {row["ownership_code"] for row in rows} == {"1", "2", "3", "5"}
    assert not {"11", "31-33", "53"}.intersection(row["naics_code"] for row in rows)
    assert not any(row["county_geoid"] == "15005" for row in rows)
    example = next(
        row
        for row in rows
        if row["county_geoid"] == "01017"
        and row["ownership_code"] == "5"
        and row["naics_code"] == "99"
    )
    assert (
        example["annual_avg_establishments"],
        example["annual_avg_jobs"],
        example["annual_payroll_usd"],
    ) == (0, 1, 24812)
    metadata = json.loads(builder.METADATA_OUT.read_text())
    assert (
        metadata["semantics"]["jobs"]
        == "covered workplace jobs; not distinct persons or resident workers"
    )
    assert metadata["coverage"]["parent_sector_rows"] == 98987
    assert metadata["coverage"]["national_jobs"]["domestic_unallocated_jobs"] == 5497365
    assert metadata["coverage"]["national_jobs"]["county_jobs"] == 149493074
    assert metadata["coverage"]["national_jobs"]["us_jobs"] == 154990441


def test_artifact_registry_mapping_and_source_hashes_agree() -> None:
    import yaml

    metadata = json.loads(builder.METADATA_OUT.read_text())
    assert (
        metadata["artifact"]["sha256"]
        == hashlib.sha256(builder.ARTIFACT_OUT.read_bytes()).hexdigest()
    )
    assert (
        metadata["function_mapping"]["sha256"]
        == hashlib.sha256(builder.MAPPING_PATH.read_bytes()).hexdigest()
    )
    assert (
        metadata["source_manifest"]["sha256"]
        == hashlib.sha256(builder.SOURCE_MANIFEST.read_bytes()).hexdigest()
    )
    assert metadata["source_manifest"]["selected_source_ids"] == ["tiger", "qcew"]
    registry = yaml.safe_load((ROOT / "data-artifacts.yaml").read_text())
    entries = [
        entry
        for entry in registry["artifacts"]
        if entry["name"] == "national_qcew_function_basis_2024"
    ]
    assert len(entries) == 1 and entries[0]["sha256"] == metadata["artifact"]["sha256"]
    assert metadata["artifact"]["bytes"] < 1024 * 1024
    assert pq.read_schema(builder.ARTIFACT_OUT) == builder.SCHEMA
