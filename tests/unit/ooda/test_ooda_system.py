"""Tests for OODASystem orchestrator (Feature 032).

Verifies three-phase orchestration, system registration, and naming.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from babylon.config.defines import GameDefines
from babylon.engine.context import TickContext
from babylon.engine.systems.ooda import OODASystem
from babylon.models.enums import ActionType, EdgeType, EventType, OrgType
from babylon.ooda.types import Action, ActionResult
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


class TestThreePhaseOrchestration:
    """Verify Layer 0 → Action Phase → Layer 3 execution."""

    def test_layer0_processes_business(self) -> None:
        """Business orgs are handled in Layer 0."""
        system = OODASystem()
        graph = _make_graph_with_orgs()
        services = _make_services()
        context = TickContext(tick=1)
        system.step(graph, services, context)

        # Event bus should have been called at least once
        assert services.event_bus.publish.called

    def test_action_phase_processes_non_business(self) -> None:
        """Non-Business orgs get NPC actions in action phase."""
        system = OODASystem()
        graph = _make_graph_with_orgs()
        services = _make_services()
        context = TickContext(tick=1)
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
        context = TickContext(tick=0)
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
    def _player_context(action_type: str) -> TickContext:
        return TickContext(
            tick=1,
            persistent_data={
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
        )

    def _results_for(self, context: TickContext) -> list[dict]:
        resolution = context.persistent_data["turn_resolution"]
        return [
            r for r in resolution["action_phase_results"] if r["action"]["org_id"] == "rev_workers"
        ]

    def test_turn_resolution_published(self) -> None:
        system = OODASystem()
        graph = _make_graph_with_orgs()
        services = _make_services()
        context = self._player_context("educate")
        system.step(graph, services, context)

        assert "turn_resolution" in context.persistent_data
        resolution = context.persistent_data["turn_resolution"]
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


class TestFirstClassReactionaryVerbPublish:
    """spec-116 FR-116-4.7: POGROM/LOCKOUT/VIGILANTISM ActionResults publish
    their own first-class bus events (payload = org/target + direct_effects);
    the per-tick ORGANIZATIONAL_ACTION summary is unchanged. Uses the
    documented ``_resolve_for_organization`` spy seam — the verbs have no
    NPC/player route yet, so resolution is patched in."""

    @staticmethod
    def _graph_single_faction() -> BabylonGraph:
        graph = BabylonGraph()
        graph.add_node(
            "fash_org",
            _node_type="organization",
            org_type=OrgType.POLITICAL_FACTION.value,
            territory_ids=["detroit"],
            ooda_profile={"action_points": 3, "decision_mode": "autocratic"},
        )
        graph.add_node("detroit", _node_type="territory")
        return graph

    @staticmethod
    def _verb_result(action_type: ActionType, event_value: str, effects: dict) -> ActionResult:
        return ActionResult(
            action=Action(org_id="fash_org", action_type=action_type, target_id="C900"),
            success=True,
            direct_effects=effects,
            events_generated=[event_value],
        )

    @staticmethod
    def _published(services: MagicMock) -> list:
        return [c.args[0] for c in services.event_bus.publish.call_args_list]

    def test_pogrom_result_publishes_first_class_event(self) -> None:
        system = OODASystem()
        services = _make_services()
        result = self._verb_result(
            ActionType.POGROM,
            EventType.POGROM.value,
            {"repression_increment": 0.15, "wealth_destroyed": 12.5},
        )
        with patch.object(OODASystem, "_resolve_for_organization", return_value=[result]):
            system.step(self._graph_single_faction(), services, TickContext(tick=3))

        pogroms = [e for e in self._published(services) if e.type == EventType.POGROM]
        assert len(pogroms) == 1
        assert pogroms[0].tick == 3
        assert pogroms[0].payload == {
            "org_id": "fash_org",
            "target_id": "C900",
            "repression_increment": 0.15,
            "wealth_destroyed": 12.5,
        }

    def test_lockout_and_vigilantism_publish(self) -> None:
        system = OODASystem()
        services = _make_services()
        results = [
            self._verb_result(
                ActionType.LOCKOUT, EventType.LOCKOUT.value, {"wage_attenuation": 0.3}
            ),
            self._verb_result(
                ActionType.VIGILANTISM,
                EventType.VIGILANTISM.value,
                {"repression_increment": 0.1},
            ),
        ]
        with patch.object(OODASystem, "_resolve_for_organization", return_value=results):
            system.step(self._graph_single_faction(), services, TickContext(tick=4))

        types = [e.type for e in self._published(services)]
        assert types.count(EventType.LOCKOUT) == 1
        assert types.count(EventType.VIGILANTISM) == 1

    def test_summary_unchanged_and_plain_actions_stay_summary_only(self) -> None:
        system = OODASystem()
        services = _make_services()
        plain = ActionResult(
            action=Action(org_id="fash_org", action_type=ActionType.EDUCATE, target_id="C900"),
            success=True,
            events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
        )
        with patch.object(OODASystem, "_resolve_for_organization", return_value=[plain]):
            system.step(self._graph_single_faction(), services, TickContext(tick=5))

        published = self._published(services)
        summaries = [e for e in published if e.type == EventType.ORGANIZATIONAL_ACTION]
        assert len(summaries) == 1
        assert summaries[0].payload["action_count"] == 1
        assert not any(
            e.type in {EventType.POGROM, EventType.LOCKOUT, EventType.VIGILANTISM}
            for e in published
        )


class TestStateRepressionFirstClassPublish:
    """Adversary-train W1: STATE_REPRESSION/STATE_SURVEILLANCE join the
    first-class publish gate (spec-116 FR-116-4.7's pattern extended) --
    before this, the type only ever lived as a string in
    ``ActionResult.events_generated`` (see ``_resolve_for_organization``'s
    old blind wrap and ``_resolve_repressive``'s pre-W1 dead tag), so the
    bus never carried it and ``event_builders.EVENT_BUILDERS``'
    ``StateRepressionEvent``/``StateSurveillanceEvent`` builders were idle.
    Uses the same ``_resolve_for_organization`` spy seam as
    ``TestFirstClassReactionaryVerbPublish`` -- this class tests the PUBLISH
    wiring in isolation from NPC target selection.
    """

    @staticmethod
    def _graph_single_state_org() -> BabylonGraph:
        graph = BabylonGraph()
        graph.add_node(
            "state_org",
            _node_type="organization",
            org_type=OrgType.STATE_APPARATUS.value,
            territory_ids=["detroit"],
            ooda_profile={"action_points": 3, "decision_mode": "autocratic"},
        )
        graph.add_node("detroit", _node_type="territory")
        return graph

    @staticmethod
    def _published(services: MagicMock) -> list:
        return [c.args[0] for c in services.event_bus.publish.call_args_list]

    def test_state_repression_result_publishes_first_class_event(self) -> None:
        system = OODASystem()
        services = _make_services()
        result = ActionResult(
            action=Action(org_id="state_org", action_type=ActionType.REPRESS, target_id="C900"),
            success=True,
            direct_effects={"backfire_delta": 0.04, "repression_increment": 0.15},
            events_generated=[EventType.STATE_REPRESSION.value],
        )
        with patch.object(OODASystem, "_resolve_for_organization", return_value=[result]):
            system.step(self._graph_single_state_org(), services, TickContext(tick=6))

        published = [e for e in self._published(services) if e.type == EventType.STATE_REPRESSION]
        assert len(published) == 1
        assert published[0].tick == 6
        assert published[0].payload == {
            "org_id": "state_org",
            "target_id": "C900",
            "backfire_delta": 0.04,
            "repression_increment": 0.15,
        }

    def test_state_surveillance_result_publishes_first_class_event(self) -> None:
        system = OODASystem()
        services = _make_services()
        result = ActionResult(
            action=Action(org_id="state_org", action_type=ActionType.SURVEIL, target_id="C900"),
            success=True,
            direct_effects={"backfire_delta": 0.01},
            events_generated=[EventType.STATE_SURVEILLANCE.value],
        )
        with patch.object(OODASystem, "_resolve_for_organization", return_value=[result]):
            system.step(self._graph_single_state_org(), services, TickContext(tick=7))

        published = [e for e in self._published(services) if e.type == EventType.STATE_SURVEILLANCE]
        assert len(published) == 1
        assert published[0].payload["org_id"] == "state_org"
        assert published[0].payload["target_id"] == "C900"


class TestNpcDriverGetsMaterialRepressionEffect:
    """Adversary-train W1: closes the player/NPC asymmetry the design doc
    names -- the NPC-selected REPRESS/SURVEIL (``select_npc_actions``, the
    RuleBasedStateAI / legacy-priority-queue driver) must now flow through
    the SAME ``resolve_action`` machinery the player-verb dispatcher's
    registered resolvers use, not the old blind ``success=True`` wrap. No
    ``_resolve_for_organization`` patching here -- exercises the REAL NPC
    dispatch path end to end.
    """

    @staticmethod
    def _graph_state_org_and_target() -> BabylonGraph:
        graph = BabylonGraph()
        graph.add_node(
            "state_org",
            _node_type="organization",
            org_type=OrgType.STATE_APPARATUS.value,
            territory_ids=["target_class"],
            ooda_profile={"action_points": 5, "decision_mode": "autocratic"},
        )
        # No faction_balance -- falls through to the legacy priority queue,
        # whose first STATE_APPARATUS priority is SURVEIL (npc_stub.py's
        # _NPC_PRIORITIES), targeting territory_ids[0].
        graph.add_node("target_class", _node_type="social_class", repression_faced=0.2)
        return graph

    def test_legacy_priority_queue_surveil_bumps_repression_faced(self) -> None:
        system = OODASystem()
        graph = self._graph_state_org_and_target()
        services = _make_services()

        system.step(graph, services, TickContext(tick=1))

        node = graph.get_node("target_class")
        assert node.attributes["repression_faced"] > 0.2, (
            "the NPC-selected SURVEIL must bump repression_faced on its "
            "target the SAME way a player-issued REPRESS/SURVEIL does"
        )

    def test_legacy_priority_queue_surveil_stamps_repression_edge(self) -> None:
        system = OODASystem()
        graph = self._graph_state_org_and_target()
        services = _make_services()

        system.step(graph, services, TickContext(tick=1))

        edge = graph.get_edge("state_org", "target_class", EdgeType.REPRESSION.value)
        assert edge is not None

    def test_legacy_priority_queue_surveil_publishes_state_surveillance(self) -> None:
        system = OODASystem()
        graph = self._graph_state_org_and_target()
        services = _make_services()

        system.step(graph, services, TickContext(tick=1))

        published = [
            c.args[0]
            for c in services.event_bus.publish.call_args_list
            if c.args[0].type == EventType.STATE_SURVEILLANCE
        ]
        assert len(published) == 1
        assert published[0].payload["org_id"] == "state_org"
        assert published[0].payload["target_id"] == "target_class"

    def test_other_npc_verbs_still_use_the_plain_summary_wrap(self) -> None:
        """Control: a political_faction NPC (no materially-resolved verb in
        its priority queue) is untouched by this unit -- its actions still
        carry the pre-W1 blind ActionResult (no direct_effects)."""
        system = OODASystem()
        graph = BabylonGraph()
        graph.add_node(
            "rev_workers",
            _node_type="organization",
            org_type=OrgType.POLITICAL_FACTION.value,
            territory_ids=["detroit"],
            consciousness_tendency="revolutionary",
            ooda_profile={"action_points": 4, "decision_mode": "autocratic"},
        )
        graph.add_node("detroit", _node_type="territory")
        services = _make_services()
        context = TickContext(tick=1)

        system.step(graph, services, context)

        results = context.persistent_data["turn_resolution"]["action_phase_results"]
        rev_workers_results = [r for r in results if r["action"]["org_id"] == "rev_workers"]
        assert rev_workers_results, "rev_workers must have acted this tick"
        for result in rev_workers_results:
            assert result["direct_effects"] == {}
            assert result["events_generated"] == [EventType.ORGANIZATIONAL_ACTION.value]
