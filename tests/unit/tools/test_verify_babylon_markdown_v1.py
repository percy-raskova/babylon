"""Independent behavioral checks for BabylonMarkdownV1."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
from tools.verify_babylon_markdown_v1 import (
    BabylonMarkdownContractRefusal,
    fog_chip,
    git_export_rewrite,
    load_contract,
    load_vectors,
    main,
    validate_profile,
    verify_all,
)

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "contracts" / "babylon_markdown_v1.yaml"
VECTORS = ROOT / "contracts" / "babylon_markdown_v1_vectors.jsonl"


def test_shared_contract_verifies_independently() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)

    assert contract["meta"]["contract"] == "BabylonMarkdownV1"
    assert verify_all(contract, vectors) == []


def test_every_vector_kind_is_present() -> None:
    vectors = load_vectors(VECTORS)

    assert {row["kind"] for row in vectors} == {"valid", "refusal", "identity", "citation"}
    assert len(vectors) == 17
    assert [row["id"] for row in vectors if row["kind"] == "valid"] == [
        "valid-archive-page-granted-links",
        "valid-archive-page-bare-link",
        "valid-assembled-profile-forms",
    ]
    assert [row["id"] for row in vectors if row["kind"] == "citation"] == [
        "citation-pinned-example",
        "citation-label-star-refuses",
        "citation-source-semicolon-refuses",
        "citation-double-separator-backtracks",
        "citation-double-separator-refuses",
        "citation-empty-value-refuses",
        "citation-locator-semicolon-accepted",
    ]


def test_valid_row_mutation_refuses_stale_profile_bytes() -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    row = next(r for r in vectors if r["id"] == "valid-assembled-profile-forms")
    raw = bytearray.fromhex(row["data"]["markdown_hex"])
    raw[0] ^= 0xFF
    row["data"]["markdown_hex"] = raw.hex()

    errors = verify_all(contract, vectors)

    assert any("valid-assembled-profile-forms" in error for error in errors)


def test_citation_row_that_disagrees_with_the_regex_is_flagged() -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    row = next(r for r in vectors if r["id"] == "citation-pinned-example")
    row["data"]["recognized"] = not row["data"]["recognized"]

    errors = verify_all(contract, vectors)

    assert any("citation-pinned-example" in error for error in errors)


def test_refusal_row_that_validates_is_flagged() -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    row = next(r for r in vectors if r["id"] == "refusal-crlf-ending")
    row["data"]["markdown_hex"] = b"# plain prose\n".hex()

    errors = verify_all(contract, vectors)

    assert any("refusal-crlf-ending" in error for error in errors)


def test_crlf_and_raw_html_refusals_fire_independently() -> None:
    assert validate_profile(b"# Title\r\n") == "crlf_ending"
    assert validate_profile(b"# Title\n\n<div>x</div>\n") == "raw_html"
    assert validate_profile(b"\xff\xfe") == "not_utf8"


def test_bare_link_chip_synthesizes_with_zero_label_bytes() -> None:
    chip = fog_chip("place", "2674900")

    assert chip == "unknown place · 2674900"
    assert "Southfield" not in chip
    exported = git_export_rewrite("[](subject:place/2674900)")
    assert exported == chip


def test_non_subject_scheme_refuses() -> None:
    assert validate_profile(b"[BLS](https://example.invalid/)\n") == "disallowed_link_scheme"


def test_main_entrypoint_verifies_repository_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vectors_path = tmp_path / "elsewhere" / "copied.jsonl"
    vectors_path.parent.mkdir(parents=True, exist_ok=True)
    vectors_path.write_text(VECTORS.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify_babylon_markdown_v1.py",
            "--schema",
            str(SCHEMA),
            "--vectors",
            str(vectors_path),
        ],
    )

    assert main() == 0


def test_contract_drift_refuses() -> None:
    contract = load_contract(SCHEMA)
    contract["constants"]["profile_id"] = "drifted"

    try:
        verify_all(contract, load_vectors(VECTORS))
    except BabylonMarkdownContractRefusal as error:
        assert error.code == "compiled_contract_drift"
    else:  # pragma: no cover - the refusal must fire
        raise AssertionError("compiled contract drift must refuse")
