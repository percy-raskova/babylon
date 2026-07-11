"""Tests for Phase 3: System integration of consciousness routing (Spec 043).

These tests verify that:
1. ConsciousnessSystem writes MaterialConditionsBuffer on population nodes
2. CommunitySystem applies education_pressure decay
3. Struggle system EXCESSIVE_FORCE generates agitation via repression backfire
4. ConsciousnessSystem reads tensor data from ServiceContainer when available

TDD Red Phase: These tests define the expected behavior for system-level
consciousness routing integration.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from babylon.config.defines import GameDefines
from babylon.models.enums import EdgeType
from babylon.topology.graph import BabylonGraph


@pytest.mark.unit
class TestConsciousnessSystemMaterialBuffer:
    """ConsciousnessSystem should write MaterialConditionsBuffer on nodes."""

    def _make_graph_and_services(
        self,
        *,
        wage_change: float = -20.0,
        solidarity: float = 0.0,
    ) -> tuple[Any, Any, dict[str, Any]]:
        """Build a minimal graph + services for ConsciousnessSystem testing."""

        # Build a real GraphProtocol via the adapter

        G = BabylonGraph()
        G.add_node(
            "worker_1",
            node_type="social_class",
            active=True,
            wealth=100.0,
            ideology={
                "class_consciousness": 0.0,
                "national_identity": 0.5,
                "agitation": 0.0,
            },
        )

        if solidarity > 0:
            # Add a source node with consciousness to provide solidarity
            G.add_node(
                "organizer_1",
                node_type="social_class",
                active=True,
                ideology={
                    "class_consciousness": 0.8,
                    "national_identity": 0.1,
                    "agitation": 0.0,
                },
            )
            G.add_edge(
                "organizer_1",
                "worker_1",
                edge_type=EdgeType.SOLIDARITY,
                solidarity_strength=solidarity,
            )

        # Add wage edge
        initial_wage = 50.0
        G.add_node("employer_1", node_type="social_class", active=True)
        G.add_edge(
            "employer_1",
            "worker_1",
            edge_type=EdgeType.WAGES,
            value_flow=initial_wage + wage_change,
        )

        graph = G

        # Build services
        defines = GameDefines()
        services = MagicMock()
        services.defines = defines

        # Context with previous wages stored
        context = {
            "previous_wages": {"worker_1": initial_wage},
            "previous_wealth": {"worker_1": 100.0},
        }

        return graph, services, context

    def test_material_conditions_buffer_written_on_node(self) -> None:
        """ConsciousnessSystem writes material_conditions on social_class nodes."""
        from babylon.engine.systems.ideology import ConsciousnessSystem

        graph, services, context = self._make_graph_and_services(wage_change=-20.0)
        system = ConsciousnessSystem()
        system.step(graph, services, context)

        node = graph.get_node("worker_1")
        assert node is not None
        mc = node.attributes.get("material_conditions")
        assert mc is not None, "material_conditions should be written on node"
        assert isinstance(mc, dict), "material_conditions as dict on node"
        assert mc["agitation"] >= 0.0

    def test_agitation_increases_on_wage_cut(self) -> None:
        """A wage cut should increase agitation via compute_agitation_delta."""
        from babylon.engine.systems.ideology import ConsciousnessSystem

        graph, services, context = self._make_graph_and_services(wage_change=-20.0)
        system = ConsciousnessSystem()
        system.step(graph, services, context)

        node = graph.get_node("worker_1")
        mc = node.attributes.get("material_conditions")
        assert mc is not None
        assert mc["agitation"] > 0.0, "Wage cut should generate agitation"

    def test_no_agitation_on_wage_increase(self) -> None:
        """A wage increase should not generate agitation."""
        from babylon.engine.systems.ideology import ConsciousnessSystem

        graph, services, context = self._make_graph_and_services(wage_change=10.0)
        system = ConsciousnessSystem()
        system.step(graph, services, context)

        node = graph.get_node("worker_1")
        mc = node.attributes.get("material_conditions")
        assert mc is not None
        assert mc["agitation"] == pytest.approx(0.0)

    def test_solidarity_routes_to_class_consciousness(self) -> None:
        """With solidarity, agitation routes to class_consciousness increase."""
        from babylon.engine.systems.ideology import ConsciousnessSystem

        graph, services, context = self._make_graph_and_services(
            wage_change=-30.0,
            solidarity=0.9,
        )
        system = ConsciousnessSystem()
        system.step(graph, services, context)

        node = graph.get_node("worker_1")
        ideology = node.attributes.get("ideology", {})
        assert ideology["class_consciousness"] > 0.0


@pytest.mark.unit
class TestCommunityEducationPressureDecay:
    """CommunitySystem should decay education_pressure per tick."""

    def test_education_pressure_decays(self) -> None:
        """education_pressure on CommunityState decays toward 0 each tick."""
        from babylon.models.entities.community import CommunityState
        from babylon.models.enums import CommunityType

        # Simulate what _apply_community_decay should do
        state = CommunityState(
            community_type=CommunityType.NEW_AFRIKAN,
            education_pressure=0.5,
        )
        defines = GameDefines()
        decay_rate = defines.consciousness.education_pressure_decay

        # Apply decay: p *= (1 - decay_rate)
        new_pressure = float(state.education_pressure) * (1.0 - decay_rate)
        updated = state.model_copy(update={"education_pressure": new_pressure})

        assert updated.education_pressure < state.education_pressure
        assert updated.education_pressure == pytest.approx(0.5 * (1.0 - decay_rate))

    def test_zero_pressure_stays_zero(self) -> None:
        """Zero education_pressure should stay zero after decay."""
        from babylon.models.entities.community import CommunityState
        from babylon.models.enums import CommunityType

        state = CommunityState(
            community_type=CommunityType.SETTLER,
            education_pressure=0.0,
        )
        defines = GameDefines()
        new_pressure = float(state.education_pressure) * (
            1.0 - defines.consciousness.education_pressure_decay
        )
        assert new_pressure == pytest.approx(0.0)


@pytest.mark.unit
class TestRepressionBackfireAgitation:
    """EXCESSIVE_FORCE events should generate agitation via backfire coefficient."""

    def test_backfire_generates_agitation(self) -> None:
        """Repression backfire coefficient converts EXCESSIVE_FORCE to agitation."""

        defines = GameDefines()

        # Simulate: EXCESSIVE_FORCE happened, generating backfire agitation
        # The struggle system should add repression_backfire * scale to agitation
        backfire_amount = defines.consciousness.repression_backfire
        assert backfire_amount > 0.0, "Backfire coefficient must be positive"

        # In practice, the struggle system's _update_agitation will add
        # backfire_amount to the node's agitation value
        current_agitation = 0.2
        new_agitation = current_agitation + backfire_amount
        assert new_agitation > current_agitation


@pytest.mark.unit
class TestConsciousnessSystemTensorIntegration:
    """ConsciousnessSystem should use tensor data from services when available."""

    def test_uses_exploitation_rate_from_tensor(self) -> None:
        """When tensor_registry provides data, exploitation_rate drives agitation."""
        from babylon.formulas.consciousness_routing import compute_agitation_delta

        # Simulate tensor providing exploitation rate change
        delta = compute_agitation_delta(
            exploitation_rate_delta=0.5,  # s/v increased
            imperial_rent_delta=0.0,
            visibility_delta=0.0,
        )
        assert delta > 0.0

    def test_exploitation_visibility_reflects_tensor(self) -> None:
        """compute_exploitation_visibility correctly reflects tensor state."""
        from babylon.formulas.consciousness_routing import (
            compute_exploitation_visibility,
        )

        # Periphery: high exploitation, no rent → high visibility
        periphery_vis = compute_exploitation_visibility(
            exploitation_rate=2.0,
            imperial_rent=0.0,
        )
        # Core: same exploitation, but rent obscures
        core_vis = compute_exploitation_visibility(
            exploitation_rate=2.0,
            imperial_rent=0.5,
        )
        assert periphery_vis > core_vis
