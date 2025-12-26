"""UI test fixtures for subcutaneous integration testing.

This module provides fixtures for testing the Babylon UI layer without
browser automation. Tests can verify data flow from Engine -> Runner -> UI
by directly asserting on component internal state.

Fixtures:
    mock_simulation: Mock Simulation with tick-incrementing step()
    mock_runner: AsyncMock AsyncSimulationRunner
    reset_main_module_state: Saves/restores module globals between tests
    main_module_with_mocks: Injects mocks into babylon.ui.main

Example:
    >>> @pytest.mark.asyncio
    ... async def test_on_step_calls_runner(main_module_with_mocks):
    ...     main = main_module_with_mocks
    ...     await main.on_step()
    ...     main.runner.step_once.assert_awaited_once()
"""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, Mock

import pytest

from babylon.engine.scenarios import create_two_node_scenario
from babylon.engine.simulation import Simulation
from babylon.models.world_state import WorldState

if TYPE_CHECKING:
    pass


# =============================================================================
# MOCK FACTORIES
# =============================================================================


@pytest.fixture
def mock_simulation() -> Mock:
    """Create a mock Simulation for isolated unit testing.

    The mock tracks tick progression and returns new WorldState on each step().
    Uses the same pattern as tests/unit/engine/test_runner.py.

    Returns:
        Mock Simulation with tick-incrementing step() side effect.
    """
    sim = Mock(spec=Simulation)
    # Start with tick 0 using minimal state
    sim.current_state = WorldState(tick=0)
    # Empty observers list for _get_narrative_director
    sim.observers = []

    def step_side_effect() -> WorldState:
        """Increment tick and return new state on each step."""
        new_tick = sim.current_state.tick + 1
        new_state = WorldState(tick=new_tick)
        sim.current_state = new_state
        return new_state

    sim.step = Mock(side_effect=step_side_effect)
    return sim


@pytest.fixture
def mock_runner() -> AsyncMock:
    """Create a mock AsyncSimulationRunner for handler testing.

    Returns:
        AsyncMock with all runner methods stubbed.
    """
    from babylon.engine.runner import AsyncSimulationRunner

    runner = AsyncMock(spec=AsyncSimulationRunner)
    runner.is_running = False

    # step_once returns None (just advances simulation)
    runner.step_once = AsyncMock(return_value=None)
    # start/stop return None
    runner.start = AsyncMock(return_value=None)
    runner.stop = AsyncMock(return_value=None)
    # get_state returns None (no pending states)
    runner.get_state = AsyncMock(return_value=None)
    # get_state_blocking returns None
    runner.get_state_blocking = AsyncMock(return_value=None)

    return runner


@pytest.fixture
def real_simulation() -> Simulation:
    """Create a real Simulation instance for integration testing.

    Uses the standard two-node scenario (Worker vs Owner).

    Returns:
        Fully initialized Simulation instance.
    """
    state, config, defines = create_two_node_scenario()
    return Simulation(state, config, defines=defines)


# =============================================================================
# MODULE STATE MANAGEMENT
# =============================================================================


@pytest.fixture
def reset_main_module_state() -> Generator[None, None, None]:
    """Save and restore babylon.ui.main module globals between tests.

    This fixture captures the state of all module-level variables before
    the test and restores them afterward, preventing test pollution.

    Yields:
        None (just provides cleanup behavior).
    """
    import babylon.ui.main as main

    # Save original state from DashboardState instance
    original_simulation = main._state.simulation
    original_runner = main._state.runner
    original_control_deck = main._state.control_deck
    original_terminal = main._state.terminal
    original_system_log = main._state.system_log
    original_trend_plotter = main._state.trend_plotter
    original_state_inspector = main._state.state_inspector
    original_last_narrative_index = main._state.last_narrative_index
    original_last_event_index = main._state.last_event_index
    original_metrics_collector = main._state.metrics_collector

    yield

    # Restore original state to DashboardState instance
    main._state.simulation = original_simulation
    main._state.runner = original_runner
    main._state.control_deck = original_control_deck
    main._state.terminal = original_terminal
    main._state.system_log = original_system_log
    main._state.trend_plotter = original_trend_plotter
    main._state.state_inspector = original_state_inspector
    main._state.last_narrative_index = original_last_narrative_index
    main._state.last_event_index = original_last_event_index
    main._state.metrics_collector = original_metrics_collector


@pytest.fixture
def main_module_with_mocks(
    mock_simulation: Mock,
    mock_runner: AsyncMock,
    reset_main_module_state: None,  # noqa: ARG001 - Fixture needed for cleanup side-effect
) -> Any:
    """Inject mocks into babylon.ui.main and return the module.

    This fixture combines the mock factories with module state reset,
    providing a clean slate for each test with mocked dependencies.

    Args:
        mock_simulation: Mock Simulation fixture.
        mock_runner: Mock AsyncSimulationRunner fixture.
        reset_main_module_state: Ensures cleanup after test.

    Returns:
        The babylon.ui.main module with mocks injected.
    """
    import babylon.ui.main as main

    main._state.simulation = mock_simulation
    main._state.runner = mock_runner

    return main


# =============================================================================
# COMPONENT FIXTURES
# =============================================================================


@pytest.fixture
def mock_control_deck() -> Mock:
    """Create a mock ControlDeck for refresh_ui testing.

    Returns:
        Mock ControlDeck with update_tick method.
    """
    from babylon.ui.controls import ControlDeck

    deck = Mock(spec=ControlDeck)
    deck.update_tick = Mock()
    return deck


@pytest.fixture
def mock_terminal() -> Mock:
    """Create a mock NarrativeTerminal for refresh_ui testing.

    Returns:
        Mock NarrativeTerminal with log method.
    """
    from babylon.ui.terminal import NarrativeTerminal

    terminal = Mock(spec=NarrativeTerminal)
    terminal.log = Mock()
    return terminal


@pytest.fixture
def mock_system_log() -> Mock:
    """Create a mock SystemLog for refresh_ui testing.

    Returns:
        Mock SystemLog with log method.
    """
    from babylon.ui.components import SystemLog

    log = Mock(spec=SystemLog)
    log.log = Mock()
    return log


@pytest.fixture
def mock_trend_plotter() -> Mock:
    """Create a mock TrendPlotter for refresh_ui testing.

    Returns:
        Mock TrendPlotter with push_data method.
    """
    from babylon.ui.components import TrendPlotter

    plotter = Mock(spec=TrendPlotter)
    plotter.push_data = Mock()
    return plotter


@pytest.fixture
def mock_state_inspector() -> Mock:
    """Create a mock StateInspector for refresh_ui testing.

    Returns:
        Mock StateInspector with refresh method.
    """
    from babylon.ui.components import StateInspector

    inspector = Mock(spec=StateInspector)
    inspector.refresh = Mock()
    return inspector
