# The Opening, Stage 5: The Builder and the New Numbers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

Drafted and checked once on 25 November 2026 against `0513cf036`; Part I is mended from the check. A prototype then
measured the builder's model under the game's own rules ("What the prototype found", below). Part II was rewritten
from it on 26 November and checked once by the lead. The Director ruled its seven open choices on 26 November
(ADR326; "Ruled by the Director on 26 November", below), and the plan was amended once for them: the ruled variants
are its built text, and each choice keeps its named field in the builder's `Settings` (Task 9, decision 2) with
the ruled value, so that a later ruling is a small edit.

**Part I** is Tasks 1 to 8 and 14a to 18 and every section outside the tasks. **Part II** is the builder: Tasks 9,
10, 10b, 11, 12 and 13. Tasks 1b, 4a, 7f and 7e were added for the rulings of 26 November. **Task 4** (the fund and
its programs) builds the benefit at each account's own needs and the fund's share part by part, as ruled; Task 4a
gives the engine the kind of program that needs, and Task 1b the scenario its keys.

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
product, the tax rates and the fund's share of each part. That scenario compiles as `national-world-v13` with its
wants, its national fund, its grants and its three programs, its prices that follow each workplace's wage, and the
map's pinned basis. It opens
with every observed job needed and the four balances of O6 each within 1%, and the country bench records it. The
shipped scenario of schema 7 keeps every byte.

**Architecture:** Four parts, in this order. (1) The policy of schema 8 learns the keys the builder writes, and the
engine learns four things it lacks: handling hours for a block of units, so retail hours need not be whole hours a
unit (Task 2); a scale on a want (Task 3b); a program that pays each recipient its own amount (Task 4a); and several
providers of one service for a buying workplace (Task 7f).
(2) The national compiler wires what the engine already has: each account's wants (stage 3), the fund, the split
taxes, the place grants and the programs (stage 4), imports and exports by product, machines by trade and of every
age, and the
map's pinned basis. (3) A Rust recorder writes the census of the twelve-trade opening (the game's workforce, bands,
wages, places, the foreign rows of every domestic buyer), committed and pinned. A Python builder reads the accounts,
the pay table and that census, solves the numbers with exact fractions, and writes the new scenario and its balance
sheet. (4) O5's price and refusal switch on, stage 2's fixture is retired in favour of the new scenario, the opening's
own report is tested before any period, and the country bench records the new scenario. Nothing in play reads the
accounts table (O3).

**Tech Stack:** Rust (`babylon-material-circuit` for four tasks, `babylon-persistence`), TOML scenario defines, Python
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
  found that the engine could not scale a want). The keys the rulings of 26 November add are Task 1b's, first in
  run B;
- run B: Tasks 1b, 4a, 4, 6, 5, 7, 7b, 7f, 7e, 7c, 7d, 8, in that order (Tasks 1b, 4a, 7f and 7e were added for
  the rulings of 26 November: the new keys first, then the engine's kind of program that Task 4 needs; Task 6
  before Task 5: Task 5 counts the replacement machines that Task 6 sets; Task 6 uses nothing of Task 5; Tasks 7b
  to 7d deal buyers to sellers after Task 5 has set what is bought abroad; Task 7f lets a workplace take a
  service from several providers, and Task 7e then gives each business buyer of a crossing service its share
  across the border; and all of them come before Task 8's census reads who sells to whom);
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
  with its margin (variant C: the accounts' margins scaled by one solved factor, at least 1.25 times wear); utility,
  business services and housing are first-stage services and household services, leisure and public provision
  second-stage ones, so that these can buy their offices and premises (ruling 1 of 26 November: V6, no engine
  change), and the order of paying is food, materials, consumer goods, utility, housing, business services,
  household services, leisure, resources;
- national opening prices from cost and margin, and each workplace's own opening price following its own wage (O5),
  with the refusal of a private product under cost at the nation's average wage; a shop posts each good at what it
  pays for it plus its charge, so goods from abroad are cheaper in the shop and the shop has no income from buying
  abroad (ruling 6: V10);
- the needs of tier 1 (today's six products) and the comforts and luxuries of tiers 2 and 3 as want rows (O7), sized
  40%, the next 60% and the next 150% of a person's average spending;
- retail handling for every shop good households buy, needed or wanted, in hours for a block of units (O9);
- import and export shares by product, each import share written so that the nation's imports are the accounts'
  share, given that only buyers with a foreign second supplier import (Task 10b, decision 8); equipment bought abroad
  by its share; business services, the one crossing service (`crossing_services`, K1), bought and sold across the
  border by businesses by shares, a home site with a second row abroad and a site abroad with rows at home providers
  (ruling 2, E2; Tasks 7f and 7e), households keeping a home provider; and foreign regions whose mix of jobs is
  computed so that each region's trade with the United States, services counted, balances (O11);
- one rate, the same on wages and on operating income (call 5); a national fund that takes from each part its own
  share of both taxes (`share_by_part`, K4), so that a part whose taxes pass its payments sends the rest to the fund,
  and that pays the funded public providers of each part whose taxes fall short (`[[place_grants]]`, K5), so that every
  part's own body opens even (ruling 4, D4); the grants stand after every benefit in the fund's budget, so a short
  fund cuts them first;
- three programs (O12, O13): `no_earner` (`kind = "own_needs"`), paying each account with no earner its own needs
  a person at its own sellers' posted prices, worked out by the compiler from the compiled opening and rounded up to
  a micro, at a share of 10,000 that politics may cut or raise (ruling 3, D2, E8; Task 4a's tag 3); `laid_off` at
  5,000 points for 13 half periods; `residence` (`own_needs`), paying each collective residence its residents' needs
  for those with no job at the opening (call 18); and the luxury scale of every account whose money passes
  its three tiers (call 20);
- public providers whose grant also covers their machines' wear for one period, so that they replace their machines as
  a private workplace does from its margin;
- machines by trade at a designed number of workers per machine, opening at every age, for the whole workforce (O14);
- the map's basis pinned as the shipped food figures, so the 187 places stay (O15);
- no working capital taken by a company at the opening (the Director's ruling of 20 November; Tasks 7a and 13), so
  that every workplace can pay for its first period;
- buyers dealt to sellers so that every workplace with people at work has custom in proportion to them (Tasks 7b to
  7d): O4 holds for a workplace, not only for a trade; utility, leisure and business services (`country_services`,
  K2) bought at home first and across state lines for the rest (ruling 5, D5), housing, household services and public
  provision in the buyer's own place;
- business services and housing first-stage services beside utility (`kind = "utility"`), so that care, schools,
  leisure and public services can buy their offices and premises; the order of paying food, materials, consumer
  goods, utility, housing, business services, household services, leisure, resources (ruling 1, D7: no compiler or
  engine change; housing cannot buy business services or utility, and the report says so);
- a shop that posts each good at what it pays for it plus its charge, so that goods from abroad are cheaper in the
  shop (ruling 6, D6; Task 14b);
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
  alone runs `mise run rust:check-no-docs`, after Tasks 4a, 4, 8 and 15.
- **The keys of 26 November** are named as the lead's decisions files name them (K1 `crossing_services`, K2
  `country_services`, K3 the program kind `own_needs` (E8), K4 `share_by_part`, K5 `[[place_grants]]`); no task
  renames one.
  Part II writes them with the same names.
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
5. **A part's body that cuts or hoards from period 1.** With one national rate, a part whose people earn more
   collects more than it pays and a poorer part less. Ruled 26 November: every part opens even (ruling 4, D4).
   Expected: each part's receipts, with the fund's grants to its providers, within 1% of its payments; the fund and
   the nation within 1%; a short fund cuts the grants before any benefit. Tests: Task 4,
   `a_part_s_own_share_sets_its_rows`, `a_place_grant_is_paid_by_the_fund`, `a_short_fund_cuts_the_grants_first`;
   Task 15, `every_public_body_opens_within_one_percent`, `the_four_balances_close_within_one_percent`.
6. **A benefit that does not follow its account.** An own amount kept beside a recipient must stay with it when the
   engine sorts the recipients, and the compiler must read the account's own sellers after every offer is final.
   Expected: each no-earner account is owed its own needs a person, rounded up to a micro, times the share. Tests:
   Task 4a, `own_amounts_are_owed_by_their_share`, `amounts_are_sorted_with_their_recipients`; Task 4,
   `each_account_is_paid_its_own_needs`; Task 15, `nobody_is_paid_above_their_needs`.
7. **A tangle across state lines.** Whole buyers against a strict national level send far more across state lines
   than the states' imbalance needs (counted: 34.7% of utility's units and 39.6% of business services', where 12.5%
   and 15.1% must cross); the home test reads the ratio before the buyer (E1): 10.0% and 11.3%. Expected: under 1% of
   each country service's workers at providers with no buyer, and the units out of state at the counted figures.
   Test: Task 7b, `country_services_are_bought_across_the_country`.
8. **A requirement shared over two providers.** A buying site with two rows of a service must order its requirement
   once, shared by the caps, and the hiring bound and the restart must read both providers. Expected: with one row
   every figure and byte is today's. Tests: Task 7f, `a_requirement_is_shared_by_the_caps`,
   `a_workplace_buys_from_two_providers`, `one_row_a_service_keeps_its_bytes`; Task 7e, `no_household_crosses`.

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `rust/crates/babylon-persistence/src/national_economy/policy/{admission,builder_keys,game}.rs` | The keys of the rebuilt opening and of the rulings of 26 November; the price scale's refusal | 1, 1b, 14a |
| `rust/crates/babylon-persistence/tests/fixtures/national_twelve_trades.defines.toml` | Takes the keys (Tasks 1, 1b), retired (Task 14a) | 1, 1b, 14a |
| `rust/crates/babylon-material-circuit/src/{catalog.rs, model.rs, wire/catalog.rs, transition/merchant_admission.rs, transition/outbound/orders.rs, recurring/firms.rs, recurring/spare_money.rs, clearing/supply.rs, clearing/limit.rs, adjustment/restart.rs, adjustment/bound.rs}` | Handling for a block of units | 2 |
| `contracts/material_circuit_v4.yaml` | The handling block | 2 |
| `rust/crates/babylon-persistence/src/national_economy/opening/{markets,actors,templates,build}.rs` | Wants, shop goods wanted, handling blocks | 3 |
| `rust/crates/babylon-material-circuit/src/financial/{model,programs,validation}.rs`, `src/wire/financial.rs` | A program's own amounts a recipient (tag 3) | 4a |
| `contracts/material_circuit_v4.yaml` | The program's tag 3; service inputs of several providers | 4a, 7f |
| `rust/crates/babylon-persistence/src/national_economy/opening/{financial,fund,equipment,templates,build}.rs`, `opening.rs`, `county_review.rs` | Fund, split taxes by part, place grants, own-needs programs, support unit, public providers' wear | 4 |
| `rust/crates/babylon-persistence/tests/support/country_bench.rs` | The bench keeps an opening's own fund | 4, 16 |
| `rust/crates/babylon-persistence/src/national_economy/opening/{markets,equipment}.rs` | Imports and exports by product; equipment abroad | 5 |
| `rust/crates/babylon-persistence/src/national_economy/opening/equipment.rs`, `grain/build.rs` | Machines by trade, of every age | 1, 6 |
| `rust/crates/babylon-persistence/src/national_economy/grain/build.rs` | The map's pinned basis | 7 |
| `rust/crates/babylon-material-circuit/src/{catalog.rs, services/requirements.rs, services/admission.rs, services/validation.rs, adjustment/bound.rs, adjustment/restart.rs}` | A buying workplace's service from several providers, by shares | 7f |
| `rust/crates/babylon-persistence/src/national_economy/opening/{dealing,markets,equipment}.rs` | Buyers dealt to sellers in proportion; country services at home first; crossing services across the border by shares | 7b to 7e |
| `rust/crates/babylon-persistence/src/economic_catalog/capture.rs` | `national_household_budget` made public for the census | 8 |
| `rust/crates/babylon-persistence/tests/national_opening_census.rs`, `tests/support/opening_census.rs` | The census recorder and its check | 8, 14a |
| `src/babylon/data/reference/economy/national_opening_census_v13.json.gz` | The game's workforce, bands, places, foreign rows, crossing force (gzipped JSON text) | 8 |
| `tools/national_opening_recut.py` | Settings, the census reader, the accounts re-cut | 9 |
| `tools/national_opening_solve.py` | Quantities, prices, margins, trade, taxes, the margin factor | 10 |
| `tools/national_opening_units.py` | Units, recipes, prices, grams, handling blocks, written rates | 10b |
| `tools/national_opening_tiers.py` | Place accounts, tiers, luxury scales, the benefit, place bodies, the two counts | 11 |
| `tools/national_opening_abroad.py` | Foreign regions' mix of jobs and export shares | 12 |
| `tools/make_national_opening_numbers.py`, `tools/national_opening_v13_defines.toml.in` | The writer and its template | 13 |
| `content/scenarios/national-rebuilt/defines.toml` (+ `defines.metadata.json`) | The rebuilt scenario and its balance sheet | 13 |
| `tests/unit/tools/test_national_opening_{recut,solve,units,tiers,abroad,numbers}.py` | The builder's tests | 9 to 13 |
| `rust/crates/babylon-persistence/tests/national_twelve_trades.rs` and the files that include the fixture | Open the rebuilt scenario | 14a |
| `rust/crates/babylon-persistence/src/national_economy/opening/{markets,financial,build,equipment}.rs`, `grain/build.rs` | O5's price and refusal; the shop's paid price | 14b |
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

### Task 1b: The keys the rulings of 26 November add (schema 8)

Commit `feat(economy): admit the keys of the rulings of 26 November in a national policy of schema 8`.

**Why, read from the code (`1a97bf28a`).** Task 1 is built (`5aca1514e`, `ddc7677a5`). Its keys sit in
`policy/builder_keys.rs` (`admit`, `programs`, `program`, `luxury_scales`, `place_services`, `fund`) and
`policy/admission.rs` (`RawMarkets`, `RawProfile`, `RawDependency`, `shares`, `markets`, `profile`). Five rulings of
26 November need keys it lacks (the lead's K1 to K5, K3 as the second-round decision E8 has it), and the rebuilt
scenario needs a larger bound (E4):
- business services cross the border (ruling 2, E2): `shares` (`admission.rs`, about L1064) admits exactly the
  priced storable goods (`shop_goods`) in `import_bps` and in every `export_bps`, so a service has no share to read;
- three services are sold across state lines (ruling 5, D5): nothing names them;
- the benefit is each account's own cost (ruling 3, E8): `program` (`builder_keys.rs`, about L284) admits
  `no_earner` as `per_person` only and `residence` as `per_person_by_place`, one amount a hub county
  (`GameProgramTerms::PerPersonByPlace { amounts: BTreeMap<CountyGeoid, Currency> }`, `game.rs` L169), and `programs`
  (L266-282) wants exactly three rows. Under E8 the scenario carries the rule, not a table: the compiler works out
  each account's own needs from the compiled opening's offers (Task 4);
- every part opens even (ruling 4, D4): `RawFund` has two national shares only, and there is no grant row;
- the size: `admission.rs` `parse` (L339-342) refuses a text above 65,536 bytes (`Bounds`) before it is parsed, and
  `NationalGamePolicy::from_captured_bytes` (`game.rs` L360-364) refuses captured bytes above 65,536 before it reads
  them as text. At that point the schema is not known: `schema_version` is a field of the parsed `RawPolicy`
  (`admission.rs` L343-350).
No reader of `GameProgramTerms` exists outside the tests yet (Task 4 is not built): `rg -n 'PerPersonByPlace'
rust/crates` finds `game.rs`, `builder_keys.rs`, `tests/national_game_policy.rs` (L809, L1135) and nothing else.
Nothing reads `import_bps` or `export_bps` but `markets::abroad_bps` (`markets.rs` L818), which looks a good up by
its key, so a service key in the tables changes nothing it reads.

**Files:**
- Modify: `rust/crates/babylon-persistence/src/national_economy/policy/{builder_keys.rs, game.rs, admission.rs}`;
  `policy.rs` and `national_economy.rs` (re-exports of the new types);
  `rust/crates/babylon-persistence/tests/fixtures/national_twelve_trades.defines.toml` (its `residence` row goes)
- Test: `rust/crates/babylon-persistence/tests/national_game_policy.rs`

**Interfaces** (`game.rs`; every name is fixed by the lead's K1 to K5):

```rust
/// What a public program pays.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GameProgramTerms {
    PerPerson { amount_per_person: Currency },
    /// "The needs in full", times `share_bps / 10_000`: each recipient its own needs a person at its own sellers'
    /// posted opening prices, worked out by the compiler (E8, Task 4). Replaces `PerPersonByPlace`, which goes.
    OwnNeeds { share_bps: u32 },
    AfterLayoff { wage_share_bps: u16, half_periods: u16 },
}
/// The most an own-needs program's share may be: ten times the needs. Equal to the engine's
/// `MAX_PROGRAM_SHARE_BPS` (Task 4a); Task 4 asserts the two equal at compile time.
pub const MAX_GAME_PROGRAM_SHARE_BPS: u32 = 100_000;
/// The most bytes a policy's text may hold: 65,536 under schema 7 and earlier, 262,144 under schema 8 (E4).
pub const MAX_POLICY_BYTES: usize = 65_536;
pub const MAX_POLICY_BYTES_SCHEMA_8: usize = 262_144;
pub struct GameFundPolicy {
    pub wage_tax_share_bps: u16,
    pub operating_income_tax_share_bps: u16,
    pub reserve_periods: u64,
    /// K4: the fund's share of both taxes collected in a part, by the part's label. Empty: the two shares above
    /// apply everywhere.
    pub share_by_part: BTreeMap<String, u16>,
}
/// K5: what the fund pays a part's funded public providers a period (D4).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GamePlaceGrant { pub part: String, pub amount_per_period: Currency }
// NationalGamePolicy gains, beside `place_services`:
//   `crossing_services: Vec<String>` (K1), sorted; empty under schema 7 and when the key is absent;
//   `country_services: Vec<String>` (K2), sorted; empty under schema 7 and when the key is absent;
//   `place_grants: Vec<GamePlaceGrant>` (K5), sorted by `part`; empty under schema 7 and when absent.
```

`builder_keys.rs` gains:

```rust
/// K1 and K2: a sorted list of period services of the scenario, each once, none of them in `excluded`. `name` is
/// the key's own name, for the refusal `Profile(name)`. K1 passes no exclusion; K2 passes the admitted
/// `place_services`, so `admit` reads `place_services` first and K2 after it.
pub(super) fn service_list(raw: Option<Vec<String>>, schema_8: bool, goods: &BTreeMap<String, GameCommodity>,
    excluded: &[String], name: &str) -> Result<Vec<String>, Error>;
/// A domestic part's label: `<hub geoid>` or `<hub geoid>/<none|below|at|above>`, the hub a county that
/// `EconomicLocation::domestic_county` admits.
fn domestic_part_label_ok(place: &str) -> bool;
```

`admission.rs`: `shares(name, rows, goods)` becomes `shares(name, rows, goods, crossing: &[String])`, and the
crossing list is admitted before the counterparts (decision 3).

**Decisions:**
1. **TOML shape** (schema 8, every key optional unless named):
   - K1: `[markets] crossing_services = ["business_services"]`. K2: `[markets] country_services = ["business_services",
     "leisure", "utility"]`. Each entry a period service of the scenario (`CommodityKind::PeriodService`), each once.
     The list is read sorted, whatever its written order.
   - K3 (E8): a `[[programs]]` row of `kind = "own_needs"` has `rank`, `share_bps` and `recipients`, and no
     `amount_per_person_micros`, `wage_share_bps` or `half_periods`. `RawProgram` loses `amounts_micros` (so the key
     anywhere is unknown, and `deny_unknown_fields` refuses it as `Syntax`). `no_earner` is `per_person` (as built) or
     `own_needs`; `residence` is `own_needs` only; `laid_off` is `after_layoff` (as built). `per_person_by_place` is
     refused. Under schema 8 the rows are `laid_off` and `no_earner`, each once, with or without `residence`: two or
     three rows (`programs` today wants exactly three).
   - K4: `[fund] share_by_part = { "<part label>" = <bps>, ... }` (`RawFund` gains `share_by_part:
     Option<BTreeMap<String, u16>>`).
   - K5: `[[place_grants]]` rows of `part = "<part label>"` and `amount_per_period_micros` (`RawPolicy` gains
     `place_grants: Option<Vec<RawPlaceGrant>>`, `deny_unknown_fields`).
2. **Refused under schema 7 and earlier** (`Shape`), each in turn: `crossing_services`, `country_services`,
   `share_by_part`, a `[[place_grants]]` table. (An `own_needs` row is refused there already: every `[[programs]]`
   row is, Task 1.)
3. **Shares of a crossing service** (K1). Under schema 8, `[markets] import_bps` and every `[counterpart.<key>]` and
   `[dependency]` `export_bps` hold exactly the five priced storable goods and each crossing service: a table that
   lacks one, or names a service that is not crossing, is `Profile("import_bps")` or `Profile("export_bps")`, as a
   wrong good is today. `parse` admits `crossing_services` right after `commodities` (it needs the goods) and before
   `counterparts` and `dependency`, and passes the list to `shares` there and in `markets`.
4. **Values refused**, each with its error:
   - K1 or K2: an entry that is no period service of the scenario (a storable good, `resource_deposit`, an unknown
     key), or named twice: `Profile("crossing_services")` or `Profile("country_services")`; a country service that
     is also in `place_services`: `Profile("country_services")`.
   - K3: `share_bps` 0 or above `MAX_GAME_PROGRAM_SHARE_BPS`: `Profile("program")`; an `own_needs` row with
     `amount_per_person_micros`, `wage_share_bps` or `half_periods`, or without `share_bps`: `Shape`; `residence` as
     `per_person` or `per_person_by_place`, `no_earner` as `per_person_by_place` or `after_layoff`:
     `Profile("program")` (a kind that does not match its key, Task 1 decision 3); a row missing `laid_off` or
     `no_earner`, or one of the three twice: `Shape` as today for a wrong count, `Profile("program")` for a key twice
     (as built).
   - K4: a key whose place has not the form of a domestic part's label: `Location`; a value above 10,000:
     `Profile("fund")`.
   - K5: a `part` that has not the form of a domestic part's label: `Location`; an amount not above 0, or a part
     twice: `Profile("place_grants")`.
   Admission reads the scenario alone: it checks a label's form. Task 4 refuses a label that names no part of the
   opening, a table of shares that leaves a domestic part out, and a grant larger than the part's grants
   (`NationalOpeningError::Policy`).
5. **The fixture's one edit.** Its `residence` row goes (E8: its table was empty, so it paid nobody); its
   `no_earner` row stays `per_person`. K1, K2, K4 and K5 stay absent, so the fixture's opening is today's: every
   stage 2 pin and every pin of Tasks 1 to 3c holds, and nothing in the compiled opening moves (no reader of a
   program exists before Task 4). A test that needs a key sets it on a copy of the fixture's text
   edited in the test, as the built tests do.
6. **Readers.** Nothing in `src/` reads a program's terms, the fund's table, a grant row, `crossing_services` or
   `country_services` before Tasks 4, 7b and 7e, so no reader maps a new field: those tasks read them. The only
   source change outside the policy is the re-export of `GamePlaceGrant`, `MAX_GAME_PROGRAM_SHARE_BPS` and the two byte
   bounds in `policy.rs` and `national_economy.rs`, and the removal of `PerPersonByPlace` (no reader in `src/`; `rg -n
   'PerPersonByPlace|per_person_by_place' rust/crates` must find nothing after this task but the refusal's test).
7. **Bytes.** Under schema 7 every new key is refused, so the shipped policy parses to the same value and every pin
   of `binary(shipped_world_bytes)` holds. The fixture's `source_digest` changes with its text (its residence row);
   a pin that holds the fixture's policy digest is re-pinned from the first failing run and listed in the hand-over
   with its old and new value. No other pin moves; if one does, stop and tell the lead.
8. **The size bound** (E4). The schema is not known until the text is parsed, so the bound is read in two steps,
   keeping every refusal of today for the same text: (a) a text above `MAX_POLICY_BYTES_SCHEMA_8` is `Bounds`, as
   before it is parsed; (b) a text above `MAX_POLICY_BYTES` is parsed, and if the parse fails (any `Syntax` fault of
   `toml::from_str`) or its `schema_version` is below 8, it is `Bounds`, never `Syntax` or a later refusal: today
   every such text is `Bounds`; (c) every other text is admitted as today. `from_captured_bytes` refuses bytes above
   `MAX_POLICY_BYTES_SCHEMA_8` (`Bounds`), and bytes above `MAX_POLICY_BYTES` that are not UTF-8 are `Bounds`, not
   `Syntax`; then `parse` as above. So a text of 65,536 bytes or fewer, and any text of schema 7 or earlier, gives
   exactly today's result. Task 13's `POLICY_BOUND` follows (262,144).

- [ ] **Step 1: Write the failing tests** in `national_game_policy.rs`:
  - `the_fixture_takes_the_fund_and_the_programs` (amend the built test): `fund` has shares (0, 0),
    `reserve_periods == 2` and an empty `share_by_part`; `programs` holds `laid_off` and `no_earner` only (two rows,
    the built `PerPerson` and `AfterLayoff` terms); `place_grants`, `crossing_services` and `country_services` are
    empty.
  - `the_shipped_policy_keeps_its_arms` (amend): `crossing_services`, `country_services` and `place_grants` empty.
  - `the_keys_of_26_november_are_refused_under_schema_7`: the shipped file plus, each in turn, `crossing_services =
    ["business_services"]` and `country_services = ["utility"]` under `[markets]`, a `[[place_grants]]` row `part =
    "26163"`, `amount_per_period_micros = 1`, gives `Err(Shape)`. A `share_by_part` cannot be written under schema
    7: a `[fund]` table is refused there whole (Task 1), which `builder_keys_are_refused_under_schema_7` holds.
  - `a_crossing_service_has_its_shares`: the fixture with `crossing_services = ["business_services"]` and
    `business_services = 1500` added to `import_bps` and `business_services = 1000` to every `export_bps` parses, with
    `crossing_services == ["business_services"]`, six rows in `import_bps` and in Canada's `export_bps`; the same
    without the row in `import_bps` is `Err(Profile("import_bps"))`; without it in Canada's `export_bps`,
    `Err(Profile("export_bps"))`; the fixture with a `business_services` row in `import_bps` and no
    `crossing_services`, `Err(Profile("import_bps"))`; `crossing_services = ["food"]`,
    `Err(Profile("crossing_services"))`; `["leisure", "leisure"]`, `Err(Profile("crossing_services"))`.
  - `country_services_are_read_sorted`: `country_services = ["utility", "business_services", "leisure"]` reads as
    `["business_services", "leisure", "utility"]`; `["housing"]` (a place service of the fixture) is
    `Err(Profile("country_services"))`; `["materials"]`, `Err(Profile("country_services"))`.
  - `own_needs_rows_are_read`: the fixture with a `residence` row `kind = "own_needs"`, `rank = 0`, `share_bps =
    10000`, `recipients = "collective_residence_at_opening"` gives three programs, the third `OwnNeeds { share_bps:
    10_000 }`; the `no_earner` row as `kind = "own_needs"`, `share_bps = 9000` and no `amount_per_person_micros` gives
    `OwnNeeds { share_bps: 9_000 }`. Refused: `share_bps = 0` and `share_bps = 100001`, `Profile("program")`; a
    `residence` row as `kind = "per_person_by_place"` or `"per_person"`, `Profile("program")`; an `own_needs` row
    with `amount_per_person_micros`, `Shape`; one with `amounts_micros = {}`, `Syntax`; the programs without
    `no_earner`, `Shape`.
  - `a_policy_of_schema_8_may_be_larger` (E4): the fixture's text padded with comment lines to 70,000 bytes parses;
    to 262,145 bytes is `Err(Bounds)`; the shipped text padded to 70,000 bytes is `Err(Bounds)` as today; a text of
    70,000 bytes that is not TOML is `Err(Bounds)` as today; the same through `from_captured_bytes`.
  - `a_part_s_share_and_grant_are_read`: the fixture with `share_by_part = { "26163" = 2600, "01073/below" = 0 }` in
    `[fund]` and two `[[place_grants]]` rows (`"26163"` at 5,000,000 micros, `"01073/below"` at 7,000,000) gives that
    table and `place_grants == [GamePlaceGrant { "01073/below", $7.00 }, GamePlaceGrant { "26163", $5.00 }]`.
    Refused: a share of 10,001, `Profile("fund")`; a share for `"canada"`, `Location`; a grant of 0,
    `Profile("place_grants")`; the same part twice, `Profile("place_grants")`; a grant for `"01073/north"`,
    `Location`.
  - `residence_amounts_and_luxury_scales_are_read` (the built test): its `amounts` closure and its three cases on
    `PerPersonByPlace`, `"99999"` and `{ "26163" = 0 }` go (the fixture has no residence row); its luxury-scale and
    `place_services` cases stay.
  - The built tests whose anchors the residence row held (`national_game_policy.rs` at `6f392489e`):
    `schema_8_needs_the_builder_keys` builds `no_programs` with `remove_between(TWELVE, "[[programs]]",
    "amounts_micros = {}\n")` (L959): it now removes up to `recipients = "no_earner_at_opening"\n`; its `two_programs`
    (L960-962, anchored on `"[[programs]]\nkey = \"residence\""`) becomes `one_program`, the fixture with its
    `no_earner` row removed (`laid_off` alone), still `Err(Shape)`. `bad_builder_values_are_refused`'s two cases on
    `key = "residence"` (L1028-1029) no longer change the text: they become `key = "no_earner"` to `key = "other"` and
    to `key = "laid_off"` (a key twice), each `Err(Profile("program"))`. `the_fixture_takes_the_fund_and_the_programs`
    (L784) keeps two keys, as above.
- [ ] **Step 2: Run them and see them fail.** `-p babylon-persistence -E 'binary(national_game_policy)'`: does not
  compile.
- [ ] **Step 3: Implement** decisions 1 to 8 and the fixture's edit.
- [ ] **Step 4: Run** `binary(national_game_policy)`, `binary(national_twelve_trades)`, `binary(national_opening)`,
  `binary(shipped_world_bytes)`, `binary(national_household_units)`, the crate. Expected: pass, no pinned value moved
  but the fixture's policy digest where a pin holds it (decision 7).
- [ ] **Step 5: Gate and commit** with the subject above. Hand over: each pin that moved, old and new.

What the player would see: nothing; no road to the screen before the game's own turn carries schema 8.

### Task 4a: A program pays each recipient its own amount (the engine)

Commit `feat(material-circuit): a program may pay each recipient its own amount a person`.

**Why, read from the code (`1a97bf28a`).** The Director ruled that the benefit is what the needs cost in each
place ("nobody with no earner opens going without, and nobody is paid above their needs. It is still one rule, 'the
needs in full', which politics can cut or raise as a percentage"), and the lead's D1 and D2 make it each account's
own amount. An engine program has one amount for every recipient: `PublicProgramTerms::PerPerson {
amount_per_person }` (`financial/model.rs` L191-199), owed `amount x persons` of each recipient's cohort
(`financial/programs.rs` `program_dues`, L21-77). A program row for each part would pass the engine's 256 programs
(316 parts, `MAX_PUBLIC_PROGRAMS`), and the plan's V3 road (a) does not fit accounts of one part that pay different
prices. So the engine gains a third kind of terms, as D2 names it, and the country's opening keeps three programs.

What it touches, read from the code:
- `financial/model.rs`: `PublicProgramTerms` (tag 1 `PerPerson`, tag 2 `AfterLayoff`) is `Copy` and stays so;
  `PublicProgram` (L202-213) gains a field.
- `financial/programs.rs` `program_dues`: a `match program.terms` for each recipient (L44-58).
- `financial/validation.rs` `validate_programs` (L190-249): a `match program.terms`; `canonicalize` (L14-30) sorts
  each program's recipients (L27-29), so an amount kept beside a recipient must be sorted with it.
- `wire/financial.rs` `append_programs` and `decode_programs` (L100-167): a tag byte and the terms, then a `u32`
  count of recipients and 32 bytes each. The programs are written only in the tail of state versions 25 and 26
  (`has_public_program_extension`, `model.rs` L144-153; `wire/state.rs` L37-54), and only then.
- `financial/layoffs.rs` (L10-40) reads `AfterLayoff` only, with `matches!` and `if let`: unchanged.
- `contracts/material_circuit_v4.yaml` L1046-1069 (`public_programs`) and `MATERIAL_CIRCUIT_SOURCE_SHA256`
  (`wire/state.rs` L31), checked by `tests/weighted_freight.rs` L382-385.
- Every `PublicProgram {` literal of the workspace (`rg -n 'PublicProgram \{' rust/crates`): the engine's own
  tests in `programs.rs` and `validation.rs`, `tests/small_world/support.rs` (two),
  `tests/support/household_time_cases.rs`, `babylon-circuit-worlds/src/doubled/opening.rs` (two) and
  `babylon-persistence/tests/support/country_fund.rs` (two).

**Files:**
- Modify: `rust/crates/babylon-material-circuit/src/financial/{model.rs, programs.rs, validation.rs}`,
  `src/wire/financial.rs`, `src/wire/state.rs` (the digest), `contracts/material_circuit_v4.yaml`; the literals
  above gain `own_amounts: vec![]`
- Test: the crate tests of `programs.rs`, `validation.rs` and `wire/financial.rs`

**Interfaces:**

```rust
/// What a program pays; its kind is fixed and its figures may change.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PublicProgramTerms {
    /// For each person of the recipient account's cohort (tag 1).
    PerPerson { amount_per_person: Currency },
    /// A share of the pay lost, for a worker laid off in play (tag 2).
    AfterLayoff { wage_share_bps: u16, half_periods: u16 },
    /// For each person of the recipient's cohort, the recipient's own amount (`PublicProgram::own_amounts`)
    /// times `share_bps / 10_000`, rounded down (tag 3). The amounts are fixed; the share may change.
    PerPersonOwn { share_bps: u32 },
}
/// The most a tag-3 share may be: ten times the amounts.
pub const MAX_PROGRAM_SHARE_BPS: u32 = 100_000;
pub struct PublicProgram {
    pub key: PublicProgramKey,
    pub payer: PublicAccountId,
    pub rank: u32,
    pub terms: PublicProgramTerms,
    /// May change. Each is the principal of a household account.
    pub recipients: Vec<FinalDemandPrincipalId>,
    /// Under tag 3 one amount a person for each recipient, in the recipients' order; empty under tags 1 and 2.
    /// Each amount is fixed for its recipient: a change of recipients adds or removes a recipient with its amount.
    pub own_amounts: Vec<Currency>,
}
```

**Decisions:**
1. **The due** of a tag-3 recipient: `floor(own amount x persons x share_bps / 10_000)`, the product in `i128` with
   checked multiplication (`Arithmetic` on overflow), the division rounded down (every figure is at least 0).
   `covered_persons` is the cohort's persons, as for tag 1. A cohort of no persons owes nothing. A recipient's own
   amount is read by its place in `recipients`; a recipient without one is `PublicProgramInvariant`.
2. **Validation** (`validate_programs`), beside tag 1's: under tag 3, `share_bps` in `1..=MAX_PROGRAM_SHARE_BPS`,
   `own_amounts.len() == recipients.len()`, every own amount above 0, every recipient with a cohort; under tags 1 and
   2, `own_amounts` empty. Each else `PublicProgramInvariant`. A household may be a recipient of any number of tag-3
   programs, as of tag 1.
3. **Canonical order.** `canonicalize` sorts a program's recipients and its own amounts together, by recipient, so
   each amount stays with its recipient. Under tags 1 and 2 it sorts the recipients as today.
4. **Bytes.** A tag-3 row writes, after the rank, the tag `3` and `share_bps` as `u32` big-endian; then the `u32`
   count of recipients and 32 bytes each, as every tag; then, under tag 3 only, each recipient's own amount as
   `i128` big-endian (16 bytes, as `accounting::decode_currency` reads money) in the recipients' order, with no count
   of its own (it is the recipients'). The decoder reads tag 3 so, refuses an amount not above 0
   (`WireNoncanonical`), and keeps refusing a tag above 3 (`WireEnum`). Why an old state keeps its bytes: the programs
   are written only in the tail of versions 25 and 26, a tag-1 or tag-2 row writes exactly its bytes of today, and
   `own_amounts` is written for tag 3 only; no state version is added, since the tag says what follows. So a state
   with no program of tag 3 writes the bytes it writes today: every measured small world, the shipped world and the
   twelve-trade fixture (whose programs Task 4 makes of tags 1 and 2) keep theirs.
5. **The contract.** `public_programs` gains, letter for letter: `terms_tag_u8: {per_person: 1, after_layoff: 2,
   per_person_own: 3}`; `terms: {..., per_person_own: [share_bps_u32]}`; the row gains `own_amounts_if_tag_3` after
   `recipient_principal_ids`, "one i128 a recipient, in its order"; and a rule: "per_person_own needs share_bps 1 to
   100,000, one own amount above 0 for each recipient and a household cohort row for each; it owes floor(own amount x
   persons x share_bps / 10,000) at the opening of the period, 0 for 0 persons. Tags 1 and 2 hold no own amounts." In
   the form "under schema 7 and earlier ...; under schema 8 ..." where a line speaks of the national scenario.
   `MATERIAL_CIRCUIT_SOURCE_SHA256` is filled once from the failing run of `tests/weighted_freight.rs`.
6. **Every existing construction** gains `own_amounts: vec![]` and keeps its terms; no figure of an existing test
   moves.

- [ ] **Step 1: Write the failing tests.**
  - `own_amounts_are_owed_by_their_share` (`programs.rs` tests): cohorts (1, 3 persons) and (2, 2 persons), a tag-3
    program with recipients [1, 2] and own amounts [$846.00, $1,691.00]: at 10,000 the dues are 2,538,000,000 and
    3,382,000,000 micros; at 9,000, 2,284,200,000 and 3,043,800,000; at 15,000, 3,807,000,000 and 5,073,000,000. One
    micro for 3 persons at 5,000 owes 1 (the floor of 1.5). A cohort of 0 persons owes 0 with `covered_persons` 0.
    An amount of `i128::MAX` for 2 persons is `Err(Arithmetic)`.
  - `a_short_list_of_amounts_is_refused` (`programs.rs` tests): two recipients and one own amount is
    `Err(PublicProgramInvariant)`.
  - `tag_3_is_validated` (`validation.rs` tests, on the two-thousand-recipient state): the same program as tag 3 with
    one amount of 1 micro each validates; `share_bps` 0 and 100,001 are each `Err(PublicProgramInvariant)`, 1 and
    100,000 validate; one own amount of 0, one amount too few, a tag-1 program with one own amount: each
    `Err(PublicProgramInvariant)`.
  - `amounts_are_sorted_with_their_recipients` (`validation.rs` tests): a program written with recipients [2, 1] and
    own amounts [20, 10] canonicalizes to recipients [1, 2] and amounts [10, 20], and its dues are 10 and 20 a person.
  - `a_program_of_own_amounts_round_trips` (`wire/financial.rs` tests): a tag-3 program (key `p`, payer `[9; 32]`, rank
    2, share 10,000, recipients `[1; 32]` and `[2; 32]`, amounts 5 and 7 micros) writes `1u8, b"p", [9; 32], 2u32, 3u8,
    10_000u32, 2u32, [1; 32], [2; 32], 5i128, 7i128` in big-endian after the count of programs, and decodes to the same
    program; the same bytes with a tag of 4 are `Err(WireEnum)`; with an amount of 0, `Err(WireNoncanonical)`.
  - The existing tests of `programs.rs`, `validation.rs`, `close.rs`, `tests/small_world/` (its benefits cases) and
    `babylon-circuit-worlds` keep their literals and their figures; the pins of `binary(shipped_world_bytes)` hold.
- [ ] **Step 2: Run them and see them fail.** `-p babylon-material-circuit -E 'test(financial::) |
  test(wire::financial::)'`: does not compile.
- [ ] **Step 3: Implement** decisions 1 to 6.
- [ ] **Step 4: Run** the `babylon-material-circuit` crate, `-p babylon-circuit-worlds`, `-p babylon-tick`, and of
  `babylon-persistence` `binary(shipped_world_bytes)`, `binary(national_household_units)` and
  `binary(national_twelve_trades)`. Then, in the background and AFTER the last change under
  `babylon-material-circuit/src`, the long tests once: `-p babylon-material-circuit --test adjustment_bench -E
  'test(/^reproduces_/) | test(hours_fold_every_reference_run)' --run-ignored only`. A `reproduces_` test that fails
  is a stop.
- [ ] **Step 5: Gate and commit** with the subject above. Hand over: every literal changed, the contract's changed
  lines, and the digest's old and new value.

What the player would see: nothing yet. Task 4 pays each household with no earner what its own needs cost, and a
later plan shows the benefit and its share on the public-body panel, where politics can cut or raise it.

### Task 4: The national fund, the split taxes, the place grants and the programs (compiler)

Commit `feat(economy): open the national fund, its share of both taxes by part, its grants and its programs`.

**Why, read from the code (`1a97bf28a`).** `opening/financial.rs` `wire` (L19-96) writes one tax row a payer and
basis, to the payer's part (`builder.domain(..).public_account()`), at the scenario's one rate; each domestic
public provider's grant (`public_provider_grant`, L352-391) as a `ProviderOperatingGrant` of its part's body at
priority 0 (L70-92); county support at priority 1 (`household_support`, L131-167); and every part's body as
`CappedInOrder` with its cap the sum of its rows and `working_capital_periods` of it as cash (`public_accounts`,
L98-129). There is no fund and no program. The rulings of 26 November (D2, D4, and E5, E6 and E8 of the second
round) set:
- **the fund's share by part** (ruling 4): a part whose taxes pass its payments sends the rest to the fund, by its
  own entry of `[fund] share_by_part` (K4), the same figure for both taxes;
- **place grants** (ruling 4, D4): where a part's own taxes are too few, the fund pays that part's funded public
  providers directly (`[[place_grants]]`, K5), because one public account cannot pay another: `validate_public`
  (`babylon-material-circuit` `financial/validation.rs` L157-176) admits an allocation as `HouseholdIncomeSupport` to
  a household, `ProviderOperatingGrant` to a site or `AgencyAppropriation` to an organization, from an account with
  a budget, at an amount above 0; allocations are unique by `(public_account, recipient, treatment)` (`structure`,
  L54-56), so the fund and the part's body may each pay one provider;
- **each account's own needs** (ruling 3, D2, E8): three engine programs, `laid_off`, `no_earner` and `residence`,
  the last two of Task 4a's tag 3 when the scenario writes them `own_needs`. The scenario carries the rule, not a
  table: only the compiled opening knows each account's sellers and their posted prices to the micro (a shop's price
  follows the makers it is dealt, Tasks 7d and 14b), so the compiler works out each recipient's amount. Every offer
  is written inside `markets::wire` (`builder.set_offer`, `build.rs` L443-451, called only from `markets.rs` L108 and
  L563 at `6f392489e`), which `finish` runs before `financial::wire` (`build.rs` L280-282); nothing after it writes
  an offer. A household's seller of each product is its purchase row's `retailer_site_id` (its shop of a good, its
  provider of a service, `markets.rs` `households`). A member of a staffing pool names its household and its
  residence (`member.household_id()`, `member.residence()`) and holds its persons `employed` and `reserve`
  (`economic_catalog/model.rs` L218-223), as `financial::wire` reads them for county support (L20-33).
How a budget in proportion orders what it pays (`financial/close.rs` `fund_in_proportion`, L189-223): standing
rows (by `priority`) and programs' dues (by `rank`) are ranked together, sorted `(rank, recipient, order)`, and
`cut::cut_in_proportion` (`financial/cut.rs` L15-47) pays the ranks lowest first, cuts the first rank it cannot
cover in proportion and pays nothing after it. So a grant at a priority above every program's rank is cut before
any benefit ("in a slump the places that live on them are hit first"). Task 1 admits a rank of at most 255.

**Files:**
- Create: `rust/crates/babylon-persistence/src/national_economy/opening/fund.rs`
- Modify: `opening/financial.rs` (`wire`, `household_support`, `support_unit_price`, `public_provider_grant` and its
  call at L71, `public_accounts`); `opening/equipment.rs` (`wear_per_period`); `opening/templates.rs` (`part_label`
  becomes `pub(super)`); `opening.rs` (the module); `opening/build.rs` (the call order:
  `fund::wire` after `financial::wire`); `national_economy/county_review.rs` (it reads `county_support_unit_price`,
  L513 at `6f392489e`); `rust/crates/babylon-persistence/tests/support/country_bench.rs` (L785, where it applies
  `with_fund`); `tests/national_household_units.rs` (L1186-1200, the fund's cash and the programs it records)
- Test: `tests/national_twelve_trades.rs`; `fund.rs` and `equipment.rs` crate tests

**Interfaces:**
- Consumes: `GameFundPolicy` (with `share_by_part`), `GamePlaceGrant`, `GameProgram`, `GameProgramTerms`
  (`OwnNeeds`), `GameMachines` (Tasks 1 and 1b); `PublicProgram` (with
  `own_amounts`), `PublicProgramKey`, `PublicProgramTerms::PerPersonOwn`, `PublicSpendingRule::CashInProportion`
  (engine, Task 4a); `templates::part_label`.
- Produces (`fund.rs` unless named):

```rust
/// The fund's account: `PublicAccountId::from_bytes(sha256_of(b"NationalFundV1\0"))`.
pub(in crate::national_economy) fn fund_account() -> PublicAccountId;
/// Where the fund sits: county 11001.
pub(in crate::national_economy) fn fund_location() -> Result<EconomicLocation>;
/// The priority of a place grant in the fund's budget: above 255, the most a program's rank may be (Task 1), so
/// a short fund cuts every grant before any program.
pub(in crate::national_economy) const PLACE_GRANT_PRIORITY: u32 = 256;
/// A domestic payer's two rows for one tax: the place's share and the fund's.
/// (place, fund): fund = floor(rate x share / 10_000), place = rate - fund.
pub(super) fn split_rate(rate_bps: u16, fund_share_bps: u16) -> (u16, u16);
/// The fund's share of a tax paid in `part` (its label): the part's entry of `share_by_part` when the table is not
/// empty, else the scenario's one share of that basis.
/// # Errors
/// `Policy` for a domestic part missing from a table that is not empty.
pub(super) fn fund_share(fund: &GameFundPolicy, part: &str, basis: TaxBasis) -> Result<u16>;
/// The fund's part of each funded public provider's own grant in one part: `row` dealt over the grants in
/// proportion to each, rounded down, then the micros left one each by largest remainder (equal remainders to the
/// lower site id). The parts sum to `row`; each is at most its grant.
/// # Errors
/// `Policy` for a row not above 0, above the grants' sum, or over no grant; `Arithmetic` on overflow.
pub(super) fn grant_parts(row: Currency, grants: &[(SiteId, Currency)]) -> Result<Vec<(SiteId, Currency)>>;
/// The programs' recipients, by the household keys of the opening, in principal order.
pub(super) fn recipients(builder: &Builder<'_>, rule: GameProgramRecipients) -> Result<Vec<FinalDemandPrincipalId>>;
/// What a household account's needs cost a period at its own sellers' posted opening prices: over the scenario's
/// `household_needs` (a residence's on a person basis only), each need's units for the account's persons or
/// households times the opening `unit_price` of its purchase row's seller of that product.
/// # Errors
/// `Policy` for a need with no purchase row or no offer of its seller; `Arithmetic` on overflow.
pub(super) fn needs_cost(builder: &Builder<'_>, household: &EconomicHouseholdSeed) -> Result<Currency>;
/// What county support pays the account a period at the opening: its `reserve` persons (summed over the staffing
/// members whose household and residence are the account's, as `financial::wire` sums them) times
/// `county_support_unit_price` (decision 9). 0 with no reserve person.
pub(super) fn county_support(builder: &Builder<'_>, household: &EconomicHouseholdSeed) -> Result<Currency>;
/// The account's own amount a person (decision 5, "the rule of own needs"), from its figures alone: `cost` its
/// needs' cost, `support` its county support, `persons`, and `jobless` (for a residence; `None` for a no-earner
/// account). `None` when it is no recipient.
pub(super) fn own_need_amount(cost: Currency, support: Currency, persons: u64, jobless: Option<u64>)
    -> Result<Option<Currency>>;
/// `own_need_amount` on the account's `needs_cost`, `county_support`, persons and, for a residence, its persons
/// with no job at the opening (`persons` less the `employed` of the staffing members whose household is the
/// account).
pub(super) fn own_amount(builder: &Builder<'_>, household: &EconomicHouseholdSeed, residence: bool)
    -> Result<Option<Currency>>;
// fund.rs also holds: const _: () = assert!(MAX_GAME_PROGRAM_SHARE_BPS ==
// babylon_material_circuit::MAX_PROGRAM_SHARE_BPS);
pub(super) fn wire(builder: &mut Builder<'_>) -> Result<()>;
/// (equipment.rs) One period of a site's machines' wear under schema 8: the machines `machine_units` gives for
/// `actor.force`, times the equipment's opening price at the actor's price scale, over `machine_life_periods`,
/// rounded up. Task 6 keeps this signature; its count follows Task 6's rule.
pub(super) fn wear_per_period(builder: &Builder<'_>, actor: &ActorContext) -> Result<Currency>;
/// (equipment.rs) Its arithmetic: ceil(machines x price / life_periods). `Arithmetic` on overflow or a life of 0.
fn wear(machines: u64, price: Currency, life_periods: u64) -> Result<Currency>;
```

**Decisions:**
1. **The fund** (stage 4's later plan B, item 1): one public account, `fund_account()`, located at
   `fund_location()`, its budget `PublicBudget { period_cap: 0, cash_floor: 0, rule: CashInProportion }`. Foreign
   regions and dependencies hold no program and pay no fund row.
2. **The split by part** (ruling 4, K4). For each tax row whose payer is domestic: the share is `fund_share(fund,
   label, basis)`, `label` the `part_label` of the payer's part (a household's own domain, a site's own domain), and
   `split_rate(rate, share)` gives the fund `floor(rate x share / 10_000)` and the part `rate - fund`, so a payer's two
   rows sum to its rate. A fund rate of 0 makes no fund row. With `share_by_part` empty the share is the scenario's one
   share of that tax, the same in every part (as approved, O12). With it not empty: every domestic part of the
   opening must have an entry, and an entry whose label is no part of the opening is refused; each
   `NationalOpeningError::Policy`. The count must stay under `MAX_TAX_POLICIES` (262,144); rows sorted by `(payer,
   basis, public_recipient)`.
3. **The place grants** (D4, K5). For each `[[place_grants]]` row: the part (`part_label` equal to the row's `part`;
   a row that names no part of the opening is `Policy`); its funded public providers, the sites of that part with a
   `ProviderOperatingGrant` of its own body above 0 (`public_provider_grant`, decision 8, in site order), BUT the City
   PD's payroll site, whose grant stays wholly its own body's (`city_pd.rs` `payroll_grant` L367-390 sums only
   Wayne's own body's grant to that site and refuses one smaller than the payroll; the site is `payroll_site`,
   L298-330, Wayne's local-government public provider with the most employee persons); and `grant_parts(row,
   grants)` over the others. A row larger than their grants together is `Policy`. The fund pays each provider its part
   as a `PublicAllocation { public_account:
   fund_account(), recipient: Site, treatment: ProviderOperatingGrant, priority: PLACE_GRANT_PRIORITY,
   amount_per_period: part }` (a part of 0 makes no row), and the part's own body pays each of them that much less:
   its row is `grant - part`, and none when that is 0. So every provider's grant is what it would be. The part's
   body's cap follows its rows as today, so it falls by the row, and its opening cash (`working_capital_periods` x
   the cap, `public_accounts`) by `working_capital_periods` x the row. `financial::wire` computes the grants first, then
   calls `fund::grant_parts` for the
   parts with a row, before `add_budget` and `public_accounts`. A row reaches provision only: county support, the
   County Review's relief and the City PD stay the part's own (V2's road (b)). A part with a row and a share above
   0 in `share_by_part` is admitted (it is the builder's to write share 0 there, D4); the opening report shows it.
4. **The places' bodies** keep the capped rule and their rows (plan B item 3): provision grants (less the fund's
   parts), county support, the County Review's relief, the City PD. The County Review's account holds no program (W15
   of the bench's plan).
5. **The programs** (plan B item 4; call 18; D2, E8), payer the fund, keys and ranks from the scenario, at most three:
   - `laid_off`: `AfterLayoff`, its recipients every domestic account whose key is `EarningLowerPaidHalf`,
     `EarningBetterPaidForty`, `EarningOwner` or `CollectiveResidence` (the aid donor is `EarningLowerPaidHalf`).
   - `no_earner`: its recipients every domestic account whose key is `NoEarnerNonowner` or `NoEarnerOwner`. Its
     terms: `PerPerson` as written for a `per_person` row (one amount, as the fixture has it); for an `own_needs` row,
     `PerPersonOwn { share_bps }`, each recipient's own amount `own_amount(.., false)`; an account of no persons is
     no recipient.
   **The rule of own needs** (E8 with the lead's decision on finding A-S6; Part II's estimate follows it word for
   word). Let `C` be the account's needs' cost a period at its own sellers' posted opening prices (`needs_cost`), `S`
   its county support a period at the opening (`county_support`: what `financial::wire` `household_support` allocates
   the account, its `reserve` persons times the county support unit of decision 9, `reserve x
   reserve_food_support_periods x the food need's units a person x the food commodity's opening price`, the
   scenario's national price at the county scale 10,000, `support_unit_price`, never the account's own shop's price),
   `P` its persons. A no-earner account's own amount a person is `max(1, ceil((C - S) / P))` micros: the
   needs less what county support already pays, over its persons, rounded up, at least 1 micro a person. A
   residence's, with `J` its persons with no job at the opening and `C` its person-basis needs' cost, is `max(1,
   ceil((C x J - S x P) / P^2))`: its jobless residents' needs (`C x J / P`) less its county support, over its
   persons. An account with `P = 0`, or a residence with `J = 0`, is no recipient. So, at `share_bps` 10,000, the
   account's whole public income at the opening (the program's due `amount x P` and its county support `S`) is
   at least its needs and less than its needs plus `P` micros, but where `S` alone passes its needs (then the due is
   1 micro a person). Those looking for work keep the county's support (call 16), and the fund brings the account up
   to its needs in full and not above (ruling 3).
   - `residence` (only when the scenario has the row): `PerPersonOwn { share_bps }`, its recipients the domestic
     `CollectiveResidence` accounts with a jobless resident at the opening, each with `own_amount(.., true)`. No
     such account, or no row, makes no `residence` program (the engine refuses a program with no recipient); the
     fixture has no row (Task 1b), so its opening has two programs.
   **The amounts are filled in `fund::wire`, after `financial::wire`,** so after every offer of the opening is final
   (the "Why"), and written to the engine program's `own_amounts` in the recipients' order. They follow whatever a
   later task does to prices (Task 14b's own prices and the shop's paid price) with no change here. A residence's
   needs are those on a person basis (none on a household basis, as `markets.rs` `purchases` leaves them out), for
   the share of its residents with no job at the opening (call 18). An account
   carved from another (an aid recipient, the support claimant, `NoEarnerNonowner`: `opening/aid.rs` `child`,
   `opening/claimant.rs` `BUDGET`) is a recipient of its own, with its own amount from its own purchase rows (E8). A
   residence is a recipient of `laid_off` and, when it has a jobless resident and the row exists, of `residence` (the
   engine allows one after-layoff program a household and any number of the others,
   `financial/validation.rs`). Each domestic account is in its programs by what it was at the opening (O12; call
   14: owner or not). No layoff record at the opening (plan B item 5): those looking for work keep today's county
   support (call 16). The programs are within `MAX_PUBLIC_PROGRAMS` (256) and their recipients within
   `MAX_MATERIAL_CIRCUIT_ROWS`; more is `NationalOpeningError::Bounds`.
6. **The fund's cash** (O13, "two periods of its payments"): `reserve_periods x` (the dues at the opening of
   `no_earner` and `residence`, each recipient's due by the engine's rule at its cohort's persons, plus the sum of
   the place grants' rows). It is opening cash, not carved out of the places' bodies. (`laid_off` owes nothing at the
   opening: no record.)
7. **The order of a short fund.** Every program's rank is at most 255 (Task 1); every place grant stands at
   `PLACE_GRANT_PRIORITY` (256). The engine ranks the fund's rows and dues together and cuts the first rank it cannot
   cover (the "Why" above), so a fund that cannot pay all pays every benefit first and cuts the grants.
8. **A public provider's grant covers its wear** (schema 8). Today the grant is `max(0, payroll + inputs at planned
   batches - fee receipts)` (`public_provider_grant`). Under schema 8 it is `max(0, payroll + inputs +
   wear_per_period - fee receipts)`, so a public provider replaces its machines as a private workplace does from its
   margin. Under schema 7 the grant is today's. Until Task 6, `machine_units` counts machines by today's rule through
   Task 1's helper; Task 6 changes the count and the grant follows it.
9. **The support unit under schema 8.** Today one person's support is `reserve_food_support_periods x` one unit of
   food (`support_unit_price`). Under schema 8 it is `reserve_food_support_periods x food need units_per_basis x` the
   food commodity's opening price (`support_unit_price` reads `policy.commodities["food"].price`, scaled at 10,000 for
   a county; Task 14b's own prices do not reach it): one period of one person's food need. The County Review's unit
   follows (`county_review.rs` reads
   `county_support_unit_price`). Under schema 7 both are today's.
10. **Both taxes' rates** are the scenario's `[financial]` figures, as today.
11. **The fixture's pins.** The fixture has no `share_by_part` and no grant row, its fund shares are 0, its
   `no_earner` row is `per_person` and it has no `residence` row (Task 1b): its tax rows keep their values, and its
   opening gains the fund's account,
   budget and cash and two programs (`laid_off`, and `no_earner` of tag 1), and its public providers' grants gain
   their wear. A stage 2 pin that counts public accounts, budgets or institutional cash, or values a grant, is
   re-pinned from the first failing run and listed in the hand-over with its old and new value;
   `the_twelve_trades_sizes` of `national_household_units.rs` is re-pinned the same way and listed; every other pin
   keeps its value. No tag-3 program is in the fixture's opening, so its state's bytes follow Task 4a's old path.
12. **The bench keeps an opening's own fund.** `country_bench.rs` (L785) applies `country_fund::with_fund` only
   to an opening that holds no `PublicProgram`; an opening that carries its own fund and programs keeps them, since
   `with_fund` would push a second public account, re-split every tax row and replace `programs`
   (`tests/support/country_fund.rs:248-310`). The shipped world holds no program and is funded as today. The
   bench's recorder (`national_household_units.rs` L1186-1200) reads the fund's cash at `country_fund::fund_account()`
   whenever `no_earner_per_person()` is `Some`, and records only `[NO_EARNER, LAID_OFF]`: for an opening that keeps
   its own fund, `no_earner_per_person()` is `None`, the cash is read at `fund::fund_account()` (made `pub` through
   `national_economy`), and `benefits_record` is given every program of the opening, `residence` included.
13. **Under schema 7** no fund, no split, no grant row and no program are written, and every byte of the shipped world
   stays (`binary(shipped_world_bytes)`).

- [ ] **Step 1: Write the failing tests.**
  - `split_rate_keeps_each_rate` (`fund.rs`), results as (place, fund): `(2320, 2530)` gives (1,734, 586); `(1,
    5000)` gives (1, 0); for every rate 0 to 10,000 and shares 0, 2,530 and 10,000 the parts sum to the rate.
  - `grant_parts_follow_each_grant` (`fund.rs`): $100.00 over grants $60.00, $30.00, $10.00 gives the same three; 5
    micros over 3, 3 and 3 micros (sites 1, 2, 3) gives 2, 2, 1; 9 over 3, 3, 3 gives 3, 3, 3; 10 over 3, 3, 3 is
    `Err(Policy)`; 0 is `Err(Policy)`; 1 over no grant is `Err(Policy)`; 7 over 5 and 2 gives 5 and 2.
  - `fund_share_reads_the_part` (`fund.rs`): with `share_by_part` empty the wage tax's share is
    `wage_tax_share_bps` and the operating income tax's `operating_income_tax_share_bps`; with `{ "26163" = 2600 }`
    both of `"26163"` are 2,600 and `"01073/below"` is `Err(Policy)`.
  - `wear_is_a_period_of_the_machines_life` (`equipment.rs` crate test of `wear`): 100 machines at $1,000.00 and a life
    of 100 periods give $1,000.00; 3 machines at $1.00 and a life of 100 periods give 30,000 micros; 1 machine at
    1,000,001 micros and a life of 100 periods gives 10,001 micros (rounded up).
  - On the fixture with fund shares 2,530 and 2,530 set in the test (`national_twelve_trades.rs`):
    - `the_fund_takes_its_share_of_each_tax`: every domestic payer has two rows of each basis whose rates sum to its
      rate, one to the fund, and the fund's rate is the same function of the payer's rate in every part; no foreign
      payer has a fund row; the count of rows is printed and below 262,144.
    - `a_part_s_own_share_sets_its_rows`: the fixture with a `share_by_part` table that names every domestic part
      of the opening at 2,530 but Wayne's parts at 0 and one other part at 10,000 (the test writes the table from the
      opening's own labels): every payer of Wayne's parts has no fund row, every payer of the part at 10,000 pays its
      whole rate to the fund, the rest as in the test above. The same table without one part is `Err(Policy)`; with
      an extra entry for a domestic county that is no hub (well formed, so admission takes it, and no part has that
      label; the test picks one from the opening's counties) it is `Err(Policy)`. (`"99999"` would be refused at
      parse, `Location`.)
    - `a_place_grant_is_paid_by_the_fund`: the fixture with one `[[place_grants]]` row for the part of the largest
      public provider's own grant in Wayne, at half the sum of that part's grants (the test reads the grants first,
      from the opening without the row): the fund holds one `ProviderOperatingGrant` for each of the part's funded
      providers, at `PLACE_GRANT_PRIORITY`, summing to the row; each provider's two rows sum to its grant without the
      row; the part's body's cap falls by the row and its opening cash by 2 x the row (`working_capital_periods`); no
      other part's rows move; in Wayne's part the City PD's payroll site keeps its whole grant from its own body. A row
      above the part's grants is
      `Err(Policy)`; a row for a part with no funded provider, `Err(Policy)`.
    - `every_domestic_account_is_in_its_programs` (the fixture with a `residence` row `kind = "own_needs"`, `rank =
      0`, `share_bps = 10000`, `recipients = "collective_residence_at_opening"` added in the test): each domestic
      household account is a recipient as decision 5 says: a no-earner account with persons of `no_earner` alone, an
      earning account of `laid_off` alone, a residence of `laid_off`, and a residence with a jobless resident also of
      `residence`; no foreign account is a recipient.
    - `each_account_is_paid_its_own_needs` (the same copy, with the `no_earner` row as `kind = "own_needs"`,
      `share_bps = 10000`): the programs are of tag 3 with `share_bps` 10,000; for every recipient, the test recomputes
      the cost of its needs from its purchase rows and its sellers' offers and its county support from its reserve
      persons, and its own amount is the rule of own needs (decision 5); its whole public income at the opening
      (`amount x persons` plus its county support) is at least its needs and less than its needs plus `persons`
      micros, or the due is 1 micro a person where the support alone passes the needs; Wayne's carved no-earner accounts
      are recipients with amounts of their own; an account of no
      persons is no recipient. Print the lowest, median and highest amount a person of each program.
    - `own_needs_follow_the_prices` (`fund.rs` crate test of `own_need_amount`): an account's needs of 30 units in
      all at 7 micros and 2 units a household at 5 micros, for 4 persons in 1 household, cost 220 micros: with no
      support, 55 a person; with 2 reserve persons at a support unit of 30 micros (support 60), `ceil(160 / 4) = 40`
      a person, and its whole public income is `160 + 60 = 220`, its needs; the same for 3 persons, `ceil(160 / 3) =
      54`, income `162 + 60 = 222`, under `220 + 3`; a cost of 50 with support 60 gives 1 micro a person. A residence
      of 10 persons, 3 of them with no job, person-basis needs costing 1,000 micros: with no support `ceil(3,000 /
      100) = 30` a person (300, the needs of 3); with 2 reserve persons at 30 (support 60), `ceil((3,000 - 600) / 100)
      = 24`, income `240 + 60 = 300`. No persons, or no jobless resident: `None`.
    - `the_fund_opens_with_two_periods_of_its_payments`: the fund's cash equals `2 x` (the dues of `no_earner` and
      `residence` by the engine's rule, plus the place grants' rows), recomputed in the test; its budget is
      `CashInProportion` with cap 0; no layoff record.
    - `a_short_fund_cuts_the_grants_first`: every fund allocation stands at `PLACE_GRANT_PRIORITY` and every program's
      rank is at most 255 (the engine's cut is held by its own tests, `cut.rs`
      `a_short_rank_is_cut_in_proportion` and `close.rs`).
    - `the_support_unit_is_a_period_of_food`: the county support of one person equals `food units_per_basis x` the
      food price; the shipped policy's is today's (`national_game_policy.rs:402-407` and Task 0's digests of stage 2
      unchanged).
    - `a_public_provider_s_grant_covers_its_wear`: every domestic public provider's grant equals `max(0, payroll +
      inputs + wear_per_period - receipts)`, recomputed in the test; the shipped world's grants are today's
      (`binary(shipped_world_bytes)`).
  - `the_bench_keeps_an_opening_s_own_fund` (`national_household_units.rs`): the fixture's bench opening with
    benefits holds exactly one fund account and the fixture's two programs.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement** decisions 1 to 13.
- [ ] **Step 4: Run** `binary(national_twelve_trades)`, `binary(national_county_review)`, `binary(national_opening)`,
  `binary(shipped_world_bytes)`, `binary(national_household_units)`, the crate.
- [ ] **Step 5: Gate and commit** with the subject above. Hand over: each pin re-pinned, old and new; the count of tax
  rows; the fund's opening cash in the fixture.

What the player would see: each part's body and the national fund as public accounts; the benefits, each
household's own needs, paid and cut; the fund's grants to the poorer parts' clinics and schools, cut first in a
slump (through the client's public-body panel, a later plan; on the bench now).

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
/// buyer's export share of its region (from the United States). `key` is a priced storable good or a crossing
/// service (K1, `policy.crossing_services`; read by Task 7e). Schema 7: the single cap, for a storable good only.
/// # Errors
/// `Policy` for a key in no table (a service that does not cross; under schema 7, any service).
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
5. **A crossing service's share** (K1, Task 1b) is read by the same function: under schema 8 the tables hold each
   crossing service beside the five goods, so `foreign_share_bps(location, "business_services")` is the domestic
   import share or the region's export share. `procure` never asks it for a service (it buys storable goods only).
6. **Task 1's helper goes.** `markets::abroad_bps` (L818-851 at `6f392489e`) has two callers, `procure`
   (`markets.rs` L889) and `equipment.rs` L321 (a process's cap abroad, which decision 2 replaces); both read
   `foreign_share_bps`, and the helper is removed (`rg -n 'abroad_bps' rust/crates` finds nothing after this
   task).

- [ ] **Step 1: Write the failing tests** (fixture; the test sets `import_bps` food 1,102, consumer goods 4,277,
  equipment 4,104, the others 2,500, and Canada's `export_bps` consumer goods 1,000):
  - `imports_follow_each_product`: for a domestic buyer of food with a foreign secondary, the foreign row's cap is
    `floor(required x 1102 / 10_000)` and the domestic row's the rest; for consumer goods, 4,277.
  - `a_foreign_buyer_takes_its_export_share`: a Canadian retailer's domestic row for consumer goods has cap
    `floor(required x 1000 / 10_000)`.
  - `a_crossing_service_has_a_share` (`markets.rs` crate test, on the fixture's policy with `crossing_services =
    ["business_services"]`, `import_bps` business services 1,500 and Canada's `export_bps` business services 1,000):
    `foreign_share_bps` gives 1,500 at county `26163` and 1,000 in Canada; on the fixture as it is, `Err(Policy)` for
    `"business_services"`; on the shipped policy, `Err(Policy)` for `"business_services"` and 2,500 for `"food"`.
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

Commit `feat(economy): deal every buyer of a service a provider in proportion, at home first`.

**Why, counted from the compiled opening (26 November; "What the compiled opening showed").** `service_provider`
(`opening/markets.rs` L665-700 at `1a97bf28a`) gives every buyer at one location the same provider of a service:
the nearest location of its state that has one (a county buyer's candidates are the counties whose geoid shares its
first two digits, L684-689; a foreign or dependency buyer's, its own location), and there the site with the most
people at work (`ProviderLocations::new` sorts each location's sites by `employed`; `ids.first()`). A place has
several: a median of 9 sellers of household services, 7 of business services, 6 of public provision, by part and by
owner. So in the twelve-trade opening 187 of 1,489 makers of household services have a buyer and 64.3% of the
trade's workers are at makers with none; public provision 62.4%, utility 49.0%, premises 31.8%, business services
26.8%. With what buyers ask scaled up to what the nation's makers can make, at most 35.7% of what
household-services workers can make can be sold. The engine holds one provider a buyer and service
(`recurring/validation.rs` `unique` on `(principal_id, good_id, unit_id)`; `services/validation.rs` on
`(buyer_site_id, good_id, unit_id)`), so the mend is in who is given to whom. This task's rule, run on the same
opening outside the engine, reaches 91.9% for household services, against 95.0% if every buyer could share every
seller of its place, and leaves 0.7% of the trade's workers at providers with no buyer.

The Director ruled on 26 November that utility, leisure and business services "are sold across the whole country,
each buyer's demand shared over providers by what they can make" (K2, `country_services`), and the lead's D5 and E1
that they are bought at home first, a buyer staying at home while its home provider's ratio BEFORE it is under the
national level (E1). Counted on the same dump, outside the repository (leisure with a want of every account in
proportion to its persons, since the fixture has no want row):

| Service | Rule | Providers with a buyer | Workers at providers with none | Sold at most | Units dealt out of state |
|---|---|--:|--:|--:|--:|
| Utility | own state (as built before this task) | 634 of 634 | 0.0% | 86.2% | 0.0% |
| Utility | D5 as first written (ratio after) | 634 of 634 | 0.0% | 93.6% | 34.7% |
| Utility | E1 (ratio before), this task | 634 of 634 | 0.0% | 94.4% | 10.0% |
| Leisure | own state | 616 of 929 | 0.3% | 96.3% | 0.0% |
| Leisure | D5 as first written | 703 of 929 | 0.1% | 99.3% | 4.1% |
| Leisure | E1, this task | 724 of 929 | 0.1% | 98.7% | 2.4% |
| Business services | own state | 432 of 1,054 | 0.8% | 82.4% | 0.0% |
| Business services | D5 as first written | 443 of 1,054 | 0.7% | 91.8% | 39.6% |
| Business services | E1, this task | 461 of 1,054 | 0.7% | 91.4% | 11.3% |

The least that must cross a state line, each state's asked units above what its own providers can make: utility
12.5%, leisure 3.3%, business services 15.1%. D5 as first written sent three times that, because a site of a kind of
its own that does not fit under the level goes to the emptiest provider anywhere; with E1 the last buyer a home
provider takes may carry it past the level, and only what is left crosses. Under E1 the workers asked for under half
of what they can make are 0.0%, 0.3% and 2.1% of the three services'.

The engine does not tie a service's buyer and provider to a place: `ServiceConnection` "authorizes service reach
without asserting a geographic path" (ADR264), `services/validation.rs` checks only that the provider makes the
service, the buyer exists and is not the provider, and the owner's restart reads a buyer's provider by its id and
its own price, wherever it is (`adjustment/restart.rs` `PlantTables::provider` L323-332, `maker_cost` L555-574,
`supplier_of` L917-933). Nothing in the bench's readers under `tests/support/` reads a state. So a provider in
another state needs no engine change.

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
/// A stall with nobody at work is `Policy`. With no stall the map is empty: the caller decides (decision 5).
pub(super) fn deal(kinds: &[Vec<Custom>], stalls: &[Stall]) -> Result<BTreeMap<AccountId, SiteId>>;
/// D5: deals a country service over every domestic provider, at home first. Kinds one after another, shares
/// carried as in `deal`. For a kind, the national level is (the shares already dealt to every stall + the shares of
/// this kind) over every stall's persons at work. Inside the kind, the buyers in `deal`'s order: a buyer goes to
/// the stall of its own state for which `deal`'s ratio after it is smallest (ties as in `deal`) when that stall's
/// ratio BEFORE it is under the national level (`dealt x all employed < level shares x employed`, in u128), the
/// buyer carrying it past the level if it must (E1); else it waits. Only that one stall is tested: the buyer waits
/// even when another stall of its state is under the level (reading (a), the lead's on finding A-S7; it is the
/// counted rule). Then the buyers of the kind that waited, in
/// the same order, are dealt over every stall by `deal`'s rule,
/// shares carried. A buyer whose location is not a county has no own state and waits. The same refusals as `deal`.
pub(super) fn deal_at_home_first(kinds: &[Vec<Custom>], stalls: &[Stall]) -> Result<BTreeMap<AccountId, SiteId>>;
/// The providers a domestic buyer at `location` may be dealt for the service `key`: those at its own location for a
/// service of the place (`policy.place_services`); every domestic provider for a service of the country
/// (`policy.country_services`); those of its own state for any other. Where its own location has none, a service of
/// the place takes those of the nearest location of its state that has one, which is the location
/// `service_provider` reads today.
pub(super) fn reach(policy: &NationalGamePolicy, providers: &ProviderLocations, network: &mut Network<'_>,
    key: &str, location: EconomicLocation) -> Result<Vec<SiteId>>;
```

A county's state is `county.geoid().state_fips()` (as `opening/grain_controls.rs` reads it).

**Decisions:**
1. **Under schema 8 only** (the policy's twelve trades, `policy.trades`), for domestic buyers. Under schema 7, and
   for a foreign or dependency buyer under either, `service_provider` is today's and every byte of the shipped
   world stays. (Task 7e deals the buyers that cross the border.)
2. **Kinds of buyers.** For one service: the household accounts are one kind, an account's weight its persons;
   the buying sites of one trade are one kind, a site's weight its `force`. The households are dealt first, then
   the trades in `EconomicFunction`'s order, and a provider's shares are carried from kind to kind. A whole buyer
   cannot be split, so a kind of one or two buyers cannot be spread: carried shares place it where the kinds before
   it left room, and the kinds of few buyers are then spread over the providers as a group, where each dealt afresh
   would pile onto the largest provider. What is in proportion to the providers' people is the sum of the shares,
   and each kind of many buyers. (Goods are dealt otherwise, Task 7d: there a buyer's need can be split, in units.)
   The dealing reads no price and no want amount, and of a recipe only whether a trade buys the service at all: it
   is the same whatever numbers the builder writes, which Task 8's census of who sells to which account depends on.
   A household account is a buyer of every service its needs or its wants name.
3. **Groups.** Buyers that `reach` gives one set of providers are dealt together: a service of the place by
   location, any other service but a country service by state, and a country service as one group over the whole
   country by `deal_at_home_first`. An account carved from another (`builder.aid.children`,
   `builder.support_claimant`: an aid donor or recipient, the support claimant) is not dealt: it takes its parent's
   provider (its parent is at its own location). A collective residence is not dealt a provider of a service it does
   not buy (a need or a want on a household basis).
4. **A country service is bought at home first** (ruling 5, D5, E1). A state's buyers fill their own providers to
   the nation's level (each provider may pass it by the last buyer it takes), and only the rest crosses a state
   line: the map shows the imbalance (Michigan buys power from
   outside, Louisiana sells it), not a tangle. The kinds are those of decision 2. The weights are persons and
   `force`, so the dealing stays free of numbers. K2 refuses a country service that is also a service of the place
   (Task 1b), so `reach` never meets both.
5. **Where nobody sells.** As today: a household account with no provider in reach is `MissingObservation`; a
   buying site with none is left without the input (`producers` skips it). A country service has a provider in
   reach wherever the country has one.
6. **The rows** are today's (`ServiceInputPolicy`, `HouseholdPurchasePolicy`, `ServiceConnection`), with the dealt
   provider in place of `service_provider`'s. No row is added: one provider a buyer and service, as before. A dealt
   provider that is the buyer itself is `Policy` (as `producers` refuses today, L632-634).
7. **The fixture's pins** move wherever a pin reads who sells a service to whom, or follows it (service
   connections, the opening's digests of the twelve trades). The fixture has no `country_services` (Task 1b), so its
   utility, leisure and business services are dealt by state. Each pin is filled once from the first failing run
   and listed in the hand-over with its old and new value. No pin of the shipped world moves.
8. **Thresholds** are the rule's own, counted on the dump of the compiled fixture at `9753016ea` (the "Why"): if a
   test's figure passes its bound, stop and tell the lead with the figures; do not loosen it.

- [ ] **Step 1: Write the failing tests.**
  - `whole_buyers_are_dealt_in_proportion` (crate test): stalls with 60, 30 and 10 at work and one kind of ten
    buyers of weight 10: 6, 3 and 1 buyers. Stalls 50 and 50 with buyers 70 and 30: one each. One stall: every
    buyer. Equal ratios go to the stall at the buyer's own location, then to the lower site id. A stall with
    nobody at work is `Err(Policy)`; no stall gives an empty map.
  - `a_later_kind_goes_where_room_is_left` (crate test): stalls 60 and 40; a first kind of one buyer; a second
    kind of one buyer: the first goes to the stall of 60, the second to the stall of 40.
  - `the_dealing_is_the_same_in_any_order` (crate test): the buyers inside each kind and the stalls shuffled give
    the same map, for `deal` and for `deal_at_home_first`.
  - `a_country_service_is_bought_at_home_first` (crate test of `deal_at_home_first`): stalls A1 (60 at work) and A2
    (20) in county `26163`, B1 (20) in county `22033`; one kind of buyers, in `26163` of weights 50 and 20, in `22033`
    of 30 and 10 (whole 110; shares 1,952,257,861, 780,903,144, 1,171,354,717 and 390,451,572, as the code floors
    them; the level's shares 4,294,967,294 over 100 persons). In order: the 50 goes to A1 (smallest ratio after; A1
    empty, under the level); the 30 to B1 (empty); the 20 to A2 (ratio after `780,903,144 / 20` below A1's
    `2,733,161,005 / 60`; A2 empty); the 10 would go to B1, whose ratio before it is past the level (`1,171,354,717 x
    100 = 117,135,471,700` against `4,294,967,294 x 20 = 85,899,345,880`): it waits, and is then dealt over A1, A2 and
    B1 by `deal`'s rule, ratios after `2,342,709,433 / 60`, `1,171,354,716 / 20`, `1,561,806,289 / 20`: A1 is
    smallest, and the buyer of `22033` crosses to A1. Result: {50: A1, 30: B1, 20: A2, 10: A1}. With `deal` by state
    the same four give {50: A1, 20: A2, 30: B1, 10: B1}. A buyer at a foreign location always waits.
  - `only_the_nearest_ratio_is_tested` (crate test of `deal_at_home_first`, telling reading (a) from (b)): stalls A1
    (100 at work) and A2 (5) in `26163`, B1 (95) in `22033`; one kind, in `26163` buyers of weights 100 and 10, in
    `22033` one of 90 (whole 200; shares 2,147,483,648, 214,748,364 and 1,932,735,283; the level's shares
    4,294,967,295 over 200 persons). The 100 goes to A1 (empty); the 90 to B1 (empty); the 10's smallest ratio after
    is A1's (`2,362,232,012 / 100` against A2's `214,748,364 / 5`), and A1's ratio before it is past the level
    (`2,147,483,648 x 200 = 429,496,729,600` against `4,294,967,295 x 100 = 429,496,729,500`): it waits, although A2
    is empty, and is then dealt by `deal`'s rule to B1 (`2,147,483,647 / 95` is smallest). Result: {100: A1, 90: B1,
    10: B1}; under reading (b) the 10 would go to A2.
  - `every_provider_with_workers_has_a_buyer` (fixture): for each service a household needs, the persons at work
    at domestic providers that no household and no site is dealt to are under 5% of the service's (print each
    share; today's are 27% to 64%, and the rule run outside the engine left under 1%).
  - `a_service_of_the_place_is_bought_in_the_place` (fixture, `place_services` as Task 1 sets them): every domestic
    account whose location has a provider of housing, of household services or of public provision has its
    provider of that service there; an account whose location has none has it at another location of its state;
    some buyer's provider of utility is at another location of its state; no provider is in another state.
  - `country_services_are_bought_across_the_country` (the fixture with `country_services = ["business_services",
    "leisure", "utility"]` and a want of leisure, `tier = "luxury"`, `basis = "persons"`, `units_per_basis = 2`, set in
    the test): for utility, leisure and business services, the persons at work at domestic providers with no buyer
    are under 1% of the service's (counted: 0.0%, 0.1%, 0.7%); the units a period dealt to a provider in another state
    (a household row's need and want, its `maximum_purchase` over `retailer_buffer_periods`; a service input's
    `quantity_per_period`), over all units dealt, are under 11% for utility, under 3% for leisure and under 12% for
    business services (counted on the dump: 10.0%, 2.4%, 11.3%); print each figure and the
    providers with a buyer. Housing,
    household services and public provision are dealt as in the fixture without the key.
  - `carved_accounts_follow_their_parents` (fixture, and the fixture with `country_services` as above): Wayne's
    carved accounts have their parents' providers.
  - `the_shipped_services_are_unchanged`: `binary(shipped_world_bytes)`.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement** decisions 1 to 7.
- [ ] **Step 4: Run** the crate tests, `binary(national_twelve_trades)`, `binary(shipped_world_bytes)`,
  `binary(national_household_units)`, the crate.
- [ ] **Step 5: Gate and commit** with the subject above. Hand over: for each service, the providers with a buyer
  over all providers, and the share of workers at providers with none, before and after; for the three country
  services on the test's copy, those and the share of units dealt out of state.

What the player would see: every clinic, school, landlord and office in a place with customers from the first
period, where today one of each has them all; power, travel and offices sold across state lines where a state
has too little or too much of them.

### Task 7f: A buying workplace may take a service from several providers (the engine)

Commit `feat(material-circuit): a workplace may take a service from several providers, by shares`.

**Why, read from the code (`6f392489e`).** Business services cross the border by shares (the lead's E2): a
buying workplace takes most of its business services from its home provider and a share from a provider across
the border, and a buying workplace abroad its export share from home providers. The engine holds one provider a
buying site and service: the catalog refuses a second row of one `(buyer_site_id, good_id, unit_id)`
(`catalog.rs` L207-209, `has_duplicate`) and sorts the rows by that key (L473-474); `services/validation.rs`
refuses it again (L141-143, `keys.insert`). A buyer's requirement of a service is the sum over its processes of
planned batches times the coefficient (`services/requirements.rs` `input_requirements`), and `required_input`
(L145-157) caps it by its one row: `min(requirement, quantity_per_period, maximum_purchase)`. This task lets a
buying site hold several rows of one service, one a provider, and shares its requirement over them by their caps.
It is the workplaces' half of the plan's V11, brought forward because exports of a service cannot be built without
it; households keep one seller of each thing until V11 is built before homes, as ruled.

**Every reader of a buyer's service inputs, and what it does with two rows** (`git grep -n service_inputs
6f392489e -- rust/crates/babylon-material-circuit/src`):
- `catalog.rs` L207-209 (duplicate check) and L473-474 (canonical sort): the key gains `provider_site_id`, last.
  With one row a buyer and service the order is the same, so the bytes are.
- `catalog.rs` L343-347 (a row's `quantity_per_period` above 0, its floor at least 0): per row, unchanged.
- `services/validation.rs` L137-160 (`validate_policies`: the bound, unique keys, a connection and an offer of the
  row's provider): the unique key gains the provider; the rest is per row and unchanged. L225-240
  (`refuse_unhandled_resale`, per row): unchanged.
- `services/requirements.rs` `required_input` (L145-157), called by `planning_grants` (L77-83, the units of a
  service credited to the buyer's planning stock) and `services/admission.rs` `requests` (L84-100, one request a
  row): today each row takes `min(requirement, cap, maximum)`, so two rows would each take the whole requirement
  and the buyer would order it twice. It becomes the row's share (decision 1). `planning_grants` then credits the
  sum of the shares: the requirement capped at the sum of the caps, less what a row's maximum cuts from its share.
- `services/admission.rs`: a request is already one a row and its order id names the provider
  (`recurring_service_order_id` L28-44), the due commitments are keyed by `(buyer, provider, good, unit)` (L204-245),
  a market is one provider's product (`phase_markets` L394-419), and a buyer's cash is spent across its requests in
  the order of paying (`funded_at_quotes` L477-522, a scratch balance a buyer). With two rows the buyer bids its two
  shares in two providers' markets. Unchanged but for `required_input`.
- `clearing/limit.rs` `cheapest_supplier` (L103-127): a maker's limit price reads the lowest posted price among the
  buyer's restocking suppliers and its service providers of the input; it already iterates every row. With two
  rows it reads the cheaper provider, as it does for a good with two suppliers. Unchanged.
- `adjustment/bound.rs` (the hiring bound): `policy` (L208-213) keeps the FIRST row of `(buyer, good, unit)`;
  `service_inputs` (L292-310) gives one `(coefficient, row)` a service input; `dependencies` (L315-333) adds the
  processes of each row's provider; `maker` (L400-425) caps the batches by `for_me = made - others, min cap, min
  maximum` over `quantity_per_batch`, and adds `quantity_per_batch x` the provider's price to the cost of a batch.
  With two rows the first wins and the second provider is never counted. It becomes: every row (the map keeps all
  rows of a key, in provider order); `dependencies` adds every row's provider; the batches the input allows are
  decision 2's; the cost of a batch adds decision 3's price.
- `adjustment/restart.rs` (the owner's restart): `PlantTables::provider` (L323-332) keeps the first row's
  `(provider, min(cap, maximum))`; `maker_cost` (L555-574) costs an input at that provider's top price;
  `supplier_of` (L917-933) and `inputs_can_be_had` (L881-914) test whether a batch's inputs can be had from that one
  provider (`planned - taken by others, min limit`). With two rows the test reads one provider. It becomes: every row;
  `inputs_can_be_had` for a service by decision 2; `maker_cost` at decision 3's price. A good keeps its one supplier
  here (the first replenishment row), as today.
- `transition/state.rs` L457-459 (service inputs refused without a recurring economy): unchanged.
- `wire/catalog.rs` `append_service_inputs` (L151-163): the row's bytes are today's; the rows come in the new
  canonical order, the same order when a buyer has one row a service. There is no catalog decoder.
- `contracts/material_circuit_v4.yaml` L162 (`service_inputs: [buyer_site_id, good_id, unit_id]`, the canonical
  key) and the lines on the hiring bound (L241-245) and on planning (L751).
No reader needs more than decision 1 to 3, so this is one task.

**Files:**
- Modify: `rust/crates/babylon-material-circuit/src/{catalog.rs, services/requirements.rs, services/admission.rs,
  services/validation.rs, adjustment/bound.rs, adjustment/restart.rs}`, `src/wire/state.rs` (the digest),
  `contracts/material_circuit_v4.yaml`
- Test: `services/requirements.rs` tests; `adjustment/bound.rs` and `adjustment/restart.rs` tests;
  `tests/market_clearing/` (a new module `shared_providers.rs` of that binary)

**Interfaces** (`services/requirements.rs`):

```rust
/// A buyer's requirement of one service shared over its rows of that service, in the rows' order (provider id):
/// the requirement, capped at the sum of the rows' caps (`quantity_per_period`), times a row's cap over that sum,
/// rounded down; the units left over one each to the rows with the largest remainders, the lower provider id on a
/// tie; each row's share then capped by its own `maximum_purchase`. With one row: `min(requirement, cap,
/// maximum_purchase)`, today's figure.
/// # Errors
/// `Arithmetic` on overflow; `ServiceInvariant` for no row.
pub(crate) fn input_shares(requirement: u128, rows: &[&ServiceInputPolicy]) -> Result<Vec<u64>>;
/// Every row's share, by (buyer, provider, good, unit), built once per planning boundary from `input_requirements`.
pub(crate) fn required_inputs(catalog: &MaterialCatalog, requirements: &InputRequirements)
    -> Result<BTreeMap<(SiteId, SiteId, GoodId, UnitId), u64>>;
/// The units of a service `site` can have for its requirement from its rows, each row offering `available[i]` (what
/// the provider can make less what its other buyers take, capped by the row's cap and maximum): a requirement up to
/// which every share fits, min over rows of floor(available[i] x sum of caps / cap[i]); with one row, `available[0]`.
/// It is a safe bound, not always the largest (caps 70 and 30 with availabilities 70 and 10 give 33, and 34, shared
/// 24 and 10, also fits).
pub(crate) fn shared_availability(rows: &[&ServiceInputPolicy], available: &[u64]) -> Result<u64>;
/// The price a buyer pays a unit of a service over its rows: ceil(sum(cap x posted price) / sum of caps); with one
/// row the provider's price.
pub(crate) fn shared_price(rows: &[&ServiceInputPolicy], prices: &[i128]) -> Result<i128>;
```

**Decisions:**
1. **The share** (E2). `R = min(requirement, sum of caps)`; row `i` gets `floor(R x cap_i / C)`, `C` the sum of the
   caps, in u128; the units `R` less the floors go one each to the rows of largest remainder (`R x cap_i mod C`),
   lower provider id first on equal remainders; then `min(share, maximum_purchase_i)`. Hand cases, caps 70 and 30
   (providers in that id order): requirement 100 gives 70 and 30; 50 gives 35 and 15; 51 gives 36 and 15 (floors 35
   and 15, the remainders 70 and 30 of 100, the unit left to the first); 120 gives 70 and 30; caps 70 and 30 with
   maxima 20 and 30 and requirement 100 give 20 and 30 (a maximum cuts its row's share and is not dealt to the
   other). One row: the share is `min(requirement, cap, maximum)` by the same operations (`R = min(requirement,
   cap)`; `R x cap / cap = R`, no remainder), so every catalog of one row a buyer and service keeps every figure.
2. **What can be had** (the hiring bound and the restart's test): a buyer's requirement `R` fits its rows when each
   share fits its row's availability, which holds for `R <= floor(available_i x C / cap_i)` for every row (a
   share is at most `ceil(R x cap_i / C)`, and that is at most `available_i` exactly when `R x cap_i <= available_i x
   C`). So `shared_availability` is the minimum of those, and `maker` caps the batches at it over
   `quantity_per_batch`, as it does today with `for_me`; `inputs_can_be_had` asks it to cover the units the batch
   lacks. With one row it is `available`, today's `for_me`.
3. **The price of an input** for the hiring bound's cost of a batch (`maker`, `quantity_per_batch x` the price) and
   for the restart's `maker_cost`: `shared_price`, the caps' weighted price rounded up (a cost is never
   understated). With one row the provider's own price, as today. Each passes the prices it reads today, one a row:
   the hiring bound each row's provider's posted price (`self.price(provider, ..)`, refused with `PurchaseInvariant`
   when it has none, as today); the restart each row's provider's `own_top` offer. In the restart, when one of the
   rows' providers has no `own_top`, `maker_cost` gives `None` (the input cannot be priced), as it does today for the
   one row; with no row at all it keeps today's fall-back to the product's `top`. The price limit (`clearing/limit.rs`)
   keeps the
   cheapest provider, as it does for a good with several suppliers.
4. **Bytes.** The canonical key of a row is `(buyer_site_id, good_id, unit_id, provider_site_id)`; a catalog with at
   most one row a buyer and service sorts and writes exactly as today, and no state's bytes change (service orders
   already name their provider). Every measured small world, the shipped world and the twelve-trade fixture keep
   their bytes; `binary(shipped_world_bytes)` and the catalog tests' pins hold.
5. **The contract.** L162 becomes `service_inputs: [buyer_site_id, good_id, unit_id, provider_site_id]`; a line is
   added to the service inputs: "A buying site may hold one row a provider of a service; its requirement, capped at
   the rows' caps, is shared over them in proportion to their caps, rounded down, the units left by largest
   remainder (the lower provider id on a tie), each share capped by its row's maximum. With one row the request is
   min(requirement, cap, maximum)." The hiring bound's line (L241-245) gains "over several providers, the batches
   every share allows and the caps' weighted price, rounded up". `MATERIAL_CIRCUIT_SOURCE_SHA256` is filled once from
   the failing run of `tests/weighted_freight.rs`.
6. **No reader multiplies a requirement by a row on its own**: every share comes from `input_shares`, every
   availability from `shared_availability` and every price from `shared_price`. The hand-over lists each call site.

- [ ] **Step 1: Write the failing tests.**
  - `a_requirement_is_shared_by_the_caps` (`requirements.rs` tests): the hand cases of decision 1; three rows of caps
    1, 1 and 1 and a requirement of 2 give 1, 1 and 0 (equal remainders to the lower ids); one row of cap 40 and
    maximum 25: requirements 10, 30 and 50 give 10, 25 and 25 (today's `min`); no row is `Err(ServiceInvariant)`.
  - `what_two_providers_can_give` (`requirements.rs` tests): caps 70 and 30 with availabilities 70 and 30 give 100; 35
    and 30 give 50 (the first row's share passes 35 above 50); 70 and 10 give 33 (`floor(10 x 100 / 30)`); one row of
    availability 17 gives 17.
  - `the_weighted_price_is_rounded_up` (`requirements.rs` tests): caps 70 and 30 at $10.00 and $4.00 give $8.20; caps
    2 and 1 at 10 and 11 micros give 11; one row gives its price.
  - `a_second_row_of_a_provider_is_admitted` (`catalog.rs` tests): two rows of one buyer and service with two
    providers are admitted; two rows of one buyer, service and provider are `Err(DuplicateRow)` (or the duplicate
    refusal `has_duplicate` gives today).
  - `one_row_a_service_keeps_its_bytes` (`catalog.rs` tests, beside `blocks_change_the_catalog_bytes_only_when_used`):
    a catalog fixture with one row a buyer and service has the bytes it had before this task (its pinned digest does
    not move).
  - `a_workplace_buys_from_two_providers` (`shared_providers.rs`): a maker needing 50 units of a service a period,
    with rows of caps 70 and 30 at two providers that each can make 100: it orders 35 and 15, is performed 35 and 15,
    and pays each provider its own price for its share; with the second provider unable to make anything, the hiring
    bound gives the batches that 0 units of the second row's share allow (none), and the restart's test says the
    inputs cannot be had.
  - The existing tests of `binary(market_clearing)`, `adjustment`, `services` and `recurring` keep their literals and
    figures; the pins of `binary(shipped_world_bytes)` hold.
- [ ] **Step 2: Run them and see them fail.** `-p babylon-material-circuit -E 'test(services::) |
  binary(market_clearing)'`.
- [ ] **Step 3: Implement** decisions 1 to 6.
- [ ] **Step 4: Run** the `babylon-material-circuit` crate, `-p babylon-circuit-worlds`, `-p babylon-tick`, and of
  `babylon-persistence` `binary(shipped_world_bytes)`, `binary(national_household_units)` and
  `binary(national_twelve_trades)`. Then, in the background and AFTER the last change under
  `babylon-material-circuit/src`, the long tests once: `-p babylon-material-circuit --test adjustment_bench -E
  'test(/^reproduces_/) | test(hours_fold_every_reference_run)' --run-ignored only`. A `reproduces_` test that fails
  is a stop.
- [ ] **Step 5: Gate and commit** with the subject above. Hand over: every call site of the three functions, the
  contract's changed lines, and the digest's old and new value.

What the player would see: nothing yet. Task 7e uses it: firms that buy part of their offices' work abroad, and
offices that sell part of theirs to firms abroad.

### Task 7e: A business buys a crossing service at home and abroad, by shares (compiler)

Commit `feat(economy): businesses buy and sell a crossing service across the border by shares`.

**Built after Task 7b** (whose home dealing it keeps), **after Task 7f** (the engine admits several providers a
buying site and service, and shares the requirement by caps) **and after Task 5** (it reads `foreign_share_bps`
for a service's key). It builds `Share` and `caps`, which Task 7d then uses for goods too (run B builds Task 7e
before Task 7d), and its own `deal_by_most_room`; Task 7d builds `deal_by_room` (nearness and room, for goods).

**Why, read from the code (`6f392489e`) and counted on the dump of the compiled fixture.** The Director ruled on
26 November that business services cross the border, "by the accounts' own import and export shares". Today no
service crosses: `service_provider` (`opening/markets.rs` L665-700) gives a county buyer a provider of its own
state and a foreign or dependency buyer one at its own location (L688), and Task 7b keeps that for buyers abroad.
Whole buyers cannot cross (the lead's E2, which replaces D3): a region abroad has ONE provider of business services
and five buying sites, one a trade (counted on the dump of the compiled opening, outside the repository: China's
five sites have a force of 319,347,288, the country's 1,054 providers 26,744,137 at work), so one site abroad dealt
to one home provider would ask it for more than the country exports. A service has no geography in the engine, so a
site abroad's export part is dealt by room alone, the home providers with the most room left first (the lead's
decision on finding A-S8): the large office centers sell abroad first. Counted on the dump, outside the
repository (each of the 88 buying sites abroad and in the dependencies exports a part in proportion to its force,
one share for all; the largest of them holds a tenth of all the exports, and the sixteen largest home providers a
quarter of the trade's workers): with at most 16 providers a buyer, 561 rows, 0.4% of the exports land beyond a
provider's room and one small provider is asked 17.2 times its room (the last of a large buyer's sixteen takes
what is left); with no limit, 1,141 rows (the widest buyer takes 90 providers), every home provider is asked exactly
its room, and the rows can never pass the providers plus the buyers less one. So no limit is set: `most` is the
number of the service's domestic providers. With Task 7f a buying
site holds a row a
provider, each with a cap, as a buyer of a good holds a restocking row a supplier (`procure`, L853-903: a home cap
`required - foreign` and a foreign cap `floor(required x share / 10_000)`). A service connection asserts no path
(`ServiceConnection`), so no route is made.

**Files:**
- Modify: `rust/crates/babylon-persistence/src/national_economy/opening/{dealing.rs, markets.rs}` (`producers`, the
  rows of service inputs; `ProviderLocations::secondary_candidates` is read for a service)
- Test: `dealing.rs` crate tests; `tests/national_twelve_trades.rs`

**Interfaces** (`dealing.rs`; `Share` and `caps` are the signatures Task 7d's text gives, built here):

```rust
/// A buyer's share at one maker: `part` of `whole`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(super) struct Share { pub maker: SiteId, pub part: u128, pub whole: u128 }
/// Deals buyers' weights over stalls by room alone. A stall's room is its persons at work over all stalls' times
/// the buyers' whole weight, kept exact in u128 as `employed x whole weight - taken x all stalls' employed`. Buyers in
/// order of weight, largest first, then by account; each takes from the stalls with the MOST room left first (the
/// lower site id on a tie), as much as each has left, up to `most` stalls; the last of them takes whatever is left,
/// past its room if it must. A share's `part` is the weight taken there and its `whole` the buyer's weight.
/// A stall with nobody at work is `Policy`; no stall gives an empty map.
pub(super) fn deal_by_most_room(custom: &[Custom], stalls: &[Stall], most: usize)
    -> Result<BTreeMap<AccountId, Vec<Share>>>;
/// A cap dealt over shares by largest remainder (equal remainders to the lower site id), so that the parts sum to
/// `cap`; a part that comes to 0 gives no row.
pub(super) fn caps(cap: u64, shares: &[Share]) -> Result<Vec<(SiteId, u64)>>;
/// The provider abroad of a domestic buying site of a crossing service: at `crossing_region`'s region, its largest
/// provider (the location's first site, `ProviderLocations::new`'s order). Reads no number of the scenario.
pub(super) fn provider_abroad(providers: &ProviderLocations, buyer: SiteId, location: EconomicLocation)
    -> Result<Option<SiteId>>;
```

`national_economy.rs` gains two public functions, so that Task 8's recorder (an integration test) applies the same
rule to every domestic site (Part II's `crossing_force`):

```rust
/// The foreign regions holding a provider of a product with persons at work, in location order: the list
/// `ProviderLocations::secondary_candidates` rotates for a county buyer (dependencies are not in it).
/// # Errors
/// The region, for a foreign region whose every site making the product has nobody at work: a stop, named.
pub fn crossing_regions(opening: &EconomicOpening, good: GoodId, unit: UnitId)
    -> std::result::Result<Vec<EconomicLocation>, EconomicLocation>;
/// A domestic buyer's region abroad: `regions[u32::from_be_bytes(first four bytes of the site id) % regions.len()]`,
/// the first location of `secondary_candidates`' rotation; `None` with no region. Reads no number.
pub fn crossing_region(regions: &[EconomicLocation], buyer: SiteId) -> Option<EconomicLocation>;
```

**Decisions:**
1. **Under schema 8 only, and only for a key in `policy.crossing_services`** (K1). Under schema 7, and for every
   other service, Task 7b's rows stand, so with `crossing_services` empty (the fixture, Task 1b) every row and pin is
   Task 7b's.
2. **Only businesses cross** (E2). The buyers are the buying sites of the service (a recipe that names it, a
   required quantity above 0, `producers`). Household accounts on both sides keep one provider at home, as Task 7b
   deals them.
3. **A domestic buying site** keeps its dealt home provider (Task 7b) with the cap `required - abroad` and gets one
   more row at `provider_abroad` with the cap `abroad = floor(required x import_bps[key] / 10_000)`
   (`foreign_share_bps`, Task 5); no row abroad when `abroad` is 0 or when no region has a provider. Each row's
   `quantity_per_period` and `maximum_purchase` are its cap; its `cash_floor` the site's payroll, as today. The
   dependencies hold no `secondary_candidates` location (`ProviderLocations::new` L50: a dependency is not a
   candidate abroad), so a domestic site's imports come from a foreign region, as a good's do.
4. **A buying site abroad or in a dependency** keeps its own location's provider with the cap `required - export`,
   and its export part, `export = floor(required x export_bps[key] / 10_000)` of its region (`foreign_share_bps`), is
   dealt over the DOMESTIC providers of the service by room: one `deal_by_most_room` for the service over every
   buying site abroad together, a buyer's weight its `export`, `most` the number of those providers (no limit: the
   count above), room in proportion to the providers'
   persons at work, the providers with the most room left first. No nearness is read: a service has no geography in
   the engine, and no route is needed. Its `export` is dealt over its providers by `caps`, one row a provider, each
   row's cap its part. The dependencies are one side with the foreign regions here (the lead's smaller points). A
   buying site abroad or in a dependency with no provider at its own location is skipped as `producers` skips it today
   (no input, no row), and so is its export part (minor 10: the lead's leaning, taken).
4b. **A region whose provider has nobody at work** (minor 11): `crossing_regions` returns the region's name, and the
   compiler stops with `NationalOpeningError::Policy`; the test prints the region. A region's providers' persons at
   work follow its `function_weights_bps`, and a weight of 0 is refused (Task 1), so this is not expected.
5. **The rows** are `ServiceInputPolicy` and `ServiceConnection` rows, one a (buyer, provider), sorted by the
   engine's key `(buyer_site_id, good_id, unit_id, provider_site_id)` (Task 7f): the sort of `service_inputs` at the
   end of `markets::wire` (`markets.rs` L163-165, today by `(buyer_site_id, good_id, unit_id)`) gains
   `provider_site_id`, which changes no byte where a buyer has one row a service. The engine shares a buyer's
   requirement over its rows by their caps (Task 7f, decision 1), so a buyer's requirement at its planned batches
   goes abroad in its share. A provider that is the buyer itself is `Policy`.
6. **The census.** The household kind is dealt by Task 7b, untouched here, so who sells a service to each account
   does not follow the shares. Task 8 gains one table that reads no number, `crossing_force`: for each crossing
   service, region and domestic trade, the summed `force` of the domestic sites with a process whose
   `crossing_region` is that region (Task 8's amendment, item 5); Task 8 calls `crossing_regions` and
   `crossing_region` on the compiled census scenario, which has no `crossing_services`, so it applies the rule itself.
   `provider_abroad` calls `crossing_region`, so the table and the rows agree. Nothing of the dealing abroad (which
   follows the shares) is in the census.
7. **Bounds.** Service inputs grow by one row a domestic buying site of the service and, for all the buying sites
   abroad together, by at most the domestic providers plus those sites less one (counted on the dump: 1,141 rows
   for the 88 sites, the widest of them 90); connections likewise. Print and pin
   the counts; past `MAX_MATERIAL_CIRCUIT_ROWS` or `MAX_SERVICE_CONNECTIONS`, `NationalOpeningError::Bounds`: stop
   and tell the lead.
8. **The fixture's pins** do not move: the fixture has no `crossing_services`. Tests set the key on a copy.
9. **Bytes.** Under schema 7 nothing changes (`binary(shipped_world_bytes)`).

- [ ] **Step 1: Write the failing tests.**
  - `caps_sum_to_the_cap` (crate test, Task 7d's text, written here; Task 7d keeps it): 10 over parts 1, 1, 1 of 3
    gives 4, 3, 3, the 4 at the lowest site id; a part that comes to 0 gives no row.
  - `the_most_room_goes_first` (crate test of `deal_by_most_room`): stalls A, B, C (site ids in that order) with 60,
    30 and 10 at work; buyers of weight 50, 30 and 20 (rooms 60, 30, 10): the 50 takes 50 of A (A has 10 left); the 30
    takes 30 of B (the most room, 30, against A's and C's 10); the 20 takes 10 of A and 10 of C (A before C on the tie
    of 10). With `most = 1` the 20 takes all 20 of A (70 asked of a room of 60). A stall with nobody at work is
    `Err(Policy)`; no stall gives an empty map.
  - `the_provider_abroad_reads_no_number` (crate test of `crossing_region` and `provider_abroad`): regions [a, b, c]
    and a site id beginning `00 00 00 04` give b (4 mod 3 = 1); `00 00 00 05`, c; no region gives `None`; the same
    buyer gives the same location whatever the order of the providers given; a location with two providers gives the
    one with more at work; `crossing_region` equals the first location `secondary_candidates` gives the same buyer.
  - On the fixture with `crossing_services = ["business_services"]`, `business_services = 1500` in `import_bps` and
    `business_services = 2000` in every `export_bps`, set in the test (`national_twelve_trades.rs`):
    - `a_home_site_buys_its_share_abroad`: every domestic buying site of business services has its home row at
      `required - floor(required x 1500 / 10_000)` with the provider Task 7b deals it (compared with the same opening
      without the three keys) and, where that floor is above 0, one row at a foreign provider with that floor; no
      domestic site has a row in a dependency.
    - `a_site_abroad_buys_its_share_at_home`: every buying site abroad or in a dependency has its own location's
      provider at `required - floor(required x 2000 / 10_000)` and rows at domestic providers whose caps sum to that
      floor; the caps from abroad sum to the export parts; the persons at work at domestic providers asked from
      abroad under half their room are under 1% of the trade's, and over twice under 1% (counted: none and none);
      no provider is asked more than twice its room (counted: exactly its room, each buyer weighed by the quantity
      it asks in the fixture). Print each figure, the rows from abroad, the widest buyer's rows and the providers
      asked. A figure past its bound is a stop: tell the lead; do
      not loosen it.
    - `no_household_crosses`: every household account's provider of business services, if it has one, is on its own
      side of the border.
    - `crossing_rows_fit_their_bounds`: print and pin the counts of service inputs and connections.
  - `the_fixture_crosses_nothing`: on the fixture as it is, no service input or connection has its buyer and its
    provider on two sides of the border.
  - `the_shipped_services_are_unchanged`: `binary(shipped_world_bytes)`.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement** decisions 1 to 9.
- [ ] **Step 4: Run** the crate tests, `binary(national_twelve_trades)`, `binary(shipped_world_bytes)`,
  `binary(national_household_units)`, the crate.
- [ ] **Step 5: Gate and commit** with the subject above. Hand over, for the test's shares: the units a period
  bought abroad by region and the units sold abroad by domestic provider, and the row counts against their bounds.

What the player would see: offices of the country selling part of their work to firms abroad, and firms here buying
part of theirs from offices abroad: a flow of business services on the money map's foreign side, beside goods (when
the game's turn plays schema 8).

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
// `Share` and `caps` are built by Task 7e, which run B builds first, with its crate test `caps_sum_to_the_cap`;
// Task 7d uses them as they are and builds `deal_by_room` (with `buyers_take_the_nearest_room`) and `routable`.
/// A buyer's share at one maker: `part` of `whole`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(super) struct Share { pub maker: SiteId, pub part: u128, pub whole: u128 }
/// Deals buyers' weights over makers by nearness and room. A maker's room is its persons at work over all makers'
/// times the buyers' whole weight, kept exact as `employed x whole weight` against `weight x all makers' employed`.
/// Buyers in order of weight, largest first, then by site id; each takes room from the makers of the nearest
/// location that has room left (`nearest` gives it; inside a location the makers by site id), then the next
/// nearest, up to `most` makers; the last takes whatever is left. So a caller sets `most` to the number of the
/// stalls where no buyer may be dealt past the makers' room (the buyers abroad, decision 3).
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
3. **Goods:** `deal_by_room` with `most = 3` for home buyers. **The buyers abroad have no limit** (amended on 26
   November, in the build): `most` is the number of the dealing's stalls, and its stalls are the good's home
   makers from whose location a route can be built to at least one buyer abroad of the good (`routable`; a maker
   that reaches none holds room nobody could take, so it is no stall of this dealing, and the count of such makers
   and their people is printed for each good). A buyer abroad is a whole region's trade: counted in the first
   build of this task, one buyer abroad of food asks a sixth of all the food asked of home makers, the sixteen
   largest makers hold 29% of the trade's people, and nine tenths of what is asked of home makers is asked from
   abroad. With a limit of sixteen the sixteenth maker took the rest past its room: a maker of 33 people was asked
   4,976 times the nation's ratio. With no limit a buyer takes the nearest room, then the next, until its cap is
   dealt, the rooms are used up together, and the rows of a good's buyers abroad cannot pass its stalls plus
   those buyers less one. The buyer's cap is dealt over its makers by `caps`; each row keeps today's
   `target_stock` and `cash_floor`. A maker is never dealt itself. A domestic buyer's row abroad is today's.
4. **Machines:** one maker a process (the engine's rule): the home buyers of machines are dealt with `most = 1`, a
   process's weight its replacement machines (Task 6). Task 5's rule on which processes buy abroad stays.
5. **Nearness** is the network's own (`Network::nearest`: hops to the buyer's location, by the good's cargo
   class). A maker location is offered to a buyer only where `routable` holds from it to the buyer, so that no
   dealt pair fails `add_stage` (`NationalOpeningError::Route`).
6. **When a buyer wants less than its caps together,** the engine serves its rows in its own order and the last go
   short (`recurring/firms.rs` `position`: each row sees what the rows before it ordered). That is today's rule
   for a home and a foreign supplier; this task leaves it.
7. **Bounds.** Restocking rows and routes grow (up to three home rows a buyer and good; for a good's buyers abroad
   together at most its stalls plus those buyers less one; and a route for each new pair of locations and cargo
   class). Print and pin the counts of restocking rows,
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
  - `caps_sum_to_the_cap` (Task 7e's crate test, already passing; it stays): 10 over parts 1, 1, 1 of 3 gives 4, 3,
    3, the 4 at the lowest site id; a part that comes to 0 gives no row.
  - `every_maker_with_workers_has_a_buyer` (fixture): for food, materials, resources, consumer goods and machines,
    the persons at work at domestic makers no buyer is dealt to are under 5% of the trade's (print each share). A
    product nothing in the fixture buys is printed and left out.
  - `makers_are_asked_in_proportion` (fixture): for food and materials, the caps asked of a maker from home and
    from abroad over its persons at work lie within a factor of two of the nation's own ratio for makers holding
    nine tenths of the trade's workers (print the shares under half and over twice). Print the same two shares
    for what home buyers alone ask, for each good; they are handed over and not asserted (in the first build food
    was 8.5% under and 1.1% over at home): in the fixture nine tenths of what is asked is asked from abroad, so
    the home dealing shows in the rebuilt scenario's own report (Task 15), not here.
  - `buyers_abroad_are_dealt_over_the_country` (fixture): the buyers abroad of food are dealt more than one home
    maker between them, and no home maker is asked from abroad for more than twice its share by people (its
    people over the people of the dealing's stalls). Print, for each good: the home makers and their people
    outside the dealing (no route to any buyer abroad), the rows from abroad, the widest buyer's rows and the
    largest multiple of its share that a maker is asked.
  - `an_installation_need_follows_its_site_s_makers` (fixture): a process whose machines need materials restocks
    them from the makers its site is dealt for materials.
  - `the_shipped_restocking_is_unchanged`: `binary(shipped_world_bytes)`.
  - `the_dealing_of_goods_fits_its_bounds` (fixture; the first build added it for decision 7): the four counts,
    pinned. The first build filled its pin under the limit of sixteen and committed nothing: the pin is filled
    once from the first failing run of the rule as amended.
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
  `src/babylon/data/reference/economy/national_opening_census_v13.json.gz` (gzipped JSON text, decision 6)
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
     (`CensusError`): the lead then widens the table. `sellers` names every product the census scenario's accounts
     buy (decision 5: the six needs and the three wanted products), so a product only wanted has its seller too.
   - For the rulings of 26 November (what Part II reads: Task 9, decision 3; every figure is read from the compiled
     census scenario, decision 5):
     - Item 1. `places[<part>].sellers[<key label>][<product>]` stays an integer, the selling site's employee wage,
       micros an hour. Beside it, `places[<part>].abroad[<key label>][<shop good>]`, a string: for a shop good
       (`food`, `materials`, `consumer_goods`), the policy key of the region of the shop's foreign second supplier
       of that good, read as `assignment` reads it, by the compiler's rotation (`secondary_candidates` and
       `secondary_supplier`, which read site ids and routes, not numbers), not from the restocking rows (a row
       exists only where a share is above 0, a number). An entry is written only where there is such a region: a
       shop whose second supplier is domestic, or that has none, has no entry, and a service never has one. (Part
       II asked for a seller as an object of the two; two plain maps hold the same and keep the file small: its
       reader builds the object from them.) The rows of `no-earner-nonowner` and `no-earner-owner` hold the six
       needs, and those of `collective-residence` its person-basis needs, in every part where the key has persons.
     - Item 2. `places[<part>].public_persons_served`, an integer: the persons of every domestic household account
       whose purchase row of `public_provision` names a seller whose part (its financial domain, read from the
       generation witness as decision 1's parts are) is this part. A carved account counts at its own row (its
       parent's provider, Task 7b). They sum to the domestic persons.
     - Item 3. `places[<part>].trades.public_provisioning.machines`, an integer: over the part's public provision
       sites with a process, `ceil(force / workers_per_machine["public_provisioning"])` at the census scenario's
       figure (Task 6's count, as `trades.<trade>.machines` counts nationally). They sum to the national figure.
     - Item 5. A top-level `crossing_force`, an object `{ "<service>": { "<region>": { "<trade>": <force> } } }`, for
       `business_services` (the crossing service the Director ruled), each counterpart's key and `"dependency"`, and
       each domestic trade with a recipe (the eleven): the summed `force` of the trade's domestic sites with a process
       whose region abroad is that region by `national_economy::crossing_regions` and `crossing_region` (Task 7e),
       the rule reading no number; a region `crossing_regions` names as a stop stops the recorder with its name. The
       census scenario has no `crossing_services`, so the recorder applies the rule itself to every such
       site, whether its recipe buys the service or not (which trades buy it follows the stages, ruling 1). The
       dependencies hold no candidate location of the rule (as for goods), so `"dependency"` is 0 for every trade;
       each `(service, trade)` summed over regions is the trade's domestic force. About 150 integers.
     - Item 6. `sources.country_services`: the sorted list the census scenario held, `["business_services",
       "leisure", "utility"]`.
2. **Not in it:** anything that follows recipes, prices, taxes or wants. Task 14a proves the census is the same from the
   rebuilt scenario (Review Focus 1).
3. The recorder is an ignored test, `record_national_opening_census`, that compiles the fixture
   (`capture_national_campaign(national_catalog_input_for(fixture)?, campaign)`) and writes the file. The checker,
   `the_committed_census_is_the_opening_s`, not ignored, computes the census again and compares bytes.
4. The register entry: `name: national_opening_census_v13`, `format: json.gz`, `source_table: null`, `generator:
   rust/crates/babylon-persistence/tests/national_opening_census.rs`, `mode: register`, `rows` the number of places,
   `sha256`, `home`, `material_relation` "the persons, jobs and wages of the twelve-trade opening, read by the stage 5
   builder". The file must stay under 1,048,576 bytes; the recorder asserts it of the gzipped file (decision 6).
5. **The census scenario** (E3). Recorder and checker compile the scenario's text with three edits, made by one
   function of `tests/support/opening_census.rs`, `census_scenario(text: &str) -> String`: `[markets]
   country_services = ["business_services", "leisure", "utility"]` (the Director's ruling of 26 November; Task 13
   writes the same list), written in place of the text's own `country_services` line where it has one (the rebuilt
   text does: a second line would be a TOML duplicate key), else added under `[markets]`; its `[[household_wants]]` rows
   replaced by exactly three, each `tier = "luxury"`, `basis =
   "persons"`, `units_per_basis = 1`, of `consumer_goods`, `leisure` and `business_services` (the products of the
   order of paying that are neither a need nor `resources`; Part II refuses a rebuilt scenario whose wants do not
   cover exactly these, `wants_cover: <product>`); and `handling_hours = 1`, `handling_units = 1` on
   `[commodity.consumer_goods]` where the text has no handling there (Task 1 requires a handling row on a storable
   good a want names). The dealing reads persons and force, never a want's amount or a handling figure (Task 7b,
   decision 2), so the census's sellers are the ones the rebuilt scenario deals, and the census stays the same from
   the fixture and from the rebuilt scenario (Task 14a's `the_census_does_not_follow_the_numbers` applies
   `census_scenario` to the rebuilt text as well). `crossing_services` and the shares are not set: crossing does not
   touch households (E2), and `crossing_force` applies the region rule itself.
6. **The file, gzipped** (the lead's decision on finding A-S12). The census as JSON text is likely over 1,048,576
   bytes (the check counted about 5,500 bytes a part before the rulings, about 1.7 MB in all, and the `abroad` map
   adds up to about 330,000). It is committed gzipped, as
   `src/babylon/data/reference/economy/national_opening_census_v13.json.gz`, written with mtime 0 and no file name:
   `flate2::GzBuilder::new().mtime(0).write(Vec::new(), flate2::Compression::best())`, then `write_all` of the JSON
   text and `finish()` (`flate2 = "1"` is a dependency of `babylon-persistence`, `Cargo.toml` L22, so its
   integration tests can use it; `freight_access/tests.rs` L16-20 writes gzip with `GzEncoder`). It is read as the
   crate reads its gzipped reference tables, `flate2::read::GzDecoder` with a limit on what it expands to
   (`michigan_economy.rs` L76, `freight_access/reference.rs` L161; here 8,388,608 bytes). Every comparison and
   every digest is of the JSON text, never of the gzipped bytes: the checker `the_committed_census_is_the_opening_s`
   decompresses the committed file and compares its text with `census_bytes` of the census computed again; the
   register entry's `sha256` is of the JSON text (the recorder prints it); the pin is of the JSON text; the
   builder's metadata names the census by the sha256 of the decompressed text, as Part II's reader takes it. The
   gzipped file is asserted under 1,048,576 bytes and the JSON text under 8,388,608. The register entry (decision 4)
   has `format: json.gz` and `home:` the path above. Step 2 hands over both sizes.

- [ ] **Step 1: Write** the checker and the recorder; run the checker and see it fail (no file).
- [ ] **Step 2: Run the recorder** in the background; then the checker passes. Hand over: the domestic persons at
  work by trade (the spike's 161.3 million in all is the size to expect, not a pin), the persons by key, the machines
  by trade, the count of parts and of hubs, the lowest and highest seller's wage of each product over the parts, the
  share of each country service's sellers that are in another state than the account, the share of shop goods'
  sellers with an `abroad` region by good, `crossing_force` summed by region, and the size.
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
The Director ruled the choices on 26 November ("Ruled by the Director on 26 November", rulings 1 to 6): each is
now one value of its setting, and the builder refuses any other.

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
BUDGET_LABEL: Final[Mapping[HouseholdKey, str]]   # `HouseholdBudgetKey::label()`, for a luxury scale's account
    # (`<part label>:<budget key label>`, Task 11 decision 10) and the metadata: EarningLowerPaidHalf,
    # EarningBetterPaidForty, EarningOwner, NoEarnerNonowner, NoEarnerOwner, CollectiveResidence
BenefitRule = Literal["each_account_own"]                 # ruling 3 (E8: the compiler works the amounts out)
PlaceBody = Literal["every_place_even"]                   # ruling 4 (D4)
ShopImportSaving = Literal["households"]                  # ruling 6 (D6)

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
    place_services: frozenset[str]             # bought in the buyer's own place: housing, household_services,
                                               # public_provision (call 30; the template's `[markets] place_services`)
TWELVE: Final[Economy]

@dataclass(frozen=True)
class Settings:
    """The Director's choices that change the builder's numbers ("Ruled by the Director on 26 November", items 1
    to 6), each at the ruled value, and the design's figures. A later ruling changes a value here and the branch it
    needs."""
    # 1. Services' stages and the order of paying (ruling 1: V6, D7).
    service_stage: Mapping[str, int] = <utility, business_services, housing 1; household_services, leisure,
                                        public_provision 2>
    paying_order: tuple[str, ...] = ("food", "materials", "consumer_goods", "utility", "housing",
                                     "business_services", "household_services", "leisure", "resources")
    # 2. The products that cross a border (ruling 2: V8, K1, E2). A service crosses between businesses only.
    crossing: frozenset[str] = frozenset({"food", "resources", "materials", "consumer_goods", "equipment",
                                          "business_services"})
    # 3. The benefit's rule (ruling 3: V3 by its road (b), E8, D2): the compiler works the amounts out.
    benefit_rule: BenefitRule = "each_account_own"
    # 4. Each part's public body (ruling 4: V1 with V2's road (b), K4, K5, D4).
    place_body: PlaceBody = "every_place_even"
    # 5. The services sold across the country (ruling 5: V9, K2, D5).
    country_services: frozenset[str] = frozenset({"business_services", "leisure", "utility"})
    # 6. Who gets what the shop saves on imports (ruling 6: V10, D6).
    shop_import_saving: ShopImportSaving = "households"
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
class PlaceKeyCount:                           # a part's row of one key: Task 8's `places` have no `accounts`
    households: int; persons: int; employed: int; reserve: int; wage_income_micros: int
@dataclass(frozen=True)
class PlaceTrade:
    employee_persons: int; payroll_micros: int; public_employee_persons: int; public_payroll_micros: int
@dataclass(frozen=True)
class Seller:                                  # who sells one product to a part's accounts of one key (Task 8)
    wage_micros: int                           # the selling site's employee wage, micros an hour (O5)
    abroad: str | None                         # a shop good: the region of the shop's foreign second supplier of
                                               # it, or None when that supplier is domestic; None for a service
@dataclass(frozen=True)
class Place:                                   # ONE PART of a pooled place: the game's unit of accounts (Task 8)
    label: str                                 # `<hub geoid>`, or `<hub geoid>/<position>` for a pooled part
    hub: str                                   # the hub county's geoid: where its accounts buy and its sites sell
    state: str                                 # the hub's first two digits: a service but a country service is
                                               # bought inside it (ruling 5)
    keys: Mapping[HouseholdKey, PlaceKeyCount]   # Wayne's detailed accounts are summed
    trades: Mapping[str, PlaceTrade]
    owner_households: int
    sellers: Mapping[HouseholdKey, Mapping[str, Seller]]   # product -> its seller to the part's accounts of the key
    public_persons_served: int                 # persons of the accounts dealt to the part's public providers
    public_machines: int                       # `places[<part>].trades.public_provisioning.machines` (Task 6's count)
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
    crossing_force: Mapping[tuple[str, str, str], int]   # (crossing service, region, buyer trade) -> the force
                                               # of the home buying sites whose provider abroad is there (E2)
    workers_per_machine: Mapping[str, int]     # the figures the census's `machines` were counted with
    sha256: str
def read_census(path: Path) -> Census: ...

Accounts = Mapping[str, Mapping[str, Mapping[str, int]]]     # block -> row -> column -> value (USD thousands)
def read_accounts(path: Path) -> Accounts: ...
def allowed(settings: Settings, economy: Economy, product_in: str, trade_out: str) -> bool: ...
def check_settings(settings: Settings, economy: Economy = TWELVE) -> None: ...   # the settings' shape
def check_ruled(settings: Settings) -> None: ...   # every choice at its ruled value (decision 2)

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
2. **The six settings, as ruled** (model-spec 3 and 10; Ruled by the Director on 26 November). Each is one
   field of `Settings`, its default the ruled value, and the metadata writes every field (Task 13, decision 6), so
   that a later ruling is a small edit:
   - `service_stage` and `paying_order` (ruling 1, D7): utility, business services and housing in the first stage
     (`kind = "utility"`), household services, leisure and public provision in the second (`kind = "service"`); the
     order of paying food, materials, consumer goods, utility, housing, business services, household services,
     leisure, resources. No engine change; Task 13 writes the kinds and the order.
   - `crossing` (ruling 2, K1, E2): the five storable goods with a price and business services. A crossing service
     is bought abroad by businesses only, by shares as a good is: households on both sides buy theirs at home (Task
     10, decision 3; Task 12, decision 4).
   - `benefit_rule = "each_account_own"` (ruling 3, E8, D2): each no-earner and residence account is paid its own
     needs at its own sellers' posted prices. The compiler works the amounts out (Task 4); the builder writes the
     rule only and estimates the amounts to size the fund (Task 10, decision 10; Task 11, decision 6).
   - `place_body = "every_place_even"` (ruling 4, K4, K5, D4): every part's public body opens even, by its own share
     to the fund or by the fund's grant to its public providers (Task 11, decision 11).
   - `country_services` (ruling 5, K2, D5): utility, leisure and business services are sold across the country. No
     figure of the national solve follows it; Task 11's counts do (decision 12), and Task 13 writes the key.
   - `shop_import_saving = "households"` (ruling 6, D6): the shop posts each good at what it pays for it plus its
     charge (Task 10, decision 7; Task 11, decision 2).
   The alternatives that were not ruled are not built: no module has a branch for them. `Settings` is checked twice.
   `recut` calls `check_settings(settings, economy)` before it reads a cell, and so every later part, which starts from
   a `Recut`, has its settings checked. `check_settings` checks the shape for any `Economy` (the tests' small economies
   take other stages and other crossing sets): every service product has a stage of at least 1; the paying order holds
   every priced product households buy and resources, once each, storable needs before any service, and every
   first-stage service before every later one (call 19; `admission.rs` `paying_order`); `crossing` holds only priced
   products; `country_services` holds only services, none of `economy.place_services`; else `setting: <field>`.
   `check_ruled`, which Task 13's `build` calls before anything is read, refuses any choice field (`service_stage`,
   `paying_order`, `crossing`, `benefit_rule`, `place_body`, `country_services`, `shop_import_saving`) that is not its
   ruled value: `setting_not_ruled: <field>`. The design's figures below them are not choices and are not checked by it.
3. **The census reader.** The census is committed gzipped,
   `src/babylon/data/reference/economy/national_opening_census_v13.json.gz` (written with mtime 0, Task 8);
   `read_census` opens it with `gzip` and its `sha256` is of the decompressed JSON text, the digest Task 13's metadata
   writes. It reads Task 8's JSON exactly, with the key names Task 8 writes (trade keys as the accounts table spells
   them; household keys as `HouseholdBudgetKey`'s serde labels after stage 2, mapped to `HouseholdKey`); an unknown key,
   a missing key or a non-integer value is `census_shape: <json path>`. It checks: the households' `wage_income_micros`
   summed over keys equals the trades' `payroll_micros` summed (`census_wages`); each trade's place rows sum to its
   national row, and each key's place rows to its national row (`census_places: <trade or key>`); `workers_per_machine`
   equals `Settings.workers_per_machine` (`census_machines: <trade>`). The census carries five figures Task 8, decision
   1 lists for Part II: `machines` and `public_employee_persons`, `public_payroll_micros` by trade, nationally and by
   place; `employed` by key in each place; and `sellers`, for each place and key the wage of the site that sells each
   product to its accounts (a provider for a service, a retailer for a shop good). The rulings add four more: for a shop
   good, the region of the shop's foreign second supplier, in the census's map `places[<part>].abroad[<key label>][<shop
   good>]`, which has an entry only where there is such a region (ruling 6; the reader builds each `Seller` from the
   `sellers` integer and that map, `abroad = None` where the map has no entry); each part's `public_persons_served` and
   `public_machines` (ruling 4); and `crossing_force` (ruling 2, E2). The reader checks them too: for each crossing
   service and each domestic trade with a recipe (every trade but distribution, which Task 8 does not write),
   `crossing_force` summed over regions equals the trade's `force` (`census_sites: <service>/<trade>`) and names only
   regions of `abroad` (`census_shape: <json path>`); the parts' `public_persons_served` sum to the domestic persons
   (`census_places: public_persons_served`), since every person buys public provision (need 1 a person);
   `public_machines` sum to public provision's `machines` (`census_machines: public_provisioning`). The census is taken
   on Part I's census scenario (E3: the fixture with `country_services` at its ruled value and a want row for every
   product households do not need), so the sellers of a country service are those D5 deals; the reader refuses a census
   whose `sources` name another list of country services (`census_shape: sources.country_services`). Public provision's
   machines by part are read at `places[<part>].trades.public_provisioning.machines`. The reader passes over
   `trades.<t>.national_wage_micros`, which Task 8 writes for reading only (Task 14b, decision 2); it is not a field of
   `TradeCount`, and the wage the builder uses is decision 1 of Task 10's. Where a Python field's name differs from the
   census's JSON name, the reader maps it so, and every other field is read under its own name:
   `TradeCount.payroll_micros` from `trades.<t>.payroll_micros_per_period` and `TradeCount.public_payroll_micros` from
   `trades.<t>.public_payroll_micros_per_period`; `KeyCount` and `PlaceKeyCount`'s `wage_income_micros` from
   `households.<key>.wage_income_micros_per_period` and `places[<part>].<key>.wage_income_micros_per_period`;
   `PlaceTrade.payroll_micros` and `.public_payroll_micros` from `places[<part>].trades.<t>.payroll_micros_per_period`
   and `.public_payroll_micros_per_period`; `Place.public_machines` from
   `places[<part>].trades.public_provisioning.machines`; `Seller` from `places[<part>].sellers` and
   `places[<part>].abroad`, as above; `Census.crossing_force` from `crossing_force.<service>.<region>.<trade>`;
   `PlaceKeyCount` has no `accounts`. A JSON name not in this mapping and not a field's own name is `census_shape: <json
   path>`, but for `trades.<t>.national_wage_micros`.
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
    goods 4,104, business services 233 (`330,768,000 / (13,829,724,000 + 330,768,000)`; the larger share over the
    game's business buyers is Task 10's `import_cover`), and 0 for every other trade (energy's 480 no longer
    crosses under R2).
  - `the_committed_recut_keeps_the_rules`: no `inputs[i][i]`; no `owner_occupied_housing` key; no input `i` to `j`
    with `allowed` false; `inputs["capital_goods"]` empty; `inputs["business_services"]["household_services"]`,
    `["leisure_hospitality"]` and `["public_provisioning"]` above 0 (ruling 1: a second-stage service buys a
    first-stage one); `inputs["business_services"]["construction_housing"]` absent or 0 (housing cannot buy a
    service of its own stage: the cell is spread under R1); `exports["business_services"]` above 0; `moved` R1
    summed over products, as a period's dollars (`x 1000 / 13`), is between 150 and 400 thousand million (the
    prototype's 260.2 under the regrouping with the border is the size, not a pin: `more/variants-lead.md`, V-j);
    `moved` R2 summed is between 5 and 30 (V-j's 12.9).
  - `bad_settings_are_refused`: a paying order with housing before utility while utility is stage 1 and housing
    stage 2 (`setting: paying_order`); `crossing` with an unpriced product (`setting: crossing`); `country_services`
    with `housing`, a service of the place (`setting: country_services`).
  - `only_the_ruled_settings_pass`: `check_ruled(Settings())` passes; `Settings()` with `service_stage` putting
    business services in the second stage, with `crossing` without business services, with `benefit_rule =
    "dearest_place"`, with `place_body = "one_share"`, with `country_services` empty and with `shop_import_saving =
    "shop"` (each made by `dataclasses.replace` in the test) give `setting_not_ruled: service_stage`, `..: crossing`,
    `..: benefit_rule`, `..: place_body`, `..: country_services` and `..: shop_import_saving`.
  - `the_census_reader_refuses_a_bad_census` (fixture JSON gzipped in `tmp_path`; a census read twice gives one
    `sha256`, of its JSON text): an unknown key, a missing trade, a float
    value, wage incomes that do not sum to the payroll, a place row over its national row, a `workers_per_machine`
    of 5, a `crossing_force` whose regions sum short of its trade's force by 1, a `crossing_force` row in a region
    the census does not name, `public_persons_served` that miss the domestic persons by 1, `sources` naming country
    services but utility: each its code.
- [ ] **Step 2: Run them and see them fail** (`mise run test:q -- tests/unit/tools/test_national_opening_recut.py`).
- [ ] **Step 3: Implement** decisions 1 to 5.
- [ ] **Step 4: Run them and the gate.**
- [ ] **Step 5: Commit** with the subject above. Hand over the committed table's R1, R2, R3 and inventory spreads
  by product, a period's dollars, beside the prototype's under the regrouping with the border (260.2 and 12.9,
  `more/variants-lead.md`, V-j; R3's 221.6 is the same in every variant `variants.md` printed; the inventories' 2.1
  is this plan's figure of the rules as they stand) for size only, and the business services import share pinned.

What the player would see: nothing; the numbers come in Task 13.

### Task 10: The builder, part 2: quantities, prices, margins, trade and taxes

Commit `feat(reference): solve the opening's prices, margins and taxes`.

**Why.** The national opening at one margin factor, and the factor itself (model-spec 4 to 7 and 9). The prototype
solved it in floats by value iteration. Here every step is exact or held on a grid, so two builds give the same
bytes and a trade at its wear floor is decided by an exact comparison. The rulings of 26 November move three things
here: business services cross between businesses (decisions 3 and 6), the shop passes on what it saves abroad
(decisions 7 and 9), and the benefit is each account's own cost, which the builder estimates and the compiler works out
(decisions 10 and 11).

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
    import_cover: Mapping[str, Fraction]      # the share a buyer that may import takes abroad, before rounding
    business_demand: Mapping[str, Fraction]   # a crossing service: sum_j a[i][j] x[j], the home businesses' demand
    service_import_bps: Mapping[str, int]     # a crossing service: the share written (Task 10b writes the same)
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
    import_saving: Mapping[str, Fraction]     # S[j] by buying trade, dollars a period (the shop's part excluded)
    shop_saving: Mapping[str, Fraction]       # the shops' saving on each shop good: households' (decision 7)
    wear: Mapping[str, Fraction]              # by trade with machines
    operating_income: Mapping[str, Fraction]  # OI[j], private trades and the shop
    public_owned_income: Fraction             # PO
    grant: Fraction; support: Fraction; benefits: Fraction
    own_cost: Mapping[tuple[str, HouseholdKey], Fraction]   # (part, key) -> the estimate of decision 10
    tax_rate: Fraction; fund_share: Fraction; payout: Fraction
    household_purchases: Mapping[str, Fraction]   # H[i], dollars a period, what households pay at the maker's
                                              # price (a shop good less the shops' saving, decision 7)
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
   (the shop's part stands for households). A good with no weight is `import_weights: <good>`. A good's
   `import_cover` is `IMP[good] x total weight / foreign weight`, the weights over all domestic buyers and over
   those with a foreign second supplier (call 22; Task 10b, decision 8 writes it rounded).
   **A crossing service** (ruling 2, K1, E2) is bought abroad by businesses only, by shares as a good is:
   households buy theirs at home. Every domestic buying site keeps its home provider and takes `floor(required x
   import_bps[key] / 10_000)` from one provider abroad, in the region the compiler's rule gives it (a rule that
   reads no number). So its `business_demand` is `sum_j a[i][j] x[j]` over the trades with a recipe, public
   provision's included, and `import_cover[i] = m[i] / business_demand[i]`, the accounts' import volume over the
   home business buyers' demand; above 1 is `import_coverage: <service>`. The share written is
   `service_import_bps[i] = half_up(10_000 x import_cover[i])`. Who sells the imports: a region's weight is `sum_j
   crossing_force(i, region, j) x 160 x a[i][j] / h[j]` over the trades that buy `i` (the census's table, E2);
   `sigma[i][region]` is that over its sum, and `import_buyers[i]` the same weights by trade, with no households'
   part. A crossing service with no weight is `import_weights: <service>`.
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
   `kx = (I - p[ext] X[ext]) / sum p[i] xs[i] x[i]` over them; the rest 0. With business services crossing (ruling
   2) the crossing products are six and the one factor `kx` runs over the five of them but resources (food,
   materials, consumer goods, equipment, business services), as the prototype's V-j. `kx` below 0 is
   `negative_exports`;
   with no export base (`sum p xs x = 0`) `kx` is 0 when `I - p[ext] X[ext] = 0`, else `negative_exports`.
   Equipment bought at home and abroad: `E = p[capital] (fin[capital] - X[capital])`. Households' purchases `H[i] =
   p[i] (fin[i] - X[i])` for the products households buy, less the shops' saving on a shop good (decision 7); one
   below 0 is `negative_residual: <product>`.
7. **What buyers save abroad.** A domestic buyer pays a foreign seller less than the national price: `S[i] = m[i]
   (p[i] - p~[i])`, dealt over buying trades by `import_buyers` (capital goods' by machines, public provision's
   part included). A firm's part is operating income of the trade that buys, and public provision's part lowers
   the grant. Without it, balance 1 is short by what imports save: counted by the lead on the prototype at 2.2% to
   3.2% of household spending (18.5 to 27.8 a period, of which the shop's part is 4.1 to 6.2), with foreign sellers
   at 60% to 40% of the country's wage. This is not in the prototype's model; listed in the metadata.
   **The shop's part goes to households** (ruling 6, D6): the shop posts each good at what it pays for it plus its
   charge, so its part of `S`, `shop_saving[i]`, is no income of the shop: `H[i] = p[i] (fin[i] - X[i]) -
   shop_saving[i]` for a shop good, and `OI[shop] = U[shop]`. A crossing service has no shop part (households buy
   it at home), so its whole `S` is the business buyers'.
8. **Operating income, public money and one tax rate** (model-spec 7; O12, O13; call 5). `Pi[j] = p[j] x[j] mu[j] /
   (1 + mu[j])`; `OI[j] = Pi[j] + U[j] + S[j] - wear[j]` for private trades and `OI[shop] = U[shop]` (decision 7);
   one below 0 is `negative_operating_income: <trade>`. `PO = sum_j OI[j] x public_employee_persons[j] /
   employee_persons[j]`. The grant `G = payroll[public] + sum_i a[i][public] p[i] x[public] + wear[public] -
   S[public] - fee x domestic persons`. Support `SUP = reserve persons x s`, `s = t1q[food] x p[food]`: one period of
   the food need at the producer's price (Task 4, decision 6; `support_unit_price` reads the commodity's price).
   Benefits `BEN` (decision 10). `W` is every trade's census payroll. Then `t = (G + SUP + BEN - PO) / (W + sum OI -
   PO)`, `f = BEN / (t (W + sum OI))`, payout `(1 - t)(sum OI - PO)` (`private_distribution_bps = 10000`). `t` or
   `f` outside `[0, 1)` is `tax_rate`.
9. **Spending and tier 1** (model-spec 7). The shop's charge follows the producer value of what it handles (retail
   hours follow value, Task 10b decision 7), whatever the shop paid: `rho = H[shop] / sum_shop goods p[i] (fin[i] -
   X[i])`. At posted prices `Hs[i] = H[i] + rho p[i] (fin[i] - X[i])` for shop goods (what households pay the shop:
   what it paid, less its saving, plus its charge), else `H[i]`; `C = sum H + H[shop]`; `cbar = C / domestic
   persons`. Tier 1 is the five needs in households' own mix: `t1[i] = tier_sizes[0] x cbar x Hs[i] / sum_needs Hs`
   a person of average size; a household need's value a household is `t1[i] x AVG`, `AVG = persons / households`
   over the five non-collective keys. Quantities a basis: `t1q[i] = t1[i] / posted[i]` accounts dollars a person
   for a person need, `t1q[i] = t1[i] x AVG / posted[i]` a household for a household need; `posted[i] = Hs[i] /
   (fin[i] - X[i])` for shop goods, the national posted price a unit as households pay it on average (`p[i] (1 +
   rho)` less the shops' saving a unit), else `p[i]`. `Opening.tier_one` holds the values a basis (`t1[i]`, or
   `t1[i] x AVG`). Public provision's need (1 a person at its fee) is outside the sizing, as the prototype.
10. **The benefit: each account's own cost** (model-spec 11; O12; call 18; ruling 3, D1). An account pays its own
    sellers' posted prices (O5), and the census names the seller of each product to each part's accounts of each key
    (`Place.sellers`). So an account's own price of a need is `pown[i] = p[i] + (w_seller[i] - wage[i]) h[i] (1 +
    mu[i])` for a service (Task 14b's `own_price`), and for a shop good what its shop pays plus its charge at its
    retailer's wage (ruling 6, D6): `pown[i] = p[i] (1 - cover[i]) + p_r[i] cover[i] + rho p[i] w_seller[i] /
    wage[shop]`, `cover[i]` the good's `import_cover` and `p_r[i]` the price of decision 6 in the region of the
    shop's foreign second supplier (`Seller.abroad`), and `pown[i] = p[i] (1 + rho x w_seller[i] / wage[shop])` for
    a shop whose second supplier is domestic. Its own tier-1 cost a person is `c1own = (persons x sum_person needs
    t1q[i] pown[i] + households x sum_household needs t1q[i] pown[i]) / persons + fee` (no household needs for a
    residence). `own_cost` holds it for every domestic no-earner account with persons (`no_earner_nonowner`,
    `no_earner_owner`) and every residence account with persons, by its part and key. The benefit is NET of the
    county support the account already gets (call 16; ruling 3: "nobody is paid above their needs"): a no-earner
    account's benefit is `ben = max(c1own x persons - reserve x s, persons / 10^6)`, a residence's `ben =
    max(c1own x (persons - employed) - reserve x s, persons / 10^6)`, `reserve` its persons looking for work at the
    opening (the census's `reserve` by part and key) and `s` decision 8's support a person (Task 4, decision 9: one
    period of one person's food need at the food price), at least one micro a person as the compiler pays. `BEN`
    is their sum: a residence is paid for its residents with no job at the opening (call 18), and the fund's cost
    falls by what the counties pay. This is the builder's ESTIMATE of what the
    compiler pays (E8: Task 4 works each account's amount out from the compiled opening's own offers, carved
    accounts each their own); it sizes the fund's payments and so the tax rate. Exact; Task 11 estimates again at
    written figures, and Task 15 compares the compiled dues with it.
11. **The national accounts and kept money** (model-spec 8; call 20). The margin factor is set on the census's
    national accounts, one for each key. Money a period: every key's `reserve x s` (support); beside it an earning
    key's and the residence's `wage income (1 - t)`, a no-earner key's sum over its accounts of `ben` (decision
    10, net of the support), the residence's sum over its accounts of `ben`; the two owner keys share the payout by
    households. Full cost: `persons x (sum of the person needs'
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
    residual passes one dollar a period. The fund's grants to short parts (ruling 4) move money between public
    accounts only and are not in balance 2 here; Task 11 sets them and Task 13 closes the fund with them (its
    decision 5).
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
    (wage/2) h (1 + mu)`; `S[food] = m (p - p~)` and its firms' part is in food's buying trades' operating income.
  - `the_shop_passes_on_what_it_saves` (ruling 6): the same region, with the shop's part of food's imports `1/4`
    of `m` set in the test's `import_buyers`: `shop_saving[food] = m (p - p~) / 4`; `H[food] = p (fin - X) -
    shop_saving[food]`; `OI[shop] = U[shop]`; `posted[food] = Hs[food] / (fin - X)`, below `p (1 + rho)` by
    `shop_saving[food] / (fin - X)`; balance 1's residual at most one dollar a period.
  - `a_crossing_service_is_imported_by_businesses_only` (ruling 2, E2): a service `s` bought by two trades A and B
    (`a[s][j] / h[j]` 1 for both); census `crossing_force`: A 70 at r1 and 30 at r2, B 60 at r1 and 40 at r2;
    `m[s] = 30`, `business_demand[s] = 60`, so `import_cover[s] = 1/2` and `service_import_bps[s] = 5,000`.
    `sigma[s]` is r1 13/20, r2 7/20; `import_buyers[s]` is A 1/2, B 1/2, with no households' part. With `m[s] =
    61`, `import_coverage: s`.
  - `largest_with_nothing_kept_is_exact`: with `kept_at(l) = max(0, l - 3/10)`, the answer is `329853488332 /
    2**40`, the largest multiple of `2^-40` not above 3/10; with `kept_at(l) = 1`, `margin_scale_none`; with
    `kept_at(l) = 0`, 1.
  - `the_benefit_is_estimated_at_each_account_s_own_cost` (ruling 3, E8): two parts whose no-earner accounts'
    sellers of household services pay $20 and $30 an hour, and one residence of 10 persons with 4 employed:
    `own_cost` of each account is its `c1own`, recomputed in the test from `pown`; the dearer seller's account has
    the higher one; `BEN` is the two no-earner accounts' `c1own x persons` and the residence's `c1own x 6`, summed.
    No figure is the dearest place's, and no account's figure is another's.
  - `a_shop_good_s_own_price_is_what_its_shop_pays`: a no-earner account whose shop of food has its foreign second
    supplier in a region at half food's wage, beside one whose shop's second supplier is domestic, both retailers
    at the national shop wage: the first's `pown[food]` is `p (1 - cover) + p_r cover + rho p`, the second's `p (1 +
    rho)`, and the first's `own_cost` is lower by `t1q[food] (p - p_r) cover`.
  - `every_key_gets_its_support`: a no-earner account of 20 persons with 10 reserve persons has `10 x s` of support
    and `ben = c1own x 20 - 10 x s` of benefit, so its money is `c1own x 20`, its needs and no more; with `s`
    above `c1own x 2` its benefit is `20 / 10^6`, one micro a person; the keys' money sums to wages after tax, the
    payout, support and benefits.
  - `refusals_have_their_codes` (hand cases): firms that take more of a product than is made and imported give
    `negative_residual: <product>`; imports worth less than extraction's exports give `negative_exports`; benefits
    above every tax base give `tax_rate`; a trade whose wear passes its margin and saving gives
    `negative_operating_income: <trade>`.
  - On the committed tables (marked `@pytest.mark.slow`; one module fixture solves once):
    `the_margin_factor_leaves_nothing_kept` (kept at `lam` 0, at `lam + 2^-40` above 0);
    `every_margin_covers_its_wear`; `the_four_balances_close_at_the_exact_solve` (each residual at most `10^-9` of
    its flow); `every_job_is_needed_at_the_exact_solve` (`h[j] x[j] = hours[j]` for every trade, exactly);
    `the_business_services_imports_meet_the_accounts` (`service_import_bps / 10_000 x business_demand` within one
    basis point of `business_demand` of `m["business_services"]`).
    Print for the hand-over: `lam`, `t`, `f`, `kx`, `BEN` (an estimate), the lowest, median and highest `own_cost`
    of the no-earner accounts and of the residences, `cbar`, `C`, `G`, `E`, `service_import_bps["business_services"]`,
    the shops' saving by good, the floored trades and the rounds. The prototype's figures under the regrouping with the
    border (`more/variants-lead.md`, V-j: `lam` 0.148, rate 22.0%, share 27.1%, `kx` 1.384, `C` $777.3bn, grant
    $150.8bn; a no-earner person at national prices $1,066, by county $846 at the fifth percentile, $1,019 at the
    median, $1,691 in the dearest; the fund $692bn a year at each place's own cost) are the size to expect, never
    asserted: the builder's people, its accounts by part, the import prices and the shops' saving all differ.
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
def region_prices(w: Written, o: Opening, wage_micros: Mapping[str, int], census: Census,
                  export_bps: Mapping[str, int] | None = None) -> Mapping[str, int]: ...
    # moved here from Task 12 (decision 9): Task 11 reads a foreign supplier's price for an account's shop
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
   machine", "machine"; public provision as the fixture. A service's `kind` follows `service_stage` (ruling 1, D7):
   utility, business services and housing `"utility"` (the first stage), household services, leisure and public
   provision `"service"`.
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
   `fund_share_bps = half_up(f x 10_000)`, the same for both taxes (Task 1's `[fund]`; the parts' own shares of
   ruling 4 are Task 11's). A domestic buyer's import share is a cap on buyers whose second supplier is foreign only
   (`procure`), so the share written makes the nation's imports what the accounts say: `import_bps[i] =
   half_up(10_000 x import_cover[i])`, Task 10 decision 3's `IMP[i] x total weight[i] / foreign weight[i]`, the
   weights over all domestic buyers and over those with a foreign second supplier; above 10,000 is
   `import_coverage: <good>`. Equipment's share is `IMP[capital]` over machines (Task 5 chooses whole processes).
   A crossing service's share (ruling 2, K1, E2) is Task 10's `service_import_bps[i]`, the accounts' import volume
   over the home business buyers' demand, unchanged here; above 10,000 is `import_coverage: <service>`. So
   `import_bps` holds exactly the five storable goods with a price and business services (K1).
9. **A region's prices** (O5; Task 14b; moved from Task 12, decision 1, so that Task 11 can price an account's shop
   abroad). Each product's at the region's census wage: Task 14b's `own_price` on the written recipe and margin,
   exactly as the compiler computes it. A shop good as the region's retailers post it, by the same rule as a shop at
   home (ruling 6; E7): what it pays plus the charge at the region's shop wage (`retail_stock`). The compiled price
   is the average over the makers Task 7d deals the shop, rounded up, which the builder cannot know (that dealing
   follows the numbers), so the builder writes an ESTIMATE and says so in the metadata: `ceil((the region's own
   price of the good x (10_000 - export_bps) + the country's written price x export_bps) / 10_000)` plus the
   charge; with `export_bps` not given, the national price plus the charge as today (Task 11 needs only the
   region's makers' prices; Task 12 passes the shares it writes in each round). Public provision's fee as at home.

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
  - `a_crossing_service_s_share_is_over_its_business_buyers` (ruling 2): a hand `Opening` whose business services
    `service_import_bps` is 1,234 writes `import_bps["business_services"] = 1234`; the keys of `import_bps` are the
    five priced storable goods and business services; a `service_import_bps` of 10,001 is
    `import_coverage: business_services`.
  - `the_kinds_follow_the_stages` (ruling 1): utility, business services and housing are written `"utility"`,
    household services, leisure and public provision `"service"`.
  - `a_region_s_prices_follow_its_wage` (moved from Task 12): a region at half the country's wage of household
    services prices it at `own_price` of the written recipe at that wage; its shop's food with `export_bps` 2,000 is
    `ceil((region's food x 8_000 + national food x 2_000) / 10_000)` plus the charge at its shop wage (E7's
    estimate: region's food 600,001 and national 1,000,000 give 680,001).
  - On the committed tables (slow): `rounded_recipes_cost_within_one_percent` (every recipe within 1%, no input 0,
    every private trade passes O5's refusal at written figures); `handling_blocks_are_close`;
    `the_import_shares_written_meet_the_accounts` (`import_bps x foreign weight / total weight` within one basis point
    of `IMP` for each good; business services' `import_bps / 10_000` within one basis point of `m /
    business_demand`). Print each recipe's `n`, `L`, error and `batch_hours_lost`, and the kinds written.
- [ ] **Step 2: Run them and see them fail. Step 3: Implement. Step 4: Run them and the gate.**
- [ ] **Step 5: Commit** with the subject above.

What the player would see: products named in days and households, prices of a few dollars a unit.

### Task 11: The builder, part 4: each place's accounts, the tiers and the benefit

Commit `feat(reference): the tiers, the benefit and each account's money`.

**Why.** The tiers must make what the game's own accounts buy, under R4, equal what households must buy of each
product, or some trade's workers are not needed (model-spec 10; the prototype: proportional contents bought by the
order of paying miss food by 29%). The accounts are the game's own: the 316 parts of the 187 pooled places by six
keys (a part is the census's row and this task's "place"); an account above its three tiers spends all on its
luxuries (call 20). Under the rulings of 26 November this task also estimates each no-earner and residence
account's own benefit, which the compiler works out (ruling 3, E8), each part's share to the fund or the fund's
grant to it (ruling 4), and counts the services of the place by state and the three country services for the
country (ruling 5).

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
    no_earner_estimate: Mapping[tuple[str, HouseholdKey], int]   # (part, key) -> the estimate a person (E8)
    residence_estimate: Mapping[str, int]                   # part -> a paid residence's estimate a person
    reach: Mapping[tuple[str, HouseholdKey], tuple[Fraction, Fraction, Fraction]]
    demand_gap: Mapping[str, Fraction]                      # bought over needed, less 1, at written figures
    own_price_gap: Mapping[str, Fraction]                   # the same with every account at its own prices
    state_services: Mapping[tuple[str, str], tuple[Fraction, Fraction]]   # (state, service of the place or the
                                                            # shop's hours) -> capacity, use
    country_services: Mapping[str, tuple[Fraction, Fraction]]   # a country service -> capacity, use (ruling 5)
    place_bodies: Mapping[str, tuple[Fraction, Fraction, Fraction]]   # part -> taxes, public-owned payout,
                                                            # payments, a period
    share_by_part_bps: Mapping[str, int]                    # every domestic part's share to the fund (K4)
    place_grant_micros: Mapping[str, int]                   # the parts the fund pays (K5)
def tiers(o: Opening, census: Census, w: Written, settings: Settings) -> Tiers: ...
```

**Decisions:**
1. **The accounts** (model-spec 8, on the game's people). One account per place and key with persons (an account of no
   persons is left out), from the census's places; Wayne's detailed accounts of one key are one account here. Money a
   period, at the exact solve, rounded down to whole micros: an earning key's and the residence's `wage income (1 - t) +
   reserve x s`; the two owner keys share the place's payout by households over `owner_households`; a no-earner key its
   estimated `amount x persons + reserve x s`; the residence its estimated `amount x persons` beside its wages (decision
   6). A place's payout is `(1 - t)` times its private operating income: `OI_c = sum_j (OI[j] x emp_c,j / emp_j + mu[j]
   (payroll_c,j - wexact[j] x 160 x emp_c,j))` less its public-owned part by the same rule over public employee persons
   and payroll, `wexact = payroll / (employee persons x 160)` exactly; the second term is O5's margin on the place's own
   wage, and it sums to 0 over places. So the places' money sums to the national accounts' within one micro an account.
2. **Rows and prices.** Tier 1 is the six needs: 28 a person of food, utility and household services, 28 a household
   of materials and housing, 1 a person of public provision (no household rows for a residence). Wants are by person
   (the prototype's reading; listed). The tier solve buys every row at the NATIONAL posted price of its unit: the
   written price plus, for a shop good, `ceil(hours x wage[shop] / units)` (Task 3, decision 4). The national
   accounts close there, and only there (decision 12). Under ruling 6 the national posted price of a shop good is
   what households pay on average (Task 10, decision 9): the written price less the shops' saving a unit, plus the
   charge, as an exact Fraction of micros (it is a price of the solve only; nothing is written from it). What
   depends on one account's own purse is set at its OWN posted prices, `Account.own_prices`: for a service Task
   14b's `own_price` at its seller's wage; for a shop good what its shop pays plus the charge at its retailer's wage
   (`Place.sellers`; ruling 6, D6, E7). The compiled price is the average over the makers Task 7d deals the shop,
   rounded up, which the builder cannot know, so this is an ESTIMATE, and the metadata says so: `ceil((written
   price x (10_000 - import_bps) + the price of the region of the shop's foreign second supplier (`Seller.abroad`,
   `region_prices` of Task 10b) x import_bps) / 10_000)` plus `ceil(hours x w_retailer / units)`; a shop whose
   second supplier is domestic, the written price plus that charge. Task 15 reports the gap between this estimate
   and the compiled prices. Those are the benefit (decision 6) and the
   luxury scales (decision 10).
3. **Buying** (R4; model-spec 10). `buy` takes tier 1, 2, 3 in turn and, inside a tier, the rows in the order of
   paying (public provision, which is not in it, last); each row whole while money lasts; the row where it ends takes
   the rest in fractional units; what is left after tier 3 is kept unless `scale` is given, when tier 3's rows are
   bought times `scale` (call 20). `pattern` records where the money ended. The order of paying is the ruled one
   (ruling 1): food, materials, consumer goods, utility, housing, business services, household services, leisure.
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
6. **The benefit estimated: each account's own cost** (O12; call 18; ruling 3, E8, D2). The scenario carries the
   rule only (`kind = "own_needs"`, Task 13); the compiler works each recipient's amount out from the compiled
   opening's own offers, after every offer is final (Task 4). The builder cannot know those offers to the micro (a
   shop's price follows the makers it is dealt), so it ESTIMATES the amounts, by the compiler's rule, at its own
   posted prices (decision 2), and reports the estimate by part. The tax is sized on Task 10's estimate (its
   decision 10). This estimate, at written figures and by the compiler's rule, is what Task 13's balance 2 and Task
   15 compare; its gap to Task 10's is printed:
   - `no_earner_estimate[(part, key)] = max(1, ceil((own tier-1 cost - reserve x support) / persons))` micros a
     person for every domestic no-earner part and key with persons (`no_earner_nonowner`, `no_earner_owner`), the
     cost its `[[household_needs]]` for one period: 28 a person of food, utility and household services, 28 a
     household of materials and housing, and the fee a person;
   - `residence_estimate[part] = max(1, ceil((own person-needs cost x (persons - employed) / persons - reserve x
     support) / persons))` for every residence with a resident with no job at the opening (call 18; no household
     rows for a residence); a residence with none is no recipient.
   Both are NET of the county support the account gets (call 16; ruling 3, "nobody is paid above their needs", as
   the compiler pays them, Task 4): `reserve` is the part and key's persons looking for work at the opening (the
   census), and `support` a person is Task 4's, decision 9: `reserve_food_support_periods x food need
   units_per_basis x the food price`, one period of one person's food need, here `1 x 28 x price_micros["food"]`,
   whole micros. The cost is exact in micros; one rounding, up, to a whole micro a person, and at least 1 (the
   compiler's floor). The fund's cost falls by what the counties pay.
   A part's carved accounts are each a recipient of their own in the compiler; the census gives them one seller a
   product with their parent (Task 7b, decision 3), so the estimate is the part's and key's, on their summed persons
   and households. The fund's estimated payments are `sum estimate x persons` (residences: `x persons`, the estimate
   being already scaled by the jobless share), which Task 13's balance 2 reads.
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
    scaled set, decision 5, is at national prices.) The compiler refuses a scale above 1,000,000 (Task 1); the builder
    refuses it first, `luxury_scale_bound: <part>/<key>`.
11. **Every part's body opens even** (model-spec 12; Ruled by the Director on 26 November, item 4; ruling 4, K4,
    K5, D4). Each part has
    its own public body, so this is by part. At the exact solve, a period:
    - taxes `T_c = t (residents' wage income_c + OI_c + PO_c)` (the wage tax where the household lives, the operating
      income tax where the site is, public-owned sites included: every site pays it, `opening/financial.rs` `wire`;
      `OI_c` and `PO_c`, the part's private and public-owned operating income, by decision 1's rule);
    - the public-owned payout `Q_c = (1 - t) PO_c`, which the part's body receives from its public-owned sites;
    - payments `P_c = grant_c + reserve_c x s`, where `grant_c` is its public providers' grants as the compiler
      makes them (Task 4, decision 8: `payroll + inputs at planned batches + wear - fee receipts`):
      `payroll_c,public + (G_inputs) x emp_c,public / emp_public + wear[public] x public_machines_c /
      machines[public] - fee x public_persons_served_c`, `G_inputs = sum_i a[i][public] p[i] x[public] - S[public]`.
    A part with `T_c > 0` and `T_c + Q_c >= P_c` sends the rest to the fund: `share_by_part_bps[c] = 10_000 -
    floor(10_000 x (P_c - Q_c) / T_c)`, at least 0 and at most 10,000 (D4's formula with the payout netted, since
    the part's body also receives `Q_c`: lead's decision E5), and has no grant. By its share it keeps `floor(10_000 x
    (P_c - Q_c) / T_c) / 10_000` of its taxes, less than one basis point of them short of even; but the compiler
    floors the fund's RATE, not the taxes (Task 4's `split_rate`), so the part keeps up to `10_000 / rate_bps`
    basis points of its taxes more (about 4.5 at a rate of 2,200). A part whose payout alone passes its payments
    (`Q_c > P_c`) sends all its taxes and still keeps `Q_c - P_c`; the metadata lists each such part with that
    figure. A part with `T_c + Q_c < P_c` keeps all its taxes
    (share 0) and has a grant `place_grant_micros[c] = ceil((P_c - Q_c - T_c) x 10^6)` whole micros, so it never
    opens short; a part with `T_c = 0` has share 0 and that grant when it is above 0. The grant is
    paid to the part's public providers in place of that much of its own allocation (D4; the compiler deals it over
    them), so it may not pass `grant_c`: else `place_grant_over_providers: <part>` (a part whose county support alone
    passes its taxes). Every part of the census is in `share_by_part_bps` (K4 and Task 4 want every domestic part
    named). The fund's receipts are `sum_c share_by_part_bps[c] x T_c / 10_000`; at the exact solve they equal Task
    10's `BEN` and the grants, up to the share's rounding (at most `T_c / 10_000` a long part) and the grants'
    (a micro a part). Against the estimated benefits of decision 6 they differ also by the gap between the two
    estimates, which is printed (Task 13, decision 5).
    `place_bodies` holds `(T_c, Q_c, P_c)`. The County Review's relief and the City PD's allocation are Wayne's
    bodies' own rows and are not in `P_c`, as in the plan before the rulings; Wayne's bodies do not open exactly
    even.
12. **What own prices and where a service is bought move: counted, not solved** (Ruled by the Director on 26 November,
    item 5; ruling 5, K2, D5). The solve balances the national accounts at national prices. Two things in the game do
    not follow it, and no tier list can make them: an account pays its own sellers' prices, and a service of the place
    is bought only in the buyer's own place (`place_services`: housing, household services, public provision), while the
    three country services (`country_services`: utility, leisure, business services) are bought at home in the buyer's
    own state first and then anywhere in the country (D5). No figure of the national solve follows either. The builder
    counts both at written figures and writes them to the metadata. Nothing is asserted.
    - `own_price_gap[product]`: every account buys again by R4 at its own posted prices, with its written scale;
      the units bought over `D`, less 1. The census's sellers are those the compiler deals (Tasks 7b and 7c, and
      D5 for a country service), so this reads each account's own seller wherever it is; it is one figure a product
      for the country, as before.
    - `state_services[(state, service)]`, for housing, household services and public provision, and for the shop's
      hours: capacity, the hours of the state's census workers of the trade over the written recipe's hours a unit
      (the shop: its workers' hours; public provision: its public workers' hours over its recipe's); and use, what
      the state's accounts buy at their own prices (public provision: 1 a person), plus what its sites need by the
      written recipes at their census hours, plus its public providers' need. The metadata also gives, for each
      such service, the share of capacity in states that use less than they can make (`idle`) and the share of use
      in states that want more than they can make (`unserved`). These three are bought in the buyer's own place, so
      a state's count is the least the places of that state miss: a place's miss can only be larger.
    - `country_services[service]`, for utility, leisure and business services: capacity, the hours of all domestic
      census workers of the trade over the written recipe's hours a unit; use, what all domestic accounts buy at
      their own prices, plus what domestic sites need by the written recipes, plus public providers' need, plus
      exports (business services), less what home businesses take abroad (business services). There is no state
      count for them: D5 deals a state's buyers to its own providers to the nation's level and the rest across
      state lines, so the country is their market.
    The prototype's sizes, never asserted (`more/places-lead.md`, rules as they stand): at state prices the gap by
    product is -0.7% to +2.4%; idle and unserved are about 8% for housing, 6% for household services and 2 to 4% for
    the shop's hours; utility's 17%, leisure's 12% and business services' 7 to 9% by state are the misses ruling 5
    takes away. Public provision was not counted by state in the prototype.

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
  - `the_benefit_is_estimated_at_each_account_s_own_cost` (ruling 3, E8): own posted prices, micros a unit: food
    1,000,000, utility 500,000, materials 250,000, housing 2,000,001, the fee 1,000,000, and household services
    3,000,000 in part `"01001"` and 4,500,000 in part `"01003"` (a seller at a higher wage). A no-earner nonowner
    account of `"01001"` of 3 persons and 2 households costs 507,000,056 at its own prices; it has 1 person looking for
    work, with support `28 x 1,000,000` = 28,000,000 (the written food price 1,000,000): its estimate is
    `ceil(479,000,056 / 3)` = 159,666,686 a person, 479,000,058 in all, two micros above its needs less its support
    (without the support it would be 169,000,019, 507,000,057). A no-earner account whose support passes its needs
    (persons 1, households 1, reserve 1, needs 20,000,000) is estimated at 1 micro. A no-earner owner account of
    `"01003"` of 2 persons and 1 household, nobody looking for work, costs 401,000,028: 200,500,014, exactly. A
    residence of `"01001"` of 10 persons and 4 employed (127,000,000 a resident, nobody looking for work) is estimated
    at 76,200,000 a person; a residence of `"01003"` of 10 persons and 10 employed is no recipient. The fund's estimated
    payments are 479,000,058 + 401,000,028 + 762,000,000.
  - `a_shop_posts_what_it_pays` (ruling 6, E7's estimate): written food 1,000,000 micros, the region of the shop's
    foreign second supplier prices it at 600,001, `import_bps["food"] = 2,500`, a block of 1 hour for 10 units and a
    retailer at 20,000,000 micros an hour: the account's own price of food is `ceil((1,000,000 x 7,500 + 600,001 x
    2,500) / 10,000)` = 900,001 (900,000.25 rounded up), plus 2,000,000: 2,900,001; an account whose shop's second
    supplier is domestic, at the same retailer wage, pays 3,000,000.
  - `a_scale_is_set_at_the_account_s_own_prices`: one account whose sellers charge twice the national price of
    leisure: its scale is `floor(10_000 x (money - tier 1 - tier 2) / tier 3)` with each tier at its own prices, and
    bought at its own prices with that scale it keeps less than one unit's price of its dearest luxury.
  - `own_prices_move_what_accounts_buy`: two accounts of equal money and persons, one whose sellers charge half
    the national price of a service and one twice. At national prices they take the same units. At their own prices
    the first takes more and the second less, by the figures in the test; `own_price_gap` is the two over `D`, less
    1.
  - `a_state_s_services_are_counted` (ruling 5): a hand census of two states, one with every household services
    worker and one with all the money: the first state's capacity is `idle` but for what its own accounts buy, the
    second's use is `unserved`, and over both states capacity equals use at national prices. With leisure, a
    country service, in the same two states: `state_services` has no leisure row, and `country_services["leisure"]`
    has capacity equal to use at national prices.
  - `every_part_opens_even` (ruling 4): part `"01001"` with taxes $100, no public-owned payout and payments $80 has
    `share_by_part_bps` 2,000 and no grant; part `"01003"` with taxes $50, payout $5 and payments $75 has share 0 and
    `place_grant_micros` 20,000,000; with these two parts alone the fund's receipts, `2,000 x $100 / 10,000` = $20,
    equal its grants with no benefit. Part `"01005"` with taxes $3 and payments $1 has share 6,667 and by it keeps
    $0.9999, short by less than one basis point of its taxes. Part `"01009"` at `t = 1/4`, with residents' wages and
    private operating income $60, public-owned operating income $40 and payments $50: `T_c = $25` (its public-owned
    sites' tax counted; without it $15), `Q_c = $30`, share `10_000 - floor(10_000 x 20 / 25)` = 2,000, no grant (the
    reading without the public-owned tax would grant it $5); the fund takes $5, and $20 + $30 = $50 is kept. Part
    `"01011"` with taxes $10, payout $60 and payments $50 has share 10,000 and is listed with $10 kept above even. Part
    `"01007"` with taxes $10, payments $50 of which its providers' grants are $30 and its county support $20 gives
    `place_grant_over_providers: 01007`.
  - On the committed tables (slow): `no_account_opens_without_its_tier_one` (every place account's money reaches
    tier 1 at its own posted prices; an account that does not is printed with its place, key and gap);
    `nothing_is_kept` (at its own prices and written scale no account keeps more than one unit's price of its
    dearest luxury a person); `the_tiers_buy_what_households_must` (each product's `demand_gap` within 1/100,
    leisure's within 1/100); `tier_money_has_its_sizes` (within 1% at written contents); print the number of scaled
    accounts and their median scale (the prototype's 236 counties of 3,144, median 1.25, is the size, never asserted),
    each key's money a person and reach, the lowest, median and highest `no_earner_estimate` and `residence_estimate`
    (the prototype's $846, $1,019 and $1,691 a no-earner person by county under the regrouping with the border,
    `more/variants-lead.md`, V-j, are the size, never asserted), `own_price_gap` by product, each service of the
    place's `idle` and `unserved` shares with its three lowest and three highest states, each country service's
    capacity and use, the count of parts that send a share to the fund and of parts the fund pays, the sum of the
    grants, and the lowest and highest share (the prototype's counties under one share, 1,867 of 3,144 short and
    1,237 short even keeping all their own taxes, V-j, are the size, never asserted).
  - `the_fund_closes_with_its_grants` (slow): the fund's receipts by the parts' shares, at the exact solve, equal
    Task 10's `BEN` plus the grants within `sum over long parts of T_c / 10_000` plus $1 a period; print the gap
    between Task 10's `BEN` and the estimated benefits of decision 6.
- [ ] **Step 2: Run them and see them fail. Step 3: Implement. Step 4: Run them and the gate.**
- [ ] **Step 5: Commit** with the subject above.

What the player would see: four standards from the first period: the bottom half getting by, the next 40%
comfortable, the owners affluent, every household with no earner fed.

### Task 12: The builder, part 5: foreign regions in balance (O11)

Commit `feat(reference): give each foreign region its mix of jobs and its share of trade`.

**Why.** The prototype did not do it. The first draft's method stands in part: a region's jobs follow the hours its
output needs, and one factor a region balances its trade. What it lacked: the region's money, which sets what its
households buy; the closure that fixes it (its employed must be needed); and the export mix by good, which must add
up to the nation's exports of each good so that the country's workers stay needed. Under ruling 2 business services
cross too, between businesses only: a region's households buy theirs at home, so what a region buys of them from
the country is a share of its businesses' requirement alone (decision 4, E2).

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
    export_bps: Mapping[str, int]             # by crossing product: the five priced goods and business services
    money_per_person_micros: int
    sales_micros: int; purchases_micros: int  # a period: to the United States, from it
    luxury_scale_bps: int | None
# region_prices is Task 10b's (its decision 9), moved there so that Task 11 can price an account's shop abroad
def regions(o: Opening, census: Census, w: Written, t: Tiers, settings: Settings) -> Mapping[str, RegionOpening]:
    ...
```

**Decisions:**
1. **A region's prices** are Task 10b's `region_prices` (its decision 9): each product's at the region's census
   wage, and a shop good as its retailers post it, with the region's `export_bps` of the round passed in.
2. **What a region sells** to the country: `s[r][i] = sigma[i][r] x m[i] / u[i]` units a period (Task 10 decision 3;
   for a crossing service `sigma` is read from the census's `crossing_force`, E2),
   valued at the region's prices: `S_r`. A region with none sells nothing and buys nothing (`export_bps` 0).
3. **What a region needs.** In units a period, with the written recipes: `A[i][j] = inputs / n`; machines as an
   input, `sum over trades (L_j / n_j) / (160 x workers_per_machine[j] x life)` units of equipment a unit of `j`;
   public provision 1 a person; retail hours from the blocks on the shop goods its households buy. Its households are
   one account (`PooledExternal`: persons, households from the census) whose money a person `mpp` buys the written
   tiers by R4 at the region's prices (tier 1 needs, the wants, then scaled luxuries if money is left: call 20 holds
   abroad too). So final demand `f(mpp)` is piecewise linear and rising in `mpp`.
4. **What it buys from the country.** `b[r][i] = beta_r x c_i x R[r][i]` for a crossing good, `R` the region's own
   requirement of `i` (`(A y)[i] + f[i]`), `c_i` one figure a good, `beta_r` one a region. For a crossing service
   (business services; ruling 2, E2) `R[r][i] = (A y)[i]` alone: the region's households buy theirs at home, so
   the region buys from the country a share of its businesses' requirement, and its households' `f[i]` is made by
   its own workers. Output `y = K (f(mpp) + s - b)`, `K = (I - A)^-1` computed once exactly (the same recipes for
   every region).
5. **The closure.** For fixed `b`, `mpp` is found by bisection on whole micros so that the hours `y` needs (recipes'
   hours and retail hours) are at least the region's `employed x 160` (the largest `mpp` whose hours do not exceed
   it, then the next micro): its workers are needed and its households spend what they make. If the hours at `mpp =
   0` already pass `employed x 160`, the region cannot make what it sells: `abroad_unbalanced: <region>`.
6. **The balance and the mix, iterated.** Start `beta = 1`, `c_i = (X[i] / u[i]) / sum_r R0[r][i]` with `R0`
   from `b = 0`.
   Each round: solve each region's `mpp` (decision 5) at the current `b`; recompute `R`; `beta_r = S_r / sum_i
   p_us[i] c_i R[r][i]` (purchases at the country's written prices equal sales); `c_i = (X[i] / u[i]) / sum_r beta_r
   R[r][i]` (the regions together take the country's exports of each good, business services included, Task 10);
   both on `SHARE_GRID`; the region's prices (decision 1) are taken again with the round's shares. Stop when
   every written figure (decisions 7 and 8) is unchanged between two rounds; after 100 rounds, `abroad_unsettled`.
7. **Weights.** A region's hours by trade, shared over 10,000 by largest remainder (`apportion`); a trade at 0 takes
   1 from the trade with most (the policy refuses 0, `admission.rs` `profile`). Written in the policy's Ord order.
8. **Shares.** `export_bps[r][i] = half_up(10_000 x beta_r x c_i)`; above 10,000 is `export_share: <region>/<good>`.
   Each region balances by construction; the nation does too (O6.3), up to the rounding of shares and of import
   prices to written micros, which Task 13 reports. For business services the share is what the country sells the
   region over the region's business buyers' demand (ruling 2, K1, E2): each buying site abroad takes
   `floor(required x export_bps / 10_000)` from the country, by shares, so the share is met up to that rounding.
9. **Scales abroad.** A region whose money passes its three tiers has `luxury_scale_bps` as Task 11 decision 10.
   It is written as `<counterpart key>:pooled-external` (`builder_keys.rs` `luxury_scales` splits at the last `:`
   and admits a counterpart's key as the place, and the key label is `pooled-external`). The dependency is one entry
   of the census (`"dependency"`) and one `[dependency]` profile, but the compiler admits its places by M49 code
   (`UsDependency::from_m49`), so its scale is written as six rows at the same scale, `016:pooled-external`,
   `316:pooled-external`, `580:pooled-external`, `630:pooled-external`, `581:pooled-external` and
   `850:pooled-external`. Above 1,000,000 is `luxury_scale_bound: <region>`.
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
  - `a_scale_abroad_is_written_where_the_compiler_admits_it`: a hand region `canada` with scale 12,500 gives the row
    `canada:pooled-external = 12500`; the dependency at 11,000 gives the six rows of its M49 codes at 11,000.
  - `a_region_buys_business_services_for_its_businesses_only` (ruling 2): a hand region whose sites need 30 units
    of business services and whose households 10: its `R` of business services is 30, its households' 10 are in
    its own output `y`, and with `beta_r c_i = 1/5` it buys 6 units from the country, `export_bps` 2,000.
  - `a_region_s_business_services_sales_follow_the_census`: two hand regions with `crossing_force` of business
    services 3 to 1 (one buying trade, `a / h` alike) and `m` of 40 units: they sell 30 and 10 units to the country.
  - On the committed tables (slow): `the_nation_balances_by_the_regions` (exports equal imports in money within 1%
    at written figures); `every_region_balances` (within 1%); print each region's weights, shares,
    `mpp` and its tier reach, and the country's exports of business services over their output (the prototype's
    15.1% under the regrouping with the border, `more/variants-lead.md`, V-j, is the size, never asserted).
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
POLICY_BOUND: Final = 262_144              # the compiler's bound on a policy of schema 8 (`admission.rs` `parse`,
                                           # raised by Task 1b, E4); it moves only with that bound (decision 3)
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
   household and wage fractions, the installation figures of `[equipment]`, and `[markets] place_services`,
   `journey_timing` and `service_reach`) is the fixture's, unchanged. `[companies] opening_treasury_bps` is 0, as
   Task 7a leaves the fixture (the Director's ruling of 20 November: a company takes no working capital at the
   opening); `render` refuses a template in which it is not (`template_marker: opening_treasury_bps`).
   The fixture's commodity labels, grams and opening prices (which decision 4 of Task 10b and its labels read) stay
   in the template as one line each, `#@fact <key> | <label> | <unit label> | <grams> | <price micros>`;
   `template_facts` reads them and `render` drops them. `render`
   replaces each marker with TOML it writes itself: keys sorted inside a table, integers only, `\n` line ends, no
   trailing spaces. An unknown marker, one left over, or a computed block with no marker is `template_marker:
   <name>`.
2. **What the builder writes** under the ruled settings: every `[commodity.<key>]` but the deposit's (label, unit label,
   kind from `service_stage`: utility, business services and housing `"utility"`, household services, leisure and public
   provision `"service"` (ruling 1), cargo class kept, grams, the four prices, `handling_hours` and `handling_units` on
   the shop goods); every `[process.<key>]` (output, `output_units_per_batch`, `labor_hours_per_batch`, inputs,
   `margin_bps` but public provision; extraction with its deposit); the six `[[household_needs]]` (28, 28, 28, 28, 28
   and 1 on their bases); the `[[household_wants]]` rows (tier `comfort` or `luxury`, basis `persons`, units);
   `[markets] import_bps` (the five priced storable goods and business services, K1), `crossing_services =
   ["business_services"]` (K1), `country_services = ["business_services", "leisure", "utility"]` (K2, sorted) and
   `paying_order` (food, materials, consumer goods, utility, housing, business services, household services, leisure,
   resources; ruling 1); `[financial]` `wage_tax_bps` and `operating_income_tax_bps` equal, `private_distribution_bps =
   10000`, `reserve_food_support_periods = 1`; `[fund]` with `evidence_class = "Designed"`, both shares `fund_share_bps`
   (the national figure; the compiler reads the parts' table where it is not empty, K4), `reserve_periods = 2` and
   `share_by_part` with every domestic part's `share_by_part_bps` (K4); a `[[place_grants]]` row for each part of
   `place_grant_micros`, `part` and `amount_per_period_micros` (K5), in label order; the programs: `laid_off`
   (`recipients = "earning_or_residence_at_opening"`, after layoff, rank 0, 5,000 and 13), `no_earner` (kind
   `own_needs`, rank 0, `share_bps = 10000`, recipients `no_earner_at_opening`; E8) and `residence` (kind `own_needs`,
   rank 0, `share_bps = 10000`, recipients `collective_residence_at_opening`; E8, call 18), with no amounts: the
   compiler works each recipient's amount out (Task 4); the luxury scales (`[luxury_scale] by_account`, as Task 1 admits
   it); `[equipment] workers_per_machine` (eleven trades) and `machine_life_periods = 100`; for each region and the
   dependency `function_weights_bps`, `export_bps` (the five priced storable goods and business services, K1) and
   `price_scale_bps = 10000`; `[grain.basis]` 16, 16, 1, 14,000 (the shipped food figures, O15); `[household_time]
   unmet_hours_per_unit = { food = <max(1, half_up(20 / 28))> }` (today's 20 hours for a person's period of food: 1). No
   `[builder]` section (call 16). The markers for the keys of the rulings are `crossing_services`, `country_services`,
   `share_by_part`, `place_grants` and `programs`; the inline table `share_by_part` is written on one line, keys sorted.
   The census was taken on Part I's census scenario (E3), so `country_services` is written exactly as that scenario has
   it, and the wants cover exactly the products it gives a want row and households do not need (consumer goods, business
   services, leisure): each of them keeps at least one want row after rounding (Task 11, decision 9), else `wants_cover:
   <product>`, and no other product that is not a need gains one.
3. **Size.** The file is at most `POLICY_BOUND` bytes, else `scenario_size`. The parts' shares (316 entries of about
   22 bytes) and a grant row for each short part (about 77 bytes a row) add about 15,000 bytes to the 25,000 the
   first draft estimated: about 40,000, under 65,536 and far under the 262,144 of schema 8 (E4). No table of
   amounts is written (E8).
4. **Settings: only the ruled values.** `build` calls `check_ruled` (Task 9, decision 2) before it reads a table:
   any choice at another value is `setting_not_ruled: <field>`. Every ruled value has its keys in the compiler
   (K1 to K5, Part I), so nothing waits for a variant and `render` refuses no setting. The settings, each field, are
   written in the metadata (decision 6).
5. **Balances as written** (design 8.1). `written_balances` recomputes O6 at the written figures: 1, the place accounts'
   money (Task 11) against what they buy by R4 at written contents, scales and their own posted prices; 2, taxes at the
   written rates on the exact bases, every site's operating income taxed, public-owned ones included (Task 11, decision
   11's `T_c`), with the fund's split of Task 4 (`floor(rate x share / 10_000)`) at each part's `share_by_part_bps`,
   against grants, support and benefits at written amounts: for the nation, for the fund (its receipts against `sum
   estimate x persons` over the no-earner and residence recipients plus the sum of `[[place_grants]]`; the benefits are
   the builder's estimate, Task 11 decision 6, since the compiler works the amounts out; the gap to Task 10's `BEN`, on
   which the tax was sized, is written and printed), and for each part (its kept taxes, payout and grant against its
   payments; the 1/100 applies to the nation and the fund, each part's residual is written to the metadata and the
   largest printed); 3, exports at written prices and shares (Task 12) against imports at the regions' written prices;
   4, wear at the written machine price over the census's machines against equipment bought at the written price. Each
   residual over its flow at most 1/100, else `balance: <n>` (the build refuses to write numbers that do not close).
6. **Metadata** (the builder's balance sheet, design 8.1): `contract: NationalOpeningNumbersV1`, `issue: PER-371`; the
   sha256 of the accounts and pay files and of the census's JSON text (decompressed, not the `.gz` bytes), the template
   and each of `BUILDER_SOURCES`; the settings, each field, with the ruling that set it (26 November, rulings 1 to 6);
   `lam`, the rate, the fund's national share, the export factor, `cbar`, `C`, the estimated no-earner amounts' and
   residences' amounts' lowest, median and highest and their sum (an estimate: the compiler's amounts are Task 4's, E8);
   three keys Task 15 reads, by these names and shapes: `benefits.estimated_dues_micros`, an object `{"no_earner":
   {<part label>: <micros>}, "residence": {<part label>: <micros>}}`, each figure a part's estimated dues a period
   (`estimate x persons`, summed over its keys, net of county support as Task 11 decision 6 estimates them), integers;
   `shops.estimated_price_micros[<part label>][<budget key label>][<good>]`, the estimated posted price of a unit of
   each shop good to that part's accounts of that key (E7), an integer; and `recut.moved[<reason>][<product>]`, Task 9's
   `moved` (reasons `R1`, `R2`, `R3`, `O4_inventories`), USD thousands a year as the string `"n/d"` beside its decimal;
   the parts' shares and grants (each part's taxes, payout, payments, share and grant, the count sending a share and the
   count paid a grant), business services' import share with its weights by trade and region (Task 10, decision 3) and
   each region's `export_bps` of it (Task 12), the shops' saving by good (ruling 6), and `country_services` with each
   one's capacity and use (Task 11, decision 12); for each trade its persons at work, wage, hours, output, inputs,
   margin (accounts and written), wear, operating income, public-owned part, tax, payout, what firms, households, public
   bodies and the regions take, what its buyers save abroad, and `batch_hours_lost`; each recipe's exact and rounded
   cost and error; each want's exact and written units; each product's `demand_gap` and `own_price_gap`;
   `state_services` with each service of the place's `idle` and `unserved` shares (Task 11, decision 12); the four
   balances at the exact solve and as written; each key's money a person and reach, nationally and by place; the scaled
   accounts; each place's body (taxes, payout, payments, its share and its grant), and the parts whose payout alone
   passes their payments, with what each keeps above even (Task 11, decision 11); each region's weights, shares, money a
   person, sales and purchases; what was moved and dropped by rule; the two designed cross-border claims
   (`cross_border_ownership_bps` of Wayne's private consumer goods plants to Japan and of Canada's plants to Wayne,
   `financial.rs` `foreign_claim`), which the solve leaves out as the prototype did, at their size a period; the tier
   solve's steps, its second start's result; the regeneration command
   `UV_PROJECT_ENVIRONMENT=.venv mise exec -- uv run --frozen python tools/make_national_opening_numbers.py`. JSON
   with `indent=2, sort_keys=True` and a trailing newline; every `Fraction` written as the string `"n/d"` and beside it
   a decimal string to 9 places, rounded half up (for reading only).
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
  - `a_setting_not_ruled_is_refused`: `build` with `place_body = "one_share"` gives `setting_not_ruled:
    place_body` before any file is read (the paths given do not exist); `Settings()` passes that check.
  - `render_writes_the_keys_of_the_rulings`: on a hand `Written`, `Tiers` and regions of two parts, the rendered
    text parses with `tomllib` and holds `[markets] crossing_services = ["business_services"]`, `country_services =
    ["business_services", "leisure", "utility"]`, the ruled `paying_order`, `kind = "utility"` on utility, business
    services and housing, `import_bps` and each region's `export_bps` with exactly the five priced storable goods
    and business services, `[fund] share_by_part` naming both parts, one `[[place_grants]]` row for the short part,
    and `no_earner` and `residence` of kind `own_needs` with `share_bps = 10000` and no `amounts_micros`.
  - `the_wants_cover_the_census_scenario_s_products` (E3): a hand `Tiers` whose leisure rows all round to 0 gives
    `wants_cover: leisure`; the rendered `country_services` equals the census scenario's list.
  - `the_committed_scenario_names_its_inputs` (fast): the committed metadata's sha256 of the accounts, pay, census,
    template and every `BUILDER_SOURCES` file equal the files' digests.
  - `the_committed_scenario_fits_its_bound` (fast): at most `POLICY_BOUND` bytes; `schema_version = 8`.
  - `a_scenario_over_its_bound_is_refused`: `render` of a hand `Written` on a template padded past `POLICY_BOUND`
    bytes gives `scenario_size`.
  - `the_committed_scenario_is_what_the_builder_writes` (slow): build into `tmp_path`, equal bytes of both files.
  - `the_balances_as_written_close_within_one_percent` (slow, from the build): each of the four, balance 2 for the
    nation and for the fund with its grants.
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
defines.toml`, with the keys Tasks 1, 1b, 3 and 4 admit: the `own_needs` rows, the fund's share by part, the place
grants, the country services, the crossing service and the luxury scales among them.

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
2. **The census check** now reads the rebuilt scenario through `census_scenario` (Task 8, decision 5) and must still
   equal the committed census:
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

### Task 14b: Own prices, the shop's paid price, and the refusal under cost

Commit `feat(economy): open each workplace at its own cost, the shop at what it pays, refuse a product under cost`.

**Why, read from the code (`1a97bf28a`).** Every offer is the scenario's national price at the site's price scale
(`markets.rs` `wire`, L101-128: `price.scaled(actor.price_scale_bps)`), and a shop posts a good at the national price
plus its charge (`retail_stock`, L522-577: `price.opening` plus `handling_charge`), whatever it paid for it. O5 sets a
workplace's own price by its own wage. The Director ruled on 26 November that the shop "sells each good at what it
paid plus its charge, so goods from abroad are cheaper in the shop. It reads 'the shop charges labor only'
strictly" (ruling 6, D6, V10). A shop buys a good from up to three home makers and one abroad (Tasks 5 and 7d: its
restocking rows, each with a cap), at each maker's own price.

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
/// What a shop pays a unit of a good (D6): over its restocking rows of the good, home and abroad, the sum of each
/// row's cap times its supplier's own opening price, over the sum of the caps, rounded up. Where the good has no
/// maker anywhere (`procure` finds no provider of it and writes no row), the good's national price.
/// # Errors
/// `Policy` for a shop whose customers need or want the good, of which a maker exists, and that holds no restocking
/// row of it; `Arithmetic` on overflow.
pub(super) fn paid_price(builder: &Builder<'_>, shop: SiteId, key: &str) -> Result<Currency>;
/// The opening's national wage of a trade: floor(census payroll / (census employee persons x 160)), summed over its
/// domestic sites.
pub(super) fn opening_national_wage(builder: &Builder<'_>, trade: EconomicFunction) -> Result<Currency>;
/// O5's refusal: national price x n >= L x national wage + sum(inputs x national prices) + wear per batch.
pub(super) fn refuse_under_cost(builder: &Builder<'_>) -> Result<()>;
```

**Decisions:**
1. Under schema 8 every workplace's offer, and every figure that reads its price (opening stock's cost,
   `source_stocks` and opening cash, a provider's fee, equipment's carrying value), uses `own_price`, its minimum,
   maximum and step moved by the same ratio as the scenario's own (rounded down, each at least 1 micro). Foreign and
   dependency workplaces too (their wage is a fraction of the country's; no price scale, Task 14a). `own_price` is
   for the site that makes a product.
2. **The shop posts what it pays** (ruling 6, D6). A shop makes no product: its posted price of a good is
   `paid_price` plus its own charge at its own wage (Task 3, decision 4), and its minimum, maximum and step are the
   scenario's moved by the ratio of `paid_price` to the national price (rounded down, each at least 1 micro), the
   charge then added to the opening, the minimum and the maximum as today. Its opening stock is valued at
   `paid_price`, and its working cash (`retail_stock`'s `working_capital_periods x required x price`) reads it too.
   So a good bought abroad below the country's price is cheaper in the shop, and the shop has no income from the
   difference. A foreign or dependency shop posts by the same rule. A rounding up of the average means a shop never
   posts a good below what its rows cost it on average.
3. **The shop pass.** Today `households` calls `retail_stock` and then `procure` for each (shop, good)
   (`markets.rs` L504-518 at `6f392489e`). After Task 7d a shop's restocking rows are written by one dealing of a good
   over every home buyer (shops, recipe inputs, installation inputs), and the recipe and installation buyers are known
   only in `producers` and `equipment::wire`, which `markets::wire` calls after `households` (L151-153). So under
   schema 8 `households` returns its `retail_requirements` (shop, good, required) without setting any shop's offer,
   stock or working cash, and a pass of its own, `shop_offers(builder, &retail_requirements)`, runs in
   `markets::wire` after `super::equipment::wire` (L153) and before the sorts (L154-166): for each (shop, good) it
   calls `retail_stock` with `paid_price` read from the rows Task 7d wrote. Makers' offers are set in `wire`'s first
   loop (L91-137), so every supplier's own price is final by then. Under schema 7 `households` keeps today's order
   and calls, and the bytes are today's (offers and rows are sorted at the end either way).
   A shop with customers who need or want a good of which a maker exists, and no restocking row of it, is
   `NationalOpeningError::Policy` (Task 7d deals every such buyer). Where the good has no maker anywhere, the shop
   posts the national price; the test counts such shops.
4. **One national wage.** `opening_national_wage` is the census's `payroll_micros_per_period / (employee_persons x
   work_hours_per_person)` of the trade, rounded down: the figure the builder uses (Task 10, decision 1). Task 8's
   `national_wage_micros` (`pay.national_wage(f)`) is for reading only.
5. **The refusal** (O5): for every private trade with a recipe, at the national wage and national prices, with wear
   per batch the machine price over `service_batches_per_unit` of its trade's definition. Public provision is left
   out (its fee is not its cost). Distribution has no recipe and is not checked: Part II gives the shop no inputs and
   no margin (R3: its charge is labor only, Task 10 decision 1).
6. **The first-stage services** (ruling 1, D7): business services and housing are `kind = "utility"` in the
   rebuilt scenario; their prices follow `own_price` as every other trade's, and nothing here reads a service's
   stage.

- [ ] **Step 1: Write the failing tests:**
  - `own_price_follows_the_wage` (crate): national $5.00, recipe 16 hours for 100 units, margin 1,400 bps, site wage
    $40, nation $30: `5_000_000 + floor(10_000_000 x 16 x 11_400 / 1_000_000)` = 6,824,000.
  - `a_price_not_above_zero_is_refused` (crate): national $5.00, the same recipe, site wage $0, nation $40:
    `5_000_000 - 7_296_000` is below 0, so `Err(Price(trade))` with the trade passed in.
  - `a_shop_pays_the_average_of_its_rows` (crate test of the rounding, on figures passed in): caps 70 and 30 at
    $10.00 and $4.00 give $8.20; caps 2 and 1 at 10 and 11 micros give 11 (`ceil(31 / 3)`); no row gives the
    national price.
  - `the_shop_posts_what_it_pays` (rebuilt scenario): for every domestic shop and good it offers, the posted price
    less its charge equals `paid_price` recomputed in the test from its restocking rows and its suppliers' offers; a
    shop with a foreign row of a good posts it below the same good of a shop of its part with home rows only, where
    the foreign supplier's price is below the home makers' (print the count of such shops and the largest gap). Print
    and pin the count of (shop, good) pairs posted at the national price for want of any maker (expected 0 in the
    rebuilt scenario); a shop whose customers want a good it has no row of is `Err(Policy)`, shown on a copy of the
    rebuilt scenario with one shop's restocking of food removed by a test hook (`#[cfg(test)]`) or, if no hook is
    built, by an inline crate test of `shop_offers` on a builder of the crate's test helpers.
  - `a_product_under_cost_is_refused`: the rebuilt scenario with food's price set to 1 micro gives
    `Err(UnderCost(Food))`; the rebuilt scenario as written compiles.
  - `wayne_services_cost_more_where_pay_is_higher`: a Wayne household services site's price over the national price
    equals its labor part at Wayne's wage (recomputed in the test).
  - `the_census_does_not_follow_the_numbers` still passes.
  - Every pin that follows prices is re-pinned from the first failing run and listed with its old and new value.
- [ ] **Step 2: Run them and see them fail. Step 3: Implement. Step 4: Run** `binary(national_twelve_trades)`,
  `binary(national_opening_census)`, `binary(national_game_policy)`, `binary(national_opening)`,
  `binary(shipped_world_bytes)`, `binary(national_household_units)`, the grain's tests, the crate.
- [ ] **Step 5: Gate and commit** with the subject above. Hand over: the pins re-pinned, old and new; the shops whose
  posted price of a good differs from the national price plus charge by more than 1%, counted by good.

What the player would see: services that cost more in Wayne than where pay is lower, foreign goods cheaper than the
country's, and cheaper in the shop too: the gain from cheap foreign labor in the price of what households consume.

### Task 15: The opening's own report, before any period

Commit `test(persistence): the rebuilt opening's report before any period`.

**What the rulings of 26 November add to it.** Each part's public body opens even, the fund paying the poorer
parts' providers (ruling 4, D4): asserted for every part. The benefit is each account's own needs, worked out by the
compiler (ruling 3, E8): every account reaches tier 1, and the compiled dues are held against the builder's estimate
(within 1% for the fund's whole), with the spread by account reported. Business services cross the border by shares
(ruling 2, E2): the trade balance counts them. The shop posts what it pays (E7): the report gives the gap between
the builder's estimate of a shop's price and the compiled one.
Utility, leisure and business services are sold across state lines (ruling 5, D5): the report gives how much of
each crosses one, and, for the services that stay in their state or place, each state's use against its own
providers. The shop posts what it pays (ruling 6, D6): the report gives its prices. Services are regrouped (ruling
1, D7): the report names what is still spread by O4 and what stays bent (housing cannot buy business services).

**Files:**
- Create: `rust/crates/babylon-persistence/tests/national_rebuilt_opening.rs`, `tests/support/opening_ledger.rs`;
  `reports/country-opening-v13/opening-report.json` (written by an ignored recorder)

**Interfaces:**

```rust
/// The opening's flows a period at posted prices and planned batches, read from the compiled opening only.
pub struct OpeningLedger {
    pub trades: BTreeMap<EconomicFunction, TradeLedger>,   // workers' hours, needed hours, revenue, costs, wear, OI
    pub accounts: Vec<AccountLedger>,                      // income parts, tier costs, standard, programs' dues
    pub bodies: Vec<BodyLedger>,                           // receipts, grants from the fund, payments: each part, fund
    pub abroad: AbroadLedger,                              // sales and purchases by region and product, services too
    pub services: Vec<ServiceUseByState>,                  // each service's use against its providers, by state
    pub shops: Vec<ShopPriceRow>,                          // each shop's posted price of each good against national
}
pub fn opening_ledger(opening: &EconomicOpening, policy: &NationalGamePolicy) -> Result<OpeningLedger, LedgerError>;
```

**Decisions:**
1. **Needed hours** of a trade: what the opening's buyers take of its product a period (each account's needs, and of
   its wants what its money reaches at its sellers' posted prices, tier by tier and, inside a tier, in the scenario's
   order of paying, each row whole until the money ends, as the engine buys (ADR313's amendment of ADR312 P7); every
   recipe's inputs at planned batches; foreign buyers' rows to domestic suppliers and their service inputs from
   domestic providers (Task 7e); equipment replacement due, public providers' included; public provision's need) over
   output a batch, times its batch hours. Retail: handling hours of every shop good households take, through the
   blocks. The builder sizes the tiers by the tier solve on the 187 pooled places' accounts at national posted prices
   (Task 11), where the national accounts close. So needed hours are counted twice: with every account buying at the
   national posted prices (asserted), and with every account buying at its own sellers' posted prices, as the engine
   buys (reported).
2. **Revenue** of a site: planned output times its own price. **Costs:** payroll, inputs at planned batches at their
   suppliers' prices, wear (machines' service used a period at their price over their life). **Operating income:**
   revenue less costs. **Tax:** rates of its rows, the part's and the fund's. **Payout:** operating income less tax,
   at 100%.
3. **An account's income:** its wages less wage tax, support, programs' dues (a tag-3 due by Task 4a's rule), payouts
   by its shares. **Its tier costs** at its sellers' posted prices; its standard as `household_standard` would read
   it at those figures.
4. **Public bodies.** A part's body: its receipts are its rows of both taxes (after the fund's share) and the earnings
   of the sites it owns; its grants from the fund are the fund's `ProviderOperatingGrant` rows to its providers
   (Task 4, decision 3), counted as the part's own; its payments are its own allocations plus the fund's rows to its
   providers (so each provider's whole grant), county support and the City PD, at their amounts. The fund: receipts its
   tax rows, payments its programs' dues and its grants. The
   nation's balance counts the domestic parts' bodies and the fund. Each foreign region's and the dependency's own
   bodies (`financial.rs:42-69`) are reported beside it, receipts against payments, and not asserted.
5. **Abroad.** Sales and purchases by region and product: goods by their restocking rows, and every service input
   whose buyer and provider are on two sides of the border (Task 7e), at the provider's posted price times the row's
   share of the buyer's requirement at planned batches, by Task 7f's `input_shares` (not the row's cap). The trade
   balance counts both.
6. **Services by state.** For each service, each state's use (what its own buyers take, at the sellers' posted
   prices, as decision 1) against what its own providers can make. For the services sold only in their place or
   their state (`place_services` and any service in no list), the shares idle and unserved by state, as the
   prototype counted them ("What the prototype found", "Places"); for the country services, also the share of units
   dealt to a provider in another state (Task 7b).
7. **Money.** The opening's money is the sum of every account's opening cash: households, sites, public bodies, the
   fund, organizations. It must equal the catalog's own sum of opening cash, and one period of the ledger's flows
   moves money only between accounts.
8. No figure is averaged; every share is two sums divided, in basis points.

- [ ] **Step 1: Write the tests** (each fails until the ledger exists):
  - `every_trade_needs_its_workers`: for each trade, needed hours at the national posted prices within one batch a
    site or 1% of its workers' hours, whichever is larger; retail within 1%. The report also gives needed hours at
    the sellers' own posted prices against workers' hours by trade, by trade and place, and by service and state
    (decision 6); none of those is asserted.
  - `every_workplace_is_asked_for_its_work` (design 8.2: "jobs needed against jobs present, by trade and place"):
    for each domestic workplace with persons at work, what the opening's buyers ask of it a period (its dealt
    accounts' needs and reached wants, its dealt sites' inputs, its buyers abroad, its home caps, machines due) over
    what it can make. Asserted: for each trade, the persons at work at workplaces asked for under half of what they
    can make are under 25% of the trade's (as the compiler dealt before Tasks 7b to 7d they were 32% to 66%; the rule,
    run outside the engine on the fixture with what is asked scaled to what can be made, leaves 1% to 10%, and for the
    three country services under D5 with E1 0.0% for utility, 0.3% for leisure and 2.1% for business services,
    counted on the dump). Reported: the same share by trade for under half and for over twice, and
    every shared freight pool whose opening use passes its room (O15). A figure that fails is reported and not
    loosened.
  - `every_workplace_can_pay_for_its_first_period` (Task 7a's test, on the rebuilt scenario): for every domestic
    workplace with a service-input row, opening cash less its payroll less the row's cash floor is at least what its
    service inputs of one period cost at their providers' opening prices. Here the prices follow each provider's
    own wage (Task 14b), so a workplace whose provider is dear is the one to fail: a failure is reported with the
    workplace, its cash, payroll, floor and cost, and nothing is loosened.
  - `every_private_price_covers_its_cost_at_the_national_wage`: national price x n at least labor, inputs and wear.
  - `no_account_opens_going_without`: every domestic account's income reaches its tier 1 at its own sellers' posted
    prices; pin the count of accounts at each standard and each band's income per person (from the first failing
    run).
  - `nobody_is_paid_above_their_needs` (ruling 3, E8 and the lead's decision on A-S6): for every domestic no-earner
    account with persons, its whole public income at the opening (its `no_earner` due and its county support) is at
    least its needs' cost at its own sellers' posted prices and less than that cost plus its persons in micros, but
    where its county support alone passes its needs (then the due is 1 micro a person); for every residence account
    that `residence` pays, the same of its jobless residents' person-basis needs. Asserted against the builder: the
    sum of the compiled dues of each program within 1% (100 bps) of the builder's estimate, the metadata's
    `benefits.estimated_dues_micros["no_earner"]` and `["residence"]` (a part's estimated dues a period, summed over
    the parts). Reported: the lowest, the median and the
    highest amount a person (no earner, residence), the part of each, Wayne's, and the builder's estimate against the
    compiled amount by part.
  - `the_four_balances_close_within_one_percent`: households' tier money against income; public receipts against
    payments (nation and fund); exports against imports, services counted (decision 5); profit kept against
    equipment: each residual at most 100 bps of its flow.
  - `every_public_body_opens_within_one_percent` (ruling 4, D4): for every domestic part, its receipts and its grants
    from the fund against its payments, the residual at most 100 bps of its payments. Reported: each part's
    receipts, grants and payments a period, the parts with a grant row and the sum of the rows, the lowest and
    highest ratio of receipts to payments before the grants.
  - `the_opening_conserves_money` (decision 7): the sum of opening cash over every account equals the catalog's sum,
    and the ledger's flows of one period sum to 0 over all accounts.
  - `sellers_under_their_own_cost_are_reported`: every site whose own price is under its own cost (labor at its own
    wage, inputs at its suppliers' prices, wear) is written into the report with its trade, place and gap; the count
    is printed, nothing asserted (design 8.2).
  - `the_shop_s_prices_are_reported` (ruling 6): for every shop and good, its posted price less its charge against
    the good's national price, and the share of its restocking caps from abroad; the count of shops below the
    national price and the largest gap are printed; and, by good and part, the builder's estimate of the shop's price
    (E7: `ceil((home share x national price + import share x the foreign supplier's own price) / 10_000)` plus the
    charge, the metadata's `shops.estimated_price_micros[<part label>][<budget key label>][<good>]`) against the
    compiled posted prices of the part's shops; nothing asserted (Task 14b
    asserts the rule).
  - `what_is_still_spread_is_reported` (ruling 1, D7): the report copies from the scenario's metadata
    (`content/scenarios/national-rebuilt/defines.metadata.json`, `recut.moved[<reason>][<product>]` in USD thousands a
    year for the reasons `R1` (a service cannot buy a service of its own stage or later), `R2`, `R3` and
    `O4_inventories`, with their sum by reason) and states what stays bent: housing and business services
    are first-stage and cannot buy one another or utility. Nothing asserted.
  - `tier_money_is_within_one_percent_of_its_sizes`.
  - The shipped world's pins: `binary(shipped_world_bytes)` in the gate.
- [ ] **Step 2: Run them.** A test that fails on a figure is reported with the figure, never loosened: the lead
  decides whether the builder or the compiler is wrong.
- [ ] **Step 3: Record** `opening-report.json` with the ignored `record_rebuilt_opening_report`: the ledger's sums by
  trade, by trade and place, band, body (each domestic part's body with its grants, the fund, each foreign region's
  and the dependency's) and region (goods and services), the services by state (decision 6), the shops' prices, the
  no-earner and residence amounts, and the sellers under their own cost (design 8.2), under 1,048,576 bytes.
- [ ] **Step 4: Gate,** `mise run check:hygiene`, **commit** with the subject above and the report.

What the player would see: nothing directly; it is the record that the opening the player starts from is in balance,
every place's public body even and nobody with no earner going without.

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
   `country_fund::with_fund` to an opening that holds programs (Task 4, decision 12). So the sets are: `as-ships` (the
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

## Ruled by the Director on 26 November

The plan was drafted with seven choices open, each built at the approved text's default with its variant written
out. The Director ruled all seven on 26 November 2026, each time as the lead recommended. ADR326 holds the picks
word for word. The ruled variants are now the plan's built text. The names V1 to V12 stay in use because the
records below speak of them. Until 26 November this section was "For the Director", and the records below call it
that; an "item" there is a row of this table.

| | Choice | Ruled | Was | Built in |
|---|---|---|---|---|
| 1 | How services are grouped into stages | Regrouped, with no engine change | V6 | Tasks 9 and 13; Task 15 |
| 2 | Whether business services cross a border | They cross | V8 | Tasks 1b, 7f, 7e; Tasks 9, 10, 12, 13; Task 15 |
| 3 | The benefit and local prices | Each place's own cost | V3, road (b) | Tasks 1b, 4a, 4; Tasks 11, 13; Task 15 |
| 4 | Each place's public body at the opening | Every place opens even | V1 with V2's road (b) | Tasks 1b, 4; Tasks 11, 13; Task 15 |
| 5 | A service across state lines | Utility, leisure and business services cross | V9 | Tasks 1b, 7b; Task 11; Task 15 |
| 6 | What the shop saves on goods from abroad | Households, in the price | V10 | Task 14b; Tasks 10, 13 |
| 7 | Several sellers of one product in one place | Deal buyers, then measure | the plan's dealing | Tasks 7b to 7d; V11 for households before homes |

What each pick binds, in the Director's words:

1. "No engine change. The scenario puts utility, business services and premises in the first stage, and care,
   schools, leisure and public services in the second, so that those can buy their offices and premises." What
   stays bent: "first-stage services cannot buy one another, so housing does not carry its business services ... It
   can be put right with homes, when the builder is run again."
2. "The compiler lets buyers take a share of their business services from across the border, by the accounts' own
   import and export shares." The country then "pays for part of the periphery's goods with offices' work (finance,
   law, management) and not with machines ... and it puts that exchange on the map."
3. "The benefit is what the needs cost in that place: nobody with no earner opens going without, and nobody is paid
   above their needs. It is still one rule, 'the needs in full', which politics can cut or raise as a percentage."
4. "A place that collects more than it needs sends the rest to the national fund. Where a place's own taxes are too
   few, the fund pays that place's public providers directly ... Those payments are a row of the fund that politics
   can later cut, and in a slump the places that live on them are hit first."
5. "Utility, leisure and business services are sold across the whole country, each buyer's demand shared over
   providers by what they can make ... Housing and household services (care, schools) stay in their own state; the
   8% and 6% that sit in the wrong states stay as a difference between regions, in play."
6. "The shop sells each good at what it paid plus its charge, so goods from abroad are cheaper in the shop."
7. "Only the three compiler tasks, already in the plan. Each household still has one seller of each thing ... The
   bench then shows whether that is enough. Shared custom is built before homes."

The lead's decisions under these rulings are calls 32 to 37 of "Calls for the lead to confirm", and calls 18, 19,
21, 22, 25 and 28 to 30 were rewritten for them. The Director was told of them on 26 November; each is a small edit
if ruled otherwise.

## The keys and the lead's decisions under the rulings

The tasks name these by their labels. The labels come from the lead's two rounds of decisions on 26 November: D1 to
D8 before the amendment was drafted, E1 to E8 after its drafts and their counts. Where a later one replaced an
earlier, the text below is the later.

**The scenario's keys (schema 8).** A part's label is the header's ("A place and its parts"); a budget key's label
is `HouseholdBudgetKey::label()`.

- **K1.** `[markets] crossing_services = ["business_services"]`. Optional; sorted; each a period service of the
  scenario; absent means none. `[markets] import_bps` and every `[counterpart.<key>]` and `[dependency]`
  `export_bps` hold exactly the five storable goods that have a price and each crossing service.
- **K2.** `[markets] country_services = ["business_services", "leisure", "utility"]`. Optional; sorted; each a
  period service of the scenario; none of them also in `place_services`; absent means none.
- **K3.** A program kind `"own_needs"`: `rank`, `share_bps` (10,000 at the opening), `recipients`. No amount is
  written in the scenario. `no_earner` is `per_person` (one amount: the fixture keeps its row) or `own_needs`.
  `residence` is `own_needs` and the row is optional. `per_person_by_place`, which Task 1 built, goes.
- **K4.** `[fund] share_by_part = { "<part label>" = <bps>, ... }`. Optional. The fund's share of both taxes
  collected in that part. Absent or empty: the two shares of `[fund]` apply everywhere. Not empty: every domestic
  part of the opening is named, and the compiler refuses a part that is missing or names nothing.
- **K5.** `[[place_grants]]` rows: `part = "<part label>"`, `amount_per_period_micros`. Optional. The fund pays
  that part's public providers this much a period.

**The decisions.**

- **D1, as E8 has it: the benefit is each account's own needs, and the compiler works them out.** The Director's
  words: "nobody with no earner opens going without, and nobody is paid above their needs", and "one rule, 'the
  needs in full', which politics can cut or raise as a percentage". Only the compiled opening knows each account's
  sellers and their posted prices to the micro. For a recipient of an `own_needs` program the amount a person is
  the cost of its needs for one period at its own sellers' posted opening prices, over its persons, rounded up to
  a whole micro. For a residence account: its person-basis needs, times its persons with no job at the opening
  over its persons, rounded up; an account with no such resident is no recipient. An account carved from another
  is a recipient of its own. The builder writes no amount; it estimates them to size the fund.
- **D2. The engine's kind of program.** `PublicProgramTerms::PerPersonOwn { share_bps }` (tag 3) and
  `PublicProgram.own_amounts`, one for each recipient. A recipient's due is `floor(own amount x persons x
  share_bps / 10_000)`. The amounts are fixed; the share may change. The opening has three engine programs.
- **D3, as E2 has it: a business buys a crossing service at home and abroad, by shares.** A region abroad has one
  provider and a few buying workplaces, each a whole trade, as large as many home providers: whole buyers cannot
  be dealt across the border. So the engine lets a buying workplace hold a row a provider, each with a cap (Task
  7f), and a business takes its share abroad as it does of a good (Task 7e). Households on both sides keep one
  provider at home. The builder writes the shares over business buyers' demand.
- **D4, with E5 and E6: every part's public body opens even.** A part whose own taxes pass its payments sends the
  rest to the fund through `share_by_part`: `10_000 - floor(10_000 x (payments - payout) / taxes)`, at least 0 and
  at most 10,000, the payout being what its public-owned workplaces pay it. A part whose payments pass them keeps
  all its taxes and has a `[[place_grants]]` row of the gap, rounded up: the fund pays that part's funded public
  providers `ProviderOperatingGrant` allocations that sum to it, and the part's own body pays each that much
  less. The grants stand at priority 256, after every program, so a short fund cuts them first. The fund opens
  with two periods of its payments: the programs' dues and the grants.
- **D5, with E1: a country service is bought at home first.** Inside one kind of buyers, a buyer goes to the
  provider of its own state with the smallest ratio while that provider's ratio BEFORE the buyer is under the
  kind's national level; else it waits, and the buyers that wait are dealt over every domestic provider by
  `deal`'s own rule with the shares carried.
- **D6, with E7: the shop posts what it pays.** Over a shop's restocking rows of a good, home and abroad, the sum
  of each row's cap times its supplier's own opening price, over the sum of the caps, rounded up; then its charge.
  The builder cannot know which makers a shop is dealt, so it prices a shop good as an estimate.
- **D7. The kinds and the order of paying.** First stage: `utility`, `business_services`, `housing` (`kind =
  "utility"`). Second stage: `household_services`, `leisure`, `public_provision`. Order of paying: food,
  materials, consumer goods, utility, housing, business services, household services, leisure, resources. A
  first-stage service can buy no period service, utility included; the builder spreads that by O4.
- **D8. Not built:** V2's road (a), V3's road (a), V4, V5, V7, V12. V11 for households is built before homes.
- **E3. The census is taken on the census scenario** (Task 8): the fixture's text with `country_services` at its
  ruled value and a want row of consumer goods, leisure and business services, so that every account is dealt a
  seller of everything it will buy. The builder writes exactly that list of country services, and wants that
  cover exactly those products.
- **E4. The scenario's size bound** is 262,144 bytes under schema 8 and 65,536 under schema 7 and earlier.

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
    the opening, rounded up to a whole micro. The account is also a recipient of `laid_off`, so a resident who loses
    a job in play is paid as any worker is (the engine allows one after-layoff program a household and any number of
    per-person ones, `financial/validation.rs`). It keeps what it was at the opening, as O12 says of households.
    Ruled on 26
    November (ruling 3, E8, D2): each account's own needs, worked out by the compiler from the opening's own
    offers, so the residences are one program, `residence`, of kind `own_needs`, its recipients the residence
    accounts with a resident with no job at the opening, and the opening has three engine programs (`laid_off`,
    `no_earner`, `residence`). This replaces the first draft's item for the Director and its variant V5.
19. **The order of paying follows the stages:** a first-stage service stands before every second-stage service, as
    the compiler asks (`policy/admission.rs` `paying_order`), and the needs keep their order among themselves. Under
    ruling 1 it is food, materials, consumer goods, utility, housing, business services, household services,
    leisure, resources.
20. **An account above its three tiers has its luxury rows scaled so that it spends all** (design call 4), and the
    margin factor is set on the national bands. Part II builds it; the scale is a key of the scenario (Tasks 1 and 3),
    set at the account's own sellers' prices (Task 11, decision 10).
21. **Imports are paid at their sellers' own prices** (O5; Task 14b), not at national prices as in the prototype,
    and what a firm saves is its operating income (Task 10, decisions 6 and 7). The shop's saving goes to households
    in the price: ruled on 26 November (ruling 6, D6), the shop posts each good at what it pays for it plus its
    charge.
22. **Import shares are written for coverage** (Task 10b, decision 8): only a buyer whose second supplier is foreign
    imports (`procure`), so the written share is the accounts' share over those buyers' weight. Business services
    cross between businesses only, by shares (ruling 2, E2), so their share is the accounts' imports over the home
    business buyers' demand (Task 10, decision 3).
23. **A foreign region's closure** (Task 12): its households' money a person is what makes its employed needed; its
    purchases from the country are one figure a region (it balances) times one a good (the regions together take the
    country's exports of each good).
24. **The tiers are solved at national prices; own prices are counted** (Task 11, decisions 2 and 12). No one tier
    list makes what accounts buy at their own sellers' prices equal what households must buy (What the prototype
    found, "Places"). The benefit and the luxury scales are set at each account's own prices.
25. **Each no-earner account's own cost** (ruled on 26 November; it replaces the one figure at the dearest place):
    an account's benefit is its own tier 1 a person at its own sellers' prices (Task 11, decision 6); the census
    gives each account's sellers' wages (Task 8).
26. **Tests that build from the committed tables are marked slow** (Task 13, decision 8): the unit suite runs `-m
    'not slow'`, a fast test holds the committed scenario to its inputs' digests, and the lead runs the slow ones
    before a push that changes the builder.
27. **No Rust parse of the written scenario in Task 13** (run C is Python only): Task 14a opens it first thing.
28. **The plan's unit of accounts is the part, not the pooled place** (the header's "A place and its parts"): the
    census has a row a part, the luxury scales name an account of a part, and the fund's share and its grants name
    a part. The engine's 256 programs are no bound any more: a program pays each recipient its own amount (Task
    4a), which the compiler works out, so the opening has three programs.
29. **Buyers are dealt to sellers in proportion to the sellers' people** (Tasks 7b to 7d), by weights that read no
    recipe, price or want, so that the census of who sells to whom is the same whatever numbers the builder writes.
    `country_services` moves who sells to whom and no number, so the census is taken on the census scenario, the
    fixture with that key at its ruled value and a want row for every product households do not need (E3), and the
    rebuilt scenario writes the same list and wants that cover the same products (Task 13, decision 2).
30. **Three services are bought in the buyer's own place:** premises (housing), household services and public
    provision, a key of the scenario (`place_services`). Utility, business services and leisure are sold across
    the country, as ruled on 26 November (`country_services`), a state's buyers at their own state's providers
    first (call 34). The pick's words for housing and household services are "stay in their own state"; the buyer's
    own place is the lead's narrower reading, made before the ruling, so that a home and a clinic are where the
    household is. What sits in the wrong place is then more than what sits in the wrong state. Counted on the
    compiled twelve-trade opening with the numbers taken out (the table under "What the compiled opening
    showed", buyers sharing the sellers they may reach): of what household services can make, 5.0% cannot be sold
    in the buyer's place against 4.5% in its state; of premises 9.9% against 6.9%; of public provision 12.9%
    against 9.7%. The Director is told.
31. **A company takes no working capital at the opening** (`opening_treasury_bps = 0` in the fixture from Task 7a
    and in the scenario): not the lead's call but the Director's ruling of 20 November, restored here.
32. **The benefit is by account, and the compiler works it out** (under ruling 3). The pick says "nobody with no
    earner opens going without, and nobody is paid above their needs". A price follows its seller's wage and every
    account is dealt its own sellers, so two accounts of one part can pay different prices, and only the compiled
    opening knows them to the micro. So the scenario carries the rule (`kind = "own_needs"`, a share of 10,000) and
    Task 4 works out each account's amount from the opening's own offers; a residence account's is a resident's own
    needs for its residents with no job (call 18). The builder only estimates them, to size the fund.
33. **Only businesses buy a crossing service across the border, and by shares** (under ruling 2). A region abroad
    has one provider and a few buying workplaces, each a whole trade, as large as many home providers; so a
    business takes its share abroad as it does of a good, with a second row, and for that the engine lets a
    workplace take a service from several providers (Task 7f: the workplaces' half of V11, brought forward).
    Households on both sides buy at home: the engine holds one seller a household and good until V11.
34. **A country service is bought at home first** (under ruling 5). A state's buyers fill their own state's
    providers to the nation's level and only the rest crosses a state line, so that the map shows the imbalance
    between states and not a tangle (counted: a tenth of utility and of business services crosses, where a plain
    dealing over the country sent more than a third). The dealing still reads no recipe, price or want.
35. **The fund's grants to a part short of taxes are cut first** (under ruling 4): they stand after every program
    in the fund's order, as the pick says ("in a slump the places that live on them are hit first").
36. **Each part's public body opens even**, not each place on the map (under ruling 4): the fund's share and the
    fund's grants are set part by part, since each part has its own public body.
37. **A want carries its scale in the engine** (Tasks 3b and 3c): found by Task 3's review, which showed that a
    scale floored on one person's units did nothing for a luxury of one or two units a person.

## Settled by approved text

- **The fund at county 11001, opening with two periods of its payments as new cash.** Stage 4's plan B, item 1:
  "a budget `CashInProportion` (cap 0, floor 0) and two periods of its payments as cash (O13)". Since the rulings of
  26 November its payments are the dues of `no_earner` and `residence` and the place grants (E6).
- **Programs by household key.** Stage 4's plan B, item 4: `no_earner` "to every account with no earner at the opening
  ... owner or not", `laid_off` "to every United States worker account of every band. Both rank 0."
- **Support for those looking for work at the opening.** Design call 16: "Those looking for work at the opening keep
  today's county support" (today a period of food; Task 4, decision 6 keeps it a period of the food need).
- **Foreign regions balanced one by one.** Design O11: "A foreign region's mix of jobs is computed, so that the region
  is in balance by construction."

## Variants not built

V1 (with V2's road (b)), V3 (by its road (b)), V6, V8, V9 and V10 were ruled on 26 November and are in the tasks.
What follows was not ruled in and is NOT built. It is kept as written before the rulings, in case of a later one:
its words on settings, branches and kinds are of the plan as it was then, and no module has such a branch now. An
"item" is a row of the table under "Ruled by the Director on 26 November".

**V2, road (a). A grant from the fund to a place's public body.** One public account may not pay another in the
engine (`validate_public`, `babylon-material-circuit/src/financial/validation.rs`, admits an allocation only as
`HouseholdIncomeSupport` to a household, `ProviderOperatingGrant` to a site or `AgencyAppropriation` to an
organization). An engine task would add a fourth `PublicTransferTreatment`, a grant to a public account, admitted
in `validate_public` and `PublicBudgetReceipt::validate` and written in the wire and the contract. The ruling took
road (b): the fund pays the place's providers.

**V3, road (a). A program row a place.** 187 rows `no_earner_<hub geoid>` beside the residences' rows would pass the
engine's 256 programs, and a place's two parts can pay different prices. The ruling is built by road (b), Task 4a.

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

**V7. One more stage in the engine** (item 1): utility and business services; housing; the rest. An engine plan of its
own before Task 1, about three tasks by the lead's estimate from reading the code: `ServiceStage` gains a stage
(`services/model.rs`), the period's loop over stages (`transition/state.rs`, about L1430) and the stage's market
moment (`services/admission.rs:694`, `clearing/table.rs` `MarketMoment`, whose order must then be decoupled from its
wire tag) follow, the compiler's `kind` gains a word for it, and every measured small world keeps its bytes. It
amends ADR264 (two stages) and ADR312 (the order of a period's steps). Part II: `Settings.service_stage` with a
stage 3, which Task 13 refuses until the compiler's word exists.

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

## What the rulings of 26 November and their one check changed

- The Director ruled the plan's seven open choices on 26 November (ADR326), each as the lead recommended. The
  amendment was drafted once, in two halves (the compiler and engine tasks; the builder's), with counts on the dump
  of the compiled twelve-trade opening, and checked once by two readers who had written none of it.
- **Added:** Task 1b (the keys), Task 4a (the engine: a program pays each recipient its own amount), Task 7f (the
  engine: a workplace may take a service from several providers) and Task 7e (a business buys a crossing service by
  shares). **Rewritten:** Tasks 4, 7b, 9, 10, 10b, 11, 12, 13, 14b and 15. **Edited:** Tasks 5, 7d, 8, 14a and 16.
- **What the drafts' counts changed in the lead's first decisions.** Whole buyers cannot be dealt across the
  border: a region abroad has one provider of business services and five buying workplaces, each a whole trade of
  tens of millions of people; so a business buys its share abroad with a second row, and the engine learns to
  share a requirement over rows (the lead's estimate of two or three tasks for the border became four). A country
  service dealt plainly over the country sent more than a third of utility and of business services across a
  state line; with the home test on the ratio before the buyer, a tenth. A table of benefit amounts written by the
  builder could not be exact, since a shop's price follows the makers it is dealt, and it would have passed the
  scenario's size bound; so the compiler works the amounts out and the scenario carries the rule.
- **What the check found in the compiler and engine tasks, and what was done.** After Task 7d a shop has no
  restocking row when its offer is set, so every shop would have posted the national price in silence: the shop's
  offers are now set in a pass of their own after the dealing. A no-earner account with people looking for work
  would have had its needs in full and the county's support on top: the amount is net of that support. A place
  grant would have shrunk the City PD's payroll grant, which its own check refuses: that site is left out. The home
  test of a country service could be read two ways with different results: one sentence and one hand case now
  tell them apart. A site abroad's export part dealt over sixteen providers left one provider asked for 17 times
  its room: with no limit, every home provider is asked exactly its room (1,141 rows). The census passes
  1,048,576 bytes as text: it is committed gzipped, and every digest is of its text.
- **What the check found in the builder's tasks, and what was done.** A part's taxes left out the tax its
  public-owned workplaces pay, so "every part opens even" would have failed in the compiled opening: they are
  counted. The fund's closing test asked for a dollar a part, which whole basis points cannot give: its tolerance
  is the rounding's. A luxury scale abroad was written under a label the compiler refuses: it is written as the
  compiler reads it. The census reader and the census disagreed on four names: they agree.
- **Three readings go beyond the picks' words, and the Director was told of each:** only businesses buy a crossing
  service across the border (call 33); a country service's buyers are dealt whole, at home first (call 34); and
  housing, household services and public provision are bought in the buyer's own place, where the pick says "in
  their own state" (call 30).

## What run B found in the build (26 November)

- **Task 7d stopped once, on the lead's own rule.** Its first builder built the task as written and two of its
  tests could not be met: with at most sixteen makers a buyer abroad, the sixteenth maker took what was left of a
  whole region's trade (53.6% of the people at food makers were asked under half or over twice the nation's ratio,
  against a bound of 10%, and seven makers were asked from abroad for more than twice their share). The builder
  changed no figure and stopped, as ordered. The lead had mended the same fault for services in Task 7e before the
  build and had not counted it for goods. The task's decision 3 now gives the buyers abroad no limit, among the
  makers a route reaches; the tests' bounds are as they were.
- **What the dealing of services did,** on the fixture (Task 7b's hand-over): the people at providers with no
  buyer fell from 64.3% to 0.7% in household services, from 62.4% to 0.0% in public provision, from 49.0% to none
  in utility and from 31.8% to 0.7% in premises. On a copy with the three country services, 10.0% of utility,
  2.4% of leisure and 11.3% of business services crosses a state line, as counted for the plan.
- **What the border did** (Task 7e's hand-over, on a copy with business services crossing): all 1,670 home buying
  workplaces have a row abroad; the 88 buying workplaces abroad are dealt over all 1,054 home providers in 1,136
  rows, the widest of them 90, and no provider is asked more than 1.001 times its room.
