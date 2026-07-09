# Progress Report — Loud Machine Remediation, Day 1

**Date:** 2026-07-08 (updated through ~5pm ET; the earlier revision of this file was the ~noon snapshot)
**Author:** Claude Fable 5, executing `project/execution/REMEDIATION_PLAN.md` under ultracode orchestration
**Scope authority:** `project/programs/09-program-full-game.md` → `project/assessments/POST_ASSESSMENT.md` → `project/assessments/HOLISTIC_REVIEW-2026-07-07.md` → the remediation plan
**Method:** scout agents produce verified file:line implementation briefs → implementation agents execute TDD in isolated git worktrees → serial merge train into `dev` with scoped tests per merge and a full `mise run check` per batch.

______________________________________________________________________

## 0. ⭐ SUPERSEDING UPDATE — PHASE 2 COMPLETE (2026-07-08 late evening, Opus 4.8)

> This section supersedes the lane-status content of §1–§10 below (the ~5pm Fable-5
> snapshot). Those sections are preserved as the historical record of the two-outage
> day; where they say a Phase-2 lane is "interrupted / snapshotted / pending," read
> the table here instead.

**All four interrupted lanes + both parked defects + the 2.R capstone are merged.
Phase 2 is complete. All six P0s are fixed. dev @ `5d954ecb`, full `mise run check`
green (9421 passed, 17 skipped, 4 xfailed).** No dangling wip branches; all
remediation worktrees removed.

| Lane | Merge | What landed |
|---|---|---|
| chore: secret-leak prevention | `88e34ab5` | `sessions/` + `.dev.vars*` gitignored; `session-ses_0d18.md` untracked (task #22 prevention half — rotation still owner-pending) |
| **2.2** territory-case no-ops | `1546a330` | `"Territory"`→`"territory"` case fix un-no-ops ReserveArmy + Dispossession; 8 Territory round-trip fields; `wage_pressure` exclusion |
| **6.2** spec-063 Vol-II circulation tail | `0fae122c` | T040/T042/T043 + FR-026 revival + T033 Canada-required + T052 atomicity-inheritance; 5 integration tests green |
| **2.4** verb-dispatch engine (**6th/last P0**) | `9f6f244e` | `ActionType.MOVE` + defines + eligibility → `Action.params` → `VERB_RESOLVERS` (9 resolvers) → OODA dispatch → bridge 9-verb map; player verbs now resolve to real deltas; canary retired to `tests/contract/verbs/` |
| **5.4** storage gates | `ad457f8c` | Gates A/B/C (two-sided storage-budget floors) + session-scoped `sim:status` (kills the false 1,295 MB/tick artifact) + record repair |
| Gate B runtime guard (cross-lane 5.4 fix) | `ab89d8a6` | 5.4's unconditional tick-0 marker read-back crashed the pure tick-loop (runtime=None) + gamma-wiring fake bridge; guarded behind `runtime is not None` |
| **Wave 3** parked defects | `276fcb2b` | `decomposition` seeds `inequality` (VitalitySystem KeyError on C700/C800 → fixed; §7.1-adjacent); `hydrate_graph` restores 7 graph-scope metadata keys via `graph_metadata.extra` (fixes §7.1 `MonotonicityViolationError`) |
| **2.R** baseline capstone + C.8 | `5d954ecb` | R-PROOF: gated-field neutrality **proven** (byte-identical old-vs-new via persisted state — consumption-path isolation holds though gamma-wiring broke spec-102's wiring-path isolation); 2.3 determinism **proven** (0/0 A/B on consciousness + hex to tick 51); Track-A scenario baselines regenerated (defines_hash-only drift); C.8 loud economics-fallback counters + `economics_fallbacks` manifest section |

### ⚠ NEW BLOCKER surfaced by 2.R → ruled to a Phase-3 spec (Percy, 2026-07-08)

The gamma wiring (`cc4a5303`, correctly merged) **exposed a latent core-loop crash**:
the canonical 520-tick run **cannot complete** — it dies deterministically at **tick 52**
with `ClassDistribution.fips String should have at least 5 characters [input_value='T001']`.
Root cause: `WorldStateBridge` mints territory ids `T{i:03d}` (real FIPS only in the
node's `name`), but `TickDynamicsSystem._get_territory_fips` / `_bootstrap_county_states`
use `str(node.id)` and feed `T001` into `ClassDistribution(fips=…)`. Dormant the entire
life of the old baseline (`melt_calculator` was `None`); gamma-wiring satisfied the gate
and lit it. **This is the same root gap §7.6 flagged** ("zooms degenerate until Territory
carries `county_fips`") — the `Territory` model has no `county_fips` field at all.

2.R also found a coupled deeper issue: the **bridged hex economy is static** — production
isn't evolving the material base; gated totals are frozen at tick-0 hydration for the
whole run (this is *why* neutrality holds, but means a crash-fixed run still wouldn't
simulate production dynamics).

**`cc4a5303` is therefore ESCALATED, not closed.** Full proof + evidence:
`specs/102-gamma-shocks/proof-2R-baseline-regen.md`. **Percy's ruling (2026-07-08):
handle via a dedicated Phase-3 spec** — the Territory↔FIPS contract fix + the
static-economy investigation. `michigan-e2e.json` stays valid on its gated fields but
cannot be refreshed to tick 519 until that spec lands. Tracked as owner-queue **item 25**.

**Next:** author spec-107 (spectrum) + spec-108 (transport) as already queued, and the
new Phase-3 Territory↔FIPS / static-economy spec (item 25). Push to origin remains
blocked on owner task #22 (token rotation).

______________________________________________________________________

## 1. Headline

**Fifteen branches are merged to dev and the full gate is green** (`mise run check`
= ruff + format + mypy strict + test:unit: **exit 0**, run twice — after the Phase-1
batch and after the final 4-branch batch). **Five of the six P0s that made the game
unplayable are fixed and merged**; the sixth (engine-side verb effects, 2.4) is
scoped with a verified brief and an empty worktree ready. Seven of the thirteen
Loud Machine gates are live in CI/pytest. A second session-limit outage (~4pm ET)
killed the four in-flight implementation agents; all of their work was recovered
into durable `wip(...)` snapshot commits (§4) and every remaining phase has a
verified implementation brief preserved in-repo (§6).

dev sits at `3371dc8c` + this docs merge, **239 commits ahead of origin, local-only**
— push is still blocked on the leaked-token owner decision (§9).

## 2. Merged to dev (all gates green at merge)

| # | Branch | What it did | Merge |
|---|---|---|---|
| 0.1 | `fix/game-session-schema-parity` | `snapshot_json` orphan removed everywhere (models, DDL, stub, test DDLs); JSONB round-trip coverage repointed at `config_json` | `3e985418` |
| 0.2 | `fix/migration-0027-idempotent` | Migration sequence idempotent under the runner's re-apply-all contract; dup `0031` renumbered → `0032`; **C.3 gate** (fresh-DB double-apply test); un-redded the 10 Postgres-path unit failures | `9101dddf` |
| 0.3 | `chore/test-infra-rearm` | **C.9**: `strict_markers`/`strict_config` as working ini options; `ai` marker real (179 tests; selected zero before); `contract` registered; pytest-timeout; all 30 stale `red_phase` markers retired; dead ui-tests CI job deleted; mise/CI gate parity | `f5dbf0c2` |
| 0.4 | `docs/commit-truth-and-push` | Truth record committed (E2E summary, post-assessment, holistic review, remediation plan); `state.yaml` v2.17.0 truth banner | `3f9d1d69` |
| 1.2 | `fix/seed-scenario-loud` | Unknown scenarios fail loud at every entry point (bridge ValueError / CommandError / API 400); `us_nationwide` kept as explicit alias; validation above session creation | `dd2fd4d7` |
| 1.3 | `feat/map-hex-projection` | **P0 #7**: bridge projects territories into `hex_latest` at create_game tick-0, every resolve_tick, and legacy backfill — map API returns real features | `da53d090` |
| 1.4 | `feat/frontend-live-verbs` | **P0 #4 + P0 #5**: VerbPage wired to live `fetchVerbTargets` + per-verb payload builders with exact backend field names; fixture import deleted; 499/499 Vitest, tsc clean | `3293833d` |
| 6.1 | `docs/spec-checkbox-truth-sweep` | Specs ledger reconciled with code: 685 tasks → `[x]` with file:line evidence, 96 → `[~]`, 14 false checks reversed in spec-059 | `cb959017` |
| — | `docs/project-management-directory` | `project/` reorganized into programs/assessments/execution/owner/reference + this report + PM README (one-stop catch-up index) | `8b2bbf38` |
| — | `docs/readme-landing-page` | Repo README rewritten to present reality (rustworkx substrate, 26 systems, web/ structure, honest "where we are" section) | `de0646bc` |
| 2.5 | `fix/web-session-hygiene` | **C.13**: resolving-watchdog (`POST /games/{id}/recover/` + `sweep_stale_sessions` command + migration 0012 un-freezing `updated_at`); session-scoped defines metadata (was cross-session-contaminating) | `de8c513f` |
| 1.1 | `fix/tick-resolve-datetime` | **P0 #6**: shared `persistence/serialization.py` (`json_default` + canonical event JSON with timestamp exclusion → idempotent retries); BOTH backends fixed (the SQLite twin had the identical bug); `model_dump(mode="json")` ×3 in the bridge. RED proven on both backends + the live web DB | `01d6e4ef` |
| 1.5 | `test/e2e-real-loop` | **C.4 + C.5**: CI Postgres/PostGIS service leg (testcontainers suites now actually run) + Playwright CI job + the first REAL submit→resolve→results e2e spec | `d129c9c4` |
| 2.3 | `fix/engine-determinism` | **III.7 + C.2(a)**: deterministic `sim_clock`, tick-derived timestamps, seeded StruggleSystem RNG (the 3897-vs-3915 divergence root cause), seeded topology purge, EventBus handler isolation, in-process 10-tick two-run A/B hash gate | `abc6073d` |
| 2.1 | `fix/from-graph-safety` | Design B + **C.1**: `WorldState.sovereigns` round-trip (un-deads the spec-070 collapse layer — 2 of 5 endings were unreachable), circular-import fix (un-broke `test:doctest` repo-wide), writer payload completeness, exclusion frozensets, `institution_relations` preserved, event-replay fallback (60/79 EventType crash), loud edge-collision pre-scan, C.1 system-on-roundtrip gate. Bonus: found+fixed the two-node scenario's silently dead SOLIDARITY edge (same-pair WAGES overwrote it — exactly the bug class the pre-scan now catches) | `3371dc8c` |

## 3. Scoreboards

**P0s (from `assessments/E2E_SUMMARY.md` + planning):**

| P0 | Status |
|---|---|
| #1 schema parity crash | ✅ merged (0.1) |
| #4 verb payloads rejected | ✅ merged (1.4) |
| #5 verb targets were fixture IDs | ✅ merged (1.4) |
| #6 tick-resolve datetime 500 | ✅ merged (1.1) |
| #7 map renders zero features | ✅ merged (1.3) |
| #8 (6th, found in planning) verbs are engine-side no-ops | ✅ merged (2.4, `9f6f244e`) — see §0 |

**Loud Machine gates:**

| Gate | Status |
|---|---|
| C.1 roundtrip · C.2(a) determinism A/B · C.3 migration idempotency · C.4 CI Postgres leg · C.5 Playwright CI · C.9 test-infra re-arm · C.13 resolving watchdog | ✅ live |
| Storage gates A/B/C (5.4 — plan-external, from the adjudication) | 🔶 in flight, snapshotted (§4) |
| C.6/C.7 degradation envelope + stub visibility · C.2(b) nightly A/B · C.10 deptry · C.11 doc-ref linter · C.12 budget gates · C.8 wiring audit (lands with 2.R) | 📋 briefs ready (§6) |

C.11 note: a prototype linter already ran — **169 broken doc refs found** (69% in
`state.yaml`/`entities.yaml`/`architecture.yaml`; details + a false-positive class
recorded in `execution/phase7-inputs.md`).

## 4. Interrupted lanes — RESUME RUNBOOK

A second session-limit outage (~4pm ET) killed all four implementation agents.
All uncommitted work was recovered into `wip(...)` snapshot commits — **these are
resume points, NEVER merge candidates**. Worktrees live under the (ephemeral)
session scratchpad `wt/` dir, but every commit below is in the main repo's object
store and survives scratchpad loss: `git worktree add <path> <branch>` recreates
a workspace anywhere.

**Resume protocol** (proven after the first outage): check `git log dev..<branch>`
+ the wip tip BEFORE assuming anything is unstarted; recreate the worktree; symlink
`data/sqlite` and `web/frontend/node_modules` from the main checkout into it (gitignored,
never carried by worktrees); run tests as
`PYTHONPATH=$PWD/src:$PWD/web <main-checkout>/.venv/bin/python -m pytest <paths> -q -p no:cacheprovider`.
A continuation agent may build directly on the wip tip or `git reset --soft` it —
but must replace it with real TDD commits before merge.

| Lane | Branch @ tip | State | Remaining |
|---|---|---|---|
| **2.2** territory-case no-ops (task #11) | `fix/territory-case-noops` @ `388cccfa` (wip only) | RED round-trip suite written — `tests/unit/engine/systems/test_feature021_territory_roundtrip.py`, 5 cases built from production-shaped `to_graph()` fixtures incl. a 3-tick compounding test; mid-edit: `reserve_army.py`, `dispossession_events.py`, `territory.py`, `world_state.py`, 4 existing test files | Finish `"Territory"`→`"territory"` fix; per-attr ruling (model field vs exclusion frozenset) for each non-model write; green the REDs; fix masking fixtures; scoped gates; merge. **Baseline-affecting → regen deferred to 2.R.** Brief: `briefs/fix-territory-case-noops.md` |
| **2.4** verb-dispatch engine (task #14, **last P0**) | `feat/verb-dispatch-engine` (= dev, no commits) | Worktree untouched — genuinely unstarted | Whole design in REMEDIATION_PLAN §A + `briefs/feat-verb-dispatch-engine.md`. Archaeology findings to honor: `get_action_base` maps only 9/25 ActionTypes (16 silently 0.0) though OODADefines has costs/deltas for all 25; no `InvestigateDefines`/`ReproduceDefines` exist; 4 canary-confirmed stub resolvers don't touch the simplex. Depends on 2.1 (✅ merged) |
| **5.4** storage gates (tasks #25–#28) | `fix/storage-contradiction` @ `7e04b422` (wip) over `9d3e8843` | **Step 1 DONE + committed** (`9d3e8843`: init bootstrap must not claim the tick-0 commit marker — the live P1 from the adjudication); wip holds Gate A/B work (Gate A `hex_template_size` tests RED — property not yet implemented on WorldStateBridge; Gate B `_verify_tick0_commit_marker` tests written) | #25 finish Gates A+B; #26 Gate C two-sided storage-budget floors; #27 session-scoped `sim:status`; #28 record repair + archival note. Adjudication (task #23, DONE): 1,295 MB/tick was a stale pre-spec-089 artifact; delta persistence is real. Brief: `briefs/fix-storage-contradiction.md` |
| **6.2** spec-063 tail (slice of task #20) | `feat/spec-063-tail` @ `423e055a` (wip) over `455c2bd1` | **T043 DONE + committed** (`455c2bd1`: `PairedCrossBorderEmissionEvaluator` + runner registration); wip holds T042 loader wiring (`postgres_initialization.py`) + all 5 integration test files (hex-graph-padding fix applied through the 5th) + `tasks.md` edits | Finish T042 wiring; green the 5 integration tests; ledger; gates; merge. Brief: `briefs/feat-spec-063-tail.md` |

## 5. Task board mirror

Completed: #1–#10, #12, #15 (all Phase 0 + Phase 1 + 2.1/2.3/2.5), #23–#24 (5.4
adjudication + step 1). In progress (= snapshotted, §4): #11 (2.2), #14 (2.4),
#25 (5.4 step 2). Pending: #13 (2.R baseline regen + proof.md — unblocks after 2.2),
#16–#17 (Phase 3), #18 (Phase 4 059 splits), #19 (Phase 5 dormant-sim wiring),
#20 (Phase 6 tails → national capstone), #21 (Phase 7 record repair), #26–#28
(5.4 steps 3–5), #22 (OWNER, §9).

## 6. Preserved knowledge — briefs are now in-repo

`project/execution/briefs/` holds all **19 verified scout briefs** (moved from the
ephemeral session scratchpad), including the two Phase-3 briefs recovered from the
killed workflow's journal (`feat-degradation-envelope.md`, 9 drift alerts;
`ci-nightly-and-audits.md`, 10 drift alerts) and re-scouted `feat-gamma-atus-adapter.md`
(5.1) + `feat-tensor-hierarchy-resolution.md` (5.3). Each encodes verified-at-HEAD
file:line seams and where reality deviates from the plan — an implementation agent
should trust brief over plan where they conflict, and re-verify anything dated
before the 2.1/2.3 merges. `execution/phase7-inputs.md` accumulates record-repair
inputs for Phase 7. Phase 4 (059 splits) intentionally has no brief — the plan
section + the now-honest spec-059 ledger are the spec.

## 7. Parked pre-existing defects (found, not fixed — do not lose)

1. ✅ **FIXED (Wave 3, `276fcb2b`).** ~~`hydrate_graph` restores no graph metadata~~
   → `hydrate_graph` now restores the 7 graph-scope keys via `graph_metadata.extra`;
   rehydrated sessions resolve without `MonotonicityViolationError`. (Found by the
   1.1 lane; was pre-existing.)
2. `_persist_events` reads `e.get("type"/"entity_id")` but events emit `event_type`
   → `simulation_event.event_type` = 'UNKNOWN', `entity_id` NULL (Phase 3.1-adjacent).
3. `StubEngineBridge.create_game` kwargs mismatch → POST /api/games/ under stub
   bridge raises TypeError (fold into C.7 work).
4. Snapshot-shape drift asserted by 3 older bridge tests (documented in 1.1 notes).
5. Per-tick atomicity integration fixtures have pre-existing setup errors.
6. `get_map_snapshot` metadata hardcodes h3_resolution 7; county/BEA/MSA/state zooms
   degenerate until Territory carries `county_fips`; `hex_latest` Marxian indicator
   columns NULL until Phase 5 wiring.

## 8. Incidents and process notes

- **Two session-limit outages** (2026-07-08 ~03:00 reset 04:40, and ~12:00 reset
  16:00 ET) each killed the live agent fleet. Damage ≈ zero both times because
  worktree commits survive agent death; after the second, all dirty worktrees were
  snapshotted as wip commits (§4). The resume protocol in §4 is now the standard.
- **Scout-first discipline keeps paying**: briefs caught the plan being wrong before
  code did (us_nationwide must stay creatable; SQLite twin shared the datetime bug;
  OODA `params` never reach the engine; datetime crash fires on FIRST persist).
- **Merge hygiene**: `--no-ff` with `chore(merge)` subjects (commitizen rejects
  `merge:`); scoped tests per merge; full `mise run check` per batch (~35–40 min).

## 9. ⚠ OWNER ACTIONS REQUIRED

1. **Leaked Cloudflare API token (task #22)** — `git push origin dev` is blocked by
   GitHub push protection: a real Cloudflare token sits in `sessions/session-ses_0d18.md`
   (commit `c1cba41a`, the first of the ~239 unpushed). Verified the ONLY secret in
   the range; it never left this machine. Required: (a) **rotate the token at
   Cloudflare** regardless; (b) choose **[A]** GitHub unblock-URL push (dead string
   stays in history, zero SHA churn) or **[B]** approve the prepared range-constrained
   `git-filter-repo` scrub (backup ref `backup/dev-pre-secret-scrub-DO-NOT-PUSH`
   exists; the automation guardrail correctly refused to let an agent rewrite
   history unilaterally). Phase 3.2 adds the secret-scanning pre-commit hook.
2. **~~New economics feature discussion queued~~ RESOLVED same evening** — the
   discussion happened and was ratified as **Program 10: the Spectrum of Unequal
   Exchange** (spec-107). Five rulings captured in
   `programs/10-spectrum-of-unequal-exchange.md` + `owner/owner-queue.md` item 23.
   Lands as Phase 5.5; spec-107 authoring is next session's first work item.

## 10. What happens next

1. **Author spec-107** (Spectrum of Unequal Exchange) via speckit from
   `programs/10-spectrum-of-unequal-exchange.md` — next session's first work item
   (rulings ratified 2026-07-08 evening; see §9.2). **Then author spec-108**
   (Transport Substrate) from `programs/11-transport-substrate.md` — ratified the
   same evening (owner-queue item 24, declared the LAST new feature; ALL rulings
   complete incl. round 2 — state-owned corridors, INFORMAL edges in slice 1,
   existing BUILD_INFRASTRUCTURE ActionType, waterways deferred — nothing blocks
   authoring; implementation prereqs: 6.2, 2.4, 5.2-Batch-C).
2. Resume 2.2 from `388cccfa` → merge → **2.R coordinated baseline regen + proof.md**
   (covers 2.2 + 2.3 + 2.1's two-node fix + the earlier gamma wiring `cc4a5303`;
   C.8 wiring audit lands here).
3. Resume 5.4 (from `7e04b422`) and 6.2 (from `423e055a`) — independent of 2.R.
4. 2.4 verb-dispatch engine (last P0) — fresh start off dev, brief + §7.1 in hand.
5. Phase 3 (briefs ready) → Phase 4 (059 splits) → Phase 5 (dormant sim, R-PROOF
   each; **5.5 = spec-107 spectrum, after 5.2/5.3**) → Phase 6 (tails → **spec-108
   transport substrate implemented here** → spec-106 national perf → 105 capstone,
   which must exhibit the spectrum live AND the transport arc: corridor severed by
   an uprising → value stranded → state-AI repair) → Phase 7 (record repair;
   inputs in `execution/phase7-inputs.md`).
