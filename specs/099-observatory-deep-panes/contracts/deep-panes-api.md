# API Contract: Observatory deep panes (`/api/observatory/*`)

Cross-cutting (all endpoints, inherited from 096): flag-gated (404 when
`OBSERVATORY_ENABLED` off, before auth/DB), auth-gated (`IsAuthenticated`),
clean 503 on data error (server-side logged), envelope `{status, data}`.

**`source` query param** (added to 096's + all 099 endpoints): `live` (default)
or `archive`. Invalid → 400. `archive` reads Parquet under
`BABYLON_ARCHIVE_ROOT/<session_id>/` read-only; a missing dir/table → empty.

---

### `GET /api/observatory/sessions/<id>/verify/?source=`

Hash-chain **structural** verification — tick contiguity, checkpoint cadence,
and hash FORMAT (length) only. **This is NOT content/tamper verification**:
the hash is never recomputed or compared against tick inputs. See
"Hash-chain verification scope" below for why.

- **200** `data`: `{session_id, source, valid: bool, min_tick, max_tick,
  tick_count, checkpoint_ticks: int[], expected_checkpoint_cadence,
  verification_scope: "structural", anomalies: [{kind, tick, detail}]}`.
  `kind` ∈ `gap | duplicate | bad_checkpoint | bad_hash` (`bad_hash` = wrong
  LENGTH, not wrong content). `valid` iff `anomalies == []`.
- **400** bad uuid / bad source. Empty session → `valid:true` with empty range.

### `GET /api/observatory/sessions/<id>/boundary/?source=&from_tick=&to_tick=`

Boundary-flow explorer over the flow register.

- **200** `data`: `{session_id, source, from_tick, to_tick, by_flow_type:
  [{flow_type, row_count, total_magnitude}], rows: [{tick, source_node_id,
  source_kind, dest_node_id, dest_kind, flow_type, magnitude}], truncated:
  bool}` (rows capped by span; grouped summary always present and NOT capped —
  only `rows` is; `truncated=true` means more raw rows exist than were
  returned). Empty register → both empty (not error).

### `GET /api/observatory/sessions/<id>/conservation/?source=&from_tick=&to_tick=&severity=`

Conservation-audit browser.

- **200** `data`: `{session_id, source, from_tick, to_tick, rows: [{tick, scale,
  invariant_name, computed_value, expected_value, residual, severity}],
  truncated: bool}`. `severity=non_ok` → warn+alarm only; default all. Empty →
  empty. `truncated=true` means more rows exist than the cap returned.
- **400** on unknown `severity`.

### Hash-chain verification scope (ground truth, 2026-07-04 adversarial-review fix)

`tick_commit.determinism_hash` is written by the headless runner as
`sha256(f"{session_id}:{tick}:{random_seed}")` — an IDENTITY hash over three
scalars, NOT a hash of tick inputs (world state / hex rows / actions). A
genuine CONTENT hash (`babylon.persistence.conservation_audit.compute_determinism_hash`,
hashing canonicalized `tick + sorted hex_state + actions + rng_seed` per
Constitution III.7) exists but is written to `conservation_audit_log.determinism_hash`
— a different column on a different table this pane does not read. Even the
shallow identity hash's `random_seed` is not reliably recoverable from
persisted session metadata for headless-runner (canonical/national) sessions
(`game_session.rng_seed` keeps its DDL default of 0 for those runs). Genuine
per-tick recomputation is therefore not implementable here without either a
`tick_commit` schema change or re-running the engine (forbidden by FR-008).
`verify_chain` / `/verify/` are scoped accordingly: structural checks only,
honestly labeled via `verification_scope: "structural"` and the frontend's
"STRUCTURE OK" / "STRUCTURE ANOMALY" wording (never "CHAIN VALID"). See the
spec-099 fix report for the full investigation.

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

**`.../hex/?source=archive` is dispatched but NOT implemented — explicit
`501`**, not silent empty/stale data (2026-07-04 adversarial-review fix #3).
The archived Parquet export deliberately excludes `hex_spatial_map` (reference
data, not session-keyed — see spec-088); every archived `dynamic_hex_state`
row's `county_fips`/`state_fips`/`region_id` are persisted NULL (verified:
0 non-null rows in the real archived session's `dynamic_hex_state.parquet`).
A per-hex archive reconstruction would therefore always come back with no
usable spatial keys — silently breaking the `county_fips` filter and
county/state display — which is worse than an honest "not supported yet"
error. Implementing this for real requires either archiving `hex_spatial_map`
per-session (schema/export change) or a separate reference-data read path —
an owner decision, tracked in the fix report's owner-review queue, not done
here. `source=live` for `hex/` is unaffected (unchanged behavior).

## Coverage

| Endpoint | Backend pytest | Frontend MSW |
|---|---|---|
| `verify/` (live+archive, ok+gap) | unit + integration | verdict render |
| `boundary/` (empty-state) | unit + integration | empty-state render |
| `conservation/` (rows + filter) | unit + integration | rows + filter |
| `diff/` | integration | series+delta render |
| `source=archive` (edf07b2e) | integration (real archive) | selector |
