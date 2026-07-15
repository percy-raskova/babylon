"""Proves Feature 039's RuleBasedStateAI actually executes in a real
wayne_county playthrough (AW3-R2 item 3 / epochs-vision-gap-audit.md §5
Wave 3 item 3), and (task #73) that it no longer self-targets.

Before this test, ``RuleBasedStateAI`` was real, tested-in-isolation code
that had *never once executed* inside any scenario: every entry point is
gated on an org attribute (``faction_balance``) that no scenario builder
ever set (see ``babylon.ooda.npc_stub._try_state_ai_dispatch``). wayne_county
now seeds one ``STATE_APPARATUS`` org ("Detroit Police Department",
``babylon.engine.scenarios._legacy_wayne._create_state_apparatus_org``)
with a real ``FactionBalance`` — this test drives the REAL scenario (no
mocking) through ``OODASystem`` for a few ticks and asserts the dispatch
fires: the seeded org's actions carry the RuleBasedStateAI signature
(``budget_cost > 0``), which the legacy static priority queue never sets
(``babylon.ooda.npc_stub.select_npc_actions`` — legacy ``Action`` objects
never pass ``budget_cost``, so it stays at the model default of 0.0).

Task #73 (Feature-039 remainder): until this fix, every dispatched action
had ``target_id=org_id`` (ORG002 REPRESSing itself) regardless of what
verb ``RuleBasedStateAI`` picked, because ``npc_stub._try_state_ai_
dispatch`` collapses every ``StateAction`` into a legacy
``ActionType.REPRESS`` (see its "Best-match legacy type" comment), and
``babylon.ooda.layer3._propagate_heat`` bumps ``heat`` on whatever
``target_id`` it's given. ``TestStateAINoLongerSelfTargets`` below proves
the fix: ORG002 now sorts non-state-org candidates by ``Heat x
Visibility`` (``babylon.ooda.state_ai.decision.select_repress_target``)
and targets the top one, or honestly no-ops when nothing is visible
(ORG001 starts at ``heat=0.0`` per ``_create_player_org`` — a fresh
scenario IS the "nothing visible yet" case, so several tests here seed a
believable nonzero heat on ORG001 first to exercise the "real threat"
branch; the no-op branch is proven separately against the untouched
scenario default).

Not one of the 5 qa:regression baseline scenarios (imperial_circuit,
two_node, starvation, glut, fascist_bifurcation — see
``tools/regression_test.py``'s ``_SCENARIO_REGISTRY``, both keyed to
``create_imperial_circuit_scenario``/``create_two_node_scenario``) touches
wayne_county, so this seeding is safe from that determinism gate.
"""

from __future__ import annotations

from typing import Any

from babylon.engine.scenarios_wayne_county import create_wayne_county_scenario
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.ooda import OODASystem
from babylon.models.enums import OrgType

# See _legacy_wayne._STATE_APPARATUS_ID / _PLAYER_ORG_ID.
_STATE_APPARATUS_ID = "ORG002"
_PLAYER_ORG_ID = "ORG001"


class TestWayneCountySeedsStateApparatus:
    """The scenario builder now creates a real STATE_APPARATUS org."""

    def test_seeded_org_is_state_apparatus_with_faction_balance(self) -> None:
        state, _config, _defines = create_wayne_county_scenario()

        org = state.organizations[_STATE_APPARATUS_ID]

        assert org.org_type == OrgType.STATE_APPARATUS
        assert org.faction_balance is not None
        assert org.rng_seed is not None

    def test_player_org_still_present_and_unchanged_id(self) -> None:
        """Adding the second org must not disturb ORG001 (the sole org every
        other wayne_county test/comment assumes — e.g.
        tests/integration/web/test_inspect_history.py's ``_WAYNE_PLAYER_ORG_ID``)."""
        state, _config, _defines = create_wayne_county_scenario()

        assert "ORG001" in state.organizations
        assert len(state.organizations) == 2


class TestStateAIExecutesInWayneCounty:
    """RuleBasedStateAI dispatch fires for real over a persistent-graph run."""

    def test_state_ai_dispatch_fires_over_several_ticks(self) -> None:
        state, _config, defines = create_wayne_county_scenario()
        graph = state.to_graph()
        services = ServiceContainer.create(defines=defines)
        system = OODASystem()

        # Task #73: ORG001 starts at heat=0.0 (_create_player_org). Post-fix,
        # zero visible threats means an honest no-op (never self-targeting),
        # so a truly untouched scenario would never set budget_cost > 0 and
        # this dispatch-fires assertion would degenerate to "never fires" —
        # correct new behavior, but useless as a "does the machinery run"
        # probe. Seed a believable nonzero heat (some organizing has already
        # drawn attention) so a real threat is visible and dispatch has
        # something to act on.
        graph.nodes[_PLAYER_ORG_ID]["heat"] = 0.4

        fired_ticks: list[int] = []
        max_ticks = 5
        for tick in range(max_ticks):
            context: dict[str, Any] = {"tick": tick}
            system.step(graph, services, context)

            resolution = context["persistent_data"]["turn_resolution"]
            for result in resolution["action_phase_results"]:
                action = result["action"]
                if action["org_id"] == _STATE_APPARATUS_ID and action["budget_cost"] > 0.0:
                    fired_ticks.append(tick)

        assert fired_ticks, (
            "RuleBasedStateAI never dispatched over 5 ticks — the "
            "faction_balance gate did not activate"
        )

    def test_legacy_priority_queue_never_sets_budget_cost(self) -> None:
        """Control: the player org (no faction_balance) never carries the
        RuleBasedStateAI signature, confirming budget_cost > 0 is a clean
        discriminator and not an artifact of some other action path."""
        state, _config, defines = create_wayne_county_scenario()
        graph = state.to_graph()
        services = ServiceContainer.create(defines=defines)
        system = OODASystem()

        context: dict[str, Any] = {"tick": 0}
        system.step(graph, services, context)

        resolution = context["persistent_data"]["turn_resolution"]
        player_org_actions = [
            r["action"]
            for r in resolution["action_phase_results"]
            if r["action"]["org_id"] == "ORG001"
        ]
        assert all(a["budget_cost"] == 0.0 for a in player_org_actions)


class TestStateAINoLongerSelfTargets:
    """Task #73: ORG002's REPRESS lands on ORG001, never on itself.

    Direct proof of the fix, over a real 5-tick wayne_county run (no
    mocking): the targeted entity's heat rises, ORG002's own heat does
    not self-inflate, and — separately — a scenario with zero visible
    threats produces an honest no-op rather than a self-target.
    """

    def test_repress_targets_other_org_and_only_targets_heat_rises(self) -> None:
        state, _config, defines = create_wayne_county_scenario()
        graph = state.to_graph()
        services = ServiceContainer.create(defines=defines)
        system = OODASystem()

        # ORG001 starts at heat=0.0 (see module docstring) -- seed a
        # visible threat so ORG002 has a real target to sort by
        # Heat x Visibility.
        graph.nodes[_PLAYER_ORG_ID]["heat"] = 0.4
        initial_state_apparatus_heat = graph.nodes[_STATE_APPARATUS_ID]["heat"]

        state_apparatus_target_ids: list[str] = []
        max_ticks = 5
        for tick in range(max_ticks):
            context: dict[str, Any] = {"tick": tick}
            system.step(graph, services, context)

            resolution = context["persistent_data"]["turn_resolution"]
            for result in resolution["action_phase_results"]:
                action = result["action"]
                if action["org_id"] == _STATE_APPARATUS_ID:
                    state_apparatus_target_ids.append(action["target_id"])

        assert state_apparatus_target_ids, "ORG002 must dispatch at least one action"
        assert all(t != _STATE_APPARATUS_ID for t in state_apparatus_target_ids), (
            f"ORG002 self-targeted at least once: {state_apparatus_target_ids}"
        )
        assert _PLAYER_ORG_ID in state_apparatus_target_ids, (
            "ORG002 never targeted the only visible non-state org (ORG001) — "
            f"got targets {state_apparatus_target_ids}"
        )

        # The targeted entity's heat rose from the seeded 0.4.
        assert graph.nodes[_PLAYER_ORG_ID]["heat"] > 0.4

        # ORG002's own heat is untouched by this mechanism -- no other
        # System writes organization heat (verified: only
        # ooda.layer3._propagate_heat does, and only for the REPRESS/
        # SURVEIL action's *target*, never the acting org).
        assert graph.nodes[_STATE_APPARATUS_ID]["heat"] == initial_state_apparatus_heat

    def test_zero_visible_threat_is_honest_no_op_never_self_target(self) -> None:
        """Untouched scenario default (ORG001 heat=0.0): the Blind Giant
        sees nothing and does nothing -- it must NOT fall back to
        self-targeting."""
        state, _config, defines = create_wayne_county_scenario()
        graph = state.to_graph()
        services = ServiceContainer.create(defines=defines)
        system = OODASystem()

        initial_state_apparatus_heat = graph.nodes[_STATE_APPARATUS_ID]["heat"]

        context: dict[str, Any] = {"tick": 0}
        system.step(graph, services, context)

        resolution = context["persistent_data"]["turn_resolution"]
        state_apparatus_actions = [
            r["action"]
            for r in resolution["action_phase_results"]
            if r["action"]["org_id"] == _STATE_APPARATUS_ID
        ]

        assert state_apparatus_actions == [], (
            "With zero visible threats, ORG002 must produce no actions at "
            f"all (honest no-op), got {state_apparatus_actions}"
        )
        assert graph.nodes[_STATE_APPARATUS_ID]["heat"] == initial_state_apparatus_heat

    def test_targeting_is_deterministic_across_independent_runs(self) -> None:
        """Constitution III.7: two fresh scenario instances, identical
        seeding, must produce byte-identical ORG002 action streams
        (action_type, target_id, budget_cost per tick)."""
        max_ticks = 5

        def _run() -> list[tuple[str, str, float]]:
            state, _config, defines = create_wayne_county_scenario()
            graph = state.to_graph()
            services = ServiceContainer.create(defines=defines)
            system = OODASystem()
            graph.nodes[_PLAYER_ORG_ID]["heat"] = 0.4

            stream: list[tuple[str, str, float]] = []
            for tick in range(max_ticks):
                context: dict[str, Any] = {"tick": tick}
                system.step(graph, services, context)
                resolution = context["persistent_data"]["turn_resolution"]
                for result in resolution["action_phase_results"]:
                    action = result["action"]
                    if action["org_id"] == _STATE_APPARATUS_ID:
                        stream.append(
                            (action["action_type"], action["target_id"], action["budget_cost"])
                        )
            return stream

        run_a = _run()
        run_b = _run()

        assert run_a, "Expected ORG002 to dispatch at least once"
        assert run_a == run_b, f"Determinism violated: run A={run_a} != run B={run_b}"
