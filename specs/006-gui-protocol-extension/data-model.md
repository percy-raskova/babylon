# Data Model: GUI Protocol Extension

**Feature**: 006-gui-protocol-extension
**Date**: 2026-01-31

## Overview

This feature extends two existing protocols and adds one new class. No new persistent entities are introduced.

## Type Aliases

### ObserverCallback

```python
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from babylon.protocols import SimulationState

ObserverCallback = Callable[[int, "SimulationState"], None]
```

**Description**: Type alias for GUI observer callbacks.

**Parameters**:

- `tick: int` - Current simulation tick number (0-indexed)
- `state: SimulationState` - Read-only interface to simulation state

**Returns**: None

______________________________________________________________________

## Protocol Extensions

### SimulationControl (Extended)

**Location**: `src/babylon/protocols/simulation_control.py`

**Existing methods** (unchanged):

- `step(n: int = 1) -> None`
- `reset() -> None`

**New methods**:

| Method                | Signature                              | Description                              |
| --------------------- | -------------------------------------- | ---------------------------------------- |
| `register_observer`   | `(callback: ObserverCallback) -> None` | Register callback for tick notifications |
| `unregister_observer` | `(callback: ObserverCallback) -> None` | Remove previously registered callback    |

**Behavior**:

- Callbacks invoked at end of each `step()` call
- Invocation order: registration order
- Duplicate registration: idempotent (callback invoked once per tick)
- Unregister unknown callback: no-op

______________________________________________________________________

### SimulationState (Extended)

**Location**: `src/babylon/protocols/simulation_state.py`

**Existing methods** (unchanged):

- `get_current_tick() -> int`
- `get_snapshot() -> SimulationSnapshot`
- `get_territory_state(territory_id: str) -> TerritoryState | None`
- `get_hexes_for_territory(territory_id: str) -> set[str]`

**New methods**:

| Method                      | Signature                           | Description |
| --------------------------- | ----------------------------------- | ----------- |
| `get_node_by_spatial_index` | \`(h3_index: str) -> TerritoryState | None\`      |

**Behavior**:

- Valid H3 index claimed by territory: returns TerritoryState
- Valid H3 index not claimed: returns None
- Invalid H3 format: raises ValueError

______________________________________________________________________

## New Classes

### ProtocolObserverAdapter

**Location**: `src/babylon/engine/observer_adapter.py`

**Purpose**: Bridge between engine observer notifications and GUI callbacks with thread-safe snapshot delivery.

**Attributes**:

| Attribute     | Type                     | Description                                    |
| ------------- | ------------------------ | ---------------------------------------------- |
| `_simulation` | `SimulationState`        | Reference to simulation for snapshot creation  |
| `_callbacks`  | `list[ObserverCallback]` | Registered GUI callbacks                       |
| `_lock`       | `threading.Lock`         | Synchronization for callback list modification |

**Methods**:

| Method       | Signature                              | Description                             |
| ------------ | -------------------------------------- | --------------------------------------- |
| `__init__`   | `(simulation: SimulationState)`        | Initialize with simulation reference    |
| `register`   | `(callback: ObserverCallback) -> None` | Add callback (thread-safe)              |
| `unregister` | `(callback: ObserverCallback) -> None` | Remove callback (thread-safe)           |
| `notify`     | `(tick: int) -> None`                  | Notify all callbacks with current state |

**Thread Safety**:

- `_lock` protects `_callbacks` list during register/unregister
- `notify()` creates snapshot before iterating (snapshot is immutable)
- Callback exceptions are caught and logged (per ADR003)

**Implementation Notes**:

```python
def notify(self, tick: int) -> None:
    """Notify all registered callbacks with current state.

    Thread-safe: creates snapshot before iteration, exceptions logged.
    """
    # Snapshot under lock to get consistent callback list
    with self._lock:
        callbacks = list(self._callbacks)

    # Notify outside lock (callbacks may take time)
    for callback in callbacks:
        try:
            callback(tick, self._simulation)
        except Exception as e:
            logger.warning("Observer callback failed: %s", e)
```

______________________________________________________________________

## Existing Entities (Reference)

### TerritoryState

**Location**: `src/babylon/models/snapshots.py`

**Used as**: Return type for `get_node_by_spatial_index()`

**Key attributes**:

- `territory_id: str` - FIPS code
- `hex_claims: frozenset[str]` - H3 indices claimed
- `tick: int` - Snapshot tick
- `profit_rate: float` - Current profit rate [0.0, 1.0]
- `equilibrium_r: float` - Territory equilibrium

**Immutability**: `model_config = ConfigDict(frozen=True)`

______________________________________________________________________

## Entity Relationships

```
┌─────────────────────┐
│  SimulationControl  │ (Protocol)
│  ───────────────────│
│  + step()           │
│  + reset()          │
│  + register_observer()   ◄── NEW
│  + unregister_observer() ◄── NEW
└─────────────────────┘
          │
          │ implements
          ▼
┌─────────────────────┐
│     Simulation      │ (Class)
│  ───────────────────│
│  _gui_callbacks     │
│  _hex_to_territory  │ (lazy index)
└─────────────────────┘
          │
          │ uses
          ▼
┌─────────────────────┐
│ ProtocolObserverAdapter │ (Class)
│  ───────────────────│    │
│  _simulation        │────┘
│  _callbacks         │
│  _lock              │
│  + notify()         │
└─────────────────────┘
          │
          │ invokes
          ▼
┌─────────────────────┐
│   ObserverCallback  │ (TypeAlias)
│  ───────────────────│
│  (tick, state) -> None
└─────────────────────┘


┌─────────────────────┐
│   SimulationState   │ (Protocol)
│  ───────────────────│
│  + get_current_tick()
│  + get_snapshot()   │
│  + get_territory_state()
│  + get_hexes_for_territory()
│  + get_node_by_spatial_index() ◄── NEW
└─────────────────────┘
          │
          │ returns
          ▼
┌─────────────────────┐
│   TerritoryState    │ (Pydantic, frozen)
│  ───────────────────│
│  territory_id       │
│  hex_claims         │
│  profit_rate        │
└─────────────────────┘
```

______________________________________________________________________

## Validation Rules

### H3 Index Validation

**Input**: `h3_index: str`

**Rules**:

1. Must be valid per `h3.is_valid_cell(h3_index)` (structural validity)
1. Format: 15-character lowercase hexadecimal (project standard: resolution 5)

**Error**: `ValueError` with descriptive message

### Callback Registration

**Input**: `callback: ObserverCallback`

**Rules**:

1. Callback must be callable
1. Duplicate registration is idempotent (no error, single invocation)
1. Unregistration of unknown callback is no-op (no error)

______________________________________________________________________

## State Transitions

### Hex Index Cache

```
┌─────────────┐   step()    ┌─────────────┐
│ Cache Valid │ ──────────► │Cache Invalid│
│ (dict)      │             │ (None)      │
└─────────────┘             └─────────────┘
       ▲                           │
       │    get_node_by_spatial_   │
       │    index() [first call]   │
       └───────────────────────────┘
```

**Invariant**: Cache is always invalidated at end of `step()` to ensure consistency.
