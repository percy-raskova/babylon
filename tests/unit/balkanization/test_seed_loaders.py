"""Spec-070 seed loader tests (T030 + T029 SOV_EXTERIOR_NULL coverage)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from babylon.data.game.balkanization import (
    load_seed_factions,
    load_seed_influences,
    load_seed_sovereigns,
    load_seed_sovereigns_raw,
)
from babylon.models.enums import ColonialStance, ExtractionPolicy, SovereigntyType

pytestmark = pytest.mark.unit


def test_load_seed_factions_returns_four_canonical_factions() -> None:
    factions = load_seed_factions()
    assert len(factions) == 4
    ids = {f.id for f in factions}
    assert ids == {
        "FAC_RESTORATIONIST",
        "FAC_WORKERS_CONGRESS",
        "FAC_DECOLONIAL",
        "FAC_LIBERAL_IMPERIAL",
    }


def test_seed_factions_have_documented_stances() -> None:
    by_id = {f.id: f for f in load_seed_factions()}
    assert by_id["FAC_RESTORATIONIST"].colonial_stance is ColonialStance.UPHOLD
    assert by_id["FAC_WORKERS_CONGRESS"].colonial_stance is ColonialStance.IGNORE
    assert by_id["FAC_DECOLONIAL"].colonial_stance is ColonialStance.ABOLISH
    assert by_id["FAC_LIBERAL_IMPERIAL"].colonial_stance is ColonialStance.IGNORE


def test_seed_factions_settler_formation_is_consistent_with_stance() -> None:
    by_id = {f.id: f for f in load_seed_factions()}
    # UPHOLD + IGNORE factions are settler formations; ABOLISH is not.
    assert by_id["FAC_RESTORATIONIST"].is_settler_formation is True
    assert by_id["FAC_WORKERS_CONGRESS"].is_settler_formation is True
    assert by_id["FAC_LIBERAL_IMPERIAL"].is_settler_formation is True
    assert by_id["FAC_DECOLONIAL"].is_settler_formation is False


def test_load_seed_sovereigns_returns_three_canonical_sovereigns() -> None:
    sovereigns = load_seed_sovereigns()
    assert len(sovereigns) == 3
    ids = {s.id for s in sovereigns}
    assert ids == {"SOV_USA_FED", "SOV_CAN_FED", "SOV_EXTERIOR_NULL"}


def test_sov_usa_fed_hard_start_at_intensify() -> None:
    """FR-040: SOV_USA_FED hard-starts ruled by FAC_RESTORATIONIST
    with INTENSIFY extraction (per spec clarification Q5)."""

    by_id = {s.id: s for s in load_seed_sovereigns()}
    usa = by_id["SOV_USA_FED"]
    assert usa.ruling_faction_id == "FAC_RESTORATIONIST"
    assert usa.extraction_policy is ExtractionPolicy.INTENSIFY
    assert usa.legitimacy == 1.0


def test_sov_can_fed_per_fr_040a() -> None:
    """FR-040a + IV.1 Detroit-Windsor: SOV_CAN_FED ruled by
    FAC_LIBERAL_IMPERIAL."""

    by_id = {s.id: s for s in load_seed_sovereigns()}
    can = by_id["SOV_CAN_FED"]
    assert can.ruling_faction_id == "FAC_LIBERAL_IMPERIAL"
    assert can.extraction_policy is ExtractionPolicy.CONTINUE


def test_sov_exterior_null_per_fr_040b() -> None:
    """FR-040b: SOV_EXTERIOR_NULL has ruling_faction_id=None paired
    with extraction_policy=CONTINUE, sovereignty_type=PROVISIONAL,
    legitimacy=0.0."""

    by_id = {s.id: s for s in load_seed_sovereigns()}
    null_sov = by_id["SOV_EXTERIOR_NULL"]
    assert null_sov.ruling_faction_id is None
    assert null_sov.extraction_policy is ExtractionPolicy.CONTINUE
    assert null_sov.sovereignty_type is SovereigntyType.PROVISIONAL
    assert null_sov.legitimacy == 0.0


def test_raw_loader_preserves_initial_claims() -> None:
    """The db-init pipeline needs ``initial_claims`` arrays which the
    Pydantic Sovereign model intentionally omits. ``load_seed_sovereigns_raw``
    exposes them."""

    raw = load_seed_sovereigns_raw()
    by_id = {record["id"]: record for record in raw}
    can = by_id["SOV_CAN_FED"]
    null_sov = by_id["SOV_EXTERIOR_NULL"]
    assert any(claim["territory_id"] == "canada" for claim in can["initial_claims"])
    assert any(claim["territory_id"] == "rest_of_usa" for claim in null_sov["initial_claims"])


def test_load_seed_influences_absent_returns_empty(tmp_path: Path) -> None:
    """The proxy-data influences seed is optional at load time."""

    assert load_seed_influences(tmp_path / "missing.json") == []


def test_load_seed_influences_reads_present_file(tmp_path: Path) -> None:
    target = tmp_path / "seed_influences.json"
    payload = {
        "version": "1.0.0",
        "influences": [
            {
                "faction_id": "FAC_DECOLONIAL",
                "territory_id": "HEX_001",
                "influence_level": 0.4,
                "support_type": "ideological",
            }
        ],
    }
    target.write_text(json.dumps(payload))
    rows = load_seed_influences(target)
    assert len(rows) == 1
    assert rows[0]["faction_id"] == "FAC_DECOLONIAL"
