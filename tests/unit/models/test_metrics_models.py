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

NOTE: All test classes are marked with @pytest.mark.red_phase to exclude them
from pre-commit fast tests. Remove this marker when implementing GREEN phase.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.metrics import (
    EdgeMetrics,
    EntityMetrics,
    SweepSummary,
    TickMetrics,
)

# All tests in this file are TDD RED phase - intentionally failing
pytestmark = pytest.mark.red_phase


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
            exploitation_tension=0.5,
            exploitation_rent=10.0,
            tribute_flow=5.0,
            wages_paid=3.0,
            solidarity_strength=0.2,
        )
        assert edges.exploitation_tension == 0.5
        assert edges.exploitation_rent == 10.0
        assert edges.tribute_flow == 5.0
        assert edges.wages_paid == 3.0
        assert edges.solidarity_strength == 0.2

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
            exploitation_tension=0.5,
            exploitation_rent=10.0,
            tribute_flow=5.0,
            wages_paid=3.0,
            solidarity_strength=0.2,
        )
        with pytest.raises((ValidationError, AttributeError)):
            edges.exploitation_tension = 0.9  # type: ignore[misc]


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
            exploitation_tension=0.5,
            exploitation_rent=10.0,
            tribute_flow=5.0,
            wages_paid=3.0,
            solidarity_strength=0.2,
        )
        metrics = TickMetrics(tick=0, edges=edges)
        assert metrics.edges is not None
        assert metrics.edges.exploitation_tension == 0.5

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
            imperial_rent_pool=100.0,
            global_tension=0.3,
        )
        assert metrics.imperial_rent_pool == 100.0
        assert metrics.global_tension == 0.3

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
            wealth=0.1,
            consciousness=0.5,
            national_identity=0.2,
            agitation=0.3,
            p_acquiescence=0.6,
            p_revolution=0.4,
            organization=0.15,
        )
        p_c = EntityMetrics(
            wealth=0.2,
            consciousness=0.3,
            national_identity=0.4,
            agitation=0.1,
            p_acquiescence=0.7,
            p_revolution=0.3,
            organization=0.2,
        )
        c_b = EntityMetrics(
            wealth=0.9,
            consciousness=0.1,
            national_identity=0.8,
            agitation=0.05,
            p_acquiescence=0.95,
            p_revolution=0.05,
            organization=0.8,
        )
        c_w = EntityMetrics(
            wealth=0.4,
            consciousness=0.2,
            national_identity=0.5,
            agitation=0.15,
            p_acquiescence=0.8,
            p_revolution=0.2,
            organization=0.3,
        )
        edges = EdgeMetrics(
            exploitation_tension=0.5,
            exploitation_rent=10.0,
            tribute_flow=5.0,
            wages_paid=3.0,
            solidarity_strength=0.2,
        )

        metrics = TickMetrics(
            tick=42,
            p_w=p_w,
            p_c=p_c,
            c_b=c_b,
            c_w=c_w,
            edges=edges,
            imperial_rent_pool=100.0,
            global_tension=0.4,
        )

        assert metrics.tick == 42
        assert metrics.p_w is not None
        assert metrics.p_w.wealth == 0.1
        assert metrics.p_c is not None
        assert metrics.p_c.wealth == 0.2
        assert metrics.c_b is not None
        assert metrics.c_b.wealth == 0.9
        assert metrics.c_w is not None
        assert metrics.c_w.wealth == 0.4
        assert metrics.edges.exploitation_tension == 0.5
        assert metrics.imperial_rent_pool == 100.0
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
                wealth=0.5,
                consciousness=0.1,
                national_identity=0.2,
                agitation=0.1,
                p_acquiescence=0.9,
                p_revolution=0.1,
                organization=0.1,
            ),
            edges=EdgeMetrics(
                exploitation_tension=0.2,
                exploitation_rent=10.0,
                tribute_flow=5.0,
                wages_paid=3.0,
                solidarity_strength=0.0,
            ),
            imperial_rent_pool=100.0,
            global_tension=0.2,
        )

        tick1 = TickMetrics(
            tick=1,
            p_w=EntityMetrics(
                wealth=0.4,
                consciousness=0.2,
                national_identity=0.2,
                agitation=0.2,
                p_acquiescence=0.8,
                p_revolution=0.2,
                organization=0.15,
            ),
            edges=EdgeMetrics(
                exploitation_tension=0.5,
                exploitation_rent=12.0,
                tribute_flow=6.0,
                wages_paid=4.0,
                solidarity_strength=0.1,
            ),
            imperial_rent_pool=90.0,
            global_tension=0.5,
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
        assert max_tension == 0.5
        assert cumulative_rent == 22.0

    def test_entity_metrics_extracted_from_world_state_pattern(self) -> None:
        """EntityMetrics fields match SocialClass extraction pattern.

        This tests that the model structure matches what we'd extract
        from a SocialClass in WorldState.
        """
        # These fields should match SocialClass/IdeologicalProfile
        entity = EntityMetrics(
            wealth=0.5,  # SocialClass.wealth
            consciousness=0.3,  # SocialClass.ideology.class_consciousness
            national_identity=0.2,  # SocialClass.ideology.national_identity
            agitation=0.1,  # SocialClass.ideology.agitation
            p_acquiescence=0.8,  # SocialClass.p_acquiescence
            p_revolution=0.2,  # SocialClass.p_revolution
            organization=0.15,  # SocialClass.organization
        )
        # All extractions should succeed
        assert entity.wealth == 0.5
        assert entity.consciousness == 0.3
        assert entity.national_identity == 0.2
        assert entity.agitation == 0.1
        assert entity.p_acquiescence == 0.8
        assert entity.p_revolution == 0.2
        assert entity.organization == 0.15
