# spec-101 R-PROOF — Written proof for the 5-tick re-baseline

**Proof window**: shared 101+102 (R-PROOF, one open window). Opened by spec-101.

## WHAT changed (the dynamics delta)

Boundary flows now populate every tick. Before spec-101 the runner built
`TickContext(tick=tick)` only, so `ImperialRentSystem._invoke_phi_distribution_if_wired`
returned early (silent no-op) and the `boundary_flow_register` table stayed empty
for the whole run. spec-101 populates the four dormant context keys
(`session_id`, `boundary_flow_register`, `external_nodes_phi`,
`county_exposure_by_external`), so every tick the Φ distribution records one
`DRAIN_EDGE` row per (external bloc with Φ>0, scope county). External-node rows
also now carry attributed national Φ (was 0) and bilateral trade USD.

## WHY it is correct

1. **The math was always built, merely unwired.** `distribute_phi_week_to_counties`
   (spec-062) and the register-flush→envelope path (spec-065) shipped and are
   unit-tested. spec-101 only supplies their inputs; it adds no new arithmetic to
   the tick.
2. **DRAIN distribution mutates NO simulation state.** `distribute_phi_week_to_counties`
   only calls `register.record(...)` — it does not touch any hex `v/c/s/k`, entity
   wealth, consciousness, edges, or graph attributes. Therefore every quantity the
   e2e-regression gate compares is provably unchanged:
   - `terminal_state.total_v` comes from static hex economics (02-engine-truths §6)
     — untouched.
   - `counties_alive` / `counties_with_population` — driven by entity vitality —
     untouched.
   - No system reads `phi_year_inflow` except the Φ-distribution path (verified
     `rg` over `engine/systems/`), so raising it from 0→attributed changes nothing
     else.
3. **Determinism hashes are byte-identical.** The per-tick hash is
   `sha256(session:tick:seed)` (not state-derived); the auditor determinism hash
   is computed over hex_state only (`compute_determinism_hash`). Neither depends on
   boundary rows. No RNG is introduced; node/county iteration is sorted.
4. **Conservation holds by construction.** The scope-renormalised exposure weights
   sum to 1.0, so `Σ_counties DRAIN = Φ_week` per bloc exactly (float). The new
   `imperial_rent_phi_week_distribution` audit rows report the relative residual
   (Σdrain/Φ_week vs 1.0) ≈ 1e-15 → OK severity → no `--strict` alarm.

## MAGNITUDE (what moves in the bundle)

- **Unchanged** (asserted by `compare-bundle`, the GATED fields): `counties_alive`,
  `counties_with_population`, `total_v` (Δ = 0.000%).
- **New outputs directly attributable to spec-101's four feature commits**
  (`f1183402`, `51289ec0`, `c3cab3b4`, plus this re-baseline commit
  `e059e50e` — verified: these touch only `postgres_initialization.py`,
  `conservation_audit.py`, `bridge.py`, `runner.py`, `audit_models.py`, and
  their tests; none touch `SurvivalSystem`, `ContradictionSystem`,
  `LifecycleSystem`, or any event-emission code):
  - `boundary_flow_register`: N `DRAIN_EDGE` rows/tick = (scope counties) × (blocs
    with Φ>0). Detroit tri-county: 3 × 6 = 18 rows/tick.
  - `summary.json` top-level `external_node_flows`: now populated (was empty) —
    per-bloc phi inflow sums (review fix #5: keyed by the external node/bloc
    id via `kind='external'`, not by the receiving county FIPS that an
    earlier `GROUP BY dest_node_id` silently produced for the DRAIN_EDGE
    flow type).
  - `conservation_audit_log`: 6 new per-bloc `imperial_rent_phi_week_distribution`
    rows/tick (one per Φ>0 bloc) plus one aggregate-coverage row (review fix
    #3, `scale=external:__national_aggregate__`), all OK.

### Honest disclosure: non-gated fields ALSO drifted, but NOT from spec-101

Adversarial review (2026-07-04) found the regenerated 5-tick baseline's diff
includes drift the paragraphs above do not cover:

- `terminal_state.max_tension`: `1.0` → `0.667728`.
- `p_acquiescence` / `p_revolution` per county: previously distinct per
  demographically-distinct county (e.g. `26099`: 0.3183/0.4264 vs `26125`/
  `26163`: 0.3234/0.4308); now **bit-identical across all three counties**
  (`0.2505638275862069` / `0.31034510344827587` for all three).
- Event-type composition: `ecological_overshoot`, `peripheral_revolt`,
  `rupture`, `excessive_force` disappear; `lifecycle_transition`,
  `surplus_extraction` appear; `population_attrition` count drops 12→3.
- `performance.per_system_ms` gains a `FascistFactionSystem` entry.

**This drift is real and verified (diffed directly against the git history),
but it is NOT caused by spec-101.** It is INHERITED from the ~106 commits
merged into this branch's ancestry since spec-086 last regenerated
`detroit-tri-county-5t.json` — specifically spec-070 (balkanization: adds
`SovereigntySystem`, `CollapseTransitionSystem`, event composition changes),
spec-071 (reactionary: adds `FascistFactionSystem` — directly explains the
`per_system_ms` diff above), and the ongoing dialectics refactor. Those specs
shipped using the narrower `_compare_bundle_command` gate (`counties_alive`,
`counties_with_population`, `total_v` only) and never regenerated this FULL
artifact. `e059e50e` is the first commit since spec-086 to do a full
`--write-baseline` regen of `detroit-tri-county-5t.json`, so 106 commits'
worth of accumulated non-gated drift surfaces all at once, in the same diff
as spec-101's genuine (total_v-neutral) additions. The two are orthogonal:
spec-101 added new, additive fields (`external_node_flows`, the new audit
rows) and touched zero lines of `SurvivalSystem`/`ContradictionSystem`/
`LifecycleSystem`/event-emission code; the pre-existing drift would have
appeared in this diff regardless of whether spec-101 shipped anything at all.

- Because the compared GATED fields are unchanged, `qa:e2e-regression` stays
  GREEN even against the OLD baseline; the baseline is regenerated because the
  OUTPUT bundle (external_node_flows, audit rows, AND the inherited drift
  above) differs from the last full regen, per R-PROOF discipline.

### Owner-queue item (review finding #8, PLAUSIBLE — not a code bug)

D2 scope-renormalisation (`county_exposure.py`) makes a **sub-national**
scoped run (e.g. michigan-canada, detroit-tri-county) absorb the FULL
national bloc Φ_week, not a proportional share of it — the study area's
county-exposure weights are renormalised to sum to 1.0 regardless of how
small a fraction of the national total those counties represent. This makes
the `Σ DRAIN_EDGE ≡ Φ_week` invariant tautologically satisfiable at
sub-national scope (D2 says this explicitly: "the study area receives the
full bloc Φ_week"), and the resulting per-tick drain magnitude is
economically inflated relative to the receiving counties' own economic
output — verified on the 520-tick michigan-canada canonical run
(`external_node_flows` cumulative phi-inflow ÷ 519 ticks, vs. that county's
terminal-tick `total_v`): county 26001, per-tick drain ≈$71.4M vs. `v`
≈$0.85M (≈84×); county 26005, per-tick drain ≈$3.44B vs. `v` ≈$24.5M
(≈141×) — roughly two orders of magnitude, consistent across sampled
counties. **This invariant validates the plumbing (Σ recorded DRAIN equals
the intended Φ_week slice), not the real-world economics of the
magnitude** — whether national-scope simulation is required before drain
magnitudes are economically meaningful is an open question for Percy (the
E:104/E:105 national-scope axis). See `spec.md` §Decision D2 for the
code-level cross-reference.

## Verification chain

- Unit: exposure loader (6), Φ attribution + Hickel-coverage preflight (10,
  after the 2026-07-04 review added the fail-loud guards' tests),
  conservation evaluator (9, after the review added the aggregate-coverage
  + weeks_per_year tests) — green.
- Integration `test_trade_circuit.py`: DRAIN rows every tick for Φ>0 blocs +
  Σ DRAIN ≡ Φ_week per bloc (now with a non-emptiness + bloc-coverage guard,
  review fix #4) + audit rows all OK — GREEN with wiring; RED (drain/audit
  assertions fail — confirmed by reverting the wiring during the 2026-07-04
  review) with the runner→context wiring reverted.
- `qa:e2e-regression`: green against the regenerated baseline (compared fields
  Δ=0.000%).
