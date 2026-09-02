"""Governance boundary for the bounded PER-20 whole-payload envelope."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
DECISIONS = ROOT / "ai" / "decisions"
ADR_STEM = "ADR243_committed_tick_envelope_v1"
TITLE = (
    "CommittedTickEnvelopeV1 binds every mandatory tick output to exact "
    "whole-payload retry equality before PostgreSQL activation"
)


def _mapping(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_adr243_binds_complete_payload_and_exact_exclusions() -> None:
    adr_path = DECISIONS / f"{ADR_STEM}.yaml"
    decision = _mapping(adr_path)[ADR_STEM]
    index = _mapping(DECISIONS / "index.yaml")

    assert decision["status"] == "accepted"
    assert decision["issue"] == "PER-20"
    assert decision["title"] == TITLE
    assert decision["owners"]["tick_content_identity"] == "babylon-kernel"
    assert decision["canonical_contract"] == {
        "schema": "contracts/committed_tick_envelope_v1.yaml",
        "vectors": "contracts/committed_tick_envelope_v1_vectors.jsonl",
        "independent_verifier": "tools/verify_committed_tick_envelope_v1.py",
    }
    normalized = " ".join(decision["decision"].split())
    for text in (
        "eight mandatory sections",
        "strictly ascending",
        "536,871,121 bytes",
        "exact equality of every canonical envelope byte",
        "creates no semantic row codec, PostgreSQL DDL, database I/O",
        "changes no material mechanic, BSL primitive, or player-facing behavior",
    ):
        assert text in normalized

    assert index["meta"]["version"] == "1.87.0"
    assert index["decisions"][ADR_STEM] == {
        "title": TITLE,
        "status": "accepted",
        "date": "2026-08-27",
        "file": adr_path.name,
    }


def test_historical_envelope_boundary_is_superseded_by_the_one_way_cutover() -> None:
    contract = _mapping(ROOT / "contracts" / "committed_tick_envelope_v1.yaml")
    design = (
        ROOT
        / "docs"
        / "superpowers"
        / "specs"
        / "2026-08-27-per-20-committed-tick-envelope-v1-design.md"
    ).read_text(encoding="utf-8")
    writer_gate = ROOT / "rust" / "crates" / "babylon-persistence" / "src" / "writer_gate.rs"
    persistence = ROOT / "rust" / "crates" / "babylon-persistence" / "src"
    runtime = (persistence / "runtime.rs").read_text(encoding="utf-8")
    live_envelope = (persistence / "committed_tick_envelope.rs").read_text(encoding="utf-8")

    assert [row["name"] for row in contract["row_families"]] == [
        "graph",
        "state",
        "event",
        "checkpoint",
        "archive_dirty_receipt",
    ]
    assert "This slice adds no semantic state" in design
    assert not writer_gate.exists()
    assert "activate_rust_persistence_v2" in runtime
    assert "DurableReplayRuntimeV2" in runtime
    assert "CommittedTickEnvelopeV2" in runtime
    assert "activate_rust_persistence_v1" not in runtime
    assert "CommittedTickEnvelopeV1" not in runtime
    assert "CommittedTickEnvelopeV1" not in live_envelope
    assert "babylon.committed-tick-envelope.v1" not in live_envelope
