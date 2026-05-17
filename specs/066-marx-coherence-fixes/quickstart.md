# Quickstart: Spec-066 Marx-Coherence Fixes

**Feature**: 066-marx-coherence-fixes
**Audience**: Operator, researcher, CI engineer
**Prerequisites**: Spec-065 quickstart works end-to-end (`mise run sim:e2e-michigan` produces a clean artifact bundle)

---

## What changed since spec-065

Spec-065 shipped the bridge surface and persistence pipeline; spec-066 fixes the **economic and political coherence** of the persisted output. After spec-066, the canonical Michigan-Canada 520-tick run produces output that satisfies Marx's accounting identities (W = c + v + s, GDP = v + s) and shows consciousness drifting under material conditions for the first time.

| Field | Spec-065 (audit-only) | Spec-066 |
|---|---|---|
| `summary.terminal_state.total_s` | $0 (degenerate) | $5–8B/week (Michigan-statewide) |
| `profit_rate` per county | 0.0 everywhere | ~0.05–0.15 (BEA-broad-v band) |
| `exploitation_rate` per county | 0.0 everywhere | ~0.10–0.30 |
| `ideology_f` (fascism axis) drift | uniform 0.225 across all 83 counties × 520 ticks | drifts ≥5% over 520 ticks; Wayne ≠ Keweenaw |
| `summary.events` count | 0 | 50+ (BIFURCATION_THRESHOLD, CONSCIOUSNESS_SHIFT, FASCIST_REVANCHISM) |
| `summary.performance.per_system_ms` | `{}` empty | 21 entries (one per engine system), all > 0 |
| `total_employment_proxy` (state) | 552K (8× undercount) | ~3.5–4.8M (within ±15% of BLS) |
| `energy_stock` vs `raw_material_stock` | byte-identical | distinct for ≥50% of counties |
| Wallclock budget | 48 min measured (no engine) | ≤90 min (engine + bridge; SC-011) |
| Initial ideology | (0.36, 0.41, 0.225) accidental, undocumented | (0.05, 0.50, 0.45) explicit placeholder per ADR043 |

---

## Section 1 — Validating the Marx identities post-run

After running `mise run sim:e2e-michigan`, point this Python snippet at the artifact directory:

```python
import csv, json
from pathlib import Path

bundle = Path("/path/to/reports/sim-runs/<timestamp>")
summary = json.loads((bundle / "summary.json").read_text())
trace = list(csv.DictReader((bundle / "trace.csv").open()))

# SC-001: total_s strictly positive
total_s = summary["terminal_state"]["total_s"]
assert total_s > 0, f"Spec-066 SC-001 FAILED: total_s = {total_s}"
print(f"✅ SC-001: total_s = ${total_s:,.0f}/week")

# SC-002: state rate of profit in [0.05, 0.50]
total_c = summary["terminal_state"]["total_c"]
total_v = summary["terminal_state"]["total_v"]
p_prime = total_s / (total_c + total_v)
assert 0.05 <= p_prime <= 0.50, f"Spec-066 SC-002 FAILED: p' = {p_prime}"
print(f"✅ SC-002: state rate of profit p' = {p_prime:.3f}")

# SC-004: per-county value-added identity (v + s = GDP within ±5%)
# Note: SC-003 (c + v + s = W) was dropped per /speckit.analyze U1 because the
# identity becomes tautological after the FR-001 formula fix (c + v + s reduces
# to c + GDP/52 by construction; there is no independent W to test against).
violations_value_added = []
for row in trace:
    if row.get("entity_kind") != "county":
        continue
    c = float(row["c"]); v = float(row["v"]); s = float(row["s"])
    # GDP is implied from c via the hex hydrator: c = 0.5 × GDP/52, so GDP/52 = 2c.
    gdp_per_week_implied = 2 * c
    relative_err = abs((v + s) - gdp_per_week_implied) / gdp_per_week_implied if gdp_per_week_implied > 0 else 0
    if relative_err > 0.05:
        violations_value_added.append((row["entity_id"], row["tick"], relative_err))

assert not violations_value_added, f"Spec-066 SC-004 FAILED: {len(violations_value_added)} rows violate v + s = GDP ± 5%"
print(f"✅ SC-004: {len(trace)} rows satisfy v + s = GDP ± 5%")
```

---

## Section 2 — Inspecting consciousness evolution

```python
import csv
from pathlib import Path
from collections import defaultdict

bundle = Path("/path/to/reports/sim-runs/<timestamp>")
trace = list(csv.DictReader((bundle / "trace.csv").open()))

# SC-005: at least one county shows ≥5% relative drift in ideology_f
by_county_tick = defaultdict(dict)
for row in trace:
    if row.get("entity_kind") != "county":
        continue
    by_county_tick[row["entity_id"]][int(row["tick"])] = float(row.get("ideology_f") or 0)

pass_sc005 = False
for county, tick_to_f in by_county_tick.items():
    f_0 = tick_to_f.get(0, 0)
    f_519 = tick_to_f.get(519, 0)
    if f_0 > 0:
        rel_change = abs(f_519 - f_0) / f_0
        if rel_change >= 0.05:
            pass_sc005 = True
            print(f"✅ SC-005: county {county} ideology_f drifted {rel_change*100:.1f}% over 520 ticks")
            break
assert pass_sc005, "Spec-066 SC-005 FAILED: no county shows ≥5% ideology_f drift"

# SC-006: Wayne (26163) and Keweenaw (26083) Pearson < 0.95
def pearsonr(xs, ys):
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = (sum((x - mx) ** 2 for x in xs)) ** 0.5
    den_y = (sum((y - my) ** 2 for y in ys)) ** 0.5
    return num / (den_x * den_y) if den_x * den_y > 0 else 1.0

ticks = sorted(by_county_tick["26163"].keys())
wayne = [by_county_tick["26163"][t] for t in ticks]
keweenaw = [by_county_tick["26083"][t] for t in ticks]
r = pearsonr(wayne, keweenaw)
assert r < 0.95, f"Spec-066 SC-006 FAILED: Wayne-Keweenaw Pearson = {r}"
print(f"✅ SC-006: Wayne-Keweenaw ideology_f Pearson = {r:.3f} (< 0.95)")
```

**Important caveat per Clarifications Q4**: this is the **un-organized canonical run** — no SOLIDARITY edges, no player verbs, no organizing infrastructure. ConsciousnessSystem routes ALL agitation to the fascism axis (`ideology_f`). The `ideology_r` (revolutionary) axis stays low. This is theoretically correct per Marx + the project's MLM-TW frame for un-organized US 2010-2020.

To see revolutionary trajectories, a future spec must add either:
- A scenario loader for SOLIDARITY edges from real US union density data, OR
- Player-verb integration (Mobilize, Organize, Educate per Constitution V), OR
- A background-organizing system that simulates ambient mutual aid at low rates

---

## Section 3 — Comparing the spec-065 baseline vs the spec-066 baseline

```bash
# After both spec-065 and spec-066 baselines have been generated:
diff <(jq '.terminal_state' tests/baselines/michigan-e2e-spec065.json) \
     <(jq '.terminal_state' tests/baselines/michigan-e2e.json)
```

Expected diff (headline — full diff has more):

```diff
-  "total_s": 0,
+  "total_s": 5840000000,
-  "total_population": null,
+  "total_population": 4234000,
-  "max_tension": 0.0,
+  "max_tension": 0.32,
```

The `total_s` going from $0 → $5–8B/week is the headline visible spec-066 outcome. CI's `qa:e2e-regression` gate will compare against the spec-066 baseline; once it ships, spec-067 / 068 work that intentionally changes simulation behavior must regenerate this baseline.

---

## Section 4 — Running the canonical pipeline

Same operator command as spec-065:

```bash
BABYLON_SLOW_TESTS=1 mise run sim:e2e-michigan
```

Expected runtime: **60–90 minutes** (vs spec-065's 48 min; the engine adds ~50–500 ms/tick, but the dominant cost is still the bridge's per-tick SQLite reads — see Phase 0 R8 + spec-069 follow-up).

Successful exit:
- `reports/sim-runs/<timestamp>/{trace.csv, summary.json, manifest.json}`
- `tests/baselines/michigan-e2e.json` refreshed via `--write-baseline` (spec-065 T085)
- All 15 SC checks pass (run the snippets in Sections 1 + 2 above to verify)

If `total_s` is still 0 after the run:
1. Check that the hex hydrator formula change shipped (`s = max(0, GDP/52 - v)`, NOT `- v - c`)
2. Check that the QCEW `industry_id = 1` filter shipped
3. Run `poetry run pytest tests/integration/test_marx_identities.py -v` for granular failure messages

If `ideology_f` doesn't drift:
1. Check that `engine.run_tick(...)` is actually being called from the runner (SC-010 — `summary.performance.per_system_ms` should have 21 entries)
2. Check that EXPLOITATION edges were seeded at `hydrate_initial` (without them, ImperialRentSystem can't extract Φ → no agitation generated)
3. Check that `defines.consciousness.routing_scale ≥ 0.2` (per FR-027 + Phase 0 R4)

---

## Section 5 — Differences from spec-065 quickstart

| Section | Spec-065 | Spec-066 |
|---|---|---|
| What's running per tick | "ConservationAuditor running end-of-tick", "EventCapture collecting every EventBus.publish() call" — but engine NOT actually invoked | All 21 engine systems actually run per tick; events actually publish; auditor actually evaluates |
| Initial ideology | Accidental defaults (~0.36, 0.41, 0.225) inherited from create_proletariat()/create_bourgeoisie() | Explicit (0.05, 0.50, 0.45) per ADR043 — cc=0.1, ni=0.5 |
| Wayne ≠ Keweenaw | Both byte-identical (engine deferred) | Distinct ideology_f trajectories |
| What's deferred | "spec-066: full SimulationEngine integration" | "spec-067 (QCEW), spec-068 (BEA I-O), spec-069 (SQLite caching), future spec for SOLIDARITY seeding / player verbs" |

### Ideology baseline placeholder — read this first

Every county at tick 0 starts at the **EXPLICIT PLACEHOLDER** ternary
`(ideology_r=0.05, ideology_l=0.50, ideology_f=0.45)`, materialized
from a single shared
`IdeologicalProfile(class_consciousness=0.1, national_identity=0.5)`
via the bridge mapping `r = cc * (1 - ni); f = ni * (1 - cc); l = 1 - r - f`.

**This is a placeholder.** It does NOT reflect 2010 per-county political
diversity — Wayne (Detroit) and Keweenaw start at the SAME ideology, and
real per-county drift over 520 ticks is small. The placeholder exists
because per-county data-driven seeding (ACS attitudes + 2010 election
returns + NLRB union density + ...) is a substantial future spec on its
own; spec-066 prioritized fixing the SURPLUS-VALUE bug + engine wiring
first. See [ADR043](../../ai-docs/decisions/ADR043_ideology_baseline_placeholder.yaml)
for the full rationale (why these specific numbers, what was rejected,
what "replace_when" looks like).

Tests that lock in this placeholder:
- `tests/integration/test_engine_bridge.py::test_tick_0_ideology_uniform_across_counties`
- `tests/integration/test_engine_bridge.py::test_ternary_simplex_preserved_at_hydrate`
- `tests/unit/engine/test_factories_ideology_seed.py::test_uniform_baseline_solves_to_target_ternary`

---

## Walkthrough verification

This quickstart will be walked through end-to-end as part of the spec-066 final commit (mirroring spec-065 T086). Until then, it's a draft target — discrepancies between this doc and the actual implementation will be reconciled before spec-066 ships.
