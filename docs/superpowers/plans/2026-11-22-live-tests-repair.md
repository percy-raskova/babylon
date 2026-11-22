# Repair of the Live Database Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the live PostgreSQL tests of the `reader` and `runtime` focuses pass again, each by
its cause: two tests of the reader focus fail on this branch and on `dev`, and four tests of the
runtime focus have never run under the runner.

**Architecture:** Three small repairs, each traced by reading before this plan was written. One is
a diagnostic span that carries another span's name (the product). One is a test whose own lock
now blocks maintenance that the product does on purpose (the test). One is a group of tests that
need a database nothing creates (the harness). No behaviour of the simulation changes, no table or
view changes, and no stored byte changes.

**Tech Stack:** Rust (`babylon-persistence`), `tools/run_rust_postgres.sh`, PostgreSQL through
the project's own runner.

**Spec:** the documents that state each promise:
`docs/concepts/architecture.rst` (the paragraphs "Graph component views resolve nodes, names and
types through exact lookup IDs" and "A regression holds prior campaign statistics"); the comment
in `rust/crates/babylon-persistence/tests/observer_material_live/runtime_process.rs` above the
count of admissions ("Existing FoundationAdmission timings therefore count only this actual
Open"); and the four tests named in Task 3 with their own comments.

## What was traced (2026-11-22, by reading; the failing runs are on record)

| Test | What fails | Cause | Since |
| --- | --- | --- | --- |
| `runtime_process::live_runtime_child_open_admits_one_foundation_without_changing_world` | counts 2 lines of `stage=FoundationAdmission` at tick 0, expects 1 | `reconstruct_material_foundation` starts two timing spans with the stage `FoundationAdmission`: one around the catalog, one around the admission. One Open prints both. | `39de111ba` (2026-10-25) added the second span |
| `tick_components::graph_reads_resolve_exact_ids_with_prior_campaign_statistics` | lock timeout, SQLSTATE 55P03 | The test holds `SHARE UPDATE EXCLUSIVE` on five tables to keep background `ANALYZE` out. Since PER-364 the product runs `ANALYZE` on those tables inside the commit of a campaign's first period. That statement needs the same lock mode, waits five seconds and is cancelled. | `aeede4e68` (2026-11-11) added the refresh |
| four `runtime::live_tests::live_event_*` tests | panic "the fixture variable is bound: NotPresent" | They read `BABYLON_EVENT_COPY_DATABASE` and require a database named `per337_event_continuity_*`. No tracked file sets the variable or creates such a database. | `18a3176c3` (2026-10-04) wrote them so |

Both commits of the first two rows are on `dev`. The reader focus was run twice on 2026-11-21.
Both times its first suite passed (`reader_role_live`, 7 tests) and its second failed
(`observer_material_live`: 24 passed, 2 failed, these two, in about 520 of its 600 seconds). Do
not spend a run on seeing them fail again.

The runner stops the reader focus at the first suite that fails. So its last part, the production
history tests, has not run in any of those runs. The repaired focus will go on to them: a longer
run, and whatever they show is new information.

## Global Constraints

- Work only in `/media/user/dev-ssd/worktrees/households-homes/babylon`, branch
  `codex/households-and-homes`. Start every shell command with `cd` to it (or to its `rust/`).
  Never push. No `.env`, no `uv.lock`.
- One cargo, mise or test process at a time on the whole machine. Never pass `-j`. Only
  `mise exec -- cargo ...` and `mise run ...`.
- **Live tests run only through the project's runner:**
  `BABYLON_POSTGRES_LIVE_FOCUS=<focus> mise run test:rust-postgres`. It starts and removes its own
  PostgreSQL. Never point a test at a play database, never run `mise run db:up`, never run `psql`
  against anything the runner did not start. A focus run takes 4 to 17 minutes: run it in the
  background with a log and wait for its end marker.
- **No test is made green by looking away.** No test is deleted, marked ignored, skipped when a
  variable is unset, or dropped from a runner filter. No assertion that states a promise is
  loosened. An expected value changes only where this plan says so in words.
- **The product's statistics refresh is not touched** (`refresh_first_publication_statistics` in
  `src/material_runtime/runtime.rs`): not removed, not moved, not made to tolerate a timeout. No
  timeout of the writer or the reader is raised.
- **Nothing stored changes.** No file under `rust/crates/babylon-persistence/migrations/`
  changes, and none under `babylon-tick`, `babylon-material-circuit`, `babylon-bsl` or
  `babylon-graph`. A saved world and a state hash keep every byte.
- Every line number is a hint; find each place by its text. If the code differs from what this
  plan says was traced, stop on that task and report the difference with the lines.
- **Scoped gate, run by every task before its last commit,** one leg at a time, from `rust/`:
  `mise exec -- cargo fmt --all -- --check`;
  `mise exec -- cargo clippy -p babylon-persistence --all-targets --locked -- -D warnings`;
  `mise run rust:test:q -- -p babylon-persistence`; and the live focus the task names.
- Commit: `git add <files>`; message in a file; `PYTHONPATH=src mise exec -- git commit -q -F
  <file>`; then check `git log --oneline -1`. Each message ends with `Part of PER-371`.

## Review Focus

1. A repair that turns a test green by weakening it: a count changed to 2, a lock removed with
   nothing in its place, a read moved to a state where it cannot fail.
2. A change to what the product does at a campaign's first period, or to any timeout.
3. A new database fixture that could ever be pointed at a database holding a player's campaign:
   the destructive tests of Task 3 must refuse any name without their test prefix.
4. A runner change that alters another focus: every other focus keeps its filters and its phases.
5. A figure written into a document that was not measured in this work.

## File Structure

| File | Change | Task |
| --- | --- | --- |
| `rust/crates/babylon-persistence/src/production_projection/diagnostics.rs` | one new stage name | 1 |
| `rust/crates/babylon-persistence/src/material_runtime/runtime.rs` | the catalog span uses it | 1 |
| `rust/crates/babylon-persistence/tests/observer_material_live/tick_components.rs` | the stale-statistics test, reordered and renamed | 2 |
| `docs/concepts/architecture.rst` | the paragraph on that regression | 2 |
| `tools/run_rust_postgres.sh` | the `reader_recovery` focus names the renamed test (2); the event tests' database, if Task 3 decides so (3) | 2, 3 |
| `rust/crates/babylon-persistence/src/runtime.rs`, `src/event_storage/store.rs` | the event tests' fixture | 3 |

---

### Task 1: One name for one span

**Files:**
- Modify: `rust/crates/babylon-persistence/src/production_projection/diagnostics.rs` (`enum Stage`)
- Modify: `rust/crates/babylon-persistence/src/material_runtime/runtime.rs`
  (`reconstruct_material_foundation`, the span `catalog_timing`)
- Test: the existing live test, unchanged:
  `runtime_process::live_runtime_child_open_admits_one_foundation_without_changing_world`

**Decisions:**
- The span around `admitted_material` gets its own stage, `FoundationCatalog`, placed in the
  enum beside the other `Foundation*` stages. The span around `from_parts` keeps
  `FoundationAdmission`. No span is removed and no span is merged.
- The test is not edited. Its count of 1 is the promise: one Open reconstructs its foundation
  once.
- Before the change, search the repository for any reader of stage names
  (`rg -n "stage=Foundation|FoundationAdmission" --glob '!rust/crates/babylon-persistence/src/**'`).
  On 2026-11-22 the only hit was the test itself. If a tool or a document lists the stages, add
  the new name there in the same commit.

- [ ] **Step 1: Make the change** in the two files.
- [ ] **Step 2: Run the scoped gate** without the live leg. Expected: PASS.
- [ ] **Step 3: Commit** `fix(persistence): name the catalog span of a foundation's
  reconstruction apart from its admission`. The body says that one Open printed two lines under
  one stage name since `39de111ba`, and that the live test counts those lines. The live run is
  Task 2's last step, which covers both tasks.

---

### Task 2: The stale-statistics regression after the first-publication refresh

**Files:**
- Modify: `rust/crates/babylon-persistence/tests/observer_material_live/tick_components.rs`
  (the test `graph_reads_resolve_exact_ids_with_prior_campaign_statistics`)
- Modify: `docs/concepts/architecture.rst` (the paragraph that begins "A regression holds prior
  campaign statistics")
- Modify: `tools/run_rust_postgres.sh` (the `reader_recovery` focus lists this test by name)

**What the test promises, and what changed under it.** The graph views resolve nodes, names and
types through exact lookup ids, so that statistics which do not describe the rows read cannot
make the planner multiply whole lookup tables. The test held the statistics of an earlier
campaign while a fresh campaign committed its first period, then read that period under a
five-second ceiling. Since PER-364 the commit of every campaign's first period refreshes those
statistics itself. A new campaign has no graph rows to read before that commit (`graph_storage::
seed` writes lookup rows only: "no tick-zero memberships exist"). So the state the test built
can no longer be reached through the product, and its lock now blocks the product's own
statement.

**Decisions:**
- The state that CAN still be reached is tested: the statistics of the first publication, and a
  read of a later period that those statistics have never seen. The order becomes: the first
  campaign commits one period; the fresh campaign is created and commits period 1 through the
  product, with the product's refresh; THEN the guard transaction takes the same lock on the same
  five tables in the same mode, so that no later `ANALYZE` can change the statistics; then the
  fresh campaign commits period 2 (the product refreshes at period 1 only); `expected` is the
  fresh session's stable graph state after period 2; both reads ask for `resolve_tick=2`. The
  ceilings, the read-only transaction, `jit=off`, the exact comparison of rows and the printed
  line stay as they are.
- The test's own `ANALYZE` of two lookup tables goes: the product's refresh at the fresh
  campaign's first period now sets the statistics the test holds. Its comment is rewritten to say
  what is held and why.
- The test is renamed `graph_reads_resolve_exact_ids_at_a_period_its_statistics_have_not_seen`.
  On 2026-11-22 the old name stood in two places: the test, and the list of the runner's
  `reader_recovery` focus. Search again and rename every mention in the same commit. The runner
  changes by that one name only.
- **The test must be shown able to fail.** One throwaway run, not committed: install the earlier
  form of the two views (`v_observer_graph_node_v1`, `v_observer_graph_node_f64_v1`) under
  other names in the test's database, taken from the history of
  `rust/crates/babylon-persistence/migrations/` (`git log -S'v_observer_graph_node_v1'` finds the
  commit that revised them), and read period 2 through them under the same guard. Report the
  result as it is, whichever it is:
  - the earlier views exceed the ceiling: say so, with the time;
  - the earlier views pass: say so plainly, with the time. The test then pins exact rows and the
    ceiling at a state the product reaches, and the case of whole lookup tables multiplied is
    covered by the product's refresh, which has its own live test
    (`assert_first_publication_statistics` in `src/runtime.rs`);
  - the earlier views cannot be installed against today's tables: say what stopped it. Invent no
    control.
- `docs/concepts/architecture.rst`: the paragraph keeps its history in one sentence (the original
  read timed out at five seconds under an earlier campaign's statistics; the revised views
  returned 1,696 nodes in 26 ms and 8,800 attributes in 60 ms; the control took 30.04 seconds) and
  then says what holds now: that the first publication refreshes statistics, what the regression
  holds and reads today, and the figures measured in this work, the control's result included.
  No figure that was not measured here is written as present.

- [ ] **Step 1: Rewrite the test** as decided.
- [ ] **Step 2: Run it.** `BABYLON_POSTGRES_LIVE_FOCUS=reader_recovery mise run test:rust-postgres`
  (about 4 minutes; on 2026-11-21: 5 passed, 1 failed, this one). Expected: 6 passed, and this
  test prints its line with both times.
- [ ] **Step 3: The control,** one throwaway run as decided. Restore the tree afterwards
  (`git status --short` shows only this task's files).
- [ ] **Step 4: Rewrite the paragraph** in `docs/concepts/architecture.rst`, then run
  `mise run docs:strict` once (the documents built with warnings as errors, as CI does). Expected:
  PASS. If it fails on a warning that this paragraph did not cause, report the warning and leave
  it.
- [ ] **Step 5: The whole reader focus, once.**
  `BABYLON_POSTGRES_LIVE_FOCUS=reader mise run test:rust-postgres`. Expected: `reader_role_live`
  7 passed; `observer_material_live` 26 passed, the test of Task 1 among them; then the production
  history tests, which run now for the first time since these failures began. Give every suite's
  counts and times. If `observer_material_live` now runs past its limit of 600 seconds, or a
  production history test fails, stop and report it with the output: raise no limit and repair
  nothing beyond this plan.
- [ ] **Step 6: Run the scoped gate and commit** `test(persistence): hold first-publication
  statistics in the stale-statistics regression`. The body says what the product does since
  PER-364, why the old state cannot be reached, what the test holds and reads now, and the
  control's result.

---

### Task 3: The event tests get their database

**Files:**
- Modify: `rust/crates/babylon-persistence/src/runtime.rs` (`event_control_config` and its
  users in the test module) and `src/event_storage/store.rs` (the two other readers of the
  variable), or `tools/run_rust_postgres.sh`, as the first step decides

**What is known.** `event_control_config()` reads `BABYLON_EVENT_COPY_DATABASE`, asserts that it
starts with `per337_event_continuity_`, and uses it as the database's name. Four tests of the
runner's `runtime` focus call it (`runtime::live_tests::live_event_*`), and two tests in
`src/event_storage/store.rs` read the same variable. Only those three places mention the
variable. The tests have never run under the runner.

**Decisions:**
- **Step 1 decides between two forms, by what the tests need.** Read the six tests and
  `event_control_runtime` first.
  - If they need only an empty database with the current schema, they make their own: the same
    disposable fixture the other live tests of this crate use (the test above them ends with
    `database.cleanup()`), under a name that starts with `per337_event_continuity_`. The
    variable goes away.
  - If they need a database prepared with data that only the runner can prepare, the runner's
    `runtime` phase creates it from the bootstrapped schema, names it
    `per337_event_continuity_<the run's own suffix>`, exports the variable for that phase only,
    and removes it with the rest.
  - If they need a history that neither can make (a copy of a real campaign's events, say),
    stop: return blocked with what they need. Do not write a fixture that pretends.
- The prefix check stays in force in either form. These tests run destructive `COPY` controls,
  and the prefix is what keeps them off a database that holds a campaign.
- The two readers in `src/event_storage/store.rs` get the same treatment. Find which focus of
  the runner selects them; if none does, say so in the report and add them to the `runtime`
  focus only if their names already match its filter's intent (`live_`). Change no other focus.

- [ ] **Step 1: Read and decide,** and write the decision with its reason in the commit message.
- [ ] **Step 2: Make the change.**
- [ ] **Step 3: Run** `BABYLON_POSTGRES_LIVE_FOCUS=runtime mise run test:rust-postgres`.
  Expected: every test of the focus passes, the four `live_event_*` among them. Give the counts.
- [ ] **Step 4: Run the scoped gate and commit** `test(persistence): give the event continuity
  tests a database the runner can make`.

---

## Self-review notes

- Each task repairs the side that is wrong by its cause: the product's label (1), the test's
  setup (2), the harness (3). None changes what a campaign stores or computes.
- Task 2 keeps a control, so the reordered test is not taken on trust.
- Task 3's unknown is named and has a stop instead of a guess.
