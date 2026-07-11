# ADR-003: Lift `System` Protocol into a true ABC with shared scaffolding

**Status**: Proposed
**Date**: 2026-05-05
**Phase**: 3 of 6
**Tier**: T2
**Estimated effort**: 1 day
**Risk**: Low

## Context

`engine/systems/protocol.py` currently defines a 41-line `System(Protocol)` with `name` and `step()`. There are **23 System implementations** in `engine/systems/`, all conforming to this Protocol. They duplicate scaffolding code:

- Constructor takes `GameDefines` (or a slice).
- Helpers `_get_X_from_node`, `_update_X_node` (visible at the top of `struggle.py:57-200`).
- Most call `services.formula_registry.get(...)` and `services.event_bus.publish(...)` per tick.
- All mutate `graph.nodes[node_id][key] = value` in place — the canonical "graph-mutation pattern" called out in CLAUDE.md "Common Gotchas".

The 23 Systems represent ~5300 LOC. Several (community.py 668, edge_transition.py 853, struggle.py 647, economic.py 737) have private helpers that read/write graph node attributes with subtle defensive patterns (mostly to handle the `data.get("field", 0.0)` masking problem flagged in the gotchas doc).

Protocol-based duck typing is the right tool when there's no shared behavior to lift. There's clearly shared behavior here. Lifting it to an ABC won't break the structural typing — Python's `runtime_checkable` Protocol is a superset of ABC.

## Decision

Replace the bare Protocol with an abstract base class that supplies the shared scaffolding while preserving the Protocol-style duck typing for tests and mocks.

### `engine/systems/base.py`

```python
from abc import ABC, abstractmethod
from typing import Any, ClassVar, TYPE_CHECKING
import networkx as nx

if TYPE_CHECKING:
    from babylon.config.defines import GameDefines
    from babylon.engine.context import TickContext
    from babylon.kernel.event_bus import Event
    from babylon.engine.services import ServiceContainer

class SystemBase(ABC):
    """Abstract base for all simulation Systems.

    Subclasses MUST set `name` (ClassVar) and implement `step()`.
    Helpers cover the read-modify-write pattern that all Systems need
    when mutating graph node attributes in place.
    """

    name: ClassVar[str]

    def __init__(self, defines: "GameDefines") -> None:
        self.defines = defines

    @abstractmethod
    def step(
        self,
        graph: nx.DiGraph[str],
        services: "ServiceContainer",
        context: "TickContext | dict[str, Any]",
    ) -> None:
        """Apply system logic to the world graph (in-place mutation)."""
        ...

    # --- Shared helpers ---

    def _read(self, graph: nx.DiGraph[str], node_id: str, key: str, *, required: bool = False):
        """Read a graph node attribute. Raises KeyError if required and missing.

        Use `required=True` to surface schema bugs instead of silently coercing
        to a default (cf. CLAUDE.md gotcha: 'data.get(\"s_bio\", 0.0) masks missing field bugs').
        """
        node = graph.nodes[node_id]
        if required and key not in node:
            raise KeyError(f"Required attribute '{key}' missing on node '{node_id}'")
        return node.get(key)

    def _write(self, graph: nx.DiGraph[str], node_id: str, key: str, value: Any) -> None:
        """Write a graph node attribute (in-place)."""
        graph.nodes[node_id][key] = value

    def _publish(self, services: "ServiceContainer", event: "Event") -> None:
        """Publish an event via the service container's event bus."""
        services.event_bus.publish(event)

# Keep the Protocol for structural typing (tests, mocks, runtime checks):
@runtime_checkable
class System(Protocol):
    name: str
    def step(self, graph, services, context) -> None: ...
```

### Migration shape per System

Before:

```python
class StruggleSystem:
    name = "struggle"
    def __init__(self, defines: GameDefines): self.defines = defines

    def step(self, graph, services, context):
        for node_id, data in graph.nodes(data=True):
            wealth = data.get("wealth", 0.0)  # silent default — gotcha
            # ...
            graph.nodes[node_id]["wealth"] = new_wealth
```

After:

```python
class StruggleSystem(SystemBase):
    name = "struggle"

    def step(self, graph, services, context):
        for node_id, _ in graph.nodes(data=True):
            wealth = self._read(graph, node_id, "wealth", required=True)
            # ...
            self._write(graph, node_id, "wealth", new_wealth)
```

The `runtime_checkable Protocol` stays alongside the ABC so `isinstance(obj, System)` keeps working in tests that pass mock objects.

## Consequences

### Positive

- ~20 helper-function duplications collapse into the base.
- The `_read(..., required=True)` pattern surfaces schema bugs at the read site (per CLAUDE.md gotcha).
- New Systems get a smaller surface to author (omit `__init__`, `name` becomes a class attribute).
- Test mocks still work via `Protocol` runtime check — no change in how `tests/unit/engine/systems/` exercises Systems.

### Negative / tradeoffs

- Requires touching 23 files. Mostly mechanical (replace `class FooSystem:` with `class FooSystem(SystemBase):` + drop `__init__`).
- Each migrated System loses the freedom to define a non-standard `__init__`. If any System needs extra constructor args (e.g., `EdgeTransitionSystem` with predicate compilers), keep the `__init__` and call `super().__init__(defines)` first.
- ABCs have a small import-time cost (registers metaclass machinery). Negligible at our scale.

## Acceptance criteria

- [ ] `engine/systems/base.py` defines `SystemBase` (ABC) and re-exports `System` (Protocol) for structural typing.
- [ ] `engine/systems/protocol.py` either re-exports from `base.py` or is removed; old `System` import path keeps working.
- [ ] All 23 Systems inherit from `SystemBase`.
- [ ] All 23 Systems use `self._read` / `self._write` / `self._publish` for graph mutations (no direct `graph.nodes[id][key] = ...` outside helpers).
- [ ] `mise run check` passes; the 9100+ test suite passes unchanged.
- [ ] At least 5 instances of `data.get("X", default)` masking are converted to `_read(..., required=True)` and the resulting `KeyError`s either fail loudly (revealing real bugs) or trigger explicit data fixes.

## Rollout

1. **`feat(engine): add SystemBase ABC alongside System Protocol`**

   - Add `engine/systems/base.py` with `SystemBase` and re-export `System` Protocol.
   - No changes to existing System classes yet.
   - Adds unit tests for `_read` / `_write` / `_publish`.

1. **`refactor(engine): migrate 5 small Systems to SystemBase`**

   - Pick: `metabolism.py`, `reserve_army.py`, `vitality.py`, `dispossession_events.py`, `contradiction_field.py`.
   - These are \<150 LOC each; minimal blast radius.

1. **`refactor(engine): migrate the remaining 18 Systems to SystemBase`**

   - One commit per "wave" (5–7 Systems each) to keep diffs reviewable.
   - Wave A: ideology, solidarity, survival, contradiction, lifecycle, ooda, decomposition.
   - Wave B: economic, struggle, territory, edge_transition, control_ratio, field_derivative, production.
   - Wave C: community, event_template (the two largest remaining).

1. **`refactor(engine): convert silent .get() defaults to _read(required=True) where appropriate`**

   - Code search for `data.get("` in `engine/systems/` → audit each.
   - Convert to `_read(..., required=True)` where the field is meant to always be present.
   - Leave `data.get("X", default)` only for genuinely optional fields, with a comment documenting why.

## Test strategy

- After each migration commit: `mise run test:unit` (full unit suite, ~30s).
- Before final merge: `mise run test:all` (full integration suite).
- New unit tests for `SystemBase`:
  - `_read(required=True)` raises `KeyError` for missing attribute.
  - `_read(required=False)` returns `None` for missing attribute (or default if passed).
  - `_write` mutates the graph node in place.
  - `isinstance(StubSystem(), System)` still returns `True` after migration.
- Stress: the existing `tests/unit/engine/systems/` tests should pass unchanged. If any test breaks, the bug is real (the System was relying on silent default coercion).

## References

- Knowledge graph nodes:
  - `class:src/babylon/engine/systems/protocol.py:System` (the existing Protocol)
  - 23 `class:src/babylon/engine/systems/*.py:*System` nodes (one per System)
  - `file:src/babylon/engine/systems/struggle.py` (647 LOC — example of the helper pattern)
  - `file:src/babylon/engine/systems/economic.py` (737 LOC — ImperialRentSystem)
- Related ADRs: ADR-001 (depends on `defines/` split for cleaner constructor injection), ADR-005 (System decomposition will use these helpers).
- CLAUDE.md sections:
  - "Common Gotchas" → Systems Mutate Shared Graph In-Place
  - "Common Gotchas" → Using `data.get("field", 0.0)` fallback masks missing field bugs
  - "Common Gotchas" → Dependency Injection Over Discovery
