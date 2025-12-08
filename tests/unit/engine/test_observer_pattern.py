"""Tests for SimulationObserver protocol and Simulation observer integration.

TDD Red Phase: These tests define the contract for the Observer Pattern
that allows AI components to observe simulation state changes without
modifying the simulation mechanics.

Design Decisions (from Sprint 3.1 Plan):
- Observer location: Simulation facade ONLY (step() remains pure)
- Notification order: After state reconstruction
- Error handling: Log and ignore (ADR003: "AI failures don't break game")
- Lifecycle hooks: on_simulation_start, on_tick, on_simulation_end
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState

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


class MockObserver:
    """Test double implementing SimulationObserver protocol."""

    def __init__(self, name: str = "MockObserver") -> None:
        self._name = name
        self.start_calls: list[tuple[WorldState, SimulationConfig]] = []
        self.tick_calls: list[tuple[WorldState, WorldState]] = []
        self.end_calls: list[WorldState] = []

    @property
    def name(self) -> str:
        """Return observer identifier."""
        return self._name

    def on_simulation_start(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Record start notification."""
        self.start_calls.append((initial_state, config))

    def on_tick(
        self,
        previous_state: WorldState,
        new_state: WorldState,
    ) -> None:
        """Record tick notification."""
        self.tick_calls.append((previous_state, new_state))

    def on_simulation_end(self, final_state: WorldState) -> None:
        """Record end notification."""
        self.end_calls.append(final_state)


class FailingObserver:
    """Observer that raises exceptions to test error handling."""

    def __init__(self, name: str = "FailingObserver") -> None:
        self._name = name

    @property
    def name(self) -> str:
        """Return observer identifier."""
        return self._name

    def on_simulation_start(
        self,
        _initial_state: WorldState,
        _config: SimulationConfig,
    ) -> None:
        """Always raise exception."""
        raise RuntimeError("FailingObserver.on_simulation_start failed")

    def on_tick(
        self,
        _previous_state: WorldState,
        _new_state: WorldState,
    ) -> None:
        """Always raise exception."""
        raise RuntimeError("FailingObserver.on_tick failed")

    def on_simulation_end(self, _final_state: WorldState) -> None:
        """Always raise exception."""
        raise RuntimeError("FailingObserver.on_simulation_end failed")


# =============================================================================
# TEST PROTOCOL VERIFICATION
# =============================================================================


@pytest.mark.unit
class TestObserverProtocol:
    """Tests for SimulationObserver protocol definition."""

    def test_observer_protocol_is_runtime_checkable(self) -> None:
        """SimulationObserver protocol is runtime_checkable for isinstance checks."""
        from babylon.engine.observer import SimulationObserver

        observer = MockObserver()
        assert isinstance(observer, SimulationObserver)

    def test_mock_observer_satisfies_protocol(self) -> None:
        """MockObserver implementation satisfies SimulationObserver protocol."""
        from babylon.engine.observer import SimulationObserver

        observer = MockObserver("TestObserver")
        assert isinstance(observer, SimulationObserver)
        assert observer.name == "TestObserver"

    def test_protocol_requires_name_property(self) -> None:
        """Protocol requires name property."""
        from babylon.engine.observer import SimulationObserver

        class MissingName:
            def on_simulation_start(
                self, initial_state: WorldState, config: SimulationConfig
            ) -> None:
                pass

            def on_tick(self, previous_state: WorldState, new_state: WorldState) -> None:
                pass

            def on_simulation_end(self, final_state: WorldState) -> None:
                pass

        assert not isinstance(MissingName(), SimulationObserver)


# =============================================================================
# TEST OBSERVER REGISTRATION
# =============================================================================


@pytest.mark.unit
class TestSimulationObserverRegistration:
    """Tests for Simulation observer registration."""

    def test_simulation_accepts_observers_in_constructor(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Simulation accepts observers list in constructor."""
        from babylon.engine.simulation import Simulation

        observer = MockObserver()
        sim = Simulation(initial_state, config, observers=[observer])

        assert observer in sim.observers

    def test_simulation_add_observer_method(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Simulation.add_observer() registers observer dynamically."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        observer = MockObserver()

        sim.add_observer(observer)

        assert observer in sim.observers

    def test_simulation_remove_observer_method(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Simulation.remove_observer() unregisters observer."""
        from babylon.engine.simulation import Simulation

        observer = MockObserver()
        sim = Simulation(initial_state, config, observers=[observer])

        sim.remove_observer(observer)

        assert observer not in sim.observers

    def test_simulation_remove_nonexistent_observer_no_error(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Removing non-existent observer does not raise error."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config)
        observer = MockObserver()

        # Should not raise
        sim.remove_observer(observer)

    def test_simulation_observers_property_returns_copy(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """observers property returns copy to preserve encapsulation."""
        from babylon.engine.simulation import Simulation

        observer = MockObserver()
        sim = Simulation(initial_state, config, observers=[observer])

        # Modify the returned list
        observers_copy = sim.observers
        observers_copy.clear()

        # Original should be unchanged
        assert len(sim.observers) == 1


# =============================================================================
# TEST NOTIFICATION BEHAVIOR
# =============================================================================


@pytest.mark.unit
class TestObserverNotification:
    """Tests for observer notification during simulation."""

    def test_observer_receives_on_tick_call(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Observer receives on_tick call after step()."""
        from babylon.engine.simulation import Simulation

        observer = MockObserver()
        sim = Simulation(initial_state, config, observers=[observer])

        sim.step()

        assert len(observer.tick_calls) == 1

    def test_observer_receives_both_previous_and_new_state(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Observer receives both previous and new state in on_tick."""
        from babylon.engine.simulation import Simulation

        observer = MockObserver()
        sim = Simulation(initial_state, config, observers=[observer])

        sim.step()

        previous_state, new_state = observer.tick_calls[0]
        assert previous_state.tick == 0
        assert new_state.tick == 1

    def test_multiple_observers_all_notified(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """All registered observers are notified."""
        from babylon.engine.simulation import Simulation

        observer1 = MockObserver("Observer1")
        observer2 = MockObserver("Observer2")
        observer3 = MockObserver("Observer3")

        sim = Simulation(initial_state, config, observers=[observer1, observer2, observer3])
        sim.step()

        assert len(observer1.tick_calls) == 1
        assert len(observer2.tick_calls) == 1
        assert len(observer3.tick_calls) == 1

    def test_observer_notification_order_deterministic(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Observers are notified in registration order."""
        from babylon.engine.simulation import Simulation

        call_order: list[str] = []

        class OrderTrackingObserver:
            def __init__(self, name: str) -> None:
                self._name = name

            @property
            def name(self) -> str:
                return self._name

            def on_simulation_start(
                self, _initial_state: WorldState, _config: SimulationConfig
            ) -> None:
                call_order.append(f"{self._name}_start")

            def on_tick(self, _previous_state: WorldState, _new_state: WorldState) -> None:
                call_order.append(f"{self._name}_tick")

            def on_simulation_end(self, _final_state: WorldState) -> None:
                call_order.append(f"{self._name}_end")

        obs1 = OrderTrackingObserver("A")
        obs2 = OrderTrackingObserver("B")
        obs3 = OrderTrackingObserver("C")

        sim = Simulation(initial_state, config, observers=[obs1, obs2, obs3])
        sim.step()

        # First tick triggers start then tick notifications
        assert call_order == ["A_start", "B_start", "C_start", "A_tick", "B_tick", "C_tick"]

    def test_empty_observers_list_no_crash(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Simulation works correctly with no observers."""
        from babylon.engine.simulation import Simulation

        sim = Simulation(initial_state, config, observers=[])
        new_state = sim.step()

        assert new_state.tick == 1


# =============================================================================
# TEST LIFECYCLE HOOKS
# =============================================================================


@pytest.mark.unit
class TestLifecycleHooks:
    """Tests for observer lifecycle hooks."""

    def test_on_simulation_start_called_with_initial_state(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """on_simulation_start is called with initial state on first step."""
        from babylon.engine.simulation import Simulation

        observer = MockObserver()
        sim = Simulation(initial_state, config, observers=[observer])

        sim.step()

        assert len(observer.start_calls) == 1
        received_state, received_config = observer.start_calls[0]
        assert received_state.tick == 0
        assert received_config == config

    def test_on_simulation_start_called_once_only(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """on_simulation_start is called only once, on first step."""
        from babylon.engine.simulation import Simulation

        observer = MockObserver()
        sim = Simulation(initial_state, config, observers=[observer])

        sim.step()
        sim.step()
        sim.step()

        assert len(observer.start_calls) == 1

    def test_on_simulation_end_called_with_final_state(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """on_simulation_end is called with final state when end() is called."""
        from babylon.engine.simulation import Simulation

        observer = MockObserver()
        sim = Simulation(initial_state, config, observers=[observer])

        sim.step()
        sim.step()
        sim.end()

        assert len(observer.end_calls) == 1
        assert observer.end_calls[0].tick == 2

    def test_lifecycle_order_start_ticks_end(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Lifecycle hooks follow correct order: start -> ticks -> end."""
        from babylon.engine.simulation import Simulation

        events: list[str] = []

        class LifecycleTracker:
            @property
            def name(self) -> str:
                return "LifecycleTracker"

            def on_simulation_start(
                self, _initial_state: WorldState, _config: SimulationConfig
            ) -> None:
                events.append("start")

            def on_tick(self, _previous_state: WorldState, new_state: WorldState) -> None:
                events.append(f"tick_{new_state.tick}")

            def on_simulation_end(self, _final_state: WorldState) -> None:
                events.append("end")

        observer = LifecycleTracker()
        sim = Simulation(initial_state, config, observers=[observer])

        sim.step()  # tick 1
        sim.step()  # tick 2
        sim.end()

        assert events == ["start", "tick_1", "tick_2", "end"]

    def test_end_without_start_no_crash(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Calling end() without step() does not crash (no-op)."""
        from babylon.engine.simulation import Simulation

        observer = MockObserver()
        sim = Simulation(initial_state, config, observers=[observer])

        # Should not raise
        sim.end()

        assert len(observer.end_calls) == 0


# =============================================================================
# TEST ERROR RESILIENCE
# =============================================================================


@pytest.mark.unit
class TestObserverErrorResilience:
    """Tests for observer error handling (ADR003: AI failures don't break game)."""

    def test_observer_error_does_not_halt_simulation(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Observer exceptions do not halt simulation."""
        from babylon.engine.simulation import Simulation

        failing_observer = FailingObserver()
        successful_observer = MockObserver()

        sim = Simulation(
            initial_state,
            config,
            observers=[failing_observer, successful_observer],
        )

        # Should not raise
        new_state = sim.step()

        # Simulation should continue
        assert new_state.tick == 1
        # Successful observer should still be notified
        assert len(successful_observer.tick_calls) == 1

    def test_observer_error_is_logged(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Observer exceptions are logged with warning level."""
        from babylon.engine.simulation import Simulation

        failing_observer = FailingObserver()
        sim = Simulation(initial_state, config, observers=[failing_observer])

        with caplog.at_level(logging.WARNING):
            sim.step()

        assert "FailingObserver" in caplog.text
        assert "failed" in caplog.text.lower()

    def test_failing_start_does_not_prevent_tick(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Failure in on_simulation_start does not prevent tick notification."""
        from babylon.engine.simulation import Simulation

        class StartFailer:
            @property
            def name(self) -> str:
                return "StartFailer"

            def on_simulation_start(
                self, _initial_state: WorldState, _config: SimulationConfig
            ) -> None:
                raise RuntimeError("Start failed")

            def on_tick(self, _previous_state: WorldState, _new_state: WorldState) -> None:
                pass  # Should still be called

            def on_simulation_end(self, _final_state: WorldState) -> None:
                pass

        observer = StartFailer()
        tick_observer = MockObserver()
        sim = Simulation(initial_state, config, observers=[observer, tick_observer])

        # Should not raise
        sim.step()

        # Tick should still happen
        assert len(tick_observer.tick_calls) == 1
