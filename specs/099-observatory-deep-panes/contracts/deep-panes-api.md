# API Contract: Observatory deep panes (`/api/observatory/*`)

Cross-cutting (all endpoints, inherited from 096): flag-gated (404 when
`OBSERVATORY_ENABLED` off, before auth/DB), auth-gated (`IsAuthenticated`),
clean 503 on data error (server-side logged), envelope `{status, data}`.

**`source` query param** (added to 096's + all 099 endpoints): `live` (default)
or `archive`. Invalid → 400. `archive` reads Parquet under
`BABYLON_ARCHIVE_ROOT/<session_id>/` read-only; a missing dir/table → empty.

---

### `GET /api/observatory/sessions/<id>/verify/?source=`

Hash-chain structural verification.

- **200** `data`: `{session_id, source, valid: bool, min_tick, max_tick,
  tick_count, checkpoint_ticks: int[], expected_checkpoint_cadence, anomalies:
  [{kind, tick, detail}]}`. `kind` ∈ `gap | duplicate | bad_checkpoint |
  bad_hash`. `valid` iff `anomalies == []`.
- **400** bad uuid / bad source. Empty session → `valid:true` with empty range.

### `GET /api/observatory/sessions/<id>/boundary/?source=&from_tick=&to_tick=`

Boundary-flow explorer over the flow register.

- **200** `data`: `{session_id, source, from_tick, to_tick, by_flow_type:
  [{flow_type, row_count, total_magnitude}], rows: [{tick, source_node_id,
  source_kind, dest_node_id, dest_kind, flow_type, magnitude}]}` (rows capped by
  span; grouped summary always present). Empty register → both empty (not error).

### `GET /api/observatory/sessions/<id>/conservation/?source=&from_tick=&to_tick=&severity=`

Conservation-audit browser.

- **200** `data`: `{session_id, source, from_tick, to_tick, rows: [{tick, scale,
  invariant_name, computed_value, expected_value, residual, severity}]}`.
  `severity=non_ok` → warn+alarm only; default all. Empty → empty.
- **400** on unknown `severity`.

### `GET /api/observatory/diff/?a=<sid>&b=<sid>&source=&from_tick=&to_tick=`

Two-session diff.

- **200** `data`: `{a, b, source, national: [{tick, a_v_sum, b_v_sum, delta}],
  commits: {a: {min_tick,max_tick,tick_count}, b: {...}, tick_count_delta,
  range_delta}}`. Series aligned by tick (outer join); missing side → null +
  delta uses 0. Self-diff → all deltas 0.
- **400** bad uuid (a or b) / bad source.

---

### `source` on 096 endpoints

`sessions/`, `.../ticks/`, `.../series/` (national only for archive — no
`hex_spatial_map` in archives), `.../commits/`, `.../hex/` all accept `source`.
Archive-source state/county series is a documented no-op (empty) — national,
commits, verify, boundary, conservation are the archive-supported reads.

## Coverage

| Endpoint | Backend pytest | Frontend MSW |
|---|---|---|
| `verify/` (live+archive, ok+gap) | unit + integration | verdict render |
| `boundary/` (empty-state) | unit + integration | empty-state render |
| `conservation/` (rows + filter) | unit + integration | rows + filter |
| `diff/` | integration | series+delta render |
| `source=archive` (edf07b2e) | integration (real archive) | selector |
