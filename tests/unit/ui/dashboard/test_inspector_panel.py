"""Unit tests for InspectorPanel widget.

Tests for the territory details panel that displays Value Tensor
properties when a hex is selected.

Feature: 007-god-mode-dashboard

TDD Status: RED Phase - These tests are written BEFORE implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

# Import the module that WILL exist - tests will fail initially
try:
    from babylon.ui.dashboard.inspector_panel import InspectorPanel

    INSPECTOR_PANEL_EXISTS = True
except ImportError:
    INSPECTOR_PANEL_EXISTS = False
    InspectorPanel = None  # type: ignore[misc, assignment]


pytestmark = [
    pytest.mark.skipif(not INSPECTOR_PANEL_EXISTS, reason="InspectorPanel not yet implemented"),
]


class TestInspectorPanelInitialization:
    """Tests for InspectorPanel widget initialization."""

    def test_inspector_panel_is_qframe(self, qtbot: QtBot) -> None:
        """InspectorPanel should be a QFrame subclass."""
        from PyQt6.QtWidgets import QFrame

        panel = InspectorPanel()
        qtbot.addWidget(panel)
        assert isinstance(panel, QFrame)

    def test_inspector_panel_has_title_label(self, qtbot: QtBot) -> None:
        """InspectorPanel should have a title label."""
        panel = InspectorPanel()
        qtbot.addWidget(panel)
        assert hasattr(panel, "_title_label")
        assert panel._title_label is not None

    def test_inspector_panel_starts_with_no_selection(self, qtbot: QtBot) -> None:
        """InspectorPanel should start in no_selection state."""
        panel = InspectorPanel()
        qtbot.addWidget(panel)
        # Display text should indicate click to select
        text = panel._get_display_text().lower()
        assert "click" in text or "select" in text


class TestInspectorPanelDisplayTerritory:
    """T019: Tests for InspectorPanel.display_territory() method."""

    def test_display_territory_shows_territory_id(
        self,
        qtbot: QtBot,
        wayne_county_territory,
    ) -> None:
        """display_territory() should show territory_id (FIPS code)."""
        panel = InspectorPanel()
        qtbot.addWidget(panel)

        panel.display_territory(wayne_county_territory)

        # Should display FIPS code 26163
        assert "26163" in panel._get_display_text()

    def test_display_territory_shows_controlling_polity(
        self,
        qtbot: QtBot,
        wayne_county_territory,
    ) -> None:
        """display_territory() should show controlling_polity."""
        panel = InspectorPanel()
        qtbot.addWidget(panel)

        panel.display_territory(wayne_county_territory)

        # Should display controller
        text = panel._get_display_text()
        assert wayne_county_territory.controlling_polity in text

    def test_display_territory_shows_profit_rate(
        self,
        qtbot: QtBot,
        wayne_county_territory,
    ) -> None:
        """display_territory() should show formatted profit_rate."""
        panel = InspectorPanel()
        qtbot.addWidget(panel)

        panel.display_territory(wayne_county_territory)

        # Wayne County has profit_rate=0.075 (7.5%), should show as percentage
        text = panel._get_display_text()
        assert "7.5" in text or "0.075" in text

    def test_display_territory_shows_equilibrium_r(
        self,
        qtbot: QtBot,
        wayne_county_territory,
    ) -> None:
        """display_territory() should show equilibrium_r."""
        panel = InspectorPanel()
        qtbot.addWidget(panel)

        panel.display_territory(wayne_county_territory)

        # Wayne County has equilibrium_r=0.065 (6.5%), displayed as 0.07 (rounded)
        text = panel._get_display_text()
        assert "0.07" in text or "0.065" in text

    def test_display_territory_shows_hex_count(
        self,
        qtbot: QtBot,
        wayne_county_territory,
    ) -> None:
        """display_territory() should show number of hex claims."""
        panel = InspectorPanel()
        qtbot.addWidget(panel)

        panel.display_territory(wayne_county_territory)

        # Wayne County has 3 hexes
        text = panel._get_display_text()
        assert "3" in text

    def test_display_territory_shows_tick(
        self,
        qtbot: QtBot,
        wayne_county_territory,
    ) -> None:
        """display_territory() should show current tick."""
        panel = InspectorPanel()
        qtbot.addWidget(panel)

        panel.display_territory(wayne_county_territory)

        # Tick should be displayed
        text = panel._get_display_text()
        assert "0" in text  # tick=0


class TestInspectorPanelDisplayNoSelection:
    """Tests for InspectorPanel.display_no_selection() method."""

    def test_display_no_selection_shows_instruction(self, qtbot: QtBot) -> None:
        """display_no_selection() should show click instruction."""
        panel = InspectorPanel()
        qtbot.addWidget(panel)

        panel.display_no_selection()

        text = panel._get_display_text().lower()
        assert "click" in text or "select" in text

    def test_display_no_selection_clears_territory_data(
        self,
        qtbot: QtBot,
        wayne_county_territory,
    ) -> None:
        """display_no_selection() should clear previous territory data."""
        panel = InspectorPanel()
        qtbot.addWidget(panel)

        # First display a territory
        panel.display_territory(wayne_county_territory)
        assert "26163" in panel._get_display_text()

        # Then clear selection
        panel.display_no_selection()
        assert "26163" not in panel._get_display_text()


class TestInspectorPanelDisplayUnclaimed:
    """Tests for InspectorPanel.display_unclaimed() method."""

    def test_display_unclaimed_shows_unclaimed_message(self, qtbot: QtBot) -> None:
        """display_unclaimed() should indicate hex is unclaimed."""
        panel = InspectorPanel()
        qtbot.addWidget(panel)

        panel.display_unclaimed("852a1000fffffff")

        text = panel._get_display_text().lower()
        assert "unclaimed" in text

    def test_display_unclaimed_shows_h3_index(self, qtbot: QtBot) -> None:
        """display_unclaimed() should show the H3 index."""
        panel = InspectorPanel()
        qtbot.addWidget(panel)

        h3_index = "852a1000fffffff"
        panel.display_unclaimed(h3_index)

        text = panel._get_display_text()
        assert h3_index in text or h3_index[:8] in text  # May truncate


class TestInspectorPanelDisplayError:
    """Tests for InspectorPanel.display_error() method with red border."""

    def test_display_error_shows_error_message(self, qtbot: QtBot) -> None:
        """display_error() should show error message."""
        panel = InspectorPanel()
        qtbot.addWidget(panel)

        panel.display_error("Connection lost")

        text = panel._get_display_text()
        assert "Connection lost" in text or "error" in text.lower()

    def test_display_error_applies_red_border(self, qtbot: QtBot) -> None:
        """display_error() should apply red border styling (FR-014)."""
        panel = InspectorPanel()
        qtbot.addWidget(panel)

        panel.display_error("Test error")

        # Should have object name for QSS styling
        assert panel.objectName() == "inspector_error"

    def test_display_territory_removes_error_border(
        self,
        qtbot: QtBot,
        wayne_county_territory,
    ) -> None:
        """display_territory() should remove error border."""
        panel = InspectorPanel()
        qtbot.addWidget(panel)

        # First show error
        panel.display_error("Test error")
        assert panel.objectName() == "inspector_error"

        # Then display territory - error styling should be removed
        panel.display_territory(wayne_county_territory)
        assert panel.objectName() == "inspector"
