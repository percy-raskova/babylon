# Research: Trade Surfaces in the Product UI

**Spec**: 103-trade-surfaces

## R1 — Existing data model (verified 2026-07-05)

### boundary_flow_register (spec-062, FR-040/R2)

Table schema (`src/babylon/persistence/migrations/0013_boundary_flow_register.sql`):
```
session_id, tick, source_node_id, source_kind, dest_node_id, dest_kind,
flow_type, magnitude
```
- `flow_type` ∈ {drain_edge, trade_inbound, trade_outbound, commute_outbound}
  (BoundaryEdgeKind enum).
- `source_kind`/`dest_kind` ∈ {hex, county, state, national, external}
  (NodeKind enum).
- For Φ distribution: source=external, dest=county, flow_type=drain_edge.
- Existing query pattern: `run_summary.py:aggregate_external_node_flows`
  groups by `dest_node_id` with `FILTER (WHERE flow_type = ...)` sums.

### dynamic_external_node_state (spec-062, §2.2)

`ExternalNode` Pydantic model (`src/babylon/persistence/external_node.py`):
```
session_id, tick, node_id, kind, phi_year_inflow, bilateral_trade_value,
bilateral_trade_tons, erdi_ratio
```
- 9 nodes: canada, china, eu, india, sub_saharan_africa, latin_america,
  russia_csi, southeast_asia (international) + rest_of_usa (domestic_rest).
- `erdi_ratio` > 0 — the unequal-exchange index (exchange-ratio deviation).
- Hydrated via `PostgresRuntime.hydrate_state()`.

### county_exposure_by_external (spec-100 — NOT YET BUILT)

Spec-100 builds `county_exposure_by_external`: per external bloc, county
weights from `fact_bea_io_coefficient` import coefficients × QCEW county
industry shares. Persisted as a new reference table in
`src/babylon/reference/schema.py`. The engine's
`phi_distribution.py:distribute_phi_week_to_counties` takes
`county_exposure: Mapping[str, float]` (county_fips → weight, weights sum to
1.0) per external node.

**Status**: spec-100 is Lane D, unbuilt. The reference table does not exist.
The bridge's `_fetch_county_exposure_weights` helper will query it
defensively (try/except → empty list). The exposure panel's weight child
degrades to zero with an "not yet built" source path. Forward-compatible:
when spec-100 lands, the weights populate without a frontend change.

## R2 — DB topology (verified 2026-07-05)

The W-lane product DB (5432/babylon) does NOT carry `boundary_flow_register`
or `dynamic_external_node_state` — confirmed via `psql` (tables absent). Those
live in the SIM DB (5433/babylon_test) per spec-096's two-DB alias map. The
bridge's persistence pool reads from whichever DB the runtime configures. In
dev/test (SQLite, per `conftest.py`), the pool is a mock — the methods degrade
to `has_data: False`.

This is the SAME pattern as spec-095's `_fetch_contradiction_field_rows`:
query the pool, catch exceptions, degrade to empty. The MSW fixtures carry the
full response shape so frontend tests + Playwright exercise the complete
drill-down chain.

## R3 — Bridge SQL query pattern (verified)

`_fetch_contradiction_field_rows` (engine_bridge.py:138) is the template:
```python
def _fetch_contradiction_field_rows(pool, session_id):
    if pool is None:
        return []
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT ... FROM contradiction_field WHERE ...", (session_id,))
            rows = cur.fetchall()
            # normalize tuple-or-dict rows → list[dict]
        return result
    except Exception:
        logger.exception(...)
        return []
```

Key details:
- `pool.connection()` context manager (psycopg3-style).
- `conn.cursor()` returns rows as dicts (RealDictCursor) or tuples — the
  normalization handles both.
- Exception → empty list (non-fatal degradation).

## R4 — Frontend provenance system (verified)

The `ScriptValue<T>` selector system (`lib/selectors/types.ts`) provides:
- `Breakdown { total, contributors }`
- `Contributor { label, value, share, source: SourceRef, children }`
- `SourceRef { kind: "snapshot_field"|"gamedefines"|"derived", path }`
- `BreakdownTooltip` renders a click-to-open Radix Popover with a recursive
  `BreakdownTree` (max depth 4).

The import-exposure breakdown is server-computed (not a frontend selector),
so it reuses the `Contributor`/`SourceRef` shape but with extended source
kinds (`reference_table`, `dynamic_table`). The `ImportExposurePanel` renders
the drill-down tree using the same visual pattern as `BreakdownTree` but fed
from server data. This honors the "BabylonScriptValue over spec-100 weights +
live boundary_flow_register flows" requirement at the backend, while the
frontend renders the chain.

## R5 — Ratified trade-UI decision

Per project/09 (lines 403-411) and the master plan scope:
- **Blocs are background noise** — no dedicated bloc screen; blocs surface as
  sparklines/bars within CONUS-primary screens.
- **No interactive world map** — CONUS stays the primary spatial view.
- **Three surfaces**: Wire INDEX per-bloc lines, Territory Detail exposure
  breakdown, Analysis trade panel.
- Bridge trade sections built WITH these panels (the bridge methods are
  co-designed with the panels that consume them).

## R6 — External node labels

The 8 international blocs + 1 domestic rest node map to display labels:
| node_id | label | kind |
|---------|-------|------|
| canada | Canada | international |
| china | China | international |
| eu | EU | international |
| india | India | international |
| sub_saharan_africa | Sub-Saharan Africa | international |
| latin_america | Latin America | international |
| russia_csi | Russia/CSI | international |
| southeast_asia | Southeast Asia | international |
| rest_of_usa | Rest of USA | domestic_rest |

The Wire INDEX surfaces all 9 (rest_of_usa included — it's a domestic flow
sink). The Analysis trade panel surfaces the 8 international blocs
prominently (rest_of_usa as a secondary row).
