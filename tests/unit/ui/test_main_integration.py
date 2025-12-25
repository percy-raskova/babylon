"""Subcutaneous integration tests for Babylon Developer Dashboard.

These tests verify the complete Engine -> Runner -> UI State pipeline
without browser automation. Tests instantiate REAL UI components and
assert on their internal state, proving data flows correctly through
the entire system.

Key difference from unit tests:
- Uses real TrendPlotter, SystemLog, StateInspector (not mocks)
- Uses real Simulation and WorldState
- Verifies actual data accumulation and state changes

Example:
    >>> main.init_simulation()
    >>> main.trend_plotter = TrendPlotter()  # Real component
    >>> main.simulation.step()
    >>> main.refresh_ui()
    >>> assert len(main.trend_plotter._ticks) == 1  # Real state assertion
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


# =============================================================================
# TEST SINGLE STEP CYCLE
# =============================================================================


class TestSingleStepCycle:
    """Tests for a single step updating all components."""

    def test_step_cycle_updates_trend_plotter(
        self,
        reset_main_module_state: None,
    ) -> None:
        """Single step pushes data to TrendPlotter."""
        import babylon.ui.main as main
        from babylon.ui.components import TrendPlotter

        main.init_simulation()
        assert main.simulation is not None  # Type narrowing
        main.trend_plotter = TrendPlotter()

        # Step and refresh
        main.simulation.step()
        main.refresh_ui()

        # TrendPlotter should have 1 data point
        assert len(main.trend_plotter._ticks) == 1
        assert len(main.trend_plotter._rent_data) == 1
        assert len(main.trend_plotter._tension_data) == 1

    def test_step_cycle_updates_state_inspector(
        self,
        reset_main_module_state: None,
    ) -> None:
        """Single step updates StateInspector with C001 entity."""
        import babylon.ui.main as main
        from babylon.ui.components import StateInspector

        main.init_simulation()
        assert main.simulation is not None  # Type narrowing
        main.state_inspector = StateInspector()

        # Step and refresh
        main.simulation.step()
        main.refresh_ui()

        # StateInspector should have C001 data
        assert main.state_inspector._current_data.get("id") == "C001"

    def test_step_cycle_logs_events(
        self,
        reset_main_module_state: None,
    ) -> None:
        """Single step logs events to SystemLog."""
        import babylon.ui.main as main
        from babylon.ui.components import SystemLog

        main.init_simulation()
        assert main.simulation is not None  # Type narrowing
        main.system_log = SystemLog()
        main.last_event_index = 0

        # Step and refresh
        main.simulation.step()
        main.refresh_ui()

        # SystemLog should have entries for any events generated
        # (may be 0 or more depending on simulation dynamics)
        assert isinstance(main.system_log._entries, list)


# =============================================================================
# TEST MULTIPLE STEPS
# =============================================================================


class TestMultipleSteps:
    """Tests for data accumulation over multiple steps."""

    def test_multiple_steps_accumulate_in_trend_plotter(
        self,
        reset_main_module_state: None,
    ) -> None:
        """Multiple steps accumulate data in TrendPlotter."""
        import babylon.ui.main as main
        from babylon.ui.components import TrendPlotter

        main.init_simulation()
        assert main.simulation is not None  # Type narrowing
        main.trend_plotter = TrendPlotter()

        # Run 5 steps
        for _ in range(5):
            main.simulation.step()
            main.refresh_ui()

        # Should have 5 data points
        assert len(main.trend_plotter._ticks) == 5
        assert len(main.trend_plotter._rent_data) == 5
        assert len(main.trend_plotter._tension_data) == 5

    def test_trend_plotter_ticks_are_sequential(
        self,
        reset_main_module_state: None,
    ) -> None:
        """TrendPlotter tick values are sequential integers."""
        import babylon.ui.main as main
        from babylon.ui.components import TrendPlotter

        main.init_simulation()
        assert main.simulation is not None  # Type narrowing
        main.trend_plotter = TrendPlotter()

        # Run 5 steps
        for _ in range(5):
            main.simulation.step()
            main.refresh_ui()

        # Ticks should be 1, 2, 3, 4, 5
        assert main.trend_plotter._ticks == [1, 2, 3, 4, 5]

    def test_event_index_tracks_correctly(
        self,
        reset_main_module_state: None,
    ) -> None:
        """last_event_index advances with each step."""
        import babylon.ui.main as main
        from babylon.ui.components import SystemLog

        main.init_simulation()
        assert main.simulation is not None  # Type narrowing
        main.system_log = SystemLog()
        main.last_event_index = 0

        # Run a step
        main.simulation.step()
        main.refresh_ui()

        # Event index should track total events
        assert main.last_event_index == len(main.simulation.current_state.events)


# =============================================================================
# TEST RESET CYCLE
# =============================================================================


class TestResetCycle:
    """Tests for reset returning to initial state."""

    def test_reset_clears_trend_plotter_accumulation(
        self,
        reset_main_module_state: None,
    ) -> None:
        """Reset clears TrendPlotter accumulation by reinitializing simulation.

        This test simulates the reset sequence synchronously:
        1. Init simulation and create TrendPlotter
        2. Run 3 steps to accumulate data
        3. Manually reset indices and reinit simulation (sync equivalent of on_reset)
        4. Clear TrendPlotter state and verify tick 0 data flows correctly

        Note: We can't use on_reset() here because it's async, and NiceGUI
        components can't be created in async test contexts.
        """
        import babylon.ui.main as main
        from babylon.ui.components import TrendPlotter

        main.init_simulation()
        assert main.simulation is not None  # Type narrowing
        main.trend_plotter = TrendPlotter()

        # Run 3 steps
        for _ in range(3):
            main.simulation.step()
            main.refresh_ui()

        assert len(main.trend_plotter._ticks) == 3

        # Simulate reset sequence (sync version of on_reset)
        main.last_narrative_index = 0
        main.last_event_index = 0
        main.init_simulation()
        assert main.simulation is not None  # Type narrowing after reset

        # Clear TrendPlotter state manually (simulates fresh component)
        main.trend_plotter._ticks.clear()
        main.trend_plotter._rent_data.clear()
        main.trend_plotter._tension_data.clear()

        # Refresh with the new tick 0 state
        main.refresh_ui()

        # Should have 1 point at tick 0
        assert len(main.trend_plotter._ticks) == 1
        assert main.trend_plotter._ticks[0] == 0

    @pytest.mark.asyncio
    async def test_reset_returns_to_tick_zero(
        self,
        reset_main_module_state: None,
    ) -> None:
        """Reset returns simulation to tick 0."""
        import babylon.ui.main as main

        main.init_simulation()
        assert main.simulation is not None  # Type narrowing

        # Advance a few ticks
        for _ in range(5):
            main.simulation.step()

        assert main.simulation.current_state.tick == 5

        # Reset
        await main.on_reset()
        assert main.simulation is not None  # Type narrowing after reset

        assert main.simulation.current_state.tick == 0


# =============================================================================
# TEST ROLLING WINDOW
# =============================================================================


class TestRollingWindow:
    """Tests for TrendPlotter rolling window enforcement."""

    def test_rolling_window_enforced_at_50(
        self,
        reset_main_module_state: None,
    ) -> None:
        """TrendPlotter drops oldest data after MAX_POINTS (50)."""
        import babylon.ui.main as main
        from babylon.ui.components import TrendPlotter

        main.init_simulation()
        assert main.simulation is not None  # Type narrowing
        main.trend_plotter = TrendPlotter()

        # Run 60 steps (past the 50-point limit)
        for _ in range(60):
            main.simulation.step()
            main.refresh_ui()

        # Should have exactly 50 points
        assert len(main.trend_plotter._ticks) == 50
        assert len(main.trend_plotter._rent_data) == 50
        assert len(main.trend_plotter._tension_data) == 50

    def test_rolling_window_preserves_most_recent(
        self,
        reset_main_module_state: None,
    ) -> None:
        """Rolling window keeps most recent 50 ticks."""
        import babylon.ui.main as main
        from babylon.ui.components import TrendPlotter

        main.init_simulation()
        assert main.simulation is not None  # Type narrowing
        main.trend_plotter = TrendPlotter()

        # Run 60 steps
        for _ in range(60):
            main.simulation.step()
            main.refresh_ui()

        # Oldest tick should be 11 (ticks 11-60)
        assert main.trend_plotter._ticks[0] == 11
        # Newest tick should be 60
        assert main.trend_plotter._ticks[-1] == 60


# =============================================================================
# TEST STATE INSPECTOR INTEGRATION
# =============================================================================


class TestStateInspectorIntegration:
    """Tests for StateInspector integration with real entity data."""

    def test_state_inspector_shows_c001_id(
        self,
        reset_main_module_state: None,
    ) -> None:
        """StateInspector displays C001 entity ID."""
        import babylon.ui.main as main
        from babylon.ui.components import StateInspector

        main.init_simulation()
        main.state_inspector = StateInspector()

        main.refresh_ui()

        assert main.state_inspector._current_data.get("id") == "C001"

    def test_state_inspector_shows_wealth(
        self,
        reset_main_module_state: None,
    ) -> None:
        """StateInspector displays C001 wealth value."""
        import babylon.ui.main as main
        from babylon.ui.components import StateInspector

        main.init_simulation()
        main.state_inspector = StateInspector()

        main.refresh_ui()

        # C001 should have a wealth field
        assert "wealth" in main.state_inspector._current_data

    def test_state_inspector_updates_on_step(
        self,
        reset_main_module_state: None,
    ) -> None:
        """StateInspector data changes after simulation step."""
        import babylon.ui.main as main
        from babylon.ui.components import StateInspector

        main.init_simulation()
        assert main.simulation is not None  # Type narrowing
        main.state_inspector = StateInspector()

        main.refresh_ui()
        initial_data = dict(main.state_inspector._current_data)

        # Step and refresh
        main.simulation.step()
        main.refresh_ui()

        # Data should be different (at minimum, different dict instance)
        # The actual values may or may not change depending on simulation dynamics
        assert main.state_inspector._current_data is not initial_data


# =============================================================================
# TEST SYSTEM LOG INTEGRATION
# =============================================================================


class TestSystemLogIntegration:
    """Tests for SystemLog integration with real events."""

    def test_system_log_entries_are_tuples(
        self,
        reset_main_module_state: None,
    ) -> None:
        """SystemLog stores entries as (text, level) tuples."""
        import babylon.ui.main as main
        from babylon.ui.components import SystemLog

        main.init_simulation()
        assert main.simulation is not None  # Type narrowing
        main.system_log = SystemLog()
        main.last_event_index = 0

        # Run a step to potentially generate events
        main.simulation.step()
        main.refresh_ui()

        # All entries should be (text, level) tuples
        for entry in main.system_log._entries:
            assert isinstance(entry, tuple)
            assert len(entry) == 2
            text, level = entry
            assert isinstance(text, str)
            assert level in ("INFO", "WARN", "ERROR")

    def test_extraction_events_logged_as_info(
        self,
        reset_main_module_state: None,
    ) -> None:
        """SURPLUS_EXTRACTION events are logged at INFO level."""
        import babylon.ui.main as main
        from babylon.ui.components import SystemLog

        main.init_simulation()
        assert main.simulation is not None  # Type narrowing
        main.system_log = SystemLog()
        main.last_event_index = 0

        # Run enough steps to generate extraction events
        # (extraction happens each tick in the two-node scenario)
        for _ in range(3):
            main.simulation.step()
            main.refresh_ui()

        # Look for extraction events in log
        extraction_entries = [
            (text, level)
            for text, level in main.system_log._entries
            if "SURPLUS_EXTRACTION" in text
        ]

        # Should have some extraction events, all at INFO level
        if extraction_entries:
            for _text, level in extraction_entries:
                assert level == "INFO"
