# The Closest Form (rules of ADR314 measured in ten rounds) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build into the engine the form the Director picked on 22 November 2026: "a bound on hiring; people
look for work in their place; no money, no work; resting price, mended restart; a goods price steps down, to its
cost and no lower". The last clause was the lead's wording and no round measured it: on 23 November the Director
ruled that the step down is built as measured, under cost if it must (ADR321, K1). Behind a setting no campaign
asks for yet. Each rule reproduces its rows of the test economy before it merges.

**Architecture:** Six rules, each asked for by one entry in a new list on the catalog's market policy, as rule A6
is asked for by its flag. A catalog that does not ask runs today's code and keeps every byte. The rules sit where
the prototypes acted: the bound at the end of the close's plans; the restart and its mends at the very end of the
close; the stop rule and the seekers in a new staffing step of the closed period; the resting price and the step
down inside today's price rules. What a rule remembers from one period to the next lives with the caller, as
persons do. The bench that measured the rules becomes a test binary of the crate, `tests/adjustment_bench.rs`,
and every rule task ends by reproducing a set of its rows byte for byte. The bench opens the doubled world of
`babylon-circuit-worlds` and steps it with that crate's `Runner`, the loop the client's scene runs, so what the
bench proves is what the scene shows. A rule task that changes the loop changes `Runner`.

**Tech Stack:** Rust (`babylon-material-circuit`; `babylon-circuit-worlds` for the world, the runner and the read
access the bench needs); `contracts/material_circuit_v4.yaml`.

**Spec:** `docs/superpowers/specs/2026-11-21-how-the-economy-adjusts-design.md`, rules A1, A6, A14, A17, A19 and
sections 6 and 8; `ai/decisions/ADR314_how_the_economy_adjusts.yaml`, `ADR318_who_carries_a_losing_workplace.yaml`
(L1), `ADR319_a_shock_is_not_a_failure.yaml` (J1 to J6). Records:
`reports/economy-repair-2026-11-20/restoring-forces/round-8.md` to `round-10.md`. The prototype is the scratch
branch `spike/r10-P` (head 3944ee9f3) and, after Task 0, `spike/closest-ref`. It shows where each rule sits and
what it computes. It is not the code to ship. Builders read it only with `git show <branch>:<path>`.

**When it is built (ADR320, 23 November 2026).** The Director ruled "screen first": the small world
runs in the client first. Asked what comes after the scene, the Director picked "Rules into the scene
first": this plan is built next, each rule with its own switch in the scene, and the bridge after it.
Task 0 may run earlier, whenever the build machine has a free turn, because it changes nothing in the
repository and its gate decides whether the plan stands.

**The road to the screen.** The client's scene of the small world
(`docs/superpowers/specs/2026-11-23-the-small-world-in-the-client-design.md`) runs the engine itself, so a
rule is seen there as soon as its task lands. Each rule task therefore has a companion task in the client,
right after it. Task 2c builds the list of switches in the rail's lower part (behind a second tab, beside the
shocks), the command, the refusal's notice and the script's command, and shows no switch. Tasks 3c to 8c each
put one rule's switch in that list, off by default, and turn its receipts into marks: a household's hours at
another workplace, and the outline and the persons that follow them; the hours a workplace asked for and those
its money and inputs allow; a workplace held back by no money, no work, its centre disc dim; a price that
rests; an owner's money going in, a sixth gold stream; a goods price that stepped down, in the panel. `table.rs`
is not edited: once the owner's money can be read (Task 7c), the table's money in and out count it as they
count every payment. A rule task is not done until its companion has put its switch on screen.
What a campaign needs before it may ask for these rules is under "Stored format" below.

The scene and the bench run one world and one loop: the doubled world and the `Runner` of
`babylon-circuit-worlds` (Tasks 1a and 1b). So a rule proven on the bench is the rule the scene runs. How a switch
behaves in the middle of a run was ruled by the Director on 23 November ("On anytime, off by restart", ADR321,
K3): a switch turns its rule on from the next period, and the rule holds until the run is started over, as the
power cut does; a rule that needs another can be turned on only once the other is on. The bench proves each set
of rules from period 1; a rule turned on later is seen on screen and is not measured. One road serves both:
`Runner::turn_on` (Task 2) turns a rule on from `next_period()`, the `from` a strike gets, and
`Runner::open_world` turns on the world's rules with it before the first step. The seekers' rows are in every
world from Task 1a, read by no rule until the seekers are on. The client's switches are Tasks 2c to 8c.

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
| member rows of other workplaces | opening state, existing row kinds | every world authors one `EmploymentTerms` and one member row for each household at each workplace of its place (Task 1a), at 0 hours, read by no rule until the seekers are on; no new kind |
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
3. **The step down is built as the prototype has it: it stops at the policy minimum,** $1 on the bench
   (`spike/r10-P` `src/recurring/prices.rs:436-439`). So this is no departure any more. The lead had planned a
   floor at cost, from words of the lead's own that no round had measured. Task 0 added that floor to the
   prototype behind a switch, proved that the switch off changes nothing, and counted both forms; the Director
   then ruled "As measured" (ADR321, K1). The floored rows are kept for the record as `pc-downfloor`, and
   nothing of the floor is built.
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
   test, the goods unsold). Task 0 and the bench use the same projection (Task 1b, decision 4).
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
  (`tests/small_world/`) keep every figure. If one must move, stop and tell the lead. The client's scene has one
  named exception, the lead's: Task 7c moves the count of streams in `the_styles_name_the_plans_units` from 9 to
  10 (the owner's money is a sixth kind of payment).
- Money is `i128` millionths of a dollar (`Currency`); quantities and hours are `u64`; arithmetic is checked and a
  failure is a typed error (`MaterialCircuitError` or `StaffingError`), never a panic or a wrap. Saturation only
  where these decisions name it.
- No environment variable and no name beginning `SPIKE` or `spike` anywhere under `src/`, in the bench or in
  `babylon-circuit-worlds`.
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
  `mise run rust:test:q -- -p babylon-tick`; `mise run rust:test:q -- -p babylon-circuit-worlds`;
  `mise run check:bsl-sentinels`. A task that changes the `src/` of `babylon-circuit-worlds` (Tasks 1a, 2, 3 and
  5) also runs the client's tests of the scene, which steps that crate's runner: `mise run rust:test:q -- -p
  babylon-client -E 'test(small_world)'`. So does Task 8, which removes one test of the scene. A task that only
  adds tests to the crate (Tasks 4, 6 and 7) does not.
  The rest of the client is compiled by the clippy leg. If a task changes anything under `tools/`, `.mise.toml` or
  `.github/`, also the Python unit tests that read it (no task here does).
  **The companion's gate** (Tasks 2c to 8c and 3d, the client's scene only), one leg at a time from `rust/`:
  the fmt and clippy legs above; `mise run rust:test:q -- -p babylon-client -E 'test(small_world)'`;
  `mise run check:bsl-sentinels`. Not the engine's, the tick's or the small worlds' legs, and not the long tests.
  A companion's proof script is run by the lead on the real display, never by the builder; the client's own
  rules (the scene plan's Global Constraints: no test opens a window; every visual entity carries
  `DeclaredSurface { id: SurfaceId::SmallWorld }`; a figure on screen is exactly a receipt's; words that name a unit
  are built from the constants; the look's numbers are the lead's) hold in every companion.
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
3. **Money is created or lost.** The restart is the only rule that moves money. Pinned by the runner's check that
   total money equals the opening's after every period of every run (Task 1a) and by Task 7's receipt test.
4. **People are created or lost.** Seekers move between members of one place. Pinned by the runner's check that
   each place's persons equal the opening's after every period (Task 3) and by the staffing receipts' own `validate`.
5. **The projection hides a difference.** Only `flow_` columns are left out (departure 5). The projection is one
   function, used on both sides. Pinned by Task 1b's `the_projection_drops_only_flow_columns`.
6. **An accident of order.** Bound order (departure 6), host order (highest wage, then most lacking, then site),
   seeker order (uncovered first, then covered by cohort age), restart order (earn over plan, then site). Each is
   pinned by the bench's rows; each is stated in its task.
7. **A rule turned on in the middle of a run.** It is on from `next_period()` and its first close is that
   period's; opening with a form is the same as turning its rules on before the first step; a late turn-on is
   deterministic and keeps money and people; each refusal changes nothing. Pinned by Task 2's
   `opening_with_a_form_is_turning_its_rules_on_first` and the runner's tests named in Tasks 2 to 8. No reference
   set covers a late turn-on, and nothing says one does.
8. **A mark the receipts did not give.** Every row a rule adds to the panel is a sum of its receipts' fields, and
   a period without the rule draws and prints what it did before. Pinned by each companion's
   `..._rows_are_its_receipt_s` tests and by Task 3c's `without_a_move_every_frame_is_as_before`.

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `rust/crates/babylon-material-circuit/tests/adjustment_bench.rs` | The bench binary's root: its modules, and `include!` of `adjustment_bench/sets.rs` | 1 |
| `rust/crates/babylon-material-circuit/tests/adjustment_bench/sets.rs` | The bench's quick tests, its long tests and `print_reference_digests` | 1, 2-8 |
| `rust/crates/babylon-material-circuit/tests/adjustment_bench/runs.rs` | The 25 runs of a set and the form's rules | 1, 2 |
| `rust/crates/babylon-material-circuit/Cargo.toml`, `rust/Cargo.lock` | The engine's dev-dependency on the small worlds | 1 |
| `rust/crates/babylon-circuit-worlds/src/doubled/world.rs` | Which world opens: plain or fund, its scale, its push, its rules | 1, 2 |
| `rust/crates/babylon-circuit-worlds/src/doubled/{catalog,opening,staffing,figures}.rs` | The world's catalog, opening and staffing, per world | 1, 2, 3 |
| `rust/crates/babylon-circuit-worlds/src/runner/{run,result}.rs` | The period loop, its checks and its read access | 1, 2, 3, 5 |
| `rust/crates/babylon-circuit-worlds/src/runner/rules.rs` | The rules of a run: `RuleOn`, `Switch`, `RuleError` | 2 |
| `rust/crates/babylon-circuit-worlds/tests/worlds.rs` | The plain world, the national figures and each opening push pinned | 1, 3 |
| `rust/crates/babylon-circuit-worlds/tests/{doubled,runner}.rs` | The pair rows' counts; a late turn-on and its refusals | 1, 2-8 |
| `rust/crates/babylon-client/src/small_world/frame.rs` | People at work summed by household, not by site; a household's persons and hours at each workplace; a held workplace; the capital stream | 1, 3c, 5c, 7c |
| `rust/crates/babylon-client/src/small_world/reading.rs` | `read_work` skips a pair receipt of 0 hours; the owner's money read as capital | 1, 7c |
| `rust/crates/babylon-client/src/small_world/rules.rs` | `SceneRule`, `SHOWN_RULES`, the list of switches in the rail's lower part, the refusals' words | 2c-8c |
| `rust/crates/babylon-client/src/small_world/marks.rs` | The rules' receipts as rows of the panel | 3c-8c |
| `rust/crates/babylon-client/src/small_world/{scene,panel,script}.rs` | `SceneCommand::TurnOn` and `Lower`, the two tabs of the rail's lower part, the dim centre disc, the notice's `say`, `{"rule": ..}` and the report's rules; the panel's rows of the rules; capital in "Not drawn" | 2c, 3c, 5c, 7c |
| `rust/crates/babylon-client/src/small_world/inspect.rs` | "At work" summed by household; `good_name` made `pub(super)` | 3c, 6c |
| `rust/crates/babylon-client/src/small_world/{scene_tests,script_tests}.rs` | The scene's tests and each companion's proof script | 2c-8c |
| `rust/crates/babylon-material-circuit/tests/adjustment_bench/rows.rs` | The row writer | 1, 3-8 |
| `rust/crates/babylon-material-circuit/tests/adjustment_bench/compare.rs` | Projection, digests, the report of a mismatch | 1 |
| `rust/crates/babylon-material-circuit/tests/adjustment_bench/digests/pc-*.txt` | sha256 of each reference run file | 1, 3-8 |
| `rust/crates/babylon-material-circuit/src/clearing/rule.rs` | `MarketClearingPolicy.adjustments` | 2 |
| `rust/crates/babylon-material-circuit/src/adjustment.rs` and `src/adjustment/*.rs` | The rules' types and arithmetic; every public receipt type, enum and `RESTART_QUIET_PERIODS` exported from `src/lib.rs` in the task that adds it, for the client's companions | 2-8 |
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

**Where:** the branch `spike/closest-ref`, made from `spike/r10-P` at 3944ee9f3. Its three commits are written in
a worktree of their own, `/media/user/dev-ssd/worktrees/closest-ref`, where nothing is ever built: the machine's
managed cargo keeps one build slot for every checkout of this repository, and a build from a second checkout
deletes it. Every build and every set runs in the game's checkout, with its head detached at the commit to run,
while no builder works there; the checkout is put back on its branch after. Rows go to `BENCH/out/<set>/`. The
runner is `BENCH/scripts/closest-ref-run.sh` (steps `p1`, `p2`, `c2sets`, `p3`, `sets`, `count`); each set takes
about 21 s after the build. `BENCH/k-scripts/cmp_sets.py` names the first period and column where two sets
differ on the projected rows.

**Produces:** the fourteen sets below and the floored form at both figures (`pc-downfloor`, for the record), each
25 files of 401 lines; nine `c2-` sets and the floored form's two under `BENCH/c2/`
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
   | `pc-a6` | none | Task 1b |
   | `pc-seek` | `SPIKE_SEEK=on` | Task 3 |
   | `pc-bound` | `SPIKE_SEEK=on SPIKE_BOUND=on` | Task 4 |
   | `pc-stop` | `SPIKE_SEEK=on SPIKE_BOUND=on SPIKE_STOP=on` | Task 5 |
   | `pc-rest` | the same and `SPIKE_REST=on` | Task 6 |
   | `pc-restart` | the same and `SPIKE_RESTART=on SPIKE_MEND=on` | Task 7 |
   | `pc-down` | the same and `SPIKE_DOWN=on SPIKE_DOWN_GOODS=on` | Task 8 |
   | `pc-downfloor` | the same and `SPIKE_DOWN_FLOOR=cost` | none: kept for the record (ADR321, K1) |

   Every intermediate form has a set: no task builds two rules to reach a reference.
3. **Every difference from the old rows is explained.** A set and its old twin of the same rules need not be
   byte-equal: the aliases are off and A6 is in F2's place. So each difference is accounted for, and the old
   rows (tied to `spike/r10-P` by the chain of byte-equal sets in `notes-design.md`) check the merge. The twins:
   `pc-a6` and `r8-ref-none`, `pc-seek` and `r8-seek-none`, `pc-bound` and `r9-bound-none` (both figures);
   `pc-restart` and `r10-M-mend-none` (small only: no national twin exists); `pc-down` and
   `r10-P-down-goods-none` (both figures). To separate the two causes, each of these nine sets is also run once
   at C2, before the merge, as `c2-<name>` (under `BENCH/c2/`; deleted when the plan is built). For each run the lead
   writes in `pc-sets.md`, on the projected rows (Task 1b, decision 4): whether `c2-<name>` equals the old twin,
   and if not the first differing period and column and why the aliases change it there; then whether
   `pc-<name>` equals `c2-<name>`, and if not the first differing period and column and the merged commit and code
   line that explain it. A difference with no explanation stops the plan. Also reported, not gated: for
   `pc-downfloor`, the count of `flow_down_uncosted` over each set; for every set,
   the number of site-periods with `restart_test_` above 0. (The old `r10-P-down-goods-none-nat-400` has none in
   all 80,000 site-periods, so at the national figures the restart's money path may never run; if
   `pc-restart-nat-400` and `pc-down-nat-400` also have none, its proof rests on the small figures and Task 7's
   unit tests, and `pc-sets.md` says so.)
4. **The Director's test as ruled.** Run the lead's counters on every set:
   `python3 -I BENCH/k-scripts/r9_tests.py BENCH/out '^pc-'` then
   `python3 -I BENCH/k-scripts/r10_ruled.py BENCH/out <tests.json>`.
   then `python3 -I BENCH/k-scripts/ruled_by_world.py <tests.json> <ruled.json>`, which scores the test as the
   Director ruled on 23 November (ADR321, K2): lines 2 and 3 over the runs of the world with a fund, line 1 in
   both calm worlds, and the runs of the world with no fund counted the same way and reported.
   **Gate:** `pc-down-400` and `pc-down-nat-400` both pass where there is a fund. If either fails, stop: the lead
   takes the rows to the Director, and no rule task (2 to 8) starts. Tasks 1a and 1b build no rule and may start
   once Task 0 has made the sets they reproduce. The other verdicts are reported only; their forms are steps,
   not candidates.

- [ ] **Step 1:** Make the worktree and the branch; write C1; run P1. Expected: 25 of 25, twice.
- [ ] **Step 2:** Write C2; run P2. Expected: 25 of 25, twice.
- [ ] **Step 3:** Before merging, run the nine `c2-` sets of decision 3 at C2. Merge (C3) as resolved there; run
  P3 and P4. Expected: all pass; P4 prints only the hunks it names. Else stop.
- [ ] **Step 4:** Run the sixteen sets; copy them to the drive; write the explanations and counts of decision 3.
  Expected: every difference explained. Else stop.
- [ ] **Step 5:** Run the counters. Expected: `pc-down` passes where there is a fund at both figures. Else stop
  and report.

### Task 1a: The small worlds hold every world of the bench

**Files:**
- Create: `rust/crates/babylon-circuit-worlds/src/doubled/world.rs`;
  `rust/crates/babylon-circuit-worlds/tests/worlds.rs`.
- Modify: `src/doubled.rs` (`mod world;` and its `pub use`); `src/doubled/figures.rs`; `src/doubled/catalog.rs`;
  `src/doubled/opening.rs` (the pair rows); `src/doubled/staffing.rs` (`members_of`); `src/ids.rs`
  (`Workplace::pair_member_id`); `src/runner/run.rs`; `src/runner/result.rs`; `src/error.rs`; `src/lib.rs`
  (exports); `tests/doubled.rs` and `tests/runner.rs` (three pinned counts and one loop, decision 7), all under
  `rust/crates/babylon-circuit-worlds/`.
- Modify (the client): `rust/crates/babylon-client/src/small_world/frame.rs` (`at_work` summed by household);
  `rust/crates/babylon-client/src/small_world/reading.rs` (`read_work` skips a pair receipt of 0 hours).

**Interfaces:**

```rust
// babylon-circuit-worlds src/doubled/world.rs
/// Which of the bench's two worlds: no public account, or a treasury and a fund.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Economy { Plain, Fund }
/// The figures of a set: a $1 price step and one period of outlay as opening cash (small), or a step of
/// 250 bps of the opening price, rounded down to the micro-unit, and two periods (national).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Scale { Small, National }
/// A change to the opening, made before the first period. The harvest is not here: it is a `Shock`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum OpeningPush {
    /// P1: the owner household's cohort counts half its persons.
    LessDemand,
    /// P3: the shop opens with half its cash.
    LessMoney,
    /// P4: the clinic pays $11 an hour.
    HigherPay,
    /// P5: the fund's 16 tax rows at three quarters of their rate. Fund world, both places.
    LowerFundTaxes,
    /// P6: the power cut from the opening: the utility plans in batches of 10 hours, and `Shock::PowerCut`
    /// holds from period 1.
    PowerCut,
    /// P7: the owner household's cohort counts half again as many persons.
    MoreMouths,
}
/// A push and where it strikes.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Pushed { pub push: OpeningPush, pub places: Places }
/// Everything that sets a doubled world before its first period.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct World { pub economy: Economy, pub scale: Scale, pub pushed: Option<Pushed> }
impl World {
    /// The scene's world: the fund world at the small figures, nothing pushed. `Runner::open` opens it.
    #[must_use] pub const fn scene() -> Self;
    /// The household accounts, in the engine's principal order: `Household::ALL` with the fund, the same
    /// without the two supported households in the plain world.
    #[must_use] pub fn households(&self) -> Vec<Household>;
    /// A household's persons at the opening without a push: plain workers 15/5/5/5 and owner 10; the fund
    /// world's are `Household::opening_persons`.
    #[must_use] pub const fn persons(&self, household: Household) -> u64;
    /// A cohort's persons after the push (P1 halves the owner's, P7 takes half again); stocks, purchases,
    /// cash and the hours stay those of `persons`.
    #[must_use] pub const fn cohort_persons(&self, household: Household) -> u64;
    /// Hours a person: 8 plain, 10 fund.
    #[must_use] pub const fn hours_per_person(&self) -> u64;
    /// The catalog's figures of period 1: `Figures::OPENING`, or the power cut where it is pushed.
    #[must_use] pub fn opening_figures(&self) -> Figures;
}
// babylon-circuit-worlds src/doubled/{catalog,opening,staffing}.rs (the old forms call these with World::scene())
/// # Errors
/// As `catalog`.
pub fn catalog_of(world: &World, figures: &Figures) -> Result<MaterialCatalog, WorldError>;
/// # Errors
/// `WorldError::PushNotInThisWorld` for `LowerFundTaxes` in the plain world; `WorldError::PushOnOnePlace` for
/// `LowerFundTaxes` struck in one place; otherwise as `opening_state`.
pub fn opening_state_of(world: &World) -> Result<MaterialCircuitState, WorldError>;
/// # Errors
/// As `staffing`.
pub fn staffing_of(world: &World) -> Result<(Vec<StaffingPoolBinding>, StaffingState), WorldError>;
/// # Errors
/// As `member`.
pub fn member_of(world: &World, workplace: Workplace, employed: u64) -> Result<StaffingMemberState, WorldError>;
/// Every pool's members at the opening, by `Workplace::index`: the workplace's own member with all its people,
/// and one member for each other workplace of its place (`pair_member_id`), with nobody.
/// # Errors
/// As `member_of`.
pub fn members_of(world: &World) -> Result<Vec<Vec<StaffingMemberState>>, WorldError>;
// babylon-circuit-worlds src/ids.rs (moved here from Task 3)
impl Workplace {
    /// The member of `home`'s household at this workplace: the workplace's own member when `home` is it, else
    /// byte `0x40 + 8 x home.index() + self.index()` (the prototype's `lend_member`).
    #[must_use] pub const fn pair_member_id(self, home: Workplace) -> StaffingMemberId;
}
// babylon-circuit-worlds src/runner/run.rs
impl Runner {
    /// The world at its opening. A pushed power cut is struck in the book from period 1, until started over.
    /// The opening's money, persons and each place's people are measured here and checked after every period.
    /// The runner keeps the world (each period's catalog is built from it) and every pool's members.
    /// # Errors
    /// `RunnerError::World` when the world or the engine refuses the opening.
    pub fn open_world(world: &World) -> Result<Self, RunnerError>;
    /// The world the runner opened.
    #[must_use] pub const fn world(&self) -> &World;
    /// The state after the last step: the opening of the next period.
    #[must_use] pub const fn state(&self) -> &MaterialCircuitState;
    /// The catalog the last step closed under; `None` before the first step.
    #[must_use] pub fn catalog(&self) -> Option<&MaterialCatalog>;
}
// babylon-circuit-worlds src/runner/result.rs
// PeriodResult gains:
/// Hours asked of staffing for the next period, by `Workplace::index`: the sum over the period's requests.
pub asked: [u64; 8],
// PeriodReceipts gains:
pub household_wants: Vec<HouseholdWantReceipt>,
pub household_tiers: Vec<HouseholdTierReceipt>,
// babylon-circuit-worlds src/error.rs, WorldError gains:
/// A push this world cannot take: the fund's taxes in the plain world.
PushNotInThisWorld,
/// The fund's taxes struck in one place: there is one fund.
PushOnOnePlace,
```

**Decisions:**
1. **One doubled world, in `babylon-circuit-worlds`.** The crate was built for the client's scene with one world: the
   fund world at the small figures. The bench needs more: the plain world, the national figures and six pushes that
   change the opening. They are added here, so that the bench has no world of its own. What each world must equal
   is the prototype's (`spike/closest-ref` `tests/small_world/support.rs`: `World::plain`, `taxed`, `benefits`,
   `with_tiers`, `doubled`, `pushed`, `pushed_a`, `definition`, `recurring`, `financial`, `add_fund`, `state`,
   `staffing`), cut to the closest form's paths. Every identity is the crate's, which are the prototype's and
   pinned by the crate's tests. No engine crate changes in this task.
2. **The two worlds.** `Economy::Plain` is the prototype's `World::plain().with_tiers()` doubled: no treasury, no
   fund, no taxes, budgets, allocations, programs or institution locations; five household accounts a place (no
   supported household); workers 15/5/5/5 and owner 10 persons; 8 hours a person; owner cash $800.
   `Economy::Fund` is the crate's world as built. Batches, hours (120/40/40/40), stocks, caps and prices are the
   same in both. A6 is on in both (`plans_from_spare_money: true`).
3. **The two scales.** `Scale::National` sets each offer's step to `opening price x 250 / 10_000` rounded down
   (power $0.30, farm food $0.625, care $0.75, shop food $0.95) and the four site cash figures to twice
   [$1,200, $880, $880, $1,400]; `Small` uses $1 and once. Floor $1 and ceiling $1,000 for every offer: the step
   is no longer the minimum. Owner, treasury and fund cash do not move.
4. **The pushes.** P1, P3, P4, P5, P6 and P7 change the opening and are `OpeningPush`. P2, P8 and their one-place
   forms are catalog figures and are struck: P2 `(HarvestFails, Both, UntilLifted)`, P8 `(HarvestFails, Both,
   TenPeriods)`, P2a and P8a the same in `Places::A`, each before the first step, so periods 1 to 10 are poor and
   11 on are not, as the prototype's `Catalogs::at` gives. P4a and P6a are `Pushed { places: Places::A }`.
   `PowerCut` builds the opening with 12 utility batches of 10 hours a place where it is pushed (planned batches,
   commitments and nameplate rows of every period), as the prototype's `batches()` does, and `open_world` strikes
   `Shock::PowerCut` there from period 1, so the catalog of period 1 is the cut's and the book says so.
   The scene offers none of the opening pushes: they are worlds a caller opens, not controls of a run.
5. **The loop** is `Runner::step` as built: close, staffing requests, staffing, each pool's receipt shared over its
   kept members (decision 7), the finish with staffing. It changes in four ways only: the members are opened from
   the world's persons (`members_of`); they are kept between periods; the runner measures the opening's money,
   cohort persons and each place's people when it opens and refuses a period that does not keep them
   (`MoneyNotConserved`, `PersonsNotConserved`); it keeps the hours asked. `Runner::open()` is
   `open_world(&World::scene())`, so the scene runs as before. The capacity rows stay written to period 1,000 (the
   prototype wrote `periods + 2`); no compared column reads a period beyond the next.
   That last point is read from the engine, not proven: Task 1b's long tests prove it. If their first difference
   comes from the horizon, the world gains a `horizon` and the bench opens with `periods + 2`; say so in the report.
   The runner goes on computing the state's digest every period (about 0.8 s in a run of 400); its own tests
   compare two runs by it.
   `Runner::state()` is a read-only borrow: nothing but the engine's own period changes the state.
6. **Style.** Types are imported and used bare; free functions are called through their module
   (`doubled::catalog_of`); no `bool` parameter; each function under 100 lines and a cognitive complexity of 25.
7. **The seekers' rows in every world** (ADR321, K3: the seekers can be turned on in the middle of a run, and the
   scene never edits the state from outside). `opening_state_of` authors, after the workplaces' own rows, one
   `EmploymentTerms` (the host's site and the rate of the host's own row, the home's household as payee) and one
   member row of 0 hours for every ordered pair of workplaces of a place: 24 in all, ids `pair_member_id`
   (`spike/closest-ref` `support.rs:2800-2825`). The runner keeps every pool's members (`members_of` at the
   opening), distributes each pool's receipt over all of them, keeps their closing employed and reserve, and
   writes one member row for each member: the own member's is the pool's hours as today, a pair member's 0. A
   pair member with anyone employed or in reserve on this path is `StaffingError::PopulationInvariant`. Why every
   member: `validate_member_budgets` counts member rows against employment terms (`payments/settlement.rs:117-131`)
   and `advance_records` wants a receipt for every wage member of a staffed site (`financial/layoffs.rs:73-79`).
   The engine's arithmetic is unchanged by rows of 0 (attendance and staffing shares with one non-zero weight,
   no money moved for 0 hours, no record of layoffs from a receipt of zeros); Task 1b's `pc-a6` proves it. Three
   pinned counts and one loop move, and the lead accepts them here: `tests/doubled.rs`
   `check_employment_and_taxes`: 32 rows; its loop asserts payee and member id for the eight own rows, and for
   each pair row the host's site, the host's rate, the home's household as payee and `pair_member_id`;
   `tests/runner.rs` `the_runner_keeps_the_member_receipts` 8 members to 32 and 8 member labor rows to 32 (the own
   rows as today, the pair rows 0). The client's `frame.rs` reads people at work by the site's workers and would
   be overwritten by the pair receipts; it sums `opening_employed` by the member's own household instead. The
   client's `reading.rs` `read_work` skips a receipt whose payee is not the workplace's own household and whose
   `attended_hours` is 0. So its pin of 8 flows (`the_quiet_period_gives_480_hours_and_no_idle_hour`) stays, no
   flow drawn today changes (`work_flows` already skips flows of 0), and a household's real hours after a move
   still show.

- [ ] **Step 1: Write the crate's failing tests** in `tests/worlds.rs`:
  - `the_plain_world_opens_with_10320_dollars_and_eighty_people`: ten household accounts (no 22, 23); cohorts
    `[15, 5, 5, 5, 10]` a place; owners $800; no `Public` account; no tax, budget, allocation or program; pools at
    8 hours a person; labor rows 120/40/40/40 a place; the catalog's needs and wants 30 rows each; total money
    10,320,000,000.
  - `the_national_figures_step_by_a_fortieth_and_double_the_site_cash`: steps 300_000, 625_000, 750_000,
    950_000 micro-units at both places, minimum 1_000_000 and maximum 1_000_000_000; site cash $2,400, $1,760,
    $1,760, $2,800; total money 20,960,000,000 (fund) and 19,040,000,000 (plain).
  - `each_opening_push_moves_only_its_figure` (fund, small): P1 owner cohorts 4 and 4, their stocks and purchase
    limits 8; P7 cohorts 12; P3 shop cash $700 in both places, total 10,840,000,000; P4 the four rows at each
    clinic's site (its own and the three of other households) `Wage($11)` in both places, every other row $10; P4a
    only the four rows at clinic A's site at $11; P5 the 16 fund rows at 1,125 bps and the 16 treasury rows at 500;
    every other part of the state equal to the quiet opening's.
  - `the_power_cut_at_the_opening_plans_in_ten_hour_batches`: utility commitments and planned batches 12, its
    nameplate rows 12 in every period, its labor 120 hours; `runner.shocks()` holds `PowerCut` from period 1 where it
    is pushed; P6a in place A only, place B as quiet; `lift` refused with `HoldsUntilStartOver`.
  - `a_push_the_world_cannot_take_is_refused`: P5 in the plain world gives `PushNotInThisWorld`; P5 in
    `Places::A` gives `PushOnOnePlace`.
  - `the_scene_world_is_the_runner_s_opening`: three steps of `Runner::open()` and of
    `Runner::open_world(&World::scene())` give equal histories.
  - `every_world_authors_the_seekers_rows` (moved from Task 3's `the_seekers_world_authors_every_pair`): in each
    of the four worlds 24 pair rows, 12 a place, each at 0 hours, at its host's rate, its payee the home's
    household, ids `pair_member_id`; no pair of two places.
  - `the_pair_rows_take_nothing`: 34 steps of `Runner::open()`: in every period each pair member's staffing
    receipt and member labor row is 0 in every field, and the own rows equal those of the same period's pool.
  The crate's tests as built pass unchanged, but for the three counts and the loop of decision 7.
- [ ] **Step 2: Run them and see them fail.** `mise run rust:test:q -- -p babylon-circuit-worlds`. Expected: does
  not compile, no `World`.
- [ ] **Step 3: Implement** the world, the per-world builders, the runner's constructor, checks and read access.
  Run the crate's tests. Expected: all pass.
- [ ] **Run the gate,** with `-p babylon-circuit-worlds` and the client's small-world tests (Global Constraints).
  **Commit** `feat(circuit-worlds): the plain world, the national figures and the pushed openings`.

### Task 1b: The bench in the repository, with no new rule (`pc-a6`)

**Files:**
- Modify (the engine): `rust/crates/babylon-material-circuit/Cargo.toml` (`[dev-dependencies]`); `rust/Cargo.lock`.
- Create (the bench): `tests/adjustment_bench.rs`; `tests/adjustment_bench/{runs,rows,compare}.rs`;
  `tests/adjustment_bench/digests/pc-a6-400.txt`, `pc-a6-nat-400.txt`.

**Interfaces:**

```rust
// tests/adjustment_bench/runs.rs
/// The rules a set runs with. Task 1b has one; each rule task adds the next.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Form { A6 }
/// One of the 25 runs: its file name (`plain-quiet`, ..., `fund-P8a`), its world, and the shocks struck
/// through `Runner::strike` before the first step.
pub(crate) struct BenchRun {
    pub(crate) name: &'static str,
    pub(crate) world: World,
    pub(crate) strikes: Vec<(Shock, Places, Lasts)>,
}
/// The 25 runs in the prototype's order: plain quiet, P1, P2, P3, P4, P6, P7, P8, P2a, P4a, P6a, P8a, then
/// fund quiet, P1, P2, P3, P4, P6, P7, P8, P5, P2a, P4a, P6a, P8a.
pub(crate) fn runs(form: Form, scale: Scale) -> Vec<BenchRun>;
// tests/adjustment_bench/rows.rs
/// One run of `periods` periods through `Runner`, reduced to its projected rows (header and one line a period).
pub(crate) fn rows(run: &BenchRun, periods: u64) -> String;
/// Exact dollars from micro-units, as the prototype writes them.
pub(crate) fn money(micro: i128) -> String;
// tests/adjustment_bench/compare.rs
/// The file without its `flow_` columns.
pub(crate) fn project(text: &str) -> String;
/// Lowercase hex sha256 of `text`'s bytes (`content_digest::sha256_of` of `babylon_kernel`).
pub(crate) fn digest_hex(text: &str) -> String;
/// Panics naming every run whose digest differs from the fixture's, with what decision 6 says.
pub(crate) fn assert_set(set: &str, produced: &[(&str, String)], fixture: &str);
```

**Decisions:**
1. **What the bench keeps.** The bench takes the world, the shocks and the period loop from `babylon-circuit-worlds`
   (Task 1a). It keeps only what is its own: the list of runs, the row writer, the projection and the digest
   comparison. It has no loop of its own and no `World` of its own. A difference between the crate's world and the
   reference rows is mended in the crate, never in the comparison. The game's `tests/small_world/` is not touched,
   but for the one literal Task 2 adds a field to.
2. **The engine's dev-dependency.** `babylon-material-circuit/Cargo.toml` `[dev-dependencies]` gains
   `babylon-circuit-worlds = { path = "../babylon-circuit-worlds" }`, before `serde_json`. Only the engine's
   integration tests (`tests/`) may use it: its unit tests would see a second copy of every engine type. In
   `rust/Cargo.lock` the engine's `dependencies` become `"babylon-circuit-worlds"`, `"babylon-kernel"`,
   `"serde_json"`, and nothing else moves. Write it offline from `rust/`: `mise exec -- cargo metadata --offline
   --format-version 1 > /dev/null`; check `git diff rust/Cargo.lock` shows that one line; never `cargo update`.
3. **The row writer** opens `Runner::open_world(&run.world)`, strikes `run.strikes`, steps `periods` times and
   after each step writes one line from `runner.history()`'s last result, `runner.state()` and `runner.catalog()`,
   the prototype's columns in its order (`spike.rs` `write_run`, `line`, `markets`, `money`; `support.rs`
   `snapshot`): names of accounts and sites as the prototype writes them (`cash_w_utility_a`, `cash_public`, ...),
   accounts of `unmet_` and `standard_` in the order of those names. `out_` is the production receipts times the
   catalog's output a batch, and a shop's food received; it is not `summary.made`. No `flow_` column is written.
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
8. **Style.** Types are imported and used bare; free functions are called through their module
   (`content_digest::sha256_of`); no `bool` parameter; each function under 100 lines and a cognitive complexity of
   25, so the writer is one function a group of columns.

- [ ] **Step 1: Write the bench's unit tests** in `compare.rs` and `rows.rs`:
  - `money_is_written_as_the_prototype_writes_it`: `money(12_000_000) == "12"`, `money(625_000) == "0.625"`,
    `money(-1_500_000) == "-1.5"`, `money(0) == "0"`.
  - `the_projection_drops_only_flow_columns`: for `"period\tflow_x\tcash_a\n1\t2\t3\n"` the projection is
    `"period\tcash_a\n1\t3\n"`; a text with no `flow_` column is returned unchanged.
- [ ] **Step 2: Write the quick test** `the_doubled_quiet_world_is_still_for_34_periods` (not ignored): for both
  worlds' `quiet` run at both scales, every one of 34 projected lines after the header equals the first, apart
  from its `period` field; `hours_attended` is 480.
- [ ] **Step 3: Write the long tests** `reproduces_pc_a6_400` and `reproduces_pc_a6_nat_400` (`#[ignore]`), each
  `assert_set` over the 25 runs at 400 periods against its fixture. Add the dev-dependency and write the lock.
  Write the runs and the writer; make the fixture with `print_reference_digests`.
- [ ] **Step 4: Run** the quick and unit tests, then the long tests in the background. Expected: 25 of 25 at both
  scales, with the seekers' rows in every world (Task 1a, decision 7): this is also the proof that rows no rule
  reads change no compared column. If not, find the first differing column. A cause in the crate's world or the
  writer is fixed there; a cause in the engine (the merged prototype's engine with every switch off differs from
  this branch) is a stop: report it. If the difference goes away with the pair rows left out (a local run, not
  committed), stop and report: the fallback is a `World` field that authors them only when the world opens with
  seekers, the scene's world always, and the plan says the bench then proves nothing of the scene's opening.
- [ ] **Run the gate. Commit** `test(material-circuit): the doubled bench of the restoring-forces rounds`.

### Task 2: The setting

**Files:**
- Create: `src/adjustment.rs`, `src/adjustment/policy.rs`.
- Modify: `src/clearing/rule.rs` (the field); `src/catalog.rs` (admission, tests); `src/wire/catalog.rs`
  (`bytes`); `src/lib.rs` (exports); every hand-built `MarketClearingPolicy` gets `adjustments: Vec::new()`
  (`rg -n 'MarketClearingPolicy \{' rust/crates` prints 18 lines; two are the struct and its `impl` in
  `clearing/rule.rs`, two are `fn` lines that return the type (`src/catalog.rs` `fn policy` and the small worlds'
  `doubled/catalog.rs` `fn market_clearing`), the other 14 are literals, among them
  `tests/small_world/support.rs:430` and the small worlds' `doubled/catalog.rs`, which gets `adjustments:
  rules.to_vec()`);
  `tests/adjustment_bench/runs.rs` (the form's list) and `tests/adjustment_bench/sets.rs` (the quick test of Step
  4);
  `babylon-circuit-worlds` `src/doubled/world.rs` (`World` gains `rules`, `switches_at` and `switches`),
  `src/doubled/catalog.rs` (`catalog_of` takes the rules), `src/runner.rs` (`mod rules; pub use`),
  `src/runner/rules.rs` (create), `src/runner/run.rs` (the rules, the cache key, `turn_on`),
  `src/runner/result.rs` (`PeriodResult.rules`), `src/runner/error.rs` (`RunnerError::Rule`), `src/lib.rs`,
  `tests/runner.rs`; `contracts/material_circuit_v4.yaml` and the digest.

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
    /// A goods price steps down when goods beyond the buffer went unsold, under its cost if it must (A1;
    /// ADR321, K1).
    GoodsStepDown,
}
impl AdjustmentRule {
    /// The rule's tag in the catalog bytes: 1 to 6 in the order above.
    pub(crate) const fn tag(self) -> u8;
    /// The rules this one needs, in the order above: `StopWithoutPay` needs `SeekingInPlace`; `OwnerRestart`
    /// needs `HiringWithinMeans`, `StopWithoutPay` and `RestingPrice`; the others need none. The one table that
    /// `refuse_combinations` and the runner read.
    #[must_use] pub const fn needs(self) -> &'static [AdjustmentRule];
}
/// Whether `rules` asks for a rule of this kind.
pub(crate) fn asks(rules: &[AdjustmentRule], rule: AdjustmentRule) -> bool;
/// The restart's periods of outlay, when the list asks for the restart.
pub(crate) fn restart_outlay_periods(rules: &[AdjustmentRule]) -> Option<u64>;
// src/clearing/rule.rs, MarketClearingPolicy gains:
/// The rules of ADR314 this policy asks for, in the order of `AdjustmentRule`, each once.
/// Empty keeps today's behaviour and bytes.
pub adjustments: Vec<AdjustmentRule>,
// babylon-circuit-worlds src/doubled/world.rs, World gains (empty in World::scene()):
/// The rules the world opens with: `Runner::open_world` turns each on, in order, before the first step.
pub rules: Vec<AdjustmentRule>,
impl World {
    /// The six rules in the order of `AdjustmentRule`, the restart with the periods of outlay of `scale`
    /// (1 period of outlay at the small figures, 2 at the national).
    #[must_use] pub const fn switches_at(scale: Scale) -> [AdjustmentRule; 6];
    /// `switches_at(self.scale)`: the six rules of this world.
    #[must_use] pub const fn switches(&self) -> [AdjustmentRule; 6];
}
// babylon-circuit-worlds src/doubled/catalog.rs (replaces Task 1a's signature)
/// # Errors
/// As `catalog`; `WorldError::Engine` when the engine's admission refuses the rules.
pub fn catalog_of(world: &World, figures: &Figures, rules: &[AdjustmentRule])
    -> Result<MaterialCatalog, WorldError>;
// babylon-circuit-worlds src/runner/rules.rs
/// A rule of the run and the first period closed under it.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RuleOn { pub rule: AdjustmentRule, pub from: u64 }
/// Where a rule's switch stands for the next period.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Switch {
    /// On from `from`; it holds until the run is started over.
    On { from: u64 },
    /// Off; `turn_on` would turn it on from the next period.
    Ready,
    /// Off; it waits for these rules, in the order of `AdjustmentRule`.
    Waits { needs: Vec<AdjustmentRule> },
}
/// Why a rule was not turned on. Nothing changes then.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum RuleError {
    /// The run is stopped.
    Stopped,
    /// A rule of this kind is on already.
    AlreadyOn { rule: AdjustmentRule, from: u64 },
    /// A rule it needs is not on.
    Waits { rule: AdjustmentRule, needs: Vec<AdjustmentRule> },
    /// The engine's admission refused the catalog of the next period with the rule.
    Refused { rule: AdjustmentRule, error: WorldError },
}
/// The rule's name, as the scene and the refusals say it.
#[must_use] pub const fn rule_name(rule: AdjustmentRule) -> &'static str;
// impl Display for RuleError, and impl Error.
// babylon-circuit-worlds src/runner/run.rs
impl Runner {
    /// Turn a rule on from the next period (`next_period()`, the `from` a strike gets). It holds until the run is
    /// started over.
    /// # Errors
    /// `RuleError`, in this order: `Stopped`; `AlreadyOn` (the same kind, any `outlay_periods`); `Waits` (a rule of
    /// `needs` is not on); `Refused` (the catalog of the next period's figures with the rule added).
    pub fn turn_on(&mut self, rule: AdjustmentRule) -> Result<(), RuleError>;
    /// The rules on, in the order turned on.
    #[must_use] pub fn rules(&self) -> &[RuleOn];
    /// The rules the catalog of `period` asks for, in the order of `AdjustmentRule`.
    #[must_use] pub fn rules_at(&self, period: u64) -> Vec<AdjustmentRule>;
    /// Where the switch of a rule of this kind stands.
    #[must_use] pub fn switch(&self, rule: AdjustmentRule) -> Switch;
}
// babylon-circuit-worlds src/runner/result.rs, PeriodResult gains:
/// The rules its catalog asked for, in the order of `AdjustmentRule`.
pub rules: Vec<AdjustmentRule>,
// babylon-circuit-worlds src/runner/error.rs, RunnerError gains:
/// `open_world` could not turn on a rule of the world.
Rule(RuleError),
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
5. **The bench's form.** `Form::rules(self, scale: Scale) -> Vec<AdjustmentRule>`, taken from
   `World::switches_at(scale)`; `Form::A6` gives an empty list. `OwnerRestart`'s `outlay_periods` is 1 at the small
   figures and 2 at the national (`SPIKE_J_PERIODS`). `Form::ALL` lists the forms built so far. `runs()` puts the
   list in each run's `World.rules`; `Runner::open_world` turns them on before the first step. No catalog is built
   in the bench. The small worlds' test `the_scene_asks_for_no_rule` pins `World::scene().rules` empty and the scene
   catalog's `adjustments` empty.
   `World::scene()` stops being `const` here, since it holds a `Vec`.
6. **The runner's rules** (ADR321, K3). The runner keeps `Vec<RuleOn>` and its world. `turn_on` checks in the
   order of its `# Errors`, then builds `catalog_of(world, &book.figures(next), &with_the_rule)` and caches it;
   only then is the rule recorded, with `from = self.state.period`. So a refusal changes nothing, and the
   engine's admission is the last word (until Task 8 it refuses a rule not yet built). `open_world` opens with no
   rule, then calls `turn_on` for each of `world.rules`, so its rules are on from period 1: one road for the bench
   and the scene. There is no turn-off; a new runner clears every rule and every shock.
7. **The cache** is `Vec<(CatalogKey, MaterialCatalog)>` with a private `CatalogKey { figures: Figures, rules:
   Vec<AdjustmentRule> }`. `advance` builds the key from `book.figures(period)` and `rules_at(period)` and puts
   the rules in `PeriodResult.rules`.
8. **Words.** `rule_name` gives the label: "A bound on hiring", "People look for work in their place", "No money,
   no work", "A resting price", "The owner restarts a stopped workplace", "A goods price steps down". Inside a
   sentence the same words stand in lower case. `RuleError` says: "the run is stopped"; "{name} is on from period
   {from} and holds until you start over"; "{name} waits for {needs in lower case, joined by \" and \"}"; "the
   engine refused {name in lower case}: {error}", where `{error}` is the inner error of `WorldError::Engine`, not
   `WorldError`'s own words. `RunnerError::Rule` says "the world's rules: {error}".

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
  `PINNED_BASE_DIGEST` and `PINNED_POLICY_DIGEST` pass unchanged. Also `needs_is_the_table_of_the_refusals`:
  for each rule, `refuse_combinations` refuses the list of the rule alone exactly when `needs()` is not empty,
  and passes it with every rule it needs added, and the rules those need, in the order of `AdjustmentRule` (for
  `OwnerRestart`: `[HiringWithinMeans, SeekingInPlace, StopWithoutPay, RestingPrice, OwnerRestart {
  outlay_periods: 1 }]`).
  In the small worlds' `tests/runner.rs`:
  - `a_rule_not_yet_built_is_refused_by_turn_on`: `Runner::open()`, two steps, `turn_on(GoodsStepDown)` gives
    `RuleError::Refused { rule: GoodsStepDown, error: WorldError::Engine(..MarketClearingInvariant..) }`;
    `rules()` is empty, `switch(GoodsStepDown)` is `Ready`, and five more steps equal a twin runner's that was
    never asked. Task 8 removes this test with `NOT_YET_BUILT`.
  - `a_switch_says_what_it_waits_for`: at the opening, `switch(StopWithoutPay)` is `Waits { needs:
    [SeekingInPlace] }` and `turn_on(StopWithoutPay)` is `RuleError::Waits` with the same list;
    `switch(OwnerRestart { outlay_periods: 1 })` is `Waits { needs: [HiringWithinMeans, StopWithoutPay,
    RestingPrice] }`; `switch(HiringWithinMeans)` is `Ready`.
  - In the existing `the_run_stops_at_its_horizon`, after the stop, add: `turn_on(HiringWithinMeans)` is
    `RuleError::Stopped`.
  - `each_period_says_its_rules`: three steps of `Runner::open()`: every `PeriodResult.rules` is empty.
- [ ] **Step 2: Run them and see them fail.** `mise run rust:test:q -- -p babylon-material-circuit -E
  'test(adjustments) | test(admission_refuses) | test(needs_is)'`, then `mise run rust:test:q -- -p
  babylon-circuit-worlds -E 'test(a_rule_not_yet_built_is_refused_by_turn_on) |
  test(a_switch_says_what_it_waits_for) | test(the_run_stops_at_its_horizon) | test(each_period_says_its_rules)'`.
  Expected: does not compile, no field `adjustments`.
- [ ] **Step 3: Implement** the type, the field, the bytes, the refusals, the 14 literals, the contract and the
  digest; `AdjustmentRule::needs`; in `babylon-circuit-worlds`, `RuleOn`, `Switch`, `RuleError`, `turn_on`,
  `rules`, `rules_at`, `switch`, `World::switches` and `switches_at`, the cache key and `PeriodResult.rules`.
- [ ] **Step 4: Run** the engine's tests, the small worlds' tests and the bench's quick tests. Add the bench's
  quick test `opening_with_a_form_is_turning_its_rules_on_first`: for each `Form::ALL` and both scales, the runs
  `fund-quiet`, `fund-P2`, `fund-P6` and `plain-P2`, 34 periods, opened as `rows` does (`open_world(&run.world)`,
  which turns the rules on, then `run.strikes` struck) and as `open_world` of the same world with no rules, then
  `run.strikes` struck, then `turn_on` of each of the form's rules in order, all before the first step: equal
  `state_digest` in every period and equal projected rows. So the order of turn-ons and strikes before the first
  step does not matter. With `Form::A6` alone this is trivial; each rule task's form makes it bite. Expected: all
  pass, no pinned value changed.
- [ ] **Run the gate. Commit** `feat(material-circuit): let a market policy name the rules of ADR314`.

### Task 2c: The rules' switches stand ready in the scene (the client; no switch yet)

**Files:**
- Create: `rust/crates/babylon-client/src/small_world/rules.rs`.
- Modify (under `rust/crates/babylon-client/src/`): `small_world.rs` (`pub mod rules;`); `small_world/scene.rs`
  (`SceneCommand::TurnOn` and `SceneCommand::Lower`, the stage's `turn_on`, the observer, the paint chain);
  `small_world/panel.rs` (`Lower`, `PanelView.lower`, `PanelButton::Lower`, `LowerBody`, the tabs of the rail's
  lower part, `paint_lower`, `ShockNotice::say`, `mark` made `pub(super)`); `small_world/script.rs`
  (`ScriptCommand::Rule`, `ScriptReport.rules`); `small_world/scene_tests.rs`; `small_world/script_tests.rs`.

**Interfaces:**

```rust
// src/small_world/rules.rs
/// A rule of the closest form as the scene names it: the kinds of `World::switches`, in the order of
/// `AdjustmentRule`.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum SceneRule { HiringWithinMeans, SeekingInPlace, StopWithoutPay, RestingPrice, OwnerRestart, GoodsStepDown }
impl SceneRule {
    pub const ALL: [SceneRule; 6];
    /// The order of the list on screen, which is the order the rules are built and the order of the list the
    /// Director picked: the seekers, the bound, the stop rule, the resting price, the restart, the step down.
    pub const LISTED: [SceneRule; 6];
    /// Its place in `World::switches`: 0 to 5 in the order of `ALL`.
    #[must_use] pub const fn index(self) -> usize;
    /// `hiring_within_means`, `seeking_in_place`, `stop_without_pay`, `resting_price`, `owner_restart`,
    /// `goods_step_down`.
    #[must_use] pub const fn script_name(self) -> &'static str;
    /// The script's name read back.
    #[must_use] pub fn named(name: &str) -> Option<SceneRule>;
    /// The rule of this kind that `world` turns on: `world.switches()[self.index()]`.
    #[must_use] pub fn rule(self, world: &World) -> AdjustmentRule;
    /// The kind of a rule (`OwnerRestart` with any `outlay_periods`).
    #[must_use] pub const fn of(rule: AdjustmentRule) -> SceneRule;
}
/// The rules whose switches the scene shows: the first of `SceneRule::LISTED`, as far as they are built. Each
/// rule's companion task appends its own; nothing else does.
pub const SHOWN_RULES: &[SceneRule] = &[];
/// Whether the rail has the rules' tab: every other place reads this, not `SHOWN_RULES.is_empty()`.
#[allow(clippy::const_is_empty, reason = "the list grows task by task")]
pub const RULES_SHOWN: bool = !SHOWN_RULES.is_empty();
/// The title of the list's one column.
pub const FROM_LINE: &str = "on from period";
/// The standing lines under the list.
pub const RULES_LINE: &str =
    "Turned on, a rule stays until you start over. A rule that needs another waits for it.";
/// A rule's switch: the button of its row in the rules' tab.
#[derive(Component, Clone, Copy, Debug, PartialEq, Eq)]
pub struct RuleButton(pub SceneRule);
/// The list of the rules' tab, rebuilt when the runner changes.
#[derive(Component)] pub struct RulesBody;
/// One row of the list as it is drawn.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SwitchRow {
    pub rule: SceneRule,
    /// `rule_name` of the world's rule of this kind.
    pub name: &'static str,
    /// The first period closed under it, while it is on.
    pub from: Option<u64>,
    /// "(needs: {names})" while it waits: each name with its first letter in lower case, joined by "; ".
    pub needs: Option<String>,
}
/// The row of one rule from where its switch stands.
#[must_use] pub fn switch_row(rule: SceneRule, name: &'static str, switch: &Switch) -> SwitchRow;
/// A row for each of `SHOWN_RULES`, in order: `switch_row` of `runner.switch(rule.rule(runner.world()))`.
#[must_use] pub fn switch_rows(runner: &Runner) -> Vec<SwitchRow>;
/// The runner's refusal in its own words, the first letter in upper case.
#[must_use] pub fn rule_refusal_words(error: &RuleError) -> String;
/// The rules' tab: `RulesBody`, then `RULES_LINE`, then a `NoticeLine`.
pub fn spawn_rules_tab(body: &mut ChildSpawnerCommands);
/// Rebuild the list when the runner changed.
pub fn paint_rules(mut commands: Commands, scene: Res<SceneRunner>, body: Query<Entity, With<RulesBody>>);
/// A press of a rule's row.
pub fn pressed(event: On<PointerClick>, buttons: Query<&RuleButton>, mut commands: MessageWriter<SceneCommand>);
// src/small_world/panel.rs
/// What the lower part of the rail shows.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum Lower { #[default] Shocks, Rules }
// PanelView gains (its `Default` gives `Lower::Shocks`):
pub lower: Lower,
// PanelButton gains:
Lower(Lower),
/// A body of the rail's lower part, shown while the view's `lower` is its own.
#[derive(Component, Clone, Copy, Debug, PartialEq, Eq)]
pub struct LowerBody(pub Lower);
impl ShockNotice {
    /// Show these words for `NOTICE_SECONDS`.
    pub fn say(&mut self, words: String);
}
pub(super) fn mark(node: &mut Node, border: &mut BorderColor, selected: bool);   // was private
/// A tab's caption: "Shocks" or "Shocks · {count} holding"; "Rules" or "Rules · {count} on". The count is left
/// out when it is 0.
#[must_use] pub fn lower_caption(lower: Lower, count: usize) -> String;
/// Show the body of the chosen tab and write the two tabs' captions.
pub fn paint_lower(
    view: Res<PanelView>,
    scene: Res<SceneRunner>,
    mut bodies: Query<(&LowerBody, &mut Node)>,
    tabs: Query<(&PanelButton, &Children)>,
    mut captions: Query<&mut Text>,
);
// src/small_world/scene.rs, SceneCommand gains:
TurnOn(SceneRule),
Lower(Lower),
// src/small_world/script.rs, ScriptCommand gains:
Rule(String),
// ScriptReport gains:
/// The rules on, in the order turned on: the script's name and the first period closed under it.
pub rules: Vec<(String, u64)>,
```

`AdjustmentRule` is imported from `babylon_material_circuit`; `World`, `Runner`, `RuleOn`, `Switch`, `RuleError`
and `rule_name` from `babylon_circuit_worlds`, as Tasks 1a and 2 export them.

**Decisions:**
1. **Where the switches stand: the lower part of the rail, as a list.** The Director picked a list in the dialog
   of 23 November: the six rules one under another, a column "on from period", "(needs: ...)" under a rule that
   waits, and the two standing sentences. The bar cannot hold six switches: a second row of them is wider than
   the window once periods have three digits, and a taller bar cuts the rail's list of shocks. So the bar and
   `BAR_HEIGHT` do not change, and `the_bar_has_one_row` stays as it is.
2. **One list.** `SHOWN_RULES` is empty here, so `RULES_SHOWN` is false: the rail's lower part keeps its title
   "Shocks", no tab and no list is spawned, and nothing on screen changes in this task. Each companion (3c to 8c)
   appends its rule, in the order of `SceneRule::LISTED`, in the same commit as its marks. The gate's clippy leg
   (`-D warnings`) would refuse `.is_empty()` on a constant (`const_is_empty`), so only `RULES_SHOWN` reads it,
   under its one `#[allow]`; every other place reads `RULES_SHOWN`. If the leg does not flag it, drop the
   attribute; do not loosen anything else.
3. **The lower part of the rail** (`panel.rs` `spawn_rail`, its second section). The shock controls with their
   notice and `ShocksBody` go into one column node with `LowerBody(Lower::Shocks)`, with and without rules, so
   the shocks' tree is one. When `RULES_SHOWN`, the title "Shocks" gives way to a row of two tabs (`column_gap` 4,
   `margin` bottom 4) built as the table's are: `spawn_pressed(tabs, PanelButton::Lower(Lower::Shocks), "Shocks",
   13.0)` and the same for `Lower::Rules` with "Rules"; and a second column node with `LowerBody(Lower::Rules)`
   follows, filled by `rules::spawn_rules_tab`. `chosen` gains the arm `PanelButton::Lower(lower) => Some(*lower
   == view.lower)`, so `paint_choices` marks the chosen tab. `press_panel` writes `SceneCommand::Lower(lower)`,
   and the stage sets `view.lower`. `paint_lower` gives the body of `view.lower` `Display::Flex` and the other
   `Display::None`, and writes the captions (`lower_caption` with the count of the rows of `shock_rows` that
   hold, and with `runner.rules().len()`) into the one text child of each tab, with `set_if_neq`. While
   `RULES_SHOWN` is false the shocks' body is shown whatever `view.lower` says. The view opens on the shocks;
   "Start over" keeps the tab (`start_over` resets only `view.period`).
4. **The list** (`paint_rules`, as `paint_shocks` rebuilds its own: only when the runner changed). `RulesBody`
   is a column with `row_gap` 2. Its first child is a node of the full width with `justify_content: FlexEnd`
   that holds `FROM_LINE` (Body 11, `GRAY`), so the title ends where the periods end. Then one column node for
   each of `switch_rows`: its row (`column_gap` 4), and under it, while the rule waits, its `needs` line (Body
   11, `GRAY`, `margin` left 12). The row holds a button with `RuleButton(rule)`, built as
   `panel::spawn_pressed` builds one (`ui::pressable()`, height 28, border 1, padding 8, no background) but
   with `flex_grow: 1.0` and its caption, the rule's name (Body 13), at the left; then a node 44 wide with
   `justify_content: FlexEnd` that holds `from` as a plain number (Body 13, `PAPER`) while the rule is on, and
   nothing otherwise. On: `panel::mark(.., true)` and the name in `PAPER`. Ready: no mark, the name in `PAPER`.
   Waiting: no mark, the name in `GRAY`. Every text is built by `controls::text`, which carries
   `DeclaredSurface { id: SurfaceId::SmallWorld }`.
5. **Under the list,** as siblings of `RulesBody` that no repaint rebuilds: `RULES_LINE` (`controls::text`,
   Body 11, `GRAY`, `margin` top 6; it wraps to two lines), then a `NoticeLine` built as the shocks' own
   (`controls::text("", 12.0, theme::RED, ..)`, `margin` top 4). `paint_notice` already writes every
   `NoticeLine`, so a refusal is read in whichever tab is shown.
6. **The rule a switch turns on** is `rule.rule(scene.runner.world())`: the scene's world's own (the restart with
   1 period of outlay at the small figures). `SceneRule::of` matches the kind, so the restart's figure is never
   written in the client.
7. **A press** (a primary click only) writes `SceneCommand::TurnOn(rule)` whatever its row says.
   `Stage::turn_on` takes the rule first (`let wanted = rule.rule(self.scene.runner.world());`, since the call
   borrows the runner mutably), then calls `Runner::turn_on(wanted)`; on `Err(error)` it calls
   `self.notice.say(rules::rule_refusal_words(&error))`. Either way it sets `self.view.lower = Lower::Rules`, so
   a script's capture after a rule shows the list. A waiting rule, a rule on, a stopped run and (until Task 8) a
   rule not yet built are all told that way, and the runner changes nothing (Task 2, decision 6). "Start over"
   clears every rule, since it opens a new runner (`scene.rs` `start_over`); nothing is added for it.
8. **The script.** `{"rule":"<name>"}` with the six names of `script_name`; `check_names` refuses any other name
   before the window opens; `begin` writes `SceneCommand::TurnOn` and checks as a strike does, so a refused rule
   ends the script with `refusal.json`. `ScriptReport.rules` lists `runner.rules()` as `(script_name, from)`.
9. **Words.** The names and the refusals are the runner's (Task 2, decision 8), a refusal's first letter raised.
   `FROM_LINE`, "(needs: ...)" and `RULES_LINE` are the words of the list the Director picked. The picked list
   named two rules shorter ("People look for work", "The owner restarts a workplace"); the scene says the
   runner's names, one source for the list, the refusals and the script's report. No word says the bench
   measured a rule (ADR321).
10. **Order of painting:** `panel::paint_lower` and `rules::paint_rules` join the `Paint` chain after
    `panel::paint_shocks`; `rules::pressed` is added as an observer beside `panel::pressed`.
11. **Room.** At 1366 x 768 the lower part has about 300 px under its tabs, and six rows with two needs lines,
    the standing lines and the notice take about 280. The sizes above are the lead's by reckoning; the lead
    looks at the real window after Task 3c and tunes them, and a builder does not judge them.
12. **A literal of `PanelView`** in a test or in the code gains `lower` (or `..PanelView::default()`). That
    changes no pinned value.

- [ ] **Step 1: Write the failing tests** (in `scene_tests.rs` unless named otherwise; `scene_app(None)` as built).
  Write the variants qualified (`SceneRule::...` for a scene's rule, `AdjustmentRule::...` inside `Switch` and
  `RuleError`): the two enums share their names, and the lines below leave the type out only to stay short.
  - `scene_rules_follow_the_world_s_switches` (in `rules.rs`): for each of `SceneRule::ALL`, `rule.index()` is
    its place in `SceneRule::ALL`, `SceneRule::of(World::scene().switches()[rule.index()]) == rule`, and
    `SceneRule::named(rule.script_name()) == Some(rule)`; `SceneRule::OwnerRestart.rule(&World::scene())` is
    `AdjustmentRule::OwnerRestart { outlay_periods: 1 }`; `SceneRule::ALL` is sorted; `SceneRule::LISTED` is
    `[SeekingInPlace, HiringWithinMeans, StopWithoutPay, RestingPrice, OwnerRestart, GoodsStepDown]`;
    `SHOWN_RULES == &SceneRule::LISTED[..SHOWN_RULES.len()]`; the six script names as in the Interfaces;
    `named("everything")` is `None`.
  - `a_rule_s_refusal_is_told_in_the_runner_s_words` (in `rules.rs`): `Waits { rule: StopWithoutPay, needs:
    vec![SeekingInPlace] }` gives "No money, no work waits for people look for work in their place";
    `AlreadyOn { rule: SeekingInPlace, from: 14 }` gives "People look for work in their place is on from period 14
    and holds until you start over"; `Stopped` gives "The run is stopped".
  - `a_row_says_where_its_switch_stands` (in `rules.rs`): `switch_row(SeekingInPlace, "People look for work in
    their place", &Switch::On { from: 14 })` has `from: Some(14)` and `needs: None`; with `Switch::Ready` both
    are `None`; `switch_row(StopWithoutPay, .., &Switch::Waits { needs: vec![SeekingInPlace] })` has `needs:
    Some("(needs: people look for work in their place)")`; with `needs: vec![HiringWithinMeans, StopWithoutPay,
    RestingPrice]` it is `Some("(needs: a bound on hiring; no money, no work; a resting price)")`.
    `switch_rows(&Runner::open()?)` has one row for each of `SHOWN_RULES`, in order, each named by `rule_name`.
  - `the_lower_tabs_count_what_holds` (in `panel.rs`): `lower_caption(Lower::Rules, 0)` is "Rules" and with 2 it
    is "Rules · 2 on"; `lower_caption(Lower::Shocks, 0)` is "Shocks" and with 3 it is "Shocks · 3 holding".
  - `the_rail_has_the_rules_tab_only_for_rules_shown`: with `RULES_SHOWN` false, no `PanelButton::Lower` and no
    `RulesBody` exist, "Shocks" is on screen once, and the one `LowerBody` is the shocks', shown. Otherwise two
    `PanelButton::Lower` tabs captioned "Shocks" and "Rules", the shocks' body shown and the rules' body
    `Display::None`; after a click on the rules' tab and two updates the two are swapped, `view.lower` is
    `Lower::Rules`, the tab's left border is `px(3)`, and under the rules' `LowerBody` stand `RulesBody`, whose
    descendants hold `FROM_LINE` and then `SHOWN_RULES.len()` `RuleButton`s in the order of `SHOWN_RULES`, then
    `RULES_LINE`, then a `NoticeLine`. Written so that it holds in every companion.
  - `a_rule_that_waits_is_refused_in_the_scene_s_words`: `TurnOn(StopWithoutPay)` before any step, two updates: the
    notice reads "No money, no work waits for people look for work in their place"; `runner.rules()` is empty;
    `history` is 0; `view.lower` is `Lower::Rules`.
  - `a_rule_not_yet_built_is_refused_in_the_scene`: one step, `TurnOn(GoodsStepDown)`: the notice starts with
    "The engine refused a goods price steps down: "; `runner.rules()` is empty. Task 8 removes this test, with
    `NOT_YET_BUILT`.
  - `every_shown_rule_turns_on_from_the_next_period_and_holds`: while `RULES_SHOWN` is false it returns
    `Ok(())` before any step. Else two steps; for each of `SHOWN_RULES` in order, with k the number of rules on
    after this click (1 for the first): click its `RuleButton`, two updates: `switch(rule.rule(world))` is `On {
    from: 3 }`, its row holds the text "3", its button's left border is `px(3)` in `YELLOW`, and the rules' tab
    is captioned "Rules · {k} on". Click it again (the list was rebuilt: find the button again): the notice is
    "{name} is on from period 3 and holds until you start over" and `rules()` is unchanged. Then `RULES_LINE`
    is on screen; then `StartOver`: `rules()` is empty, no row holds a period, and the tab is captioned "Rules".
    With `SHOWN_RULES` empty this test checks nothing; each companion makes it bite, as Task 2's
    `opening_with_a_form_is_turning_its_rules_on_first` does for the bench.
  - In `script_tests.rs`: `the_script_names_the_six_rules` (each `{"rule":"<name>"}` parses to `Rule(name)`;
    `{"rule":"everything"}` on line 2 is `Line { line: 2, .. }`).
  - `a_refused_rule_ends_the_script_and_keeps_the_refusal` (in `scene_tests.rs`, beside
    `a_refused_strike_ends_the_script_and_keeps_the_refusal`, with 500 updates as
    `a_script_presses_the_same_controls` has, since a step waits for its beats to rest): script `{"step":1}`,
    `{"rule":"stop_without_pay"}`: replies "done" then "refused" with reason "No money, no work waits for people
    look for work in their place"; `refusal.json` exists and its `rules` is `[]`.
- [ ] **Step 2: Run them and see them fail.** `mise run rust:test:q -- -p babylon-client -E 'test(small_world)'`.
  Expected: does not compile, no module `rules`.
- [ ] **Step 3: Implement** the module, the two commands, the stage's `turn_on`, the lower part's bodies and
  tabs, `paint_lower`, the list, the notice's `say`, the script's command and the report's field.
- [ ] **Step 4: Run them.** Expected: all pass; no pinned value of the client changed, `the_bar_has_one_row`
  among them.
- [ ] **Step 5: The proof script for the lead** (decision 7 of the scene plan's Task 9). Add it to
  `script_tests.rs` as `PROOF_2C` with `the_proof_script_of_task_2c_parses` (4 commands). Hand the lead the command
  `mise exec -- cargo run -p babylon-client -- --small-world --small-world-script <folder>/proof.jsonl` (from
  `rust/`, a folder made by `mktemp -d`) and the script; do not run it:
  `{"step":2}`, `{"report":"before-rules"}`, `{"capture":"before-rules"}`, `{"rule":"stop_without_pay"}`.
  The lead's check: the window looks as at the third look (the lower part titled "Shocks", no tab);
  `before-rules.json` has `"rules": []`; `replies.jsonl` ends with line 4 "refused" and the waiting words;
  `refusal.json` exists.
- [ ] **Run the companion's gate** (Global Constraints). **Commit** `feat(client): the rules' switches stand ready in
  the small world`.

### Task 3: People look for work in their place (`pc-seek`)

**Files:**
- Create: `src/staffing/place.rs`; `src/adjustment/receipts.rs`.
- Modify: `src/staffing.rs` (`mod place; pub use`); `src/transition/state.rs` (`ClosedMaterialPeriod`);
  `src/model.rs` (`MaterialCircuitTransition.adjustments`); `src/financial/layoffs.rs` (advance with moves);
  `src/catalog.rs` (lift the refusal); `src/lib.rs`; the contract and the digest.
- Modify (the small worlds): `src/doubled/staffing.rs` (`pool_members_of`, `places`); `src/runner/run.rs` (from
  the seekers' first period, the staffing step through `staff_in_places`, the members and bindings taken from it,
  each place's people checked); `src/runner/result.rs` (`PeriodReceipts.adjustments`); `tests/worlds.rs`;
  `tests/runner.rs`. The pair rows and `Workplace::pair_member_id` are Task 1a's.
- Modify: the bench: `runs.rs` (`Form::Seek`), `rows.rs` (the seekers' columns); add `digests/pc-seek-400.txt`,
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
// babylon-circuit-worlds src/doubled/staffing.rs
/// Each place's pools: place A's four, then place B's.
#[must_use] pub fn places() -> Vec<StaffingPlace>;
/// Every pool's members at the opening, as `members_of` (Task 1a), one `PoolMembers` a pool in pool order.
/// # Errors
/// As `member_of`.
pub fn pool_members_of(world: &World) -> Result<Vec<PoolMembers>, WorldError>;
// babylon-circuit-worlds src/runner/run.rs
impl Runner {
    /// The staffing after the last step.
    #[must_use] pub const fn staffing(&self) -> &StaffingState;
    /// The members the runner keeps between periods: every pool's, one for each household of its place, on both
    /// paths. The runner's field becomes `Vec<PoolMembers>` here.
    #[must_use] pub fn members(&self) -> &[PoolMembers];
}
// babylon-circuit-worlds src/runner/result.rs, PeriodReceipts gains:
pub adjustments: Vec<AdjustmentReceipt>,
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
7. **The place** is the caller's. Every pool is in exactly one place. The caller is the runner: it passes
   `doubled::places()`, each place of the doubled world its own.
8. **The runner.** Every world holds the pair rows and the runner keeps every pool's members from the opening
   (Task 1a, decision 7). For each period whose rules (`rules_at(period)`) hold `SeekingInPlace`, it staffs with
   `staff_in_places` over its kept members and `doubled::places()` and finishes with
   `finish_with_place_staffing` in place of `advance_staffing`, `distribute_staffing_members` and
   `finish_with_staffing`; it then keeps `PlaceStaffing.members`, the state, and the pools' bindings read from
   `PlaceStaffing.state` (a move changes a pool's labor force, decision 5), which `staffing_requests` takes from
   the next period on. A period without the rule runs the loop of Task 1a. `finish_with_staffing` refuses a
   catalog that asks for `SeekingInPlace` (`MarketClearingInvariant`), as `staff_in_places` refuses one that does
   not, so a wrong path fails loudly in either direction. Turned on in the middle of a run (from period F), the
   first close with the rule is F's; its moves set the people of F + 1; nobody moves in a period before F. The
   members at F are the kept ones, whose own member holds the pool's people (the force never changed before F),
   and the records of layoffs that decide who is covered are the state's, kept since period 1.
   Task 1a's `every_world_authors_the_seekers_rows` replaces this task's `the_seekers_world_authors_every_pair`,
   and `the_quiet_world_without_seekers_has_no_pair` is dropped: by the ruling every world has the rows.
9. **Bench columns:** `seekers_<copy>`, `people_<copy>`, `people_<site>`, `looking_<site>`,
   `covered_own_<site>`, `parked_<site>`, `pair_working_/pair_looking_/pair_covered_<host>_from_<home>`, in the
   prototype's order (`spike.rs` `line`, the step S block). They are computed from `PlaceStaffing` and the state's
   record of layoffs, read through `PeriodResult`, `Runner::staffing`, `Runner::members` and `Runner::state`. The
   runner checks each place's persons (the sum of its pools' labor forces) against the opening's after every
   period, and each workplace's as in Task 1a only for periods closed before the seekers' first period; it
   refuses with `PersonsNotConserved`.

- [ ] **Step 1: Write the failing unit tests** in `src/staffing/place.rs`:
  - `a_host_takes_the_uncovered_first`: two pools of one place, host need 3, the other pool's member reserves
    uncovered 2 and covered 4 (age 0): moves are 2 uncovered, then 1 covered of age 0.
  - `the_highest_wage_is_served_first`: two hosts in one place, wages $11 and $10, each need 2, seekers 3: the $11
    host takes 2, the $10 host 1.
  - `a_seeker_stays_in_their_place`: two places, a host in one and seekers only in the other: no move.
  - `a_move_keeps_every_person`: in each of the above, the sum of every pool's labor force before equals after.
  - `a_pool_in_no_place_is_refused` and `a_pool_in_two_places_is_refused`.
  - `the_old_finish_refuses_a_catalog_that_asks_for_seekers` (`finish_with_staffing` with a catalog asking
    `SeekingInPlace`: `Err(MarketClearingInvariant)`; decision 8).
- [ ] **Step 2: Run them and see them fail** (`-E 'test(place) | test(the_old_finish)'`): `staff_in_places` not
  found.
- [ ] **Step 3: Implement** the step, the receipts, the finish, the contract line (replacing the refusal line of
  Task 2) and the digest. Lift the refusal of `SeekingInPlace`.
- [ ] **Step 4: The runner and the bench.** In the crate: the members and bindings kept from `PlaceStaffing`, the
  runner's call by period, the check by place. In `tests/runner.rs`, the late turn-on script that Tasks 4 to 8
  extend, `const LATE: [(u64, AdjustmentRule); 1] = [(20, SeekingInPlace)]` (turn on after that many steps):
  - `a_late_turn_on_gives_the_same_bytes_twice`: the scene's world with `(HarvestFails, Both, UntilLifted)`
    struck before step 1, `LATE` applied, 60 steps, twice: equal histories and state digests; `rules()` is
    `[RuleOn { rule: SeekingInPlace, from: 21 }]`; `history()[19].rules` is empty, `history()[20].rules` is
    `[SeekingInPlace]`.
  - `nobody_moves_before_the_seekers_are_on`: the same run: no `PlaceMove` receipt in periods 1 to 20.
  - `a_rule_on_cannot_be_turned_on_again`: after `LATE`, `turn_on(SeekingInPlace)` is `RuleError::AlreadyOn {
    rule: SeekingInPlace, from: 21 }` and the next five steps equal a twin's.
  In the bench: `Form::Seek` (`[SeekingInPlace]`), the columns, and the quick test
  `a_late_turn_on_keeps_money_and_people`: for each form beyond `A6` and both scales, the runs `fund-quiet`,
  `fund-P2`, `fund-P6` and `plain-P2`: 20 steps, then the form's rules turned on in order, then 40 steps; every
  step is `Ok` (the runner's checks of money, persons and each place hold) and every `PeriodResult.rules` before
  period 21 is empty. Add the
  quick test `the_quiet_world_with_seekers_is_still_for_34_periods` (as Task 1b's, with the seekers' columns) and
  the long tests `reproduces_pc_seek_400` and `reproduces_pc_seek_nat_400`; make their fixtures.
- [ ] **Step 5: Run** the crate's tests, then every long test in the background. Expected: `pc-a6` and `pc-seek`,
  25 of 25 at both figures.
- [ ] **Run the gate. Commit** `feat(material-circuit): people look for work in their place (A14)`.

### Task 3c: People look for work, switched on in the scene (the client)

**Files:**
- Create: `rust/crates/babylon-client/src/small_world/marks.rs`.
- Modify (under `rust/crates/babylon-client/src/small_world/`): `rules.rs` (`SHOWN_RULES` gains
  `SeekingInPlace`); `frame.rs` (the workforce set and the persons by member); `inspect.rs` ("At work" summed by
  household); `panel.rs` (`rows_for` appends `marks::rule_rows`); `../small_world.rs` (`pub mod marks;`);
  `scene_tests.rs`; `script_tests.rs`.

**Interfaces:**

```rust
// src/small_world/marks.rs
type Rows = Vec<(String, String)>;
/// The rows the rules add to the panel of a pick, for the period at `index` of `history`.
/// # Errors
/// `FrameError::Edge` for a receipt of no workplace, pool or household of the world;
/// `FrameError::Arithmetic` for a sum that overflows.
pub fn rule_rows(history: &[PeriodResult], index: usize, pick: &Pick) -> Result<Rows, FrameError>;
/// Whether the period's catalog asked for a rule of this kind.
#[must_use] pub fn holds(result: &PeriodResult, rule: SceneRule) -> bool;
/// The period's moves of people, in receipt order.
pub fn moves(result: &PeriodResult) -> impl Iterator<Item = &PlaceMoveReceipt>;
fn seeker_rows_of_workplace(result: &PeriodResult, w: Workplace, rows: &mut Rows) -> Result<(), FrameError>;
fn seeker_rows_of_household(result: &PeriodResult, h: Household, rows: &mut Rows) -> Result<(), FrameError>;
// src/small_world/frame.rs, Population gains:
/// Persons of a household at work at a workplace: the `opening_employed` of the member of that household at
/// that site.
at_work_at: BTreeMap<(Household, Workplace), usize>,
/// Which of a household's persons work where: its own workplace first, then `Workplace::ALL` order; persons
/// not at work follow.
fn person_ranges(pop: &Population, h: Household) -> Vec<(Workplace, Range<usize>)>;
```

**Decisions:**
1. **The switch.** `SHOWN_RULES` becomes `&[SeekingInPlace]`: the rail's lower part gets its two tabs and the
   list its first row, and Task 2c's tests now bite for this rule.
2. **On the plane, nothing new**, with two mends found in `frame.rs`. A mover's hours are a member
   labor receipt of its home household at the host (Task 1a, decision 7), read as a `WorkFlow` from the household
   to the host, so the bone dots already go there. Two things did not follow them, and are mended here:
   - The workforce set of `w` (Groups mode) holds `w.workers()` with the hours its own household gave `w`, then
     each other household with hours given to `w` above 0, with those hours. Today the whole of `given_to(w)` is
     booked to `w.workers()`.
   - People mode: `Population` keeps the persons of each household at each workplace (`opening_employed` of each
     member receipt, by the member's household and site, each at most the household's persons). `person_ranges`
     gives a household's persons out by member, own workplace first, then `Workplace::ALL` order, then the
     persons not at work. `stand_people` clusters each range at the wage anchor of its workplace; a workforce's
     persons are the persons of each household in its range at `w` (for the own household, every person not
     in a range at another workplace, as today), `HOURS_PER_PERSON` each in order from that household's hours.
   Without a move each household has one range, at its own workplace, and every frame is byte for byte today's.
3. **The household's "At work"** sums `opening_employed` over every member receipt of the household, at most its
   persons (`inspect.rs` `household_rows`). Today it reads the first member at the site.
4. **Rows of a workplace** (`marks.rs`), only while `holds(result, SeekingInPlace)`, numbers by
   `human_numbers::grouped`:
   - "Looked for work in {place label}": the sum of `closing_reserve` over the period's member receipts at its
     site (the engine's decision before any move, Task 3 decision 6);
   - "Found work at {host label}", one row a host, in `Workplace::ALL` order: the sum of `persons` of the moves
     whose `from_pool` is its pool;
   - "Taken on from {household label}", one row a household, in `Household::ALL` order: the sum of `persons` of
     the moves whose `host_pool` is its pool;
   - "Working here from {household label}", one row each other household with `opening_employed` above 0 at its
     site.
5. **Rows of a worker household**, only while the rule holds: "Worked at {workplace label}", one row a workplace
   with its member's `opening_employed` above 0, in `Workplace::ALL` order.
6. **Pool to workplace** is `Workplace::ALL.find(|w| w.pool_id() == pool)`; none is `FrameError::Edge`. A move is
   for the next period (Task 3, decision 8), so a host's "Taken on" of period F is its "Working here" of F + 1.
7. **The table is not changed:** it already books hours to the workplace they reached and to the household that
   gave them (`table.rs` `row`).

- [ ] **Step 1: Write the failing tests:**
  - `a_move_is_read_from_its_receipts` (in `marks.rs`): a world and strikes as the bench runs them, with
    `rules: vec![World::switches_at(Scale::Small)[1]]` (the seekers): first `fund-P2`, opened as the bench opens
    it (`Runner::open_world(&World { rules, ..World::scene() })`, then `strike(HarvestFails, Both, UntilLifted)`
    before step 1; the client cannot call the bench itself). The test
    finds, in its own run, the first period that holds a `PlaceMove` receipt and pins it; the builder checks once,
    by hand, that the bench's `pair_working_` column of that run (`BENCH/out/pc-seek-400/fund-P2.tsv`) is above 0
    from that period on (or the next one, as Task 3's writer has it) and writes the number into the test. If
    `fund-P2` has no move, the builder takes by hand the first fund run of `pc-seek-400` in run order whose
    `pair_working_` column is above 0. The test never reads the drive. In that period: a `PlaceMove` receipt
    exists; the host's rows "Taken on from {home}" and the home workplace's "Found work at {host}" equal the
    sums of its `persons`. In the next period: the
    host's "Working here from {home}" and the home household's "Worked at {host}" equal its member receipt's
    `opening_employed`; the host's workforce set (Groups) has `household:{home}` with the hours of that
    household's `WorkFlow` to the host; in People mode the host's workforce holds that many persons of the home
    household, each at most `HOURS_PER_PERSON` hours. If no fund run of the set has a move, stop and report.
  - `without_a_move_every_frame_is_as_before` (in `frame.rs`): 34 steps of `Runner::open()` with the seekers
    turned on before step 1, and of a twin without them: `build_picture` equal in both modes in every period.
  - `a_household_is_at_work_wherever_its_members_work` (in `inspect.rs`): a quiet period whose member receipts are
    edited so that 1 of farm A's 4 workers is the member of their household at clinic A: "At work" is still 4,
    and with the rule in `result.rules` the rows "Worked at Place A farm" 3 and "Worked at Place A clinic" 1.
  - In `script_tests.rs`: `the_proof_script_of_task_3c_parses` (9 commands).
  - `a_script_turns_a_rule_on` (in `scene_tests.rs`): script `{"step":1}`, `{"rule":"seeking_in_place"}`,
    `{"report":"on"}`: three "done" replies; `on.json` has `"rules": [["seeking_in_place", 2]]`.
- [ ] **Step 2: Run them and see them fail** (`-E 'test(small_world)'`): `marks` not found.
- [ ] **Step 3: Implement** the rule in the list, the frame's persons by member, "At work", the rows.
- [ ] **Step 4: Run** the client's scene tests. Expected: all pass, the frame tests as pinned, and Task 2c's
  `every_shown_rule_turns_on_from_the_next_period_and_holds` and
  `the_rail_has_the_rules_tab_only_for_rules_shown` now checking the seekers' switch, and
  `every_visual_entity_of_the_scene_declares_the_small_world` now biting for the tabs and the list.
- [ ] **Step 5: The proof script for the lead** (`PROOF_3C`, as Task 2c's Step 5):
  `{"step":20}`, `{"strike":{"shock":"harvest_fails","places":"a","lasts":"until_lifted"}}`, `{"step":10}`,
  `{"rule":"seeking_in_place"}`, `{"step":20}`, `{"capture":"seekers-on"}`, `{"particles":"people"}`,
  `{"capture":"seekers-people"}`, `{"report":"seekers-on"}`. The check: `seekers-on.json` has
  `"rules": [["seeking_in_place", 31]]`; the pictures show the rail's lower part with its two tabs, "Rules · 1
  on" chosen, the row "People look for work in their place" marked with 31 under "on from period", and the
  standing lines. This is the lead's first look at the list in the real window: its sizes are the lead's to
  tune, and the Director is shown it before the other switches follow. Whether anyone moved is read from the
  people view and the lead's pick.
- [ ] **Run the companion's gate. Commit** `feat(client): people look for work, switched on in the small world`.

### Task 3d: Mends from the lead's look at the first switch (the client)

A companion task: it changes only the client's scene and runs the companion's gate. Commit
`feat(client): a home for each unpaid group, and a script that opens tabs and picks`.

**Why.** The lead ran Task 3c's proof on the display on 24 November. The list of switches stands as the Director
picked it. Three things of the scene itself did not:

- With the harvest failed in Place A from period 21 and the seekers turned on from period 31, the farm, the
  clinic and the shop of Place A give no hours by period 50. Three groups are then paid by nobody: the workers
  of the clinic, the workers of the shop, and the owners of Place A (counted from the period's reading; the
  farm's workers are paid by the utility, where some of them work). A group paid by nobody stands at its
  place's one `HOME` point, so the three stood there together and the owner's outline, drawn round the owners'
  group, was drawn round unpaid workers too. An outline round a dot says the dot belongs to the set. (With no
  rule on, the same shock leaves every group paid at period 50, and the picture is sound.)
- The panel of a household group said "At work 4" beside "Hours given 0": the four are on the rolls of
  workplaces that give no hours.
- A script could not open the rules' tab or pick a body, so the look needed a patch that is never committed;
  and fifty periods at the scene's own beat keep a window open for two and a half minutes.

**Files:**
- Modify (under `rust/crates/babylon-client/src/small_world/`): `layout.rs` (`home_of`, `stand_at`; `HOME` goes);
  `frame.rs` (`stand_of`); `inspect.rs` (the word; `workplace_of` becomes `pub(super)`); `script.rs` (three
  commands); `script_tests.rs`; `scene_tests.rs`.

**Interfaces:**

```rust
// src/small_world/layout.rs  (the constant HOME is removed)
/// How far behind its workplace's wage anchor a workers' group paid by nobody stands (plan units, up).
pub const UNPAID_BEHIND: f64 = 1.6;
/// Where a group paid by nobody this period stands. A workers' group: behind its own workplace's people,
/// `(WORKPLACE_X[w.index()], WAGE_ANCHOR_Y + UNPAID_BEHIND)`. An owners' group: on the profit row under the
/// middle of its place's four workplaces, `(-6.8, PROFIT_ANCHOR_Y)` for Place A and `(6.8, PROFIT_ANCHOR_Y)` for
/// Place B (the mean of their `WORKPLACE_X`). A supported group: at the fund's anchor on its own side,
/// `(FUND_ANCHOR.0 + BENEFIT_LEAN[place.index()], FUND_ANCHOR.1)`.
#[must_use] pub fn home_of(h: Household) -> Point;
/// The weighted mean of the anchors that paid a household, or `home` when nobody did.
pub fn stand_at(home: Point, paid: &[(Point, f64)]) -> Result<Point, GeometryError>;

// src/small_world/script.rs: ScriptCommand gains three variants (one JSON value a line, as the others)
/// `{"lower":"shocks"}` or `{"lower":"rules"}`: what a click on that tab of the rail's lower part does.
Lower(String),
/// `{"pick":"<id>"}`: what a click on that body or particle picks. `household:N` or `person:N:k` (N is 11 to 18
/// for the workers of utility A, utility B, farm A, farm B, clinic A, clinic B, shop A, shop B; 20 and 21 the
/// owners of A and B; 22 and 23 the supported of A and B), a workplace's id (`workplace:a:farm`), `treasury`,
/// `fund`, or `none` (a click on empty space).
Pick(String),
/// `{"beat_millis":N}`: from now on every beat lasts N milliseconds (20 to 1000; the scene's own is 1000).
BeatMillis(u32),
```

**Decisions:**
1. **A home for each household.** `stand_of` in `frame.rs` calls `layout::stand_at(layout::home_of(h), anchors)`.
   No hour enters a position: a home is a constant of the household. A workers' group paid by nobody stands
   one row behind its own workplace's people, outside the workforce's outline and far from the owner's; the
   owners' group paid by nobody stands under its own place; a supported group paid by nobody stands where the
   fund would have put it. `UNPAID_BEHIND` is the lead's to tune at the look.
2. **The people view follows with no other change.** A worker household's persons who are out of work and paid
   no benefits already cluster at `stand_of(benefits, h)`: that is now `home_of(h)`, one row behind their
   workplace's people. Owners' and supported persons cluster at their group's point, as today.
3. **The word.** The panel of a household group says "Employed" where it said "At work". The figure is the
   same: its persons on a workplace's rolls at the period's opening. A workplace that gives no hours keeps its
   rolls, and the row "Hours given" beside it says what they gave.
4. **The script presses what a player presses.** `lower` writes `SceneCommand::Lower`; an unknown name is refused
   when the script is read. `pick` sets `ScenePick` to exactly what `inspect::picked` sets for a click on that
   entity: `Pick::Body` for a workplace, the treasury or the fund; `Pick::Particle(id)` for an id `household_of`
   knows; `None` for `none`. An id that none of these knows is refused when the script is read, with the id in
   the words. A person's number is not checked against the group's size (the inspector answers for the group).
   After a pick the script goes on only when the scene rests, as after every press.
5. **Fast beats are for proofs.** `beat_millis` sets every length of `FieldConfig::beats` to that many
   milliseconds; outside 20 to 1000 it is refused when the script is read. A picture is taken only while no
   beat plays, so a fast script's pictures are the same pictures. Nothing but a script can set it: the scene
   has no control for it and its own beat stays 1,000 ms.
6. **The later proofs.** From this task on the lead may add `lower`, `pick`, `wait_frames` and `beat_millis`
   lines to a companion's proof script when running it. The proof scripts of Tasks 4c to 8c stay as written.

- [ ] **Step 1: Write the failing tests.**
  - In `layout.rs`, `a_group_paid_by_nobody_stands_at_its_own_home` (it replaces
    `a_group_paid_by_nobody_stands_at_home_and_one_paid_leans_to_the_larger_share`, keeping that test's two
    assertions on a paid group with a home passed in): each to within 1e-12, `home_of` of clinic A's workers is
    `(-5.4, 4.9)`; of the owners of A `(-6.8, -2.4)` and of B `(6.8, -2.4)`; of the supported of A `(1.2, 8.3)`
    and of B `(3.2, 8.3)`; the twelve homes of `Household::ALL` are twelve points, no two nearer than
    `GROUP_SPREAD.0`; `stand_at(home_of(h), &[])` is `home_of(h)`.
  - In `scene_tests.rs`, `groups_paid_by_nobody_stand_at_their_own_homes`: with `scene_app(None)`: 20 steps;
    strike `HarvestFails` in `Places::A`, `Lasts::UntilLifted`; 10 steps; `TurnOn(SeekingInPlace)`; 20 steps
    (period 50). First the test shows that it bites: among the households that the reading of period 50 shows
    paid by nobody (no payment that `layout::anchor` places) are the owners of Place A and at least one workers'
    group of Place A; else it fails with the list. (The lead counted the list on 24 November: the workers of
    clinic A, the workers of shop A, the owners of A.) Then, in the frame of period 50 in
    `ParticleMode::Groups`: every household paid by nobody stands within `GROUP_SPREAD.0` of its `home_of`; and
    no two particles stand nearer than `GROUP_SPREAD.0`.
  - In `inspect.rs`, the test that reads the row "At work" reads "Employed" (same value); a row "At work" is
    in no panel.
  - In `script_tests.rs`, `the_script_names_tabs_picks_and_beats`: `{"lower":"rules"}`,
    `{"pick":"household:15"}`, `{"pick":"workplace:a:farm"}`, `{"pick":"treasury"}`, `{"pick":"none"}` and
    `{"beat_millis":60}` parse to their variants; `{"lower":"table"}`, `{"pick":"household:19"}`,
    `{"pick":"workplace:c:farm"}`, `{"beat_millis":5}` and `{"beat_millis":5000}` are each refused with the
    line's number.
  - In `scene_tests.rs` or `script_tests.rs`, with the app of `scene_app` and a script given as text:
    `a_scripted_pick_is_a_click_s_pick` (after `{"pick":"household:15"}` the `ScenePick` is
    `Some(Pick::Particle("household:15"))`; after `{"pick":"workplace:a:farm"}` it is
    `Some(Pick::Body(Party::Workplace(..)))` of farm A; after `{"pick":"none"}` it is `None`);
    `a_scripted_tab_is_a_click_s_tab` (after `{"lower":"rules"}` `PanelView.lower` is `Lower::Rules`; after
    `{"lower":"shocks"}`, `Lower::Shocks`); `fast_beats_change_no_frame` (two apps, the same script but for one
    `{"beat_millis":40}` at its head: after the same three steps both hold period 3 and equal frames, compared
    as the frame tests compare them).
  - `the_proof_script_of_task_3d_parses` (19 commands).
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement.**
- [ ] **Step 4: Run** the client's scene tests. Expected: all pass. A pinned frame of a period in which a group
  is paid by nobody may move: report each such test with the period and the group; a pinned frame of any other
  period that moves is a stop.
- [ ] **Step 5: The proof script for the lead** (`PROOF_3D`, as Task 2c's Step 5), one command a line:
  `{"beat_millis":60}`, `{"step":20}`,
  `{"strike":{"shock":"harvest_fails","places":"a","lasts":"until_lifted"}}`, `{"step":10}`,
  `{"rule":"seeking_in_place"}`, `{"step":20}`, `{"wait_frames":30}`, `{"capture":"slump-groups"}`,
  `{"pick":"household:15"}`, `{"wait_frames":30}`, `{"capture":"slump-clinic-workers"}`,
  `{"pick":"workplace:a:farm"}`, `{"wait_frames":30}`, `{"capture":"slump-farm"}`, `{"particles":"people"}`,
  `{"wait_frames":60}`, `{"capture":"slump-people"}`, `{"report":"slump"}`, `"quit"` (19). The check: in
  `slump-groups.png` the workers' groups of clinic A and shop A each stand above their own workplace, outside
  every outline, and the owners' group of A stands under its place; the panel of clinic A's workers says
  "Employed"; `slump.json` has `"rules": [["seeking_in_place", 31]]`.
- [ ] **Run the companion's gate. Commit** the subject above.

### Task 4: A bound on hiring (`pc-bound`)

**Files:**
- Create: `src/adjustment/bound.rs`.
- Modify: `src/transition/state.rs` (`next_plans`, `ClosedMaterialPeriod` field and `staffing_requests`);
  `src/adjustment/receipts.rs`; `src/catalog.rs`; the contract and the digest; the bench (`Form::Bound`,
  `bound_hours_<site>`, `bound_by_<site>`); `digests/pc-bound-400.txt`, `pc-bound-nat-400.txt`; the small worlds'
  `tests/runner.rs` (`LATE` gains the bound). The runner does not change.
- Modify: `src/lib.rs` (export the new receipt types for the client's companion).

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
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
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
7. **Turned on in the middle of a run** (from period F): the bound keeps nothing from one close to the next (the
   prototype's `BOUND` serves only its own close's `next_period`, `spike_bound.rs:99-122`). The close of F is the
   first to reckon it; it cuts the attendance planned for F + 1 and caps that close's staffing requests, so hours
   first change in F + 1. Period F's own attendance was planned without it at the close of F - 1.

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
  `reproduces_pc_bound_nat_400`, their fixtures. The small worlds' `LATE` gains `(24, HiringWithinMeans)`; its
  tests then also pin `[RuleOn { SeekingInPlace, 21 }, RuleOn { HiringWithinMeans, 25 }]` and no `HiringBound`
  receipt before period 25. The bench's `opening_with_a_form_is_turning_its_rules_on_first` and
  `a_late_turn_on_keeps_money_and_people` cover `Form::Bound` by `Form::ALL`.
- [ ] **Step 5: Run** the crate's tests, then every long test. Expected: three forms, 25 of 25 at both figures.
- [ ] **Run the gate. Commit** `feat(material-circuit): a workplace asks for hands it can pay and supply`.

### Task 4c: A bound on hiring, switched on in the scene (the client)

**Files:**
- Modify (under `rust/crates/babylon-client/src/small_world/`): `rules.rs` (`SHOWN_RULES` gains
  `HiringWithinMeans`); `marks.rs` (the bound's rows); `scene_tests.rs` or `marks.rs` tests;
  `script_tests.rs`.

**Interfaces:**

```rust
// src/small_world/marks.rs
/// The bound's rows of a workplace from the period's `HiringBound` receipts of its site.
fn bound_rows(result: &PeriodResult, w: Workplace, rows: &mut Rows) -> Result<(), FrameError>;
/// "nothing", "its capacity", "its inputs", "its money", "another limit".
#[must_use] pub const fn limit_words(limit: HiringLimit) -> &'static str;
/// 0 to 4 in the order of `HiringLimit`, as the bench writes `bound_by_` (Task 4, decision 4).
const fn limit_code(limit: HiringLimit) -> u8;
```

**Decisions:**
1. **The switch.** `SHOWN_RULES` becomes `&[SeekingInPlace, HiringWithinMeans]`.
2. **No mark on the plane.**
3. **Rows of a workplace**, when the period holds `HiringBound` receipts of its site: "Hours asked for the next
   period" (the sum of `asked_hours`), "Hours its money and inputs allow" (the sum of `bound_hours`), "Bound by"
   (`limit_words` of the limit of the receipt with the largest `limit_code`; `HiringLimit` derives no order).
   Hours by `human_numbers::grouped`. "Next period" because the bound of the close of P cuts the
   attendance of P + 1 (Task 4, decision 7).

- [ ] **Step 1: Write the failing tests:**
  - `the_bound_s_rows_are_its_receipt_s` (in `marks.rs`): a quiet period with one `HiringBoundReceipt` injected for
    farm A's site (`asked_hours: 40, bound_hours: 30, limit: HiringLimit::Money`): the rows read "40", "30", "its
    money"; each `HiringLimit` has its words.
  - `the_bound_reads_as_the_bench_counts_it` (in `marks.rs`): as Task 3c's run, with `Form::Bound`'s rules (`[
    HiringWithinMeans, SeekingInPlace]` from `World::switches_at(Scale::Small)`). The test finds, in its own run,
    the first period that holds a `HiringBound` receipt whose `limit` is not `HiringLimit::None` and pins it; the
    builder checks once, by hand, that the bench's `bound_by_` column of that site in `BENCH/out/pc-bound-400/` of
    that run is above 0 from that period on (or the next one, as Task 4's writer has it) and writes the number into
    the test. The test never reads the drive. At that period that site's "Bound by" is not "nothing", and in every
    period up to it each workplace's rows equal its receipts' sums. If no fund run of the set has a cut, stop and
    report.
  - `the_proof_script_of_task_4c_parses` (11 commands).
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement.** **Step 4: Run** (Task 2c's tests bite for two
  switches).
- [ ] **Step 5: The proof script for the lead** (`PROOF_4C`, as Task 2c's Step 5), one command a line:
  `{"step":20}`, `{"strike":{"shock":"harvest_fails","places":"a","lasts":"until_lifted"}}`, `{"step":10}`,
  `{"rule":"seeking_in_place"}`, `{"step":5}`, `{"rule":"hiring_within_means"}`, `{"step":20}`,
  `{"capture":"bound-on"}`, `{"particles":"people"}`, `{"capture":"bound-people"}`, `{"report":"bound-on"}`
  (11). The check: `"rules": [["seeking_in_place", 31], ["hiring_within_means", 36]]`; the row "A bound on
  hiring" marked, with 36.
- [ ] **Run the companion's gate. Commit** `feat(client): a bound on hiring, switched on in the small world`.

### Task 5: No money, no work (`pc-stop`)

**Files:**
- Create: `src/adjustment/standing.rs`.
- Modify: `src/staffing/place.rs`; `src/transition/state.rs` (the close's entry with standing; the refusal in the
  others; `PlaceStaffing.standing`); `src/adjustment/receipts.rs`; `src/catalog.rs`; the contract and the digest;
  `babylon-circuit-worlds` `src/runner/run.rs` (the standing kept between periods, the close with standing for
  each period whose rules hold `StopWithoutPay`, `Runner::standing`) and `tests/runner.rs`; the bench
  (`Form::Stop`, `stopped_<site>`); `digests/pc-stop-*.txt`.
- Modify: `src/lib.rs` (export the new receipt types for the client's companion).

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

The runner gains (babylon-circuit-worlds `src/runner/run.rs`):

```rust
impl Runner {
    /// What the rules remember of each workplace after the last step; `WorkplaceStanding::opening()` before it.
    #[must_use] pub const fn standing(&self) -> &WorkplaceStanding;
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
   the rule in `PlaceStaffing.standing`; the runner keeps that and passes it to the next close. The runner closes
   with `close_material_period_with_standing` for each period whose rules (`rules_at(period)`) hold
   `StopWithoutPay`, else with `close_material_period` as in Task 1a. The runner holds
   `WorkplaceStanding::opening()` from the opening until the first close with the rule, so a rule turned on in
   the middle of a run (from period F) starts from an empty standing, as period 1 does: every workplace `Free`.
   That is sound because the rule's test reads the receipts of the period it closes (decision 2): a workplace
   that cannot pay in F is held at the close of F, and its limit caps the staffing of F + 1.
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
  - `the_new_entry_with_an_empty_standing_is_the_opening_s`: `close_material_period_with_standing` with
    `WorkplaceStanding::opening()`, and with a standing that a crate test builds with one `Free` row for each
    site: both closes give equal transitions after the same finish.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement**; lift the refusal; contract and digest.
- [ ] **Step 4: The runner and the bench.** The runner's close with standing and `Runner::standing`; `Form::Stop`,
  the column, the quick test
  `the_quiet_world_with_the_stop_rule_is_still_for_34_periods`, `reproduces_pc_stop_400`,
  `reproduces_pc_stop_nat_400`, their fixtures. The small worlds' `LATE` gains `(28, StopWithoutPay)`, and
  `tests/runner.rs` gains `the_stop_rule_turned_on_late_starts_from_an_empty_standing`: after 28 steps of `LATE`,
  `standing()` equals `&WorkplaceStanding::opening()`; no `Stop` receipt before period 29; a `Stop` receipt for
  each of the 8 sites at period 29 (each site is tested at each close, decision 2).
- [ ] **Step 5: Run.** Expected: four forms, 25 of 25 at both figures.
- [ ] **Run the gate. Commit** `feat(material-circuit): no money, no work (A17)`.

### Task 5c: No money, no work, switched on in the scene (the client)

**Files:**
- Modify (under `rust/crates/babylon-client/src/small_world/`): `rules.rs` (`SHOWN_RULES` gains
  `StopWithoutPay`); `frame.rs` (`BodyPicture.held`); `scene.rs` (`BodyCore`, the dim material, `paint_cores`);
  `marks.rs` (the stop's rows, `held_since`); `scene_tests.rs`; `script_tests.rs`.

**Interfaces:**

```rust
// src/small_world/frame.rs, BodyPicture gains:
/// Held back by no money, no work at this close: its site's `StopReceipt` of the period says `Held`.
/// Only on workplaces.
pub held: bool,
// src/small_world/scene.rs
/// A body's centre disc: a component put on the existing core disc, not a new entity.
#[derive(Component)] struct BodyCore;
// SceneMaterials gains `dim: Handle<StandardMaterial>` (`unlit(DIM)`).
/// The centre disc of a held workplace in `DIM`, every other in gold; all gold while nothing is shown.
fn paint_cores(
    shown: Res<SceneShown>,
    materials: Option<Res<SceneMaterials>>,
    plates: Query<&SceneBody>,
    mut cores: Query<(&ChildOf, &mut MeshMaterial3d<StandardMaterial>), With<BodyCore>>,
);
// src/small_world/marks.rs
/// The first period of the unbroken run of closes, ending at `index`, whose receipts hold the site `Held`.
#[must_use] pub fn held_since(history: &[PeriodResult], index: usize, w: Workplace) -> Option<u64>;
fn stop_rows(history: &[PeriodResult], index: usize, w: Workplace, rows: &mut Rows) -> Result<(), FrameError>;
```

**Decisions:**
1. **The switch.** `SHOWN_RULES` becomes `&[SeekingInPlace, HiringWithinMeans, StopWithoutPay]`. It waits for the
   seekers (Task 2): until they are on its name is in `GRAY`, with "(needs: people look for work in their place)"
   under it, and its press tells the runner's words.
2. **On the plane:** a workplace whose `StopReceipt` of the period says `StopHold::Held` has its centre disc in
   `DIM`, the field palette's no-reading colour; its rings, which are its hours and money of the period, and its
   label do not change. `paint_cores` runs in the `Paint` chain after `redraw_rings`, only when `SceneShown`
   changed. Held, not the bench's `stopped_` (no hours and nobody employed): the rule's own word for a workplace
   it holds back.
3. **Rows of a workplace**, when the period holds its site's `StopReceipt`: if `Held`, "No money, no work" |
   "held since period {held_since}" and, when `limit` is `Some(n)`, "Most it may employ" | n; if it could not pay
   (`could_not_pay`, or `Payment::Short` if Task 5 made it an enum), "Hours it could not pay" | the sum of
   `unattended_hours` of the period's member labor receipts at its site. A `Free` site that paid gets no row.
4. `held_since` walks back from `index` while each period holds a `Held` receipt for the site; it reads only the
   history's receipts.

- [ ] **Step 1: Write the failing tests:**
  - `a_held_workplace_is_drawn_dim` (in `scene_tests.rs`): one step; build the picture of that period with a
    `StopReceipt { site_id: clinic A, could_not_pay: true, hold: Held, limit: Some(0), .. }` pushed into its
    `receipts.adjustments`; put it in `SceneShown`; two updates: clinic A's `BodyCore` has the dim handle, the
    other nine the gold one; its two rings and its label as before; `SceneShown(None)`: all gold.
  - `held_since_counts_the_unbroken_run` (in `marks.rs`): a history of 7 copies of a quiet period, periods 1 to
    7, with clinic A `Free` at 4 and `Held` at 5, 6, 7: `held_since(.., 6, clinic A) == Some(5)`; at index 3,
    `None`.
  - `the_stop_s_rows_are_its_receipt_s` (in `marks.rs`): on that history, at index 6: "No money, no work" |
    "held since period 5", "Most it may employ" | "0", and "Hours it could not pay" equal to the sum of the
    period's `unattended_hours` at the site.
  - `every_close_with_the_rule_tests_every_site` (in `marks.rs`): `Runner::open()`, seekers and the stop rule
    turned on before step 1, 34 steps: 8 `Stop` receipts a period; every workplace's rows equal its receipt's (the
    stop rule never acts on the bench, so these are `Free` and print nothing: say so in the report).
  - `the_stop_rule_waits_for_the_seekers_on_screen` (in `scene_tests.rs`): at the opening the row "No money, no
    work" has its name in `GRAY` and the line "(needs: people look for work in their place)" under it; a click on
    it: the notice "No money, no work waits for people look for work in their place"; then the seekers' row
    clicked: its name is `PAPER` and that line is gone.
  - `the_proof_script_of_task_5c_parses` (13 commands).
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement.** **Step 4: Run.**
- [ ] **Step 5: The proof script for the lead** (`PROOF_5C`, as Task 2c's Step 5), one command a line:
  `{"step":20}`, `{"strike":{"shock":"harvest_fails","places":"a","lasts":"until_lifted"}}`, `{"step":10}`,
  `{"rule":"seeking_in_place"}`, `{"step":5}`, `{"rule":"hiring_within_means"}`, `{"step":5}`,
  `{"rule":"stop_without_pay"}`, `{"step":20}`, `{"capture":"stop-on"}`, `{"particles":"people"}`,
  `{"capture":"stop-people"}`, `{"report":"stop-on"}` (13). The check: three rules, the stop from 41; a capture of the
  list with three marked rows. A second script, `waits.jsonl`: `{"step":1}`, `{"rule":"stop_without_pay"}`:
  `refusal.json` with the waiting words.
- [ ] **Run the companion's gate. Commit** `feat(client): no money, no work, switched on in the small world`.

### Task 6: A resting price (`pc-rest`)

**Files:**
- Modify: `src/recurring/prices.rs`; `src/services/market.rs`; `src/clearing/table.rs` (`offered`);
  `src/adjustment/receipts.rs`; `src/catalog.rs`; the contract and the digest; the bench (`Form::Rest`);
  `digests/pc-rest-*.txt`.
- Modify: `src/lib.rs` (export the new receipt types for the client's companion).

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
4. **Turned on in the middle of a run** (from period F): the rule keeps nothing between closes (the prototype's
   `IDLE` is set before each close and `RESTED` taken after it, `spike_rest.rs:40-69`); it reads the labor rows of
   the period it closes, which exist in every period. The close of F is the first whose prices for F + 1 rest.

- [ ] **Step 1: Write the failing unit tests:** `a_workplace_with_hands_does_not_rest` (8 hours, offered 0:
  false); `a_workplace_with_goods_on_offer_does_not_rest` (0 hours, offered 3: false); `an_idle_workplace_rests`
  (0 hours, offered 0, catalog asks: true; not asking: false).
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement**; lift the refusal; contract and digest.
- [ ] **Step 4: The bench.** `Form::Rest`, the quick test, `reproduces_pc_rest_400`, `reproduces_pc_rest_nat_400`.
  The small worlds' `LATE` gains `(32, RestingPrice)`; no `RestingPrice` receipt before period 33.
- [ ] **Step 5: Run.** Expected: five forms, 25 of 25 at both figures.
- [ ] **Run the gate. Commit** `feat(material-circuit): a stopped workplace's price rests`.

### Task 6c: A resting price, switched on in the scene (the client)

**Files:**
- Modify (under `rust/crates/babylon-client/src/small_world/`): `rules.rs` (`SHOWN_RULES` gains `RestingPrice`);
  `marks.rs` (the rest's row); `inspect.rs` (`good_name` made `pub(super)`); `script_tests.rs`.

**Interfaces:**

```rust
// src/small_world/marks.rs
fn resting_rows(result: &PeriodResult, w: Workplace, rows: &mut Rows) -> Result<(), FrameError>;
```

**Decisions:**
1. **The switch.** `SHOWN_RULES` becomes `&[SeekingInPlace, HiringWithinMeans, StopWithoutPay, RestingPrice]`.
2. **No mark on the plane.** A row a `RestingPriceReceipt` of its site: "Price rests · {good}" |
   `human_numbers::currency(price)`, the good's name as `inspect.rs` `good_name` gives it (made `pub(super)`).

- [ ] **Step 1: Write the failing tests:** `the_resting_price_s_row_is_its_receipt_s` (in `marks.rs`: a quiet
  period with a `RestingPriceReceipt` for farm A's food at $25 injected: "Price rests · food" | "$25.00"; no row
  for any other workplace); `the_proof_script_of_task_6c_parses` (15 commands).
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement.** **Step 4: Run.**
- [ ] **Step 5: The proof script for the lead** (`PROOF_6C`, as Task 2c's Step 5), one command a line:
  `{"step":20}`, `{"strike":{"shock":"harvest_fails","places":"a","lasts":"until_lifted"}}`, `{"step":10}`,
  `{"rule":"seeking_in_place"}`, `{"step":5}`, `{"rule":"hiring_within_means"}`, `{"step":5}`,
  `{"rule":"stop_without_pay"}`, `{"step":5}`, `{"rule":"resting_price"}`, `{"step":20}`,
  `{"capture":"rest-on"}`, `{"particles":"people"}`, `{"capture":"rest-people"}`, `{"report":"rest-on"}` (15).
  The check: four rules, the rest from 46.
- [ ] **Run the companion's gate. Commit** `feat(client): a resting price, switched on in the small world`.

### Task 7: The owner restarts a stopped workplace, mended (`pc-restart`)

**Files:**
- Create: `src/adjustment/restart.rs`.
- Modify: `src/adjustment/standing.rs` (two counters); `src/transition/state.rs` (the step at the end of the
  close); `src/adjustment/bound.rs` (the rebound); `src/valuation/` (one booking function on the cost book);
  `src/adjustment/receipts.rs`; `src/catalog.rs`; the contract and the digest; the bench (`Form::Restart`; columns
  `restart_test_<site>`, `stopped_since_<site>`, `restart_inputs_<site>`, `owner_spare_<copy>`, read from
  `PeriodReceipts.adjustments` and `Runner::standing`; the runner does not change);
  `digests/pc-restart-*.txt`; the small worlds' `tests/runner.rs`.
- Modify: `src/lib.rs` (export the new receipt types for the client's companion).

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
3. **Counters.** They advance only in a close whose catalog asks for the restart, as the prototype's do (made at
   0 before period 1, `support.rs:3957`, and advanced only in `restart_close`, `3705-3711`); a site with no row
   gets one (`Free`, 0, 0). `periods_since_work` and `quiet_periods` go to 0 if the site made or sold anything
   this period, else up by one, after (b) has run. The prototype's words, kept exactly (`sales_and_output`,
   `support.rs:3622`, and its caller in `run_staffed`, about 3966): `sales` = the quantity of its local
   transfers as supplier, plus its local fulfillments as retailer, plus its service markets'
   `performed_quantity`; `output` = a production receipt's `produced_batches x quantity_per_batch` (the last such
   receipt of the site, as the prototype assigns it), plus the quantity of local transfers it received as buyer.
   It made or sold anything when `sales > 0`, or when it has a recurring production row and `output > 0`.
4. **The test**, for each site whose labor rows of the closing period offer 0 hours and with
   `quiet_periods >= 3` (`pub const RESTART_QUIET_PERIODS: u64 = 3`, exported from `src/lib.rs`: the scene's words
   are built from it, Task 7c): `turned` = the sum, over every
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
10. **Turned on in the middle of a run** (from period F): the counters are 0 at the close of F, whatever the site
    did before (decision 3). A site idle before F counts 1, 2, 3 at the closes of F, F + 1 and F + 2, is first
    tested at the close of F + 2 (`RESTART_QUIET_PERIODS`), and if restarted works from F + 3. Counted from
    period 1 the arithmetic is the same. The hold the stop rule kept since its own first period is the standing's
    and is read as it stands. The restart needs the bound and the resting price on, so this close has a
    `HiringBound` and its `RestingPriceReceipt`s. This is the lead's call of 23 November, reported to the
    Director: the rule counts quiet periods from the period it is turned on, and the scene's words must say that
    a workplace is tested after three quiet periods under the rule: while the rule holds, a workplace's panel
    reads "Tested after | 3 quiet periods under the rule" (Task 7c).

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
  - `a_workplace_is_tested_at_its_third_quiet_close` (a standing row of 0 and 0 for a site with 0 hours that made
    and sold nothing: `NotTested` at the first and second close, tested at the third).
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement**; lift the refusal; contract and digest.
- [ ] **Step 4: The bench.** `Form::Restart` (`[HiringWithinMeans, SeekingInPlace, StopWithoutPay, RestingPrice,
  OwnerRestart { outlay_periods }]`, 1 period small, 2 national), its columns, the quick test,
  `reproduces_pc_restart_400`, `reproduces_pc_restart_nat_400`. The small worlds' `LATE` gains
  `(36, OwnerRestart { outlay_periods: 1 })`; no `Restart` receipt before period 37. And
  `the_restart_waits_for_its_rules`: with seekers and the stop rule on only, `switch(OwnerRestart {
  outlay_periods: 1 })` is `Waits { needs: [HiringWithinMeans, RestingPrice] }` and `turn_on` is `RuleError::Waits`
  with that list.
- [ ] **Step 5: Run.** Expected: six forms, 25 of 25 at both figures.
- [ ] **Run the gate. Commit** `feat(material-circuit): an owner restarts a stopped workplace with its own money`.

### Task 7c: An owner restarts a stopped workplace, switched on in the scene (the client)

**Files:**
- Modify (under `rust/crates/babylon-client/src/small_world/`): `rules.rs` (`SHOWN_RULES` gains
  `OwnerRestart`); `reading.rs` (`PaymentKind::Capital`); `frame.rs` (`STREAM_MONEY`, the styles,
  `payment_stream`, the pinned count of streams); `panel.rs` (`not_drawn_line`); `marks.rs` (the restart's rows,
  the owner's spare); `scene_tests.rs` (the not-drawn line with capital); `script_tests.rs`.

**Interfaces:**

```rust
// src/small_world/reading.rs, PaymentKind gains (last, so `ALL` keeps its order):
/// An owner's money put into a workplace it owns (`CashTransferPurpose::CapitalContribution`).
Capital,
pub const ALL: [PaymentKind; 6];   // label "capital"
// src/small_world/frame.rs
/// The streams of wages, purchases, taxes, benefits, profit and capital.
pub const STREAM_MONEY: [u16; 6] = [4, 5, 6, 7, 8, 9];
// src/small_world/marks.rs
fn restart_rows(result: &PeriodResult, w: Workplace, rows: &mut Rows) -> Result<(), FrameError>;
fn owner_rows(result: &PeriodResult, h: Household, rows: &mut Rows) -> Result<(), FrameError>;
/// "not tested", "tested, failed", "tested, no owner's money", "restarted".
#[must_use] pub const fn test_words(test: RestartTest) -> &'static str;
```

**Decisions:**
1. **The switch.** `SHOWN_RULES` becomes the five rules without `GoodsStepDown`. It waits for the bound, the stop
   rule and the resting price; its rule is the scene world's (`outlay_periods: 1`).
2. **The money:** `read_payments` reads `CashTransferPurpose::CapitalContribution` as `PaymentKind::Capital`,
   its payer the debit's cash account, as a tax is read. `HouseholdTransfer`, `TransportService` and `MutualAid`
   stay refused. Without this the first restart stops the scene: `read_payments` refuses that purpose today.
3. **On the plane:** a sixth gold stream, `STREAM_MONEY[5]`, built as the other five (beat 2, `MONEY_PER_MARK`,
   streaks, swatch 2), from the owner's household group to the workplace: `money_flows` draws it with no change.
   `layout::anchor` gives capital no anchor, so the owner's group does not move for it.
4. **The panel:** "Money in · capital" on the workplace and "Money out · capital" on the owner come from the
   existing loop over `PaymentKind::ALL`. A `RestartReceipt` of the site adds "Owner's restart" | `test_words`;
   when tested, "Turned away" | `turned` units and "One batch costs" | `batch_cost`; when restarted, "Owner put
   in" | `money`; when `inputs_short`, "Inputs short" | "yes". A `RestingPriceToCostReceipt` adds "Resting price
   raised to cost" | "{old} to {raised}". An owner household with an `OwnerSpareReceipt` adds "Spare for a
   restart" | `spare`. Money by `human_numbers::currency`.
5. **The sentence of ADR321's reading** (Task 7, decision 10): while `holds(result, OwnerRestart)`, every
   workplace's panel has "Tested after" | "{RESTART_QUIET_PERIODS} quiet periods under the rule", the figure from
   the engine's constant, which Task 7 makes public.
6. **"Not drawn"** names capital only when the period's report has a capital stream with a total above 0: ",
   capital {c}" at its end. So `not_drawn_line_prints_the_report` keeps its words.
7. **The table is not edited.** It sums every payment, so the owner's money is in its money in and out, where
   without decision 2 it could not be built at all.
8. **A pinned count moves** (named in the Global Constraints): `the_styles_name_the_plans_units` expects 10
   streams, not 9.

- [ ] **Step 1: Write the failing tests:**
  - `a_capital_contribution_is_read_as_capital` (in `reading.rs`): the first period with its first profit transfer
    edited (purpose `Cash(CapitalContribution)`, debit and credit locations swapped, so the owner pays the site):
    one `Capital` payment, owner to site, of that amount; the profit total less that amount; the other four
    totals unchanged.
  - `the_owner_s_money_is_a_sixth_gold_stream` (in `frame.rs`): that period's picture has one flow of stream 9
    from the owner's group point to the site's body; `each_stream_draws_and_counts_exactly_its_own_total`'s check
    (drawn plus not drawn is the total) holds for it.
  - `the_panel_lists_the_owner_s_money` (in `marks.rs`): the workplace's rows hold "Money in · capital" and the
    owner's "Money out · capital", each the amount; the table's money in of the workplace counts it.
  - `the_restart_s_rows_are_its_receipt_s` (in `marks.rs`): injected `RestartReceipt { test: Restarted, money:
    $40, batch_cost: $23, turned: 3, inputs_short: false, .. }`: "restarted", "3", "$23.00", "$40.00"; with
    `OwnerRestart` in `result.rules`, "Tested after" | "3 quiet periods under the rule"; without it, no such row;
    each `RestartTest` has its words; an `OwnerSpareReceipt` of $50 gives the owner "Spare for a restart" |
    "$50.00".
  - `the_not_drawn_line_names_capital_only_when_there_is_some` (in `scene_tests.rs`, beside
    `not_drawn_line_prints_the_report`): the quiet period's report gives the line as pinned; the same report
    with a capital stream's entry added by hand, its total above 0, gives a line that ends with ", capital {c}".
  - `the_proof_script_of_task_7c_parses` (17 commands).
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement.** **Step 4: Run** (with the one moved count).
- [ ] **Step 5: The proof script for the lead** (`PROOF_7C`, as Task 2c's Step 5), one command a line:
  `{"step":20}`, `{"strike":{"shock":"harvest_fails","places":"a","lasts":"until_lifted"}}`, `{"step":10}`,
  `{"rule":"seeking_in_place"}`, `{"step":5}`, `{"rule":"hiring_within_means"}`, `{"step":5}`,
  `{"rule":"stop_without_pay"}`, `{"step":5}`, `{"rule":"resting_price"}`, `{"step":5}`,
  `{"rule":"owner_restart"}`, `{"step":20}`, `{"capture":"restart-on"}`, `{"particles":"people"}`,
  `{"capture":"restart-people"}`, `{"report":"restart-on"}` (17). The check: five rules, the restart from 51;
  whether a restart happens in the run is read from the panel (Task 0 counted 39 restarts over the 25 runs of
  `pc-restart-400`; this run may hold none).
- [ ] **Run the companion's gate. Commit** `feat(client): an owner restarts a stopped workplace, switched on in the
  small world`.

### Task 8: A goods price steps down, as measured (`pc-down`)

**Files:**
- Modify: `src/recurring/prices.rs` (`update_prices`, `quote`); `src/clearing/table.rs` and
  `src/clearing/ladder.rs` (offered, sold, gain at a price); `src/transition/state.rs` (`next_plans` order);
  `src/recurring/firms.rs` (the gain in the plans); `src/adjustment/receipts.rs`; `src/catalog.rs`; the contract
  (`P9_posted_price` too) and the digest; the bench (`Form::Down`, `unsold_<site>`, `turned_payers_<site>` for
  farms and shops); `digests/pc-down-*.txt`.
- Modify: `src/lib.rs` (export the new receipt types for the client's companion).
- Modify (the client): `rust/crates/babylon-client/src/small_world/scene_tests.rs` (remove
  `a_rule_not_yet_built_is_refused_in_the_scene`).

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
    pub offered: u64, pub sold: u64, pub kept: u64, pub planned_gain: u64,
}
```

**Decisions** (the prototype is `spike/closest-ref` `src/recurring/prices.rs:262-477` with
`SPIKE_DOWN_GOODS=on` and the floor's switch unset, `clearing/table.rs:175-277`, `clearing/ladder.rs:190-218`,
`state.rs:1189-1259`, `firms.rs:764-767, 926-928`):
1. **The test.** `waiting` as today (paid household purchases not filled, restock orders not shipped, final-demand
   orders not filled, and what bids could pay for at the posted price in a short market and did not get).
   `kept` = the seller's production policy's `output_buffer` (0 for a seller with none). `unsold` = sold plus kept
   below what its goods markets offered. Order: `Fixed`; a resting seller holds; step up as today; else step down
   one step if `waiting == 0` and (`stock > target_stock` or `unsold`); else hold.
2. **No floor at cost** (the Director's ruling of 23 November, ADR321, K1). A step down stops at the price
   policy's `minimum`, as every step down of the engine does today: the seller may sell under its cost and bears
   the loss from its own money. The reference branch's switch `SPIKE_DOWN_FLOOR` is not this rule and nothing of
   it is built. A step down for unsold goods records reason `ExcessStock`, the step-down reason that exists: no
   new `PriceDecision`, because `babylon-tick` and `babylon-persistence` match on it exhaustively
   (`recurring_receipt.rs:159-167`, `projection.rs:110-143`). The `GoodsOfferReceipt` says why.
3. **Plans at the new price.** While the catalog asks, goods are quoted before `plan_production`, and a seller that
   stepped down adds `goods_gain_at(new price)` to its unshipped quantity (makers) or its merchandise (merchants'
   handling hours). Services are untouched: no quote before plans, no gain (departure 4).
4. **Bench columns:** `unsold_<site>` = `offered - sold` (without `kept`), `turned_payers_<site>` = the price
   receipt's `unserved_quantity`, farms and shops only, after the bound's columns, as `spike.rs` `write_run`.
5. **Turned on in the middle of a run** (from period F): the rule keeps nothing between closes; the close of F is
   the first to quote goods before plans and post a stepped-down price for F + 1.

- [ ] **Step 1: Write the failing unit tests** in `src/recurring/prices.rs`: `a_step_down_goes_under_cost` (old
  $38, step $1, unit cost $38, goods unsold, nobody waiting: $37); `a_step_down_stops_at_the_minimum` (old $1.50,
  step $1, minimum $1: $1; old $1: holds at $1);
  `a_buffer_is_not_unsold` (offered 40, sold 0, kept 40: not unsold); `a_buyer_who_could_pay_and_waited_bars_the_step`
  (waiting 1, unsold: no step down); `not_asking_keeps_todays_price_rule` (the same offers, catalog not asking:
  today's decisions).
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement**; lift the refusal; contract and digest.
- [ ] **Step 4: The bench.** `Form::Down` (the six rules), its columns, the quick test,
  `reproduces_pc_down_400`, `reproduces_pc_down_nat_400`. The small worlds' `LATE` gains `(40, GoodsStepDown)`;
  no `GoodsOffer` receipt before period 41. Remove `a_rule_not_yet_built_is_refused_by_turn_on` with
  `NOT_YET_BUILT` (Task 2, decision 3), and the scene's twin `a_rule_not_yet_built_is_refused_in_the_scene`
  (the client's `scene_tests.rs`), which fails once the engine admits the last rule. Then run the client's
  scene tests too: `mise run rust:test:q -- -p babylon-client -E 'test(small_world)'`.
- [ ] **Step 5: Run.** Expected: seven forms, 25 of 25 at both figures. The `pc-down` rows passed the Director's
  test where there is a fund in Task 0, so the built form passes it: every column the counters read is compared.
- [ ] **Run the gate. Commit** `feat(material-circuit): a goods price steps down when goods go unsold (A1)`.

### Task 8c: A goods price steps down, switched on in the scene (the client)

**Files:**
- Modify (under `rust/crates/babylon-client/src/small_world/`): `rules.rs` (`SHOWN_RULES` is the six); `marks.rs`
  (the offer's rows); `script_tests.rs`.

**Interfaces:**

```rust
// src/small_world/marks.rs
fn offer_rows(result: &PeriodResult, w: Workplace, rows: &mut Rows) -> Result<(), FrameError>;
```

**Decisions:**
1. **The switch.** `SHOWN_RULES` is `SceneRule::LISTED`, the six.
2. **No mark on the plane.** For each `GoodsOfferReceipt` of the site: "Offered · {good}" | `offered`, "Sold ·
   {good}" | `sold`, "Kept as a buffer · {good}" | `kept` (units by `grouped`); and when the period's
   `PriceReceipt` of that site and good has `reason: PriceDecision::ExcessStock` and `next_price < old_price`:
   "Price stepped down · {good}" | "{old} to {next}". `planned_gain` is not printed.
3. **The rule not yet built is gone:** Task 8 removed `NOT_YET_BUILT` and, with it, the scene's test
   `a_rule_not_yet_built_is_refused_in_the_scene`. No other assertion changes.

- [ ] **Step 1: Write the failing tests:** `the_offer_s_rows_are_its_receipt_s` (in `marks.rs`: a quiet period with
  a `GoodsOfferReceipt` for farm A's food, offered 40, sold 30, kept 4, injected, and its `PriceReceipt` set to
  `ExcessStock`, $25 to $24: the four rows "40", "30", "4", "$25.00 to $24.00"; with `UnservedDemand`, no "stepped
  down" row); `every_offer_reads_as_its_receipt` (as Task 3c's run with the six rules from
  `World::switches_at(Scale::Small)`, 40 periods: at least one `GoodsOffer` receipt, else stop and report; every
  workplace's rows equal its receipts); `the_proof_script_of_task_8c_parses` (12 commands).
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement.** **Step 4: Run.** Expected: every client test
  passes; Task 2c's tests check all six switches.
- [ ] **Step 5: The proof script for the lead** (`PROOF_8C`): `{"step":1}`,
  `{"strike":{"shock":"harvest_fails","places":"both","lasts":"until_lifted"}}`, `{"step":20}`,
  `{"rule":"seeking_in_place"}`, `{"rule":"hiring_within_means"}`, `{"rule":"stop_without_pay"}`,
  `{"rule":"resting_price"}`, `{"rule":"owner_restart"}`, `{"rule":"goods_step_down"}`, `{"step":40}`,
  `{"capture":"all-six"}`, `{"report":"all-six"}`. The check: six rules, each from 22; the list shows six marked
  rows, the standing lines and no needs line, all inside the rail; the lead looks at the hours of `all-six.json`
  beside those of the same run without rules.
- [ ] **Run the companion's gate. Commit** `feat(client): a goods price steps down, switched on in the small world`.

## Self-review notes

- **Every rule has a task.** (a) the bound, Task 4; (b) seekers, Task 3; (c) the stop rule, Task 5; (d) the
  resting price, Task 6; (e) the restart with its three mends, Task 7; (g) the step down, Task 8. Rule A6
  is built; Task 1b proves the bench against it.
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
  `refuse_combinations` and `NOT_YET_BUILT` (Task 2, the const lifted kind by kind in Tasks 3 to 8). In the
  client: `SceneRule`, `SHOWN_RULES`, `RuleButton` and `SceneCommand::TurnOn` (Task 2c, the list grown kind by
  kind in Tasks 3c to 8c), `marks::rule_rows` (Task 3c, one group of rows added in each of 4c to 8c),
  `BodyPicture.held` (5c), `PaymentKind::Capital` (7c).

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
- Task 1b: the small world's one literal is the exception to "not touched"; `print_reference_digests` reads the
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

## What the built crate changed (23 November 2026)

The crate of small worlds was built for the client's scene after this plan was written and checked. A second reader
compared the two. What it found, and what the lead decided:

- **The crate held one world of the bench's four.** It had the fund world at the small figures. The bench also runs
  the plain world and the national figures. Task 1a adds them.
- **Six pushes are openings, not four.** P1, P3, P4, P5, P6 and P7 change the opening state. Only the harvest (P2,
  P8 and their one-place forms) is a catalog figure that can be struck. P6 changes the catalog and also the
  opening: the utility plans 12 batches of 10 hours. The scene's own power cut, struck in the middle of a run,
  swaps the catalog only, so it is not the bench's P6, and the reference rows do not cover it.
- **One loop.** The bench had its own period loop in this plan. It now steps the crate's `Runner`, the loop the
  scene runs. Tasks 1a, 2, 3 and 5 change that runner (Tasks 3 and 5 where they changed the bench's loop).
- **Timing was checked by reading:** a ten-period strike before the first step holds in periods 1 to 10, as the
  prototype's catalogs do. The engine calls of the runner and of the prototype's loop are the same, in the same
  order.
- **The lead's answers to the reader's questions.** The pair rows of the seekers are authored when the world asks
  for seekers, as the prototype did; whether they are authored always, so that a switch can turn seekers on in the
  middle of a run, is settled with the companion tasks, before Task 3 is built. The horizon stays at 1,000 periods
  unless Task 1b's long tests show a difference from it. The scoped gate gains the crate's tests, and the client's
  tests of the scene where the crate changes. The opening pushes need no feature of their own: the scene offers
  none of them. `Runner::state()` is public and read-only. The runner keeps computing the state's digest.
- **In the way of a switch in the middle of a run:** the pair rows exist only if authored at the opening; without
  seekers the runner rebuilds each member from the opening's people, so the members would have to be kept on both
  paths; the runner's cache of catalogs is keyed by the production figures alone; and a rule that needs another
  cannot be turned off alone.
  Settled (Tasks 1a, 2, 3, 5): the pair rows in every world; the members kept on both paths; the cache keyed by
  figures and rules; no turn-off, so no chain to undo.
- **Task 0 is not built in a worktree of its own,** as first written: see its "Where".

## The Director's rulings of 23 November, afternoon (ADR321)

Task 0's first runs, on the prototype's own engine, were counted before anything was built. The record is
`pc-sets.md` on the bench's drive. Two findings went to the Director, and four answers came back in the dialog.

**What was found.** The lead's words "to its cost and no lower" were not the measured rule: with that floor the
whole form fails line 3 of the test at both sets of figures, and as measured it passes. And rounds nine and ten
queued buyers in an order the engine does not have (departure 2): in the engine's own order the form as measured
passes at the country's figures and fails line 3 in one run of 25 at the small figures. Every failure is a clinic
shut for good in the world with no fund. In the world with a fund no workplace is shut at the end in any of 104
runs.

**Why a clinic stays shut** (counted over all 23 long clinic stops of the no-fund world): care is the last thing a
household buys; in a squeeze there comes a period when no household buys it; the clinic had planned as many hours
as its money could pay, pays for them and uses none; its money falls to a few dollars in that one period; then no
money, no work, and its owner restarts it only from spare money.

**The answers** (labels word for word):

1. "As measured (Recommended)": no floor at cost. Task 8, departure 3, the reference set `pc-down` and the name
   `GoodsStepDown` follow. The floored rows are kept as `pc-downfloor`.
2. "Play, as you ruled (Recommended)": the test is scored in the world with a fund; the world with no fund is
   counted and reported. Task 0's gate follows.
3. "On anytime, off by restart (Recommended)": a rule turned on works from the next period and holds until the
   run is started over. A rule that needs another waits for it: the stop rule needs the seekers; the restart
   needs the stop rule, the resting price and the bound (Task 2's refusals).
4. "Yes, go on (Recommended)": the look of the scene's real window stands.

**Each step of the form in the engine's own order** (prototype's engine, small figures; a lasting failure is a
place left without a product for good):

| Built so far | Runs with a lasting failure, of 25 | In the fund world, of 13 | Mean hours, of 480 |
| --- | --- | --- | --- |
| no new rule (`c2-pc-a6`) | 6 | 4 | 340 |
| looking for work, alone (`c2-pc-seek`) | 8 | 4 | 216 |
| with the bound (`c2-pc-bound`) | 6 | 4 | 340 |
| with the stop rule, the resting price and the restart (`c2-pc-restart`) | 1 | 1 | 405 |
| with the step down as measured (`c2-pc-down`) | 1 | 0 | 440 |

**What a switch in the middle of a run asks of the build** (settled in Tasks 1a, 1b, 2 and 3 to 8):

- `Runner::turn_on` (Task 2) turns a rule on from `next_period()`, the `from` a strike gets, and refuses, changing
  nothing: a stopped run; a rule already on; a rule whose needed rules are not on; a catalog the engine's
  admission refuses. There is no turn-off; starting over is a new runner. `Runner::open_world` turns the world's
  rules on with it before the first step. The cache of catalogs is keyed by the figures and the rules.
- The seekers' rows are authored in every world (Task 1a). The state has no catalog digest and the scene's design
  forbids a state edit from outside, so they cannot be added at turn-on. The loop without seekers keeps every
  member and writes a member row for each, as the engine's payroll and layoff checks require. `pc-a6` (Task 1b)
  proves they change no compared column; three pinned counts and one loop of the crate's tests move (Task 1a,
  decision 7).
- The bound, the resting price and the step down keep nothing between closes. `WorkplaceStanding` starts as
  `WorkplaceStanding::opening()` at the stop rule's first close; the restart's counters start at 0 at its first
  close and advance only while it is on.
- The runner gives the scene, for each rule, `Switch::On { from }`, `Ready` or `Waits { needs }` (Task 2); the
  scene's switches read it (Task 2c), and each rule's companion puts its switch on screen (Tasks 3c to 8c).

## What Tasks 1a and 1b built (23 November 2026, evening)

Both are built, reviewed and approved (`69cff3d0b`, `096d5a528`). The bench reproduces `pc-a6-400` and
`pc-a6-nat-400`, 25 runs of 25 each, at its first run; the lead ran the two long tests again. So the crate's
worlds are the prototype's, and the seekers' rows that every world now authors change no compared column. A
later task builds on the code as it stands, which differs from the text above in these points:

- **The bench's tests stand in `tests/adjustment_bench/sets.rs`,** which the root `tests/adjustment_bench.rs`
  pulls in with `include!("adjustment_bench/sets.rs")`. The sentinels allow a file with a folder beside it only
  `mod` and `pub use`, and a test inside a child module would not match the long tests' filter
  (`test(/^reproduces_/)`). Where a task says a test goes into `tests/adjustment_bench.rs`, it goes into
  `sets.rs`.
- **`print_reference_digests`** reads no environment variable. It prints every set, each under a line
  `== <set>`: `--run-ignored only -E 'test(print_reference_digests)' --no-capture`. A rule task adds its two sets
  to it and copies its lines into the new fixtures.
- **The runner and the world** gained what their tests needed beyond the Interfaces: `RunnerError::Shock`
  (`open_world` strikes a pushed power cut through the book), `World::is_pushed(push, place)`, and
  `Workplace::pairs()`, the ordered (home, host) pairs of one place, the home first, which is the order of the
  authored pair rows.
- **The client's `inspect.rs` was not changed:** a household's "At work" still reads the first member at its
  workplace's site. It is right while nobody moves, since a pool's own member sorts first. Task 3c mends it
  (its decision 3).
- **Reviewers' notes kept for one later task** (none blocks a rule): the push test sets the book and the costs
  aside for every push, not only for the shops' push; the power-cut test does not read the planned batches of
  the recurring production; in the runner a pool with no staffing receipt would lose its members without a
  word of its own (`run.rs`, `kept`; the check of each place's people would then refuse the period); the
  projection drops every empty line; the row writer takes its header from period 1 and adds unchecked.
