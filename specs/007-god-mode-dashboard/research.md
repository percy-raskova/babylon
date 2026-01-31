# Research: God Mode Dashboard (Phase 1)

**Feature**: 007-god-mode-dashboard | **Date**: 2026-01-31

## Executive Summary

This document captures technology research and decisions for the God Mode Dashboard. The dashboard visualizes Babylon simulation state using PyQt6 with pydeck H3 hexagonal maps. Key decisions resolve around:

1. **PyQt6 + QWebEngineView** for embedding pydeck WebGL maps
2. **QWebChannel** for bidirectional JavaScript-Python communication
3. **Incremental JSON updates** to avoid 10MB HTML regeneration per tick
4. **30 FPS throttling** with state coalescing for rapid tick updates

## 1. GUI Framework Selection

### Decision: PyQt6

**Alternatives Considered**:

| Framework | Pros | Cons |
|-----------|------|------|
| PyQt6 | QWebEngineView for pydeck, mature, well-documented | Commercial license for closed-source |
| PySide6 | LGPL license, Qt-official | Fewer community examples |
| DearPyGui | Already in project (dpg_runner.py) | Cannot render WebGL; 74k hex limit proven |
| NiceGUI | Web-first, hot reload | Requires browser, network overhead |

**Rationale**: PyQt6 selected because:
- QWebEngineView (Chromium) supports pydeck WebGL rendering
- Same Qt binding family as existing research (ai-docs/epochs/epoch2)
- Babylon is open-source (GPL-compatible usage)
- DearPyGui proven inadequate for 74k+ territories per ai-docs rationale

### Reference: ai-docs/epochs/epoch2/pyqt-visualization.yaml

```yaml
rationale:
  problem: "DearPyGui canvas cannot render 74,000+ territories"
  solution: "Embed deck.gl via QWebEngineView for WebGL-accelerated hexagons"
```

## 2. Map Rendering Strategy

### Decision: pydeck + H3HexagonLayer

**Approach**:
1. Generate initial HTML via `pydeck.Deck.to_html()`
2. Inject QWebChannel bridge JavaScript into HTML
3. Use `evaluateJavaScript()` for incremental color updates

**Initial Render**:
```python
import pydeck as pdk

layer = pdk.Layer(
    "H3HexagonLayer",
    data=territories_df,  # DataFrame with h3 column
    get_hexagon="h3",
    get_fill_color="color",  # RGB list
    extruded=False,
    opacity=0.8,
)

deck = pdk.Deck(
    layers=[layer],
    initial_view_state=pdk.ViewState(
        latitude=42.3314,   # Detroit center
        longitude=-83.0458,
        zoom=9,
    ),
    map_style="dark",
)

html = deck.to_html(as_string=True)
```

**Incremental Update** (FR-011 compliant):
```python
# Instead of regenerating HTML, push JSON and call deck.setProps()
update_js = f"""
deck.setProps({{
    layers: [new deck.H3HexagonLayer({{
        data: {json.dumps(hex_data)},
        getHexagon: d => d.h3,
        getFillColor: d => d.color,
    }})]
}});
"""
self.map_view.page().runJavaScript(update_js)
```

**Performance Benefit**:
- Initial HTML: ~200KB (pydeck runtime + initial data)
- Incremental JSON: ~50KB for 2,000 hexes with colors
- Avoids 10MB HTML regeneration per tick

## 3. JavaScript-Python Bridge

### Decision: QWebChannel

**Mechanism**:
1. Register Python QObject with QWebChannel
2. Inject `qwebchannel.js` into pydeck HTML
3. Call Python slots from JavaScript, emit signals back

**Python Side**:
```python
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt6.QtWebChannel import QWebChannel

class HexBridge(QObject):
    hex_clicked = pyqtSignal(str)  # Emits H3 index

    @pyqtSlot(str)
    def on_hex_click(self, h3_index: str) -> None:
        """Called from JavaScript when user clicks hex."""
        self.hex_clicked.emit(h3_index)
```

**JavaScript Side** (injected into pydeck HTML):
```javascript
new QWebChannel(qt.webChannelTransport, function(channel) {
    window.bridge = channel.objects.bridge;

    deck.setProps({
        onClick: function(info) {
            if (info.object && info.object.h3) {
                window.bridge.on_hex_click(info.object.h3);
            }
        }
    });
});
```

**Registration**:
```python
channel = QWebChannel(self.map_view.page())
channel.registerObject("bridge", self.bridge)
self.map_view.page().setWebChannel(channel)
```

## 4. Threading Model

### Decision: Main Thread Only (MVP)

**Spec Assumption**:
> Observer callbacks from SimulationControl.register_observer() are invoked on the main thread; no cross-thread marshalling is required in the dashboard.

**Implications**:
- No QThread or QRunnable needed for MVP
- Observer callback directly updates Qt widgets
- Throttling implemented via QTimer coalescing, not thread synchronization

**Future Consideration** (post-MVP):
If simulation runs in worker thread, use `pyqtSignal` to marshal to main thread:
```python
class DashboardObserver(QObject):
    tick_received = pyqtSignal(int, object)  # tick, snapshot

    def on_tick(self, tick: int, snapshot: SimulationSnapshot) -> None:
        # This may be called from worker thread
        self.tick_received.emit(tick, snapshot)

    @pyqtSlot(int, object)
    def _handle_tick(self, tick: int, snapshot: SimulationSnapshot) -> None:
        # This runs on main thread
        self._update_display(tick, snapshot)
```

## 5. Throttling Strategy

### Decision: 30 FPS with State Coalescing

**Requirements**:
- SC-003: Updates visible within 100ms of tick
- Edge Case: Handle 100+ ticks/second by coalescing

**Implementation**:
```python
class ThrottledObserver:
    MIN_INTERVAL_MS = 33  # 30 FPS

    def __init__(self) -> None:
        self._last_update = 0
        self._pending_snapshot: SimulationSnapshot | None = None
        self._timer = QTimer()
        self._timer.timeout.connect(self._flush)

    def on_tick(self, tick: int, snapshot: SimulationSnapshot) -> None:
        now = time.time() * 1000
        if now - self._last_update >= self.MIN_INTERVAL_MS:
            self._apply_update(snapshot)
            self._last_update = now
        else:
            # Coalesce: save latest, flush on timer
            self._pending_snapshot = snapshot
            if not self._timer.isActive():
                remaining = self.MIN_INTERVAL_MS - (now - self._last_update)
                self._timer.start(int(remaining))

    def _flush(self) -> None:
        if self._pending_snapshot:
            self._apply_update(self._pending_snapshot)
            self._pending_snapshot = None
            self._last_update = time.time() * 1000
        self._timer.stop()
```

**Behavior**:
- First tick: immediate update
- Rapid ticks (<33ms apart): buffer latest, timer fires at 33ms
- Always displays most recent state (no stale data)

## 6. Memory Management

### Decision: Explicit Cleanup + Monitoring

**Concern**: SC-006 requires <50MB growth over 10,000 ticks

**Strategies**:
1. **Explicit unregister**: `unregister_observer()` in `closeEvent()`
2. **Snapshot disposal**: Don't cache old snapshots; each tick overwrites
3. **JavaScript GC**: Deck.gl manages WebGL resources; call `deck.finalize()` on close
4. **Monitoring**: Add debug logging for memory if needed

**Close Event**:
```python
def closeEvent(self, event: QCloseEvent) -> None:
    self.simulation.unregister_observer(self.observer.on_tick)
    self.map_view.page().runJavaScript("if (deck) deck.finalize();")
    event.accept()
```

## 7. Error Handling

### Decision: Graceful Degradation per FR-015

**Requirements**:
- FR-015: Handle exceptions gracefully, log, display error indicator

**Approach**:
```python
def on_tick(self, tick: int, snapshot: SimulationSnapshot) -> None:
    try:
        self._update_map(snapshot)
        self._update_inspector(snapshot)
    except Exception as e:
        logger.error("Tick update failed: %s", e, exc_info=True)
        self._show_error_indicator()
```

**Error Indicator**:
- Red border on inspector panel
- Status bar message: "Update error - see logs"
- Continue displaying last known good state

## 8. Testing Strategy

### Decision: pytest-qt + Mock Simulation

**Dependencies**:
```toml
[tool.poetry.group.dev.dependencies]
pytest-qt = "^4.2"
```

**Test Layers**:

| Layer | What | How |
|-------|------|-----|
| Unit | Color mapping, theme constants | Pure Python tests |
| Component | InspectorPanel display | pytest-qt with mock TerritoryState |
| Integration | Full dashboard + simulation | pytest-qt with MockSimulation |

**Mock Simulation**:
```python
class MockSimulation:
    """Implements SimulationState + SimulationControl protocols."""

    def __init__(self, territories: list[TerritoryState]) -> None:
        self._tick = 0
        self._territories = {t.territory_id: t for t in territories}
        self._observers: list[ObserverCallback] = []

    def step(self, n: int = 1) -> None:
        for _ in range(n):
            self._tick += 1
            snapshot = self._make_snapshot()
            for cb in self._observers:
                cb(self._tick, snapshot)
```

## 9. Open Questions Resolved

| Question | Resolution |
|----------|------------|
| pyqtSignal for components? | Yes, use signals for decoupling (e.g., `hex_clicked`) |
| setHtml vs setUrl? | Use `setHtml()` for MVP simplicity; temp files add I/O overhead |
| H3 resolution? | Resolution 5 per TerritoryState model validation |

## 10. Documentation Research (Context7 + Web)

### H3 Resolution 5 Specifications

From [H3 Official Documentation](https://h3geo.org/):

| Resolution | Average Hexagon Area | Average Edge Length |
|------------|---------------------|---------------------|
| 5 | ~252.9 km² | ~8.5 km |

Resolution 5 is appropriate for county-level visualization:
- Detroit metro (~17 counties) fits comfortably
- ~2,000 hexes covers the region
- `highPrecision: 'auto'` works well at res 5 (coarse resolution may trigger high-precision mode)

### deck.gl H3HexagonLayer Click Handling

From [deck.gl Official Documentation](https://deck.gl/docs/api-reference/geo-layers/h3-hexagon-layer):

```javascript
// H3HexagonLayer with click handling
new H3HexagonLayer({
  id: 'h3-layer',
  data: hexData,
  pickable: true,  // REQUIRED for click events
  getHexagon: d => d.hex,
  getFillColor: d => d.color,
  onClick: (info, event) => {
    // info.object contains the clicked data item
    if (info.object) {
      console.log('Clicked hex:', info.object.hex);
    }
  }
});
```

**Key Properties**:
- `pickable: true` - Required to enable picking/click events
- `onClick(info, event)` - Callback receives PickingInfo with `.object` property
- `getTooltip({object})` - Built-in tooltip support
- `coverage` - Hexagon radius multiplier (0-1), default 1

### deck.gl setProps for Incremental Updates

From [deck.gl Performance Guide](https://deck.gl/docs/developer-guide/performance):

```javascript
// Efficient layer updates via setProps
deckInstance.setProps({
  layers: [
    new H3HexagonLayer({
      id: 'h3-layer',  // IMPORTANT: consistent ID for layer matching
      data: newData,
      // ... other props
    })
  ]
});
```

**Performance Notes**:
- deck.gl compares layer props by reference
- Only changed props trigger buffer regeneration
- Use consistent layer IDs for efficient diffing
- For large datasets, consider async iterables (v7.2.0+)

### PyQt6 Signal/Slot Pattern

From [PyQt6 Official Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/signals_slots):

```python
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

class HexBridge(QObject):
    # Define signal with type
    hex_clicked = pyqtSignal(str)

    @pyqtSlot(str)
    def on_hex_click(self, h3_index: str) -> None:
        """Slot called from JavaScript via QWebChannel."""
        self.hex_clicked.emit(h3_index)

# Connection
bridge.hex_clicked.connect(inspector.display_territory_for_hex)

# Disconnect
bridge.hex_clicked.disconnect(inspector.display_territory_for_hex)
```

### pydeck HTML Generation

From [pydeck Documentation](https://deckgl.readthedocs.io/en/latest/):

```python
# Generate HTML with options
html = deck.to_html(
    as_string=True,           # Return string, not file
    css_background_color="#1a1a1a",  # Theme background
    custom_libraries=[        # Inject external JS
        {
            "libraryName": "QWebChannelBridge",
            "resourceUri": "qrc:///qtwebchannel/qwebchannel.js"
        }
    ]
)
```

**Key Parameters**:
- `as_string=True` - Returns HTML string for `setHtml()`
- `css_background_color` - Background color styling
- `custom_libraries` - Inject additional JavaScript
- `offline=True` - Use bundled assets (no CDN)

### QWebChannel Setup

From [Qt6 Documentation](https://doc.qt.io/qt-6/qwebchannel.html):

```python
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEnginePage

# Setup
channel = QWebChannel(page)
channel.registerObject("bridge", bridge_object)
page.setWebChannel(channel)

# In JavaScript (after loading qwebchannel.js)
new QWebChannel(qt.webChannelTransport, function(channel) {
    window.bridge = channel.objects.bridge;
    // Now can call: window.bridge.on_hex_click("852a1072fffffff")
});
```

**Note**: `qt.webChannelTransport` is automatically available when QWebChannel is set on the page.

## References

- ai-docs/epochs/epoch2/pyqt-visualization.yaml
- ai-docs/design-system.yaml
- specs/006-gui-protocol-extension/
- [pydeck Documentation](https://deckgl.readthedocs.io/en/latest/)
- [deck.gl H3HexagonLayer](https://deck.gl/docs/api-reference/geo-layers/h3-hexagon-layer)
- [deck.gl Performance Guide](https://deck.gl/docs/developer-guide/performance)
- [PyQt6 Signals and Slots](https://www.riverbankcomputing.com/static/Docs/PyQt6/signals_slots)
- [Qt6 QWebChannel](https://doc.qt.io/qt-6/qwebchannel.html)
- [H3 Geospatial Indexing](https://h3geo.org/)
