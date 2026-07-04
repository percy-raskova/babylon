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

- **Unchanged** (asserted by `compare-bundle`): `counties_alive`,
  `counties_with_population`, `total_v` (Δ = 0.000%).
- **New outputs**:
  - `boundary_flow_register`: N `DRAIN_EDGE` rows/tick = (scope counties) × (blocs
    with Φ>0). Detroit tri-county: 3 × 6 = 18 rows/tick.
  - `summary.json` top-level `external_node_flows`: now populated (was empty) —
    per-dest phi inflow sums.
  - `conservation_audit_log`: 6 new `imperial_rent_phi_week_distribution` rows/tick
    (one per Φ>0 bloc), all OK.
- Because the compared gate fields are unchanged, `qa:e2e-regression` stays GREEN
  even against the OLD baseline; the baseline is regenerated because the OUTPUT
  bundle (external_node_flows, audit rows) differs, per R-PROOF discipline.

## Verification chain

- Unit: exposure loader (6), Φ attribution (7), conservation evaluator (5) — green.
- Integration `test_trade_circuit.py`: DRAIN rows every tick for Φ>0 blocs +
  Σ DRAIN ≡ Φ_week per bloc + audit rows all OK — GREEN with wiring; RED
  (drain/audit assertions fail) with the runner→context wiring reverted.
- `qa:e2e-regression`: green against the regenerated baseline (compared fields
  Δ=0.000%).
