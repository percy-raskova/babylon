# Implementation Plan: ADR Bundle 1 — structural prep for Spec 057

**Branch**: `058-adr-bundle-1-pre-spec-057` | **Date**: 2026-05-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/058-adr-bundle-1-pre-spec-057/spec.md`

## Summary

Bundle 1 is a five-part pure structural refactor that lands the architectural changes ADR-001, ADR-002, ADR-006.3, and ADR-006.5 — and the ADR-001 OODA dedup — in the order that minimizes inter-commit conflict. It removes the four pre-existing rough surfaces that Spec 057 (Leontief Imperial Rent Integration) would otherwise have to refactor around: (1) the 4168-LOC `defines.py` monolith, (2) the 1298-LOC `enums.py` monolith with 45 enum types, (3) the 1705-LOC `tick/system.py` god-class with 33 methods including the spec-057-stub `_compute_imperial_rent`, and (4) the untyped runtime-reparsed BEA-to-Department TOML.

**Technical approach**: Mechanical splits using Python's `__init__.py` re-export idiom (no behavior changes); a new `core/protocol_kit.py` module providing `DataSource`, `CachedSource[T]` (LRU + `NoDataSentinel`-aware, with per-source `cache_negative_results` opt-out per Clarifications 2026-05-08), and `SourceRegistry` (type-keyed registry replacing the 4 `create_*_services()` factories); a god-class decomposition of `tick/system.py` into a ≤200-LOC `TickDynamicsSystem` facade plus 6–8 focused sub-modules; and a frozen `BEAMappings` Pydantic model loaded once at import time. Backward-compat is internal-first (no external downstream consumers per Q2 clarification): every new `__init__.py` declares an explicit `__all__`, all flat re-exports continue to resolve, pickle qualname stability is explicitly *not* preserved.

## Technical Context

**Language/Version**: Python 3.12+ (project standard)
**Primary Dependencies** (no new dependencies introduced by this bundle):
- `pydantic` 2.x (frozen models, `Literal`, `Field(ge/le)` for `BEAMappings`)
- `tomllib` (stdlib, used by `economics/tensor_hierarchy/mappings/__init__.py`)
- `networkx` 3.x (already in `tick/system.py`)
- `typing.Protocol` + `runtime_checkable` (stdlib, used by `protocol_kit.py`)
**Storage**: N/A — this is a refactor; no schema changes, no new persistence
**Testing**:
- `pytest` 8.x with the existing markers (`@pytest.mark.unit`, `@pytest.mark.integration`)
- `mise run test:unit` + `mise run test:int` is the regression net (current baseline: 8988 passed / 186 skipped / 1 xfailed / 0 failures / 0 errors on `dev` after `fix/dev-test-debt` merge)
- New tests added: `tests/unit/test_public_import_surface.py` (FR-001, FR-002), `tests/unit/core/test_protocol_kit.py` (FR-004, FR-005), `tests/integration/economics/tick/test_facade_behavioral_fence.py` (FR-007), `tests/unit/economics/tensor_hierarchy/test_bea_mappings.py` (FR-009)
**Target Platform**: Linux dev (Debian 13) + CI (whatever the project's CI runs); no platform-specific code
**Project Type**: Single Python project with monorepo layout (`src/babylon/...`, `tests/...`, `specs/...`); Bundle 1 touches only the `src/` and `tests/` halves
**Performance Goals**: SC-001 — same `mise run test:unit` + `mise run test:int` wall-clock-time within ±10% (no perf regressions from the refactor); no perf benchmarks introduced (per "Out of Scope" in spec)
**Constraints**:
- 600-LOC cap on every file in the new `enums/` and `defines/` packages (SC-002)
- 400-LOC cap on every file in the new `tick/system/` package (SC-002)
- 200-LOC cap on `TickDynamicsSystem` facade (FR-007, SC-002)
- 150-LOC cap on `economics/factory.py` post-migration (SC-004)
- Behavioral fence on `tick/system/`: identical return-type classes, exception class hierarchies, event-bus emission ordering (FR-007 per Q3 clarification)
- Cache-by-default with per-source opt-out for `CachedSource[T]` (FR-004 per Q4 clarification)
- Internal-first backward-compat: flat re-exports + `__all__` discipline; no pickle qualname stability (FR-001/FR-002 per Q2 clarification)
**Scale/Scope**:
- 5 user stories, 12 functional requirements, 9 success criteria
- 7 conventional commits expected (one per acceptance scenario or rollout step)
- Touches ~30 source files (10 deletions of monoliths replaced by ~25 sub-modules; ~10 `Default*` class migrations; ~6 sub-module extractions for `tick/system`; 4 callsite updates for OODA dedup; 2 file edits for BEA mappings); ~4 new test files added

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Bundle 1 is a structural refactor that touches **configuration data, type vocabulary, and a god-class decomposition** — it does not introduce new theory, new formulas, new data sources, or new mechanics. The Constitution Check focuses on whether the refactor preserves the principles that govern the affected files.

### Pre-Phase-0 Gate Evaluation

**P0 (Never Drop) — relevance to Bundle 1:**

| Principle | Relevance | Compliance |
|-----------|-----------|------------|
| I.19 Dialectic Primitive | None — bundle does not touch `models/dialectic.py` or any pole/morphism code | ✅ pass (untouched) |
| I.20 Spatial Substrate | None — bundle does not touch `engine/systems/territory.py` or H3 grid code | ✅ pass (untouched) |
| II.9 Morphism Dyadic | None — bundle does not touch the morphism graph layer | ✅ pass (untouched) |
| **III.7 Determinism Hash** | **Affected** — the `tick/system/` decomposition must preserve the deterministic-hash output of every tick | ✅ pass: FR-007's behavioral fence (per Q3 clarification) explicitly preserves return-type classes, exception classes, and event-bus emission *order*. Tick-determinism is a strict consequence of these three preservation guarantees. The behavioral-snapshot test at `tests/integration/economics/tick/test_facade_behavioral_fence.py` is the regression net. |
| III.8 Aleksandrov Test | None — bundle does not introduce new formalism, operators, or constructs | ✅ pass (untouched) |
| V Verb Atomicity | None — bundle does not touch verb implementations | ✅ pass (untouched) |

**P1 (Load-Bearing) — relevance to Bundle 1:**

| Principle | Relevance | Compliance |
|-----------|-----------|------------|
| **II.6 State is Data, Engine is Transformation** | **Affected** — `defines.py` is configuration data; `enums.py` is type vocabulary; `tick/system.py` is engine | ✅ pass: refactor preserves the Data/Engine boundary. `defines/` and `enums/` packages stay pure-data (Pydantic models + Enum subclasses, no methods that mutate WorldState). `TickDynamicsSystem` facade stays pure-transformation (`step(world, services, context) → new_world` shape preserved). |
| **II.11 Subsystem Table Ownership** | **Affected** — `economics/factory.py` and `tick/system.py` mediate cross-subsystem reads | ✅ pass: refactor does not introduce new cross-subsystem reads. `SourceRegistry.builtin_economics()` registers sources by Protocol type — exactly the same wiring that the existing `create_*_services()` functions perform, just collapsed into one entry point. The `tick/system/` decomposition keeps every cross-subsystem read at its current location (national → county → tensor lookups stay in the sub-module that owns the responsibility, e.g., `tick/system/county_distribution.py`). |
| **III.1 No Magic Constants** | **Affected** — `defines.py` IS the no-magic-constants apparatus | ✅ pass — strengthens compliance: the split makes per-category traceability easier (`from babylon.config.defines.economy import EconomyDefines` reads only the relevant category file); explicit `__all__` declarations (per Q2) catch accidental constant leakage at lint time. |
| **III.4 Data Catalog (Fixture vs Runtime)** | **Affected for US4** — `BEAMappings` is loaded from a fixture TOML at import time | ✅ pass — strengthens compliance: III.4.2 mandates fixtures be "versioned, hashed, and stored in the repository". Typing the fixture loader as `BEAMappings.model_validate(tomllib.loads(_path.read_text()))` at import time provides a fail-loud check that the fixture is well-formed. The TOML file itself is unchanged — only the loader is typed. |

**P2 (Elaboration) — selectively relevant:**
- VIII Anti-Patterns: refactor does not introduce any of the 10 listed anti-patterns
- VI.3 Flag Scope Creep: bundle is *narrowly* scoped — defers Bundle 3 items (ADR-003, ADR-004, ADR-005, ADR-006.1/6.2/6.4/6.6) explicitly. This *prevents* scope creep, doesn't cause it.

**Pre-Phase-0 verdict**: ✅ **PASS — no constitution violations identified.** Refactor preserves all P0 and relevant P1 principles. No new abstractions introduced (the `SourceRegistry` is a thin replacement for an existing pattern, not a new primitive). The behavioral fence on `tick/system/` (Q3) is the load-bearing safety net for III.7 (Determinism Hash).

### Post-Phase-1 Re-check

Performed against the generated `data-model.md`, `contracts/*.md`, and `quickstart.md`. All checks ✅ pass.

| Check | Verdict |
|-------|---------|
| **No `data-model.md` entity introduces a new mechanic outside the ADR scope** | ✅ pass. The 6 entities (`DepartmentMapping`, `BEAMappings`, `DataSource`, `CachedSource[T]`, `SourceRegistry`, `BEA_TO_DEPARTMENT` constant) are all *plumbing* types: a typed loader, a marker Protocol, a cache mixin, a DI registry, a constant. None introduces a new Marxian primitive (no new pole types, no new morphism relations, no new transport edge types per Constitution II.13, no new contradiction characters). The `_compute_membership_overlap` function move is mechanical. |
| **No `contracts/` interface lifts a hidden pole/morphism into the public surface** | ✅ pass. `protocol_kit.md` and `source_registry.md` describe a generic DI mechanism — they do NOT reference dialectics, morphisms, hyperedges, contradictions, or any other Constitutional primitive. `bea_mappings.md` describes a typed configuration loader; "Department I/II/III" are existing Marxian primitives from Constitution I.5 (Department III is already a constitutional commitment), not newly lifted. |
| **No `quickstart.md` instruction violates the Data/Engine boundary** | ✅ pass. The verification recipes invoke the existing test suite, run lint, run mypy, and check file LOC. None modifies the engine's tick computation; none reads from the database during a tick; none creates persistent state that would violate II.6 (State is Data, Engine is Transformation) or II.11 (Subsystem Table Ownership). The "Spec 057 forward-compat sanity check" (last section) authors a *smoke test* file in `/tmp/` — pure throwaway code, not committed. |
| **Behavioral fence preserves III.7 Determinism Hash** | ✅ pass — re-verified. The `tick/system/` decomposition's behavioral fence (FR-007 per Q3) explicitly preserves return-type classes, exception class hierarchies, and event-bus emission ordering. These are the three inputs to the deterministic-hash function (the hash is computed over post-tick `WorldState` + emitted events). The new behavioral-snapshot test at `tests/integration/economics/tick/test_facade_behavioral_fence.py` makes this checkable per-commit. |
| **Internal-first backward-compat does not violate II.11 Subsystem Table Ownership** | ✅ pass. The `__all__` discipline added by FR-001/FR-002 (per Q2) is a public-surface declaration on the `enums/` and `defines/` packages; it does NOT touch persistence tables. Spec 058 does not introduce or modify any database table. |

**Post-Phase-1 verdict**: ✅ **PASS — no constitution violations introduced by Phase 1 design.** The bundle remains a pure structural refactor; no new mechanics, no new theory, no new persistence, no boundary violations. Ready for `/speckit.tasks`.

## Project Structure

### Documentation (this feature)

```text
specs/058-adr-bundle-1-pre-spec-057/
├── plan.md              # This file
├── research.md          # Phase 0 output — ADR-to-FR cross-walk, code surveys, ordering rationale
├── data-model.md        # Phase 1 output — entity definitions for the 4 new types
├── quickstart.md        # Phase 1 output — how a contributor verifies the bundle locally
├── contracts/           # Phase 1 output — DataSource / CachedSource / SourceRegistry / BEAMappings
│   ├── protocol_kit.md
│   ├── source_registry.md
│   └── bea_mappings.md
├── checklists/
│   └── requirements.md  # Spec quality (already complete from /speckit.specify)
├── spec.md              # Feature specification
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

Bundle 1 touches the following directories. Files marked **NEW** are introduced by this bundle; files marked **REPLACED** become package directories with `__init__.py` re-exports; files marked **EDITED** receive surgical changes; files marked **DELETED** are removed (their contents moved into a package).

```text
src/babylon/
├── core/
│   └── protocol_kit.py             # NEW (FR-004) — DataSource, CachedSource[T], SourceRegistry
├── models/
│   ├── enums.py                    # DELETED (FR-001)
│   └── enums/                      # NEW (FR-001) — package replacing the monolith
│       ├── __init__.py             # NEW — re-exports + explicit __all__ (per Q2 clarification)
│       └── *.py                    # 7-9 sub-module files chosen by import-graph clustering (per Q1 clarification)
├── config/
│   ├── defines.py                  # DELETED (FR-002)
│   └── defines/                    # NEW (FR-002) — package replacing the monolith
│       ├── __init__.py             # NEW — GameDefines facade + re-exports + __all__
│       ├── _assembler.py           # NEW — composition / pyproject.toml [tool.babylon] loading
│       └── *.py                    # 7-10 sub-module files chosen by import-graph clustering
├── ooda/
│   ├── _helpers.py                 # NEW (FR-003) — canonical home for _compute_membership_overlap
│   ├── action_costs.py             # EDITED — import from ._helpers, drop local definition
│   └── action_effects.py           # EDITED — import from ._helpers, drop local definition
├── economics/
│   ├── factory.py                  # EDITED (FR-006) — shrink from 662 to <150 LOC; create_*_services() become 3-line shims
│   ├── department_mapper.py        # EDITED (FR-009) — consume typed BEAMappings instead of reparsing TOML
│   ├── melt/                       # 6 Default* classes migrate to CachedSource[T] (FR-005)
│   ├── gamma/                      # 4 Default* classes migrate to CachedSource[T] (FR-005)
│   ├── tensor_hierarchy/
│   │   └── mappings/
│   │       ├── _models.py          # NEW (FR-009) — DepartmentMapping, BEAMappings (frozen Pydantic)
│   │       ├── __init__.py         # NEW — module-level BEA_TO_DEPARTMENT loaded at import time
│   │       └── bea_to_department.toml  # UNCHANGED
│   └── tick/
│       ├── system.py               # DELETED (FR-007)
│       └── system/                 # NEW (FR-007) — package replacing the god-class
│           ├── __init__.py         # NEW — TickDynamicsSystem facade (≤200 LOC per SC-002)
│           ├── initialization.py   # NEW — _determine_year, _get_territory_fips, _bootstrap_county_states
│           ├── national_parameters.py  # NEW — _compute_national_params, _update_coefficients
│           ├── county_distribution.py  # NEW — _compute_county_states, _derive_precarity, _write_hex_substrate
│           ├── imperial_rent.py    # NEW — _compute_imperial_rent stub (preserves spec-057 quarantine)
│           ├── crisis.py           # NEW — _check_crisis_triggers, _emit_crisis_event, _check_dispossession_cascade, _get_profit_rate
│           ├── volume_layers.py    # NEW — _compute_vol1_layer, _compute_circulation_layer, _compute_financial_layer + their county/national subhelpers
│           ├── tensor_helpers.py   # NEW — _get_best_tensor_year, _get_county_profit_rate, _get_county_surplus
│           ├── bifurcation.py      # NEW — _compute_bifurcation_risk, _emit_bifurcation_event
│           └── transitions.py      # NEW — _simulate_transitions, _validate_distributions, _compute_tick_summary

tests/
├── unit/
│   ├── test_public_import_surface.py           # NEW (SC-006) — asserts every symbol in new __all__ resolves
│   ├── core/
│   │   └── test_protocol_kit.py                # NEW (FR-004 acceptance) — DataSource, CachedSource[T], SourceRegistry contracts
│   └── economics/
│       └── tensor_hierarchy/
│           └── test_bea_mappings.py            # NEW (FR-009 acceptance) — BEAMappings validation: production TOML + malformed fixtures
└── integration/
    └── economics/
        └── tick/
            └── test_facade_behavioral_fence.py # NEW (FR-007 per Q3) — frozen-seed tick + WorldState diff + event-bus history diff
```

**Structure Decision**: Single-project monorepo (already in place). No new top-level directories; the bundle adds one new sub-package (`core/`) and converts three existing single-file modules (`enums.py`, `defines.py`, `tick/system.py`) into packages with the same public import paths.

## Complexity Tracking

> No Constitution Check violations identified — Complexity Tracking section not required.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)* | — | — |

## Phase 0 Output

See [`research.md`](research.md). Resolves the planner-determined questions:

- **R1**: Empirical validation of FR-011's bundle ordering (US5 → US3 → US1 → US2 → US4) against the actual import graph
- **R2**: Import-graph clustering algorithm choice for `enums.py` and `defines.py` per Q1
- **R3**: MRO inspection of the 10 `melt/` + `gamma/` `Default*` classes for `CachedSource[T]` compatibility per the spec's Risks section
- **R4**: Method-cluster mapping for `tick/system.py`'s 33 methods to the 8 proposed sub-modules, with per-cluster LOC estimates
- **R5**: Spec discrepancy reconciliation (spec previously said 25 enums and 7 `create_*_services()`; actuals are 45 enums and 4 `create_*` + 3 `load_*` helpers — the spec has since been corrected per the 2026-05-08 `/speckit.analyze` remediation pass; R5 retained as historical reference for the Phase 0 work)

## Phase 1 Outputs

- [`data-model.md`](data-model.md): Frozen-Pydantic shapes for `BEAMappings`, `DepartmentMapping`; type definitions for `DataSource` (Protocol), `CachedSource[T]` (Generic ABC), `SourceRegistry` (concrete class)
- [`contracts/protocol_kit.md`](contracts/protocol_kit.md): Public surface of `DataSource`, `CachedSource[T]`, with semantic guarantees (cache key derivation, `cache_negative_results` opt-out, `invalidate(key)` and `clear()` methods)
- [`contracts/source_registry.md`](contracts/source_registry.md): Public surface of `SourceRegistry`, including `register`, `get`, `builtin_economics`, and `variant="test"` substitution semantics
- [`contracts/bea_mappings.md`](contracts/bea_mappings.md): Public surface of `BEAMappings` and its loader, including the validation policy for malformed TOML
- [`quickstart.md`](quickstart.md): Local workflow for verifying the bundle (run `mise run check`, run the new behavioral-fence test, verify `git grep` byte-equality on flat-import lines)
