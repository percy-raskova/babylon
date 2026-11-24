# The Pay Fight, Part One Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** In a small world that asks for the pay fight, the people of a workplace stop work over their pay, the
place's people who look for work take the struck hours or leave them, and the owners give way or hold out. Each
decides from its own accounts. The scene shows every step. Then the later slump is run with the fight on and no
organization, and counted.

**Architecture:** The engine learns five material acts as orders of one period: a rate that changes at a
boundary, hours withheld, withheld hours filled above the rolls, named people taken on with a floor on the rolls,
and payments to and from a fund. It checks them, applies them and answers with receipts. It decides none and
keeps nothing of an order after its period. Everything that decides lives in a new module tree of the small
worlds crate, as the scene's stand-in for the participation and founding resolvers of the August design: the
measures, each household's weighings, the employer's rule, the order inside a period, the news. The scene reads
that record: a Fight tab with its switch, a workplace's rate, the people at the gate, struck work and who takes
it, the news, the stoppage and both counts. A world that does not ask keeps every byte.

**Tech Stack:** Rust: `babylon-material-circuit` (the engine, and the bench in its tests),
`babylon-circuit-worlds` (the small worlds and their runner), `babylon-client` (the scene, Bevy).

**Spec:** `docs/superpowers/specs/2026-11-24-the-pay-fight-design.md` (rules PF1 to PF18, "The order inside a
period", calls 1 to 47, the build order of sixteen items); `ai/decisions/ADR323_the_pay_fight.yaml` (F1 to F14).
Issue PER-371.

**When it is built.** After stored hours (`docs/superpowers/plans/2026-11-23-stored-hours-in-the-small-world.md`,
Tasks 2 to 7) and before the bridge (ADR323, F10). The tasks were written against commit 98a0e3624, where stored
hours' Task 1 is built and its Tasks 2 to 7 are not. Line numbers are those of that commit and are hints: find
each place by its text. Where the code differs from a line number, the code binds. Where it differs from an
interface, stop and report. The lead reads the plan against the built stored-hours code once before Task 1 starts;
the last section says what that reading changed.

**Two parts.** This plan is Part One: the design's build-order items 1 to 7, each with its piece of the scene. It
ends with a counted run on the bench (Task 9). The lead reads that count with the Director before Part Two (items
8 to 16) is detailed. The design says why: "If won rises do not end the slump on today's engine, the rows go to
the Director before anything else is built on it." Part Two's nine tasks are listed near the end, one line each.

**The order of the tasks:** 1, 2, 2c, 3, 3c, 4, 4c, 5, 5c, 6, 7, 8, 6c, 8c, 9. A task with a `c` is the scene's
piece of the task with its number (Task 8c is the scene's piece of Tasks 7 and 8). Task 6c is built after Task 8,
because the news it words has kinds that Task 8 adds. One task is built at a time. The lead looks at the window
after Task 2c (the tab and its switch), after Task 4c (the word "Apply") and runs Task 8c's proof script on the
real display; the lead runs the live database tests after Task 5 and after Task 9.

**Paths.** Below `rust/crates/`: `E` = `babylon-material-circuit/src`, `T` = `babylon-material-circuit/tests`,
`W` = `babylon-circuit-worlds/src`, `C` = `babylon-client/src/small_world`. The bench is `T/adjustment_bench`.

## The Director's rulings (ADR323), and where Part One meets each

**F1. The measures only nudge.** No measure starts a fight. Each is read from receipts and raises news. Tasks 6
and 6c.

**F2. All four may start a fight:** a union that moves in, the workers themselves, other organizations, yours.
Part One builds the workers themselves: a household stops on its own measure (Tasks 7 and 8). Organizations are
Part Two.

**F3. Whoever organizes the seekers.** "A seeker takes struck work when their household goes without and nobody
offers anything else." Part One builds that weighing, the struck work and the taking of places (Tasks 5, 7 and
8). What an organization gives to hold them (relief, or work asked for them) is Part Two.

**F4. Real wins, payer shown.** A stoppage can win pay anywhere. Part One builds the won rate (Tasks 3 and 8).
The payer's panels are Part Two.

**F5. Others act, yours waits.** "Workers with no organization can walk out too: small, with no fund." Part One
is exactly that. Events for the player are Part Two.

**F6. A win is a contract with an end.** Part Two. In Part One nobody negotiates, so a win is a rate and nothing
holds it (PF11).

**F7. Founding is designed now.** Part Two. Part One opens the accounts kept for it (Task 2).

**F8. A stoppage may ask for work for the people who look for it.** Part Two. Part One builds the engine's acts
it needs (Task 5: hours for people named, taking on, the floor); they reach the screen in Part Two.

**F9. A win is judged by the winners' hours.** Part Two.

**F10. Approved; built after stored hours and before the bridge.**

**F11. One employer has one loss, shared by takings.** Ruled while this plan was written. "A stoppage at one
workplace alone still counts the whole loss, so the people of a utility can win by stopping the power. A walkout
of a whole place asks for more and takes longer to win." Task 8 (`own_takes`, `loss_shares` and their two
tests); Task 9 counts what it does to the later slump.

**F12. Short pay is one person's, at full work.** Ruled while this plan was written. "A household with people
laid off is not short of pay while prices are calm." Task 6 (`Measure::PayShort`), Task 7 (`fewest_steps`) and,
on screen, Task 6c.

**F13. The benefit's delay is built in Part Two.** Ruled while this plan was written. In Part One a person whose
place is taken is laid off at that close and covered from the next period (Task 5). Part Two holds the benefit
back while the rest of the stoppage lasts.

**F14. The Standard points here.** One sentence at question W-A of the Game Design Standard names July's ruling
and this record. It is committed with this plan and is no task.

## Global Constraints

- Work only in `/media/user/dev-ssd/worktrees/households-homes/babylon`, branch `codex/households-and-homes`.
  Start every shell command with `cd` to it (or its `rust/`). Never push. No `.env`, no `uv.lock`.
- One cargo, mise or test process at a time on the whole machine. Never pass `-j`. Only `mise exec -- cargo
  ...` and `mise run ...`. A build in another checkout empties this one's cache: launch long tests with
  `--no-build` after a build when the lead says another checkout is building.
- A command that may run longer than ten minutes runs in the background: output to a log in your scratch
  directory, the line ending `; echo "END <name> status=$?" >> <log>`. Wait for the end marker; never poll the
  log in a loop.
- **Nothing under `babylon-tick`, `babylon-persistence` or `babylon-practice-contract` changes.** No new
  field of `MaterialCircuitState`, `MonetaryCircuit`, `FinancialInstitutions`, `EmploymentTerms`,
  `MemberLaborUseReceipt` or the catalog (each has struct literals in those crates). No new
  `CashTransferPurpose`, no new `AdjustmentReceipt` variant, no new `MaterialCircuitError` code.
- No pinned value of an existing test changes, but one named here:
  `the_rail_has_the_rules_tab_only_for_rules_shown` counts three bodies in the rail's lower part where it
  counted two (Task 2c: the Fight tab). The small world's runs (`tests/small_world/`) keep every figure.
- Money is `i128` millionths of a dollar in `Currency`; hours `u64` (micro-hours `u128` in the ledger only);
  arithmetic checked; a failure is a typed error (`PeriodOrderError`, `FightError`, `RunnerError`), never a
  panic or a wrap. No `unwrap`; an `allow` or `expect` carries a `reason`. No `bool` parameter (enums). No
  `mod.rs`; a file with a folder beside it holds only `mod` and `pub use`. Import a type and use its bare
  name; import the module of a free function and call `module::function`. No `Option<Option<T>>`, no needless
  `Result`. Functions under 100 lines and a cognitive complexity of 25 (`rust/clippy.toml`). Every new value
  is declared Observed, Derived, Calibrated or Designed in its doc comment, with its source.
- **No constant decides where a response turns** (Amendment AM, ADR300): every weighing compares amounts of
  the one household or employer. `YEAR_PERIODS`, the step of pay
  (`pay_step`) and the bench's labelled figures are horizons and
  sizes, never cut-offs; Task 7's planted-cut-off test guards it.
- A contract line that changes is changed with `MATERIAL_CIRCUIT_SOURCE_SHA256` (`E/wire/state.rs`) in the
  same commit; edit the yaml last, then compute the digest; 120 characters a line.
- **Gates**, one leg at a time from `rust/`: fmt `mise exec -- cargo fmt --all -- --check`; clippy `mise
  exec -- cargo clippy --workspace --all-targets --locked -- -D warnings -D clippy::cognitive_complexity`;
  `mise run rust:test:q -- -p <crate>`; `mise run check:bsl-sentinels`. **Scoped engine gate** (Tasks 1, 3,
  4, 5): fmt, clippy, `-p babylon-material-circuit`, `-p babylon-tick`, `-p babylon-circuit-worlds`, `-p
  babylon-client -E 'test(small_world)'`, sentinels. **Small worlds' gate** (Tasks 2, 6, 7, 8, 9): fmt,
  clippy, `-p babylon-circuit-worlds`, `-p babylon-material-circuit --test adjustment_bench`, `-p
  babylon-client -E 'test(small_world)'`, sentinels. **Companion's gate** (2c to 8c): fmt, clippy, `-p
  babylon-client -E 'test(small_world) | test(human_numbers)'`, sentinels. The client's rules hold: no test
  opens a window; every text entity is built by `controls::text` with `DeclaredSurface { id:
  SurfaceId::SmallWorld }`; a figure on screen is exactly a record's; unit words from constants; sizes,
  colours and places on screen are the lead's. A proof script is run by the lead on the real display.
- **The long tests**: the 14 `reproduces_` tests (`mise run rust:test:q -- -p babylon-material-circuit --test
  adjustment_bench -E 'test(/^reproduces_/)' --run-ignored only`) at the end of Tasks 1, 2, 4, 5, 8 and 9, and
  stored hours' `hours_fold_every_reference_run` at the end of Tasks 2 and 8, each in the background.
- **The live database tests are the lead's, not a builder's.** Persistence reaches the engine's close only
  through the older entries, which this plan keeps byte for byte. The lead runs all three focuses (`reader`,
  `runtime`, `money_journal`: `BABYLON_POSTGRES_LIVE_FOCUS=<focus> mise run test:rust-postgres`, from the
  repository root, one at a time) after Task 5 and again after Task 9, and names the focuses that ran. A builder
  never runs `mise run db:up`.
- Commit: `git add <files>`; message in a file; `PYTHONPATH=src mise exec -- git commit -q -F <file>`; then
  check `git log --oneline -1`. Body ends with `Part of PER-371` and a `Co-Authored-By` line naming the model.
- Scratch branches `spike/...` are never merged or switched to; read them with `git show`.
- The design's figures of the sketch are a sketch, not readings; a test that pins one reads it from receipts.
- **Where the plan and the code disagree,** stop and report: do not guess, and do not change an expected value to
  make a test pass. Each type and function is defined in the Interfaces block of the task that produces it; where a
  listing in File Structure and a task's Interfaces differ, the task binds.

## Review Focus

1. **A win holds the workplace back at once.** The plan of period N+1 was bounded at close N at the old rate
   (`next_plans`, state.rs:1956-1975); a rise ordered for N+1 makes `attended < planned`, so with the stop
   rule on the workplace is held and its people limited in the first period of the win (standing.rs:148-154).
   No design rule says it, and a player would read it as a win that laid people off. Pin: Task 3's
   `a_rise_the_cash_cannot_pay_leaves_hours_unpaid` and Task 8's `a_won_rate_s_first_period_in_the_slump`
   (fund-P2 form Fight: count the won rises followed by a `StopReceipt { could_not_pay: true }` in the same
   period); the lead brings the count to the Director. Owner: Task 8.
2. **Ordinary staffing separates strikers.** Strikers stay employed, but `advance_pool`'s target still follows
   the requests and one period of retention (staffing/transition.rs:71-77); separations fall in proportion on
   every member, strikers among them (members.rs:241-253), and the household's next `WithheldOrder` names a
   member with fewer persons. Pin: `a_struck_workplace_s_rolls_fall_only_by_the_ordinary_rule` (counts the
   separations of struck members over a 60-period stoppage and checks each withheld order against the rolls of
   its period). Owner: Task 8.
3. **People above the rolls are also in reserve.** A taker's persons stay in its member's reserve while it
   works (File Structure, "The engine's orders"), so the place's count of people looking for work, the
   seekers' rule of the next close and
   the record of layoffs all still count them, and a covered taker draws the benefit of a period in which it
   took struck work (benefits are paid from the previous staffing's record, state.rs:1653). Pin:
   `the_takers_persons_stay_in_reserve_while_they_work_above_the_rolls` and
   `a_covered_taker_s_benefit_in_a_period_of_struck_work` (Task 5; the second pins what happens: design call 36);
   on screen `takers_are_drawn_at_the_struck_workplace` and `a_taker_already_on_the_rolls_is_one_range` (Task
   5c). In Part One a taker's place is taken at the same close (PF13), so the next weighing finds it on the
   rolls. Owner: Task 5.
4. **The year's edges.** A stoppage in the first periods (no baseline period, PF7 "or of the periods there
   are"), a household whose old cost leaves the count after 13 periods and walks out again, and a second
   stoppage whose baseline skips the first stoppage's periods. Pin: Task 8's
   `a_stoppage_before_any_baseline_period_has_no_baseline`, `a_household_walks_out_again_after_a_year` and
   `the_baseline_skips_struck_periods`. Owner: Task 8.
5. **A household at two workplaces.** PF6's "the pay of its other people" depends on its own PF5 decisions of
   the same step; PF5 workplace by workplace and then PF6 must be the order, and a household with people out at
   one workplace and looking at another must not take its own struck work. Pin:
   `a_household_at_two_workplaces_decides_stop_first_then_struck_work` on a fund-world run after a move
   (the seekers' first move, period 16 of `fund_p2` in `C/marks.rs`). Owner: Task 8.

## File Structure

Each type and function is defined in the Interfaces block of the task that produces it. The listings here are the
map of the whole; where a listing and a task's Interfaces differ, the task binds.

### How a period runs

The engine learns the five material acts as **orders of one period**: a value `PeriodOrders` passed to a new
close entry beside the existing ones, checked against the opening state, applied at named points of the
close, and answered with `OrderReceipt`s in a new list of the transition. The engine keeps nothing of an order
after its period. The only lasting state an order changes is what the state already holds: the rate on
`EmploymentTerms.compensation` (`E/payments/attendance.rs:35-42`), the balances of `AccountId::Organization`
accounts, and persons moved by a staffing order. A world that does not ask never calls the new entry.

Everything that decides (organizations, what is asked, the counts, the weighings PF5 to PF8 and PF18, the
employer's rule PF7, measures, news, events, the forecast, contracts) lives in a new module tree
`W/fight.rs` + `W/fight/*.rs`, the scene's stand-in for the participation and founding resolvers. The runner
keeps a `FightBook` between periods, as it keeps `WorkplaceStanding`; it is not engine state. A world asks for
the fight at its opening (`World.fight`), because accounts exist only from `MonetaryBook::open`.

The decisions of a period N+1 (design steps 2 and 3) are made at the **start** of the runner's `advance` for
N+1, before the engine's close, so that the player's commands, given between steps, are read at step 2. Step
1 (employer, contract dates, founding, measures, news, events) runs at the **end** of `advance` for N, after
the close, the staffing, the checks and the hours fold. Nothing is lost: the employer's offer of close N is
weighed at the start of N+1 and its rate holds from N+1's first hour.

```text
Runner::step()                                          (W/runner/run.rs:191-215, keeps Stepped on Ok only)
 └ advance() for period P                               (run.rs:339-428)
    ├ catalog of P                                      (as today, run.rs:340-357)
    ├ [fight] fight::decide(book, view)                  steps 2 and 3 for P:
    │    organizations in id order (yours from queued commands; Part Two), then households:
    │    weigh::stop (PF5) workplace by workplace, weigh::struck_work (PF6), membership (PF8), paying in (PF18)
    │    -> Decided { book, orders: PeriodOrders, decisions, payments }
    ├ close of P (step 4)
    │    none:  engine::close_material_period[_with_standing]          (run.rs:358-363, unchanged)
    │    fight: engine::close_material_period_with_orders(catalog, state, standing, &orders)
    │       close_with_rules(.., Some(orders))           (E/transition/state.rs:1921)
    │        └ close_support_parts -> close_funded_production (state.rs:1641-1700)
    │            settle_deliveries; retire_resolved_purchases
    │            orders::apply_rates            <- RateOrder, before the benefit reads a rate
    │            FinancialClose::opening       (benefits, state.rs:1653)
    │            orders::pay_funds              <- FundPaymentOrder: strike pay, relief, refunds
    │            payments::fund_attendance(.., &OrderedHours)  <- WithheldOrder, AboveRollsOrder, FloorOrder
    │            costs.admit_attendance
    │            orders::take_wage_shares       <- WageShareOrder: dues, paying in (before any purchase)
    │            ... purchases, production, taxes (1727), profit last (1747)
    │        next_plans; transition literal gains `orders` (state.rs:2014-2063)
    │        restart_stopped: `count` skips a struck workplace (E/adjustment/restart.rs:779-782)
    ├ closed.staffing_requests                          (as today)
    ├ closed.staff_in_places(..)  reads the closed period's orders:
    │      stop round sees offered hours (E/adjustment/standing.rs:257); StaffingOrder moves; FloorOrder
    ├ closed.finish_with_place_staffing                 publishes staffing-order receipts into `orders`
    ├ check_conserved                                    (as today)
    ├ stored hours: HoursLedger::fold                    (stored-hours Task 3, decision 2)
    ├ digest, read_closing, take_receipts (gains `orders`)
    └ [fight] fight::close(decided, closed view)         step 1 of P's close:
         measures (PF14), employer (PF7) -> offer or give way, struck work offered for P+1,
         contract dates and founding (Part Two), news, events with forecasts -> (FightBook, PeriodFight)
Scene (C/scene.rs Stage::handle, 593-620): StartOverWithFight -> a new Runner on World::scene_with_fight();
  Step/Play as today; Part Two: SceneCommand::Yours(YoursCommand) -> Runner::command(..) queued for step 2.
```

### The engine's orders

New module `E/orders.rs` (`mod` and `pub use` only) with `E/orders/{model,receipts,error,validate,apply,
attendance,staffing,digest}.rs`, exported from `E/lib.rs`. All types derive `Clone, Debug, PartialEq, Eq`;
the fieldless enums and the order rows also `Copy`. Money is `Currency` (micro-units); hours `u64`.

```rust
// E/orders/model.rs
/// The orders of one period. Canonical: every list sorted by its key, no key twice (validate refuses).
pub struct PeriodOrders {
    pub period: u64,
    pub rates: Vec<RateOrder>,             // key (site_id, unit_id)
    pub withheld: Vec<WithheldOrder>,      // key member_id
    pub above_rolls: Vec<AboveRollsOrder>, // key member_id
    pub floors: Vec<FloorOrder>,           // key pool_id; Part Two (PF12)
    pub moves: Vec<StaffingOrder>,         // key (host_pool, to_member, from_member)
    pub fund_payments: Vec<FundPaymentOrder>, // key (organization, household)
    pub wage_shares: Vec<WageShareOrder>,  // key (payer, organization)
}
impl PeriodOrders {
    #[must_use] pub const fn none(period: u64) -> Self;   // every list empty
    #[must_use] pub fn is_empty(&self) -> bool;
}
/// PF1: one rate for every row of (site, unit) from the first hour of the period.
pub struct RateOrder { pub site_id: SiteId, pub unit_id: UnitId, pub rate: Currency }
/// PF2: the share of a member's hours on the rolls it withholds this period; 10_000 is all (call 8).
pub struct WithheldOrder { pub member_id: StaffingMemberId, pub share_bps: u16 }
/// PF2, PF12: hours above the rolls this period, paid through `member_id`'s terms (a pair member at the host).
pub struct AboveRollsOrder { pub member_id: StaffingMemberId, pub hours: u64, pub cause: AboveRollsCause }
pub enum AboveRollsCause { StruckWork, Named }
/// PF12 (Part Two): the pool's target at this close is at least `persons`; this period's plan pays at least
/// `paid_hours` (idle where there is no work). Gives way to the stop rule's limit. `site_id` and `unit_id`
/// name the pool's own site and its unit of hours (the close knows no pool bindings).
pub struct FloorOrder { pub pool_id: StaffingPoolId, pub site_id: SiteId, pub unit_id: UnitId,
    pub persons: u64, pub paid_hours: u64 }
/// PF13 and PF12: persons moved for good at this close's staffing, from `from_member`'s reserve into
/// `to_member` (the host's member of the same household). `PlaceTaken` also displaces as many struck persons
/// of the host's own striking members, chosen by `proportional_shares` over their employed.
/// One slot may be both ends (`from_member == to_member`): the persons are called back from that member's
/// own reserve. The same pool with two different members is refused.
pub struct StaffingOrder { pub host_pool: StaffingPoolId, pub to_member: StaffingMemberId,
    pub from_pool: StaffingPoolId, pub from_member: StaffingMemberId, pub persons: u64,
    pub kind: StaffingOrderKind }
pub enum StaffingOrderKind { PlaceTaken, TakenOn }
/// PF3: strike pay, relief, a refund of PF18: organization -> household, at the period's opening.
pub struct FundPaymentOrder { pub organization: OrganizationAccountId, pub household: FinalDemandPrincipalId,
    pub amount: Currency }
/// PF3, PF18: dues or paying in: `share_bps` of the payer's wages of this period net of its wage tax to come,
/// household -> organization, when wages are paid.
pub struct WageShareOrder { pub payer: FinalDemandPrincipalId, pub organization: OrganizationAccountId,
    pub share_bps: u16 }

// E/orders/receipts.rs  (MaterialCircuitTransition gains `pub orders: Vec<OrderReceipt>`, empty unless ordered)
pub enum OrderReceipt { Rate(RateReceipt), Withheld(WithheldReceipt), AboveRolls(AboveRollsReceipt),
    Floor(FloorReceipt), Staffing(StaffingOrderReceipt), FundPayment(FundPaymentReceipt),
    WageShare(WageShareReceipt) }
pub struct RateReceipt { pub period: u64, pub site_id: SiteId, pub unit_id: UnitId, pub old_rate: Currency,
    pub new_rate: Currency, pub rows: u32 }
pub struct WithheldReceipt { pub period: u64, pub member_id: StaffingMemberId, pub site_id: SiteId,
    pub payee: FinalDemandPrincipalId, pub rolls_hours: u64, pub withheld_hours: u64 }
/// `hours`: what was ordered. `attended_hours`: the hours attended above the member's rolls' hours (the
/// rolls' hours are attended first).
pub struct AboveRollsReceipt { pub period: u64, pub member_id: StaffingMemberId, pub site_id: SiteId,
    pub payee: FinalDemandPrincipalId, pub hours: u64, pub attended_hours: u64, pub cause: AboveRollsCause }
pub struct FloorReceipt { pub period: u64, pub pool_id: StaffingPoolId, pub persons: u64,
    pub held: FloorHeld, pub paid_hours: u64 }
pub enum FloorHeld { Held, GaveWayToStop { limit: u64 } }
/// `moved`: the persons the order moved, on what the close left; `displaced`: those it displaced.
pub struct StaffingOrderReceipt { pub period: u64, pub order: StaffingOrder,
    pub household_id: FinalDemandPrincipalId, pub moved: u64, pub displaced: Vec<(StaffingMemberId, u64)> }
pub struct FundPaymentReceipt { pub period: u64, pub order: FundPaymentOrder, pub transfer_ordinal: u32 }
pub struct WageShareReceipt { pub period: u64, pub order: WageShareOrder, pub net_wages: Currency,
    pub amount: Currency, pub transfer_ordinal: Option<u32> }   // None: nothing owed (no pay)

// E/orders/error.rs  (a typed enum of its own; MaterialCircuitError's u16 code table, model.rs:641-679,
// is not touched). impl Display, Error.
pub enum PeriodOrderError {
    WrongPeriod { orders: u64, opening: u64 }, NotMonetary, NotCanonical, Arithmetic,
    UnknownSite(SiteId), RateNotPositive { site_id: SiteId }, NoWageAt { site_id: SiteId, unit_id: UnitId },
    UnknownMember(StaffingMemberId), ShareOutOfRange { member_id: StaffingMemberId, share_bps: u16 },
    NotAWage { member_id: StaffingMemberId },
    StruckWorkWithoutStoppage { site_id: SiteId },
    FillPassesWithheld { site_id: SiteId, withheld: u64, filled: u64 },
    OwnPeopleStopped { member_id: StaffingMemberId },       // PF6: a payee that withholds at that site
    StaffingWithoutSeekers,                                 // moves or floors in a catalog without A14
    UnknownOrganization(OrganizationAccountId), UnknownHousehold(FinalDemandPrincipalId),
    PaymentNotPositive, FundShort { organization: OrganizationAccountId, cash: Currency, ordered: Currency },
    WageShareOutOfRange { payer: FinalDemandPrincipalId, share_bps: u16 },
    MoveFromNoReserve { from_member: StaffingMemberId, reserve: u64, persons: u64 },
    MoveOutOfPlace { host_pool: StaffingPoolId, from_pool: StaffingPoolId },
    DisplacesMoreThanStruck { host_pool: StaffingPoolId, struck: u64, persons: u64 },
    FloorNotThePool { pool_id: StaffingPoolId, site_id: SiteId },
    NotBuilt(OrderKind),                                    // lifted task by task; gone after Task 5 (Part One)
}
pub enum OrderKind { Rate, Withheld, AboveRolls, Floor, Staffing, FundPayment, WageShare }
pub enum OrderedCloseError { Circuit(MaterialCircuitError), Order(PeriodOrderError) } // From both, for `?`
// PlaceStaffingError (E/staffing/place.rs:64-69) gains `Order(PeriodOrderError)`.

// E/transition/state.rs, beside close_material_period_with_standing (1895-1907)
/// The close with the orders of the period. `standing` is `Some` exactly when the catalog asks for the stop
/// rule. With `PeriodOrders::none(opening.period)` it is the matching older entry, byte for byte.
/// # Errors
/// `Order(..)` for an order the opening refuses (E/orders/validate.rs), else as `close_material_period`.
pub fn close_material_period_with_orders(catalog: &MaterialCatalog, opening: &MaterialCircuitState,
    standing: Option<&WorkplaceStanding>, orders: &PeriodOrders)
    -> Result<ClosedMaterialPeriod, OrderedCloseError>;
// close_with_rules (1921) gains `orders: Option<&PeriodOrders>`; the three older entries pass None.
// ClosedMaterialPeriod (621-627) gains `orders: Option<PeriodOrders>` (private; `Some` only when the orders
// are not empty); staff_in_places and finish_with_place_staffing keep their signatures and read it.
// E/orders/digest.rs
/// SHA-256 of the canonical bytes of the orders (domain "babylon.period-orders.v1").
pub fn period_orders_digest(orders: &PeriodOrders) -> Result<[u8; 32], PeriodOrderError>;
```

**Where each order acts** (validation first, in `close_with_rules` before `CompanyInvestment::prepare`; all
or nothing; every error typed as above; the four checks that need the staffing, `MoveFromNoReserve`,
`MoveOutOfPlace`, `DisplacesMoreThanStruck` and `FloorNotThePool`, run in `staff_in_places` and come back as
`PlaceStaffingError::Order`):

1. **Rate.** `orders::apply_rates` in `close_funded_production`, after `retire_resolved_purchases` and before
   `FinancialClose::opening` (state.rs:1652-1653): every `EmploymentTerms` row of (site, unit), own and pair,
   gets `Wage(rate)`. So the benefit (`financial/programs.rs`, wage read from the row), the wages of this
   period, and every rule of this close (bound in `next_plans`, stop rule, host order in `staff_in_places`,
   state.rs:859-867) read it. Refused: rate `<= 0` (settlement.rs validates `> 0`), no `Wage` row there.
   The rate is state: it holds until another order. The plan of this period was bounded at the close before,
   at the old rate (Review Focus 1).
2. **Fund payments.** `orders::pay_funds` right after `FinancialClose::opening`: `book.transfer_cash(
   Organization(o), Household(h), amount, CashTransferPurpose::MutualAid)` and `costs.cash_gift(..)` as
   `E/collection.rs:565-575` does the other way. Refused before any money moves when an organization's orders
   sum above its opening cash (`FundShort`): the runner orders only from cash it read at the last close.
3. **Withheld, above the rolls, floor: `payments::fund_attendance`** (attendance.rs:277-360) gains
   `hours: &OrderedHours` (crate-private: per member `withheld`, `above`; per (site, unit) `paid_floor`;
   `OrderedHours::none()` from every other caller, e.g. `recurring/households_tests.rs:315`). For each member
   the hours **offered** are `capacity - withheld + above`, where `capacity` is the member's
   `MemberLaborCapacityRow` (299-304) and `withheld = capacity * share_bps / 10_000` (floor). `planned` (322-
   334) becomes `plan.max(paid_floor).min(offered_total)`; `proportional_shares(planned, &offered)` (335);
   `fund_member_attendance` is unchanged (attended = min(cash / rate, planned), 371-376). Its receipt's
   `available_hours` is the member's **offered** hours, so `validate` (91-120) holds unchanged. **The member
   rows do not change:** each `MemberLaborCapacityRow` keeps the rolls' hours through the close (the site's own
   labor row is set to its attended hours, as today, attendance.rs:349), so `rest::made_hours` (rest.rs:37-50)
   still sees the rolls' hours: **the resting price and the restart's test
   (`is_tested`, restart.rs:92-94) do not act on withheld hours**, as PF2 asks, with no change to either.
   Withheld hours are never planned, so never `unattended`. Receipts: `WithheldReceipt`, `AboveRollsReceipt`.
4. **The stop rule** (standing.rs): `test_workplaces` (257) gains `withheld: &BTreeMap<SiteId, u64>` (hours,
   from the closed period's `WithheldReceipt`s); `SiteTest.available` and `bill` are read from offered hours
   (already so through point 3); `employed` excludes the persons whose hours were withheld (withheld hours /
   hours a person, whole by call 8); a `limit` is raised by those persons. So no verdict is made on struck
   hours, and a struck workplace is neither freed nor held by them.
5. **The restart's count:** `count` (restart.rs:97-112) is not called for a site with a `WithheldReceipt` in
   the closing period (its `quiet_periods` and `periods_since_work` stay), read in `restart_stopped`
   (779-782) from `transition.orders`.
6. **Wage shares.** `orders::take_wage_shares` in `close_funded_production` after `costs.admit_attendance`
   (1655) and before `HouseholdLists::open` (1658): `net = base - sum of fraction(base, rate_bps, 10_000)`
   over the payer's `TaxBasis::WageIncome` rows, with `base` the period's wage
   accruals to the payer (the `WageAccrualReceipt`s that `fund_attendance` pushed; `costs.tax_base` is still 0 at
   this point of the close),
   the same arithmetic `collect_taxes` will use (`E/financial/close.rs:292-294`); `amount = fraction(net,
   share_bps, 10_000)`; 0 moves nothing. Purpose `MutualAid`, posted with `costs.cash_gift`.
   Before purchases: this is how paying into a fund in the making (PF18) and dues that an employer collects
   under a contract (PF12) are taken. A member's own dues, paid at the close from what is left after it has
   bought, are an act of Part Two.
7. **Staffing orders and floors** in `staff_in_places` (state.rs:844-894) -> `staffing::staff_places`
   (place.rs:425-465): `PlaceRules` (82-93) gains `floors: &BTreeMap<SiteId, u64>`, `moves:
   &[StaffingOrder]` and `striking: &BTreeSet<StaffingMemberId>`. `advance_pool`
   (staffing/transition.rs:62-123) takes the floor:
   `target = requested.max(floor).min(labor_force).min(limit)`, so the stop rule's limit wins (PF12).
   After `pools_decided` (191-227) and before the hosts fill, each `StaffingOrder` in key order: `PlaceTaken`
   moves `persons` of the host's own striking members (those with a `WithheldReceipt` this period) from
   employed to reserve, split by `proportional_shares` over their employed (members.rs:180-209), each a
   separation of the record of layoffs (`record_receipt`), then moves `persons` from `from_member`'s reserve
   (uncovered first, then covered newest first, as `Taking::fill`) to `to_member` employed; `TakenOn` only the
   second. Both rebind labor forces as `conclude` (468-) does. The hosts' `need` is read after them.
   Where one slot is both ends of an order, the persons are called back from that slot's own reserve, the newest
   laid off first, and its labor force does not change. An order is applied to what the engine's decision of
   this close leaves: it moves at most the from slot's reserve and the room under the stop rule's limit, and
   displaces at most the persons still out; it is refused only where it passes what the orderer saw at the
   opening. Its receipt says what moved.
   `StaffingOrderReceipt`s are appended to `transition.orders` by `finish_with_place_staffing` (929-968).

**Why hours above the rolls are an order of one period.** The staffing state's persons are only `employed` and
`reserve` (`StaffingMemberState`, members.rs:87-91) and the pool's labor force is the sum of its members'
(place.rs:508-517). A person who takes struck work is not on any roll that period: their persons stay in their
member's reserve, and only their hours are added. A place is taken for good only by a `StaffingOrder` at a
close. So the fight needs the seekers' path: **a world that asks for the fight opens with `SeekingInPlace`**
(the runner's own `staff` path, run.rs:453, keeps each workplace's people fixed and `check_conserved` refuses
a move without the seekers, run.rs:686-693).

### Bytes that must not change

For a world whose `fight` is `Fight::Absent` (every bench run, `World::scene()`, every golden):

| Place | Why nothing changes |
| --- | --- |
| `World` (W/doubled/world.rs:57-67) gains `fight: Fight` | `Absent` opens no account: `cash_accounts` (opening.rs:158-181) adds organization accounts, and `financial` (490-509) their `InstitutionLocation`s, only for `Asked`. The book, the cost book (`HistoricalCostBook::open`, one capital row per book account) and so `material_circuit_state_digest` are as today. Literals to edit: `tests/worlds.rs:30,39` and the bench's `runs.rs:88` gain `fight: Fight::Absent`; the bench's `sets.rs` and the client's `marks.rs` use `..World::scene()` and need nothing |
| `Runner::advance` | with `self.fight == None` it calls the two older entries exactly as run.rs:358-363 does, and no fight code runs |
| `close_with_rules(.., None)` | every new step is behind `if let Some(orders)`; tick and persistence reach only the older entries |
| `fund_attendance(.., &OrderedHours::none())` | offered = capacity, `paid_floor` 0: the same `planned`, the same shares, the same receipts |
| `test_workplaces(.., &empty)`, `restart_stopped` | no withheld hours: the same tests, the same counts |
| `MaterialCircuitTransition.orders` | a new `Vec`, empty; the engine encodes states, not transitions; the tick builds no transition literal (only state.rs:2014) and encodes chosen receipt lists, never this one |
| `PeriodReceipts.orders`, `PeriodResult.fight` | not in the state digest; the bench's rows name their columns (`adjustment_bench/rows.rs`), so its 14 sets keep their digests |
| `MaterialCatalog` | no catalog field: the fight asks nothing of the catalog, so catalog version 9 and its bytes stay |
| `CashTransferPurpose` (7 variants) | no new purpose: `babylon-persistence` `money_journal/model.rs:46-49` and the client's `site_financial_statements.rs:88-91` keep their matches |
| `AdjustmentReceipt` | no new variant: the four exhaustive matches of `C/marks.rs` stay |
| `MaterialCircuitError` | its code table is untouched; new refusals are `PeriodOrderError` |
| `contracts/material_circuit_v4.yaml` | new keys `ADR323_*` change `MATERIAL_CIRCUIT_SOURCE_SHA256` (`E/wire/state.rs`, pinned by `tests/weighted_freight.rs`); no state digest reads it (the closest form changed it six times with all 14 long tests equal) |
| `PlaceStaffingError` | one new variant, one new arm in `run.rs:541` `place_error`; the bench's `sets.rs:253` matches a named variant |
| the client | Part One adds no party and no payment kind (both come with P2-1); nothing in the client walks the account book, so the 16 kept accounts of a fight world are never met; the one pin that moves is the count of bodies in the rail's lower part (Global Constraints) |
| stored hours | the fold never meets an organization account in such a world |

Proof: the 14 `reproduces_` long tests; `empty_orders_close_as_the_older_entry` (Task 1);
`a_world_that_does_not_ask_steps_as_before` (Task 2: 34 periods of `World::scene()` and of the bench's
`fund-P2` form `Down`, state digests equal to those of the
same world before Task 2, pinned as hex in the test from a run on the code before Task 2; Task 1 runs the 14
long tests at its own end, so a byte it moved is found there).

### The small worlds' new modules

```text
W/fight.rs               mod + pub use only
W/fight/world.rs         Fight, FightOpening, OrganizationOpening; the accounts a world opens; constants
W/fight/organization.rs  OrganizationId, Line, Organization, Fund (read), Membership (Part Two use)
W/fight/ask.rs           Ask, Asker, Term, fewest_steps; the ask with no call
W/fight/counts.rs        EmployerCount, HouseholdCount: the two counts over the last year
W/fight/measures.rs      Measure, MeasureRow, WorkplaceTake, needs_cost: PF14 from receipts
W/fight/weigh.rs         StopAccounts, weigh_stop (PF5); SeekerAccounts, weigh_struck_work (PF6);
                         Part Two: weigh_membership (PF8), weigh_paying_in (PF18)
W/fight/employer.rs      employer_decides (PF7), the offer, struck work offered
W/fight/stoppage.rs      Stoppage, StoppagePeriod, StoppageEnd: the record of an episode
W/fight/news.rs          News, NewsItem, Cause; Part Two: Event, Forecast, EventChoice
W/fight/period.rs        FightBook, decide (steps 2-3), close (step 1), PeriodFight, FightError
W/fight/period_tests.rs  Task 8's unit tests of decide and close (they read the book's private fields)
W/fight/payments.rs      FundPaymentKind, PaymentRecord: the runner's own receipts of each payment's kind
W/fight/contract.rs      Part Two: Contract, ContractTerms, calendar
W/fight/founding.rs      Part Two: FundInMaking, founding
W/fight/yours.rs         Part Two: YoursCommand, CommandError
W/fight/payer.rs         Part Two: PayerPanel, the line under a win (PF17)
W/fight/am.rs            the response test of Amendment AM, for every weighing
```

```rust
// W/fight/world.rs
pub enum Fight { Absent, Asked(FightOpening) }
pub struct FightOpening { pub organizations: Vec<OrganizationOpening>, pub employers: Employers }
/// `OfferAtOnce` is a labelled figure of the bench (Task 9's second table), never of the scene: what the
/// people of a workplace would ask is offered at once, with no stoppage.
pub enum Employers { ByTheirCount, OfferAtOnce }
pub struct OrganizationOpening { pub line: Line, pub fund: Currency, pub members: Vec<Household> }
/// Designed (PF18, call 28): accounts kept for founding, a ceiling of the build.
pub const FOUNDING_ACCOUNTS_PER_WORKPLACE: usize = 2;
/// Designed: one year of the weighings, ADR314 A16 and the homes design's call 13 (= kernel TICKS_PER_YEAR).
pub const YEAR_PERIODS: u64 = 13;
/// Designed (A15, call 38): a step of pay at the small figures, millionths of a dollar ($1 an hour).
pub const PAY_STEP_MICRO: i128 = 1_000_000;
/// Designed (call 38): at the national figures a step is 250 basis points of the workplace's opening wage.
pub const NATIONAL_PAY_STEP_BPS: i128 = 250;
#[must_use] pub fn pay_step(world: &World, workplace: Workplace) -> Currency;
impl World { #[must_use] pub fn with_fight(self, opening: FightOpening) -> Self; }
// W/ids.rs gains: OrganizationSlot(u8), its field private (`OrganizationSlot::new(index: usize) ->
// Result<Self, WorldError>`, `index()`), and `organization_account(slot) -> OrganizationAccountId` (32
// copies of byte 40 + slot); WorldError gains FightNeedsSeekers and TooManyOrganizations.

// W/fight/organization.rs
pub struct OrganizationId(pub u8);                 // the slot; ids order step 2
pub enum Line { Yours, Union, Founded, Other }
pub struct Organization { pub id: OrganizationId, pub account: OrganizationAccountId, pub line: Line,
    pub members: Vec<Household>, pub standing: OrganizationStanding }
pub enum OrganizationStanding { Kept, Alive { since: u64 }, Dead { since: u64 } }  // Kept: a founding account
pub struct Membership { pub household: Household, pub organization: OrganizationId, pub since: u64 }

// W/fight/ask.rs
pub enum Asker { Household(Household), Organization(OrganizationId) }
pub enum Term { PayFollowsPrices, TakenBackFirst, DuesCollected, WorkForSeekers }   // Part Two
pub struct Ask { pub workplace: Workplace, pub asker: Asker, pub rate_now: Currency, pub rate_asked: Currency,
    pub steps: u32, pub terms: Vec<Term>, pub named: Vec<(Household, u64)> }
/// The fewest steps that make a period's pay after tax cover `needs` (PF5 1, measure a).
pub fn fewest_steps(pay_after_tax: Currency, needs: Currency, hours: u64, wage_tax_bps: u32, step: Currency)
    -> Result<u32, FightError>;

// W/fight/counts.rs  (both over the last YEAR_PERIODS, started again when what is asked is won)
pub struct EmployerCount { pub employer: Household, pub workplace: Workplace, pub losses: Vec<(u64, Currency)> }
pub struct HouseholdCount { pub household: Household, pub workplace: Workplace, pub costs: Vec<(u64, Currency)> }
impl EmployerCount { pub fn within_year(&self, period: u64) -> Result<Currency, FightError>; }
impl HouseholdCount { pub fn within_year(&self, period: u64) -> Result<Currency, FightError>; }
/// PF7: what all the employer's workplaces paid it a period, mean of the last YEAR_PERIODS periods with no
/// hours withheld at `workplace` (or of those there are); `None` when there are none.
pub fn baseline(history: &[PeriodResult], employer: Household, workplace: Workplace)
    -> Result<Option<Currency>, FightError>;
// Task 8 also defines `own_takes` and `loss_shares`: one employer's loss of a period is shared among its
// struck workplaces by what each had been paying it (design call 44).

// W/fight/measures.rs
/// PayShort: one person's, at full work (pay after the tax to come against the cost of one person's needs).
pub enum Measure { PayShort { pay: Currency, needs: Currency }, PayCut { from: Currency, to: Currency },
    HandsShort { asked_hours: u64, filled_hours: u64 },
    TakeGrows { take: Currency, before: Currency, laid_off: u64, cut: Currency } }
pub enum Begins { Now, Continues }
pub struct MeasureRow { pub period: u64, pub workplace: Workplace, pub household: Option<Household>,
    pub measure: Measure, pub begins: Begins }
pub struct WorkplaceTake { pub to_owners: Currency, pub to_people: Currency }
pub fn measures(result: &PeriodResult, before: Option<&PeriodResult>, last: &[MeasureRow])
    -> Result<Vec<MeasureRow>, FightError>;
pub fn take_of(result: &PeriodResult, workplace: Workplace) -> Result<WorkplaceTake, FightError>;
/// A household's needs for a period at the posted prices of the close (`summary.prices`), its required
/// quantities from the consumption and service receipts; food from its shop, power and care from its place's.
pub fn needs_cost(result: &PeriodResult, household: Household) -> Result<Currency, FightError>;

// W/fight/weigh.rs  (one household's own amounts in, a decision with what was weighed out; no constant)
pub enum Ground { Called, OwnMeasure(Measure), Nothing }
pub enum Condition { Holds, Fails }
pub struct StopAccounts { pub ground: Ground, pub pay_here: Currency, pub pay_elsewhere: Currency,
    pub money: Currency, pub funds_pay: Currency, pub needs: Currency, pub cost_within_year: Currency,
    pub asked_year: Currency }
pub enum StopChoice { Stop, Work }
pub struct StopDecision { pub choice: StopChoice, pub something: Condition, pub can_go_without: Condition,
    pub worth_it: Condition, pub cost_this_period: Currency, pub weighed: StopAccounts }
pub fn weigh_stop(accounts: &StopAccounts) -> Result<StopDecision, FightError>;
pub enum OwnPeople { StoppedHere, NotStoppedHere }
pub struct SeekerAccounts { pub persons: u64, pub struck_pay: Currency, pub money: Currency,
    pub benefit: Currency, pub relief: Currency, pub other_pay: Currency, pub needs: Currency,
    pub own_people: OwnPeople }
pub enum TakeChoice { Take, Refuse }
pub struct TakeDecision { pub choice: TakeChoice, pub goes_without: Condition, pub more_to_live_on: Condition,
    pub without: Currency, pub with: Currency, pub weighed: SeekerAccounts }
pub fn weigh_struck_work(accounts: &SeekerAccounts) -> Result<TakeDecision, FightError>;
// Part Two adds MemberAccounts/weigh_membership (PF8) and PayInAccounts/weigh_paying_in (PF18), same form.

// W/fight/am.rs
pub enum Response { Differs, Same }
/// Amendment AM: the population's choices differ when, and only when, their own amounts differ.
pub fn responds_to_own_amounts<A, D: PartialEq>(population: &[A], weigh: impl Fn(&A) -> D) -> Response;

// W/fight/employer.rs
pub enum EmployerDecision { GiveWay { cost: Currency, asked_year: Currency },
    OfferStruckWork { hours: u64, cost: Currency, asked_year: Currency }, NeverPaid }
pub fn employer_decides(count: &EmployerCount, period: u64, asked_year: Currency, baseline: Option<Currency>,
    withheld_hours: u64) -> Result<EmployerDecision, FightError>;
pub struct StruckOffer { pub workplace: Workplace, pub period: u64, pub hours: u64, pub rate: Currency }

// W/fight/stoppage.rs
pub enum StoppageEnd { GaveWay, WentBack, PlacesTaken }
/// `out`, `filled`: persons by household.
pub struct StoppagePeriod { pub period: u64, pub out: Vec<(Household, u64)>, pub filled: Vec<(Household, u64)>,
    pub paid: Vec<PaymentRecord> }
pub struct Stoppage { pub workplace: Workplace, pub began: u64, pub ask: Ask, pub periods: Vec<StoppagePeriod>,
    pub ended: Option<(u64, StoppageEnd)> }

// W/fight/payments.rs
pub enum FundPaymentKind { Dues, PayingIn, StrikePay, Relief, Refund }
pub struct PaymentRecord { pub period: u64, pub kind: FundPaymentKind, pub organization: OrganizationId,
    pub household: Household, pub amount: Currency }

// W/fight/news.rs
pub enum Cause { Measure, Weighing(Household), Employer(Household), Order(OrderKind), Founding, Contract }
/// `Stopped.out` and `StruckWorkTaken.by`: persons by household.
pub enum NewsItem { MeasureBegins(MeasureRow), Stopped { workplace: Workplace, out: Vec<(Household, u64)>,
    ask: Ask }, WentBack { workplace: Workplace, household: Household },
    StruckWorkOffered(StruckOffer), StruckWorkTaken { workplace: Workplace, by: Vec<(Household, u64)> },
    GaveWay { workplace: Workplace, rate: Currency }, PlacesTaken { workplace: Workplace, persons: u64 },
    RateChanged { workplace: Workplace, from: Currency, to: Currency } }    // Part Two adds its items
pub struct News { pub period: u64, pub item: NewsItem, pub cause: Cause }

// W/fight/period.rs
pub enum HouseholdDecision { Stop { household: Household, workplace: Workplace, decision: StopDecision },
    StruckWork { household: Household, workplace: Workplace, decision: TakeDecision } }
pub struct EmployerRecord { pub employer: Household, pub workplace: Workplace, pub decision: EmployerDecision }
/// What the fight did in one period; `PeriodResult.fight` (W/runner/result.rs:18-38) gains `Option<PeriodFight>`.
pub struct PeriodFight { pub orders: PeriodOrders, pub orders_digest: [u8; 32],
    pub decisions: Vec<HouseholdDecision>, pub payments: Vec<PaymentRecord>,
    pub employers: Vec<EmployerRecord>, pub offered: Vec<StruckOffer>, pub stoppages: Vec<Stoppage>,
    pub measures: Vec<MeasureRow>, pub news: Vec<News>, pub organizations: Vec<(Organization, Currency)> }
pub struct FightBook { /* private: organizations, stoppages, counts, offers, measures of the last close */ }
pub enum FightError { Arithmetic, UnknownHousehold(Household), NoReceipt(String), AccountsFull,
    Order(PeriodOrderError) }                     // RunnerError gains Fight { period: u64, error: FightError }
pub(crate) fn open(world: &World) -> Result<Option<FightBook>, WorldError>;
pub(crate) fn decide(book: &FightBook, view: &DecideView<'_>) -> Result<Decided, FightError>;
pub(crate) fn close(decided: Decided, closed: &ClosedView<'_>) -> Result<(FightBook, PeriodFight), FightError>;
```

How `advance` composes them (run.rs:339-428; `Stepped` (20-26) gains `fight: Option<FightBook>`):

```rust
fn advance(&mut self) -> Result<Stepped, RunnerError> {
    let period = self.state.period;                       // horizon, figures, rules, catalog: as today
    let decided = match &self.fight {                     // steps 2 and 3 for `period`
        None => None,
        Some(book) => Some(fight::decide(book, &DecideView {
            world: &self.world, period, state: &self.state, members: &self.members,
            last: self.history.last(), history: &self.history,
            // Part Two: commands: &self.queued (yours, at its turn in id order)
        }).map_err(|error| RunnerError::Fight { period, error })?),
    };
    let stop_on = rules.contains(&AdjustmentRule::StopWithoutPay);
    let closed = match &decided {                         // step 4: the period runs with its orders
        None if stop_on => engine::close_material_period_with_standing(catalog, &self.state, &self.standing)
            .map_err(|e| engine_error(period, Stage::Close, e))?,
        None => engine::close_material_period(catalog, &self.state)
            .map_err(|e| engine_error(period, Stage::Close, e))?,
        Some(d) => engine::close_material_period_with_orders(
            catalog, &self.state, stop_on.then_some(&self.standing), &d.orders)
            .map_err(|e| ordered_error(period, e))?,      // Order(..) -> RunnerError::Orders
    };
    let requests = closed.staffing_requests(catalog, &self.bindings)?;         // as today
    let (staffed, transition) = /* as today, run.rs:367-393: the fight always takes the seekers' arm */;
    check_conserved(period, &self.opening, &transition.state, (..), seeking)?; // as today
    let (ledger, hours) = /* stored hours, Task 3: fold when self.hours is Some */;
    let state_digest = engine::material_circuit_state_digest(catalog, &transition.state)?;
    let (closing, summary) = read_closing(period, &figures, &transition, staffed.employed, staffed.reserve)?;
    let receipts = take_receipts(&transition);            // gains `orders: transition.orders.clone()`
    let mut result = PeriodResult { period, figures, rules, members: staffed.members, closing, summary,
        state_digest, asked: staffed.asked, receipts, hours, fight: None };
    let book = match decided {                            // step 1 of this close reads the result so far
        None => None,
        Some(d) => {
            let view = ClosedView { period, result: &result, history: &self.history, state: &transition.state };
            let (book, record) = fight::close(d, &view).map_err(|error| RunnerError::Fight { period, error })?;
            result.fight = Some(record);
            Some(book)
        }
    };
    Ok(Stepped { result, state: transition.state, staffing: staffed.staffing, members: staffed.kept,
        standing: staffed.standing, hours: ledger, fight: book })
}
```

`decide` and `close` are written out in Task 8: the order of the decisions, how each amount is formed from a
household's own accounts, and the orders they build. No household reads another's decision of the same step:
`decide` reads only the last close and its book. Task 2 composes `advance` as above; Task 8 does not touch the
runner.

### The scene

Files (all under `C/`): `small_world.rs` (`mod fight;`), new `fight.rs` (the Fight tab, its switch, its rows
and words; Part Two: the event's buttons), `reading.rs`, `frame.rs`, `layout.rs`, `panel.rs`, `inspect.rs`,
`scene.rs`, `script.rs`, `scene_tests.rs`, `script_tests.rs`. Modelled on the rules' switches (`rules.rs`
`SceneRule`, `spawn_rules_tab` 203-227, `RuleButton`, `rules::pressed` added as an observer in
`SmallWorldPlugin::build`, scene.rs:280-282) and on the shocks' list (`panel::paint_shocks`, `LiftButton`).

| Piece | How it reaches the runner | What is drawn | Task |
| --- | --- | --- | --- |
| The fight's switch | `Lower::Fight` (panel.rs:51-55 gains it), a `FightButton` in `fight.rs`; `SceneCommand::StartOverWithFight` -> `Stage::start_over_with(World::scene_with_fight())` through `scene::open_runner_of(world)` (stored hours' `open_runner()` calls it with `World::scene()`); script `{"fight":"on"}`, `{"lower":"fight"}` | "The pay fight: from the opening (starts over)"; the switch's state | 2c |
| Organizations' money | `Party::Organization(OrganizationId)` in `reading.rs` (`from_account`, 26-36); `PaymentKind::MutualAid` (49-69) read from `Cash(MutualAid)` (298-302 stop refusing it) | a gold stream like every payment; the fund's cash as a row of the tab; kind words from `PaymentRecord` | P2-1 |
| A workplace's rate | `RateReceipt` and the compensation of the period's member receipts | "Pays $10.00 an hour" in a workplace's panel (`inspect.rs`), "from period N" after a change | 3c |
| The people at the gate | `WithheldReceipt` | a household's persons whose hours are withheld stand at `layout::gate_of(w)`; no hours stream from them into the workplace (falls out of the receipts) | 4c |
| Struck work and who takes it | `AboveRollsReceipt`, `StaffingOrderReceipt` (5c); `PeriodFight.offered` (8c) | takers drawn at the struck workplace from their home; "Struck work offered: N hours" and "taken by ..." rows; places taken in the news | 5c |
| The measures and the news | `PeriodFight.measures`, `.news` | a news list in the Fight tab, each item with its cause; the four measures in a workplace's panel | 6c (built after Task 8) |
| The stoppage and both counts | `PeriodFight.stoppages`, `.employers`, `.decisions` | the gate, the ask, "cost the owners $X of a year's $Y", a household's weighing in its panel | 8c |
| Rings, the thinner ring | Part Two | hatched ring round member households (`ring_mesh` with a dash, scene.rs:648-660); thinner for a fund in the making | P2 |
| An event with buttons, the forecast | Part Two: `SceneCommand::Yours(YoursCommand)` -> `Runner::command` | the event's line, its forecast, "[ Pay the 3 ] [ Pay the farm's people too ] [ Let it be ]" | P2 |
| A contract on a workplace; the payer's panels | Part Two | its pay, terms, last period; the three panels and the line under a win | P2 |

Design call 40: the button that brings a shock reads "Apply" (Task 4c). `SceneCommand::Strike` and
`ShockButton::Strike` become `Apply`; the script's `strike` key and `Runner::strike` keep their names.

### Where this meets stored hours

| File | Stored hours (its task) | The pay fight (task) |
| --- | --- | --- |
| `W/runner/run.rs` `advance` | the fold after `check_conserved`, before the digest; `hours: Option<HoursLedger>` field; `Stepped` gains the ledger (3) | steps 2-3 before the close, the orders entry, step 1 after `take_receipts`; `Stepped` gains `fight` (2) |
| `W/runner/run.rs` `open_world` | `open_world_with_hours` (3) | `fight::open(world)` in `open_world`, so both entries carry the fight (2) |
| `W/runner/result.rs` | `PeriodResult.hours` (3) | `PeriodResult.fight`, `PeriodReceipts.orders` (2) |
| `W/runner/error.rs` | `HoursRefused`, `HoursRunsDiffer`, `HoursUnplaced`, `ClaimRefused`, `PurseNotBook`, `ClaimsNotBack` (3, 4) | `Orders { period, error }`, `Fight { period, error }`, `Stage::Orders` (2) |
| `W/runner.rs`, `W/lib.rs` | `pub mod hours`, its exports (3, 4) | `pub mod fight` at the crate root, its exports (2) |
| `babylon-recorded-labor/src/claim/kind.rs`, `purses.rs` | `Cash(MutualAid)` into a household is `Support`; any `Cash(..)` out draws the mix; a transfer with no household side changes no purse (4, decisions 1-2) | relies on it: strike pay and relief are support, dues leave the purse; Task 2 adds `a_fight_world_folds_its_payments` |
| `bench sets.rs` | `hours_fold_every_reference_run` (3, 4) | `fight_counts_the_later_slump` (9); neither is a `reproduces_` test |
| `C/reading.rs` | `GoodsMove.opening` (5) | nothing in Part One (`Party::Organization` and `PaymentKind::MutualAid` come with P2-1) |
| `C/frame.rs`, `panel.rs`, `table.rs`, `inspect.rs`, `scene.rs`, `script.rs`, `script_tests.rs`, `scene_tests.rs` | part-full squares, standing line, table switch, details panel, `open_runner`, `ScriptReport.stored_hours` (5-7) | gate, takers, Fight tab, rows, `StartOverWithFight` through `open_runner_of` (2c-8c) |

What PF17 (Part Two, task P2-7) needs, in the stored-hours plan's names: the runner opened with
`Runner::open_world_with_hours`; per period `PeriodResult.hours: Option<PeriodHours>`;
`PeriodHours::household(Household) -> Option<&HouseholdHours>`; `HouseholdHours.clock: u64` (hours on the
clock, whole, `attended_hours`), `HouseholdHours.claims: ClaimHours { work, owning, support, not_recorded }`
(micro-hours, `work` = hours back for work). "Hours beyond the clock" has no name there: the bribe is counted
only by the test `no_group_s_back_for_work_passes_its_clock` (`W/../tests/hours.rs`, over the run so far).
PF17 derives it in `W/fight/payer.rs` over a span of six periods as `max(0, sum(claims.work) - 1_000_000 *
sum(clock))`, and each figure "for one person on the clock" over the span's persons on the clock, the sum of
the household's members' `opening_employed` (`PeriodResult.members`). Spans: the six periods before the
stoppage began and the six after the win. Call 24 amends the stored-hours test for runs with a win: that test
runs worlds with no fight, so the amendment is a sentence of the stored-hours design and a guard that
`hours_fold_every_reference_run` folds no fight world.

### Notes for the engine's tasks (1, 3, 4, 5)

- **The contract and its digest.** A task that changes `contracts/material_circuit_v4.yaml` changes
  `MATERIAL_CIRCUIT_SOURCE_SHA256` (`E/wire/state.rs:30-34`) in the same commit, as the closest form's tasks did
  (`d4ac7dc0d` changed the two together). Edit the yaml last; lines of at most 120 characters. Then, from the
  repository root: `python3 -I -c "import hashlib; d = hashlib.sha256(open('contracts/material_circuit_v4.yaml',
  'rb').read()).digest(); print(', '.join(str(b) for b in d))"`, put the 32 numbers in the array, run `mise exec
  -- cargo fmt --all` and see `row_permutations_and_wire_roundtrip_preserve_complete_continuation`
  (`T/weighted_freight.rs:350-405`, which compares the file's SHA-256 with the constant) pass: `mise run
  rust:test:q -- -p babylon-material-circuit --test weighted_freight`.

**The test file of these tasks** is `T/period_orders.rs`, a root that holds only `#[path]` modules (as
`T/small_world.rs` does): `support` (Task 1), `payments` (Task 1), `rates` (Task 3), `withheld` (Task 4),
`struck_work` (Task 5). One test: `mise run rust:test:q -- -p babylon-material-circuit --test period_orders -E
'test(<name>)'`; the file: `... --test period_orders`.

**The figures the tests use, and where they are** (fund world, `World::scene()`; all in
`W/doubled/opening.rs` unless said): the wage $10 an hour on every row (`WAGE`, line 25; `employment`,
591-607); 10 hours a person (`World::hours_per_person`, `W/doubled/world.rs`); workers 12 at a utility and 4
at a farm, a clinic or a shop (`Household::opening_persons`, `W/ids.rs:282-290`), so the opening's hours are
utility 120, farm 40, clinic 40, shop 40 a place (`site_hours`, 89-107), and the attendance plan of period 1 is
the same hours (`recurring`, 466-474); site cash farm $880, utility $1,200, clinic $880, shop $1,400
(`SITE_CASH`, 29); the wage taxes on each worker household, 500 bps to the treasury and 1,500 bps to the fund
(`add_public_accounts`, 512-541); the benefit after a layoff 5,000 bps of the member's wage for 13 half periods
(570-584; `E/financial/layoffs.rs:177-211`). In period 1 nothing moves a site's cash before wages: the opening
has no orders (`opening_state_of`, `orders: vec![]`), no contributions, and public funding pays households only.
A farm worker household's wages of period 1 are 40 hours at $10 = $400.

### Notes for the small worlds' tasks (2, 6, 7, 8, 9)

**Builds on:** stored hours Tasks 3 and 4 as built (`Runner::open_world_with_hours`, `HoursLedger`, `PeriodHours`,
`PeriodResult.hours`, `Stepped.hours`, the claim's purses), and the engine's Task 1 of this plan (the orders of a
period, fund payments and wage shares applied). Tasks 3, 4 and 5 of the engine come between Task 2 and Task 6.
Where the code you find differs from a line number here, the code binds; where it differs from an interface, stop
and report.

Every test below opens worlds through the crate's public API, except the two unit-test files named (they reach
`pub(crate)` items). In tests, money is built with `fn dollars(v: i128) -> Currency { Currency::from_micro_units(v
* 1_000_000) }`. The engine's errors have no `Display`: in a test returning `Result<(), Box<dyn Error>>`, map them
with `.map_err(|e| format!("{e:?}"))?`. The shorthands `UTILITY_A`, `FARM_A`, `CLINIC_A`, `SHOP_A` are
`Workplace { place: Place::A, kind: Kind::.. }`.

### Notes for the scene's tasks (2c to 8c)

**What binds you** (read once, it holds for all six tasks):

- The client's rules: no test opens a window; every text entity is built by `controls::text`, which carries
  `DeclaredSurface { id: SurfaceId::SmallWorld }`; a figure on screen is exactly a record's (a sum or a
  difference of record fields is written out in the task); sizes, colours and places on screen are the lead's.
  Each starting value below is labelled "starting value" and the lead tunes it at the look.
- Hours and money never meet (ADR317, R1): the client never divides money by hours. A wage rate on screen is the
  engine's own figure (`LaborCompensation::Wage(rate)`, a `RateReceipt`, an `Ask`), printed as it is.
- Import a type and use its bare name; call a free function through its module. No `unwrap`; an `allow` or
  `expect` carries a `reason`. Arithmetic is checked; a failure is `FrameError::Arithmetic` or
  `FrameError::Edge(words)`. Functions under 100 lines, cognitive complexity under 25.
- A match on `OrderReceipt` names every variant (no wildcard), as the client does for `AdjustmentReceipt`.
- `Currency::checked_add` and `checked_sub` fail with `CurrencyOverflow`, which has no `Error`: in a test write
  `.map_err(|e| format!("{e:?}"))?` after each.
- Nothing drawn for a world with no fight differs from today. Task 2c pins it
  (`a_world_with_no_fight_draws_as_before`), and every later task runs that test unchanged.
- One cargo or mise process at a time on the machine; never `-j`. Commands run from `rust/` of
  `/media/user/dev-ssd/worktrees/households-homes/babylon`. Never push.
- **One test:** `mise run rust:test:q -- -p babylon-client -E 'test(<name>)'`.
- **The companion's gate**, one leg at a time: `mise exec -- cargo fmt --all -- --check`; `mise exec -- cargo
  clippy --workspace --all-targets --locked -- -D warnings -D clippy::cognitive_complexity`; `mise run
  rust:test:q -- -p babylon-client -E 'test(small_world) | test(human_numbers)'`; `mise run check:bsl-sentinels`.
- **Commit:** `git add <files>`; the message in a file; `PYTHONPATH=src mise exec -- git commit -q -F <file>`;
  then `git log --oneline -1`. The body ends with `Part of PER-371` and a `Co-Authored-By` line naming the model.
- A proof script is run by the lead on the real display, never by the builder.

**What stored hours' Tasks 5 to 7 will have changed first** (by that plan's names). Read the file as it stands:

| File | Stored hours | What it means for you |
| --- | --- | --- |
| `C/scene.rs` | `open_runner()` opens `World::scene()` with `Runner::open_world_with_hours`; both openings call it (5); `SceneCommand::Columns(Columns)` and its `Stage::handle` arm (6) | Task 2c adds `open_runner_of(world)` beside it |
| `C/reading.rs` | `GoodsMove.opening`, `PeriodReading.opening_per_hundred` (5) | `Party` and `PaymentKind` are as at 98a0e3624 |
| `C/frame.rs` | `goods_flows` writes a full and a hollow flow (5) | `STREAM_MONEY`, `payment_stream`, `Standing::point` as at 98a0e3624 |
| `C/panel.rs` | `STORED_WORK_LINE` gone (5); `Columns`, `PanelView.columns`, `PanelButton::Columns`, the switch at the pager's end, `TO_THE_HOUR_LINE`, `chosen` and `press_panel` arms (6) | `Lower`, `spawn_lower`, `lower_caption`, `paint_lower`, `rows_for` as at 98a0e3624 |
| `C/table.rs` | `HoursRow`, `HoursTable`, `hours_table`; `NOT_MEASURED` gone (5, 6) | unchanged by Part One |
| `C/inspect.rs` | rows of hours before the money rows of a household and a workplace (6) | the fight's rows come after the rules' rows (3c) |
| `C/controls.rs` | `GOODS_HOLLOW_LINE`'s words, `OpeningLine`, `PEOPLE_LINE_AT` 5 (5) | unchanged by Part One |
| `C/script.rs` | `ScriptCommand::Columns`, `columns_named` (6); `ScriptReport.stored_hours` (7) | Task 2c adds `Fight`; Task 8c adds `ScriptReport.fight` |
| `C/scene_tests.rs`, `C/script_tests.rs` | `PROOF_SH5`, `PROOF_SH6`, `PROOF_SH7` and their tests (5-7) | keep them |

**What the engine and the small worlds hand you** (built by Tasks 1 to 8; the names of the plan's File Structure,
"The engine's orders" and "The small worlds' new modules", exactly):
`babylon_material_circuit::{OrderReceipt, RateReceipt, WithheldReceipt, AboveRollsReceipt, AboveRollsCause,
StaffingOrderReceipt, StaffingOrder, StaffingOrderKind, OrderKind}`; `PeriodReceipts.orders: Vec<OrderReceipt>`;
`PeriodResult.fight: Option<PeriodFight>` (`Some` exactly for a world whose `fight` is `Fight::Asked`);
`babylon_circuit_worlds::fight::{Fight, FightOpening, PeriodFight, News, NewsItem, Cause, MeasureRow, Measure,
Begins, WorkplaceTake, StruckOffer, Stoppage, StoppagePeriod, StoppageEnd, Ask, Asker, HouseholdDecision,
EmployerRecord, EmployerDecision, StopDecision, StopChoice, StopAccounts, TakeDecision, TakeChoice, SeekerAccounts,
Ground, Condition, OwnPeople}`, `fight::take_of`, `fight::pay_step(world: &World, workplace: Workplace) ->
Currency` ($1 an hour at the small figures); `babylon_circuit_worlds::World` with `World::scene_with_fight()` and
`World.fight`. If Task 2 exported a name from the crate root and not from `fight`, import it from where it is; the
name does not change.

**What exists when.** `PeriodFight` is built up by tasks: after Task 2 it has `orders`, `orders_digest`,
`payments` and `organizations`. In Part One `payments` is empty, and `organizations` lists only the 16 kept
accounts (`Line::Founded`, `OrganizationStanding::Kept`, no cash, two for each workplace), which the scene does not
draw; no test asserts that it is empty. Task 6 adds `measures` and `news`; Task 8 adds `decisions`,
`employers`, `offered` and `stoppages`. The order of building is 1, 2, 2c, 3, 3c, 4, 4c, 5, 5c, 6, 7, 8, 6c, 8c, 9,
and each client task reads only what exists before it. In `StoppagePeriod.out`, `StoppagePeriod.filled`,
`NewsItem::Stopped.out` and `NewsItem::StruckWorkTaken.by` every figure is persons, by household.
`AboveRollsReceipt.attended_hours` is the hours attended above the member's rolls' hours; `hours` is what was
ordered. `StaffingOrderReceipt` is `{ period, order, household_id, moved: u64, displaced: Vec<(StaffingMemberId,
u64)> }`: the engine applies an order to what the close leaves, so `moved` (the persons moved) can be less than
`order.persons`, or 0, and `displaced` is what was displaced. `PeriodResult.members` stays the engine's decision
before any move or order: people moved by an order are read from the receipts, never from `closing_employed`.
`FightOpening` has `employers: Employers` (`ByTheirCount`, `OfferAtOnce`); the scene calls only
`World::scene_with_fight()`, which uses `ByTheirCount`, and no test of these tasks writes a `FightOpening`.

## The tasks

### Task 1: The orders of a period, and payments to and from a fund

**Files:**
- Create: `E/orders.rs` (`mod` and `pub use` only); `E/orders/model.rs`, `E/orders/receipts.rs`,
  `E/orders/error.rs`, `E/orders/validate.rs`, `E/orders/apply.rs`, `E/orders/attendance.rs`,
  `E/orders/digest.rs`. (`E/orders/staffing.rs` is created by Task 5, which first has something to put in it.)
- Create: `T/period_orders.rs`, `T/period_orders/support.rs`, `T/period_orders/payments.rs`.
- Modify: `E/lib.rs` (`mod orders;` beside the other `mod` lines; `pub use orders::{..}` of every public name
  below; `close_material_period_with_orders` in the `pub use transition::{..}` list, 121-125);
  `E/transition.rs` (`close_material_period_with_orders` in `pub use state::{..}`, 10-13);
  `E/model.rs` (`MaterialCircuitTransition`, 751-803: the field `orders` after `adjustments`);
  `E/transition/state.rs`: `ClosedMaterialPeriod` (621-627), `close_funded_production` (1641-1700),
  `close_support_parts` (1766-1842), `close_material_period_with_portfolios` and
  `close_material_period_with_standing` (1866-1907: pass `None`), the new entry beside them, `close_with_rules`
  (1921-2078, its transition literal 2014-2063);
  `E/payments/attendance.rs` (`fund_attendance`, 277-360);
  `E/recurring/households_tests.rs` (the call of `fund_attendance` at 315: pass `&OrderedHours::none()`);
  `E/staffing/place.rs` (`PlaceStaffingError`, 64-79);
  `W/runner/run.rs` (`place_error`, 541-551: one arm);
  `contracts/material_circuit_v4.yaml` and `E/wire/state.rs` (the digest).

**Interfaces:**

Consumes nothing.

Produces (names, fields and orders exactly as File Structure, "The engine's orders"):

```rust
// E/orders/model.rs
/// The orders of one period. Canonical: every list sorted by its key, no key twice (validate refuses).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PeriodOrders {
    pub period: u64,
    pub rates: Vec<RateOrder>,                // key (site_id, unit_id)
    pub withheld: Vec<WithheldOrder>,         // key member_id
    pub above_rolls: Vec<AboveRollsOrder>,    // key member_id
    pub floors: Vec<FloorOrder>,              // key pool_id
    pub moves: Vec<StaffingOrder>,            // key (host_pool, to_member, from_member)
    pub fund_payments: Vec<FundPaymentOrder>, // key (organization, household)
    pub wage_shares: Vec<WageShareOrder>,     // key (payer, organization)
}
impl PeriodOrders {
    /// Every list empty.
    #[must_use] pub const fn none(period: u64) -> Self;
    #[must_use] pub fn is_empty(&self) -> bool;
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RateOrder { pub site_id: SiteId, pub unit_id: UnitId, pub rate: Currency }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct WithheldOrder { pub member_id: StaffingMemberId, pub share_bps: u16 }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct AboveRollsOrder { pub member_id: StaffingMemberId, pub hours: u64, pub cause: AboveRollsCause }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AboveRollsCause { StruckWork, Named }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct FloorOrder { pub pool_id: StaffingPoolId, pub site_id: SiteId, pub unit_id: UnitId,
    pub persons: u64, pub paid_hours: u64 }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct StaffingOrder { pub host_pool: StaffingPoolId, pub to_member: StaffingMemberId,
    pub from_pool: StaffingPoolId, pub from_member: StaffingMemberId, pub persons: u64,
    pub kind: StaffingOrderKind }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum StaffingOrderKind { PlaceTaken, TakenOn }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct FundPaymentOrder { pub organization: OrganizationAccountId, pub household: FinalDemandPrincipalId,
    pub amount: Currency }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct WageShareOrder { pub payer: FinalDemandPrincipalId, pub organization: OrganizationAccountId,
    pub share_bps: u16 }

// E/orders/receipts.rs (each derives Clone, Debug, PartialEq, Eq; all but StaffingOrderReceipt and
// OrderReceipt also Copy)
pub enum OrderReceipt { Rate(RateReceipt), Withheld(WithheldReceipt), AboveRolls(AboveRollsReceipt),
    Floor(FloorReceipt), Staffing(StaffingOrderReceipt), FundPayment(FundPaymentReceipt),
    WageShare(WageShareReceipt) }
pub struct RateReceipt { pub period: u64, pub site_id: SiteId, pub unit_id: UnitId, pub old_rate: Currency,
    pub new_rate: Currency, pub rows: u32 }
pub struct WithheldReceipt { pub period: u64, pub member_id: StaffingMemberId, pub site_id: SiteId,
    pub payee: FinalDemandPrincipalId, pub rolls_hours: u64, pub withheld_hours: u64 }
/// `attended_hours`: the hours attended above the rolls, the member's attended hours beyond its rolls' hours
/// offered this period (the rolls' hours are attended first): `attended.saturating_sub(capacity -
/// withheld).min(hours)`.
pub struct AboveRollsReceipt { pub period: u64, pub member_id: StaffingMemberId, pub site_id: SiteId,
    pub payee: FinalDemandPrincipalId, pub hours: u64, pub attended_hours: u64, pub cause: AboveRollsCause }
pub struct FloorReceipt { pub period: u64, pub pool_id: StaffingPoolId, pub persons: u64,
    pub held: FloorHeld, pub paid_hours: u64 }
pub enum FloorHeld { Held, GaveWayToStop { limit: u64 } }
/// `moved`: the persons the order moved (or called back); `displaced`: those it displaced, by member. An order
/// that moves nothing still has its receipt, with `moved: 0`.
pub struct StaffingOrderReceipt { pub period: u64, pub order: StaffingOrder,
    pub household_id: FinalDemandPrincipalId, pub moved: u64, pub displaced: Vec<(StaffingMemberId, u64)> }
pub struct FundPaymentReceipt { pub period: u64, pub order: FundPaymentOrder, pub transfer_ordinal: u32 }
pub struct WageShareReceipt { pub period: u64, pub order: WageShareOrder, pub net_wages: Currency,
    pub amount: Currency, pub transfer_ordinal: Option<u32> }   // None: nothing owed (no pay)

// E/orders/error.rs (Clone, Copy, Debug, PartialEq, Eq; impl Display and std::error::Error)
pub enum PeriodOrderError {
    WrongPeriod { orders: u64, opening: u64 }, NotMonetary, NotCanonical, Arithmetic,
    UnknownSite(SiteId), RateNotPositive { site_id: SiteId }, NoWageAt { site_id: SiteId, unit_id: UnitId },
    UnknownMember(StaffingMemberId), ShareOutOfRange { member_id: StaffingMemberId, share_bps: u16 },
    NotAWage { member_id: StaffingMemberId },
    StruckWorkWithoutStoppage { site_id: SiteId },
    FillPassesWithheld { site_id: SiteId, withheld: u64, filled: u64 },
    OwnPeopleStopped { member_id: StaffingMemberId },
    StaffingWithoutSeekers,
    UnknownOrganization(OrganizationAccountId), UnknownHousehold(FinalDemandPrincipalId),
    PaymentNotPositive, FundShort { organization: OrganizationAccountId, cash: Currency, ordered: Currency },
    WageShareOutOfRange { payer: FinalDemandPrincipalId, share_bps: u16 },
    MoveFromNoReserve { from_member: StaffingMemberId, reserve: u64, persons: u64 },
    MoveOutOfPlace { host_pool: StaffingPoolId, from_pool: StaffingPoolId },
    DisplacesMoreThanStruck { host_pool: StaffingPoolId, struck: u64, persons: u64 },
    FloorNotThePool { pool_id: StaffingPoolId, site_id: SiteId },
    NotBuilt(OrderKind),                       // lifted task by task; removed by Task 5
}
/// Clone, Copy, Debug, PartialEq, Eq.
pub enum OrderKind { Rate, Withheld, AboveRolls, Floor, Staffing, FundPayment, WageShare }
/// Clone, Copy, Debug, PartialEq, Eq; Display, Error; From<MaterialCircuitError>, From<PeriodOrderError>.
pub enum OrderedCloseError { Circuit(MaterialCircuitError), Order(PeriodOrderError) }
// E/staffing/place.rs: PlaceStaffingError gains `Order(PeriodOrderError)` and From<PeriodOrderError>.

// E/model.rs, MaterialCircuitTransition gains, after `adjustments`:
/// What the orders of the period did, in the order they acted (ADR323). Empty unless the close was given
/// orders.
pub orders: Vec<OrderReceipt>,

// E/transition/state.rs
/// The close with the orders of the period. `standing` is `Some` exactly when the catalog asks for the stop
/// rule. With `PeriodOrders::none(opening.period)` it is the matching older entry, byte for byte.
/// # Errors
/// `Order(..)` for an order the opening refuses (E/orders/validate.rs), else as `close_material_period`.
pub fn close_material_period_with_orders(catalog: &MaterialCatalog, opening: &MaterialCircuitState,
    standing: Option<&WorkplaceStanding>, orders: &PeriodOrders)
    -> Result<ClosedMaterialPeriod, OrderedCloseError>;
// ClosedMaterialPeriod gains (private) `orders: Option<PeriodOrders>`: Some only when the orders are not empty.

// E/orders/digest.rs
/// SHA-256 of the canonical bytes of the orders (domain "babylon.period-orders.v1").
/// # Errors
/// `NotCanonical` for a list out of its key order or a key twice; `Arithmetic` for a list longer than u32.
pub fn period_orders_digest(orders: &PeriodOrders) -> Result<[u8; 32], PeriodOrderError>;

// E/orders/attendance.rs (crate-private; E/orders.rs re-exports it pub(crate))
pub(crate) struct OrderedHours { withheld_bps: BTreeMap<StaffingMemberId, u16>,
    above: BTreeMap<StaffingMemberId, u64>, paid_floor: BTreeMap<(SiteId, UnitId), u64> }
impl OrderedHours {
    pub(crate) const fn none() -> Self;
    /// `capacity - withheld_hours(capacity, bps) + above` of the member.
    pub(crate) fn offered(&self, member: StaffingMemberId, capacity: u64) -> Result<u64, MaterialCircuitError>;
    /// The least hours the (site, unit) plans to pay this period; 0 when no floor.
    pub(crate) fn paid_floor(&self, site: SiteId, unit: UnitId) -> u64;
}
/// `floor(capacity * share_bps / 10_000)`, in u128.
pub(crate) fn withheld_hours(capacity: u64, share_bps: u16) -> Result<u64, MaterialCircuitError>;
```

Later tasks rely on: every name above; `transition.orders`; `ClosedMaterialPeriod.orders`; `OrderedHours` and
`withheld_hours`; `PlaceStaffingError::Order`; `orders::validate::validate(catalog, opening, orders)`
(crate-private); the support helpers of `T/period_orders/support.rs` (Step 1).

- [ ] **Step 1: Write the test support** in `T/period_orders/support.rs` (the bench's `sets.rs:280-318` shows the
  pattern: a `Runner` for the opening of a period, then the engine's own entries):

  ```rust
  /// The account of the one organization the tests open: slot 0 of Task 2's `organization_account`.
  pub(crate) const ORGANIZATION: OrganizationAccountId = OrganizationAccountId::from_bytes([40; 32]);
  /// The opening of one period and everything a close and its staffing read.
  pub(crate) struct Period { pub world: World, pub catalog: MaterialCatalog, pub state: MaterialCircuitState,
      pub staffing: StaffingState, pub members: Vec<PoolMembers>, pub standing: WorkplaceStanding }
  /// A refusal of one step, by where it came from.
  #[derive(Debug, PartialEq)]
  pub(crate) enum Refused { Close(OrderedCloseError), Place(PlaceStaffingError), Finish(MaterialCircuitError) }
  /// A closed, staffed and finished period.
  pub(crate) struct Closed { pub transition: MaterialCircuitTransition, pub placed: PlaceStaffing }
  /// Period 1 of a world: `doubled::opening_state_of`, `staffing_of`, `pool_members_of`, `catalog_of(world,
  /// &world.opening_figures(), &world.rules)`, `WorkplaceStanding::opening()`.
  pub(crate) fn opening(world: &World) -> Period;
  /// The opening of the runner's next period: its state, staffing, members, standing, and the catalog
  /// `doubled::catalog_of(runner.world(), &runner.shocks().figures(p), &runner.rules_at(p))`, p = next period.
  pub(crate) fn of_runner(runner: &Runner) -> Period;
  /// `World { rules: vec![AdjustmentRule::SeekingInPlace], ..World::scene() }`: the fight's worlds staff in
  /// place (File Structure, "The engine's orders", its last paragraph).
  pub(crate) fn fund_world() -> World;
  /// The same state with one more cash account, `Organization(account)` holding `cash`, its location, and the
  /// cost book opened again from the new book. Only for an opening state: asserts period 1 and no purchase or
  /// shift in the book.
  pub(crate) fn with_organization(state: &MaterialCircuitState, account: OrganizationAccountId,
      cash: Currency) -> MaterialCircuitState;
  /// The new entry (standing `Some` when `period.catalog.market_clearing`'s adjustments ask for
  /// `StopWithoutPay`), then
  /// `staff_in_places(.., &doubled::places())` and `finish_with_place_staffing`.
  pub(crate) fn close(period: &Period, orders: &PeriodOrders) -> Result<Closed, Refused>;
  /// The opening after `closed`: its state, `placed.state`, `placed.members`, `placed.standing`, same catalog.
  pub(crate) fn next(period: &Period, closed: &Closed) -> Period;
  /// The cash of an account in a state.
  pub(crate) fn cash(state: &MaterialCircuitState, account: AccountId) -> Currency;
  ```

  `with_organization`: `let mut snapshot = economy.book.snapshot()`; push `CashAccount { id:
  AccountId::Organization(account), cash }`; `MonetaryBook::open(snapshot.accounts)`; `let costs =
  economy.costs.snapshot()`; `HistoricalCostBook::open(&book, costs.stocks, costs.freight, costs.equity,
  costs.equipment)` (`E/valuation/book.rs:47-80` gives every book account its capital row; at period 1 the
  opening capitals are the net assets, so every other row is as before). Also push `InstitutionLocation {
  account: AccountId::Organization(account), location: <the treasury's location, copied from
  economy.financial.locations> }` into `economy.financial.locations`, kept sorted by `account`: every close
  refuses a book whose organization or public accounts are not exactly the accounts of `financial.locations`
  (`E/financial/validation.rs:59-74`, through `begin_close` and `payments::validate`). Tests use `expect` with
  a reason.
- [ ] **Step 2: Write the failing tests** in `T/period_orders/payments.rs`. Unless named otherwise each opens
  `opening(&fund_world())` with its state replaced by `with_organization(&state, ORGANIZATION, $500)`; farm A
  is `Workplace { place: Place::A, kind: Kind::Farm }`, its workers `Household::Workers(farm_a).principal()`.
  - `empty_orders_close_as_the_older_entry`: the run of the client's proof of Task 7c (`PROOF_7C`,
    `babylon-client/src/small_world/script_tests.rs:385-402`): `Runner::open_world(&World::scene())`; before
    step index 20 `strike(HarvestFails, Places::A, UntilLifted)`; before step indices 30, 35, 40, 45 and 50
    `turn_on` `SeekingInPlace`, `HiringWithinMeans`, `StopWithoutPay`, `RestingPrice`, `OwnerRestart {
    outlay_periods: 1 }`; 70 steps. Before each step, with `p = of_runner(&runner)` and `stop_on` = the
    catalog's rules hold `StopWithoutPay`: the older entry (`close_material_period_with_standing(&p.catalog,
    &p.state, &p.standing)` when `stop_on`, else `close_material_period`) and
    `close_material_period_with_orders(&p.catalog, &p.state, stop_on.then_some(&p.standing),
    &PeriodOrders::none(p.state.period))` give equal `format!("{:?}")` (every field of the closed period); in
    periods whose rules hold `SeekingInPlace`, both are staffed and finished as `close` does and give equal
    `PlaceStaffing` and equal `MaterialCircuitTransition` (its `orders` empty), and after `runner.step()` the
    runner's `state_digest` equals `material_circuit_state_digest(&p.catalog, &transition.state)`. At the end,
    from `runner.history()`: at least one `AdjustmentReceipt::PlaceMove`, a `Stop` receipt in every period from
    41, and a `Restart` receipt with `RestartTest::Restarted`. Why this run: it meets the older entry without
    the seekers (1 to 30), with them (31 to 40), the stop rule's entry (41 to 70), the moves of the seekers, and
    a restart: the lead counted it on 24 November ("clinic A shut from 37 ... at the close of 53 its owners
    restart it", `docs/superpowers/plans/2026-11-23-adjust-2-the-closest-form.md`, "What Tasks 6 to 8c built").
    If a guard of the last sentence fails, stop and tell the lead: the run no longer meets what it must.
  - `the_orders_entry_refuses_the_stop_rule_without_its_memory`: `opening(&World { rules:
    vec![HiringWithinMeans, SeekingInPlace, StopWithoutPay], ..World::scene() })`; the new entry with standing
    `None` and `PeriodOrders::none(1)`: `Err(OrderedCloseError::Circuit(MaterialCircuitError::
    MarketClearingInvariant))`, as `close_material_period_with_portfolios` refuses (`state.rs:1877-1879`).
  - `a_fund_pays_a_household_at_the_opening`: one `FundPaymentOrder { organization: ORGANIZATION, household:
    farm A's workers, amount: $50 }`. In `transition.money_transfers`, the transfer `i` of purpose
    `Cash(MutualAid)` has debit `Cash(Organization(ORGANIZATION))` delta -$50 and credit
    `Cash(Household(farm A's workers))` +$50; `i` is after every `Cash(PublicTransfer)` and before the first
    `WagePayment(_)`. `transition.orders == [OrderReceipt::FundPayment(FundPaymentReceipt { period: 1, order,
    transfer_ordinal: i })]`. The organization's cash in `transition.state` is $450.
  - `dues_are_a_share_of_pay_net_of_tax`: one `WageShareOrder { payer: farm A's workers, organization:
    ORGANIZATION, share_bps: 1_000 }`. Farm A's workers earn $400 (40 hours at $10); the taxes to come are 5 %
    and 15 % of it, $20 and $60; net $320; the share $32. The receipt is `WageShareReceipt { period: 1, order,
    net_wages: $320, amount: $32, transfer_ordinal: Some(i) }`, transfer `i` is `Cash(MutualAid)` from the
    household to the organization and comes after every `WagePayment(_)`; the two `TaxReceipt`s of that payer
    still assess $20 and $60 (`taxable_amount` $400); the organization's closing cash is $532.
  - `no_pay_owes_no_dues`: a `WageShareOrder` from `Household::Supported(Place::A)` (no employment row):
    `WageShareReceipt { net_wages: $0, amount: $0, transfer_ordinal: None, .. }`, no `Cash(MutualAid)`
    transfer, the organization's cash $500.
  - `a_short_fund_is_refused_before_any_money_moves`: the organization opens with $100; payments of $60 to farm
    A's workers and $50 to clinic A's workers (key order: by household): `Err(Refused::Close(Order(FundShort {
    organization: ORGANIZATION, cash: $100, ordered: $110 })))`. One payment of exactly $100 closes. Two
    payments of `Currency::from_micro_units(i128::MAX)`: `Err(..Order(Arithmetic))`.
  - `a_payment_names_known_accounts_and_a_positive_amount`: organization `[41; 32]` (no account):
    `UnknownOrganization`; household `[99; 32]`: `UnknownHousehold`; amount $0: `PaymentNotPositive`; a wage
    share naming `[41; 32]`: `UnknownOrganization`; a wage share of unknown payer: `UnknownHousehold`; shares
    0 and 10_001: `WageShareOutOfRange { payer, share_bps }`.
  - `orders_of_another_period_are_refused`: `PeriodOrders::none(2)` at period 1: `Order(WrongPeriod { orders:
    2, opening: 1 })`.
  - `orders_out_of_order_are_refused`: two payments whose households come in descending order; the same key
    twice; two wage shares out of key order: each `Order(NotCanonical)`.
  - `orders_need_a_world_with_money`: the opening with `state.accounting = CircuitAccounting::PhysicalControl`
    and one fund payment: `Order(NotMonetary)`; the same state with `PeriodOrders::none(1)` is not refused by the
    orders (whatever the close then says is the older entry's).
  - `an_order_of_a_kind_not_built_is_refused`: one table row per kind not built: a `RateOrder` at farm A
    (`NotBuilt(OrderKind::Rate)`), a `WithheldOrder` (`Withheld`), an `AboveRollsOrder` (`AboveRolls`), a
    `FloorOrder` (`Floor`), a `StaffingOrder` (`Staffing`). Tasks 3, 4 and 5 delete their rows.
  - `money_is_conserved_with_payments`: periods 1 and 2 (`next`), each with a payment of $50 to
    `Household::Supported(Place::A)` and the dues of farm A's workers at 1,000 bps: in each transition
    `book.total_cash_and_reserves()` equals the opening state's; the organization's cash is $482 after period 1
    ($500 - $50 + $32) and $482 - $50 + that period's `WageShareReceipt.amount` after period 2.
  - `the_digest_reads_every_order`: an orders value with one row in each of the seven lists (any ids);
    `period_orders_digest` of it is `Ok`; changing the period, or any one field of any one row (each of the 25
    fields of the rows, cause and kind included, and the period), gives another digest; two
    `PeriodOrders::none(5)` give the same digest and `none(6)` another; a list out of key order is
    `Err(NotCanonical)`.
- [ ] **Step 3: Run them and see them fail:** `mise run rust:test:q -- -p babylon-material-circuit --test
  period_orders`. Expected: does not compile, no `PeriodOrders` and no `close_material_period_with_orders`.
- [ ] **Step 4: The types.** Write `E/orders/model.rs`, `receipts.rs`, `error.rs` and `E/orders.rs` as the
  Interfaces say; export them from `E/lib.rs`. Each type's doc comment carries its line of "The engine's
  orders" (PF1, PF2, PF3, PF12, PF13, PF18). `Display` of `PeriodOrderError`: one sentence a variant naming
  its fields, money as `{:?}` or its `micro_units()` (`Currency` has no `Display`), for example "the
  organization {organization:?} holds {cash:?} and is ordered to pay {ordered:?}"; of
  `OrderedCloseError`: "the close refused: {error:?}" and "the orders refused: {error}".
- [ ] **Step 5: The digest** in `E/orders/digest.rs`, with `babylon_kernel::content_digest::sha256_of` over these
  bytes (Designed: the domain and the layout are this plan's):

  ```text
  b"babylon.period-orders.v1\0", period u64 BE,
  then each list in field order: its length as u32 BE, then each row:
    rate          site 32, unit 32, rate i128 BE
    withheld      member 32, share_bps u16 BE
    above_rolls   member 32, hours u64 BE, cause u8 (1 StruckWork, 2 Named)
    floor         pool 32, site 32, unit 32, persons u64 BE, paid_hours u64 BE
    staffing      host_pool 32, to_member 32, from_pool 32, from_member 32, persons u64 BE,
                  kind u8 (1 PlaceTaken, 2 TakenOn)
    fund_payment  organization 32, household 32, amount i128 BE
    wage_share    payer 32, organization 32, share_bps u16 BE
  ids by `as_bytes()`; money by `micro_units()`.
  ```

  The canonical check (every list strictly increasing by its key) is one function in `E/orders/validate.rs`,
  `pub(crate) fn canonical(orders: &PeriodOrders) -> Result<(), PeriodOrderError>`, which both the digest and
  `validate` call.
- [ ] **Step 6: Validation**, `pub(crate) fn validate(catalog: &MaterialCatalog, opening: &MaterialCircuitState,
  orders: &PeriodOrders) -> Result<(), PeriodOrderError>` in `E/orders/validate.rs`, in this order (the first
  refusal is returned; nothing is changed):

  ```text
  1. orders.period != opening.period                              -> WrongPeriod { orders, opening }
  2. orders.is_empty()                                            -> Ok(())
  3. opening.accounting is not Monetary                           -> NotMonetary
  4. canonical(orders)                                            -> NotCanonical
  5. the first non-empty of rates, withheld, above_rolls, floors, moves -> NotBuilt(that kind)
  6. each fund payment, in key order:
       book.cash(Organization(o)) fails                           -> UnknownOrganization(o)
       household not in opening.final_demand_principals           -> UnknownHousehold(h)
       amount <= 0                                                -> PaymentNotPositive
  7. each organization, in key order: its amounts summed (checked -> Arithmetic) > its opening cash
                                                                  -> FundShort { organization, cash, ordered }
  8. each wage share, in key order: payer unknown -> UnknownHousehold; organization unknown ->
     UnknownOrganization; share_bps == 0 or > 10_000 -> WageShareOutOfRange { payer, share_bps }
  ```

- [ ] **Step 7: The entry and the threading** in `E/transition/state.rs`.
  - `close_material_period_with_orders`: if `standing` is `None` and the catalog asks for `StopWithoutPay`,
    `Err(Circuit(MarketClearingInvariant))`; then `orders::validate(catalog, opening, orders)?` (before
    `close_with_rules`, so before `CompanyInvestment::prepare`); then `close_with_rules(catalog, opening, (&[],
    &[], &[]), (None, &[]), standing, Some(orders))?`; set `orders: (!orders.is_empty()).then(||
    orders.clone())` on the closed period.
  - `close_with_rules` gains `orders: Option<&PeriodOrders>` (last); the two older callers pass `None`.
    `close_support_parts` gains the same and passes it to `close_funded_production`, which gains it too (its
    eighth parameter: `#[allow(clippy::too_many_arguments, reason = "the orders of the period join the inputs
    of the funded close")]`, as `recurring/firms.rs:761` does). `FundedProductionReceipts` (1630-1639) gains
    `orders: Vec<OrderReceipt>`; the transition literal sets `orders: close.funded.orders`.
  - In `close_funded_production`, behind `if let Some(orders) = orders` only: `orders::apply::pay_funds(state,
    costs, orders, money_transfers)?` right after `FinancialClose::opening`, pushing its receipts; and
    `orders::apply::take_wage_shares(state, costs, orders, wage_accruals, money_transfers)?` right after
    `costs.admit_attendance(attendance)` and before `HouseholdLists::open`. `fund_attendance` takes
    `&OrderedHours::none()` here in this task.
  - `ClosedMaterialPeriod` gains `orders: Option<PeriodOrders>`; the older entries set `None`.
  - Receipts stand in `transition.orders` in the order they acted: rates, fund payments, withheld, above the
    rolls, wage shares (the close), then floors and staffing orders (the staffing, appended at the finish); each
    kind in key order. The digest refuses orders out of key order (`NotCanonical`) rather than sorting them, and
    `NotMonetary` is read only for orders that are not empty.
- [ ] **Step 8: Payments** in `E/orders/apply.rs`:
  `pub(crate) fn pay_funds(state: &mut MaterialCircuitState, costs: &mut CostClose, orders: &PeriodOrders,
  money_transfers: &mut Vec<MoneyTransferReceipt>) -> Result<Vec<OrderReceipt>, MaterialCircuitError>`: in key
  order, `transfer_ordinal = u32::try_from(money_transfers.len())` (`RowLimit` if it does not fit), then
  `book.transfer_cash(Organization(o), Household(h), amount, CashTransferPurpose::MutualAid)` and
  `costs.cash_gift(Organization(o), Household(h), amount)`, as `E/collection.rs:565-575` does the other way.
  `pub(crate) fn take_wage_shares(state, costs, orders, wage_accruals: &[WageAccrualReceipt],
  money_transfers) -> Result<Vec<OrderReceipt>, MaterialCircuitError>`, each wage share in key order:

  ```text
  base   = sum of wage_accruals[..].amount with payee == Household(payer) and period == state.period
  taxes  = sum over economy.financial.taxes with payer == Household(payer) and basis == WageIncome
           of crate::financial::fraction(base, rate_bps, 10_000)
  net    = max(base - taxes, 0)
  amount = crate::financial::fraction(net, share_bps, 10_000)
  amount == 0: receipt with transfer_ordinal None, nothing moves
  else: transfer_cash(Household(payer), Organization(o), amount, MutualAid); costs.cash_gift(same);
        receipt with Some(ordinal)
  ```

  The base is the period's wage accruals, not `costs.tax_base`: wage income enters the cost book only in
  `close_household_reproduction` (`costs.payroll`, `state.rs:1541`), after the purchases; `collect_taxes`
  (`E/financial/close.rs:292-294`) will tax the same sum for a household paid only through attendance. A
  share of wages is taken when wages are paid: paying into a fund in the making (PF18) and dues that an employer
  collects under a contract (PF12); a member's own dues, paid at the close from what is left after it has
  bought, are an act of Part Two.
- [ ] **Step 9: Hours threaded.** `E/orders/attendance.rs`: `OrderedHours` and `withheld_hours` as the
  Interfaces say. `fund_attendance(state, transfers, accruals, hours: &OrderedHours)`: each member's
  `available` becomes `hours.offered(member, capacity)?`; `planned` (322-334) becomes
  `plan.planned_hours.max(hours.paid_floor(site, unit)).min(offered_total)` with a recurring economy and
  `offered_total` without one, `offered_total` the sum of the members' offered hours;
  `proportional_shares(planned, &offered)`; `fund_member_attendance` is unchanged. With `none()` every
  `offered` is the capacity and the floor 0, and a validated state's labor row equals its members' sum
  (`validate_member_budgets`, `E/payments/settlement.rs:88-138`), so nothing moves.
- [ ] **Step 10: The two refusals outside the orders.** `PlaceStaffingError::Order(PeriodOrderError)` with its
  `From`. In `W/runner/run.rs` `place_error`, the arm `PlaceStaffingError::Order(_) => engine_error(period,
  Stage::StaffInPlaces, MaterialCircuitError::MarketClearingInvariant)`, with a comment that the runner gives no
  orders before Task 2, which gives the arm `RunnerError::Orders`.
- [ ] **Step 11: Run the tests and see them pass:** `mise run rust:test:q -- -p babylon-material-circuit --test
  period_orders`. Expected: all pass. If `empty_orders_close_as_the_older_entry` differs in a period, the
  first differing field of the two `Debug` strings names the step that is not behind `if let Some(orders)`.
- [ ] **Step 12: The contract.** Add a top-level mapping before the comment `# Households buy in tiers (O7,
  O8)...` (line 304), and recompute the digest:

  ```yaml
  # The pay fight (ADR323): the orders of one period. A close that is given none keeps today's bytes.
  period_orders:
    ADR323_orders: >-
      a close may be given the orders of its period: rates, hours withheld, hours above the rolls, floors on
      the rolls, staffing moves, payments from a fund and shares of wages, each list in the order of its key
      with no key twice; the orders are refused as a whole, before anything closes, when one names what the
      opening does not hold, and a kind not yet built is refused; the engine keeps nothing of an order after
      its period, and each order has a receipt; a payment from a fund goes from an organization's account to
      a household after the public programs and before wages, and an organization's payments of a period sum
      to no more than its cash at the opening; a share of wages goes from a household to an organization when
      wages are paid and before any purchase, as the share of that period's wages net of the wage taxes to
      come, and nothing when there are no wages (paying into a fund in the making and dues an employer
      collects; a member's own dues at the close come later); both are mutual aid; the orders have a digest of their own
      (domain babylon.period-orders.v1); the state's digest reads only what they change; empty orders close
      as the entry without orders, byte for byte
  ```

- [ ] **Step 13: Run the scoped engine gate.** Then, in the background (Global Constraints), the 14 long tests
  (expected: 14 of 14; this task threads the close and the attendance of every world, and
  `empty_orders_close_as_the_older_entry` compares the two entries with each other, not with the bytes of
  before). The live database tests are the lead's.
- [ ] **Step 14: Commit** `feat(material-circuit): the orders of a period, and payments to and from a fund`. The
  body says: a close may be given the orders of its period; they are checked against the opening as a whole and
  answered with receipts in the transition; payments from a fund at the opening and shares of wages when wages
  are paid are built, as mutual aid; the other kinds are refused until their tasks; the orders have their own
  digest; empty orders close byte for byte as the older entries, over a run with the seekers, the stop rule and
  a restart; the contract line and its digest change together. `Part of PER-371`.

**What this task must not do:**
- Touch anything under `babylon-tick`, `babylon-persistence` or `babylon-practice-contract`; add a field to
  `MaterialCircuitState`, `MonetaryCircuit`, `FinancialInstitutions`, `EmploymentTerms`,
  `MemberLaborUseReceipt` or the catalog; add a `CashTransferPurpose`, an `AdjustmentReceipt` variant or a
  `MaterialCircuitError` code.
- Run any new step outside `if let Some(orders)`; change what the older entries do; give the runner an order.
- Use `costs.tax_base` for the base of a share of wages (it is 0 at that point of the close).
- Leave the orders on the closed period when they are empty.

---

### Task 2: A world asks for the fight at its opening

Commit `feat(circuit-worlds): a world asks for the pay fight at its opening`.

**Files:**
- Create: `W/fight.rs` (`mod` and `pub use` only); `W/fight/world.rs`; `W/fight/organization.rs`;
  `W/fight/payments.rs`; `W/fight/period.rs`; `rust/crates/babylon-circuit-worlds/tests/fight.rs`.
- Modify: `W/lib.rs` (`pub mod fight;`, `pub use fight::{Employers, Fight, FightOpening, OrganizationOpening};`);
  `W/ids.rs` (after `fund()`, 335-339: `OrganizationSlot`, `organization_account`); `W/error.rs` (`WorldError`,
  its `Display`); `W/doubled/world.rs` (`World` 57-67 gains `fight`; `scene()` 80-87; `scene_with_fight()`);
  `W/doubled/opening.rs` (`cash_accounts` 158-181; `financial` 490-509: the organizations' locations; `wage`
  139-145 becomes `pub(crate)`);
  `W/runner/result.rs` (`PeriodResult` 18-38 gains `fight`; `PeriodReceipts` 42-69 gains `orders`);
  `W/runner/error.rs` (`Stage::Orders`, `RunnerError::{Orders, Fight}`, their words); `W/runner/run.rs` (the
  `Runner` struct 59-72 and `Stepped` 20-26 gain `fight`; `open_world` 89-122; `step` 191-215; `advance` 339-428;
  `place_error` 541-550; `take_receipts` 828-856); `W/runner/hours.rs` (one unit test, the file stored hours
  made); `rust/crates/babylon-circuit-worlds/tests/worlds.rs` (literals 30 and 39);
  the bench's `runs.rs` (the literal in `run`, 88).

**Interfaces:**

Consumes (engine, Task 1): `PeriodOrders` (`none(period)`, `is_empty()`), `FundPaymentOrder`, `OrderReceipt`,
`PeriodOrderError`, `OrderedCloseError::{Circuit, Order}`, `PlaceStaffingError::Order`,
`MaterialCircuitTransition.orders: Vec<OrderReceipt>`, `period_orders_digest(&PeriodOrders) -> Result<[u8; 32],
PeriodOrderError>`, `close_material_period_with_orders(catalog, opening, standing: Option<&WorkplaceStanding>,
orders) -> Result<ClosedMaterialPeriod, OrderedCloseError>`. Stored hours: `HoursLedger::open(catalog, state)`,
`HoursLedger::fold(&self, world, catalog, before, transition) -> Result<(Self, PeriodHours), RunnerError>`,
`PeriodHours::household(Household) -> Option<&HouseholdHours>`, `HouseholdHours.{back_micro_hours, claims}`.

Produces:

```rust
// W/fight/world.rs
#[derive(Clone, Debug, PartialEq, Eq)] pub enum Fight { Absent, Asked(FightOpening) }
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FightOpening { pub organizations: Vec<OrganizationOpening>, pub employers: Employers }
/// How the employers of a world that asks answer what their people would ask.
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum Employers {
    /// PF7: each employer by its own count over the last year (the game's rule; `scene_with_fight()`).
    ByTheirCount,
    /// Designed, a labelled figure of the bench and never of the scene: what the people of a workplace would ask
    /// is offered at once, with no stoppage. It measures what rises that follow needs do; it is no rule of the game.
    OfferAtOnce }
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OrganizationOpening { pub line: Line, pub fund: Currency, pub members: Vec<Household> }
/// Designed (PF18, call 28): accounts kept for founding, a ceiling of the build.
pub const FOUNDING_ACCOUNTS_PER_WORKPLACE: usize = 2;
impl World { #[must_use] pub fn with_fight(self, opening: FightOpening) -> Self; }
/// Designed (A15, call 38): a step of pay at the small figures, millionths of a dollar ($1 an hour).
pub const PAY_STEP_MICRO: i128 = 1_000_000;
/// Designed (call 38): at the national figures a step is 250 basis points of the workplace's opening wage.
pub const NATIONAL_PAY_STEP_BPS: i128 = 250;
/// The step of pay at a workplace: $1 small; 250 bps of its opening wage (`doubled::opening::wage`), rounded
/// down to the micro-unit, national ($0.25 at $10, $0.275 at the clinic's $11 under P4).
#[must_use] pub fn pay_step(world: &World, workplace: Workplace) -> Currency;
/// The organization accounts a world opens, asked ones first in their order, then the kept ones, each with its
/// opening cash (a kept account opens with none). Empty for `Fight::Absent`.
/// # Errors  `WorldError::TooManyOrganizations` past the slots of `OrganizationSlot::new`.
pub(crate) fn organization_accounts(world: &World) -> Result<Vec<(OrganizationAccountId, Currency)>, WorldError>;
// W/ids.rs
/// The slot of an organization account: 0 to 87, so that its byte (40 + slot) stays below 128 as every identity
/// byte of this world does (`byte`, 71-78).
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)] pub struct OrganizationSlot(u8);
impl OrganizationSlot {
    /// # Errors  `WorldError::TooManyOrganizations` for an index above 87.
    pub fn new(index: usize) -> Result<Self, WorldError>;
    #[must_use] pub const fn index(self) -> usize;
}
/// 32 copies of byte 40 + slot.
#[must_use] pub const fn organization_account(slot: OrganizationSlot) -> OrganizationAccountId;
// W/error.rs, WorldError gains
FightNeedsSeekers, TooManyOrganizations,
// W/doubled/world.rs
pub struct World { /* as today */ pub fight: Fight }   // scene(): `fight: Fight::Absent`
/// The scene's world with the seekers on and the fight asked for, with no organization (Part One).
#[must_use] pub fn scene_with_fight() -> World;
// W/fight/organization.rs
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)] pub struct OrganizationId(pub u8);
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum Line { Yours, Union, Founded, Other }
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum OrganizationStanding { Kept, Alive { since: u64 }, Dead { since: u64 } }
#[derive(Clone, Debug, PartialEq, Eq)] pub struct Organization { pub id: OrganizationId,
    pub account: OrganizationAccountId, pub line: Line, pub members: Vec<Household>,
    pub standing: OrganizationStanding }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Membership { pub household: Household, pub organization: OrganizationId, pub since: u64 }
// W/fight/payments.rs
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum FundPaymentKind { Dues, PayingIn, StrikePay, Relief, Refund }
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub struct PaymentRecord { pub period: u64, pub kind: FundPaymentKind,
    pub organization: OrganizationId, pub household: Household, pub amount: Currency }
// W/fight/period.rs
/// What the fight did in one period. Part One's later tasks add, in this order of fields: `decisions` after
/// `orders_digest` (Task 8), `employers`, `offered`, `stoppages` after `payments` (Task 8), `measures`, `news`
/// before `organizations` (Task 6).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PeriodFight { pub orders: PeriodOrders, pub orders_digest: [u8; 32], pub payments: Vec<PaymentRecord>,
    pub organizations: Vec<(Organization, Currency)> }
#[derive(Clone, Debug, PartialEq, Eq)] pub struct FightBook { organizations: Vec<Organization>, rule: Employers }
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum FightError { Arithmetic, UnknownHousehold(Household), NoReceipt(String), AccountsFull,
    Order(PeriodOrderError) }                       // impl Display, Error, From<PeriodOrderError>
pub(crate) struct DecideView<'a> { pub(crate) world: &'a World, pub(crate) period: u64,
    pub(crate) state: &'a MaterialCircuitState, pub(crate) members: &'a [PoolMembers],
    pub(crate) last: Option<&'a PeriodResult>, pub(crate) history: &'a [PeriodResult] }
/// `result` is the closed period's, built before step 1 with `fight: None`; `history` the periods before it;
/// `state` the next state.
pub(crate) struct ClosedView<'a> { pub(crate) period: u64, pub(crate) result: &'a PeriodResult,
    pub(crate) history: &'a [PeriodResult], pub(crate) state: &'a MaterialCircuitState }
/// Task 8 adds `decisions: Vec<HouseholdDecision>` after `orders`.
pub(crate) struct Decided { pub(crate) book: FightBook, pub(crate) orders: PeriodOrders,
    pub(crate) payments: Vec<PaymentRecord> }
pub(crate) fn open(world: &World) -> Result<Option<FightBook>, WorldError>;
pub(crate) fn decide(book: &FightBook, view: &DecideView<'_>) -> Result<Decided, FightError>;
pub(crate) fn close(decided: Decided, closed: &ClosedView<'_>) -> Result<(FightBook, PeriodFight), FightError>;
// W/runner/result.rs
PeriodResult { /* as today, then stored hours' `hours` */ pub fight: Option<PeriodFight> }
PeriodReceipts { /* as today */ pub orders: Vec<OrderReceipt> }   // after `adjustments`
// W/runner/error.rs
Stage::Orders            // words: "the close with its orders"
RunnerError::Orders { period: u64, error: PeriodOrderError }
RunnerError::Fight { period: u64, error: FightError }
```

`payments` is empty in Part One; `organizations` lists every organization account the world opened, the 16 kept
ones of `scene_with_fight()` among them (`Line::Founded`, `OrganizationStanding::Kept`, $0), which the scene does
not draw.

`W/fight.rs` holds `pub mod organization; pub mod payments; pub mod period; pub mod world;`, the `pub use` of
every public type above, and `pub(crate) use period::{close, decide, open, ClosedView, DecideView, Decided};`, so
the runner calls `fight::decide(..)`.

- [ ] **Step 1: Pin the bytes before anything changes.** On the code as it stands, before any edit of this task,
  create `tests/fight.rs` with this one test and a helper `fn hex(bytes: &[u8; 32]) -> String` (`{b:02x}` per
  byte):

  ```rust
  /// A world that does not ask steps as before: digests pinned from a run of the code before Task 2.
  const SCENE_34: &str = "";            // filled in Step 2
  const DOWN_FUND_P2_34: &str = "";     // filled in Step 2
  #[test]
  fn a_world_that_does_not_ask_steps_as_before() -> TestResult {
      let mut scene = Runner::open_world(&World::scene())?;
      let mut down = Runner::open_world(&World { rules: World::switches_at(Scale::Small).to_vec(),
          ..World::scene() })?;
      down.strike(Shock::HarvestFails, Places::Both, Lasts::UntilLifted)?;
      for _ in 0..34 { scene.step()?; down.step()?; }
      let last = |r: &Runner| r.history().last().map(|p| hex(&p.state_digest)).unwrap_or_default();
      eprintln!("scene 34: {}\ndown fund-P2 34: {}", last(&scene), last(&down));
      assert_eq!(last(&scene), SCENE_34);
      assert_eq!(last(&down), DOWN_FUND_P2_34);
      Ok(())
  }
  ```

  The literal `World { rules, ..World::scene() }` compiles before and after this task.
- [ ] **Step 2: Read the two digests and pin them.** Run `mise run rust:test:q -- -p babylon-circuit-worlds -E
  'test(a_world_that_does_not_ask_steps_as_before)' --no-capture`. Expected: it fails on the empty constants and
  prints two lines of 64 hex characters. Copy each into its constant; run again: it passes. Do not change these two
  constants after this step.
- [ ] **Step 3: Write the failing tests.** In `tests/fight.rs`, beside Step 1's test. `seekers()` is
  `World { rules: vec![AdjustmentRule::SeekingInPlace], ..World::scene() }`; `yours(fund)` is
  `FightOpening { organizations: vec![OrganizationOpening { line: Line::Yours, fund, members: vec![] }],
  employers: Employers::ByTheirCount }`; `none()` is `FightOpening { organizations: vec![], employers:
  Employers::ByTheirCount }`.
  - Add to Step 1's test, for the scene's runner: every `result.fight` is `None` and every
    `result.receipts.orders` is empty.
  - `a_fight_world_opens_its_kept_accounts`: `doubled::opening_state_of(&seekers().with_fight(yours(dollars(500))))`.
    Its book's `AccountId::Organization` accounts, in order, are `organization_account(OrganizationSlot::new(i)?)`
    for i in 0..17, with cash $500 for slot 0 and $0 for slots 1 to 16; each of the 17 has an `InstitutionLocation`
    in `financial.locations`; `total_cash_and_reserves()` is `OPENING_MONEY + 500_000_000`; the other accounts and
    their cash are those of `opening_state_of(&seekers())`. With `none()`: 16
    accounts, slots 0 to 15, all $0, and the total is `OPENING_MONEY`.
  - `a_fight_world_without_seekers_is_refused`: `Runner::open_world(&World::scene().with_fight(none()))` is
    `Err(RunnerError::World(WorldError::FightNeedsSeekers))`. With 72 organizations (each `line: Line::Other`, fund $0)
    the seekers' world opens; with 73, `opening_state_of` is `Err(WorldError::TooManyOrganizations)`.
  - `a_fight_world_with_empty_orders_steps_as_the_same_world_without_orders`: `world = World::scene_with_fight()`;
    a runner of it, stepped 34 times, against a loop of the engine's older entry on the same world:

    ```rust
    let catalog = doubled::catalog_of(&world, &Figures::OPENING, &[AdjustmentRule::SeekingInPlace])?;
    let mut state = doubled::opening_state_of(&world)?;
    let (_, mut staffing) = doubled::staffing_of(&world)?;
    let mut members = doubled::pool_members_of(&world)?;
    for _ in 0..34 {
        let result = runner.step()?.clone();
        let closed = engine::close_material_period(&catalog, &state).map_err(|e| format!("{e:?}"))?;
        let placed = closed.staff_in_places(&catalog, &staffing, &members, &doubled::places())
            .map_err(|e| format!("{e:?}"))?;
        let transition = closed.finish_with_place_staffing(&catalog, &placed).map_err(|e| format!("{e:?}"))?;
        let digest = engine::material_circuit_state_digest(&catalog, &transition.state)
            .map_err(|e| format!("{e:?}"))?;
        assert_eq!(digest, result.state_digest, "period {}", result.period);
        let fight = result.fight.as_ref().ok_or("a fight world records its fight")?;
        assert!(fight.orders.is_empty() && fight.payments.is_empty(), "period {}", result.period);
        assert_eq!(fight.orders_digest, engine::period_orders_digest(&fight.orders).map_err(|e| format!("{e}"))?);
        (state, staffing, members) = (transition.state, placed.state, placed.members);
    }
    ```

  - `money_and_people_are_conserved_with_accounts`: `seekers().with_fight(yours(dollars(500)))`, the harvest
    struck in `Places::Both` until lifted before step 1, 60 steps, each `Ok`. Every period:
    `summary.total_money == OPENING_MONEY + 500_000_000`, `summary.persons == 80`, slot 0's cash in
    `closing.cash` is $500 and each kept account's $0, and `fight.organizations` lists the 17 accounts in slot
    order with those amounts (slot 0 `Line::Yours`, `Alive { since: 1 }`; the others `Line::Founded`, `Kept`).
  - `a_step_of_pay_is_a_dollar_or_a_fortieth_of_the_wage`: `pay_step(&World::scene(), SHOP_A) == $1`; at
    `Scale::National` `$0.25` (250,000 micro) for the shop; with `pushed: Some(Pushed { push:
    OpeningPush::HigherPay, places: Places::Both })` at `Scale::National`, `$0.275` (275,000 micro) for `CLINIC_A`
    and `$0.25` for `SHOP_A`.
  - In `W/runner/hours.rs`'s test module: `a_fight_world_folds_its_payments`. No hook in `decide`: the test closes
    period 1 itself with one payment and folds it.

    ```rust
    let world = World { rules: vec![SeekingInPlace], ..World::scene() }.with_fight(FightOpening {
        organizations: vec![OrganizationOpening { line: Line::Yours, fund: dollars(500), members: vec![] }],
        employers: Employers::ByTheirCount });
    let catalog = doubled::catalog_of(&world, &Figures::OPENING, &[SeekingInPlace])?;
    let state = doubled::opening_state_of(&world)?;
    let (_, staffing) = doubled::staffing_of(&world)?;
    let members = doubled::pool_members_of(&world)?;
    let shop_a = Household::Workers(Workplace { place: Place::A, kind: Kind::Shop });
    let orders = PeriodOrders { fund_payments: vec![FundPaymentOrder { organization:
        ids::organization_account(OrganizationSlot::new(0)?), household: shop_a.principal(),
        amount: dollars(100) }], ..PeriodOrders::none(1) };
    // close with `orders`, staff_in_places, finish_with_place_staffing; then
    let ledger = HoursLedger::open(&catalog, &state)?;
    let (_, hours) = ledger.fold(&world, &catalog, &state, &transition)?;
    ```

    Assert: the shop's workers' `claims.support > 0`, `claims.work > claims.support` ($400 of wages against $100
    of support in its purse), `claims.owning == 0`, `claims.not_recorded == 0`, and the four add up to
    `back_micro_hours`. The same close with `PeriodOrders::none(1)` gives `claims.support == 0`.
- [ ] **Step 4: Run them and see them fail:** `mise run rust:test:q -- -p babylon-circuit-worlds -E 'test(fight) |
  test(folds_its_payments) | test(step_of_pay)'`. Expected: does not compile (no `Fight`, no `with_fight`, no field
  `fight`, no `organization_account`). Step 1's test is not among the failures once the rest compiles.
- [ ] **Step 5: Implement the names and the world** in `W/ids.rs`, `W/error.rs`, `W/fight/world.rs`,
  `W/fight/organization.rs`, `W/fight/payments.rs`, `W/doubled/world.rs`. `World::scene()` gains
  `fight: Fight::Absent` (it stays `const fn`). `scene_with_fight()` is `World { rules: vec![SeekingInPlace],
  fight: Fight::Asked(FightOpening { organizations: Vec::new(), employers: Employers::ByTheirCount }),
  ..World::scene() }`. `pay_step` reads `doubled::opening::wage` (made `pub(crate)`): `dollars(1)` at
  `Scale::Small`, else `wage * NATIONAL_PAY_STEP_BPS / 10_000` in micro-units, rounded down. Words:
  `FightNeedsSeekers`: "the pay fight needs people who look for work in their place: open the world with the
  seekers"; `TooManyOrganizations`: "a world keeps at most 88 organization accounts".
- [ ] **Step 6: Open the accounts** in `W/doubled/opening.rs`: `cash_accounts` appends
  `fight::world::organization_accounts(world)?` as `CashAccount { id: AccountId::Organization(id), cash }` after
  the public accounts; `financial` adds an `InstitutionLocation { account: AccountId::Organization(id), location:
  ids::location()? }` for each, before the public accounts' locations, so `locations` stays sorted by account
  (organization accounts sort before public ones; `canonicalize`, `E/financial/validation.rs:14-15`). The engine
  refuses a book whose organization or public accounts have no location (`E/financial/validation.rs:64-74`), in
  the plain world too. For `Fight::Absent` both functions add nothing, so the book, the cost book and every digest
  are as today.
- [ ] **Step 7: The book and its three functions** in `W/fight/period.rs`. `open`: `None` for `Absent`; for `Asked`,
  `FightNeedsSeekers` unless `world.rules` contains `AdjustmentRule::SeekingInPlace`; then one `Organization` for each
  account of `organization_accounts` (asked: `OrganizationId(slot)`, its line and members, `Alive { since: 1 }`; kept:
  `Line::Founded`, no members, `Kept`); `rule` is the opening's `employers`. `decide` (Part One so far): `Decided {
  book: book.clone(), orders: PeriodOrders::none(view.period), payments: Vec::new() }`. `close`: `orders_digest` is
  `period_orders_digest(&decided.orders)?`; `organizations` is each organization with its cash in
  `closed.result.closing.cash` (an account missing there is `FightError::NoReceipt`). `FightError` words: "a sum or
  product of the pay fight overflowed"; "the pay fight met a household the world does not hold: {label}"; "the pay fight
  found no receipt of {what}"; "every account kept for founding is in use"; and the order's own words.
- [ ] **Step 8: The runner** in `W/runner/{result,error,run}.rs`. `Runner` and `Stepped` gain
  `fight: Option<FightBook>`; `open_world` sets it from `fight::open(world)?` (so `open_world_with_hours` carries
  it too); `step` keeps `stepped.fight` with the state, only on `Ok`. `advance` is that of File Structure, "The
  small worlds' new modules": the `PeriodResult` is built with `fight: None` before step 1, and step 1 reads it.

  ```rust
  let decided = match &self.fight { None => None, Some(book) => Some(fight::decide(book, &DecideView {
      world: &self.world, period, state: &self.state, members: &self.members,
      last: self.history.last(), history: &self.history }).map_err(|error| RunnerError::Fight { period, error })?) };
  // close: `None` keeps run.rs:358-363 exactly; `Some(d)` calls close_material_period_with_orders(catalog,
  // &self.state, stop_on.then_some(&self.standing), &d.orders).map_err(|e| ordered_error(period, e))?
  // ... staffing, check_conserved, stored hours' fold, digest, read_closing: as today ...
  let mut result = PeriodResult { period, figures, rules, members: staffed.members, closing, summary,
      state_digest, asked: staffed.asked, receipts: take_receipts(&transition), hours, fight: None };
  let book = match decided { None => None, Some(d) => {
      let (book, record) = fight::close(d, &ClosedView { period, result: &result, history: &self.history,
          state: &transition.state }).map_err(|error| RunnerError::Fight { period, error })?;
      result.fight = Some(record);
      Some(book) } };
  ```

  `ordered_error`: `OrderedCloseError::Circuit(e)` is `RunnerError::Engine { period, stage: Stage::Orders, error:
  e }`; `OrderedCloseError::Order(e)` is `RunnerError::Orders { period, error: e }`. The arm Task 1 added to
  `place_error` for `PlaceStaffingError::Order(e)` now returns `RunnerError::Orders { period, error: e.clone() }`.
  `take_receipts` gains `orders: transition.orders.clone()`. Words: `Orders`: "Period {period}: the engine refused
  the period's orders: {error}"; `Fight`: "Period {period}: the pay fight refused: {error}".
- [ ] **Step 9: The literals.** `tests/worlds.rs` 30 and 39 and the bench's `runs.rs` 88 gain `fight:
  Fight::Absent`. The literals of `sets.rs` 231, 261, 282 and of the client's `marks.rs` 504, 645, 1218 use
  `..World::scene()` and need nothing.
- [ ] **Step 10: Run them and see them pass:** the command of Step 4, then `mise run rust:test:q -- -p
  babylon-circuit-worlds`. Expected: all pass, Step 1's pins unchanged.
- [ ] **Run the gate:** the small worlds' gate; then, in the background, the 14 long tests and
  `hours_fold_every_reference_run`. Expected: 25 of 25 in each `reproduces_` set; the hours fold passes.
- [ ] **Commit** the subject above. The body says: a world asks for the fight at its opening and opens the
  accounts it asks for and 16 kept for founding, with their locations; a world that does not ask keeps every byte
  (the two pinned digests, the 14 long tests); the runner decides before the close and closes with the orders
  entry, and records `PeriodFight`; `decide` gives no order yet; the step of pay of each workplace; how the
  employers answer (`Employers`). Ends with `Part of PER-371` and the `Co-Authored-By` line.

**What this task must not do:**
- Add an account, a location or any byte for `Fight::Absent`; touch the catalog; add a `CashTransferPurpose`.
- Call the orders entry, or any fight code, when `self.fight` is `None`.
- Add a test-only hook to `decide` or a setter of the runner's state.
- Give "yours" a fund figure in `scene_with_fight()` (the plan's "Calls of the lead", 4: Part Two).
- Change anything under `babylon-tick`, `babylon-persistence` or `babylon-practice-contract`.

---

### Task 2c: The pay fight's switch and its tab

After this task a person at the window sees a third tab, "Fight", in the rail's lower part. On it a switch,
"The pay fight: from the opening (starts over)", starts a new run of the scene's world with the fight asked for:
people look for work in their place from the opening, the switch is marked, and the tab says "The pay fight is on
from the opening. Start over to leave it." Part One's scene has no organization: "yours" and its fund come with
Part Two's first task. The tab's lines of what happens come with the tasks that make them: the news (6c), the
stoppage and both counts (8c). Nothing on the plane moves differently.

**What the fight world's kept accounts need of the client: nothing.** A fight world's book holds 16 organization
accounts with no cash (two for each workplace, kept for organizations founded in play). No path of the client meets
them: `reading::read_payments` (reading.rs:252-319) reads only money transfers, and none moves on those accounts;
`read_goods` (208-237) reads sites and buyers of goods; `inspect::cash_row` (inspect.rs:167-178) and
`frame::capital_of` (frame.rs:810-824) look up one known party's account with `find`, never walk the book;
`marks::owner_rows` (marks.rs:157-166) compares `Party::from_account` with `Some(..)`, so `None` adds no row;
`table.rs` sums the reading only; `controls.rs` reads bodies. So `Party` is left as it is, and the test
`a_fight_world_with_no_organization_reads_and_draws` proves it on the fight world's first periods.

**Files:**
- Create: `C/fight.rs` (the Fight tab: its switch, its state line, its body; tests in its own `mod tests`).
- Modify:
  - `rust/crates/babylon-client/src/small_world.rs`: `pub mod fight;`.
  - `C/panel.rs`: `Lower` (50-55) gains `Fight`; `spawn_lower` (461-518) spawns a third tab and a third
    `LowerBody`; `lower_caption` (906-916); `paint_lower` (919-958); `view_index` (589) becomes `pub(super)`.
  - `C/scene.rs`: `SceneCommand` (96-111) gains `StartOverWithFight`; `open_runner_of`; `Stage::start_over_with`;
    `Stage::handle` (593-620); `SmallWorldPlugin::build` (261-312) adds `fight::pressed` as an observer and
    `fight::paint_fight` to the `Paint` chain after `rules::paint_rules`. The chain holds 18 systems at 98a0e3624
    and stored hours' Tasks 5 and 6 add two; Bevy's system tuples stop at 20, so if the chain already holds 20,
    `(rules::paint_rules, fight::paint_fight)` becomes one element of it.
  - `C/script.rs`: `ScriptCommand` (34-66) gains `Fight(String)`; `lower_named` (128-134) knows `"fight"`;
    `check_names` (149-193); `begin` (519-610).
  - Test: `C/scene_tests.rs` (the pin at 1195, two new tests), `C/script_tests.rs`, `C/frame.rs` (the frames'
    pin), `C/fight.rs`.
- The `World { .. }` literals of `C/marks.rs` (504, 645, 1218) use `..World::scene()` and need nothing.

**Interfaces:**

Consumes (Task 2; stored hours' Task 3):
```rust
// babylon_circuit_worlds
impl World { #[must_use] pub fn scene_with_fight() -> World; }   // the scene's world, seekers on, the fight asked
pub struct World { /* .. */ pub fight: Fight }
pub enum Fight { Absent, Asked(FightOpening) }
// PeriodResult.fight: Option<PeriodFight>, Some exactly in a fight world (orders, orders_digest, payments and
// organizations after Task 2; in Part One payments is empty and organizations holds the 16 kept accounts)
// stored hours, Task 3: Runner::open_world_with_hours(world: &World) -> Result<Runner, RunnerError>
```

Produces:
```rust
// C/panel.rs
pub enum Lower { #[default] Shocks, Rules, Fight }
pub(super) fn view_index(view: &PanelView, closed: usize) -> Option<usize>;
// C/scene.rs
pub enum SceneCommand { /* .. */ StartOverWithFight }
/// The scene's runner of `world`, with the hours ledger. `open_runner()` is `open_runner_of(&World::scene())`.
/// # Errors
/// As `Runner::open_world_with_hours`.
pub fn open_runner_of(world: &World) -> Result<Runner, RunnerError>;
// C/fight.rs
pub const FIGHT_SWITCH: &str = "The pay fight: from the opening (starts over)";
pub const FIGHT_OFF_LINE: &str = "No pay fight in this run.";
pub const FIGHT_ON_LINE: &str = "The pay fight is on from the opening. Start over to leave it.";
pub const FIGHT_LINE: &str = "Every household decides for itself what it does.";
#[derive(Component, Clone, Copy, Debug, PartialEq, Eq)] pub struct FightButton;
#[derive(Component)] pub struct FightBody;     // the tab's lines of the period, rebuilt (empty until Task 6c)
#[derive(Component)] pub struct FightState;    // FIGHT_OFF_LINE or FIGHT_ON_LINE
/// The tab's body: the switch, `FightState`, `FIGHT_LINE`, then `FightBody`.
pub fn spawn_fight_tab(body: &mut ChildSpawnerCommands);
/// Write the state line, mark the switch and rebuild `FightBody` when the runner or the view changed.
pub fn paint_fight(/* commands, Res<SceneRunner>, Res<PanelView>, the body, the state line, the switch */);
/// A press of the switch writes `SceneCommand::StartOverWithFight`.
pub fn pressed(event: On<PointerClick>, buttons: Query<&FightButton>, commands: MessageWriter<SceneCommand>);
// C/script.rs
/// `{"fight":"on"}`: what a press of the Fight tab's switch does.
Fight(String),
```

What is drawn: the tab is the existing `panel::spawn_pressed` button and `controls::text` lines; nothing on the
plane. `FightBody` holds no line in this task: Task 6c gives it the news, Task 8c the stoppages.

- [ ] **Step 1: Pin today's frames first.** In `C/frame.rs`'s tests, before any other edit of this task, write:

```rust
/// FNV-1a over the frames' debug text: a fingerprint of what is drawn, stable across runs.
fn fingerprint(pictures: &[Picture]) -> u64 {
    let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
    for picture in pictures {
        for byte in format!("{:?}", picture.frame).bytes() {
            hash ^= u64::from(byte);
            hash = hash.wrapping_mul(0x0100_0000_01b3);
        }
    }
    hash
}

/// Twelve periods of the scene's world without the fight, the harvest failed in Place B from period 3, as they
/// were drawn before the pay fight's first client task. Written once from a run of the tree before Task 2c.
const NO_FIGHT_FRAMES: [u64; 2] = [0, 0];

#[test]
fn a_world_with_no_fight_draws_as_before() -> TestResult {
    let found = [
        fingerprint(&twelve_periods(ParticleMode::Groups)?),
        fingerprint(&twelve_periods(ParticleMode::People)?),
    ];
    assert_eq!(found, NO_FIGHT_FRAMES, "write the found pair into NO_FIGHT_FRAMES before any other edit");
    Ok(())
}
```

- [ ] **Step 2: See it fail for the pin, then write the pin.** Run
  `mise run rust:test:q -- -p babylon-client -E 'test(a_world_with_no_fight_draws_as_before)'`. Expected: it
  fails with the found pair (the zeros are not the frames). Write the found pair into `NO_FIGHT_FRAMES`, run
  again: it passes. This is the tree before this task's first edit (stored hours' Tasks 5 to 7 and this plan's
  Tasks 1 and 2 built). The pin never changes again in Part One.
- [ ] **Step 3: Write the failing tests.**

In `C/fight.rs`'s tests:
```rust
fn fight_period() -> Result<PeriodResult, Box<dyn Error>> {
    Ok(Runner::open_world(&World::scene_with_fight())?.step()?.clone())
}

/// The fight world's kept accounts are in its book with no cash, and every reading of the scene takes its
/// periods: read, drawn in both modes, tabled in every grouping, and every body and group inspected.
#[test]
fn a_fight_world_with_no_organization_reads_and_draws() -> TestResult {
    use crate::small_world::{frame, inspect, marks, reading, table};
    use crate::small_world::frame::ParticleMode;
    use crate::small_world::inspect::Pick;
    use crate::small_world::table::Grouping;
    let mut runner = Runner::open_world(&World::scene_with_fight())?;
    runner.strike(Shock::HarvestFails, Places::Both, Lasts::UntilLifted)?;
    for _ in 0..12 { runner.step()?; }
    let history = runner.history().to_vec();
    for (index, result) in history.iter().enumerate() {
        let kept: Vec<&(AccountId, Currency)> = result.closing.cash.iter()
            .filter(|(account, _)| matches!(account, AccountId::Organization(_))).collect();
        assert_eq!(kept.len(), 16, "period {}", result.period);
        assert!(kept.iter().all(|(_, cash)| cash.micro_units() == 0));
        assert!(result.fight.is_some());
        let read = reading::read_period(result)?;
        for grouping in [Grouping::Workplace, Grouping::Class, Grouping::Place] {
            table::table(&read, grouping)?;
        }
        for mode in [ParticleMode::Groups, ParticleMode::People] {
            let picture = frame::build_picture(result, mode)?;
            let mut picks: Vec<Pick> = Workplace::ALL.into_iter().map(|w| Pick::Body(Party::Workplace(w))).collect();
            picks.extend([Pick::Body(Party::Treasury), Pick::Body(Party::Fund)]);
            picks.extend(Household::ALL.into_iter().map(|h| Pick::Particle(frame::household_id(h))));
            for pick in &picks {
                inspect::inspect(&picture, result, pick)?;
                marks::rule_rows(&history, index, pick)?;
            }
        }
    }
    Ok(())
}
```

In `C/scene_tests.rs`:
```rust
fn fight_switch(app: &mut App) -> Result<Entity, Box<dyn Error>> {
    use crate::small_world::fight::FightButton;
    let world = app.world_mut();
    world.query_filtered::<Entity, With<FightButton>>().iter(world).next().ok_or_else(|| "no fight switch".into())
}

#[test]
fn the_fight_switch_starts_over_with_the_fight() -> TestResult {
    use crate::small_world::fight::{FIGHT_OFF_LINE, FIGHT_ON_LINE, FIGHT_SWITCH};
    use babylon_circuit_worlds::fight::Fight;
    let mut app = scene_app(None)?;
    send(&mut app, SceneCommand::Step);
    updates(&mut app, 3);
    let tab = panel_button(&mut app, PanelButton::Lower(Lower::Fight))?;
    click(&mut app, tab);
    updates(&mut app, 2);
    assert_eq!(app.world().resource::<PanelView>().lower, Lower::Fight);
    assert_eq!(caption_of(&mut app, Lower::Fight)?, "Fight");
    assert!(texts(&mut app).contains(&FIGHT_SWITCH.to_owned()));
    assert!(texts(&mut app).contains(&FIGHT_OFF_LINE.to_owned()));
    let switch = fight_switch(&mut app)?;
    click(&mut app, switch);
    updates(&mut app, 2);
    assert_eq!(history(&app), 0);
    {
        let scene = app.world().resource::<SceneRunner>();
        assert!(matches!(scene.runner.world().fight, Fight::Asked(_)));
        assert_eq!(scene.runner.world().rules, BabylonWorld::scene_with_fight().rules);
    }
    assert_eq!(app.world().resource::<PanelView>().lower, Lower::Fight);
    assert_eq!(app.world().get::<Node>(switch).ok_or("the switch's node")?.border.left, px(3));
    assert!(texts(&mut app).contains(&FIGHT_ON_LINE.to_owned()));
    send(&mut app, SceneCommand::Step);
    updates(&mut app, 3);
    let last = app.world().resource::<SceneRunner>().runner.history().last().ok_or("a period")?.clone();
    assert!(last.fight.is_some());
    send(&mut app, SceneCommand::StartOver);
    updates(&mut app, 2);
    assert!(matches!(app.world().resource::<SceneRunner>().runner.world().fight, Fight::Absent));
    assert!(texts(&mut app).contains(&FIGHT_OFF_LINE.to_owned()));
    assert_eq!(app.world().get::<Node>(switch).ok_or("the switch's node")?.border.left, px(1));
    Ok(())
}

#[test]
fn a_script_turns_the_fight_on() -> TestResult {
    use babylon_circuit_worlds::fight::Fight;
    let (app, folder) = scripted("{\"fight\":\"on\"}\n{\"step\":1}\n{\"report\":\"f\"}\n", 600)?;
    let replies = std::fs::read_to_string(folder.0.join("replies.jsonl"))?;
    let lines: Vec<&str> = replies.lines().collect();
    assert_eq!(lines.len(), 3, "{replies}");
    for (k, line) in lines.iter().enumerate() {
        assert_eq!(*line, format!("{{\"event\":\"done\",\"line\":{}}}", k + 1));
    }
    let scene = app.world().resource::<SceneRunner>();
    assert!(matches!(scene.runner.world().fight, Fight::Asked(_)));
    assert_eq!(scene.runner.history().len(), 1);
    Ok(())
}
```
and in `the_rail_has_the_rules_tab_only_for_rules_shown` the pin `assert_eq!(count_of::<LowerBody>(&mut app), 2);`
(1195) becomes `3` (the Fight tab is the third body; Global Constraints name this pin). The pin
`count_of::<NoticeLine>(&mut app) == 2` stays: the Fight tab has no notice line.

In `C/script_tests.rs`:
```rust
#[test]
fn the_script_turns_the_fight_on() {
    assert_eq!(script::parse_script(r#"{"fight":"on"}"#), Ok(vec![ScriptCommand::Fight("on".into())]));
    assert_eq!(script::parse_script(r#"{"lower":"fight"}"#), Ok(vec![ScriptCommand::Lower("fight".into())]));
    for bad in [r#"{"fight":"off"}"#, r#"{"fight":"yes"}"#] {
        assert!(matches!(script::parse_script(bad), Err(ScriptError::Line { line: 1, .. })), "{bad}");
    }
}
```

- [ ] **Step 4: See them fail.** `mise run rust:test:q -- -p babylon-client -E 'test(small_world)'`. Expected: does
  not compile: no `fight` module, no `Lower::Fight`, no `SceneCommand::StartOverWithFight`, no
  `ScriptCommand::Fight`. (`a_fight_world_with_no_organization_reads_and_draws` needs only the module to exist:
  once it compiles it passes, which is its point; it guards every later task.)
- [ ] **Step 5: The Fight tab** (`C/fight.rs`, `C/panel.rs`). `spawn_lower` spawns a third tab
  `spawn_pressed(tabs, PanelButton::Lower(Lower::Fight), "Fight", 13.0)` after "Rules", and a third body
  `LowerBody(Lower::Fight)` (display `None`) whose children `fight::spawn_fight_tab` spawns: the switch
  (`spawn_pressed(body, FightButton, FIGHT_SWITCH, 13.0)`), the `FightState` line (12.0, `theme::GRAY`), the
  `FIGHT_LINE` (11.0, `theme::GRAY`) and the `FightBody` column. `lower_caption(Lower::Fight, count)` is
  `("Fight", "stopped")`; `paint_lower` passes 0 for it (Task 8c counts). `paint_fight` runs when `SceneRunner`
  or `PanelView` changed: it writes `FIGHT_ON_LINE` when `runner.world().fight` is `Fight::Asked`, else
  `FIGHT_OFF_LINE`; it marks the switch with `panel::mark(.., on)`; it empties `FightBody` (the period the view
  reads, `panel::view_index`, is where Tasks 6c and 8c read their lines). Sizes and colours are starting values;
  the lead's to tune.
- [ ] **Step 6: The command** (`C/scene.rs`). `open_runner_of(world)` is `Runner::open_world_with_hours(world)`;
  `open_runner()` calls it with `World::scene()`. `Stage::start_over_with(&mut self, world: &World)` holds what
  `start_over` does today with `open_runner_of(world)`; `start_over` calls it with `World::scene()`.
  `SceneCommand::StartOverWithFight` calls `start_over_with(&World::scene_with_fight())` and then sets
  `view.lower = Lower::Fight`. A second press starts over again with the fight: the switch's caption says so.
  "Start over" opens the world without the fight, as it clears rules and shocks.
- [ ] **Step 7: The script** (`C/script.rs`). `ScriptCommand::Fight(name)`: `check_names` accepts only `"on"`
  (`known(fight_named(name), "fight", name)`, `fight_named` beside `lower_named`); `begin` writes
  `SceneCommand::StartOverWithFight` and goes to `State::Checking(0)`. `lower_named("fight")` is `Lower::Fight`.
  The doc of `ScriptCommand` names `fight` beside the others.
- [ ] **Step 8: See them pass.** `mise run rust:test:q -- -p babylon-client -E 'test(small_world)'`. Expected: all
  pass; `a_world_with_no_fight_draws_as_before` passes with the pin of Step 2; no pinned value changed but the
  `LowerBody` count (2 to 3). The styles stay ten streams in Part One.
- [ ] **Step 9: Run the companion's gate. Commit** `feat(client): the pay fight's switch and its tab` (body:
  `Part of PER-371`).

**What this task must not do:** open a window in a test; add a `Party`, a payment kind, a money stream or a row
that nothing in Part One can reach; change any frame of a world with no fight
(`a_world_with_no_fight_draws_as_before` proves the frames equal); give the Fight tab a `NoticeLine`.

---

### Task 3: Pay changes at a boundary

**Files:**
- Modify: `E/orders/validate.rs` (the rate checks; step 5 no longer names rates); `E/orders/apply.rs`
  (`apply_rates`); `E/transition/state.rs` (`close_funded_production`: one call); `T/period_orders.rs`
  (`mod rates`); create `T/period_orders/rates.rs`; `T/period_orders/payments.rs` (delete the `Rate` row of
  `an_order_of_a_kind_not_built_is_refused`); the contract and the digest.

**Interfaces:**

Consumes (Task 1): `PeriodOrders`, `RateOrder`, `RateReceipt`, `OrderReceipt::Rate`, `PeriodOrderError::{
UnknownSite, NoWageAt, RateNotPositive}`, `close_material_period_with_orders`, `orders::validate::validate`,
the support helpers `opening`, `of_runner`, `fund_world`, `close`, `next`, `Refused`, `Closed`.

Produces:

```rust
// E/orders/apply.rs
/// PF1: every `Wage` row of each (site, unit) ordered gets the new rate, from the first hour of the period.
pub(crate) fn apply_rates(state: &mut MaterialCircuitState, orders: &PeriodOrders)
    -> Result<Vec<OrderReceipt>, MaterialCircuitError>;
```

`RateOrder` applied (point 1 of The engine's orders) and `RateReceipt { period, site_id, unit_id, old_rate,
new_rate, rows }`: `old_rate` the largest `Wage` rate of the rows before (as `spare_money::wages` reads a site's
rate, `E/recurring/spare_money.rs:161-171`), `rows` the number of rows set. `NotBuilt(OrderKind::Rate)` is gone.

- [ ] **Step 1: Write the failing tests** in `T/period_orders/rates.rs`. Farm A as in Task 1; `hours =
  babylon_circuit_worlds::hours_unit()`; `$x` is `Currency::from_micro_units(x * 1_000_000)`.
  - `a_rate_holds_from_the_first_hour`: `opening(&fund_world())`, `RateOrder { farm A, hours, $12 }`. Every
    `member_labor_use` row at farm A has `compensation == Wage($12)`; farm A's own member attends 40 hours
    (cash $880 / $12 = 73 > 40) and `accrued_wages == $480`; the four `EmploymentTerms` rows of farm A in
    `transition.state` (its own and three pair rows) are `Wage($12)`, every other row `Wage($10)`;
    `transition.orders == [Rate(RateReceipt { period: 1, site_id: farm A, unit_id: hours, old_rate: $10,
    new_rate: $12, rows: 4 })]`.
  - `the_benefit_reads_the_new_rate`: `Runner::open_world(&fund_world())`, `strike(HarvestFails, Both,
    UntilLifted)`, step until the state's `financial.layoffs` holds a record with a cohort above 0 (at most 40
    steps; fail "no layoff in 40 periods"); `p = of_runner(&runner)`. Close `p` twice: with
    `PeriodOrders::none` and with a `RateOrder` at $12 for each of the eight workplaces (site order, hours
    unit). For every `PublicProgramReceipt` of program `laid_off` the two closes name the same recipients and
    `due` (micro-units) satisfies `ordered * 10 == none * 12` (the due is `wage x 10 x 5_000 x units / 20_000`,
    exact at whole dollars, `E/financial/layoffs.rs:198-208`); at least one `due` is above 0.
  - `the_bound_and_the_hosts_read_the_new_rate_at_that_close`: `opening(&World { rules:
    vec![HiringWithinMeans, SeekingInPlace], ..World::scene() })`. Without an order farm A's
    `HiringBoundReceipt` (period 2) has `bound_hours == asked_hours`, `asked_hours > 0`, `limit ==
    HiringLimit::None` (the quiet world is not cut, `the_quiet_world_with_the_bound_is_still_for_34_periods`).
    With `RateOrder { farm A, hours, $100_000 }` (farm A pays no hour: $880 / $100,000 = 0) its receipt has
    `asked_hours > 0`, `bound_hours == 0` and `limit == HiringLimit::Money`: one batch's ten hours cost
    $1,000,000, more than the farm can hold at the close. The closed state's employment rows of farm A carry
    the new rate; they are what `staff_in_places` reads for the hosts' order (`state.rs:859-867`). These rows
    are the pin of the hosts' reading: no public view shows the hosts' order.
  - `a_rate_holds_until_another_order`: from `opening(&fund_world())`, three periods through `next`: period 1
    `RateOrder { farm A, $12 }`, period 2 `PeriodOrders::none(2)`, period 3 `RateOrder { farm A, $11 }`. Farm
    A's own member's `compensation` is `Wage($12)`, `Wage($12)`, `Wage($11)`; rate receipts only in periods 1
    and 3, the second `old_rate: $12, new_rate: $11, rows: 4`; after period 3 farm A's rows are $11 and every
    other row $10.
  - `a_rate_of_zero_or_at_no_wage_is_refused`: at period 1, `Err(Refused::Close(Order(..)))` for: rate $0
    (`RateNotPositive { site_id: farm A }`); rate `-1` micro-unit (the same); site `SiteId::from_bytes([99;
    32])` (`UnknownSite(..)`); farm A with `UnitId::from_bytes([7; 32])` (`NoWageAt { site_id, unit_id }`).
  - `a_rise_the_cash_cannot_pay_leaves_hours_unpaid` (Review Focus 1, pinned as it is):
    `opening(&World { rules: vec![HiringWithinMeans, SeekingInPlace, StopWithoutPay], ..World::scene() })`,
    `RateOrder { farm A, hours, $30 }`. The plan of period 1 was made at $10 (40 hours). Farm A's own member:
    `available_hours 40, planned_hours 40, attended_hours 29, unattended_hours 11, accrued_wages $870` ($880 /
    $30 = 29 whole hours); the `StopReceipt` of farm A is `{ period: 1, could_not_pay: true, hold: Held, limit:
    Some(3) }` (`min(4, ceil(29 / 10))`, `E/adjustment/standing.rs:148-154`).
- [ ] **Step 2: Run them and see them fail:** `mise run rust:test:q -- -p babylon-material-circuit --test
  period_orders -E 'test(rate) | test(benefit) | test(bound)'`. Expected: each fails with
  `Err(Refused::Close(Order(NotBuilt(Rate))))`.
- [ ] **Step 3: Validation.** In `validate`, step 5 drops `rates`; a new step 5a, before it, for each rate in
  key order:

  ```text
  no employment row with this site_id                   -> UnknownSite(site_id)
  no Wage row with this (site_id, unit_id)              -> NoWageAt { site_id, unit_id }
  rate <= 0                                             -> RateNotPositive { site_id }
  ```

- [ ] **Step 4: Implement `apply_rates`** and call it in `close_funded_production` behind `if let Some(orders)`,
  after `retire_resolved_purchases` and before `FinancialClose::opening` (`state.rs:1652-1653`); its receipts
  go first into `orders`. Rows that are `WorkingOwner` or `UnpaidFamily` keep their terms.
- [ ] **Step 5: Run them and see them pass** (the command of Step 2, then `--test period_orders` whole).
- [ ] **Step 6: The contract.** Under `period_orders`, after `ADR323_orders`; recompute the digest:

  ```yaml
    ADR323_rate: >-
      a rate order sets one wage on every wage row of a workplace and labor unit from the first hour of its
      period: it is applied after the period's deliveries settle and before the public programs pay, so the
      benefit after a layoff, the period's wages and every rule of the close read it (the bound, the stop rule,
      the order in which hosts are served); the rate is state and holds until another order; the plan of the
      period was made at the close before, at the old rate; a rate of 0 or less, a workplace with no
      employment row and a unit with no wage row are refused; its receipt has the old rate (the largest), the
      new rate and the rows set
  ```

- [ ] **Step 7: Run the scoped engine gate.**
- [ ] **Step 8: Commit** `feat(material-circuit): pay changes at a period's boundary`. The body: a rate order
  sets the wage of every row of a workplace from the first hour of its period; the benefit, the wages and every
  rule of that close read it; it holds until another order; the first period of a rise is paid from the money
  the workplace has, at a plan made at the old rate, and a test pins what follows (design call 35); the contract
  line and its digest change together. `Part of PER-371`.

**What this task must not do:**
- Add a field to `EmploymentTerms` or any state type; change the rate anywhere but in `apply_rates`.
- Mend Review Focus 1 (the first period's plan at the old rate): it is pinned and counted, not changed.
- Change the rate of a row that is not `Wage`.

---

### Task 3c: A workplace's rate in its panel

After this task a person who clicks a workplace in a fight world reads what it pays: "Pays" | "$10.00 an hour",
and after a change "$12.00 an hour from period 32". Part One issues a rate order only when an employer gives way
(Task 8), so until then the row shows the opening rate.

**Files:**
- Modify: `C/inspect.rs` (`rate_rows`, its tests); `C/fight.rs` (`panel_rows`, `AN_HOUR`, `rates_of`);
  `C/panel.rs` (`rows_for`, 838-859: after `marks::rule_rows`, `rows.extend(fight::panel_rows(history, index,
  pick)?)`). Stored hours' Task 6 has put rows of hours into `inspect::workplace_rows` first; the fight's rows
  come after the rules' rows, so they do not meet.

**Interfaces:**

Consumes (Task 3): `OrderReceipt::Rate(RateReceipt { period: u64, site_id: SiteId, unit_id: UnitId, old_rate:
Currency, new_rate: Currency, rows: u32 })` in `PeriodReceipts.orders`; the period's pay of each member,
`MemberLaborUseReceipt.compensation: LaborCompensation` (`Wage(Currency)` for a wage row,
`payments/attendance.rs:19-22`). The state's employment rows are not in a `PeriodResult`; the member receipts carry
each row's compensation of that period, so they are read instead.

Produces:
```rust
// C/fight.rs
type Rows = Vec<(String, String)>;
/// The unit word of a wage rate. Designed: the design's own words ("$12 an hour").
pub const AN_HOUR: &str = "an hour";
/// The period's rate receipts, in receipt order (every `OrderReceipt` variant named).
pub fn rates_of(result: &PeriodResult) -> impl Iterator<Item = &RateReceipt>;
/// The fight's rows of a pick for the period at `index`: none for a period with no fight. Workplace: the rate.
/// Later tasks append theirs here.
/// # Errors
/// As the rows it gathers.
pub fn panel_rows(history: &[PeriodResult], index: usize, pick: &Pick) -> Result<Rows, FrameError>;
// C/inspect.rs
/// "Pays" | "{rate} an hour", with " from period {p}" when a rate receipt of its site stands in the history up to
/// `index` (the latest one). The rate is the compensation of the member receipt of the workplace's own household
/// at its site.
/// # Errors
/// `FrameError::Edge` when the period has no such receipt, when its two receipts of that pair disagree, or when the
/// latest rate receipt's `new_rate` is not the rate the period paid (while no later receipt stands).
pub fn rate_rows(history: &[PeriodResult], index: usize, w: Workplace) -> Result<Rows, FrameError>;
```

What is drawn: one row of the inspector's panel (the existing `panel::spawn_rows`), last after the rules' rows,
read from the member receipts and the rate receipts. Nothing on the plane.

- [ ] **Step 1: Write the failing tests** (in `C/inspect.rs`'s tests):

```rust
fn shop_a() -> Workplace { Workplace { place: Place::A, kind: Kind::Shop } }

/// Three copies of a fight world's first period, numbered 1 to 3; from copy 2 the shop pays one step of pay more on
/// every row at its site, and copy 2 holds the rate receipt.
fn rate_history() -> Result<(Vec<PeriodResult>, Currency, Currency), Box<dyn Error>> {
    use babylon_circuit_worlds::fight::pay_step;
    use babylon_circuit_worlds::World;
    use babylon_material_circuit::{LaborCompensation, OrderReceipt, RateReceipt};
    let first = Runner::open_world(&World::scene_with_fight())?.step()?.clone();
    let own = first.receipts.member_labor_use.iter()
        .find(|r| r.site_id == shop_a().site_id() && r.payee == shop_a().workers().principal())
        .ok_or("the shop's own member receipt")?;
    let old = own.compensation.wage_rate();
    let new = old.checked_add(pay_step(&World::scene_with_fight(), shop_a())).map_err(|e| format!("{e:?}"))?;
    let unit = own.unit_id;
    let mut history = Vec::new();
    for period in 1..=3_u64 {
        let mut result = first.clone();
        result.period = period;
        if period >= 2 {
            for r in result.receipts.member_labor_use.iter_mut().filter(|r| r.site_id == shop_a().site_id()) {
                r.compensation = LaborCompensation::Wage(new);
            }
        }
        if period == 2 {
            result.receipts.orders.push(OrderReceipt::Rate(RateReceipt { period, site_id: shop_a().site_id(),
                unit_id: unit, old_rate: old, new_rate: new, rows: 1 }));
        }
        history.push(result);
    }
    Ok((history, old, new))
}

#[test]
fn a_workplace_shows_its_rate_and_since_when() -> TestResult {
    use crate::small_world::fight::AN_HOUR;
    let (history, old, new) = rate_history()?;
    let pays = |k: usize| rate_rows(&history, k, shop_a());
    assert_eq!(pays(0)?, vec![row("Pays", format!("{} {AN_HOUR}", human_numbers::currency(old.micro_units())))]);
    let since = format!("{} {AN_HOUR} from period 2", human_numbers::currency(new.micro_units()));
    assert_eq!(pays(1)?, vec![row("Pays", since.clone())]);
    assert_eq!(pays(2)?, vec![row("Pays", since)]);
    let quiet = Runner::open()?.step()?.clone();
    let pick = Pick::Body(Party::Workplace(shop_a()));
    assert_eq!(crate::small_world::fight::panel_rows(&[quiet], 0, &pick)?, Vec::new());
    Ok(())
}

#[test]
fn a_rate_row_is_the_receipt_s() -> TestResult {
    use babylon_material_circuit::OrderReceipt;
    let (mut history, old, _) = rate_history()?;
    let pick = Pick::Body(Party::Workplace(shop_a()));
    let rows = crate::small_world::fight::panel_rows(&history, 1, &pick)?;
    let receipt = crate::small_world::fight::rates_of(&history[1]).next().ok_or("the rate receipt")?.clone();
    assert_eq!(value(&rows, "Pays").ok_or("a rate row")?.split(' ').next(),
        Some(human_numbers::currency(receipt.new_rate.micro_units()).as_str()));
    if let Some(OrderReceipt::Rate(rate)) = history[1].receipts.orders.first_mut() {
        rate.new_rate = old;     // a receipt that says another rate than the period paid
    }
    assert!(matches!(rate_rows(&history, 1, shop_a()), Err(FrameError::Edge(_))));
    Ok(())
}
```

- [ ] **Step 2: See them fail.** `mise run rust:test:q -- -p babylon-client -E 'test(rate)'`. Expected: does not
  compile: no `rate_rows`, `panel_rows`, `rates_of`, `AN_HOUR`.
- [ ] **Step 3: Implement** `rates_of` (a `filter_map` over `result.receipts.orders` with all seven arms),
  `rate_rows` as its doc says (walk `history[..=index]` back for the latest `RateReceipt` of the site), and
  `panel_rows`: `Ok(Vec::new())` when `history[index].fight` is `None`; for `Pick::Body(Party::Workplace(w))`,
  `inspect::rate_rows(history, index, w)`; every other pick none (later tasks add theirs). `rows_for` extends its
  rows with `fight::panel_rows` after `marks::rule_rows`.
- [ ] **Step 4: See them pass.** `mise run rust:test:q -- -p babylon-client -E 'test(small_world)'`. Expected: all
  pass; `a_world_with_no_fight_draws_as_before` unchanged.
- [ ] **Step 5: Run the companion's gate. Commit** `feat(client): a workplace's rate in its panel` (body:
  `Part of PER-371`).

**What this task must not do:** compute a rate from wages and hours (the rate is the receipt's); show the row in a
world with no fight; change a frame (the pinned test proves it).

---

### Task 4: Hours withheld

**Files:**
- Modify: `E/orders/attendance.rs` (`OrderedHours::of`, `withheld_receipts`); `E/orders/validate.rs`;
  `E/transition/state.rs` (`close_funded_production`: the hours and the receipts; `stop_round`, 898-922: the
  withheld map); `E/adjustment/standing.rs` (`test_workplaces`, 257-; a new `judge_struck`);
  `E/adjustment/restart.rs` (`restart_stopped`, 762-861: the count); `T/period_orders.rs` (`mod withheld`);
  create `T/period_orders/withheld.rs`; `T/period_orders/payments.rs` (delete the `Withheld` row); the contract
  and the digest.

**Interfaces:**

Consumes (Task 1): `WithheldOrder`, `WithheldReceipt`, `OrderReceipt::Withheld`, `OrderedHours`,
`withheld_hours`, `PeriodOrderError::{UnknownMember, NotAWage, ShareOutOfRange}`, `transition.orders`; (Task 3)
`RateOrder` applied, for the stop rule's test; the support helpers.

Produces:

```rust
// E/orders/attendance.rs
impl OrderedHours {
    /// The orders' withheld shares; above and floor empty until Task 5.
    pub(crate) fn of(orders: &PeriodOrders) -> Self;
}
/// One receipt per withheld order, in key order, from the opening's member rows of the period and the terms.
pub(crate) fn withheld_receipts(state: &MaterialCircuitState, orders: &PeriodOrders)
    -> Result<Vec<OrderReceipt>, MaterialCircuitError>;
// E/adjustment/standing.rs
/// `judge` of the workplace with `struck` persons (withheld hours / hours a person, rounded down) left out of
/// `employed`, and any limit raised by them.
pub(crate) fn judge_struck(previous: StopHold, test: &SiteTest, struck: u64) -> Result<Verdict, MaterialCircuitError>;
/// gains `withheld`: hours withheld at each site this period, from the closed period's WithheldReceipts.
pub(crate) fn test_workplaces(economy: &MonetaryCircuit, uses: &[MemberLaborUseReceipt], period: u64,
    opening: &StaffingState, wages: &BTreeMap<SiteId, i128>, previous: &WorkplaceStanding,
    withheld: &BTreeMap<SiteId, u64>) -> Result<StopRound, PlaceStaffingError>;
```

`WithheldOrder` applied (points 3, 4 and 5 of The engine's orders); `WithheldReceipt { rolls_hours: the member's
labor row of the period, withheld_hours: withheld_hours(rolls, share_bps) }`. `NotBuilt(Withheld)` is gone.

- [ ] **Step 1: Write the failing tests** in `T/period_orders/withheld.rs` (fund world with the seekers unless
  named) and in `E/adjustment/standing.rs`'s tests:
  - `withheld_hours_are_not_on_the_clock_not_paid_and_make_nothing`: `WithheldOrder { farm A's own member
    (Workplace::member_id), 10_000 }`. Its `MemberLaborUseReceipt`: `available 0, planned 0, unplanned 0,
    attended 0, unattended 0, accrued $0`; farm A's `LaborUseReceipt.available_hours == 0`; no
    `WageAccrualReceipt` has payee `Household(farm A's workers)`; farm A's `ProductionReceipt.produced_batches
    == 0`; `transition.orders == [Withheld(WithheldReceipt { period: 1, member_id, site_id: farm A, payee: farm
    A's workers, rolls_hours: 40, withheld_hours: 40 })]`.
  - `the_people_stay_on_the_rolls`: the same order. In `placed.member_labor` and in the finished state's
    `member_labor`, farm A's own member has 40 hours for period 2 (4 persons employed after the staffing,
    `placed.members`); farm A's labor row for period 2 is 40; period 2 closes with `PeriodOrders::none(2)` (so
    `validate_member_budgets` passes) and, with the order again, its receipt has `rolls_hours: 40`. (The site's
    labor row of period 1 is set to the attended hours by `fund_attendance` itself, `attendance.rs:349`; the
    member rows are what keep the rolls' hours through the close, `rest.rs` doc.)
  - `a_struck_workplace_does_not_rest_its_price`: `opening(&World { rules: vec![SeekingInPlace,
    RestingPrice], ..World::scene() })`, all of clinic A's own member withheld. No `AdjustmentReceipt::
    RestingPrice` names clinic A's site; clinic A's `ServiceMarketReceipt` (care) has `reason ==
    ServicePriceDecision::FundedUnmet` and `next_price == old_price + $1` (households paid for care that was not
    performed; a rest would read `Hold`). Without this task's rows kept, its people would have made no hours and
    it offered nothing, so it would rest (`rest.rs:18-33`).
  - `a_struck_workplace_is_not_tested_for_a_restart_and_its_quiet_count_stays`: `opening(&World { rules:
    World::switches_at(Scale::Small).to_vec(), ..World::scene() })`, five periods through `next`, each with all
    of clinic A's own member withheld: after each, clinic A's row in `placed.standing` has `periods_since_work ==
    0` and `quiet_periods == 0`, and no `Restart` receipt names clinic A; its `StopReceipt` each period is `{
    could_not_pay: false, hold: Free, limit: None }`.
  - In `standing.rs` tests, `the_stop_rule_neither_frees_nor_holds_on_struck_hours` (rates in micro-units,
    `hours_per_person 10`, `rate 10_000_000`):
    - employed 4, struck 2, available 20, attended 10, unattended 10, previous Free: `Verdict {
      could_not_pay: true, hold: Held, limit: Some(3) }` (`min(2, 1) + 2`; `judge` alone gives `Some(1)`);
    - employed 4, struck 4, available 0, attended 0, unattended 0, previous Free: `{ false, Free, None }`;
    - the same, previous Held, cash 500_000_000, bill 0: `{ false, Held, Some(9) }` (`0 + 500 / 100 + 4`).
  - `a_partly_struck_workplace_pays_the_rest`: `WithheldOrder { utility A's own member, 5_000 }` and `{ farm
    A's own member, 2_500 }`: utility A's own row `available 60, planned 60, attended 60, accrued $600`,
    receipt `rolls 120, withheld 60`; farm A's own row `available 30, attended 30, accrued $300`, receipt
    `rolls 40, withheld 10`.
  - `withheld_by_a_working_owner_row_is_refused`: the opening with farm A's own row set to
    `LaborCompensation::WorkingOwner`, and the order: `Err(Refused::Close(Order(NotAWage { member_id })))`. In
    the same test: member `StaffingMemberId::from_bytes([99; 32])`: `UnknownMember(..)`; shares 0 and 10_001:
    `ShareOutOfRange { member_id, share_bps }`.
  - `output_shortage_and_prices_follow_in_the_circuit`: `opening(&World { rules: vec![SeekingInPlace,
    RestingPrice], ..World::scene() })`, six periods through `next`, each with all of farm A's
    own member withheld: farm A's `produced_batches == 0` every period; in some period a `Household` of place A
    has a food `HouseholdConsumptionReceipt` with `unmet_quantity > 0` (shop A buys food only from farm A:
    `recurring`, `W/doubled/opening.rs:428-437`); every period's receipts hold no `RestingPrice` for farm A
    or shop A. The stoppage writes only the hours; the rest follows in the circuit (A22).
- [ ] **Step 2: Run them and see them fail:** `mise run rust:test:q -- -p babylon-material-circuit --test
  period_orders -E 'test(withheld) | test(struck) | test(rolls) | test(shortage)'` and `mise run rust:test:q --
  -p babylon-material-circuit -E 'test(neither_frees)'`. Expected: the first with `NotBuilt(Withheld)`; the
  second does not compile, no `judge_struck`.
- [ ] **Step 3: Validation.** Step 5 drops `withheld`; a new step 5b, for each withheld order in key order:

  ```text
  no employment row with this member_id                 -> UnknownMember(member_id)
  its row is not Wage                                   -> NotAWage { member_id }
  share_bps == 0 or > 10_000                            -> ShareOutOfRange { member_id, share_bps }
  ```

- [ ] **Step 4: The hours.** `OrderedHours::of(orders)`; in `close_funded_production` behind `if let
  Some(orders)`: `withheld_receipts(state, orders)?` before `fund_attendance` (the member rows of the period are
  read before anything changes them) and `fund_attendance(.., &OrderedHours::of(orders))`; the receipts go into
  `orders` after the fund payments'. Without orders the call stays `&OrderedHours::none()`.
- [ ] **Step 5: The stop rule.** `judge_struck`: `judge(previous, &SiteTest { employed:
  employed.checked_sub(struck)?, ..*test })` (`Arithmetic` when struck passes employed), then `limit + struck`
  (checked). `test_workplaces` takes `withheld` and calls `judge_struck` with `withheld[site] /
  hours_per_person` (0 when absent). `stop_round` builds the map from `self.transition.orders`: the sum of
  `withheld_hours` of the `Withheld` receipts by `site_id`.
- [ ] **Step 6: The restart's count.** In `restart_stopped` (779-782), `count` is not called for a site with a
  `Withheld` receipt of `withheld_hours > 0` in `transition.orders`; its `periods_since_work` and
  `quiet_periods` stay. `is_tested` and `rest::made_hours` are unchanged: the member rows keep the rolls' hours.
- [ ] **Step 7: Run them and see them pass** (the commands of Step 2, then `--test period_orders` whole).
- [ ] **Step 8: The contract.** After `ADR323_rate`; recompute the digest:

  ```yaml
    ADR323_withheld: >-
      an order of hours withheld names a household's place at a workplace (its staffing member, whose terms are
      a wage) and the share, 1 to 10000 basis points, of that member's hours on the rolls that it withholds,
      rounded down; the hours offered are the rolls' less the withheld; withheld hours are never planned,
      attended, paid or used, and the people stay on the rolls: the member rows keep the rolls' hours, so the
      resting price and the restart's test do not act on withheld hours; the stop rule reads the offered hours,
      leaves the persons whose hours were withheld (whole persons, rounded down) out of those it employs and
      raises its limit by them; the restart does not count a workplace with hours withheld as quiet or busy in
      that close; its receipt has the rolls' hours and the hours withheld
  ```

- [ ] **Step 9: Run the scoped engine gate;** then the 14 long tests in the background (Global
  Constraints). Expected: 14 of 14.
- [ ] **Step 10: Commit** `feat(material-circuit): hours withheld stay on the rolls and off the clock`. The
  body: an order withholds a share of a member's hours; those hours are not planned, paid or used, and the
  people stay on the rolls; the stop rule, the resting price and the restart do not act on struck hours; output,
  shortage and prices follow in the circuit; the contract line and its digest change together. `Part of
  PER-371`.

**What this task must not do:**
- Change a stored row (`MemberLaborCapacityRow`, `LaborCapacityRow`) or `rest::made_hours` or `is_tested`: the
  rolls' hours stay in the rows, and that is what keeps the resting price and the restart's test off.
- Let a withheld hour be planned, and so become `unattended` and make the stop rule hold the workplace.
- Count a struck workplace's persons as laid off by the stop rule's limit (Review Focus 2's separations by
  ordinary staffing are Task 8's to count, not this task's to mend).

---

### Task 4c: The people at the gate; the shock button's word becomes "Apply"

After this task a person sees a stoppage as people: in the people view the persons whose hours a household
withholds stand at their workplace's gate, not at its wage anchor; in the groups view a household with persons
out that nobody pays stands at that gate; no hours go in from them (the receipts carry none). The panel of the
workplace reads "Out at the gate" and the household's "Out at the gate of Place A shop". The button that brings a
shock reads "Apply" (call 40). Until Task 8 nothing withholds, so a person sees the gate only in the lead's
proof of Task 8c; the word "Apply" is seen at once.

**Files:**
- Modify:
  - `C/layout.rs`: `GATE_BELOW`, `gate_of`.
  - `C/frame.rs`: `at_the_gate`; `Population` (382-444) gains `out_at`; `stand` (542-581) gives a household with
    persons out a gate for a home; `stand_people` (586-636) clusters persons out at the gate.
  - `C/fight.rs`: `withheld_of`; `panel_rows` gains the gate's rows.
  - `C/panel.rs`: `ShockButton::Strike(Shock)` (98) becomes `ShockButton::Apply(Shock)`; `spawn_shock` (396)
    captions it "Apply"; `press_shock` (1106-1114) writes `SceneCommand::Apply`; the doc lines 97, 112 and 312
    say "Apply".
  - `C/scene.rs`: `SceneCommand::Strike` (105) becomes `SceneCommand::Apply(Shock, Places, Lasts)`;
    `Stage::strike` (571-575) becomes `Stage::apply`; the `handle` arm (613).
  - `C/script.rs`: `begin` (542) writes `SceneCommand::Apply`. The script's own key `{"strike":..}` and
    `ScriptCommand::Strike` stay: every proof script uses them, and nothing on screen shows them.
  - Tests: `C/scene_tests.rs` (585, 607, 1386, 1457 name the new variants), `C/frame.rs`, `C/layout.rs`.
- All six uses of `SceneCommand::Strike` are in the scene's own files (`scene.rs`, `panel.rs`, `script.rs`,
  `scene_tests.rs`; `tests/decision_surface_contract.rs` writes only `SceneCommand::Step`), so it is renamed, as
  the plan's "Calls of the lead", 9, asks. `Runner::strike` in the small worlds keeps its name. The script's key
  `{"strike":..}` and `ScriptCommand::Strike` keep their names: nothing on screen shows them.

**Interfaces:**

Consumes (Task 4): `OrderReceipt::Withheld(WithheldReceipt { period: u64, member_id: StaffingMemberId, site_id:
SiteId, payee: FinalDemandPrincipalId, rolls_hours: u64, withheld_hours: u64 })`; `PeriodResult.members:
Vec<StaffingMemberReceipt>` (`member.member_id()`, `opening_employed`).

Produces:
```rust
// C/layout.rs
/// How far below its workplace a workplace's gate stands (plan units, down). Starting value; the lead's to tune.
pub const GATE_BELOW: f64 = 1.2;
/// Where the people out of a workplace stand: `(WORKPLACE_X[w.index()], -GATE_BELOW)`.
#[must_use] pub fn gate_of(w: Workplace) -> Point;
// C/frame.rs
/// Persons of each household out at each workplace this period: for each withheld receipt, the
/// `opening_employed` of its member times `withheld_hours` over `rolls_hours` (floor; 0 when the rolls hold no
/// hour), summed by (household, workplace), at most the household's persons.
/// # Errors
/// `FrameError::Edge` for a receipt of no household, workplace or member of the period; `Arithmetic`.
pub fn at_the_gate(result: &PeriodResult) -> Result<BTreeMap<(Household, Workplace), usize>, FrameError>;
// C/fight.rs
/// The period's withheld receipts, in receipt order (every `OrderReceipt` variant named).
pub fn withheld_of(result: &PeriodResult) -> impl Iterator<Item = &WithheldReceipt>;
// C/panel.rs: ShockButton::Apply(Shock); C/scene.rs: SceneCommand::Apply(Shock, Places, Lasts)
```

What is drawn, as marks: no new mark. The persons out are the existing person particles (style 1, `Glyph::Disc`)
of `stand_people`, clustered by `layout::cluster` at `layout::gate_of(w)`, read from the withheld receipts. In a
household's range at `w` (`person_ranges`), the persons out are the LAST `out` persons of the range, so that
`put_persons` gives the hours the household gave to its persons still at work first. In the groups view,
`stand_of` takes `layout::gate_of(w)` for its home in place of `layout::home_of(h)` when the household has persons
out at `w` (the first such `w` in `Workplace::ALL` order): a group paid by nobody stands at the gate; a group paid
by anyone leans by its money as today. No position reads hours.

- [ ] **Step 1: Pin the fight world's frames first.** In `C/frame.rs`'s tests, before any other edit of this task,
  beside Task 2c's `fingerprint` and `NO_FIGHT_FRAMES`, write:

```rust
/// Twelve periods of the fight world, the harvest failed in Place B from period 3, in one mode.
fn fight_twelve_periods(mode: ParticleMode) -> Result<Vec<Picture>, Box<dyn Error>> {
    let mut runner = Runner::open_world(&World::scene_with_fight())?;
    let mut pictures = Vec::new();
    for period in 1..=12 {
        if period == 3 {
            runner.strike(Shock::HarvestFails, Places::B, Lasts::TenPeriods)?;
        }
        pictures.push(build_picture(&runner.step()?.clone(), mode)?);
    }
    Ok(pictures)
}

/// The fight world's twelve periods as they were drawn before Task 4c. Written once from a run of the tree before
/// Task 4c; unchanged by Tasks 4c, 5c, 6c and 8c.
const FIGHT_FRAMES: [u64; 2] = [0, 0];

#[test]
fn without_a_stoppage_every_frame_is_as_before() -> TestResult {
    let found = [
        fingerprint(&fight_twelve_periods(ParticleMode::Groups)?),
        fingerprint(&fight_twelve_periods(ParticleMode::People)?),
    ];
    assert_eq!(found, FIGHT_FRAMES, "write the found pair into FIGHT_FRAMES before any other edit");
    Ok(())
}
```

- [ ] **Step 2: See it fail for the pin, then write the pin.** `mise run rust:test:q -- -p babylon-client -E
  'test(without_a_stoppage_every_frame_is_as_before)'`. Expected: it fails with the found pair. Write it into
  `FIGHT_FRAMES`, run again: it passes. No stoppage comes in these twelve periods (none begins before about period
  20), so the pin holds every later task to the fight world's frames as they are.
- [ ] **Step 3: Write the failing tests.**

In `C/frame.rs`'s tests:
```rust
fn shop_a() -> Workplace { Workplace { place: Place::A, kind: Kind::Shop } }

/// A fight world's first period with shop A's workers out at shop A: their member receipt there emptied of
/// hours, their wages there taken out of the transfers, and a withheld receipt of all its rolls' hours pushed.
/// Returns the period and the persons out (the member's `opening_employed`).
fn struck_period() -> Result<(PeriodResult, usize), Box<dyn Error>> {
    use babylon_material_circuit::{
        AccountId, MoneyLocation, MoneyTransferPurpose, OrderReceipt, WithheldReceipt,
    };
    let mut result = Runner::open_world(&World::scene_with_fight())?.step()?.clone();
    let household = shop_a().workers();
    let receipt = result.receipts.member_labor_use.iter_mut()
        .find(|r| r.site_id == shop_a().site_id() && r.payee == household.principal())
        .ok_or("the shop's own member receipt")?;
    let rolls = receipt.available_hours;
    for hours in [&mut receipt.attended_hours, &mut receipt.production_hours, &mut receipt.handling_hours,
        &mut receipt.maintenance_hours, &mut receipt.installation_hours, &mut receipt.idle_hours] {
        *hours = 0;
    }
    let withheld = WithheldReceipt { period: result.period, member_id: receipt.member_id,
        site_id: shop_a().site_id(), payee: household.principal(), rolls_hours: rolls, withheld_hours: rolls };
    result.receipts.money_transfers.retain(|t| !(matches!(t.purpose, MoneyTransferPurpose::WagePayment(_))
        && t.credit.location == MoneyLocation::Cash(AccountId::Household(household.principal()))));
    result.receipts.orders.push(OrderReceipt::Withheld(withheld.clone()));
    let out = result.members.iter().find(|m| m.member.member_id() == withheld.member_id)
        .map(|m| usize::try_from(m.opening_employed)).ok_or("the member")??;
    Ok((result, out))
}

#[test]
fn persons_out_stand_at_the_gate() -> TestResult {
    let (result, out) = struck_period()?;
    let household = shop_a().workers();
    assert!(out > 0);
    assert_eq!(at_the_gate(&result)?.get(&(household, shop_a())).copied(), Some(out));
    let gate = layout::gate_of(shop_a());
    let wage = (WORKPLACE_X[shop_a().index()], WAGE_ANCHOR_Y);
    let distance = |a: Point, b: Point| (a.0 - b.0).hypot(a.1 - b.1);
    let people = build_picture(&result, ParticleMode::People)?;
    let mut at_gate = 0;
    for k in 0..out {
        let at = people.positions.get(&person_id(household, k)).ok_or("a person")?;
        if distance(at, gate) < distance(at, wage) { at_gate += 1; }
    }
    assert_eq!(at_gate, out);
    let groups = build_picture(&result, ParticleMode::Groups)?;
    let at = groups.positions.get(&household_id(household)).ok_or("the group")?;
    assert!(distance(at, gate) < GROUP_SPREAD.0, "{at:?} {gate:?}");
    Ok(())
}

#[test]
fn no_hours_go_in_from_them() -> TestResult {
    let (result, _) = struck_period()?;
    let picture = build_picture(&result, ParticleMode::Groups)?;
    let body = hypergraph_rs_bevy::plan_to_scene((WORKPLACE_X[shop_a().index()], 0.0), MARK_Y);
    let into: u64 = picture.frame.flows.iter()
        .filter(|f| f.stream == STREAM_WORK && near(f.to, body)).map(|f| f.amount).sum();
    let given: u64 = picture.reading.work.iter().filter(|f| f.workplace == shop_a()).map(|f| f.given).sum();
    assert_eq!(into, given);
    assert!(picture.reading.work.iter()
        .filter(|f| f.workplace == shop_a() && f.household == shop_a().workers())
        .all(|f| f.given == 0 && f.idle == 0));
    Ok(())
}
```
(`a_world_with_no_fight_draws_as_before` of Task 2c and `without_a_stoppage_every_frame_is_as_before` of Step 1 run
unchanged beside them.)

In `C/layout.rs`'s tests:
```rust
#[test]
fn a_gate_stands_below_its_workplace() {
    for w in Workplace::ALL {
        assert_eq!(gate_of(w), (WORKPLACE_X[w.index()], -GATE_BELOW));
    }
}
```

In `C/scene_tests.rs`:
```rust
#[test]
fn the_shock_button_reads_apply() -> TestResult {
    let mut app = scene_app(None)?;
    updates(&mut app, 2);
    let all = texts(&mut app);
    assert_eq!(all.iter().filter(|t| *t == "Apply").count(), Shock::ALL.len());
    assert!(!all.iter().any(|t| t == "Strike"));
    Ok(())
}
```
and in `a_strike_from_the_controls_holds_from_the_next_period` and the two tests that send the command,
`ShockButton::Strike` and `SceneCommand::Strike` become `ShockButton::Apply` and `SceneCommand::Apply`.

- [ ] **Step 4: See them fail.** `mise run rust:test:q -- -p babylon-client -E 'test(small_world)'`. Expected:
  does not compile: no `gate_of`, `at_the_gate`, `ShockButton::Apply`, `SceneCommand::Apply`.
- [ ] **Step 5: Implement the gate** (`layout.rs`, `frame.rs`, `fight.rs`): `gate_of`, `withheld_of`,
  `at_the_gate`; `Population::of` takes the map into `out_at`; `stand` and `stand_people` as "What is drawn"
  says. `panel_rows` appends, while the period's fight is `Some`: for a picked workplace with persons out,
  `("Out at the gate", grouped(sum over households))`; for a picked household or its particle, one row for each
  workplace where it has persons out, in `Workplace::ALL` order, `("Out at the gate of {w.label()}", grouped(persons))`.
- [ ] **Step 6: The word.** Rename as Files says. The caption of `spawn_shock`'s last button is `"Apply"`.
- [ ] **Step 7: See them pass.** `mise run rust:test:q -- -p babylon-client -E 'test(small_world)'`. Expected:
  all pass; `a_world_with_no_fight_draws_as_before` and `without_a_stoppage_every_frame_is_as_before` unchanged.
- [ ] **Step 8: Run the companion's gate. Commit** `feat(client): the people at the gate, and a shock is applied`
  (body: `Part of PER-371`).

**What this task must not do:** move a position by hours (the gate is a home, a constant; persons are counted
from member receipts); draw a flow the receipts do not hold; rename the script's `strike` key or
`Runner::strike`; change any frame of a world with no fight (`a_world_with_no_fight_draws_as_before`) or of a
fight world's period with no withheld receipt (`without_a_stoppage_every_frame_is_as_before`).

---

### Task 5: Withheld hours filled above the rolls; whose places are taken

The floor (`FloorOrder`), the cause `Named` and the kind `TakenOn` are built here too, so that `NotBuilt` and
its refusal go; they are reached on screen only in Part Two, and the contract says so.

**Files:**
- Create: `E/orders/staffing.rs` (the staffing orders' checks and arithmetic, and their records of layoffs);
  `T/period_orders/struck_work.rs`.
- Modify: `E/orders/attendance.rs` (`OrderedHours::of` fills `above` and `paid_floor`; `above_receipts`);
  `E/orders/validate.rs` (steps 5c to 5e; step 5 and `NotBuilt` go); `E/orders/error.rs` (`NotBuilt`
  removed); `E/staffing/place.rs` (`PlaceRules`, 82-93; `Slot`, 96-109; `pools_decided`, 191-227;
  `member_after`, 401-420; `staff_places`, 425-465; `conclude`, 468-; `PlaceStaffing`, 34-60; and the test
  literal of `PlaceRules` in `run`, 691, with the test `Case`, 650-660); `E/staffing/transition.rs`
  (`advance_pool`, 62-123; `advance_staffing_limited`, 146-170); `E/staffing/tests.rs`; `E/transition/state.rs`
  (`close_funded_production`; `staff_in_places`, 844-894; `finish_with_place_staffing`, 929-968);
  `T/period_orders.rs` (`mod struck_work`); `T/period_orders/payments.rs` (delete
  `an_order_of_a_kind_not_built_is_refused`); the contract and the digest.

**Interfaces:**

Consumes (Task 1) `AboveRollsOrder`, `AboveRollsCause`, `FloorOrder`, `StaffingOrder`, `StaffingOrderKind`,
`AboveRollsReceipt`, `FloorReceipt`, `FloorHeld`, `StaffingOrderReceipt` (with `moved`), `OrderedHours`,
`ClosedMaterialPeriod.orders`, `PlaceStaffingError::Order`; (Task 3) `RateOrder`; (Task 4) `withheld_hours`,
`withheld_receipts`, `Withheld` receipts in `transition.orders`; the support helpers.

Produces:

```rust
// E/orders/attendance.rs
/// One receipt per above-rolls order, in key order. `attended_hours` is the hours attended above the rolls:
/// `attended.saturating_sub(capacity - withheld).min(hours)`, with `attended` the member's ledger row,
/// `capacity` its labor row of the period and `withheld = withheld_hours(capacity, share_bps)` (0 unordered).
pub(crate) fn above_receipts(state: &MaterialCircuitState, orders: &PeriodOrders, ledger: &AttendanceLedger)
    -> Result<Vec<OrderReceipt>, MaterialCircuitError>;
// E/orders/staffing.rs
/// PF13: `persons` displaced over the striking members by largest remainders of their employed, in member
/// order; members with a share of 0 are left out.
pub(crate) fn displaced_shares(persons: u64, striking: &[(StaffingMemberId, u64)])
    -> Result<Vec<(StaffingMemberId, u64)>, StaffingError>;
/// What one staffing order does to what the close leaves: `moved = min(persons, reserve, room + struck)` (no
/// room: no limit at the host; `struck` is `Some` only for a place taken, the striking slots' employed now)
/// and `displaced = min(moved, struck)`. `Arithmetic` on overflow.
pub(crate) fn order_amounts(persons: u64, reserve: u64, room: Option<u64>, struck: Option<u64>)
    -> Result<(u64, u64), StaffingError>;
/// A member's record of layoffs after its staffing orders, from the record its engine decision and the close's
/// moves give: `called_back` leave the newest cohorts first (then the uncovered, who have no cohort); then
/// `displaced` start a cohort of this close (index 0). Persons taken on from another pool draw down no
/// cohort of the slot they arrive in: they are not an argument. Trailing zeros dropped;
/// `PublicProgramInvariant` when the record would cover more than `closing_reserve`.
pub(crate) fn after_orders(cohorts: &[u64], called_back: u64, displaced: u64, closing_reserve: u64)
    -> Result<Vec<u64>, MaterialCircuitError>;
/// What the finish applies after `advance_records`: one row per member whose record is kept and that a
/// staffing order called back or displaced.
pub(crate) struct OrderRecord { pub(crate) member_id: StaffingMemberId, pub(crate) hours_per_person: u64,
    pub(crate) called_back: u64, pub(crate) displaced: u64, pub(crate) closing_reserve: u64 }
/// Each row's record set to `after_orders(its cohorts or [], ..)`, a new `LayoffRecord` made when there was
/// none, an empty one dropped; the list stays in member order.
pub(crate) fn apply_order_records(records: &mut Vec<LayoffRecord>, rows: &[OrderRecord])
    -> Result<(), MaterialCircuitError>;
// E/staffing/transition.rs (crate-private; `advance_staffing` passes an empty map)
pub(crate) fn advance_staffing_limited(opening: &StaffingState, requests: &[StaffingWorkRequest],
    limits: &BTreeMap<SiteId, u64>, floors: &BTreeMap<SiteId, u64>) -> Result<StaffingTransition, StaffingError>;
// E/staffing/place.rs: PlaceRules gains `floors: &BTreeMap<SiteId, u64>`, `moves: &[StaffingOrder]` and
// `striking: &BTreeSet<StaffingMemberId>`; PlaceStaffing gains `pub(crate) order_receipts: Vec<OrderReceipt>`
// and `pub(crate) order_records: Vec<OrderRecord>`.
```

`AboveRollsOrder` (both causes), `FloorOrder`, `StaffingOrder` (both kinds) applied (points 3 and 7 of The
engine's orders); `NotBuilt` and the step that gives it are gone; `OrderKind` stays (the runner's news names
it). A staffing order may name one slot as both ends (`from_pool == host_pool` and `from_member == to_member`):
the persons are called back from that member's own reserve. The taker household's member at the struck
workplace `w` is `w.pair_member_id(home)`, which is `w`'s own member when `w` is the household's home
(`W/ids.rs:178-185`); no check or test of this task assumes a pair member.

**Orders are applied to what the close leaves.** The orderer builds its staffing orders at the opening, from
the persons it sees then; the engine's decision of the same close hires and separates in proportion over every
member (`E/staffing/members.rs:229-260`). So an order moves what the decision and the earlier orders of the
close leave, within the stop rule's limit at the host, and its receipt says what it moved (`moved`) and whom it
displaced; an order that moves nothing has its receipt with `moved: 0`. Only what contradicts the opening is
refused. After staffing orders, the persons of each member are in `PlaceStaffing.members` (the runner's kept
members); `member_receipts`, and so `PeriodResult.members`, stay the engine's decision before any move or order.
A person whose place is taken is laid off at that close and covered from the next period (design call 46: where
the rest of the stoppage goes on, the law would hold that benefit back until it ends; Part Two builds that
delay).

- [ ] **Step 1: Write the failing tests** in `T/period_orders/struck_work.rs` and the unit tests. The helpers
  read the opening, as an orderer does (`runner.members()` for persons employed and in reserve, the state's
  `member_labor` rows for hours), on one run (fund world with the seekers, harvest failed in Both until lifted);
  each fails with its message when its bound is reached, and then the builder stops and tells the lead:
  - `layoff_period()`: Task 3's loop, the first opening with a record of layoffs (at most 40 steps).
  - `taking_period() -> (Period, PeriodOrders)`: the first opening (at most 60 steps) with a member of reserve
    `>= 1` at a workplace `p`, of a household not `Workers(h)`, and another workplace `h` of the same place whose
    own member employs `>= 1` with a labor row `>= 10`, at which the orders of the place-taken test (withheld
    `h`'s own member 10_000; above 10 `StruckWork` on the taker's member at `h`; `StaffingOrder { host_pool:
    h.pool_id(), to_member, from_pool: p.pool_id(), from_member, persons: 1, kind: PlaceTaken }`) close with a
    receipt of `moved == 1`.
  - `laid_off_at_host_period() -> (Period, PeriodOrders)`: the first opening (at most 80 steps) with, in one
    workplace `w`'s pool, a member `m` of reserve `>= 1` and a member `s` of another household employing `>= 1`
    with a labor row `>= 10`, at which the orders (withheld `s` 10_000; above 10 `StruckWork` on `m`;
    `StaffingOrder { host_pool: w.pool_id(), to_member: m, from_pool: w.pool_id(), from_member: m, persons: 1,
    kind: PlaceTaken }`) close with `moved == 1`. After the seekers' first moves (period 16 of this run) pair
    members hold persons and the engine separates over every member's employed, so `m` can be the own member or
    a pair member.
  - `two_on_the_rolls_period()`: the first opening (at most 80 steps) at which one workplace's pool has two
    members of two households, `x` and `y`, each with a labor row `>= 10`.
  - `hired_back_period()`: the first opening (at most 80 steps) at which a member of reserve `r >= 1` at a
    workplace `p` is left by the engine's decision with `closing_reserve < r` (read from a close with
    `PeriodOrders::none`: staffing orders act after the decision and change nothing before it, so a close with
    only a `TakenOn` makes the same decision), with another workplace `q` of the same place.
  In the tests the taker household's member at a workplace `h` is `h.pair_member_id(home)`, `home` the
  workplace whose workers are that household (the own member when `h` is its home). "Against the engine's
  decision" means against `placed.member_receipts` and the close's `PlaceMove`s to and from each member.
  - `struck_work_is_paid_through_the_taker_s_pair_member`: `opening(&fund_world())`; `WithheldOrder { farm A's
    own member, 10_000 }`, `AboveRollsOrder { farm_a.pair_member_id(shop_a), 20, StruckWork }`. The pair row:
    `available 20, planned 20, attended 20, accrued $200`, payee shop A's workers (shares over farm A's members
    in member order, own first: capacities `[0, 0, 0, 0 + 20]`); a `WageAccrualReceipt { employer: Site(farm
    A), payee: Household(shop A's workers), amount: $200, .. }`; `AboveRollsReceipt { period: 1, member_id,
    site_id: farm A, payee: shop A's workers, hours: 20, attended_hours: 20, cause: StruckWork }`; farm A's
    `produced_batches == 2` (20 hours at 10 a batch).
  - `a_household_cannot_fill_hours_its_people_withhold`: withheld farm A's own member, above 10 on the same
    member: `Order(OwnPeopleStopped { member_id: farm A's own })`; withheld farm A's own member and
    `farm_a.pair_member_id(shop_a)` (0 hours), above 10 on that pair member: `OwnPeopleStopped { member_id:
    the pair member }`.
  - `a_fill_cannot_pass_the_withheld_hours`: withheld farm A's own member (40 hours); above 30 on the shop's
    pair member and 20 on the clinic's: `Order(FillPassesWithheld { site_id: farm A, withheld: 40, filled: 50
    })`. In the same test, above 10 `StruckWork` at clinic A with nothing withheld there:
    `StruckWorkWithoutStoppage { site_id: clinic A }`; above 0 hours: `NotCanonical`.
  - `a_place_taken_moves_the_taker_for_good_and_lays_off_the_striker`: `taking_period()`. In
    `transition.orders`: `StaffingOrderReceipt { period, order, household_id: the taker's household, moved: 1,
    displaced }`, `displaced` naming `h`'s own member and summing to `min(1, its employed after the engine's
    decision)`. Against the engine's decision, in `placed.members`: `h`'s own member employed fewer and reserve
    more by that sum, the taker's member at `h` employed one more; in the finished state's
    `financial.layoffs`, `h`'s own member's record has `cohorts[0]` at least that sum (a cohort of this close:
    covered from the next period).
  - `a_place_is_taken_by_the_workplace_s_own_laid_off`: `laid_off_at_host_period()`. The close is `Ok` through
    the finish (the record of layoffs it advances matches `PlaceStaffing.records`). `StaffingOrderReceipt {
    period, order, household_id: m's household, moved: 1, displaced }`, `displaced` naming `s`; against the
    engine's decision `m` employed one more and reserve one fewer with its labor force unchanged, `s` employed
    fewer and reserve more by `displaced`; `m`'s `AboveRollsReceipt.attended_hours ==
    attended.saturating_sub(capacity).min(10)` from `m`'s own `MemberLaborUseReceipt` and labor row; `s`'s
    record has `cohorts[0] >=` its displaced persons.
  - `an_order_moves_what_the_close_leaves`: `hired_back_period()`; `StaffingOrder { host_pool: q.pool_id(),
    to_member: q.pair_member_id(home), from_pool: p.pool_id(), from_member, persons: r, kind: TakenOn }`: no
    refusal (`r` is the reserve the orderer saw); the receipt has `moved` equal to the from member's
    `closing_reserve` in the engine's decision, so `moved < r`, and `displaced` empty; the to member employs
    `moved` more than the engine's decision.
  - `a_place_taken_displaces_what_is_still_out` (in `E/orders/staffing.rs` tests, `order_amounts`):
    `(3, 2, None, None) == (2, 0)`; `(3, 5, Some(1), None) == (1, 0)` (a taking on stops at the limit);
    `(3, 5, None, Some(1)) == (3, 1)` (only one of those out is still on the rolls); `(3, 5, Some(0), Some(1))
    == (1, 1)` (the room counts the person displaced); `(3, 1, None, Some(3)) == (1, 1)`.
  - `the_takers_persons_stay_in_reserve_while_they_work_above_the_rolls` (Review Focus 3, the engine's half;
    Task 5c pins the screen): `taking_period()`'s period and orders without the `StaffingOrder`: the
    `AboveRollsReceipt` has `attended_hours == attended.saturating_sub(capacity).min(10)` from the taker
    member's `MemberLaborUseReceipt` and labor row, and `> 0`; in `placed.members` the reserve member and the
    taker's member at `h` are as the engine's decision leaves them; the taker's member's labor row of the next
    period is its employed persons times 10, the above hours not in it.
  - `a_covered_taker_s_benefit_in_a_period_of_struck_work` (Review Focus 3, pinned as it is: design call 36):
    `layoff_period()`; the household `H` of a member with a record; `h` a workplace of its place other than its
    home with its own row `>= 10` hours; orders: withheld `h`'s own member 10_000, above 10 `StruckWork` on
    `h.pair_member_id(home of H)`. Its `laid_off` `PublicProgramReceipt` has the same `due` and `paid` as in the
    close with `PeriodOrders::none`, and `paid > 0`; a `WageAccrualReceipt` pays `H` from `Site(h)`.
  - `fewer_takers_than_places_split_by_the_layoff_order`: in `E/orders/staffing.rs` tests:
    `displaced_shares(3, &[(m1, 4), (m2, 2)]) == [(m1, 2), (m2, 1)]`; `displaced_shares(1, &[(m1, 1), (m2,
    1)]) == [(m1, 1)]`; `displaced_shares(2, &[(m1, 1)])` is `Err(PopulationInvariant)`.
  - `a_floor_holds_the_target_and_yields_to_the_stop_rule`: in `E/staffing/tests.rs`, with `binding(1, 5, 10,
    &[1])`, `pool(binding, 4, 0)` and `request(&binding, 1, 0)`: floor 3 gives `target_employed 3`
    (separations 1); floor 5 gives 5 (hires 1); floor 5 and limit 2 give 2. In `struck_work.rs`, the world of
    Task 3's `a_rise_the_cash_cannot_pay_leaves_hours_unpaid` with its `RateOrder { farm A, $30 }` and
    `FloorOrder { pool_id: farm A's pool, site_id: farm A, unit_id: hours, persons: 4, paid_hours: 0 }`:
    `FloorReceipt { period: 1, pool_id, persons: 4, held: GaveWayToStop { limit: 3 }, paid_hours: 0 }` and farm
    A's pool employs 3 in `placed.state`; the floor alone in `fund_world()`: `held: Held`, farm A employs 4.
  - `a_paid_floor_pays_idle_hours`: `fund_world()`, `AboveRollsOrder { farm_a.pair_member_id(shop_a), 20,
    Named }` (no stoppage needed) and `FloorOrder { farm A's pool, farm A, hours, persons: 4, paid_hours: 60 }`:
    farm A plans 60 hours (`max(40, 60).min(40 + 20)`): own row attended 40, pair row 20, $600 in all; farm A's
    `LaborUseReceipt.paid_idle_hours >= 20` (four batches use 40).
  - `hours_above_the_rolls_add_to_hours_on_them`: `two_on_the_rolls_period()`; withheld `x` 10_000, above 10
    `StruckWork` on `y` (its payee withholds nothing there): the close is `Ok`; `y`'s `MemberLaborUseReceipt`
    has `available_hours == capacity_y + 10`; its `AboveRollsReceipt.attended_hours ==
    attended_y.saturating_sub(capacity_y).min(10)`.
  - `hours_above_the_rolls_are_counted_after_the_rolls_hours`: `opening(&fund_world())`; withheld farm A's own
    member 5_000 (rolls 40, withheld 20) and `AboveRollsOrder { farm A's own member, 10, Named }` (only struck
    work is refused by its own household's withholding): offered 30,
    planned 30, attended 30, and `attended_hours == 10`. With also `RateOrder { farm A, hours,
    Currency::from_micro_units(35_200_000) }` the cash pays 25 hours ($880 / $35.20): `attended_hours == 5`.
  - `the_record_of_layoffs_dates_every_person_moved_by_an_order` (in `E/orders/staffing.rs` tests,
    `after_orders`): `(&[1, 2], 0, 0, 3) == [1, 2]` (no order changes nothing); displaced start a cohort of
    this close: `(&[0, 2], 0, 1, 3) == [1, 2]`, `(&[], 0, 2, 2) == [2]`; called back leave the newest first:
    `(&[1, 2], 2, 0, 1) == [0, 1]`, and past the cohorts from the uncovered: `(&[1], 3, 0, 0) == []`; called
    back before displaced: `(&[1], 1, 2, 2) == [2]`; `(&[2], 0, 1, 2)` is `Err(PublicProgramInvariant)`.
  - In `E/staffing/place.rs` tests, on the harness `case(..)` and `run` (650-700), with the recipients and a
    record of window 7:
    - `the_own_laid_off_are_called_back_as_a_call_back_is`: one pool whose member of household 1 employs 1 and
      holds 2 in reserve under the record `[2]`, asking one person's hours (the engine's receipt shows no hire
      and no separation); a `TakenOn` from that member to itself of 2: it employs 3 with reserve 0 and its labor
      force 3, its receipt has `moved: 2`, and `records` holds no row for it.
    - `taken_on_draws_down_no_cohort_where_it_arrives`: two pools of one place; household 1 holds 1 covered in
      reserve under `[1]` in pool 1 and 1 uncovered in pool 2's reserve; a `TakenOn` of 1 from pool 2's member to
      pool 1's: pool 1's member employs one more, and its row of `records` is `[1]`, the same as in the case
      without the order.
    - `no_order_keeps_every_staffing_byte`: every existing case of the harness, with the new fields empty,
      gives the same `PlaceStaffing` as before (the existing tests pass unchanged).
  - `staffing_orders_are_checked_against_the_staffing`, each refusal `Refused::Close(Order(..))` or
    `Refused::Place(PlaceStaffingError::Order(..))` as written:
    - `World::scene()` (no seekers) with a floor: `Close(StaffingWithoutSeekers)`;
    - a move naming member `[99; 32]`: `Close(UnknownMember(..))`; persons 0: `Close(NotCanonical)`;
    - a floor at farm A's site with `UnitId [7; 32]`: `Close(NoWageAt { .. })`;
    - a floor of farm A's pool naming clinic A's site: `Place(FloorNotThePool { pool_id, site_id })`;
    - host farm A's pool, from shop B's pool: `Place(MoveOutOfPlace { host_pool, from_pool })`;
    - host and from farm A's pool, to farm A's own member, from `farm_a.pair_member_id(shop_a)` (the same pool,
      two different members): `Place(MoveOutOfPlace { host_pool, from_pool })`;
    - `PlaceTaken` at farm A with nothing withheld there: `Place(DisplacesMoreThanStruck { host_pool, struck:
      0, persons: 1 })` (no member of farm A's pool is striking at the opening);
    - `TakenOn` at farm A from shop A's own member at period 1 (nobody in reserve at the opening):
      `Place(MoveFromNoReserve { from_member, reserve: 0, persons: 1 })`;
    - two orders out of one member whose persons sum past its reserve at the opening: `MoveFromNoReserve` with
      `persons` the sum.
  - `persons_are_conserved_in_each_place`: in the run of the place-taken test, for each place the sum of
    employed and reserve over every member of its four pools in `placed.members` equals that sum in
    `runner.members()` before the close.
- [ ] **Step 2: Run them and see them fail:** `mise run rust:test:q -- -p babylon-material-circuit --test
  period_orders` and `mise run rust:test:q -- -p babylon-material-circuit -E 'test(floor) |
  test(fewer_takers) | test(displaces_what) | test(dates_every) | test(called_back) | test(taken_on_draws) |
  test(no_order_keeps)'`. Expected: the first with `NotBuilt(AboveRolls)`, `NotBuilt(Floor)` and
  `NotBuilt(Staffing)`; the second does not compile (no `displaced_shares`, `order_amounts`, `after_orders`,
  and `advance_staffing_limited` takes no floors).
- [ ] **Step 3: Validation at the close.** Step 5 (and `NotBuilt` with it) goes. New steps, before the fund
  payments:

  ```text
  5c each above-rolls order, in key order:
       no employment row with member_id -> UnknownMember; not Wage -> NotAWage { member_id }; hours == 0 -> NotCanonical
       StruckWork: no withheld order at the member's site          -> StruckWorkWithoutStoppage { site_id }
                   a withheld order at that site has the same payee -> OwnPeopleStopped { member_id }
     then each site, in site order: StruckWork hours there summed (checked) > the withheld hours there
       (withheld_hours(member row, share_bps) summed over its withheld orders) -> FillPassesWithheld { site_id, withheld, filled }
  5d floors and moves not empty and the catalog does not ask for SeekingInPlace -> StaffingWithoutSeekers
     (read with crate::adjustment::asks on catalog.market_clearing, as state.rs:1054-1059 does)
  5e each floor: no Wage row at (site_id, unit_id) -> NoWageAt { site_id, unit_id }
     each move: to_member or from_member with no employment row -> UnknownMember; persons == 0 -> NotCanonical
  ```

  Nothing in 5c asks for a member with nobody on its rolls: an above-rolls order on a member with hours on the
  rolls whose payee withholds nothing at that site is accepted, and its offered hours are its rolls' hours less
  any withheld plus the hours above (`OrderedHours::offered`). An above-rolls order of 0 hours and a staffing
  order of 0 persons are `NotCanonical`: an order of nothing is not canonical input.

- [ ] **Step 4: Hours above the rolls and the paid floor.** `OrderedHours::of` fills `above` (hours by member)
  and `paid_floor` (`paid_hours` by the floor's `(site_id, unit_id)`). In `close_funded_production`,
  `above_receipts(state, orders, &attendance)?` between `fund_attendance` and `costs.admit_attendance`; its
  receipts go into `orders` after the withheld receipts and before the wage shares'. A receipt's
  `attended_hours` is the hours attended above the rolls: `attended.saturating_sub(capacity -
  withheld).min(hours)`, `attended` the member's row in the ledger, `capacity` its labor row of the period,
  `withheld = withheld_hours(capacity, share_bps)` of its withheld order (0 when none). `fund_member_attendance`
  pays one figure for the member's whole row (`min(cash / rate, planned)`, `attendance.rs:371-376`) and splits
  nothing, so the split is this reading: the rolls' hours are attended first, and the taker's count (the runner
  and the scene count takers from this field) never includes hours the member works on its own rolls.
- [ ] **Step 5: The floor in the staffing.** `advance_pool` gains `floor: u64`: `target =
  requested_people.max(floor).min(labor_force).min(limit)`, so the stop rule's limit wins (PF12).
  `advance_staffing_limited` passes `floors.get(&site)` (0 when absent). In `pools_decided`, `people =
  asked.div_ceil(hours).max(floor)`, then less `closing_employed` and the limit as today. In `staff_in_places`,
  `floors` is built from `self.orders`' floor orders by `site_id`, and the stop round's limits are read first;
  for each floor a `FloorReceipt`: `held = GaveWayToStop { limit }` when the site has a limit below `persons`,
  else `Held`.
- [ ] **Step 6: The staffing orders** in `staff_places`. Every refusal comes first, before the engine's
  decision, and reads only the opening of this staffing, what the orderer saw: `members: &[PoolMembers]` (each
  `StaffingMemberState`'s `employed()` and `reserve()`) and `at`. Then, after `pools_decided` and before the hosts
  are chosen, each order in key order is applied to what the close leaves (errors are
  `PlaceStaffingError::Order`):

  ```text
  refusals, each order in key order, then the sums:
    host_pool or from_pool not in `at`, or not in one place             -> MoveOutOfPlace { host_pool, from_pool }
    from_pool == host_pool and from_member != to_member                 -> MoveOutOfPlace { host_pool, from_pool }
    to_member not a member of host_pool, from_member not one of from_pool,
      or their households differ                                        -> MoveOutOfPlace { host_pool, from_pool }
    each from member: persons ordered out of it, summed (checked), > its reserve() in `members`
                                                                        -> MoveFromNoReserve { from_member, reserve, persons }
    each host_pool: PlaceTaken persons there, summed, > the employed() in `members` of its members in `striking`
                                                                        -> DisplacesMoreThanStruck { host_pool, struck, persons }
  apply, each order in key order, after pools_decided:
    employed_now(pool) = sum over its slots of closing_employed + taken_on + called_back - displaced
    reserve_now = the from slot's uncovered + sum(covered), as earlier orders of this close left them
    room   = the host site's stop limit, less employed_now(host) (saturating); None when the site has no limit
    struck = PlaceTaken: Some(sum over the host's striking slots of closing_employed - displaced); TakenOn: None
    (moved, displaced) = order_amounts(persons, reserve_now, room, struck)
    displaced_shares(displaced, the striking slots' employed now) -> each slot.displaced += share
    two slots (from_pool != host_pool): take `moved` from the from slot, uncovered first then covered by age 0..
                (as Taking::fill, into left_uncovered / left_covered); to slot.taken_on += moved
    one slot (from_pool == host_pool, from_member == to_member): take `moved` from the slot's own reserve as a
                call-back is: covered by age 0.. (newest laid off first), then uncovered, lowering `covered` and
                `uncovered`; slot.called_back += moved
    receipt StaffingOrderReceipt { period: opening.period(), order, household_id, moved, displaced }
  then each pool's need is reckoned again from employed_now, never above what pools_decided gave
  ```

  So a `TakenOn` takes no more than the room the stop rule's limit leaves, and a `PlaceTaken` counts the persons
  it displaces in that room (PF12: the limit wins). `striking` is built in `staff_in_places` from
  `self.transition.orders`: the members of `Withheld` receipts with `withheld_hours > 0`; `moves` from
  `self.orders`. Displaced persons are not offered to the hosts of the same close: they join the slot's reserve
  after the fills. `to_member` may be the host's own member (the taker is the workplace's own household and those
  out are a pair household's); nothing here reads which it is.

  `Slot` gains `taken_on`, `called_back` and `displaced`. `member_after`: `employed = closing_employed + gained +
  taken_on + called_back - displaced`, `reserve = closing_reserve - left_uncovered - left_covered - called_back +
  displaced` (checked), so a call-back leaves the member's labor force as it was. `record_receipt(slot)` is
  unchanged and reads none of the three: it is the receipt of the engine's decision and the close's moves (an
  order's two-slot taking is one of those moves, through `left_*`), and it is still what `record_receipts`
  publishes and what `advance_records` advances at the finish.

  **The record of layoffs after staffing orders.** It equals the record advanced by the engine's decision and
  the close's moves, then by the orders: persons displaced start a cohort of this close; persons called back
  leave the newest cohorts; persons taken on from another pool draw down no cohort of the slot they arrive in.
  One `StaffingMemberReceipt` cannot carry this (its `validate` refuses hires and separations both, and a hire
  would draw down the arriving slot's cohorts), so it is carried in two steps, by the same functions in
  `conclude` and in the finish: first `crate::financial::advance_layoffs(held, window, &record_receipt(slot)?)`,
  then `after_orders(that, called_back, displaced, reserve after the orders)`. In `conclude`, for a slot with
  `taken_on`, `called_back` or `displaced` above 0 whose record is kept (`rules.window > 0` and its household
  in `rules.recipients`), the row of `records` is those two steps' result (dropped when empty), and when
  `called_back` or `displaced` is above 0 an `OrderRecord` goes into `order_records` (with the slot's
  `hours_per_person` and its reserve after the orders). `order_receipts` holds the floor receipts then the
  staffing receipts.
- [ ] **Step 7: Publish.** `finish_with_place_staffing`, after `advance_records(economy, closing,
  &staffing.record_receipts)` and before it compares the record with `staffing.records`, calls
  `orders::staffing::apply_order_records(&mut economy.financial.layoffs, &staffing.order_records)?`; then it
  extends `self.transition.orders` with `staffing.order_receipts` after the moves are put in `adjustments`.
- [ ] **Step 8: Run them and see them pass** (the commands of Step 2, then `--test period_orders` whole).
- [ ] **Step 9: The contract.** Replace "and a kind not yet built is refused" in `ADR323_orders` with "the
  floor, hours for people named in a demand and taking on are built and reached on screen only in Part Two";
  after `ADR323_withheld` add these two keys; recompute the digest:

  ```yaml
    ADR323_above_rolls: >-
      an order of hours above the rolls adds hours to a member this period, paid through its terms: for struck
      work only at a workplace with hours withheld in the same orders, never through a household that withholds
      there, and in all no more than the hours withheld there; or for people named in a demand; the hours offered
      are the rolls' less the withheld plus those above; the people above the rolls stay in their reserve; a
      floor order makes a workplace's plan pay at least its hours, idle where there is no work, and its pool's
      target at the close at least its persons, the stop rule's limit first; each has a receipt, whose hours
      attended above the rolls are those the member attended beyond its rolls' hours offered
    ADR323_staffing_orders: >-
      a staffing order moves persons for good at the close's staffing, after the engine's decision and before the
      hosts fill, from a member's reserve (the uncovered first, then the covered, the newest laid off first) to
      the host's member of the same household in the same place, or calls persons back from the host member's
      own reserve as the staffing calls back (the newest laid off first); it moves what the decision and the
      earlier orders leave, within the room the stop rule's limit leaves at the host, and its receipt says what
      it moved; a place taken also moves as many of the persons still out at the host (its members that withheld
      hours this period) from employed to reserve, shared by largest remainders of their employed: a person whose
      place is taken is laid off at that close and covered from the next period (where the rest of the stoppage
      goes on, the law would hold that benefit back until it ends; that delay is built later); the record of
      layoffs dates the displaced from this close, takes the called back from the newest cohorts, and draws down
      no cohort where persons taken on arrive; taken on moves only; an order is refused when it names members
      out of one place or two members of one pool, takes more out of a member than its reserve at the opening,
      or takes more places at a host than were out there at the opening; each has a receipt
  ```

- [ ] **Step 10: Run the scoped engine gate;** then the 14 long tests in the background (Global Constraints).
  Expected: 14 of 14. (The live database tests are the lead's.)
- [ ] **Step 11: Commit** `feat(material-circuit): withheld hours filled above the rolls, and places taken`. The
  body: struck work is paid through the taker's member at the struck workplace and its people stay in reserve;
  a staffing order moves what the close leaves and says what it moved; a place taken moves the taker for
  good, or calls back the workplace's own laid off, and lays off as many of those still out, by largest
  remainders, dated from that close in the record of layoffs; the floor, named hours and taking on are
  built for Part Two; every kind of order is now built; the contract lines and the digest change together.
  `Part of PER-371`.

**What this task must not do:**
- Put a taker on a roll for the period it works above it: its persons stay in its member's reserve; only a
  `StaffingOrder` at a close moves persons.
- Offer displaced strikers to another host in the same close, or let a floor pass the stop rule's limit.
- Change `PlaceMoveReceipt`, add an `AdjustmentReceipt` variant, or change what the staffing does when no
  staffing order and no floor is given (`PlaceRules` empty: the same targets, needs, moves and records).
- Decide who takes struck work or when a place counts as taken: the runner orders (Task 8).

---

### Task 5c: Struck work and who takes it

After this task a person sees who takes struck work and whose places are taken, in neutral words: the struck
workplace's panel says "Struck work taken by Place A farm workers", "Places taken by Place A farm workers" (or
"Called back into places taken: Place A shop workers" when a workplace's own laid off are called back) and "Laid
off when places were taken: Place A shop workers"; the taker's panel says "Took struck work at Place A shop". On
the plane the takers' hours already go from their home to the struck workplace (their member receipts at the
host); in the people view the persons who took it stand at the struck workplace with its workforce. The offer of
struck work comes with Task 8 (`PeriodFight.offered`), so its row is Task 8c's. Until Task 8 nothing takes struck
work, so this is seen in the proof of Task 8c.

**Files:**
- Modify: `C/frame.rs` (`Population` gains `above_at`; `person_ranges` (449-470) places them); `C/fight.rs`
  (`above_of`, `placed_of`, `struck_rows`, the taker's and the displaced household's rows in `panel_rows`,
  `REFUSED_WORDS`); `C/inspect.rs` (nothing but the call through `panel_rows`). Tests in `C/frame.rs` and
  `C/fight.rs`.

**Interfaces:**

Consumes (Task 5): `OrderReceipt::AboveRolls(AboveRollsReceipt { period, member_id, site_id, payee, hours: u64,
attended_hours: u64, cause: AboveRollsCause })` (`StruckWork`, `Named`; `attended_hours` is the hours attended
above the member's rolls' hours, `hours` what was ordered); `OrderReceipt::Staffing(StaffingOrderReceipt { period,
order: StaffingOrder { host_pool, to_member, from_pool, from_member, persons: u64, kind: StaffingOrderKind },
household_id: FinalDemandPrincipalId, moved: u64, displaced: Vec<(StaffingMemberId, u64)> })` (`moved` is the
persons the engine moved, which can be less than `order.persons` or 0; people moved are read from these receipts,
never from `PeriodResult.members`, which is the decision before any move);
`StaffingMemberReceipt.hours_per_person`. The member that takes struck work at a workplace may be the workplace's
own member, or a pair member that also has persons on the rolls there; a staffing receipt may name one member as
both ends (`order.from_member == order.to_member`: the workplace's own laid off, called back into places taken).

Produces:
```rust
// C/fight.rs
pub fn above_of(result: &PeriodResult) -> impl Iterator<Item = &AboveRollsReceipt>;   // every variant named
pub fn placed_of(result: &PeriodResult) -> impl Iterator<Item = &StaffingOrderReceipt>;
/// A struck workplace's rows (empty without a fight):
/// ("Struck work taken by {household}", "{attended_hours summed} hours") one row a household, `Household::ALL`
/// order, from `StruckWork` receipts at its site;
/// ("Places taken by {household}", "{moved summed}") from `PlaceTaken` receipts whose `host_pool` is its pool and
/// whose two members differ; ("Called back into places taken: {household}", "{moved summed}") from those whose
/// `from_member` is their `to_member`; a receipt with `moved: 0` adds to no row, and a row whose sum is 0 is left
/// out;
/// ("Laid off when places were taken: {household}", "{displaced persons summed}") one row a displaced household.
/// # Errors
/// `FrameError::Edge` for a receipt of no household, member or pool of the period; `Arithmetic`.
pub fn struck_rows(result: &PeriodResult, w: Workplace) -> Result<Vec<(String, String)>, FrameError>;
/// The words no row of the fight may hold (whole words, any case): design, "What would make it a failure".
pub const REFUSED_WORDS: [&str; 24] = ["scab", "scabs", "scabbing", "blackleg", "blacklegs", "strikebreaker",
    "strikebreakers", "breaker", "breakers", "fink", "finks", "rat", "rats", "traitor", "traitors", "betrayed",
    "betrayal", "enemy", "enemies", "collaborator", "collaborators", "knobstick", "replacement", "replacements"];
// C/frame.rs, Population gains:
/// Persons of a household above the rolls at a workplace this period: for each `StruckWork` or `Named` receipt,
/// its `attended_hours` over the host member's `hours_per_person`, rounded up, at most the household's persons
/// not employed.
above_at: BTreeMap<(Household, Workplace), usize>,
```
A household's rows, in `panel_rows` for a picked household or its particle: ("Took struck work at {w}",
"{hours} hours") and ("Took places at {w}", "{moved}") as a taker whose two members differ; ("Called back to
{w}", "{moved}") for a receipt with one member as both ends; ("Its places taken at {w}", "{displaced}") as a
household displaced.

What is drawn, as marks: no new mark. Groups view: nothing new; the taker's `WorkFlow` to the host is a member
receipt of its member there (`read_work`, reading.rs:170-198), so its bone dots go from its group to the struck
workplace, and its wages from the host lean it to the host's wage anchor, as every wage does. People view:
`person_ranges` gives a household one range a workplace, its persons employed there and then its persons above
the rolls there (`above_at`): a member that already has persons on the rolls at the host is one range, never two.
A workplace where the household has only persons above the rolls gets its range after the employed ranges, in
`Workplace::ALL` order, before its persons not at work. `stand_people` clusters each range at that workplace's
wage anchor, the persons out of Task 4c last in it; `workforces` (People) finds the range at the host and gives
its persons the household's hours there in order. Read from `AboveRollsReceipt`s.

- [ ] **Step 1: Write the failing tests.**

In `C/frame.rs`'s tests (on Task 4c's `struck_period`):
```rust
fn farm_a() -> Workplace { Workplace { place: Place::A, kind: Kind::Farm } }

/// `struck_period` with one of farm A's workers in reserve, working one person's hours above the rolls at shop A
/// through its pair member there, and one place taken.
fn taken_period() -> Result<(PeriodResult, u64), Box<dyn Error>> {
    use babylon_material_circuit::{AboveRollsCause, AboveRollsReceipt, OrderReceipt, StaffingOrder,
        StaffingOrderKind, StaffingOrderReceipt};
    let (mut result, _) = struck_period()?;
    let taker = farm_a().workers();
    let own = result.members.iter_mut()
        .find(|m| m.site_id == farm_a().site_id() && m.member.household_id() == taker.principal())
        .ok_or("the taker's own member")?;
    own.opening_employed -= 1;
    own.opening_reserve += 1;
    let from_member = own.member.member_id();
    let pair = result.members.iter()
        .find(|m| m.site_id == shop_a().site_id() && m.member.household_id() == taker.principal())
        .ok_or("the taker's pair member at the shop")?.clone();
    let hours = pair.hours_per_person;
    let row = result.receipts.member_labor_use.iter_mut()
        .find(|r| r.member_id == pair.member.member_id()).ok_or("the pair's labor receipt")?;
    row.attended_hours = hours;
    row.production_hours = hours;
    let striker = result.members.iter()
        .find(|m| m.site_id == shop_a().site_id() && m.member.household_id() == shop_a().workers().principal())
        .ok_or("the striker's member")?.member.member_id();
    result.receipts.orders.push(OrderReceipt::AboveRolls(AboveRollsReceipt { period: result.period,
        member_id: pair.member.member_id(), site_id: shop_a().site_id(), payee: taker.principal(), hours,
        attended_hours: hours, cause: AboveRollsCause::StruckWork }));
    result.receipts.orders.push(OrderReceipt::Staffing(StaffingOrderReceipt { period: result.period,
        order: StaffingOrder { host_pool: shop_a().pool_id(), to_member: pair.member.member_id(),
            from_pool: farm_a().pool_id(), from_member, persons: 1, kind: StaffingOrderKind::PlaceTaken },
        household_id: taker.principal(), moved: 1, displaced: vec![(striker, 1)] }));
    Ok((result, hours))
}

/// A fight world's first period in which farm A's workers' pair member at shop A, with one person on the rolls
/// there, stops, and shop A's own member, with one of its persons laid off, takes that person's hours above its
/// rolls; then the laid-off person is called back into the place taken (one member as both ends).
fn own_taker_period() -> Result<(PeriodResult, u64), Box<dyn Error>> {
    use babylon_material_circuit::{AboveRollsCause, AboveRollsReceipt, OrderReceipt, StaffingOrder,
        StaffingOrderKind, StaffingOrderReceipt, WithheldReceipt};
    let mut result = Runner::open_world(&World::scene_with_fight())?.step()?.clone();
    let (farm, shop) = (farm_a().workers(), shop_a().workers());
    let member_of = |r: &PeriodResult, h: Household, w: Workplace| r.members.iter()
        .find(|m| m.site_id == w.site_id() && m.member.household_id() == h.principal())
        .map(|m| (m.member.member_id(), m.hours_per_person)).ok_or("a member");
    let (striker, hours) = member_of(&result, farm, shop_a())?;
    let (own, _) = member_of(&result, shop, shop_a())?;
    for m in &mut result.members {
        let id = m.member.member_id();
        if m.site_id == farm_a().site_id() && m.member.household_id() == farm.principal() { m.opening_employed -= 1; }
        if id == striker { m.opening_employed += 1; }
        if id == own { m.opening_employed -= 1; m.opening_reserve += 1; }
    }
    result.receipts.orders.push(OrderReceipt::Withheld(WithheldReceipt { period: result.period, member_id: striker,
        site_id: shop_a().site_id(), payee: farm.principal(), rolls_hours: hours, withheld_hours: hours }));
    result.receipts.orders.push(OrderReceipt::AboveRolls(AboveRollsReceipt { period: result.period,
        member_id: own, site_id: shop_a().site_id(), payee: shop.principal(), hours, attended_hours: hours,
        cause: AboveRollsCause::StruckWork }));
    result.receipts.orders.push(OrderReceipt::Staffing(StaffingOrderReceipt { period: result.period,
        order: StaffingOrder { host_pool: shop_a().pool_id(), to_member: own, from_pool: shop_a().pool_id(),
            from_member: own, persons: 1, kind: StaffingOrderKind::PlaceTaken },
        household_id: shop.principal(), moved: 1, displaced: vec![(striker, 1)] }));
    Ok((result, hours))
}

#[test]
fn takers_are_drawn_at_the_struck_workplace() -> TestResult {
    let (result, hours) = taken_period()?;
    let taker = farm_a().workers();
    let groups = build_picture(&result, ParticleMode::Groups)?;
    let flow = groups.reading.work.iter().find(|f| f.household == taker && f.workplace == shop_a())
        .ok_or("the taker's hours at the shop")?;
    assert_eq!(flow.given, hours);
    let workforce = groups.sets.workforces.members_with_data(&workforce_edge(shop_a())).ok_or("the set")?;
    assert!(workforce.iter().any(|(m, v)| *m == household_id(taker) && **v == hours));
    let people = build_picture(&result, ParticleMode::People)?;
    let persons = result.closing.households.iter().find(|c| c.principal_id == taker.principal())
        .map(|c| usize::try_from(c.persons)).ok_or("the taker's persons")??;
    let last = person_id(taker, persons - 1);
    let at = people.positions.get(&last).ok_or("the taker's last person")?;
    let distance = |a: Point, b: Point| (a.0 - b.0).hypot(a.1 - b.1);
    let here = (WORKPLACE_X[shop_a().index()], WAGE_ANCHOR_Y);
    let home = (WORKPLACE_X[farm_a().index()], WAGE_ANCHOR_Y);
    assert!(distance(at, here) < distance(at, home), "{at:?}");
    let shop = people.sets.workforces.members_with_data(&workforce_edge(shop_a())).ok_or("the set")?;
    assert!(shop.iter().any(|(m, v)| *m == last && **v == hours));
    Ok(())
}

#[test]
fn a_taker_already_on_the_rolls_is_one_range() -> TestResult {
    let (result, _) = own_taker_period()?;
    let shop = shop_a().workers();
    let pop = Population::of(&result)?;
    let ranges = person_ranges(&pop, shop);
    let at_shop: Vec<&(Workplace, Range<usize>)> = ranges.iter().filter(|(w, _)| *w == shop_a()).collect();
    assert_eq!(at_shop.len(), 1, "{ranges:?}");
    assert_eq!(at_shop[0].1.len(), pop.at_work_at(shop, shop_a()) + 1);
    let people = build_picture(&result, ParticleMode::People)?;
    let set = people.sets.workforces.members_with_data(&workforce_edge(shop_a())).ok_or("the set")?;
    for k in at_shop[0].1.clone() {
        let id = person_id(shop, k);
        assert_eq!(set.iter().filter(|(m, _)| **m == id).count(), 1, "{id}");
    }
    assert_eq!(at_the_gate(&result)?.get(&(farm_a().workers(), shop_a())).copied(), Some(1));
    Ok(())
}
```

In `C/fight.rs`'s tests (`struck_period`, `taken_period` and `own_taker_period` copied there as helpers: a test
module's items are not visible to a sibling module):
```rust
#[test]
fn struck_rows_are_the_receipts() -> TestResult {
    let (result, hours) = taken_period()?;
    let rows = struck_rows(&result, shop_a())?;
    let taker = farm_a().workers().label();
    let striker = shop_a().workers().label();
    assert_eq!(rows, vec![
        (format!("Struck work taken by {taker}"), format!("{} hours", human_numbers::grouped(u128::from(hours)))),
        (format!("Places taken by {taker}"), "1".to_owned()),
        (format!("Laid off when places were taken: {striker}"), "1".to_owned()),
    ]);
    let pick = Pick::Body(Party::Household(farm_a().workers()));
    let mine = panel_rows(&[result.clone()], 0, &pick)?;
    assert!(mine.contains(&(format!("Took struck work at {}", shop_a().label()),
        format!("{} hours", human_numbers::grouped(u128::from(hours))))));
    assert!(mine.contains(&(format!("Took places at {}", shop_a().label()), "1".to_owned())));
    // A receipt the close left nothing to move gives no row.
    let mut none = result.clone();
    let clinic = Workplace { place: Place::A, kind: Kind::Clinic }.workers();
    let mut empty = placed_of(&result).next().ok_or("the staffing receipt")?.clone();
    empty.household_id = clinic.principal();
    empty.moved = 0;
    empty.displaced = Vec::new();
    none.receipts.orders.push(OrderReceipt::Staffing(empty));
    assert!(struck_rows(&none, shop_a())?.iter().all(|(label, _)| !label.ends_with(&clinic.label())));
    assert!(struck_rows(&Runner::open()?.step()?.clone(), shop_a())?.is_empty());
    Ok(())
}

#[test]
fn a_member_called_back_into_places_taken_is_both_ends() -> TestResult {
    let (result, hours) = own_taker_period()?;
    let (shop, farm) = (shop_a().workers().label(), farm_a().workers().label());
    let rows = struck_rows(&result, shop_a())?;
    assert_eq!(rows, vec![
        (format!("Struck work taken by {shop}"), format!("{} hours", human_numbers::grouped(u128::from(hours)))),
        (format!("Called back into places taken: {shop}"), "1".to_owned()),
        (format!("Laid off when places were taken: {farm}"), "1".to_owned()),
    ]);
    let mine = panel_rows(&[result.clone()], 0, &Pick::Body(Party::Household(shop_a().workers())))?;
    assert!(mine.contains(&(format!("Called back to {}", shop_a().label()), "1".to_owned())));
    assert!(!mine.iter().any(|(label, _)| label.starts_with("Took places at")));
    Ok(())
}

/// Every row of the fight that can name a household that took struck work.
fn rows_about_takers() -> Result<Vec<String>, Box<dyn Error>> {
    let mut all: Vec<String> = Vec::new();
    for (result, _) in [taken_period()?, own_taker_period()?] {
        for w in Workplace::ALL {
            for (label, value) in struck_rows(&result, w)? { all.push(label); all.push(value); }
        }
        for h in Household::ALL {
            for (label, value) in panel_rows(&[result.clone()], 0, &Pick::Body(Party::Household(h)))? {
                all.push(label);
                all.push(value);
            }
        }
    }
    Ok(all)
}

#[test]
fn no_word_names_a_taker_an_enemy() -> TestResult {
    let rows = rows_about_takers()?;
    assert!(!rows.is_empty());
    for row in &rows {
        let lower = row.to_lowercase();
        for word in lower.split(|c: char| !c.is_alphanumeric()) {
            assert!(!REFUSED_WORDS.contains(&word), "{row:?} holds the word {word:?}");
        }
    }
    Ok(())
}
```

- [ ] **Step 2: See them fail.** `mise run rust:test:q -- -p babylon-client -E 'test(small_world)'`. Expected:
  does not compile: no `struck_rows`, `above_of`, `placed_of`, `REFUSED_WORDS`; then
  `takers_are_drawn_at_the_struck_workplace` fails in the people view (the taker's last person stands with its
  household's persons not at work), and `a_taker_already_on_the_rolls_is_one_range` fails (no persons above the
  rolls in the range).
- [ ] **Step 3: Implement** `above_of`, `placed_of` (all seven arms), `struck_rows` as its doc says, the
  household's rows in `panel_rows`, and `above_at` with `person_ranges` as "What is drawn" says (`rest_of` then
  starts after the last range). A household's pool and member are found through `result.members`
  (`member.member_id()`, `member.household_id()`, `pool_id`, `site_id`); a pool of no workplace is
  `FrameError::Edge`.
- [ ] **Step 4: See them pass.** `mise run rust:test:q -- -p babylon-client -E 'test(small_world)'`. Expected:
  all pass; `a_world_with_no_fight_draws_as_before` and `without_a_stoppage_every_frame_is_as_before` unchanged.
- [ ] **Step 5: Run the companion's gate. Commit** `feat(client): struck work and who takes it` (body:
  `Part of PER-371`).

**What this task must not do:** use any word of `REFUSED_WORDS` (or another that makes an enemy of a household
that took struck work: the rows say who took whose place and what it had, nothing else); count a taker's persons
from money; read `PeriodFight.offered` (Task 8 adds it); give a member two ranges at one workplace; change a frame
of a period with no above-the-rolls receipt (the two pinned frame tests).

---

### Task 6: The measures and the news

Commit `feat(circuit-worlds): the four measures and the news, read from receipts`.

**Files:**
- Create: `W/fight/measures.rs`; `W/fight/news.rs`.
- Modify: `W/fight.rs` (`pub mod measures; pub mod news;` and their `pub use`); `W/fight/period.rs`
  (`FightBook` gains `measures: Vec<MeasureRow>`; `PeriodFight` gains `measures`, `news`; `close` computes them);
  `tests/fight.rs`.

**Interfaces:**

Consumes: `PeriodResult` and its receipts (`members`, `receipts.member_labor_use`, `receipts.taxes`,
`receipts.household_consumption`, `receipts.household_services`, `receipts.distributions`, `receipts.orders`,
`summary.prices`, `asked`); `RateReceipt` (Task 3, in `receipts.orders`); `ClosedView`, `FightBook`, `PeriodFight`
(Task 2).

Produces:

```rust
// W/fight/measures.rs   (all derive Clone, Copy where every field is, Debug, PartialEq, Eq)
pub enum Measure { PayShort { pay: Currency, needs: Currency }, PayCut { from: Currency, to: Currency },
    HandsShort { asked_hours: u64, filled_hours: u64 },
    TakeGrows { take: Currency, before: Currency, laid_off: u64, cut: Currency } }
pub enum Begins { Now, Continues }
pub struct MeasureRow { pub period: u64, pub workplace: Workplace, pub household: Option<Household>,
    pub measure: Measure, pub begins: Begins }
pub struct WorkplaceTake { pub to_owners: Currency, pub to_people: Currency }
/// The rows that hold at this close, by workplace in `Workplace::ALL` order, then measure (a, b, c, d), then
/// household in `Household::ALL` order. `before` is the period before (the take's growth, d); `last` the rows of
/// the last close (`Begins`).
pub fn measures(result: &PeriodResult, before: Option<&PeriodResult>, last: &[MeasureRow])
    -> Result<Vec<MeasureRow>, FightError>;
pub fn take_of(result: &PeriodResult, workplace: Workplace) -> Result<WorkplaceTake, FightError>;
pub fn needs_cost(result: &PeriodResult, household: Household) -> Result<Currency, FightError>;
// W/fight/news.rs   (Task 8 adds NewsItem's other seven variants)
pub enum Cause { Measure, Weighing(Household), Employer(Household), Order(OrderKind), Founding, Contract }
pub enum NewsItem { MeasureBegins(MeasureRow) }
pub struct News { pub period: u64, pub item: NewsItem, pub cause: Cause }
// PeriodFight gains, before `organizations`:
pub measures: Vec<MeasureRow>, pub news: Vec<News>,
```

What each measure reads (no figure divides money by hours, ADR317 R1):

| Measure | For | Holds when | Its figures, from receipts |
| --- | --- | --- | --- |
| (a) `PayShort` | each household with `opening_employed > 0` in a member receipt of the workplace's pool | `pay < needs` | one person's figures, at full work: `pay = net(rate * hours_per_person)`, `needs = needs_cost(result, h) / persons` (below) |
| (b) `PayCut` | the same households | a `RateReceipt` of this period at the site has `new_rate < old_rate` (that period only) | `from` = `old_rate`, `to` = `new_rate` |
| (c) `HandsShort` | the workplace (`household: None`) | `filled_hours < asked_hours` | `asked_hours` = `result.asked[w.index()]`; `filled_hours` = the sum of `next_opening_hours` of the pool's member receipts |
| (d) `TakeGrows` | the workplace | `take > before` and (`laid_off > 0` or `cut > 0`) | `take`, `before`: `take_of(..).to_owners` of this period and of `before` (no `before`: never holds); `laid_off`: the sum of `separations` of the pool's member receipts; `cut`: the sum of `old_rate - new_rate` over lowering `RateReceipt`s at the site |

**Measure (a) is one person's, at full work** (PF14 a: "a period's pay against the cost of their own needs";
PF5 2: "at full work"; the sketch's $80 against $91). A household's layoffs are not in it: they are measure (d),
whose remedy is work for the people let go (PF12), not a rate. Its records, all in the `PeriodResult`:
- `rate`: `compensation.wage_rate()` of the household's member row at the workplace's site in
  `receipts.member_labor_use` (every member has a row, pair members too; it carries the rate the period was paid
  at, after a `RateOrder`). A row that is not `Wage` gives no row of (a).
- `hours_per_person`: the member receipt's (`StaffingMemberReceipt.hours_per_person`).
- the tax to come: `net(x) = x - sum of floor(x * rate_bps / 10_000)` over the household's `TaxBasis::WageIncome`
  rows of `receipts.taxes` (the close writes a receipt for every tax policy every period, base 0 or not,
  `E/financial/close.rs:291-311`; none in the plain world). Before dues (PF14).
- `persons`: the household's cohort `persons` in `closing.households`. Each need is one unit a person
  (`HouseholdNeedBasis::Persons`, `units_per_basis: 1`, `W/doubled/catalog.rs:143-158`; the required quantity is
  the cohort's persons, `E/recurring/model.rs:77-90`), so the division is exact in the small worlds; it is rounded
  down to the micro-unit, which keeps it exact wherever the needs are so sized.
The figures are the same for every household of a workplace with the same basket; what differs between
households is in their own accounts (Task 8's `StopAccounts`). Measure (b) holds in the period of a lowering
`RateReceipt` only: nothing lowers a rate in Part One, and P2-9 measures it again. Measure (c)'s hours filled are
the `next_opening_hours` of the pool's member receipts.

`take_of`: `to_owners` is the sum of `paid` of the `DistributionReceipt`s whose `issuer_site_id` is the
workplace's site; `to_people` the sum of `accrued_wages` of its `member_labor_use` rows. `needs_cost`: for each of
its consumption receipts (food) and service receipts (power, care), `required_quantity` times the posted price at
the close in `summary.prices` of its place's seller (food: the shop; power: the utility; care: the clinic); a
missing price is `FightError::NoReceipt`. A member whose household is no household of the world is
`FightError::NoReceipt` naming the member. `Begins::Now` unless `last` has a row of the same workplace, household
and kind of measure.

- [ ] **Step 1: Write the failing tests** in `tests/fight.rs`. `down_fund_p2(fight: Fight)` is `World { rules:
  World::switches_at(Scale::Small).to_vec(), fight, ..World::scene() }` with the harvest struck in `Places::Both`
  until lifted before step 1. Rows of a run without a fight are made by folding `measures` over its history:
  `last = measures(&h[i], i.checked_sub(1).map(|j| &h[j]), &last)?`.
  - `in_the_quiet_world_no_measure_holds`: 34 steps of `World::scene()`: every period's folded rows are empty
    (a person's pay after tax $80 equals a person's needs $80, hands asked equal hands filled). 34 steps of
    `World::scene_with_fight()`: every `fight.measures` and `fight.news` is empty.
  - `the_later_slump_s_pay_short_begins_as_recorded`: 30 steps of `down_fund_p2(Fight::Absent)` (the run of the
    design's "Today", `fund-P2` of the closest form), rows folded. At period 30 the row of `SHOP_A` for
    `Household::Workers(SHOP_A)` is `Measure::PayShort { pay, needs }` with `pay` equal to the test's own reading of
    that period's records (the rate of its member row at the shop times that member receipt's `hours_per_person`,
    less each of its wage tax rows' `rate_bps`) and `needs` equal to the test's own sum (each `required_quantity`
    times the price in `summary.prices`) divided by its cohort's persons, and `pay < needs`. The first period
    whose rows hold it has `Begins::Now`; each following period that holds it has `Begins::Continues`. Print both
    figures and that first period with `eprintln!` for the record; type in no figure of the design's sketch.
  - `a_household_with_people_laid_off_is_not_pay_short_at_calm_prices`: 60 steps each of the closest form's
    `fund-P1` (`World { rules: World::switches_at(Scale::Small).to_vec(), pushed: Some(Pushed { push:
    OpeningPush::LessDemand, places: Places::Both }), ..World::scene() }`) and of `down_fund_p2(Fight::Absent)`,
    rows folded. The test finds every (period, workplace, household) with people there (`opening_employed > 0`)
    and fewer of its persons on the rolls than its cohort holds (the sum of its members' `opening_employed` below
    its `persons`) whose own household totals fall short (its `accrued_wages` less its wage taxes' `assessed`
    below its `needs_cost`) while one person's pay at full work covers one person's needs. At least one is found
    (else fail with "no household with people laid off at calm prices in fund-P1 or fund-P2 to 60: report to the
    lead"), and for each the period's rows hold no `PayShort` of that household at that workplace. Print how many.
  - `needs_cost_is_required_quantities_at_posted_prices`: period 1 of `World::scene()`: after asserting that
    `summary.prices` holds food $38 at each shop, power $12 at each utility and care $30 at each clinic, the needs
    are $320 for the shop's and the farm's and the clinic's workers of each place, $960 for the utility's, $640 for
    the owners and for the supported. At period 30 of `down_fund_p2(Fight::Absent)`, every household's
    `needs_cost` equals the test's own sum.
  - `take_of_is_profit_and_wages_of_the_period`: period 2 of `World::scene()`: each workplace's `to_people` is its
    persons times 10 hours times $10 ($400 for `SHOP_A`, $1,200 for `UTILITY_A`), and `to_owners` the sum of the
    `paid` of its distribution receipts, summed in the test.
  - `a_measure_that_begins_is_news_once`: 60 steps of `down_fund_p2(Fight::Asked(none()))` (`none()` as in
    Task 2). Some period has a row. In every period, each row with `Begins::Now` has exactly one `News { period,
    item: NewsItem::MeasureBegins(row), cause: Cause::Measure }`, and the news holds no other `MeasureBegins`.
  - `a_measure_starts_nothing`: the same run: every `fight.orders` is empty and every `fight.payments` is empty
    while measures hold (nothing weighs yet).
- [ ] **Step 2: Run them and see them fail:** `mise run rust:test:q -- -p babylon-circuit-worlds -E 'test(measure)
  | test(needs_cost) | test(take_of) | test(pay_short) | test(laid_off)'`. Expected: does not compile (no
  `fight::measures`).
- [ ] **Step 3: Implement** `measures.rs` and `news.rs` as the table says.
- [ ] **Step 4: Wire them into `close`** in `period.rs`: `let measures = measures::measures(closed.result,
  closed.history.last(), &book.measures)?;` one `News` with `Cause::Measure` for each row that begins now, in the
  rows' order; `book.measures = measures.clone()`; both into `PeriodFight`.
- [ ] **Step 5: Run them and see them pass:** the command of Step 2, then `mise run rust:test:q -- -p
  babylon-circuit-worlds`.
- [ ] **Run the gate:** the small worlds' gate.
- [ ] **Commit** the subject above. The body says: the four measures of PF14 for the people of each workplace, from
  receipts only, with no figure divided by hours; a measure that begins is news; a measure starts nothing; the
  figures of the later slump are read from the run's receipts. Ends with `Part of PER-371` and the
  `Co-Authored-By` line.

**What this task must not do:**
- Issue an order, or let any measure feed `decide` (Task 8 does).
- Read the owners' accounts into a household's row, or any figure from the design's sketch into a test.
- Divide money by hours anywhere.

---

### Task 7: The households' weighings; the ask that needs no call; the two tests of Amendment AM

Commit `feat(circuit-worlds): each household weighs its own accounts (PF5, PF6)`.

**Files:**
- Create: `W/fight/weigh.rs`; `W/fight/ask.rs`; `W/fight/counts.rs`; `W/fight/am.rs`;
  `rust/crates/babylon-circuit-worlds/tests/fight_am.rs`.
- Modify: `W/fight.rs` (`pub mod am; pub mod ask; pub mod counts; pub mod weigh;` and their `pub use`);
  `W/fight/world.rs` (`YEAR_PERIODS`); `tests/fight.rs`.

**Interfaces:**

Consumes: `Measure` (Task 6), `FightError`, `OrganizationId` (Task 2). Pure functions: nothing of the runner.

Produces (every type derives Clone, Debug, PartialEq, Eq; the fieldless enums also Copy):

```rust
// W/fight/world.rs
/// Designed: one year of the weighings, ADR314 A16 and the homes design's call 13 (= kernel TICKS_PER_YEAR).
pub const YEAR_PERIODS: u64 = 13;
// W/fight/ask.rs
pub enum Asker { Household(Household), Organization(OrganizationId) }
pub enum Term { PayFollowsPrices, TakenBackFirst, DuesCollected, WorkForSeekers }   // Part Two
pub struct Ask { pub workplace: Workplace, pub asker: Asker, pub rate_now: Currency, pub rate_asked: Currency,
    pub steps: u32, pub terms: Vec<Term>, pub named: Vec<(Household, u64)> }
/// The fewest steps that make a period's pay after tax cover `needs` (PF5 1, measure a).
pub fn fewest_steps(pay_after_tax: Currency, needs: Currency, hours: u64, wage_tax_bps: u32, step: Currency)
    -> Result<u32, FightError>;
// W/fight/counts.rs
pub struct HouseholdCount { pub household: Household, pub workplace: Workplace, pub costs: Vec<(u64, Currency)> }
impl HouseholdCount { pub fn within_year(&self, period: u64) -> Result<Currency, FightError>; }
// W/fight/weigh.rs
pub enum Ground { Called, OwnMeasure(Measure), Nothing }
pub enum Condition { Holds, Fails }
pub struct StopAccounts { pub ground: Ground, pub pay_here: Currency, pub pay_elsewhere: Currency,
    pub money: Currency, pub funds_pay: Currency, pub needs: Currency, pub cost_within_year: Currency,
    pub asked_year: Currency }
pub enum StopChoice { Stop, Work }
pub struct StopDecision { pub choice: StopChoice, pub something: Condition, pub can_go_without: Condition,
    pub worth_it: Condition, pub cost_this_period: Currency, pub weighed: StopAccounts }
pub fn weigh_stop(accounts: &StopAccounts) -> Result<StopDecision, FightError>;
pub enum OwnPeople { StoppedHere, NotStoppedHere }
pub struct SeekerAccounts { pub persons: u64, pub struck_pay: Currency, pub money: Currency,
    pub benefit: Currency, pub relief: Currency, pub other_pay: Currency, pub needs: Currency,
    pub own_people: OwnPeople }
pub enum TakeChoice { Take, Refuse }
pub struct TakeDecision { pub choice: TakeChoice, pub goes_without: Condition, pub more_to_live_on: Condition,
    pub without: Currency, pub with: Currency, pub weighed: SeekerAccounts }
pub fn weigh_struck_work(accounts: &SeekerAccounts) -> Result<TakeDecision, FightError>;
// W/fight/am.rs
pub enum Response { Differs, Same }
/// Amendment AM: the population's choices differ when, and only when, their own amounts differ.
pub fn responds_to_own_amounts<A, D: PartialEq>(population: &[A], weigh: impl Fn(&A) -> D) -> Response;
```

The weighings, in the order the code reckons them (checked arithmetic; an overflow is `FightError::Arithmetic`):

```text
weigh_stop (PF5):
  something        Holds unless ground is Nothing
  can_go_without   Holds if money > 0, or funds_pay > 0, or pay_here + pay_elsewhere < needs (call 7)
  cost_this_period = max(0, pay_here - funds_pay)                       (never below nothing: the lead's call 5)
  worth_it         Holds if cost_within_year + cost_this_period < asked_year
  choice           Stop if all three hold, else Work; `weighed` is a copy of the accounts
weigh_struck_work (PF6):
  without          = money + benefit + relief + other_pay               (counts in full: the lead's call 6)
  with             = money + relief + other_pay + struck_pay            (a taker does not keep the benefit, PF13)
  goes_without     Holds if without < needs
  more_to_live_on  Holds if with > without
  choice           Take if own_people is NotStoppedHere and both hold, else Refuse
fewest_steps:
  0 when pay_after_tax >= needs; else net_step = step * hours - floor(step * hours * wage_tax_bps / 10_000),
  and the smallest n with pay_after_tax + n * net_step >= needs; hours 0 with pay short is Arithmetic
  (no number of steps covers it; the caller asks nothing where it has no hours)
HouseholdCount::within_year(period): the sum of costs (p, c) with p <= period and p + YEAR_PERIODS > period,
  that is the periods period - 12 to period
responds_to_own_amounts: Same for an empty population or when every member's weigh equals the first's
```

How each amount is formed from a household's own accounts is Task 8's (`stop_accounts`, `seeker_accounts`). The
household's amounts are in its own dollars net of the tax to come: what it lives on; the employer's are gross,
what it pays. A taker does not count its benefit in what it would have with the struck work (PF13: the benefit is
kept only while refusing); the engine still pays it in that first period (Review Focus 3, pinned as it is). The
measure that may be a household's ground (`Ground::OwnMeasure`) carries one person's figures (Task 6); the
accounts beside it are the household's.

**Amendment AM, for each weighing of Part One** (the design's table, "How we know it works"):

| Weighing | The member | The amounts it compares | The population | What differs between members |
| --- | --- | --- | --- | --- |
| PF5, `weigh_stop` | a household with people at a workplace | its pay there and elsewhere, its money, what funds pay it, the cost of its needs, what stoppages there have cost it within the year, a year of what is asked on its hours | the households with people at that workplace | money held, pay of its other people, people at other workplaces, strike pay |
| PF6, `weigh_struck_work` | a household with people who look for work | what it has to live on without the work (money, benefit, relief, other pay), the cost of its needs, the pay of the struck work | the households of the place with people looking | the benefit and how long it has left, pay of its other people, money, relief |

PF6's "same demand", PF8 and PF18 are Part Two's (P2-5, P2-2, P2-3), each with its row and the same two tests.

**How a reviewer checks that no constant decides where a response turns:** in `weigh.rs` every `<`, `>` or
`max` compares two amounts of the one accounts value, or an amount with 0 (none at all); there is no literal
amount and no import of a constant (`rg -n 'dollars|_000|YEAR_PERIODS|PAY_STEP' W/fight/weigh.rs` finds
nothing). Because every comparison is between the household's own amounts, a household whose every amount is
multiplied by the same factor decides the same: Step 1's scaled population. A weighing with a planted cut-off
fails that population: Step 1's planted test.

- [ ] **Step 1: Write the failing tests.** In `tests/fight.rs` (each calls the pure function with amounts; every
  amount is the household's own; `step` is $1):
  - `nothing_to_stop_for_works` (PF5 1): `ground: Nothing`, pay_here $320, needs $364, money 0, funds 0, costs 0,
    asked_year $832: `Work`, `something: Fails`, the other two `Holds`.
  - `cannot_go_without_works` (PF5 2): `OwnMeasure(PayCut { from: $11, to: $10 })`, pay_here $320, needs $300,
    money 0, funds 0, asked_year $416: `Work`, `can_go_without: Fails`.
  - `not_worth_it_works` (PF5 3): as the last with money $40, cost_within_year $96 and asked_year $416:
    $96 + $320 = $416 is not less than $416: `Work`, `worth_it: Fails`. With cost_within_year $95: `Stop`.
  - `going_without_at_full_work_may_stop_with_no_money` (call 7): `OwnMeasure(PayShort { pay: $80, needs: $91 })`
    (one person's), pay_here $320, pay_elsewhere 0, needs $364, money 0, funds 0, costs 0, asked_year $832:
    `Stop`, all three
    `Holds`, `cost_this_period == $320`.
  - `a_household_goes_back_when_the_fight_has_cost_a_year_of_the_ask` (check 2's case 3.1, one step on four
    people, no tax, no fund): pay_here $400, needs $420, money 0, asked_year $520 (a step on 40 hours, 13
    periods). With cost_within_year 0: `Stop` ($0 + $400 < $520). With `HouseholdCount { costs: vec![(2,
    $400)] }.within_year(3)? == $400` as cost_within_year: `Work` ($800), `worth_it: Fails`.
  - `a_struck_period_costs_never_below_nothing` (the lead's call 5): pay_here $400, funds_pay $500:
    `cost_this_period == 0`.
  - `a_household_s_count_forgets_after_a_year`: costs `[(2, $400), (10, $100)]`: `within_year(14) == $500`,
    `within_year(15) == $100`, `within_year(23) == 0`.
  - `a_seeker_takes_struck_work_only_when_it_goes_without` (PF6): persons 2, struck_pay $160, money 0, relief 0,
    other_pay 0, needs $182, `NotStoppedHere`: benefit 0: `Take` (without 0 < 182; with 160 > 0); benefit $100:
    `Take` (100 < 182; 160 > 100); benefit $200: `Refuse`, `goes_without: Fails`; benefit $170 and struck_pay
    $160: `Refuse`, `more_to_live_on: Fails` (it would have less).
  - `a_seeker_never_takes_work_its_own_people_stopped`: the first case with `StoppedHere`: `Refuse`, both
    conditions `Holds`.
  - `fewest_steps_buys_the_needs_again` ($10 to $12 in the sketch's figures, fund world 2,000 bps):
    `fewest_steps($320, $364, 40, 2_000, $1) == 2` ($32 a step, $44 short); per person `($80, $91, 10, 2_000, $1)
    == 2`; `($320, $352, 40, ..) == 1`; `($320, $353, 40, ..) == 2`; `($320, $320, 40, ..) == 0`; the national
    step `($320, $364, 40, 2_000, $0.25) == 6` ($8 a step); `($0, $364, 0, 2_000, $1)` is `Err(Arithmetic)`.
  - In `tests/fight_am.rs`, the two tests of Amendment AM, as code:

    ```rust
    fn household(money: Currency) -> StopAccounts {
        StopAccounts { ground: Ground::OwnMeasure(Measure::PayCut { from: dollars(11), to: dollars(10) }),
            pay_here: dollars(320), pay_elsewhere: dollars(0), money, funds_pay: dollars(0),
            needs: dollars(300), cost_within_year: dollars(0), asked_year: dollars(416) }
    }
    fn choice(a: &StopAccounts) -> Result<StopChoice, FightError> { weigh::weigh_stop(a).map(|d| d.choice) }
    /// Every amount of one household times `k`.
    fn scaled(a: &StopAccounts, k: i128) -> StopAccounts { /* each Currency field and the measure's, times k */ }

    #[test]
    fn three_households_of_unlike_money_respond_differently() {
        // Three households at one workplace; only their money differs. $0 cannot go without; $40 and $900 can.
        let unlike = [household(dollars(0)), household(dollars(40)), household(dollars(900))];
        assert_eq!(am::responds_to_own_amounts(&unlike, choice), Response::Differs);
        // The difference removed: the same three with the same money respond the same.
        let alike = [household(dollars(40)), household(dollars(40)), household(dollars(40))];
        assert_eq!(am::responds_to_own_amounts(&alike, choice), Response::Same);
    }

    #[test]
    fn a_planted_cut_off_fails_the_am_test() {
        // One household's accounts at three scales: its own amounts keep their proportions, so its own
        // weighing does not move.
        let base = household(dollars(40));
        let scales = [scaled(&base, 1), scaled(&base, 10), scaled(&base, 100)];
        assert_eq!(am::responds_to_own_amounts(&scales, choice), Response::Same);
        // A fixed amount put in on purpose: "a household with more than $100 never stops".
        let planted = |a: &StopAccounts| choice(a).map(|c| if a.money > dollars(100) { StopChoice::Work } else { c });
        assert_eq!(am::responds_to_own_amounts(&scales, planted), Response::Differs);
    }
    ```

    The same two tests for PF6 (`seeker_households_of_unlike_benefit_respond_differently` with the benefits 0,
    $100, $200 of the PF6 case above, then all $100; `a_planted_cut_off_fails_the_am_test_of_struck_work` with the
    first case scaled 1, 10, 100 and the plant `if a.needs > dollars(500) { TakeChoice::Refuse }`).
- [ ] **Step 2: Run them and see them fail:** `mise run rust:test:q -- -p babylon-circuit-worlds -E 'test(works) |
  test(stop) | test(seeker) | test(fewest) | test(count) | test(am) | test(nothing) | test(respond)'`. Expected:
  does not compile (no `fight::weigh`, no `fight::am`).
- [ ] **Step 3: Implement** `ask.rs`, `counts.rs`, `weigh.rs` and `am.rs` as the text block says, and
  `YEAR_PERIODS` in `world.rs`, each value with its doc line (Designed, with its source).
- [ ] **Step 4: Run them and see them pass:** the command of Step 2, then `mise run rust:test:q -- -p
  babylon-circuit-worlds`.
- [ ] **Run the gate:** the small worlds' gate.
- [ ] **Commit** the subject above. The body says: PF5 and PF6 as rules of one household's own amounts, each
  decision carrying what was weighed; the ask with no call is the fewest steps that buy the needs again; the
  household's count over the last year; Amendment AM's two tests, the difference removed and a planted cut-off.
  Ends with `Part of PER-371` and the `Co-Authored-By` line.

**What this task must not do:**
- Put any constant amount, share or threshold in a weighing; read `YEAR_PERIODS` or a pay step in `weigh.rs`.
- Read another household's accounts or decision: a weighing takes one accounts value.
- Call these functions from `decide` (Task 8 does).

---

### Task 8: The employer's rule, the offer, both counts, the order inside a period

Commit `feat(circuit-worlds): the employer's rule and the order inside a period`.

**Files:**
- Create: `W/fight/employer.rs`; `W/fight/stoppage.rs`; `W/fight/period_tests.rs` (declared in `period.rs` as
  `#[cfg(test)] #[path = "period_tests.rs"] mod tests;`, so it reads the book's private fields and no folder is
  made beside `period.rs`).
- Modify: `W/fight.rs` (`pub mod employer; pub mod stoppage;` and their `pub use`); `W/fight/counts.rs`
  (`EmployerCount`, `baseline`, `own_takes`, `loss_shares`); `W/fight/news.rs` (seven variants);
  `W/fight/period.rs` (`FightBook`, `Decided.decisions`, `PeriodFight`'s fields, `decide`, `close`);
  `tests/fight.rs` (and Task 6's `a_measure_starts_nothing`, rewritten in Step 2). `W/runner/run.rs` is not
  changed: Task 2 composed `advance`.

**Interfaces:**

Consumes: engine Tasks 1 and 3 to 5: `PeriodOrders`, `RateOrder`, `WithheldOrder`, `AboveRollsOrder`,
`AboveRollsCause::StruckWork`, `StaffingOrder`, `StaffingOrderKind::PlaceTaken`, `OrderKind`, and in
`receipts.orders`: `OrderReceipt::{Rate, Withheld, AboveRolls, Staffing}` with `RateReceipt`, `WithheldReceipt`,
`AboveRollsReceipt` (`attended_hours`: the hours attended above the member's rolls' hours), and
`StaffingOrderReceipt { period, order, household_id, moved: u64, displaced: Vec<(StaffingMemberId, u64)> }`
(Task 5 applies an order to what the close leaves: `moved = min(persons, the from slot's reserve now, the room
under the stop rule's limit)`, and a `PlaceTaken` displaces `min(moved, the striking slots' employed now)`; it
refuses only an order that passes what the orderer saw at the opening). Task 2: `DecideView`, `ClosedView`,
`Decided`, `FightBook`, `PeriodFight`, `Employers`, `pay_step`. Task 6: `measures`, `MeasureRow`, `needs_cost`, `News`,
`NewsItem`, `Cause`. Task 7: `weigh_stop`,
`weigh_struck_work`, the accounts, decisions and choices, `Ask`, `Asker`, `fewest_steps`, `HouseholdCount`,
`YEAR_PERIODS`.

Produces:

```rust
// W/fight/counts.rs
pub struct EmployerCount { pub employer: Household, pub workplace: Workplace, pub losses: Vec<(u64, Currency)> }
impl EmployerCount { pub fn within_year(&self, period: u64) -> Result<Currency, FightError>; } // as the household's
/// PF7: what all the employer's workplaces paid it a period (the `paid` of every distribution receipt whose
/// beneficiary is its account), the mean, rounded down, of the last YEAR_PERIODS periods of `history` with no
/// `WithheldReceipt` at `workplace`'s site (or of those there are); `None` when there are none.
pub fn baseline(history: &[PeriodResult], employer: Household, workplace: Workplace)
    -> Result<Option<Currency>, FightError>;
/// PF7 for one employer's struck workplaces of one period: over the last YEAR_PERIODS periods of `history` with no
/// `WithheldReceipt` at any of `struck` (or of those there are), the mean, rounded down, of what all its
/// workplaces paid it, and for each of `struck` the mean of what that workplace paid it (the `paid` of the
/// distribution receipts whose `issuer_site_id` is its site and whose beneficiary is the employer), in the order of
/// `struck`. `None` when there are no such periods. With one workplace struck, the first figure is `baseline`'s.
pub fn own_takes(history: &[PeriodResult], employer: Household, struck: &[Workplace])
    -> Result<Option<(Currency, Vec<(Workplace, Currency)>)>, FightError>;
/// One employer has one loss a period. Each `(workplace, own, asked_year)` of its workplaces struck this period
/// takes `floor(loss * own / sum of own)`; where the sum of `own` is 0, in proportion to `asked_year` the same
/// way; a workplace struck alone takes the whole loss (design call 3). In the order of `struck`.
pub fn loss_shares(loss: Currency, struck: &[(Workplace, Currency, Currency)])
    -> Result<Vec<(Workplace, Currency)>, FightError>;
// W/fight/employer.rs
pub enum EmployerDecision { GiveWay { cost: Currency, asked_year: Currency },
    OfferStruckWork { hours: u64, cost: Currency, asked_year: Currency }, NeverPaid }
/// NeverPaid when `baseline` (of all its workplaces) is None or not above 0; GiveWay when the count within the year is more than
/// `asked_year`; else OfferStruckWork of `withheld_hours`. `cost` is the count within the year.
pub fn employer_decides(count: &EmployerCount, period: u64, asked_year: Currency, baseline: Option<Currency>,
    withheld_hours: u64) -> Result<EmployerDecision, FightError>;
pub struct StruckOffer { pub workplace: Workplace, pub period: u64, pub hours: u64, pub rate: Currency }
// W/fight/stoppage.rs
pub enum StoppageEnd { GaveWay, WentBack, PlacesTaken }
/// `out`: PERSONS by household whose hours were withheld (`WithheldReceipt.withheld_hours` / hours a person).
/// `filled`: PERSONS by household who worked above the rolls (`AboveRollsReceipt.attended_hours`, the hours
/// attended above the member's rolls' hours, over hours a person, rounded up).
pub struct StoppagePeriod { pub period: u64, pub out: Vec<(Household, u64)>, pub filled: Vec<(Household, u64)>,
    pub paid: Vec<PaymentRecord> }
/// `ended`: the last period in which hours were withheld, and how it ended.
pub struct Stoppage { pub workplace: Workplace, pub began: u64, pub ask: Ask, pub periods: Vec<StoppagePeriod>,
    pub ended: Option<(u64, StoppageEnd)> }
// W/fight/news.rs, NewsItem gains (`Stopped.out` and `StruckWorkTaken.by`: PERSONS by household, as the
// stoppage's period records them; `PlacesTaken.persons`: persons)
Stopped { workplace: Workplace, out: Vec<(Household, u64)>, ask: Ask }, WentBack { workplace: Workplace,
household: Household }, StruckWorkOffered(StruckOffer), StruckWorkTaken { workplace: Workplace,
by: Vec<(Household, u64)> }, GaveWay { workplace: Workplace, rate: Currency }, PlacesTaken { workplace: Workplace,
persons: u64 }, RateChanged { workplace: Workplace, from: Currency, to: Currency },
// W/fight/period.rs
pub enum HouseholdDecision { Stop { household: Household, workplace: Workplace, decision: StopDecision },
    StruckWork { household: Household, workplace: Workplace, decision: TakeDecision } }
pub struct EmployerRecord { pub employer: Household, pub workplace: Workplace, pub decision: EmployerDecision }
pub struct PeriodFight { pub orders: PeriodOrders, pub orders_digest: [u8; 32],
    pub decisions: Vec<HouseholdDecision>, pub payments: Vec<PaymentRecord>,
    pub employers: Vec<EmployerRecord>, pub offered: Vec<StruckOffer>, pub stoppages: Vec<Stoppage>,
    pub measures: Vec<MeasureRow>, pub news: Vec<News>, pub organizations: Vec<(Organization, Currency)> }
pub struct FightBook { organizations: Vec<Organization>, rule: Employers, stoppages: Vec<Stoppage>,
    employers: Vec<EmployerCount>, households: Vec<HouseholdCount>, offers: Vec<StruckOffer>,
    given_way: Vec<(Workplace, Currency)>, measures: Vec<MeasureRow> }   // offers, given_way: of the last close
pub(crate) struct Decided { pub(crate) book: FightBook, pub(crate) orders: PeriodOrders,
    pub(crate) decisions: Vec<HouseholdDecision>, pub(crate) payments: Vec<PaymentRecord> }
```

**How a household's amounts are formed** (private helpers of `period.rs`, each reading `view`, the book and,
for PF6 only, the same household's own decisions of this step; amounts net of the tax to come, `net(x) = x -
floor(x * bps / 10_000)`, `bps` the sum of `rate_bps` of the state's `TaxPolicy` rows with payer
`Household(h)` and basis `WageIncome`, 0 in the plain world):

| Amount | Read from |
| --- | --- |
| rate at a workplace | the largest `Wage` rate of the state's `employment` rows at its site (own and pair rows) |
| persons on the rolls, persons looking | `view.members`: the household's members' `employed()` at that pool; `reserve()` over the pools of its place |
| `pay_here`, `pay_elsewhere` | `net(rate * persons on the rolls * world.hours_per_person())` at this workplace; the same summed over its other workplaces (all its pay at full work, as of the last close) |
| `money` | its cash in `last.closing.cash` |
| `funds_pay`, `relief` | 0 in Part One: no organization orders a payment yet |
| `needs` | `measures::needs_cost(last, h)` |
| `cost_within_year` | the book's `HouseholdCount` of (h, workplace) `.within_year(view.period)`, else 0 |
| `asked_year` | `net((ask.rate_asked - ask.rate_now) * its attended hours there in the period before the stoppage began, or in the last period for a new ask) * YEAR_PERIODS` |
| `benefit` | the `paid` of every `PublicProgramReceipt` to it in `last` (a worker household is a recipient of `laid_off` only, opening.rs:558-584) |
| `other_pay` (PF6) | `pay_elsewhere` over the workplaces where its own decision of this step is not `Stop`, plus the struck pay it took at earlier offers of this step |
| `persons`, `struck_pay` (PF6) | the sum of what each of its slots still holds: each slot's reserve at the opening (`view.members`) less what that slot gave at earlier offers of this step; `net(offer.rate * min(offer.hours, persons * hours a person))` |

The persons a household brings to an offer are taken from its slots after subtracting what each slot gave at
earlier offers of this step, so no slot gives more than its reserve at the opening, and no host has more places
taken than its striking slots' `employed()` at the opening: the two sums the engine's Task 5 checks.

**`own_ask`**, the ask with no call (PF5 1), for household `h` at workplace `w`, given its measure row of the
last close:

```rust
fn own_ask(view: &DecideView<'_>, book: &FightBook, w: Workplace, h: Household, row: Option<&MeasureRow>)
    -> Result<Option<Ask>, FightError> {
    let (Some(row), Some(last)) = (row, view.last) else { return Ok(None) };       // Ground::Nothing (PF5 1)
    if let Some(open) = book.open_stoppage(w) {                     // what is asked there, while its own
        return Ok(match row.measure {                               // measure (a) or (b) still holds
            Measure::PayShort { .. } | Measure::PayCut { .. } => Some(open.ask.clone()),
            Measure::HandsShort { .. } | Measure::TakeGrows { .. } => None,
        });
    }
    let rate_now = rate_of(view.state, w)?;
    let step = world::pay_step(view.world, w);
    let (rate_asked, steps) = match row.measure {
        Measure::PayShort { pay, needs } => {                     // one person's, at full work (Task 6)
            let hours = hours_per_person(last, h, w)?;             // its member receipt at w's pool
            let bps = wage_tax_bps(last, h)?;                      // its WageIncome tax receipts' rate_bps
            let steps = ask::fewest_steps(pay, needs, hours, bps, step)?;
            if steps == 0 { return Ok(None); }
            (rate_now + steps * step, steps)                       // checked
        }
        Measure::PayCut { from, .. } => (from, ceil((from - rate_now) / step)),   // the cut withdrawn
        Measure::HandsShort { .. } | Measure::TakeGrows { .. } => return Ok(None), // no ground (PF14)
    };
    Ok(Some(Ask { workplace: w, asker: Asker::Household(h), rate_now, rate_asked, steps,
        terms: Vec::new(), named: Vec::new() }))
}
```

`ground` is `Ground::OwnMeasure(row.measure)` when `own_ask` is `Some`, else `Ground::Nothing`. The ask is
reckoned on one person's figures, so it is the same for every household of a workplace with the same basket and
does not grow with a household's layoffs; what differs between households is in their `StopAccounts`. When several
households stop at a workplace with no stoppage open, the workplace's ask is the largest `rate_asked` of theirs,
the first in `Household::ALL` order on a tie (the plan's "Calls of the lead", 2).

**Decided here.** `pay_elsewhere` is the household's pay at full work at its other workplaces as of the last
close; PF6's `other_pay` leaves out the workplaces where its own decision of the step is `Stop`. An employer that
never gives way (`NeverPaid`) still offers struck work from the period after (PF7). When more come than there are
struck places, the places are shared over the takers' persons by largest remainders, `Household::ALL` order on
ties; a taker whose share is 0 gets no order, its `TakeDecision` stays `Take`, and `StruckWorkTaken.by` lists only
the takers with a share. A stoppage with no striker left on the rolls ends `PlacesTaken` if a place was taken in
it, else `WentBack`; `ended` names the last period with hours withheld. A place counts as taken at the close of
the period in which the struck work was taken up, whether or not the workplace could pay its hours. A household
whose own measure no longer holds has nothing to stop for and goes back (PF5 1), though a stoppage is open there.
The workplace's ask that a household weighs once a stoppage is open equals its own in the small worlds: the ask is
one person's figures, and every worker household of a world has the same hours a person and the same tax rows
(`W/doubled/opening.rs:522-533`); the bridge must say how a household weighs an ask formed from another's.

**One employer has one loss a period** (PF7, call 44): where several of its workplaces are struck in one period,
what that period cost it is shared among them by `counts::loss_shares`, in proportion to what each had been
paying it (`own_takes`); a workplace struck alone takes the whole loss whatever its own take (call 3: the people of
a utility can win though the utility earns little). `NeverPaid` stays "the baseline of all its workplaces is
`None` or not above 0".

**Employers that offer at once** (`Employers::OfferAtOnce`, the bench's instrument, no rule of the game): in
`decide` (b) a workplace where a household's own ask exists gets a `RateOrder` at the largest `rate_asked` of that
step, nobody stops there and no `Stop` decision is recorded; there is no count, no offer and no stoppage, and the
news at the close is `RateChanged` with `Cause::Measure`.

**The taker's member and its slots.** A taker household `h` works the struck hours through its member at the
struck workplace's pool: `w.member_id()` when `w` is its home, else `w.pair_member_id(home)` (`W/ids.rs:178-184`
gives exactly this). The slots it brings persons from are its members with persons looking in the place, in pool
then member order, and they may include that very member: the workplace's own laid off, of a household whose
people there did not stop, are the first of "the place's people who look for work" (PF7). Such a slot gives a
`StaffingOrder` with `from_pool == host_pool` and `from_member == to_member` (the persons are called back from
that member's own reserve); the engine's Task 5 accepts exactly this and refuses the same pool with two members.

**`decide`, the order of decisions** (steps 2 and 3 of the design's period; it reads only `view` and the book):

```rust
let mut book = book.clone();
let mut orders = PeriodOrders::none(view.period);
let mut decisions = Vec::new();
let Some(last) = view.last else { return Ok(Decided { book, orders, decisions, payments: Vec::new() }) };
// (c) what was offered at the last close: all that is asked, from this period's first hour (PF7, PF1)
for (w, rate) in mem::take(&mut book.given_way) {
    orders.rates.push(RateOrder { site_id: w.site_id(), unit_id: ids::hours_unit(), rate });
}
// (b) PF5, workplace by workplace, each household from its own accounts
for w in Workplace::ALL {
    if gave_way(&orders, w) { continue; }               // its people go back to the rate offered
    if book.rule == Employers::OfferAtOnce {            // the bench's instrument: the largest own ask, at once
        if let Some(rate) = largest_own_ask(view, &book, w)? { orders.rates.push(RateOrder { site_id:
            w.site_id(), unit_id: ids::hours_unit(), rate }); }
        continue;
    }
    let mut stopping = Vec::new();
    for h in households_on_rolls(view.members, w) {      // Household::ALL order, persons on w's rolls
        let row = book.measures.iter().find(|m| m.workplace == w && m.household == Some(h));
        let ask = own_ask(view, &book, w, h, row)?;
        let decision = weigh::weigh_stop(&stop_accounts(view, &book, w, h, ask.as_ref(), row)?)?;
        if decision.choice == StopChoice::Stop { stopping.push((h, ask)); }
        decisions.push(HouseholdDecision::Stop { household: h, workplace: w, decision });
    }
    book.begin_continue_or_end(w, view.period, &stopping)?; // none stops: ended (period - 1, WentBack)
    for (h, _) in &stopping {                               // the member of h at w's pool, with employed() > 0
        orders.withheld.push(WithheldOrder { member_id, share_bps: 10_000 });   // call 8: all or nothing
    }
}
// (a) PF6, the offers of the last close for stoppages still open, workplace by workplace
for offer in book.offers_for(view.period) {             // Workplace::ALL order
    let places = struck_persons(&orders, offer.workplace) .min(offer.hours / hours_per_person);
    let mut takers = Vec::new();
    for h in households_looking(view.members, offer.workplace.place) {   // Household::ALL order, Workers only
        let own = if stops_at(&decisions, h, offer.workplace) { OwnPeople::StoppedHere }
            else { OwnPeople::NotStoppedHere };
        let accounts = seeker_accounts(view, &book, &offer, h, own, &own_decisions(&decisions, h))?;
        let decision = weigh::weigh_struck_work(&accounts)?;
        if decision.choice == TakeChoice::Take { takers.push((h, accounts.persons)); }
        decisions.push(HouseholdDecision::StruckWork { household: h, workplace: offer.workplace, decision });
    }
    // all takers' persons when they fit in `places`, else largest remainders over their persons
    // (Household::ALL order on ties; the engine's `proportional_shares` is crate-private, so the same rule here)
    for (h, persons) in shares(places, &takers)?.into_iter().filter(|(_, persons)| *persons > 0) {
        // to = taker_member(w, home): w.member_id() if home == w, else w.pair_member_id(home)
        // AboveRollsOrder { member_id: to, hours: persons * hpp, cause: StruckWork }
        // StaffingOrder { host_pool: w.pool_id(), to_member: to, from_pool, from_member, persons: from that slot,
        //     kind: PlaceTaken }, one for each of h's slots with persons still looking (its reserve at the
        //     opening less what it gave at earlier offers of this step), in pool then member order, until
        //     `persons` are covered; a slot at w's own pool is `to` itself (from_pool == host_pool,
        //     from_member == to_member). PF13: a place counts as taken at this close.
    }
}
// every list sorted by its key (PeriodOrders is canonical); Ok(Decided { book, orders, decisions, payments })
```

**`close`, step 1 of the design's period** (after Task 6's measures, in this order):

1. `book.offers` and `book.given_way` are cleared (they were the last close's).
2. For each stoppage open in this period (begun or continued by `decide`): append its `StoppagePeriod` (`out` from
   this period's `WithheldReceipt`s at its site by `payee`, in persons; `filled` from its `AboveRollsReceipt`s by
   `payee`, in persons: `attended_hours` (above the rolls) over hours a person, rounded up; `paid` empty);
   push each out household's cost `(period, max(0, net(ask.rate_now * withheld_hours) - funds paid))` onto its
   `HouseholdCount` of (household, workplace). Then, from the `StaffingOrderReceipt`s at its host pool (their
   `moved` and `displaced`, never `order.persons`): a striker's persons left on the rolls are its member's
   `closing_employed` in `result.members` (the engine's decision before any move or order) less the persons the
   period's `StaffingOrderReceipt`s displaced from that member. When none is left, it ends `(period,
   PlacesTaken)` if any place was taken in it, else `(period, WentBack)`.
3. PF7, employer by employer. `employer` is the beneficiary of the workplace's ownership claim in
   `result.closing.ownership`. For each employer, its workplaces with a stoppage still open, in `Workplace::ALL`
   order, are `struck`; `own_takes(closed.history, employer, &struck)?` gives `baseline` and each `own(w)`; the
   period's one loss is `max(0, baseline - what all its workplaces paid it in this period)` (0 when `None`);
   for each `w`, `asked_year = (ask.rate_asked - ask.rate_now) * summary.hours_attended[w]` of the period before
   `began` `* YEAR_PERIODS`; `loss_shares(loss, &[(w, own(w), asked_year)..])?` gives each `w` its share, pushed
   onto its `EmployerCount` of (employer, w); then for each `w`, `employer_decides(&count, period, asked_year,
   baseline, withheld_hours)`. `GiveWay`: the stoppage ends `(period, GaveWay)`, `book.given_way` gets `(w,
   ask.rate_asked)`, and every `EmployerCount` and `HouseholdCount` of w is dropped (both counts start again when
   what is asked is won). Otherwise (`OfferStruckWork` or `NeverPaid`): `book.offers` gets `StruckOffer {
   workplace: w, period: period + 1, hours: withheld_hours, rate: ask.rate_now }`. Counts lost by a walkout that
   failed stay. Entries older than a year (`p + YEAR_PERIODS <= period`) are pruned.
4. News, in this order, each with its cause: `MeasureBegins` (`Measure`); `Stopped` for a stoppage begun this period
   (`Weighing(asker)`); `WentBack` for each household whose `Stop` decision this period chose `Work` at a workplace
   where it was out at the last close (`Weighing(h)`); `RateChanged` for each `RateReceipt` of this period
   (`Order(OrderKind::Rate)`; `Cause::Measure` under `Employers::OfferAtOnce`); `StruckWorkTaken`
   (`Order(OrderKind::AboveRolls)`, `by` the takers' `filled` persons); `PlacesTaken` (`Order(OrderKind::Staffing)`,
   `persons` the sum of the receipts' `moved`); `GaveWay` and `StruckWorkOffered` (`Employer(employer)`).
5. `PeriodFight`: `decisions` and `orders` from `Decided`; `employers` and `offered` of this close; `stoppages`:
   every stoppage open at the start of this period's decisions or begun in them, as it stands now.

- [ ] **Step 1: Build the test world** in `period_tests.rs`. It is the quiet fight world's own records with
  figures put on them, so that its arithmetic can be worked by hand:

  ```rust
  /// The first 30 periods of `World::scene_with_fight()`, quiet, with the runner's state and members after them.
  fn quiet_30() -> Result<(World, MaterialCircuitState, Vec<PoolMembers>, Vec<PeriodResult>), Box<dyn Error>>;
  /// Set what each Place A workplace pays Owner(A) in this period (the `paid` of its distribution receipt to the
  /// owners; push one if it has none).
  fn pay_owners(result: &mut PeriodResult, paid: [i128; 4]);          // dollars: utility, farm, clinic, shop
  /// Set a posted price at the close in `summary.prices`.
  fn post(result: &mut PeriodResult, seller: Workplace, good: Good, dollars: i128);
  /// The period struck at these workplaces: its number, a `WithheldReceipt` for each one's own member with
  /// `rolls_hours == withheld_hours ==` its quiet hours (utility 120, others 40), their attended hours 0, and the
  /// struck workplaces' distribution receipts to their owners paid $0.
  fn struck(result: &PeriodResult, period: u64, at: &[Workplace]) -> PeriodResult;
  ```

  The arithmetic, period by period (put this comment above the fixture):

  ```text
  Periods 1 to 30: Place A's workplaces pay Owner(A) utility $350, farm $0, clinic $0, shop $1,050: $1,400 a
    period, so PF7's baseline (the mean of the 13 periods 18 to 30) is $1,400, and the own takes are $350, $0,
    $0 and $1,050.
  Period 30: at the close, food $53 at shop A and care $26 at clinic A (power stays $12): a person's needs are
    $91. Measure (a), one person's at full work: pay 10 h x $10 = $100, less 2,000 bps of wage tax, $80; needs
    $364 / 4 persons = $91. It holds ($80 < $91, short by $11 a person) at all four workplaces of Place A, for
    the same basket. fewest_steps(80, 91, 10, 2_000, $1): a step adds $10 less 20 %, $8; $11 short: 2 steps, $12
    asked, at each of the four. Place B: quiet, nothing holds.
    The households' own accounts: shop A's 4 people, pay_here 4 x $80 = $320, needs $364; the farm's and the
    clinic's the same; the utility's 12, pay_here $960, needs $1,092.
  Decide 31 (PF5): shop A: something holds (a); can go without holds ($320 < $364 at full work, call 7); worth
    it: $0 + $320 < 2 steps x $1 x 40 h less 20 % x 13 = $832. It stops. Farm A, clinic A: the same. Utility A:
    $0 + $960 < 2 x $1 x 120 h less 20 % x 13 = $2,496. It stops. Orders: WithheldOrder 10,000 bps on the four
    own members of Place A; no struck work yet (none was offered).
  Period 31 (made by `struck`): every Place A workplace withholds all its hours and pays Owner(A) $0.
  Close 31 (PF7, one employer, one loss): $1,400 - $0 = $1,400, shared by the own takes: utility $350, farm $0,
    clinic $0, shop $1,050. Shop A: a year of the ask, 2 x $1 x 40 h x 13 = $1,040; $1,050 > $1,040: gives way
    at $12. Farm A, clinic A: $0 against $1,040 each: struck work offered for 32, 40 hours at $10 each.
    Utility A: $350 against 2 x $1 x 120 h x 13 = $3,120: struck work offered for 32, 120 hours at $10.
    Household counts: the shop's dropped (won); the farm's and the clinic's (31, $320); the utility's (31, $960).
  Decide 32: a RateOrder of $12 at shop A; the others weigh again: farm A, clinic A $320 + $320 = $640 < $832,
    utility A $960 + $960 = $1,920 < $2,496: they stay out. Nobody in Place A looks for work (the quiet world's
    reserve is 0): nobody is offered a choice and nobody takes the struck work.
  ```

- [ ] **Step 2: Write the failing tests.** In `period_tests.rs`, each running `decide` then `close` on the made
  periods (`DecideView { world, period, state, members, last, history }`; `ClosedView { period, result, history,
  state }`; history holds the periods before):
  - `the_sketch_s_shop_wins_two_steps`: close 30's `measures` has `MeasureRow { period: 30, workplace: SHOP_A,
    household: Some(Workers(SHOP_A)), measure: PayShort { pay: $80, needs: $91 }, begins: Now }`, and the rows of
    the utility's, the farm's and the clinic's workers carry the same `PayShort { pay: $80, needs: $91 }`. Decide
    31: the shop's `Stop` decision has `choice: Stop`, the three conditions `Holds`, `cost_this_period: $320`,
    `weighed.pay_here: $320`, `weighed.needs: $364`, `weighed.asked_year: $832`; `orders.withheld` is the four
    Place A own members at 10,000 bps, in member order. Close 31: its stoppage at `SHOP_A` began 31 with `ask {
    rate_now: $10, rate_asked: $12, steps: 2, asker: Household(Workers(SHOP_A)) }` and `ended: Some((31,
    GaveWay))`; `employers`, in `Workplace::ALL` order: `UTILITY_A` `OfferStruckWork { hours: 120, cost: $350,
    asked_year: $3,120 }`, `FARM_A` and `CLINIC_A` `OfferStruckWork { hours: 40, cost: $0, asked_year: $1,040 }`,
    `SHOP_A` `GiveWay { cost: $1,050, asked_year: $1,040 }`; the news has `GaveWay { workplace: SHOP_A, rate:
    $12 }`. Decide 32: `orders.period == 32`, `orders.rates == [shop A $12]`, `orders.withheld` is the own members
    of utility A, farm A and clinic A, `orders.above_rolls` is empty.
  - `a_walkout_of_a_whole_place_shares_the_loss`: after close 31 the employer counts of Owner(A) are utility
    `[(31, $350)]`, farm `[(31, $0)]`, clinic `[(31, $0)]` and the shop's dropped after it gave way at `$1,050`:
    the one loss of $1,400, counted once. Pure: `loss_shares($1,400, &[(UTILITY_A, $350, $3,120), (FARM_A, $0,
    $1,040), (CLINIC_A, $0, $1,040), (SHOP_A, $1,050, $1,040)]) == [$350, $0, $0, $1,050]`; with every own take
    $0, `loss_shares($1,000, &[(FARM_A, $0, $1,040), (CLINIC_A, $0, $3,120)]) == [$250, $750]` (by `asked_year`).
  - `a_stoppage_at_one_workplace_counts_the_whole_loss`: the farm's, the clinic's and the shop's member rows of
    period 30 paid `Wage($12)` (one person's $96 covers $91: only the utility's people stop at 31); period 31 made
    by `struck(.., 31, &[UTILITY_A])` with Owner(A) paid $0 by all four workplaces. Close 31: the utility's
    employer count is `[(31, $1,400)]`, the whole loss though its own take is $350, and its record `OfferStruckWork
    { hours: 120, cost: $1,400, asked_year: $3,120 }`. Pure: `loss_shares($1,400, &[(UTILITY_A, $0, $3,120)]) ==
    [(UTILITY_A, $1,400)]`.
  - `struck_work_is_offered_from_the_period_after_a_stoppage_begins`: decide 31 has no `AboveRollsOrder` and no
    `StruckWork` decision; close 31's `offered` is `[StruckOffer { workplace: UTILITY_A, period: 32, hours: 120,
    rate: $10 }, FARM_A 40 hours, CLINIC_A 40 hours]` (period 32, $10) and nothing for the shop that gave way.
  - `an_offer_made_at_the_close_holds_from_the_next_period`: close 31 gives way at the shop; decide 32 carries the
    shop's `RateOrder`, no `WithheldOrder` on the shop's member and no `Stop` decision at `SHOP_A` (its people go
    back). The engine applies a rate from its period's first hour (Task 3's `a_rate_holds_from_the_first_hour`).
  - `both_counts_start_again_when_what_is_asked_is_won`: after close 31 the book has no `EmployerCount` and no
    `HouseholdCount` of `SHOP_A`; `FARM_A` and `CLINIC_A` have household `[(31, $320)]` and employer `[(31, $0)]`;
    `UTILITY_A` household `[(31, $960)]` and employer `[(31, $350)]`.
  - `a_failed_walkout_still_counts_for_a_year`: period 32 made by `struck(.., 32, &[UTILITY_A, FARM_A,
    CLINIC_A])` with Owner(A) paid by the shop $1,050 and by the rest $0. Close 32: one loss, $1,400 - $1,050 =
    $350, shared by the own takes ($350, $0, $0): the utility's employer count is `[(31, $350), (32, $350)]`
    ($700 < $3,120: offered again for 33). Decide 33: the three go back (utility $1,920 + $960 = $2,880, farm and
    clinic $640 + $320 = $960, none less than its year of the ask): the three stoppages `ended: Some((32,
    WentBack))`, no `WithheldOrder`, no struck work answered. The counts stay: the utility household's
    `within_year(43) == $1,920`, `(44) == $960`, `(45) == 0`.
  - `a_household_whose_measure_is_gone_goes_back`: decide 32 with period 31's posted prices back at food $38 and
    care $30 (one person's $80 covers $80: no measure at close 31). The utility's, the farm's and the clinic's
    households weigh `Ground::Nothing` and `Work`; their three stoppages end `(31, WentBack)`; no `WithheldOrder`;
    the offers of close 31 are not answered.
  - `a_stoppage_is_broken_by_takers`: as decide 32, with the members of the view changed so that the 12 people of
    the farm's, the clinic's and the shop's households of Place A are in reserve at their own members (employed 0,
    reserve 4: "laid off by the test"); the farm's and the clinic's stoppages, with nobody on their rolls, end
    `(31, WentBack)` and their offers are not answered. Each of the three weighs the utility's offer: persons 4,
    struck pay `net($10 x 40 h) = $320`, money its cash, benefit 0, other pay 0, needs $364: without < needs, with
    > without: `Take`. Orders: three `AboveRollsOrder { member_id: UTILITY_A.pair_member_id(home), hours: 40,
    cause: StruckWork }` and three `StaffingOrder { host_pool: UTILITY_A.pool_id(), to_member:
    UTILITY_A.pair_member_id(home), from_pool: home.pool_id(), from_member: home.member_id(), persons: 4, kind:
    PlaceTaken }`. Close 32 on a made period with the receipts the engine would give: three `AboveRollsReceipt`s
    (attended 40), three `StaffingOrderReceipt`s `{ moved: 4, displaced: [(UTILITY_A.member_id(), 4)] }`, and
    utility A's own member receipt as the engine decided before any order (`closing_employed: 12`): 12 - 12
    displaced leaves none, so the stoppage `ended: Some((32, PlacesTaken))`; the news has `StruckWorkTaken {
    workplace: UTILITY_A, by: [(farm, 4), (clinic, 4), (shop, 4)] }` and `PlacesTaken { workplace: UTILITY_A,
    persons: 12 }`. A variant where the shop's receipt has `moved: 3, displaced: [(UTILITY_A.member_id(), 3)]`:
    `PlacesTaken { persons: 11 }`, one striker left, the stoppage stays open.
  - `the_workplace_s_own_laid_off_take_its_struck_work`: as decide 32, with the view's members changed so that the
    farm's household of Place A has 2 persons laid off at utility A: its pair member there `employed 0, reserve 2`
    (built with `binding().with_living_force(2)` and `StaffingMemberState::try_new`). Its people at the utility did
    not stop, so it weighs the utility's offer: persons 2, struck pay `net($10 x 20 h) = $160`, other pay 0 (its
    4 at the farm are out: its own `Stop` decision there), money its cash, needs $364: without < needs, with >
    without: `Take`. Orders: `AboveRollsOrder { member_id: UTILITY_A.pair_member_id(FARM_A), hours: 20, cause:
    StruckWork }` and one `StaffingOrder { host_pool: UTILITY_A.pool_id(), to_member:
    UTILITY_A.pair_member_id(FARM_A), from_pool: UTILITY_A.pool_id(), from_member:
    UTILITY_A.pair_member_id(FARM_A), persons: 2, kind: PlaceTaken }`: the same pool and the same member, called
    back from its own reserve. At the farm's own offer it has no persons left to bring and refuses its own
    stopped work (`StoppedHere`).
  - `no_household_reads_another_s_decision_of_the_step`: decide 31 three times: as made; with the farm's member
    row in period 30's `member_labor_use` paid `Wage($12)` (one person's pay after tax $96 covers $91: the farm
    does not stop); and with the farm's cash in period 30's `closing.cash` raised by $1,000. The shop's
    `StopDecision` is equal in all three; only the farm's decision or its accounts differ. The shape guarantees
    it: `stop_accounts` and `seeker_accounts` take `view`, the book and the household's own decisions only
    (`own_decisions(&decisions, h)`), and the weighings are pure.
  - `employers_that_offer_at_once_raise_pay_with_no_stoppage`: the book of `fight::open` on the twin world with
    `employers: Employers::OfferAtOnce`. Decide 31: `orders.rates == [utility A, farm A, clinic A, shop A at
    $12]`, no `WithheldOrder`, no `Stop` decision in Place A. Close 31 on period 31 made from 30 with the four
    `RateReceipt`s `{ old_rate: $10, new_rate: $12 }` and nothing withheld: no stoppage, no employer record, no
    offer; the news has four `RateChanged { from: $10, to: $12 }` with `Cause::Measure`.
  - Rewrite Task 6's `a_measure_starts_nothing` as `a_measure_alone_orders_nothing`: over the same run, every
    `WithheldOrder` of a period has a `Stop` decision with `choice: Stop` of its household at its workplace, and
    every `AboveRollsOrder` has a `Take` decision and an offer of the close before.
  In `tests/fight.rs`:
  - `an_employer_paid_nothing_never_gives_way`: `employer_decides(&EmployerCount { losses: vec![(31, $0)], .. },
    31, $1,040, Some($0), 40) == NeverPaid`; with `None`: `NeverPaid`; with `Some($1,400)` and losses `[(31,
    $1,040)]`: `OfferStruckWork { hours: 40, cost: $1,040, asked_year: $1,040 }` (more than, not as much as); losses
    `[(31, $1,041)]`: `GiveWay`.
  - `the_baseline_skips_struck_periods`: 20 quiet periods of `World::scene_with_fight()`, Owner(A) paid by the shop
    $10 a period in periods 1 to 4 and $100 in 5 to 20 (the other three $0), periods 12 to 17 with a
    `WithheldReceipt` at the shop and paid $0: `baseline(&history, Owner(A), SHOP_A) == Some(79_230_769 micro)`:
    the 13 periods 20, 19, 18, 11 down to 2, ($100 x 10 + $10 x 3) / 13, rounded down.
  - `a_stoppage_before_any_baseline_period_has_no_baseline`: `baseline(&[], ..) == None`; one struck period alone:
    `None`; one quiet period paid $50: `Some($50)` (of the periods there are).
  - `a_household_walks_out_again_after_a_year` (Review Focus 4): `HouseholdCount { costs: vec![(10, $400)] }`;
    with pay_here $400, needs $420, money 0, asked_year $520: at period 11 `weigh_stop` is `Work` ($800); at
    period 23 (`within_year(23) == 0`) it is `Stop` again.
  - `the_quiet_fight_world_stays_still`: 34 steps of `World::scene_with_fight()`: every summary equals period 1's;
    every `fight.orders` is empty; every decision is a `Stop` decision with `choice: Work`.
  - On `fund_p2_fight()` = `down_fund_p2(Fight::Asked(none()))`, 120 steps each
    `Ok` (the runner refuses money or people not conserved):
    - `a_won_rate_s_first_period_in_the_slump` (Review Focus 1): count the `RateReceipt`s with `new_rate >
      old_rate`, those of them whose site has a `LaborUseReceipt` with `unfunded_hours > 0` in the same period,
      and those whose site has an `AdjustmentReceipt::Stop` with `hold: Held` in the same period; print the three
      counts with `eprintln!`. It asserts only that every step is `Ok`; nothing is mended in Part One.
    - `a_struck_workplace_s_rolls_fall_only_by_the_ordinary_rule` (Review Focus 2): some period has a
      `WithheldReceipt` (else fail with "no stoppage in fund-P2 to 120: report to the lead"); each
      `WithheldReceipt` has `rolls_hours == withheld_hours ==` its member's `opening_employed * hours_per_person` in
      that period's member receipts; print the sum of `separations` of struck members over the run.
    - `a_household_at_two_workplaces_decides_stop_first_then_struck_work` (Review Focus 5): in every period every
      `Stop` decision comes before every `StruckWork` decision; no household takes struck work where its own
      `Stop` decision of that period chose `Stop`, and its `TakeDecision` there has `own_people: StoppedHere`;
      print how many periods have a household with both kinds of decision.
- [ ] **Step 3: Run them and see them fail:** `mise run rust:test:q -- -p babylon-circuit-worlds -E 'test(sketch) |
  test(offer) | test(counts) | test(walkout) | test(broken) | test(reads_another) | test(employer) |
  test(baseline) | test(walks_out) | test(quiet_fight) | test(won_rate) | test(rolls) | test(two_workplaces) |
  test(own_laid_off) | test(shares_the_loss) | test(whole_loss) | test(measure_is_gone) | test(at_once) |
  test(alone_orders_nothing)'`.
  Expected: does not compile (no `fight::employer`, no `HouseholdDecision`); once compiling, the period tests fail
  because `decide` gives no order.
- [ ] **Step 4: Implement** `employer.rs`, `stoppage.rs`, `EmployerCount`, `baseline`, `own_takes` and
  `loss_shares` in `counts.rs`, the news variants.
- [ ] **Step 5: Implement `decide` and `close`** in `period.rs` as the two blocks above, with `own_ask`,
  `stop_accounts`, `seeker_accounts`, `shares` and the book's helpers as private functions; each under 100 lines
  and a cognitive complexity of 25 (split by step of the blocks).
- [ ] **Step 6: Run them and see them pass:** the command of Step 3, then `mise run rust:test:q -- -p
  babylon-circuit-worlds`. If `fund_p2_fight` is refused at some period, stop and report the period and the
  refusal's words (a refusal of the engine's orders names a fault of `decide` or of an engine task).
- [ ] **Run the gate:** the small worlds' gate; then, in the background, the 14 long tests and
  `hours_fold_every_reference_run`.
- [ ] **Commit** the subject above. The body says: the employer's rule over all its workplaces against the baseline
  of the periods with no hours withheld; both counts over the last year, started again on a win and kept after a
  failed walkout; the decisions of a period in the design's order, PF5 workplace by workplace and then PF6, each
  household from its own accounts; one employer has one loss a period, shared among its struck workplaces by
  what each paid it; a won offer is a rate from the next period; struck work offered from the period after a
  stoppage begins, and places taken at the close of the period they are taken up, read from what the engine
  moved; employers that offer at once, the bench's instrument; the three counts of Review Focus 1 printed, not
  mended. Ends with `Part of PER-371` and the `Co-Authored-By` line.

**What this task must not do:**
- Let a household's accounts read another household's decision of the same step, or the owners' accounts.
- Put a constant where a response turns: the employer compares its own loss with a year of what is asked.
- Change the runner's composition, the engine, or any byte of a world that does not ask.
- Mend the first period of a won rate (Review Focus 1): count it.

---

### Task 6c: The news, and the measures in a workplace's panel

**Built after Task 8:** the news it words has kinds that Task 8 adds.

After this task a person reads, on the Fight tab, the period's news, each item with its cause ("Place A shop: pay
short of needs: $80.00 against $91.00 a person · cause: a measure"), and in a workplace's panel the four measures
that hold for its people and what the period's work paid the owners and paid the people. A measure starts
nothing; the rows only say it.

**Files:**
- Modify: `C/fight.rs` (`news_rows`, `news_words`, `cause_words`, `order_words`, `measure_words`, `A_PERSON`;
  `paint_fight` draws the news in the tab's `FightBody`; `panel_rows` adds the measure rows);
  `C/inspect.rs` (`measure_rows`); `C/panel.rs` (nothing but the call through `rows_for`). Tests in
  `C/fight.rs` and `C/inspect.rs`; `no_word_names_a_taker_an_enemy` (Task 5c) gains the news rows.

**Interfaces:**

Consumes (Tasks 6 and 8): `PeriodFight.measures: Vec<MeasureRow { period, workplace, household: Option<Household>,
measure: Measure, begins: Begins }>`; `Measure::{PayShort { pay, needs }, PayCut { from, to }, HandsShort {
asked_hours, filled_hours }, TakeGrows { take, before, laid_off, cut }}`; `Begins::{Now, Continues}`;
`fight::take_of(result, w) -> Result<WorkplaceTake { to_owners, to_people }, FightError>`; `PeriodFight.news:
Vec<News { period, item: NewsItem, cause: Cause }>` with the eight `NewsItem`s of File Structure, "The small
worlds' new modules" and `Cause::{Measure, Weighing(Household), Employer(Household), Order(OrderKind), Founding,
Contract}`.

Produces:
```rust
// C/fight.rs
/// The unit word of a measure's money, which Task 6 records for one person at full work (the plan's
/// "Calls of the lead", 10).
pub const A_PERSON: &str = "a person";
/// (label, value) of a measure; no figure divides money by hours.
#[must_use] pub fn measure_words(measure: &Measure) -> (String, String);
#[must_use] pub fn cause_words(cause: &Cause) -> String;
#[must_use] pub const fn order_words(kind: OrderKind) -> &'static str;
#[must_use] pub fn news_words(item: &NewsItem) -> String;
/// One line a news item, in record order: "{news_words(item)} · cause: {cause_words(cause)}"; empty without a fight.
#[must_use] pub fn news_rows(result: &PeriodResult) -> Vec<String>;
// C/inspect.rs
/// A workplace's measures (`PeriodFight.measures` of `w`, in record order; "; begins this period" after the value
/// when `Begins::Now`; a row whose `household` is `Some(h)` has the label "{label} ({h.label()})"), then
/// ("This period's work paid the owners", to_owners) and ("It paid the people",
/// to_people) from `take_of`. Empty without a fight.
/// # Errors
/// `FrameError::Edge` with the small worlds' words when `take_of` refuses.
pub fn measure_rows(result: &PeriodResult, w: Workplace) -> Result<Vec<(String, String)>, FrameError>;
```

The words (each `{..}` is a field through `human_numbers::currency` for money, `human_numbers::grouped` for hours
and persons; `{w}` is `workplace.label()`, `{h}` is `household.label()`):

| Record | Words |
| --- | --- |
| `PayShort` | ("Pay short of needs", "{pay} against {needs} a person: short by {needs - pay}") |
| `PayCut` | ("Pay cut", "from {from} to {to}") |
| `HandsShort` | ("Hours asked and not filled", "{asked_hours - filled_hours} of {asked_hours} hours") |
| `TakeGrows` | ("Owners' take growing", "{take}, was {before}; {laid_off} laid off") and, when `cut` is above 0, "; pay cut by {cut}" |
| `MeasureBegins(row)` | "{w}: {label in lower case}: {value}" |
| `Stopped { workplace, out, ask }` | "{w}: a stoppage. {sum of out} people out. They ask {rate_asked} an hour" |
| `WentBack { workplace, household }` | "{h} went back to work at {w}" |
| `StruckWorkOffered(offer)` | "{w}: struck work offered: {hours} hours at {rate} an hour, for period {period}" |
| `StruckWorkTaken { workplace, by }` | "{w}: struck work taken by {h} ({persons} people)", households joined by ", " |
| `GaveWay { workplace, rate }` | "{w}: the owners gave way: it pays {rate} an hour. Nobody negotiated: it is a rate, and nothing holds it" |
| `PlacesTaken { workplace, persons }` | "{w}: {persons} places taken by people who looked for work" |
| `RateChanged { workplace, from, to }` | "{w}: pay from {from} to {to} an hour" |
| `Cause` | Measure "a measure"; Weighing(h) "what {h} weighed"; Employer(h) "the owners' count ({h})"; Order(k) `order_words(k)`; Founding "a fund founded"; Contract "a contract" |
| `OrderKind` | Rate "a rate"; Withheld "hours withheld"; AboveRolls "hours above the rolls"; Floor "a floor on the rolls"; Staffing "places moved"; FundPayment "a payment from a fund"; WageShare "a share of wages" |

What is drawn: lines of the Fight tab's `FightBody` (`controls::text`, 12.0, `theme::PAPER`, starting values;
the lead's to tune), and rows of the workplace's panel (`panel::spawn_rows`), last after the rate and the gate.
Nothing on the plane.

- [ ] **Step 1: Write the failing tests.**

In `C/fight.rs`'s tests:
```rust
/// One news item of every kind and one of every cause, built from a fight period's own records (Task 8 has
/// brought the last seven kinds by the time this task is built).
fn every_news(result: &PeriodResult) -> Result<Vec<News>, Box<dyn Error>> {
    let shop = shop_a();
    let h = shop.workers();
    let rate = result.receipts.member_labor_use.iter()
        .find(|r| r.site_id == shop.site_id() && r.payee == h.principal())
        .ok_or("the shop's own member")?.compensation.wage_rate();
    let step = pay_step(&World::scene_with_fight(), shop);
    let asked = rate.checked_add(step).map_err(|e| format!("{e:?}"))?.checked_add(step).map_err(|e| format!("{e:?}"))?;
    let persons = result.members.iter().find(|m| m.site_id == shop.site_id()
        && m.member.household_id() == h.principal()).ok_or("the member")?.opening_employed;
    let hours = result.summary.hours_attended[shop.index()];
    let ask = Ask { workplace: shop, asker: Asker::Household(h), rate_now: rate, rate_asked: asked, steps: 2,
        terms: Vec::new(), named: Vec::new() };
    let measure = MeasureRow { period: result.period, workplace: shop, household: Some(h),
        measure: Measure::HandsShort { asked_hours: result.asked[shop.index()], filled_hours: hours },
        begins: Begins::Now };
    let items = vec![
        (NewsItem::MeasureBegins(measure), Cause::Measure),
        (NewsItem::Stopped { workplace: shop, out: vec![(h, persons)], ask }, Cause::Weighing(h)),
        (NewsItem::WentBack { workplace: shop, household: h }, Cause::Weighing(h)),
        (NewsItem::StruckWorkOffered(StruckOffer { workplace: shop, period: result.period + 1, hours, rate }),
            Cause::Employer(Household::Owner(Place::A))),
        (NewsItem::StruckWorkTaken { workplace: shop, by: vec![(farm_a().workers(), persons)] },
            Cause::Order(OrderKind::AboveRolls)),
        (NewsItem::GaveWay { workplace: shop, rate: asked }, Cause::Employer(Household::Owner(Place::A))),
        (NewsItem::PlacesTaken { workplace: shop, persons }, Cause::Order(OrderKind::Staffing)),
        (NewsItem::RateChanged { workplace: shop, from: rate, to: asked }, Cause::Order(OrderKind::Rate)),
    ];
    Ok(items.into_iter().map(|(item, cause)| News { period: result.period, item, cause }).collect())
}

#[test]
fn every_news_row_names_its_cause() -> TestResult {
    let mut result = fight_period()?;
    let news = every_news(&result)?;
    result.fight.as_mut().ok_or("the fight")?.news = news.clone();
    let rows = news_rows(&result);
    assert_eq!(rows.len(), news.len());
    for (row, item) in rows.iter().zip(&news) {
        assert!(row.ends_with(&format!(" · cause: {}", cause_words(&item.cause))), "{row}");
        assert!(row.starts_with(&news_words(&item.item)), "{row}");
    }
    assert_eq!(rows[5], format!("{}: the owners gave way: it pays {} {AN_HOUR}. Nobody negotiated: it is a rate, \
        and nothing holds it · cause: the owners' count ({})", shop_a().label(),
        human_numbers::currency(match &news[5].item { NewsItem::GaveWay { rate, .. } => rate.micro_units(),
            _ => return Err("the sixth item gives way".into()) }), Household::Owner(Place::A).label()));
    assert!(news_rows(&Runner::open()?.step()?.clone()).is_empty());
    Ok(())
}

#[test]
fn news_rows_are_the_record_s() -> TestResult {
    let mut runner = Runner::open_world(&World::scene_with_fight())?;
    runner.strike(Shock::HarvestFails, Places::Both, Lasts::UntilLifted)?;
    let mut seen = 0;
    for _ in 0..60 {
        let result = runner.step()?.clone();
        let fight = result.fight.as_ref().ok_or("the fight")?;
        let rows = news_rows(&result);
        assert_eq!(rows.len(), fight.news.len(), "period {}", result.period);
        for (row, item) in rows.iter().zip(&fight.news) {
            if let NewsItem::MeasureBegins(MeasureRow { workplace, measure: Measure::PayShort { pay, needs }, .. })
                = &item.item {
                assert!(row.starts_with(&workplace.label()));
                assert!(row.contains(&human_numbers::currency(pay.micro_units())));
                assert!(row.contains(&human_numbers::currency(needs.micro_units())));
            }
        }
        seen += rows.len();
    }
    assert!(seen > 0, "no news in 60 periods of the slump: stop and tell the lead");
    Ok(())
}
```
(`shop_a`, `farm_a`, `fight_period` are this module's test helpers from Tasks 2c and 5c.)

In `C/inspect.rs`'s tests:
```rust
#[test]
fn measure_rows_divide_no_money_by_hours() -> TestResult {
    use babylon_circuit_worlds::fight::{self, pay_step, Begins, Measure, MeasureRow};
    use crate::small_world::fight::{measure_words, A_PERSON};
    let mut runner = Runner::open_world(&babylon_circuit_worlds::World::scene_with_fight())?;
    let before = runner.step()?.clone();
    let mut result = runner.step()?.clone();
    let shop = shop_a();
    let h = shop.workers();
    let reading = crate::small_world::reading::read_period(&result)?;
    let sum = |kind: PaymentKind, payee: bool| -> i128 { reading.payments.iter()
        .filter(|p| p.kind == kind && (if payee { p.payee } else { p.payer }) == Party::Household(h))
        .map(|p| p.amount).sum() };
    let (pay, needs) = (Currency::from_micro_units(sum(PaymentKind::Wages, true)),
        Currency::from_micro_units(sum(PaymentKind::Purchases, false)));
    let rate = result.receipts.member_labor_use.iter().find(|r| r.site_id == shop.site_id()
        && r.payee == h.principal()).ok_or("the own member")?.compensation.wage_rate();
    let step = pay_step(runner.world(), shop);
    let (take, was) = (fight::take_of(&result, shop)?, fight::take_of(&before, shop)?);
    let measures = [
        Measure::PayShort { pay, needs },
        Measure::PayCut { from: rate, to: rate.checked_sub(step).map_err(|e| format!("{e:?}"))? },
        Measure::HandsShort { asked_hours: result.asked[shop.index()],
            filled_hours: result.summary.hours_attended[shop.index()] },
        Measure::TakeGrows { take: take.to_owners, before: was.to_owners, laid_off: result.closing.reserve[shop.index()],
            cut: Currency::from_micro_units(0) },
    ];
    let fight_now = result.fight.as_mut().ok_or("the fight")?;
    fight_now.measures = measures.iter().map(|m| MeasureRow { period: result.period, workplace: shop,
        household: Some(h), measure: m.clone(), begins: Begins::Continues }).collect();
    let rows = measure_rows(&result, shop)?;
    let money = |c: Currency| human_numbers::currency(c.micro_units());
    assert_eq!(rows[0], (format!("Pay short of needs ({})", h.label()), format!("{} against {} {A_PERSON}: short by {}",
        money(pay), money(needs), money(needs.checked_sub(pay).map_err(|e| format!("{e:?}"))?))));
    let cut = rate.checked_sub(step).map_err(|e| format!("{e:?}"))?;
    assert_eq!(rows[1].1, format!("from {} to {}", money(rate), money(cut)));
    assert_eq!(rows[4], ("This period's work paid the owners".to_owned(), money(take.to_owners)));
    assert_eq!(rows[5], ("It paid the people".to_owned(), money(take.to_people)));
    for (label, value) in &rows {
        for unit in ["an hour", "per hour", "a hour", "/h"] {
            assert!(!label.contains(unit) && !value.contains(unit), "{label} | {value}");
        }
    }
    for m in &measures {
        let (label, value) = measure_words(m);
        assert!(rows.contains(&(format!("{label} ({})", h.label()), value)));
    }
    Ok(())
}
```
and `no_word_names_a_taker_an_enemy`'s `rows_about_takers` gains `news_rows` of a period carrying `every_news`.

- [ ] **Step 2: See them fail.** `mise run rust:test:q -- -p babylon-client -E 'test(small_world)'`. Expected: does
  not compile: no `news_rows`, `measure_rows`, `measure_words`, `cause_words`.
- [ ] **Step 3: Implement** the words of the table, `news_rows`, `measure_rows` (a `FightError` of `take_of` is
  `FrameError::Edge(format!("{error:?}"))`), the news lines in `paint_fight`'s `FightBody`, and the measure
  rows in `panel_rows` for a picked workplace after the gate's row.
- [ ] **Step 4: See them pass.** `mise run rust:test:q -- -p babylon-client -E 'test(small_world)'`. Expected: all
  pass; the two pinned frame tests unchanged. If `news_rows_are_the_record_s` finds no news in 60 periods, stop
  and report to the lead (Task 6's measures should begin in the slump).
- [ ] **Step 5: Run the companion's gate. Commit** `feat(client): the news with its causes, and a workplace's
  measures` (body: `Part of PER-371`).

**What this task must not do:** divide money by hours or print a measure with "an hour"; print a figure that is
not a field of a `MeasureRow`, a `News` or a `WorkplaceTake` (or the difference the table writes); let a measure
change anything but its rows; change a frame.

---

### Task 8c: The stoppage, the ask and both counts on screen; Part One's proof script

After this task a person sees a whole stoppage in the scene: on the Fight tab "STOPPAGE · Place A shop · from
period 31", the people out, what they ask and that nobody called it, "It has cost the owners $1,050.00 of a year's
$1,040.00" and each stopping household's own count; the tab's caption says "Fight · {n} stopped" with n the
stoppages under way; the struck
workplace's panel says "Struck work offered" with its hours, rate and period; a household's panel shows what it
weighed and what it had to live on. The lead runs Part One's proof on the real display.

**Files:**
- Modify: `C/fight.rs` (`stoppage_rows`, `end_words`, `condition_words`; `paint_fight` draws them in `FightBody`
  before the news; `struck_rows` gains the offer's row); `C/panel.rs` (`paint_lower` passes the count of stoppages
  under way to `lower_caption(Lower::Fight, ..)`); `C/inspect.rs` (`weighing_rows`; `panel_rows` calls it for a
  household); `C/script.rs` (`ScriptReport.fight`, `build_report`); `C/script_tests.rs` (`PROOF_PF8` and its tests);
  `C/scene_tests.rs` (`the_report_carries_the_fight`); `no_word_names_a_taker_an_enemy` gains these rows.
  Stored hours' Task 7 has added `ScriptReport.stored_hours`; keep it and add `fight` after it.

**Interfaces:**

Consumes (Tasks 7 and 8): `PeriodFight.stoppages: Vec<Stoppage { workplace, began, ask: Ask, periods:
Vec<StoppagePeriod { period, out: Vec<(Household, u64)>, filled: Vec<(Household, u64)>, paid }>, ended:
Option<(u64, StoppageEnd)> }>` (`paid` is empty in Part One and is not read); `PeriodFight.offered:
Vec<StruckOffer { workplace, period, hours, rate }>`; `PeriodFight.employers: Vec<EmployerRecord { employer, workplace,
decision: EmployerDecision }>` (`GiveWay { cost, asked_year }`, `OfferStruckWork { hours, cost, asked_year }`,
`NeverPaid`); `PeriodFight.decisions: Vec<HouseholdDecision>` (`Stop { household, workplace, decision:
StopDecision }`, `StruckWork { household, workplace, decision: TakeDecision }`) with the fields of
`StopDecision`, `StopAccounts`, `TakeDecision`, `SeekerAccounts`, `Ground`, `Condition`, `OwnPeople` in
File Structure, "The small worlds' new modules". In `out` and in `filled` every figure is persons, by household.

Produces:
```rust
// C/fight.rs
/// "the owners gave way", "the people went back", "their places were taken".
#[must_use] pub const fn end_words(end: StoppageEnd) -> &'static str;
/// "yes" for `Holds`, "no" for `Fails`.
#[must_use] pub const fn condition_words(condition: Condition) -> &'static str;
/// The Fight tab's lines of every stoppage of the period, in record order; empty without a fight.
/// # Errors
/// `FrameError::Arithmetic` for a sum that overflows.
pub fn stoppage_rows(result: &PeriodResult) -> Result<Vec<String>, FrameError>;
// C/inspect.rs
/// What a household weighed this period: its `HouseholdDecision`s of `PeriodFight.decisions`, in record order.
#[must_use] pub fn weighing_rows(result: &PeriodResult, h: Household) -> Vec<(String, String)>;
// C/script.rs, ScriptReport gains:
/// The Fight tab's lines of the last period kept: `stoppage_rows`, then `news_rows`; empty without a fight.
pub fight: Vec<String>,
// C/script_tests.rs
/// Part One's proof script; the lead runs it on the display.
const PROOF_PF8: &str;
```

The lines of `stoppage_rows`, for each stoppage (figures through `human_numbers`; `{w}` its workplace's label):
1. `"STOPPAGE · {w} · from period {began}"`, and when `ended` is `Some((p, end))`:
   `" · ended at period {p}: {end_words(end)}"` on the same line;
2. for each `(h, persons)` of the last `StoppagePeriod`'s `out`: `"{persons} people of {h} out"`;
3. `"They ask {rate_asked} an hour, {steps} steps from {rate_now}"`;
4. for `Asker::Household(h)`: `"Asked by {h}. Nobody called it."`; for `Asker::Organization(id)`:
   `"Called by organization {id.0}"`;
5. for the `EmployerRecord` of its workplace this period, if any: `GiveWay` → `"It has cost the owners {cost} of a
   year's {asked_year}: they gave way"`; `OfferStruckWork` → `"It has cost the owners {cost} of a year's
   {asked_year}: they offer {hours} hours of struck work"`; `NeverPaid` → `"Its owners were paid nothing by their
   workplaces in the periods counted: a stoppage costs them nothing"`;
6. for each `HouseholdDecision::Stop` of that workplace: `"It has cost {h} {cost_within_year} of a year's
   {asked_year}"` (both from `decision.weighed`);
7. for each `(h, persons)` of the last `StoppagePeriod`'s `filled`: `"{persons} people of {h} on struck work"`.

`struck_rows` (Task 5c) gains, first, one row for each offer of `PeriodFight.offered` whose workplace is `w`:
("Struck work offered", "{hours} hours at {rate} an hour, for period {period}").

The rows of `weighing_rows`:
- `Stop`: ("Weighed a stoppage at {w}", "stops" or "works"), ("Ground", "called" / `measure_words(m)`'s label in
  lower case / "nothing to stop for"), ("Something to stop for", `something`), ("Can go without the pay",
  `can_go_without`), ("Worth it", `worth_it`) through `condition_words`, then the money of `weighed`: ("Pay
  here", `pay_here`), ("Pay elsewhere", `pay_elsewhere`), ("Money held", `money`), ("Funds would pay",
  `funds_pay`), ("Needs", `needs`), ("Cost of the fight in the last year", `cost_within_year`), ("A year of what
  is asked", `asked_year`), ("Cost of this period", `decision.cost_this_period`).
- `StruckWork`: ("Weighed struck work at {w}", "takes" or "refuses"), ("Goes without", `goes_without`), ("More to
  live on", `more_to_live_on`), ("To live on without it", `without`), ("To live on with it", `with`), then of
  `weighed`: ("Persons", `persons`), ("Struck work's pay", `struck_pay`), ("Money held", `money`), ("Benefit",
  `benefit`), ("Relief", `relief`), ("Other people's pay", `other_pay`), ("Needs", `needs`), ("Its own people
  stopped here", "yes" for `StoppedHere`, "no" for `NotStoppedHere`).

What is drawn: lines of the Fight tab and rows of the household's panel, as Tasks 2c and 6c draw theirs; the gate
of Task 4c; nothing new on the plane. Read from `PeriodFight`. `lower_caption(Lower::Fight, n)` reads
"Fight · {n} stopped" with `n` the stoppages with `ended` of `None` in the last period of the history.

- [ ] **Step 1: Write the failing tests.**

In `C/fight.rs`'s tests:
```rust
/// The scene's world with the fight, the harvest failed in both places until lifted, for `periods` periods.
fn slump(periods: usize) -> Result<Vec<PeriodResult>, Box<dyn Error>> {
    let mut runner = Runner::open_world(&World::scene_with_fight())?;
    runner.strike(Shock::HarvestFails, Places::Both, Lasts::UntilLifted)?;
    for _ in 0..periods { runner.step()?; }
    Ok(runner.history().to_vec())
}

#[test]
fn a_stoppage_is_drawn_from_its_record() -> TestResult {
    let history = slump(60)?;
    let (result, stoppage) = history.iter().find_map(|r| {
        r.fight.as_ref()?.stoppages.iter().find(|s| s.began == r.period).map(|s| (r, s.clone()))
    }).ok_or("no stoppage began in 60 periods of the slump: stop and tell the lead")?;
    let rows = stoppage_rows(result)?;
    let w = stoppage.workplace.label();
    let ended = stoppage.ended.map_or_else(String::new, |(p, end)| format!(" · ended at period {p}: {}",
        end_words(end)));
    assert_eq!(rows[0], format!("STOPPAGE · {w} · from period {}{ended}", stoppage.began));
    let last = stoppage.periods.last().ok_or("a period of the stoppage")?;
    for (h, persons) in &last.out {
        assert!(rows.contains(&format!("{} people of {} out", human_numbers::grouped(u128::from(*persons)),
            h.label())));
    }
    assert!(rows.contains(&format!("They ask {} {AN_HOUR}, {} steps from {}",
        human_numbers::currency(stoppage.ask.rate_asked.micro_units()), stoppage.ask.steps,
        human_numbers::currency(stoppage.ask.rate_now.micro_units()))));
    let fight = result.fight.as_ref().ok_or("the fight")?;
    for decision in &fight.decisions {
        if let HouseholdDecision::Stop { household, workplace, decision } = decision {
            if *workplace == stoppage.workplace {
                assert!(rows.contains(&format!("It has cost {} {} of a year's {}", household.label(),
                    human_numbers::currency(decision.weighed.cost_within_year.micro_units()),
                    human_numbers::currency(decision.weighed.asked_year.micro_units()))));
            }
        }
    }
    // The people at the gate are the record's people out.
    let gate = crate::small_world::frame::at_the_gate(result)?;
    for (h, persons) in &last.out {
        assert_eq!(gate.get(&(*h, stoppage.workplace)).copied(), Some(usize::try_from(*persons)?));
    }
    // Both counts: once the owners' record of this workplace is there, its line is on the tab.
    if let Some(record) = fight.employers.iter().find(|e| e.workplace == stoppage.workplace) {
        let cost_line = match &record.decision {
            EmployerDecision::GiveWay { cost, asked_year } | EmployerDecision::OfferStruckWork { cost, asked_year, .. }
                => format!("It has cost the owners {} of a year's {}", human_numbers::currency(cost.micro_units()),
                    human_numbers::currency(asked_year.micro_units())),
            EmployerDecision::NeverPaid =>
                "Its owners were paid nothing by their workplaces in the periods counted".to_owned(),
        };
        assert!(rows.iter().any(|row| row.starts_with(&cost_line)), "{cost_line}");
    }
    for (h, persons) in &last.filled {
        assert!(rows.contains(&format!("{} people of {} on struck work",
            human_numbers::grouped(u128::from(*persons)), h.label())));
    }
    Ok(())
}

#[test]
fn the_offer_s_row_is_the_record_s() -> TestResult {
    let (mut result, hours) = taken_period()?;
    let rate = result.receipts.member_labor_use.iter()
        .find(|r| r.site_id == shop_a().site_id() && r.payee == shop_a().workers().principal())
        .ok_or("the shop's own member")?.compensation.wage_rate();
    let offer = StruckOffer { workplace: shop_a(), period: result.period + 1, hours, rate };
    result.fight.as_mut().ok_or("the fight")?.offered.push(offer.clone());
    let rows = struck_rows(&result, shop_a())?;
    assert_eq!(rows[0], ("Struck work offered".to_owned(), format!("{} hours at {} {AN_HOUR}, for period {}",
        human_numbers::grouped(u128::from(offer.hours)), human_numbers::currency(offer.rate.micro_units()),
        offer.period)));
    assert!(struck_rows(&result, farm_a())?.iter().all(|(label, _)| label != "Struck work offered"));
    Ok(())
}
```

In `C/inspect.rs`'s tests:
```rust
#[test]
fn a_household_s_panel_shows_what_it_weighed() -> TestResult {
    use babylon_circuit_worlds::fight::{HouseholdDecision, StopChoice};
    use crate::small_world::fight::condition_words;
    let mut runner = Runner::open_world(&babylon_circuit_worlds::World::scene_with_fight())?;
    runner.strike(babylon_circuit_worlds::Shock::HarvestFails, babylon_circuit_worlds::Places::Both,
        babylon_circuit_worlds::Lasts::UntilLifted)?;
    let mut found = None;
    for _ in 0..60 {
        let result = runner.step()?.clone();
        let stop = result.fight.as_ref().and_then(|f| f.decisions.iter().find_map(|d| match d {
            HouseholdDecision::Stop { household, workplace, decision } if decision.choice == StopChoice::Stop =>
                Some((*household, *workplace, decision.clone())),
            _ => None,
        }));
        if let Some(stop) = stop { found = Some((result, stop)); break; }
    }
    let (result, (h, w, decision)) = found.ok_or("no household stopped in 60 periods: stop and tell the lead")?;
    let all = weighing_rows(&result, h);
    // The rows of this decision: from its "Weighed a stoppage at {w}" up to the next row whose label starts "Weighed".
    let head = format!("Weighed a stoppage at {}", w.label());
    let start = all.iter().position(|(label, _)| *label == head).ok_or("the decision's first row")?;
    let end = all[start + 1..].iter().position(|(label, _)| label.starts_with("Weighed"))
        .map_or(all.len(), |k| start + 1 + k);
    let rows = all[start..end].to_vec();
    let money = |c: Currency| human_numbers::currency(c.micro_units());
    assert_eq!(value(&rows, &head), Some("stops".to_owned()));
    assert_eq!(value(&rows, "Worth it"), Some(condition_words(decision.worth_it).to_owned()));
    assert_eq!(value(&rows, "Money held"), Some(money(decision.weighed.money)));
    assert_eq!(value(&rows, "Needs"), Some(money(decision.weighed.needs)));
    assert_eq!(value(&rows, "Cost of this period"), Some(money(decision.cost_this_period)));
    let pick = Pick::Body(Party::Household(h));
    let panel = crate::small_world::fight::panel_rows(&[result.clone()], 0, &pick)?;
    assert!(all.iter().all(|row| panel.contains(row)));
    Ok(())
}
```
(`Condition`, `StopChoice` derive `Clone, Copy, PartialEq, Eq` as File Structure, "The engine's orders", says for
fieldless enums; if Task 7 left `Copy` off, compare by `==` on references.)

In `C/scene_tests.rs`:
```rust
#[test]
fn the_report_carries_the_fight() -> TestResult {
    use babylon_circuit_worlds::{Lasts, Places, Runner, Shock};
    // The first period with news, read from a runner of the same run.
    let mut runner = Runner::open_world(&BabylonWorld::scene_with_fight())?;
    runner.strike(Shock::HarvestFails, Places::Both, Lasts::UntilLifted)?;
    let mut first = None;
    for _ in 0..60 {
        let result = runner.step()?;
        if result.fight.as_ref().is_some_and(|f| !f.news.is_empty()) { first = Some(result.period); break; }
    }
    let period = first.ok_or("no news in 60 periods: stop and tell the lead")?;
    let text = format!("{{\"fight\":\"on\"}}\n{{\"strike\":{{\"shock\":\"harvest_fails\",\"places\":\"both\",\
        \"lasts\":\"until_lifted\"}}}}\n{{\"step\":{period}}}\n{{\"report\":\"f\"}}\n");
    let frames = usize::try_from(period)? * 400 + 400;
    let (app, folder) = scripted(&text, frames)?;
    let kept: Value = serde_json::from_str(&std::fs::read_to_string(folder.0.join("f.json"))?)?;
    let result = app.world().resource::<SceneRunner>().runner.history().last().ok_or("a period")?.clone();
    assert_eq!(result.period, period);
    let mut want = crate::small_world::fight::stoppage_rows(&result)?;
    want.extend(crate::small_world::fight::news_rows(&result));
    assert!(!want.is_empty());
    assert_eq!(kept["fight"], serde_json::json!(want));
    Ok(())
}
```

In `C/script_tests.rs`, the script and its two tests. The script is written with six slots, `<S>`, `<O-S>`,
`<E-O>`, `<60-E>`, `<W>` and `<H>`; Step 2 fills them from the run:
```rust
/// Part One's proof (the pay fight's Task 8c): the fight on, the harvest failed in both places until lifted,
/// 60 periods; captures at the first stoppage, at the first offer of struck work and at the end of the first
/// stoppage. The lead runs it on the display.
const PROOF_PF8: &str = r#"{"beat_millis":60}
{"wait_frames":120}
{"fight":"on"}
{"strike":{"shock":"harvest_fails","places":"both","lasts":"until_lifted"}}
{"lower":"fight"}
{"step":<S>}
{"wait_frames":30}
{"capture":"pf8-stoppage"}
{"pick":"<W>"}
{"wait_frames":30}
{"capture":"pf8-stoppage-workplace"}
{"pick":"<H>"}
{"wait_frames":30}
{"capture":"pf8-stoppage-household"}
{"particles":"people"}
{"wait_frames":60}
{"capture":"pf8-stoppage-people"}
{"particles":"groups"}
{"report":"pf8-stoppage"}
{"step":<O-S>}
{"pick":"<W>"}
{"wait_frames":30}
{"capture":"pf8-offer"}
{"report":"pf8-offer"}
{"step":<E-O>}
{"wait_frames":30}
{"capture":"pf8-end"}
{"report":"pf8-end"}
{"step":<60-E>}
{"report":"pf8-60"}
"quit"
"#;

#[test]
fn the_proof_script_of_the_pay_fight_parses() {
    let commands = script::parse_script(PROOF_PF8).expect("the proof parses");
    assert_eq!(commands.len(), 31);
    assert_eq!(commands[2], ScriptCommand::Fight("on".into()));
    assert_eq!(commands[3], ScriptCommand::Strike { shock: "harvest_fails".into(), places: "both".into(),
        lasts: "until_lifted".into() });
    let steps: u32 = commands.iter().filter_map(|c| match c { ScriptCommand::Step(n) => Some(*n), _ => None }).sum();
    assert_eq!(steps, 60);
}

/// The script's periods and picks are those of the run it shows: the first period in which a stoppage begins
/// (S), its workplace (W) and the first household out (H); the first close that offers struck work at W (O); the
/// first period whose record shows that first stoppage ended (E, which is where `pf8-end` is taken; a `WentBack`
/// end is written a period late, as `(E - 1, WentBack)`, so its `ended.0` may be E - 1).
#[test]
fn the_proof_s_periods_are_its_run_s() -> Result<(), Box<dyn std::error::Error>> {
    use crate::small_world::frame;
    use babylon_circuit_worlds::{Lasts, Places, Runner, Shock, World};
    let mut runner = Runner::open_world(&World::scene_with_fight())?;
    runner.strike(Shock::HarvestFails, Places::Both, Lasts::UntilLifted)?;
    for _ in 0..60 { runner.step()?; }
    let history = runner.history();
    let first = history.iter().find_map(|r| r.fight.as_ref()?.stoppages.iter()
        .find(|s| s.began == r.period).cloned()).ok_or("no stoppage in 60 periods: stop and tell the lead")?;
    let s = first.began;
    let o = history.iter().find(|r| r.fight.as_ref()
            .is_some_and(|f| f.offered.iter().any(|offer| offer.workplace == first.workplace)))
        .map(|r| r.period).ok_or("no struck work offered at W in 60 periods: stop and tell the lead")?;
    let e = history.iter().find(|r| r.fight.as_ref().is_some_and(|f| f.stoppages.iter()
            .any(|st| st.workplace == first.workplace && st.began == s && st.ended.is_some())))
        .map(|r| r.period).ok_or("the first stoppage does not end in 60 periods: stop and tell the lead")?;
    let h = first.periods.first().and_then(|p| p.out.first()).map(|(h, _)| *h).ok_or("nobody out")?;
    assert!(s <= o && o <= e && e <= 60, "the order is S {s}, O {o}, E {e}: tell the lead before writing the script");
    let want = [s, o - s, e - o, 60 - e];
    let commands = script::parse_script(PROOF_PF8)?;
    let steps: Vec<u64> = commands.iter().filter_map(|c| match c { ScriptCommand::Step(n) => Some(u64::from(*n)),
        _ => None }).collect();
    let picks: Vec<&str> = commands.iter().filter_map(|c| match c { ScriptCommand::Pick(id) => Some(id.as_str()),
        _ => None }).collect();
    assert_eq!(steps, want, "write S {s}, O-S, E-O, 60-E into PROOF_PF8");
    assert_eq!(picks, [frame::workplace_id(first.workplace), frame::household_id(h), frame::workplace_id(first.workplace)],
        "write W and H into PROOF_PF8");
    Ok(())
}
```

- [ ] **Step 2: See them fail, then fill the script.** `mise run rust:test:q -- -p babylon-client -E
  'test(small_world)'`. Expected first: does not compile (no `stoppage_rows`, `weighing_rows`,
  `ScriptReport.fight`); after Step 3, `the_proof_s_periods_are_its_run_s` fails and prints S, O, E, W and H (and
  `the_proof_script_of_the_pay_fight_parses` fails while the slots stand, since `<S>` is not JSON). Write the
  four figures and two ids into `PROOF_PF8` in place of the slots; both pass. If any of the test's "stop and tell
  the lead" words show, stop: the run has no such period, and the lead decides the script.
- [ ] **Step 3: Implement** `end_words`, `condition_words`, `stoppage_rows` and `weighing_rows` as the lists above
  say; `struck_rows` gains the offer's row; `paint_fight` draws, in order, `stoppage_rows`, `news_rows` (a refusal
  of `stoppage_rows` is one line in `theme::RED`: "The fight's rows cannot be built: {error}"); `panel_rows` adds
  `weighing_rows` for a picked household or its particle; `paint_lower` counts the stoppages under way;
  `build_report` fills `fight` from the last period of the history (empty when it has no fight). The 8c test
  `the_offer_s_row_is_the_record_s` lives in `C/fight.rs`'s tests beside the copied `taken_period`.
- [ ] **Step 4: See them pass.** `mise run rust:test:q -- -p babylon-client -E 'test(small_world)'`. Expected: all
  pass; `a_world_with_no_fight_draws_as_before` and `without_a_stoppage_every_frame_is_as_before` unchanged;
  `no_word_names_a_taker_an_enemy` passes with the stoppage and weighing rows of `slump(60)` added to its list.
- [ ] **Step 5: Hand the lead the proof.** Do not run it. The command, from `rust/`, in a folder made by `mktemp
  -d` holding `PROOF_PF8` as `proof.jsonl`: `mise exec -- cargo run -p babylon-client -- --small-world
  --small-world-script <folder>/proof.jsonl`. What the lead must see to call it right:
  - `pf8-stoppage.png`: the Fight tab open, its caption "Fight · {n} stopped" with n the report's stoppages under
    way (expect most workplaces of both places stopped at about period 20: one basket a place, and a person's pay
    at full work falls below its needs at about the same close everywhere; the line "STOPPAGE · {W} · from
    period {S}", the people out, "They ask ... an hour, ... steps from ...", "Asked by .... Nobody called it.";
    on the plane, no bone dots going into W, W's hours ring gone or thin, and W's workers' group standing at W's
    gate below it (if nobody pays it).
  - `pf8-stoppage-workplace.png`: W's panel with "Pays", "Out at the gate", its measures and "This period's work
    paid the owners"; `pf8-stoppage-household.png`: H's panel with "Weighed a stoppage at {W}" "stops", the three
    conditions and the money it weighed; `pf8-stoppage-people.png`: H's persons out clustered at W's gate.
  - `pf8-offer.png`: W's panel with "Struck work offered" (hours, rate, period O + 1) and the owners' count line
    "It has cost the owners ... of a year's ...: they offer ... hours of struck work". An owner's loss of a period
    is shared among its struck workplaces by what each had been paying it (a rule of the small worlds' Task 8), so
    the owners of a place do not give way everywhere at once, and struck work is offered at the workplaces that
    hold out. If no struck work is offered at W in 60 periods, the test says so and the lead decides the script:
    the five rules of the closest form on from period 1 (`{"rule":..}` after `{"fight":"on"}`, before the first
    step), or the harvest failed in one place only.
  - `pf8-end.png`: the first line ends "· ended at period {p}: ..." with p the record's `ended.0` (E, or E - 1
    for a `WentBack` end, which is recorded a period late), and the news says how ("the owners gave way:
    it pays ... an hour", or "places taken", or "went back"); after a win, W's "Pays" row reads "from period
    {E + 1}" in the next capture's report.
  - `pf8-*.json`: `fight` holds exactly the lines of the captures; `rules` is `[["seeking_in_place", 1]]`; no line
    anywhere names a household that took struck work with a word of `REFUSED_WORDS`.
  - Then the lead looks at the window as a player would, and compares it with the design's "What the player
    sees"; sizes, colours and the gate's place are the lead's to tune (`GATE_BELOW`, the tab's text sizes).
- [ ] **Step 6: Run the companion's gate. Commit** `feat(client): the stoppage and both counts on screen, with
  Part One's proof` (body: `Part of PER-371`).

**What this task must not do:** run the proof script; open a window in a test; print a count that is not a
`StopAccounts`, `EmployerDecision` or `Stoppage` field; call a stoppage anything but a stoppage; use a word of
`REFUSED_WORDS`; change a frame of a world with no fight (`a_world_with_no_fight_draws_as_before`).

---

### Task 9: The counted runs: the later slump with the fight and no organization, and with rises offered at once

Commit `test(material-circuit): the later slump counted with the pay fight`.

**Files:**
- Modify: the bench's `runs.rs` (`Form` 7-23 gains `Fight` and `Offered`; `Form::rules` 39-56 their arm; `runs` 166-190
  asks for the fight when the form is either); `rows.rs` (a counter of its own, beside `rows_and_digests`); `sets.rs`
  (the long test). The record `reports/economy-repair-2026-11-20/pay-fight/count-1.md` is the lead's, not this task's.

**Interfaces:**

Consumes: everything of Part One: `World::with_fight`, `FightOpening`, `PeriodResult.fight`, `PeriodFight`'s
fields, `Stoppage`, `StoppageEnd`, `HouseholdDecision`, `StopChoice`, and in `receipts.orders` the receipts of
Tasks 3 to 5.

Produces:

```rust
// runs.rs
/// The closest form with the pay fight asked for and no organization. Not in `Form::ALL`: no `reproduces_` set
/// changes.
Form::Fight,                                   // rules: World::switches_at(scale).to_vec()
/// The same with `Employers::OfferAtOnce`: a measuring instrument of the bench, what rises that follow needs do.
/// Not in `Form::ALL`.
Form::Offered,                                 // rules: World::switches_at(scale).to_vec()
// runs(Form::Fight, scale): the 25 runs of `Form::Down`, each world `.with_fight(FightOpening {
//     organizations: Vec::new(), employers: Employers::ByTheirCount })`; runs(Form::Offered, scale): the same
//     with `employers: Employers::OfferAtOnce`
// rows.rs
/// What one run of the fight did, read from its records only (`PeriodFight` and receipts).
/// One field for each column of the table below, and `stopped: Vec<String>`, `took: Vec<String>`: the lines of the
/// two blocks, already worded. `line()` writes only the table.
pub(crate) struct FightCount { /* .. */ }
pub(crate) fn fight_count(run: &BenchRun, absent: &BenchRun, periods: u64) -> FightCount;
impl FightCount { pub(crate) fn line(&self) -> String; pub(crate) const HEADER: &'static str; }
// sets.rs
#[test] #[ignore = "200 runs of 400 periods: fight and offered, each with its absent twin; run in the background"]
fn fight_counts_the_later_slump();
```

`fight_count` opens both runs with `Runner::open_world` and strikes as `rows_and_digests` does
(`TurnedOn::AtOpening`), steps each `periods` times, and panics on a refusal with the run's name, the scale and the
period. It does not call `rows::rows`: the row writer's `account_name` refuses an organization account
(rows.rs:44-58), and the fight run's book holds 16. A taker or a striker is named by `Household::label()`.

**The columns, one line for each of the 25 runs at each figures (50 lines), tab-separated:**

| Column | Read from |
| --- | --- |
| `run`, `scale` | the run's name; `Small` or `National` |
| `stoppages` | distinct `(workplace, began)` of every `PeriodFight.stoppages` over the run |
| `stoppages_utility`, `_farm`, `_clinic`, `_shop` | the same, by `workplace.kind` |
| `steps_max` | the largest `ask.steps` of a stoppage begun in the run (`-` when none) |
| `periods_out` | the sum, over the run's stoppages, of their `periods` (each a period with hours withheld) |
| `households_stopped` | distinct households of a `HouseholdDecision::Stop` with `choice: Stop` |
| `gave_way`, `went_back`, `places_taken_ends` | stoppages by `ended`'s `StoppageEnd` at the run's end; `open` those with `ended: None` |
| `rises_won`, `rise_micro` | `RateReceipt`s (in `receipts.orders`) with `new_rate > old_rate`; the sum of `new_rate - old_rate` |
| `takers`, `places_taken` | distinct payees of `AboveRollsReceipt`s with `cause: StruckWork` and `attended_hours > 0`; the sum of `moved` of `StaffingOrderReceipt`s with `kind: PlaceTaken` (never `order.persons`) |
| `rises_unpaid`, `rises_held` | Review Focus 1: rises whose site has, in the same period, a `LaborUseReceipt` with `unfunded_hours > 0`; an `AdjustmentReceipt::Stop` with `hold: Held` |
| `clock_1`, `clock_200`, `clock_400` | the sum of `summary.hours_attended` at periods 1, 200 and 400 of the fight run |
| `absent_200`, `absent_400` | the same of the `Form::Down` run of the same name and figures |
| `low_clock`, `low_period` | the lowest sum of `summary.hours_attended` over the fight run, and its first period |
| `back_400_per_100` | `clock_400 * 100 / clock_1` (whole); `absent_back_400_per_100` the same of the absent run |
| `first_stoppage`, `last_end` | the period of the first stoppage begun; the last `ended` period (`-` when none) |

After the table, two blocks for the lead, each line naming its run and scale: `stopped <run> <scale> <period>
<workplace> <household>:<persons> ...` for every stoppage begun (from `Stoppage.began` and its first `out`), and
`took <run> <scale> <period> <taker> at <host> <persons> from <household>:<persons> ...` for every
`StaffingOrderReceipt` (its `household_id`, `order.host_pool`, `moved` and `displaced` by member, each member
named by its household).

**The second table, `Form::Offered`**, one line for each of the same 25 runs at each figures, after the first
table and its blocks, under its own header: `run`, `scale`, `rises_won`, `rise_micro`, `rises_unpaid`,
`rises_held`, `clock_1`, `clock_200`, `clock_400`, `absent_200`, `absent_400`, `low_clock`, `low_period`,
`back_400_per_100`, `absent_back_400_per_100`, and `steps_max` as the largest steps offered (from the
`RateReceipt`s: `(new_rate - old_rate)` over the workplace's `pay_step`, the most of the run). Each column reads
as in the first table. The same `fight_count` gives it; the stoppage columns, which are 0 there, are left out.

**What it asserts** (and only this): every step of every run is `Ok` (the runner refuses money or people not
conserved, and any refusal of the orders); every `PeriodFight.orders_digest` equals
`period_orders_digest(&orders)`; for `Form::Fight` only, every `RateReceipt` follows a `GaveWay` of the close
before at its site; `Form::ALL` contains neither `Form::Fight` nor `Form::Offered`. **What it only prints:** everything
in the table and the two blocks,
for the lead to read with the Director. The 14 `reproduces_` sets are proved untouched by the gate, not by this
test.

- [ ] **Step 1: Write the failing test** in `sets.rs`: `fight_counts_the_later_slump`, `#[ignore]`, not named
  `reproduces_` so the long tests' filter does not take it. For `scale` in `[Scale::Small, Scale::National]`, zip
  `runs::runs(Form::Fight, scale)` with `runs::runs(Form::Down, scale)` (same order, same names: assert it),
  `println!` the header once and `fight_count(fight, absent, PERIODS_LONG).line()` for each, then the two blocks;
  then the same for `runs::runs(Form::Offered, scale)` under the second header. Also a quick test
  `the_fight_form_is_down_with_the_fight`: for both scales, each `Form::Fight` run's world equals its `Form::Down`
  twin's with `fight: Fight::Asked(FightOpening { organizations: vec![], employers: Employers::ByTheirCount })`,
  each `Form::Offered` run's the same with `Employers::OfferAtOnce`, and `Form::ALL` contains neither.
- [ ] **Step 2: Run the quick test and see it fail:** `mise run rust:test:q -- -p babylon-material-circuit --test
  adjustment_bench -E 'test(the_fight_form_is_down_with_the_fight)'`. Expected: does not compile (no
  `Form::Fight`, no `fight_count`).
- [ ] **Step 3: Implement** `Form::Fight`, `Form::Offered` and their arm in `runs.rs`, and `FightCount`,
  `fight_count` in `rows.rs`.
- [ ] **Step 4: Run the quick test and see it pass:** the command of Step 2. Then, in the background:

  ```sh
  cd /media/user/dev-ssd/worktrees/households-homes/babylon/rust && mise run rust:test:q -- -p \
    babylon-material-circuit --test adjustment_bench -E 'test(fight_counts_the_later_slump)' --run-ignored only \
    --no-capture > "$SCRATCH/fight-count.log" 2>&1; echo "END fight-count status=$?" >> "$SCRATCH/fight-count.log"
  ```

  It steps 200 runs of 400 periods (`fight_count` steps a run and its absent twin, for the fight's table and for
  the offered one, 25 of each at both figures), about the time of eight `reproduces_` sets; note the time in the
  report. A failure names the run, the scale and the period: stop and report it, do not mend it here.
- [ ] **Run the gate:** the small worlds' gate; then the 14 long tests in the background: 25 of 25 in each set.
- [ ] **Commit** the subject above, without the log. The body says: the closest form with the fight asked for and
  no organization, and with rises offered at once (the bench's instrument), as forms outside `Form::ALL`; the
  count of the 25 runs at both figures over 400 periods, from
  `PeriodFight` and receipts only, against the same runs with the fight absent; Review Focus 1 counted; what it
  asserts and that the rest is printed for the lead. Ends with `Part of PER-371` and the `Co-Authored-By` line.
  Hand the log's table and blocks to the lead; the lead writes `count-1.md` and reads it with the Director before
  Part Two is detailed.

**What this task must not do:**
- Add `Form::Fight` or `Form::Offered` to `Form::ALL`, or change any form, fixture, digest or `reproduces_` test.
- Judge the count: no assertion on how many stoppages, wins or hours there are.
- Read a figure from a picture or from the design's sketch.

---

## Part Two (the design's build-order items 8 to 16), one line each

Detailed after the count of Task 9 is read with the Director.

- **P2-1** Organizations as actors in step 2, yours (pay, invite, call, withdraw, negotiate, take up),
  `YoursCommand` and `Runner::command`, the event and its forecast, with its scene piece (the event's buttons).
  The scene's world then opens yours with its labelled fund, and the scene reads organizations and their money
  (the section after this list).
  Consumes `FightBook`, `decide`, `FundPaymentOrder`, `WageShareOrder`, `PaymentRecord`, `weigh_stop`
  (`Ground::Called`), `EmployerCount`, `Line::Yours`.
- **P2-2** Membership PF8 (`weigh_membership`), ties and the record, the hatched ring; a member's own
  dues, paid at the close from what is left after it has bought (one more act of the engine). Consumes `Organization`,
  `Membership`, `PaymentRecord`, `responds_to_own_amounts`.
- **P2-3** Founding PF18 (`FundInMaking`, `weigh_paying_in`, the refund), its four tests, the thinner ring.
  Consumes `OrganizationStanding::Kept`, `FOUNDING_ACCOUNTS_PER_WORKPLACE`, `WageShareOrder`, `FundPaymentOrder`,
  `FundPaymentKind::{PayingIn, Refund}`, `Stoppage`.
- **P2-4** The contract, its calendar and terms (pay follows prices, dues collected), bargaining's event; the
  benefit of people whose places were taken, held back while their stoppage lasts (PF13, design call 45).
  Consumes `RateOrder`, `Term`, `Ask`, `fewest_steps`, `needs_cost`, `WageShareOrder`.
- **P2-5** The demand for work: named people above the rolls then taken on, the floor and its yielding, idle
  hours paid, the same demand's weighing. Consumes `AboveRollsCause::Named`, `StaffingOrderKind::TakenOn`,
  `FloorOrder`, `FloorReceipt`, `StopAccounts`.
- **P2-6** A union present by A16, a union moving in by rank under its fund, "ask me". Consumes P2-1,
  `employer_decides`'s arithmetic for the union's test, `weigh_struck_work` for "nobody would take the places".
- **P2-7** The payer PF17: the employer's six periods, the buyers, the hours ledger over two spans, the line
  under a win. Consumes `PeriodResult.hours` (section 6), `Stoppage.ended`, `take_of`, receipts.
- **P2-8** The three counted comparisons on 400 periods at both figures, the lead's look, the Director's
  page. Consumes Task 9's harness.
- **P2-9** A15 behind its own switch (`RateOrder` with the employer's own cause), measured again. Consumes
  `RateOrder`, `Measure::PayCut`, `Measure::HandsShort`.

## For Part Two's first task (P2-1): organizations and their money on screen

Part One's scene opens no organization, so nothing can order a payment and nothing below can be reached from the
screen before P2-1 brings "yours", its fund and the commands that use them. These pieces were written for Part One
and moved here whole; P2-1's detailer writes their steps.

Interfaces:
```rust
// C/reading.rs
pub enum Party { Workplace(Workplace), Household(Household), Treasury, Fund, Organization(OrganizationId) }
// Party::from_account: AccountId::Organization(id) is Party::Organization(OrganizationId(s)) for the index s
// (from 0, while OrganizationSlot::new(s) is Ok) whose organization_account(OrganizationSlot::new(s)?) is id;
// None for any other organization account. Party::Organization(id).label() is "Organization {id.0}".
pub enum PaymentKind { Wages, Purchases, Taxes, Benefits, Profit, Capital,
    /// A payment to or from an organization's fund (`CashTransferPurpose::MutualAid`): dues, paying in, strike
    /// pay, relief, a refund.
    MutualAid }
// PaymentKind::ALL: [PaymentKind; 7]; label "mutual aid"; read_payments reads Cash(MutualAid) through cash_of;
// HouseholdTransfer and TransportService stay refused; a_receipt_of_no_party_is_refused stays as it is (its
// mutual-aid wage transfer still debits a payroll reserve).
// C/frame.rs: STREAM_MONEY: [u16; 7] = [4, 5, 6, 7, 8, 9, 10]; payment_stream(MutualAid) = STREAM_MONEY[6];
// party_id(Party::Organization(id)) = "organization:{id.0}"; Standing::point(Organization(id)) = organization_at(id);
// the_styles_name_the_plans_units: 10 streams become 11 (the one pin named in Global Constraints).
// C/layout.rs
/// Where a payment to or from an organization's fund starts or ends. Starting value; the lead's to tune.
pub const ORGANIZATION_AT: Point = (0.0, 11.2);
/// Every organization at `ORGANIZATION_AT` until an organization is drawn as a ring.
#[must_use] pub fn organization_at(id: OrganizationId) -> Point;
// Arms for Party::Organization: inspect::account_of -> AccountId::Organization(organization_account(..));
// inspect::inspect -> Err(missing("an organization is not a body of the scene")); marks::rule_rows (two no-op
// arms); table::row -> false (and hours_table's match); controls::body_extent -> CORE_EXTENT; reading's test
// closure place_of -> None. panel::not_drawn_line appends ", mutual aid {..}" only when that stream holds some.
// C/fight.rs
/// "Yours", "A union", "A local", "Another organization".
#[must_use] pub const fn line_words(line: Line) -> &'static str;
/// "Dues", "Paid in", "Strike pay", "Relief", "Paid back".
#[must_use] pub const fn payment_words(kind: FundPaymentKind) -> &'static str;
/// The Fight tab's rows of organizations and payments of one period; empty for a period with no fight. Drawn in
/// `FightBody` before `stoppage_rows` and `news_rows`, and carried first by `ScriptReport.fight`.
#[must_use] pub fn fight_rows(result: &PeriodResult) -> Vec<String>;
```

Words of `fight_rows`, in order: for each `(organization, cash)` of `PeriodFight.organizations` whose `standing`
is not `Kept`: `"{line_words(line)}: a fund of {currency(cash)} at the close"` and `"{line_words(line)}:
{grouped(members.len())} member households"`; for each `PaymentRecord` of `PeriodFight.payments`:
`"{payment_words(kind)}: {currency(amount)} between {line_words(its organization's line)} and {household.label()}"`.
`stoppage_rows` gains, last for each stoppage, for each `PaymentRecord` of the last `StoppagePeriod`'s `paid`:
`"{payment_words(kind)}: {amount} to {h}"`.

What is drawn: a mutual-aid payment is a gold streak on `STREAM_MONEY[6]` (`Glyph::Streak`) from
`organization_at(id)` to the household's point or back. It leans no household (`layout::anchor` answers `None`).
An organization's account is in no row of the table. No body, ring or label is spawned for an organization until
its ring is designed.

Tests written for these pieces (in Part One's form, kept for P2-1): `an_organization_account_is_a_party`
(reading.rs: slots 0, 1 and 16 read as `Party::Organization`; an organization account of `[7; 32]` reads `None`;
the label); `a_payment_to_or_from_a_fund_is_read_as_mutual_aid` (reading.rs: two profit transfers of a fight period
made into strike pay from yours' fund and dues into it; two mutual-aid payments, payer and payee the organization;
`ALL` has 7; the label); `a_mutual_aid_payment_draws_on_its_own_stream` (frame.rs: one flow on `STREAM_MONEY[6]`
for each payment, amounts equal, ends at `ORGANIZATION_AT`, households where they stood); `every_fight_row_is_a_
record_s` (fight.rs: each organization's cash equal to the closing book's, its two lines on the tab, a planted
`PaymentRecord`'s line, the five payment words, no rows without a fight).

## Calls of the lead

Numbered as the tasks cite them.

1. A step of pay is $1 an hour at the small figures and 250 basis points of the workplace's opening wage at the
   national figures (`pay_step`). Designed (design call 38).
2. Where several households stop on asks of their own, the workplace's ask is the largest of them (design call
   37).
3. Payments to and from a fund reach the screen in Part Two's first task. Part One adds no command of yours.
4. The labelled figures of the scene (yours' fund, strike pay, the share of dues, a contract's length) are Part
   Two's. `World::scene_with_fight()` opens no organization (design call 43).
5. A household's cost of a struck period is never below 0.
6. PF6's "what it has without it": money held; the benefit drawn in the period just closed; relief committed for
   the next period; its other people's pay at full work.
7. Measure (d)'s "growing": this period's take from that workplace above the last period's.
8. A struck place is taken at the close of the period in which the struck work was taken up, whether or not the
   workplace could pay its hours (PF13; design call 46).
9. The button that brings a shock reads "Apply" (design call 40). `SceneCommand::Strike` and
   `ShockButton::Strike` become `Apply`; the script's `strike` key and `Runner::strike` keep their names.
10. Measure (a) is one person's, at full work, and reads so on screen: "$80.00 against $91.00 a person" (design
    call 41). Ruled so by the Director (F12).
11. The workplace's own laid off may take its struck work when their household's people at work there did not
    stop (design call 42). So one slot may be both ends of a staffing order.
12. The orders of a period are bound by a digest of their own. Nothing of them is stored before the bridge.
13. The first period of a won rate is paid from the money the workplace has (design call 35; Review Focus 1). Part
    One pins what happens and counts it in Task 9. It mends nothing.
14. Task 6c is built after Task 8. The live database tests are the lead's (Global Constraints).
15. One employer has one loss (design call 44). Where several of its workplaces are struck in one period, the
    period's cost is shared among them by what each had been paying it; a workplace struck alone takes the whole.
    On this bench the people of a whole place walk out together, so without this one loss would win three fights.
    Ruled so by the Director (F11).
16. Orders about people are carried out on what the close leaves (design call 46): an order moves at most the
    reserve that is still there and displaces at most the people still out, and its receipt says what moved. An
    order is refused only where it passes what its orderer saw at the opening.
17. A person whose place is taken is laid off at that close and covered from the next period (design call 45).
    Where the rest of the stoppage goes on, the law would hold that benefit back; Part Two builds that delay.
    Ruled so by the Director (F13).
18. Task 9 counts a second run that is no rule of the game (design call 47): `Employers::OfferAtOnce`, where what
    the people of a workplace would ask is offered at once. It tells whether rises that follow needs end the later
    slump, even if few stoppages win. It is never reachable from the scene.

### Confirmed for the engine's tasks

- Task 1: until Task 2, `place_error`'s arm for `PlaceStaffingError::Order(_)` is
  `engine_error(.., Stage::StaffInPlaces, MarketClearingInvariant)` (the runner gives no orders before Task 2).
- Task 1: `period_orders_digest` refuses orders out of key order (`NotCanonical`) rather than sorting them.
- Task 1: receipts stand in `transition.orders` in the order they acted: rates, fund payments, withheld, above
  the rolls, wage shares (the close), then floors and staffing orders (the staffing); each kind in key order.
- Task 1: validation's `NotMonetary` is read only for orders that are not empty.
- Task 3: the hosts' reading of the new rate is pinned through the closed state's employment rows only (no
  public view shows the hosts' order).
- Task 4: the restart's count is skipped only at a site with `withheld_hours > 0` (a withheld order on a member
  with nobody on its rolls does not stop the count).
- Task 4: struck persons are withheld hours over hours a person, rounded down.
- Task 5: an above-rolls order of 0 hours and a staffing order of 0 persons are `NotCanonical`.
- Task 5: `MoveOutOfPlace` also covers members not of their pools, members of two households, and two
  different members of one pool.
- Task 5: one slot may be both ends of a staffing order: the persons are called back from its own reserve, the
  newest laid off first.
- Task 5: `AboveRollsReceipt.attended_hours` is the hours attended above the rolls,
  `attended.saturating_sub(capacity - withheld).min(hours)`.
- Task 5: an above-rolls order on a member with hours on the rolls, whose payee withholds nothing there, is
  accepted; its offered hours are its rolls' hours less any withheld plus those above.
- Task 5: displaced strikers are not offered to another host in the same close.
- Task 5: staffing orders are applied to what the close leaves; only what contradicts the opening is refused.
- Task 5: a person whose place is taken is laid off at that close and covered from the next period (design call
  46: where the rest of the stoppage goes on, the law would hold that benefit back until it ends; Part Two
  builds that delay).
- Task 5: the record of layoffs dates every person an order moves: the displaced from this close, the called
  back from the newest cohorts, the taken on drawing down no cohort where they arrive; no refusal is added for a
  state a run can reach.
- Task 1: a share of wages is taken when wages are paid (paying into a fund in the making, dues an employer
  collects); a member's own dues at the close are an act of Part Two.
- Task 1: runs the 14 long tests at its end.

### Confirmed for the small worlds' tasks

- Task 2: `scene_with_fight()` opens no organization; "yours" and its fund come with P2-1.
- Task 2: kept accounts are recorded as `Line::Founded` with `OrganizationStanding::Kept`; at most 88 organization
  accounts (72 asked beside the 16 kept).
- Task 6: measure (a) is one person's at full work: `net(rate * hours_per_person)` against the household's needs
  over its persons; layoffs are measure (d)'s.
- Task 6: measure (b) holds in the period of a lowering `RateReceipt` only (P2-9 measures it again).
- Task 6: measure (c)'s hours filled are the `next_opening_hours` of the pool's member receipts.
- Task 7: a household's amounts (pay, cost, a year of the ask, struck pay) are net of the tax to come; the
  employer's are gross.
- Task 7: a taker does not count its benefit in what it would have with the struck work (PF13); the engine still
  pays it in that first period (Review Focus 3, pinned as it is).
- Task 8: `pay_elsewhere` is its pay at full work at its other workplaces as of the last close; PF6's `other_pay`
  leaves out the workplaces where its own decision of the step is `Stop`.
- Task 8: an employer that never gives way (`NeverPaid`) still offers struck work from the period after.
- Task 8: when more come than there are struck places, the places are shared over the takers' persons by largest
  remainders, `Household::ALL` order on ties.
- Task 8: a stoppage with no striker left on the rolls ends `PlacesTaken` if a place was taken in it, else
  `WentBack`; `ended` names the last period with hours withheld.
- Task 8: the taker's member at the struck workplace is its own member there when that is its home, else the pair
  member; its slot at the struck pool itself is ordered with `from_pool == host_pool` and `from_member ==
  to_member`, and the workplace's own laid off may take its struck work.
- Task 8 and Task 9: `out`, `filled`, `Stopped.out` and `StruckWorkTaken.by` are persons by household;
  `filled` reads `AboveRollsReceipt.attended_hours`, the hours above the rolls.
- Task 9: "work comes back" is printed as hours on the clock at 400 per hundred of period 1, beside the absent
  run's, and is not judged by the test.
- Task 8: a place counts as taken at the close of the period in which the struck work was taken up, whether or not
  the workplace could pay its hours.
- Task 8: a taker whose share of the struck places is 0 gets no order; its `TakeDecision` stays `Take`.
- Task 8: one employer has one loss a period, shared among its struck workplaces in proportion to what each had
  been paying it (by `asked_year` where none paid it), and taken whole by a workplace struck alone.
- Task 8: the workplace's ask a household weighs once a stoppage is open equals its own in the small worlds; the
  bridge must say how a household weighs an ask formed from another's.
- Task 2 and Task 9: `Employers::OfferAtOnce` is a labelled figure of the bench, never of the scene, and no rule of
  the game.
- Task 2: `organizations` of `PeriodFight` lists the 16 kept accounts, which the scene does not draw; `payments` is
  empty in Part One.

### Confirmed for the scene's tasks

- 2c: "Start over" leaves the fight (as it clears rules and shocks); the switch's press always starts over with it.
- 3c, 4c, 5c, 6c, 8c: the fight's rows of the panel (rate, gate, struck work, measures, weighing) show only in a
  fight world.
- 4c: in the groups view a household with persons out at a workplace takes that workplace's gate for its home;
  `GATE_BELOW = 1.2` below the workplace is a starting value; the lead's to tune.
- 4c: the script's `{"strike":..}` key and `ScriptCommand::Strike` keep their names.
- 5c: a taker's persons above the rolls are its hours above the rolls over the host member's `hours_per_person`,
  rounded up.
- 6c: `Measure::PayShort`'s `pay` and `needs` are one person's at full work (the sketch's $80 and $91);
  `PayCut`'s `from` and `to` print with no unit word.
- 8c: the Fight tab's caption counts stoppages under way as "Fight · {n} stopped".
- 8c: `ScriptReport.fight` carries the Fight tab's lines of the last period, so the lead checks the proof by text.
- 8c: the proof stays as written (the fight on, the harvest failed in both places until lifted, 60 periods). Most
  workplaces of both places are expected to stop at about period 20, and an owner's loss is shared among its struck
  workplaces (the small worlds' Task 8), so struck work is offered where owners hold out. If none is offered at W in
  60 periods, the lead decides the script: the five rules of the closest form on from period 1, or the harvest
  failed in one place only.
- 2c: if the Paint chain already holds 20 systems, `(rules::paint_rules, fight::paint_fight)` is one element of it.
- P2-1 (moved, decided as written): an organization's label "Organization {slot}"; names by line; one point
  `ORGANIZATION_AT` for every organization; a mutual-aid payment leans no household; an organization's account in
  no table row; kept accounts not listed.

## What changed from the first architecture

The first architecture was a working paper of 24 November and is not in the repository. Everything below is
already in this plan's File Structure and tasks; the list says what the detailing changed and why, for a reviewer.

### The engine

1. **The base of a share of wages.** Point 6 of The engine's orders reads `base =
   costs.tax_base(Household(payer), WageIncome)` after `costs.admit_attendance`. At that point it is 0: wage
   income enters the cost book only in `costs.payroll` (`E/valuation/close.rs:704-724`), called from
   `close_household_reproduction` (`E/transition/state.rs:1541`), after the purchases. Task 1 reads the base
   from the period's `wage_accruals` to the payer (pushed by `fund_attendance`, `E/payments/attendance.rs:381-383`)
   and taxes it with the payer's `WageIncome` rows as `collect_taxes` does. No signature changes;
   `take_wage_shares` takes `wage_accruals: &[WageAccrualReceipt]`.
2. **`FloorOrder` carries its site and unit.** The close has no pool bindings (`staffing_requests` takes them
   from the caller, `state.rs:664-668`; `fund_attendance` knows only employment rows), so `paid_hours` cannot
   be keyed by pool in the attendance. New form: `pub struct FloorOrder { pub pool_id: StaffingPoolId, pub
   site_id: SiteId, pub unit_id: UnitId, pub persons: u64, pub paid_hours: u64 }` (key still `pool_id`; the
   digest's row gains the two ids), and `PeriodOrderError::FloorNotThePool { pool_id: StaffingPoolId,
   site_id: SiteId }` when the pool's binding is of another site (checked at the staffing).
3. **`PeriodOrderError::WageShareOutOfRange { payer: FinalDemandPrincipalId, share_bps: u16 }`.**
   `ShareOutOfRange` names a staffing member; a share of wages has none.
4. **The staffing orders' checks that read the staffing** (`MoveFromNoReserve`, `MoveOutOfPlace`,
   `DisplacesMoreThanStruck`, `FloorNotThePool`) cannot run "first, in `close_with_rules`": the close has no
   `StaffingState` or pool members. They run in `staff_in_places` and come back as `PlaceStaffingError::Order`.
   The checks that read only the opening state run in the close's validation.
5. **"The site's labor row keeps the rolls' hours" is true of the member rows only.** `fund_attendance` sets
   each site's labor row of the period to its attended hours (`E/payments/attendance.rs:349`); the member rows
   (`economy.member_labor`) are what keep the rolls' hours through the close (`E/adjustment/rest.rs:13-17`).
   No interface changes; Task 4's tests read the member rows and the next period's rows.
6. **`ClosedMaterialPeriod.orders` is `Some` only when the orders are not empty**, so that a period closed with
   empty orders is the older entry's field for field (Task 1's test compares the two closed periods whole).
7. **`close_funded_production` takes an eighth parameter** under `#[allow(clippy::too_many_arguments, reason =
   ..)]`; `PlaceRules` (crate-private) also gains `striking: &BTreeSet<StaffingMemberId>` beside `floors` and
   `moves`; `PlaceStaffing` gains `pub(crate) order_receipts`. All crate-private.
8. **`advance_staffing_limited` gains `floors: &BTreeMap<SiteId, u64>`** (crate-private; the public
   `advance_staffing` is unchanged), so `advance_pool` can take the floor.
9. **A staffing order may name one slot as both ends.** `from_pool == host_pool` is accepted exactly when
   `from_member == to_member`: the persons are called back from that member's own reserve (Task 5, Step 6),
   newest laid off first, then the uncovered, as a call-back is (`advance_layoffs` step (d)); a move between
   pools stays uncovered first. `Slot` gains `called_back`.
10. **`AboveRollsReceipt.attended_hours` is the hours attended above the rolls**:
    `attended.saturating_sub(capacity - withheld).min(hours)` (Task 5, Step 4). `fund_member_attendance` pays
    one figure for the whole member row, so this reading (the rolls' hours first) is the exact definition the
    code allows.
11. **Orders are applied to what the close leaves.** An order is built at the opening and the engine's decision
    of the same close moves persons first, so a staffing order moves `min(persons, the reserve left, the room
    the stop rule's limit leaves at the host, counting those it displaces)`, and a place taken displaces
    `min(moved, those still out)`. New form: `pub struct StaffingOrderReceipt { pub period: u64, pub order:
    StaffingOrder, pub household_id: FinalDemandPrincipalId, pub moved: u64, pub displaced:
    Vec<(StaffingMemberId, u64)> }`; new `order_amounts(persons: u64, reserve: u64, room: Option<u64>, struck:
    Option<u64>) -> Result<(u64, u64), StaffingError>`. `MoveFromNoReserve` and `DisplacesMoreThanStruck` are
    read against the opening of the staffing (`PoolMembers`' `reserve()` and `employed()`), summed over the
    close's orders, before the engine's decision.
12. **The record of layoffs after staffing orders is carried in two steps.** `with_orders` is gone: one
    `StaffingMemberReceipt` cannot date displaced, called-back and taken-on persons together. The record is
    `advance_layoffs` of the unchanged `record_receipt(slot)`, then `after_orders(cohorts: &[u64], called_back:
    u64, displaced: u64, closing_reserve: u64) -> Result<Vec<u64>, MaterialCircuitError>`; the finish applies
    `apply_order_records(records: &mut Vec<LayoffRecord>, rows: &[OrderRecord]) -> Result<(),
    MaterialCircuitError>` from `PlaceStaffing.order_records` (crate-private).
13. **The people moved by orders are not in `PeriodResult.members`.** `member_receipts` stay the engine's
    decision; the persons after orders are in `PlaceStaffing.members`, and readers take the orders from the
    `StaffingOrderReceipt`s.

### The small worlds

1. **`PAY_STEP: Currency` cannot be a constant.** `Currency::from_micro_units` is not a `const fn`
   (`rust/crates/babylon-kernel/src/currency.rs:45`), and the national step depends on each workplace's opening
   wage (the clinic's is $11 under P4, `W/doubled/opening.rs:139-145`). New (Task 8, `W/fight/world.rs`):
   `pub const PAY_STEP_MICRO: i128 = 1_000_000; pub const NATIONAL_PAY_STEP_BPS: i128 = 250;`
   `#[must_use] pub fn pay_step(world: &World, workplace: Workplace) -> Currency;` with `doubled::opening::wage`
   made `pub(crate)`. They are Task 2's (Task 3c of the scene reads `pay_step`), with the test
   `a_step_of_pay_is_a_dollar_or_a_fortieth_of_the_wage`; Task 8 consumes them.
2. **`employer_decides` cannot tell `NeverPaid` nor fill `OfferStruckWork.hours` from its three arguments.** The
   count holds losses only, and a loss of 0 is the same whether the baseline was 0 or the owners lost nothing.
   New (`W/fight/employer.rs`): `pub fn employer_decides(count: &EmployerCount, period: u64, asked_year: Currency,
   baseline: Option<Currency>, withheld_hours: u64) -> Result<EmployerDecision, FightError>;`.
3. **`ClosedView` holds the closed period's `PeriodResult`, not its parts.** `measures`, `take_of` and
   `needs_cost` take `&PeriodResult` (`File Structure, "The small worlds' new modules"`), and the result is built
   after `read_closing` and before step 1 (`W/runner/run.rs:403-420`). New: `pub(crate) struct ClosedView<'a> {
   pub(crate) period: u64, pub(crate) result: &'a PeriodResult, pub(crate) history: &'a [PeriodResult],
   pub(crate) state: &'a MaterialCircuitState }`; `advance` builds `PeriodResult { .., fight: None }`, calls
   `close`, then sets `result.fight`. `DecideView` and `Decided` are written out in Task 2.
4. **`measures(result, before)` cannot set `Begins` for measure (d).** Whether the take grew in `before` needs the
   period before `before`. New: `pub fn measures(result: &PeriodResult, before: Option<&PeriodResult>, last:
   &[MeasureRow]) -> Result<Vec<MeasureRow>, FightError>;` (`last`: the rows of the last close, kept by the book).
5. **Measure (a) is one person's, at full work.** `PayShort { pay, needs }` is `net(rate * hours_per_person)`
   against `needs_cost(result, h) / persons` (Task 6, with the records named there), not the household's wages
   against its whole needs, so layoffs do not read as pay short and the ask does not grow with them; `own_ask`
   calls `fewest_steps(pay, needs, hours_per_person, bps, step)` with the member receipt's hours a person and the
   household's wage tax receipts' `rate_bps`. `StopAccounts` keep the household's own amounts.
6. **The taker's member and a slot at the struck pool.** The taker works through `w.member_id()` when `w` is its
   home, else `w.pair_member_id(home)`; a `StaffingOrder` may have `from_pool == host_pool` exactly when
   `from_member == to_member` (the engine's Task 5 accepts that and refuses the same pool with two members).
   `AboveRollsReceipt.attended_hours` are the hours attended above the member's rolls' hours.
7. **Units.** `StoppagePeriod.out`, `StoppagePeriod.filled`, `NewsItem::Stopped.out` and
   `NewsItem::StruckWorkTaken.by` are persons by household.
8. **Task 9's table gains `steps_max` and `periods_out`.**
9. **`OrganizationSlot(u8)` keeps its field private** with `pub fn new(index: usize) -> Result<Self, WorldError>`
   and `pub const fn index(self) -> usize`: `organization_account` is infallible, and byte 40 + slot must stay
   below 128 like every identity byte of the world (`W/ids.rs:71-78`); a public field would let a slot overflow
   into another identity.
10. **`File Structure, "Bytes that must not change"` misses one function in its row for `World`.** The engine
    refuses a book whose organization or public accounts lack an `InstitutionLocation`
    (`E/financial/validation.rs:64-74`), so `financial` (`W/doubled/opening.rs:490-509`) also adds the
    organizations' locations for `Asked`, in both worlds. For `Absent` it adds nothing, and the bytes are as that
    section says.
11. **`a_refused_period_keeps_the_book` is dropped.** A stopped runner never steps again (`W/runner/run.rs:191-215`,
    `Stopped`), so no test can see the book after a refusal, and no refusal after `decide` can be provoked from
    outside without a test hook, which Task 2 forbids. What it pinned is the shape: the book travels only in
    `Stepped` and `step` keeps it in the `Ok` arm only. The reviewer reads `step`.
12. **Task 8 does not touch `W/runner/run.rs`.** Task 2 composes `advance` (its tests need the orders entry in
    use); Task 8 fills `decide` and `close`.
13. **`World::scene_with_fight()` opens no organization in Part One.** The plan's "Calls of the lead", 4, puts every
    labelled figure of the scene in Part Two. Its fund and "yours" come with P2-1.
14. **Staffing orders are applied to what the close leaves.** `StaffingOrderReceipt` is `{ period, order,
    household_id, moved: u64, displaced: Vec<(StaffingMemberId, u64)> }` (the engine's Task 5: `moved = min(persons,
    the from slot's reserve now, the room under the stop rule's limit)`, a `PlaceTaken` displaces `min(moved, the
    striking slots' employed now)`, refused only past what the orderer saw at the opening). `decide` sizes orders
    from `view.members` and keeps to those two sums (a slot gives no more than its reserve at the opening, across
    every offer of the step); `close`, `PlacesTaken.persons`, `StoppagePeriod` and Task 9 read `moved` and
    `displaced`, never `order.persons`; a striker left on the rolls is its member's `closing_employed` in
    `result.members` (the engine's decision before any order) less what the period's receipts displaced from it.
15. **One employer has one loss a period** (PF7's new sentence, call 44). New in `W/fight/counts.rs`:
    `pub fn own_takes(history: &[PeriodResult], employer: Household, struck: &[Workplace]) ->
    Result<Option<(Currency, Vec<(Workplace, Currency)>)>, FightError>;` and `pub fn loss_shares(loss: Currency,
    struck: &[(Workplace, Currency, Currency)]) -> Result<Vec<(Workplace, Currency)>, FightError>;`. `close` step 3
    reckons the loss once per employer and shares it; `employer_decides` is unchanged.
16. **How the employers answer, an opening choice.** `FightOpening { pub organizations: Vec<OrganizationOpening>,
    pub employers: Employers }` with `pub enum Employers { ByTheirCount, OfferAtOnce }` (Task 2); `FightBook` keeps it
    as `rule`; under `OfferAtOnce` `decide` (b) orders the largest own ask at once (Task 8), and Task 9 counts it as
    `Form::Offered`, outside `Form::ALL`.
17. **`own_ask` gives an open stoppage's ask only while the household's own measure (a) or (b) holds**; else
    `Ground::Nothing` and it goes back (PF5 1).
18. **Task 6's `a_measure_starts_nothing` is rewritten in Task 8** as `a_measure_alone_orders_nothing`.

### The scene

1. **Part One's scene has no organization.** `World::scene_with_fight()` opens none; its book holds 16 kept
   organization accounts with no cash. No client path meets them (Task 2c says where), so `Party` is unchanged in
   Part One, and `PaymentKind::MutualAid`, the seventh money stream, `organization_at`, `line_words`,
   `payment_words`, `fight_rows` and the `paid` line of `stoppage_rows` move to P2-1 (section above). The styles
   stay ten streams in Part One.
2. **The pin of the rail's bodies.** `C/scene_tests.rs:1195` (`the_rail_has_the_rules_tab_only_for_rules_shown`)
   pins `count_of::<LowerBody>(&mut app) == 2`. The Fight tab is a third `LowerBody`, so the pin becomes `3`
   (Task 2c). Global Constraints name only the count of streams and styles as a pin that moves. The `NoticeLine`
   pin (1196) stays because the Fight tab has none.
3. **`inspect::rate_rows(result, w)` becomes `inspect::rate_rows(history: &[PeriodResult], index: usize, w:
   Workplace) -> Result<Rows, FrameError>`** (Task 3c). "from period N" needs the last rate receipt, which a
   single `PeriodResult` does not hold once the change is older than the period shown; the client reads history
   as `marks::held_since` (marks.rs:279) does. A `PeriodResult` holds no employment rows of the state, so the rate
   is read from `MemberLaborUseReceipt.compensation` (payments/attendance.rs:68).
4. **`open_runner()` cannot open the fight's world** (stored hours' Task 5 gives it no argument). Task 2c adds
   `scene::open_runner_of(world: &World) -> Result<Runner, RunnerError>`; `open_runner()` calls it with
   `World::scene()`.
5. **The test name `the_proof_script_of_task_8c_parses` exists** (`C/script_tests.rs:451`, the closest form's
   `PROOF_8C`). Task 8c's test is `the_proof_script_of_the_pay_fight_parses`; the script stays `PROOF_PF8`.
6. **Call 23's word.** File Structure, "The scene", said "Bring the shock"; the plan's "Calls of the lead", 9, and
   design call 40 say "Apply". Task 4c writes "Apply", and renames `SceneCommand::Strike` to `SceneCommand::Apply`
   and `ShockButton::Strike` to `ShockButton::Apply`: every use is in the scene's own files.
7. **The offer's row moves from Task 5c to Task 8c.** `PeriodFight.offered` comes with Task 8, after 5c; 5c's
   `struck_rows` reads only the engine's receipts, and 8c adds the "Struck work offered" row and its test.
8. **Persons, not hours.** `StoppagePeriod.filled` and `NewsItem::StruckWorkTaken.by` are persons, as `out` is;
   their words say "people". `AboveRollsReceipt.attended_hours` is the hours above the rolls, which the struck
   workplace's and the taker's rows print as hours.
9. **One range a member.** A member that takes struck work where it already has persons on the rolls is one range
   of `person_ranges`, employed persons and then persons above the rolls; a staffing receipt with one member as
   both ends reads "Called back" (Task 5c, two tests).
10. **`PAY_STEP` is `fight::pay_step(world, workplace)`** in every test that needs a step of pay (Tasks 3c, 6c).
11. **Return types left open before:** `fight::struck_rows` and `inspect::measure_rows` return
    `Result<Vec<(String, String)>, FrameError>`; `fight::stoppage_rows(result) -> Result<Vec<String>,
    FrameError>`; `fight::news_rows(result) -> Vec<String>`; `frame::at_the_gate(result) ->
    Result<BTreeMap<(Household, Workplace), usize>, FrameError>`; `inspect::weighing_rows(result, h) ->
    Vec<(String, String)>`.

12. **The fight world's frames are pinned** (`FIGHT_FRAMES`, Task 4c, written before any other edit of 4c and
    unchanged by 4c, 5c, 6c and 8c). Comparing a period with its own copy stripped of orders could not fail: no
    order comes in twelve periods.
13. **A staffing receipt carries `moved`.** "Places taken", "Took places at" and "Called back" read `moved`, not
    `order.persons`; a receipt with `moved: 0` gives no row. `PeriodResult.members` is the decision before any
    move, so moved people are read from receipts only.
14. **`PeriodFight.organizations` is not empty in Part One:** it lists the 16 kept accounts (`Line::Founded`,
    `Kept`, no cash), which the scene does not draw; no test asserts it empty.
15. **The proof's periods** (Task 8c): the header line carries " · ended at period {p}: .." whenever the record
    holds an end, also at the close the stoppage began; O is the first offer at W; E is the first period whose
    record shows the stoppage ended (a `WentBack` end is recorded a period late); the slots are six, filled with four
    figures and two ids.
16. **`the_report_carries_the_fight` steps to the first period with news** and asserts that the lines are not
    empty; a period-1 report holds none.
17. **Words:** a measure row of a household reads "{label} ({h.label()})"; the `NeverPaid` line reads "Its owners
    were paid nothing by their workplaces in the periods counted: a stoppage costs them nothing"; the gate's
    household rows are one for each workplace where it has persons out.
18. **`Currency`'s checked sums** fail with `CurrencyOverflow`, which has no `Error`: every test writes
    `.map_err(|e| format!("{e:?}"))?`.

## Checked against the code (commit 98a0e3624)

### The engine

1. `close_with_rules` (state.rs:1921-2078) is reached by the portfolios entry and the standing entry, which pass
   `None`/`Some(standing)`; the portfolios entry refuses a catalog that asks for the stop rule (1877-1879).
2. The transition literal is built once, at state.rs:2014; no other crate builds `MaterialCircuitTransition`
   (`git grep 'MaterialCircuitTransition {'`).
3. In `close_funded_production` (1641-1700): `settle_deliveries`, `retire_resolved_purchases`,
   `FinancialClose::opening` (1653), `fund_attendance` (1654), `admit_attendance`, then `HouseholdLists::open`.
4. `FinancialClose::opening` pays contributions then public funding (financial/close.rs:62-78); taxes come in
   `close_household_finance` after the purchases (state.rs:1727).
5. Wage income reaches the cost statement only in `costs.payroll` (valuation/close.rs:704-724, from
   state.rs:1541), so `tax_base` is 0 right after the attendance.
6. `fund_attendance` (attendance.rs:277-360): `planned = plan.min(labor.available)`, shares by
   `proportional_shares(planned, &available)`, `attended = min(cash / rate, planned)` (371-376), and it sets
   `labor.available = attended_total` (349).
7. `MemberLaborUseReceipt::validate` requires `planned + unplanned == available` and `attended + unattended ==
   planned` (attendance.rs:91-120).
8. `rest::made_hours` reads `economy.member_labor` of the period (rest.rs:37-50); `restart_stopped` counts with
   `count` (779-782) and tests with `is_tested(.., made_hours)` (796-799).
9. `test_workplaces` reads `available`, `attended`, `unattended`, `bill` from the member receipts and `employed`
   from the staffing pools (standing.rs:198-310); `judge` gives `min(employed, ceil(attended / hpp))` (148-154).
10. `staff_in_places` builds the hosts' wage map from the closed state's employment rows (state.rs:859-867) and
    runs the stop round before `staff_places` (872-892).
11. `advance_pool`: `target = requested_people.min(labor_force).min(limit)` (staffing/transition.rs:71-77).
12. `record_receipt` refuses a slot that both gained and lost, and a gained slot with engine separations
    (place.rs:332-347); `StaffingMemberReceipt::validate` refuses hires and separations both (members.rs:166).
13. `finish_with_place_staffing` compares the record of layoffs it advanced with `PlaceStaffing.records` and
    refuses a difference with `PublicProgramInvariant` (state.rs:940-952).
14. `PlaceStaffingError` is matched outside the engine only in `W/runner/run.rs:541-551` and, by one named
    variant, in the bench's `sets.rs:253`.
15. The benefit after a layoff reads each record's member's `Wage` row (financial/programs.rs:88-101) at
    `FinancialClose::opening`, and is `wage x hours x 5_000 x units / 20_000` (layoffs.rs:198-208).
16. `MonetaryBook::transfer_cash` refuses identical parties, non-positive amounts and short cash
    (accounts.rs:736-756); `CostClose::cash_gift` posts gift expense and income (valuation/close.rs:456-475).
17. `HistoricalCostBook::open` gives every money-book account a capital row (valuation/book.rs:47-80), which is
    how a test opens an organization's account before Task 2.
18. The `Runner` exposes `state`, `staffing`, `standing`, `members`, `shocks`, `rules_at` and `next_period`
    (W/runner/run.rs:126-302); the bench's `sets.rs:280-318` closes a runner's state with the engine directly.
19. The contract's digest is pinned once, by `T/weighted_freight.rs:382-386` against `MATERIAL_CIRCUIT_SOURCE_
    SHA256` (E/wire/state.rs:31); `d4ac7dc0d` changed the yaml and the constant in one commit.
20. Farm A at period 1: 4 persons, 40 hours planned, $880 of cash before wages; tax rows 500 and 1,500 bps on
    each worker household's wages (W/doubled/opening.rs:29, 89-107, 466-474, 523-540).
21. Every close refuses a book whose organization or public accounts are not exactly those of
    `financial.locations` (financial/validation.rs:59-74), so a test's organization account needs its location.
22. `advance_records` advances each member's record from one receipt with `advance_layoffs`, whose step (d)
    takes hires from the newest cohort first and then from the uncovered (layoffs.rs:46-106, 125-160).
23. `PlaceRules` has a second literal in the unit tests' `run` (place.rs:691), beside the test `Case` (650-660).
24. `Currency` has no `Display` impl (no `impl Display for Currency` in the workspace).

### The small worlds

1. `World` derives `Clone, Debug, PartialEq, Eq` and has four fields; `scene()` is a `const fn`
   (`W/doubled/world.rs:57-67, 80-87`).
2. Only three `World` literals name every field: `tests/worlds.rs:30,39` and the bench's `runs.rs:88`; `sets.rs`
   231/261/282 and the client's `marks.rs` 504/645/1218 use `..World::scene()`.
3. `cash_accounts` lists sites, households, then the treasury and the fund only in the fund world
   (`W/doubled/opening.rs:158-181`).
4. Every `Organization` and `Public` account of the book must have an `InstitutionLocation`
   (`E/financial/validation.rs:64-74`); `canonicalize` sorts the locations by account (14-15).
5. `OrganizationAccountId` is an identity type with a `const fn from_bytes` (`E/accounts.rs:17`,
   `E/model.rs:58-75`), exported from the engine's root (`E/lib.rs:54`).
6. `Currency::from_micro_units` is not `const` (`babylon-kernel/src/currency.rs:45`).
7. The fund world taxes each worker household's `WageIncome` at 500 and 1,500 bps (`W/doubled/opening.rs:42-43,
   522-533`); the wage is $10 (`:25`), the clinic's $11 under P4 (`:37`, `wage` 139-145, private).
8. A shop's workers are 4 persons, a utility's 12 (`W/ids.rs:280-290`); a fund-world person works 10 hours
   (`W/doubled/world.rs:164-171`).
9. Each workplace's owner is `Household::Owner(place)` with one share (`W/doubled/opening.rs:492-497`); profit is
   `DistributionReceipt.paid` to `beneficiary` (`E/financial/model.rs:262-272`).
10. `TaxReceipt` carries `payer`, `basis`, `rate_bps`, `assessed` (`E/financial/model.rs:250-261`);
    `PublicProgramReceipt` carries `recipient` and `paid` (215-226).
11. `StaffingMemberReceipt` carries `pool_id`, `site_id`, `member` (with `household_id()`), `hours_per_person`,
    `opening_employed`, `separations`, `closing_employed`, `next_opening_hours` (`E/staffing/members.rs:136-152`).
12. `proportional_shares` is crate-private in the engine (`E/staffing.rs:11`, `E/staffing/members.rs:180`).
13. `advance` closes, staffs, checks, digests, reads, then builds `PeriodResult` (`W/runner/run.rs:339-428`); `step`
    keeps `Stepped` only on `Ok` and stops the run otherwise (191-215).
14. Without the seekers each workplace's people must stay its opening workers (`W/runner/run.rs:686-693`).
15. `PeriodSummary.prices` are the posted offers at the close, `i128` (`W/runner/result.rs:99-100`, filled
    `W/runner/run.rs:742-746`); `asked` and `hours_attended` are by `Workplace::index` (result.rs:29-31, 91).
16. The bench's `account_name` panics on any account but sites, households and public ones (`rows.rs:44-58`), and
    `put_prices_and_output` names every book account (`rows.rs:211-214`): a fight world cannot go through `rows`.
17. `Form::ALL` lists seven forms; `opening_with_a_form_is_turning_its_rules_on_first` loops over it only
    (`runs.rs:27-35`, `sets.rs:169-191`).
18. The close writes a `TaxReceipt` for every tax policy every period, base 0 or not, with its `rate_bps`
    (`E/financial/close.rs:291-311`); every member, pair members too, has a `member_labor_use` row with its
    `compensation` (`tests/runner.rs:74-91`).
19. Each small-world need is one unit a person (`HouseholdNeedBasis::Persons`, `W/doubled/catalog.rs:143-158`),
    and a required quantity is the cohort's persons (`E/recurring/model.rs:77-90`): per-person needs are exact.
20. `RunnerError` derives `Clone, PartialEq, Eq` (`W/runner/error.rs:48`): `PeriodOrderError` and `FightError`
    must derive them too.
21. `PeriodResult.members` is the engine's staffing decision before the seekers' moves (`placed.member_receipts`,
    `W/runner/run.rs:527-537`), so a striker's persons left after a taken place are read from the orders' receipts.

### The scene

- `rust/crates/babylon-kernel/src/currency.rs:28-32`: `CurrencyOverflow` derives `Debug` only; no `Error` or
  `Display` impl for it exists in `rust/`, so a test maps it to words before `?`.
- `C/scene.rs:289-310`: the Paint chain holds 18 systems at 98a0e3624.
- `C/reading.rs:252-319`, `inspect.rs:167-178`, `frame.rs:810-824`, `marks.rs:157-166`: the client reads money
  transfers and looks up known parties' accounts; no path walks the closing book's accounts, so the fight world's
  16 kept organization accounts meet nothing.
- `C/reading.rs:16-21`: `Party` has four variants; `from_account` (26-36) answers `None` for every
  `AccountId::Organization`.
- `C/reading.rs:298-302`: `read_payments` refuses `CashTransferPurpose::MutualAid` as `UnexpectedPayment`.
- `rust/crates/babylon-material-circuit/src/accounts.rs:685-687`: a `WagePayment` debits `PayrollReserve`, so
  `a_receipt_of_no_party_is_refused` (reading.rs:538-547) still refuses after mutual aid is read.
- `C/frame.rs:38`: `STREAM_MONEY: [u16; 6]`; `field_styles` (218-253) makes one stream a `STREAM_MONEY` entry;
  `the_styles_name_the_plans_units` (1553-1565) pins 10 streams.
- `C/frame.rs:650-661`: `Standing::point` matches `Party` exhaustively, as do `party_id` (356-363),
  `inspect::account_of` (45-52), `controls::body_extent` (503-506) and `table::row` (83-87).
- `C/layout.rs:80-93`: `anchor` ends in `_ => None`, so a new payment kind places no one.
- `C/panel.rs:50-55`: `Lower` is `Shocks, Rules`; `spawn_lower` (461-518) spawns two `LowerBody`s;
  `scene_tests.rs:1195` pins 2.
- `C/panel.rs:589`: `view_index` is private; `paint_table` (707) and `paint_inspector` (794) use it.
- `C/panel.rs:838-859`: `rows_for` extends `inspect::inspect`'s rows with `marks::rule_rows`.
- `C/panel.rs:396`: the shock button's caption is "Strike"; `SceneCommand::Strike` is written only in
  `scene.rs`, `panel.rs`, `script.rs` and `scene_tests.rs` (`tests/decision_surface_contract.rs` writes only
  `Step`).
- `C/scene.rs:506-519`: `start_over` opens `Runner::open()` and keeps `view.lower`; `turn_on` (585-591) sets
  `view.lower` to its tab.
- `C/scene.rs:280-282`: the scene's presses are observers (`panel::pressed`, `rules::pressed`) added in
  `SmallWorldPlugin::build`; the paint systems are one chain (289-310).
- `C/script.rs:128-134`: `lower_named` knows `shocks` and `rules`; `check_names` (149-193) refuses an unknown name
  before the window opens.
- `C/script_tests.rs:436-451`: `PROOF_8C` and `the_proof_script_of_task_8c_parses` already exist.
- `rust/crates/babylon-material-circuit/src/payments/attendance.rs:63-85`: `MemberLaborUseReceipt` carries
  `compensation: LaborCompensation` and `member_id`; `LaborCompensation::wage_rate` (26-31).
- `rust/crates/babylon-material-circuit/src/staffing/members.rs:138-148`: `StaffingMemberReceipt` carries
  `member: StaffingMemberBinding` (`member_id()`, 68; `household_id()`, 72), `hours_per_person` and
  `opening_employed`.
- `rust/crates/babylon-circuit-worlds/src/runner/result.rs:73-86`: `Closing.cash` is every cash account in the
  book's order, so an organization's fund is there once Task 2 opens it.
- `C/frame.rs:487-516`: a group's position is the money-weighted mean of its payers' anchors, else its home
  (`layout::home_of`); `idle_of` puts persons not at work at the idle ground.
- `C/frame.rs:1444-1454`: `twelve_periods(mode)` (12 periods of `Runner::open()`, harvest failed in Place B from
  period 3) exists for the frame pin.
- `C/scene_tests.rs:1323-1330`: `scripted(text, frames)` runs a script in the headless app; `a_script_turns_a_rule_on`
  (1301-1320) reads `replies.jsonl` as the new script tests do.

## Self-review notes

**The design's build order, items 1 to 7, and the tasks.**

| Item of the design | Tasks |
| --- | --- |
| 1. The orders of a period; organizations and the accounts kept for founding; dues, strike pay and relief as payments; the scene reads them | 1 (orders, payments to and from a fund, shares of wages), 2 (a world asks; the kept accounts), 2c (the switch and the tab). The scene reads payments in P2-1, with the first organization that can pay |
| 2. Pay changes at a boundary; shown for each workplace | 3, 3c |
| 3. Hours withheld; the stop rule, the resting price and the restart leave struck hours alone; the people at the gate | 4, 4c |
| 4. Withheld hours filled above the rolls; whose places are taken; the order of a loss | 5, 5c. "What happens to the people taken on after a win" needs a contract or a call: Part Two |
| 5. The measures and the news | 6, 6c |
| 6. The household's weighing and the ask with no call; the weighing of the people who look for work; the two tests of Amendment AM | 7 (the pure weighings and both tests), 8 (how each amount is formed) |
| 7. The employer's rule, the offer, both counts over the last year | 8, 8c |
| The order inside a period (item 8's first clause) | 2 (the runner's composition), 8 (`decide` and `close`) |
| The later slump with no organization (comparison 2, first run), and the same with every ask offered at once (a measuring run, call 18) | 9 |

**Rules of the design that Part One does not build:** PF3's organizations as actors, PF8, PF9's ties, PF10, PF11's
contract, PF12, PF16, PF17, PF18, A15 behind its switch (PF4), events and the forecast (PF15). Each has its line in
Part Two.

**How we know it works, in Part One.** Conservation: the runner refuses money or people not conserved in every
period of every test and of Task 9's hundred runs. Nothing moves by itself: `empty_orders_close_as_the_older_entry`
(Task 1), `a_world_that_does_not_ask_steps_as_before` (Task 2), `a_world_with_no_fight_draws_as_before` (Task
2c), and the fourteen `reproduces_` long tests after Tasks 1, 2, 4, 5, 8 and 9. Each weighing shown for one member:
Task 7's two tests for PF5 and PF6. The counted comparison: Task 9. The lead's look: after Tasks 2c and 4c, and
Task 8c's proof script.

**The one check, and what it changed.** Three readers checked the engine's, the small worlds' and the scene's
tasks against the code at 98a0e3624, the design and each other. Six findings would have stopped a builder or a
run: a test helper that opened an organization's account with no location; staffing orders checked against a
decision their orderer cannot see; a taker's slots counted twice across two offers; orders of nothing for a taker
with no share; `pay_step` used two tasks before it existed; and one loss of the owners counted against each of
their struck workplaces. All are folded in; none was checked again. Three calls that the check led to were put
to the Director the same day and ruled as the lead had called them (F11 to F13).

**What a reader should know is not here.** No test of Part One can show a payment to or from a fund on screen, a
call, a contract, a founding, or the line under a win: they are Part Two's. Task 5 builds three acts of the engine
(hours for people named, taking on, the floor) that only Part Two reaches on screen; the contract text says so.

## What the reading against the built stored-hours code changed

Nothing yet. The reading is owed before Task 1 starts: stored hours' Tasks 2 to 7 were not built when this plan
was written.
