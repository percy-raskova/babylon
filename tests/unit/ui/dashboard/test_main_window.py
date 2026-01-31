"""Unit tests for DashboardWindow main window.

Tests for the main window layout, theme application, and logging
as specified in User Story 4 (Phase 6).

Feature: 007-god-mode-dashboard
Requirements Covered: FR-010, FR-013, FR-015, SC-001
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

# Import the module that WILL exist - tests will fail initially
try:
    from babylon.ui.dashboard.main_window import (
        MIN_WINDOW_HEIGHT,
        MIN_WINDOW_WIDTH,
        DashboardWindow,
    )

    MAIN_WINDOW_EXISTS = True
except ImportError:
    MAIN_WINDOW_EXISTS = False
    DashboardWindow = None  # type: ignore[misc, assignment]
    MIN_WINDOW_WIDTH = 1460  # noqa: N816
    MIN_WINDOW_HEIGHT = 820  # noqa: N816

try:
    from babylon.ui.dashboard.testing import MockSimulation

    MOCK_SIMULATION_EXISTS = True
except ImportError:
    MOCK_SIMULATION_EXISTS = False
    MockSimulation = None  # type: ignore[misc, assignment]


pytestmark = [
    pytest.mark.skipif(
        not MAIN_WINDOW_EXISTS or not MOCK_SIMULATION_EXISTS,
        reason="DashboardWindow or MockSimulation not yet implemented",
    ),
]


class TestDashboardWindowLayout:
    """T044: Tests for DashboardWindow layout (QSplitter 70/30)."""

    def test_dashboard_window_is_qmainwindow(
        self, qtbot: QtBot, mock_simulation_detroit: MockSimulation
    ) -> None:
        """DashboardWindow should be a QMainWindow subclass."""
        from PyQt6.QtWidgets import QMainWindow

        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)
        assert isinstance(window, QMainWindow)

    def test_dashboard_has_map_viewport(
        self, qtbot: QtBot, mock_simulation_detroit: MockSimulation
    ) -> None:
        """DashboardWindow should contain a MapViewport widget."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)
        assert hasattr(window, "map_viewport")
        assert window.map_viewport is not None

    def test_dashboard_has_inspector_panel(
        self, qtbot: QtBot, mock_simulation_detroit: MockSimulation
    ) -> None:
        """DashboardWindow should contain an InspectorPanel widget."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)
        assert hasattr(window, "inspector_panel")
        assert window.inspector_panel is not None

    def test_dashboard_uses_splitter_layout(
        self, qtbot: QtBot, mock_simulation_detroit: MockSimulation
    ) -> None:
        """DashboardWindow should use QSplitter for layout."""
        from PyQt6.QtWidgets import QSplitter

        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)
        central = window.centralWidget()
        assert isinstance(central, QSplitter)

    def test_splitter_has_70_30_ratio(
        self, qtbot: QtBot, mock_simulation_detroit: MockSimulation
    ) -> None:
        """QSplitter should have approximately 70/30 map/inspector ratio."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)

        from PyQt6.QtWidgets import QSplitter

        splitter = window.centralWidget()
        assert isinstance(splitter, QSplitter)

        # Resize to force layout calculation
        window.resize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        window.show()
        qtbot.waitExposed(window)

        sizes = splitter.sizes()
        assert len(sizes) == 2

        total = sum(sizes)
        if total > 0:  # Avoid division by zero
            map_ratio = sizes[0] / total
            # Allow some tolerance (60-80% for map)
            assert 0.60 <= map_ratio <= 0.80

    def test_map_is_left_panel(self, qtbot: QtBot, mock_simulation_detroit: MockSimulation) -> None:
        """MapViewport should be the left (first) widget in splitter."""
        from babylon.ui.dashboard.map_viewport import MapViewport

        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)

        from PyQt6.QtWidgets import QSplitter

        splitter = window.centralWidget()
        assert isinstance(splitter, QSplitter)

        # First widget should be MapViewport
        first_widget = splitter.widget(0)
        assert isinstance(first_widget, MapViewport)

    def test_inspector_is_right_panel(
        self, qtbot: QtBot, mock_simulation_detroit: MockSimulation
    ) -> None:
        """InspectorPanel should be the right (second) widget in splitter."""
        from babylon.ui.dashboard.inspector_panel import InspectorPanel

        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)

        from PyQt6.QtWidgets import QSplitter

        splitter = window.centralWidget()
        assert isinstance(splitter, QSplitter)

        # Second widget should be InspectorPanel
        second_widget = splitter.widget(1)
        assert isinstance(second_widget, InspectorPanel)


class TestDashboardWindowSize:
    """T049: Tests for minimum window size (1460x820)."""

    def test_minimum_width(self, qtbot: QtBot, mock_simulation_detroit: MockSimulation) -> None:
        """DashboardWindow should have minimum width of 1460."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)
        assert window.minimumWidth() >= MIN_WINDOW_WIDTH

    def test_minimum_height(self, qtbot: QtBot, mock_simulation_detroit: MockSimulation) -> None:
        """DashboardWindow should have minimum height of 820."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)
        assert window.minimumHeight() >= MIN_WINDOW_HEIGHT

    def test_window_title_set(self, qtbot: QtBot, mock_simulation_detroit: MockSimulation) -> None:
        """DashboardWindow should have appropriate window title."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)
        title = window.windowTitle()
        assert "babylon" in title.lower() or "dashboard" in title.lower()


class TestDashboardWindowTheme:
    """T045: Tests for theme application (QSS)."""

    def test_stylesheet_applied(
        self, qtbot: QtBot, mock_simulation_detroit: MockSimulation
    ) -> None:
        """DashboardWindow should have a stylesheet applied."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)
        stylesheet = window.styleSheet()
        assert len(stylesheet) > 0

    def test_stylesheet_contains_background_color(
        self, qtbot: QtBot, mock_simulation_detroit: MockSimulation
    ) -> None:
        """DashboardWindow stylesheet should set background-color."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)
        stylesheet = window.styleSheet()
        assert "background-color" in stylesheet

    def test_stylesheet_uses_bunker_constructivism_colors(
        self, qtbot: QtBot, mock_simulation_detroit: MockSimulation
    ) -> None:
        """DashboardWindow stylesheet should use theme colors."""
        from babylon.ui.dashboard.theme import BUNKER_CONSTRUCTIVISM

        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)
        stylesheet = window.styleSheet().lower()

        # Check for at least one theme color
        theme_colors_found = sum(
            1 for color in BUNKER_CONSTRUCTIVISM.values() if color.lower() in stylesheet
        )
        assert theme_colors_found >= 1

    def test_stylesheet_contains_monospace_font(
        self, qtbot: QtBot, mock_simulation_detroit: MockSimulation
    ) -> None:
        """DashboardWindow stylesheet should specify monospace font."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)
        stylesheet = window.styleSheet().lower()
        assert "monospace" in stylesheet


class TestDashboardWindowStatusBar:
    """T050: Tests for status bar with connection indicator."""

    def test_status_bar_exists(self, qtbot: QtBot, mock_simulation_detroit: MockSimulation) -> None:
        """DashboardWindow should have a status bar."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)
        status_bar = window.statusBar()
        assert status_bar is not None

    def test_status_bar_shows_connection_status(
        self, qtbot: QtBot, mock_simulation_detroit: MockSimulation
    ) -> None:
        """Status bar should display connection status."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)
        status_bar = window.statusBar()
        message = status_bar.currentMessage().lower()
        # Should show connected or status info
        assert "connected" in message or "tick" in message

    def test_status_bar_shows_tick_number(
        self, qtbot: QtBot, mock_simulation_detroit: MockSimulation
    ) -> None:
        """Status bar should display current tick number."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)
        status_bar = window.statusBar()
        message = status_bar.currentMessage()
        # Should include tick info
        assert "tick" in message.lower() or any(c.isdigit() for c in message)


class TestDashboardWindowLogging:
    """T045a: Tests for DEBUG logging on connection state changes (FR-013)."""

    def test_initialization_logs_info(
        self,
        qtbot: QtBot,
        mock_simulation_detroit: MockSimulation,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """DashboardWindow initialization should log at INFO level."""
        with caplog.at_level(logging.INFO, logger="babylon.ui.dashboard.main_window"):
            window = DashboardWindow(simulation=mock_simulation_detroit)
            qtbot.addWidget(window)

        assert any("initialized" in record.message.lower() for record in caplog.records)

    def test_connection_error_logs_error(
        self,
        qtbot: QtBot,
        mock_simulation_detroit: MockSimulation,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """set_connection_error() should log at ERROR level (FR-013)."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)

        with caplog.at_level(logging.ERROR, logger="babylon.ui.dashboard.main_window"):
            window.set_connection_error("Test connection lost")

        assert any("error" in record.message.lower() for record in caplog.records)

    def test_close_event_logs_info(
        self,
        qtbot: QtBot,
        mock_simulation_detroit: MockSimulation,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """closeEvent() should log unregistration (FR-012, FR-013)."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)

        with caplog.at_level(logging.INFO, logger="babylon.ui.dashboard.main_window"):
            window.close()

        assert any("closing" in record.message.lower() for record in caplog.records)

    def test_observer_registration_logs_debug(
        self,
        qtbot: QtBot,
        mock_simulation_detroit: MockSimulation,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Observer registration should log at DEBUG level."""
        with caplog.at_level(logging.DEBUG, logger="babylon.ui.dashboard.main_window"):
            window = DashboardWindow(simulation=mock_simulation_detroit)
            qtbot.addWidget(window)

        debug_messages = [r.message.lower() for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("observer" in msg or "signal" in msg for msg in debug_messages)


class TestDashboardWindowExceptionHandling:
    """T052: Tests for graceful exception handling (FR-015)."""

    def test_invalid_simulation_does_not_crash(
        self, qtbot: QtBot, mock_simulation_detroit: MockSimulation
    ) -> None:
        """DashboardWindow should handle simulation with no territories gracefully."""
        # Use empty simulation
        from babylon.ui.dashboard.testing import MockSimulation

        empty_sim = MockSimulation()
        # Should not raise
        window = DashboardWindow(simulation=empty_sim)
        qtbot.addWidget(window)
        assert window is not None

    def test_set_connection_error_updates_inspector(
        self, qtbot: QtBot, mock_simulation_detroit: MockSimulation
    ) -> None:
        """set_connection_error() should update inspector panel (FR-015)."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)

        window.set_connection_error("Test error")

        # Inspector should show error state
        panel = window.inspector_panel
        assert panel.objectName() == "inspector_error"

    def test_set_connection_error_updates_status_bar(
        self, qtbot: QtBot, mock_simulation_detroit: MockSimulation
    ) -> None:
        """set_connection_error() should update status bar (FR-015)."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)

        window.set_connection_error("Connection timeout")

        status = window.statusBar().currentMessage()
        assert "error" in status.lower() or "timeout" in status.lower()


class TestDashboardWindowObserver:
    """Tests for DashboardObserver integration."""

    def test_observer_registered_on_init(
        self, qtbot: QtBot, mock_simulation_detroit: MockSimulation
    ) -> None:
        """DashboardObserver should be registered during init."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)
        # MockSimulation tracks registered observers
        assert len(mock_simulation_detroit.observers) == 1

    def test_observer_unregistered_on_close(
        self, qtbot: QtBot, mock_simulation_detroit: MockSimulation
    ) -> None:
        """DashboardObserver should be unregistered on window close."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)

        assert len(mock_simulation_detroit.observers) == 1
        window.close()
        assert len(mock_simulation_detroit.observers) == 0


class TestDashboardWindowHexBridge:
    """Tests for HexBridge integration."""

    def test_hex_bridge_exists(self, qtbot: QtBot, mock_simulation_detroit: MockSimulation) -> None:
        """DashboardWindow should have a HexBridge instance."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)
        assert hasattr(window, "hex_bridge")
        assert window.hex_bridge is not None

    def test_hex_bridge_connected_to_inspector(
        self,
        qtbot: QtBot,
        mock_simulation_detroit: MockSimulation,
        wayne_county_territory,
    ) -> None:
        """HexBridge.territory_selected should update InspectorPanel."""
        window = DashboardWindow(simulation=mock_simulation_detroit)
        qtbot.addWidget(window)

        # Simulate territory selection
        window.hex_bridge.territory_selected.emit(wayne_county_territory)

        # Inspector should display the territory
        text = window.inspector_panel._get_display_text()
        assert wayne_county_territory.territory_id in text


__all__ = [
    "TestDashboardWindowLayout",
    "TestDashboardWindowSize",
    "TestDashboardWindowTheme",
    "TestDashboardWindowStatusBar",
    "TestDashboardWindowLogging",
    "TestDashboardWindowExceptionHandling",
    "TestDashboardWindowObserver",
    "TestDashboardWindowHexBridge",
]
