# Quickstart: God Mode Dashboard (Phase 1)

**Feature**: 007-god-mode-dashboard | **Date**: 2026-01-31

## Overview

The God Mode Dashboard provides real-time visualization of the Babylon simulation. This guide shows how to launch the dashboard and connect it to a running simulation.

## Prerequisites

```bash
# Install dependencies (PyQt6 + pydeck)
poetry install

# Verify PyQt6 is available
poetry run python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')"

# Verify pydeck is available
poetry run python -c "import pydeck; print('pydeck OK')"
```

## Basic Usage

### Launch Dashboard with Simulation

```python
from babylon.engine.simulation import Simulation
from babylon.ui.dashboard import DashboardWindow

# Create simulation (hydrates from Detroit data)
sim = Simulation()

# Create and show dashboard
app = QApplication([])
dashboard = DashboardWindow(sim)
dashboard.show()

# Run Qt event loop
app.exec()
```

### Launch Dashboard Standalone (Development)

```python
from babylon.ui.dashboard import DashboardWindow
from babylon.ui.dashboard.testing import MockSimulation

# Create mock simulation with test data
mock = MockSimulation.with_detroit_territories()

# Create and show dashboard
app = QApplication([])
dashboard = DashboardWindow(mock)
dashboard.show()
app.exec()
```

## User Interactions

### Viewing the Map

1. Launch the dashboard
2. The Detroit region displays as H3 hexagons
3. Colors indicate profit_rate:
   - **Red** (#D40000): Low profit rate (0.0)
   - **Green** (#39FF14): High profit rate (1.0)
   - **Gradient**: Values between 0 and 1

### Selecting a Territory

1. Click any hexagon on the map
2. The Inspector panel (right side) updates to show:
   - Territory ID (FIPS code)
   - Controlling polity
   - Current tick
   - Profit rate (percentage)
   - Equilibrium R value
   - Hex count (number of claimed hexes)
3. Selected territory hexes are highlighted

### Clicking Unclaimed Hexes

If you click a hex that no territory claims:
- Inspector shows "No territory claims this hex"
- The clicked H3 index is displayed for reference

### Clearing Selection

Click on the map background (not on any hex) to clear the selection.

## Real-Time Updates

When connected to a running simulation:

1. The simulation's `step()` method triggers observer callbacks
2. Dashboard receives `SimulationSnapshot` with updated state
3. Map colors update to reflect new profit_rate values
4. Inspector updates if the selected territory changed

```python
# Manual stepping (for testing)
sim.step()        # Advance 1 tick
sim.step(10)      # Advance 10 ticks

# Each step triggers dashboard update automatically
```

## Throttling Behavior

The dashboard throttles updates to 30 FPS (33ms minimum interval):

- If ticks arrive faster than 30 FPS, intermediate states are coalesced
- The dashboard always displays the most recent snapshot
- This prevents UI freezing during rapid simulation runs

## Error Handling

### Connection Lost

If the simulation becomes unavailable:
1. Status bar shows "Disconnected"
2. Last known state is preserved
3. Selected territory remains highlighted
4. Dashboard auto-reconnects when simulation resumes

### Exceptions

If an update fails:
1. Error is logged at DEBUG level (FR-013)
2. Error indicator appears in status bar
3. Dashboard continues operating with last known good state

## Configuration

### Theme

The dashboard uses the "Bunker Constructivism" theme from the design system:

```python
# Colors are defined in src/babylon/ui/dashboard/theme.py
BUNKER_CONSTRUCTIVISM = {
    "void": "#050505",           # Deep black
    "wet_concrete": "#1a1a1a",   # Primary background
    "soot": "#2d2d2d",           # Secondary background
    "data_green": "#39FF14",     # High profit rate
    "phosphor_burn_red": "#D40000",  # Low profit rate
}
```

### Window Size

Default window: 1460×820 pixels (minimum supported size)

The splitter between map and inspector can be adjusted by dragging.

## API Reference

### DashboardWindow

```python
class DashboardWindow(QMainWindow):
    """Main dashboard window.

    Args:
        simulation: Object implementing SimulationState and SimulationControl protocols.
        parent: Optional parent widget.
    """

    def __init__(
        self,
        simulation: SimulationState & SimulationControl,
        parent: QWidget | None = None,
    ) -> None: ...
```

### MapViewport

```python
class MapViewport(QWidget):
    """H3 hexagonal map visualization.

    Signals:
        hex_clicked(str): Emitted when user clicks a hex. Payload is H3 index.
    """

    def update_colors(self, snapshot: SimulationSnapshot) -> None:
        """Update hex colors from simulation snapshot."""

    def highlight_territory(self, territory_id: str) -> None:
        """Highlight all hexes belonging to a territory."""

    def clear_highlight(self) -> None:
        """Remove all highlights."""
```

### InspectorPanel

```python
class InspectorPanel(QWidget):
    """Territory detail display panel.

    Shows the "Value Tensor" (all numeric properties) of the selected territory.
    """

    def display_territory(self, territory: TerritoryState) -> None:
        """Display territory details."""

    def display_no_selection(self) -> None:
        """Display 'No territory selected' message."""

    def display_unclaimed(self, h3_index: str) -> None:
        """Display 'No territory claims this hex' message."""
```

## Testing the Dashboard

### Run with Mock Data

```bash
# Launch dashboard with demo simulation (no database required)
poetry run python -m babylon.ui.dashboard --demo
```

### Run Integration Tests

```bash
# Run dashboard tests (requires pytest-qt)
poetry run pytest tests/integration/ui/test_dashboard_simulation.py -v
```

## Troubleshooting

### "No module named PyQt6"

```bash
poetry install  # Ensure dependencies installed
```

### Blank Map (No Hexes)

1. Check simulation has territories: `len(sim.get_snapshot().territories)`
2. Check territories have hex_claims: `territory.hex_claims`
3. Check H3 indices are valid resolution 5

### Clicks Not Registering

1. Check QWebChannel is connected (console log in DevTools)
2. Verify HexBridge is registered correctly
3. Check for JavaScript errors in pydeck HTML

### Performance Issues

1. Enable throttling debug logging: `DEBUG=babylon.ui.dashboard`
2. Check if >30 FPS updates are being coalesced
3. Profile with Qt Creator if needed
