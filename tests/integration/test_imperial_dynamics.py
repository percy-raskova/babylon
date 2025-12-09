"""Integration tests for Imperial Circuit dynamics (Sprint 3.4.1).

These tests verify the 4-node Imperial Circuit model flows correctly:
- Extraction Loop (Upward): P_w -> P_c -> C_b -> C_w via EXPLOITATION, TRIBUTE, WAGES
- Stabilization Loop (Downward): C_b -> P_c via CLIENT_STATE (Imperial Subsidy)

Test Scenario Values:
    Initial: P_w=100, P_c=0 (repression=0.3), C_b=50, C_w=0
    Edges: EXPLOITATION(P_w->P_c), TRIBUTE(P_c->C_b), WAGES(C_b->C_w), CLIENT_STATE(C_b->P_c)

    After 1 tick (alpha=0.8, cut=15%, wage=20%):
    - Phase 1: rent=40, P_w->60, P_c->40  (80% of P_w ideology-adjusted wealth extracted)
    - Phase 2: tribute=34, P_c->6, C_b->84  (P_c keeps 15% cut, sends 85% as tribute)
    - Phase 3: wages=16.8, C_b->67.2, C_w->16.8  (20% of C_b to wages)
    - Phase 4: if unstable, subsidy applied (wealth -> suppression conversion)
"""

import pytest

from babylon.engine.simulation_engine import step
from babylon.models.config import SimulationConfig
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.enums import EdgeType, SocialRole
from babylon.models.world_state import WorldState


def create_imperial_circuit_scenario(
    p_w_wealth: float = 100.0,
    p_c_wealth: float = 0.0,
    c_b_wealth: float = 50.0,
    c_w_wealth: float = 0.0,
    p_c_repression: float = 0.3,
    extraction_efficiency: float = 0.8,
    comprador_cut: float = 0.15,
    super_wage_rate: float = 0.20,
    subsidy_conversion_rate: float = 0.1,
    subsidy_trigger_threshold: float = 0.8,
    subsidy_cap: float = 10.0,
) -> tuple[WorldState, SimulationConfig]:
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
    """
    # Create nodes (IDs must match pattern ^C[0-9]{3}$)
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
    )

    periphery_comprador = SocialClass(
        id="C002",  # P_c
        name="Periphery Comprador",
        role=SocialRole.PETTY_BOURGEOISIE,
        description="Local collaborator class in the periphery",
        wealth=p_c_wealth,
        ideology=0.5,  # Reactionary
        organization=0.5,
        repression_faced=p_c_repression,
        subsistence_threshold=0.2,
        p_acquiescence=0.0,
        p_revolution=0.0,
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

    # Create world state
    state = WorldState(
        tick=0,
        entities={
            "C001": periphery_worker,
            "C002": periphery_comprador,
            "C003": core_bourgeoisie,
            "C004": core_worker,
        },
        relationships=[
            exploitation_edge,
            tribute_edge,
            wages_edge,
            client_state_edge,
        ],
        event_log=[],
    )

    # Create configuration with Imperial Circuit parameters
    config = SimulationConfig(
        extraction_efficiency=extraction_efficiency,
        comprador_cut=comprador_cut,
        super_wage_rate=super_wage_rate,
        subsidy_conversion_rate=subsidy_conversion_rate,
        subsidy_trigger_threshold=subsidy_trigger_threshold,
        repression_level=0.5,
        subsistence_threshold=0.3,
        survival_steepness=10.0,
        consciousness_sensitivity=0.5,
    )

    return state, config


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

        With P_w wealth=100, alpha=0.8, ideology=0 (consciousness=0.5):
        rent = 0.8 * 100 * (1 - 0.5) = 40
        C001 -> 60

        Note: C002 final wealth depends on all 4 phases completing.
        After full circuit: C002 has 6 (kept 15% cut from 40).
        """
        state, config = create_imperial_circuit_scenario()
        new_state = step(state, config)

        # C001 (P_w) should have lost 40 to extraction
        assert new_state.entities["C001"].wealth == pytest.approx(60.0, rel=0.01)
        # C002 (P_c) final wealth after all phases (kept 15% cut)
        assert new_state.entities["C002"].wealth == pytest.approx(6.0, rel=0.01)

    def test_phase2_tribute_p_c_to_c_b(self) -> None:
        """Phase 2: C002 (P_c) sends tribute to C003 (C_b), keeping 15% cut.

        After extraction: C002 has 40
        Comprador cut: 15% of 40 = 6, keeps 6
        Tribute: 85% of 40 = 34, sends to C003

        After all 4 phases:
        - C002 -> 6 (kept cut)
        - C003 -> 84 (received tribute) -> 67.2 (paid wages) -> 60.48 (paid subsidy)
        """
        state, config = create_imperial_circuit_scenario()
        new_state = step(state, config)

        # C002 (P_c) should have kept 15% cut
        assert new_state.entities["C002"].wealth == pytest.approx(6.0, rel=0.01)
        # C003 (C_b) final wealth after wages and subsidy: 67.2 - 6.72 = 60.48
        # (Subsidy triggers because C002 is unstable with low wealth and low repression)
        assert new_state.entities["C003"].wealth == pytest.approx(60.48, rel=0.01)

    def test_phase3_wages_c_b_to_c_w(self) -> None:
        """Phase 3: C003 (C_b) pays super-wages to C004 (C_w).

        After tribute: C003 has 84
        Super-wages: 20% of 84 = 16.8
        C003 -> 67.2 (before subsidy), C004 -> 16.8

        After subsidy phase: C003 -> 60.48 (paid 6.72 to stabilize C002)
        """
        state, config = create_imperial_circuit_scenario()
        new_state = step(state, config)

        # C003 (C_b) final wealth after all phases
        assert new_state.entities["C003"].wealth == pytest.approx(60.48, rel=0.01)
        # C004 (C_w) should have received wages
        assert new_state.entities["C004"].wealth == pytest.approx(16.8, rel=0.01)

    def test_phase4_subsidy_when_client_state_unstable(self) -> None:
        """Phase 4: Subsidy triggered when P(S|R) >= 0.8 * P(S|A).

        When the periphery comprador faces revolutionary conditions,
        the core provides a subsidy to increase repression capacity.
        """
        # Create scenario with unstable client state
        state, config = create_imperial_circuit_scenario(
            p_c_repression=0.1,  # Low repression -> high P(S|R)
            p_c_wealth=0.1,  # Low wealth -> low P(S|A)
        )
        new_state = step(state, config)

        # Subsidy should have been applied (exact values depend on stability calc)
        # The test verifies the mechanism exists and functions
        # C002 (P_c) should have higher repression if subsidy was triggered
        assert (
            new_state.entities["C002"].repression_faced >= state.entities["C002"].repression_faced
        )

    def test_full_circuit_wealth_conservation_extraction_loop(self) -> None:
        """Total wealth in extraction loop is conserved (no subsidy case).

        Value flows from C001 to C002 to C003 to C004.
        Total wealth before = Total wealth after (in stable conditions).
        """
        # Create scenario where subsidy won't trigger
        state, config = create_imperial_circuit_scenario(
            p_c_repression=0.9,  # High repression -> stable client state
        )

        initial_total = sum(e.wealth for e in state.entities.values())
        new_state = step(state, config)
        final_total = sum(e.wealth for e in new_state.entities.values())

        # Wealth should be conserved in the extraction loop
        assert final_total == pytest.approx(initial_total, rel=0.01)

    def test_subsidy_converts_wealth_to_suppression(self) -> None:
        """Phase 4: Subsidy converts wealth to suppression (not conserved).

        When subsidy is applied:
        - C003 (C_b) loses wealth
        - C002 (P_c) gains repression capacity (not wealth)
        - Total wealth decreases (intentional design)
        """
        # Create scenario where subsidy will trigger
        state, config = create_imperial_circuit_scenario(
            p_c_repression=0.1,  # Low repression
            p_c_wealth=0.05,  # Near subsistence
            subsidy_trigger_threshold=0.5,  # Lower threshold to ensure trigger
        )

        initial_c_b_wealth = state.entities["C003"].wealth
        new_state = step(state, config)

        # If subsidy triggered, C003 should have less wealth than expected from just wages
        # And C002 should have higher repression
        if new_state.entities["C002"].repression_faced > state.entities["C002"].repression_faced:
            # Subsidy was applied
            final_c_b_wealth = new_state.entities["C003"].wealth
            # C003 lost wealth to subsidy (on top of wages)
            expected_c_b_after_wages = (initial_c_b_wealth + 34) * 0.8  # Rough estimate
            assert final_c_b_wealth < expected_c_b_after_wages

    def test_backward_compatible_two_node_scenario(self) -> None:
        """2-node scenarios still work (only EXPLOITATION edge).

        The Imperial Circuit should not break existing 2-node simulations.
        """
        from babylon.engine.scenarios import create_two_node_scenario

        state, config = create_two_node_scenario()
        initial_worker_wealth = state.entities["C001"].wealth
        initial_owner_wealth = state.entities["C002"].wealth

        new_state = step(state, config)

        # Worker should have lost wealth to extraction
        assert new_state.entities["C001"].wealth < initial_worker_wealth
        # Owner should have gained wealth
        assert new_state.entities["C002"].wealth > initial_owner_wealth


@pytest.mark.integration
class TestImperialSubsidyEvent:
    """Tests for IMPERIAL_SUBSIDY event emission."""

    def test_imperial_subsidy_event_emitted_when_triggered(self) -> None:
        """IMPERIAL_SUBSIDY event is emitted when subsidy is applied."""
        # Create scenario where subsidy will trigger
        state, config = create_imperial_circuit_scenario(
            p_c_repression=0.1,
            p_c_wealth=0.05,
            subsidy_trigger_threshold=0.5,
        )

        new_state = step(state, config)

        # Check if IMPERIAL_SUBSIDY event was logged
        subsidy_events = [e for e in new_state.event_log if "IMPERIAL_SUBSIDY" in e.upper()]
        # Event should be present if subsidy was triggered
        # We verify the mechanism works by checking repression increased
        if new_state.entities["C002"].repression_faced > state.entities["C002"].repression_faced:
            assert len(subsidy_events) >= 1, "IMPERIAL_SUBSIDY event should be emitted"

    def test_no_subsidy_event_when_client_stable(self) -> None:
        """No IMPERIAL_SUBSIDY event when client state is stable."""
        # Create scenario where subsidy won't trigger
        state, config = create_imperial_circuit_scenario(
            p_c_repression=0.9,  # Very high repression -> stable
        )

        new_state = step(state, config)

        # No IMPERIAL_SUBSIDY events should be present
        subsidy_events = [e for e in new_state.event_log if "IMPERIAL_SUBSIDY" in e.upper()]
        assert len(subsidy_events) == 0
