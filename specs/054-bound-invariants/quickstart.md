# Quickstart: Bound Invariants

**Feature**: 054-bound-invariants
**Audience**: Maintainers landing a change to any System, formula, or
constrained type field who need to verify no bound invariants regress.

---

## TL;DR

Run the fast gate before pushing:

```bash
mise run test:unit
```

If a bound invariant fails, look for output like:

```text
FAILED tests/property/invariants/test_probability_bounds.py::TestProbabilityBounds::test_post_runtick_in_range[SocialClass.p_acquiescence]
    INV-006: Field SocialClass.p_acquiescence on entity proletariat_us = 1.000023 (out of [0, 1])
    Falsifying example: state=WorldState(entities={"proletariat_us": SocialClass(...)})
```

The bracketed parameter (`[SocialClass.p_acquiescence]`) tells you exactly
which `(ModelClass, field_name)` pair the bug is in. The diagnostic line
names the entity ID and the offending value. The Hypothesis-shrunk minimal
example follows.

---

## Running the tests

| Command | What it runs |
|---------|--------------|
| `mise run test:unit` | All four bound-invariant suites + Spec 053 conservation suites + the rest of unit tests, default profile (max_examples=100, derandomize=True). Target: ≤ 30 s for the bound suites. |
| `poetry run pytest tests/property/invariants/test_probability_bounds.py -v` | US1 only |
| `poetry run pytest tests/property/invariants/test_wealth_heat_bounds.py -v` | US2 only — per-System trace visible with `-v` |
| `poetry run pytest tests/property/invariants/test_simplex_pipeline.py -v` | US3 only |
| `poetry run pytest tests/property/invariants/test_alpha_smoothing.py -v` | US4 only |
| `HYPOTHESIS_PROFILE=slow poetry run pytest tests/property/invariants/ -v` | Slow profile (max_examples=500). Target: ≤ 5 min. |
| `HYPOTHESIS_PROFILE=nightly poetry run pytest tests/property/invariants/ -v` | Nightly profile (max_examples=5000) — for pre-release sweeps |

---

## What each suite catches

### US1 — `test_probability_bounds.py`

Runs after every code change that touches:

- Anything under `src/babylon/models/` that adds or modifies a
  `Probability`-typed field
- Any formula in `src/babylon/formulas/` whose name matches `*probability*`
  or `*credibility*`
- Any System that mutates entity probability fields
- `SolidaritySystem` (writes `solidarity_strength` on edges)

A failure here means a value escaped the unit interval somewhere in the
pipeline. Look at the parametrize ID to identify which field; the diagnostic
shows which System or formula produced it.

### US2 — `test_wealth_heat_bounds.py`

Runs after every code change that touches:

- Any of the 21 Systems in `src/babylon/engine/systems/`
- `ImperialRentSystem`, `SurvivalSystem`, `StruggleSystem` (most-likely
  Wealth offenders)
- `TerritorySystem`, `ContradictionSystem` (most-likely Heat offenders)
- The economic factories in `src/babylon/engine/factories.py`

A failure here means an entity ended a step with negative wealth or a
territory ended with negative heat. The per-System trace tells you which
System produced the violation; if Predicate B (full-pipeline) fails but
every Predicate A (per-System) passes, you have a multi-System interaction
bug.

### US3 — `test_simplex_pipeline.py`

Runs after every code change that touches:

- `ConsciousnessSystem`, `SolidaritySystem`, `IdeologySystem`,
  `CommunitySystem`
- `formulas/consciousness_routing.py`,
  `formulas/consciousness.py`
- `models/entities/consciousness.py`

A failure here means a System wrote raw `(r, l, f)` to a graph node
without renormalizing, or the routing math has drifted off the simplex.
The diagnostic shows the offending `(r, l, f)` triple and the simplex
error.

### US4 — `test_alpha_smoothing.py`

Runs after every code change that touches:

- `economics/tick/smoothing.py` (the canonical EMA implementation)
- `institution/balance.py`
- `engine/systems/community.py` (heat / cohesion / infrastructure decay)
- Any `*_alpha`, `alpha_smoothing_rate`, or `*_decay_alpha` field in
  `defines.py`
- Crisis-detection logic in `economics/tick/crisis_detector.py`

A failure on Predicate A (synthesized) means the EMA formula is wrong.
A failure on Predicate B (observed) means a System bypassed the smoother.
Both layers run on every change — the per-coefficient parametrize ID
identifies which.

---

## Adding a new System (US2 coverage extension)

The `SystemRegistry` in `tests/property/harness/system_registry.py`
auto-discovers Systems via `pkgutil.iter_modules` over
`src/babylon/engine/systems/`. Adding a new System file is enough — no
test list needs updating.

If the new System legitimately violates a bound invariant (rare), add the
opt-out marker:

```python
class MyNewSystem:
    bypasses_bound_invariant: ClassVar[dict[str, str]] = {
        "non_negative_wealth": "transient negative state during atomic transfer; reconciled within step()",
    }
```

The harness reads the marker and skips that predicate for that System,
producing a `SKIPPED` row in the per-System trace with the justification
visible.

---

## Adding a new `Probability`-typed field (US1 coverage extension)

The discovery walker in
`tests/property/harness/probability_discovery.py` introspects
`model_fields` recursively across `src/babylon/models/`. Adding a new
field with type annotation `Probability` is enough — coverage extends
automatically. Verify with:

```bash
poetry run python -c "from tests.property.harness.probability_discovery import discover_probability_fields; print(discover_probability_fields())"
```

Should list your new field as a `(YourModelClass, "your_field_name")`
tuple.

---

## Adding a new α-smoothed coefficient (US4 coverage extension)

The discovery walker in `tests/property/harness/alpha_discovery.py`
matches the regex `(?:.*_alpha|alpha_smoothing_rate|.*_decay_alpha)$`
against field names in `defines.py`. Naming a new field consistently
extends coverage automatically.

If your new field is *not* an EMA rate (e.g., a power-law exponent that
happens to be called `pareto_alpha`), add it to `_NOT_EMA_ALPHAS` in
`alpha_discovery.py`:

```python
_NOT_EMA_ALPHAS: Final[frozenset[str]] = frozenset({
    "pareto_alpha",
    "curvature_alpha",
    "your_new_non_ema_alpha",  # explanation comment
})
```

---

## Diagnosing a Hypothesis failure

1. Read the parametrize ID — tells you the (Field/System/Formula) under
   test.
2. Read the diagnostic message — tells you the entity ID and the
   offending value.
3. Read the `Falsifying example:` block — Hypothesis has shrunk to a
   minimal counterexample. Often a single-entity `WorldState`.
4. To replay the exact failing seed, copy the `@reproduce_failure` line
   that Hypothesis prints into the test temporarily.
5. To reproduce locally with the same input distribution as CI, ensure
   `HYPOTHESIS_PROFILE` matches the failing run (default for `mise run
   test:unit`; `slow` for the nightly sweep).

The Hypothesis example database under `.hypothesis/` (gitignored) caches
counterexamples across runs — once a bug is found, subsequent runs will
hit the same example first.

---

## CI integration

The bound suites run inside `mise run test:unit`. CI must:

1. Cache the `.hypothesis/` directory across runs so previously found
   counterexamples are surfaced first (matches Spec 053's CI caching
   note).
2. Set `HYPOTHESIS_PROFILE` per environment:
   - PR CI: `default` (already the env default)
   - Nightly: `slow`
   - Pre-release: `nightly`
3. Fail-fast on any bound-invariant failure — these are correctness
   bugs, not flakes.

---

## Future work (out of scope for this spec)

- Narrow formula return annotations from `-> float` to `-> Probability`
  for every formula whose mathematical contract is "returns a
  probability." Would replace the allow-list in research §2 with a
  type-driven discovery rule. Tracked separately.
- Extend bound coverage to other constrained types (`Coefficient`,
  `Intensity`, `Ideology`). Would be a sister spec — same harness,
  different invariant classes.
- Property-test coefficient smoothing across crisis transitions
  (`NORMAL → ONSET → EARLY → DEEP → RECOVERY → NORMAL`) to verify the
  reset and re-equilibration semantics. Out of scope here; the spec
  carves crisis ticks out as suspended.
