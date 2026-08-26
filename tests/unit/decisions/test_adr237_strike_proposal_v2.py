"""Exact decision-index contract for V2 strike-proposal admission."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DECISIONS_DIR = Path(__file__).resolve().parents[3] / "ai" / "decisions"
ADR_STEM = "ADR237_strike_proposal_v2"
ADR_PATH = DECISIONS_DIR / f"{ADR_STEM}.yaml"
INDEX_PATH = DECISIONS_DIR / "index.yaml"
CONTRACT_PATH = DECISIONS_DIR.parents[1] / "contracts" / "strike_proposal_v2.yaml"
EXPECTED_TITLE = (
    "Strike Proposal V2 requires authoritative habitation and material worker "
    "connection while leaving every affected cohort independent"
)


def _mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_adr237_records_authoritative_habitation_and_worker_independence() -> None:
    decision = _mapping(ADR_PATH)[ADR_STEM]
    index = _mapping(INDEX_PATH)

    assert decision["status"] == "accepted"
    assert decision["date"] == "2026-08-26"
    assert decision["title"] == EXPECTED_TITLE
    assert decision["crate"] == "babylon-practice-contract"
    assert decision["live_activation"] is False

    decision_text = " ".join(str(decision["decision"]).split())
    for required_text in (
        "complete `ResolvedPracticeBatchV2`",
        "cannot bypass campaign habitation",
        "attributed organization membership",
        "does not re-mint the retired `EMPLOYMENT` edge",
        "grant no strike authority",
        "`PENDING_INDEPENDENT_RESOLUTION`",
        "cannot select, omit, rank, vote for, or command",
        "not worker, organization, workplace, unit-size, rank, or participation quotas",
    ):
        assert required_text in decision_text

    assert index["meta"]["version"] == "1.86.0"
    assert index["decisions"][ADR_STEM] == {
        "title": EXPECTED_TITLE,
        "status": "accepted",
        "date": "2026-08-26",
        "file": ADR_PATH.name,
    }


def test_adr237_schema_pins_material_intersection_and_pending_only_rows() -> None:
    contract = _mapping(CONTRACT_PATH)

    assert contract["strike_contract_values"] == {
        "material_connection_law": 1,
        "participation_law": 1,
        "max_affected_cohorts": 65_536,
        "max_organization_relations": 65_536,
    }
    assert contract["participation_states"] == {"PENDING_INDEPENDENT_RESOLUTION": 1}
    assert contract["canonical_lengths"] == {
        "strike_contract_bytes": 48,
        "labor_process_register_header_bytes": 91,
        "affected_cohort_row_bytes": 96,
        "organization_relation_row_bytes": 104,
        "proposal_key_bytes": 82,
        "participation_row_bytes": 33,
        "admitted_proposal_header_bytes": 220,
    }
    assert "gameplay activation" in contract["excluded_surfaces"]
