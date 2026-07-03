# 01 — State of the World

**As of**: 2026-07-03 ~00:30 EDT. Update this file whenever a unit completes.

## PROGRAM PIVOT (2026-07-02 evening, owner directive)

Percy re-prioritized: the **Lawverian dialectics refactor** is now the most
important foundation of the active goal — it precedes spec-071. Contract:
`06-lawverian-dialectics.md`. Owner decisions: direct refactor (NO speckit),
re-ground in place, executable + law-tested category theory, Fable designs
and reviews / implementation delegated. Branch:
`refactor/lawverian-dialectics` (off `fix/web-local-play-wireup`).

- Phase A DONE (`091f6f74`): `src/babylon/dialectics/` core
  (GaloisConnection, AdjointCylinder, LevelLattice/Aufhebung,
  OppositionRegistry), 43 law tests, mypy --strict clean.
- Phases B–E: per `06-lawverian-dialectics.md` §4–§7 (delegated sessions).
- After Phase E: resume the catalog at spec-071, which then CONSUMES the
  categorical machinery (fascist pull as gap/monad computation).

## Catalog scoreboard

- **DONE**: spec-070 Balkanization (shipped pre-session), spec-086 QCEW
  loader + imputation (this session; not an audit-catalog spec but the
  ratified data prerequisite), spec-097 finalized as decision record.
- **IN PROGRESS**: Lawverian dialectics refactor (see pivot above).
- **NOT STARTED**: 25 catalog specs (071–083 per audit Part 3, plus Waves 6–7
  content). Next after the refactor: **spec-071** (see `03-next-spec-071.md`).

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

- **Merge to dev**: `fix/web-local-play-wireup` (contains everything above).
  Suggest splitting engine vs web at PR time if clean revert lines wanted.
- **dev → main release**: explicitly DEFERRED by owner (main ~200 commits behind).
- `--drop-backup` operator step (above).

## Environment facts (verified 2026-07-02)

- **Repo**: `/home/user/projects/game/babylon`. Python 3.12, Poetry venv at
  `.venv`. Task runner: `mise` (after editing `.mise.toml`, run `mise trust`).
- **Reference DB (SQLite)**: `data/sqlite/marxist-data-3NF.sqlite` — the
  `data/sqlite` DIRECTORY is a symlink to `/media/user/data/babylon-data/sqlite/`
  (the trove is canonical; one DB file, one inode). The symlink is NOT in git.
- **Runtime DB (Postgres)**: local test instance,
  DSN `host=localhost port=5433 dbname=babylon_test user=test password=test`.
  Env var consumed by the runner: `BABYLON_PG_DSN`.
- **babylon-data repo** (loader home): `/home/user/projects/game/babylon-data`;
  imported via committed symlink `src/babylon_data` → that repo's
  `src/babylon_data`, with `PYTHONPATH=src`. QCEW loader modules:
  `singlefile.py`, `hierarchy.py`, `imputation.py`, `writer.py`,
  `validation.py`, `audit.py`, `__main__.py` (+ legacy `api_client.py`,
  `downloader.py`, `loader_3nf.py` recovered earlier).
- **Staged QCEW source data**: `/media/user/data/babylon-data/qcew/`
  (BLS annual singlefiles 2010–2024, 8.3 GB, complete).
- **Canonical sim**: `poetry run python -m babylon.engine.headless_runner --scope michigan-canada --ticks 520` (add
  `--write-baseline tests/baselines/michigan-e2e.json` to re-baseline)
  (~45–75 min; run in background). 5-tick gate baseline:
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
- **Lawverian dialectics refactor (project/06) COMPLETE** — Phases A-E on branch
  `refactor/lawverian-dialectics`; see ADR051 and `project/06` §7. The contradiction
  layer is now executable (opposition registry + level lattices + fixed-point regimes);
  Systems 19-21 are live; EventType gained LEVEL_TRANSITION.
- `WorldState.from_graph()` drops `institution_relations` + non-core
  Relationship attrs on round-trip.
- EndgameDetector docstring claims REVOLUTIONARY_VICTORY-first priority; code
  checks it last (FR-033).
- Django `accounts` app has no `migrations/` dir.
- ~68 modified test files sit in the working tree from a pre-session state —
  NOT this program's work; leave them alone.
- May-era 520-tick trace.csv files are git-LFS pointers locally.
