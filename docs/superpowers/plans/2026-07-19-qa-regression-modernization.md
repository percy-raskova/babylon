# qa:regression Modernization Implementation Plan

> **For agentic workers:** execute via superpowers:subagent-driven-development, one implementer
> per task. Per the spec's own sequencing warning ("never change the measuring instrument while
> an approval gate is in flight"), this program executes on `refactor/qa-regression-modernization`
> off post-merge `dev` AFTER the current queue PR lands, and BEFORE the parquet Phase 6 cutover —
> so the cutover's gate-3 runs on the modernized instrument, whose county/financial coverage is
> exactly what IMPORT_USE will exercise.

**Goal:** Close the gate-coverage blindness the Vol III program proved (spec
`docs/superpowers/specs/2026-07-19-qa-regression-modernization-design.md`, owner-approved):
declared+sentinel-proven scenario coverage, county-bearing canonical scenarios, financial
dense-trace channels with a no-dead-columns rule, first-divergence attribution, and a gate with
teeth on `defines_hash` + in-gate two-process determinism.

**Architecture:** four phases matching the spec's E-elements, baseline-neutral first
(E1 → E4 → E5-hash → E2+E3+E5-two-process as ONE minting ceremony). Byte-identity (III.7)
untouched throughout. Every phase ships its mutation-validated sentinel (standing rule).

**Tech Stack:** existing `tools/regression_test.py` estate (+ successor module for scenario
declarations), `babylon.sentinels.coverage`, SessionRecorder traces, dense CSV goldens,
frozen Pydantic.

## Global Constraints

- **Byte-identity stays**; no change to III.7 or comparison strictness — coverage and
  observability only.
- **CI never touches the babylon-data drive**: `single_county`'s inputs ship as committed
  deterministic artifacts (D4/ci-data pattern; LFS-pointer traps per test-estate memory).
- The **nationwide** slot is DECLARED but `deferred: owner-tabled 2026-07-15` — reserved in the
  estate declaration, not implemented (un-tabling is the owner's call, then it lands as a final
  phase with its own runtime budget).
- Runtime budget MEASURED: full local `qa:regression` stays < 5 min; two-tier CI envelope
  (Program 15) holds. Measurement is a task deliverable, not an assumption.
- One baseline ceremony total (Phase D), owner-audited; Phases A–C are baseline-neutral except
  C's declared hash-field-only refresh.
- Sentinel-per-error-class, mutation-validated; conventional commits + trailer; single-flight
  heavy runs.

## Phase A — E1: Declared coverage, sentinel-enforced (baseline-neutral)

### Task A1: `ScenarioCoverage` declarations
**Files:** create `tools/regression_estate.py` (the successor module the spec names — scenario
declarations as DATA); modify `tools/regression_test.py` (import + expose the estate); test
`tests/unit/tools/test_regression_estate.py`.
**Interfaces:** frozen Pydantic `ScenarioCoverage(scenario: str, systems: frozenset[str],
layers: frozenset[str], channels_at_rest: dict[str, str])` (channel → reason; the county-free
five declare the financial channels at rest here, with reasons); module-level
`CANONICAL_ESTATE: tuple[ScenarioCoverage, ...]` covering the 5 scenarios + the reserved
`nationwide` entry marked deferred; helper `estate_by_name()`.
**Steps:** red tests (estate completeness: every canonical scenario has a declaration; the
deferred slot present; reasons non-empty) → implement → scoped green → commit
`feat(qa): declared scenario-coverage estate (E1 data layer)`.

### Task A2: coverage-truth sentinel
**Files:** extend `src/babylon/sentinels/coverage/` (new module `gate_estate.py` runs beside
vol3's `check_gate_estate_coverage` — read it first; extend rather than duplicate if it already
half-covers this); CLI stays under the `coverage` family; tests in the coverage sentinel's test
home.
**Checks:** (a) every DECLARED system observably fires in that scenario — proven against the
SessionRecorder trace of a fresh scenario run (dev-box/refdata tier if it needs a run; static
declaration-shape checks stay fast-tier); (b) the UNION of declarations covers all 30
`_DEFAULT_SYSTEMS` + every declared layer — an uncovered system is a loud failure naming the
hole. **Mutation validation:** delete a declaration row → union check fails; declare a system a
scenario never fires → truth check fails. Record both outputs.
**Commit:** `feat(sentinels): gate-estate coverage truth checks (E1), mutation-validated`.

## Phase B — E4: First-divergence attribution (baseline-neutral)

### Task B1: attribution walk + report
**Files:** modify `tools/regression_test.py` (or successor) FAIL path; create
`tools/first_divergence.py` if the walk warrants its own module; tests
`tests/unit/tools/test_first_divergence.py`.
**Interfaces:** `first_divergence(trace, baseline) -> Divergence | None` where frozen
`Divergence(tick: int, system: str | None, channel: str, county: str | None, baseline_value,
actual_value, last_agreeing_tick: int)`; system attribution = the dense-trace column's owning
system per the estate declaration (E1's data — the two phases compose). On FAIL the tool prints
one human line + writes a machine-readable JSON block; `tools/capture_qa_diff.py` (landed with
vol3) consumes it for delta reports.
**Steps:** red tests (synthetic trace pairs: first-divergence identified at exact
tick/channel; equal traces → None; divergence at tick 0; absent-column case) → implement →
green → commit `feat(qa): first-divergence attribution on gate failure (E4)`.

## Phase C — E5a: `defines_hash` grows teeth (declared hash-field refresh)

### Task C1: gate the hash + refresh stale hashes
**Files:** `tools/regression_test.py:919-944` region (WARNING → gating FAIL naming the
regeneration ceremony); the 5 baseline JSONs' `defines_hash` fields; tests.
**Steps:** red test (mismatched hash → exit 1 with ceremony-naming message) → implement →
regenerate the five stale hash FIELDS via `generate_all_baselines` — **verify tick values
byte-identical, only hash lines move** (assert with `git diff` scoped to the hash keys; if any
value moves, STOP — that's an undeclared drift, investigate) → commit as the declared mini-
ceremony `test(baselines): defines_hash refresh — the five stale advisory hashes become gating
(E5a)` with the per-file hash table in the body.

## Phase D — E2+E3+E5b: the minting ceremony (ONE owner-audited commit set)

### Task D1: `single_county` scenario + committed artifact
Wayne-seeded minimal county scenario as a committed deterministic artifact (D4 pattern — the
artifact generation script + hash-pinned inputs; NO drive reads at gate time). Smallest graph
where the Vol III financial layer, MELT, and `s = p + i + r + t` all fire. Tick count chosen by
measurement to keep local qa:regression < 5 min. Coverage declaration added (financial channels
NOT at rest — that is the point).

### Task D2: `detroit_tri_county` promotion
From Δ%-summary (`qa:e2e-regression`) to full byte-identical dense-trace membership; its
coverage declaration; keep the e2e Δ% tool as-is for its other users or retire it into the gate
(implementer proposes based on remaining consumers — decision recorded in the PR, not silently).

### Task D3: E3 financial channels + no-dead-columns rule
Dense traces gain: endogenous rate, `profit_rate_ceiling`, `s_r`, τ, county
`interest_payments`, `p`/`i`/`r_rent`/`t`, serviceability inputs. Gate rule: an all-zeros/
all-absent channel across a run FAILS unless the scenario's declaration marks it `at_rest`
with a reason. Mutation validation: zero out a live channel in a synthetic trace → gate names
it.

### Task D4: E5b two-process leg + ceremony
Fold the U7.0 two-process byte-comparison into `qa:regression` as a per-run leg (one scenario;
unit test stays as the fast-tier mirror). Then THE ceremony: mint `single_county` +
`detroit_tri_county` baselines + widened dense traces for all, one
`test(baselines):` commit with the full per-scenario table (what was minted, what widened, what
went at-rest where), owner audits in the PR. Wall-clock measured and recorded vs the < 5 min
budget; if busted, tick counts shrink BEFORE the ceremony, never after.

## Verification

- Per-phase: scoped suites + `mise run check`; Phases A/B/C leave `qa:regression` 5/5
  byte-identical (C moves only hash fields, proven by scoped diff).
- Phase D: the ceremony commit is the expected change; after it, `qa:regression` green on the
  NEW estate (7 scenarios incl. two county-bearing) + two-process leg green + all sentinels
  green.
- Final: honest PR body with the coverage-before/after table; the parquet Phase 6 cutover then
  runs against THIS gate.

## Explicitly out of scope
Nationwide implementation (owner-tabled #49); employment-100k + Wayne `capital_stock=0`
disclosed inputs (E3 will show them at-rest, which is the honest state); mutation testing in
CI; any III.7 change.
