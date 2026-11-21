# Plans from Spare Money (rule A6) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** A workplace that holds more money than one period of what it pays out plans for what was asked of it,
not only for what was paid for, as far as its spare money carries. One without spare money plans as today.

**Architecture:** One step inside today's planning of hours (`recurring/firms.rs` `plan_attendance`), after
goods and services have made their paid-for plans. It reads what was asked and not paid for from receipts the
close already holds, raises each workplace's planned batches (makers of goods and services) or handling hours
(merchants) as far as its spare money pays, and lets today's planning turn batches into hours, capped as today
by nameplate and inputs. A market policy asks for it with one flag. A catalog that does not ask runs today's
code and keeps every byte.

**Tech Stack:** Rust (`babylon-material-circuit`); `contracts/material_circuit_v4.yaml`.

**Spec:** `docs/superpowers/specs/2026-11-21-how-the-economy-adjusts-design.md`, rule A6 and sections 6 and 8;
`ai/decisions/ADR314_how_the_economy_adjusts.yaml`. Measurement (rule "f"):
`reports/economy-repair-2026-11-20/restoring-forces/round-1.md` to `round-4.md`. The prototype of the rounds is
a scratch file of the measurement. The lead hands its path to the implementer. It shows where the rule sits and
what it computes; it is not the code to ship.

**Stored format: not stopped.** The rule adds no state field, no receipt, no receipt field and no register
change. The prototype's `reserve_plans` receipt is not built. The one byte change is the catalog's own: a
catalog whose market policy asks writes catalog version 8 before the bytes it writes today. That is how ADR312
(version 6) and the tiers (version 7) were asked for, and the catalog digest that travels with every state
must commit to a rule that changes behaviour. The state frame, its versions and every receipt are untouched.

**Where the built rule departs from the prototype.** Three places, each on purpose. So the built rule's
figures are its own, and Task 4 measures them.

1. Hours go through today's planning. The prototype added hours beside it and so paid idle hours past
   nameplate.
2. A merchant's restocking counts in what it pays out, as the design's words say. The prototype left it out.
   By the prototype's definition the shop held $1,000 of "spare" money at the opening, and that money is its
   restocking.
3. A raise stops at nameplate, and takes no stocked input that a paid-for plan needs. A6 is about not cutting.
   Growing is the business of other rules.

## Global Constraints

- Work only in `/media/user/dev-ssd/worktrees/households-homes/babylon`, branch `codex/households-and-homes`.
  Start every shell command with `cd` to it (or to its `rust/`). Never push. No `.env`, no `uv.lock`.
- One cargo process at a time on the whole machine. Never pass `-j`. Only `mise exec -- cargo ...` and
  `mise run ...`.
- No pinned value of any existing test changes. No assertion is loosened. The small world's runs
  (`tests/small_world/`) keep every figure. If one must move, stop and tell the lead.
- Money is `i128` millionths of a dollar; quantities are `u64`; arithmetic is checked and a failure is a typed
  error, never a panic or a wrap.
- A contract line that changes is changed with its pinned digest (`MATERIAL_CIRCUIT_SOURCE_SHA256` in
  `src/wire/state.rs`) in the same commit. The digest is the SHA-256 of the file's bytes. One test checks it
  (`tests/weighted_freight.rs`, near line 382). Nothing else in the repository holds it: no state bytes, no
  baseline, no other crate. The contract is linted on commit with a limit of 120 characters a line.
- `babylon-tick` does not accept the engine's market policy yet: it refuses every transition that has market
  clearings or tier records (`babylon-tick/src/material_world/register.rs`, near line 1899). That wiring is
  ADR312's own remaining task. So the rule is reachable from this crate's tests only, and this plan changes
  nothing in `babylon-tick`.
- Every line number is a hint; find each place by its text.
- **Scoped gate, run by every task before its last commit,** one leg at a time: from `rust/`,
  `mise exec -- cargo fmt --all -- --check`; `mise exec -- cargo clippy --workspace --all-targets --locked --
  -D warnings -D clippy::cognitive_complexity`; `mise run rust:test:q -- -p babylon-material-circuit`;
  `mise run rust:test:q -- -p babylon-tick`; `mise run check:bsl-sentinels`.
- Commit: `git add <files>`; message in a file; `PYTHONPATH=src mise exec -- git commit -q -F <file>`; then
  check `git log --oneline -1`. The body ends with `Part of PER-371` and a `Co-Authored-By` line naming the
  model that wrote the commit.
- No share and no environment variable: the rule plans for all of what was asked (round 3: the whole share is
  best, a quarter fails). Functions stay under 100 lines and a cognitive complexity of 25 (`rust/clippy.toml`).

## Review Focus

1. **The quiet world moves.** At the opening every workplace holds exactly one period of what it pays out:
   the utility $1,200 − 120 × $10; the farm $880 − (400 + 4 × 10 × $12); the clinic $880 − (400 + 40 × $12);
   the shop $1,400 − (40 × $10 + 40 × $25), its restocking counted. And in a quiet world nothing is asked and
   left unpaid, so `extend` returns at its first step. A test of `>=` instead of `>`, a merchant's outlay
   without its restocking, or a gap that counts something paid for would move it. Pinned by Task 3,
   `asking_changes_nothing_in_a_quiet_world`, and Task 2, `the_outlay_of_the_opening_shop_is_its_cash`.
2. **Money is created.** The rule only changes a plan; wages are still paid only as far as cash allows
   (`payments/attendance.rs`). The harness already refuses a period in which money is not conserved
   (`run_staffed` in `tests/small_world/support.rs`, near line 1435), so every asking run of Tasks 3 and 4
   pins it.
3. **What was paid for is planned twice.** Goods priced out at the market are already in today's plan
   (`unshipped_quantities`); a service planned above its asking has nothing unpaid. Pinned by Task 2,
   `priced_out_is_not_counted_twice` and `a_service_planned_above_its_asking_has_nothing_unpaid`.
4. **A receipt changes.** The receipts keep the paid-for plan; only the state carries the extension. Nothing
   compares the two: next period's commitments and staffing are read from the state. Pinned by Task 3,
   `the_receipts_keep_the_paid_for_plan`.
5. **A raise takes from a paid-for plan, or grows the workplace.** Extra batches become hours only through
   today's planning. Where a stocked input is short, that planning shares it in proportion to what each
   process asks (`src/production.rs`, `proportional_floor`), so a raised process would take input from one
   that was not raised. And equipment investment reads the state's planned batches at the next close
   (`src/equipment/investment.rs`, `src/equipment/choice.rs`), so a plan raised above nameplate would buy
   machines with money outside the spare-money check. Both are closed by the two bounds of Task 3's order.
   Pinned by Task 2, `a_stocked_input_leaves_room_only_beyond_the_paid_for_plans`, and Task 3,
   `a_raise_stops_at_nameplate`. The wiring of the input bound is checked by the reviewer's reading unless
   Task 3's optional test can be built.

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `rust/crates/babylon-material-circuit/src/clearing/rule.rs` | `MarketClearingPolicy.plans_from_spare_money` | 1 |
| `rust/crates/babylon-material-circuit/src/wire/catalog.rs` | Catalog version 8 | 1 |
| `contracts/material_circuit_v4.yaml` | The catalog version line and rule A6 | 1 |
| `rust/crates/babylon-material-circuit/src/recurring/spare_money.rs` | What was unpaid, the outlay, the extension | 2, 3 |
| `rust/crates/babylon-material-circuit/src/recurring/firms.rs` | `Wanted` widened; `plan_attendance` calls the rule | 3 |
| `rust/crates/babylon-material-circuit/src/transition/state.rs` | Builds the widened `Wanted` | 3 |
| `rust/crates/babylon-material-circuit/tests/small_world/spare_money.rs` | The small world asking for the rule | 3, 4 |
| `rust/crates/babylon-material-circuit/tests/small_world/support.rs` | The switch (Task 3); a run of any length (Task 4) | 3, 4 |
| `reports/economy-repair-2026-11-20/small-world.md` | The record of the runs | 4 |

---

### Task 1: The market policy asks for the rule

**Files:**
- Modify: `src/clearing/rule.rs` (the field); `src/wire/catalog.rs` (`bytes`); `src/catalog.rs` (tests);
  `contracts/material_circuit_v4.yaml` and the digest in `src/wire/state.rs`.
- Modify: every hand-built `MarketClearingPolicy` gets `plans_from_spare_money: false`
  (`rg -n 'MarketClearingPolicy \{' rust/crates` lists 13, all in this crate; the small world's is in
  `tests/small_world/support.rs`, near line 405). Task 3 adds the small world's switch; here every literal is
  `false`.

**Interfaces:**

```rust
// src/clearing/rule.rs, MarketClearingPolicy gains:
/// Rule A6 (ADR314): a workplace with more money than one period of what it pays out plans for
/// what was asked of it, as far as that money carries. `false` keeps today's plans and bytes.
pub plans_from_spare_money: bool,
// src/wire/catalog.rs
/// A market policy that plans from spare money writes this version first, then every byte the same
/// catalog writes without it.
const SPARE_MONEY_CATALOG_SCHEMA_VERSION: u16 = 8;
```

**Decisions:**
1. The flag lives in the market policy: without a policy a service already plans for what was asked
   (`services/market.rs` `planned_quantity`), so A6 only has work where plans follow what was paid for.
2. Bytes: `false` writes today's bytes. `true` writes `8_u16` right after the domain and terminator, then the
   bytes the same catalog writes with the flag off (6 or 7, the base version, the body, the tails). One prefix,
   as 6 is a prefix before the base version today. Nothing decodes catalog bytes or switches on their version:
   their only readers take the digest.
3. Admission refuses nothing new: any market policy may ask.
4. Contract: `catalog_version` (near line 74) gains "a market policy that plans from spare money writes 8
   first, then the bytes the same catalog writes without it"; the tail comments (near line 126) say the same in
   their style; the `market_clearing` section (from line 151) gains `A6_spare_money`, stating Task 3's rule in
   the contract's style; and `P13_asking` (near line 190) gains "and A6 only by setting
   plans_from_spare_money".
5. No scenario key now. The shipped scenarios ask for no market policy yet (`babylon-persistence/src/
   economic_catalog/compile.rs` builds `market_clearing: None`); the flag is read where ADR312's remaining
   task will read the policy.
6. If the prefix takes `bytes` over a limit, move the choice of the leading version into a helper of its own.

- [ ] **Step 1: Write the failing tests** in `src/catalog.rs`'s tests:
  `spare_money_writes_version_eight_before_the_bytes_without_it` (with `policy(&[1, 2])` asking: bytes at
  `head..head + 2` are `8_u16`, and `bytes[head + 2..]` equals the bytes of the same catalog not asking from
  `head`); `spare_money_changes_the_digest` (with and without wants: each digest differs from its twin's).
  `a_catalog_without_a_market_policy_keeps_its_digest`, `a_market_policy_without_wants_keeps_its_digest` and
  `wants_write_version_seven_and_change_the_digest` pass unchanged.
- [ ] **Step 2: Run them and see them fail.** `mise run rust:test:q -- -p babylon-material-circuit -E
  'test(spare_money)'`. Expected: does not compile, no field `plans_from_spare_money`.
- [ ] **Step 3: Implement** the field, the constant, the prefix in `bytes`, the 13 literals, the contract and
  its digest.
- [ ] **Step 4: Run** `mise run rust:test:q -- -p babylon-material-circuit`. Expected: all pass, no pinned
  value changed.
- [ ] **Run the gate. Commit** `feat(material-circuit): let a market policy ask for plans from spare money`.

### Task 2: The arithmetic

**Files:**
- Create: `src/recurring/spare_money.rs` (`pub(crate) mod spare_money;` in `src/recurring.rs`), with its
  `#[cfg(test)] mod tests`.

**Interfaces:**

```rust
// The key type exists already as a private alias in recurring/firms.rs and recurring/prices.rs:
// (SiteId, GoodId, UnitId). Make ONE of them pub(crate) and use it here; do not define a third.

/// What was asked of each seller and not paid for at its posted price, by seller and product, rows
/// above 0 only: a service's requested quantity above its paid-for plan; a goods seller's restock
/// orders and household requests not admitted, less what its buyers were priced out of.
pub(crate) fn unpaid_asking(
    services: &[ServiceMarketReceipt],
    procurement: &[ProcurementReceipt],
    demand: &[HouseholdDemandReceipt],
    priced_out: impl Fn(StockKey) -> u64,
) -> Result<BTreeMap<StockKey, u64>, MaterialCircuitError>;

/// One period of what a site pays out: each (hours, wage) of its planned hours, each (batches,
/// inputs of one batch) of its planned processes, and each (units, price) of a merchant's
/// restocking. `Ok(None)` when a positive quantity has no price.
pub(crate) fn outlay(
    hours: &[(u64, Option<i128>)],
    batches: &[(u64, Option<i128>)],
    restock: &[(u64, Option<i128>)],
) -> Result<Option<i128>, MaterialCircuitError>;

/// How many of `asked` (batches or units) `spare` pays for at `per` each: 0 when `spare <= 0` or
/// nothing is asked; all of it when `per == 0`; else `min(asked, spare / per)`.
pub(crate) fn affordable(asked: u64, per: i128, spare: i128) -> Result<u64, MaterialCircuitError>;

/// How many more batches a stocked input leaves room for, once the site's paid-for plans have
/// what they ask: `(available - paid_for) / per_batch`, 0 when they already ask for all of it.
pub(crate) fn input_room(available: u64, paid_for: u128, per_batch: u64) -> Result<u64, MaterialCircuitError>;
```

**Decisions** (what the prototype computes, checked against the code, and where the plan departs from it):
1. **What was asked.** Services: `ServiceMarketReceipt.requested_quantity` less `planned_quantity`, the
   receipt `services/market.rs` `update` fills. Goods: at the supplier, `ProcurementReceipt.desired_quantity`
   less `admitted_quantity`; at the retailer, `HouseholdDemandReceipt.requested_quantity` less
   `admitted_quantity`; the sum at each key less `MarketTable::priced_out` at that key, which
   `unshipped_quantities` already plans for.
2. Every subtraction there saturates at 0, as the prototype's: a plan above its asking (owed or future orders)
   or priced-out want rungs above a need's gap mean nothing unpaid, not a fault. Sums are `checked_add`,
   `Arithmetic` on overflow.
3. **Outlay** sums `i128::from(q) * price` with `checked_mul` and `checked_add` (`Arithmetic`). A quantity of
   0 needs no price.
4. `affordable` computes `min(i128::from(asked), spare / per)` in `i128` before the cast, so a deep purse is
   never refused; `per < 0` is `Err(MonetaryInvariant)`.
5. `input_room` saturates at 0 when `paid_for >= available`; `per_batch == 0` is `Err(Arithmetic)`; the
   quotient is cast with `try_from` (`Arithmetic`).
6. Nothing calls these functions until Task 3, and the lint leg refuses dead code. Mark the four functions with
   `#[cfg_attr(not(test), allow(dead_code, reason = "Task 3 calls them from extend"))]` (the precedent is in
   `src/clearing/table.rs`, near line 206). Task 3 removes the attribute.

- [ ] **Step 1: Write the failing tests** (money in millionths):
  - `no_spare_money_plans_nothing_more`: `affordable(10, 23_000_000, 0)` and `(10, 23_000_000, -40_000_000)`
    are 0.
  - `spare_money_carries_part_of_what_was_asked`: `affordable(4, 23_000_000, 52_000_000) == 2` (the clinic at
    $11 with power at $12, $52 spare).
  - `spare_money_carries_all_that_was_asked`: `affordable(3, 23_000_000, 1_000_000_000) == 3`.
  - `a_workplace_asked_nothing_plans_nothing_more`: `affordable(0, 23_000_000, 10^12) == 0`, and
    `unpaid_asking` of receipts whose asking equals their plan or admission is empty.
  - `a_free_batch_is_planned_in_full`: `affordable(7, 0, 1) == 7`.
  - `the_largest_values_do_not_overflow`: `affordable(u64::MAX, 1, i128::MAX) == u64::MAX`;
    `affordable(u64::MAX, i128::MAX, i128::MAX) == 1`; `affordable(5, -1, 10)` is `Err(MonetaryInvariant)`;
    `outlay(&[(u64::MAX, Some(i128::MAX))], &[], &[])` is `Err(Arithmetic)`.
  - `the_outlay_of_the_opening_clinic_is_its_cash`: `outlay(&[(40, Some(10_000_000))], &[(40,
    Some(12_000_000))], &[]) == Ok(Some(880_000_000))`; with a wage of `None` on 40 hours it is `Ok(None)`; on
    0 hours, `Ok(Some(480_000_000))`.
  - `the_outlay_of_the_opening_shop_is_its_cash`: `outlay(&[(40, Some(10_000_000))], &[], &[(40,
    Some(25_000_000))]) == Ok(Some(1_400_000_000))`; with a restock price of `None` on 40 units it is
    `Ok(None)`.
  - `a_service_asked_above_its_paid_plan_is_unpaid_for_the_difference`: requested 40, planned 36 gives 4 at
    the provider's key.
  - `a_service_planned_above_its_asking_has_nothing_unpaid`: requested 36, planned 40 gives no row.
  - `restock_and_household_asking_add_at_their_sellers`: a restock row shop from farm, desired 40, admitted
    30, gives 10 at the farm; a household row at the shop, requested 40, admitted 35, with `priced_out` 3 at
    the shop, gives 2 at the shop.
  - `priced_out_is_not_counted_twice`: a household gap of 5 with `priced_out` 9 gives no row.
  - `a_stocked_input_leaves_room_only_beyond_the_paid_for_plans`: `input_room(100, 100, 5) == 0`;
    `input_room(100, 120, 5) == 0`; `input_room(100, 60, 5) == 8`; `input_room(100, 60, 0)` is
    `Err(Arithmetic)`.
- [ ] **Step 2: Run them and see them fail.** `mise run rust:test:q -- -p babylon-material-circuit -E
  'test(spare_money)'`. Expected: does not compile, `affordable` not found.
- [ ] **Step 3: Implement** the four functions. They are pure; nothing calls them yet.
- [ ] **Step 4: Run them and see them pass.**
- [ ] **Run the gate. Commit** `feat(material-circuit): the arithmetic of plans from spare money`.

### Task 3: A workplace with spare money plans for what was asked

**Files:**
- Modify: `src/recurring/spare_money.rs` (`extend` and its parts; the `dead_code` attributes of Task 2 go);
  `src/recurring/firms.rs` (`Wanted` near 492, its two destructurings near 503 and 632, `plan_attendance`
  near 690); `src/transition/state.rs` (the `Wanted` built in `close_material_period_with_portfolios`, near
  1684).
- Modify: `tests/small_world/support.rs` (`World.spare_money`, `with_spare_money`, the policy literal);
  `tests/small_world.rs` (`mod spare_money`).
- Create: `tests/small_world/spare_money.rs`.

**Interfaces:**

```rust
// src/recurring/firms.rs, Wanted gains:
/// The period's service markets: what each provider was asked and planned (rule A6).
pub(crate) services: &'a [ServiceMarketReceipt],
/// The period's restocking decisions (rule A6).
pub(crate) procurement: &'a [ProcurementReceipt],
/// Today's hours: production through `derive_shared_labor_requests`, equipment work, merchant handling
/// and maintenance. The body of `plan_attendance` before `install_attendance_plans`, moved.
fn planned_hours(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    wanted: Wanted<'_>,
    dispatches: &[RoutedDispatchReceipt],
    sold: (&[LocalTransferReceipt], &[LocalRetailFulfillmentReceipt]),
    maintenance: Option<&MaintenanceReceipt>,
    next_period: u64,
) -> Result<BTreeMap<(SiteId, UnitId), u64>, MaterialCircuitError>;

// src/recurring/spare_money.rs
/// What the rule added at one close.
pub(crate) struct Extension {
    /// Some process's planned batches were raised, so its hours must be planned again.
    pub(crate) raised_batches: bool,
    /// Extra handling hours of merchants, by site and labor unit.
    pub(crate) handling: BTreeMap<(SiteId, UnitId), u64>,
}
/// Rule A6 at the close, after the paid-for plans of goods and services and before hours are
/// installed. Raises `planned_batches` in the state's recurring production; writes no receipt.
pub(crate) fn extend(
    catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState,
    hours: &BTreeMap<(SiteId, UnitId), u64>,
    wanted: Wanted<'_>,
    next_period: u64,
) -> Result<Extension, MaterialCircuitError>;
// tests/small_world/support.rs
/// Rule A6 on the market policy; sets `market` too.
pub(crate) fn with_spare_money(mut self) -> Self;
```

`extend` does not fit the limits as one function. Split it along these lines, each a private function of
`spare_money.rs`: `wages(economy)`, `input_prices(recurring)`, `batch_inputs(catalog, prices, process)`,
`extend_site(..)`, `raise_maker(..)`, `raise_merchant(..)`.

**The order of `extend`** (the signature does not determine it):
1. `unpaid_asking` from `wanted`. Empty: return at once, nothing touched.
2. A wage for each (site, labor unit): the largest `LaborCompensation::Wage` rate of `economy.employment` for
   it. A price for each (good, unit) of an input: the largest posted `unit_price` of `recurring.offers` for it,
   as the offers stand when `extend` runs. A service's offer is already the coming period's then
   (`services.plan` sets it); a good's is still this period's (prices of goods are updated after).
3. For each site with unpaid asking, in site order, its `outlay`:
   - its rows of `hours` at their wage;
   - its `recurring.production` rows' `planned_batches` at the price of one batch's `input_coefficients` (a
     plan already above nameplate overstates this, which errs on the side of not extending);
   - for each of this close's `wanted.procurement` rows whose `buyer_site_id` is the site and whose good the
     site handles as a merchant (`handling_coefficients`), `desired_quantity` at that supplier's own posted
     price, the offer of `(supplier_site_id, good_id, unit_id)`. A maker's stocked inputs are not counted
     here: they are in its batches already.

   An unpriced site is skipped. `spare = book.cash(Site) - outlay` (`checked_sub`); `spare <= 0` skips it.
4. Its unpaid products in key order, while `spare > 0`:
   - A product it makes (`process_outputs`): `per` = labor `quantity_per_batch` x wage + one batch's inputs.
     The extra batches are the least of three figures: `affordable(gap.div_ceil(quantity_per_batch), per,
     spare)`; the room under nameplate, `capacity::process_available(catalog, state, process, site,
     next_period)` less `planned_batches`, saturating at 0; and, for every stocked input of the process,
     `input_room(available, paid_for, quantity_per_batch)`, where `available` is what today's allocation
     reads (`production_resource_available`) and `paid_for` is what the site's processes ask of that input at
     their plans as they stand before any raise at this site (the loop over `requests` in
     `src/production.rs`, near line 360). Then `planned_batches += batches` (`checked_add`),
     `spare -= batches x per`, and the inputs a raise will use come off the room left for the site's later
     products.
   - Else a product it handles (`merchants`, `handling_coefficients`): `per` = `hours_per_unit` x the wage of
     the merchant's labor unit; `units = affordable(gap, per, spare)`; `handling += units x hours_per_unit`;
     `spare -= units x per`.
   - Else, or with no wage for the hours or no price for an input, the product is skipped.
5. `plan_attendance`: `hours = planned_hours(..)`; when the policy asks, `extend`; when `raised_batches`,
   `hours = planned_hours(..)` again; add `handling` with `add_hours`; then `install_attendance_plans` as
   today. A catalog that does not ask never calls `extend`.

**Decisions:**
1. **One place for both kinds.** Services set `planned_batches` in `services.plan` before `next_plans`, goods
   in `plan_production` inside it; both are set before `plan_attendance` runs, so one step covers makers of
   goods, services and merchants, as the prototype did.
2. **Hours through today's planning.** Raised batches are planned again by `derive_shared_labor_requests`,
   which caps them at nameplate and inputs on hand (service inputs are counted from the plan,
   `planning_grants`), as for any plan. Merchant hours are not capped today, nor here.
3. **Spare money** is cash at the close, after taxes and payouts, less one period of what the site pays out:
   wages of its planned hours, inputs of its planned batches, and a merchant's restocking. Restocking is
   valued at what it asked for at this close (`desired_quantity`), which is what it sold and must buy back.
   Largest wage and largest posted input price: a bound that never understates the cost.
4. **No receipt changes.** `ProductionPlanReceipt` and `ServiceMarketReceipt` keep the paid-for plan; only
   the state's `planned_batches` and attendance plans carry the extension. The records of A6 come with rule
   A23.
5. **A raise never grows the workplace and never starves a paid-for plan.** The nameplate bound keeps
   equipment investment, which reads the state's planned batches at the next close, from buying machines on a
   plan that only holds on. The input bound keeps a raised process from taking a stocked input that today's
   proportional sharing would otherwise take from a process that was not raised.
6. `extend` reads `book.cash`, which only payments change: no money moves here.
7. Both destructurings of `Wanted` in `firms.rs` (`let Wanted { demand, markets } = wanted;`) take `..`.

- [ ] **Step 1: Write the failing tests** in `tests/small_world/spare_money.rs`:
  - `asking_changes_nothing_in_a_quiet_world`: for `World::plain().with_market()`, `World::plain()
    .with_tiers()` and `World::benefits().with_tiers()`, each with `.with_spare_money()`:
    `support::assert_still_rows` passes, and its rows equal, field for field, those of the same world not
    asking.
  - `spare_money_extends_a_plan_under_the_pay_rise`: `support::run_observed` on
    `World::higher_pay().with_tiers().with_spare_money()`; in some period some provider's `planned_batches`
    in the state exceeds that period's `ServiceMarketReceipt.planned_quantity` for it (one unit a batch). Not
    asking, never. Pin the first such period and its site.
  - `the_receipts_keep_the_paid_for_plan`: in the asking runs of P4 with tiers and of
    `World::benefits().with_tiers().pushed(Push::LowerFundTaxes)`, every `ProductionPlanReceipt` has
    `planned_batches <= dispatched + unshipped + buffer - closing stock`, 0 exactly when that is 0; period 1's
    `production_plans` and `service_markets` equal the same world's not asking.
  - `the_extension_asks_no_hours_beyond_nameplate`: in those two runs the hours asked of the utility and the
    clinic (`Snapshot.asked`) never exceed their market receipt's `available_capacity` (one hour a batch).
  - `a_raise_stops_at_nameplate`: in those two runs, for every period and provider, the state's
    `planned_batches` is at most the larger of that period's `ServiceMarketReceipt.planned_quantity` and its
    `available_capacity`.
- [ ] **Step 2: Run them and see them fail.** `mise run rust:test:q -- -p babylon-material-circuit -E
  'binary(small_world)'`. Expected: does not compile, no `with_spare_money`; after the builder alone,
  `spare_money_extends_a_plan_under_the_pay_rise` fails.
- [ ] **Step 3: Implement** `Wanted`'s two fields, `planned_hours`, `extend` and its parts, and the call. Run
  once, read the first period and site of the extension from the run, and pin them.
- [ ] **Step 4: The input bound.** No world in this crate's tests has two processes that share a stocked
  input under a market policy. If you can build one from an existing fixture in under 60 lines, add
  `a_raise_leaves_a_paid_for_plan_its_inputs`: stock covers the paid-for plans exactly, one process is asked
  for more than was paid for, the site holds spare money, and the other process's granted batches at the next
  opening equal those of the same world not asking. If you cannot, say so in your report: the reviewer then
  checks the wiring of `input_room` by reading (Review Focus 5).
- [ ] **Step 5: Run** `mise run rust:test:q -- -p babylon-material-circuit`. Expected: every existing test,
  the small world's `quiet.rs`, `pushed.rs`, `tiers.rs` and `benefits.rs` included, passes unchanged.
- [ ] **Run the gate. Commit** `feat(material-circuit): a workplace with spare money plans for what was asked`.

### Task 4: What the rule does alone, at 34 periods and at 400

**Files:**
- Modify: `tests/small_world/support.rs` (`World.periods`, `for_periods`, the horizon in `build`, the loop of
  `run_staffed`, the row count in `assert_still_rows`); `tests/small_world/spare_money.rs`;
  `tests/small_world/dump.rs`; `reports/economy-repair-2026-11-20/small-world.md` (a section after "Form (b)
  after").

**Interfaces:**

```rust
// tests/small_world/support.rs, World gains:
/// How many periods a run lasts: `PERIODS` unless a test asks for a longer look.
pub periods: u64,
/// The same world, run for `periods` periods. The catalog's horizon follows it.
pub(crate) fn for_periods(mut self, periods: u64) -> Self;
```

**What is known before the task.** Tasks 1 to 3 are built. The first attempt at this task stopped by its own
rule: the tax cut with the rule on was below the same run without it in three periods of its window. The lead
then ran every push once, with and without the rule, for 34 and for 400 periods, on a scratch copy of the
harness. The figures below are that reading. This task's tests are its check: a figure that differs is a
finding to report in your return, and nothing is bent to match the table.

Hours attended, out of 240. "Plain" is `World::plain().with_tiers()` and its pushes; "fund" is
`World::benefits().with_tiers()` and its pushes. Quiet, P1 and P3 stay at 240 in every period of every run.

| Run | Rule | Period 34 | 100 | 200 | 300 | 400 | Unmet at 400 (food, power, care) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| plain P4, the pay rise | no | 179 | 129 | 15 | 15 | 15 | 40, 25, 40 |
| plain P4, the pay rise | yes | 240 | 240 | 240 | 240 | 240 | 0, 0, 3 |
| plain P2, the poor harvest | no | 156 | 116 | 15 | 15 | 15 | 40, 25, 40 |
| plain P2, the poor harvest | yes | 237 | 230 | 237 | 239 | 240 | 6, 10, 10 |
| fund P2, the poor harvest | no | 197 | 177 | 113 | 100 | 80 | 40, 8, 21 |
| fund P2, the poor harvest | yes | 190 | 128 | 120 | 66 | 66 | 40, 16, 22 |
| fund P4, the pay rise | no | 237 | 238 | 122 | 101 | 63 | 40, 6, 29 |
| fund P4, the pay rise | yes | 191 | 174 | 120 | 112 | 70 | 40, 16, 21 |
| fund P5, the tax cut | no | 225 | 183 | 116 | 70 | 58 | 40, 8, 30 |
| fund P5, the tax cut | yes | 234 | 156 | 129 | 19 | 16 | 40, 26, 40 |

In words: without taxes the rule alone turns ruin into a steady economy, for 400 periods, under both lasting
pushes. With taxes and the benefits fund it saves no pushed run: each ends in ruin with the rule and without
it. In the plain pay rise the rule holds 240 hours in every period from 1 to 400. In the tax cut at 34 periods
the rule's hours are below the same run's without it in periods 17, 24, 25 and 26, and above in 23 periods.

**Decisions:**
1. **Full work** is 240 hours attended (the sum of `Snapshot.hours_attended`) in every period from 25 to 34,
   with no site's output 0 in any period.
2. **A run of any length.** `World.periods` defaults to `PERIODS`. `build` uses `self.periods + 2` where it
   uses `PERIODS + 2` today (the catalog's horizon; a run past it stops every maker). `run_staffed` loops to
   `world.periods`. `assert_still_rows` compares the number of rows with `world.periods`. With the default,
   every existing test keeps every figure.
3. **The name says the result.** At 34 periods:
   - `p4_with_tiers_and_spare_money_returns_to_full_work`
     (`World::higher_pay().with_tiers().with_spare_money()`): decision 1 holds, and more: 240 hours in every
     period from 1 to 34. Pins at period 34: `unmet`, `output` and the cash of the four sites and the owner.
     The same world not asking attends fewer than 240 hours at period 34; pin its figure.
   - `p5_on_the_fund_with_tiers_and_spare_money_does_not_return_alone`
     (`World::benefits().with_tiers().pushed(Push::LowerFundTaxes).with_spare_money()`): decision 1 does not
     hold. Pins: the hours at period 34 with the rule and without it; the exact periods in which the rule's
     hours are below the same world's not asking, and the number in which they are above; and at period 34
     `unmet`, `output` and the cash of the four sites, the owner, the fund and the public account.
4. **The long look, at 400 periods** (a run is never judged by 34 periods alone):
   - `asking_changes_nothing_in_a_quiet_world_for_400_periods`: `World::plain().with_tiers()` and
     `World::benefits().with_tiers()`, each `.for_periods(400).with_spare_money()`, pass `assert_still_rows`.
   - `the_pay_rise_holds_full_work_for_400_periods`: the plain pay rise with the rule attends 240 hours in
     every period from 1 to 400; at period 400 `unmet` is pinned and is the owner's alone. Without the rule the
     same world's hours at period 400 are pinned.
   - `the_poor_harvest_holds_most_work_for_400_periods`: the plain poor harvest with the rule never attends
     fewer than 230 hours; at period 400 `unmet` is pinned and is the owner's alone. Without the rule the same
     world's hours at period 400 are pinned.
   - `spare_money_alone_does_not_save_the_fund_world`: for the fund's P2, P4 and P5, with the rule and without
     it, the hours at period 400 are pinned, six figures, and each is below 120.
5. **The record** says all of this plainly, the failure in the fund world first among the findings. No figure
   in it that a dump did not print.

- [ ] **Step 1: The run of any length.** Add `World.periods` and `for_periods` as decision 2 says. Run
  `mise run rust:test:q -- -p babylon-material-circuit -E 'binary(small_world)'`. Expected: every existing
  test passes with its figures unchanged.
- [ ] **Step 2: Run once for the figures.** Add `("spare tiers quiet", ..)`, `("spare tiers P4", ..)`,
  `("spare fund quiet", ..)` and `("spare fund P5", ..)` to `dump_every_run`. Add a second ignored printer,
  `dump_spare_money_long_runs`, that prints, for the plain P2 and P4 and the fund's P2, P4 and P5, with the
  rule and without it, the hours attended and `unmet` at periods 34, 100, 200, 300 and 400, and at period 400
  every account's cash and `unmet_by_account`. Run both: `mise run rust:test:q -- -p babylon-material-circuit
  -E 'test(dump_)' --run-ignored only --no-capture`. Compare with the table above and note every difference.
- [ ] **Step 3: Write the six tests** of decisions 3 and 4 with the figures of Step 2. Run them and see them
  pass.
- [ ] **Step 4: Record** in `small-world.md` a section "Spare money (rule A6)": the four 34-period runs' tables
  from `dump_every_run`, in the columns and periods of "Form (b) after"; the long-run table from
  `dump_spare_money_long_runs`; one line for each pushed run saying whether it meets decision 1 and whether it
  holds to period 400; where the money sits at period 400 in the fund's three runs, with the rule and without
  it; and three lines on what carries the plain runs and what the fund's runs lack, traced to the code as the
  record's other sections are.
- [ ] **Run the gate. Commit** `test(material-circuit): what spare money does alone, at 34 periods and at 400`.

### Task 5: The loose ends of the reviews

**Files:**
- Modify: `contracts/material_circuit_v4.yaml` and its digest in `src/wire/state.rs`; `src/catalog.rs` (one
  test); `src/recurring/prices.rs`; `src/recurring/spare_money.rs`.

**Decisions** (each is a reviewer's note on Tasks 1 to 3 that was left open):
1. In the contract, the sentence Task 1 added to `catalog_version` sits inside a folded scalar and reads as a
   run-on with the sentence before it ("...the wants tail after the market tail A market policy that
   plans..."). End the earlier sentence with a full stop, or join the two with a semicolon and a lower-case
   "a". The file's bytes change, so the pinned digest changes with it in the same commit.
2. `spare_money_writes_version_eight_before_the_bytes_without_it` finds the head of the bytes with a literal
   copy of the catalog's domain string. Use the constant the encoder uses, so the test follows the domain.
3. `recurring/prices.rs` keeps a private alias `StockKey` equal to the one `recurring/firms.rs` now shares.
   Import the shared one and delete the copy.
4. In `spare_money.rs`, `paid_for` and `raise_maker` read a process's nameplate with `unwrap_or(0)`. Every
   process of a site is in that map, so the default cannot be reached, but if it ever were, a missing row
   would silently mean "no room". Return the crate's typed invariant error for a process that is missing from
   its map, the variant the neighbouring planning code uses for the same fault. No test can reach it; the
   reviewer checks it by reading.

- [ ] **Step 1:** Make the four changes. There is no new test: decisions 1 to 3 change no behaviour, and
  decision 4 cannot be reached.
- [ ] **Step 2:** `mise run rust:test:q -- -p babylon-material-circuit`. Expected: all pass; the digest test in
  `tests/weighted_freight.rs` passes with the new digest; no other pinned value moved.
- [ ] **Run the gate. Commit** `chore(material-circuit): close the reviews' loose ends on spare money`.
