"""Independent behavioral checks for CountyDossierParityV1."""

from __future__ import annotations

import copy
import json
import struct
from pathlib import Path

import pytest
from tools.verify_county_dossier_parity_v1 import (
    CountyDossierParityRefusal,
    canonical_statblock,
    load_contract,
    load_vectors,
    main,
    verify_all,
)

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "contracts" / "county_dossier_parity_v1.yaml"
VECTORS = ROOT / "contracts" / "county_dossier_parity_v1_vectors.jsonl"


def test_shared_contract_verifies_independently() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)

    assert contract["meta"]["contract"] == "CountyDossierParityV1"
    assert verify_all(contract, vectors) == []


def test_vector_ids_and_kinds_are_pinned() -> None:
    vectors = load_vectors(VECTORS)

    assert [row["id"] for row in vectors] == [
        "parity-wayne-normal",
        "parity-oakland-zero-wage",
        "parity-wayne-negative-zero",
        "parity-oakland-absent-phi",
        "parity-wayne-field-grant-redacted",
        "parity-wayne-place-redlink",
    ]
    assert {row["kind"] for row in vectors} == {"parity"}


def test_signal_value_mutation_refuses() -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    row = vectors[0]
    row["data"]["expected"]["signals"][0]["value"] = "999.000000"

    errors = verify_all(contract, vectors)

    assert any(f"{row['id']}: signal parity mismatch" in error for error in errors)


def test_grant_removal_moves_the_visible_signal_list() -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    row = next(item for item in vectors if item["id"] == "parity-wayne-field-grant-redacted")
    row["data"]["grants"]["field_keys"] = ["median-wage", "phi-hour"]

    errors = verify_all(contract, vectors)

    assert any("parity-wayne-field-grant-redacted" in error for error in errors)


def test_absent_committed_field_emits_no_signal_and_null_view_bits() -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    row = next(item for item in vectors if item["id"] == "parity-oakland-absent-phi")
    assert row["data"]["committed"]["phi_hour_bits"] is None
    assert row["data"]["expected"]["county_view"]["phi_hour_bits"] is None
    assert all(signal["grant_key"] != "phi-hour" for signal in row["data"]["expected"]["signals"])

    assert verify_all(contract, vectors) == []


def test_off_grid_committed_value_refuses_as_the_known_divergence() -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    row = next(item for item in vectors if item["id"] == "parity-wayne-normal")
    # 0.1 + 1e-9 is not a fixed point of the oracle's 1e-6 quantization grid.
    off_grid = struct.pack(">d", 0.1 + 1e-9).hex()
    row["data"]["committed"]["median_wage_bits"] = off_grid
    row["data"]["expected"]["county_view"]["median_wage_bits"] = off_grid

    errors = verify_all(contract, vectors)

    assert any("off-grid committed value" in error for error in errors)


def test_negative_zero_canonicalization_is_pinned_not_vacuous() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    row = next(item for item in vectors if item["id"] == "parity-wayne-negative-zero")

    assert row["data"]["committed"]["median_wage_bits"] == "8000000000000000"
    assert row["data"]["expected"]["county_view"]["median_wage_bits"] == "0" * 16
    median_signal = next(
        signal
        for signal in row["data"]["expected"]["signals"]
        if signal["grant_key"] == "median-wage"
    )
    assert median_signal["value"] == "0.000000"
    assert canonical_statblock(-0.0) == "0.000000"
    assert verify_all(contract, vectors) == []


def test_places_follow_place_subject_grants() -> None:
    vectors = load_vectors(VECTORS)
    known = next(item for item in vectors if item["id"] == "parity-wayne-normal")
    known_names = {
        place["place_geoid"]: place["known_name"] for place in known["data"]["expected"]["places"]
    }
    assert known_names["2622000"] == "Detroit city"
    assert known_names["2668880"] is None
    redlink = next(item for item in vectors if item["id"] == "parity-wayne-place-redlink")
    assert all(place["known_name"] is None for place in redlink["data"]["expected"]["places"])
    geoids = [place["place_geoid"] for place in redlink["data"]["expected"]["places"]]
    assert geoids == sorted(geoids)


def test_county_view_presence_of_non_null_field_refuses() -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    row = vectors[0]
    row["data"]["expected"]["county_view"]["legitimacy"] = 0.9

    errors = verify_all(contract, vectors)

    assert any("legitimacy must be null under D2" in error for error in errors)


def test_compiled_contract_drift_refuses() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    contract["constants"]["statblock_format"] = "%.5f"

    with pytest.raises(CountyDossierParityRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == "compiled_contract_drift"


def test_missing_vector_row_refuses_with_vector_id_drift() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)[1:]

    with pytest.raises(CountyDossierParityRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == "vector_id_drift"


def test_duplicate_vector_id_refuses_before_indexing() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    duplicate = copy.deepcopy(vectors[1])
    duplicate["id"] = vectors[0]["id"]
    vectors.append(duplicate)

    with pytest.raises(CountyDossierParityRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == "duplicate_vector_id"


def test_cli_prints_typed_refusal_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vectors = copy.deepcopy(load_vectors(VECTORS))
    vectors[0].pop("id")
    vectors_path = tmp_path / "malformed.jsonl"
    vectors_path.write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in vectors),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify_county_dossier_parity_v1.py",
            "--schema",
            str(SCHEMA),
            "--vectors",
            str(vectors_path),
        ],
    )

    assert main() == 1
    assert capsys.readouterr().out == "vector_row_shape: 1\n"


def test_cli_passes_on_the_checked_corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vectors_path = tmp_path / "elsewhere" / "copied.jsonl"
    vectors_path.parent.mkdir(parents=True, exist_ok=True)
    vectors_path.write_text(VECTORS.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify_county_dossier_parity_v1.py",
            "--schema",
            str(SCHEMA),
            "--vectors",
            str(vectors_path),
        ],
    )

    assert main() == 0


def test_vector_loader_refuses_row_and_line_overflow(tmp_path: Path) -> None:
    row = '{"id":"x","kind":"parity","data":{}}'
    rows_path = tmp_path / "rows.jsonl"
    rows_path.write_text("\n".join([row] * 17), encoding="utf-8")
    with pytest.raises(CountyDossierParityRefusal, match="too_many_rows"):
        load_vectors(rows_path)

    line_path = tmp_path / "line.jsonl"
    line_path.write_text("x" * 16_385, encoding="utf-8")
    with pytest.raises(CountyDossierParityRefusal, match="invalid_line_length"):
        load_vectors(line_path)


def test_vector_loader_refuses_duplicate_json_keys(tmp_path: Path) -> None:
    vectors_path = tmp_path / "duplicate-key.jsonl"
    vectors_path.write_text(
        '{"id":"a","id":"b","kind":"parity","data":{}}',
        encoding="utf-8",
    )

    with pytest.raises(CountyDossierParityRefusal) as exc_info:
        load_vectors(vectors_path)

    assert exc_info.value.code == "duplicate_json_key"


def test_non_finite_committed_bits_refuse(tmp_path: Path) -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    vectors[0]["data"]["committed"]["median_wage_bits"] = "7ff0000000000000"  # +inf

    errors = verify_all(contract, vectors)

    assert any("non_finite_value" in error for error in errors)


def test_unsorted_links_refuse_with_the_typed_code() -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    row = next(item for item in vectors if item["id"] == "parity-wayne-normal")
    row["data"]["links"][0], row["data"]["links"][1] = (
        row["data"]["links"][1],
        row["data"]["links"][0],
    )

    errors = verify_all(contract, vectors)

    assert any("invalid_link_order" in error for error in errors)


def test_missing_nullable_committed_member_refuses_not_null() -> None:
    """A dropped nullable member is not an explicit JSON null."""
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    absent = next(item for item in vectors if item["id"] == "parity-oakland-absent-phi")
    absent["data"]["committed"].pop("phi_hour_bits")

    with pytest.raises(CountyDossierParityRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == "invalid_key_set"


def test_missing_d2_null_county_view_field_refuses_not_null() -> None:
    """Every D2-null field must be present-and-null, never dropped."""
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    vectors[0]["data"]["expected"]["county_view"].pop("legitimacy")

    with pytest.raises(CountyDossierParityRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == "invalid_key_set"


def test_extra_nested_member_refuses() -> None:
    """A stray nested key is drift even when every required member matches."""
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    vectors[0]["data"]["committed"]["surplus"] = None

    with pytest.raises(CountyDossierParityRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == "invalid_key_set"


def test_non_mapping_vector_kinds_refuses_typed() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    contract["vector_kinds"] = ["parity"]

    with pytest.raises(CountyDossierParityRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == "invalid_schema"


def test_non_mapping_divergence_entry_refuses_typed() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    contract["known_divergences"] = ["oracle-snap-to-grid"]

    with pytest.raises(CountyDossierParityRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == "invalid_schema"


def test_duplicate_yaml_key_refuses_invalid_schema(tmp_path: Path) -> None:
    schema_path = tmp_path / "duplicate-key.yaml"
    schema_path.write_text(
        SCHEMA.read_text(encoding="utf-8").replace(
            'statblock_format: "%.6f"',
            'statblock_format: "%.6f"\n  statblock_format: "%.5f"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(CountyDossierParityRefusal) as exc_info:
        load_contract(schema_path)

    assert exc_info.value.code == "invalid_schema"


def test_negative_median_wage_refuses_out_of_the_oracle_domain() -> None:
    """CountyView.median_wage is the non-negative Currency type."""
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    row = vectors[0]
    negative = struct.pack(">d", -21.0).hex()
    row["data"]["committed"]["median_wage_bits"] = negative
    row["data"]["expected"]["county_view"]["median_wage_bits"] = negative

    with pytest.raises(CountyDossierParityRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == "value_out_of_domain"


def test_negative_phi_hour_remains_in_the_signed_domain() -> None:
    """CountyView.imperial_rent_phi is SignedLaborHours: negative values are legal."""
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    row = vectors[0]
    negative_phi = struct.pack(">d", -2.5).hex()
    row["data"]["committed"]["phi_hour_bits"] = negative_phi
    row["data"]["expected"]["county_view"]["phi_hour_bits"] = negative_phi
    for signal in row["data"]["expected"]["plan_signals"]:
        if signal["grant_key"] == "phi-hour":
            signal["value"] = "-2.500000"
    for signal in row["data"]["expected"]["signals"]:
        if signal["grant_key"] == "phi-hour":
            signal["value"] = "-2.500000"

    assert verify_all(contract, vectors) == []


def test_huge_finite_committed_value_refuses_typed_not_traceback() -> None:
    """1e308 overflows the quantizer's *1e6; the refusal must stay typed."""
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    row = vectors[0]
    huge = struct.pack(">d", 1e308).hex()
    row["data"]["committed"]["median_wage_bits"] = huge
    row["data"]["expected"]["county_view"]["median_wage_bits"] = huge

    with pytest.raises(CountyDossierParityRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == "value_out_of_domain"
