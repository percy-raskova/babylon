"""Tests for MetricsCollector observer (Sprint 4.1: Dashboard/Sweeper Unification).

TDD RED Phase: These tests define the contract for MetricsCollector that
unifies metrics collection between the parameter sweeper and dashboard.

The MetricsCollector:
- Implements SimulationObserver protocol
- Extracts entity metrics (wealth, consciousness, survival probabilities)
- Extracts edge metrics (tension, value flows, solidarity)
- Tracks global metrics (imperial_rent_pool, global_tension)
- Supports two modes: "interactive" (rolling window) and "batch" (full history)
- Provides summary statistics for parameter sweeps
- Exports to CSV-compatible format

All tests should FAIL until GREEN phase implements the observer.

NOTE: All test classes are marked with @pytest.mark.red_phase to exclude them
from pre-commit fast tests. Remove this marker when implementing GREEN phase.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from babylon.engine.observers.metrics import MetricsCollector
from babylon.engine.scenarios import (
    create_imperial_circuit_scenario,
    create_two_node_scenario,
)
from babylon.models import SimulationConfig, WorldState
from babylon.models.entities.economy import GlobalEconomy
from babylon.models.enums import EdgeType

if TYPE_CHECKING:
    pass

# All tests in this file are TDD RED phase - intentionally failing
pytestmark = pytest.mark.red_phase


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def config() -> SimulationConfig:
    """Create default simulation config."""
    return SimulationConfig()


@pytest.fixture
def four_node_state() -> WorldState:
    """Create 4-node imperial circuit scenario state."""
    state, _, _ = create_imperial_circuit_scenario()
    return state


@pytest.fixture
def two_node_state() -> WorldState:
    """Create 2-node minimal scenario state."""
    state, _, _ = create_two_node_scenario()
    return state


@pytest.fixture
def state_with_tension(four_node_state: WorldState) -> WorldState:
    """Create state with non-zero tension on edges."""
    from babylon.models.entities.relationship import Relationship

    # Find the exploitation edge and add tension
    new_rels = []
    for rel in four_node_state.relationships:
        if rel.edge_type == EdgeType.EXPLOITATION:
            new_rel = Relationship(
                source_id=rel.source_id,
                target_id=rel.target_id,
                edge_type=rel.edge_type,
                value_flow=10.0,
                tension=0.5,
                description=rel.description,
            )
            new_rels.append(new_rel)
        else:
            new_rels.append(rel)

    return four_node_state.model_copy(update={"relationships": new_rels})


# =============================================================================
# TEST PROTOCOL COMPLIANCE
# =============================================================================


@pytest.mark.unit
class TestMetricsCollectorProtocol:
    """Tests for MetricsCollector protocol compliance."""

    def test_implements_observer_protocol(self) -> None:
        """MetricsCollector satisfies SimulationObserver protocol."""
        from babylon.engine.observer import SimulationObserver

        collector = MetricsCollector()
        assert isinstance(collector, SimulationObserver)

    def test_name_property_returns_metrics_collector(self) -> None:
        """Name property returns 'MetricsCollector'."""
        collector = MetricsCollector()
        assert collector.name == "MetricsCollector"

    def test_has_on_simulation_start_method(self) -> None:
        """Has on_simulation_start method accepting WorldState and SimulationConfig."""
        collector = MetricsCollector()
        assert hasattr(collector, "on_simulation_start")
        assert callable(collector.on_simulation_start)

    def test_has_on_tick_method(self) -> None:
        """Has on_tick method accepting two WorldState arguments."""
        collector = MetricsCollector()
        assert hasattr(collector, "on_tick")
        assert callable(collector.on_tick)

    def test_has_on_simulation_end_method(self) -> None:
        """Has on_simulation_end method accepting WorldState."""
        collector = MetricsCollector()
        assert hasattr(collector, "on_simulation_end")
        assert callable(collector.on_simulation_end)


# =============================================================================
# TEST MODE CONFIGURATION
# =============================================================================


@pytest.mark.unit
class TestModeConfiguration:
    """Tests for MetricsCollector mode configuration."""

    def test_default_mode_is_interactive(self) -> None:
        """Default mode is 'interactive' for dashboard use."""
        collector = MetricsCollector()
        assert collector._mode == "interactive"

    def test_can_specify_batch_mode(self) -> None:
        """Can create collector in 'batch' mode for parameter sweeps."""
        collector = MetricsCollector(mode="batch")
        assert collector._mode == "batch"

    def test_default_rolling_window_is_50(self) -> None:
        """Default rolling window is 50 ticks for interactive mode."""
        collector = MetricsCollector()
        assert collector._rolling_window == 50

    def test_can_specify_custom_rolling_window(self) -> None:
        """Can customize rolling window size."""
        collector = MetricsCollector(rolling_window=100)
        assert collector._rolling_window == 100

    def test_interactive_mode_uses_rolling_window(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Interactive mode limits history to rolling window size.

        When more ticks are collected than the window size,
        old entries should be evicted.
        """
        collector = MetricsCollector(mode="interactive", rolling_window=5)
        collector.on_simulation_start(four_node_state, config)

        # Simulate 10 ticks
        prev = four_node_state
        for i in range(10):
            new = prev.model_copy(update={"tick": i + 1})
            collector.on_tick(prev, new)
            prev = new

        # History should be capped at rolling window
        assert len(collector.history) <= 5

    def test_batch_mode_accumulates_all_history(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Batch mode accumulates all history without limit."""
        collector = MetricsCollector(mode="batch")
        collector.on_simulation_start(four_node_state, config)

        # Simulate 100 ticks
        prev = four_node_state
        for i in range(100):
            new = prev.model_copy(update={"tick": i + 1})
            collector.on_tick(prev, new)
            prev = new

        # History should contain all ticks plus initial
        assert len(collector.history) == 101  # tick 0 + 100 steps


# =============================================================================
# TEST PROPERTIES
# =============================================================================


@pytest.mark.unit
class TestMetricsCollectorProperties:
    """Tests for MetricsCollector properties."""

    def test_latest_returns_none_when_empty(self) -> None:
        """latest property returns None when no data collected."""
        collector = MetricsCollector()
        assert collector.latest is None

    def test_latest_returns_tick_metrics_after_data(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """latest property returns TickMetrics after collecting data."""
        from babylon.models.metrics import TickMetrics

        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        latest = collector.latest
        assert latest is not None
        assert isinstance(latest, TickMetrics)
        assert latest.tick == 0

    def test_latest_returns_most_recent_tick(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """latest returns the most recent tick's metrics."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        # Add several ticks
        prev = four_node_state
        for i in range(5):
            new = prev.model_copy(update={"tick": i + 1})
            collector.on_tick(prev, new)
            prev = new

        latest = collector.latest
        assert latest is not None
        assert latest.tick == 5

    def test_history_returns_list_not_deque(self) -> None:
        """history property returns a list, not a deque."""
        collector = MetricsCollector()
        history = collector.history
        assert isinstance(history, list)

    def test_history_returns_empty_list_when_empty(self) -> None:
        """history property returns empty list when no data collected."""
        collector = MetricsCollector()
        assert collector.history == []

    def test_summary_returns_none_when_empty(self) -> None:
        """summary property returns None when no data collected."""
        collector = MetricsCollector()
        assert collector.summary is None

    def test_summary_returns_sweep_summary_after_data(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """summary property returns SweepSummary after collecting data."""
        from babylon.models.metrics import SweepSummary

        collector = MetricsCollector(mode="batch")
        collector.on_simulation_start(four_node_state, config)

        summary = collector.summary
        assert summary is not None
        assert isinstance(summary, SweepSummary)


# =============================================================================
# TEST ENTITY EXTRACTION
# =============================================================================


@pytest.mark.unit
class TestEntityExtraction:
    """Tests for entity metrics extraction from WorldState."""

    def test_extracts_c001_as_p_w(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Extracts C001 (Periphery Worker) metrics as p_w slot."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.p_w is not None

        # Verify extraction from actual entity
        entity = four_node_state.entities["C001"]
        assert latest.p_w.wealth == float(entity.wealth)
        assert latest.p_w.organization == float(entity.organization)

    def test_extracts_c002_as_p_c(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Extracts C002 (Comprador) metrics as p_c slot."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.p_c is not None

        entity = four_node_state.entities["C002"]
        assert latest.p_c.wealth == float(entity.wealth)

    def test_extracts_c003_as_c_b(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Extracts C003 (Core Bourgeoisie) metrics as c_b slot."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.c_b is not None

        entity = four_node_state.entities["C003"]
        assert latest.c_b.wealth == float(entity.wealth)

    def test_extracts_c004_as_c_w(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Extracts C004 (Labor Aristocracy) metrics as c_w slot."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.c_w is not None

        entity = four_node_state.entities["C004"]
        assert latest.c_w.wealth == float(entity.wealth)

    def test_handles_missing_entities_gracefully(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Two-node scenario has only C001/C002, others should be None."""
        collector = MetricsCollector()
        collector.on_simulation_start(two_node_state, config)

        latest = collector.latest
        assert latest is not None
        # Two-node has C001 and C002
        assert latest.p_w is not None  # C001 exists
        assert latest.p_c is not None  # C002 exists
        # C003 and C004 don't exist in two-node
        assert latest.c_b is None
        assert latest.c_w is None

    def test_extracts_consciousness_from_ideology_profile(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Extracts consciousness from entity.ideology.class_consciousness."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.p_w is not None

        entity = four_node_state.entities["C001"]
        assert latest.p_w.consciousness == float(entity.ideology.class_consciousness)

    def test_extracts_national_identity_from_ideology_profile(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Extracts national_identity from entity.ideology.national_identity."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.p_w is not None

        entity = four_node_state.entities["C001"]
        assert latest.p_w.national_identity == float(entity.ideology.national_identity)

    def test_extracts_agitation_from_ideology_profile(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Extracts agitation from entity.ideology.agitation."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.p_w is not None

        entity = four_node_state.entities["C001"]
        assert latest.p_w.agitation == float(entity.ideology.agitation)

    def test_extracts_survival_probabilities(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Extracts p_acquiescence and p_revolution from entity."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.p_w is not None

        entity = four_node_state.entities["C001"]
        assert latest.p_w.p_acquiescence == float(entity.p_acquiescence)
        assert latest.p_w.p_revolution == float(entity.p_revolution)


# =============================================================================
# TEST EDGE EXTRACTION
# =============================================================================


@pytest.mark.unit
class TestEdgeExtraction:
    """Tests for edge metrics extraction from WorldState."""

    def test_extracts_exploitation_edge_tension(
        self,
        state_with_tension: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Extracts tension from EXPLOITATION edge."""
        collector = MetricsCollector()
        collector.on_simulation_start(state_with_tension, config)

        latest = collector.latest
        assert latest is not None
        assert latest.edges.exploitation_tension == 0.5

    def test_extracts_exploitation_edge_value_flow(
        self,
        state_with_tension: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Extracts value_flow from EXPLOITATION edge as exploitation_rent."""
        collector = MetricsCollector()
        collector.on_simulation_start(state_with_tension, config)

        latest = collector.latest
        assert latest is not None
        assert latest.edges.exploitation_rent == 10.0

    def test_extracts_tribute_flow(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Extracts value_flow from TRIBUTE edge."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        latest = collector.latest
        assert latest is not None
        # Initial value_flow is 0.0
        assert latest.edges.tribute_flow >= 0.0

    def test_extracts_wages_paid(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Extracts value_flow from WAGES edge."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.edges.wages_paid >= 0.0

    def test_extracts_solidarity_strength(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Extracts solidarity_strength from SOLIDARITY edge."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        latest = collector.latest
        assert latest is not None
        # Default solidarity is 0.0 in imperial circuit
        assert latest.edges.solidarity_strength >= 0.0

    def test_handles_missing_edges_with_defaults(
        self,
        config: SimulationConfig,
    ) -> None:
        """Missing edges default to 0.0 values."""
        # Create minimal state with no relationships
        state = WorldState(tick=0, entities={}, relationships=[])

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.edges.exploitation_tension == 0.0
        assert latest.edges.exploitation_rent == 0.0
        assert latest.edges.tribute_flow == 0.0
        assert latest.edges.wages_paid == 0.0
        assert latest.edges.solidarity_strength == 0.0


# =============================================================================
# TEST GLOBAL METRICS
# =============================================================================


@pytest.mark.unit
class TestGlobalMetrics:
    """Tests for global metrics extraction."""

    def test_extracts_imperial_rent_pool(
        self,
        config: SimulationConfig,
    ) -> None:
        """Extracts imperial_rent_pool from state.economy."""
        economy = GlobalEconomy(imperial_rent_pool=100.0)
        state = WorldState(tick=0, economy=economy)

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.imperial_rent_pool == 100.0

    def test_calculates_global_tension_as_average(
        self,
        state_with_tension: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Calculates global_tension as average of all relationship tensions."""
        collector = MetricsCollector()
        collector.on_simulation_start(state_with_tension, config)

        latest = collector.latest
        assert latest is not None
        # At least one edge has tension 0.5
        assert latest.global_tension >= 0.0
        assert latest.global_tension <= 1.0

    def test_global_tension_is_zero_when_no_relationships(
        self,
        config: SimulationConfig,
    ) -> None:
        """Global tension is 0.0 when no relationships exist."""
        state = WorldState(tick=0, relationships=[])

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.global_tension == 0.0


# =============================================================================
# TEST SUMMARY CALCULATION
# =============================================================================


@pytest.mark.unit
class TestSummaryCalculation:
    """Tests for SweepSummary calculation from history."""

    def test_ticks_survived_equals_history_length(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """ticks_survived equals the number of recorded ticks."""
        collector = MetricsCollector(mode="batch")
        collector.on_simulation_start(four_node_state, config)

        # Add 5 ticks
        prev = four_node_state
        for i in range(5):
            new = prev.model_copy(update={"tick": i + 1})
            collector.on_tick(prev, new)
            prev = new

        summary = collector.summary
        assert summary is not None
        assert summary.ticks_survived == 6  # tick 0 + 5 steps

    def test_outcome_is_died_when_p_w_wealth_zero(
        self,
        config: SimulationConfig,
    ) -> None:
        """Outcome is 'DIED' when p_w wealth <= 0.001."""
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.enums import SocialRole

        # Create state with dead worker
        dead_worker = SocialClass(
            id="C001",
            name="Dead Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.0,  # Dead
            ideology=0.0,
            organization=0.1,
            repression_faced=0.5,
            subsistence_threshold=0.3,
        )
        state = WorldState(tick=0, entities={"C001": dead_worker})

        collector = MetricsCollector(mode="batch")
        collector.on_simulation_start(state, config)

        summary = collector.summary
        assert summary is not None
        assert summary.outcome == "DIED"

    def test_outcome_is_survived_when_p_w_wealth_positive(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Outcome is 'SURVIVED' when p_w wealth > 0.001."""
        collector = MetricsCollector(mode="batch")
        collector.on_simulation_start(four_node_state, config)

        summary = collector.summary
        assert summary is not None
        assert summary.outcome == "SURVIVED"

    def test_crossover_tick_detects_first_psr_greater_than_psa(
        self,
        config: SimulationConfig,
    ) -> None:
        """crossover_tick records first tick where P(S|R) > P(S|A)."""
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.enums import SocialRole

        # Create initial state with p_acquiescence > p_revolution
        worker_stable = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.5,
            ideology=0.0,
            organization=0.1,
            repression_faced=0.5,
            subsistence_threshold=0.3,
            p_acquiescence=0.8,
            p_revolution=0.2,
        )
        state0 = WorldState(tick=0, entities={"C001": worker_stable})

        # Create crossover state with p_revolution > p_acquiescence
        worker_crossover = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.3,
            ideology=-0.5,
            organization=0.5,
            repression_faced=0.3,
            subsistence_threshold=0.3,
            p_acquiescence=0.3,  # Now lower
            p_revolution=0.7,  # Now higher
        )
        state1 = WorldState(tick=1, entities={"C001": worker_crossover})

        collector = MetricsCollector(mode="batch")
        collector.on_simulation_start(state0, config)
        collector.on_tick(state0, state1)

        summary = collector.summary
        assert summary is not None
        assert summary.crossover_tick == 1

    def test_crossover_tick_is_none_when_no_crossover(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """crossover_tick is None when P(S|R) never exceeds P(S|A)."""
        collector = MetricsCollector(mode="batch")
        collector.on_simulation_start(four_node_state, config)

        summary = collector.summary
        assert summary is not None
        # With default scenario parameters, worker doesn't cross over
        assert summary.crossover_tick is None

    def test_max_tension_tracks_maximum(
        self,
        state_with_tension: WorldState,
        config: SimulationConfig,
    ) -> None:
        """max_tension is the maximum exploitation_tension across all ticks."""
        collector = MetricsCollector(mode="batch")
        collector.on_simulation_start(state_with_tension, config)

        summary = collector.summary
        assert summary is not None
        assert summary.max_tension == 0.5

    def test_cumulative_rent_sums_exploitation_rent(
        self,
        state_with_tension: WorldState,
        config: SimulationConfig,
    ) -> None:
        """cumulative_rent sums all exploitation_rent values."""
        collector = MetricsCollector(mode="batch")
        collector.on_simulation_start(state_with_tension, config)

        # Initial state has exploitation_rent = 10.0
        summary = collector.summary
        assert summary is not None
        assert summary.cumulative_rent == 10.0

    def test_peak_consciousness_tracks_maximum(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """peak_p_w_consciousness tracks maximum p_w consciousness."""
        collector = MetricsCollector(mode="batch")
        collector.on_simulation_start(four_node_state, config)

        summary = collector.summary
        assert summary is not None
        # Should be >= 0.0 (valid consciousness)
        assert summary.peak_p_w_consciousness >= 0.0


# =============================================================================
# TEST CSV EXPORT
# =============================================================================


@pytest.mark.unit
class TestCsvExport:
    """Tests for CSV export functionality."""

    def test_to_csv_rows_returns_list_of_dicts(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """to_csv_rows returns list of dictionaries."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        rows = collector.to_csv_rows()
        assert isinstance(rows, list)
        assert len(rows) == 1
        assert isinstance(rows[0], dict)

    def test_csv_rows_have_tick_key(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Each CSV row has a 'tick' key."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        rows = collector.to_csv_rows()
        assert "tick" in rows[0]
        assert rows[0]["tick"] == 0

    def test_csv_rows_flatten_entity_metrics(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Entity metrics are flattened to p_w_wealth, p_w_consciousness format."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        rows = collector.to_csv_rows()
        row = rows[0]

        # Should have flattened p_w fields
        assert "p_w_wealth" in row
        assert "p_w_consciousness" in row
        assert "p_w_national_identity" in row
        assert "p_w_agitation" in row
        assert "p_w_psa" in row  # p_acquiescence shortened
        assert "p_w_psr" in row  # p_revolution shortened
        assert "p_w_organization" in row

    def test_csv_rows_include_edge_metrics(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """CSV rows include edge metrics directly."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        rows = collector.to_csv_rows()
        row = rows[0]

        assert "exploitation_tension" in row
        assert "exploitation_rent" in row
        assert "tribute_flow" in row
        assert "wages_paid" in row
        assert "solidarity_strength" in row

    def test_csv_rows_compatible_with_parameter_analysis(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """CSV rows have format compatible with parameter_analysis.py.

        The column names should match those in collect_tick_data().
        """
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        rows = collector.to_csv_rows()
        row = rows[0]

        # These are the exact columns from parameter_analysis.py
        expected_columns = [
            "tick",
            "p_w_wealth",
            "p_w_consciousness",
            "p_w_national_identity",
            "p_w_agitation",
            "p_w_psa",
            "p_w_psr",
            "p_w_organization",
            "p_c_wealth",
            "c_b_wealth",
            "c_w_wealth",
            "c_w_consciousness",
            "c_w_national_identity",
            "c_w_agitation",
            "exploitation_tension",
            "exploitation_rent",
            "tribute_flow",
            "wages_paid",
            "solidarity_strength",
        ]

        for col in expected_columns:
            assert col in row, f"Missing expected column: {col}"


# =============================================================================
# TEST LIFECYCLE
# =============================================================================


@pytest.mark.unit
class TestLifecycle:
    """Tests for observer lifecycle hooks."""

    def test_on_simulation_start_clears_history(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """on_simulation_start clears any existing history."""
        collector = MetricsCollector()

        # First run
        collector.on_simulation_start(four_node_state, config)
        assert len(collector.history) == 1

        # Add some ticks
        prev = four_node_state
        for i in range(3):
            new = prev.model_copy(update={"tick": i + 1})
            collector.on_tick(prev, new)
            prev = new

        assert len(collector.history) == 4

        # Second run should clear
        collector.on_simulation_start(four_node_state, config)
        assert len(collector.history) == 1

    def test_on_simulation_start_records_tick_0(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """on_simulation_start records initial state as tick 0."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        assert len(collector.history) == 1
        assert collector.history[0].tick == 0

    def test_on_tick_appends_to_history(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """on_tick appends new metrics to history."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        tick1_state = four_node_state.model_copy(update={"tick": 1})
        collector.on_tick(four_node_state, tick1_state)

        assert len(collector.history) == 2
        assert collector.history[1].tick == 1

    def test_on_simulation_end_is_noop(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """on_simulation_end is a no-op (does not modify state)."""
        collector = MetricsCollector()
        collector.on_simulation_start(four_node_state, config)

        history_before = len(collector.history)

        # End simulation
        collector.on_simulation_end(four_node_state)

        # History should be unchanged
        assert len(collector.history) == history_before

    def test_multiple_runs_dont_accumulate(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Multiple simulation runs don't accumulate history."""
        collector = MetricsCollector()

        # Run 1
        collector.on_simulation_start(four_node_state, config)
        tick1 = four_node_state.model_copy(update={"tick": 1})
        collector.on_tick(four_node_state, tick1)
        collector.on_simulation_end(tick1)

        # Run 2
        collector.on_simulation_start(four_node_state, config)

        # Should only have 1 tick from new run
        assert len(collector.history) == 1


# =============================================================================
# TEST ERROR HANDLING
# =============================================================================


@pytest.mark.unit
class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_handles_empty_entities(
        self,
        config: SimulationConfig,
    ) -> None:
        """Handles state with no entities gracefully."""
        state = WorldState(tick=0, entities={})

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.p_w is None
        assert latest.p_c is None
        assert latest.c_b is None
        assert latest.c_w is None

    def test_handles_empty_relationships(
        self,
        config: SimulationConfig,
    ) -> None:
        """Handles state with no relationships gracefully."""
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.enums import SocialRole

        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.5,
        )
        state = WorldState(tick=0, entities={"C001": worker}, relationships=[])

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.edges.exploitation_tension == 0.0

    def test_summary_handles_empty_history(self) -> None:
        """Summary returns None for empty collector."""
        collector = MetricsCollector()
        assert collector.summary is None


# =============================================================================
# TEST INTEGRATION WITH SIMULATION
# =============================================================================


@pytest.mark.unit
class TestSimulationIntegration:
    """Integration tests with the Simulation facade."""

    def test_can_register_with_simulation(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """MetricsCollector can be registered with Simulation."""
        from babylon.engine.simulation import Simulation

        collector = MetricsCollector()
        sim = Simulation(four_node_state, config, observers=[collector])

        assert collector in sim.observers

    def test_receives_notifications_during_simulation(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """MetricsCollector receives notifications during simulation steps."""
        from babylon.engine.simulation import Simulation

        collector = MetricsCollector()
        sim = Simulation(four_node_state, config, observers=[collector])

        # Run a step
        sim.step()

        # Should have recorded start and tick
        assert len(collector.history) == 2  # tick 0 (start) + tick 1

    def test_captures_metrics_after_step(
        self,
        four_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Metrics are captured after each simulation step."""
        from babylon.engine.simulation import Simulation

        collector = MetricsCollector(mode="batch")
        sim = Simulation(four_node_state, config, observers=[collector])

        # Run 5 steps
        for _ in range(5):
            sim.step()

        # Should have 6 entries (tick 0 + 5 steps)
        assert len(collector.history) == 6

        # Ticks should be sequential
        for i, metrics in enumerate(collector.history):
            assert metrics.tick == i


# =============================================================================
# BATCH 4: ECONOMY DRIVER EXTRACTION TESTS (Phase 4.1B)
# =============================================================================


@pytest.mark.unit
class TestEconomyDriverExtraction:
    """Tests for economy driver extraction from WorldState.

    Phase 4.1B: Expose Meaningful Metrics - Economy Driver Extraction.
    These tests verify that the MetricsCollector correctly extracts
    economy driver values from the simulation state.
    """

    def test_extracts_current_super_wage_rate_from_economy(
        self,
        config: SimulationConfig,
    ) -> None:
        """Extracts current_super_wage_rate from state.economy.

        The super-wage rate is extracted from GlobalEconomy.super_wage_rate.
        """
        economy = GlobalEconomy(super_wage_rate=0.25)
        state = WorldState(tick=0, economy=economy)

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.current_super_wage_rate == 0.25

    def test_extracts_current_repression_level_from_economy(
        self,
        config: SimulationConfig,
    ) -> None:
        """Extracts current_repression_level from state.economy.

        The repression level is extracted from GlobalEconomy.repression_level.
        """
        economy = GlobalEconomy(repression_level=0.7)
        state = WorldState(tick=0, economy=economy)

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.current_repression_level == 0.7

    def test_calculates_pool_ratio_from_economy(
        self,
        config: SimulationConfig,
    ) -> None:
        """Calculates pool_ratio as imperial_rent_pool / initial_pool.

        The pool ratio indicates how depleted the rent pool is.
        """
        economy = GlobalEconomy(imperial_rent_pool=80.0, initial_pool=100.0)
        state = WorldState(tick=0, economy=economy)

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.pool_ratio == 0.8

    def test_pool_ratio_uses_100_as_initial_pool_default(
        self,
        config: SimulationConfig,
    ) -> None:
        """pool_ratio uses 100.0 as the default initial pool.

        When initial_pool is not specified, use 100.0 as the denominator.
        """
        economy = GlobalEconomy(imperial_rent_pool=50.0)
        state = WorldState(tick=0, economy=economy)

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        # 50 / 100 = 0.5
        assert latest.pool_ratio == 0.5

    def test_pool_ratio_clamped_to_one(
        self,
        config: SimulationConfig,
    ) -> None:
        """pool_ratio is clamped to max 1.0.

        Even if imperial_rent_pool exceeds initial_pool (e.g., due to
        external injection), the ratio is clamped to 1.0.
        """
        economy = GlobalEconomy(imperial_rent_pool=150.0, initial_pool=100.0)
        state = WorldState(tick=0, economy=economy)

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.pool_ratio == 1.0  # Clamped from 1.5

    def test_handles_missing_economy_gracefully(
        self,
        config: SimulationConfig,
    ) -> None:
        """Returns default values when state.economy is None.

        When economy is not set, use default values for all economy drivers.
        """
        state = WorldState(tick=0)  # No economy

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        # Default values when economy is missing
        assert latest.current_super_wage_rate == 0.2
        assert latest.current_repression_level == 0.5
        assert latest.pool_ratio == 1.0


# =============================================================================
# BATCH 5: DIFFERENTIAL CALCULATION TESTS (Phase 4.1B)
# =============================================================================


@pytest.mark.unit
class TestDifferentialCalculation:
    """Tests for derived differential calculations.

    Phase 4.1B: Expose Meaningful Metrics - Differential Calculation.
    These tests verify that the MetricsCollector correctly computes
    derived differentials from entity values.
    """

    def test_calculates_consciousness_gap(
        self,
        config: SimulationConfig,
    ) -> None:
        """Calculates consciousness_gap as P_w.consciousness - C_w.consciousness.

        The consciousness gap measures how far ahead the periphery worker is
        in class consciousness compared to the labor aristocracy.
        """
        from babylon.models.entities.social_class import (
            IdeologicalProfile,
            SocialClass,
        )
        from babylon.models.enums import SocialRole

        # Periphery worker with consciousness 0.7
        p_w = SocialClass(
            id="C001",
            name="Periphery Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.5,
            ideology=IdeologicalProfile(class_consciousness=0.7),  # Higher consciousness
        )
        # Labor aristocracy with consciousness 0.3
        c_w = SocialClass(
            id="C004",
            name="Labor Aristocracy",
            role=SocialRole.LABOR_ARISTOCRACY,
            wealth=0.6,
            ideology=IdeologicalProfile(class_consciousness=0.3),  # Lower consciousness
        )
        state = WorldState(tick=0, entities={"C001": p_w, "C004": c_w})

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        # 0.7 - 0.3 = 0.4
        assert abs(latest.consciousness_gap - 0.4) < 0.001

    def test_consciousness_gap_handles_missing_p_w(
        self,
        config: SimulationConfig,
    ) -> None:
        """Returns 0.0 for consciousness_gap when P_w is missing.

        When the periphery worker entity is not present, default to 0.0.
        """
        from babylon.models.entities.social_class import (
            IdeologicalProfile,
            SocialClass,
        )
        from babylon.models.enums import SocialRole

        # Only labor aristocracy, no periphery worker
        c_w = SocialClass(
            id="C004",
            name="Labor Aristocracy",
            role=SocialRole.LABOR_ARISTOCRACY,
            wealth=0.6,
            ideology=IdeologicalProfile(class_consciousness=0.3),
        )
        state = WorldState(tick=0, entities={"C004": c_w})

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.consciousness_gap == 0.0

    def test_consciousness_gap_handles_missing_c_w(
        self,
        config: SimulationConfig,
    ) -> None:
        """Returns 0.0 for consciousness_gap when C_w is missing.

        When the labor aristocracy entity is not present, default to 0.0.
        """
        from babylon.models.entities.social_class import (
            IdeologicalProfile,
            SocialClass,
        )
        from babylon.models.enums import SocialRole

        # Only periphery worker, no labor aristocracy
        p_w = SocialClass(
            id="C001",
            name="Periphery Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.5,
            ideology=IdeologicalProfile(class_consciousness=0.7),
        )
        state = WorldState(tick=0, entities={"C001": p_w})

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.consciousness_gap == 0.0

    def test_calculates_wealth_gap(
        self,
        config: SimulationConfig,
    ) -> None:
        """Calculates wealth_gap as C_b.wealth - P_w.wealth.

        The wealth gap measures the wealth differential between the
        core bourgeoisie and the periphery worker.
        """
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.enums import SocialRole

        # Periphery worker with wealth 0.2
        p_w = SocialClass(
            id="C001",
            name="Periphery Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.2,
        )
        # Core bourgeoisie with wealth 0.9
        c_b = SocialClass(
            id="C003",
            name="Core Bourgeoisie",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=0.9,
        )
        state = WorldState(tick=0, entities={"C001": p_w, "C003": c_b})

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        # 0.9 - 0.2 = 0.7
        assert abs(latest.wealth_gap - 0.7) < 0.001

    def test_wealth_gap_handles_missing_entities(
        self,
        config: SimulationConfig,
    ) -> None:
        """Returns 0.0 for wealth_gap when either entity is missing.

        When P_w or C_b is not present, default to 0.0.
        """
        state = WorldState(tick=0, entities={})

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.wealth_gap == 0.0


# =============================================================================
# BATCH 6: GLOBAL TENSION BUG FIX TESTS (Phase 4.1B)
# =============================================================================


@pytest.mark.unit
class TestGlobalTensionBugFix:
    """Tests for global_tension calculation bug fix.

    Phase 4.1B: Bug Fix - global_tension should only average EXPLOITATION edges.
    The current implementation incorrectly averages all edge tensions,
    including SOLIDARITY, WAGES, etc., which dilutes the metric.
    """

    def test_global_tension_only_averages_exploitation_edges(
        self,
        config: SimulationConfig,
    ) -> None:
        """global_tension should only average EXPLOITATION edge tensions.

        EXPLOITATION edges represent the core class antagonism; other edge
        types should not factor into global tension.
        """
        from babylon.models.entities.relationship import Relationship

        # Create state with one EXPLOITATION edge (tension 0.8)
        # and one SOLIDARITY edge (tension 0.2)
        exploitation_edge = Relationship(
            source_id="C003",
            target_id="C001",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.8,
            value_flow=10.0,
        )
        solidarity_edge = Relationship(
            source_id="C001",
            target_id="C004",
            edge_type=EdgeType.SOLIDARITY,
            tension=0.2,  # Should be IGNORED
            value_flow=0.0,
        )
        state = WorldState(
            tick=0,
            relationships=[exploitation_edge, solidarity_edge],
        )

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        # Only EXPLOITATION tension matters: 0.8
        assert latest.global_tension == 0.8

    def test_global_tension_ignores_solidarity_edges(
        self,
        config: SimulationConfig,
    ) -> None:
        """global_tension ignores SOLIDARITY edge tensions.

        SOLIDARITY represents mutual support, not class antagonism.
        """
        from babylon.models.entities.relationship import Relationship

        solidarity_edge = Relationship(
            source_id="C001",
            target_id="C004",
            edge_type=EdgeType.SOLIDARITY,
            tension=0.9,  # High tension on SOLIDARITY (should be ignored)
            value_flow=0.0,
        )
        state = WorldState(tick=0, relationships=[solidarity_edge])

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        # No EXPLOITATION edges, so tension is 0.0
        assert latest.global_tension == 0.0

    def test_global_tension_ignores_wages_edges(
        self,
        config: SimulationConfig,
    ) -> None:
        """global_tension ignores WAGES edge tensions.

        WAGES represents payment to labor aristocracy, not exploitation.
        """
        from babylon.models.entities.relationship import Relationship

        wages_edge = Relationship(
            source_id="C003",
            target_id="C004",
            edge_type=EdgeType.WAGES,
            tension=0.7,  # Should be ignored
            value_flow=5.0,
        )
        state = WorldState(tick=0, relationships=[wages_edge])

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.global_tension == 0.0

    def test_global_tension_zero_when_no_exploitation_edges(
        self,
        config: SimulationConfig,
    ) -> None:
        """global_tension is 0.0 when no EXPLOITATION edges exist.

        With no exploitation relationships, there is no class tension
        to measure.
        """
        from babylon.models.entities.relationship import Relationship

        # Only non-exploitation edges
        tribute_edge = Relationship(
            source_id="C002",
            target_id="C003",
            edge_type=EdgeType.TRIBUTE,
            tension=0.5,
            value_flow=10.0,
        )
        state = WorldState(tick=0, relationships=[tribute_edge])

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        assert latest.global_tension == 0.0

    def test_global_tension_multiple_exploitation_edges(
        self,
        config: SimulationConfig,
    ) -> None:
        """global_tension averages multiple EXPLOITATION edge tensions.

        When multiple exploitation relationships exist, average their tensions.
        """
        from babylon.models.entities.relationship import Relationship

        # Two EXPLOITATION edges with different tensions
        expl1 = Relationship(
            source_id="C003",
            target_id="C001",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.4,
            value_flow=10.0,
        )
        expl2 = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.8,
            value_flow=5.0,
        )
        state = WorldState(tick=0, relationships=[expl1, expl2])

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        # Average: (0.4 + 0.8) / 2 = 0.6
        assert abs(latest.global_tension - 0.6) < 0.001


# =============================================================================
# BATCH 7: EDGE AGGREGATION FIX TESTS (Phase 4.1B)
# =============================================================================


@pytest.mark.unit
class TestEdgeAggregationFix:
    """Tests for edge aggregation in EdgeMetrics.

    Phase 4.1B: Bug Fix - Multiple edges of the same type should be aggregated.
    When multiple EXPLOITATION, TRIBUTE, or SOLIDARITY edges exist, their
    values should be aggregated correctly (max for tension, sum for flows).
    """

    def test_aggregates_multiple_exploitation_tensions(
        self,
        config: SimulationConfig,
    ) -> None:
        """exploitation_tension uses max() across all EXPLOITATION edges.

        When multiple exploitation relationships exist, use the maximum
        tension to reflect the most volatile relationship.
        """
        from babylon.models.entities.relationship import Relationship

        expl1 = Relationship(
            source_id="C003",
            target_id="C001",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.3,
            value_flow=10.0,
        )
        expl2 = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.7,  # Higher tension
            value_flow=5.0,
        )
        state = WorldState(tick=0, relationships=[expl1, expl2])

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        # Max: max(0.3, 0.7) = 0.7
        assert latest.edges.exploitation_tension == 0.7

    def test_aggregates_multiple_exploitation_rents(
        self,
        config: SimulationConfig,
    ) -> None:
        """exploitation_rent uses sum() across all EXPLOITATION edges.

        Total imperial rent extracted is the sum of all exploitation flows.
        """
        from babylon.models.entities.relationship import Relationship

        expl1 = Relationship(
            source_id="C003",
            target_id="C001",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.3,
            value_flow=10.0,
        )
        expl2 = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.7,
            value_flow=5.0,
        )
        state = WorldState(tick=0, relationships=[expl1, expl2])

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        # Sum: 10.0 + 5.0 = 15.0
        assert latest.edges.exploitation_rent == 15.0

    def test_aggregates_multiple_tribute_flows(
        self,
        config: SimulationConfig,
    ) -> None:
        """tribute_flow uses sum() across all TRIBUTE edges.

        Total tribute is the sum of all comprador-to-core flows.
        """
        from babylon.models.entities.relationship import Relationship

        trib1 = Relationship(
            source_id="C002",
            target_id="C003",
            edge_type=EdgeType.TRIBUTE,
            tension=0.0,
            value_flow=8.0,
        )
        trib2 = Relationship(
            source_id="C005",  # Another comprador
            target_id="C003",
            edge_type=EdgeType.TRIBUTE,
            tension=0.0,
            value_flow=12.0,
        )
        state = WorldState(tick=0, relationships=[trib1, trib2])

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        # Sum: 8.0 + 12.0 = 20.0
        assert latest.edges.tribute_flow == 20.0

    def test_aggregates_multiple_solidarity_strengths(
        self,
        config: SimulationConfig,
    ) -> None:
        """solidarity_strength uses max() across all SOLIDARITY edges.

        The solidarity network's strength is its strongest link.
        """
        from babylon.models.entities.relationship import Relationship

        sol1 = Relationship(
            source_id="C001",
            target_id="C004",
            edge_type=EdgeType.SOLIDARITY,
            tension=0.0,
            solidarity_strength=0.4,
        )
        sol2 = Relationship(
            source_id="C001",
            target_id="C005",
            edge_type=EdgeType.SOLIDARITY,
            tension=0.0,
            solidarity_strength=0.8,  # Stronger link
        )
        state = WorldState(tick=0, relationships=[sol1, sol2])

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        latest = collector.latest
        assert latest is not None
        # Max: max(0.4, 0.8) = 0.8
        assert latest.edges.solidarity_strength == 0.8

    def test_csv_export_includes_aggregated_values(
        self,
        config: SimulationConfig,
    ) -> None:
        """CSV export includes properly aggregated edge values.

        The to_csv_rows() method should reflect aggregated values,
        not just the first edge encountered.
        """
        from babylon.models.entities.relationship import Relationship

        expl1 = Relationship(
            source_id="C003",
            target_id="C001",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.3,
            value_flow=10.0,
        )
        expl2 = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.7,
            value_flow=5.0,
        )
        state = WorldState(tick=0, relationships=[expl1, expl2])

        collector = MetricsCollector()
        collector.on_simulation_start(state, config)

        rows = collector.to_csv_rows()
        assert len(rows) == 1
        row = rows[0]

        # Aggregated values in CSV
        assert row["exploitation_tension"] == 0.7  # max
        assert row["exploitation_rent"] == 15.0  # sum
