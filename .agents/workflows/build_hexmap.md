# Workflow: Build HexMap E2E

Build the HexMap component as a full vertical slice using the contract-first methodology defined in `.agents/skills/hexmap_contract.md`.

## Pre-Flight

1. Read `.agents/rules/babylon_constraints.md` — internalize the project constraints.
1. Read `.agents/skills/hexmap_contract.md` — this is your implementation spec.
1. Verify the workspace has `web/game/` (Django app) and `web/frontend/src/` (React app) directories. If not, flag the missing structure before proceeding.
1. Verify Python dependencies: `h3`, `shapely`, `django`, `psycopg2`. Verify Node dependencies: check `web/frontend/package.json` exists.

## Phase 1 — Mock Fixture (Steps 1)

1. Write `scripts/generate_mock_hexes.py` using real H3 geometry for Detroit tri-county.
1. Run it to produce `web/frontend/src/fixtures/mock_map_data.json`.
1. Write `tests/test_mock_fixture.py` (5 tests).
1. Run `pytest tests/test_mock_fixture.py` — all 5 must pass.
1. **Report results. Pause for approval before proceeding.**

## Phase 2 — Backend Contract (Steps 2–5)

1. Create `sim.hex_states` Postgres table via migration or raw SQL.
1. Write `seed_hex_data.py` management command.
1. Write `tests/test_hex_postgres.py` (4 tests). Run them.
1. Implement `EngineBridge.get_map_snapshot()` in `web/game/engine_bridge.py`.
1. Implement `GET /api/games/{id}/map/` in `web/game/api.py`.
1. Write `tests/test_map_api.py` (6 tests). Run them.
1. Write `tests/test_contract_parity.py` (1 test). Run it.

**Step 5 is the gate. If `test_contract_parity.py` fails, do NOT proceed. Fix the API until the response shape matches the mock fixture shape exactly. Report the failure and what diverged.**

8. **Report results: 4 + 6 + 1 = 11 backend tests. Pause for approval.**

## Phase 3 — Frontend (Steps 6–8)

1. Add `leaflet` and `react-leaflet` to `web/frontend/package.json`. Install.
1. Implement `colorScale.js` with constitutional palette gradients.
1. Write `colorScale.test.js` (5 tests). Run with `npx vitest run`.
1. Implement `HexMap.jsx` with Leaflet + GeoJSON rendering.
1. Write `HexMap.test.jsx` (5 tests). Run with `npx vitest run`.
1. Create `DevHarness.jsx` importing the mock fixture.
1. **Take a screenshot of the DevHarness showing Detroit hexagons. Attach as artifact.**
1. **Report results: 10 frontend tests. Pause for approval.**

## Phase 4 — Integration (Step 9)

1. Wire `useGameState.js` to fetch from the live API endpoint.
1. Verify DevHarness now shows live Postgres data instead of static fixture.
1. Confirm zero changes were needed in `HexMap.jsx` for the swap.
1. **Take a screenshot of live data rendering. Attach as artifact.**

## Final Verification

Run the full acceptance checklist from the skill file. Report pass/fail for each of the 10 criteria. Do not mark the task complete until all 10 pass.
