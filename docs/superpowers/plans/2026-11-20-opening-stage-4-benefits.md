# The Opening, Stage 4: Benefits and the Public Budget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** A public account can hold named programs beside its standing rows: a benefit for each
person of a household with no earner, and half pay for 26 weeks for a worker laid off in play. A
body that asks for it pays in full while it has the cash and cuts each rank in proportion when it
has not.

**Architecture:** Programs, the budget's rule and the record of layoffs are state in
`FinancialInstitutions`, so a later typed command can change a rate as the County Review changes
its rows. They are paid in today's pass, `FinancialClose::opening`, before wages. The record is kept
per staffing member (one household's part of one pool) and advanced by a new finish,
`finish_with_staffing`, from the member receipts the caller has. A state without any of this writes
today's bytes; with it, version 25 (26 with a lifecycle book) and one tail after the financial rows.
One tax basis of one payer may be split between two public accounts.

**Tech Stack:** Rust (`babylon-material-circuit`; in `babylon-tick` the gate and one change to the
County Review's facts, Task 2, the only change of behavior outside the engine; one literal in
`babylon-persistence`), `contracts/material_circuit_v4.yaml`, the small world's test binary
`rust/crates/babylon-material-circuit/tests/small_world.rs`.

**Spec:** `docs/superpowers/specs/2026-11-20-the-opening-of-the-national-economy-design.md`, rules
O12 and O13, section 2 ("A layoff has two steps", "Public money that is spent") and build stage 4;
`ai/decisions/ADR313_the_national_economy_opens_in_balance.yaml`;
`reports/economy-repair-2026-11-20/small-world.md`. The Director: "public benefits, cut when
taxes fall, the benefits and state services and disability pension etc can become a site of
struggle eventually and be modified, tweaked, increased, etc thru the political/electoral system".

**Prerequisites:** the price rule's Tasks 1 to 7 and the tiers plan (stage 3) are built.
**Build order:** Tasks 1 to 5 in order. Each leaves every earlier byte unchanged. No shipped world
holds a program before later plan B, so the tick's gates (Tasks 1 and 3) are never met in play.
Lines were read on 20 November while the price rule's Task 5 was uncommitted: find each by its text.

Checked once against the code by a second reader on 20 November 2026; its findings are in the tasks.

**Lead's rulings (20 November):** the two benefits share one rank at the opening, cut together; a
rank stays a figure that can change. Across a pool's households people go back in proportion to
each one's people looking for work; "last laid off, first back" holds inside one household's share.
A benefit is not taxed. The County Review counts only its own account's money (its wage tax
collected, its support paid).

## Global Constraints

- Work only in `/media/user/dev-ssd/worktrees/households-homes/babylon`, branch
  `codex/households-and-homes`. Start every shell command with `cd` to it (or to its `rust/`
  directory). Never push. No secrets, no `.env`, no `babylon-data` on this disk.
- One cargo or pytest process at a time, on the whole machine. Never pass `-j` or `--jobs`.
- A run that outlasts one command goes to the background with a log, ends with its own marker
  (`...; echo "exit=$?" >> <log>`), and is waited for on that marker. Never wait on the word `real`:
  this shell is zsh, whose `time` prints `total`. Leave no shell running when you report.
- **Scoped gate, run by every task before its last commit,** one leg at a time: from `rust/`,
  `mise exec -- cargo fmt --all -- --check`; `mise exec -- cargo clippy --workspace --all-targets
  --locked -- -D warnings -D clippy::cognitive_complexity`; the test binaries the task names with
  `mise run rust:test:q -- -p <crate> -E 'binary(<name>)'`; `mise run rust:test:q -- -p <crate>`
  once for each crate the task changed; `mise run check:bsl-sentinels`. The lead alone runs `mise
  run rust:check-no-docs`, after Task 3 and after Task 5.
- Commit one unit of work at a time: `git add <files>` then `PYTHONPATH=src mise exec -- git commit
  -q -F <message file>`; check that `git log --oneline -1` moved. The body ends with `Part of
  PER-371` and a `Co-Authored-By` line naming the model that wrote the commit. Never commit
  `uv.lock`.
- **Bytes.** A state with no program, no layoff record, no budget that asks for the cut and no
  payer with two tax rows gives every byte it gives today: state, receipts, register. No pinned
  value of an existing test changes; in particular every run of `tests/small_world/quiet.rs`,
  `pushed.rs` and `tiers.rs` (stage 3) keeps its figures. If one must change, stop and tell the lead.
- No floating point. Money is `i128` millionths of a dollar (`Currency`). Persons and hours are
  `u64`. Products are taken in `i128` with checked arithmetic.
- Every refusal is a typed error. No panic, no `unwrap` outside tests, no silent clamp. A field
  that a rule does not read is refused when it is not zero, never ignored.
- Money is conserved: `payments::conserved` holds at every close; each test that moves public
  money asserts the total of the book before and after.
- Functions stay under 100 lines and under a cognitive complexity of 25.
- A change to `contracts/material_circuit_v4.yaml` updates `MATERIAL_CIRCUIT_SOURCE_SHA256` in
  `rust/crates/babylon-material-circuit/src/wire/state.rs` in the same commit. A contract line
  that a task makes false is rewritten by that task, in the form "without ...; with ...".
- Markdown is wrapped at 120 columns, headings at 80. Refer to the player as "they".

## Review Focus

1. **A County Review account beside a fund.** Expected: its payments, receipts and the review's
   figures are today's, whatever the fund collects or pays. Tasks 1, 2 and 3.
2. **Nobody to pay for** (0 persons; nobody laid off). Expected: a receipt with due and paid 0, no
   transfer, no division by zero; a zero claim in a short rank gets nothing. Tasks 1, 3 and 4.
3. **People who leave the reserve unhired** (deaths). Expected: they leave from the oldest end, the
   uncovered first; covered cohorts are trimmed only when the record would exceed the reserve, so
   the record never pays more persons than are looking. Task 4.
4. **A finish that forgets the record.** Expected: `finish_with_workforce`, `finish_with_labor` and
   `advance_material_circuit` refuse a state with an after-layoff program. Task 4.
5. **A payer short of cash with two tax rows.** Expected: rows collect in key order from one running
   balance; the second is short; nothing is overdrawn. Task 2.

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `rust/crates/babylon-material-circuit/src/financial/model.rs` | `PublicSpendingRule`, the program types, `LayoffRecord`, `PublicProgramReceipt`; new fields of `PublicBudget` and `FinancialInstitutions` | 1, 3, 4 |
| `rust/crates/babylon-material-circuit/src/financial/cut.rs` | `cut_in_proportion`, the cut of one budget | 1 |
| `rust/crates/babylon-material-circuit/src/financial/programs.rs` | What each program owes each recipient this period | 3, 4 |
| `rust/crates/babylon-material-circuit/src/financial/layoffs.rs` | The record of layoffs: advancing it, and what it is owed | 4 |
| `rust/crates/babylon-material-circuit/src/financial/close.rs` | `public_funding` by rule, with programs; `collect_taxes` from one balance per payer | 1, 2, 3 |
| `rust/crates/babylon-material-circuit/src/financial/validation.rs` | Keys, rules, programs and records | 1, 2, 3, 4 |
| `rust/crates/babylon-material-circuit/src/wire/{financial.rs, accounting.rs, state.rs}` | The tail and the state versions | 1, 2, 3, 4 |
| `rust/crates/babylon-material-circuit/src/transition/state.rs` | `finish_with_staffing`; the program receipts in the transition | 3, 4 |
| `rust/crates/babylon-material-circuit/tests/small_world/{support.rs, benefits.rs, dump.rs}` | The fund variant, its runs and its pins | 2, 3, 4, 5 |
| `rust/crates/babylon-tick/src/material_world/register.rs` | The gate until the later plan carries the new records | 1, 3 |
| `rust/crates/babylon-tick/src/material_world/county_review.rs` | The review counts only its own account's taxes and support | 2 |
| `reports/economy-repair-2026-11-20/small-world.md` | What the fund does to the small world | 5 |

### Task 1: A budget that is cut in proportion

**Files:**
- Create: `src/financial/cut.rs` (with its `#[cfg(test)] mod tests`)
- Modify: `src/financial/model.rs` (`PublicSpendingRule`; `PublicBudget.rule`);
  `src/financial/close.rs` (`public_funding`, about 92 to 134); `src/financial/validation.rs`
  (`validate_public`); `src/model.rs` (`PublicProgramInvariant = 39` and its arm in `TryFrom<u16>`;
  `MaterialCircuitState::has_public_program_extension`); `src/wire/state.rs` (`state_version`,
  the two new versions, the decoder's accepted versions at 625 to 631, the digest);
  `src/wire/accounting.rs` and `src/wire/financial.rs` (the tail, read only under versions 25 and
  26); `tests/weighted_freight.rs` (the registry: 39 is `Ok`, 40 is refused);
  `contracts/material_circuit_v4.yaml` (meta lines 3 and 4 gain the two versions;
  `period_close` line 390; `financial_institutions` field order, rows, widths and the invariant at
  860; refusal `public_program_invariant: 39` after line 598)
- Modify: the 14 `PublicBudget {` literals in three crates (`rg -n 'PublicBudget \{' rust/crates`
  finds them and the struct; one is `babylon-persistence/src/national_economy/opening/financial.rs`)
  get `rule: CappedInOrder`
- Modify: `rust/crates/babylon-tick/src/material_world/register.rs` (in `company_receipt_format`,
  before the format is chosen, refuse `transition.state` when `has_public_program_extension()`,
  with `MaterialWorldError::Wire`; the price rule's Task 7 removes the market refusal there)
- Test: `src/financial/cut.rs`; `tests/financial_circuit.rs`

**Interfaces:**
- Produces:

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum PublicSpendingRule {
    /// Today: min(period_cap, cash less floor); in a rank, the first by identifier first.
    CappedInOrder = 1,
    /// Cash less floor, no cap; ranks lowest first; the first rank not covered is cut in proportion.
    CashInProportion = 2,
}
// PublicBudget gains
pub rule: PublicSpendingRule,
/// The shares of `budget` over claims sorted by rank, one result per claim, in the claims' order.
/// # Errors
/// `FinancialInvariant` for a negative budget or claim, or ranks out of order; `Arithmetic` on overflow.
pub(crate) fn cut_in_proportion(budget: Currency, claims: &[(u32, Currency)])
    -> Result<Vec<Currency>, MaterialCircuitError>;
impl MaterialCircuitState { // version 25 or 26: a budget in proportion, a program or a layoff record
    #[must_use] pub fn has_public_program_extension(&self) -> bool; } // (Task 2: or a split tax)
pub const MATERIAL_CIRCUIT_PUBLIC_PROGRAMS_STATE_SCHEMA_VERSION: u16 = 25;
pub const MATERIAL_CIRCUIT_LIFECYCLE_PUBLIC_PROGRAMS_STATE_SCHEMA_VERSION: u16 = 26;
```

**Decisions (the plan's calls):**
1. The rule is a field of the budget row, `CappedInOrder` for every row written today. Under
   `CashInProportion` the row's `period_cap` must be 0 (refused otherwise, `FinancialInvariant`):
   the rule does not read it.
2. The cut: ranks in ascending order; a rank whose total is at most what is left is paid in full;
   the first rank that is not gets, for each claim, `floor(amount x left / rank total)`; the
   micro-units still left go one each to the claims of that rank in their order, skipping a claim
   already at its amount; later ranks get 0. The products are `i128` checked.
3. `public_funding` takes the budgets in account order. A capped account runs today's loop over its
   rows, unchanged. An account in proportion builds its claims, sorted by `(rank, recipient,
   source)` where `source` is the standing row's treatment, ahead of any program (Task 3), cuts,
   then makes its transfers and receipts in that order. Each standing row's `PublicBudgetReceipt`
   keeps today's fields.
4. The tail of the financial rows, written only when `has_public_program_extension()`: a `u32`
   count equal to the budgets' count and one `u8` rule for each budget in its order; then the
   programs (Task 3) and the records (Task 4) as `u32` counts, 0 in this task. The decoder reads it
   only under 25 and 26, and the frame's version must then equal `state_version(state)`, as today.
5. `state_version`: 22 plain, 24 with a lifecycle book, 25 with the extension, 26 with both (check
   with `rg -n 'schema_version' contracts/` that this frame has used neither). 6. The tick refuses
   the extension until later plan A teaches its register, stored records and projections.

- [ ] **Step 1: Write the failing tests.** In `cut.rs`, money in micro-units, a claim `(rank,
  amount)`:

| Test | budget | claims | result |
|---|---|---|---|
| `enough_pays_everyone_in_full` | 1_000 | (0,30), (1,60), (1,40), (1,20), (2,5) | 30, 60, 40, 20, 5 |
| `a_short_rank_is_cut_in_proportion` | 100 | the same | 30, 36, 23, 11, 0 |
| `a_rank_exactly_covered_leaves_nothing_after` | 150 | the same | 30, 60, 40, 20, 0 |
| `nothing_in_the_budget_pays_nothing` | 0 | the same | 0, 0, 0, 0, 0 |
| `a_zero_claim_gets_no_remainder` | 5 | (0,0), (0,10), (0,10) | 0, 3, 2 |

  Add `the_laws_hold_for_every_budget`: for the claims above and every budget from 0 to 160, the
  results add to `min(budget, total)`, each is at most its claim, and inside the cut rank each is at
  least `floor(amount x left / rank total)`. Add `bad_input_is_refused`: a budget of -1, a claim of
  -1, and ranks (1, 0) each give `Err(FinancialInvariant)`; two claims of `i128::MAX / 2` and a
  budget of 10 give `Err(Arithmetic)`.

  In `tests/financial_circuit.rs`, on `appropriation_state` (about 370):
  `standing_rows_of_one_rank_are_cut_in_proportion` (cash 30, rule `CashInProportion`, cap 0,
  both rows at priority 0: paid 15 and 15, unfunded 5 and 5, the treasury ends at 0, total money
  30, and the state round-trips through encode and decode with version byte 25);
  `a_budget_in_proportion_keeps_its_floor` (cash 100, floor 70: paid 15 and 15);
  `a_budget_in_proportion_with_a_cap_is_refused` (cap 40: `FinancialInvariant`);
  `a_state_without_the_extension_keeps_its_bytes` (the digest of `appropriation_state(30, 0, 40,
  0)` from `material_circuit_state_digest` equals the value printed at this task's base commit,
  pinned as a literal, and its version byte is 22). Every existing test of the file passes
  unchanged. In `babylon-tick`, beside the register's tests:
  `the_register_refuses_a_state_with_the_extension` (a fixture's budget set to `CashInProportion`,
  cap 0: preparing the transition gives `MaterialWorldError::Wire`).
- [ ] **Step 2: Run them and see them fail:** `mise run rust:test:q -- -p babylon-material-circuit -E
  'test(cut::tests) | binary(financial_circuit)'`; it does not compile. Step 3: **Implement** the
  rule, the cut, the funding by rule, the tail, the versions, code 39 and the gate; fill every literal.
- [ ] **Step 4: Run** the binaries, then `-p babylon-material-circuit`, `-p babylon-tick`,
  `-p babylon-persistence`. Expected: all pass, no pinned value changed.
- [ ] **Step 5: Commit** `feat(material-circuit): cut a public budget in proportion when asked`.

### Task 2: One tax, two public accounts

**Files:**
- Modify: `src/financial/validation.rs` (`canonicalize` at 16 and `structure` at 41: the key
  `(payer, basis, public_recipient)`, bounded by `MAX_TAX_POLICIES`); `src/financial/close.rs`
  (`collect_taxes`, about 136 to 180); `src/wire/financial.rs` (`append_taxes` and `decode_taxes`
  at 89 to 114: the bound and the order); `src/model.rs` (`MAX_TAX_POLICIES`);
  `src/model.rs` or `src/financial/model.rs` (`has_public_program_extension` counts a payer with
  two rows); `contracts/material_circuit_v4.yaml` (`tax_policies` at 514 with its comment,
  `tax_receipts_per_period` at 555, the canonical key at 846, the invariant "One tax policy per
  eligible payer" at 862) and the digest
- Modify: `tests/small_world/support.rs` (the fund account; the name `"fund"`). Create:
  `tests/small_world/benefits.rs` (a module of `tests/small_world.rs`)
- Modify: `rust/crates/babylon-tick/src/material_world/county_review.rs` (`group_facts`, 495 to
  541: the tax filter at 507 to 509 also requires `tax.public_recipient` to be the review's
  account; `support_income_micros` at 536 becomes the sum of `paid` over `transition.public_budgets`
  rows whose `public_account` is the review's and whose recipient is the group's household, in
  place of the income statement's `public_transfer_income`). Test:
  `rust/crates/babylon-tick/tests/` beside the county review tests, on
  `tests/support/county_review_fixture.rs`

**Interfaces:**
- Produces:

```rust
/// Two bases and two recipients for each captured account.
pub const MAX_TAX_POLICIES: usize = 262_144;
// tests/small_world/support.rs
pub(crate) struct Fund {
    pub wage_bps: u16,
    pub operating_bps: u16,
    pub opening_cash: Currency,
    /// The benefit for each person of the account that does not work (Task 3).
    pub per_person: Option<Currency>,
    /// The share of a laid-off worker's pay and its length in half periods (Task 4).
    pub after_layoff: Option<(u16, u16)>,
}
impl World { pub(crate) fn with_fund(self, fund: Fund) -> Self; }
```

**Decisions (the plan's calls):**
1. The smallest change: a payer may hold one row for each `(basis, public_recipient)`. The row's
   bytes do not change; only the key and the bound do. With one row per payer the order is today's.
2. `collect_taxes` assesses every row before any credit, as today, but reads the payer's cash once
   and takes each row's collection from that running balance, in key order: `collected =
   min(assessed, available(balance, row floor))`. With one row per payer this is today's figure.
3. `MAX_TAX_POLICIES = 262_144`: the national opening measured 76,327 tax rows (contract 526);
   splitting each between a place and the fund gives about 152,654, above today's 131,072.
   `has_public_program_extension` gains its last clause here: a payer with more than one tax row.
5. **The County Review counts only its own account** (lead's ruling). Today `group_facts` adds every
   `WageIncome` receipt of the payer, whatever its recipient, so a split counts taxed wages twice
   and moves the review's ranks (`babylon-practice-contract/src/county_review/place.rs:100-140`,
   `session.rs:337-342`); and support income is the whole statement's public transfers, so the
   fund's benefits would count. With one public account the new figures equal today's: every tax
   row goes to it and every public transfer comes from it (the county account holds no program).
4. The fund: id `[31; 32]` (after the treasury's `[30; 32]`), its cash, its location (the one
   place), a budget `CashInProportion`, cap 0, floor 0; `account_name` maps it to `"fund"`.

- [ ] **Step 1: Write the failing tests** in `tests/small_world/benefits.rs`, each closing period 1 of
  `World::taxed()` with the treasury's rates replaced as named and a fund paying nothing:
  - `one_wage_tax_is_paid_to_two_public_accounts`: the treasury's rates 500 and 500, the fund's
    1500 and 1500. Assert, for payer `w_utility`, two tax rows in the order treasury then fund,
    collected 60 and 180; for site `utility`, 12 and 36; the collected total 640, as in the taxed
    run; money conserved.
  - `a_payer_short_of_cash_pays_its_rows_in_order`: `w_utility`'s rows at 1000 (treasury) and 1500
    (fund). Assert assessed 120 and 180, collected 120 and 120, uncollected 0 and 60; the account
    ends at 0; money conserved.
  - `a_split_tax_writes_the_extended_state`: with the fund's budget `CappedInOrder` (cap 0), the
    split alone gives version byte 25, and the state round-trips.
  - `a_tax_row_repeated_for_one_recipient_is_refused`: two wage rows of one payer to the treasury
    give `DuplicateRow`.

  In `babylon-tick`: `the_county_review_counts_only_its_own_account`: the county review fixture
  plus a fund (cash, location, budget `CappedInOrder` with a standing support row of $50 to one
  group's household), and a second `WageIncome` row at 500 points from one group's payer to the
  fund. Assert the review's period facts (`labor_facts`, `period_facts`), its session's payments
  and the county account's receipts equal those of the same run without the fund.
- [ ] **Step 2: Run them and see them fail** (`binary(small_world)`, the tick test). Step 3:
  **Implement** the key, the bound, the running balance, the review's filter and the fund.
- [ ] **Step 4: Run** the binary (every existing small-world test passes with its figures), then
  `binary(financial_circuit)`, `binary(collection_receipts)`, the crate, and `-p babylon-tick`
  (its county review tests unchanged).
- [ ] **Step 5: Commit** `feat(material-circuit): let one tax be paid to two public accounts`.

### Task 3: Programs, and the benefit for each person

**Files:**
- Create: `src/financial/programs.rs`
- Modify: `src/financial/model.rs` (the program types, `PublicProgramReceipt`,
  `FinancialInstitutions.programs`, `empty()`); `src/financial/close.rs` (`public_funding` gathers
  the programs' claims into its account's cut; `FinancialClose.programs`);
  `src/financial/validation.rs`; `src/wire/financial.rs` (the programs in the tail);
  `src/model.rs` (`MaterialCircuitTransition.public_programs`, `MAX_PUBLIC_PROGRAMS`);
  `src/transition/state.rs` (the one construction of the transition at 1620);
  `src/lib.rs` (re-exports); the 4 `FinancialInstitutions {` literals (`wire/financial.rs:24`,
  `tests/financial_circuit.rs:50`, `tests/support/organizer_funding_control.rs:409`, the tick's
  `tests/staffed_material_replay/financial.rs:54`) and `empty()` get `programs: vec![]`;
  `rust/crates/babylon-tick/src/material_world/register.rs` (refuse a non-empty
  `public_programs` beside the gate of Task 1); `contracts/material_circuit_v4.yaml` (a
  `public_programs` section: the rows, the bytes, the rules of this task) and the digest
- Modify, tests: `tests/small_world/support.rs` (the fund's per-person program; the snapshot's
  program figures; `World::benefits`), `tests/small_world/benefits.rs`,
  `tests/support/household_time_cases.rs` (one lifecycle test)

**Interfaces:**
- Consumes: `cut_in_proportion`, `PublicSpendingRule`, `Fund`, `with_fund`.
- Produces:

```rust
/// A short name that politics refers to: 1 to 32 bytes of `a-z`, `0-9` and `_`, a letter first.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct PublicProgramKey(String);
impl PublicProgramKey { // new: Err(PublicProgramInvariant) for an empty, long or ill-formed key
    pub fn new(text: &str) -> Result<Self, MaterialCircuitError>; pub fn as_str(&self) -> &str; }
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PublicProgramTerms {
    PerPerson { amount_per_person: Currency },                // tag 1
    AfterLayoff { wage_share_bps: u16, half_periods: u16 },   // tag 2 (Task 4)
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PublicProgram {
    pub key: PublicProgramKey,                  // fixed
    pub payer: PublicAccountId,                 // fixed
    pub rank: u32,                              // may change
    pub terms: PublicProgramTerms,              // its kind is fixed; its figures may change
    pub recipients: Vec<FinalDemandPrincipalId>, // may change
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PublicProgramReceipt {
    pub period: u64,
    pub public_account: PublicAccountId,
    pub program: PublicProgramKey,
    pub recipient: FinalDemandPrincipalId,
    pub rank: u32,
    /// Per person: the account's persons. After a layoff: the persons covered this period.
    pub covered_persons: u64,
    pub due: Currency,
    pub paid: Currency,
    pub unfunded: Currency,
}
impl PublicProgramReceipt { // Err(PublicProgramInvariant) unless period > 0, 0 <= paid <= due = paid + unfunded
    pub fn validate(&self) -> Result<(), MaterialCircuitError>; }
// FinancialInstitutions gains
pub programs: Vec<PublicProgram>,
// MaterialCircuitTransition gains
pub public_programs: Vec<PublicProgramReceipt>,
pub const MAX_PUBLIC_PROGRAMS: usize = 256;
/// One claim for each program and recipient, in (program key, recipient) order.
pub(crate) fn program_dues(state: &MaterialCircuitState, programs: &[PublicProgram])
    -> Result<Vec<(PublicProgramReceipt, Currency)>, MaterialCircuitError>;
```

**Decisions (the plan's calls):**
1. Programs are state, in `FinancialInstitutions`, because a rate that politics changes is state:
   a later typed command may change `rank`, the figures inside `terms` and `recipients`; `key`,
   `payer` and the kind are fixed. Every close re-validates them, as it does the County Review's
   rows, so the later command needs no check of its own.
2. Validation (`PublicProgramInvariant`): keys unique in the state; at most `MAX_PUBLIC_PROGRAMS`;
   the payer holds a budget `CashInProportion` (a capped account holds no program, so the County
   Review's account cannot); recipients not empty, unique, each a household account in the
   book; the recipients of all programs together at most `MAX_MATERIAL_CIRCUIT_ROWS`; per person:
   amount > 0, and each recipient has a `HouseholdCohort` row (so the state is recurring).
   `canonicalize` sorts programs by key and each recipient list.
3. **Persons are read from the cohort.** A per-person program owes `amount_per_person x
   cohort.persons`, read from `recurring.households` at the opening of the period. With a lifecycle
   book that row is kept equal to the book's persons at each close
   (`household_lifecycle/close.rs:41-45`), so births and deaths of the last close are counted;
   without one it is the opening's figure. A cohort of 0 persons owes 0.
4. Programs and standing rows of one rank are cut together (Task 1's claims; a program's `source`
   sorts after every standing treatment, then by key). Every program and recipient gives one
   receipt each period, also when it owes 0, so a state with a program always has receipts. The
   receipts are sorted by `(program key, recipient)`. A paid amount moves as today's
   `CashTransferPurpose::PublicTransfer` and `costs.public_transfer`; a benefit is not wage income,
   so the wage tax does not reach it.
5. Bytes of a program: key length `u8` and its bytes; payer 32; rank `u32`; tag `u8`; per person
   the amount `i128`, after a layoff `u16` share and `u16` half periods; a `u32` count of
   recipients and 32 bytes each. Programs in key order.
6. `World::benefits()`: `World::taxed()` with the treasury at 500 and 500 points and a fund at 1500
   and 1500, opening with $960 (two periods of payments, O13), paying `no_earner`, $60 a person,
   rank 0, to the account that does not work. The treasury's support row, cap and cash become $160
   (`support_payment` less the fund's rate times the supported persons). Taxes: wages 2,400 give 120
   and 360, operating income 800 gives 40 and 120; treasury 160 in and out, fund 480 in and out;
   the supported account receives 160 + 480 = 640, its need.
7. The snapshot gains `program_due` and `program_paid`, maps from `(program key, account name)` to
   micro-units, and `covered`, a map from account name to persons covered; `public_payments` adds
   the programs' paid amounts (no earlier run has any).

- [ ] **Step 1: Write the failing tests.** In `tests/small_world/benefits.rs`:
  - `the_fund_pays_each_person_and_the_world_is_still`: 34 periods of `World::benefits()` (with
    `after_layoff: None`). Assert every period equals the first, the first's cash is the opening's,
    `employed` is `[12, 4, 4, 4]`, `public_receipts` and `public_payments` are 640 and 640, cash
    `fund` 960 and `public` 160, `program_due` and `program_paid` of `("no_earner", "supported")`
    480_000_000 each, and `covered["supported"]` 8.
  - `per_person_reads_the_persons_of_the_cohort`: build the opening, set the supported cohort's
    persons to 6, close one period: due and paid 360_000_000, `covered_persons` 6. At 0 persons: due
    and paid 0 and no transfer to the account.
  - `the_place_pays_as_today_beside_the_funds_program`: the opening with the fund's cash at 0.
    Assert the program's receipt has due 480_000_000, paid 0, unfunded 480_000_000; the treasury's
    `PublicBudgetReceipt` is requested, paid, unfunded 160, 160, 0, and equals the treasury's
    receipt from the same world without the program and the fund's budget.
  - `a_program_and_a_standing_row_of_one_rank_are_cut_together`: the fund also holds a standing
    support row of $480 to `supported` at priority 0 and opens with $480. Assert the row and the
    program are each paid 240_000_000.
  - `bad_programs_are_refused`: each gives `PublicProgramInvariant`: the key `"No-earner"`; a key
    used twice; the payer the treasury (capped); a recipient with no cohort; an amount of 0; a
    recipient listed twice. (An unsorted list is sorted by `canonical_state` before it is checked;
    in bytes, decode refuses it with `WireNoncanonical`: add that case to the round-trip test.)
  - `a_program_writes_the_extended_state_and_round_trips`: version byte 25; the decoded state equals
    the encoded one.

  In `tests/support/household_time_cases.rs`, beside
  `lifecycle_changes_only_next_opening_needs_and_restarts_without_a_new_job` (535): add
  `a_benefit_per_person_follows_births`: the same opening, plus a fund (cash $1,000, its location
  and a budget in proportion) paying $10 a person to the lifecycle's principal. Assert the due of
  period 2 exceeds that of period 1 by 40_000_000 (four births) and the state's version byte is 26.
  In `babylon-tick`: `the_register_refuses_program_receipts` (a transition whose `public_programs`
  holds one row, its state otherwise plain: `MaterialWorldError::Wire`).
- [ ] **Step 2: Run them and see them fail** (`binary(small_world)`, `binary(recurring_circuit)`).
  Step 3: **Implement** the types, checks, bytes, dues, payment, receipts and the tick's refusal.
- [ ] **Step 4: Run** both binaries, `binary(financial_circuit)`, the crate, then `-p babylon-tick`
  (its county review tests pass unchanged) and `-p babylon-persistence`.
- [ ] **Step 5: Commit** `feat(material-circuit): public programs, and a benefit for each person`.

### Task 4: Half pay after a layoff, and the record of who was laid off when

**Files:**
- Create: `src/financial/layoffs.rs` (with its `#[cfg(test)] mod tests`)
- Modify: `src/financial/model.rs` (`LayoffRecord`; `FinancialInstitutions.layoffs`);
  `src/financial/programs.rs` (the after-layoff dues); `src/financial/validation.rs`;
  `src/wire/financial.rs` (the records in the tail); `src/transition/state.rs`
  (`finish_with_staffing` beside `finish_with_workforce` at 772; the refusal in the public entry
  points, decision 6);
  `contracts/material_circuit_v4.yaml` (the `public_programs` section gains the record; the
  `staffing` section at 630 says the record of layoffs lives in the circuit state and is advanced
  from member receipts) and the digest; the 4 `FinancialInstitutions {` literals and `empty()` get
  `layoffs: vec![]`
- Modify, tests: `tests/small_world/support.rs` (members; `finish_with_staffing` in `run`; a
  driven run); `tests/small_world/benefits.rs`

**Interfaces:**
- Consumes: `PublicProgram`, `PublicProgramTerms::AfterLayoff`, `program_dues`,
  `StaffingMemberReceipt` (`staffing/members.rs:139`, public fields).
- Produces:

```rust
/// One staffing member's people laid off in play and still looking, newest first: `cohorts[k]`
/// were laid off at the staffing of the period `k + 1` before this opening. Never empty; the last
/// entry is not 0.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LayoffRecord {
    pub member_id: StaffingMemberId,
    /// The schedule of the job lost, set when the record is made and never refreshed.
    pub hours_per_person: u64,
    pub cohorts: Vec<u64>,
}
pub const MAX_LAYOFF_HALF_PERIODS: u16 = 26; pub const MAX_LAYOFF_PERIODS: usize = 13;
// FinancialInstitutions gains
pub layoffs: Vec<LayoffRecord>,
/// The cohorts after one staffing decision. `window` is the periods the record keeps.
pub(crate) fn advance_layoffs(cohorts: &[u64], window: usize, receipt: &StaffingMemberReceipt)
    -> Result<Vec<u64>, MaterialCircuitError>;
/// Persons covered and the amount owed this period for one member's record.
pub(crate) fn layoff_due(wage: Currency, hours_per_person: u64, wage_share_bps: u16,
    half_periods: u16, cohorts: &[u64]) -> Result<(u64, Currency), MaterialCircuitError>;
impl ClosedMaterialPeriod {
    /// `finish_with_workforce`, after advancing the record of layoffs from the member receipts.
    /// # Errors
    /// `PublicProgramInvariant` for a missing, repeated or inconsistent member receipt.
    pub fn finish_with_staffing(self, catalog: &MaterialCatalog, next_labor: Vec<LaborCapacityRow>,
        member_labor: Vec<MemberLaborCapacityRow>, members: &[StaffingMemberReceipt])
        -> Result<MaterialCircuitTransition, MaterialCircuitError>;
}
// tests/small_world/support.rs: staffing by hand, `employed(p)` each site's persons after period p
pub(crate) fn run_driven(world: &World, employed: impl Fn(u64) -> [u64; 4]) -> Vec<Snapshot>;
```

**Decisions (the plan's calls):**
1. **Where the record lives.** Not in `StaffingPoolState`: pools are read from graph fields in the
   tick (`material_staffing/composition.rs` 265 to 330), and the payment inside
   `close_material_period` sees only the circuit state. A pool's people belong to several households
   (`national_resident_allocation/allocation.rs:400-433`) and the wage is the member's own
   (`EmploymentTerms`). So the record is per member, in `FinancialInstitutions.layoffs`;
   `advance_pool` is unchanged. In the small world each pool has one member.
2. **Who has a record.** A member whose `EmploymentTerms` pays a `Wage` and whose payee is a
   recipient of an after-layoff program, while it has someone covered. A record whose cohorts are
   all 0 is removed, and so is one whose payee is no longer a recipient (a later command may drop
   one). A world with no layoff in play has no record, and its bytes are those of Task 3. The
   opening has none: people looking for work at the opening are never covered.
3. **Advancing the record** (`advance_layoffs`), for one receipt, in this order: (a) people who left
   the reserve without being hired (deaths, `reconcile_resident_workforce`, applied before
   staffing, so the receipt's `opening_reserve` already counts them) leave from the oldest end: the
   oldest cohorts are trimmed until the sum is at most `opening_reserve`; (b) every cohort ages one
   period and the one at `window` leaves; (c) `separations` start a new cohort at the front; (d)
   `hires` take from the newest cohort first, and once the covered are all back, from the
   uncovered; (e) trailing zeros are dropped, and the sum must be at most `closing_reserve`.
   Between members, hires follow `distribute_staffing_members`, in proportion to each household's
   people looking for work (lead's ruling), so the last laid off go back first inside one
   household's share of a pool only. The record says so (Task 5).
4. **The window** is the largest `ceil(half_periods / 2)` over the after-layoff programs, at most
   `MAX_LAYOFF_PERIODS`. Validation accepts up to 13 cohorts, so a later command that shortens a
   term is valid at once and the next finish trims the record.
5. **What a record is owed** (`layoff_due`): with `H = half_periods`, a cohort at `k < H / 2` counts
   two half periods, one at `k == H / 2` when `H` is odd counts one, older ones nothing. `units =`
   the sum of persons times those counts; `due = floor(wage x hours_per_person x wage_share_bps x
   units / 20_000)`, one floor per member. `covered` is the persons counted. A program's due for a
   recipient is the sum over that household's members. With $10, 10 hours, 5,000 points and
   `H = 13`: $50 a person for six periods, $25 in the seventh.
6. **The finish.** The refusal sits in the public entry points: `finish_with_labor`,
   `finish_with_workforce`, `advance_material_circuit` and `advance_material_circuit_with_aid`
   refuse a state that holds an after-layoff program (`PublicProgramInvariant`): the record could
   not age. Each then calls a private unchecked path (`finish_workforce_unchecked`, ending in the
   private `finish`). `finish_with_staffing` checks: each receipt's period is the closing period;
   one receipt per member; each receipt's household equals its member's payee; a member holding a
   record has a receipt, and so does every member that can have one (decision 2) at a site and unit
   that has any receipt. (A pool with labor force 0 and no members gets no receipt,
   `staffing/members.rs:218`, and is allowed.) Receipts of members that cannot have a record are
   ignored: the tick passes every pool's receipts, and most are not covered. It drops records whose
   payee is no longer a recipient, advances the rest, and calls the unchecked path. With no
   after-layoff program it equals `finish_with_workforce` exactly.
7. Validation of terms: `wage_share_bps` 1 to 10,000; `half_periods` 1 to 26; a household is a
   recipient of at most one after-layoff program (a second is refused). Of a record: its member
   has a `Wage` row (a record whose payee is no longer a recipient is valid and owed nothing, so a
   program change never makes the state unreadable); `hours_per_person` > 0; 1 to 13 cohorts, the
   last not 0; records unique and sorted by member, at most `MAX_STAFFING_MEMBERS`. Bytes: member
   32, hours `u64`, a `u8` count and each cohort `u64`.
8. In the small world, `run` always finishes with `finish_with_staffing`, the member receipts made
   by `distribute_staffing_members` from each pool's receipt and its one member. `World::benefits()`
   gains `laid_off`: after layoff, 5,000 points, 13 half periods, rank 0, to the four worker
   accounts. `run_driven` skips `advance_staffing`: it builds each member receipt and labor row from
   the persons it is given, and so tests the program, not the staffing rule.

- [ ] **Step 1: Write the failing tests.** In `layoffs.rs` (a receipt given as opening reserve,
  hires, separations; window 7 unless named):

| Test | cohorts | receipt | result |
|---|---|---|---|
| `a_layoff_starts_a_cohort` | [] | 0, 0, 2 | [2] |
| `cohorts_age_and_the_oldest_leaves_after_its_half` | [1, 0, 0, 0, 0, 0, 3] | 4, 0, 0 | [0, 1] |
| `hires_take_the_newest_first` | [3, 2] | 5, 4, 0 | [0, 0, 1] |
| `hires_beyond_the_covered_come_from_the_uncovered` | [2] | 10, 5, 0 | [] |
| `departures_leave_from_the_oldest_end` | [2, 3] | 4, 0, 0 | [0, 2, 2] |
| `a_shorter_window_drops_older_cohorts` (window 3) | [1, 1, 1, 1, 1, 1, 1] | 7, 0, 0 | [0, 1, 1] |

  `layoff_due` cases: ($10, 10, 5000, 13, [2, 0, 0, 0, 0, 0, 1]) gives (3, 125_000_000); ($10, 10,
  5000, 12, [0, 0, 0, 0, 0, 0, 4]) gives (0, 0); (10_000_001 micro, 7, 3333, 13, [1]) gives (1,
  23_331_002).

  In `tests/small_world/benefits.rs`, every world `World::benefits()` with the fund's opening cash at
  $10,000 unless named:
  - `the_fund_with_both_programs_is_still`: 34 periods, every period equals the first; `laid_off`
    due 0 for each worker account; `no_earner` 480_000_000; no layoff record in any state.
  - `a_layoff_is_paid_half_pay_for_six_and_a_half_periods`: `run_driven` with employed `[10, 4, 4,
    4]` from period 1 on. Assert `laid_off` for `w_utility`, periods 2 to 9: due and paid
    100, 100, 100, 100, 100, 100, 50, 0 (dollars, as micro-units), covered 2, 2, 2, 2, 2, 2, 2, 0;
    period 1: 0.
  - `the_last_laid_off_go_back_first`: employed `[10, ...]` after period 1, `[7, ...]` after 2,
    `[11, ...]` from 3 on. Assert due for periods 2 to 9: 100, 250, 50, 50, 50, 50, 25, 0.
  - `finishing_without_the_member_receipts_is_refused`: the opening, closed, then
    `finish_with_workforce` gives `PublicProgramInvariant`; so does `advance_material_circuit`.
  - `a_member_receipt_for_another_household_is_refused`: `PublicProgramInvariant`.
  - `a_dropped_recipient_leaves_a_readable_state`: after the layoff of the test above, remove
    `w_utility` from `laid_off`'s recipients; the state validates and round-trips, the next period
    owes it nothing, and the next finish removes its record.
  - `a_household_in_two_after_layoff_programs_is_refused`: `PublicProgramInvariant`.
  - `without_an_after_layoff_program_both_finishes_agree`: for `World::taxed()`, period 1's
    transition from `finish_with_staffing` equals that from `finish_with_workforce`.
- [ ] **Step 2: Run them and see them fail.** Step 3: **Implement** the record, its advance, its dues,
  its bytes and the finish.
- [ ] **Step 4: Run** `binary(small_world)` (every earlier small-world test keeps its figures),
  `binary(resident_staffing)`, `binary(staffed_closing)`, the crate, then `-p babylon-tick`.
- [ ] **Step 5: Commit** `feat(material-circuit): half pay for 26 weeks after a layoff in play`.

### Task 5: The small world with a fund, pushed

**Files:**
- Modify: `tests/small_world/support.rs` (`Push` and `World::pushed`; the existing constructors
  become `Self::plain().pushed(..)` with the same figures); `tests/small_world/dump.rs` (six more
  runs); `tests/small_world/benefits.rs` (the pins);
  `reports/economy-repair-2026-11-20/small-world.md` (a new section after "What this means")

**Interfaces:**
- Consumes: `World::benefits`, `run`, the snapshot's program figures.
- Produces:

```rust
#[derive(Clone, Copy, Debug)]
pub(crate) enum Push { LessDemand, LessSupply, LessMoney, HigherPay, LowerFundTaxes }
impl World { pub(crate) fn pushed(self, push: Push) -> Self; }
```

**Decisions (the plan's calls):**
1. P1 to P4 are today's pushes applied to `World::benefits()` with its $960: the owner's cohort
   counts half its persons (8 to 4); the farm yields 9; the shop opens with $700; the clinic pays
   $11. P5 (`LowerFundTaxes`) cuts the fund's two rates by a quarter, 1500 to 1125, and leaves the
   treasury's: the fund then collects 270 + 90 = 360 against 480, drains its reserve by about 120 a
   period, and is first short at about period 6 unless layoffs come sooner. Both programs are rank 0,
   so the cut falls on both in the same proportion.
2. The record is what the engine does. Nothing is tuned to give an expected result. The expectation
   to test, not to assume: a layoff cuts a household's spending by about half for six and a half
   periods and then to nothing, in two steps that the program's receipts show. The small world's
   worker accounts are pooled, so the report gives the covered persons and the account's income and
   purchases, and says how far the pooled account is from the single household of the expectation,
   and that across a pool's households people go back in proportion (in the small world one each).

- [ ] **Step 1: Run the dump** (`mise run rust:test:q -- -p babylon-material-circuit -E
  'binary(small_world)' --run-ignored only`, or the crate's documented form of `--ignored`) with the
  six new runs: fund quiet, P1 to P5 on the fund.
- [ ] **Step 2: Write the report section** "With a national fund", in the style of the existing
  sections: the derivation (taxes 5% and 15%, the fund's $960, $60 a person, half pay for 13 half
  periods); the quiet run; for each push its table of the periods 1, 2, 3, 5, 8, 13, 21, 34 with
  the existing columns plus "fund cash", "due / paid" of both programs and "covered"; for each the
  class of its end (still, settles, runs away) beside the same push without the fund; the first
  period of a cut in P5 and how the cut was shared; and whether the two steps of a layoff appear,
  with the period numbers. Then a numbered list of what the fund changes, as the existing list.
- [ ] **Step 3: Pin the record** in `benefits.rs`, one test for each push, named for its end
  (`p1_with_a_fund_<what happens>`): the figures the report names (the period of the first layoff
  and of the first cut; the covered persons and dues of the first layoff cohort that is not taken
  back for 8 periods, period by period; the period-34 unmet triple; the fund's cash at 34). Add
  `every_cut_is_in_proportion` for P5: in each period where the fund is short, with `total` the
  rank's dues and `budget` the fund's cash at that opening, each rank-0 receipt's paid is
  `floor(due x budget / total)` or that plus one, and the paid amounts add to the budget.
- [ ] **Step 4: Run** `binary(small_world)`, then the crate (`pushed.rs`, `quiet.rs`, `tiers.rs` keep figures).
  **Step 5: Commit** `test(material-circuit): the small world with a national fund, pushed`; the
  lead reads the report and runs the whole gate.

## Later plan A: the tick, the stored records and the client

The tick refuses this plan's records (Tasks 1 and 3) until this plan lands. It must land before
later plan B, or the tick refuses every period of the shipped world. It must:

1. **Finish with staffing.** `babylon-tick/src/material_replay.rs` at 353 calls
   `finish_with_staffing` with `effects.member_receipts()` in place of `finish_with_workforce`;
   `MaterialWorld::prepare_next` (`register.rs:855`, `advance_material_circuit`) is refused for a
   world with an after-layoff program and must say so, or take the staffed path.
2. **The register.** A new receipt family for `PublicProgramReceipt`. It is not fixed width: the key
   is a `u8` length and 1 to 32 bytes; then period `u64`, account 32, recipient 32, rank `u32`,
   covered `u64`, three `i128`. Formats are ordered: the price rule's Task 7 takes 23, the tiers
   plan's carrier 24, and this carrier 25, a superset of 24, chosen whenever the state has the
   extension; its row limit; the decoder. Tax receipts are ordered by `(payer, basis,
   public_recipient)` in `material_world/financial_receipt.rs:289`, bound 262,144. Remove both gates.
3. **The state.** Persistence's state storage (`receipt_storage`, `state_storage/layout.rs`)
   accepts state versions 25 and 26; `tools/devtools/national_storage_qualification.py` and its
   test learn them.
4. **Money's reconciliations.** Every check that explains a `PublicTransfer` movement by a
   `PublicBudgetReceipt` (`material_world/monetary_receipt.rs`, `money_journal`,
   `site_financial_statements/projection.rs`, `observer_reader/household.rs`) also accepts a
   program receipt's paid amount.
5. **The County Review** counts only its own account (Task 2). Add one refusal: it does not open on
   an account that holds a program or asks for the cut (its figures read `period_cap`). Persistence's
   `tests/support/household_accounts.rs:397` also sums every tax row of a household: filter it the
   same way, or say why its figure is the household's total.
6. **The client.** For each public body: its receipts by tax, its standing rows, its programs with
   what was due, paid and cut this period. For each household account: its benefits by program,
   the persons covered, and for a laid-off cohort the period its half pay halves and the period it
   ends: the two steps, seen coming.
7. A command that changes a program belongs to the politics lane; this plan's validation checks it.

## Later plan B: the national opening's side

In `rust/crates/babylon-persistence/src/national_economy/opening/financial.rs` and the scenario:

1. **The fund.** One national public account with an `InstitutionLocation`, a budget
   `CashInProportion` (cap 0, floor 0) and two periods of its payments as cash (O13). Foreign
   regions hold no program.
2. **The split.** Each place's wage and operating-income rows become one to the place's body and one
   to the fund, at the builder's rates (O13). Measure the count against `MAX_TAX_POLICIES`.
3. **The places' bodies** keep the capped rule and their rows: provision, relief list, City PD.
4. **The programs** (`defines.toml`, `schema_version = 8`): `no_earner`, per person, at the
   opening's tier-1 price of a person's needs, to every account with no earner at the opening and
   every collective residence's account of people with no job (O12), owner or not; `laid_off`, 5,000
   points, 13 half periods, to every United States worker account of every band. Both rank 0.
5. **No one is covered at the opening**: no layoff record; those looking for work keep today's
   county support (design call 16). The opening's report gives each body's receipts against
   payments and the fund's reserve in periods. The compiler is `national-world-v13` (O16).
