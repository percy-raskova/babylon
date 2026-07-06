# Tasks: Trade Surfaces in the Product UI

**Spec**: 103-trade-surfaces

## Phase 0 — Speckit

- [x] T001 Create `specs/103-trade-surfaces/spec.md`
- [x] T002 Create `specs/103-trade-surfaces/plan.md`
- [x] T003 Create `specs/103-trade-surfaces/tasks.md`
- [x] T004 Create `specs/103-trade-surfaces/research.md`
- [x] T005 Create `specs/103-trade-surfaces/contracts/trade-flows.yaml`
- [x] T006 Create `specs/103-trade-surfaces/contracts/county-exposure.yaml`
- [x] T007 Create `specs/103-trade-surfaces/contracts/trade-panel.yaml`

## Phase 1 — RED tests (TDD red phase)

- [ ] T010 Red: `tests/unit/web/test_spec103_bridge.py` — `get_trade_flows`
      returns per-bloc series from mock pool seeded with boundary_flow_register
- [ ] T011 Red: `tests/unit/web/test_spec103_bridge.py` —
      `get_county_import_exposure` returns breakdown with contributors,
      children, source refs, citations
- [ ] T012 Red: `tests/unit/web/test_spec103_bridge.py` — `get_trade_panel`
      returns aggregate data from mock pool
- [ ] T013 Red: `tests/unit/web/test_spec103_bridge.py` — all 3 methods
      degrade to `has_data: False` when pool is None
- [ ] T014 Red: `tests/unit/web/test_api.py` — 3 new views return envelopes
- [ ] T015 Red: `web/frontend/src/__tests__/integration/trade-flows-contract.test.tsx`
- [ ] T016 Red: `web/frontend/src/__tests__/integration/county-exposure-contract.test.tsx`
- [ ] T017 Red: `web/frontend/src/__tests__/integration/trade-panel-contract.test.tsx`

## Phase 2 — Backend GREEN

- [ ] T020 Implement `_fetch_boundary_flow_series` helper in `engine_bridge.py`
- [ ] T021 Implement `_fetch_external_node_latest` helper in `engine_bridge.py`
- [ ] T022 Implement `_fetch_county_exposure_weights` helper in `engine_bridge.py`
- [ ] T023 Implement `get_trade_flows` in `engine_bridge.py`
- [ ] T024 Implement `get_county_import_exposure` in `engine_bridge.py`
- [ ] T025 Implement `get_trade_panel` in `engine_bridge.py`
- [ ] T026 Add 3 stub methods to `stub_bridge.py`
- [ ] T027 Implement `game_trade_flows` view in `api.py`
- [ ] T028 Implement `game_county_exposure` view in `api.py`
- [ ] T029 Implement `game_trade_panel` view in `api.py`
- [ ] T030 Add 3 routes in `urls.py`
- [ ] T031 Verify backend tests green: `PYTHONPATH=src poetry run pytest tests/unit/web/ -q`

## Phase 3 — Frontend GREEN

- [ ] T035 Create `types/trade.ts` (TradeFlowsPayload, ExposurePayload, TradePanelPayload)
- [ ] T036 Create `hooks/useTradeFlows.ts`, `hooks/useCountyExposure.ts`, `hooks/useTradePanel.ts`
- [ ] T037 Create `components/wire/BlocFlowLines.tsx` + `bloc-flow.css`
- [ ] T038 Create `components/intel/ImportExposurePanel.tsx` + `import-exposure.css`
- [ ] T039 Create `components/pages/TradePanel.tsx` + `trade-panel.css`
- [ ] T040 Mount `BlocFlowLines` in `IndexPage.tsx`
- [ ] T041 Mount `ImportExposurePanel` in `TerritoryDetailView.tsx`
- [ ] T042 Mount `TradePanel` in `AnalysisPage.tsx`
- [ ] T043 Add 3 MSW handlers in `test/handlers.ts`
- [ ] T044 Verify frontend tests green: `mise run web:check`

## Phase 4 — Gates

- [ ] T050 `mise run web:check` green (3 pre-existing tick-resolution failures acceptable)
- [ ] T051 `PYTHONPATH=src poetry run pytest tests/unit/web/ -q` green
- [ ] T052 Playwright e2e (owner-run, gated on `SPEC061_TEST_SESSION_ID`)
- [ ] T053 County-exposure contract test passes — drill-down chain ends at citations
- [ ] T054 3 MSW contract tests pass

## Phase 5 — Governance

- [ ] T060 Update `ai-docs/state.yaml`
- [ ] T061 Create ADR in `ai-docs/decisions.yaml`
- [ ] T062 Commit all work
