# Stored Hours in the Small World Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** The small world's scene shows the hours stored in goods, measured by the existing recorded-labor ledger,
split by the claim through which they reached each household group.

**Architecture:** The fold of the ledger (the step that carries hours through one period) first reads a view of
one period inside the stored records, then moves into a crate of its own that needs only the engine; the stored
records keep their register checks, their checkpoint codec, their check of attendance and their binding to one
catalog, byte for byte. The runner of the small worlds, when it is opened with hours, folds every period twice
(once in hours, once in units of opening stock) and splits each household group's hours back by the kinds of
money in its purse. The scene reads that record: goods squares part full and part hollow, a standing line, a
second set of table columns and the details panel.

**Tech Stack:** Rust: `babylon-persistence` (stored records), a new crate `babylon-recorded-labor` (the fold and
the split by claim), `babylon-circuit-worlds` (the runner), `babylon-material-circuit` (the bench, tests only),
`babylon-client` (the scene, Bevy).

**Spec:** `docs/superpowers/specs/2026-11-23-stored-hours-in-the-small-world-design.md` (rules S1 to S11, "How
we know it works", the build order of seven tasks); `ai/decisions/ADR322_whose_hours.yaml` (H1 to H4). Issue
PER-371.

**When it is built.** After the closest form's plan
(`docs/superpowers/plans/2026-11-23-adjust-2-the-closest-form.md`), Tasks 2 to 8 and 2c to 8c, and before the
bridge (ADR322, H3). Tasks 1 and 2 touch only the stored records and are written against the code as it stands
today. Tasks 3 to 7 are written against the closest form's Interfaces; at the head of each, the code as built
binds, and the lead reads the task again against the built code before it starts.

## The Director's rulings (ADR322)

**H1. By the claim.** A group's hours back are split by its own kinds of money: for work (wages), by owning
(profit, later rent and interest), as support (benefits, later kin and aid). No national rate; only the group's
own sums. Built in Task 4, drawn in Task 6.

**H2. Lending, collecting rent and guarding store nothing.** A ruled direction for banks, landlords' companies
and police, not built here (the lead's reading). In the small world nothing changes: the shop carries the food
and keeps its hours in it. No task builds anything for H2; Task 2 keeps the place where such hours will enter
(direct work posted to an end of its own, as the ledger already does for an organizer's and an agency's hours).

**H3. After the six rules.** Seven tasks between the closest form and the bridge; the Director kept the order
when told seven, not five. This plan is those seven.

**H4. The bribe is read against hours on the clock.** Hours back for work beyond the hours a worker was on the
clock, worked or idle. In the small world it is not expected to arise, so nothing is drawn. It is counted over
the run so far, not period by period, and by tests, not by the runner (Task 4); if a test finds one, the builder
stops and the lead brings it to the Director (the lead's reading).

## Global Constraints

- Work only in `/media/user/dev-ssd/worktrees/households-homes/babylon`, branch `codex/households-and-homes`. Start
  every shell command with `cd` to it (or to its `rust/`). Never push. No `.env`, no `uv.lock`.
- One cargo, mise or test process at a time on the whole machine. Never pass `-j`. Only `mise exec -- cargo ...`
  and `mise run ...`. A build in another checkout empties this one's cache: launch long tests with `--no-build`
  after a build when the lead says another checkout is building.
- A command that may run longer than ten minutes runs in the background: its output goes to a log file in your
  scratch directory, and the command line ends with `; echo "END <name> status=$?" >> <log>`. Wait for the end
  marker; never poll the log in a loop.
- **The stored records do not change behaviour.** Their stored formats (the checkpoint's bytes and digest, the
  JSON of a period), their refusals and the order of their refusals stay. The tests that go through the ledger's
  public entry (`RecordedLaborLedger`) and the live database tests pass unchanged. Tests of the fold's inner parts
  keep every check and change only where they find those parts (`use` lines, the view they pass).
- **The engine is not changed.** No file under `rust/crates/babylon-material-circuit/src` changes in this plan.
  No hours enter the engine, its state, its digests or its receipts.
- **Hours and money never meet** but in one place: `claim::split_hours`, which splits hours by the shares of one
  group's own purse (Task 4). No rate between hours and money anywhere.
- **The new crate** `babylon-recorded-labor` depends on `babylon-material-circuit`, `babylon-kernel` and `serde`
  only; never on `babylon-tick`, `babylon-persistence`, `babylon-circuit-worlds` or the client.
- No pinned value of an existing test changes, but those this plan names (Task 5): by S11, the three lines of
  `scene_tests.rs` that name `STORED_WORK_LINE` (its import, `all.contains` of "Stored work got back: not measured
  yet." and the `assert_eq!` in `the_table_switches_its_grouping_and_period`), and `panel.rs`'s test
  `the_stored_work_line_is_built_from_the_not_measured_words`, which goes with the line;
  `not_drawn_line_prints_the_report`: "food 8" becomes "food 4" (the opening's food is drawn hollow and the
  farm's new food full, each set to 95 % on its own). Inner tests change imports and the view they pass only
  (Tasks 1, 2).
- Hours are `u64` whole hours where the engine counts them (given, on the clock), `u128` micro-hours where the
  ledger carries them; opening stock in the second run is `u128` micro-units (a unit is 1,000,000). Money is
  `i128` millionths of a dollar. Arithmetic is checked; a failure is a typed error, never a panic or a wrap.
- Functions under 100 lines and a cognitive complexity of 25 (`rust/clippy.toml`). No `unwrap`; an `allow` or
  `expect` attribute carries a `reason`. Import a type and use its bare name (bsl-sentinels refuses a
  module-qualified type used inline). No `mod.rs`; a file with a folder beside it holds only `mod` and `pub use`.
  No `bool` parameter. Every line number is a hint; find each place by its text.
- The client's standing rules (Tasks 5 to 7): no test opens a window; every text entity is built by
  `controls::text`, which carries `DeclaredSurface { id: SurfaceId::SmallWorld }`; a figure on screen is exactly
  the record's (a rounded figure says so on screen and the panel gives the exact one); words that name a unit are
  built from the constants; sizes, colours and places on screen are the lead's, and a builder does not judge them.
  A proof script is run by the lead on the real display, never by the builder.
- **Gates.** Each task lists its legs; run them one at a time, from `rust/` unless written otherwise:
  - fmt: `mise exec -- cargo fmt --all -- --check`
  - clippy: `mise exec -- cargo clippy --workspace --all-targets --locked -- -D warnings -D
    clippy::cognitive_complexity`
  - a crate's tests: `mise run rust:test:q -- -p <crate>` (with `-E '<filter>'` where a task says so)
  - sentinels: `mise run check:bsl-sentinels`
  - **The companion's gate** (Tasks 5 to 7): fmt; clippy; `mise run rust:test:q -- -p babylon-client -E
    'test(small_world)'` (Tasks 6 and 7: `-E 'test(small_world) | test(human_numbers)'`); sentinels.
  - **The live database tests** (Tasks 1 and 2), from the repository root, each in the background (each takes
    about half an hour): `BABYLON_POSTGRES_LIVE_FOCUS=reader mise run test:rust-postgres` and
    `BABYLON_POSTGRES_LIVE_FOCUS=money_journal mise run test:rust-postgres`. What must be up first: the Docker
    daemon, and `psql` on the `PATH`. The runner (`tools/run_rust_postgres.sh`) builds its image and starts its
    own disposable container on a dynamic port; it never touches `babylon-pg-isolated` (port 5433). Never run
    `mise run db:up` for these. Read the log: every phase line `Rust PostgreSQL phase complete: ... status=0`,
    and every `running N tests` line with N above 0. **A phase that prints "running 0 tests" is a fault, not a
    pass**: stop and report it. A failing test is compared with the baseline of Task 1, Step 0.
- Commit: `git add <files>`; the message in a file; `PYTHONPATH=src mise exec -- git commit -q -F <file>`; then
  check `git log --oneline -1` (a hook can abort silently). Subjects in the repository's form, a scope with no
  space. The body ends with `Part of PER-371` and a `Co-Authored-By` line naming the model that wrote the commit.

## Review Focus

1. **A stored format drifts while the code moves.** A checkpoint's bytes, its digest or a period's JSON could
   change with no test failing: no test pins them today (both checkpoint tests compare a checkpoint with itself).
   Pinned by Task 1's `the_stored_forms_of_three_periods_are_pinned`, written and seen passing before anything
   moves, and run unchanged at the end of Tasks 1 and 2.
2. **A refusal comes in another order.** The attendance check runs inside today's fold after the check of opening
   positions; the split could move it. Pinned by Task 1's `the_refusals_keep_their_order` (the three pairs the
   public entry can reach), run unchanged in Task 2; the reviewer reads `advance`'s order for the rest.
3. **The two runs drift apart.** The second run (opening units) is the same fold on a second figure. If a phase
   ever decided by what it carries, the runs would hand over different moves. The runner pairs the two runs'
   hand-overs one by one and refuses a period where they differ (Task 3,
   `the_two_runs_hand_over_the_same_moves`), and the long test folds every reference run (Task 3).
4. **A figure on screen the ledger did not produce.** The client must not sum hours of its own. Every hollow part
   is a move's `opening` from the record; every table cell is a sum of the record's household or workplace
   figures. Pinned by Task 5's `every_hollow_part_is_the_record_s` and Task 6's `the_hours_table_is_the_record_s`.
5. **Money meets hours outside the split, or the split does not add up.** Pinned by Task 4's unit tests of
   `split_hours` and the runner's two identities, checked every period of every run (a refusal stops the run),
   and by the long test. A reviewer greps the new crate and the runner for any product of a money amount and an
   hours amount outside `claim/split.rs`. A hidden bribe (a group's hours back for work passing its hours on the
   clock, counted over the run so far) is looked for by Task 4's `no_group_s_back_for_work_passes_its_clock` and
   by the long test. The runner does not refuse it: it would be a fact of the economy, not a broken sum. If a
   test finds one, the builder stops and the lead brings it to the Director.
6. **The bench changes.** The reference tests must not fold, so their rows and their time stay. Pinned by Task
   3's `a_runner_opened_without_hours_keeps_no_record` and by the closest form's long `reproduces_` tests, run at
   the end of Task 3.

## File Structure

| File | What it holds | Tasks |
| --- | --- | --- |
| `rust/crates/babylon-persistence/src/recorded_labor/stored_form_tests.rs` | The stored forms and the order of refusals pinned | 1 |
| `rust/crates/babylon-persistence/src/recorded_labor/view.rs` | The view of one period, and the map of the tick's receipts into it | 1, 2 |
| `rust/crates/babylon-persistence/src/recorded_labor/{period,attendance,identities,checkpoint,model}.rs` | The stored entry, attendance, assets, the codec, the stored types | 1, 2 |
| `rust/crates/babylon-persistence/src/recorded_labor/{book,production,circulation,services*,auxiliary*}.rs` | The fold's parts, until Task 2 moves them | 1, 2 |
| `rust/crates/babylon-persistence/src/recorded_labor/{tests,collection_tests,checkpoint_tests}.rs`, `services/tests.rs`, `auxiliary/{tests,aid_tests}.rs` | Inner tests: imports and the view only | 1, 2 |
| `rust/crates/babylon-persistence/Cargo.toml`, `rust/Cargo.toml`, `rust/Cargo.lock` | The new crate in the workspace and in the stored records | 2 |
| `rust/crates/babylon-recorded-labor/Cargo.toml`, `src/lib.rs` | The new crate | 2 |
| `rust/crates/babylon-recorded-labor/src/{model,book,view,fold,phases}.rs` | Ledger types, the stock book, the view, the entry, the phases for the stored records' tests | 2 |
| `rust/crates/babylon-recorded-labor/src/{production,circulation,household_work}.rs`, `services.rs`, `services/close.rs`, `auxiliary.rs`, `auxiliary/{aid,assets}.rs` | The fold's phases, moved | 2 |
| `rust/crates/babylon-recorded-labor/src/claim.rs`, `src/claim/{kind,mix,purses,split,tests}.rs` | By the claim: kinds, mixes, purses, the split | 4 |
| `tests/unit/test_mise_tasks.py`, `tools/postgres_national_lifecycle.sh` | The new crate named in two rosters | 2 |
| `rust/crates/babylon-circuit-worlds/Cargo.toml`, `src/runner.rs`, `src/lib.rs` | The dependency and the exports | 3 |
| `rust/crates/babylon-circuit-worlds/src/runner/hours.rs` | The runner's ledger: both runs, `PeriodHours`, the checks | 3, 4 |
| `rust/crates/babylon-circuit-worlds/src/runner/{run,result,error}.rs` | `open_world_with_hours`, `PeriodResult.hours`, the refusals | 3, 4 |
| `rust/crates/babylon-circuit-worlds/tests/hours.rs` | The pinned figures, the laws, both shocks, work elsewhere, the claims | 3, 4 |
| `rust/crates/babylon-material-circuit/tests/adjustment_bench/sets.rs` | `hours_fold_every_reference_run` | 3, 4 |
| `rust/crates/babylon-client/src/small_world/{reading,frame,controls,panel,table,scene}.rs` | Part-full squares, the standing line, the words, the table's switch | 5, 6 |
| `rust/crates/babylon-client/src/small_world/inspect.rs`, `src/human_numbers.rs` | The details panel's hours, exact figures | 6 |
| `rust/crates/babylon-client/src/small_world/{script,script_tests,scene_tests}.rs` | Commands, the report's hours, proof scripts | 5, 6, 7 |

---

### Task 1: The view of one period, still inside the stored records

Written against the code as it stands. Commit
`refactor(persistence): the recorded-labor fold reads a view of one period`.

**Files:**
- Create: `rust/crates/babylon-persistence/src/recorded_labor/stored_form_tests.rs`;
  `rust/crates/babylon-persistence/src/recorded_labor/view.rs`;
  `rust/crates/babylon-persistence/src/recorded_labor/household_work.rs`.
- Modify (under `rust/crates/babylon-persistence/src/`): `recorded_labor.rs` (the new modules);
  `recorded_labor/period.rs` (the entry builds the view; the fold body becomes `fold_period`);
  `recorded_labor/attendance.rs` (keeps `report` and `household_time`; `agency_observations` and `collections`
  move to `household_work.rs`); `recorded_labor/production.rs`, `circulation.rs`, `services/close.rs`,
  `auxiliary/aid.rs`, `auxiliary/assets.rs` (each phase takes `&PeriodView<'_>` in place of the states and
  `&MaterialTickReceipts` it took); the inner tests `collection_tests.rs`, `services/tests.rs`,
  `auxiliary/tests.rs`, `auxiliary/aid_tests.rs` (they pass a `PeriodView` built from their receipts, decision 6).

**Interfaces:**

```rust
// src/recorded_labor/view.rs
/// One agency observation as hours of one household: what the fold needs of an `AgencyPaidReceipt`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct AgencyHours { pub principal_id: FinalDemandPrincipalId, pub labor_unit_id: UnitId, pub hours: u64 }
/// The receipts of one period that the fold reads, borrowed; every list in the order of its source.
pub(crate) struct ReceiptView<'a> {
    pub aid: &'a [AidReceipt], pub collections: &'a [CollectionReceipt], pub agency: &'a [AgencyHours],
    pub installation: &'a [InstallationReceipt], pub equipment_wear: &'a [EquipmentWearReceipt],
    pub maintenance: Option<&'a MaintenanceReceipt>, pub production: &'a [ProductionReceipt],
    pub dispatches: &'a [RoutedDispatchReceipt], pub losses: &'a [FreightLossReceipt],
    pub arrivals: &'a [ArrivalReceipt], pub handling: &'a [MerchantHandlingReceipt],
    pub local_fulfillments: &'a [LocalRetailFulfillmentReceipt], pub local_transfers: &'a [LocalTransferReceipt],
    pub procurement: &'a [ProcurementReceipt], pub service_outputs: &'a [ServiceOutputReceipt],
    pub service_performance: &'a [ServicePerformanceReceipt], pub household_services: &'a [HouseholdServiceReceipt],
    pub household_consumption: &'a [HouseholdConsumptionReceipt],
}
/// One period: the number it closes, the states either side of it, and its receipts.
pub(crate) struct PeriodView<'a> { pub period: u64, pub before: &'a MaterialCircuitState,
    pub after: &'a MaterialCircuitState, pub receipts: ReceiptView<'a> }
/// The agency rows of the tick's receipts as hours by household, in their order.
pub(crate) fn agency_hours(receipts: &MaterialTickReceipts) -> Vec<AgencyHours>;
/// The view of the tick's receipts; `agency` is `agency_hours(receipts)`, kept by the caller.
pub(crate) fn receipt_view<'a>(receipts: &'a MaterialTickReceipts, agency: &'a [AgencyHours]) -> ReceiptView<'a>;
// src/recorded_labor/period.rs (private)
/// The positions of `before` match `book`; the sum of the book's hours. Refuses `OpeningPositionMismatch`,
/// then `Arithmetic`, as today's two steps do.
fn check_opening(book: &Book, catalog: &MaterialCatalog, before: &MaterialCircuitState)
    -> Result<(u128, Vec<RecordedLaborPosition>)>;
/// The fold of one period over a copy of `book`: the phases in today's order, the closing check and the law.
fn fold_period(book: &Book, catalog: &MaterialCatalog, view: &PeriodView<'_>) -> Result<Folded>;
/// What one fold gives back: the closing book, the totals, the closing positions and the edges.
struct Folded { book: Book, closing_positions: Vec<RecordedLaborPosition>, closing_recorded: u128,
    direct: u128, released: u128, edges: Vec<LaborEdge> }
// src/recorded_labor/household_work.rs: `agency_observations(frame, view: &PeriodView<'_>)` and
// `collections(frame, view: &PeriodView<'_>)`, moved from attendance.rs; only their reads of the receipts change.
```

Each phase takes `&PeriodView<'_>` (period, before, after, receipts) in place of the states and
`&MaterialTickReceipts` it took; `household_work::collections` likewise. Each phase that read `r.resolve_tick`
reads `view.period`; each that read `&receipts.maintenance` reads `view.receipts.maintenance`. The phases' names
and their order in the fold do not change.

**Decisions:**
1. **The guard first.** No existing test pins a stored form: `checkpoint_tests.rs` compares a checkpoint with
   itself (`checkpoint_resumes_real_carry_...`, `checkpoint_validates_...`), and no test under
   `babylon-persistence/tests/` pins checkpoint bytes or a period's JSON (checked with `rg -n "sha256|BYLLABOR"`
   over both). So this task writes the guard before it changes anything, sees it pass, and sees it pass again at
   the end. It goes only through the public entry (`RecordedLaborLedger`), so Task 2 does not touch it.
2. **What is pinned.** The fixture is `production_projection::recurring_fixture::materials()` as
   `checkpoint_tests.rs` opens it, three periods (`prepare_next` and `decode_material_receipts`, as there). For
   each period: the lowercase hex of `content_digest::sha256_of(&checkpoint.bytes)` and of `checkpoint.sha256`
   (they are equal), the hex of `sha256_of(&serde_json::to_vec(&period)?)` for the `RecordedLaborPeriod`, and its
   four totals. Then one period of `production_projection::equipment_fixture` as `tests.rs` uses it
   (`a_project_started_and_finished_in_one_close_...`), pinned the same way, so equipment and installation nodes
   are in the JSON. The builder runs the test once with the digests empty, copies what the failure message prints
   into the literals, and commits the test with those values. A value is never edited after that.
3. **The order of refusals today** (`period.rs` `advance`): `DiscontinuousPeriod`; `OpeningPositionMismatch`;
   `Arithmetic` of the opening sum; `ReceiptMismatch("household_time")`; `InvalidAttendance`; then the fold's own
   refusals in the order of its phases; `ClosingPositionMismatch`; `Conservation`; then the assets'
   `ReceiptMismatch`. The view does not change it: `advance` checks continuity, then `check_opening`, then
   `household_time`, then `attendance::report`, then `fold_period`, then `identities::crossed`. `fold_period`
   checks the opening positions again at its head (it passes there, so the order is unchanged); Task 2 needs that
   check inside the fold.
4. **What stays with the stored records:** continuity and digests, attendance (`report`, which calls
   `production_projection::validate_completed_labor`), household time, assets (`identities::crossed`, which reads
   `MaterialTickReceipts.installation`), the codec and the ledger's source. They keep reading
   `MaterialTickReceipts`. Everything else reads the view.
5. **The agency rows** become `AgencyHours` (principal, unit, hours), in the order of `receipts.agency_paid`. The
   fold reads nothing else of them. `ReceiptRef::new(AgencyPaid, ordinal)` keeps its ordinal.
6. **The inner tests** build `PeriodView { period: receipts.resolve_tick, before, after, receipts:
   receipt_view(&receipts, &[]) }` (or `&agency_hours(&receipts)` where a test has agency rows) and pass it where
   they passed the states and `&receipts`. No assertion changes.

- [ ] **Step 0: The baseline of the live tests,** on the code as it stands, before any change, both focuses
  (Global Constraints), in the background, one after the other. Keep the two logs: they are the baseline for
  Tasks 1 and 2. If either is not green, stop and report: this plan's Global Constraint cannot be checked.
- [ ] **Step 1: Write the guard** in `stored_form_tests.rs` (`#[cfg(test)] mod stored_form_tests;` in
  `recorded_labor.rs`):
  - `the_stored_forms_of_three_periods_are_pinned` (decision 2).
  - `the_refusals_keep_their_order`: from the recurring fixture's first period, the three cases the public entry
    can reach, each asserting the earlier refusal: a successor register of the wrong tick together with a member
    labor receipt off by one (`InvalidAttendance`'s fault) gives `DiscontinuousPeriod`; that member labor receipt
    together with a household consumption closing off by one gives `InvalidAttendance`; the consumption closing
    off by one alone gives `ReceiptMismatch("household_consumption")` (as `tests.rs` already has). Build the
    faults as `tests.rs` does, by editing a decoded receipt or the register before `advance`. Not reachable, so
    not built: `OpeningPositionMismatch` (the book is private to `period`, and `restore_checkpoint` refuses a book
    whose quantities differ) and `ReceiptMismatch("household_time")` (the fixture models no household time).
  Run them: `mise run rust:test:q -- -p babylon-persistence -E 'test(stored_form_tests)'`. Expected: they pass on
  the code as it stands (after the digests are filled once, decision 2).
- [ ] **Step 2: Write the view** and change every phase to read it; move `agency_observations` and `collections`
  to `household_work.rs`; split `advance` into `check_opening` and `fold_period`. No logic changes.
- [ ] **Step 3: Run** the ledger's tests: `mise run rust:test:q -- -p babylon-persistence -E
  'test(recorded_labor) | test(money_journal) | test(observer_material) | test(labor)'`. Expected: all pass, the
  guard among them, unchanged.
- [ ] **Step 4: Run the gate:** fmt; clippy; `mise run rust:test:q -- -p babylon-persistence` (in the background,
  Global Constraints); sentinels; then both live focuses in the background. Compare with Step 0's logs: the same
  phases, the same counts, every phase `status=0`, no "running 0 tests". **Commit** the subject above.

### Task 2: The fold moves into its own crate, with an entry that takes each period's catalog

Written against the code as it stands after Task 1. Commit
`refactor(recorded-labor): the ledger's fold in a crate of its own`.

**Files:**
- Create: `rust/crates/babylon-recorded-labor/Cargo.toml`; `src/lib.rs`; `src/model.rs`; `src/book.rs`;
  `src/view.rs`; `src/fold.rs`; `src/phases.rs`; `src/production.rs`; `src/circulation.rs`;
  `src/household_work.rs`; `src/services.rs`; `src/services/close.rs`; `src/auxiliary.rs`;
  `src/auxiliary/aid.rs`; `src/auxiliary/assets.rs`; `src/tests.rs` (all under the new crate).
- Delete (moved; `git mv` where a file moves whole): from `rust/crates/babylon-persistence/src/recorded_labor/`,
  `book.rs`, `production.rs`, `circulation.rs`, `household_work.rs`, `services.rs` (its `tests` module stays:
  see decision 6), `services/close.rs`, `auxiliary.rs` (likewise), `auxiliary/aid.rs`, `auxiliary/assets.rs`.
- Modify: `rust/Cargo.toml` (member; `[profile.dev.package."babylon-recorded-labor"] opt-level = 3` beside
  the persistence one); `rust/Cargo.lock`; `rust/crates/babylon-persistence/Cargo.toml` (the dependency);
  `babylon-persistence/src/recorded_labor.rs` (re-exports); `recorded_labor/model.rs` (keeps the stored types:
  `RecordedAttendance`, `RecordedCompensation`, `RecordedHouseholdTime`, `RecordedLaborPeriod`);
  `recorded_labor/view.rs` (keeps only `agency_hours` and `receipt_view`, returning the new crate's types);
  `recorded_labor/period.rs` (calls the new crate's entry); `recorded_labor/checkpoint.rs` (reads the new crate's
  `Book` and `Position`); the inner tests (imports); `tests/unit/test_mise_tasks.py` (`PEDANTIC_RUST_PACKAGES`);
  `tools/postgres_national_lifecycle.sh` (both lists of `national_source_paths`).

**Interfaces:**

```rust
// babylon-recorded-labor src/model.rs: moved from the stored records with their derives, docs and Serialize
// unchanged: LaborBasis, LaborId (its hex written here, byte for byte the stored records' `digest_hex`),
// LaborNode (its constructors `site`, `household`, `process`, `work`, `freight`, `installation`, `equipment`,
// `maintenance`, `household_work`, `sink` become `pub`), LaborEdge, ReceiptRef (`new` becomes `pub`),
// LaborReceiptFamily, LaborDisposition, RecordedLaborPosition, RecordedLaborError (every variant, with its
// Display), MICROS_PER_HOUR.
/// One unit of opening stock in the second run, as hours are counted: a millionth is the smallest share.
pub const MICROS_PER_UNIT: u128 = 1_000_000;
// src/book.rs
/// What a fold carries: hours of work, or units of opening stock (each opening unit carries `MICROS_PER_UNIT`,
/// and work adds none).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Carry { Hours, OpeningUnits }
#[derive(Clone, Copy, Default, PartialEq, Eq, Debug)]
pub struct Position { pub quantity: u64, pub basis: LaborBasis }
pub type Book = BTreeMap<LaborNode, Position>;
/// One move of stock from one holder to another, as the fold handed it over: a service performed, a local
/// transfer, a dispatch, a retail fulfillment. `basis` includes the handling hours added at the hand-off; `to` is
/// the receiver's own node (a household's stock even when the fold booked it to `FinalDemandOutlay`).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Handed { pub receipt: ReceiptRef, pub from: LaborNode, pub to: LaborNode, pub quantity: u64,
    pub basis: LaborBasis }
pub struct Frame { pub book: Book, pub edges: Vec<LaborEdge>, pub handed: Vec<Handed>,
    pub direct_micro_hours: u128, pub released_micro_hours: u128, carry: Carry }
impl Frame {
    /// A frame that carries hours: today's `new`.
    #[must_use] pub fn new(book: Book) -> Self;
    #[must_use] pub fn carrying(book: Book, carry: Carry) -> Self;
    // quantity, take, credit, edge, move_units, release, release_basis: moved, `pub`, unchanged.
    /// Direct work: posts `hours` as micro-hours under `Carry::Hours`, and nothing under `Carry::OpeningUnits`;
    /// the edge is written either way.
    pub fn direct(&mut self, workplace: LaborNode, dest: LaborNode, hours: u64, receipt: ReceiptRef)
        -> Result<LaborBasis, RecordedLaborError>;
}
// src/view.rs: AgencyHours, ReceiptView, PeriodView of Task 1, now `pub` with `pub` fields.
// src/fold.rs
/// Every positive stock of `state` by node (today's `quantities`). Errors: `QuantityMismatch`.
pub fn positions_of(catalog: &MaterialCatalog, state: &MaterialCircuitState)
    -> Result<BTreeMap<LaborNode, u64>, RecordedLaborError>;
/// The opening book: every position of `state` not measured (`unknown_opening`), carrying 0 (`Carry::Hours`) or
/// its quantity times `MICROS_PER_UNIT` (`Carry::OpeningUnits`). Errors: as `positions_of`; `Arithmetic`.
pub fn opening_book(catalog: &MaterialCatalog, state: &MaterialCircuitState, carry: Carry)
    -> Result<Book, RecordedLaborError>;
/// `book` holds the positions of `before`: its total and rows. Errors: `OpeningPositionMismatch`, `Arithmetic`.
pub fn check_opening(book: &Book, catalog: &MaterialCatalog, before: &MaterialCircuitState)
    -> Result<(u128, Vec<RecordedLaborPosition>), RecordedLaborError>;
/// One period folded. The four totals are micro-hours under `Carry::Hours`, micro-units under `OpeningUnits`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FoldedPeriod { pub closing: Book, pub opening_positions: Vec<RecordedLaborPosition>,
    pub closing_positions: Vec<RecordedLaborPosition>, pub opening_recorded: u128, pub closing_recorded: u128,
    pub direct: u128, pub released: u128, pub edges: Vec<LaborEdge>, pub handed: Vec<Handed> }
/// Fold one period from `book` under the catalog that period closed under; the book is not changed. Errors:
/// `DiscontinuousPeriod` (`before.period != period` or `after.period != period + 1`); as `check_opening`; the
/// phases' refusals; `ClosingPositionMismatch`; `Conservation`.
pub fn fold_period(book: &Book, catalog: &MaterialCatalog, view: &PeriodView<'_>, carry: Carry)
    -> Result<FoldedPeriod, RecordedLaborError>;
// src/phases.rs: `pub use` only, for the stored records' inner tests: production::execute,
// services::{handoff, finish}, circulation::{freight_arrivals, outbound, consume},
// auxiliary::{aid_arrivals, aid_dispatch, maintenance_and_installation, productive_assets, installation,
// maintenance_close} (each `pub`, its signature unchanged; the last two are `pub(super)` in `assets.rs` today and
// `auxiliary/tests.rs` calls them), household_work::{agency_observations, collections}.
// babylon-persistence src/recorded_labor.rs gains:
pub use babylon_recorded_labor::{LaborBasis, LaborDisposition, LaborEdge, LaborId, LaborNode, LaborReceiptFamily,
    ReceiptRef, RecordedLaborError, RecordedLaborPosition, MICROS_PER_HOUR};
```

**Decisions:**
1. **The name and the place.** `rust/crates/babylon-recorded-labor`, package `babylon-recorded-labor`, library
   `babylon_recorded_labor`: the workspace names crates `babylon-<what it holds>`, and the ledger's types are all
   `RecordedLabor*` and `Labor*`. Its manifest copies `babylon-circuit-worlds`'s (workspace fields, `[lints]
   workspace = true`), with `babylon-kernel`, `babylon-material-circuit` and `serde = { version = "1", features =
   ["derive"] }` (the kernel already depends on serde; the moved types keep their `Serialize`, so the JSON the
   stored records publish keeps its bytes). Description: "The recorded-labor ledger's fold: hours carried through
   one period of the material circuit".
2. **One type for each thing.** The moved types are re-exported by the stored records at their old paths, so every
   consumer (`observer_reader`, `money_journal`, the CLIs, the live tests, the client's money map) compiles
   unchanged. `RecordedLaborError` moves whole, with the variants only the stored records produce
   (`FoundationRequired`, `CheckpointBinding`, `CheckpointDigest`, `CheckpointFormat`, `CheckpointVersion`,
   `InvalidAttendance`), so its paths, its variants and its Display stay. `RecordedAsset` and
   `RecordedAssetIdentity` stay with the stored records. Each item made `pub` gains its `# Errors` doc and
   `#[must_use]` where clippy asks; the new crate has its own `decimal` and hex writer, byte for byte the stored
   records'; the stored records keep theirs for `RecordedLaborPeriod` and the rest.
3. **The entry.** `RecordedLaborLedger::advance` keeps its checks (continuity, digests, one catalog), then
   `fold::check_opening`, `attendance::household_time`, `attendance::report`, then
   `fold::fold_period(&self.inventory, catalog, &view, Carry::Hours)`, then `identities::crossed`, then commits
   the closing book. It builds `RecordedLaborPeriod` from `FoldedPeriod` and ignores `handed`. `from_foundation`
   uses `opening_book(.., Carry::Hours)`; `restore_checkpoint` passes `positions_of` to the codec. The stored
   records keep refusing a changed catalog: the new crate's entry takes any catalog; the binding stays in
   `advance`.
4. **`handed`** is written where today's code takes a move's basis: `services::handoff` (a performed service, its
   basis as taken) and `circulation`'s `Handoff::debit` (a dispatch, a local transfer, a fulfillment, its basis
   with the handling hours added). For a fulfillment without a pantry row `to` is the household's stock node,
   though the hours go to `FinalDemandOutlay`. `handed` is written only when the quantity is above 0
   (`Handoff::debit` runs for a move of 0 too). It changes no edge, no book and no total.
5. **`Carry::OpeningUnits`** changes only `Frame::direct` (the seven calls of today's fold: production, handling,
   two in assets, aid, agency, collections) and `opening_book`. No phase reads `carry`. The law holds on the
   second figure by itself.
6. **The inner tests stay in the stored records** (they use `recurring_fixture` and `test_support`, which are the
   stored records' own): `services.rs` and `auxiliary.rs` of the stored records shrink to `#[cfg(test)] mod
   tests;` (and `mod aid_tests;`), the test files stay where they are, and each test reaches the phases through
   `babylon_recorded_labor::phases` and the book through `babylon_recorded_labor::{Book, Frame, Position}`. The
   floor-remainder test of `tests.rs` and `checkpoint_validates_...` change only their `use` lines. The codec reads
   `Position` and `Book` through their public fields.
7. **The new crate's own tests** (`src/tests.rs`), frame-level, with hand-built nodes as `tests.rs:85` builds them:
   it cannot use the stored records' fixtures, and the small worlds will depend on it (Task 3).
8. **Two rosters name every local crate**, so the new one is added: `tests/unit/test_mise_tasks.py`
   `PEDANTIC_RUST_PACKAGES` (it compares the list with every manifest that has `[lints] workspace = true`), and
   `tools/postgres_national_lifecycle.sh` `national_source_paths` (its loop list and its `case` list: it refuses
   "unrecorded local native dependency" otherwise, and `babylon-persistence` now has one). Nothing else changes in
   either file.
9. **The lock.** Written offline from `rust/`: `mise exec -- cargo metadata --offline --format-version 1 >
   /dev/null`. `git diff rust/Cargo.lock` shows one new package entry and one added dependency name in
   `babylon-persistence`; nothing else moves. Never `cargo update`.

- [ ] **Step 1: Write the new crate's failing tests** in `src/tests.rs`:
  - `opening_units_take_the_same_floor_shares_as_hours`: the floor-remainder case of the stored records'
    `mixed_inventory_preserves_the_floor_remainder_...` built twice, once `Frame::carrying(.., Hours)` and once
    `OpeningUnits` with the same quantities: every `take` returns the same share of its pool's figure, and the
    last unit carries the rest in both.
  - `direct_work_adds_nothing_to_opening_units`: `Frame::carrying(Book::new(), OpeningUnits).direct(.., 10, ..)`
    returns `LaborBasis::default()`, `direct_micro_hours` stays 0, and one edge of quantity 10 is written;
    under `Hours` it returns 10,000,000.
  - `the_opening_book_carries_a_unit_as_a_million`: through the crate-private `book_of(positions, carry)` that
    `opening_book` uses (a whole state needs the engine's fixtures): 40 units of one site stock carry 0 under
    `Hours` and 40,000,000 under `OpeningUnits`, `unknown_opening` in both.
  - `a_hand_over_is_recorded_with_its_handling`: `Handoff::debit` (crate-private) of 4 units from a pool of 8
    holding 8,000,000, with a handling row of 4 hours: one `Handed` with basis 8,000,000 (4 taken, 4 handled),
    `to` the receiver.
- [ ] **Step 2: Run them and see them fail:** `mise run rust:test:q -- -p babylon-recorded-labor`. Expected: does
  not compile, no package.
- [ ] **Step 3: Move** the files, write the entry, the re-exports, the manifest lines, the two rosters and the
  lock. Run the new crate's tests, then the ledger's tests as in Task 1, Step 3. Expected: all pass, the guard of
  Task 1 unchanged.
- [ ] **Step 4: Run the gate:** fmt; clippy; `mise run rust:test:q -- -p babylon-recorded-labor`;
  `mise run rust:test:q -- -p babylon-persistence` (background); `mise run rust:test:q -- -p babylon-client -E
  'test(money_map)'` (the client reads the re-exported types); sentinels; from the repository root
  `uv run --frozen pytest tests/unit/test_mise_tasks.py tests/unit/tools/test_postgres_national_capture.py -o
  addopts="" -q`; both live focuses in the background, compared with Task 1's baseline. **Commit** the subject
  above.

### Task 3: The runner folds, both runs

The lead read this task against the runner as built on 24 November (`Runner::turn_on`, `rules_at`,
`PeriodResult.rules`, `PeriodReceipts.adjustments`, both paths of the close); the text below is amended. Commit
`feat(circuit-worlds): the runner folds the hours of each period, twice`.

**Files:**
- Create: `rust/crates/babylon-circuit-worlds/src/runner/hours.rs`; `rust/crates/babylon-circuit-worlds/tests/hours.rs`.
- Modify: `babylon-circuit-worlds/Cargo.toml` (`babylon-recorded-labor`); `rust/Cargo.lock`; `src/runner.rs`
  (`pub mod hours;` beside its four modules, and the `pub use` of the hours' types); `src/lib.rs` (the same names
  in its `pub use runner::{..}`); `src/runner/run.rs` (`open_world_with_hours`, the fold in `advance`, the ledger
  in `Stepped` and kept by `step`); `src/runner/result.rs` (`PeriodResult.hours`); `src/runner/error.rs`
  (the refusals); `rust/crates/babylon-material-circuit/tests/adjustment_bench/sets.rs` (the long test).

**Interfaces:**

```rust
// babylon-circuit-worlds src/runner/hours.rs
/// A goods move as the scene reads it: the receipt list and its index.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum MovedBy { ServicePerformance(usize), LocalTransfer(usize), LocalFulfillment(usize) }
/// The hours and the opening units in one move, from the two runs' `Handed`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MoveHours { pub moved_by: MovedBy, pub quantity: u64, pub micro_hours: u128, pub opening_micro_units: u128 }
/// One household group's hours. `given`: hours into goods and services (production, handling, upkeep,
/// installing) by the household that gave them, idle apart (ruling 17). `clock`: worked or idle
/// (`attended_hours`). `back_micro_hours`: measured hours in what reached its home this period. `units`
/// received, `opening_micro_units` of them from the opening.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct HouseholdHours { pub given: u64, pub clock: u64, pub back_micro_hours: u128,
    pub opening_micro_units: u128, pub units: u64 }
/// One workplace's hours. `made_micro_hours`: the production edges into its own stock, as made. `handed_*`:
/// every `Handed` from its stocks.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct WorkplaceHours { pub given: u64, pub made_units: u64, pub made_micro_hours: u128,
    pub handed_units: u64, pub handed_micro_hours: u128, pub handed_opening_micro_units: u128 }
/// One place's sums, for the identity of "How we know it works": `given_micro_hours` is a million times the sum
/// of its workplaces' `given`; `held_*` are the hours in the stocks of its workplaces at the opening and the
/// close; `left` the hours released from those stocks, unsold or lost.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct PlaceHours { pub given_micro_hours: u128, pub back_micro_hours: u128, pub held_opening: u128,
    pub held_closing: u128, pub left_micro_hours: u128 }
/// The ledger's totals of one run.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct LedgerTotals { pub opening: u128, pub direct: u128, pub closing: u128, pub released: u128 }
/// The hours of one closed period. `moves`: one for each move of `service_performance`, `local_transfers` and
/// `local_fulfillments`, in that order. `households` in `World::households()` order; `workplaces` in
/// `Workplace::ALL` order; `places` in `Place::ALL` order.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PeriodHours { pub hours: LedgerTotals, pub opening_units: LedgerTotals, pub moves: Vec<MoveHours>,
    pub households: Vec<(Household, HouseholdHours)>, pub workplaces: Vec<(Workplace, WorkplaceHours)>,
    pub places: Vec<(Place, PlaceHours)> }
impl PeriodHours {
    #[must_use] pub fn of_move(&self, moved_by: MovedBy) -> Option<&MoveHours>;
    #[must_use] pub fn household(&self, household: Household) -> Option<&HouseholdHours>;
    #[must_use] pub fn workplace(&self, workplace: Workplace) -> Option<&WorkplaceHours>;
}
/// The two books the runner keeps from period to period (crate-private).
pub(crate) struct HoursLedger { hours: Book, units: Book }
impl HoursLedger {
    /// Both books from the opening state, every stock not measured.
    pub(crate) fn open(catalog: &MaterialCatalog, state: &MaterialCircuitState) -> Result<Self, RunnerError>;
    /// Fold one period twice and read its record; the ledger is not changed.
    pub(crate) fn fold(&self, world: &World, catalog: &MaterialCatalog, before: &MaterialCircuitState,
        transition: &MaterialCircuitTransition) -> Result<(Self, PeriodHours), RunnerError>;
}
/// The two runs' hand-overs agree index by index (decision 4); else `HoursRunsDiffer` (private).
fn same_moves(period: u64, hours: &[Handed], units: &[Handed]) -> Result<(), RunnerError>;
// babylon-circuit-worlds src/runner/run.rs
impl Runner {
    /// As `open_world`, with the hours ledger: each period is folded twice and its record kept in
    /// `PeriodResult.hours`. The scene opens with it; the bench's reference tests open with `open_world`.
    /// # Errors
    /// As `open_world`; `RunnerError::HoursRefused` when the ledger refuses the opening.
    pub fn open_world_with_hours(world: &World) -> Result<Self, RunnerError>;
}
// src/runner/result.rs, PeriodResult gains:
/// The hours of the period; `None` for a runner opened without hours.
pub hours: Option<PeriodHours>,
// src/runner/error.rs
/// Which of the two folds refused.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum HoursRun { Hours, OpeningUnits }
// RunnerError gains:
/// The hours ledger refused the period: a movement it has never seen, or closing stocks that differ.
HoursRefused { period: u64, run: HoursRun, error: RecordedLaborError },
/// The two runs handed over different moves.
HoursRunsDiffer { period: u64 },
/// A receipt the hours record cannot place: an agency row, or an account or site of no party of the world.
HoursUnplaced { period: u64, what: String },
```

**Decisions:**
1. **Asked for at the opening.** `open_world` does not change, and the bench's `rows` and every reference test
   keep calling it: they never fold, so their rows and their time stay. `open_world_with_hours` is `open_world`
   (rules turned on, pushes struck) and then `HoursLedger::open` with the catalog of the next period's figures
   and rules and the opening state. That catalog is in the runner's own `catalogs` under `CatalogKey { figures:
   book.figures(state.period), rules: rules_at(state.period) }`: `open_world` has made it, and
   `Runner::catalog()` is still `None` before the first step. `Runner::open()` keeps opening without hours, so no
   pinned test of the crate
   moves; the scene opens with hours (Task 5), which names the client's pins that move. The runner's field is
   `hours: Option<HoursLedger>`.
2. **Inside the step.** In `advance`, right after `check_conserved(..)?` and before
   `material_circuit_state_digest`, when `hours` is `Some`: `ledger.fold(&self.world, catalog, &self.state,
   &transition)?`. `catalog` is `advance`'s own local one, of this period's figures and rules, the one the close
   used: a rule turned on in the middle of a run, or a push, is folded under its own period's catalog. Both paths
   of the close reach this point (with the seekers, `staff_in_places` and `finish_with_place_staffing`; without,
   `staff` and `finish_with_staffing`). The new ledger goes into `Stepped`, beside `standing`, and is kept by
   `step` with the state, so a refused period changes nothing. The stop rule's standing is not read by the fold.
   The fold reads the whole transition, not `PeriodReceipts` (which leave out aid, collections,
   agency, household time, installation, equipment wear, maintenance, dispatches, arrivals and losses).
3. **The view of the transition:** `period` is `before.period`, `before` is the runner's state, `after` is
   `transition.state`, each list the transition's own; `agency` is empty. A transition with a row of
   `agency_attendance` is refused with `HoursUnplaced` ("an agency row"): the small world has none, and its rows'
   checks are the tick's.
4. **Both runs.** `fold_period(&self.hours, .., Carry::Hours)` and `fold_period(&self.units, ..,
   Carry::OpeningUnits)` on the same view. An error of either is `HoursRefused` with its `run`. The two `handed`
   lists must have the same length and, index by index, the same `receipt`, `from`, `to` and `quantity`; else
   `HoursRunsDiffer` (`same_moves`). The stock rule is the ledger's own pooled average (S4); nothing here rounds.
5. **The record.** `moves`: each `Handed` of family `ServicePerformance`, `LocalTransfers` or
   `LocalFulfillments`, with the hours run's `basis.recorded_micro_hours` and the units run's, in the order of
   their receipts (a move of quantity 0 has no `Handed`; the scene skips it too). `households`: `given` and
   `clock` from `transition.member_labor_use` by `payee` (the sums the client's `read_work` makes, so given
   follows the household, not the workplace); `back`, `opening`, `units` from every `Handed` whose `to` is a
   household stock of that household. `workplaces`: `given` by `site_id`; `made` from the production edges into
   the site's own stock (`LaborNode::Process` to `SiteStock` of the site); `handed` from every `Handed` whose
   `from` is a stock of the site. `places`: sums of their households and workplaces, except
   `given_micro_hours`: a million times the sum of the place's workplaces' `given` (equal to its households'
   while people work only in their place); `held` is the hours of the
   site stocks of the place's workplaces in the opening and closing books; `left` is the hours of every edge from
   a site stock of the place to a sink. A party of no household or workplace of the world is `HoursUnplaced`.
6. **Words.** `HoursRefused`: "Period {period}: the hours ledger refused it: {error}" and, for the second run,
   "Period {period}: the hours ledger refused it (opening units): {error}". `HoursRunsDiffer`: "Period {period}:
   the two runs of the hours ledger handed over different moves". `HoursUnplaced`: "Period {period}: the hours
   ledger cannot place {what}". The scene shows a refusal in the runner's words, as it shows every refusal.
7. **The long test** goes in the bench's `sets.rs`, beside the `reproduces_` tests, `#[ignore]`, and is not named
   `reproduces_` so the long tests' filter does not take it: `hours_fold_every_reference_run`. For each of
   `Form::ALL` and both scales (seven forms: 350 runs of 400 periods, each period folded twice), each run of
   `runs(form, scale)`, opened with `Runner::open_world_with_hours(&run.world)`
   and struck as `rows` strikes (`TurnedOn::AtOpening`; a rule turned on later is the crate's own test,
   `rules_turned_on_late_keep_the_ledger`), stepped `PERIODS_LONG` times: every step is `Ok`, and every period
   keeps both
   ledgers' law (`opening + direct == closing + released`), `hours.direct` equals 1,000,000 times the sum of
   `given`, and each place's identity holds (decision 8). On a failure it names the form, the scale, the run and
   the period. Its command: `mise run rust:test:q -- -p babylon-material-circuit --test adjustment_bench -E
   'test(hours_fold_every_reference_run)' --run-ignored only`, in the background.
8. **The place's identity** (How we know it works): `back + held_closing + left == given + held_opening`, in
   micro-hours. Only the tests check it; the ledger's law is what the runner enforces.

- [ ] **Step 1: Write the failing tests** in `tests/hours.rs`, each opened with
  `Runner::open_world_with_hours(&World::scene())` unless named otherwise, place A read (B is the same):
  - `the_scene_s_catalog_folds_its_first_period`: one step is `Ok` and `hours` is `Some` (the scene's real
    catalog, with its market rules, before anything is built on it).
  - `the_quiet_world_climbs_as_pinned`: 12 steps. In period p, place A's `back_micro_hours` is `240_000_000 -
    (80_000_000 >> (p - 1))` exactly for p = 1 to 11 (160, 200, 220, 230, 235, 237.5 hours, ...), and below
    240,000,000 in period 12. `given_micro_hours` is 240,000,000 every period. Each worker household's `given` is
    10 times its `Household::opening_persons`; owners' and supported `given` 0. In period 1 the backs are: utility
    workers 48, farm, clinic and shop workers 16 each, owners 32, supported 32 hours.
  - `a_unit_holds_its_recipe_s_hours`: from period 1, utility A `handed_micro_hours == handed_units * 1_000_000`
    (power 1); clinic A `== handed_units * 2_000_000` (care 2); farm A `made_micro_hours == made_units *
    2_000_000` (food 2 as made); shop A in period 1 `handed_micro_hours == handed_units * 1_000_000` with
    `handed_opening_micro_units == handed_units * 1_000_000` (every unit from the opening).
  - `the_opening_share_halves`: periods 1 to 4: food reaching place A's homes: the `moves` of
    `MovedBy::LocalFulfillment(i)` whose receipt (`result.receipts.local_fulfillments[i]`, its
    `demand_principal_id`) names a place A household (food is the only good a shop fulfils); summed,
    `opening_micro_units * 100` against `quantity * 1_000_000`: 100, 50, 25, 12.5 of every hundred. Over all of
    place A's moves (`moves` of its sites) 25, 12.5, 6.25, 3.125 of every hundred.
  - `every_period_keeps_both_laws_and_the_place_identity`: 34 steps quiet, and 60 steps under each of
    `(HarvestFails, A, UntilLifted)`, `(HarvestFails, Both, UntilLifted)`, `(PowerCut, A, UntilLifted)`,
    `(PowerCut, Both, UntilLifted)`, and harvest and cut both struck in Both, each struck before step 1: both
    `LedgerTotals` keep the law, `hours.direct` is 1,000,000 times the sum of every household's `given`, and each
    place's identity holds.
  - `the_failed_harvest_makes_food_of_twenty_ninths`: harvest struck in A before step 1: farm A's
    `made_micro_hours * 9 == made_units * 20_000_000` in periods 1 to 3.
  - `the_power_cut_makes_power_of_ten_ninths`: the cut struck in A: utility A's `made_micro_hours * 9 ==
    made_units * 10_000_000` in periods 1 to 3.
  - `given_follows_the_household_that_works_elsewhere`: the run of `fund_p2` in the client's `marks.rs` (the
    scene's world with the seekers as its one rule, `World::switches_at(Scale::Small)[1]`; harvest struck in
    Both after the opening and before step 1; the first move is in period 16), opened with hours; in the first
    period after a move, the home household's `given` equals
    the sum of its member receipts' given hours at every site, the host's `given` the sum at its site, and they
    differ from the hours of the host's own household.
  - `every_rule_on_keeps_the_ledger_for_60_periods`: the scene's world with all six rules (`World { rules:
    World::switches_at(Scale::Small).to_vec(), ..World::scene() }`), harvest in Both: 60 steps `Ok`, the laws as
    above.
  - `rules_turned_on_late_keep_the_ledger`: the run of `late_run` in the crate's `tests/runner.rs` (harvest in
    Both, the six rules of `LATE` turned on in the middle of the run, on from periods 21 to 41), opened with
    `open_world_with_hours`, for 60 steps: every step `Ok`, the laws as above. A rule turned on changes the next
    period's catalog; this is the test that a fold takes each period under its own.
  - `a_runner_opened_without_hours_keeps_no_record`: 34 steps of `open_world(&World::scene())` and of
    `open_world_with_hours(&World::scene())`: equal `state_digest` every period; `hours` is `None` and `Some`.
  - In `src/runner/hours.rs` tests: `the_two_runs_hand_over_the_same_moves` (a real period of the scene: the two
    `handed` lists agree, and `same_moves` of the hours run's list and a copy of the units run's list with one
    quantity changed gives `HoursRunsDiffer`);
    `a_refusal_is_told_in_the_ledger_s_words` (a real transition with one `local_fulfillments` quantity raised by
    one: `HoursRefused { run: Hours, .. }`, and its Display begins "Period 1: the hours ledger refused it: ");
    `an_agency_row_is_not_placed`.
- [ ] **Step 2: Run them and see them fail:** `mise run rust:test:q -- -p babylon-circuit-worlds -E 'test(hours)'`.
  Expected: does not compile, no `open_world_with_hours`.
- [ ] **Step 3: Implement** the ledger, the record, the refusals and the long test.
- [ ] **Step 4: Run** the crate's tests, then the long test, then every `reproduces_` long test of the bench, each
  in the background. Expected: all pass; the `reproduces_` sets 25 of 25 as before. If the long hours test finds
  a refused period, stop and report the form, run and period: a movement of the six rules the ledger has never
  seen is the first thing the bridge must know.
- [ ] **Run the gate:** fmt; clippy; `mise run rust:test:q -- -p babylon-circuit-worlds`; `mise run rust:test:q --
  -p babylon-material-circuit`; `mise run rust:test:q -- -p babylon-client -E 'test(small_world)'`; sentinels.
  **Commit** the subject above.

### Task 4: By the claim

The code as built binds: the lead reads this task again against the runner and the engine's money receipts after
the closest form's Task 7 (the owner's `CapitalContribution`) before it starts. Commit
`feat(circuit-worlds): hours back split by the claim, checked every period`.

**Files:**
- Create (under `rust/crates/babylon-recorded-labor/src/`): `claim.rs` (`mod` and `pub use` only);
  `claim/kind.rs`; `claim/mix.rs`; `claim/purses.rs`; `claim/split.rs`; `claim/tests.rs`.
- Modify: `babylon-recorded-labor/src/lib.rs`; `babylon-circuit-worlds/src/runner/hours.rs` (the purses kept and
  followed, the split, the checks); `src/runner/error.rs`; `src/lib.rs`; `tests/hours.rs`.

**Interfaces:**

```rust
// babylon-recorded-labor src/claim/kind.rs
/// The kind of money a group's hours back came through. `Work`: wages. `Owning`: profit (later rent and
/// interest). `Support`: benefits and the treasury's payments (later kin and aid). `NotRecorded`: money held at
/// the opening, whose kind was never recorded.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Claim { Work, Owning, Support, NotRecorded }
impl Claim { pub const ALL: [Claim; 4]; #[must_use] pub const fn index(self) -> usize; }
// src/claim/mix.rs
/// Money in millionths of a dollar by kind, in the order of `Claim::ALL`; every amount at least 0.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Mix { amounts: [i128; 4] }
impl Mix {
    #[must_use] pub const fn of(claim: Claim, amount: i128) -> Self;
    #[must_use] pub const fn amount(&self, claim: Claim) -> i128;
    pub fn total(&self) -> Result<i128, ClaimError>;                 // Arithmetic
    pub fn add(&mut self, other: Mix) -> Result<(), ClaimError>;     // Arithmetic
    /// Take `amount` out by the average rule (decision 3). Errors: `Overdrawn` (above the total or below 0).
    pub fn draw(&mut self, amount: i128) -> Result<Mix, ClaimError>;
}
// src/claim/split.rs
/// Hours split by kind, in micro-hours.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct ClaimHours { pub work: u128, pub owning: u128, pub support: u128, pub not_recorded: u128 }
impl ClaimHours {
    pub fn total(&self) -> Result<u128, ClaimError>;                 // Arithmetic
    pub fn add(&mut self, other: ClaimHours) -> Result<(), ClaimError>;
}
/// Split `micro_hours` by the shares of `paid`, the mix of the money that paid for them: each kind its floor
/// share, the rest to the last kind in order that holds money. The one place where hours and money meet.
/// Errors: `Unpaid` (`paid` totals 0 and `micro_hours` is above 0); `Arithmetic`.
pub fn split_hours(micro_hours: u128, paid: &Mix) -> Result<ClaimHours, ClaimError>;
// src/claim/purses.rs
/// Every household's purse by kind, and the money set aside for each of its open orders.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Purses { cash: BTreeMap<FinalDemandPrincipalId, Mix>,
    reserves: BTreeMap<OutboundOrderId, (FinalDemandPrincipalId, Mix)> }
/// What paid for each order this period: the mix that left its reserve by `DeliverySettlement`.
pub type Paid = BTreeMap<OutboundOrderId, Mix>;
impl Purses {
    /// Every household's cash and open reserves at the opening, all `NotRecorded`. Errors: `NotMonetary`.
    pub fn open(state: &MaterialCircuitState) -> Result<Self, ClaimError>;
    /// Follow the period's transfers in their order; what paid for each order. Errors: `Unexpected { index }`
    /// for a household's transfer of a purpose decision 1 does not name; `Overdrawn`; `UnknownOrder`.
    pub fn follow(&mut self, transfers: &[MoneyTransferReceipt]) -> Result<Paid, ClaimError>;
    /// Each household's kinds equal its cash in the book; the kinds held for each open order equal that
    /// purchase's reserve. Errors: `PurseDiffers`, `ReserveDiffers`.
    pub fn check(&self, state: &MaterialCircuitState) -> Result<(), ClaimError>;
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ClaimError { Arithmetic, NotMonetary, Overdrawn, Unpaid, UnknownOrder(OutboundOrderId),
    Unexpected { index: usize }, PurseDiffers { principal: FinalDemandPrincipalId, kinds: i128, book: i128 },
    ReserveDiffers { order: OutboundOrderId, kinds: i128, book: i128 } }
// impl Display and Error for ClaimError.
// babylon-circuit-worlds src/runner/hours.rs, HouseholdHours gains:
/// Its back split by the claim; the four add up to `back_micro_hours`.
pub claims: ClaimHours,
// HoursLedger gains `purses: Purses`. RunnerError gains:
/// The purses could not follow the period's money.
ClaimRefused { period: u64, error: ClaimError },
/// The kinds of a household's purse and its reserves are not its cash and reserves in the book.
PurseNotBook { period: u64, error: ClaimError },
/// The splits of a group's back do not add up to its back.
ClaimsNotBack { period: u64, household: Household, back: u128, claims: u128 },
```

`ClaimHours` and `Claim` are re-exported by the small worlds' crate, so the client does not depend on the new
crate.

**Decisions:**
1. **Kinds by purpose, on the credit side:** `WagePayment` into a household's cash is `Work`;
   `Cash(OwnershipDistribution)` is `Owning`; `Cash(PublicTransfer)` (the fund's benefits, its laid-off program and
   the treasury's income support), `Cash(HouseholdTransfer)` and `Cash(MutualAid)` are `Support`. Money held at
   the opening is `NotRecorded`. A transfer into a household's cash of any other purpose is `Unexpected`.
2. **The debit side draws the mix.** A household's `PurchaseReservation(order)` draws from its cash into
   `reserves[order]`; `DeliverySettlement(order)` draws from that reserve, and the mix drawn is added to
   `Paid[order]`; `PurchaseRefund(order)` draws from the reserve back into the cash; `Cash(Tax)`,
   `Cash(CapitalContribution)` and any other `Cash(..)` out of a household draw from its cash and leave. A reserve
   that reaches 0 is removed. Transfers with no household on either side (wages reserved by a site, a site's
   purchases, the public accounts' own) change no purse.
3. **The rounding of a draw.** "Floor shares, the last carries the rest" cannot be used across kinds as written:
   with kinds 1, 1, 0 and a draw of 1, the floors are 0 and the last kind would carry 1 it does not hold. So each
   kind gives its floor share, `amount * k / total` in the ledger's form `(k / total) * amount + ((k % total) *
   amount) / total`, and the rest (fewer units than there are kinds) is taken from the kinds in the order of
   `Claim::ALL`, each as far as it still holds. A draw of the whole purse takes every kind whole. The split of
   hours (`split_hours`) is the ledger's own rule: floor shares, the rest to the last kind that holds money.
4. **The split of back.** For each `Handed` whose `to` is a household's stock: its order is the receipt's
   (`LocalFinalDemand(order_id)` of a fulfillment, `Service(order_id)` of a performance); the hours run's
   `basis` is split by `Paid[order]`; the group's `claims` are the sum of its moves' splits. A move to a household
   with no `Paid` entry is `ClaimError::UnknownOrder`. So the splits add up to back by construction, and the
   runner checks it anyway (`ClaimsNotBack`).
5. **The order of the money.** `transition.money_transfers` is followed in its own order, as the moves of money
   in the period. The check found wages paid at the period's opening, before any buying, benefits at the opening
   of the finance close, and profit shared out last; this task's first test confirms the list is in that order,
   on periods with no restart. Read from the close itself on 24 November, the list runs: delivery settlements,
   benefits, wages, household orders and their reserves, services, taxes and collections, profit, then
   equipment investment. That puts benefits before wages, where the first check had wages first: the first
   test settles it, and the purse follows the list as it is. Under the closest form's restart an owner's
   `Cash(CapitalContribution)` to the workplace it restarts comes last of all; decision 2 draws it out of the
   owner's purse, and no household's hours back change by it.
   If `an_owner_s_back_is_by_owning_from_period_two` fails because a later move is listed before an earlier one,
   stop and report: the purse would mix money that had not yet arrived.
6. **The checks, every period, in this order** after the fold: `follow` (`ClaimRefused`), `check` against
   `transition.state` (`PurseNotBook`), the split, the sum (`ClaimsNotBack`). The purses are kept with the books
   in `Stepped`, so a refusal changes nothing. **The bribe (H4) is not a check of the runner:** a group whose
   hours back for work pass its hours on the clock is a fact of the economy, not a broken sum, and the runner
   refuses only broken sums. It is not read period by period either: wages paid for one period's hours can be
   spent in a later one (a laid-off group buying with saved wages has no hours on the clock that period). The
   tests of Step 1 count it over the run so far.
7. **The three cases that arise** follow the same rule with nothing of their own: the fund's laid-off program pays
   worker households (their purse mixes wages and support); wage taxes at the close draw the mix; under the six
   rules an owner's payment into a workplace draws the mix.

- [ ] **Step 1: Write the failing tests.** In `claim/tests.rs`:
  - `a_draw_takes_floor_shares_then_the_rest_in_order`: mix `[1, 1, 0, 0]` (micro-dollars), draw 1: `[1, 0, 0, 0]`
    taken, `[0, 1, 0, 0]` left; mix `[3, 0, 5, 0]`, draw 4: floors `[1, 0, 2, 0]`, the rest 1 from `Work`:
    `[2, 0, 2, 0]` taken.
  - `a_whole_draw_takes_every_kind`: mix `[7, 0, 2, 9]` draw 18: all taken, `[0; 4]` left.
  - `a_split_of_hours_adds_up_and_skips_an_empty_kind`: 10,000,000 micro-hours by `[1, 0, 2, 0]`: work 3,333,333,
    support 6,666,667 (the rest to the last kind that holds money), owning and not recorded 0.
  - `a_reserve_keeps_its_mix_until_paid_or_refunded`: wages $10 and benefits $10 in; a reservation of $8 draws
    `[4, 0, 4, 0]` (dollars); a settlement of $6 adds `[3, 0, 3, 0]` to `Paid`; a refund of $2 returns
    `[1, 0, 1, 0]`; the purse is then `[7, 0, 7, 0]` and the reserve is gone.
  - `each_purpose_enters_as_its_kind`: one transfer of each purpose of decision 1 into an empty purse.
  - `a_tax_and_a_contribution_draw_the_mix` and `an_overdraft_is_refused` (`Overdrawn`, the purse unchanged).
  In `tests/hours.rs`:
  - `a_worker_s_and_a_supported_person_s_back_are_whole_from_period_one`: 12 quiet steps: each worker household's
    `claims.work == back_micro_hours`, every other kind 0; each supported household's `claims.support ==
    back_micro_hours`.
  - `an_owner_s_back_is_by_owning_from_period_two`: period 1, `claims.not_recorded == back_micro_hours`; from
    period 2, `claims.owning == back_micro_hours`.
  - `every_period_the_splits_add_up_and_the_purses_are_the_book_s`: the runs of Task 3's
    `every_period_keeps_both_laws_and_the_place_identity` and `every_rule_on_keeps_the_ledger_for_60_periods`:
    every step `Ok` (the runner refuses otherwise), and the four claims add up to back in every household.
  - `no_group_s_back_for_work_passes_its_clock`: the same runs: for every household keep two running sums from
    period 1, of `claims.work` and of `clock`; after every period the first is at most the second times
    1,000,000 (decision 6). If it is not, stop and report the run, the household, the period and both sums: the
    lead brings it to the Director. Do not weaken the test to make it pass.
  - `the_laid_off_program_mixes_wages_and_support`: the run of Task 3's harvest in Both until lifted, 60 periods:
    the builder finds the first period in which a worker household's `claims.support` and `claims.work` are both
    above 0 and pins it with that household's two figures; if no period has it, the test pins that none does
    over the 60 periods, and the report says so (the unit test then carries the case).
  In `src/runner/hours.rs` tests: `a_purse_that_is_not_the_book_s_is_refused` (a real period with its last
  `Cash(OwnershipDistribution)` to an owner taken out of the transfer list: profit is shared out last, so nothing
  draws on it after, and the refusal is `PurseNotBook`, not `ClaimRefused`); and the Display of each new
  `RunnerError`.
- [ ] **Step 2: Run them and see them fail:** `mise run rust:test:q -- -p babylon-recorded-labor -E 'test(claim)'`
  and `mise run rust:test:q -- -p babylon-circuit-worlds -E 'test(hours)'`. Expected: does not compile.
- [ ] **Step 3: Implement** the module, the purses in the runner's ledger, the split and the checks.
- [ ] **Step 4: Run** both crates' tests. Then add to `hours_fold_every_reference_run` the same two running sums
  for every household of every reference run, with the same assertion, and run it in the background (it now also
  meets the claims' checks in every reference run). A failure names the form, the scale, the run, the household
  and the period.
- [ ] **Run the gate:** fmt; clippy; `mise run rust:test:q -- -p babylon-recorded-labor`; `mise run rust:test:q
  -- -p babylon-persistence -E 'test(recorded_labor)'`; `mise run rust:test:q -- -p babylon-circuit-worlds`;
  `mise run rust:test:q -- -p babylon-client -E 'test(small_world)'`; sentinels. **Commit** the subject above.

### Task 5: The scene, first part: goods part full, the standing line, the words

The code as built binds: the lead reads this task again against the client after the closest form's Task 8c
(`rules.rs`, `marks.rs`, the two tabs of the rail's lower part, `PaymentKind::Capital`, the sixth money stream)
before it starts. Commit `feat(client): goods squares fill as their hours are measured`.

**Files:**
- Modify (under `rust/crates/babylon-client/src/small_world/`): `scene.rs` (the scene opens its runner with
  hours); `reading.rs` (`GoodsMove.opening`, `PeriodReading.opening_per_hundred`); `frame.rs` (a goods move as two
  flows); `controls.rs` (`GOODS_HOLLOW_LINE`'s words, the standing line, `PEOPLE_LINE_AT` becomes 5);
  `panel.rs` (`STORED_WORK_LINE` goes); `table.rs` (`NOT_MEASURED` goes); `../small_world.rs` (exports);
  `scene_tests.rs`; `script_tests.rs` (`PROOF_SH5`).

**Interfaces:**

```rust
// src/small_world/scene.rs
/// The scene's runner: the scene's world with the hours ledger. "Start over" opens it again.
/// # Errors
/// As `Runner::open_world_with_hours`.
pub fn open_runner() -> Result<Runner, RunnerError>;
// src/small_world/reading.rs, GoodsMove gains:
/// Units of the move that come from the opening stock, to the nearest whole unit (half up); `None` when the
/// period has no record of hours.
pub opening: Option<u64>,
// PeriodReading gains:
/// Of every 100 units moved this period, how many come from the opening stock, to the nearest whole number
/// (half up); `None` without a record of hours.
pub opening_per_hundred: Option<u64>,
// src/small_world/controls.rs
/// The figure of the standing line: 100.
pub const PER_HUNDRED: u64 = 100;
pub const GOODS_HOLLOW_LINE: &str =
    "A hollow part of a square: goods from the opening stock, whose hours were never measured.";
/// The standing line of ruling 18: "Of every 100 units moved this period, {n} come from the opening stock.";
/// empty without a record.
#[must_use] pub fn opening_line(per_hundred: Option<u64>) -> String;
/// The standing line's text entity.
#[derive(Component)] pub struct OpeningLine;
/// Write the standing line when the picture changes.
pub fn paint_opening_line(shown: Res<SceneShown>, scene: Res<SceneRunner>, view: Res<PanelView>,
    mut line: Query<&mut Text, With<OpeningLine>>);
/// Where the people line stands: after the five fixed lines of the key (was 4).
const PEOPLE_LINE_AT: usize = 5;
// src/small_world/script_tests.rs
/// The proof script of Task 5, one JSON command a line (Step 5); the lead runs it, never the builder.
const PROOF_SH5: &str;
```

**Decisions:**
1. **The scene asks for hours.** Its two openings (`scene.rs`, the first and "Start over") call `open_runner()`.
   Every test that goes through `scene_app` now draws goods part full. Every other test of the client that opens
   `Runner::open()` keeps a runner without hours and draws as today: the frame's pin
   `each_stream_draws_and_counts_exactly_its_own_total` (all goods hollow) stays as it is.
2. **A move's opening units** are read in `read_goods` by its receipt list and index (`MovedBy`) while the moves
   are pushed, before the empty moves are dropped and before sorting,
   from `result.hours`: `opening = (opening_micro_units + 500_000) / 1_000_000`, at most `quantity`. A move that
   has no `MoveHours` while `hours` is `Some` is `ReadingError::UnknownParty` with the move's receipt.
3. **Drawn part full, part hollow** (S10). `goods_flows` writes, for a move with `opening: Some(n)`, a full flow of
   `quantity - n` and a hollow flow of `n`, each only when above 0, same stream, same ends; with `None`, one
   hollow flow as today. So a part that rounds to no unit is drawn full. Whether a part smaller than one mark
   (`UNITS_PER_MARK`) draws is the library's own count, shown as today in the "not drawn" line; the lead judges at
   the window.
4. **The standing line** counts every move drawn (power, care and food together; calls list 16):
   `opening_per_hundred = (100 * sum(opening_micro_units) + half) / (sum(quantity) * 1_000_000)` with half equal
   to half the divisor, so 12.5 shows 13. Built in `read_period` from `result.hours.moves`. Its text entity sits
   in the standing column where `GOODS_HOLLOW_LINE` stands, right under it, built by `controls::text` like its
   neighbours; `paint_opening_line` writes it for the period the scene shows, and is registered in the plugin
   beside `controls::paint_people_line` and `panel::paint_not_drawn`. The key now has five fixed lines,
   so `PEOPLE_LINE_AT` becomes 5 (the people line still stands after the key, before the "not drawn" line).
5. **The words** (S11): `GOODS_HOLLOW_LINE` gets the new words above. `STORED_WORK_LINE` goes from the rail and
   from the code, and with it the table's `NOT_MEASURED` and its `pub use`. `TO_THE_CENT_LINE` stays.
6. **The scene's refusal** of a period the ledger refused is the runner's own (Task 3, decision 6), shown where
   every refusal of a step is shown; nothing is drawn for that period.

- [ ] **Step 1: Write the failing tests** (in `scene_tests.rs` unless named; `scene_app(None)` as built):
  - `the_scene_measures_hours`: after one step, `scene.runner.history()[0].hours` is `Some`; after "Start over" and
    one step, again.
  - `every_hollow_part_is_the_record_s` (in `frame.rs`, `open_runner()`): period 1: the food stream's hollow total
    is 120 and its full total 40 (both places: 40 to homes and 20 of the 40 farm to shop each, from the opening);
    power full 240 and hollow 0; care full 80 and hollow 0. Period 2: food hollow 60, full 100. In every period of
    12, each move's hollow flow equals its record's opening rounded as decision 2, and full plus hollow equals the
    move's quantity.
  - `the_standing_line_counts_the_opening_share`: periods 1 to 4 read "Of every 100 units moved this period, 25
    come from the opening stock.", then 13, 6 and 3; `opening_line(None)` is "".
  - `the_goods_line_says_a_hollow_part_is_opening_stock`: `GOODS_HOLLOW_LINE` on screen once with the words
    above; no text on screen contains "not measured".
  - In `the_table_switches_its_grouping_and_period`, the three lines that name the line go: the import of
    `STORED_WORK_LINE` (it shares its `use` line with `TO_THE_CENT_LINE`: take out the one name), `all.contains`
    of "Stored work got back: not measured yet." and its `assert_eq!`; in their place one assertion: no text on
    screen starts "Stored work got back". `panel.rs`'s `the_stored_work_line_is_built_from_the_not_measured_words`
    goes with the line (S11), and with it that test's `use` of `NOT_MEASURED` and the `pub use` of it in
    `small_world.rs`.
  - In `not_drawn_line_prints_the_report`: "food 8" becomes "food 4"; the rest of
    the line is unchanged (power 12, care 4). The opening's food is drawn hollow and the farm's new food full,
    each set to 95 % on its own. These are the pinned assertions this task moves.
  - In `script_tests.rs`: `the_proof_script_of_stored_hours_task_5_parses` (8 commands).
- [ ] **Step 2: Run them and see them fail:** `mise run rust:test:q -- -p babylon-client -E 'test(small_world)'`.
  Expected: does not compile, no `open_runner`.
- [ ] **Step 3: Implement** the opening, the reading, the two flows, the line and the words.
- [ ] **Step 4: Run them.** Expected: all pass; no pinned value of the client changed but those Step 1 names.
- [ ] **Step 5: The proof script for the lead** (`PROOF_SH5` in `script_tests.rs`). Hand the lead the command
  `mise exec -- cargo run -p babylon-client -- --small-world --small-world-script <folder>/proof.jsonl` (from
  `rust/`, a folder made by `mktemp -d`) and the script; do not run it: `{"step":1}`, `{"capture":"hours-1"}`,
  `{"step":1}`, `{"capture":"hours-2"}`, `{"step":2}`, `{"capture":"hours-4"}`, `{"step":8}`,
  `{"capture":"hours-12"}`. The lead's check: in `hours-1` the food squares are mostly hollow and power and care
  full, and the line reads 25; in `hours-2` it reads 13; in `hours-4` 3; in `hours-12` 0 and the squares look
  full. The sizes and the place of the line are the lead's to tune.
- [ ] **Run the companion's gate. Commit** the subject above.

### Task 6: The scene, second part: the table's switch and the details panel

The lead read this task against `panel.rs`, `inspect.rs` and `script.rs` as built on 24 November; the text below
is amended. It is read once more after Task 5, which changes the same files. Commit
`feat(client): the table's stored hours and the details of a pick`.

**Files:**
- Modify (under `rust/crates/babylon-client/src/`): `small_world/table.rs` (`HoursRow`, `HoursTable`,
  `hours_table`); `small_world/panel.rs` (`Columns`, `PanelView.columns`, `PanelButton::Columns`, the switch at
  the right end of the pager's row, the second set of columns, `TO_THE_HOUR_LINE`); `small_world/scene.rs`
  (`SceneCommand::Columns`); `small_world/inspect.rs` (the rows of hours); `small_world/script.rs`
  (`ScriptCommand::Columns`, `columns_named`); `human_numbers.rs` (`micro_hours`, `micro_hours_to_hour`);
  `money_map/rail.rs` (`labor_hours` calls `micro_hours`); `small_world/scene_tests.rs`;
  `small_world/script_tests.rs`.

**Interfaces:**

```rust
// src/small_world/table.rs
/// One row of the table's second set. `None` is a dash.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HoursRow { pub label: String, pub given: Option<u64>, pub back: Option<u128>,
    pub for_work: Option<u128>, pub by_owning: Option<u128>, pub support: Option<u128> }
/// `scale`: the largest figure of the rows shown, in micro-hours (given counted as micro-hours for the bars).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HoursTable { pub grouping: Grouping, pub period: u64, pub rows: Vec<HoursRow>, pub scale: u128 }
/// The second set of the period, grouped as the table's tabs; `None` without a record of hours. Errors:
/// `Arithmetic`; `UnknownParty` for a household or workplace the record does not hold.
pub fn hours_table(result: &PeriodResult, grouping: Grouping) -> Result<Option<HoursTable>, ReadingError>;
// src/small_world/panel.rs
/// Which set of columns the table shows.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum Columns { #[default] Money, Hours }
// PanelView gains (its hand-written `impl Default` gives `Columns::Money`):
pub columns: Columns,
// PanelButton gains:
Columns,
const HOURS_COLUMNS: [&str; 5] = ["Given", "Back", "For work", "By owning", "Support"];
/// The cells' widths of the second set, the lead's to tune.
const HOURS_CELL_WIDTHS: [f32; 5] = [40.0, 44.0, 48.0, 52.0, 48.0];
/// The switch's caption.
pub const COLUMNS_SWITCH: &str = "Hours back";
/// Under the table while the second set shows.
pub const TO_THE_HOUR_LINE: &str = "Hours in the table are rounded to the hour. Click a body for exact figures.";
// src/small_world/scene.rs, SceneCommand gains:
Columns(Columns),
// src/small_world/script.rs, ScriptCommand gains:
/// `{"columns":"money"}` or `{"columns":"hours"}`. (`Pick` is built: the closest form's Task 3d.)
Columns(String),
// src/human_numbers.rs
/// Micro-hours as an exact decimal of hours, trailing zeros dropped: 239_921_875 is "239.921875".
pub(crate) fn micro_hours(value: u128) -> String;
/// Micro-hours to the nearest whole hour, half up, grouped as `grouped` groups.
pub(crate) fn micro_hours_to_hour(value: u128) -> String;
// src/small_world/script_tests.rs
/// The proof script of this plan's Task 6 (Step 5); the lead runs it.
const PROOF_SH6: &str;
```

**Decisions:**
1. **The switch** (P6). One button, `PanelButton::Columns`, captioned `COLUMNS_SWITCH`, built by `spawn_pressed`
   as the pager's buttons are, at the right end of the pager's row: a node with `flex_grow: 1.0` stands before
   it. The rail is 400 wide; there is no room for a row of its own. A press writes `SceneCommand::Columns` with
   the other set; the stage sets `view.columns`, where it sets the tab for `SceneCommand::Lower`. `chosen` marks
   it (`panel::mark(.., true)`) while `Columns::Hours` shows: it gains the arm `(_, Some(PanelButton::Columns),
   _) => Some(view.columns == Columns::Hours)`, and `press_panel`, which matches `PanelButton` exhaustively,
   gains the button's arm. "Start over" keeps the set, as it keeps the tab.
2. **The second set** (S10): by workplace, `given` is the workplace's `given`, the other four `None`. By class and
   by place, every figure is the sum of the group's households' own (`HouseholdHours.given`,
   `back_micro_hours`, `claims.work`, `claims.owning`, `claims.support`); the shared row "Shared: treasury and
   fund" is all `None`. No column for "not recorded" (calls list 5): while it lasts the three claims add up to
   less than back, and the panel shows the rest. The first set's rows by place take their hours from the
   workplaces; this set sums households. The two agree while nobody works outside their place, and the seekers
   move within one place only. An owner's capital put into a workplace is in the money columns only.
3. **Cells.** Hours to the hour (`micro_hours_to_hour`; given with `grouped`), a dash for `None`; bars in `BONE`
   on one scale, `HoursTable.scale`. Under the table `TO_THE_HOUR_LINE` shows while the second set does, and
   `TO_THE_CENT_LINE` while the first does (the lines under the table are spawned once today: the one that
   changes with the set gets a marker component and a paint system, as the "not drawn" line has). The headers
   and widths of the first set do not change. Without a
   record (`None`) the second set shows one line, "No hours were measured for this period.", in `GRAY`.
4. **The details panel** (S10, What the player sees). Its rows of hours stand before the money rows. A household
   group, after "Hours given": "Hours back"
   (`micro_hours`), "For work", "By owning", "Support", "Not recorded", "Units from the opening stock" (its
   `opening_micro_units` as an exact decimal of units, by `micro_hours`'s writing). A workplace, after "Made":
   "Hours in a unit handed over, to the millionth" (`handed_micro_hours / handed_units`, floored to the
   micro-hour, by `micro_hours`; the row's name says it is rounded) and "From the opening stock" ("{n} of
   every 100 units", rounded as the standing line), both only when `handed_units > 0`. Hours a unit is a
   quotient of the record's two figures, so the panel also shows "Hours handed over" and "Units handed over"
   exactly. The rows stand before the rules' rows of `marks.rs`. A period without a record shows none of them.
5. **The script's command.** `columns` takes "money" or "hours" (`columns_named`, beside `lower_named`) and
   writes `SceneCommand::Columns`, as `lower` writes its own; `check_names` refuses any other name before the
   window opens. `pick` is built already (`inspect::pick_named`, the closest form's Task 3d), and
   `household_of` and `workplace_of` are `pub(super)`.
6. **Words.** The column names are the design's; "Hours back" names the switch by the figure it brings.
   `micro_hours` never rounds; a rounded figure says so (`TO_THE_HOUR_LINE`). `micro_hours` is the number part
   of `money_map/rail.rs`'s `labor_hours`, which then calls it and writes the same bytes as today (run the
   `money_map` tests).

- [ ] **Step 1: Write the failing tests** (`open_runner()` runs; place A):
  - `the_hours_table_is_the_record_s` (in `table.rs`): period 2 of the quiet world, each grouping: every `back`,
    `for_work`, `by_owning` and `support` is the sum of its households' record; by workplace the four are `None`
    and `given` is the workplace's; the shared row is all `None`; by place A, `given` 240 and `back` 200,000,000.
  - `the_second_set_has_no_column_for_not_recorded` (in `table.rs`): period 1, by class: the owners' row
    ("Owners who do not earn", both places summed) has `by_owning` 0 and `back` 64,000,000 (32 hours a place).
  - `micro_hours_are_written_exactly` (in `human_numbers.rs`): 239,921,875 is "239.921875"; 1,000,000 is "1";
    2,222,222 is "2.222222"; `micro_hours_to_hour(237_500_000)` is "238".
  - `the_switch_stands_at_the_end_of_the_pager_s_row`: the pager's row's last child is the switch; a click and two
    updates: `view.columns` is `Hours`, the switch's left border is `px(3)`, the header row reads the five names,
    `TO_THE_HOUR_LINE` is on screen and `TO_THE_CENT_LINE` is not; a second click: as before.
  - `a_household_s_panel_shows_its_hours_by_claim`: period 2, pick place A's supported household: "Hours back"
    is its record's exactly, "Support" equal to it, "For work" "0"; place A's owners in period 1: "Not recorded"
    equal to "Hours back".
  - `a_workplace_s_panel_shows_the_hours_in_a_unit`: period 1, pick place A's shop: "Hours in a unit handed over,
    to the millionth" "1", "From the opening stock" "100 of every 100 units"; utility "1", clinic "2".
  - In `script_tests.rs`: `the_script_names_columns` (`{"columns":"money"}`, `{"columns":"hours"}`, and
    `{"columns":"table"}` refused on its line) and `the_proof_script_of_stored_hours_task_6_parses` (11
    commands).
- [ ] **Step 2: Run them and see them fail** (`-E 'test(small_world) | test(human_numbers)'`). Expected: does not
  compile, no `hours_table`.
- [ ] **Step 3: Implement** the table's second set, the switch, the panel's rows and the script's commands.
- [ ] **Step 4: Run them.** Expected: all pass; no pinned value of the client changed.
- [ ] **Step 5: The proof script for the lead** (`PROOF_SH6`, as Task 5's Step 5): `{"step":2}`,
  `{"columns":"hours"}`, `{"wait_frames":30}`, `{"capture":"table-hours"}`, `{"pick":"household:22"}`,
  `{"wait_frames":30}`, `{"capture":"panel-supported"}`, `{"pick":"workplace:a:shop"}`, `{"wait_frames":30}`,
  `{"capture":"panel-shop"}`, `"quit"` (a tab or a pick is drawn some frames after its command, so each capture
  waits). The check: the switch at the right end of the
  pager's row, the five columns with dashes where decision 2 puts them, the panels' rows as decision 4.
- [ ] **Run the companion's gate. Commit** the subject above.

### Task 7: A scripted run on the real display

The code as built binds: the lead reads this task again after Task 6. The builder writes the script and the
report's figures; the lead runs it on the real display, looks at the window, compares it with the design, and
shows the Director (ADR322, H3: "show you the first window"). Commit
`feat(client): the script reports the stored hours for the lead's look`.

**Files:**
- Modify (under `rust/crates/babylon-client/src/small_world/`): `script.rs` (`ScriptReport.stored_hours`);
  `script_tests.rs` (`PROOF_SH7`); `scene_tests.rs`.

**Interfaces:**

```rust
// src/small_world/script.rs
/// The stored hours of the last period of the run (the report's `period`).
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ReportHours {
    /// The standing line's figure.
    pub opening_per_hundred: u64,
    /// Each place's label and its back, exact (`micro_hours`).
    pub back_by_place: Vec<(String, String)>,
    /// Each household group's label and its back, for work, by owning, support and not recorded, exact.
    pub households: Vec<(String, [String; 5])>,
}
// ScriptReport gains (None without a record). Its three series `hours_on_the_clock`, `hours_given` and
// `hours_idle` keep their names: "the hours" of a report are `hours_given`. It stays `PartialEq` only.
pub stored_hours: Option<ReportHours>,
// src/small_world/script_tests.rs
/// The proof script of this plan's Task 7 (decision 2); the lead runs it.
const PROOF_SH7: &str;
```

**Decisions:**
1. **What the report writes** is read from `result.hours` of the last period of the history (`build_report`
   reads the whole run, whatever period the scene shows), with `micro_hours`: the lead checks the pinned figures
   in the report's file, not by eye. A record that cannot be read is `build_report`'s `Err`, and the script
   refuses in those words.
2. **The script** (`PROOF_SH7`): `{"step":1}`, `{"capture":"stored-1"}`, `{"report":"stored-1"}`, `{"step":1}`,
   `{"report":"stored-2"}`, `{"step":10}`, `{"columns":"hours"}`, `{"wait_frames":30}`,
   `{"capture":"stored-12-table"}`, `{"pick":"household:22"}`, `{"wait_frames":30}`,
   `{"capture":"stored-12-panel"}`, `{"report":"stored-12"}`, `"quit"`. Twelve periods, as the design asks; the
   pictures are kept for the Director.
3. **The lead's check.** `stored-1.json`: `opening_per_hundred` 25; place A's back "160". `stored-2.json`: 13 and
   "200". `stored-12.json`: place A's back below "240" and above "239.9"; every worker group's for work equal to
   its back; owners all by owning. The pictures: squares filling, the standing line, the table's second set, a
   supported household's panel. The lead then looks at the window as a player would, since a review misses what a
   player sees.

- [ ] **Step 1: Write the failing tests:** `the_report_carries_the_hours_of_its_period` (in `scene_tests.rs`: script
  `{"step":2}`, `{"report":"h"}`; `h.json`'s `stored_hours.opening_per_hundred` is 13 and place A's back "200");
  `the_proof_script_of_stored_hours_task_7_parses` (14 commands, in `script_tests.rs`).
- [ ] **Step 2: Run them and see them fail** (`-E 'test(small_world)'`).
- [ ] **Step 3: Implement** the report's field.
- [ ] **Step 4: Run them.** Expected: all pass.
- [ ] **Step 5: Hand the lead** the command of Task 5's Step 5 and `PROOF_SH7`; do not run it.
- [ ] **Run the companion's gate. Commit** the subject above.

## Self-review notes

**The design's rules, each with its task.**

| Rule | What it asks | Task |
| --- | --- | --- |
| S1 | One ledger; the fold in a crate of its own; the stored records' formats, refusals and order unchanged | 1, 2 |
| S2 | A period at a time, with that period's catalog; the stored entry keeps refusing a changed catalog | 2 (entry), 3 (each period's catalog) |
| S3 | The runner folds, asked for at its opening; a refused period stops the run | 3 |
| S4 | The pooled average, unchanged | 2 (moved unchanged), 3 |
| S5 | The second run in opening units, a unit as a million, work adds none, never stored | 2 (`Carry`), 3 |
| S6 | Given is ruling 17, by the household; a good holds its recipe's hours | 3 |
| S7 | Back is what reached the household | 2 (`Handed.to`), 3 |
| S8 | By the claim: kinds, average rule, reserves, three cases, exact, no rate; the bribe against the clock, over the run | 4 |
| S9 | Hours that store nothing: not built; the place where they will enter stays | 2 (kept), none built |
| S10 | Part full and hollow; the standing line, rounded; the table's second set; the panel | 5, 6 |
| S11 | The goods line's new words; "Stored work got back" goes | 5 |

**The pinned figures, each with its test.**

| Figure | Test | Task |
| --- | --- | --- |
| Power 1, care 2 a unit from period 1; farm food 2 as made | `a_unit_holds_its_recipe_s_hours` | 3 |
| Shop food nears 3, never reached | `the_quiet_world_climbs_as_pinned` (back below 240) | 3 |
| Given: worker 10, owners and supported 0, place 240 | `the_quiet_world_climbs_as_pinned` | 3 |
| Back 240 − 80 ÷ 2^(p−1), exact through period 11 | `the_quiet_world_climbs_as_pinned` | 3 |
| Food reaching homes from the opening: 100, 50, 25, 12.5 | `the_opening_share_halves` | 3 |
| All units moved from the opening: 25, 12.5, 6.25, 3.125 | `the_opening_share_halves`; the line 25, 13, 6, 3 | 3, 5 |
| Harvest: 20/9 a unit as made | `the_failed_harvest_makes_food_of_twenty_ninths` | 3 |
| Power cut: 10/9 a unit as made | `the_power_cut_makes_power_of_ten_ninths` | 3 |
| The place's identity; both laws; direct equals given | `every_period_keeps_both_laws_and_the_place_identity` | 3 |
| Both shocks, one place and both, 60 periods | the same test | 3 |
| Given follows the household | `given_follows_the_household_that_works_elsewhere` | 3 |
| Worker all for work and supported all support from period 1 | `a_worker_s_and_a_supported_person_s_back_...` | 4 |
| Owner all by owning from period 2 | `an_owner_s_back_is_by_owning_from_period_two` | 4 |
| Splits add up; purses equal cash and reserves | `every_period_the_splits_add_up_...`; the runner's checks | 4 |
| Back for work at most the clock over the run so far, every household | `no_group_s_back_for_work_passes_its_clock`; the long test | 4 |
| Every reference run folded, no refusal, the law | `hours_fold_every_reference_run` | 3, 4 |
| The bench's reference tests step without the ledger | `a_runner_opened_without_hours_keeps_no_record`; `reproduces_` | 3 |
| The stored records' formats, refusals and order | `the_stored_forms_...`, `the_refusals_keep_their_order`; live tests | 1, 2 |
| Twelve periods by script, a picture kept | `PROOF_SH7` | 7 |
| Period 1 by group: 48, 16, 16, 16, 32, 32 (the check's figures) | `the_quiet_world_climbs_as_pinned` | 3 |

**Names agree between tasks:** the view (Task 1, public in 2); `Carry`, `Handed`, `FoldedPeriod`, `fold_period`
(2, read in 3); `PeriodHours` and its parts, `open_world_with_hours` (3, read in 4 to 7); `ClaimHours` (4, read
in 6 and 7); `open_runner`, `GoodsMove.opening` (5, read in 6); `micro_hours` (6, read in 7).

## What the reading of 24 November changed

The closest form's six rules were built between this plan's writing and its first task. One reader compared the
plan with the code twice, after that plan's Task 5c and after its Task 8c, and the lead amended Tasks 3 to 7
above from what it found. Tasks 1 and 2 needed nothing: no file they lean on had changed.

- **Task 3:** where the fold sits in `advance` and under which catalog; how `open_world_with_hours` finds its
  catalog; the exports; two tests of rules (all six at the opening; the six of `LATE` turned on in the middle of
  a run); the client's `fund_p2` named as the run of the seekers' test; the long test's count.
- **Task 4:** the order of the money as the close writes it, with an owner's capital last.
- **Task 5:** the pinned lines named by their tests; `read_goods` reads the opening share before it drops empty
  moves; where the new paint system is registered; the proof's name.
- **Task 6:** `pick` is built already and is taken out; `columns_named`; the hand-written `Default`,
  `press_panel` and `chosen`; a paint system for the line under the table; the rows of hours stand before the
  money rows; `micro_hours` shared with `labor_hours`; the proof waits before each capture and quits.
- **Task 7:** the report's field is `stored_hours`, of the last period of the run; the proof waits and quits.
- **Not checked by reading** (the tasks' own tests show them): the pinned figures; whether the fold accepts the
  seekers' path, a restart's capital and a rule turned on in the middle of a run; the order of the money inside
  the support close; whether the pager's row has room for one more button (the lead's look).
