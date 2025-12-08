"""Tests for babylon.engine.simulation Simulation facade class.

TDD Red Phase: These tests define the contract for the Simulation facade
that wraps ServiceContainer and provides a convenient API for running
multi-tick simulations with history preservation.
"""

import pytest

from babylon.engine.services import ServiceContainer
from babylon.models import (
    EdgeType,
    Relationship,
    SimulationConfig,
    SocialClass,
    SocialRole,
    WorldState,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def worker() -> SocialClass:
    """Create a periphery worker social class."""
    return SocialClass(
        id="C001",
        name="Worker",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=0.5,
        ideology=0.0,
        organization=0.1,
        repression_faced=0.5,
        subsistence_threshold=0.3,
    )


@pytest.fixture
def owner() -> SocialClass:
    """Create a core owner social class."""
    return SocialClass(
        id="C002",
        name="Owner",
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=10.0,
        ideology=0.5,
        organization=0.7,
        repression_faced=0.1,
        subsistence_threshold=0.1,
    )


@pytest.fixture
def exploitation_edge() -> Relationship:
    """Create an exploitation relationship from worker to owner."""
    return Relationship(
        source_id="C001",
        target_id="C002",
        edge_type=EdgeType.EXPLOITATION,
        value_flow=0.0,
        tension=0.0,
    )


@pytest.fixture
def initial_state(
    worker: SocialClass,
    owner: SocialClass,
    exploitation_edge: Relationship,
) -> WorldState:
    """Create initial WorldState with two nodes and one edge."""
    return WorldState(
        tick=0,
        entities={"C001": worker, "C002": owner},
        relationships=[exploitation_edge],
    )


@pytest.fixture
def config() -> SimulationConfig:
    """Create default simulation config."""
    return SimulationConfig()


# =============================================================================
# TEST SIMULATION CREATION
# =============================================================================


@pytest.mark.unit
class TestSimulationCreation:
    """Tests for Simulation class creation and initialization."""

    def test_creates_service_container(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Simulation creates and holds a ServiceContainer."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        assert sim.services is not None
        assert isinstance(sim.services, ServiceContainer)

    def test_holds_initial_state(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Simulation holds the initial state."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        assert sim.current_state == initial_state

    def test_holds_config(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Simulation holds the config."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        assert sim.config == config

    def test_services_config_matches(
        self,
        initial_state: WorldState,
    ) -> None:
        """ServiceContainer config matches the provided config."""
        from babylon.engine.simulation import Simulation

        custom_config = SimulationConfig(extraction_efficiency=0.5)
        sim = Simulation(initial_state, custom_config)
        assert sim.services.config.extraction_efficiency == pytest.approx(0.5)


# =============================================================================
# TEST SIMULATION STEP
# =============================================================================


@pytest.mark.unit
class TestSimulationStep:
    """Tests for Simulation.step() method."""

    def test_step_advances_tick(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """step() advances the tick counter by 1."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        assert sim.current_state.tick == 0

        sim.step()
        assert sim.current_state.tick == 1

    def test_step_returns_new_state(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """step() returns the new WorldState."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        new_state = sim.step()

        assert new_state is not initial_state
        assert new_state.tick == 1

    def test_step_updates_current_state(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """step() updates current_state property."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        new_state = sim.step()

        assert sim.current_state is new_state

    def test_multiple_steps_increment_correctly(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Multiple step() calls increment tick correctly."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        sim.step()
        sim.step()
        sim.step()

        assert sim.current_state.tick == 3


# =============================================================================
# TEST SIMULATION RUN
# =============================================================================


@pytest.mark.unit
class TestSimulationRun:
    """Tests for Simulation.run() method."""

    def test_run_executes_n_ticks(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """run(n) executes exactly n ticks."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        sim.run(10)

        assert sim.current_state.tick == 10

    def test_run_returns_final_state(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """run() returns the final WorldState."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        final_state = sim.run(5)

        assert final_state.tick == 5
        assert final_state is sim.current_state

    def test_run_zero_ticks_no_change(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """run(0) does not change state."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        sim.run(0)

        assert sim.current_state.tick == 0

    def test_run_100_ticks(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """run(100) executes 100 ticks successfully."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        final_state = sim.run(100)

        assert final_state.tick == 100


# =============================================================================
# TEST HISTORY PRESERVATION
# =============================================================================


@pytest.mark.unit
class TestSimulationHistory:
    """Tests for Simulation history preservation."""

    def test_preserves_event_history_across_ticks(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Event history accumulates across ticks."""
        from babylon.engine.simulation import Simulation

        # Start with an event in the log
        state_with_event = initial_state.add_event("Initial event")
        sim = Simulation(state_with_event, config)

        sim.run(5)

        # Initial event should still be in the log
        assert "Initial event" in sim.current_state.event_log

    def test_get_history_returns_all_states(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """get_history() returns all WorldState snapshots."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        sim.run(5)

        history = sim.get_history()

        # Should have 6 states: initial (tick 0) + 5 steps
        assert len(history) == 6
        assert history[0].tick == 0
        assert history[5].tick == 5

    def test_history_contains_initial_state(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """History includes the initial state at tick 0."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        sim.run(3)

        history = sim.get_history()
        assert history[0] == initial_state

    def test_history_preserves_entity_values(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """History snapshots preserve entity values at each tick."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        initial_worker_wealth = initial_state.entities["C001"].wealth

        sim.run(10)
        history = sim.get_history()

        # Initial state should have original wealth
        assert history[0].entities["C001"].wealth == pytest.approx(initial_worker_wealth)

        # Later states should show wealth changes
        # Worker loses wealth through extraction
        assert history[10].entities["C001"].wealth < initial_worker_wealth

    def test_step_also_records_history(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Individual step() calls also record history."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        sim.step()
        sim.step()

        history = sim.get_history()
        assert len(history) == 3  # initial + 2 steps


# =============================================================================
# TEST SERVICE CONTAINER PERSISTENCE
# =============================================================================


@pytest.mark.unit
class TestServiceContainerPersistence:
    """Tests that ServiceContainer persists across ticks."""

    def test_services_same_across_steps(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Same ServiceContainer instance is used across steps."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        services_before = sim.services

        sim.step()
        sim.step()

        assert sim.services is services_before

    def test_services_same_after_run(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Same ServiceContainer instance after run()."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        services_before = sim.services

        sim.run(50)

        assert sim.services is services_before
