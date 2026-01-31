"""MapViewport widget for H3 hexagonal map display.

This module provides the MapViewport widget that renders simulation
territories as H3 hexagons using pydeck H3HexagonLayer via QWebEngineView.

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QUrl  # type: ignore[import-not-found]
from PyQt6.QtWebChannel import QWebChannel  # type: ignore[import-not-found]
from PyQt6.QtWebEngineWidgets import QWebEngineView  # type: ignore[import-not-found]
from PyQt6.QtWidgets import QVBoxLayout, QWidget  # type: ignore[import-not-found]

from babylon.ui.dashboard.models import HexDisplayData
from babylon.ui.dashboard.theme import profit_rate_to_rgb

if TYPE_CHECKING:
    from babylon.models.snapshots import SimulationSnapshot
    from babylon.protocols import SimulationState
    from babylon.ui.dashboard.hex_bridge import HexBridge

logger = logging.getLogger(__name__)

# Detroit center coordinates
DETROIT_LATITUDE = 42.3314
DETROIT_LONGITUDE = -83.0458
DEFAULT_ZOOM = 9


class MapViewport(QWidget):  # type: ignore[misc]
    """H3 hexagonal map widget using pydeck and QWebEngineView.

    This widget renders simulation territories as colored hexagons on a
    dark-themed map. Colors are derived from territory profit_rate values
    using the Bunker Constructivism palette.

    Architecture:
    1. Initial render: Generate pydeck HTML via to_html()
    2. Incremental updates: Use deck.setProps() via runJavaScript()
       (FR-011 compliance - no HTML regeneration per tick)

    Example:
        >>> viewport = MapViewport()
        >>> viewport.initialize(simulation)
        >>> # On each tick:
        >>> viewport.update_colors(snapshot)
    """

    def __init__(
        self,
        latitude: float = DETROIT_LATITUDE,
        longitude: float = DETROIT_LONGITUDE,
        zoom: int = DEFAULT_ZOOM,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize MapViewport with view state.

        Args:
            latitude: Initial map center latitude. Defaults to Detroit.
            longitude: Initial map center longitude. Defaults to Detroit.
            zoom: Initial zoom level. Defaults to 9 (city-level).
            parent: Parent widget.
        """
        super().__init__(parent)

        self._latitude = latitude
        self._longitude = longitude
        self._zoom = zoom
        self._initialized = False
        self._hex_data: list[HexDisplayData] = []
        self._channel: QWebChannel | None = None
        self._bridge: HexBridge | None = None

        # Create QWebEngineView for pydeck rendering
        self._web_view = QWebEngineView(self)

        # Set up layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._web_view)

        logger.debug(
            "MapViewport created: lat=%.4f, lon=%.4f, zoom=%d",
            latitude,
            longitude,
            zoom,
        )

    def initialize(self, simulation: SimulationState) -> None:
        """Initialize the map with simulation state.

        Generates pydeck HTML and loads it into the web view.
        Must be called before update_colors().

        Args:
            simulation: Simulation state to render.
        """
        try:
            import pydeck as pdk  # type: ignore[import-not-found]
        except ImportError as e:
            msg = "pydeck is required for MapViewport. Install with: pip install pydeck"
            raise ImportError(msg) from e

        # Get initial snapshot
        snapshot = simulation.get_snapshot()

        # Build hex data from territories
        self._hex_data = self._build_hex_data(snapshot)

        # Convert to pydeck-compatible format
        layer_data = self._hex_data_to_pydeck_format(self._hex_data)

        # Create pydeck layer
        layer = pdk.Layer(
            "H3HexagonLayer",
            data=layer_data,
            get_hexagon="h3",
            get_fill_color="color",
            extruded=False,
            opacity=0.8,
            pickable=True,  # Enable click events
        )

        # Create deck with dark style (Bunker Constructivism theme)
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=pdk.ViewState(
                latitude=self._latitude,
                longitude=self._longitude,
                zoom=self._zoom,
            ),
            map_style="dark",
            tooltip={"html": "<b>Profit Rate:</b> {profit_rate_pct}"},
        )

        # Generate HTML
        html = deck.to_html(as_string=True)

        # Inject QWebChannel bridge JavaScript for click handling
        html = self._inject_webchannel_bridge(html)

        # Load into web view
        self._web_view.setHtml(html, QUrl("about:blank"))
        self._initialized = True

        logger.info(
            "MapViewport initialized with %d hexes from %d territories",
            len(self._hex_data),
            len(snapshot.territories),
        )

    def update_colors(self, snapshot: SimulationSnapshot) -> None:
        """Update hex colors based on new snapshot.

        Uses deck.setProps() for incremental update (FR-011 compliance).
        Does NOT regenerate HTML.

        Args:
            snapshot: New simulation snapshot with updated territory states.

        Raises:
            RuntimeError: If called before initialize().
        """
        if not self._initialized:
            msg = "MapViewport not initialized. Call initialize() first."
            raise RuntimeError(msg)

        # Build updated hex data
        self._hex_data = self._build_hex_data(snapshot)

        # Convert to pydeck format
        layer_data = self._hex_data_to_pydeck_format(self._hex_data)

        # Generate JavaScript for incremental update
        update_js = self._generate_update_js(layer_data)

        # Execute JavaScript
        self._web_view.page().runJavaScript(update_js)

        logger.debug(
            "MapViewport updated colors for %d hexes at tick %d",
            len(self._hex_data),
            snapshot.tick,
        )

    def highlight_territory(self, territory_id: str) -> None:
        """Highlight hexes belonging to a territory (FR-014).

        Args:
            territory_id: Territory to highlight.
        """
        # Update hex data with selection state
        for i, hex_data in enumerate(self._hex_data):
            if hex_data.territory_id == territory_id:
                self._hex_data[i] = HexDisplayData(
                    h3=hex_data.h3,
                    color=hex_data.color,
                    territory_id=hex_data.territory_id,
                    selected=True,
                )

        # Re-render with highlight
        layer_data = self._hex_data_to_pydeck_format(self._hex_data)
        update_js = self._generate_update_js(layer_data)
        self._web_view.page().runJavaScript(update_js)

        logger.debug("Highlighted territory: %s", territory_id)

    def clear_highlight(self) -> None:
        """Clear any territory highlight."""
        for i, hex_data in enumerate(self._hex_data):
            if hex_data.selected:
                self._hex_data[i] = HexDisplayData(
                    h3=hex_data.h3,
                    color=hex_data.color,
                    territory_id=hex_data.territory_id,
                    selected=False,
                )

        # Re-render without highlight
        layer_data = self._hex_data_to_pydeck_format(self._hex_data)
        update_js = self._generate_update_js(layer_data)
        self._web_view.page().runJavaScript(update_js)

        logger.debug("Cleared territory highlight")

    def register_bridge(self, bridge: HexBridge) -> None:
        """Register HexBridge with QWebChannel for click handling.

        This connects the JavaScript click events to Python signals.
        Must be called after initialize() for the bridge to work.

        Args:
            bridge: HexBridge instance to register.
        """
        self._bridge = bridge

        # Create QWebChannel and register bridge
        self._channel = QWebChannel(self._web_view.page())
        self._channel.registerObject("bridge", bridge)
        self._web_view.page().setWebChannel(self._channel)

        logger.info("HexBridge registered with QWebChannel")

    def _build_hex_data(self, snapshot: SimulationSnapshot) -> list[HexDisplayData]:
        """Build HexDisplayData list from snapshot.

        Args:
            snapshot: Simulation snapshot.

        Returns:
            List of HexDisplayData for rendering.
        """
        hex_data: list[HexDisplayData] = []

        for territory_id, territory in snapshot.territories.items():
            color = profit_rate_to_rgb(territory.profit_rate)

            for h3_index in territory.hex_claims:
                hex_data.append(
                    HexDisplayData(
                        h3=h3_index,
                        color=color,
                        territory_id=territory_id,
                        selected=False,
                    )
                )

        return hex_data

    def _hex_data_to_pydeck_format(self, hex_data: list[HexDisplayData]) -> list[dict[str, object]]:
        """Convert HexDisplayData to pydeck-compatible format.

        Args:
            hex_data: List of HexDisplayData.

        Returns:
            List of dicts for pydeck layer data.
        """
        result = []
        for data in hex_data:
            # For selected hexes, add border effect by adjusting color
            color = list(data.color)
            if data.selected:
                # Brighten selected hexes
                color = [min(255, c + 40) for c in color]

            territory = data.territory_id or "unclaimed"
            # Calculate profit rate percentage for tooltip
            # Reverse-engineer from color (approximation)
            r, g, _b = data.color
            # Green component increases with profit rate
            profit_pct = f"{(g / 255.0) * 100:.1f}%"

            result.append(
                {
                    "h3": data.h3,
                    "color": color,
                    "territory_id": territory,
                    "profit_rate_pct": profit_pct,
                    "selected": data.selected,
                }
            )
        return result

    def _generate_update_js(self, layer_data: list[dict[str, object]]) -> str:
        """Generate JavaScript for incremental deck.setProps() update.

        Args:
            layer_data: Pydeck-format layer data.

        Returns:
            JavaScript code string.
        """
        data_json = json.dumps(layer_data)

        return f"""
        if (typeof deck !== 'undefined') {{
            deck.setProps({{
                layers: [new deck.H3HexagonLayer({{
                    id: 'h3-layer',
                    data: {data_json},
                    getHexagon: d => d.h3,
                    getFillColor: d => d.color,
                    extruded: false,
                    opacity: 0.8,
                    pickable: true,
                }})]
            }});
        }}
        """

    def _inject_webchannel_bridge(self, html: str) -> str:
        """Inject QWebChannel bridge JavaScript into pydeck HTML.

        This enables click events to be sent from JavaScript to Python.

        Args:
            html: Original pydeck HTML.

        Returns:
            HTML with QWebChannel bridge injected.
        """
        # JavaScript to inject before closing body tag
        bridge_js = """
        <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Initialize QWebChannel when available
            if (typeof qt !== 'undefined' && qt.webChannelTransport) {
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    window.bridge = channel.objects.bridge;

                    // Set up click handler for deck
                    if (typeof deck !== 'undefined') {
                        deck.setProps({
                            onClick: function(info) {
                                if (info.object && info.object.h3) {
                                    if (window.bridge) {
                                        window.bridge.on_hex_click(info.object.h3);
                                    }
                                } else {
                                    // Background click
                                    if (window.bridge) {
                                        window.bridge.on_background_click();
                                    }
                                }
                            }
                        });
                    }
                });
            }
        });
        </script>
        """

        # Insert before </body>
        if "</body>" in html:
            html = html.replace("</body>", bridge_js + "</body>")
        else:
            # Fallback: append at end
            html += bridge_js

        return html


__all__ = [
    "MapViewport",
    "DETROIT_LATITUDE",
    "DETROIT_LONGITUDE",
    "DEFAULT_ZOOM",
]
