# M5 Maps — seam contracts (Tasks 37–40)

**Charter:** plan `docs/superpowers/plans/2026-07-26-ratatui-client.md`
§M5. Recon: 3-scout sweep `wf_88f20c03-3eb`. Branch `feature/ratatui-m5`
off post-Wave-1 dev. Design row of record: "Live choropleth: county/state
tiers from `v_hex_state_asof` (never raw `dynamic_hex_state`); lenses
value|tension|fog; zoom/pan; county WKT polygons from reference data via
host."

## 1. `choropleth_json(args_json)` — call1 (host), Task 37

- Arg `{"tier": "county"|"state"|"ea", "lens": "value"|"tension"|"fog"}`
  (field order pinned; the M4 `topology_json` args pattern). Unknown tier
  or lens raises a loud `ValueError` through the session (the M4
  out-of-vocabulary precedent — never laundered to `null`).
- Three-layer shape, verbatim from M4: `CampaignHandle.choropleth_view(
  tier, lens) -> dict | None` (@runtime_checkable Protocol member) →
  `GameSession.choropleth_view` (compute fresh, never cache) →
  `RustClientHost.choropleth_json` thin passthrough; `"null"` string is
  the sole absence signal (unbound session, or an empty tier).
- **_FakeCampaign Protocol-widening sweep (the M4 trap, pre-scouted):**
  exactly 4 files carry `isinstance(..., CampaignHandle)` seams and need
  the no-op stub — `test_app_dashboard_live`, `test_app_hud_live`,
  `test_app_action_bar_live`, `test_app_lobby_flow`. The ~9 deliberately
  narrow doubles stay untouched.
- Envelope (hand-built dict, the M4 discipline):
  `{"tier", "lens", "verified_tick", "bands": [[threshold|null, role]...],
  "cells": [{"region_id", "value": float|null, "wkt": str|null,
  "centroid": [lon, lat]|null}...]}`.
  - `bands` ships the `map_room._band_color` table AS DATA (plan ruling:
    bands are data, not Rust literals): `[[null,"panel"],[1.0,"dim"],
    [2.0,"gold"],[null,"crimson"]]` — null threshold on the absence row
    and the open-ended top band; roles are §9b tokens the client maps to
    its parity-guarded constants.
  - `cells` values: lens `value` = exploitation rate from
    `county_choropleth_cells` (county tier — reads the registered
    `v_county_value_aggregate`) / `state_choropleth_cells_from_hex_rows`
    (state tier — reads `v_hex_state_asof` rows ONLY; the producer's own
    multi-tick ValueError guard is the spec-089 discipline, kept).
  - `wkt` comes from `persistence.tiger_ingestion.
    fetch_county_geometries_wkt(pool, geoids)` — **the first production
    caller of that wired-but-unconsumed seam** (county tier only; state
    tier ships `wkt: null` + centroid-less cells this milestone —
    dissolving state boundaries from county WKT is real work with no
    consumer pull yet). EPSG:4269 ≈ WGS84 for CONUS; the client treats
    lon/lat as plain x/y (equirectangular — honest at county scale).
- **LENS DISCLOSURE (Director-visible, the §9.9 pattern):** only the
  `value` lens has a producer anywhere in the codebase. `tension` and
  `fog` return cells with `value: null` for every region plus the
  envelope's `"lens_absent_reason"` string naming the missing producer
  ("no tension scalar exists on DynamicHexState"; "the epistemic fog
  package is not wired to choropleth cells") — rendered as a declared
  absence banner, never fabricated data (III.11 / Mock Doctrine).
  Landing either producer is engine-train work outside M5's charter.
- **EA tier**: `ea_choropleth_cells` returns None by design (no bridge)
  — the envelope for `tier: "ea"` is `"null"` absence; the client's tier
  cycle SKIPS ea until a producer exists (recorded here, not a bug).
- **TUTORIAL-CAMPAIGN DISCLOSURE:** the WAYNE scenario's territories
  carry NO `county_fips` and NO hex-state rows — the live tutorial
  campaign's map pane renders honest absence naming this cause. The
  harness pins the absence line (pin-goes-red = producer-landed
  announcement, the M4 §9.9 mechanism). Non-empty rendering is proven by
  fixture-fed tests (tri-county FIPS 26163/26125/26099 + real TIGER WKT
  fixtures).

## 2. MapView canvas (Task 38)

- `views/map.rs`, the TopologyView shape verbatim: `MapView { tier,
  lens, payload: Option<ChoroplethPayload>, payload_failed: bool,
  viewport }` chrome-owned on `PlayChrome`; `ingest_choropleth(raw)`
  with the loud parse-failure flag; `args_json()`; `mod
  view_state_tests` pure state-machine pins.
- Render: `ratatui::widgets::canvas::Canvas`, `Marker::HalfBlock`
  (2-colors-per-cell — the richest cell form), `x_bounds`/`y_bounds`
  from the cells' WKT bounding box (plus margin).
- **Polygon fill is a hand-written `Shape`** (recon: NO built-in
  polygon fill exists in ratatui 0.30) — scanline point-in-polygon over
  the painter grid within the polygon's bbox, colored by the band the
  cell's value falls in (bands from the ENVELOPE, resolved to the
  parity-guarded theme constants by role name). Exterior-ring-only for
  v1.0 (county WKT holes are negligible at braille resolution — noted).
- Absent `value` (null) fills with PANEL (the absence band row);
  absent `wkt` renders the region as a labeled centroid dot only, or —
  when every cell lacks geometry — the honest-absence line naming the
  tier's state. `lens_absent_reason` renders as a one-line CRIMSON
  banner over the canvas (declared, the pixel-degradation precedent).
- Labels: `Context::print` for region ids at centroids (labels always
  draw on top — recon).

## 3. Keys + chrome integration (Tasks 38/40)

- The Pane::Map absence fence arm is REPLACED by `chrome.map.render`;
  `refresh_map()` mirrors `refresh_topology()` (pane-entry '2' fetch +
  `refresh_after_tick` gate — without it the pane goes silently stale).
- Map-pane key block inserted BEFORE the wiki fallthrough (the
  match-arm-order trap, third time): **`l` cycles lens** value→tension→
  fog→value (RECORDED DEVIATION from the plan's "1/2/3 lens switch" —
  digits 1–4 are the GLOBAL pane-switch keys and cannot be shadowed
  pane-locally without breaking the '1'-'4' contract §1 wire; the 'g'
  kind-cycle precedent applies instead). **`t` cycles tier**
  county→state (ea skipped per §1)... `t` is the GLOBAL tick key —
  ALSO taken. Tier cycle key: **`y`** (mnemonic: tier). Zoom `+`/`-`,
  arrows pan, `0` reset viewport (topology camera-key parity), `Esc` →
  wiki. Every arm returns the `MapAction` mirror of `TopologyAction`.
- Wheel (Wave 1 §5): the `Pane::Map` no-op arm in the region:center
  wheel route becomes zoom in/out (the topology-3D precedent).
- Keybar: `KeybarSurface::Map` variant — `l lens · y tier · +/- zoom ·
  ←→↑↓ pan · 0 reset · Esc wiki` + the global tail; help section added
  (one source of truth holds).
- Viewport math (Task 40): pan shifts both bounds by 10% of span;
  zoom scales spans by ×0.8 / ×1.25 about the center, clamped to the
  data bbox ±1 span; `0` restores the fitted bbox. Pure functions,
  unit-tested.

## 4. Extrusion (Task 39) — SLICED to v1.1

The prereq is NOT built at the pinned hypergraph-rs rev: h3o 0.10's
`CellIndex::boundary()` exists in the dep but nothing converts spherical
boundaries to scene space; `sankey.rs::ground_hex` is still a synthetic
regular hexagon; no general fan-triangulate exists. The plan's own BD-4
rule ("if this would delay v1.0, it slips to v1.1 with a one-line
ADR150 note — before it delays anything else") FIRES: sliced, ADR150
note lands with the M5 close-out. No sibling-repo work this milestone.

## 5. Testing + goldens

- TDD red-first per unit. Python: contract tests over choropleth_view /
  choropleth_json with tri-county fixtures (real FIPS, small synthetic
  WKT squares — deterministic, no drive reads: CI never touches the
  babylon-data drive); the spec-089 multi-tick guard pinned; the lens
  disclosure pinned; the 4 _FakeCampaign stubs.
- Rust: view_state_tests (lens/tier cycles, loud parse flag, viewport
  math); a frame-content golden per lens over a 3-cell fixture — pin
  CONTENT (band-colored braille/halfblock cells present, absence
  banner text) never just titles (the golden-certifies-what-you-render
  class, strike three's lesson).
- The M3/M4 harness: the WAYNE arc's map-pane beat flips from the
  MAP_FENCE line to the pane's own honest-absence line — transcript
  golden regen (wheel-first), the fence pin in
  `test_pane_fences_render_under_the_strip` updates for Map.
- Smoke (Task 40 close-out): fixture-fed tri-county render at county
  tier — 3 filled polygons in 3 bands; the "tri-county" ambiguity the
  recon flagged (WAYNE ≠ detroit_tri_county) is resolved AS the
  fixture-fed reading: the detroit_tri_county scenario's committed
  golden is county-aggregated, matching the county tier exactly.

## 6. Deviations discovered during implementation

(recorded as they arise)
