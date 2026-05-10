# Implementation Plan: ADR Bundle 2 — post-Spec-057 architectural cleanup

**Branch**: `059-adr-bundle-2-post-spec-057` | **Date**: 2026-05-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/059-adr-bundle-2-post-spec-057/spec.md`

## Summary

Bundle 2 finishes the architectural cleanup pass that ADRs 001–006 collectively
describe. With Bundle 1 (Spec 058) and Spec 057 already merged into this
branch, four remaining ADRs land:

- **ADR-003** lifts `engine/systems/protocol.py:System` Protocol into a
  `SystemBase` ABC with shared `_read`/`_write`/`_publish` helpers and migrates
  the **22** existing System implementations (research.md D1: not 23 as ADR-003
  asserts).
- **ADR-004** replaces the implicit `event_type`-string dispatch in
  `deserialize_event` with a Pydantic 2 discriminated `TickEvent` union over
  **19 leaf variants** (research.md D2: not 22), splits `models/events.py` into
  a package, and threads `assert_never` exhaustiveness into observers
  (research.md D7).
- **ADR-005** decomposes the two remaining god-classes,
  `persistence/postgres_runtime.py` (2094 LOC) and `engine/simulation.py`
  (1048 LOC), into facade-plus-sub-component packages, each sub-component
  ≤400 LOC, each facade ≤200 LOC.
- **ADR-006** items 6.1, 6.2, 6.4, and 6.6 land the remaining cleanup:
  Scenario ABC migrating **6 builders** (research.md D3: not 9), package
  splits for `circulation/types.py` and `edge_transition.py`, and the
  graph-orphan vs runtime-unused schema audit (research.md D6).

ADR-006 items 6.3 (decompose `economics/tick/system.py`) and 6.5 (type the
BEA→Department mapping) shipped in Bundle 1 and are out of Bundle 2 scope
(research.md D4).

The technical approach is composition-over-monolith for ADR-005, ABC + dual
`runtime_checkable Protocol` coexistence for ADR-003, Pydantic 2 discriminated
union for ADR-004, and `__init_subclass__` registry for ADR-006.1
(research.md P1–P4).

## Technical Context

**Language/Version**: Python 3.12+ (existing project standard)
**Primary Dependencies**: Pydantic 2.x (frozen models, discriminated unions),
NetworkX 3.x (`GraphProtocol` / `nx.DiGraph`), psycopg 3.x +
psycopg_pool (postgres_runtime), SQLAlchemy 2.x (existing ORM),
`abc.ABC` + `typing.Protocol`/`runtime_checkable` (stdlib).
**Storage**: PostgreSQL 16+ for runtime state (unchanged); SQLite for
reference data (unchanged); no schema changes.
**Testing**: pytest 8.x, mypy `--strict` on ABC migration + observer
exhaustiveness, `mise run test:unit`/`test:int` for fast/integration gates,
`mise run sim:trace` for byte-equality (contracts/byte-equality.md).
**Target Platform**: Linux server (existing project target).
**Project Type**: refactor of an existing single-project Python codebase (no
new modules; new package shapes for existing files).
**Performance Goals**: preserve current per-tick wall time. ADR-005's
composition adds one method dispatch per IO call (negligible at simulation
tick frequency, ≪ kHz, per ADR-005 Consequences).
**Constraints**:
- No file in any new sub-package may exceed 400 LOC; facades ≤200 LOC; events
  sub-files ≤300 LOC (FR-001/002/007/013/014, SC-002).
- Public import paths preserved byte-for-byte (FR-003;
  contracts/import-equivalence.md).
- `sim:trace 200` CSV byte-identical against `pre-bundle-2-baseline` for the
  default `imperial_circuit` scenario (SC-007;
  contracts/byte-equality.md B1).
- Test tally preserved at every commit boundary (FR-016, SC-001).
- `mise run check` passes with zero new findings (SC-009).
**Scale/Scope**: 4 ADRs, ~11 days nominal effort, ~22 source files migrated
(SystemBase) + 6 packages created (5 splits + 1 Scenario ABC) + 8 schemas
audited.

No NEEDS CLARIFICATION items remain after Phase 0 (research.md resolves all
drift, ordering, and orphan-schema disambiguation questions).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The Babylon Constitution (v2.6.1) governs theoretical primitives, architecture
principles, methodological constraints, and governance. Bundle 2 is a
structural refactor; it modifies no theoretical primitive. Each gate below is
evaluated against `.specify/memory/constitution.md`.

### P0 (Never Drop) — gates

| Principle | Affected? | Justification |
|---|---|---|
| **I.19 Dialectic Primitive** | No | Refactor preserves `Dialectic`/pole types verbatim; no changes to `models/dialectic.py` or its consumers. |
| **I.20 Spatial Substrate** | No | H3 grid and federal county data untouched. The PostgreSQL spatial schema (`postgres_runtime/spatial_io.py` after decomposition) is structurally identical to the pre-Bundle-2 layout. |
| **II.9 Morphism Dyadic** | No | `morphism` types and dyadic constraints untouched. |
| **III.7 Determinism Hash** | **Tested** | The byte-equality contract (contracts/byte-equality.md B1) is the operationalization of III.7 for this refactor: identical inputs MUST produce identical outputs. The decomposition's facade composition does not introduce non-determinism (no new random sources, no new clock reads). |
| **III.8 Aleksandrov Test** | No | No new operators or formal constructs are introduced. The ABC, the discriminated union, and the facade pattern are scaffolding choices, not formalisms. |
| **V Verb Atomicity** | No | Action vocabulary untouched. |

**Gate verdict**: PASS. No P0 principle is at risk; III.7 is actively
exercised by the byte-equality contract.

### P1 (Load-Bearing) — gates

| Principle | Affected? | Justification |
|---|---|---|
| **I.16 Organization vs Institution** | No | The Systems that act on Organizations (e.g., OODASystem, StruggleSystem) inherit from `SystemBase` after migration; their behavior and invariants are preserved by the SystemBase contract (`_read`/`_write`/`_publish`). |
| **II.6 State is Data, Engine is Transformation** | **Reinforced** | `SystemBase._read`/`_write` make the read-modify-write pattern explicit at the type level, surfacing the in-place graph mutation that II.6 sanctions. The Pydantic discriminated union strengthens the "State is Data" half: events become validated data, not loosely-typed dicts. |
| **II.11 Subsystem Table Ownership** | **Examined** | The PostgresRuntime decomposition splits per-table IO across sub-modules (`tick_io.py`, `archival_io.py`, `spatial_io.py`, `community_io.py`, `trace_io.py`). Per-subsystem table ownership is preserved: `community_io.py` owns the XGI hyperedge tables; `spatial_io.py` owns the PostGIS hex tables; etc. The facade composes these without leaking cross-subsystem reads. |
| **III.1 No Magic Constants** | No | Refactor introduces no new constants. The 19 `kind: Literal[...]` event values are protocol identifiers, not magic numbers; each is documented in data-model.md §1.2. |
| **III.4 Data Catalog** | No | No data sources added or moved. |

**Gate verdict**: PASS. II.6 and II.11 are reinforced by the refactor.

### P2 (Elaboration) — note

No P2 principle is in scope for this refactor. Per III.9, dropping P2 from
session context is permitted; the AI implementer may operate from P0 + the
five P1 principles above.

### Methodological gates

- **III.2 Falsifiability**: The acceptance criteria (SC-001 through SC-010)
  are concrete, measurable, and falsifiable. SC-007's byte-equality is the
  strongest possible falsifier for this kind of refactor.
- **III.7 Determinism Hash**: As above — operationalized by SC-007.
- **VI.3 Flag Scope Creep**: The Out-of-Scope section in spec.md is
  generous and explicit; no scope creep risk identified during planning.

### Re-check after Phase 1

Phase 1 produced data-model.md, three contract files, and quickstart.md.
None introduces a new theoretical primitive, no new data source, no new
external dependency. Re-evaluating the same gates above produces the same
PASS verdicts.

**Final Constitution Check verdict**: PASS — no Complexity Tracking entries
required.

## Project Structure

### Documentation (this feature)

```text
specs/059-adr-bundle-2-post-spec-057/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 — drift resolution, ordering, patterns
├── data-model.md        # Phase 1 — new abstractions + package shapes
├── quickstart.md        # Phase 1 — pre-flight + per-ADR + final gates
├── contracts/           # Phase 1
│   ├── import-equivalence.md     # C1–C7: every public import path preserved
│   ├── protocol-satisfaction.md  # P1–P6: isinstance / issubclass checks
│   └── byte-equality.md          # B1–B4: sim:trace + event roundtrip
├── checklists/
│   └── requirements.md           # Spec quality checklist (pre-existing)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

Bundle 2 introduces six new package directories and one new ABC module under
the existing `src/babylon/` tree. No top-level layout changes.

```text
src/babylon/
├── persistence/
│   ├── postgres_runtime/             # NEW package (replaces postgres_runtime.py)
│   │   ├── __init__.py               # PostgresRuntime facade (~150 LOC)
│   │   ├── _pool.py
│   │   ├── tick_io.py
│   │   ├── archival_io.py            # Phase 8 stub preserved
│   │   ├── spatial_io.py
│   │   ├── community_io.py
│   │   └── trace_io.py
│   ├── pgvector_store.py             # UNCHANGED (already in own file)
│   └── protocols.py                  # UNCHANGED (Protocol definitions)
├── engine/
│   ├── simulation/                   # NEW package (replaces simulation.py)
│   │   ├── __init__.py               # Simulation facade (~150 LOC)
│   │   ├── orchestrator.py
│   │   ├── observer_dispatch.py
│   │   ├── lifecycle.py
│   │   └── error_recovery.py
│   ├── scenarios/                    # NEW package (replaces scenarios.py)
│   │   ├── __init__.py               # registry + 6 backward-compat shims
│   │   ├── base.py                   # Scenario ABC + __init_subclass__ registry
│   │   ├── two_node.py
│   │   ├── high_tension.py
│   │   ├── labor_aristocracy.py
│   │   ├── imperial_circuit.py
│   │   ├── us.py
│   │   └── wayne_county.py
│   ├── scenarios_wayne_county.py     # SHIM (1 line: re-export from scenarios.wayne_county)
│   ├── observers/                    # MUTATED (assert_never threading per FR-008)
│   │   ├── causal.py
│   │   ├── economic.py
│   │   ├── endgame_detector.py
│   │   ├── metrics.py
│   │   ├── persistence_observer.py
│   │   ├── schema_validator.py
│   │   └── session_recorder.py
│   └── systems/
│       ├── base.py                   # NEW — SystemBase ABC + System Protocol re-export
│       ├── protocol.py               # MUTATED — re-export from base.py (or removed)
│       ├── edge_transition/          # NEW package (replaces edge_transition.py)
│       │   ├── __init__.py
│       │   ├── predicates.py
│       │   └── system.py             # EdgeTransitionSystem(SystemBase)
│       └── *.py                      # 21 Systems migrated to inherit SystemBase
├── economics/
│   ├── circulation/
│   │   └── types/                    # NEW package (replaces types.py)
│   │       ├── __init__.py
│   │       ├── flow.py
│   │       ├── fixed_capital.py
│   │       ├── crisis.py
│   │       └── _enums.py
│   └── tick/system/                  # UNCHANGED (Bundle 1 deliverable; TickDynamicsSystem inherits SystemBase per ADR-003)
└── models/
    └── events/                       # NEW package (replaces events.py)
        ├── __init__.py               # Re-exports + TickEvent assembly
        ├── _base.py                  # SimulationEvent root + intermediate bases
        ├── economic.py
        ├── consciousness.py
        ├── struggle.py
        ├── contradiction.py
        ├── topology.py
        └── system.py

tests/
├── contract/
│   ├── persistence/                  # MUTATED (existing tests run unchanged; test_systembase_inheritance new)
│   └── engine/                       # NEW (test_simulation_facade_surface, test_systembase_inheritance)
├── integration/
│   ├── test_scenario_*.py            # MUTATED (verify Scenario shim equivalence)
│   └── test_worldstate_event_roundtrip.py   # MUTATED (covers ≥5 leaf variants)
├── unit/
│   ├── engine/
│   │   ├── observers/                # MUTATED (FR-008 assert_never)
│   │   ├── scenarios/                # NEW directory + tests
│   │   └── systems/                  # MUTATED (existing tests run unchanged)
│   ├── models/
│   │   ├── test_tick_event_discriminator.py   # NEW
│   │   └── test_tick_event_roundtrip.py       # NEW (parametrized over 19 leaves)
│   └── persistence/                  # MUTATED (existing tests run unchanged)
└── …                                 # other test directories untouched

ai-docs/
├── decisions.yaml                    # MUTATED (8 orphan-schema audit entries per FR-015)
├── state.yaml                        # MUTATED (test counts, sprint status post-bundle)
└── …
```

**Structure Decision**: Bundle 2 follows the package-shape pattern established
by Bundle 1 (ADR-001) for `enums/` and `defines/`: an existing oversized file
becomes a directory of the same base name, with a re-exporting `__init__.py`
preserving every existing import path. Six packages follow this shape
(`postgres_runtime/`, `simulation/`, `scenarios/`, `events/`,
`circulation/types/`, `edge_transition/`); one new ABC module (`base.py`)
adds the `SystemBase` scaffolding consumed by the migrated Systems.

## Complexity Tracking

> Constitution Check returned PASS with no violations. No entries required.

The following design choices were **considered and accepted** without flagging
as complexity concerns; they are documented here for transparency rather than
as exception requests:

| Choice | Tradeoff | Why accepted |
|---|---|---|
| Dual `SystemBase` ABC + `runtime_checkable Protocol System` (P2) | Two ways to be a System | PEP 544 explicitly supports this dual-export; FR-010 requires it (mocks). |
| Pydantic discriminator over 19 leaves with 5 intermediate-base classes preserved (D2) | Could collapse intermediates into leaves | Intermediates carry shared fields; flattening is a larger refactor than ADR-004 envisions. |
| `__init_subclass__` registry for `Scenario` (P4) | "Mildly magic" per ADR-006.1 | Containment is high (registry is private to `scenarios/base.py`); fallback to explicit `register_scenario` decorator is documented. |
| Facade composition adds one extra method dispatch per IO call (P3) | Tiny perf cost | ≪ kHz simulation tick frequency makes the cost negligible; verified by ADR-005 Consequences. |
