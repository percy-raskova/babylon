"""Governance boundary for the first PER-20 tick-commit slice."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
DECISIONS = ROOT / "ai" / "decisions"
ADR_STEM = "ADR242_tick_commit_claim_v1"
TITLE = (
    "TickCommitClaimV1 binds a durable campaign and tick directly to the "
    "kernel-owned content identity before PostgreSQL activation"
)


def _mapping(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_adr242_binds_contract_ownership_and_exclusions() -> None:
    adr_path = DECISIONS / f"{ADR_STEM}.yaml"
    decision = _mapping(adr_path)[ADR_STEM]
    index = _mapping(DECISIONS / "index.yaml")

    assert decision["status"] == "accepted"
    assert decision["issue"] == "PER-20"
    assert decision["title"] == TITLE
    assert decision["owners"]["tick_content_identity"] == "babylon-kernel"
    assert decision["canonical_contract"] == {
        "schema": "contracts/tick_commit_claim_v1.yaml",
        "vectors": "contracts/tick_commit_claim_v1_vectors.jsonl",
        "independent_verifier": "tools/verify_tick_commit_claim_v1.py",
    }
    normalized = " ".join(decision["decision"].split())
    for text in (
        "fixed 93-byte",
        "Persistence does not alias, re-export, decode, or independently recompute",
        "not `CommittedTickEnvelope`",
        "grants no PostgreSQL I/O or writer authority",
    ):
        assert text in normalized

    assert index["meta"]["version"] == "1.87.0"
    assert index["decisions"][ADR_STEM] == {
        "title": TITLE,
        "status": "accepted",
        "date": "2026-08-27",
        "file": adr_path.name,
    }


def test_historical_slice_boundary_is_superseded_by_the_one_way_cutover() -> None:
    design = (
        ROOT / "docs" / "superpowers" / "specs" / "2026-08-27-per-20-tick-commit-claim-design.md"
    ).read_text(encoding="utf-8")
    writer_gate = ROOT / "rust" / "crates" / "babylon-persistence" / "src" / "writer_gate.rs"
    runtime = (ROOT / "rust" / "crates" / "babylon-persistence" / "src" / "runtime.rs").read_text(
        encoding="utf-8"
    )

    assert "This slice adds no migration, SQL, database connection" in design
    assert not writer_gate.exists()
    assert "activate_rust_persistence_v1" in runtime
    assert "PersistenceAuthorityStateV1::RustActive" in runtime
