# A7 static-economy R-PROOF — per-tick flow accrual (owner item 25 pt. 2)

**Lane:** A7 — spec-109 (Option B, owner-approved).
**Worktree/branch:** `feature/109-static-economy`, off `dev@5cfcd46b`.
**Postgres:** shared `babylon_test` @ localhost:5433.

This is a partial proof authored by the implementing agent. Parts 0, 1, 5 are
complete (empirically verified in this worktree). Parts 2, 3, 4, 6 are the
orchestrator's responsibility (520-tick canonical run + A/B determinism) and
are left as explicit TODO sections below — **not run here**, per the lane
brief ("Do NOT run the 520-tick canonical yourself").

---

## Part 0 — WHAT changed since the last baseline

`tests/baselines/detroit-tri-county-5t.json` (the qa:e2e-regression baseline)
and `tests/baselines/storage-budget-5t.json` were last content-updated at
`628cbc7c` (2026-07-04, "update detroit-tri-county-5t for BEA share wiring").
The most recent commit to **re-verify** (not regen) both baselines
byte-identical against a real run is `b57faee6` (2026-07-09, the tick-52
`Territory.county_fips` fix, owner item 25 pt. 1) — its commit message
records "detroit-tri-county completes 55 ticks past tick 52... qa:regression
5/5 byte-identical."

Commits between `b57faee6` and this worktree's branch point (`dev@5cfcd46b`)
that touch any file this lane's change also touches:

| Commit | What | Could touch A7's surface? |
|---|---|---|
| `c5c19e21` (spec-109 A6) | Seeds the spec-070 balkanization/faction layer into web sessions; touches `world_state.py` | Only the sovereign/faction reconstruction path (`_reconstruct_sovereign`/`_reconstruct_faction`) and `_add_political_nodes`. Does not touch `_reconstruct_territory`, `TERRITORY_EXCLUDED_FIELDS`, or `TickDynamicsSystem`. Verified by `git diff` scoped to those symbols: no overlap. |
| `665e0814`, `08e3131a`, `9addfa94`, `b0907b97`, `f1a57ff3` (spec-109 A1-A5, A8) | Web dashboard/persistence/lens wiring in `web/game/engine_bridge.py` and frontend | Do not touch `src/babylon/economics/tick/` or `src/babylon/engine/systems/production.py`. |
| `504302bf`, `30f5512e` (spec-110 B1) | `src/frontend` scaffold | Disjoint tree. |
| `4bb8aa0b`, `0ac23e8f`, `30fb8241`, `b8cef899` | Constitution v2.8.0 relocation + docs | Docs only. |

**Conclusion:** no commit between the last empirical re-verification
(`b57faee6`) and this lane's starting point touches the files A7 changes.
The `628cbc7c`-authored baseline content is current as of `b57faee6`'s
re-verification, and A7's diff (below) is the first behavioral change to
that surface since.

### A7's diff surface

1. `src/babylon/economics/tick/system/__init__.py` — `TickDynamicsSystem.step()`
   two-mode restructure: non-boundary ticks now call a new `_accrue_flows()`;
   boundary ticks call `_accrue_flows()` (close-out, pre-recompute) then the
   **unchanged** annual pipeline, then a new `_reset_flow_accrual()`
   (post-recompute). Two new private methods, ~65 LOC.
2. `src/babylon/models/world_state.py` — `_reconstruct_territory` now also
   strips `flow_`-prefixed node attrs (mirrors the existing `tick_` strip
   from `b57faee6`, identical `extra="forbid"` landmine class).
3. `src/babylon/engine/systems/production.py` — separate commit, SEPARATE
   concern: `current_year` in the tensor-registry lookup now advances with
   tick (`base_year + tick // weeks_per_year`) instead of staying pinned at
   the hydrated `base_year` forever.

No `GameDefines` field was added; **no `defines_hash` movement is expected
from A7 alone** (see Part 5 for the actual Track-A result, which does show
`defines_hash` drift — pre-existing, unrelated, see below).

---

## Part 1 — Value-neutrality argument for non-flow changes

**Claim:** A7 changes nothing for any run that (a) has no territory nodes,
(b) has territory nodes but no county has ever crossed a year boundary or
been bootstrapped with `tick_phi_hour`, or (c) is the hex-substrate
aggregate consumed by `qa:e2e-regression`/`qa:storage-budget`.

### (a) No territory nodes — the 5 qa:regression scenarios
`imperial_circuit`, `two_node`, `starvation`, `glut`, `fascist_bifurcation`
(`tools/regression_test.py::SCENARIOS`) are built from
`create_imperial_circuit_scenario`/`create_two_node_scenario` — entity-only
graphs, zero `territory` nodes. `_accrue_flows`/`_reset_flow_accrual` both
open with `graph.query_nodes(node_type="territory")`; zero territory nodes
means zero iterations, zero `graph.update_node` calls — a **provable
no-op**, not merely an empirically-observed one (see
`tests/unit/economics/tick/test_flow_accrual.py::TestStepWiresFlowAccrual
::test_calculator_free_scenario_with_no_territories_is_untouched`, which
asserts the exact node-attr-key-set is unchanged after two `step()` calls,
one boundary and one not). Empirically confirmed: `qa:regression` 5/5
byte-identical (Part 5).

### (b) Territory nodes with no boundary-authoritative state yet
`_accrue_flows` reads `node.attributes.get("tick_phi_hour")`; when absent
(`None`) the node is skipped — an EMPTY DOMAIN per Constitution III.11, not
a Loud Failure, and not a default-to-zero fabrication. This is the state of
**every** territory node in **every** run shorter than one year (52 ticks)
that starts cold (no bootstrap) — which includes the 5-tick
`qa:e2e-regression`/`qa:storage-budget` runs at the `TickDynamicsSystem`
layer specifically (see (c) below for why this doesn't matter to those two
gates anyway).

### (c) Consumption-path isolation — qa:e2e-regression / qa:storage-budget
Both gates consume `view_runtime_trace_emission` /
`_county_terminal_snapshot` (`runner.py::_county_terminal_snapshot`), which
is built **entirely** from `dynamic_hex_state` (see
`0030_views_current.sql`'s `view_runtime_trace_emission` / `v_hex_state_asof`
definitions — both are `WITH ... FROM dynamic_hex_state h ...` with no
reference to `tick_dynamics`, `tick_`-prefixed territory attrs, or anything
`TickDynamicsSystem` writes). `A7` writes only `flow_phi_accrued` /
`flow_wage_accrued` onto **territory graph nodes** — it never touches
`dynamic_hex_state`, `HexGrid`, or any hex-substrate writer (binding design
explicitly excludes the hex frame — "OUT OF SCOPE for this lane, do not
touch the hex frame" — verified by `git diff` touching zero files under
`src/babylon/economics/substrate/`). **Consequence, verified empirically in
Part 5: `qa:e2e-regression` and `qa:storage-budget` are unaffected by A7 —
contrary to this lane's original expectation** (see the structural finding
recorded in `tests/integration/web/test_static_economy_flow.py`'s module
docstring and this document's Part 5).

### ProductionSystem base_year fix — separate value-neutrality argument
`current_year = base_year + tick // weeks_per_year` is used **only** inside
`if tensor_registry is not None: ... if fips_code is not None:`. For
`tick < weeks_per_year` (52), `tick // weeks_per_year == 0`, so
`current_year == base_year` — **byte-identical to the pre-fix value** for
any run of fewer than 52 ticks, which covers all 3 gates below (5-tick
`qa:e2e-regression`/`qa:storage-budget`; the 5 `qa:regression` scenarios have
no `tensor_registry` wired at all, so the branch never executes regardless
of tick count).

---

## Part 2 — Empirical canonical result (520-tick)

**TODO — orchestrator.** Not run by this agent per the lane brief. Expected,
based on Part 1(c): the 520-tick `michigan-canada`/canonical run's
`terminal_state` gated fields (`total_v/total_c/total_s/total_k/
counties_alive`) should be **unaffected** by A7 (consumption-path
isolation), but `TickDynamicsSystem`'s territory-node `tick_`/`flow_` attrs
(not gated) WILL differ — specifically `flow_phi_accrued`/`flow_wage_accrued`
should be nonzero and monotonically increasing within each year, resetting
to `0.0` at every year boundary. If the canonical run reaches a second year
boundary (tick 104), the conservation invariant
(`tests/unit/economics/tick/test_flow_accrual.py::TestConservation`) predicts
`flow_phi_accrued` at tick 103 (last non-boundary tick of year 2) equals the
year-2 `tick_phi_hour * HOURS_PER_YEAR` to float tolerance — this is
NOT verified against the live canonical run by this agent.

---

## Part 3 — Gated-field neutrality re-verification

**TODO — orchestrator.** This agent verified gated-field neutrality only at
5-tick scale (`qa:e2e-regression` bundle compare, Part 5) — not at
520-tick / `v_hex_state_asof` scale. Recommend the same method as
`proof-2R-baseline-regen.md` Part 3: query `v_hex_state_asof` at tick 0 and
the canonical run's terminal tick, pre- vs. post-A7, and diff
`total_v/total_c/total_s/total_k/counties_alive`.

---

## Part 4 — A/B determinism

**TODO — orchestrator.** Not run by this agent. A7's new code paths
(`_accrue_flows`/`_reset_flow_accrual`) contain no RNG, no wall-clock, and
iterate `graph.query_nodes(node_type="territory")` — confirm this iteration
order is deterministic (insertion-ordered per Constitution III.7; BabylonGraph
is rustworkx-backed, and `query_nodes` is used identically by the pre-existing
`_get_territory_fips`/`_bootstrap_county_states`, which are already exercised
by `b57faee6`'s A/B-adjacent proof work) before re-running the two-session
`EXCEPT`-diff method.

---

## Part 5 — qa:regression Track-A scan + e2e/storage-budget gates

**`mise run qa:regression` (Track A, 5 abstract scenarios):**

```
Comparing imperial_circuit... PASS
Comparing two_node... PASS
Comparing starvation... PASS
Comparing glut... PASS
Comparing fascist_bifurcation... PASS

Results: 5 passed, 0 failed
All regression tests passed!
```

**5/5 byte-identical, including `defines_hash`** — this lane added no
`GameDefines` field, so unlike the `2.R` capstone's Track-A run (which
carried a pre-existing, unrelated `defines_hash` drift from specs merged
07-03→07-08), A7's run against this worktree shows **zero diff at all**
(re-ran `tools/regression_test.py compare` directly; no baseline
regeneration needed or performed).

**`mise run qa:e2e-regression` (5-tick `detroit-tri-county`):**

```
✓ counties_alive == 3
✓ population liveness: 3/3 counties alive
✓ total_v: actual=1.497e+09, expected=1.497e+09, Δ=0.000%% (tolerance ±1.0%%)
✓ no critical conservation violations

All regression checks passed.
```

**PASS, zero drift — this CONTRADICTS the lane brief's stated expectation**
("Your change SHOULD move detroit-tri-county values... EXPECT failure...
regenerate the baseline"). Root cause (Part 1(c), verified by reading
`0030_views_current.sql`): the fields this comparison checks
(`total_v`/`counties_alive`/conservation) are sourced from
`view_runtime_trace_emission`, which is built exclusively from
`dynamic_hex_state` — the hex substrate layer this lane was explicitly
instructed NOT to touch ("hex-level persisted c/v/s/k NEVER moves... OUT OF
SCOPE for this lane, do not touch the hex frame"). A7's flow accrual writes
only to territory graph nodes (`flow_phi_accrued`/`flow_wage_accrued`), which
never feed `dynamic_hex_state`. **The baseline was NOT regenerated** — there
is nothing to regenerate; the comparison tool cannot see this lane's change
at all. See `tests/integration/web/test_static_economy_flow.py` for where
the actual movement IS proven (through the full engine pipeline, asserting
directly on graph node attrs rather than through this DB-view-mediated
comparison).

**`mise run qa:storage-budget` (5-tick, quiescent owned DB):**

```
✓ boundary_flow_register: 14.4 rows/tick within budget 14.4
✓ conservation_audit_log: 5.6 rows/tick within budget 5.6
✓ contradiction_field: 4 rows/tick within budget 4
✓ dynamic_consciousness_state: 3 rows/tick within budget 3
✓ dynamic_demographics_state: 3 rows/tick within budget 3
✓ dynamic_employment_state: 3 rows/tick within budget 3
✓ dynamic_external_node_state: 9 rows/tick within budget 9
✓ dynamic_hex_state: 209 rows/tick within budget 209
✓ dynamic_relationship_state: 9 rows/tick within budget 9
✓ tick_commit: 1 rows/tick within budget 1

Storage budget check passed.
```

**PASS, unchanged** — as expected (hex frame untouched); not regenerated.

---

## Part 6 — Structural finding: web sessions cannot exercise this lane's
## mechanism across ticks (escalated, not closed)

Verified empirically and by full source read of
`babylon.engine.simulation_engine.step`, `EngineBridge.resolve_tick`,
`WorldState.from_graph`/`_reconstruct_territory`,
`_restore_graph_context`/`_save_graph_context`:

- `EngineBridge.resolve_tick` advances via the module-level round-tripping
  `step(state, ...)` function (not the headless runner's direct,
  persistent-in-memory `engine.run_tick(graph, ...)` loop).
- `step()` does `state.to_graph() -> run_tick() -> WorldState.from_graph()`
  on **every call**; `_reconstruct_territory` strips every `tick_`/`flow_`
  -prefixed territory-node attr (both pre-existing `tick_` since `b57faee6`,
  and this lane's `flow_`) because `Territory` has `extra="forbid"`.
- `_restore_graph_context`/`_save_graph_context` thread only
  `graph.graph["tick_dynamics"]` (a **graph-level** dict, which does include
  a `county_states` fallback) through `persistent_context` — they do **not**
  restore **territory-node-level** `tick_`/`flow_` attrs.
- `EngineBridge.resolve_tick` passes a **fresh** `persistent_context={}` on
  every call (verified: no caller in `test_full_persistence.py` threads one
  across `resolve_tick` calls; `resolve_tick`'s own signature defaults it to
  `None` and re-initializes to `{}` when absent).

**Net effect: no territory-node-level `tick_`/`flow_` state can survive
across two separate `EngineBridge.resolve_tick()` calls, for ANY web
session, today — regardless of this lane's change.** This is a pre-existing
gap in cross-call `persistent_context` threading (it threads the
graph-level `tick_dynamics` dict but not territory-node attrs), **out of
this lane's scope to fix**.

Separately: the `wayne_county` web scenario's territories are hex-resolution
(H3 ids, `county_fips=None` for all of them — verified directly:
`_build_initial_state_for_scenario('wayne_county').territories` yields IDs
like `862ab2c8fffffff` with `county_fips` unset), so even a hypothetical fix
to the persistent_context gap above would not let `wayne_county` specifically
exercise county-level flows without ALSO wiring a county-resolution
territory layer into that scenario — a second, larger, separate concern.

**Consequence for the acceptance test (G3 symptom):** the lane brief's literal
target ("a wayne_county session shows at least one MOVING economic value
between tick 1 and tick 2" via `EngineBridge.resolve_tick`) is **not
reachable** as specified. `tests/integration/web/test_static_economy_flow.py`
instead proves the mechanism two ways:

1. `TestFlowAccrualAcrossConsecutiveTicks` — the real symptom, through the
   FULL 26-system default engine pipeline (`SimulationEngine(_DEFAULT_SYSTEMS)
   .run_tick`) on ONE persistent graph object across two consecutive ticks —
   exactly the model the headless runner (and hence `qa:e2e-regression`'s
   underlying mechanism, once it reaches a year boundary) actually uses.
   `flow_phi_accrued` is asserted `> 0` after tick 1 and strictly greater
   after tick 2, with the boundary-authoritative `tick_capital_stock` (a
   LEVEL) asserted flat across the same two ticks.
2. `TestWayneCountyResolveDoesNotRegress` — a Postgres-gated regression-safety
   test proving the real `EngineBridge.resolve_tick` production path (the
   literal instructed pattern) does not crash or otherwise regress with A7's
   change wired into the default system order.

**Recommendation:** open a follow-on item for the `persistent_context`
territory-node-attr threading gap (affects `TickDynamicsSystem`'s entire
output, not just this lane's flow accrual — the annual `tick_` state itself
already can't survive a web resolve today either) before attempting to
satisfy a literal cross-resolve web-session acceptance target for any
`TickDynamicsSystem` output.

---

## Verification chain

- Unit: `tests/unit/economics/tick/test_flow_accrual.py` (18 new), full
  `tests/unit/economics/tick/` (302 passed), `tests/unit/engine/systems/
  test_production.py` (+2 new, 25 passed total in that file + 2 adjacent
  files). Full `tests/unit` suite: **9414 passed, 17 skipped (pre-existing),
  4 xfailed (pre-existing)**, `mypy` clean (573 files), `ruff` clean.
- Integration: `tests/integration/web/test_static_economy_flow.py` (3 passed,
  1 Postgres-gated), `test_full_persistence.py` + `test_dashboards.py` +
  `test_balkanization_seed.py` (11 passed, no regressions).
- `qa:regression`: 5/5 byte-identical (Part 5).
- `qa:e2e-regression`: PASS, zero drift, not regenerated (Part 5 — contradicts
  the lane brief's expectation; root-caused).
- `qa:storage-budget`: PASS, unchanged, not regenerated (Part 5).
- 520-tick canonical + A/B determinism: **TODO, orchestrator** (Parts 2/3/4).
