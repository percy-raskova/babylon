"""Spec-071: FascistFactionSystem unit tests.

The fascism branch of the George Jackson bifurcation. Verifies fascist pull
-> fascist_alignment drift -> fascist-faction capture, the StanceIntervention
hook (ADR051), and the dialectical_regime read.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.graph import BabylonGraph
from babylon.engine.systems.reactionary import FascistFactionSystem
from babylon.models.enums import EventType

pytestmark = pytest.mark.unit


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

    def get_history(self) -> list[_CapturedEvent]:
        return self.events


def _services() -> Any:
    container = MagicMock()
    container.event_bus = _RecordingEventBus()
    container.defines = GameDefines()
    container.rng = None
    return container


def _events_of(services: Any, event_type: EventType) -> list[_CapturedEvent]:
    return [e for e in services.event_bus.events if e.type == event_type]


def _add_la(
    g: BabylonGraph,
    node_id: str = "C001",
    *,
    agitation: float = 1.0,
    entitlement: float = 0.8,
    fascist_alignment: float = 0.0,
    aligned_faction_id: str | None = None,
) -> None:
    g.add_node(
        node_id,
        "social_class",
        role="labor_aristocracy",
        active=True,
        county_fips="26163",
        entitlement=entitlement,
        volatility=0.0,
        fascist_alignment=fascist_alignment,
        aligned_faction_id=aligned_faction_id,
        ideology={"class_consciousness": 0.1, "national_identity": 0.5, "agitation": agitation},
    )


def _add_fascist_faction(g: BabylonGraph, fid: str = "FAC_SETTLER") -> None:
    g.add_node(
        fid,
        "balkanization_faction",
        is_settler_formation=True,
        colonial_stance="uphold",
        ideology="settler-restorationism",
    )


class TestFascistDrift:
    def test_crisis_pull_drives_drift(self) -> None:
        g = BabylonGraph()
        _add_la(g, agitation=1.0, entitlement=0.8)  # pull = 1.0 * 0.8/0.1 = 8.0 > 1.0
        services = _services()
        FascistFactionSystem().step(g, services, {"tick": 5})
        node = g.get_node("C001")
        assert node is not None
        step = services.defines.reactionary.fascist_drift_step
        assert node.attributes["fascist_alignment"] == pytest.approx(step)
        assert len(_events_of(services, EventType.FASCIST_DRIFT)) == 1

    def test_hegemony_zero_agitation_no_drift(self) -> None:
        g = BabylonGraph()
        _add_la(g, agitation=0.0, entitlement=0.8)
        services = _services()
        FascistFactionSystem().step(g, services, {"tick": 5})
        assert g.get_node("C001").attributes["fascist_alignment"] == 0.0
        assert _events_of(services, EventType.FASCIST_DRIFT) == []

    def test_solidarity_suppresses_drift(self) -> None:
        g = BabylonGraph()
        _add_la(g, agitation=1.0, entitlement=0.8)
        # strong solidarity: pull = 1.0 * 0.8/(0.9+0.1) = 0.8 < 1.0 threshold
        g.add_node("C900", "social_class", role="periphery_proletariat", active=True)
        g.add_edge("C900", "C001", "solidarity", solidarity_strength=0.9)
        services = _services()
        FascistFactionSystem().step(g, services, {"tick": 5})
        assert g.get_node("C001").attributes["fascist_alignment"] == 0.0
        assert _events_of(services, EventType.FASCIST_DRIFT) == []

    def test_comprador_also_drifts(self) -> None:
        g = BabylonGraph()
        g.add_node(
            "C002",
            "social_class",
            role="comprador_bourgeoisie",
            active=True,
            entitlement=0.7,
            volatility=0.0,
            fascist_alignment=0.0,
            aligned_faction_id=None,
            ideology={"class_consciousness": 0.1, "national_identity": 0.5, "agitation": 1.0},
        )
        services = _services()
        FascistFactionSystem().step(g, services, {"tick": 5})
        assert g.get_node("C002").attributes["fascist_alignment"] > 0.0


class TestFascistCapture:
    def test_saturated_node_captured_by_fascist_faction(self) -> None:
        g = BabylonGraph()
        _add_la(g, agitation=0.0, fascist_alignment=1.0)  # already saturated
        _add_fascist_faction(g)
        services = _services()
        FascistFactionSystem().step(g, services, {"tick": 5})
        node = g.get_node("C001")
        assert node.attributes["aligned_faction_id"] == "FAC_SETTLER"
        assert len(_events_of(services, EventType.FASCIST_RECRUITMENT)) == 1

    def test_capture_is_idempotent(self) -> None:
        g = BabylonGraph()
        _add_la(g, agitation=0.0, fascist_alignment=1.0, aligned_faction_id="FAC_SETTLER")
        _add_fascist_faction(g)
        services = _services()
        FascistFactionSystem().step(g, services, {"tick": 5})
        assert _events_of(services, EventType.FASCIST_RECRUITMENT) == []

    def test_no_capture_without_fascist_faction(self) -> None:
        g = BabylonGraph()
        _add_la(g, agitation=0.0, fascist_alignment=1.0)  # saturated, but no faction
        services = _services()
        FascistFactionSystem().step(g, services, {"tick": 5})
        node = g.get_node("C001")
        assert node.attributes["aligned_faction_id"] is None
        assert _events_of(services, EventType.FASCIST_RECRUITMENT) == []


class TestStanceInterventionHook:
    def test_pull_writes_stance_intervention(self) -> None:
        g = BabylonGraph()
        _add_la(g, agitation=1.0, entitlement=0.8)
        # capital_labor opposition must be known for the intervention to be written.
        g.set_graph_attr("opposition_states", {"capital_labor": {"key": "capital_labor"}})
        services = _services()
        FascistFactionSystem().step(g, services, {"tick": 5})
        interventions = g.get_graph_attr("opposition_interventions", [])
        assert len(interventions) == 1
        assert interventions[0]["target_key"] == "capital_labor"
        assert interventions[0]["delta_balance"] > 0.0  # toward the capital/reactionary pole

    def test_no_intervention_when_opposition_absent(self) -> None:
        # No opposition_states -> no intervention written (no crash, no ValueError downstream).
        g = BabylonGraph()
        _add_la(g, agitation=1.0, entitlement=0.8)
        services = _services()
        FascistFactionSystem().step(g, services, {"tick": 5})
        assert g.get_graph_attr("opposition_interventions", []) == []


class TestRegimeRead:
    def test_reads_dialectical_regime_without_crash(self) -> None:
        g = BabylonGraph()
        _add_la(g, agitation=1.0, entitlement=0.8)
        g.set_graph_attr(
            "dialectical_regime", {"regime": "crisis", "opposition": "capital_labor", "rate": 0.2}
        )
        services = _services()
        FascistFactionSystem().step(g, services, {"tick": 5})
        drift = _events_of(services, EventType.FASCIST_DRIFT)
        assert len(drift) == 1
        assert drift[0].payload.get("regime") == "crisis"
