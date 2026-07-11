"""Spec-071: FascistFactionSystem unit tests.

The fascism branch of the George Jackson bifurcation. Verifies fascist pull
-> fascist_alignment drift -> fascist-faction capture, the StanceIntervention
hook (ADR051), and the dialectical_regime read.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.systems.reactionary import FascistFactionSystem
from babylon.models.enums import EdgeType, EventType
from babylon.topology.graph import BabylonGraph


class _AlwaysDefect(random.Random):
    """Deterministic RNG whose roll always succeeds (roll < any p_defect)."""

    def random(self) -> float:  # type: ignore[override]
        return 0.0


class _NeverDefect(random.Random):
    def random(self) -> float:  # type: ignore[override]
        return 1.0


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


def _add_org_with_la_members(
    g: BabylonGraph, org_id: str, member_ids: list[str], *, cadre_level: float = 0.0
) -> None:
    g.add_node(org_id, "organization", cadre_level=cadre_level)
    for mid in member_ids:
        g.add_node(
            mid,
            "social_class",
            role="labor_aristocracy",
            active=True,
            entitlement=0.8,
            fascist_alignment=0.0,
            aligned_faction_id=None,
            ideology={"class_consciousness": 0.1, "national_identity": 0.5, "agitation": 0.0},
        )
        g.add_edge(org_id, mid, "membership")


class TestChauvinism:
    def test_chauvinism_accrues_base_rate(self) -> None:
        g = BabylonGraph()
        _add_org_with_la_members(g, "ORG1", ["C001"])
        services = _services()
        FascistFactionSystem().step(g, services, {"tick": 5})
        edge = g.get_edge("ORG1", "C001", EdgeType.MEMBERSHIP)
        base = services.defines.reactionary.chauvinism_base_rate
        assert edge.attributes["chauvinism"] == pytest.approx(base)

    def test_superwage_adds_bonus(self) -> None:
        g = BabylonGraph()
        _add_org_with_la_members(g, "ORG1", ["C001"])
        # A WAGES edge with a positive super-wage bonus.
        g.add_node("C500", "social_class", role="core_bourgeoisie", active=True)
        g.add_edge("C500", "C001", "wages", super_wage_bonus=0.5)
        services = _services()
        FascistFactionSystem().step(g, services, {"tick": 5})
        edge = g.get_edge("ORG1", "C001", EdgeType.MEMBERSHIP)
        r = services.defines.reactionary
        assert edge.attributes["chauvinism"] == pytest.approx(
            r.chauvinism_base_rate + r.chauvinism_superwage_bonus
        )


class TestDefectionAndCoup:
    def _crisis_services(self, rng: random.Random) -> Any:
        services = _services()
        services.rng = rng
        services.event_bus.events.append(
            _CapturedEvent(type=EventType.ECONOMIC_CRISIS, tick=5, payload={})
        )
        return services

    def test_defection_fires_organizational_fracture(self) -> None:
        g = BabylonGraph()
        _add_org_with_la_members(g, "ORG1", ["C001"])
        # pre-load high chauvinism so p_defect is high
        g.update_edge("ORG1", "C001", EdgeType.MEMBERSHIP, chauvinism=0.99)
        services = self._crisis_services(_AlwaysDefect())
        FascistFactionSystem().step(g, services, {"tick": 5})
        assert len(_events_of(services, EventType.ORGANIZATIONAL_FRACTURE)) == 1

    def test_no_defection_without_crisis(self) -> None:
        g = BabylonGraph()
        _add_org_with_la_members(g, "ORG1", ["C001"])
        g.update_edge("ORG1", "C001", EdgeType.MEMBERSHIP, chauvinism=0.99)
        services = _services()
        services.rng = _AlwaysDefect()  # would defect IF crisis, but no crisis event
        FascistFactionSystem().step(g, services, {"tick": 5})
        assert _events_of(services, EventType.ORGANIZATIONAL_FRACTURE) == []

    def test_majority_defection_fires_red_brown_coup(self) -> None:
        g = BabylonGraph()
        _add_org_with_la_members(g, "ORG1", ["C001", "C002", "C003"])
        for mid in ("C001", "C002", "C003"):
            g.update_edge("ORG1", mid, EdgeType.MEMBERSHIP, chauvinism=0.99)
        services = self._crisis_services(_AlwaysDefect())
        FascistFactionSystem().step(g, services, {"tick": 5})
        assert len(_events_of(services, EventType.RED_BROWN_COUP)) == 1
        assert len(_events_of(services, EventType.ORGANIZATIONAL_FRACTURE)) == 3

    def test_no_coup_when_no_defections(self) -> None:
        g = BabylonGraph()
        _add_org_with_la_members(g, "ORG1", ["C001", "C002"])
        services = self._crisis_services(_NeverDefect())
        FascistFactionSystem().step(g, services, {"tick": 5})
        assert _events_of(services, EventType.RED_BROWN_COUP) == []

    def test_defection_is_deterministic(self) -> None:
        results = []
        for _ in range(2):
            g = BabylonGraph()
            _add_org_with_la_members(g, "ORG1", ["C001", "C002"])
            for mid in ("C001", "C002"):
                g.update_edge("ORG1", mid, EdgeType.MEMBERSHIP, chauvinism=0.6)
            services = self._crisis_services(random.Random(1234))
            FascistFactionSystem().step(g, services, {"tick": 5})
            results.append(len(_events_of(services, EventType.ORGANIZATIONAL_FRACTURE)))
        assert results[0] == results[1]


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
