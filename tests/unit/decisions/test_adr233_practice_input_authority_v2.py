"""Exact decision-index contract for V2 practice-input authority."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

DECISIONS_DIR = Path(__file__).resolve().parents[3] / "ai" / "decisions"
ADR_STEM = "ADR233_practice_input_authority_v2"
ADR_PATH = DECISIONS_DIR / f"{ADR_STEM}.yaml"
INDEX_PATH = DECISIONS_DIR / "index.yaml"
CONTRACT_PATH = DECISIONS_DIR.parents[1] / "contracts" / "practice_input_authority_v2.yaml"
VECTORS_PATH = DECISIONS_DIR.parents[1] / "contracts" / "practice_input_authority_v2_vectors.jsonl"
EXPECTED_TITLE = (
    "PracticeInputAuthorityV2 makes campaign habitation authoritative while "
    "preserving V1 bytes and granting no material eligibility"
)


def _mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_adr233_declares_the_v2_authority_boundary_and_exact_index_row() -> None:
    adr_document = _mapping(ADR_PATH)
    index_document = _mapping(INDEX_PATH)

    assert list(adr_document) == [ADR_STEM]
    decision = adr_document[ADR_STEM]
    assert decision["status"] == "accepted"
    assert decision["date"] == "2026-08-26"
    assert decision["title"] == EXPECTED_TITLE
    assert decision["crate"] == "babylon-practice-contract"
    assert decision["live_activation"] is False

    decision_text = " ".join(str(decision["decision"]).split())
    for required_text in (
        "authoritative campaign state",
        "exactly one active PLAYER_SEAT",
        "16,384-row",
        "not an organization or political quota",
        "grants no material eligibility",
        "V1 domains, bytes, digests, refusal vectors",
        "resource-reservation and capacity-allocation contract remains separate",
        "mid-campaign player-seat reassignment",
    ):
        assert required_text in decision_text

    assert index_document["meta"]["version"] == "1.84.0"
    assert str(index_document["meta"]["updated"]) == "2026-08-26"
    assert index_document["decisions"][ADR_STEM] == {
        "title": EXPECTED_TITLE,
        "status": "accepted",
        "date": "2026-08-26",
        "file": ADR_PATH.name,
    }


def test_adr233_row_size_matches_the_schema_and_literal_vector() -> None:
    decision = _mapping(ADR_PATH)[ADR_STEM]
    contract = _mapping(CONTRACT_PATH)
    cases = [json.loads(line) for line in VECTORS_PATH.read_text(encoding="utf-8").splitlines()]
    manifest = next(case for case in cases if case["case_id"] == "manifest")
    authority = next(case for case in cases if case["case_id"] == "authority-player")
    actual_bytes = len(bytes.fromhex(authority["data"]["canonical_hex"]))

    assert contract["limits"]["row_canonical_bytes"]["value"] == actual_bytes
    assert manifest["data"]["row_canonical_bytes"] == actual_bytes
    assert actual_bytes == 127
    assert "127 canonical bytes" in decision["decision"]
    assert "2,080,768 bytes" in decision["decision"]
