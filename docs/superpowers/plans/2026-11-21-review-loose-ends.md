# Loose Ends of the Reviews Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the small defects and test gaps that the reviews of the price rule, the tiers and the benefits
named as not blocking, so that none of them is carried into the stages that build on this engine.

**Architecture:** No new behavior. Each item is a check made explicit, a test added, or a comment made true.
A world without a market policy, wants or programs keeps every byte.

**Tech Stack:** Rust (`babylon-material-circuit`); `contracts/material_circuit_v4.yaml`.

**Spec:** the plans whose reviews named these items, with their designs:
`docs/superpowers/plans/2026-11-20-price-of-a-short-market.md`,
`docs/superpowers/plans/2026-11-20-opening-stage-3-tiers.md`,
`docs/superpowers/plans/2026-11-20-opening-stage-4-benefits.md`.

## Global Constraints

- Work only in `/media/user/dev-ssd/worktrees/households-homes/babylon`, branch `codex/households-and-homes`.
  Start every shell command with `cd` to it (or to its `rust/`). Never push. No `.env`, no `uv.lock`.
- One cargo process at a time on the whole machine. Never pass `-j`. Only `mise exec -- cargo ...` and
  `mise run ...`.
- Every item is checked against the code first. If the code already does what the item asks, or the item is
  wrong, change nothing for it and say so in the report, with the evidence.
- No pinned value of any existing test changes. No assertion is loosened. The small world's runs
  (`tests/small_world/`) keep every figure.
- Money is `i128` millionths of a dollar; quantities are `u64`; arithmetic is checked and a failure is a typed
  error, never a panic or a wrap.
- A contract line that changes is changed with its pinned digest (`MATERIAL_CIRCUIT_SOURCE_SHA256` in
  `src/wire/state.rs`) in the same commit.
- Every line number is a hint; find each place by its text.
- **Scoped gate, run by every task before its last commit,** one leg at a time: from `rust/`,
  `mise exec -- cargo fmt --all -- --check`; `mise exec -- cargo clippy --workspace --all-targets --locked --
  -D warnings -D clippy::cognitive_complexity`; `mise run rust:test:q -- -p babylon-material-circuit`;
  `mise run rust:test:q -- -p babylon-tick`; `mise run check:bsl-sentinels`.
- Commit: `git add <files>`; message in a file; `PYTHONPATH=src mise exec -- git commit -q -F <file>`; then
  check `git log --oneline -1`.

## Review Focus

1. A fix that changes behavior where the item asked only for a check or a comment.
2. A new refusal that an admitted world of today could reach.
3. A test that passes without the fix (each new test is seen to fail first, where a fix exists).

---

### Task 1: Checks made explicit in the engine

**Files:** as each item names. **Test:** beside the code each item touches.

- [ ] **Item 1.** `src/services/close.rs`, `consume_households`: `need + want` is an unchecked `u64` addition.
  Use `checked_add` and return `MaterialCircuitError::Arithmetic`. Test: a need and a want whose sum passes
  `u64::MAX` give `Err(Arithmetic)`.
- [ ] **Item 2.** `src/tiers/lists.rs`, `need_item`: a service need's request is found with `.find` on (buyer,
  good, unit), and the requests now also hold want requests with the same key; it is right only because the
  sort keeps the need first. Leave want requests out explicitly. Test: a list built from requests in which the
  want's request comes first still takes the need's request.
- [ ] **Item 3.** `src/services/tiers.rs`, `seat_of`: `clearing::limit_price` is computed for every business
  seat, also one with nothing requested or no money, where the stage market before tiers computed it only for
  bidders. Compute it only for a seat that bids. Test: a business seat with nothing requested, whose limit
  could not be computed, does not refuse the stage.
- [ ] **Item 4.** `src/recurring/households.rs`, `refuse_open_want_orders`: for every want it scans all
  final-demand orders. Collect the want order ids of the period once and scan the orders once. Test: the
  existing refusal test still passes; add one with two wants and three orders where the second want's order is
  the open one.
- [ ] **Item 5.** `src/tiers/lists.rs`, `HouseholdLists::open` reads intents and requests before
  `recurring::validate` has run, so a malformed state with wants can be refused with another error than
  validation gives. Open the lists after validation. Test: a state that validation refuses is refused with
  validation's error when the catalog has wants.
- [ ] **Item 6.** `src/clearing/limit.rs`, `merchant_figure` returns `MerchantInvariant` when a merchant site
  buys a product that it also offers and has no handling coefficient for. Find whether catalog admission
  already refuses such a merchant. If it does, add the test that shows it. If it does not, make admission
  refuse it with the error it uses for a merchant without its coefficient, and add that test.
- [ ] **Item 7.** No test pins `clearing::limit_price` together with `CostClose::funded_wage`. Add
  `the_limit_reads_the_sites_own_funded_wage` in the crate: one site with one wage earner and one working
  owner, $200 funded over 20 hours, the plan's example of the price plan's Task 5: the limit is $130.
- [ ] **Run the gate. Commit** `fix(material-circuit): make five checks explicit and pin the limit price`.

### Task 2: Tests and words made true

**Files:** as each item names.

- [ ] **Item 1.** `tests/small_world/pushed.rs`: the doc comment of P4 under the policy says the clinic, the
  farm and the shop stopped at periods 12, 21 and 30 before; under the policy before Task 6b they stopped at
  19, 19 and 26. The doc comment of P2 under the policy says 13; it was 11. Correct both.
- [ ] **Item 2.** `src/clearing/table.rs`, the doc of `priced_out_goods` says services are planned from what
  was asked. Under a market policy they plan from the demand at the quote (rule P14). Correct it.
- [ ] **Item 3.** `contracts/material_circuit_v4.yaml`, the line "Service offers use Fixed or
  ServiceResponsive": add "under a market policy a service in the order of paying is ServiceResponsive".
  Update the digest.
- [ ] **Item 4.** `tests/market_clearing/support.rs`, `held` takes two bare booleans. Give them names (a small
  enum or a struct), and update its callers.
- [ ] **Item 5.** `src/clearing/rule.rs`, `MarketClearingPolicy::wants_of`: say in its doc that it reads an
  admitted catalog, whose wants are in canonical order.
- [ ] **Item 6.** `tests/market_clearing/wants.rs`: `an_empty_shelf_leaves_a_want_unbought` also asserts that
  no final-demand order of the closed state carries the want's order id;
  `declared_wants_change_nothing_yet` compares the whole transition (it derives `PartialEq`) after putting
  the state without want rows in its place.
- [ ] **Item 7.** The tick's `a_transition_with_tier_rows_is_refused` first asserts that the unchanged
  transition encodes, as its twin for want rows does.
- [ ] **Item 8.** Decision 5 of the tiers plan's Task 4a (a public-provision market settles its need, so that
  it stops reserving money from later wants) has no test that shows its effect. Add a fixture option that puts
  the public service in the utility stage with a local want after it, and the test
  `a_public_need_bought_frees_the_later_want`.
- [ ] **Item 9.** Comment and record lines past their width: the `# Errors` paragraph of `settle` in
  `src/tiers/lists.rs`; `tests/small_world/tiers.rs` near 191; `reports/economy-repair-2026-11-20/small-world.md`
  near 373 and 408. Rewrap; change no figure.
- [ ] **Item 10.** From the review of the tiers plan's Task 6. `tests/market_clearing/wants.rs`,
  `the_amount_held_back_is_what_the_close_assesses` proves the amount only to the $4 step of the shelf's price.
  Add a unit test in the crate that reads `tax_ahead` through `HouseholdLists::open` for each household account
  of a taxed fixture with two wage tax rows and compares it, to the millionth, with the sum of `assessed` over
  that account's wage tax receipts of the same close.
- [ ] **Item 11.** `tax_ahead` leaves out a wage booked after the lists open (the agency attendance shift,
  settled at the household close). Show with a test in the crate that such a wage is paid after the period's
  buying and is taxed at that same close, so that no want can be bought with its tax. If the test shows that a
  want can be bought with it, stop and report: that is a fault of Task 6 and not a loose end.
- [ ] **Item 12.** `tests/small_world/benefits.rs`, the doc of
  `p1_with_a_fund_and_tiers_returns_to_its_opening_state` says the owner has no comforts to buy with; the
  record shows it buying $120 of comforts and $200 of luxuries in every period. Correct the comment.
- [ ] **Item 13.** The record's section "Form (b) after" has no table for the quiet run, where "Form (b)
  before" has one: add it from the dump, in the same columns and periods. One blank line, not two, after the
  notice under "Form (b) before". Change no figure.
- [ ] **Run the gate. Commit** `test(material-circuit): cover what the reviews found uncovered`.

### Task 3: Public programs: scans, clamps, names and the record

**Files:** as each item names. **Test:** beside the code each item touches.

- [ ] **Item 1.** Scans that grow with the square of the national world. `src/financial/programs.rs`,
  `program_dues` finds each recipient's cohort with a linear `find`; `validate_programs` scans the cohorts once
  for each recipient; `src/financial/close.rs`, `public_funding` filters every due once for each budget;
  `src/financial/validation.rs`, `validate_layoffs` scans every employment row for each record. Build one map
  (or use a binary search on the sorted rows) in each, so that each is linear or n log n. No figure changes:
  every existing test of the four functions passes unchanged. Add one test for each that builds 2,000
  recipients (or records) and finishes; it is there to catch a return of the square, not to time it.
- [ ] **Item 2.** `src/financial/layoffs.rs`, `advance_records` takes every record out of the state before
  its early return for a state with no after-layoff recipient, so a state that still holds records after its
  last program was removed loses them in `finish_with_staffing` and keeps them unaged in
  `finish_with_workforce`. Decide by the stage 4 plan's rule (a record whose payee is no longer covered is owed
  nothing and the finish drops it): both finishes drop such records. Test: a state with one record and no
  program gives the same state from both finishes, with no record and no tail.
- [ ] **Item 3.** Silent clamps in `src/wire/financial.rs`: `unwrap_or(u8::MAX)` and `unwrap_or(u32::MAX)` for
  a program's key length and recipient count, and `u8::try_from(r.cohorts.len()).unwrap_or(u8::MAX)` for a
  record's cohorts. Return a typed wire error instead (as `append_bounded_rows` does). No test can reach
  them through an admitted state; show each with a unit test of the helper if one exists, else say so.
- [ ] **Item 4.** `src/wire/financial.rs`, `decode_programs` refuses an ill-formed key in the bytes with
  `PublicProgramInvariant`; it is a fault of the bytes: refuse it with the wire error the decoder uses for a
  malformed field. `src/financial/validation.rs`, `validate_layoffs` refuses unsorted records with
  `FinancialInvariant` where every other layoff refusal is `PublicProgramInvariant`: use the one class. Update
  the tests that name these errors.
- [ ] **Item 5.** `contracts/material_circuit_v4.yaml`: the field is named `financial_institutions.layoff_records`
  in one line and `layoffs` in the canonical keys and in the Rust field: use `layoffs`. The
  `cash_in_proportion` invariant says "its allocations": say "its allocations and programs". The tax
  invariant reads "without one per payer; with it ...": write "without the extension, one tax policy per
  payer; with it, one per payer, basis and public recipient". `field_order` of the financial institutions
  names the tail. Update the digest once for all of them.
- [ ] **Item 6.** Tests. `tests/small_world/benefits.rs` `per_person_reads_the_persons_of_the_cohort` and
  `tests/support/household_time_cases.rs` `a_benefit_per_person_follows_births` compare the book's total
  before and after. A test shows that a program's recipients given out of order are put in order by the
  period's canonical state and accepted. `the_county_review_counts_only_its_own_account` also compares the
  session's payments. `benefits.rs` `cents()` returns whole dollars: compare exact millionths where a test
  uses it. `assert_pin` refuses a cohort that starts at period 1 instead of underflowing.
- [ ] **Item 7.** The record `reports/economy-repair-2026-11-20/small-world.md`, words only, no figure: the
  P3 form (a) control says the treasury holds $160 where the taxed world with no fund holds $640; item 3 of
  "What the fund changes" says worker accounts close every period at $0 where two periods of one run hold $5
  to $6; item 6 groups P5 with pushes that have a control without a fund; a line near 500 calls the plain P1
  "runs away slowly"; P4 of form (a) says "about 12%" and "a tenth" of the same payment. Make each true to
  the dump.
- [ ] **Run the gate** (with `mise run rust:test:q -- -p babylon-persistence` if any persistence file
  changed). **Commit** `fix(material-circuit): public programs scale, refuse by class and read true`.

### Task 4: Tiers and the market table at the size of the country

Found by the check of the records plan on 21 November 2026. Each of these scans one long list for every row
of another. The national world has about 14,660 household accounts and may have three wants for each; the
bounds are 131,072 needs, 262,144 wants and 131,072 market rows. No figure changes: every existing test of
the functions named passes unchanged.

**Files:** `src/tiers/lists.rs`; `src/tiers/records.rs`; `src/clearing/table.rs`; `src/recurring/households.rs`;
the callers of each. **Test:** `src/tiers/tests.rs`; `src/clearing/` tests; one integration test in
`tests/market_clearing/wants.rs`.

- [ ] **Item 1.** `src/tiers/lists.rs`, `HouseholdLists::open`: for every want it asks `items.iter().any(..)`
  whether the account needs the product. Build the set of (principal, good, unit) of the needs once.
- [ ] **Item 2.** `src/tiers/lists.rs`, `Opening::posted` (the posted price of an item): it scans the offers
  for every item. The offers are sorted by (site, good, unit): search them, or build one map.
- [ ] **Item 3.** `bare_want_intents` (find it with `rg`): it scans for every want. One pass or one map.
- [ ] **Item 4.** `src/tiers/records.rs`, the tier sums in `receipts()` and in `validate_records`: for every
  tier row they filter every want row. Both families are sorted by (principal, tier): one merge pass.
- [ ] **Item 5.** `src/clearing/table.rs`, `MarketTable::has_row`, `price`, `priced_out` and
  `demand_at_quote` scan the rows on every call, and `record` calls `has_row`. Keep an index by the market's
  key beside the rows (the rows keep their order, which the receipts need).
- [ ] **Item 6.** Search the engine code added since `d53f6caa7` (`git diff d53f6caa7..HEAD` over the crate's
  `src`) for any other scan of one bounded family inside a loop over another (`.iter().find(`, `.iter().any(`,
  `.iter().filter(` inside `for`), and for each say in the report whether both sides can be long in the
  national world; fix those that can. Tasks 1 and 3 of this plan already hold `refuse_open_want_orders`,
  `program_dues`, `validate_programs`, `public_funding` and `validate_layoffs`.
- [ ] **A test of size.** `tests/market_clearing/wants.rs`, `a_large_world_of_wants_closes`: the goods fixture
  with 20,000 household accounts, each with one need and three wants (one of a good it also needs, two of a
  good it only wants), closes one period; the tier rows number 40,000 and the money is conserved. It is
  there to catch a return of the square, not to time anything: say in its doc what it guards.
- [ ] **Run the gate. Commit** `perf(material-circuit): tiers and the market table without squares`.
