"""Independent contract tests for PER-319 QCEW county economics."""

from __future__ import annotations

import copy
import csv
import gzip
import hashlib
import io
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import make_qcew_county_economics_artifacts as builder  # type: ignore[import-not-found]  # noqa: E402
from verify_qcew_county_economics_v1 import (  # type: ignore[import-not-found]  # noqa: E402
    QcewCountyEconomicsRefusal,
    load_contract,
    verify_artifact_manifest,
    verify_artifacts,
    verify_contract,
    verify_source_manifest,
)

CONTRACT = ROOT / "contracts" / "qcew_county_economics_v1.yaml"
MANIFEST = ROOT / "data-artifacts.yaml"
SOURCE_MANIFEST = ROOT / "tools" / "qcew_county_economics_v1_source_manifest.json"
ARTIFACT = (
    ROOT
    / "src"
    / "babylon"
    / "data"
    / "reference"
    / "economy"
    / "qcew_county_economics_mi_2024.csv.gz"
)

WAYNE_ROW = ["26163", "36727", "725504", "55436615328", "1469"]


def _gzip_csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with (
        path.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as binary,
        io.TextIOWrapper(binary, encoding="utf-8", newline="") as text,
    ):
        writer = csv.writer(text, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _read_artifact_rows(path: Path = ARTIFACT) -> tuple[list[str], list[list[str]]]:
    with gzip.GzipFile(fileobj=io.BytesIO(path.read_bytes()), mode="rb") as compressed:
        text = io.TextIOWrapper(compressed, encoding="utf-8", newline="")
        reader = csv.reader(text)
        return list(next(reader)), list(reader)


def _fixture_county_rows(
    geoid: str = "26001",
    *,
    disclosure_code: str = "",
    annual_avg_emplvl: str = "1494",
) -> list[dict[str, str]]:
    row = dict.fromkeys(builder.EXPECTED_SOURCE_COLUMNS, "0")
    row.update(
        {
            "area_fips": geoid,
            "own_code": "0",
            "industry_code": "10",
            "agglvl_code": "70",
            "size_code": "0",
            "year": "2024",
            "qtr": "A",
            "disclosure_code": disclosure_code,
            "area_title": "Alcona County, Michigan",
            "own_title": "Total Covered",
            "industry_title": "10 Total, all industries",
            "agglvl_title": "County, Total Covered",
            "size_title": "All establishment sizes",
            "annual_avg_estabs_count": "214",
            "annual_avg_emplvl": annual_avg_emplvl,
            "total_annual_wages": "62042985",
            "annual_avg_wkly_wage": "798",
        }
    )
    return [row]


def test_source_manifest_declares_exactly_the_83_michigan_county_files() -> None:
    entries = builder.load_source_manifest(SOURCE_MANIFEST)

    assert len(entries) == 83
    geoids = []
    for entry in entries:
        match = builder.COUNTY_FILE_RE.fullmatch(entry["file"])
        assert match is not None, entry["file"]
        geoids.append(match.group(1))
        assert len(entry["sha256"]) == 64
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
    assert geoids == sorted(builder.MICHIGAN_COUNTY_GEOIDS)
    assert geoids == sorted(geoids)


def test_checked_in_contract_artifact_and_manifest_verify() -> None:
    contract = load_contract(CONTRACT)

    assert contract["meta"] == {
        "contract": "QcewCountyEconomicsV1",
        "version": 1,
        "issue": "PER-319",
        "parent": "PER-10",
    }
    verify_contract(contract)
    verify_source_manifest(contract, SOURCE_MANIFEST)
    rows = verify_artifacts(contract, ROOT)
    verify_artifact_manifest(contract, MANIFEST)
    assert len(rows) == contract["artifact"]["rows"] == 83


def test_builder_output_is_byte_identical_across_runs(tmp_path: Path) -> None:
    first = tmp_path / "first.csv.gz"
    second = tmp_path / "second.csv.gz"

    first_stats = builder.build(out_path=first)
    second_stats = builder.build(out_path=second)

    assert first.read_bytes() == second.read_bytes()
    assert first_stats == second_stats
    assert first_stats.rows == 83


def test_committed_artifact_schema_and_ordering() -> None:
    header, rows = _read_artifact_rows()

    assert header == list(builder.COLUMNS)
    assert len(rows) == 83
    geoids = [row[0] for row in rows]
    assert geoids == sorted(geoids)
    assert len(set(geoids)) == 83
    assert geoids == list(builder.MICHIGAN_COUNTY_GEOIDS)
    for row in rows:
        assert len(row) == 5
        assert re.fullmatch(r"26[0-1][0-9]{2}", row[0])
        assert all(re.fullmatch(r"[0-9]+", value) for value in row[1:])


def test_wayne_county_known_values_match_bls_public_record() -> None:
    _, rows = _read_artifact_rows()

    assert WAYNE_ROW in rows


def test_gzip_writer_is_byte_identical_across_output_paths(tmp_path: Path) -> None:
    rows = [WAYNE_ROW]
    first = tmp_path / "first.csv.gz"
    second = tmp_path / "second.csv.gz"

    first_stats = builder._write_gzip_csv(first, builder.COLUMNS, rows)
    second_stats = builder._write_gzip_csv(second, builder.COLUMNS, rows)

    assert first.read_bytes() == second.read_bytes()
    assert first_stats == second_stats


def test_canonicalizer_refuses_source_schema_drift() -> None:
    rows = _fixture_county_rows()
    fieldnames = [column for column in builder.EXPECTED_SOURCE_COLUMNS if column != "qtr"]

    with pytest.raises(builder.QcewBuildError, match="source_schema"):
        builder.canonicalize_county_row("26001", fieldnames, rows)


def test_canonicalizer_refuses_missing_or_duplicate_county_total() -> None:
    with pytest.raises(builder.QcewBuildError, match="source_selection"):
        builder.canonicalize_county_row("26001", builder.EXPECTED_SOURCE_COLUMNS, [])
    with pytest.raises(builder.QcewBuildError, match="source_selection"):
        builder.canonicalize_county_row(
            "26001",
            builder.EXPECTED_SOURCE_COLUMNS,
            _fixture_county_rows() * 2,
        )


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("area_fips", "26003", "source_geoid"),
        ("disclosure_code", "N", "source_disclosure"),
        ("size_code", "1", "source_row_identity"),
        ("qtr", "1", "source_row_identity"),
        ("year", "2023", "source_row_identity"),
        ("industry_code", "1024", "source_row_identity"),
        ("annual_avg_emplvl", "1,494", "source_value"),
        ("annual_avg_emplvl", "", "source_value"),
        ("annual_avg_wkly_wage", "nan", "source_value"),
    ],
)
def test_canonicalizer_refuses_noncanonical_source_values(
    field: str, value: str, code: str
) -> None:
    rows = _fixture_county_rows()
    rows[0][field] = value

    with pytest.raises(builder.QcewBuildError, match=code):
        builder.canonicalize_county_row("26001", builder.EXPECTED_SOURCE_COLUMNS, rows)


def test_builder_refuses_source_manifest_digest_mismatch(tmp_path: Path) -> None:
    staged = tmp_path / "staged.csv"
    staged.write_bytes(b"tampered")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "contract": "QcewCountyEconomicsV1",
                "version": 1,
                "entries": [
                    {
                        "file": "2024.annual 26001 Alcona County, Michigan.csv",
                        "sha256": "0" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(builder.QcewBuildError, match="source_sha256"):
        builder.build(
            source_dir=tmp_path,
            out_path=tmp_path / "out.csv.gz",
            source_manifest=manifest,
        )


def test_contract_refuses_missing_substantive_value_classification() -> None:
    contract = copy.deepcopy(load_contract(CONTRACT))
    del contract["classifications"]["semantic_digests"]

    with pytest.raises(QcewCountyEconomicsRefusal, match="contract_shape"):
        verify_contract(contract)


def test_contract_loader_refuses_duplicate_keys(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.yaml"
    duplicate.write_text("meta: first\nmeta: second\n", encoding="utf-8")

    with pytest.raises(QcewCountyEconomicsRefusal, match="invalid_contract"):
        load_contract(duplicate)


def test_artifact_verifier_refuses_unsorted_rows(tmp_path: Path) -> None:
    contract = copy.deepcopy(load_contract(CONTRACT))
    artifact_path = tmp_path / str(contract["artifact"]["path"])
    rows = [
        ["26163", "36727", "725504", "55436615328", "1469"],
        ["26001", "214", "1494", "62042985", "798"],
    ]
    _gzip_csv(artifact_path, list(contract["artifact"]["columns"]), rows)
    contract["artifact"]["path"] = str(artifact_path.relative_to(tmp_path))
    contract["artifact"]["rows"] = 2
    contract["artifact"]["sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()

    with pytest.raises(QcewCountyEconomicsRefusal, match="artifact_order"):
        verify_artifacts(contract, tmp_path)


def test_artifact_manifest_tripwire_is_not_managed_by_sqlite_generator() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    by_name = {row["name"]: row for row in manifest["artifacts"]}
    managed = {spec.name for spec in builder.make_data_artifacts_specs()}

    assert builder.ARTIFACT_NAME in by_name
    assert builder.ARTIFACT_NAME not in managed


def test_contract_json_is_finite_and_canonicalizable() -> None:
    contract = load_contract(CONTRACT)

    encoded = json.dumps(contract, sort_keys=True, allow_nan=False).encode("utf-8")
    assert encoded
