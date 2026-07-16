"""Contract: graph-write round-trip safety (verb-dispatch engine, §8).

Every attribute a resolver writes MUST be a model field that survives
``WorldState.from_graph`` OR a member of the matching exclusion frozenset. For
each verb: dispatch, then reconstruct — reconstruction must not raise, and the
intended mutation must survive (or be a documented transient).
"""

from __future__ import annotations

import pytest

from babylon.engine.actions import resolve_player_action
from babylon.models.enums import ActionType, EdgeType
from babylon.models.world_state import TERRITORY_EXCLUDED_FIELDS, WorldState
from babylon.ooda.layer3 import process_layer3
from babylon.ooda.types import Action
from tests.contract.verbs.conftest import (
    CLASS_ID,
    HOME_TERRITORY,
    ORG_ID,
    OTHER_TERRITORY,
    RIVAL_ID,
    org_attrs,
)

pytestmark = pytest.mark.contract


def _dispatch(verb_graph, services, action_type, target_id, **params):
    action = Action(org_id=ORG_ID, action_type=action_type, target_id=target_id, params=params)
    return resolve_player_action(action, org_attrs(verb_graph), verb_graph, services)


class TestRoundTripSurvives:
    """from_graph must not raise after any verb, and mutations must survive."""

    def test_educate_roundtrips(self, verb_graph, services) -> None:
        _dispatch(verb_graph, services, ActionType.EDUCATE, CLASS_ID)
        WorldState.from_graph(verb_graph, tick=1)  # must not raise

    def test_campaign_roundtrips(self, verb_graph, services) -> None:
        _dispatch(verb_graph, services, ActionType.PROPAGANDIZE, CLASS_ID)
        WorldState.from_graph(verb_graph, tick=1)

    def test_aid_transfer_survives(self, verb_graph, services) -> None:
        wealth_before = float(verb_graph.nodes[CLASS_ID]["wealth"])
        _dispatch(verb_graph, services, ActionType.PROVIDE_SERVICE, CLASS_ID, transfer_amount=10.0)
        ws = WorldState.from_graph(verb_graph, tick=1)
        assert float(ws.entities[CLASS_ID].wealth) == pytest.approx(wealth_before + 10.0)
        assert float(ws.organizations[ORG_ID].budget) == pytest.approx(90.0)

    def test_reproduce_survives(self, verb_graph, services) -> None:
        cadre_before = float(verb_graph.nodes[ORG_ID]["cadre_level"])
        _dispatch(verb_graph, services, ActionType.RECRUIT, HOME_TERRITORY, mode="cadre_training")
        ws = WorldState.from_graph(verb_graph, tick=1)
        assert float(ws.organizations[ORG_ID].cadre_level) > cadre_before

    def test_attack_infra_is_a_transient_territory_attr(self, verb_graph, services) -> None:
        # §8.3 landmine: layer 3 writes `infrastructure` onto the territory,
        # which is not a Territory field — it must be an excluded transient.
        assert "infrastructure" in TERRITORY_EXCLUDED_FIELDS
        result = _dispatch(verb_graph, services, ActionType.ATTACK_INFRASTRUCTURE, HOME_TERRITORY)
        process_layer3([result], verb_graph, services.defines.ooda)
        assert "infrastructure" in verb_graph.nodes[HOME_TERRITORY]
        ws = WorldState.from_graph(verb_graph, tick=1)  # must not raise
        assert HOME_TERRITORY in ws.territories
        # Acting-org heat (a real field) survives.
        assert float(ws.organizations[ORG_ID].heat) > 0.0

    def test_mobilize_agitation_survives(self, verb_graph, services) -> None:
        _dispatch(verb_graph, services, ActionType.PROTEST, CLASS_ID, sl_committed=2.0)
        ws = WorldState.from_graph(verb_graph, tick=1)
        assert ws.entities[CLASS_ID].ideology.agitation > 0.0

    def test_mobilize_territory_heat_survives(self, verb_graph, services) -> None:
        _dispatch(verb_graph, services, ActionType.PROTEST, HOME_TERRITORY, sl_committed=2.0)
        ws = WorldState.from_graph(verb_graph, tick=1)
        assert float(ws.territories[HOME_TERRITORY].heat) > 0.0

    def test_investigate_roundtrips(self, verb_graph, services) -> None:
        _dispatch(verb_graph, services, ActionType.MAP_NETWORK, CLASS_ID)
        WorldState.from_graph(verb_graph, tick=1)

    def test_player_investigate_territory_intel_roundtrips(self, services) -> None:
        """EH Phase 2 crash class (2026-07-16 adversarial-verify critical):
        the PLAYER org investigating a TERRITORY writes ``investigation_intel``
        onto the territory node inside ``step()``'s internal graph — the same
        graph ``from_graph()`` immediately reconstructs. Reconstruction must
        not raise, and the earned intel must SURVIVE (it is accumulated
        event-sourced state, not a recomputable shadow attr)."""
        from tests.contract.verbs.conftest import build_verb_world

        world = build_verb_world()
        workers = world.entities[CLASS_ID]
        receptive = workers.model_copy(
            update={
                "population": 1000,
                "ideology": workers.ideology.model_copy(update={"class_consciousness": 0.8}),
            }
        )
        world = world.model_copy(
            update={
                "player_org_id": ORG_ID,
                "entities": {**world.entities, CLASS_ID: receptive},
            }
        )
        graph = world.to_graph()
        # Receptive masses in the target territory (M_r = (1-0)·0.8·1.0 = 0.8):
        # the corpus gate ("cannot investigate if masses won't talk") is met.
        graph.add_edge(CLASS_ID, HOME_TERRITORY, edge_type=EdgeType.TENANCY.value)

        result = _dispatch(graph, services, ActionType.MAP_NETWORK, HOME_TERRITORY)
        assert result.success

        ws = WorldState.from_graph(graph, tick=1)  # must not raise
        boost = services.defines.epistemic_horizon.investigate_intel_boost
        assert ws.territories[HOME_TERRITORY].investigation_intel == pytest.approx(boost)

    def test_move_territory_ids_survive(self, verb_graph, services) -> None:
        _dispatch(verb_graph, services, ActionType.MOVE, OTHER_TERRITORY)
        ws = WorldState.from_graph(verb_graph, tick=1)
        assert ws.organizations[ORG_ID].territory_ids == [OTHER_TERRITORY]

    def test_negotiate_edge_flip_survives(self, verb_graph, services) -> None:
        verb_graph.add_edge(ORG_ID, RIVAL_ID, edge_type=EdgeType.EXPLOITATION.value)
        _dispatch(verb_graph, services, ActionType.PROPOSE_ALLIANCE, RIVAL_ID)
        ws = WorldState.from_graph(verb_graph, tick=1)
        flipped = [
            r
            for r in ws.relationships
            if r.source_id == ORG_ID
            and r.target_id == RIVAL_ID
            and r.edge_type == EdgeType.TRANSACTIONAL
        ]
        assert len(flipped) == 1
