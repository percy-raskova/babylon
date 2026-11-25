"""The twelve-trade mapping cuts consumer goods and leisure out of version 1's ten trades."""

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
import make_national_cohort_reference as cohort  # type: ignore[import-not-found]  # noqa: E402
import make_national_cohort_reference_v2 as cohort_v2  # type: ignore[import-not-found]  # noqa: E402
import make_national_county_reference as county  # type: ignore[import-not-found]  # noqa: E402
import make_national_qcew_function_basis as basis  # type: ignore[import-not-found]  # noqa: E402
import make_national_qcew_function_basis_v2 as v2  # type: ignore[import-not-found]  # noqa: E402
import make_national_trade_accounts as trade_accounts  # type: ignore[import-not-found]  # noqa: E402
import make_national_trade_pay as trade_pay  # type: ignore[import-not-found]  # noqa: E402


def document() -> dict[str, object]:
    return copy.deepcopy(json.loads(v2.MAPPING_V2_PATH.read_bytes()))


def functions(doc: dict[str, object]) -> list[dict[str, object]]:
    found = doc["functions"]
    assert isinstance(found, list)
    return found


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v2_mapping_has_twelve_trades() -> None:
    mapping = v2.load_mapping_v2()
    assert tuple(item["id"] for item in mapping.document["functions"]) == v2.FUNCTION_IDS_V2
    assert len(mapping.code_to_function) == 63
    assert len(mapping.source_codes) == 64
    assert mapping.document["contract"] == "NationalQcewFunctionMappingV2"
    assert v2.MAPPING_V2_PATH.stat().st_size < 16_384


def test_v2_mapping_moves_the_cut_industries() -> None:
    mapping = v2.load_mapping_v2()
    for code in ("3361", "3343", "3352", "314", "339"):
        assert mapping.function_for(code) == "consumer_goods"
    for code in ("3364", "3353", "3341"):
        assert mapping.function_for(code) == "capital_goods"
    for code in ("332", "3122"):
        assert mapping.function_for(code) == "manufacturing"
    for code in ("71", "72"):
        assert mapping.function_for(code) == "leisure_hospitality"
    assert mapping.function_for("62") == "household_services"
    assert mapping.function_for("99") is None
    for code in ("334", "335", "336"):
        with pytest.raises(county.ReferenceBuildError, match="unsupported_naics"):
            mapping.function_for(code)


def test_v2_mapping_refuses_overlap_duplicates_and_identity() -> None:
    doc = document()
    next(f for f in functions(doc) if f["id"] == "capital_goods")["naics_codes"].append("336")  # type: ignore[union-attr]
    with pytest.raises(county.ReferenceBuildError, match="overlapping_naics"):
        v2.validate_mapping_v2(doc)

    doc = document()
    next(f for f in functions(doc) if f["id"] == "food")["naics_codes"].append("333")  # type: ignore[union-attr]
    with pytest.raises(county.ReferenceBuildError, match="duplicate_naics"):
        v2.validate_mapping_v2(doc)

    doc = document()
    doc["contract"] = "NationalQcewFunctionMappingV1"
    with pytest.raises(county.ReferenceBuildError, match="function_mapping_identity"):
        v2.validate_mapping_v2(doc)

    doc = document()
    doc["functions"] = [f for f in functions(doc) if f["id"] != "leisure_hospitality"]
    with pytest.raises(county.ReferenceBuildError, match="function_mapping_functions"):
        v2.validate_mapping_v2(doc)


def test_version_1_files_keep_their_digests() -> None:
    economy = ROOT / "src/babylon/data/reference/economy"
    assert (
        digest(basis.MAPPING_PATH)
        == "7185d0bedb1bf4a830ff5199d4af9fbd53aa88b66ca4e34c167404422c22c07d"
    )
    assert digest(economy / "national_qcew_function_basis_2024.parquet") == (
        "df7b6937540a0e6afab334de146c8229fac4865829347f8fca37c86c9a056d7c"
    )
    assert digest(economy / "national_cohort_reference_2024.csv.gz") == (
        "1c963f6b709c31f798253e41662619a32ad31d4532022931392cf2fbd78eb497"
    )
    version_1 = (
        basis.MAPPING_PATH,
        basis.ARTIFACT_OUT,
        basis.METADATA_OUT,
        cohort.ARTIFACT_OUT,
        cohort.METADATA_OUT,
    )
    version_2 = (
        v2.MAPPING_V2_PATH,
        v2.ARTIFACT_OUT,
        v2.METADATA_OUT,
        cohort_v2.ARTIFACT_OUT,
        cohort_v2.METADATA_OUT,
        trade_pay.ARTIFACT_OUT,
        trade_pay.METADATA_OUT,
        trade_accounts.ARTIFACT_OUT,
        trade_accounts.METADATA_OUT,
        trade_accounts.ACCOUNTS_MAPPING,
    )
    assert set(version_1).isdisjoint(version_2)
    assert len(set(version_2)) == len(version_2)


def source(
    area: str,
    level: int,
    *,
    code: str = "3361",
    ownership: str = "5",
    establishments: str = "4",
    jobs: str = "10",
    payroll: str = "1000",
    disclosure: str = "",
) -> dict[str, str]:
    return {
        "area_fips": area,
        "own_code": ownership,
        "industry_code": code,
        "agglvl_code": str(level),
        "size_code": "0",
        "year": "2024",
        "qtr": "A",
        "disclosure_code": disclosure,
        "annual_avg_estabs": establishments,
        "annual_avg_emplvl": jobs,
        "total_annual_wages": payroll,
        "annual_avg_wkly_wage": "0",
    }


COUNTIES = {"01017", "26163"}


def test_each_area_takes_its_role() -> None:
    mapping = v2.load_mapping_v2()
    rows = [
        source("US000", 16),
        source("01000", 56),
        source("01017", 76),
        source("01017", 75, code="336"),
    ]
    capture = v2.capture_basis_v2(rows, COUNTIES, mapping)
    got = [(r.row_role, r.agglvl_code) for r in capture.rows]
    assert got == [
        ("county_leaf", 76),
        ("county_parent", 75),
        ("nation_leaf", 16),
        ("state_leaf", 56),
    ]
    keys = [(r.row_role, r.area_fips, r.ownership_code, r.naics_code) for r in capture.rows]
    assert keys == sorted(keys)


def test_only_the_placement_parents_are_kept() -> None:
    mapping = v2.load_mapping_v2()
    rows = [
        source("01017", 74, code="31-33"),
        source("01017", 75, code="115"),
        source("01017", 71, code="10"),
        source("01017", 74, code="21"),
        source("01017", 76, code="3331"),
        source("01017", 77, code="3361"),
        source("01017", 70, code="10", ownership="0", jobs="500"),
    ]
    capture = v2.capture_basis_v2(rows, COUNTIES, mapping)
    roles = {(r.naics_code, r.row_role) for r in capture.rows}
    assert roles == {
        ("31-33", "county_parent"),
        ("115", "county_parent"),
        ("10", "county_parent"),
        ("21", "county_leaf"),
    }
    assert capture.diagnostics["national_jobs"]["county_jobs"] == 500


def test_a_wrong_level_for_the_role_is_refused() -> None:
    mapping = v2.load_mapping_v2()
    with pytest.raises(county.ReferenceBuildError, match="aggregation_identity: 3361"):
        v2.capture_basis_v2([source("01000", 76)], COUNTIES, mapping)


def test_unallocated_and_territories_make_no_rows() -> None:
    mapping = v2.load_mapping_v2()
    rows = [source("01999", 76), source("72000", 56)]
    capture = v2.capture_basis_v2(rows, COUNTIES, mapping)
    assert capture.rows == ()
    assert capture.diagnostics["outside_rows"] == {
        "domestic_unallocated": 1,
        "outside_50_states_dc": 1,
    }


def test_a_second_row_for_one_cell_is_refused() -> None:
    mapping = v2.load_mapping_v2()
    with pytest.raises(county.ReferenceBuildError, match="duplicate_source_cell"):
        v2.capture_basis_v2([source("01017", 76), source("01017", 76)], COUNTIES, mapping)


def test_changed_source_bytes_are_refused_before_parsing(tmp_path: Path) -> None:
    target = tmp_path / "tiger/county/tl_2024_us_county.dbf"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"x")
    with pytest.raises(county.ReferenceBuildError, match="source_digest: tiger"):
        v2.build(
            source_root=tmp_path,
            artifact_out=tmp_path / "out.parquet",
            metadata_out=tmp_path / "out.metadata.json",
        )


def test_the_committed_v2_basis_holds_every_role() -> None:
    import yaml

    rows = v2.read_basis_v2()
    by_role = {role: [r for r in rows if r.row_role == role] for role in v2.ROLES}
    assert {k: len(v) for k, v in by_role.items()} == {
        "county_leaf": 151_199,
        "county_parent": 32_482,
        "nation_leaf": 166,
        "state_leaf": 5_119,
    }
    assert len(rows) == 188_966
    withheld = {k: sum(r.disclosure_code == "N" for r in v) for k, v in by_role.items()}
    assert withheld == {
        "county_leaf": 64_131,
        "county_parent": 9_400,
        "nation_leaf": 26,
        "state_leaf": 624,
    }
    assert not {"334", "335", "336"} & {r.naics_code for r in by_role["county_leaf"]}
    keys = [(r.row_role, r.area_fips, r.ownership_code, r.naics_code) for r in rows]
    assert all(a < b for a, b in zip(keys, keys[1:], strict=False))
    assert pq.read_schema(v2.ARTIFACT_OUT) == v2.SCHEMA_V2
    metadata = json.loads(v2.METADATA_OUT.read_text())
    assert metadata["artifact"]["sha256"] == digest(v2.ARTIFACT_OUT)
    registry = yaml.safe_load((ROOT / "data-artifacts.yaml").read_text())
    entries = [
        e for e in registry["artifacts"] if e["name"] == "national_qcew_function_basis_v2_2024"
    ]
    assert len(entries) == 1
    assert entries[0]["sha256"] == digest(v2.ARTIFACT_OUT)
    assert entries[0]["rows"] == 188_966
    assert v2.ARTIFACT_OUT.stat().st_size < 2_097_152
