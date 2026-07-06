# Plan: Trade Surfaces in the Product UI

**Spec**: 103-trade-surfaces
**Branch**: `103-trade-surfaces` (off `13438ac5`)

## Architecture

Three new GET-only bridge methods + Django views + React surfaces. All reads
over persisted engine state. No engine writes. No `babylon.*` imports in
frontend.

### Data sources (all read via persistence pool SQL)

| Table | Lane | Present in product DB? | Degrades when absent? |
|-------|------|------------------------|-----------------------|
| `boundary_flow_register` | E (062/101) | No (SIM DB 5433) | Yes → empty series |
| `dynamic_external_node_state` | E (062) | No (SIM DB 5433) | Yes → zero latest |
| `county_exposure_by_external` | D (100) | No (unbuilt) | Yes → empty weights |

### Backend (web/game/)

```
engine_bridge.py
  ├─ _fetch_boundary_flow_series(pool, session_id) → list[dict]     # NEW helper
  ├─ _fetch_external_node_latest(pool, session_id) → list[dict]     # NEW helper
  ├─ _fetch_county_exposure_weights(pool, county_fips) → list[dict] # NEW helper
  ├─ get_trade_flows(session_id) → dict                             # NEW
  ├─ get_county_import_exposure(session_id, county_fips) → dict     # NEW
  └─ get_trade_panel(session_id) → dict                             # NEW

api.py
  ├─ game_trade_flows(view)        # NEW — GET /api/games/:id/trade-flows/
  ├─ game_county_exposure(view)    # NEW — GET /api/games/:id/exposure/?county_fips=
  └─ game_trade_panel(view)        # NEW — GET /api/games/:id/trade-panel/

urls.py
  └─ 3 new path() entries
```

### Frontend (web/frontend/src/)

```
types/trade.ts                    # NEW — TradeFlowsPayload, ExposurePayload, TradePanelPayload
hooks/useTradeFlows.ts            # NEW — poll GET /trade-flows/
hooks/useCountyExposure.ts        # NEW — poll GET /exposure/?county_fips=
hooks/useTradePanel.ts            # NEW — poll GET /trade-panel/
components/wire/BlocFlowLines.tsx # NEW — per-bloc sparklines in INDEX tab
components/wire/bloc-flow.css     # NEW
components/intel/ImportExposurePanel.tsx  # NEW — drill-down provenance chain
components/intel/import-exposure.css      # NEW
components/pages/TradePanel.tsx   # NEW — aggregate trade panel
components/pages/trade-panel.css  # NEW
test/handlers.ts                  # EXTEND — 3 new MSW handlers
```

### Provenance design (BabylonScriptValue over spec-100 + live flows)

The `get_county_import_exposure` breakdown is the spec's deepest surface. It
mirrors the frontend `ScriptValue` Breakdown/Contributor types but is
computed server-side from two data sources:

```
total_exposure = Σ_bloc (weight_bloc × flow_bloc)

breakdown.contributors[i] = {
  label: "Canada",
  value: weight_canada × flow_canada,
  share: value / total,
  source: { kind: "derived", path: "exposure[26161][canada]" },
  children: [
    { label: "spec-100 exposure weight", value: 0.32, source: { kind: "reference_table", path: "county_exposure_by_external[canada][26161]" } },
    { label: "live Φ flow (DRAIN_EDGE)", value: 385.6, source: { kind: "dynamic_table", path: "boundary_flow_register[canada→26161]" } },
  ]
}

citations = [
  { id: "bea-io-2023", source: "BEA I-O imports", table: "fact_bea_io_coefficient", year: 2023 },
  { id: "qcew-2023q2", source: "QCEW county industry shares", table: "fact_qcew", year: "2023Q2" },
  { id: "hickel-drain", source: "Hickel drain", table: "immutable_reference_hickel_drain" },
]
```

When spec-100's table is absent, the weight child degrades to `value: 0,
source: { kind: "reference_table", path: "county_exposure_by_external (not yet built)" }`
and the flow child still renders if `boundary_flow_register` has rows. The
citations always render (they describe the reference-data lineage the weights
WILL trace to when spec-100 lands).

### TDD sequence

1. RED: `tests/unit/web/test_spec103_bridge.py` — 3 bridge method contract
   tests (mock pool seeded with boundary_flow_register + external_node rows).
2. RED: `tests/unit/web/test_api.py` — 3 new view tests.
3. RED: 3 frontend contract tests (MSW).
4. GREEN: backend bridge methods + views + routes.
5. GREEN: frontend types + hooks + components + MSW handlers.
6. REFACTOR: extract shared sparkline/bar primitives.

## File impact

| File | Action | Lines (est.) |
|------|--------|--------------|
| `web/game/engine_bridge.py` | EDIT — 3 methods + 3 helpers | +220 |
| `web/game/api.py` | EDIT — 3 views | +60 |
| `web/game/urls.py` | EDIT — 3 routes | +9 |
| `web/game/stub_bridge.py` | EDIT — 3 stub methods | +15 |
| `web/frontend/src/types/trade.ts` | NEW | +90 |
| `web/frontend/src/hooks/useTradeFlows.ts` | NEW | +80 |
| `web/frontend/src/hooks/useCountyExposure.ts` | NEW | +85 |
| `web/frontend/src/hooks/useTradePanel.ts` | NEW | +80 |
| `web/frontend/src/components/wire/BlocFlowLines.tsx` | NEW | +120 |
| `web/frontend/src/components/wire/bloc-flow.css` | NEW | +40 |
| `web/frontend/src/components/intel/ImportExposurePanel.tsx` | NEW | +160 |
| `web/frontend/src/components/intel/import-exposure.css` | NEW | +50 |
| `web/frontend/src/components/pages/TradePanel.tsx` | NEW | +130 |
| `web/frontend/src/components/pages/trade-panel.css` | NEW | +40 |
| `web/frontend/src/test/handlers.ts` | EDIT — 3 handlers | +120 |
| `web/frontend/src/components/wire/IndexPage.tsx` | EDIT — mount BlocFlowLines | +8 |
| `web/frontend/src/components/intel/TerritoryDetailView.tsx` | EDIT — mount panel | +12 |
| `web/frontend/src/components/pages/AnalysisPage.tsx` | EDIT — mount panel | +10 |
| `tests/unit/web/test_spec103_bridge.py` | NEW | +250 |
| 3 frontend contract tests | NEW | +150 |
