# Phase 0 Research — spec-101 Trade Activation

All findings verified in-repo against the live reference DB
(`data/sqlite/marxist-data-3NF.sqlite`) and the wiring targets on 2026-07-03/04.

## R1 — The dormant seam is real and 4-keyed

`ImperialRentSystem._invoke_phi_distribution_if_wired` (`engine/systems/economic.py`
~L103–151) reads `context.get(...)` for `boundary_flow_register`, `session_id`,
`external_nodes_phi`, `county_exposure_by_external`; returns silently if any is
None. The runner builds `TickContext(tick=tick)` only (`runner.py:311` in
`_advance_tick`). The register is already constructed
(`runner.py:603 boundary_register`, injected as `services.boundary_register`).
`bridge.persist_tick` already flushes the register into the per-tick envelope
(`bridge.py:482`) — so once phi-distribution records rows, they persist with no
further plumbing.

## R2 — CRITICAL: all external-node Φ is currently ZERO

`_bootstrap_external_nodes` → `_fetch_node_phi_and_trade`
(`postgres_initialization.py`) resolves `phi_year_inflow` from
`immutable_reference_hickel_drain.partner_node_id = ANY(_EXTERNAL_PARTNER_KEYS[node])`.
But `_copy_hickel_drain` (`sqlite_hydrator.py`) sources `partner_node_id` from
`fact_hickel_erdi_annual.scale_type`, whose ONLY values are `Intensive` /
`Extensive` / `Intensive_China_Inflection` — a **single national aggregate**
($8,625B "Intensive" for 2010), NOT per-partner. No `_EXTERNAL_PARTNER_KEYS`
entry ("Canada", "China", …) matches "Intensive" → **every node hydrates with
Φ=0.0**. Pure wiring ⇒ zero DRAIN_EDGE rows ⇒ gate unsatisfiable. Hence the Φ
attribution (spec.md D3). `phi_year_inflow` is consumed by NO dynamics system
(verified `rg` over `engine/systems/`) — only by the phi-distribution path — so
attributing it is safe (observational + the new DRAIN path only).

## R3 — Exposure map: bloc-invariant, weights sum to exactly 1.0

`fact_county_exposure_by_external`: 384,200 rows = 8 `dim_country is_region=1`
blocs × ~3,108 counties × 15 years. **Bloc-invariance verified**: blocs 1 and 12
for 2010 have 0 differing per-county weights (identical maps). Per-(bloc,year)
weights sum to exactly 1.0 over 3,108 counties. All 83 Michigan (26xxx) counties
present (combined national weight 0.0394). ⇒ broadcast ONE `{fips:weight}` map to
all 8 engine nodes; renormalise to the scope (spec.md D2). Column: `dim_county.fips`
(VARCHAR5). Annual `time_id` for 2010 = 14 (`dim_time.is_annual=1`).

## R4 — Bilateral trade: is_region-bloc-keyed, USD

`fact_bilateral_trade_annual`: 120 rows = 8 blocs × 15 yrs. 2010 totals
(USD millions): EU 558,855 · Advanced Technology Products 627,564 ·
North America 920,543 · Europe 667,476 · Africa 113,348 · Pacific Rim 980,305 ·
Asia 1,183,488 · Australia and Oceania 37,099. Engine nodes (canada/china/eu/…)
≠ these blocs → an injective node→bloc crosswalk is required (spec.md D3). Today's
`bilateral_trade_value` comes from `_copy_ricci_unequal` (per-country
`fact_trade_monthly` Σ imports+exports) — NOT hardcoded 0.0 as the program text
assumed; spec-100 R8 supersedes it with the audited annual table.

## R5 — TRADE_EDGE has no LODES-free path

`vol2_circulation.py` emits TRADE_EDGE ONLY as a paired wage-repatriation row
alongside COMMUTE_OUT, both from the LODES OD matrix (`_od_loader.load_year`).
No other `register.record(... TRADE_EDGE ...)` exists in `src/`. So TRADE_EDGE
cannot be activated without COMMUTE_OUT and without LODES data (absent →
098-LODES). Program "activate vol2_step TRADE_EDGE" assumption refuted by code;
vol2_step stays unwired (spec.md D5). `Vol2CirculationStep` is constructed
nowhere in `src/` today.

## R6 — Conservation identity holds by construction; needs relative grading

`distribute_phi_week_to_counties` splits `phi_week = phi_year/52` by weights that
sum to 1.0 ⇒ `Σ_counties DRAIN = phi_week` exactly (float). The auditor already
enumerates `imperial_rent_phi_week_distribution` in `_DEFAULT_INVARIANTS` but no
evaluator is registered. `grade_severity` uses ABSOLUTE thresholds
(ok ≤ epsilon; alarm > 1e-6). Φ_week is ~$1e11 scale, so an absolute residual is
meaningless — report the **relative** residual (computed=`Σdrain/phi_week`,
expected=`1.0`; residual ≈1e-15 ⇒ OK). `qa:e2e-regression` runs `--strict`, which
aborts on the first ALARM row — the relative form guarantees no false alarm.

## R7 — Baseline impact is bounded (R-PROOF magnitude)

`compare-bundle` (qa:e2e-regression) asserts only `counties_alive`,
`counties_with_population`, `total_v` (±tol). `distribute_phi_week_to_counties`
records boundary rows ONLY — it mutates NO hex `v`/entity wealth/consciousness.
`total_v` comes from static hex economics (`02-engine-truths` §6). ⇒ the compared
fields are provably UNCHANGED; the 5-tick gate stays green even pre-rebaseline.
What moves: the summary's top-level `external_node_flows` (now populated) + new
`conservation_audit_log` rows. Determinism hashes are byte-identical (the per-tick
hash is `sha256(session:tick:seed)`; the auditor hash is over hex_state only).
Re-baseline per R-PROOF because the OUTPUT (rows, summary) changes.
