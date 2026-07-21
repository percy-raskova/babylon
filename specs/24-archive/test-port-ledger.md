# Program 24 — The Archive: test-port ledger

**Scope:** every behavioral assertion the legacy web client's test estate makes,
mapped to the contract test that carries it after the cutover. Seeded at P1
(county scope); **full closure is a P4 cutover-gate criterion** (charter
criterion 1). Format follows the Program 12 precedent
(`specs/112-cutover/test-port-ledger.md`).

**Authority:** `project/programs/24-the-archive.md` (P1 item 1, P4 gate).
**Method:** dispositions per row — PORTED (test moved, asserts the same
behavior), REWRITTEN (behavior re-asserted against the projection contract),
RE-GUARDED (behavior now pinned by a registry/view contract test), CARRIED
(deferred to a named P2 lane), RETIRED (legacy-only behavior, dies with the
web client).

## Disposition counts (P1 seed + P2 WO-38)

| Disposition | Rows |
|---|---|
| PORTED | 4 |
| REWRITTEN | 6 |
| RE-GUARDED | 2 |
| CARRIED (P2) | 1 |
| RETIRED | 1 |

## Ledger

| Old assertion (source) | Destination contract test | Disposition | Landed |
|---|---|---|---|
| `src/frontend/e2e/real-loop.spec.ts` (tick→page loop) | `tests/integration/archive/test_county_e2e.py` | REWRITTEN | WO-7 |
| `src/frontend/e2e/inspection-stack.spec.ts` (inspector reads) | `tests/unit/projection/test_county.py` (`project_county` contract) | REWRITTEN | WO-3 ✓ |
| `src/frontend/e2e/briefing-map-smoke.spec.ts` + `map-lens-cycling.spec.ts` | `tests/unit/projection/test_registry.py` (`v_county_value_aggregate` declared contract) | RE-GUARDED | WO-2 ✓ |
| `src/frontend/e2e/veil.spec.ts` | `tests/unit/projection/fog/` (veil gate carried with the fog relocate) | PORTED | WO-1 ✓ |
| `tests/unit/web/test_engine_bridge.py::TestGetEconomy` / `TestImperialRentGapByRegion` | `tests/unit/projection/test_county.py` (per-county Φ field: `tick_phi_hour` producer ruling) | REWRITTEN | WO-3 ✓ |
| `::TestSerializeTerritoryGraphThreading` / `TestStateToSnapshot` | `tests/unit/projection/test_view_models.py` (`CountyView` hydration) | REWRITTEN | WO-2 ✓ |
| `::TestHexStateProjection` | `tests/unit/projection/test_registry.py` (`v_hex_state_asof` declared contract) | RE-GUARDED | WO-2 ✓ |
| `::TestDeriveIntelLedger*` | `tests/unit/projection/fog/test_ledger.py` | PORTED | WO-1 ✓ |
| `::TestOrgCountByTerritory` / `TestMeanTerritoryAttr` / `TestHeatDeltaByTerritory` | `tests/unit/projection/test_county.py` (aggregation helpers contract) | REWRITTEN | WO-3 ✓ |
| `::TestEndgameDetection` (national axes) | national dossier lane — the axis is national-only, not county | CARRIED (P2 Lane P) | — |
| `::TestExpectedDeltas` (spec-116 preview == resolution) | `tests/unit/projection/verbs/test_preview.py` (`TestResolverParity` — doctrine threading pinned per-resolver; heuristic verbs pinned) | PORTED | WO-38 ✓ |
| `::get_verb_eligibility` plate assertions (eligibility predicates + (reason, remedy) copy + affordability ride-along) | `tests/unit/projection/verbs/test_plate.py` (`build_verb_plate` contract; copy table relocated to `projection/verbs/copy.py`, web shim `is`-single-sourced) | PORTED | WO-38 ✓ |
| `src/frontend/e2e/verb-submit.spec.ts` (plate render: 9 verbs, ineligible shows reason) | `tests/unit/projection/verbs/test_plate.py` + WO-26 verb-plate snapshot | REWRITTEN | WO-38 ✓ (widget golden lands WO-26) |
| `src/frontend/e2e/end-turn-flow.spec.ts` (submit → resolve) | `tests/integration/archive/test_verb_resolution.py` (submit → fold → OODASystem adjudicates; rejection never reaches the engine) | REWRITTEN | WO-39 ✓ |
| `::TestEngineBridgeActions` / `TestActionInjection` (submit affordability + injection shape) | `tests/unit/projection/verbs/test_submit.py` (attack mode-specific labor gates; JSON-null params coercion; org-absent fallthrough pinned) | PORTED | WO-39 ✓ |
| bridge endgame-recognition block (century horizon, UNRESOLVED fallback, lock window) | `tests/unit/projection/test_endgame.py` (`endgame_status` pure fold; detector stays engine-side) | PORTED | WO-39 ✓ |
| `::TestHexFeaturePropertiesVeilGate` / `TestDerivedEconomyVeilGate` + `test_veil.py` (doctrine veil tiers) | `tests/unit/projection/test_veil_gating.py` + `tests/unit/web/test_veil.py` (green through the `is`-identity shim over `babylon.projection.veil`) | PORTED | WO-41 ✓ |
| `test_vision_gate.py` (desert/mud/water class gate) | `tests/unit/projection/test_veil_gating.py::TestClassVisionPort` (pure `apply_class_vision`; bridge wrapper delegates, its 12 behavioral tests stay green) | PORTED | WO-41 ✓ |
| fog+class-vision two-gates hazard (`fog/filter.py` header, unresolved at P1) | `tests/unit/projection/test_veil_gating.py::TestGateComposition` (`apply_political_gates`: vision-then-fog, restriction-map composition — RESOLVED, not carried) | REWRITTEN | WO-41 ✓ |
| `src/frontend/e2e/auth.spec.ts` (Django login) | none — Django auth dies with the web client | RETIRED | — |

## Deviations recorded

- **No forced bridge delegation in WO-3.** The work-order draft named
  `web/game/engine_bridge.py::get_county_import_exposure` as a thin-shim
  delegation site; inspection shows it serves spec-103 *import-exposure
  provenance* — a different quantity than the `CountyView` dossier, so a
  delegation there would be cosmetic, not a real seam. The genuine Django
  shim landed with the fog relocate (WO-1: `web/game/fog/*` re-export shims,
  `is`-identity guarded by `tests/unit/web/test_fog_shim.py`). Bridge
  *inspection* reads are REWRITTEN rows above; the bridge keeps serving the
  legacy client untouched until P4 deletes it.
- The disabled `test_engine_bridge.py` suite (module-level skip, owner ruling
  2026-07-20) remains in-tree as the P4 closure worklist: at cutover, every
  one of its 63 test classes must appear in this ledger with a disposition.
