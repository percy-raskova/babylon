"""Tests for async button handlers in babylon.ui.main.

These tests verify the async handler functions that respond to
ControlDeck button clicks:

- on_step() - Single step via AsyncSimulationRunner
- on_play() - Start continuous simulation
- on_pause() - Stop continuous simulation
- on_reset() - Reset simulation state
- poll_runner() - Consume states from runner queue

All handlers are async functions that must properly await runner methods.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    pass


# =============================================================================
# TEST STEP HANDLER
# =============================================================================


@pytest.mark.asyncio
class TestStepHandler:
    """Tests for on_step() async handler."""

    async def test_on_step_calls_runner_step_once(
        self,
        main_module_with_mocks: Any,
    ) -> None:
        """on_step() awaits runner.step_once()."""
        main = main_module_with_mocks

        await main.on_step()

        main.runner.step_once.assert_awaited_once()

    async def test_on_step_calls_refresh_ui(
        self,
        main_module_with_mocks: Any,
    ) -> None:
        """on_step() calls refresh_ui() after stepping."""
        main = main_module_with_mocks

        with patch.object(main, "refresh_ui") as mock_refresh:
            await main.on_step()
            mock_refresh.assert_called_once()

    async def test_on_step_handles_none_runner(
        self,
        reset_main_module_state: None,
    ) -> None:
        """on_step() handles None runner gracefully."""
        import babylon.ui.main as main

        main.runner = None

        # Should not raise
        await main.on_step()


# =============================================================================
# TEST PLAY HANDLER
# =============================================================================


@pytest.mark.asyncio
class TestPlayHandler:
    """Tests for on_play() async handler."""

    async def test_on_play_calls_runner_start(
        self,
        main_module_with_mocks: Any,
    ) -> None:
        """on_play() awaits runner.start()."""
        main = main_module_with_mocks

        await main.on_play()

        main.runner.start.assert_awaited_once()

    async def test_on_play_handles_none_runner(
        self,
        reset_main_module_state: None,
    ) -> None:
        """on_play() handles None runner gracefully."""
        import babylon.ui.main as main

        main.runner = None

        # Should not raise
        await main.on_play()


# =============================================================================
# TEST PAUSE HANDLER
# =============================================================================


@pytest.mark.asyncio
class TestPauseHandler:
    """Tests for on_pause() async handler."""

    async def test_on_pause_calls_runner_stop(
        self,
        main_module_with_mocks: Any,
    ) -> None:
        """on_pause() awaits runner.stop()."""
        main = main_module_with_mocks

        await main.on_pause()

        main.runner.stop.assert_awaited_once()

    async def test_on_pause_handles_none_runner(
        self,
        reset_main_module_state: None,
    ) -> None:
        """on_pause() handles None runner gracefully."""
        import babylon.ui.main as main

        main.runner = None

        # Should not raise
        await main.on_pause()


# =============================================================================
# TEST RESET HANDLER
# =============================================================================


@pytest.mark.asyncio
class TestResetHandler:
    """Tests for on_reset() async handler."""

    async def test_on_reset_stops_runner(
        self,
        main_module_with_mocks: Any,
    ) -> None:
        """on_reset() awaits runner.stop() first."""
        main = main_module_with_mocks
        original_runner = main.runner

        # Patch init_simulation to prevent replacing the mock runner
        with patch.object(main, "init_simulation"):
            await main.on_reset()

        original_runner.stop.assert_awaited_once()

    async def test_on_reset_resets_narrative_index(
        self,
        main_module_with_mocks: Any,
    ) -> None:
        """on_reset() resets last_narrative_index to 0."""
        main = main_module_with_mocks
        main.last_narrative_index = 10

        await main.on_reset()

        assert main.last_narrative_index == 0

    async def test_on_reset_resets_event_index(
        self,
        main_module_with_mocks: Any,
    ) -> None:
        """on_reset() resets last_event_index to 0."""
        main = main_module_with_mocks
        main.last_event_index = 5

        await main.on_reset()

        assert main.last_event_index == 0

    async def test_on_reset_reinitializes_simulation(
        self,
        main_module_with_mocks: Any,
    ) -> None:
        """on_reset() calls init_simulation() to create fresh state."""
        main = main_module_with_mocks

        with patch.object(main, "init_simulation") as mock_init:
            await main.on_reset()
            mock_init.assert_called_once()

    async def test_on_reset_calls_refresh_ui(
        self,
        main_module_with_mocks: Any,
    ) -> None:
        """on_reset() calls refresh_ui() after reinitializing."""
        main = main_module_with_mocks

        with patch.object(main, "refresh_ui") as mock_refresh:
            await main.on_reset()
            mock_refresh.assert_called_once()

    async def test_on_reset_handles_none_runner(
        self,
        reset_main_module_state: None,
    ) -> None:
        """on_reset() handles None runner gracefully."""
        import babylon.ui.main as main

        main.runner = None
        main.last_narrative_index = 10
        main.last_event_index = 5

        # Should not raise
        await main.on_reset()

        # Indices should still be reset
        assert main.last_narrative_index == 0
        assert main.last_event_index == 0


# =============================================================================
# TEST POLL RUNNER
# =============================================================================


@pytest.mark.asyncio
class TestPollRunner:
    """Tests for poll_runner() timer callback."""

    async def test_poll_runner_calls_get_state(
        self,
        main_module_with_mocks: Any,
    ) -> None:
        """poll_runner() awaits runner.get_state()."""
        main = main_module_with_mocks
        main.runner.get_state = AsyncMock(return_value=None)

        await main.poll_runner()

        main.runner.get_state.assert_awaited()

    async def test_poll_runner_drains_queue(
        self,
        main_module_with_mocks: Any,
    ) -> None:
        """poll_runner() drains all states from queue."""
        main = main_module_with_mocks

        # Set up mock to return 3 states then None
        from babylon.models.world_state import WorldState

        states = [
            WorldState(tick=1),
            WorldState(tick=2),
            WorldState(tick=3),
            None,  # End of queue
        ]
        main.runner.get_state = AsyncMock(side_effect=states)

        with patch.object(main, "refresh_ui") as mock_refresh:
            await main.poll_runner()
            # refresh_ui called once per non-None state
            assert mock_refresh.call_count == 3

    async def test_poll_runner_handles_empty_queue(
        self,
        main_module_with_mocks: Any,
    ) -> None:
        """poll_runner() handles empty queue (returns None immediately)."""
        main = main_module_with_mocks
        main.runner.get_state = AsyncMock(return_value=None)

        with patch.object(main, "refresh_ui") as mock_refresh:
            await main.poll_runner()
            # No states, no refresh calls
            mock_refresh.assert_not_called()

    async def test_poll_runner_handles_none_runner(
        self,
        reset_main_module_state: None,
    ) -> None:
        """poll_runner() returns early when runner is None."""
        import babylon.ui.main as main

        main.runner = None

        # Should not raise
        await main.poll_runner()


# =============================================================================
# TEST INIT SIMULATION
# =============================================================================


class TestInitSimulation:
    """Tests for init_simulation() function."""

    def test_init_simulation_creates_simulation(
        self,
        reset_main_module_state: None,
    ) -> None:
        """init_simulation() sets module-level simulation variable."""
        import babylon.ui.main as main

        main.simulation = None
        main.runner = None

        main.init_simulation()

        assert main.simulation is not None

    def test_init_simulation_creates_runner(
        self,
        reset_main_module_state: None,
    ) -> None:
        """init_simulation() sets module-level runner variable."""
        import babylon.ui.main as main

        main.simulation = None
        main.runner = None

        main.init_simulation()

        assert main.runner is not None

    def test_init_simulation_runner_wraps_simulation(
        self,
        reset_main_module_state: None,
    ) -> None:
        """init_simulation() creates runner that wraps the simulation."""
        import babylon.ui.main as main

        main.simulation = None
        main.runner = None

        main.init_simulation()
        assert main.runner is not None  # Type narrowing

        assert main.runner.simulation is main.simulation

    def test_init_simulation_runner_has_one_second_interval(
        self,
        reset_main_module_state: None,
    ) -> None:
        """init_simulation() creates runner with 1.0s tick interval."""
        import babylon.ui.main as main

        main.simulation = None
        main.runner = None

        main.init_simulation()
        assert main.runner is not None  # Type narrowing

        assert main.runner.tick_interval == pytest.approx(1.0)
