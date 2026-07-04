# spec-101 — Trade activation: boundary flows live

**Program**: 09 Full-Game Build, Lane E (engine). **Provisional number**: 101
(first-come per `project/00-mission.md`; audit-advisory: none).
**Depends on**: spec-100 (county-exposure + bilateral-trade reference tables,
merged). **Proof window**: shared 101+102 (R-PROOF). **Status**: implemented.

## Why

Spec-062 built the imperial-rent Φ→county distribution machinery
(`phi_distribution.distribute_phi_week_to_counties`) and the
`BoundaryFlowRegister`, but left the runner tick loop passing
`TickContext(tick=tick)` only. `ImperialRentSystem._invoke_phi_distribution_if_wired`
therefore silently no-ops every tick: no `DRAIN_EDGE` boundary rows ever flow.
Spec-100 then materialised the `county_exposure_by_external` weight map and the
`fact_bilateral_trade_annual` table. Spec-101 activates the boundary-flow
circuit end-to-end so imperial rent drains from the external world-system into
US counties every tick, recorded as an auditable ledger.

## What ships (functional requirements)

- **FR-101-1** — The runner populates the four dormant `TickContext` keys every
  tick: `session_id`, `boundary_flow_register` (the already-constructed
  `services.boundary_register`), `external_nodes_phi`
  (`{node_id: phi_year_inflow}`), `county_exposure_by_external`
  (`{node_id: {county_fips: weight}}`). Result: `_invoke_phi_distribution_if_wired`
  records `DRAIN_EDGE` rows every tick.
- **FR-101-2** — `county_exposure_by_external` is loaded from spec-100's
  `fact_county_exposure_by_external` reference table, filtered to the run's
  scope counties and **renormalised so the present weights sum to 1.0**
  (scope projection, §Decision D2). Because the distribution is bloc-invariant
  (spec-100 R6, verified: 0 differing rows across blocs), ONE `{fips: weight}`
  map is broadcast to all 8 international engine nodes.
- **FR-101-3** — External-node Φ is made grounded-nonzero. The reference DB's
  Hickel drain is a single **national aggregate** (`scale_type='Intensive'`,
  no per-bloc resolution — verified 2026-07-03), so the national Φ is
  **attributed across the international engine nodes by bilateral-trade share**
  (spec-100 `fact_bilateral_trade_annual`) via a documented injective
  engine-node→bloc crosswalk (§Decision D3). Nodes without a grounded
  containing bloc receive Φ=0 (no fabricated specificity, III.8).
- **FR-101-4** — `ExternalNode.bilateral_trade_value` (USD) is populated from
  `fact_bilateral_trade_annual.total_trade_usd_millions` via the same crosswalk
  (spec-100 R8 handoff: consume the annual table; target the value field, never
  `bilateral_trade_tons`). `bilateral_trade_tons` stays 0.0 (needs FAF freight —
  future 098-family slice).
- **FR-101-5** — The conservation auditor gains an evaluator for the (already
  enumerated) `imperial_rent_phi_week_distribution` invariant: per bloc with
  Φ>0, `Σ DRAIN_EDGE credits this tick ≡ Φ_week` (`= phi_year_inflow/52`). The
  residual is reported **relative** (`Σdrain/Φ_week` vs `1.0`) so absolute float
  error at $1e12 magnitude cannot trip `--strict`'s 1e-6 alarm (§Decision D4).
- **FR-101-6** — The `vol2_step` TRADE_EDGE/COMMUTE_OUT path stays GATED
  (dormant, no-op) — it is inseparable from COMMUTE_OUT and both require the
  LODES OD matrix (absent until 098-LODES). See §Decision D5.

## Non-goals

- Commute emission (COMMUTE_OUT) — 098-LODES.
- Agentic or recursive blocs — R-AMEND (blocs stay Layer-0 register machinery).
- Per-bloc / per-country Φ or trade resolution — needs a data source that does
  not exist in the reference DB; the trade-share proxy is the grounded interim.
- Trade UI surfaces — spec-103.

## Key decisions (recorded)

- **D1 — Φ attribution is a design decision, not pure wiring.** The task framed
  spec-101 as "wire the dormant keys; the math is already built." Verification
  found the hydrated external nodes carry **Φ=0.0 for all 8 blocs** (Hickel is a
  single national aggregate keyed `scale_type`, matching no `_EXTERNAL_PARTNER_KEYS`
  entry). Pure wiring alone would emit zero DRAIN_EDGE rows — the gate would be
  unsatisfiable. Spec-101 therefore attributes the national Φ to blocs (D3).
  **This attribution model is the #1 owner-review item** (see close-out).
- **D2 — Scope renormalisation.** `distribute_phi_week_to_counties` requires the
  county weights to sum to 1.0 (it rejects non-unit sums, III.1 no silent
  renormalisation). A scoped run (Michigan = 83 counties = 3.94% of national
  exposure) is a strict subset. The exposure map is filtered to scope counties
  and **renormalised at load** (an explicit caller-side study-area projection —
  the distribution function still receives unit-sum weights). This makes "the
  study area receives the full bloc Φ_week, split by relative intra-scope
  exposure" — the contract the conservation identity (FR-101-5) requires. At
  national scope it is a near-no-op.
- **D3 — Injective node→bloc crosswalk for Φ attribution + trade value.** The 8
  engine nodes (`canada, china, eu, india, sub_saharan_africa, latin_america,
  russia_csi, southeast_asia`) do not equal the 8 `dim_country is_region=1`
  blocs. An **injective** crosswalk (each node → at most one distinct bloc)
  avoids double-counting: `eu→EU`, `canada→North America`,
  `sub_saharan_africa→Africa`, `china→Asia`, `southeast_asia→Pacific Rim`,
  `russia_csi→Europe`. `india` and `latin_america` have no distinct grounded
  bloc (Asia taken by china; no Latin-America bloc — "South and Central America"
  is `is_region=0`) → **Φ=0, disclosed** (not fabricated). Unmapped blocs
  (Advanced Technology Products — a product category, not geographic;
  Australia & Oceania — no engine node) are excluded. Φ share =
  `bloc_total_trade / Σ(mapped-bloc total_trade)`; `Σ shares = 1.0` →
  `Σ_nodes Φ_node = national Φ` (national conservation holds by construction).
  **Fidelity limitations disclosed**: containing-bloc granularity (SSA gets all
  of Africa; SE Asia all of Pacific Rim); `russia_csi→Europe` is weak; `india`
  and `latin_america` drop out. A future per-bloc drain / per-country trade
  slice replaces the proxy.
- **D4 — Relative conservation residual.** Reported as `Σdrain/Φ_week` vs `1.0`
  (≈1e-15 error) so the absolute 1e-6 `--strict` alarm threshold is magnitude-
  independent at the $1e12 Φ scale.
- **D5 — vol2_step stays gated.** In `vol2_circulation.py` TRADE_EDGE is emitted
  ONLY as a wage-repatriation pair with COMMUTE_OUT, both sourced from the LODES
  OD matrix. TRADE_EDGE cannot be activated independently of COMMUTE_OUT or of
  LODES. Since the program directs "COMMUTE_OUT stays GATED; do NOT enable
  commute here," the vol2 sub-stage is NOT wired (`vol2_step` absent from
  context → existing silent no-op preserved). The program §2 phrase "activate
  the vol2_step TRADE_EDGE path" rests on the assumption that TRADE_EDGE is
  separable; observed code refutes it (program §0: repo wins). Deferred to
  098-LODES.

## Gate (program 09 §2)

- `boundary_flow_register` populates every tick (DRAIN_EDGE rows for all blocs
  with Φ>0).
- `mise run qa:e2e-regression` green against the NEW proven baseline.
- Canonical `mise run sim:e2e-bg` passes liveness 83/83.
- Conservation identity `Σ DRAIN_EDGE ≡ Φ_week` per bloc holds.
