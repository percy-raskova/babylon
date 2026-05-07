# Implementation Plan: Causal/Temporal Invariants — Property-Based Tests

**Branch**: `056-causal-invariants` | **Date**: 2026-05-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/056-causal-invariants/spec.md`

## Summary

Convert four causal/temporal invariants — Material Base before Action Phase
ordering (US1), Consequences after all OODA per-organization actions
(US2), no DB I/O during the `run_tick` execution boundary (US3), and
**monotonic-idempotent** persistence per tick (US4) — into Hypothesis-driven
property tests. Each invariant becomes a single parametrized test file under
`tests/property/invariants/` that mirrors the Spec 053 / 054 / 055 harness
style: project-wide profile registration, default-deny + opt-out marker
pattern, single-source-of-truth imports from production code (the new
`MATERIAL_BASE_SYSTEMS` / `ACTION_PHASE_SYSTEMS` / `CONSEQUENCE_SYSTEMS`
constants in `simulation_engine.py`, the existing `ServiceContainer`
attribute surface for DB-I/O detection, the `RuntimePersistence` protocol
for the monotonic-idempotent check). The harness adds three instrumentation
helpers: `SystemCallSpy` (US1 + US2 trace recorder),
`OrganizationActionSpy` (US2 per-org trace recorder, patches the new
`OODASystem._resolve_for_organization` helper), and a
`no_db_io_during_tick(engine)` context manager (US3 patched-services scope).
A `causal_harness.py` module bundles shared event dataclasses but no
runner class is added (the original `CausalInvariantHarness` was dropped
post-analyze per finding C1; tests use spy + context-manager primitives
directly). Production-side changes (per the 2026-05-07 post-verification
F6 + F7 decisions): (a) add the three System-classification constants in
`simulation_engine.py` AND **reorder `_DEFAULT_SYSTEMS`** so `OODASystem`
runs at position 14 (between `MetabolismSystem` and `SurvivalSystem`),
matching ADR032's documented partition; (b) add `MonotonicityViolationError`
+ refine the `RuntimePersistence.persist_tick` docstring to declare
**monotonic-idempotent** semantics (same payload succeeds, different
payload raises) — preserves existing UPSERT-retry callers
(`persistence_observer.py:146`, `session_recorder.py:168`) while blocking
silent rewrite; (c) extract `OODASystem._resolve_for_organization` helper
method (behavior-preserving refactor) so `unittest.mock.patch.object` has a
clean named seam for the per-organization spy.

## Technical Context

**Language/Version**: Python 3.12+ (existing project standard)
**Primary Dependencies**: Hypothesis ^6.149.0 (in `[tool.poetry.group.dev.dependencies]` since Spec 053), pytest 8.x, Pydantic 2.x (frozen models). For US4's PostgresRuntime branch (gated under `mise run test:integration`): psycopg 3.x + psycopg_pool (already in `pyproject.toml` since Spec 037). No new third-party dependencies are required for the default fast gate.
**Storage**: For US4: in-memory `RuntimeDatabase` (default fast gate) + `PostgresRuntime` against a transient test database (`mise run test:integration` only). For US1 / US2 / US3: N/A — pure in-memory `WorldState` exercised by the engine.
**Testing**: pytest with `@pytest.mark.unit` markers; profile registration in `tests/conftest.py` (project-wide) and `tests/property/conftest.py` (per-package) per Spec 053 / 054 / 055 pattern
**Target Platform**: `mise run test:unit` (default fast gate, US1 + US2 + US3 + US4-in-memory) + `HYPOTHESIS_PROFILE=slow` (nightly / pre-release) + `mise run test:integration` (US4 PostgresRuntime branch only)
**Project Type**: Testing infrastructure extending the existing `tests/property/` module
**Performance Goals**: 4 invariant test files complete in ≤ 60 s on default profile (`max_examples=100`, `derandomize=True`); ≤ 5 min on slow profile (`max_examples=500`); combined `tests/property/` suite (Specs 053 + 054 + 055 + 056) ≤ 4 min on default profile (current baseline ~88 s + ~30 s headroom for new spy-based tests)
**Constraints**: Must reuse Spec 053 / 054 / 055 harness style (profile registration, opt-out ClassVar markers, single-source-of-truth imports); zero new third-party dependencies for the default fast gate; deterministic on default profile; failure messages must point at offending System pair (US1) / consequence-organization pair (US2) / DB surface (US3) / overwritten tick number (US4); spies must be observably non-interfering per FR-012
**Scale/Scope**: 21 Systems × random `WorldState` (US1 + US2 trace recordings); ≥ 2 organizations per US2 example; ≥ 5-tick monotonicity sequence (US4); 2 RuntimePersistence backends (US4); ServiceContainer attribute introspection picks up DB-bearing services automatically (US3)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Tier | Compliance |
|-----------|------|------------|
| **III.7 Determinism Hash and Replayability** | P0 | **PASS — direct alignment for US3 + US4.** III.7 declares "non-determinism is a bug, not a design choice." US3 enforces this for the *intra-tick* domain (no DB reads can introduce non-determinism into the System loop). US4 enforces it for the *inter-tick* domain (once tick N is persisted it cannot be silently rewritten — replay from any tick is preserved). Default profile uses `derandomize=True` (per Spec 053 / 054 / 055 convention); a failing Hypothesis seed is reproducible across runs. |
| **III.8 Aleksandrov Test (Structural Provenance)** | P0 | **PASS — explicit alignment table in research.md §6.** Each of the four invariants ties to a material relation: US1 encodes the materialist causality ordering of ADR032 (base before superstructure); US2 encodes the OODA-deliberation contract (organizations observe a fixed material state before acting); US3 encodes II.6's "no DB I/O during tick" (the engine is a pure transformation); US4 encodes the historical-record commitment (the audit trail is immutable). |
| **II.6 State is Data, Engine is Transformation** | P1 | **PASS — US3 + US4 ARE the operational tests.** II.6 explicitly states "No DB I/O during tick" — US3 converts that constitutional commitment into a machine-checkable property. II.6's "engine is transformation" half is independently asserted by Spec 055 US3 (no in-place mutation) and is not duplicated here. US4 ties to the persistence half: durable state IS data, and once written is immutable. |
| **III.2 Falsifiability Required** | P1 | **PASS — direct alignment.** Each causal invariant becomes a Hypothesis-driven falsifiability harness. Predictions are encoded as predicates on call traces (US1 + US2), patched-service raise behavior (US3), and persistence-read assertions (US4). Falsifying observations are Hypothesis-shrunk minimal trace inversions / DBIONotPermitted captures / MonotonicityViolation absences. |
| **II.11 Subsystem Table Ownership** | P1 | **PASS — direct alignment for US3.** US3's no-DB-I/O ban inherently enforces II.11 because no System can read another subsystem's tables during a tick if it cannot read any DB at all. |
| **I.18 Material-Ideological Distinction** | P2 | **PASS — US1 IS the operational test.** I.18's "material basis exists regardless of consciousness" maps to ADR032's "Material Base before Superstructure"; US1 is the call-order spy that catches a regression where superstructure (deliberation) decides against stale material data. |
| **II.10 World Runtime** | P2 | **PASS — US3 + US4 are the operational tests.** II.10 declares the runtime boundary; ADR037 extends the persistence half to PostgresRuntime. US3 enforces the runtime boundary (no I/O during execution); US4 enforces the persistence-write boundary (writes are append-only modulo the strict-raise contract). |
| **I.17 OODA** | P2 | **PASS — US2 IS the operational lint.** I.17's commitment that organizations deliberate over a fixed material snapshot becomes a machine-checkable contract: every per-organization action MUST resolve before any consequence System touches the graph. The "all organizations have acted, not interleaved" property is exactly the order-independence-over-organization-set claim US2 asserts via Acceptance Scenario 3. |
| **I.20 Spatial Substrate Immutable** | P0 | **PASS — substrate is read-only.** Tests do not mutate hex grid; spies are non-interfering (FR-012); patched DB scope only blocks reads/writes, does not corrupt state. |
| **II.9 Morphism Dyadic** | P0 | **N/A — no morphism construction.** Tests exercise existing Systems / persistence; no new morphism edges added. |
| **V Verb Atomicity** | P0 | **N/A — no verb invocation.** Tests exercise Systems / persistence, not player verbs. |
| **III.1 No Magic Constants** | P1 | **PASS.** All thresholds (≥ 5 ticks for US4 monotonicity, ≥ 2 orgs for US2, etc.) are derived from acceptance criteria in spec.md and recorded in research.md §3 with provenance. |

**Gate decision (Phase 0 pre-research): PASS.** No constitutional violations.
US3 and US4 are the *operational realization* of constitutional commitments
(II.6 "No DB I/O during tick"; III.7 determinism for replay) that are
declared in the constitution but not previously asserted as properties.
US1 and US2 are the operational realization of ADR032's materialist
causality and I.17's OODA contract. Proceed to Phase 0.

**Re-evaluation (post-Phase 1 design + post-/speckit.analyze remediation): PASS.**
The design (`data-model.md` + four contracts in `contracts/`) introduces:

- Three new System-classification constants in `simulation_engine.py`
  (`MATERIAL_BASE_SYSTEMS`, `ACTION_PHASE_SYSTEMS`, `CONSEQUENCE_SYSTEMS`)
  that partition `_DEFAULT_SYSTEMS` into three frozensets. Read-only at
  test time; production-side declaration adjacent to ADR032's documented
  ordering so the two cannot drift out of sync.
- One `_DEFAULT_SYSTEMS` reorder (per F6=α, post-verification): move
  `OODASystem` from position 21 (current end) to position 14 (between
  `MetabolismSystem` and `SurvivalSystem`). This makes the codebase's
  actual execution order match ADR032's "Material Base → Action Phase
  → Superstructure" partition. The reorder is behavior-preserving for
  the persistence observer, the session recorder, and all existing
  unit tests (audit included in T004); risk is bounded.
- One new exception class (`MonotonicityViolationError`) and a
  refinement of the `RuntimePersistence.persist_tick` docstring (per
  F7=B, post-verification) to declare monotonic-idempotent semantics:
  same-payload retry succeeds, different-payload retry raises. Both
  `RuntimeDatabase` and `PostgresRuntime` implementations acquire the
  same-payload-vs-different comparison; existing UPSERT-retry callers
  (`persistence_observer.py:146`, `session_recorder.py:168`) continue
  to work. This is contract-tightening, not contract-changing.
- One `OODASystem._resolve_for_organization` helper extraction (per
  F1, post-/speckit.analyze): the per-organization loop body becomes
  a named private method so `unittest.mock.patch.object` has a clean
  seam for the per-org spy. Behavior-preserving refactor; the
  `_collect_org_nodes` helper at `ooda.py:198` remains unchanged.
- A `causal_harness.py` module bundling shared event dataclasses
  (`SystemCallEvent`, `OrganizationActionEvent`, `TickTrace`) — the
  original `CausalInvariantHarness` runner class was dropped per
  C1 finding (YAGNI; tests use primitives directly, matching Spec
  055's `TopologyInvariantHarness` light-touch usage).
- New Hypothesis strategies are minimal: US1/US2 reuse `worldstate_strategy`
  from Spec 040 with `min_entities >= 2` for org-bearing examples; US3
  reuses `worldstate_strategy` directly; US4 uses a small synthetic
  multi-tick generator. No third-party dependency additions.
- Reuse of Spec 053–055 harness infrastructure (profile registration,
  `system_registry`, `_iter_worldstate_collections`) without modification.

Nothing in the design adds primitives (no new dialectic types, morphism
relations, transport edge types), mutates substrate (I.20), introduces
non-determinism (default profile `derandomize=True`), uses magic constants
(System sets imported from production), produces unfalsifiable formalism
(each invariant has a falsification predicate), invokes AI adjudication
(II.5), reads cross-subsystem tables (II.11 — US3 explicitly bans this),
or depends on `[TRANSITION STATE]` principles (no II.7 / I.18 / VIII.9
amendment dependency in scope this time). Aleksandrov Test trace is
documented in `research.md §6`. Proceed to Phase 2 (`/speckit.tasks`).

## Project Structure

### Documentation (this feature)

```text
specs/056-causal-invariants/
├── plan.md                              # This file (/speckit.plan command output)
├── spec.md                              # Already written (/speckit.specify + /speckit.clarify)
├── research.md                          # Phase 0 output — patterns + decisions
├── data-model.md                        # Phase 1 output — entities, attributes, relationships
├── quickstart.md                        # Phase 1 output — how to run + interpret failures
├── contracts/                           # Phase 1 output — per-invariant predicate contracts
│   ├── material_base_ordering.md
│   ├── consequence_after_actions.md
│   ├── no_db_io_during_tick.md
│   └── tick_persistence_monotonic.md
├── checklists/
│   └── requirements.md                  # Already written (spec quality checklist)
└── tasks.md                             # Phase 2 output (/speckit.tasks command — NOT created here)
```

### Source Code (repository root)

```text
tests/property/
├── conftest.py                          # MODIFY — only if Spec 053 / 054 / 055 fixtures are insufficient
│                                        #          (default: reuse as-is)
├── invariants/                          # Existing directory from Spec 053 / 054 / 055
│   ├── test_value_conservation.py       # Spec 053 — unchanged
│   ├── test_h3_hierarchical.py          # Spec 053 — unchanged
│   ├── test_circulation_v.py            # Spec 053 — unchanged
│   ├── test_population.py               # Spec 053 — unchanged
│   ├── test_capital_recurrence.py       # Spec 053 — unchanged
│   ├── test_probability_bounds.py       # Spec 054 — unchanged
│   ├── test_wealth_heat_bounds.py       # Spec 054 — unchanged
│   ├── test_simplex_pipeline.py         # Spec 054 — unchanged
│   ├── test_alpha_smoothing.py          # Spec 054 — unchanged
│   ├── test_edge_mode_trajectory.py     # Spec 055 — unchanged
│   ├── test_community_membership_lint.py  # Spec 055 — unchanged
│   ├── test_frozen_discipline.py        # Spec 055 — unchanged
│   ├── test_round_trip_identity.py      # Spec 055 — unchanged
│   ├── test_material_base_ordering.py   # NEW — US1 (P1)
│   ├── test_consequence_after_actions.py  # NEW — US2 (P1)
│   ├── test_no_db_io_during_tick.py     # NEW — US3 (P2)
│   └── test_tick_persistence_monotonic.py  # NEW — US4 (P3)
├── strategies/                          # Existing from Spec 053 / 054 / 055
│   ├── ... (unchanged)
│   └── multi_tick_sequence.py           # NEW — synthetic multi-tick generator for US4
└── harness/                             # Existing from Spec 054 / 055
    ├── __init__.py                      # MODIFY — re-export `causal_harness`, `system_call_spy`,
    │                                    #          `org_action_spy`, `no_db_io_during_tick`
    ├── bound_harness.py                 # Spec 054 — unchanged
    ├── topology_harness.py              # Spec 055 — unchanged
    ├── frozen_audit.py                  # Spec 055 — unchanged
    ├── model_class_registry.py          # Spec 055 — unchanged
    ├── system_registry.py               # Spec 054 — REUSED for US1 + US2 spy wrapping
    ├── causal_harness.py                # NEW — CausalInvariantHarness runner
    ├── system_call_spy.py               # NEW — SystemCallSpy wrapping each System.step
    ├── org_action_spy.py                # NEW — OrganizationActionSpy injected into OODASystem
    └── no_db_io_during_tick.py          # NEW — context manager patching DB surfaces

src/babylon/engine/simulation_engine.py  # MODIFY — (a) add three Final[frozenset[type[System]]] constants:
                                         #   MATERIAL_BASE_SYSTEMS,
                                         #   ACTION_PHASE_SYSTEMS,
                                         #   CONSEQUENCE_SYSTEMS
                                         # adjacent to _DEFAULT_SYSTEMS; partition is verified at import
                                         # time by an assertion that they cover _DEFAULT_SYSTEMS exactly.
                                         # (b) REORDER `_DEFAULT_SYSTEMS` so OODASystem moves from
                                         # position 21 (current end) to position 14 (between
                                         # MetabolismSystem and SurvivalSystem), matching ADR032's
                                         # documented Material Base → Action Phase → Consequences
                                         # partition (F6=α, 2026-05-07).

src/babylon/persistence/protocols.py     # MODIFY — add `MonotonicityViolationError` exception class;
                                         # refine `RuntimePersistence.persist_tick` docstring to declare
                                         # monotonic-idempotent semantics: same-payload retry succeeds,
                                         # different-payload retry raises (F7=B, 2026-05-07).

src/babylon/persistence/runtime_db.py    # MODIFY — add monotonic-idempotent check in `RuntimeDatabase.persist_tick`:
                                         # compare new payload against existing for same (session_id, tick);
                                         # if equal, return silently; if different, raise
                                         # `MonotonicityViolationError`.

src/babylon/persistence/postgres_runtime.py  # MODIFY — add monotonic-idempotent check in
                                         # `PostgresRuntime.persist_tick`: catch psycopg.UniqueViolation
                                         # from the existing INSERT, SELECT the existing payload,
                                         # compare against the new payload, return silently if equal,
                                         # raise `MonotonicityViolationError` if different. Schema
                                         # migration adds `UNIQUE (session_id, tick)` constraint.

src/babylon/engine/systems/ooda.py       # MODIFY — extract `_resolve_for_organization(self, graph, services,
                                         # context, org_id, org_data) -> None` private helper method on
                                         # `OODASystem`, lifting the per-organization loop body currently
                                         # inlined in `step` (F1, 2026-05-07). Behavior-preserving refactor;
                                         # the `_collect_org_nodes` module-level helper is unchanged. This
                                         # gives `unittest.mock.patch.object` a clean named seam for
                                         # `OrganizationActionSpy`.

src/babylon/engine/systems/*.py          # MODIFY (per-System, on-demand) — add
                                         # `bypasses_causal_invariant: ClassVar[dict[str, str]] = {…}`
                                         # markers ONLY for Systems that the harness empirically finds
                                         # legitimately bypass a predicate. Default-deny — most Systems
                                         # will not need a marker.
```

**Structure Decision**: This is a testing-infrastructure feature; the new
artifacts live almost entirely under `tests/property/`, mirroring the Spec
055 layout. Production-side changes are concentrated in three files:
`simulation_engine.py` (three new partition constants),
`persistence/protocols.py` (new exception + contract update), and the
two `RuntimePersistence` implementations (`runtime_db.py`,
`postgres_runtime.py` — overwrite detection). The `harness/` directory
gains four modules (`causal_harness.py`, `system_call_spy.py`,
`org_action_spy.py`, `no_db_io_during_tick.py`) and reuses
`system_registry.py` and the `_iter_worldstate_collections` helper from
Spec 054 without modification. No new third-party dependencies; no changes
to `pyproject.toml`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. Section intentionally empty.
