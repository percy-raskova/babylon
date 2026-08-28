"""Governance contract for PER-20 Migration 0004 and its typed storage map."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
DECISIONS = ROOT / "ai" / "decisions"
ADR_STEM = "ADR244_committed_tick_postgresql_storage_v1"
TITLE = (
    "Migration 0004 stores every CommittedTickEnvelopeV1 family in one exact "
    "schema-qualified PostgreSQL relation without activating Rust writes"
)
FAMILIES = (
    ("graph", 16, "babylon_state.tick_graph_row"),
    ("state", 17, "babylon_state.tick_state_row"),
    ("event", 18, "babylon_state.tick_event_row"),
    ("subsystem", 19, "babylon_state.tick_subsystem_row"),
    ("conservation", 20, "babylon_state.tick_conservation_row"),
    ("boundary_flow", 21, "babylon_state.tick_boundary_flow_row"),
    ("checkpoint", 22, "babylon_state.tick_checkpoint_row"),
    (
        "archive_dirty_receipt",
        23,
        "babylon_state.tick_archive_dirty_receipt_row",
    ),
)


def _mapping(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_adr244_binds_the_migration_mapping_and_closed_authority() -> None:
    adr_path = DECISIONS / f"{ADR_STEM}.yaml"
    decision = _mapping(adr_path)[ADR_STEM]
    index = _mapping(DECISIONS / "index.yaml")

    assert decision["status"] == "accepted"
    assert decision["issue"] == "PER-20"
    assert decision["title"] == TITLE
    assert decision["canonical_contract"] == {
        "schema": "contracts/committed_tick_storage_v1.yaml",
        "migration": ("rust/crates/babylon-persistence/migrations/0004_committed_tick_storage.sql"),
        "rust_mapping": ("rust/crates/babylon-persistence/src/committed_tick_storage.rs"),
    }
    normalized = " ".join(decision["decision"].split())
    for text in (
        "one explicit babylon_state relation for each of the eight",
        "permits the future atomic writer to insert tick_commit last",
        "cannot construct RustWriterAuthority",
        "Python remains the sole live writer and migrator",
    ):
        assert text in normalized
    assert index["decisions"][ADR_STEM] == {
        "title": TITLE,
        "status": "accepted",
        "date": "2026-08-27",
        "file": adr_path.name,
    }


def test_contract_pins_all_eight_relations_and_exact_migration_bytes() -> None:
    contract = _mapping(ROOT / "contracts" / "committed_tick_storage_v1.yaml")
    migration_path = ROOT / contract["migration"]["file"]
    migration = migration_path.read_bytes()
    actual_families = tuple(
        (row["family"], row["tag_u8"], row["relation"]) for row in contract["row_families"]
    )

    assert contract["migration"]["version"] == 4
    assert hashlib.sha256(migration).hexdigest() == contract["migration"]["sha256"]
    assert actual_families == FAMILIES
    assert contract["family_row_shape"]["primary_key"] == [
        "campaign_id",
        "resolve_tick",
        "row_key",
    ]
    assert contract["family_row_shape"]["marker_foreign_key"]["timing"] == (
        "DEFERRABLE_INITIALLY_DEFERRED"
    )
    assert "Runtime construction of RustWriterAuthority" in contract["excluded_authority"]
    for _, _, relation in FAMILIES:
        assert f"CREATE TABLE {relation} (".encode() in migration
