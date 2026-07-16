"""Contract: per-verb effect classes (verb-dispatch engine).

Each canonical verb must produce its characteristic REAL effect when dispatched
through :func:`babylon.engine.actions.resolve_player_action` — proving the
resolvers are no longer blind ``success=True`` no-ops.
"""

from __future__ import annotations

import copy

import pytest

from babylon.engine.actions import resolve_player_action
from babylon.models.enums import ActionType, EdgeType
from babylon.ooda.layer3 import process_layer3
from babylon.ooda.types import Action, ActionResult
from tests.contract.verbs.conftest import (
    CLASS_ID,
    HOME_TERRITORY,
    ORG_ID,
    OTHER_TERRITORY,
    RIVAL_ID,
    org_attrs,
)

pytestmark = pytest.mark.contract


def _dispatch(verb_graph, services, action_type, target_id, **params) -> ActionResult:
    action = Action(
        org_id=ORG_ID,
        action_type=action_type,
        target_id=target_id,
        params=params,
    )
    return resolve_player_action(action, org_attrs(verb_graph), verb_graph, services)


class TestConsciousnessVerbs:
    """educate / campaign route through the five-factor CI machinery."""

    def test_educate_produces_consciousness_delta(self, verb_graph, services) -> None:
        result = _dispatch(verb_graph, services, ActionType.EDUCATE, CLASS_ID)
        assert result.success is True
        assert result.consciousness_delta is not None
        assert result.consciousness_delta.collective_identity_delta != 0.0

    def test_campaign_produces_consciousness_delta(self, verb_graph, services) -> None:
        result = _dispatch(verb_graph, services, ActionType.PROPAGANDIZE, CLASS_ID)
        assert result.success is True
        assert result.consciousness_delta is not None
        assert result.consciousness_delta.collective_identity_delta != 0.0


class TestEducateDoctrineStudy:
    """Educate(Doctrine) sub-verb — the Study order (DoctrineSystem Unit 7b).

    A ``doctrine_node_id`` param turns EDUCATE into a standing study order the
    DoctrineSystem honors (save-toward-target instead of greedy). The Article V
    roster is untouched — this is a target type of the existing Educate verb,
    exactly as Investigate carries Territory/Org/Edge sub-verbs.
    """

    def test_study_order_sets_standing_target(self, verb_graph, services) -> None:
        result = _dispatch(
            verb_graph, services, ActionType.EDUCATE, ORG_ID, doctrine_node_id="trade_unionism"
        )
        assert result.success is True
        assert result.direct_effects["study_target_id"] == "trade_unionism"
        assert verb_graph.nodes[ORG_ID]["study_target_id"] == "trade_unionism"

    def test_trap_target_refused_loudly(self, verb_graph, services) -> None:
        result = _dispatch(
            verb_graph, services, ActionType.EDUCATE, ORG_ID, doctrine_node_id="adventurism"
        )
        assert result.success is False
        assert "trap" in (result.failure_reason or "").lower()
        assert verb_graph.nodes[ORG_ID].get("study_target_id") is None

    def test_unknown_node_refused_loudly(self, verb_graph, services) -> None:
        result = _dispatch(
            verb_graph, services, ActionType.EDUCATE, ORG_ID, doctrine_node_id="no_such_node"
        )
        assert result.success is False
        assert "no_such_node" in (result.failure_reason or "")

    def test_already_acquired_target_refused(self, verb_graph, services) -> None:
        verb_graph.update_node(ORG_ID, acquired_doctrine_ids=("class_consciousness",))
        result = _dispatch(
            verb_graph,
            services,
            ActionType.EDUCATE,
            ORG_ID,
            doctrine_node_id="class_consciousness",
        )
        assert result.success is False
        assert "already" in (result.failure_reason or "").lower()

    def test_plain_educate_unchanged_by_the_sub_verb(self, verb_graph, services) -> None:
        # No doctrine_node_id param → the classic consciousness path, untouched.
        result = _dispatch(verb_graph, services, ActionType.EDUCATE, CLASS_ID)
        assert result.success is True
        assert result.consciousness_delta is not None


class TestAidTransfer:
    """aid conserves value: org budget loss == target wealth gain × efficiency."""

    def test_aid_transfers_budget_to_wealth(self, verb_graph, services) -> None:
        budget_before = float(verb_graph.nodes[ORG_ID]["budget"])
        wealth_before = float(verb_graph.nodes[CLASS_ID]["wealth"])

        result = _dispatch(
            verb_graph, services, ActionType.PROVIDE_SERVICE, CLASS_ID, transfer_amount=10.0
        )

        assert result.success is True
        assert result.direct_effects["amount_transferred"] == 10.0
        efficiency = result.direct_effects["efficiency"]
        assert float(verb_graph.nodes[ORG_ID]["budget"]) == pytest.approx(budget_before - 10.0)
        assert float(verb_graph.nodes[CLASS_ID]["wealth"]) == pytest.approx(
            wealth_before + 10.0 * efficiency
        )

    def test_aid_insufficient_budget_fails_loud(self, verb_graph, services) -> None:
        result = _dispatch(
            verb_graph, services, ActionType.PROVIDE_SERVICE, CLASS_ID, transfer_amount=1e9
        )
        assert result.success is False
        assert result.failure_reason is not None


class TestReproduce:
    """reproduce (cadre training) raises cadre_level and cohesion."""

    def test_cadre_training_raises_cadre_and_cohesion(self, verb_graph, services) -> None:
        cadre_before = float(verb_graph.nodes[ORG_ID]["cadre_level"])
        cohesion_before = float(verb_graph.nodes[ORG_ID]["cohesion"])

        result = _dispatch(
            verb_graph, services, ActionType.RECRUIT, HOME_TERRITORY, mode="cadre_training"
        )

        assert result.success is True
        assert float(verb_graph.nodes[ORG_ID]["cadre_level"]) > cadre_before
        assert float(verb_graph.nodes[ORG_ID]["cohesion"]) > cohesion_before


class TestAttack:
    """attack raises acting-org heat AND routes the infra delta through layer 3."""

    def test_attack_infra_channel_fires_via_layer3(self, verb_graph, services) -> None:
        heat_before = float(verb_graph.nodes[ORG_ID]["heat"])
        result = _dispatch(verb_graph, services, ActionType.ATTACK_INFRASTRUCTURE, HOME_TERRITORY)
        assert result.success is True
        # Acting-org heat rose (a real graph write).
        assert float(verb_graph.nodes[ORG_ID]["heat"]) > heat_before

        # The ATTACK ActionResult routes through layer 3, decrementing the
        # target territory's infrastructure (default 0.5 -> 0.4).
        summary = process_layer3([result], verb_graph, services.defines.ooda)
        assert summary["infrastructure_updates"] == 1
        assert float(verb_graph.nodes[HOME_TERRITORY]["infrastructure"]) < 0.5


class TestMobilize:
    """mobilize routes agitation into a class target, heat into a territory."""

    def test_agitation_routes_into_social_class(self, verb_graph, services) -> None:
        agitation_before = float(verb_graph.nodes[CLASS_ID]["ideology"]["agitation"])
        result = _dispatch(verb_graph, services, ActionType.PROTEST, CLASS_ID, sl_committed=2.0)
        assert result.success is True
        assert result.direct_effects["turnout"] > 0.0
        assert float(verb_graph.nodes[CLASS_ID]["ideology"]["agitation"]) > agitation_before

    def test_heat_routes_into_territory(self, verb_graph, services) -> None:
        heat_before = float(verb_graph.nodes[HOME_TERRITORY]["heat"])
        result = _dispatch(
            verb_graph, services, ActionType.PROTEST, HOME_TERRITORY, sl_committed=2.0
        )
        assert result.success is True
        assert float(verb_graph.nodes[HOME_TERRITORY]["heat"]) > heat_before


class TestInvestigate:
    """investigate reveals attributes WITHOUT mutating any graph state."""

    def test_no_graph_mutation_but_effects_reported(self, verb_graph, services) -> None:
        before = copy.deepcopy(dict(verb_graph.nodes(data=True)))
        result = _dispatch(verb_graph, services, ActionType.MAP_NETWORK, CLASS_ID)
        after = dict(verb_graph.nodes(data=True))

        assert result.success is True
        assert result.direct_effects["revealed"]
        assert before == after, "INVESTIGATE mutated the graph"


class TestMove:
    """move rewrites the acting org's territory_ids."""

    def test_relocate_rewrites_territory_ids(self, verb_graph, services) -> None:
        result = _dispatch(verb_graph, services, ActionType.MOVE, OTHER_TERRITORY)
        assert result.success is True
        assert verb_graph.nodes[ORG_ID]["territory_ids"] == [OTHER_TERRITORY]

    def test_move_to_non_territory_fails_loud(self, verb_graph, services) -> None:
        result = _dispatch(verb_graph, services, ActionType.MOVE, CLASS_ID)
        assert result.success is False
        assert result.failure_reason is not None


class TestNegotiate:
    """negotiate flips an antagonistic edge to TRANSACTIONAL."""

    def test_flips_exploitation_to_transactional(self, verb_graph, services) -> None:
        verb_graph.add_edge(ORG_ID, RIVAL_ID, edge_type=EdgeType.EXPLOITATION.value)
        result = _dispatch(verb_graph, services, ActionType.PROPOSE_ALLIANCE, RIVAL_ID)
        assert result.success is True
        assert result.direct_effects["edge_flipped"] is True
        assert verb_graph.get_edge_data(ORG_ID, RIVAL_ID)["edge_type"] == (
            EdgeType.TRANSACTIONAL.value
        )

    def test_creates_edge_when_none_exists(self, verb_graph, services) -> None:
        assert verb_graph.get_edge_data(ORG_ID, RIVAL_ID) is None
        result = _dispatch(verb_graph, services, ActionType.PROPOSE_ALLIANCE, RIVAL_ID)
        assert result.success is True
        assert verb_graph.get_edge_data(ORG_ID, RIVAL_ID)["edge_type"] == (
            EdgeType.TRANSACTIONAL.value
        )
