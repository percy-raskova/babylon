# Quickstart: Marx Value-Form Invariants

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

A new developer (or a future Claude instance) can follow this end-to-end
flow to exercise the invariant bundle on the existing branch.

## Prerequisites

- Branch `060-value-form-invariants` checked out.
- Dev dependencies installed: `poetry install`.
- Hypothesis already in dev deps (since spec 053); no install needed.
- (Optional) Local Postgres NOT required for this bundle — all tests
  run in-memory.

## Run the bundle

```bash
# Whole bundle
poetry run pytest -m invariant -v

# Per-user-story
poetry run pytest -m invariant -k numeraire      # US1 / FR-001, FR-002
poetry run pytest -m invariant -k melt_consistency   # US2 / FR-003
poetry run pytest -m invariant -k aggregate_equ  # US3 / FR-005
poetry run pytest -m invariant -k wage_occ       # US4 / FR-006
poetry run pytest -m invariant -k productivity   # US5 / FR-007
poetry run pytest -m invariant -k 'relabel or roundtrip or markov or h3'  # US6
poetry run pytest -m invariant -k 'proportional or monotonicity or volume_iii'  # US7
```

Standard test reports land in `reports/test-results/` per the project's
`mise test:*` conventions.

## Interpret the diagnostic output

Every failing assertion includes:

1. The offending entity / aggregate (`entity_id`).
2. The numerical magnitude of the violation (relative + absolute).
3. A `spec-060 FR-XYZ` reference pointing back to this spec.

Example failing output (synthetic):

```text
FAILED tests/integration/economics/test_melt_consistency.py::test_per_entity_money_equals_labor_times_tau

ConsistencyReport(
    n_entities_checked=12, n_skipped_no_data=0, n_skipped_degenerate=2,
    max_relative_error=0.0034,
    worst_entity=EntityViolation(
        entity_id="DETROIT_PROLETARIAT",
        field_name="s",
        labor_hours=125_000.0,
        money_currency=8_062_500.00,
        expected_money=8_125_000.00,   # 125_000 × τ where τ = $65/hr
        relative_error=0.0077,
        absolute_error_currency=-62_500.00,
    ),
    violations=[...3 more...],
)

Violates spec-060 FR-003: |money_s - labor_s × τ| / |money_s| ≤ 1e-9
required; measured 7.7e-3 worst-case.
```

## Deliberately introduce a bug to verify a test catches it

The bundle's value depends on its sensitivity. Test each FR by
introducing a known-bad behavior and confirming the corresponding test
fails. Suggested experiments:

### Numeraire invariance (US1 / FR-001)

Edit `src/babylon/economics/derived_metrics.py` to add a `1.0` to the
profit rate computation (a hard-coded money offset):

```python
# WRONG: introduces a money-unit dependency
profit_rate_flow = self.tensor.profit_rate + 1.0  # ← bug
```

`poetry run pytest -m invariant -k numeraire` should fail because
profit rates now depend on the absolute scale.

### MELT consistency (US2 / FR-003)

Edit `src/babylon/economics/melt/melt_calculator.py` to return a τ that's
10% off:

```python
def get_melt(self, year):
    return 0.9 * (gdp / employment / 2080)   # ← bug
```

`poetry run pytest -m invariant -k melt_consistency` should fail with
~10% relative error.

### UUID relabeling (US6a / FR-013)

Introduce an iteration-order-dependent reduction somewhere in
`src/babylon/engine/simulation_engine.py`:

```python
# WRONG: iteration order = dict insertion order, which differs after
# relabeling because alias names sort differently
for org_id in sorted(world.organizations.keys()):  # ← would still pass
for org_id in world.organizations.keys():          # ← inserts may differ post-relabel; CPython 3.7+ preserves insertion order
```

A more reliable bug: introduce a hash-dependent reduction like
`hash(org_id) % N` used as a coefficient. `poetry run pytest -m invariant
-k relabel` should fail.

### H3 round-trip (US6d / FR-016)

Edit `src/babylon/config/h3_splitter.py` so `split_uniformly` returns
`[parent_value / (n_children - 1)] * n_children` (off-by-one). The H3
round-trip test should immediately fail at the parent-conservation
assertion.

## Verify byte-equality is preserved (FR-012, SC-008)

```bash
# Snapshot baseline BEFORE landing the bundle (do this on parent commit)
git checkout origin/main
poetry run python tools/parameter_analysis.py trace \
  --csv /tmp/spec-060-baseline.csv --ticks 200

# After landing the bundle
git checkout 060-value-form-invariants
poetry run python tools/parameter_analysis.py trace \
  --csv /tmp/spec-060-after.csv --ticks 200

cmp -s /tmp/spec-060-baseline.csv /tmp/spec-060-after.csv \
  && echo "✅ byte-identical" \
  || echo "❌ DIVERGENCE: bundle broke the byte-equality invariant"
```

The bundle is a test-only addition and MUST produce byte-identical
output. Any divergence is a bug in the bundle.

## Run individual property tests with extra examples

For deeper coverage during development:

```bash
poetry run pytest -m invariant -k numeraire \
  --hypothesis-profile=ci \
  --hypothesis-seed=42 \
  --hypothesis-verbosity=verbose
```

Per FR-020, CI runs use `derandomize=true` so failures are reproducible.

## Read the contracts before writing tests

The contracts under `contracts/` define **exactly** what each test
asserts. If you're implementing a contract (during `/speckit.tasks`),
read its Given-When-Then before writing code.

| Contract | File | FR |
|---|---|---|
| Test contracts | `contracts/invariant_test_contracts.md` | FR-001 through FR-022 |
| Transformation probe | `contracts/transformation_mode_probe.md` | FR-021 |
| Monetary rescaling | `contracts/monetary_rescaling.md` | FR-001, FR-002 |
| UUID relabeler | `contracts/uuid_relabeler.md` | FR-013 |

## Common pitfalls

1. **Forgetting the `@pytest.mark.invariant` marker.** Per FR-022,
   every test in this bundle must have it. CI does not strictly enforce
   this but losing the bundle's group-run semantics is a regression.

2. **Re-implementing the transformation-mode probe.** Per FR-021, do not.
   Import from `tests/_helpers/invariants/transformation_mode.py`.

3. **Floating-point tolerances too tight.** Use exactly the tolerances
   the spec calls for: 1e-15 (US6 a/c), 1e-12 (US1, US7-prop), 1e-9
   (US2, US6 d), 1e-6 (US3). Tighter tolerances will create flake on
   different hardware.

4. **Comparing `WorldState` instances with `assert a == b`.** Works for
   Pydantic structural equality (frozen models) but emits unreadable
   diffs. Use DeepDiff (already in dev deps) for diagnostics; the test
   should still use `==` for the actual assertion.

5. **Skipping cleanly without a spec reference.** Every `pytest.skip`
   call MUST include "spec-060 FR-XYZ" or the equivalent ADR reference
   so the skip is traceable per FR-010.

## What to do if a test fails on `main` already

If a test fails on the parent commit (before this bundle's changes),
that is a **pre-existing engine bug surfaced by the invariant**. Do not
silence the test. File an issue, reference the FR, and continue with
the spec-060 landing. Quarantining the test would violate the spec's
purpose (it exists to surface exactly such bugs).
