# Household Units Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every Wayne household unit money of its own, so that the player can see by count who
is going without, reach one of those households through the County Review, and read next period
whether it ate.

**Architecture:** A household unit is an ordinary household account of the engine. The opening
build runs the County Review's own placement once on Wayne's pooled budget groups, reads the units
from its rows (budget group, crew at the opening or none, band), and divides each group's persons,
cash, pantry, crews, business shares and ages among them before any money is wired. The County
Review then builds its roster from those same rows, with one county group for each unit, so its
rules run on positions inside units with no change to the rules themselves. The engine gains one
capability: a household buys its needs in a declared order. The County Review's facts gain each
unit's closing cash, net assets and unmet needs; its projection and the client show who went
without, folded by band and unit. A campaign asks for all of this with one optional section of the
policy file, which selects a new compiler name; every earlier compiler gives the bytes it gives
today.

**Tech Stack:** Rust (workspace `rust/crates`: `babylon-practice-contract`,
`babylon-material-circuit`, `babylon-tick`, `babylon-persistence`, `babylon-client` on Bevy), TOML
scenario defines, PostgreSQL runtime for the recorded playthroughs, Python 3 for the reference
tables and the second gate report, YAML decision records, reStructuredText lessons.

**Spec:** `docs/superpowers/specs/2026-11-20-households-and-homes-design.md`, approved by the
Director on 20 November 2026 and corrected the same day (commit `ad7d3a548`). This plan is its
"Plan 1: a unit holds its own money". Read sections 4, 5, 7.1 to 7.6, 8, 9, 10 and 12 before any
task. Step B (homes, sections 7.7 to 7.19) is not in this plan and nothing here builds toward it
beyond Tasks 9 and 10.

**Build order:** Tasks 1, 2, 3, 6, 4, 5, 7, 8, 9, 10. The numbers follow the design's list. Task 6
(the order of going without) is built before Task 4, so that Task 4's report is recorded once, on
the final buying rule. The design's item 9 is Tasks 9 and 10. Tasks 9 and 10 touch no Rust source
of the game and can be built at any point after Task 4.

**Checkpoints with the Director.** These are reports, not stops, unless a gate is red or a finding
contradicts the design.

1. After Task 1: the share of household wealth the top tenth holds today, beside the law's two
   thirds, and whether every budget group has at least one person outside the labor force for each
   household (the opening's persons rule needs it).
2. After Task 4: the same on the units, band by band. The top 1% is one unit with no wage and no
   relief unit, so it is expected to go without within about four periods. The design names the
   remedy (section 7.2): the division of the shares moves forward. The Director decides.
3. After Task 8: the gate's first report.
4. After Task 10: the gate's second report. Plan 2 is written only after the Director has read both.

## Global Constraints

- Work only in `/media/user/dev-ssd/worktrees/households-homes/babylon`, branch
  `codex/households-and-homes`. Start every shell command with `cd` to it (or to its `rust/`
  directory). Never push. Never open a pull request. The branch stands on the County Review branch,
  which is local and unpushed too.
- The disk is unencrypted: no secrets, no `.env`, no `babylon-data` there.
- One cargo or pytest process at a time, on the whole machine. Never pass `-j` or `--jobs`; the cap
  of 4 jobs comes from `.mise.toml`. Before a cargo build in this checkout, say that it evicts the
  build cache of any other checkout.
- **Scoped gate, run by every task before its last commit,** one leg at a time: from `rust/`,
  `mise exec -- cargo fmt --all -- --check`, then `mise exec -- cargo clippy --workspace
  --all-targets --locked -- -D warnings -D clippy::cognitive_complexity`; then the test binaries the
  task names, with `mise run rust:test:q -- -p <crate> -E 'binary(<name>)'`; then `mise run
  rust:test:q -- -p <crate>` once for each crate the task changed; then `mise run
  check:bsl-sentinels` if the task touched a rule file or a governed table. While a task is being
  written, iterate on clippy and one test binary only.
- **Whole gate, run by the lead only, three times:** after Task 4, after Task 7 and in Task 8.
  `mise run rust:check-no-docs` takes about 35 minutes; start it in the background with its output
  in a log file, and use cargo for nothing else until it ends. A task never runs it.
- An ignored test runs with `--run-ignored ignored-only` added to the scoped test command.
- Python runs as `mise run test:q -- <path>`; the Python gate is `mise run check`.
- Commit one unit of work at a time: `git add <files>` then `PYTHONPATH=src mise exec -- git commit
  -q -F <message file>`. Check that `git log --oneline -1` moved; a hook can refuse without a
  visible error. The body ends with `Part of PER-369` and a `Co-Authored-By` line naming the model
  that wrote the commit. Never commit `uv.lock`.
- No file under `tests/baselines/` is expected to change. If one must, stop and tell the lead; such
  a commit needs the trailer `Baselines: blessed(<slug>)`.
- **Bytes.** A campaign whose policy has no `[household_units]` section keeps every byte it has
  today: opening, catalog, register, snapshot, receipt, fixture. New serde fields are `Option` with
  `#[serde(default, skip_serializing_if = "Option::is_none")]`.
  `contracts/national_storage_qualification_v6.json` stays byte-identical. Saved catalogs of
  compiler `national-world-v12` still open.
- No rule uses floating point. Money is `i128` millionths of a dollar. Counts are `u64`. Shares are
  exact fractions or basis points that add back.
- No rule of the County Review reads an identifier to settle a tie or to order an outcome. The
  opening's exact splits among a group's household units order them by band, crew, households and
  labor force, and take the canonical order of the pooled crew's member id as the last tie only, as
  the opening's other splits already do. ADR306 R6 records it.
- No rule reads the average of a group. A household's labor figures are its position's; its money is
  its unit's (spec section 5). A figure "for each household" is a rate of two of the unit's totals.
- Every refusal is a typed error that names what was refused. No panic, no `unwrap` outside tests,
  no silent clamp, no fallback value.
- In code the new object is `HouseholdUnit...` or `household_unit`. A bare `unit` already means the
  engine's unit of measure (`UnitId`) and the county's relief unit (`PositionKey.units`).
- On screen the new object is a "household unit" and the county's support is a "relief unit". A
  budget group reads "with a business share" or "no business share"; "owner" is kept for homes.
  On-screen text never calls households "workers", "proletariat" or "the base". Every view of the
  County Review keeps the line: "This slice has no nation, no solidarity and no consciousness.
  Households act on their own money only."
- Counts are public. A unit's dollar figures are shown only when the player has earned them by
  contact (spec 7.5, ADR182). Shares are public.
- Scenario numbers stay in `content/scenarios/national/defines.toml`, each with its evidence class.
- Recorded reports go to `reports/household-units-2026-11-20/`: JSON with money as decimal strings
  of millionths, a trailing newline, each file under 1 MiB. The records in
  `reports/county-review-2026-11-19/` are history and are never rewritten.
- Markdown is wrapped at 120 columns, headings at 80; reStructuredText at 100. Refer to the player
  as "they".
- Downloads (Task 9 only) go to a new dated directory on the data drive, never into the repository
  and never onto this disk. A request carries a generic client name and no name of a person or of
  this project. A downloaded file is read with `python3 -I`, with its path passed as an argument.

## Review Focus

1. **A campaign saved before household units.** Its policy has no `[household_units]` section, its
   county groups are budget groups and its facts carry no purse. Expected: it opens and plays with
   the bytes it has today; the roster folds by band and shows each budget group as one unit; the
   views that need a purse say "not in this campaign" with the reason. Tests in Tasks 3, 5 and 7.
2. **A unit with no money left.** The top 1% is expected to reach this within about four periods.
   Expected: the close does not fail; nothing is admitted; every need is unmet and every household
   of the unit is counted as going without; no wage tax is collected and the record says so; a need
   with a requirement of zero divides nothing. Tests in Tasks 5 and 6.
3. **A unit that shrinks or empties.** A unit of one or two households loses a person, or every
   household of a unit leaves. Expected: the leaving households come from the unit's rows with
   nobody in the labor force, the roster still adds to the engine's counts, a unit with no
   households is not shown, and a rate "for each household" of an empty unit is shown as "none" and
   never divides by zero. Tests in Tasks 2, 5 and 7.
4. **A unit in two bands, and a unit with no households.** The aid donors are one unit in two
   bands; the collective residence is one unit with no households and with relief units on the
   roll. Expected: every figure shown by band adds back to the units' totals exactly; the donors
   appear under both bands with their own positions; the collective residence is absent from the
   fold and its relief units stay on the county's roll. Tests in Tasks 4, 5 and 7.
5. **The player presses a roster slot after the roster moved.** The fold changed, the page changed,
   or the chosen position no longer exists when the contact lands. Expected: a press on a band or a
   unit only folds or unfolds and never spends the period's contact; a press on a position chooses
   the position that was on the screen; if it is gone when the turn closes, the turn commits and
   the session records `no_such_position`, as today. Tests in Task 7.

## File Structure

New files, each with one responsibility. Everything else is a change inside an existing file, and
each task lists those.

| File | Responsibility | Task |
|---|---|---|
| `ai/decisions/ADR306_household_units_in_wayne.yaml` | The rulings of step A | 2 |
| `rust/crates/babylon-persistence/src/national_economy/opening/household_units.rs` | The opening's units: pooled placement, the table, the splits | 3 |
| `rust/crates/babylon-practice-contract/src/county_review/household_units.rs` | The kernel's count of who went without and the household-unit views | 5 |
| `rust/crates/babylon-persistence/tests/national_household_units.rs` | The slice's one persistence test binary: reports, add-back, limits | 1, 3, 4, 6, 8, 10 |
| `rust/crates/babylon-persistence/tests/support/household_accounts.rs` | Reading household accounts and receipts period by period | 1, 4 |
| `reports/household-units-2026-11-20/` | Recorded reports, playthroughs and the two gate reports | 1, 4, 8, 10 |
| `docs/tutorials/who-goes-without.rst` | The lesson of step A's loop | 8 |
| `tools/make_national_housing_reference.py` with its sources file and tests | The census housing tables, built and pinned | 9 |
| `tools/household_units_gate_report.py` with its tests | The second gate report's arithmetic | 10 |

---
## Rulings That Override a Task

The ten task sections were drafted one by one and each was checked against the code. Where two of
them name the same thing differently, these rulings decide. Read them before your task. If the code
contradicts a ruling or a task, the code wins: say so in your report and build the code-true thing.

**R-A. One producer for each shared thing.** A task consumes only what an earlier task in the
build order produces.

| Thing | Producer | Consumers |
|---|---|---|
| `opening_roster_from_rows`, `split_by_largest_remainder` (kernel) | Task 2 | 3, 4, 5, 8 |
| ADR306 and every ruling in it | Task 2 | all |
| the policy section, v13, the units table, `national_household_units()`, the re-exports of the three table types, `input_before_household_units()` | Task 3 | 4, 5, 6, 8, 10 |
| `HouseholdNeed.rank`, the ranked templates, `household_template` | Task 6 | 4, 5 |
| `AccountSpec`, `read_accounts`, `read_period`, the report shapes | Task 1 (pooled), Task 4 (units) | 8, 10 |
| the kernel facts and the views of R-C | Task 5 | 7, 8 |
| the housing parts, their metadata, the Federal Reserve table | Task 9 | 10 |

A later task edits ADR306 in place only if its code-true rule differs from the ruling's words.

**R-B. The kernel's money split is Task 2's.** In
`rust/crates/babylon-practice-contract/src/county_review/split.rs`, public, exported as `apportion`
is:

```rust
/// Divides `total` among parts in proportion to `weights`. Each part gets the floor of
/// total × weight ÷ Σ weights; what is left goes one each to the largest remainders, and equal
/// remainders go to the earlier part. Unlike `apportion`, the total is not capped by the weights.
pub fn split_by_largest_remainder(total: u128, weights: &[u64]) -> Result<Vec<u128>, CountyReviewError>;
```

Σ weights = 0 with a total above 0 is `CountyReviewError::Arithmetic`, and so is any overflow. A
total of 0 gives all zeros. Pinned values: `(7, [3, 1]) -> [5, 2]`; `(300_000_000, [2, 1]) ->
[200_000_000, 100_000_000]`; `(10_000, [0, 1, 1, 1]) -> [0, 3334, 3333, 3333]`; `(1, [1, 1]) ->
[1, 0]`; `(0, [0, 0]) -> [0, 0]`; `(5, [0, 0]) -> Err(Arithmetic)`. Callers list the parts from the
bottom 50% up. Task 5 defines no private copy. Task 4's test helper `split_by_households` is a thin
wrapper over it.

**R-C. The household-unit views are these.** Task 5 produces them and Task 7 consumes exactly
them. Where Task 7's text names a field differently (`facts_period`, `support_micros`,
`aid_micros`, `wealth_basis_points`, a unit row for each band), this is the form.

```rust
// CountyReviewProjection.household_units: Option<HouseholdUnitsView>  (serde default; skipped when None)
pub struct HouseholdUnitsView {
    pub period: Option<u64>,            // the period the facts are from; None before the first close
    pub needs: Vec<String>,             // each need's label, in the config's order
    pub bands: Vec<BandUnitsView>,      // four, top first, as band_counts orders them
    pub units: Vec<HouseholdUnitView>,  // the ordinary groups the roster holds households in, config order
}
pub struct BandUnitsView {
    pub band: Band,
    pub went_without: Vec<u64>,               // households, per need
    pub wealth_bps: Option<u16>,              // share of household wealth; None when no band holds any
    pub ownership_to_needs_bps: Option<u64>,  // ownership pay over the cost of needs; None at zero cost
}
pub struct HouseholdUnitView {
    pub group: u32,
    pub label: String,
    pub bands: Vec<HouseholdUnitBandView>,    // one for each band the unit has households in, bottom 50% first
    pub not_supplied: Vec<bool>,              // per need: its seller supplied less than the unit paid for
    pub wage_tax_short: bool,                 // assessed > collected in the period closed
    pub earned: Option<HouseholdUnitEarned>,
}
pub struct HouseholdUnitBandView {
    pub band: Band,
    pub went_without: Vec<u64>,               // per need: the unit's count in this band
}
pub struct HouseholdUnitEarned {
    pub households: u64,
    pub closing_cash_micros: i128,
    pub cash_micros_per_household: i128,
    pub net_assets_micros: i128,
    pub wages_micros: i128,
    pub wage_tax_assessed_micros: i128,
    pub wage_tax_collected_micros: i128,
    pub support_income_micros: i128,
    pub aid_income_micros: i128,
    pub ownership_income_micros: i128,
    pub ownership_micros_per_household: i128,
    pub free_hours: u64,
    pub needs: Vec<NeedPeriodFacts>,
    pub could_not_buy_micros: Vec<i128>,      // per need: unpaid × the period's price; 0 when nothing is required
}
```

- A unit's count for a need is `went_without(required, unmet, households)`. A unit in two bands
  divides it between them by its roster households in each (the kernel's `apportion`, bottom 50%
  first), so the units' parts under a band add exactly to that band's count.
- `not_supplied` is a flag, not a count: what a unit asks of a good includes its pantry, so the
  quantity "unsupplied" can exceed what its households need.
- The client divides nothing. Every figure it shows arrives in the view. It builds a unit's one
  sentence from the unit's public fields.
- Public: everything but `earned`. A unit's households stay earned, as a position's are today. A
  unit is earned when any contacted position is one of its positions.

**R-D. The recorded reports' shapes.** `wayne-unit-accounts.json` (Task 4) is columnar. Each of
`units[]` has `principal`, `label`, `bands` as `[[band, households], ...]` and `series`. Stock
figures have 35 points, point 0 being the opening: `households`, `persons`, `labor_force`,
`cash_micros`, `pantry_cost_micros`, `other_assets_micros`, `net_assets_micros`. Flow figures have
34: `wages_micros`, `support_micros`, `aid_micros`, `company_payouts_micros`,
`site_distributions_micros`, `ownership_income_micros`, `wage_tax_assessed_micros`,
`wage_tax_collected_micros`, `needs_cost_micros`. `needs` is an object keyed by need key, each with
34-point arrays `required`, `unmet`, `unpaid`, `unsupplied`, `cost_micros`. Task 1's
`wayne-pooled-accounts.json` uses the same figure names. Task 10's reader parses exactly this.

**R-E. The reference tables' names.** Task 9 writes them and Task 10 reads them in this form.

- Parts: `src/babylon/data/reference/economy/national_housing_reference_2024_<part>.csv.gz` for
  `tenure`, `tenure_by_income`, `structure_and_vacancy`, `value`, `mortgage_and_dollars`, `rent`;
  columns `county_geoid`, then `<table>_<E|M><line:03>_value`, `_raw`, `_status`.
- Metadata: `src/babylon/data/reference/economy/national_housing_reference_2024.metadata.json`.
- The Federal Reserve's table:
  `src/babylon/data/reference/national/federal_reserve_dfa_networth_levels_2026q2.csv`, the header
  row and the five 2026:Q2 rows as published (`TopPt1`, `RemainingTop1`, `Next9`, `Next40`,
  `Bottom50`; millions of dollars). The top 1% is `TopPt1` plus `RemainingTop1`. Task 10 does not
  expect a long `group,measure,value` table.
- Task 10 registers the artifacts in `data-artifacts.yaml` by hand and raises the count that
  `tests/unit/reference/test_data_artifacts.py` pins. Never run `mise run data:artifacts`.

**R-F. One reader of the opening's units.** Task 3 produces
`CapturedEconomicCatalog::national_household_units(&self) -> Option<&OpeningHouseholdUnits>` and
the `pub use` of the three table types from `opening.rs` and `national_economy.rs`. Task 4 adds
neither.

**R-G. The policy before household units.** Task 3 adds to
`rust/crates/babylon-persistence/tests/national_household_units.rs` the helper `fn
input_before_household_units() -> EconomicCatalogInput` (the shipped input with the policy source
cut at `"\n[household_units]\n"`) and moves Task 1's tests onto it in the commit that appends the
section, so the pooled measurement keeps compiling as `national-world-v12` with 8 county groups.
Tasks 4 and 8 use that helper and define no other cut.

**R-H. What ADR306 must also say.** Task 2 writes these into the rulings its table lists.

- R8: `grain = "group"` gives the pooled opening value for value, apart from the identifiers the
  engine hashes from the policy text (the aid mandates' ids and source hash, the commitments that
  carry them, the config's policy digest) and the labels of R14.
- R12: under v13 a county group has a business share by its budget key
  (`HouseholdBudgetKey::owner_exposure`), not by how its shares rounded.
- R13: a unit's households stay earned; a unit is earned when any contacted position is one of its
  positions; the went-without counts and the flags "not supplied" and "wage tax not collected in
  full" are public.
- R14: the organizer archive's sentence about what the county could pay says "relief units" for
  every campaign. It is derived text, not a stored field.
- R9 already holds the pantry call. Task 6 adds no ruling.

**R-I. What Task 10 found about step B's opening** (carrying census counts to the game's
households, the classes of building size, a missing refusal, the Federal Reserve's ratios) goes
into the second gate report as findings for the Director. No task edits the design.

---

### Task 1: The measurement on today's accounts

Design section 9 item 1 and 7.2 ("Wealth is measured", "What the top 1% are paid is measured too");
ADR305 R4. Test-only: no engine or persistence source changes. It reads today's pooled Wayne
accounts and records them, and Task 4 calls the same reader again with the units' accounts.

**Files:**
- Create: `rust/crates/babylon-persistence/tests/support/household_accounts.rs` (the reader)
- Create: `rust/crates/babylon-persistence/tests/national_household_units.rs` (a new test binary.
  It includes the reader with `#[path = "support/household_accounts.rs"] mod household_accounts;`.
  No `Cargo.toml` change, because every dependency the reader needs is a normal dependency)
- Create: `reports/household-units-2026-11-20/wayne-pooled-accounts.json` and its `README.md`

**Interfaces:**
- Consumes (unchanged, at HEAD): `CapturedEconomicCatalog::capture_national_campaign(
  economic_catalog::national_catalog_input(), campaign)`, `compiler_version()` (capture.rs:335),
  `create_foundation(self, ReplaySessionId, ReplaySeed)`, `MaterialReplaySession::material()`
  (:649), `catalog()` (:654), `prepare_advance(&self, &OrderedPracticeActionBatch)`,
  `commit_prepared_and_publish`, `PreparedMaterialTick::material()` (:582),
  `PreparedMaterialWorld::receipt_bytes()`, `material_world::decode_material_receipts(&[u8])`,
  `HistoricalCostBook::capital_accounts()` / `snapshot()` (valuation/book.rs:38, :172),
  `MonetaryBook::cash` / `snapshot()` (accounts.rs), `CountyReviewRegister::config()` / `state()`.
- Produces (in `tests/support/household_accounts.rs`; the names here are a contract with Task 4):

```rust
pub type Session = MaterialReplaySession<HypergraphStore>;
pub struct AccountSpec { pub label: String, pub principal: FinalDemandPrincipalId, pub bands: Vec<(Band, u64)> }
pub struct AccountReading {            // the state after a commit, or at the opening
    pub households: u64, pub persons: u64, pub labor_force: u64,
    pub cash_micros: i128, pub pantry_cost_micros: i128,
    pub other_assets_micros: i128,     // freight + claims carried + purchase escrows + wages owed to it
    pub net_assets_micros: i128,       // capital row: opening_capital + contributed_capital + retained_earnings
}
pub struct NeedReading { pub key: String, pub required: u64, pub unmet: u64,
    pub unpaid: u64, pub unsupplied: u64, pub cost_micros: i128 }
pub struct PeriodReading {             // one close, read from the candidate before it commits
    pub wages_micros: i128, pub support_micros: i128, pub aid_micros: i128,
    pub company_payouts_micros: i128, pub site_distributions_micros: i128, pub ownership_income_micros: i128,
    pub wage_tax_assessed_micros: i128, pub wage_tax_collected_micros: i128,
    pub needs_cost_micros: i128, pub needs: Vec<NeedReading>,   // in the catalog's need order
}
pub fn read_accounts(session: &Session, specs: &[AccountSpec]) -> Vec<AccountReading>;
pub fn read_period(session: &Session, candidate: &PreparedMaterialTick<HypergraphStore>,
                   labels: &[CommodityLabel], specs: &[AccountSpec]) -> Vec<PeriodReading>;
pub struct TopTenth { pub households: u64, pub net_assets_micros: i128, pub household_net_assets_micros: i128,
                      pub ownership_income_micros: i128, pub needs_cost_micros: i128 }
pub fn top_tenth(specs: &[AccountSpec], accounts: &[AccountReading], period: Option<&[PeriodReading]>) -> TopTenth;
```

Both readers return one row per spec, in spec order. `Band` is `babylon_persistence::runtime_session::Band`;
`CommodityLabel` is `babylon_persistence::economic_catalog::CommodityLabel`. `top_tenth` counts only
specs whose bands are not empty and are all `Top1` or `Next9`.

**Decisions:**
- *Where each figure comes from.* The account is `AccountId::Household(spec.principal)`. Households and
  persons come from its `HouseholdCohort` in `recurring.households`. The labor force is Σ (at_work +
  seeking) × households over the County Review roster rows whose group is the config group with
  `group_id == spec.principal.as_bytes()`. The kernel checks that roster against the engine every
  period. Cash comes from `book.cash`. The pantry at cost is Σ `snapshot().stocks` owned by the
  account. Net assets are read from the capital account row only: the engine checks that row against
  the money book at every close (validation.rs:66-76), and `net_assets` itself is `pub(super)`.
  `other_assets_micros` is Σ freight and claims carried for the owner (`snapshot().freight`,
  `.equity`), plus `reserved_amount()` of book purchases with `buyer == account`, plus
  `outstanding_wages()` of shifts with `payee == account`. Aid lots in transit belong to the donor,
  so this term is not always zero.
- *Ownership income comes by two routes.* The campaign compiles as `national-world-v12`, which has
  companies: a member site's household claims become company claims at the opening. So
  `company_payouts_micros` = Σ `company_distributions.paid` and `site_distributions_micros` = Σ
  `distributions.paid`, each with `beneficiary == account`. The reader asserts that their sum
  equals `IncomeReceipt.statement.distribution_income`. Wages, support and aid are that statement's
  `wage_income`, `public_transfer_income` and `gift_income`. Wage tax is Σ `assessed` and Σ
  `collected` over the `TaxReceipt` rows with `payer == account` and `basis == TaxBasis::WageIncome`
  (as county_review.rs:505-516 sums them).
- *Needs.* Food and materials are goods. For them, `required` and `unmet` come from
  `HouseholdConsumptionReceipt`, `unpaid` = requested − admitted, and `unsupplied` = admitted −
  fulfilled, from `HouseholdDemandReceipt`. Utility, housing, household services and public
  provision are services, and utility is a service too (policy/admission.rs:729). For them,
  `required` and `unmet` come from `HouseholdServiceReceipt`, and `unpaid` and `unsupplied` are Σ
  over `ServicePerformanceReceipt` rows with `buyer == account` and that good. `cost_micros` =
  required × the period's price. That price is the `SellerOffer.unit_price` of the account's
  `HouseholdPurchasePolicy` retailer, read from `session` before the period is prepared, which is
  the price admission uses. For goods the reader asserts that it equals `demand.unit_price`. Keys
  come from `labels` by good id. This keeps "could not pay" apart from "paid and not supplied"
  (C9).
- *The top tenth* is the set of specs whose bands are not empty and are all `Top1` or `Next9`. A
  spec with no bands (the collective residence) is never in it. The cheap test proves that this set
  is exactly the groups with `has_ownership_income`. Its share of wealth is the ratio of its Σ net
  assets to Σ over every spec with households > 0. The collective residence is listed, but it
  holds no household's wealth. All money is added as sums; no rate is ever averaged. [Call]
- *Campaign and seed.* `campaign()` returns `CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7036))`
  (as national_county_review.rs:27-29) and the seed is `ReplaySeed::new(319)`: the campaign and
  seed of the County Review's recorded runs. No organizer commitment is made, so the run matches
  the `no-contact` line.
- *After Task 3.* Task 3 appends `[household_units]` to the shipped `defines.toml`, which makes the
  shipped campaign v13. This test must keep reading the pooled accounts, so Task 3 changes
  `campaign()`'s catalog input to the shipped policy cut before `[household_units]` (the cut-file
  pattern the older-compiler tests use). The v12, 8-group and 7-ordinary pins then stand. Task 3's
  step list names this test among those it amends.
- *Pooled specs* are built in the test binary, not in the reader: one per config group, in config
  order, labelled with the group's label. `bands` is the households per band over the group's
  opening roster rows, lowest band first, with zero bands left out. Task 4 builds its own list.
- *Clippy limits.* Pedantic `too_many_lines` (100) and `cognitive_complexity` (25) apply, and the
  gate denies warnings. The recorder splits into named helpers in `national_household_units.rs`:
  `check_period(&register_facts, &specs, &accounts, &period_readings, period)`,
  `account_json(&AccountReading, Option<&PeriodReading>)`, `top_tenth_json(&TopTenth)` and
  `other_persons_json(&specs, &opening)`. In the reader, the goods arm and the services arm of
  `read_period` are separate functions. No `#[allow]` or `#[expect]` of either lint.

- [ ] **Step 1: Write the cheap test (opening only)**

In `national_household_units.rs`: add `campaign()`, `pooled_specs(&Session) -> Vec<AccountSpec>`,
the `mod household_accounts;` line above, and the test below.

```rust
#[test]
fn the_pooled_opening_accounts_add_back() {
    let catalog = CapturedEconomicCatalog::capture_national_campaign(national_catalog_input(), campaign())
        .expect("the national campaign");
    assert_eq!(catalog.compiler_version(), "national-world-v12");
    let session = catalog.create_foundation(ReplaySessionId::try_from("household-units-pooled")
        .expect("id"), ReplaySeed::new(319)).expect("foundation").into_session().expect("session");
    let specs = pooled_specs(&session);
    let accounts = read_accounts(&session, &specs);
    assert_eq!(specs.len(), 8);
    assert!(specs[4].bands.is_empty(), "the collective residence has no roster rows");
    let ordinary: Vec<_> = (0..8).filter(|&i| accounts[i].households > 0).collect();
    assert_eq!(ordinary.len(), 7);
    assert_eq!(ordinary.iter().map(|&i| accounts[i].households).sum::<u64>(), 700_591);
    for (spec, account) in specs.iter().zip(&accounts) {
        assert_eq!(spec.bands.iter().map(|b| b.1).sum::<u64>(), account.households, "{}", spec.label);
        assert_eq!(account.net_assets_micros,
            account.cash_micros + account.pantry_cost_micros + account.other_assets_micros, "{}", spec.label);
    }
    // band totals across specs: Top1 7_006, Next9 63_054, Next40 280_236, Bottom50 350_295
    // the top-tenth specs are exactly the config groups with has_ownership_income
    assert_eq!(top_tenth(&specs, &accounts, None).households, 70_060);
}
```

Write out the two commented assertions in full: a `BTreeMap<Band, u64>` of the four totals, and
the set comparison against `config.groups[i].has_ownership_income`, using the not-empty rule.

- [ ] **Step 2: Run it and see it fail**

`cd /media/user/dev-ssd/worktrees/households-homes/babylon && mise run rust:test:q -- -p babylon-persistence
-E 'binary(national_household_units) & test(the_pooled_opening_accounts_add_back)'`
Expected: the build fails with E0583 (file not found for module `household_accounts`), because the
reader does not exist yet.

- [ ] **Step 3: Write the reader**

Write the interfaces above in `tests/support/household_accounts.rs`, following the decisions. Read
state with `let CircuitAccounting::Monetary(economy) = &session.material().state().accounting`.
A missing cohort, capital row, roster group, purchase policy, income receipt or label stops the
reader with `expect` and a message that names the spec's label. `top_tenth` with `None` leaves the
two flow sums at 0.

- [ ] **Step 4: Run the cheap test and see it pass**

Same command as Step 2. Expected: 1 passed, in about 40 s; capture and opening took 27 to 28 s in
the County Review's runs.

- [ ] **Step 5: Write the ignored recorder**

```rust
#[test]
#[ignore = "writes reports/household-units-2026-11-20/wayne-pooled-accounts.json"]
fn record_wayne_pooled_accounts()
```

Capture as in Step 1. Keep `catalog.opening().commodity_labels.clone()` before
`create_foundation`. Record period 0 with `read_accounts`. Then, for periods 1 to 34, copy the
loop of `national_household_lifecycle.rs:171-232`: `organizer_action_batch(.., None, ..)`, assert
`actions.resolve_tick() == period`, `prepare_advance`, `read_period(&session, &candidate,
&labels, &specs)`, `commit_prepared_and_publish`, then `read_accounts(&session, &specs)`. In
`check_period`, assert these in every period:
- the net-assets add-back of Step 1, for every account;
- the reader's ownership, support and aid income, closing households and wage tax collected equal
  `last_facts.groups[i]` of the county register (`ownership_income_micros`,
  `support_income_micros`, `aid_income_micros`, `closing_households`,
  `wage_tax_collected_micros`);
- in period 1, `ownership_income_micros == 0` for every account, as `no-contact.json` records.

JSON (serde_json default key order; money as `i128::to_string()`):
- `campaign` (`campaign().as_uuid().to_string()`), `replay_seed: 319`, `compiler`;
- `accounts`: label and bands;
- `periods`: for each of 0 to 34, the `period`, one object per account with every field of both
  readings (no flow fields at period 0), and `top_tenth` with its five sums,
  `share_bps = net × 10_000 / household_net` (floor; a zero denominator stops the test),
  `law_share: "2/3"` and `ownership_over_needs_bps = ownership × 10_000 / needs` (floor; written
  only when needs > 0);
- `other_persons`: at the opening, for each ordinary account, `persons`, `labor_force`,
  `households`, `other_persons = persons − labor_force` and `admits_every_crewless_unit =
  other_persons >= households`. This is C8's test.

Assert that the serialized text is under 1,048,576 bytes before writing it. Write it with the
pattern of `print_wayne_opening_roster` (national_county_review.rs:426-434), to
`../../../reports/household-units-2026-11-20/wayne-pooled-accounts.json`, ending in `"\n"`.

- [ ] **Step 6: Run the recorder once**

`cd /media/user/dev-ssd/worktrees/households-homes/babylon && mise run rust:test:q -- -p babylon-persistence
-E 'binary(national_household_units) & test(record_wayne_pooled_accounts)' --run-ignored ignored-only`
Expected: 1 passed in about 6 minutes (about 28 s to open, plus 34 closes at the County Review's
9.1 s mean). The in-memory time has not been measured before, so the README records the real
time. nextest marks the test SLOW after 60 s but does not stop it. Check by hand: the
no-earner-owner group's period-2 `ownership_income_micros` against 22456090950558 in
`no-contact.json`. If they differ, report it to the lead and do not adjust anything.

- [ ] **Step 7: Write the README**

`reports/household-units-2026-11-20/README.md` has these sections:
- what was run: the campaign, the seed, the compiler and the command of Step 6;
- the time it took;
- where each figure comes from (the Decisions above, in plain words);
- the meaning of unmet, could not pay and paid but not supplied;
- the findings, every number read from the file: the top tenth's share at periods 0, 1 and 34
  beside the law's two thirds; ownership pay beside the cost of needs for the top tenth, period by
  period; the other nine tenths (every spec with households > 0 outside the top tenth): ownership
  pay, which is 0, beside the cost of their needs, period by period; the first period in which
  each group had unmet need; any group whose `admits_every_crewless_unit` is false;
- the line "Homes are not in yet: a household's wealth in this engine is cash, a pantry and claims
  carried at zero."

The lead takes this README to the Director at the checkpoint after Task 1.

- [ ] **Step 8: Gate and commit**

From `rust/`: `mise exec -- cargo fmt --all -- --check` and `mise exec -- cargo clippy --workspace
--all-targets --locked -- -D warnings -D clippy::cognitive_complexity`. Then
`mise run rust:test:q -- -p babylon-persistence -E 'binary(national_household_units)'` and
`mise run rust:test:q -- -p babylon-persistence`. `git add` the four files
(`tests/support/household_accounts.rs`, `tests/national_household_units.rs`,
`reports/household-units-2026-11-20/wayne-pooled-accounts.json`, its `README.md`) and commit with
`PYTHONPATH=src mise exec -- git commit -q -F <message file>`: subject
`test(persistence): measure Wayne's pooled household accounts`, body ending `Part of PER-369` and
the co-author trailer. Check that `git log --oneline -1` moved.

### Task 2: The decision record and the kernel's opening rows

This task covers design section 8 (ADR306, and the amendments to ADR301, ADR302 and ADR305), item 2
of section 9, the [Record needed] mark of section 5's "A household's own figures" (the law of the
state is ADR310, plan 2) and those of 7.1 to 7.3, and brief C1 to C14. It also adds the kernel
function that makes the County Review's roster from the opening's own rows (7.2, C5), and the
kernel proof that a household that leaves never needs a crew row (7.3, C2). Nothing calls the new
function until Task 3, so no stored byte changes.

**Files:**
- Create: `ai/decisions/ADR306_household_units_in_wayne.yaml`
- Modify: `ai/decisions/index.yaml` (meta lines 2-3; new entry above `ADR305_rule_of_thirds_anchoring_law:`, line 28)
- Modify: `ai/decisions/ADR301_county_review_session.yaml` (R2, R3, `calls`),
  `ADR302_household_roster_and_counting.yaml` (R2, R5, `alternatives_rejected`),
  `ADR305_rule_of_thirds_anchoring_law.yaml` (R2, `verification`)
- Modify: `rust/crates/babylon-practice-contract/src/county_review/types.rs` (`CountyReviewError`: four
  variants after `OpeningReachNotPlaceable`, line 43)
- Modify: `rust/crates/babylon-practice-contract/src/county_review/roster.rs` (new function after
  `opening_roster`, which starts at line 491)
- Test: `rust/crates/babylon-practice-contract/tests/county_review/roster.rs` (add `OpeningCrew`,
  `PositionKey`, `RosterRow` to the import at lines 2-4; add the new tests at the end of the file)

**Interfaces:**
- Consumes: `opening_roster(config: &CountyReviewConfig, crews: &[OpeningCrew], opening_reach: &[(u32, u64)])
  -> Result<Roster, CountyReviewError>` (roster.rs:491); `validate_county_review_config` (:96); the private
  `crews_by_group` (:141), `check_row` (:518) and `place_opening_reach` (:445); the test builders
  `support::{config, open, hand_roster, facts, rows, random_opening, Changes, Rng}` and `base()`/`nine()`
  in `tests/county_review/roster.rs`.
- Produces: the record id `ADR306` with rulings R1 to R16 (cited by Tasks 3 to 10), and:

```rust
// types.rs, CountyReviewError
/// An opening row arrives with households already reached.
OpeningRowReached,
/// A row's band is not one its group's income allows: top 1% or next 9% with a business share,
/// else the other two.
BandOutsideGroup,
/// An opening row bound to a crew has nobody in the labor force.
OpeningCrewRowOutsideLaborForce,
/// An opening row's relief units differ from its people looking for work.
OpeningUnitsNotSeekers,

// roster.rs
pub fn opening_roster_from_rows(
    config: &CountyReviewConfig,
    crews: &[OpeningCrew],
    rows: &[RosterRow],
    opening_reach: &[(u32, u64)],
) -> Result<Roster, CountyReviewError>;
```

**Decisions:**
- *What `opening_roster_from_rows` admits.* **[Call]** It admits a row only if `opening_roster` could make
  a row like it: its band in its group's pair (the pair `band_rows` uses, roster.rs:418-422), a crew for every
  next 40% row (`WageBandOutsideLaborForce`, ADR305 R5), someone in the labor force on every crew row
  (`place_one_each` and `place_crew`, roster.rs:189-266), units equal to seekers (`placed_row`, roster.rs:183),
  nobody reached. It admits a roster only if its sums match the config and the crews. It does not check band
  sizes or the even spread of the placement: those are the pooled law's, applied once in Task 3, and a
  household unit's config cannot repeat them (R4). Reason: Task 3 maps the pooled rows onto unit indices,
  and a mapping fault must be refused by name.
- *The order of refusal is fixed*, so each test pins the first refusal. The checks run in this order:
  `validate_county_review_config`; `crews_by_group` (`DuplicateCrew`, `UnknownCrew`); more rows than
  `COUNTY_REVIEW_MAX_ROWS` (`SizeLimit`); rows sorted and unique (`RosterNotCanonical`); then for each row:
  `reached != 0` (`OpeningRowReached`), `check_row`, the band's pair (`BandOutsideGroup`), a next 40% row with
  no crew (`WageBandOutsideLaborForce`), a crew row with `at_work == 0 && seeking == 0`
  (`OpeningCrewRowOutsideLaborForce`) and `units != seeking` (`OpeningUnitsNotSeekers`); then for each
  ordinary group, households (`GroupHouseholdsMismatch`) and then Σ units × households against `roll_units`
  (`RollMismatch`); then for each configured crew, Σ at work × households and Σ seeking × households against
  its `OpeningCrew`, with 0 for a crew not listed (`RosterEngineMismatch`). Last comes `place_opening_reach`.
  A private helper that builds the `RosterGroup` list is shared with `opening_roster`, and the row checks go
  in a helper, to stay under Clippy's cognitive-complexity limit of 25.
- *What is edited in place.* Only words that units make false are edited (C13; precedents 3854bdeee and
  235cec85f). No ruling is renumbered. ADR269 is merged and is not edited: R14 states its amendment.
  The `related` lists of ADR301, ADR302 and ADR305 stay as they are, and ADR306's own `related` list
  names all three. ADR305 R4's "70,060 of 700,583" is a scope without the aid donors and partners (the
  four budget groups plus the claimants). It is not about units, so it stays.
- *ADR302 R5 says "No split reads an identifier."* The kernel already obeys it: `shrink_group`
  (roster.rs:905-944) sorts one group's crewless keys, which `check_row` forces to at_work = seeking = 0, so
  units or band always decide; `take_level`/`next_level` (roster.rs:780-836) sort one crew's keys by every
  other field; every other split uses `Ties::Withhold`. The only identifier tie is the opening's split among
  units (C8). ADR306 R6 records it, and R5's edit says so (brief B, "the record says so").
- *The proof is a kernel test* over every closing the engine can give a small crew unit. The engine closes with
  `min(households, persons)` (`household_lifecycle/model.rs:169`) and, in the same period, trims the labor force to
  at most the closing eligible (`household_lifecycle/workforce.rs:35-85`). The test also takes one closing the engine
  never gives, to show that the refusal stands.

- [ ] **Step 1: Write ADR306** in the shape of ADR305, with an `open_questions` key as in ADR302:105 (title,
  date `'2026-11-20'`, status `accepted`, issue `PER-369`, evidence_class `Designed`, authority, context,
  decision, calls, alternatives_rejected, open_questions, verification, related). Key
  `ADR306_household_units_in_wayne`. Title: `Give each Wayne household unit its own account, cut once from its
  budget group at the opening`. The `authority` entries quote the Director word for word from design section 2:
  the aim ("to give richness to the "NPC"s and enhance their agency with NPCs being household units and social
  classes"), the direction ("i approve of direction 2 which you chose, with that caveat"), the rule of thirds in
  step A ("Measure now, bind with homes", with the landlord note), and the approval (design 13, item 11). Then
  come ADR302 R1, ADR184 and ADR182. The `decision` block, one paragraph for each ruling:

| Ruling | Exact decision | Source |
|---|---|---|
| R1. THE HOUSEHOLD UNIT. | The households of one Wayne budget group that share one purse, and whose three answers never change: the budget group, the crew their people were bound to at the opening or none, and the band at the opening. It is an account of a kind the engine has (principal, cohort, budget, subject). No new kind of account. | 7.1 [Record needed] |
| R2. IDENTITY. | principal = SHA-256(`NationalHouseholdUnitV1\0` ‖ group principal bytes ‖ pooled opening member id bytes, or 32 zero bytes with no crew ‖ band byte: top 1% 1, next 9% 2, next 40% 3, bottom 50% 4). The unit with the most households keeps the group's own account. A tie goes to the lower band, then to the unit with no crew, then the build refuses by name. | 7.1, 7.2 [Call]; C4 |
| R3. ONE PURSE, OWN FIGURES. | A household's labor figures are its position's. Its money is its unit's. A unit pays or buys for as many households as its cash covers, and the rest go without (ADR302 R1, third rule). A figure "for each household" is a rate of two of the unit's totals (the second rule). | 5 [Call][Record needed]; 7.1 [Call] |
| R4. ONE PLACEMENT, RUN ONCE. | The County Review's placement runs once, on the pooled groups, inside the opening build and before money is wired. Each distinct (group, crew, band) of a splittable group is a unit. The opening keeps the rows. At capture the roster is made from them by `opening_roster_from_rows` and is never placed again, because placing again would move households between bands. Law: `from_rows(c, k, opening_roster(c, k, [])·rows, r) = opening_roster(c, k, r)`. | 7.2 [Record needed]; C3, C5 |
| R5. NAMED GROUPS WHOLE. | The claimants, the aid donors, the aid partners and collective residence each stay one unit, with accounts, members and employment rows untouched, even in two bands. Their positions keep their bands. A figure by band divides the unit's total by households, by largest remainder. This replaces the first form, which refused today's Wayne. | 7.1 [Call]; C1 |
| R6. THE OPENING SPLIT. | Cash, goods, needs and support follow the engine's formulas on the unit's counts. Persons = labor force + a households-share of the other adults and of the children, by largest remainder; eligible = labor force + other adults. A unit with fewer persons than households refuses the campaign by name. A crew in two bands becomes two members (same site, labor unit and pay mode), with the unit as payee. Business shares and ages split in two stages: to groups as today, then to units by households. Order of every split: band from the bottom 50% up, no crew first, more households, more labor force, and as the last tie only, the canonical order of the pooled member id. The other units of a selected group join the detail. | 7.2 [Call]; C8 |
| R7. WHAT THE COUNTS DO NOT EXPLAIN. | The unit that keeps the group's account keeps the remainder: its cash and each stock are the pooled seed's figure less the other units' formula figures, refused if negative (the aid recipient's endowment kept at its parent). | 7.2 [Call]; C4 |
| R8. WAYNE ONLY, ON ASKING. | Units exist only under a policy's `[household_units]` for the County Review's county. It compiles as `national-world-v13`. Every earlier compiler gives the same bytes, and `grain = "group"` gives the pooled opening value for value. | 7.1 [Call]; C7 |
| R9. THE ORDER OF GOING WITHOUT. | A short unit pays for food, materials, utility, housing, household services and public provision, in that order, by its own ranked buying rule; storable goods before services. Buying food and materials includes refilling the pantry. | 7.3 [Call][Record needed] |
| R10. TAX COLLECTED LAST. | As today. The list ranks a household by the wage tax collected from its own unit. A unit that spent its cash on needs stands lower, recorded as "ranked lower: tax not collected". | 7.3, 7.4 |
| R11. A HOUSEHOLD THAT LEAVES. | ADR302 R4(6) and R7 stand. Proof: a unit closes at min(households, persons), and its labor force is cut in the same period to at most the closing eligible. Each crew row holds someone in the labor force (refused by name at the opening otherwise), so crew households ≤ labor force ≤ closing households, and crewless households ≥ leavers. `HouseholdsBelowLaborHouseholds` stands. Nothing is clamped. | 7.3 [Call][Record needed]; C2 |
| R12. THE COUNTY REVIEW ON UNITS. | Each unit is a County Review group: its own collected tax over its own taxed wages, its own free hours, its own support line. Its facts gain its purse: closing cash, net assets from its capital account, wage tax assessed, and for each need the amounts required, unmet, unpaid and unsupplied and the cost. Went without = ceil(unmet × households / required). | 7.4; C10 |
| R13. WHAT IS PUBLIC. | Public: the counts of who went without (by need, band and unit), the one sentence for each unit, each band's share of household wealth in basis points adding to 10,000, and each band's ownership pay as a share of the cost of its needs. Dollar figures of a unit are earned by contact (ADR182). | 7.5; C11 [Call] |
| R14. WORDS. | On screen, "household unit" for the new object and "relief unit" for the county's support. Budget groups read "with a business share" and "no business share", and "owner" is kept for homes. Stored field names do not change. This amends ADR269's word on screen only. Its "private-owner exposure" keeps its engine meaning, and the rest of ADR269 stands. | 7.1 [Call]; C12; design 8 |
| R15. THE LAW IN STEP A. | The thirds are measured band by band in step A and bind step B's opening, with homes. This amends ADR305 R2. | 7.2 [Director] |
| R16. THE RECORDS. | Amends ADR301 R2 and R3, ADR302 R2 and R5, and ADR305 R2 in place (they are unmerged), and ADR269 by R14. ADR208 R9 is applied, not amended. | 8; C13 |

  `calls`: one entry for each [Call] above (R2, R3, R5, R6, R7, R8, R9, R11, R13, R14), with its design section
  in the form `'... (design 7.2).'`. `alternatives_rejected`: a ledger inside the pooled account (6); a unit for
  every position (6); refusing an opening that cuts a named group (7.1, first form); placing again on units at
  capture (7.2); a new rule that takes leavers from crew rows (7.3, first form); cutting every need in
  proportion, and need first with the pantry last (7.3); taking wage tax when the wage is paid (7.3); dollars by
  band, because the top 1% is one unit (C11); binding the thirds at step A's opening (7.2). `open_questions`:
  (1) a short seller serves its buyers in `order_id` order (`babylon-material-circuit/src/services/close.rs:174`,
  `sell_grants`; goods through the order book). With units, that order can decide which unit goes without. Step A
  keeps it and records "could not pay" apart from "paid and was not supplied". Does the Director want another
  rule before step B? (2) If Task 4's report shows the top 1% unit going without, does the division of the shares
  between the top 1% and the next 9% move into step A by a small amendment (7.2, 12)? (3) The three "Corrected
  after approval" statements, for the Director to check (design 13). `verification`: the law and the leaving proof
  in the kernel (this task); the add-back of 7.6 and `grain = "group"` (Task 4); the tick test of R11 (Task 5);
  the recorded playthroughs (Task 8). `related`: ADR182_derivation_inspector_rulings,
  ADR184_capacity_belongs_to_organizations, ADR208_docket_sitting_2026_08_17, ADR269_sparse_household_budgets,
  ADR300_amendment_am_no_imposed_functional_form, ADR301_county_review_session,
  ADR302_household_roster_and_counting, ADR305_rule_of_thirds_anchoring_law.
- [ ] **Step 2: Index.** Above line 28 add `ADR306_household_units_in_wayne:` with `title` (as above), `status:
  accepted`, `date: '2026-11-20'` and `file: ADR306_household_units_in_wayne.yaml`. Set `version: 1.99.0` and
  `updated: '2026-11-20'`.
- [ ] **Step 3: Edit the three records in place.** Re-wrap each block at its width.

| Record, place (HEAD) | Current words | New words |
|---|---|---|
| ADR301 R2, line 46 | by the wage tax that household paid on its own wage | by the wage tax that household paid on its own wage, counted at the rate collected from its own household unit where the campaign has household units (ADR306) |
| ADR301 R3, line 56 | asks only if its budget group has two | asks only if its household unit, or its budget group in a campaign without units, has two |
| ADR301 calls, line 117 | 'A household asks only if its budget group has two free hours | 'A household asks only if its household unit, or its budget group in a campaign without units, has two free hours |
| ADR302 R2, lines 30-31 | A position is one budget group's households bound to one crew, | A position is one group's households bound to one crew, where a group is a budget group or, in a campaign that has them, a household unit (ADR306), |
| ADR302 R2, line 33 | A crew is one budget group's people at one workplace, | A crew is one group's people at one workplace, |
| ADR302 R5, line 60 | No split reads an identifier. | No split of the roster reads an identifier. The opening's split of a budget group among its household units takes the canonical order of the pooled crew's member id as its last tie only (ADR306 R6). |
| ADR302 alternatives_rejected, line 104 | It belongs to a later slice. | Household units hold cash and stock instead, and a position is a row inside a unit (ADR306). |
| ADR305 R2, lines 49-51 | They bind the opening split of a county's household wealth in the next slice, when positions hold accounts of their own. | They bind the opening split of a county's household wealth at the opening of the next slice's step B, when household units hold homes. Step A gives household units accounts of their own and measures each band's share beside the law, by the Director's ruling of 2026-11-20, "Measure now, bind with homes" (ADR306 R15). |
| ADR305 verification, lines 91-92 | Next slice: the opening contract splits wealth by R1 with its source named, | Next slice: step A measures each band's share beside R1 (ADR306); step B's opening contract splits wealth by R1 with its source named, |

- [ ] **Step 4: Verify the records.** `cd /media/user/dev-ssd/worktrees/households-homes/babylon && mise run
  check:adr-catalog` prints `"status":"ok"` with no `index-status-conflict`; `mise run check:governance-mass`
  prints `governance-mass: ok`; `PYTHONPATH=src mise exec -- uv run --frozen pre-commit run --files
  ai/decisions/ADR30[1256]*.yaml ai/decisions/index.yaml` passes.
- [ ] **Step 5: Commit** the five YAML files as `docs(decisions): record household units in Wayne (ADR306)`.
- [ ] **Step 6: Write the failing kernel tests** at the end of `tests/county_review/roster.rs` (the layout
  below is compact; Step 8 formats it):

```rust
type Edit<'a> = dyn FnOnce(&mut CountyReviewConfig, &mut Vec<OpeningCrew>, &mut Vec<RosterRow>) + 'a;
fn from_rows_base() -> (CountyReviewConfig, Vec<OpeningCrew>, Vec<RosterRow>) {
    let (c, r) = base(); // 4 households, roll 3, E = 6, S = 3
    (c, vec![support::open(0, 6, 3)], r.rows)
}
fn edited(edit: Box<Edit<'_>>) -> Result<Roster, CountyReviewError> {
    let (mut c, mut k, mut rows) = from_rows_base();
    edit(&mut c, &mut k, &mut rows);
    practice_contract::opening_roster_from_rows(&c, &k, &rows, &[])
}
#[test]
fn from_rows_gives_the_opening_roster_with_its_reach() {
    let (c, k, rows) = from_rows_base();
    let reaches: [&[(u32, u64)]; 4] = [&[], &[(0, 3)], &[(0, 2)], &[(0, 5)]];
    for reach in reaches {
        let law = practice_contract::opening_roster(&c, &k, reach);
        assert_eq!(practice_contract::opening_roster_from_rows(&c, &k, &rows, reach), law);
    }
    let r = practice_contract::opening_roster_from_rows(&c, &k, &rows, &[(0, 3)]).expect("opens");
    let want = vec![((0, B50, Some(0), 1, 1, 1), 2, 1), ((0, N40, Some(0), 2, 0, 0), 1, 1),
        ((0, N40, Some(0), 2, 1, 1), 1, 1)];
    assert_eq!(support::rows(&r), want);
}
#[test]
fn from_rows_obeys_the_law_on_random_openings() {
    let (mut rng, mut accepted, mut attempts, mut opened) = (Rng(0x2545_f491_4f6c_dd1d), 0, 0, 0);
    while accepted < 200 {
        attempts += 1;
        assert!(attempts < 200_000, "the law accepted too few random openings");
        let Some((c, k, _)) = support::random_opening(&mut rng) else { continue };
        accepted += 1;
        let reach: Vec<(u32, u64)> = c.groups.iter().enumerate()
            .filter(|(_, g)| g.kind == GroupKind::Ordinary)
            .map(|(i, g)| (u32::try_from(i).expect("small"), rng.up_to(g.opening_households / 4)))
            .collect();
        let pooled = practice_contract::opening_roster(&c, &k, &[]).expect("opens without reach");
        let law = practice_contract::opening_roster(&c, &k, &reach);
        opened += usize::from(law.is_ok());
        assert_eq!(practice_contract::opening_roster_from_rows(&c, &k, &pooled.rows, &reach), law);
    }
    assert!(opened > 0, "some random reach must place");
}
#[test]
fn from_rows_keeps_the_pooled_bands_when_a_group_is_cut_into_units() {
    let (_, pooled) = nine(); // the crew of nine() lies in two bands: it becomes crews 0 and 1
    let units = support::config(&[(3, 0, false), (2, 2, false), (4, 0, false)], &[1, 2]);
    let held = support::hand_roster(&units, &[((0, B50, None, 0, 0, 0), 3, 0),
        ((1, B50, Some(0), 0, 1, 1), 2, 0), ((2, N40, Some(1), 1, 0, 0), 4, 0)]);
    let crews = [support::open(0, 0, 2), support::open(1, 4, 0)];
    let r = practice_contract::opening_roster_from_rows(&units, &crews, &held.rows, &[]).expect("opens");
    assert_eq!(r, held);
    assert_eq!(r.band_counts(), pooled.band_counts());
}
fn refused(edit: Box<Edit<'_>>, error: CountyReviewError) { assert_eq!(edited(edit), Err(error)); }
#[test]
fn from_rows_refuses_rows_the_opening_never_makes() {
    use CountyReviewError as E;
    refused(Box::new(|_, _, r| r[0].reached = 1), E::OpeningRowReached);
    refused(Box::new(|_, _, r| r.reverse()), E::RosterNotCanonical);
    refused(Box::new(|_, _, r| r[0].key.crew = None), E::CrewlessRowInLaborForce);
    refused(Box::new(|c, _, _| c.groups[0].has_ownership_income = true), E::BandOutsideGroup);
    refused(Box::new(|_, _, r| r[1].key.units = 1), E::OpeningUnitsNotSeekers);
}
fn insert(c: &mut CountyReviewConfig, r: &mut Vec<RosterRow>, at: usize, key: PositionKey) {
    c.groups[0].opening_households = 5;
    r.insert(at, RosterRow { key, households: 1, reached: 0 });
}
#[test]
fn from_rows_refuses_a_crewless_household_in_the_next_forty() {
    let k = PositionKey { band: N40, crew: None, at_work: 0, seeking: 0, units: 0, ..from_rows_base().2[0].key };
    let e = edited(Box::new(move |c, _, r| insert(c, r, 1, k)));
    assert_eq!(e, Err(CountyReviewError::WageBandOutsideLaborForce));
}
#[test]
fn from_rows_refuses_a_crew_row_with_nobody_in_the_labor_force() {
    let k = PositionKey { band: B50, crew: Some(0), at_work: 0, seeking: 0, units: 0, ..from_rows_base().2[0].key };
    let e = edited(Box::new(move |c, _, r| insert(c, r, 0, k)));
    assert_eq!(e, Err(CountyReviewError::OpeningCrewRowOutsideLaborForce));
}
#[test]
fn from_rows_refuses_a_roster_whose_sums_miss_the_config() {
    use CountyReviewError as E;
    refused(Box::new(|_, _, r| r[0].households = 3), E::GroupHouseholdsMismatch);
    refused(Box::new(|c, _, _| c.groups[0].roll_units = 4), E::RollMismatch);
    refused(Box::new(|_, k, _| k[0].at_work = 7), E::RosterEngineMismatch);
    refused(Box::new(|_, k, _| k[0].seeking = 4), E::RosterEngineMismatch);
    refused(Box::new(|_, k, _| k.clear()), E::RosterEngineMismatch);
    refused(Box::new(|_, k, _| k.push(k[0])), E::DuplicateCrew);
    refused(Box::new(|_, k, _| k[0].crew = 1), E::UnknownCrew);
}
#[test]
fn a_household_that_leaves_a_crews_unit_never_needs_a_crew_row() {
    // one unit: 3 households of one crew in the next 40%, E = 3, S = 2, roll 2, nobody outside the labor force
    let c = support::config(&[(3, 2, false)], &[0]);
    let held = support::hand_roster(&c, &[((0, N40, Some(0), 1, 0, 0), 1, 0), ((0, N40, Some(0), 1, 1, 1), 2, 0)]);
    let crews = [support::open(0, 3, 2)];
    let r = practice_contract::opening_roster_from_rows(&c, &crews, &held.rows, &[]).expect("opens");
    for left_at_work in 0..=3 {
        for left_seeking in 0..=2 {
            let force = (3 - left_at_work) + (2 - left_seeking); // the labor force the engine leaves
            for closing in force.min(3)..=3 { // min(households, persons), and persons >= force
                let changes = Changes { left_at_work, left_seeking, ..Changes::default() };
                let f = support::facts(&c, &r, &[(0, changes)], &[closing]);
                let next = practice_contract::roll_forward(&c, &r, &f)
                    .expect("a leaver always finds a household with nobody in the labor force");
                assert_eq!(next.groups[0].households, closing);
                assert_eq!((next.crew_at_work(0), next.crew_seeking(0)), (3 - left_at_work, 2 - left_seeking));
                assert_eq!(next.group_units(0) + next.groups[0].departed_units, 2);
            }
        }
    }
    let gone = Changes { left_at_work: 3, ..Changes::default() }; // force 2; a closing of 1 the engine never gives
    let f = support::facts(&c, &r, &[(0, gone)], &[1]);
    assert_eq!(practice_contract::roll_forward(&c, &r, &f), Err(CountyReviewError::HouseholdsBelowLaborHouseholds));
}
```

- [ ] **Step 7: Run.** `cd /media/user/dev-ssd/worktrees/households-homes/babylon && mise run rust:test:q -- -p
  babylon-practice-contract -E 'binary(county_review) & (test(from_rows) | test(leaves_a_crews_unit))'`. Expected:
  a compile failure, because `opening_roster_from_rows` and the four variants do not exist.
- [ ] **Step 8: Implement** the four variants in `types.rs` and `opening_roster_from_rows` in `roster.rs`. The
  doc comment states the law of R4, lists the refusals in the order the Decisions give, and says, in the
  Decisions' words, what it admits and that it does not check band sizes. The function returns
  `Roster { period: 0, groups, rows }`, with `groups` built exactly as `opening_roster` builds them (households
  of an ordinary group, 0 for collective residence, `departed_units: 0`) and the reach placed by
  `place_opening_reach`. Then, from `rust/`, run `mise exec -- cargo fmt --all` to format the new code and tests.
- [ ] **Step 9: Run** the command of Step 7. Expected: 9 tests PASS (each refusal pinned by its own assertion,
  15 refusals and laws in all). Then the scoped gate, from `rust/`: `mise exec -- cargo fmt --all -- --check`;
  `mise exec -- cargo clippy --workspace --all-targets --locked -- -D warnings -D clippy::cognitive_complexity`;
  then `mise run rust:test:q -- -p babylon-practice-contract`. Expected: PASS, with the 88 existing County Review
  tests unchanged. Then, from `rust/`, run `mise exec -- cargo run -p bsl-lint --locked -- all` once (`mise run
  check:bsl-sentinels`): it checks ADR306 against `index.yaml` and the new Rust against the style sentinel.
- [ ] **Step 10: Commit** `types.rs`, `roster.rs` and `tests/county_review/roster.rs` as `feat(county-review): make
  the opening roster from the opening's rows`.

### Task 3: The opening: units, splits and the new compiler

Design 7.1 and 7.2 (the unit, the opening) and 7.18 (one new compiler). C3, C4, C6, C7 and C8. The build
divides each Wayne budget group into household units once, inside `Builder::finish`. The County
Review then builds its roster from the opening's rows and does not place them again. A policy without
`[household_units]` compiles as v12 and keeps every byte.

**Files:**
- Create: `rust/crates/babylon-persistence/src/national_economy/opening/household_units.rs`
- Modify `rust/crates/babylon-persistence/src/national_economy/`:
  - `policy/game.rs`: `NationalGamePolicy`, plus the new types.
  - `policy/admission.rs`: `RawPolicy`, `parse` (the literal at :360), `validate_globals` (:641).
  - `policy.rs` and `../national_economy.rs`: the two `pub use` lists.
  - `identity.rs`: `household_unit_principal`.
  - `opening.rs`: `mod household_units;` and its `pub use`.
  - `opening/build.rs`: `Builder`, `Builder::new` (literal at :341), `Builder::finish` (a call after
    `aid::fund` at :273), `NationalOpening` and its literal (:302).
  - `opening/actors.rs` (`household_identity`, :187), `opening/household_time.rs` (`eligibility`, :102).
  - `opening/financial.rs`: `PrivateOwners` (:188), `private_owners` (:290), `private_claims` (:310).
  - `opening/lifecycle.rs` (`pushforward`, :78), `opening/detail.rs` (`partition`, the loop at :39).
  - `county_review.rs`: `CountyReviewCapture` (:91), `group_label` (:132), `groups` (:221),
    `assemble` (the `opening_roster` call at :519).
- Modify: `rust/crates/babylon-persistence/src/national_resident_allocation/allocation.rs` (`member`, :401)
- Modify `rust/crates/babylon-persistence/src/economic_catalog/`: `capture.rs` (`compiler_for` at :486,
  its experiment arm at :521, `assemble_county_review` at :447 (the `CountyReviewCapture` literal at
  :469), a new accessor), `national.rs` (`NationalSources` and its literal at :110), `codec.rs`
  (:20-23), `preset.rs` (`from_compiler`, :11)
- Modify: `content/scenarios/national/defines.toml` (the section is appended at the end),
  `contracts/economic_catalog_v1.yaml` (:28-29, :77-80 and a `national_household_units` entry)
- Test (in `rust/crates/babylon-persistence/`): `tests/national_game_policy.rs`,
  `tests/national_household_units.rs` (Task 1's binary), `tests/support/company_scale.rs`,
  `tests/support/national_household_controls.rs`, the v12 pins listed in Step 4,
  `src/national_economy/opening/household_units.rs` (`#[cfg(test)]`)

**Interfaces:**
- Consumes: Task 2's `opening_roster_from_rows` (C5). Also these existing functions: `pub(crate) fn
  apportion(total: u64, weights: &[u64]) -> Result<Vec<u64>>` (allocation.rs:441, largest remainder,
  ties to the lower index) and `pub fn opening_roster(config: &CountyReviewConfig, crews:
  &[OpeningCrew], opening_reach: &[(u32, u64)]) -> Result<Roster, CountyReviewError>`.
- Produces (names from C4, C6 and C7, plus the additions marked in Decisions):

```rust
// policy/game.rs
pub struct GameHouseholdUnitsPolicy { pub county: [u8; 5], pub grain: HouseholdUnitGrain,
                                      pub going_without: Option<Vec<String>> }
pub enum HouseholdUnitGrain { Group, Unit }                 // Debug, Clone, Copy, PartialEq, Eq
// NationalGamePolicy: pub household_units: Option<GameHouseholdUnitsPolicy>, after county_review
// identity.rs
pub(super) fn household_unit_principal(group: FinalDemandPrincipalId,
    opening_member: Option<StaffingMemberId>, band: Band) -> FinalDemandPrincipalId;
// household_units.rs: C6's three structs (Clone, Debug, PartialEq, Eq; no serde derive, the ids
// do not implement Serialize; Task 4's recorder writes serde_json::json! with hex ids), and:
//   OpeningHouseholdUnit   gains pub opening_member: Option<StaffingMemberId>  (the pooled crew)
//   OpeningHouseholdUnitRow gains pub member: Option<StaffingMemberId>         (the row's crew)
pub enum HouseholdUnitRefusal { Placement(CountyReviewError), KeeperTie { group: FinalDemandPrincipalId },
    FewerPersonsThanHouseholds { household_unit: FinalDemandPrincipalId },
    EndowmentShort { group: FinalDemandPrincipalId }, NoEmploymentTerms { member: StaffingMemberId } }
pub(super) struct HouseholdUnitCounts { pub principal: FinalDemandPrincipalId, pub households: u64,
                                        pub labor_force: u64 }
pub(super) fn divide(builder: &mut Builder<'_>, time_controls: &NationalHouseholdTimeAllocation) -> Result<()>;
pub(super) fn split_persons(persons: u64, eligible: u64, household_units: &[HouseholdUnitCounts])
    -> Result<Vec<(u64, u64)>>;                              // (persons, eligible), in C8 order
impl OpeningHouseholdUnits { pub fn of_group(&self, group: FinalDemandPrincipalId) -> Vec<&OpeningHouseholdUnit>; }
// build.rs: NationalOpeningError::HouseholdUnits(HouseholdUnitRefusal); the household_units field on Builder
// (pub(in crate::national_economy)) and on NationalOpening (pub(crate)), as C6 gives them
// actors.rs, extracted from household_identity, which calls it (bytes unchanged)
pub(super) fn household_endowment(builder: &Builder<'_>, kind: HouseholdKind, persons: u64,
    households: u64, price_scale_bps: u16) -> Result<(Vec<OpeningCommodityStock>, Currency)>;
// allocation.rs: the id preimage and the "member-<base32(id)>" subject member() builds today;
// member() calls it, and each new unit member is made with it
pub(crate) fn member_at(site_id: SiteId, location: EconomicLocation, mode: ResidentAttendanceMode,
    principal: FinalDemandPrincipalId, employed: u64, reserve: u64) -> Result<AssignedResidentMember>;
// capture.rs
impl CapturedEconomicCatalog { pub fn national_household_units(&self) -> Option<&OpeningHouseholdUnits>; }
// codec.rs: pub(super) const COUNTY_REVIEW_COMPILERS: [&str; 2] = ["national-world-v12", "national-world-v13"];
```

**Decisions:**
- *Commits.* (a) policy and v13; (b) `household_units.rs`, identity, persons, cash and stock, members
  and terms, the builder maps, and the ages; (c) the two-stage shares and the detail selection; (d)
  the roster from the opening's rows, the v13 labels, and the shipped grain set to `"unit"`. The ages
  move into (b) because `lifecycle::wire` refuses a county seed with no ages
  (`domestic.remove(..).ok_or(Error::Identity)`, lifecycle.rs:192). Without them no unit opening
  builds. From (a) to (c) the shipped file says `grain = "group"`, because until (d) the capture
  places the unit groups again (county_review.rs:519) and could not reproduce the bands.
- *The section's place.* It goes after `[county_review]`, as `\n[household_units]\n`, with its comment
  lines after the header and no double quotes in them. Cutting the text at `"\n[household_units]\n"`
  then gives today's bytes exactly, and the tests that cut at earlier markers keep working.
- *Admission.* The `validate_globals` tuple gains `raw.household_units.is_some()`. The arms are today's
  five with `false` appended, plus `(7, true, true, true, true, true, true)`. The section without
  `[county_review]` is `Error::Shape`. The other refusals are: evidence `Error::Evidence`; a county
  other than the County Review's `Error::Profile("household units county")`; a grain other than
  `group`/`unit` `Error::Profile("household units grain")`; an order whose length is not the number
  of needs `Error::Profile("household units order of going without")`; an unknown or repeated key,
  or a storable good after a service, `Error::HouseholdNeed(<that key>)`. The grain is a `String`
  in `RawHouseholdUnits` (`deny_unknown_fields`), so a bad grain is a typed refusal and not `Syntax`.
- *The experiment preset* gets `&& policy.household_units.is_none()` on its arm, so it falls to
  `Err(Identity)`. `support/company_scale.rs` `capture` cuts the section when it adds
  `experiment_controller_count`. v13 frames the county footer exactly as v12 does. No new footer.
- *Named groups* [Call] (C1). These are the claimant, the aid children located in the county, and the
  collective residence. Each is one unit with `group == principal`, holding all its rows, and its
  seed, members and terms are not touched. Every other ordinary seed of the county is split. A
  unit's `member` is `Some(m)` when every row of the unit is a row of crew `m`, and `None` otherwise.
- *The pooled config* (C3) carries only what placement reads. `divide` runs before `financial::wire`,
  so it reads no support line or ownership claim. Its `schema_version` is
  `COUNTY_REVIEW_SCHEMA_VERSION`. Its terms are `campaign_id [0; 16]`, `actor_id 0`, `authority_id
  [0; 16]`, empty labels, `public_account_id [0; 32]` and `content_digest [0; 32]`, with
  `unit_price_micros = county_support_unit_price(policy)`, `going_wage_micros = policy.default_wage`
  and the `[county_review]` session and bring hours. Its groups are the county's seeds sorted by
  principal, each with kind and `opening_households` as `groups()` gives them (:163); `roll_units` =
  Σ `member.reserve` over the staffing members bound to the seed (the figure `financial::wire` turns
  into support at financial.rs:19-30); `has_ownership_income = household_keys[p].owner_exposure()`;
  `receives_mutual_aid = (p == aid.children[1].principal)`. `crews()`'s rules (:230) give the crews:
  members of ordinary groups only, and a member with people but no term is refused
  `NoEmploymentTerms`. The placement is `opening_roster(&pooled, &crews, &[])`.
- *C8 order* sorts on the key `(band, member.is_some(), Reverse(households), Reverse(labor_force),
  opening_member)`. A unit's labor force is Σ (at_work + seeking) × households over its rows. Every
  split among a group's units lists them in that order and calls `apportion`, so ties go to the
  earlier unit. The kernel's `split::apportion` is not used, because it refuses a total larger than
  its weights (other adults can outnumber households).
- *Persons, cash, stock* (C4, C8). The group's eligible is `household_time::eligibility(..)` (made
  `pub(super)`), and its labor force is Σ `labor_force()` of the members bound to it. The keeper
  keeps the group's principal, subject and the remainder of its cash and of each stock. Every other
  unit gets `household_endowment(.., 10_000)`; 10,000 is the scale `domestic_households` uses
  (actors.rs:583). The subject is `principal_subject(principal)`: the graph has one node per seed
  subject (economic_catalog/graph.rs:118), so only the template and the kind are copied.
- *Members* (C8). Each unit member is `member_at(site, builder.actors[site].location, mode,
  unit.principal, employed, reserve)`. The mode comes from the term's `LaborCompensation`, and the
  residence is the pooled member's. The keeper's crew therefore keeps its pooled id. Pooled members
  and terms whose id is no longer used are removed. The new terms copy the site, labor unit and
  compensation, with `payee` set to the unit. Pool members are sorted again by `member_id`.
- *Shares* (C8). `PrivateOwners` becomes `BTreeMap<FinancialDomainId, Vec<OwnerGroup { group,
  households, units: Vec<(FinalDemandPrincipalId, u64)> }>>`. Groups are sorted by group principal
  and units are in C8 order. A row that is not a unit is a group of one, so every other county
  keeps its bytes. Stage 1 runs `apportion` over the group households, stage 2 over the unit
  households. The change lives in `private_claims`, so both call sites in `ownership` (:218 and
  :229) and, through them, the company weights follow.
- *Ages* (C8). In `pushforward`, when the opening holds more than one unit with `group ==
  parent.destination`, the ages this call gives `parent.destination` (in either branch, :120 or
  :125) are split again with `split` over those units. The units are in C8 order, with `Exposure
  { eligible, under_16: persons - eligible }`.
- *Detail.* Every unit whose `group` is in `selection.household_principals` is added before the
  employment loop at detail.rs:39, so the foreground workplaces stay the ones they are today.
- *Capture* [Call]. Under v13 `groups()` sets `has_ownership_income` from
  `household_keys[p].owner_exposure()`, not from ownership rows. The opening placed its bands with
  `has_ownership_income = owner_exposure()` (C3), so the capture reads the same fact and does not
  depend on how the shares rounded. Under v13, `assemble` turns each unit row into `RosterRow {
  key: PositionKey { group: <index of unit.principal>, band, crew: <index of row.member>, at_work,
  seeking, units: relief_units }, households, reached: 0 }`. The rows are sorted by key, and
  `assemble` calls `opening_roster_from_rows(&config, &people, &rows, &reach)` for both grains.
  Earlier compilers keep `opening_roster`.
- *Labels* (C12). When `policy.household_units.is_some()`, `group_label` writes "earning, no business
  share", "earning, with a business share", "no earner, no business share", "no earner, with a
  business share" and "collective residence", plus today's role suffix. `PooledExternal` is
  `UnnamedGroup`.

- [ ] **Step 1: Write the failing policy test** in `tests/national_game_policy.rs` (`use
  babylon_persistence::national_economy::{HouseholdUnitGrain, NationalGamePolicyError as Error}`):

```rust
fn with_units(edit: impl Fn(&str) -> String) -> String {
    let (head, units) = SOURCE.split_once("\n[household_units]\n").expect("the section is last");
    format!("{head}\n[household_units]\n{}", edit(units))
}
#[test]
fn household_units_terms_are_designed_optional_and_bound_to_the_county_review() {
    let terms = NationalGamePolicy::parse(SOURCE).expect("shipped").household_units.expect("section");
    assert_eq!((terms.county, terms.grain), (*b"26163", HouseholdUnitGrain::Group)); // Unit from Step 14
    let order = ["food", "materials", "utility", "housing", "household_services", "public_provision"];
    assert_eq!(terms.going_without, Some(order.map(String::from).to_vec()));
    let (v12, _) = SOURCE.split_once("\n[household_units]\n").expect("the section is last");
    assert_eq!(NationalGamePolicy::parse(v12).expect("schema 7 without it").household_units, None);
    let unordered = with_units(|t| t.replacen(&format!("going_without = {order:?}\n"), "", 1));
    assert_eq!(NationalGamePolicy::parse(&unordered).expect("order optional")
        .household_units.expect("section").going_without, None);
    let review = SOURCE.find("\n# The county review.").expect("the county review's comment");
    let no_review = format!("{}{}", &SOURCE[..review], &SOURCE[SOURCE.find("\n[household_units]\n").unwrap()..]);
    assert_eq!(NationalGamePolicy::parse(&no_review), Err(Error::Shape));
    for (changed, refusal) in [
        (with_units(|t| t.replacen("\"Designed\"", "\"Observed\"", 1)), Error::Evidence),
        (with_units(|t| t.replacen("\"26163\"", "\"26125\"", 1)), Error::Profile("household units county".into())),
        (with_units(|t| t.replacen("grain = \"", "grain = \"x", 1)), Error::Profile("household units grain".into())),
        (with_units(|t| t.replacen(", \"public_provision\"", "", 1)),
         Error::Profile("household units order of going without".into())),
        (with_units(|t| t.replacen("\"public_provision\"", "\"food\"", 1)), Error::HouseholdNeed("food".into())),
        (with_units(|t| t.replacen("\"public_provision\"", "\"rent\"", 1)), Error::HouseholdNeed("rent".into())),
        (with_units(|t| t.replacen("\"materials\", \"utility\"", "\"utility\", \"materials\"", 1)),
         Error::HouseholdNeed("materials".into())),
    ] {
        assert_ne!(changed, SOURCE);
        assert_eq!(NationalGamePolicy::parse(&changed), Err(refusal));
    }
}
```

  `format!("{order:?}")` prints `["food", "materials", ...]`, which is the TOML line's array.

- [ ] **Step 2: Write the failing compiler tests** in `tests/national_household_units.rs`. Each test
  captures what it reads through `OnceLock` helpers (nextest runs one process per test, so a static
  only spares repeated captures within one test); Task 1's helper is reused if it exists. Keep the
  tests that capture both policies to the ones listed. The text is edited the way
  `tests/national_company_capture.rs:52-63` edits it: take the `SourceKind::NationalGamePolicy`
  source from `economic_catalog::national_catalog_input()`, edit it, and replace it with
  `SourceArtifact::capture(kind, bytes)`.

```rust
static V12: OnceLock<CapturedEconomicCatalog> = OnceLock::new();
fn campaign() -> CampaignId { CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7036)) }
fn with_policy(edit: impl FnOnce(&str) -> String) -> EconomicCatalogInput { /* as above */ }
fn v12() -> &'static CapturedEconomicCatalog {
    V12.get_or_init(|| CapturedEconomicCatalog::capture_national_campaign(
        with_policy(|t| t.split_once("\n[household_units]\n").expect("last").0.to_owned()), campaign())
        .expect("a v12 campaign"))
}
#[test]
fn a_policy_without_household_units_compiles_and_reopens_as_v12() {
    assert_eq!(v12().compiler_version(), "national-world-v12");
    let reopened = CapturedEconomicCatalog::decode(v12().canonical_bytes(), v12().digest())
        .expect("a saved v12 catalog reopens");
    assert_eq!(reopened.compiler_version(), "national-world-v12");
}
#[test]
fn the_experiment_preset_refuses_household_units() {
    let mut input = with_policy(|t| t.replacen("[companies]", "[companies]\nexperiment_controller_count = 300", 1));
    "national-company-scale-experiment".clone_into(&mut input.preset_id);
    assert!(matches!(CapturedEconomicCatalog::capture(input, None), Err(EconomicCatalogError::Identity)));
}
```

- [ ] **Step 3: Run** `mise run rust:test:q -- -p babylon-persistence -E 'binary(national_game_policy)
  & test(household_units)'`, then the same for `binary(national_household_units) & (test(v12) |
  test(experiment))`. Expected: `national_game_policy` fails to compile (no `household_units`
  field, no `HouseholdUnitGrain`); `national_household_units` fails at run time (the v12 test
  panics `last`; the experiment capture returns `Ok`).
- [ ] **Step 4: Implement (a).** Append to `defines.toml`:

```toml

[household_units]
# Household units in Wayne (ADR306): the households of a budget group that share one purse. The
# group grain keeps one unit for each budget group; the unit grain divides each group at the opening.
evidence_class = "Designed"
county = "26163"
grain = "group"
going_without = ["food", "materials", "utility", "housing", "household_services", "public_provision"]
```

  Then make these code changes:
  - The game, admission and export changes listed under Decisions.
  - In `compiler_for`, the first arm is `CompanyConditionOrder::FirstApplicable if
    policy.household_units.is_some() => "national-world-v13"`. Add the experiment guard.
  - `from_compiler` gains `"national-world-v13"`.
  - `frames_county_review` returns `COUNTY_REVIEW_COMPILERS.contains(&compiler)`.
  - `company_scale.rs` cuts the section.
  - The contract YAML lists v13, the `national_identity` compiler v13, the footer "under
    national-world-v12 and national-world-v13", and a `national_household_units` entry. That entry
    says: the optional section of schema 7 compiles as v13; earlier policies keep their opening.

  The pins that name v12 all become `"national-world-v13"`:
  - `tests/captured_economic_catalog.rs:38` and `:40`
    (`capture_retains_sources_once_and_regenerates_the_exact_native_opening`). The truncation of 5
    stays, and `v10`/`v18` still refuse.
  - `tests/captured_national_organizer.rs:37`
    (`actual_national_playable_source_and_cold_foundation_preserve_one_opening`).
  - `tests/national_household_lifecycle.rs:147`
    (`dated_national_world_wayne_residents_change_the_next_food_requirement`).
  - `src/runtime_session/backend.rs:396` (`national_economy_new_founds_the_full_observer_company_world`).

  In `codec.rs` `only_the_county_compiler_frames_a_county_review_footer`, both of
  `COUNTY_REVIEW_COMPILERS` encode to `unframed_length + 5` and decode to their own name. The other
  assertions are kept, with `COUNTY_REVIEW_COMPILERS[1]` where the test named the constant.
- [ ] **Step 5: Run** Step 3's two commands and `mise run rust:test:q -- -p babylon-persistence -E
  'binary(captured_economic_catalog) | binary(captured_national_organizer) |
  binary(national_household_lifecycle) | binary(national_company_replay) | (binary(babylon_persistence)
  & (test(national_economy_new_founds) | test(only_the_county_compiler)))'`. Expected: PASS.
- [ ] **Step 6: Commit (a)** with the files of Steps 1, 2 and 4:
  `feat(persistence): the household units policy section and compiler national-world-v13`.
- [ ] **Step 7: Write the failing tests for (b).** The first are `#[cfg(test)]` tests in
  `household_units.rs`. The worked values are 6 other adults and 4 children over households 3:2:1:

```rust
#[test]
fn persons_are_the_labor_force_plus_a_households_share_of_the_rest() {
    let at = |n: u8, households, labor_force| HouseholdUnitCounts {
        principal: FinalDemandPrincipalId::from_bytes([n; 32]), households, labor_force };
    let household_units = [at(1, 3, 0), at(2, 2, 2), at(3, 1, 2)];
    assert_eq!(split_persons(14, 10, &household_units).expect("admitted"), vec![(5, 3), (5, 4), (4, 3)]);
    assert_eq!(split_persons(5, 4, &household_units), Err(NationalOpeningError::HouseholdUnits(
        HouseholdUnitRefusal::FewerPersonsThanHouseholds {
            household_unit: FinalDemandPrincipalId::from_bytes([1; 32]) })));
}
```

  Add to the same module: (1) `household_unit_principal(g, Some(m), Band::Next9)` equals
  `sha256(b"NationalHouseholdUnitV1\0" ‖ g ‖ m ‖ [2])`, and the `None` case hashes 32 zero bytes
  in place of `m`; (2) two units of one group with equal households, the same band and both with a
  crew are refused `KeeperTie { group }`; (3) two units that tie on households and labor force are
  ordered by `opening_member`, and the lower one gets the remainder of an `apportion`.

  The second is in `tests/national_household_units.rs`. It uses `static UNITS` and
  `units() = CapturedEconomicCatalog::capture(with_policy(|t| t.replacen("grain = \"group\"", "grain =
  \"unit\"", 1)), None)`. This is the opening alone: the County Review is not assembled until (d).

```rust
#[test]
fn wayne_divides_into_household_units() {
    let table = units().national_household_units().expect("the opening's units");
    let ordinary: Vec<_> = table.units.iter().filter(|u| u.households > 0).collect();
    assert_eq!((table.county, table.units.len(), ordinary.len()), (*b"26163", 66, 65));
    assert_eq!(ordinary.iter().map(|u| u.households).sum::<u64>(), 700_591);
    assert_eq!(ordinary.iter().map(|u| u.rows.len()).sum::<usize>(), 111);
    assert_eq!(ordinary.iter().filter(|u| u.member.is_some()).count(), 61);
    let mut crewless: Vec<_> = ordinary.iter().filter(|u| u.member.is_none()).map(|u| u.households).collect();
    crewless.sort_unstable();
    assert_eq!(crewless, [4, 7_006, 9_379, 147_457]);
    let mut sizes: Vec<_> = ordinary.iter().map(|u| u.households).collect();
    sizes.sort_unstable();
    assert_eq!(sizes[..9], [2, 2, 4, 4, 4, 8, 9, 11, 32]);
    for (band, units, households) in [(Band::Top1, 1, 7_006), (Band::Next9, 8, 63_054),
                                      (Band::Next40, 21, 280_236), (Band::Bottom50, 36, 350_295)] {
        let rows = || ordinary.iter().flat_map(|u| &u.rows).filter(|r| r.band == band);
        assert_eq!(ordinary.iter().filter(|u| u.rows.iter().any(|r| r.band == band)).count(), units);
        assert_eq!(rows().map(|r| r.households).sum::<u64>(), households);
    }
    assert!(table.units.windows(2).all(|p| p[0].principal < p[1].principal));
    let opening = units().opening();
    for u in &table.units {
        let seed = opening.households.iter().find(|h| h.principal_id == u.principal).expect("seed");
        assert_eq!((seed.persons, seed.households), (u.persons, u.households));
        assert!(u.eligible <= u.persons && (u.households == 0 || u.households <= u.persons));
        let Some(m) = u.member else { continue };
        let member = staffing_member(opening, m);              // household_id() == u.principal
        let sum = |f: fn(&OpeningHouseholdUnitRow) -> u64| u.rows.iter().map(|r| f(r) * r.households).sum();
        assert_eq!((member.household_id(), member.employed, member.reserve),
                   (u.principal, sum(|r| r.at_work.into()), sum(|r| r.seeking.into())));
        assert_eq!(terms_of(opening, m).iter().filter(|t| t.payee == u.principal).count(), 1);
    }
}
```

  `staffing_member` and `terms_of` are test helpers over the opening's staffing pool and its
  `EmploymentTerms` rows.
- [ ] **Step 8: Run** `mise run rust:test:q -- -p babylon-persistence -E 'binary(babylon_persistence) &
  test(household_units)'` and `-E 'binary(national_household_units) & test(wayne_divides)'`.
  Expected: compile failure (`split_persons`, `national_household_units` missing).
- [ ] **Step 9: Implement (b).** `divide` returns at once when `policy.household_units` is `None`. It
  is called from `finish` after `aid::fund`. Under `Group`, the table holds one unit for each county
  seed, with its pooled rows and nothing else changed. Under `Unit`, it follows C3, C4 and C8 with the
  Decisions above. Also add:
  - `household_unit_principal` per C4. The preimage is `b"NationalHouseholdUnitV1\0"`, then the 32
    group bytes, then the pooled member's 32 bytes (or 32 zero bytes), then the band byte: Top1 1,
    Next9 2, Next40 3, Bottom50 4.
  - The `household_endowment` and `member_at` extractions.
  - `eligibility` made `pub(super)`.
  - The new `Builder` and `NationalOpening` fields. `Builder::new` sets `None`; the literal passes
    `builder.household_units`.
  - `NationalSources.household_units` from `opening.household_units`, and the accessor.
  - The third age stage in `pushforward`.

  Refusals name the group or unit, as `HouseholdUnitRefusal` gives them. Add to
  `tests/national_household_units.rs` a check on the shipped `group` grain:
  `table.units.len() == 8`, and every unit has `group == principal`.
- [ ] **Step 10: Run** Step 8's commands and `mise run rust:test:q -- -p babylon-persistence -E
  'binary(national_county_review) | binary(national_opening) | binary(captured_economic_catalog)'`.
  Expected: PASS. The shipped grain is still `group`, so no other opening changes.
- [ ] **Step 11: Commit (b)** (`household_units.rs`, `identity.rs`, `opening.rs`, `build.rs`,
  `actors.rs`, `household_time.rs`, `lifecycle.rs`, `allocation.rs`, `capture.rs`, `national.rs`, the
  export lists, the two tests): `feat(persistence): divide Wayne's budget groups into household units`.
- [ ] **Step 12: Write the failing test for (c)** in `tests/national_household_units.rs`. Here
  `shares(c)` maps `(site, principal)` to shares, over `c.opening().institutions.ownership` and
  `c.national_company_finances().expect("companies").sources` (`original_shares`). Both are taken
  for `AccountId::Household` beneficiaries only.

```rust
#[test]
fn wayne_units_add_back_each_groups_shares_and_keep_the_foreground_workplaces() {
    let table = units().national_household_units().expect("units");
    let group: BTreeMap<_, _> = table.units.iter().map(|u| (u.principal, u.group)).collect();
    let mut summed = BTreeMap::new();
    for ((site, owner), n) in shares(units()) {
        *summed.entry((site, *group.get(&owner).unwrap_or(&owner))).or_insert(0_u64) += n;
    }
    assert_eq!(summed, shares(v12()));
    let foreground = |c: &CapturedEconomicCatalog| {
        c.national_detail().expect("detail").foreground().workplaces().to_vec()
    };
    assert_eq!(foreground(units()), foreground(v12()));
}
```

- [ ] **Step 13: Run** `-E 'binary(national_household_units) & test(add_back_each_groups_shares)'`.
  Expected: FAIL. Shares are still split in one stage over unit rows, and the foreground loses the
  sites whose members now pay units. **Implement** `OwnerGroup`, the two-stage `private_claims`
  and the detail insertion. Run again. Expected: PASS. **Commit (c)** (`financial.rs`, `detail.rs`,
  the test): `feat(persistence): household units take their shares in two stages`.
- [ ] **Step 14: Write the failing test for (d).** Set `grain = "unit"` in `defines.toml` and
  `HouseholdUnitGrain::Unit` in Step 1's test. `units()` becomes
  `capture_national_campaign(national_catalog_input(), campaign())`. Read the roster through
  `create_foundation(..).initial_register().county_review()`, as `tests/national_county_review.rs:35-48`
  does; `create_foundation` consumes the catalog, so call `county_review_of(units().clone())`. Define
  `label_of(config, p) -> &str` (the label of the group whose principal is `p`), `rows_of(review, p)
  -> Vec<(Band, bool, u16, u16, u16, u64, u64)>` (band, crew.is_some(), at_work, seeking, units,
  households, reached of that group's rows) and `seed_of(c, p) -> EconomicHouseholdSeed`.

```rust
#[test]
fn the_county_review_opens_on_wayne_household_units() {
    let (review, pooled) = (county_review_of(units().clone()), county_review_of(v12().clone()));
    let (config, roster) = (review.config(), &review.state().roster);
    assert_eq!((config.groups.len(), config.crews.len(), roster.rows.len()), (66, 61, 111));
    assert_eq!(roster.band_counts().iter().map(|b| b.households).collect::<Vec<_>>(),
               [7_006, 63_054, 280_236, 350_295]);
    let aid = units().national_aid_capture().expect("aid");
    let claimant = units().national_support_claimant().expect("claimant").principal;
    for (principal, label) in [(claimant, "no earner, no business share (claimants)"),
                               (aid.children[0].principal, "earning, no business share (aid donors)"),
                               (aid.children[1].principal, "no earner, no business share (aid partners)")] {
        assert_eq!(label_of(config, principal), label);
        assert_eq!(rows_of(&review, principal), rows_of(&pooled, principal));
        assert_eq!(seed_of(units(), principal), seed_of(v12(), principal));
    }
    assert_eq!(label_of(pooled.config(), aid.children[0].principal), "earning-nonowner (aid donors)");
}
```

- [ ] **Step 15: Run** `-E 'binary(national_household_units) & test(opens_on_wayne_household_units)'`.
  Expected: FAIL. The capture places the unit groups again, refusing or giving other bands, and the
  labels are today's. **Implement** the capture rules and labels in Decisions:
  - `CountyReviewCapture.household_units` is filled in the literal at capture.rs:469 from
    `national.household_units`.
  - Rows that cannot be mapped are `EconomicCatalogError::Identity`.

  Then update the tests that read a Wayne group principal as the whole group:
  - aid.rs `captured_refinements_conserve_county_margins_and_real_opening_money` sums the parent's
    units (`group == parent`).
  - `tests/support/national_household_controls.rs` `assert_endowments_and_ownership` gains `units:
    Option<&OpeningHouseholdUnits>`; every unit whose group is an owner principal is added to
    `domestic_owners`; its callers pass `capture.national_household_units()`.

  Any other test that fails is named to the lead before it is changed. Run again. Expected: PASS.
- [ ] **Step 16: Run the scoped gate.** From `rust/`, run fmt and clippy. Then run the test binaries
  above, `mise run rust:test:q -- -p babylon-persistence`, and `mise run check:bsl-sentinels`, since
  `defines.toml` changed. Expected: PASS.
- [ ] **Step 17: Commit (d)** (`county_review.rs`, `capture.rs`, `defines.toml`, the tests of Steps 1,
  14 and 15, `support/national_household_controls.rs`):
  `feat(persistence): the county review's roster comes from the opening's household units`.

### Task 4: The proofs, and the units' report

Design 7.6 (proof), with 7.2 (the opening's splits) and 9 item 1 repeated on units. Built after Task
6, so the report is recorded once, on the final buying rule. Nothing in the game changes. The task
adds one public reader of the opening's units table, the proofs, and the recorded report.

**Files:**
- Modify: `rust/crates/babylon-persistence/src/economic_catalog/capture.rs` (a new reader on
  `CapturedEconomicCatalog`, beside `national_support_claimant` at :253)
- Modify: `rust/crates/babylon-persistence/src/national_economy/opening.rs` (`pub use
  household_units::{OpeningHouseholdUnit, OpeningHouseholdUnitRow, OpeningHouseholdUnits};` beside
  `pub use build::{...}` at :31), unless Task 3 already added it: `household_units` is a child of
  the private `opening` module
- Modify: `rust/crates/babylon-persistence/src/national_economy.rs` (the `pub use opening::{...}` at
  :15-17 also names the three table types of C6)
- Modify: `rust/crates/babylon-persistence/tests/support/household_accounts.rs` (Task 1's reader:
  add `household_unit_specs`, `group_of`, `fold`, `split_by_households`)
- Test: `rust/crates/babylon-persistence/tests/national_household_units.rs` (Tasks 1 and 3 made it)
- Create: `reports/household-units-2026-11-20/wayne-unit-accounts.json`, `wayne-opening-units.json`
- Modify: `reports/household-units-2026-11-20/README.md` (one section for the two new files)

**Interfaces:**
- Consumes: C6's `OpeningHouseholdUnits`, `OpeningHouseholdUnit`, `OpeningHouseholdUnitRow`, kept on
  `NationalSources` by Task 3 for the capture-time roster; Task 1's `AccountSpec { label: String,
  principal: FinalDemandPrincipalId, bands: Vec<(Band, u64)> }`, `read_accounts(session,
  &[AccountSpec])` and its period loop (the body of `advance`, `tests/national_county_review.rs:276`);
  C7's `[household_units]` text in the shipped `defines.toml`; Task 6's declared order.
- Produces:

```rust
// economic_catalog/capture.rs, impl CapturedEconomicCatalog
#[must_use]
pub fn national_household_units(&self) -> Option<&OpeningHouseholdUnits>;   // None: Michigan, or no section
// tests/support/household_accounts.rs
pub fn household_unit_specs(catalog: &CapturedEconomicCatalog) -> Vec<AccountSpec>;   // one per unit, in table order
pub fn group_of(units: &OpeningHouseholdUnits) -> impl Fn(FinalDemandPrincipalId) -> FinalDemandPrincipalId + '_;
pub fn fold<K: Ord>(pairs: impl IntoIterator<Item = (K, i128)>) -> BTreeMap<K, i128>;   // sums equal keys
pub fn split_by_households(total: i128, parts: &[(Band, u64)]) -> Vec<(Band, i128)>;
```

**Decisions:**
- *The pooled figures* are read from a capture whose policy is the shipped file with `grain = "unit"`
  replaced by `grain = "group"` and the `going_without = [...]` line removed. Its units table holds
  the 8 Wayne groups, each with `principal == group`, so it is keyed by the group's own principal.
  The same capture is the "no declared order" opening of the grain test, so it serves both. [Call]
- *The comparison.* `group_of` maps a unit's principal to its `group` and every other principal to
  itself. Each add-back builds `(key, value)` pairs from both openings, folds the unit opening's keys
  through `group_of` (an `AccountId::Household` beneficiary too), and asserts the two `fold` maps
  equal. The maps cover every principal of the nation, so the rest of the country is shown
  unchanged in the same assertion. No row count is compared: a unit with no share gets no row.
- *One test for the thirteen add-backs.* Nextest runs each `#[test]` in its own process, and two
  national captures per process times thirteen processes on a 12-core, 31 GB machine is the
  fan-out that froze the box before. The add-backs are thirteen named check functions called from
  one test that captures both openings once; each `assert_eq!` message names the check. Three
  distinct policies; six capture runs across the four non-ignored tests (pooled twice, shipped
  twice). [Call]
- *Shares and company weights.* Site shares are compared per `(issuer_site_id, beneficiary)` on
  `opening.institutions.ownership` and per `(site, company, beneficiary)` on
  `national_company_finances().sources` (company member sites lose their household rows at
  `companies::fund`). Weights are compared per `(company, beneficiary)` on
  `opening.policies.company_payouts` and on `national_company_finances().claims`. A weight is
  capital × shares × a site factor, so equal folded shares give equal folded weights exactly.
- *Fields hashed from the policy text.* Three things carry a digest of the full policy bytes, which
  differ between the grain policy and the control: the county config's `policy_source_digest`
  (`policy/admission.rs:351`); each `opening.policies.aid_mandates` row's `source_hash` and `id`
  (`opening/aid.rs:152-157`, sha256 of `b"NationalAidMandateV1\0"` ‖ source hash ‖ recipient); and
  the detail partition's commitment ids (`opening/detail.rs:51-53`), which are those mandate ids.
  The grain test copies them from the control before comparing, and asserts the pooled ids against
  that formula on the grain policy's bytes. Under v13 the config's group labels are C12's, so they
  are copied too; Task 5 adds `household_units` to the copied fields. The roster is asserted equal
  with nothing set aside.
- *Band figures.* A unit in two bands (only the aid donors: 3 households in the bottom 50%, 1 in the
  next 40%) has its money divided by `split_by_households`: floor of total × households / all
  households, the leftover millionths one each to the largest remainders, an exact tie to the part
  listed first; parts are listed bottom 50% first (C8's order). It panics on a negative total, and
  returns all zeros when every part is 0. The kernel's `split::apportion` cannot do this: it refuses
  a total above its weights. [Call]
- *Wealth shares* are `split_by_households(10_000, …)` over each band's summed net assets, so they
  add to 10,000. Net assets are i128 millionths: each weight is `u64::try_from(band net assets)`,
  which panics naming the band if the sum is negative. The law's thirds by the same rule are bottom
  50% 0, next 40% 3,334, next 9% 3,333, top 1% 3,333.
- *The report's size.* 66 units over 35 points would pass 1 MiB as rows. `wayne-unit-accounts.json`
  is columnar (one array per figure per unit) and compact (`serde_json::to_vec`); the recorder
  asserts each file is under 1,048,576 bytes before it writes, as `write_record` does.
- *Drift is not an error* (design 7.6 last bullet). The recorder asserts the opening's shape only.

- [ ] **Step 1: Write the failing tests** in `national_household_units.rs`. The control policy is the
  shipped text cut at `"\n[household_units]"`; captures use `capture_national_campaign` and campaign
  `0x0026_1631_7036`; rosters come from `create_foundation(…, ReplaySeed::new(319))` as
  `county_review_of` does (`national_county_review.rs:36`).

```rust
#[test]
fn the_household_units_add_back_to_their_groups() {
    let (pooled, units) = (capture(group_grain), capture(str::to_owned));
    for check in [add_back_households, add_back_persons, add_back_eligible_persons, add_back_people_at_work,
                  add_back_people_looking, add_back_ages, add_back_cash, add_back_pantry, add_back_need_requirements,
                  add_back_buying_limits, add_back_support, add_back_shares, add_back_company_weights] {
        check(&pooled, &units);
    }
}
// Each check: assert_eq!(fold(pairs(&pooled, identity)), fold(pairs(&units, group_of(table))), "<check name>").
//  households, persons, cash   opening.households: (principal_id, households | persons | opening_cash.micro_units())
//  eligible persons            policies.household_time_policy: (principal_id, eligible_persons)
//  at work, looking            staffing[].members: (member.household_id(), employed | reserve)
//  ages                        Modeled(book).lifecycle.positions: ((principal_id, band 0..4), ages field)
//  pantry                      opening_stock: ((p, amount.good_id, amount.unit_id, 0), amount.quantity),
//                              ((p, amount.good_id, amount.unit_id, 1), total_cost.micro_units())
//  need requirements           template coefficients of the seed: ((p, good_id, unit_id), units_per_basis × persons|households)
//  buying limits               household_purchases: ((p, good, unit, retailer, 0), target_closing_stock), (…, 1, maximum_purchase)
//  support                     institutions.public_allocations where treatment == HouseholdIncomeSupport:
//                              ((public_account, recipient), amount_per_period.micro_units()); and public_budgets equal
//  shares, company weights     as Decisions say

#[test]
fn the_group_grain_opens_as_a_policy_without_the_section() {
    let (pooled, control) = (capture(group_grain), capture(without_section));
    assert_eq!((pooled.compiler_version(), control.compiler_version()), ("national-world-v13", "national-world-v12"));
    /* each pooled aid mandate id == sha256(b"NationalAidMandateV1\0" ‖ sha256(grain bytes) ‖ recipient);
       clone the pooled opening, copy id and source_hash of each aid_mandates row from the control, then: */
    assert_eq!(patched_opening, *control.opening());
    assert_eq!(pooled.national_company_finances(), control.national_company_finances());
    /* detail partitions part by part: background_households(), background_workplaces(), conservation(),
       foreground organizations, household_principals, workplaces, partner_workplaces equal; foreground
       commitments and commitments() equal with each id mapped to the matching control mandate's id */
    let table = pooled.national_household_units().expect("the group grain keeps its table");
    assert_eq!(table.units.len(), 8);
    assert!(table.units.iter().all(|unit| unit.principal == unit.group));
    assert!(control.national_household_units().is_none());
    /* config equal after copying labels and policy_source_digest from the control; rosters equal */
}

#[test]
fn the_engine_limits_and_the_status_line_hold_with_household_units() {
    /* on the shipped capture: 66 Wayne seeds, config 66 groups and 61 crews, 111 roster rows; and
       households, household_time_policy, lifecycle positions, Σ unmet_burdens, opening_stock rows,
       public_allocations <= MAX_MATERIAL_CIRCUIT_ROWS (65_536); household_purchases and the compiled
       catalog's household_needs (built as compile.rs:319-331 builds it) <= MAX_HOUSEHOLD_NEEDS;
       service_connections <= MAX_SERVICE_CONNECTIONS; taxes and households + sites + institutional_cash
       <= MAX_MONETARY_ACCOUNTS; ownership, equity and Σ company_payouts claims <= MAX_OWNERSHIP_CLAIMS;
       Σ staffing members <= MAX_STAFFING_MEMBERS (all 131_072); groups, crews, rows <= COUNTY_REVIEW_MAX_ROWS;
       the OrganizerStatus line, built as national_county_review.rs:202-219 builds it,
       < RUNTIME_SESSION_MAX_LINE_BYTES / 2 (524_288) */
}

#[test]
fn three_periods_keep_every_household_units_roster_on_the_engines_counts() {
    /* advance 1..=3 with no commitment; each commit must succeed (the engine's money and valuation
       checks run in the close, valuation/validation.rs:66). After period p, with roster and last_facts:
       facts.period == roster.period == p; for every crew c, crew_at_work(c) == closing_at_work and
       crew_seeking(c) == closing_seeking; for every ordinary group g, roster.groups[g].households ==
       facts.groups[g].closing_households == the engine cohort's households, and group_units(g) +
       departed_units == roll_units; for every group, the summed HouseholdIncomeSupport amount to its
       account (0 when it has no row) == roll_units × unit_price_micros (no session before period 4). */
}

#[test]
fn a_household_unit_in_two_bands_divides_its_money_by_households() {
    let parts = [(Band::Bottom50, 3), (Band::Next40, 1)];
    assert_eq!(split_by_households(7, &parts), [(Band::Bottom50, 5), (Band::Next40, 2)]);
    let law = [(Band::Bottom50, 0), (Band::Next40, 1), (Band::Next9, 1), (Band::Top1, 1)];
    assert_eq!(split_by_households(10_000, &law),
               [(Band::Bottom50, 0), (Band::Next40, 3_334), (Band::Next9, 3_333), (Band::Top1, 3_333)]);
    let empty = [(Band::Bottom50, 0), (Band::Next40, 0)];
    assert_eq!(split_by_households(5, &empty), [(Band::Bottom50, 0), (Band::Next40, 0)]);
}
```

- [ ] **Step 2: Run.** `cd /media/user/dev-ssd/worktrees/households-homes/babylon && mise run
  rust:test:q -- -p babylon-persistence -E 'binary(national_household_units)'`. Expected: compile
  failure, no `national_household_units` on `CapturedEconomicCatalog` and no `split_by_households`.
- [ ] **Step 3: Implement** the reader and re-exports (Produces), and the four helpers.
  `household_unit_specs` takes each unit's label from the county config group whose `group_id`
  equals the unit's principal, and its bands from its rows, households summed per band, bottom 50%
  first. Run Step 2's command. Expected: PASS. A red add-back names its check; fix the split in
  `opening/household_units.rs` (Task 3), never the check.
- [ ] **Step 4: Write and run the recorder.** `#[ignore = "writes reports/household-units-2026-11-20/
  wayne-unit-accounts.json and wayne-opening-units.json"] fn record_wayne_unit_accounts()`, on the
  shipped capture, Task 1's loop for 34 periods with no commitment. Before the first period it
  asserts the bands' households 7,006 / 63,054 / 280,236 / 350,295 (sum 700,591) and that the top 1%
  is one unit of 7,006 households with no one at work or looking and no relief unit. File shapes
  (keys in serde_json's order, money as decimal strings of millionths, a trailing newline):

```text
wayne-opening-units.json  { campaign, compiler, organizer_status_line_bytes,
  organizer_status_line_limit: 1048576, organizer_status_line_bound: 524288,
  limits: [{ name, limit, count }], bands: [{ band, households, units, people_at_work, people_seeking, relief_units }],
  units: [{ principal, group, label, member (hex or null), households, persons, eligible,
            opening_cash_micros, pantry_cost_micros, rows: [{ band, at_work, seeking, relief_units, households }] }] }
wayne-unit-accounts.json  { campaign, seed: 319, periods: 34,
  law_wealth_share_bps: { bottom50: 0, next40: 3334, next9: 3333, top1: 3333 },
  units: [{ principal, label, bands: [[band, households]], series: { <each figure of Task 1's reader>: [...],
            needs: { <need key>: { required, unmet, unpaid, unsupplied } } } }],
  bands: [{ band, series: { households, net_assets_micros, wealth_share_bps, company_payouts_micros,
            site_distributions_micros, needs_cost_micros } }],
  summary: { first_unmet: [{ principal, need, period }], unsupplied: [{ principal, period, need, quantity }] } }
```

  Stock figures have 35 points (point 0 is the opening); flows have 34. Run `cd
  /media/user/dev-ssd/worktrees/households-homes/babylon && mise run rust:test:q -- -p
  babylon-persistence -E 'binary(national_household_units) & test(record_wayne_unit_accounts)'
  --run-ignored ignored-only`, about 6 minutes. Expected: PASS, both files under 1 MiB. Add to the
  README the two files, the run command, the first period each band went without each need, and
  every `unsupplied` entry.
- [ ] **Step 5: Scoped gate.** From `rust/`: fmt and clippy; Step 2's binary; `mise run rust:test:q
  -- -p babylon-persistence`. Expected: PASS, and no existing test changed.
- [ ] **Step 6: Commit** twice. `capture.rs`, `opening.rs`, `national_economy.rs`, the test binary and
  the support file as `test(persistence): prove that Wayne's household units add back to their
  groups`; then the two JSON files and the README as `docs(reports): record Wayne's household units,
  band by band`.
- [ ] **Step 7: Checkpoint (C14).** The lead runs the whole gate, then reports to the Director:
  each band's wealth share beside the law's thirds; ownership pay beside the cost of needs for each
  band (sums, never a mean of rates); the first period the top 1% unit went without each need
  (expected within about four periods, since it has no wage and no relief unit) and the design's
  remedy, moving the division of the shares forward, for the Director to decide [Director]; and at
  once any `unsupplied` entry (C9).

### Task 5: The County Review on units

Design 7.3 (wage tax and going without, read per unit), 7.4 (what the County Review shows) and 7.5
(who went without is public, a unit's money is earned), with brief C1, C10 and C11. Built after
Task 4: each unit is already a `CountyReviewGroup` whose `group_id` is its own principal. This
task adds the purse facts, `went_without`, the capture of the needs, the tick reading of the close
and the unit and band views. A campaign without `[household_units]` keeps every byte.

**Files:**
- Create: `rust/crates/babylon-practice-contract/src/county_review/household_units.rs`
  (`went_without`, the money split, the view types and the function `project` calls),
  `rust/crates/babylon-practice-contract/tests/county_review/household_units.rs`
- Modify: `babylon-practice-contract/src/county_review/types.rs` (`CountyReviewConfig` at 205,
  `GroupPeriodFacts` at 310, `CountyReviewError` at 13, the C10 types), `roster.rs`
  (`validate_county_review_config`, `check_facts_shape`), `projection.rs`
  (`CountyReviewProjection` at 150, `project` at 498), `src/county_review.rs` (the module and its
  `pub use`), `tests/county_review.rs` (the `#[path]` module), `tests/county_review/support.rs`
  (`config` and `facts` literals), `tests/county_review/codec.rs`
- Modify: `rust/crates/babylon-tick/src/material_world/county_review.rs` (`CountyGroupLabor`,
  `group_facts` at 495, `labor_facts` at 545, `validate_world` at 293,
  `CountyReviewRegisterError` at 34, new `purse_facts` and `need_facts`), `register.rs` (the
  `labor_facts` call at 916), `county_review_execution.rs` (`period_facts`, the literal at 119),
  `county_review_tests.rs` (the `config` literal at 60, new tests),
  `tests/support/county_review_fixture.rs` (the literal at 143)
- Modify: `rust/crates/babylon-persistence/src/national_economy/county_review.rs` (`assemble`, the
  literal at 497; new `county_needs`; `CountyReviewCaptureError::UnknownNeed`; the test literal at
  537), `src/organizer_runtime/county_review_tests.rs` (literal at 280),
  `tests/observer_material_live/county_review_playthroughs.rs` (literal at 1612),
  `tests/national_county_review.rs` (new tests)
- Modify: `rust/crates/babylon-client/src/organizer/county_tests.rs` (the full
  `CountyReviewProjection` literal in `fixture()`, line 93; the others spread `..fixture()`)

**Interfaces:**
- Consumes: Task 3's `NationalGamePolicy.household_units: Option<GameHouseholdUnitsPolicy>`
  (`grain`, `going_without`) and its unit opening; `GameNeed.key` and `GameCommodity { good_id,
  unit_id, label }` (`policy/game.rs`); the close's `taxes`, `household_demand`,
  `household_consumption`, `service_performance`, `household_services` and `state`.
- Produces (C10 verbatim; every new field `#[serde(default, skip_serializing_if =
  "Option::is_none")]`, last in its struct; money fields `#[serde(with = "super::decimal")]`):

```rust
// types.rs
pub struct CountyHouseholdUnits { pub needs: Vec<CountyNeed> }  // CountyReviewConfig.household_units: Option<_>
pub struct CountyNeed { pub key: String, pub label: String, pub good_id: [u8; 32], pub unit_id: [u8; 32] }
pub struct UnitPurseFacts {                                         // on GroupPeriodFacts as `purse`
    pub closing_cash_micros: i128,
    pub net_assets_micros: i128,
    pub wage_tax_assessed_micros: i128,
    pub needs: Vec<NeedPeriodFacts>,                                // in the config's need order
}
pub struct NeedPeriodFacts {
    pub required: u64, pub unmet: u64, pub unpaid: u64, pub unsupplied: u64, pub cost_micros: i128,
}
// CountyReviewError gains NeedsNotCanonical, UnmetExceedsRequired
// household_units.rs
pub fn went_without(required: u64, unmet: u64, households: u64) -> Result<u64, CountyReviewError>;
fn split_by_largest_remainder(total: u128, weights: &[u64]) -> Result<Vec<u128>, CountyReviewError>;
pub struct HouseholdUnitsView { pub needs: Vec<String>, // each need's label, in the config's order
    pub period: Option<u64>, pub bands: Vec<BandUnitsView>, pub units: Vec<HouseholdUnitView> }
pub struct BandUnitsView { pub band: Band, pub went_without: Vec<u64>,
    pub wealth_bps: Option<u16>, pub ownership_to_needs_bps: Option<u64> }
pub struct HouseholdUnitView { pub group: u32, pub label: String, pub bands: Vec<Band>,
    pub went_without: Vec<u64>, pub wage_tax_short: bool, pub earned: Option<HouseholdUnitEarned> }
pub struct HouseholdUnitEarned { pub households: u64, pub closing_cash_micros: i128,
    pub cash_micros_per_household: i128, pub net_assets_micros: i128, pub wages_micros: i128,
    pub wage_tax_assessed_micros: i128, pub wage_tax_collected_micros: i128, pub support_income_micros: i128,
    pub aid_income_micros: i128, pub ownership_income_micros: i128, pub ownership_micros_per_household: i128,
    pub free_hours: u64, pub needs: Vec<NeedPeriodFacts> }
// CountyReviewProjection.household_units: Option<HouseholdUnitsView>
// babylon-tick county_review.rs
pub(super) fn labor_facts(register: &CountyReviewRegister, catalog: &MaterialCatalog,
    transition: &MaterialCircuitTransition) -> Result<CountyLaborFacts, MaterialWorldError>;
// CountyGroupLabor.purse: Option<UnitPurseFacts>; CountyReviewRegisterError gains Needs
// babylon-persistence national_economy/county_review.rs
fn county_needs(policy: &NationalGamePolicy) -> Result<Option<CountyHouseholdUnits>>;
```

**Decisions:**
- *When the section exists.* [Call] `county_needs` returns `Some` only for `grain = "unit"`.
  Task 4 proves that `grain = "group"` gives the same county configuration as a policy without
  the section, so the group grain carries no needs and its tick writes no purse. Order: the
  policy's `going_without` if declared, else the order of `[[household_needs]]`. A key with no
  commodity is `UnknownNeed { key }`.
- *Where the purse is read.* In `labor_facts`, from the transition before later operations change
  the state. Closing cash is `economy.book.cash(AccountId::Household(p))` on `transition.state`.
  Net assets are the `economy.costs.capital_accounts()` row for that account: `opening_capital +
  contributed_capital + retained_earnings`. A missing account or row is `Cohort`. Assessed tax is
  the sum of `assessed` over the same `TaxReceipt`s `group_facts` reads.
- *A need, per principal.* [Call] If the catalog has no `HouseholdNeed` for (principal, good,
  unit), every figure is 0. Otherwise the need is a service when the close has a
  `HouseholdServiceReceipt` for it, and a good when it has a `HouseholdConsumptionReceipt`. Neither
  or both is `Receipt`. A unit with no stock row writes no consumption receipt, so it is refused
  and never shown as fed.
- *A good:* `required`, `unmet` come from the consumption receipt; from the one demand receipt
  (none is `Receipt`), `unpaid = requested - admitted`, `unsupplied = admitted - fulfilled` and
  `cost = required × unit_price`. What was requested includes refilling the pantry (Task 6).
- *A service:* `required` and `unmet` come from the service receipt. `unpaid` is the sum of
  `requested_quantity - admitted_quantity` and `unsupplied` the sum of `admitted_quantity -
  performed_quantity`, over every `ServicePerformanceReceipt` with `buyer == Household(p)` and the
  same good and unit. One order of the opening due that period gives a second receipt
  (`services/admission.rs` 192-198). [Call] Every receipt of one need must carry one
  `unit_price`, which prices `cost`; two prices are `Receipt`. Such due orders come only from the
  opening, priced like period 1's offers. Refusing is better than choosing a price by order id.
  A service need with no performance receipt (no `household_purchases` row; the close still
  writes its `HouseholdServiceReceipt`, `services/close.rs` 354-385) has unpaid = unsupplied = 0
  and is `Receipt` unless its required is 0: no price means no cost, and cost is never guessed.
- *Households in the count.* [Call] `went_without` takes the group's `closing_households`, the
  households the roster holds after the roll. Not chosen: the period's opening households
  (`HouseholdLifecycleReceipt.opening_households`), which the facts do not carry.
- *A unit in two bands* (C1). Each figure shown by band is split by the unit's roster households
  in each band, bands from the bottom 50% up. Each need's went-without count is split with
  `apportion(.., Ties::InOrder)`; it never exceeds the unit's households, so `apportion`'s cap
  holds. Net assets, ownership income and the sum of the needs' cost are split once, with
  `split_by_largest_remainder`, because `apportion` refuses a total above its weights
  (`split.rs` 41-43) and takes only u64.
- *The money split.* `split_by_largest_remainder` (private, in `household_units.rs`): each part
  is ⌊total × w ÷ Σw⌋; the leftover goes one each to the largest remainders, equal remainders to
  the earlier part. The total is not capped by the weights. Σw = 0 with a nonzero total is
  `Arithmetic`. A negative net assets, ownership income or cost is `Arithmetic` (households hold
  no debt in step A); it is never clamped.
- *Shares.* `wealth_bps` = `split_by_largest_remainder(10_000, band net assets)` from the bottom
  50% up, so a county holding 1 micro still splits. All four are `None` when no band holds any
  wealth, because a zero sum cannot be split. `ownership_to_needs_bps` = ⌊10,000 × ownership ÷
  cost⌋, `None` at zero cost. It may pass 10,000. Both are sums of money, never averages.
- *Earned.* [Call] Today a position is earned when its key is in `contacted` (projection.rs
  `position_view`). A unit is earned when any key in `contacted` has its group index, because a
  unit never changes. Not chosen: earned only while that position still exists. No new state.
  Without `last_facts`, `earned` is `None`.
- *Earned figures.* `households` is the group's `closing_households`. `wages_micros` is the sum
  of `accrued_wages_micros` over the crews whose `group` is the unit.
  `cash_micros_per_household` = ⌊closing cash ÷ households⌋ and `ownership_micros_per_household`
  = ⌊ownership income ÷ households⌋, both 0 when households is 0. Every other field is copied
  from the group's facts and purse.
- *Public per unit* (C11): label, bands, `went_without` and `wage_tax_short` (assessed > collected,
  which the unit's sentence needs). Its households stay earned, as a position's are today. The
  sentence's words are Task 7's.
- *Order.* `units` lists the ordinary groups the roster holds households in, in config order.
  `bands` lists four, top first, as `band_counts` does. Before the first close, `period` is `None`,
  the counts are empty and every share is `None`.
- *Validation.* `validate_county_review_config` refuses empty needs, an empty key, a repeated key
  or a repeated (good, unit) with `NeedsNotCanonical`. `check_facts_shape` refuses `FactsShape`
  when a purse is present without the section, missing with it, or has the wrong number of needs.
  It refuses `UnmetExceedsRequired` when a need's unmet is above its required. The tick's
  `validate_world` refuses with `CountyReviewRegisterError::Needs` a config need whose (good, unit)
  no catalog `HouseholdNeed` carries, so a mistyped need never reads 0 for everyone.

- [ ] **Step 1: Write the failing kernel tests** in `tests/county_review/household_units.rs`. Fixture
  `units()`: `support::config(&[(4, 0, false), (3, 0, false), (2, 0, true)], &[0])` with needs
  food (`[1; 32]`, label "Food") and housing (`[2; 32]`, "Housing"). Rows: `((0, N40, Some(0), 1,
  0, 0), 4, 0)`, `((1, B50, None, 0, 0, 0), 2, 0)`, `((1, N40, None, 0, 0, 0), 1, 0)`, `((2, T1,
  None, 0, 0, 0), 2, 0)`. Facts: `support::facts(&c, &roster, &[], &[4, 3, 2])`, with these purses
  (unpaid = unmet, unsupplied 0):

| group | cash | net assets | assessed | food (req, unmet, cost) | housing (req, unmet, cost) | other |
|---|---|---|---|---|---|---|
| 0 | 400_000_000 | 1_000_000_000 | 30_000_000 | 12, 0, 60_000_000 | 4, 1, 400_000_000 | collected 20_000_000 |
| 1 | 90_000_000 | 300_000_000 | 0 | 9, 4, 45_000_000 | 3, 3, 300_000_000 | |
| 2 | 2_000_000_000 | 5_000_000_000 | 0 | 6, 0, 30_000_000 | 2, 0, 200_000_000 | ownership 150_000_000 |

```rust
#[test]
fn went_without_counts_the_fewest_whole_households() {
    assert_eq!([(12, 0, 4), (12, 1, 4), (12, 4, 4), (12, 12, 4), (4, 3, 4), (0, 0, 4)]
        .map(|(r, u, h)| went_without(r, u, h)), [Ok(0), Ok(1), Ok(2), Ok(4), Ok(3), Ok(0)]);
    assert_eq!(went_without(12, 13, 4), Err(CountyReviewError::UnmetExceedsRequired));
    assert_eq!(went_without(0, 1, 4), Err(CountyReviewError::UnmetExceedsRequired));
}
#[test]
fn bands_show_counts_and_shares_and_a_contacted_unit_shows_its_money() {
    let view = project_units(&[key(1, B50)]);   // contacted: group 1's bottom-50% position
    assert_eq!(view.bands.iter().map(|b| (b.band, b.went_without.clone(), b.wealth_bps,
        b.ownership_to_needs_bps)).collect::<Vec<_>>(), [(T1, vec![0, 0], Some(7_937), Some(6_521)),
        (N9, vec![0, 0], Some(0), None), (N40, vec![1, 2], Some(1_746), Some(0)),
        (B50, vec![1, 2], Some(317), Some(0))]);
    assert_eq!(view.units.iter().map(|u| (u.group, u.bands.clone(), u.went_without.clone(),
        u.wage_tax_short, u.earned.is_some())).collect::<Vec<_>>(), [(0, vec![N40], vec![0, 1], true, false),
        (1, vec![B50, N40], vec![2, 3], false, true), (2, vec![T1], vec![0, 0], false, false)]);
    let earned = view.units[1].earned.as_ref().expect("contacted");
    assert_eq!((earned.households, earned.cash_micros_per_household, earned.net_assets_micros,
        earned.ownership_micros_per_household), (3, 30_000_000, 300_000_000, 0));
    assert_eq!(earned.wages_micros, crew_wages(&facts, 1)); // Σ accrued_wages_micros, group 1
}
```

  Also: `one_micro_of_wealth_still_splits_its_shares` (net assets 0, 0, 1: the four
  `wealth_bps` are `Some` and sum to 10,000); `before_the_first_close_units_show_no_figures`
  (`last_facts: None`: `period` `None`, every count empty, every share `None`, every `earned`
  `None`); `a_county_without_units_projects_as_before` (`household_units` is `None`, and the
  projection's JSON has no `household_units`); `needs_that_are_not_canonical_are_refused` (empty
  list, empty key, repeated key, repeated pair: `NeedsNotCanonical`);
  `purses_that_do_not_fit_the_section_are_refused` (`FactsShape` three ways, then
  `UnmetExceedsRequired`); `a_state_with_purses_survives_encode_and_decode`. In `codec.rs`:
  `a_recorded_county_without_units_keeps_every_key`. It reads
  `reports/county-review-2026-11-19/no-contact.json` from `env!("CARGO_MANIFEST_DIR")/../../..`.
  It decodes `county_config` and every period's `facts` and asserts that `serde_json::to_value`
  equals the recorded value. It asserts that `encode_county_review_config` holds no
  `household_units` bytes. The record's keys are sorted, so the test compares values, not bytes.
  Nothing else in a serialized type changes, so no new key means no new byte.
- [ ] **Step 2: Run** `mise run rust:test:q -- -p babylon-practice-contract -E 'binary(county_review)
  & (test(household_units) | test(a_recorded_county))'`. Expected: compile failure (no
  `went_without`, no `purse`).
- [ ] **Step 3: Implement** the types, the two variants, the checks, `household_units.rs` and the
  projection field. Add `household_units: None` to `support::config` and `purse: None` to
  `support::facts`. Run Step 2. Expected: PASS. Then run the whole binary `-E
  'binary(county_review)'`. Expected: every earlier test passes unchanged.
- [ ] **Step 4: Write the failing tick tests** in `county_review_tests.rs`. `units_register()` is
  `county_register(4)` with `config.household_units` holding needs for goods 1 to 6 of
  `agency_control` (labels "Need 1" to "Need 6"). The donors need all six (goods 1 and 2 are
  stored goods, 3 to 6 are services). The recipients need food (good 2) only, hold a stock row
  of 0 and have a disabled purchase policy, so their demand receipt requests 0. The expected
  transition is `babylon_material_circuit::advance_material_circuit(&catalog, opening.state())`.
  - `the_close_fills_each_purse_from_its_receipts`: donors' `closing_cash_micros ==
    agency_control::cash(&transition.state, AccountId::Household(donor()))`; `net_assets_micros`
    equals the donor's capital row sum; `wage_tax_assessed_micros` equals the sum of `assessed`
    and is at least `labor.groups[0].wage_tax_collected_micros`. Each donor need equals the rules
    in Decisions, recomputed from the transition. The recipients' food is `(required, unmet,
    unpaid, unsupplied) == (4, 4, 0, 0)`, its cost is 4 × the demand's `unit_price`, and their
    goods 1 and 3 to 6 are all zero.
  - `several_service_receipts_for_one_need_are_summed_and_carry_one_price`: in a clone of the
    transition, push a copy of the donors' good 3 performance receipt with a new `order_id`. Then
    `labor_facts` doubles that need's `unpaid` and `unsupplied`. With the copy's `unit_price` + 1,
    it refuses with `CountyReviewRegisterError::Receipt`.
  - `a_need_with_no_receipt_of_its_kind_is_refused`: in a clone of the transition, remove the
    donors' good 1 consumption receipt: `Receipt`. In another, remove their good 1 demand
    receipt: `Receipt`. In another, add a `HouseholdServiceReceipt` for good 1: `Receipt`. In
    another, remove every donor performance receipt for good 3: `Receipt`.
  - `a_need_no_household_carries_is_refused`: a config need for a (good, unit) with no
    `HouseholdNeed` gives `CountyReviewRegisterError::Needs` from `validate_world`.
  - `a_crew_unit_that_loses_households_gives_up_those_left_outside_the_labor_force` (C2). The
    donors open as one crew unit with no row outside the crew: three households with one at work
    and one with one seeker. Lifecycle receipt: opening `age_18_64: 8`, deaths 6, closing 2,
    households 4 to 2. The attrition comes from
    `babylon_material_circuit::reconcile_resident_workforce(&[receipt], &[(StaffingPoolId::from_bytes([4; 32]),
    member)])`, where `member` is `StaffingMemberState::try_new(StaffingMemberBinding::try_new(StaffingMemberId::from_bytes([1;
    32]), donor(), "county:26163".parse()?, 4)?, 3, 1)?`. Assert `attrition[0].employed_removed
    == 2 && attrition[0].reserve_removed == 0` (the tie order of `proportional_shares`), so a
    change to the engine's tie order shows here. Write it into the closed period's
    `labor.crews[0]` (`left_*`, closing counts) and set `groups[0].closing_households = 2`. Then
    `hold_period` is `Ok`, the donors hold 2 households and no crewless row, the crew's people
    equal the closing counts, and `departed_units` equals the sum of `units × households` over
    the opening roster rows the roll emptied, read from `state_for(&config).roster` (two at-work
    households leave).
  - `a_county_without_units_writes_no_purse`: on `county_register(4)` every
    `last_facts.groups[i].purse` is `None` after `resolve`, and the encoded section has no `purse`.
- [ ] **Step 5: Run** `mise run rust:test:q -- -p babylon-tick -E 'test(county_review_tests)'`.
  Expected: compile failure.
- [ ] **Step 6: Implement** `purse_facts` and `need_facts`, taking the principal and the section's
  needs, and the `Needs` check in `validate_world`. Make the `labor_facts` change, pass `catalog`
  at register.rs:916, carry `purse` through `period_facts`, and add the literals. Run Step 5.
  Expected: PASS. Then `mise run rust:test:q -- -p babylon-tick -E
  'binary(county_review_replay)'`. Expected: PASS unchanged (no fixture there has units).
- [ ] **Step 7: Write the failing persistence tests** in `tests/national_county_review.rs`:
  - `wayne_under_units_names_the_six_needs_in_the_order_of_going_without`: `(key, label)` pairs
    are `[("food", "Food for one person for 28 days"), ("materials", "Manufactured supplies"),
    ("utility", "Utility provision"), ("housing", "Housing provision"), ("household_services",
    "Household services"), ("public_provision", "Public provisioning")]`. Each `good_id` and
    `unit_id` equals the policy commodity's.
  - `wayne_without_the_section_captures_todays_county`: `without_household_units(input)` cuts the
    `NationalGamePolicy` source at `"\n[household_units]"` and captures it again with
    `SourceArtifact::capture`, as `national_company_capture.rs` `pre_company_input` does. The
    result's config has `household_units: None` and no `household_units` bytes. The keys of
    `to_value(config)` equal those of the recorded `no-contact.json` `county_config`.
  - `the_opening_snapshot_shows_the_units_and_none_of_their_money`: `snapshot(national_opening())`
    has `household_units` `Some`, `period` `None`, four bands and every `earned` `None`.
  - `a_need_key_with_no_commodity_is_refused`: a policy whose `going_without` names a key with no
    commodity gives `CountyReviewCaptureError::UnknownNeed { key }`.
- [ ] **Step 8a: Make the crate compile.** Add `household_units: None` to the four
  `CountyReviewConfig` literals (county_review.rs:497 and :537, organizer_runtime
  county_review_tests.rs:280, county_review_playthroughs.rs:1612) and `UnknownNeed { key: String
  }` to `CountyReviewCaptureError`. Run `mise run rust:test:q -- -p babylon-persistence -E
  'binary(national_county_review)'`. Expected: the six-needs, opening-snapshot and unknown-need
  tests fail; `wayne_without_the_section_captures_todays_county` passes (it guards the cut, not
  the new code).
- [ ] **Step 8b: Implement** `county_needs` and call it in `assemble`. Run Step 8a's command.
  Expected: PASS, including `the_wayne_status_line_fits_the_protocol` with the new view in the
  line.
- [ ] **Step 9: Scoped gate.** Add `household_units: None` to `fixture()` in
  `babylon-client/src/organizer/county_tests.rs:93`. Run `cd rust && cargo fmt --all -- --check`
  and, per crate, `cargo clippy -p <crate> --all-targets --locked -- -D warnings -D
  clippy::cognitive_complexity`; then `mise run rust:test:q -- -p` for
  `babylon-practice-contract`, `babylon-tick`, `babylon-persistence`, `babylon-client` (one at a
  time). Expected: PASS. No snapshot or fixture moves. No fixture in
  `babylon-persistence/tests/fixtures` or `babylon-client/tests/fixtures` holds a county section
  (checked at HEAD). Every new field is skipped when `None`, and the records in
  `reports/county-review-2026-11-19/` are only read.
- [ ] **Step 10: Commit** the files above as `feat(county-review): each household unit's purse, who
  went without, and the unit and band views`.

### Task 6: The declared order of going without

Design 7.3, the bullet "A unit that is short goes without, in a declared order". Built after Task 3
and before Task 4. Each household need gets a rank; the engine admits a ranked household's goods,
then its services, each in rank order. The order applies only to households in the county that
`[household_units]` names. Every other household keeps rank 0 and the engine's order.

**Files:**
- Modify (engine, `rust/crates/babylon-material-circuit/`): `src/recurring/model.rs` (`HouseholdNeed`
  at 57-63 gains `rank`); `src/model.rs` (`MaterialCircuitError` gains code 38 after line 649, and
  `TryFrom<u16>` gets a new arm at 695-697); `src/catalog.rs` (`validate_definitions` at 311 calls the
  new `validate_need_ranks`); `src/wire/catalog.rs` (`bytes`: the version match at 161-169 and a
  rank tail after the portfolio section, which ends at 212); `src/recurring/households.rs`
  (`admit_household_orders`: the sort at 105 and the receipts it returns); `src/services/admission.rs`
  (`Request` at 54-62 gains `rank`, `requests` fills it, the sort at 129); `src/wire/state.rs`
  (`MATERIAL_CIRCUIT_SOURCE_SHA256` at 31-34 is pinned again)
- Modify: `contracts/material_circuit_v4.yaml` (`household_need_rank_invariant: 38` after line 543;
  beside `catalog_version` at line 72, a line stating that catalog version 6 is version 5 plus one
  rank byte for each household need, in canonical key order; at line 119, a note that
  `household_needs` rows gain a trailing `rank_u8` tail only in catalog version 6)
- Modify (`rank: 0`, 20 literals in 16 files): material-circuit `src/recurring/households_tests.rs`
  (279, 604), `tests/period_services/inventory_limits.rs` (224),
  `tests/recurring_circuit/counterfactuals.rs` (295), `tests/recurring_circuit/support.rs` (95, 845),
  `tests/support/{aid_cases.rs (68), economic_location_cases.rs (131), financial_operations.rs (167),
  household_policy_bounds.rs (159), household_service_time_cases.rs (43),
  organizer_funding_control.rs (581, 593), period_service_cases.rs (126)}`; persistence
  `src/production_projection/{recurring_fixture.rs (323), services_fixture.rs (448)}`; tick
  `src/material_world/tests.rs (433)`, `tests/staffed_material_replay/recurring.rs (130)`,
  `tests/support/organizer_aid_fixture.rs (478, 580)`
- Modify (persistence, `rust/crates/babylon-persistence/src/`), in the engine commit:
  `economic_catalog/model.rs` (`HouseholdNeedCoefficient` at 153 gains `rank`);
  `national_economy/opening/templates.rs` (the coefficient literal at 77 sets `rank: 0`);
  `economic_catalog/compile.rs` (the need literal at 325 passes `rank: need.rank`);
  `national_economy/organizer.rs` (the literal at 421 passes `rank: coefficient.rank`)
- Modify (persistence), in the persistence commit: `national_economy/opening/templates.rs`
  (`compile`; new `household_template`); `national_economy/opening/actors.rs` (`household_identity`:
  the template choice at 257-261)
- Modify: the ADR306 file that Task 2 created under `ai/decisions/` gets one new ruling (Decision 1)
- Test: `rust/crates/babylon-material-circuit/src/recurring/households_tests.rs`,
  `tests/weighted_freight.rs` (`successor_refusal_registry_includes_accounting_and_rejects_unknown_codes`);
  `rust/crates/babylon-persistence/tests/national_household_units.rs` (Task 1's binary),
  `tests/support/national_household_controls.rs` (line 116: 2 templates become 4)

**Interfaces:**
- Consumes: from Task 3, `NationalGamePolicy.household_units: Option<GameHouseholdUnitsPolicy>` with
  `county: [u8; 5]` and `going_without: Option<Vec<String>>`. The policy has already checked that
  every need key appears exactly once and that every storable good comes before every service.
- Produces:

```rust
// babylon-material-circuit/src/recurring/model.rs
pub struct HouseholdNeed { /* principal_id, good_id, unit_id, basis, units_per_basis, */
    /// 0: the engine's order. Otherwise the need's place in its principal's declared order.
    pub rank: u8,
}
// src/model.rs
pub enum MaterialCircuitError { /* ... */ HouseholdNeedRankInvariant = 38 }
// src/catalog.rs
impl MaterialCatalogDefinition { fn validate_need_ranks(&self) -> Result<(), MaterialCircuitError>; }
// babylon-persistence/src/economic_catalog/model.rs
pub struct HouseholdNeedCoefficient { /* good_id, unit_id, basis, units_per_basis, */ pub rank: u8 }
// babylon-persistence/src/national_economy/opening/templates.rs
pub(super) fn household_template(policy: &NationalGamePolicy, location: EconomicLocation,
                                 kind: HouseholdKind) -> HouseholdTemplateId;
```

**Decisions:**
1. *The pantry is part of food.* [Call], recorded as a new ruling in ADR306. A ranked good's request
   stays today's `desired`: this period's need plus the refill up to `target_closing_stock`, capped
   at `maximum_purchase` (2 × the need, `markets.rs:398-402`). So a short unit refills its food and
   materials pantry before it pays for utility or housing. The other bound, which the ruling names, is
   to buy every ranked good's need first, then the services, then the pantries. That needs a second
   goods pass after `ServiceClose::new` and a change to `validate_demand_receipts`, which recomputes
   what was requested. Reason: the cash rule then stays one window and one formula, and Task 4's
   report shows what the pantry costs a unit.
2. *The rank lives on the catalog's need, not on the purchase policy.* The state frame, the 145-byte
   row of storage layout 33 and the state versions 22/24 do not change. Only the catalog's bytes
   change, and only when a rank is present.
3. *What validation refuses* (`validate_need_ranks`, `HouseholdNeedRankInvariant`), per principal.
   A principal with any non-zero rank must have every need ranked with distinct ranks, and every
   storable need must rank below every service need. Gaps are allowed. For a principal with any
   non-zero rank, a need whose `(good_id, unit_id)` is not in `self.commodities` is refused with the
   same code; unranked principals keep today's checks and codes. The goods-before-services check is
   the engine's, not only the policy's: the engine admits all goods before all services, so a service
   ranked first could never be served first, and the declared order would be broken without a word.
4. *The wire* (brief section D). The rank tail is one `u8` for each need, in canonical
   `(principal, good, unit)` order, written after the portfolio section. A catalog with a rank is
   version 6 when its portfolio order is `FirstApplicable`. It is refused with `WireVersion` in every
   other combination (no portfolios, with or without payouts, or `HighDemandBeforeSpare`). A catalog
   with no rank writes exactly today's bytes and versions 2 to 5. The new code 38 follows the precedent
   of d7cb00067: the code is documented in the contract and the contract's digest is pinned again.
5. *The sorts.* Goods use `(principal_id, rank, good_id, unit_id)`, with the rank looked up by need
   key in `catalog.household_needs`. Services use `(buyer, rank, good, unit, provider)`: a site
   request has rank 0, and a household request takes its need's rank. With every rank 0, both orders
   are today's. The goods demand receipts are sorted back to `(principal, good, unit)` before
   `admit_household_orders` returns them. The money movements stay in the order the cash moved.
   Service receipts are already sorted by `order_id` (admission.rs:257).
6. *Ranks in the opening.* When `going_without` is present, `templates::compile` first refuses it
   with `NationalOpeningError::Policy` unless `policy.companies` is present with
   `CompanyConditionOrder::FirstApplicable` (Decision 4 would otherwise refuse the catalog late, with
   `WireVersion`, inside `MaterialCatalog::try_new`). It then appends two templates:
   `HouseholdTemplateId(3)` holds template 1's needs and `HouseholdTemplateId(4)` holds template 2's
   person needs. A need's rank is 1 plus its position in `going_without`, so ranks run 1 to 6;
   `compile` maps the `u8::try_from` failure of `1 + position` to `NationalOpeningError::Arithmetic`.
   `household_template` returns 3 (ordinary) or 4 (collective residence) only when
   `policy.household_units` has `going_without: Some(_)` and the seed's location is
   `EconomicLocation::County(c)` with `c.geoid().as_bytes() == units.county`; otherwise 1 or 2. So
   every Wayne seed uses the ranked templates: groups, units (Task 3 copies the group's template), the
   claimant, the aid households and the collective residence. Without `going_without` there are
   still two templates and no byte moves. The rank cannot come from `policy.household_needs`, because
   `needs()` sorts the needs by key (admission.rs:883).
7. *Engine fixtures with ranks carry a `FirstApplicable` portfolio policy and one payout.* Decision 4
   requires it. The close-level paths would then also need company accounts, so the goods, services
   and combined tests run the real admission window: `crate::admit_household_orders`, then
   `crate::services::ServiceClose::new`, the two calls at state.rs:1325-1326.

- [ ] **Step 1: Pin today's catalog bytes (at HEAD, before any field exists).** In
  `households_tests.rs`, add `fn service_opening(household_cash: i128) -> (MaterialCatalogDefinition,
  MaterialCircuitState)`. It is `opening(household_cash, 0)` as a definition, plus two goods
  `s6() = GoodId::from_bytes([6; 32])` and `s7() = [7; 32]`. Each is `CommodityKind::PeriodService {
  stage: ServiceStage::LocalServiceProvision }` with unit `u()`, needed once for each person (4
  persons). Each has an offer at `s()` for `cash(4)` (`PricePolicy::Fixed`), a policy with
  `target_closing_stock: 0, maximum_purchase: 4` and a sorted `ServiceConnection { provider_site_id:
  s(), buyer: AccountId::Household(h()), .. }`. The fixture has no service process, so it is valid
  only for the admission window: do not call `crate::services::validate` on it. Its s6/s7 need
  literals take `rank: 0` from Step 3 on. Add `fn first_applicable(d: &mut
  MaterialCatalogDefinition)`, which copies the policy of `tests/support/company_portfolio.rs:15-31`:
  rows `[[70,30,0,0],[10,70,15,5],[60,25,15,0],[10,10,60,20]]`, `8000`, `3`, `5000`, and one payout
  for company `[9; 32]` with `earnings_bps: 0` and claims `[(AccountId::Household(h()), 1)]`. Then
  write `catalog_bytes_without_ranks_keep_their_versions_and_digests`. For each of the four
  combinations (no policy and no payout, payout only, `HighDemandBeforeSpare`, `FirstApplicable`), it
  asserts that bytes `28..30` of `crate::wire::catalog_bytes` are 2, 3, 4 and 5, and that the SHA-256
  of the bytes equals a pin. Take the four pins from one run at HEAD (print them once with
  `eprintln!`, paste them, then delete the print). The pins come from HEAD and never from changed code.
  Run `mise run rust:test:q -- -p babylon-material-circuit -E 'binary(babylon_material_circuit) &
  test(catalog_bytes_without_ranks)'`. It passes at HEAD.
- [ ] **Step 2: Write the failing engine tests** in `households_tests.rs`. `fn ranked_opening(cash:
  i128, ranks: [u8; 3])` is `service_opening` plus `first_applicable`, with the ranks set on `[g(),
  s6(), s7()]`. `p8() = FinalDemandPrincipalId::from_bytes([8; 32])` is a second household with the
  same three needs, all rank 0, its own cash and connections:

```rust
#[test] // sibling of one_household_budget_is_shared_in_canonical_need_order: same fixture, plus
fn a_declared_rank_reverses_the_canonical_need_order() { // first_applicable, rank 2 on g(), 1 on other
    assert_eq!(first, second);
    assert_eq!(first.iter().map(|r| (r.good_id, r.admitted_quantity)).collect::<Vec<_>>(),
               vec![(g(), 0), (other, 1)]);           // canonical receipt order; the rank decided
    assert_eq!(economy(&mut state).book.cash(AccountId::Household(h())).expect("payer"), cash(0));
}
#[test]
fn a_declared_rank_orders_household_services() {      // cash 32: goods 16, then one service of 16
    for (ranks, want) in [([0, 0, 0], [(s6(), 4), (s7(), 0)]), ([1, 3, 2], [(s6(), 0), (s7(), 4)])] {
        // admit_household_orders gives [(g(), 4)]; then ServiceClose::new(&catalog, &mut state, &mut t, None)
        // the performance rows of AccountId::Household(h()) as (good_id, admitted_quantity), sorted == want
    }
    // with p8() added (cash 32, unranked) beside h() ranked [1, 3, 2]: h()'s rows == the ranked want,
    // and p8()'s rows == [(s6(), 4), (s7(), 0)], the all-zero result
}
#[test] // pins Decision 1; passes before the sorts change
fn food_and_its_pantry_are_bought_before_any_service() { // ranks [1, 2, 3], cash 32;
    // g()'s policy: target_closing_stock 4, maximum_purchase 8 (need 4 + pantry 4)
    // goods (good, requested, admitted) == [(g(), 8, 8)]
    // services (good, requested, admitted) == [(s6(), 4, 0), (s7(), 4, 0)]; household cash 0
}
#[test]
fn need_ranks_are_whole_distinct_goods_first_and_first_applicable_only() {
    for ranks in [[1, 2, 0], [1, 2, 2], [2, 1, 3]] { // partial; repeated; a service before the good
        assert_eq!(MaterialCatalog::try_new(ranked_opening(32, ranks).0).err(),
                   Some(MaterialCircuitError::HouseholdNeedRankInvariant));
    }
    assert!(MaterialCatalog::try_new(ranked_opening(32, [1, 5, 9]).0).is_ok()); // gaps allowed
    // h() ranked [1, 3, 2] beside p8() all rank 0 -> Ok (the rule is per principal)
    // with ranks [1, 3, 2]: policy None (with and without payouts), HighDemandBeforeSpare
    //   -> try_new(..).err() == Some(MaterialCircuitError::WireVersion)
}
#[test]
fn ranked_catalog_bytes_are_version_six_and_one_rank_byte_per_need() {
    // d = try_new(ranked_opening(32, [1, 3, 2]).0).into_definition(); u = d with every rank 0
    // r[28..30] == 6u16.to_be_bytes(); u[28..30] == 5u16.to_be_bytes(); r[..28] == u[..28];
    // r[30..u.len()] == u[30..]; r[u.len()..] == [1, 3, 2]
}
```

  In `weighted_freight.rs`, the registry test asserts `try_from(38) ==
  Ok(HouseholdNeedRankInvariant)`, and its last line becomes `try_from(39).is_err()`. Run `mise run
  rust:test:q -- -p babylon-material-circuit -E 'binary(babylon_material_circuit) &
  test(households_tests)'`. Expect a compile failure: `HouseholdNeed` has no field `rank`.
- [ ] **Step 3: Implement the engine** as in Interfaces and Decisions 2 to 5. Add `rank: 0` to the 20
  literals. In persistence, `HouseholdNeedCoefficient` gains `rank: u8` (templates.rs:77 sets
  `rank: 0`), compile.rs:325 passes `rank: need.rank` and organizer.rs:421 passes
  `rank: coefficient.rank`; every rank is still 0, so no persistence byte moves. Add the contract
  lines. Pin `MATERIAL_CIRCUIT_SOURCE_SHA256` to the `sha256sum` of the edited
  `contracts/material_circuit_v4.yaml`; the value is known only from that run. Run the Step 2
  command, then `-E 'binary(weighted_freight)'`. All pass, Step 1's pins included. Then reverse each
  sort key in turn (goods, services) and see `a_declared_rank_reverses...` or
  `a_declared_rank_orders...` fail; restore them. Run `mise exec -- cargo check -p
  babylon-persistence -p babylon-tick --all-targets --locked`; it must pass before the commit.
- [ ] **Step 4: Commit the engine.** `git add` the material-circuit files, the contract, the
  persistence and tick literal files, and the four persistence files of Step 3 (`model.rs`,
  `templates.rs`, `compile.rs`, `organizer.rs`). Subject: `feat(material-circuit): admit a ranked
  household's needs in its declared order`.
- [ ] **Step 5: Write the failing persistence tests** in `tests/national_household_units.rs`. They use
  the binary's opening from Task 3, or the `build_national_opening` call of
  `tests/national_opening.rs:10-63`, on the shipped file:

```rust
#[test]
fn wayne_households_carry_the_declared_order_and_others_none() {
    // keys: (good_id, unit_id) -> label key, from opening.commodity_labels
    // for each seed in opening.households: its template's needs as (key, rank), sorted by rank
    // Wayne = EconomicLocation::County(c) with c.geoid().as_bytes() == *b"26163"
    // Wayne ordinary: [("food",1),("materials",2),("utility",3),("housing",4),
    //                  ("household_services",5),("public_provision",6)]
    // Wayne collective residence: [("food",1),("utility",3),("household_services",5),("public_provision",6)]
    // every other seed: every rank 0; at least one Wayne seed and one other seed exist
}
#[test]
fn the_compiled_catalog_carries_wayne_ranks_and_is_admitted() {
    // compile the opening as national_household_controls.rs `assert_admitted_state` does;
    // every compiled.catalog.household_needs row of a Wayne principal has its template need's rank,
    // every other row has rank 0; MaterialCatalog::try_new(compiled.catalog) is Ok
}
#[test]
fn going_without_is_refused_without_first_applicable_companies() {
    // the shipped file with [companies] condition_order = HighDemandBeforeSpare
    // -> the opening build fails with NationalOpeningError::Policy
}
```

  Change `national_household_controls.rs:116` to `4`. Run `mise run rust:test:q -- -p
  babylon-persistence -E 'binary(national_household_units) & (test(wayne_households_carry) |
  test(the_compiled_catalog) | test(going_without_is_refused))'`. They fail on their assertions:
  every rank is 0, and the third policy builds.
- [ ] **Step 6: Implement persistence** as in Decision 6. Write the ADR306 ruling for Decision 1.
  Run Step 5's command and `-E 'binary(national_opening)'`; both pass. A pinned digest of a campaign
  captured from the shipped file may move. Pin it again in this commit, and name the test in the
  commit body. A pin of a campaign without the section must not move; if one does, stop.
- [ ] **Step 7: Scoped gate, then commit.** Run fmt, clippy, the binaries above, then `mise run
  rust:test:q -- -p babylon-material-circuit`, `-p babylon-persistence` and `-p babylon-tick`.
  `git add` the persistence files, the test binary, the support file and the ADR306 file. Subject:
  `feat(persistence): give Wayne's households the declared order of going without`.

### Task 7: The screens

Design 7.5 (cited by section), with the words of 7.1 and 7.4 and decisions C1, C11 and C12. The
roster folds by band, then household unit, then position, over today's 8 slots and today's
control-socket actions. It shows who went without, each household unit's sentence, its money when
earned, and wealth by band beside the law's thirds. Every figure arrives in the projection
(Task 5); the client only formats.

**Files:**
- Modify: `rust/crates/babylon-client/src/organizer/county.rs`: `band_line` (98), `who_works`
  (118), `name_of` (138), `income_lines` (166), `position_line` (212), `roster_page` (271),
  `page_count` (280), `page_after` (285), `keep_page` (296), `control_visible` (307),
  `control_enabled` (328), `perform_control` (347), `slot_selected` (376), `roster_lines` (389),
  `roster_header` (400), `spawn_roster` (893), `paint_labels` (918); remove `slot_position` (251)
  and `slot_key` (262); add the items under Produces
- Modify: `organizer/client.rs`: `OrganizerClient` (a field beside `roster_page`, 289),
  `standing_clause` (222); `organizer/ui.rs`: `TextPart` (189), `painted_button` beside `button`
  (231), `inspect` (1719), `paint_text` (2128)
- Modify: `organizer/qualification_input.rs`: `Pending` (497-499), `Pending::new` (509-517),
  `presentation_applied` (2140-2153), the test helper `pending` (3775)
- Modify: `rust/crates/babylon-persistence/src/organizer_runtime/county_review.rs`:
  `session_signal_text` (the format string at 278-279)
- Modify: `tools/devtools/national_windowed_qualification.py`: `PlannedChoice` (818) and its
  `at_period` (859-866), `ControlChannel.perform` (the roster checks at 1383-1393),
  `open_review_contact` (1547)
- Test: `organizer/county_tests.rs` (incl. `app_with_roster`, 192); `organizer/qualification_input.rs`
  (`county_roster_actions_are_applied_by_the_ordinary_handlers_and_reported`, 4096);
  `babylon-persistence/src/organizer_runtime/county_review_tests.rs` (349, 366, 426);
  `tests/unit/tools/test_national_windowed_qualification.py` (1643-1795)

**Interfaces:**
- Consumes (Task 5, in `babylon-practice-contract` `county_review`, re-exported by
  `babylon_persistence::runtime_session` beside `PositionView` and `workplace_text`; Task 5 adds
  `household_units: None` to every literal, the client's `fixture()` included):

```rust
pub struct HouseholdUnitsView {        // CountyReviewProjection.household_units: Option<_>, serde default + skip
    pub facts_period: Option<u64>,     // the period the facts are from; None before the first close
    pub needs: Vec<String>,            // need labels, in the declared order of going without
    pub bands: Vec<BandUnitsView>,     // four, top first
    pub units: Vec<HouseholdUnitView>, // one per (group, band) the config holds, sorted by (group, band)
}
pub struct BandUnitsView { pub band: Band, pub went_without: Vec<u64>,      // households, per need
    pub wealth_basis_points: u16, pub ownership_to_needs_basis_points: u64 } // C11's two shares
pub struct HouseholdUnitView { pub group: u32, pub band: Band,
    pub went_without: Vec<u64>,        // went_without(required, unmet, households), per need
    pub not_supplied: Vec<u64>,        // went_without(required, unsupplied, households), per need
    pub wage_tax_short: bool,          // assessed > collected in the period closed
    pub earned: Option<HouseholdUnitEarned> }
pub struct HouseholdUnitEarned { pub households: u64, pub closing_cash_micros: i128,
    pub wages_micros: i128, pub wage_tax_assessed_micros: i128, pub wage_tax_collected_micros: i128,
    pub support_micros: i128, pub aid_micros: i128, pub ownership_income_micros: i128,
    pub unpaid_cost_micros: Vec<i128>, // per need: unpaid × the period's price
    pub free_hours: u64 }
```

- Produces:

```rust
// county.rs (named RosterEntry: the kernel's county_review::RosterRow, types.rs:249, is another thing)
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub(super) enum RosterEntry { Band(Band), HouseholdUnit { band: Band, group: u32 }, Position(PositionKey) }
pub(super) fn visible_rows(view: &CountyReviewProjection, open: &BTreeSet<RosterEntry>) -> Vec<RosterEntry>;
pub(super) fn slot_row(view: &CountyReviewProjection, open: &BTreeSet<RosterEntry>, page: usize, slot: u8)
    -> Option<RosterEntry>;
pub(super) fn row_line(view: &CountyReviewProjection, row: RosterEntry) -> String;
pub(super) fn roster_page(view: &CountyReviewProjection, open: &BTreeSet<RosterEntry>, page: usize) -> Vec<String>;
pub(super) fn page_count(view: &CountyReviewProjection, open: &BTreeSet<RosterEntry>) -> usize;
pub(super) fn open_roster(client: &mut OrganizerClient);          // page 0, everything folded
pub(super) fn roster_buttons(client: &OrganizerClient) -> Vec<String>; // empty unless the roster is open
pub(super) fn household_unit_sentence(units: &HouseholdUnitsView, unit: &HouseholdUnitView) -> String;
pub(super) fn wealth(view: &CountyReviewProjection) -> Option<String>; // None without household_units
// client.rs, on OrganizerClient (Default stays derived)
pub(super) roster_open: BTreeSet<super::county::RosterEntry>,    // holds Band and HouseholdUnit rows only
// ui.rs
TextPart::RosterButton(u8)
pub(super) fn painted_button(parent: &mut ChildSpawnerCommands, part: TextPart, action: OrganizerAction) -> Entity;
// qualification_input.rs, Pending: `roster_key: Option<PositionKey>` becomes
roster_entry: Option<super::county::RosterEntry>, roster_entry_open: bool,
```

```python
class RosterPress(FrozenRecord):        # national_windowed_qualification.py
    page: Annotated[StrictInt, Field(ge=0, le=2**32 - 1)]
    slot: Annotated[StrictInt, Field(ge=0, le=ROSTER_PAGE_ROWS - 1)]
# PlannedChoice: `page` and `slot` are replaced by
    presses: tuple[RosterPress, RosterPress, RosterPress] | None = None  # band, household unit, position
```

**Decisions:**
- *The rows* [Call]. A household unit row is a (band, group) pair read from `view.positions`, so a
  named group in two bands is two rows (C1) and a household unit with no position is never shown.
  Bands: the four of `view.bands`, top first, always. Household units: by their first position in
  the projection's order (the county's list). Positions: in the projection's order. Paging: 8
  visible rows a page.
- *Opens folded* [Call] (design 7.5). `Inspect(CountyRoster)` calls `open_roster`, and `keep_page`
  on a new `roster_period` clears `roster_open` and sets page 0; within a period a fold keeps the
  page, clamped to the last. It also makes a scripted press path fixed without a new reply field.
- *A slot press.* Band or household unit: toggle that row in `roster_open`; rows under it keep
  their state. Position: `choose(ReviewContact(key))`, as today. A fold is reading: enabled
  whenever the roster is open, in a past period and before the first session; only a position uses
  `reviewable`.
- *Button labels* [Call], painted each frame through `TextPart::RosterButton(slot)` (N = slot + 1):
  "Open (N)" or "Fold (N)" for a band or household unit, "Reach a household here (N)" for a
  position. Accessibility label: "{label}: {name}", the name being the band label, the household
  unit's "{band_label} · {group_label}", or a position's `position_name` + " · {a} at work · {s}
  looking for work"; a slot with no row: "Roster slot (N): no row on this page".
- *No new action, no reply field.* The v5 wire fixtures are SHA-pinned exact producer output
  round-tripped through `ControlState` (extra=forbid), so the reply keeps its fields and the
  Python planned contact names three presses instead of a page and slot.
- *Line conventions* (today's): segments joined by " · "; each sub-line two spaces deeper than its
  row (household unit rows indent 2, position rows 4); counts by `counted` (singular for one,
  grouped digits); money by `human_numbers::currency`; a share in basis points as
  "{bp/100}.{bp%100:02}%". A "for each household" figure is a total over the household unit's
  `earned.households` (always that `h`, on the unit row and its position rows alike, never
  `PositionEarned.households`), rounded down in the client: a rate of two of the unit's totals
  (ADR302 second rule), labelled "a household".
- *The rows' names.* The household unit row names its band and group, never one position's
  workplace: a budget group and a named group span several workplaces (C1, C3). Each position row
  names its workplace by `workplace_text(workplace_label, pay_mode)`.
- *The sentence* [Call], needs in `units.needs` order, lists joined "a, b and c": "Paid for {needs
  with went_without 0}." "Went without {needs with went_without > not_supplied}." "Not supplied
  with {needs with not_supplied > 0}." "Wage tax not collected in full." when `wage_tax_short`;
  empty clauses omitted; "No period has closed yet." when `facts_period` is `None`. With
  `facts_period` `None` the band and household unit went-without lines also read "No period has
  closed yet." in place of the period's line.
- *Campaigns without household units* (saved v12 catalogs still open). `household_units` is
  `None`: no sentence, went-without, money or wealth lines; the level noun stays "budget group";
  "(the group's total, not a household's)", "(the group's total)" and "Homes and wealth are not in
  this slice." stay, because they are true there. With household units they go (design 7.4).
- *Relief words* (C12): "relief unit(s)" in `band_line`, `position_line`, the `name_of` fallback
  and the two named strings. In `position_line` the rank clause reads "rank {r} · {n relief
  unit(s)} paid · {m} unpaid" and the earned line "{h households}, {r} reached · a relief unit is
  worth {stake} to each". Session, ledger and preview texts speak only of relief and keep "unit".

Strings with `household_units` present (examples are the test values):

| Row | Text |
|---|---|
| band | `{band_label} · {households} · {k household unit(s)}` (k counts the household unit rows shown, so Next 9% reads `0 household units`) + `\n  Went without in period {p}: {need} {n households} · …` (needs with n > 0) or `\n  Nobody went without in period {p}.` |
| household unit | `  {band_label} · {group_label} · {k position(s)}` + `\n    {sentence}` + the went-without line at 4 + earned block or `\n    Amounts are earned by contact. Reach a household in this household unit.` |
| earned | `\n    {h households} · cash at the close {c} · {c/h} a household` `\n    Wages {w} · wage tax assessed {a} · collected {t}` `\n    County support {s} · mutual aid {m} · ownership income {o} · {o/h} a household` `\n    Could not buy: {need} {cost} · …` or `Could not buy: nothing.` `\n    Free hours: {h}` |
| position | `    {workplace_text} · {a} at work · {s} looking for work · {n relief unit(s)} held` + the rank clause and earned line of *Relief words*; income labels "(the household unit's total)", ownership adds ` · {o/h} a household` |
| header | who works (last line `Bands are set at the opening.`), then `wealth`, then `\n\nHousehold roster · page {n} of {pages} · {k} rows open · press a band to open its household units and a household unit to open its positions` |
| wealth | `\n\nWealth by band, from the household units' net assets, beside the law's thirds (Designed)` `\n{band_label} · {pct} of household wealth · the law: a third` (Bottom 50%: `the law: none`) `\nHomes are not in yet.` `\nPaid from ownership against what needs cost: Top 1% {pct} · Next 9% {pct} · Next 40% {pct} · Bottom 50% {pct}` |

- [ ] **Step 1: Write the failing pure tests** in `county_tests.rs`. Add `household_unit_key(group,
  band, crew, at_work, units)` (`PositionKey { group, ..key(..) }`), `household_unit_earned()`
  (households 5, cash 1_250_000_003, wages 2_400_000_000, assessed 240_000_000, collected
  240_000_000, support and aid 0, ownership 7, `unpaid_cost_micros` [0, 0, 1_500_000_000], free
  hours 120) and `household_units()`: `..fixture()` with positions `[(1, Top1, None, 0, 0) rank 1,
  (0, Next40, Some(0), 1, 0) rank 2 earned, (0, Bottom50, Some(0), 2, 1) rank 3, (0, Bottom50,
  Some(0), 1, 0) rank 4]`, and `household_units` with `facts_period: Some(3)`, needs food, utility,
  housing; bands Top1 [0,2,0] 98 bp 31_250 bp, Next9 [0,0,0] 902 10_417, Next40 [0,0,12] 4_110 0,
  Bottom50 [3,0,40] 4_890 0; units (0, Bottom50) [3,0,40] [0,0,0] short, (0, Next40) [0,0,12]
  [0,0,0] `Some(household_unit_earned())`, (1, Top1) [0,2,0] [0,2,0], (2, Next9) with no position.
  Tests (assertions as code, exact values; lines broken under 120 columns):
  - `the_roster_opens_folded_and_opens_band_by_band_and_unit_by_unit`: folded, `visible_rows` is
    the four `RosterEntry::Band`s top first; with Next 9% and Bottom 50% open it is those four plus
    `HouseholdUnit { band: Bottom50, group: 0 }` ("group 2 has no position"); with that unit open,
    `[5..]` is `Position(positions[2].key)`, `Position(positions[3].key)`.
  - `a_household_unit_shows_who_went_without_in_public_and_its_money_only_when_earned`: the
    Bottom 50% unit's `row_line` starts with `"  Bottom 50% · Wayne households · "`, contains
    `"Went without in period 3: food 3 households · housing 40 households"`, `"Paid for utility.
    Went without food and housing. Wage tax not collected in full."`, `"Amounts are earned by
    contact. Reach a household in this household unit."` and no `'$'`. The Next 40% unit contains
    `"5 households · cash at the close $1,250.00 · $250.00 a household"`, `"Wages $2,400.00 · wage
    tax assessed $240.00 · collected $240.00"`, `"ownership income $0.00 · $0.00 a household"`,
    `"Could not buy: housing $1,500.00"`, `"Free hours: 120"`, `"Paid for food and utility. Went
    without housing."`. `household_unit_sentence(hu, &hu.units[2])` == `"Paid for food and housing.
    Not supplied with utility."`; with `facts_period: None` the sentence of `units[0]` and the
    Bottom 50% band row read `"No period has closed yet."`. `Band(Next9)` contains `"0 household
    units"` and `"Nobody went without in period 3."`.
  - `a_position_row_names_its_workplace_and_its_relief_units`: `row_line(&household_units(),
    Position(positions[1].key))` contains `"Wayne plant"`, `"1 relief unit held"`... wait no: the
    key's units are 0, so `"0 relief units held"`, `"rank 2 · "` + `"relief unit"` + `" paid"`,
    `"Ownership income (the household unit's total)"`, `"a relief unit is worth"`, and `" · $0.00 a
    household"`. On `fixture()`: `HouseholdUnit { band: Top1, group: 0 }` contains
    `"budget group"`; `Position(positions[0].key)` contains `"(the group's total, not a
    household's)"`; `who_works(&fixture())` contains `"0 relief units"`; `name_of` of an unknown
    key contains `"relief unit"`.
  - `wealth_by_band_stands_beside_the_laws_thirds_and_says_homes_are_not_in`: `wealth` contains
    `"Top 1% · 0.98% of household wealth · the law: a third"`, `"Bottom 50% · 48.90% of household
    wealth · the law: none"`, `"Homes are not in yet."` and `"Paid from ownership against what
    needs cost: Top 1% 312.50% · Next 9% 104.17% · Next 40% 0.00% · Bottom 50% 0.00%"` (a `let pin`
    split over two lines); `wealth(&fixture())` is `None`; `who_works(&household_units())` ends
    with `"Bands are set at the opening."`.
  - `the_folded_roster_pages_by_eight_rows_and_starts_folded_in_a_new_period`: `paged(10)`, open =
    `{Band(Bottom50), HouseholdUnit { Bottom50, 0 }}`: `page_count` is 1 folded and 2 open;
    `roster_page(.., 1).len()` is 7; `slot_row(.., 1, 1)` is `Position(key(Bottom50, Some(0), 4,
    0))`, `slot_row(.., 1, 7)` is `None`. Then, as code: an `OrganizerClient` with `county_review:
    Some(view)`, `roster_page: 1`, `roster_open: open`; `keep_page` with the same view keeps page 1
    and the open set; with `roster_period: 4` it gives page 0 and an empty `roster_open`.
- [ ] **Step 2: Run** `cd /media/user/dev-ssd/worktrees/households-homes/babylon && mise run
  rust:test:q -- -p babylon-client -E 'binary(babylon_client) & test(organizer::ui::county_tests)'`.
  Expected: compile failure (`RosterEntry`, `visible_rows`, `row_line`, `household_unit_sentence`,
  `wealth` do not exist).
- [ ] **Step 3: Implement the row model and the texts** in `county.rs` (Produces, the strings
  above), `roster_open` on `OrganizerClient`, `TextPart::RosterButton` and `painted_button` (the
  bundle of `button`, its label child carrying the part and starting empty) in `ui.rs`;
  `spawn_roster` uses `painted_button` for the 8 slots; `paint_text` paints `RosterButton(slot)`
  from `roster_buttons`. Also move `control_visible`, `control_enabled`, `perform_control`,
  `slot_selected` and `Pending::new` onto `slot_row` (positions only, as today), so the library
  compiles. Run Step 2's command. Expected: the library compiles; the test module fails to compile
  only at the old calls that Step 4 changes (`slot_key`, two-argument `roster_page`/`page_count`).
- [ ] **Step 4: Change the pinned tests**, old -> new, give `app_with_roster` a projection parameter
  (`app_with_roster(fixture())` at today's callers), and add the window test below:

| Test (line) | Old | New |
|---|---|---|
| `an_uncontacted_position_shows_structure_and_hides_amounts` (256) | `roster_page(&fixture(), 0)`, lines found by `"no wage"` and `"Next 40%"` | `row_line` of `Position(positions[0].key)` and `Position(positions[1].key)`; the six pins stay; add `"rank 1 · 0 relief units paid"` |
| `the_roster_says_once_…_moved_since` (275) | `after[0]` has `"rank 1"`; line `starts_with("Next 9%")` | `row_line(&held(), Position(positions[0].key))` has `"rank 1"`; `Position(positions[3].key)` has the moved text |
| `choosing_a_slot_reviews_and_confirms_a_review_contact` (293) | press `"Reach a household here (1)"` | press `"Open (1)"`, `"Open (2)"`, `"Reach a household here (3)"` (Top 1%, its household unit, its position) |
| `the_roster_counts_who_works_…` (332) | every `roster_page` line starts with a band | with all rows open: band rows start with a band label, household unit rows with `"  "` + a band label, positions with `"    "` |
| `a_past_period_disables_the_slots_with_a_reason` (350), `each_reason_a_slot_is_disabled_…` (396) | `!enabled(ChooseRosterSlot(0))` | with Top 1% and its household unit open: `enabled(ChooseRosterSlot(0))` (a fold) and `!enabled(ChooseRosterSlot(2))` |
| `no_county_text_names_a_class` (472) | `roster_page(&fixture(), 0)`, `roster_page(&held(), 0)` | `row_line` of every row with all open, of `fixture()`, `held()` and `household_units()`, plus `wealth(&household_units())` |
| `the_roster_pages_by_eight_and_resets_…` (578) | slots of a flat page | replaced by Step 1's paging test and the window test below |
| `a_slot_button_is_named_…` (628) | `"Reach a household here (1): Top 1%"`, `"no position on this page"` | `"Open (1): Top 1%"`, `"Roster slot (8): no row on this page"` |
| `a_session_that_changes_whether_…` (709, 715) | `"…the county paid no household unit."` | `"…the county paid no relief unit."` |
| `county_roster_actions_are_applied_…` (qualification_input 4096) | page, then slot 1 of page 1 = at_work 9 | slots 8, 9, 255 refused; slot 3 (Bottom 50%) and slot 4 (its household unit) `"applied"`, inspector `"CountyRoster"`; `roster_next_page` applied, page 1; again refused; slot 1 drafts `at_work` 4 |
| `county_review_tests.rs` 349, 366, 426 | `"household units"` | `"relief units"` |

  `a_slot_press_folds_a_band_or_unit_and_chooses_a_position`, as code:
  `app_with_roster(household_units())`; press `"Household roster"`, `"Open (4)"`: `roster_open ==
  {Band(Bottom50)}`; press `"Open (5)"`: the household unit joins; press `"Fold (4)"`: four rows
  visible, the unit stays in `roster_open`; press `"Open (4)"`, `"Reach a household here (6)"`:
  `choice == ReviewContact(household_units().positions[2].key)`, inspector `Closed`; press
  `"Household roster"`: `roster_open` is empty and `roster_page` is 0. Run Step 2's command.
  Expected: Step 1's tests and the rewritten pins PASS; the window test, the two fold-enabled pins
  and the qualification test FAIL (folds are not yet performed or enabled).
- [ ] **Step 5: Implement the controls**: the fold in `control_enabled`, `perform_control`,
  `slot_selected` and `paint_labels`; `inspect` calls `open_roster` for `CountyRoster`;
  `Pending::new` captures `slot_row` and whether it was open; `presentation_applied` treats a fold
  as applied when `roster_open.contains(&entry) != roster_entry_open`; C12 strings in
  `standing_clause` and `session_signal_text`. Run Step 2's command, then `mise run rust:test:q --
  -p babylon-client -E 'binary(babylon_client) & test(organizer::qualification_input::tests::county_)'`
  and `mise run rust:test:q -- -p babylon-persistence -E 'binary(babylon_persistence) &
  test(organizer_runtime::county_review_tests)'`. Expected: PASS.
- [ ] **Step 6: Play the folded roster in the real game.** No other cargo process may run (the
  launcher builds). Copy the driver
  `/home/user/.claude/projects/-media-user-data-worktrees-e87c-babylon/079b909b-9fac-4045-80e8-2e993d18119f/handoff-d7/wf/play_check.py`
  to `/media/user/dev-ssd/worktrees/households-homes/play-check-369/` and change only its
  `choose_contact`: for Bottom 50% (slot 3) then Next 40% (slot 2), open the roster, press the
  band, press each household unit slot after it, then each position slot under it, review, and
  confirm the first preview with a place open. Check `docker exec babylon-pg-isolated psql -U test
  -d postgres -tAc 'SELECT 1'` and note `docker inspect -f '{{.State.StartedAt}}'
  babylon-pg-isolated`; create the database: `docker exec babylon-pg-isolated psql -U test -d
  postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE babylon_playcheck_369 OWNER test;"`. Run:

```sh
cd /media/user/dev-ssd/worktrees/households-homes/babylon && PLAY_CHECK_DATABASE=babylon_playcheck_369 \
  BABYLON_PG_DATA=/media/user/data/babylon-pg-17 DISPLAY=:0 mise exec -- uv run --frozen python \
  /media/user/dev-ssd/worktrees/households-homes/play-check-369/play_check.py \
  /media/user/dev-ssd/worktrees/households-homes/babylon /media/user/dev-ssd/worktrees/households-homes/play-check-369/first --until 5
```

  Pass: frame `03-household-roster-opening` shows four band rows and no position, the wealth block
  and "Homes are not in yet."; a band opens to household units and a household unit to positions,
  each position naming its workplace; a contact is confirmed in period 3; no text runs outside its
  panel at 1366x768; `StartedAt` is unchanged. Report what was seen, that the window opened on `:0`
  with sound, and that the continue pointer moved. A fault found here is fixed in this task before
  Step 7.
- [ ] **Step 7: The Python planned contact.** In the test file: `planned_contact` gives `presses`
  `[{page 0, slot 3}, {page 0, slot 4}, {page 1, slot 2}]` and no page or slot;
  `test_a_planned_review_contact_names_its_roster_page_slot_and_position` becomes
  `..._names_its_three_roster_presses_and_position` and pins that `at_period` copies `presses`.
  The refusal cases become: no presses or no position for `review_contact`; two presses; a press
  with slot 8 or page -1; presses whose pages decrease (pages 1, 0, 0); an aid allocation; presses
  or a position on `hold`; and the old `page`/`slot` keys (extra forbidden). `serve_roster` answers
  slots 3 and 4 with `"applied"` and inspector `"CountyRoster"`, and slot 2 as today. Expected
  requests: `["status", "inspect_county_roster", {"choose_roster_slot": {"slot": 3}},
  {"choose_roster_slot": {"slot": 4}}, "roster_next_page", {"choose_roster_slot": {"slot": 2}},
  "review", "confirm", "status"]`. A fold reply that closes the roster is refused with "native
  roster fold closed the roster". Correct the docstring at test line 1784 ("The client keeps its
  roster page between openings"), now false. Run `mise run test:q --
  tests/unit/tools/test_national_windowed_qualification.py`: FAIL; implement `RosterPress`,
  `presses`, the decreasing-page validator, `at_period` copying `presses`, `open_review_contact`
  (open the roster, move page by page to each press's page, press; only the last press passes
  `expected_contact`) and, in `perform`, run the draft and position checks only when
  `expected_contact` is not None; without it a `ChooseRosterSlot` reply must keep inspector
  `"CountyRoster"`, else the fold refusal. Run: PASS.
- [ ] **Step 8: The scoped gate** for `babylon-client` and `babylon-persistence`, then
  `mise run test:q -- tests/unit/tools/test_national_windowed_qualification.py
  tests/unit/tools/test_national_qualification_v3_wire.py`. Expected: PASS, the v5 wire digests
  unchanged.
- [ ] **Step 9: Play again at the end**, as Step 6 with `--final` and the out directory
  `.../play-check-369/final`. Pass: after the contact the contacted household unit's row shows its
  money and every other one says "Amounts are earned by contact."; each household unit shows a
  sentence; the session notice reads "relief unit" where it names relief. Leave the database and
  report its name.
- [ ] **Step 10: Commit.** `git add` `county.rs`, `county_tests.rs`, `client.rs`, `ui.rs`,
  `qualification_input.rs`, `organizer_runtime/county_review.rs`, `county_review_tests.rs`,
  `national_windowed_qualification.py`, `test_national_windowed_qualification.py`; then
  `PYTHONPATH=src mise exec -- git commit -q -F <message file>` with subject `feat(client): fold the
  household roster by band and household unit`, a body ending `Part of PER-369` and the co-author
  trailer; check `git log --oneline -1` moved.

### Task 8: Playthroughs, lessons, the first gate report and every gate

Design section 9, item 8 and the gate's first bullet; sections 7.4 ("The recorded playthroughs
change") and 7.6 (the last bullet: drift is reported, not an error). The four County Review lines
are recorded again on household units into a new directory; the housing crew is diagnosed; two
lessons and the how-to are made true; the first gate report goes to the Director; every gate runs.

**Files:**
- Modify: `rust/crates/babylon-persistence/tests/observer_material_live/county_review_playthroughs.rs`
  (`reports_dir`, the module doc line 7, `period_json`, `run_json`, `replay_placement`,
  `placement_bounds`, `assert_contact_spreads`, `assert_every_run`, both ignored tests; new helpers
  below)
- Modify: `rust/crates/babylon-persistence/tests/national_county_review.rs` (`print_wayne_opening_roster`,
  lines 363 and 427: its ignore text and path move to the new directory)
- Modify: `rust/crates/babylon-persistence/tests/national_household_units.rs` (Task 1's binary: the
  housing crew recorder)
- Modify: `tools/run_rust_postgres.sh` (the `county_review)` branch, lines 834-846)
- Create: in `reports/household-units-2026-11-20/`: `no-contact.json`, `one-position.json`,
  `two-positions.json`, `food-runs.json`, a sibling `<line>-units.json` for each, `placement-bounds.json`,
  `wayne-opening-roster.json`, `housing-crew.json`, `gate-report-1.md`; Modify: its `README.md`
  (Task 1's)
- Modify: `docs/tutorials/first-county-review.rst`, `docs/tutorials/index.rst`,
  `docs/how-to/organize-in-wayne.rst`; Create: `docs/tutorials/who-goes-without.rst`

**Interfaces:**
- Consumes: Task 5's `CountyReviewConfig.household_units: Option<CountyHouseholdUnits>`,
  `GroupPeriodFacts.purse: Option<UnitPurseFacts>`, `went_without(required: u64, unmet: u64,
  households: u64) -> Result<u64, CountyReviewError>`; the kernel's `pub fn apportion(total: u64,
  weights: &[u64], ties: Ties) -> Result<Apportionment, CountyReviewError>` (split.rs:32); Task 4's
  `wayne-unit-accounts.json` and `wayne-opening-units.json`; Task 1's `wayne-pooled-accounts.json`;
  Task 7's folded roster and its control-socket actions; `CapturedEconomicCatalog::
  capture_national_campaign`, `county_review_config()` (capture.rs:276), `opening()` (:355).
- Produces (all in the playthrough module unless named):
  - `fn household_unit_rows_json(facts: &CountyPeriodFacts) -> Vec<Value>` and its inverse
    `fn household_unit_rows_facts(rows: &[Value]) -> Vec<GroupPeriodFacts>`
  - `fn band_shares(total: u64, rows: &[(Band, u64)]) -> Vec<(Band, u64)>`
  - `fn household_units_json(run: &Run) -> Value`; `fn assert_household_unit_opening(run: &Run)`;
    `fn assert_household_units_add_back(run: &Run)`
  - `fn replay_placement(record: &Value, units: &Value, placement: Placement) -> Vec<u64>` and
    `fn placement_bounds(record: &Value, units: &Value, run: &Run) -> Value` (today each takes one
    record)
  - in `national_household_units.rs`: `fn input_before_household_units() -> EconomicCatalogInput`
    and the ignored test `housing_crew_diagnostic`

**Decisions:**
- *The new directory.* `reports_dir()` returns `../../../reports/household-units-2026-11-20`; the
  test names stay, so the runner's case list (`county_review_playthroughs |
  county_review_playthroughs_smoke`) is unchanged. `print_wayne_opening_roster` would otherwise
  overwrite `reports/county-review-2026-11-19/wayne-opening-roster.json` with the units' opening, so
  it writes `wayne-opening-roster.json` in the new directory. Reason: the County Review's records are
  history and the design's sources cite them by line.
- *The record split.* [Call] Measured on today's `no-contact.json` (462,155 B): `facts.groups` is
  about 218 B a group a period and `facts.crews` 187 B a crew a period. With 66 groups and 61 crews
  the one record would pass 1 MiB without the purse (about 1.08 MB), and the purse in serde form
  adds about 1.5 MB. So:
  `<line>.json` is `"version": 2`: today's keys, plus `"household_units_record": "<line>-units.json"`;
  in each period `facts.groups` is `[]` (so `CountyPeriodFacts` still deserializes) and `session`
  drops `lines`, `collective_lines` and `hour_charges`.
  `<line>-units.json` is `{"version": 1, "line", "record", "needs": [need keys in the config's
  order], "columns", "need_columns", "periods": [{"period", "groups", "lines", "collective_lines",
  "hour_charges", "went_without_by_band"}], "first_went_without"}`. A group row is an array in the
  order of `columns` = `["group", "closing_households", "free_hours", "taxed_wages_micros",
  "wage_tax_collected_micros", "ownership_income_micros", "support_income_micros",
  "aid_income_micros", "closing_cash_micros", "net_assets_micros", "wage_tax_assessed_micros",
  "needs"]`, `needs` an array of `[required, unmet, unpaid, unsupplied, cost_micros]`
  (`need_columns`). For a group with `purse: None`, columns 8 to 11 (`closing_cash_micros`,
  `net_assets_micros`, `wage_tax_assessed_micros`, `needs`) are each `null`; the row is never null.
  Lines are `[group, units, amount_micros]`, hour charges `[group, hours_in_room, hours_bringing]`,
  `first_went_without` rows `[group, need_index, period]`. `went_without_by_band` is an array in
  `band_counts` order (Top1, Next9, Next40, Bottom50) of `[band, [households for each need in
  `needs` order]]`; the per-unit counts are not stored again, they are read from the group rows'
  `needs`. Money stays a decimal string. Columns, not objects: about 22 KB a period, about 800 KB
  for 34 periods, about 960 KB at 40, close to the limit (see Step 3's fallback).
- *Who went without, by band.* A unit's count for a need is `went_without(required, unmet,
  closing_households)`, given to its one band. A unit in two bands (only the aid donors) divides it
  by `band_shares`: `apportion` over its rows' households at that period, weights in the order
  Bottom50, Next40, Next9, Top1, `Ties::InOrder` (C1 and C8's order). Output in `band_counts` order.
- *The doubling.* [Call] Design 7.4 makes the hours a household spends the unit's own. A unit short
  of free hours brings fewer, which today's assertion would call a failure. `assert_contact_spreads`'
  `open` also needs `no_time == 0` (the family's `asked_no_time + roll_no_time`), and each session's
  figures gain `"no_time"`. The doubling is still asserted while a place is open and hours last.
- *The housing crew.* Diagnosed in memory, not on PostgreSQL, on two openings with campaign
  `0x0026_1631_7036` and `ReplaySeed::new(319)`: today's (`input_before_household_units()`: the
  shipped input with the `NationalGamePolicy` source cut before `\n[household_units]\n`, compiler
  `national-world-v12`; use Task 4's cut if it already wrote one) and the units' (shipped,
  `national-world-v13`). The site is found from the county config: every crew labelled
  `"Wayne County: construction_housing (5)"`, asserted to share one `site_id`. The pooled run must
  reproduce the recorded wages of those crews before the record explains them.
- *The gate report* lives at `reports/household-units-2026-11-20/gate-report-1.md`. It states
  figures read from files. It decides nothing.

- [ ] **Step 1: Write the failing record tests** (not ignored; they run in the binary without a
  database, like the two tests at lines 1672-1724):

```rust
#[test]
fn a_units_record_gives_back_the_facts_the_replay_reads() {
    let (_, mut facts) = wage_county();
    let base = GroupPeriodFacts { group: 0, taxed_wages_micros: 48_000_000,
        wage_tax_collected_micros: 2_400_000, ownership_income_micros: 0,
        support_income_micros: 280_000_000, aid_income_micros: 0, free_hours: 1_200,
        closing_households: 10, purse: None };
    facts.groups = vec![
        GroupPeriodFacts { purse: Some(UnitPurseFacts { closing_cash_micros: 5_000_000_000,
            net_assets_micros: 5_600_000_000, wage_tax_assessed_micros: 2_400_000,
            needs: vec![NeedPeriodFacts { required: 25, unmet: 5, unpaid: 5, unsupplied: 0,
                cost_micros: 7_000_000_000 }] }), ..base.clone() },
        GroupPeriodFacts { group: 1, ..base },
    ];
    let rows = household_unit_rows_json(&facts);
    assert_eq!(rows[0][0], json!(0));
    assert_eq!(rows[0][11], json!([[25, 5, 5, 0, "7000000000"]]));
    assert_eq!(rows[1][8], Value::Null);
    assert_eq!(rows[1][11], Value::Null);
    assert_eq!(household_unit_rows_facts(&rows), facts.groups);
}

#[test]
fn a_two_band_unit_divides_who_went_without_by_households() {
    use Band::{Bottom50, Next40, Next9, Top1};
    assert_eq!(band_shares(3, &[(Bottom50, 3), (Next40, 1)]),
        vec![(Top1, 0), (Next9, 0), (Next40, 1), (Bottom50, 2)]);
    assert_eq!(band_shares(1, &[(Bottom50, 1), (Next40, 1)]),
        vec![(Top1, 0), (Next9, 0), (Next40, 0), (Bottom50, 1)], "a tie goes to the lower band");
}
```

- [ ] **Step 2: Run them and see them fail.** `cd /media/user/dev-ssd/worktrees/households-homes/
  babylon && mise run rust:test:q -- -p babylon-persistence -E 'binary(observer_material_live) &
  (test(units_record) | test(two_band_unit))'`. Expected: a compile error, ``cannot find function
  `household_unit_rows_json` ``.
- [ ] **Step 3: Implement the split and the assertions.** The signatures above. `play_and_record`
  and the final writes call `write_record` twice, for `<line>.json` and `<line>-units.json`, each
  with today's 1 MiB assertion. The new checks:
  - `assert_household_unit_opening` (called first in `assert_every_run`): `config.groups.len() ==
    66`, `config.crews.len() == 61`, `opening_roster.rows.len() == 111`; the four opening bands'
    households are `[7_006, 63_054, 280_236, 350_295]` in `band_counts` order; exactly one group
    has opening rows in two bands, and its label ends with `" (aid donors)"`.
  - `assert_household_units_add_back` (in `assert_every_run`): in every period, for each group `i`,
    `roster.groups[i].households` equals that group's `closing_households`; a group's rows lie only
    in the bands of its opening rows; every `Ordinary` group has `purse: Some` with as many needs as
    `config.household_units.needs`; for each period and need, the band counts in
    `went_without_by_band` add to the sum of the units' `went_without` counts, and a single-band
    unit's count lies wholly in the band of its rows.
  - `assert_bands`, `assert_county_keeps_its_word`, `assert_no_contact_moves_nothing`,
    `assert_untouchable_alike`, `assert_nobody_paid_when_relief_ends`, "the four final records
    differ" and `replay_agrees` keep their text. A line is now a unit's, and the "line of group"
    check is per unit with no change of code.
  - The smoke test writes both files to `temp_dir()/county-review-smoke` and asserts
    `units_bytes * 40 / 6 < RECORD_LIMIT_BYTES` and `main_bytes * 40 / 6 < RECORD_LIMIT_BYTES`
    (40 = `MAXIMUM_LAST_PERIOD`; only periods 4 to 6 hold sessions, so read both as lower bounds).
    It prints both sizes and the mean of the closes' `close_seconds`. If either projection fails,
    drop `cost_micros` from `need_columns` (the gate report recomputes it as `required` × the
    period's price from `facts`) and run the smoke test again; do not raise the limit.
- [ ] **Step 4: Run the record tests.** The Step 2 command: PASS. Then the smoke run:
  `cd /media/user/dev-ssd/worktrees/households-homes/babylon && BABYLON_POSTGRES_LIVE_FOCUS=county_review
  BABYLON_COUNTY_REVIEW_TEST=county_review_playthroughs_smoke mise run test:rust-postgres`.
  Today it takes about 10 minutes. Expected: PASS and the two sizes printed. If the mean close
  times 170 plus 465 s (five openings and five observer backlogs, README "Time") passes 3,000 s,
  raise that branch's `run_phase` limit from 3600 to 5400 and its comment's time.
- [ ] **Step 5: Record the playthroughs.** Same command without `BABYLON_COUNTY_REVIEW_TEST`. Today
  it takes 1,991 s; run nothing else that uses cargo while it runs. Expected: PASS, nine files written
  (four records, four units records, `placement-bounds.json`), each under 1 MiB with a trailing
  newline. A failed assertion keeps the records, because they are written first. Then
  `cd /media/user/dev-ssd/worktrees/households-homes/babylon && mise run rust:test:q -- -p
  babylon-persistence -E 'binary(national_county_review) & test(print_wayne_opening_roster)'
  --run-ignored ignored-only`. Expected: PASS, and `reports/household-units-2026-11-20/
  wayne-opening-roster.json` is written with 66 groups, 61 crews and 111 positions.
- [ ] **Step 6: Write the housing recorder.** In `national_household_units.rs`:
  `#[ignore = "writes reports/household-units-2026-11-20/housing-crew.json"] fn
  housing_crew_diagnostic()`. It plays both openings 34 periods with the session creation and the
  prepare, decode and commit loop of `national_household_lifecycle.rs:162-232`, playing today's
  opening to period 34 and dropping its session before capturing the units' opening (two live
  national sessions peak near 8 GB). For today's opening it sums `MemberLaborUseReceipt.
  accrued_wages` over the receipts whose `member_id` is the `crew_id` of a config crew labelled
  `"Wayne County: construction_housing (5)"` and asserts that sum is 104_766_720_000_000 in
  period 1, 16_814_208_000_000 in periods 2 to 27, 4_637_376_000_000 in period 28 and 0 in periods
  29 to 34 (the recorded no-contact run); any other member at the same `site_id` is recorded
  separately. For each period and opening it writes: site cash after commit; the
  site's `IncomeReceipt` sales and tax expense; its `MoneyTransferReceipt` outflows summed by
  purpose; `planned_hours`, `attended_hours`, `available_hours`, `accrued_wages`; the housing
  `ServiceMarketReceipt` (requested, admitted, performed, available capacity, old and next price,
  reason); its `ProcurementReceipt` desired against admitted; the `old_price` of housing at every
  Wayne site labelled `construction_housing` (the rent of the period). A mismatch of the wage series
  means the in-memory run is not today's run: report it, do not loosen it.
  Run: `mise run rust:test:q -- -p babylon-persistence -E 'binary(national_household_units) &
  test(housing_crew_diagnostic)' --run-ignored ignored-only`. Expected: about 12 minutes, PASS.
- [ ] **Step 7: The README.** In `reports/household-units-2026-11-20/README.md`: what was run (the
  commands, wall times, foundation digest, each line's world hash at its last period, first 16
  hex), what each line shows beside `reports/county-review-2026-11-19/README.md`, and what was not
  shown (homes, rent owed, the windowed run). Every figure is read from a file of the directory.
- [ ] **Step 8: Commit the records.** Scoped gate first (fmt, clippy, the two binaries above, then
  `mise run rust:test:q -- -p babylon-persistence`). First commit,
  `test(household-units): record the County Review playthroughs on units`:
  `county_review_playthroughs.rs`, `national_county_review.rs`, `tools/run_rust_postgres.sh` if
  Step 4 changed it, the nine records and `wayne-opening-roster.json`. Second commit,
  `test(household-units): diagnose the housing crew's wages`: `national_household_units.rs`,
  `housing-crew.json` and `README.md` (written in Step 7 after both runs).
- [ ] **Step 9: The lessons.** `first-county-review.rst`: every figure, string and position is read
  again from `one-position.json`, `no-contact.json` and the walk. These change: Step 3's "page 1 of
  14 · 111 positions" and Step 7's "page 1 of 17 · 131 positions" (line 154; the roster now opens
  folded by band, then household unit, then position); Step 2's eleven lines and "line 7" /
  "line 11", and the line numbers and amounts of Step 12 (lines 251-252) and Step 13 (line 290)
  (lines are per unit); "units held" becomes "relief units held"; Step 8's "eighth position of
  page 1" (from the new action log's probes); the paths of lines 320 and 343. `who-goes-without.rst`
  teaches one thing: read who went without food, utility or housing by band and by unit, read that
  unit's sentence, reach a household of it, and read the next period's count to see whether it
  ate. Its period is the later of period 3 and the first food row of `no-contact-units.json`'s
  `first_went_without`; if there is no food row, it uses the first row of any need, and the gate
  report states that first. Its figures and strings come from the walk. In `index.rst` it gets a
  toctree entry, item 5 of the numbered "Tutorials" list (after line 28), and a "What You'll
  Learn" paragraph. In `organize-in-wayne.rst` "Take a household to the county review": the folded
  roster, a paragraph on who goes without, "the county paid no relief unit" (C12's string), and the
  new directory beside the old one.
  Check: `cd /media/user/dev-ssd/worktrees/households-homes/babylon && PYTHONPATH=src mise exec -- uv
  run --frozen pre-commit run --files docs/tutorials/first-county-review.rst
  docs/tutorials/who-goes-without.rst docs/tutorials/index.rst docs/how-to/organize-in-wayne.rst`.
  Expected: rstcheck and doc8 (100 columns, `setup.cfg`) pass.
- [ ] **Step 10: Walk each lesson in the real game.** Copy `play_check.py` (memory note
  `bevy-client-scripted-play-check`; path in Task 7) to
  `/media/user/dev-ssd/worktrees/households-homes/play-task8/`, set its presses to the lesson's, and
  run it once for each lesson: `cd /media/user/dev-ssd/worktrees/households-homes/babylon &&
  DISPLAY=:0 mise exec -- uv run --frozen python ../play-task8/play_check.py "$PWD"
  ../play-task8/<lesson>`. Every string the lesson quotes must appear in `replies.jsonl` or a
  saved frame. Fix the lesson where it differs. Commit: `docs(tutorial): who goes without, and the
  first county review on units` (the four RST files).
- [ ] **Step 11: `gate-report-1.md`.** One section for each item, each figure named with its file
  and key:
  1. Who went without, by need, band and unit, and when: `<line>-units.json`
     `went_without_by_band`, the group rows' `needs` and `first_went_without`, four lines; the top
     1% unit named first (C14 expected it within about four periods).
  2. Could not pay against paid and not supplied (C9): sums of `unpaid` and `unsupplied` by need
     and line from the units records. Any `unsupplied` above zero is stated first.
  3. What the County Review's results became: `first_short_session`, `relief_ended_in_session`,
     `contact_spread` (where the doubling ended, and whether for want of hours) and each session's
     `household_units_payable` in `<line>.json`, beside the same keys of
     `reports/county-review-2026-11-19/<line>.json` (first short session 29 there).
  4. What each band was paid from ownership beside what its needs cost, and wealth by band beside
     the law's thirds ("Homes are not in yet."): `wayne-unit-accounts.json` beside
     `wayne-pooled-accounts.json`.
  5. The rent of every period: `housing-crew.json`, `old_price` at each Wayne housing site, both
     openings.
  6. Why the housing crew is paid nothing from about period 28: `housing-crew.json`, today's
     opening, periods 26 to 30. Cash against `planned_hours` × $24; sales against outflows; the
     outflows gated by the old payroll of $104,766,720 (the period-1 wages); and the company route of
     its distributions. Then whether units change it.
  7. Drift (design 7.6): for each pooled group and period, its figures in
     `wayne-pooled-accounts.json` (cash, wages, support, ownership income, wage tax, and each
     need's unmet) beside the sum over its units in `wayne-unit-accounts.json`, with the first
     period each one differs. Then, as a separate line, the units' mean close time against today's
     9.1 s (`close_seconds` of the four records). World hashes are listed in the README only.
  8. The gates of Step 12, and every failure the branch did not cause, with its evidence.
  9. For the Director [Director]: the identifier order of a short seller (C9), and whether to move
     the division of the shares forward if the top 1% unit goes without (design 7.2).
  Check: `.markdownlintignore` lists `reports/`, so pre-commit checks nothing here. Run
  `cd /media/user/dev-ssd/worktrees/households-homes/babylon && mise exec -- npx --yes
  markdownlint-cli@0.49.1 --config .markdownlint.yaml --ignore-path /dev/null
  reports/household-units-2026-11-20/gate-report-1.md` (or `awk 'length > 120'` on the file).
  Expected: no output.
- [ ] **Step 12: Every gate.** `cd /media/user/dev-ssd/worktrees/households-homes/babylon && mise run
  rust:check-no-docs > /media/user/dev-ssd/worktrees/households-homes/task8-whole-gate.log 2>&1`, in
  the background, about 35 minutes, with no other cargo process. Then `mise run check`, then `mise
  run check:ceremony`. Expected: PASS. Write the result into item 8 of the report. Commit:
  `docs(report): the first gate report of households and homes` (`gate-report-1.md`).

### Task 9: The housing reference tables

Design 7.15 "The tables" and 9 item 9. A new builder, copied from
`tools/make_national_household_reference.py`, captures 22 ACS 2024 five-year housing tables for the
3,144 counties as six parts by table family, each under the 1 MiB large-file gate
(`.pre-commit-config.yaml:209`), with one sources file and one metadata file, and pins the Federal
Reserve's accounts by wealth group for 2026:Q2. Nothing in the game reads them; Task 10 will.

**Files:**
- Create: `tools/make_national_housing_reference.py`,
  `tools/national_housing_reference_2024_sources.json`
- Create (built): `src/babylon/data/reference/economy/national_housing_reference_2024_<part>.csv.gz`
  (six parts), `src/babylon/data/reference/economy/national_housing_reference_2024.metadata.json`,
  `src/babylon/data/reference/national/federal_reserve_dfa_networth_levels_2026q2.csv`
- On the drive only: `/media/user/data/babylon-data/national_reference_2024/housing_<UTC date>/`
- Test: `tests/unit/tools/test_national_housing_reference.py` (Create)

**Interfaces:**
- Consumes, imported: from `tools/make_national_county_reference.py` `ROOT`, `ACS_GEO_ID`,
  `STATE_COUNTS`, `Cell`, `ReferenceBuildError`, `integer(raw: str, identity: str) -> int` (:221),
  `parse_acs_cell(raw: str, *, margin: bool) -> Cell` (:227), `sha256(path: Path) -> str` (:467),
  `_unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]` (:472),
  `provenance_path(path: Path) -> str` (:527), `ensure_output_paths(outputs: tuple[Path, ...],
  inputs: tuple[Path, ...]) -> None` (:534); from `tools/make_national_household_reference.py`
  `COUNTY_PATH`, `CountyControl` (:63), `known_sum(values: Iterable[int | None]) -> int | None`
  (:70, which already refuses past `MAX_I64`), `county_controls() -> dict[str, CountyControl]` (:112).
- Produces, in `tools/make_national_housing_reference.py`:

```python
Tables = Mapping[str, Mapping[str, tuple[tuple[Cell, Cell], ...]]]
SOURCE_MANIFEST = ROOT / "tools/national_housing_reference_2024_sources.json"
ARTIFACT_DIR = ROOT / "src/babylon/data/reference/economy"
METADATA_OUT = ARTIFACT_DIR / "national_housing_reference_2024.metadata.json"
WEALTH_OUT = ROOT / "src/babylon/data/reference/national/federal_reserve_dfa_networth_levels_2026q2.csv"
def part_path(directory: Path, part: str) -> Path  # <directory>/national_housing_reference_2024_<part>.csv.gz
def part_columns(part: str) -> tuple[str, ...]  # household COLUMNS order, see below
def source_paths(source_root: Path, manifest: Mapping[str, Any]) -> dict[str, Path]
def definitions(path: Path) -> dict[str, dict[str, str]]
def capture_table(path: Path, table: str, controls: Mapping[str, CountyControl]
                  ) -> dict[str, tuple[tuple[Cell, Cell], ...]]
def reconcile(tables: Tables, controls: Mapping[str, CountyControl]) -> dict[str, int]  # counties checked
def coverage(tables: Tables) -> dict[str, dict[str, Any]]  # kind: "count" | "dollars" | "median"
def bounded_parts(tables: Tables, counties: Iterable[str]) -> dict[str, bytes]  # part -> gzip bytes
def capture_wealth_accounts(path: Path) -> tuple[tuple[str, ...], ...]  # header row, then five rows
def build(source_root: Path, *, manifest_path: Path = SOURCE_MANIFEST, artifact_dir: Path = ARTIFACT_DIR,
          metadata_out: Path = METADATA_OUT, wealth_out: Path = WEALTH_OUT) -> dict[str, Any]
```

`part_columns(part)` is `county_geoid`, then for each table of the part, for each line, for E then
M, the `<T>_<E|M><line:03>_value`, `_raw` and `_status` columns (the household `COLUMNS` order,
`make_national_household_reference.py:51-60`).

The data, read from the pinned shells (`ACS20245YR_Table_Shells.txt`, sha `5b46f4af…b517d`). `PARTS`
maps each part to its tables in this order; `TABLES` follows it (22 tables, 166 lines):

| Part | Tables (lines) | `UNIVERSES` |
|---|---|---|
| `tenure` | B25003 (3); B25003A to I (3 each) | Occupied housing units; A to I "Occupied housing units with a householder who is " + White alone / Black or African American alone / American Indian and Alaska Native alone / Asian alone / Native Hawaiian and Other Pacific Islander alone / Some Other Race alone / Two or More Races / White alone, not Hispanic or Latino / Hispanic or Latino |
| `tenure_by_income` | B25118 (25) | Occupied housing units |
| `structure_and_vacancy` | B25032 (23), B25004 (8) | Occupied housing units; Vacant housing units |
| `value` | B25075 (27), B25077 (1) | Owner-occupied housing units |
| `mortgage_and_dollars` | B25081 (9), B25082 (3), B25080 (8), B25090 (3) | Owner-occupied housing units |
| `rent` | B25063 (27), B25064 (1), B25065 (1) | Renter-occupied housing units; B25064 and B25065: Renter-occupied housing units paying cash rent |

`MEDIANS = frozenset({"B25064", "B25077"})`; `DOLLARS = frozenset({"B25065", "B25080", "B25082",
"B25090"})`; every other table is `count`. `PARTITIONS` as (parent, members), with no key for
B25064, B25065 and B25077:

```python
{**{t: ((1, (2, 3)),) for t in ("B25003", *(f"B25003{r}" for r in "ABCDEFGHI"))},
 "B25118": ((1, (2, 14)), (2, tuple(range(3, 14))), (14, tuple(range(15, 26)))),
 "B25081": ((1, (2, 9)), (2, (3, 4, 8)), (4, (5, 6, 7))), "B25075": ((1, tuple(range(2, 28))),),
 "B25082": ((1, (2, 3)),), "B25090": ((1, (2, 3)),), "B25080": ((1, tuple(range(2, 9))),),
 "B25032": ((1, (2, 13)), (2, tuple(range(3, 13))), (13, tuple(range(14, 24)))),
 "B25063": ((1, (2, 27)), (2, tuple(range(3, 27)))), "B25004": ((1, tuple(range(2, 9))),)}
```

| Check (per county; skipped when a side is withheld) | Relation | Refusal |
|---|---|---|
| `household_control` | B25003_001 = the county reference's B11001 households estimate (the estimate only; B25003's margin is its own figure) | `household_control: <county>` |
| `EQUALITIES` | `income_total` B25118_001 = B25003_001; `income_owners` B25118_002 = B25003_002; `income_renters` B25118_014 = B25003_003; `mortgage_owners` B25081_001 = B25003_002; `value_owners` B25075_001 = B25003_002; `structure_total` B25032_001 = B25003_001; `structure_owners` B25032_002 = B25003_002; `structure_renters` B25032_013 = B25003_003; `rent_renters` B25063_001 = B25003_003; `value_dollars` B25080_001 = B25082_001 | `cross_table: <name>/<county>` |
| `race_001` to `race_003` | B25003A to G, line k, summed = B25003 line k (A to G partition the total) | `cross_table: race_00k/<county>` |
| `white_not_hispanic_001` to `_003` | B25003H line k <= B25003A line k (H and I overlap and are never summed) | `cross_table_bound: <name>/<county>` |

Wealth: `WEALTH_MEMBER = "dfa-networth-levels.csv"`, `WEALTH_QUARTER = "2026:Q2"`, `WEALTH_GROUPS =
("TopPt1", "RemainingTop1", "Next9", "Next40", "Bottom50")`, `WEALTH_HEADER` = the header row of the
table in Step 1. Values are parsed with `integer(raw, f"wealth_value: {group}")`; the five 2026:Q2
rows hold only non-negative integers. `MAX_PART_BYTES = 1_000_000` compressed;
`MAX_DECODED_BYTES = 8_388_608`.

**Decisions:**
- *A new artifact, not a wider one:* the household artifact's sha is pinned in Rust
  (`national_households/artifact.rs:29`) and its bytes reach the opening.
- *Six parts under one bound the builder enforces.* At the household artifact's rate (932,960
  bytes for 41 lines) 166 lines are about 3.8 MB; the largest part has 31 lines. `bounded_parts`
  compresses every part in memory and refuses `part_too_large: <part>` or
  `part_decoded_too_large: <part>` before any file is written. If a real part is refused, its last
  table moves to a new part named for its family, said in the commit; the bound never rises. [Call]
- *Medians are carried, never summed* (`kind` `median`, no `total_estimate` or
  `line_estimate_totals`); dollars are totals, checked like counts (`kind` `dollars`); no ratios.
- *Every check refuses on the first real build.* If the real files refuse a partition, a race sum or
  a cross-table check, stop and report the check and county to the lead: design 7.15 refuses an
  opening whose tables do not add up, so relaxing a check is a design change. [Director]
- *The Fed's table is the five 2026:Q2 rows as published,* in millions of dollars (the unit from the
  zip's `dfa-general-levels-detail-dictionary.txt`; the columns from `dfa-data-definitions.txt`).
  Three identities: `net_worth` (Net worth = Assets - Liabilities), `assets` (Assets = the seven
  asset columns), `liabilities` (Liabilities = Home mortgages + Consumer credit + Other
  liabilities). The published sums are rounded; this quarter's residuals are at most 1 (liabilities
  0). The builder refuses a residual above 1 (`wealth_identity: <group>/<identity>`), records each
  in `wealth_accounts.residuals[group][identity]`, corrects none. Public domain, cite the Board
  (`federalreserve.gov/disclaimer.htm`). [Call]
- *The two surveys are not captured.* No page found states the rental-owner survey's terms; the SCF
  is under the Board's statement, but no task of this plan reads either (wire-before-buy).
  `held_back` in the metadata names both and why; Task 10 cites design 7.15's Derived parts. [Call]
- *Not registered in `data-artifacts.yaml` yet:* audit 8.2 admits an entry with a wired consumer, so
  Task 10 registers by hand and `tests/unit/reference/test_data_artifacts.py:66` keeps
  `checked == 37` here. Never run `mise run data:artifacts`: it drops the hand-registered
  `national_*` entries.
- *Imported, not copied:* `CountyControl`, `county_controls`, `known_sum`, `integer`; the sources
  file is read with `_unique_object`. Ruff covers `tools/`, the gate's mypy does not
  (`.mise.toml:131`).

- [ ] **Step 1: Write the synthetic tests** in the new file, headed as
  `test_national_age_reference.py:1-13` with `import make_national_housing_reference as builder`.
  Helpers: `dat(path, table, estimates, margins=None)` writes one `26163` row (unlisted estimates
  "0", margins "5"); `CONTROL = {"26163": CountyControl(population=Cell(10, "10", "published"),
  households=(Cell(10, "10", "published"), Cell(5, "5", "published")))}` and `ZERO`, the same with
  households 0; `zero_tables(**cells)` gives every line of every table for `26163` estimate 0 and
  margin 0 unless named (`None` = missing); `shells(path, edit=None, header=None)` writes the shells
  header (or `header`), one `int` row per wanted line with its universe, and the real empty-id row
  `B25010|0.5|0||Average household size --|x|Occupied housing units|float`. Lines below may be
  wrapped by `ruff format` (Step 7).

```python
def test_definitions_bind_universes_and_refuse_edits(tmp_path: Path) -> None:
    assert len(builder.definitions(shells(tmp_path / "a"))) == 166  # B25010's empty id ignored
    for edit in [("B25003B_001", 6, "Households"), ("B25077_001", 7, "float"), ("B25064_001", 3, "")]:
        with pytest.raises(builder.ReferenceBuildError, match=r"^table_definition$"):
            builder.definitions(shells(tmp_path / edit[0], edit=edit))
    bad = "Table ID|Line|Indent|Unique ID|Label|Title|Universe|Kind"
    with pytest.raises(builder.ReferenceBuildError, match=r"^table_definition_schema$"):
        builder.definitions(shells(tmp_path / "s", header=bad))

def test_partitions_refuse_counts_and_dollars_and_skip_withheld(tmp_path: Path) -> None:
    ok = builder.capture_table(dat(tmp_path / "a", "B25003", {1: "10", 2: "6", 3: "4"}), "B25003", CONTROL)
    assert [pair[0].value for pair in ok["26163"]] == [10, 6, 4]
    for table, cells in [("B25003", {1: "10", 2: "6", 3: "5"}), ("B25082", {1: "100", 2: "60", 3: "41"})]:
        with pytest.raises(builder.ReferenceBuildError, match=f"partition: {table}/26163/1"):
            builder.capture_table(dat(tmp_path / table, table, cells), table, CONTROL)
    held = builder.capture_table(dat(tmp_path / "h", "B25003", {1: "10", 3: "-666666666"}), "B25003", CONTROL)
    assert held["26163"][2][0].status == "estimate_not_computable"

def test_medians_are_carried_and_never_totalled(tmp_path: Path) -> None:
    m = builder.capture_table(dat(tmp_path / "m", "B25077", {1: "2000001"}, {1: "-333333333"}), "B25077", CONTROL)
    assert (m["26163"][0][0].value, m["26163"][0][1].status) == (2000001, "moe_open_ended_median")
    d = builder.capture_table(dat(tmp_path / "d", "B25082", {1: "100", 2: "60", 3: "40"}), "B25082", CONTROL)
    report = builder.coverage({"B25077": m, "B25082": d})
    assert report["B25077"]["kind"] == "median"
    assert not {"total_estimate", "line_estimate_totals"} & set(report["B25077"])
    assert (report["B25082"]["kind"], report["B25082"]["total_estimate"]) == ("dollars", 100)

def test_cross_table_checks_refuse_by_name_and_skip_withheld() -> None:
    assert builder.reconcile(zero_tables(), ZERO)["income_total"] == 1
    assert builder.reconcile(zero_tables(B25118_001=None), ZERO)["income_total"] == 0
    for cells, error in [({"B25003_001": 1}, "household_control: 26163"),
                         ({"B25118_001": 1}, "cross_table: income_total/26163"),
                         ({"B25080_001": 1}, "cross_table: value_dollars/26163"),
                         ({"B25003A_002": 1}, "cross_table: race_002/26163"),
                         ({"B25003H_003": 1}, "cross_table_bound: white_not_hispanic_003/26163")]:
        with pytest.raises(builder.ReferenceBuildError, match=error):
            builder.reconcile(zero_tables(**cells), ZERO)

def test_parts_cover_every_table_once_under_the_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    assert sum(builder.TABLES.values()) == 166 and not builder.MEDIANS & set(builder.PARTITIONS)
    assert sorted(t for ts in builder.PARTS.values() for t in ts) == sorted(builder.TABLES)
    blobs = builder.bounded_parts(zero_tables(), ["26163"])
    assert list(blobs) == list(builder.PARTS)
    assert gzip.decompress(blobs["rent"]).decode().split("\n")[0] == ",".join(builder.part_columns("rent"))
    monkeypatch.setattr(builder, "MAX_DECODED_BYTES", 10)
    with pytest.raises(builder.ReferenceBuildError, match="part_decoded_too_large: tenure"):
        builder.bounded_parts(zero_tables(), ["26163"])
    monkeypatch.setattr(builder, "MAX_PART_BYTES", 10)
    with pytest.raises(builder.ReferenceBuildError, match="part_too_large: tenure"):
        builder.bounded_parts(zero_tables(), ["26163"])
```

  `test_source_digest_drift_refused_before_any_output`: write `b"original"` for every id of
  `[*builder.TABLES, "acs_table_shells", "dfa"]` and a manifest (contract
  `NationalHousingReference2024SourcesV1`, `county_reference_sha256`
  `28ad84a461f00c12489b11e0d770ad71bc3f09190dbc35774d725fc2333fec8e`, bytes 8, the sha of
  `b"original"`); overwrite `B25032` with `b"tampered"`; `build(tmp_path, manifest_path=...,
  artifact_dir=out, metadata_out=out / "m.json", wealth_out=out / "w.csv")` raises `source_digest:
  B25032` and `out` does not exist; a manifest naming `"contract"` twice raises
  `manifest_duplicate_key: contract`; a manifest without the `dfa` entry raises
  `source_manifest_coverage`. `test_wealth_accounts_keep_the_quarter_as_published`: a zip whose
  `dfa-networth-levels.csv` holds `WEALTH_HEADER`, one `2026:Q1` row and the five rows below gives
  back the header and those rows in `WEALTH_GROUPS` order; a renamed column raises `wealth_header`,
  a missing `Bottom50` row or a second `2026:Q2,TopPt1` row `wealth_groups`, and `TopPt1`'s net
  worth plus 2 `wealth_identity: TopPt1/net_worth`. The rows, `WEALTH_ROWS` in the test, are from
  the zip of 2026-11-20 (sha `e7f35451dc4df13986ef416d8659d00689ad98a9af79f4b09977e41be5e35919`):

| Date | Category | Net worth | Assets | Real estate | Consumer durables | Corporate equities and mutual fund shares | DB pension entitlements | DC pension entitlements | Unincorporated businesses | Other assets | Liabilities | Home mortgages | Consumer credit | Other liabilities |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026:Q2 | TopPt1 | 27867091 | 28168034 | 1966460 | 740398 | 16153923 | 297905 | 231774 | 4780991 | 3996583 | 300943 | 117243 | 52381 | 131319 |
| 2026:Q2 | RemainingTop1 | 32445932 | 33334932 | 4705920 | 421786 | 16735623 | 968137 | 1744881 | 4105038 | 4653546 | 888999 | 453093 | 111186 | 324720 |
| 2026:Q2 | Next9 | 67634079 | 71849146 | 15083366 | 1918467 | 24014368 | 7129334 | 7589929 | 5328226 | 10785457 | 4215067 | 3410241 | 524901 | 279925 |
| 2026:Q2 | Next40 | 53425884 | 62317685 | 23214769 | 3864458 | 7362060 | 9637124 | 6823101 | 2371758 | 9044416 | 8891801 | 6836034 | 1787916 | 267851 |
| 2026:Q2 | Bottom50 | 4278038 | 10272832 | 4821163 | 2169713 | 374196 | 488457 | 817645 | 168117 | 1433541 | 5994794 | 3160326 | 2643874 | 190594 |

- [ ] **Step 2: Run them and see them fail.**
  `cd /media/user/dev-ssd/worktrees/households-homes/babylon && mise run test:q --
  tests/unit/tools/test_national_housing_reference.py`. Expected: a collection error,
  `ModuleNotFoundError: No module named 'make_national_housing_reference'`.
- [ ] **Step 3: Implement the builder** to the signatures and data above. `definitions` also
  requires the header `Table ID|Line|Indent|Unique ID|Label|Title|Universe|Type`
  (`table_definition_schema`) and refuses an empty Unique ID in a wanted table (`table_definition`).
  `capture_table` is the household one with `PARTITIONS.get(table, ())`. `source_paths` requires
  `{*TABLES, "acs_table_shells", "dfa"}` (`source_manifest_coverage`). `build`: manifest, paths,
  `ensure_output_paths` (parts, metadata, wealth file), county and source digests, definitions,
  controls, tables, `reconcile`, `bounded_parts`, wealth; only then write; gzip as the household
  builder (`filename=""`, `mtime=0`, `compresslevel=9`). Metadata: `contract`
  `NationalHousingReference2024V1`, `issue` `PER-369`, `vintage`, `source_values_evidence_class`
  `Observed`, `parts` (path, sha256, bytes, decoded_bytes, rows, tables), `wealth_accounts` (path,
  sha256, quarter, unit, residuals), `source_manifest`, `sources`, `county_control`, `definitions`,
  `coverage`, `cross_table_checks`, `held_back`, `native_readers` [], `runtime_consumers` [],
  `semantics`, and `regeneration` (Step 7's build).
- [ ] **Step 4: Run Step 2's command.** Expected: 7 passed.
- [ ] **Step 5: Download into a new dated directory.** `cd
  /media/user/dev-ssd/worktrees/households-homes/babylon && df -h /media/user/data` (2 GB free at
  least); `D=/media/user/data/babylon-data/national_reference_2024/housing_$(date -u +%F) && mkdir
  "$D"`; for each of the 22 ids in `builder.TABLES`, lowercased (b25003, b25003a … b25003i, b25118,
  b25032, b25004, b25075, b25077, b25081, b25082, b25080, b25090, b25063, b25064, b25065),
  `curl -fsS --retry 3 -A 'reference-data-client/1.0' -o "$D/acsdt5y2024-$t.dat"
  "$BASE/acsdt5y2024-$t.dat"` with
  `BASE=https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData`,
  then `dfa.zip` from `https://www.federalreserve.gov/releases/z1/dataviz/download/zips/dfa.zip`
  alike. A 404 stops the task and goes to the lead. If the zip's sha is not `e7f35451…5919`, copy
  the 2026-11-20 capture `/home/user/.claude/jobs/11dcc24e/tmp/data/dfa/dfa.zip` (that sha, 895,897
  bytes) into `$D`, record both shas in `provenance.json` and report the revision to the lead (a
  revised Fed file moves design 7.15's figures); stop only if no copy with the pinned sha exists.
  Write `$D/provenance.json` with a one-off script kept outside `$D` and the repo, run as
  `python3 -I <script> "$D"`, shaped as `households_2026-10-02/provenance.json`
  (`captured_at_utc`; per table `id`, `url`, `path`, `bytes`, `sha256`, `domestic_county_rows`,
  `admitted_cell_statuses`, `columns`, `annotations`; for `dfa` `id`, `url`, `path`, `bytes`,
  `sha256`, `member`, `quarter`, `rows`) plus the Board's statement and URL. The sources file: 22
  table entries, `acs_table_shells` copied from the household sources file, and `dfa`, each path
  relative to the source root.
- [ ] **Step 6: Write the committed-file tests; they fail** on the missing metadata.
  `test_committed_parts_are_pinned_bounded_and_cover_every_county`: the metadata's
  `source_manifest.sha256` is the sources file's; each part's sha is `parts[part].sha256`, its size
  <= `MAX_PART_BYTES`, its header `part_columns(part)`, its ids 3,144, unique and sorted; the
  metadata is under 1,048,576 bytes. `test_committed_wayne_row_and_national_totals`: Wayne's
  `B25003_E001_value == "700591"` (the county reference's households), owners + renters == 700591,
  its `B25118_E002_value` and `B25032_E002_value` equal its `B25003_E002_value`;
  `coverage["B25003"]["total_estimate"] == 129227496` (B11001 summed over the 3,144 counties);
  B25064 and B25077 are `median` with no total; B25082 is `dollars`.
  `test_committed_wealth_table_is_the_quarter_as_published`: the file is the header and five rows
  above joined by `\n` with a final newline, its sha the metadata's. Parse the committed CSV; for a
  column, `top1` = TopPt1 + RemainingTop1 and `tenth` = `top1` + Next9; assert
  `top1 * 10_000 // tenth` is 6251 for `Unincorporated businesses` (design 7.15's 62.5% of the top
  tenth's businesses) and 5779 for `Corporate equities and mutual fund shares` (its 57.8%).
- [ ] **Step 7: Build, then see every test pass.**
  `cd /media/user/dev-ssd/worktrees/households-homes/babylon && mise exec -- uv run --frozen python
  tools/make_national_housing_reference.py --source-root /media/user/data/babylon-data`; Step 2's
  command (10 passed); `mise exec -- uv run --frozen ruff format`, then `ruff check` and
  `ruff format --check`, on the builder and the test; once, `mise exec -- uv run --frozen mypy
  tools/make_national_housing_reference.py`. Report each part's bytes, Wayne's B25003, B25081 and
  B25082 rows and `cross_table_checks` to the lead.
- [ ] **Step 8: Commit** the builder, the sources file, the six parts, the metadata, the Fed table
  and the test: `git add <those files>`, then `PYTHONPATH=src mise exec -- git commit -q -F <message
  file>` with subject `feat(reference): pin the 2024 housing tables and the Fed's wealth-group
  accounts`, a body ending `Part of PER-369` and the co-author trailer; check `git log --oneline -1`
  moved.

### Task 10: The second gate report

Design section 9, the gate's second bullet, working every placement of section 7.15 (steps 1 to 5,
"the rule of thirds with homes") on Wayne's real figures, and the company questions of sections
7.8 and 7.9 ("the property company belongs to a larger company", "the lender"). The report applies
nothing and changes no game byte. It is a checkpoint for the Director (C14).

**Files:**
- Create: `tools/household_units_gate_report.py` (reads committed files only; writes the report)
- Create: `tests/unit/tools/test_household_units_gate_report.py`
- Modify: `rust/crates/babylon-persistence/tests/national_household_units.rs` (Task 1's binary:
  add `company_questions`, one test and one ignored recorder)
- Create (recorded): `reports/household-units-2026-11-20/wayne-companies.json`,
  `reports/household-units-2026-11-20/gate-report-2.md`
- Modify: `reports/household-units-2026-11-20/README.md` (Task 1's: list the two files, digests)

**Interfaces:**
- Consumes (Rust, copied from HEAD):
  `CapturedEconomicCatalog::national_companies(&self) -> Option<&CompanyCapture>` and
  `national_company_finances(&self) -> Option<&CompanyFinances>` (`economic_catalog/capture.rs:340,
  348`), `opening(&self) -> &EconomicOpening`; `pub struct CompanyMember { pub site: SiteId, pub
  company: CompanyKey, pub county: CountyGeoid, pub employed: u64 }`, `CompanyKey::label(self) ->
  String`, `CompanyKey::id(self) -> CompanyId` (`national_economy/companies/model.rs`);
  `CompanyTreasury { company, total_weight, .. }` (`companies/treasury/model.rs`); `pub struct
  CompanyPayoutPolicy { pub company: CompanyId, pub earnings_bps: u16, pub claims: Vec<(AccountId,
  u128)> }` (`babylon-material-circuit/src/financial/model.rs:9`); `pub struct ServiceConnection {
  pub provider_site_id: SiteId, pub buyer: AccountId, pub good_id: GoodId, pub unit_id: UnitId }`;
  `pub fn commodity_good_id(key: &str) -> GoodId`; `pub const MAX_OWNERSHIP_CLAIMS: usize =
  131_072;`; `EconomicFunction::BusinessServices`, `EconomicFunction::source_key`.
- Consumes (committed files): Task 9's housing metadata
  `src/babylon/data/reference/economy/national_housing_reference_2024.metadata.json` (its parts,
  each with path and sha256; columns `<table>_E<line:03>_value|_raw|_status`, row `county_geoid`
  `26163`) and Task 9's Federal Reserve table
  `src/babylon/data/reference/national/federal_reserve_dfa_2026q2.csv` (`group,measure,
  value_millions`; groups `top_1, next_9, next_40, bottom_50`; measures `real_estate,
  home_mortgages, private_businesses, corporate_equities_and_mutual_fund_shares`); Task 4's
  `reports/household-units-2026-11-20/wayne-unit-accounts.json`, per household unit `label`, `bands`
  [`{band, households}`] and per period (period 0 = the opening) `households`, `cash_micros`,
  `net_assets_micros`, `needs` [`{key, required, cost_micros}`], money as decimal strings;
  `content/scenarios/national/defines.toml` (`period_days = 28`, `[commodity.housing]
  opening_price_micros = 1450000000`, `[financial] operating_income_tax_bps = 1500`).
- Produces (Rust, test binary only): `fn company_questions(catalog: &CapturedEconomicCatalog) ->
  serde_json::Value`; tests `company_questions_add_up` and `record_wayne_companies` (ignored).
- Produces (Python, money in integer micros, rates as `Fraction`, bands ordered top 1%, next 9%,
  next 40%, bottom 50%):

```python
class GateReportError(ValueError): ...
class ValueBracket(NamedTuple): count: int; lower: int; upper: int | None  # dollars; None = open top
class HouseholdUnitPeriod(NamedTuple): households: int; cash_micros: int; net_assets_micros: int; needs: tuple[Need, ...]
class HouseholdUnitAccounts(NamedTuple): label: str; bands: tuple[tuple[str, int], ...]; periods: tuple[HouseholdUnitPeriod, ...]
def largest_remainder(total: int, weights: Sequence[int]) -> tuple[int, ...]  # ties: lower index
def carry(census: Sequence[Fraction], census_bands: Sequence[int], game_bands: Sequence[int]) -> tuple[int, ...]
def owners_by_band(brackets: Sequence[tuple[int, int]], bands: Sequence[int]) -> tuple[Fraction, ...]
def owners_from_top(owners: int, bands: Sequence[int]) -> tuple[int, ...]
def home_values(brackets: Sequence[ValueBracket], aggregate: int, owners: Sequence[int]) -> tuple[Fraction, ...]
def rented_homes(by_size: Mapping[str, int], vacant_for_rent: int, single_house_part: Fraction) -> tuple[int, int]
def solve_top_shares(wealth: tuple[int, int, int, int]) -> tuple[int, int]
def could_buy(cash: int, tenants: int, price: int, non_housing_needs: int, tax: int) -> int
def homes_to_let(cash: int, needs: int, price: int, tax: int) -> int
def census_count(row: Mapping[str, str], table: str, line: int) -> int | None
def per_mille(part: int, whole: int) -> int   # half up
def read_household_unit_accounts(path: Path) -> tuple[HouseholdUnitAccounts, ...]
def build(root: Path = ROOT) -> str           # the Markdown; main() writes gate-report-2.md
```

**Decisions:**
- *Two halves.* Company membership, claim weights and service sellers are in no committed file, so
  one ignored Rust recorder writes them once; the Python tool reads only committed files. [Call]
- *Census to game.* Census bands are `largest_remainder(B25118_001, (7006, 63054, 280236,
  350295))`. Every placement is worked on census counts; `carry` takes each band's result to the
  game's band households (exact `x_b = census_b × H_b / C_b`, total `floor(Σ x_b)`, leftover by
  largest fractional part). No step rounds a census figure before `carry`. Inside a band,
  `largest_remainder` over the household units' households. [Call]
- *Step 1* brackets from the highest income down, owner line k (3..13) beside renter line k+12;
  `owners_by_band` walks the four census bands, so the top tenth's census owners are split exactly,
  in proportion to the census band sizes c1 : c9 (Fractions), and `carry` makes them whole on the
  game's bands. Other bound: `owners_from_top`.
- *Step 2.* Bottom-half owners all mortgaged; the rest of B25081_002 and all of B25081_009 shared
  over the top three bands in proportion to owners. Other bound: B25081_002 in proportion to owners
  in every band. Added refusal: bottom-half owners above B25081_002 ("the bottom half's owners
  exceed the mortgaged homes"), because the design's rule cannot hold then. [Call]
- *Step 3* middle values: `(lower + upper) / 2` with upper the next bracket's lower edge; "Less than
  $10,000" at 5,000; "$2,000,000 or more" at 2,000,000; scaled to B25082_001. Other bound: every
  home at `B25082_001 / B25075_001`.
- *Step 4* sizes: "1, detached" and "1, attached" single houses (65%, other reading 60%); "2" and
  "3 or 4" at 65%; "5 to 9" and "10 to 19" at 21%; "20 to 49" and "50 or more" at 6%; mobile homes,
  "Boat, RV, van, etc." and B25004_002 the company's; households' homes `floor(Σ exact parts)`.
  [Call] Between bands: households (Designed) beside the Fed's private-business division.
- *The value of a let home* is printed both ways: the county mean owner value and the bottom half's
  value from step 3. The management part: 10% beside 0%. Both are the Director's. [Director]
- *Year to period:* yearly tax × 28 / 365 exact (`period_days`). Tax rate = B25090_001 / B25082_001.
  A let home adds 0.9% a year. Mortgage payment: balance / 196 + balance × 5% × 28 / 365.
- *Could buy* = `min(tenants, max(0, (cash − 2 × non_housing_needs) // (price + 2 × tax)))`, with
  `non_housing_needs` the household unit's own cost of every need but housing for one period
  (Σ `cost_micros` over needs other than `housing`); the same whole-unit reserve as
  `homes_to_let = max(0, (cash − 2 × needs) // (price + 2 × tax))`. Cash under the reserve gives 0,
  printed as "under the reserve". Price twice: $500 (the second offer) and the band's home value.
  Tenants = households less step 1's owners.
- *The lender* is every Wayne `BusinessServices` site, by `opening_cash_micros`; every candidate
  tied at the most opening cash is printed and listed, never broken. Payout leaving Wayne is
  measured by claim weight, `total_weight − Wayne households' weight`, not by cash paid. [Call]
- *A withheld census cell* gives `None`; every step that needs it prints "not computable:
  withheld <table>_<line>", never a zero.

| Report section | Figures | Source | Formula |
|---|---|---|---|
| Sources | each file's sha256 | metadata, accounts, companies JSON | `hashlib.sha256` of the bytes; parts checked against metadata |
| The census on Wayne | tenure, by race (A to I), mortgage, aggregates | housing parts, row 26163 | B25003, B25003A..I, B25081, B25082, B25090; medians B25064, B25077 shown only |
| Rent check | census mean rent beside $1,450 | B25065_001, B25063_002, defines.toml | `B25065_001 / B25063_002 × 12 × 28 / 365` (B25065 is a monthly aggregate over renters paying cash rent, B25063_002) |
| Tables add up | each partition, each control | housing parts | B25003 1=2+3; B25118 1=2+14; B25081 1=2+9; B25032 1=2+13; B25003_002=B25118_002=B25081_001=B25075_001; B25003_003=B25118_014=B25032_013; Σ A..G = B25003 per line |
| Step 1 | owners and tenants by band and household unit | B25118, accounts `bands` | `owners_by_band`, `carry`, `largest_remainder`; other bound `owners_from_top` |
| Step 2 | mortgaged and free homes by band | B25081_002, B25081_009 | as Decisions; other bound in proportion |
| Step 3 | value per home by band | B25075, B25082_001 | `home_values`; other bound the county mean |
| Step 4 | households' and company's let homes, by band, each reading | B25032 14..23, B25004_002, Fed | `rented_homes`; split by households and by `private_businesses` top_1 : next_9 |
| What each band owes | debt per mortgaged home | Fed `home_mortgages / real_estate` | ratio × band's lived-in value; bottom 50% = whole value |
| Step 5 | added opening cash by band | steps 2 to 4, tax rate | 2 × (tax + mortgage payment) per owner; 2 × let-home tax; less 2 × housing `cost_micros` per owner |
| Management and let value | top 1% and next 9% rent and wealth | defines.toml `[commodity.housing]`, `[financial]`, step 4 | let homes × $1,450 × (1 − part) × (1 − `operating_income_tax_bps` / 10,000) per period |
| The thirds | wealth by band; V1, V9; division | accounts period 0, steps 1 to 5 | `net_assets` + homes − debt + step 5; `solve_top_shares`; division `V1/(V1+V9)` beside Fed 62.5% and 57.8% |
| Refusals | each pass or "would refuse" | all above | bottom share in [−1.8%, 3.7%]; V ≥ 0; debt ≤ value; debt needs a mortgaged home; free homes ≤ top-three owners; tables add up; each top band within 5 points of a third |
| Who could buy | per period and band | accounts periods 1 to 34 | `could_buy`, `homes_to_let` per household unit, summed by band (C1 division) |
| Companies | sellers, lender, companies, parts | wayne-companies.json | leaving share `per_mille(total − wayne, total)`; parts beside 131,072 |

If the solved division gives the top 1% half or less, the report says so in one sentence.

- [ ] **Step 1: Write the failing Python tests** in `test_household_units_gate_report.py` (import
  as `tests/unit/tools/test_national_age_reference.py` does):

```python
def test_owners_split_a_bracket_in_proportion():
    assert builder.owners_by_band([(18, 2), (20, 20), (10, 30)], (10, 40, 50)) == (9, 24, 15)
    assert builder.owners_by_band([(18, 2), (20, 20), (10, 30)], (5, 5, 40, 50))[:2] == (Fraction(9, 2), Fraction(9, 2))
    assert builder.largest_remainder(9, (1, 9)) == (1, 8)
    assert builder.largest_remainder(1, (1, 1)) == (1, 0)
    assert builder.owners_from_top(48, (10, 40, 50)) == (10, 38, 0)
def test_carry_shares_the_leftover_by_fraction():
    assert builder.carry((Fraction(1), Fraction(2)), (3, 3), (4, 4)) == (1, 3)
def test_values_walk_from_the_dearest():
    b = [ValueBracket(2, 0, 10_000), ValueBracket(2, 10_000, 20_000), ValueBracket(1, 20_000, None)]
    assert builder.home_values(b, 120_000, (1, 2, 2)) == (40_000, 30_000, 10_000)
def test_rented_homes_both_readings():
    sizes = {"1, detached": 80, "1, attached": 20, "2": 30, "3 or 4": 20, "5 to 9": 40,
             "10 to 19": 20, "20 to 49": 10, "50 or more": 10, "Mobile home": 5, "Boat, RV, van, etc.": 0}
    assert builder.rented_homes(sizes, 15, Fraction(65, 100)) == (111, 139)
    assert builder.rented_homes(sizes, 15, Fraction(60, 100)) == (106, 144)
def test_the_top_two_are_solved_together():
    assert builder.solve_top_shares((10, 50, 300, 40)) == (290, 250)
    with pytest.raises(builder.GateReportError, match="solved_below_zero: next 9%"):
        builder.solve_top_shares((10, 400, 300, 40))
def test_who_could_buy():
    assert builder.could_buy(4_500, 6, 500, 2_000, 50) == 0   # under the reserve
    assert builder.could_buy(6_400, 6, 500, 2_000, 50) == 4
    assert builder.could_buy(10_000, 6, 500, 2_000, 50) == 6
    assert (builder.homes_to_let(10_000, 3_000, 500, 50), builder.homes_to_let(5_000, 3_000, 500, 50)) == (6, 0)
def test_per_mille_rounds_half_up():
    assert builder.per_mille(1, 2000) == 1
def test_a_withheld_cell_is_not_zero():
    row = {"B25118_E003_value": "", "B25118_E003_status": "insufficient_sample_cases"}
    assert builder.census_count(row, "B25118", 3) is None
def test_a_withheld_step_says_so(tmp_path):
    # copy every input of build() into tmp_path, blank B25081_E002_value in row 26163 (status
    # "insufficient_sample_cases"), rewrite that part's sha256 in the copied metadata
    assert "not computable: withheld B25081_002" in builder.build(tmp_path)
def test_unit_accounts_without_need_costs_are_refused(tmp_path):
    path = tmp_path / "accounts.json"  # one household unit, one period, needs without cost_micros
    path.write_text(json.dumps([{"label": "u", "bands": [{"band": "bottom_50", "households": 1}],
        "periods": [{"households": 1, "cash_micros": "0", "net_assets_micros": "0",
                     "needs": [{"key": "food", "required": "1"}]}]}]))
    with pytest.raises(builder.GateReportError, match="accounts_key: cost_micros"):
        builder.read_household_unit_accounts(path)
def test_federal_reserve_ratios_match_the_design():
    m, r, p, e = (builder.fed_measure(ROOT, k) for k in ("home_mortgages", "real_estate",
                  "private_businesses", "corporate_equities_and_mutual_fund_shares"))
    assert [builder.per_mille(m[g], r[g]) for g in ("top_1", "next_9", "next_40")] == [84, 227, 295]
    assert builder.per_mille(p["top_1"], p["top_1"] + p["next_9"]) == 625
    assert builder.per_mille(e["top_1"], e["top_1"] + e["next_9"]) == 578
def test_committed_report_is_current():
    assert builder.build() == (ROOT / "reports/household-units-2026-11-20/gate-report-2.md").read_text()
```

  (`fed_measure(root, measure) -> dict[str, int]` reads the committed Fed CSV, millions by group.)
- [ ] **Step 2: Run** `mise run test:q -- tests/unit/tools/test_household_units_gate_report.py`.
  Expected: collection error, no module `household_units_gate_report`.
- [ ] **Step 3: Write the failing Rust test** in `national_household_units.rs`, on the shipped
  policy's opening as the binary captures it: `company_questions_add_up` asserts, for every
  company in the value, `wayne_household_weight + other_weight == total_weight` and `total_weight ==`
  the `CompanyTreasury.total_weight` of that company; `Σ members_by_state[].sites ==` its members in
  `national_companies()`; the sellers' `wayne_buyers` plus `wayne_buyers_without_a_seller` equal
  `wayne_buyers`; `company_parts == Σ claims.len()` over `opening().policies.company_payouts` and
  `<= MAX_OWNERSHIP_CLAIMS`, and `ownership_rows == opening().institutions.ownership.len()`. Run
  `mise run rust:test:q -- -p babylon-persistence -E 'binary(national_household_units) &
  test(company_questions)'`. Expected: compile failure, no `company_questions`.
- [ ] **Step 4: Implement `company_questions`.** Keys, ids as lowercase hex, weights as decimal
  strings: `version: 1`; `housing {wayne_buyers, wayne_households, wayne_buyers_without_a_seller,
  site_buyers, sellers: [{site, label, county, function, company, wayne_buyers, wayne_households,
  other_buyers, other_households, site_buyers}], one_business_in_wayne}` from `service_connections`
  with `good_id == commodity_good_id("housing")`. Buyer counts are buyer accounts
  (`AccountId::Household`), their households summed beside them; a Wayne buyer is a household
  seed located in `26163`; site buyers are counted apart as `site_buyers` and do not decide
  `one_business_in_wayne` (one seller, in Wayne, no other household buyers). `lender {candidates:
  [{site, label, opening_cash_micros, original_cash_micros, company}], tie}`:
  `opening_cash_micros` is `EconomicSiteSeed.opening_cash` as captured, after the company sweep;
  `original_cash_micros` from `CompanyFinances.members` beside it; `company` is null for a site
  in no company. `companies: [{company, label, wayne_sites, members_by_state: [{state, sites,
  employed}], total_weight, wayne_household_weight, other_weight, claims}]` for the companies of
  the housing sellers and of every candidate tied at the most opening cash; `limits
  {company_parts, ownership_rows, max_ownership_claims}`. Add `record_wayne_companies`
  (`#[ignore = "writes reports/household-units-2026-11-20/wayne-companies.json"]`), writing as
  Task 1's recorder writes. Run step 3's command (expected: PASS), then `mise run rust:test:q --
  -p babylon-persistence -E 'binary(national_household_units) & test(record_wayne_companies)'
  --run-ignored ignored-only`. Expected: PASS; `reports/household-units-2026-11-20/
  wayne-companies.json` exists and is under 1 MiB.
- [ ] **Step 5: Implement the tool** with the signatures, the table and the Decisions above, then
  run `mise exec -- uv run --frozen python tools/household_units_gate_report.py`, which writes
  `gate-report-2.md`. `build()` writes Markdown that markdownlint accepts: prose wrapped at 100
  columns, headings under 80, every figure in a table. Run `mise exec -- npx markdownlint --config
  .markdownlint.yaml reports/household-units-2026-11-20/gate-report-2.md`. Expected: no output.
  Run step 2's command. Expected: every test PASSES. Run `mise exec -- uv run --frozen ruff check
  tools/household_units_gate_report.py tests/unit/tools/test_household_units_gate_report.py` and
  `ruff format --check` on the same two files. Read the report whole: every figure has its source
  and formula, every refusal a pass or a named "would refuse". Add both files and their sha256 to
  the README.
- [ ] **Step 6: Scoped gate** (fmt, clippy, `binary(national_household_units)`, then `mise run
  rust:test:q -- -p babylon-persistence`). Expected: PASS, no existing test changed.
- [ ] **Step 7: Commit** the tool, its test, `national_household_units.rs`, `wayne-companies.json`,
  `gate-report-2.md` and the README as `docs(reports): the second gate report on Wayne's figures`.
  The lead sends the report to the Director (C14).
