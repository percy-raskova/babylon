"""Tests for OODASystem orchestrator (Feature 032).

Verifies three-phase orchestration, system registration, and naming.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from babylon.config.defines import GameDefines
from babylon.engine.systems.ooda import OODASystem
from babylon.models.enums import OrgType
from babylon.topology.graph import BabylonGraph


def _make_services() -> MagicMock:
    """Create a mock ServiceContainer with real defines."""
    services = MagicMock()
    services.defines = GameDefines()
    services.event_bus = MagicMock()
    return services


def _make_graph_with_orgs() -> BabylonGraph:
    """Create a graph with a mix of org types."""
    graph = BabylonGraph()

    # Business org
    graph.add_node(
        "ford",
        _node_type="organization",
        org_type=OrgType.BUSINESS.value,
        territory_ids=["detroit"],
        ooda_profile={"action_points": 3, "decision_mode": "autocratic"},
    )

    # Political faction
    graph.add_node(
        "rev_workers",
        _node_type="organization",
        org_type=OrgType.POLITICAL_FACTION.value,
        territory_ids=["detroit"],
        consciousness_tendency="revolutionary",
        ooda_profile={"action_points": 4, "decision_mode": "autocratic"},
    )

    # State apparatus
    graph.add_node(
        "fbi",
        _node_type="organization",
        org_type=OrgType.STATE_APPARATUS.value,
        territory_ids=["detroit"],
        jurisdiction="national",
        ooda_profile={"action_points": 5, "decision_mode": "autocratic"},
    )

    # Territory node (not an org)
    graph.add_node("detroit", _node_type="territory")

    return graph


class TestOODASystemProperties:
    """System name and protocol conformance."""

    def test_name(self) -> None:
        system = OODASystem()
        assert system.name == "ooda"

    def test_step_accepts_dict_context(self) -> None:
        system = OODASystem()
        graph = _make_graph_with_orgs()
        services = _make_services()
        context = {"tick": 0}
        # Should not raise
        system.step(graph, services, context)


class TestThreePhaseOrchestration:
    """Verify Layer 0 → Action Phase → Layer 3 execution."""

    def test_layer0_processes_business(self) -> None:
        """Business orgs are handled in Layer 0."""
        system = OODASystem()
        graph = _make_graph_with_orgs()
        services = _make_services()
        context = {"tick": 1}
        system.step(graph, services, context)

        # Event bus should have been called at least once
        assert services.event_bus.publish.called

    def test_action_phase_processes_non_business(self) -> None:
        """Non-Business orgs get NPC actions in action phase."""
        system = OODASystem()
        graph = _make_graph_with_orgs()
        services = _make_services()
        context = {"tick": 1}
        system.step(graph, services, context)

        # Verify event was published with action counts
        call_args = services.event_bus.publish.call_args
        event = call_args[0][0]
        assert event.payload["org_count"] >= 1

    def test_empty_graph_no_error(self) -> None:
        """Empty graph should not crash."""
        system = OODASystem()
        graph = BabylonGraph()
        services = _make_services()
        context = {"tick": 0}
        system.step(graph, services, context)


class TestSystemRegistration:
    """Verify OODASystem is registered in simulation engine."""

    def test_registered_in_default_systems(self) -> None:
        from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS

        system_names = [s.name for s in _DEFAULT_SYSTEMS]
        assert "ooda" in system_names

    def test_registered_between_metabolism_and_survival(self) -> None:
        """Spec 056 (F6=α) reordered OODASystem from last (after
        edge_transition) to position 14 — between MetabolismSystem
        and SurvivalSystem — so the engine's actual execution order
        matches ADR032's documented Material Base → Action Phase →
        Consequences partition.

        Pre-spec-056 contract was ``ooda_idx > edge_idx`` (OODA last).
        Post-spec-056 contract is ``metabolism_idx < ooda_idx <
        survival_idx`` (OODA between Material Base and Consequences).
        """
        from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS

        system_names = [s.name for s in _DEFAULT_SYSTEMS]
        metabolism_idx = system_names.index("Metabolism")
        ooda_idx = system_names.index("ooda")
        survival_idx = system_names.index("Survival Calculus")
        assert metabolism_idx < ooda_idx < survival_idx, (
            f"OODA must run between Material Base (Metabolism, idx "
            f"{metabolism_idx}) and Consequences (Survival, idx "
            f"{survival_idx}); got OODA at idx {ooda_idx}"
        )


class TestPlayerActionDispatch:
    """Verb-dispatch engine: player actions route through the resolver registry
    (real effects + loud failure) instead of the old blind ``success=True`` wrap,
    and the turn resolution is published to context.persistent_data.
    """

    @staticmethod
    def _player_context(action_type: str) -> dict:
        return {
            "tick": 1,
            "persistent_data": {
                "player_actions": {
                    "rev_workers": [
                        {
                            "action_type": action_type,
                            "target_id": "detroit",
                            "org_id": "rev_workers",
                            "params": {},
                        }
                    ]
                }
            },
        }

    def _results_for(self, context: dict) -> list[dict]:
        resolution = context["persistent_data"]["turn_resolution"]
        return [
            r for r in resolution["action_phase_results"] if r["action"]["org_id"] == "rev_workers"
        ]

    def test_turn_resolution_published(self) -> None:
        system = OODASystem()
        graph = _make_graph_with_orgs()
        services = _make_services()
        context = self._player_context("educate")
        system.step(graph, services, context)

        assert "turn_resolution" in context["persistent_data"]
        resolution = context["persistent_data"]["turn_resolution"]
        assert resolution["action_phase_results"]

    def test_known_verb_dispatches_to_resolver(self) -> None:
        """EDUCATE routes through resolve_educate — success with the right action."""
        system = OODASystem()
        graph = _make_graph_with_orgs()
        services = _make_services()
        context = self._player_context("educate")
        system.step(graph, services, context)

        results = self._results_for(context)
        assert len(results) == 1
        assert results[0]["action"]["action_type"] == "educate"
        assert results[0]["success"] is True

    def test_unregistered_verb_fails_loud_not_blind(self) -> None:
        """A verb with no resolver (FUNDRAISE) is a loud failure — the OLD
        blind wrap would have reported ``success=True``."""
        system = OODASystem()
        graph = _make_graph_with_orgs()
        services = _make_services()
        context = self._player_context("fundraise")
        system.step(graph, services, context)

        results = self._results_for(context)
        assert len(results) == 1
        assert results[0]["success"] is False
        assert results[0]["failure_reason"] is not None

    def test_tick_context_variant(self) -> None:
        """Publication works with a TickContext (not just a dict)."""
        from babylon.engine.context import TickContext

        system = OODASystem()
        graph = _make_graph_with_orgs()
        services = _make_services()
        context = TickContext(
            tick=1,
            persistent_data={
                "player_actions": {
                    "rev_workers": [
                        {
                            "action_type": "educate",
                            "target_id": "detroit",
                            "org_id": "rev_workers",
                            "params": {},
                        }
                    ]
                }
            },
        )
        system.step(graph, services, context)
        assert "turn_resolution" in context.persistent_data
        assert context.persistent_data["turn_resolution"]["action_phase_results"]
