# Feature Specification: Marx Value-Form Invariants

**Feature Branch**: `060-value-form-invariants`
**Created**: 2026-05-11
**Status**: Draft
**Input**: User description: "Pure numeraire invariance; MELT-mediated consistency;
TSSI/NI aggregate equalities; OCC-conditional wage asymmetry; productivity-shock
value-price decoupling — extended with software/numerical metamorphic invariants
(UUID relabeling, serialization round-trip, Markovian step semantics, H3
resolution round-trip) and Marxist sign/monotonicity invariants (proportional
c+v scaling, OCC monotonicity, Volume III equalization tendency)."

## Overview

The Babylon engine maintains two distinct value domains: a **labor-time domain**
(c/v/s in `LaborHours` on `ValueTensor4x3`) and a **money domain** (`Currency`
capital fields on `Organization`, aggregated at the hex via
`CountyEconomicState`). The bridge between them is **MELT** (`τ`,
`$ / labor-hour`), computed by `DefaultMELTCalculator` as
`τ = GDP / (employment × 2080)` per Axiom B3 of the TVT axiom catalogue.

Despite this two-domain architecture and considerable per-module unit-test
coverage, the engine currently has no executable check that the two domains
**stay coherent across a tick**, that the engine's numerical outputs are
invariant under software-irrelevant relabelings (UUIDs, monetary units, H3
resolution, serialization), or that classical Marxist sign/monotonicity
relationships hold across the simulated economy.

A bug in any one of: unit handling, MELT application, transformation logic,
sectoral wage propagation, hex aggregation, persistence round-tripping, or
tick semantics could pass every existing unit test and silently corrupt
downstream results. Individual modules verify their own internal invariants,
but no test asserts the **cross-domain, cross-tick, cross-resolution
consistency** that Marxian value theory **and** correct numerical software
both require.

This feature adds a property/metamorphic test bundle organised into seven
independently-testable user stories grouped into two families:

**Value-form invariants** (US1–US5):

1. **Numeraire invariance** — rescaling money preserves dimensionless ratios.
2. **MELT-mediated per-entity consistency** — money X equals labor-time X × τ.
3. **Aggregate value-price equalities** (TSSI/NI) — Σ money-profit = Σ surplus × τ;
   Σ money-price = Σ value × τ.
4. **OCC-conditional wage asymmetry** — uniform wage shocks differentially
   affect prices of production by organic composition.
5. **Productivity-shock value-price decoupling** — value changes immediately,
   prices re-equalize on a slower clock.

**Software & Marxist sign/monotone invariants** (US6–US7):

6. **Software metamorphic invariants** — UUID relabeling invariance,
   serialization round-trip identity, Markovian step semantics, H3 resolution
   round-trip conservation.
7. **Marxist sign/monotonicity invariants** — proportional c+v scaling at
   constant rate of surplus value, OCC monotonicity (sign property), Volume III
   profit-rate equalization (monotone variance reduction over many ticks).

All seven user stories deliver test invariants only — pytest properties and
metamorphic tests. They are read-only with respect to engine behavior: they
do not change what the engine computes, only what is asserted about it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Numeraire Invariance Property Test (Priority: P1)

A developer changing any monetary computation in the engine wants automatic
feedback when their change accidentally couples a "unitless" quantity (a
ratio) to the absolute scale of money. Concretely: if all money-denominated
fields (wages, constant capital, prices, MELT) are multiplied by a constant
`k > 0`, then every ratio in the engine — profit rate `s/(c+v)`, exploitation
rate `s/v`, organic composition `c/v`, MELT-normalized labor share, imperial
rent ratio — must be **bit-identical** to the unscaled run (or differ by at
most floating-point round-off, ≤ 1e-12 relative).

**Why this priority**: This is the deepest, cheapest, most theoretically
uncontroversial invariant. It catches an entire class of bugs (mixed units,
accidental currency conversion, hardcoded magic numbers in formulas) with
one parameterized property test. Required because spec 058's `Currency` type
does not, by itself, prevent unit-confusion: a developer can still write a
formula that subtracts `Currency` from a unitless quantity, or hardcodes
"1.0 USD" as a scaling factor, and the type system will not catch it.

**Independent Test**: Run a scenario tick twice — once with all monetary
inputs at base scale `k=1`, once with `k=100` (cents) and `k=0.01`. Assert
every dimensionless metric returned by `DerivedTensorMetrics` is bit-identical
(relative error ≤ 1e-12). Test exits non-zero if any ratio drifts.

**Acceptance Scenarios**:

1. **Given** a two-county scenario with non-trivial c, v, s, K, and MELT,
   **When** all monetary fields (constant capital, variable capital, wages,
   MELT τ) are multiplied by `k=100`, **Then** the resulting profit rate,
   exploitation rate, and OCC each match the base-scale values within 1e-12
   relative tolerance.

2. **Given** the same scenario, **When** the scaling factor is `k=0.01`,
   **Then** the ratios still match the base-scale values within 1e-12
   relative tolerance (no sign flip, no precision loss at small scale).

3. **Given** a scenario where MELT is itself scaled by `k`, **When** the tick
   runs, **Then** every entity's labor-time figures (in `LaborHours`) are
   **unchanged** by the monetary rescale (labor time is invariant under
   monetary numéraire choice).

4. **Given** a property-based test with Hypothesis generating random monetary
   scales `k ∈ [1e-3, 1e6]` and random valid economic configurations, **When**
   the test runs 100 examples, **Then** zero examples violate the invariance
   check.

---

### User Story 2 - MELT-Mediated Per-Entity Consistency (Priority: P1)

A developer modifying the MELT calculator, value tensor, or any system that
produces both money- and labor-time-denominated outputs wants an executable
check that within any single tick, for every entity (county tensor,
organization), the dimensional identity
`money_X = labor_time_X × τ` holds for `X ∈ {c, v, s, total_value}`.

**Why this priority**: This is the per-tick, per-entity dimensional invariant
that makes the MELT module's claim "τ bridges labor-time and money domains"
actually verifiable. Without it, the two domains can drift apart silently
and the simulation's economic outputs become uninterpretable. Per the feature
description, the property is "probably already tested somewhere in
`tests/unit/economics/melt/`" — and indeed `test_melt_calculator.py` exists.
The task is to (a) confirm the unit-level coverage and (b) **lift it to a
tick-level integration invariant** so the bridge is asserted after **all**
systems run, not just inside the MELT calculator's own unit tests.

**Independent Test**: For one tick of a Detroit-vertical-slice scenario,
after all systems have run, iterate every county and every productive
organization; assert `entity.money_X ≈ entity.labor_time_X × τ` within 1e-9
relative tolerance. Test reports the worst-offending entity and the
magnitude of the discrepancy.

**Acceptance Scenarios**:

1. **Given** a one-tick run on the two-county fixture with MELT τ = $65/hr,
   **When** the consistency check iterates every productive entity, **Then**
   for each entity `|money_X - labor_time_X × τ| / |money_X| < 1e-9` for X ∈
   {c, v, s, total_value}.

2. **Given** a tick where `DefaultMELTCalculator.get_melt(year)` returns
   `NoDataSentinel` (e.g., year out of range), **When** the consistency check
   runs, **Then** entities are skipped cleanly (warning emitted; test does
   not fail).

3. **Given** a scenario with one productive organization producing 100 hours
   of surplus and MELT = $65/hr, **When** the tick completes, **Then** the
   organization's money-form surplus equals $6500 ± $0.01 (penny tolerance).

4. **Given** the existing `tests/unit/economics/melt/` coverage, **When**
   this feature lands, **Then** a new test at the integration layer (e.g.,
   `tests/integration/economics/test_melt_consistency.py`) explicitly imports
   the tick output and asserts the cross-entity invariant.

---

### User Story 3 - TSSI/NI Aggregate Value-Price Equalities (Priority: P2)

A developer working on the transformation problem, prices of production, or
any distribution-side computation wants automatic feedback if their change
breaks the two New-Interpretation / TSSI invariants that Marxian value theory
claims hold even when sectoral money-prices diverge from sectoral
labor-values:

- **Aggregate profit-surplus equality**: Σ money-profit (over all entities)
  = (Σ labor-surplus) × τ.
- **Aggregate price-value equality**: Σ money-price (over all entities) =
  (Σ labor-value) × τ.

**Why this priority**: P2 because the engine's current transformation logic
(`TransformationDialectic`) is still under development; this invariant
becomes load-bearing once prices-of-production diverge sectorally from values.
Until then it holds trivially (because prices are proportional to values),
but having the test in place guards against the regression that would land
the day someone "fixes" the transformation to do sectoral redistribution and
accidentally breaks the aggregate.

**Independent Test**: After a tick, sum money-profit across all productive
entities, sum labor-surplus across the same entities, multiply the latter by
τ, and assert equality within 1e-6 relative tolerance. Then do the same for
money-price vs. labor-value × τ.

**Acceptance Scenarios**:

1. **Given** a scenario where prices = values × τ (proportional case, current
   engine behavior), **When** the test runs, **Then** both aggregate
   equalities hold with relative error < 1e-12 (trivially, by construction).

2. **Given** a scenario where the transformation engine has been activated
   and sectoral prices diverge from values (high-OCC sectors above value,
   low-OCC sectors below), **When** the test runs, **Then** both aggregate
   equalities still hold within 1e-6 relative tolerance (the redistribution
   is intra-aggregate only).

3. **Given** a scenario where, after a transformation change, sectoral
   redistribution introduces a systematic bias (total prices exceed total
   value × τ), **When** the test runs, **Then** the test fails with a
   diagnostic naming the discrepancy magnitude and (where computable) the
   sectoral contributions to the imbalance.

4. **Given** a property-based test that randomly perturbs sectoral c/v/s
   ratios while holding aggregates constant, **When** the test runs 50
   examples, **Then** zero examples violate aggregate equalities.

---

### User Story 4 - OCC-Conditional Wage-Shock Asymmetry (Priority: P2)

A developer modifying the price-of-production or wage-propagation logic
wants automatic detection of the "monetary scaling" failure mode: applying a
uniform wage increase that uniformly inflates all prices, instead of
differentially affecting prices of production based on each hex's organic
composition.

In the correct Volume-III behavior: a 10% wage increase (with constant
capital fixed) should **decrease** prices of production in high-OCC hexes
(those with relatively more constant capital, where wages are a smaller cost
share) and **increase** prices of production in low-OCC hexes. The pivot is
at the economy-wide average OCC. **If a uniform wage shock produces uniform
monetary scaling, the engine is implementing prices as `value × constant`,
not as proper Volume-III equalization** — that is the failure mode this test
catches.

**Why this priority**: P2 because it depends on a functional transformation
engine (same gate as US3). Critical signal when transformation is active;
SKIPs explicitly otherwise. Phrased as a metamorphic test: it asserts a
sign relationship between two paired runs, not a specific numerical outcome.

**Independent Test**: Run tick A with baseline wages. Run tick B with all
variable-capital (wage) flows multiplied by 1.10, constant capital identical.
For each hex, classify as high-OCC (OCC > national median) or low-OCC.
Assert: high-OCC hexes have `price_B / value_B < price_A / value_A` (price
ratio decreased); low-OCC hexes have the inverse.

**Acceptance Scenarios**:

1. **Given** a scenario with at least 5 hexes spanning a range of OCC values,
   **When** wages are uniformly raised 10%, **Then** at least 80% of high-OCC
   hexes show a decreased price/value ratio, and at least 80% of low-OCC
   hexes show an increased price/value ratio (relative to the national-median
   split).

2. **Given** the same scenario but with the engine in proportional-prices
   mode (no transformation), **When** wages are raised 10%, **Then** the test
   SKIPs with a documented reason — it does not fail; it does not silently
   pass.

3. **Given** a scenario where a developer has broken the transformation logic
   such that wage shocks produce uniform monetary scaling, **When** the test
   runs, **Then** ≤ 50% of high-OCC hexes show the expected decrease (well
   below the 80% threshold), and the test fails with a diagnostic naming
   the failure mode.

4. **Given** a property-based test generating random hex configurations with
   varied OCCs, **When** the test runs 20 examples, **Then** the median
   high-OCC-vs-low-OCC asymmetry is at least 0.1 (a measurable, non-trivial
   sign asymmetry).

---

### User Story 5 - Productivity-Shock Value-Price Decoupling (Priority: P3)

A developer modifying the SNLT (socially necessary labor time) recomputation
or the timing relationship between value updates and price-of-production
re-equalization wants automatic detection of bugs that conflate the two
clocks.

In the correct Marxian behavior, doubling productivity in one sector
should:
(a) **Immediately** halve the labor-value of that sector's output (SNLT per
unit falls by half — this is by definition).
(b) **Not** immediately halve the money-price of that sector's output. The
money-price falls only as competition equalizes — over multiple ticks. The
gap between (a) and (b) is the testable content of the value/price
distinction.

**Why this priority**: P3 because it depends on both the transformation
engine and a working SNLT recomputation pathway. It is the most theoretically
subtle of the five value-form invariants and is most likely to fail trivially
today (because SNLT is currently a per-tick recompute and transformation is
not yet fully wired). Lower priority does not mean lower value: when it
lights up, it lights up a class of bugs no other test catches.

**Independent Test**: Run a baseline tick. Run a paired tick where, just
before the tick starts, the SNLT (or `c+v` per unit) of one designated
sector is halved. Assert: in tick T+1, sector value is halved; sector
money-price is **not** halved (falls by strictly less); over ticks T+1
through T+5, sector money-price approaches but does not instantaneously
equal new value × τ.

**Acceptance Scenarios**:

1. **Given** a scenario with a productive sector having stable c, v, s,
   **When** the productivity of that sector is doubled at tick boundary T,
   **Then** in tick T+1 the sector's labor-value per unit is halved (within
   1e-9) **and** `new_price / old_price > 0.5 + ε` for some small ε > 0.

2. **Given** the same scenario simulated for T+1 through T+10, **When** the
   sector's money-price is plotted against `new_value × τ`, **Then** the
   price approaches the new-value-times-τ asymptotically (monotonically
   decreasing gap), demonstrating equalization without collapsing
   instantaneously.

3. **Given** an engine where a developer has broken sequencing such that
   prices and values update on the same clock (no decoupling), **When** the
   test runs, **Then** the test fails because `new_price / old_price ≈ 0.5`
   at T+1 with no gap — the precise failure mode the test exists to detect.

4. **Given** the engine in current state (transformation not yet active),
   **When** the test runs, **Then** it SKIPs with a documented reason, not
   silently passes.

---

### User Story 6 - Software Metamorphic Invariants (Priority: P1)

A developer changing any part of the engine — the world state model, the
graph adapter, persistence, h3 spatial indexing, tick semantics — wants
automatic feedback when their change introduces a hidden dependency on
**software-irrelevant** properties of the state: opaque entity UUIDs, the
absolute tick counter, the in-memory representation between persistence
boundaries, or the h3 resolution at which spatial aggregates are accumulated.

This story covers **four sub-invariants**, each independently testable and
each addressing a distinct failure mode:

(a) **UUID relabeling invariance.** Replace every entity UUID (string fields
typed as `UUID` or `str`-of-uuid) with a deterministic but different mapping
(e.g., `f"alias-{i}"` for the i-th entity by canonical order). Run a tick.
Every numerical output — every Currency value, every LaborHours value, every
profit rate, every aggregate — must be **bit-identical** to the baseline.
Only the string UUIDs themselves are allowed to differ. Catches: a system
that accidentally couples behavior to UUID lexicographic order; iteration-
order-dependent reductions over a set; ID-based randomness seeding that
should have used a domain-meaningful key.

(b) **Serialization round-trip identity.** Take a `WorldState`, serialize it
(via Pydantic `model_dump_json` or its persistence equivalent), deserialize
it back into a `WorldState`, and assert the two are equal under the engine's
defined notion of state equality. Then run a tick on each and assert
identical tick output. Catches: silent precision loss in serializers,
missing fields in `to_graph`/`from_graph` round-trips (a documented "common
gotcha" in `CLAUDE.md`), or persistence schemas drifting from in-memory
schemas.

(c) **Markovian step semantics.** The tick function `step(W_t) → W_{t+1}`
must depend only on `W_t`, never on the absolute tick number `t`. Operate
the same engine on two paired runs: run A starts from `W_t` with `t=100`;
run B starts from the **same state** with `t=10000`. Both produce the same
`W_{t+1}` modulo the explicit tick counter increment. Catches: a system that
gates behavior on `t % N == 0`; a formula that uses `t` as an input rather
than as a label; tick-counter leakage into deterministic randomness.

(d) **H3 resolution round-trip conservation.** Take a hex-indexed aggregate
(e.g., constant capital totals at H3 resolution R), aggregate it up one
resolution (R-1, parent hex sums), then disaggregate back to R (uniformly or
proportionally per the engine's defined splitter). Assert: the original
totals are recovered, and the parent-level total equals the sum of children
within numerical tolerance (Σ child = parent, lossless). Catches: hex
boundary arithmetic bugs, double-counting at H3 ring boundaries,
fractional-coverage errors in spatial joins.

**Why this priority**: P1. These are universal numerical-software invariants
that hold regardless of the engine's economic correctness. They are cheap
to write (each is a paired-run comparison) and catch deep, hard-to-debug
bugs that the Marxian invariants cannot see because they are pre-Marxian:
they are about software hygiene, not theory. Their failure would also
invalidate every other test result in the suite.

**Independent Test**: Four small paired-run tests, each on the two-county
fixture. Each takes < 5 s wall clock.

**Acceptance Scenarios**:

1. **Given** a tick on the two-county scenario, **When** every entity UUID is
   replaced with a deterministic non-equal alias (sub-invariant a), **Then**
   every Currency, LaborHours, and dimensionless ratio in the resulting state
   matches the baseline to bit-identity (relative error ≤ 1e-15).

2. **Given** a populated `WorldState`, **When** it is round-tripped through
   the serializer (sub-invariant b), **Then** the post-round-trip state is
   equal to the original under `WorldState.__eq__` (or an explicit semantic-
   equality helper); a one-tick run from each starting point yields identical
   output.

3. **Given** the engine run from `W_t` with two different absolute tick
   counters `t=100` and `t=10000` (sub-invariant c), **When** one tick of
   `step()` is applied, **Then** the resulting states are identical except
   for the tick counter itself — every payload, every numeric field, every
   event ordering.

4. **Given** an aggregate quantity (constant capital) at H3 resolution
   `R=7`, **When** it is rolled up to `R=6` and rolled back to `R=7` per
   the engine's splitter (sub-invariant d), **Then** the per-hex totals at
   `R=7` match the originals within 1e-9 relative tolerance, and the parent
   totals at `R=6` exactly equal the sum of children.

5. **Given** any of the four sub-invariants is broken by a deliberate bug
   (UUID-based iteration order, asymmetric serializer, tick-counter leakage,
   double-counted boundary hex), **When** the corresponding test runs,
   **Then** the test fails with a diagnostic naming the offending field and
   the magnitude of the violation.

---

### User Story 7 - Marxist Sign and Monotonicity Invariants (Priority: P2)

A developer changing the value tensor, the per-tick economic update, or the
inter-sectoral profit-rate equalization mechanism wants automatic feedback
when their change violates a **direction-of-effect** or **monotonicity**
property that Marxian value theory requires — even if it does not violate
the exact aggregate equalities of US3.

This story covers **three sub-invariants** that are weaker than the equality
invariants but stronger in coverage:

(a) **Proportional (c, v) scaling at constant rate of surplus value.**
If every entity's constant capital `c` and variable capital `v` are scaled
by the same positive factor `k`, **and** the rate of surplus value `s/v` is
held constant (so `s` scales by `k` automatically), then total value
`c + v + s` for every entity should scale by exactly `k`. Profit rate
`s/(c+v)`, organic composition `c/v`, and exploitation rate `s/v` should be
**unchanged**. Catches: a formula that breaks when `c` and `v` are both
doubled; a "saturating" non-linearity hidden in a production function;
accidental units mismatch between `c`-source and `v`-source numbers.

(b) **OCC monotonicity (sign property).** For any entity, monotonically
increasing `c` (with `v` fixed) must monotonically increase its organic
composition `c/v`; symmetrically, monotonically increasing `v` (with `c`
fixed) must monotonically decrease its OCC. The property is **sign-only**:
it does not pin a numeric outcome, only the direction. Catches: a derived-
metrics module that confuses numerator and denominator; an off-by-one bug
in a column index; a sign error in a difference formula.

(c) **Volume III equalization tendency (long-run monotone variance
reduction).** Over many ticks (e.g., 50 ticks) on a scenario where capital
is permitted to migrate between sectors per the engine's defined rule, the
**inter-sectoral variance of the profit rate** should **monotonically
decrease** (or at least: the moving-window variance over the last 10 ticks
should be strictly less than the moving-window variance over the first 10
ticks). This is a coarse but cheap test of the Volume III equalization
mechanism. It does not assert convergence to a specific profit rate, only
that the equalization tendency is operative. Catches: a capital-migration
module that is wired backwards (capital flowing toward high-profit-rate
sectors but failing to depress them); a mis-signed feedback loop; a missing
update step.

**Why this priority**: P2 because (a) is testable today (no transformation
engine needed) but (b) requires a stable derived-metrics path and (c)
requires the capital-migration mechanism to be active. They form a strict-
hierarchy ladder: (a) is the "you can't have a working engine without this"
sanity check; (b) is the sign-only direction check; (c) is the long-run
monotone test that lights up when Volume III logic is actually doing
something. All three are cheap and additive.

**Independent Test**: Three small tests, two paired-run, one long-run. Each
runs in < 15 s wall clock; (c) takes the longest (~10 s for 50 ticks).

**Acceptance Scenarios**:

1. **Given** a scenario where every entity has non-zero c, v, s, **When** c
   and v are scaled by `k=2` and s is rescaled to hold `s/v` constant (sub-
   invariant a), **Then** every entity's total value `c+v+s` is exactly
   `2 × baseline_total_value` within 1e-12 relative tolerance, and profit
   rate, OCC, and exploitation rate are unchanged within 1e-12.

2. **Given** a productive entity with baseline c, v (sub-invariant b),
   **When** c is monotonically increased from baseline through 11 evenly-
   spaced points spanning ±50% of baseline (with v fixed), **Then** the
   reported OCC is strictly monotone non-decreasing across the 11 points;
   the same holds (strictly monotone non-increasing) when v is varied with
   c fixed.

3. **Given** a 50-tick run on a scenario with active capital migration
   (sub-invariant c), **When** the inter-sectoral variance of the profit
   rate is computed for ticks 1–10 (var_early) and 41–50 (var_late),
   **Then** `var_late < var_early`. Diagnostic also reports both numbers
   and the percent reduction.

4. **Given** sub-invariant (c) on an engine where capital migration is
   disabled (proportional-prices mode), **When** the long-run test runs,
   **Then** it SKIPs with a documented reason, not silently passes.

5. **Given** sub-invariant (b) is broken by a deliberate bug (`organic_
   composition` returns `v/c` instead of `c/v`), **When** the test runs,
   **Then** the monotonicity assertion fails and the diagnostic names the
   sign-flip.

---

### Edge Cases

- **Zero MELT / `NoDataSentinel`**: When `DefaultMELTCalculator.get_melt(year)`
  returns `NoDataSentinel`, all MELT-dependent invariants (US2, US3, US4, US5)
  skip per-entity assertions cleanly (warning, not failure). The sentinel is
  a *known-acceptable* state.

- **Degenerate tensors** (`c=0` or `v=0` in a department): ADR-037 already
  documents such tensors as by-design exclusions. The invariants in this
  spec skip degenerate entities with the same convention. For US7(b), a
  zero-`v` entity is mathematically excluded (division by zero); the test
  uses non-degenerate fixtures.

- **Currency precision**: All money values use `Currency` (Pydantic-
  constrained numeric type). Cent-level rounding is acceptable for US2
  (penny tolerance); ratio-level tests in US1 and US6 use 1e-12 (US1) or
  1e-15 (US6 a/c) relative tolerance.

- **Empty scenario**: Two-county vertical slice is the minimum bar. A
  zero-entity tick is undefined for these invariants; tests fail fast with
  a clear "no productive entities" diagnostic.

- **Numeric scale extremes**: US1 property tests bound monetary scale `k ∈
  [1e-3, 1e6]`. Outside that band, IEEE-754 round-off can exceed the 1e-12
  tolerance.

- **Transformation engine inactive**: US3, US4, US5, US7(c) detect this and
  SKIP rather than report false-passes. The skip reason references this
  spec so the remediation path is discoverable.

- **Random property-test seed**: All Hypothesis-driven tests use a fixed
  derandomization seed in CI (per existing project policy from spec 053) so
  failures are reproducible.

- **UUID relabeling edge case** (US6 a): Some entity IDs may be referenced
  by string in adapter dicts, observer event payloads, or trace CSV columns;
  the relabel must apply consistently across **all** references in a
  `WorldState`, not just the primary identifier fields. The test fixture
  performs the full sweep; partial relabel is itself a bug surface and is
  reported.

- **Serialization round-trip edge case** (US6 b): If a `WorldState` field
  is a computed property (no setter), the deserializer must compute it on
  load. Mismatched computed fields are reported with a diagnostic naming
  the field and both values.

- **H3 splitter convention** (US6 d): The engine must declare its
  disaggregation rule (uniform, area-weighted, or population-weighted). The
  test reads this rule from configuration. If no rule is declared, the test
  fails fast with a "splitter rule not declared" diagnostic.

- **Markov tick semantics edge case** (US6 c): The only field that may
  legitimately differ between paired runs is the tick counter itself.
  Trace-stamping with absolute tick (`tick=N` in trace CSV) is allowed
  insofar as the **payload** does not depend on `N`; if it does, that is
  the bug.

- **Long-run equalization edge case** (US7 c): If the scenario has only one
  productive sector, inter-sectoral variance is undefined; the test fails
  with a clear "need ≥ 2 productive sectors" diagnostic.

## Requirements *(mandatory)*

### Functional Requirements

#### Value-Form Invariants (US1–US5)

- **FR-001**: System MUST provide a test that runs a single simulation tick
  at two monetary scales `k=1` and `k=100`, and asserts that every
  dimensionless ratio in `DerivedTensorMetrics` (profit_rate_flow,
  profit_rate_stock, organic_composition, exploitation_rate) is identical
  within 1e-12 relative tolerance between the two runs.

- **FR-002**: System MUST provide a Hypothesis-property test for FR-001
  that generates random valid economic configurations and random scale
  factors `k ∈ [1e-3, 1e6]`, runs ≥ 100 examples per CI invocation, and
  reports the first failing example reproducibly via the existing
  `.hypothesis/` example DB.

- **FR-003**: System MUST provide an integration-layer test that, after one
  tick on a representative scenario, iterates every productive entity
  (county tensor + organization) and asserts `|money_X - labor_time_X × τ| /
  |money_X| < 1e-9` for `X ∈ {c, v, s, total_value}`, where τ is the
  tick's MELT.

- **FR-004**: System MUST cleanly skip per-entity MELT-consistency
  assertions (FR-003) when `DefaultMELTCalculator.get_melt(year)` returns
  `NoDataSentinel`, emitting a `pytest.skip` with a documented reason —
  not silently passing.

- **FR-005**: System MUST provide a tick-level test that asserts the two
  TSSI/NI aggregate equalities: `Σ money_profit = (Σ labor_surplus) × τ`
  and `Σ money_price = (Σ labor_value) × τ`, both within 1e-6 relative
  tolerance, over all productive entities in the scenario.

- **FR-006**: System MUST provide a metamorphic test for OCC-conditional
  wage-shock asymmetry: run a paired (baseline, +10%-wage) tick, classify
  hexes as high-OCC or low-OCC by national-median split, and assert at
  least 80% of high-OCC hexes show a decreased price/value ratio while at
  least 80% of low-OCC hexes show an increased ratio.

- **FR-007**: System MUST provide a metamorphic test for productivity-
  shock value-price decoupling: halve SNLT-per-unit in one designated
  sector at tick boundary T, assert (a) labor-value is halved at T+1
  within 1e-9 and (b) money-price has fallen strictly less than half at
  T+1, and (c) the gap asymptotically closes over ticks T+1..T+5.

- **FR-008**: System MUST detect when the transformation engine is in its
  "proportional prices" (pre-transformation) mode, and cause FR-005 (in
  its redistribution-sensitive form), FR-006, FR-007, and FR-019 tests to
  SKIP with a documented reason rather than report false-passes.

#### Software Metamorphic Invariants (US6)

- **FR-013**: System MUST provide a UUID-relabeling invariance test that
  replaces every UUID-typed field in a populated `WorldState` with a
  deterministic non-equal alias, runs one tick, and asserts every
  numerical field of the resulting state is bit-identical to the
  baseline (relative error ≤ 1e-15).

- **FR-014**: System MUST provide a serialization round-trip identity
  test that serializes a `WorldState`, deserializes it, and asserts (a)
  the round-tripped state is semantically equal to the original, and (b)
  a one-tick run from each starting point produces identical output.

- **FR-015**: System MUST provide a Markovian-step-semantics test that
  runs `step(W_t)` on identical states with two different absolute tick
  counters (`t=100` and `t=10000`) and asserts the resulting `W_{t+1}`
  states are identical except for the tick counter itself.

- **FR-016**: System MUST provide an H3-resolution-round-trip test that
  takes an aggregate at H3 resolution R, rolls it up to R-1 and back
  down to R per the engine's declared splitter rule, and asserts (a)
  per-hex totals at R are recovered within 1e-9 relative tolerance and
  (b) parent totals at R-1 exactly equal the sum of children.

#### Marxist Sign / Monotonicity Invariants (US7)

- **FR-017**: System MUST provide a proportional-(c, v)-scaling test that
  scales c and v by `k=2` while holding `s/v` constant, and asserts (a)
  every entity's total value scales by exactly k within 1e-12, and (b)
  profit rate, OCC, and exploitation rate are unchanged within 1e-12.

- **FR-018**: System MUST provide an OCC monotonicity test that varies c
  through 11 evenly-spaced points with v fixed, and asserts OCC is
  strictly monotone non-decreasing; symmetrically, varies v with c fixed
  and asserts OCC is strictly monotone non-increasing.

- **FR-019**: System MUST provide a Volume III equalization tendency test
  that runs ≥ 50 ticks on a scenario with active capital migration and
  asserts the inter-sectoral profit-rate variance over the last 10 ticks
  is strictly less than the variance over the first 10 ticks. Test
  SKIPs cleanly when capital migration is inactive.

#### Cross-Cutting Requirements

- **FR-009**: System MUST run all invariant tests on the project's
  standard fast gate (`mise run test:unit` plus `test:int`) without
  requiring AI models, external services, or non-local databases. Each
  individual test (excluding US7-c long-run test) MUST complete in under
  10 seconds wall-clock; the US7-c long-run test MUST complete in under
  60 seconds.

- **FR-010**: Each failing invariant test MUST produce a diagnostic
  message naming (a) the offending entity or aggregate, (b) the
  numerical magnitude of the violation, and (c) a pointer (URL or path)
  to this spec or its successor ADR.

- **FR-011**: System MUST NOT alter engine behavior. All work is test-
  only: new tests, fixtures, helpers under `tests/`. No `src/babylon/`
  file changes for production behavior; helper utilities for tests may
  live under `tests/_helpers/` or be imported from existing
  `tests/factories/`. The one exception: if FR-016 reveals the engine
  has no declared H3 splitter rule, declaring the rule as a single named
  constant under `babylon.config` is permitted.

- **FR-012**: All invariant tests MUST preserve the byte-equality
  invariant from spec 059 SC-007: `mise run sim:trace 200` continues to
  emit a byte-identical CSV vs. the baseline.

- **FR-020**: All Hypothesis-driven tests MUST set
  `derandomize=true` (or equivalent fixed-seed convention from spec 053)
  in CI mode so failing examples are reproducible across runs.

- **FR-021**: All tests that depend on the transformation engine being
  active (FR-005 redistribution arm, FR-006, FR-007, FR-019) MUST share
  a single helper utility that probes engine state and returns a
  `TransformationModeFlag` (active / inactive). The helper MUST be the
  sole authority on the gate; each test must not re-detect the flag
  itself.

- **FR-022**: System MUST add one `pytest.mark` (e.g., `@pytest.mark.
  invariant`) to all tests in this bundle so they can be run as a group
  via `poetry run pytest -m invariant`. The marker MUST also be
  registered in `pyproject.toml` to avoid the "unknown marker" warning.

### Key Entities *(include if feature involves data)*

- **MonetaryRescaling**: A test-only operation that takes a `WorldState`
  and a positive scalar `k`, returns a new `WorldState` with all
  `Currency`-typed fields (organization c and v, MELT τ, prices)
  multiplied by `k`. Pure; reversible by passing `1/k`. Idempotent on
  labor-time fields. Used by US1 / FR-001 / FR-002.

- **ConsistencyReport**: A test-only diagnostic returned by the MELT
  consistency check, containing `worst_entity`, `max_relative_error`,
  `n_entities_checked`, `n_skipped_no_data`, and (when failing) a
  pointer to the offending entity's c/v/s and money values. Used by
  US2 / FR-003.

- **TransformationModeFlag**: A test-only probe that inspects the
  current state of `TransformationDialectic` and reports whether the
  engine is in proportional-prices mode (skip US3/US4/US5/US7c) or
  full-transformation mode (run them). Single-source-of-truth per
  FR-021.

- **MetamorphicPair**: A pair of `(baseline_world, perturbed_world)`
  produced by an explicit perturbation function (`+10% wages`, `halve
  SNLT in sector S`, `relabel UUIDs`, `serialize-and-load`, `shift
  tick counter`, `roll-up-and-down-h3`), where the test asserts a
  *relationship between* the two outputs rather than absolute values.

- **UUIDRelabeler**: A test-only function `(world, alias_fn) → world'`
  that produces a `WorldState` with every UUID-typed field replaced by
  `alias_fn(uuid)`. The relabeling must be a bijection within the
  state. Used by US6(a) / FR-013.

- **H3SplitterRule**: A configuration constant naming the
  disaggregation rule (`uniform`, `area_weighted`, `population_
  weighted`). Read by the test at FR-016 to drive the round-trip; if
  not declared in `babylon.config`, the test fails fast.

- **ProfitRateVarianceTrace**: A test-only collector that runs the
  engine for N ticks and records the inter-sectoral profit-rate
  variance at each tick. Used by US7(c) / FR-019 to compute
  `var_early` vs. `var_late`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Numeraire invariance (FR-001/FR-002) holds with relative
  error ≤ 1e-12 on every tick of the two-county scenario, for monetary
  scale factors `k=1`, `k=100`, and `k=0.01`. Verified by an automated
  test that fails the run if drift exceeds tolerance.

- **SC-002**: MELT-mediated per-entity consistency (FR-003) holds with
  relative error ≤ 1e-9 on every productive entity in the Wayne County
  scenario for one tick when MELT is available. The integration test
  reports the worst-offending entity and its delta.

- **SC-003**: TSSI/NI aggregate equalities (FR-005) hold with relative
  error ≤ 1e-6 on the two-county scenario for one tick under the
  current proportional-prices behavior. Trivial today; load-bearing
  once transformation is active.

- **SC-004**: OCC-conditional wage-shock asymmetry (FR-006) detects the
  "uniform monetary scaling" bug when intentionally introduced behind a
  feature flag: the test fails with ≤ 50% of high-OCC hexes showing
  the expected decrease (below the 80% threshold).

- **SC-005**: Productivity-shock decoupling (FR-007) detects the "same-
  clock" bug when intentionally introduced behind a feature flag: the
  test fails because `new_price / old_price ≈ 0.5` at T+1 with no gap.

- **SC-006**: All invariant tests complete in under **120 seconds**
  total wall-clock on the project's fast gate (`mise run check`). The
  US7-c long-run test alone must complete in under 60 s; all others
  must complete in under 10 s each. Verified by pytest's `--durations`
  output captured in `reports/test-results/{unit,int}/`.

- **SC-007**: All invariant tests run green at landing with zero
  unintentional skips. Intentional skips (transformation-inactive
  gates in US3/US4/US5/US7c, NoDataSentinel-MELT gate in US2) report a
  SKIP reason that references this spec or its successor ADR. The
  fast-gate report shows ≤ 5 SKIPs attributable to this spec.

- **SC-008**: `mise run sim:trace 200` produces a CSV byte-identical
  to the pre-spec-060 baseline (the byte-equality invariant inherited
  from spec 059). Verified by `cmp -s` in the quickstart.

- **SC-009**: UUID-relabeling invariance (FR-013) holds with relative
  error ≤ 1e-15 on the two-county scenario for one tick. Verified by
  an automated test that fails the run if any numeric field diverges.

- **SC-010**: Serialization round-trip identity (FR-014) holds:
  `WorldState.model_dump_json` followed by `model_validate_json`
  returns a state semantically equal to the original on every field
  except non-deterministic UUIDs (if any), and a paired one-tick run
  produces identical output. Verified automatically.

- **SC-011**: Markovian step semantics (FR-015) holds: running the
  same `step()` on identical states with `t=100` and `t=10000`
  produces `W_{t+1}` states identical in every payload field
  (excluding the tick counter itself). Verified automatically.

- **SC-012**: H3 round-trip conservation (FR-016) holds: rolling up
  and down through one H3 resolution recovers per-hex totals within
  1e-9 relative tolerance and parent totals exactly equal Σ children.
  Verified automatically.

- **SC-013**: Proportional c+v scaling (FR-017): scaling c and v by
  `k=2` at constant `s/v` scales every entity's total value by
  exactly 2 within 1e-12 relative tolerance; OCC, profit rate, and
  exploitation rate unchanged within 1e-12. Verified automatically.

- **SC-014**: OCC monotonicity (FR-018): varying c through 11
  evenly-spaced points (v fixed) produces strictly non-decreasing
  OCC across the points; symmetric for v varied (c fixed). Verified
  automatically.

- **SC-015**: Volume III equalization tendency (FR-019): inter-
  sectoral profit-rate variance over the final 10 ticks of a 50-tick
  run is strictly less than the variance over the first 10 ticks on
  a scenario with active capital migration. Verified automatically.
  SKIPs cleanly with a documented reason when capital migration is
  inactive.

- **SC-016**: At least one invariant test in this bundle catches a
  real bug between landing and the next minor release. This is the
  only outcome-based metric in this list; the others are correctness
  criteria. SC-016 is verified retrospectively in the post-merge ADR.

## Assumptions

- **MELT is national**: Per `DefaultMELTCalculator` and Axiom B4,
  there is one national τ per tick. Tests use the national MELT for
  all entities; no regional MELT is assumed or computed. If a future
  change introduces regional MELT, FR-003 and FR-005 must be
  reformulated.

- **Productive vs. unproductive entities**: Only productive entities
  (non-zero c, v, s in the value tensor; productive sectors in
  `Organization.economic_role`) are subject to value-price assertions.
  Test fixtures explicitly tag which entities are productive.

- **Currency type**: Money-denominated fields use Pydantic-
  constrained `Currency`. The 1e-12 numeraire-invariance tolerance
  (US1) and 1e-15 UUID-relabeling tolerance (US6 a) are within IEEE-
  754 precision in the assumed scale band `k ∈ [1e-3, 1e6]`.

- **TSSI/NI framework**: The two aggregate equalities in US3 assume
  a Temporal-Single-System-Interpretation / New-Interpretation reading
  of Marx, consistent with the engine's MELT-based architecture.
  Sraffian and dual-system Steedman readings are out of scope.

- **Transformation engine still maturing**: US3, US4, US5, US7(c)
  SKIP today because `TransformationDialectic` does not yet perform
  sectoral redistribution. Skips light up automatically when the
  transformation engine matures.

- **Capital migration mechanism**: US7(c) assumes the engine has, or
  will have, a defined inter-sectoral capital-migration step. If
  none exists, US7(c) SKIPs with a clear reason; landing US7(c) does
  not require landing the migration mechanism itself.

- **Hypothesis is available**: Spec 053 added Hypothesis as a dev
  dependency. This spec relies on it for FR-002. No new dependency
  required.

- **`WorldState.model_dump_json` is the canonical serializer for FR-
  014**: Other serializers (Postgres TraceRecorder, archival
  Parquet) are not in scope. If they drift from Pydantic
  serialization, a follow-up spec is required.

- **H3 splitter rule already declared OR declared as part of FR-
  016**: If the engine does not currently expose a named
  disaggregation rule, FR-011 permits declaring one constant in
  `babylon.config` (the only allowed production-side change). If no
  rule is appropriate, FR-016 is deferred to a follow-up spec.

- **No new persistence**: All tests run in-memory against existing
  `WorldState`, `ValueTensor4x3`, and `HexGrid`; no new DB tables,
  no new file formats.

- **No new MCP / network calls**: Tests are fully offline. CI
  parity is preserved.

- **Reuses existing scenarios**: Two-county fixture from
  `scenarios/two_node.py` and Wayne County fixture from
  `scenarios/wayne_county.py` are the test substrate. No new
  scenario factories are required.

- **"Bit-identical" is a relative-error claim**: SC-001's and SC-
  009's "bit-identical" is a 1e-12 / 1e-15 relative-error claim, not
  exact IEEE-754 equality. The deepest tests that would produce
  strict bit-equality require fixed-point arithmetic, which the
  engine does not use.

- **Out of scope (deferred)**: A combinatorial property-based test
  exploring the joint distribution of (monetary scale × OCC
  distribution × productivity shock × UUID relabeling × tick offset
  × H3 resolution) is deferred — too many interacting parameters
  for one CI-friendly bundle. This spec covers each invariant
  individually; combinatorial coverage is a future spec.

- **No existing test is modified**: New tests are additive. Old skip
  patterns (ADR-037) are unchanged.
