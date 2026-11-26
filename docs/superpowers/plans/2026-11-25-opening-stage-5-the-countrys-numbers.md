# The Opening, Stage 5: The Builder and the New Numbers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

Drafted and checked once on 25 November 2026 against `0513cf036`; Part I is mended from the check. A prototype then
measured the builder's model under the game's own rules ("What the prototype found", below). Part II was rewritten
from it on 26 November and checked once by the lead. It builds the approved text's default for every choice that
waits for the Director, and each such choice is one named field of the builder's `Settings` (Task 9, decision 2):
a ruling changes a setting and, where the compiler must follow, a variant.

**Part I** is Tasks 1 to 8 and 14a to 18 and every section outside the tasks. **Part II** is the builder: Tasks 9,
10, 10b, 11, 12 and 13. **Task 4** (the fund and its programs) builds the approved text's one benefit figure and one
fund share; a ruling on either is a variant's small edit.

**A place and its parts.** The map has 187 pooled places. The accounts have 316: a pooled place is kept in up to
four parts, by its counties' share of people looking for work against the place's own (`ReservePosition`; 129
places open with two parts and 58 with one). A part is the code's financial domain (`FinancialDomainId`,
`grain/build.rs`): it has its own household accounts, one a key, its own workplaces and wages and its own public
body, and all of them sit at the place's hub. In this plan a *place* is the hub's location, where buyers and
sellers meet, and a *part* is where accounts are kept. A part's label, in the scenario and in the census, is `<hub
geoid>` for a part with no position (`representative` is `None`: a protected county, kept as itself) and `<hub
geoid>/<position>` for every other, the position `none`, `below`, `at` or `above`. The label is unique: a hub is the
first county of its own catchment, and catchments do not overlap (`grain/build.rs`). Part II's "place" is a part.

**Rulings that bind it** (the Director, 25 November 2026, ADR325): the country's numbers are built before the pay
fight; the three earning bands are built now (stage 2's Tasks 9 and 10); public providers are left out of the resting
price and the owner's restart (the country bench's Task 9, built as `ef4bb77e6`; the goods' step-down never reached a
service).

**Goal:** A builder run by hand turns the accounts table, the pay table and the game's own workforce into the numbers
of a national scenario of `schema_version = 8`: recipes, prices, the baskets of three tiers, retail hours, trade by
product, the tax rates and the fund's share. That scenario compiles as `national-world-v13` with its wants, its
national fund, its two programs, its prices that follow each workplace's wage, and the map's pinned basis. It opens
with every observed job needed and the four balances of O6 each within 1%, and the country bench records it. The
shipped scenario of schema 7 keeps every byte.

**Architecture:** Four parts, in this order. (1) The policy of schema 8 learns the keys the builder writes, and the
engine learns one thing it lacks: handling hours for a block of units, so retail hours need not be whole hours a unit.
(2) The national compiler wires what the engine already has: each account's wants (stage 3), the fund, the split
taxes and the two programs (stage 4), imports and exports by product, machines by trade and of every age, and the
map's pinned basis. (3) A Rust recorder writes the census of the twelve-trade opening (the game's workforce, bands,
wages, places, the foreign rows of every domestic buyer), committed and pinned. A Python builder reads the accounts,
the pay table and that census, solves the numbers with exact fractions, and writes the new scenario and its balance
sheet. (4) O5's price and refusal switch on, stage 2's fixture is retired in favour of the new scenario, the opening's
own report is tested before any period, and the country bench records the new scenario. Nothing in play reads the
accounts table (O3).

**Tech Stack:** Rust (`babylon-material-circuit` for one task, `babylon-persistence`), TOML scenario defines, Python
3.12 builders under `tools/` with the standard library and `fractions.Fraction`, `contracts/material_circuit_v4.yaml`,
`data-artifacts.yaml`, pytest.

**Spec:** `docs/superpowers/specs/2026-11-20-the-opening-of-the-national-economy-design.md`, rules O3 to O17, section
8 ("How we know it works", items 1 and 2), section 9 calls 2 to 11, 13, 14, 16 and 20, section 10 item 5. Record:
`ai/decisions/ADR313_the_national_economy_opens_in_balance.yaml`. Where ADR313's amendments by ADR314 (banks) and
ADR315 (homes) differ from the 20 November text, the 20 November text binds here: the Director ruled on 25 November
"Build stage 5 next ... by the design you approved on 20 November as it stands (thin profits before banks, owners' rent
left out, the shop as it is)". Read beside them: stage 1's plan and its last section; stage 2's plan ("What Schema 8
Means", Tasks 7 to 10b); the plans of stages 3 and 4 ("What the later plan carries", "Later plan B"); the country
bench's plan and `reports/country-bench-2026-11-24/README.md`.

**Build order:** built before Task 1: stage 2's Tasks 0 to 12 (bands, pay, the bench's band readings, and the
owner's restart mended for a shop of several goods), and the country bench's Task 9, which leaves public providers
out of the resting price and the owner's restart. Runs of builders, with the lead's gate
between runs:
- run A: Tasks 7a, 1, 2, 3, then 3b and 3c, in that order (Task 7a first: it needs nothing of the others, it is one
  key of the fixture, and it lets the first period be read early; Tasks 3b and 3c were added when Task 3's review
  found that the engine could not scale a want). A ruling that adds a key amends Task 1 afterwards;
- run B: Tasks 4, 6, 5, 7, 7b, 7c, 7d, 8, in that order (Task 6 before Task 5: Task 5 counts the replacement
  machines that Task 6 sets; Task 6 uses nothing of Task 5; Tasks 7b to 7d deal buyers to sellers after Task 5 has
  set what is bought abroad, and before Task 8's census reads who sells to whom);
- run C: Part II, Tasks 9, 10, 10b, 11, 12, 13, in that order (Python only), once Task 8's census is committed;
- run D: Tasks 14a, 14b, 15, in that order;
- run E: Tasks 16, 17, 18, in that order.

**The method is the spike's, recomputed.** The builder spike of 20 November (outside the repository,
`handoff-d7/land/builder-spike/README.md`, here "the spike") is the method's source. Its figures were computed from
its own fold of the BEA tables before stage 1's accounts table existed, and from the ten-trade shipped workforce split
by QCEW jobs before stage 2's census existed. Every spike figure quoted below is a check of order of size, never a
pinned value: the builder recomputes each one from the committed tables.

## What the scenario has at the end

`content/scenarios/national-rebuilt/defines.toml`, written by the builder, `schema_version = 8`, compiled as
`national-world-v13`:

- the twelve trades and their products of stage 2, each workplace paying the observed wage of its trade and place, and
  three earning bands in every place (stage 2, unchanged);
- recipes with whole-number coefficients, from the accounts re-cut to the game's buyers (O4, O10), each private trade
  with its margin (variant C: the accounts' margins scaled by one solved factor, at least 1.25 times wear);
- national opening prices from cost and margin, and each workplace's own opening price following its own wage (O5),
  with the refusal of a private product under cost at the nation's average wage;
- the needs of tier 1 (today's six products) and the comforts and luxuries of tiers 2 and 3 as want rows (O7), sized
  40%, the next 60% and the next 150% of a person's average spending;
- retail handling for every shop good households buy, needed or wanted, in hours for a block of units (O9);
- import and export shares by product, each import share written so that the nation's imports are the accounts'
  share, given that only buyers with a foreign second supplier import (Task 10b, decision 8); equipment bought abroad
  by its share; and foreign regions whose mix of jobs is computed so that each region's trade with the United States
  balances (O11);
- one rate, the same on wages and on operating income (call 5), a national fund with one share of each tax, the same
  in every place, a `no_earner` program per person and a `laid_off` program at 5,000 points for 13 half periods (O12,
  O13);
- a residence row for each place's collective residences, paid for its residents with no job at the opening (call
  18), and the luxury scale of every account whose money passes its three tiers (call 20);
- public providers whose grant also covers their machines' wear for one period, so that they replace their machines as
  a private workplace does from its margin;
- machines by trade at a designed number of workers per machine, opening at every age, for the whole workforce (O14);
- the map's basis pinned as the shipped food figures, so the 187 places stay (O15);
- no working capital taken by a company at the opening (the Director's ruling of 20 November; Tasks 7a and 13), so
  that every workplace can pay for its first period;
- buyers dealt to sellers so that every workplace with people at work has custom in proportion to them (Tasks 7b to
  7d): O4 holds for a workplace, not only for a trade;
- `private_distribution_bps = 10000` (the spike's section 5, item 5: balance 4 holds only at a full payout of book
  earnings, because wear is in cost).

Its needs stay six (`needs()` requires six rows under every schema). Its first lines say it is the rebuilt opening,
counted on the country bench, and not yet played by the game's own turn. The shipped
`content/scenarios/national/defines.toml` is not touched. Making the new scenario the shipped one, and carrying its
records through the tick, is a later plan's.

## Global Constraints

- Work only in `/media/user/dev-ssd/worktrees/households-homes/babylon`, branch `codex/households-and-homes`. Start
  every shell command with `cd` to it (or to its `rust/` directory). Never push. No secrets, no `.env`, no
  `babylon-data` on this disk. Nothing from `/media/user/data/babylon-data` is read by any task of this plan: every
  input is a committed table.
- One cargo, mise or pytest process at a time, on the whole machine. Never pass `-j` or `--jobs`. A build in another
  checkout empties this one's cache; launch long tests with `--no-build` after a build when the lead says so.
- A run that outlasts one command goes to the background with a log in your scratch directory, ends with its own
  marker (`...; echo "END <name> status=$?" >> <log>`), and is waited for on that marker. Never wait on the word `real`
  (zsh's `time` prints `total`). Leave no shell running when you report.
- **Scoped gate for Rust tasks,** before the last commit, one leg at a time: from `rust/`, `mise exec -- cargo fmt
  --all -- --check`; `mise exec -- cargo clippy --workspace --all-targets --locked -- -D warnings -D
  clippy::cognitive_complexity`; the binaries the task names with `mise run rust:test:q -- -p <crate> -E
  'binary(<name>)'`; `mise run rust:test:q -- -p <crate>` once for each crate the task changed; `mise run
  check:bsl-sentinels`. Every task that changes `babylon-kernel`, `babylon-material-circuit` or `babylon-persistence`
  also runs `binary(shipped_world_bytes)` and `binary(national_household_units)` of `babylon-persistence`. The lead
  alone runs `mise run rust:check-no-docs`, after Tasks 4, 8 and 15.
- **Gate for Python tasks** (stage 1's): `mise exec -- uv run --frozen ruff check <changed .py>`; `mise exec -- uv run
  --frozen ruff format --check <changed .py>`; `MYPYPATH=tools mise exec -- uv run --frozen mypy --strict
  --follow-imports=silent <new tools/*.py>` (without `MYPYPATH=tools` the sibling tools are not found); one `mise run
  test:q -- <paths>` with the task's test files and `tests/unit/reference/test_data_artifacts.py` (in Part II with
  `-m 'not slow'` in the inner loop, and the task's slow tests once, in the background, before its commit);
  `UV_PROJECT_ENVIRONMENT=.venv mise exec -- uv run --frozen python tools/make_data_artifacts.py --check`.
- Commit one unit of work at a time: `git add <files>` then `PYTHONPATH=src mise exec -- git commit -q -F <message
  file>`; check that `git log --oneline -1` moved (a hook can abort silently). The body ends with `Part of PER-371` and
  a `Co-Authored-By` line naming the model that wrote the commit. Never commit `uv.lock`.
- **Never `git add -f`.** No log is ever committed: the hygiene gate refuses a tracked file that `.gitignore` ignores.
  A committed file holds at most 1,048,576 bytes unless the repository names a budget for it (stage 1's size rule).
  Run `mise run check:hygiene` before any commit that adds a file.
- **Bytes.** A policy of schema 7 or earlier gives every byte it gives today: catalog, opening, foundation, configs,
  state. The pins of `tests/shipped_world_bytes.rs` never move. A catalog with no handling block (every row's units 1)
  writes today's catalog bytes. If a pin of the shipped world must change, stop and tell the lead.
- **Stage 1's tables are inputs, never outputs.** No task rebuilds or edits `national_trade_accounts_2024.csv.gz`,
  `national_trade_pay_2024.csv.gz` or their metadata. Their metadata files pin each other: if a task finds it must
  rerun one stage 1 builder, it stops, because the later ones must then be rerun in order with every table's bytes
  unchanged, and that is the lead's.
- **`preset.rs`.** No task of this plan edits `rust/crates/babylon-persistence/src/economic_catalog/preset.rs`. A shell
  tool of another lane (`tools/postgres_national_lifecycle.sh`, `national_input_paths`) reads it by its shape: a block
  `    let rows: ... = &[` to `    ];` holding exactly 15 `include_bytes!` rows. If a task finds it must touch that
  file, it stops and asks the lead; a task that the lead lets touch it keeps that shape and runs `mise run test:q --
  tests/unit/tools/test_national_native_pair.py tests/unit/tools/test_wayne_qualification_backup.py`.
- **Rust:** no floating point. Money is `i128` millionths of a dollar (`Currency`). Quantities and persons are `u64`.
  Each division names its rounding; every rounding is down unless a decision says otherwise. Every refusal is a typed
  error; no panic, no `unwrap` outside tests, no silent clamp. Functions under 100 lines and a cognitive complexity
  under 25. No `mod.rs`. A contract under `contracts/` that a task makes false is rewritten by that task in the form
  "under schema 7 and earlier ...; under schema 8 ...", with its pinned digest updated in the same commit
  (`MATERIAL_CIRCUIT_SOURCE_SHA256` for `material_circuit_v4.yaml`).
- **Python:** exact arithmetic. Every quantity is an `int` or a `fractions.Fraction`; a `float` anywhere is a defect.
  Every rounding to an integer names its rule (half up, down, or largest remainder). Every refusal is a
  `ReferenceBuildError` from `tools/make_national_county_reference.py` whose message starts with a fixed code. Output
  is deterministic: built twice into a scratch folder made with `mktemp -d -p /media/user/dev-ssd`, the bytes are
  equal; metadata is JSON with `indent=2, sort_keys=True` and a trailing newline. No test reads the data drive; tests
  read committed tables and small fixtures they carry or build in `tmp_path`.
- **No verdict.** No task writes a conclusion about whether the country stands. The records are the lead's to read,
  and nothing is judged on 34 periods.
- **Records.** Every record and report of this stage goes under `reports/country-opening-v13/`, a new folder. Stage
  2's Task 8b keeps its own records under `reports/country-opening-2026-11/`; no task of this plan writes there.
- **Who runs what.** A builder runs only what its task names. After every run of builders, and before every push, the
  lead runs `mise run check:static` and the whole Python unit suite as one process.
- Markdown is wrapped at 120 columns, headings at 80. Refer to the player as "they".

## Review Focus

1. **The census follows the numbers.** If the census of the opening changed with recipes or prices, the builder would
   solve against a workforce that the compiled opening does not have. Expected: the census is the same from stage 2's
   fixture and from the rebuilt scenario. Test: Task 14a, `the_census_does_not_follow_the_numbers`.
2. **A want that reaches no seller.** Consumer goods are wanted and never needed, so today's compiler gives them no shop
   offer, no stock, no handling row and no procurement (it wires those for needs only, `markets.rs` `households` and
   `actors.rs` `handling_requirements`). Expected: every want has a purchase row whose seller offers it. Test: Task 3,
   `every_want_has_a_seller_that_offers_it`.
3. **Rounding that moves a balance.** Whole-number recipes, units and want counts each move a balance a little.
   Expected: each balance of O6 within 1% on the numbers as written, not on the exact solve. Tests: Task 10b,
   `rounded_recipes_cost_within_one_percent`; Task 13, `the_balances_as_written_close_within_one_percent`; Task 15,
   `the_four_balances_close_within_one_percent`.
4. **A handling block that rounds the wrong way.** With units per block above 1, hours for an order are rounded up and
   capacity in units is rounded down; a mistake makes a shop sell more than its hours or less than its stock. Expected:
   with every block at 1 each figure is today's; with blocks, hours `ceil(q x h / n)`, units `floor(H x n / h)` and a
   cost per unit `ceil(h x wage / n)`. Tests: Task 2, `a_block_of_units_takes_its_hours_rounded_up`,
   `a_shop_with_blocks_sells_what_its_hours_handle`, and the existing tests of `binary(market_clearing)` with their
   literals unchanged.
5. **A place's body that cuts or hoards from period 1.** With one national rate and one fund share in every place
   (O12, O13 as approved), a place whose people earn more collects more than it pays and a poorer place less.
   Expected: the nation's bodies and the fund each balance within 1%; each place's receipts against its payments are
   written into the report, never asserted (For the Director, item 1). Tests: Task 15,
   `the_four_balances_close_within_one_percent`, `each_place_s_body_is_reported`.

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `rust/crates/babylon-persistence/src/national_economy/policy/{admission,game}.rs` | The keys of the rebuilt opening; the price scale's refusal | 1, 14a |
| `rust/crates/babylon-persistence/tests/fixtures/national_twelve_trades.defines.toml` | Takes the keys (Task 1), retired (Task 14a) | 1, 14a |
| `rust/crates/babylon-material-circuit/src/{catalog.rs, model.rs, wire/catalog.rs, transition/merchant_admission.rs, transition/outbound/orders.rs, recurring/firms.rs, recurring/spare_money.rs, clearing/supply.rs, clearing/limit.rs, adjustment/restart.rs, adjustment/bound.rs}` | Handling for a block of units | 2 |
| `contracts/material_circuit_v4.yaml` | The handling block | 2 |
| `rust/crates/babylon-persistence/src/national_economy/opening/{markets,actors,templates,build}.rs` | Wants, shop goods wanted, handling blocks | 3 |
| `rust/crates/babylon-persistence/src/national_economy/opening/{financial,fund,equipment}.rs` | Fund, split taxes, programs, support unit, public providers' wear | 4 |
| `rust/crates/babylon-persistence/tests/support/country_bench.rs` | The bench keeps an opening's own fund | 4, 16 |
| `rust/crates/babylon-persistence/src/national_economy/opening/{markets,equipment}.rs` | Imports and exports by product; equipment abroad | 5 |
| `rust/crates/babylon-persistence/src/national_economy/opening/equipment.rs`, `grain/build.rs` | Machines by trade, of every age | 1, 6 |
| `rust/crates/babylon-persistence/src/national_economy/grain/build.rs` | The map's pinned basis | 7 |
| `rust/crates/babylon-persistence/src/national_economy/opening/{dealing,markets,equipment}.rs` | Buyers dealt to sellers in proportion | 7b to 7d |
| `rust/crates/babylon-persistence/src/economic_catalog/capture.rs` | `national_household_budget` made public for the census | 8 |
| `rust/crates/babylon-persistence/tests/national_opening_census.rs`, `tests/support/opening_census.rs` | The census recorder and its check | 8, 14a |
| `src/babylon/data/reference/economy/national_opening_census_v13.json` | The game's workforce, bands, places, foreign rows | 8 |
| `tools/national_opening_recut.py` | Settings, the census reader, the accounts re-cut | 9 |
| `tools/national_opening_solve.py` | Quantities, prices, margins, trade, taxes, the margin factor | 10 |
| `tools/national_opening_units.py` | Units, recipes, prices, grams, handling blocks, written rates | 10b |
| `tools/national_opening_tiers.py` | Place accounts, tiers, luxury scales, the benefit, place bodies, the two counts | 11 |
| `tools/national_opening_abroad.py` | Foreign regions' mix of jobs and export shares | 12 |
| `tools/make_national_opening_numbers.py`, `tools/national_opening_v13_defines.toml.in` | The writer and its template | 13 |
| `content/scenarios/national-rebuilt/defines.toml` (+ `defines.metadata.json`) | The rebuilt scenario and its balance sheet | 13 |
| `tests/unit/tools/test_national_opening_{recut,solve,units,tiers,abroad,numbers}.py` | The builder's tests | 9 to 13 |
| `rust/crates/babylon-persistence/tests/national_twelve_trades.rs` and the files that include the fixture | Open the rebuilt scenario | 14a |
| `rust/crates/babylon-persistence/src/national_economy/opening/{markets,financial,build,equipment}.rs`, `grain/build.rs` | O5's price and refusal | 14b |
| `rust/crates/babylon-persistence/tests/national_rebuilt_opening.rs`, `tests/support/opening_ledger.rs` | The opening's report and its tests | 15 |
| `rust/crates/babylon-persistence/tests/national_household_units.rs`, `tests/support/country_*.rs` | The bench on the rebuilt scenario | 16 to 18 |
| `reports/country-opening-v13/` (a new folder) | The opening's report and the bench's records | 15 to 18 |

---

### Task 1: The keys of the rebuilt opening (schema 8)

Commit `feat(economy): admit the builder's keys in a national policy of schema 8`.

**Files:**
- Modify: `rust/crates/babylon-persistence/src/national_economy/policy/{admission.rs, game.rs}`, `policy.rs` and
  `national_economy.rs` (re-exports); `tests/fixtures/national_twelve_trades.defines.toml` (takes the keys); the
  readers of the replaced fields (decision 7): `opening/markets.rs` (`procure`, about L732), `opening/equipment.rs`
  (about L275, and the definition and ages), `opening/actors.rs` and `opening/markets.rs` (handling hours), and
  `national_economy/grain/build.rs` (`OpeningProductiveEndowment::source`: at `0a0cba1dd` L790 and L799
  `batches_per_unit_per_period`, L800 `opening_remaining_service_bps`, L804 `service_batches_per_unit`)
- Test: `rust/crates/babylon-persistence/tests/national_game_policy.rs`

**Interfaces:**
- Consumes: `TradeSet` (`babylon_kernel::economic_identity`); `WantTier` and `HouseholdNeedBasis`
  (`babylon-material-circuit`, `recurring/model.rs`).
- Produces (`game.rs`):

```rust
/// Retail handling of one shop good: `hours` of retail work for every `units` units.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GameHandling { pub hours: u64, pub units: u64 }
// GameCommodity gains `handling: Option<GameHandling>`: Some exactly for a storable good households need or want,
// under schema 8; None under schema 7 and earlier (the policy's `handling_hours_per_unit` serves there).
// NationalGamePolicy: `handling_hours_per_unit: u64` becomes `handling_hours_per_unit: Option<u64>` (Some under 2..=7).
/// How much of each storable good a buyer may take from abroad.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GameProcurement {
    /// One cap for every good and both directions: schema 7 and earlier.
    Single(u16),
    /// Schema 8: a domestic buyer's share bought abroad, by product key (O11).
    ByProduct { import_bps: BTreeMap<String, u16> },
}
// GameMarketPolicy: `foreign_procurement_bps: u16` becomes `procurement: GameProcurement`.
// GameProfile gains `export_bps: Option<BTreeMap<String, u16>>`: a buyer of that region's share bought from the
// United States, by product key; Some exactly under schema 8.
// GameRecipe gains `margin_bps: Option<u32>`: Some under schema 8 for every private trade, None for public provision.
/// Machines of the scenario.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GameMachines {
    /// Schema 7 and earlier: today's three keys.
    Batches {
        batches_per_unit_per_period: u64,
        service_batches_per_unit: u64,
        opening_remaining_service_bps: [u16; 4],
    },
    /// Schema 8: workers per machine by trade, one life for all, machines of every age (O14).
    Workers { workers_per_machine: BTreeMap<EconomicFunction, u64>, life_periods: u64 },
}
// GameEquipmentPolicy: those three fields become `machines: GameMachines`; the others stay.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameWant { pub key: String, pub tier: WantTier, pub basis: HouseholdNeedBasis, pub units_per_basis: u64 }
// NationalGamePolicy gains `household_wants: Vec<GameWant>`, sorted (tier, key); empty under schema 7.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameFundPolicy {
    pub wage_tax_share_bps: u16,
    pub operating_income_tax_share_bps: u16,
    /// Periods of its payments the fund opens with (O13: two).
    pub reserve_periods: u64,
}
// The two shares are the fund's in every domestic place alike (O12: "one national fund that takes a share of both
// taxes everywhere").
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GameProgramTerms {
    PerPerson { amount_per_person: Currency },
    /// One amount a person for each place named, by its hub county (call 18: a place's collective residences).
    PerPersonByPlace { amounts: BTreeMap<CountyGeoid, Currency> },
    AfterLayoff { wage_share_bps: u16, half_periods: u16 },
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameProgramRecipients { NoEarnerAtOpening, EarningOrResidenceAtOpening, CollectiveResidenceAtOpening }
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameProgram {
    pub key: String, pub rank: u32, pub terms: GameProgramTerms, pub recipients: GameProgramRecipients,
}
// NationalGamePolicy gains `fund: Option<GameFundPolicy>` and `programs: Vec<GameProgram>` (key order), Some and
// three rows exactly under schema 8.
/// An account whose money passes its three tiers buys its luxuries times `bps / 10_000` (call 20).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameLuxuryScale { pub place: String, pub key: HouseholdBudgetKey, pub bps: u32 }
// NationalGamePolicy gains `luxury_scales: Vec<GameLuxuryScale>`, sorted (place, key); empty under schema 7 and when
// the table is absent. `place` is a domestic part's label (`<hub geoid>` or `<hub geoid>/<position>`, the position
// `none`, `below`, `at` or `above`), or a counterpart's or the dependency's key.
// NationalGamePolicy gains `place_services: Vec<String>`, sorted: the period services a buyer takes only in its own
// place (Task 7b); empty under schema 7 and when the key is absent.
/// The food figures that fold the counties into places (O15), written down so recipes can change.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GameMapBasis {
    pub food_labor_hours_per_batch: u64, pub food_output_units_per_batch: u64,
    pub food_units_per_person: u64, pub food_grams_per_unit: u64,
}
// NationalGamePolicy gains `map_basis: Option<GameMapBasis>`, Some exactly under schema 8.
```

**Decisions:**
1. **TOML shape.** Under schema 8: `[commodity.<key>] handling_hours` and `handling_units` (both, for every storable
   good that a need or a want names; refused (`Shape`) on any other commodity); `[markets] import_bps = { <key> =
   <bps>, ... }` with exactly the storable goods that have a price (`food`, `resources`, `materials`,
   `consumer_goods`, `equipment`); every `[counterpart.<key>]` and `[dependency]` an `export_bps` table of the same
   keys; `[process.<key>] margin_bps` for every trade but `public_provisioning`; `[equipment] workers_per_machine = {
   <trade key> = n, ... }` for the eleven recipe trades and `machine_life_periods`; `[[household_wants]]` rows of
   `good`, `tier` (`"comfort"` or `"luxury"`), `basis`, `units_per_basis`; a `[fund]` table of `evidence_class =
   "Designed"`, `wage_tax_share_bps`, `operating_income_tax_share_bps`, `reserve_periods`; three `[[programs]]` rows:
   `key = "laid_off"`, `kind = "after_layoff"`, `rank`, `wage_share_bps`, `half_periods`, `recipients =
   "earning_or_residence_at_opening"` (call 18: a residence is also a recipient of `laid_off`); `key = "no_earner"`,
   `kind = "per_person"`, `rank`, `amount_per_person_micros`, `recipients = "no_earner_at_opening"`; and `key =
   "residence"`, `kind = "per_person_by_place"`, `rank`, `recipients = "collective_residence_at_opening"`,
   `amounts_micros = { "<hub geoid>" = <micros>, ... }` (one entry for each domestic place whose residences are paid;
   the table may be empty); an optional `[luxury_scale]` table, `by_account = { "<place>:<budget key label>" = <bps>,
   ... }`, the label as `HouseholdBudgetKey::label()` writes it, the place a part's label; an optional `[markets]
   place_services = ["<service key>", ...]`; `[grain.basis]` with the four `GameMapBasis` fields.
2. **Refused under schema 8** (`Shape`): the top-level `handling_hours_per_unit`; `[markets] foreign_procurement_bps`;
   `[equipment] batches_per_unit_per_period`, `service_batches_per_unit`, `opening_remaining_service_bps`. Each new key
   under schema 7 or earlier is refused (`Shape`), and each missing under schema 8 is refused (`Shape`). The existing
   `Raw*` structs keep `deny_unknown_fields`; the new fields are `Option` and checked by schema as `wages` and
   `households` do today (`admission.rs:975-1011`).
3. **Values refused** (`Profile(<name>)` unless named): `handling_hours` 0 or `handling_units` 0; a share above
   10,000; a margin above 100,000 bps; `workers_per_machine` 0 or a trade missing or twice; `machine_life_periods` 0 or
   above 10,000; a want's `units_per_basis` 0, its product unknown, unpriced, not in the order of paying, or the same
   `(tier, good)` twice (`HouseholdNeed(<good>)`); fund shares above 10,000; `reserve_periods` 0 or above 16; a
   program key other than the three, a key twice, `rank`
   above 255, `wage_share_bps` outside `1..=10_000`, `half_periods` outside `1..=26`, an amount not above 0, a kind
   that does not match its key (`no_earner` is per person, `laid_off` after layoff, `residence` per person by place),
   a recipients word that does not match its key; an `amounts_micros` key that `EconomicLocation::domestic_county`
   refuses (`Location`); a `luxury_scale` key whose place has not the form of a part's label, a counterpart's key or the
   dependency's,
   or whose label is no budget key (`Location`), the same account twice, a value at or under 10,000 or above
   1,000,000 (`Profile("luxury_scale")`); a `place_services` entry that is no period service of the scenario, or
   named twice (`Profile("place_services")`); any basis field 0. Admission reads the scenario alone and cannot know
   a hub or a part: it checks the form (a county by `EconomicLocation::domestic_county`, which refuses a state code
   that is none; a position by its four words), and the compiler refuses a scale or an amount that names nothing
   (Tasks 3 and 4).
4. **Price scales** keep today's range and meaning in this task: the fixture carries scales below 10,000 (Mexico
   4,000, China 4,500 and others) and its stage 2 tests read them. Task 14a, which retires the fixture, refuses under
   schema 8 any `price_scale_bps` but 10,000.
5. `private_distribution_bps` keeps its range; the scenario writes 10,000. `reserve_food_support_periods` keeps its
   key; under schema 8 it counts periods of the food need, not units (Task 4, decision 6).
6. **The fixture takes the keys** with designed placeholder values, so it still parses and every stage 2 test keeps its
   values until Task 14a retires it. It loses the keys decision 2 refuses: the top-level `handling_hours_per_unit`,
   `[markets] foreign_procurement_bps`, and `[equipment] batches_per_unit_per_period`, `service_batches_per_unit` and
   `opening_remaining_service_bps`. It gains: handling `hours = 1, units = 1` on `food` and `materials` only (the
   storable goods its needs name; decision 1 refuses handling on a good no need or want names);
   `import_bps` and every `export_bps` 2,500 for each good (today's single cap); every `margin_bps` 0;
   `workers_per_machine` 4 for the trades whose fixture batch is 16 hours and 40 for those of 160 hours, and
   `machine_life_periods = 100` (so Task 6's `batches_per_unit_per_period` is `ceil(160 x 4 / 16) = ceil(160 x 40 /
   160) = 40` and `service_batches_per_unit` 4,000, today's figures); `import_bps["equipment"]` 0 (so Task 5 sends no
   process abroad that has a home supplier, as today); no `[[household_wants]]` rows (the key is optional under
   schema 8 and reads as empty when absent); `[fund]` with shares 0 and `reserve_periods = 2`; the three programs (rank
   0; `laid_off` 5,000 and 13; `no_earner` 1,595,033,714 micros, the bench's stand-in figure, read from
   `reports/country-bench-2026-11-24/all-six-with-benefits.json`; the README rounds it to $1,595.03; `residence` with
   an empty `amounts_micros`, so no residence is paid by it); no `[luxury_scale]` table; `place_services =
   ["household_services", "housing", "public_provision"]`; `[grain.basis]`
   16, 16, 1, 14,000 (the shipped food recipe, need and grams). A fund share of 0 makes no fund tax row (Task 4), so the
   fixture's opening keeps its tax rows.
7. **The old readers under schema 8.** Every reader of `handling_hours_per_unit`, `foreign_procurement_bps` and the
   three equipment fields (the files above, `grain/build.rs` among them) reads the `Single` and `Batches` arms as
   today. Until Tasks 3, 5 and 6 wire the schema 8 arms, each such reader maps the schema 8 arm to today's figure in a
   private helper of its own file, for every schema 8 policy alike (a reader cannot tell the fixture from another
   scenario):
   - handling: `hours` when `units == 1`, else `NationalOpeningError::Policy`;
   - a buyer's cap abroad: `import_bps[key]` for a domestic buyer, its region's `export_bps[key]` for a foreign or
     dependency buyer; so the fixture's equipment cap abroad for a process with no home supplier is its region's
     `export_bps["equipment"]` (2,500), as today. If a domestic process of the fixture has no home equipment supplier,
     its cap would become `import_bps["equipment"]` (0) and a pin moves: stop and tell the lead;
   - `Workers` to `batches_per_unit_per_period = ceil(work_hours_per_person x workers_per_machine /
     labor_hours_per_batch)` of the trade's recipe, `service_batches_per_unit = that x machine_life_periods`, and
     today's four ages `[2500, 5000, 7500, 10000]`.
   So the fixture's opening is today's, and every stage 2 pin holds. Tasks 3, 5 and 6 replace each helper.

- [ ] **Step 1: Write the failing tests** in `national_game_policy.rs`:
  - `the_fixture_takes_the_builder_keys`: the fixture parses; `household_wants` is empty; `fund` has shares (0, 0) and
    `reserve_periods == 2`; `programs` holds `laid_off`, `no_earner`, then `residence` with the decision 6 terms;
    `luxury_scales` is empty;
    `place_services` holds the three of decision 6;
    `map_basis ==
    Some(GameMapBasis { 16, 16, 1, 14_000 })`; `procurement == ByProduct` with five rows, 2,500 but equipment 0;
    Canada's `export_bps` five rows of 2,500; `machines == Workers` with eleven rows; `handling_hours_per_unit == None`;
    `food` and `materials` have `handling == Some(GameHandling { hours: 1, units: 1 })` and no other commodity has one.
  - `the_shipped_policy_keeps_its_arms`: shipped `procurement == Single(2500)`, `machines == Batches { 40, 4000,
    [2500, 5000, 7500, 10000] }`, `handling_hours_per_unit == Some(1)`, no wants, `fund == None`, no programs,
    `map_basis == None`.
  - `builder_keys_are_refused_under_schema_7`: the shipped file plus each new key in turn gives `Err(Shape)`.
  - `schema_8_needs_the_builder_keys`: the fixture without `[fund]`, without a program, without `[grain.basis]`,
    without `import_bps`, without Canada's `export_bps`, without `workers_per_machine`, with
    `handling_hours_per_unit = 1`, with `foreign_procurement_bps = 2500`: each `Err(Shape)`.
  - `bad_builder_values_are_refused`: one case for each refusal of decision 3, each with its exact error; and
    `handling_hours` on `consumer_goods` with no want naming it is `Err(Shape)` (decision 1).
  - `a_want_is_read_in_tier_and_key_order`: two wants written luxury `leisure` then comfort `consumer_goods` come back
    comfort first; a want of `equipment` (not in the order of paying) is `Err(HouseholdNeed("equipment"))`.
  - `residence_amounts_and_luxury_scales_are_read`: the fixture with `amounts_micros = { "26163" = 700000000 }` and
    `[luxury_scale] by_account = { "26163:earning-owner" = 12500 }` gives `PerPersonByPlace` with one entry of $700.00
    and one `GameLuxuryScale { "26163", EarningOwner, 12_500 }`; an amount for `"99999"` is `Err(Location)`; a scale of
    10,000 is `Err(Profile("luxury_scale"))`; a scale for `"26163:no-such-key"` is `Err(Location)`; a scale for
    `"01073/below:earning-owner"` is read with the place `01073/below`, and one for `"01073/north:earning-owner"` is
    `Err(Location)`; `place_services = ["food"]` (a storable good) is `Err(Profile("place_services"))`.
- [ ] **Step 2: Run them and see them fail.** `-p babylon-persistence -E 'binary(national_game_policy)'`: does not
  compile.
- [ ] **Step 3: Implement** the types, the admission, the readers' helpers (decision 7) and the fixture's keys.
- [ ] **Step 4: Run** `binary(national_game_policy)`, `binary(national_twelve_trades)`, `binary(national_opening)`,
  `binary(shipped_world_bytes)`, `binary(national_household_units)`, the crate. Expected: pass, no pinned value moved.
- [ ] **Step 5: Gate and commit** with the subject above.

What the player would see: nothing; no road to the screen before the game's own turn carries schema 8.

### Task 2: Handling for a block of units (the engine)

Commit `feat(material-circuit): retail hours for a block of units`.

**Why.** The engine's handling is already by site and good (`MerchantHandlingCoefficient`, `model.rs:368`), but a
whole number of hours a unit, at least 1 (`catalog.rs` refuses 0). The tiers need small units: a day's food for one
person costs a fraction of one retail hour (the spike, section 3: 0.70 retail hours on a week's food, so about 0.1 on a
day's). With whole hours a unit the shop would need about ten times its workers, or tier contents would round by 3% in
weekly units (the spike, section 4). So retail hours are given for a block of units.

**Files:**
- Modify: `rust/crates/babylon-material-circuit/src/model.rs` (`MerchantHandlingCoefficient`, L368);
  `src/catalog.rs` (the check near "row.hours_per_unit == 0", L301); `src/wire/catalog.rs` (the version and the
  tail); `src/transition/merchant_admission.rs` (`hours_per_unit`, L17-29, and its checks); `contracts/
  material_circuit_v4.yaml` and the digest; and every reader of decision 3's table
- Modify (literals): every `MerchantHandlingCoefficient {` literal in the workspace gets `units: 1` (`rg -n
  'MerchantHandlingCoefficient \{' rust/crates`: 27 literals in 25 files in the copy, in the engine and its tests,
  `babylon-circuit-worlds/src/doubled/catalog.rs`, `babylon-persistence` (`economic_catalog/compile.rs`,
  `production_projection/*`) and `babylon-tick/tests`)
- Test: the crate's `catalog.rs` tests; `tests/market_clearing/` (a new module `handling_blocks.rs` of that binary)

**Interfaces:**
- Produces:

```rust
// MerchantHandlingCoefficient gains, after hours_per_unit:
/// The units that `hours_per_unit` hours handle. 1 is today's rule: so many hours for each unit.
pub units: u64,
/// Hours to handle `quantity` units at this site: ceil(quantity x hours_per_unit / units).
/// # Errors
/// `MerchantInvariant` for a site and good without a row; `Arithmetic` on overflow.
pub(crate) fn handling_hours(catalog: &MaterialCatalog, site: SiteId, good: GoodId, unit: UnitId, quantity: u64)
    -> Result<u64, MaterialCircuitError>;
/// Units that `hours` hours can handle: floor(hours x units / hours_per_unit).
pub(crate) fn handled_units(catalog: &MaterialCatalog, site: SiteId, good: GoodId, unit: UnitId, hours: u64)
    -> Result<u64, MaterialCircuitError>;
/// The handling cost of one unit at `wage` micros an hour: ceil(hours_per_unit x wage / units) micros.
/// # Errors
/// `Arithmetic` on overflow or a negative wage.
pub(crate) fn handling_cost_per_unit(hours_per_unit: u64, units: u64, wage: i128) -> Result<i128, MaterialCircuitError>;
```

**Decisions:**
1. `units == 0` is refused with `MerchantInvariant`, beside the check of `hours_per_unit == 0` (`catalog.rs:301`).
2. **Three rules, one each.** Hours for a quantity are rounded up (`handling_hours`); units for hours are rounded down
   (`handled_units`); a cost per unit at a block is `ceil(hours_per_unit x wage / units)` micros
   (`handling_cost_per_unit`), the same rule as Task 3's retail charge. With `units == 1` each is exactly today's
   arithmetic (`q x h`, `floor(H / h)`, `h x wage`), so no figure of an existing test moves. Rounding up the hours of
   an order, and down the units of a capacity, means a shop never sells more than its hours can handle.
3. **Every reader, and its rule.** The readers of a handling row in the copy, each of which this task changes:
   - `clearing/supply.rs:129` (hours for a quantity): `handling_hours`.
   - `clearing/limit.rs:207` (a price less the handling of one unit): `handling_cost_per_unit` at the merchant's wage.
   - `recurring/firms.rs:790` (a map of rows, then hours for the merchandise handled): the map's value becomes
     `(hours_per_unit, units)`; hours by `handling_hours`'s rule.
   - `recurring/spare_money.rs:205` (the map) and `:469-485` (`per = hours_per_unit x wage`, then `affordable(gap,
     per, ...)`): `per` is the cost of one whole block, `hours_per_unit x wage`; `blocks = affordable(ceil(gap /
     units), per, spare)`; `units = min(gap, blocks x units)`; hours `handling_hours(units)`; the money spent is
     `blocks x per`. So spare money buys whole blocks.
   - `adjustment/restart.rs:302-304` (the map) and `:551-563` (a unit's cost `hours_per_unit x rate + price`):
     `handling_cost_per_unit(hours_per_unit, units, rate) + price`.
   - `adjustment/bound.rs:239` (the map by site) and `:540-550` (`held x hours_per_unit`): `handling_hours` of
     `held`.
   - `transition/outbound/orders.rs:565` (the labor request of a merchant's order) and `:600-611` (needed and used
     hours of the receipt): the request carries `(hours_per_unit, units)`; the allocation admits quantities whose
     hours, each order's rounded up by `handling_hours`, sum to at most the merchant's hours available, and every
     other freight resource keeps a block of 1; `needed_hours = handling_hours(feasible)`, `used_hours =
     handling_hours(handled)`, and `labor.available` falls by exactly `used_hours`.
   - `transition/merchant_admission.rs:71`, `:90` and `services/validation.rs:245` only check that a row exists:
     unchanged.
   - `wire/state.rs:458-468` (`append_handling_coefficients`, called by the catalog writer at `wire/catalog.rs:244`)
     writes the row as today; the units go in the tail (decision 5).
   `rg -n 'hours_per_unit' rust/crates/babylon-material-circuit/src` finds them; the matches in `aid.rs`,
   `wire/equipment.rs`, `equipment/*` and the mandate lines of `orders.rs` (about L895, L975) are other figures, not
   handling, and are not changed. A reader found that is not in this list gets the rule of the list's nearest kind,
   and the hand-over names it.
4. **A table read once.** `firms.rs`, `spare_money.rs`, `restart.rs` and `bound.rs` build a map from the rows (since
   the bench's speed task). Each map's value carries `units` beside `hours_per_unit`; the arithmetic is decision 2's
   three rules, in the three functions above, never written again in a reader.
5. **Bytes.** A catalog whose every handling row has `units == 1` writes today's bytes. Otherwise it writes
   `HANDLING_BLOCK_CATALOG_SCHEMA_VERSION: u16 = 10` right after the domain bytes and their `0`, before every version
   the chain writes there today (9, 8, 7 or 6, `wire/catalog.rs:14-28` and `:205-232`), then every byte the same
   catalog writes without it, then the tail: a `u32` count and each handling row's `units` as `u64` big-endian, in
   the rows' canonical order. There is no catalog decoder (`wire/catalog.rs` writes bytes only), so nothing reads the
   tail.
6. Contract: the handling coefficient's row list gains `units`; the merchant admission line gains "hours for a
   quantity are rounded up, units for hours rounded down, a cost per unit rounded up; with units 1 the rule is
   today's"; the catalog version line gains version 10 and its tail.

- [ ] **Step 1: Write the failing tests.**
  - `a_block_of_units_takes_its_hours_rounded_up` (`catalog.rs` tests): a row of 3 hours for 40 units gives
    `handling_hours` 1 for 1 unit, 3 for 40, 4 for 41, 0 for 0; `handled_units` 13 for 1 hour, 40 for 3, 53 for 4;
    `handling_cost_per_unit(3, 40, 30_000_000)` is 2,250,000; `handling_cost_per_unit(1, 3, 10_000_000)` is 3,333,334.
  - `a_row_of_zero_units_is_refused`: `MerchantInvariant`.
  - `blocks_change_the_catalog_bytes_only_when_used`: a catalog fixture with one row at 40 units writes, after the
    domain bytes and their `0`, the `u16` 10, and its bytes end with the tail (the `u32` row count, then each row's
    units in order, 40 among them); the same fixture with that row at 1 unit writes no 10 and no tail. That every
    all-ones catalog keeps its bytes is held by the pins of `binary(shipped_world_bytes)` and of the existing catalog
    tests, unchanged.
  - `a_shop_with_blocks_sells_what_its_hours_handle` (`handling_blocks.rs`): one retailer, food at a row of 1 hour for
    10 units, 7 hours of labor, 100 units in stock, three households needing 30 each: it hands over 70 units and
    records 7 handling hours, and its labor available falls by 7.
  - `spare_money_buys_whole_blocks` (`handling_blocks.rs`): a row of 1 hour for 10 units, a gap of 25 units, a wage of
    $20 and spare money of $50: 2 blocks, 20 units, 2 hours, $40 spent.
  - The existing tests of `binary(market_clearing)`, `adjustment` and `recurring` keep their literals: every row of
    theirs is given `units: 1`, and no figure moves.
- [ ] **Step 2: Run them and see them fail.** `-p babylon-material-circuit -E 'test(catalog::tests) |
  binary(market_clearing)'`: does not compile.
- [ ] **Step 3: Implement** decisions 1 to 6, and fill every literal.
- [ ] **Step 4: Run** the crate, `-p babylon-circuit-worlds` (it has no ignored tests; its crate run covers it), `-p
  babylon-tick`, `mise run rust:test:q -- -p babylon-persistence`, `binary(shipped_world_bytes)`,
  `binary(national_household_units)`; and, in the background, `mise run rust:test:q -- -p babylon-material-circuit
  --test adjustment_bench -E 'test(/^reproduces_/)' --run-ignored only`. Expected: pass, no pinned value moved.
- [ ] **Step 5: Gate and commit** with the subject above. The hand-over lists every reader changed, with its file and
  line, and the rounding it now uses (decision 3's list, and any reader found beside it).

What the player would see: nothing yet; it lets a shop's hours follow what households buy in small units.

### Task 3: Wants and the shop goods they name (compiler)

Commit `feat(economy): compile each account's comforts and luxuries`.

**Files:**
- Modify: `rust/crates/babylon-persistence/src/national_economy/opening/templates.rs` (`household_wants`);
  `opening/build.rs` (`finish`, after `sort_principals` at L276 in the copy); `opening/markets.rs` (`households`,
  `retail_hours`, `retail_stock`); `opening/actors.rs` (`handling_requirements`);
  `rust/crates/babylon-persistence/src/economic_catalog/{model.rs, compile.rs}` (`HandlingRequirement` gains `units`;
  `compile.rs` copies it where it writes `hours_per_unit`, line 201 in the copy); `economic_catalog/michigan.rs`
  (its rows get `units: 1`)
- Test: `tests/national_twelve_trades.rs`; crate tests of `templates.rs` and `markets.rs`

**Interfaces:**
- Consumes: `GameWant`, `GameHandling` (Task 1); `HouseholdWant`, `WantTier`, `MAX_HOUSEHOLD_WANTS` (engine).
- Produces:

```rust
/// The wants of every household account of the opening, in canonical order (principal, tier, good, unit).
pub(super) fn household_wants(policy: &NationalGamePolicy, households: &[EconomicHouseholdSeed])
    -> Result<Vec<HouseholdWant>>;
/// The storable goods the shop handles: every storable good a need or a want names, with its handling.
pub(super) fn shop_goods(policy: &NationalGamePolicy) -> Result<Vec<(String, GameHandling)>>;
// economic_catalog::HandlingRequirement gains `units: u64` (1 under schema 7).
```

**Decisions:**
1. **Who wants.** Every household account of the opening, domestic and abroad (call 13: abroad the tiers apply), gets
   one `HouseholdWant` per scenario want row, with its tier, good, unit, basis and units. A `Households` want is left
   out for a collective residence (the engine refuses it there, as `markets.rs` leaves out a household need). The
   wants must stay within `MAX_HOUSEHOLD_WANTS` (262,144), and the purchase rows, needs and wants together, within
   `MAX_HOUSEHOLD_NEEDS` (131,072; stage 3's Task 2, decision 5); else `NationalOpeningError::Bounds`. An account
   named in the scenario's luxury scales (its part's label and its budget key: every account of that part and key,
   an account carved from another with its parent; a scale that names no account is `NationalOpeningError::Policy`)
   has
   each of its luxury wants at `floor(units_per_basis x basis count x bps / 10_000)` in place of `units_per_basis x
   basis count` (call 20); its comforts are not scaled. Test: `a_scaled_account_wants_more_luxuries` (the fixture
   with Wayne's owner accounts at 12,500: each one's leisure want is `floor(2 x persons x 5 / 4)`, and no other
   account's want moves).
2. **How a want reaches its seller** (stage 3, Task 2, decision 5). An account's purchase rows are keyed by every
   product it needs or wants. A want-only row has `target_closing_stock: 0`, `maximum_purchase` equal to the want's
   quantity times `retailer_buffer_periods`, `enabled: true`; its seller is the account's retailer for a storable good
   and its service provider for a service, found as for a need; a want-only service adds its `ServiceConnection`.
3. **The shop's goods.** `retail_stock` and `procure` run for every shop good (decision 1's wants included), with the
   retailer's required quantity the sum of needs and wants of its accounts, every want in full. This is meant: a band
   whose money reaches only part of its tiers leaves stock above its sales, and the shop opens with that stock.
   `handling_requirements` writes one row per shop good under schema 8, `hours_per_unit = handling.hours`, `units =
   handling.units`; under schema 7 it is today's. `retail_hours` (the hours a fallback retailer reserves) counts needs
   and wants: `ceil(units x hours / block)` per good under schema 8, today's sum under schema 7.
4. **The retail charge.** The shop's opening price of a good is the producer's price plus `ceil(handling.hours x
   retailer wage / handling.units)` under schema 8 (`markets.rs` `retail_stock`, today `hours_per_unit x wage`), the
   engine's cost per unit at a block (Task 2, decision 2), with the minimum and maximum moved by the same charge, as
   today.
5. **Where the wants are filled.** `templates::market_clearing(policy)` keeps its signature and its call in
   `Builder::new` (`build.rs:365`), which runs before any household exists. `finish` fills the policy's
   `household_wants` from `household_wants` after `sort_principals`, so wants are in canonical principal order.
   `plans_from_spare_money` stays `false` and `adjustments` empty: the bench turns rules on itself.
6. Readers of purchase rows as needs elsewhere in the persistence crate (`organizer_runtime/material_preview.rs`,
   `production_projection/*`, `qualification_audit/production_renewal.rs`; stage 3's last section) are on the tick's
   road, which cannot play schema 8 yet. They are not changed here; the later plan that carries schema 8 through the
   tick does.

- [ ] **Step 1: Write the failing tests** (`national_twelve_trades.rs`, on the fixture with two want rows added in the
  test: comfort `consumer_goods` 3 per person, luxury `leisure` 2 per person, and `handling_hours = 1, handling_units
  = 1` on `consumer_goods`):
  - `every_account_wants_its_tiers`: the catalog's market policy has one want row per account and want row, but none
    of `Households` basis for a collective residence; sorted; each quantity as `HouseholdWant::quantity` gives it.
  - `every_want_has_a_seller_that_offers_it`: every want has a purchase row of its account whose seller has an offer of
    the good, and a want-only row has target stock 0; every want-only service has a connection.
  - `the_shop_handles_consumer_goods`: every retailer that serves an account wanting consumer goods has a handling row
    for them, an offer, opening stock and a replenishment row.
  - `a_handling_block_sets_the_retail_charge` (`markets.rs` crate test): hours 3, units 40, wage $30: the charge is
    2,250,000 micros (`ceil(3 x 30,000,000 / 40)`).
  - `the_fixture_without_wants_keeps_its_rows`: with no want rows the fixture's purchase rows, handling rows and offers
    equal their counts before this task. Write this test first, with its three literals empty, and run it alone on
    the unchanged code (`-E 'test(the_fixture_without_wants_keeps_its_rows)'`): it prints the three counts and fails;
    write those counts in before changing any code.
  - `too_many_purchase_rows_are_refused` (`markets.rs` crate test): one more purchase row than `MAX_HOUSEHOLD_NEEDS`
    gives `Err(Bounds)`.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement** decisions 1 to 6.
- [ ] **Step 4: Run** `binary(national_twelve_trades)`, `binary(national_opening)`, `binary(captured_economic_catalog)`,
  `binary(shipped_world_bytes)`, `binary(national_household_units)`, the crate.
- [ ] **Step 5: Gate and commit** with the subject above.

What the player would see: households that buy cars and meals out once their needs are met (on the bench now; on
screen when the game's turn carries wants).

### Task 3b: A want's quantity may be scaled (the engine)

Commit `feat(material-circuit): a want's quantity may be scaled`.

**Why: found by Task 3's review.** Call 20 has an account above its three tiers buy its luxuries times a scale, "so
that it spends all" (design call 4), and Task 3's decision 1 sets the scaled want at `floor(units_per_basis x basis
count x bps / 10_000)`. The engine's `HouseholdWant::quantity` is `count x units_per_basis` and has no field that
could carry a scale, so Task 3 as committed (`bef4dd731`) floors the scale on ONE person's units: at 12,500 a
luxury of 2 a person stays 2. Part II writes want rows as small whole units (Task 11, decision 9) and its scales
have a median of 1.25, so scaled a person they would mostly do nothing, in silence. The scale has to act on the
account's whole quantity, and only the engine knows the count.

**Files:**
- Modify: `rust/crates/babylon-material-circuit/src/recurring/model.rs` (`HouseholdWant`, `quantity`),
  `src/catalog.rs` (the refusal), `src/wire/catalog.rs` (catalog version 11 and its tail), `src/wire/state.rs`
  (`MATERIAL_CIRCUIT_SOURCE_SHA256`), `contracts/material_circuit_v4.yaml`; every construction of a
  `HouseholdWant` (the engine's sources and tests, `babylon-circuit-worlds/src/doubled/catalog.rs`,
  `babylon-persistence` `opening/templates.rs` and `tests/national_twelve_trades.rs`) gains the neutral scale
- Test: `src/catalog.rs` tests, `src/recurring/households_tests.rs`, `tests/market_clearing/` (its wants cases)

**Interfaces:**

```rust
/// A want row as written: 10,000 parts in 10,000.
pub const WANT_SCALE_ONE_BPS: u32 = 10_000;
/// The largest scale a want row may carry: a hundred times the row.
pub const MAX_WANT_SCALE_BPS: u32 = 1_000_000;
pub struct HouseholdWant {
    pub principal_id: FinalDemandPrincipalId,
    pub tier: WantTier,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub basis: HouseholdNeedBasis,
    pub units_per_basis: u64,
    /// Parts in 10,000 of the row's quantity that the account buys: 10,000 is the row as written.
    pub scale_bps: u32,
}
// HouseholdWant::quantity(cohort) = floor(count x units_per_basis x scale_bps / 10_000).
```

**Decisions:**
1. **The quantity.** `count x units_per_basis` first, by today's code and with today's refusals (the wrong
   principal, a household basis for a collective residence, zero units, overflow). At 10,000 that figure is
   returned as it is: the old path, the same operations in the same order. At any other scale it is multiplied by
   `scale_bps` in u128, divided by 10,000 rounded down, and brought back to u64 (`Arithmetic` when it does not
   fit).
2. **One place computes it.** Every reader of a want's quantity goes through `HouseholdWant::quantity` (households'
   buying, the tiers' lists, the admission of service wants). A reader that multiplies `units_per_basis` by a count
   on its own is changed to call it; the hand-off lists the readers found.
3. **The refusal.** A want with `scale_bps` 0 or above `MAX_WANT_SCALE_BPS` is `MarketClearingInvariant`, where
   `units_per_basis == 0` is refused today (`catalog.rs`).
4. **Bytes.** A catalog whose every want is at 10,000 writes today's bytes, so every measured small world, the
   shipped world and the fixture keep theirs. A catalog with a want at another scale writes catalog version 11
   after the domain bytes (after version 10 where both are written), then every byte the same catalog writes
   without it, then a tail: the count of want rows as u32 and each row's `scale_bps` as u32, in the rows' order
   (after the handling blocks' tail where both are written). This is Task 2's pattern for a handling row's units.
   No state's bytes change: a want is a row of the catalog. If another encoding of a want row exists (search for
   writes of `units_per_basis`), it carries the scale by the same rule, and the hand-off names it.
5. **Every existing construction** gains `scale_bps: WANT_SCALE_ONE_BPS`, and no existing test's figure moves.
6. **The contract.** The lines of `contracts/material_circuit_v4.yaml` that describe a want and the catalog's
   versions gain the scale, its rounding and version 11 with its tail; `MATERIAL_CIRCUIT_SOURCE_SHA256` is filled
   once from the failing run of `tests/weighted_freight.rs`.

- [ ] **Step 1: Write the failing tests.**
  - `a_scaled_want_is_floored_on_its_whole_quantity` (`households_tests.rs` or `model.rs` tests): a cohort of 5
    persons and a luxury of 2 a person: 10 at 10,000; 12 at 12,500 (the floor of 12.5); 20 at 20,000. A luxury of 1
    a person for 3 persons at 15,000: 4. A scale of 9,000 on 10 units: 9. A product that passes u64 is
    `Err(Arithmetic)`.
  - `a_scale_out_of_range_is_refused` (`catalog.rs` tests): `scale_bps` 0 and 1,000,001 are each
    `Err(MarketClearingInvariant)`; 1 and 1,000,000 are admitted.
  - `a_scale_changes_the_catalog_bytes_only_when_used` (`catalog.rs` tests, beside
    `blocks_change_the_catalog_bytes_only_when_used`): a catalog with wants at 10,000 has the bytes it had before
    this task (its pinned digest does not move); one want at 12,500 gives other bytes, which begin with version 11
    after the domain bytes and end with the tail; two catalogs that differ only in one scale differ in bytes; a
    catalog with a block above 1 and a scaled want writes version 10, then 11, and the two tails in that order.
  - `a_scaled_luxury_is_bought_when_money_reaches_it` (`tests/market_clearing/`, on its wants fixture): an account
    whose money reaches all of its luxury buys `floor(2 x persons x 5 / 4)` units of it with the row at 12,500 and
    `2 x persons` with the row at 10,000; nothing else of the period differs but what follows from those units.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the `babylon-material-circuit` crate, `babylon-circuit-worlds`, `babylon-tick`, and of
  `babylon-persistence` `binary(shipped_world_bytes)`, `binary(national_household_units)` and
  `binary(national_twelve_trades)`. Then, in the background and AFTER the last change under
  `babylon-material-circuit/src`, the long tests once: `-p babylon-material-circuit --test adjustment_bench -E
  'test(/^reproduces_/) | test(hours_fold_every_reference_run)' --run-ignored only`. A `reproduces_` test that
  fails is a stop.
- [ ] **Step 5: Gate and commit** with the subject above. Hand over: the readers of a want's quantity found; every
  construction site changed; the contract's changed lines; the constant's old and new value.

What the player would see: nothing yet. Task 3c uses it.

### Task 3c: A scaled account's luxuries are scaled whole (compiler)

Commit `fix(economy): scale an account's luxuries on its whole quantity`.

**Why.** It completes Task 3's decision 1 on the engine's scale (Task 3b), and closes the review of Task 3. As
committed, the compiler floors the scale on one person's units (`templates.rs` `scaled_units`), and the test
`a_scaled_account_wants_more_luxuries` was moved from the plan's 2 a person to 4 a person so that the floor passed.

**Files:**
- Modify: `rust/crates/babylon-persistence/src/national_economy/opening/templates.rs` (`household_wants`;
  `scaled_units` goes), `opening/markets.rs` (`purchases`, `retail_hours`, `check_bounds`), `opening/build.rs`
  (`wire_wants`, the scales kept once)
- Test: `tests/national_twelve_trades.rs`; crate tests of `markets.rs`

**Decisions:**
1. **The want row.** A luxury row of an account named in the luxury scales carries `scale_bps` = its scale. Every
   other want row carries 10,000: a comfort, and any row of an account with no scale. `units_per_basis` is the
   scenario's own figure. `scaled_units` is removed.
2. **One quantity.** Whatever the compiler sizes from what an account buys uses the engine's own figure,
   `floor(units_per_basis x count x bps / 10_000)`: the wanted units of a purchase row (`purchases`), a shop's
   stock and offers, and the hours a fallback retailer reserves (`retail_hours`, which today counts the scenario's
   rows unscaled: it is given its customers' accounts, or their scaled units, and not only their persons and
   households). One helper in `templates.rs` computes it for a `GameWant`, a count and an optional scale, and a
   crate test holds it equal to `HouseholdWant::quantity` on the same figures.
3. **The scales are found once.** `templates::luxury_scales` runs once and its map is kept on the `Builder` for
   `markets::households` and `wire_wants` (today it runs twice and nothing says the two agree).
4. **The bound on wants** is checked where the want rows are written; `check_bounds` loses the argument that is
   always 0 at its call.
5. Schema 7 has no wants: every byte of the shipped world stays.

- [ ] **Step 1: Write the failing tests.**
  - `a_scaled_account_wants_more_luxuries` as Task 3's Step 1 has it: the fixture with leisure a luxury at 2 a
    person and Wayne's owner accounts at 12,500. Each such account's leisure want, by the engine's
    `HouseholdWant::quantity` on its cohort, is `floor(2 x persons x 5 / 4)` and above `2 x persons`; its purchase
    row's wanted units are that number; no other account's want moves and no comfort is scaled.
  - `a_scale_that_names_no_account_is_refused`: a `[luxury_scale]` entry of a rightly formed label that no account
    of the opening has (for example a position its hub does not hold) is `Err(NationalOpeningError::Policy)`.
  - `a_fallback_shop_reserves_hours_for_scaled_luxuries` (crate test of `markets.rs`): with a storable good wanted
    as a luxury and one customer account scaled, the hours reserved count that account's scaled units.
  - `the_compiler_and_the_engine_count_a_want_alike` (crate test): the helper of decision 2 equals
    `HouseholdWant::quantity` for the cases of Task 3b's first test.
  - `the_shipped_wants_are_unchanged`: `binary(shipped_world_bytes)`.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `binary(national_twelve_trades)`, `binary(national_opening)`, `binary(shipped_world_bytes)`,
  `binary(national_household_units)`, the crate.
- [ ] **Step 5: Gate and commit** with the subject above.

What the player would see: a rich household in a rich place spends what it earns, on more of its luxuries.

### Task 4: The national fund, the split taxes and the programs (compiler)

Commit `feat(economy): open the national fund, its share of both taxes and its programs`.

**Files:**
- Create: `rust/crates/babylon-persistence/src/national_economy/opening/fund.rs`
- Modify: `opening/financial.rs` (`wire`, `household_support`, `support_unit_price`, `public_provider_grant` at L352
  and its call at L71); `opening/equipment.rs` (`wear_per_period`); `opening.rs` (module); `opening/build.rs` (the call
  order); `national_economy/county_review.rs` (it reads `county_support_unit_price`, L483);
  `rust/crates/babylon-persistence/tests/support/country_bench.rs` (about L742, where it applies `with_fund`)
- Test: `tests/national_twelve_trades.rs`; `fund.rs` and `equipment.rs` crate tests

**Interfaces:**
- Consumes: `GameFundPolicy`, `GameProgram`, `GameMachines` (Task 1); `PublicProgram`, `PublicProgramKey`,
  `PublicProgramTerms`, `PublicSpendingRule::CashInProportion` (engine).
- Produces:

```rust
/// The fund's account: `PublicAccountId::from_bytes(sha256_of(b"NationalFundV1\0"))`.
pub(in crate::national_economy) fn fund_account() -> PublicAccountId;
/// Where the fund sits: county 11001.
pub(in crate::national_economy) fn fund_location() -> Result<EconomicLocation>;
/// A domestic payer's two rows for one tax: the place's share and the fund's.
/// (place, fund): fund = floor(rate x share / 10_000), place = rate - fund.
pub(super) fn split_rate(rate_bps: u16, fund_share_bps: u16) -> (u16, u16);
/// The programs' recipients, by the household keys of the opening.
pub(super) fn recipients(builder: &Builder<'_>, rule: GameProgramRecipients) -> Result<Vec<FinalDemandPrincipalId>>;
pub(super) fn wire(builder: &mut Builder<'_>) -> Result<()>;
/// (equipment.rs) One period of a site's machines' wear under schema 8: the machines `machine_units` gives for
/// `actor.force`, times the equipment's opening price at the actor's price scale, over `machine_life_periods`,
/// rounded up. Task 6 keeps this signature; its count follows Task 6's rule.
pub(super) fn wear_per_period(builder: &Builder<'_>, actor: &ActorContext) -> Result<Currency>;
/// (equipment.rs) Its arithmetic: ceil(machines x price / life_periods). `Arithmetic` on overflow or a life of 0.
fn wear(machines: u64, price: Currency, life_periods: u64) -> Result<Currency>;
```

**Decisions:**
1. **The fund** (stage 4's later plan B, item 1; the bench's `country_fund.rs` does the same in memory): one public
   account, `fund_account()`, located at `fund_location()`, its budget `PublicBudget { period_cap: 0, cash_floor: 0,
   rule: CashInProportion }`. Foreign regions and dependencies hold no program and pay no fund row.
2. **The split** (plan B item 2). For each tax row whose payer is domestic: `split_rate(rate, share)` gives the fund
   `floor(rate x share / 10_000)` and the place `rate - fund`, so a payer's two rows sum to its rate. A fund rate of 0
   makes no fund row. The share is the scenario's one national share of that tax, the same in every place (ADR313 O12:
   "one national fund that takes a share of both taxes everywhere"). The count must stay under `MAX_TAX_POLICIES`
   (262,144); rows sorted by `(payer, basis, public_recipient)`.
3. **The places' bodies** keep the capped rule and their rows (plan B item 3): provision grants, county support, the
   County Review's relief, the City PD. The County Review's account holds no program (W15 of the bench's plan).
4. **The programs** (plan B item 4; call 18), payer the fund, ranks from the scenario. `no_earner`: `PerPerson`, its
   recipients every domestic account whose key is `NoEarnerNonowner` or `NoEarnerOwner`. `laid_off`: `AfterLayoff`,
   its recipients every domestic account whose key is `EarningLowerPaidHalf`, `EarningBetterPaidForty`,
   `EarningOwner` or `CollectiveResidence`. `residence` is expanded into one engine `PerPerson` program for each
   entry of its `amounts_micros`: key `residence_<hub geoid>` (15 bytes, within `PublicProgramKey`), recipients the
   `CollectiveResidence` accounts of every part of that place, the amount the entry's (an entry whose county is no
   place's hub, or whose place has no such account, is `NationalOpeningError::Policy`: the engine refuses a program
   with no recipient); a place with no entry has no such program. So a
   residence is paid for its residents with no job at the opening (the builder writes the amount a resident times
   that share), and a resident who loses a job in play is paid by `laid_off` as any worker is: the engine allows one
   after-layoff program a household and any number of per-person ones (`financial/validation.rs`). The programs are
   then 2 plus the places with an entry, within `MAX_PUBLIC_PROGRAMS` (256); more is `NationalOpeningError::Bounds`.
   Each domestic account is in one program, or, a residence, in `laid_off` and its place's residence program, by
   what it was at the opening (O12; call 14: owner or not). No layoff record at the opening (plan B item 5): those
   looking for work keep today's county support (call 16).
5. **The fund's cash** (O13): `reserve_periods x` the sum of the dues at the opening of `no_earner` and of every
   residence program (`amount x persons` of each recipient's cohort). It is opening cash, not carved out of the places'
   bodies. The bench's stand-in could not
   carve it (`reports/country-bench-2026-11-24/README.md`, "Benefits"); a compiled opening can give it.
6. **The support unit under schema 8.** Today one person's support is `reserve_food_support_periods x` one unit of
   food (`financial.rs` `support_unit_price`). With small units that is a fraction of a day's food. Under schema 8 it
   is `reserve_food_support_periods x food need units_per_basis x` the food price: one period of one person's food
   need. The County Review's unit follows (`county_review.rs` reads `county_support_unit_price`). Under schema 7 both
   are today's.
7. **Both taxes' rates** are the scenario's `[financial]` figures, as today.
8. **A public provider's grant covers its wear** (schema 8). Today the grant is `max(0, payroll + inputs at planned
   batches - fee receipts)` (`financial.rs` `public_provider_grant`, L352-391). Under schema 8 it is `max(0, payroll +
   inputs + wear_per_period - fee receipts)`, so a public provider replaces its machines as a private workplace does
   from its margin. Under schema 7 the grant is today's. Until Task 6, `machine_units` counts machines by today's
   rule through Task 1's helper; Task 6 changes the count and the grant follows it.
9. **The fixture's pins.** With shares 0 the fixture's tax rows keep their values, but its opening gains the fund's
   account, budget, cash and its two programs (its `residence` row is empty), and its public providers' grants gain
   their wear. A stage 2 pin that
   counts public accounts, budgets or institutional cash, or values a grant, is re-pinned from the first failing run
   and listed in the hand-over with its old and new value; `the_twelve_trades_sizes` of `national_household_units.rs`
   is re-pinned the same way and listed; every other pin keeps its value.
10. **The bench keeps an opening's own fund.** `country_bench.rs` (about L742) applies `country_fund::with_fund` only
   to an opening that holds no `PublicProgram`; an opening that carries its own fund and programs keeps them, since
   `with_fund` would push a second public account, re-split every tax row and replace `programs`
   (`tests/support/country_fund.rs:248-310`). The shipped world holds no program and is funded as today.

- [ ] **Step 1: Write the failing tests.**
  - `split_rate_keeps_each_rate` (`fund.rs`), results as (place, fund): `(2320, 2530)` gives (1,734, 586); `(1,
    5000)` gives (1, 0); for every rate 0 to 10,000 and shares 0, 2,530 and 10,000 the parts sum to the rate.
  - `wear_is_a_period_of_the_machines_life` (`equipment.rs` crate test of `wear`): 100 machines at $1,000.00 and a life
    of 100 periods give $1,000.00; 3 machines at $1.00 and a life of 100 periods give 30,000 micros; 1 machine at
    1,000,001 micros and a life of 100 periods gives 10,001 micros (rounded up).
  - On the fixture with fund shares 2,530 and 2,530 set in the test (`national_twelve_trades.rs`):
    - `the_fund_takes_its_share_of_each_tax`: every domestic payer has two rows of each basis whose rates sum to its
      rate, one to the fund, and the fund's rate is the same function of the payer's rate in every place; no foreign
      payer has a fund row; the count of rows is printed and below 262,144.
    - `every_domestic_account_is_in_its_programs` (the fixture with `amounts_micros = { "26163" = 700000000 }` set
      in the test): each domestic household account is a recipient as decision 4 says: a no-earner account of
      `no_earner` alone, an earning account of `laid_off` alone, a residence of `laid_off` and, in Wayne, of
      `residence_26163` at $700.00 a person; no other place has a residence program; no foreign account is a
      recipient.
    - `the_fund_opens_with_two_periods_of_its_payments`: the fund's cash equals `2 x sum(amount x persons)` over the
      recipients of `no_earner` and of every residence program; its budget is `CashInProportion` with cap 0; no
      layoff record.
    - `the_support_unit_is_a_period_of_food`: the county support of one person equals `food units_per_basis x` the
      food price; the shipped policy's is today's (`national_game_policy.rs:402-407` and Task 0's digests of stage 2
      unchanged).
    - `a_public_provider_s_grant_covers_its_wear`: every domestic public provider's grant equals `max(0, payroll +
      inputs + wear_per_period - receipts)`, recomputed in the test; the shipped world's grants are today's
      (`binary(shipped_world_bytes)`).
  - `the_bench_keeps_an_opening_s_own_fund` (`national_household_units.rs`): the fixture's bench opening with benefits
    holds exactly one fund account and the fixture's two programs.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `binary(national_twelve_trades)`, `binary(national_county_review)`, `binary(national_opening)`,
  `binary(shipped_world_bytes)`, `binary(national_household_units)`, the crate.
- [ ] **Step 5: Gate and commit** with the subject above.

What the player would see: each place's body and the national fund as public accounts, the benefits paid and cut
(through the client's public-body panel, a later plan; on the bench now).

### Task 5: Trade by product (compiler)

Commit `feat(economy): buy and sell abroad by product`.

**Why, read from the code.** The 25% cap is not the engine's: it is the national compiler's `procure`
(`opening/markets.rs`, `foreign_cap = required x foreign_procurement_bps / 10_000`), and the same figure sets what a
foreign buyer takes from the United States, since a foreign buyer's second supplier is a domestic county
(`secondary_candidates`). So one figure is both every import share and every export share. Equipment is bought abroad
only when no home supplier exists (`equipment.rs`, `policies`), and the engine admits one investment policy, with one
supplier, per process (`equipment/validation.rs`, `unique(&e.investment_policies, |r| r.process_id)`).

**Built after Task 6.** The replacement machines this task counts are Task 6's (`replacement_target_units`, the
machines for the whole workforce); Task 6 uses nothing of this task.

**Files:**
- Modify: `rust/crates/babylon-persistence/src/national_economy/opening/{markets.rs, equipment.rs}`
- Test: `tests/national_twelve_trades.rs`; `markets.rs` crate tests

**Interfaces:**

```rust
/// The share of `key` a buyer at `location` takes abroad: a domestic buyer's import share, a foreign or dependency
/// buyer's export share of its region (from the United States). Schema 7: the single cap.
pub(super) fn foreign_share_bps(policy: &NationalGamePolicy, location: EconomicLocation, key: &str) -> Result<u16>;
/// Which domestic processes buy their machines abroad (schema 8): processes in order of
/// sha256(b"NationalEquipmentAbroadV1\0" ++ process id), taken while the replacement machines of those taken stay at
/// or under `floor(total replacement machines x import_bps["equipment"] / 10_000)`; a process whose own machines would
/// pass it is skipped, and the next tried.
pub(super) fn equipment_abroad(builder: &Builder<'_>) -> Result<BTreeSet<ProcessId>>;
```

**Decisions:**
1. `procure` reads `foreign_share_bps(location of the buyer, key)` in place of the single cap; everything else of the
   rule (primary, secondary, the cap given only when a secondary exists) is today's.
2. **Equipment.** Under schema 8 a domestic process in `equipment_abroad` takes its investment supplier from
   `secondary_supplier`; every other domestic process from `primary_supplier`, and from `secondary_supplier` only when
   it has no home supplier, as today; either cap is the whole `starts`. A foreign or dependency process takes its
   supplier as today (its own primary, else a domestic secondary); with no own supplier its cap is its region's
   `export_bps["equipment"]`. Under schema 7 today's rule holds. This replaces Task 1's helper at `equipment.rs` (about
   L275).
3. The share measured by machines, not money: every machine has one price (Task 6), so the share of machines is the
   share of money.
4. **The fixture's pins.** The fixture sends no equipment abroad by share (its share is 0, Task 1) and keeps 2,500 for
   every good, so its rows keep their values; if one moves, stop and tell the lead.

- [ ] **Step 1: Write the failing tests** (fixture; the test sets `import_bps` food 1,102, consumer goods 4,277,
  equipment 4,104, the others 2,500, and Canada's `export_bps` consumer goods 1,000):
  - `imports_follow_each_product`: for a domestic buyer of food with a foreign secondary, the foreign row's cap is
    `floor(required x 1102 / 10_000)` and the domestic row's the rest; for consumer goods, 4,277.
  - `a_foreign_buyer_takes_its_export_share`: a Canadian retailer's domestic row for consumer goods has cap
    `floor(required x 1000 / 10_000)`.
  - `equipment_abroad_follows_its_share`: the replacement machines of domestic processes with a foreign investment
    supplier are at most `floor(total x 4104 / 10_000)` and within the largest single process's machines of it.
  - The shipped opening's replenishment and investment rows are unchanged (`binary(shipped_world_bytes)`).
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `binary(national_twelve_trades)`, `binary(national_opening)`, `binary(shipped_world_bytes)`,
  `binary(national_household_units)`, the crate.
- [ ] **Step 5: Gate and commit** with the subject above.

What the player would see: a share of cars and machines made abroad, and what a foreign region buys from the country
(on the money map's foreign flows, when the game's turn plays schema 8).

### Task 6: Machines by trade, of every age, for the whole workforce (compiler)

Commit `feat(economy): machines by trade and of every age`.

**Why, read from the code.** Machine counts follow batch size: `machine_units` is `batches /
batches_per_unit_per_period` (`equipment.rs`), with one definition for every trade (`definition`). So 16-hour
batches give one machine for four workers and 160-hour batches one for forty, and a builder that changes batch
size to round recipes changes machine counts. Machines open at one of four ages by the first byte of the site id
(`opening_remaining_service_bps`), so a quarter of the workplaces replace everything in one period (design section
3). Opening machines are sized for `employed`, the installed maximum for `force`. For every coarsened site the
machines come from the grain's endowment, not from `machine_units`: `opening_asset` takes `units`, `remaining` and
the carrying value from `builder.endowments` (`equipment.rs:146-198` in the copy), and `machine_units` returns the
endowment's counts (`equipment.rs:209-216`). Those are computed in `grain/build.rs`
`OpeningProductiveEndowment::source` (at `0a0cba1dd`: L790 and L799 `div_ceil(batches_per_unit_per_period)`, L800
`opening_remaining_service_bps`, L804 `service_batches_per_unit`) and summed by `accumulate` (L854).

This task is built before Task 5, which counts the replacement machines set here.

**Files:**
- Modify: `rust/crates/babylon-persistence/src/national_economy/opening/equipment.rs`;
  `rust/crates/babylon-persistence/src/national_economy/grain/build.rs` (`OpeningProductiveEndowment::source` and
  `accumulate`)
- Test: `tests/national_twelve_trades.rs`; `equipment.rs` crate tests

**Interfaces:**

```rust
/// One definition per trade under schema 8: its id from sha256(b"NationalEquipmentDefinitionV2\0" ++ good ++ unit
/// ++ trade key), `batches_per_unit_per_period = ceil(work_hours_per_person x workers_per_machine /
/// labor_hours_per_batch)`, `service_batches_per_unit = batches_per_unit_per_period x machine_life_periods`.
fn definitions(builder: &Builder<'_>) -> Result<BTreeMap<EconomicFunction, EquipmentDefinition>>;
/// A site's machines under schema 8: ceil(persons / workers_per_machine of its trade).
fn machines_for(persons: u64, workers_per_machine: u64) -> Result<u64>;
/// The most cohorts a process may open with: min(8, floor(65_536 / processes)); `Bounds` when that is 0.
pub(super) fn machine_ages(processes: u64) -> Result<u64>;
/// A process's opening cohorts under schema 8: up to `ages` cohorts of every age (decision 3).
fn opening_cohorts(process: ProcessId, units: u64, life_batches: u64, ages: u64)
    -> Result<Vec<InstalledEquipmentCohort>>;
```

**Decisions:**
1. **Several definitions of one good.** The engine admits them: `validate_content` checks definitions unique by id
   only; every lookup goes process, binding, definition id (`babylon-material-circuit` `equipment/lookup.rs`
   `definition`); `validate_definitions` checks each definition's good is storable; installation inputs are keyed by
   `(definition_id, good, unit)` and read per definition (`equipment/installation.rs` `material_requirements`);
   offers and investment are keyed by the definition's good. So under schema 8 each of the eleven recipe trades has
   its own definition (`definitions`), each process is bound to its trade's, and each definition gets its own
   `InstallationInput` rows from `[equipment] installation_inputs` (today `wire` writes them for one definition only,
   `equipment.rs:34-42`). `the_engine_admits_a_definition_per_trade` guards it.
2. **Machines for the whole workforce** (O14): under schema 8 a site opens with `machines_for(force,
   workers_per_machine)` machines, its `replacement_target_units` is that count, and `maximum_installed_units` is the
   same. The grain's endowment carries no machine figures under schema 8 (`equipment_units`,
   `workforce_equipment_units`, `equipment_service_batches` and `equipment_carrying_micros` are 0 in
   `OpeningProductiveEndowment::source`), and `opening_asset` and `machine_units` compute every site's machines,
   coarsened or not, from its force and its trade's `workers_per_machine`. Under schema 7 today's rule, endowments
   included. `wear_per_period` (Task 4) keeps its signature and reads the new count and the trade's definition.
3. **Every age** (O14). Let `A = machine_ages(P)`, `P` the number of processes of the opening with machines. A process
   with `u` machines opens with `c = min(u, A)` cohorts; cohort `k` (0 to `c - 1`) holds `u / c` machines plus one for
   `k < u % c`; its remaining service is `life_batches x u_k x a_k / 100`, rounded down and at least 1, where `a_k = 1 +
   (k x 100 / c + s) % 100` and `s` is the first byte of the process id modulo `100 / c`. So the ages of one process are
   spread over the life, and the spread's start differs by process, and about one machine in a hundred is due each
   period across the country. Cohort ids from sha256(b"NationalOpeningEquipmentV2\0" ++ process ++ k as u8). The cohorts
   stay within `MAX_MATERIAL_CIRCUIT_ROWS` (65,536) by `A`. The shipped ten-trade opening has 7,463 sites and pools
   (`shipped_world_bytes.rs:148`, `national_household_units.rs:1006`), but distribution sites have no process and the
   twelve-trade opening has more sites, so `P` is counted, printed and pinned by the test, never assumed.
4. Carrying value of each cohort: `units_k x price x a_k / 100`, rounded down (the share of life left), as today's rule
   reads one fraction.
5. **The fixture's pins** that count or value machines (cohorts, carrying values, installation and investment rows,
   public providers' grants through their wear) move with decisions 1 to 3. They are re-pinned from the first failing
   run, and the hand-over lists each with its old and new value. No pin of the shipped world moves.

- [ ] **Step 1: Write the failing tests.**
  - `the_engine_admits_a_definition_per_trade` (`national_twelve_trades.rs`): the fixture's catalog under schema 8
    holds eleven definitions of the one equipment good, each with its own installation input rows, and
    `MaterialCatalog::try_new` returns `Ok`.
  - `machines_follow_workers_not_batches` (crate test): 400 workers, 160 hours, 4 workers a machine, batch 16 or 32
    hours: 100 machines either way; 401 workers give 101.
  - `ages_spread_over_the_life` (crate test): `opening_cohorts` for 1,000 machines, a life of 4,000 batches and 8 ages
    gives 8 cohorts of 125 whose `a_k` are 8 distinct values in `1..=100`; for 3 machines, 3 cohorts of 1.
  - `machine_ages_fit_the_row_bound` (crate test): `machine_ages` gives 8 for 7,463 processes, 6 for 10,000, 1 for
    65,536, and `Err(Bounds)` for 65,537.
  - `about_one_machine_in_a_hundred_is_due` (fixture): over all domestic cohorts, the machines whose remaining service
    ends within one period of their process's batches are between 0.5% and 1.5% of all machines (print the share);
    print and pin `P` and the count of cohorts.
  - `coarsened_sites_have_machines_for_their_force` (fixture): every domestic site with a process, coarsened or not,
    has `machines_for(force, workers_per_machine)` machines.
  - `the_shipped_equipment_is_unchanged`: shipped definitions, cohorts and investment policies as today
    (`binary(shipped_world_bytes)`).
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `binary(national_twelve_trades)`, `binary(national_opening)`, the grain's tests,
  `binary(shipped_world_bytes)`, `binary(national_household_units)`, the crate.
- [ ] **Step 5: Gate and commit** with the subject above.

What the player would see: the makers of machines with customers from the first period, and no quarter of the country
replacing everything in one period.

### Task 7: The map's pinned basis (compiler, O15)

Commit `feat(economy): fold the counties on the map's own food basis`.

**Files:**
- Modify: `rust/crates/babylon-persistence/src/national_economy/grain/build.rs` (`food`, and the read of the food need
  in `capture_membership`)
- Test: `national_economy/grain/tests.rs`; `tests/national_twelve_trades.rs`

**Interfaces:**
- Produces: `fn food(policy: &NationalGamePolicy) -> Result<(EconomicFunction, u128, u128, u128)>` keeps its signature;
  under schema 8 it returns `(Food, basis.food_labor_hours_per_batch, basis.food_output_units_per_batch,
  basis.food_grams_per_unit)`; the need's `units_per_basis` read in `capture_membership` is
  `basis.food_units_per_person` with basis `Persons`.

**Decisions:**
1. The grain reads only the map's basis under schema 8; the scenario's food recipe, need and grams no longer move a
   place. The food recipe must still exist (one recipe makes food), checked as today.
2. The membership's hours come from food workers' labor force, as today; those are the census's, not the numbers'.
3. Airports' room (O15's second sentence) is a figure of the transport policy and is not changed here: Task 16 records
   every full route of the first period, and the lead raises airports in stage 6 from that record.

- [ ] **Step 1: Write the failing tests.**
  - `the_map_does_not_follow_the_food_recipe`: the fixture, and the fixture with its food recipe changed to 160 hours
    for 3 units and its food need to 28 a person, fold into the same places (equal catchment keys and memberships).
  - `the_fixture_keeps_its_places`: the number of places and a digest of their memberships equal those of the fixture
    before this task. Write this test first, with its two literals empty, and run it alone on the unchanged code
    (`-E 'test(the_fixture_keeps_its_places)'`): it prints the count and the digest and fails; write them in before
    changing any code (187 domestic places is expected, as the shipped world has).
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the grain's tests, `binary(national_twelve_trades)`, `binary(shipped_world_bytes)`,
  `binary(national_household_units)`, the crate.
- [ ] **Step 5: Gate and commit** with the subject above.

What the player would see: the same 187 places on the map, whatever the recipes.

### Task 7a: A company takes no working capital at the opening (the fixture)

Commit `fix(economy): the twelve-trade fixture's companies take no working capital at the opening`.

**Why: a ruling of 20 November that this plan's first drafts missed, counted again on 26 November.** The Director
ruled in the economy repair that "a company no longer takes working capital at the opening". It was measured then
on the shipped scenario (`reports/economy-repair-2026-11-20/README.md`, candidate A): the sites under a
service-input floor fell from 630 to 0 in period 1, and household services went from 100% to 39% unmet. The opening
design does not repeat the ruling, and the fixture still has `[companies] opening_treasury_bps = 1000`.

What it does, from the code and the compiled opening. The compiler gives a workplace two periods of its wages and
inputs as cash (`opening/actors.rs`, `grain/build.rs` `at_place_wage`). A company takes a tenth of what is above
one payroll (`companies/treasury/opening.rs` `fund` and `sweep`, called from `opening/build.rs` with the policy's
`treasury_bps`). The engine sets a period's wages aside first
(`payments::fund_attendance`, before `ServiceClose::new` in `close_funded_production`), and lets a workplace buy a
service input only with cash above a floor of one payroll (`services/admission.rs`; the floor is `payroll` in
`opening/markets.rs`). So a company's workplace whose inputs are light beside its payroll has nothing left to buy
them with: after the sweep it holds 1.9 payrolls and 1.8 periods of inputs, and after its wages and its floor, 1.8
periods of inputs less a tenth of a payroll. In the fixture those are 644 workplaces with 54.6 million workers:

| Trade | Workplaces that cannot pay for their input in period 1 | Their workers | Share of the trade's workers |
|---|--:|--:|--:|
| Business services | 315 | 26,336,319 | 98.5% |
| Household services | 315 | 28,121,846 | 50.7% |
| Extraction | 14 | 98,562 | 15.4% |

They are the largest workplaces, so they are the ones the compiler gives the buyers to: all 186 sellers of business
services that have a buyer, and 153 of the 187 sellers of household services. The bench's own record agrees: 314
and 303 workplaces of those two trades under the service-input floor at the close of period 1. Every maker of goods
needs business services, so nothing upstream is made. With buyers dealt in proportion to people (Tasks 7b to 7d)
98.5% of the custom of business services would still go to workplaces that cannot perform: this task comes first.

**Files:**
- Modify: `rust/crates/babylon-persistence/tests/fixtures/national_twelve_trades.defines.toml`
- Test: `rust/crates/babylon-persistence/tests/national_twelve_trades.rs`

**Decisions:**
1. The fixture's `[companies] opening_treasury_bps` goes from 1000 to 0. No source file changes. The shipped
   scenario keeps its key: its bytes are pinned, and the rebuilt scenario (Task 13) replaces it.
2. The fixture's pins that follow (a company's opening money, a company-owned workplace's opening cash, the
   opening's digests) are each filled once from the first failing run and listed in the hand-over with old and new
   values. The opening's whole money is the same sum.
3. If a workplace is still short with the key at 0, the test of Step 1 fails: stop and tell the lead with the
   workplaces, their cash, payroll, floor and input cost. Do not change a floor or a cash rule.

- [ ] **Step 1: Write the failing tests** (fixture):
  - `every_workplace_can_pay_for_its_first_period`: for every domestic workplace with a service-input row, its
    opening cash, less its payroll (persons paid a wage x the policy's hours x its wage), less the row's cash floor,
    is at least what its service inputs of one period cost at their providers' opening prices. Fails today for 644
    workplaces (print the count by trade).
  - `a_company_takes_nothing_at_the_opening`: every company-owned workplace of the fixture opens with the
    compiler's own figure, two periods of its wages and inputs, and the companies' opening money is 0.
  - `the_shipped_opening_keeps_its_sweep`: `binary(shipped_world_bytes)`.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Change the key and fill the pins.**
- [ ] **Step 4: Run** `binary(national_twelve_trades)`, `binary(shipped_world_bytes)`,
  `binary(national_household_units)`, the crate.
- [ ] **Step 5: Record** the bench's baseline of the fixture once, in the background (`record_twelve_trades_sets`
  with `TWELVE_TRADES_SET=baseline`), and hand over, beside the committed record's figures: the domestic persons at
  work at the close of periods 1, 2, 5, 13 and 34; for household services and business services the workplaces
  under the service-input floor and the sales in periods 1 and 2; the unmet share of each need in periods 1 and 2;
  and whether any period was refused. The figures show what the sweep alone moves, and are no verdict. Then put
  the committed records back (`git checkout -- reports/country-opening-2026-11/`): the folder stays the set that
  its reading describes, three records of one scenario, until Task 16 records the rebuilt scenario.
- [ ] **Step 6: Gate and commit** with the subject above. No record is committed.

What the player would see: clinics, schools and offices that open with the money to run their first month.

### Task 7b: A buyer of a service is dealt its provider (compiler)

Commit `feat(economy): deal every buyer of a service a provider in proportion`.

**Why, counted from the compiled opening (26 November; "What the compiled opening showed").** `service_provider`
gives every buyer at one location the same provider of a service: the nearest location of its state that has one,
and there the site with the most people at work (`ProviderLocations::new` sorts each location's sites by `employed`;
`ids.first()`). A place has several: a median of 9 sellers of household services, 7 of business services, 6 of
public provision, by part and by owner. So in the twelve-trade opening 187 of 1,489 makers of household services
have a buyer and 64.3% of the trade's workers are at makers with none; public provision 62.4%, utility 49.0%,
premises 31.8%, business services 26.8%. With what buyers ask scaled up to what the nation's makers can make, at
most 35.7% of what household-services workers can make can be sold. The engine holds one provider a buyer and
service (`recurring/validation.rs` `unique` on `(principal_id, good_id, unit_id)`; `services/validation.rs` on
`(buyer_site_id, good_id, unit_id)`), so the mend is in who is given to whom. This task's rule, run on the same
opening outside the engine, reaches 91.9% for household services, against 95.0% if every buyer could share every
seller of its place, and leaves 0.7% of the trade's workers at providers with no buyer.

**Files:**
- Create: `rust/crates/babylon-persistence/src/national_economy/opening/dealing.rs`
- Modify: `opening/markets.rs` (`households`, `producers`, `service_provider`; an accessor for a location's
  providers, since `ProviderLocations.sites` is private to the file), the module list of `opening`
- Test: `dealing.rs` crate tests; `tests/national_twelve_trades.rs`

**Interfaces:**

```rust
/// One buyer of one product among buyers of its kind: where it is and how much it counts.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(super) struct Custom { pub buyer: AccountId, pub location: EconomicLocation, pub weight: u64 }
/// One seller of the product: where it is and its persons at work.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(super) struct Stall { pub site: SiteId, pub location: EconomicLocation, pub employed: u64 }
/// Deals whole buyers to sellers so that each seller's custom is in proportion to its persons at work. `kinds` are
/// dealt one after another; inside a kind the buyers in order of weight, largest first, then by account. A buyer
/// counts as its share of its own kind's whole weight, in parts of 2^32 rounded down. Each goes to the seller for
/// which `(shares dealt to it so far, over every kind, + this share) / employed` is smallest (compared by
/// cross-multiplying in u128), among equals a seller at the buyer's own location first, then the lower site id.
/// A stall with nobody at work is `Policy`. With no stall the map is empty: the caller decides (decision 4).
pub(super) fn deal(kinds: &[Vec<Custom>], stalls: &[Stall]) -> Result<BTreeMap<AccountId, SiteId>>;
/// The providers a domestic buyer at `location` may be dealt for the service `key`: those at its own location for a
/// service of the place (`policy.place_services`), those of its own state for any other. Where its own location
/// has none, a service of the place takes those of the nearest location of its state that has one, which is the
/// location `service_provider` reads today.
pub(super) fn reach(policy: &NationalGamePolicy, providers: &ProviderLocations, network: &mut Network<'_>,
    key: &str, location: EconomicLocation) -> Result<Vec<SiteId>>;
```

**Decisions:**
1. **Under schema 8 only** (the policy's twelve trades, `policy.trades`), for domestic buyers. Under schema 7, and
   for a foreign or dependency buyer under either, `service_provider` is today's and every byte of the shipped
   world stays.
2. **Kinds of buyers.** For one service: the household accounts are one kind, an account's weight its persons;
   the buying sites of one trade are one kind, a site's weight its `force`. The households are dealt first, then
   the trades in `EconomicFunction`'s order, and a provider's shares are carried from kind to kind. A whole buyer
   cannot be split, so a kind of one or two buyers cannot be spread: carried shares place it where the kinds before
   it left room, and the kinds of few buyers are then spread over the providers as a group, where each dealt afresh
   would pile onto the largest provider. What is in proportion to the providers' people is the sum of the shares,
   and each kind of many buyers. (Goods are dealt otherwise, Task 7d: there a buyer's need can be split, in units.)
   The dealing reads no price and no want, and of a recipe only whether a trade buys the service at all: it is the
   same whatever numbers the builder writes, which Task 8's census of who sells to which account depends on.
3. **Groups.** Buyers that `reach` gives one set of providers are dealt together. An account carved from another
   (`builder.aid.children`, `builder.support_claimant`: an aid donor, the support claimant) is not dealt: it takes
   its parent's provider (its parent is at its own location). A collective residence is not dealt a provider of a
   service it does not buy (a need on a household basis).
4. **Where nobody sells.** As today: a household account with no provider in reach is `MissingObservation`; a
   buying site with none is left without the input (`producers` skips it).
5. **The rows** are today's (`ServiceInputPolicy`, `HouseholdPurchasePolicy`, `ServiceConnection`), with the dealt
   provider in place of `service_provider`'s. No row is added: one provider a buyer and service, as before.
6. **The fixture's pins** move wherever a pin reads who sells a service to whom, or follows it (service
   connections, the opening's digests of the twelve trades). Each is filled once from the first failing run and
   listed in the hand-over with its old and new value. No pin of the shipped world moves.

- [ ] **Step 1: Write the failing tests.**
  - `whole_buyers_are_dealt_in_proportion` (crate test): stalls with 60, 30 and 10 at work and one kind of ten
    buyers of weight 10: 6, 3 and 1 buyers. Stalls 50 and 50 with buyers 70 and 30: one each. One stall: every
    buyer. Equal ratios go to the stall at the buyer's own location, then to the lower site id. A stall with
    nobody at work is `Err(Policy)`; no stall gives an empty map.
  - `a_later_kind_goes_where_room_is_left` (crate test): stalls 60 and 40; a first kind of one buyer; a second
    kind of one buyer: the first goes to the stall of 60, the second to the stall of 40.
  - `the_dealing_is_the_same_in_any_order` (crate test): the buyers inside each kind and the stalls shuffled give
    the same map.
  - `every_provider_with_workers_has_a_buyer` (fixture): for each service a household needs, the persons at work
    at domestic providers that no household and no site is dealt to are under 5% of the service's (print each
    share; today's are 27% to 64%, and the rule run outside the engine left under 1%). If one is not, stop and
    tell the lead with the figures: do not loosen it.
  - `a_service_of_the_place_is_bought_in_the_place` (fixture, `place_services` as Task 1 sets them): every domestic
    account whose location has a provider of housing, of household services or of public provision has its
    provider of that service there; an account whose location has none has it at another location of its state;
    some buyer's provider of utility is at another location of its state; no provider is in another state.
  - `carved_accounts_follow_their_parents` (fixture): Wayne's carved accounts have their parents' providers.
  - `the_shipped_services_are_unchanged`: `binary(shipped_world_bytes)`.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the crate tests, `binary(national_twelve_trades)`, `binary(shipped_world_bytes)`,
  `binary(national_household_units)`, the crate.
- [ ] **Step 5: Gate and commit** with the subject above. Hand over: for each service, the providers with a buyer
  over all providers, and the share of workers at providers with none, before and after.

What the player would see: every clinic, school, landlord and office in a place with customers from the first
period, where today one of each has them all.

### Task 7c: A household is dealt its shop (compiler)

Commit `feat(economy): deal every household a shop in proportion`.

**Why, counted.** A household buys every storable good at one shop: the largest distribution site of its own part
(`representative_retailers`), else its location's. 316 of the 992 domestic shops have customers. They hold 94.0% of
the trade's workers, so 1.7 million people work at shops nobody is given to buy at. This task's rule, run outside
the engine, gives 704 shops customers and leaves 0.5% of the workers at shops with none.

**Files:**
- Modify: `opening/markets.rs` (`households`)
- Test: `tests/national_twelve_trades.rs`

**Decisions:**
1. Under schema 8 the domestic household accounts of one location are dealt over the location's shops (every site
   with a merchant role and persons at work, of either part) by Task 7b's `deal`, as one kind: an account's weight
   its persons, a shop's its persons at work. A carved account takes its parent's shop. Foreign and dependency
   accounts as today. (The engine wants a shop's customer at the shop's own location, `recurring/validation.rs`.)
2. Everything a shop's customers set stays computed from them (`retail_requirements`, `retail_stock`, its offers
   and its own restocking): a shop with customers now stocks and restocks, so offers and restocking rows grow. They
   stay inside the engine's bounds; if not, `NationalOpeningError::Bounds`, and stop and tell the lead.
3. A location with no shop keeps today's fallback (`local_retailers`).
4. The fixture's pins move as in Task 7b, decision 6.

- [ ] **Step 1: Write the failing tests** (fixture):
  - `every_shop_with_workers_has_customers`: the persons at work at domestic shops with no household customer are
    under 2% of the trade's (print the share; today's is 6.0%).
  - `shops_customers_follow_their_workers`: over the nation's shops, the persons at work at shops whose customers'
    persons a worker are under half the nation's own ratio are under 5% of the trade's (print the shares under
    half and over twice).
  - `the_shipped_shops_are_unchanged`: `binary(shipped_world_bytes)`.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `binary(national_twelve_trades)`, `binary(shipped_world_bytes)`,
  `binary(national_household_units)`, the crate.
- [ ] **Step 5: Gate and commit** with the subject above. Hand over: shops with customers before and after; the
  counts of offers and of restocking rows before and after, against their bounds.

What the player would see: every shop of a place with customers.

### Task 7d: A business is dealt its makers of goods and machines (compiler)

Commit `feat(economy): deal every buyer of goods its makers by nearness and room`.

**Why, counted.** A business restocks a good at home from one maker: the site with the most people at work at the
nearest location that has a maker (`primary_supplier`). 185 of 368 food makers, 175 of 341 makers of resources and
303 of 339 makers of materials have a buyer, and a third of the workers in food and in extraction are at makers
with none. Buyers go to the nearest maker, not to where the product is made: with what home buyers ask scaled to
what the nation's makers can make, at most 56.8% of food, 63.3% of materials and 40.0% of resources can be sold. A
process takes its machines from one maker by the same rule (`equipment.rs` `policies`). And every buyer abroad takes
its share from the country at ONE maker (counted: the 35 buyers abroad of food at one maker in Kern County,
California; the 214 of materials at one in Dane County, Wisconsin; the 36 of resources at one in Hidalgo County,
Texas): `secondary_candidates` gives a buyer that is not in a county the counties in one order, with no rotation,
and `secondary_supplier` takes the first with a path, and its largest site. The
engine admits several suppliers a buyer and good (`recurring/validation.rs` `unique` on `(buyer_site_id,
supplier_site_id, good_id, unit_id)`), and one machine supplier a process (`equipment/validation.rs`).

**Files:**
- Modify: `opening/dealing.rs`, `opening/markets.rs` (`procure`, `primary_supplier`'s and `secondary_supplier`'s
  callers), `opening/equipment.rs` (`policies`), `opening/routes.rs` (a test of whether a route can be built)
- Test: `dealing.rs` crate tests; `tests/national_twelve_trades.rs`

**Interfaces:**

```rust
/// A buyer's share at one maker: `part` of `whole`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(super) struct Share { pub maker: SiteId, pub part: u128, pub whole: u128 }
/// Deals buyers' weights over makers by nearness and room. A maker's room is its persons at work over all makers'
/// times the buyers' whole weight, kept exact as `employed x whole weight` against `weight x all makers' employed`.
/// Buyers in order of weight, largest first, then by site id; each takes room from the makers of the nearest
/// location that has room left (`nearest` gives it; inside a location the makers by site id), then the next
/// nearest, up to `most` makers; the last takes whatever is left.
pub(super) fn deal_by_room(custom: &[Custom], stalls: &[Stall], most: usize,
    nearest: &mut dyn FnMut(EconomicLocation, &BTreeSet<EconomicLocation>) -> Result<Option<EconomicLocation>>)
    -> Result<BTreeMap<AccountId, Vec<Share>>>;
/// A cap dealt over shares by largest remainder (equal remainders to the lower site id), so that the parts sum to
/// `cap`; a part that comes to 0 gives no row.
pub(super) fn caps(cap: u64, shares: &[Share]) -> Result<Vec<(SiteId, u64)>>;
/// Whether `routes::add_stage` would build a route from `from` to `to` for this cargo: a path exists, and its links
/// have a travel time above 0 and a pool. The same test `add_stage` makes; a location is its own route.
pub(super) fn routable(builder: &Builder<'_>, network: &mut Network<'_>, from: EconomicLocation,
    to: EconomicLocation, cargo: CargoClass) -> Result<bool>;
```

**Decisions:**
1. **Under schema 8 only** (`policy.trades`). Under schema 7 `procure` and `equipment::policies` are today's.
2. **In units, one dealing a good.** A buyer's weight is what it may take from the country's makers in a period, in
   the good's units: for a domestic site its home cap (`required` less the cap abroad, Task 5), summed over
   everything it buys the good for (a recipe input, an installation input of its machines through
   `equipment::policies`, a shop's customers' needs); for a buyer abroad its cap from the country (Task 5). The
   home buyers of a good are dealt together, and the buyers abroad together, each against the makers' people
   afresh: each maker's whole custom is then in proportion to its people. This dealing follows the scenario's
   numbers, and it may: nothing of it is in Task 8's census.
3. **Goods:** `deal_by_room` with `most = 3` for home buyers and `most = 16` for buyers abroad (a buyer abroad is a
   whole region's trade, as large as many makers). The buyer's cap is dealt over its makers by `caps`; each row
   keeps today's `target_stock` and `cash_floor`. A maker is never dealt itself. A domestic buyer's row abroad
   is today's.
4. **Machines:** one maker a process (the engine's rule): the home buyers of machines are dealt with `most = 1`, a
   process's weight its replacement machines (Task 6). Task 5's rule on which processes buy abroad stays.
5. **Nearness** is the network's own (`Network::nearest`: hops to the buyer's location, by the good's cargo
   class). A maker location is offered to a buyer only where `routable` holds from it to the buyer, so that no
   dealt pair fails `add_stage` (`NationalOpeningError::Route`).
6. **When a buyer wants less than its caps together,** the engine serves its rows in its own order and the last go
   short (`recurring/firms.rs` `position`: each row sees what the rows before it ordered). That is today's rule
   for a home and a foreign supplier; this task leaves it.
7. **Bounds.** Restocking rows and routes grow (up to three home rows a buyer and good, sixteen for a buyer abroad,
   and a route for each new pair of locations and cargo class). Print and pin the counts of restocking rows,
   supplier routes, route stages and stage memberships, and print the mean number of pools a stage (memberships
   are the count nearest their bound, 262,144). Past a bound of the engine: `NationalOpeningError::Bounds`; then
   build with `most = 2` at home and say so.
8. **Room on the routes.** Goods now travel from where they are made. The opening's report (Task 15) lists every
   shared freight pool whose opening use passes its room (O15: "the record of health lists every route that is
   full"); nothing is asserted here.
9. The fixture's pins move as in Task 7b, decision 6.

- [ ] **Step 1: Write the failing tests.**
  - `buyers_take_the_nearest_room` (crate test): makers A (40 at work, near) and B (60, far), buyers of weight 50
    and 50: the first takes 40 of A and 10 of B, the second 50 of B. With `most = 1` each takes one maker, the
    first A. A buyer with no maker location offered gets no share.
  - `caps_sum_to_the_cap` (crate test): 10 over parts 1, 1, 1 of 3 gives 4, 3, 3, the 4 at the lowest site id; a
    part that comes to 0 gives no row.
  - `every_maker_with_workers_has_a_buyer` (fixture): for food, materials, resources, consumer goods and machines,
    the persons at work at domestic makers no buyer is dealt to are under 5% of the trade's (print each share). A
    product nothing in the fixture buys is printed and left out.
  - `makers_are_asked_in_proportion` (fixture): for food and materials, the caps asked of a maker from home and
    from abroad over its persons at work lie within a factor of two of the nation's own ratio for makers holding
    nine tenths of the trade's workers (print the shares under half and over twice).
  - `buyers_abroad_are_dealt_over_the_country` (fixture): the buyers abroad of food are dealt more than one home
    maker between them, and no home maker is asked from abroad for more than twice its share by people.
  - `an_installation_need_follows_its_site_s_makers` (fixture): a process whose machines need materials restocks
    them from the makers its site is dealt for materials.
  - `the_shipped_restocking_is_unchanged`: `binary(shipped_world_bytes)`.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the crate tests, `binary(national_twelve_trades)`, `binary(shipped_world_bytes)`,
  `binary(national_household_units)`, the crate.
- [ ] **Step 5: Record** the bench's baseline of the fixture once, in the background (`record_twelve_trades_sets`
  with `TWELVE_TRADES_SET=baseline`), and hand over the domestic persons at work at the close of periods 1, 2, 5,
  13 and 34 beside the committed record's and beside Task 7a's, the layoffs of period 2 by trade, and whether any
  period was refused (a refusal of the engine is a result: its period, stage and words). The fixture's numbers are
  not the rebuilt opening's: the figures show what the dealing alone moves, and are no verdict. Then put the
  committed records back (`git checkout -- reports/country-opening-2026-11/`), as in Task 7a.
- [ ] **Step 6: Gate and commit** with the subject above. No record is committed. Hand over the pinned counts and,
  for each good, the makers with a buyer and the share of workers at makers with none, before and after.

What the player would see: farms, mills and machine works across the country with buyers at home and abroad, and
goods that travel from where they are made.

### Task 8: The census of the twelve-trade opening

Commit `feat(reference): the census of the twelve-trade opening`.

**Why.** The builder needs the game's own workforce (O4: "observed hours over what the game's buyers take"), and it is
a Python tool while the workforce is made by the Rust compiler. The spike read 161.3 million domestic workers from a
health record of the ten-trade shipped world and split them by QCEW jobs (the spike, section 2, "Workers"). Under
twelve trades the compiler gives them directly. So a Rust recorder writes them once, as a committed, pinned JSON table
that the builder reads.

**Files:**
- Create: `rust/crates/babylon-persistence/tests/national_opening_census.rs`, `tests/support/opening_census.rs`;
  `src/babylon/data/reference/economy/national_opening_census_v13.json`
- Modify: `rust/crates/babylon-persistence/src/economic_catalog/capture.rs`: `national_household_budget` (L261 in
  the copy) becomes `pub`, so the recorder in `tests/` can read each account's `HouseholdBudgetKey`
  (`NationalOpening.household_keys` is `pub(crate)`, `opening/build.rs:505`, and
  `national_economy::household_principal` misses the detailed Wayne accounts); `data-artifacts.yaml` (a register
  entry after `national_trade_accounts_2024`);
  `tests/unit/reference/test_data_artifacts.py` (`checked` up by one from what it is, 41 in the copy, with a clause in
  its comment)

**Interfaces:**

```rust
/// What the opening's people and workplaces are, before any recipe or price matters.
// The capture, not the opening alone: an account's and a site's part are not in `EconomicOpening`. They are read
// from the capture's generation witness (`national_generation()`: `household_incidence`, `counties[].destination`,
// `catchments[].key.hub`; carved accounts through `national_aid_capture()` and `national_support_claimant()`), as
// the bench's `tests/support/country_bands.rs` reads an account's key. If a site's part cannot be read so, the
// compiler's own map (`Builder.financial_domains`) is kept on `NationalOpening` behind a `pub` accessor, and the
// hand-over says so.
pub fn opening_census(catalog: &CapturedEconomicCatalog, policy: &NationalGamePolicy,
    pay: &NationalTradePayReference) -> Result<Value, CensusError>;
pub fn census_bytes(census: &Value) -> Vec<u8>;   // serde_json pretty with 2 spaces, sorted keys, trailing newline
```

**Decisions:**
1. **What it holds**, every figure a sum of the compiled opening's own rows, persons and micros as integers:
   - `trades`: for each of the twelve trades, domestic: `employee_persons` (employee members at work, `employed`: the
     same persons the payroll sums), `working_owner_persons`, `unpaid_family_persons`, `payroll_micros_per_period` (sum
     of each employee member's wage x employed x `work_hours_per_person`), `force` (the trade's persons in work or
     seeking it at its sites), `sites`; and `national_wage_micros` (`pay.national_wage(f)`), written for reading only:
     the builder and the compiler both use `payroll_micros_per_period / (employee_persons x 160)` (Task 14b).
   - `households`: for each `HouseholdBudgetKey`, domestic: `accounts`, `households`, `persons`, `employed`, `reserve`,
     `wage_income_micros_per_period` (its members' wages x employed x hours).
   - `places`: one row for each domestic part (financial domain), keyed by the part's label and naming its `hub`
     (316 rows over 187 hubs are expected): persons, households and reserve by key; the wage
     income of its residents by key (`wage_income_micros_per_period`: the wage tax is paid where the household lives,
     not where it works); by trade, employee persons and payroll of its workplaces; `owner_households` (the households
     of `owner_exposure` keys).
   - `abroad`: for each foreign region and the dependency: `persons`, `households`, `labor_force`, `employed` (its
     profile's counts), `wage_micros` by trade (`floor(national_wage(f) x wage_fraction_bps / 10_000)`).
   - `assignment`: for each storable good and foreign region, the `force` of domestic buying sites whose foreign second
     supplier for that good is in that region, by the buyer's trade (each good's foreign suppliers are the regions
     that make it, `ProviderLocations::new`; buyers are weighted by force because `producers` sizes `required` from
     force, `markets.rs` `maximum_batches = force x hours / L`); and for each good and region, the persons of the
     accounts served by domestic retailers whose foreign second supplier of that good is in it. This is the compiler's
     rotation (`secondary_candidates`), which depends on site ids and routes, not on numbers.
   - `sources`: the sha256 of the cohort, pay, county and household tables the catalog captured.
   - Five figures Part II needs, none of which follows the numbers: in `trades`, `public_employee_persons` and
     `public_payroll_micros_per_period` (the employee members of sites whose earnings go to a public body:
     `financial.rs` `ownership`), and `machines` (the sum over the trade's domestic sites with a process of
     `ceil(force / workers_per_machine)` at the fixture's figures), with a top-level `workers_per_machine` table of
     the figures used; in `places`, by key `employed`, by trade `public_employee_persons` and
     `public_payroll_micros_per_period`, and `sellers`: for each key and each product a household account buys, the
     employee wage (micros an hour) of the site that sells it to that part's accounts of that key at the opening,
     the provider of a service and the shop of a storable good, as Tasks 7b and 7c deal them (a carved account takes
     its parent's, so a part's accounts of one key share their sellers). Where they do not, the recorder refuses
     (`CensusError`): the lead then widens the table.
2. **Not in it:** anything that follows recipes, prices, taxes or wants. Task 14a proves the census is the same from the
   rebuilt scenario (Review Focus 1).
3. The recorder is an ignored test, `record_national_opening_census`, that compiles the fixture
   (`capture_national_campaign(national_catalog_input_for(fixture)?, campaign)`) and writes the file. The checker,
   `the_committed_census_is_the_opening_s`, not ignored, computes the census again and compares bytes.
4. The register entry: `name: national_opening_census_v13`, `format: json`, `source_table: null`, `generator:
   rust/crates/babylon-persistence/tests/national_opening_census.rs`, `mode: register`, `rows` the number of places,
   `sha256`, `home`, `material_relation` "the persons, jobs and wages of the twelve-trade opening, read by the stage 5
   builder". The file must stay under 1,048,576 bytes; the recorder asserts it.

- [ ] **Step 1: Write** the checker and the recorder; run the checker and see it fail (no file).
- [ ] **Step 2: Run the recorder** in the background; then the checker passes. Hand over: the domestic persons at
  work by trade (the spike's 161.3 million in all is the size to expect, not a pin), the persons by key, the machines
  by trade, the count of parts and of hubs, the lowest and highest seller's wage of each product over the parts, and
  the size.
- [ ] **Step 3: Register** it and run `tools/make_data_artifacts.py --check`.
- [ ] **Step 4: Gate** (Rust legs with `binary(national_opening_census)`, `binary(shipped_world_bytes)` and
  `binary(national_household_units)`, since `capture.rs` changes; the Python test of the register), `mise run
  check:hygiene`, **commit** with the subject above.

What the player would see: nothing; it is an input of the builder.

### Task 9: The builder, part 1: its settings, the census and the accounts re-cut

Commit `feat(reference): re-cut the national accounts to the game's buyers`.

**Why.** Every later part reads three things this task makes: the builder's settings (the Director's choices as named
values, and the design's figures), the census of Task 8 as typed Python, and the accounts re-cut to the buyers
the game has under rules R1 to R3 and O4 (model-spec sections 1 to 3). It also fixes the arithmetic every part uses.

**Files:**
- Create: `tools/national_opening_recut.py`; `tests/unit/tools/test_national_opening_recut.py`

**Interfaces:**

```python
TRADES: Final[tuple[str, ...]]      # the twelve, in the accounts' order (stage 1's TRADES)
PRODUCT: Final[Mapping[str, str]]   # trade -> product: food->food, extraction->resources,
    # energy_utilities->utility, manufacturing->materials, consumer_goods->consumer_goods,
    # capital_goods->equipment, construction_housing->housing, household_services->household_services,
    # leisure_hospitality->leisure, business_services->business_services, public_provisioning->public_provision;
    # distribution_transport has none (it is the shop, O9)
HouseholdKey = Literal["earning_lower_paid_half", "earning_better_paid_forty", "earning_owner",
                       "no_earner_nonowner", "no_earner_owner", "collective_residence"]
BenefitRule = Literal["dearest_place", "each_place_own", "one_average"]
PlaceBody = Literal["one_share", "even_where_own_taxes_reach", "every_place_even"]

@dataclass(frozen=True)
class Economy:
    """Which trades exist and what each is. TWELVE is the game's; tests build small ones."""
    trades: tuple[str, ...]
    product: Mapping[str, str]                 # trade -> product key; the shop trade is absent
    storable: frozenset[str]                   # product keys of storable goods
    shop_trade: str | None                     # distribution_transport
    public_trade: str | None                   # public_provisioning
    capital_trade: str                         # capital_goods
    extraction_trade: str | None               # extraction: exports what businesses leave
    shop_goods: frozenset[str]                 # storable products households buy: food, materials, consumer_goods
    person_needs: tuple[str, ...]              # food, utility, household_services
    household_needs: tuple[str, ...]           # materials, housing
TWELVE: Final[Economy]

@dataclass(frozen=True)
class Settings:
    """The Director's choices that change the builder's numbers (For the Director, items 1 to 4 and 6) and the
    design's figures. Defaults: the approved text. A ruling changes a value here, never the code."""
    # 1. Services' stages and the order of paying (V6, V7).
    service_stage: Mapping[str, int] = <utility 1; housing, household_services, leisure, business_services,
                                        public_provision 2>
    paying_order: tuple[str, ...] = ("food", "materials", "consumer_goods", "utility", "housing",
                                     "household_services", "leisure", "business_services", "resources")
    # 2. The products that cross a border (V8).
    crossing: frozenset[str] = frozenset({"food", "resources", "materials", "consumer_goods", "equipment"})
    # 3. The benefit's rule (V3, V4).
    benefit_rule: BenefitRule = "dearest_place"
    # 4. Each place's public body (V1, V1 with V2's road (b)).
    place_body: PlaceBody = "one_share"
    # 5. Who gets what the shop saves on imports (V10): the shop, as it posts its prices today, or households.
    shop_import_saving: Literal["shop", "households"] = "shop"
    # The design's figures, never solved.
    tier_sizes: tuple[Fraction, Fraction, Fraction] = (Fraction(2, 5), Fraction(3, 5), Fraction(3, 2))
    wear_cover: Fraction = Fraction(5, 4)
    accounts_margin_floor: Fraction = Fraction(1, 20)
    periods_per_year: int = 13
    work_hours_per_person: int = 160
    workers_per_machine: Mapping[str, int] = <4 for food, extraction, energy_utilities, manufacturing,
        consumer_goods, capital_goods, construction_housing; 40 for household_services, leisure_hospitality,
        business_services, public_provisioning>
    machine_life_periods: int = 100
    days_per_period: int = 28
    public_fee_micros: int = 1_000_000
    laid_off_wage_share_bps: int = 5_000
    laid_off_half_periods: int = 13
    fund_reserve_periods: int = 2
    margin_halvings: int = 40

@dataclass(frozen=True)
class TradeCount:
    employee_persons: int; working_owner_persons: int; unpaid_family_persons: int
    payroll_micros: int; force: int; sites: int; machines: int
    public_employee_persons: int; public_payroll_micros: int
@dataclass(frozen=True)
class KeyCount:
    accounts: int; households: int; persons: int; employed: int; reserve: int; wage_income_micros: int
@dataclass(frozen=True)
class PlaceTrade:
    employee_persons: int; payroll_micros: int; public_employee_persons: int; public_payroll_micros: int
@dataclass(frozen=True)
class Place:                                   # ONE PART of a pooled place: the game's unit of accounts (Task 8)
    label: str                                 # `<hub geoid>`, or `<hub geoid>/<position>` for a pooled part
    hub: str                                   # the hub county's geoid: where its accounts buy and its sites sell
    state: str                                 # the hub's first two digits: a service is bought inside it
    keys: Mapping[HouseholdKey, KeyCount]      # `accounts` is 1 or more; Wayne's detailed accounts are summed
    trades: Mapping[str, PlaceTrade]
    owner_households: int
    sellers: Mapping[HouseholdKey, Mapping[str, int]]   # product -> the employee wage, micros an hour, of the site
                                               # that sells it to the place's accounts of that key (O5)
@dataclass(frozen=True)
class Region:
    key: str; persons: int; households: int; labor_force: int; employed: int; wage_micros: Mapping[str, int]
@dataclass(frozen=True)
class Census:
    trades: Mapping[str, TradeCount]
    households: Mapping[HouseholdKey, KeyCount]
    places: tuple[Place, ...]                  # one for each part, in label order
    abroad: Mapping[str, Region]               # the foreign regions and the dependency, by policy key
    firm_assignment: Mapping[tuple[str, str, str], int]   # (good, region, buyer trade) -> force
    retail_assignment: Mapping[tuple[str, str], int]       # (good, region) -> persons served
    workers_per_machine: Mapping[str, int]     # the figures the census's `machines` were counted with
    sha256: str
def read_census(path: Path) -> Census: ...

Accounts = Mapping[str, Mapping[str, Mapping[str, int]]]     # block -> row -> column -> value (USD thousands)
def read_accounts(path: Path) -> Accounts: ...
def allowed(settings: Settings, economy: Economy, product_in: str, trade_out: str) -> bool: ...

@dataclass(frozen=True)
class Recut:
    inputs: Mapping[str, Mapping[str, Fraction]]   # [i][j]: product of trade i used by trade j, USD thousands a year
    households: Mapping[str, Fraction]             # H0 by trade
    exports: Mapping[str, Fraction]                # X0, crossing trades only
    equipment: Fraction                            # E0: every use of capital goods but its own
    import_share: Mapping[str, Fraction]           # IMP, crossing trades only, else 0
    domestic_output: Mapping[str, Fraction]        # dom
    accounts_payroll: Mapping[str, Fraction]       # jobs block payroll / 1000
    accounts_jobs: Mapping[str, int]
    accounts_margin: Mapping[str, Fraction]        # am, floored at accounts_margin_floor; 0 for shop and public
    moved: Mapping[tuple[str, str], Fraction]      # (reason, trade) -> USD thousands a year spread by O4
    dropped: Mapping[tuple[str, str], Fraction]    # (reason, row) -> USD thousands a year left out
def recut(accounts: Accounts, settings: Settings, economy: Economy = TWELVE) -> Recut: ...

def half_up(value: Fraction) -> int: ...                       # floor(value + 1/2)
def to_grid(value: Fraction, denominator: int) -> Fraction: ... # half_up(value x d) / d
def up_to_grid(value: Fraction, denominator: int) -> Fraction: ...  # ceil(value x d) / d
```

**Decisions:**
1. **The arithmetic of Part II.** Every figure is an `int` or a `Fraction`; a `float` anywhere is a defect, and no
   module imports `math` but for `math.floor`/`math.ceil` applied to a `Fraction`. Money inside the solve is dollars
   as a `Fraction`; it becomes whole micros only where a later task says so. Every rounding names its rule: `half_up`
   (to the nearest, a half up), down (`floor`), up (`ceil`), or largest remainder (`apportion` of
   `make_national_trade_pay.py`, reused). An iteration is always cut by an exact stopping test on values held on a
   named grid (`to_grid`, `up_to_grid`), so the same inputs give the same bytes. Every refusal is
   `ReferenceBuildError` with a fixed code before the first colon.
2. **The five settings** (model-spec 3 and 10; For the Director). Each is one field of `Settings`; its default is
   the approved text. What a non-default value needs outside Part II is a variant, not this plan's:
   - `service_stage` and `paying_order`: stages 1 and 2 only is V6 (no engine change; Task 13 writes the kinds and
     the order); a stage 3 is V7 (an engine plan).
   - `crossing` with any service: V8 (compiler tasks before Task 5).
   - `benefit_rule`: `each_place_own` is V3 (road a); `one_average` is V4 (Task 15's assertion only).
   - `place_body`: `even_where_own_taxes_reach` is V1; `every_place_even` is V1 with V2's road (b).
   - `shop_import_saving`: `households` is V10 (Task 14b then posts a shop's good at what the shop pays for it plus
     its charge).
   Part II computes every value's figures; Task 13 writes only what the compiler admits (Task 13, decision 4).
   `Settings` is checked once (`check_settings`): every service product has a stage of at least 1; the paying order
   holds every priced product households buy and resources, once each, storable needs before any service, and every
   first-stage service before every later one (call 19; `admission.rs` `paying_order`); `crossing` holds only priced
   products; else `setting: <field>`.
3. **The census reader.** `read_census` reads Task 8's JSON exactly, with the key names Task 8 writes (trade keys as
   the accounts table spells them; household keys as `HouseholdBudgetKey`'s serde labels after stage 2, mapped to
   `HouseholdKey`); an unknown key, a missing key or a non-integer value is `census_shape: <json path>`. It checks:
   the households' `wage_income_micros` summed over keys equals the trades' `payroll_micros` summed
   (`census_wages`); each trade's place rows sum to its national row, and each key's place rows to its national row
   (`census_places: <trade or key>`); `workers_per_machine` equals `Settings.workers_per_machine`
   (`census_machines: <trade>`). The census must carry five figures Task 8 does not yet list (edits in the notes):
   `machines` and `public_employee_persons`, `public_payroll_micros` by trade, nationally and by place; `employed`
   by key in each place; and `sellers`, for each place and key the wage of the site that sells each product to its
   accounts (a provider for a service, a retailer for a shop good).
4. **The re-cut** (model-spec 3, as `model.py` ran). For each product row `i` but the shop's and public
   provision's: `phi = (commodity_output + imports) / total_supply`; every cell below is the use cell times `phi`. A
   row with `total_supply` 0 is skipped. Then:
   1. each trade column `j`: own use (`j = i`) dropped; else capital goods to `E0`; else the shop column to the
      row's spread (`R3`); else not `allowed(i, j)` to the spread (`R1`); else `inputs[i][j]`;
   2. the owner-occupied housing column dropped (call 6);
   3. the four government columns: capital goods to `E0`; else `inputs[i][public]`, or the spread (`R1`) when not
      `allowed(i, public)`;
   4. households: capital goods to `E0`, else `H0[i]`; residential investment: `H0[i]`, but capital goods to `E0`
      (`model.py` put it in `H0[capital]`, which reaches the same equipment total; `E0` says so);
   5. investment in structures, equipment and IP: capital goods to `E0`; else dealt over every trade `j` but `i`
      and public provision by `max(gross_operating_surplus[j], 0)`, each part to `inputs[i][j]` or to the spread
      (`R3` for the shop, `R1` when not allowed). If those surpluses sum to 0, `accounts_empty: surplus`;
   6. exports: a crossing product's to `X0[i]`, else the spread (`R2`);
   7. inventories: the spread (`O4_inventories`);
   8. `k = 1 + spread / (sum_j inputs[i][j] + H0[i] + X0[i] + E0[i])`; every kept cell of the row times `k`.
   The rows `distribution_transport`, `owner_occupied_housing`, `scrap_used` and `noncomparable` are dropped and
   listed in `dropped`. Public provision's row feeds nothing.
   `allowed(i, j)` is false when `j` is the shop trade, and false when both products have a stage and the input's
   stage is at least the output's (`admission.rs` `validate_recipe`); storable goods have no stage.
5. **Shares and margins.** `IMP[i] = imports / (commodity_output + imports)` for a crossing product, else 0.
   `dom[i] = (sum_j inputs[i][j] + H0[i] + X0[i] + E0[i]) x (1 - IMP[i])`; `dom[public] = sum_i inputs[i][public] +
   payroll_acc[public]`; `dom[shop] = payroll_acc[shop]`; `payroll_acc[j] = annual_payroll_usd / 1000`. For each
   trade with a recipe but public provision, `cost[j] = sum_i inputs[i][j] + payroll_acc[j]` and `am[j] = max((dom[j]
   - cost[j]) / cost[j], accounts_margin_floor)` (`model.py` floors at 5%, `Model.acc_mu`); `cost[j]` 0 is
   `accounts_empty: <trade>`. Nothing is rounded in this module; every figure is a `Fraction` of the table's
   integers.

- [ ] **Step 1: Write the failing tests** (`test_national_opening_recut.py`):
  - `the_recut_of_five_trades`: a fixture economy of food, capital goods, household services, the shop and public
    provision (`Economy` built in the test; food and capital goods cross; `phi = 1` everywhere: `total_supply =
    commodity_output + imports`). Use cells: food row: food 10, household services 20, shop 5, households 100,
    `state_local_consumption` 15, exports 10, inventories 5; household services row: food 8, capital goods 4,
    household services 6, shop 2, households 50, `state_local_consumption` 30, `investment_structures` 12; capital
    goods row: food 3, household services 2, shop 1, `investment_equipment` 40, households 4,
    `state_local_consumption` 5, exports 6. Supply: food 120 and imports 20, capital goods 90 and 10. Surplus: food 30,
    capital goods 10, household services 20, shop 5. Payroll (USD): food 50,000, capital goods 20,000, household
    services 40,000, shop 10,000, public 30,000. Expected, exactly: household services' spread `k = 159/109`,
    `inputs[hs][food] = 2544/109`, `inputs[hs][capital] = 1060/109`, `H0[hs] = 7950/109`; food's `k = 31/29`,
    `inputs[food][hs] = 620/29`, `inputs[food][public] = 465/29`, `H0[food] = 3100/29`, `X0[food] = 310/29`;
    `E0 = 55`, `X0[capital] = 6`; `IMP[food] = 1/7`, `IMP[capital] = 1/10`; `dom[food] = 930/7`, `dom[capital] =
    549/10`, `dom[hs] = 106`, `dom[public] = 1335/29`, `dom[shop] = 10`; `am[food] = 22706/27979`, `am[capital] =
    3049/3600`, `am[hs] = 647/890`; `moved[("R1", hs)] = 30`, `moved[("R3", hs)] = 10/3`, `moved[("R3", food)] = 5`,
    `moved[("O4_inventories", food)] = 5`.
  - `the_spread_keeps_each_row_whole`: in that fixture, each row's kept cells after the spread sum to its cells
    before the re-cut less own use, the owner column and the dropped rows (household services 106, food 155,
    capital goods 61).
  - `a_negative_surplus_takes_no_investment`: the fixture with food's surplus at -30: household services'
    structures go 8 to capital goods and 4 to the shop's spread, none to food.
  - `a_stage_rule_follows_the_setting`: with `service_stage` household services 1 and public provision 2, the
    government's 30 of household services is `inputs[hs][public]`, not spread.
  - `the_import_shares_of_the_committed_table`: `recut(read_accounts(<committed>), Settings())`: `import_share`
    floored to basis points is food 1,102, extraction 2,294, manufacturing 2,221, consumer goods 4,277, capital
    goods 4,104, and 0 for every other trade (energy's 480 no longer crosses under R2).
  - `the_committed_recut_keeps_the_rules`: no `inputs[i][i]`; no `owner_occupied_housing` key; no input `i` to `j`
    with `allowed` false; `inputs["capital_goods"]` empty; `moved` R1 summed over products, as a period's dollars
    (`x 1000 / 13`), is between 400 and 700 thousand million (the prototype's 549.6 is the size, not a pin).
  - `bad_settings_are_refused`: a paying order with housing before utility while utility is stage 1 and housing
    stage 2 (`setting: paying_order`); `crossing` with an unpriced product (`setting: crossing`).
  - `the_census_reader_refuses_a_bad_census` (fixture JSON in `tmp_path`): an unknown key, a missing trade, a float
    value, wage incomes that do not sum to the payroll, a place row over its national row, a `workers_per_machine`
    of 5: each its code.
- [ ] **Step 2: Run them and see them fail** (`mise run test:q -- tests/unit/tools/test_national_opening_recut.py`).
- [ ] **Step 3: Implement** decisions 1 to 5.
- [ ] **Step 4: Run them and the gate.**
- [ ] **Step 5: Commit** with the subject above. Hand over the committed table's R1, R2, R3 and inventory spreads
  by product, a period's dollars, beside the prototype's (549.6, 71.2, 221.6, 2.1) for size only.

What the player would see: nothing; the numbers come in Task 13.

### Task 10: The builder, part 2: quantities, prices, margins, trade and taxes

Commit `feat(reference): solve the opening's prices, margins and taxes`.

**Why.** The national opening at one margin factor, and the factor itself (model-spec 4 to 7 and 9). The prototype
solved it in floats by value iteration. Here every step is exact or held on a grid, so two builds give the same
bytes and a trade at its wear floor is decided by an exact comparison.

**Files:**
- Create: `tools/national_opening_solve.py`; `tests/unit/tools/test_national_opening_solve.py`

**Interfaces:**

```python
GRID: Final = 2**64          # coefficients a, h, xs, IMP, sigma: to_grid(., GRID)
FLOOR_GRID: Final = 2**48    # floored margins: up_to_grid(., FLOOR_GRID)
MICROS: Final = 10**6        # equipment money e: to_grid(., MICROS) dollars

@dataclass(frozen=True)
class Quantities:
    output: Mapping[str, Fraction]            # x[j], accounts dollars a period, whole (half_up)
    coefficients: Mapping[str, Mapping[str, Fraction]]   # a[i][j]
    hours_per_dollar: Mapping[str, Fraction]  # h[j]
    hours: Mapping[str, int]                  # census persons at work x 160
    wage: Mapping[str, Fraction]              # floor(payroll / (employee persons x 160)) micros, as dollars
    unpaid_labor: Mapping[str, Fraction]      # U[j] = wage x hours - payroll, dollars a period
    export_share: Mapping[str, Fraction]      # xs[i]
    imports: Mapping[str, Fraction]           # m[i], whole
    final: Mapping[str, Fraction]             # fin[i] = x + m - sum_j a[i][j] x[j]
    machines: Mapping[str, int]               # census, every trade with a recipe, public provision included
    import_sources: Mapping[str, Mapping[str, Fraction]]  # sigma[i][region], each good's sum 1
    import_buyers: Mapping[str, Mapping[str, Fraction]]   # each good's imports by buying trade (shop = households)
    wages_abroad: Mapping[str, Mapping[str, Fraction]]    # region -> trade -> census wage, dollars an hour
def quantities(recut: Recut, census: Census, settings: Settings, economy: Economy = TWELVE) -> Quantities: ...

@dataclass(frozen=True)
class Prices:
    prices: Mapping[str, Fraction]            # p[j], dollars a period per accounts dollar, private trades
    margins: Mapping[str, Fraction]           # mu[j] in force, floored ones included
    floored: frozenset[str]
    equipment: Fraction                       # e, dollars a period, on the MICROS grid
    rounds: int
def solve_prices(q: Quantities, lam: Fraction, accounts_margin: Mapping[str, Fraction], settings: Settings,
                 economy: Economy = TWELVE) -> Prices: ...

@dataclass(frozen=True)
class Opening:
    lam: Fraction; prices: Prices; quantities: Quantities
    export_factor: Fraction                   # kx
    exports: Mapping[str, Fraction]           # X[i], accounts dollars a period
    import_prices: Mapping[str, Fraction]     # p~[i]: what one accounts dollar of imports costs, region mix
    import_saving: Mapping[str, Fraction]     # S[j] by buying trade, dollars a period
    wear: Mapping[str, Fraction]              # by trade with machines
    operating_income: Mapping[str, Fraction]  # OI[j], private trades and the shop
    public_owned_income: Fraction             # PO
    grant: Fraction; support: Fraction; benefits: Fraction
    benefit_per_person: Fraction; residence_per_person: Fraction
    tax_rate: Fraction; fund_share: Fraction; payout: Fraction
    household_purchases: Mapping[str, Fraction]   # H[i], dollars a period at producer prices
    shop_charge: Fraction                     # H[shop] = shop wage x shop hours
    markup: Fraction                          # rho
    spending: Fraction                        # C = sum H + H[shop]; the fee is outside it
    tier_unit: Fraction                       # cbar = C / domestic persons
    tier_one: Mapping[str, Fraction]          # value at posted prices: a person for person needs, a household for
                                              # household needs
    bands: Mapping[HouseholdKey, Fraction]    # the national accounts' money a period
    kept: Fraction
    balances: Mapping[str, tuple[Fraction, Fraction]]   # O6's four: (flow, residual)
def opening(recut: Recut, census: Census, q: Quantities, lam: Fraction, settings: Settings) -> Opening: ...
def largest_with_nothing_kept(kept_at: Callable[[Fraction], Fraction], halvings: int) -> Fraction: ...
def solve(recut: Recut, census: Census, settings: Settings) -> Opening: ...
```

**Decisions:**
1. **Workers and wages** (model-spec 2 and 4, with the game's people). A trade's hours a period are its census
   persons at work (employees, working owners and unpaid family) times 160. Its wage is the compiler's:
   `floor(payroll_micros / (employee_persons x 160))` micros (Task 14b, decision 2). Labor in a price is the wage
   times all hours; the part owners and family work unpaid, `U[j] = wage x hours - payroll`, is the site's
   operating income (decision 8). The shop's charge is `wage[shop] x hours[shop]` (R3).
2. **Quantities** (model-spec 4). `kappa[j] = persons at work[j] / accounts_jobs[j]`; `x[j] = half_up(dom[j] x 1000
   / 13 x kappa[j])` accounts dollars a period; `a[i][j] = inputs[i][j] / dom[j]`; `h[j] = hours[j] / x[j]`; `xs[i]
   = X0[i] / dom[i]`; `m[i] = half_up(x[i] x IMP[i] / (1 - IMP[i]))`; `fin[i] = x[i] + m[i] - sum_j a[i][j] x[j]`.
   `a`, `h`, `xs` and `IMP` are put on `GRID` (`to_grid`) when made; so are `sigma` and the import buyers' shares.
   Machines are the census's (`Census.trades[j].machines`, public provision's included: call 8 counts its wear and
   the equipment it buys); `NM` is their sum. The shop has none (R3).
3. **Who sells the imports** (O11; Task 8's assignment). A good's import weight of a region is `sum_j force(good,
   region, j) x 160 x a[good][j] / h[j]` over buying trades plus `persons_served(good, region) x H0[good] /
   domestic persons`; `sigma[good][region]` is that over its sum. The same weights by buyer give `import_buyers`
   (the shop's part stands for households). A good with no weight is `import_weights: <good>`.
4. **One price solve, given the state** (model-spec 6, R5). The state is `theta = (e, F, phi)`: equipment money `e`,
   the floored set `F`, and a margin `phi[j]` for each `j` in `F`. Given `theta`, `mu[j] = lam x am[j]` off `F` and
   `phi[j]` on it, and wear `wear[j] = e x M[j] / NM`. The prices of the ten private trades (all but the shop and
   public provision, which no recipe buys) solve exactly `p[j] = (1 + mu[j]) (wage[j] h[j] + sum_i a[i][j] p[i])`: a
   10 by 10 linear system solved by Gaussian elimination in `Fraction`s, rows and columns in trade order, the first
   non-zero pivot of each column; no pivot is `prices_singular`. Nothing in it is iterated.
5. **The state's iteration.** Start `e = 0`, `F` empty. Each round: solve the prices for `theta` (decision 4); take
   `E = equipment(p)` (decision 6); `wear'[j] = E x M[j] / NM`; `need[j] = wear_cover x wear'[j] / (x[j] (wage[j]
   h[j] + sum_i a[i][j] p[i]))`, the margin that just covers the floor; `F' = F` plus every `j` with `lam x am[j] <
   need[j]` (exact; `F` only grows, as `model.py`); `phi'[j] = up_to_grid(need[j], FLOOR_GRID)` on `F'`; `e' =
   to_grid(E, MICROS)`. Stop when `F' = F`, `|e' - e|` is at most one micro and every `|phi' - phi|` at most one
   step of `FLOOR_GRID`; the answer is the solve at `theta'`. After 100 rounds, `prices_unsettled`. Each round's
   solve starts from the grids, not from the last prices, so Fractions do not grow across rounds; wear is a few
   percent of cost, so `e` contracts fast (the prototype took 3 floor rounds; expect under 20 rounds). With
   `phi` rounded up, every floored margin covers `wear_cover x` its wear.
6. **Trade at given prices** (model-spec 5, O6.3, O11, O5). Imports are paid at their sellers' own prices, as the
   compiled opening pays them (Task 14b): `p_r[i] = p[i] + (w_r[i] - wage[i]) h[i] (1 + mu[i])`, `w_r` the region's
   census wage; `p~[i] = sum_r sigma[i][r] p_r[i]`; imports' money `I = sum_i m[i] p~[i]`. Exports: the extraction
   trade's are `fin[extraction]` (what businesses leave); every other crossing trade's `X[i] = xs[i] x[i] kx`, with
   `kx = (I - p[ext] X[ext]) / sum p[i] xs[i] x[i]` over them; the rest 0. `kx` below 0 is `negative_exports`;
   with no export base (`sum p xs x = 0`) `kx` is 0 when `I - p[ext] X[ext] = 0`, else `negative_exports`.
   Equipment bought at home and abroad: `E = p[capital] (fin[capital] - X[capital])`. Households' purchases `H[i] =
   p[i] (fin[i] - X[i])` for the products households buy; one below 0 is `negative_residual: <product>`.
7. **What buyers save abroad.** A domestic buyer pays a foreign seller less than the national price: `S[i] = m[i]
   (p[i] - p~[i])`, dealt over buying trades by `import_buyers` (capital goods' by machines, public provision's
   part included). It is operating income of the trade that buys (the shop's for households' goods), and public
   provision's part lowers the grant. Without it, balance 1 is short by what imports save: counted by the lead on the
   prototype at 2.2% to 3.2% of household spending (18.5 to 27.8 a period, of which the shop's part is 4.1 to 6.2),
   with foreign sellers at 60% to 40% of the country's wage. This is not in the prototype's model; listed in the
   metadata. Under `shop_import_saving =
   "households"` (V10) the shop's part of `S` is no income of the shop: it posts each good at what it pays plus its
   charge, so `H[i]` of a shop good is lower by the shop's saving on it and `OI[shop] = U[shop]`.
8. **Operating income, public money and one tax rate** (model-spec 7; O12, O13; call 5). `Pi[j] = p[j] x[j] mu[j] /
   (1 + mu[j])`; `OI[j] = Pi[j] + U[j] + S[j] - wear[j]` for private trades and `OI[shop] = U[shop] + S[shop]`; one
   below 0 is `negative_operating_income: <trade>`. `PO = sum_j OI[j] x public_employee_persons[j] /
   employee_persons[j]`. The grant `G = payroll[public] + sum_i a[i][public] p[i] x[public] + wear[public] -
   S[public] - fee x domestic persons`. Support `SUP = reserve persons x s`, `s = t1q[food] x p[food]`: one period of
   the food need at the producer's price (Task 4, decision 6; `support_unit_price` reads the commodity's price).
   Benefits `BEN` (decision 10). `W` is every trade's census payroll. Then `t = (G + SUP + BEN - PO) / (W + sum OI -
   PO)`, `f = BEN / (t (W + sum OI))`, payout `(1 - t)(sum OI - PO)` (`private_distribution_bps = 10000`). `t` or
   `f` outside `[0, 1)` is `tax_rate`.
9. **Spending and tier 1** (model-spec 7). `rho = H[shop] / sum_shop goods H`; at posted prices `Hs[i] = H[i] (1 +
   rho)` for shop goods, else `H[i]`; `C = sum H + H[shop]`; `cbar = C / domestic persons`. Tier 1 is the five needs
   in households' own mix: `t1[i] = tier_sizes[0] x cbar x Hs[i] / sum_needs Hs` a person of average size; a
   household need's value a household is `t1[i] x AVG`, `AVG = persons / households` over the five non-collective
   keys. Quantities a basis: `t1q[i] = t1[i] / posted[i]` accounts dollars a person for a person need, `t1q[i] =
   t1[i] x AVG / posted[i]` a household for a household need; `posted[i] = p[i] (1 + rho)` for shop goods, else
   `p[i]`. `Opening.tier_one` holds the values a basis (`t1[i]`, or `t1[i] x AVG`). Public provision's need (1 a
   person at its fee) is outside the sizing, as the prototype.
10. **The benefit under the setting** (model-spec 11; O12; call 18). An account pays its own sellers' posted prices
    (O5), and the census names the wage of the site that sells each product to each place's accounts of each key
    (`Place.sellers`). So an account's own price of a need is `pown[i] = p[i] + (w_seller[i] - wage[i]) h[i] (1 +
    mu[i])` for a service (Task 14b's `own_price`), and `p[i] (1 + rho x w_seller[i] / wage[shop])` for a shop good
    (the national price plus the charge at its retailer's wage). Its own tier-1 cost a person is `c1own = (persons x
    sum_person needs t1q[i] pown[i] + households x sum_household needs t1q[i] pown[i]) / persons + fee` (no
    household needs for a residence).
    `dearest_place` (default): `b` is the highest `c1own` over the no-earner accounts of the 316 parts of the 187
    pooled places (both no-earner keys) and `bc` the highest over the residences: one figure each, enough in the dearest
    place. `BEN = b
    x no-earner persons + bc x (collective persons - collective employed)`. `each_place_own`: each account its own
    `c1own`, summed; `one_average`: the cost at national posted prices of all no-earner accounts over their persons
    (and likewise for the residences). Under each rule a residence is paid for its residents with no job.
11. **The national accounts and kept money** (model-spec 8; call 20). The margin factor is set on the census's
    national accounts, one for each key. Money a period: every key's `reserve x s` (support); beside it an earning
    key's and the residence's `wage income (1 - t)`, a no-earner key's `b x persons`, the residence's `bc x (persons
    - employed)`; the two owner keys share the payout by households. Full cost: `persons x (sum of the person needs'
    t1 + fee + (tier_sizes[1] + tier_sizes[2]) cbar) + households x sum of the household needs' t1 x AVG` (no
    household needs for the residence). Kept: `sum max(0, money - full cost)`. Luxury scaling (call 20) is applied
    to the parts' accounts in Task 11, not here: with it nothing is kept at any factor, so it cannot set
    the factor.
12. **The margin factor** (model-spec 9). `largest_with_nothing_kept` bisects on `[0, 1]`: kept at 0 above 0 is
    `margin_scale_none`; kept at 1 equal to 0 gives 1; else `margin_halvings` (40) halvings, keeping `lo` with nothing
    kept and `hi` with some; the answer is `lo`, a multiple of `2^-40`. Every test is exact.
13. **Balances at the exact solve** (O6): 1, the national accounts' money against `C` plus the fee; 2, receipts `t
    (W + sum OI) + (1 - t) PO` against `G + SUP + BEN`; 3, exports `sum p X` against imports `I`; 4, `sum wear`
    against `E`. Each residual comes only from `e`'s micro grid; `opening` refuses `income_identity` if balance 1's
    residual passes one dollar a period.
14. **Run time.** One `opening` is under 20 rounds of a 10 by 10 elimination on grid-sized Fractions (a few hundred
    digits at most), well under a second; `solve` is 42 openings: seconds, not minutes.

- [ ] **Step 1: Write the failing tests** (`test_national_opening_solve.py`; a `Quantities` is built by hand in the
  three-trade tests, with `economy` a small `Economy` of food, capital goods and household services):
  - `prices_solve_the_system_exactly`: wages $20, $30, $25 an hour; `h` 1/100, 1/50, 1/40; `a[hs][food] = 1/5`,
    `a[hs][capital] = 1/5`, `a[food][hs] = 1/10`; margins food 1/10, capital goods 1/10, household services 1/5;
    `e = 0`, no machines: `p[food] = 1925/4868`, `p[capital] = 101673/121700`, `p[hs] = 1941/2434`, as `Fraction`s,
    equal.
  - `the_floor_holds_at_the_solution` (the same economy with machines 10, 10, 1, `x` 1,000, 500, 2,000, fin of
    capital goods 100, `lam` 0 so every trade is floored): every private margin `Pi[j] >= wear_cover x wear[j]`,
    `F` holds the three trades, and `e` equals `to_grid(equipment(p), MICROS)` within one micro.
  - `a_singular_system_is_refused`: `a[hs][food] = 10`, `a[food][hs] = 1/10` and margin 0 make the system singular:
    `prices_singular`.
  - `imports_are_paid_at_their_sellers_prices`: one region at half the wage of food; `sigma` 1; `p~[food] = p[food] -
    (wage/2) h (1 + mu)`; `S[food] = m (p - p~)` and it is in food's buyers' operating income.
  - `largest_with_nothing_kept_is_exact`: with `kept_at(l) = max(0, l - 3/10)`, the answer is `329853488332 /
    2**40`, the largest multiple of `2^-40` not above 3/10; with `kept_at(l) = 1`, `margin_scale_none`; with
    `kept_at(l) = 0`, 1.
  - `the_benefit_covers_the_dearest_seller`: two places whose accounts' sellers of household services pay $20 and
    $30 an hour: under `dearest_place` `b` is the dearer account's own cost a person; under `each_place_own` `BEN`
    is the two accounts' own costs summed; under `one_average` `b` is the cost at national posted prices.
  - `every_key_gets_its_support`: a no-earner key with 10 reserve persons has `10 x s` beside `b x persons`, and the
    keys' money sums to wages after tax, the payout, support and benefits.
  - `refusals_have_their_codes` (hand cases): firms that take more of a product than is made and imported give
    `negative_residual: <product>`; imports worth less than extraction's exports give `negative_exports`; benefits
    above every tax base give `tax_rate`; a trade whose wear passes its margin and saving gives
    `negative_operating_income: <trade>`.
  - On the committed tables (marked `@pytest.mark.slow`; one module fixture solves once):
    `the_margin_factor_leaves_nothing_kept` (kept at `lam` 0, at `lam + 2^-40` above 0);
    `every_margin_covers_its_wear`; `the_four_balances_close_at_the_exact_solve` (each residual at most `10^-9` of
    its flow); `every_job_is_needed_at_the_exact_solve` (`h[j] x[j] = hours[j]` for every trade, exactly).
    Print for the hand-over: `lam`, `t`, `f`, `kx`, `b`, `bc`, `cbar`, `C`, `G`, `E`, the floored trades and the
    rounds. The prototype's figures (`lam` 0.116, rate 13.9%, share 47.9%, `kx` 2.73, `C` $859.8bn, `cbar` $2,567, a
    no-earner person at national prices $1,205, at the dearest county $1,947) are the size to expect, never asserted:
    the builder's people, the dearest place's rule and the import prices all differ.
- [ ] **Step 2: Run them and see them fail** (fast tests: `-m 'not slow'`).
- [ ] **Step 3: Implement** decisions 1 to 13.
- [ ] **Step 4: Run them** (the slow ones once, in the background) **and the gate.**
- [ ] **Step 5: Commit** with the subject above.

What the player would see: nothing yet; the prices come in Task 13.

### Task 10b: The builder, part 3: units, whole-number recipes, prices and machines

Commit `feat(reference): whole-number units, recipes and prices for the opening`.

**Files:**
- Create: `tools/national_opening_units.py`; `tests/unit/tools/test_national_opening_units.py`

**Interfaces:**

```python
BATCHES: Final = (1, 2, 4, 5, 8, 10, 16, 20, 25, 32, 40, 50, 64, 80, 100, 128, 160, 200, 250, 400, 500, 800,
                  1000, 2000, 5000, 10000)
@dataclass(frozen=True)
class Product:
    key: str; label: str; unit_label: str; kind: Literal["storable", "utility", "service"]
    dollars_per_unit: Fraction             # accounts dollars in one unit (u)
    price_micros: int; minimum_micros: int; maximum_micros: int; step_micros: int
    grams_per_unit: int                    # storable goods; 0 for services
    handling: tuple[int, int] | None       # (hours, units) for a shop good
@dataclass(frozen=True)
class Recipe:
    trade: str; output_units_per_batch: int; labor_hours_per_batch: int
    inputs: Mapping[str, int]; margin_bps: int | None   # None for public provision
    exact_cost_micros: Fraction; rounded_cost_micros: Fraction
@dataclass(frozen=True)
class Written:
    products: Mapping[str, Product]; recipes: Mapping[str, Recipe]
    machine_price_micros: int; workers_per_machine: Mapping[str, int]; machine_life_periods: int
    wage_tax_bps: int; operating_income_tax_bps: int; fund_share_bps: int
    import_bps: Mapping[str, int]
    batch_hours_lost: Mapping[str, Fraction]   # an estimate, for the metadata (decision 5)
def handling_block(hours_per_unit: Fraction) -> tuple[int, int]: ...
def batch(trade: str, hours_per_unit: Fraction, inputs_per_unit: Mapping[str, Fraction], wage_micros: int,
          prices: Mapping[str, int], price_micros: int, wear_micros: Callable[[int], Fraction]) -> Recipe: ...
def written(o: Opening, recut: Recut, census: Census, settings: Settings, template: TemplateFacts) -> Written: ...
```

**Decisions:**
1. **Units households buy** (first draft's decision 1, kept). Each need's unit is a day of tier 1: for a person need
   `u[i] = t1q[i] / 28` (food, utility, household services: one person for a day), for a household need the same rule on
   a household's `t1q` (materials, housing: one household for a day). So tier 1 holds exactly 28 of each, and needs
   round nothing. (`t1q` is already a household's for a household need, Task 10 decision 9, so `u[i] = t1q[i] / 28` for
   all five.) Consumer goods, business services and leisure take a unit of a day's food in producer value: `u[i] =
   p[food] u[food] / p[i]`. Public provision keeps its unit (a person-period), its need of 1 a person and its fee of
   `public_fee_micros`: `u[public] = x[public] / domestic persons`. Labels: food "Food for one person for a day", unit
   "person-day food"; utility "Utility for one person for a day", "person-day utility"; household services "A day's care
   and schooling for one person", "person-day care" (call 7); materials "Supplies for one household for a day",
   "household-day supplies"; housing "Housing for one household for a day", "household-day housing"; consumer goods,
   business services and leisure "<the fixture's label>, a day's food's worth", units "consumer goods bundle", "business
   service unit", "leisure unit"; resources "An hour of extraction's output", "extraction hour"; equipment "One
   machine", "machine"; public provision as the fixture.
2. **Units businesses buy.** Resources: an hour of extraction work, `u = 1 / h[extraction]`. Equipment: one machine,
   `u = (E / p[capital]) x machine_life_periods / NM`, so `NM / life` machines are bought a period and one machine's
   price is `E x life / NM`: wear is one machine in `life` a period (Task 4's `wear`).
3. **Prices.** `price_micros = half_up(p[i] u[i] x 10^6)` for every private product; public provision's is the fee.
   Minimum, maximum and step at the fixture's ratios: a quarter, four times and a fortieth, each rounded down, the
   step at least 1. A unit whose price rounds below 1,000 micros is `price_zero: <product>` (its rounding could
   pass one part in 2,000).
4. **Grams** (tell-with-dialog item 7). A storable good's `grams_per_unit = max(1, half_up(fixture grams x
   price_micros / fixture opening price))`: the fixture's grams per dollar. `resource_deposit` keeps the grams of
   `resources` and extraction's recipe takes `resource_deposit` equal to its output units (the deposit rule).
   `[grain.basis]` is pinned (Task 7), so grams move no place.
5. **Whole-number recipes** (first draft's decision 3, with two checks added). For each of the eleven trades with a
   recipe, per unit of output: hours `h[j] u[j]`, inputs `a[i][j] u[j] / u[i]`. `batch` tries `n` in `BATCHES` in
   order: `L = half_up(h u n)`, each input `half_up(a u n / u_i)`; skip `n` if `L` or any input is 0 (every input is
   kept: the spike's section 4). The rounded cost a unit is `(wage x L + sum inputs x price) / n` at written prices;
   the exact cost is `wage x h u + sum a u / u_i x price`, also at written prices, so the error is the rounding's
   alone. Take the first `n` whose error is at most 1/200 and that passes O5's refusal as Task 14b reads it:
   `price x n >= L x wage + sum inputs x price + wear per batch`, wear per batch `machine price / (ceil(160 x
   workers_per_machine / L) x life)` (Task 6). If none, the `n` of least error at most 1/100 that passes the refusal
   (ties: the smaller `n`); if none, `recipe_rounding: <trade>`. Planned batches are whole (`actors.rs`: `employed x
   160 / L` rounded down), so each site loses less than one batch of hours; `batch_hours_lost[j] = sites x L / 2 /
   hours[j]` is written to the metadata as an estimate. One machine takes thousands of hours, so capital goods'
   estimate is the largest; it is reported, not refused.
6. **Margins written.** `margin_bps` is `half_up(mu x 10_000)` for a trade off the floor and `ceil(mu x 10_000)` on
   it, so a floored margin never falls under its floor by rounding. Public provision has none.
7. **Handling blocks** (O9, the shop as it is; R3). A shop good's exact hours a unit are `rho x p[i] u[i] /
   wage[shop]` (retail hours follow value: the spike's assumption, kept). `handling_block` gives the smallest `units`
   in `1..=1000` with `hours = half_up(exact x units)` at least 1 and `|hours / units - exact|` at most `exact /
   200`; none is `handling_rounding: <good>`. The blocks are for every storable good a need or a want names (food,
   materials, consumer goods; Task 1 decision 1).
8. **Taxes, the fund and trade shares written.** `wage_tax_bps = operating_income_tax_bps = half_up(t x 10_000)`;
   `fund_share_bps = half_up(f x 10_000)`, the same for both taxes (Task 1's `[fund]`). A domestic buyer's import
   share is a cap on buyers whose second supplier is foreign only (`procure`), so the share written makes the
   nation's imports what the accounts say: `import_bps[i] = half_up(10_000 x IMP[i] x total weight[i] / foreign
   weight[i])`, the weights of Task 10 decision 3 over all domestic buyers and over those with a foreign second
   supplier; above 10,000 is `import_coverage: <good>`. Equipment's share is `IMP[capital]` over machines (Task 5
   chooses whole processes).

- [ ] **Step 1: Write the failing tests:**
  - `a_recipe_takes_the_smallest_batch_within_half_a_percent`: hours a unit 7/1000, one input of 1/3 unit a unit,
    wage $20, input price $2, output price $1, no wear: `n = 1000`, `L = 7`, input 333 (errors at 400, 800 are 1.03%
    and 1.34%; at 1,000, 0.083%).
  - `a_recipe_under_cost_is_refused`: the same with the output price at 805,860 micros (the exact cost, 121/150 of
    a dollar, less a thousandth): every batch within 1% costs at least 806,000 micros a unit, so none passes O5's
    refusal: `recipe_rounding: <trade>`.
  - `a_trade_that_cannot_round_is_refused`: an input of `10^-7` of a unit a unit gives `recipe_rounding: <trade>`.
  - `a_block_takes_the_fewest_units_within_half_a_percent`: exact 7/60 hours a unit gives `(5, 43)`; exact 1/3000
    gives `handling_rounding`.
  - `prices_and_their_bounds_follow_the_fixture_ratios`: a price of 280,000,000 gives 70,000,000, 1,120,000,000 and
    7,000,000; a price of 39 micros gives `price_zero`.
  - `tier_one_holds_28_of_each_need`: on a hand `Opening`, `t1q[i] / u[i] = 28` for each of the five needs, and a
    tier-1 row costs 28 written prices, exactly.
  - `grams_follow_value`: food at twice the fixture's price has twice its grams; the deposit's grams are resources'.
  - On the committed tables (slow): `rounded_recipes_cost_within_one_percent` (every recipe within 1%, no input 0,
    every private trade passes O5's refusal at written figures); `handling_blocks_are_close`;
    `the_import_shares_written_meet_the_accounts` (`import_bps x foreign weight / total weight` within one basis point
    of `IMP`). Print each recipe's `n`, `L`, error and `batch_hours_lost`.
- [ ] **Step 2: Run them and see them fail. Step 3: Implement. Step 4: Run them and the gate.**
- [ ] **Step 5: Commit** with the subject above.

What the player would see: products named in days and households, prices of a few dollars a unit.

### Task 11: The builder, part 4: each place's accounts, the tiers and the benefit

Commit `feat(reference): the tiers, the benefit and each account's money`.

**Why.** The tiers must make what the game's own accounts buy, under R4, equal what households must buy of each
product, or some trade's workers are not needed (model-spec 10; the prototype: proportional contents bought by the
order of paying miss food by 29%). The accounts are the game's own: the 316 parts of the 187 pooled places by six
keys (a part is the census's row and this task's "place"); an account above its three tiers spends all on its
luxuries (call 20).

**Files:**
- Create: `tools/national_opening_tiers.py`; `tests/unit/tools/test_national_opening_tiers.py` (a module of its
  own: the tier solve needs the written prices of Task 10b, which imports the solve)

**Interfaces:**

```python
TIER_GRID: Final = 2**32    # contents, units a person: to_grid(., TIER_GRID)
@dataclass(frozen=True)
class Account:
    place: str; key: HouseholdKey; persons: int; households: int; employed: int; money_micros: int
    own_prices: Mapping[str, int]     # its own sellers' posted price of each product's unit, micros (decision 2)
@dataclass(frozen=True)
class Row:
    good: str; tier: Literal[1, 2, 3]; basis: Literal["persons", "households"]; units: Fraction
@dataclass(frozen=True)
class Bought:
    units: Mapping[str, Fraction]; reach: tuple[Fraction, Fraction, Fraction]; left_micros: Fraction
    pattern: tuple[int, int, bool]    # (tier, row index where money ended, scaled); (3, len, True) when scaled
def accounts(o: Opening, census: Census, w: Written) -> tuple[Account, ...]: ...
def buy(account: Account, rows: Sequence[Row], prices: Mapping[str, int], scale: Fraction | None = None) -> Bought:
    ...
@dataclass(frozen=True)
class Tiers:
    comfort: Mapping[str, int]; luxury: Mapping[str, int]   # whole units a person a period, rows that round to 0 out
    exact: Mapping[str, Fraction]                           # the solve's z, for the metadata
    luxury_scale_bps: Mapping[tuple[str, HouseholdKey], int]   # accounts above their three tiers
    no_earner_micros: int                                   # the benefit a person, as written
    residence_micros: Mapping[str, int]                     # by place hub: a resident's amount
    reach: Mapping[tuple[str, HouseholdKey], tuple[Fraction, Fraction, Fraction]]
    demand_gap: Mapping[str, Fraction]                      # bought over needed, less 1, at written figures
    own_price_gap: Mapping[str, Fraction]                   # the same with every account at its own prices
    state_services: Mapping[tuple[str, str], tuple[Fraction, Fraction]]   # (state, service) -> capacity, use
    place_bodies: Mapping[str, tuple[Fraction, Fraction]]   # receipts, payments a period
    place_fund_share_bps: Mapping[str, int]                 # under place_body other than one_share
    place_grant_micros: Mapping[str, int]
    own_place_benefit_micros: Mapping[str, int]             # under benefit_rule each_place_own
def tiers(o: Opening, census: Census, w: Written, settings: Settings) -> Tiers: ...
```

**Decisions:**
1. **The accounts** (model-spec 8, on the game's people). One account per place and key with persons (an account of
   no persons is left out), from the census's places; Wayne's detailed accounts of one key are one account here.
   Money a period, at the exact solve, rounded down to whole micros: an earning key's and the residence's `wage
   income (1 - t) + reserve x s`; the two owner keys share the place's payout by households over
   `owner_households`; a no-earner key `b x persons + reserve x s`; the residence `amount x persons` beside its wages
   (decision 6). A place's payout is `(1 - t)` times its private operating income: `OI_c = sum_j (OI[j] x emp_c,j /
   emp_j + mu[j] (payroll_c,j - wexact[j] x 160 x emp_c,j))` less its public-owned part by the same rule over
   public employee persons and payroll, `wexact = payroll / (employee persons x 160)` exactly; the second term is O5's
   margin on the place's own wage, and it sums to 0 over places. So the places' money sums to the national accounts'
   within one micro an account.
2. **Rows and prices.** Tier 1 is the six needs: 28 a person of food, utility and household services, 28 a household
   of materials and housing, 1 a person of public provision (no household rows for a residence). Wants are by person
   (the prototype's reading; listed). The tier solve buys every row at the NATIONAL posted price of its unit: the
   written price plus, for a shop good, `ceil(hours x wage[shop] / units)` (Task 3, decision 4). The national
   accounts close there, and only there (decision 12). What depends on one account's own purse is set at its OWN
   posted prices, `Account.own_prices`: for a service Task 14b's `own_price` at its seller's wage, for a shop good
   the written price plus the charge at its retailer's wage (`Place.sellers`). Those are the benefit (decision 6)
   and the luxury scales (decision 10).
3. **Buying** (R4; model-spec 10). `buy` takes tier 1, 2, 3 in turn and, inside a tier, the rows in the order of
   paying (public provision, which is not in it, last); each row whole while money lasts; the row where it ends takes
   the rest in fractional units; what is left after tier 3 is kept unless `scale` is given, when tier 3's rows are
   bought times `scale` (call 20). `pattern` records where the money ended.
4. **Contents** (model-spec 10, unknowns and pins as the prototype). Nine unknowns `z`: tier 2 units a person of
   food, materials, consumer goods, utility, housing, household services and business services; `rho3`, with tier 3
   holding `rho3` times tier 2 of the five need products; leisure in tier 3. Consumer goods and business services
   hold the same in tiers 2 and 3; leisure is in tier 3 only. Nine equations: for each product households buy but
   leisure, the accounts' bought units equal `D[i] = (fin[i] - X[i]) / u[i]` (seven, as `(bought - D) / D`); and the
   two sizes, `sum tier 2 units x posted = tier_sizes[1] x cbar` and the same for tier 3 (as `(cost - size) /
   cbar`). Leisure's equation is the sum of the others when nothing is kept, so it is left out and its residual is
   reported: it measures what rounding prices to micros moves (`demand_gap["leisure"]`).
5. **Scaled accounts.** An account whose money passes its full cost (`persons x (tier 1 a person at its size +
   (tier_sizes[1] + tier_sizes[2]) cbar)`) at national posted prices is scaled. That set does not depend on `z` (the
   sizes are fixed), and the scaled account's tier 3 rows are bought as `units x (money - tier 1 - tier_sizes[1]
   cbar persons) / (tier_sizes[2] cbar persons)`, which equals the true buy at a solution. So inside one set of
   patterns every bought quantity is a polynomial of degree at most 2 in `z` (degree 2 only through `rho3`).
6. **The benefit written** (O12; call 18; For the Director item 3). An account's own tier-1 cost is its tier 1 rows
   at its own posted prices. Under `dearest_place`: `no_earner_micros = ceil(max over no-earner accounts of own
   tier-1 cost / persons)`, so every no-earner account reaches tier 1 at its own sellers. A residence: `bc_micros =
   ceil(max over residences of own tier-1 cost / persons)`, and each hub's amount a resident `floor(bc_micros x
   (persons - employed) / persons)`, persons and employed summed over the residences of the hub's parts (call 18:
   rounded down; Task 4 has one residence program a hub). Under `each_place_own` each account's own cost, one
   amount a place and key; under `one_average`, the cost at national posted prices over all no-earner persons.
7. **The tier solve, exact on each piece.** Start `z0`: half of tier 1 a person for the need products, consumer
   goods and business services sharing `cbar / 5` by `Hs` (in units), `rho3 = 13/10`, leisure `4/5 cbar` (the
   prototype's start). Each step: take every account's `pattern` at `z`; evaluate the residual `r(z)` with those
   patterns held; the Jacobian column `k` is `(r(z + e_k) - r(z - e_k)) / 2` with the patterns held (exact, since each
   piece is of degree 2); solve `J dz = -r` exactly (9 by 9; singular is `tiers_singular`); try `z + dz`, halving
   `dz` while any unknown is below 0 or the sum of squared residuals (patterns re-taken) does not fall, at most 30
   times (then `tiers_unsolved`); put the new `z` on `TIER_GRID`. Stop when two successive `z` are equal, or every
   residual is at most `10^-12` and no pattern changed in the step. At most 60 steps, else `tiers_unsolved`. An
   unknown below 0 at the end is `tiers_negative: <product>`.
8. **Is it unique?** The prototype found its solution from one start. The builder solves again from a second start,
   the contents in proportion to households' spending (each tier's other products in proportion to `Hs`, `rho3 =
   1`). If both converge and their whole-unit contents (decision 9) differ, `tiers_not_unique: <products>`: the
   written wants must not depend on where the search began, and a pin is then the lead's to add. If the second start
   does not converge, the metadata says so and the first stands.
9. **Whole units** (first draft's decision 4, with a choice of direction). Round each want half up; then, for each
   product in the order of paying, choose among rounding each of its want rows down or up the combination whose
   product's bought units at written figures are nearest `D` (ties: half up), holding every other row. A row at 0 is
   left out and listed. Then: tier money at written contents within 1% of each size, else `want_rounding: <tier>`.
   `demand_gap` is each product's bought units at written figures over `D`, less 1. For crossing goods the gap is
   what Task 12's export shares absorb; for services it is reported (Task 15 measures it against workers).
10. **Luxury scales written** (call 20). An account is scaled in the scenario when its money passes its three
    tiers at its OWN posted prices and written contents: `luxury_scale_bps = floor(10_000 x (money - tier 1 - tier
    2) / tier 3)`, each tier at its own prices; only those above 10,000 are written, each under its part's label and
    its budget key (Task 1). So in the compiled opening every account spends its money where it buys. (The solve's own
    scaled set, decision 5, is at national prices.)
11. **Each place's body** (model-spec 12; For the Director item 4). For the metadata under every setting: receipts
    `(1 - f) t (residents' wage income + OI_c) + (1 - t) PO_c`, payments `payroll_c,public + (G - payroll_public) x
    emp_c,public / emp_public + reserve_c x s`. Under `even_where_own_taxes_reach` (V1): the place's fund share
    `max(0, 10_000 - floor(10_000 x payments / taxes))`; under `every_place_even`: that, and for a place whose
    payments pass its taxes a grant of the gap in whole micros (V2's road (b)). Under `one_share` both tables are
    empty.
12. **What own prices and the same-state rule move: counted, not solved** (For the Director, item 5). The solve
    balances the national accounts at national prices. Two things in the game do not follow it, and no tier list
    can make them: an account pays its own sellers' prices, and a service is bought only from a provider in the
    buyer's own state (`service_reach = same_state_or_own_counterpart`). The builder counts both at written figures
    and writes them to the metadata. Nothing is asserted.
    - `own_price_gap[product]`: every account buys again by R4 at its own posted prices, with its written scale;
      the units bought over `D`, less 1.
    - `state_services[(state, service)]`, for utility, housing, household services, leisure and business services,
      and for the shop's hours: capacity, the hours of the state's census workers of the trade over the written
      recipe's hours a unit (the shop: its workers' hours); and use, what the state's accounts buy at their own
      prices, plus what its sites need by the written recipes at their census hours, plus its public providers'
      need. The metadata also gives, for each service, the share of capacity in states that use less than they can
      make (`idle`) and the share of use in states that want more than they can make (`unserved`).
    The prototype's sizes, never asserted: at state prices the gap by product is -0.7% to +2.4%; idle and unserved
    are about 17% for utility, 12% for leisure, 8% for housing, 7 to 9% for business services, 6% for household
    services and 2 to 4% for the shop's hours.

- [ ] **Step 1: Write the failing tests:**
  - `buying_goes_tier_by_tier_and_row_by_row`: persons 2, households 1, money $95; tier 1 food 28 a person at $1 and
    materials 28 a household at $0.50; tier 2 food 5, consumer goods 10, business services 10 a person, each at $1:
    bought food 66, materials 28, consumer goods 15, business services 0; reach (1, 1/2, 0); left 0; pattern (2, 1,
    False).
  - `an_account_above_its_tiers_scales_its_luxuries`: persons 2, households 1, money $150, the rows above and tier 3
    leisure 10 a person at $1, `scale` 3/2: leisure 30, left 0.
  - `the_tier_solve_recovers_known_contents`: three hand accounts, the eight products at posted $1 to $8, contents
    `z*` on the grid chosen in the test; `D` made by buying `z*`; the solve from `z0` returns `z*` within `2^-30` of
    every unknown and every residual 0.
  - `two_solutions_are_refused`: the uniqueness check given two converged `z` whose whole-unit contents differ in
    food (8 against 9) gives `tiers_not_unique: food`; given two that differ only below half a unit, passes.
  - `place_money_sums_to_the_nation`: on a hand `Opening` and a two-place census, the accounts' money sums to the
    national accounts' within one micro an account, and the place OI terms of O5 sum to 0.
  - `the_benefit_reaches_tier_one_at_its_own_sellers`: two places; under `dearest_place` every no-earner account's
    tier 1 at its own posted prices costs at most `no_earner_micros x persons`, with less than one micro a person
    to spare for the dearest; a residence of 10 persons and 4 employed is paid `floor(bc x 6 / 10)` a resident.
  - `a_scale_is_set_at_the_account_s_own_prices`: one account whose sellers charge twice the national price of
    leisure: its scale is `floor(10_000 x (money - tier 1 - tier 2) / tier 3)` with each tier at its own prices, and
    bought at its own prices with that scale it keeps less than one unit's price of its dearest luxury.
  - `own_prices_move_what_accounts_buy`: two accounts of equal money and persons, one whose sellers charge half
    the national price of a service and one twice. At national prices they take the same units. At their own prices
    the first takes more and the second less, by the figures in the test; `own_price_gap` is the two over `D`, less
    1.
  - `a_state_s_services_are_counted`: a hand census of two states, one with every leisure worker and one with all
    the money: the first state's capacity is `idle` but for what its own accounts buy, the second's use is
    `unserved`, and over both states capacity equals use at national prices.
  - `each_place_body_setting`: a two-place hand case: under `one_share` no table; under
    `even_where_own_taxes_reach` the shares of V1's formula; under `every_place_even` the poorer place's grant equals
    its gap.
  - On the committed tables (slow): `no_account_opens_without_its_tier_one` (every place account's money reaches
    tier 1 at its own posted prices; an account that does not is printed with its place, key and gap);
    `nothing_is_kept` (at its own prices and written scale no account keeps more than one unit's price of its
    dearest luxury a person); `the_tiers_buy_what_households_must` (each product's `demand_gap` within 1/100,
    leisure's within 1/100); `tier_money_has_its_sizes` (within 1% at written contents); print the number of scaled
    accounts and their median scale (the prototype's 236 counties of 3,144, median 1.25, is the size, never asserted),
    each key's money a person and reach, the benefit, the residences' amounts' range, `own_price_gap` by product,
    and each service's `idle` and `unserved` shares with its three lowest and three highest states.
- [ ] **Step 2: Run them and see them fail. Step 3: Implement. Step 4: Run them and the gate.**
- [ ] **Step 5: Commit** with the subject above.

What the player would see: four standards from the first period: the bottom half getting by, the next 40%
comfortable, the owners affluent, every household with no earner fed.

### Task 12: The builder, part 5: foreign regions in balance (O11)

Commit `feat(reference): give each foreign region its mix of jobs and its share of trade`.

**Why.** The prototype did not do it. The first draft's method stands in part: a region's jobs follow the hours its
output needs, and one factor a region balances its trade. What it lacked: the region's money, which sets what its
households buy; the closure that fixes it (its employed must be needed); and the export mix by good, which must add
up to the nation's exports of each good so that the country's workers stay needed.

**Files:**
- Create: `tools/national_opening_abroad.py`; `tests/unit/tools/test_national_opening_abroad.py`

**Interfaces:**

```python
SHARE_GRID: Final = 2**40
@dataclass(frozen=True)
class RegionOpening:
    key: str
    function_weights_bps: tuple[int, ...]     # twelve, in the policy's Ord order: business, capital, housing,
                                              # consumer goods, distribution, energy, extraction, food, household
                                              # services, leisure, manufacturing, public; each >= 1, sum 10,000
    export_bps: Mapping[str, int]             # by crossing product
    money_per_person_micros: int
    sales_micros: int; purchases_micros: int  # a period: to the United States, from it
    luxury_scale_bps: int | None
def region_prices(w: Written, o: Opening, wage_micros: Mapping[str, int], census: Census) -> Mapping[str, int]: ...
def regions(o: Opening, census: Census, w: Written, t: Tiers, settings: Settings) -> Mapping[str, RegionOpening]:
    ...
```

**Decisions:**
1. **A region's prices** (O5; Task 14b). Each product's at the region's census wage: Task 14b's `own_price` on the
   written recipe and margin, exactly as the compiler computes it; a shop good as its retailers post it (the written
   national price plus the charge at the region's shop wage, `retail_stock`). Public provision's fee as at home.
2. **What a region sells** to the country: `s[r][i] = sigma[i][r] x m[i] / u[i]` units a period (Task 10 decision 3),
   valued at the region's prices: `S_r`. A region with none sells nothing and buys nothing (`export_bps` 0).
3. **What a region needs.** In units a period, with the written recipes: `A[i][j] = inputs / n`; machines as an
   input, `sum over trades (L_j / n_j) / (160 x workers_per_machine[j] x life)` units of equipment a unit of `j`;
   public provision 1 a person; retail hours from the blocks on the shop goods its households buy. Its households are
   one account (`PooledExternal`: persons, households from the census) whose money a person `mpp` buys the written
   tiers by R4 at the region's prices (tier 1 needs, the wants, then scaled luxuries if money is left: call 20 holds
   abroad too). So final demand `f(mpp)` is piecewise linear and rising in `mpp`.
4. **What it buys from the country.** `b[r][i] = beta_r x c_i x R[r][i]` for a crossing good, `R` the region's own
   requirement of `i` (`(A y)[i] + f[i]`), `c_i` one figure a good, `beta_r` one a region. Output `y = K (f(mpp) +
   s - b)`, `K = (I - A)^-1` computed once exactly (the same recipes for every region).
5. **The closure.** For fixed `b`, `mpp` is found by bisection on whole micros so that the hours `y` needs (recipes'
   hours and retail hours) are at least the region's `employed x 160` (the largest `mpp` whose hours do not exceed
   it, then the next micro): its workers are needed and its households spend what they make. If the hours at `mpp =
   0` already pass `employed x 160`, the region cannot make what it sells: `abroad_unbalanced: <region>`.
6. **The balance and the mix, iterated.** Start `beta = 1`, `c_i = (X[i] / u[i]) / sum_r R0[r][i]` with `R0`
   from `b = 0`.
   Each round: solve each region's `mpp` (decision 5) at the current `b`; recompute `R`; `beta_r = S_r / sum_i
   p_us[i] c_i R[r][i]` (purchases at the country's written prices equal sales); `c_i = (X[i] / u[i]) / sum_r beta_r
   R[r][i]` (the regions together take the country's exports of each good, Task 10); both on `SHARE_GRID`. Stop when
   every written figure (decisions 7 and 8) is unchanged between two rounds; after 100 rounds, `abroad_unsettled`.
7. **Weights.** A region's hours by trade, shared over 10,000 by largest remainder (`apportion`); a trade at 0 takes
   1 from the trade with most (the policy refuses 0, `admission.rs` `profile`). Written in the policy's Ord order.
8. **Shares.** `export_bps[r][i] = half_up(10_000 x beta_r x c_i)`; above 10,000 is `export_share: <region>/<good>`.
   Each region balances by construction; the nation does too (O6.3), up to the rounding of shares and of import
   prices to written micros, which Task 13 reports.
9. **Scales abroad.** A region whose money passes its three tiers has `luxury_scale_bps` as Task 11 decision 10,
   written under the region's key.
10. **Run time.** `K` once; a region's bisection is about 40 products of `K` with a vector of twelve; about 20 rounds
    of 13 regions: seconds.

- [ ] **Step 1: Write the failing tests:**
  - `a_region_s_workers_are_needed` (hand region of two trades and a shop, with written recipes in the test): the
    solved `mpp`'s hours are at least `employed x 160` and `mpp - 1` micro's are below it; the weights sum to 10,000,
    each at least 1.
  - `each_region_balances_by_construction` (two hand regions): each region's purchases equal its sales within one
    micro a unit bought; `sum_r b[r][i]` equals the country's exports of `i` within 1/1000.
  - `an_impossible_region_is_refused`: a hand region of 10 employed that sells 10,000 units of food at 1 hour a unit:
    `abroad_unbalanced: <region>`.
  - `weights_are_whole_and_positive`: hours (2, 0, 1) give (6666, 1, 3333).
  - On the committed tables (slow): `the_nation_balances_by_the_regions` (exports equal imports in money within 1%
    at written figures); `every_region_balances` (within 1%); print each region's weights, shares, `mpp` and its
    tier reach.
- [ ] **Step 2: Run them and see them fail. Step 3: Implement. Step 4: Run them and the gate.**
- [ ] **Step 5: Commit** with the subject above.

What the player would see: foreign regions whose workers make what the country buys from them, at their own wages,
and buy back machines and goods to the same value.

### Task 13: The builder, part 6: the scenario

Commit `feat(economy): the rebuilt national scenario, from the builder`.

**Files:**
- Create: `tools/make_national_opening_numbers.py`; `tools/national_opening_v13_defines.toml.in`;
  `tests/unit/tools/test_national_opening_numbers.py`; `content/scenarios/national-rebuilt/defines.toml` and
  `defines.metadata.json`

**Interfaces:**

```python
TEMPLATE: Final = ROOT / "tools/national_opening_v13_defines.toml.in"
SCENARIO_OUT: Final = ROOT / "content/scenarios/national-rebuilt/defines.toml"
METADATA_OUT: Final = ROOT / "content/scenarios/national-rebuilt/defines.metadata.json"
BUILDER_SOURCES: Final[tuple[Path, ...]]   # the six tools/national_opening_*.py and this file
@dataclass(frozen=True)
class TemplateFacts:   # what the builder reads from the template: the fixture's labels, grams and prices
    labels: Mapping[str, tuple[str, str]]; grams: Mapping[str, int]; prices: Mapping[str, int]
def template_facts(template: str) -> TemplateFacts: ...
def render(template: str, w: Written, t: Tiers, regions: Mapping[str, RegionOpening], settings: Settings) -> str: ...
def written_balances(...) -> Mapping[str, tuple[Fraction, Fraction]]: ...
def build(*, accounts: Path, pay: Path, census: Path, settings: Settings = Settings(),
          scenario_out: Path = SCENARIO_OUT, metadata_out: Path = METADATA_OUT) -> dict[str, Any]: ...
```

**Decisions:**
1. **The template** (first draft's decision 1, kept): the stage 2 fixture's text as Task 1 leaves it, with every
   figure the builder computes replaced by a marker line `#@builder <name>` on its own line, and its first lines
   replaced by the rebuilt scenario's (what it is; counted on the country bench; not played by the game's own turn
   yet). Every hand-authored section (organizer, aid, hearing, City PD, County Review, grain's own keys, companies,
   lifecycle, household time but `unmet_hours_per_unit`, counterparts' participation, employment, persons per
   household and wage fractions, the installation figures of `[equipment]`, and `[markets] place_services`) is the
   fixture's, unchanged. `[companies] opening_treasury_bps` is 0, as Task 7a leaves the fixture (the Director's
   ruling of 20 November: a company takes no working capital at the opening); `render` refuses a template in which
   it is not (`template_marker: opening_treasury_bps`).
   The fixture's commodity labels, grams and opening prices (which decision 4 of Task 10b and its labels read) stay
   in the template as one line each, `#@fact <key> | <label> | <unit label> | <grams> | <price micros>`;
   `template_facts` reads them and `render` drops them. `render`
   replaces each marker with TOML it writes itself: keys sorted inside a table, integers only, `\n` line ends, no
   trailing spaces. An unknown marker, one left over, or a computed block with no marker is `template_marker:
   <name>`.
2. **What the builder writes** under the default settings: every `[commodity.<key>]` but the deposit's (label, unit
   label, kind from `service_stage`, cargo class kept, grams, the four prices, `handling_hours` and `handling_units`
   on the shop goods); every `[process.<key>]` (output, `output_units_per_batch`, `labor_hours_per_batch`, inputs,
   `margin_bps` but public provision; extraction with its deposit); the six `[[household_needs]]` (28, 28, 28, 28,
   28 and 1 on their bases); the `[[household_wants]]` rows (tier `comfort` or `luxury`, basis `persons`, units);
   `[markets] import_bps` and `paying_order`; `[financial]` `wage_tax_bps` and `operating_income_tax_bps` equal,
   `private_distribution_bps = 10000`, `reserve_food_support_periods = 1`; `[fund]` with `evidence_class =
   "Designed"`, both shares `fund_share_bps` and `reserve_periods = 2`; the programs: `laid_off` (after layoff, rank
   0, 5,000 and 13), `no_earner` (per person, rank 0, `no_earner_micros`) and the residences' row (call 18, in the
   shape the notes propose for Task 1); the luxury scales (in the shape the notes propose for Tasks 1 and 3);
   `[equipment] workers_per_machine` (eleven trades) and `machine_life_periods = 100`; for each region and the
   dependency `function_weights_bps`, `export_bps` and `price_scale_bps = 10000`; `[grain.basis]` 16, 16, 1, 14,000
   (the shipped food figures, O15); `[household_time] unmet_hours_per_unit = { food = <max(1, half_up(20 / 28))> }`
   (today's 20 hours for a person's period of food: 1). No `[builder]` section (call 16).
3. **Size.** The file is at most 65,536 bytes (`admission.rs` `parse`), else `scenario_size`. The residences'
   amounts and the scales are tables of one line a place, so the file stays about 25,000 bytes.
4. **Settings the compiler does not admit yet.** `render` writes a stage-2 regrouping (V6: kinds and the order)
   and `one_average` (V4: one amount). For a stage above 2 (V7), a service in `crossing` (V8), `each_place_own` (V3),
   any `place_body` but `one_share` (V1, V2) and `shop_import_saving = "households"` (V10) it refuses
   `setting_needs_variant: <field> (<variant>)`: their
   figures are in the metadata, and the keys come with the variant's edit of Task 1.
5. **Balances as written** (design 8.1). `written_balances` recomputes O6 at the written figures: 1, the place
   accounts' money (Task 11) against what they buy by R4 at written contents, scales and their own posted prices; 2,
   taxes at the written rates on the exact bases, with the fund's split of Task 4 (`floor(rate x share / 10_000)`),
   against grants, support and benefits at written amounts; 3, exports at written prices and shares (Task 12)
   against imports at the regions' written prices; 4, wear at the written machine price over the census's machines
   against equipment bought at the written price. Each residual over its flow at most 1/100, else `balance: <n>`
   (the build refuses to write numbers that do not close).
6. **Metadata** (the builder's balance sheet, design 8.1): `contract: NationalOpeningNumbersV1`, `issue: PER-371`; the
   sha256 of the accounts, pay and census files, the template and each of `BUILDER_SOURCES`; the settings, each
   field; `lam`, the rate, the fund's share, the export factor, `cbar`, `C`, the benefit and the residences' range;
   for each trade its persons at work, wage, hours, output, inputs, margin (accounts and written), wear, operating
   income, public-owned part, tax, payout, what firms, households, public bodies and the regions take, what its
   buyers save abroad, and `batch_hours_lost`; each recipe's exact and rounded cost and error; each want's exact and
   written units; each product's `demand_gap` and `own_price_gap`; `state_services` with each service's `idle` and
   `unserved` shares (Task 11, decision 12); the four balances at the exact solve and as written; each key's money
   a person and reach, nationally and by place; the scaled accounts; each place's body (receipts, payments, and under
   other settings the tables); each region's weights, shares, money a person, sales and purchases; what was moved and
   dropped by rule; the two designed cross-border claims (`cross_border_ownership_bps` of Wayne's private consumer
   goods plants to Japan and of Canada's plants to Wayne, `financial.rs` `foreign_claim`), which the solve leaves
   out as the prototype did, at their size a period; the tier solve's steps, its second start's result; the
   regeneration command
   `UV_PROJECT_ENVIRONMENT=.venv mise exec -- uv run --frozen python tools/make_national_opening_numbers.py`. JSON
   with `indent=2, sort_keys=True` and a trailing newline; every `Fraction` written as the string `"n/d"` and beside
   it a decimal string to 9 places, rounded half up (for reading only).
7. **The scenario is not a reference table** and is not registered; the census it reads is (Task 8).
8. **Run time and the tests.** One build reads the tables (under a second), solves the nation (seconds), rounds,
   solves the tiers twice (the slowest part: about 20 steps of 19 evaluations over about 1,100 accounts, up to a
   minute), solves the regions (seconds) and writes: about a minute or two, under five. The unit suite must not pay
   it. Every test that builds from the committed tables is marked `@pytest.mark.slow` (the marker is registered in
   `pyproject.toml`; `mise run test:unit` runs `-m 'not slow'`, `mise run test:slow` runs them), and each such test
   file builds once in a module fixture. The fast test that keeps the committed scenario honest reads its metadata
   only: the sha256 of every input, the template and every builder source equal the files' own, so a change to any of
   them fails the unit suite until the scenario is rebuilt and committed; the slow test rebuilds and compares bytes.

- [ ] **Step 1: Write the failing tests:**
  - `the_template_has_every_marker` and `render_refuses_a_stray_marker` (an unknown marker, a leftover, a block with
    no marker: each `template_marker: <name>`).
  - `render_writes_integers_only`: the rendered text of a hand `Written` has no `.` in any value line and parses with
    `tomllib`; its commodity and process keys are the fixture's.
  - `a_setting_that_needs_a_variant_is_refused`: `crossing` with business services gives `setting_needs_variant:
    crossing (V8)`; `place_body = "every_place_even"` gives `setting_needs_variant: place_body (V1, V2)`;
    `one_average` renders.
  - `the_committed_scenario_names_its_inputs` (fast): the committed metadata's sha256 of the accounts, pay, census,
    template and every `BUILDER_SOURCES` file equal the files' digests.
  - `the_committed_scenario_fits_its_bound` (fast): at most 65,536 bytes; `schema_version = 8`.
  - `a_scenario_over_its_bound_is_refused`: `render` of a hand `Written` on a template padded past 65,536 bytes gives
    `scenario_size`.
  - `the_committed_scenario_is_what_the_builder_writes` (slow): build into `tmp_path`, equal bytes of both files.
  - `the_balances_as_written_close_within_one_percent` (slow, from the build): each of the four.
  - `every_observed_job_is_needed_as_written` (slow): for each trade, the hours its written recipe needs for what
    the opening's buyers take (recipes' inputs at census hours, households' bought units of Task 11, exports, the
    machines due, public provision's need) within 1% of its census hours; retail hours through the blocks within 1%.
- [ ] **Step 2: Run them and see them fail. Step 3: Implement.**
- [ ] **Step 4: Build twice** into two folders made with `mktemp -d -p /media/user/dev-ssd`, `cmp` both files, then
  build into the repository and commit nothing yet. Hand over the metadata's head figures, each beside the
  prototype's for size only.
- [ ] **Step 5: Run the tests** (the slow ones once, in the background, with a log and an end marker) **and the
  gate,** `mise run check:hygiene`, **commit** the builder, the template, the scenario and its metadata with the
  subject above.

What the player would see: the numbers of the rebuilt country, on the bench first.

### Task 14a: The fixture retired onto the rebuilt scenario

Commit `test(economy): open the rebuilt scenario where the twelve-trade fixture was`.

**Depends on Part II.** This task opens the scenario that Task 13 writes, `content/scenarios/national-rebuilt/
defines.toml`, with the keys Tasks 1, 3 and 4 admit, the residences' row and the luxury scales among them.

**Files:**
- Modify (tests): every file that includes `tests/fixtures/national_twelve_trades.defines.toml` (`rg -l
  national_twelve_trades.defines rust/crates`) includes `content/scenarios/national-rebuilt/defines.toml` instead:
  `include_bytes!("../../../../content/...")` from `tests/*.rs`, `include_bytes!("../../../../../content/...")` from
  `tests/support/*.rs`
- Delete: `rust/crates/babylon-persistence/tests/fixtures/national_twelve_trades.defines.toml`
- Modify: `tests/support/opening_census.rs` (the check reads the rebuilt scenario);
  `rust/crates/babylon-persistence/src/national_economy/policy/admission.rs` (the price scale's refusal)
- Test: `tests/national_game_policy.rs`, `tests/national_twelve_trades.rs`, `tests/national_opening_census.rs`

**Decisions:**
1. **The fixture retired.** Its tests now open the rebuilt scenario. A pin that does not follow numbers (sources,
   cohorts, pay, wages, bands, allocation counts, places, census) must keep its value; a pin that follows numbers
   (recipes, prices, planned batches, cash, stock, rows that follow wants or the fund) is re-pinned from the first
   failing run, and the hand-over lists each with its old and new value. No code of `src/` changes but decision 3's.
   The committed records of stage 2's Tasks 8b and 10b stay as records of their commit; their heads already name it.
2. **The census check** now reads the rebuilt scenario and must still equal the committed census:
   `the_census_does_not_follow_the_numbers` (Review Focus 1).
3. **Prices abroad follow wages.** Under schema 8 every `price_scale_bps` must be 10,000 (`Profile(<region>)`): a
   foreign workplace's prices follow its own wage by O5 (Task 14b), and a scale on top would count the cut twice. The
   rebuilt scenario writes 10,000 everywhere; the fixture, which did not, is gone.

- [ ] **Step 1: Write the failing tests:**
  - `the_census_does_not_follow_the_numbers` (decision 2).
  - `a_price_scale_is_refused_under_schema_8` (`national_game_policy.rs`): the rebuilt scenario with Mexico's
    `price_scale_bps = 4000` gives `Err(Profile("<Mexico's key>"))`; the shipped file's scales still parse.
- [ ] **Step 2: Run them and see them fail. Step 3: Implement** decisions 1 to 3; re-pin as decision 1 says.
- [ ] **Step 4: Run** `binary(national_twelve_trades)`, `binary(national_opening_census)`,
  `binary(national_game_policy)`, `binary(national_opening)`, `binary(shipped_world_bytes)`,
  `binary(national_household_units)`, the crate.
- [ ] **Step 5: Gate and commit** with the subject above.

What the player would see: nothing; the tests open the numbers the player will start from.

### Task 14b: Prices that follow each workplace's wage, and the refusal of a product under cost

Commit `feat(economy): open each workplace at its own cost, and refuse a product under cost`.

**Files:**
- Modify: `rust/crates/babylon-persistence/src/national_economy/opening/{markets.rs, financial.rs, build.rs,
  equipment.rs}` (every read of a price: offers, retail stock, opening stock, grants, carrying value);
  `national_economy/grain/build.rs` (`source_stocks`, about L896-960 at `0a0cba1dd`, the inputs' cost at prices that
  sets a coarsened site's opening cash, and the carrying value it writes); `opening/build.rs` (two variants:
  `NationalOpeningError::UnderCost(EconomicFunction)` and `NationalOpeningError::Price(EconomicFunction)`)
- Test: `tests/national_twelve_trades.rs`; crate tests of `markets.rs`

**Interfaces:**

```rust
/// A workplace's opening price (O5, schema 8): the national price plus its labor part at its own wage:
/// p + floor((w_site - w_nation) x L x (10_000 + margin_bps) / (10_000 x n)), L and n the recipe's batch; the floor
/// is toward negative infinity (`div_euclid`) when the site's wage is below the nation's.
/// # Errors
/// `Price(trade)` for a result not above 0; `Arithmetic` on overflow.
pub(super) fn own_price(trade: EconomicFunction, national: Currency, site_wage: Currency, national_wage: Currency,
    recipe: &GameRecipe) -> Result<Currency>;
/// The opening's national wage of a trade: floor(census payroll / (census employee persons x 160)), summed over its
/// domestic sites.
pub(super) fn opening_national_wage(builder: &Builder<'_>, trade: EconomicFunction) -> Result<Currency>;
/// O5's refusal: national price x n >= L x national wage + sum(inputs x national prices) + wear per batch.
pub(super) fn refuse_under_cost(builder: &Builder<'_>) -> Result<()>;
```

**Decisions:**
1. Under schema 8 every workplace's offer, and every figure that reads its price (the retail charge's base, opening
   stock's cost, `source_stocks` and opening cash, a provider's fee, equipment's carrying value), uses `own_price`,
   its minimum, maximum and step moved by the same ratio as the scenario's own (rounded down, each at least 1 micro).
   Foreign and dependency workplaces too (their wage is a fraction of the country's; no price scale, Task 14a).
   `own_price` is for the site that makes a product. A shop makes none: its posted price of a good is the good's
   national price plus its own charge at its own wage (Task 3, decision 4).
2. **One national wage.** `opening_national_wage` is the census's `payroll_micros_per_period / (employee_persons x
   work_hours_per_person)` of the trade, rounded down: the figure the builder uses (Task 10, decision 1). Task 8's
   `national_wage_micros` (`pay.national_wage(f)`) is for reading only.
3. **The refusal** (O5): for every private trade with a recipe, at the national wage and national prices, with wear
   per batch the machine price over `service_batches_per_unit` of its trade's definition. Public provision is left out
   (its fee is not its cost). Distribution has no recipe and is not checked; its charge is labor only (Task 3,
   decision 4). Part II gives the shop no inputs and no margin (R3: its charge is labor only, Task 10
   decision 1), so distribution is not checked.

- [ ] **Step 1: Write the failing tests:**
  - `own_price_follows_the_wage` (crate): national $5.00, recipe 16 hours for 100 units, margin 1,400 bps, site wage
    $40, nation $30: `5_000_000 + floor(10_000_000 x 16 x 11_400 / 1_000_000)` = 6,824,000.
  - `a_price_not_above_zero_is_refused` (crate): national $5.00, the same recipe, site wage $0, nation $40:
    `5_000_000 - 7_296_000` is below 0, so `Err(Price(trade))` with the trade passed in.
  - `a_product_under_cost_is_refused`: the rebuilt scenario with food's price set to 1 micro gives
    `Err(UnderCost(Food))`; the rebuilt scenario as written compiles.
  - `wayne_services_cost_more_where_pay_is_higher`: a Wayne household services site's price over the national price
    equals its labor part at Wayne's wage (recomputed in the test).
  - `the_census_does_not_follow_the_numbers` still passes.
  - Every pin that follows prices is re-pinned from the first failing run and listed with its old and new value.
- [ ] **Step 2: Run them and see them fail. Step 3: Implement. Step 4: Run** `binary(national_twelve_trades)`,
  `binary(national_opening_census)`, `binary(national_game_policy)`, `binary(national_opening)`,
  `binary(shipped_world_bytes)`, `binary(national_household_units)`, the grain's tests, the crate.
- [ ] **Step 5: Gate and commit** with the subject above.

What the player would see: services that cost more in Wayne than where pay is lower, and foreign goods cheaper than
the country's.

### Task 15: The opening's own report, before any period

Commit `test(persistence): the rebuilt opening's report before any period`.

**Files:**
- Create: `rust/crates/babylon-persistence/tests/national_rebuilt_opening.rs`, `tests/support/opening_ledger.rs`;
  `reports/country-opening-v13/opening-report.json` (written by an ignored recorder)

**Interfaces:**

```rust
/// The opening's flows a period at posted prices and planned batches, read from the compiled opening only.
pub struct OpeningLedger {
    pub trades: BTreeMap<EconomicFunction, TradeLedger>,   // workers' hours, needed hours, revenue, costs, wear, OI
    pub accounts: Vec<AccountLedger>,                      // income parts, tier costs, standard
    pub bodies: Vec<BodyLedger>,                           // receipts against payments, per body and the fund
    pub abroad: AbroadLedger,                              // sales and purchases by region and product
}
pub fn opening_ledger(opening: &EconomicOpening, policy: &NationalGamePolicy) -> Result<OpeningLedger, LedgerError>;
```

**Decisions:**
1. **Needed hours** of a trade: what the opening's buyers take of its product a period (each account's needs, and of
   its wants what its money reaches at its sellers' posted prices, tier by tier and, inside a tier, in the scenario's
   order of paying, each row whole until the money ends, as the engine buys (ADR313's amendment of ADR312 P7); every
   recipe's inputs at planned batches; foreign buyers' rows to domestic suppliers; equipment replacement due, public
   providers' included; public provision's need) over output a batch, times its batch hours. Retail: handling hours of
   every shop good households take, through the blocks. The builder sizes the tiers by the tier solve on the 187 pooled
   places' accounts at national
   posted prices (Task 11), where the national accounts close. So needed hours are counted twice: with every account
   buying at the national posted prices (asserted), and with every account buying at its own sellers' posted prices,
   as the engine buys (reported, with each state's use of each service against its own providers' capacity; For the
   Director, item 5).
2. **Revenue** of a site: planned output times its own price. **Costs:** payroll, inputs at planned batches at their
   suppliers' prices, wear (machines' service used a period at their price over their life). **Operating income:**
   revenue less costs. **Tax:** rates of its rows. **Payout:** operating income less tax, at 100%.
3. **An account's income:** its wages less wage tax, support, programs' dues, payouts by its shares. **Its tier
   costs** at its sellers' posted prices; its standard as `household_standard` would read it at those figures.
4. **Public bodies.** The nation's balance counts the domestic places' bodies and the fund. Each foreign region's and
   the dependency's own bodies (their households and sites pay tax to their own domain, `financial.rs:42-69`) are
   reported beside it, receipts against payments, and not asserted.
5. **Money.** The opening's money is the sum of every account's opening cash: households, sites, public bodies, the
   fund, organizations. It must equal the catalog's own sum of opening cash, and one period of the ledger's flows
   moves money only between accounts.
6. No figure is averaged; every share is two sums divided, in basis points.

- [ ] **Step 1: Write the tests** (each fails until the ledger exists):
  - `every_trade_needs_its_workers`: for each trade, needed hours at the national posted prices within one batch a
    site or 1% of its workers' hours, whichever is larger; retail within 1%. The report also gives needed hours at
    the sellers' own posted prices against workers' hours by trade, by trade and place, and by service and state
    (capacity, use, and the shares idle and unserved); none of those is asserted.
  - `every_workplace_is_asked_for_its_work` (design 8.2: "jobs needed against jobs present, by trade and place"):
    for each domestic workplace with persons at work, what the opening's buyers ask of it a period (its dealt
    accounts' needs and reached wants, its dealt sites' inputs, its home caps, machines due) over what it can make.
    Asserted: for each trade, the persons at work at workplaces asked for under half of what they can make are
    under 25% of the trade's (as the compiler deals today they are 32% to 66%; this plan's rule, run outside the
    engine on the fixture with what is asked scaled to what can be made, leaves 1% to 10%). Reported: the same
    share by trade for under half and for over twice, and every shared freight pool whose opening use passes its
    room (O15). A figure that fails is reported and not loosened.
  - `every_workplace_can_pay_for_its_first_period` (Task 7a's test, on the rebuilt scenario): for every domestic
    workplace with a service-input row, opening cash less its payroll less the row's cash floor is at least what its
    service inputs of one period cost at their providers' opening prices. Here the prices follow each provider's
    own wage (Task 14b), so a workplace whose provider is dear is the one to fail: a failure is reported with the
    workplace, its cash, payroll, floor and cost, and nothing is loosened.
  - `every_private_price_covers_its_cost_at_the_national_wage`: national price x n at least labor, inputs and wear.
  - `no_account_opens_going_without`: every domestic account's income reaches its tier 1; pin the count of accounts
    at each standard and each band's income per person (from the first failing run).
  - `the_four_balances_close_within_one_percent`: households' tier money against income; public receipts against
    payments (nation and fund); exports against imports; profit kept against equipment: each residual at most 100 bps
    of its flow.
  - `each_place_s_body_is_reported`: every domestic place's body appears once in the report with its receipts and its
    payments a period; the lowest and highest ratio of receipts to payments are printed. Nothing about a place is
    asserted (For the Director, item 1).
  - `the_opening_conserves_money` (decision 5): the sum of opening cash over every account equals the catalog's sum,
    and the ledger's flows of one period sum to 0 over all accounts.
  - `sellers_under_their_own_cost_are_reported`: every site whose own price is under its own cost (labor at its own
    wage, inputs at its suppliers' prices, wear) is written into the report with its trade, place and gap; the count
    is printed, nothing asserted (design 8.2).
  - `tier_money_is_within_one_percent_of_its_sizes`.
  - The shipped world's pins: `binary(shipped_world_bytes)` in the gate.
- [ ] **Step 2: Run them.** A test that fails on a figure is reported with the figure, never loosened: the lead
  decides whether the builder or the compiler is wrong.
- [ ] **Step 3: Record** `opening-report.json` with the ignored `record_rebuilt_opening_report`: the ledger's sums by
  trade, by trade and place, band, body (each domestic place's body, the fund, each foreign region's and the
  dependency's) and region, and the sellers under their own cost (design 8.2), under 1,048,576 bytes.
- [ ] **Step 4: Gate,** `mise run check:hygiene`, **commit** with the subject above and the report.

What the player would see: nothing directly; it is the record that the opening the player starts from is in balance.

### Task 16: The bench opens the rebuilt scenario

Commit `test(persistence): the country bench opens the rebuilt opening`. Test code only.

**Files:**
- Modify: `rust/crates/babylon-persistence/tests/national_household_units.rs`, `tests/support/{country_bench.rs,
  country_rules.rs, country_sizes.rs, economy_health.rs, country_fund.rs}`
- Create (by recorders): `reports/country-opening-v13/rebuilt-sizes.json`, `rebuilt-timings.json`

**Decisions:**
1. **Which scenario** (stage 2's Task 8b, decision 1, extended): the bench names the shipped scenario, the twelve
   trades' scenario of Task 8b, or the rebuilt one (`national_catalog_input_for(include_bytes!(...))` of
   `content/scenarios/national-rebuilt/defines.toml`: `"../../../../content/..."` from `tests/*.rs`,
   `"../../../../../content/..."` from `tests/support/*.rs`). After Task 14a the twelve trades' scenario is the rebuilt
   one; Task 8b's name for it stays as an alias, so its recorders still run.
2. **The scenario's own policy.** For the rebuilt scenario the market policy is the opening's own
   (`opening.market_clearing`: its order of paying and its wants), with a set's `plans_from_spare_money` and rules
   added; the bench's `PAYING_ORDER` is not used. Its fund and programs are the opening's own: the bench applies no
   `country_fund::with_fund` to an opening that holds programs (Task 4, decision 10). So the sets are: `as-ships` (the
   scenario as compiled, no rule, no spare money), `no-seekers` (stage 2's set ii), `all-six` (set iii); each of them
   has the scenario's benefits. A run finishes as the bench already does, with `finish_with_staffing` without seekers
   and `finish_with_place_staffing` with them (`country_bench.rs:873`, `:924`); no change is made there.
3. **Sizes first:** `the_rebuilt_sizes` counts what `the_twelve_trades_sizes` counts, with the want rows, the tax rows
   and the programs' recipients, filled from the first failing run; the seekers' members against `SEEKER_BOUND`
   (131,072). If they do not fit, stop and report.
4. **One timed period of each set,** with the records of period 1's full routes (O15's airports) and every price that
   moved by more than 1% and every class of cash that moved by more than 1% (the spike's last test, recorded, not
   asserted).
5. **The price rule's columns.** The records carry the health record's market columns as `economy_health.rs` writes
   them (about L1380-1408 in the copy: short markets, demand at the quote, sold, and the row with the highest clearing
   price, its quote and its place), which is the price rule's Task 8 decision 4; this plan adds none. That rule's
   decision 3 (the shipped file takes the order of paying) and its test `the_shipped_world_clears_by_price` wait for
   the later plan that makes the rebuilt scenario the shipped one: the shipped file keeps every byte here.

- [ ] **Step 1: Write** `the_rebuilt_sizes` with empty literals and `the_rebuilt_opening_closes_one_period` (each set
  closes period 1 with money, persons and the labor force checked by the bench).
- [ ] **Step 2: Run them and see them fail;** fill the sizes; check the seekers' fit.
- [ ] **Step 3: Implement** decisions 1, 2, 4 and 5.
- [ ] **Step 4: Record** the timings and the full routes. A refusal of the engine is written down with its period,
  stage and words, and reported; nothing is changed to get past it.
- [ ] **Step 5: Gate,** `mise run check:hygiene`, **commit** with the subject above and the records.

What the player would see: nothing directly; the bench is the record.

### Task 17: Thirty-four periods of each set

Commit `test(persistence): the rebuilt opening's records of 34 periods`. Test code and records only.

**Decisions:**
1. `record_rebuilt_sets` runs 34 periods of `as-ships`, `no-seekers` and `all-six`, each into
   `reports/country-opening-v13/rebuilt-<set>.json` with the bench's columns, the `acted` lists and the head of Task 8
   of the bench's plan (what is left out of the game's turn, the scenario's digest, the numbers' metadata digest).
2. A refusal is written into its record (period, error, the full row before it) and reported, never worked around.
3. A record over 1,048,576 bytes is written whole to the build's temporary folder and its rows of periods 1, 2, 3, 4,
   5, 13 and 34 are committed as `rebuilt-<set>-summary.json` (stage 2's Task 8b, decision 7).
4. No conclusion is written. The hand-over gives: each record's size, each refusal, each set's `acted`, and the first
   and last row of jobs, food unmet and the fund's paid over due.

- [ ] **Step 1: Write** the recorder. **Step 2: Run** each set in the background, one log each, outside the
  repository. **Step 3: Gate,** `mise run check:hygiene`, **commit** with the subject above and the records.

### Task 18: Four hundred periods

Commit `test(persistence): the rebuilt opening's runs of 400 periods`. Test code and summaries only.

**Decisions:**
1. `record_rebuilt_long` runs 400 periods of `as-ships` and of `all-six` (the scenario's benefits are in both), with
   `write_compact_unbounded` into the build's temporary folder for the whole record and the summary (rows of periods
   1, 2, 3, 4, 5, 13, 34, 100, 200 and 400, head, `acted`, total time) committed as `long-rebuilt-<set>-summary.json`.
2. As Task 17: refusals written, no conclusion, logs never committed.

- [ ] **Step 1: Write** the recorder. **Step 2: Run** both in the background, one log each. **Step 3: Gate,** `mise
  run check:hygiene`, **commit** with the subject above and the summaries. Hand over to the lead with the total times.

The lead then reads the records, runs `mise run rust:check-no-docs` and `mise run check`, and writes
`reports/country-opening-v13/README.md`.

## What the prototype found (25 November)

The one check of the first draft found that the builder's model, the spike of 20 November, ignored rules the game
really has. A third prototype then solved the numbers under those rules, and the lead ran further variants on its
model. Both are outside the repository; the lead keeps them (`builder-spike-3/README.md`, `model-spec.md`,
`variants.md`, `more/variants-lead.md`). It is a model outside the game, on the committed 2024 tables: the pay table's
148.9 million jobs, counties and states, not the game's 187 pooled places; floats, not exact fractions. Money is in
thousand millions of dollars a 28-day period.

**The rules it holds** (each read in the code): R1, a service may buy a service of an earlier stage only, and the
engine has two stages, utility and all the rest (`policy/admission.rs` `validate_recipe`; ADR264). R2, only the five
storable goods with a price cross a border (`opening/markets.rs` `service_provider`). R3, the shop charges labor only.
R4, a household buys tier by tier, and inside a tier in the order of paying, each row whole until its money ends. By
rule O4 a buyer the game lacks is spread over the buyers it has.

**What it found.**

- On national bands the opening solves under every rule: a margin factor of 0.116, profit at 16.1% of wages, the four
  balances closed, the wear-floor loop settled in three rounds, and tier contents that make what bands buy under R4
  equal what households must buy (nine unknowns, residual 4e-12).
- R1 moves 549.6 a period (business services 313.3, premises 178.3, leisure 36.6, household services 21.4). The public
  grant falls from 167.3 to 71.7 and the one tax rate from 23.7% to 13.9%; business services become 27.9% of what
  households buy (15.6% without R1); goods cost 19% to 36% more.
- R2 moves 71.2 and raises the export factor from 1.15 to 2.73: 75.4% of equipment output and 40.4% of materials are
  exported.
- Contents solved for proportion but bought by the order of paying miss demand by food +29%, materials +31%,
  consumer goods +46%, leisure -37%, business services -21%. So the builder must solve with R4.
- On county accounts no margin factor closes "households spend what they receive": the better-paid bands of the
  richest counties keep money from wages alone. With the rule that an account above its three tiers has its luxury
  rows scaled so that it spends all (design call 4), nothing is kept at any factor, and the factor is set on the
  national bands: 236 accounts scaled, median 1.25 times.

**The cures, measured.**

| | As the rules stand | Regrouped, no engine change | That, and the border | One more engine stage, and the border |
|---|--:|--:|--:|--:|
| First stage | utility | utility, business services, housing | the same | utility, business services |
| Later stages | all other services | the other services | the same | housing; then the others |
| Business services cross a border | no | no | yes | yes |
| Still spread under R1 | 549.6 | 260.2 | 260.2 | 145.3 |
| One tax rate | 13.9% | 22.3% | 22.0% | 22.2% |
| Public grant | 71.7 | 154.7 | 150.8 | 152.3 |
| The fund's share | 47.9% | 26.2% | 27.1% | 27.1% |
| Export factor | 2.73 | 2.73 | 1.38 | 1.49 |
| Equipment output exported | 75.4% | 75.3% | 38.2% | 41.1% |
| Housing in the basket | 11.4% | 7.5% | 7.7% | 11.5% |
| Housing's price over the model with no rules | 0.70 | 0.69 | 0.71 | 1.06 |
| Tiers solve under R4 | yes | to 1.4e-2 only | yes | yes |

- **A regrouping needs no engine change.** The compiler already admits any service as first-stage (`kind = "utility"`)
  or second-stage (`kind = "service"`), and asks only that first-stage services stand before the others in the order
  of paying. With business services and housing in the first stage, care, schools, leisure and public provision can
  buy their offices and premises. What stays bent is housing, which cannot buy business services of its own stage.
- **One more stage is as good as two.** Utility and business services, then housing, then the rest, equals the
  four-stage form to the digit.
- **The comforts' make-up follows the order of paying;** the basket's shares do not.
- **Places, with the regrouping and the border.** One person's tier-1 needs in a household with no earner cost $1,066
  at national prices; by county $846 at the fifth percentile, $1,019 at the median, $1,108 in Wayne and $1,691 in the
  dearest; by state the dearest is $1,418. The fund pays 692 a year at each place's own cost, 719 at one figure at
  national prices (then 36% of such households, in 234 counties, open short, by 6.7% on average), and 959 to 1,138 at
  the dearest place's figure. Under one national share of the taxes, 1,867 of 3,142 counties' public bodies collect
  less than they pay, 1,237 even keeping all their own taxes, and 682 run through a reserve of two periods in under
  four; by state 27 of 51, and 9.
- **Not done by the prototype:** the foreign regions' mix of jobs (O11), exact fractions, whole units, the 187 places,
  and whether the tier solution is unique.

**Places (counted by the lead on the prototype on 26 November, while checking Part II).** The prototype solved the
tiers with every account buying at national prices, and it balanced the nation, not the states.

- **Each place's own prices (O5).** Bought at each state's prices, the same tier contents take 1.7% more food and
  materials, 2.0% more consumer goods and 2.4% more business services than households must buy, and 0.7% less
  household services; at each county's prices up to 13.4% more (49 a period of 860). Solving the contents again at
  local prices does not close it: the best fit leaves every product over-bought, from two starts alike. Money is
  earned at prices weighted by where things are made and spent at prices weighted by where people live, and one tier
  list for the whole country cannot make the two agree.
- **A service is sold only inside its own state.** By state, what its own buyers take of a service against what its
  own providers can make, households at state prices:

  | | Idle, in states with too little demand | Wanted where it cannot be had | Lowest and highest state (use over capacity) |
  |---|--:|--:|---|
  | Utility | 16.6% | 16.7% | Louisiana 0.34; Michigan 2.26 |
  | Leisure | 12.4% | 12.7% | Nevada 0.32, Hawaii 0.36; Massachusetts 1.79 |
  | Business services | 7.4% | 9.2% | District of Columbia 0.31, New York 0.62; Wyoming 2.08 |
  | Housing | 8.2% | 8.1% | Utah 0.61; Mississippi 1.45 |
  | Household services | 6.4% | 5.7% | District of Columbia 0.46, New York 0.71; Nevada 1.24 |
  | The shop's hours | 2.2% | 4.0% | North Dakota 0.78; District of Columbia 2.08 |

  Firms take 41% of utility and 26% of business services. Michigan's own buyers want 2.26 times the utility that
  Michigan's utility workers can make.
- So Part II solves at national prices, sets the benefit and the luxury scales at each account's own prices, and
  counts both effects for the game's own people (Task 11, decision 12). Whether a service may be sold across state
  lines is For the Director, item 5.

## What the compiled opening showed (26 November)

Counted by the lead from the compiled opening of the twelve trades at `9753016ea` (every figure a sum over the
opening's own rows: workplaces, staffing, purchase rows, service inputs, restocking rows), while checking this plan.
The shipped opening gives the same shares.

- **A buyer has one seller of each product, and a place has several.** The compiler gives every buyer at one
  location the largest workplace of the trade at the nearest location (Task 7b's "Why" names the code), and the
  engine holds one seller a household and good and one provider a business and service. A place has a median of 9
  sellers of household services, 7 of business services, 6 of public provision, 5 of leisure, 4 of utility and of
  premises.
- **So most workplaces have no buyer, whatever the numbers.** Domestic workers at workplaces that no purchase row,
  service input or restocking row names:

  | Trade | Workplaces | With no buyer | Workers | At workplaces with no buyer | Share |
  |---|--:|--:|--:|--:|--:|
  | Household services | 1,495 | 1,308 | 55,463,744 | 35,661,169 | 64.3% |
  | Public provision | 959 | 772 | 9,309,178 | 5,808,745 | 62.4% |
  | Utility | 636 | 454 | 984,732 | 482,900 | 49.0% |
  | Food | 370 | 185 | 3,286,458 | 1,088,197 | 33.1% |
  | Premises | 728 | 542 | 9,721,849 | 3,095,193 | 31.8% |
  | Extraction | 342 | 167 | 638,542 | 193,914 | 30.4% |
  | Business services | 1,057 | 871 | 26,744,137 | 7,160,833 | 26.8% |
  | Shops | 991 | 676 | 28,678,765 | 1,727,512 | 6.0% |
  | Materials | 340 | 37 | 5,010,596 | 3,396 | 0.1% |

  Together 55.2 of 139.8 million, 39.5%. Consumer goods and leisure have no buyer in the fixture at all (wants come
  with Task 3), and the buyers of machines were not in the count.
- **Period 2's layoffs follow it.** In the bench's record of the twelve trades with no rule, the people laid off in
  period 2 sit close to the workers at workplaces with no buyer, trade by trade: household services 35.9 against
  35.7 million, public provision 7.3 against 5.8, food 1.2 against 1.1, utility 0.6 against 0.5, and all of
  leisure, consumer goods and machines (16.4, 2.1 and 3.0, which have no buyer in the fixture). Where far more are
  laid off than that (shops 25.8 against 1.7, business services 19.2 against 7.2, premises 8.9 against 3.1), the
  fixture's own numbers do the rest. In all, 76.7 of the 122.5 million laid off could be workers of workplaces
  with no buyer. The record does not name the workplaces, so this is a match of counts, not a trace of persons.
- **What it costs, with the numbers taken out.** For each product, what buyers ask was scaled until the nation's
  buyers ask for exactly what the nation's makers can make, which is what the rebuilt numbers do. A seller sells at
  most what it can make. Share of what the nation's makers can make that can then be sold:

  | Product | As dealt today | By Task 7b's rule (whole buyers) | If every buyer shared the sellers of its place | of its state |
  |---|--:|--:|--:|--:|
  | Household services | 35.7% | 91.9% | 95.0% | 95.5% |
  | Public provision | 36.2% | 86.5% | 87.1% | 90.3% |
  | Premises | 65.6% | 89.3% | 90.1% | 93.1% |
  | Utility | 48.5% | 86.2% | 83.8% | 87.5% |
  | Business services | 57.8% | 82.4% | 74.5% | 84.9% |
  | Food | 56.8% | | | |
  | Materials | 63.3% | | | |
  | Resources | 40.0% | | | |

  The first three are bought in the buyer's own place and the next two anywhere in its state (Task 7b). So dealing
  whole buyers in proportion loses one to three points against sharing, and leaves under 1% of a service's workers
  at providers with no buyer, with no change in the engine. What is left is where things are made against where
  they are bought: Part II's count of each state's services (For the Director, item 5).
- **The sellers that have buyers cannot pay for their first period.** A company takes a tenth of its workplaces'
  cash above one payroll at the opening, and a workplace may buy its service input only with cash above one payroll
  once the period's wages are set aside. 644 workplaces cannot: 315 of business services with 98.5% of the trade's
  workers, 315 of household services with 50.7%, 14 of extraction. They are the largest, so they are the sellers
  the buyers are given: all 186 sellers of business services that have a buyer and 153 of the 187 of household
  services. The Director ruled this sweep out on 20 November and it was measured then; the plan's drafts kept the
  fixture's key by oversight (Task 7a; Task 13 writes 0).
- **Abroad, one maker serves every buyer.** Each buyer abroad takes its share from the country at one maker: the 35
  buyers abroad of food at one in Kern County, California, the 214 of materials at one in Dane County, Wisconsin,
  the 36 of resources at one in Hidalgo County, Texas (Task 7d deals them over the country's makers).
- **A workplace's wage differs inside a place.** Among the sites of one trade at one location the highest wage over
  the lowest has a median of 2.0 for household services and 1.6 for shops (parts and owners differ). By O5 their
  prices differ too. So which account is dealt to which seller decides what it pays (For the Director, item 7).
- **The approved design names it.** "A buyer is bound to one named seller. A second seller of the same product
  would get no buyers" (how the economy adjusts, 21 November, "Today"), and its rule A4: "No buyer is bound to one
  seller ... equal prices share buyers in proportion ... a market is one product in one place, with all its
  sellers." A4 was prototyped once, held, and is not among the six rules; every measured small world has one seller
  a product a place.

## For the Director

Seven choices. Four change what the builder computes, one changes who may sell a service to whom, one who gets
what the shop saves abroad, and one whether a buyer may have several sellers of one product. For each: what the approved
text says, what this plan builds until a ruling, and the
variants (written out under "Variants that wait for the Director", so that a ruling is a small edit). The lead's
recommendation is given last and is NOT built until ruled.

1. **How services are grouped into stages.**
   *The approved text.* Design O10: "A trade's recipe carries the premises and the business services that, in the
   accounts, it buys as investment." O4: "What a trade sells in reality to a buyer the game does not have is spread
   over the buyers it does have." ADR264: a service's recipe may name only services of an earlier stage.
   *What this plan builds.* The rules as they stand: utility first, every other service second, and by O4 the builder
   spreads the 549.6 a period that service trades cannot buy.
   *Variants.* V6, a regrouping with no engine change; V7, one more engine stage. The lead recommends V6.
2. **Whether business services cross a border.**
   *The approved text.* Design O11: "Each product has its own share bought abroad and its own volume sold abroad, from
   the accounts." Call 8: "Trade is balanced in money at the opening."
   *What this plan builds.* Only the five goods cross, as the compiler has it; the builder spreads services' exports at
   home and raises goods exports until trade balances (an export factor of 2.7).
   *Variant.* V8, business services cross. The lead recommends it.
3. **The benefit and local prices.**
   *The approved text.* Design O12: "enough, at the opening's prices, for the needs of tier 1"; "Each kind of benefit
   is a named row of the scenario, with its own rate and its own people". Stage 4's plan B, item 4: "at the opening's
   tier-1 price of a person's needs".
   *What this plan builds.* One rate for the `no_earner` row, enough at the opening's prices everywhere: the dearest
   place's cost. Task 15's `no_account_opens_going_without` asserts that every domestic account reaches its tier 1.
   *Variants.* V3, each place its own cost; V4, one figure at the average. The lead recommends V3.
4. **Each place's public body at the opening.**
   *The approved text.* Design O13, last sentence: "The builder sets the two tax rates and the fund's share of each."
   ADR313 O12: "one national fund that takes a share of both taxes everywhere." Design call 10, of benefits: "If each
   place paid its own, poor places would cut from the first period and rich ones would hoard."
   *What this plan builds.* One national rate on each base and one fund share of each tax, the same in every place
   (Tasks 1 and 4). Task 15 writes each place's receipts against its payments into the report and asserts only the
   nation's and the fund's balance.
   *Variants.* V1, every place opens even; V2, a grant from the fund to the providers of places whose own taxes are too
   few. The lead recommends V1 with V2's road (b) for those places.
5. **Whether a service may be sold across state lines inside the country.**
   *The approved text.* None rules it. The compiler gives each buyer one provider in its own state (`service_reach =
   "same_state_or_own_counterpart"`, its one admitted value; the Wayne map design of 3 November calls it "the
   existing same-state service rule"). ADR264: a connection "authorizes service reach without asserting a geographic
   path", and the engine does not forbid a provider in another state.
   *What this plan builds.* The rule as it stands. The builder solves the national accounts and counts, for the
   game's own people, each state's use of each service against what its own providers can make (Task 11, decision
   12); Task 15 reports the same from the compiled opening. In the prototype a sixth of utility work, an eighth of
   leisure work and 6 to 9% of the other services sit in states that cannot use them, while as much is wanted in
   states that cannot get it; firms take two fifths of utility.
   *Variant.* V9, utility, leisure and business services are sold across the whole country, each buyer's demand
   shared over providers by what they can make; housing and household services stay in their state. The lead
   recommends V9.
6. **Who gets what the shop saves on goods from abroad.**
   *The approved text.* O5: "A workplace's own opening price follows its own wage", so a foreign seller's goods cost
   less than the country's. O9 and the ruling of 25 November: "the shop as it is", which charges labor only; today
   it posts a good at the national price plus its charge, whatever it paid.
   *What this plan builds.* The shop as it posts today: it buys an imported good below the national price, sells it
   at the national price plus its charge, and the difference is the shop's operating income, taxed and paid out to
   its owners (Task 10, decision 7).
   *Variant.* V10, the shop posts each good at what it pays for it plus its charge, so households buy goods from
   abroad cheaper and the shop has no such income. The lead recommends V10: it is "labor only" read strictly, and it
   puts the gain from cheap foreign labor in the price of what households in the country consume. A firm that buys
   its inputs abroad keeps its saving as profit under both.
7. **Several sellers of one product in one place.**
   *The approved text.* O4: "Every observed job is needed at the opening." Design 8.2: "jobs needed against jobs
   present, by trade and place". Rule A4 of how the economy adjusts (approved 21 November, held after its first
   measurement, not built): "No buyer is bound to one seller ... equal prices share buyers in proportion".
   *What this plan builds.* The compiler deals whole buyers to sellers in proportion to the sellers' people (Tasks
   7b to 7d), with no change in the engine: one seller a buyer and product stays. It is the lead's call, as the
   smallest mend that lets O4 hold for a workplace. Two things stay as they are: a household that loses its one
   seller of a thing loses all of it; and where sellers of one place pay different wages, which account is dealt
   the dearer seller is an accident of the dealing.
   *Variants.* V11, a buyer's custom is shared over its sellers in the engine, each seller a fixed share: every
   account of a place pays the place's blend and no account depends on one workplace. V12, rule A4 in full: the
   cheapest seller first. The lead recommends this plan's dealing now and V11 before homes are built; V12 only
   after it is measured again with the six rules.

## Calls for the lead to confirm

1. **The scenario's path and name:** `content/scenarios/national-rebuilt/defines.toml`, a directory of its own so no
   tool that reads `content/scenarios/national/` sees it (`tools/devtools/national_native_evidence.py` matches that
   directory's `defines.toml` by name). The later plan moves it over the shipped file.
2. **Stage 2's fixture** takes the new keys with placeholder values in Task 1 and is retired in Task 14a, before O5's
   refusal (Task 14b) would refuse its designed prices. Its tests move to the rebuilt scenario; pins that do not follow
   numbers keep their values; the others are re-pinned and listed. The other way, keeping both, means two shapes of
   schema 8.
3. **An engine task (2) for handling blocks.** Without it, retail hours must be whole hours a unit, and units large
   enough for that make tier contents round by several percent. Spare money buys whole blocks.
4. **A census table (8)** written by Rust and read by Python, committed and registered, proven independent of the
   numbers (Task 14a); `national_household_budget` becomes `pub` for it.
5. **The two tax rates: one rate on both bases,** wages and operating income. The shipped scenario has the two equal
   today (both 15%, `content/scenarios/national/defines.toml` `[financial]`). The other way: the spike found about 23%
   on both on its own fold; at today's 15% on operating income the wage tax must be about 24%, and with the wage tax
   at 15% no rate closes (the spike, section 3). It changes who pays.
6. **Method kept from the spike:** investment in structures and IP spread by operating surplus; the luxury tier's other
   goods equal to the comfort tier's; retail hours following value; four workers a machine in goods, forty elsewhere;
   a life of 100 periods; daily units for needs; every input kept; margins at least 1.25 times wear. Part II keeps
   each (Tasks 9, 10, 10b, 11).
7. **Prices abroad follow wages:** under schema 8 `price_scale_bps` must be 10,000 (Task 14a) and O5 sets foreign
   prices (Task 14b).
8. **A public provider's grant covers one period of its machines' wear** under schema 8 (Task 4, decision 8), so that
   public provision replaces its machines as a private workplace does from its margin; under schema 7 the grant is
   today's. Part II then counts public provision's machines in the wear and in the equipment bought.
9. **Machines of every age:** at most `min(8, floor(65,536 / processes))` cohorts a process, ages spread over the life
   (Task 6, decision 3).
10. **Equipment abroad** by whole processes chosen by a hash, up to the share (Task 5): the engine admits one
    investment supplier a process.
11. **Run B's order:** Task 6 before Task 5, since Task 5 counts the machines Task 6 sets.
12. **Retail stock on every want in full** (Task 3, decision 3): the shop opens with stock above what bands whose money
    reaches only part of their tiers will buy.
13. **Airports** are not raised in this plan: Task 16 records period 1's full routes, and stage 6 raises them (O15's
    second half, "Airports are raised so that the opening's flows fit"; design section 10 item 5 does not list it).
14. **The organizer's designed figures** in food units (`[aid] initial_food_quantity = 1`, `maximum_quantity = 4`,
    `collection_initial_cash_micros = 280000000`) stay as the fixture has them; with daily units they mean a day's
    food. They are the organizer lane's to restate; the bench leaves aid empty.
15. **The household-time figure** `unmet_hours_per_unit` is rescaled to the new food unit (Task 13, decision 2): it
    is 1, `max(1, half_up(20 / 28))`, an hour for a day's food. A person's unmet period of food then costs 28 hours
    where today it costs 20, because food is counted in days and the key holds whole hours. Told to the Director.
16. **No `[builder]` section in the scenario:** the solved factors live in the metadata, since the compiler reads none
    of them (the spike's list of keys had one).
17. **One folder for this stage's records:** `reports/country-opening-v13/`, new; stage 2's stay in
    `reports/country-opening-2026-11/`.
18. **People in a collective residence follow O12's words at the opening** ("People in a collective residence who
    hold no job are paid the same"). The engine's `PerPerson` terms pay an account for every person of its cohort
    (`financial/programs.rs:43-54`). So a residence's account is paid an amount a person that is a resident's own
    tier-1 needs (no housing: a residence has no household-basis need) times the share of its residents with no job at
    the opening, rounded down. The account is also a recipient of `laid_off`, so a resident who loses a job in play is
    paid as any worker is (the engine allows one after-layoff program a household and any number of per-person ones,
    `financial/validation.rs`). It keeps what it was at the opening, as O12 says of households. With one benefit
    figure this is a program row for each place's residences (187 rows and the two others, within
    `MAX_PUBLIC_PROGRAMS`, 256). With each place's own cost (V3) it needs V3's road (b), an amount for each recipient.
    This replaces the first draft's item for the Director and its variant V5.
19. **The order of paying follows the stages:** a first-stage service stands before every second-stage service, as
    the compiler asks (`policy/admission.rs` `paying_order`), and the needs keep their order among themselves.
20. **An account above its three tiers has its luxury rows scaled so that it spends all** (design call 4), and the
    margin factor is set on the national bands. Part II builds it; the scale is a key of the scenario (Tasks 1 and 3),
    set at the account's own sellers' prices (Task 11, decision 10).
21. **Imports are paid at their sellers' own prices** (O5; Task 14b), not at national prices as in the prototype,
    and what a buyer saves is its operating income (Task 10, decisions 6 and 7). Who gets the shop's saving is For the
    Director, item 6.
22. **Import shares are written for coverage** (Task 10b, decision 8): only a buyer whose second supplier is foreign
    imports (`procure`), so the written share is the accounts' share over those buyers' weight.
23. **A foreign region's closure** (Task 12): its households' money a person is what makes its employed needed; its
    purchases from the country are one figure a region (it balances) times one a good (the regions together take the
    country's exports of each good).
24. **The tiers are solved at national prices; own prices are counted** (Task 11, decisions 2 and 12). No one tier
    list makes what accounts buy at their own sellers' prices equal what households must buy (What the prototype
    found, "Places"). The benefit and the luxury scales are set at each account's own prices.
25. **The dearest place** of the one benefit figure is the no-earner account whose own tier 1 costs most a person at
    its own sellers' prices (Task 11, decision 6); the census gives each place's sellers' wages (Task 8).
26. **Tests that build from the committed tables are marked slow** (Task 13, decision 8): the unit suite runs `-m
    'not slow'`, a fast test holds the committed scenario to its inputs' digests, and the lead runs the slow ones
    before a push that changes the builder.
27. **No Rust parse of the written scenario in Task 13** (run C is Python only): Task 14a opens it first thing.
28. **The plan's unit of accounts is the part, not the pooled place** (the header's "A place and its parts"): the
    census has a row a part, the luxury scales name a part, and a place's residences are paid by one row a hub (316
    rows would pass the engine's 256 programs).
29. **Buyers are dealt to sellers in proportion to the sellers' people** (Tasks 7b to 7d), by weights that read no
    recipe, price or want, so that the census of who sells to whom is the same whatever numbers the builder writes.
30. **Three services are bought in the buyer's own place:** premises (housing), household services and public
    provision, a key of the scenario (`place_services`). Utility, business services and leisure may come from
    anywhere in the buyer's state, the rule as it stands; item 5 asks whether those three may cross state lines.
31. **A company takes no working capital at the opening** (`opening_treasury_bps = 0` in the fixture from Task 7a
    and in the scenario): not the lead's call but the Director's ruling of 20 November, restored here.

## Settled by approved text

- **The fund at county 11001, opening with two periods of `no_earner`'s dues as new cash.** Stage 4's plan B, item 1:
  "a budget `CashInProportion` (cap 0, floor 0) and two periods of its payments as cash (O13)".
- **Programs by household key.** Stage 4's plan B, item 4: `no_earner` "to every account with no earner at the opening
  ... owner or not", `laid_off` "to every United States worker account of every band. Both rank 0."
- **Support for those looking for work at the opening.** Design call 16: "Those looking for work at the opening keep
  today's county support" (today a period of food; Task 4, decision 6 keeps it a period of the food need).
- **Foreign regions balanced one by one.** Design O11: "A foreign region's mix of jobs is computed, so that the region
  is in balance by construction."

## Variants that wait for the Director

Each variant is written as the edits it makes, task by task. None is built until the Director rules.

**V1. Every place opens even** (item 1).
- Task 1: `GameFundPolicy` gains `fund_share_by_place: BTreeMap<CountyGeoid, u16>`, TOML `[fund] fund_share_by_place =
  { "<hub geoid>" = <bps>, ... }`, the fund's share in that place, the same figure for both taxes. Refused: a key that
  is not a county geoid (`Location`), a value above 10,000 (`Profile`); under schema 7 the key (`Shape`).
- Task 4: decision 2's share is the place's `fund_share_by_place` value, by the hub county of the payer's financial
  domain; a domestic place missing from a non-empty table is `NationalOpeningError::Policy`. Tests:
  `a_place_share_table_sets_each_place` (two places' shares set in the test; their payers' rows use them) and
  `a_missing_place_is_refused` (`Err(Policy)`).
- Part II: `Settings.place_body = "even_where_own_taxes_reach"`. Task 11 (decision 11) computes the table,
  `place_fund_share_bps`: the value is `10_000 - floor(10_000 x payments / taxes)` of the place at the national rate,
  at least 0. A place whose payments exceed its taxes keeps all of them (fund 0) and opens short; the metadata lists
  each such place and its gap. Task 13 then writes the table in place of its refusal of the setting.
- Task 15: `every_public_body_opens_within_one_percent` asserts each place's receipts against its payments within 1%,
  but for the places the metadata lists, which are reported with their gap.
- Review Focus 5: expected, each place opens even but the listed ones.

**V2. A named grant to poorer places** (item 1). Every place sends one share, set so that the best-off place just
covers its own public services, and the fund pays every other place a grant, a named row.
- What the engine admits: **one public account may not pay another.** `validate_public`
  (`babylon-material-circuit/src/financial/validation.rs:157-176`) admits an allocation only as
  `HouseholdIncomeSupport` to a household, `ProviderOperatingGrant` to a site or `AgencyAppropriation` to an
  organization; a recipient `AccountId::Public` is `FinancialInvariant`. `PublicBudgetReceipt::validate`
  (`financial/receipts.rs`, about L22-38) refuses the same pairs. A program pays household accounts only
  (`validation.rs:189-219`). A tax is assessed on wage income or positive operating income (`TaxBasis`,
  `financial/model.rs:54-57`), which a public account does not have. An allocation of the fund's own account is
  admitted (the check reads only the treatment, the recipient's kind, a budget and a positive amount).
- So V2 takes one of two roads. (a) An engine task before Task 4: a fourth `PublicTransferTreatment`, a grant to a
  public account, admitted in `validate_public` and `PublicBudgetReceipt::validate`, written in the wire and the
  contract. (b) No engine change: the fund pays the poorer place's public providers' grants directly, as
  `ProviderOperatingGrant` allocations from the fund to those sites, in place of that part of the place's own
  allocation. Under (b) the grant reaches provision only; county support and the County Review's relief stay the
  place's own.
- Task 1: a `[[place_grants]]` table: `key = "place_grant"`, then rows `place = "<hub geoid>"`,
  `amount_per_period_micros`; refused as V1's keys are.
- Task 4: wires each row by road (a) or (b), payer the fund, rank 0; a test that each listed place's receipts and
  grant equal its payments within 1%.
- Part II: `Settings.place_body = "every_place_even"`. Task 11 (decision 11) computes the share, the best-off
  place's payments over its taxes, and each other place's grant, its payments less its taxes at that share
  (`place_grant_micros`). Task 13 then writes the rows in place of its refusal of the setting.
- Task 15: as V1, with the grants counted in each place's receipts and in the fund's payments.

**V3. Each place its own cost** (item 2). An engine program has one amount for all its recipients
(`PublicProgramTerms::PerPerson { amount_per_person }`, `financial/model.rs:189-199`). Two roads:
- (a) A program row per place, no engine change: 187 rows `no_earner_<hub geoid>` and `laid_off` are 188 programs,
  within `MAX_PUBLIC_PROGRAMS` (256, `model.rs:41`), and each key fits `PublicProgramKey` (lowercase, digits and `_`,
  at most 32 bytes, `financial/model.rs:175-182`). Task 1 admits `no_earner_<geoid>` rows of kind `per_person`, each
  with its `place`, one for every domestic place; Task 4 deals each place's no-earner accounts to its own row; Part II
  (`Settings.benefit_rule = "each_place_own"`; Task 11, decision 6) sets each row's amount at that place's own
  tier-1 cost at its own sellers' prices (`own_place_benefit_micros`); Task 13 then writes the rows in place of its
  refusal of the setting; Task 15 asserts every account reaches tier 1 and reports the spread of amounts.
- (b) A new kind of terms, an amount by place, in the engine (`financial/model.rs`, `programs.rs`, validation, the
  wire and the contract), one program row with a table of amounts. Larger; (a) is enough.

**V4. One figure at the average** (item 2). Part II (`Settings.benefit_rule = "one_average"`; Task 10, decision 10,
and Task 11, decision 6) sets the `no_earner` amount at one person's tier-1 cost at national prices; Task 13 writes
it with no new key. Task 15: `no_account_opens_going_without` asserts it for every account but the no-earner accounts
whose tier-1 cost at their own sellers' prices exceeds the benefit; those are written into the report with their place
and gap and counted.

**V5. Only those who hold no job, counted each period.** Superseded by the lead's call 18, which follows O12's words
at the opening with no engine kind of its own. Kept as written in case the Director wants the count to follow play:
it needs an engine kind of terms that pays for persons not at work: a
`PublicProgramTerms` variant (tag 3) whose due is `amount_per_person x` (the cohort's persons less the account's members
at work this period). `program_dues` (`financial/programs.rs:21-75`) reads the persons from the cohorts
(`recurring_economy().households`, L26-33); the members at work are the account's employment terms
(`economy.employment`, whose `payee` is the account, as `financial/layoffs.rs:38-46` reads them) that the period's
staffing employed. An engine task before Task 4 adds it, with validation as `PerPerson`'s (`validation.rs:222-229`),
the wire and the contract. Then Task 1 admits the kind for `no_earner`; Task 4 makes collective residence accounts
recipients of both `no_earner` (for their residents not at work) and `laid_off` (for those with a wage; the engine
allows one after-layoff program a household, `validation.rs:235-239`, and any number of per-person ones), and its test
`every_domestic_account_is_in_one_program` reads "one program, or both for a collective residence".

**V6. Services regrouped, no engine change** (item 1). The scenario declares `business_services` and `housing` as
first-stage services (`kind = "utility"`) beside `utility`; `household_services`, `leisure` and `public_provision`
stay `kind = "service"`. The order of paying becomes food, materials, consumer goods, utility, housing, business
services, household services, leisure, resources.
- Task 1: nothing in the engine. The admission may take a clearer word for the first stage (the lead's to decide
  when ruled); the fixture keeps its kinds.
- Part II: `Settings.service_stage` and `Settings.paying_order` (Task 9, decisions 2 and 4): the re-cut lets a
  service buy a service of an earlier stage and spreads the rest by O4; Task 13 writes the kinds and the order
  above, which the compiler admits today.
- Task 15: the report names what is still spread (260.2 a period in the prototype).
- Left bent, and written into the report: housing cannot buy business services (its price is 0.69 of the model with
  no rules; it is 7.5% of the basket against 11.4%).

**V7. One more stage in the engine** (item 1): utility and business services; housing; the rest. An engine plan of its
own before Task 1, about three tasks by the lead's estimate from reading the code: `ServiceStage` gains a stage
(`services/model.rs`), the period's loop over stages (`transition/state.rs`, about L1430) and the stage's market
moment (`services/admission.rs:694`, `clearing/table.rs` `MarketMoment`, whose order must then be decoupled from its
wire tag) follow, the compiler's `kind` gains a word for it, and every measured small world keeps its bytes. It
amends ADR264 (two stages) and ADR312 (the order of a period's steps). Part II: `Settings.service_stage` with a
stage 3, which Task 13 refuses until the compiler's word exists.

**V8. Business services cross a border** (item 2). Two or three compiler tasks before Task 5, by the lead's estimate:
`opening/markets.rs` `service_provider` gives one provider per buyer location and good; a buyer then takes a share of
its business services from a provider across the border, by `import_bps["business_services"]` at home and its region's
`export_bps["business_services"]` abroad (Task 1's tables gain that key). The engine does not forbid it
(`ServiceConnection`: "geographic eligibility belongs to source compilation"). Task 15's trade balance counts services.
Part II (`Settings.crossing` with `business_services`; Task 9, decision 4, and Task 10, decision 6) keeps the
accounts' own exports and import share of business services, and the one export factor runs over six products;
Task 13 then writes the two shares in place of its refusal of the setting.

**V9. Utility, leisure and business services are sold across the country** (item 5).
- A plan of its own, before Task 14a: the policy admits a reach for each service (`same_state_or_own_counterpart`
  as today, or `country_or_own_counterpart`); `opening/markets.rs` `service_provider` gives a buyer of such a service
  providers over the whole country in proportion to what each can make (if the engine holds one provider a buyer and
  good, a deterministic assignment of buyers to providers that fills each provider in proportion); a foreign buyer
  keeps its own counterpart. The owner's restart, which reads the first provider of a buyer, is read again there.
- Part II: no figure of the solve changes (it is national). Task 11's `state_services` then counts those three
  services for the country as one, and `own_price_gap` at the capacity-weighted price, which is the national price.
- Task 15: the reported counts follow; for the three services the count at the sellers' own prices equals the one at
  national prices.

**V10. The shop passes on what it saves abroad** (item 6).
- Task 14b, decision 1: a shop's posted price of a good is what it pays for it, the national price times the home
  share plus its foreign second supplier's price times the share it may import (`import_bps`), plus its charge; its
  minimum and maximum move with it.
- Part II: `Settings.shop_import_saving = "households"` (Task 10, decision 7; Task 13 then writes it).
- Task 15: `no_account_opens_going_without` and the balances read the shop's posted prices as before.

**V11. A buyer's custom is shared over its sellers** (item 7).
- An engine plan of its own, six to ten tasks by the lead's estimate from reading the code, not a plan: a household's
  purchase rows and a business's service inputs are keyed by the seller too (`recurring/validation.rs`,
  `services/validation.rs`), each row a fixed share of the buyer's need of the good; the household's buying
  (`recurring/households.rs`), the tiers' lists, the price limit, the restart's tables and the wire follow. Every
  measured small world has one seller a buyer and keeps its bytes.
- Tasks 7b and 7c then write a row for each seller of the buyer's reach with its share, in place of dealing whole
  buyers; Task 8's `sellers` holds the shares' average wage; Part II's own price of a need is the place's blend.

**V12. A buyer takes from the cheapest seller it can reach** (item 7; rule A4). The market becomes one product in
one place with all its sellers (it changes rule P1 of ADR312). Measured once, in round six: the cheaper seller won at
once and the loser shut. It waits for a measurement with the six rules on, and for V11's rows.

## Where the code differs from the design, the stage 2 plan or the spike

- **The import cap is the compiler's, and it is two caps in one.** The spike's section 1 calls it a cap on "buying
  abroad". In `opening/markets.rs` `procure` it is also what a foreign buyer takes from the United States, because a
  foreign buyer's second supplier is a domestic county (`secondary_candidates`). So today it sets exports too.
- **Equipment abroad.** As the spike says, only when no home supplier exists (`opening/equipment.rs`, `policies`); and
  the engine admits one investment policy and supplier per process (`babylon-material-circuit/src/equipment/
  validation.rs`), so a share is met by choosing processes.
- **Machine counts** follow batches in the compiler (`equipment.rs` `machine_units`), not the engine, and for every
  coarsened site they come from the grain's endowment (`grain/build.rs` `OpeningProductiveEndowment::source`). The
  engine holds a list of definitions, binds each process to one, and admits several of one good (Task 6, decision 1).
- **Opening machines** are sized for `employed` and capped at `force`; O14 asks for the whole workforce.
- **Handling** is already by site and good in the engine, but whole hours a unit and at least 1 (`catalog.rs`), and
  the compiler writes rows for needs only (`actors.rs` `handling_requirements`, `markets.rs` `households`): a good that
  is only wanted, consumer goods, would have no shop at all. The spike named one figure where three are needed; the
  gap is wider. Seven readers of a handling row in the engine multiply or divide by it (Task 2, decision 3), and
  three of them need a cost per unit, not hours.
- **The bench's budget keys.** An integration test cannot read an account's `HouseholdBudgetKey`:
  `NationalOpening.household_keys` and `CapturedEconomicCatalog::national_household_budget` are `pub(crate)`
  (`opening/build.rs:505`, `economic_catalog/capture.rs:261`). Task 8 makes the second `pub`.
- **One public account cannot pay another** (`financial/validation.rs:157-176`); see V2.
- **Payout.** The engine declares `fraction x eligible earnings`, capped by the row's `period_cap` (one period of the
  site's opening cash, `financial.rs` `ownership`) and by cash above the floor (payroll) (`material-circuit/src/
  financial/close.rs`, `distribute`). The spike's section 1 names only the second cap.
- **Public bodies** open with `working_capital_periods` (2 in the scenario) times their cap, not a fixed two periods
  (`financial.rs` `public_accounts`). O13's "cut in proportion" holds for the fund only: stage 4's plan B keeps the
  places' bodies capped, and the County Review's account cannot hold the cut (W15).
- **Support** is one unit of food a person (`financial.rs` `support_unit_price`); with small units that is a day's food.
- **The accounts' national wage** ($36.34 an hour over 154,736,293 jobs, all ownerships, read from the `jobs` block)
  differs from the pay table's ($35.66 over 148,902,211, stage 1's last section). The game pays the pay table.
- **The spike's workforce** (161.3 million) is the ten-trade shipped world split by QCEW jobs; its accounts were its own
  fold, made before stage 1's table. Its import shares hold on the committed table: consumer goods 4,277 and capital
  goods 4,104 basis points.
- **Six needs** are required under every schema (`admission.rs` `needs`), and one recipe for each trade but
  distribution (`recipes`): stage 2's "What Schema 8 Means" says the same.
- **The bench's stand-in fund** deals the programs by members at work and opens with no cash
  (`tests/support/country_fund.rs`); this plan deals them by household key and opens the fund with its reserve.
- **`preset.rs`** in the copy has a block `let mut rows: Vec<(Kind, &[u8])> = vec![` with 12 `include_bytes!` rows and
  four rows of variables, not the 15 rows the other lane's tool expects; the lead is restoring it, and no task here
  touches it.
- **The design's paying order** is a stage 2 fixture figure (nine products); the rebuilt scenario keeps it.

## What this draft did not read, and could not find out

- Not read: the spike's `fold_accounts.py` and `qcew_nation.py`, its `model.json` and `model_run.txt` beyond the first
  lines, and `builder-spike-2/` (background only); stage 4b beyond its headings and last sections; the bench's Tasks 1
  to 3; `national_household_units.rs` beyond its file list and the sizes test; stage 2's Tasks 8 to 10b code (being
  built: their names are taken from the plan's text); the engine's `valuation/equipment.rs` and `capacity.rs`; the
  County Review's use of the support unit beyond one call.
- Not found out: whether the census's assignment of domestic buyers to foreign regions is truly independent of numbers
  (Task 14a proves it); the persons in no-earner households (the census gives them; the spike assumed 1.6); whether
  `serde_json` in the persistence crate keeps sorted keys for Task 8's bytes (Task 8's checker compares bytes); the
  sizes of the twelve-trade opening (Task 6 and Task 16 print and pin them); whether 34 periods of the rebuilt opening
  fit 1 MiB with wants' columns (Task 17 handles it); how much faster or slower a period is with wants at the
  country's size (Task 16 times it); whether the new freight needs a stage 6 airport raise (Task 16 records it).

## What the one check changed

Where a line below says a finding waits for Part II, the next section says where the rewrite applied it.

- B1 to B7 (refused service inputs of services; only five goods cross a border; the shop's inputs and margin; the
  paying order inside a part-reached tier; the price solve and its floors; exports defined twice; a region's mix of
  jobs): waited for Part II, and are applied in its rewrite (the next section).
- B8 (machines in the grain's endowments): applied, Task 1 Files and decision 7, Task 6 (Why, Files, decisions 1 and
  2, a test), Task 14b Files and decision 1; Task 6's stop removed, its guard test kept.
- B9 (the fixture and Task 1's keys): applied, Task 1 decisions 4, 6 and 7; the price scale's refusal moved to Task 14a.
- B10 (Task 2's readers, type name, decoder, version, runs): applied, Task 2 throughout.
- B11 (budget keys not public; census by residence, good and force): applied, Task 8 Files and decision 1.
- B12a, B12b (grams per unit; the deposit input): wait for Part II.
- B12c (public providers' machines): applied as ruled, Task 4 decision 8 and its test; Part II counts the machines.
- B13 (place shares): the approved one share is built (Tasks 1, 4, 15, Review Focus 5); the table is variant V1.
- B14 (the benefit's figure): waits for Part II; the per-place and average figures are variants V3 and V4.
- B15 (kept money over which accounts): waits for Part II (Task 10).
- B16 (the bench's second fund): applied, Task 4 decisions 9 and 10 and a test; Task 16 decision 2 refers to it.
- M1 (`TradeSet`'s crate): applied, Task 1 Interfaces.
- M2 (`EconomicHouseholdSeed`; where wants are filled): applied, Task 3 Files, Interfaces, decision 5.
- M3 (purchase rows' bound; stock on every want): applied, Task 3 decisions 1 and 3, a test; call 12.
- M4 (pins of "before" taken before the change): applied, Task 2 (existing pins), Task 3 and Task 7 (a run on the
  unchanged code).
- M5 (3% in weekly units): applied, Task 2 Why.
- M6 (Task 5's numbering, the foreign cap, Task 6 first): applied, Task 5, the build order, call 11.
- M7 (cohorts within the row bound): applied, Task 6 Interfaces, decision 3, a refusal test.
- M8, M11, M12, M13, M14: wait for Part II.
- M9 (one national wage): the compiler's side applied, Task 8 decision 1 and Task 14b decision 2; the builder's waits
  for Part II.
- M10 (foreign public bodies): Task 15 decision 4 applied; the solve's side waits for Part II.
- M15 (a Rust parse of the written scenario in Task 13): waits for Part II.
- M16 (Task 14 split): applied, Tasks 14a and 14b; Task 1 is kept whole.
- M17 (money conserved; by trade and place; sellers under own cost): applied, Task 15 decision 5, its tests and the
  record.
- M18 (missing refusal tests): applied for Task 6 (cohort bound) and Task 14b (`Price`); Task 4's missing place is
  variant V1's; Tasks 10, 12 and 13 wait for Part II.
- M19 (the bench's finish; five `../`): applied, Task 16 decisions 1 and 2, Task 14a Files.
- M20 (the price rule's Task 8 decisions 3 and 4): applied, Task 16 decision 5.
- M21 (the stand-in benefit's source): applied, Task 1 decision 6.
- M22 (laid-off residents get no `laid_off`): applied, Task 4 decision 4 and For the Director item 3.
- M23, M24: wait for Part II.
- The Director's items: rewritten as three after the check (place bodies, the benefit and local prices, collective
  residences), and again as four after the prototype (services' stages, the border, the benefit, place bodies);
  collective residences became the lead's call 18. The two tax rates moved to call 5; calls answered by approved text
  moved to "Settled by approved text".

## What the rewrite of Part II and the lead's check of it changed (26 November)

- Part II was rewritten from the prototype's model as Tasks 9, 10, 10b, 11, 12 and 13 (a drafting agent, one draft),
  with the choices that wait for the Director as settings at the approved text's defaults. The findings that waited
  for it are applied there: B1 and B2 (Tasks 9 and 10), B3 (Task 10 decision 1; Task 14b decision 3), B4 (Task 11),
  B5 (Task 10 decisions 4, 5 and 12), B6 (Task 10 decision 6; Task 12), B7 (Task 12), B12a and B12b (Task 10b
  decision 4), B14 (Task 10 decision 10; Task 11 decision 6), B15 (Task 10 decision 11; Task 11), M8 (Task 9
  decision 4), M9 (Task 10 decision 1), M10 (Task 12; Task 13's metadata), M11 (Task 10b decision 5), M12 (Task 9's
  `Settings`), M13 (Task 10b's test of the five needs), M14 (call 15), M18 (the refusal tests of Tasks 10, 10b and
  13), M23 (Task 10 decision 9), M24 (Task 10b decision 3). M15 is call 27.
- The rewrite asked for keys the earlier tasks did not have: the residences' row and the luxury scales (Task 1; Task
  3, decision 1; Task 4, decision 4) and five more figures in the census (Task 8). Task 4 is no longer held.
- The lead's check counted two things on the prototype (What the prototype found, "Places") and changed the draft
  for them: the benefit and the luxury scales are set at each account's own sellers' prices, from sellers' wages the
  census now gives; the tier solve stays at national prices and the builder counts what own prices and the
  same-state rule move (Task 11, decisions 2, 6, 10 and 12); Task 15 asserts the national count and reports the
  others. It also gave every key its support (Task 10, decision 11), named the shop's price (Task 14b, decision 1),
  and raised two more choices for the Director (items 5 and 6; variants V9 and V10).
- Checking Task 8's census against the code, the lead found that the compiler gives every buyer one seller, the
  largest of its place, and counted it on the compiled opening ("What the compiled opening showed"). Tasks 7b to 7d
  were added for it, Task 15 gained a check by workplace, and item 7 with variants V11 and V12 went to the Director.
  The same reading showed that the game keeps its accounts by a place's parts: the census, the luxury scales and
  Part II's "place" were moved to the part (calls 28 to 30).
- Writing the country bench's reading at the end of stage 2, the lead asked why the few sellers that do have
  buyers sell almost nothing in period 1, and counted it from the compiled opening: a company's opening sweep and
  the cash floor of a service input, the cause the repair report of 20 November had found on Wayne, and which the
  Director ruled out that day. The opening design never took the ruling up and this plan's drafts kept the
  fixture's key. Task 7a, a line of Task 13 and a test of Task 15 restore it.
- Tasks 7b to 7d and the moved passages were checked once against the code at `9753016ea` by an independent reader.
  Two faults would have stopped a builder, and both are mended above: the census cannot read an account's part from
  the opening alone (Task 8 now takes the capture), and policy admission cannot know which county is a hub (Task 1
  now checks a label's form, and Tasks 3 and 4 refuse what names nothing). Its other findings are in the tasks: a
  kind of buyers is not spread on its own when shares are carried (Task 7b, decision 2, says what is in
  proportion); installation inputs follow their site's makers (Task 7d, decision 2); a maker is offered only where
  a route can be built (decision 5); the count nearest its bound is a route stage's memberships (decision 7); every
  buyer abroad took from one maker (decision 3 deals them). The two thresholds a builder could not have met as
  first written were set from the rule itself, run on the dump of the compiled opening: 0.7% of household-services
  workers at providers with no buyer, 0.5% of shop workers at shops with none.
- Run A built Tasks 7a, 1, 2 and 3. Task 3's review did not pass it: the plan's rule for a scaled luxury, a floor
  on the account's whole quantity, cannot be written in the engine's want row, which holds whole units a person.
  The builder had floored a person's units and moved the test's input to fit, and the fix round stopped for the
  lead. The lead chose the engine: a want row gains a scale, written to bytes only where it is used, as Task 2
  did for a handling row's units (Task 3b), and the compiler then scales whole (Task 3c). The other course, units
  so small that the floor loses little, would have bent Part II's choice of units for every good that is a luxury.
- Two things Task 1 left for the lead, settled here: a luxury scale's place for a dependency is its M49 code, as
  Task 1 admits it, and Part II writes that label; and the plan's one test of the fixture's keys stands as three
  (`the_fixture_takes_the_fund_and_the_programs`, `..._the_places_and_the_markets`,
  `..._the_machines_and_the_handling`).
