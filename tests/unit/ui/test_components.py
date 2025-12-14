"""Tests for SystemLog UI component.

RED Phase: These tests define the contract for the SystemLog component.
The SystemLog provides INSTANT display of raw simulation events (NO typewriter
animation - this is the key difference from NarrativeTerminal).

Test Intent:
- SystemLog initializes with empty entries and scroll area
- Log entries are added INSTANTLY (not queued)
- Log levels default to INFO and can be WARN or ERROR
- Each level has correct Design System colors
- Multiple logs maintain chronological order

Aesthetic: "Bunker Constructivism" - Terminal output style.

Design System Colors (from ai-docs/design-system.yaml):
- Container: bg-[#050505] border border-[#404040] p-4 overflow-auto
- INFO level: text-[#39FF14] (data_green)
- WARN level: text-[#FFD700] (exposed_copper)
- ERROR level: text-[#D40000] (phosphor_burn_red)
"""


class TestSystemLogInitialization:
    """Test SystemLog instantiation and initial state."""

    def test_can_be_instantiated(self) -> None:
        """SystemLog can be created without error."""
        from babylon.ui.components import SystemLog

        log = SystemLog()

        assert log is not None

    def test_initializes_with_empty_entries(self) -> None:
        """SystemLog starts with an empty entries list."""
        from babylon.ui.components import SystemLog

        log = SystemLog()

        assert log._entries == []
        assert len(log._entries) == 0

    def test_has_scroll_area(self) -> None:
        """SystemLog creates a scroll_area element."""
        from babylon.ui.components import SystemLog

        log = SystemLog()

        assert hasattr(log, "scroll_area")
        assert log.scroll_area is not None


class TestSystemLogLogging:
    """Test log entry operations."""

    def test_log_adds_entry_immediately(self) -> None:
        """log() adds entry to _entries list immediately (no queue)."""
        from babylon.ui.components import SystemLog

        log = SystemLog()

        log.log("Test message")

        assert len(log._entries) == 1
        assert log._entries[0][0] == "Test message"

    def test_log_default_level_is_info(self) -> None:
        """log() defaults to INFO level when not specified."""
        from babylon.ui.components import SystemLog

        log = SystemLog()

        log.log("Test message")

        assert log._entries[0][1] == "INFO"

    def test_log_accepts_warn_level(self) -> None:
        """log() accepts WARN level."""
        from babylon.ui.components import SystemLog

        log = SystemLog()

        log.log("Warning message", level="WARN")

        assert log._entries[0][1] == "WARN"

    def test_log_accepts_error_level(self) -> None:
        """log() accepts ERROR level."""
        from babylon.ui.components import SystemLog

        log = SystemLog()

        log.log("Error message", level="ERROR")

        assert log._entries[0][1] == "ERROR"

    def test_log_stores_level_with_entry(self) -> None:
        """log() stores the level alongside the text as a tuple."""
        from babylon.ui.components import SystemLog

        log = SystemLog()

        log.log("Some message", level="WARN")

        entry = log._entries[0]
        assert isinstance(entry, tuple)
        assert len(entry) == 2
        assert entry == ("Some message", "WARN")

    def test_multiple_logs_maintain_order(self) -> None:
        """Multiple log() calls maintain chronological order."""
        from babylon.ui.components import SystemLog

        log = SystemLog()

        log.log("First message", level="INFO")
        log.log("Second message", level="WARN")
        log.log("Third message", level="ERROR")

        assert log._entries[0] == ("First message", "INFO")
        assert log._entries[1] == ("Second message", "WARN")
        assert log._entries[2] == ("Third message", "ERROR")


class TestSystemLogStyling:
    """Test Design System color compliance."""

    def test_info_level_uses_data_green(self) -> None:
        """INFO level maps to data_green (#39FF14) from Design System."""
        from babylon.ui.components import SystemLog

        expected_color = "#39FF14"

        assert SystemLog.LEVEL_COLORS["INFO"] == expected_color

    def test_warn_level_uses_exposed_copper(self) -> None:
        """WARN level maps to exposed_copper (#FFD700) from Design System."""
        from babylon.ui.components import SystemLog

        expected_color = "#FFD700"

        assert SystemLog.LEVEL_COLORS["WARN"] == expected_color

    def test_error_level_uses_phosphor_burn_red(self) -> None:
        """ERROR level maps to phosphor_burn_red (#D40000) from Design System."""
        from babylon.ui.components import SystemLog

        expected_color = "#D40000"

        assert SystemLog.LEVEL_COLORS["ERROR"] == expected_color


class TestSystemLogContainerStyling:
    """Test container styling constants."""

    def test_container_classes_match_design_system(self) -> None:
        """Container classes match Bunker Constructivism terminal_output spec."""
        from babylon.ui.components import SystemLog

        # Based on design-system.yaml terminal_output component
        expected = "bg-[#050505] border border-[#404040] p-4 overflow-auto font-mono text-sm"

        assert expected == SystemLog.CONTAINER_CLASSES


# =============================================================================
# TrendPlotter Tests
# =============================================================================

"""Tests for TrendPlotter UI component.

RED Phase: These tests define the contract for the TrendPlotter component.
TrendPlotter provides real-time EChart line graphs for Imperial Rent and
Global Tension metrics over the last 50 ticks.

Test Intent:
- TrendPlotter initializes with empty data lists
- push_data() adds tick, rent, and tension values
- Rolling window maintains max 50 data points
- Colors match Design System specification

Aesthetic: "Bunker Constructivism" - CRT-style charts.

Design System Colors (from ai-docs/design-system.yaml):
- Chart background: void (#050505)
- Axis lines/grid: dark_metal (#404040)
- Axis labels/legend: silver_dust (#C0C0C0)
- Imperial Rent line: data_green (#39FF14)
- Global Tension line: phosphor_burn_red (#D40000)
"""


class TestTrendPlotterInitialization:
    """Test TrendPlotter instantiation and initial state."""

    def test_can_be_instantiated(self) -> None:
        """TrendPlotter can be created without error."""
        from babylon.ui.components import TrendPlotter

        plotter = TrendPlotter()

        assert plotter is not None

    def test_initializes_with_empty_data(self) -> None:
        """TrendPlotter starts with empty data lists."""
        from babylon.ui.components import TrendPlotter

        plotter = TrendPlotter()

        assert len(plotter._ticks) == 0
        assert len(plotter._rent_data) == 0
        assert len(plotter._tension_data) == 0

    def test_ticks_list_starts_empty(self) -> None:
        """TrendPlotter _ticks list starts empty."""
        from babylon.ui.components import TrendPlotter

        plotter = TrendPlotter()

        assert plotter._ticks == []

    def test_rent_data_list_starts_empty(self) -> None:
        """TrendPlotter _rent_data list starts empty."""
        from babylon.ui.components import TrendPlotter

        plotter = TrendPlotter()

        assert plotter._rent_data == []

    def test_tension_data_list_starts_empty(self) -> None:
        """TrendPlotter _tension_data list starts empty."""
        from babylon.ui.components import TrendPlotter

        plotter = TrendPlotter()

        assert plotter._tension_data == []


class TestTrendPlotterDataManagement:
    """Test data management and rolling window behavior."""

    def test_push_data_adds_tick(self) -> None:
        """push_data() adds tick to _ticks list."""
        from babylon.ui.components import TrendPlotter

        plotter = TrendPlotter()

        plotter.push_data(tick=1, rent=100.0, tension=0.5)

        assert 1 in plotter._ticks

    def test_push_data_adds_rent_value(self) -> None:
        """push_data() adds rent value to _rent_data list."""
        from babylon.ui.components import TrendPlotter

        plotter = TrendPlotter()

        plotter.push_data(tick=1, rent=100.0, tension=0.5)

        assert 100.0 in plotter._rent_data

    def test_push_data_adds_tension_value(self) -> None:
        """push_data() adds tension value to _tension_data list."""
        from babylon.ui.components import TrendPlotter

        plotter = TrendPlotter()

        plotter.push_data(tick=1, rent=100.0, tension=0.5)

        assert 0.5 in plotter._tension_data

    def test_push_data_maintains_max_50_points(self) -> None:
        """push_data() caps data at MAX_POINTS (50)."""
        from babylon.ui.components import TrendPlotter

        plotter = TrendPlotter()

        # Add exactly 50 points
        for i in range(50):
            plotter.push_data(tick=i, rent=float(i), tension=float(i) / 100)

        assert len(plotter._ticks) == 50
        assert len(plotter._rent_data) == 50
        assert len(plotter._tension_data) == 50

    def test_push_data_with_51_points_removes_oldest_tick(self) -> None:
        """push_data() removes oldest tick when exceeding MAX_POINTS."""
        from babylon.ui.components import TrendPlotter

        plotter = TrendPlotter()

        # Add 51 points
        for i in range(51):
            plotter.push_data(tick=i, rent=float(i), tension=float(i) / 100)

        # Tick 0 should be gone, tick 1 should be first
        assert 0 not in plotter._ticks
        assert plotter._ticks[0] == 1
        assert len(plotter._ticks) == 50

    def test_push_data_with_51_points_removes_oldest_rent(self) -> None:
        """push_data() removes oldest rent when exceeding MAX_POINTS."""
        from babylon.ui.components import TrendPlotter

        plotter = TrendPlotter()

        # Add 51 points with unique rent values
        for i in range(51):
            plotter.push_data(tick=i, rent=float(i * 10), tension=float(i) / 100)

        # Rent 0.0 should be gone, rent 10.0 should be first
        assert 0.0 not in plotter._rent_data
        assert plotter._rent_data[0] == 10.0
        assert len(plotter._rent_data) == 50

    def test_push_data_with_51_points_removes_oldest_tension(self) -> None:
        """push_data() removes oldest tension when exceeding MAX_POINTS."""
        from babylon.ui.components import TrendPlotter

        plotter = TrendPlotter()

        # Add 51 points with unique tension values
        for i in range(51):
            plotter.push_data(tick=i, rent=float(i), tension=float(i) / 1000)

        # Tension 0.0 should be gone, tension 0.001 should be first
        assert 0.0 not in plotter._tension_data
        assert plotter._tension_data[0] == 0.001
        assert len(plotter._tension_data) == 50

    def test_multiple_push_maintains_order(self) -> None:
        """Multiple push_data() calls maintain chronological order."""
        from babylon.ui.components import TrendPlotter

        plotter = TrendPlotter()

        plotter.push_data(tick=1, rent=100.0, tension=0.1)
        plotter.push_data(tick=2, rent=200.0, tension=0.2)
        plotter.push_data(tick=3, rent=300.0, tension=0.3)

        assert plotter._ticks == [1, 2, 3]
        assert plotter._rent_data == [100.0, 200.0, 300.0]
        assert plotter._tension_data == [0.1, 0.2, 0.3]


class TestTrendPlotterStyling:
    """Test Design System color compliance."""

    def test_imperial_rent_color_is_data_green(self) -> None:
        """Imperial Rent line color is data_green (#39FF14) from Design System."""
        from babylon.ui.components import TrendPlotter

        expected_color = "#39FF14"

        assert expected_color == TrendPlotter.DATA_GREEN

    def test_global_tension_color_is_phosphor_burn_red(self) -> None:
        """Global Tension line color is phosphor_burn_red (#D40000) from Design System."""
        from babylon.ui.components import TrendPlotter

        expected_color = "#D40000"

        assert expected_color == TrendPlotter.PHOSPHOR_BURN_RED

    def test_max_points_constant_is_50(self) -> None:
        """MAX_POINTS constant is 50 for rolling window."""
        from babylon.ui.components import TrendPlotter

        assert TrendPlotter.MAX_POINTS == 50
