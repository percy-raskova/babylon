"""Exact decision-index contract for V2 practice-intent identity."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

DECISIONS_DIR = Path(__file__).resolve().parents[3] / "ai" / "decisions"
ADR_STEM = "ADR234_practice_intent_v2"
ADR_PATH = DECISIONS_DIR / f"{ADR_STEM}.yaml"
INDEX_PATH = DECISIONS_DIR / "index.yaml"
CONTRACT_PATH = DECISIONS_DIR.parents[1] / "contracts" / "practice_intent_v2.yaml"
VECTORS_PATH = DECISIONS_DIR.parents[1] / "contracts" / "practice_intent_v2_vectors.jsonl"
EXPECTED_TITLE = (
    "PracticeIntentV2 binds stable proposals to authoritative habitation while "
    "preserving V1 and granting no material eligibility"
)


def _mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_adr234_declares_the_v2_intent_boundary_and_exact_index_row() -> None:
    decision = _mapping(ADR_PATH)[ADR_STEM]
    index = _mapping(INDEX_PATH)

    assert decision["status"] == "accepted"
    assert decision["date"] == "2026-08-26"
    assert decision["title"] == EXPECTED_TITLE
    assert decision["crate"] == "babylon-practice-contract"
    assert decision["live_activation"] is False

    decision_text = " ".join(str(decision["decision"]).split())
    for required_text in (
        "stable 32-byte target identity",
        "nonce distinguishes genuinely different proposals and grants no priority",
        "STRIKE accepts only LABOR_PROCESS",
        "every V2 semantic allowlist is empty",
        "a strike cannot name participation or withholding",
        "not actor capacity or organization quotas",
        "V1 and V2 intent decoders refuse the other domain",
        "ResolvedPracticeBatchV2",
    ):
        assert required_text in decision_text

    assert index["meta"]["version"] == "1.83.0"
    assert index["decisions"][ADR_STEM] == {
        "title": EXPECTED_TITLE,
        "status": "accepted",
        "date": "2026-08-26",
        "file": ADR_PATH.name,
    }


def test_adr234_schema_and_literal_vector_stay_in_lockstep() -> None:
    contract = _mapping(CONTRACT_PATH)
    cases = [json.loads(line) for line in VECTORS_PATH.read_text(encoding="utf-8").splitlines()]
    manifest = next(case for case in cases if case["case_id"] == "manifest")["data"]
    intent = next(case for case in cases if case["case_id"] == "intent-strike")["data"]

    assert contract["practice_ids"] == {
        "ORGANIZE": 1,
        "AGITATE": 2,
        "MUTUAL_AID": 3,
        "STRIKE": 4,
        "BLOCKADE": 5,
        "OCCUPATION": 6,
        "DAMAGE": 7,
        "CAPITAL_STRIKE": 8,
    }
    assert contract["target_allowlists"]["STRIKE"] == ["LABOR_PROCESS"]
    assert contract["parameter_contract"]["semantic_allowlists"] == "empty"
    assert contract["limits"]["intent_canonical_bytes"]["value"] == 16_384
    assert manifest["canonical_example_bytes"] == len(bytes.fromhex(intent["canonical_hex"]))
    assert manifest["practice_codes"] == list(range(1, 9))
    assert manifest["target_tag_codes"] == list(range(1, 13))
