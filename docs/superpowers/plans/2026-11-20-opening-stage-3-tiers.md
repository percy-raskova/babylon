# Households Buy in Tiers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** A household buys its needs, then its comforts, then its luxuries, in the same markets and at
the same price as everyone else, with the money its own list does not need; each period records what
each account wanted and bought in each tier, and so its standard.

**Architecture:** A want is a catalog row inside the market policy. A household brings one bid per
market, a rung for its need and one for each want of the product, each rung with a reserve: the
posted cost of what is ahead of it in its list and still to buy. One pure function beside
`clear_market` prices such a market; a period-long list (`HouseholdLists`) gives the reserves and
writes the records. A want is used at its purchase and reaches no pantry and no reader of unmet need.

**Tech Stack:** Rust (`babylon-material-circuit`; one refusal in `babylon-tick`); `contracts/material_circuit_v4.yaml`.

**Spec:** `docs/superpowers/specs/2026-11-20-the-opening-of-the-national-economy-design.md`, rules O7
and O8 and section 2's four standards; ADR313. It amends
`docs/superpowers/specs/2026-11-20-price-of-a-short-market-design.md` (ADR312) at P2 and P7. Read
both, and `reports/economy-repair-2026-11-20/small-world.md`, before any task.

**Prerequisites:** the price rule's Tasks 1 to 6, 6b and 6c are built.
(`docs/superpowers/plans/2026-11-20-price-of-a-short-market.md`.) Task 4a reads the business limit
that its Task 5 gives a service bid. Task 6b plans a service, under a market policy, from
`MarketTable::demand_at_quote(moment, site, good, unit) -> Option<u64>`: `planned_quantity = (owed +
funded).max(future)`, `funded` being that demand (0 when no buyer bid). This plan's ladder markets
record their totals, so that demand counts every rung, wants included, and no planning rule is added.
Its Task 7 may land before or after; the two register refusals sit side by side until the later plan
(last section) removes both. Task 6c refuses a fixed-price seller of a product that is in the order
of paying. So a fixture that puts such a seller under a market policy pins its posted price with a
responsive policy (`minimum == maximum == unit_price`, `step` one millionth of a dollar), as Task
6c's fixtures do; this plan's lifecycle tests on `time_opening(4)` do that for the retailer's $4
offer. Tasks go in order: 1, 2, 3a, 3b, 4a, 4b, 5.

**Checked once against the code by a second reader on 20 November 2026; its findings are in the tasks.**

## Global Constraints

- Every line number is a hint, from the commit `c0f523c50` or the tree in flight; find each place by
  its quoted text.
- Work only in `/media/user/dev-ssd/worktrees/households-homes/babylon`, branch
  `codex/households-and-homes`. Start every shell command with `cd` to it (or to its `rust/`
  directory). Never push. No secrets, no `.env`, no `babylon-data` on this disk.
- One cargo or pytest process at a time, on the whole machine. Never pass `-j` or `--jobs`.
- A run that outlasts one command goes to the background with a log and its own marker (`...; echo
  "exit=$?" >> <log>`), waited for on that marker, never on `real` (zsh's `time` prints `total`).
  Leave no shell running when you report.
- **Scoped gate, run by every task before its last commit,** one leg at a time: from `rust/`,
  `mise exec -- cargo fmt --all -- --check`; `mise exec -- cargo clippy --workspace --all-targets
  --locked -- -D warnings -D clippy::cognitive_complexity`; the test binaries the task names with
  `mise run rust:test:q -- -p <crate> -E 'binary(<name>)'`; `mise run rust:test:q -- -p <crate>`
  once for each crate the task changed; `mise run check:bsl-sentinels`. The lead alone runs `mise
  run rust:check-no-docs`, after Task 4b and in Task 5.
- Commit one unit of work at a time: `git add <files>` then `PYTHONPATH=src mise exec -- git commit
  -q -F <message file>`; check that `git log --oneline -1` moved. The body ends with `Part of
  PER-371` and a `Co-Authored-By` line naming the model that wrote the commit. Never commit
  `uv.lock`.
- **Bytes.** A catalog with no want rows gives every byte it gives today: catalog, state, receipts,
  register. That holds with and without a market policy. No test of the price plan's Tasks 1 to 7
  changes a pinned value. If one must, stop and tell the lead.
- No floating point. Money is `i128` millionths of a dollar (`Currency`). Quantities are `u64`.
- Every refusal is a typed error. No panic, no `unwrap` outside tests, no silent clamp. This plan
  adds no refusal code: catalog, rung and record faults are `MarketClearingInvariant`, state faults
  `FinalDemandInvariant`, a service fault `ServiceInvariant`, an open order at the close
  `PurchaseInvariant`.
- Money is conserved: `payments::conserved` holds at every close; tests assert buyers' payments equal
  sellers' receipts. Functions stay under 100 lines and a cognitive complexity of 25.
- `contracts/material_circuit_v4.yaml` changes with its pinned digest
  (`MATERIAL_CIRCUIT_SOURCE_SHA256` in `rust/crates/babylon-material-circuit/src/wire/state.rs`) in
  the same commit. A contract line a task makes false is rewritten by that task, in the form
  "without wants ...; with them ...".
- Markdown is wrapped at 120 columns, headings at 80. Refer to the player as "they".

## Review Focus

1. **A market policy and no wants.** Version 6 catalog bytes, no new records, every receipt as the
   price plan pins it. Tests: Task 2's digest test; Task 3b's no-tier-rows test; every existing test.
2. **Cash that exactly covers needs** (the small world). Wants bid nothing, leave no order and no
   performance row, and reach no plan (Task 6b). Tests: Task 4a's unfunded want; Task 5's quiet run.
3. **A want of a product not needed.** A zero-target purchase row names its seller; no pantry row;
   every reader of purchase rows accepts it. Tests in Tasks 2, 3b, 4a and 4b.
4. **A comfort against a poorer need in a short market.** One price; the comfort can win (O8).
   Tests: Task 1 row 4; Task 3b and Task 4a, the comfort that outbids a need.
5. **A want that cannot be reached** (nothing on offer, a disabled row, priced out). Bought 0, no
   division by zero, no order, no unmet need; a need not met holds its posted cost back from every
   want for the rest of the period. Tests in Tasks 3a, 3b and 4a.

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `rust/crates/babylon-material-circuit/src/clearing/ladder.rs` | The bid with rungs and its price | 1 |
| `src/recurring/model.rs` | `WantTier`, `HouseholdWant` beside `HouseholdNeed` | 2 |
| `src/clearing/rule.rs` | `MarketClearingPolicy.household_wants` | 2 |
| `src/catalog.rs`, `src/wire/catalog.rs` | Want validation, canonical order, version 7 bytes | 2 |
| `src/recurring/validation.rs` | Purchase rows for wants | 2 |
| `src/tiers.rs` with `src/tiers/lists.rs`, `src/tiers/records.rs` | The period's lists, reserves, records, standards, order ids | 3a |
| `src/recurring/households.rs`, `src/valuation/close.rs` | Goods wants at the household moment, and their cost | 3b |
| `src/services/admission.rs`, `src/services/close.rs` | Service wants in their stage, and their use | 4a |
| `src/collection_funding.rs`, `src/collection.rs` | A donor's wants are checked and not counted as funding | 4b |
| `tests/market_clearing/{wants, service_wants, unreached_wants}.rs` | The engine's tests of tiers | 2 to 4b |
| `tests/support/household_time_cases.rs` | Wants that follow births and deaths; household time | 2, 3b, 4b |
| `tests/small_world/tiers.rs` | The small world with tiers, quiet and pushed | 5 |
| `reports/economy-repair-2026-11-20/small-world.md` | The record | 5 |

Paths below are under `rust/crates/babylon-material-circuit/` unless they start with `rust/` or
`contracts/`.

---

### Task 1: The bid with rungs

**Files:**
- Create: `src/clearing/ladder.rs`
- Modify: `src/clearing.rs` (module and re-exports), `src/lib.rs` (re-exports)

**Interfaces:**
- Consumes: `MarketOutcome` (`clearing/rule.rs`), unchanged; `clear_market` is not modified.
- Produces:

```rust
/// One rung of a bid: a quantity and the money the rung may not touch.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct BidRung { pub wanted: u64, pub reserve: Currency }
#[derive(Debug, Clone, PartialEq, Eq)]   // one buyer's bid in one market, rungs in its list's order
pub struct LadderBid { pub rungs: Vec<BidRung>, pub purse: Currency, pub limit: Option<Currency> }
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LadderOutcome {
    pub price: Currency,
    pub quantities: Vec<Vec<u64>>,   // for each bid, in the bids' order, one quantity per rung
    pub demand_at_quote: u64,
}
impl LadderOutcome {
    /// One quantity per bid, the sum of its rungs, for `MarketTable::record`.
    pub fn totals(&self) -> Result<MarketOutcome, MaterialCircuitError>;
}
/// # Errors
/// `MarketClearingInvariant` for a quote that is not positive, a negative purse or reserve, a bid
/// with no rung, or reserves that fall along a bid's rungs; `Arithmetic` on overflow.
pub fn clear_ladder_market(supply: u64, quote: Currency, bids: &[LadderBid])
    -> Result<LadderOutcome, MaterialCircuitError>;
```

**Decisions:**
1. **The rungs at a price `p`** (rule 5 of the brief). Above the bid's limit (a limit under the quote
   reads as the quote) every rung is 0. Else, with `spent = 0`, for each rung in order: `room = purse -
   reserve - spent`; 0 when `room <= 0`, else `min(wanted, floor(room / p))`; `spent += rung x p`.
2. **Reserves never fall along a bid** (the plan's call). With reserves that do not fall, each
   rung's quantity and each bid's total fall or stay as `p` rises, so the bisection of `clear_market`
   is sound and a rung sold at the price could pay for at least as much at the quote. The reserve
   rule of Task 3a gives reserves that never fall; a bid that breaks this is refused.
3. **The price** is `clear_market`'s algorithm on the bids' totals (the quote when demand fits; the
   quote and nothing sold at supply 0; else bisection up to `1 +` the largest `min(purse, limit)`).
4. **At a step** (demand at `stop` below the supply): the price is `stop - 1`; each bid's total is
   shared exactly as `clear_market` shares a bid's quantity (base at `stop`, margins, `floor` shares
   in `u128`, the last units in the slice's order). A bid's total then fills its rungs in order, each
   up to its quantity at `stop - 1`.

- [ ] **Step 1: Write the failing tests** in `ladder.rs` (`#[cfg(test)] mod tests`), one per row,
  asserting price, quantities and `demand_at_quote`. Money in millionths. A bid is
  `(purse, limit, [(wanted, reserve), ...])`; `M` is 1_000_000.

| Test | supply | quote | bids | price | quantities | at quote |
|---|---|---|---|---|---|---|
| `a_comfort_waits_for_the_money_its_needs_do_not_use` | 100 | 10M | (100M, -, [(5, 0), (5, 30M)]) | 10M | [5, 2] | 7 |
| `a_reserve_above_the_purse_bids_nothing` | 100 | 10M | (100M, -, [(5, 0), (5, 200M)]) | 10M | [5, 0] | 5 |
| `a_luxury_bids_after_its_comfort` | 100 | 10M | (200M, -, [(4, 0), (4, 40M), (10, 60M)]) | 10M | [4, 4, 6] | 14 |
| `a_comfort_outbids_a_poorer_need` | 10 | 10M | (1_000M, -, [(5, 0), (10, 0)]), (60M, -, [(6, 0)]) | 90_909_091 | [5, 5], [0] | 21 |
| `a_short_market_drops_the_luxury_first` | 12 | 10M | (200M, -, [(4, 0), (4, 40M), (10, 60M)]), (90M, -, [(6, 0)]) | 18_000_001 | [4, 4, 0], [4] | 20 |
| `a_step_fills_each_bids_rungs_in_order` | 7 | 75M | (300M, -, [(1, 0), (3, 0)]) three times | 100M | [1, 2], [1, 1], [1, 1] | 12 |
| `a_step_with_reserves` | 5 | 100M | (1_000M, -, [(2, 0), (2, 100M)]) twice | 300M | [2, 1], [2, 0] | 8 |
| `a_business_beside_a_household_ladder` | 120 | 100M | (10^15, 245M, [(100, 0)]), (5_000M, -, [(20, 0), (30, 1_000M)]) | 190_476_191 | [100], [20, 0] | 140 |

  Add `a_one_rung_ladder_is_clear_market`: for every row of `clearing::tests`'s table, the same
  bids as one rung each with reserve 0 and the same limit give that row's price, quantities (one per
  bid) and `demand_at_quote`. Add `the_laws_hold_for_ladders`: for the bids of rows 5, 6 and 8 and
  every supply from 0 to `demand_at_quote + 2`, assert: all quantities add to `min(supply,
  demand_at_quote)`; each rung is at most its `wanted`; for every rung `k` above 0, (the bid's rungs
  up to `k`) x price + rung `k`'s reserve is at most the purse; no bid above 0 has a limit under the
  price; the price is at least the quote; and the price at `supply + 1` is not above the price at
  `supply` when `supply >= 1`. Add `a_bad_ladder_is_refused`: a quote of 0, a purse of -1, a reserve
  of -1, no rungs, and reserves 0, 50M, 10M each give `Err(MarketClearingInvariant)`. (The values
  above were checked with an exact model, and the laws over 20,000 random markets.)
- [ ] **Step 2: Run them and see them fail** (`-E 'test(clearing::ladder::tests)'`: does not compile).
- [ ] **Step 3: Implement** `clear_ladder_market`, `LadderOutcome::totals` and the types.
- [ ] **Step 4: Run them and see them pass,** then `test(clearing::tests)` unchanged.
- [ ] **Step 5: Commit** `feat(material-circuit): a bid with a rung for each tier`.

### Task 2: Wants in the catalog and the state

**Files:**
- Modify: `src/recurring/model.rs` (the two types); `src/clearing/rule.rs` (the field and
  `wants_of`); `src/model.rs` (`MAX_HOUSEHOLD_WANTS`); `src/catalog.rs` (`validate_market_clearing`,
  `canonicalize`); `src/wire/catalog.rs` (`bytes`); `src/recurring/validation.rs` (108 to 116, 137);
  `src/services/admission.rs` (`requests`, 95 to 111); `src/household_lifecycle/close.rs`
  (`rebase_purchases`, 61 to 69, becomes `pub(super)`); every `MarketClearingPolicy` built by hand
  (`rg -n 'MarketClearingPolicy \{' rust/crates`: 8 literals in 6 files at `c0f523c50`) gets
  `household_wants: vec![]`; `contracts/material_circuit_v4.yaml` and the digest
- Test: `src/catalog.rs` tests; `src/recurring/households_tests.rs`; `src/household_lifecycle/tests.rs`;
  `tests/support/household_time_cases.rs` (`recurring_circuit` binary); `tests/market_clearing/wants.rs`
  (new module of the `market_clearing` binary) with `tests/market_clearing/support.rs`

**Interfaces:**
- Produces:

```rust
/// The tier of a want. Needs are tier 1 and are not a want.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[repr(u8)]
pub enum WantTier { Comfort = 2, Luxury = 3 }
/// What a household account buys, after its needs, when its money reaches it. A flow: what is bought
/// in a period is used in that period. So many units per person or per household, as a need.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdWant {
    pub principal_id: FinalDemandPrincipalId, pub tier: WantTier, pub good_id: GoodId,
    pub unit_id: UnitId, pub basis: HouseholdNeedBasis, pub units_per_basis: u64,
}
impl HouseholdWant {
    /// This period's quantity from the cohort's counts; the rules of `HouseholdNeed::required_quantity`.
    pub fn quantity(&self, cohort: &HouseholdCohort) -> Result<u64, MaterialCircuitError>;
}
// MarketClearingPolicy
pub household_wants: Vec<HouseholdWant>,
impl MarketClearingPolicy {
    /// One account's wants, in canonical order.
    #[must_use] pub fn wants_of(&self, principal: FinalDemandPrincipalId) -> &[HouseholdWant];
}
pub const MAX_HOUSEHOLD_WANTS: usize = 262_144;
```

**Decisions:**
1. **Wants live in the market policy** (the plan's call): no policy, no wants; no hand-built
   `MaterialCatalogDefinition` changes. 2. `canonicalize` sorts wants by `(principal_id, tier, good_id,
   unit_id)` and leaves the order of paying as written.
3. `validate_market_clearing` refuses with `MarketClearingInvariant`: `units_per_basis` 0; a product not
   in the order of paying; a key twice; more than `MAX_HOUSEHOLD_WANTS` rows (262,144: two tiers of
   the 131,072 bound on needs).
4. **Bytes.** No wants: version 6 and today's bytes. With wants: `MARKET_TIERS_CATALOG_SCHEMA_VERSION
   = 7` where 6 is written, then the version without the policy, the body, the market tail, then the
   wants tail: a `u32` count and each row as principal id, tier `u8`, good id, unit id, basis `u8`
   and units per basis `u64` big-endian (106 bytes), in canonical order.
5. **How a want reaches its seller** (the plan's call: the smallest change). A household's purchase
   rows are keyed by every product it needs or wants: `purchase_keys == need_keys ∪ want_keys`. Its
   stock rows stay its stored needs (`stock_keys == stored_need_keys`, unchanged). A purchase row whose
   product is no need of the account must have `target_closing_stock == 0`; its `maximum_purchase`
   is not read; `enabled == false` stops every rung of that product. A want's principal must be a
   cohort, and a `Households` basis is refused for a collective residence, as for a need. Refusal:
   `FinalDemandInvariant`. A want-only service row keeps today's provider-connection check. Purchase
   rows stay capped at `MAX_HOUSEHOLD_NEEDS` (`row_limits` in `validation.rs`; contract
   `household_needs_and_purchase_policies: 131072`): the union of need and want keys must fit it, and
   is refused with `RowLimit` otherwise.
5b. **Wants follow persons** (ruling of the lead). A need's units per basis live in the catalog, its
   counts in the cohort, which `household_lifecycle::close` moves at each birth and death before
   `rebase_purchases` resets the need rows. A want takes the same path: each period's quantity is
   `HouseholdWant::quantity` of the cohort as the period opens. With no lifecycle book the counts, and
   so the quantity, stay as opened.
6. Readers that need a need per purchase row skip a row without one: `requests` makes no need request
   for it; `rebase_purchases` leaves it as written; `household_intents` already skips it.
7. Until Task 3b a want is admitted, never bought. Contract: `catalog_version` (72 to 74) gains "with
   household wants 7, and the wants tail after the market tail"; the row list (121 to 123) gains
   `household_wants: [count_u32, rows of principal_id, tier_u8, good_id, unit_id, need_basis_u8,
   units_per_basis]`; `catalog_canonical_keys` gains `household_wants: [principal_id, tier_u8, good_id,
   unit_id]`; `market_clearing.admission` gains the three refusals of decision 3; the state
   `admission:` line (from 298) "each configured household need has a purchase policy" becomes "each
   household need and want has a purchase policy; only stored needs have a pantry row including zeros;
   a policy for a want alone has a zero stock target"; `limits.family_overrides` gains
   `household_wants: 262144`.

- [ ] **Step 1: Write the failing tests.** In `src/catalog.rs`:
  `a_market_policy_without_wants_keeps_its_digest` (the policy fixture's `catalog_digest()`, printed
  before this task's change and pinned as a literal); `wants_write_version_seven_and_change_the_digest`
  (after the domain, the terminator `0`, then `u16` big-endian `00 07`, then the inner `u16`);
  `a_want_is_refused_when_zero_unlisted_twice_or_too_many` (four refusals);
  `wants_are_sorted_and_found_by_principal` (out of order in, canonical out; `wants_of` gives one
  account's). In `households_tests.rs`: `a_purchase_row_for_a_want_alone_is_admitted`;
  `a_want_without_a_purchase_row_is_refused`; `a_purchase_row_for_a_want_alone_with_a_stock_target_is_refused`.
  In `household_lifecycle/tests.rs`, `a_purchase_row_for_a_want_alone_survives_the_rebase` builds its
  own catalog (as `catalog.rs`'s tests do: one need, a policy with one want of a second good), a
  `RecurringEconomy` (one cohort, the need's row, the want-only row) and a book holding the principal;
  after `rebase_purchases` the want-only row's target is 0 and its maximum as written. In
  `tests/support/household_time_cases.rs`, beside `lifecycle_changes_only_next_opening_needs_...`,
  `wants_follow_births_and_deaths`: `time_opening(4)` with `market_clearing` set on its definition
  (order of paying `[good(2)]`, its one stored need) and a `Persons` tier 2 want of good 2, 2 units;
  the book of that test with births 250,000 per million (one birth of the four aged 18 to 64), and in
  a second case births 0 and deaths `[0, 0, 250_000, 0]` (one death); after one close the want's
  quantity, read with `HouseholdWant::quantity` from the closed state's cohort, is 2 higher, and in the
  second case 2 lower. In `tests/market_clearing/wants.rs`: `declared_wants_change_nothing_yet` (three
  accounts, one tier 2 want each, one of a good not needed: every receipt list equals the one without).
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement.** Extend `Fixture`
  (`tests/market_clearing/support.rs`) with `household_wants: Vec<(u8, WantTier, u8, u64)>` (account,
  tier, shelf good, quantity, written as a `Households` want of that many units: each account is one
  household) and `Shelf::needed: bool` (default true; false gives a purchase row and no need or stock
  row for that good).
- [ ] **Step 4: Run** the binary, `binary(recurring_circuit)`, the crate, `-p babylon-tick`, `-p babylon-persistence`.
- [ ] **Step 5: Commit** `feat(material-circuit): let a catalog name households' comforts and luxuries`.

### Task 3a: The period's lists and its records

**Files:**
- Create: `src/tiers.rs`, `src/tiers/lists.rs`, `src/tiers/records.rs`
- Modify: `src/lib.rs`; `src/services/admission.rs` (`requests` becomes `pub(crate)`);
  `src/services/close.rs` (`ServiceClose::new` takes the lists; `tier_receipts`);
  `src/transition/state.rs` (`close_funded_production`, where `MarketTable::default()` is made, opens
  the lists; the transition built near `market_clearings:` takes `tier_receipts`); `src/model.rs`
  (`MaterialCircuitTransition`); `rust/crates/babylon-tick/src/material_world/register.rs` (beside
  the refusal "if !transition.market_clearings.is_empty()")
- Test: `src/tiers.rs` tests; `rust/crates/babylon-tick/src/material_world/tests.rs`

**Interfaces:**
- Consumes: `BidRung` (Task 1); `HouseholdWant`, `WantTier`, `MarketClearingPolicy::wants_of` (Task 2).
- Produces:

```rust
/// Domain b"babylon.recurring-household-want-order.v1\0", then period, the key's three ids, the tier.
#[must_use] pub fn recurring_household_want_order_id(period: u64,
    key: (FinalDemandPrincipalId, GoodId, UnitId), tier: WantTier) -> OrderId;
/// Domain b"babylon.recurring-service-want-order.v1\0", then period, principal, provider, good,
/// unit, tier. Used from Task 4a.
#[must_use] pub fn recurring_service_want_order_id(period: u64,
    principal: FinalDemandPrincipalId, provider: SiteId, good: GoodId, unit: UnitId,
    tier: WantTier) -> OrderId;

/// One account, tier and product this period. `posted_price` values the tier; `unit_price` is the market's.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdWantReceipt {
    pub period: u64, pub principal_id: FinalDemandPrincipalId, pub tier: WantTier,
    pub seller_site_id: SiteId, pub good_id: GoodId, pub unit_id: UnitId, pub order_id: OrderId,
    pub wanted_quantity: u64, pub bought_quantity: u64, pub posted_price: Currency, pub unit_price: Currency,
}
/// One account and tier this period, at posted prices.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdTierReceipt {
    pub period: u64, pub principal_id: FinalDemandPrincipalId, pub tier: WantTier,
    pub wanted_value: Currency, pub bought_value: Currency,
}
// Both have `pub fn validate(&self) -> Result<(), MaterialCircuitError>`.

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum HouseholdStandard { GoingWithout = 1, GettingBy = 2, Comfortable = 3, Affluent = 4 }
/// # Errors
/// `MarketClearingInvariant` when a tier row of the account is missing or appears twice.
pub fn household_standard(principal: FinalDemandPrincipalId,
    consumption: &[HouseholdConsumptionReceipt], services: &[HouseholdServiceReceipt],
    tiers: &[HouseholdTierReceipt]) -> Result<HouseholdStandard, MaterialCircuitError>;

/// What every household has still to buy this period, and what it bought of its wants.
#[derive(Debug, Clone, Default)]
pub(crate) struct HouseholdLists { /* items; empty when the catalog has no wants */ }
pub(crate) struct ListRung { pub tier: u8, pub order_id: OrderId, pub rung: BidRung }
impl HouseholdLists {
    pub(crate) fn open(catalog: &MaterialCatalog, state: &MaterialCircuitState)
        -> Result<Self, MaterialCircuitError>;
    /// The rungs of one account in one market: its need (`need` units, reserve 0), then each want
    /// of the product, each with its reserve.
    pub(crate) fn rungs(&self, principal: FinalDemandPrincipalId, good: GoodId, unit: UnitId,
        need: u64) -> Result<Vec<ListRung>, MaterialCircuitError>;
    /// Record each rung's (order id, bought), the need's included, and settle the product's items.
    pub(crate) fn settle(&mut self, principal: FinalDemandPrincipalId, good: GoodId, unit: UnitId,
        bought: &[(OrderId, u64)], price: Currency) -> Result<(), MaterialCircuitError>;
    pub(crate) fn is_want_order(&self, order: OrderId) -> bool;
    pub(crate) fn receipts(&self, period: u64)
        -> Result<(Vec<HouseholdWantReceipt>, Vec<HouseholdTierReceipt>), MaterialCircuitError>;
    /// Tests only: a list from hand-built items, without a catalog or a state.
    #[cfg(test)] pub(crate) fn from_items(items: Vec<ListItem>) -> Self;
}
// ServiceClose::new gains `lists: HouseholdLists` after `donor`; it keeps them for Tasks 3b to 4b.
impl ServiceClose { pub(crate) fn tier_receipts(&self, period: u64)
    -> Result<(Vec<HouseholdWantReceipt>, Vec<HouseholdTierReceipt>), MaterialCircuitError>; }
// MaterialCircuitTransition, after market_clearings
pub household_wants: Vec<HouseholdWantReceipt>,  // sorted (principal, tier, good, unit)
pub household_tiers: Vec<HouseholdTierReceipt>,  // sorted (principal, tier)
```

**Decisions:**
1. **The list** is opened in `close_funded_production` before the household moment, only under a
   market policy with wants; otherwise it is empty and nothing below runs. For each household
   cohort it holds one item (`ListItem`) per need and per want: tier (1, 2 or 3), place in the order
   of paying (`usize::MAX` for a need outside it), product, seller (the purchase row's), posted price
   (the seller's offer), quantity wanted, quantity bought and quantity still to buy. A goods need's
   quantity is today's `requested_quantity`; a service need's is its `Request::requested` from
   `requests` (already net of orders funded earlier); a want's is `HouseholdWant::quantity` of the
   cohort, or 0 when its purchase row is disabled.
2. **The reserve of a want rung** of tier `t` at place `q` (rule O8, brief point 4) is the posted
   cost, `quantity still to buy x posted price`, of the account's items of every other product that
   are needs, or wants of an earlier tier (2 before 3), or wants of tier `t` at a place before `q`.
   The account's own need and earlier wants of this product are the rungs before it. Reserves so
   built never fall along a bid (the second reader confirmed it).
3. **What is still to buy** (ruling of the lead, reading O8 as approved). A need is still to buy, for
   the whole period, by the part of it the household did not get: `settle` sets its quantity still
   to buy to `wanted - bought`, and that part's posted cost is held back from every comfort and
   luxury until the period closes. This holds against wants only: a later need of the same period
   still bids with the whole purse, as O8 says, and may spend that money. Next period every need bids
   with the whole purse as always. A want is done once its market has cleared for the household,
   whatever it got: `settle` sets its quantity still to buy to 0.
4. **Records.** Each period, for every want of a cohort, one `HouseholdWantReceipt`: `wanted` is the
   item's quantity; `bought` what its rung bought; `unit_price` the market's price, or the posted price
   when its market was not reached. For every cohort, whenever the catalog has a want, one
   `HouseholdTierReceipt` per tier, its values the sums over the account's want rows of `wanted x
   posted` and `bought x posted` (zero when it has none in that tier). Validation
   (`MarketClearingInvariant`): period > 0; `bought <= wanted`; posted > 0; `unit_price >= posted`;
   `bought_value <= wanted_value`, both `>= 0`; and each tier row equals the sums of its want rows.
5. **The standard**: going without when any need row of the account (`consumption` or `services`)
   has `unmet_quantity > 0`; else getting by when tier 2's `bought_value < wanted_value`; else
   comfortable when tier 3's is; else affluent. A pooled account is read the same way from its two
   values.
6. Until Task 3b nothing is bid for: every want row shows bought 0 at the posted price.
7. **The register refuses** a transition whose `household_wants` or `household_tiers` is not empty,
   with `MaterialWorldError::Wire`, beside the market refusal. Any period of a catalog with wants has
   both, so the refusal covers the rows wants add to other families (fulfillments, handling,
   transfers, service performance).

- [ ] **Step 1: Write the failing tests.** In `src/tiers.rs`, on lists made with `from_items` (one
  account, food need 10 at $4, utility need 10 at $2 (stage 1), a tier 2 want of 5 utility and a tier
  3 want of 5 food at place 0):
  `the_reserve_counts_what_is_ahead_and_still_to_buy` (the tier 3 food rung's reserve is $20 + $10 =
  $30 before any market, $0 after utility settles with its need met and its want bought 0);
  `an_unmet_need_keeps_its_reserve_and_a_want_does_not` (utility settles with its need bought 4 and
  its want bought 0: the food luxury's reserve is $12, the 6 utility units not got, and nothing for the
  want); `reserves_never_fall_along_a_bid` (`rungs` of each product gives non-falling reserves);
  `receipts_sum_each_tier_at_posted_prices`; `each_standard_is_read_from_the_records` (four cases);
  `a_missing_tier_row_is_refused`; `want_order_ids_differ_by_tier_and_from_the_need`. In the tick's
  `material_world/tests.rs`: `a_transition_with_household_wants_is_refused` and
  `a_transition_with_tier_rows_is_refused` (close `admission_control()`'s period, push one row,
  `encode_material_receipts` gives `Err(Wire)`).
- [ ] **Step 2: Run them and see them fail** (`-E 'test(tiers::tests)'`). **Step 3: Implement.**
- [ ] **Step 4: Run** the crate (every existing test unchanged), then `-p babylon-tick`.
- [ ] **Step 5: Commit** `feat(material-circuit): what each household has still to buy, and its records`.

### Task 3b: Households buy goods in tiers

**Files:**
- Modify: `src/recurring/households.rs` (`sell_household_goods`, `sell_market`, `complete_purchases`,
  `consume_household_needs`); `src/valuation/close.rs` (`retail`, 555 to 597 at `c0f523c50`);
  `src/transition/state.rs` (pass the lists to `sell_household_goods`);
  `contracts/material_circuit_v4.yaml` and the digest
- Test: `tests/market_clearing/wants.rs`; `tests/support/household_time_cases.rs`

**Interfaces:**
- Consumes: `clear_ladder_market`, `LadderOutcome::totals` (Task 1); `HouseholdLists::{rungs, settle,
  is_want_order}`, `recurring_household_want_order_id` (Task 3a); `MarketTable::record` as today.
- Produces: `CostClose::use_at_purchase(&mut self, order: OrderId)` (`pub(crate)`: the order's goods
  are used at the purchase, not stocked); `sell_household_goods` gains `lists: &mut HouseholdLists` after
  `markets`.

**Decisions:**
1. **The household moment.** A market's bids are one per account with a positive total wanted and a
   positive purse, sorted by `recurring_household_order_id(period, key)` (also for an account that
   wants the product and does not need it), so a catalog without wants bids exactly as today. Purse:
   the account's cash; no limit. The table records `outcome.totals()` with the number of bids, so its
   demand at the quote counts every rung, and Task 6b's `MarketTable::demand_at_quote` reads it for a
   ladder market as for a one-rung market. `settle` runs for every account with an item in the
   market, bidding or not.
2. **A want rung that sells is its own order**, `recurring_household_want_order_id`: escrow at the
   market's price, `costs.use_at_purchase(id)`, hand-over with the need orders of the market, then
   settled and retired at once. It is never credited to the pantry. `CostClose::retail`, for a marked
   order, posts the household's payment to its `consumption_expense` instead of the pantry's basis or
   `final_demand_outlay`.
3. The need's `HouseholdDemandReceipt` is today's, from the need rung alone.
4. `consume_household_needs` also refuses (`PurchaseInvariant`) an open order or reserve under any
   want order id of the period.
5. **Why the state check of household orders still holds.** `validate_households`
   (`validation.rs`, "!stock_keys.contains") refuses a household order whose product has no stock
   row. A want order of a good that is only wanted has none; the check stays safe because every want
   order is made and retired inside `sell_household_goods`, between two `validate` calls.
6. Contract: `market_clearing.P2_bid` and `P4_shares` get the rungs and "a bid's share fills its
   rungs in order"; `P7_order_of_paying` gets "a household's list goes by tier first and by the order
   inside a tier"; a new `household_tiers` section states O7, O8 and Task 3a's decisions 2 to 5 in the
   contract's style; `allocation` ("with one, a household's purchase is made at the market's price")
   gains "a want is handed over and used at once, never credited to stock"; the stock identity line
   ("household opening stock plus actual handoffs", 487 at `c0f523c50`) reads "plus actual need
   handoffs"; the state admission line "every finite order of a configured household names a captured
   recipient stock before admission" (336) becomes "... before admission; a want's order, made and
   retired within the household moment, names none"; valuation ("household handoff capitalizes
   pantry purchases") gains "a want's purchase is consumption expense at the hand-over".

- [ ] **Step 1: Write the failing tests** in `tests/market_clearing/wants.rs`, on the three-account
  fixture: one retailer, good 2 at $4, each account needs 100; purses $400, $600, $40,000.
  - `a_comfort_buys_with_the_money_needs_do_not_use`: stock 1,000; each account a tier 2 want of 50.
    Assert want rows (wanted, bought) (50, 0), (50, 50), (50, 50), each `unit_price` 4_000_000; tier 2
    rows (200_000_000, 0), (200_000_000, 200_000_000) twice; tier 3 rows all (0, 0); standards
    `GettingBy`, `Affluent`, `Affluent`; the retailer's cash rises by $1,600 and equals what
    households paid; each pantry closes as in the same fixture without wants; the third account keeps
    $39,400; no order remains.
  - `a_comfort_outbids_a_poorer_need`: stock 240; the third account a tier 2 want of 100. Assert the
    market's price 24_000_001 on every purchase; the need receipts admit 16, 24 and 100; the want row
    bought 100; unmet need 84 and 76 for the first two; standards `GoingWithout`, `GoingWithout`,
    `Affluent`; the market row has `supply` 240, `demand_at_quote` 400, `bidders` 3.
  - `a_want_of_a_good_that_is_not_needed`: a second shelf, good 3 at $10 with 100 in stock, not
    needed; order of paying [2, 3]; the third account a tier 3 want of 5 of good 3. Assert it buys 5
    at $10, has no stock row and no demand receipt for good 3, and the shelf closes at 95.
  - `a_luxury_waits_for_a_comfort_still_to_buy`: good 3 at $10, 1,000 in stock, not needed; order
    [2, 3]; the second account wants 50 of good 2 in tier 3 and 10 of good 3 in tier 2. Assert it buys
    25 of good 2 (its reserve is the $100 of good 3), then 10 of good 3, ends with $0, standard
    `Comfortable`.
  - `a_household_short_of_food_buys_no_leisure_with_its_money`: the food shelf (good 2) holds 0;
    good 3 at $10, 1,000 in stock, not needed; order [2, 3]; the first two accounts each want 30 of
    good 3 in tier 3. Assert the first buys 0 of good 3 and closes with $400; the second buys 20 (its
    reserve is the $400 posted cost of the 100 food it did not get) and closes with $400; both
    `GoingWithout`; their food unmet 100 each.
  - `an_empty_shelf_leaves_a_want_unbought`: the good-3 shelf holds 0; the want row has bought 0 and
    `unit_price` $10; no order or transfer names it.
  - `a_disabled_purchase_wants_nothing`: the good-3 purchase row disabled; the want row has wanted 0,
    and the account's tier is complete.
  - `a_market_policy_without_wants_writes_no_tier_rows`: the price plan's Task 3 fixture; both new
    vectors are empty.

  In `tests/support/household_time_cases.rs`, beside Task 2's lifecycle tests,
  `the_next_periods_wants_follow_a_birth`: the one-birth case closed twice; the second period's want
  receipt has `wanted_quantity` 2 higher than the first's.
- [ ] **Step 2: Run them and see them fail** (`binary(market_clearing)`, `binary(recurring_circuit)`).
  **Step 3: Implement.**
- [ ] **Step 4: Run** both binaries, the crate, then `-p babylon-tick`.
- [ ] **Step 5: Commit** `feat(material-circuit): households buy goods in tiers`.

### Task 4a: Service wants in their stage

**Files:**
- Modify: `src/services/admission.rs` (`Request` gains its tier; `requests`; `funded_at_quotes`;
  `price_stage_market`; `book_order`; `admit_stage`); `src/services/close.rs` (`credit_grants`,
  `consume_households`, `finish`); `contracts/material_circuit_v4.yaml` (the service lines "direct
  household service satisfaction consumes current performance without pantry stock" and the stage
  admission lines) and the digest
- Test: `tests/market_clearing/service_wants.rs`, `tests/market_clearing/service_support.rs`

**Interfaces:**
- Consumes: `HouseholdLists::{rungs, settle, is_want_order}`, `recurring_service_want_order_id`
  (Task 3a); `clear_ladder_market` (Task 1); the business limit of the price plan's Task 5.
- Produces: `Request` (`services/admission.rs`) gains `pub(super) tier: Option<WantTier>`, `None` for a need
  and for a business.

**Decisions:**
1. `requests` adds one request per catalog want whose product is a service: order id
   `recurring_service_want_order_id`, the purchase row's provider, `requested` as in Task 3a's item,
   floor 0. Orders funded earlier for the period are deducted from need requests only.
2. **A stage market's bids** are one per buyer. A business keeps one rung, its purse lowered by its
   floor as today (the floor is not a rung reserve), and its limit. A household's rungs are
   `lists.rungs(principal, good, unit, need)`. Bids are sorted by the need request's order id, or by
   `recurring_service_order_id(period, buyer, provider, good, unit)` for an account that only wants
   the product, so a catalog without wants bids as today. The table records `outcome.totals()`, so
   the demand at the quote that Task 6b plans from counts every rung.
3. `funded_at_quotes` reads the same rungs at the posted price, spending from its scratch cash and
   closing items in a scratch clone of the lists, so a stage's batches are made for wants that money
   can reach.
4. **A want's performance row** has `requested_quantity` = what its rung could pay for at the posted
   price with the account's cash at that moment, and `admitted_quantity` = what it bought. A want rung
   whose `requested` is 0 leaves no row and no order. (The plan's call, so that a want's row reads as
   a need's does; the next period's plan does not rest on it: it follows Task 6b.)
5. `settle` runs after each stage market for every account with an item in it, also after a market
   left out of the order of paying (`supply` `None`, public provision), so a public need bought in
   full stops reserving from later wants.
6. **Use.** `credit_grants` adds a household want order's performed quantity to a separate
   `wants_used` map, not to `households`. `consume_households` withdraws a key's want part first,
   `costs.consume_service(key, need + want, want, false)`, then the need as today from the need's own
   quantity. The `HouseholdServiceReceipt` counts the need alone. In `finish`, the loop that hands
   `used` to the rows in order-id order is changed: want rows first take `used = performed`,
   `unused = 0`, then the need rows share what is left in order-id order, as today.
7. `finish` refuses (`ServiceInvariant`) a want row whose performed quantity is not its admitted
   quantity; under a market policy every admitted order is performed in full.

- [ ] **Step 1: Write the failing tests.** `ServiceFixture` gains `household_wants: Vec<(u8, WantTier,
  u8, u64)>` (account, tier, service, quantity, written as a `Households` want: each account is one
  household); a want of a service the account does not need adds its purchase row and connection.
  Utility is $4, the local service $3, capacities 1,000 unless set. In `service_wants.rs`:
  - `a_utility_comfort_keeps_the_money_for_a_local_need`: one account, $500, needs 100 local, wants
    100 utility in tier 2. Assert the want's performance row: requested 50, admitted 50, performed
    50, price 4_000_000, used 50, unused 0; the utility's output receipt produced 50; the local need's
    household row satisfied 100, unmet 0, unused 0; no household row for utility; the want row
    wanted 100, bought 50; cash $0; standard `GettingBy`.
  - `a_short_local_service_sells_a_comfort_before_a_poor_need`: local capacity 100; account 0 has $150
    and needs 100; account 1 has $10,000, needs 50 and wants 100 in tier 2. Assert price 100_000_001
    on every local row; account 0 admitted 1 and unmet 99; account 1's need 50 and want 49; one
    market row with `demand_at_quote` 200; the provider's receipts equal the buyers' payments.
  - `an_unfunded_want_leaves_the_plan_as_it_was`: account 0 has $300, needs 100 local, wants 100 in
    tier 2. Assert no performance row for the want; the local market receipt's `requested_quantity`
    and `planned_quantity` are 100, as without the want (Task 6b's demand at the quote is 100); the
    want row 100 wanted, 0 bought.
  - `a_public_need_bought_stops_reserving`: a public need of 10 met in full and a tier 3 want of the
    local service: the want's reserve after the public market holds nothing for it.
  - `without_wants_the_stage_is_unchanged`: every receipt of `services.rs`'s first case equals its
    value with an empty `household_wants`.
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement.**
- [ ] **Step 4: Run** the binary, `binary(period_services)`, the crate, then `-p babylon-tick`.
- [ ] **Step 5: Commit** `feat(material-circuit): households buy services in tiers`.

### Task 4b: Wants kept out of every reader of unmet need

**Files:**
- Modify: `src/collection_funding.rs` (`reconcile`); `src/collection.rs` (the call of `reconcile`,
  "facts.admissions.reconcile"; `CollectionEvidence` gains the want order ids);
  `src/transition/state.rs` (`close_household_finance` passes them); `src/services/close.rs`
  (`want_orders`)
- Test: `tests/market_clearing/unreached_wants.rs`; `tests/support/household_time_cases.rs`;
  `tests/organizer_funding_control.rs`

**Interfaces:**
- Produces: `ServiceClose::want_orders(&self) -> BTreeSet<OrderId>` (`pub(crate)`); `CollectionEvidence`
  gains `pub want_orders: &'a BTreeSet<OrderId>`; `ServiceAdmissions::reconcile` gains `wants:
  &BTreeSet<OrderId>` after `movements`.

**Decisions:**
1. **Collection checks a want's money and does not count it as funding** (the lead's preferred fix,
   checked against the code). `capture_requests` keeps every row of the donor, wants included, as
   today, so `record_leg` (`collection_funding.rs`, the `PurchaseReservation(OutboundOrderId::Service
   (id))` arm) finds a leg for each want's reservation, settlement and refund and does not refuse it.
   `reconcile` verifies each want row's admission and payment legs as it does a need's, and leaves it
   out of `funded`. The other way, passing the want ids for `record_leg` to skip, would leave a want's
   payment unchecked, and `funded` must exclude wants anyway: `protected_refund` compares its
   `performed` with the need's household row, which counts the need alone (Task 4a, decision 6).
   `CollectionEvidence.performance` stays the whole period's performance.
2. **Readers of unmet need, and how wants stay out** (brief point 6): the consumption close reads
   pantry stocks, which wants never enter (Task 3b); `collection.rs` reads consumption, the household
   service rows and `funded` (decision 1); `household_lifecycle` reads no unmet need and skips
   purchase rows without one (Task 2); `household_time.rs` reads consumption and the household
   service rows (the loop over `consumption` and `services` that fills `unmet`), which hold needs
   only; the services' close counts needs only (Task 4a, decision 6).

- [ ] **Step 1: Write the failing tests.** In `unreached_wants.rs`,
  `an_unreached_want_is_not_going_without`: the goods fixture and the service fixture, each with every
  account given wants its money cannot reach; assert, against the same fixtures without wants: equal
  `household_consumption`, `household_services` and `household_demand`; every `unmet_quantity` 0;
  standard `GettingBy`. In `household_time_cases.rs`, `an_unreached_want_leaves_household_time_as_it_was`:
  `time_opening(4)` under the market policy of Task 2's lifecycle tests, with and without a tier 2
  want of good 2 its money cannot reach; equal `household_time`. In `organizer_funding_control.rs`,
  `a_donor_with_a_service_want_reconciles`: `a_donors_service_orders_reconcile_under_a_market_policy`'s
  case with one tier 2 want of the donor's utility (good 3) that its money reaches; assert the close
  succeeds with `Collected`, the want bought at least 1, and the donor's `household_services` rows
  equal those of the case without the want.
- [ ] **Step 2: Run them and see them fail** (the donor's case fails today with `PurchaseInvariant`).
  **Step 3: Implement.**
- [ ] **Step 4: Run** `binary(market_clearing)`, `binary(recurring_circuit)`,
  `binary(organizer_funding_control)`, the crate, then `-p babylon-tick`.
- [ ] **Step 5: Commit** `fix(material-circuit): keep wants out of every reader of unmet need`. The lead
  then runs the whole gate.

### Task 5: The small world in tiers

**Files:**
- Create: `tests/small_world/tiers.rs`
- Modify: `tests/small_world.rs` (the module); `tests/small_world/support.rs` (`World::with_tiers`,
  the want rows, three `Snapshot` fields); `tests/small_world/dump.rs`;
  `reports/economy-repair-2026-11-20/small-world.md`

**Interfaces:**
- Consumes: `HouseholdWant`, `WantTier`, `household_standard`, the transition's two new vectors.
- Produces (test support only):

```rust
impl World { pub(crate) fn with_tiers(self) -> Self; }   // also sets `market`
// Snapshot
pub want_bought: [u64; 3],                                        // units bought for wants, by good
pub tier_values: BTreeMap<&'static str, [(i128, i128); 2]>,       // dollars (wanted, bought), tiers 2, 3
pub standards: BTreeMap<&'static str, HouseholdStandard>,
```

**Decisions:**
1. **The wants** (the plan's call): every household account wants, per person (`Persons`, 1 unit),
   one household service in tier 2, and one food and one utility in tier 3, so they follow the
   cohort as needs do (P1's owner, counted at 5 persons, wants 5 of each). Order of paying unchanged:
   food, utility, household services.
2. **Why the quiet run stays still at any size:** each account's cash at its moments of sale is
   exactly its needs' posted cost (workers are paid their need at the opening, the owner holds its
   need), so every want's room is 0, and the markets' demand at the quote, from which Task 6b plans,
   is the needs' alone.
3. Runs without tiers do not move (their new fields are empty). Each run is recorded as it happens:
   a test pins what was measured, never what was hoped.
4. **The comparison** (the plan's call): each push with tiers beside the same push under the market
   policy without tiers; P2's exists, and this task adds P1, P3 and P4 as the baseline.

- [ ] **Step 1: Write the quiet test** `the_balanced_opening_with_tiers_is_still_for_34_periods`:
  `assert_still(&World::plain().with_tiers())` (`assert_still` moves from `quiet.rs` to support as
  `pub(crate)`); every snapshot's measures other than the three new
  fields equal the market-policy quiet run's; in every period the clinic's planned batches are 40,
  the utility's 120, and the clinic's service market receipt has `planned_quantity` 40;
  `want_bought` is [0, 0, 0]; every account `GettingBy`;
  `tier_values` (wanted, bought): w_utility (450, 0), (750, 0); w_farm, w_clinic and w_shop (150, 0),
  (250, 0); owner (300, 0), (500, 0). Run it: it fails to compile, then implement the support, then it
  passes.
- [ ] **Step 2: Run the eight pushed runs** through the ignored `dump_every_run` (P1 to P4 under the
  market policy, with and without tiers) and read them against the rules of the record. P2 under the
  market policy is already pinned (`pushed.rs`, `less_supply_under_a_market_policy_...`): compare
  against it and do not pin it again.
- [ ] **Step 3: Pin each run** in `tiers.rs`, one test per run named for what it does
  (`<push>_with_tiers_<outcome>`, `<push>_under_the_market_<outcome>`). Each pins: the first period
  in which each site's output is 0, if any; `unmet` at period 34; the largest worker account's cash
  at periods 13 and 34; the value bought for wants (both tiers, all accounts) at periods 1, 13 and
  34; the number of accounts at each standard at periods 1, 13 and 34; and money conserved.
- [ ] **Step 4: Record it** in `small-world.md`: a section "Tiers" after "P2 under the market
  policy": the wants and why the quiet run stays still; for each push, its table in the existing
  columns plus "wants bought $" and "standards", beside the run without tiers, and the rules that carry
  it. Add to "What this means" whether money a push frees is now spent on wants, and whether
  workplaces still run dry from idle cash in workers' accounts (its point 3), with the figures. Change
  no figure of the existing sections.
- [ ] **Step 5: Run** `binary(small_world)` and the gate. **Step 6: Commit** `test(material-circuit):
  the small world buys in tiers` with the record.

## What the later plan carries

The engine's transition now holds the records; the tick register refuses them (Task 3a, decision 7).
The plan that carries them into the register, the stored records and the client must do this, as the
price plan's Task 7 did for the market's receipt, and then remove the refusal.

**Two new families,** fixed width, before the register's framing:

| Family | Fields, in order | Bytes | Key, strictly increasing | Bound |
|---|---|---|---|---|
| household want | period `u64`, principal 32, tier `u8`, seller site 32, good 32, unit 32, order id 32, wanted `u64`, bought `u64`, posted price `i128`, unit price `i128` | 217 | (principal, tier, good, unit) | `MAX_HOUSEHOLD_WANTS` |
| household tier | period `u64`, principal 32, tier `u8`, wanted value `i128`, bought value `i128` | 73 | (principal, tier) | two per cohort |

The decoder checks each row's `validate`, each tier row against its want rows, and the tier byte.

**Rows that wants add to existing families,** each under a want order id that no demand or household
service receipt carries: `local_fulfillments`, `handling` and `money_transfers`
(`LocalFinalDemand(want id)`) for a goods want; `service_performance` rows (requested = what the rung
could pay at the posted price; no `household_services` partner) and `money_transfers` (`Service(want
id)`) for a service want. The stored records' joins and price checks must accept them: a want's price
is its market's (the market row's `clearing_price`, else the posted price).

**State and catalog.** A household purchase row may name a product the account does not need, with
a zero stock target. Persistence reads purchase rows as needs in `organizer_runtime/material_preview.rs:355`,
`production_projection/{households/projection.rs:213, households/services.rs:73, lifecycle/period.rs:139,
lifecycle/services.rs:199, merchants.rs:264}`, `qualification_audit/production_renewal.rs:683` and
`national_economy/opening/markets.rs:160, 392`. A catalog with wants writes version 7;
`economic_catalog/compile.rs` builds none until the scenario plan sizes the tiers.

**The format.** Receipt format 24, chosen when the catalog has wants (the price rule's Task 7 takes 23;
the benefits plan's carrier takes 25 as a superset of 24), with its storage domain, budget test and tool
tables, as that plan's Task 7 lists them.

**Organizer reports** must leave want orders out: in `babylon-tick/src/material_world/organizer_reports.rs`
`food()` (about 121 to 214) finds a hand-off's escrow through a demand receipt, so every want hand-off
gives `ReportRetailHandoff`; `service()` (about 254 to 310) sums performed over every row of a buyer,
good and unit against the household row. `babylon-practice-contract/src/organizer/partner_reports.rs`
shows them.

**Readers handled in this plan** that the brief's point 6 did not name: `CostClose::retail`
(`valuation/close.rs`, 555 to 597 at `c0f523c50`, which would add a want's payment to the pantry's
cost) in Task 3b, decision 2; `collection_funding.rs` (`capture_requests`, `reconcile`, `record_leg`) in
Task 4b, decision 1.

**The client** shows each account's standard (read with `household_standard`) and its tier values.
