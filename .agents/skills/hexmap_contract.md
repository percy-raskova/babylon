# Skill: Contract-First React Component

## Objective

Build a React component end-to-end by using a mock JSON fixture as the API contract. The fixture defines the exact shape of data the Django API must return. The React component is built against this fixture. The Django backend is built to match it. A contract parity test proves they agree. This methodology uses frontend development as a specification tool for the backend.

## Rules of Engagement

- **Mock First**: Every component starts with a hand-crafted JSON fixture containing realistic Detroit test case data. This fixture IS the API contract. It is not throwaway scaffolding.
- **Contract Parity Gate**: Step 5 of the implementation order is the gate. If the API response shape does not match the fixture shape, do NOT proceed to React work. Fix the API.
- **Artifact Handover**: Save mock fixtures to `web/frontend/src/fixtures/`. Save Django code to `web/game/`. Save tests to `tests/`. Save React components to `web/frontend/src/components/`.
- **One Vertical Slice**: Each component is a full vertical slice — Postgres table, Django endpoint, API contract, React component, tests at every layer. Do not build all fixtures first, then all tables, then all endpoints. Go deep on one component before starting the next.
- **Constitutional Compliance**: Read `.agents/rules/babylon_constraints.md` before writing any code. The engine bridge, import boundary, color palette, edge mode display rules, and no-magic-constants rules are non-negotiable.

## Instructions

Follow the nine-step implementation order below. Each step produces a testable artifact before the next begins. Do not skip steps.

### Step 1 — Generate Mock Fixture

Create `web/frontend/src/fixtures/mock_map_data.json`.

This is a GeoJSON FeatureCollection with ~50 representative H3 resolution-7 hexagons covering metro Detroit. The hex boundaries must be real H3 geometry (use the `h3` Python library to generate them). The economic values are synthetic but directionally correct per the Detroit test case constraints.

Distribution:

- 15–20 hexes in Wayne County (downtown Detroit, Dearborn, River Rouge, Highland Park)
- 15–20 hexes in Oakland County (Southfield, Pontiac, Troy, Birmingham)
- 10–15 hexes in Macomb County (Warren, Sterling Heights, Mount Clemens)

The fixture must match this schema exactly:

```json
{
  "type": "FeatureCollection",
  "metadata": {
    "tick": 0,
    "scenario": "detroit_test",
    "h3_resolution": 7,
    "available_metrics": [
      "profit_rate", "exploitation_rate", "occ",
      "imperial_rent", "heat", "org_presence"
    ],
    "bounds": {
      "sw": [42.1, -83.5],
      "ne": [42.7, -82.9]
    }
  },
  "features": [
    {
      "type": "Feature",
      "id": "<h3_index>",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[ [lng, lat], ... ]]
      },
      "properties": {
        "h3_index": "<string>",
        "county_fips": "<string: 26163|26125|26099>",
        "county_name": "<string>",
        "profit_rate": "<float 0-1>",
        "exploitation_rate": "<float 0-1>",
        "occ": "<float 0-1>",
        "imperial_rent": "<float 0-1>",
        "heat": "<float 0-1>",
        "org_presence": "<int 0-N>",
        "dominant_class": "<string: LABOR_ARISTOCRACY|PROLETARIAT|PETIT_BOURGEOISIE|BOURGEOISIE|LUMPENPROLETARIAT>",
        "population": "<int>"
      }
    }
  ]
}
```

Directional realism requirements:

- Wayne County hexes: lower profit_rate (0.02–0.08), higher heat (0.3–0.7), higher exploitation_rate
- Oakland County hexes: higher profit_rate (0.08–0.15), lower heat (0.0–0.2), lower exploitation_rate
- Macomb County hexes: middle values on all metrics

Write a one-time generator script `scripts/generate_mock_hexes.py` that produces this fixture. Requires `h3` and `shapely`.

**Tests** (`tests/test_mock_fixture.py`, 5 tests):

```python
def test_fixture_is_valid_geojson():
    """Top-level keys: type, metadata, features."""

def test_fixture_has_required_metadata():
    """metadata contains tick, scenario, h3_resolution, available_metrics, bounds."""

def test_all_features_have_required_properties():
    """Every feature has all property keys from the schema."""

def test_county_distribution():
    """At least 10 hexes per county FIPS code."""

def test_directional_realism():
    """Mean profit_rate for Wayne < Macomb < Oakland."""
```

### Step 2 — Create Postgres Table + Seed Command

Create table `sim.hex_states` in the simulation schema (Feature 037 owns this schema).

```sql
CREATE TABLE IF NOT EXISTS sim.hex_states (
    id          SERIAL PRIMARY KEY,
    game_id     INTEGER NOT NULL REFERENCES game_gamesession(id),
    tick        INTEGER NOT NULL,
    h3_index    VARCHAR(20) NOT NULL,
    county_fips VARCHAR(5) NOT NULL,
    county_name VARCHAR(50) NOT NULL,
    profit_rate       DOUBLE PRECISION,
    exploitation_rate DOUBLE PRECISION,
    occ               DOUBLE PRECISION,
    imperial_rent     DOUBLE PRECISION,
    heat              DOUBLE PRECISION,
    org_presence      INTEGER DEFAULT 0,
    dominant_class    VARCHAR(30),
    population        INTEGER,
    UNIQUE(game_id, tick, h3_index)
);
CREATE INDEX idx_hex_game_tick ON sim.hex_states(game_id, tick);
```

Create Django management command `web/game/management/commands/seed_hex_data.py` that reads the mock fixture and inserts rows into `sim.hex_states` for a given GameSession.

**Tests** (`tests/test_hex_postgres.py`, 4 tests):

```python
def test_table_exists():
    """sim.hex_states table exists in Postgres."""

def test_seed_command_populates():
    """Running seed_hex_data creates rows matching fixture count."""

def test_unique_constraint():
    """Duplicate (game_id, tick, h3_index) raises IntegrityError."""

def test_county_fips_values():
    """All rows have county_fips in {26163, 26125, 26099}."""
```

### Step 3 — Implement EngineBridge Method

Add `get_map_snapshot(game_id, tick=None)` to `web/game/engine_bridge.py`.

This method queries `sim.hex_states` for the given game and tick (default: latest), builds H3 boundary polygons using the `h3` library, and returns a Python dict matching the exact fixture schema from Step 1. If tick is None, use `GameSession.current_tick`.

The method must produce output structurally identical to the mock fixture. Same keys, same nesting, same types. This is what the contract parity test verifies.

### Step 4 — Implement Django API Endpoint

Add `GET /api/games/{id}/map/` to `web/game/api.py`.

Response envelope:

```json
{
  "status": "ok",
  "data": { <GeoJSON FeatureCollection from EngineBridge> },
  "tick": 42,
  "session_id": "<uuid>"
}
```

Query parameter `?metric=profit_rate` optionally pre-computes `metric_range` (min/max for the requested metric across all features) and includes it in metadata. This enables the frontend to build color scales without iterating features client-side.

Requires session authentication. Returns 404 if game doesn't exist or isn't owned by the requesting user.

**Tests** (`tests/test_map_api.py`, 6 tests):

```python
def test_unauthenticated_returns_401()
def test_nonexistent_game_returns_404()
def test_wrong_user_returns_404()
def test_valid_request_returns_geojson()
def test_response_has_envelope()
def test_metric_range_included_when_requested()
```

### Step 5 — Contract Parity Test (THE GATE)

This is the critical test. It proves that the shape of data coming from the live API matches the shape of the mock fixture. If this test passes, swapping mock data for live API data in the React component is a zero-change operation.

```python
# tests/test_contract_parity.py

class ContractParityTest(TestCase):
    """
    Proves API response shape matches mock fixture shape.
    If this passes, React can swap from mock to live with zero changes.
    """

    def test_api_response_shape_matches_fixture(self):
        # Load fixture
        # Seed Postgres from fixture
        # Hit API endpoint
        # Assert: top-level keys identical
        # Assert: metadata keys — fixture keys are subset of API keys
        # Assert: feature property keys identical
        # Assert: feature geometry type is Polygon
        # Assert: feature has id field
```

**IF THIS TEST FAILS, STOP. Do not proceed to Step 6. Fix the API until the shapes match.**

### Step 6 — Color Scale Utility

Create `web/frontend/src/utils/colorScale.js`.

Maps metric values to constitutional palette colors. Each metric has its own gradient:

- `profit_rate`: CRIMSON (#8b0000) at low → GOLD (#daa520) at high
- `exploitation_rate`: GOLD at low → CRIMSON at high (inverted — high exploitation is bad)
- `heat`: ASH (#808080) at low → CRIMSON at mid → GOLD at high
- `occ`, `imperial_rent`: ASH at low → SILVER (#c0c0c0) at high
- `org_presence`: BLOOD_VOID (#1a0005) at 0 → GOLD at max

Function signature: `metricToColor(value, min, max, metricName) → hex color string`

All ranges derived from data (min/max passed in). No hardcoded breakpoints.

**Tests** (`web/frontend/src/utils/__tests__/colorScale.test.js`, 5 tests):

```javascript
test("returns CRIMSON for low profit_rate")
test("returns GOLD for high profit_rate")
test("handles heat metric with ash→crimson→gold gradient")
test("returns BLOOD_VOID for zero org_presence")
test("handles edge case where min equals max")
```

### Step 7 — HexMap React Component

Create `web/frontend/src/components/HexMap.jsx`.

Uses `react-leaflet` with MapContainer, TileLayer (CARTO dark tiles, no API key), and GeoJSON layer. Props:

```javascript
HexMap({ mapData, onHexSelect, selectedMetric, onMetricChange })
```

- Renders GeoJSON hexagons colored by `selectedMetric` using `colorScale.js`
- Metric selector dropdown showing `metadata.available_metrics`
- Click handler calls `onHexSelect(feature)` with the clicked feature
- Tick indicator showing `metadata.tick`
- Empty state: "No hex data loaded." when `mapData` is null
- Map centered on Detroit: `[42.35, -83.1]`, zoom 10

Dependencies to add to `package.json`: `leaflet`, `react-leaflet`.

**Tests** (`web/frontend/src/components/__tests__/HexMap.test.jsx`, 5 tests):

```javascript
test("renders without crashing with mock data")
test("shows empty state when no data provided")
test("renders metric selector with all available metrics")
test("renders tick indicator")
test("passes correct feature count to GeoJSON layer")
```

Mock `react-leaflet` in tests since it requires browser DOM + canvas.

### Step 8 — DevHarness with Mock Data

Create `web/frontend/src/DevHarness.jsx`.

A dev-only wrapper that imports the mock fixture and renders HexMap with it. This is the visual smoke test — open it in a browser and verify you see Detroit hexagons with color encoding.

Clicking a hex should `console.log` its `h3_index` and properties. The metric selector should change hex coloring. Wayne County hexes should be visibly darker than Oakland hexes when colored by `profit_rate`.

This step is manual verification, not automated tests.

### Step 9 — Swap Mock Data for Live API

Update `web/frontend/src/hooks/useGameState.js` (or create it) to fetch from `GET /api/games/{id}/map/` and pass the response to HexMap.

Because the contract parity test passed in Step 5, this swap should require zero changes to HexMap.jsx. The component doesn't know or care whether its data came from a JSON file or an API call.

Manual verification: the DevHarness now shows live data from Postgres instead of the static fixture.

## Approval Gate

After completing all 9 steps, verify the full acceptance criteria:

1. `pytest tests/test_mock_fixture.py` — 5 pass
1. `pytest tests/test_hex_postgres.py` — 4 pass
1. `pytest tests/test_map_api.py` — 6 pass
1. `pytest tests/test_contract_parity.py` — 1 pass
1. `npx vitest run` — 10 pass (color + component tests)
1. DevHarness renders a visible hex grid of Detroit with colored hexagons
1. Clicking a hex logs its `h3_index` and properties to console
1. Metric selector dropdown changes hex coloring
1. Wayne County hexes are visibly darker than Oakland hexes when colored by `profit_rate`
1. No hardcoded color breakpoints — all ranges derived from data

**Pause and report results before proceeding to the next component.**

## Scope Exclusions — Do NOT Implement

- **Leaflet vs deck.gl debate**: Use Leaflet. If performance is inadequate with 800+ polygons, swap later. The GeoJSON data contract is the same either way.
- **H3 resolution switching**: MVP renders all hexes at res 7 regardless of zoom level. Multi-resolution is deferred.
- **InspectorPanel**: The hex click emits a selection event via callback. The panel that displays hex detail is a separate component and a separate spec.
- **Tile server**: CARTO dark tiles, free tier, no API key. Swap to Mapbox or self-hosted later if unreliable.
- **Real engine data**: The mock fixture has synthetic economic values. Wiring to the actual simulation engine's Layer 0 output is a separate task.

## Files Created/Modified

```
web/
├── game/
│   ├── api.py                          # ADD map_view endpoint
│   ├── urls.py                         # ADD map URL pattern
│   ├── engine_bridge.py                # ADD get_map_snapshot()
│   └── management/commands/
│       └── seed_hex_data.py            # NEW
├── frontend/
│   ├── package.json                    # ADD leaflet, react-leaflet
│   └── src/
│       ├── components/
│       │   ├── HexMap.jsx              # NEW
│       │   └── __tests__/
│       │       └── HexMap.test.jsx     # NEW
│       ├── utils/
│       │   ├── colorScale.js           # NEW
│       │   └── __tests__/
│       │       └── colorScale.test.js  # NEW
│       ├── hooks/
│       │   └── useGameState.js         # ADD fetchMapData
│       ├── fixtures/
│       │   └── mock_map_data.json      # NEW
│       └── DevHarness.jsx              # NEW
tests/
├── test_mock_fixture.py                # NEW
├── test_hex_postgres.py                # NEW
├── test_map_api.py                     # NEW
└── test_contract_parity.py             # NEW
scripts/
└── generate_mock_hexes.py              # NEW
```
