"""Tests for ``resolve_build`` (spec-108 FR-108-5, T4).

**Not yet registered in ``VERB_RESOLVERS``** (``engine/actions/__init__.py``):
doing so would make BUILD_INFRASTRUCTURE the 10th player verb, which breaks
``tests/contract/verbs/test_registry.py``'s hard 9-verb pin AND requires a
companion entry in ``web/game/engine_bridge.py``'s ``VERB_TO_ACTION_TYPE``
(actually defined in ``src/babylon/projection/verbs/preview.py``) to keep
``TestBridgeParity`` green — ``src/babylon/projection/**`` is this unit's
forbidden-file fence (another lane's territory). ``resolve_build`` is
implemented, real, and tested directly here (dispatchable the moment a
follow-up PR in the projection lane adds the "build" verb mapping and bumps
the registry contract to 10) rather than left unregistered-and-untested.
"""

from __future__ import annotations

import pytest

from babylon.engine.actions.build import resolve_build
from babylon.engine.services import ServiceContainer
from babylon.models.enums import ActionType, EventType, NodeType, OrgType
from babylon.ooda.types import Action
from babylon.topology import BabylonGraph

ORG = "org_state"
TERRITORY = "T001"

pytestmark = pytest.mark.unit


def _graph() -> BabylonGraph:
    graph = BabylonGraph()
    graph.add_node(
        ORG,
        NodeType.ORGANIZATION,
        id=ORG,
        org_type=OrgType.STATE_APPARATUS.value,
        heat=0.2,
    )
    graph.add_node(TERRITORY, NodeType.TERRITORY, id=TERRITORY)
    return graph


def _action(target_id: str = TERRITORY) -> Action:
    return Action(org_id=ORG, action_type=ActionType.BUILD_INFRASTRUCTURE, target_id=target_id)


class TestResolveBuild:
    def test_succeeds(self) -> None:
        result = resolve_build(_action(), {}, _graph(), ServiceContainer.create())
        assert result.success is True

    def test_carries_the_build_action_for_layer3(self) -> None:
        """Layer 3's EXISTING BUILD branch (ooda/layer3.py::_propagate_infrastructure)
        applies the positive infrastructure delta -- it fires because the
        ActionResult carries an ActionType.BUILD_INFRASTRUCTURE action, not
        because this resolver writes `infrastructure` itself."""
        result = resolve_build(_action(), {}, _graph(), ServiceContainer.create())
        assert result.action.action_type == ActionType.BUILD_INFRASTRUCTURE

    def test_direct_effects_carry_the_target(self) -> None:
        result = resolve_build(_action(), {}, _graph(), ServiceContainer.create())
        assert result.direct_effects["target_id"] == TERRITORY

    def test_emits_infrastructure_change_event(self) -> None:
        """D5: INFRASTRUCTURE_CHANGE is the correct event for BUILD/REPAIR/
        ATTACK corridor narrative -- reused, not reinvented; this is its
        first production emitter."""
        result = resolve_build(_action(), {}, _graph(), ServiceContainer.create())
        assert result.events_generated == [EventType.INFRASTRUCTURE_CHANGE.value]

    def test_does_not_raise_the_acting_orgs_heat(self) -> None:
        """Unlike resolve_attack, BUILD is not a covert/violent act -- it
        draws no state attention onto its own actor."""
        graph = _graph()
        resolve_build(_action(), {}, graph, ServiceContainer.create())
        assert graph.nodes[ORG]["heat"] == pytest.approx(0.2)

    def test_missing_target_node_is_still_a_success(self) -> None:
        """Territory-scoped targeting (Director ruling 4 default, ADR165):
        this resolver's own job is just to carry the action forward for
        layer 3 -- it does not itself require the target to already exist
        in the graph (layer3's own None-guard handles that case)."""
        result = resolve_build(_action(target_id="GHOST"), {}, _graph(), ServiceContainer.create())
        assert result.success is True
