# Quickstart: Running Causal/Temporal Invariant Tests

**Feature**: 056-causal-invariants
**Audience**: Maintainers running these tests locally or interpreting CI failures.

## TL;DR

```bash
# Default fast gate (US1 + US2 + US3 + US4-in-memory)
mise run test:unit

# Slow gate (5x more Hypothesis examples per test)
HYPOTHESIS_PROFILE=slow poetry run pytest tests/property/invariants/test_material_base_ordering.py -v
HYPOTHESIS_PROFILE=slow poetry run pytest tests/property/invariants/test_consequence_after_actions.py -v
HYPOTHESIS_PROFILE=slow poetry run pytest tests/property/invariants/test_no_db_io_during_tick.py -v
HYPOTHESIS_PROFILE=slow poetry run pytest tests/property/invariants/test_tick_persistence_monotonic.py -v

# US4 PostgresRuntime branch (requires running Postgres + transient test DB)
mise run test:integration

# Single test, default profile, verbose
poetry run pytest tests/property/invariants/test_material_base_ordering.py -v
```

## What these tests guard

The four test files in this feature each guard one constitutional or
architectural commitment:

| Test File | Invariant | Guards |
|-----------|-----------|--------|
| `test_material_base_ordering.py` | INV-013 | ADR032 Materialist Causality — base before superstructure |
| `test_consequence_after_actions.py` | INV-014 | I.17 OODA + III.7 Determinism — order independence over the organization set |
| `test_no_db_io_during_tick.py` | INV-015 | II.6 ("No DB I/O during tick") + II.10 + II.11 + ADR037 |
| `test_tick_persistence_monotonic.py` | INV-016 | II.6 (State is Data) + III.7 (replay) — audit trail immutability |

Each test combines a Hypothesis property strategy with a harness assertion;
failures are Hypothesis-shrunk minimal examples that point at the
violating System / organization / DB surface / tick number.

## Reading a failure

Hypothesis failures look like this (example for INV-013):

```text
test_material_base_ordering.py::TestMaterialBaseOrdering::test_material_base_runs_before_action_phase FAILED

Falsifying example: state=WorldState(...)
  Expected: call_index(VitalitySystem) < call_index(OODASystem)
  Got:      call_index(VitalitySystem) = 5, call_index(OODASystem) = 2

Inversion detected: OODASystem ran at index 2, but VitalitySystem (Material Base) ran at index 5.
Material Base Systems must complete before any Action Phase System begins.

To reproduce locally:
  HYPOTHESIS_SEED=<seed_from_above> poetry run pytest \
    tests/property/invariants/test_material_base_ordering.py::TestMaterialBaseOrdering::test_material_base_runs_before_action_phase -v
```

The default profile uses `derandomize=True` (per Spec 053 / 054 / 055
convention) so a failing seed is reproducible across runs and across
machines.

### Common failure patterns

| Symptom | Likely Cause | First Action |
|---------|--------------|--------------|
| `INV-013` fails after editing `_DEFAULT_SYSTEMS` | New System not classified into one of the three partition sets | Edit `simulation_engine.py`: add the new System to whichever of `MATERIAL_BASE_SYSTEMS` / `ACTION_PHASE_SYSTEMS` / `CONSEQUENCE_SYSTEMS` is correct. Import-time assertion will catch which set is missing the System |
| `INV-014` fails with `(consequence_system, organization_id)` triple | A Consequence System ran inside the per-org loop instead of after | Audit the `step()` of the named Consequence System; ensure it operates over the post-OODA graph state, not on a per-org callback |
| `INV-014` Acceptance Scenario 3 fails | `OODASystem` introduced order-dependence over the org set | Audit any state that depends on iteration order: dict insertion order, list-prepend operations, accumulator reductions that aren't commutative |
| `INV-015` fails with `DBIONotPermittedError(database, execute)` | A System opened a DB connection during its `step()` | Move the DB call to hydration (before `run_tick`) or persistence (after `run_tick`). If the data is genuinely needed mid-tick, hydrate it into the graph upfront. |
| `INV-015` fails with `DBIONotPermittedError(persistence, write_state)` | A System wrote intermediate state to durable storage during the tick | All durable writes happen post-tick via the persistence pipeline; remove the intra-tick write |
| `INV-016` fails: "no MonotonicityViolationError raised" | Persistence backend silently allowed overwrite | Add the strict-raise check to the implementation per `data-model.md §1.3` |
| `INV-016` fails: "read_tick returned overwrite payload" | Persistence backend allowed the overwrite to commit before raising | Move the duplicate check BEFORE the write transaction, not after |

## What's NEW vs. what's REUSED

### NEW production surface (concentrated, minimal)

- `src/babylon/engine/simulation_engine.py` — three `Final[frozenset[type[System]]]`
  constants (`MATERIAL_BASE_SYSTEMS`, `ACTION_PHASE_SYSTEMS`,
  `CONSEQUENCE_SYSTEMS`) + import-time partition assertion (~30 LOC)
- `src/babylon/persistence/protocols.py` — `MonotonicityViolationError`
  exception class + docstring extension on `RuntimePersistence.write_state`
  (~15 LOC)
- `src/babylon/persistence/runtime_db.py` — overwrite-detection check in
  `write_state` (~3 LOC)
- `src/babylon/persistence/postgres_runtime.py` — overwrite-detection
  wrapper around INSERT + schema migration adding `UNIQUE` constraint on
  `tick` column (~5 LOC + 1 migration file)

### NEW test surface

- `tests/property/invariants/test_material_base_ordering.py`
- `tests/property/invariants/test_consequence_after_actions.py`
- `tests/property/invariants/test_no_db_io_during_tick.py`
- `tests/property/invariants/test_tick_persistence_monotonic.py`
- `tests/property/harness/causal_harness.py` — `CausalInvariantHarness`,
  `TickTrace`
- `tests/property/harness/system_call_spy.py` — `SystemCallSpy`,
  `SystemCallEvent`
- `tests/property/harness/org_action_spy.py` — `OrganizationActionSpy`,
  `OrganizationActionEvent`
- `tests/property/harness/no_db_io_during_tick.py` — context manager +
  `DBIONotPermittedError`
- `tests/property/strategies/multi_tick_sequence.py` — strategy for US4

### REUSED from Spec 053 / 054 / 055

- `tests/property/conftest.py` profile registration (default / dev / ci /
  nightly) — unchanged
- `tests/property/strategies/worldstate.py::worldstate_strategy` —
  unchanged
- `tests/property/harness/system_registry.py` — unchanged; reused for
  enumerating Systems to wrap with `SystemCallSpy`
- `tests/property/harness/bound_harness.py::HarnessResult` — unchanged;
  reused for assertion result shape
- Spec 055 exclude rules (`SOCIAL_CLASS_COMPUTED_FIELDS`,
  `TERRITORY_EXCLUDED_FIELDS`) — reused in the `test_spy_does_not_alter_post_state`
  non-interference check (FR-012)
- The `bypasses_*_invariant` ClassVar marker pattern — same shape,
  renamed to `bypasses_causal_invariant`

## Adding a new System (the workflow)

Per Spec 056, adding a new System to `_DEFAULT_SYSTEMS` is now a four-step
workflow:

1. Add the System class to the imports + the `_DEFAULT_SYSTEMS` list in
   `simulation_engine.py` (existing workflow).
2. Add the System type to **exactly one** of `MATERIAL_BASE_SYSTEMS`,
   `ACTION_PHASE_SYSTEMS`, or `CONSEQUENCE_SYSTEMS` in `simulation_engine.py`.
3. The import-time partition assertion verifies the partition is still
   complete and disjoint. If it fails, you missed step 2.
4. The four invariant tests automatically pick up the new System via the
   imports — no test edits required.

## Adding a new persistence backend

Per Spec 056, a new `RuntimePersistence` implementation MUST:

1. Implement `write_state(tick, payload)` to raise
   `MonotonicityViolationError` on any overwrite of an
   already-persisted tick.
2. Be added to the `pytest.parametrize` list in
   `test_tick_persistence_monotonic.py` (one entry per implementation).
3. Pass all three predicates (sequential writes, same-tick overwrite,
   back-in-time overwrite).

## Combined performance budget

Per SC-005:

- Default profile (`max_examples=100`): four files complete in ≤ 60s
- Slow profile (`max_examples=500`): four files complete in ≤ 5 min
- Combined `tests/property/` suite (Specs 053 + 054 + 055 + 056) on
  default profile: ≤ 4 min total (current baseline ~88 s for Specs
  053–055; Spec 056 adds ~30s headroom for the spy-based tests)

If a future System addition pushes the suite past these limits, the
remediation is to reduce `max_examples` per Hypothesis profile rather
than disable tests.

## Seeing also

- `spec.md` — feature specification
- `plan.md` — implementation plan
- `research.md` — Phase 0 research and decision rationale
- `data-model.md` — entity shapes (production + test)
- `contracts/` — per-invariant predicate contracts
- ADR032 — Materialist Causality system order
- ADR037 — Postgres Runtime DB
- Constitution II.6 — State is Data, Engine is Transformation (the
  binding source for US3 and US4)
