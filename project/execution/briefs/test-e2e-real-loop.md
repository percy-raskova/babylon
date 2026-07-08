# Implementation Brief — `test/e2e-real-loop` (C.4 CI Postgres leg + C.5 Playwright CI leg + real submit→resolve→results spec)

Scouted at `chore/test-infra-rearm` HEAD `9101dddf` (= dev + test-infra edits). All line numbers verified against current code on 2026-07-08.

---

## 1. Verified seams (current state)

### 1.1 `.github/workflows/ci.yml` — jobs at HEAD

File: `/home/user/projects/game/babylon/.github/workflows/ci.yml` (288 lines). Last touched by `fa8648b7 chore(tests): re-arm the disarmed guardrails (C.9)` which **deleted the stale PyQt6 `ui-tests` job** (confirmed: no `ui-tests` in file; claude-mem obs 42332).

Current jobs:
| job | lines | gate |
|---|---|---|
| `ci` (Lint, Type Check & Test) | 19–81 | always; `pytest --ignore=tests/unit/ai -m "not red_phase" --tb=short -q` at line 60 |
| `security` | 83–111 | always |
| `docs` | 113–153 | main only (line 117) |
| `style` | 157–186 | informational (`continue-on-error: true`) |
| `mutation` | 190–256 | PRs to main only (line 193) |
| `ai-tests` | 258–287 | `continue-on-error: true` |

There is **no Postgres anywhere in CI**. The new jobs go after `ai-tests` (or after `ci`; order in file is cosmetic — jobs run in parallel).

### 1.2 Skip gate for `tests/integration/web/` — env var is `POSTGRES_HOST`

`tests/integration/web/test_game_lifecycle.py:17-23` (identical block in `test_bridge_roundtrip.py:16-22`):
```python
pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(
        not os.environ.get("POSTGRES_HOST"),
        reason="PostgreSQL not configured (set POSTGRES_HOST)",
    ),
]
```
Helper in `tests/integration/web/conftest.py:38-40`:
```python
def postgres_available() -> bool:
    """Check if PostgreSQL connection details are configured."""
    return os.environ.get("POSTGRES_HOST", "") != ""
```
Markers registered in `pyproject.toml:169-170`:
```
"requires_postgres: Tests requiring a running PostgreSQL instance (skipped if unavailable)",
"postgres: Tests using testcontainers ephemeral PostgreSQL (requires Docker)",
```
Two distinct families in `tests/integration/web/`:
- `test_game_lifecycle.py` (5 tests) + `test_bridge_roundtrip.py` — marker `requires_postgres`, gated on `POSTGRES_HOST`, connect **directly** to that host via `PostgresRuntime`.
- `test_pg_contract.py` — marker `postgres` (line 34), uses the **testcontainers** session fixture in `conftest.py:52-91` (`PostgresContainer(image="postgis/postgis:16-3.4-alpine", username="test", password="test", dbname="babylon_test")`); needs only Docker, self-skips if Docker missing (`conftest.py:70-72`). Already runnable via `mise run test:pg` (`.mise.toml:244-253`).

⚠️ **The `requires_postgres` fixtures are broken at HEAD** — see Drift alert #2. They call:
```python
# test_game_lifecycle.py:42-48 (same at test_bridge_roundtrip.py:41-47)
persistence = PostgresRuntime(
    host=os.environ.get("POSTGRES_HOST", "localhost"),
    port=int(os.environ.get("POSTGRES_PORT", "5432")),
    database=os.environ.get("POSTGRES_DB", "babylon_test"),
    user=os.environ.get("POSTGRES_USER", "babylon"),
    password=os.environ.get("POSTGRES_PASSWORD", "babylon"),
)
```
but the real constructor is `src/babylon/persistence/postgres_runtime/_legacy.py:78`:
```python
def __init__(self, pool: ConnectionPool[Connection[Any]]) -> None:
```
(re-exported unchanged via `postgres_runtime/__init__.py:24`). Setting `POSTGRES_HOST` in CI without fixing these fixtures = instant `TypeError`. Fix is part of this branch (step 3 below).

### 1.3 Playwright setup — boots only Vite (confirmed)

`web/frontend/playwright.config.ts:20-24`:
```ts
webServer: {
    command: "npm run dev",     // package.json: "dev": "vite"
    port: 5173,
    reuseExistingServer: !process.env.CI,   // under CI: never reuse — always self-starts Vite
},
```
`baseURL: "http://localhost:5173"` (line 11); CI mode: `workers: 1`, `retries: 1`, `forbidOnly` (lines 6-8). Django (port 8000) is **not** started by Playwright — Vite proxies `/api`, `/accounts`, `/health` to `http://localhost:8000` (`web/frontend/vite.config.ts:15-27`). The CI job must start Django itself.

Existing specs (`web/frontend/e2e/`, 11 files):
- **`end-turn-flow.spec.ts`** — REAL end-turn against a seeded session. Gate at lines 17+21: `const SESSION_ID = process.env.SPEC061_TEST_SESSION_ID;` / `test.skip(!SESSION_ID, "SPEC061_TEST_SESSION_ID env var required");`. Flow: `/games/${SESSION_ID}/orgs` → click `/End Turn/` → URL `/resolution` → text `/Resolving Tick/` → click `/Continue/` → back to `/games/${SESSION_ID}` → `/games/${SESSION_ID}/log` → `Event Log` heading + soft `No events recorded yet|t=\d+` assertion (lines 26-53).
- **`verb-submit.spec.ts`** — **RENDER-ONLY** despite its docstring claiming "submits, and confirms the action appears on the Results page" (lines 2-11). The three actual tests (lines 27-60) only assert: actor/verb pickers render, a `/submit/i` button is visible, and `investigate` is absent from the picker. **No click on submit, no resolve, no results check.** Same `SPEC061_TEST_SESSION_ID` gate (lines 21, 25).
- **Map specs self-stub** — confirmed. `briefing-map-smoke.spec.ts:53-67`:
```ts
await page.route("**/accounts/whoami/", (r) =>
  r.fulfill(ok({ is_authenticated: true, username: "smoke" })),
);
await page.route("**/api/games/*/state/", (r) => r.fulfill(ok(SNAPSHOT)));
await page.route("**/api/games/*/actions/available/", (r) => r.fulfill(ok([])));
await page.route("**/api/games/*/map/**", (r) =>
  r.fulfill(ok({ type: "FeatureCollection", features: [] })),
);
```
  `map-lens-cycling.spec.ts:162-174` uses the identical `page.route` pattern with a richer balkanization mock. Both need **only Vite** (their docstrings say so explicitly, lines 10-11 / 18-19). These two are the only specs that are green in a backend-less CI today.
- Other `SPEC061_TEST_SESSION_ID`-gated (auto-skip) specs: `orgs-live-data`, `briefing-live-data`, `intel-results-analysis`, `polling-tick-aligned`, `wire-50-tick` (that one says "owner-run only" and needs a 50+-tick session — leave skipped in CI).
- **`auth.spec.ts`** — NOT gated and NOT stubbed; needs a real backend + a `testuser/testpass` user; asserts `Your Games` (lines 26, 46) which **no longer exists** — the UI renders `Your Operations` (`web/frontend/src/components/GameList.tssx:138` — `title="Your Operations"`). See Drift #4.
- `visual.spec.ts` — screenshot suite with committed snapshots; do not add it to the CI leg (font/GPU variance); scope CI to explicit files instead.

TS note: `web/frontend/tsconfig.json` `"include": ["src", "vitest.config.ts"]` — e2e specs are NOT typechecked by `npm run check`; Playwright transpiles them itself. New spec files won't affect `web:check`.

### 1.4 `seed_initial_game` — verified

`web/game/management/commands/seed_initial_game.py`:
- Prints the session id at line 93: `self.stdout.write(self.style.SUCCESS(f"Game session created: {session_id}"))` (plus `Navigate to: /games/{session_id}` at line 97).
- Refuses a missing/stub bridge, lines 73-86:
```python
bridge = game_api._bridge_instance  # noqa: SLF001 — module singleton
if bridge is None:
    raise CommandError(
        "EngineBridge not initialized. Set up PostgreSQL and run via the "
        "production settings module, or call init_bridge(persistence) "
        "before invoking this command."
    )
if type(bridge).__name__ != "EngineBridge":
    raise CommandError(...)
```
- Creates the auth user `admin` with password `admin` (`user.set_password(player_username)` — password == username, lines 55-61) with `is_staff=True, is_superuser=True`.

**Critical gotcha (empirically verified this session):** the bridge is initialized only in `GameConfig.ready()` (`web/game/apps.py:40-69`), and line 55-56 short-circuits:
```python
if settings.DEBUG and os.environ.get("RUN_MAIN") != "true":
    return
```
`manage.py` defaults to `babylon_web.settings.development` (`web/manage.py:12`) where `DEBUG = True` (`development.py:10`). A management command never sets `RUN_MAIN`, so under the documented invocation the bridge is `None` and seeding raises `CommandError`. Verified:
- without `RUN_MAIN`: `_bridge_instance` → `None`
- with `RUN_MAIN=true`: `_bridge_instance` → `EngineBridge`

**Every CI/manual seed invocation must be `RUN_MAIN=true poetry run python manage.py seed_initial_game …`.** Same applies to `runserver --noreload` (Drift #5): the reloader child of plain `runserver` sets `RUN_MAIN=true` itself, but `--noreload` does not — if you use `--noreload` in CI, export `RUN_MAIN=true` for the server process too, or `/api/*` will silently serve the `StubEngineBridge` fallback (`web/game/api.py:77-86`).

### 1.5 What the Playwright CI job needs (all verified)

- **Postgres image**: `django.contrib.gis.db.backends.postgis` is the default engine (`web/babylon_web/settings/base.py:92`), read from env `POSTGRES_DB/USER/PASSWORD/HOST/PORT` (base.py:93-97, defaults `babylon/babylon/babylon/localhost/5432`). `PostgresRuntime.init_schema()` (`_legacy.py:86-95`) executes `POSTGRES_SCHEMA_DDL` **with no per-statement error tolerance**, and the DDL's first three statements are `CREATE EXTENSION IF NOT EXISTS postgis / vector / "uuid-ossp"` (`src/babylon/persistence/postgres_schema.py:33-35`). ⇒ a plain `postgres:16` **or even `postgis/postgis:16-3.4`** service breaks schema init at statement 2. The repo already ships the correct image: `docker/postgres/Dockerfile` = `FROM postgis/postgis:16-3.4` + `postgresql-16-pgvector`, with `docker/postgres/initdb/01-babylon-init.sql` creating all extensions in `template1` **and** `babylon_test`, wired by `docker-compose.yml` (service `babylon-pg`, host port **5433**, `test/test/babylon_test`, healthcheck) and canonically started with `docker compose up -d --wait babylon-pg` (= `mise run db:up`, `.mise.toml:709-711`). GitHub `services:` blocks cannot build Dockerfiles, so **use the compose bring-up as a step, not a service block.** The initdb script hardcodes `\connect babylon_test` and `ALTER ROLE test`, so CI must keep the compose env (`test/test/babylon_test@5433`).
- **GeoDjango system libs**: the postgis backend loads GEOS/GDAL/PROJ at first connection. Current CI never opens a postgis connection (pytest uses `babylon_web.settings.testing` → SQLite, `pyproject.toml:132` + `testing.py:14-19`), so the runner never needed them. The Playwright leg (development settings) does: `sudo apt-get install -y binutils libproj-dev gdal-bin` (Django docs' minimal set).
- **Node**: `.mise.toml [tools]` has only `python = "3.12"` and `poetry` (lines 17-19) — **no node**. Use `actions/setup-node@v4` (node 22, `cache: npm`, `cache-dependency-path: web/frontend/package-lock.json` — lockfile exists). The local `node_modules` symlink convention does not exist in CI: run `npm ci`.
- **Playwright browsers**: `npx playwright install --with-deps chromium` (dep `@playwright/test ^1.58.2` in `web/frontend/package.json`).
- **Django deps**: root poetry env serves the web app (no `web/pyproject.toml`; `django >=5.0,<6.0`, DRF in root `pyproject.toml:76-78`).
- **Migrate**: `cd web && poetry run python manage.py migrate` (= `mise run web:migrate`, `.mise.toml:1126-1129`). E2E_SUMMARY.md:40 confirms this applies `accounts.0001 + game.0011` and creates the Django-managed tables against real Postgres; `init_persistence()` (`web/game/engine_bridge.py:3659-3691`) then applies the runtime DDL via `persistence.init_schema()` at server boot.
- **Seed + capture session id** (see §1.4 gotcha):
```bash
SEED_OUT=$(RUN_MAIN=true poetry run python manage.py seed_initial_game --scenario wayne_county --player admin)
echo "$SEED_OUT"
SESSION_ID=$(echo "$SEED_OUT" | grep -oE 'Game session created: [0-9a-f-]{36}' | awk '{print $4}')
echo "SPEC061_TEST_SESSION_ID=$SESSION_ID" >> "$GITHUB_ENV"
```
- **Start Django**: `(cd web && RUN_MAIN=true nohup poetry run python manage.py runserver 8000 --noreload > ../django-ci.log 2>&1 &)` then poll `curl -sf http://localhost:8000/health/` (returns `{"status":"ok"}`). `--noreload` + explicit `RUN_MAIN=true` avoids the double-process reloader AND satisfies the apps.py guard. On init failure the worker exits 1 by design (apps.py:100-110) — the health poll catches it.
- **Vite**: started by Playwright's own `webServer` — do not start it manually (under CI `reuseExistingServer` is false).

### 1.6 Wayne County seed runtime — measured

`_build_initial_state_for_scenario("wayne_county")` (`web/game/engine_bridge.py:3062-3064`) delegates to `create_wayne_county_scenario` → `scenarios/_legacy_wayne.py` (569 LOC, **pure in-memory, zero DB/file reads** — verified by grep). Measured this session: import 1.00 s, build 0.00 s, 81 territories / 4 entities. Prior run log (`.web-pids/django.log:4248-4249`) shows a full engine tick resolving within the same wall-clock second. Seed step total ≈ **5–15 s** (Django boot + idempotent DDL + tick-0 persist). Budget 60 s in CI; it will not be the long pole (that's `docker compose` image build ≈ 2–4 min uncached, and `npx playwright install` ≈ 1 min).

### 1.7 Backend contract cheat-sheet for the new spec (all verified)

- Auth: all `/api/*` views are `@permission_classes([IsAuthenticated])` (`web/game/api.py:184-185` etc.). Login page: placeholders `Username`/`Password`, button label `Enter` / `Authenticating...` (`LoginPage.tsx:71,80,93`). Seeded credentials: `admin`/`admin`.
- Create game: `POST /api/games/` (`api.game_list`, urls.py:24; `CreateGameSerializer` = `scenario`, optional `config/defines/rng_seed`, serializers.py:18-24) → 201 `{"session_id": …}`. UI: `/games` page, panel `New Operation`, card list `Your Operations` (`GameList.tsx:91,138`).
- State: `GET /api/games/<id>/state/`; Map: `GET /api/games/<id>/map/?zoom=…`, `VALID_ZOOM_LEVELS = {"state","bea","bea_ea","msa","county","cz","hex"}`, `DEFAULT_ZOOM="county"` (`api.py:369-374`).
- Educate submit: `POST /api/games/<id>/actions/educate/` → `EducateSubmitSerializer` requires `org_id` + **`target_community_id`** + optional `params` dict (`serializers.py:512-516`; view `api.py:1249-1291` responds 201 with `action_id`). The frontend still sends `{org_id, target_id, ...paramVals}` (`VerbPage.tsx:225-229` via `gameStore.submitAction`, `gameStore.ts:162-173` — verb in URL path, rest as body) ⇒ educate 400s today. **Phase 1.4 owns this fix** (the dormant correct config exists at `web/frontend/src/lib/verbs/educate.ts` with `targetPayloadKey: "target_community_id"`).
- Resolve: `POST /api/games/<id>/resolve/` (urls.py:197). **Currently 500s** — Bug #6, `json.dumps(event, sort_keys=True)` without a datetime default at `src/babylon/persistence/postgres_runtime/_legacy.py:203`. **Phase 1.1 owns this fix.**
- Results: `GET /api/games/<id>/results/<tick>/` (urls.py:199-203); UI route `/games/:id/results` shows title `Results`, subtitle `Tick ${tick} resolution summary` (`ResultsPage.tsx:27-28`).
- End Turn button: `OrgsPage.tsx:227` — `{resolving ? "Resolving…" : "End Turn ▸"}`; resolution screen: `TickResolutionPage.tsx:119` `▸ Resolving Tick …`, continue button line 170 `▸ Continue · Tick …`; Event Log page title `Event Log`, empty state `No events recorded yet` (`EventLogPage.tsx:80,106`).
- Frontend routes under `/games/:id`: index (Briefing), `orgs`, `results`, `intel`, `actions/:verb`, `analysis`, `log`, `resolution`, `wire`, `dialectic`, `chronicle`, `objectives` (`App.tsx:106-144`).

---

## 2. Implementation steps

### Step 0 — branch
```bash
git checkout dev && git checkout -b test/e2e-real-loop
```

### Step 1 (RED) — new Playwright spec `web/frontend/e2e/real-loop.spec.ts`

New file. Follows the house style of `end-turn-flow.spec.ts` (header comment with owner-run instructions, `SPEC061_TEST_SESSION_ID` gate, `PLAYWRIGHT_BASE_URL` override, text-based locators — the pages have no `data-testid` except the map controls). Outline:

```ts
/**
 * Real core-loop gate (C.5): create → map features → submit educate →
 * end turn → tick advances → results deltas → event log.
 *
 * Unlike verb-submit.spec.ts (render-only) this spec drives the FULL
 * submit→resolve→results path against a live Postgres-backed EngineBridge.
 * Requires SPEC061_TEST_SESSION_ID + a running dev server (Django :8000 +
 * Vite :5173) and the seeded admin/admin user (seed_initial_game).
 * Skipped automatically otherwise.
 *
 * Owner setup:
 *   1. mise run db:up && mise run web:migrate
 *   2. RUN_MAIN=true poetry run python web/manage.py seed_initial_game --scenario wayne_county
 *   3. mise run web:dev
 *   4. SPEC061_TEST_SESSION_ID=<printed id> npx playwright test real-loop
 */
import { expect, test } from "@playwright/test";

const SESSION_ID = process.env.SPEC061_TEST_SESSION_ID;
const BASE = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:5173";

test.describe("real core loop (C.5 gate)", () => {
  test.skip(!SESSION_ID, "SPEC061_TEST_SESSION_ID env var required");
  // Serial: each step mutates the same session.
  test.describe.configure({ mode: "serial" });

  test("login lands on the operations list showing the seeded game", async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.getByPlaceholder("Username").fill("admin");
    await page.getByPlaceholder("Password").fill("admin");
    await page.getByRole("button", { name: "Enter" }).click();
    await expect(page.getByText("Your Operations")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("wayne_county").first()).toBeVisible();
  });

  test("map endpoint serves real GeoJSON features for the seeded session", async ({ request, page }) => {
    // API-level: Phase 1.3's deliverable — real features, not the empty
    // FeatureCollection the self-stubbed map smokes fabricate.
    // (log in first so the session cookie exists on this context)
    …login via page as above, then:
    const res = await page.request.get(`${BASE}/api/games/${SESSION_ID}/map/?zoom=county`);
    expect(res.ok()).toBe(true);
    const body = await res.json();
    const features = body.data?.features ?? body.features ?? [];
    expect(features.length).toBeGreaterThan(0);   // RED until Phase 1.3
  });

  test("educate composes and submits without a 400", async ({ page }) => {
    …login, then:
    await page.goto(`${BASE}/games/${SESSION_ID}/actions/educate`);
    await expect(page.locator("text=/Actor/").first()).toBeVisible({ timeout: 10000 });
    // select first target, then submit — watch the network response
    const [resp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes("/actions/educate/") && r.request().method() === "POST"),
      page.locator("button", { hasText: /submit/i }).first().click(),
    ]);
    expect(resp.status()).toBe(201);              // RED until Phase 1.4
  });

  test("end turn advances the tick and records results + events", async ({ page }) => {
    …login, capture tick from GET state, then:
    await page.goto(`${BASE}/games/${SESSION_ID}/orgs`);
    await page.getByText(/End Turn/).click();
    await expect(page).toHaveURL(new RegExp(`/games/${SESSION_ID}/resolution$`), { timeout: 20000 });   // RED until Phase 1.1
    await expect(page.getByText(/Continue/)).toBeVisible({ timeout: 15000 });
    await page.getByText(/Continue/).click();
    // tick advanced
    const state = await page.request.get(`${BASE}/api/games/${SESSION_ID}/state/`);
    expect((await state.json()).data.tick).toBeGreaterThan(tickBefore);
    // results page shows the resolved tick's summary
    await page.goto(`${BASE}/games/${SESSION_ID}/results`);
    await expect(page.getByText(/resolution summary/)).toBeVisible({ timeout: 10000 });
    // event log renders history (or honest empty state) without crashing
    await page.goto(`${BASE}/games/${SESSION_ID}/log`);
    await expect(page.getByText(/Event Log/i).first()).toBeVisible({ timeout: 10000 });
  });
});
```
Notes for the implementer: factor the login into a helper at the top of the file (`async function login(page: Page)`), keep everything text-locator based, and prefer `page.request` (shares cookies with the page context) over a separate `request` fixture for authenticated API asserts. The envelope shape is `{status:"ok", data:…}` (`_envelope` in api.py) — unwrap `.data`.

**Red-first expectation:** the educate-submit test is RED until Phase 1.4, the end-turn test RED until Phase 1.1, map-features RED until Phase 1.3. That is intentional — this spec is the acceptance gate those phases turn green. If this branch must merge green before those phases, mark the three loop tests with `test.fixme(…, "RED: blocked on Phase 1.1/1.3/1.4 — bugs #6/#7/#4")` and flip to plain `test` in each phase's PR; do NOT weaken the assertions.

### Step 2 — assertion additions to existing specs

The task named `real-map-features` and `games-list` specs — **neither file exists** (see Drift #3). Map the intent onto real files:
- `web/frontend/e2e/auth.spec.ts` (the de-facto games-list spec): replace both `page.getByText("Your Games")` occurrences (lines 26, 46) with `page.getByText("Your Operations")` (matches `GameList.tsx:138`), change the credentials to the seeded `admin`/`admin` (the CI DB has no `testuser`), and ADD after login: `await expect(page.getByText("New Operation")).toBeVisible();` and `await expect(page.getByText("wayne_county").first()).toBeVisible();` (asserts the seeded game card renders — the exact regression Bug #1 caused).
- `web/frontend/e2e/briefing-map-smoke.spec.ts` stays backend-free (its point is the no-white-screen guarantee); the REAL map-features assertion lives in `real-loop.spec.ts` test 2 above. Optionally add one more assertion there: `zoom=hex` also returns >0 features (81 H3 cells exist in state per E2E_SUMMARY).

### Step 3 (C.4 prep) — fix the dead `requires_postgres` fixtures

`tests/integration/web/test_game_lifecycle.py:37-52` and `test_bridge_roundtrip.py:36-51` — replace the fixture body (keep the `_django_setup` dependency and docstring style):

```python
@pytest.fixture
def bridge(_django_setup: None) -> Generator[object, None, None]:
    """Create an EngineBridge connected to PostgreSQL."""
    from psycopg_pool import ConnectionPool

    from babylon.persistence.postgres_runtime import PostgresRuntime

    conninfo = (
        f"host={os.environ.get('POSTGRES_HOST', 'localhost')} "
        f"port={os.environ.get('POSTGRES_PORT', '5433')} "
        f"dbname={os.environ.get('POSTGRES_DB', 'babylon_test')} "
        f"user={os.environ.get('POSTGRES_USER', 'test')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', 'test')}"
    )
    pool: ConnectionPool = ConnectionPool(conninfo=conninfo, min_size=1, max_size=2, timeout=10)
    persistence = PostgresRuntime(pool)
    persistence.init_schema()

    from game.engine_bridge import EngineBridge

    yield EngineBridge(persistence)
    persistence.close()
```
This mirrors the production pattern in `web/game/engine_bridge.py:3671-3689` (`init_persistence`). Add `from collections.abc import Generator` to imports. Note the defaults now match the compose DB (`test/test/babylon_test@5433`) so `mise run db:up && POSTGRES_HOST=localhost pytest …` works locally with no further env. TDD: run the suite with `POSTGRES_HOST` set BEFORE the fix to capture the `TypeError` (that is the red), then apply and go green. `EngineBridge.create_game` writes only through the persistence layer (engine_bridge.py:776-793), not the Django ORM, so no `django_db` marker is needed — matches the tests' current shape.

### Step 4 — `ci.yml` job 1: `postgres-integration` (C.4)

Append after the `ai-tests` job:

```yaml
  postgres-integration:
    name: Postgres Integration (web bridge)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.12"

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: "1.8.4"
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Load cached venv
        uses: actions/cache@v5
        with:
          path: .venv
          key: venv-${{ runner.os }}-${{ hashFiles('**/poetry.lock') }}

      - name: Install dependencies
        run: poetry install --no-interaction

      # Repo-canonical Postgres 16 + PostGIS + pgvector (spec-087 image).
      # A services: block can't build docker/postgres/Dockerfile, and a stock
      # postgis image lacks pgvector, which aborts PostgresRuntime.init_schema
      # at `CREATE EXTENSION vector` (postgres_schema.py:33-35).
      - name: Start isolated Postgres (compose, port 5433)
        run: docker compose up -d --wait babylon-pg

      - name: Run web integration suites (requires_postgres + testcontainers contract)
        env:
          POSTGRES_HOST: localhost
          POSTGRES_PORT: "5433"
          POSTGRES_DB: babylon_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        run: poetry run pytest tests/integration/web/ --tb=short -q

      - name: Stop Postgres
        if: always()
        run: docker compose down -v
```
`tests/integration/web/` runs all three modules: the two `requires_postgres` suites hit the compose DB directly; `test_pg_contract.py` spins its own testcontainer (Docker is available on ubuntu-latest). Runtime estimate: compose build 2–4 min (uncached) + tests <2 min.

### Step 5 — `ci.yml` job 2: `playwright-e2e` (C.5)

```yaml
  playwright-e2e:
    name: Playwright E2E (real loop)
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v6

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.12"

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: "1.8.4"
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Load cached venv
        uses: actions/cache@v5
        with:
          path: .venv
          key: venv-${{ runner.os }}-${{ hashFiles('**/poetry.lock') }}

      - name: Install dependencies
        run: poetry install --no-interaction

      # GeoDjango: settings/base.py uses the postgis backend, which loads
      # GEOS/GDAL/PROJ at first connection (Django docs' minimal set).
      - name: Install GeoDjango system libraries
        run: sudo apt-get update && sudo apt-get install -y --no-install-recommends binutils libproj-dev gdal-bin

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: web/frontend/package-lock.json

      - name: Install frontend dependencies
        working-directory: web/frontend
        run: npm ci

      - name: Install Playwright Chromium
        working-directory: web/frontend
        run: npx playwright install --with-deps chromium

      - name: Start isolated Postgres (compose, port 5433)
        run: docker compose up -d --wait babylon-pg

      - name: Django migrate
        working-directory: web
        env: &pgenv
          POSTGRES_HOST: localhost
          POSTGRES_PORT: "5433"
          POSTGRES_DB: babylon_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        run: poetry run python manage.py migrate

      - name: Seed wayne_county session
        working-directory: web
        env:
          <<: *pgenv
          RUN_MAIN: "true"   # apps.py:55 skips bridge init for DEBUG commands otherwise
        run: |
          SEED_OUT=$(poetry run python manage.py seed_initial_game --scenario wayne_county --player admin)
          echo "$SEED_OUT"
          SESSION_ID=$(echo "$SEED_OUT" | grep -oE 'Game session created: [0-9a-f-]{36}' | awk '{print $4}')
          test -n "$SESSION_ID"
          echo "SPEC061_TEST_SESSION_ID=$SESSION_ID" >> "$GITHUB_ENV"

      - name: Start Django backend
        working-directory: web
        env:
          <<: *pgenv
          RUN_MAIN: "true"   # --noreload never sets it; without it /api serves the stub bridge
        run: |
          nohup poetry run python manage.py runserver 8000 --noreload > ../django-ci.log 2>&1 &
          for i in $(seq 1 30); do
            curl -sf http://localhost:8000/health/ && break
            sleep 1
          done
          curl -sf http://localhost:8000/health/

      - name: Run Playwright suite (Vite auto-started by webServer)
        working-directory: web/frontend
        env:
          CI: "true"
        run: npx playwright test e2e/real-loop.spec.ts e2e/end-turn-flow.spec.ts e2e/verb-submit.spec.ts e2e/auth.spec.ts e2e/briefing-map-smoke.spec.ts e2e/map-lens-cycling.spec.ts

      - name: Upload Playwright report + Django log
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: |
            web/frontend/playwright-report/
            django-ci.log

      - name: Stop Postgres
        if: always()
        run: docker compose down -v
```
(If YAML anchors are unwanted in workflow files — GitHub Actions does NOT support `&anchor`/`<<:` — inline the five `POSTGRES_*` vars in each step's `env:`. **Use the inline form; the anchor form above is shorthand for this brief only.**) Deliberately scoped to an explicit spec list: excludes `visual.spec.ts` (snapshot variance), `wire-50-tick` / `polling-tick-aligned` / live-data specs (long/owner-run; they'd now RUN because `SPEC061_TEST_SESSION_ID` is exported — scoping the file list is what keeps them out).

WebGL note: headless Chromium uses SwiftShader; `map-lens-cycling.spec.ts:147-152` already filters the known `maxTextureDimension2D` pageerror. Don't assert on deck.gl canvas pixels in the new spec — assert API GeoJSON + DOM.

### Step 6 — docs touch-up (same branch, small)
- `web/HOW-TO-LOCAL-DEV.md:107,155`: prefix the seed invocation with `RUN_MAIN=true` (currently contradicts `apps.py:55` — verified failure without it).
- `end-turn-flow.spec.ts` header (lines 11-13): same `RUN_MAIN=true` prefix in the owner checklist.

---

## 3. Tests: existing / un-skip / new

**Existing tests covering the area**
- `tests/integration/web/test_game_lifecycle.py` — 5 tests incl. `test_full_lifecycle_create_submit_resolve` (lines 105-143: create → submit AGITATE → resolve → verify tick advanced). Skipped everywhere today (no `POSTGRES_HOST` in CI). Un-skipped by the C.4 job + fixture fix.
- `tests/integration/web/test_bridge_roundtrip.py` — snapshot-shape/serializability. Same gate, same fix.
- `tests/integration/web/test_pg_contract.py` — Django-model-vs-DDL parity on real PG via testcontainers (`postgres` marker). Already green when Docker exists; C.4 puts it in CI for the first time.
- `web/frontend/e2e/end-turn-flow.spec.ts`, `verb-submit.spec.ts` — `SPEC061_TEST_SESSION_ID`-gated; C.5 exports the var, un-skipping them in CI for the first time. (`end-turn-flow` is RED until Phase 1.1 — same `test.fixme` policy as the new spec if merge order demands green.)
- `web/frontend/e2e/auth.spec.ts` — currently broken against real UI (Drift #4); fixed in Step 2.
- `web/frontend/src/components/pages/__tests__/pages-v2.test.tsx:86-127` — jsdom End-Turn unit coverage (already green; untouched).

**New tests (red-first)**
1. `web/frontend/e2e/real-loop.spec.ts` (Step 1) — RED on three counts (bugs #4/#6/#7) by design.
2. The fixture fix in Step 3 is itself TDD'd: run with `POSTGRES_HOST` set → observe `TypeError: __init__() got an unexpected keyword argument 'host'` → fix → green.

---

## 4. Verification commands

```bash
# C.4 locally (one-time: mise run db:up)
docker compose up -d --wait babylon-pg
POSTGRES_HOST=localhost POSTGRES_PORT=5433 POSTGRES_DB=babylon_test \
POSTGRES_USER=test POSTGRES_PASSWORD=test \
  poetry run pytest tests/integration/web/ -v --tb=short

# testcontainers contract tests alone (pre-existing task)
mise run test:pg

# Nothing else regressed (fast gate)
mise run test:q -- tests/integration/web
poetry run ruff check tests/integration/web
poetry run mypy src   # unchanged src; must stay clean

# C.5 locally
mise run web:migrate
( cd web && RUN_MAIN=true poetry run python manage.py seed_initial_game --scenario wayne_county --player admin )
mise run web:dev
cd web/frontend && SPEC061_TEST_SESSION_ID=<printed uuid> npx playwright test e2e/real-loop.spec.ts --reporter=list

# Skip-behavior sanity: without the env var the new spec must skip, not fail
cd web/frontend && npx playwright test e2e/real-loop.spec.ts --reporter=list   # expect: skipped

# Workflow lint (if actionlint is available)
actionlint .github/workflows/ci.yml
```

Commit plan (conventional commits, one per unit): ① `test(integration): fix PostgresRuntime pool fixtures in web integration suites`, ② `test(e2e): add real submit→resolve→results loop spec (red: bugs #4/#6/#7)`, ③ `test(e2e): repair auth spec against Your Operations UI + games-list assertions`, ④ `ci: add postgres-integration and playwright-e2e legs (C.4+C.5)`, ⑤ `docs(web): RUN_MAIN=true required for seed under development settings`.
