# Research: GUI Protocol Extension

**Feature**: 006-gui-protocol-extension
**Date**: 2026-01-31
**Sources**: Context7 documentation (PyQt6, H3), existing codebase analysis

## 1. PyQt6 Thread Communication

### Problem

The GUI (PyQt6 event loop) runs in a different thread than the simulation engine. How do we safely deliver state updates from the engine thread to the GUI thread?

### Research Findings

**Qt Connection Types** (from PyQt6 documentation):

| Type                       | Behavior                                            | Thread Safety         |
| -------------------------- | --------------------------------------------------- | --------------------- |
| `AutoConnection` (default) | Automatically uses QueuedConnection if cross-thread | Safe                  |
| `QueuedConnection`         | Slot invoked in receiver's event loop               | Safe                  |
| `DirectConnection`         | Immediate invocation in signalling thread           | NOT safe cross-thread |
| `BlockingQueuedConnection` | Blocks until slot returns                           | Can deadlock          |

**Recommended Pattern**: Worker objects with `moveToThread()` and signals/slots.

```python
# Qt pattern for cross-thread communication
class Worker(QObject):
    resultReady = pyqtSignal(object)  # Signal with snapshot

    def doWork(self):
        # ... work in worker thread ...
        self.resultReady.emit(result)  # Auto-queued to receiver's thread
```

### Decision

**Use deep copy + frozen Pydantic models** (not Qt signals directly).

**Rationale**:

1. The engine is NOT a Qt application - it shouldn't depend on PyQt6
1. Frozen Pydantic models (`frozen=True`) are already thread-safe by immutability
1. The ProtocolObserverAdapter can use Qt signals internally if the GUI layer chooses
1. This keeps the protocol layer decoupled from Qt

**Implementation**:

- Engine creates immutable snapshot via `get_snapshot()` (already frozen Pydantic)
- ProtocolObserverAdapter receives snapshot, delivers to registered callbacks
- If callback is Qt slot, Qt handles thread marshalling via AutoConnection

### Alternatives Considered

| Alternative                     | Rejected Because                                           |
| ------------------------------- | ---------------------------------------------------------- |
| Require Qt signals in protocol  | Couples engine to PyQt6; breaks non-Qt consumers           |
| Shared mutable state with locks | Complex; easy to deadlock; violates immutability principle |
| Copy-on-read lazy snapshots     | More complex; no performance benefit for small state       |

______________________________________________________________________

## 2. H3 Validation

### Problem

How do we validate H3 index format before lookup? The spec requires ValueError for invalid formats.

### Research Findings

**H3 Python API** (from h3 library documentation):

```python
import h3

# Validation function
h3.is_valid_cell(h)  # Returns bool

# String format
# H3 indices are 15-character hexadecimal strings at most resolutions
# Example: "8a2a1072b59ffff" (resolution 10)
# Example: "822d57fffffffff" (resolution 2)
```

**Existing codebase pattern** (from `src/babylon/models/snapshots.py`):

```python
H3_INDEX_PATTERN = re.compile(r"^[0-9a-f]{15}$")
```

This regex expects exactly 15 lowercase hex characters, which is correct for resolution 5 (the project standard per A3).

### Decision

**Use `h3.is_valid_cell()` for validation** in addition to regex.

**Rationale**:

1. Library function validates structural correctness (not just format)
1. Handles edge cases that regex cannot (e.g., invalid resolution encoding)
1. Project already depends on `h3 ^4.2` in pyproject.toml

**Implementation**:

```python
def get_node_by_spatial_index(self, h3_index: str) -> TerritoryState | None:
    # Validate format and structure
    if not h3.is_valid_cell(h3_index):
        raise ValueError(f"Invalid H3 index: {h3_index}")

    # Lookup territory by hex claim
    ...
```

### Alternatives Considered

| Alternative                 | Rejected Because                                   |
| --------------------------- | -------------------------------------------------- |
| Regex only                  | Doesn't catch structurally invalid indices         |
| No validation (return None) | Spec requires ValueError for invalid format        |
| Custom validation           | Reinventing wheel; h3 library already handles this |

______________________________________________________________________

## 3. Existing Observer Pattern

### Problem

How does the current SimulationObserver work? How does the new callback pattern relate to it?

### Research Findings

**Current SimulationObserver** (from `src/babylon/engine/observer.py`):

```python
@runtime_checkable
class SimulationObserver(Protocol):
    @property
    def name(self) -> str: ...

    def on_simulation_start(self, initial_state: WorldState, config: SimulationConfig) -> None: ...
    def on_tick(self, previous_state: WorldState, new_state: WorldState) -> None: ...
    def on_simulation_end(self, final_state: WorldState) -> None: ...
```

**Key characteristics**:

- Full lifecycle hooks (start, tick, end)
- Receives both previous and new state for delta analysis
- Designed for AI/narrative observers (rich interface)
- Error handling: log and ignore per ADR003

**Current usage** (from `src/babylon/engine/simulation.py`):

```python
def add_observer(self, observer: SimulationObserver) -> None:
    self._observers.append(observer)

def _notify_observers_tick(self) -> None:
    for observer in self._observers:
        try:
            observer.on_tick(previous_state, new_state)
        except Exception as e:
            logger.warning("Observer %s failed: %s", observer.name, e)
```

### Decision

**Keep SimulationObserver for AI/narrative; add lightweight callback registration to SimulationControl**.

**Rationale**:

1. SimulationObserver is heavyweight (3 methods, name property, WorldState pairs)
1. GUI needs lightweight updates (just current tick and state reference)
1. Callback signature `Callable[[int, SimulationState], None]` is minimal and flexible
1. No breaking changes to existing observer infrastructure

**Relationship**:

```
SimulationObserver (existing)     ObserverCallback (new)
├── AI/Narrative consumers        ├── GUI consumers
├── Full lifecycle hooks          ├── Per-tick only
├── Previous + New WorldState     ├── Tick number + SimulationState
└── Rich interface (Protocol)     └── Simple callable
```

### Alternatives Considered

| Alternative                                 | Rejected Because                                           |
| ------------------------------------------- | ---------------------------------------------------------- |
| Extend SimulationObserver                   | Would require GUI to implement unused lifecycle methods    |
| Replace SimulationObserver                  | Breaking change; existing observers depend on it           |
| Adapter from callback to SimulationObserver | Unnecessary complexity; two patterns serve different needs |

______________________________________________________________________

## 4. Spatial Index Implementation

### Problem

How do we efficiently map H3 index → TerritoryState?

### Research Findings

**Current territory structure** (from `src/babylon/models/snapshots.py`):

```python
class TerritoryState(BaseModel):
    territory_id: str
    hex_claims: frozenset[str]  # Set of H3 indices
    ...

class SimulationSnapshot(BaseModel):
    territories: dict[str, TerritoryState]  # territory_id -> state
    hexes: dict[str, HexState]  # h3_index -> hex state
```

**Current implementation** has:

- Forward mapping: territory_id → TerritoryState (direct dict lookup)
- Forward mapping: h3_index → HexState (direct dict lookup)
- Reverse mapping: h3_index → territory_id (NOT indexed, requires scan)

### Decision

**Build reverse index lazily on first query**.

**Rationale**:

1. Most simulations won't use spatial queries (only GUI does)
1. Building index upfront wastes memory for non-GUI uses
1. Index can be cached in Simulation instance for repeated queries
1. Territories change infrequently (only on tick), so cache invalidation is simple

**Implementation**:

```python
class Simulation:
    _hex_to_territory: dict[str, str] | None = None  # Lazy cache

    def _build_hex_index(self) -> dict[str, str]:
        index = {}
        for tid, territory in self._mvp_territories.items():
            for h3_idx in territory.hex_claims:
                index[h3_idx] = tid
        return index

    def get_node_by_spatial_index(self, h3_index: str) -> TerritoryState | None:
        if not h3.is_valid_cell(h3_index):
            raise ValueError(f"Invalid H3 index: {h3_index}")

        if self._hex_to_territory is None:
            self._hex_to_territory = self._build_hex_index()

        territory_id = self._hex_to_territory.get(h3_index)
        return self._mvp_territories.get(territory_id) if territory_id else None
```

**Cache invalidation**: Clear `_hex_to_territory = None` at end of each `step()`.

### Alternatives Considered

| Alternative                               | Rejected Because                                   |
| ----------------------------------------- | -------------------------------------------------- |
| Scan all territories per query            | O(n×m) where n=territories, m=avg hex claims; slow |
| Always build index upfront                | Wastes memory for non-GUI simulations              |
| Store reverse index in SimulationSnapshot | Breaks immutability; snapshot should be minimal    |

______________________________________________________________________

## Summary

| Research Area    | Decision                                                       | Confidence |
| ---------------- | -------------------------------------------------------------- | ---------- |
| Thread Safety    | Deep copy + frozen Pydantic                                    | High       |
| H3 Validation    | `h3.is_valid_cell()`                                           | High       |
| Observer Pattern | Separate callback (lightweight) from SimulationObserver (rich) | High       |
| Spatial Index    | Lazy reverse index with per-tick invalidation                  | High       |

All research questions resolved. Ready to proceed to Phase 1 design.
