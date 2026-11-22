# Plans Through the Chain (rule A5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** At the close each business places its orders for the next period from its new plan, and each service
it buys from plans from those orders; the plans are made again, a bounded number of times, until they rest.

**Architecture:** Today's close is kept as it is. When a market policy asks, one step runs after the makers of
goods have planned (`plan_production`) and before hours are asked for (`plan_attendance`): every business works
out what its new plan needs of each service it buys, as far as its cash pays at the price posted in the period
that closed, and each placed service plans for its households' part, what is owed and those orders. The step is
repeated over all services at once (each pass reads only the pass before) until a pass changes nothing, at most
three times. Nothing is set aside: an order is a figure of the close, paid at the next period's stage as today.

**Tech Stack:** Rust (`babylon-material-circuit`); `contracts/material_circuit_v4.yaml`; the bench's Python
scripts (Task 5 only).

**Spec:** `docs/superpowers/specs/2026-11-21-how-the-economy-adjusts-design.md`, rule A5 and sections 6, 8 and A23;
`ai/decisions/ADR314_how_the_economy_adjusts.yaml`; `ai/decisions/ADR312_the_price_of_a_short_market.yaml` (rule
P14, amended by ADR314: "A supplier plans from the orders its business buyers place at the close"). The measurement
folder is a scratch folder of the measurement rounds, kept outside the repository; the lead hands its path to the
builder of Task 5. Measurement (prototype "D", plans down the chain):
`reports/economy-repair-2026-11-20/restoring-forces/round-4.md` (section "D"), `round-5.md`, `round-6.md` (sections
2, 5, 11). The prototype is the switch `SPIKE_D` on the local branch `spike/r6-A4` (commit f2215184c). It shows
where the rule sits and what it computes; it is not code to ship. The pattern plan is
`docs/superpowers/plans/2026-11-21-adjust-1a-plans-from-spare-money.md` (rule A6).

## The rule, for every kind of workplace

The design's words: "At the close each workplace plans, places its orders for the next period, and its suppliers
take those orders into their own plans. This is repeated a bounded number of times until the plans rest."

| Kind | As a buyer, at the close | As a supplier, at the close |
| --- | --- | --- |
| Maker of goods | For each service it buys (`ServiceInputPolicy`): what its new batches need, capped by the policy, as far as its cash pays. New. Stocked goods: its restocking order, already placed in this close, as today | Plans from the orders it holds, what it sent and its buffer, as today (its business buyers' orders are already in its plan, see below) |
| Service | For each service of an earlier stage it buys: as a maker of goods. New | A product in the order of paying: owed + its households' part of what was payable at its posted price + its business buyers' orders, or what is already funded for the next period if more. New: this is P14 changed for buyers that are businesses. A product outside the order: as today |
| Merchant | Restocking as today. A merchant has no process, so no service need (`input_requirements` reads processes only): it orders no service, as today | Sells to households: unchanged (A5 is for buyers that are businesses). Goods sold to a business: as a maker of goods |

Why goods are already chained. A restocking order is placed inside the close (`replenish`, called from
`dispatch_and_replenish` before the plans), it is for the next period (it ships from the next period's output),
and its supplier counts it when it plans (`unshipped_quantities` adds `ordered - shipped`). So a goods supplier is
never a period behind its business buyers. What differs from the design's words is the size of the order: it
follows the buyer's target stock, not the buyer's new plan. This plan keeps that (see "Where the built rule
departs from the design"), and so no circle through goods can arise.

**The bound and what "rest" means.** A pass computes, for every placed service market, its planned quantity in
whole units from the plans of the pass before. The plans rest when a pass returns, market by market, exactly the
quantities it was given (`BTreeMap<StockKey, u64>` equality). Pass zero is today's P14 plan. The bound is
`CHAIN_PASSES = 3`, one more than the number of service stages (`ServiceStage` has two). Why it suffices: a
service buys only from services of an earlier stage (`services/validation.rs` `validate`, run when a state is
admitted against its catalog, refuses a service input of the same or a later stage), and goods plans and goods
orders are fixed before the step. A buyer's need is read from its processes' recipes (`input_coefficients`), so
summing it by buyer site does not add a path between stages. So the plans of the last stage depend only on goods
and are final after pass one; those of the stage before after pass two; pass three changes nothing. Reaching the
bound without rest cannot happen on an admitted state; it returns `ServiceInvariant`, never a silent plan.
Because each pass reads only the pass before, the order in which markets are visited cannot change the result.

## Where the design goes beyond the prototype

1. **Every workplace.** The prototype changes the services' plans only. Its buyers are any site with a service
   input policy, so makers of goods and services are covered as buyers; on the bench only the utility's plan ever
   moved (the clinic has no business buyers). Goods suppliers and merchants were untouched; the table above says
   what that means for them.
2. **Orders placed for the next period.** The prototype counts a need; it places no order. The built rule does
   the same: an order is a figure of the close, not a funded claim in the state. See departure D1 below.
3. **Repeated until the plans rest.** The prototype makes one pass in a fixed order (local services, then the
   utility). The built rule repeats, bounded, as above. On every admitted catalog both give the same plans.

## Where the built rule departs from the prototype

Each on purpose. None is expected to move any column of the bench's rows; Task 5 checks it.

1. **Passes until rest** (above), not one ordered pass. The design asks for it, and it makes the result
   independent of the visiting order.
2. **One purse.** A buyer's cash at the close pays its orders once, in the order of paying, then by provider; the
   prototype judged each order against the whole purse. The design says "as far as its cash pays". On the bench
   each buyer buys one service, so it cannot differ there.
3. **A free service** (posted price 0) is ordered in full when the purse stands above its floor, through
   `recurring::spare_money::affordable` (which returns 0 for a purse at or under 0 before it looks at the price);
   the prototype divided by the price, and would panic at 0.
4. **Where it runs.** Today's `services.plan` stays where it is, and the chain runs after `plan_production`. The
   prototype moved all of `services.plan` after `plan_production` (and did so even without a market policy).
   The values are the same: `services::market::update` reads service performance, the market table, what is
   owed, service orders and offers, none of which `plan_production` writes; and `plan_production` skips service
   processes and reads goods orders, household demand and the market table, none of which `update` writes (it
   writes service plans and service offers' prices). Kept so that a catalog that does not ask runs today's code.
5. **Asked by the catalog,** with one flag on the market policy, not by an environment variable; the business
   buyers' part of a market is recorded only when the flag is set; its sum is checked, not a bare `.sum()`.
6. **No receipt.** `SpikeDReceipt` and the `flow_d_*` columns are not built. The records of A5 come with A23.
7. **No price-step gain.** The prototype's plan adds `gain`, what buyers could pay for at a lower new price
   (spike e, `SPIKE_E`). Spike e is not built, so the built plan has no such term. It is 0 whenever `SPIKE_E` is
   off, as in the best set, so it cannot move the bench.
8. **The cheapest-seller path is not built.** The prototype also records the business part where A4 groups
   sellers (`services/tiers.rs`, near line 446, under `SPIKE_A4`). A4 is not built; that line is off on the
   bench.

## Where the built rule departs from the design

- **D1. An order is not set aside.** The engine carries orders for a later period and uses none (see the Forward
  orders note in Task 4). They are funded claims: money is set aside at a price when the order is made. Using
  them would set money aside at the close, at the closing period's price, before the next period's wages, and
  before the next period's market finds its price, which ADR312's first call forbids ("The price is found when
  the buyers bid and the supply is known, before money is set aside"). So the order stays a figure of the close
  and is paid at the next period's stage as today. Brought to the lead for the Director.
- **D2. A goods order follows target stock,** not the buyer's new plan. Changing it was never prototyped (section
  8: every piece is a measured prototype first), would re-clear the restocking market of ADR312 at the close, and
  is the only thing that could make plans run in a circle. Brought to the lead for the Director.
- **D3. A buyer orders for the plan it made,** even past what its people or nameplate can work, as the prototype
  did (round four, D's difference 3: the utility then pays idle hours). Kept so that the built rule is the
  measured one.

## Stored format: not stopped

The rule adds no state field, no receipt and no receipt field. A catalog whose market policy asks writes catalog
version 9 right after the domain and terminator, then every byte the same catalog writes without the flag (so a
policy that asks for A5 and A6 writes 9, then 8, then the rest). That is how versions 6, 7 and 8 were asked for,
and the catalog digest that travels with every state must commit to a rule that changes behaviour. When asking,
`ServiceMarketReceipt.planned_quantity` of a placed service carries the rested plan, as the prototype wrote it:
its value changes, not its form. Rule A6 reads that field, so A6 measures unpaid asking against the chained plan,
as it did on the bench. A6's own raise comes after the chain has rested and does not go back into it, as in the
prototype. Shipped scenarios carry no market policy (`babylon-persistence/src/economic_catalog/compile.rs` builds
`market_clearing: None`), so no saved world can ask.

## What the design's section 8 asks of this plan

Section 8 asks every piece's prototype to be measured for 400 periods at both sets of figures before it is planned,
and the rows of the first part to pass its tests. D was: in round four's core at 400 periods (`out/r4-core-400`,
`out/r4-core-nat-400`) and in round six's `two-plain`, `two-core` and `two-no-signal` at 400. The first part's tests
are of the first part as a whole; round six read them (section 11). It asks nothing of a piece alone, and section 7
says no piece works alone. So the pattern plan's Task 4 (A6 alone at 34 and 400 periods) has no counterpart here.
What section 8 does ask of every piece is kept: **still when quiet** (Task 4, at 34 and at 400 periods, with and
without A6) and **exact money** (the harness, `run_staffed` in `tests/small_world/support.rs`, refuses a period
whose total money moved; the bench's `write_run` turns that check off and the rows carry `total_money`). In place of
the pattern plan's Task 4 stands the bench equality (Task 5): the built rule must give the prototype's rows. The
best set was run at 200 periods only (round six, section 10); Task 5 compares at 200, and its script takes the
length as an argument if the lead asks for 400. At 400 only comparisons 2 and 3 can be made (both sides are run
fresh on the bench branch); comparison 1 needs round six's rows, which stop at 200.

## Global Constraints

- Work only in `/media/user/dev-ssd/worktrees/households-homes/babylon`, branch `codex/households-and-homes`, except
  Task 5 (a throwaway branch in the same worktree). Start every shell command with `cd` to it (or to its `rust/`).
  Never push. No `.env`, no `uv.lock`.
- One cargo process at a time on the whole machine. Never pass `-j`. Only `mise exec -- cargo ...` and
  `mise run ...`. A build in another checkout wipes this one's cache: warn the lead before a long build.
- While working: `mise run rust:test:q -- -p babylon-material-circuit -E '<filter>'`, one test binary. Once at the
  end of each task: from `rust/`, `mise exec -- cargo fmt --all -- --check`; `mise exec -- cargo clippy -p
  babylon-material-circuit --all-targets --locked -- -D warnings -D clippy::cognitive_complexity`;
  `mise run rust:test:q -- -p babylon-material-circuit`; `mise run rust:test:q -- -p babylon-tick`. Before a
  push (the lead's): `mise run rust:check-no-docs --dev` and `mise run check:bsl-sentinels`.
- Tests never read the data drive (`/media/user/data`).
- No pinned value of any existing test changes. No assertion is loosened. If one must move, stop and tell the
  lead.
- Money is `i128` millionths of a dollar; quantities are `u64` whole units; arithmetic is checked, a failure is a
  typed `MaterialCircuitError`, never a panic, an `unwrap` or a wrap outside tests. Maps are `BTreeMap`; every
  pass over workplaces goes in key order.
- A contract line that changes is changed with its pinned digest (`MATERIAL_CIRCUIT_SOURCE_SHA256` in
  `src/wire/state.rs`, the SHA-256 of the file's bytes, checked in `tests/weighted_freight.rs` near line 382) in
  the same commit. The contract is linted on commit at 120 characters a line.
- `babylon-tick` refuses every transition with market clearings or tier records
  (`babylon-tick/src/material_world/register.rs`, near line 1900). The rule is reachable from this crate's tests
  only; nothing in `babylon-tick` changes.
- Functions stay under 100 lines and a cognitive complexity of 25 (`rust/clippy.toml`); at most 7 parameters.
- Every line number is a hint; find each place by its text. Markdown lines at most 120 columns.
- Commit: `git add <files>`; message in a file; `PYTHONPATH=src mise exec -- git commit -q -F <file>`; then check
  `git log --oneline -1`. The body ends with `Part of PER-371` and a `Co-Authored-By` line naming the model that
  wrote the commit.

## Review Focus

1. **A world that does not ask moves.** Moving `services.plan`, recording the business part unasked, or the
   refactor of `input_requirements` would change bytes. Pinned by Task 1,
   `a_world_that_does_not_ask_keeps_its_bytes`, re-run unchanged by Tasks 2 to 4.
2. **The business part exceeds what was payable.** The two places that record it (`services/admission.rs`
   `price_stage_market` and `services/tiers.rs` `price_market`) read different structures; a mismatch makes the
   households' part negative, and that is an error that stops the run. Pinned by Task 3,
   `households_part_is_payable_less_business`, and Task 4, `every_push_closes_with_the_chain` (tiers and no tiers).
3. **A purse paid twice.** A buyer with two service policies must not spend its cash twice. Pinned by Task 3,
   `one_purse_pays_a_buyers_orders_once`.
4. **The order of visiting decides, the passes never end, or a pass reads the state instead of the plans it
   is given.** On the bench and in the small world only the utility's plan moves, so a pass that read every
   service's batches from the state would rest after one pass with the same figures. Pinned by Task 3,
   `the_order_of_the_keys_does_not_change_the_rest` and `plans_that_never_rest_are_refused_at_the_bound`; by
   Task 4, `a_last_stage_service_with_a_business_buyer_chains_into_the_utility`; and by every asking run of Task
   4 (a close that did not rest is an error).
5. **The state and the receipt disagree.** A6 reads the receipt's `planned_quantity`, the next period reads the
   state's `planned_batches`. Pinned by Task 4, `the_receipt_carries_the_chained_plan`.

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `rust/crates/babylon-material-circuit/tests/small_world/chain.rs` | The small world asking for the rule; the pin | 1, 4 |
| `rust/crates/babylon-material-circuit/tests/small_world.rs` | `mod chain` | 1 |
| `rust/crates/babylon-material-circuit/src/clearing/rule.rs` | `MarketClearingPolicy.plans_through_the_chain` | 2 |
| `rust/crates/babylon-material-circuit/src/wire/catalog.rs` | Catalog version 9 | 2 |
| `rust/crates/babylon-material-circuit/src/catalog.rs` | Its tests | 2 |
| `contracts/material_circuit_v4.yaml`, `src/wire/state.rs` | The version line, rule A5, the digest | 2 |
| `rust/crates/babylon-material-circuit/src/services/chain.rs` | Orders, plans, the passes; the step | 3, 4 |
| `rust/crates/babylon-material-circuit/src/services/requirements.rs` | `requirements_from` | 3 |
| `rust/crates/babylon-material-circuit/src/clearing/table.rs` | The business buyers' part of a market | 4 |
| `src/services/admission.rs`, `src/services/tiers.rs` | Record it | 4 |
| `src/services/market.rs`, `src/services/close.rs` | `future_quantities`, `moment_of`; the step's entry | 4 |
| `rust/crates/babylon-material-circuit/src/transition/state.rs` | `Asked`; the step after `plan_production` | 4 |
| `rust/crates/babylon-material-circuit/tests/small_world/support.rs` | `World.chain`, `with_chain`, `with_farm_buying_care` | 2, 4 |
| Bench worktree and `restoring-spike/scripts/a5*.{sh,py}` | Built rule against its prototype; ships nothing | 5 |
| `reports/economy-repair-2026-11-20/small-world.md` | The record | 6 |

---

### Task 1: Pin a world that does not ask

**Files:**
- Create: `tests/small_world/chain.rs` (paths in this crate are under `rust/crates/babylon-material-circuit/`).
- Modify: `tests/small_world.rs` (`#[path = "small_world/chain.rs"] mod chain;`).

**Interfaces:**
- Consumes: `support::{run_observed, World, Push}`; `babylon_material_circuit::material_circuit_state_digest`;
  `MaterialCatalog::catalog_digest`; `babylon_kernel::content_digest::sha256_of`.
- Produces: `fn worlds() -> [World; 6]` (the six worlds of decision 2, in that order) and
  `fn fingerprint(world: &World) -> String`, both private to `chain.rs`, used again by Task 4.

**Decisions:**
1. A fingerprint is the hex SHA-256 of: the catalog digest; then, for each period, the state digest and the bytes
   of `format!("{transition:?}")`. It pins state, receipts and catalog at once. A toolchain that changed derived
   `Debug` text would move it; then the lead decides, nothing is re-pinned silently.
2. Six worlds, 34 periods each: `World::plain()`; `World::less_supply().with_market()`;
   `World::higher_pay().with_tiers()`; `World::benefits().with_tiers().pushed(Push::LessSupply)`;
   `World::benefits().with_tiers().pushed(Push::LowerFundTaxes)`; `World::higher_pay().with_tiers()
   .with_spare_money()`. They cover no policy, a policy without tiers, tiers, the fund and A6.

- [ ] **Step 1: Write the test** `a_world_that_does_not_ask_keeps_its_bytes`:

```rust
const PINNED: [(&str, &str); 6] = [("plain", ""), ("market P2", ""), ("tiers P4", ""),
    ("fund tiers P2", ""), ("fund tiers P5", ""), ("spare tiers P4", "")];
let got: Vec<(&str, String)> = PINNED.iter().zip(worlds())
    .map(|((name, _), world)| (*name, fingerprint(&world))).collect();
let want: Vec<(&str, String)> = PINNED.iter().map(|(n, h)| (*n, (*h).to_owned())).collect();
assert_eq!(got, want); // all six are printed when one differs
```

- [ ] **Step 2: Run it and see it fail,** printing each fingerprint. `mise run rust:test:q -- -p
  babylon-material-circuit -E 'test(a_world_that_does_not_ask_keeps_its_bytes)'`.
- [ ] **Step 3: Pin** the six printed values. Nothing in `src/` changes in this task.
- [ ] **Step 4: Run it and see it pass;** run it twice: the same values.
- [ ] **Run the gate. Commit** `test(material-circuit): pin the bytes of worlds that do not plan through the chain`.

### Task 2: The market policy asks for the rule

**Files:**
- Modify: `src/clearing/rule.rs` (the field); `src/wire/catalog.rs` (`bytes`); `src/catalog.rs` (tests);
  `contracts/material_circuit_v4.yaml` and the digest in `src/wire/state.rs`.
- Modify: every hand-built `MarketClearingPolicy` gets `plans_through_the_chain: false`
  (`rg -n 'MarketClearingPolicy \{' rust/crates` lists them, all in this crate; the struct, its `impl` and the
  signature `fn policy(order: &[u8]) -> MarketClearingPolicy {` in `src/catalog.rs` are three of the lines that
  are not literals). The small world's literal (`tests/small_world/support.rs`, near line 430) is `false` here; Task 4
  gives it its switch.

**Interfaces:**

```rust
// src/clearing/rule.rs, MarketClearingPolicy gains:
/// Rule A5 (ADR314): at the close each business orders what its new plan needs of the services it
/// buys, and each service in the order of paying plans for those orders, until the plans rest.
/// `false` keeps today's plans and bytes.
pub plans_through_the_chain: bool,
// src/wire/catalog.rs
/// A market policy that plans through the chain writes this version first, then every byte the
/// same catalog writes without it.
const CHAIN_CATALOG_SCHEMA_VERSION: u16 = 9;
```

**Decisions:**
1. `true` writes `9_u16` right after the domain and terminator, before the `8` of A6 if that is asked too, then
   the bytes the same catalog writes with this flag off. Nothing decodes catalog bytes; their readers take the
   digest. Admission refuses nothing new.
2. Contract: `catalog_version` (near line 74) gains "a market policy that plans through the chain writes 9
   first, then the bytes the same catalog writes without it, so one that also plans from spare money writes 9,
   then 8"; the tail comment (near line 130) says the same; `P13_asking` gains "and A5 only by setting
   plans_through_the_chain"; and a new `A5_chain` after it, in the contract's style: "at the close each business
   orders, for each service in the order of paying that it buys, what its new plan needs, capped by its policy,
   as far as its cash at the close pays at the price posted in the period that closed, one purse for all its
   orders in the order of paying; such a service plans owed, its households' part of what was payable at its
   posted price and those orders, or what is funded for the next period if more; the plans are made again from
   the plans before until a pass changes nothing, at most 3 passes; no money moves and no order is stored; a
   catalog that does not set plans_through_the_chain plans as before".
3. No scenario key: shipped scenarios ask for no market policy.

- [ ] **Step 1: Write the failing tests** in `src/catalog.rs`'s tests, beside A6's:
  `chain_writes_version_nine_before_the_bytes_without_it` (as A6's twin: `bytes[head..head + 2] == 9_u16
  .to_be_bytes()` and `bytes[head + 2..] == plain_bytes[head..]`, `head` from `MATERIAL_CATALOG_DOMAIN_BYTES`);
  `chain_and_spare_money_write_nine_then_eight` (both flags: `bytes[head..head + 4]` is `9_u16` then `8_u16`, and
  `bytes[head + 2..]` equals the bytes with A6 alone); `chain_changes_the_digest` (with and without wants, each
  digest differs from its twin's). Every existing digest test passes unchanged.
- [ ] **Step 2: Run them and see them fail.** `mise run rust:test:q -- -p babylon-material-circuit -E
  'test(chain_)'`. Expected: does not compile, no field `plans_through_the_chain`.
- [ ] **Step 3: Implement** the field, the constant, the prefix in `bytes`, the literals, the contract and its
  digest.
- [ ] **Step 4: Run** `mise run rust:test:q -- -p babylon-material-circuit`. Expected: all pass, Task 1's pin
  included.
- [ ] **Run the gate. Commit** `feat(material-circuit): let a market policy ask for plans through the chain`.

### Task 3: The arithmetic of the chain

**Files:**
- Create: `src/services/chain.rs` (`mod chain;` in `src/services.rs`), with its `#[cfg(test)] mod tests`.
- Modify: `src/services/requirements.rs` (`requirements_from`; `input_requirements` calls it).

**Interfaces:**

```rust
// src/services/requirements.rs
/// Service inputs of these batches, by buyer site and service; `input_requirements` builds the
/// batches from the state and calls this.
pub(crate) fn requirements_from(
    catalog: &MaterialCatalog,
    batches: &BTreeMap<ProcessId, u64>,
) -> Result<InputRequirements>;

// src/services/chain.rs (StockKey is crate::recurring::firms::StockKey; define no new alias)
/// One more pass than there are service stages: the plans of the last stage are final after one
/// pass, those of each stage before it one pass later, and one more pass confirms the rest.
pub(crate) const CHAIN_PASSES: usize = 3;

/// What households could pay for at the posted price: what every buyer could, less the business
/// buyers' part. `Err(ServiceInvariant)` when the business part is larger.
pub(crate) fn households_part(payable: Option<u64>, business: u64) -> Result<u64>;

/// A placed service's plan for the next period: owed, households' part and business orders, or
/// what is funded for the next period if that is more.
pub(crate) fn chained_plan(owed: u64, households: u64, orders: u64, future: u64) -> Result<u64>;

/// One order a business places at the close for the next period.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct ChainOrder {
    pub(crate) buyer: SiteId,
    /// The product's place in the order of paying.
    pub(crate) place: usize,
    pub(crate) provider: StockKey,
    /// What the buyer's new plan needs, capped by its policy.
    pub(crate) need: u64,
    /// The provider's price posted in the period that closed.
    pub(crate) price: Currency,
    pub(crate) floor: Currency,
}

/// What each provider is ordered, summed over its buyers. A buyer's cash pays its orders once, in
/// the order (buyer, place, provider); each takes `affordable(need, price, left - floor)`.
pub(crate) fn orders_from_purses(
    orders: &[ChainOrder],
    cash: &BTreeMap<SiteId, i128>,
) -> Result<BTreeMap<StockKey, u64>>;

/// Repeat `pass` from `first` until a pass returns what it was given, at most `bound` passes.
/// Returns the rested plans and the number of passes; `Err(ServiceInvariant)` at the bound.
pub(crate) fn rest<P: PartialEq>(
    bound: usize,
    first: P,
    pass: impl FnMut(&P) -> Result<P>,
) -> Result<(P, usize)>;
```

**Decisions:**
1. `orders_from_purses` sorts a copy of its input by `(buyer, place, provider)`; a buyer missing from `cash` is
   `Err(MonetaryInvariant)`; spending is `checked_mul` and `checked_sub`; sums are `checked_add` (`Arithmetic`).
   It reuses `recurring::spare_money::affordable` (0 at or under the floor, all of it at price 0 above the
   floor). The map holds only providers ordered above 0; a reader takes a missing key as 0.
2. `rest` calls `pass` at most `bound` times and never loops otherwise; equality is `PartialEq` on the whole map.
3. Until Task 4 calls them, mark the new items with
   `#[cfg_attr(not(test), allow(dead_code, reason = "Task 4 calls them from the close"))]`, as Task 2 of the
   pattern plan did. Task 4 removes the attribute.

- [ ] **Step 1: Write the failing tests** (money in millionths):
  - `the_plan_is_owed_households_and_orders`: `chained_plan(2, 30, 50, 0) == Ok(82)`;
    `chained_plan(2, 30, 50, 100) == Ok(100)`; `chained_plan(u64::MAX, 1, 0, 0)` is `Err(Arithmetic)`.
  - `households_part_is_payable_less_business`: `(Some(80), 50) == Ok(30)`; `(Some(80), 0) == Ok(80)`;
    `(None, 0) == Ok(0)`; `(Some(10), 11)` and `(None, 1)` are `Err(ServiceInvariant)`.
  - `a_buyer_orders_what_its_plan_needs_when_its_cash_pays`: need 50 at $12, cash $1,000 gives 50.
  - `a_buyer_orders_only_what_its_cash_pays`: need 50 at $12, cash $300 gives 25; with a floor of $60, 20.
  - `one_purse_pays_a_buyers_orders_once`: one buyer, place 0 need 10 at $10 and place 1 need 10 at $10, cash
    $150: 10 and 5; the input in the other order gives the same map.
  - `two_buyers_of_one_provider_add`: 30 and 12 at one provider give 42.
  - `a_purse_at_or_below_its_floor_orders_nothing`: cash 0, cash −$40, and cash $60 with a floor of $60, each
    give an empty map.
  - `a_free_service_is_ordered_in_full`: need 7 at $0, cash $1 gives 7; cash 0 gives an empty map (the purse is
    read before the price, as `affordable` does).
  - `rest_stops_when_a_pass_changes_nothing`: `rest(3, 5_u64, |p| Ok(*p)) == Ok((5, 1))`.
  - `a_chain_of_two_stages_rests_in_three_passes`: plans `{a: 0, b: 0}`, a pass sets `a = 10` and
    `b = previous a + 1`: `Ok(({a: 10, b: 11}, 3))`.
  - `the_order_of_the_keys_does_not_change_the_rest`: the same chain with the dependent market named so that it
    sorts first: the same plans and passes.
  - `plans_that_never_rest_are_refused_at_the_bound`: a pass that flips `0` and `1` gives `Err(ServiceInvariant)`
    and was called exactly 3 times.
  - `the_bound_counts_every_service_stage`: an exhaustive `match` over `ServiceStage` (no `_` arm) counts 2
    stages, and `CHAIN_PASSES == 2 + 1`. A new stage breaks the build until the bound is revisited.
- [ ] **Step 2: Run them and see them fail.** `mise run rust:test:q -- -p babylon-material-circuit -E
  'test(chain::)'`. Expected: does not compile.
- [ ] **Step 3: Implement** the five functions and `requirements_from`. They are pure; nothing calls them yet but
  `input_requirements`.
- [ ] **Step 4: Run them and see them pass;** then `mise run rust:test:q -- -p babylon-material-circuit`, Task 1's
  pin included.
- [ ] **Run the gate. Commit** `feat(material-circuit): the arithmetic of plans through the chain`.

### Task 4: Plans through the chain at the close

**Files:**
- Modify: `src/clearing/table.rs` (the business part); `src/services/admission.rs` (`price_stage_market`, near
  line 560) and `src/services/tiers.rs` (`price_market`, near line 225) record it; `src/services/market.rs`
  (a new `future_quantities` beside `update`, which keeps its own grouping and lazy sum unchanged: its comment
  says the lazy sum keeps the first refusal, an offer missing before a sum that overflows; `moment_of` taken out
  of `planned_quantity`, same values);
  `src/services/chain.rs` (`plan`, `asks`; Task 3's attributes go); `src/services/close.rs`
  (`plan_through_the_chain`); `src/transition/state.rs` (`Asked`, `next_plans` near 1136, its call near 1675).
- Modify: `tests/small_world/support.rs` (`World.chain`, `with_chain`, `World.farm_buys_care`,
  `with_farm_buying_care`, the policy literal); `tests/small_world/chain.rs`.

**Interfaces:**
- Consumes: Task 2's flag; Task 3's functions and `requirements_from`; `required_input`;
  `recurring::spare_money::affordable`; `admission::owed_quantities`.
- Produces:

```rust
// src/clearing/table.rs, MarketTable gains:
/// What the business buyers of a market could pay for at the posted price (rule A5).
business: BTreeMap<MarketKey, u64>,
pub(crate) fn record_business(&mut self, moment: MarketMoment, seller: (SiteId, GoodId, UnitId),
    quantity: u64) -> Result<(), MaterialCircuitError>;
/// 0 when nothing was recorded.
pub(crate) fn business_at_quote(&self, moment: MarketMoment, site: SiteId, good: GoodId,
    unit: UnitId) -> u64;
// src/services/market.rs
pub(super) fn future_quantities(state: &MaterialCircuitState, next_period: u64)
    -> Result<BTreeMap<StockKey, u64>>;
pub(super) fn moment_of(catalog: &MaterialCatalog, key: StockKey) -> Result<MarketMoment>;
// src/services/chain.rs
/// Whether the catalog's market policy asks for rule A5.
pub(crate) fn asks(catalog: &MaterialCatalog) -> bool;
/// Rule A5 at the close, after the makers of goods have planned. Writes each placed service's
/// receipt `planned_quantity` and state `planned_batches`; returns the passes made.
pub(crate) fn plan(
    catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState,
    books: (&MarketTable, &BTreeMap<StockKey, u64>),
    markets: &mut [ServiceMarketReceipt],
    next_period: u64,
) -> Result<usize>;
// src/services/close.rs, ServiceClose gains:
pub(crate) fn plan_through_the_chain(&mut self, catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState, priced: &MarketTable, next_period: u64) -> Result<()>;
// src/transition/state.rs
/// What the close's planning reads besides the state, and the service close it may plan again.
pub(crate) struct Asked<'a> {
    pub(crate) demand: &'a [HouseholdDemandReceipt],
    pub(crate) markets: &'a MarketTable,
    pub(crate) procurement: &'a [ProcurementReceipt],
    pub(crate) services: &'a mut ServiceClose,
}
// next_plans takes `asked: Asked<'_>` in place of `wanted: Wanted<'_>`; still 7 parameters.
// tests/small_world/support.rs, World gains `pub chain: bool` and:
/// Rule A5 on the market policy; sets `market` too.
pub(crate) fn with_chain(mut self) -> Self;
/// World gains `pub farm_buys_care: bool`: the farm's process takes one care a batch, bought from
/// the clinic under a service input policy capped at twice the opening need, with its service
/// connection in the opening state. Used by one test only; no pinned world sets it.
pub(crate) fn with_farm_buying_care(mut self) -> Self;
```

**The order of `plan`** (the signatures do not determine it):
1. The fixed rows, for each receipt in `markets` (key order) whose product is placed (`policy.place`): its
   process and quantity per batch; owed (`books.1`); `households_part(priced.demand_at_quote(moment, key),
   priced.business_at_quote(moment, key))`; `future_quantities`; the receipt's `old_price`.
2. Pass zero: each fixed row's receipt `planned_quantity` (today's P14 plan, already written by `update`).
3. A pass from plans `p`: batches are the state's `planned_batches` of every process, with each fixed row's
   process set to `p[key].div_ceil(per_batch)`; `requirements_from` those batches; for each `catalog
   .service_inputs` policy whose provider key is a fixed row, a `ChainOrder` with `need = required_input(..)`,
   that row's price, the policy's `place` and `cash_floor`; `cash` is `book.cash(AccountId::Site(buyer))` of each
   buyer, read once before the first pass; the new plan of each row is `chained_plan(owed, households,
   orders[key], future)`.
4. `rest(CHAIN_PASSES, pass_zero, pass)`.
5. Write each rested plan to its receipt's `planned_quantity` and `plan.div_ceil(per_batch)` to its process's
   `planned_batches`.

**Decisions:**
1. **Recording.** When `chain::asks(catalog)`, `price_stage_market` records, for a market with a private supply,
   the sum over its business bidders of each one's demand at the posted price alone
   (`clear_market(u64::MAX, posted, &[bid]).demand_at_quote`); `price_market`, when `supply.is_some()`, the sum
   of the reachable quantities of its seats whose account is a site. That is the prototype's arithmetic
   (`spike/r6-A4`, `services/admission.rs` near 630 and `services/tiers.rs` near 248). Not asking, neither
   records.
2. **The close.** `close_material_period_with_portfolios` calls `services.plan` where it does today, then
   `next_plans` with an `Asked`. Inside: build `Wanted` from `asked` and run `plan_production`; when
   `chain::asks(catalog)`, `asked.services.plan_through_the_chain(..)`; build `Wanted` again (its `services` now
   holds the chained receipts) and run `plan_attendance` and `update_prices` as today.
3. **Forward orders.** The engine carries orders for a later period and uses none: `ServiceOrder
   .performance_period` (`services/model.rs`, near 34-43, "a funded claim") is validated `>= state.period`
   (`services/validation.rs`, near 108-110), stored (`wire/services.rs`, near 54 and 66; contract line 308), read
   for the next period by `update` (`services/market.rs`, near 105-133 and 196, `.max(future)`) and by
   `planning_grants` (`services/requirements.rs`, near 64-73), and admitted as due commitments
   (`services/admission.rs`, near 205-245, 263-271 and 444-458); but every order is made with
   `performance_period: state.period` (`admission.rs`, near 297 and 615; `close.rs`, near 152). This task leaves
   them so (departure D1). `future_quantities` keeps reading them: if one is ever made, the plan honours it.
4. `plan` and its helpers stay under the limits: split it along `fixed_rows`, `pass` and `write`.
5. `plan` returns `Ok(0)` and changes nothing when the accounting is not monetary or has no recurring economy,
   as `update` does. `record_business` refuses a second record for one market key with
   `Err(MarketClearingInvariant)`, as `record` does; each market is priced once a period.

- [ ] **Step 1: Write the failing tests** in `tests/small_world/chain.rs`:
  - `asking_changes_nothing_in_a_quiet_world`: for `World::plain().with_market()`, `World::plain().with_tiers()`,
    `World::benefits().with_tiers()` and `World::plain().with_tiers().with_spare_money()`, each `.with_chain()`:
    `support::assert_still_rows` passes and its rows equal, field for field, the same world's not asking.
  - `asking_changes_nothing_in_a_quiet_world_for_400_periods`: `World::plain().with_tiers()`,
    `World::benefits().with_tiers()` and `World::plain().with_tiers().with_spare_money()`, each
    `.for_periods(400).with_chain()`, pass `assert_still_rows`.
  - `the_utility_plans_for_its_buyers_new_plans`: `World::less_supply().with_tiers()` with and without
    `.with_chain()`, period 1 (both runs are equal until that close); and the same assertions for
    `World::less_supply().with_market()`, the only form that reaches the recording in `price_stage_market`
    (every bench world has tiers):

```rust
assert_ne!(with.utility.planned_quantity, without.utility.planned_quantity);
// orders: what the farm's and the clinic's batches in the asking state need, capped at the policy
let orders = (10 * with.farm_batches).min(cap_farm) + with.clinic_batches.min(cap_clinic);
// what the farm and the clinic asked of the utility in period 1 (each was admitted in full)
assert!(business.iter().all(|r| r.admitted_quantity == r.requested_quantity));
let asked: u64 = business.iter().map(|r| r.requested_quantity).sum();
assert_eq!(i128::from(with.utility.planned_quantity) - i128::from(without.utility.planned_quantity),
    i128::from(orders) - i128::from(asked));
assert_eq!(with.clinic.planned_quantity, without.clinic.planned_quantity);
// and pin both utility plans
```

    where `business` is period 1's `service_performance` rows at the utility whose buyer is a site, `cap_*` the
    policy caps (twice the opening need), and the cash of both buyers at the close covers their orders at $12
    (assert it). If the buyers' cash does not cover them at period 1, say so in your report.
  - `a_last_stage_service_with_a_business_buyer_chains_into_the_utility`:
    `World::less_supply().with_tiers().with_farm_buying_care()` with and without `.with_chain()`, period 1. The
    clinic now has a business buyer, so its plan moves and the utility must plan from the clinic's moved plan:

```rust
assert_ne!(with.clinic.planned_quantity, without.clinic.planned_quantity);
// the utility's orders read the clinic's batches in the ASKING state, the chained ones
let orders = (10 * with.farm_batches).min(cap_farm) + with.clinic_batches.min(cap_clinic);
assert_eq!(i128::from(with.utility.planned_quantity) - i128::from(without.utility.planned_quantity),
    i128::from(orders) - i128::from(asked_of_utility));
```

    with `asked_of_utility` and the admitted-in-full check as in the test above. A pass that read the clinic's
    batches from the state, not from the plans it was given, fails the second assertion. If the clinic's plan
    does not move at period 1, say so in your report rather than change the world.
  - `the_receipt_carries_the_chained_plan`: in the asking runs of `World::less_supply().with_tiers()`,
    `World::higher_pay().with_tiers()` and `World::benefits().with_tiers().pushed(Push::LowerFundTaxes)`, in every
    period and for every service receipt, the state's `planned_batches` of its process equals
    `planned_quantity.div_ceil(per_batch)` (one unit a batch on the bench).
  - `every_push_closes_with_the_chain`: `World::plain().with_tiers()` pushed by each of `LessDemand`,
    `LessSupply`, `LessMoney`, `HigherPay`; `World::benefits().with_tiers()` pushed by `LessSupply`, `HigherPay`,
    `LowerFundTaxes`; `World::less_supply().with_market()` (no tiers); and `World::higher_pay().with_tiers()
    .with_spare_money()`; each `.with_chain()`: `support::run` completes. A close that did not rest, or a business
    part above what was payable, is an error and fails it; money is checked in every period by the harness.
- [ ] **Step 2: Run them and see them fail.** `mise run rust:test:q -- -p babylon-material-circuit -E
  'binary(small_world)'`. Expected: does not compile, no `with_chain`; after the builder alone,
  `the_utility_plans_for_its_buyers_new_plans` fails.
- [ ] **Step 3: Implement** the table, the recording, `future_quantities` and `moment_of`, `plan`, the
  `ServiceClose` entry, `Asked` and the call, and the two builders. Run once, read period 1's utility plans, pin
  them.
- [ ] **Step 4: Run** `mise run rust:test:q -- -p babylon-material-circuit`. Expected: every existing test passes
  unchanged, Task 1's pin and the small world's `quiet.rs`, `pushed.rs`, `tiers.rs`, `benefits.rs` and
  `spare_money.rs` included.
- [ ] **Run the gate. Commit** `feat(material-circuit): plans through the chain at the close`.

### Task 5: The built rule against its prototype, on the bench

This task builds nothing that ships. Its branch is never pushed and never merged. Its result goes to the lead
before the rule is called done.

**Files** (all throwaway):
- The worktree itself, switched to a new branch `spike/r7-A5-bench` made from `spike/r6-A4`, with the head of
  Task 4 merged in, as the measurement rounds did. No second checkout: this machine keeps one build cache for all
  checkouts, and a build in another checkout would evict it. The worktree goes back to
  `codex/households-and-homes`, clean, before the task reports.
- In it: `rust/crates/babylon-material-circuit/tests/small_world/support.rs` (its policy literal, near line 885,
  and `spike_a5_built`), `tests/small_world/spike.rs` (the refusal in `write_run`) and `tests/small_world.rs`.
- Create: `a5all.sh` and `a5same.py` in `<the measurement folder>/scripts/`. The run
  script is `r6Trun.sh` there, as it stands.

**Interfaces:**
- Consumes: Task 4's `plans_through_the_chain`, `MarketTable::record_business` and `business_at_quote`; the
  prototype's `babylon_material_circuit::spike_d()`.
- Produces, in the bench harness only (`tests/small_world/support.rs`, so the policy literal can read it):

```rust
/// The built rule A5 on the bench's market policy: `SPIKE_A5_BUILT=on`; unset or `off` leaves it
/// off; any other value panics. Read once. With `SPIKE_D=on` too, `write_run` panics.
pub(crate) fn spike_a5_built() -> bool;
```

**Decisions:**
1. **The merge.** Where it conflicts, the spike's side wins, except the lines that carry rule A5 as built and the
   two policy fields. The built rule A6 may be dropped where it conflicts with the spike's port of it (F2): the
   bench reaches A6 through `SPIKE_F2`, and the built A6 flag stays `false`. The chain call goes where the spike
   calls `services.plan` under `SPIKE_D`: after `plan_production`, before F2 reads the service receipts; with
   `SPIKE_D` off, `services.plan` stays where the built close calls it.
   **The business part is the built one, for both forms.** Keep Task 4's `MarketTable.business`,
   `record_business` and the two built recording sites; delete the spike's own `business` list and its two
   `record_business` calls (`services/admission.rs` near 640, `services/tiers.rs` near 259; the A4 call near 446
   is changed to the built signature with `?`). The built sites record when `chain::asks(catalog) || spike_d()`,
   and the prototype's `update` reads the built `business_at_quote`. So comparison 1 also proves the built
   recording against the prototype's, and comparison 2 is about the chain alone.
   **The test binary.** The bench runs only `spike_rows` in `--test small_world`, but the whole binary must
   build. Where a module that came with the merge (`spare_money.rs`, `chain.rs`) does not build against the
   spike's `support.rs`, remove its `mod` line from `tests/small_world.rs` on the bench branch; keep `spike.rs`.
2. **The sets** (`a5all.sh`, bash, one run after another; `S=$root/scripts/r6Trun.sh`):

```bash
BEST="SPIKE_TWO=on SPIKE_F2=on SPIKE_D2=on SPIKE_RULE=a"   # round six's two-bound-plain, without D
NAT="SPIKE_STEP_BPS=250 SPIKE_J_PERIODS=2"
bash $S a5-proto-200 200 $BEST SPIKE_D=on;       bash $S a5-proto-nat-200 200 $BEST SPIKE_D=on $NAT
bash $S a5-built-200 200 $BEST SPIKE_A5_BUILT=on; bash $S a5-built-nat-200 200 $BEST SPIKE_A5_BUILT=on $NAT
bash $S a5-none-200 200 $BEST;                    bash $S a5-none-nat-200 200 $BEST $NAT
bash $S a5-proto-400 400 $BEST SPIKE_D=on;       bash $S a5-proto-nat-400 400 $BEST SPIKE_D=on $NAT
bash $S a5-built-400 400 $BEST SPIKE_A5_BUILT=on; bash $S a5-built-nat-400 400 $BEST SPIKE_A5_BUILT=on $NAT
```

   Rows land in `<the measurement folder>/out/<name>/`, 25 TSV files each. Run
   `a5all.sh` with bash, not zsh (zsh does not split `$BEST`). `BEST` with `SPIKE_D=on` is exactly
   `V[two-bound-plain]` of `r6allvariants.sh`.
3. **What is compared.** Every column the two runs share, except those whose name starts with `flow_d_` (the
   prototype's own receipt, `SpikeDReceipt`, which the built rule does not have). A column on one side only,
   other than `flow_d_*`, is itself a difference. Plan columns are compared too: `next_*`, `asked_next_*`,
   `employed_next_*`, `spare_*` and `flow_f2_*` read the plans the chain wrote (F2 reads the services' planned
   quantities), and a built rule that differs only in a plan is still not the prototype. Round six's step X
   proved its two ends the same way, on every column the two forms share but the forms' own flows
   (`scripts/r6Xcols.py`; round six, section 2).
   **Realized columns,** used to classify a difference in the report: every column but those starting with
   `flow_`, `next_`, `asked_next_` or `spare_`. They are what happened: period, cash, posted prices (`quote_*`,
   `price_next_*`), output, stock, hours planned, attended and used, idle paid, employed, wages, markets, needs,
   wants, standards, taxes, public payments and total money.
4. **`a5same.py <dirA> <dirB> [--all]`** (run as `python3 -I`): the same TSV names in both, the same row count in
   each pair and the same `period` on each line; it compares cell text, column by column, over the shared columns
   of decision 3, or with `--all` over every column and requires equal headers. For each run it prints `equal`,
   or each differing column, marked `realized` or `plan`, with the number of periods, the first and last period
   and the first pair of values. It exits 0 only if every run is equal.
5. **Comparisons, in order** (`P=<the measurement folder>`; `same="python3 -I
   $P/scripts/a5same.py"`; each line also at `-nat-200`):

```bash
$same $P/out/a5-proto-200 $P/out/r6-two-bound-plain-200 --all   # 1: the merge kept the prototype
$same $P/out/a5-built-200 $P/out/a5-proto-200                   # 2: the finding
$same $P/out/a5-none-200  $P/out/a5-proto-200                   # 3: the control
```

   1. Every run equal. This proves the merge kept the prototype and that the built recording gives the
      prototype's business part. If not, the merge is wrong: fix the merge, never the rule.
   2. The finding.
   3. Equal in `plain-` and `fund-` `quiet`, `P1`, `P3` and `P7`; different in the other 17 runs at each set of
      figures (P2, P4, P5, P6, P8 and the one-copy forms). These are exactly the runs whose round-six rows have a
      non-zero `flow_d_beyond_*` column in some period. Otherwise the comparison cannot see A5, and the finding of
      2 means nothing. (`out/r6-two-no-D-200` is not this control: it frees the buyers and adds the price rules.)
   4. The lead asks for comparison 2 at 400 periods too, at both sets of figures (`a5-built-400` against
      `a5-proto-400`, and the `-nat-400` pair), because the design measures at 400.
6. **If 2 is not equal:** add one switch for each departure that can move rows, each turning the built rule's
   form into the prototype's: `SPIKE_A5_AS_D_ONE_PASS` (one pass, local services then the utility),
   `SPIKE_A5_AS_D_PURSE` (each order against the whole purse), `SPIKE_A5_AS_D_WHOLE_PLAN` (all of
   `services.plan` after `plan_production`). Prove both ends: every switch off gives `a5-built` byte for byte
   (`--all`); every switch on gives `a5-proto` in every column of decision 3. Then each switch alone names the
   runs it moves. A difference no switch explains is a fault in the built rule: stop and report it with its first
   run, period, column and values.
7. **What the bench cannot see.** Every bench world has tiers, one service policy a buyer, no business buyer of
   the clinic, no price at 0 and no forward order; the built A6 is off. So equality says nothing about the
   recording in `price_stage_market`, one purse over two orders, a rest that needs three passes, a free service,
   or A5 beside the built A6. Those are Task 3's and Task 4's tests (`one_purse_pays_a_buyers_orders_once`,
   `a_free_service_is_ordered_in_full`, `a_last_stage_service_with_a_business_buyer_chains_into_the_utility`,
   the `with_market()` form of `the_utility_plans_for_its_buyers_new_plans`, and the spare-money worlds of
   `every_push_closes_with_the_chain`). The report says so.

- [ ] **Step 1:** In the worktree, check that it is clean and on `codex/households-and-homes`, and note its head
  (Task 4's head). Then `git switch -c spike/r7-A5-bench spike/r6-A4`; `git merge --no-ff <Task 4's head>`;
  resolve by decision 1; commit the merge. The first run of Step 3 builds it.
- [ ] **Step 2:** Add `spike_a5_built()`, the literal and the refusal; commit on the bench branch.
- [ ] **Step 3:** Write `a5run.sh`, `a5all.sh` and `a5same.py`; run `bash a5all.sh`.
- [ ] **Step 4:** Make comparison 1. Expected: equal in all 50 runs.
- [ ] **Step 5:** Make comparisons 2 and 3. Expected: 2 equal in all 50 runs; 3 as decision 5 says.
- [ ] **Step 6:** Only if 2 differs, decision 6.
- [ ] **Step 7:** Report to the lead: for each comparison and each set of figures, the runs equal and not; for
  every difference, `realized` or `plan`, its departure and switch; decision 7's list; the commands as run; the
  commit of the bench branch and the Task 4 commit merged into it. Do not call the rule done. Then
  `git switch codex/households-and-homes` and check that `git status --short` is empty and the head is the one
  noted in Step 1. Delete nothing; the lead removes the branch when the rule is accepted.

### Task 6: The record

**Files:**
- Modify: `reports/economy-repair-2026-11-20/small-world.md` (a section "Plans through the chain (rule A5)"
  after "Spare money (rule A6)").

**Decisions:**
1. The section says, in the record's style: what the rule does for each kind of workplace (the table above); the
   bound and rest; that no order is stored or funded, and that goods orders follow target stock (D1, D2, as open
   points for the Director); the departures from the prototype; Task 4's pinned period-1 plans of the utility;
   and Task 5's result as the lead accepted it, with its commands and counts. No figure a test or a run did not
   print.
2. The contract text is Task 2's; the decision records are not edited (ADR312 already carries ADR314's amendment
   of P14).

- [ ] **Step 1:** Write the section. Lines at most 120 columns.
- [ ] **Step 2:** Check that no line outside a table or a code block passes 120 columns.
- [ ] **Commit** `docs(economy): record plans through the chain (rule A5)`.
