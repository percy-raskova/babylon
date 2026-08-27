"""Exact decision-index contract for V2 practice-resource allocation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DECISIONS_DIR = Path(__file__).resolve().parents[3] / "ai" / "decisions"
ADR_STEM = "ADR236_practice_resource_allocation_v2"
ADR_PATH = DECISIONS_DIR / f"{ADR_STEM}.yaml"
INDEX_PATH = DECISIONS_DIR / "index.yaml"
CONTRACT_PATH = DECISIONS_DIR.parents[1] / "contracts" / "practice_resource_allocation_v2.yaml"
EXPECTED_TITLE = (
    "Practice Resource Allocation V2 derives exact material requests from sealed content "
    "and conserves scarcity without order priority"
)


def _mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_adr236_records_the_complete_allocator_law_and_exact_index_row() -> None:
    decision = _mapping(ADR_PATH)[ADR_STEM]
    index = _mapping(INDEX_PATH)

    assert decision["status"] == "accepted"
    assert decision["date"] == "2026-08-26"
    assert decision["title"] == EXPECTED_TITLE
    assert decision["crate"] == "babylon-practice-contract"
    assert decision["live_activation"] is False

    decision_text = " ".join(str(decision["decision"]).split())
    for required_text in (
        "sealed content, never actor-authored intent parameters",
        "quoted_resource_contract_digest",
        "floor(available * requested_i / total_requested)",
        "remains explicitly unallocated",
        "selects no winner",
        "`authority_resource_conflict`",
        "committed material outcome",
        "canonical order grants no material priority",
        "does not reuse `babylon-graph::Capacity::allocate`",
    ):
        assert required_text in decision_text

    assert index["meta"]["version"] == "1.87.0"
    assert index["decisions"][ADR_STEM] == {
        "title": EXPECTED_TITLE,
        "status": "accepted",
        "date": "2026-08-26",
        "file": ADR_PATH.name,
    }


def test_adr236_schema_pins_exact_units_conservation_and_inert_activation() -> None:
    contract = _mapping(CONTRACT_PATH)

    assert contract["encoding"]["quantity_encoding"] == "u64"
    assert contract["allocation_contract_values"] == {
        "quantity_width_bits": 64,
        "request_derivation_law": 1,
        "divisible_law": 1,
        "exclusive_tie_law": 1,
        "residual_law": 1,
        "max_requests_per_intent": 16,
        "max_requests_total": 65_536,
        "max_capacities_total": 65_536,
    }
    assert contract["canonical_lengths"] == {
        "allocation_contract_bytes": 66,
        "request_bytes": 202,
        "capacity_bytes": 122,
        "allocation_outcome_header_bytes": 90,
        "allocation_row_bytes": 40,
        "balance_row_bytes": 48,
    }
    assert contract["canonical_order"]["priority"] == "canonical order grants no material priority"
    assert "gameplay activation" in contract["excluded_surfaces"]
