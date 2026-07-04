# API Contract: `/api/observatory/*`

All endpoints:
- Require an authenticated session (DRF `IsAuthenticated`); unauthenticated →
  the product's standard 403/401.
- Return **404** (no body data) when `OBSERVATORY_ENABLED` is False — checked
  before any DB access (FR-018).
- On success return the standard product envelope
  `{"status": "ok", "data": <payload>}`; on error
  `{"status": "error", "message": <str>}` with an appropriate HTTP status
  (CSV endpoint excepted — it streams `text/csv`).
- Read the `sim` alias only; never write.

---

### `GET /api/observatory/status/`

Feature-flag probe for the frontend.

- **200** `{"status":"ok","data":{"enabled":true,"sim_alias":"sim"}}` when enabled.
- **404** when disabled.

---

### `GET /api/observatory/sessions/`

List sessions with at least one committed tick.

- **200** `data`: `SessionSummary[]` ordered by `max_tick` desc then
  `session_id`. Empty array when none (not an error).

---

### `GET /api/observatory/sessions/<session_id>/ticks/`

Committed tick range + checkpoint ticks for one session.

- **200** `data`: `TickRange`.
- **400** if `session_id` is not a UUID.
- **404** (envelope error) if the session has no committed ticks.

---

### `GET /api/observatory/sessions/<session_id>/series/`

Value-aggregate time-series.

Query params:
- `scope` = `national` (default) | `state` | `county`.
- `scope_id` — required for `state` (2 digits) and `county` (5 digits);
  ignored for `national`.
- `from_tick`, `to_tick` — optional inclusive bounds; default to the session's
  committed range; a maximum span caps the window.

- **200** `data`: `{session_id, scope, scope_id, from_tick, to_tick, points: ValueAggregatePoint[]}`.
  One point per committed tick in range (empty when the scope has no hexes).
- **400** on bad `scope`, missing/invalid `scope_id`, or `from_tick > to_tick`.

---

### `GET /api/observatory/sessions/<session_id>/series.csv/`

Same data as `series/` streamed as CSV.

- **200** `Content-Type: text/csv`, `Content-Disposition: attachment;
  filename="<session>_<scope>_<scope_id>.csv"`. Header row +
  one row per committed tick: `tick,c_sum,v_sum,s_sum,k_sum,biocapacity_sum,hex_count`.
- Same 400s as `series/`.

---

### `GET /api/observatory/sessions/<session_id>/commits/`

Per-tick commit chain summary. Bounded like `series/`.

Query params:
- `from_tick`, `to_tick` — optional inclusive bounds; default to the session's
  committed range; span capped (a national multi-hundred-tick chain is never
  returned unbounded per call).

- **200** `data`: `CommitRecord[]` ordered by tick asc.
- **400** on bad UUID, non-integer / out-of-INT4-range bound, or
  `from_tick > to_tick`.

---

### `GET /api/observatory/sessions/<session_id>/hex/`

Reconstructed hex frame at a committed tick (via `v_hex_state_asof`).
**Bounded + paginated** — a national res-7 frame is hundreds of thousands of
hexes, so the endpoint never buffers the whole frame.

Query params:
- `tick` — required (int, INT4-ranged).
- `county_fips` — optional 5-digit spatial filter.
- `limit` — optional page size (default 5000, hard cap 50000, min 1).
- `after_h3` — optional pagination cursor; returns only `h3_index > after_h3`.

- **200** `data`: `{session_id, tick, county_fips?, limit, hexes:
  HexStatePoint[], truncated: bool, next_h3: str|null}`. `truncated` is true
  when more rows exist; `next_h3` is the cursor for the next page (pass it as
  `after_h3`) or null when exhausted. Empty `hexes` when the tick is beyond the
  committed range or the county has no hexes (not an error).
- **400** on bad UUID, missing/invalid `tick` (incl. out-of-INT4-range), or
  `limit < 1`.

---

## Contract test coverage (frontend MSW + backend pytest)

| Endpoint | Backend pytest | Frontend MSW contract |
|---|---|---|
| `status/` (on/off) | gating unit + integration | disabled-banner render |
| `sessions/` | integration (seeded) | picker renders list |
| `.../ticks/` | integration | (used by browser) |
| `.../series/` (national/state/county) | integration | chart renders points |
| `.../series.csv/` | integration | client CSV mirror test |
| `.../commits/` | integration | contract pinned (`fetchCommits` MSW test) |
| `.../hex/` | integration (+ bound + carry-forward) | **backend-only** — no frontend hex client/type/MSW yet; deep hex consumption is spec-099 |
