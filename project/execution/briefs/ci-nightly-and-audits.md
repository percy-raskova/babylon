# Phase 3.2 `ci/nightly-and-audits` — implementation brief (scouted 2026-07-08, dev @ 3371dc8c)

Everything below was verified against the live tree with real line numbers. Repo root: `/home/user/projects/game/babylon`.

## Ground truth that reshapes the plan

1. **The tick_commit hash chain CANNOT be the A/B comparator.** The runner's per-tick `determinism_hash` is `sha256(f"{session_id}:{tick}:{config.random_seed}")` — `src/babylon/engine/headless_runner/runner.py:1313-1315` (tick 0: `:1287-1289`). It is a session-scoped spine hash (documented as such in `0029_tick_commit.sql:9-10` and observation 41189), NOT state-dependent, and session_id differs per run. The state-dependent hash, `compute_determinism_hash` (`src/babylon/persistence/conservation_audit.py:70-111`, hashes sorted hex rows + actions + seed), is consumed only inside `ConservationAuditor` (`conservation_audit.py:340`) and lands in `conservation_audit_log` rows, not in a comparable cross-run stream keyed without session_id.
2. **The valid cross-run comparator already exists: the artifact bundle.** trace.csv's 22 columns (`trace_emitter.py:31-54`) contain no session_id and no timestamps; `manifest.py:325-329` states the contract explicitly: *"Two runs with identical input_hash MUST produce byte-identical trace.csv and summary.json (modulo wallclock fields)"*. The spec-069 quickstart already blesses `diff -q run1/trace.csv run2/trace.csv` (`tests/integration/engine/headless_runner/test_cache_byte_identical_trace.py:9-13`). summary.json's volatile keys across two same-seed runs are exactly: `run_metadata.session_id`, `run_metadata.wallclock_start`, `run_metadata.wallclock_end`, and the whole `performance` block (`run_summary.py:75-95`); everything else (`terminal_state`, `external_node_flows`, `county_terminal_snapshot`, `conservation_audit`) must be equal.
3. **GitHub Actions cannot run the headless runner.** It needs (a) Postgres via `BABYLON_PG_DSN`/`BABYLON_TEST_PG_DSN` (`runner.py:243-247`) — CI could compose that (`docker compose up -d --wait babylon-pg`, port 5433, service in `docker-compose.yml:18-22`, already done by the C.4/C.5 jobs at `ci.yml:324-325,396-397`) — but also (b) the 6.08 GB reference SQLite (`data/sqlite` is a symlink to `/media/user/data/babylon-data/sqlite/`; `ls -laL` shows `marxist-data-3NF.sqlite` = 6,077,046,784 bytes). `initialize_session` (`postgres_initialization.py:601-616`) hex-hydrates from `dim_county_geometry` (`hex_hydrator.py:518`) and the runner hard-fails on zero hex rows (`runner.py:972-975`). The test fixture `build_test_sqlite` (`tests/unit/engine/headless_runner/conftest.py:76-106`) only builds `fact_census_income` + `fact_qcew_annual` — insufficient. **Decision: split by data gravity — a new GitHub `nightly.yml` for portable legs (deptry, doc-refs, Hypothesis-slow property run, C.2(a) re-run), and a local `qa:nightly` mise task for the DB-bound legs (A/B, tick-budget, storage-budget).**
4. `tools/determinism_check.py` referenced by REMEDIATION_PLAN.md:85 **does not exist** (verified: no hit under tools/). It must be created.
5. The C.2(a) in-process gate is already merged: `tests/unit/engine/test_determinism_ab.py` (commit 810eb10e), 10-tick two-run event-hash + final-state equality on the imperial-circuit scenario.

---

## (a) C.2(b) — full headless A/B nightly

### New file `tools/determinism_check.py` (~150 LOC, stdlib + subprocess)

Follow the house tool style (argparse `main()`, exit 0/1, docstring header like `tick_budget_check.py:1-17`). Keep the comparison logic PURE for unit testing (precedent: `tools/storage_budget.py` whose pure halves are tested in `tests/unit/tools/test_storage_budget.py`).

```python
"""Full headless determinism A/B gate (C.2(b), Constitution III.7).

Runs the bridged headless runner TWICE with identical seed/scope/ticks and
asserts artifact equivalence: byte-identical trace.csv, summary.json equality
modulo the declared wallclock fields (manifest.py "input_hash" contract).
Compares run-vs-run, never run-vs-committed-baseline, so it stays valid
across baseline regens (2.R).

Usage:
    poetry run python tools/determinism_check.py [--scope S] [--ticks N] [--seed N]
"""
from __future__ import annotations

import argparse, hashlib, json, subprocess, sys, tempfile
from pathlib import Path
from typing import Any

_RUNS = 2  # fixed upper bound
#: summary.json keys legitimately different between two runs
#: (run_summary.py:75-95 — session_id + wallclock + performance).
_VOLATILE_RUN_METADATA = frozenset({"session_id", "wallclock_start", "wallclock_end"})
_VOLATILE_TOP_LEVEL = frozenset({"performance"})


def _sha256_file(path: Path) -> str: ...          # mirror manifest.py:335-341

def _stable_summary(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    for key in _VOLATILE_TOP_LEVEL:
        payload.pop(key, None)
    meta = payload.get("run_metadata", {})
    for key in _VOLATILE_RUN_METADATA:
        meta.pop(key, None)
    return payload


def compare_bundles(dir_a: Path, dir_b: Path) -> list[str]:
    """Pure comparison — returns human-readable divergence list (empty = pass)."""
    failures: list[str] = []
    if _sha256_file(dir_a / "trace.csv") != _sha256_file(dir_b / "trace.csv"):
        failures.append("trace.csv sha256 divergence")
    if _stable_summary(dir_a / "summary.json") != _stable_summary(dir_b / "summary.json"):
        failures.append("summary.json divergence (wallclock fields excluded)")
    return failures


def _run_once(*, scope: str, ticks: int, seed: int, out: Path) -> None:
    cmd = [sys.executable, "-m", "babylon.engine.headless_runner",
           "--scope", scope, "--ticks", str(ticks), "--seed", str(seed),
           "--output-dir", str(out)]
    proc = subprocess.run(cmd, check=False)   # streams runner stderr through
    if proc.returncode != 0:
        raise RuntimeError(f"headless run exited {proc.returncode}: {' '.join(cmd)}")
```

`main()` runs both into `tempfile.TemporaryDirectory()` subdirs `run-a/`/`run-b/` (or `--keep-artifacts DIR` for debugging), prints the divergence list, exits 1 on any. Defaults: `--scope michigan-statewide-no-canada --ticks 104 --seed 2010`. Rationale for 104 (2 sim-years): michigan 5-tick median is ~2,040 ms/tick (REMEDIATION_PLAN.md:237), so 2×104 ticks ≈ ~7 min — nightly-friendly; the full 520-tick A/B stays available via `--ticks 520` for pre-2.R proof runs. Do NOT pass `--strict` (a conservation alarm is a different gate; also 3.1's hydration-strict policy will make `--strict` fail loud on fabricated constants). Note: each invocation writes 2 new sessions to babylon_test (~100 MB/run post-spec-089) — the task should end with a reminder line to run `mise run sim:archive -- archive --all` periodically.

Optional third comparator (cheap, catches persistence-layer divergence trace.csv might miss): after each run, read back per-tick `compute_determinism_hash`-based audit rows — SKIP for v1; trace.csv + summary already cover graph state (trace rows come from the as-of SQL view over persisted hex/county state).

### TDD (new `tests/unit/tools/test_determinism_check.py`)

House import pattern from `tests/unit/tools/test_storage_budget.py:15-18`:
```python
TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))
import determinism_check  # type: ignore[import-not-found]  # noqa: E402
```
RED cases (pure, tmp_path fixtures — write tiny trace.csv/summary.json pairs):
- identical bundles → `compare_bundles` returns `[]`
- one CSV byte flipped → `["trace.csv sha256 divergence"]`
- summary differing ONLY in `session_id`/`wallclock_*`/`performance` → passes
- summary differing in `terminal_state.total_v` → fails
Scoped run: `poetry run pytest tests/unit/tools/test_determinism_check.py -q` (or `mise run test:q -- tests/unit/tools/test_determinism_check.py`).

### `.mise.toml` — `[tasks."qa:nightly"]` (insert after `qa:tick-budget`, line 781)

```toml
[tasks."qa:nightly"]
description = "Local nightly gate battery: determinism A/B + tick/storage budgets + slow Hypothesis (needs PG 5433 + the 6 GB reference SQLite — dev box only)"
run = """
set -e
export BABYLON_PG_DSN=${BABYLON_PG_DSN:-dbname=babylon_test host=localhost port=5433 user=test password=test}
echo '=== C.2(b) determinism A/B (2x headless, run-vs-run) ==='
poetry run python tools/determinism_check.py --scope michigan-statewide-no-canada --ticks 104
echo '=== C.12 tick budget (michigan 5-tick vs ratified budget.json) ==='
mise run qa:tick-budget
echo '=== C.12 wayne 3-tick budget smoke ==='
poetry run python tools/tick_budget_check.py --ticks 3 --fips 26163 --budget specs/104-national-tick-compute/budget-wayne-smoke.json
echo '=== spec-087 storage budget ==='
mise run qa:storage-budget
echo '=== Hypothesis nightly profile (property suite) ==='
HYPOTHESIS_PROFILE=nightly poetry run pytest tests/property -m "not red_phase" -q --tb=short
echo '=== C.10 deptry ==='
poetry run deptry src tools web
echo '=== C.11 doc refs ==='
poetry run python tools/check_doc_refs.py
echo 'qa:nightly complete. Consider: mise run sim:archive -- archive --all'
"""
```
The DSN-default idiom copies `qa:tick-budget` (`.mise.toml:781`). Scheduling on the dev box is a systemd user timer / cron line invoking `mise run qa:nightly` — document it in the task description or `project/` notes; do not attempt GitHub scheduling for this half.

---

## (b) C.10 — deptry

### Current state (verified by execution today)

- `deptry = "^0.25.1"` already in dev deps (`pyproject.toml:107`). No `[tool.deptry]` section exists (checked full `[tool.*]` list, `pyproject.toml:1-463`).
- `poetry run deptry .` from repo root → **1,626 issues** (1,538 DEP003 — mostly first-party `babylon` misclassified when scanning tests/, plus `game`/`babylon_web`/`shared` DEP001). Bare-root invocation is unusable.
- `poetry run deptry src tools web` → **exactly the review's 38 issues** (multi-root invocation makes tools/ and web/ source roots, so `shared`, `game`, `babylon_web` resolve as local). Full captured list:
  - **DEP002 (16 unused main deps)**: tokenizers, typer, coloredlogs, pyproj, requests, certifi, filelock, rstcheck, doc8, polars, boto3, pgvector, ansible-dev-tools, django-cors-headers, gunicorn, sentence-transformers
  - **DEP005 (1)**: `uuid` (stdlib — just delete from `[tool.poetry.dependencies]`; safe, do it in this branch as its own commit)
  - **DEP004 (dev-dep leaks into tools/, 12 hits)**: optuna (`tools/tune_agent.py:35,43,44`), SALib (`tools/sensitivity_analysis.py:59-62`), midiutil (5 files under tools/), markdownify (`tools/ingest_corpus.py:155`), pytest (`web/game/tests/conftest.py:9`)
  - **DEP003 (transitive imports, 9 hits)**: matplotlib (`tools/analyze_wealth_distribution.py:319`), networkx (`tools/benchmarks/graph_backend_bench.py:23`), httpx (`tools/ingest_lodes_od.py:22`), tomli/tomli_w (`tools/run_mutmut.py:21-27`)

### `pyproject.toml` addition (place after `[tool.pydantic-mypy]` at :311)

```toml
[tool.deptry]
# Gate scope is `deptry src tools web` (see qa:deps / ci.yml). tests/ excluded:
# pytest fixtures import dev deps by design.
extend_exclude = ["tests", "mutants", "specs", "docs", "examples", "assets"]

[tool.deptry.per_rule_ignores]
# Frozen 2026-07-08 inventory (38 issues) — RATCHET: new issues fail CI,
# existing ones burn down via the deps-cleanup follow-up + Phase 7.
DEP002 = ["tokenizers", "typer", "coloredlogs", "pyproj", "requests", "certifi",
          "filelock", "rstcheck", "doc8", "polars", "boto3", "pgvector",
          "ansible-dev-tools", "django-cors-headers", "gunicorn", "sentence-transformers"]
DEP003 = ["matplotlib", "networkx", "httpx", "tomli", "tomli_w"]
DEP004 = ["optuna", "SALib", "midiutil", "markdownify", "pytest"]
```
(No DEP005 entry — remove the `uuid` dep instead: one line out of `[tool.poetry.dependencies]` + `poetry lock --no-update`.) Verify each ignore key against deptry 0.25 docs at land time; run `poetry run deptry src tools web` → must exit 0 after config.

### Wiring

- **`qa:deps`** (`.mise.toml:602-615`): insert before the vulture block:
  ```
  echo "=== deptry (manifest drift, gate) ==="
  poetry run deptry src tools web
  ```
  Note the task's `|| true` style on other legs — deptry must NOT get `|| true` (it's the gate).
- **`ci.yml`**: add one step to the main `ci` job after "Type check with MyPy" (`ci.yml:55-56`):
  ```yaml
      - name: Dependency audit (deptry)
        run: poetry run deptry src tools web
  ```
  Fast (~seconds), no PG, no extra install (dev group already installed by `poetry install`).

---

## (c) C.11 — `tools/check_doc_refs.py`

### Verified current violations

A prototype with the exact heuristics below found **768 refs checked, 169 unique missing** across `CLAUDE.md` + `ai/*.yaml` + `project/README.md`. Distribution: `ai/state.yaml` 67, `ai/entities.yaml` 23, `ai/architecture.yaml` 11, `project/README.md` 9, `CLAUDE.md` 6, theory/persistence-spec/game-loop-architecture 5 each, long tail across ~20 more yamls. Genuine rot it catches on day one:
- `CLAUDE.md:297` → `src/babylon/engine/simulation.py` (now the `simulation/` package)
- `CLAUDE.md:804` → `ai/decisions.yaml` (now the `ai/decisions/` directory); `CLAUDE.md:810` → `ai/roadmap.md` (gone)
- `project/README.md:71-75` → `project/POST_ASSESSMENT.md`, `project/HOLISTIC_REVIEW-2026-07-07.md`, `project/REMEDIATION_PLAN.md`, `project/_PROGRESS.md`, `project/_HANDOFF.md`, `project/c17-test-migration-ledger.md`, `project/owner-queue.md` — all stale since the assessments/execution/owner reorg (the actual files live in subdirs). **Fix these 9 in this branch** (tiny, unambiguous); the ai mass belongs to Phase 7 (state.yaml is regenerated wholesale there).
- False-positive classes that need policy: placeholder examples (`tests/unit/foo.py` CLAUDE.md:125, `tests/unit/test_foo.py` :213), runtime artifact dirs (`reports/test-results/...`), pattern-refs (`project/NN`, `project/programs/NN`).

### Design (stdlib only: `re`, `sys`, `argparse`, `pathlib`)

```python
_ROOTS = r"(?:src|tests|tools|web|ai|project|specs|docs|data|reports|assets|contracts)"
PATH_RE = re.compile(rf"(?<![\w./-])({_ROOTS}/[A-Za-z0-9_.\-/]+[A-Za-z0-9_])")
PLACEHOLDER_RE = re.compile(r"(?:^|/)(?:foo|bar|baz|example|NN)(?:[_./]|$)", re.IGNORECASE)
SKIP_SUBSTRINGS = ("*", "<", ">", "{", "}", "$")
SKIP_PREFIXES = ("reports/test-results", "reports/sim-runs", "results/")
TARGETS = ["CLAUDE.md", "project/README.md", *sorted(Path("ai").glob("*.yaml"))]
```
- Strip trailing `.,:;)` from tokens; dirs count as existing (`(repo / tok).exists()`).
- **Allowlist ratchet**: `tools/doc_ref_allowlist.txt`, one `doc-path:ref-path` per line, `#` comments. Seed it from the first run's output (169 minus the 9 project/README fixes minus placeholder-skips). New violations (not in allowlist) → exit 1; allowlist entries whose ref now EXISTS → print "stale allowlist entry" warning (exit 0) so Phase 7 burn-down is visible. `--update-allowlist` regenerates the file (developer convenience; never run in CI).
- Anchor repo root via `Path(__file__).resolve().parents[1]` — no sys.path surgery needed (no babylon imports; this also sidesteps the ADR036 `shared.py` question — stdlib-only is exempt, matching `check_doc_refs`'s zero-dependency mandate).

### TDD (`tests/unit/tools/test_check_doc_refs.py`)

Pure-function tests on tmp_path trees: extraction (backticked, prose, yaml-value paths), placeholder skip, `SKIP_PREFIXES`, trailing-punctuation strip, allowlist hit/miss/stale, exit-code contract. Then one repo-truth test: running against the real repo with the committed allowlist exits 0 (this is the gate proving the allowlist is in sync). `poetry run pytest tests/unit/tools/test_check_doc_refs.py -q`.

### Wiring

- **pre-commit** (append to the `repo: local` frontend block region of `.pre-commit-config.yaml`, after :162):
  ```yaml
      - id: doc-refs
        name: doc refs (paths in CLAUDE.md / ai / project README exist)
        entry: poetry run python tools/check_doc_refs.py
        language: system
        pass_filenames: false
        files: ^(CLAUDE\.md|ai/[^/]+\.ya?ml|project/README\.md|tools/(check_doc_refs\.py|doc_ref_allowlist\.txt))$
  ```
- **ci.yml**: one step in the main `ci` job next to the deptry step: `poetry run python tools/check_doc_refs.py`.

---

## (d) C.12 — budget gates

### The checker today

`tools/tick_budget_check.py` (119 LOC): `check_budget(ticks, budget_path, scope)` at :39-96 **mixes the simulation run and the comparison** — untestable as-is (confirmed zero coverage; HOLISTIC_REVIEW:981-982). `qa:tick-budget` exists (`.mise.toml:779-781`, michigan-statewide 5-tick, DSN default `port=5433 user=test password=test`) but is wired into NO CI/nightly anywhere. `budget.json` (`specs/104-national-tick-compute/budget.json`) is michigan-scoped 5-tick cumulative-ms ceilings, 2× measured (`_scope`/`_ticks` metadata keys at :3-4 — note `budget.get(sys_name)` never collides because system class names never start with `_`).

### Refactor for testability (surgical, same file)

Extract the pure core between :76-89 into:
```python
class BudgetRow(NamedTuple):
    system: str
    total_ms: float
    ms_per_tick: float
    budget_ms: float | None   # None → not budgeted (N/A)
    passed: bool | None       # None when budget_ms is None


def evaluate_budget(
    per_system_ms: Mapping[str, float],
    budget: Mapping[str, float],
    ticks_completed: int,
) -> tuple[bool, list[BudgetRow]]:
    """Compare measured per-system ms against ceilings. Pure; no I/O."""
    ticks = max(ticks_completed, 1)
    rows = [...]   # sorted by total_ms desc, exactly today's :77-89 semantics
    return all(r.passed is not False for r in rows), rows
```
`check_budget` keeps the run + printing, calls `evaluate_budget`. Preserve current behaviors as pinned test cases: missing budget file → warn + empty budget (:69-72, never fails), unbudgeted system → N/A not fail (:87-88), `max(ticks_completed, 1)` floor (:62). Add a `--fips` passthrough mirroring the runner's own branch (`runner.py:183-192` — 5-digit validation, `scope_name="custom"`); `SimulationRunConfig` gains nothing (it already takes `scope_name`/`scope_fips` — see `tick_budget_check.py:50-56`).

### TDD (`tests/unit/tools/test_tick_budget_check.py`)

House pattern from `test_storage_budget.py:15-18` (sys.path insert + `import tick_budget_check`). Cases: within-budget pass; single over-budget FAIL flips return; unbudgeted N/A; empty budget passes; ticks floor; `_`-prefixed metadata keys ignored (they're simply never looked up); row ordering. `poetry run pytest tests/unit/tools/test_tick_budget_check.py -q`.

### What needs Postgres (explicit answer to the ask)

EVERYTHING that invokes `headless_run` needs (1) live PG at `BABYLON_PG_DSN` (`runner.py:243-247`) AND (2) the 6.08 GB reference SQLite (hex hydration reads `dim_county_geometry`, `hex_hydrator.py:518`; zero hex rows aborts, `runner.py:972-975`). So:
- **CI-light (GitHub)** = the checker's UNIT tests only (they run in the normal unit leg — free). Do not attempt the wayne run in GitHub; `build_test_sqlite` lacks geometry tables and extending it is real scope creep (flag as optional follow-up, not this branch).
- **Wayne 3-tick smoke** = LOCAL, inside `qa:nightly` (sketch above): `tick_budget_check.py --ticks 3 --fips 26163 --budget specs/104-national-tick-compute/budget-wayne-smoke.json`. Create `budget-wayne-smoke.json` by measuring once (`--budget` pointing at a nonexistent path prints measured values without enforcement — existing :69-72 behavior), then ratify 2× measured, same `_comment/_scope/_ticks` convention as budget.json. Keep unit tests fixture-driven (never assert against committed budget.json values — it gets re-ratified national at 2.R/6.6).

---

## (e) HYPOTHESIS_PROFILE — nightly slow leg

### Verified bug: `HYPOTHESIS_PROFILE=nightly` crashes TODAY

Reproduced live: `HYPOTHESIS_PROFILE=nightly poetry run pytest tests/property/... --collect-only` → `hypothesis.errors.InvalidArgument: Profile 'nightly' is not registered`. Cause: root `tests/conftest.py:70` calls `settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "default"))` at root-conftest import, but `nightly` (max_examples=5000, deadline=None) and `ci` (500) are registered in `tests/property/conftest.py:20-38`, which imports LATER. Only `mutmut`/`default`/`slow` (root conftest :45-67) work. `slow` = max_examples=500, derandomize=False.

### Fix (in this branch)

Move the `ci` and `nightly` `settings.register_profile(...)` blocks from `tests/property/conftest.py:20-38` into `tests/conftest.py` immediately after the `slow` registration (:61-67), before `load_profile` (:70); leave `dev` where it is or move it too (mechanical). Note `[tool.hypothesis]` in `pyproject.toml:427-429` (deadline=500, max_examples=100) is overridden by any loaded profile — no change needed. TDD: `tests/unit/test_hypothesis_profiles.py` asserting `settings.get_profile("nightly").max_examples == 5000` and `get_profile("slow").derandomize is False` after `import tests.conftest`-time registration (simplest: the assertions run in-suite, where root conftest has already executed). RED first by writing the test before moving the blocks.

### Wiring

- Local: the `qa:nightly` leg (above) uses `HYPOTHESIS_PROFILE=nightly` on `tests/property` (43 files carry `@given`).
- GitHub: new **`.github/workflows/nightly.yml`** (portable legs only):
```yaml
name: Nightly Audits
on:
  schedule:
    - cron: "0 7 * * *"   # 07:00 UTC nightly
  workflow_dispatch:
jobs:
  property-slow:
    name: Hypothesis non-derandomized property sweep
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with: {python-version: "3.12"}
      - uses: snok/install-poetry@v1
        with: {version: "1.8.4", virtualenvs-create: true, virtualenvs-in-project: true}
      - uses: actions/cache@v5
        with: {path: .venv, key: venv-${{ runner.os }}-${{ hashFiles('**/poetry.lock') }}}
      - run: poetry install --no-interaction
      - name: Property tests (slow profile, new examples every night)
        env: {HYPOTHESIS_PROFILE: slow}
        run: poetry run pytest tests/property -m "not red_phase" -q --tb=short
      - name: In-process determinism A/B (C.2(a) re-run)
        run: poetry run pytest tests/unit/engine/test_determinism_ab.py -q
  audits:
    name: deptry + doc refs
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with: {python-version: "3.12"}
      - uses: snok/install-poetry@v1
        with: {version: "1.8.4", virtualenvs-create: true, virtualenvs-in-project: true}
      - uses: actions/cache@v5
        with: {path: .venv, key: venv-${{ runner.os }}-${{ hashFiles('**/poetry.lock') }}}
      - run: poetry install --no-interaction
      - run: poetry run deptry src tools web
      - run: poetry run python tools/check_doc_refs.py
```
Use `slow` (500 ex) in GitHub for wall-time; reserve `nightly` (5000 ex) for the local box. `extended-analysis.yml` (weekly Sunday cron, :10-11) stays untouched — don't overload it; its `parameter-analysis` job is legacy and unverified.

---

## (f) Secret scanning — recommendation: **gitleaks** (not detect-secrets)

### Incident context

Task list #22: "rotate leaked Cloudflare token + choose push-unblock path" — the token is in git HISTORY (hence push-unblock), not the working tree. `sessions/session-ses_0d18.md` is tracked and already redacted (scanned: no token-shaped strings). Known-public creds that must NOT fire: `POSTGRES_PASSWORD: test` (`docker-compose.yml:25`, `ci.yml:333,406,418,436`), the DSN literal in `.mise.toml:781` and in the new qa:nightly task. No gitleaks/detect-secrets config exists anywhere today (verified).

### Why gitleaks over detect-secrets for THIS repo

1. **False-positive economics**: detect-secrets' KeywordDetector fires on any `password`-keyword assignment — every `POSTGRES_PASSWORD: test` and `password=test` DSN would enter `.secrets.baseline`, and the baseline pins line numbers that churn on every edit of ci.yml/.mise.toml (both actively edited by this very branch and by in-flight tasks #26/#27). gitleaks' default rules are entropy/pattern-gated — the literal `test` cannot trip them; the allowlist below is documentation, not necessity.
2. **The incident class**: gitleaks ships a dedicated `cloudflare-api-key`/`cloudflare-global-api-key` ruleset — exactly what leaked.
3. **Toolchain fit**: single static binary installable through the repo's existing mise `[tools]` block (`.mise.toml:17-19`); no Go build in pre-commit, no Python dep added to the already-drifting manifest (see C.10).
4. **History scanning**: `gitleaks git` scans full history natively with `.gitleaksignore` fingerprints — needed because the leaked token IS in history and would otherwise fail every CI run.

### Exact blocks

`.mise.toml:17-19` `[tools]`:
```toml
[tools]
python = "3.12"
poetry = "latest"
gitleaks = "latest"   # secret scanning (post-incident 2026-07); pin after first install
```

`.pre-commit-config.yaml` — append a new section after GENERAL HYGIENE (:189):
```yaml
  # ==========================================================================
  # SECRET SCANNING - gitleaks (added after the 2026-07 leaked-token incident)
  # ==========================================================================
  - repo: local
    hooks:
      - id: gitleaks
        name: gitleaks (staged secret scan)
        entry: gitleaks git --pre-commit --staged --redact --verbose
        language: system
        pass_filenames: false
```
(`language: system` + mise-provisioned binary avoids pre-commit's golang toolchain build; the alternative `repo: https://github.com/gitleaks/gitleaks` pinned-rev hook is acceptable if the implementer prefers remote-repo symmetry — verify the current v8.x rev and that pre-commit's Go auto-provisioning works on the dev box before choosing it.)

New `.gitleaks.toml` at repo root:
```toml
title = "babylon gitleaks config"

[extend]
useDefault = true

[allowlist]
description = "Known-public dev defaults (compose test creds) and committed fixtures"
regexes = [
  '''POSTGRES_PASSWORD[:=]\s*"?test"?''',
  '''password=test\b''',
]
paths = [
  '''tests/baselines/.*\.json''',
]
```
Deliberately do NOT allowlist `sessions/` — it is redacted and should stay scanned so a future unredacted paste gets caught.

New `.gitleaksignore`: run `gitleaks git --redact` once locally over full history; it will fire on the historical Cloudflare token — copy each finding's `Fingerprint:` line in. **Sequencing dependency: land this AFTER (or simultaneously with) the owner's rotation ruling (#22)** — fingerprinting an un-rotated live token would normalize it; the hook itself can land immediately (it only scans staged changes).

`ci.yml` — new job:
```yaml
  secrets:
    name: Secret Scan (gitleaks)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0   # full history scan
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```
(gitleaks-action is license-free for personal accounts — `percy-raskova` origin is a user account; if that ever changes, swap to a plain `mise`/binary-download step running `gitleaks git --redact`.)

---

## Rollout order (each its own conventional commit via `mise run commit`)

1. `feat(tools): C.11 doc-ref linter + allowlist + project/README path fixes` — zero deps, immediately green; includes the 9 README fixes + pre-commit + ci.yml step + tests.
2. `fix(tests): hoist Hypothesis ci/nightly profiles to root conftest` — fixes the verified `HYPOTHESIS_PROFILE=nightly` crash; test first (RED).
3. `chore(deps): remove stdlib uuid dep` then `feat(ci): C.10 deptry gate with frozen per-rule ignores` (pyproject `[tool.deptry]` + qa:deps + ci.yml step).
4. `refactor(tools): extract evaluate_budget + --fips in tick_budget_check` + `test(tools): C.12 budget-checker unit tests` (RED→GREEN).
5. `feat(tools): C.2(b) determinism_check A/B` + `test(tools)` (pure comparator TDD) — measure once, then `feat(mise): qa:nightly battery` + `budget-wayne-smoke.json` ratification.
6. `feat(ci): nightly.yml portable legs` (property-slow, C.2(a) re-run, deptry, doc-refs).
7. `feat(security): gitleaks hook + config + CI job` — LAST, coordinated with owner task #22 for the `.gitleaksignore` fingerprints.

Merge-ready check per repo law: `mise run check` green + the scoped commands above. New files: `tools/determinism_check.py`, `tools/check_doc_refs.py`, `tools/doc_ref_allowlist.txt`, `specs/104-national-tick-compute/budget-wayne-smoke.json`, `.gitleaks.toml`, `.gitleaksignore`, `.github/workflows/nightly.yml`, `tests/unit/tools/test_determinism_check.py`, `tests/unit/tools/test_check_doc_refs.py`, `tests/unit/tools/test_tick_budget_check.py`, `tests/unit/test_hypothesis_profiles.py`. Edited: `pyproject.toml` (deptry config, uuid removal), `.mise.toml` (qa:deps, qa:nightly, [tools]), `.pre-commit-config.yaml` (doc-refs, gitleaks), `.github/workflows/ci.yml` (deptry + doc-refs steps, secrets job), `tests/conftest.py` + `tests/property/conftest.py` (profile hoist), `tools/tick_budget_check.py` (evaluate_budget + --fips), `project/README.md` (9 path fixes).

## Style constraints (repo law)

Frozen-Pydantic/NamedTuple for any structured data in tools; mypy strict does NOT cover `tools/` (pre-commit mypy excludes `^tools/`, `.pre-commit-config.yaml:58`) but write to strict standard anyway; ruff enforces `zip(strict=)` B905 and C90 complexity ≤15 on src only — tools/ still passes `ruff check .` in CI (`ci.yml:53` runs repo-wide); all loops bounded (`_RUNS = 2`, `range` over finite target lists); RST docstrings on all public functions; no bare `except Exception`.

## Drift alerts (scout-verified deviations from the plan)

- C.2(b) plan assumption is wrong in a load-bearing way: the tick_commit hash chain (migration 0029) stores sha256(session_id:tick:seed) — runner.py:1313-1315 — a session-scoped spine hash, NOT a state hash. It cannot detect cross-run divergence. The valid comparator is the artifact bundle (byte-identical trace.csv + summary.json modulo session_id/wallclock/performance, per manifest.py:325-329). Any implementation that diffs tick_commit rows across two runs would be a green-forever no-op gate.
- tools/determinism_check.py named in REMEDIATION_PLAN.md:85 does not exist anywhere in the tree — it must be created from scratch, not extended.
- GitHub-Actions-scheduled full A/B and the wayne budget smoke are both infeasible in hosted CI: the headless runner requires the 6.08 GB reference SQLite (data/sqlite is a dev-box symlink to /media/user/data/babylon-data/sqlite) for hex hydration (hex_hydrator.py:518 reads dim_county_geometry; runner.py:972-975 aborts on zero hex rows). The brief splits nightly into GitHub nightly.yml (portable legs) + local qa:nightly (DB-bound legs).
- HYPOTHESIS_PROFILE=nightly crashes TODAY (reproduced live: InvalidArgument 'Profile nightly is not registered') because tests/property/conftest.py:20-38 registers ci/nightly AFTER root tests/conftest.py:70 calls load_profile. The nightly leg cannot ship without hoisting those registrations to the root conftest.
- deptry issue count depends entirely on invocation: bare `deptry .` = 1,626 issues (first-party misclassification noise from tests/); `deptry src tools web` = exactly the review's 38. The gate must standardize on the scoped invocation or the [tool.deptry] config; there is no [tool.deptry] section today.
- .mise.toml collision risk with in-flight work: tasks #26 (storage-budget floors) and #27 (session-scope sim:status) are actively editing .mise.toml and tools/storage_budget.py in another lane. The qa:nightly insertion point (after line 781) and any qa:storage-budget invocation should be re-verified against the tree at implementation time, not against this scout snapshot.
- In-flight verb-dispatch lane (engine_bridge.py + ooda, task #14): no direct file overlap with 3.2's file set, BUT 2.2/2.3/2.R and any future NPC-through-resolvers routing are baseline-affecting — determinism_check MUST compare run-vs-run (self-consistent), never run-vs-committed-baseline, to stay decoupled from the 2.R regen. The brief's design already does this; do not 'improve' it into a baseline comparison.
- budget.json will be re-ratified at national scope in 6.6 (current file is the michigan 5-tick proxy, budget.json:2-4). C.12 unit tests must be fixture-driven and never pin committed budget.json values.
- Secret-scanning sequencing: the leaked Cloudflare token lives in git HISTORY (owner task #22 'push-unblock'), so the CI full-history gitleaks job will fail until the finding is fingerprinted in .gitleaksignore — and fingerprinting should follow rotation, not precede it. The pre-commit staged-only hook has no such dependency and can land first.
- project/README.md itself carries 9 broken path refs (lines 71-75, stale since the assessments/execution/owner reorg) — the C.11 gate would fail on its own documentation set on day one unless these are fixed in the same branch (they are one-line fixes; the brief includes them).
