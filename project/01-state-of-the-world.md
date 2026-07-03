# 01 — State of the World

**As of**: 2026-07-03 ~15:20 EDT. Update this file whenever a unit completes.

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
  (ADR051), graph-substrate migration (ADR052).
- **NOT STARTED**: 25 catalog specs (071–083 per audit Part 3, plus Waves
  6–7 content). **Next: spec-071** (see `03-next-spec-071.md`) — now
  unblocked on both foundations.

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

- **Merge to dev**: the branch chain `fix/web-local-play-wireup` →
  `refactor/lawverian-dialectics` → `refactor/networkx-to-rustworkx`
  (contains everything above plus ADR051+ADR052 programs). Suggest
  splitting engine vs web vs substrate at PR time if clean revert lines
  wanted.
- **dev → main release**: explicitly DEFERRED by owner (main ~200 commits behind).
- `--drop-backup` operator step (above).

## Environment facts (verified 2026-07-02)

- **Repo**: `/home/user/projects/game/babylon`. Python 3.12, Poetry venv at
  `.venv`. Task runner: `mise` (after editing `.mise.toml`, run `mise trust`).
- **Reference DB (SQLite)**: `data/sqlite/marxist-data-3NF.sqlite` — the
  `data/sqlite` DIRECTORY is a symlink to `/media/user/data/babylon-data/sqlite/`
  (the trove is canonical; one DB file, one inode). The symlink is NOT in git.
- **Runtime DB (Postgres)**: Docker container `babylon-pg-isolated`
  (postgres:15, host port 5433),
  DSN `host=localhost port=5433 dbname=babylon_test user=test password=test`.
  Env var consumed by the runner: `BABYLON_PG_DSN`.
  **Storage reality (measured 2026-07-03)**: one canonical 520-tick
  michigan-canada run writes **~7 GB** into `babylon_test`
  (48,827 H3 hexes × full per-tick state); nothing prunes finished runs
  (spec-037 archival is still `NotImplementedError` stubs). Pressure
  valves: `mise run clean:testdb` (drop/recreate/re-bootstrap) and
  `mise run clean:docker` (leaked test containers + volumes). Killed
  test runs leak ephemeral postgis containers — clean:docker flushes.
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
