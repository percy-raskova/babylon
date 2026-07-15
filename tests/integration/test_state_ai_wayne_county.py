"""Proves Feature 039's RuleBasedStateAI actually executes in a real
wayne_county playthrough (AW3-R2 item 3 / epochs-vision-gap-audit.md §5
Wave 3 item 3).

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

# See _legacy_wayne._STATE_APPARATUS_ID.
_STATE_APPARATUS_ID = "ORG002"


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
