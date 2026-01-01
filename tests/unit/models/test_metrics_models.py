"""Tests for babylon.models.metrics.

TDD RED Phase: These tests define the contract for MetricsCollector data models.
All tests should FAIL until the GREEN phase implements the models.

The metrics models capture simulation state for analysis and visualization:
- EntityMetrics: Per-entity snapshot (wealth, consciousness, survival probabilities)
- EdgeMetrics: Per-edge snapshot (tension, value flows, solidarity)
- TickMetrics: Complete tick snapshot (all entities, all edges, global state)
- SweepSummary: Aggregated statistics across a simulation run

These models mirror the data structures in tools/parameter_analysis.py
but with proper Pydantic validation for dashboard integration.

TDD GREEN Phase: All tests pass with implementation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from tests.constants import TestConstants

from babylon.models.metrics import (
    EdgeMetrics,
    EntityMetrics,
    SweepSummary,
    TickMetrics,
)

TC = TestConstants

# TDD GREEN phase - all tests now pass with implementation


# =============================================================================
# ENTITY METRICS TESTS
# =============================================================================


@pytest.mark.math
class TestEntityMetrics:
    """Tests for EntityMetrics model.

    EntityMetrics captures a snapshot of a single entity's state at a tick.
    It includes wealth, consciousness, and survival probabilities.
    """

    def test_can_instantiate_with_all_fields(self) -> None:
        """EntityMetrics accepts all required fields.

        Expected fields (from parameter_analysis.py collect_tick_data):
        - wealth: Currency >= 0
        - consciousness: Probability [0, 1] (class consciousness)
        - national_identity: Probability [0, 1]
        - agitation: Probability [0, 1]
        - p_acquiescence: Probability [0, 1]
        - p_revolution: Probability [0, 1]
        - organization: Probability [0, 1]
        """
        entity = EntityMetrics(
            wealth=0.5,
            consciousness=0.3,
            national_identity=0.2,
            agitation=0.1,
            p_acquiescence=0.8,
            p_revolution=0.2,
            organization=0.15,
        )
        assert entity.wealth == 0.5
        assert entity.consciousness == 0.3
        assert entity.national_identity == 0.2
        assert entity.agitation == 0.1
        assert entity.p_acquiescence == 0.8
        assert entity.p_revolution == 0.2
        assert entity.organization == 0.15

    def test_wealth_must_be_non_negative(self) -> None:
        """Wealth uses Currency type constraint (>= 0)."""
        with pytest.raises(ValidationError):
            EntityMetrics(
                wealth=-0.1,  # Invalid: negative
                consciousness=0.3,
                national_identity=0.2,
                agitation=0.1,
                p_acquiescence=0.8,
                p_revolution=0.2,
                organization=0.15,
            )

    def test_consciousness_must_be_probability(self) -> None:
        """Class consciousness is bounded [0, 1]."""
        # Test upper bound
        with pytest.raises(ValidationError):
            EntityMetrics(
                wealth=0.5,
                consciousness=1.5,  # Invalid: > 1.0
                national_identity=0.2,
                agitation=0.1,
                p_acquiescence=0.8,
                p_revolution=0.2,
                organization=0.15,
            )
        # Test lower bound
        with pytest.raises(ValidationError):
            EntityMetrics(
                wealth=0.5,
                consciousness=-0.1,  # Invalid: < 0.0
                national_identity=0.2,
                agitation=0.1,
                p_acquiescence=0.8,
                p_revolution=0.2,
                organization=0.15,
            )

    def test_p_acquiescence_must_be_probability(self) -> None:
        """P(S|A) is bounded [0, 1]."""
        with pytest.raises(ValidationError):
            EntityMetrics(
                wealth=0.5,
                consciousness=0.3,
                national_identity=0.2,
                agitation=0.1,
                p_acquiescence=1.5,  # Invalid: > 1.0
                p_revolution=0.2,
                organization=0.15,
            )

    def test_p_revolution_must_be_probability(self) -> None:
        """P(S|R) is bounded [0, 1]."""
        with pytest.raises(ValidationError):
            EntityMetrics(
                wealth=0.5,
                consciousness=0.3,
                national_identity=0.2,
                agitation=0.1,
                p_acquiescence=0.8,
                p_revolution=1.5,  # Invalid: > 1.0
                organization=0.15,
            )

    def test_organization_must_be_probability(self) -> None:
        """Organization level is bounded [0, 1]."""
        with pytest.raises(ValidationError):
            EntityMetrics(
                wealth=0.5,
                consciousness=0.3,
                national_identity=0.2,
                agitation=0.1,
                p_acquiescence=0.8,
                p_revolution=0.2,
                organization=-0.1,  # Invalid: < 0.0
            )

    def test_model_is_frozen(self) -> None:
        """EntityMetrics should be immutable (frozen=True)."""
        entity = EntityMetrics(
            wealth=0.5,
            consciousness=0.3,
            national_identity=0.2,
            agitation=0.1,
            p_acquiescence=0.8,
            p_revolution=0.2,
            organization=0.15,
        )
        with pytest.raises((ValidationError, AttributeError)):
            entity.wealth = 1.0  # type: ignore[misc]

    def test_accepts_boundary_values(self) -> None:
        """All boundary values (0.0, 1.0) are valid."""
        entity = EntityMetrics(
            wealth=0.0,  # Minimum
            consciousness=0.0,
            national_identity=0.0,
            agitation=0.0,
            p_acquiescence=1.0,  # Maximum
            p_revolution=1.0,
            organization=1.0,
        )
        assert entity.wealth == 0.0
        assert entity.p_acquiescence == 1.0

    def test_serializes_to_json(self) -> None:
        """EntityMetrics serializes to JSON correctly."""
        entity = EntityMetrics(
            wealth=0.5,
            consciousness=0.3,
            national_identity=0.2,
            agitation=0.1,
            p_acquiescence=0.8,
            p_revolution=0.2,
            organization=0.15,
        )
        json_str = entity.model_dump_json()
        assert "0.5" in json_str  # wealth
        assert "0.3" in json_str  # consciousness


# =============================================================================
# EDGE METRICS TESTS
# =============================================================================


@pytest.mark.math
class TestEdgeMetrics:
    """Tests for EdgeMetrics model.

    EdgeMetrics captures relationship edge data at a tick.
    It includes tension, value flows, and solidarity strength.
    """

    def test_can_instantiate_with_all_fields(self) -> None:
        """EdgeMetrics accepts all edge-related fields.

        Expected fields (from parameter_analysis.py collect_tick_data):
        - exploitation_tension: Probability [0, 1]
        - exploitation_rent: Currency >= 0 (value_flow on EXPLOITATION)
        - tribute_flow: Currency >= 0 (value_flow on TRIBUTE)
        - wages_paid: Currency >= 0 (value_flow on WAGES)
        - solidarity_strength: Probability [0, 1]
        """
        edges = EdgeMetrics(
            exploitation_tension=TC.Probability.MIDPOINT,
            exploitation_rent=TC.Wealth.DEFAULT_WEALTH,
            tribute_flow=TC.RevolutionaryFinance.DEFAULT_WAR_CHEST,
            wages_paid=TC.RevolutionaryFinance.DUES_INCOME,
            solidarity_strength=TC.Probability.LOW,
        )
        assert edges.exploitation_tension == TC.Probability.MIDPOINT
        assert edges.exploitation_rent == TC.Wealth.DEFAULT_WEALTH
        assert edges.tribute_flow == TC.RevolutionaryFinance.DEFAULT_WAR_CHEST
        assert edges.wages_paid == TC.RevolutionaryFinance.DUES_INCOME
        assert edges.solidarity_strength == TC.Probability.LOW

    def test_tension_must_be_probability(self) -> None:
        """Exploitation tension is bounded [0, 1]."""
        with pytest.raises(ValidationError):
            EdgeMetrics(
                exploitation_tension=1.5,  # Invalid: > 1.0
                exploitation_rent=10.0,
                tribute_flow=5.0,
                wages_paid=3.0,
                solidarity_strength=0.2,
            )

    def test_value_flows_must_be_non_negative(self) -> None:
        """Value flows use Currency type (>= 0)."""
        with pytest.raises(ValidationError):
            EdgeMetrics(
                exploitation_tension=0.5,
                exploitation_rent=-1.0,  # Invalid: negative
                tribute_flow=5.0,
                wages_paid=3.0,
                solidarity_strength=0.2,
            )

    def test_solidarity_strength_must_be_probability(self) -> None:
        """Solidarity strength is bounded [0, 1]."""
        with pytest.raises(ValidationError):
            EdgeMetrics(
                exploitation_tension=0.5,
                exploitation_rent=10.0,
                tribute_flow=5.0,
                wages_paid=3.0,
                solidarity_strength=1.5,  # Invalid: > 1.0
            )

    def test_all_fields_have_defaults(self) -> None:
        """EdgeMetrics should allow empty construction with defaults of 0.0.

        This matches the behavior in collect_tick_data where edge columns
        are initialized with 0.0 defaults.
        """
        edges = EdgeMetrics()
        assert edges.exploitation_tension == 0.0
        assert edges.exploitation_rent == 0.0
        assert edges.tribute_flow == 0.0
        assert edges.wages_paid == 0.0
        assert edges.solidarity_strength == 0.0

    def test_model_is_frozen(self) -> None:
        """EdgeMetrics should be immutable (frozen=True)."""
        edges = EdgeMetrics(
            exploitation_tension=TC.Probability.MIDPOINT,
            exploitation_rent=TC.Wealth.DEFAULT_WEALTH,
            tribute_flow=TC.RevolutionaryFinance.DEFAULT_WAR_CHEST,
            wages_paid=TC.RevolutionaryFinance.DUES_INCOME,
            solidarity_strength=TC.Probability.LOW,
        )
        with pytest.raises((ValidationError, AttributeError)):
            edges.exploitation_tension = TC.Probability.EXTREME  # type: ignore[misc]


# =============================================================================
# TICK METRICS TESTS
# =============================================================================


@pytest.mark.math
class TestTickMetrics:
    """Tests for TickMetrics model.

    TickMetrics is a complete snapshot of simulation state at a tick.
    It aggregates entity metrics, edge metrics, and global state.
    """

    def test_can_instantiate_with_tick_only(self) -> None:
        """TickMetrics requires at minimum a tick number."""
        metrics = TickMetrics(tick=0)
        assert metrics.tick == 0

    def test_tick_must_be_non_negative(self) -> None:
        """Tick number must be >= 0."""
        with pytest.raises(ValidationError):
            TickMetrics(tick=-1)

    def test_accepts_entity_metrics(self) -> None:
        """TickMetrics accepts optional EntityMetrics for each entity.

        Entity slots (from parameter_analysis.py column prefixes):
        - p_w: Periphery Worker (C001)
        - p_c: Comprador (C002)
        - c_b: Core Bourgeoisie (C003)
        - c_w: Labor Aristocracy (C004)
        """
        p_w = EntityMetrics(
            wealth=0.1,
            consciousness=0.5,
            national_identity=0.2,
            agitation=0.3,
            p_acquiescence=0.6,
            p_revolution=0.4,
            organization=0.15,
        )
        metrics = TickMetrics(tick=0, p_w=p_w)
        assert metrics.p_w is not None
        assert metrics.p_w.wealth == 0.1

    def test_all_entity_slots_are_optional(self) -> None:
        """Entity metrics slots default to None for missing entities."""
        metrics = TickMetrics(tick=0)
        assert metrics.p_w is None
        assert metrics.p_c is None
        assert metrics.c_b is None
        assert metrics.c_w is None

    def test_accepts_edge_metrics(self) -> None:
        """TickMetrics accepts EdgeMetrics for relationship data."""
        edges = EdgeMetrics(
            exploitation_tension=TC.Probability.MIDPOINT,
            exploitation_rent=TC.Wealth.DEFAULT_WEALTH,
            tribute_flow=TC.RevolutionaryFinance.DEFAULT_WAR_CHEST,
            wages_paid=TC.RevolutionaryFinance.DUES_INCOME,
            solidarity_strength=TC.Probability.LOW,
        )
        metrics = TickMetrics(tick=0, edges=edges)
        assert metrics.edges is not None
        assert metrics.edges.exploitation_tension == TC.Probability.MIDPOINT

    def test_edges_defaults_to_empty_edge_metrics(self) -> None:
        """Edge metrics defaults to EdgeMetrics with all zeros."""
        metrics = TickMetrics(tick=0)
        assert metrics.edges is not None
        assert metrics.edges.exploitation_tension == 0.0

    def test_accepts_global_metrics(self) -> None:
        """TickMetrics accepts global state metrics.

        Global metrics:
        - imperial_rent_pool: Currency >= 0
        - global_tension: Probability [0, 1] (average of all tensions)
        """
        metrics = TickMetrics(
            tick=0,
            imperial_rent_pool=TC.EconomicFlow.INITIAL_RENT_POOL,
            global_tension=TC.Probability.MODERATE,
        )
        assert metrics.imperial_rent_pool == TC.EconomicFlow.INITIAL_RENT_POOL
        assert metrics.global_tension == TC.Probability.MODERATE

    def test_imperial_rent_pool_must_be_non_negative(self) -> None:
        """Imperial rent pool uses Currency type (>= 0)."""
        with pytest.raises(ValidationError):
            TickMetrics(tick=0, imperial_rent_pool=-10.0)

    def test_global_tension_must_be_probability(self) -> None:
        """Global tension is bounded [0, 1]."""
        with pytest.raises(ValidationError):
            TickMetrics(tick=0, global_tension=1.5)

    def test_global_metrics_have_defaults(self) -> None:
        """Global metrics default to 0.0."""
        metrics = TickMetrics(tick=0)
        assert metrics.imperial_rent_pool == 0.0
        assert metrics.global_tension == 0.0

    def test_model_is_frozen(self) -> None:
        """TickMetrics should be immutable (frozen=True)."""
        metrics = TickMetrics(tick=0)
        with pytest.raises((ValidationError, AttributeError)):
            metrics.tick = 1  # type: ignore[misc]

    def test_full_construction_with_all_entities(self) -> None:
        """TickMetrics can hold all 4 entity metrics simultaneously."""
        p_w = EntityMetrics(
            wealth=TC.Probability.LOW,
            consciousness=TC.Probability.MIDPOINT,
            national_identity=TC.Probability.LOW,
            agitation=TC.Probability.MODERATE,
            p_acquiescence=TC.Probability.ELEVATED,
            p_revolution=0.4,
            organization=0.15,
        )
        p_c = EntityMetrics(
            wealth=TC.Probability.LOW,
            consciousness=TC.Probability.MODERATE,
            national_identity=0.4,
            agitation=TC.Probability.LOW,
            p_acquiescence=TC.Probability.HIGH,
            p_revolution=TC.Probability.MODERATE,
            organization=TC.Probability.LOW,
        )
        c_b = EntityMetrics(
            wealth=TC.Probability.EXTREME,
            consciousness=TC.Probability.LOW,
            national_identity=TC.Probability.VERY_HIGH,
            agitation=0.05,
            p_acquiescence=0.95,
            p_revolution=0.05,
            organization=TC.Probability.VERY_HIGH,
        )
        c_w = EntityMetrics(
            wealth=0.4,
            consciousness=TC.Probability.LOW,
            national_identity=TC.Probability.MIDPOINT,
            agitation=0.15,
            p_acquiescence=TC.Probability.VERY_HIGH,
            p_revolution=TC.Probability.LOW,
            organization=TC.Probability.MODERATE,
        )
        edges = EdgeMetrics(
            exploitation_tension=TC.Probability.MIDPOINT,
            exploitation_rent=TC.Wealth.DEFAULT_WEALTH,
            tribute_flow=TC.RevolutionaryFinance.DEFAULT_WAR_CHEST,
            wages_paid=TC.RevolutionaryFinance.DUES_INCOME,
            solidarity_strength=TC.Probability.LOW,
        )

        metrics = TickMetrics(
            tick=42,
            p_w=p_w,
            p_c=p_c,
            c_b=c_b,
            c_w=c_w,
            edges=edges,
            imperial_rent_pool=TC.EconomicFlow.INITIAL_RENT_POOL,
            global_tension=0.4,
        )

        assert metrics.tick == 42
        assert metrics.p_w is not None
        assert metrics.p_w.wealth == TC.Probability.LOW
        assert metrics.p_c is not None
        assert metrics.p_c.wealth == TC.Probability.LOW
        assert metrics.c_b is not None
        assert metrics.c_b.wealth == TC.Probability.EXTREME
        assert metrics.c_w is not None
        assert metrics.c_w.wealth == 0.4
        assert metrics.edges.exploitation_tension == TC.Probability.MIDPOINT
        assert metrics.imperial_rent_pool == TC.EconomicFlow.INITIAL_RENT_POOL
        assert metrics.global_tension == 0.4


# =============================================================================
# SWEEP SUMMARY TESTS
# =============================================================================


@pytest.mark.math
class TestSweepSummary:
    """Tests for SweepSummary model.

    SweepSummary aggregates metrics across a complete simulation run.
    It provides summary statistics for parameter sweep analysis.
    """

    def test_can_instantiate_with_all_fields(self) -> None:
        """SweepSummary accepts all summary fields.

        Expected fields (from parameter_analysis.py extract_sweep_summary):
        - ticks_survived: int >= 0
        - outcome: str ("SURVIVED" | "DIED" | "ERROR")
        - final_p_w_wealth: Currency >= 0
        - final_p_c_wealth: Currency >= 0
        - final_c_b_wealth: Currency >= 0
        - final_c_w_wealth: Currency >= 0
        - max_tension: Probability [0, 1]
        - crossover_tick: Optional[int] >= 0 (when P(S|R) > P(S|A))
        - cumulative_rent: Currency >= 0
        - peak_p_w_consciousness: Probability [0, 1]
        - peak_c_w_consciousness: Probability [0, 1]
        """
        summary = SweepSummary(
            ticks_survived=50,
            outcome="SURVIVED",
            final_p_w_wealth=0.1,
            final_p_c_wealth=0.2,
            final_c_b_wealth=0.9,
            final_c_w_wealth=0.4,
            max_tension=0.8,
            crossover_tick=25,
            cumulative_rent=150.0,
            peak_p_w_consciousness=0.6,
            peak_c_w_consciousness=0.3,
        )
        assert summary.ticks_survived == 50
        assert summary.outcome == "SURVIVED"
        assert summary.final_p_w_wealth == 0.1
        assert summary.crossover_tick == 25
        assert summary.cumulative_rent == 150.0

    def test_ticks_survived_must_be_non_negative(self) -> None:
        """Ticks survived must be >= 0."""
        with pytest.raises(ValidationError):
            SweepSummary(
                ticks_survived=-1,  # Invalid
                outcome="SURVIVED",
                final_p_w_wealth=0.1,
                final_p_c_wealth=0.2,
                final_c_b_wealth=0.9,
                final_c_w_wealth=0.4,
                max_tension=0.8,
                crossover_tick=None,
                cumulative_rent=150.0,
                peak_p_w_consciousness=0.6,
                peak_c_w_consciousness=0.3,
            )

    def test_outcome_must_be_valid_literal(self) -> None:
        """Outcome must be one of the valid strings."""
        # Valid outcomes
        for outcome in ["SURVIVED", "DIED", "ERROR"]:
            summary = SweepSummary(
                ticks_survived=50,
                outcome=outcome,
                final_p_w_wealth=0.1,
                final_p_c_wealth=0.2,
                final_c_b_wealth=0.9,
                final_c_w_wealth=0.4,
                max_tension=0.8,
                crossover_tick=None,
                cumulative_rent=150.0,
                peak_p_w_consciousness=0.6,
                peak_c_w_consciousness=0.3,
            )
            assert summary.outcome == outcome

        # Invalid outcome
        with pytest.raises(ValidationError):
            SweepSummary(
                ticks_survived=50,
                outcome="UNKNOWN",  # Invalid
                final_p_w_wealth=0.1,
                final_p_c_wealth=0.2,
                final_c_b_wealth=0.9,
                final_c_w_wealth=0.4,
                max_tension=0.8,
                crossover_tick=None,
                cumulative_rent=150.0,
                peak_p_w_consciousness=0.6,
                peak_c_w_consciousness=0.3,
            )

    def test_wealth_fields_must_be_non_negative(self) -> None:
        """All wealth fields use Currency type (>= 0)."""
        with pytest.raises(ValidationError):
            SweepSummary(
                ticks_survived=50,
                outcome="DIED",
                final_p_w_wealth=-0.1,  # Invalid
                final_p_c_wealth=0.2,
                final_c_b_wealth=0.9,
                final_c_w_wealth=0.4,
                max_tension=0.8,
                crossover_tick=None,
                cumulative_rent=150.0,
                peak_p_w_consciousness=0.6,
                peak_c_w_consciousness=0.3,
            )

    def test_max_tension_must_be_probability(self) -> None:
        """Max tension is bounded [0, 1]."""
        with pytest.raises(ValidationError):
            SweepSummary(
                ticks_survived=50,
                outcome="SURVIVED",
                final_p_w_wealth=0.1,
                final_p_c_wealth=0.2,
                final_c_b_wealth=0.9,
                final_c_w_wealth=0.4,
                max_tension=1.5,  # Invalid: > 1.0
                crossover_tick=None,
                cumulative_rent=150.0,
                peak_p_w_consciousness=0.6,
                peak_c_w_consciousness=0.3,
            )

    def test_crossover_tick_is_optional(self) -> None:
        """Crossover tick can be None (no crossover detected)."""
        summary = SweepSummary(
            ticks_survived=50,
            outcome="SURVIVED",
            final_p_w_wealth=0.1,
            final_p_c_wealth=0.2,
            final_c_b_wealth=0.9,
            final_c_w_wealth=0.4,
            max_tension=0.8,
            crossover_tick=None,  # No crossover
            cumulative_rent=150.0,
            peak_p_w_consciousness=0.6,
            peak_c_w_consciousness=0.3,
        )
        assert summary.crossover_tick is None

    def test_crossover_tick_when_provided_must_be_non_negative(self) -> None:
        """If crossover tick is provided, it must be >= 0."""
        with pytest.raises(ValidationError):
            SweepSummary(
                ticks_survived=50,
                outcome="SURVIVED",
                final_p_w_wealth=0.1,
                final_p_c_wealth=0.2,
                final_c_b_wealth=0.9,
                final_c_w_wealth=0.4,
                max_tension=0.8,
                crossover_tick=-1,  # Invalid
                cumulative_rent=150.0,
                peak_p_w_consciousness=0.6,
                peak_c_w_consciousness=0.3,
            )

    def test_cumulative_rent_must_be_non_negative(self) -> None:
        """Cumulative rent uses Currency type (>= 0)."""
        with pytest.raises(ValidationError):
            SweepSummary(
                ticks_survived=50,
                outcome="SURVIVED",
                final_p_w_wealth=0.1,
                final_p_c_wealth=0.2,
                final_c_b_wealth=0.9,
                final_c_w_wealth=0.4,
                max_tension=0.8,
                crossover_tick=None,
                cumulative_rent=-10.0,  # Invalid
                peak_p_w_consciousness=0.6,
                peak_c_w_consciousness=0.3,
            )

    def test_peak_consciousness_must_be_probability(self) -> None:
        """Peak consciousness values are bounded [0, 1]."""
        with pytest.raises(ValidationError):
            SweepSummary(
                ticks_survived=50,
                outcome="SURVIVED",
                final_p_w_wealth=0.1,
                final_p_c_wealth=0.2,
                final_c_b_wealth=0.9,
                final_c_w_wealth=0.4,
                max_tension=0.8,
                crossover_tick=None,
                cumulative_rent=150.0,
                peak_p_w_consciousness=1.5,  # Invalid
                peak_c_w_consciousness=0.3,
            )

    def test_model_is_frozen(self) -> None:
        """SweepSummary should be immutable (frozen=True)."""
        summary = SweepSummary(
            ticks_survived=50,
            outcome="SURVIVED",
            final_p_w_wealth=0.1,
            final_p_c_wealth=0.2,
            final_c_b_wealth=0.9,
            final_c_w_wealth=0.4,
            max_tension=0.8,
            crossover_tick=None,
            cumulative_rent=150.0,
            peak_p_w_consciousness=0.6,
            peak_c_w_consciousness=0.3,
        )
        with pytest.raises((ValidationError, AttributeError)):
            summary.ticks_survived = 100  # type: ignore[misc]

    def test_serializes_to_json(self) -> None:
        """SweepSummary serializes to JSON correctly."""
        summary = SweepSummary(
            ticks_survived=50,
            outcome="SURVIVED",
            final_p_w_wealth=0.1,
            final_p_c_wealth=0.2,
            final_c_b_wealth=0.9,
            final_c_w_wealth=0.4,
            max_tension=0.8,
            crossover_tick=25,
            cumulative_rent=150.0,
            peak_p_w_consciousness=0.6,
            peak_c_w_consciousness=0.3,
        )
        json_str = summary.model_dump_json()
        assert '"outcome":"SURVIVED"' in json_str or '"outcome": "SURVIVED"' in json_str
        assert "50" in json_str  # ticks_survived

    def test_round_trip_json_preserves_values(self) -> None:
        """SweepSummary survives JSON serialization round-trip."""
        original = SweepSummary(
            ticks_survived=50,
            outcome="SURVIVED",
            final_p_w_wealth=0.1,
            final_p_c_wealth=0.2,
            final_c_b_wealth=0.9,
            final_c_w_wealth=0.4,
            max_tension=0.8,
            crossover_tick=25,
            cumulative_rent=150.0,
            peak_p_w_consciousness=0.6,
            peak_c_w_consciousness=0.3,
        )
        json_str = original.model_dump_json()
        restored = SweepSummary.model_validate_json(json_str)

        assert restored.ticks_survived == original.ticks_survived
        assert restored.outcome == original.outcome
        assert restored.crossover_tick == original.crossover_tick


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


@pytest.mark.math
class TestMetricsModelsIntegration:
    """Integration tests for metrics models working together."""

    def test_tick_metrics_nested_in_sweep_calculation(self) -> None:
        """TickMetrics can be used to calculate SweepSummary.

        This test verifies the models can work together to implement
        the logic in extract_sweep_summary().
        """
        # Create a series of TickMetrics representing a simulation run
        tick0 = TickMetrics(
            tick=0,
            p_w=EntityMetrics(
                wealth=TC.Probability.MIDPOINT,
                consciousness=TC.Probability.LOW,
                national_identity=TC.Probability.LOW,
                agitation=TC.Probability.LOW,
                p_acquiescence=TC.Probability.EXTREME,
                p_revolution=TC.Probability.LOW,
                organization=TC.Probability.LOW,
            ),
            edges=EdgeMetrics(
                exploitation_tension=TC.Probability.LOW,
                exploitation_rent=TC.Wealth.DEFAULT_WEALTH,
                tribute_flow=TC.RevolutionaryFinance.DEFAULT_WAR_CHEST,
                wages_paid=TC.RevolutionaryFinance.DUES_INCOME,
                solidarity_strength=TC.Probability.ZERO,
            ),
            imperial_rent_pool=TC.EconomicFlow.INITIAL_RENT_POOL,
            global_tension=TC.Probability.LOW,
        )

        tick1 = TickMetrics(
            tick=1,
            p_w=EntityMetrics(
                wealth=0.4,
                consciousness=TC.Probability.LOW,
                national_identity=TC.Probability.LOW,
                agitation=TC.Probability.LOW,
                p_acquiescence=TC.Probability.VERY_HIGH,
                p_revolution=TC.Probability.LOW,
                organization=0.15,
            ),
            edges=EdgeMetrics(
                exploitation_tension=TC.Probability.MIDPOINT,
                exploitation_rent=12.0,
                tribute_flow=6.0,
                wages_paid=4.0,
                solidarity_strength=TC.Probability.LOW,
            ),
            imperial_rent_pool=90.0,
            global_tension=TC.Probability.MIDPOINT,
        )

        # Simulate calculating summary
        history = [tick0, tick1]
        last = history[-1]

        ticks_survived = len(history)
        # DIED if p_w wealth <= 0.001
        assert last.p_w is not None
        outcome = "DIED" if last.p_w.wealth <= 0.001 else "SURVIVED"
        max_tension = max(t.edges.exploitation_tension for t in history)
        cumulative_rent = sum(t.edges.exploitation_rent for t in history)

        assert ticks_survived == 2
        assert outcome == "SURVIVED"
        assert max_tension == TC.Probability.MIDPOINT
        assert cumulative_rent == 22.0

    def test_entity_metrics_extracted_from_world_state_pattern(self) -> None:
        """EntityMetrics fields match SocialClass extraction pattern.

        This tests that the model structure matches what we'd extract
        from a SocialClass in WorldState.
        """
        # These fields should match SocialClass/IdeologicalProfile
        entity = EntityMetrics(
            wealth=TC.Probability.MIDPOINT,  # SocialClass.wealth
            consciousness=TC.Probability.MODERATE,  # SocialClass.ideology.class_consciousness
            national_identity=TC.Probability.LOW,  # SocialClass.ideology.national_identity
            agitation=TC.Probability.LOW,  # SocialClass.ideology.agitation
            p_acquiescence=TC.Probability.VERY_HIGH,  # SocialClass.p_acquiescence
            p_revolution=TC.Probability.LOW,  # SocialClass.p_revolution
            organization=0.15,  # SocialClass.organization
        )
        # All extractions should succeed
        assert entity.wealth == TC.Probability.MIDPOINT
        assert entity.consciousness == TC.Probability.MODERATE
        assert entity.national_identity == TC.Probability.LOW
        assert entity.agitation == TC.Probability.LOW
        assert entity.p_acquiescence == TC.Probability.VERY_HIGH
        assert entity.p_revolution == TC.Probability.LOW
        assert entity.organization == 0.15


# =============================================================================
# BATCH 1: ECONOMY DRIVERS MODEL TESTS (Phase 4.1B)
# =============================================================================


@pytest.mark.math
class TestTickMetricsEconomyDrivers:
    """Tests for TickMetrics economy driver fields.

    Phase 4.1B: Expose Meaningful Metrics - Economy Drivers.
    These fields expose the current super-wage rate and repression level
    that drive the simulation dynamics.
    """

    def test_accepts_current_super_wage_rate(self) -> None:
        """TickMetrics accepts Coefficient field for current super-wage rate.

        The super-wage rate (Wc/Vc) determines how much core workers receive
        above the value they produce, funded by imperial rent.
        """
        metrics = TickMetrics(tick=0, current_super_wage_rate=TC.Probability.MODERATE)
        assert metrics.current_super_wage_rate == TC.Probability.MODERATE
        # Verify it's a float (Coefficient type serializes to float)
        assert isinstance(metrics.current_super_wage_rate, float)

    def test_current_super_wage_rate_defaults_to_zero_point_two(self) -> None:
        """current_super_wage_rate defaults to 0.20.

        Default super-wage rate of 20% matches the imperial rent extraction
        efficiency coefficient in GameDefines.
        """
        metrics = TickMetrics(tick=0)
        assert metrics.current_super_wage_rate == 0.2

    def test_current_super_wage_rate_must_be_non_negative(self) -> None:
        """current_super_wage_rate must be >= 0 (Coefficient constraint).

        Negative super-wage rates are economically meaningless.
        """
        with pytest.raises(ValidationError):
            TickMetrics(tick=0, current_super_wage_rate=-0.1)

    def test_accepts_current_repression_level(self) -> None:
        """TickMetrics accepts Probability field for current repression level.

        The repression level represents the intensity of state violence
        directed at the periphery proletariat.
        """
        metrics = TickMetrics(tick=0, current_repression_level=TC.Probability.HIGH)
        assert metrics.current_repression_level == TC.Probability.HIGH

    def test_current_repression_level_defaults_to_zero_point_five(self) -> None:
        """current_repression_level defaults to 0.5.

        Default repression level of 50% represents baseline state violence.
        """
        metrics = TickMetrics(tick=0)
        assert metrics.current_repression_level == 0.5

    def test_current_repression_level_must_be_probability(self) -> None:
        """current_repression_level must be bounded [0, 1].

        Repression is a probability-like value bounded between 0 (no repression)
        and 1 (maximum repression).
        """
        # Test upper bound
        with pytest.raises(ValidationError):
            TickMetrics(tick=0, current_repression_level=1.5)
        # Test lower bound
        with pytest.raises(ValidationError):
            TickMetrics(tick=0, current_repression_level=-0.1)

    def test_accepts_pool_ratio(self) -> None:
        """TickMetrics accepts Probability field for pool ratio.

        The pool ratio represents imperial_rent_pool / initial_pool,
        indicating how depleted the rent pool is.
        """
        metrics = TickMetrics(tick=0, pool_ratio=TC.Probability.VERY_HIGH)
        assert metrics.pool_ratio == TC.Probability.VERY_HIGH

    def test_pool_ratio_defaults_to_one(self) -> None:
        """pool_ratio defaults to 1.0.

        Default pool ratio of 1.0 means the rent pool is at its initial value
        (no depletion yet).
        """
        metrics = TickMetrics(tick=0)
        assert metrics.pool_ratio == 1.0


# =============================================================================
# BATCH 2: TOPOLOGY SUMMARY MODEL TESTS (Phase 4.1B)
# =============================================================================


@pytest.mark.math
class TestTopologySummary:
    """Tests for TopologySummary model.

    Phase 4.1B: Expose Meaningful Metrics - Topology Summary.
    This model captures the topological phase state of the simulation,
    including percolation ratio, cadre density, and phase classification.
    """

    def test_can_instantiate_with_all_fields(self) -> None:
        """TopologySummary accepts all topology-related fields.

        Expected fields:
        - percolation_ratio: Probability [0, 1] (largest component / total)
        - cadre_density: Probability [0, 1] (cadres / total_proletariat)
        - num_components: int >= 0 (number of connected components)
        - phase: str (topological phase classification)
        """
        from babylon.models.metrics import TopologySummary

        topology = TopologySummary(
            percolation_ratio=TC.Probability.VERY_HIGH,
            cadre_density=0.15,
            num_components=3,
            phase="transitional",
        )
        assert topology.percolation_ratio == TC.Probability.VERY_HIGH
        assert topology.cadre_density == 0.15
        assert topology.num_components == 3
        assert topology.phase == "transitional"

    def test_percolation_ratio_must_be_probability(self) -> None:
        """percolation_ratio must be bounded [0, 1].

        The percolation ratio is the fraction of nodes in the largest
        connected component, which is always between 0 and 1.
        """
        from babylon.models.metrics import TopologySummary

        # Test upper bound (invalid boundary values kept inline)
        with pytest.raises(ValidationError):
            TopologySummary(
                percolation_ratio=1.5,
                cadre_density=0.15,
                num_components=3,
                phase="gaseous",
            )
        # Test lower bound (invalid boundary values kept inline)
        with pytest.raises(ValidationError):
            TopologySummary(
                percolation_ratio=-0.1,
                cadre_density=0.15,
                num_components=3,
                phase="gaseous",
            )

    def test_cadre_density_must_be_probability(self) -> None:
        """cadre_density must be bounded [0, 1].

        Cadre density is the fraction of proletarians who are cadres,
        always between 0 and 1.
        """
        from babylon.models.metrics import TopologySummary

        with pytest.raises(ValidationError):
            TopologySummary(
                percolation_ratio=0.8,
                cadre_density=1.5,  # Invalid: > 1.0
                num_components=3,
                phase="gaseous",
            )

    def test_num_components_must_be_non_negative(self) -> None:
        """num_components must be >= 0.

        The number of connected components cannot be negative.
        """
        from babylon.models.metrics import TopologySummary

        with pytest.raises(ValidationError):
            TopologySummary(
                percolation_ratio=0.8,
                cadre_density=0.15,
                num_components=-1,  # Invalid: < 0
                phase="gaseous",
            )

    def test_phase_accepts_valid_phases(self) -> None:
        """phase field accepts valid phase strings.

        Valid phases are based on percolation theory:
        - "gaseous": Fragmented, no percolation (ratio < 0.25)
        - "transitional": Near percolation threshold (0.25 <= ratio < 0.5)
        - "liquid": Partial percolation (0.5 <= ratio < 0.75)
        - "solid": Full percolation (ratio >= 0.75)
        """
        from babylon.models.metrics import TopologySummary

        for phase in ["gaseous", "transitional", "liquid", "solid"]:
            topology = TopologySummary(
                percolation_ratio=TC.Probability.MIDPOINT,
                cadre_density=0.15,
                num_components=3,
                phase=phase,
            )
            assert topology.phase == phase

    def test_phase_rejects_invalid_phase(self) -> None:
        """phase field rejects invalid phase strings.

        Only the four valid phases are accepted.
        """
        from babylon.models.metrics import TopologySummary

        with pytest.raises(ValidationError):
            TopologySummary(
                percolation_ratio=TC.Probability.MIDPOINT,
                cadre_density=0.15,
                num_components=3,
                phase="plasma",  # Invalid phase
            )

    def test_all_fields_have_defaults(self) -> None:
        """TopologySummary can be constructed with no arguments.

        All fields should have sensible defaults:
        - percolation_ratio: 0.0 (no percolation)
        - cadre_density: 0.0 (no cadres)
        - num_components: 0 (empty graph)
        - phase: "gaseous" (fragmented initial state)
        """
        from babylon.models.metrics import TopologySummary

        topology = TopologySummary()
        assert topology.percolation_ratio == 0.0
        assert topology.cadre_density == 0.0
        assert topology.num_components == 0
        assert topology.phase == "gaseous"

    def test_tick_metrics_accepts_topology_field(self) -> None:
        """TickMetrics accepts optional TopologySummary field.

        The topology field provides topological phase information
        for dashboard visualization.
        """
        from babylon.models.metrics import TopologySummary

        topology = TopologySummary(
            percolation_ratio=TC.Probability.VERY_HIGH,
            cadre_density=0.15,
            num_components=3,
            phase="solid",
        )
        metrics = TickMetrics(tick=0, topology=topology)
        assert metrics.topology is not None
        assert metrics.topology.phase == "solid"
        assert metrics.topology.percolation_ratio == TC.Probability.VERY_HIGH

        # Also test that it defaults to None
        metrics_no_topology = TickMetrics(tick=0)
        assert metrics_no_topology.topology is None


# =============================================================================
# BATCH 3: DERIVED DIFFERENTIALS TESTS (Phase 4.1B)
# =============================================================================


@pytest.mark.math
class TestTickMetricsDifferentials:
    """Tests for TickMetrics differential/gap fields.

    Phase 4.1B: Expose Meaningful Metrics - Derived Differentials.
    These fields expose pre-computed differentials between entity values
    that drive key simulation dynamics.
    """

    def test_accepts_consciousness_gap(self) -> None:
        """TickMetrics accepts float field for consciousness gap.

        The consciousness gap (p_w.consciousness - c_w.consciousness) measures
        how far ahead the periphery worker is in class consciousness compared
        to the labor aristocracy.
        """
        metrics = TickMetrics(tick=0, consciousness_gap=TC.Probability.MODERATE)
        assert metrics.consciousness_gap == TC.Probability.MODERATE

    def test_consciousness_gap_can_be_negative(self) -> None:
        """consciousness_gap can be negative.

        Negative gap means labor aristocracy has higher consciousness
        than periphery worker (rare but possible scenario).
        """
        metrics = TickMetrics(tick=0, consciousness_gap=TC.Ideology.LEANING_REVOLUTIONARY)
        assert metrics.consciousness_gap == TC.Ideology.LEANING_REVOLUTIONARY

    def test_consciousness_gap_bounded_minus_one_to_one(self) -> None:
        """consciousness_gap is bounded [-1.0, 1.0].

        Since both consciousnesses are in [0, 1], the difference is in [-1, 1].
        """
        # Test upper bound
        with pytest.raises(ValidationError):
            TickMetrics(tick=0, consciousness_gap=1.5)
        # Test lower bound
        with pytest.raises(ValidationError):
            TickMetrics(tick=0, consciousness_gap=-1.5)
        # Boundary values should work
        metrics_max = TickMetrics(tick=0, consciousness_gap=1.0)
        assert metrics_max.consciousness_gap == 1.0
        metrics_min = TickMetrics(tick=0, consciousness_gap=-1.0)
        assert metrics_min.consciousness_gap == -1.0

    def test_consciousness_gap_defaults_to_zero(self) -> None:
        """consciousness_gap defaults to 0.0.

        Default gap of 0 means no consciousness differential.
        """
        metrics = TickMetrics(tick=0)
        assert metrics.consciousness_gap == 0.0

    def test_accepts_wealth_gap(self) -> None:
        """TickMetrics accepts float field for wealth gap.

        The wealth gap (c_b.wealth - p_w.wealth) measures the wealth
        differential between core bourgeoisie and periphery worker.
        """
        metrics = TickMetrics(tick=0, wealth_gap=TC.Probability.VERY_HIGH)
        assert metrics.wealth_gap == TC.Probability.VERY_HIGH

    def test_wealth_gap_defaults_to_zero(self) -> None:
        """wealth_gap defaults to 0.0.

        Default gap of 0 means no wealth differential.
        """
        metrics = TickMetrics(tick=0)
        assert metrics.wealth_gap == 0.0


# =============================================================================
# BATCH 8: ECOLOGICAL METRICS TESTS (Sprint 1.4C - The Wiring)
# =============================================================================


class TestTickMetricsEcologicalFields:
    """Tests for TickMetrics ecological metric fields.

    Sprint 1.4C: The Wiring - TickMetrics must include ecological metrics
    for the Metabolic Rift feedback loop to be observable in dashboards.
    """

    def test_tick_metrics_has_overshoot_ratio_field(self) -> None:
        """TickMetrics should have overshoot_ratio field.

        overshoot_ratio = total_consumption / total_biocapacity
        When > 1.0, we are in ecological overshoot (consumption exceeds capacity).
        """
        # Check field exists in model
        assert "overshoot_ratio" in TickMetrics.model_fields, (
            "TickMetrics missing 'overshoot_ratio' field. "
            "Add: overshoot_ratio: float = Field(default=0.0, ge=0.0)"
        )

    def test_tick_metrics_has_total_biocapacity_field(self) -> None:
        """TickMetrics should have total_biocapacity field.

        total_biocapacity is the global sum of territory biocapacity,
        representing the planet's regenerative capacity.
        """
        assert "total_biocapacity" in TickMetrics.model_fields, (
            "TickMetrics missing 'total_biocapacity' field. "
            "Add: total_biocapacity: Currency = Field(default=0.0, ge=0.0)"
        )

    def test_tick_metrics_has_total_consumption_field(self) -> None:
        """TickMetrics should have total_consumption field.

        total_consumption is the global sum of entity consumption needs,
        representing total resource demand from all social classes.
        """
        assert "total_consumption" in TickMetrics.model_fields, (
            "TickMetrics missing 'total_consumption' field. "
            "Add: total_consumption: Currency = Field(default=0.0, ge=0.0)"
        )

    def test_overshoot_ratio_accepts_values(self) -> None:
        """overshoot_ratio field should accept valid float values.

        Overshoot can be > 1.0 (in overshoot) or <= 1.0 (sustainable).
        """
        # Overshoot scenario (>1.0) - test-specific value
        metrics = TickMetrics(tick=0, overshoot_ratio=1.5)
        assert metrics.overshoot_ratio == 1.5

        # Sustainable scenario (<=1.0)
        metrics_sustainable = TickMetrics(tick=0, overshoot_ratio=TC.Probability.HIGH)
        assert metrics_sustainable.overshoot_ratio == TC.Probability.HIGH

    def test_overshoot_ratio_defaults_to_zero(self) -> None:
        """overshoot_ratio should default to 0.0.

        When no ecological data is available, default to 0 (no consumption).
        """
        metrics = TickMetrics(tick=0)
        assert metrics.overshoot_ratio == 0.0

    def test_overshoot_ratio_must_be_non_negative(self) -> None:
        """overshoot_ratio should not accept negative values.

        Negative overshoot is physically meaningless.
        """
        with pytest.raises(ValidationError):
            TickMetrics(tick=0, overshoot_ratio=-0.5)

    def test_total_biocapacity_accepts_values(self) -> None:
        """total_biocapacity field should accept valid Currency values."""
        metrics = TickMetrics(tick=0, total_biocapacity=500.0)
        assert metrics.total_biocapacity == 500.0

    def test_total_biocapacity_defaults_to_zero(self) -> None:
        """total_biocapacity should default to 0.0."""
        metrics = TickMetrics(tick=0)
        assert metrics.total_biocapacity == 0.0

    def test_total_biocapacity_must_be_non_negative(self) -> None:
        """total_biocapacity should not accept negative values."""
        with pytest.raises(ValidationError):
            TickMetrics(tick=0, total_biocapacity=-100.0)

    def test_total_consumption_accepts_values(self) -> None:
        """total_consumption field should accept valid Currency values."""
        metrics = TickMetrics(tick=0, total_consumption=300.0)
        assert metrics.total_consumption == 300.0

    def test_total_consumption_defaults_to_zero(self) -> None:
        """total_consumption should default to 0.0."""
        metrics = TickMetrics(tick=0)
        assert metrics.total_consumption == 0.0

    def test_total_consumption_must_be_non_negative(self) -> None:
        """total_consumption should not accept negative values."""
        with pytest.raises(ValidationError):
            TickMetrics(tick=0, total_consumption=-50.0)

    def test_ecological_metrics_serialize_to_json(self) -> None:
        """Ecological metrics should serialize correctly to JSON."""
        metrics = TickMetrics(
            tick=5,
            overshoot_ratio=1.25,
            total_biocapacity=400.0,
            total_consumption=500.0,
        )
        json_str = metrics.model_dump_json()
        assert "1.25" in json_str  # overshoot_ratio
        assert "400" in json_str  # total_biocapacity
        assert "500" in json_str  # total_consumption
