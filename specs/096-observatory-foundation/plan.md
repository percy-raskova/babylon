# Implementation Plan: Observatory Foundation

**Branch**: `096-observatory-foundation` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/096-observatory-foundation/spec.md`
**Program**: 09 Full-Game Build — Lane O. Provisional number 096 (per §2 first-come rule).

## Summary

Add a read-only bridge from the Django web product to the simulation runner's
Postgres, plus a small Django app (`web/observatory/`) exposing read endpoints
under `/api/observatory/` and a lazy React route group at `/observatory`. The
bridge is a second Django database alias (`sim`) governed by a database router
that (a) refuses migrations for the alias and (b) opens every connection with
`default_transaction_read_only=on`. Endpoints read the runner's **declared view
interfaces only** (`v_*_value_aggregate`, `v_hex_state_asof`) plus the
`tick_commit` table, never the internal `dynamic_*` delta tables directly.
The dashboard is gated by `OBSERVATORY_ENABLED` (True in development, False in
production). Zero engine-dynamics change, zero new tables, zero baseline churn.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.7 (frontend)
**Primary Dependencies**: Django 5.x + DRF (backend); React 19, Recharts 2,
react-router 7, Vitest + MSW (frontend). No new dependencies (`duckdb`/`pyarrow`
already present but not needed until spec-099).
**Storage**: Read-only over the simulation Postgres (`localhost:5433/babylon_test`,
spec-062 `dynamic_*` + spec-087–089 additions) via a second Django DB alias
`sim`; the product DB (`default`, 5432/babylon spec-037) is untouched.
**Testing**: pytest (`tests/unit/observatory/` fast; `tests/integration/observatory/`
Postgres-gated), Vitest + MSW contract tests (`web/frontend/src/observatory/`).
**Target Platform**: Linux dev machine (local play); production build ships with
the flag off.
**Project Type**: Web application (Django backend + React frontend).
**Performance Goals**: Interactive dev tool; series/commit queries return within
typical dashboard latency over a few-hundred-tick session. Tick windows are
bounded to keep payloads finite.
**Constraints**: STRICT read-only over the sim DB; migration refusal for the
`sim` alias; no change to any existing product/engine test or determinism
baseline; ownership law (Lane O writes only `web/observatory/**`,
`web/frontend/src/observatory/**`, one route line in `App.tsx`, settings
additions, and `web/HOW-TO-LOCAL-DEV.md`).
**Scale/Scope**: One new Django app, ~6 read endpoints, ~3 React pages + a
reusable chart, one settings alias + router, doc update.

## Constitution Check (v2.7.0)

*GATE: Must pass before design. Re-checked after design — still passing.*

This spec changes **no dynamics** and adds **no persistence**; it is a
read-only observer. The determinism-hash article (III.7) is therefore not a
change gate here — instead the **read-only guarantee** is the load-bearing
constraint, and it is what the tests prove.

| Article | Binds here? | Disposition |
|---|---|---|
| **II.11 Subsystem Table Ownership** (P1) | **YES — central** | The Observatory is a *cross-subsystem reader*. It reads the runner-owned schema **exclusively through declared interfaces**: the SQL views (`v_county/state/national_value_aggregate`, `v_hex_state_asof`) and the `tick_commit` commit-marker table. It never selects from the internal `dynamic_hex_state` delta table (which is SPARSE; reading it by tick is prohibited). The read-only alias + router make direct-write / schema-mutation structurally impossible. **PASS** and this is the spec's core invariant. |
| **VII Visual Design** (P2) | **YES — UI** | Series charts reuse the product's Recharts + Tufte-minimal, palette-token visual language (VII.2 color-as-data, VII.3 data-ink, VII.9 monospace, VII.10 no chartjunk/hardcoded colors). No decorative glow; colors via CSS tokens. **PASS**. |
| **VIII.9 / VIII.10 Hyperedge anti-patterns** | No | The Observatory renders time-series and tabular data, no community/hyperedge rendering (that is 093/095). N/A. |
| **III.7 Determinism Hash** (P0) | Read-only | The Observatory *surfaces* the `tick_commit` hash chain but computes nothing and changes no dynamics → **no determinism impact** (SC-008). Recompute/verify is deferred to 099. **PASS**. |
| **III.1 No Magic Constants** (P1) | Minor | The only constants are the DSN default (`localhost:5433/babylon_test`, an environment default overridable via `BABYLON_PG_DSN`) and the read-only GUC string — configuration, not model magic. The 52-tick checkpoint cadence etc. are read from the DB, never hardcoded into logic. **PASS**. |
| **III.8 Data Grounding / Aleksandrov** (P0) | Read-only | Every number displayed traces to a runner-persisted view row; nothing is synthesized. **PASS**. |
| **II.12 Authoring API** (P1) | No | No graph construction; N/A. |
| **I.20 Spatial Substrate** (P0) | No | No substrate mutation (read-only). N/A. |
| **IV Michigan Test Case** (P1) | Supports | The canonical Michigan session is a primary read target; integration tests seed a Michigan-shaped session. **PASS**. |
| **Amendment K (dialectics) / L (rustworkx)** | No | Engine-only amendments; the Observatory touches neither the engine nor the graph substrate. N/A. |

**Read-only guarantee (the load-bearing gate)** — proven three ways in tests:
1. Router-level: `allow_migrate("sim", …) is False` (unit).
2. Connection-level: `default_transaction_read_only=on` in the alias OPTIONS →
   any write raises `ReadOnlySqlTransaction` (integration).
3. App-level: the `observatory` app declares **zero models** → contributes zero
   migrations → cannot own or mutate any table (unit + `makemigrations --check`).

No Complexity-Tracking violations. No amendment required (R-AMEND analog: a
read-only observer over already-sanctioned register/view machinery needs no
constitutional change).

## Project Structure

### Documentation (this feature)

```text
specs/096-observatory-foundation/
├── spec.md              # Feature spec (done)
├── plan.md              # This file
├── research.md          # Decisions & rationale (Phase 0)
├── data-model.md        # Read-model entities (Phase 1)
├── quickstart.md        # How to run/verify (Phase 1)
├── contracts/
│   └── observatory-api.md   # Endpoint contracts (Phase 1)
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit.tasks)
```

### Source Code (repository root) — Lane O ownership only

```text
web/observatory/                     # NEW Django app (owned)
├── __init__.py
├── apps.py                          # ObservatoryConfig
├── db.py                            # build_sim_database_alias(dsn) helper
├── router.py                        # SimDatabaseRouter (migration + write refusal)
├── queries.py                       # raw-SQL read helpers over the sim views
├── serializers.py                   # thin dataclasses/typed dicts for payloads
├── views.py                         # DRF read endpoints (flag-gated, auth-gated)
├── urls.py                          # /api/observatory/* routes
└── migrations/__init__.py           # empty — app declares NO models

web/babylon_web/settings/
├── base.py                          # + DATABASES["sim"], DATABASE_ROUTERS, OBSERVATORY_ENABLED default
├── development.py                   # OBSERVATORY_ENABLED = True
└── production.py                    # OBSERVATORY_ENABLED = False
web/babylon_web/urls.py              # + path("api/observatory/", include(...))

web/frontend/src/observatory/        # NEW React route group (owned)
├── ObservatoryPage.tsx              # shell + gating (status probe)
├── SessionPicker.tsx
├── SeriesBrowser.tsx
├── ObservatoryChart.tsx             # Recharts wrapper (Tufte-minimal, tokens)
├── api.ts                           # typed client for /api/observatory/*
├── types.ts
├── csv.ts                           # series → CSV
└── __tests__/*.test.tsx             # Vitest + MSW contract tests
web/frontend/src/App.tsx             # + ONE lazy route line for /observatory

tests/unit/observatory/              # fast, no Postgres (router, alias, gating)
tests/integration/observatory/       # Postgres-gated (read-only proof, endpoints)

web/HOW-TO-LOCAL-DEV.md              # + two-DB alias map section
```

**Structure Decision**: Web application. The Observatory is deliberately a
*separate* Django app that BYPASSES `web/game/engine_bridge.py` (Lane W's file):
it issues raw read-only SQL against the runner-owned tables through the `sim`
alias. This keeps the two lanes' file ownership disjoint (collision law, §3) and
keeps the read-only boundary auditable in one place (the router + alias).

## Key Design Decisions (see research.md for rationale)

1. **Second Django DB alias `sim`**, ENGINE `django.db.backends.postgresql`
   (plain — no PostGIS needed for the value views), config built by
   `build_sim_database_alias(dsn)` which parses `BABYLON_PG_DSN` (libpq
   keyword DSN, the `tools/tick_probe.py` default) into Django params and sets
   `OPTIONS={"options": "-c default_transaction_read_only=on"}`.
2. **`SimDatabaseRouter`**: `allow_migrate` returns `False` for `db == "sim"`
   (and `None` otherwise); `db_for_read`/`db_for_write` return `None` (the
   observatory app has no models, so default routing governs product models).
   Observatory queries target the alias explicitly via `connections["sim"]`.
3. **Session source of truth** = `tick_commit` grouped by `session_id`
   (authoritative for committed ticks), LEFT JOIN `game_session` for optional
   scenario/status enrichment (`game_session.id` is CHAR(32) hex; joined via
   `replace(session_id::text,'-','')`). Absence of `game_session` rows must not
   break the listing (FR-007).
4. **Hex reads** go through `v_hex_state_asof` only (FR-013); the raw sparse
   `dynamic_hex_state` is never queried by tick.
5. **Flag gate**: endpoints return HTTP 404 when `OBSERVATORY_ENABLED` is False
   (security-through-obscurity, mirroring `/health/detail/`), checked BEFORE any
   DB access. A `GET /api/observatory/status/` returns `{enabled: true}` (200)
   when on and 404 when off, so the React route can gate itself off a single
   backend source of truth without a build-time env var.
6. **Frontend**: `/observatory` is a lazily-imported chunk (React.lazy +
   Suspense) — one route line in `App.tsx` — so it adds no weight to the main
   bundle (FR-016) and cleanly overlaps trivially with Lane W's App.tsx edits.
   Charts are an observatory-local Recharts wrapper (the existing
   `charts/TimeSeries.tsx` is store-coupled and outside Lane O ownership;
   "reuse" = reuse the library + visual language in-lane).

## Testing Strategy (TDD, red-first)

- **Unit (fast, no DB)** — `tests/unit/observatory/`:
  - `test_router.py`: migration refusal + write-routing contract.
  - `test_db_alias.py`: DSN parse → correct ENGINE/HOST/PORT/NAME/USER/PASSWORD
    and read-only OPTIONS.
  - `test_settings.py`: app installed, router registered, flag defaults per env.
  - `test_endpoints_gating.py`: 404 when disabled, 403/401 when unauthenticated
    (no DB touched).
  - `test_queries_sql.py`: query builders emit parameterized SQL against the
    declared views/table names only (no `dynamic_hex_state` by tick).
- **Integration (Postgres-gated)** — `tests/integration/observatory/`:
  - `test_read_only.py`: a write via `connections["sim"]` raises
    `ReadOnlySqlTransaction`; `allow_migrate` proven against live alias.
  - `test_endpoints_data.py`: seed a unique session (migrations + envelope via
    `pg_pool`), then endpoints return that session's data (list, ticks, national/
    state/county series, commit chain, hex frame, CSV).
- **Frontend (Vitest + MSW)** — `web/frontend/src/observatory/__tests__/`:
  - contract test per endpoint (response envelope parsed correctly);
  - disabled-state render (status 404 → disabled banner);
  - session-picker → series-browser flow renders a chart; CSV builder output.

All red-first: write the failing test, observe RED, then implement to GREEN.

## Complexity Tracking

No constitutional violations to justify. The design is the minimum that
delivers a read-only bridge: one alias, one router, one app, no models.
