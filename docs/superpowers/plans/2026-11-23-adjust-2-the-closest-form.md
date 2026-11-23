# The Closest Form (rules of ADR314 measured in ten rounds) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build into the engine the form the Director picked on 22 November 2026: "a bound on hiring; people
look for work in their place; no money, no work; resting price, mended restart; a goods price steps down, to its
cost and no lower". Behind a setting no campaign asks for yet. Each rule reproduces its rows of the test economy
before it merges.

**Architecture:** Six rules, each asked for by one entry in a new list on the catalog's market policy, as rule A6
is asked for by its flag. A catalog that does not ask runs today's code and keeps every byte. The rules sit where
the prototypes acted: the bound at the end of the close's plans; the restart and its mends at the very end of the
close; the stop rule and the seekers in a new staffing step of the closed period; the resting price and the step
down inside today's price rules. What a rule remembers from one period to the next lives with the caller, as
persons do. The bench that measured the rules becomes a test binary of the crate, `tests/adjustment_bench.rs`,
and every rule task ends by reproducing a set of its rows byte for byte.

**Tech Stack:** Rust (`babylon-material-circuit` only); `contracts/material_circuit_v4.yaml`.

**Spec:** `docs/superpowers/specs/2026-11-21-how-the-economy-adjusts-design.md`, rules A1, A6, A14, A17, A19 and
sections 6 and 8; `ai/decisions/ADR314_how_the_economy_adjusts.yaml`, `ADR318_who_carries_a_losing_workplace.yaml`
(L1), `ADR319_a_shock_is_not_a_failure.yaml` (J1 to J6). Records:
`reports/economy-repair-2026-11-20/restoring-forces/round-8.md` to `round-10.md`. The prototype is the scratch
branch `spike/r10-P` (head 3944ee9f3) and, after Task 0, `spike/closest-ref`. It shows where each rule sits and
what it computes. It is not the code to ship. Builders read it only with `git show <branch>:<path>`.

**When it is built (ADR320, 23 November 2026).** The Director ruled "screen first": the small world
runs in the client first, then the bridge is built, then this plan, each rule visible when it lands.
Task 0 may run earlier, whenever the build machine has a free turn, because it changes nothing in the
repository and its gate decides whether the plan stands.

**The road to the screen.** The client's scene of the small world
(`docs/superpowers/specs/2026-11-23-the-small-world-in-the-client-design.md`) runs the engine itself, so a
rule is seen there as soon as its task lands. Each rule task therefore has a companion task in the client,
written when the scene exists: the rule becomes a named switch of the scene, off by default, and its
receipts become marks (a move of people between workplaces; a workplace that rests; an owner's money
going in; a price that came down, in the table). A rule task is not done until its switch is on screen.
What a campaign needs before it may ask for these rules is under "Stored format" below.

**The bench's drive.** `BENCH` below is `/media/user/dev-ssd/babylon-bench/restoring-forces`: the rows of
every measured set (`out/`), the scripts that ran them (`scripts/`) and the lead's counters (`k-scripts/`).

**Stored format: the state frame is not stopped.** No field is added to `MaterialCircuitState`, so the state's
versions (22, 24, 25, 26) and every state byte stay. Every state struct is built by struct literals in
`babylon-tick` and `babylon-persistence` (for example `babylon-tick/src/material_world/service_receipt.rs:484`,
`babylon-persistence/src/economic_catalog/compile.rs:527`), so a new state field would change those crates, which
this plan may not do. What changes:

| What | Kind | Cost |
| --- | --- | --- |
| `MarketClearingPolicy.adjustments` | catalog field | catalog version 9 and the rule list, written first, only when the list is not empty; contract lines and `MATERIAL_CIRCUIT_SOURCE_SHA256` (Task 2) |
| `MaterialCircuitTransition.adjustments` | receipts | a new `Vec<AdjustmentReceipt>`, empty unless the catalog asks; not encoded by this crate (Task 3) |
| `WorkplaceStanding` | caller-owned memory | a value the caller keeps between periods, like `StaffingState`; never in the state frame (Task 5, Task 7) |
| member rows of other workplaces | opening state, existing row kinds | the world authors one `EmploymentTerms` and one member row for each household at each workplace of its place (Task 3); no new kind |
| the restart's money | an existing kind of movement | `CashTransferPurpose::CapitalContribution`, with its `MoneyTransferReceipt` (Task 7) |

What that means for a campaign. `babylon-persistence` compiles every campaign catalog with `market_clearing: None`
(`economic_catalog/compile.rs:76`), so no campaign can ask. `babylon-tick` refuses every stored period with market
clearings or tier rows (`material_world/register.rs:1897-1907`) and does not encode `adjustments`, closes through
`close_material_period_with_portfolios` (which, from Task 5, refuses a catalog that asks for the stop rule, and so
the restart, which needs it) and finishes with `finish_with_workforce`. Before a campaign asks, that wiring
must: build the policy in the compiler; store the new receipts, or refuse a transition that has them; keep
`WorkplaceStanding` and the members of each household at each workplace beside the persons it already keeps; call
`staff_in_places`. And its price-receipt check must accept the receipts named in Tasks 7 and 8. None of this is in
this plan.

**Where the built rule departs from the prototype.** Each item says how the reference rows are kept exact.

1. **The game's engine moved on after the prototype forked.** `spike/r10-P` left the game's branch at cb4761200.
   Eleven commits to the engine's `src/` came after (`git log cb4761200..f93b3beaa --
   rust/crates/babylon-material-circuit/src`), none of them on the prototype: among them rule A6 itself
   (08e06ce14 to 125d6dbf6 and 389bd1c32), the wage tax by payee (5f1db9c22), public programs (f20e069cb), the
   market table without squares (4cd2a237e) and the five explicit checks (9e43c949e). No set of rows that exists
   was made by the engine the rules are built on. Task 0 merges the game's branch into a copy of the prototype and
   remakes every reference set there. The prototype's rule F2 is not the game's A6, and the bound and the step
   down call F2-era code; Task 0's C3 states how the merge keeps both, and its P4 and decision 3 prove it.
2. **The doubled bench rewrote the engine's identity digests.** `spike/r10-P` `src/spike_t.rs` makes the second
   copy's buyers and members queue as the first copy's do, by digesting old identities and flipping a bit. That is a
   measuring aid inside the engine, and nothing of it is built. Task 0 adds one switch that leaves it unregistered
   (`spike_t.rs` is then inert, byte for byte, by its own doc comment) and makes every reference set with it.
3. **The step down stops at cost.** The prototype stops at the policy minimum, $1 (`spike/r10-P`
   `src/recurring/prices.rs:436-439`). Task 0 adds the cost floor to the prototype behind a switch, proves the
   switch off changes nothing, and judges the new sets by the Director's test before anything is built.
4. **The step down is for goods only.** The prototype's `SPIKE_DOWN` also moves services: a provider quotes before
   it plans and plans for buyers at a lower price (`services/market.rs:408, 596-610` on `spike/r10-P`). The
   Director's words and D1 name goods. Task 0 makes the reference with the prototype's own `SPIKE_DOWN_GOODS=on`,
   which leaves services as they are without the rule. Round ten measured that form: "The same, with the step down
   for goods only | no credit | 0 and 0 | 436 and 440 | nothing" (`round-10.md` section 2). It is one of the six
   forms that pass the Director's test at both sets of figures. Building it, and not the form with the service
   part (439 and 443 hours), is the lead's reading of the Director's words, reported to them on 23 November.
5. **The comparison leaves out every column whose name begins `flow_`.** They are written only in runs where they
   fired, from records the prototype kept in thread-locals; rule A6 as built writes none of its own. Every flow is a
   change in, or a record behind, a column that is compared (cash, prices, hours, people, the bound, the restart's
   test, the goods unsold). Task 0 and the bench use the same projection (Task 1, decision 4).
6. **Order by explicit rule, not by identity.** The bound reckons a service provider before its buyers because the
   utility's process id sorts first (`spike/r10-P` `src/spike_bound.rs:232-236`). The built bound orders processes
   so that every provider comes before its buyers, ties by process id. On the bench that is the same order.
7. **Wages, hours per person and places are read from the engine, not from the fixture.** The prototype reads the
   opening wage and `world.hours_per_person` from the test world. The built rules read the largest `Wage` rate of a
   site's employment terms and each pool's `hours_per_person`; the caller names the pools of each place. On the
   bench these are equal, since no pay rule runs.
8. **Moves are their own receipts.** The prototype rewrites member receipts so that a move looks like a hire
   (`seek_hands`, `support.rs:741-779`). The built rule publishes the staffing decision as it is and a receipt
   for each move, and advances the record of layoffs internally with the same arithmetic.
9. **Money moves with a receipt.** The prototype's restart edits the book and the cost book after the close and
   writes no receipt (`support.rs:3773-3845`); its mend edits offers without the price receipt
   (`support.rs:3605-3610`). The built rule writes a `MoneyTransferReceipt` and its own receipt, and updates the
   period's price receipt. None of these is a compared column.
10. **The rules' memory lives with the caller, not in the stored state.** `WorkplaceStanding` and the members of
    each household at each workplace are kept by the caller between periods, so a stored `MaterialCircuitState`
    no longer holds all of what the rules remember. `notes-bench.md` item 8 says this memory belongs in
    `MaterialCircuitState`. It is accepted here because no campaign can ask for these rules, and it is a debt:
    before a campaign asks, the memory moves into the state frame (a new state version) or the wiring listed above
    stores it beside the persons. The reference rows do not depend on where it lives.

If any task's long test cannot reproduce its set and the cause is not in that task's code, stop and report.
Nothing is bent to match.

## Global Constraints

- Work only in `/media/user/dev-ssd/worktrees/households-homes/babylon`, branch `codex/households-and-homes`. Start
  every shell command with `cd` to it (or to its `rust/`). Never push. No `.env`, no `uv.lock`.
- One cargo, mise or test process at a time on the whole machine. Never pass `-j`. Only `mise exec -- cargo ...`
  and `mise run ...`. A build in another checkout empties this one's cache: launch long tests with `--no-build`
  after a build when the lead says another checkout is building.
- No pinned value of an existing test changes. No assertion is loosened. The small world's runs
  (`tests/small_world/`) keep every figure. If one must move, stop and tell the lead.
- Money is `i128` millionths of a dollar (`Currency`); quantities and hours are `u64`; arithmetic is checked and a
  failure is a typed error (`MaterialCircuitError` or `StaffingError`), never a panic or a wrap. Saturation only
  where these decisions name it.
- No environment variable and no name beginning `SPIKE` or `spike` anywhere under `src/` or in the bench.
- A contract line that changes is changed with its pinned digest (`MATERIAL_CIRCUIT_SOURCE_SHA256` in
  `src/wire/state.rs`) in the same commit. The digest is the SHA-256 of the file's bytes; one test checks it
  (`tests/weighted_freight.rs`, near line 382). Edit the yaml last, then compute the digest. The contract is
  linted on commit with a limit of 120 characters a line.
- Functions stay under 100 lines and a cognitive complexity of 25 (`rust/clippy.toml`). No `unwrap`; an `allow`
  or `expect` attribute carries a `reason`. Import a type and use its bare name (bsl-sentinels refuses a
  module-qualified type used inline). No `mod.rs`; a non-leaf module holds only `mod` and `pub use`.
- Every line number is a hint; find each place by its text.
- **Scoped gate, run by every task before its last commit,** one leg at a time: from `rust/`,
  `mise exec -- cargo fmt --all -- --check`; `mise exec -- cargo clippy --workspace --all-targets --locked --
  -D warnings -D clippy::cognitive_complexity`; `mise run rust:test:q -- -p babylon-material-circuit`;
  `mise run rust:test:q -- -p babylon-tick`; `mise run check:bsl-sentinels`. If a task changes anything under
  `tools/`, `.mise.toml` or `.github/`, also the Python unit tests that read it (no task here does).
- **The long tests.** Ignored by default. Run once at the end of the task, in the background, in one cargo
  process: `mise run rust:test:q -- -p babylon-material-circuit --test adjustment_bench -E
  'test(/^reproduces_/)' --run-ignored only`. This runs every set built so far: a later task must not change an
  earlier form's rows.
- Commit: `git add <files>`; message in a file; `PYTHONPATH=src mise exec -- git commit -q -F <file>`; then check
  `git log --oneline -1`. The body ends with `Part of PER-371` and a `Co-Authored-By` line naming the model that
  wrote the commit.
- Scratch branches named `spike/...` are never merged, cherry-picked or switched to in this worktree. Read them
  only with `git show <branch>:<path>`, `git grep` and `git diff`. A step that must run a prototype names the
  branch, the switches and the command; the lead runs it or hands the builder the build slot.

## Review Focus

1. **A catalog that does not ask moves.** Every rule is behind one `if` on its entry of `adjustments`. An empty list
   writes today's catalog bytes. Pinned by Task 2's catalog tests and by every existing test passing unchanged.
2. **The quiet world moves.** At the opening every workplace holds exactly one period of its outlay, so the bound's
   money test is an equality (utility 120 h x $10 = $1,200; farm 4 x (10 h x $10 + 10 x $12) = $880; clinic
   40 x (1 h x $10 + 1 x $12) = $880). A `<` for `<=` cuts the quiet world. Pinned by Task 4's unit test and by
   each task's 34-period quiet test.
3. **Money is created or lost.** The restart is the only rule that moves money. Pinned by the bench's assertion
   that total money equals the opening in every period of every run (Task 1) and by Task 7's receipt test.
4. **People are created or lost.** Seekers move between members of one place. Pinned by the bench's assertion that
   each copy's persons equal the opening's in every period (Task 3) and by the staffing receipts' own `validate`.
5. **The projection hides a difference.** Only `flow_` columns are left out (departure 5). The projection is one
   function, used on both sides. Pinned by Task 1's `the_projection_drops_only_flow_columns`.
6. **An accident of order.** Bound order (departure 6), host order (highest wage, then most lacking, then site),
   seeker order (uncovered first, then covered by cohort age), restart order (earn over plan, then site). Each is
   pinned by the bench's rows; each is stated in its task.

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `rust/crates/babylon-material-circuit/tests/adjustment_bench.rs` | The bench binary: modules and the long tests | 1, 3-8 |
| `rust/crates/babylon-material-circuit/tests/adjustment_bench/world.rs` | The doubled world, its runs, the two figures | 1, 3 |
| `rust/crates/babylon-material-circuit/tests/adjustment_bench/run.rs` | One run's period loop | 1, 3, 5 |
| `rust/crates/babylon-material-circuit/tests/adjustment_bench/rows.rs` | The row writer | 1, 3-8 |
| `rust/crates/babylon-material-circuit/tests/adjustment_bench/compare.rs` | Projection, digests, the report of a mismatch | 1 |
| `rust/crates/babylon-material-circuit/tests/adjustment_bench/digests/pc-*.txt` | sha256 of each reference run file | 1, 3-8 |
| `rust/crates/babylon-material-circuit/src/clearing/rule.rs` | `MarketClearingPolicy.adjustments` | 2 |
| `rust/crates/babylon-material-circuit/src/adjustment.rs` and `src/adjustment/*.rs` | The rules' types and arithmetic | 2-8 |
| `rust/crates/babylon-material-circuit/src/staffing/place.rs` | Seekers in their place; the stop rule's limits | 3, 5 |
| `rust/crates/babylon-material-circuit/src/transition/state.rs` | The close's new steps and the closed period's methods | 3-7 |
| `rust/crates/babylon-material-circuit/src/recurring/prices.rs`, `src/clearing/table.rs` | Rest and step down of goods | 6, 8 |
| `rust/crates/babylon-material-circuit/src/services/market.rs` | Rest of a service price | 6 |
| `rust/crates/babylon-material-circuit/src/wire/catalog.rs`, `src/catalog.rs` | Catalog version 9, admission | 2-8 |
| `contracts/material_circuit_v4.yaml`, `src/wire/state.rs` | The rules' text and the digest | 2-8 |

The six engine modules: `src/adjustment.rs` (`mod` and `pub use` only); `src/adjustment/policy.rs`
(`AdjustmentRule`); `src/adjustment/receipts.rs` (`AdjustmentReceipt` and its rows); `src/adjustment/bound.rs`;
`src/adjustment/standing.rs` (`WorkplaceStanding`); `src/adjustment/restart.rs`.

---

### Task 0: The reference sets (the lead runs it; no repository change)

**Where:** a new worktree `/media/user/dev-ssd/worktrees/closest-ref` on a new branch `spike/closest-ref` made from
`spike/r10-P` at 3944ee9f3. Rows go to `BENCH/out/<set>/`. The runner is `BENCH/scripts/r6Trun.sh`
with its `cd` pointed at the new worktree and its output folder at that drive; each set takes about 21 s after
the build.

**Produces:** the fourteen sets below, each 25 files of 401 lines; nine `c2-` sets under `BENCH/c2/`
(decision 3); a note `pc-sets.md` beside them with every proof line (P1 to P4), the hunks of C3 (b) that could not
keep their lines, every explained difference, every count and both verdicts. Nothing in the repository.

**Decisions:**
1. **Three commits, each proven alone.**
   - C1, the floor. `SPIKE_DOWN_FLOOR=cost` (unset or `off` is today's; anything else panics; it needs
     `SPIKE_DOWN=on`). In `quote` (`src/recurring/prices.rs`, near 410), when it is on, both step-down branches
     (`ExcessStock` and `Unsold`) floor at `max(minimum, u)` where `u` is `cost.unit_cost()` of the period, the
     figure the cost-pressure test reads (`valuation/prices.rs` `unit_cost`: carrying cost plus handling wages
     over the quantity produced or released this period, rounded up). When the period has no observation, the
     floor is `minimum`, as rule W's floor is (`prices.rs:436-439`). One flow column, `flow_down_uncosted`, counts
     the step downs that had no observation; it is written only when the switch is on. Proof P1: with the switch
     unset, `r10-P-down-none-400` and `r10-P-down-none-nat-400` are remade and are 25 of 25 byte-equal to the
     sets on the drive.
   - C2, the aliases. `SPIKE_T_ALIAS=off` (unset or `on` is today's) makes the harness skip `register_aliases`
     (`tests/small_world/support.rs:3449`). Proof P2: unset, the same two sets are again 25 of 25 equal.
   - C3, the game's engine. Merge `codex/households-and-homes` at f93b3beaa. This is a port, and its
     resolution is fixed here. The prototype's rule F2 is not the game's A6: 389bd1c32 ("bound a raise by stocked
     inputs only") and the A6 commits after cb4761200 are not on `spike/r10-P`, and F2's `extend` takes the
     service markets and restocking through `ReserveInputs` (`spike/r10-P` `src/recurring/firms.rs`
     `plan_attendance`, near 959) where A6 reads them from `Wanted` (f93b3beaa `firms.rs:493-500, 718-738`).
     Two of the closest form's rules call F2-era code: the bound reads `crate::recurring::spare_money::wages(e)`
     (`spike/r10-P` `src/spike_bound.rs` `compute`, line 151; the function is `spare_money.rs:275` there), and the
     step down's plan gain goes through `plan_production(.., &gains, ..)`, `plan_attendance(.., &gains,
     next_period, &mut reserve)` and `planned_hours(.., gains, ..)` (`spike/r10-P` `src/transition/state.rs`
     `next_plans`, 1184-1259; `firms.rs:764-767, 926-928`). The game's `plan_production` (f93b3beaa
     `firms.rs:541`) and `plan_attendance` (`firms.rs:699`) take neither. The resolution:
     - (a) Every `src/spike_*.rs` file stays byte for byte as on `spike/r10-P`.
     - (b) Every other hunk of `git diff cb4761200..spike/r10-P` keeps its lines; the game's changes are merged
       around them. In the files both sides changed (`clearing.rs`, `clearing/limit.rs`, `clearing/table.rs`,
       `financial/close.rs`, `payments/attendance.rs`, `production.rs`, `recurring.rs`, `recurring/firms.rs`,
       `recurring/households.rs`, `recurring/prices.rs`, `recurring/spare_money.rs`, `services/admission.rs`,
       `services/close.rs`, `services/tiers.rs`, `tiers/lists.rs`, `tiers/records.rs`, `transition/state.rs`,
       `tests/small_world.rs`, `tests/small_world/support.rs`), a hunk that cannot keep its lines is written in
       `pc-sets.md` with the lines and the reason before Step 4.
     - (c) Only rule F2 is dropped, because A6 takes its place: the `if super::spare_money::spike_f2()` block of
       `plan_attendance` and its `SpareRecord`; `extend` and the `as_f_*` switches of the prototype's
       `spare_money.rs`; `spare_plans` and `spare_hours` of the transition (`model.rs:784-788`) and their export
       (`recurring.rs:13`); the harness's `flow_f2_` block (`tests/small_world/spike.rs:106-128`).
     - (d) `src/recurring/spare_money.rs` is the game's file of f93b3beaa with three changes: its private
       `fn wages` (line 162, the largest `Wage` rate of each (site, unit)) becomes `pub(crate)`, so the bound's
       call in `spike_bound.rs:151` resolves to it unchanged; the prototype's `SPIKE_PAY` branch is put back at
       the head of that body (it is the only difference between the two bodies, and `SPIKE_PAY` is unset in
       every set); the readers `spike_f2()` and `spike_pay()` are kept, since the harness reads both.
     - (e) `plan_production`, `plan_attendance`, `planned_hours` and `next_plans` are the prototype's, with
       `gains` and `ReserveInputs` as they are there (`plan_attendance` then returns the reserve plans alone),
       and with the game's A6 block (f93b3beaa `firms.rs:718-738`) in F2's place, gated by the catalog's
       `plans_from_spare_money` and reading `wanted.services` and `wanted.procurement` as the game does
       (f93b3beaa `state.rs:1687-1688`). `gains` stays empty unless `SPIKE_E` or `SPIKE_DOWN` is on, as on
       `spike/r10-P` (`state.rs` `next_plans`, 1203-1213).
     - (f) The harness sets `plans_from_spare_money: true` in its market policy when `SPIKE_F2=on`
       (`tests/small_world/support.rs` `definition`).

     Proof P3: with every switch unset, `mise run rust:test:q -- -p babylon-material-circuit` passes and the
     game's small-world tests keep their figures. Proof P4, which the lead runs before Step 4, and which stops the
     plan if it fails:
     - `git diff spike/r10-P spike/closest-ref -- 'rust/crates/babylon-material-circuit/src/spike_*.rs'` prints
       nothing.
     - A script the lead writes under `BENCH/k-scripts/` reads
       `git diff -U0 cb4761200 spike/r10-P -- rust/crates/babylon-material-circuit/src
       rust/crates/babylon-material-circuit/tests`. For every hunk (the lead's answer of 23 November: every
       hunk, not only those that name a switch), it looks for the added lines, in order and as one block, in
       the same file on `spike/closest-ref`, and prints each hunk it does not find. Every hunk printed is an
       F2 drop of (c), the `wages` change of (d), or a hunk written in `pc-sets.md` under (b). Anything else
       stops the plan.
2. **The sets, at C3.** `BASE = SPIKE_TWO=on SPIKE_F2=on SPIKE_T_ALIAS=off`; `NAT = SPIKE_STEP_BPS=250
   SPIKE_J_PERIODS=2`. Each set is run at the small figures as `<name>-400` and with `NAT` as `<name>-nat-400`:

   | Name | Switches beyond BASE | Built by |
   | --- | --- | --- |
   | `pc-a6` | none | Task 1 |
   | `pc-seek` | `SPIKE_SEEK=on` | Task 3 |
   | `pc-bound` | `SPIKE_SEEK=on SPIKE_BOUND=on` | Task 4 |
   | `pc-stop` | `SPIKE_SEEK=on SPIKE_BOUND=on SPIKE_STOP=on` | Task 5 |
   | `pc-rest` | the same and `SPIKE_REST=on` | Task 6 |
   | `pc-restart` | the same and `SPIKE_RESTART=on SPIKE_MEND=on` | Task 7 |
   | `pc-down` | the same and `SPIKE_DOWN=on SPIKE_DOWN_GOODS=on SPIKE_DOWN_FLOOR=cost` | Task 8 |

   Every intermediate form has a set: no task builds two rules to reach a reference.
3. **Every difference from the old rows is explained.** A set and its old twin of the same rules need not be
   byte-equal: the aliases are off and A6 is in F2's place. So each difference is accounted for, and the old
   rows (tied to `spike/r10-P` by the chain of byte-equal sets in `notes-design.md`) check the merge. The twins:
   `pc-a6` and `r8-ref-none`, `pc-seek` and `r8-seek-none`, `pc-bound` and `r9-bound-none` (both figures);
   `pc-restart` and `r10-M-mend-none` (small only: no national twin exists); `pc-down` and
   `r10-P-down-goods-none` (both figures). To separate the two causes, each of these nine sets is also run once
   at C2, before the merge, as `c2-<name>` (under `BENCH/c2/`; deleted when the plan is built). For each run the lead
   writes in `pc-sets.md`, on the projected rows (Task 1, decision 4): whether `c2-<name>` equals the old twin,
   and if not the first differing period and column and why the aliases (or, for `pc-down` only, C1: a price
   held at cost) change it there; then whether `pc-<name>` equals `c2-<name>`, and if not the first differing
   period and column and the merged commit and code line that explain it. A difference with no explanation stops the
   plan. Also reported, not gated: for `pc-down`, the count of `flow_down_uncosted` over each set; for every set,
   the number of site-periods with `restart_test_` above 0. (The old `r10-P-down-goods-none-nat-400` has none in
   all 80,000 site-periods, so at the national figures the restart's money path may never run; if
   `pc-restart-nat-400` and `pc-down-nat-400` also have none, its proof rests on the small figures and Task 7's
   unit tests, and `pc-sets.md` says so.)
4. **The Director's test as ruled.** Run the lead's counters on every set:
   `python3 -I BENCH/k-scripts/r9_tests.py BENCH/out '^pc-'` then
   `python3 -I BENCH/k-scripts/r10_ruled.py BENCH/out <tests.json>`.
   Record `passes_as_ruled` for each. **Gate:** `pc-down-400` and `pc-down-nat-400` both pass. If either fails,
   stop: the lead takes the rows to the Director, and no task of this plan starts. The other twelve verdicts are
   reported only; their forms are steps, not candidates.

- [ ] **Step 1:** Make the worktree and the branch; write C1; run P1. Expected: 25 of 25, twice.
- [ ] **Step 2:** Write C2; run P2. Expected: 25 of 25, twice.
- [ ] **Step 3:** Before merging, run the nine `c2-` sets of decision 3 at C2. Merge (C3) as resolved there; run
  P3 and P4. Expected: all pass; P4 prints only the hunks it names. Else stop.
- [ ] **Step 4:** Run the fourteen sets; copy them to the drive; write the explanations and counts of decision 3.
  Expected: every difference explained. Else stop.
- [ ] **Step 5:** Run the counters. Expected: `pc-down` passes at both figures. Else stop and report.

### Task 1: The bench in the repository, with no new rule (`pc-a6`)

**Files:**
- Create: `tests/adjustment_bench.rs`; `tests/adjustment_bench/{world,run,rows,compare}.rs`;
  `tests/adjustment_bench/digests/pc-a6-400.txt`, `pc-a6-nat-400.txt`.

**Interfaces:**

```rust
// tests/adjustment_bench/world.rs
/// The figures of a set: a $1 price step and one period of outlay as opening cash (small), or a step of
/// 250 bps of the opening price and two periods (national).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Figures { Small, National }
/// The rules a set runs with. Task 1 has one; each rule task adds the next.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Form { A6 }
/// One of the 25 runs: its file name (`plain-quiet`, ..., `fund-P8a`) and its world. `BenchWorld` is the
/// prototype's `World` as ported (decision 1), with the form's rules and the figures in it.
pub(crate) struct BenchRun { pub(crate) name: &'static str, pub(crate) world: BenchWorld }
/// The 25 runs in the prototype's order: plain quiet, P1, P2, P3, P4, P6, P7, P8, P2a, P4a, P6a, P8a, then
/// fund quiet, P1, P2, P3, P4, P6, P7, P8, P5, P2a, P4a, P6a, P8a.
pub(crate) fn runs(form: Form, figures: Figures) -> Vec<BenchRun>;
// tests/adjustment_bench/run.rs
/// One run of `periods` periods, reduced to its projected rows (header and one line a period).
pub(crate) fn rows(run: &BenchRun, periods: u64) -> String;
// tests/adjustment_bench/compare.rs
/// The file without its `flow_` columns.
pub(crate) fn project(text: &str) -> String;
/// Lowercase hex sha256 of `text`'s bytes (babylon_kernel::content_digest::sha256_of).
pub(crate) fn digest_hex(text: &str) -> String;
/// Panics naming every run whose digest differs from the fixture's, with what decision 6 says.
pub(crate) fn assert_set(set: &str, produced: &[(&str, String)], fixture: &str);
```

**Decisions:**
0. **If the crate of small worlds already holds the doubled world** (`babylon-circuit-worlds`, made by the
   scene's plan under ADR320), the bench takes the world, its opening and its shocks from that crate as a
   dev-dependency, and ports only what the crate lacks: the pushes that are openings (P1, P3, P5, P7), the
   loop and the row writer. The world is then proven here against `pc-a6`; a difference is mended in that
   crate, never in the comparison. Decision 1 below says what the world must equal either way.
1. **A port, not a rewrite.** The world, the pushes, the period loop and the row writer are those of
   `spike/closest-ref` (`tests/small_world/support.rs`: `World::doubled`, `part`, `pushed`, `pushed_a`,
   `definition`, `state`, `recurring`, `financial`, `staffing`, `Catalogs::at`, `snapshot`, `run_staffed`;
   `tests/small_world/spike.rs`: `baseline`, `write_run`, `line`, `markets`, `money`), cut to the closest form's
   paths: no bank, pay rule, lending, rules D, H, O, R, S, W, A4, L, the reserve share or d2. Every identity is the
   prototype's (site byte `g + 1`, worker household `11 + 2 x (g % 4) + g / 4`, owner `20 + c`, supported
   `22 + c`, treasury 30, fund 31), and nothing is aliased. The game's `tests/small_world/` is not touched, but
   for the one literal Task 2 adds a field to (`tests/small_world/support.rs:430`).
2. **Two figures, nothing else.** `Figures::National` sets each offer's step to
   `opening price x 250 / 10_000` rounded down (power $0.30, farm food $0.625, care $0.75, shop food $0.95) and
   opening site cash to `[1200, 880, 880, 1400] x 2` dollars; `Small` uses $1 and `x 1`. Floor $1 and ceiling
   $1,000 for every offer.
3. **The loop of Task 1** is the engine's own: `close_material_period`, `staffing_requests`, `advance_staffing`,
   `distribute_staffing_members` (one member a pool), `finish_with_staffing`. Rule A6 is on in every run
   (`plans_from_spare_money: true`). After each period the loop asserts that total money equals the opening's.
4. **The projection.** Split the text on `\n` (the last piece is empty); split each line on `\t`; keep the indices
   of header names that do not start with `flow_`; write the kept fields joined by `\t`, each line ended by `\n`.
   The bench writes its rows through the same `project`, so a column it did not write would show as a missing
   column, not as a hidden one.
5. **The fixture.** `digests/<set>.txt` holds 25 lines `<run> <sha256 hex>`, in run order, of each reference file
   projected. Make it with the ignored helper `print_reference_digests`, which reads, for each run of `runs()` in
   order, `/media/user/dev-ssd/babylon-bench/restoring-forces/out/<set>/<run>.tsv` (not the directory: it also
   holds `summary6.txt` and `summary.json`) and prints the lines; commit what it printed. No other test reads the
   drive.
6. **A mismatch.** `assert_set` writes each differing run's projected rows to
   `<CARGO_TARGET_TMPDIR>/adjustment-bench/<set>/<run>.tsv`. If the reference file exists on the drive, it names the
   first differing period and column; else it says where the reference rows are
   (`/media/user/dev-ssd/babylon-bench/restoring-forces/out/<set>/`).
7. **Period count:** 400 for the long tests (`PERIODS_LONG: u64 = 400`); 34 for the quick test.

- [ ] **Step 1: Write the unit tests** in `compare.rs` and `rows.rs`:
  - `money_is_written_as_the_prototype_writes_it`: `money(12_000_000) == "12"`, `money(625_000) == "0.625"`,
    `money(-1_500_000) == "-1.5"`, `money(0) == "0"`.
  - `the_projection_drops_only_flow_columns`: for `"period\tflow_x\tcash_a\n1\t2\t3\n"` the projection is
    `"period\tcash_a\n1\t3\n"`; a text with no `flow_` column is returned unchanged.
- [ ] **Step 2: Write the quick test** `the_doubled_quiet_world_is_still_for_34_periods` (not ignored): for both
  worlds' `quiet` run at both figures, every one of 34 projected lines after the header equals the first, apart
  from its `period` field; `hours_attended` is 480.
- [ ] **Step 3: Write the long tests** `reproduces_pc_a6_400` and `reproduces_pc_a6_nat_400` (`#[ignore]`), each
  `assert_set` over the 25 runs at 400 periods against its fixture.
- [ ] **Step 4: Port** the world, the loop and the writer; make the fixture with `print_reference_digests`.
- [ ] **Step 5: Run** the quick and unit tests, then the long tests in the background. Expected: 25 of 25 at both
  figures. If not, find the first differing column. A cause in the port is fixed; a cause in the engine (the
  merged prototype's engine with every switch off differs from this branch) is a stop: report it.
- [ ] **Run the gate. Commit** `test(material-circuit): the doubled bench of the restoring-forces rounds`.

### Task 2: The setting

**Files:**
- Create: `src/adjustment.rs`, `src/adjustment/policy.rs`.
- Modify: `src/clearing/rule.rs` (the field); `src/catalog.rs` (admission, tests); `src/wire/catalog.rs`
  (`bytes`); `src/lib.rs` (exports); every hand-built `MarketClearingPolicy` gets `adjustments: Vec::new()`
  (`rg -n 'MarketClearingPolicy \{' rust/crates` prints 16 lines; two are the struct and its `impl` in
  `clearing/rule.rs`, the other 14 are literals, among them `tests/small_world/support.rs:430`);
  `tests/adjustment_bench/world.rs` (the form's list); `contracts/material_circuit_v4.yaml` and the digest.

**Interfaces:**

```rust
// src/adjustment/policy.rs
/// One rule of ADR314 measured in rounds eight to ten, asked for by a market policy.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum AdjustmentRule {
    /// A workplace asks for hands only for the hours its inputs and its money can use.
    HiringWithinMeans,
    /// People not needed look for work at the other workplaces of their place (A14).
    SeekingInPlace,
    /// A workplace that cannot pay the hours its plan asked keeps only those it paid (A17).
    StopWithoutPay,
    /// A workplace that employs nobody and offered nothing holds its price.
    RestingPrice,
    /// Its owner restarts a stopped workplace with the owner's own money (A17, A19, ADR318 L1),
    /// for `outlay_periods` periods of one batch's cost a batch.
    OwnerRestart { outlay_periods: u64 },
    /// A goods price steps down when goods beyond the buffer went unsold, to its cost and no lower (A1).
    StepDownToCost,
}
impl AdjustmentRule {
    /// The rule's tag in the catalog bytes: 1 to 6 in the order above.
    pub(crate) const fn tag(self) -> u8;
}
/// Whether `rules` asks for a rule of this kind.
pub(crate) fn asks(rules: &[AdjustmentRule], rule: AdjustmentRule) -> bool;
/// The restart's periods of outlay, when the list asks for the restart.
pub(crate) fn restart_outlay_periods(rules: &[AdjustmentRule]) -> Option<u64>;
// src/clearing/rule.rs, MarketClearingPolicy gains:
/// The rules of ADR314 this policy asks for, in the order of `AdjustmentRule`, each once.
/// Empty keeps today's behaviour and bytes.
pub adjustments: Vec<AdjustmentRule>,
// src/wire/catalog.rs
/// A market policy that asks for adjustments writes this version first, then its rules, then every byte the
/// same catalog writes without them.
const ADJUSTMENT_CATALOG_SCHEMA_VERSION: u16 = 9;
```

`asks` compares the kind: `OwnerRestart` with any `outlay_periods` is the same kind. Write it with
`mem::discriminant`.

**Decisions:**
1. **One list, one entry a rule.** Each task can then be proven against its own set, and each entry names one rule
   of the design. A list, not six booleans: clippy's `struct_excessive_bools` and the style's "enum over bool".
2. **Bytes.** Empty: today's bytes. Not empty: right after the domain and its terminator, `9_u16`, then the count
   as `u16`, then each rule's tag as `u8` and, for `OwnerRestart`, `outlay_periods` as `u64`, all big-endian;
   then every byte the same catalog writes without the list, A6's `8_u16` included. No other version word 9 is
   written at that place, so every list has distinct bytes.
3. **Admission refuses, with `MarketClearingInvariant`:** a list out of order or with a kind twice;
   `StopWithoutPay` without `SeekingInPlace`; `OwnerRestart` without `StopWithoutPay`, `RestingPrice` and
   `HiringWithinMeans`; `outlay_periods == 0`. These are the prototype's own refusals (`support.rs:118-160`).
   Every other combination is admitted. These refusals live in one crate-private function,
   `fn refuse_combinations(rules: &[AdjustmentRule]) -> Result<(), MaterialCircuitError>`, which admission calls.
   **Until the task that builds a rule, admission refuses that rule too**: a crate-private
   `const NOT_YET_BUILT: &[AdjustmentRule]` lists the six, and admission, after `refuse_combinations`, refuses a
   list that names one of their kinds. Each rule task removes its own kind from the const and nothing else; Task 8
   removes the const, the refusal and the test `admission_refuses_a_rule_not_yet_built`. So no catalog can ask
   for a rule that does nothing, and no test assertion changes but that one, which the plan ends.
4. **Contract.** `catalog_version` (near line 74) gains "a market policy that asks for adjustments writes 9
   first, then its rules, then the bytes the same catalog writes without them"; the tail comment of
   `catalog_row_field_order` says the same; the `market_clearing` section gains `ADR314_adjustments` (not
   `A14_...`, which is the design's name for the seekers' rule), naming the six
   rules, the refusals and "a rule not yet built is refused"; `P13_asking` gains "and the rules of ADR314 only by
   naming them in adjustments". Each later task replaces its rule's line there with its rule in the contract's
   style.
5. **The bench's form.** `Form::rules(self, figures: Figures) -> Vec<AdjustmentRule>`; `Form::A6` gives an empty
   list. `OwnerRestart`'s `outlay_periods` is 1 at the small figures and 2 at the national (`SPIKE_J_PERIODS`).

- [ ] **Step 1: Write the failing tests** in `src/catalog.rs`'s tests:
  `adjustments_write_version_nine_before_the_bytes_without_them` (with `[HiringWithinMeans]`: bytes at
  `head..head + 2` are `9_u16`, then `1_u16`, then `1_u8`; the rest equals the same catalog's bytes without the
  list from `head`); `a_restart_writes_its_periods` (`[HiringWithinMeans, SeekingInPlace, StopWithoutPay,
  RestingPrice, OwnerRestart { outlay_periods: 2 }]`: the fifth tag `5_u8` is followed by `2_u64`);
  `adjustments_change_the_digest` (with and without A6's flag: each digest differs from its twin's);
  `admission_refuses_a_list_out_of_order_or_twice`; `admission_refuses_the_stop_rule_without_seekers`;
  `admission_refuses_a_restart_without_its_rules`; `admission_refuses_a_restart_of_zero_periods`;
  `admission_refuses_a_rule_not_yet_built` (for each kind in `NOT_YET_BUILT`, a list of it with the rules it
  needs passes `refuse_combinations` and is refused by `MaterialCatalog::try_new`).
  The three byte and digest tests cannot go through `MaterialCatalog::try_new`, which refuses every rule until
  its task: they call `crate::wire::catalog_bytes(&definition)` (`wire/state.rs:716`, which takes a
  `MaterialCatalogDefinition`) and `digest(&definition)` (`catalog.rs:437`) on definitions that are not admitted.
  The four combination tests call `refuse_combinations` directly, each with a list that it must refuse and the
  same list with the missing rule added (or in order, or with `outlay_periods: 1`), which it must pass. So they
  are never refused for being not yet built, and they hold in every task.
  `PINNED_BASE_DIGEST` and `PINNED_POLICY_DIGEST` pass unchanged.
- [ ] **Step 2: Run them and see them fail.** `mise run rust:test:q -- -p babylon-material-circuit -E
  'test(adjustments) | test(admission_refuses)'`. Expected: does not compile, no field `adjustments`.
- [ ] **Step 3: Implement** the type, the field, the bytes, the refusals, the 14 literals, the contract and the
  digest.
- [ ] **Step 4: Run** the crate's tests and the bench's quick test. Expected: all pass, no pinned value changed.
- [ ] **Run the gate. Commit** `feat(material-circuit): let a market policy name the rules of ADR314`.

### Task 3: People look for work in their place (`pc-seek`)

**Files:**
- Create: `src/staffing/place.rs`; `src/adjustment/receipts.rs`.
- Modify: `src/staffing.rs` (`mod place; pub use`); `src/transition/state.rs` (`ClosedMaterialPeriod`);
  `src/model.rs` (`MaterialCircuitTransition.adjustments`); `src/financial/layoffs.rs` (advance with moves);
  `src/catalog.rs` (lift the refusal); `src/lib.rs`; the contract and the digest.
- Modify: the bench: `world.rs` (`Form::Seek`; the members of each household at each workplace),
  `run.rs` (the staffing step), `rows.rs` (the seekers' columns); add `digests/pc-seek-400.txt`,
  `pc-seek-nat-400.txt`.

**Interfaces:**

```rust
// src/staffing/place.rs
/// The pools whose people look for work at one another: one place.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StaffingPlace { pub pools: Vec<StaffingPoolId> }
/// A pool's members: one for each household of its place, in member order.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PoolMembers { pub pool_id: StaffingPoolId, pub members: Vec<StaffingMemberState> }
/// The staffing of a closed period by the rules of the catalog.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PlaceStaffing {
    pub state: StaffingState,
    pub members: Vec<PoolMembers>,
    pub labor: Vec<LaborCapacityRow>,
    pub member_labor: Vec<MemberLaborCapacityRow>,
    /// The engine's own decision, pool by pool and member by member, before any move.
    pub receipts: Vec<StaffingReceipt>,
    pub member_receipts: Vec<StaffingMemberReceipt>,
    /// Every move of persons from one pool's reserve to a host.
    pub moves: Vec<PlaceMoveReceipt>,
}
/// Why `staff_in_places` refused: the circuit's own refusal or the staffing's. There is no
/// `From<StaffingError> for MaterialCircuitError` today, and this plan adds none.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum PlaceStaffingError { Circuit(MaterialCircuitError), Staffing(StaffingError) }
// with `From<MaterialCircuitError>` and `From<StaffingError>` for `?`.
// src/adjustment/receipts.rs
/// What the rules of ADR314 did at one close, in the order they acted.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum AdjustmentReceipt { PlaceMove(PlaceMoveReceipt) }
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PlaceMoveReceipt {
    pub period: u64,
    pub host_pool: StaffingPoolId,
    pub host_member: StaffingMemberId,
    pub from_pool: StaffingPoolId,
    pub from_member: StaffingMemberId,
    pub household_id: FinalDemandPrincipalId,
    pub persons: u64,
    /// `None`: no record of layoffs covered them. `Some(age)`: from the cohort laid off `age` periods before.
    pub covered_age: Option<u8>,
}
// src/model.rs, MaterialCircuitTransition gains:
/// What the rules of ADR314 did, in the order they acted. Empty unless the catalog asks.
pub adjustments: Vec<AdjustmentReceipt>,
// src/transition/state.rs
impl ClosedMaterialPeriod {
    /// The catalog's staffing for a world whose people look for work in their place.
    /// # Errors
    /// `Circuit(MarketClearingInvariant)` when the catalog does not ask for `SeekingInPlace`; a circuit
    /// refusal of the requests; `Staffing(..)` for a pool in no place or in two, members that are not the
    /// pool's people, or arithmetic.
    pub fn staff_in_places(
        &self,
        catalog: &MaterialCatalog,
        opening: &StaffingState,
        members: &[PoolMembers],
        places: &[StaffingPlace],
    ) -> Result<PlaceStaffing, PlaceStaffingError>;
    /// Finish after `staff_in_places`: advance the record of layoffs with the moves, install the hours, and
    /// put the moves in `adjustments`.
    /// # Errors
    /// As `finish_with_staffing`.
    pub fn finish_with_place_staffing(
        self,
        catalog: &MaterialCatalog,
        staffing: &PlaceStaffing,
    ) -> Result<MaterialCircuitTransition, MaterialCircuitError>;
}
```

**Decisions** (the prototype is `seek_hands`, `open_slots`, `cohorts_after`, `support.rs:476-871` on
`spike/closest-ref`; read it before you write):
1. **The engine's decision first.** `staffing_requests`, then `advance_staffing`, then
   `distribute_staffing_members` for each pool over its members. A workplace calls back its own people first.
2. **Seekers** are each member's closing reserve. A seeker is covered when the member's household is a recipient
   of an `AfterLayoff` program and the member's record of layoffs, as the engine would advance it with this
   decision (the steps of `financial/layoffs.rs` `advance_layoffs`), still holds a cohort for them. The window is
   `ceil(half_periods / 2)`. Without such a program nobody is covered.
3. **Hosts.** A pool whose `need = ceil(requested hours / hours_per_person) - closing employed` is above 0
   (saturating). `requested hours` is the sum over every staffing request of the pool. The prototype sums
   `asked` per site over all requests (`support.rs` `run_staffed`); with one pool a site, as on the bench, the
   two are the same. Order: the highest wage first (the largest `Wage` rate of the site's employment terms), then the
   largest need, then the pool's site order in the place. A host's own reserve is 0 by decision 1; check it
   (`StaffingError::PopulationInvariant` if not).
4. **Taking.** A host takes from the other pools of its place, `left = need`: first uncovered seekers, pools in
   site order, members in member order, as many as each has; then covered seekers by cohort age 0, 1, ... (the
   newest laid off first), pools in site order, members in member order. It stops when `left` is 0 or nobody is
   left. Whole persons.
5. **A move is for good.** The person leaves the old pool's member and joins the host's member of their own
   household. Both pools' labor forces change (`StaffingPoolBinding::try_new` with the new force; the pool keeps
   its `previous_unretained_hours`). Labor rows and member rows of the next period are `employed x
   hours_per_person`. The host's wage is paid through that member's employment terms, which the world authored.
6. **The record of layoffs** is advanced, inside `finish_with_place_staffing`, exactly as the prototype's
   rewritten receipts advance it (`support.rs:741-779`): a covered person who leaves counts as a hire of the
   member they leave; an uncovered one as a person who left that member's reserve before the decision; at the host
   each newcomer is a hire from the member's reserve. Those rows are built and used internally; they are not
   published. `member_receipts` stay the engine's decision.
7. **The place** is the caller's. Every pool is in exactly one place. The bench gives each copy its own place.
8. **The bench's world** authors, when the form asks for seekers, one member and one `EmploymentTerms` row (the
   host's site and rate, the person's household as payee) and one member row of 0 hours for every ordered pair of
   workplaces of a copy (`support.rs:2776-2802, 2852-2861`), with the prototype's member identities
   (`slot_member`). The bench keeps the members between periods and passes them in.
9. **Bench columns:** `seekers_<copy>`, `people_<copy>`, `people_<site>`, `looking_<site>`,
   `covered_own_<site>`, `parked_<site>`, `pair_working_/pair_looking_/pair_covered_<host>_from_<home>`, in the
   prototype's order (`spike.rs` `line`, the step S block). They are computed from `PlaceStaffing` and the state's
   record of layoffs. The bench asserts each copy's persons equal the opening's in every period.

- [ ] **Step 1: Write the failing unit tests** in `src/staffing/place.rs`:
  - `a_host_takes_the_uncovered_first`: two pools of one place, host need 3, the other pool's member reserves
    uncovered 2 and covered 4 (age 0): moves are 2 uncovered, then 1 covered of age 0.
  - `the_highest_wage_is_served_first`: two hosts in one place, wages $11 and $10, each need 2, seekers 3: the $11
    host takes 2, the $10 host 1.
  - `a_seeker_stays_in_their_place`: two places, a host in one and seekers only in the other: no move.
  - `a_move_keeps_every_person`: in each of the above, the sum of every pool's labor force before equals after.
  - `a_pool_in_no_place_is_refused` and `a_pool_in_two_places_is_refused`.
- [ ] **Step 2: Run them and see them fail** (`-E 'test(place)'`): `staff_in_places` not found.
- [ ] **Step 3: Implement** the step, the receipts, the finish, the contract line (replacing the refusal line of
  Task 2) and the digest. Lift the refusal of `SeekingInPlace`.
- [ ] **Step 4: The bench.** `Form::Seek` (`[SeekingInPlace]`), the members, the loop's call, the columns. Add the
  quick test `the_quiet_world_with_seekers_is_still_for_34_periods` (as Task 1's, with the seekers' columns) and
  the long tests `reproduces_pc_seek_400` and `reproduces_pc_seek_nat_400`; make their fixtures.
- [ ] **Step 5: Run** the crate's tests, then every long test in the background. Expected: `pc-a6` and `pc-seek`,
  25 of 25 at both figures.
- [ ] **Run the gate. Commit** `feat(material-circuit): people look for work in their place (A14)`.

### Task 4: A bound on hiring (`pc-bound`)

**Files:**
- Create: `src/adjustment/bound.rs`.
- Modify: `src/transition/state.rs` (`next_plans`, `ClosedMaterialPeriod` field and `staffing_requests`);
  `src/adjustment/receipts.rs`; `src/catalog.rs`; the contract and the digest; the bench (`Form::Bound`,
  `bound_hours_<site>`, `bound_by_<site>`); `digests/pc-bound-400.txt`, `pc-bound-nat-400.txt`.

**Interfaces:**

```rust
// src/adjustment/bound.rs
/// The bound of the next period: each production process's batches and hours, and each attendance row's cut.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct HiringBound {
    pub(crate) next_period: u64,
    pub(crate) process: BTreeMap<ProcessId, (u64, u64)>,
    pub(crate) rows: Vec<HiringBoundReceipt>,
}
/// Reckon the bound and lower the next period's attendance plans by it.
pub(crate) fn bound_hiring(
    catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState,
    performance: &[ServicePerformanceReceipt],
    maintenance: Option<&MaintenanceReceipt>,
    next_period: u64,
) -> Result<HiringBound, MaterialCircuitError>;
/// The largest `b <= most` with `spent + b x per <= cash`; all of `most` when `per == 0`; 0 when `cash < spent`.
pub(crate) fn batches_within(most: u64, per: i128, spent: i128, cash: i128) -> Result<u64, MaterialCircuitError>;
// src/adjustment/receipts.rs, AdjustmentReceipt gains HiringBound(HiringBoundReceipt):
pub struct HiringBoundReceipt {
    pub period: u64,
    pub site_id: SiteId,
    pub unit_id: UnitId,
    pub asked_hours: u64,
    pub bound_hours: u64,
    pub limit: HiringLimit,
}
/// What set a cut: the bench writes 0 to 4 in this order.
pub enum HiringLimit { None, Capacity, Inputs, Money, Other }
```

`ClosedMaterialPeriod` gains a private `hiring_bound: Option<HiringBound>`.

**Decisions** (the prototype is `compute`, `spike/closest-ref` `src/spike_bound.rs:137-411`, and its reader in
`state.rs:698-710`):
1. **Where.** At the end of `next_plans`, after `plan_attendance` and the goods prices, only when the catalog asks.
   The receipts go into `adjustments`; the bound is kept on the closed period.
2. **A maker's process** (in the order of decision 6): from the engine's own request
   (`derive_shared_labor_requests`), `asked = hours / hours per batch`; `capacity = process_available(next)`;
   for each service input only: `made` = the provider's planned batches, capped at its nameplate and at its own
   bound when already reckoned, times output per batch; `others` = what it performed this period for buyers other
   than this site; `for_me = min(made - others (saturating), quantity_per_period, maximum_purchase)`;
   `by_inputs = for_me / input per batch`. Money: `per = hours per batch x wage + each service input per batch x
   its provider's posted price` (the price the offers hold when the bound runs); `wage` is the largest `Wage` rate
   of the site's employment terms. `by_money = batches_within(min(asked, capacity, by_inputs), per, spent, cash at
   the close)`, `spent` being what this site's earlier requests of this pass took.
3. **A merchant:** `handling` = its planned attendance hours less its other work; `to_handle` = the goods it holds
   or has due by the next period times hours a unit; then money at its wage. Its restocking is not counted against
   its money.
4. **The cut.** Each attendance row of the next period loses `request - cap` (`saturating_sub`). `limit`: `Money`
   if money cut, else `Capacity` or `Inputs` by which is smaller, else `Other`, else `None`. Planned batches,
   orders and prices are not cut. A merchant's limit is only `Money` or `Inputs`. A process with 0 hours a batch
   is not cut and sets no limit (`hpb == 0`, `spike_bound.rs:193-196`).
   **Several rows of one site.** The engine keeps one limit per (site, unit): the last limit other than `None`
   in the reckoning order (`note_by`, `spike_bound.rs:182-188`); a receipt with no cut says `None`, a cut with no
   limit noted says `Other`. The bench's `bound_by_<site>` is the largest code over the site's receipts, as
   `spike.rs` `write_run` writes it (`by[k].max(r.by)`, line 1034).
5. **Readers.** `staffing_requests` caps each production request at the bound's hours for its process; a
   merchant's request follows the capped plan as today. Payroll reads the capped plan.
6. **Order:** processes so that every provider of a service input comes before its buyers, ties and cycles by
   process id (departure 6).

- [ ] **Step 1: Write the failing unit tests** in `src/adjustment/bound.rs`:
  - `the_opening_is_not_cut`: `batches_within(120, 10_000_000, 0, 1_200_000_000) == 120` (the utility),
    `batches_within(4, 220_000_000, 0, 880_000_000) == 4` (the farm), `batches_within(40, 22_000_000, 0,
    880_000_000) == 40` (the clinic).
  - `money_cuts_by_whole_batches`: `batches_within(40, 22_000_000, 0, 879_999_999) == 39`.
  - `money_spent_by_an_earlier_request_counts`: `batches_within(10, 10_000_000, 95_000_000, 100_000_000) == 0`.
  - `a_free_batch_is_not_cut`: `batches_within(7, 0, 0, 0) == 7`.
  - `providers_come_before_their_buyers`: a catalog whose buyer's process id sorts before its provider's is
    reckoned provider first.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement**; lift the refusal; contract and digest.
- [ ] **Step 4: The bench.** `Form::Bound` (`[HiringWithinMeans, SeekingInPlace]`), its columns, the quick test
  `the_quiet_world_with_the_bound_is_still_for_34_periods`, the long tests `reproduces_pc_bound_400` and
  `reproduces_pc_bound_nat_400`, their fixtures.
- [ ] **Step 5: Run** the crate's tests, then every long test. Expected: three forms, 25 of 25 at both figures.
- [ ] **Run the gate. Commit** `feat(material-circuit): a workplace asks for hands it can pay and supply`.

### Task 5: No money, no work (`pc-stop`)

**Files:**
- Create: `src/adjustment/standing.rs`.
- Modify: `src/staffing/place.rs`; `src/transition/state.rs` (the close's entry with standing; the refusal in the
  others; `PlaceStaffing.standing`); `src/adjustment/receipts.rs`; `src/catalog.rs`; the contract and the digest;
  the bench (`Form::Stop`, the standing kept between periods, `stopped_<site>`); `digests/pc-stop-*.txt`.

**Interfaces:**

```rust
// src/adjustment/standing.rs
/// What the rules remember of each workplace from one close to the next. The caller keeps it, as it keeps
/// the staffing state.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct WorkplaceStanding { rows: Vec<WorkplaceStandingRow> }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct WorkplaceStandingRow { pub site_id: SiteId, pub hold: StopHold }
/// Whether the stop rule holds a workplace back.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum StopHold { #[default] Free, Held }
impl WorkplaceStanding {
    /// Nothing remembered: the opening.
    #[must_use] pub fn opening() -> Self;
    /// One row for each workplace the rules have seen, in site order.
    #[must_use] pub fn rows(&self) -> &[WorkplaceStandingRow];
}
// src/transition/state.rs
/// `close_material_period` for a catalog whose rules remember workplaces.
/// # Errors
/// As `close_material_period`.
pub fn close_material_period_with_standing(
    catalog: &MaterialCatalog,
    opening: &MaterialCircuitState,
    standing: &WorkplaceStanding,
) -> Result<ClosedMaterialPeriod, MaterialCircuitError>;
// PlaceStaffing gains:
pub standing: WorkplaceStanding,
// AdjustmentReceipt gains Stop(StopReceipt):
pub struct StopReceipt {
    pub period: u64,
    pub site_id: SiteId,
    pub could_not_pay: bool,
    pub hold: StopHold,
    /// The most persons it may employ after this close; `None` when not limited.
    pub limit: Option<u64>,
}
```

`StopReceipt.could_not_pay` is a receipt field, not a parameter, so the style's bare-`bool` finding does not apply;
if bsl-lint flags it, make it an enum `Payment { Paid, Short }`.

**Decisions** (the prototype is `support.rs:4029-4078, 4129-4162` on `spike/closest-ref`):
1. **Where.** Inside `staff_in_places`, before the engine's staffing. `ClosedMaterialPeriod` gains a private
   `standing: Option<WorkplaceStanding>`. The body of `close_material_period_with_portfolios` moves, unchanged,
   into one private function, `fn close_with_rules(catalog, opening, aid_inputs, collection_inputs,
   agency_inputs, previous, selections, standing: Option<&WorkplaceStanding>)`. `close_material_period_with_portfolios`
   refuses a catalog that asks for `StopWithoutPay` (`MarketClearingInvariant`), before anything is closed, and
   then calls it with `None`; `close_material_period_with_standing` calls it with no aid, collections, agency or
   portfolios and `Some(standing)`, and only it sets the field. Every other close entry goes through
   `close_material_period_with_portfolios` (f93b3beaa `state.rs:1382-1640`), so each refuses too. So
   `close_material_period_with_portfolios`, which `babylon-tick` calls, cannot run the rule without its memory, and
   neither can the restart, which needs the stop rule. `staff_in_places` returns the standing as it stands after
   the rule in `PlaceStaffing.standing`; the caller passes that to the next close.
2. **The test**, per site, from this period's `member_labor_use` receipts: `available`, `attended`,
   `unattended` summed over its members; `bill = sum(available_hours x member's wage rate)`; `employed` = its pools'
   opening employed; `hpp` = its pool's hours per person.
   - `unattended > 0`: could not pay. `limit = min(employed, ceil(attended / hpp))`; `hold = Held`.
   - else, if `Held` and `available > 0` and `unattended == 0`: `hold = Free`.
   - else, if still `Held`: `limit = employed + floor(max(cash - bill, 0) / (rate x hpp))`, `rate` the largest `Wage`
     rate of the site.
   - `cash` is the site's cash in the closed period's state, the state `staff_in_places` reads. From Task 7 that
     state holds the restart's money, as the prototype's does: it reads `closed.spike_state()` in the stop block,
     after the mend block's `restart_close` (`support.rs` `run_staffed`, about 3980 and 4034). The bench cannot
     catch a wrong choice here: planned hours equal attended hours in every period of all 100 runs of
     `r10-P-down-none`, `-nat`, `-goods` and `-goods-nat`, so the rule never acts. Nor can it differ: the
     restart's money goes only to the restarted site, whose hold the restart sets `Free` (Task 7, decision 6), so
     no `Held` site's cash changes. The unit test `a_held_workplace_hires_only_as_far_as_its_money` pins the
     arithmetic.
3. **The limit** caps the pool's target in the engine's staffing (`target = min(target, limit)`) and the host's
   need in the seekers' step (`need = min(need, limit - employed)`, saturating). Give `advance_staffing` a crate-
   private twin with limits; its public form is unchanged.
4. **The bench column** `stopped_<site>` is 1 when the site attended 0 hours and employs nobody after staffing.

- [ ] **Step 1: Write the failing unit tests** in `src/staffing/place.rs`:
  - `a_workplace_that_could_not_pay_keeps_whom_it_paid` (employed 5, hpp 8, attended 20, unattended 20: limit 3,
    held);
  - `a_held_workplace_that_paid_everyone_is_free` (held, available 40, unattended 0: free, no limit);
  - `a_held_workplace_hires_only_as_far_as_its_money` (held, available 0, cash $500, bill $400, rate $10, hpp 8,
    employed 5: limit 6);
  - `the_old_entry_refuses_the_stop_rule` (`close_material_period` with a catalog asking `StopWithoutPay`:
    `Err(MarketClearingInvariant)`).
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement**; lift the refusal; contract and digest.
- [ ] **Step 4: The bench.** `Form::Stop`, the close with standing, the column, the quick test
  `the_quiet_world_with_the_stop_rule_is_still_for_34_periods`, `reproduces_pc_stop_400`,
  `reproduces_pc_stop_nat_400`, their fixtures.
- [ ] **Step 5: Run.** Expected: four forms, 25 of 25 at both figures.
- [ ] **Run the gate. Commit** `feat(material-circuit): no money, no work (A17)`.

### Task 6: A resting price (`pc-rest`)

**Files:**
- Modify: `src/recurring/prices.rs`; `src/services/market.rs`; `src/clearing/table.rs` (`offered`);
  `src/adjustment/receipts.rs`; `src/catalog.rs`; the contract and the digest; the bench (`Form::Rest`);
  `digests/pc-rest-*.txt`.

**Interfaces:**

```rust
// src/clearing/table.rs
/// What a seller offered at its markets of a product this period: the sum of `supply` over its rows.
pub(crate) fn offered(&self, site: SiteId, good: GoodId, unit: UnitId) -> u64;
// src/recurring/prices.rs and src/services/market.rs
/// Whether a workplace rests at this close: the catalog asks, its labor rows of the closing period offer
/// 0 hours, and it offered nothing at its markets.
pub(crate) fn rests(catalog: &MaterialCatalog, state: &MaterialCircuitState, site: SiteId, offered: u64) -> bool;
// AdjustmentReceipt gains RestingPrice(RestingPriceReceipt):
pub struct RestingPriceReceipt {
    pub period: u64,
    pub site_id: SiteId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub price: Currency,
}
```

**Decisions** (the prototype is `spike/closest-ref` `src/spike_rest.rs:60-69`, `prices.rs:376-385`,
`services/market.rs:481-495, 550-558`):
1. "Employs nobody in the period" is read from the state's labor rows of the closing period, which the last
   staffing wrote as `employed x hours_per_person`. The prototype reads the same from the pools.
2. A resting goods offer is not quoted: reason `Hold`. A resting service keeps its price: reason `Hold`. The cost
   and priced-out step ups do not run for it.
3. `rests` is a free function of the price modules; put it in `src/adjustment/` and import it in both.

- [ ] **Step 1: Write the failing unit tests:** `a_workplace_with_hands_does_not_rest` (8 hours, offered 0:
  false); `a_workplace_with_goods_on_offer_does_not_rest` (0 hours, offered 3: false); `an_idle_workplace_rests`
  (0 hours, offered 0, catalog asks: true; not asking: false).
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement**; lift the refusal; contract and digest.
- [ ] **Step 4: The bench.** `Form::Rest`, the quick test, `reproduces_pc_rest_400`, `reproduces_pc_rest_nat_400`.
- [ ] **Step 5: Run.** Expected: five forms, 25 of 25 at both figures.
- [ ] **Run the gate. Commit** `feat(material-circuit): a stopped workplace's price rests`.

### Task 7: The owner restarts a stopped workplace, mended (`pc-restart`)

**Files:**
- Create: `src/adjustment/restart.rs`.
- Modify: `src/adjustment/standing.rs` (two counters); `src/transition/state.rs` (the step at the end of the
  close); `src/adjustment/bound.rs` (the rebound); `src/valuation/` (one booking function on the cost book);
  `src/adjustment/receipts.rs`; `src/catalog.rs`; the contract and the digest; the bench (`Form::Restart`; columns
  `restart_test_<site>`, `stopped_since_<site>`, `restart_inputs_<site>`, `owner_spare_<copy>`);
  `digests/pc-restart-*.txt`.

**Interfaces:**

```rust
// src/adjustment/standing.rs, WorkplaceStandingRow gains:
/// Periods since it last made or sold anything.
pub periods_since_work: u64,
/// The same, counted again from 0 at a restart: the restart's test reads it.
pub quiet_periods: u64,
// src/adjustment/restart.rs
/// The mended restart at the end of the close, before staffing.
pub(crate) fn restart_stopped(
    catalog: &MaterialCatalog,
    transition: &mut MaterialCircuitTransition,
    standing: &mut WorkplaceStanding,
    bound: &mut HiringBound,
    next_period: u64,
) -> Result<(), MaterialCircuitError>;
/// One batch's cost: a maker's hours at `rate` and each input at the highest posted price among its
/// provider's offers; a merchant's hours a unit at `rate` and its supplier's posted price (one unit a batch).
/// `Ok(None)` when a price it needs is not posted.
pub(crate) fn batch_cost(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    site: SiteId,
    rate: i128,
) -> Result<Option<i128>, MaterialCircuitError>;
// src/valuation, HistoricalCostBook gains:
/// An owner's capital paid into a workplace after the close: the owner's equity carrying amount and the
/// workplace's contributed capital, each up by `amount`; an equity row is made if there is none.
pub(crate) fn add_contribution(
    &mut self,
    owner: AccountId,
    issuer: SiteId,
    amount: Currency,
) -> Result<(), MaterialCircuitError>;
// AdjustmentReceipt gains Restart(RestartReceipt), OwnerSpare(OwnerSpareReceipt), RestingPriceToCost(..):
pub struct RestartReceipt {
    pub period: u64, pub site_id: SiteId, pub test: RestartTest, pub inputs_short: bool,
    pub owner: Option<AccountId>, pub money: Currency, pub batch_cost: Currency, pub turned: u64,
}
/// The bench writes 0 to 3 in this order.
pub enum RestartTest { NotTested, Failed, NoBuyer, Restarted }
pub struct OwnerSpareReceipt { pub period: u64, pub owner: AccountId, pub spare: Currency }
pub struct RestingPriceToCostReceipt { pub period: u64, pub site_id: SiteId, pub old: Currency, pub raised: Currency }
```

**Decisions** (the prototype is `restart_close`, `batch_cost`, `mend_rest_prices`, `sales_and_output`,
`support.rs:3490-3855, 3954-4003`, and `spike_mend_inputs`, `rebound`, `src/spike_bound.rs:413-609`, on
`spike/closest-ref`; this task builds the mended form only, so the unmended order is never built):
1. **Where.** At the very end of `close_with_rules`'s body (Task 5, decision 1), after the tier receipts, when the
   catalog asks and `standing` is `Some`. Only `close_material_period_with_standing` passes `Some`; the other entry
   refuses every catalog that asks for the restart, since it asks for `StopWithoutPay`. Order: (b) resting prices
   to cost; the counters; the test; the money; (c) the bound reckoned again.
2. **(b)** A price that rested at this close (a `RestingPriceReceipt` of this close, Task 6) and stands under one
   unit's cost is raised to that cost, at the rate of decision 4:
   `unit = ceil(batch_cost / output a batch)`, every offer of the site set to it; the period's price or service
   market receipt gets the new `next_price` (its reason stays `Hold`), and a `RestingPriceToCostReceipt`.
3. **Counters.** `periods_since_work` and `quiet_periods` go to 0 if the site made or sold anything this period,
   else up by one, after (b) has run. The prototype's words, kept exactly (`sales_and_output`, `support.rs:3622`,
   and its caller in `run_staffed`, about 3966): `sales` = the quantity of its local transfers as supplier, plus
   its local fulfillments as retailer, plus its service markets' `performed_quantity`; `output` = a production
   receipt's `produced_batches x quantity_per_batch` (the last such receipt of the site, as the prototype assigns
   it), plus the quantity of local transfers it received as buyer. It made or sold anything when `sales > 0`, or
   when it has a recurring production row and `output > 0`.
4. **The test**, for each site whose labor rows of the closing period offer 0 hours and with
   `quiet_periods >= 3` (`const RESTART_QUIET_PERIODS: u64 = 3`): `turned` = the sum, over every
   `market_clearings` receipt of the site this close (not only short markets), of `demand_at_quote -
   sold_quantity` (`restart_close`, `support.rs`, about 3728-3733; checked subtraction, a negative is
   `Arithmetic`); `revenue = min(turned, out) x price`; pass only if
   `revenue > batch_cost`. Then (a) the inputs of one batch can be had (held, or each lacking input is made by a
   supplier that employs people, made it this period, and whose planned make, capped at nameplate and its own
   bound, less its other buyers' take covers it; a merchant's batch is one unit of each good it handles); else
   `inputs_short`, not restarted. `batches = max(1, min(turned / out, nameplate))`;
   `earn = min(turned, batches x out) x price - batches x batch_cost`; `plan = batches x batch_cost x
   outlay_periods`; `money = plan - cash`; a restart with `money <= 0` is refused (mend a).
5. **The buyer** is the holder of the site's ownership claim, only from its own money:
   `spare = cash - one period of its own required goods and services at posted prices`. Candidates in order of
   `earn / plan`, highest first (compare `earn_b x plan_a` with `earn_a x plan_b`), ties by site. Each restart's
   money comes out of what is left of that owner's spare; one that does not fit gets `NoBuyer`.
6. **The money.** `book.transfer_cash(owner -> site, money, CapitalContribution)`, its `MoneyTransferReceipt`
   pushed to `money_transfers`, `add_contribution` on the cost book. Capital: never paid back, never earnings. The
   standing's hold of the site goes `Free` and `quiet_periods` to 0.
7. **(c)** The bound of the next period is reckoned again: each attendance row of the next period gets back this
   close's cut, then `bound_hiring` runs again and replaces the bound and its receipts.
8. A catalog that asks for `OwnerRestart` asks for `StopWithoutPay` (Task 2), so a close with no standing refuses
   it already (Task 5). The step reads and writes the closed period's own standing.
9. `rate` in decisions 2 and 4 is the largest `Wage` rate of the site's employment terms (departure 7); `price` is
   the site's posted price; `out` is the output of one batch (one unit for a merchant); `cash` is the site's cash at
   the close.

- [ ] **Step 1: Write the failing unit tests** in `src/adjustment/restart.rs`:
  - `a_restart_that_puts_in_nothing_is_refused` (plan $40, cash $40: no restart; cash $39: $1 put in);
  - `candidates_rank_by_earn_over_plan` (earn $10 plan $100 against earn $3 plan $20: the second first; equal
    ratios: the lower site first);
  - `a_resting_price_under_cost_is_raised_to_it` (batch cost $23, output 1, price $12: $23; price $30: unchanged;
    batch cost $230, output 9: $25.555556, rounded up to the micro-unit);
  - `an_owner_puts_in_only_its_own_spare` (spare $50, two candidates of $40 each: the first restarts, the second is
    `NoBuyer`);
  - `the_restart_moves_money_with_a_receipt` (the transfer receipt's amount equals the site's cash gain and the
    owner's cash loss; total money unchanged).
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement**; lift the refusal; contract and digest.
- [ ] **Step 4: The bench.** `Form::Restart` (`[HiringWithinMeans, SeekingInPlace, StopWithoutPay, RestingPrice,
  OwnerRestart { outlay_periods }]`, 1 period small, 2 national), its columns, the quick test,
  `reproduces_pc_restart_400`, `reproduces_pc_restart_nat_400`.
- [ ] **Step 5: Run.** Expected: six forms, 25 of 25 at both figures.
- [ ] **Run the gate. Commit** `feat(material-circuit): an owner restarts a stopped workplace with its own money`.

### Task 8: A goods price steps down, to its cost and no lower (`pc-down`)

**Files:**
- Modify: `src/recurring/prices.rs` (`update_prices`, `quote`); `src/clearing/table.rs` and
  `src/clearing/ladder.rs` (offered, sold, gain at a price); `src/transition/state.rs` (`next_plans` order);
  `src/recurring/firms.rs` (the gain in the plans); `src/adjustment/receipts.rs`; `src/catalog.rs`; the contract
  (`P9_posted_price` too) and the digest; the bench (`Form::Down`, `unsold_<site>`, `turned_payers_<site>` for
  farms and shops); `digests/pc-down-*.txt`.

**Interfaces:**

```rust
// src/clearing/table.rs
/// Whether a seller's goods markets (`HouseholdGoods` and `Restocking` rows) sold less than they offered
/// beyond `kept`: `sold + kept < supply`.
pub(crate) fn goods_unsold(&self, key: StockKey, kept: u64) -> Result<bool, MaterialCircuitError>;
/// What its goods markets offered and sold this period; `None` when it has no goods market row.
pub(crate) fn goods_offered_sold(&self, key: StockKey) -> Option<(u64, u64)>;
/// What its bids could buy at `price` beyond what they bought at the quote (`demand_at_price` less
/// `demand_at_quote`, summed over its goods markets).
pub(crate) fn goods_gain_at(&self, key: StockKey, price: Currency) -> Result<u64, MaterialCircuitError>;
// AdjustmentReceipt gains GoodsOffer(GoodsOfferReceipt):
pub struct GoodsOfferReceipt {
    pub period: u64, pub site_id: SiteId, pub good_id: GoodId, pub unit_id: UnitId,
    pub offered: u64, pub sold: u64, pub kept: u64, pub floor: Currency, pub planned_gain: u64,
}
```

**Decisions** (the prototype is `spike/closest-ref` `src/recurring/prices.rs:262-477` with
`SPIKE_DOWN_GOODS=on` and `SPIKE_DOWN_FLOOR=cost`, `clearing/table.rs:175-277`, `clearing/ladder.rs:190-218`,
`state.rs:1189-1259`, `firms.rs:764-767, 926-928`):
1. **The test.** `waiting` as today (paid household purchases not filled, restock orders not shipped, final-demand
   orders not filled, and what bids could pay for at the posted price in a short market and did not get).
   `kept` = the seller's production policy's `output_buffer` (0 for a seller with none). `unsold` = sold plus kept
   below what its goods markets offered. Order: `Fixed`; a resting seller holds; step up as today; else step down
   one step if `waiting == 0` and (`stock > target_stock` or `unsold`); else hold.
2. **The floor**, for every step down while the catalog asks: `max(minimum, unit cost)`, the unit cost being
   `costs.goods_price_cost(key).unit_cost()` of the period, the figure the cost-pressure test reads; with no
   observation this period, `minimum` (departure 3; Task 0 counts how often). A step down for unsold goods records
   reason `ExcessStock`, the step-down reason that exists: no new `PriceDecision`, because `babylon-tick` and
   `babylon-persistence` match on it exhaustively (`recurring_receipt.rs:159-167`, `projection.rs:110-143`). The
   `GoodsOfferReceipt` says why.
3. **Plans at the new price.** While the catalog asks, goods are quoted before `plan_production`, and a seller that
   stepped down adds `goods_gain_at(new price)` to its unshipped quantity (makers) or its merchandise (merchants'
   handling hours). Services are untouched: no quote before plans, no gain (departure 4).
4. **Bench columns:** `unsold_<site>` = `offered - sold` (without `kept`), `turned_payers_<site>` = the price
   receipt's `unserved_quantity`, farms and shops only, after the bound's columns, as `spike.rs` `write_run`.

- [ ] **Step 1: Write the failing unit tests** in `src/recurring/prices.rs`: `a_step_down_stops_at_cost` (old $38,
  step $1, unit cost $37.50: $37.50); `a_step_down_below_cost_is_not_taken` (unit cost $38: holds at $38);
  `without_a_cost_the_floor_is_the_minimum` (old $1.50, step $1, no observation: $1);
  `a_buffer_is_not_unsold` (offered 40, sold 0, kept 40: not unsold); `a_buyer_who_could_pay_and_waited_bars_the_step`
  (waiting 1, unsold: no step down); `not_asking_keeps_todays_price_rule` (the same offers, catalog not asking:
  today's decisions).
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement**; lift the refusal; contract and digest.
- [ ] **Step 4: The bench.** `Form::Down` (the six rules), its columns, the quick test,
  `reproduces_pc_down_400`, `reproduces_pc_down_nat_400`.
- [ ] **Step 5: Run.** Expected: seven forms, 25 of 25 at both figures. The `pc-down` rows passed the Director's
  test as ruled in Task 0, so the built form passes it: every column the counters read is compared.
- [ ] **Run the gate. Commit** `feat(material-circuit): a goods price steps down to its cost and no lower (A1)`.

## Self-review notes

- **Every rule has a task.** (a) the bound, Task 4; (b) seekers, Task 3; (c) the stop rule, Task 5; (d) the
  resting price, Task 6; (e) the restart with its three mends, Task 7; (g) the step down to cost, Task 8. Rule A6
  is built; Task 1 proves the bench against it.
- **Every task has a reference that Task 0 makes.** No reference that exists today was made by this branch's engine
  (departure 1), so all fourteen are made anew from the prototype changed in exactly three proven ways (C1 to C3)
  and run with switches only. The merge keeps every spike file and switched hunk (P4), and every difference from
  the old rows is explained or the plan stops (decision 3). The form as built is judged by the Director's test
  before any task starts.
- **Order follows the references**: seekers before the bound (`pc-seek` exists in every form of the prototype, the
  bound without seekers would need its own set), the stop rule before the rest, both before the restart. Rest has
  its own set, so the restart task is the mended form alone.
- **Not built (D2):** banks and loans, the pay rule, letting go at once and the service price rule, plans down the
  chain, capacity added, idle money taken out, organized workers, cheapest-seller buyers, the opening seekers
  (`SPIKE_SEEKERS`, unset in the closest form), the services part of the prototype's step down. The closest form
  passes through inert code of several of these on the prototype (`financial/close.rs:66-68`, `spare_money.rs`
  `wages` reading the pay switch, `advance_pool` reading `SPIKE_O`, `quote` reading `SPIKE_S` and `SPIKE_W`); none
  of it is built.
- **The stop rule never acts on the bench** (hours planned equal hours attended in all 50 runs of the closest form,
  `notes-bench.md` fact 1). Its set proves it changes nothing it should not; its unit tests prove what it does.
- **Names agree between tasks:** `AdjustmentRule` and its six variants (Task 2), `AdjustmentReceipt` (Task 3, a
  variant added in each of Tasks 4 to 8), `PlaceStaffing` (Task 3, `standing` added in Task 5),
  `WorkplaceStanding` (Task 5, counters added in Task 7), `HiringBound` and `bound_hiring` (Task 4, read again in
  Task 7), `close_material_period_with_standing` and the private `close_with_rules` (Task 5, used by Task 7),
  `refuse_combinations` and `NOT_YET_BUILT` (Task 2, the const lifted kind by kind in Tasks 3 to 8).

## The lead's answers to the plan's three questions (23 November 2026)

1. The nine `c2-` runs stay. They are cheap, and they are the only way to tell a difference made by the
   aliases from one made by the merge.
2. P4 checks every hunk of the prototype, not only those that name a switch. The list of named misses is
   longer; each is read.
3. If the national sets show no restart test at all, that is reported and not a stop: at those figures no
   workplace stays stopped long enough to be tested, which is what the rules are for. The restart's proof
   then rests on the small figures and on Task 7's unit tests, and `pc-sets.md` says so.

## What the check changed

- Task 0, C3: the merge's resolution is stated, file by file: spike files byte for byte; switched hunks kept;
  only F2 dropped; the game's `spare_money::wages` made `pub(crate)` for the bound, with the `SPIKE_PAY` branch
  put back; `gains` and `ReserveInputs` kept in the prototype's plans, with A6 in F2's place; the harness sets
  A6's flag under `SPIKE_F2=on`.
- Task 0: new proof P4 (spike files unchanged; every switched, `gains` or `ReserveInputs` hunk found on
  `spike/closest-ref`, or named), run before Step 4, stopping on failure.
- Task 0, decision 3: the count against old twins became a gate. Each of nine sets is also run at C2, and every
  first difference (old twin to C2 to C3) is explained in `pc-sets.md` or the plan stops. `pc-down` gained its
  twin `r10-P-down-goods-none`. Steps 3 and 4 and "Produces" follow.
- Task 0, decision 3: the count of restart tests per set is reported, with the note that the national goods-only
  rows never tested a restart.
- Task 0, decision 4: the counters' paths are absolute.
- Departure 1 points to C3. New departure 10 records the caller-owned memory as a debt.
- Task 1: the small world's one literal is the exception to "not touched"; `print_reference_digests` reads the
  runs of `runs()`, not the directory.
- Task 2: the 16 lines `rg` prints are named (14 literals). The byte and digest tests use `catalog_bytes` and
  `digest` on definitions. The combination refusals live in `refuse_combinations`, tested directly with a
  refused and an admitted twin, so they are not vacuous while a kind is not yet built. The contract key is
  `ADR314_adjustments`.
- Task 3: `need` is summed per pool, and the prototype's per-site sum is named.
- Task 4: how limits combine over a site's rows, a merchant's two limits and the 0-hours process are stated.
- Task 5: the close body is the private `close_with_rules`; the held limit's cash is the closed state's, and why
  the choice cannot change a row.
- Task 7: the restart sits at the end of `close_with_rules`; "made or sold" and `turned` are the prototype's
  exact sums.
