# Test Suite Reference

Reference documentation for the `tests/` tree — what exists, how it is tiered in CI, and
the commands a contributor actually runs. For *why* the suite is split this way, see
`ai/decisions/ADR008_test_separation.yaml`.

## Directory structure

```
tests/
├── conftest.py        # Root fixtures: BLAS pin, Hypothesis profiles, random-seed isolation,
│                       # Django DB setup override, Postgres pool fixture, mock fixtures
├── constants.py        # TestConstants — pulls from GameDefines (YAML-first)
├── constants_063.py     # Spec-063 fixtures: Detroit tri-county H3 hex sets, port codes, FIPS sets
├── assertions.py         # BabylonAssert fluent assertion library (domain-language assertions)
├── test_simplex_invariants.py  # Root-level Hypothesis property tests (consciousness ternary simplex)
├── unit/                 # Fast, isolated tests — the dev CI tier (see below)
├── integration/           # Multi-component / DB-backed tests (Postgres, reference SQLite)
├── property/               # Hypothesis property-based tests (circulation, dialectics, invariants)
├── contract/                # Contract tests pinning cross-boundary interfaces
├── scenarios/                 # Full multi-tick simulation scenario tests
├── benchmark/                   # Performance/memory benchmarks for tensor operations
├── baselines/                     # Committed golden JSON/CSV traces for qa:regression
├── fixtures/                        # Shared static test data (qcew/, test_data/)
├── factories/                         # DomainFactory — builds configured domain entities for tests
├── mocks/                                # Hand-written test doubles (e.g. metrics_collector spy)
├── _helpers/                               # Shared invariant-checking helpers (h3 round-trip, MELT
│                                            # consistency, metamorphic, serialization, ...)
└── scripts/                                  # Shell/Python one-off verification scripts, not pytest
```

There is no `tests/unit/data/`, `tests/unit/ui/`, or `tests/e2e/`. Browser E2E tests
(Playwright) live at `src/frontend/e2e/`, not under `tests/`.

`tests/unit/` mirrors `src/babylon/`'s top-level packages (`ai`, `balkanization`,
`bifurcation`, `config`, `core`, `dialectics`, `domain`, `economics`, `engine`, `formulas`,
`infrastructure`, `institution`, `kernel`, `ledger`, `metrics`, `models`, `observatory`,
`ooda`, `organizations`, `persistence`, `protocols`, `reference`, `sentinels`, `state_ai`,
`tools`, `topology`, `utils`, `web`) plus a handful of root-level guard tests
(`test_blas_thread_cap.py`, `test_contract_parity.py`, `test_mise_tasks.py`,
`test_public_import_surface.py`, ...).

## Root `conftest.py`

- **BLAS/OpenMP thread pin** — sets `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`,
  `MKL_NUM_THREADS`, `NUMEXPR_NUM_THREADS`, `RAYON_NUM_THREADS` to `1` before any
  numpy/scipy/rustworkx import, and holds a `threadpoolctl` limiter alive for the session.
  Prevents OpenBLAS/rayon thread oversubscription under `pytest-xdist`; also a determinism
  win (fixes FP reduction order per Constitution III.7). See `test_blas_thread_cap.py`.
- **Mutmut compatibility shim** — makes `multiprocessing.set_start_method` idempotent
  (mutmut calls it at import time, conflicting with pytest-asyncio's context).
- **Hypothesis profiles** — registers `mutmut`, `default`, and `slow` here; `dev`, `ci`, and
  `nightly` are registered in `tests/property/conftest.py` (must run after this file per
  Hypothesis's registration-before-load ordering). `HYPOTHESIS_PROFILE` env var selects the
  active profile (defaults to `default`); see the table below.
- **`_isolate_random_state`** (autouse) — seeds `random` with `42` before every test and
  restores the prior state after, for reproducibility across test orderings.
- **`enable_logging_propagation`** (autouse) — re-enables propagation on the `babylon`
  logger so `caplog` captures it despite Django disabling propagation.
- **`test_dir`** (session-scoped) — temp directory, owner-only permissions, cleaned up after
  the session.
- **`reference_sqlite_session_factory`** — function-scoped SQLAlchemy session factory backed
  by a fresh in-memory `NormalizedBase` schema (same dialect as the production reference DB
  at `data/sqlite/marxist-data-3NF.sqlite`).
- **`metrics_collector`** — fresh `MetricsCollector` per test.
- **`mock_llm_provider`** / **`mock_simulation`** — `MagicMock(spec=...)` fixtures for
  `LLMProvider` and `Simulation`. These are the only mock fixtures the root conftest
  provides; there are no ChromaDB mock fixtures (ChromaDB was removed in favor of pgvector —
  see `tests/unit/rag/test_retrieval.py`).
- **`django_db_setup`** override — replicates pytest-django's default fixture but excludes
  the `"postgres"` alias, which `tests/integration/web/conftest.py` owns via an ephemeral
  testcontainers PostGIS instance.
- **`pg_dsn`** / **`pg_pool`** — session-scoped Postgres connection pool for integration
  tests. Reads `BABYLON_TEST_PG_DSN` (defaults to the `mise run db:up` container: port 5433,
  db `babylon_test`, user/password `test`/`test`). `pg_pool` calls `pytest.skip(...)` if the
  database is unreachable — tests depending on it skip cleanly rather than error when
  Postgres isn't running locally.

## Hypothesis profiles

| Profile   | Registered in                 | `max_examples` | `deadline` | Notes |
| --------- | ------------------------------ | --------------- | ---------- | ----- |
| `default` | `tests/conftest.py`             | 100             | `None`     | Active unless `HYPOTHESIS_PROFILE` is set |
| `slow`    | `tests/conftest.py`             | 500             | `None`     | `derandomize=False` |
| `mutmut`  | `tests/conftest.py`             | (Hypothesis default) | — | Suppresses `differing_executors` health check |
| `dev`     | `tests/property/conftest.py`    | 20              | 1000ms     | |
| `ci`      | `tests/property/conftest.py`    | 500             | 5000ms     | Default for `test:rest-ci` (the only shard running `tests/property`) |
| `nightly` | `tests/property/conftest.py`    | 5000            | `None`     | |

Select with `HYPOTHESIS_PROFILE=slow poetry run pytest ...`.

## Pytest markers

Declared in `pyproject.toml` `[tool.pytest.ini_options] markers` with `strict_markers = true`
(an unrecognized marker fails collection):

- `unit` — fast, isolated, no I/O, no AI
- `math` — deterministic mathematical formulas
- `ledger` — economic/political state tests
- `topology` — graph/network operations
- `integration` — database/Postgres tests (I/O bound)
- `ai` — AI/RAG evaluation tests (slow, non-deterministic)
- `red_phase` — intentionally-failing TDD RED phase tests
- `slow` — long-running scenario tests (2000+ ticks, multi-minute runtime)
- `scenario` — full simulation scenario tests (multi-tick arcs)
- `theory_rent`, `theory_rift`, `theory_solidarity`, `theory` — Marxian-theory validation
  domains (imperial rent, metabolic rift, solidarity/consciousness, Capital Vol. II schema)
- `property` — Hypothesis property-based tests
- `empirical` — requires real QCEW data
- `benchmark` — performance/memory benchmarks
- `requires_postgres` — needs a running PostgreSQL instance (skipped if unavailable)
- `postgres` — uses a testcontainers ephemeral PostgreSQL (requires Docker)
- `invariant` — Marx value-form and software metamorphic invariant tests
- `cross_scale` — spec-062 cross-scale integration
- `contract` — contract tests pinning cross-boundary interfaces (`tests/contract/`)
- `requires_reference_db` — needs the reference SQLite DB
  (`data/sqlite/marxist-data-3NF.sqlite`); excluded from the dev CI tier, run on the nightly
  `refdata-tests` job against a pinned ci-data subset artifact

## CI tier model

- **Dev fast lane** (`.github/workflows/ci.yml`, push/PR to `dev` or `main`, ~8-10 min):
  `check:hygiene`, `check:seams`, `check:coverage`, lint, `lint:imports`, format, `typecheck`,
  then `test:unit-ci` and `qa:regression`, plus frontend/security/secret-scan jobs.
  `test:unit-ci` runs `tests/unit` (excluding `tests/unit/ai`) under `xdist -n4`, deselecting
  `red_phase`, `slow`, and `requires_reference_db`, and gates
  `src/babylon/engine/systems` coverage at ≥80%.
- **Main full pipeline** (`.github/workflows/main.yml`, push/PR to `main`): everything the
  fast lane runs, plus `test:rest-ci` (the heavy shard) and a `postgres-integration` job
  running `tests/integration/web/`.
- **Nightly** (`.github/workflows/nightly.yml`, scheduled against `dev` HEAD): daily —
  `test:rest-ci`, security audit, `postgres-integration`
  (`tests/integration/web/`), and `refdata-tests` (`-m requires_reference_db`, excluding
  `tests/integration/web`) against a pinned reference-DB artifact. Weekly (Sunday) — a Python
  3.13 forward-compatibility suite and simulation trace/sweep artifact generation. Mutation
  testing (mutmut) was retired from CI and is local-only; run `tools/run_mutmut.py` directly.

`test:rest-ci` runs everything outside `tests/unit` except `tests/integration/web` (its own
job), deselecting `red_phase` and `requires_reference_db`, then runs the `slow`-marked tests
under `tests/unit` (which `test:unit-ci` excludes) as a second pass — this is the only shard
that runs `tests/property`, defaulting `HYPOTHESIS_PROFILE` to `ci` unless the caller
overrides it.

## Running tests

```bash
mise run test:q -- tests/unit/formulas/       # quiet, scoped — the inner-loop default
mise run test:failed                          # re-run only last test:q's failures
mise run test:unit                            # tests/unit, deselecting red_phase + slow — what `mise run check` runs
mise run qa:regression                        # 5-scenario byte-identical baseline gate
```

`test:unit` (used by `mise run check`) is not identical to CI's `test:unit-ci`: it does not
exclude `tests/unit/ai` or `requires_reference_db`, and carries no coverage gate. To
reproduce the exact CI shards locally, run `mise run test:unit-ci` / `mise run test:rest-ci`
(verbose, JUnit/coverage artifacts under `reports/test-results/`). `mise tasks` lists the
full `test:*` namespace (`test:int`, `test:pg`, `test:scenario`, `test:doctest`, `test:ai`,
`test:cov`, ...).

## References

- **Test constants**: `tests/constants.py` (`TestConstants`, pulled from `GameDefines`)
- **GameDefines (YAML source)**: `src/babylon/data/defines.yaml`
- **Domain factory**: `tests/factories/domain.py` (`DomainFactory`)
- **Fluent assertions**: `tests/assertions.py` (`Assert(...)`)
- **ADR008 (test separation)**: `ai/decisions/ADR008_test_separation.yaml`
- **Hypothesis docs**: https://hypothesis.readthedocs.io/
