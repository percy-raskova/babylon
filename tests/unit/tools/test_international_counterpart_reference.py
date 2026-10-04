"""Disjoint source capture must not create trade or convert missingness to zero."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import make_international_counterpart_reference as builder  # type: ignore[import-not-found]  # noqa: E402


def test_exact_amounts_and_missing_directions_are_distinct() -> None:
    assert builder.amount("438741.99807800003") == Decimal("438741.99807800003")
    assert builder.amount("") is None
    assert builder.amount("0") == Decimal(0)
    assert builder.amount("6.3e-05") == Decimal("0.000063")
    for invalid in ("NaN", "Infinity", "-1", "1e99", " 2", "9" * 41):
        with pytest.raises(builder.ReferenceBuildError, match="trade_amount"):
            builder.amount(invalid)


def test_membership_is_disjoint_and_preserves_approved_edges() -> None:
    rows = builder.load_membership()
    members = {row.identity_id: row for row in rows}
    assert len(rows) == len(members) == 252
    for code in ("304", "060", "666", "412"):
        assert members[f"m49:{code}"].counterpart_id == "remaining_europe"
    assert members["m49:364"].counterpart_id == "west_asia_north_africa"
    assert members["m49:196"].counterpart_id == "european_union"
    assert sum(row.counterpart_id == "european_union" for row in rows) == 27
    for code in ("158", "344", "446"):
        assert members[f"m49:{code}"].counterpart_id == "remaining_asia_pacific"
    assert members["m49:156"].counterpart_id == "china"
    assert members["m49:010"].disposition == "nonmarket"
    assert members["m49:840"].disposition == "domestic"
    assert {row.identity_id for row in rows if row.disposition == "us_dependency"} == {
        "m49:016",
        "m49:316",
        "m49:580",
        "m49:581",
        "m49:630",
        "m49:850",
    }
    for code in ("583", "584", "585"):
        assert members[f"m49:{code}"].us_relationship == "freely_associated_state"
        assert members[f"m49:{code}"].disposition == "counterpart"
    with pytest.raises(builder.ReferenceBuildError, match="duplicate_membership"):
        builder.validate_membership((*rows, rows[0]))


def test_committed_capture_preserves_missingness_and_disjoint_trade() -> None:
    with gzip.open(builder.ARTIFACT_OUT, "rt", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 252
    assert [row["identity_id"] for row in rows] == sorted({row["identity_id"] for row in rows})
    observed = [row for row in rows if row["trade_row_status"] == "published"]
    assert len(observed) == 233
    assert len({row["census_code"] for row in observed}) == 233
    assert all(row["disposition"] == "counterpart" for row in observed)
    assert not any(row["census_code"].startswith("00") for row in rows)
    for row in rows:
        if row["disposition"] in {"domestic", "us_dependency", "nonmarket"}:
            assert row["us_imports_annual_raw"] == row["us_exports_annual_raw"] == ""
            assert row["us_imports_status"] == row["us_exports_status"] == "not_published"
    palestine = next(row for row in rows if row["identity_id"] == "m49:275")
    assert palestine["trade_row_status"] == "not_published"
    assert palestine["population_identity_id"] == "m49:275"
    assert palestine["population_aggregation"] == "independent_area"
    children = [row for row in observed if row["m49_code"] == "275"]
    assert {row["census_code"] for row in children} == {"5082", "5083"}
    assert all(
        row["population_identity_id"] == "m49:275"
        and row["population_aggregation"] == "trade_only_exclude_from_population"
        for row in children
    )
    assert all(
        row["census_reporter_code"] in {"GZ", "WE"} and not row["iso_alpha2"] for row in children
    )
    metadata = json.loads(builder.METADATA_OUT.read_text())
    assert len(metadata["controls"]) == 15
    assert metadata["runtime_consumers"] == []
    for direction in ("us_imports", "us_exports"):
        raw_sum = sum((Decimal(row[f"{direction}_annual_raw"]) for row in observed), Decimal(0))
        assert Decimal(metadata["reconciliation"][direction]["leaf_annual_sum"]) == raw_sum
        assert (
            sum(
                (
                    Decimal(row[direction]["published_sum"])
                    for row in metadata["counterpart_totals"]
                ),
                Decimal(0),
            )
            == raw_sum
        )
    assert (
        metadata["artifact"]["sha256"]
        == hashlib.sha256(builder.ARTIFACT_OUT.read_bytes()).hexdigest()
    )
    assert (
        metadata["membership"]["sha256"]
        == hashlib.sha256(builder.MAPPING_PATH.read_bytes()).hexdigest()
    )


def test_one_missing_direction_does_not_erase_the_other_or_claim_complete_total() -> None:
    rows = (builder.TradeRow("5700", "China", ("1",) * 12, "", ("2",) * 12, "24"),)
    totals = builder.summarize(rows)
    assert totals["us_imports"] == {
        "published_sum": "0",
        "published_rows": 0,
        "missing_rows": 1,
        "complete_sum": None,
    }
    assert totals["us_exports"]["complete_sum"] == "24"


def test_duplicate_or_unmapped_trade_cannot_enter_capture() -> None:
    row = builder.TradeRow("5700", "China", ("1",) * 12, "12", ("2",) * 12, "24")
    with pytest.raises(builder.ReferenceBuildError, match="duplicate_trade"):
        builder.validate_trade((row, row))
    with pytest.raises(builder.ReferenceBuildError, match="unmapped_trade"):
        builder.check_trade_coverage((row,), {})


def test_corrupt_source_refused_before_extraction(tmp_path: Path) -> None:
    raw = tmp_path / "source.html"
    raw.write_bytes(b"corrupt")
    manifest = tmp_path / "pins.json"
    manifest.write_text(
        json.dumps(
            {
                "contract": "InternationalCounterpartSourcesV1",
                "sources": [{"id": "example", "path": raw.name, "bytes": 7, "sha256": "0" * 64}],
            }
        )
    )
    with pytest.raises(builder.ReferenceBuildError, match="source_digest"):
        builder.verify_sources(tmp_path, manifest)


def write_workbook(path: Path, *, formula: bool = False) -> None:
    import xml.etree.ElementTree as et
    import zipfile

    namespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    strings = (*builder.HEADER, "5700", "China")
    shared = et.Element("sst", xmlns=namespace)
    for text in strings:
        et.SubElement(et.SubElement(shared, "si"), "t").text = text
    sheet = et.Element("worksheet", xmlns=namespace)
    data = et.SubElement(sheet, "sheetData")
    columns = (*"ABCDEFGHIJKLMNOPQRSTUVWXYZ", "AA", "AB", "AC")
    header = et.SubElement(data, "row", r="1")
    for index, column in enumerate(columns):
        cell = et.SubElement(header, "c", r=f"{column}1", t="s")
        et.SubElement(cell, "v").text = str(index)
    for index, year in enumerate(("2024", "2025"), start=2):
        row = et.SubElement(data, "row", r=str(index))
        values = (
            year,
            "29",
            "30",
            "6.3e-05",
            *("0" for _ in range(11)),
            "",
            *("2" for _ in range(12)),
            "24.00000000003",
        )
        for column, value in zip(columns, values, strict=True):
            cell = et.SubElement(
                row, "c", r=f"{column}{index}", t="s" if column in {"B", "C"} else "n"
            )
            if value:
                et.SubElement(cell, "v").text = value
            if formula and column == "P":
                et.SubElement(cell, "f").text = "SUM(D2:O2)"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/sharedStrings.xml", et.tostring(shared))
        archive.writestr("xl/worksheets/sheet1.xml", et.tostring(sheet))
        archive.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{namespace}"><sheets><sheet name="country"/></sheets></workbook>',
        )


def test_workbook_extraction_retains_raw_tokens_and_selects_2024(tmp_path: Path) -> None:
    path = tmp_path / "country.xlsx"
    write_workbook(path)
    (row,) = builder.read_trade(path)
    assert row.census_code == "5700" and row.source_name == "China"
    assert row.us_imports_months == ("6.3e-05", *("0" for _ in range(11)))
    assert row.us_imports_annual == ""
    assert row.us_exports_annual == "24.00000000003"
    fields = builder.trade_fields(row)
    assert fields["us_imports_status"] == "missing_cell"
    assert fields["us_imports_monthly_sum"] == "0.000063"
    assert fields["us_imports_annual_minus_monthly"] == ""
    assert fields["us_exports_annual_minus_monthly"] == "0.00000000003"


def test_formulas_are_not_silently_treated_as_observations(tmp_path: Path) -> None:
    path = tmp_path / "country.xlsx"
    write_workbook(path, formula=True)
    with pytest.raises(builder.ReferenceBuildError, match="formula"):
        builder.read_trade(path)


def test_source_and_membership_outputs_cannot_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.xlsx"
    source.write_bytes(b"irreplaceable source")
    monkeypatch.setattr(builder, "verify_sources", lambda *_args: {"census_trade": source})
    with pytest.raises(builder.ReferenceBuildError, match="output_overlap"):
        builder.build(
            source_root=tmp_path, artifact_out=source, metadata_out=tmp_path / "metadata.json"
        )
    assert source.read_bytes() == b"irreplaceable source"
    alias = tmp_path / "alias.csv"
    alias.hardlink_to(source)
    with pytest.raises(builder.ReferenceBuildError, match="output_overlap"):
        builder.build(
            source_root=tmp_path, artifact_out=alias, metadata_out=tmp_path / "metadata.json"
        )


def test_us_dependency_cannot_be_assigned_to_external_counterpart() -> None:
    invalid = builder.Membership("m49:630", "latin_america_caribbean", "counterpart", "none")
    with pytest.raises(builder.ReferenceBuildError, match="membership_us_relationship"):
        builder.validate_membership((invalid,))


def test_registry_and_provenance_pin_exact_components() -> None:
    import yaml

    metadata = json.loads(builder.METADATA_OUT.read_text())
    for key, path in (
        ("policy", builder.POLICY_PATH),
        ("source_manifest", builder.SOURCE_MANIFEST),
    ):
        assert metadata[key]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    registry = yaml.safe_load((ROOT / "data-artifacts.yaml").read_text())
    (entry,) = [
        row
        for row in registry["artifacts"]
        if row["name"] == "international_counterpart_reference_2024"
    ]
    assert entry["rows"] == 252
    assert entry["sha256"] == metadata["artifact"]["sha256"]
    sources = json.loads(builder.SOURCE_MANIFEST.read_text())
    assert sources["trade_year"] == 2024 and sources["identity_snapshot"] == "2026-09-20"
    assert len(sources["sources"]) == 7
