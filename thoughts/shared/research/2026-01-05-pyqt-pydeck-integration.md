---
date: 2026-01-05T15:39:32-05:00
researcher: Claude
git_commit: 9b00617a3da023422f5f915fa685851bfa17fa10
branch: dev
repository: babylon
topic: "PyQt6 + QWebEngineView + pydeck Integration Patterns for H3 Map Visualization"
tags: [research, pyqt, pydeck, deckgl, qwebengineview, h3, visualization, migration]
status: complete
last_updated: 2026-01-05
last_updated_by: Claude
related_research:
  - thoughts/shared/research/2026-01-05-h3-hexagonal-integration.md
  - thoughts/shared/research/2026-01-05-h3-visualization-comparison.md
---

# Research: PyQt6 + QWebEngineView + pydeck Integration Patterns

**Date**: 2026-01-05T15:39:32-05:00
**Researcher**: Claude
**Git Commit**: 9b00617a3da023422f5f915fa685851bfa17fa10
**Branch**: dev
**Repository**: babylon

## Research Question

How to integrate PyQt6 with QWebEngineView and pydeck/deck.gl for H3 hexagonal map visualization in Babylon Phase 2, including:
1. Architecture patterns for embedding WebGL in Qt
2. Python-JavaScript bidirectional communication
3. Dynamic data updates from simulation
4. Migration path from current DearPyGui implementation

## Summary

The recommended architecture uses **PyQt6 + QWebEngineView + deck.gl JavaScript API** (bypassing pydeck for dynamic updates). Key findings:

1. **pydeck's dynamic updates are Jupyter-only** - Use deck.gl JavaScript directly with QWebChannel bridge
2. **QWebEngineView setHtml() has 2MB limit** - Use file-based loading for large visualizations
3. **QWebChannel enables bidirectional communication** - Python sends data, JavaScript returns events
4. **Crash recovery via process isolation** - Chromium runs in separate QtWebEngineProcess
5. **Current DPG UI maps cleanly to PyQt patterns** - Observer polling, rolling windows, color themes all portable

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PyQt6 Main Window                        │
├──────────────────┬──────────────────────────────────────────┤
│                  │                                          │
│  Native Widgets  │  QWebEngineView (deck.gl H3 Map)        │
│  ├─ QPushButton  │  ├─ H3HexagonLayer (territories)        │
│  ├─ PyQtGraph    │  ├─ ScatterplotLayer (agents)           │
│  ├─ QTextEdit    │  └─ deck.gl JavaScript API              │
│  └─ QLabel       │                                          │
│                  │  QWebChannel Bridge                      │
│                  │  ├─ Python → JS: updateData signal       │
│                  │  └─ JS → Python: receiveClick slot       │
│                  │                                          │
├──────────────────┴──────────────────────────────────────────┤
│                    Simulation Engine                         │
│  ├─ Observers (MetricsCollector, TopologyMonitor, etc.)     │
│  └─ WorldState → H3 hex_id mapping                          │
└─────────────────────────────────────────────────────────────┘
```

## Detailed Findings

### 1. QWebEngineView Setup

**Installation**:
```bash
pip install PyQt6 PyQt6-WebEngine
```

**Critical Import Order**: Import QtWebEngineWidgets BEFORE creating QApplication:
```python
from PyQt6.QtWebEngineWidgets import QWebEngineView  # FIRST
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)  # SECOND
```

**Required Settings for WebGL/deck.gl**:
```python
from PyQt6.QtWebEngineCore import QWebEngineSettings

view = QWebEngineView()
settings = view.settings()

# Enable WebGL (required for deck.gl)
settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)

# Enable local file access (for offline mode)
settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
```

**Loading Content**:

| Method | Use Case | Limit | Notes |
|--------|----------|-------|-------|
| `setHtml(html, baseUrl)` | Small HTML | 2 MB | Converts to data: URL |
| `setUrl(QUrl.fromLocalFile(path))` | Large files | None | Recommended for deck.gl |
| `load(QUrl("https://..."))` | Remote | None | Requires internet |

### 2. Python ↔ JavaScript Communication (QWebChannel)

**Python Side**:
```python
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal, QVariant
from PyQt6.QtWebChannel import QWebChannel

class MapBridge(QObject):
    """Bridge between Python simulation and JavaScript deck.gl"""

    # Signal to push data to JavaScript
    dataUpdated = pyqtSignal(str)  # Emits JSON string

    @pyqtSlot(str)
    def onHexagonClick(self, event_json: str):
        """Receive click events from deck.gl"""
        import json
        event = json.loads(event_json)
        hex_id = event.get('hex_id')
        print(f"Clicked territory: {hex_id}")
        # Update UI, show details, etc.

    @pyqtSlot(str)
    def onViewStateChange(self, view_state_json: str):
        """Track map zoom/pan for fog of war"""
        import json
        view = json.loads(view_state_json)
        self.current_zoom = view.get('zoom', 0)

# Setup
view = QWebEngineView()
channel = QWebChannel()
bridge = MapBridge()
channel.registerObject('bridge', bridge)
view.page().setWebChannel(channel)
```

**JavaScript Side** (in HTML):
```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://unpkg.com/deck.gl@latest/dist.min.js"></script>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
</head>
<body>
    <div id="map"></div>
    <script>
        let deckgl;
        let bridge;

        // Initialize QWebChannel connection
        new QWebChannel(qt.webChannelTransport, function(channel) {
            bridge = channel.objects.bridge;

            // Listen for data updates from Python
            bridge.dataUpdated.connect(function(jsonData) {
                const data = JSON.parse(jsonData);
                updateMap(data);
            });
        });

        // Initialize deck.gl
        deckgl = new deck.DeckGL({
            container: 'map',
            mapStyle: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
            initialViewState: {
                longitude: -98.5795,
                latitude: 39.8283,
                zoom: 4
            },
            controller: true,
            layers: [],
            onClick: (info) => {
                if (info.object && bridge) {
                    bridge.onHexagonClick(JSON.stringify({
                        hex_id: info.object.hex_id,
                        properties: info.object
                    }));
                }
            },
            onViewStateChange: ({viewState}) => {
                if (bridge) {
                    bridge.onViewStateChange(JSON.stringify(viewState));
                }
            }
        });

        function updateMap(territoryData) {
            deckgl.setProps({
                layers: [
                    new deck.H3HexagonLayer({
                        id: 'territories',
                        data: territoryData,
                        getHexagon: d => d.hex_id,
                        getFillColor: d => d.color,
                        getElevation: d => d.heat * 1000,
                        extruded: true,
                        pickable: true
                    })
                ]
            });
        }
    </script>
</body>
</html>
```

### 3. Dynamic Data Updates

**Critical Finding**: pydeck's `.update()` method only works in Jupyter notebooks, not standalone HTML.

**Solution**: Use deck.gl JavaScript API directly with `setProps()`:

```python
# Python: Emit data after each simulation tick
def on_simulation_tick(self, world_state):
    territory_data = self.export_territories_for_map(world_state)
    json_data = json.dumps(territory_data)
    self.bridge.dataUpdated.emit(json_data)  # Signal to JS

def export_territories_for_map(self, world_state):
    """Convert WorldState territories to deck.gl format"""
    territories = []
    for territory in world_state.territories:
        territories.append({
            'hex_id': territory.h3_index,  # H3 cell ID
            'color': self.heat_to_color(territory.heat),
            'heat': territory.heat,
            'population': territory.population,
            'sector_type': territory.sector_type.value
        })
    return territories
```

```javascript
// JavaScript: Update layers without page reload
bridge.dataUpdated.connect(function(jsonData) {
    const data = JSON.parse(jsonData);

    // Update existing deck.gl instance
    deckgl.setProps({
        layers: [
            new deck.H3HexagonLayer({
                id: 'territories',
                data: data,
                getHexagon: d => d.hex_id,
                getFillColor: d => d.color,
                // ... other properties
                transitions: {
                    getFillColor: 300  // Smooth color transitions
                }
            })
        ]
    });
});
```

### 4. Crash Recovery and Error Handling

**Process Isolation**:
QWebEngineView runs Chromium in a separate process (QtWebEngineProcess). If it crashes, the main app survives.

```python
from PyQt6.QtWebEngineCore import QWebEnginePage

class RobustWebView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.page().renderProcessTerminated.connect(self.handle_crash)
        self.loadFinished.connect(self.handle_load_finished)
        self._load_attempts = 0

    def handle_crash(self, status, exit_code):
        """Handle Chromium renderer crashes"""
        if status == QWebEnginePage.RenderProcessTerminationStatus.CrashedTerminationStatus:
            if self._load_attempts < 3:
                self._load_attempts += 1
                QTimer.singleShot(1000, self.reload)
            else:
                self.show_fallback_error()

    def handle_load_finished(self, ok):
        if ok:
            self._load_attempts = 0
        elif self.url().toString().startswith("data:"):
            # setHtml() exceeded 2MB limit
            self.setHtml("<h1>Content too large</h1>")

    def show_fallback_error(self):
        self.setHtml("""
            <h1>Map Unavailable</h1>
            <p>The visualization encountered an error.
               Simulation continues without map.</p>
        """)
```

### 5. Performance Optimization

**deck.gl Performance**:
- 1M data items at 60 FPS (official benchmark)
- 74,000 hexagons is trivial workload
- Use `transitions` for smooth updates

**Qt WebEngine Settings**:
```python
# Enable hardware acceleration
settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)

# Cache for faster reloads
profile = view.page().profile()
profile.setPersistentStoragePath("./cache/webengine")
profile.setCachePath("./cache/webengine_cache")
```

**Data Batching**:
```python
# Don't send every tick - batch updates
class MapUpdater:
    def __init__(self, bridge, interval_ms=500):
        self.bridge = bridge
        self.pending_data = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.flush)
        self.timer.start(interval_ms)

    def queue_update(self, data):
        self.pending_data = data  # Latest wins

    def flush(self):
        if self.pending_data:
            self.bridge.dataUpdated.emit(json.dumps(self.pending_data))
            self.pending_data = None
```

### 6. Basemap Configuration (Mapbox-free)

**Carto Free Tiles** (no API key):
```javascript
mapStyle: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'
// or: 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json'
```

**Offline/No Basemap**:
```javascript
const deckgl = new deck.DeckGL({
    container: 'map',
    mapStyle: null,  // No basemap
    initialViewState: {...},
    controller: true,
    layers: [...]
});
```

### 7. Migration Path from DearPyGui

**Component Mapping**:

| DPG Component | PyQt Equivalent | Notes |
|---------------|-----------------|-------|
| `dpg.window()` | `QMainWindow` | Main application window |
| `dpg.child_window()` | `QFrame`/`QScrollArea` | Scrollable containers |
| `dpg.add_button()` | `QPushButton` | With `clicked.connect()` |
| `dpg.add_text()` | `QLabel` | Static text |
| `dpg.add_plot()` | `pyqtgraph.PlotWidget` | Time-series charts |
| `dpg.add_line_series()` | `PlotWidget.plot()` | Line data |
| Global render loop | `QTimer` | Event-driven updates |
| `get_state()` global | `self.state` attribute | Class-based state |

**DashboardState Migration**:
```python
# Current DPG pattern (dpg_runner.py:115-172)
@dataclass
class DashboardState:
    simulation: Simulation | None = None
    simulation_running: bool = False
    tick: int = 0
    rent_data_x: list[float] = field(default_factory=list)
    rent_data_y: list[float] = field(default_factory=list)
    # ...

# PyQt pattern
class BabylonDashboard(QMainWindow):
    tick_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.simulation: Simulation | None = None
        self.simulation_running = False
        self.tick = 0
        self.rent_data = deque(maxlen=50)  # Auto-rolling window
```

**Callback Migration**:
```python
# DPG pattern (dpg_runner.py:633-647)
def on_step():
    state = get_state()
    state.simulation.step()
    update_all_ui()

# PyQt pattern
class BabylonDashboard(QMainWindow):
    @pyqtSlot()
    def on_step(self):
        self.simulation.step()
        self.update_all_ui()
```

**Timer-Based Simulation Loop**:
```python
# Replace DPG render loop (dpg_runner.py:1455-1479)
class BabylonDashboard(QMainWindow):
    def __init__(self):
        super().__init__()

        # 1-second tick timer (matches current TICK_INTERVAL)
        self.tick_timer = QTimer()
        self.tick_timer.timeout.connect(self.on_timer_tick)

    def on_play(self):
        self.simulation_running = True
        self.tick_timer.start(1000)  # 1 second

    def on_pause(self):
        self.simulation_running = False
        self.tick_timer.stop()

    def on_timer_tick(self):
        if self.simulation and self.simulation_running:
            try:
                self.simulation.step()
                self.tick = self.simulation.current_state.tick
                self.update_all_ui()
            except Exception as e:
                self.log_error(str(e))
                self.on_pause()  # Auto-pause on error
```

**Observer Access** (preserved pattern):
```python
# Current pattern (dpg_runner.py:839-847)
for observer in state.simulation._observers:
    if isinstance(observer, MetricsCollector):
        metrics_collector = observer
        break

# Same pattern works in PyQt
for observer in self.simulation._observers:
    if isinstance(observer, MetricsCollector):
        self.metrics_collector = observer
        break
```

### 8. Complete Integration Example

```python
"""
babylon_qt_dashboard.py - PyQt6 + deck.gl H3 Map Dashboard

Architecture:
- QMainWindow with native widgets for controls/plots
- QWebEngineView for H3 hexagonal map (deck.gl)
- QWebChannel for Python ↔ JavaScript communication
"""

import sys
import json
import os
from pathlib import Path
from collections import deque
from typing import Any

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSplitter, QTextEdit
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal, QTimer, QUrl, Qt

import pyqtgraph as pg

# Babylon imports
from babylon.engine.simulation import Simulation
from babylon.scenarios.imperial_circuit import create_imperial_circuit_scenario
from babylon.engine.observer import MetricsCollector


class MapBridge(QObject):
    """Bridge between Python and JavaScript deck.gl"""

    dataUpdated = pyqtSignal(str)

    @pyqtSlot(str)
    def onHexagonClick(self, event_json: str):
        event = json.loads(event_json)
        print(f"Territory clicked: {event.get('hex_id')}")

    @pyqtSlot(str)
    def onViewStateChange(self, view_state_json: str):
        pass  # Track zoom level for fog of war


class BabylonDashboard(QMainWindow):
    """Main dashboard window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Babylon - The Fall of America")
        self.setGeometry(100, 100, 1600, 900)

        # State
        self.simulation: Simulation | None = None
        self.simulation_running = False
        self.tick = 0
        self.metrics_collector: MetricsCollector | None = None

        # Rolling window buffers (50 points)
        self.rent_data = deque(maxlen=50)
        self.wealth_data = {
            'p_w': deque(maxlen=50),
            'c_b': deque(maxlen=50),
        }

        # Timer for PLAY mode
        self.tick_timer = QTimer()
        self.tick_timer.timeout.connect(self.on_timer_tick)

        self.init_ui()
        self.init_simulation()

    def init_ui(self):
        """Build UI layout"""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout()
        central.setLayout(main_layout)

        # Left panel: Controls + Plots
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)

        # Control buttons
        btn_layout = QHBoxLayout()
        self.btn_step = QPushButton("STEP")
        self.btn_step.clicked.connect(self.on_step)
        self.btn_play = QPushButton("PLAY")
        self.btn_play.clicked.connect(self.on_play)
        self.btn_pause = QPushButton("PAUSE")
        self.btn_pause.clicked.connect(self.on_pause)
        btn_layout.addWidget(self.btn_step)
        btn_layout.addWidget(self.btn_play)
        btn_layout.addWidget(self.btn_pause)
        left_layout.addLayout(btn_layout)

        # Tick display
        self.tick_label = QLabel("Tick: 0")
        left_layout.addWidget(self.tick_label)

        # PyQtGraph plot
        self.rent_plot = pg.PlotWidget(title="Imperial Rent Pool")
        self.rent_curve = self.rent_plot.plot(pen='g')
        left_layout.addWidget(self.rent_plot)

        # Event log
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        left_layout.addWidget(self.event_log)

        # Right panel: H3 Map
        self.map_view = QWebEngineView()
        self.setup_map_view()

        # Splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.map_view)
        splitter.setSizes([500, 1100])

        main_layout.addWidget(splitter)

    def setup_map_view(self):
        """Configure QWebEngineView for deck.gl"""
        settings = self.map_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

        # Setup bridge
        self.channel = QWebChannel()
        self.bridge = MapBridge()
        self.channel.registerObject('bridge', self.bridge)
        self.map_view.page().setWebChannel(self.channel)

        # Load HTML
        html_path = Path(__file__).parent / "map_template.html"
        self.map_view.setUrl(QUrl.fromLocalFile(str(html_path.absolute())))

    def init_simulation(self):
        """Create simulation with observers"""
        initial_state, config, defines = create_imperial_circuit_scenario()

        self.metrics_collector = MetricsCollector(mode="interactive", rolling_window=50)

        self.simulation = Simulation(
            initial_state, config,
            observers=[self.metrics_collector],
            defines=defines,
        )

    @pyqtSlot()
    def on_step(self):
        """Execute single simulation tick"""
        if self.simulation:
            try:
                self.simulation.step()
                self.tick = self.simulation.current_state.tick
                self.update_all_ui()
            except Exception as e:
                self.log_event(f"ERROR: {e}", "red")

    @pyqtSlot()
    def on_play(self):
        """Start automatic ticking"""
        self.simulation_running = True
        self.tick_timer.start(1000)  # 1 second interval

    @pyqtSlot()
    def on_pause(self):
        """Stop automatic ticking"""
        self.simulation_running = False
        self.tick_timer.stop()

    def on_timer_tick(self):
        """Called by QTimer in PLAY mode"""
        if self.simulation_running:
            self.on_step()

    def update_all_ui(self):
        """Update all UI components"""
        self.tick_label.setText(f"Tick: {self.tick}")

        # Update plots
        if self.metrics_collector and self.metrics_collector.latest:
            metrics = self.metrics_collector.latest
            self.rent_data.append(metrics.imperial_rent_pool)
            self.rent_curve.setData(list(self.rent_data))

        # Update map
        self.update_map()

    def update_map(self):
        """Send territory data to deck.gl"""
        if not self.simulation:
            return

        # Export territories with H3 indices
        territory_data = []
        state = self.simulation.current_state

        for territory in state.territories:
            territory_data.append({
                'hex_id': getattr(territory, 'h3_index', '89283082c2fffff'),  # Placeholder
                'heat': float(territory.heat),
                'color': self.heat_to_color(territory.heat),
            })

        self.bridge.dataUpdated.emit(json.dumps(territory_data))

    def heat_to_color(self, heat: float) -> list[int]:
        """Convert heat value to RGBA color"""
        if heat < 0.3:
            return [57, 255, 20, 200]   # Green (cool)
        elif heat < 0.7:
            return [255, 215, 0, 200]   # Amber (warm)
        else:
            return [212, 0, 0, 200]     # Red (hot)

    def log_event(self, text: str, color: str = "white"):
        """Add event to log"""
        self.event_log.append(f'<span style="color:{color}">{text}</span>')


def main():
    app = QApplication(sys.argv)

    # Apply dark theme
    app.setStyleSheet("""
        QWidget { background-color: #050505; color: #C0C0C0; }
        QPushButton { background-color: #404040; padding: 8px; }
        QPushButton:hover { background-color: #1A1A1A; }
        QTextEdit { background-color: #1A1A1A; }
    """)

    window = BabylonDashboard()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

## Code References

### Current Implementation
- `src/babylon/ui/dpg_runner.py:1345-1483` - DPG main render loop
- `src/babylon/ui/dpg_runner.py:115-172` - DashboardState dataclass
- `src/babylon/ui/dpg_runner.py:197-235` - create_simulation() with observers
- `src/babylon/ui/dpg_runner.py:633-802` - Button callbacks
- `src/babylon/ui/dpg_runner.py:1231-1241` - update_all_ui() orchestration
- `src/babylon/ui/design_system.py:42-247` - Color palette (BunkerPalette, DPGColors)

### Future Implementation Points
- Territory model needs `h3_index` field: `src/babylon/models/entities/territory.py:21`
- WorldState graph conversion: `src/babylon/models/world_state.py:108-275`

## Architecture Documentation

### Process Model
```
Main Process (Python/Qt)
    │
    ├── GUI Thread (QApplication event loop)
    │   ├── Native widgets (QPushButton, QLabel, etc.)
    │   ├── PyQtGraph plots
    │   └── QWebEngineView (proxy to renderer)
    │
    └── QtWebEngineProcess (Chromium renderer, separate process)
        ├── deck.gl JavaScript
        ├── WebGL context
        └── H3 hexagon rendering
```

### Data Flow
```
Simulation.step()
    ↓
MetricsCollector.on_tick()
    ↓
update_all_ui()
    ├── update_plots() → PyQtGraph
    └── update_map() → MapBridge.dataUpdated.emit()
                           ↓
                       QWebChannel IPC
                           ↓
                       JavaScript callback
                           ↓
                       deckgl.setProps({layers: [...]})
```

## Historical Context

This research builds on:
- `thoughts/shared/research/2026-01-05-h3-hexagonal-integration.md` - H3 fundamentals
- `thoughts/shared/research/2026-01-05-h3-visualization-comparison.md` - DPG vs web-based comparison
- Decision to use PyQt + pydeck (this session)

## Open Questions

1. **H3 Index Generation**: When to generate H3 indices for territories?
   - At scenario creation? (static assignment)
   - At runtime from coordinates? (dynamic)

2. **Map Template Location**: Where to store `map_template.html`?
   - `src/babylon/ui/templates/` (bundled with app)
   - Qt resource system (`.qrc` files)

3. **Offline Assets**: Should deck.gl JS be bundled or loaded from CDN?
   - CDN: Smaller distribution, requires internet
   - Bundle: Larger distribution, fully offline

4. **Threading**: Should simulation run in separate QThread?
   - Current: Main thread (1-second tick is fast enough)
   - Future: QThread if simulation becomes slow

5. **Hot Reload**: Can we update deck.gl without full page reload?
   - Yes: `deckgl.setProps()` with transitions
   - Implemented in JavaScript side

## Sources

### PyQt6 / QWebEngineView
- [QWebEngineView Documentation](https://doc.qt.io/qt-6/qwebengineview.html)
- [QWebChannel JavaScript API](https://doc.qt.io/qtforpython-6/overviews/qtwebchannel-javascript.html)
- [PyQt6-WebEngine PyPI](https://pypi.org/project/PyQt6-WebEngine/)

### pydeck / deck.gl
- [pydeck Deck API](https://deckgl.readthedocs.io/en/latest/deck.html)
- [deck.gl Standalone Usage](https://deck.gl/docs/get-started/using-standalone)
- [H3HexagonLayer API](https://deck.gl/docs/api-reference/geo-layers/h3-hexagon-layer)

### Integration Examples
- [PyQt WebView JavaScript Example](https://gist.github.com/mphuie/63e964e9ff8ae25d16a949389392e0d7)
- [pyqt-folium-example](https://github.com/yjg30737/pyqt-folium-example)
- [Qt WebEngine CORS Issues](https://forum.qt.io/topic/132956/qwebengineview-javascript-fetch-cors-error)
