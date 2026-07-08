# Progress Report — Loud Machine Remediation, Day 1

**Date:** 2026-07-08 (written mid-execution, ~noon)
**Author:** Claude Fable 5, executing `project/execution/REMEDIATION_PLAN.md` under ultracode orchestration
**Scope authority:** `project/programs/09-program-full-game.md` → `project/assessments/POST_ASSESSMENT.md` → `project/assessments/HOLISTIC_REVIEW-2026-07-07.md` → the remediation plan
**Method:** scout agents produce verified file:line implementation briefs → implementation agents execute TDD in isolated git worktrees → serial merge train into `dev` with scoped gates per merge and a full `mise run check` per batch.

______________________________________________________________________

## 1. Headline

Six of the program's branches are **merged to dev** and verified; eight more are
**in flight** in parallel worktrees as this is written. Three of the six original
P0s that made the game unplayable are fixed and merged (map blank, verb payloads,
fixture targets); the fourth (tick-resolve datetime crash) is committed on its
branch awaiting final gates. The disarmed test guardrails are re-armed. The specs
ledger has been reconciled with code reality across 24 spec directories.

**One item needs Percy personally — see §5 (leaked Cloudflare token).**

## 2. Merged to dev (all gates green at merge)

| Branch | What it fixed | Evidence |
|---|---|---|
| `fix/game-session-schema-parity` (0.1) | `snapshot_json` orphan removed everywhere (models, DDL, stub, test DDLs); JSONB round-trip coverage repointed at `config_json` | merged `3e985418` |
| `fix/migration-0027-idempotent` (0.2) | Migration sequence idempotent under the runner's re-apply-all contract; dup `0031` renumbered → `0032`; **C.3 gate** (fresh-DB double-apply test) added; un-redded the 10 Postgres-path unit failures | merged `9101dddf`; idempotency suite 3/3 |
| `chore/test-infra-rearm` (0.3, gate C.9) | `strict_markers`/`strict_config` as working ini options (the addopts flags were verified no-ops on pytest 9); `ai` marker real (179 tests; `-m ai` selected **zero** before); `contract` marker registered; pytest-timeout installed; **all 30 stale `red_phase` markers retired** (ground truth: 51 pass / 10 documented skips / 0 fail); dead ui-tests CI job deleted; mise/CI gate parity | merged `f5dbf0c2`; full gate 9,227 passed / 0 failed (34m24s) |
| `docs/commit-truth-and-push` (0.4) | Truth record committed (E2E summary, post-assessment, holistic review, remediation plan); `state.yaml` v2.17.0 truth banner + authority chain | merged `3f9d1d69` |
| `fix/seed-scenario-loud` (1.2) | Unknown scenarios fail loud at **every** entry point (bridge ValueError / CommandError / API 400); `us_nationwide` kept as explicit alias (the UI submits it); validation moved above session creation (no orphaned rows); the old silent-fallback tests inverted | merged `dd2fd4d7`; 341 scoped tests green |
| `feat/map-hex-projection` (1.3, **P0 #7**) | Bridge projects territories into `hex_latest` at create_game tick-0, every resolve_tick, and legacy backfill — the map API now returns real features (RED test reproduced the exact E2E zero-features symptom first) | merged `da53d090`; 372 scoped tests green |
| `feat/frontend-live-verbs` (1.4, **P0 #4 + fixture-targets P0**) | VerbPage wired to live `fetchVerbTargets` + per-verb payload builders with exact backend field names; fixture import deleted; per-verb parseTargets drift fixed (investigate groups, attack edges, reproduce self-target, mobilize status check); 3 Vitest harness reds fixed | merged `3293833d`; 499/499 Vitest, tsc clean, eslint 0 errors (independently re-verified by the orchestrator) |
| `docs/spec-checkbox-truth-sweep` (6.1) | Specs ledger reconciled with code: 685 tasks flipped to `[x]` with file:line evidence across 21 specs, 96 to `[~]` partial, 14 **false checks reversed** in spec-059 (the never-done monolith splits) | merged `cb959017`; `[record-reconciliation]` trailers |

Post-merge scoped verification on dev: 353 backend + 499 frontend tests green.
A full `mise run check` batch gate was launched after the Phase-1 merges.

## 3. In flight right now (parallel worktrees, agents working)

| Branch | Phase | State when last checked |
|---|---|---|
| `fix/tick-resolve-datetime` | 1.1 (**P0 #6**) | All code written (shared `persistence/serialization.py`, both backends fixed — the SQLite twin had the identical bug —, canonical-payload timestamp exclusion, 3× `model_dump(mode="json")` in the bridge); continuation agent finishing commits + gates |
| `fix/from-graph-safety` | 2.1 (Design B + **C.1 gate**) | 6 commits landed (circular-import fix, `WorldState.sovereigns` round-trip, writer payload completeness, exclusions, `institution_relations`, event-replay fallback); continuation agent finishing the edge-merge pre-scan + the C.1 system-on-roundtrip gate |
| `fix/engine-determinism` | 2.3 (III.7 + **C.2(a) gate**) | All 6 commits landed (sim clock, tick-derived timestamps, seeded struggle RNG, seeded topology purge, bus handler isolation, in-process determinism A/B gate); verification agent closing it out |
| `test/e2e-real-loop` | 1.5 (**C.4 + C.5**) | Agent standing up the real stack (PostGIS CI leg, Playwright CI job, the first real submit→resolve→results spec) |
| `fix/web-session-hygiene` | 2.5 (**C.13**) | Agent implementing the resolving-watchdog (`/recover/` + sweeper + un-frozen `updated_at`) and session-scoped defines metadata |
| `fix/storage-contradiction` | 5.4 | **Adjudicated:** the 1,295 MB/tick observation was a stale pre-spec-089 artifact, **but a live P1 tick-0 marker collision was found**; agent building the loud gates (template-size gate, tick-0 commit-marker verification, two-sided storage-budget floors, session-scoped `sim:status`) |
| `feat/spec-063-tail` | 6.2 | Agent implementing T042 loader wiring + T043 `PairedCrossBorderEmissionEvaluator` + the 5 missing integration tests |
| Scout re-runs | 5.1 gamma-ATUS, 5.3 tensor-hierarchy | Rebuilding the two briefs lost to the session-limit outage |

Verified implementation briefs are ready and waiting for: 5.2 (Vol II/III service
wiring), 6.3 (spec-043 land tail), 2.2/2.4 (blocked on 2.1's merge by design).
Phase 3 scout briefs are the next scouting wave.

## 4. Incidents and process notes

- **Session-limit outage (2026-07-08 ~03:00–04:40 ET):** killed 6 agents mid-lane.
  Damage was limited because worktree commits survive agent death — 2.3 was fully
  committed, 2.1 was 6/8 items in, 1.1's code was written but uncommitted.
  Continuation agents were given exact gap lists rather than restarting lanes.
  Lesson encoded: check `git log dev..<branch>` before assuming a lane is unstarted.
- **Scout-first discipline paid for itself repeatedly.** Verified briefs caught the
  plan being wrong in ways that would have shipped bugs: `us_nationwide` had to stay
  creatable (the UI submits it); the SQLite runtime twin shared the datetime bug; the
  dormant hex writers the plan wanted reused need tables the bridge never populates;
  the datetime crash fires on FIRST persist, not just retries; OODA `params` never
  reach the engine at all.
- **Merge hygiene:** every merge is `--no-ff` with `chore(merge)` subjects
  (commitizen rejects `merge:`), scoped tests before each merge, full gate per batch.

## 5. ⚠ OWNER ACTION REQUIRED — leaked Cloudflare API token

`git push origin dev` is **blocked by GitHub push protection**: a real Cloudflare
Account API token sits in `sessions/session-ses_0d18.md` (4 occurrences, commit
`c1cba41a` — the *first* of the ~190 unpushed commits). A full-range sweep confirmed
it is the **only** secret in the unpushed history. It never left this machine.

Required, in order:
1. **Rotate the token at Cloudflare** (it also lives in local MCP config, so it must
   be rotated regardless of what happens in git).
2. Choose the push path:
   **[A]** Use GitHub's unblock-secret URL and push as-is — the dead token string
   stays in public history; zero SHA churn. Fastest.
   **[B]** Approve the prepared history scrub — `git-filter-repo --replace-text`,
   range-constrained to the unpushed commits (`e3f14d02..dev`); a dry run verified
   the already-pushed prefix keeps its SHAs. Local backup ref exists
   (`backup/dev-pre-secret-scrub-DO-NOT-PUSH`). The automation guardrail correctly
   refused to let an agent rewrite dev history without you.
3. Hardening follow-up already scheduled in Phase 3.2: a secret-scanning pre-commit
   hook so a pasted credential can never reach a commit again.

Until then dev accumulates safely local-only.

## 6. What happens next (unchanged plan order)

1. Land the in-flight lanes (merge train, full gate per batch).
2. 2.2 territory-case no-ops (unblocks on 2.1) → 2.R coordinated baseline regen +
   proof.md → 2.4 verb-dispatch engine (the 6th P0 — engine-side verb effects).
3. Phase 3: degradation envelope (C.6/C.7), nightly + audit gates (C.2b/C.10/C.11/
   C.12 + secret scanning).
4. Phase 4: the 059 monolith splits (now honestly unchecked in the ledger).
5. Phase 5: wire the dormant sim (gamma-ATUS, Vol II/III services, tensor hierarchy)
   — each defines-gated with R-PROOF proof.md.
6. Phase 6: spec tails → spec-106 national perf → the 105 national capstone run.
7. Phase 7: record repair (regenerate `state.yaml`, ai-docs corrections, supersession
   banners) — accumulated inputs are being kept in the session scratchpad.
