# \_HANDOFF.md — Program 09 execution handoff (2026-07-04 ~04:30 EDT)

**Written for:** any coding agent continuing this work (the previous orchestrator
hit its weekly token limit mid-execution; resets Jul 7 4am ET).
**Written by:** the Claude Code orchestrator session `19bb4b93` (Opus orchestrating
Sonnet subagents, adversarial-review discipline).

______________________________________________________________________

## 0. What you are doing, in one paragraph

You are executing **Program 09 — Full-Game Build** (`project/09-program-full-game.md`,
the ratified master plan) for Babylon, a Marxist geopolitical simulation engine.
Work runs in **4 parallel lanes** (E=engine, W=web product, D=data, O=observatory)
in **git worktrees**, one spec at a time per lane, with **fresh implementer
subagents per spec**, **adversarial multi-agent review of every spec**, a **fix
pass per review**, and re-verification. Nothing merges to `dev`/`main` — the owner
(Percy Raskova, the Benevolent Dictator) merges; you queue owner decisions. The
detailed running ledger of everything done so far is
**`/home/user/projects/game/babylon/.superpowers/sdd/progress.md`** — read it
after this file; it is the authoritative play-by-play (Waves 1–14).

______________________________________________________________________

## 1. Repo / worktree topology (verified at handoff time, all trees CLEAN)

Main repo: `/home/user/projects/game/babylon` — branch `dev` @ `e3f14d02` (untouched).
Second repo: `/home/user/projects/game/babylon-data` — branch `100-county-exposure` @ `6bf3024` (D:100 loader code, ready for owner).

| Worktree         | Branch @ HEAD                             | Contents                                                                                                                                                                 |
| ---------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `worktrees/e071` | `071-reactionary-subject` @ `80441be3`    | E:071 COMPLETE (17 commits)                                                                                                                                              |
| `worktrees/e101` | `102-gamma-shocks` @ `70e6512a`           | E:101 COMPLETE underneath (`101-trade-activation` @ `8210db17`, pushed to origin); E:102 built on top, **review-fix pass NOT started**                                   |
| `worktrees/w090` | `093-territory-org-detail` @ `24fc95f3`   | W:090/091/092 COMPLETE underneath (stacked: `090-cold-collapse`→`091-frontend-consolidation`→`092-event-log` @ `8044d7c5`); W:093 built, **review-fix pass NOT started** |
| `worktrees/o096` | `099-observatory-deep-panes` @ `c19a4a87` | O:096 + O:099 COMPLETE (entire O lane done)                                                                                                                              |
| `worktrees/d100` | `098-qcew-adapter-fix` @ `2cb081b1`       | D:100 + D:098 COMPLETE (D independent work done)                                                                                                                         |

Branch stacking (important for review bases):

- `101-trade-activation` = dev + 071 + merge of `100-county-exposure` (at `8cea433b`) + 101's commits. `102-gamma-shocks` stacks on `8210db17`.
- w090 chain: 090 (→`42232a15`) → 091 (→`c1d1a834`) → 092 (→`8044d7c5`) → 093 (→`24fc95f3`).

Worktree symlinks already in place: `.venv` → main repo venv; `data/sqlite` → the
trove symlink; w090+o096 also `web/frontend/node_modules` → main.

______________________________________________________________________

## 2. CRITICAL environment gotchas (each cost real debugging time)

1. **Bare `poetry run` inside a worktree imports the MAIN repo's `babylon`** (editable
   .pth). Always `mise run <task>` or `PYTHONPATH=src poetry run ...` from the worktree.
1. **Two Postgres instances**: product **5432**/`babylon` (Django/web; lanes W+O) vs
   runner **5433**/`babylon_test` (headless sim; lanes E+D-integration). Never run the
   E-lane canonical sim concurrently with anything else touching 5433.
1. **hex_spatial_map / TIGER contention (root cause found, partially fixed)**:
   `hex_spatial_map` is a GLOBAL non-session-scoped table on 5433; some integration
   test truncates/repopulates TIGER-derived tables without isolation. A concurrent
   run once zeroed a canonical baseline silently. E:102's STEP-0 commit (`6b7a1fd4`)
   added a fail-loud guard (`_assert_county_resolution_or_raise` in
   `src/babylon/engine/headless_runner/runner.py`). The deeper fix (session-scoping /
   finding the offending test) is **open task #18** — must land before E:105.
1. **Sparse hex state (II.11)**: never read `dynamic_hex_state WHERE tick=N` raw —
   rows are delta-only + 52-tick checkpoints. Use `v_hex_state_asof`; last committed
   tick = `MAX(tick) FROM tick_commit`, not from the hex table.
1. **`mise run commit -- "type(scope): msg"`** for all commits (pre-runs hooks,
   re-stages hook fixes, verifies HEAD moved). Conventional-commit format enforced.
1. **The determinism hashes cannot verify cross-run determinism** (systemic, two
   independent confirmations): `tick_commit.determinism_hash` =
   `sha256(session_id:tick:seed)` (contentless identity digest);
   `conservation_audit_log.determinism_hash` hashes real state but embeds
   session_id. Cross-run determinism must be checked by comparing persisted VALUES
   (`v_hex_state_asof` + per-bloc DRAIN_EDGE) — E:102's tests do this correctly.
   Owner-queue item; do NOT "fix" the hash code casually (baselines depend on it).
1. Reference SQLite (read-only source data): `data/sqlite/marxist-data-3NF.sqlite`
   (a symlinked dir → trove at `/media/user/data/babylon-data/`). Archives land at
   `/media/user/data/babylon-archives/` via `mise run sim:archive`.
1. Canonical baseline: `tests/baselines/michigan-e2e.json` — gated fields are
   `counties_alive=83`, `counties_with_population=83`, `total_v≈3126580386.69`,
   tick 519. **Never commit a baseline whose gated fields are 0/zeroed** — that
   happened once (contention corruption) and was caught at the last moment.
   Regression gate: `mise run qa:e2e-regression` (total_v Δ must be 0.000%).

______________________________________________________________________

## 3. Status board (tasks #1–#18)

### DONE — reviewed, fixed, verified; awaiting owner (BD) merge

| Spec                                           | Branch                                       | Evidence                                                                                                  |
| ---------------------------------------------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| E:071 Reactionary Subject                      | `071-reactionary-subject`                    | byte-identical, canonical 83/83 archived, review clean                                                    |
| E:101 Trade activation (Φ boundary flows live) | `101-trade-activation` @ `8210db17` (pushed) | 8-finding fix pass done; baseline committed + verified; session `a8202ed0` archived                       |
| W:090 Cold Collapse design system              | in w090 chain                                | review clean after adjudication                                                                           |
| W:091 Frontend consolidation                   | in w090 chain                                | fix pass clean                                                                                            |
| W:092 Event Log + Tick Resolution              | `092-event-log` @ `8044d7c5`                 | 10-finding fix pass done (incl. the VARCHAR(12) severity migration 0031)                                  |
| O:096 Observatory foundation                   | in o096 chain                                | fix pass clean                                                                                            |
| O:099 Observatory deep panes                   | `099-observatory-deep-panes` @ `c19a4a87`    | 7-finding fix pass done (honest "STRUCTURE OK" relabel) — **O lane 100% complete**                        |
| D:100 County-exposure loader                   | `100-county-exposure` (both repos)           | fix + re-review clean; 384,200 exposure rows + 120 trade rows applied                                     |
| D:098 QCEW adapter fix                         | `098-qcew-adapter-fix` @ `2cb081b1`          | 21 schema-drift failures → 0; 0-vs-None fix; sibling MELT adapter fixed (national emp 2022 = 146,158,953) |

### IN FLIGHT — implementation done, **review-fix pass pending** (this is where you resume)

| Spec                                                  | State                                                                                                                                                                                                                                                                                                                                                                                                     | What must happen next                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **E:102 Gamma hydration + bloc shocks** (task #15)    | Built (10 commits `8210db17..70e6512a`). Adversarial review returned **4 CONFIRMED (1 critical) + 1 plausible + 7 minors, 0 refuted**. Fix brief is ready and authoritative: **`/home/user/projects/game/babylon/.superpowers/sdd/reports/102-fixes.md`**. A fix agent was dispatched but was killed by the token limit after only reading files — **zero fix commits exist; branch still @ `70e6512a`**. | Dispatch/perform the fix pass per the brief. Headline: `get_alpha()` (src/babylon/economics/melt/gamma_hydration.py:150) double-counts overlapping trade blocs (Europe⊇EU, Asia∩PacificRim, ATP is a commodity category) → use a non-overlapping total (spec-101's injective-crosswalk treatment in `postgres_initialization.py` is the in-repo precedent); `shock_schedule` missing from manifest `input_hash`; guard exit-code 5 unreachable from CLI; partial-resolution gap leaks NULL rows. Then re-run `qa:e2e-regression` (must stay Δ=0.000%) + `mise run check`, then a re-review or targeted verification.                                                                                                                                                                                                                                                                                            |
| **W:093 Territory/Org Detail + map lenses** (task #7) | Built (10 commits `8044d7c5..24fc95f3`). Adversarial review returned **12 CONFIRMED (6 critical), 0 refuted** — the worst review of the program. Fix brief ready and authoritative: **`/home/user/projects/game/babylon/.superpowers/sdd/reports/093-fixes.md`**. **Fix pass never dispatched.**                                                                                                          | Dispatch/perform the fix pass per the brief. Headline: the de-fixture *queries don't work* — `get_educate_targets` queries a node type (`community`) nothing creates; the extractive-edge filter reads the wrong attribute; `extraction_intensity` read from the wrong node type; `get_mobilize_targets` uses `"civil_society_org"` vs real enum `"civil_society"` → verbs return EMPTY in real games. Plus: no MSW/contract test exercises the real `/map/` wire shape; "no data" state never triggers (backend always sends non-null empty block); faction + Collapse-Moment lenses non-functional; economy stats missing BreakdownTooltip. One CROSS-LANE item: `WorldState.from_graph()` (src/babylon/models/world_state.py:505 — E-lane file, W must NOT edit) crashes on community/faction/sovereign nodes — the brief tells the W agent to assess whether its bridge path triggers it and flag, not fix. |

### PENDING (in dependency order)

- **#8 W:094 The Wire** (deterministic narrator; deps 090+092 ✅ — dispatchable once W:093 fix lands, W lane is serialized) — scope at project/09 lines ~256-273.
- **#9 W:095 Endgame chronicle + Journal + Dialectic screen** (after 094).
- **#10 W:103 Trade surfaces in product UI** (deps 101 ✅, 093, 094).
- **#13 D:068 completion slice** — ⚠️ SEQUENCING FINDING (Wave 8): the remaining work
  (hex_hydrator wiring T056–T058 in `specs/068-bea-national-io-ingest/tasks.md`) is
  **baseline-changing** (SC-005 requires terminal stddev(c/v)≥0.2) and touches
  **engine files** (`src/babylon/engine/factories.py`) → it is E-lane-sequenced, NOT
  a concurrent D task. Slot it before/with E:104. (spec-068 ground truth: US1/US2/US4
  done, US3 partial — the tasks.md checkboxes are stale; tables populated:
  fact_bea_national_industry=1065 rows, fact_bea_io_coefficient=131,239 rows.)
- **#16 E:104 National tick-compute profile + budget** (after 102 closes + 068-hydrator).
- **#18 hex_spatial_map hardening** (session-scoping / find the truncating test) — MUST land before #17.
- **#17 E:105 National canonical acceptance** (last; deps 104, 101/102, 068, 096 ✅, #18).

______________________________________________________________________

## 4. The working method (follow it — it caught real bugs every single time)

Per spec: (1) dispatch a **fresh implementer subagent** with a scoped brief
(worktree, branch-off point, ownership boundaries, gates, TDD, "commit per unit");
(2) when DONE, generate a review package:
`~/.claude/plugins/cache/superpowers-marketplace/superpowers/6.1.1/skills/subagent-driven-development/scripts/review-package BASE HEAD`
(BASE = recorded pre-dispatch commit, never HEAD~1);
(3) run an **adversarial multi-dimension review** (5-6 domain-specific finder agents
→ every non-minor finding gets 2 independent refuter agents; CONFIRMED = 0 refutes,
PLAUSIBLE = 1, REFUTED = 2); (4) orchestrator adjudicates (some findings are
correct-by-design — check the spec/ADR text before accepting), writes a fix brief to
`.superpowers/sdd/reports/<spec>-fixes.md`, dispatches a fix agent; (5) verify the
fix (spot-check the highest-value items yourself with grep/SQL — don't just trust
the report), then mark complete and update the ledger.

Reviews are READ-ONLY when a DB is in use by another lane. Reviewers may run
read-only SQLite queries against the reference DB — that's how the two data bugs
(0-vs-None, alpha double-count) were caught.

Track record (why you should keep doing this): every single review found real,
verified defects that green test suites missed — a `VARCHAR(12)` column that made a
feature silently 100% broken with 255 green unit tests; a `0-vs-None` conflation;
tautological conservation gates; a proof document laundering inherited drift; a
zeroed canonical baseline about to be committed; de-fixture queries that return
empty in every real game.

______________________________________________________________________

## 5. Key artifacts index

- **Ledger (read first):** `/home/user/projects/game/babylon/.superpowers/sdd/progress.md`
- **Master plan:** `project/09-program-full-game.md` (lane law §3, spec catalog §2, per-spec protocol §4)
- **State docs:** `project/00-mission.md`, `project/01-state-of-the-world.md`
- **Pending fix briefs (the immediate work):**
  - `.superpowers/sdd/reports/102-fixes.md` (E:102 — not started)
  - `.superpowers/sdd/reports/093-fixes.md` (W:093 — not started)
- **Completed fix briefs + reports** (patterns to copy): `.superpowers/sdd/reports/{096,099,100,101,092,098,091}-fixes.md` and `{spec}.md` fix reports (some live in the worktree's own `.superpowers/sdd/reports/`)
- **Review packages:** `<worktree>/.superpowers/sdd/review-<BASE>..<HEAD>.diff`
- **Canonical archives:** sessions `edf07b2e-…` (071) and `a8202ed0-…` (101) under `/media/user/data/babylon-archives/`

______________________________________________________________________

## 6. Owner-review queue (present to Percy; do NOT act without her ruling)

1. **Article VII Cold Collapse amendment** — drafted at `specs/090-cold-collapse/article-vii-amendment.md` (Amendment M; includes the alarm-terminal luminance exception §66-67).

Percy approves this.

2. **E:071 fascist_alignment ratchet** — monotonic by deliberate I.7 design; should sub-threshold alignment decay when hegemony is restored?

For now, just monotoic and we can expand as necessary. Nail the basic mechanics first before getting more complex. - percy

3. **E:101 `_NODE_TO_BLOC` Φ-attribution crosswalk** — ratify/adjust (india/latin_america→Φ=0; russia_csi→Europe weak). Changing it reopens the 101 proof window.

I ratify this - percy

4. **E:101/104/105 scope-renorm drain magnitude** — sub-national runs absorb the FULL national bloc Φ_week (~84-141× county output); is national scope required for meaningful magnitudes?

Yes, national scope is required and ideally international scope as well bc colonisation! - percy

5. **SYSTEMIC: III.7 determinism-hash gate is non-functional for cross-run verification** (O:099 + E:102 both proved it). Genuine content hash needs a schema change; value-comparison is the current honest workaround.

Approve - percy

6. **O:099** — hash pane honestly relabeled "STRUCTURE OK" (content verify impossible from pane data); hex/ archive endpoint 501 (hex_spatial_map not exported). Want the schema changes to enable either?

Yes, I approve teh schema change - percy

7. **D:098 Oakland conflict** — LODES data says Oakland County is a net job IMPORTER (residence 554,099 < workplace 696,243); 3 tests assume exporter, left honestly failing. Correct tests vs investigate data?

Investigate data to confirm, then correct based on findings - percy

8. **W:093 balkanization seed gap** — the map political lenses work but NO scenario seeds spec-070 balkanization data (seed_influences.json pipeline never built) → live game shows "no data". In scope for "game works locally"?

Yes, this is in scope! - percy

9. **E:102 gamma shipped-but-inert** — hydration works but TickDynamicsSystem is unwired in the canonical runner; wiring it changes the baseline (needs a proof window). Wire now or later?

Wire now or at some point duringf your work whenever it makes sense - percy

10. **spec-100/101 trade column naming** — loader wrote `bilateral_trade_value` (USD); program text said `bilateral_trade_tons`. USD ruled correct by data; confirm.

Confirmed - percy

11. **W:092 minor** — eventClassifier UPPERCASE-key casing still affects the legacy notification tray (small recast, deferred); journal-event id UUID5 mismatch (latent).

Fix it however you see best fit. No need to worry abouty backward compatibiliyty - just fix it! - percys ruling

______________________________________________________________________

## 7. Exact resume checklist (in order)

1. Read `.superpowers/sdd/progress.md` (Waves 1–14) for full context.
1. **E:102 fix pass**: worktree `e101`, branch `102-gamma-shocks` @ `70e6512a`, brief
   `.superpowers/sdd/reports/102-fixes.md`. TDD, commit per unit, then
   `mise run qa:e2e-regression` (Δ=0.000%) + `mise run check`. Then verify (targeted
   re-review or orchestrator spot-checks: the alpha fix must exclude overlapping
   blocs — check with SQLite; the manifest hash must change when shock_schedule changes).
1. **W:093 fix pass**: worktree `w090`, branch `093-territory-org-detail` @ `24fc95f3`,
   brief `.superpowers/sdd/reports/093-fixes.md`. The agent must derive correct node
   types/attributes/enums from the ENGINE's writing code (spec-070 systems,
   src/babylon/models enums) — not guess. Gates: `mise run web:check`,
   `PYTHONPATH=src poetry run pytest tests/unit/web/ -q`, Playwright lens-cycling,
   `rg '26163' web/game/engine_bridge.py` stays clean. Then re-review (the 12-finding
   review means the re-review should be a full adversarial pass, not a spot-check).
1. Handle the W:093 cross-lane flag: if the bridge triggers the `from_graph()` crash
   on faction/sovereign/community nodes, open an E-lane task to add those branches
   (E-lane file: `src/babylon/models/world_state.py`).
1. Then continue the lanes: W:094 → W:095 → W:103; E: close 102 → 068-hydrator slice
   (baseline-changing; E-sequenced) → 104 → #18 hardening → 105.
1. Keep updating `.superpowers/sdd/progress.md` (append waves), the task list, and
   the owner queue. Commit only in worktrees, never to dev/main.
1. When all specs are done: final whole-branch reviews per lane, then present the
   owner queue + branch list to Percy for BD merge.

## 8. Session-scoped constraints that still bind

- **Goal (Stop-hook)**: "`project/` fully implemented" = Program 09 executed to done.
- Subagents run on **Sonnet** (`model: 'sonnet'`) — Opus/lead orchestrates only (token economy).
- Ultracode/adversarial-review discipline stays ON for all substantive work.
- Never touch `design/mockups/**` (read-only canon), never `git -C`, always ripgrep.
- The 5 owner decisions in project/07 are RULED — don't relitigate.
- If a subagent dies mid-task: its committed work is in git (trees were verified
  clean at handoff); re-dispatch a fresh agent pointed at the same brief; the git
  state + brief file is the context, not the dead agent's memory.
