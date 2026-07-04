"""Spec-071: fascist action verb resolution (POGROM / LOCKOUT / VIGILANTISM).

RED_BROWN_COUP is auto-triggered by the FascistFactionSystem, not resolved
through OODA, so it is covered by that system's tests.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import OODADefines, OrganizationDefines
from babylon.engine.graph import BabylonGraph
from babylon.models.enums import ActionType, EdgeType, EventType
from babylon.ooda.action_effects import resolve_action
from babylon.ooda.types import Action

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
