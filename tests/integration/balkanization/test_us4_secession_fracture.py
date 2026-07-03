"""Spec-070 US4 secession + civil war + O(1) fracture integration tests
(T081, FR-027, FR-028, FR-029a, SC-004).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from babylon.engine.graph import BabylonGraph
from babylon.engine.systems.collapse_transition import CollapseTransitionSystem
from babylon.models.enums import EventType

pytestmark = pytest.mark.integration


@dataclass
class _CapturedEvent:
    type: Any
    tick: int
    payload: dict[str, Any]


class _RecordingEventBus:
    def __init__(self) -> None:
        self.events: list[_CapturedEvent] = []

    def publish(self, event: Any) -> None:
        self.events.append(_CapturedEvent(type=event.type, tick=event.tick, payload=event.payload))


@pytest.fixture
def services() -> Any:
    container = MagicMock()
    container.event_bus = _RecordingEventBus()
    return container


def _events_of(bus: _RecordingEventBus, ev: Any) -> list[_CapturedEvent]:
    return [e for e in bus.events if e.type is ev]


def _build_parent_with_n_claims(adapter: BabylonGraph, n: int) -> str:
    adapter.add_node(
        "SOV_USA_FED",
        "sovereign",
        sovereignty_type="recognized_state",
        legitimacy=1.0,
        color_hex="#3c3b6e",
        ruling_faction_id="FAC_RESTORATIONIST",
        extraction_policy="intensify",
        founded_tick=0,
    )
    adapter.add_node(
        "FAC_DECOLONIAL",
        "balkanization_faction",
        colonial_stance="abolish",
        class_reduction=0.5,
    )
    for i in range(n):
        territory_id = f"HEX_{i:05d}"
        adapter.add_node(territory_id, "territory")
        adapter.add_edge(
            "SOV_USA_FED",
            territory_id,
            "claims",
            control_level=1.0,
            legal_status="de_jure",
            fiscal_status="taxed",
            recognition_level=1.0,
            claimed_since_tick=0,
        )
    return "SOV_USA_FED"


def test_secession_creates_new_sovereign_via_bulk_partition(services: Any) -> None:
    """FR-027 / FR-028: a secession-eligible (faction, sovereign) pair
    produces a new breakaway Sovereign holding the contiguous Territory
    subregion via the O(K) bulk-partition operation."""

    adapter = BabylonGraph()
    _build_parent_with_n_claims(adapter, 100)
    seceding = {f"HEX_{i:05d}" for i in range(30)}
    context: dict[str, Any] = {
        "tick": 15,
        "persistent_data": {
            "balkanization.secession_eligible": [
                {
                    "secessionist_faction_id": "FAC_DECOLONIAL",
                    "parent_sovereign_id": "SOV_USA_FED",
                    "contiguous_territory_ids": tuple(sorted(seceding)),
                }
            ],
        },
    }

    CollapseTransitionSystem().step(adapter, services, context)

    # Parent retains the OTHER 70 territories.
    parent_claims = {t for t, _, _ in adapter.query_sovereign_claims("SOV_USA_FED")}
    assert len(parent_claims) == 70
    assert parent_claims.isdisjoint(seceding)

    # A new breakaway Sovereign holds the 30 seceding territories.
    sovereign_ids = {n.id for n in adapter.query_nodes(node_type="sovereign")}
    breakaway = [s for s in sovereign_ids if s.startswith("SOV_BREAK_")]
    assert len(breakaway) == 1
    new_claims = {t for t, _, _ in adapter.query_sovereign_claims(breakaway[0])}
    assert new_claims == seceding


def test_civil_war_declared_event_emitted_with_contested_count(
    services: Any,
) -> None:
    adapter = BabylonGraph()
    _build_parent_with_n_claims(adapter, 50)
    seceding = {f"HEX_{i:05d}" for i in range(20)}
    context: dict[str, Any] = {
        "tick": 8,
        "persistent_data": {
            "balkanization.secession_eligible": [
                {
                    "secessionist_faction_id": "FAC_DECOLONIAL",
                    "parent_sovereign_id": "SOV_USA_FED",
                    "contiguous_territory_ids": tuple(sorted(seceding)),
                }
            ],
        },
    }

    CollapseTransitionSystem().step(adapter, services, context)

    civil_wars = _events_of(services.event_bus, EventType.CIVIL_WAR_DECLARED)
    assert len(civil_wars) == 1
    payload = civil_wars[0].payload
    assert payload["parent_sovereign_id"] == "SOV_USA_FED"
    assert payload["secessionist_faction_id"] == "FAC_DECOLONIAL"
    assert payload["contested_territory_count"] == 20


def test_orphaned_sovereign_pruned_when_all_territories_secede(
    services: Any,
) -> None:
    """Edge case from spec: when the secessionist holds 100% of the
    parent's territories, the parent becomes orphaned and is deleted in
    the same tick."""

    adapter = BabylonGraph()
    _build_parent_with_n_claims(adapter, 5)
    seceding = {f"HEX_{i:05d}" for i in range(5)}  # All of them.
    context: dict[str, Any] = {
        "tick": 1,
        "persistent_data": {
            "balkanization.secession_eligible": [
                {
                    "secessionist_faction_id": "FAC_DECOLONIAL",
                    "parent_sovereign_id": "SOV_USA_FED",
                    "contiguous_territory_ids": tuple(sorted(seceding)),
                }
            ],
        },
    }

    CollapseTransitionSystem().step(adapter, services, context)

    sovereign_ids = {n.id for n in adapter.query_nodes(node_type="sovereign")}
    assert "SOV_USA_FED" not in sovereign_ids
    breakaway = [s for s in sovereign_ids if s.startswith("SOV_BREAK_")]
    assert len(breakaway) == 1


def test_sov_exterior_null_never_orphan_pruned(services: Any) -> None:
    """SOV_EXTERIOR_NULL is the documented fallback Sovereign and must
    survive orphan-cleanup passes."""

    adapter = BabylonGraph()
    adapter.add_node(
        "SOV_EXTERIOR_NULL",
        "sovereign",
        sovereignty_type="provisional",
        legitimacy=0.0,
        color_hex="#404040",
        ruling_faction_id=None,
        extraction_policy="continue",
        founded_tick=0,
    )
    context: dict[str, Any] = {"tick": 5, "persistent_data": {}}

    CollapseTransitionSystem().step(adapter, services, context)

    assert adapter.get_node("SOV_EXTERIOR_NULL") is not None


def test_collapse_with_winning_factions_creates_successor_sovereigns(
    services: Any,
) -> None:
    """FR-024 step 4: a collapsing Sovereign's territories partition
    among the per-Territory winning Factions; each Faction inherits its
    share as a new Sovereign at control_level = 0.8 + legal_status =
    DE_FACTO."""

    adapter = BabylonGraph()
    adapter.add_node(
        "SOV_OLD",
        "sovereign",
        sovereignty_type="recognized_state",
        legitimacy=0.0,  # Collapse trigger.
        color_hex="#3c3b6e",
        ruling_faction_id="FAC_RESTORATIONIST",
        extraction_policy="intensify",
        founded_tick=0,
    )
    for fac, stance in [
        ("FAC_DECOLONIAL", "abolish"),
        ("FAC_WORKERS_CONGRESS", "ignore"),
    ]:
        adapter.add_node(
            fac,
            "balkanization_faction",
            colonial_stance=stance,
            class_reduction=0.5,
        )
    for i in range(4):
        territory_id = f"HEX_{i:03d}"
        adapter.add_node(territory_id, "territory")
        adapter.add_edge(
            "SOV_OLD",
            territory_id,
            "claims",
            control_level=1.0,
            legal_status="de_jure",
            fiscal_status="taxed",
            recognition_level=1.0,
            claimed_since_tick=0,
        )
    # Pre-computed winning Faction per Territory (would normally come
    # from FactionInfluenceSystem).
    winning = {
        "HEX_000": "FAC_DECOLONIAL",
        "HEX_001": "FAC_DECOLONIAL",
        "HEX_002": "FAC_WORKERS_CONGRESS",
        "HEX_003": "FAC_WORKERS_CONGRESS",
    }
    context: dict[str, Any] = {
        "tick": 10,
        "persistent_data": {"balkanization.winning_faction_by_territory": winning},
    }

    CollapseTransitionSystem().step(adapter, services, context)

    sovereign_ids = {n.id for n in adapter.query_nodes(node_type="sovereign")}
    new_sovs = [s for s in sovereign_ids if s.startswith("SOV_AUTO_T10")]
    assert len(new_sovs) == 2
    # Each successor holds its Faction's share of territories.
    for sov in new_sovs:
        claims = adapter.query_sovereign_claims(sov)
        assert all(legal == "de_facto" for _t, _c, legal in claims)
        # control_level honors the defines default (0.8).
        assert all(ctrl == pytest.approx(0.8) for _t, ctrl, _l in claims)
