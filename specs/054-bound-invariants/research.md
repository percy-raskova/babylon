# Phase 0 Research: Bound Invariants

**Feature**: 054-bound-invariants
**Date**: 2026-05-06
**Spec**: [spec.md](./spec.md)

## Purpose

Resolve open implementation patterns and surface findings that emerged from
reading the production code. The four `/speckit.clarify` decisions are
already in `spec.md`; this document records the *technical* decisions that
follow from them.

---

## §1. `Probability` constrained type — discovery pattern

**Decision**: Walk every Pydantic model in `src/babylon/models/` (recursively
through subpackages), iterate `model_fields.items()`, and for each field
inspect its `metadata` list for the sentinel marker that distinguishes
`Probability` from a bare `float`. Yield each `(ModelClass, field_name)`
pair whose annotation resolves to the `Probability` alias.

**Rationale**: `Probability` is defined in `src/babylon/models/types.py:50` as

```python
Probability = Annotated[
    float,
    Field(ge=0.0, le=1.0, description="Value in range [0.0, 1.0] ..."),
    SnapToGrid,
]
```

Pydantic v2 collects the `Annotated` metadata into
`FieldInfo.metadata`; `field_info.metadata[0]` is the `FieldInfo` containing
`ge=0.0` and `le=1.0`, and `field_info.metadata[1]` is the `AfterValidator`
wrapping `quantize`. The cleanest detection rule is **identity-by-import**:
import `Probability` directly into the discovery module and check whether a
field's `annotation` *is* the `Probability` alias. This works because
`Annotated[X, …]` is hashable and identity-stable when bound to a name in
the importing module.

```python
from typing import get_args, get_type_hints
from babylon.models.types import Probability

def is_probability_field(annotation: type) -> bool:
    """True iff annotation is the Probability constrained type alias."""
    return annotation is Probability
```

**Alternatives considered**:

- **Metadata sniffing** (look for `FieldInfo(ge=0.0, le=1.0)` in
  `metadata`): brittle — `Coefficient` and `Intensity` have the same `ge=0.0
  / le=1.0` bounds, so this would conflate three distinct types. Rejected.
- **Manual registry** (`PROBABILITY_FIELDS = [(SocialClass,
  "p_acquiescence"), …]`): explicitly forbidden by the Q1 clarification
  ("no hand-maintained registry"). Rejected.
- **String-name heuristic** (any field starting with `p_` or containing
  `probability`): would falsely include `population` and `prev_*`. Rejected.

---

## §2. Probability-returning formulas — discovery pattern

**Decision**: Use a **two-layer hybrid**: (a) a hardcoded allow-list of the
canonical probability formulas (`calculate_acquiescence_probability`,
`calculate_revolution_probability`, etc.) maintained in
`tests/property/strategies/probability_field.py`, AND (b) an automated scan
that warns when a new formula in `src/babylon/formulas/` has "probability"
or "credibility" in its name but is not in the allow-list. The harness uses
the allow-list for assertion; the warning surfaces drift.

**Rationale**: A grep for `-> Probability` in `src/babylon/formulas/`
returns **zero hits**. Probability formulas all currently return `-> float`:

```
src/babylon/formulas/survival_calculus.py:24:    ) -> float:
src/babylon/formulas/survival_calculus.py:44:def calculate_revolution_probability(cohesion: float, repression: float) -> float:
```

The formulas mathematically produce values in `[0, 1]`, but the Pydantic
constrained type is only applied at the *field* boundary (when the float is
stored on a `SocialClass.p_acquiescence` slot). FR-002(b) as worded would
silently discover zero formulas — which would pass vacuously but provide no
falsification. The two-layer approach honors the spec's intent (every
formula whose mathematical contract is "returns a probability") while being
robust to current code that uses `float`.

The allow-list can be retired once formula return annotations are
narrowed to `Probability` in a separate refactor (out of scope).

**Alternatives considered**:

- **Strict literal rule**: discover only `-> Probability` formulas. Rejected
  because the discovery set is currently empty; tests would pass vacuously.
- **Docstring scan** for "Returns Probability [0, 1]" or "P(S|...)": fragile
  because docstrings drift and Sphinx-cross-references add noise.
- **Annotate the formulas**: refactor every probability formula to return
  `Probability`. Out of scope for this spec; would touch ~20 formulas and
  require their callers to handle the constrained type. Tracked as a
  follow-up in `quickstart.md`.

---

## §3. System auto-discovery — reuse Spec 053 pattern

**Decision**: Reuse the `_discover_non_opt_out_engine_systems` pattern from
`tests/property/invariants/test_value_conservation.py:79`. Refactor it into
`tests/property/harness/system_registry.py` so US2's Wealth/Heat test and
US3's pipeline test share the same discovery code.

**Rationale**: Spec 053 already implements the `pkgutil.iter_modules` walk
across `src/babylon/engine/systems/`, filtering out `protocol`, `__init__`,
and the `System` Protocol itself. The same discovery satisfies SC-002's "no
manual list maintenance" requirement and is already battle-tested through
the conservation suite.

The new wrinkle is that the bound-invariant harness reads a
**`bypasses_bound_invariant: ClassVar[dict[str, str]]`** marker rather than
the `creates_value: ClassVar[bool]` marker. Both markers coexist
peacefully — the conservation suite reads `creates_value`; the bound suite
reads `bypasses_bound_invariant`. Adding either marker to a System is
purely additive.

**Alternatives considered**:

- **Hardcoded list of 22 Systems**: explicitly forbidden by SC-002.
- **Decorator-based discovery** (`@bound_invariant_target` on each System):
  requires touching every System file. Rejected as lower-yield than the
  introspection pattern.

---

## §4. α-smoothed coefficient discovery — name-pattern walk

**Decision**: Walk `defines.py` recursively through nested Pydantic models.
For each leaf field, match the field name against the regex
`(?:.*_alpha|alpha_smoothing_rate|.*_decay_alpha)$`. Yield each
`(ModelClass, field_name, default_value)` triple. Manually inspect the
discovered set during implementation and prune false-positives (e.g.,
`pareto_alpha` and `curvature_alpha` are *parameters of a power law*, not
EMA smoothing rates — they need exclusion).

**Rationale**: `grep -rn 'alpha' src/babylon/config/defines.py` yields ~13
candidates. Manual inspection (already done in spec investigation) shows:

| Field | Module | Use |
|-------|--------|-----|
| `alpha_smoothing_rate` | InstitutionDefines | EMA — in scope |
| `heat_decay_alpha` | CommunityDefines | EMA — in scope |
| `cohesion_decay_alpha` | CommunityDefines | EMA — in scope |
| `infrastructure_decay_alpha` | CommunityDefines | EMA — in scope |
| `alpha_21`, `alpha_31`, `alpha_32`, `alpha_41`, `alpha_42`, `alpha_43` | (4-class transition rates) | EMA per pair — in scope |
| `pareto_alpha` | (Pareto distribution exponent) | NOT EMA — exclude |
| `curvature_alpha` | (curvature scaling) | NOT EMA — exclude |

The regex captures all 8 in-scope coefficients and 2 false-positives. The
false-positives need explicit exclusion. Encoding the exclusion list in
`alpha_discovery.py` keeps the false-positive contract auditable:

```python
_NOT_EMA_ALPHAS: Final[frozenset[str]] = frozenset({
    "pareto_alpha",       # power-law distribution exponent, not EMA rate
    "curvature_alpha",    # geometric curvature scale, not EMA rate
})
```

**Alternatives considered**:

- **Tag fields explicitly** with `Field(json_schema_extra={"is_ema": True})`:
  requires touching every smoothed-coefficient field site (~8 fields).
  Tracked as a follow-up if the heuristic accumulates false-positives.
- **Walk `economics/tick/smoothing.py` callers**: only finds the gamma
  EMA, not the institution / community EMAs. Too narrow.

---

## §5. Crisis-phase classification — `CrisisPhase.NORMAL`, not `None`

**Decision**: Steady state is `phase == CrisisPhase.NORMAL or phase is
None`. Crisis is any other `CrisisPhase` enum value (`ONSET`, `EARLY`,
`DEEP`, `RECOVERY`). The spec's "is None ⇒ steady state" wording is a
simplification that holds for fields where `CrisisPhase | None` is the
type but **not** for fields where `phase: CrisisPhase = CrisisPhase.NORMAL`.

**Rationale**: `src/babylon/economics/tick/types.py:39` defines

```python
class CrisisPhase(StrEnum):
    NORMAL = "normal"
    ONSET = "onset"
    EARLY = "early"
    DEEP = "deep"
    RECOVERY = "recovery"
```

The `NORMAL` value is the canonical steady-state marker. Code in
`src/babylon/economics/tick/system.py:1558` uses
`crisis = crisis_phase != CrisisPhase.NORMAL`. The
`CrisisStateInspector.is_steady_state(state)` method should mirror this:

```python
def is_steady_state(state: HasCrisisPhase) -> bool:
    phase = getattr(state, "crisis_phase", None) or getattr(
        state.crisis_state, "phase", None
    ) if hasattr(state, "crisis_state") else None
    return phase is None or phase == CrisisPhase.NORMAL
```

The `RECOVERY` phase is *not* steady state — it's the post-crisis
re-equilibration window where coefficients can still be discontinuously
reset. Treating it as crisis preserves the spec's α-smoothing contract.

**Alternatives considered**:

- **`is_steady_state = phase is None`**: would falsely treat `NORMAL` ticks
  as crisis ticks (suspending the inequality assertion when it should
  apply). Rejected — directly violates US4's intent.
- **Treat `RECOVERY` as steady state**: would assert the inequality during
  re-equilibration, which the spec explicitly carves out as suspended.
  Rejected.

---

## §6. Aleksandrov Test alignment (Constitutional III.8)

Each invariant traces to a material relation. This is the
provenance-chain documentation required by P0 principle III.8.

| Invariant | Material Relation | Why the Bound is Real |
|-----------|-------------------|------------------------|
| **`Probability ∈ [0, 1]`** | Survival probability `P(S\|A)`, `P(S\|R)` and edge `solidarity_strength` encode classical likelihoods of physical events (will an agent survive this tick? will a class transmit consciousness across this edge?). The closed unit interval is the Kolmogorov axiom for measure spaces. A probability outside `[0, 1]` has no measure-theoretic meaning. | The bound *is* the measure-space contract — there is no probability without it. |
| **`Wealth ≥ 0`** | Wealth represents a stock of accumulated labor-time products convertible to subsistence. Negative wealth would imply an agent owes more labor than has ever been produced — physically impossible at the agent level. (Indebtedness is modeled as a *separate* `Debt` field, not as negative wealth.) | The bound *is* the conservation-of-stock semantics. Negative wealth = debt that the simulation does not represent at the agent layer. |
| **`Heat ≥ 0`** | Heat is the territory's accumulated state-attention metric (carceral geography per CLAUDE.md). It accumulates from HIGH_PROFILE actions and decays exponentially. Negative heat would mean the territory has *less* state attention than the absence of any attention — physically meaningless. | The bound *is* the accumulation semantics — heat is a stock variable, never a flow with sign. |
| **`r + l + f = 1`** | Ternary consciousness `(r, l, f)` represents the *probability distribution* of a class's ideological state across three pure tendencies (revolutionary, liberal, fascist). The simplex constraint *is* the requirement that the distribution sum to unity. Components below 0 or above 1 are unrepresentable. | The bound *is* the probability-distribution contract on the `{r, l, f}` simplex. |
| **`α-smoothing inequality`** | Constitutional principle II.4 ("Quantities flux per tick. Coefficients α-smooth. Crisis = discontinuous coefficient reset, not gradual drift") — coefficients represent *historically averaged* material conditions (e.g., gamma in the gamma EMA represents the smoothed visibility ratio `gamma_III`). They cannot change faster than the smoothing rate permits without violating their definitional role as "history-aware." Crisis is the only legitimate exception. | The bound *is* the historicity contract on coefficients. |

This table is referenced from the Constitution Check post-design re-eval
in `plan.md`.

---

## §7. WorldState scale defaults

**Decision**: For the bound-invariant tests (US1, US2, US3), default
`max_entities=200` and `max_edges=2000` in the `WorldState` strategy.
These are an order of magnitude smaller than Spec 053's `max_hexes=25_000`
because:

- All four predicates are `O(N)` per check (one comparison per entity per
  predicate); raw cost is dominated by graph mutation, not invariant
  evaluation.
- The default profile budget is 30 s for the entire bound suite (4 test
  files × ~100 examples × 22 Systems for US2 = 8,800 trial runs in
  budget). At larger N the budget overflows.
- Falsification quality saturates well below `N=200`: bound violations are
  almost always single-entity / single-edge bugs that shrink to `N=1`
  during Hypothesis minimization.

The slow profile (`HYPOTHESIS_PROFILE=slow`) increases `max_entities` to
1,000 and `max_edges` to 10,000 for the nightly sweep.

**Rationale**: SC-005 fixes the time budget; the strategy parameters
follow from the budget, not the other way around. Larger N adds rare-bug
discovery surface but with diminishing returns once N covers the
canonical small graphs that the engine's own factories produce.

**Alternatives considered**:

- **Match Spec 053's `max_hexes=25_000`**: 100× the entity count for these
  tests; would blow the time budget. Rejected.
- **Per-test customization**: more flexible but adds maintenance.
  Defer until empirical CI timing data shows it's needed.

---

## §8. Test-file layout

**Decision**: One test file per User Story under
`tests/property/invariants/`, named `test_<predicate>.py`:

```
tests/property/invariants/
├── test_probability_bounds.py     # US1 (P1)
├── test_wealth_heat_bounds.py     # US2 (P2)
├── test_simplex_pipeline.py       # US3 (P2)
└── test_alpha_smoothing.py        # US4 (P3)
```

This matches the Spec 053 convention (`test_value_conservation.py`,
`test_h3_hierarchical.py`, …) and ensures `pytest -k` patterns are
predictable.

The harness modules live under a sibling `harness/` directory rather than
in each test file:

```
tests/property/harness/
├── __init__.py
├── bound_harness.py            # BoundInvariantHarness runner
├── crisis_inspector.py         # CrisisStateInspector
├── probability_discovery.py    # Pydantic walker for §1
├── alpha_discovery.py          # defines.py walker for §4
└── system_registry.py          # extracted from Spec 053's _discover_non_opt_out_*
```

**Rationale**: Spec 053 inlined its harness logic into the test files
because each invariant had its own bespoke check. This spec has *more*
cross-cutting plumbing (Pydantic introspection used by US1 and US3;
crisis classification used by US4 and potentially US3 multi-tick;
System registry used by US2 and US3). Extracting to a shared `harness/`
package is the lower-duplication choice.

---

## §9. Patterns reused from Spec 053

| Spec 053 artifact | Spec 054 use |
|-------------------|--------------|
| Profile registration in `tests/conftest.py` (`default`, `slow`) | Reuse as-is — no changes |
| Profile registration in `tests/property/conftest.py` (`dev`, `ci`, `nightly`) | Reuse as-is — no changes |
| `_tol(n, magnitude)` helper from `test_value_conservation.py:58` | Extract to `tests/property/harness/__init__.py` so US3 (simplex) and US4 (α-smoothing) can import. US1 and US2 use exact comparison and do not need it (per FR-008). |
| `_discover_non_opt_out_engine_systems` from `test_value_conservation.py:79` | Extract to `harness/system_registry.py`; US2 and US3 import. |
| `creates_value: ClassVar[bool]` opt-out marker | Sister marker `bypasses_bound_invariant: ClassVar[dict[str, str]]` per Q4 clarification. |
| `@composite` strategies in `tests/property/strategies/` | New strategies in same directory — no churn. |

---

## Open Questions Carried to Phase 1

None. All technical decisions resolved; spec FR-002 will be implemented
per §2 (two-layer hybrid: allow-list + drift warning); spec FR-005's
crisis classification will be implemented per §5
(`CrisisPhase.NORMAL or None ⇒ steady state`).

These two refinements do not invalidate the spec — they sharpen the
implementation contract. They are recorded here rather than rewritten
into the spec because both arise from production-code investigation that
post-dates the spec write-up; they belong in research, not in
requirements.
