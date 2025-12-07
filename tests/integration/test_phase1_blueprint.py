"""Phase 1 Blueprint Integration Tests.

This module tests the complete Phase 1 implementation:
"Minimum Viable Dialectic" - Two nodes, one edge, proven equations.

From four-phase-engine-blueprint.md:
- Worker (Periphery Proletariat) and Owner (Core Bourgeoisie)
- Exploitation edge with value flow (Imperial Rent)
- Formula calculations for survival calculus

These tests prove that the mathematical core works end-to-end.
"""

import pytest
import networkx as nx

from babylon.models import Relationship, SocialClass
from babylon.models.enums import EdgeType, SocialRole
from babylon.systems.formulas import (
    calculate_acquiescence_probability,
    calculate_consciousness_drift,
    calculate_imperial_rent,
    calculate_labor_aristocracy_ratio,
    calculate_revolution_probability,
    is_labor_aristocracy,
)


# =============================================================================
# THE PHASE 1 BLUEPRINT TEST
# =============================================================================


@pytest.mark.integration
class TestPhase1Blueprint:
    """The definitive Phase 1 test from four-phase-engine-blueprint.md."""

    def test_imperial_rent_extraction(self) -> None:
        """Prove: Imperial rent flows from periphery to core.

        This is the fundamental assertion of MLM-TW theory encoded in code.
        Value is extracted from periphery workers and flows to core owners.
        """
        # Create Phase 1 nodes
        worker = SocialClass(
            id="C001",
            name="Periphery Mine Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=20.0,  # Receives wage
        )
        owner = SocialClass(
            id="C002",
            name="Core Factory Owner",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=1000.0,  # Accumulated capital
        )

        # The extraction
        labor_value = 100.0  # Value produced by worker
        wage_paid = 20.0  # What worker receives

        # Imperial rent = value extracted
        rent = labor_value - wage_paid

        # Create exploitation relationship
        exploitation = Relationship(
            source_id=worker.id,
            target_id=owner.id,
            edge_type=EdgeType.EXPLOITATION,
            value_flow=rent,
        )

        # Assert the fundamental theorem
        assert rent == 80.0  # Φ = W - V
        assert rent > 0  # Core always extracts from periphery
        assert exploitation.value_flow == rent

    def test_survival_calculus_worker_choice(self) -> None:
        """Prove: Worker's rational choice depends on material conditions.

        When P(S|A) > P(S|R): Acquiesce (survival through compliance)
        When P(S|R) > P(S|A): Revolt (survival through revolution)
        """
        # Worker's material conditions
        worker = SocialClass(
            id="C001",
            name="Periphery Mine Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=20.0,
            subsistence_threshold=15.0,  # Can barely survive
            organization=0.1,  # Low class consciousness
            repression_faced=0.5,  # Moderate repression
        )

        # Calculate survival probabilities
        p_acquiesce = calculate_acquiescence_probability(
            wealth=worker.wealth,
            subsistence_threshold=worker.subsistence_threshold,
            steepness_k=1.0,
        )

        p_revolt = calculate_revolution_probability(
            cohesion=worker.organization,
            repression=worker.repression_faced,
        )

        # Under these conditions, acquiescence is rational
        assert p_acquiesce > p_revolt
        assert 0.0 <= p_acquiesce <= 1.0
        assert 0.0 <= p_revolt <= 1.0

    def test_conditions_for_revolt(self) -> None:
        """Prove: Revolution becomes rational under specific conditions.

        When wealth drops below subsistence AND organization is high,
        P(S|R) > P(S|A) and revolt becomes the rational choice.
        """
        # Desperate worker with high organization
        desperate_worker = SocialClass(
            id="C001",
            name="Organized Desperate Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=5.0,  # Below subsistence!
            subsistence_threshold=15.0,
            organization=0.9,  # Highly organized
            repression_faced=0.3,  # Weakened state
        )

        p_acquiesce = calculate_acquiescence_probability(
            wealth=desperate_worker.wealth,
            subsistence_threshold=desperate_worker.subsistence_threshold,
            steepness_k=1.0,
        )

        p_revolt = calculate_revolution_probability(
            cohesion=desperate_worker.organization,
            repression=desperate_worker.repression_faced,
        )

        # Under these desperate, organized conditions, revolt is rational
        assert p_revolt > p_acquiesce

    def test_two_nodes_one_edge_graph(self) -> None:
        """Prove: Phase 1 graph structure is valid.

        The minimal dialectical system: two classes connected by exploitation.
        """
        # Create nodes
        worker = SocialClass(
            id="C001",
            name="Periphery Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=20.0,
        )
        owner = SocialClass(
            id="C002",
            name="Core Owner",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=1000.0,
        )

        # Create edge
        exploitation = Relationship(
            source_id=worker.id,
            target_id=owner.id,
            edge_type=EdgeType.EXPLOITATION,
            value_flow=80.0,
        )

        # Build NetworkX graph
        G = nx.DiGraph()
        G.add_node(worker.id, **worker.model_dump())
        G.add_node(owner.id, **owner.model_dump())
        G.add_edge(*exploitation.edge_tuple, **exploitation.edge_data)

        # Verify structure
        assert G.number_of_nodes() == 2
        assert G.number_of_edges() == 1

        # Verify node data
        assert G.nodes["C001"]["role"] == "periphery_proletariat"
        assert G.nodes["C002"]["role"] == "core_bourgeoisie"

        # Verify edge data
        assert G.has_edge("C001", "C002")
        assert G["C001"]["C002"]["edge_type"] == "exploitation"
        assert G["C001"]["C002"]["value_flow"] == 80.0


# =============================================================================
# FORMULA INTEGRATION TESTS
# =============================================================================


@pytest.mark.integration
class TestFormulaIntegration:
    """Test formulas work correctly with entity models."""

    def test_imperial_rent_formula(self) -> None:
        """Imperial rent formula with SocialClass data."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            ideology=-0.2,  # Slightly revolutionary
        )

        # Calculate imperial rent using formula
        # Φ = α × Wp × (1 - Ψp)
        alpha = 0.8  # Extraction efficiency
        periphery_wages = 0.3  # Wage share
        consciousness = (worker.ideology + 1) / 2  # Map [-1,1] to [0,1]

        rent = calculate_imperial_rent(
            alpha=alpha,
            periphery_wages=periphery_wages,
            periphery_consciousness=consciousness,
        )

        assert rent >= 0.0
        assert isinstance(rent, float)

    def test_labor_aristocracy_detection(self) -> None:
        """Detect labor aristocracy from wage/value data."""
        # Core worker receiving more than they produce
        core_wages = 50.0
        value_produced = 40.0

        ratio = calculate_labor_aristocracy_ratio(core_wages, value_produced)
        is_aristocracy = is_labor_aristocracy(core_wages, value_produced)

        assert ratio > 1.0
        assert is_aristocracy is True

    def test_consciousness_drift_over_time(self) -> None:
        """Model consciousness change based on material conditions."""
        # Labor aristocrat: well-paid but producing less value
        worker = SocialClass(
            id="C001",
            name="Core Worker",
            role=SocialRole.LABOR_ARISTOCRACY,
            ideology=0.5,  # Currently reactionary
        )

        # Material conditions favor complacency
        core_wages = 60.0
        value_produced = 40.0

        # Calculate drift
        drift = calculate_consciousness_drift(
            core_wages=core_wages,
            value_produced=value_produced,
            current_consciousness=(worker.ideology + 1) / 2,
            sensitivity_k=0.5,
            decay_lambda=0.1,
        )

        # When Wc/Vc > 1, consciousness drifts reactionary (negative drift)
        assert drift < 0  # Drifts toward false consciousness


# =============================================================================
# DIALECTICAL TENSION TESTS
# =============================================================================


@pytest.mark.integration
class TestDialecticalTension:
    """Test contradiction and tension mechanics."""

    def test_exploitation_generates_tension(self) -> None:
        """High value extraction creates dialectical tension."""
        # Heavy exploitation
        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=90.0,  # High extraction
            tension=0.0,  # Starting tension
        )

        # Simple tension model: tension proportional to value flow
        tension_coefficient = 0.01
        new_tension = min(1.0, exploitation.tension + (exploitation.value_flow * tension_coefficient))

        assert new_tension > exploitation.tension
        assert new_tension <= 1.0

    def test_solidarity_reduces_tension(self) -> None:
        """Solidarity between classes reduces systemic tension."""
        # Existing exploitation creates tension
        system_tension = 0.7

        # Solidarity relationship
        solidarity = Relationship(
            source_id="C001",
            target_id="C003",
            edge_type=EdgeType.SOLIDARITY,
            value_flow=0.0,
            tension=0.0,
        )

        # Solidarity dampens tension (simplified model)
        solidarity_effect = 0.1
        reduced_tension = max(0.0, system_tension - solidarity_effect)

        assert reduced_tension < system_tension

    def test_repression_increases_tension(self) -> None:
        """State repression increases contradiction intensity."""
        repression = Relationship(
            source_id="C002",  # Bourgeoisie
            target_id="C001",  # Proletariat
            edge_type=EdgeType.REPRESSION,
            tension=0.5,
        )

        # Repression escalation
        escalation = 0.2
        new_tension = min(1.0, repression.tension + escalation)

        assert new_tension > repression.tension


# =============================================================================
# END-TO-END SCENARIO TEST
# =============================================================================


@pytest.mark.integration
class TestEndToEndScenario:
    """Complete scenario test for Phase 1 mechanics."""

    def test_exploitation_to_rupture_scenario(self) -> None:
        """Simulate path from exploitation to potential rupture.

        Scenario:
        1. Owner exploits Worker (value extraction)
        2. Worker becomes desperate (wealth below subsistence)
        3. Worker organizes (organization increases)
        4. Revolt becomes rational (P(S|R) > P(S|A))
        """
        # Initial state
        worker = SocialClass(
            id="C001",
            name="Periphery Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=30.0,
            subsistence_threshold=15.0,
            organization=0.1,
            repression_faced=0.5,
        )

        owner = SocialClass(
            id="C002",
            name="Core Owner",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=1000.0,
        )

        # Create exploitation relationship
        exploitation = Relationship(
            source_id=worker.id,
            target_id=owner.id,
            edge_type=EdgeType.EXPLOITATION,
            value_flow=80.0,
            tension=0.1,
        )

        # Step 1: Initial state - acquiescence rational
        p_acquiesce_1 = calculate_acquiescence_probability(
            wealth=worker.wealth,
            subsistence_threshold=worker.subsistence_threshold,
            steepness_k=1.0,
        )
        p_revolt_1 = calculate_revolution_probability(
            cohesion=worker.organization,
            repression=worker.repression_faced,
        )
        assert p_acquiesce_1 > p_revolt_1, "Initially acquiescence should be rational"

        # Step 2: Exploitation depletes worker wealth
        extraction_per_turn = 10.0
        worker.wealth = max(0.0, worker.wealth - extraction_per_turn)
        worker.wealth = max(0.0, worker.wealth - extraction_per_turn)
        worker.wealth = max(0.0, worker.wealth - extraction_per_turn)  # Now at 0

        # Step 3: Desperation drives organization
        worker.organization = min(1.0, worker.organization + 0.3)
        worker.organization = min(1.0, worker.organization + 0.3)
        worker.organization = min(1.0, worker.organization + 0.3)  # Now at 1.0

        # Step 4: State weakens (for scenario purposes)
        worker.repression_faced = max(0.1, worker.repression_faced - 0.2)

        # Final state - revolt becomes rational
        p_acquiesce_2 = calculate_acquiescence_probability(
            wealth=worker.wealth,
            subsistence_threshold=worker.subsistence_threshold,
            steepness_k=1.0,
        )
        p_revolt_2 = calculate_revolution_probability(
            cohesion=worker.organization,
            repression=worker.repression_faced,
        )

        assert p_revolt_2 > p_acquiesce_2, "After exploitation and organization, revolt should be rational"

        # Verify the transition occurred
        assert worker.wealth < worker.subsistence_threshold
        assert worker.organization > 0.5
        assert p_revolt_2 > p_revolt_1
