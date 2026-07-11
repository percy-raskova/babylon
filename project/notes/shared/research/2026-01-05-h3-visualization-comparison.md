---
date: 2026-01-05T15:17:51-05:00
researcher: Claude
git_commit: 4f61f6d17780799df58e62157ac5fef67fc577c7
branch: dev
repository: babylon
topic: "H3 Hexagonal Visualization: DearPyGui Canvas vs Web-Based (Kepler.gl, deck.gl)"
tags: [research, h3, visualization, dearpygui, kepler, deckgl, webgl, hexagonal]
status: complete
last_updated: 2026-01-05
last_updated_by: Claude
related_research: thoughts/shared/research/2026-01-05-h3-hexagonal-integration.md
---

# Research: H3 Visualization - DearPyGui Canvas vs Web-Based Options

**Date**: 2026-01-05T15:17:51-05:00
**Researcher**: Claude
**Git Commit**: 4f61f6d17780799df58e62157ac5fef67fc577c7
**Branch**: dev
**Repository**: babylon

## Research Question

For future epochs of Babylon, which visualization approach should be used for H3 hexagonal map rendering?
1. DearPyGui canvas rendering (current tech stack)
2. Web-based solutions (Kepler.gl, deck.gl/pydeck, Plotly, Folium)

Key evaluation criteria:
- Performance at scale (74,000+ hexagons for Epoch 2)
- Integration with Babylon's architecture (Embedded Trinity, no external servers)
- Interactive features (zoom, pan, tooltips)
- Dynamic updates from simulation

## Summary

| Option | Performance (74k hexagons) | H3 Support | Babylon Fit |
|--------|---------------------------|------------|-------------|
| **DearPyGui** | Poor (1-5k max) | Manual | Current stack but limited |
| **pydeck** | Excellent (60 FPS @ 1M) | Native H3HexagonLayer | Best performance |
| **Kepler.gl** | Good (~500k records) | Native auto-detect | Best UI/UX |
| **Plotly** | Moderate | Manual GeoJSON | Easiest NiceGUI integration |
| **Folium** | Poor (freezes >10k) | Manual | Not recommended |

**Recommendation**: For Epoch 2+, migrate map visualization to **pydeck** for performance or **Kepler.gl** for rapid prototyping. Keep DearPyGui for simulation controls and time-series plots. Embed web visualization via PyQt WebEngine or standalone HTML export.

## Detailed Findings

### 1. Current Babylon Visualization Infrastructure

**Location**: `src/babylon/ui/dpg_runner.py` (1,483 lines)

The current "Synopticon" dashboard uses DearPyGui for immediate-mode GUI. Key characteristics:

**What Exists**:
- Line plots for time-series data (Imperial Rent, LA Stability, Wealth, Metabolic Rift)
- Scrollable text logs (Narrative feed, Event log)
- Status bar with phase indicators
- Endgame modal
- Control panel (STEP, PLAY, PAUSE, RESET)

**What Does NOT Exist**:
- No `dpg.draw_*` canvas calls
- No spatial/map visualization
- No Territory positioning or hexagonal rendering
- All visualization is 1D temporal (tick-based), not 2D spatial

**Data Flow Pattern**:
```
Simulation.step() → Observers.on_tick() → update_all_ui() → dpg.set_value()
```

The UI pulls from Observer aggregations (MetricsCollector, NarrativeDirector, TopologyMonitor) via type-based search.

**Code References**:
- `src/babylon/ui/dpg_runner.py:1345-1483` - Main render loop
- `src/babylon/ui/dpg_runner.py:243-626` - UI component builders
- `src/babylon/ui/design_system.py:187-247` - Color palette (DPGColors)

### 2. DearPyGui Canvas Capabilities for Hexagons

**Drawing API**:
```python
with dpg.drawlist(width=800, height=600):
    dpg.draw_polygon(hex_points, color=(255,255,255,255), fill=(255,0,0,255))
```

**Critical Limitations**:

| Limitation | Impact |
|------------|--------|
| No native zoom/pan for drawlists | Must implement manually or use plot workaround |
| No spatial indexing | Can't efficiently cull off-screen hexagons |
| No coordinate system support | No WGS84/Mercator projections |
| No tile system | Unlike Leaflet, no auto tile loading |
| Performance ceiling ~5k polygons | Far below 74k target |

**Workaround for Zoom/Pan**: Draw on a `plot` element instead of `drawlist`:
```python
with dpg.plot(width=800, height=600):
    dpg.add_plot_axis(dpg.mvXAxis)
    dpg.add_plot_axis(dpg.mvYAxis)
    dpg.draw_polygon(points, color=(255,255,255,255))  # Inherits plot zoom/pan
```

**Performance at Scale**:
- Realistic limit: 1,000-5,000 simple shapes at 60fps
- `dpg.move_item()` is "horribly slow" for thousands of items
- No automatic LOD (level-of-detail) system

**Alternative Desktop Libraries**:
| Library | Performance | Zoom/Pan | Notes |
|---------|-------------|----------|-------|
| PyQtGraph | 10k-100k shapes | Built-in | OpenGL, NumPy integration |
| Matplotlib | 1k-10k | Toolbar | Static/slow refresh |
| Vispy | 100k+ | Built-in | OpenGL, steep learning curve |

**Sources**:
- [DearPyGui Drawing API](https://dearpygui.readthedocs.io/en/latest/documentation/drawing-api.html)
- [GitHub Issue #1898 - Pan/Zoom Request](https://github.com/hoffstadt/DearPyGui/issues/1898) (closed, not on roadmap)
- [dearpygui-map](https://github.com/mkouhia/dearpygui-map) - Reference implementation

### 3. Kepler.gl - Native H3 Visualization

**Overview**: WebGL-based geospatial visualization tool by Uber, built on deck.gl.

**Python Package**: `keplergl` (v0.3.7)
```bash
pip install keplergl
```

**H3 Integration** - Auto-detection of H3 columns:
```python
from keplergl import KeplerGl
import pandas as pd

df = pd.DataFrame({
    'hex_id': ['89283082c2fffff', ...],  # Auto-detected!
    'wealth': [1000.0, ...],
    'consciousness': [0.5, ...]
})

map_1 = KeplerGl(height=600, use_arrow=True)  # GeoArrow for performance
map_1.add_data(data=df, name='babylon_territories')
map_1.save_to_html('babylon_map.html', read_only=True)
```

**Performance**:
- Recommended limit: ~500,000 records or ~100MB
- Browser memory ceiling: ~250MB upload limit, >540MB crashes
- GeoArrow encoding (`use_arrow=True`) provides 2-3x speedup
- For 74,000 hexagons: Should perform well

**Interactive Features**:
- Zoom/pan (WebGL-accelerated)
- Customizable tooltips
- Time-series playback
- Filters (range, categorical)
- 3D extrusion
- Color/height encodings

**Limitations**:
- No real-time streaming (data updates require full reload)
- Single H3 resolution per layer
- WGS84 only (no projected coordinates)
- Browser-based memory constraints

**Embedding Options**:

**Option A: Standalone HTML**
```python
map_1.save_to_html('babylon_map.html')
import webbrowser
webbrowser.open('babylon_map.html')
```

**Option B: PyQt WebEngine** (real-time integration)
```python
from PyQt6.QtWebEngineWidgets import QWebEngineView

class KeplerWidget(QWebEngineView):
    def __init__(self):
        super().__init__()
        self.setHtml(map_obj._repr_html_())

    def update_data(self, new_df):
        map_obj.add_data(data=new_df, name='territories')
        self.setHtml(map_obj._repr_html_())
```

**Basemap Options** (Mapbox-free since v3.0):
- MapLibre (open-source)
- MapTiler
- OpenStreetMap

**Sources**:
- [Kepler.gl H3 Layer Docs](https://docs.kepler.gl/docs/user-guides/c-types-of-layers/j-h3)
- [keplergl Jupyter Docs](https://docs.kepler.gl/docs/keplergl-jupyter)
- [Kepler.gl 3.0 MapLibre Announcement](https://openjsf.org/blog/whats-new-in-the-keplergl-30-application)

### 4. pydeck (deck.gl) - Best Performance

**Overview**: Python bindings for deck.gl, Uber's WebGL2 visualization framework.

**Python Package**: `pydeck` (v0.9.1)
```bash
pip install pydeck
```

**Native H3HexagonLayer**:
```python
import pydeck as pdk
import pandas as pd

df = pd.DataFrame({
    'hex': ['89283082c2fffff', ...],
    'count': [64, ...]
})

layer = pdk.Layer(
    "H3HexagonLayer",
    df,
    get_hexagon="hex",
    get_fill_color="[255 - count, 255, count]",
    get_elevation="count",
    pickable=True,
    extruded=True
)

view = pdk.ViewState(latitude=37.7, longitude=-122.4, zoom=11)
deck = pdk.Deck(layers=[layer], initial_view_state=view)
deck.to_html("map.html", offline=True)  # Embeds JS for portability
```

**Performance** - Best-in-class:
- **1 million data items at 60 FPS** (2015 MacBook Pro benchmark)
- For 74,000 hexagons: Expect 60 FPS
- Instanced drawing mode for efficiency
- WebGL2 GPU acceleration

**Interactive Features**:
- Zoom/pan
- Tooltips
- 3D extrusion
- Hover/click events
- Multiple layers

**Limitations**:
- Binary data transport optimized for Jupyter
- Standalone HTML requires periodic regeneration for updates
- No bidirectional Python ↔ JavaScript callbacks

**Integration with NiceGUI** (alternative UI):
```python
from nicegui import ui

html_str = deck.to_html(as_string=True, offline=True)
ui.html(html_str)
```

**Sources**:
- [H3HexagonLayer API](https://deck.gl/docs/api-reference/geo-layers/h3-hexagon-layer)
- [deck.gl Performance Guide](https://deck.gl/docs/developer-guide/performance)
- [pydeck Examples](https://deckgl.readthedocs.io/en/latest/gallery/h3_hexagon_layer.html)

### 5. Plotly - Easiest Integration

**Python Package**: `plotly`
```bash
pip install plotly
```

**H3 Integration** (manual GeoJSON conversion):
```python
import plotly.express as px
import h3

# Convert H3 cells to GeoJSON
geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [h3.cell_to_boundary(hex_id, geo_json=True)]
            },
            "id": hex_id
        }
        for hex_id in df['hex_id']
    ]
}

fig = px.choropleth_mapbox(
    df,
    geojson=geojson,
    locations='hex_id',
    color='wealth',
    mapbox_style="carto-positron"
)
```

**Performance**:
- Moderate (slower than deck.gl)
- May lag with 74k hexagons
- Optimization: Use NumPy arrays, not Python lists

**Native NiceGUI Support**:
```python
from nicegui import ui
ui.plotly(fig)  # Direct embedding!
```

**Sources**:
- [Plotly H3 Tutorial](https://towardsdatascience.com/constructing-hexagon-maps-with-h3-and-plotly-a-comprehensive-tutorial-8f37a91573bb)
- [GeoHexViz](https://github.com/mrempel/geohexviz) - High-level wrapper

### 6. Folium - Not Recommended

**Why Not**:
- Client-side Leaflet.js (SVG/Canvas, not WebGL)
- Degrades significantly above 10,000 polygons
- For 74,000 hexagons: Browser will freeze

**Verdict**: Do not use for Babylon's scale requirements.

## Comparison Matrix

| Feature | DearPyGui | pydeck | Kepler.gl | Plotly |
|---------|-----------|--------|-----------|--------|
| **Performance (74k)** | Poor (1-5k) | Excellent (1M+) | Good (500k) | Moderate |
| **H3 Native Support** | None | H3HexagonLayer | Auto-detect | Manual GeoJSON |
| **Zoom/Pan** | Manual | Built-in | Built-in | Built-in |
| **3D Extrusion** | No | Yes | Yes | Yes |
| **Tooltips** | Manual | Built-in | Built-in | Built-in |
| **Real-time Updates** | Yes | Regen HTML | Regen HTML | Dash callbacks |
| **Offline Mode** | Yes | Yes (`offline=True`) | Yes (save_to_html) | Partial |
| **Learning Curve** | Low | Medium | Low | Low |
| **Babylon Fit** | Current stack | Best performance | Best UX | Easy NiceGUI |

## Architecture Integration

### Babylon's Current Pattern
```
Simulation → Observers → DearPyGui UI
                         ├── Line Plots (time-series)
                         ├── Text Logs
                         └── Status Indicators
```

### Proposed Hybrid Pattern
```
Simulation → Observers → DearPyGui (Controls + Time-series)
                      └→ Web Visualization (H3 Map)
                         ├── pydeck (Epoch 2: performance)
                         └── Kepler.gl (prototyping)
```

### Integration Approaches

**Option A: Two Windows**
- DearPyGui window for simulation controls
- Separate browser window for H3 map
- Simplest implementation, no dependencies added

**Option B: PyQt Hybrid**
- Replace DearPyGui with PyQt6
- Embed WebEngine for map visualization
- Single window, unified experience
- Requires significant refactor

**Option C: Export-Only**
- Keep DearPyGui as primary UI
- Add "Export to Web Map" feature
- Generate HTML snapshots at key ticks
- No real-time map, but minimal changes

**Option D: NiceGUI Migration**
- NiceGUI already exists in `mutants/src/babylon/ui/`
- Native Plotly support: `ui.plotly(fig)`
- Web-based, runs in browser
- Can embed pydeck via `ui.html()`

## Recommendations by Epoch

### Epoch 1 (Current)
- **No changes needed**
- Abstract territories don't require spatial visualization
- Focus on mechanics validation

### Epoch 2 (The Game)
- **Primary**: pydeck with H3HexagonLayer
  - 74,000 hexagons at 60 FPS
  - Standalone HTML export with `offline=True`
  - Open in browser from DearPyGui button

- **Alternative**: Kepler.gl for rapid prototyping
  - Auto-detects H3 columns
  - Rich UI out-of-the-box
  - Good for stakeholder demos

### Epoch 3 (The Platform)
- **Consider**: Full migration to PyQt + WebEngine
  - Unified desktop application
  - Embedded pydeck map with zoom/pan
  - DuckDB H3 extension for native queries

- **Or**: NiceGUI migration
  - Web-first architecture
  - Native Plotly/pydeck integration
  - Multi-user support possible

## Code References

- `src/babylon/ui/dpg_runner.py:1345-1483` - Current main render loop
- `src/babylon/ui/dpg_runner.py:243-626` - UI component builders
- `src/babylon/models/entities/territory.py:21-193` - Territory model (needs H3 field)
- `mutants/src/babylon/ui/main.py:1-379` - NiceGUI alternative implementation
- `ai-docs/synopticon-spec.yaml` - UI design spec

## Historical Context

- Previous research: `thoughts/shared/research/2026-01-05-h3-hexagonal-integration.md`
  - Established H3 resolution strategy (Res 4 for counties)
  - Identified FCC hexagon download capability
  - Documented NetworkX integration pattern

## Open Questions

1. **Two Windows vs Unified UI**: Is separate browser window acceptable for map visualization?

2. **Performance Profiling**: Need to benchmark actual Territory dataset size vs theoretical limits

3. **Update Frequency**: How often should map refresh during simulation?
   - Every tick? (potentially expensive)
   - On-demand? (user clicks "Refresh Map")
   - Key events only? (ruptures, phase transitions)

4. **Basemap Selection**: Which OpenStreetMap style for Babylon's aesthetic?
   - Dark themes (Carto Dark Matter) align with Bunker Constructivism
   - Neutral themes for data legibility

5. **NiceGUI vs DearPyGui**: Is Epoch 3 the right time to migrate UI frameworks?

## Sources

### DearPyGui
- [Drawing API Documentation](https://dearpygui.readthedocs.io/en/latest/documentation/drawing-api.html)
- [Pan/Zoom Issue #1898](https://github.com/hoffstadt/DearPyGui/issues/1898)
- [dearpygui-map](https://github.com/mkouhia/dearpygui-map)

### pydeck / deck.gl
- [H3HexagonLayer API](https://deck.gl/docs/api-reference/geo-layers/h3-hexagon-layer)
- [Performance Guide](https://deck.gl/docs/developer-guide/performance)
- [pydeck Gallery](https://deckgl.readthedocs.io/en/latest/gallery/h3_hexagon_layer.html)

### Kepler.gl
- [H3 Layer Documentation](https://docs.kepler.gl/docs/user-guides/c-types-of-layers/j-h3)
- [Jupyter Integration](https://docs.kepler.gl/docs/keplergl-jupyter)
- [Kepler.gl 3.0 Announcement](https://openjsf.org/blog/whats-new-in-the-keplergl-30-application)

### Plotly
- [H3 Choropleth Tutorial](https://towardsdatascience.com/constructing-hexagon-maps-with-h3-and-plotly-a-comprehensive-tutorial-8f37a91573bb)
- [GeoHexViz Package](https://github.com/mrempel/geohexviz)

### General
- [H3 Official Documentation](https://h3geo.org/)
- [h3-py GitHub](https://github.com/uber/h3-py)
- [Red Blob Games - Hexagonal Grids](https://www.redblobgames.com/grids/hexagons/)
