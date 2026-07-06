# 01 — State of the World

**As of**: 2026-07-03 ~21:30 EDT. Update this file whenever a unit completes.

## Current branch + the two foundations (both COMPLETE 2026-07-03)

Branch: **`refactor/networkx-to-rustworkx`** (continues
`refactor/lawverian-dialectics`, which was cut off `fix/web-local-play-wireup`).
Two foundation programs landed back-to-back today; spec-071 is next and
consumes both:

1. **Lawverian dialectics refactor — COMPLETE (Phases A–E, ADR051)**.
   Record: `06-lawverian-dialectics.md` (consolidated master). The
   contradiction layer is executable: OppositionRegistry of measured
   adjunction defects, connectivity/scale/value-form instances, level
   lattices + Aufhebung, fixed-point regimes; Systems 19–21 LIVE;
   EventType 71 (`LEVEL_TRANSITION`); constitution Amendment K;
   canonical re-baseline accepted (contradiction_field rows flow,
   max_tension non-saturating).
1. **Graph substrate: NetworkX → rustworkx — COMPLETE (Amendment L,
   ADR052)**. Record: `08-graph-substrate.md`. `BabylonGraph` /
   `BabylonUGraph` (`src/babylon/engine/graph.py`) are BOTH the
   GraphProtocol implementation AND the nx-compat authoring API;
   NetworkXAdapter deleted; zero `networkx` imports in `src/`+`web/`
   (semgrep-banned); determinism baselines byte-identical; raw-layer
   algorithms 2–5x.

## Catalog scoreboard

- **DONE**: spec-070 Balkanization (pre-session), spec-086 QCEW loader +
  imputation, spec-097 (decision record), Lawverian dialectics refactor
  (ADR051), graph-substrate migration (ADR052), **storage scaling
  program specs 087+088+089 (ADR053, same day)** — delta persistence +
  partitioning + local Parquet archival; canonical Michigan run
  re-verified on the new substrate (Δ=0.000%, 455,720 vs 25.4M hex
  rows, 17 vs ~52 min).
- **IN REVIEW (2026-07-04)**: **spec-071 Reactionary Subject** — Lane-E
  implemented on branch `071-reactionary-subject` (ADR054):
  speckit spec/plan/tasks + formulas/defines + enums + SocialClass fields +
  FascistFactionSystem @17.4 + chauvinism/defection + L_u SPONTANEOUS_RIOT +
  fascist OODA verbs + carceral create-on-demand + crisis integration.
  `mise run check` green; income-circuit suite green;
  `qa:e2e-regression` **byte-identical (total_v Δ=0.000%, liveness 3/3)** —
  the always-on FascistFactionSystem is dormant during the pacified decade
  (agitation crisis-gated), so NO baseline regeneration was needed. Canonical
  520-tick relaunched at close-out (orchestrator monitors/archives). Awaiting
  BD merge to dev.
- **NOT STARTED**: 24 catalog specs (072–083 per audit Part 3, plus Waves
  6–7 content). Next engine unit after the trade window: Wave 2 (072–074).
- **ACTIVE PROGRAM**: `09-program-full-game.md` (ratified 2026-07-03
  evening) — four parallel lanes: `[E:071→101→102→104→105]`
  `[W:090→091→092∥093→094→095→103]` `[D:100 ∥ 098-LODES ∥ 068-slice]`
  `[O:096→099]`. Design canon staged at `design/mockups/` (66 files).
- **spec-101 Trade activation — CODE DONE 2026-07-04** (branch
  `101-trade-activation`, on origin, ADR055, unmerged; opens the shared
  101+102 proof window). Boundary flows are LIVE: the runner populates the
  four dormant TickContext keys so `_invoke_phi_distribution_if_wired`
  records DRAIN_EDGE rows every tick. **Discovery**: Hickel Φ is a single
  national aggregate (all blocs hydrated Φ=0), so the national Φ is
  attributed across engine nodes by bilateral-trade share via an injective
  `_NODE_TO_BLOC` crosswalk (`postgres_initialization.py`) — **the #1
  owner-review item** (india/latin_america get Φ=0; russia_csi→Europe is
  weak). Conservation `Σ DRAIN_EDGE ≡ Φ_week` per bloc gated (relative
  residual; migration 0031 admits `external:<node>` scale). `vol2_step`
  TRADE_EDGE stays gated (needs 098-LODES). 18 unit + 4 integration tests
  green; total_v + liveness unchanged; 5-tick baseline regenerated.
  Canonical `sim:e2e-bg` launched for 83/83 re-verification.
- **spec-102 Gamma hydration + scheduled bloc shocks — CODE DONE
  2026-07-04** (branch `102-gamma-shocks`, stacked on
  `101-trade-activation`@`8210db17`, ADR056, unmerged; closes the shared
  101+102 proof window). `SQLiteGammaHydrationSource` hydrates real
  per-year α (BEA final demand + bilateral trade) and γ_import
  (1/Hickel-ERDI), killing `basket_visibility.py`'s MVP hardcode (III.1).
  **Decisive verified finding**: NO canonical re-baseline needed —
  `ServiceContainer.create(defines=defines)` in the headless runner never
  wires `melt_calculator`/`basket_calculator`, so `TickDynamicsSystem`
  (the only caller of `get_gamma_basket`) is an unconditional no-op in
  every headless-runner execution today, canonical included.
  `ScheduledBlocShock` + `SimulationRunConfig.shock_schedule` ship a
  deterministic, non-agentic (R-AMEND) exogenous Φ-multiplier schedule,
  empty by default. **Course-corrected mid-implementation** (empirical):
  the planned `tick_commit.determinism_hash` cross-run diff was found to
  always diverge (embeds `session_id` by construction — confirmed by
  running the unmodified spec-101 baseline twice); the shipped
  determinism test instead compares raw persisted hex state +
  `DRAIN_EDGE` magnitudes (byte-identical across two runs). A separate
  test confirms the shock visibly bends a bloc's Φ trajectory at its
  scheduled tick. 35 unit + 5 integration tests green; both existing
  baselines (`michigan-e2e.json`, `detroit-tri-county-5t.json`) untouched.
  - **Lane D spec-100 County-exposure loader — DONE 2026-07-04** (branch
    `100-county-exposure`, unmerged; two repos: babylon worktree schema +
    babylon-data loader). Built the never-computed `county_exposure_by_external`
    map (BEA I-O import coeffs × QCEW county shares via `bridge_naics_bea`) +
    bloc-year bilateral trade. Two additive SQLite reference tables
    (`fact_county_exposure_by_external` 384,200 rows,
    `fact_bilateral_trade_annual` 120 rows) applied to the real DB; all gates
    green (sum=1.0, weight-conservation ±2%, hash reproduces, schema-valid
    audit). Unblocks
    spec-101 (S1). Reconciliation notes in
    `specs/100-county-exposure/research.md`.

## What shipped 2026-07-02 (one session), by commit

All on branch **`fix/web-local-play-wireup`** (cut from
`086-qcew-loader-imputation`, so it contains the full 086 history too —
BD may merge as one or split web/engine/data at PR time).

### Spec-086 (QCEW imputation) — complete + live-applied

- `619a86f6` US2: `mise run data:qcew` CLI task + tombstone + ledger
- `a9abb05c` CS### CSA exclusion regression pin
- `08832aad` US3: audit contract + provenance suites
- `53cde3da` live-DB reconciliation gates SC-001..SC-006
- `a7ec34bc` T034 live 2010 dry-run PASS
- `7737a0d0` ADR050 + state.yaml v2.14.0 + live-apply audit artifacts
- `0394b43d` T038 post-imputation canonical baseline + regression-gate scope repair
- **Live result**: `fact_qcew_annual` 15,097,464 → 14,670,249 leaf rows;
  240,488 rollup rows; 10,479,767 imputed (71.4%); all 9 SCs verified live
  (SC-003 Wayne 2010: +0.001%; wages exact to the penny; SC-005 national
  +0.19..+0.41%/yr; SC-008 digests reproduce).
- **Operator follow-up (Percy)**: after her own verification, run
  `mise run data:qcew -- --drop-backup` to drop the ~5 GB
  `fact_qcew_annual__pre_086` backup table.

### Web local-play sprint — all green

- `e3881c98` fix the 6 spec-061-era backend unit failures → backend web 246/246
- `574ed157` TopBarV2 reads live snapshot (scenario via `/api/games/`)
- `8b91b01e` IntelPageV2 Communities variant (over `snapshot.hyperedges`) +
  frontend 310/310 (first fully-green frontend since spec-061). Store-seeding
  helper: `web/frontend/src/__tests__/helpers/seedSnapshot.ts`.

### Engine: the extinction forensics + fixes (see `02-engine-truths.md`)

- `b758a4fa` ADR044 completion: per-county Territory + TENANCY income circuit
- `2c81f86a` canonical baseline with living economy (83/83 counties alive @ t519)
- `02ad41b2` population-liveness gate (`terminal_state.counties_with_population`
  - compare-bundle assert)
- `23cfacc2` **core workers hydrate as LABOR_ARISTOCRACY** + WAGES edge →
  the full imperial circuit runs (Φ grows 0.008→0.78/tick over 80 ticks,
  bourgeoisie accumulate, P(S|A)→0.995 while P(S|R)=0.167)

## Canonical verification: DONE (2026-07-03 ~00:35 EDT)

The 520-tick labor-aristocracy canonical VERIFIED and committed. (First
attempt died at t387 when session compaction killed the harness background
task — relaunch as a `nohup`-detached process survived; lesson: long runs
must be detached, not harness-managed.) Bundle `2026-07-02T23-37-23Z`:
`counties_alive == counties_with_population == 83`; qa:e2e-regression green
(liveness 3/3, total_v Δ=0.000%, zero conservation criticals). This baseline
is the PRE-REFACTOR comparison point for the Lawverian program — Phase E
re-baselines after the contradiction semantics change.

## In-flight / awaiting Percy (BD)

- ~~Merge to dev~~ **DONE 2026-07-03 ~20:15 EDT** (owner-directed):
  `dev` fast-forwarded `9dd4c4f6 → 2f506bc2` (97 commits — web
  local-play sprint, ADR051 dialectics, ADR052 substrate, ADR053
  storage program) and pushed to origin. Historical branch lines are
  preserved as `archive/*` tags; working branches now: `main`, `dev`,
  `u/percy`, plus per-program branches.
- **dev → main release**: explicitly DEFERRED by owner (main ~200 commits behind).
- `--drop-backup` operator step (above).
- **Program 09 owner items** (see `09-program-full-game.md` §6):
  Article VII palette amendment (with 090); DB convergence question;
  095's chronicle partial-forward; national tick budget (after 104);
  USGS minerals stretch; EndgameDetector priority resolution (at 095).

## Environment facts (verified 2026-07-02)

- **Repo**: `/home/user/projects/game/babylon`. Python 3.12, Poetry venv at
  `.venv`. Task runner: `mise` (after editing `.mise.toml`, run `mise trust`).
- **Reference DB (SQLite)**: `data/sqlite/marxist-data-3NF.sqlite` — the
  `data/sqlite` DIRECTORY is a symlink to `/media/user/data/babylon-data/sqlite/`
  (the trove is canonical; one DB file, one inode). The symlink is NOT in git.
- **Runtime DB (Postgres)**: compose-managed container `babylon-pg-isolated`
  (pinned `postgis/postgis:16-3.4` + pgvector, tuned conf, data dir on
  the 3.6 TB drive via `BABYLON_PG_DATA`; `docker-compose.yml` +
  `docker/postgres/`), host port 5433,
  DSN `host=localhost port=5433 dbname=babylon_test user=test password=test`.
  Env var consumed by the runner: `BABYLON_PG_DSN`. Fresh-clone
  bootstrap: `mise run setup`.
  **Storage (solved 2026-07-03, specs 087–089/ADR053)**: delta
  persistence (changed rows + yearly checkpoint frames; canonical
  Michigan = 455,720 hex rows vs 25.4M before), LIST(session_id)
  partitioning, `tick_commit` (per-tick commit marker + queryable
  III.7 hash chain), as-of views (`v_hex_state_asof` is the hex-history
  read interface — raw `dynamic_hex_state` is SPARSE), local Parquet
  archival: `mise run sim:archive -- archive --session <id>` →
  verify → DROP PARTITION → DuckDB reads under `BABYLON_ARCHIVE_ROOT`
  (`/media/user/data/babylon-archives`). Archive finished sessions
  instead of letting them accumulate; `mise run clean:docker` still
  flushes leaked test containers. National res-7 projection:
  6.8–22.7 GiB/run (was ~450 GB). `qa:storage-budget` gates rows/tick.
- **babylon-data repo** (loader home): `/home/user/projects/game/babylon-data`;
  imported via committed symlink `src/babylon_data` → that repo's
  `src/babylon_data`, with `PYTHONPATH=src`. QCEW loader modules:
  `singlefile.py`, `hierarchy.py`, `imputation.py`, `writer.py`,
  `validation.py`, `audit.py`, `__main__.py` (+ legacy `api_client.py`,
  `downloader.py`, `loader_3nf.py` recovered earlier).
- **Staged QCEW source data**: `/media/user/data/babylon-data/qcew/`
  (BLS annual singlefiles 2010–2024, 8.3 GB, complete).
- **Canonical sim**: `mise run sim:e2e-bg` (daemonized, pidfile+log under
  `.sim-pids/`; ~45–120 min); watch via `mise run sim:status` / `sim:watch`.
  Direct command + baseline flag: see the standing loop in
  `05-catalog-execution.md`. 5-tick gate baseline:
  `tests/baselines/detroit-tri-county-5t.json` via `mise run qa:e2e-regression`.
- **Test reports**: every `mise run test:*` writes
  `reports/test-results/<task>/{junit.xml,report.json,report.html}`.
- **Web**: `mise run web:dev` / `web:test` / `web:check`; backend web tests
  `poetry run pytest tests/unit/web/`.

## spec-091 — Frontend consolidation + Django debt (DONE 2026-07-03, branch `091-frontend-consolidation`)

Stacks on `090-cold-collapse` (`42232a15`). One codebase, no legacy siblings:

- **042 audited + closed superseded** (R-042): `specs/042-game-ui-overhaul/AUDIT-091.md`
  classifies all 49 tasks (done-with-evidence / superseded / residual→092/093/095);
  042's god-page composition (`GameShell`/`RightPanel`/`BottomPanel`/`LensBar`) is
  gone, its library layer survived in the 16-route app.
- **Course-correction verified** (phases 1–7): `specs/091-.../course-correction-verification.md`.
  Phases 1/2/3/6/7 met; Phase-4/5 infra (`lib/verbs`+`VerbShell`, `HexInspector`+
  `BreakdownTooltip`) exists+tested but UNROUTED (superseded by spec-061 `VerbPage`/
  `IntelPageV2`) — PRESERVED as infra; live provenance wiring is spec-093.
- **Legacy siblings deleted**: `ActionPage`, `GameView`, `HexMap`, `IntelPage`,
  `OrganizationsPage`, `OrgDashboard`, `TimeSeriesPanel` + the dead panel-`Inspector`
  cluster (`Inspector`, `Breadcrumbs`) + their dead tests; react-leaflet removed
  (`rg leaflet web/frontend/src` EMPTY; lockfile-only, node_modules untouched).
  `mock_map_data.json` was RESTORED (it is the backend `seed_hex_data` fixture, not
  DevHarness-only). The `/dev/hexmap` DevHarness (leaflet-only) retired.
- **Map promoted to first-class**: `BriefingPage` now renders the live `DeckGLMap`
  (was the SVG `HexMapPlaceholder`), snapshot-fed.
- **Django debt cleared**: `web/accounts/migrations/0001_initial.py` (PlayerProfile
  → `player_profile` table), `web/game/migrations/0011_*` (7 runner-owned snapshot
  models, all `managed=False` — Django tracks state, does NOT own the spec-037
  tables), `django.contrib.gis` added to INSTALLED_APPS.
- **090 residuals a–f**: prettier hook pinned to 3.8.1; 35 semantic type-role
  tokens ported into `index.css`; faux-italic removed (BreakdownTooltip); C6
  lens→layer contract pinned against independent expectations; ramp docstrings
  aligned to the Article VII amendment (monotonic EXCEPT named alarm terminals/
  diverging); NEW Playwright visual-baseline suite (`e2e/visual.spec.ts` + login
  chrome baseline) pinning the Cold Collapse canon.
- **Review fixes (2026-07-04, same branch)**: (1) the Briefing deck.gl map is
  now wrapped in an `ErrorBoundary` (HexMapPlaceholder fallback) so a WebGL init
  failure degrades gracefully instead of white-screening the in-game index route
  (+ Vitest test forcing a throw); (2) the two god-page e2e relics
  (`navigation.spec`, `game-loop.spec`) that asserted DELETED UI were removed
  (superseded by the spec-061 live suites) and a backend-free real-browser route
  smoke added; (3) 5 GameView/ActionPage orphans (ActionPanel, TickResults,
  ResourcePanel, TrapIndicator, VerbShell — all untested, no consumer) DELETED as
  deletion debris; (4) 042-audit line counts corrected (game.ts 578, lensDefinitions.ts 340).
- **Gates**: Vitest **364/364** (44 files); `poetry run pytest tests/unit/web/`
  **248 green**; backend-free Playwright (visual + route smoke) **3 green**; tsc
  clean. **OWNER-VERIFICATION-PENDING**: the behavioural Playwright gate (auth
  login-success/logout + the 5 `SPEC061_TEST_SESSION_ID` suites — briefing-live-data,
  orgs-live-data, verb-submit, intel-results-analysis, polling-tick-aligned) needs
  a live seeded backend (`mise run web:dev` + a testuser + a seeded session);
  these were NOT run here — see the owner-run checklist in
  `.superpowers/sdd/reports/091.md`. The code work is done; this gate leg awaits
  Percy. (Pre-existing note: a few fetch-error unit tests are mildly flaky under
  network-race; a clean `npx vitest run` is 364 green.)

## Web layer facts (verified 2026-07-03 — read before any web/ or Observatory work)

- **THE TWO-DB SPLIT** (documented nowhere else until now): the web app
  (Django, `web/babylon_web/settings/base.py`) runs against its OWN
  Postgres at `localhost:5432/babylon` using the spec-037 layer schema
  (`game_session`, `hex_latest`, `territory_snapshot`, `tick_summary`,
  …; Django models are `managed=False` wrappers). The headless sim
  runner writes `localhost:5433/babylon_test` using the spec-062
  `dynamic_*` schema + the 087–089 additions (`tick_commit`,
  `v_hex_state_asof`, `v_county/state/national_value_aggregate`,
  session partitioning). **Nothing bridges them** — no Django model,
  endpoint, or ETL reads `dynamic_*`. The Observatory (program 09,
  spec-096) adds a read-only `DATABASES["sim"]` alias for exactly this;
  DSN pattern: `tools/tick_probe.py`.
- **Frontend**: React 19, Vite 6, Tailwind v4, Zustand 5, deck.gl 9,
  Recharts 2, Sigma 3; the v2 16-route architecture is LIVE in
  `web/frontend/src/App.tsx`; polling (2 s), no websockets; Vitest
  **378/378** (was 364 at spec-091; +14 across spec-092's Event Log +
  Tick Resolution pages, journal/alerts contract test, End Turn wiring).
  Playwright: 3 backend-free green (visual + route smoke); the god-page
  relics were deleted, leaving 7 behavioural suites (was 6; spec-092
  added `end-turn-flow.spec.ts`) that are **owner-run** (need a seeded
  backend).
  `web/frontend/src/index.css` **now carries the ratified Cold Collapse
  tokens** (spec-090, branch `090-cold-collapse`): cyan-spire primary,
  gold demoted to scarce rupture, four self-hosted OFL font families
  (JetBrains Mono / Space Grotesk / Redaction 35 / Departure Mono under
  `web/frontend/public/fonts/`; Inter + Roboto Mono removed; no Google
  Fonts at runtime), and the six luminance-monotonic data ramps in
  `theme/colors.ts` + `lib/lensDefinitions.ts`. The **Article VII
  amendment** is DRAFTED (`specs/090-cold-collapse/article-vii-amendment.md`)
  and awaits Percy's ratification at PR review — per R-VII the branch
  carries the full swap but must not merge until ratified.
- **Stub inventory** (the debt program 09 retires): bridge dashboard
  methods return `{}` (`get_economy/edges/state_apparatus/summary` and
  the wired `get_inspector_*` variants, `web/game/engine_bridge.py`);
  ~~`get_journal`/`get_alerts`~~ **RESOLVED (spec-092)**:
  `get_journal_dashboard`/`get_alerts_dashboard` now read real
  `tick_event` history (`resolve_tick` persists each tick's events via
  the new `_persist_tick_events_safe` helper +
  `PostgresRuntime.query_session_events`/existing `query_tick_events`);
  five verb-target methods return hardcoded Wayne County fixtures;
  `investigate`/`move`/`negotiate` filtered as unsupported (their
  handlers belong in catalog specs 076/075/077); ~~`/games/:id/log`
  renders "coming soon"~~ **RESOLVED (spec-092)**: `/games/:id/log` is
  the real `EventLogPage` (severity-filtered over `useJournal`) and a
  new `/games/:id/resolution` `TickResolutionPage` + End Turn button
  (OrgsPage) now exist; ~~the map only renders via `/dev/hexmap`~~
  **map is now first-class on Briefing (spec-091); `/dev/hexmap`
  retired**; AnalysisPage topology/correlations are placeholders;
  `StubEngineBridge` fallback serves mock Wayne data when bridge init
  fails. **Known gap (spec-092, unfixed)**: `lib/eventClassifier.ts`'s
  severity map uses UPPERCASE event-type keys (matching
  `test/fixtures.ts`'s existing convention) while the real `EventType`
  enum values are lowercase snake_case (verified in
  `src/babylon/models/enums/events.py`) — real production events all
  classify as "informational" today; predates spec-092 (already
  affects the live notification tray via `gameStore.ts`), flagged, not
  silently fixed.
- ~~**Django debt** (fixed in spec-091)~~ **RESOLVED (spec-091)**:
  `accounts/migrations/0001_initial.py` materializes PlayerProfile;
  `game/migrations/0011_*` captures pending changes (all `managed=False`);
  `django.contrib.gis` is now in `INSTALLED_APPS`.
- **Design canon**: staged at `design/mockups/` (66 files, replay-
  extracted from the claude.ai export 2026-07-03; provenance +
  fidelity caveats in `design/mockups/PROVENANCE.md`).

## Known non-blockers (pre-existing, documented, do not "fix" in passing)

- `tests/unit/economics/throughput/test_commuter_adjusted.py::…::test_frozen` fails (pre-existing).
- `tests/integration/test_grundrisse_cycle.py::TestPrincipalSelection` briefly
  broke between D5 and the Phase E review: the C1.7-era test fed the WAGES edge
  but the Phase-D5 wage measure reads `(w_paid, v_produced)` node attrs. FIXED
  at the Phase E review boundary — the test now drives the defect pair directly
  (same arithmetic, new channel) and asserts the overtake on the wage/imperial
  defect family (their gaps are pinned equal until Phase D's periphery data).
- `WorldState.from_graph()` drops `institution_relations` + non-core
  Relationship attrs on round-trip.
- EndgameDetector docstring claims REVOLUTIONARY_VICTORY-first priority; code
  checks it last (FR-033).
- Django `accounts` app has no `migrations/` dir.
- `tests/integration/economics/` has ~34 data-availability failures
  (NoDataSentinel — LODES rows absent from the reference DB build;
  spec-086/097/098 remediation territory). Untouched by the 2026-07-03
  programs; not migration breakage.
- `mise run test:doctest` is broken (models→formulas circular import under
  `--doctest-modules`); pre-existing, fails identically before Amendment L.
- Django `game` app has model changes with no migration written
  (`makemigrations` pending, owner's call).
- May-era 520-tick trace.csv files are git-LFS pointers locally.
