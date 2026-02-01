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

        # Enable JavaScript console logging to Python logger
        self._setup_js_console_logging()

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

    def _setup_js_console_logging(self) -> None:
        """Connect JavaScript console messages to Python logger."""
        from PyQt6.QtWebEngineCore import QWebEnginePage  # type: ignore[import-not-found]

        # Create custom page to capture console messages
        page = self._web_view.page()

        def handle_console_message(
            level: QWebEnginePage.JavaScriptConsoleMessageLevel,
            message: str,
            line: int,
            _source: str,
        ) -> None:
            # Only log messages from our Babylon code (prefixed with [Babylon])
            if "[Babylon]" in message:
                logger.info("JS: %s", message)
            elif level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorLevel:
                logger.warning("JS Error: %s (line %d)", message, line)

        page.javaScriptConsoleMessage = handle_console_message

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
                    profit_rate=hex_data.profit_rate,
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
                    profit_rate=hex_data.profit_rate,
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
            profit_rate = territory.profit_rate

            logger.debug(
                "Territory %s: profit_rate=%.2f, color=%s",
                territory_id,
                profit_rate,
                color,
            )

            for h3_index in territory.hex_claims:
                hex_data.append(
                    HexDisplayData(
                        h3=h3_index,
                        color=color,
                        profit_rate=profit_rate,
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
            # Use actual profit_rate value for tooltip
            profit_pct = f"{data.profit_rate * 100:.1f}%"

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
        """Generate JavaScript for incremental layer data update.

        Finds the deck.gl instance and updates the layer data via setProps().
        Falls back gracefully if the update mechanism isn't available.

        Args:
            layer_data: Pydeck-format layer data.

        Returns:
            JavaScript code string.
        """
        data_json = json.dumps(layer_data)

        # JavaScript that finds the actual deck.gl instance and updates layer data
        return f"""
        (function() {{
            // Find the deck.gl instance - pydeck stores it in various locations
            var deckInstance = null;
            if (window.deck && typeof window.deck.setProps === 'function') {{
                deckInstance = window.deck;
            }} else if (window.deck && window.deck.deck && typeof window.deck.deck.setProps === 'function') {{
                deckInstance = window.deck.deck;
            }} else if (window.deckgl && typeof window.deckgl.setProps === 'function') {{
                deckInstance = window.deckgl;
            }}

            if (deckInstance) {{
                // Update the layer data directly
                var currentLayers = deckInstance.props.layers || [];
                if (currentLayers.length > 0) {{
                    var newData = {data_json};
                    // Clone the layer with new data
                    var oldLayer = currentLayers[0];
                    var newLayer = oldLayer.clone({{data: newData}});
                    deckInstance.setProps({{layers: [newLayer]}});
                    console.log('[Babylon] Layer data updated');
                }}
            }} else {{
                console.log('[Babylon] deck.setProps not available for update');
            }}
        }})();
        """

    def _inject_webchannel_bridge(self, html: str) -> str:
        """Inject QWebChannel bridge JavaScript into pydeck HTML.

        This enables click events to be sent from JavaScript to Python.
        Modifies pydeck's HTML to expose the deck instance globally, then
        uses canvas click interception with deck.gl pickObject() API.

        Args:
            html: Original pydeck HTML.

        Returns:
            HTML with QWebChannel bridge injected.
        """
        # First, expose pydeck's deckInstance to window scope
        # pydeck creates: const deckInstance = createDeck({...})
        # We replace it with: const deckInstance = window.deckInstance = createDeck({...})
        html = html.replace(
            "const deckInstance = createDeck(",
            "const deckInstance = window.deckInstance = createDeck(",
        )

        # JavaScript to inject before closing body tag
        # Uses IIFE with closure for state management and robust element detection
        bridge_js = """
        <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        <script>
        (function() {
            var bridgeReady = false;
            var clickHandlerReady = false;
            var retryCount = 0;
            var MAX_RETRIES = 50;  // 5 seconds max

            // Initialize QWebChannel
            function initBridge() {
                if (typeof qt !== 'undefined' && qt.webChannelTransport) {
                    new QWebChannel(qt.webChannelTransport, function(channel) {
                        window.bridge = channel.objects.bridge;
                        bridgeReady = true;
                        console.log('[Babylon] QWebChannel bridge connected');
                    });
                } else {
                    console.log('[Babylon] qt.webChannelTransport not available, retrying...');
                    setTimeout(initBridge, 100);
                }
            }

            // Find the deck.gl instance
            function findDeckInstance() {
                // Check our exposed global (from HTML modification above)
                if (window.deckInstance && typeof window.deckInstance.pickObject === 'function') {
                    return window.deckInstance;
                }
                // Fallback checks
                if (window.deck && typeof window.deck.pickObject === 'function') {
                    return window.deck;
                }
                if (window.deckgl && typeof window.deckgl.pickObject === 'function') {
                    return window.deckgl;
                }
                return null;
            }

            // Set up click handling on canvas
            function setupClickHandler() {
                if (clickHandlerReady) return;

                retryCount++;
                if (retryCount > MAX_RETRIES) {
                    console.log('[Babylon] Max retries reached, giving up on click handler setup');
                    return;
                }

                var canvas = document.querySelector('canvas');
                if (!canvas) {
                    console.log('[Babylon] Canvas not found, retry', retryCount);
                    setTimeout(setupClickHandler, 100);
                    return;
                }

                var deckInstance = findDeckInstance();
                if (!deckInstance) {
                    console.log('[Babylon] Deck instance not found, retry', retryCount);
                    setTimeout(setupClickHandler, 100);
                    return;
                }

                console.log('[Babylon] Found deck instance:', deckInstance);

                canvas.addEventListener('click', function(event) {
                    if (!bridgeReady || !window.bridge) {
                        console.log('[Babylon] Bridge not ready for click');
                        return;
                    }

                    var rect = canvas.getBoundingClientRect();
                    var x = event.clientX - rect.left;
                    var y = event.clientY - rect.top;

                    console.log('[Babylon] Click at canvas coords:', x, y);

                    try {
                        var picked = deckInstance.pickObject({
                            x: x,
                            y: y,
                            radius: 0
                        });

                        console.log('[Babylon] Pick result:', picked);

                        if (picked && picked.object && picked.object.h3) {
                            console.log('[Babylon] Hex clicked:', picked.object.h3);
                            window.bridge.on_hex_click(picked.object.h3);
                        } else {
                            console.log('[Babylon] Background clicked (no object)');
                            window.bridge.on_background_click();
                        }
                    } catch (e) {
                        console.log('[Babylon] pickObject error:', e);
                        window.bridge.on_background_click();
                    }
                });

                clickHandlerReady = true;
                console.log('[Babylon] Click handler attached to canvas');
            }

            // Initialize when DOM is ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function() {
                    initBridge();
                    setTimeout(setupClickHandler, 500); // Wait for pydeck to initialize
                });
            } else {
                initBridge();
                setTimeout(setupClickHandler, 500);
            }
        })();
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
