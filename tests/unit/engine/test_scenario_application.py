"""Tests for apply_scenario() function.

RED Phase: These tests will fail initially until apply_scenario() is implemented.
"""

from __future__ import annotations

import pytest

# Imports will fail in RED phase - this is expected
from babylon.engine.scenarios import apply_scenario, create_two_node_scenario
from babylon.models import SimulationConfig, WorldState
from babylon.models.enums import EdgeType
from babylon.models.scenario import ScenarioConfig


class TestApplyScenarioBasics:
    """Test basic apply_scenario() functionality."""

    @pytest.fixture
    def base_scenario(self) -> tuple[WorldState, SimulationConfig]:
        """Create a base two-node scenario for testing."""
        return create_two_node_scenario()

    @pytest.mark.unit
    def test_returns_tuple(self, base_scenario: tuple[WorldState, SimulationConfig]) -> None:
        """Test that apply_scenario returns (WorldState, SimulationConfig) tuple."""
        state, config = base_scenario
        scenario = ScenarioConfig(name="test")

        result = apply_scenario(state, config, scenario)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], WorldState)
        assert isinstance(result[1], SimulationConfig)

    @pytest.mark.unit
    def test_does_not_mutate_original_state(
        self, base_scenario: tuple[WorldState, SimulationConfig]
    ) -> None:
        """Test that apply_scenario does not mutate the original WorldState."""
        state, config = base_scenario
        original_state_dump = state.model_dump()

        scenario = ScenarioConfig(name="test", superwage_multiplier=2.0)
        apply_scenario(state, config, scenario)

        # Original should be unchanged
        assert state.model_dump() == original_state_dump

    @pytest.mark.unit
    def test_does_not_mutate_original_config(
        self, base_scenario: tuple[WorldState, SimulationConfig]
    ) -> None:
        """Test that apply_scenario does not mutate the original SimulationConfig."""
        state, config = base_scenario
        original_config_dump = config.model_dump()

        scenario = ScenarioConfig(name="test", superwage_multiplier=2.0)
        apply_scenario(state, config, scenario)

        # Original should be unchanged
        assert config.model_dump() == original_config_dump


class TestApplyScenarioSuperwageMultiplier:
    """Test superwage_multiplier application in apply_scenario()."""

    @pytest.fixture
    def base_scenario(self) -> tuple[WorldState, SimulationConfig]:
        """Create a base two-node scenario for testing."""
        return create_two_node_scenario(extraction_efficiency=0.8)

    @pytest.mark.unit
    def test_superwage_multiplier_modifies_extraction_efficiency(
        self, base_scenario: tuple[WorldState, SimulationConfig]
    ) -> None:
        """Test that superwage_multiplier multiplies extraction_efficiency in config."""
        state, config = base_scenario
        original_extraction = config.extraction_efficiency

        # Apply 1.5x superwage multiplier
        scenario = ScenarioConfig(name="high_sw", superwage_multiplier=1.5)
        _, new_config = apply_scenario(state, config, scenario)

        # Note: We need to clamp to [0, 1] since extraction_efficiency is a Coefficient
        expected = min(1.0, original_extraction * 1.5)
        assert new_config.extraction_efficiency == expected

    @pytest.mark.unit
    def test_superwage_multiplier_one_no_change(
        self, base_scenario: tuple[WorldState, SimulationConfig]
    ) -> None:
        """Test that superwage_multiplier=1.0 (default) leaves extraction unchanged."""
        state, config = base_scenario
        original_extraction = config.extraction_efficiency

        scenario = ScenarioConfig(name="default")
        _, new_config = apply_scenario(state, config, scenario)

        assert new_config.extraction_efficiency == original_extraction

    @pytest.mark.unit
    def test_low_superwage_multiplier_reduces_extraction(
        self, base_scenario: tuple[WorldState, SimulationConfig]
    ) -> None:
        """Test that superwage_multiplier=0.3 reduces extraction efficiency."""
        state, config = base_scenario
        original_extraction = config.extraction_efficiency

        scenario = ScenarioConfig(name="low_sw", superwage_multiplier=0.3)
        _, new_config = apply_scenario(state, config, scenario)

        expected = original_extraction * 0.3
        assert new_config.extraction_efficiency == pytest.approx(expected, rel=1e-6)


class TestApplyScenarioSolidarityIndex:
    """Test solidarity_index application in apply_scenario()."""

    @pytest.fixture
    def base_scenario_with_solidarity(self) -> tuple[WorldState, SimulationConfig]:
        """Create a scenario with a SOLIDARITY edge for testing."""
        state, config = create_two_node_scenario()

        # Add a SOLIDARITY edge from C001 to C002
        from babylon.models.entities.relationship import Relationship

        solidarity_edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.SOLIDARITY,
            description="Test solidarity edge",
            solidarity_strength=0.0,  # Will be set by apply_scenario
        )

        updated_relationships = list(state.relationships) + [solidarity_edge]
        state = state.model_copy(update={"relationships": updated_relationships})

        return state, config

    @pytest.mark.unit
    def test_solidarity_index_sets_solidarity_strength(
        self, base_scenario_with_solidarity: tuple[WorldState, SimulationConfig]
    ) -> None:
        """Test that solidarity_index sets solidarity_strength on SOLIDARITY edges."""
        state, config = base_scenario_with_solidarity

        scenario = ScenarioConfig(name="high_sol", solidarity_index=0.8)
        new_state, _ = apply_scenario(state, config, scenario)

        # Find the solidarity edge
        solidarity_edges = [
            r for r in new_state.relationships if r.edge_type == EdgeType.SOLIDARITY
        ]
        assert len(solidarity_edges) > 0

        for edge in solidarity_edges:
            assert edge.solidarity_strength == 0.8

    @pytest.mark.unit
    def test_solidarity_index_does_not_affect_exploitation_edges(
        self, base_scenario_with_solidarity: tuple[WorldState, SimulationConfig]
    ) -> None:
        """Test that solidarity_index does not modify EXPLOITATION edges."""
        state, config = base_scenario_with_solidarity

        # Get original exploitation edge strength
        original_exploitation = [
            r for r in state.relationships if r.edge_type == EdgeType.EXPLOITATION
        ][0]

        scenario = ScenarioConfig(name="high_sol", solidarity_index=0.8)
        new_state, _ = apply_scenario(state, config, scenario)

        # Find the exploitation edge
        new_exploitation = [
            r for r in new_state.relationships if r.edge_type == EdgeType.EXPLOITATION
        ][0]

        # Solidarity strength should be unchanged on exploitation edges
        assert new_exploitation.solidarity_strength == original_exploitation.solidarity_strength


class TestApplyScenarioRepressionCapacity:
    """Test repression_capacity application in apply_scenario()."""

    @pytest.fixture
    def base_scenario(self) -> tuple[WorldState, SimulationConfig]:
        """Create a base two-node scenario for testing."""
        return create_two_node_scenario(repression_level=0.5)

    @pytest.mark.unit
    def test_repression_capacity_updates_social_class_repression(
        self, base_scenario: tuple[WorldState, SimulationConfig]
    ) -> None:
        """Test that repression_capacity updates repression_faced on SocialClass entities."""
        state, config = base_scenario

        scenario = ScenarioConfig(name="high_rep", repression_capacity=0.8)
        new_state, _ = apply_scenario(state, config, scenario)

        # Check that at least one entity has updated repression
        for entity in new_state.entities.values():
            assert entity.repression_faced == 0.8

    @pytest.mark.unit
    def test_low_repression_capacity(
        self, base_scenario: tuple[WorldState, SimulationConfig]
    ) -> None:
        """Test that repression_capacity=0.2 sets low repression on entities."""
        state, config = base_scenario

        scenario = ScenarioConfig(name="low_rep", repression_capacity=0.2)
        new_state, _ = apply_scenario(state, config, scenario)

        for entity in new_state.entities.values():
            assert entity.repression_faced == 0.2

    @pytest.mark.unit
    def test_repression_capacity_updates_config_repression_level(
        self, base_scenario: tuple[WorldState, SimulationConfig]
    ) -> None:
        """Test that repression_capacity also updates repression_level in config."""
        state, config = base_scenario

        scenario = ScenarioConfig(name="high_rep", repression_capacity=0.8)
        _, new_config = apply_scenario(state, config, scenario)

        assert new_config.repression_level == 0.8


class TestApplyScenarioCombined:
    """Test combined scenario application effects."""

    @pytest.fixture
    def base_scenario_with_solidarity(self) -> tuple[WorldState, SimulationConfig]:
        """Create a scenario with a SOLIDARITY edge for testing."""
        state, config = create_two_node_scenario(
            extraction_efficiency=0.8,
            repression_level=0.5,
        )

        # Add a SOLIDARITY edge
        from babylon.models.entities.relationship import Relationship

        solidarity_edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.SOLIDARITY,
            description="Test solidarity edge",
            solidarity_strength=0.0,
        )

        updated_relationships = list(state.relationships) + [solidarity_edge]
        state = state.model_copy(update={"relationships": updated_relationships})

        return state, config

    @pytest.mark.unit
    def test_all_modifiers_applied(
        self, base_scenario_with_solidarity: tuple[WorldState, SimulationConfig]
    ) -> None:
        """Test that all three modifiers are applied together."""
        state, config = base_scenario_with_solidarity

        scenario = ScenarioConfig(
            name="all_modifiers",
            superwage_multiplier=1.5,
            solidarity_index=0.8,
            repression_capacity=0.3,
        )
        new_state, new_config = apply_scenario(state, config, scenario)

        # Check superwage multiplier effect on extraction
        expected_extraction = min(1.0, 0.8 * 1.5)  # Clamped
        assert new_config.extraction_efficiency == expected_extraction

        # Check solidarity effect on edges
        solidarity_edges = [
            r for r in new_state.relationships if r.edge_type == EdgeType.SOLIDARITY
        ]
        for edge in solidarity_edges:
            assert edge.solidarity_strength == 0.8

        # Check repression effect on entities
        for entity in new_state.entities.values():
            assert entity.repression_faced == 0.3

        # Check repression effect on config
        assert new_config.repression_level == 0.3

    @pytest.mark.unit
    def test_extreme_stable_scenario(self) -> None:
        """Test 'stable' scenario: High SW + Low Solidarity + High Repression."""
        state, config = create_two_node_scenario()

        scenario = ScenarioConfig(
            name="HighSW_LowSol_HighRep",
            superwage_multiplier=1.5,
            solidarity_index=0.2,
            repression_capacity=0.8,
        )
        new_state, new_config = apply_scenario(state, config, scenario)

        # High extraction, low solidarity, high repression = stable for capital
        assert (
            new_config.extraction_efficiency >= 0.8 * 1.5 or new_config.extraction_efficiency == 1.0
        )
        assert new_config.repression_level == 0.8
        for entity in new_state.entities.values():
            assert entity.repression_faced == 0.8

    @pytest.mark.unit
    def test_extreme_collapse_scenario(self) -> None:
        """Test 'collapse' scenario: Low SW + High Solidarity + Low Repression."""
        state, config = create_two_node_scenario()

        scenario = ScenarioConfig(
            name="LowSW_HighSol_LowRep",
            superwage_multiplier=0.3,
            solidarity_index=0.8,
            repression_capacity=0.2,
        )
        new_state, new_config = apply_scenario(state, config, scenario)

        # Low extraction, high solidarity, low repression = favorable for revolution
        assert new_config.extraction_efficiency == pytest.approx(0.8 * 0.3, rel=1e-6)
        assert new_config.repression_level == 0.2
        for entity in new_state.entities.values():
            assert entity.repression_faced == 0.2


class TestApplyScenarioIntegration:
    """Integration tests for apply_scenario with simulation engine."""

    @pytest.mark.unit
    def test_applied_scenario_produces_valid_step_input(self) -> None:
        """Test that apply_scenario output can be passed to step()."""
        from babylon.engine.simulation_engine import step

        state, config = create_two_node_scenario()
        scenario = ScenarioConfig(
            name="integration_test",
            rent_level=1.2,
            solidarity_index=0.6,
            repression_capacity=0.4,
        )

        new_state, new_config = apply_scenario(state, config, scenario)

        # Should not raise any errors
        result = step(new_state, new_config)

        assert result.tick == new_state.tick + 1
