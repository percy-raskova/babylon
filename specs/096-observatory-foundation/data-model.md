# Data Model (Read-Only): Observatory Foundation

The Observatory owns **no tables** and defines **no ORM models**. These are
*read* shapes projected from the runner-owned declared interfaces. Field names
mirror the underlying view columns (verified against
`src/babylon/persistence/migrations/0030_views_current.sql` and
`0029_tick_commit.sql`).

## SessionSummary  (from `tick_commit` [+ optional `game_session`])

| Field | Type | Source |
|---|---|---|
| `session_id` | UUID (str) | `tick_commit.session_id` |
| `min_tick` | int | `MIN(tick_commit.tick)` |
| `max_tick` | int | `MAX(tick_commit.tick)` |
| `tick_count` | int | `COUNT(*)` committed ticks |
| `checkpoint_count` | int | `COUNT(*) FILTER (WHERE is_checkpoint)` |
| `latest_hash` | str(64) | `determinism_hash` at `max_tick` |
| `scenario` | str \| null | `game_session.scenario` (optional enrichment) |
| `status` | str \| null | `game_session.status` (optional) |
| `created_at` | ISO str \| null | `game_session.created_at` (optional) |

## TickRange  (from `tick_commit`, one session)

| Field | Type | Source |
|---|---|---|
| `session_id` | UUID (str) | filter |
| `min_tick` | int | `MIN(tick)` |
| `max_tick` | int | `MAX(tick)` |
| `tick_count` | int | `COUNT(*)` |
| `checkpoint_ticks` | int[] | ticks where `is_checkpoint` |

## ValueAggregatePoint  (from `v_{national,state,county}_value_aggregate`)

| Field | Type | Notes |
|---|---|---|
| `tick` | int | committed tick |
| `scope` | "national"\|"state"\|"county" | request-derived |
| `scope_id` | str | `"USA"` / state_fips(2) / county_fips(5) |
| `c_sum` | float | constant capital |
| `v_sum` | float | variable capital |
| `s_sum` | float | surplus |
| `k_sum` | float | k |
| `biocapacity_sum` | float | biocapacity |
| `hex_count` | int | hexes summed |

A **series** is `{session_id, scope, scope_id, from_tick, to_tick, points[]}`.

## CommitRecord  (from `tick_commit`)

| Field | Type | Source |
|---|---|---|
| `tick` | int | `tick` |
| `determinism_hash` | str(64) | `determinism_hash` |
| `hex_rows_written` | int (≥0) | `hex_rows_written` |
| `is_checkpoint` | bool | `is_checkpoint` |
| `created_at_utc` | ISO str | `created_at_utc` |

## HexStatePoint  (from `v_hex_state_asof`)

| Field | Type | Source |
|---|---|---|
| `h3_index` | str | `h3_index` |
| `county_fips` | str | `county_fips` |
| `state_fips` | str | `state_fips` |
| `region_id` | str \| null | `region_id` |
| `c`,`v`,`s`,`k` | float | value tuple |
| `biocapacity_stock` | float | stock |
| `energy_stock` | float | stock |
| `raw_material_stock` | float | stock |
| `internet_access_pct` | float | coupling |
| `surveillance_coupling` | float | coupling |
| `written_at_tick` | int | the tick this row's value was actually written |

A **hex frame** is `{session_id, tick, county_fips?, hexes[]}`.

## Validation rules

- `session_id` is a UUID string; endpoints 400 on a non-UUID.
- Tick range: `from_tick ≤ to_tick`; a bounded window is enforced (default full
  committed range if omitted; a max span caps the payload).
- `scope=state` requires a 2-digit `scope_id`; `scope=county` a 5-digit one;
  `scope=national` ignores `scope_id` (`"USA"`).
- All numeric sums coalesce `NULL → 0.0`; `hex_count` coalesces `NULL → 0`
  (mirrors `postgres_aggregation.py`).
