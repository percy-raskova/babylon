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
