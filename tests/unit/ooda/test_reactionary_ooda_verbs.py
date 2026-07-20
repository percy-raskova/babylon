"""Spec-071: fascist action verb resolution (POGROM / LOCKOUT / VIGILANTISM).

RED_BROWN_COUP is auto-triggered by the FascistFactionSystem, not resolved
through OODA, so it is covered by that system's tests.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import OODADefines, OrganizationDefines, ReactionaryDefines
from babylon.models.enums import ActionType, EdgeType, EventType
from babylon.ooda.action_effects import resolve_action
from babylon.ooda.types import Action
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit

_ORG_ATTRS = {"_node_type": "organization", "id": "ORG1", "org_type": "political_faction"}
_DEFINES = OODADefines()
_ORG_DEFINES = OrganizationDefines()


class TestFascistVerbResolution:
    def test_pogrom_raises_repression_and_destroys_wealth(self) -> None:
        g = BabylonGraph()
        g.add_node("ORG1", **_ORG_ATTRS)
        g.add_node("C900", _node_type="social_class", repression_faced=0.2, wealth=100.0)
        action = Action(org_id="ORG1", action_type=ActionType.POGROM, target_id="C900")
        result = resolve_action(action, _ORG_ATTRS, g, _DEFINES, _ORG_DEFINES)
        assert result.success
        assert EventType.POGROM.value in result.events_generated
        node = g.get_node("C900")
        assert node.attributes["repression_faced"] > 0.2
        assert node.attributes["wealth"] < 100.0

    def test_vigilantism_raises_repression(self) -> None:
        g = BabylonGraph()
        g.add_node("ORG1", **_ORG_ATTRS)
        g.add_node("C900", _node_type="social_class", repression_faced=0.2, wealth=100.0)
        action = Action(org_id="ORG1", action_type=ActionType.VIGILANTISM, target_id="C900")
        result = resolve_action(action, _ORG_ATTRS, g, _DEFINES, _ORG_DEFINES)
        assert EventType.VIGILANTISM.value in result.events_generated
        node = g.get_node("C900")
        assert node.attributes["repression_faced"] > 0.2
        # Vigilantism does not destroy wealth (only POGROM does).
        assert node.attributes["wealth"] == 100.0

    def test_lockout_attenuates_wages(self) -> None:
        g = BabylonGraph()
        g.add_node("ORG1", **{**_ORG_ATTRS, "org_type": "business"})
        g.add_node("C500", _node_type="social_class", role="core_bourgeoisie")
        g.add_node("C900", _node_type="social_class", role="labor_aristocracy")
        g.add_edge("C500", "C900", edge_type=EdgeType.WAGES.value, value_flow=10.0)
        action = Action(org_id="ORG1", action_type=ActionType.LOCKOUT, target_id="C900")
        result = resolve_action(action, _ORG_ATTRS, g, _DEFINES, _ORG_DEFINES)
        assert EventType.LOCKOUT.value in result.events_generated
        edge = g.get_edge("C500", "C900", EdgeType.WAGES)
        assert edge.attributes["value_flow"] < 10.0

    def test_reactionary_override_is_honored(self) -> None:
        # III.5: a caller-supplied ReactionaryDefines override flows into the
        # verb effect (vs the dataclass default) — the defines.yaml path.
        g = BabylonGraph()
        g.add_node("ORG1", **_ORG_ATTRS)
        g.add_node("C900", _node_type="social_class", repression_faced=0.0, wealth=100.0)
        override = ReactionaryDefines(pogrom_wealth_destruction=0.5)
        action = Action(org_id="ORG1", action_type=ActionType.POGROM, target_id="C900")
        resolve_action(action, _ORG_ATTRS, g, _DEFINES, _ORG_DEFINES, reactionary=override)
        # 0.5 override (default is 0.1) → wealth halved.
        assert g.get_node("C900").attributes["wealth"] == pytest.approx(50.0)


class TestRepressionEdgeProducer:
    """Task #42-B: POGROM/VIGILANTISM must ALSO stamp a REPRESSION edge
    (org -> target) alongside the pre-existing ``repression_faced`` scalar
    bump — ``EdgeType.REPRESSION`` had zero producers and 3 read-only
    consumers (``negotiate.py``, ``bifurcation/axis.py``,
    ``bifurcation/analysis.py``) before this. Weight is grounded in the SAME
    ``ReactionaryDefines`` increment the scalar bump uses, never an invented
    constant.
    """

    def test_pogrom_stamps_repression_edge_from_org_to_target(self) -> None:
        g = BabylonGraph()
        g.add_node("ORG1", **_ORG_ATTRS)
        g.add_node("C900", _node_type="social_class", repression_faced=0.2, wealth=100.0)
        action = Action(org_id="ORG1", action_type=ActionType.POGROM, target_id="C900")
        resolve_action(action, _ORG_ATTRS, g, _DEFINES, _ORG_DEFINES)

        edge = g.get_edge("ORG1", "C900", EdgeType.REPRESSION.value)
        assert edge is not None, "POGROM must stamp a REPRESSION edge org -> target"
        assert edge.weight == pytest.approx(ReactionaryDefines().pogrom_repression_increment)

    def test_vigilantism_stamps_repression_edge_from_org_to_target(self) -> None:
        g = BabylonGraph()
        g.add_node("ORG1", **_ORG_ATTRS)
        g.add_node("C900", _node_type="social_class", repression_faced=0.2, wealth=100.0)
        action = Action(org_id="ORG1", action_type=ActionType.VIGILANTISM, target_id="C900")
        resolve_action(action, _ORG_ATTRS, g, _DEFINES, _ORG_DEFINES)

        edge = g.get_edge("ORG1", "C900", EdgeType.REPRESSION.value)
        assert edge is not None, "VIGILANTISM must stamp a REPRESSION edge org -> target"
        assert edge.weight == pytest.approx(ReactionaryDefines().vigilantism_repression_increment)

    def test_repeated_pogroms_accumulate_edge_weight_capped_at_one(self) -> None:
        g = BabylonGraph()
        g.add_node("ORG1", **_ORG_ATTRS)
        g.add_node("C900", _node_type="social_class", repression_faced=0.2, wealth=100.0)
        action = Action(org_id="ORG1", action_type=ActionType.POGROM, target_id="C900")

        resolve_action(action, _ORG_ATTRS, g, _DEFINES, _ORG_DEFINES)
        first_weight = g.get_edge("ORG1", "C900", EdgeType.REPRESSION.value).weight
        resolve_action(action, _ORG_ATTRS, g, _DEFINES, _ORG_DEFINES)
        second_weight = g.get_edge("ORG1", "C900", EdgeType.REPRESSION.value).weight

        increment = ReactionaryDefines().pogrom_repression_increment
        assert first_weight == pytest.approx(increment)
        assert second_weight == pytest.approx(min(1.0, 2 * increment))
        assert second_weight > first_weight

    def test_reactionary_override_increment_flows_into_edge_weight(self) -> None:
        # III.5: a caller-supplied ReactionaryDefines override must also
        # ground the edge weight, not just the scalar bump.
        g = BabylonGraph()
        g.add_node("ORG1", **_ORG_ATTRS)
        g.add_node("C900", _node_type="social_class", repression_faced=0.0, wealth=100.0)
        override = ReactionaryDefines(pogrom_repression_increment=0.4)
        action = Action(org_id="ORG1", action_type=ActionType.POGROM, target_id="C900")
        resolve_action(action, _ORG_ATTRS, g, _DEFINES, _ORG_DEFINES, reactionary=override)

        edge = g.get_edge("ORG1", "C900", EdgeType.REPRESSION.value)
        assert edge.weight == pytest.approx(0.4)

    def test_repression_edge_skips_rather_than_clobbers_a_different_edge_type(self) -> None:
        """The graph stores one edge per node pair (multigraph=False) --
        stamping REPRESSION over a pre-existing DIFFERENT edge type would
        silently corrupt it. Mirrors ``_mass_work.py``'s
        create-or-strengthen-or-skip idiom for the identical constraint."""
        g = BabylonGraph()
        g.add_node("ORG1", **_ORG_ATTRS)
        g.add_node("C900", _node_type="social_class", repression_faced=0.2, wealth=100.0)
        g.add_edge("ORG1", "C900", edge_type=EdgeType.SOLIDARITY.value, solidarity_strength=0.5)
        action = Action(org_id="ORG1", action_type=ActionType.POGROM, target_id="C900")
        resolve_action(action, _ORG_ATTRS, g, _DEFINES, _ORG_DEFINES)

        assert g.get_edge("ORG1", "C900", EdgeType.REPRESSION.value) is None
        existing = g.get_edge("ORG1", "C900", EdgeType.SOLIDARITY.value)
        assert existing is not None, "the pre-existing SOLIDARITY edge must not be clobbered"
        assert existing.attributes["solidarity_strength"] == pytest.approx(0.5)

    def test_lockout_does_not_stamp_a_repression_edge(self) -> None:
        """LOCKOUT is a wage-attenuation verb, not a repression verb -- no
        REPRESSION edge should appear from it."""
        g = BabylonGraph()
        g.add_node("ORG1", **{**_ORG_ATTRS, "org_type": "business"})
        g.add_node("C500", _node_type="social_class", role="core_bourgeoisie")
        g.add_node("C900", _node_type="social_class", role="labor_aristocracy")
        g.add_edge("C500", "C900", edge_type=EdgeType.WAGES.value, value_flow=10.0)
        action = Action(org_id="ORG1", action_type=ActionType.LOCKOUT, target_id="C900")
        resolve_action(action, _ORG_ATTRS, g, _DEFINES, _ORG_DEFINES)

        assert g.get_edge("ORG1", "C900", EdgeType.REPRESSION.value) is None
