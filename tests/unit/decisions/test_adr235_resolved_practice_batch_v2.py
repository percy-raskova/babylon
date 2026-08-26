"""Exact decision-index contract for the V2 resolved-practice batch."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DECISIONS_DIR = Path(__file__).resolve().parents[3] / "ai" / "decisions"
ADR_STEM = "ADR235_resolved_practice_batch_v2"
ADR_PATH = DECISIONS_DIR / f"{ADR_STEM}.yaml"
INDEX_PATH = DECISIONS_DIR / "index.yaml"
CONTRACT_PATH = DECISIONS_DIR.parents[1] / "contracts" / "resolved_practice_batch_v2.yaml"
EXPECTED_TITLE = (
    "ResolvedPracticeBatchV2 binds exact accepted proposals to committed authority "
    "without allocation priority or a self-referential digest"
)


def _mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_adr235_declares_the_resolved_batch_boundary_and_exact_index_row() -> None:
    decision = _mapping(ADR_PATH)[ADR_STEM]
    index = _mapping(INDEX_PATH)

    assert decision["status"] == "accepted"
    assert decision["date"] == "2026-08-26"
    assert decision["title"] == EXPECTED_TITLE
    assert decision["crate"] == "babylon-practice-contract"
    assert decision["live_activation"] is False

    decision_text = " ".join(str(decision["decision"]).split())
    for required_text in (
        "exact active row selected from that ledger",
        "complete `PracticeProposalKeyV2`",
        "grants no material priority",
        "never appears inside those bytes",
        "not actor capacity, organization count, political rank, or a gameplay quota",
        "does not create the accepted-input persistence transaction",
        "`authority_resource_conflict`",
    ):
        assert required_text in decision_text

    assert index["meta"]["version"] == "1.84.0"
    assert index["decisions"][ADR_STEM] == {
        "title": EXPECTED_TITLE,
        "status": "accepted",
        "date": "2026-08-26",
        "file": ADR_PATH.name,
    }


def test_adr235_schema_pins_no_self_hash_and_no_live_allocation() -> None:
    contract = _mapping(CONTRACT_PATH)

    assert contract["limits"]["items"]["value"] == 4_096
    assert contract["limits"]["nested_authority_bytes"] == {
        "value": 127,
        "classification": "Derived",
        "purpose": "equal the frozen PracticeInputAuthorityV2 canonical byte length",
    }
    assert contract["limits"]["batch_canonical_bytes"]["value"] == 67_645_599
    assert contract["digest_contract"] == {
        "algorithm": "SHA-256",
        "preimage": "validated canonical batch bytes",
        "embedded_digest_field": "forbidden",
    }
    assert "resource reservation, clearing, or capacity allocation" in contract["excluded_surfaces"]
    assert "gameplay activation" in contract["excluded_surfaces"]
