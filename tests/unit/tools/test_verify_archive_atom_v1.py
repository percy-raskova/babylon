"""Independent behavioral checks for ArchiveAtomV1."""

from __future__ import annotations

import copy
import json
import struct
from pathlib import Path

from tools.verify_archive_atom_v1 import (
    ArchiveAtomContractRefusal,
    atom_id_from_fields,
    load_contract,
    load_vectors,
    main,
    verify_all,
)

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "contracts" / "archive_atom_v1.yaml"
VECTORS = ROOT / "contracts" / "archive_atom_v1_vectors.jsonl"


def _rows() -> list[dict]:
    return load_vectors(VECTORS)


def _row(row_id: str) -> dict:
    return next(row for row in _rows() if row["id"] == row_id)


def test_shared_contract_verifies_independently() -> None:
    contract = load_contract(SCHEMA)

    assert contract["meta"]["contract"] == "ArchiveAtomV1"
    assert verify_all(contract, _rows(), ROOT) == []


def test_main_exits_zero_on_the_pinned_corpus(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["verify_archive_atom_v1.py", "--schema", str(SCHEMA), "--vectors", str(VECTORS)],
    )
    assert main() == 0


def test_atom_id_is_content_addressed_over_every_field() -> None:
    row = copy.deepcopy(_row("encoding-place-f64-derived"))

    base, _ = atom_id_from_fields(row["data"])
    row["data"]["grant_key"] = "median-wage-2"
    changed, _ = atom_id_from_fields(row["data"])

    assert base != changed


def test_neg_zero_canonicalizes_to_pos_zero_identity() -> None:
    neg = copy.deepcopy(_row("encoding-f64-neg-zero-canonical"))
    pos = copy.deepcopy(neg)
    pos["data"]["value"]["bits_hex"] = "0000000000000000"

    neg_id, _ = atom_id_from_fields(neg["data"])
    pos_id, _ = atom_id_from_fields(pos["data"])

    assert neg_id == pos_id
    assert neg_id.hex() == neg["data"]["atom_id_hex"]


def test_nonfinite_bits_refuse_independently() -> None:
    for bits_hex in ("7ff0000000000000", "fff0000000000000", "7ff8000000000000"):
        row = copy.deepcopy(_row("encoding-place-f64-derived"))
        row["data"]["value"] = {"kind": "f64", "bits_hex": bits_hex}
        try:
            atom_id_from_fields(row["data"])
        except ArchiveAtomContractRefusal as error:
            assert error.code == "value_f64_nonfinite"
        else:  # pragma: no cover - refusal is mandatory
            raise AssertionError(f"{bits_hex} must refuse")


def test_finite_payload_encodings_match_bit_layouts() -> None:
    row = copy.deepcopy(_row("encoding-place-f64-derived"))
    row["data"]["value"] = {"kind": "f64", "bits_hex": "4029000000000000"}
    atom_id, kind = atom_id_from_fields(row["data"])
    assert kind == "f64"
    assert struct.unpack(">d", struct.pack(">Q", 0x4029000000000000))[0] == 12.5
    assert atom_id != b""

    u64_row = _row("encoding-concept-u64-designed")
    assert atom_id_from_fields(u64_row["data"])[1] == "u64"
    bool_row = _row("encoding-concept-bool-designed")
    assert atom_id_from_fields(bool_row["data"])[1] == "bool"


def test_visibility_predicate_boundaries() -> None:
    contract = load_contract(SCHEMA)
    rows = _rows()
    visible = next(row for row in rows if row["id"] == "visibility-granted-in-horizon")
    visible["data"]["expected_visible"] = False

    errors = verify_all(contract, rows, ROOT)

    assert any("visibility-granted-in-horizon" in error for error in errors)


def test_visibility_requires_a_grant_row() -> None:
    no_grant = _row("visibility-no-grant-row")

    assert no_grant["data"]["granted_tick"] is None
    assert no_grant["data"]["expected_visible"] is False


def test_atom_id_hex_drift_refuses() -> None:
    contract = load_contract(SCHEMA)
    rows = _rows()
    row = next(row for row in rows if row["id"] == "encoding-county-subject-text-observed")
    row["data"]["atom_id_hex"] = "0" * 64

    errors = verify_all(contract, rows, ROOT)

    assert any("encoding-county-subject-text-observed" in error for error in errors)


def test_required_row_ids_are_pinned() -> None:
    contract = load_contract(SCHEMA)
    rows = [row for row in _rows() if row["id"] != "refuse-f64-nan"]

    try:
        verify_all(contract, rows, ROOT)
    except ArchiveAtomContractRefusal as error:
        assert error.code == "vector_id_drift"
    else:  # pragma: no cover - the corpus set is pinned
        raise AssertionError("dropped refusal row must refuse")


def test_subject_id_discipline_per_kind() -> None:
    contract = load_contract(SCHEMA)
    rows = _rows()
    row = next(row for row in rows if row["id"] == "encoding-county-subject-text-observed")
    row["data"]["subject_id"] = "2600"

    errors = verify_all(contract, rows, ROOT)

    assert any("encoding-county-subject-text-observed" in error for error in errors)


def test_vector_file_is_utf8_jsonl() -> None:
    for line in VECTORS.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        assert set(row) == {"id", "kind", "data"}
