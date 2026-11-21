# The Opening's New Records, Carried Once: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** The market's receipt, the households' want and tier rows and the public program receipts are carried by the
tick's register, kept in the stored records, checked by every stored-record reader, shown in the reports, and put in
front of the player, with one new receipt format and one new storage domain.

**Architecture:** One receipt format, 23, appends four fixed-width families to format 22's 41. It is chosen whenever
the catalog has a market policy or the state has the public-program extension. One storage domain,
`BabylonReceiptStorageV6\0`, stores it inside today's byte budget. The tick finishes a period with staffing, so the
record of layoffs ages. The stored records learn three facts: a short market's price, a want order, a program payment.
The engine's small test worlds move into one test-support crate, so the tick and persistence test against the same
worlds the engine pins. Two client tasks show a price paid in a short market, a household's standard, its benefits,
and its layoff's two steps.

Checked once against the built engine by a second reader on 21 November 2026; its findings are in the tasks.

**Tech Stack:** Rust (`babylon-tick`, `babylon-persistence`, `babylon-client`; one constant in
`babylon-material-circuit`; a new unpublished crate `babylon-circuit-worlds`), Python devtools (`tools/devtools/`),
contracts under `contracts/`.

**Spec:** `docs/superpowers/specs/2026-11-20-the-opening-of-the-national-economy-design.md` (section 2, "What the
player sees"); `docs/superpowers/specs/2026-11-20-price-of-a-short-market-design.md`. What must be carried is
specified by: the price plan's Task 7 (`docs/superpowers/plans/2026-11-20-price-of-a-short-market.md`), the tiers
plan's last section (`docs/superpowers/plans/2026-11-20-opening-stage-3-tiers.md`, "What the later plan carries") and
the benefits plan's "Later plan A" (`docs/superpowers/plans/2026-11-20-opening-stage-4-benefits.md`). Read all five.

**Prerequisites:** the price plan's Tasks 1 to 6c, the tiers plan's Tasks 1 to 5 and the benefits plan's Tasks 1 to 5
are built. Interfaces this plan leans on, by plan and task:

| Interface | Defined in |
|---|---|
| `MarketClearingReceipt`, `MarketMoment`, `MaterialCircuitTransition.market_clearings`, `MaterialCatalog.market_clearing` | price, Tasks 2 and 3 |
| `HouseholdWantReceipt`, `HouseholdTierReceipt`, `WantTier`, `HouseholdStandard`, `household_standard`, `transition.household_wants`, `transition.household_tiers` | tiers, Task 3a |
| `recurring_household_want_order_id`, `recurring_service_want_order_id` | tiers, Task 3a |
| `MAX_HOUSEHOLD_WANTS = 262_144`; a purchase row for a want alone has target stock 0 | tiers, Task 2 |
| `PublicSpendingRule`, `PublicBudget.rule`, `MaterialCircuitState::has_public_program_extension`, state versions 25 and 26 | benefits, Task 1 |
| `MAX_TAX_POLICIES = 262_144`; tax key `(payer, basis, public_recipient)` | benefits, Task 2 |
| `PublicProgram`, `PublicProgramKey`, `PublicProgramTerms`, `PublicProgramReceipt`, `transition.public_programs`, `MAX_PUBLIC_PROGRAMS` | benefits, Task 3 |
| `LayoffRecord`, `FinancialInstitutions.layoffs`, `ClosedMaterialPeriod::finish_with_staffing` | benefits, Task 4 |

Every row was read in the built code at `13777bd84`. Ruling D of the lead: the engine's own scans that grow with the
square (the lists' opening and the tier sums in `tiers/`, the market table's lookups, the programs' dues) are fixed by
another small plan before this one is built; this plan does not edit the engine's `tiers/` or `clearing/`.

## Global Constraints

- Every line number is a hint, from `13777bd84`; find each place by its quoted text.
- Work only in `/media/user/dev-ssd/worktrees/households-homes/babylon`, branch `codex/households-and-homes`. Start
  every shell command with `cd` to it (or to its `rust/` directory). Never push. No secrets, no `.env`, no
  `babylon-data` on this disk.
- One cargo or pytest process at a time, on the whole machine. Never pass `-j` or `--jobs`.
- A run that outlasts one command goes to the background with a log and its own marker (`...; echo "exit=$?" >>
  <log>`), waited for on that marker, never on `real` (zsh's `time` prints `total`). Leave no shell running.
- **Scoped gate, run by every task before its last commit,** one leg at a time: from `rust/`, `mise exec -- cargo fmt
  --all -- --check`; `mise exec -- cargo clippy --workspace --all-targets --locked -- -D warnings -D
  clippy::cognitive_complexity`; the test binaries the task names with `mise run rust:test:q -- -p <crate> -E
  'binary(<name>)'`; `mise run rust:test:q -- -p <crate>` once for each crate the task changed; `mise run
  check:bsl-sentinels`. A task that changes Python runs `mise run test:q -- <its test files>`. The lead alone runs `mise
  run rust:check-no-docs`, after Task 6 and in Task 11.
- Commit one unit of work at a time: `git add <files>` then `PYTHONPATH=src mise exec -- git commit -q -F <message
  file>`; check that `git log --oneline -1` moved. The body ends with `Part of PER-371` (Task 3 also `Part of
  PER-370`) and a `Co-Authored-By` line naming the model that wrote the commit. Never commit `uv.lock`.
- **Bytes.** A world whose catalog has no market policy and whose state has no public-program extension keeps its
  receipt format (20, 21 or 22) and every byte: register, receipts, stored receipts, stored state. No pinned value of
  an existing test changes. If one must, stop and tell the lead.
- No floating point. Money is `i128` millionths of a dollar (`Currency`). Quantities and persons are `u64`.
- Every refusal is a typed error. No panic, no `unwrap` outside tests, no silent clamp. A reader that meets a row it
  cannot explain refuses it; it never skips it, unless the task names the skip.
- Money is conserved: every check that a task changes still requires each transfer to be explained once.
- Functions stay under 100 lines and under a cognitive complexity of 25. **No check this plan writes grows with the
  square of its rows:** a check across two families merges two sorted lists in one pass or builds one map and looks
  each row up once.
- **Words** (ruling A of the lead). A household line says it "got less than it asked in a short market", with the
  price paid against the posted one. "Priced out" is the market's own count only: `demand_at_quote - sold`.
- New code imports modules, not functions (`google-rust-style` in `check:bsl-sentinels`; its grandfather register is
  `rust/crates/bsl-lint/data/google_rust_style_macro_residual.txt`). Remove a register line when its import goes.
- **Contract digests.** `contracts/material_circuit_v4.yaml` changes with `MATERIAL_CIRCUIT_SOURCE_SHA256`
  (`rust/crates/babylon-material-circuit/src/wire/state.rs`) in the same commit.
  `contracts/committed_material_tick_v3.yaml`, `material_world_register_v7.yaml` and `nominal_material_world_v3.yaml`
  have no pinned digest in code (checked: `rg` finds no reader); the first gains format 23 and its storage domain; the
  other two name no receipt format and do not change. `tools/devtools/national_storage_qualification.py` pins family
  counts and limits; it changes with its test.
- Markdown is wrapped at 120 columns, headings at 80. Refer to the player as "they".

## Review Focus

1. **A world with a market policy and nothing short, no wants, no program.** Expected: format 23 with every new family
   empty, and every stored-record check passes as it does for format 22. Tests: Task 1
   `a_quiet_market_policy_writes_format_23_with_empty_families`; Task 2 round trip of an empty register.
2. **A short market whose restocking order was cut back by the route.** Expected: the procurement receipt keeps the
   sold quantity; the stored records read the refunds of the same order as its cancellation and accept the closing
   order. Test: Task 3 `a_restocking_order_cut_back_by_the_route_is_explained`.
3. **A want of a product the household does not need.** Expected: its hand-over, its payment and its handling are
   explained by its want row; no reader counts it as unmet need or as pantry stock. Tests in Tasks 4, 5a and 5b.
4. **A public body that is short.** Expected: the program receipt's unfunded part shows as a cut; the transfer that was
   made is explained by the receipt's `paid`; the County Review's account is untouched. Tests in Tasks 6 and 8.
5. **A layoff record that ends mid-period.** Expected: a household's report says the period its half pay halves and the
   period it ends, from the record and the program's terms, also for odd and even half periods. Test in Task 8.

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `rust/crates/babylon-circuit-worlds/` (new, unpublished) | The engine's small test worlds, shared by three crates' tests | 0 |
| `rust/crates/babylon-tick/src/material_world/receipt_format.rs` | Format 23: domain, version, widths, limits, maximum | 1 |
| `rust/crates/babylon-tick/src/material_world/opening_receipt.rs` (new) | The four families' row codecs and their own checks | 1 |
| `rust/crates/babylon-tick/src/material_world/register.rs` | The choice of format, the family table, encode, decode, the refusals | 1, 3, 4, 6 |
| `rust/crates/babylon-tick/src/material_world/financial_receipt.rs` | Program payments explained by their receipts | 6 |
| `rust/crates/babylon-tick/src/material_world/organizer_reports.rs` | Want orders left out of the organizer's reports | 4 |
| `rust/crates/babylon-tick/src/material_world/county_review.rs` | The review refuses an account that holds a program or cuts | 6 |
| `rust/crates/babylon-tick/src/material_replay.rs` | The staffed finish | 6 |
| `rust/crates/babylon-persistence/src/receipt_storage/{storage.rs, layout.rs}` | Domain V6, budget, header, row packing | 2 |
| `rust/crates/babylon-persistence/src/state_storage/{schema.rs, layout.rs}` | State versions 25 and 26 and their tail | 2 |
| `rust/crates/babylon-persistence/src/production_projection/` | Price, cancellation and want checks | 3, 5a |
| `rust/crates/babylon-persistence/src/{economic_flows, company_statements, qualification_audit}/` | Want orders as principals; the cut-back order in the trade audit | 3, 5b |
| `rust/crates/babylon-persistence/src/recorded_labor/` | Want hand-overs and service wants in the labor accounts | 5b |
| `rust/crates/babylon-persistence/src/observer_reader/{household.rs, site_procurement.rs}` | Household report; procurement reading | 3, 8 |
| `rust/crates/babylon-persistence/src/production_projection/prices/` | The market's figures beside the posted price | 3, 8 |
| `rust/crates/babylon-client/src/production/readings.rs` | The quote block shows the price paid and the count priced out | 9 |
| `rust/crates/babylon-client/src/money_map/household.rs` | Standard, tiers, benefits and the layoff's two steps | 10 |
| `contracts/committed_material_tick_v3.yaml`, `contracts/material_circuit_v4.yaml` | Format 23, domain V6, the market bound | 1, 2 |
| `tools/devtools/{national_storage_qualification.py, national_storage_snapshot.py}` | Domain V6 and 45 families | 2 |

---

### Task 0: One home for the small worlds

Ruling C of the lead. The worlds the later tests need are built only inside the engine's integration tests, which the
tick and persistence cannot import. The tick's tests build their own small states (`material_world/tests.rs`'s
`admission_control()`, `tests/support/county_review_fixture.rs`, `tests/staffed_material_replay/`), and persistence has
`src/test_support.rs`; none has a market policy, wants or a fund. The needed builders are not small: the goods fixture
is 586 lines, the service fixture 570, the restocking fixture 579, the small world 1,519. Writing them again would build
them twice, so they move, unchanged, into one crate (the plan's call).

**Files:**
- Create: `rust/crates/babylon-circuit-worlds/Cargo.toml` (`publish = false`, `[lints] workspace = true`,
  dependencies `babylon-kernel` and `babylon-material-circuit` by path, nothing else); `src/lib.rs` (modules and one
  crate-level `#![allow(..., reason = "test worlds: ...")]` for each pedantic lint that a library's `pub` items raise
  and test code did not, such as `clippy::missing_panics_doc` and `clippy::must_use_candidate`: only those clippy
  names)
- Move with `git mv`, `pub(crate)` becoming `pub`: `babylon-material-circuit/tests/market_clearing/support.rs` to
  `src/goods.rs`; `market_clearing/service_support.rs` to `src/services.rs`; `market_clearing/restock_support.rs` to
  `src/restock.rs` (their `use super::support;` becomes `use crate::goods as support;`); `tests/small_world/support.rs`
  to `src/small_world.rs`
- Modify: `rust/Cargo.toml` (`members` gains the crate: 14 members, under bsl-lint's `MAX_MANIFESTS` of 32);
  `babylon-material-circuit/Cargo.toml`, `babylon-tick/Cargo.toml`, `babylon-persistence/Cargo.toml`
  (`[dev-dependencies]` gains `babylon-circuit-worlds = { path = "../babylon-circuit-worlds" }`);
  `babylon-material-circuit/tests/market_clearing.rs` and `tests/small_world.rs` (each `#[path] mod support;` becomes
  `use babylon_circuit_worlds::goods as support;` and likewise for the other three; no glob import, which
  `wildcard_imports = "deny"` refuses); `rust/Cargo.lock`

**Decisions:**
1. **The cycle.** The engine dev-depends on a crate that depends on the engine; cargo allows it for dev-dependencies.
   Only the engine's integration tests (`tests/`) may use the crate: its unit tests (`src/`, `#[cfg(test)]`) would see a
   second copy of every engine type. The tick and persistence may use it from unit and integration tests.
2. **`Cargo.lock`** gains one `[[package]]` entry (`babylon-circuit-worlds`, depending on `babylon-kernel` and
   `babylon-material-circuit`) and the dev-dependency in three packages' lists; no external crate is added, so the lock
   is written offline (`mise exec -- cargo metadata --offline --format-version 1 > /dev/null` from `rust/`) and the
   `--locked` legs then pass. `deny.toml` allows path dependencies without a version (`allow-wildcard-paths`).
   bsl-lint's dependency check (`sfs_non_authorability.rs`) only refuses an engine crate that reaches
   `babylon-evidence`, which this crate does not. `tools/rust_test_report.py`'s `DEV_INTEGRATION_TARGETS` does not
   change: the crate has no tests.
3. **The worlds and their pinned figures** that later tasks use, each already pinned by an engine test:

| World | Builder | Figures the later tests rely on | Engine test that pins them |
|---|---|---|---|
| Short shelf | `goods::Fixture::new(240, &[$400, $600, $40,000])` | price 7_058_824; admitted 56, 84, 100; supply 240, demand at quote 300, bidders 3, served 3 | `market_clearing/households.rs` `a_short_shelf_raises_the_price_for_everyone` |
| Short utility | `services::ServiceFixture` | price 7_058_824 on rows admitting 56, 84, 100 | `services.rs` `a_short_utility_is_priced_in_its_stage` |
| Route cut back | `restock::Restock` | sold 100 at $100; closing `ordered` 40, `shipped` 40; reserved $10,000, refunded $6,000; supplier holds 60 | `restocking.rs` `what_the_route_cannot_carry_is_cancelled_and_refunded` |
| Goods wants | `goods::Fixture` with `household_wants` | want rows (50, 0), (50, 50), (50, 50); standards `GettingBy`, `Affluent`, `Affluent`; the outbid case's price 24_000_001 | `wants.rs` `a_comfort_buys_with_the_money_needs_do_not_use`, `a_comfort_outbids_a_poorer_need` |
| Service wants | `services::ServiceFixture` with `household_wants` | the $500 account's want row: requested 50, admitted 50 | `service_wants.rs` `a_utility_comfort_keeps_the_money_for_a_local_need` |
| The fund | `small_world::World::benefits()`, `run_driven` | `no_earner` 480_000_000 a period; a layoff of 2 owes 100, 100, 100, 100, 100, 100, 50, 0 dollars in periods 2 to 9 | `small_world/benefits.rs` |

- [ ] **Step 1: Record the engine's test list.** `mise run rust:test:q -- -p babylon-material-circuit -E
  'binary(market_clearing) | binary(small_world)' --list` (or the crate's documented listing form), saved beside the
  task's notes.
- [ ] **Step 2: Move the files, add the crate, write the lock.**
- [ ] **Step 3: Run** both binaries and the whole engine crate: the same tests pass with the same names and no pinned
  value moves; then the scoped gate (clippy on the new crate included).
- [ ] **Step 4: Commit** `test(material-circuit): share the small worlds with the tick and persistence`.

### Task 1: The frame of format 23

**Files:**
- Create: `rust/crates/babylon-tick/src/material_world/opening_receipt.rs` (with `#[cfg(test)] mod tests`)
- Modify: `receipt_format.rs` (variant, `OPENING_WIDTHS`, `identify` list, `row_limit`); `register.rs`
  (`company_receipt_format` at 1868, `receipt_families` at 1910, `encode_receipt_family_rows!` at 1692, the decoder's
  `try_reserve_exact` and row arms at 2294 and 2343, the `HouseholdLifecycle` tests at 2333 and 2596, the decoder's
  checks after 2613, `MaterialTickReceipts` at 2122); `src/material_world.rs` (module, re-exports); the 19 builders of
  `MaterialTickReceipts` (1 in `register.rs`, 18 in persistence and tick tests) get the four empty vectors
- Modify, engine: `rust/crates/babylon-material-circuit/src/model.rs` (`MAX_MARKET_CLEARINGS_PER_PERIOD` beside
  `MAX_HOUSEHOLD_WANTS`; the engine's `MarketTable` is not edited (ruling D): it cannot pass the bound by construction,
  and the tick's row limit refuses it at encode); `src/lib.rs` (re-export); `contracts/material_circuit_v4.yaml`
  (`limits`: `market_clearings_per_period: 131072 # one per offer at two moments`) and the digest
- Modify, contract: `contracts/committed_material_tick_v3.yaml` (a section `opening_receipts` after
  `household_lifecycle_receipts`)
- Test: `opening_receipt.rs` tests; `rust/crates/babylon-tick/src/material_world/tests.rs`

**Interfaces:**
- Produces:

```rust
// receipt_format.rs
pub enum MaterialReceiptFormat { Site, Company, HouseholdLifecycle, OpeningRecords }
// OpeningRecords: domain b"babylon.material-tick-receipts.v23\0", version 23, 45 widths.
impl MaterialReceiptFormat {
    /// The row limit of a zero-based family in this format. Equal to `receipt_row_limit(index)` except,
    /// under `OpeningRecords`, families 41 to 44 and the overrides of Task 1 decision 4.
    #[must_use] pub const fn row_limit(self, index: usize) -> usize;
}
// opening_receipt.rs
pub const MARKET_BYTES: usize = 169;
pub const WANT_BYTES: usize = 217;
pub const TIER_BYTES: usize = 73;
pub const PROGRAM_BYTES: usize = 165;
pub(crate) fn encode_markets(rows: &[MarketClearingReceipt], tick: u64, out: &mut Vec<u8>)
    -> Result<(), MaterialWorldError>;
pub(crate) fn decode_market(cursor: &mut ReceiptCursor<'_>, tick: u64)
    -> Result<MarketClearingReceipt, MaterialWorldError>;
// likewise encode_wants / decode_want, encode_tiers / decode_tier, encode_programs / decode_program
/// Order, keys and the rows' own `validate`; tier rows against want rows.
pub(crate) fn validate(markets: &[MarketClearingReceipt], wants: &[HouseholdWantReceipt],
    tiers: &[HouseholdTierReceipt], programs: &[PublicProgramReceipt]) -> Result<(), MaterialWorldError>;
// MaterialTickReceipts gains
pub market_clearings: Vec<MarketClearingReceipt>,
pub household_wants: Vec<HouseholdWantReceipt>,
pub household_tiers: Vec<HouseholdTierReceipt>,
pub public_programs: Vec<PublicProgramReceipt>,
// babylon-material-circuit
pub const MAX_MARKET_CLEARINGS_PER_PERIOD: usize = 2 * MAX_MATERIAL_CIRCUIT_ROWS; // 131_072
```

**Decisions (the plan's calls):**
1. **Name.** The price plan called the variant `MarketClearing`; it carries more, so it is `OpeningRecords`.
2. **The families**, after format 22's 41, each fixed width, big-endian, before the register's framing:

| Tag | Family | Fields, in order | Bytes | Key, strictly increasing | Row limit |
|---|---|---|---|---|---|
| 42 | market clearing | period `u64`, moment `u8`, site 32, good 32, unit 32, quote `i128`, clearing `i128`, supply `u64`, demand at quote `u64`, sold `u64`, bidders `u32`, served `u32` | 169 | (moment, site, good, unit) | 131,072 |
| 43 | household want | period `u64`, principal 32, tier `u8`, seller 32, good 32, unit 32, order 32, wanted `u64`, bought `u64`, posted `i128`, unit price `i128` | 217 | (principal, tier, good, unit) | 262,144 |
| 44 | household tier | period `u64`, principal 32, tier `u8`, wanted value `i128`, bought value `i128` | 73 | (principal, tier) | 131,072 |
| 45 | public program | period `u64`, account 32, key length `u8`, key 32 (zero padded), recipient 32, rank `u32`, covered `u64`, due `i128`, paid `i128`, unfunded `i128` | 165 | (key, recipient) | 65,536 |

3. **The program key is padded to 32 bytes** (the plan's call). The benefits plan wrote a variable key; every register
   family is fixed width and the storage transposes columns, so one variable family would need its own codec. The
   decoder refuses a length outside 1 to 32, a non-zero pad byte, and a key `PublicProgramKey::new` refuses
   (`MaterialWorldError::Wire`).
4. **Row limits.** Markets: every offer row (at most `MAX_MATERIAL_CIRCUIT_ROWS`) is a market at two moments at most
   (a good at the household moment and at restocking; a service at its one stage). Wants: `MAX_HOUSEHOLD_WANTS`.
   Tiers: two per cohort, cohorts at most 65,536. Programs: one per program and recipient, recipients of all programs
   at most `MAX_MATERIAL_CIRCUIT_ROWS`. Three overrides under format 23, for the rows wants and split taxes add:
   local fulfillments (index 7, today the default 65,536) `MAX_HOUSEHOLD_NEEDS + MAX_HOUSEHOLD_WANTS` = 393,216 (the
   national world with three goods wants an account has 29,320 need hand-overs and 43,980 want hand-overs, 73,300);
   handling (index 6, today 131,072, shared by deliveries and retail) `MAX_HANDLING_RECEIPTS_PER_PERIOD +
   MAX_HOUSEHOLD_WANTS` = 393,216; taxes (index 24) `MAX_TAX_POLICIES` = 262,144. Service performance (index 19,
   196,608) needs none: the engine refuses more at `services/admission.rs:734`, and the national world holds about
   43,980 household need rows, up to 118,881 business connections and one row a service want, about 177,521 with one
   service want an account, 19,087 under the bound (Task 11 measures it). Money transfers (1,441,792) gain two a
   goods want and one a paid program row, about 117,280 nationally; no override. `receipt_row_limit(index)` keeps its
   values, so the Site budget and the pinned storage bound do not move; the register's encoder and decoder call
   `format.row_limit`.
5. **The maximum** of format 23 is `MAX_MATERIAL_TICK_RECEIPT_BYTES`, 947,585,922, as for 21 and 22: the new families
   share the headroom, each with its own row limit (the contract's existing rule for families 38 to 41). The sum of
   the new families' limits times widths is 117,768,192 bytes (markets 22,151,168; wants 56,885,248; tiers 9,568,256;
   programs 10,813,440; the tax rows beyond 131,072, 18,350,080); no family's own limit alone passes the shared cap.
6. **The choice** (`company_receipt_format`): `OpeningRecords` when `catalog.market_clearing.is_some()` or
   `transition.state.has_public_program_extension()`, in every period, with or without rows; else today's rule. Under
   `OpeningRecords`: the lifecycle families may be empty when the state has no lifecycle book (`validate_close` still
   runs and must agree); the company families may be empty; the basis check runs as for 22. The staffing decoder
   (`workforce_receipt/codec.rs:58`) takes `from_living_force` under 22 and 23, which admits a force that `try_new`
   refuses; so after the decode loop, when the format-23 register's lifecycle family is empty, each staffing row's
   binding is checked again with `StaffingMemberBinding::try_new` from its own fields, and a refusal is `Wire`. A
   market world without a lifecycle book is then held to format 21's rule.
7. **Refusals stay** in this task, as built in `company_receipt_format`: the extension and programs together at
   1874 to 1876, the markets at 1900, the wants and tiers at 1905. A transition under a market policy with no row now
   encodes as format 23; one with rows is still refused. Tasks 3, 4 and 6 remove them; the extension refusal moves
   below the choice of format so that a state with the extension reaches format 23.
8. **The decoder's checks** of the new families run only under format 23, after the existing checks: each row's own
   `validate` (mapped to `Wire`), the keys, every row's period equal to the resolve tick, and the tier rows against the
   want rows. That last check is one merge pass over the two families, both sorted by `(principal, tier)`: for each
   tier row, the want rows of its key are summed as the cursor passes them; a want row with no tier row is refused. A
   register of format 20 to 22 decodes as today with the four vectors empty.
9. **Contract.** `opening_receipts`: version 23; activation "the catalog has a market policy or the closing state has
   the public-program extension"; domain; `family_count: 45`; the four families with tag, name, width,
   `maximum_rows`; `tax_receipts_maximum_rows: 262144`; `maximum_complete_bytes: 947585922` with the basis line of
   decision 5; `maximum_stored_bytes: 947588276`.

- [ ] **Step 1: Write the failing tests.** In `opening_receipt.rs`:
  - `a_market_row_round_trips_in_169_bytes`: the row (period 3, `HouseholdGoods`, site `[1;32]`, good `[2;32]`, unit
    `[3;32]`, quote 4_000_000, clearing 7_058_824, supply 240, demand at quote 300, sold 240, bidders 3, served 3)
    encodes to 169 bytes, byte 8 is `0x01`, and decodes equal.
  - `a_want_row_round_trips_in_217_bytes`, `a_tier_row_round_trips_in_73_bytes`,
    `a_program_row_round_trips_in_165_bytes` (key `"no_earner"`: byte 40 is 9, bytes 50 to 72 are 0).
  - `a_program_key_with_a_dirty_pad_or_bad_length_is_refused` (pad byte 1; length 0; length 33: each `Wire`).
  - `rows_out_of_key_order_are_refused` (two market rows swapped; two want rows of one key: `Wire`).
  - `a_tier_row_that_is_not_its_wants_sum_is_refused` (tier 2 wanted value 1 micro above the want rows' sum: `Wire`).
  In `material_world/tests.rs`:
  - `format_22_and_21_receipts_keep_their_bytes`: the SHA-256 of `encode_material_receipts` for the lifecycle
    fixture's first period and for `admission_control()`'s, printed at this task's base commit, pinned as literals.
  - `a_quiet_market_policy_writes_format_23_with_empty_families`: `admission_control()` with a market policy whose
    order of paying covers its household good and a seller whose posted price is pinned (price Task 6c); its first
    close encodes with `identify == Some(OpeningRecords)`, the length of the empty frame's header is `35 + 12 + 45 *
    9 = 452` plus the rows of today's families, and it decodes with the four vectors empty.
  - `a_format_23_register_with_a_truncated_or_overlong_family_is_refused`: drop the last byte (`Wire`); a family 42
    count of 131,073 (`ByteLimit`).
  - `the_new_row_limits_are_pinned`: `OpeningRecords.row_limit(41..=44)` are 131_072, 262_144, 131_072, 65_536;
    under `OpeningRecords` `row_limit(6)`, `row_limit(7)` and `row_limit(24)` are 393_216, 393_216 and 262_144, and
    under `HouseholdLifecycle` 131_072, 65_536 and 131_072;
    `OpeningRecords.widths()[41..]` is `[169, 217, 73, 165]`; `maximum_bytes()` is 947_585_922.
  - `a_market_world_without_a_book_keeps_the_strict_staffing_rule`: a format-23 register whose staffing row
    `try_new` refuses and whose lifecycle family is empty: `Wire`.
  - `a_market_refusal_is_in_place_until_task_3`: `a_short_shelf_raises_the_price_for_everyone`'s close (Task 0's
    short shelf) gives `Err(Wire)`; no tick test covered that refusal before (Task 3 inverts it).
- [ ] **Step 2: Run them and see them fail** (`-p babylon-tick -E 'test(opening_receipt) |
  test(material_world::tests)'`).
- [ ] **Step 3: Implement** the constant, the variant, the codecs, the choice, the decoder checks, and the four fields.
- [ ] **Step 4: Run** the tick's tests, then `-p babylon-material-circuit` and `-p babylon-persistence` (builders only).
- [ ] **Step 5: Commit** `feat(tick): frame receipt format 23 for the opening's records`.

### Task 2: Stored receipts in domain V6; stored states 25 and 26

**Files:**
- Modify: `rust/crates/babylon-persistence/src/receipt_storage/storage.rs` (`OPENING_DOMAIN =
  b"BabylonReceiptStorageV6\0"` in `storage_domain`, `storage_budget` and `decode_header`; `unpack_row` at 184 takes
  the canonical width from `OpeningRecords.widths()`, a superset whose first 41 widths are format 22's; `encode` and
  `restore_canonical` check counts with `format.row_limit(index)`); `src/receipt_storage/layout.rs` (`FIELDS_42` to
  `FIELDS_45` in `fields(tag)`); `src/state_storage/schema.rs` (`state` accepts versions 22, 24, 25, 26; `accounting`
  walks the tail); `src/state_storage/layout.rs` (`fixed!(47, 84, 131_072, ...)` at 196 to 201, `financial.taxes`,
  becomes 262_144); `src/test_support.rs`
- Modify: `tests/sql_material_bounds.rs` (a budget test for format 23; its import of `receipt_row_limit` is register
  line 110 of the style residual: keep that import as it is); `contracts/committed_material_tick_v3.yaml`
  (`storage_domains` gains `opening_receipt: "BabylonReceiptStorageV6\0"`; `receipt_storage` notes the program key's
  raw 33 bytes); `tools/devtools/national_storage_qualification.py` (`Literal[3, 4, 5, 6]` at 284 and its validator
  at 318; `{3: 37, 4: 39, 5: 41, 6: 45}` at 354; the company limits for 6; the V6 header at 393 to 399;
  `ECONOMIC_COVERAGE_SQL` at 33 to 43, decision 5); `tools/devtools/national_storage_snapshot.py` (the call at 133
  passes the third domain); `tests/unit/tools/test_national_storage_qualification.py` (the cases at 437, 594 to
  606, 2055 and 4464 to 4477 gain version 6)
- Test: `storage.rs` tests; `rust/crates/babylon-persistence/src/state_storage/tests.rs`

**Interfaces:**
- Consumes: Task 1's `OpeningRecords`, `row_limit`, the four codecs; benefits Task 1's version constants.
- Produces: no new public names. `IdentityKind` gains nothing: the program key is stored raw.

**Decisions (the plan's calls):**
1. **Identity fields of the new families** (interned 32-byte ids, offsets in the canonical row): 42 `[site 9, good 41,
   unit 73]`; 43 `[principal 8 (FinalDemandPrincipal), seller 41 (Site), good 73, unit 105, order 137 (Order)]`; 44
   `[principal 8]`; 45 `[account 8 (PublicAccount), recipient 73 (FinalDemandPrincipal)]`. Packed widths: 85, 77, 45,
   109. The numeric packing is the generic mode for all four.
2. **The budget passes nothing.** The stored record of a format-23 register at its maximum, raw: `24 + 88 + 45 x 59 +
   (947_585_922 - (35 + 12 + 45 x 9)) = 947_588_237`, under `MAX_STORED_MATERIAL_RECEIPT_BYTES` (947,588,276) by 39
   bytes. So `storage_budget(OpeningRecords)` is `MAX_RECEIPT_STORAGE_BYTES`, the SQL column bound and
   `migrations/current_schema.sql` do not change, and no migration is needed.
3. **The state's tail** (benefits Task 1 decision 4, Tasks 3 and 4 bytes). Under versions 25 and 26 only, the walker
   reads, after section 50 (`financial.contributions`), one variable section, id 75: a `u32` budget count equal to
   section 48's count and one rule byte each (1 or 2); a `u32` program count (at most 256), each program its key
   length `u8` (1 to 32) and key, payer 32, rank `u32`, tag `u8` (1: `i128`; 2: two `u16`), a `u32` recipient count
   and 32 bytes each (all programs' recipients at most 65,536); a `u32` record count (at most 131,072), each member
   32, hours `u64`, a `u8` cohort count (1 to 13) and `u64` cohorts. Section 75 is kept raw, not interned. Version 26
   also walks the lifecycle section as 24 does. A tail under 22 or 24, or a missing tail under 25 or 26, is
   `StorageError::Framing`. The state storage domain stays `babylon.state-storage.v4\0`. Verify the tail's place
   against the built `wire/financial.rs` before writing the walker; if it is elsewhere, follow the code and say so.
4. **Tax rows** keep their 84-byte state row; only the bound rises (benefits Task 2), at layout id 47.
5. **The company books' coverage.** `ECONOMIC_COVERAGE_SQL` requires a company accounting row exactly when the stored
   receipts are V4 or V5. A company book is written when the catalog has company payouts
   (`money_journal/company_books/source.rs:91`), which format 23 does not imply. So it takes a third domain parameter:
   a V6 period may have the row or not, and when it has one its world hash must agree, as today.

- [ ] **Step 1: Write the failing tests.** In `storage.rs`:
  - `opening_receipts_round_trip_with_every_new_family`: a format-23 register with two rows in each new family encodes
    under `BabylonReceiptStorageV6\0` and restores the exact canonical bytes; the lookup grows by the new identities.
  - `an_empty_format_23_register_restores_exactly`: header 2,767 bytes (`24 + 88 + 45 x 59`) plus the empty payloads.
  - `a_v6_package_with_a_dirty_program_pad_refuses`: flip one pad byte in the restored body: `Error::Canonical`.
  - `earlier_domains_restore_as_today`: the existing V3, V4 and V5 fixtures' stored bytes, SHA-256 pinned at this task's
    base commit, encode and restore unchanged. In `tests/sql_material_bounds.rs`,
    `opening_receipts_fit_the_physical_budget_without_compression`: version 23, `widths()[41..] == [169, 217, 73, 165]`,
    and the raw package of decision 2 is at most the stored maximum. In `state_storage/tests.rs`:
    `a_state_of_version_25_and_26_is_stored_and_read_back` (Task 0's `World::benefits()` state after one close, and its
    lifecycle variant: walk, store, restore equal bytes); `a_tail_under_version_22_is_refused`;
    `a_tax_section_of_262144_rows_is_admitted_and_one_more_refused`. In the Python test:
    `test_v6_receipt_package_counts_45_families` (minimum header `len(b"BabylonReceiptStorageV6\0") + 88 + 45 * 59 ==
    2767`, limits 947,585,922 and 947,588,276); `test_v6_coverage_admits_a_period_without_company_books`.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `-p babylon-persistence`, `binary(sql_material_bounds)`, and `mise run test:q --
  tests/unit/tools/test_national_storage_qualification.py`.
- [ ] **Step 5: Commit** `feat(persistence): store receipt format 23 and the public-program state`.

### Task 3: The market's receipt reaches the stored records

The price plan's Task 7 is this task's specification; the frame and the storage are Tasks 1 and 2.

**Files:**
- Modify, tick: `register.rs` (remove the refusal "if !transition.market_clearings.is_empty()" at 1900, inverting
  Task 1's `a_market_refusal_is_in_place_until_task_3`; refuse market rows under a catalog without a market policy)
- Modify, persistence: `src/production_projection/lifecycle/period.rs` (`admit_households` near 175, `admit_firms`
  near 288, the order replay and `reconcile` near 499); `src/production_projection/lifecycle/services.rs` (`requests`
  near 104 and 167); `src/production_projection/prices/projection.rs` (near 86) and `prices/flows.rs` (`waiting`, 128
  to 160); `src/observer_reader/site_procurement.rs` (`new_goods_orders`, the check `order.ordered !=
  row.admitted_quantity` near 251); `src/qualification_audit/trade.rs` (`reconcile`, 370 to 393: `Reservation` and
  `Refund`)
- Test: `rust/crates/babylon-tick/tests/` beside `service_receipt_wire.rs` (new `market_receipt_wire.rs`);
  persistence's projection tests (`src/production_projection/events_tests.rs` and the lifecycle tests)

**Interfaces:**
- Produces, persistence (`production_projection`):

```rust
/// The price every order of one market paid this period: its row's clearing price, else `None`
/// (the posted price applies).
pub(crate) struct ClearedPrices { /* one BTreeMap keyed (moment, site, good, unit); one lookup a row */ }
impl ClearedPrices {
    pub(crate) fn new(rows: &[MarketClearingReceipt]) -> Self;
    pub(crate) fn expected(&self, moment: MarketMoment, site: SiteId, good: GoodId, unit: UnitId,
        posted: Currency) -> Currency;
    /// Demand at the quote less what was sold, over every moment of this seller's product.
    pub(crate) fn priced_out(&self, site: SiteId, good: GoodId, unit: UnitId) -> Result<u64, ProductionProjectionError>;
}
```

**Decisions:**
1. **The expected price** (decided point 6). Household demand (`HouseholdGoods`, retailer), procurement
   (`Restocking`, supplier), a service request (`Utility` or `LocalService`, provider; a provider's product is in one
   stage, so the check takes whichever of the two rows exists) and a want row (Task 5a) each expect
   `ClearedPrices::expected`. All orders of one market in one period carry one price. A price that neither the posted
   offer nor a row explains is refused as today.
2. **The unserved quantity** that `prices/projection.rs` recomputes adds `priced_out` for the seller's product, as the
   engine's `update_prices` does (price Task 6, decision 1).
3. **The cut-back restocking order** (price Task 5, decision 6, the known wrinkle). The procurement receipt keeps the
   quantity sold; the unsent part is refunded within the period. The stored records read it so: for a restocking
   order made this period, `cancelled = refunded amount / unit_price` over the refund transfers of
   `OutboundOrderId::Delivery(order)` in the period (an amount that is not a whole number of units is refused); the
   replayed order row's `ordered` is `admitted - cancelled`, which must equal `shipped` when `cancelled > 0`; when
   `cancelled == admitted` the order leaves no closing row and its escrow is retired. Without a market policy
   `cancelled` must be 0, as today. `site_procurement.rs` applies the same rule: `order.ordered + cancelled ==
   admitted_quantity`, and a missing closing row is valid when `cancelled == admitted_quantity`. The trade audit
   (`trade.rs`) takes the same `cancelled`: the reservation it expects is the value of `remaining - cancelled`, and
   the refund it expects is the value of `lost + cancelled`.
4. A market row under a catalog without a market policy is refused at encode (`Wire`).

- [ ] **Step 1: Write the failing tests.** In `market_receipt_wire.rs`:
  `two_market_rows_round_trip_through_the_register`
  (price plan Task 3's `a_short_shelf_raises_the_price_for_everyone` closed and encoded: one row decodes equal);
  `market_rows_without_a_market_policy_are_refused`. All worlds are Task 0's. In persistence:
  `a_period_with_a_cleared_market_is_projected` (that period through `lifecycle::join`: accepted; the demand rows'
  `unit_price` 7_058_824);
  `a_price_no_market_row_explains_is_refused` (one demand row's price raised by 1 micro:
  `ProductionProjectionError::State`);
  `a_cleared_service_price_is_accepted` (price Task 4's `a_short_utility_is_priced_in_its_stage`);
  `priced_out_buyers_count_as_unserved` (the price projection's `unserved_quantity` for the shelf is 60 = 300 - 240);
  `a_restocking_order_cut_back_by_the_route_is_explained` (price Task 5's
  `what_the_route_cannot_carry_is_cancelled_and_refunded`: projected; closing `ordered` 40; the site procurement reading
  shows 100 sold, 60 cancelled; the trade audit of the period passes);
  `an_order_wholly_cancelled_leaves_no_row_and_is_accepted`;
  `a_refund_that_is_not_whole_units_is_refused`.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement,** and remove the refusal.
- [ ] **Step 4: Run** `-p babylon-tick`, `-p babylon-persistence`.
- [ ] **Step 5: Commit** `feat(tick): carry the market's receipt into the stored records`.

### Task 4: Wants and tiers in the register and the tick's reports

**Files:**
- Modify: `register.rs` (remove the want and tier refusal at 1905; cross-checks at encode and decode);
  `opening_receipt.rs` (`validate_want_orders`); `organizer_reports.rs` (`food()` about 121 to 214, `service()` about
  254 to 310, `money()` at 51); `rust/crates/babylon-practice-contract/src/organizer/partner_reports.rs` (no field
  changes; its tests gain a case)
- Test: `material_world/tests.rs` (the refusal tests at 867 and 892 become round trips); the organizer report tests

**Interfaces:**
- Produces:

```rust
/// Every hand-over, handling row, transfer and performance row under a want order id is explained by
/// its want row: seller, product, bought quantity and unit price agree.
pub(crate) fn validate_want_orders(wants: &[HouseholdWantReceipt], fulfillments: &[LocalRetailFulfillmentReceipt],
    performance: &[ServicePerformanceReceipt], transfers: &[MoneyTransferReceipt]) -> Result<(), MaterialWorldError>;
```

**Decisions:**
1. **What a want adds** (tiers plan, last section): for a goods want, `local_fulfillments`, `handling` and
   `money_transfers` (`LocalFinalDemand(want id)`); for a service want, `service_performance` (no `household_services`
   partner) and `money_transfers` (`Service(want id)`). A want row with `bought > 0` has exactly these and they agree
   with it; a want row with `bought == 0` has none (`Wire` otherwise). The check builds one map from order id to want
   row and looks each fulfillment, handling, performance and transfer row up once. The goods want's
   order id is `recurring_household_want_order_id`, the service want's `recurring_service_want_order_id`; the want
   row's `order_id` names it.
2. **The organizer's reports leave want orders out.** `food()` skips a hand-off, and `money()` a transfer, whose order
   id is in the set of want order ids, built once; `service()` sums performance only over rows outside that set. A want
   is consumption above needs, not provision the organizer can claim.
3. Every period of a catalog with wants writes both vectors (tiers Task 3a, decision 4); the encoder requires a tier
   row for every cohort and tier when the catalog has any want.

- [ ] **Step 1: Write the failing tests.** `a_period_with_wants_round_trips` (Task 0's goods wants closed and encoded:
  decoded want and tier rows equal the transition's); `a_hand_over_under_an_unknown_want_id_is_refused`;
  `a_want_row_bought_without_its_transfer_is_refused`; `a_service_want_round_trips_without_a_household_row` (Task 0's
  service wants); `the_food_report_leaves_wants_out` (the same close with and without wants gives equal
  `ReportRetailHandoff` lists); `the_service_report_leaves_wants_out`.
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement,** and remove the refusal.
- [ ] **Step 4: Run** `-p babylon-tick`, `-p babylon-practice-contract`.
- [ ] **Step 5: Commit** `feat(tick): carry households' wants and tiers in the register`.

### Task 5a: Want orders in the production projections

**Files:**
- Modify, persistence `production_projection/`: `lifecycle/period.rs` (`admit_households` reads purchase rows at 139;
  `add_movements` at 354; `purchase_amounts` at 693; `advance_purchase` at 737); `lifecycle/services.rs` (`admit` at 23,
  purchase rows at 199); `outbound.rs` (`final_facts`, 198); `events.rs` (199); `merchants.rs` (198; 264 display only);
  `prices/flows.rs` (64); `households/{projection.rs, services.rs}` (213, 73); `services.rs` (`validate`, 65 to 90 and
  208 to 225)
- Test: the projection tests beside each file, on Task 0's goods and service wants

**Interfaces:**
- Produces, persistence:

```rust
/// The period's want orders, by order id (one BTreeMap): principal, seller, product, bought, unit price.
pub(crate) struct WantOrders { /* from MaterialTickReceipts.household_wants with bought > 0 */ }
impl WantOrders {
    pub(crate) fn new(rows: &[HouseholdWantReceipt]) -> Self;
    pub(crate) fn get(&self, order: OrderId) -> Option<&HouseholdWantReceipt>;
}
```

**Decisions:**
1. **A want order is an order of one period** (decided point 6: a household's order that no need explains and no
   unmet need counts). `lifecycle::join` opens a final order for each goods want row with `bought > 0` (ordered and
   fulfilled = bought, price = unit price, escrow made and retired in the period) beside the orders it opens from
   demand rows; `add_movements`, `purchase_amounts`, `outbound`, `events`, `merchants` and `prices/flows` then find it
   as any final order. Its unit price is checked by Task 3's `ClearedPrices`; its `posted_price` must equal the offer.
   It reaches no pantry: `households/projection.rs`'s `received_stock` keeps skipping it.
2. **A service want** is a generated request of `lifecycle/services.rs::admit` under its want order id, with
   `requested` as the performance row's and the price of Task 3. `services.rs::validate` sums `grants` and `used` per
   buyer and product over every performance row and compares them with the household service row, which counts needs
   only: a performance row whose order id `WantOrders` holds is left out of those two sums, and its own used quantity
   must equal its performed quantity (tiers Task 4a, decision 6).
3. **Purchase rows read as needs.** A purchase row whose product is no need of the account (target stock 0) is skipped
   by `admit_households` (no demand row is expected), `households/projection.rs:213`, `households/services.rs:73` and
   `lifecycle/services.rs:199` (no need request). `merchants.rs:264` shows it. `national_economy/opening/markets.rs`
   160 and 392 write rows and do not change.
4. **Settled safe, by reading:** `material_balance/balance.rs:561-580` adds every hand-over to the retailer's
   `final_demand_fulfilled`, which is right for a want: the goods leave the retailer's stock. A test pins it.

- [ ] **Step 1: Write the failing tests:** `a_period_with_goods_wants_is_projected` (accepted; each pantry closes as
  without wants); `a_period_with_service_wants_is_projected` (an account that needs and wants one service: accepted);
  `a_want_paid_at_a_price_no_market_explains_is_refused`; `a_want_of_a_good_not_needed_expects_no_demand_row`;
  `the_retailers_material_balance_counts_want_hand_overs` (`final_demand_fulfilled` 400: needs 300, wants 100).
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement.** **Step 4: Run** `-p babylon-persistence`.
- [ ] **Step 5: Commit** `feat(persistence): explain want orders in the production projections`.

### Task 5b: Want orders in the labor accounts, the money flows and the audits

**Files:**
- Modify, persistence: `recorded_labor/circulation.rs` (212 to 235); `recorded_labor/services/close.rs` (120 to 130);
  `economic_flows/principals.rs` (77); `economic_flows/payments.rs` (100); `company_statements/cash.rs` (28);
  `qualification_audit/aid/reports.rs` (`Payments::new` 254, `handoff_price` 315, `food` 352);
  `qualification_audit/production_renewal.rs` (476, 683); `organizer_runtime/material_preview.rs` (355)
- Test: beside each file, on Task 0's wants

**Interfaces:**
- Consumes: Task 5a's `WantOrders`.

**Decisions:**
1. **Labor accounts.** `circulation.rs` credits a hand-over to the household's pantry node whenever a stock row exists;
   a hand-over whose order id `WantOrders` holds goes to `LaborDisposition::FinalDemandOutlay` and releases its basis,
   as an untracked one does today. `services/close.rs` leaves want performance rows out of the household node's
   totals, as Task 5a decision 2 (else `ReceiptMismatch("service use")`); a want row's use goes to the outlay.
2. **Principals and payments.** `principals.rs` binds a want order's escrow principal from its row; `payments.rs`,
   `company_statements/cash.rs` and `qualification_audit/aid/reports.rs` then accept its transfers.
3. **Audits.** `production_renewal.rs` counts a want hand-off as `want_household`, beside `other_household`, and skips a
   want-only purchase row at 683; `material_preview.rs:355` shows no preview line for one. Settled safe by reading:
   `qualification_audit/economic.rs` indexes hand-overs (123 to 131) and payments by order and reads only the keys of
   demand rows (392 to 420, 453 to 466), so want rows are indexed and never asked for. A test pins it.

- [ ] **Step 1: Write the failing tests:** `a_want_hand_over_is_final_demand_outlay_in_the_labor_accounts`;
  `a_service_want_leaves_the_household_service_totals_as_without`; `want_transfers_have_principals` (the flows reading
  counts the want payment once); `the_renewal_audit_counts_wants_apart` (`want_household` 1, `other_household` 0);
  `the_preview_shows_no_line_for_a_want_alone`; `the_economic_audit_passes_a_period_with_wants`.
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement.** **Step 4: Run** `-p babylon-persistence`.
- [ ] **Step 5: Commit** `feat(persistence): explain want orders in the labor accounts and audits`.

### Task 6: Public programs in the tick

**Files:**
- Modify: `rust/crates/babylon-tick/src/material_replay.rs` (353: `finish_with_staffing` with
  `effects.member_receipts()`); `register.rs` (remove the refusal at 1874 to 1876); `financial_receipt.rs` (`validate`
  at 271: expected postings gain each program receipt's `paid` under the key `(1, Public(account),
  Household(recipient))`); `county_review.rs` (`validate_world`, called at `register.rs:498`)
- Modify, persistence test support: `tests/support/household_accounts.rs` (the sum of every tax row near 380 to 397)
- Test: `material_world/tests.rs` (the refusal tests at 911 and 938 become round trips); beside the county review
  tests, on `tests/support/county_review_fixture.rs`; `tests/staffed_material_replay/` given Task 0's fund

**Interfaces:**
- Consumes: `finish_with_staffing(self, catalog, next_labor, member_labor, members: &[StaffingMemberReceipt])`
  (benefits Task 4).
- Produces: `CountyReviewRegisterError::ProgramAccount`.

**Decisions:**
1. **The staffed finish** (decided point 4). The replay always calls `finish_with_staffing`; with no after-layoff
   program it equals `finish_with_workforce` (benefits Task 4, decision 6), so every pinned replay holds. The line
   that sets `transition.staffing_members` stays.
2. **`prepare_next` already refuses** a state that holds an after-layoff program: it reaches
   `advance_material_circuit`, which calls `refuse_without_record_of_layoffs` (`transition/state.rs:997-1004`), and the
   error arrives as `MaterialWorldError::Circuit(PublicProgramInvariant)` (`register.rs:334-337`). Nothing is added; a
   test pins it.
3. **Money** (decided point 6, a program receipt explains a public transfer). Only `financial_receipt::validate`
   explains a `PublicTransfer` by a receipt (checked: `monetary_receipt.rs`, `money_journal`,
   `site_financial_statements/projection.rs` and `observer_reader/household.rs` classify it and explain nothing, so
   the benefits plan's list in "Later plan A" item 4 is three items too long). A program row with `paid > 0` adds to
   the expected totals; one with `paid == 0` adds nothing.
4. **Tax order** is already `(payer, basis, public_recipient)` in every format (`financial_receipt.rs:289`); only
   the row limit changes, in Task 1.
5. **The County Review** (decided point 5). `validate_world` refuses, with `ProgramAccount`, a register whose review
   account's budget has `rule != CappedInOrder` or is the payer of any program. An account with neither works as
   today. `group_facts` already counts only the review account's tax rows; `household_accounts.rs` is filtered the
   same way.
6. The `public_programs` family must be non-empty in every period of a state with a program (benefits Task 3,
   decision 4): the encoder refuses a state with a program and no receipt.

- [ ] **Step 1: Write the failing tests.** `a_program_period_round_trips` (Task 0's `World::benefits()`: one close,
  format 23, its program receipt decodes equal); `a_program_payment_without_its_receipt_is_refused` (drop the receipt,
  keep the transfer: `Wire`); `prepare_next_refuses_a_world_with_an_after_layoff_program`
  (`MaterialWorldError::Circuit(PublicProgramInvariant)`); `the_replay_ages_the_record_of_layoffs` (a staffed replay
  with one separation: the closing state's record is `[1]`, and in a second period `[0, 1]`);
  `the_county_review_refuses_an_account_with_a_program` and `..._that_cuts_in_proportion` (`ProgramAccount`);
  `the_county_review_without_a_program_is_unchanged` (the fixture's review facts, payments and county receipts equal the
  values before this task).
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement,** and remove both refusals.
- [ ] **Step 4: Run** `-p babylon-tick` (every county review and staffed replay test unchanged), then
  `-p babylon-persistence`.
- [ ] **Step 5: Commit** `feat(tick): carry public programs and finish each period with staffing`.

### Task 7: Public programs in the stored records

**Files:**
- Modify, persistence: `src/organizer_runtime/county_review.rs` (`projection` at 158: refuse an account the tick
  refuses, as Task 6 decision 5, with `RuntimeSessionErrorCode::OrganizerRefused`, the code it returns today for an
  organizer it cannot serve); `src/site_financial_statements/projection.rs` (the public
  transfer category, about 227 to 300); `src/money_journal/model.rs` (285, no change of rule: a test only)
- Test: beside each file, without PostgreSQL: Task 0's fund closed twice, its receipts stored and restored through
  `receipt_storage` (Task 2) and read by the readers in memory

**Decisions:**
1. A stored program period is restored and re-admitted by Task 1's decoder (Task 2 stores it); this task proves the
   readers above it accept it. A household's public income in the site statements and the money journal counts
   standing support and program payments together, as `PublicTransfer` already does.
2. The organizer's County Review projection refuses what the tick refuses, so the client never opens a review the
   tick would not run.

- [ ] **Step 1: Write the failing tests:** `a_stored_program_period_is_read_back` (two closes of Task 0's fund stored
  and restored; the money journal balances; the site statements' public income of the supported account is 640_000_000
  per period, as the small world's derivation in benefits Task 3, decision 6);
  `the_county_review_projection_refuses_a_program_account`.
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement.** **Step 4: Run** `-p babylon-persistence`.
- [ ] **Step 5: Commit** `feat(persistence): read public programs back from the stored records`.

### Task 8: The reports

**Files:**
- Modify: `rust/crates/babylon-persistence/src/observer_reader/household.rs` (`HouseholdPeriodReport` and its reader at
  179 and 201); `src/production_projection/prices/{model.rs, projection.rs}` (`CompletedGoodsPrice`)
- Test: beside each

**Interfaces:**
- Produces:

```rust
// HouseholdPeriodReport: `version` rises by one; new fields
pub standard: Option<HouseholdStandard>,          // None when the period has no tier rows
pub tiers: Vec<HouseholdTierUse>,                 // tiers 2 and 3, empty without wants
pub benefits: Vec<HouseholdBenefit>,              // one per program that names the household
// HouseholdGoodUse and HouseholdServiceUse gain
pub posted_price_micros: String,
pub price_paid_micros: Option<String>,            // Some when its market has a row this period
pub short_market: bool,                           // its market had a row and it bought less than it asked
pub struct HouseholdTierUse { pub tier: u8, pub wanted_micros: String, pub bought_micros: String }
pub struct HouseholdBenefit {
    pub program: String, pub public_payer: String, pub covered_persons: u64,
    pub due_micros: String, pub paid_micros: String, pub cut_micros: String,  // cut = unfunded
    pub wage_share_bps: Option<u16>,              // the after-layoff program's share; None per person
    pub layoff_steps: Vec<LayoffStep>,
}
/// One cohort of the household's laid-off people, read from the closing state's record and the program's terms.
pub struct LayoffStep { pub persons: u64, pub full_through_period: Option<u64>, pub half_in_period: Option<u64>,
    pub ends_after_period: u64 }
// CompletedGoodsPrice gains
pub market: Option<CompletedMarket>,
pub struct CompletedMarket { pub moment: u8, pub quote_micro: i128, pub clearing_micro: i128, pub supply: u64,
    pub demand_at_quote: u64, pub sold: u64, pub bidders: u32, pub served_bidders: u32 }
```

**Decisions (the plan's calls):**
1. **The standard** is `household_standard` (tiers Task 3a) of the account's rows; `None` without tier rows, because
   the four standards are read from tiers; the existing unmet lines still show going without.
2. **A short market** (ruling A). A household's line is marked `short_market` when its market has a row and it bought
   less than it asked; the receipts carry no household's demand at the posted price, so no household is called priced
   out. "Priced out" is the site's count: `demand_at_quote - sold` (Task 9).
3. **The layoff's two steps.** For each record of a staffing member whose payee is the household, under an after-layoff
   program with `H` half periods, and for each cohort at index `k` of the closing state's record, after period `P`: the
   program's full rate (`wage_share_bps` of pay) is due in each period from `P + 1` while `k + j < H / 2` (`j` periods
   on), half that rate in the period where `k + j == H / 2` when `H` is odd, nothing after. `full_through_period` is
   `None` when no full period is left; `half_in_period` is `None` when `H` is even or the half period has passed.
4. A program with `paid < due` shows the difference as `cut_micros`, the benefit cut of section 2.

- [ ] **Step 1: Write the failing tests.** `a_household_report_shows_its_standard_and_tiers` (Task 0's goods wants,
  account 1: `GettingBy`, tier 2 (200_000_000, 0)); `a_household_report_marks_a_short_market` (the outbid case, account
  0: posted 4_000_000, paid 24_000_001, `short_market` true; account 2: `short_market` false);
  `a_report_without_wants_has_no_standard`; `a_benefit_shows_due_paid_and_cut` (Task 0's fund with its cash at 0: due
  480_000_000, paid 0, cut 480_000_000); `a_layoff_shows_its_two_steps` (benefits
  `a_layoff_is_paid_half_pay_for_six_and_a_half_periods`, after period 1: one step, persons 2, full through 7, half in
  8, ends after 8; after period 7: full `None`, half in 8; `wage_share_bps` 5,000);
  `an_even_term_has_no_half_period` (H = 12, after period 1: full through 7, half `None`, ends after 7);
  `a_completed_price_carries_its_market` (Task 0's short shelf: clearing 7_058_824, demand 300, sold 240).
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement.** **Step 4: Run** `-p babylon-persistence`.
- [ ] **Step 5: Commit** `feat(persistence): report standards, prices paid and benefits`.

### Task 9: The client shows a price paid in a short market

**Files:**
- Modify: `rust/crates/babylon-client/src/production/readings.rs` (`describe_prices`, 807 to 856);
  `src/money_map/household.rs` (`provisioning`, about 219)
- Test: beside each (the client's reading tests)

**Decisions:**
1. In the site's quote block, a good whose completed price has a market shows one line under the price: "Short market:
   paid $X a unit against $Y posted; N of M buyers served; Q units priced out" (`Q = demand_at_quote - sold`).
2. In the household panel's goods and services lines, a `short_market` line adds "got less than it asked in a short
   market: paid $X (posted $Y)".
3. **Money on these two lines** is shown to the nearest cent, half away from zero, by a new
   `human_numbers::cents(micros: i128) -> String` (`$7.06`, `$24.00`, `$4.00`, `-$7.06`). The lead's call: a player
   reads a price, not a millionth. Every other price in the client keeps `human_numbers::currency`, and the reports
   of Task 8 keep the exact amounts.
4. Nothing changes for a good without a market.

- [ ] **Step 1: Write the failing tests:** `cents_round_to_the_nearest_cent` (7,058,824 millionths read "$7.06";
  24,000,001 read "$24.00"; 4,995,000 read "$5.00"; 4,994,999 read "$4.99"; -7,058,824 read "-$7.06"; 1,234,567,890,000
  read "$1,234,567.89"); `a_short_market_line_reads_its_figures` (the Task 8 fixture: "paid $7.06 a unit against $4.00
  posted; 3 of 3 buyers served; 60 units priced out"); `a_short_market_household_line_reads_its_price` ("got less
  than it asked in a short market: paid $24.00 (posted $4.00)"); `a_good_without_a_market_reads_as_before` (the
  quote block's text equals the text before this task).
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement.** **Step 4: Run** `-p babylon-client`.
- [ ] **Step 5: Commit** `feat(client): show the price paid in a short market`.

### Task 10: The client shows a household's standard, benefits and layoff

**Files:**
- Modify: `rust/crates/babylon-client/src/money_map/household.rs` (`sections` at 381, `support_and_time` at 304)
- Test: beside it

**Decisions:**
1. The panel's first line after the household's name reads its standard ("Going without", "Getting by",
   "Comfortable", "Affluent"); without one (a world without wants, ruling B), nothing is added. Under it, comforts and
   luxuries as "wanted $X, bought $Y".
2. Each benefit reads "program: due $X, paid $Y" and, when cut, "cut $Z". A layoff step reads "N laid off: R% of pay
   through period A, R/2% in period B, ends after period C", dropping the parts that are `None`; `R` is
   `wage_share_bps / 100` and `R/2` is `wage_share_bps / 200`, each shown with at most two decimals, half up, with
   trailing zeros trimmed (5,000 gives "50%" and "25%"; 3,333 gives "33.33%" and "16.67%"). The lead's call.

- [ ] **Step 1: Write the failing tests:** `the_standard_heads_the_panel`; `a_cut_benefit_reads_its_cut`;
  `a_layoff_reads_its_two_steps` (Task 8's fixture: "2 laid off: 50% of pay through period 7, 25% in period 8, ends
  after period 8"); `a_share_of_3333_points_reads_to_two_decimals`; `a_household_without_new_records_reads_as_before`.
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement.** **Step 4: Run** `-p babylon-client`.
- [ ] **Step 5: Commit** `feat(client): show a household's standard, benefits and layoff`.

### Task 11: Prove the untouched worlds, and measure the national one

Run by the lead.

- [ ] **The untouched worlds.** These must pass unchanged after Task 10: `tick_goldens.rs` (world hashes);
  Task 1's `format_22_and_21_receipts_keep_their_bytes`; Task 2's `earlier_domains_restore_as_today`;
  `sql_material_bounds.rs`'s two existing tests; `national_company_replay.rs` (the shipped world still identifies as
  `HouseholdLifecycle`); `receipt_storage`'s V3 to V5 tests; the County Review tests; the small world's
  `quiet.rs`, `pushed.rs`, `tiers.rs`, `benefits.rs` figures.
- [ ] **The national world's size.** The shipped world has none of the new records until the rebuilt opening (price Task
  8, benefits later plan B). Estimates from the contract's measured counts (87,960 need rows, six needs a household
  account: about 14,660 accounts; 76,327 tax rows), raw and before storage compression, per period, with three goods
  wants an account: markets at most 22,151,168 bytes (all 131,072 short); want rows 9,543,660 (31,812,200 at ten); tier
  rows 2,140,360; program rows about 4,837,800 (two an account); the split tax rows 10,685,780; the rows wants add to
  other families, a hand-over 168, a handling row 97 and two transfers of 50 for each of 43,980 goods wants, 16,052,700;
  program payments, 50 bytes each, 1,466,000. In all 66,877,468 raw; after interning about 34,352,948, against
  `maximum_tick_growth_bytes` 40,000,000 in `contracts/national_storage_qualification_v6.json`. Service performance
  would hold about 177,521 of its 196,608 rows (Task 1 decision 4). When the rebuilt opening lands, run the ignored
  `national_storage_encoded_measurement.rs` on PostgreSQL for 13 periods; if growth passes 40,000,000, stop and tell the
  Director's lead before any shipped world asks for wants.
- [ ] **Read a slow run rightly** (ruling D). Until the other plan lands, the engine's own scans grow with the square:
  the lists' opening and the tier sums of its records (`tiers/lists.rs`, `tiers/records.rs`), the market table's
  lookups (`clearing/table.rs`: `has_row`, `priced_out`, `demand_at_quote` walk every row), and the programs' dues
  (`financial/programs.rs`). A slow national close is first checked against those, not this plan's checks.
- [ ] Play Wayne for 12 periods in the real client on a fixture world with a market policy, wants and the fund (until
  the rebuilt opening, Wayne's shipped world shows none of the four things), and read the quote block and the
  household panel.
- [ ] Run `mise run rust:check-no-docs` and `mise run check`.

## What this plan leaves to a follow-up

`docs/superpowers/plans/<date>-the-public-body-in-the-client.md` (ruling B): the design's "Public money that is
spent", each public body's receipts by tax, standing rows and programs with due, paid and cut. The client has no such
panel today (`money_map/grouping.rs:54` only groups the account), so it is a third client task.
