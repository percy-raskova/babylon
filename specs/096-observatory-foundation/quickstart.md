# Quickstart: Observatory Foundation

## What it is

A read-only developer dashboard over the **simulation** Postgres (5433/
`babylon_test`), reachable from the web product at `/observatory`. Enabled by
default in development, disabled in production.

## The two-database split (read this first)

| Alias | Database | Schema | Who writes it |
|---|---|---|---|
| `default` | `localhost:5432/babylon` | spec-037 product (`game_session`, `hex_latest`, …) | the Django product |
| `sim` | `localhost:5433/babylon_test` (`BABYLON_PG_DSN`) | spec-062 `dynamic_*` + spec-087–089 (`tick_commit`, `v_hex_state_asof`, `v_*_value_aggregate`) | the headless sim runner |

The Observatory reads `sim` **read-only** and never migrates it.

## Run it locally

```bash
# 1. Have a simulation session in the sim DB (small probe is enough):
mise run sim:probe -- --county 26163 --ticks 3

# 2. Start the web app (development settings → OBSERVATORY_ENABLED=True):
mise run web:dev            # Django :8000 + Vite :5173

# 3. Open the dashboard:
#    http://localhost:5173/observatory
#    → pick a session → view national/state/county series → export CSV
```

Point at a different sim DB with `BABYLON_PG_DSN`:

```bash
export BABYLON_PG_DSN="host=localhost port=5433 dbname=babylon_test user=test password=test"
```

## Verify (gates)

```bash
# Backend fast unit gate (router, alias, gating):
mise run test:q -- tests/unit/observatory/

# Backend integration (needs Postgres at BABYLON_TEST_PG_DSN / 5433):
poetry run pytest tests/integration/observatory/ -q

# Frontend quality + Vitest + MSW contracts (no Playwright leg):
mise run web:check
```

## Read-only proof (why it's safe to browse a live run)

- The `sim` alias opens every connection with
  `default_transaction_read_only=on` → any write raises
  `ReadOnlySqlTransaction`.
- `SimDatabaseRouter.allow_migrate("sim", …)` is `False` and the app has no
  models → `manage.py migrate` never touches the sim schema.
- Endpoints select only from the declared views + `tick_commit` (never the raw
  sparse `dynamic_hex_state`).
