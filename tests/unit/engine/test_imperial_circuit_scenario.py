"""Unit tests for create_imperial_circuit_scenario function.

RED PHASE TDD: These tests define the expected behavior of the 4-node
Imperial Circuit scenario that fixes the "Robin Hood" bug where super-wages
incorrectly flow to periphery workers instead of labor aristocracy.

The Fix:
    WAGES edge targets C004 (LABOR_ARISTOCRACY), NOT C001 (PERIPHERY_PROLETARIAT)

Topology:
    P_w (C001) --EXPLOITATION--> P_c (C002) --TRIBUTE--> C_b (C003) --WAGES--> C_w (C004)
                                      |                         |
                                 (keeps 15% cut)          CLIENT_STATE
                                      ^-----------------------+
                                      |
                                SOLIDARITY (strength=0.0)
                                      +<------------------------- P_w
"""

import pytest

from babylon.config.defines import EconomyDefines, GameDefines
from babylon.engine.scenarios import create_imperial_circuit_scenario
from babylon.models import SimulationConfig, WorldState
from babylon.models.enums import EdgeType, SocialRole


@pytest.mark.unit
class TestImperialCircuitScenarioStructure:
    """Test that create_imperial_circuit_scenario creates correct structure."""

    def test_returns_worldstate_and_config_tuple(self) -> None:
        """Returns (WorldState, SimulationConfig, GameDefines) tuple."""
        result = create_imperial_circuit_scenario()
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], WorldState)
        assert isinstance(result[1], SimulationConfig)

    def test_creates_four_entities(self) -> None:
        """Scenario must have exactly 4 social class entities."""
        state, _, _ = create_imperial_circuit_scenario()
        assert len(state.entities) == 4

    def test_entity_ids_follow_pattern(self) -> None:
        """Entity IDs: C001-C004 (matches ^C[0-9]{3}$ pattern)."""
        state, _, _ = create_imperial_circuit_scenario()
        expected_ids = {"C001", "C002", "C003", "C004"}
        actual_ids = set(state.entities.keys())
        assert actual_ids == expected_ids


@pytest.mark.unit
class TestImperialCircuitEntityRoles:
    """Test that each entity has the correct SocialRole."""

    def test_periphery_worker_is_periphery_proletariat(self) -> None:
        """C001 (P_w) must have role=PERIPHERY_PROLETARIAT."""
        state, _, _ = create_imperial_circuit_scenario()
        assert state.entities["C001"].role == SocialRole.PERIPHERY_PROLETARIAT

    def test_comprador_is_comprador_bourgeoisie(self) -> None:
        """C002 (P_c) must have role=COMPRADOR_BOURGEOISIE."""
        state, _, _ = create_imperial_circuit_scenario()
        assert state.entities["C002"].role == SocialRole.COMPRADOR_BOURGEOISIE

    def test_core_bourgeoisie_has_correct_role(self) -> None:
        """C003 (C_b) must have role=CORE_BOURGEOISIE."""
        state, _, _ = create_imperial_circuit_scenario()
        assert state.entities["C003"].role == SocialRole.CORE_BOURGEOISIE

    def test_labor_aristocracy_has_correct_role(self) -> None:
        """C004 (C_w) must have role=LABOR_ARISTOCRACY."""
        state, _, _ = create_imperial_circuit_scenario()
        assert state.entities["C004"].role == SocialRole.LABOR_ARISTOCRACY


@pytest.mark.unit
class TestImperialCircuitEdgeTopology:
    """Test that edges have correct source/target direction.

    This is the critical fix: WAGES edge goes to LABOR_ARISTOCRACY, not periphery.
    """

    def test_exploitation_edge_from_pw_to_pc(self) -> None:
        """EXPLOITATION must flow FROM P_w (C001) TO P_c (C002)."""
        state, _, _ = create_imperial_circuit_scenario()
        exploitation_edges = [
            r for r in state.relationships if r.edge_type == EdgeType.EXPLOITATION
        ]
        assert len(exploitation_edges) == 1
        edge = exploitation_edges[0]
        assert edge.source_id == "C001"
        assert edge.target_id == "C002"

    def test_tribute_edge_from_pc_to_cb(self) -> None:
        """TRIBUTE must flow FROM P_c (C002) TO C_b (C003)."""
        state, _, _ = create_imperial_circuit_scenario()
        tribute_edges = [r for r in state.relationships if r.edge_type == EdgeType.TRIBUTE]
        assert len(tribute_edges) == 1
        edge = tribute_edges[0]
        assert edge.source_id == "C002"
        assert edge.target_id == "C003"

    def test_wages_edge_from_cb_to_cw(self) -> None:
        """WAGES must flow FROM C_b (C003) TO C_w (C004)."""
        state, _, _ = create_imperial_circuit_scenario()
        wages_edges = [r for r in state.relationships if r.edge_type == EdgeType.WAGES]
        assert len(wages_edges) == 1
        edge = wages_edges[0]
        assert edge.source_id == "C003"
        assert edge.target_id == "C004"

    def test_wages_edge_NOT_to_periphery_worker(self) -> None:
        """WAGES edge must NOT target PERIPHERY_PROLETARIAT.

        THIS IS THE KEY TEST: The bug we're fixing is that wages were
        going to periphery workers instead of labor aristocracy.
        """
        state, _, _ = create_imperial_circuit_scenario()
        wages_edges = [r for r in state.relationships if r.edge_type == EdgeType.WAGES]
        for edge in wages_edges:
            target_role = state.entities[edge.target_id].role
            assert target_role != SocialRole.PERIPHERY_PROLETARIAT
            assert target_role == SocialRole.LABOR_ARISTOCRACY

    def test_client_state_edge_from_cb_to_pc(self) -> None:
        """CLIENT_STATE must flow FROM C_b (C003) TO P_c (C002)."""
        state, _, _ = create_imperial_circuit_scenario()
        client_state_edges = [
            r for r in state.relationships if r.edge_type == EdgeType.CLIENT_STATE
        ]
        assert len(client_state_edges) == 1
        edge = client_state_edges[0]
        assert edge.source_id == "C003"
        assert edge.target_id == "C002"

    def test_solidarity_edge_from_pw_to_cw(self) -> None:
        """SOLIDARITY must flow FROM P_w (C001) TO C_w (C004)."""
        state, _, _ = create_imperial_circuit_scenario()
        solidarity_edges = [r for r in state.relationships if r.edge_type == EdgeType.SOLIDARITY]
        assert len(solidarity_edges) == 1
        edge = solidarity_edges[0]
        assert edge.source_id == "C001"
        assert edge.target_id == "C004"

    def test_solidarity_starts_at_zero(self) -> None:
        """SOLIDARITY edge strength starts at 0.0 (workers separated)."""
        state, _, _ = create_imperial_circuit_scenario()
        solidarity_edges = [r for r in state.relationships if r.edge_type == EdgeType.SOLIDARITY]
        assert len(solidarity_edges) == 1
        edge = solidarity_edges[0]
        assert edge.solidarity_strength == pytest.approx(0.0)


@pytest.mark.unit
class TestImperialCircuitWealthCalculations:
    """Test that wealth values are correctly derived from parameters."""

    def test_default_periphery_worker_wealth(self) -> None:
        """C001 (P_w) wealth = periphery_wealth (default 0.6, calibrated for P(S|A) > P(S|R))."""
        state, _, _ = create_imperial_circuit_scenario()
        assert state.entities["C001"].wealth == pytest.approx(0.6)

    def test_default_comprador_wealth(self) -> None:
        """C002 (P_c) wealth = periphery_wealth * 2 (default 1.2)."""
        state, _, _ = create_imperial_circuit_scenario()
        assert state.entities["C002"].wealth == pytest.approx(1.2)

    def test_default_core_bourgeoisie_wealth(self) -> None:
        """C003 (C_b) wealth = core_wealth (default 0.9)."""
        state, _, _ = create_imperial_circuit_scenario()
        assert state.entities["C003"].wealth == pytest.approx(0.9)

    def test_default_labor_aristocracy_wealth(self) -> None:
        """C004 (C_w) wealth = core_wealth * 0.2 (default 0.18)."""
        state, _, _ = create_imperial_circuit_scenario()
        assert state.entities["C004"].wealth == pytest.approx(0.18)

    def test_custom_periphery_wealth(self) -> None:
        """Custom periphery_wealth affects C001 and C002."""
        state, _, _ = create_imperial_circuit_scenario(periphery_wealth=0.5)
        assert state.entities["C001"].wealth == pytest.approx(0.5)
        assert state.entities["C002"].wealth == pytest.approx(1.0)

    def test_custom_core_wealth(self) -> None:
        """Custom core_wealth affects C003 and C004."""
        state, _, _ = create_imperial_circuit_scenario(core_wealth=1.0)
        assert state.entities["C003"].wealth == pytest.approx(1.0)
        assert state.entities["C004"].wealth == pytest.approx(0.2)


@pytest.mark.unit
class TestImperialCircuitSubsistenceThresholds:
    """Test vulnerability settings via subsistence thresholds."""

    def test_periphery_worker_high_vulnerability(self) -> None:
        """C001 (P_w) subsistence = 0.3 (high vulnerability)."""
        state, _, _ = create_imperial_circuit_scenario()
        assert state.entities["C001"].subsistence_threshold == pytest.approx(0.3)

    def test_labor_aristocracy_low_vulnerability(self) -> None:
        """C004 (C_w) subsistence = 0.1 (low vulnerability due to super-wages)."""
        state, _, _ = create_imperial_circuit_scenario()
        assert state.entities["C004"].subsistence_threshold == pytest.approx(0.1)


@pytest.mark.unit
class TestImperialCircuitConfiguration:
    """Test that SimulationConfig is correctly populated."""

    def test_default_superwage_multiplier(self) -> None:
        """superwage_multiplier = 1.5 (high PPP) in GameDefines."""
        _, _, defines = create_imperial_circuit_scenario()
        # Paradox Refactor: superwage_multiplier moved from config to defines.economy
        assert defines.economy.superwage_multiplier == pytest.approx(1.5)

    def test_default_comprador_cut(self) -> None:
        """comprador_cut = 0.90 (90%) in GameDefines - calibrated to prevent Comprador Liquidation."""
        _, _, defines = create_imperial_circuit_scenario()
        # Paradox Refactor: comprador_cut moved from config to defines.economy
        assert defines.economy.comprador_cut == pytest.approx(0.90)

    def test_custom_comprador_cut(self) -> None:
        """Custom comprador_cut is applied to GameDefines."""
        _, _, defines = create_imperial_circuit_scenario(comprador_cut=0.20)
        # Paradox Refactor: comprador_cut moved from config to defines.economy
        assert defines.economy.comprador_cut == pytest.approx(0.20)

    def test_default_extraction_efficiency(self) -> None:
        """extraction_efficiency = 0.8 (default alpha) in GameDefines."""
        _, _, defines = create_imperial_circuit_scenario()
        # Paradox Refactor: extraction_efficiency moved from config to defines.economy
        assert defines.economy.extraction_efficiency == pytest.approx(0.8)

    def test_custom_extraction_efficiency(self) -> None:
        """Custom extraction_efficiency is applied to GameDefines."""
        _, _, defines = create_imperial_circuit_scenario(extraction_efficiency=0.5)
        # Paradox Refactor: extraction_efficiency moved from config to defines.economy
        assert defines.economy.extraction_efficiency == pytest.approx(0.5)

    def test_default_repression_level(self) -> None:
        """repression_level = 0.5 (default) in GameDefines."""
        _, _, defines = create_imperial_circuit_scenario()
        # Paradox Refactor: repression_level moved from config to defines.survival
        assert defines.survival.default_repression == pytest.approx(0.5)

    def test_custom_repression_level(self) -> None:
        """Custom repression_level is applied to GameDefines."""
        _, _, defines = create_imperial_circuit_scenario(repression_level=0.8)
        # Paradox Refactor: repression_level moved from config to defines.survival
        assert defines.survival.default_repression == pytest.approx(0.8)


@pytest.mark.unit
@pytest.mark.math
class TestWageCalculationCorrectness:
    """Verify wages are calculated from income flow, not accumulated wealth.

    BUG FIX: The wage calculation was treating super-wages as a wealth tax
    on bourgeoisie accumulated capital instead of a distribution from current
    income flow (tribute). This caused C_b to hemorrhage wealth to C_w.

    Theory: In MLM-TW, super-wages come from extracted imperial rent surplus,
    not from bourgeoisie capital. Wages should be capped at tribute_inflow.
    """

    def test_wages_based_on_tribute_not_wealth(self) -> None:
        """Wages should be percentage of tribute, not percentage of total wealth.

        With correct formula: desired_wages = tribute_inflow * wage_rate
        Core Bourgeoisie keeps (1-rate) of incoming tribute, always positive.

        With buggy formula: desired_wages = bourgeoisie_wealth * wage_rate
        If wealth >> tribute, wages >> tribute, causing net loss.

        Uses base_subsistence=0.0 to isolate wage transfer mechanics from
        subsistence costs (The Calorie Check).
        """
        from babylon.engine.simulation_engine import step

        state, config, _ = create_imperial_circuit_scenario(
            periphery_wealth=0.1,
            core_wealth=0.9,
        )

        # Isolate wage mechanics from subsistence deductions
        no_subsistence_defines = GameDefines(economy=EconomyDefines(base_subsistence=0.0))

        initial_cb = state.entities["C003"].wealth
        assert initial_cb == pytest.approx(0.9), "C_b should start at 0.9"

        # Run one tick
        new_state = step(state, config, defines=no_subsistence_defines)
        final_cb = new_state.entities["C003"].wealth

        # Core Bourgeoisie should NOT lose wealth to wages
        # They should accumulate from tribute (even after paying wages)
        assert final_cb >= initial_cb, (
            f"C_b should accumulate or hold steady, not drain: {initial_cb:.4f} -> {final_cb:.4f}"
        )

    def test_core_bourgeoisie_accumulates_over_time(self) -> None:
        """After 10 ticks, C_b should have more wealth than at start.

        This is the fundamental test for MLM-TW correctness: the Core
        Bourgeoisie extracts value from the periphery and accumulates
        capital, even after paying super-wages to labor aristocracy.

        Uses base_subsistence=0.0 to isolate wage/tribute mechanics from
        subsistence costs (The Calorie Check).
        """
        from babylon.engine.simulation_engine import step

        state, config, _ = create_imperial_circuit_scenario()

        # Isolate wage mechanics from subsistence deductions
        no_subsistence_defines = GameDefines(economy=EconomyDefines(base_subsistence=0.0))

        initial_cb = state.entities["C003"].wealth

        for _ in range(10):
            state = step(state, config, defines=no_subsistence_defines)

        final_cb = state.entities["C003"].wealth
        assert final_cb > initial_cb, (
            f"C_b should accumulate over 10 ticks: {initial_cb:.4f} -> {final_cb:.4f}"
        )

    def test_labor_aristocracy_receives_modest_wages(self) -> None:
        """C_w should receive wages, but not drain C_b's wealth.

        The labor aristocracy should receive super-wages proportional
        to extracted surplus, not proportional to bourgeoisie capital.

        Uses base_subsistence=0.0 to isolate wage transfer mechanics from
        subsistence costs (The Calorie Check).
        """
        from babylon.engine.simulation_engine import step

        state, config, _ = create_imperial_circuit_scenario()
        initial_cw = state.entities["C004"].wealth
        initial_cb = state.entities["C003"].wealth

        # Isolate wage mechanics from subsistence deductions
        no_subsistence_defines = GameDefines(economy=EconomyDefines(base_subsistence=0.0))

        # Run 10 ticks
        for _ in range(10):
            state = step(state, config, defines=no_subsistence_defines)

        final_cw = state.entities["C004"].wealth
        final_cb = state.entities["C003"].wealth

        # C_w should gain some wages
        assert final_cw > initial_cw, "Labor aristocracy should receive wages"

        # But C_b should NOT be drained
        assert final_cb > initial_cb * 0.5, (
            f"C_b should not be drained below 50% of initial: {initial_cb:.4f} -> {final_cb:.4f}"
        )
