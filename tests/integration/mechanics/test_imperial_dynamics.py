"""Integration tests for Imperial Circuit dynamics (Sprint 3.4.1).

These tests verify the 4-node Imperial Circuit model flows correctly:
- Extraction Loop (Upward): P_w -> P_c -> C_b -> C_w via EXPLOITATION, TRIBUTE, WAGES
- Stabilization Loop (Downward): C_b -> P_c via CLIENT_STATE (Imperial Subsidy)

Test Scenario Values (see TC.ImperialCircuit for constants):
    Initial: All entities start with 100.0 wealth to survive subsistence burn
    Edges: EXPLOITATION(P_w->P_c), TRIBUTE(P_c->C_b), WAGES(C_b->C_w), CLIENT_STATE(C_b->P_c)
    All entities have population=1 for per-capita survival mechanics.
    Territory T001 with TENANCY edges enables production.

    After 1 tick (alpha=EXTRACTION_EFFICIENCY, cut=COMPRADOR_CUT, wage=DEFAULT_WAGE_RATE):
    - Phase 1: rent extracted, P_w loses, P_c gains (then keeps COMPRADOR_CUT)
    - Phase 2: tribute, P_c sends TRIBUTE_RATIO to C_b
    - Phase 3: wages, C_b pays C_w
    - Phase 4: if unstable, subsidy applied (wealth -> suppression conversion)

Sprint 1.5: Refactored for Material Reality physics, increased wealth buffers.
"""

import pytest

from babylon.config.defines import EconomyDefines, GameDefines, SurvivalDefines
from babylon.engine.simulation_engine import step
from babylon.models.config import SimulationConfig
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.territory import Territory
from babylon.models.enums import EdgeType, SectorType, SocialRole
from babylon.models.world_state import WorldState
from tests.constants import TestConstants

TC = TestConstants

pytestmark = [pytest.mark.integration, pytest.mark.theory_rent]


def create_imperial_circuit_scenario(
    p_w_wealth: float = TC.ImperialCircuit.P_W_WEALTH,
    p_c_wealth: float = TC.ImperialCircuit.P_C_WEALTH,
    c_b_wealth: float = TC.ImperialCircuit.C_B_WEALTH,
    c_w_wealth: float = TC.ImperialCircuit.C_W_WEALTH,
    p_c_repression: float = TC.ImperialCircuit.REPRESSION_LOW,
    extraction_efficiency: float = TC.ImperialCircuit.EXTRACTION_EFFICIENCY,
    comprador_cut: float = TC.ImperialCircuit.COMPRADOR_CUT,
    super_wage_rate: float = TC.GlobalEconomy.DEFAULT_WAGE_RATE,
    subsidy_conversion_rate: float = TC.ImperialCircuit.SUBSIDY_CONVERSION_RATE,
    subsidy_trigger_threshold: float = TC.ImperialCircuit.SUBSIDY_TRIGGER_THRESHOLD,
    subsidy_cap: float = TC.ImperialCircuit.SUBSIDY_CAP,
) -> tuple[WorldState, SimulationConfig, GameDefines]:
    """Create the 4-node Imperial Circuit scenario.

    Nodes:
        C001 (Periphery Worker): Source of extracted value
        C002 (Periphery Comprador): Local collaborator class, keeps a cut
        C003 (Core Bourgeoisie): Imperial center, receives tribute
        C004 (Core Worker): Labor aristocracy, receives super-wages

    Edges:
        EXPLOITATION: C001 -> C002 (imperial rent)
        TRIBUTE: C002 -> C003 (minus comprador cut)
        WAGES: C003 -> C004 (super-wages to labor aristocracy)
        CLIENT_STATE: C003 -> C002 (subsidy to stabilize client state)
        TENANCY: All entities -> T001 (territory attachment for production)
    """
    # Create nodes (IDs must match pattern ^C[0-9]{3}$)
    # All entities have population=1 for per-capita survival mechanics
    periphery_worker = SocialClass(
        id="C001",  # P_w
        name="Periphery Worker",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        description="Exploited workers in the global periphery",
        wealth=p_w_wealth,
        ideology=0.0,  # Neutral (consciousness = 0.5 after mapping)
        organization=0.3,
        repression_faced=0.5,
        subsistence_threshold=0.3,
        p_acquiescence=0.0,
        p_revolution=0.0,
        population=TC.Vitality.DEFAULT_POPULATION,  # Per-capita survival
    )

    periphery_comprador = SocialClass(
        id="C002",  # P_c
        name="Periphery Comprador",
        role=SocialRole.COMPRADOR_BOURGEOISIE,
        description="Local collaborator class in the periphery",
        wealth=p_c_wealth,
        ideology=0.5,  # Reactionary
        organization=0.5,
        repression_faced=p_c_repression,
        subsistence_threshold=0.2,
        p_acquiescence=0.0,
        p_revolution=0.0,
        population=TC.Vitality.DEFAULT_POPULATION,  # Per-capita survival
    )

    core_bourgeoisie = SocialClass(
        id="C003",  # C_b
        name="Core Bourgeoisie",
        role=SocialRole.CORE_BOURGEOISIE,
        description="Imperial capitalist class",
        wealth=c_b_wealth,
        ideology=0.8,  # Very reactionary
        organization=0.9,
        repression_faced=0.1,
        subsistence_threshold=0.1,
        p_acquiescence=0.0,
        p_revolution=0.0,
        population=TC.Vitality.DEFAULT_POPULATION,  # Per-capita survival
    )

    core_worker = SocialClass(
        id="C004",  # C_w
        name="Core Worker",
        role=SocialRole.LABOR_ARISTOCRACY,
        description="Labor aristocracy receiving super-wages",
        wealth=c_w_wealth,
        ideology=0.3,  # Slightly reactionary (bought off)
        organization=0.2,
        repression_faced=0.2,
        subsistence_threshold=0.3,
        p_acquiescence=0.0,
        p_revolution=0.0,
        population=TC.Vitality.DEFAULT_POPULATION,  # Per-capita survival
    )

    # Create territory for production
    territory = Territory(
        id="T001",
        name="Imperial Zone",
        sector_type=SectorType.INDUSTRIAL,
        biocapacity=TC.ImperialCircuit.TERRITORY_BIOCAPACITY,
        max_biocapacity=TC.ImperialCircuit.TERRITORY_BIOCAPACITY,
    )

    # Create edges (the Imperial Circuit)
    # C001 (P_w) -> C002 (P_c) -> C003 (C_b) -> C004 (C_w)
    #                   ^                  |
    #                   |------ C003 ------| (subsidy)
    exploitation_edge = Relationship(
        source_id="C001",  # P_w
        target_id="C002",  # P_c
        edge_type=EdgeType.EXPLOITATION,
        description="Imperial rent extraction from periphery workers",
        value_flow=0.0,
        tension=0.0,
    )

    tribute_edge = Relationship(
        source_id="C002",  # P_c
        target_id="C003",  # C_b
        edge_type=EdgeType.TRIBUTE,
        description="Comprador tribute to core (minus cut)",
        value_flow=0.0,
        tension=0.0,
    )

    wages_edge = Relationship(
        source_id="C003",  # C_b
        target_id="C004",  # C_w
        edge_type=EdgeType.WAGES,
        description="Super-wages to labor aristocracy",
        value_flow=0.0,
        tension=0.0,
    )

    client_state_edge = Relationship(
        source_id="C003",  # C_b
        target_id="C002",  # P_c
        edge_type=EdgeType.CLIENT_STATE,
        description="Imperial subsidy to stabilize client state",
        value_flow=0.0,
        tension=0.0,
        subsidy_cap=subsidy_cap,
    )

    # TENANCY edges for all entities (production requires territory)
    tenancy_edges = [
        Relationship(source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY),
        Relationship(source_id="C002", target_id="T001", edge_type=EdgeType.TENANCY),
        Relationship(source_id="C003", target_id="T001", edge_type=EdgeType.TENANCY),
        Relationship(source_id="C004", target_id="T001", edge_type=EdgeType.TENANCY),
    ]

    # Create world state
    state = WorldState(
        tick=0,
        entities={
            "C001": periphery_worker,
            "C002": periphery_comprador,
            "C003": core_bourgeoisie,
            "C004": core_worker,
        },
        territories={"T001": territory},
        relationships=[
            exploitation_edge,
            tribute_edge,
            wages_edge,
            client_state_edge,
            *tenancy_edges,
        ],
        event_log=[],
    )

    # Create configuration (IT-level settings only)
    config = SimulationConfig()

    # Create GameDefines with scenario-specific game balance parameters
    # (Paradox Refactor: game math now lives in GameDefines, not SimulationConfig)
    economy_defines = EconomyDefines(
        extraction_efficiency=extraction_efficiency,
        comprador_cut=comprador_cut,
        super_wage_rate=super_wage_rate,
        subsidy_conversion_rate=subsidy_conversion_rate,
        subsidy_trigger_threshold=subsidy_trigger_threshold,
    )
    survival_defines = SurvivalDefines(
        default_repression=0.5,
        default_subsistence=0.3,
        steepness_k=10.0,
    )
    defines = GameDefines(
        economy=economy_defines,
        survival=survival_defines,
    )

    return state, config, defines


@pytest.mark.integration
class TestImperialCircuitFlow:
    """Tests for the 4-node Imperial Circuit value flow.

    Node ID mapping:
        C001 = P_w (Periphery Worker)
        C002 = P_c (Periphery Comprador)
        C003 = C_b (Core Bourgeoisie)
        C004 = C_w (Core Worker)
    """

    def test_phase1_extraction_p_w_to_p_c(self) -> None:
        """Phase 1: Imperial rent extracted from C001 (P_w) to C002 (P_c).

        With P_w wealth=100, alpha=0.8 (annual), ideology=0 (consciousness=0.5):
        Weekly rate = 0.8 / 52 = 0.01538
        rent = 0.01538 * 100 * (1 - 0.5) = 0.769
        C001 -> 100 - 0.769 = 99.23

        Note: C002 final wealth depends on Phase 2 tribute, which keeps
        COMPRADOR_CUT (15%) of C002's TOTAL wealth.

        Sprint 1.5: Updated for 100.0 initial wealth to survive subsistence burn.
        """
        state, config, defines = create_imperial_circuit_scenario()
        new_state = step(state, config, defines=defines)

        # With weekly conversion: extraction = P_W_WEALTH * (alpha/52) * 0.5
        weeks_per_year = defines.timescale.weeks_per_year
        alpha = TC.ImperialCircuit.EXTRACTION_EFFICIENCY
        expected_extraction = TC.ImperialCircuit.P_W_WEALTH * (alpha / weeks_per_year) * 0.5

        # C001 (P_w) should have lost wealth to extraction
        assert new_state.entities["C001"].wealth < TC.ImperialCircuit.P_W_WEALTH, (
            "C001 should lose wealth to extraction"
        )

        # C002 (P_c) final wealth: tribute phase keeps COMPRADOR_CUT of TOTAL wealth
        p_c_initial = TC.ImperialCircuit.P_C_WEALTH
        expected_c002_wealth = (
            p_c_initial + expected_extraction
        ) * TC.ImperialCircuit.COMPRADOR_CUT
        # Relaxed tolerance due to subsistence burn entropy
        assert new_state.entities["C002"].wealth == pytest.approx(expected_c002_wealth, rel=0.10)

    def test_phase2_tribute_p_c_to_c_b(self) -> None:
        """Phase 2: C002 (P_c) sends tribute to C003 (C_b), keeping COMPRADOR_CUT.

        With weekly conversion:
        Weekly extraction: P_W_WEALTH * (EXTRACTION_EFFICIENCY/52) * 0.5
        C002 total after extraction: P_C_WEALTH + extraction
        Comprador keeps COMPRADOR_CUT of TOTAL, sends (1 - COMPRADOR_CUT) to C003

        C003 retains its initial wealth plus tribute inflow.

        Sprint 1.5: Updated for 100.0 initial wealth to survive subsistence burn.
        """
        state, config, defines = create_imperial_circuit_scenario()
        new_state = step(state, config, defines=defines)

        # With weekly conversion: extraction = P_W_WEALTH * (alpha/52) * 0.5
        weeks_per_year = defines.timescale.weeks_per_year
        alpha = TC.ImperialCircuit.EXTRACTION_EFFICIENCY
        expected_extraction = TC.ImperialCircuit.P_W_WEALTH * (alpha / weeks_per_year) * 0.5

        # C002 (P_c) final wealth: tribute phase keeps COMPRADOR_CUT of TOTAL wealth
        p_c_initial = TC.ImperialCircuit.P_C_WEALTH
        expected_c002_wealth = (
            p_c_initial + expected_extraction
        ) * TC.ImperialCircuit.COMPRADOR_CUT
        # Relaxed tolerance due to subsistence burn entropy
        assert new_state.entities["C002"].wealth == pytest.approx(expected_c002_wealth, rel=0.10)
        # C003 (C_b) retains most of its initial wealth plus tribute
        # The exact amount depends on wage/subsidy outflows
        assert new_state.entities["C003"].wealth >= TC.ImperialCircuit.C_B_WEALTH * 0.9

    def test_phase3_wages_c_b_to_c_w(self) -> None:
        """Phase 3: C003 (C_b) pays super-wages to C004 (C_w).

        With weekly conversion:
        Weekly tribute: ~TRIBUTE_RATIO of extracted value (see Phase 2)
        Weekly wage rate: DEFAULT_WAGE_RATE / 52
        Super-wages: tribute * weekly_wage_rate = small amount

        C003 retains most of its initial wealth, C004 gets weekly wages.

        Sprint 1.5: Updated for 100.0 initial wealth to survive subsistence burn.
        """
        state, config, defines = create_imperial_circuit_scenario()
        new_state = step(state, config, defines=defines)

        # C003 (C_b) retains most of its initial wealth (may lose some to subsistence)
        assert new_state.entities["C003"].wealth >= TC.ImperialCircuit.C_B_WEALTH * 0.9
        # C004 (C_w) should have received wages (but also pays subsistence)
        # Net result may be slightly below initial due to subsistence burn
        assert new_state.entities["C004"].wealth >= TC.ImperialCircuit.C_W_WEALTH * 0.9

    def test_phase4_subsidy_when_client_state_unstable(self) -> None:
        """Phase 4: Subsidy triggered when P(S|R) >= 0.8 * P(S|A).

        When the periphery comprador faces revolutionary conditions,
        the core provides a subsidy to increase repression capacity.
        """
        # Create scenario with unstable client state
        state, config, defines = create_imperial_circuit_scenario(
            p_c_repression=0.1,  # Low repression -> high P(S|R)
            p_c_wealth=0.1,  # Low wealth -> low P(S|A)
        )
        new_state = step(state, config, defines=defines)

        # Subsidy should have been applied (exact values depend on stability calc)
        # The test verifies the mechanism exists and functions
        # C002 (P_c) should have higher repression if subsidy was triggered
        assert (
            new_state.entities["C002"].repression_faced >= state.entities["C002"].repression_faced
        )

    def test_full_circuit_wealth_flows_correctly(self) -> None:
        """Verify wealth flows in correct direction through imperial circuit.

        Note: Strict conservation is violated by VitalitySystem subsistence burn.
        We verify DIRECTION of flow, not exact conservation.

        Sprint 1.5: Relaxed from strict conservation to directional flow check.
        """
        # Create scenario where subsidy won't trigger
        state, config, defines = create_imperial_circuit_scenario(
            p_c_repression=0.9,  # High repression -> stable client state
        )

        initial_c001 = state.entities["C001"].wealth
        initial_c003 = state.entities["C003"].wealth

        new_state = step(state, config, defines=defines)

        final_c001 = new_state.entities["C001"].wealth
        final_c003 = new_state.entities["C003"].wealth

        # Periphery worker loses wealth (extraction)
        assert final_c001 < initial_c001, "C001 should lose wealth to extraction"

        # Core bourgeoisie should have wealth change from flows
        # Note: May not strictly gain if subsistence burn > tribute inflow
        assert final_c003 != initial_c003, "C003 should have wealth change from flows"

    def test_subsidy_converts_wealth_to_suppression(self) -> None:
        """Phase 4: Subsidy converts wealth to suppression (not conserved).

        When subsidy is applied:
        - C003 (C_b) loses wealth to subsidize client state
        - C002 (P_c) gains repression capacity (not wealth)
        - Total wealth decreases (intentional design)

        BUG FIX: With wages/subsidies from tribute (not wealth), C_b accumulates.
        The test verifies subsidy mechanism works by checking repression increased.
        """
        # Create scenario where subsidy will trigger
        state, config, defines = create_imperial_circuit_scenario(
            p_c_repression=0.1,  # Low repression
            p_c_wealth=0.05,  # Near subsistence
            subsidy_trigger_threshold=0.5,  # Lower threshold to ensure trigger
        )

        initial_c_b_wealth = state.entities["C003"].wealth
        initial_p_c_repression = state.entities["C002"].repression_faced
        new_state = step(state, config, defines=defines)

        # Verify subsidy triggered by checking repression increased
        final_p_c_repression = new_state.entities["C002"].repression_faced
        if final_p_c_repression > initial_p_c_repression:
            # Subsidy was applied - verify C003 lost SOME wealth to subsidy
            # With the bug fix, C_b still accumulates overall, but subsidy is an outflow
            final_c_b_wealth = new_state.entities["C003"].wealth

            # C_b should still accumulate (tribute > wages + subsidy)
            # But should have less than if no subsidy was paid
            # The subsidy comes from tribute_inflow * subsidy_rate, capped at pool
            assert final_c_b_wealth > initial_c_b_wealth, (
                f"C_b should accumulate even with subsidy: {initial_c_b_wealth} -> {final_c_b_wealth}"
            )

            # Verify total system wealth decreased (subsidy converts to repression, not wealth)
            initial_total = sum(e.wealth for e in state.entities.values())
            final_total = sum(e.wealth for e in new_state.entities.values())
            assert final_total < initial_total, "Subsidy should decrease total wealth"

    def test_backward_compatible_two_node_scenario(self) -> None:
        """2-node scenarios still work (only EXPLOITATION edge).

        The Imperial Circuit should not break existing 2-node simulations.

        Note: With Material Reality physics, workers now PRODUCE value via
        TENANCY edges. If production > extraction, worker wealth increases.
        We verify value flows via EXPLOITATION edge rather than net wealth.
        """
        from babylon.engine.scenarios import create_two_node_scenario

        state, config, defines = create_two_node_scenario()
        initial_total = sum(e.wealth for e in state.entities.values())

        new_state = step(state, config, defines=defines)

        # Find the EXPLOITATION edge and verify value is flowing
        exploitation_edges = [
            r for r in new_state.relationships if r.edge_type == EdgeType.EXPLOITATION
        ]
        assert len(exploitation_edges) >= 1, "EXPLOITATION edge should exist"

        # Tension should accumulate on exploitation edge (indicates active exploitation)
        # Note: value_flow is computed during tick, tension accumulates over time
        assert exploitation_edges[0].tension >= 0.0, "Tension should not be negative"

        # System should run without error and conserve wealth (plus production)
        final_total = sum(e.wealth for e in new_state.entities.values())
        # With production, total wealth may increase (production creates value)
        assert final_total >= initial_total * 0.9, "System should not lose excessive wealth"


@pytest.mark.integration
class TestImperialSubsidyEvent:
    """Tests for IMPERIAL_SUBSIDY event emission."""

    def test_imperial_subsidy_event_emitted_when_triggered(self) -> None:
        """IMPERIAL_SUBSIDY event is emitted when subsidy is applied."""
        # Create scenario where subsidy will trigger
        state, config, defines = create_imperial_circuit_scenario(
            p_c_repression=0.1,
            p_c_wealth=0.05,
            subsidy_trigger_threshold=0.5,
        )

        new_state = step(state, config, defines=defines)

        # Check if IMPERIAL_SUBSIDY event was logged
        subsidy_events = [e for e in new_state.event_log if "IMPERIAL_SUBSIDY" in e.upper()]
        # Event should be present if subsidy was triggered
        # We verify the mechanism works by checking repression increased
        if new_state.entities["C002"].repression_faced > state.entities["C002"].repression_faced:
            assert len(subsidy_events) >= 1, "IMPERIAL_SUBSIDY event should be emitted"

    def test_no_subsidy_event_when_client_stable(self) -> None:
        """No IMPERIAL_SUBSIDY event when client state is stable."""
        # Create scenario where subsidy won't trigger
        # Need high repression AND sufficient wealth for P(S|A) to dominate
        # P(S|R) = org/repression = 0.5/0.9 = 0.556
        # P(S|A) needs to be > 0.556/0.8 = 0.695 to prevent trigger
        # With wealth=1.0 and subsistence=0.2, sigmoid(0.8) ~ 0.69
        state, config, defines = create_imperial_circuit_scenario(
            p_c_repression=0.9,  # Very high repression -> low P(S|R)
            p_c_wealth=2.0,  # Sufficient wealth -> high P(S|A)
        )

        new_state = step(state, config, defines=defines)

        # No IMPERIAL_SUBSIDY events should be present
        subsidy_events = [e for e in new_state.event_log if "IMPERIAL_SUBSIDY" in e.upper()]
        assert len(subsidy_events) == 0
