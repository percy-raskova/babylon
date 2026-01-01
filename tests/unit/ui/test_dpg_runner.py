"""Unit tests for Dear PyGui dashboard runner.

Tests cover:
- DPG context initialization
- Simulation creation and observer wiring
- UI state management (play/pause/step/reset)
- Error handling for ContradictionError
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    pass


class TestDPGRunnerImports:
    """Test that dpg_runner module can be imported."""

    def test_dpg_runner_module_exists(self) -> None:
        """The dpg_runner module should be importable."""
        from babylon.ui import dpg_runner

        assert dpg_runner is not None

    def test_main_function_exists(self) -> None:
        """The main() function should exist."""
        from babylon.ui.dpg_runner import main

        assert callable(main)

    def test_create_simulation_function_exists(self) -> None:
        """The create_simulation() function should exist."""
        from babylon.ui.dpg_runner import create_simulation

        assert callable(create_simulation)


class TestSimulationCreation:
    """Test simulation initialization."""

    def test_create_simulation_returns_simulation(self) -> None:
        """create_simulation() should return a Simulation instance."""
        from babylon.engine.simulation import Simulation
        from babylon.ui.dpg_runner import create_simulation

        sim = create_simulation()
        assert isinstance(sim, Simulation)

    def test_create_simulation_has_metrics_collector(self) -> None:
        """The simulation should have a MetricsCollector observer."""
        from babylon.ui.dpg_runner import create_simulation

        sim = create_simulation()
        observer_types = [type(o).__name__ for o in sim._observers]
        assert "MetricsCollector" in observer_types

    def test_create_simulation_has_narrative_director(self) -> None:
        """The simulation should have a NarrativeDirector observer."""
        from babylon.ui.dpg_runner import create_simulation

        sim = create_simulation()
        observer_types = [type(o).__name__ for o in sim._observers]
        assert "NarrativeDirector" in observer_types


class TestDashboardState:
    """Test dashboard state management."""

    def test_dashboard_state_exists(self) -> None:
        """DashboardState class should exist."""
        from babylon.ui.dpg_runner import DashboardState

        assert DashboardState is not None

    def test_dashboard_state_initializes(self) -> None:
        """DashboardState should initialize with default values."""
        from babylon.ui.dpg_runner import DashboardState

        state = DashboardState()
        assert state.simulation_running is False
        assert state.tick == 0

    def test_dashboard_state_has_time_series_data(self) -> None:
        """DashboardState should have time series data lists."""
        from babylon.ui.dpg_runner import DashboardState

        state = DashboardState()
        assert hasattr(state, "rent_data_x")
        assert hasattr(state, "rent_data_y")
        assert hasattr(state, "la_data_x")
        assert hasattr(state, "la_data_y")
        assert isinstance(state.rent_data_x, list)


class TestUIBuilders:
    """Test UI builder functions (without actually creating UI)."""

    def test_build_narrative_feed_exists(self) -> None:
        """build_narrative_feed() function should exist."""
        from babylon.ui.dpg_runner import build_narrative_feed

        assert callable(build_narrative_feed)

    def test_build_telemetry_panel_exists(self) -> None:
        """build_telemetry_panel() function should exist."""
        from babylon.ui.dpg_runner import build_telemetry_panel

        assert callable(build_telemetry_panel)

    def test_build_control_panel_exists(self) -> None:
        """build_control_panel() function should exist."""
        from babylon.ui.dpg_runner import build_control_panel

        assert callable(build_control_panel)


class TestCallbacks:
    """Test callback functions."""

    def test_on_step_exists(self) -> None:
        """on_step() callback should exist."""
        from babylon.ui.dpg_runner import on_step

        assert callable(on_step)

    def test_on_play_exists(self) -> None:
        """on_play() callback should exist."""
        from babylon.ui.dpg_runner import on_play

        assert callable(on_play)

    def test_on_pause_exists(self) -> None:
        """on_pause() callback should exist."""
        from babylon.ui.dpg_runner import on_pause

        assert callable(on_pause)

    def test_on_reset_exists(self) -> None:
        """on_reset() callback should exist."""
        from babylon.ui.dpg_runner import on_reset

        assert callable(on_reset)


class TestColorConstants:
    """Test DPG color constants."""

    def test_dpg_colors_exist_in_design_system(self) -> None:
        """DPG color tuples should exist in design_system."""
        from babylon.ui.design_system import DPGColors

        assert hasattr(DPGColors, "VOID")
        assert hasattr(DPGColors, "DATA_GREEN")
        assert hasattr(DPGColors, "PHOSPHOR_RED")

    def test_dpg_colors_are_rgba_tuples(self) -> None:
        """DPG colors should be RGBA tuples (4 integers)."""
        from babylon.ui.design_system import DPGColors

        assert isinstance(DPGColors.VOID, tuple)
        assert len(DPGColors.VOID) == 4
        assert all(isinstance(c, int) for c in DPGColors.VOID)

    def test_dpg_colors_in_valid_range(self) -> None:
        """DPG color values should be in 0-255 range."""
        from babylon.ui.design_system import DPGColors

        for color in [DPGColors.VOID, DPGColors.DATA_GREEN, DPGColors.PHOSPHOR_RED]:
            assert all(0 <= c <= 255 for c in color)


# =============================================================================
# PHASE 1: STATUS BAR TESTS (RED PHASE)
# =============================================================================


class TestStatusBarExists:
    """Test Status Bar builder function exists."""

    def test_build_status_bar_exists(self) -> None:
        """build_status_bar() function should exist.

        The Status Bar displays phase state, pool ratio, and bifurcation trend.
        """
        from babylon.ui.dpg_runner import build_status_bar

        assert callable(build_status_bar)

    def test_update_status_bar_exists(self) -> None:
        """update_status_bar() function should exist.

        Updates the status bar with current simulation state.
        """
        from babylon.ui.dpg_runner import update_status_bar

        assert callable(update_status_bar)


class TestStatusBarPhaseDisplay:
    """Test Status Bar phase display format."""

    def test_phase_colors_mapping_exists(self) -> None:
        """PHASE_COLORS constant should exist mapping phase names to colors.

        Design requirement: Different colors for gaseous/transitional/liquid/solid.
        """
        from babylon.ui.dpg_runner import PHASE_COLORS

        assert isinstance(PHASE_COLORS, dict)
        assert "gaseous" in PHASE_COLORS
        assert "transitional" in PHASE_COLORS
        assert "liquid" in PHASE_COLORS

    def test_gaseous_phase_uses_silver(self) -> None:
        """Gaseous phase should use SILVER_DUST color (atomized, weak)."""
        from babylon.ui.design_system import DPGColors
        from babylon.ui.dpg_runner import PHASE_COLORS

        assert PHASE_COLORS["gaseous"] == DPGColors.SILVER_DUST

    def test_liquid_phase_uses_green(self) -> None:
        """Liquid phase should use DATA_GREEN color (organized, strong)."""
        from babylon.ui.design_system import DPGColors
        from babylon.ui.dpg_runner import PHASE_COLORS

        assert PHASE_COLORS["liquid"] == DPGColors.DATA_GREEN


class TestTopologyMonitorWiring:
    """Test TopologyMonitor is wired as observer."""

    def test_create_simulation_has_topology_monitor(self) -> None:
        """create_simulation() should include TopologyMonitor observer.

        TopologyMonitor provides phase transition data needed for Status Bar.
        """
        from babylon.ui.dpg_runner import create_simulation

        sim = create_simulation()
        observer_types = [type(o).__name__ for o in sim._observers]
        assert "TopologyMonitor" in observer_types


# =============================================================================
# PHASE 2: EVENT LOG TESTS (RED PHASE)
# =============================================================================


class TestEventLogExists:
    """Test Event Log builder function exists."""

    def test_build_event_log_exists(self) -> None:
        """build_event_log() function should exist.

        The Event Log displays typed simulation events with color coding.
        """
        from babylon.ui.dpg_runner import build_event_log

        assert callable(build_event_log)

    def test_update_event_log_exists(self) -> None:
        """update_event_log() function should exist."""
        from babylon.ui.dpg_runner import update_event_log

        assert callable(update_event_log)

    def test_log_event_function_exists(self) -> None:
        """log_event() helper function should exist."""
        from babylon.ui.dpg_runner import log_event

        assert callable(log_event)


class TestEventLogColorMapping:
    """Test Event Log color mapping by EventType."""

    def test_event_type_colors_constant_exists(self) -> None:
        """EVENT_TYPE_COLORS constant should exist."""
        from babylon.ui.dpg_runner import EVENT_TYPE_COLORS

        assert isinstance(EVENT_TYPE_COLORS, dict)

    def test_surplus_extraction_uses_copper(self) -> None:
        """SURPLUS_EXTRACTION events should use EXPOSED_COPPER."""
        from babylon.models.enums import EventType
        from babylon.ui.design_system import DPGColors
        from babylon.ui.dpg_runner import EVENT_TYPE_COLORS

        assert EVENT_TYPE_COLORS[EventType.SURPLUS_EXTRACTION] == DPGColors.EXPOSED_COPPER

    def test_uprising_uses_red(self) -> None:
        """UPRISING events should use PHOSPHOR_RED (danger)."""
        from babylon.models.enums import EventType
        from babylon.ui.design_system import DPGColors
        from babylon.ui.dpg_runner import EVENT_TYPE_COLORS

        assert EVENT_TYPE_COLORS[EventType.UPRISING] == DPGColors.PHOSPHOR_RED

    def test_solidarity_spike_uses_purple(self) -> None:
        """SOLIDARITY_SPIKE events should use GROW_PURPLE."""
        from babylon.models.enums import EventType
        from babylon.ui.design_system import DPGColors
        from babylon.ui.dpg_runner import EVENT_TYPE_COLORS

        assert EVENT_TYPE_COLORS[EventType.SOLIDARITY_SPIKE] == DPGColors.GROW_PURPLE

    def test_mass_awakening_uses_green(self) -> None:
        """MASS_AWAKENING events should use DATA_GREEN (positive)."""
        from babylon.models.enums import EventType
        from babylon.ui.design_system import DPGColors
        from babylon.ui.dpg_runner import EVENT_TYPE_COLORS

        assert EVENT_TYPE_COLORS[EventType.MASS_AWAKENING] == DPGColors.DATA_GREEN

    def test_phase_transition_uses_blue(self) -> None:
        """PHASE_TRANSITION events should use ROYAL_BLUE."""
        from babylon.models.enums import EventType
        from babylon.ui.design_system import DPGColors
        from babylon.ui.dpg_runner import EVENT_TYPE_COLORS

        assert EVENT_TYPE_COLORS[EventType.PHASE_TRANSITION] == DPGColors.ROYAL_BLUE

    def test_economic_crisis_uses_amber(self) -> None:
        """ECONOMIC_CRISIS events should use WARNING_AMBER."""
        from babylon.models.enums import EventType
        from babylon.ui.design_system import DPGColors
        from babylon.ui.dpg_runner import EVENT_TYPE_COLORS

        assert EVENT_TYPE_COLORS[EventType.ECONOMIC_CRISIS] == DPGColors.WARNING_AMBER


class TestEventLogState:
    """Test Event Log state tracking."""

    def test_dashboard_state_has_last_event_idx(self) -> None:
        """DashboardState should have last_event_idx for tracking displayed events."""
        from babylon.ui.dpg_runner import DashboardState

        state = DashboardState()
        assert hasattr(state, "last_event_idx")
        assert state.last_event_idx == 0


# =============================================================================
# PHASE 3: WEALTH TREND TESTS (RED PHASE)
# =============================================================================


class TestWealthTrendExists:
    """Test Wealth Trend builder function exists."""

    def test_build_wealth_trend_panel_exists(self) -> None:
        """build_wealth_trend_panel() function should exist.

        Displays 4-line plot of class wealth over time.
        """
        from babylon.ui.dpg_runner import build_wealth_trend_panel

        assert callable(build_wealth_trend_panel)

    def test_update_wealth_trend_exists(self) -> None:
        """update_wealth_trend() function should exist."""
        from babylon.ui.dpg_runner import update_wealth_trend

        assert callable(update_wealth_trend)


class TestWealthTrendDataState:
    """Test Wealth Trend data storage in DashboardState."""

    def test_dashboard_state_has_pw_wealth_data(self) -> None:
        """DashboardState should have pw_wealth_x and pw_wealth_y lists."""
        from babylon.ui.dpg_runner import DashboardState

        state = DashboardState()
        assert hasattr(state, "pw_wealth_x")
        assert hasattr(state, "pw_wealth_y")
        assert isinstance(state.pw_wealth_x, list)
        assert isinstance(state.pw_wealth_y, list)

    def test_dashboard_state_has_pc_wealth_data(self) -> None:
        """DashboardState should have pc_wealth_x and pc_wealth_y lists."""
        from babylon.ui.dpg_runner import DashboardState

        state = DashboardState()
        assert hasattr(state, "pc_wealth_x")
        assert hasattr(state, "pc_wealth_y")

    def test_dashboard_state_has_cb_wealth_data(self) -> None:
        """DashboardState should have cb_wealth_x and cb_wealth_y lists."""
        from babylon.ui.dpg_runner import DashboardState

        state = DashboardState()
        assert hasattr(state, "cb_wealth_x")
        assert hasattr(state, "cb_wealth_y")

    def test_dashboard_state_has_cw_wealth_data(self) -> None:
        """DashboardState should have cw_wealth_x and cw_wealth_y lists."""
        from babylon.ui.dpg_runner import DashboardState

        state = DashboardState()
        assert hasattr(state, "cw_wealth_x")
        assert hasattr(state, "cw_wealth_y")


class TestWealthTrendColors:
    """Test Wealth Trend uses correct colors per class."""

    def test_wealth_colors_constant_exists(self) -> None:
        """WEALTH_COLORS constant should map class names to colors."""
        from babylon.ui.dpg_runner import WEALTH_COLORS

        assert isinstance(WEALTH_COLORS, dict)
        assert "p_w" in WEALTH_COLORS
        assert "p_c" in WEALTH_COLORS
        assert "c_b" in WEALTH_COLORS
        assert "c_w" in WEALTH_COLORS

    def test_pw_uses_data_green(self) -> None:
        """Periphery Worker (P_w) should use DATA_GREEN (the exploited)."""
        from babylon.ui.design_system import DPGColors
        from babylon.ui.dpg_runner import WEALTH_COLORS

        assert WEALTH_COLORS["p_w"] == DPGColors.DATA_GREEN

    def test_pc_uses_exposed_copper(self) -> None:
        """Comprador (P_c) should use EXPOSED_COPPER."""
        from babylon.ui.design_system import DPGColors
        from babylon.ui.dpg_runner import WEALTH_COLORS

        assert WEALTH_COLORS["p_c"] == DPGColors.EXPOSED_COPPER

    def test_cb_uses_phosphor_red(self) -> None:
        """Core Bourgeoisie (C_b) should use PHOSPHOR_RED (the exploiter)."""
        from babylon.ui.design_system import DPGColors
        from babylon.ui.dpg_runner import WEALTH_COLORS

        assert WEALTH_COLORS["c_b"] == DPGColors.PHOSPHOR_RED

    def test_cw_uses_royal_blue(self) -> None:
        """Labor Aristocracy (C_w) should use ROYAL_BLUE."""
        from babylon.ui.design_system import DPGColors
        from babylon.ui.dpg_runner import WEALTH_COLORS

        assert WEALTH_COLORS["c_w"] == DPGColors.ROYAL_BLUE


# =============================================================================
# PHASE 4: KEY METRICS TESTS (RED PHASE)
# =============================================================================


class TestKeyMetricsExists:
    """Test Key Metrics builder function exists."""

    def test_build_key_metrics_panel_exists(self) -> None:
        """build_key_metrics_panel() function should exist.

        Displays key simulation metrics as text values.
        """
        from babylon.ui.dpg_runner import build_key_metrics_panel

        assert callable(build_key_metrics_panel)

    def test_update_key_metrics_exists(self) -> None:
        """update_key_metrics() function should exist."""
        from babylon.ui.dpg_runner import update_key_metrics

        assert callable(update_key_metrics)


# =============================================================================
# NARRATIVE FEED FIX TESTS (TDD - Issue: Narrative Feed Empty)
# =============================================================================


class TestNarrativeDirectorLLMWiring:
    """Test NarrativeDirector is wired with LLM provider for narrative generation."""

    def test_narrative_director_has_use_llm_enabled(self) -> None:
        """NarrativeDirector should have use_llm=True to enable narrative generation.

        Root cause of empty Narrative Feed: NarrativeDirector(use_llm=False) disables
        all narrative generation. The narrative_log is never populated.
        """
        from babylon.ai.director import NarrativeDirector
        from babylon.ui.dpg_runner import create_simulation

        sim = create_simulation()
        director = next(o for o in sim._observers if isinstance(o, NarrativeDirector))
        assert director._use_llm is True, "use_llm must be True for narrative generation"

    def test_narrative_director_has_llm_provider(self) -> None:
        """NarrativeDirector should have an LLM provider (MockLLM) attached.

        Without an LLM provider, even with use_llm=True, no narratives are generated.
        """
        from babylon.ai.director import NarrativeDirector
        from babylon.ui.dpg_runner import create_simulation

        sim = create_simulation()
        director = next(o for o in sim._observers if isinstance(o, NarrativeDirector))
        assert director._llm is not None, "LLM provider required for narrative generation"

    def test_narrative_director_llm_is_mock_llm(self) -> None:
        """NarrativeDirector should use MockLLM for offline MVP behavior.

        MockLLM provides consistent, deterministic narratives without API costs.
        """
        from babylon.ai.director import NarrativeDirector
        from babylon.ai.llm_provider import MockLLM
        from babylon.ui.dpg_runner import create_simulation

        sim = create_simulation()
        director = next(o for o in sim._observers if isinstance(o, NarrativeDirector))
        assert isinstance(director._llm, MockLLM), "Should use MockLLM for MVP"


# =============================================================================
# WEALTH TREND COLORS FIX TESTS (TDD - Issue: P_c Line Not Visible)
# =============================================================================


class TestWealthTrendSeriesColorApplication:
    """Test that WEALTH_COLORS are actually applied to DPG line series."""

    def test_create_series_theme_function_exists(self) -> None:
        """_create_series_theme() helper should exist for creating themed series.

        This function creates a DPG theme with mvPlotCol_Line color for line series.
        """
        from babylon.ui.dpg_runner import _create_series_theme

        assert callable(_create_series_theme)


# =============================================================================
# IMPERIAL CIRCUIT 4-NODE WEALTH DATA FLOW TESTS (TDD)
# Issue: P_c (Comprador) wealth line was invisible on dashboard
# =============================================================================


class TestImperialCircuitWealthDataFlow:
    """TDD tests for 4-node Imperial Circuit wealth data in dashboard.

    Verifies that all four social classes (P_w, P_c, C_b, C_w) are properly
    wired from the simulation through MetricsCollector to the dashboard display.

    Issue being investigated: "invisible P_c (Comprador) wealth line"

    Test requirements:
    1. Wealth changes: Each class wealth should change over ticks (non-static)
    2. Consistent updates: All 4 lines update on same tick (no lag between series)
    3. Value flow logic: Verify MLM-TW flows (P_w↓, C_b↑, C_w↑, P_c>0)
    """

    def test_all_four_entity_slots_populated_after_tick(self) -> None:
        """All four slots (p_w, p_c, c_b, c_w) must be populated in TickMetrics.

        The MetricsCollector ENTITY_SLOTS mapping must capture all 4 nodes from
        the imperial circuit scenario. If any slot is None, the corresponding
        wealth line will be invisible on the dashboard.
        """
        from babylon.engine.observers import MetricsCollector
        from babylon.engine.scenarios import create_imperial_circuit_scenario
        from babylon.engine.simulation import Simulation

        state, config, defines = create_imperial_circuit_scenario()
        metrics = MetricsCollector(mode="interactive")
        sim = Simulation(state, config, observers=[metrics], defines=defines)

        sim.step()

        latest = metrics.latest
        assert latest is not None, "MetricsCollector should have recorded tick"
        assert latest.p_w is not None, "P_w (C001) metrics missing"
        assert latest.p_c is not None, "P_c (C002) metrics missing - invisible line bug"
        assert latest.c_b is not None, "C_b (C003) metrics missing"
        assert latest.c_w is not None, "C_w (C004) metrics missing"

    def test_wealth_values_change_over_simulation_ticks(self) -> None:
        """Each class wealth should change (non-static) over simulation ticks.

        MLM-TW value flow requires wealth to move between classes. Static values
        indicate broken economic system wiring.

        Runs 10 ticks and verifies at least one class has changing wealth values.
        """
        from babylon.engine.observers import MetricsCollector
        from babylon.engine.scenarios import create_imperial_circuit_scenario
        from babylon.engine.simulation import Simulation

        state, config, defines = create_imperial_circuit_scenario()
        metrics = MetricsCollector(mode="batch")
        sim = Simulation(state, config, observers=[metrics], defines=defines)

        # Run 10 ticks
        for _ in range(10):
            sim.step()

        history = metrics.history
        assert len(history) == 11, "Should have tick 0 + 10 steps"

        # Extract wealth series
        p_w_wealth = [t.p_w.wealth for t in history if t.p_w]
        p_c_wealth = [t.p_c.wealth for t in history if t.p_c]
        c_b_wealth = [t.c_b.wealth for t in history if t.c_b]
        c_w_wealth = [t.c_w.wealth for t in history if t.c_w]

        # All series should have 11 values (tick 0 + 10 steps)
        assert len(p_w_wealth) == 11, "P_w wealth series incomplete"
        assert len(p_c_wealth) == 11, "P_c wealth series incomplete - invisible line bug"
        assert len(c_b_wealth) == 11, "C_b wealth series incomplete"
        assert len(c_w_wealth) == 11, "C_w wealth series incomplete"

        # At least C_b should accumulate (wealth increases over time)
        # Check that not all values are identical
        assert len(set(c_b_wealth)) > 1, "C_b wealth should change (accumulating tribute)"

    def test_mlm_tw_value_flow_direction(self) -> None:
        """Verify MLM-TW theory value flow directions.

        After 10 ticks:
        - P_w wealth decreases (exploitation source)
        - C_b wealth increases (tribute accumulation)
        - C_w wealth increases (super-wages)
        - P_c wealth remains positive (keeps 15% comprador cut)
        """
        from babylon.engine.observers import MetricsCollector
        from babylon.engine.scenarios import create_imperial_circuit_scenario
        from babylon.engine.simulation import Simulation

        # Use higher initial wealth so extraction visibly dominates production
        state, config, defines = create_imperial_circuit_scenario(periphery_wealth=100.0)
        metrics = MetricsCollector(mode="batch")
        sim = Simulation(state, config, observers=[metrics], defines=defines)

        # Record initial values
        initial_p_w = float(state.entities["C001"].wealth)
        initial_c_b = float(state.entities["C003"].wealth)
        initial_c_w = float(state.entities["C004"].wealth)

        # Run 10 ticks
        for _ in range(10):
            sim.step()

        latest = metrics.latest
        assert latest is not None

        # P_w decreases (exploitation)
        assert latest.p_w is not None
        assert latest.p_w.wealth < initial_p_w, (
            f"P_w should decrease: {initial_p_w} -> {latest.p_w.wealth}"
        )

        # C_b accumulates (tribute)
        assert latest.c_b is not None
        assert latest.c_b.wealth > initial_c_b, (
            f"C_b should accumulate: {initial_c_b} -> {latest.c_b.wealth}"
        )

        # C_w receives wages
        assert latest.c_w is not None
        assert latest.c_w.wealth > initial_c_w, (
            f"C_w should receive wages: {initial_c_w} -> {latest.c_w.wealth}"
        )

        # P_c has positive wealth (kept cut)
        assert latest.p_c is not None
        assert latest.p_c.wealth > 0, (
            f"P_c should have positive wealth from 15% cut: {latest.p_c.wealth}"
        )

    def test_dashboard_state_updates_all_four_wealth_series(self) -> None:
        """DashboardState should have data for all 4 wealth series after update.

        This tests the wiring between MetricsCollector and DashboardState.
        If P_c data is not appended, the line will be invisible.
        """
        from babylon.engine.observers import MetricsCollector
        from babylon.engine.scenarios import create_imperial_circuit_scenario
        from babylon.engine.simulation import Simulation
        from babylon.ui.dpg_runner import DashboardState, update_wealth_trend

        state, config, defines = create_imperial_circuit_scenario()
        metrics = MetricsCollector(mode="interactive")
        sim = Simulation(state, config, observers=[metrics], defines=defines)

        # Create dashboard state
        dash_state = DashboardState()
        dash_state.simulation = sim

        # Mock DPG calls since we're not running actual GUI
        with (
            patch("babylon.ui.dpg_runner.dpg") as mock_dpg,
            patch("babylon.ui.dpg_runner.get_state", return_value=dash_state),
        ):
            mock_dpg.set_value = MagicMock()
            mock_dpg.fit_axis_data = MagicMock()

            # Run a tick
            sim.step()

            # Call update_wealth_trend
            update_wealth_trend()

            # Verify all 4 series have data
            assert len(dash_state.pw_wealth_x) == 1, "P_w x data missing"
            assert len(dash_state.pw_wealth_y) == 1, "P_w y data missing"
            assert len(dash_state.pc_wealth_x) == 1, "P_c x data missing - invisible line bug"
            assert len(dash_state.pc_wealth_y) == 1, "P_c y data missing - invisible line bug"
            assert len(dash_state.cb_wealth_x) == 1, "C_b x data missing"
            assert len(dash_state.cb_wealth_y) == 1, "C_b y data missing"
            assert len(dash_state.cw_wealth_x) == 1, "C_w x data missing"
            assert len(dash_state.cw_wealth_y) == 1, "C_w y data missing"

    def test_all_series_update_on_same_tick(self) -> None:
        """All 4 wealth series must update together (no lag between series).

        If one series has N points, all series should have N points.
        This ensures consistent display updates across all wealth lines.
        """
        from babylon.engine.observers import MetricsCollector
        from babylon.engine.scenarios import create_imperial_circuit_scenario
        from babylon.engine.simulation import Simulation
        from babylon.ui.dpg_runner import DashboardState, update_wealth_trend

        state, config, defines = create_imperial_circuit_scenario()
        metrics = MetricsCollector(mode="interactive")
        sim = Simulation(state, config, observers=[metrics], defines=defines)

        dash_state = DashboardState()
        dash_state.simulation = sim

        with (
            patch("babylon.ui.dpg_runner.dpg") as mock_dpg,
            patch("babylon.ui.dpg_runner.get_state", return_value=dash_state),
        ):
            mock_dpg.set_value = MagicMock()
            mock_dpg.fit_axis_data = MagicMock()

            # Run 5 ticks
            for _ in range(5):
                sim.step()
                update_wealth_trend()

            # All series should have same length
            pw_len = len(dash_state.pw_wealth_x)
            pc_len = len(dash_state.pc_wealth_x)
            cb_len = len(dash_state.cb_wealth_x)
            cw_len = len(dash_state.cw_wealth_x)

            assert pw_len == pc_len == cb_len == cw_len == 5, (
                f"Series lengths differ: pw={pw_len}, pc={pc_len}, cb={cb_len}, cw={cw_len}"
            )

    def test_p_c_wealth_distinguishable_from_other_classes(self) -> None:
        """P_c wealth values should be distinct from other classes.

        Root cause investigation: If P_c values overlap with another class,
        the line may appear invisible due to z-order or identical positioning.
        """
        from babylon.engine.observers import MetricsCollector
        from babylon.engine.scenarios import create_imperial_circuit_scenario
        from babylon.engine.simulation import Simulation

        state, config, defines = create_imperial_circuit_scenario()
        metrics = MetricsCollector(mode="batch")
        sim = Simulation(state, config, observers=[metrics], defines=defines)

        # Run 10 ticks
        for _ in range(10):
            sim.step()

        latest = metrics.latest
        assert latest is not None
        assert latest.p_w is not None
        assert latest.p_c is not None
        assert latest.c_b is not None
        assert latest.c_w is not None

        # Get all wealth values
        p_w = latest.p_w.wealth
        p_c = latest.p_c.wealth
        c_b = latest.c_b.wealth
        c_w = latest.c_w.wealth

        # P_c should be distinct from all others (not overlapping)
        # Allow for small differences (0.001 threshold) but should be distinguishable
        assert abs(p_c - p_w) > 0.001, f"P_c ({p_c}) overlaps with P_w ({p_w})"
        assert abs(p_c - c_b) > 0.001, f"P_c ({p_c}) overlaps with C_b ({c_b})"
        assert abs(p_c - c_w) > 0.001, f"P_c ({p_c}) overlaps with C_w ({c_w})"

        # P_c should be positive (has 15% cut)
        assert p_c > 0, f"P_c wealth should be positive: {p_c}"
