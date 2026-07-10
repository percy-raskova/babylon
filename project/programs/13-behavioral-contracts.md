# Program 13 — Behavioral Contracts (Durable Spec hardening)

**Ratified:** 2026-07-09 (Percy: "update project/ and CONSTITUTION.md and everything else
with the plan which I read over and approve").
**Constitutional anchor:** Amendment Q (v2.9.0) — III.12 Behavioral Contracts +
VIII.13 Spec Trapped in Implementation.
**Evidence base:** `project/assessments/TEST_SUITE_REWRITE_AUDIT-2026-07-09.md`.
**Status:** ✅ **COMPLETE 2026-07-09 (same day as ratification).** Item 1 `66125a22`
(determinism-contract.rst, hand-computation gate satisfied); item 2 `60a919e3` (dense
per-tick goldens for all 5 scenarios, byte-compared in qa:regression by default, shared
tick-loop core so wall time is unchanged, double-generation determinism proof, synthetic
1-value mutation caught with tick+column named); item 3 is standing law (III.12).
Constitution marker flipped to `[IMPLEMENTED]` in v2.9.1.

## Premise

Code is a materialized view of understanding — cheap to regenerate, risky to mutate
(Majors). The durable assets are whatever would let us validate a regeneration: the
rewrite test. The 2026-07-09 audit found Babylon unusually well-positioned (baselines,
defines.yaml, predicate specs, six redundant verification layers) with exactly three
gaps, which are this program's work items.

## Work items

1. ✅ **DONE 2026-07-09 (`66125a22`)** — **`docs/reference/determinism-contract.rst`** — the
   language-agnostic specification of every constitutional hash (621 lines; worked example
   reproduces the committed imperial_circuit `defines_hash` exactly; hand-computation gate
   satisfied; three implementation/doc discrepancies surfaced as owner-queue item 31):
   - `defines_hash`: exact byte recipe (today: sha256 over Python `json.dumps` of the
     Pydantic dump, first 16 hex chars — `tools/regression_test.py:131`; the doc must pin
     field order, separators, float formatting so a non-Python implementation can
     reproduce it).
   - the `tick_commit` chain (spec-089): what bytes are hashed, in what order, chained
     how; note the known session-id embedding (cross-run comparison uses the Postgres
     `EXCEPT` row-diff instead — per proof-2R Part 4 precedent).
   - the III.7 tick hash: inputs (World state + actions + seed), canonical serialization.
   - **Float policy:** byte-identical replay is an intra-implementation guarantee
     (CPython + one libm). Cross-implementation validation = tolerance-bounded checkpoint
     comparison; every tolerance ships with a written derivation (pattern:
     `specs/053-conservation-invariants/contracts/value_conservation.md`,
     `tol(N) = max(1e-10, 1e-11·N)`).
   Gate: a reviewer can compute `defines_hash` for a toy defines fragment by hand from
   the doc alone, without reading the Python.

2. ✅ **DONE 2026-07-09 (`60a919e3`)** — **Dense golden traces for the five regression
   scenarios.** Extend
   `tools/regression_test.py` with a dense mode: per-tick, full-variable trace artifacts
   (committed alongside the sampled-checkpoint JSONs, which stay for fast diagnosis).
   Today `imperial_circuit.json` pins ~9 variables × ~6 checkpoints ≈ 54 numbers for a
   52-tick world; a plausible-but-wrong engine could pass. The detroit-tri-county bundle
   (full `trace.csv`, byte-compared) is the density standard — bring the five unit
   scenarios up to it. Gate: `qa:regression` compares dense traces byte-identically
   (intra-implementation); artifact format documented in the determinism contract.

3. **Contract-per-boundary discipline (standing, now constitutional).** Every new system
   boundary ships with a contract test + its behavioral artifact — the practice Phase A
   established (`web/game/map_contract.py`, `test_dashboards.py`,
   `test_full_persistence.py`) — enforced via III.12 in review, no new tooling required.

## Non-goals

- No Rust rewrite is planned. The rewrite test is the acceptance criterion for the spec
  layer, not a migration proposal.
- No mass porting of unit tests to "behavioral style" — implementation-coupled unit
  scaffolding is legitimate and regenerable; we only forbid it being the ONLY home of
  load-bearing knowledge (VIII.13).
- Item 2 must not slow the inner loop: dense comparison can run as the `qa:regression`
  default only if wall-time stays acceptable; otherwise sampled stays default and dense
  runs in CI/pre-merge.

## Definition of done

`mise run check` green; the determinism-contract doc exists and passes its
hand-computation gate; five dense goldens committed + compared in `qa:regression`;
Amendment Q's corollary (a) flips `[PENDING CODE]` → `[IMPLEMENTED]` in
`CONSTITUTION.md`; ADR notes the landing.
