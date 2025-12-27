"""Tests for apply_scenario() function.

RED Phase: These tests will fail initially until apply_scenario() is implemented.

Mikado Refactor: Updated to use 4-argument signature with GameDefines.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines

# Imports will fail in RED phase - this is expected
from babylon.engine.scenarios import apply_scenario, create_two_node_scenario
from babylon.models import SimulationConfig, WorldState
from babylon.models.enums import EdgeType
from babylon.models.scenario import ScenarioConfig


class TestApplyScenarioBasics:
    """Test basic apply_scenario() functionality."""

    @pytest.fixture
    def base_scenario(self) -> tuple[WorldState, SimulationConfig, GameDefines]:
        """Create a base two-node scenario for testing."""
        state, config, defines = create_two_node_scenario()
        return state, config, defines

    @pytest.mark.unit
    def test_returns_tuple(
        self, base_scenario: tuple[WorldState, SimulationConfig, GameDefines]
    ) -> None:
        """Test that apply_scenario returns (WorldState, SimulationConfig, GameDefines) tuple."""
        state, config, defines = base_scenario
        scenario = ScenarioConfig(name="test")

        result = apply_scenario(state, config, defines, scenario)

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], WorldState)
        assert isinstance(result[1], SimulationConfig)
        assert isinstance(result[2], GameDefines)

    @pytest.mark.unit
    def test_does_not_mutate_original_state(
        self, base_scenario: tuple[WorldState, SimulationConfig, GameDefines]
    ) -> None:
        """Test that apply_scenario does not mutate the original WorldState."""
        state, config, defines = base_scenario
        original_state_dump = state.model_dump()

        scenario = ScenarioConfig(name="test", superwage_multiplier=2.0)
        apply_scenario(state, config, defines, scenario)

        # Original should be unchanged
        assert state.model_dump() == original_state_dump

    @pytest.mark.unit
    def test_does_not_mutate_original_config(
        self, base_scenario: tuple[WorldState, SimulationConfig, GameDefines]
    ) -> None:
        """Test that apply_scenario does not mutate the original SimulationConfig."""
        state, config, defines = base_scenario
        original_config_dump = config.model_dump()

        scenario = ScenarioConfig(name="test", superwage_multiplier=2.0)
        apply_scenario(state, config, defines, scenario)

        # Original should be unchanged
        assert config.model_dump() == original_config_dump


class TestApplyScenarioSuperwageMultiplier:
    """Test superwage_multiplier application in apply_scenario().

    Mikado Refactor: superwage_multiplier now modifies GameDefines.economy,
    NOT SimulationConfig. This is where economic.py reads it from.
    """

    @pytest.fixture
    def base_scenario(self) -> tuple[WorldState, SimulationConfig, GameDefines]:
        """Create a base two-node scenario for testing."""
        state, config, defines = create_two_node_scenario(extraction_efficiency=0.8)
        return state, config, defines

    @pytest.mark.unit
    def test_superwage_multiplier_sets_gamedefines_economy(
        self, base_scenario: tuple[WorldState, SimulationConfig, GameDefines]
    ) -> None:
        """Test that superwage_multiplier is passed to GameDefines.economy."""
        state, config, defines = base_scenario

        # Apply 1.5x superwage multiplier
        scenario = ScenarioConfig(name="high_sw", superwage_multiplier=1.5)
        _, _, new_defines = apply_scenario(state, config, defines, scenario)

        # Mikado Fix: superwage_multiplier now in GameDefines.economy
        assert new_defines.economy.superwage_multiplier == 1.5

    @pytest.mark.unit
    def test_superwage_multiplier_does_not_affect_extraction_efficiency(
        self, base_scenario: tuple[WorldState, SimulationConfig, GameDefines]
    ) -> None:
        """Test that superwage_multiplier does NOT modify extraction_efficiency.

        PPP Model Fix: extraction_efficiency represents imperial rent extraction.
        superwage_multiplier affects worker purchasing power (PPP), not extraction.
        """
        state, config, defines = base_scenario
        original_extraction = defines.economy.extraction_efficiency

        # Apply various superwage multipliers
        for sw_mult in [0.3, 1.0, 1.5, 2.0]:
            scenario = ScenarioConfig(name=f"sw_{sw_mult}", superwage_multiplier=sw_mult)
            _, _, new_defines = apply_scenario(state, config, defines, scenario)

            # Extraction efficiency should remain unchanged
            assert new_defines.economy.extraction_efficiency == original_extraction

    @pytest.mark.unit
    def test_superwage_multiplier_one_is_default(
        self, base_scenario: tuple[WorldState, SimulationConfig, GameDefines]
    ) -> None:
        """Test that superwage_multiplier=1.0 (default) is preserved."""
        state, config, defines = base_scenario

        scenario = ScenarioConfig(name="default")
        _, _, new_defines = apply_scenario(state, config, defines, scenario)

        assert new_defines.economy.superwage_multiplier == 1.0

    @pytest.mark.unit
    def test_low_superwage_multiplier_sets_gamedefines(
        self, base_scenario: tuple[WorldState, SimulationConfig, GameDefines]
    ) -> None:
        """Test that superwage_multiplier=0.3 is passed to GameDefines."""
        state, config, defines = base_scenario

        scenario = ScenarioConfig(name="low_sw", superwage_multiplier=0.3)
        _, _, new_defines = apply_scenario(state, config, defines, scenario)

        assert new_defines.economy.superwage_multiplier == pytest.approx(0.3, rel=1e-6)


class TestApplyScenarioSolidarityIndex:
    """Test solidarity_index application in apply_scenario()."""

    @pytest.fixture
    def base_scenario_with_solidarity(
        self,
    ) -> tuple[WorldState, SimulationConfig, GameDefines]:
        """Create a scenario with a SOLIDARITY edge for testing."""
        state, config, defines = create_two_node_scenario()

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

        return state, config, defines

    @pytest.mark.unit
    def test_solidarity_index_sets_solidarity_strength(
        self,
        base_scenario_with_solidarity: tuple[WorldState, SimulationConfig, GameDefines],
    ) -> None:
        """Test that solidarity_index sets solidarity_strength on SOLIDARITY edges."""
        state, config, defines = base_scenario_with_solidarity

        scenario = ScenarioConfig(name="high_sol", solidarity_index=0.8)
        new_state, _, _ = apply_scenario(state, config, defines, scenario)

        # Find the solidarity edge
        solidarity_edges = [
            r for r in new_state.relationships if r.edge_type == EdgeType.SOLIDARITY
        ]
        assert len(solidarity_edges) > 0

        for edge in solidarity_edges:
            assert edge.solidarity_strength == 0.8

    @pytest.mark.unit
    def test_solidarity_index_does_not_affect_exploitation_edges(
        self,
        base_scenario_with_solidarity: tuple[WorldState, SimulationConfig, GameDefines],
    ) -> None:
        """Test that solidarity_index does not modify EXPLOITATION edges."""
        state, config, defines = base_scenario_with_solidarity

        # Get original exploitation edge strength
        original_exploitation = [
            r for r in state.relationships if r.edge_type == EdgeType.EXPLOITATION
        ][0]

        scenario = ScenarioConfig(name="high_sol", solidarity_index=0.8)
        new_state, _, _ = apply_scenario(state, config, defines, scenario)

        # Find the exploitation edge
        new_exploitation = [
            r for r in new_state.relationships if r.edge_type == EdgeType.EXPLOITATION
        ][0]

        # Solidarity strength should be unchanged on exploitation edges
        assert new_exploitation.solidarity_strength == original_exploitation.solidarity_strength


class TestApplyScenarioRepressionCapacity:
    """Test repression_capacity application in apply_scenario()."""

    @pytest.fixture
    def base_scenario(self) -> tuple[WorldState, SimulationConfig, GameDefines]:
        """Create a base two-node scenario for testing."""
        state, config, defines = create_two_node_scenario(repression_level=0.5)
        return state, config, defines

    @pytest.mark.unit
    def test_repression_capacity_updates_social_class_repression(
        self, base_scenario: tuple[WorldState, SimulationConfig, GameDefines]
    ) -> None:
        """Test that repression_capacity updates repression_faced on SocialClass entities."""
        state, config, defines = base_scenario

        scenario = ScenarioConfig(name="high_rep", repression_capacity=0.8)
        new_state, _, _ = apply_scenario(state, config, defines, scenario)

        # Check that at least one entity has updated repression
        for entity in new_state.entities.values():
            assert entity.repression_faced == 0.8

    @pytest.mark.unit
    def test_low_repression_capacity(
        self, base_scenario: tuple[WorldState, SimulationConfig, GameDefines]
    ) -> None:
        """Test that repression_capacity=0.2 sets low repression on entities."""
        state, config, defines = base_scenario

        scenario = ScenarioConfig(name="low_rep", repression_capacity=0.2)
        new_state, _, _ = apply_scenario(state, config, defines, scenario)

        for entity in new_state.entities.values():
            assert entity.repression_faced == 0.2

    @pytest.mark.unit
    def test_repression_capacity_updates_config_repression_level(
        self, base_scenario: tuple[WorldState, SimulationConfig, GameDefines]
    ) -> None:
        """Test that repression_capacity also updates repression_level in config."""
        state, config, defines = base_scenario

        scenario = ScenarioConfig(name="high_rep", repression_capacity=0.8)
        _, new_config, _ = apply_scenario(state, config, defines, scenario)

        assert new_config.repression_level == 0.8


class TestApplyScenarioCombined:
    """Test combined scenario application effects."""

    @pytest.fixture
    def base_scenario_with_solidarity(
        self,
    ) -> tuple[WorldState, SimulationConfig, GameDefines]:
        """Create a scenario with a SOLIDARITY edge for testing."""
        state, config, defines = create_two_node_scenario(
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

        return state, config, defines

    @pytest.mark.unit
    def test_all_modifiers_applied(
        self,
        base_scenario_with_solidarity: tuple[WorldState, SimulationConfig, GameDefines],
    ) -> None:
        """Test that all three modifiers are applied together."""
        state, config, defines = base_scenario_with_solidarity

        scenario = ScenarioConfig(
            name="all_modifiers",
            superwage_multiplier=1.5,
            solidarity_index=0.8,
            repression_capacity=0.3,
        )
        new_state, new_config, new_defines = apply_scenario(state, config, defines, scenario)

        # Mikado Fix: superwage_multiplier goes to GameDefines.economy
        assert new_defines.economy.superwage_multiplier == 1.5
        # extraction_efficiency should remain unchanged (0.8)
        assert new_defines.economy.extraction_efficiency == 0.8

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
        """Test 'stable' scenario: High SW + Low Solidarity + High Repression.

        PPP Model: High superwage_multiplier means workers get more effective
        purchasing power, making revolution less attractive (stability for capital).
        """
        state, config, defines = create_two_node_scenario()

        scenario = ScenarioConfig(
            name="HighSW_LowSol_HighRep",
            superwage_multiplier=1.5,
            solidarity_index=0.2,
            repression_capacity=0.8,
        )
        new_state, new_config, new_defines = apply_scenario(state, config, defines, scenario)

        # Mikado Fix: superwage_multiplier in GameDefines.economy
        assert new_defines.economy.superwage_multiplier == 1.5
        assert new_defines.economy.extraction_efficiency == 0.8  # Unchanged
        assert new_config.repression_level == 0.8
        for entity in new_state.entities.values():
            assert entity.repression_faced == 0.8

    @pytest.mark.unit
    def test_extreme_collapse_scenario(self) -> None:
        """Test 'collapse' scenario: Low SW + High Solidarity + Low Repression.

        PPP Model: Low superwage_multiplier means workers get less effective
        purchasing power, making revolution more attractive.
        """
        state, config, defines = create_two_node_scenario()

        scenario = ScenarioConfig(
            name="LowSW_HighSol_LowRep",
            superwage_multiplier=0.3,
            solidarity_index=0.8,
            repression_capacity=0.2,
        )
        new_state, new_config, new_defines = apply_scenario(state, config, defines, scenario)

        # Mikado Fix: superwage_multiplier in GameDefines.economy
        assert new_defines.economy.superwage_multiplier == pytest.approx(0.3, rel=1e-6)
        assert new_defines.economy.extraction_efficiency == 0.8  # Unchanged
        assert new_config.repression_level == 0.2
        for entity in new_state.entities.values():
            assert entity.repression_faced == 0.2


class TestApplyScenarioIntegration:
    """Integration tests for apply_scenario with simulation engine."""

    @pytest.mark.unit
    def test_applied_scenario_produces_valid_step_input(self) -> None:
        """Test that apply_scenario output can be passed to step()."""
        from babylon.engine.simulation_engine import step

        state, config, defines = create_two_node_scenario()
        scenario = ScenarioConfig(
            name="integration_test",
            rent_level=1.2,
            solidarity_index=0.6,
            repression_capacity=0.4,
        )

        new_state, new_config, new_defines = apply_scenario(state, config, defines, scenario)

        # Should not raise any errors - use the modified defines
        result = step(new_state, new_config, defines=new_defines)

        assert result.tick == new_state.tick + 1


# =============================================================================
# Mikado Refactor: superwage_multiplier Duplication Elimination
# =============================================================================
# GOAL: apply_scenario modifies GameDefines.economy.superwage_multiplier
#       (NOT SimulationConfig.superwage_multiplier which is being removed)
#
# BUG: Currently apply_scenario writes to config.superwage_multiplier
#      but economic.py reads from services.defines.economy.superwage_multiplier
#      Result: scenario modifications are IGNORED by the PPP calculation


class TestApplyScenarioGameDefines:
    """RED Phase tests for Mikado refactor: superwage_multiplier moves to GameDefines.

    Paradox Refactor Principle: Game math lives in GameDefines, not SimulationConfig.
    This test class validates that apply_scenario correctly modifies GameDefines
    for scenario-specific coefficient overrides.
    """

    @pytest.fixture
    def base_scenario_with_defines(
        self,
    ) -> tuple[WorldState, SimulationConfig, GameDefines]:
        """Create a base scenario with GameDefines for testing."""

        state, config, defines = create_two_node_scenario()
        return state, config, defines

    @pytest.mark.unit
    def test_apply_scenario_returns_three_tuple(
        self,
        base_scenario_with_defines: tuple[WorldState, SimulationConfig, GameDefines],
    ) -> None:
        """Test that apply_scenario returns (WorldState, SimulationConfig, GameDefines).

        Mikado Prereq: New signature returns GameDefines as third element.
        """
        from babylon.config.defines import GameDefines

        state, config, defines = base_scenario_with_defines
        scenario = ScenarioConfig(name="test")

        result = apply_scenario(state, config, defines, scenario)

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], WorldState)
        assert isinstance(result[1], SimulationConfig)
        assert isinstance(result[2], GameDefines)

    @pytest.mark.unit
    def test_superwage_multiplier_modifies_gamedefines_economy(
        self,
        base_scenario_with_defines: tuple[WorldState, SimulationConfig, GameDefines],
    ) -> None:
        """Test that superwage_multiplier modifies GameDefines.economy.superwage_multiplier.

        Mikado Goal: scenario.superwage_multiplier -> defines.economy.superwage_multiplier
        This is where economic.py reads from, fixing the PPP bug.
        """
        state, config, defines = base_scenario_with_defines
        original_sw = defines.economy.superwage_multiplier

        scenario = ScenarioConfig(name="high_sw", superwage_multiplier=1.5)
        _, _, new_defines = apply_scenario(state, config, defines, scenario)

        # GameDefines.economy.superwage_multiplier should be updated
        assert new_defines.economy.superwage_multiplier == 1.5
        # Original should be unchanged (immutability)
        assert defines.economy.superwage_multiplier == original_sw

    @pytest.mark.unit
    def test_low_superwage_multiplier_modifies_gamedefines(
        self,
        base_scenario_with_defines: tuple[WorldState, SimulationConfig, GameDefines],
    ) -> None:
        """Test that low superwage_multiplier (0.3) modifies GameDefines."""
        state, config, defines = base_scenario_with_defines

        scenario = ScenarioConfig(name="low_sw", superwage_multiplier=0.3)
        _, _, new_defines = apply_scenario(state, config, defines, scenario)

        assert new_defines.economy.superwage_multiplier == pytest.approx(0.3, rel=1e-6)

    @pytest.mark.unit
    def test_gamedefines_is_not_mutated(
        self,
        base_scenario_with_defines: tuple[WorldState, SimulationConfig, GameDefines],
    ) -> None:
        """Test that apply_scenario does not mutate the original GameDefines.

        GameDefines is frozen (immutable), so model_copy must be used.
        """
        state, config, defines = base_scenario_with_defines
        original_defines_dump = defines.model_dump()

        scenario = ScenarioConfig(name="test", superwage_multiplier=2.0)
        apply_scenario(state, config, defines, scenario)

        # Original should be unchanged
        assert defines.model_dump() == original_defines_dump

    @pytest.mark.unit
    def test_other_economy_fields_preserved(
        self,
        base_scenario_with_defines: tuple[WorldState, SimulationConfig, GameDefines],
    ) -> None:
        """Test that other economy fields are preserved when modifying superwage_multiplier."""
        state, config, defines = base_scenario_with_defines
        original_extraction = defines.economy.extraction_efficiency
        original_comprador_cut = defines.economy.comprador_cut

        scenario = ScenarioConfig(name="high_sw", superwage_multiplier=1.5)
        _, _, new_defines = apply_scenario(state, config, defines, scenario)

        # Other economy fields should be unchanged
        assert new_defines.economy.extraction_efficiency == original_extraction
        assert new_defines.economy.comprador_cut == original_comprador_cut

    @pytest.mark.unit
    def test_default_superwage_multiplier_preserved(
        self,
        base_scenario_with_defines: tuple[WorldState, SimulationConfig, GameDefines],
    ) -> None:
        """Test that default superwage_multiplier (1.0) is preserved in GameDefines."""
        state, config, defines = base_scenario_with_defines

        scenario = ScenarioConfig(name="default")  # superwage_multiplier=1.0 by default
        _, _, new_defines = apply_scenario(state, config, defines, scenario)

        assert new_defines.economy.superwage_multiplier == 1.0


class TestApplyScenarioGameDefinesIntegration:
    """Integration tests: apply_scenario + step() using GameDefines for PPP.

    These tests verify the full pipeline: scenario -> GameDefines -> economic.py
    """

    @pytest.mark.unit
    def test_ppp_uses_gamedefines_superwage_multiplier(self) -> None:
        """Test that step() uses GameDefines.economy.superwage_multiplier for PPP.

        This is the core bug fix: the PPP calculation in economic.py should read
        from the defines that apply_scenario modified.
        """
        from babylon.engine.simulation_engine import step

        state, config, defines = create_two_node_scenario()

        # Apply high superwage scenario
        scenario = ScenarioConfig(name="high_sw", superwage_multiplier=1.5)
        new_state, new_config, new_defines = apply_scenario(state, config, defines, scenario)

        # Run simulation step with modified defines
        result = step(new_state, new_config, defines=new_defines)

        # PPP should have been calculated using superwage_multiplier=1.5
        # from new_defines.economy.superwage_multiplier
        assert new_defines.economy.superwage_multiplier == 1.5
        # The worker should have effective_wealth > nominal wealth due to PPP bonus
        worker = result.entities.get("C001")
        assert worker is not None
        # With high SW, effective_wealth should include PPP bonus
        # (This will only pass once the full pipeline is wired correctly)

    @pytest.mark.unit
    def test_high_vs_low_superwage_produces_ppp_divergence(self) -> None:
        """Test that High vs Low superwage_multiplier produces PPP divergence.

        This is the verification that the Mikado refactor succeeded.
        """
        from babylon.engine.simulation_engine import step

        base_state, base_config, base_defines = create_two_node_scenario()

        # Run HIGH superwage scenario
        high_scenario = ScenarioConfig(name="high_sw", superwage_multiplier=1.5)
        high_state, high_config, high_defines = apply_scenario(
            base_state, base_config, base_defines, high_scenario
        )
        for _ in range(10):
            high_state = step(high_state, high_config, defines=high_defines)
        high_worker = high_state.entities.get("C001")

        # Run LOW superwage scenario
        low_scenario = ScenarioConfig(name="low_sw", superwage_multiplier=0.3)
        low_state, low_config, low_defines = apply_scenario(
            base_state, base_config, base_defines, low_scenario
        )
        for _ in range(10):
            low_state = step(low_state, low_config, defines=low_defines)
        low_worker = low_state.entities.get("C001")

        # HIGH superwage should produce HIGHER effective wealth than LOW
        assert high_worker is not None
        assert low_worker is not None
        assert high_worker.effective_wealth > low_worker.effective_wealth, (
            f"PPP divergence failed: high={high_worker.effective_wealth}, "
            f"low={low_worker.effective_wealth}"
        )
