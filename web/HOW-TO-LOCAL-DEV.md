# How to Run the Babylon Web App Locally

This guide shows you how to start the Django backend and React frontend on your
development machine, run the test suites, and expose the app across a local
network for testing on other devices.

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

# Start the development server on port 8000
poetry run python manage.py runserver 8000
```

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

## Start the React Frontend

In a separate terminal:

```bash
cd web/frontend/

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
cd web/frontend/
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

cd web/frontend/
npm run test:e2e          # Headless Chromium
npm run test:e2e:ui       # Interactive UI mode
```

### Frontend Quality Checks

```bash
cd web/frontend/
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
cd web/frontend/
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
cd web/frontend/
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
