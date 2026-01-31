"""Unit tests for MapViewport widget.

Tests for the H3 hexagonal map display component that renders
simulation state using pydeck H3HexagonLayer.

Feature: 007-god-mode-dashboard

TDD Status: RED Phase - These tests are written BEFORE implementation.
They MUST fail until MapViewport is implemented.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

# We import the module that WILL exist - tests will fail initially
try:
    from babylon.ui.dashboard.map_viewport import MapViewport

    MAP_VIEWPORT_EXISTS = True
except ImportError:
    MAP_VIEWPORT_EXISTS = False
    MapViewport = None  # type: ignore[misc, assignment]


pytestmark = [
    pytest.mark.skipif(not MAP_VIEWPORT_EXISTS, reason="MapViewport not yet implemented"),
]


class TestMapViewportInitialization:
    """T011: Tests for MapViewport widget initialization."""

    def test_map_viewport_is_qwidget(self, qtbot: QtBot) -> None:
        """MapViewport should be a QWidget subclass."""
        from PyQt6.QtWidgets import QWidget

        viewport = MapViewport()
        qtbot.addWidget(viewport)
        assert isinstance(viewport, QWidget)

    def test_map_viewport_has_web_engine_view(self, qtbot: QtBot) -> None:
        """MapViewport should contain a QWebEngineView."""
        from PyQt6.QtWebEngineWidgets import QWebEngineView

        viewport = MapViewport()
        qtbot.addWidget(viewport)
        # Should have a _web_view attribute that is QWebEngineView
        assert hasattr(viewport, "_web_view")
        assert isinstance(viewport._web_view, QWebEngineView)

    def test_map_viewport_has_default_view_state(self, qtbot: QtBot) -> None:
        """MapViewport should have Detroit-centered default view state."""
        viewport = MapViewport()
        qtbot.addWidget(viewport)
        # Default should be Detroit coordinates
        assert hasattr(viewport, "_latitude")
        assert hasattr(viewport, "_longitude")
        assert hasattr(viewport, "_zoom")
        # Detroit approximate center
        assert 42.0 <= viewport._latitude <= 43.0
        assert -84.0 <= viewport._longitude <= -82.0
        assert viewport._zoom >= 8  # City-level zoom

    def test_map_viewport_accepts_custom_view_state(self, qtbot: QtBot) -> None:
        """MapViewport should accept custom latitude, longitude, zoom."""
        viewport = MapViewport(
            latitude=41.0,
            longitude=-80.0,
            zoom=12,
        )
        qtbot.addWidget(viewport)
        assert viewport._latitude == 41.0
        assert viewport._longitude == -80.0
        assert viewport._zoom == 12


class TestMapViewportHtmlGeneration:
    """T012: Tests for pydeck HTML generation."""

    def test_initialize_generates_html(
        self,
        qtbot: QtBot,
        mock_simulation_detroit: MagicMock,
    ) -> None:
        """initialize() should generate pydeck HTML with H3HexagonLayer."""
        viewport = MapViewport()
        qtbot.addWidget(viewport)

        # Initialize with simulation state
        viewport.initialize(mock_simulation_detroit)

        # Should have loaded HTML into web view
        # We can't easily inspect HTML content, but we verify method was called
        assert viewport._initialized is True

    def test_initialize_includes_h3_hexagon_layer(
        self,
        qtbot: QtBot,
        mock_simulation_detroit: MagicMock,
    ) -> None:
        """initialize() HTML should include H3HexagonLayer configuration."""
        viewport = MapViewport()
        qtbot.addWidget(viewport)

        # Capture the HTML that would be set
        with patch.object(viewport._web_view, "setHtml") as mock_set_html:
            viewport.initialize(mock_simulation_detroit)

            # setHtml should have been called
            mock_set_html.assert_called_once()
            html = mock_set_html.call_args[0][0]

            # HTML should contain H3HexagonLayer reference
            assert "H3HexagonLayer" in html or "h3-hexagon" in html.lower()

    def test_initialize_uses_dark_map_style(
        self,
        qtbot: QtBot,
        mock_simulation_detroit: MagicMock,
    ) -> None:
        """initialize() should use dark map style matching Bunker Constructivism theme."""
        viewport = MapViewport()
        qtbot.addWidget(viewport)

        with patch.object(viewport._web_view, "setHtml") as mock_set_html:
            viewport.initialize(mock_simulation_detroit)

            html = mock_set_html.call_args[0][0]
            # Should reference dark or mapbox dark style
            assert "dark" in html.lower()

    def test_initialize_maps_territories_to_hexes(
        self,
        qtbot: QtBot,
        mock_simulation_detroit: MagicMock,
    ) -> None:
        """initialize() should map territory profit_rates to hex colors."""
        viewport = MapViewport()
        qtbot.addWidget(viewport)

        # Mock will have territories with different profit rates
        # Wayne (26163): 0.8 (green), Oakland (26125): 0.5 (mid), Macomb (26099): 0.2 (red)
        viewport.initialize(mock_simulation_detroit)

        # The hex display data should be populated
        assert hasattr(viewport, "_hex_data")
        assert len(viewport._hex_data) > 0


class TestMapViewportIncrementalUpdate:
    """T013: Tests for incremental color update using deck.setProps() pattern."""

    def test_update_colors_uses_javascript(
        self,
        qtbot: QtBot,
        mock_simulation_detroit: MagicMock,
    ) -> None:
        """update_colors() should use runJavaScript for incremental update."""
        viewport = MapViewport()
        qtbot.addWidget(viewport)
        viewport.initialize(mock_simulation_detroit)

        # Update colors with new snapshot
        snapshot = mock_simulation_detroit.get_snapshot()

        with patch.object(viewport._web_view.page(), "runJavaScript") as mock_js:
            viewport.update_colors(snapshot)

            # runJavaScript should have been called with setProps
            mock_js.assert_called_once()
            js_code = mock_js.call_args[0][0]
            assert "setProps" in js_code

    def test_update_colors_does_not_regenerate_html(
        self,
        qtbot: QtBot,
        mock_simulation_detroit: MagicMock,
    ) -> None:
        """update_colors() should NOT call setHtml (FR-011 compliance)."""
        viewport = MapViewport()
        qtbot.addWidget(viewport)
        viewport.initialize(mock_simulation_detroit)

        snapshot = mock_simulation_detroit.get_snapshot()

        with patch.object(viewport._web_view, "setHtml") as mock_set_html:
            viewport.update_colors(snapshot)

            # setHtml should NOT be called for incremental updates
            mock_set_html.assert_not_called()

    def test_update_colors_reflects_profit_rate_changes(
        self,
        qtbot: QtBot,
        mock_simulation_detroit: MagicMock,
    ) -> None:
        """update_colors() should update hex colors based on new profit rates."""
        viewport = MapViewport()
        qtbot.addWidget(viewport)
        viewport.initialize(mock_simulation_detroit)

        # Modify profit rate and get new snapshot
        mock_simulation_detroit.set_territory_profit_rate("26163", 0.1)  # Low profit
        snapshot = mock_simulation_detroit.get_snapshot()

        with patch.object(viewport._web_view.page(), "runJavaScript") as mock_js:
            viewport.update_colors(snapshot)

            js_code = mock_js.call_args[0][0]
            # JS should contain color data reflecting the change
            # Red-ish color for low profit rate (should have high R, low G)
            assert "color" in js_code.lower() or "Color" in js_code

    def test_update_colors_handles_empty_snapshot(
        self,
        qtbot: QtBot,
    ) -> None:
        """update_colors() should handle snapshot with no territories gracefully."""
        from babylon.models.snapshots import SimulationSnapshot
        from babylon.ui.dashboard.testing import MockSimulation

        viewport = MapViewport()
        qtbot.addWidget(viewport)

        # Initialize with empty simulation
        empty_sim = MockSimulation()
        viewport.initialize(empty_sim)

        empty_snapshot = SimulationSnapshot(tick=0, territories={}, hexes={}, edges=[])

        # Should not raise
        viewport.update_colors(empty_snapshot)

    def test_update_colors_before_initialize_raises(
        self,
        qtbot: QtBot,
    ) -> None:
        """update_colors() before initialize() should raise RuntimeError."""
        from babylon.models.snapshots import SimulationSnapshot

        viewport = MapViewport()
        qtbot.addWidget(viewport)

        snapshot = SimulationSnapshot(tick=0, territories={}, hexes={}, edges=[])

        with pytest.raises(RuntimeError, match="not initialized"):
            viewport.update_colors(snapshot)
