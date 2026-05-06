# ADR-004: Discriminated `TickEvent` union replaces `deserialize_event`

**Status**: Proposed
**Date**: 2026-05-05
**Phase**: 4 of 6
**Tier**: T2
**Estimated effort**: 2 days
**Risk**: Medium

## Context

`models/events.py` is **1011 lines** containing 22 Event subclasses plus a hand-rolled `deserialize_event` switch. CLAUDE.md "Common Gotchas" already warns about `WorldState.events` being per-tick (not cumulative), and about `mypy` missing Pydantic attribute errors. Both gotchas converge on the events module:

1. The discriminator dispatch is implicit in `deserialize_event`, so static analysis can't catch a missing case.
1. `Event` subclasses lack a `kind` field that Pydantic could use for automatic disambiguation.
1. Per CLAUDE.md gotcha: `snapshot.phase  # AttributeError: 'TopologySnapshot' has no attribute 'phase'` — same class of bug applies to events when serialized through `from_graph()`.

The cleanest path forward in Pydantic 2 is a **discriminated union** with `Annotated[..., Field(discriminator='kind')]`. This is the canonical Pydantic 2 idiom for sum types, and it gets Pydantic to do all the dispatch work — including validating that every variant has a unique `kind` literal at class-definition time.

## Decision

Convert the 22-variant `Event` hierarchy into a Pydantic discriminated union keyed on a `Literal[...]` `kind` field. Replace `deserialize_event` with Pydantic's built-in dispatch.

### `models/events.py` after refactor

```python
from typing import Annotated, Literal, Union
from pydantic import BaseModel, ConfigDict, Field

class _EventBase(BaseModel):
    """Common fields. Subclasses MUST set kind: Literal[...]."""
    model_config = ConfigDict(frozen=True)
    tick: int
    timestamp: str  # ISO-8601

class ImperialCollapse(_EventBase):
    kind: Literal["imperial_collapse"] = "imperial_collapse"
    cause: str

class RevolutionaryRupture(_EventBase):
    kind: Literal["revolutionary_rupture"] = "revolutionary_rupture"
    territory_id: str
    p_revolution: float

# ... 20 more variants, each with a unique kind: Literal["..."]

TickEvent = Annotated[
    Union[ImperialCollapse, RevolutionaryRupture, ...],  # all 22 variants
    Field(discriminator="kind"),
]
```

### `models/world_state.py` after refactor

```python
class WorldState(BaseModel):
    model_config = ConfigDict(frozen=True)
    events: list[TickEvent]  # Pydantic validates and dispatches automatically
    # ...
```

### `deserialize_event` becomes a one-liner shim

```python
# Kept for back-compat only — new code uses TickAdapter directly.
from pydantic import TypeAdapter
_event_adapter = TypeAdapter(TickEvent)
def deserialize_event(data: dict) -> TickEvent:
    return _event_adapter.validate_python(data)
```

### Splitting events.py at the same time

While we're touching it, split the 1011-line file into:

```
src/babylon/models/events/
├── __init__.py             # Re-exports TickEvent + every variant
├── _base.py                # _EventBase, TickEvent union assembly
├── economic.py             # imperial_collapse, dispossession, surplus_realization, ...
├── consciousness.py        # revolutionary_rupture, fascism_drift, ideology_shift, ...
├── territory.py            # eviction, heat_spike, ...
└── system.py               # tick_started, tick_completed, invariant_violation, ...
```

This is the same shape as ADR-001's enum split.

## Consequences

### Positive

- **Mypy becomes useful for events.** Adding a new variant with a new `kind` literal forces every consumer's `match` statement to handle it (or fail mypy via the `assert_never` exhaustiveness pattern).
- Pydantic does all dispatch — `deserialize_event`'s ~80 lines of switch logic disappear.
- Roundtrips through `WorldState.from_graph()` no longer need bespoke event reconstruction.
- Catches a class of runtime bugs (typos in event-kind strings, missing variants) at typecheck time.

### Negative / tradeoffs

- **Discriminator field must be a `Literal[...]`, not a free-form `str`.** Variants that historically built their `event_type` field dynamically need a hard-coded literal. Audit needed.
- The split into `events/` package follows ADR-001's pattern; minor risk of import-cycle if any consumer imports `models.events.economic` directly while `models.events.__init__` re-exports across modules. Standard cure: defer imports to `TYPE_CHECKING`.
- Existing code that constructs events via `Event(event_type="X", ...)` must change to construct the specific variant. Mostly already done — the 22 subclasses already carry intent.
- Observers using `match event:` over `Event` need a final `case _: assert_never(event)` or similar.

## Acceptance criteria

- [ ] All 22 Event subclasses carry a unique `kind: Literal["..."]` field.
- [ ] `TickEvent = Annotated[Union[...], Field(discriminator="kind")]` is defined.
- [ ] `WorldState.events: list[TickEvent]` validates correctly: passing a mismatched dict raises `ValidationError`, not silently accepts.
- [ ] `deserialize_event` either deleted (preferred) or reduced to a 3-line `TypeAdapter.validate_python` shim.
- [ ] `models/events.py` either ≤200 LOC (just `TickEvent` assembly + `_EventBase`) or split into `models/events/` package with no file >300 LOC.
- [ ] All `match event:` statements in observers and tests gain `case _: assert_never(event)` or are converted to `if isinstance(...)` chains with full coverage.
- [ ] `mise run check` passes. `mise run test:all` passes including integration tests that round-trip events through `to_graph()` / `from_graph()`.

## Rollout

1. **`refactor(models): introduce TickEvent discriminated union`**

   - Add `kind: Literal[...]` to all 22 Event subclasses.
   - Define `TickEvent` union in `events.py`.
   - Keep `deserialize_event` as a shim around `TypeAdapter`.
   - No consumer changes yet.

1. **`refactor(models): split events.py into events/ package`**

   - Mirror ADR-001 enum-split pattern.
   - Re-export everything from `events/__init__.py`.

1. **`refactor(engine): consume TickEvent union in WorldState and observers`**

   - `WorldState.events: list[TickEvent]`.
   - Update `observers/causal.py`, `observers/endgame_detector.py`, `observers/session_recorder.py`, `observers/economic.py` to use `match event:` (or isinstance chains) over the union with exhaustiveness checks.

1. **`refactor(models): remove deserialize_event`**

   - Once no caller remains, delete the shim.
   - Update `from_graph()` to use `TypeAdapter` directly.

## Test strategy

- After step 1: `pytest tests/ -k "event"` should pass unchanged (the shim preserves behavior).
- After step 2: full `mise run check`.
- After step 3: integration tests in `tests/integration/` that drive multi-tick simulations and inspect emitted events. Run `mise run test:int`.
- After step 4: `git grep deserialize_event` returns zero results.
- New unit tests in `tests/unit/models/test_events.py`:
  - Each variant validates and round-trips: `TickEvent.validate_python(variant.model_dump()) == variant`.
  - Mismatched `kind` raises `ValidationError`.
  - Variant with extra fields (forward-compat) raises `ValidationError` (default Pydantic behavior, no `extra='allow'`).
  - `assert_never` exhaustiveness compiles for the canonical observer match statement.

## References

- Knowledge graph nodes:
  - `file:src/babylon/models/events.py` (1011 LOC, 22 event subclasses)
  - `function:src/babylon/models/events.py:deserialize_event`
  - `function:src/babylon/models/world_state.py:WorldState.from_graph`
  - 7 observer files in `engine/observers/` that consume events
- Related ADRs: ADR-001 (sets the precedent for splitting barrel files; same package shape).
- CLAUDE.md sections:
  - "Common Gotchas" → WorldState.events is Per-Tick, NOT Cumulative
  - "Common Gotchas" → Mypy Misses Pydantic Attribute Errors
  - "Coding Standards" → Pydantic First
- Pydantic 2 docs: [Discriminated Unions](https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions).
