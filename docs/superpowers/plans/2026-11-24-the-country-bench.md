# The Country Bench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** A test runner steps the real national catalog through the engine's own period, with the price of a short
market, spare money, the six adjustment rules and benefits turned on, beside a run with none. Trade routes, imports,
foreign regions and companies all run. The record shows whether the rules run at the country's size, how fast, and
what breaks.

**Architecture:** Everything is test code in the persistence crate's recorder binary, `national_household_units`,
and its `tests/support/`. The runner takes the shipped opening (`national-world-v12`) as the campaign compiler
builds it. It sets a market policy on a copy of the catalog, keeps the staffing in memory, and closes each period
with the engine's public entries, as the small worlds' runner does (`babylon-circuit-worlds/src/runner/run.rs`). It
checks money and people every period. The recorder's reader, which today reads a tick session, first learns to read
a catalog, a state and the receipts, so that the tick's recorder and the bench write records of one form. The engine
changes in one task only: work that grows with the square of the size is removed, with no admitted world changing
by one byte.

**Tech Stack:** Rust. `babylon-persistence` (tests only: `tests/national_household_units.rs`, `tests/support/`),
`babylon-material-circuit` (Task 7 only), `babylon-tick` (read, never changed).

**Spec:** the Director's ruling of 24 November, recorded in
`ai/decisions/ADR324_the_country_before_more_of_the_small_world.yaml`, and this plan's own sections "What the bench
is and is not" and "What stops the country today". Issue PER-371.

**When it is built.** Next, before more of the small world and before the bridge. After it, the country's rebuilt
opening is built, and each of its steps is counted on this bench.

## The Director's ruling

24 November 2026, question dialog. The option picked:

> "First a country bench, 5 to 7 tasks: a test runner steps the real national catalog on the engine's own period,
> with the price rule, the six rules and benefits on, beside a run with none. Trade routes, imports, foreign regions
> and companies all run. It shows whether the rules run at the country's size, how fast, and what breaks."

The lead's sizing found seven tasks. This plan has eight, because the sizes are read first (Task 1) and the work
that grows with the square of the size is a task of its own (Task 7).

## What the bench is and is not

**It is** the engine's own period, run on the whole country: 187 places with households, every foreign region and
dependency, about 7,463 workplaces, companies' treasuries and payouts, shared freight corridors, imports, public
bodies, the household lifecycle. It is the same catalog and opening state the game opens with
(`economic_catalog/foundation.rs:165` compiles the opening the same way).

**It leaves out four things of the game's own turn.** Each record says so on its first lines:
1. The companies' portfolio choice is off. In the game it is a governed draw in the graph (`replay_session.rs:918`,
   `company_portfolio_bridge.rs:72`). Without it the engine refuses from period 2 (`portfolio/execution.rs:43-48`).
   So the bench sets the catalog's `company_portfolios` to `None`. Company payouts stay.
2. No City PD attendance. Its agency inputs come only from a selected City PD intent (`material_replay.rs:120`).
3. No County Review period (`material_world/county_review_execution.rs`).
4. No register checks. The tick's register validates and encodes every family (`register.rs:2023-2128`). The
   bench runs only the engine's own checks.

The organizer's aid and collections are empty in the bench, as they are in the tick recorder, which makes no
commitment.

**So every run is judged against the bench's own baseline**, the same 34 periods with no rule on. It is never
judged against the record of 20 November (`reports/economy-repair-2026-11-20/`), which went through the tick.

**What is on.** The price of a short market (a market policy with the paying order of the products), spare money
(rule A6), the six adjustment rules, and benefits. For benefits, the national fund and its two programs are added
to the opening in memory, as the benefits plan's "Later plan B" items 1 to 5 describe
(`docs/superpowers/plans/2026-11-20-opening-stage-4-benefits.md:674-692`).

**What is off.** Comforts and luxuries (tiers and wants). Their lists would be invented figures until the baskets
of stage 5 exist.

**What these first runs can tell.** The shipped opening collapses from causes the rules were not built to cure:
- recipes that need a quarter of the workforce, with 110 million laid off in period 2;
- households with no earner and no income;
- one wage of $24 at every job;
- a fixed basket.

These causes are listed in `docs/superpowers/specs/2026-11-20-the-opening-of-the-national-economy-design.md`,
section 3. One cause the market policy does touch: orders stuck behind a full route are cancelled and refunded
(price plan Task 5). So these runs tell four things: whether the rules run at the country's size, how fast, what
breaks, and what they do to that collapse. They do not tell whether a balanced country holds. That is the rebuilt
opening's work, counted on this same bench.

## What stops the country today

Read from `957e09d18`, on 24 November. These walls stand in the game's own turn, through the tick. The bench goes
around them. They are kept here as the record of why it must.

| # | Wall | Where | What it guards |
|---|---|---|---|
| W1 | Every campaign catalog is compiled with `market_clearing: None`; the policy has no key for one | `babylon-persistence/src/economic_catalog/compile.rs:76` | No campaign can ask for any rule |
| W2 | The register refuses public programs and their extension | `babylon-tick/src/material_world/register.rs:1874-1876` | Stored records without programs |
| W3 | The register refuses market rows | `register.rs:1900-1902` | Same, for the market's receipt |
| W4 | The register refuses want and tier rows | `register.rs:1905-1907` | Same, for tiers |
| W5 | Adjustment receipts are never encoded: dropped, not refused | `register.rs:2132` (no field) | Nothing; a gap |
| W6 | The tick's close refuses the stop rule; the close with standing takes no support inputs | `babylon-material-circuit/src/transition/state.rs:1877-1879`, `1895-1909` | The stop rule's memory |
| W7 | The restart refuses without the stop rule's memory and the bound | `state.rs:2065-2070` | The restart |
| W8 | `WorkplaceStanding` is the caller's; the tick keeps none | `adjustment/standing.rs:5-6` | Stop and restart across periods |
| W9 | The tick staffs on graph nodes and finishes with `finish_with_workforce`, which does not check for seekers | `babylon-tick/src/material_replay.rs:338-358` | Staffing by place (silently not done) |
| W10 | `finish_with_workforce` refuses an after-layoff program | `state.rs:798`, `970-978` | The record of layoffs |
| W11 | Seekers need one member for each household at each workplace of its place; the opening has members only where residents were assigned | `national_resident_allocation/allocation.rs:398-441`; `staffing/place.rs:268-273` | Seekers, and so stop and restart |
| W12 | The restart's money has no contribution receipt, and the tick refuses unexplained contributions | `babylon-tick/src/material_world/financial_receipt.rs:324-333` | Money explained once |
| W13 | A resting price is written `Hold` whatever the cost; the tick refuses `Hold` under cost pressure | `recurring_receipt.rs:161`; `recurring/prices.rs:258-266` | Price receipts (likely, not proven) |
| W14 | A session pins one catalog digest: no rule can be turned on mid-run | `material_replay.rs:616-618` | Replay identity |
| W15 | The County Review refuses an account holding a program | `material_world/county_review.rs:293` | The review's figures |

What the tiny world cannot show. These are the features of the national catalog that the small world's catalog
(`babylon-circuit-worlds/src/doubled/catalog.rs:260-290`) does not have at all:
- routes with shared corridors and stages, and imports from foreign regions and dependencies;
- companies with many workplaces, their treasuries and payouts;
- more than one employer of one trade in a place, and several members of one household in one pool;
- bands of households, public bodies in every place, aid mandates, household time, equipment, rolling capacity;
- the household lifecycle, with births, deaths and the workforce's attrition;
- one wage everywhere (so the seekers' "highest wage first" falls to its tie-breaks).

## Global Constraints

- Work only in `/media/user/dev-ssd/worktrees/households-homes/babylon`, branch `codex/households-and-homes`.
  Start every shell command with `cd` to it (or to its `rust/`). Never push. No `.env`, no `uv.lock`.
- One cargo, mise or test process at a time on the whole machine. Never pass `-j`. Only `mise exec -- cargo ...`
  and `mise run ...`. A build in another checkout empties this one's cache: launch long tests with `--no-build`
  after a build when the lead says another checkout is building.
- A command that may run longer than ten minutes runs in the background. Its output goes to a log file in your
  scratch directory, and the command line ends with `; echo "END <name> status=$?" >> <log>`. Wait for the end
  marker; never poll the log in a loop.
- **Where code goes.** All new code is under `rust/crates/babylon-persistence/tests/`: the binary
  `national_household_units.rs` and files under `tests/support/` that it names with `#[path = "support/..."]`. No
  change to the campaign compiler, to `babylon-tick`, or to `babylon-persistence/src`.
- **The engine.** No file under `rust/crates/babylon-material-circuit/src` changes, except in Task 7. There, no
  admitted world may change by one byte: every engine test, the small worlds' tests and the fourteen long
  `reproduces_` tests stay as they are.
- **No new API.** If a task needs a public function, field or accessor that does not exist, the builder stops and
  reports. It does not widen an API on its own.
- **A refusal is a finding.** If the engine refuses a period, the builder writes down the period, the refusal and
  the receipts of the period before it, and reports. It mends nothing in the engine and changes no figure of the
  opening to get past it.
- **Figures are sums.** A share is two sums divided, in basis points. Nothing is averaged. Money is `i128`
  millionths of a dollar (`Currency`). Quantities and persons are `u64`. Arithmetic is checked; a failure is a
  typed error (`BenchError::Arithmetic`), never a wrap.
- Functions under 100 lines and a cognitive complexity of 25 (`rust/clippy.toml`). No `unwrap`. An `expect` in a
  test carries its reason in its message. An `allow` attribute carries a `reason`. No `bool` parameter. No
  `mod.rs`. Import a type and use its bare name (the sentinels refuse a module-qualified type used inline). Every
  line number is a hint; find each place by its text.
- **Records** are written only by ignored tests, into `reports/country-bench-2026-11-24/`, with
  `write_compact` (`national_household_units.rs:587`). A record of 34 periods must stay under 1 MiB, as that
  function asserts. The one exception is the whole record of a 400-period run, which is not committed (Task 8,
  decision 4).
- **Gates.** Each task lists its legs. Run them one at a time: `mise exec -- cargo ...` from the checkout's
  `rust/`, and `mise run ...` from the checkout's root.
  - fmt: `mise exec -- cargo fmt --all -- --check`
  - clippy: `mise exec -- cargo clippy --workspace --all-targets --locked -- -D warnings -D
    clippy::cognitive_complexity`
  - the recorder's binary: `mise run rust:test:q -- -p babylon-persistence -E 'binary(national_household_units)'`
  - a named ignored test: `mise run rust:test:q -- -p babylon-persistence -E
    'binary(national_household_units) & test(<name>)' --run-ignored only`
  - sentinels: `mise run check:bsl-sentinels`
  - Task 7 adds: `mise run rust:test:q -- -p babylon-material-circuit`; `mise run rust:test:q -- -p
    babylon-circuit-worlds`; and in the background `mise run rust:test:q -- -p babylon-material-circuit --test
    adjustment_bench -E 'test(/^reproduces_/)' --run-ignored only`.
  - The live database tests are the lead's. No task runs them.
- Commit: `git add <files>`; the message in a file; `PYTHONPATH=src mise exec -- git commit -q -F <file>`; then
  check `git log --oneline -1` (a hook can abort silently). Subjects in the repository's form, a scope with no
  space. The body ends with `Part of PER-371` and a `Co-Authored-By` line naming the model that wrote the commit.

## Review Focus

1. **The reader drifts while it moves.** Moving the reader off the session could change a figure with no test
   failing, since no test pins a record. Pinned by Task 2's `the_reader_writes_the_same_record_for_three_periods`,
   written and seen passing before anything moves, and run again at the end of Task 2.
2. **The bench is not the game's opening.** The bench could compile an opening that differs from the one a session
   opens with, and then measure another economy. Pinned by Task 3's `the_bench_opens_on_the_session_s_state`: the
   bench's opening state digest equals the session's (`material_circuit_state_digest`).
3. **A rule is on and does nothing.** A rule can be admitted and never act at the country's figures. A run would
   still look like a run with the rule. Shown by the `rules` column of every period (Task 4) and by the
   `"acted"` lists of every record (Task 8): the periods in which each rule acted. Task 4's
   `the_rule_columns_add_back` pins the columns' arithmetic only; it passes when every rule does nothing.
4. **People leak in the seekers' moves or in attrition.** The household lifecycle changes persons every period, so
   a check that holds persons constant would fail falsely, and a check that skips them would miss a leak. Pinned
   by the runner's own check, every period of every run: closing persons equal opening persons plus births less
   deaths, and the labor force falls by exactly the attrition (Task 3, `BenchError::PersonsNotExplained`). Task 3's
   `the_three_checks_refuse_a_difference_of_one` sees each check refuse. Task 5's
   `the_seekers_rows_keep_every_person` pins the opening.
5. **The fund prints money.** Adding the fund could add cash to the economy. Pinned by Task 6's
   `the_fund_keeps_the_opening_s_money`: total money is equal before and after the fund is added, and each payer's
   tax rate is the sum of its two rows.

## File Structure

| File | What it holds | Tasks |
| --- | --- | --- |
| `rust/crates/babylon-persistence/tests/support/country_sizes.rs` | The country's sizes, read from a compiled opening | 1, 5 |
| `rust/crates/babylon-persistence/tests/support/economy_health.rs` | The reader, off the session; the new columns | 2, 4 |
| `rust/crates/babylon-persistence/tests/support/country_bench.rs` | The runner: open, step, checks, errors | 3, 4, 5 |
| `rust/crates/babylon-persistence/tests/support/country_rules.rs` | The rule sets and the market policy | 4 |
| `rust/crates/babylon-persistence/tests/support/country_seekers.rs` | The seekers' member rows in memory | 5 |
| `rust/crates/babylon-persistence/tests/support/country_fund.rs` | The fund, the split taxes and the two programs | 6 |
| `rust/crates/babylon-persistence/tests/national_household_units.rs` | The tests and the ignored recorders | 1-6, 8 |
| `rust/crates/babylon-material-circuit/src/{recurring/prices.rs, clearing/table.rs, adjustment/*.rs, recurring/spare_money.rs, staffing/place.rs}` | The squares removed | 7 |
| `rust/crates/babylon-material-circuit/tests/...` (found in Task 7, Step 1) | The size tests | 7 |
| `reports/country-bench-2026-11-24/*.json`, `*.log` | The records and logs, handed to the lead | 3, 8 |

Each support file is named once in `national_household_units.rs` with `#[path = "support/<file>.rs"] mod <file>;`,
like the three already there (`national_household_units.rs:23-28`).

---

## The tasks

### Task 1: The country's sizes

Commit `test(persistence): pin the national opening's sizes and the seekers' rows`.

**Files:**
- Create: `rust/crates/babylon-persistence/tests/support/country_sizes.rs`.
- Modify: `rust/crates/babylon-persistence/tests/national_household_units.rs` (the module line, one test).

**Interfaces:**

```rust
// consumes: CapturedEconomicCatalog::capture_national_campaign(national_catalog_input(), campaign())
//   and .opening(): &EconomicOpening (national_household_units.rs:80-88); EconomicOpening::compile()
//   (economic_catalog/compile.rs:46), whose CompiledEconomicOpening has pub catalog, state, staffing.
// tests/support/country_sizes.rs
/// One place: an `EconomicLocation` that some site or household account has.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct PlaceKey(pub EconomicLocation);
/// The sizes of one place.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct PlaceSizes {
    pub workplaces: u64,      // sites located here
    pub pools: u64,           // staffing pools whose site is here
    pub households: u64,      // distinct household ids among the members of those pools
    pub members: u64,         // existing members of those pools
    pub seeker_rows: u64,     // households x pools
    pub new_rows: u64,        // seeker_rows less the (pool, household) pairs that already have a member
}
/// The sizes of the whole opening.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CountrySizes {
    pub places_with_households: u64,          // domestic County places with a household account
    pub workplaces_by_scope: BTreeMap<&'static str, u64>,  // "domestic", "foreign", "dependency"
    pub household_accounts_by_scope: BTreeMap<&'static str, u64>,
    pub pools: u64,
    pub members: u64,
    pub employment_terms: u64,
    pub member_labor_rows: u64,
    pub offers_goods: u64,
    pub offers_services: u64,
    pub market_rows_at_most: u64,             // 2 x offers_goods + offers_services
    pub members_outside_their_place: u64,     // members whose residence is not their pool's site's place
    pub seeker_rows: u64,                     // sum over places
    pub members_with_seekers: u64,            // members + sum of new_rows
    pub by_place: BTreeMap<PlaceKey, PlaceSizes>,
}
pub fn country_sizes(opening: &EconomicOpening, compiled: &CompiledEconomicOpening) -> CountrySizes;
/// The bound the seekers must fit: the smaller of `MAX_STAFFING_MEMBERS` and the contract's
/// `employment_and_member_labor_rows` (131,072, `contracts/material_circuit_v4.yaml:708`).
pub const SEEKER_BOUND: u64 = 131_072;
```

**Decisions:**
1. **A place** is the `EconomicLocation` of a site (`EconomicSiteSeed.location`, `economic_catalog/model.rs:140`).
   A pool's place is its site's place. A place's households are the distinct `household_id()` of the members of its
   pools. This is what `staff_in_places` needs: a host takes a person only into its own member of the same household
   (`staffing/place.rs:268-273`).
2. **The pools and members** are read from `opening.staffing` (`Vec<ResidentStaffingPoolSeed>`): `pool.site_id()`,
   and each member's `member.household_id()` and `member.residence()`.
3. **Scope** is read as the recorder reads it, with `economy_health::scope` of the location's string
   (`economy_health.rs:82`). Make `scope` `pub` if it is not. It is test support, so that is not an API change.
4. **Offers** are `opening.policies.offers`, split by the commodity's kind (`CommodityKind::Storable` against
   `PeriodService`, from `opening.commodities`).
5. **What is pinned.** Every field of `CountrySizes` but `by_place`. The builder runs the test once with the
   literals empty, copies what the failure prints, and commits the values. A value is never edited after that.
6. **If the seekers do not fit.** If `members_with_seekers > SEEKER_BOUND`, the test still pins the figures. The
   builder stops after the commit and reports `members_with_seekers` and the twenty places with the most `new_rows`.
   Raising the engine's limit and narrowing where people may look are not this plan's to decide. Tasks 2, 3, 4, 6
   and 7 can still be built; Task 5 and set (iii) wait for the lead, and Task 6 then builds the fund on the set
   without seekers (its own first lines say how).
7. **Members outside their place.** If `members_outside_their_place > 0`, report the count. Decision 1 still holds:
   such a member's household counts in its pool's place.

- [ ] **Step 1: Write the test** `the_country_s_sizes` in `national_household_units.rs`. It compiles the shipped
  opening once, calls `country_sizes`, and prints the struct with `{:#?}`. It prints the twenty places with the
  most `new_rows`, sorted by `new_rows` from the most, then by place. It asserts each pinned field
  (`assert_eq!`), and it asserts `sizes.workplaces_by_scope.values().sum::<u64>() ==
  u64::try_from(opening.sites.len())`. It asserts `seeker_rows == by_place.values().map(|p| p.seeker_rows).sum()`.
  It does not assert that the seekers fit.
- [ ] **Step 2: Run it** with the literals empty:
  `mise run rust:test:q -- -p babylon-persistence -E 'binary(national_household_units) & test(the_country_s_sizes)'`.
  It fails and prints the sizes. Fill in the literals and run it again. Expected: it passes.
- [ ] **Step 3: Report** the printed sizes to the lead in the hand-off, with `members_with_seekers` against
  `SEEKER_BOUND` (decision 6). Compare them with the estimates of the sizing: 7,463 workplaces (7,283 domestic, 120
  foreign, 60 dependency), and 187 places with households.
- [ ] **Step 4: Gate:** fmt; clippy; the recorder's binary; sentinels. **Commit** the subject above.

**What this task must not do:** change the opening, add a member, or decide anything about the seekers. It only
counts.

### Task 2: The reader reads a state, not a session

Commit `refactor(persistence): the economy health reader reads a catalog and a state`.

**Files:**
- Modify: `rust/crates/babylon-persistence/tests/support/economy_health.rs`;
  `rust/crates/babylon-persistence/tests/national_household_units.rs` (the callers, one new test).

**Interfaces:**

```rust
// economy_health.rs, after this task (every `&Session` parameter of the reader is gone):
pub fn economy(state: &MaterialCircuitState) -> &MonetaryCircuit;
fn corridor_available(catalog: &MaterialCatalog, state: &MaterialCircuitState, period: u64,
    corridor: CorridorId) -> u64;
impl Opening { pub fn read(census: &Census, catalog: &MaterialCatalog, state: &MaterialCircuitState) -> Self; }
pub fn money_record(census: &Census, after: &MaterialCircuitState) -> Value;
pub fn period_record(census: &Census, open: &Opening, receipts: &MaterialTickReceipts,
    catalog: &MaterialCatalog, after: &MaterialCircuitState) -> Value;
pub fn session_counts(census: &Census, state: &MaterialCircuitState) -> Counts;
// businesses(..) and trade(..) take `after: &MaterialCircuitState` (and `catalog` where they read it).
// The tick recorder passes `session.catalog()` and `session.material().state()`.
```

**Decisions:**
1. **The guard first.** No test pins a health record today. So this task writes the guard before it changes
   anything, sees it pass, and sees it pass again at the end.
2. **What is pinned:** the lowercase hex of `sha256_of(&serde_json::to_vec(&health_report("shipped", &[], 3))?)`,
   using `babylon_kernel::content_digest::sha256_of`. That is the shipped campaign, three periods through the tick,
   exactly as `record_national_economy_health` makes its record (`national_household_units.rs:549-585`). The
   builder runs the test once with the literal empty and copies what the failure prints.
3. The guard is `#[ignore]` (three national periods through the tick, a minute or more). Its reason says so.
4. Only the reader's inputs change. No figure, key or order of the JSON changes. Remove `economy_health`'s
   `Session` alias once no reader takes it: no other file uses it (`household_accounts.rs` and `supply_chain.rs`
   have their own), and left unused it fails clippy as dead code.

- [ ] **Step 1: Write the guard** `the_reader_writes_the_same_record_for_three_periods` (decision 2), with
  `#[ignore = "three national periods through the tick; run by Task 2's gate"]`.
- [ ] **Step 2: Run it** on the code as it stands. It fails once, printing the digest. Fill the literal in and run
  it again: `mise run rust:test:q -- -p babylon-persistence -E 'binary(national_household_units) &
  test(the_reader_writes_the_same_record_for_three_periods)' --run-ignored only`. Expected: it passes.
- [ ] **Step 3: Change the reader** to the interfaces above, and its callers in `national_household_units.rs`
  (`health_report`, `the_health_reader_adds_back_at_the_opening`).
- [ ] **Step 4: Run** the guard again (Step 2's command) and the binary's default tests. Expected: both pass, and
  the digest is unchanged.
- [ ] **Step 5: Gate:** fmt; clippy; the recorder's binary; the guard; sentinels. **Commit** the subject above.

**What this task must not do:** add a column, change a figure, or touch the tick.

### Task 3: The bench with no rules, and its baseline

Commit `test(persistence): a country bench that closes the national opening on the engine's own period`.

**Files:**
- Create: `rust/crates/babylon-persistence/tests/support/country_bench.rs`.
- Modify: `rust/crates/babylon-persistence/tests/national_household_units.rs` (three tests, one ignored recorder).
- Create (by the recorder): `reports/country-bench-2026-11-24/baseline.json`.

**Interfaces:**

```rust
// consumes, from the engine (lib.rs re-exports): close_material_period, close_material_period_with_standing,
//   ClosedMaterialPeriod::{staffing_requests, household_lifecycle, staff_in_places, finish_with_staffing,
//   finish_with_place_staffing}, advance_staffing, distribute_staffing_members, reconcile_resident_workforce,
//   material_circuit_state_digest, StaffingState::try_new, StaffingPoolState::try_new,
//   StaffingMemberState::try_new, StaffingMemberBinding::with_living_force, StaffingPoolBinding::with_living_force,
//   MaterialCatalog::{into_definition, try_new}, MonetaryBook::total_cash_and_reserves.
// tests/support/country_bench.rs
/// Which rules the bench turns on. Tasks 4 to 6 add variants; this task has `None` alone.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RuleSet { None }
impl RuleSet {
    /// The set's name in a record's head and in its file's name. `None` is "baseline".
    pub const fn name(self) -> &'static str;
}
/// The three checks of decision 5, each a difference refused.
pub fn check_money(period: u64, opening: i128, closing: i128) -> Result<(), BenchError>;
pub fn check_persons(period: u64, before: u64, births: u64, deaths: u64, after: u64) -> Result<(), BenchError>;
pub fn check_labor_force(period: u64, before: u64, removed: u64, after: u64) -> Result<(), BenchError>;
/// A stage of one period, for an error.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum BenchStage { Open, Close, Attrition, StaffingRequests, AdvanceStaffing, Distribute, StaffInPlaces,
    Finish, Read }
#[derive(Debug)]
pub enum BenchError {
    Opening(EconomicCatalogError),
    Engine { period: u64, stage: BenchStage, error: MaterialCircuitError },
    Staffing { period: u64, stage: BenchStage, error: StaffingError },
    Place { period: u64, error: PlaceStaffingError },
    MoneyNotConserved { period: u64, opening: i128, closing: i128 },
    PersonsNotExplained { period: u64, expected: u64, closing: u64 },
    LaborForceNotExplained { period: u64, expected: u64, closing: u64 },
    Arithmetic { period: u64 },
}
/// What one period hands back.
pub struct BenchPeriod {
    pub period: u64,
    pub receipts: MaterialTickReceipts,        // built from the transition, decision 6
    pub market_clearings: Vec<MarketClearingReceipt>,
    pub adjustments: Vec<AdjustmentReceipt>,
    pub public_programs: Vec<PublicProgramReceipt>,
    pub closing_members: Vec<PoolMembers>,
    pub elapsed: Duration,                     // the step alone, `Instant` around it
}
pub struct CountryBench { /* catalog, state, staffing: StaffingState, members: Vec<PoolMembers>,
    places: Vec<StaffingPlace>, standing: WorkplaceStanding, set: RuleSet, opening_money: i128 */ }
impl CountryBench {
    /// # Errors
    /// `BenchError::Opening` when the opening does not compile; `Engine { stage: Open, .. }` when the catalog
    /// with portfolios off is refused.
    pub fn open(opening: &EconomicOpening, set: RuleSet) -> Result<Self, BenchError>;
    pub fn catalog(&self) -> &MaterialCatalog;
    pub fn state(&self) -> &MaterialCircuitState;
    /// Close one period. A refusal leaves the bench as it was.
    /// # Errors
    /// The period's refusal, typed by stage; the checks of decision 5.
    pub fn step(&mut self) -> Result<BenchPeriod, BenchError>;
}
/// The record's first lines (decision 8).
pub fn bench_header(set: RuleSet) -> Value;
```

**Decisions:**
1. **The opening.** `opening.compile()` gives the catalog, the state and the staffing. The catalog is rebuilt with
   `catalog.into_definition()`, `company_portfolios = None` and `MaterialCatalog::try_new`. If `try_new` refuses,
   or the first period refuses with a portfolio error, stop and report: the bench cannot leave the choice out. Do
   not set a fixed portfolio in its place.
2. **The staffing, in memory.** For each `ResidentStaffingPoolSeed` of `opening.staffing`, in order:
   `StaffingPoolState::try_new(seed.pool.clone(), sum of employed, sum of reserve, seed.previous_unretained_hours)`,
   and the members `StaffingMemberState::try_new(member.member.clone(), member.employed, member.reserve)`. Then
   `StaffingState::try_new(1, pools)`. The pools and members come in the order of the seeds. `places` is one
   `StaffingPlace` per place (Task 1, decision 1), places in `EconomicLocation` order, pools in site order. It is
   built here but read only when seekers are on (Task 5).
3. **One period, with no seekers**, in the tick's order (`material_replay.rs:300-374`,
   `material_staffing/composition.rs:537-596`):
   1. `close_material_period(&catalog, &state)`. When the set asks for `StopWithoutPay`, it is
      `close_material_period_with_standing(&catalog, &state, &standing)` instead (Task 5).
   2. **Attrition.** If `closed.household_lifecycle()` is not empty, the bench calls
      `reconcile_resident_workforce(lifecycle, &members)`, where `members` is one flat
      `&[(StaffingPoolId, StaffingMemberState)]` over all pools, built as the tick builds it
      (`composition.rs:603-612`) and bounded at `MAX_STAFFING_MEMBERS` in total
      (`household_lifecycle/workforce.rs:35-39`). It applies the changes as the tick's
      `apply_resident_attrition` does (`composition.rs:598-666`). Each changed member gets
      `binding.with_living_force(working + waiting)` and a new state. Each pool gets
      `binding.with_living_force(employed + reserve)` and a new `StaffingPoolState` with the same
      `previous_unretained_hours`. The state is rebuilt with `StaffingState::try_new(period, pools)`. Copy the
      logic; do not call into `babylon-tick` (it is `pub(crate)` there).
   3. `closed.staffing_requests(&catalog, &bindings)`, with the bindings of the state after attrition.
   4. `advance_staffing(&staffing, &requests)`. For each receipt, `distribute_staffing_members(receipt, &members)`
      for its pool. The next member state of each row is `StaffingMemberState::try_new(row.member.clone(),
      row.closing_employed, row.closing_reserve)`. The next member labor rows are `MemberLaborCapacityRow {
      member_id, period: row.period + 1, available_hours: row.next_opening_hours }`, sorted by `(period,
      member_id)`. The next labor is `transition.next_labor()`.
   5. `closed.finish_with_staffing(&catalog, next_labor, member_labor, &member_receipts)`. With no after-layoff
      program it equals `finish_with_workforce` (`state.rs:806-810`), and with one it ages the record of layoffs.
   6. Then `transition.staffing_members = member_receipts` and `transition.resident_workforce_attrition =
      attrition`, as the tick sets them (`material_replay.rs:358-361`).
4. The bench keeps the transition's `state`, the next staffing, the members and (Task 5) the standing. A refusal
   at any stage returns the error and changes nothing.
5. **The checks, every period:**
   - Money: `total_cash_and_reserves()` of the closing book equals the opening's, else `MoneyNotConserved`. It
     returns `Result<Currency, MonetaryError>` (`accounts.rs:438`); its error is `BenchError::Arithmetic`.
   - Persons: the cohorts' persons after equal those before, plus the sum of `births`, less the sum of
     `deaths.persons()` over the period's lifecycle receipts. Else `PersonsNotExplained`. The national opening has
     a household lifecycle (`content/scenarios/national/defines.toml:431`), so persons are not constant.
   - Labor force: the pools' labor force after attrition equals that before, less the sum of `employed_removed +
     reserve_removed` of the attrition rows. After staffing it is unchanged. Else `LaborForceNotExplained`.
   - `step` makes each check by calling `check_money`, `check_persons` and `check_labor_force`, and by nothing
     else, so that the test of the three functions is a test of the bench's checks.
6. **The receipts.** `MaterialTickReceipts` has public fields (`register.rs:2132-2178`). The bench fills each from
   the transition field of the same name. It sets `agency_paid` to empty, `resolve_tick` to the period, and
   `maintenance` to `transition.maintenance`. `market_clearings`, `adjustments` and `public_programs`, which
   `MaterialTickReceipts` does not have, go into `BenchPeriod`.
7. **Time.** `elapsed` is the step alone, not the opening's compile.
8. **The record's head.** `bench_header(set)` gives `{"bench": "country-bench-2026-11-24", "set": <name>,
   "leaves_out": [<the four sentences of "What the bench is and is not", items 1 to 4>], "judged_against":
   "the bench's own baseline (baseline.json), never the record of 20 November"}`. The recorder writes these keys
   before `periods`.

- [ ] **Step 1: Write the tests** in `national_household_units.rs`:
  - `the_bench_opens_on_the_session_s_state`: `material_circuit_state_digest(session.catalog(), bench.state())`
    equals `material_circuit_state_digest(session.catalog(), session.material().state())` for a session opened as
    `opened_session` does. Both states are digested under the session's catalog: the digest covers the catalog's
    own digest (`wire/state.rs:542-558`), and the bench's catalog differs from the session's by its portfolios
    setting. The test's doc says so.
  - `one_bench_period_conserves_money_and_persons`: `RuleSet::None`, one `step()`, which returns `Ok`. Its
    `receipts.resolve_tick == 1`. The closing money equals the opening's. Its `staffing_members` is not empty.
    Print `elapsed`.
  - `the_three_checks_refuse_a_difference_of_one`: each of `check_money`, `check_persons` and
    `check_labor_force` returns `Ok` when its two sides are equal, and its own error (`MoneyNotConserved`,
    `PersonsNotExplained`, `LaborForceNotExplained`, each with the period given) when one side is one more and
    when it is one less. For persons: before 100, births 3, deaths 2, after 101 is `Ok`; after 100 and after 102
    are refused.
- [ ] **Step 2: Run them:** `mise run rust:test:q -- -p babylon-persistence -E 'binary(national_household_units) &
  test(bench)'`. Expected: they fail to compile, then fail, before the runner exists.
- [ ] **Step 3: Implement** `country_bench.rs` (decisions 1 to 8).
- [ ] **Step 4: Run** Step 2's command. Expected: all pass. Write the period's `elapsed` in the hand-off.
- [ ] **Step 5: The baseline.** Write the ignored recorder `record_country_bench_baseline` with
  `#[ignore = "writes reports/country-bench-2026-11-24/baseline.json"]`. It opens the census as `health_report`
  does, opens `CountryBench` with `RuleSet::None`, and steps 34 periods. For each period it reads `Opening::read`
  before the step and `period_record` after it. It writes `bench_header`, `"columns"`, `"panel"` and `"periods"`
  with `write_compact`. Each period's row also has `"elapsed_ms"`. Run it in the background (Global Constraints).
  Expected: 34 rows, no refusal, the money total of every row equal. If the engine refuses, see the Global
  Constraints: report the period, the refusal and the period before.
- [ ] **Step 6: Gate:** fmt; clippy; the recorder's binary; sentinels. **Commit** the subject above with
  `baseline.json`.

**What this task must not do:** turn any rule on, edit the opening, or compare with the record of 20 November.

### Task 4: The market policy, the rules without seekers, and the rule columns

Commit `test(persistence): the bench turns on the market price and the rules that need no seekers`.

**Files:**
- Create: `rust/crates/babylon-persistence/tests/support/country_rules.rs`.
- Modify: `tests/support/country_bench.rs` (`RuleSet` gains variants; `open` sets the policy);
  `tests/support/economy_health.rs` (the new columns); `tests/national_household_units.rs` (tests, the timing
  recorder).

**Interfaces:**

```rust
// country_bench.rs
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RuleSet {
    None,
    /// (i) The price of a short market alone.
    Market,
    /// (ii) The market, spare money, the bound on hiring, the resting price and the step-down.
    NoSeekers,
    // Task 5: AllSix. Task 6: the set with benefits.
}
// `RuleSet::name` (Task 3) gains "market" and "no-seekers".
// country_rules.rs
/// The seven products in the order a buyer's purse reaches them (price plan Task 8, decision 1).
pub const PAYING_ORDER: [&str; 7] = ["food", "materials", "utility", "housing", "household_services",
    "business_services", "resources"];
/// The policy of a set, or `None` for the baseline. Labels are `CommodityLabel.key`.
pub fn market_policy(opening: &EconomicOpening, set: RuleSet) -> Result<Option<MarketClearingPolicy>, BenchError>;
/// The adjustment rules of a set, in the order of `AdjustmentRule`.
pub fn rules_of(set: RuleSet) -> Vec<AdjustmentRule>;
// economy_health.rs
/// What the bench has beside `MaterialTickReceipts`.
pub struct BenchReceipts<'a> {
    pub market_clearings: &'a [MarketClearingReceipt],
    pub adjustments: &'a [AdjustmentReceipt],
    pub public_programs: &'a [PublicProgramReceipt],
    pub closing_members: &'a [PoolMembers],
    /// Production policies whose planned batches after the close exceed the period's plan receipt.
    pub spare_money_raised: u64,
}
pub fn markets_record(census: &Census, bench: &BenchReceipts<'_>) -> Value;
pub fn rules_record(bench: &BenchReceipts<'_>) -> Value;
pub fn jobs_after_moves(census: &Census, closing_members: &[PoolMembers], staffing: &StaffingState) -> Value;
```

**Decisions:**
1. **The policy.** `paying_order` is `PAYING_ORDER` mapped through `opening.commodity_labels` (`key` to `(good_id,
   unit_id)`). A missing label is `BenchError::Opening`. `household_wants` is empty. `plans_from_spare_money` is
   `true` for `NoSeekers` and later sets, `false` for `Market`. `adjustments` is `rules_of(set)`.
2. **`rules_of`:** `None` and `Market` get no rules. `NoSeekers` gets `[HiringWithinMeans, RestingPrice,
   GoodsStepDown]`. The stop rule is not in this set: it needs `SeekingInPlace` (`adjustment/policy.rs:31`,
   `NEEDS_STOP`), and the standing it keeps comes only from `staff_in_places` (`state.rs:844-895`). It moves to
   set (iii), Task 5.
3. The policy is set on the definition beside `company_portfolios = None` (Task 3, decision 1), and the catalog is
   admitted with `try_new`. A refusal is `Engine { stage: Open, .. }`: report it, do not change the order.
4. **`markets_record`**, by product label and by the seller's scope: `[short_markets, demand_at_quote,
   sold_quantity, highest clearing price, the quote of that row, county or region of that row]`. A market row is a
   short market (`clearing/table.rs` `into_receipts` keeps only rows with a receipt). The highest is a maximum, not
   an average. Add its legend to `columns()` as `"market": [...]`.
5. **`rules_record`**, counts of the period:
   - `hiring_bound`: `[rows, rows with bound_hours < asked_hours, sum of asked_hours - bound_hours]`;
   - `moves`: `[rows, persons]`;
   - `stops`: `[rows, rows with could_not_pay, rows held]`;
   - `resting_prices`: rows; `resting_to_cost`: rows;
   - `restarts`: `[rows Restarted, rows Failed, rows NoBuyer, sum of money]`; `owner_spare`: rows;
   - `goods_offers`: `[rows, rows with planned_gain > 0]`;
   - `spare_money_raised`;
   - `programs`: `[rows, sum of paid, sum of unfunded]`.

   Read the exact field names from `adjustment/receipts.rs` and `financial/model.rs` (`PublicProgramReceipt`).
   Every key is present in every period, with zeros when nothing acted.
6. **`spare_money_raised`.** Rule A6 writes no receipt (`recurring/spare_money.rs:498-499`). The bench counts the
   production policies of the closing state whose `planned_batches` exceeds the `planned_batches` of the period's
   `ProductionPlanReceipt` for the same process. It uses one map by process, not a scan.
7. **`jobs_after_moves`**, by scope of the pool's site: `[at_work, looking]`, summed over the closing members'
   `employed()` and `reserve()`. With no seekers it equals the record's `jobs` at the close; Task 4's test checks
   that.
8. **The recorder's row** for a bench period adds `"markets"`, `"rules"` and `"jobs_after_moves"` to
   `period_record`'s object, and `"elapsed_ms"`. The tick's records are unchanged (Task 2's guard).

- [ ] **Step 1: Write the tests:**
  - `a_market_policy_names_every_storable_need`: for `RuleSet::Market`, `market_policy` returns `Some` with seven
    products, and the catalog admits it.
  - `the_rule_columns_add_back`: one period of `NoSeekers`. The `rules` column's `hiring_bound[0]` equals the
    count of `AdjustmentReceipt::HiringBound` rows in `BenchPeriod.adjustments`, and the same for every kind. The
    `market` column's short markets summed over products equal `market_clearings.len()`. `jobs_after_moves`
    equals the `jobs` column's close.
  - `one_period_of_each_set_without_seekers_closes`: `Market` and `NoSeekers` each step one period with `Ok`, the
    money conserved.
- [ ] **Step 2: Run them** (`-E 'binary(national_household_units) & test(/market|rule|without_seekers/)'`).
  Expected: they fail before the code exists.
- [ ] **Step 3: Implement** decisions 1 to 8.
- [ ] **Step 4: Run** Step 2's command. Expected: all pass.
- [ ] **Step 5: The timing.** Write the ignored recorder `record_country_bench_timings`, with
  `#[ignore = "writes reports/country-bench-2026-11-24/timings.json"]`. For each set built so far, in the order of
  `RuleSet`, it opens a bench, steps one period, and writes `{"set", "elapsed_ms", "ratio_to_baseline_bps"}`. The
  ratio is `elapsed of the set x 10_000 / elapsed of the baseline`. It also prints the table. Run it.
- [ ] **Step 6: Report** the timings in the hand-off. A set whose ratio passes 100,000 (ten times) is named. Its
  34-period run waits for Task 7 (Calls of the lead, 5).
- [ ] **Step 7: Gate:** fmt; clippy; the recorder's binary; Task 2's guard; sentinels. **Commit** the subject above
  with `timings.json`.

**What this task must not do:** run 34 periods of a set with rules (that is Task 8), add wants, or turn on a rule
that needs seekers.

### Task 5: The seekers' member rows, and all six rules

Commit `test(persistence): the bench gives every household a member at each workplace of its place`.

**Built only if Task 1 found that the seekers fit** (`members_with_seekers <= SEEKER_BOUND`). If they do not fit,
this task waits for the lead's word. Set (iii) waits with it, and Task 6 builds the fund on the set without
seekers instead.

**Files:**
- Create: `rust/crates/babylon-persistence/tests/support/country_seekers.rs`.
- Modify: `tests/support/country_bench.rs` (`RuleSet::AllSix`; the seekers' path of `step`; the standing);
  `tests/support/country_rules.rs`; `tests/national_household_units.rs`.

**Interfaces:**

```rust
// country_seekers.rs
/// The id of the member a household holds at a pool it has none at: the first 32 bytes of
/// `sha256_of(b"CountryBenchSeekerMemberV1\0" ++ pool_id bytes ++ household_id bytes)`.
pub fn seeker_member_id(pool: StaffingPoolId, household: FinalDemandPrincipalId) -> StaffingMemberId;
/// What the opening gains: for each place, each household of the place at each pool of the place where it has no
/// member, one member of nobody, one `EmploymentTerms` and one 0-hour `MemberLaborCapacityRow` of period 1.
pub struct SeekerRows {
    pub members: Vec<(StaffingPoolId, StaffingMemberState)>,
    pub terms: Vec<EmploymentTerms>,
    pub hours: Vec<MemberLaborCapacityRow>,
}
pub fn seeker_rows(opening: &EconomicOpening, places: &[StaffingPlace]) -> Result<SeekerRows, BenchError>;
// country_bench.rs
pub enum RuleSet { None, Market, NoSeekers, /// (iii) all six, with spare money.
    AllSix }
```

**Decisions:**
1. **The new members.** Each has the binding `StaffingMemberBinding::from_living_force(seeker_member_id(pool,
   household), household, residence, 0)`. Its residence is the residence of that household's first existing
   member in member order. Its state is `StaffingMemberState::try_new(binding, 0, 0)`. It goes after the pool's
   existing members, new members sorted by household id.
2. **Their terms.** `EmploymentTerms { member_id, site_id: pool's site, unit_id: pool's unit, payee: household,
   compensation }`. The compensation is `LaborCompensation::Wage` of the highest wage among the pool's existing
   wage terms. A pool with no wage term pays its new members the policy's default wage, $24 an hour: 24,000,000
   micros (`national_household_units.rs:539-546` reads it). Check whether the engine admits a working owner or
   unpaid family member moving into a wage member of the same household: it moves "persons of a household", and the
   compensation is the host member's. Report it either way.
3. **Where they go.** The members join the bench's `PoolMembers`, and the pool's binding is unchanged (they hold
   nobody). The terms are merged into `MonetaryCircuit.employment` and the hours into `member_labor`, both kept in
   the order the engine admits. Read that order from `payments/attendance.rs` and `state.rs`'s validation, and
   check it with `encode_material_circuit_state(&catalog, &state)` once.
4. **`rules_of(AllSix)`:** `[HiringWithinMeans, SeekingInPlace, StopWithoutPay, RestingPrice, OwnerRestart {
   outlay_periods: 2 }, GoodsStepDown]`. The restart puts in two periods of a batch's cost, the closest form's
   figure for the national scale (`docs/superpowers/plans/2026-11-23-adjust-2-the-closest-form.md:759`).
   `plans_from_spare_money` is `true`.
5. **The seekers' path of a period:** close with standing (`close_material_period_with_standing(&catalog, &state,
   &standing)`); attrition (Task 3, decision 3.2, over every member, the new ones included); then
   `closed.staff_in_places(&catalog, &staffing, &members, &places)` and
   `closed.finish_with_place_staffing(&catalog, &placed)`. The bench keeps `placed.state`, `placed.members` and
   `placed.standing`. It sets `transition.staffing_members = placed.member_receipts`. These are the engine's
   decision before any move (`staffing/place.rs:43-44`), so `jobs_after_moves` is the true count after them.
6. The standing opens as `WorkplaceStanding::opening()`.
7. The persons check is Task 3's. The moves change no household's persons, and the labor-force check holds over
   all pools.

- [ ] **Step 1: Write the tests:**
  - `every_pool_has_a_member_for_each_household_of_its_place`: after `seeker_rows`, for every place, every pool
    holds a member of every household of the place. The total members equal Task 1's pinned
    `members_with_seekers`.
  - `the_seekers_rows_keep_every_person`: the opening's persons, labor force and money are unchanged by the rows.
    The state with the rows encodes (`encode_material_circuit_state` returns `Ok`).
  - `one_period_with_all_six_rules_closes`: `AllSix` steps one period with `Ok`. Print the count of
    `AdjustmentReceipt::PlaceMove` rows and of `Stop` rows.
- [ ] **Step 2: Run them** (`-E 'binary(national_household_units) & test(/seeker|all_six|every_pool/)'`).
  Expected: they fail first.
- [ ] **Step 3: Implement** decisions 1 to 7.
- [ ] **Step 4: Run** Step 2's command. Expected: all pass. If the engine refuses the first period, that is a
  finding (Global Constraints): report it, and do not change a rule or a row to get past it.
- [ ] **Step 5: Time it.** Add `AllSix` to `record_country_bench_timings` and run it. Report its ratio.
- [ ] **Step 6: Gate:** fmt; clippy; the recorder's binary; sentinels. **Commit** the subject above with
  `timings.json`.

**What this task must not do:** raise `MAX_STAFFING_MEMBERS`, leave a household out of a place, or add a member as
a graph node.

### Task 6: The fund and its two programs, in memory

Commit `test(persistence): the bench adds the national fund and its two programs to the opening`.

**Files:**
- Create: `rust/crates/babylon-persistence/tests/support/country_fund.rs`.
- Modify: `tests/support/country_bench.rs` (the set with benefits; `open` edits the opening before it
  compiles); `tests/national_household_units.rs`.

**Which set it builds.** Look for `RuleSet::AllSix` in `tests/support/country_bench.rs` when this task starts.
- It is there (Task 5 was built): build `RuleSet::AllSixWithBenefits`, named `"all-six-with-benefits"`. Its twin
  without the fund is `AllSix`.
- It is not there (Task 5 waits): build `RuleSet::NoSeekersWithBenefits`, named `"no-seekers-with-benefits"`. Its
  twin without the fund is `NoSeekers`.

Below, "the set with benefits" is the one of the two that is built, and "its twin" is the set it stands beside.

**Interfaces:**

```rust
// country_fund.rs
/// The fund's account: `PublicAccountId::from_bytes` of the first 32 bytes of
/// `sha256_of(b"CountryBenchNationalFundV1\0")`.
pub fn fund_account() -> PublicAccountId;
/// The program keys.
pub const NO_EARNER: &str = "no_earner";
pub const LAID_OFF: &str = "laid_off";
/// Where the fund sits: Washington, District of Columbia (county 11001).
pub fn fund_location() -> Result<EconomicLocation, BenchError>;
/// The opening with the fund (plan B items 1 to 5).
/// `per_person` is the `no_earner` amount (decision 5).
pub fn with_fund(opening: &EconomicOpening, per_person: Currency) -> Result<EconomicOpening, BenchError>;
/// The `no_earner` amount: decision 5, read from the baseline's first period.
pub fn no_earner_per_person(opening: &EconomicOpening, first: &BenchPeriod) -> Result<Currency, BenchError>;
// country_bench.rs: `RuleSet` gains ONE variant, by "Which set it builds" above:
//   AllSixWithBenefits       (iv) all six with benefits, or
//   NoSeekersWithBenefits    the rules without seekers, with benefits.
```

**Decisions.** Plan B items 1 to 5 (`opening-stage-4-benefits.md:674-692`), on the shipped opening:
1. **The fund.** One public account, `fund_account()`, with `InstitutionLocation { account: Public(fund),
   location: fund_location() }`. Its budget is `PublicBudget { period_cap: 0, cash_floor: 0, rule:
   CashInProportion }`. Foreign regions and dependencies hold no program.
2. **The split.** Each tax row of `opening.institutions.taxes` whose payer's location is a domestic county becomes
   two rows: the place's body at `rate_bps - rate_bps / 2`, and the fund at `rate_bps / 2` (integer division).
   Both have the row's `cash_floor`. A payer's two rates sum to its old rate. Rows with a rate of 0 or 1 keep one
   row (no 0-rate fund row). The rows are sorted by `(payer, basis, public_recipient)`. The count must stay under
   `MAX_TAX_POLICIES` (262,144); print it.
3. **The places' bodies** keep their capped budgets, allocations and rows: provision, relief list, City PD.
4. **The programs**, both `rank: 0`, `payer: fund_account()`, sorted by key:
   - `no_earner`: `PerPerson { amount_per_person: per_person }`. Its recipients are every domestic household
     account whose principal is the household of no member of `opening.staffing`. This covers collective
     residences with no job. Sort them.
   - `laid_off`: `AfterLayoff { wage_share_bps: 5_000, half_periods: 13 }`. Its recipients are every domestic
     household account whose principal is the household of a member. Sort them.
   - So an account whose members are all looking for work at the opening has no earner and is on `laid_off`'s
     list only. It is paid neither benefit at the opening and keeps the county's support, as the design's call 16
     has it (Calls of the lead, 15). Count such accounts and their persons at the opening.
5. **The `no_earner` amount.** "At the opening's prices, for the needs of tier 1." This is one national figure
   and two sums divided. Over the domestic accounts in the baseline's first period, take the sum of
   `required_quantity x unit_price` of their `HouseholdDemandReceipt` rows (the need; `requested_quantity` adds the
   pantry's refill and is not used), and of `requested_quantity x unit_price` of the `ServicePerformanceReceipt`
   rows whose `buyer` is `AccountId::Household` of one of those accounts (`HouseholdServiceReceipt` has no price,
   `services/model.rs:59-84`). Divide it by the sum of those accounts' persons at the opening, rounding down. It
   is a stand-in figure of the bench: the rebuilt opening's builder will set the real one.
6. **No one is covered at the opening:** no layoff record (`layoffs` stays empty).
7. **The fund's opening cash** is two periods of its payments: `2 x per_person x` the persons of the `no_earner`
   recipients. It is moved from the domestic places' public bodies' `institutional_cash`, each giving
   `floor(its cash x fund cash / their total cash)`. The remainder comes from the body with the most cash. No money
   is made: the opening's total is unchanged. If the bodies hold less than the fund needs, stop and report.
8. **The order of opening.** For the set with benefits, `CountryBench::open` first opens a baseline bench, steps
   one period to read decision 5, then builds `with_fund(opening, per_person)`, compiles it, and opens on it as
   its twin opens: with the seekers (Task 5) and `rules_of(AllSix)` for `AllSixWithBenefits`; with
   `rules_of(NoSeekers)` and no seekers for `NoSeekersWithBenefits`. A period finishes as its twin's does:
   `finish_with_place_staffing` with the seekers, `finish_with_staffing` without. `finish_with_staffing` accepts
   an after-layoff program (`transition/state.rs:815-829`); `finish_with_workforce` refuses one. The amount is
   printed and written in the record's head as `"no_earner_per_person_micros"`.
9. If the engine refuses the fund's location, the split or the programs at compile, stop and report the refusal.
   Do not choose another location.

- [ ] **Step 1: Write the tests:**
  - `the_fund_keeps_the_opening_s_money`: the sum of `institutional_cash` and of every seed's cash is equal before
    and after `with_fund`. The fund's cash equals decision 7's figure.
  - `the_split_taxes_keep_each_rate`: for every payer and basis, the rates of its rows after the split sum to its
    rate before.
  - `every_domestic_account_is_in_one_program`: each domestic household account is a recipient of exactly one of
    the two programs.
  - `one_period_with_benefits_closes`: the set with benefits steps one period with `Ok`. Its `public_programs`
    rows, if any, have `paid <= due`.
- [ ] **Step 2: Run them** (`-E 'binary(national_household_units) & test(/fund|split|program|benefits/)'`).
  Expected: they fail first.
- [ ] **Step 3: Implement** decisions 1 to 9.
- [ ] **Step 4: Run** Step 2's command. Expected: all pass.
- [ ] **Step 5: Time it.** Add the set to `record_country_bench_timings` and run it. Report its ratio, the
  `no_earner` amount, and decision 4's count: the accounts whose members are all looking for work at the opening,
  and their persons.
- [ ] **Step 6: Gate:** fmt; clippy; the recorder's binary; sentinels. **Commit** the subject above with
  `timings.json`.

**What this task must not do:** pay anyone at the opening, give a foreign region a program, or make money.

### Task 7: The engine without squares

Commit `perf(material-circuit): the rules' reads at the size of the country, without squares`.

**When.** It is built before Task 8 when any set's one-period ratio in `timings.json` passes ten times the
baseline's (100,000 bps). If none does, the builder reports the ratios, and the lead decides whether to build it
before the 400-period runs (Calls of the lead, 5).

**Files** (each found by its text):
- `rust/crates/babylon-material-circuit/src/recurring/prices.rs` (`update_prices`: `resting_among` with
  `markets.offered`, and `goods_unsold`, `goods_offered_sold`, `goods_gain_at` for each offer);
- `src/clearing/table.rs` (`offered`, `goods_rows`);
- `src/adjustment/rest.rs` (`made_hours`);
- `src/adjustment/restart.rs` (the `production.iter().find`, `replenishment`, `household_purchases` and `seated`
  lookups for each site);
- `src/recurring/spare_money.rs` (`extend`, `site_outlay`, `paid_for`, `raise_merchant`);
- `src/adjustment/bound.rs` (`reckon_makers`, `made`);
- `src/staffing/place.rs` (`place_pools` for each host, `fill`, `take`, `pools_decided`'s `find`, `slots_of`'s
  record `find`);
- tests: found in Step 1.

**Interfaces:** none new outside the crate. Each change keeps every function's signature, and every receipt and
its order. The new indices are `BTreeMap`s built once per close (or per call where the call is once a close),
beside the rows they index.

**Decisions:**
1. **Only these.** Each item scans one long list for every row of another, and both are long at the country's size
   (sizing, answer 4). No other function changes, and no figure changes.
2. **Bytes.** No admitted world changes by one byte. The fourteen `reproduces_` sets, every engine test and the
   small worlds' tests pass unchanged. A change that moves a byte is wrong: revert it and report. Those tests run
   the doubled world, where one row matches each key. The code this task rewrites works on many matching rows at
   the country's shape (many sellers of a good, many pools of a place), and no existing test runs the national
   catalog under a rule. So the bench itself is pinned before anything changes (Step 2b).
3. **The order.** Where a scan returned the first match in row order, the map keeps the first match in row order
   (insert only when absent).
4. **The size tests** guard against a square coming back. They do not time anything; their docs say so.

- [ ] **Step 1: Write the size tests' own builders.** The fixtures at hand cannot reach these sizes: both take
  `u8` ids (`tests/market_clearing/support.rs:22`, `site(id: u8)`; `src/staffing/place.rs`'s tests,
  `site(pool: u8)` and `household(h: u8)`). Write the smallest builder in each test file itself, with ids made
  from a `u32`.
- [ ] **Step 2: Write the size tests,** in the style of `2026-11-21-review-loose-ends.md`, Task 4:
  - `a_market_of_many_sellers_closes_with_the_step_down_and_the_rest` (in `tests/market_clearing/`): 20,000 sellers
    of one good, each offering, under a market policy with `RestingPrice` and `GoodsStepDown`. One period closes.
    There are 20,000 price receipts, and the money is conserved.
  - `many_pools_of_one_place_staff_in_place` (in `staffing/place.rs`'s tests): 2,000 pools in one place, 20
    households, a need at every pool. `staff_places` returns `Ok`, and every person is kept (`assert_kept`).
  - Run each once on the code as it stands, and write its time in the hand-off.
- [ ] **Step 2b: Pin the bench.** Write `the_bench_digests_before_the_squares` in `national_household_units.rs`,
  `#[ignore = "two national periods of every set; run by Task 7's gate"]`. For the baseline and each set that
  exists when this task is built, it opens the bench, steps two periods, and asserts
  `material_circuit_state_digest(bench.catalog(), bench.state())` and the second period's `adjustments.len()` and
  `market_clearings.len()` against literals. Run it once with the literals empty and fill them in from what the
  failure prints. Two periods are enough, and this task may be built before any 34-period run of a slow set
  (Calls of the lead, 5).
- [ ] **Step 3: Implement** decisions 1 to 3, one file at a time. After each file, run
  `mise run rust:test:q -- -p babylon-material-circuit`.
- [ ] **Step 4: Run** the size tests again and write their times. Run `the_bench_digests_before_the_squares`
  again: every digest and count is unchanged. Then run the engine's crate, the small worlds' crate, and the long
  `reproduces_` tests in the background (Global Constraints). Expected: all pass, unchanged.
- [ ] **Step 5: Time the sets again:** run `record_country_bench_timings`. Report the ratios before and after.
- [ ] **Step 6: Gate:** fmt; clippy; the engine's crate; the small worlds' crate; the `reproduces_` tests; the
  recorder's binary; `the_bench_digests_before_the_squares`; sentinels. **Commit** the subject above with
  `timings.json`.

**What this task must not do:** change a receipt, a figure, an order of rows, a bound or a public signature, or
touch any rule's logic.

### Task 8: The runs, and the hand-over

Commit `test(persistence): the country bench's runs of 34 and 400 periods`.

**Files:**
- Modify: `rust/crates/babylon-persistence/tests/national_household_units.rs` (two ignored recorders).
- Create (by the recorders): `reports/country-bench-2026-11-24/<set>.json` for the baseline and every set built
  (`<set>` is `RuleSet::name`), `long-baseline-summary.json`, `long-<the set with benefits>-summary.json`, and the
  logs `*.log`.

**Interfaces:**

```rust
/// Runs one set for `periods` and returns its record (head, columns, panel, periods) and its refusal, if any.
fn bench_report(set: RuleSet, periods: u64) -> (Value, Option<BenchError>);
/// For each kind of the `rules` column, the periods in which it was not zero.
fn acted(record: &Value) -> Value;
```

**Decisions:**
1. **The sets.** `COUNTRY_BENCH_SET` names one set (`RuleSet::name`). Without it, the recorder runs the baseline
   and every set built, one after the other. Each run writes its own file. The baseline is written again here
   (`baseline.json`, replacing Task 3's), so that it has Task 4's columns and this task's head, and every set
   stands beside a baseline of its own form.
2. **A refusal is written, not thrown.** The record keeps the periods that closed. It adds
   `"refused": {"period", "error": format!("{error:?}")}` and the full row of the period before it. The builder
   reports it.
3. **`"acted"`** is written at the head of every record: for each kind of the `rules` column, the list of periods
   in which its first count was not zero. A rule that is on and never acted shows an empty list.
4. **The long runs.** `record_country_bench_long` runs 400 periods for the baseline and for the set with benefits
   (Task 6). A 400-period record would pass 1 MiB. So the full record goes under `CARGO_TARGET_TMPDIR`'s
   `country-bench/` and is not committed. It is written by a copy of `write_compact` without the size assertion
   (`write_compact_unbounded`, test code): `write_compact` writes the file and then asserts its size
   (`national_household_units.rs:587-608`), so it would panic after the first long run and lose the second. Only
   the committed summary goes through `write_compact`. The summary keeps the head, `"acted"`, the total time, and
   the rows of periods 1, 2, 3, 4, 5, 13, 34, 100, 200 and 400.
5. **Time.** Every record's head has `"total_ms"` and the slowest period with its `elapsed_ms`.

- [ ] **Step 1: Re-time** with `record_country_bench_timings`. If a set's ratio still passes ten times and Task 7
  was not built, stop and report: the lead decides.
- [ ] **Step 2: Write** `record_country_bench_sets` with `#[ignore = "writes the sets' records under
  reports/country-bench-2026-11-24/"]`, and `record_country_bench_long` with `#[ignore = "400 periods; writes
  summaries under reports/country-bench-2026-11-24/"]`.
- [ ] **Step 3: Run** `record_country_bench_sets` in the background, one log for each set
  (`COUNTRY_BENCH_SET=<name>`), one after the other. Expected: five records of 34 periods (`baseline`, `market`,
  `no-seekers`, `all-six`, `all-six-with-benefits`), or four if Task 5 waits (`baseline`, `market`, `no-seekers`,
  `no-seekers-with-benefits`).
- [ ] **Step 4: Run** `record_country_bench_long` in the background with a log. Note its total time.
- [ ] **Step 5: Hand over** to the lead: the record files, the logs, `timings.json`, every refusal (period, error,
  the row before), each set's `"acted"`, and the total times. Do not write the README. The lead writes
  `reports/country-bench-2026-11-24/README.md` and its conclusions, with figures as sums and shares as two sums
  divided, as the record of 20 November does.
- [ ] **Step 6: Gate:** fmt; clippy; the recorder's binary; sentinels. **Commit** the subject above with the
  records, the summaries and the logs.

**What this task must not do:** write conclusions, rerun a refused set with a change, or compare with the record
of 20 November.

## Calls of the lead

1. Around the tick, test-only: the runner and everything it needs live under
   `rust/crates/babylon-persistence/tests/`. No change to the campaign compiler, to `babylon-tick`, or to
   `babylon-persistence/src`. The engine changes only in Task 7, with no admitted world changing by one byte. A
   missing public accessor stops the builder.
2. In: the price of a short market, spare money, the six adjustment rules, and benefits (plan B items 1 to 5, in
   memory). Out: comforts and luxuries (tiers and wants), whose lists would be invented figures until stage 5.
3. The country's sizes come first (Task 1). If the seekers' member rows do not fit, the builder stops and reports
   the count by place.
4. The reader before the runner, proven by the tick recorder's first three periods writing the same JSON. Then the
   runner with no rules. Every run is judged against the bench's own baseline.
5. One period is timed before any long run. The squares task (Task 7) comes before the 34-period runs of any set
   whose one period takes more than ten times the baseline's, with a size test first.
6. The sets, each beside the baseline: (i) the market price; (ii) with spare money and the rules that need no
   seekers; (iii) all six; (iv) all six with benefits. Each record says whether each rule ever acted. 34 periods
   for every set; 400 for the baseline and the set with benefits, in the background. A refusal is a finding.
7. The recorder's new columns: market rows, adjustment rows by rule, jobs after the moves.
8. The record goes in `reports/country-bench-2026-11-24/`. Its README is the lead's.
9. "What the bench is and is not" says what the first runs can and cannot tell.
10. *(Mine.)* **The stop rule moves from set (ii) to set (iii).** The code does not allow it without the seekers:
    `StopWithoutPay` needs `SeekingInPlace` (`adjustment/policy.rs:31`), and the standing comes only from
    `staff_in_places`. Set (ii) is the market, spare money, the bound, the resting price and the step-down.
11. *(Mine.)* **Persons are checked against the household lifecycle, not held constant.** The national opening has
    births and deaths. The check is: persons after equal persons before, plus births, less deaths. The labor force
    falls by exactly the attrition.
12. *(Mine.)* **The portfolio choice is turned off in the catalog** (`company_portfolios = None`), not replaced by
    a fixed choice. If the engine refuses that, the builder stops.
13. *(Mine.)* **The reader takes one more argument** for the bench's columns: `BenchReceipts`. `MaterialTickReceipts`
    has no market, adjustment or program family.
14. *(Mine.)* **The seekers' new members:** their ids, their place (a site's location), a place's households (the
    households of its pools' members), and their pay (the pool's highest wage, else the $24 default).
15. *(Mine.)* **The fund's figures**, which stage 5 will set and the Director may change:
    - it sits at county 11001;
    - it takes half of each domestic tax rate, rounded down, so no payer's total rate changes;
    - `no_earner` pays the baseline's first-period spend on needs per domestic person;
    - `no_earner` recipients are the domestic accounts with no member, and `laid_off` recipients those with one.
      So an account whose members are all looking for work at the opening is paid neither benefit at the opening;
      it keeps the county's support (the design's call 16). Task 6 counts such accounts and their persons;
    - its two periods of reserve are moved from the places' bodies in proportion to their cash, so no money is made.
16. *(Mine.)* The restart puts in two periods of a batch's cost (the closest form's national figure).
17. *(Mine.)* Every set without seekers finishes with `finish_with_staffing`. It equals the tick's
    `finish_with_workforce` when there is no after-layoff program.
18. *(Mine.)* The 400-period records are kept whole only under the cargo target. Only their summaries are
    committed, because a full record passes the 1 MiB bound of `write_compact`.
19. *(Mine.)* The paying order is the seven products of the price plan's Task 8.
20. *(Mine.)* If no set's period passes ten times the baseline's, building Task 7 before the 400-period runs is the
    lead's choice.
21. *(The lead's, after the check.)* **Benefits are counted even if the seekers do not fit.** Task 6 then builds
    the fund on the set without seekers (`no-seekers-with-benefits`), beside set (ii), and the 400-period run is
    of that set.
22. *(The lead's, after the check.)* **The `no_earner` amount counts the need,** `required_quantity`, not the
    pantry's refill. It is a stand-in of the bench, like every figure of call 15.

## Self-review notes

**Coverage.** Each item of the ruling has a task:
- the real national catalog: Tasks 1 and 3;
- the engine's own period, with money and people checked: Task 3;
- the price rule and spare money: Task 4;
- the six rules: Tasks 4 and 5;
- benefits: Task 6;
- beside a run with none: Task 3's baseline and every record's head;
- at the country's size, how fast: Tasks 1, 4 to 7, and 8's times;
- what breaks: the refusals of Task 8 and the `"acted"` lists.

Each of the five Review Focus items is pinned by a named test in its task.

**What is not built.**
- The tick, the register, the stored records and the client: the bridge.
- Tiers and wants.
- The rebuilt opening (stages 1, 2 and 5).
- The seekers, if Task 1 finds that they do not fit.
- The portfolio choice, City PD attendance and the County Review inside the bench.
- The README's conclusions.

**How we know it works.**
- The reader's record of the tick is unchanged (Task 2's guard).
- The bench opens on the session's own state (Task 3).
- Every period of every run conserves money and explains every person and worker, or it stops with a typed error.
- Each rule's receipts are counted in every period, so a rule that never acted is seen.
- The engine's squares are removed with every admitted byte kept: the fourteen `reproduces_` sets, the engine's
  and the small worlds' tests.

**Unknowns, each made the first step of its task.**
- Whether the seekers fit (Task 1).
- Whether the catalog admits portfolios off (Task 3, decision 1).
- Whether the bench's opening digest equals the session's (Task 3, Step 1).
- Whether a working owner may move into a wage member (Task 5, decision 2).
- The fields that give the `no_earner` amount (Task 6, decision 5).
- Whether the engine admits the fund's location (Task 6, decision 9).
- Which fixture can be made large (Task 7, Step 1).

## What the one check changed

A second reader checked this plan once against the code at `a74aa54d0`, before any task was built. The lead folded
its findings in. Four would have stopped a builder or built the wrong thing:

- **Task 6, the `no_earner` amount.** The plan read a requested quantity and a price from the household service
  rows, which have neither, so its own stop would always have fired. It now reads the need from
  `HouseholdDemandReceipt` and the services from `ServicePerformanceReceipt`.
- **Task 6 needed Task 5** while Task 1 said it did not. Task 6 now builds the fund on all six rules if the
  seekers were built, and on the set without seekers if they wait (call 21). Task 8 counts its records to match.
- **Task 8, the 400-period record** went through `write_compact`, which asserts 1 MiB after it writes. The whole
  record now goes through a copy without the assertion, under the cargo target; only the summary is committed.
- **Task 7, the bytes.** The tests it ran never run the national catalog under a rule, and the squares live
  where many rows match one key. The bench's own digests are now pinned before the squares change (Step 2b).

Smaller changes: the filter of Task 5's tests; `RuleSet::name` from Task 3 on; the bench's opening compared with
the session's under one catalog; the three checks of a period as functions, each seen refusing a difference of
one; the reader's unused alias removed; what the columns' test does not pin; the baseline written again in the
sets' form; the flat list the attrition takes; who is paid neither benefit at the opening, said and counted; the
size tests' own builders; one form of `--run-ignored`; where each kind of command runs.

**Not checked by reading.** Each is shown by the task named:
- Whether a national period on the engine's entries, without the tick, conserves money and explains every person:
  Task 3, its first step and its 34 periods.
- The counts behind `SEEKER_BOUND`: Task 1.
- Whether the domestic public bodies hold enough cash for the fund's two periods: Task 6, decision 7, which stops
  if they do not.
- Whether a 34-period record with the new columns stays under 1 MiB: Task 8, Step 3 (`write_compact` asserts it).
- Whether `kind = "utility"` compiles to a period service, and so which of Task 6's two sums it falls in: Task 6,
  Step 3; report it.
- Whether the hiring bound or the fund's attendance do anything unexpected with members of no hours: Task 5,
  Step 4.
- The line anchors of the table of walls. They are hints and steer no build.
