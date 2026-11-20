# The Price of a Short Market Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** In a period in which a private seller is short, the price paid rises to the first level at
which what its buyers can pay for equals what there is, every buyer pays that price, and the seller
keeps the difference.

**Architecture:** The price is found when the buyers bid and the supply is known, before any money
is set aside, so the engine's rule that an accepted order keeps its price stands. One pure function
finds the price and each buyer's quantity. The engine calls it at four moments of a period:
households buying goods, the utility stage, the local service stage, and businesses restocking. A
household's goods are handed over at the purchase. A campaign asks for the rule with an order of
paying in its policy; the catalog carries it, and a catalog without it runs today's code byte for
byte.

**Tech Stack:** Rust (`babylon-material-circuit`, `babylon-tick`, `babylon-persistence`), the
language-neutral contracts under `contracts/`, TOML scenario defines, YAML decision records.

**Spec:** `docs/superpowers/specs/2026-11-20-price-of-a-short-market-design.md`. Rule numbers P1 to
P13 below are its section 4. Read sections 3 to 8 before any task.

**Build order:** Tasks 1 to 9 in order. Each task leaves every earlier compiler's bytes unchanged.
No campaign asks for the rule before Task 8, so the stored records' own checks of a price, which
Task 7 teaches about the rule, never meet a cleared price before then.

**Checked once against the code** by a second reader on 20 November 2026. Where a task names a line,
the line was read that day.

**After the repair experiments (20 November 2026, evening).** Twelve candidate repairs by policy text
were measured (`reports/economy-repair-2026-11-20/`). None keeps households supplied for 34 periods,
and the Director has ruled that the scenario's recipes and prices are rebuilt from the national
accounts (PER-371). So Tasks 1 to 7 are built now. Task 8's change to the shipped file and Task 9 land
with that rebuilt opening. One finding bears on Task 5: a buyer counts every order it holds as
arriving, also an order stuck behind a full route, and then stops ordering. The lead settles that rule
before Task 5 starts.

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
  run rust:check-no-docs`, after Task 6 and in Task 9.
- Commit one unit of work at a time: `git add <files>` then `PYTHONPATH=src mise exec -- git commit
  -q -F <message file>`; check that `git log --oneline -1` moved. The body ends with `Part of
  PER-370` and a `Co-Authored-By` line naming the model that wrote the commit. Never commit
  `uv.lock`.
- **Bytes.** A catalog whose `market_clearing` is `None` gives every byte it gives today: catalog,
  state, receipts, register. No test of an earlier compiler changes its pinned values. If one must,
  stop and tell the lead.
- No floating point. Money is `i128` millionths of a dollar (`Currency`). Quantities are `u64`.
- Every refusal is a typed error. No panic, no `unwrap` outside tests, no silent clamp.
- Money is conserved: `payments::conserved` must hold at every close, and each task's tests assert
  that the buyers' payments equal the seller's receipts.
- Functions stay under 100 lines and under a cognitive complexity of 25.
- A contract file under `contracts/` that changes gets its pinned digest updated in the same commit
  (`MATERIAL_CIRCUIT_SOURCE_SHA256` in `rust/crates/babylon-material-circuit/src/wire/state.rs` for
  `material_circuit_v4.yaml`; the tests name the others). A contract line that a task makes false
  is rewritten by that task, in the form "without a market policy ...; with one ...".
- Markdown is wrapped at 120 columns, headings at 80. Refer to the player as "they".

## Review Focus

1. **A catalog with no order of paying.** Expected: today's code path and today's bytes at every
   one of the four moments. Tests: every existing test passes unchanged; Task 2 adds a digest test.
2. **Nothing on offer.** A seller with no stock or no output and buyers with money. Expected: no
   order is made, no money moves, nothing divides by zero, the market's receipt records the posted
   price with nothing sold, and the seller's next plan sees what was wanted. Tests in Tasks 1, 3, 5.
3. **A buyer with no money, or a business under its floor.** Expected: it bids nothing, gets
   nothing, and does not move the price. Tests in Tasks 1 and 3.
4. **One buyer that wants more than the whole supply.** A household account is many households and
   pays up to its purse. A business stops at its limit (P5) and never pays its whole cash for one
   input. Tests in Tasks 1 and 5.
5. **A seller that already owes goods, or whose shelf feeds its own production.** Orders accepted
   earlier and not yet moved, service orders funded for this period by an organizer, and a retailer
   that also runs a process. Expected: owed orders are served first at their own prices; only the
   rest is on offer; what a household buys cannot be used up by the seller afterwards. Tests in
   Tasks 3, 4 and 5.

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `rust/crates/babylon-material-circuit/src/clearing.rs` | The price rule, the market policy, the market's receipt and the period's table of markets | 1, 2, 3 |
| `rust/crates/babylon-material-circuit/src/clearing/supply.rs` | What a seller has on offer: stock less what is owed, a merchant's hands and room | 3, 5 |
| `rust/crates/babylon-material-circuit/src/clearing/limit.rs` | A business's limit price (P5) | 5 |
| `rust/crates/babylon-material-circuit/tests/market_clearing.rs` with `tests/market_clearing/` | The engine's tests of the four moments | 3, 4, 5, 6 |
| `rust/crates/babylon-tick/src/material_world/clearing_receipt.rs` | The new receipt's bytes in the register | 7 |
| `ai/decisions/ADR312_the_price_of_a_short_market.yaml` | The rulings (committed with the design) | lead |

---

### Task 1: The price rule

**Files:**
- Create: `rust/crates/babylon-material-circuit/src/clearing.rs`
- Modify: `rust/crates/babylon-material-circuit/src/lib.rs` (module and re-exports);
  `src/model.rs` (`MaterialCircuitError::MarketClearingInvariant = 38`, with its arm in
  `TryFrom<u16>`); `contracts/material_circuit_v4.yaml` (the refusal code, and the pinned digest in
  `src/wire/state.rs`); `tests/weighted_freight.rs` (the registry test of refusal codes)

**Interfaces:**
- Produces:

```rust
/// One buyer's bid in one market.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MarketBid {
    /// What the buyer asks for at the posted price, before any cash limit.
    pub wanted: u64,
    /// The money the buyer can commit now. Never negative.
    pub purse: Currency,
    /// The highest price a business pays. `None` for a household.
    pub limit: Option<Currency>,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MarketOutcome {
    pub price: Currency,
    /// One quantity for each bid, in the bids' order.
    pub quantities: Vec<u64>,
    /// What the buyers could pay for at the posted price.
    pub demand_at_quote: u64,
}
/// # Errors
/// `MarketClearingInvariant` for a quote that is not positive or a negative purse;
/// `Arithmetic` on overflow, or when the demand at the quote does not fit `u64`.
pub fn clear_market(supply: u64, quote: Currency, bids: &[MarketBid])
    -> Result<MarketOutcome, MaterialCircuitError>;
```

**The algorithm** (the signature and the tests do not determine it):

1. A limit under the quote reads as the quote.
2. `can_pay(bid, p)` is 0 when `p` is above the bid's limit, else `min(wanted, floor(purse / p))`,
   with the minimum taken in `i128` before the cast to `u64`. `demand(p)` is the sum over the bids
   in `u128`.
3. `demand_at_quote = demand(quote)`. If it is at most `supply`: the price is the quote and each bid
   gets `can_pay(bid, quote)`.
4. Otherwise, if `supply` is 0: the price is the quote and every quantity is 0.
5. Otherwise find `stop`, the least price above the quote with `demand(stop) <= supply`, by
   bisection between `quote + 1` and `1 +` the largest of `min(purse, limit)` over the bids (at that
   price nobody can pay for one unit).
6. If `demand(stop) == supply`: the price is `stop` and each bid gets `can_pay(bid, stop)`.
7. Otherwise the price is `stop - 1`. Each bid first gets `base = can_pay(bid, stop)`. With `margin =
   can_pay(bid, stop - 1) - base` and `rest = supply - sum(base)`, each bid then gets `floor(rest x
   margin / sum(margin))` in `u128`, and the units still left go to the bids in the slice's order,
   each taking as much as its margin allows (the contract's `residual_grant`). The caller passes the
   bids in order of order id.

- [ ] **Step 1: Write the failing tests** in `clearing.rs` (`#[cfg(test)] mod tests`). One test for
  each row, asserting price, quantities and `demand_at_quote`. Money in millionths; a bid is
  `(wanted, purse, limit)`.

| Test | supply | quote | bids | price | quantities | at quote |
|---|---|---|---|---|---|---|
| `enough_for_all_sells_at_the_quote` | 300 | 75_000_000 | (100, 7_500_000_000, -), (100, 11_250_000_000, -), (100, 10^15, -) | 75_000_000 | 100, 100, 100 | 300 |
| `a_fifth_short` | 240 | 75_000_000 | the same | 132_352_942 | 56, 84, 100 | 300 |
| `half_short` | 150 | 75_000_000 | the same | 362_903_226 | 20, 30, 100 | 300 |
| `equal_purses_share` | 5 | 75_000_000 | (4, 300_000_000, -) three times | 150_000_000 | 2, 2, 1 | 12 |
| `nothing_on_offer_sells_nothing` | 0 | 75_000_000 | (100, 7_500_000_000, -), (100, 10^15, -) | 75_000_000 | 0, 0 | 200 |
| `a_business_stops_at_its_limit` | 120 | 100_000_000 | (100, 10^15, 106_000_000), (100, 10^15, 245_000_000), (50, 5_000_000_000, -) | 238_095_239 | 0, 100, 20 | 250 |
| `businesses_below_cost_share_at_the_quote` | 60 | 100_000_000 | (100, 10^15, 40_000_000) twice | 100_000_000 | 30, 30 | 200 |
| `a_step_at_the_quote_shares_what_is_left` | 7 | 100_000_000 | (10, 10^12, 100_000_000) twice, (4, 400_000_000, -) | 100_000_000 | 3, 1, 3 | 24 |
| `a_limit_under_the_quote_never_outbids` | 4 | 100_000_000 | (10, 10^12, 40_000_000), (10, 10^12, 150_000_000) | 150_000_000 | 0, 4 | 20 |
| `one_unit_and_three_purses` | 1 | 280_000_000 | (1000, 3_000_000_000, -), (1000, 9_000_000_000, -), (1000, 500_000_000, -) | 4_500_000_001 | 0, 1, 0 | 43 |
| `one_buyer_wants_more_than_there_is` | 10 | 280_000_000 | (1000, 9_000_000_000, -) | 818_181_819 | 10 | 32 |
| `an_empty_purse_does_not_bid` | 3 | 280_000_000 | (5, 0, -), (5, 1_400_000_000, -), (5, 560_000_000, -) | 466_666_667 | 0, 2, 1 | 7 |
| `food_at_the_scale_of_wayne` | 400_000 | 280_000_000 | (456_528, 127_827_840_000_000, -), (50_726, 56_813_120_000_000, -), (173_993, 24_359_020_000_000, -), (19_334, 16_240_560_000_000, -) | 461_254_209 | 277_130, 50_726, 52_810, 19_334 | 613_584 |
| `a_very_deep_purse_does_not_overflow` | 1_000_000 | 75_000_000 | (2_000_000, 10^24, -), (2_000_000, 150_000_000_000_000, -) | 999_999_000_001_000_000 | 1_000_000, 0 | 4_000_000 |

  Add `the_laws_hold_on_every_small_market`: for the bids of `a_business_stops_at_its_limit`,
  `equal_purses_share` and `a_step_at_the_quote_shares_what_is_left`, and every supply from 0 to
  `demand_at_quote + 2`, assert: the quantities add to `min(supply, demand_at_quote)`; each quantity
  is at most the bid's `wanted`; `quantity x price <= purse`; a bid with a quantity above 0 has no
  limit under the price; the price is at least the quote; and the price at `supply + 1` is not above
  the price at `supply` when `supply >= 1`. Add `a_bad_quote_or_purse_is_refused`: a quote of 0 and
  a purse of -1 each give `Err(MarketClearingInvariant)`. Add
  `wants_beyond_u64_are_refused_not_wrapped`: two bids that each want `u64::MAX` with purses that
  cover them give `Err(Arithmetic)`.

- [ ] **Step 2: Run them and see them fail.** `mise run rust:test:q -- -p babylon-material-circuit -E
  'test(clearing::tests)'`. Expected: does not compile, `clear_market` not found.
- [ ] **Step 3: Implement `clear_market`** as the algorithm above, with one private helper for
  `can_pay` and one for the sum.
- [ ] **Step 4: Run them and see them pass.** Then add the refusal code to the contract and the
  registry test, pin the digest, and run `mise run rust:test:q -- -p babylon-material-circuit`.
- [ ] **Step 5: Commit** `feat(material-circuit): find the price of a short market`.

### Task 2: The catalog's market policy

**Files:**
- Modify: `rust/crates/babylon-material-circuit/src/catalog.rs` (`MaterialCatalogDefinition` gains
  `market_clearing`; `validate` calls the new check; `canonicalize` leaves the order as written);
  `src/wire/catalog.rs` (`bytes`: version 6 and the tail); `src/clearing.rs` (the policy type and
  its lookups); `contracts/material_circuit_v4.yaml` (a `market_clearing` section stating P1 to P13
  in the contract's style, the catalog version line, and that "admitted escrows retain their own
  prices" stands); the pinned digest
- Modify: the 34 places that build a `MaterialCatalogDefinition` by hand get `market_clearing: None`
  (`rg -n 'MaterialCatalogDefinition \{' rust/crates` lists them with four headers in `catalog.rs`)

**Interfaces:**
- Produces:

```rust
/// The products that clear by price, in the order in which a buyer's purse reaches them.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MarketClearingPolicy { pub paying_order: Vec<(GoodId, UnitId)> }
impl MarketClearingPolicy {
    /// The product's place in the order, or `None` when it does not clear by price.
    #[must_use] pub fn place(&self, good: GoodId, unit: UnitId) -> Option<usize>;
}
// MaterialCatalogDefinition
pub market_clearing: Option<MarketClearingPolicy>,
```

**Decisions:**
1. `validate` refuses with `MarketClearingInvariant`: an empty order; a product named twice; a
   product that is not in `commodities`; a storable product that some row of `household_needs`
   names and the order leaves out (a campaign that clears by price prices every good its households
   buy; a service may be left out).
2. Catalog bytes: `Some` writes version 6, then, as a `u16`, the version the same catalog writes
   without the policy (2, 3, 4 or 5), then the body exactly as that version writes it, then the
   tail: a `u32` count and each product's good id and unit id, in the order of paying. `None` gives
   the version and the bytes of today. A market policy does not require company portfolios.
3. There is no catalog decoder: persistence rebuilds the catalog in `economic_catalog/compile.rs`.

- [ ] **Step 1: Write the failing tests** in `src/catalog.rs`'s tests (or the nearest existing
  catalog test file): `a_catalog_without_a_market_policy_keeps_its_digest` (build one existing
  fixture catalog, assert its `catalog_digest()` equals the value printed before this task's
  change, pinned as a literal); `a_market_policy_changes_the_digest_and_the_version`;
  `a_market_policy_is_refused_when_empty_duplicated_unknown_or_missing_a_household_good` (four
  refusals, each `MarketClearingInvariant`); `place_follows_the_order_of_paying`;
  `a_market_policy_needs_no_company_portfolio`.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement** the field, the check, the bytes and `place`. Add `market_clearing: None`
  to every hand-built definition.
- [ ] **Step 4: Run** `mise run rust:test:q -- -p babylon-material-circuit`, then `-p babylon-tick`,
  then `-p babylon-persistence`. Expected: all pass with no pinned value changed.
- [ ] **Step 5: Commit** `feat(material-circuit): let a catalog name its order of paying`.

### Task 3: Households buy goods at the market's price and take them home

**Files:**
- Create: `rust/crates/babylon-material-circuit/src/clearing/supply.rs`;
  `tests/market_clearing.rs`, `tests/market_clearing/support.rs`,
  `tests/market_clearing/households.rs`
- Modify: `src/recurring/households.rs` (new `sell_household_goods`; `admit_household_orders` and
  `complete_household_orders` stay as they are for a catalog without a policy); `src/clearing.rs`
  (the receipt and the period's table of markets); `src/model.rs` (`MaterialCircuitTransition` gains
  `market_clearings`); `src/transition/state.rs` (`close_funded_production` at 1324 calls the new
  function when the catalog has a policy; `dispatch_and_replenish` at 985 then does not call
  `complete_household_orders`, and adds the sale's fulfilment and handling receipts to its own; the
  table travels through `FundedProductionReceipts` to `next_plans` and the transition);
  `src/transition/outbound/orders.rs` (make the first pass's hand-over postings callable for one
  list of household sales); `src/equipment/choice.rs` (`sale_commitments` moves to
  `clearing/supply.rs` and is used from both); `contracts/material_circuit_v4.yaml` line 347 and
  the digest; `rust/crates/babylon-tick/src/material_world/register.rs` (refuse a transition whose
  `market_clearings` is not empty, with `MaterialWorldError::Wire`, as it does for an unexpected
  `company_basis`; Task 7 replaces the refusal)

**Interfaces:**
- Consumes: `clear_market`, `MarketClearingPolicy::place`.
- Produces:

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum MarketMoment { HouseholdGoods = 1, Utility = 2, LocalService = 3, Restocking = 4 }

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MarketClearingReceipt {
    pub period: u64,
    pub moment: MarketMoment,
    pub site_id: SiteId,          // the seller
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub quote_price: Currency,
    pub clearing_price: Currency,
    pub supply: u64,              // on offer to new buyers
    pub demand_at_quote: u64,
    pub sold_quantity: u64,
    pub bidders: u32,
    pub served_bidders: u32,
}
impl MarketClearingReceipt {
    /// # Errors: `MarketClearingInvariant` unless period > 0, quote > 0, clearing >= quote,
    /// demand_at_quote > supply, sold == supply, served <= bidders, and clearing == quote
    /// when supply == 0.
    pub fn validate(&self) -> Result<(), MaterialCircuitError>;
}
/// The markets of one close, in the order they cleared.
#[derive(Debug, Default)]
pub(crate) struct MarketTable { /* rows; the price paid by (moment, site, good, unit) */ }
impl MarketTable {
    /// Record one market: always its price, and a receipt when it was short.
    pub(crate) fn record(&mut self, period: u64, moment: MarketMoment, seller: (SiteId, GoodId, UnitId),
        quote: Currency, supply: u64, bids: usize, outcome: &MarketOutcome)
        -> Result<(), MaterialCircuitError>;
    /// What buyers could pay for at the posted price and did not get, at this seller's product.
    pub(crate) fn priced_out(&self, site: SiteId, good: GoodId, unit: UnitId) -> u64;
    pub(crate) fn has_row(&self, moment: MarketMoment, site: SiteId, good: GoodId, unit: UnitId) -> bool;
    /// Sorted by (moment, site, good, unit).
    pub(crate) fn into_receipts(self) -> Vec<MarketClearingReceipt>;
}
// clearing/supply.rs
/// What the seller owes to accepted orders: unshipped deliveries and unfilled retail orders.
pub(crate) fn sale_commitments(state: &MaterialCircuitState)
    -> Result<InventoryLedger, MaterialCircuitError>;
/// Tracks, for one moment of sale, what each seller still has on offer.
pub(crate) struct Offer { /* stock less what is owed; each merchant's hours and room left */ }
impl Offer {
    pub(crate) fn new(catalog: &MaterialCatalog, state: &MaterialCircuitState)
        -> Result<Self, MaterialCircuitError>;
    /// What the seller can sell of this product now.
    pub(crate) fn supply(&self, site: SiteId, good: GoodId, unit: UnitId)
        -> Result<u64, MaterialCircuitError>;
    /// Take a sale out of the stock, the hours and the room.
    pub(crate) fn take(&mut self, site: SiteId, good: GoodId, unit: UnitId, quantity: u64)
        -> Result<(), MaterialCircuitError>;
}
// recurring/households.rs
pub(crate) struct HouseholdGoodsSale {
    /// Final: fulfilled equals admitted and nothing is expired.
    pub demand: Vec<HouseholdDemandReceipt>,
    pub fulfillments: Vec<LocalRetailFulfillmentReceipt>,
    pub handling: Vec<MerchantHandlingReceipt>,
}
pub(crate) fn sell_household_goods(catalog: &MaterialCatalog, state: &mut MaterialCircuitState,
    costs: &mut CostClose, transfers: &mut Vec<MoneyTransferReceipt>, markets: &mut MarketTable)
    -> Result<HouseholdGoodsSale, MaterialCircuitError>;
// MaterialCircuitTransition
pub market_clearings: Vec<MarketClearingReceipt>,
```

**Decisions:**
1. With `market_clearing` `None`, nothing changes: `admit_household_orders` before production, the
   first shipping pass, `complete_household_orders`.
2. With `Some`, `sell_household_goods` runs where `admit_household_orders` runs today. It takes the
   markets sorted by `(place, retailer site id)` and the bids of a market sorted by order id
   (`recurring_household_order_id`). A bid: `wanted` is today's `requested_quantity`; the purse is
   the household's cash at that moment; no limit.
3. What a seller has on offer (`Offer`): stock less what it owes. For a merchant, also `hours left /
   hours per unit` and `room left / grams per unit`, where the hours are the seller's `state.labor`
   row for the period less the hours its owed orders need, and the room is
   `capacity::shared_available` for its `capacity_id` less the grams its owed orders need. Each sale
   is taken out before the next market of that seller is cleared.
4. A sale is completed at once, with the postings the first pass uses: the reserve at the market's
   price, the debit of the seller's stock, `costs.retail`, the handling hours and room with
   `costs.handling`, the credit of the household's stock, the settlement, and the retirement of the
   order. A posting that finds less than the sale needs is `MarketClearingInvariant`: the supply was
   read from the same state.
5. The demand receipt carries the market's price, `admitted_quantity` and `fulfilled_quantity` both
   equal to what was sold, and `expired_quantity` 0. Its other fields are as today.
6. A market leaves a `MarketClearingReceipt` only when `demand_at_quote > supply`.
7. The first shipping pass then sees no generated household order. Orders a household holds from an
   earlier period are served there as today.

- [ ] **Step 1: Write the failing tests** in `tests/market_clearing/households.rs`, on a small
  recurring economy built from `tests/recurring_circuit/support.rs`'s fixtures, with one retailer,
  one good at a posted price of $4 and three household accounts that each ask for 100 units and
  hold $400, $600 and $40,000:
  - `a_short_shelf_raises_the_price_for_everyone`: the shelf holds 240. Assert the three demand
    receipts carry one `unit_price` of 7_058_824, the admitted quantities are 56, 84 and 100, each
    is fulfilled in full, nothing is refunded, the retailer's cash rises by exactly the sum of the
    three payments, `payments::conserved` holds, and `market_clearings` holds one row with `supply`
    240, `demand_at_quote` 300, `sold_quantity` 240, `bidders` 3, `served_bidders` 3.
  - `a_full_shelf_sells_at_the_posted_price`: the shelf holds 300. Assert `unit_price` is $4 for
    all, quantities 100 each, and `market_clearings` is empty.
  - `an_empty_shelf_sells_nothing_and_moves_no_money`: the shelf holds 0. Assert no order, no
    transfer, and one row with `sold_quantity` 0 and `clearing_price` equal to the posted price.
  - `a_household_pays_for_food_before_materials`: two goods in the order of paying, both short, one
    account whose cash covers one of them. Assert it buys the first and is priced out of the
    second.
  - `without_a_market_policy_the_shelf_is_shared_in_proportion`: the first case with
    `market_clearing: None`. Assert today's result: each account is admitted 100 at $4 and receives
    80.
  - `goods_already_owed_are_not_on_offer`: the retailer owes 100 to an order accepted earlier and
    holds 240. Assert `supply` is 140.
  - `a_shelf_that_feeds_the_sellers_own_production_is_sold_first`: the retailer also runs a process
    that takes the same good as an input and would use all of it. Assert the households receive
    what they bought and the process runs on what is left.
  - `too_few_hands_make_a_short_market`: a merchant with stock for 300 and hours for 240. Assert
    `supply` is 240 and the price rises.
- [ ] **Step 2: Run them and see them fail.** `mise run rust:test:q -- -p babylon-material-circuit -E
  'binary(market_clearing)'`.
- [ ] **Step 3: Implement** `Offer`, the receipt, the table and `sell_household_goods`.
- [ ] **Step 4: Run** the binary, then the crate, then `-p babylon-tick`.
- [ ] **Step 5: Commit** `feat(material-circuit): households buy goods at the market's price`.

### Task 4: Services clear in their stage

**Files:**
- Modify: `src/services/admission.rs` (the due orders and the requests of one stage; admission at a
  market's price; the bounds of 238 and 264 counted over the whole period); `src/services/close.rs`
  (`ServiceClose::new` admits nothing when a market policy is present; `admit_stage`;
  `funded_at_quotes`; the donor's requests are captured once, from the finished `performance`,
  after the last stage); `src/production.rs` (`execute_production` calls `admit_stage` between
  `allocate_production_batches` at 414 and `services.allocate` at 423;
  `initial_production_allocations` takes the funded quantities it caps batches by);
  `src/transition/state.rs` (`execute_production_stages` passes the table);
  `contracts/material_circuit_v4.yaml` lines 348 to 351 and 761 to 764, and the digest
- Test: `tests/market_clearing/services.rs`

**Interfaces:**
- Consumes: `clear_market`, `MarketTable`, `MarketMoment::{Utility, LocalService}`.
- Produces:

```rust
impl ServiceClose {
    /// Bid for, price and fund the service orders of one stage. A no-op without a market policy.
    pub(crate) fn admit_stage(&mut self, catalog: &MaterialCatalog, state: &mut MaterialCircuitState,
        stage: ServiceStage, potential: &InventoryLedger, costs: &CostClose,
        movements: &mut Vec<MoneyTransferReceipt>, markets: &mut MarketTable)
        -> Result<(), MaterialCircuitError>;
    /// What buyers could fund at the posted prices, by market, for the stage's cap on batches.
    pub(crate) fn funded_at_quotes(&self, catalog: &MaterialCatalog, state: &MaterialCircuitState,
        stage: ServiceStage) -> Result<InventoryLedger, MaterialCircuitError>;
}
```

**Decisions:**
1. With `market_clearing` `None`: today's code, untouched.
2. With `Some`, a stage runs in this order. (a) `funded_at_quotes`: the stage's requests, taken
   market by market in the order of paying, each buyer spending `can_pay(quote) x quote` from a
   scratch copy of its cash; plus the orders already funded for this period in this stage. (b) The
   stage's batches are capped by that figure, then fitted to labor and inputs, as today. (c)
   `admit_stage`: first the receipts of the orders already funded for this period whose product is
   in this stage, and only those; then, for each market in `(place, provider site id)` order, the
   supply is the stage's potential output for the provider less those funded orders, the bids are
   the stage's requests with the buyers' real cash at that moment (a business's cash above the
   request's floor, with `limit: None` until Task 5), and each sale is set aside at the market's
   price. (d) `services.allocate`, production and `handoff` as today: every order admitted in the
   stage is performed in full.
3. `ServiceClose.performance` is sorted by order id after each stage (`allocate` searches it).
   `MAX_SERVICE_RECEIPTS_PER_PERIOD` and `check_order_principal_limits` count both stages together.
4. A service order funded earlier for this period keeps its price and is served first. If the
   potential output is under what is owed, the owed orders share it as today and nothing is on
   offer.
5. A service not in the order of paying, which in the national world is public provision, is
   admitted in its stage at the posted price and shared in proportion, as today.
6. The performance receipt of an order admitted in a stage carries `requested_quantity` as today,
   `admitted_quantity` as what was sold, and the market's price.

- [ ] **Step 1: Write the failing tests** in `tests/market_clearing/services.rs`, on
  `tests/period_services/support.rs`'s fixtures:
  - `a_short_utility_is_priced_in_its_stage`: one utility with output for 240, two households and
    one business that each ask for 100. Assert one price above the posted one on the three
    performance receipts, performed equals admitted on each, no refund, the provider's receipts
    equal the buyers' payments, and one market row with `moment` `Utility`.
  - `utility_is_paid_before_the_local_service`: a household whose cash covers the posted cost of
    both, a short utility and an ample local service. Assert it buys utility at the higher price and
    then less of the local service.
  - `an_order_funded_by_a_donor_is_served_first`: a service order already funded for this period
    for 50 units, output of 60, new bids for 100. Assert the funded order is performed in full at
    its own price, `supply` is 10, and the donor's funding reconciles (`collection::close` accepts
    the period).
  - `public_provision_is_still_shared`: a service left out of the order, short. Assert today's
    proportional result and no market row.
  - `a_stage_two_order_does_not_appear_in_stage_one`: both stages have orders funded earlier.
    Assert each appears once in `service_performance`.
  - `without_a_market_policy_services_are_admitted_at_the_start`: assert today's receipts.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the binary, `binary(period_services)`, the crate, then `-p babylon-tick`.
- [ ] **Step 5: Commit** `feat(material-circuit): price a short service in its stage`.

### Task 5: Businesses restock at the price of the market

**Files:**
- Create: `rust/crates/babylon-material-circuit/src/clearing/limit.rs`
- Modify: `src/recurring/firms.rs` (`replenish` gains `catalog`, `costs` and the table);
  `src/transition/state.rs` (its caller at 994); `src/services/admission.rs` (a business's bid for
  a service takes its limit); `src/valuation/close.rs` (`CostClose::funded_wage`);
  `contracts/material_circuit_v4.yaml` line 372 and the digest
- Test: `tests/market_clearing/restocking.rs`

**Interfaces:**
- Consumes: `clear_market`, `Offer`, `MarketTable`, `MarketMoment::Restocking`,
  `CostClose::attendance_members()` (`valuation/close.rs:50`; each row has `site_id`, `unit_id`,
  `attended_hours`, `accrued_wages`).
- Produces:

```rust
impl CostClose {
    /// The wages and the hours this site has funded for the period, for one kind of labor.
    pub(crate) fn funded_wage(&self, site: SiteId, unit: UnitId)
        -> Result<(Currency, u64), MaterialCircuitError>;
}
/// The highest price this business pays for this input (P5). Never under the input's posted price.
pub(crate) fn limit_price(catalog: &MaterialCatalog, state: &MaterialCircuitState, costs: &CostClose,
    buyer: SiteId, good: GoodId, unit: UnitId, quote: Currency)
    -> Result<Currency, MaterialCircuitError>;
```

**Decisions:**
1. `funded_wage` adds every member row of the site and labor unit, working owners included: their
   hours count and their wage is 0. The limit uses this funded average, not the share that a later
   use of hours is charged.
2. The limit of a maker. For each process of the buyer's site that takes the input: `receipts =
   output units per batch x the buyer's own posted price for the output`; `wages = floor(labor hours
   per batch x funded wages / funded hours)` (0 when no hours are funded); `others =` the sum over
   the process's other inputs of `quantity per batch x the lowest posted price among the buyer's own
   suppliers or providers of it` (an input with no priced seller counts 0); `limit = floor((receipts
   - wages - others) / the input's quantity per batch)`. A process whose output the buyer has no
   offer for gives no figure. The buyer's limit is the largest figure over its processes.
3. The limit of a merchant, a site that has an offer for the same product: its own posted price
   less `floor(hours per unit x funded wages / funded hours)`.
4. The result is `max(quote, that figure)`, and the quote when there is no figure. So a buyer with
   no selling price of its own never outbids.
5. `replenish` with a market policy: the policies of the products in the order of paying are taken
   market by market, sorted by `(place, supplier site id)`, the bids of a market by order id. A
   bid's `wanted` is today's `desired`, computed when its market is reached, so that what the buyer
   has just bought from another supplier counts in its position, as today (a business may have
   several suppliers of one product). Its purse is its cash above the policy's floor. The supply is
   `Offer::supply` for the supplier after the first shipping pass. An order row and its reserve are
   made for what was sold, at the market's price. Nothing is ordered from a seller with nothing on
   offer. A product not in the order of paying is ordered by today's rule.
6. The second shipping pass is unchanged. What a route cannot carry waits as an accepted order.
7. Equipment bought as investment (`equipment::invest`) is unchanged.

- [ ] **Step 1: Write the failing tests** in `tests/market_clearing/restocking.rs`:
  - `a_maker_stops_bidding_at_its_cost_price`: two makers want the same short input. One makes a
    product whose batch covers the input up to $245, the other up to $106; the posted price is
    $100. Assert the price paid lies above $106 and at most $245, the second maker gets nothing, and
    neither pays more than its limit.
  - `a_maker_below_its_cost_buys_at_the_posted_price_only`: both makers are below cost at posted
    prices. Assert the price paid is the posted price and they share in proportion.
  - `a_merchant_stops_at_its_own_price_less_handling`.
  - `nothing_is_ordered_from_an_empty_supplier`: assert no order row, no reserve, and one market row
    with `sold_quantity` 0.
  - `goods_sold_and_not_yet_shipped_are_not_sold_twice`: a supplier with 100 in stock owes 70 to an
    accepted order that its route could not carry. Assert `supply` is 30.
  - `a_second_supplier_sees_what_the_first_sold`: one buyer with two suppliers of one product.
    Assert its bid at the second is its target less what it holds, has inbound and has just bought.
  - `the_limit_reads_the_sites_own_funded_wage`: pin one `limit_price` by hand from a fixture's
    recipe, prices and funded hours, with one working owner among the members.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the binary, `binary(recurring_circuit)`, the crate, then `-p babylon-tick`.
- [ ] **Step 5: Commit** `feat(material-circuit): businesses bid for stock up to their cost price`.

### Task 6: The seller plans from what was wanted

**Files:**
- Modify: `src/recurring/firms.rs` (`plan_production`, `handling_quantities`);
  `src/recurring/prices.rs` (`update_prices`); `src/services/market.rs` (`update`, `quote`);
  `src/services/model.rs` (`ServicePriceDecision::PricedOut = 6`, valid when `admitted ==
  performed` and `next_price >= old_price`); `src/transition/state.rs` (`next_plans` and
  `ServiceClose::plan` receive the table); `contracts/material_circuit_v4.yaml` line 767 and the
  digest; `rust/crates/babylon-tick/src/material_world/service_receipt.rs` (the decoder at 216 to
  223 accepts reason 6); `contracts/committed_material_tick_v3.yaml` (`service_price_decision_tag`
  at 536 gains `priced_out: 6`) and its pinned digest
- Test: `tests/market_clearing/plans.rs`; the tick's `tests/service_receipt_wire.rs`

**Decisions:**
1. For goods, `priced_out = MarketTable::priced_out(seller, product)`. `plan_production` adds it to
   `waiting`. `update_prices` adds it to the unserved quantity it reads, so the posted price steps
   up when stock is at or under its target. `handling_quantities` adds it for a merchant.
2. For services nothing is added to the plan: a service is already planned from what was asked
   (`services/market.rs:117-131`).
3. A service market with a row of the period takes the reason `PricedOut`. `quote` decides it
   before `CostPressure` and `SpareCapacity`, and its posted price steps up as `FundedUnmet` does.
4. Without a market policy there are no rows and every figure is today's.

- [ ] **Step 1: Write the failing tests**: `a_priced_out_buyer_raises_next_periods_plan` (the plan
  receipt's `unshipped_quantity` includes the priced-out quantity and `planned_batches` covers it);
  `the_posted_price_steps_up_after_buyers_are_priced_out` (goods: reason `UnservedDemand`; services:
  reason `PricedOut`, also when the provider has spare capacity; each one step up, inside its
  bounds); `a_run_of_three_periods_closes_the_gap` (a seller with spare capacity and a short first
  period: the price paid falls back to the posted price by the third period); in the tick, a market
  receipt with reason 6 round-trips.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the binary, the crate, `-p babylon-tick`, `-p babylon-persistence`.
- [ ] **Step 5: Commit** `feat(material-circuit): plan next period from what buyers wanted`.

The lead then runs the whole gate.

### Task 7: The market's receipt reaches the stored records

Follow commit `564bd4560`, which added the household lifecycle's two receipt families.

**Files:**
- Create: `rust/crates/babylon-tick/src/material_world/clearing_receipt.rs`
- Modify, engine: `rust/crates/babylon-material-circuit/src/wire/` (the receipt's canonical bytes);
  `src/model.rs` or `src/clearing.rs` (`MAX_MARKET_CLEARINGS_PER_PERIOD`)
- Modify, tick: `src/material_world.rs` (module and re-export); `material_world/receipt_format.rs`
  (`MaterialReceiptFormat::MarketClearing`, version 23, domain
  `b"babylon.material-tick-receipts.v23\0"`, the lifecycle widths plus one family, the `identify`
  list at 68, the maximum bytes); `material_world/register.rs` (encode; decode; `receipt_families`
  at 1906 to 1950; `receipt_row_limit` at 1649; the choice of format at 1872 to 1876; every test of
  `format == MaterialReceiptFormat::HouseholdLifecycle`, at 2329, 2592 and on the encode side, also
  accepts the new format, because it selects the staffing row decoder); `MaterialTickReceipts` gains
  the field, in the 21 places that build it (`rg 'MaterialTickReceipts \{'`)
- Modify, persistence: `src/receipt_storage/storage.rs` (a domain `BabylonReceiptStorageV6\0` in
  `storage_domain`, `storage_budget` and `decode_header`; `unpack_row` near 184 is written for the
  lifecycle widths); `src/receipt_storage/layout.rs` (`FIELDS_42`: site at 9, good at 41, unit at
  73, in `fields(tag)`); `src/test_support.rs`; `tests/sql_material_bounds.rs` (a budget test for
  the new format against `MAX_STORED_MATERIAL_RECEIPT_BYTES`); and the stored records' own checks
  of a price, which must take a cleared market's price as the expected one:
  `src/production_projection/lifecycle/period.rs` at 175 (household demand) and 288 (procurement),
  `src/production_projection/lifecycle/services.rs` at 104 (service orders), and
  `src/production_projection/prices/projection.rs` at 86 with `prices/flows.rs` 128 to 160 (the
  unserved quantity now includes what the period's market rows record as priced out)
- Modify, contracts and tools: `contracts/material_world_register_v7.yaml`,
  `contracts/committed_material_tick_v3.yaml` (the family list and `storage_domains`, 603 to 638),
  `contracts/nominal_material_world_v3.yaml`, `contracts/material_circuit_v4.yaml`, with their
  pinned digests; `tools/devtools/national_storage_qualification.py` (the pinned `{3: 37, 4: 39, 5:
  41}` at 354 and the domains at 393 to 399) with
  `tests/unit/tools/test_national_storage_qualification.py`;
  `tools/devtools/national_storage_snapshot.py` (the domain list at 133)
- Test: `rust/crates/babylon-tick/tests/` beside `service_receipt_wire.rs`; persistence's projection
  tests

**Decisions:**
1. A row is fixed width: period `u64`, moment `u8`, three 32-byte ids, two `i128` prices, three
   `u64` quantities, two `u32` counts. 169 bytes before the register's own framing.
2. The format is chosen from the catalog, before the lifecycle check: a catalog with a market policy
   uses format 23 in every period, with or without rows. Format 23 accepts empty lifecycle families
   when the state has no lifecycle book.
3. A register in an earlier format decodes as today, with no market rows. A transition with market
   rows and a catalog with no market policy is refused.
4. A stored record's check of a price accepts, for a market that has a row in the period, that
   row's `clearing_price`; for any other market it expects the posted price, as today. All orders of
   one market in one period carry one price.

- [ ] **Step 1: Write the failing tests**: a round trip of two rows through the register; a register
  of format 22 still decodes to its pinned bytes; a truncated and an over-long family are refused;
  the stored form round-trips through `receipt_storage`; a projection accepts a period with a
  cleared market and still refuses a price that no market row explains.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement,** and remove Task 3's refusal.
- [ ] **Step 4: Run** `-p babylon-tick`, `-p babylon-persistence`, and `mise run test:q --
  tests/unit/tools/test_national_storage_qualification.py`.
- [ ] **Step 5: Commit** `feat(tick): carry the market's receipt in the register`.

### Task 8: The national world asks for it

**Files:**
- Modify: `rust/crates/babylon-persistence/src/national_economy/policy/{admission.rs, game.rs}`
  (`[markets]` gains an optional `paying_order`); `economic_catalog/{capture.rs, codec.rs,
  preset.rs, compile.rs}` (the compiler name `national-world-v13` when the policy has an order of
  paying; the catalog's `market_clearing` from it); `content/scenarios/national/defines.toml`;
  `contracts/economic_catalog_v1.yaml`
- Test: `rust/crates/babylon-persistence/tests/national_household_units.rs` and its support
  (`economy_health.rs`); the tests that pin the shipped compiler's name and bytes

**Decisions:**
1. `paying_order = ["food", "materials", "utility", "housing", "household_services",
   "business_services", "resources"]`. The policy refuses: an unknown product; a product twice; a
   storable need of households after a service or left out; `utility` after a local service; a
   product with no price.
2. A policy without the key compiles as it does today, under its present name.
3. The shipped file takes the key in the commit that makes the repair of PER-370 permanent, so the
   shipped world changes its compiler name once.
4. The health record gains, for each product and period: the lowest and highest price paid, the
   number of short markets, what was wanted at the posted price and what was sold, and the largest
   ratio of price paid to posted price with its county.

- [ ] **Step 1: Write the failing tests**: `a_policy_without_an_order_of_paying_keeps_its_compiler`;
  `an_order_of_paying_is_refused_when_wrong` (five refusals); `the_shipped_world_clears_by_price`
  (its catalog's `market_clearing` holds the seven products in order); and, in the health record's
  cheap test, that the opening has no market rows.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the binary, then `-p babylon-persistence`.
- [ ] **Step 5: Commit** `feat(economy): the national world clears a short market by price`.

### Task 9: Measure it, and keep it measured

Run by the lead.

- [ ] Record the health record for 34 periods on the shipped world and commit it with a README table:
  for each need, the share of households' requirement met, the price paid against the posted price
  at periods 1, 2, 3, 5, 13 and 34, and the counties with the highest price paid.
- [ ] Add the standing test: on the shipped world, for 34 periods, every market row validates, money
  is conserved, no household account pays more than its cash, and no business pays above its limit.
- [ ] Play Wayne for 12 periods in the real client on PostgreSQL and read the County Review. Read
  the organizer's preview of a purchase (`organizer_runtime/material_preview.rs:363`) and the relief
  unit's value (`national_economy/county_review.rs:206`): both still show the posted price.
- [ ] Run `mise run rust:check-no-docs` and `mise run check`.
- [ ] Report to the Director: what the price did to who goes without, by band; where prices rose
  most; what sellers earned from it; the six consequences of the design's section 9, measured; and
  the two figures that still read the posted price, to rule on.
