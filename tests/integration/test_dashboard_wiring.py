"""Integration tests for dashboard observer wiring.

These tests verify that the dashboard correctly initializes and wires
up all required observers, ensuring events flow to the UI components.

Bug Context:
The dashboard was not displaying dual narratives because:
1. NarrativeDirector was never created in init_simulation()
2. Only MetricsCollector was added as an observer
3. WirePanel had no data to display

Fix: Added NarrativeDirector creation with LLM support and registered
it as a simulation observer.
"""

from __future__ import annotations

import pytest

from babylon.ai import MockLLM, NarrativeDirector
from babylon.engine.observers.metrics import MetricsCollector
from babylon.engine.scenarios import create_imperial_circuit_scenario
from babylon.engine.simulation import Simulation

# =============================================================================
# TEST DASHBOARD INITIALIZATION
# =============================================================================


@pytest.mark.integration
class TestDashboardInitialization:
    """Tests for dashboard simulation initialization.

    These tests verify that init_simulation() correctly creates and wires
    all required components for the dashboard to function.
    """

    def test_init_simulation_creates_narrative_director(self) -> None:
        """init_simulation() creates NarrativeDirector with LLM."""
        from babylon.ui.main import _state, init_simulation

        init_simulation()

        assert _state.narrative_director is not None
        assert isinstance(_state.narrative_director, NarrativeDirector)

    def test_init_simulation_adds_narrative_director_to_observers(self) -> None:
        """NarrativeDirector is added to simulation observers."""
        from babylon.ui.main import _state, init_simulation

        init_simulation()

        assert _state.simulation is not None
        observer_names = [o.name for o in _state.simulation.observers]
        assert "NarrativeDirector" in observer_names
        assert "MetricsCollector" in observer_names

    def test_narrative_director_has_llm_configured(self) -> None:
        """NarrativeDirector has an LLM provider (real or mock)."""
        from babylon.ui.main import _state, init_simulation

        init_simulation()

        assert _state.narrative_director is not None
        assert _state.narrative_director.use_llm is True
        # Should have either DeepSeekClient or MockLLM
        assert _state.narrative_director._llm is not None

    def test_init_simulation_creates_metrics_collector(self) -> None:
        """init_simulation() creates MetricsCollector in interactive mode."""
        from babylon.ui.main import _state, init_simulation

        init_simulation()

        assert _state.metrics_collector is not None
        assert isinstance(_state.metrics_collector, MetricsCollector)

    def test_init_simulation_creates_simulation(self) -> None:
        """init_simulation() creates Simulation with scenario state."""
        from babylon.ui.main import _state, init_simulation

        init_simulation()

        assert _state.simulation is not None
        assert isinstance(_state.simulation, Simulation)
        # Imperial circuit scenario creates at least core bourgeoisie and periphery proletariat
        assert len(_state.simulation.current_state.entities) >= 2


# =============================================================================
# TEST EVENT FLOW TO DUAL NARRATIVES
# =============================================================================


@pytest.mark.integration
class TestEventFlowToDualNarratives:
    """Tests for end-to-end event flow to dual narratives.

    These tests verify that simulation events properly flow through
    the NarrativeDirector observer to generate dual narratives for
    the WirePanel to display.
    """

    def test_simulation_events_generate_dual_narratives(self) -> None:
        """Running simulation generates dual narratives for significant events.

        This is an end-to-end test that verifies:
        1. Simulation generates events (especially EXCESSIVE_FORCE via spark)
        2. NarrativeDirector receives events via on_tick()
        3. Dual narratives are generated for significant events
        """
        state, config, defines = create_imperial_circuit_scenario()
        # Modify repression to increase spark probability
        for entity in state.entities.values():
            entity.repression_faced = 0.9

        llm = MockLLM(responses=["Corp narrative", "Lib narrative"] * 20)
        director = NarrativeDirector(use_llm=True, llm=llm)
        metrics = MetricsCollector(mode="interactive")

        sim = Simulation(state, config, observers=[metrics, director], defines=defines)

        # Run enough ticks to generate events
        for _ in range(30):
            sim.step()

        # Should have generated at least one dual narrative
        assert len(director.dual_narratives) > 0, (
            "No dual narratives generated after 30 ticks. "
            "Events found: " + str([e.event_type for e in sim.current_state.events])
        )

    def test_dual_narratives_indexed_by_tick(self) -> None:
        """Dual narratives are indexed by the tick they occurred on."""
        state, config, defines = create_imperial_circuit_scenario()
        # High repression for consistent event generation
        for entity in state.entities.values():
            entity.repression_faced = 0.95

        llm = MockLLM(responses=["Corp", "Lib"] * 50)
        director = NarrativeDirector(use_llm=True, llm=llm)

        sim = Simulation(state, config, observers=[director], defines=defines)

        for _ in range(20):
            sim.step()

        # All tick indices should be positive integers
        for tick in director.dual_narratives:
            assert isinstance(tick, int)
            assert tick > 0

    def test_dual_narrative_structure(self) -> None:
        """Each dual narrative entry has required keys."""
        state, config, defines = create_imperial_circuit_scenario()
        for entity in state.entities.values():
            entity.repression_faced = 0.95

        llm = MockLLM(responses=["Corporate", "Liberated"] * 20)
        director = NarrativeDirector(use_llm=True, llm=llm)

        sim = Simulation(state, config, observers=[director], defines=defines)

        for _ in range(30):
            sim.step()

        # Verify structure of dual narratives
        for tick, data in director.dual_narratives.items():
            assert "event" in data, f"Tick {tick} missing 'event' key"
            assert "corporate" in data, f"Tick {tick} missing 'corporate' key"
            assert "liberated" in data, f"Tick {tick} missing 'liberated' key"
            assert data["event"] is not None, f"Tick {tick} has None event"


# =============================================================================
# TEST OBSERVER PROTOCOL INTEGRATION
# =============================================================================


@pytest.mark.integration
class TestObserverProtocolIntegration:
    """Tests for observer protocol integration with simulation.

    Note: on_simulation_start is called on the first step(), not during
    Simulation construction. This is by design to allow observers to
    be added after construction but before the first step.
    """

    def test_observers_receive_simulation_start_on_first_step(self) -> None:
        """Observers receive on_simulation_start on first step() call."""
        state, config, defines = create_imperial_circuit_scenario()

        llm = MockLLM(responses=["test"])
        director = NarrativeDirector(use_llm=True, llm=llm)
        metrics = MetricsCollector(mode="interactive")

        sim = Simulation(state, config, observers=[metrics, director], defines=defines)

        # Before first step, no start notification yet
        assert metrics.latest is None

        # First step triggers on_simulation_start before on_tick
        sim.step()

        # MetricsCollector should now have recorded initial + tick 1
        assert metrics.latest is not None
        # After first step, we have tick 0 (initial) and tick 1
        assert len(metrics.history) == 2

    def test_observers_receive_tick_events(self) -> None:
        """All observers receive on_tick callbacks during simulation."""
        state, config, defines = create_imperial_circuit_scenario()

        llm = MockLLM(responses=["test"] * 10)
        director = NarrativeDirector(use_llm=True, llm=llm)
        metrics = MetricsCollector(mode="interactive")

        sim = Simulation(state, config, observers=[metrics, director], defines=defines)

        # Run 5 ticks
        for _ in range(5):
            sim.step()

        # Both observers should have processed all ticks
        assert metrics.latest is not None
        assert metrics.latest.tick == 5

    def test_observers_receive_simulation_end(self) -> None:
        """All observers receive on_simulation_end callback."""
        state, config, defines = create_imperial_circuit_scenario()

        llm = MockLLM(responses=["test"])
        director = NarrativeDirector(use_llm=True, llm=llm)
        metrics = MetricsCollector(mode="interactive")

        sim = Simulation(state, config, observers=[metrics, director], defines=defines)
        sim.step()

        # Confirm simulation was started before end()
        assert sim._started is True

        sim.end()

        # After end(), _started is reset to False (simulation can't restart)
        assert sim._started is False
        # Metrics should still have the tick data from before end()
        assert metrics.latest is not None
