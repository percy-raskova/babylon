# Research & Decisions: Observatory Foundation

All facts verified in-repo 2026-07-03 on branch `096-observatory-foundation`.

## D1 — How to attach a read-only second Postgres to Django

**Decision**: Add a `DATABASES["sim"]` alias using the plain
`django.db.backends.postgresql` backend (NOT the PostGIS backend the `default`
alias uses). The value-aggregate views and `tick_commit` return no geometry, so
GIS is unneeded and adds coupling. Read-only enforced at the connection level
via libpq options:

```python
"OPTIONS": {"options": "-c default_transaction_read_only=on"}
```

Django passes `OPTIONS` into the psycopg connection; the `options` key becomes
the libpq `options` parameter, and `-c default_transaction_read_only=on` sets
that server GUC for every connection. Any write then raises
`psycopg.errors.ReadOnlySqlTransaction`.

**Rationale**: Declarative, per-alias, no signals or middleware. Matches how
`tests/integration/web/conftest.py` already registers a second `postgres`
alias at runtime; we make ours permanent config.

**Alternatives rejected**:
- `connection_created` signal issuing `SET default_transaction_read_only` — more
  moving parts, easy to forget on pooled reconnects.
- A read-only DB *role* — correct in production but out of scope; the runner's
  local container uses a superuser test role, and the GUC guarantees read-only
  regardless of role privileges.

## D2 — DSN parsing

**Decision**: `BABYLON_PG_DSN` is a libpq keyword DSN
(`host=localhost port=5433 dbname=babylon_test user=test password=test`), the
exact default in `tools/tick_probe.py`. Parse it into Django's
HOST/PORT/NAME/USER/PASSWORD via a small helper `build_sim_database_alias(dsn)`.
`psycopg.conninfo.make_conninfo` + `conninfo_to_dict` gives a robust parse; a
tiny hand parser is the fallback. `NAME` maps from `dbname`.

**Rationale**: Reusing the tick_probe DSN shape means an operator who already
runs the sim can point the Observatory at it with the same string. Factoring
the builder into a pure function makes it unit-testable with no DB.

## D3 — Migration refusal

**Decision**: `SimDatabaseRouter.allow_migrate(db, app_label, model_name=None,
**hints)` returns `False` iff `db == "sim"`, else `None`. Registered in
`settings.DATABASE_ROUTERS`. The `observatory` app additionally declares **no
models**, so it contributes no migrations at all.

**Rationale**: Two independent guarantees. The runner's `_apply_migrations`
(`src/babylon/engine/headless_runner/runner.py`, globbing
`migrations/00*.sql`) is the *sole* owner of the `dynamic_*` schema; Django must
never attempt DDL there. `allow_migrate=False` is the Django-blessed mechanism.

## D4 — Session source of truth

**Decision**: Derive the session list from `tick_commit` (grouped by
`session_id`): min/max tick, committed-tick count, checkpoint count, latest
hash. LEFT JOIN `game_session` for optional `scenario`/`status`/`created_at`.

**Verified**: On live `localhost:5433/babylon_test`, `tick_commit` holds 58
probe sessions; `game_session` also exists there with 58 rows (columns
`id, player_id, scenario, current_tick, status, …`). `game_session.id` is
CHAR(32) hex (no dashes); `tick_commit.session_id` is a UUID. Join key:
`game_session.id = replace(tick_commit.session_id::text, '-', '')`. LEFT JOIN so
sessions without a `game_session` row still list (FR-007).

**Rationale**: `tick_commit` is the spec-089 authoritative commit marker — the
only reliable "these ticks committed" record under delta persistence.
`MAX(tick) FROM dynamic_hex_state` is explicitly NOT the last committed tick.

## D5 — Hex reads via as-of view

**Decision**: The hex-frame endpoint reads `v_hex_state_asof` filtered by
`session_id` + `tick` (+ optional `county_fips`). Never `dynamic_hex_state` by
tick.

**Verified**: `0030_views_current.sql` defines `v_hex_state_asof` as the
full-resolution reconstruction (checkpoint + deltas, fill-forward) — the
declared hex-history read interface (spec-089 FR-009). Raw `dynamic_hex_state`
is sparse.

## D6 — View column contracts (verified against 0030_views_current.sql)

- `v_national_value_aggregate(session_id, tick, national_id, c_sum, v_sum,
  s_sum, k_sum, biocapacity_sum, hex_count)`
- `v_state_value_aggregate(session_id, tick, state_fips, c_sum, v_sum, s_sum,
  k_sum, biocapacity_sum, hex_count)`
- `v_county_value_aggregate(session_id, tick, county_fips, c_sum, v_sum, s_sum,
  k_sum, biocapacity_sum, hex_count)`
- `v_hex_state_asof(session_id, tick, h3_index, county_fips, state_fips,
  region_id, c, v, s, k, biocapacity_stock, energy_stock, raw_material_stock,
  internet_access_pct, surveillance_coupling, written_at_tick)`
- `tick_commit(session_id UUID, tick, determinism_hash CHAR(64),
  hex_rows_written, is_checkpoint BOOL, created_at_utc TIMESTAMPTZ)`

A live national query on session `bc680a6f-…` returned ticks 0–4, `v_sum ≈
1.497e9`, `hex_count = 1045` — real, non-empty data to validate against.

**Note on reuse**: `src/babylon/persistence/postgres_aggregation.py` already
provides typed fetch helpers over these views, but they use the runner's
`psycopg_pool` (`PostgresRuntime._pool`). The Observatory instead queries via
Django's `connections["sim"]` cursor (the read-only alias) — that is the whole
point of the bridge. We mirror the SQL, not the pool, to keep the read-only
guarantee in one place (the alias) and stay within Lane O ownership
(`src/babylon/**` is off-limits).

## D7 — Feature gating & frontend flag propagation

**Decision**: `OBSERVATORY_ENABLED` in settings (True dev, False prod).
Endpoints check it first and return 404 when off (precedent: `HealthDetailView`
returns 404 to non-staff via the health-obscuring exception handler). A
`GET /api/observatory/status/` returns `{enabled: true}` (200) when on, 404 when
off. The React `/observatory` route is always registered (lazy) but its shell
probes `status/`; a 404 renders the disabled state.

**Rationale**: Single backend source of truth for the flag; no Vite build-time
env var, no coupling to other apps' code. Mirrors the `/dev/hexmap` precedent
(a dev-only route that ships today) but with a real backend gate.

## D8 — Test provisioning pattern

**Decision**: Follow the existing integration pattern
(`tests/integration/test_cross_scale_aggregation.py`): use the session-scoped
`pg_pool` fixture (DSN from `BABYLON_TEST_PG_DSN`, default 5433/babylon_test),
apply `migrations/00*.sql`, seed a **unique `uuid4` session** via
`PerTickTransactionEnvelope` + `runtime.persist_*`, and let the views filter by
that session id (isolation without a private database). Endpoint tests point the
Django `sim` alias at the same DSN and use the Django test client (auth/session
live in the SQLite `default`; series data reads from `sim`). Skips cleanly when
Postgres is unavailable (`@pytest.mark.integration`).

**Rationale**: This is the sanctioned, working pattern; a per-test unique
session is the established isolation unit and never pollutes shared rows.
Probe sessions already present are also fine to read (task note).

## D9 — CSV export

**Decision**: The series endpoint accepts `format=csv` (or a sibling
`series.csv` path) and streams `text/csv` with a header row + one row per
committed tick. Frontend also has a client-side `csv.ts` for exporting the
already-fetched series (offline-friendly, no extra round trip). Backend CSV is
the contract of record (FR-011); the client helper is a convenience mirror.
