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
- **NOT STARTED**: 25 catalog specs (071–083 per audit Part 3, plus Waves
  6–7 content). **Next: spec-071** (see `03-next-spec-071.md`) — now
  unblocked on both foundations.
- **ACTIVE PROGRAM**: `09-program-full-game.md` (ratified 2026-07-03
  evening) — four parallel lanes: `[E:071→101→102→104→105]`
  `[W:090→091→092∥093→094→095→103]` `[D:100 ∥ 098-LODES ∥ 068-slice]`
  `[O:096→099]`. Design canon staged at `design/mockups/` (66 files).
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
  310/310 and 8 Playwright suites green (2026-07-02).
  `web/frontend/src/index.css` still carries the PRE-ratification
  gold/Inter tokens — Cold Collapse migration is spec-090 (needs the
  Article VII amendment, `09` §1 R-VII).
- **Stub inventory** (the debt program 09 retires): bridge dashboard
  methods return `{}` (`get_economy/edges/state_apparatus/journal/alerts/summary` and the wired `get_inspector_*` variants,
  `web/game/engine_bridge.py`); five verb-target methods return
  hardcoded Wayne County fixtures; `investigate`/`move`/`negotiate`
  filtered as unsupported (their handlers belong in catalog specs
  076/075/077); `/games/:id/log` renders "coming soon"; the map only
  renders via `/dev/hexmap` (no in-game map route); AnalysisPage
  topology/correlations are placeholders; `StubEngineBridge` fallback
  serves mock Wayne data when bridge init fails.
- **Django debt** (fixed in spec-091): `accounts` app has NO
  `migrations/` dir (PlayerProfile table never created); `game` app has
  model changes pending `makemigrations`; DB engine is postgis but
  `django.contrib.gis` is absent from `INSTALLED_APPS`.
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
- `tests/integration/economics/` had ~34 NoDataSentinel results (21 FAILED +
  11 SKIPPED). **RESOLVED 2026-07-04 (spec-098 slice)**: LODES data was never
  missing (`fact_lodes_commuter_flow` fully loaded, 2010-2021). The real cause
  was `src/babylon/economics/throughput/adapters.py` reading the pre-spec-086
  `fact_qcew_annual` shape (`own_code='0'` total rollup + 2-digit sectors);
  post-086 that table is 6-digit-leaf-only and the county total moved to
  `fact_qcew_county_rollup`. Fixed by pointing the total-employment read at
  the rollup table and aggregating leaves to sector via
  `dim_industry.sector_code`. The remaining 11 skips were a `TEST_YEAR=2022`
  hardcode in `tests/integration/economics/test_throughput_validation.py`
  exceeding LODES's max year (2021); LODES-dependent tests now pin to a
  separate `LODES_YEAR = 2021` constant. Baseline-neutral: the throughput
  calculator is unwired in the canonical runner. Net: 21 FAILED + 43 SKIPPED
  (whole-file baseline including test_detroit_wiring.py) → 6 FAILED + 28
  SKIPPED — see the two new items below for what's left.
- **NEW (spec-098 slice, un-skipping LODES tests surfaced this)**: 3
  `TestDetroitCommuterPatterns`/`TestCommuterAdjustedMetricsIntegration` tests
  in `test_throughput_validation.py` fail on real data: Oakland County, MI is
  a net job IMPORTER in every available LODES year (2019-2021, e.g. 2021:
  +166,150), not the "bedroom community net exporter" the tests assume —
  and this holds across years, so it isn't a 2021-pandemic artifact. This is
  a pre-existing incorrect empirical assumption in the Feature-014 tests,
  only now exercised (previously masked because `TEST_YEAR=2022` made them
  skip unconditionally). Left failing deliberately — flagged inline in the
  test file — pending an owner call on whether to correct the assertions or
  investigate further. Out of scope for the QCEW-adapter fix.
- **NEW (spec-098 slice)**: `TestCorrelationAnalysis::test_high_pi_wage_correlation`
  and `::test_throughput_class_correlation` (200-county samples) now take
  ~400s/~370s each once QCEW data actually flows (previously failed instantly
  on the schema-drift bug). Each `SQLiteQCEWCountyNAICSSource` call opens its
  own session/query; not fixed in this slice (correctness-only fix; flagged
  for a future batching/session-reuse pass if `tests/integration/economics/`
  runtime becomes a problem).
- **CORRECTED (spec-098 review #2)**: the 3 `test_detroit_wiring.py` failures
  ("No tick dynamics snapshots after 52 ticks" / empty time-series) were
  previously mischaracterized above as "unrelated to LODES/QCEW". They are
  actually the SAME spec-086 QCEW-schema-drift bug class as the throughput
  fix, manifesting in an unpatched sibling adapter:
  `SQLiteQCEWNationalEmploymentSource.get_national_employment` in
  `src/babylon/economics/melt/adapters.py` still queried `fact_qcew_annual`
  with `own_code='0'` + `naics_code='10'` (the pre-086 "total" row
  convention) — both filters match zero rows post-086, so
  `DefaultMELTCalculator.get_melt` returned `NoDataSentinel` ("Employment
  data unavailable") for every year, which is what
  `TickDynamics Step 2: MELT unavailable for year 2022` was logging. Same
  trivial fix pattern as the throughput adapters: read the county
  Total-Covered figure from
  `fact_qcew_county_rollup` (own_code='0') and SUM across all counties
  (the rollup table has no industry dimension, so no sector aggregation is
  needed). Fixed in this slice — all 6 `test_detroit_wiring.py` tests now
  pass (previously 3 failed).
- `mise run test:doctest` is broken (models→formulas circular import under
  `--doctest-modules`); pre-existing, fails identically before Amendment L.
- Django `game` app has model changes with no migration written
  (`makemigrations` pending, owner's call).
- May-era 520-tick trace.csv files are git-LFS pointers locally.
