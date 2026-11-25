"""The twelve-trade mapping cuts consumer goods and leisure out of version 1's ten trades."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import make_national_county_reference as county  # type: ignore[import-not-found]  # noqa: E402
import make_national_qcew_function_basis as basis  # type: ignore[import-not-found]  # noqa: E402
import make_national_qcew_function_basis_v2 as v2  # type: ignore[import-not-found]  # noqa: E402


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
    assert v2.MAPPING_V2_PATH != basis.MAPPING_PATH
