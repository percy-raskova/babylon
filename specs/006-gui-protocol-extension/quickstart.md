# Quickstart: GUI Protocol Extension

**Feature**: 006-gui-protocol-extension
**Date**: 2026-01-31

## Overview

This guide shows how to use the GUI protocol extensions to integrate a visualization layer with the simulation engine.

## Prerequisites

- Simulation initialized via `Simulation.from_sqlite()` or constructor
- Understanding of H3 hex indices (15-character hex strings at resolution 5)

## 1. Observer Registration

### Basic Usage

```python
from babylon.engine.simulation import Simulation
from babylon.protocols import SimulationControl, SimulationState

def on_tick(tick: int, state: SimulationState) -> None:
    """Called after each simulation tick."""
    snapshot = state.get_snapshot()
    print(f"Tick {tick}: {len(snapshot.territories)} territories")

# Initialize simulation
sim = Simulation.from_sqlite(fips_codes=["26163", "26125"])

# Register observer
sim.register_observer(on_tick)

# Run simulation - on_tick called after each tick
sim.step(10)

# Unregister when done
sim.unregister_observer(on_tick)
```

### Multiple Observers

Observers are invoked in registration order:

```python
def observer_a(tick: int, state: SimulationState) -> None:
    print(f"A: tick {tick}")

def observer_b(tick: int, state: SimulationState) -> None:
    print(f"B: tick {tick}")

sim.register_observer(observer_a)
sim.register_observer(observer_b)

sim.step()
# Output:
# A: tick 1
# B: tick 1
```

### Error Handling

Callback exceptions are logged but don't halt simulation:

```python
def buggy_observer(tick: int, state: SimulationState) -> None:
    raise RuntimeError("Oops!")

sim.register_observer(buggy_observer)
sim.step()  # Continues despite exception
# Warning logged: "Observer callback failed: Oops!"
```

## 2. Spatial Queries

### Basic Lookup

```python
from babylon.protocols import SimulationState

def handle_hex_click(sim: SimulationState, h3_index: str) -> None:
    """Handle map click event from pydeck."""
    try:
        territory = sim.get_node_by_spatial_index(h3_index)
        if territory:
            print(f"Territory: {territory.territory_id}")
            print(f"Profit rate: {territory.profit_rate:.2%}")
        else:
            print("Unclaimed hex")
    except ValueError as e:
        print(f"Invalid H3 index: {e}")
```

### Integration with Map Events

```python
# Example with pydeck (conceptual)
import pydeck as pdk

def on_click(event):
    # pydeck provides H3 index on click
    h3_index = event["object"]["h3_index"]
    territory = sim.get_node_by_spatial_index(h3_index)
    update_sidebar(territory)

# In PyQt6 GUI
layer = pdk.Layer(
    "H3HexagonLayer",
    data=hex_data,
    pickable=True,
    on_click=on_click
)
```

## 3. Thread-Safe GUI Integration

### Using ProtocolObserverAdapter

For PyQt6 applications where the GUI runs in a separate thread:

```python
from babylon.engine.observer_adapter import ProtocolObserverAdapter
from PyQt6.QtCore import QObject, pyqtSignal

class GuiBridge(QObject):
    """Bridge between simulation thread and Qt GUI."""

    tick_updated = pyqtSignal(int, object)  # tick, snapshot

    def __init__(self, simulation):
        super().__init__()
        self.adapter = ProtocolObserverAdapter(simulation)
        self.adapter.register(self._on_tick)

    def _on_tick(self, tick: int, state):
        """Called from simulation thread."""
        # Emit signal - Qt auto-queues to GUI thread
        snapshot = state.get_snapshot()  # Immutable, safe to pass
        self.tick_updated.emit(tick, snapshot)


# In main window
class MainWindow(QMainWindow):
    def __init__(self, simulation):
        super().__init__()
        self.bridge = GuiBridge(simulation)
        self.bridge.tick_updated.connect(self.update_display)

    def update_display(self, tick: int, snapshot):
        """Called in GUI thread."""
        self.tick_label.setText(f"Tick: {tick}")
        self.territory_count.setText(f"Territories: {len(snapshot.territories)}")
```

### Thread Safety Guarantees

1. **Snapshots are immutable**: Frozen Pydantic models can be safely passed across threads
1. **Registration is thread-safe**: `register_observer`/`unregister_observer` use internal locking
1. **Callbacks receive consistent state**: Snapshot created before callback iteration

## 4. Complete Example

```python
"""Complete example: GUI observer with spatial queries."""

from babylon.engine.simulation import Simulation
from babylon.protocols import SimulationState


class SimulationViewer:
    """Example GUI integration class."""

    def __init__(self, fips_codes: list[str]):
        self.sim = Simulation.from_sqlite(fips_codes=fips_codes)
        self.sim.register_observer(self._on_tick)
        self.selected_territory = None

    def _on_tick(self, tick: int, state: SimulationState) -> None:
        """Update display after each tick."""
        snapshot = state.get_snapshot()

        # Update tick display
        print(f"\n=== Tick {tick} ===")

        # Update territory summary
        for tid, territory in snapshot.territories.items():
            print(f"  {tid}: r={territory.profit_rate:.2%}")

        # Update selected territory details
        if self.selected_territory:
            territory = state.get_territory_state(self.selected_territory)
            if territory:
                print(f"  Selected: {territory.territory_id} @ {territory.profit_rate:.2%}")

    def on_hex_click(self, h3_index: str) -> None:
        """Handle map click."""
        try:
            territory = self.sim.get_node_by_spatial_index(h3_index)
            if territory:
                self.selected_territory = territory.territory_id
                print(f"Selected territory: {territory.territory_id}")
            else:
                self.selected_territory = None
                print("Clicked unclaimed hex")
        except ValueError:
            print("Invalid hex index")

    def run(self, ticks: int) -> None:
        """Run simulation."""
        self.sim.step(ticks)

    def cleanup(self) -> None:
        """Cleanup on exit."""
        self.sim.unregister_observer(self._on_tick)


# Usage
if __name__ == "__main__":
    viewer = SimulationViewer(["26163", "26125"])
    viewer.run(5)
    viewer.cleanup()
```

## Common Patterns

### Pattern 1: Debounced Updates

For expensive GUI updates, debounce rapid tick notifications:

```python
import time

class DebouncedObserver:
    def __init__(self, update_fn, min_interval: float = 0.1):
        self.update_fn = update_fn
        self.min_interval = min_interval
        self.last_update = 0

    def __call__(self, tick: int, state: SimulationState) -> None:
        now = time.time()
        if now - self.last_update >= self.min_interval:
            self.update_fn(tick, state)
            self.last_update = now
```

### Pattern 2: Filtered Updates

Only update when specific conditions change:

```python
class FilteredObserver:
    def __init__(self, update_fn, territory_id: str):
        self.update_fn = update_fn
        self.territory_id = territory_id
        self.last_profit_rate = None

    def __call__(self, tick: int, state: SimulationState) -> None:
        territory = state.get_territory_state(self.territory_id)
        if territory and territory.profit_rate != self.last_profit_rate:
            self.update_fn(tick, territory)
            self.last_profit_rate = territory.profit_rate
```

## Error Reference

| Error                          | Cause                                  | Solution                                        |
| ------------------------------ | -------------------------------------- | ----------------------------------------------- |
| `ValueError: Invalid H3 index` | Malformed H3 string                    | Validate with `h3.is_valid_cell()` before query |
| Callback not invoked           | Not registered or already unregistered | Check registration state                        |
| Stale data in callback         | Using old snapshot reference           | Always call `state.get_snapshot()` fresh        |
