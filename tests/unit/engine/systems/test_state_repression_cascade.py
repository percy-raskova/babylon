"""Adversary-train W1: the Aleksandrov proof.

``repression_faced`` (:class:`~babylon.models.entities.social_class.SocialClass`)
IS the P(S|R) denominator (``SurvivalSystem``, ``survival_calculus.py``) and the
``ConsciousnessSystem`` continuous repression term (task #42-B,
``test_ideology_repression_continuous_term.py``) — a formal construct with an
immediate material relation (Constitution's Aleksandrov Test). Before W1,
``babylon.ooda.action_effects._resolve_repressive`` computed a CI backfire
nobody consumed and never touched ``repression_faced`` at all, so a state
REPRESS was invisible to both downstream systems no matter how it was
dispatched. This module proves the chain now activates through the SAME
tested channels the design doc names, end to end from the REAL
``resolve_action`` entry point OODASystem's NPC branch now calls — not just
the event tag.

OODASystem runs at position 14 (Action phase); SurvivalSystem at 15 and
ConsciousnessSystem at 17 (both Consequence phase) — all in the SAME tick,
strict order, each system reading the prior systems' graph mutations. The
cascade is same-tick, not next-tick.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.ideology import ConsciousnessSystem
from babylon.engine.systems.survival import SurvivalSystem
from babylon.models.enums import ActionType, OrgType
from babylon.ooda.action_effects import resolve_action
from babylon.ooda.types import Action
from babylon.topology.graph import BabylonGraph

_WORKER_ID = "worker_1"
_STATE_ORG_ID = "state_org"

_ORG_ATTRS = {
    "_node_type": "organization",
    "id": _STATE_ORG_ID,
    "org_type": OrgType.STATE_APPARATUS.value,
}


def _fresh_ideology() -> dict[str, float]:
    return {"class_consciousness": 0.0, "national_identity": 0.5, "agitation": 0.0}


def _graph_with_worker() -> BabylonGraph:
    """A single social_class node at the ambient ``repression_faced``
    default (0.5, ``SocialClass``'s own model default) with no wage/wealth
    motion at all — every OTHER agitation/survival source pinned at zero
    (mirrors ``test_ideology_repression_continuous_term.py``'s own fixture
    philosophy) so any change this tick is attributable ONLY to the REPRESS
    action, not some other channel."""
    graph = BabylonGraph()
    graph.add_node(
        _WORKER_ID,
        _node_type="social_class",
        wealth=1.0,
        population=1,
        organization=0.3,
        ideology=_fresh_ideology(),
        repression_faced=0.5,
    )
    return graph


def _repress_worker(graph: BabylonGraph, defines: GameDefines) -> None:
    """Resolve a REPRESS action against ``_WORKER_ID`` through the REAL
    ``resolve_action`` entry point — the SAME call
    ``OODASystem._resolve_for_organization``'s NPC branch (adversary-train
    W1) and the player-verb dispatcher's registered resolvers use."""
    action = Action(org_id=_STATE_ORG_ID, action_type=ActionType.REPRESS, target_id=_WORKER_ID)
    resolve_action(action, _ORG_ATTRS, graph, defines.ooda, defines.organization)


@pytest.mark.unit
class TestStateRepressionCascadesToSurvivalAndConsciousness:
    """The material chain, not just the event: a state REPRESS raises
    ``repression_faced``, which lowers ``SurvivalSystem``'s P(S|R) and
    raises ``ConsciousnessSystem``'s agitation — through EXISTING tested
    channels, no new wiring beyond W1's ``_resolve_repressive`` fix."""

    def test_repress_lowers_survival_p_revolution(self) -> None:
        defines = GameDefines()
        services = ServiceContainer.create(defines=defines)

        control = _graph_with_worker()
        SurvivalSystem().step(control, services, TickContext(tick=1))
        control_p_revolution = control.nodes[_WORKER_ID]["p_revolution"]

        treatment = _graph_with_worker()
        _repress_worker(treatment, defines)
        SurvivalSystem().step(treatment, services, TickContext(tick=1))
        treatment_p_revolution = treatment.nodes[_WORKER_ID]["p_revolution"]

        assert (
            treatment.nodes[_WORKER_ID]["repression_faced"]
            > control.nodes[_WORKER_ID]["repression_faced"]
        )
        assert treatment_p_revolution < control_p_revolution, (
            "a state REPRESS must LOWER the target's P(S|R) -- "
            "repression_faced is the denominator of "
            "calculate_revolution_probability (survival_calculus.py); more "
            "repression, harder to survive revolt"
        )

    def test_repress_raises_consciousness_agitation(self) -> None:
        defines = GameDefines()
        services = ServiceContainer.create(defines=defines)

        graph = _graph_with_worker()
        _repress_worker(graph, defines)

        ConsciousnessSystem().step(graph, services, TickContext(tick=1))

        ideology = graph.nodes[_WORKER_ID]["ideology"]
        assert ideology["agitation"] > 0.0, (
            "a state REPRESS must generate agitation via ConsciousnessSystem's "
            "continuous repression term (ideology.py) once repression_faced "
            "is produced above the ambient baseline -- the SAME term task "
            "#42-B wires (test_ideology_repression_continuous_term.py), now "
            "fed by a REAL state action instead of a hand-set attribute"
        )

    def test_material_chain_fires_within_the_same_tick(self) -> None:
        """OODA (position 14) runs before SurvivalSystem (15) and
        ConsciousnessSystem (17) in the SAME tick -- systems mutate the
        shared graph in strict order, so the bump is visible immediately
        to both, not on some later tick."""
        defines = GameDefines()
        services = ServiceContainer.create(defines=defines)
        graph = _graph_with_worker()
        context = TickContext(tick=1)

        _repress_worker(graph, defines)
        SurvivalSystem().step(graph, services, context)
        ConsciousnessSystem().step(graph, services, context)

        assert graph.nodes[_WORKER_ID]["p_revolution"] < 1.0
        assert graph.nodes[_WORKER_ID]["ideology"]["agitation"] > 0.0

    def test_repression_edge_also_stamped_alongside_the_cascade(self) -> None:
        """The REPRESSION edge (task #42-B pattern, org -> target) stamps
        alongside the SAME scalar bump feeding the cascade above -- not a
        second, independent effect."""
        from babylon.models.enums import EdgeType

        defines = GameDefines()
        graph = _graph_with_worker()
        _repress_worker(graph, defines)

        edge = graph.get_edge(_STATE_ORG_ID, _WORKER_ID, EdgeType.REPRESSION.value)
        assert edge is not None
        assert edge.weight == pytest.approx(defines.ooda.repress_heat_delta)
