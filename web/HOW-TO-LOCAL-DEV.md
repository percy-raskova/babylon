# How to Run the Babylon Web App Locally

This guide shows you how to start the Django backend and React frontend on your
development machine, run the test suites, and expose the app across a local
network for testing on other devices.

## The Two-Database Split (read this first)

Babylon runs against **two separate Postgres databases**. This is the single
most confusing fact for an incoming developer, so it is documented up front.
Django addresses both through database *aliases* (spec-096):

| Alias     | Database (default)                                    | Schema                                                                                                                                     | Written by                         | Read by                             |
| --------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------- | ----------------------------------- |
| `default` | `localhost:5432/babylon`                              | spec-037 **product** schema (`game_session`, `hex_latest`, `territory_snapshot`, `tick_summary`, …)                                        | the Django product (game play)     | the whole web product               |
| `sim`     | `localhost:5433/babylon_test` (from `BABYLON_PG_DSN`) | spec-062 `dynamic_*` + spec-087–089 (`tick_commit`, `v_hex_state_asof`, `v_{county,state,national}_value_aggregate`, session partitioning) | the headless **simulation runner** | **the Observatory only, READ-ONLY** |

Nothing bridges these two except the **Observatory** (`web/observatory/`,
spec-096, Lane O). The Observatory adds the read-only `sim` alias and the
`/api/observatory/*` endpoints; it never writes the sim DB and never migrates
its schema.

**Read-only guarantees** (see `web/observatory/db.py`, `router.py`):

- The `sim` alias opens every connection with
  `default_transaction_read_only=on` — any write raises
  `ReadOnlySqlTransaction` at the Postgres level.
- `SimDatabaseRouter.allow_migrate("sim", …)` is `False` and the `observatory`
  app declares no models, so `manage.py migrate` never touches the sim schema
  (the runner's idempotent `src/babylon/persistence/migrations/00*.sql` are its
  sole owner — Constitution II.11).

**Point the Observatory at a different sim DB** by overriding the DSN (libpq
keyword or URL form; the `tools/tick_probe.py` default):

```bash
export BABYLON_PG_DSN="host=localhost port=5433 dbname=babylon_test user=test password=test"
```

The Observatory is gated by `OBSERVATORY_ENABLED` — **True** in
`settings/development.py`, **False** in `settings/production.py`. When off,
every `/api/observatory/*` endpoint returns 404 and the `/observatory` page
renders a disabled state. See
`specs/096-observatory-foundation/quickstart.md`.

### `source=live | archive` (spec-099 deep panes)

Every Observatory read accepts a `source` selector (a dropdown in the UI):

- **`live`** (default) — reads the runner Postgres via the read-only `sim`
  alias (above).
- **`archive`** — reads a session's exported Parquet under
  `BABYLON_ARCHIVE_ROOT` (default `/media/user/data/babylon-archives`, one
  directory per session; `mise run sim:archived` shows the root) via an
  in-memory DuckDB, **read-only** (never writes the Parquet). This is how you
  browse a run that was archived and purged from Postgres. Archive-source
  supports the national series, commit chain, hash-chain verification, boundary
  and conservation panes; state/county series is live-only (archives carry no
  `hex_spatial_map`).

Deep panes (spec-099): **verify** (`/verify/` — walks the `tick_commit` chain
and reports contiguity / checkpoint-cadence / hash anomalies), **boundary**
(`/boundary/` — cross-boundary flows, empty until trade activates in spec-101),
**conservation** (`/conservation/` — the audit log, warn/alarm filter), and
**diff** (`/diff/?a=&b=` — two sessions' national series + commit chains).
See `specs/099-observatory-deep-panes/`.

## Before You Begin

Ensure you have:

- Python 3.12+ with `poetry` installed
- Node.js 20+ with `npm`
- PostgreSQL 16+ with the **PostGIS** extension enabled
- A local PostgreSQL database named `babylon` (or whatever you set in env vars)

The Django backend uses the `django.contrib.gis.db.backends.postgis` engine, so
plain PostgreSQL without PostGIS will not work.

## Quick Start (Mise)

If you have [Mise](https://mise.jdx.dev/) installed and the database already set
up, you can run everything from the project root:

| Command                 | What it does                                                   |
| ----------------------- | -------------------------------------------------------------- |
| `mise run web:install`  | Install Python + Node dependencies                             |
| `mise run web:migrate`  | Run Django database migrations                                 |
| `mise run web:dev`      | Start Django + Vite as background daemons                      |
| `mise run web:stop`     | Gracefully stop both servers (SIGTERM, then SIGKILL after 5s)  |
| `mise run web:status`   | Show running/stopped status for each server                    |
| `mise run web:logs`     | Tail both server log files                                     |
| `mise run web:backend`  | Start Django in foreground (port 8000)                         |
| `mise run web:frontend` | Start Vite in foreground (port 5173)                           |
| `mise run web:test`     | Run frontend tests (Vitest)                                    |
| `mise run web:check`    | Run frontend quality checks (tsc + eslint + prettier + vitest) |
| `mise run web:build`    | Build frontend for production                                  |

Bootstrap order on a clean database:

1. `mise run web:migrate` — apply all Django migrations (including 0006–0010
   from spec 061, which drop the orphan `sim.hex_states` schema, purge legacy
   fixture sessions, drop `game_session.snapshot_json`, and reconcile the
   `document_chunk` pgvector schema)
1. `poetry run python manage.py createsuperuser` (from `web/`) — create the
   Django user the seed command will own the game as
1. `RUN_MAIN=true poetry run python manage.py seed_initial_game --scenario wayne_county --player admin`
   — seed the first real-engine game session (`RUN_MAIN=true` is required:
   under the DEBUG development settings `game/apps.py` skips EngineBridge
   init for management commands otherwise, and the seed refuses the stub)
1. `mise run web:dev` — start backend + frontend

For first-time database setup and superuser creation, see the detailed steps
below.

## Set Up the Database

Create the database and enable PostGIS:

```bash
createdb babylon
psql babylon -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

Create a database user (or use your system user):

```bash
psql -c "CREATE USER babylon WITH PASSWORD 'babylon';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE babylon TO babylon;"
psql babylon -c "GRANT ALL ON SCHEMA public TO babylon;"
```

## Start the Django Backend

From the repository root:

```bash
cd web/

# Install Python dependencies (if not already done)
poetry install

# Set environment variables (defaults work for local dev)
export POSTGRES_DB=babylon
export POSTGRES_USER=babylon
export POSTGRES_PASSWORD=babylon
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432

# Run migrations
poetry run python manage.py migrate

# Create a superuser for the admin panel and game access
poetry run python manage.py createsuperuser

# Seed an initial game session against the real engine.
# RUN_MAIN=true is required: under DEBUG development settings game/apps.py
# skips EngineBridge init for management commands unless it is set.
RUN_MAIN=true poetry run python manage.py seed_initial_game --scenario wayne_county --player admin

# Start the development server on port 8000
poetry run python manage.py runserver 8000
```

`seed_initial_game` invokes the real `EngineBridge.create_game()` — there is no
mock fallback. The `--player` argument must match an existing Django username
(usually the superuser you just created). The `--scenario` argument selects from
the scenarios exposed by the engine; `wayne_county` is the default vertical
slice.

When `createsuperuser` prompts for username, press Enter to accept the
default shown (for example, `user` on your machine). Babylon auth is
username-based (`username` + `password`), not email-based.

Example interactive input:

```text
Username (leave blank to use 'user'): [press Enter]
Email address: user@localhost
Password: ********
Password (again): ********
Superuser created successfully.
```

The `manage.py` defaults to `babylon_web.settings.development`, which enables
`DEBUG=True` and CORS headers for the Vite dev server on port 5173.

Verify the backend is running:

```bash
curl http://localhost:8000/health/
```

You should get `{"status": "ok"}`.

`/health/` is intentionally minimal — it reports liveness only. For richer
diagnostics (which `EngineBridge` implementation is active, when it last
resolved a tick, current pool size, pinned embedding model, git SHA), the
project exposes `/health/detail/`. That endpoint is gated to staff users:
unauthenticated and non-staff requests get a standard 404 (deliberate
information-hiding per spec 061 FR-009; see also ADR039). After logging in as
a superuser you can curl it via a session cookie or browse to it directly.

If the engine cannot reach Postgres at startup, `GameConfig.ready()` retries
three times (1s, 2s) before calling `sys.exit(1)`. Under `runserver` that just
kills the dev process; under systemd in production, the unit's
`Restart=on-failure` kicks in with exponential backoff. Mid-session DB outages
surface as HTTP 503 from any engine-dependent endpoint (state, resolve,
timeseries, communities) with a uniform error envelope — `/health/` and
`/health/detail/` are exempt from this 503 wrapping so you can still observe a
degraded backend.

## Start the React Frontend

In a separate terminal:

```bash
cd src/frontend/

# Install Node dependencies
npm install

# Start the Vite dev server
npm run dev
```

The Vite dev server starts on **port 5173** and proxies API requests to Django:

| URL pattern   | Proxied to                         |
| ------------- | ---------------------------------- |
| `/api/*`      | `http://localhost:8000/api/*`      |
| `/accounts/*` | `http://localhost:8000/accounts/*` |
| `/health/*`   | `http://localhost:8000/health/*`   |

Open `http://localhost:5173` in your browser. You should see the login page.
Log in with the superuser credentials you created above.

## Run the Test Suites

### Frontend Unit and Integration Tests (Vitest)

```bash
cd src/frontend/
npm run test              # Run all 210 tests
npm run test:watch        # Watch mode for development
npm run test:coverage     # With coverage report (thresholds: 80/75/80)
```

### Frontend E2E Tests (Playwright)

E2E tests require both the Django backend and Vite dev server running:

```bash
# Terminal 1: Django backend (see above)
# Terminal 2: Start the Vite dev server (Playwright's webServer config does this
#             automatically, but you need the backend running separately)

cd src/frontend/
npm run test:e2e          # Headless Chromium
npm run test:e2e:ui       # Interactive UI mode
```

### Frontend Quality Checks

```bash
cd src/frontend/
npm run check             # TypeScript + ESLint + Prettier (no tests)
npm run typecheck         # TypeScript only
npm run lint              # ESLint only
npm run format:check      # Prettier only
```

### Django Backend Tests

```bash
cd web/
DJANGO_SETTINGS_MODULE=babylon_web.settings.testing \
  poetry run python manage.py test
```

The `testing` settings module uses SQLite in-memory, so no PostGIS is needed for
backend tests.

## Build the Frontend for Production

```bash
cd src/frontend/
npm run build
```

This produces a `dist/` directory with static files. In production, nginx serves
these directly. For local verification:

```bash
npm run preview
```

This starts a local server at `http://localhost:4173` serving the production build.

## Test Across a Local Network

To access the app from another device on the same network (e.g., a phone or
second machine), you need to bind both servers to `0.0.0.0` and update CORS.

### Step 1: Find Your Local IP

```bash
# Linux
ip addr show | grep 'inet ' | grep -v 127.0.0.1

# macOS
ifconfig | grep 'inet ' | grep -v 127.0.0.1
```

Note your LAN IP (e.g., `192.168.1.42`).

### Step 2: Start Django on 0.0.0.0

```bash
cd web/

# Add your LAN IP to ALLOWED_HOSTS in development settings,
# or override via environment variable and production settings:
DJANGO_SETTINGS_MODULE=babylon_web.settings.development \
  poetry run python manage.py runserver 0.0.0.0:8000
```

You also need to temporarily add your LAN IP to the `ALLOWED_HOSTS` in
`babylon_web/settings/development.py`:

```python
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "192.168.1.42"]
```

And add the CORS origin for your LAN:

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://192.168.1.42:5173",
]
```

### Step 3: Start Vite on 0.0.0.0

```bash
cd src/frontend/
npx vite --host 0.0.0.0
```

### Step 4: Update the Vite Proxy Target

If the other device needs to hit the Django backend through Vite's proxy, update
`vite.config.ts` to point the proxy target at your LAN IP instead of
`localhost`:

```ts
proxy: {
  "/api": {
    target: "http://192.168.1.42:8000",
    changeOrigin: true,
  },
  // ... same for /accounts and /health
},
```

### Step 5: Access from the Other Device

On the other device, open `http://192.168.1.42:5173`.

If your machine has a firewall, ensure ports 5173 and 8000 are open:

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 5173/tcp
sudo ufw allow 8000/tcp

# firewalld (Fedora/RHEL)
sudo firewall-cmd --add-port=5173/tcp --add-port=8000/tcp
```

### Cleanup

Revert your changes to `development.py` and `vite.config.ts` before committing.
These LAN-specific settings should not be checked in.

## Logs

Django writes structured JSON logs to `web/logs/`:

| File               | Contents                      |
| ------------------ | ----------------------------- |
| `web.jsonl`        | All request/response activity |
| `web_errors.jsonl` | Errors only (5xx responses)   |

The console also shows human-readable log output during development.

## Troubleshooting

**"No module named 'django.contrib.gis'"**: PostGIS and its Python bindings are
missing. Install `libgdal-dev` and `libgeos-dev` on Debian/Ubuntu, then
`poetry install` again.

**CSRF token errors on login**: The Vite proxy must forward cookies. The
`changeOrigin: true` setting in `vite.config.ts` handles this. If you see CSRF
errors, ensure you are accessing the app through `localhost:5173`, not
`localhost:8000` directly.

**`createdb` / `psql` fails with `FATAL: role "user" does not exist`**: This
happens when PostgreSQL tries to authenticate as your Linux username (`user`),
but that DB role does not exist. Use the `postgres` superuser to create/fix the
application role and verify login over TCP:

```bash
# Check service is up
pg_isready

# Use postgres superuser for admin commands
sudo -u postgres psql -c "ALTER ROLE babylon WITH LOGIN PASSWORD 'babylon';"

# Ensure DB and PostGIS exist (note: EXTENSION spelling matters)
sudo -u postgres psql -tAc "SELECT datname FROM pg_database WHERE datname='babylon';"
sudo -u postgres psql -d babylon -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# Verify app credentials (uses password auth, not peer auth)
PGPASSWORD=babylon psql -h localhost -U babylon -d babylon -c "SELECT current_user, current_database();"
```

If `sudo -u postgres ...` prompts for your password, enter your Linux account
password.

**"relation does not exist" errors**: Run `poetry run python manage.py migrate`
from the `web/` directory. The `game_session`, `game_turn`, and `action_result`
tables are created by the engine's DDL (`postgres_schema.py`), not Django
migrations. Only `game_event_log` and `accounts_playerprofile` are
Django-managed.
