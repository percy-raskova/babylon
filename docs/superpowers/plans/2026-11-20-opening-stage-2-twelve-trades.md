# The Opening, Stage 2: Twelve Trades, Pay and Bands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

Checked once against the code and the data by a second reader on 20 November 2026; its findings are in the tasks.
Read again against the code of 25 November 2026 (commit `4143657fd`) by another reader: the national compiler had not
moved, and what that reading changed is in the tasks and in the last section.

**Goal:** A national scenario of `schema_version = 8` compiles as `national-world-v13` with twelve trades, each
workplace paying the observed wage of its trade in its place, and three earning accounts in every place; the shipped
scenario of schema 7 keeps every byte it has today.

**Architecture:** The kernel learns two trades and a `TradeSet` that names which list a scenario uses: ten for schema 7
and earlier, twelve for schema 8. The cohort reader holds both mappings and both cohort tables, each pinned, and decodes
the one the policy's set names. A new reader parses stage 1's pay table, which sets pay and nothing else. The policy of
schema 8 asks for the twelve trades, observed wages, the bands and the order of paying; the opening reads the trade set
wherever it reads the ten today, takes each workplace's wage from its place's pay rows, and splits each county's earning
households into three accounts whose members are dealt that county's jobs by pay. Nothing changes on a schema 7 path; a
new test pins today's bytes first.

**Tech Stack:** Rust (`babylon-kernel`, `babylon-persistence`, `babylon-client`), gzip CSV reference tables read with
`flate2`, TOML scenario defines, the YAML contracts under `contracts/`, the two Python builders of stage 1.

**Spec:** `docs/superpowers/specs/2026-11-20-the-opening-of-the-national-economy-design.md`, rules O1, O2, O16 and O17,
section 9 calls 3, 12 and 15, section 10 stage 2. Decision record:
`ai/decisions/ADR313_the_national_economy_opens_in_balance.yaml`. Read beside it stage 1's plan, the reference tables
(its last section lists what the Rust reader checks), and the price rule's plan
(`docs/superpowers/plans/2026-11-20-price-of-a-short-market.md`).

**Build order:** Tasks 0 to 10 in order, with Task 8b after Task 8 and Task 10b after Task 10. Built before Task 0:
stage 1 (the v2 mapping, the v2 cohort table and the pay table, with their metadata), the price rule's Tasks 1 to 6c,
the tiers plan (stage 3) and the benefits plan (stage 4).
The price rule's Task 7 is not a prerequisite: carrying the market's receipt, the wants and the programs into the
register and the stored records is one later plan. So this plan's schema 8 fixture is compiled, inspected and counted
on the country bench (`tests/national_household_units.rs`), which goes around the tick (ADR324: the opening is "counted
on that bench as it is built"). It is never played through the tick. Tasks 8b and 10b are the bench's.

**From the price rule's plan.** This plan takes its Task 8's decision 1 (refusals of an order of paying), the name
`national-world-v13` (chosen by schema 8, not by the key) and `market_clearing` from the policy. Stage 5 keeps decisions
3 and 4, `the_shipped_world_clears_by_price` and the health record's cheap test; that plan's Task 9 is stage 6.

## What Schema 8 Means

At the end of this plan a schema 8 scenario has: the twelve trades of O1 and their twelve products; the version 2
mapping, cohort table and pay table as captured sources; a wage for every workplace by trade and place (O2), and for a
foreign region a designed fraction of the United States wage; three earning accounts in every domestic place (O17); an
order of paying (ADR312); the compiler `national-world-v13`. Its needs are today's six, bought as one basket, and its
prices, recipes and taxes are the scenario's own figures.

The plans of stages 3 and 4 are the engine's only. Stage 5 carries the compiler's side of both (the wants, the
national fund, the split of the two taxes and the two programs), with the builder's numbers, O5's price and refusal,
the map's pinned basis (O15) and the shipped file. It adds required schema 8 keys; since schema 8 refuses unknown keys,
this fixture takes them then. Nothing this plan builds needs reopening for it: each member's wage, the band keys,
`ActorContext.wage` and `national_wage` are present.

## Global Constraints

- Work only in `/media/user/dev-ssd/worktrees/households-homes/babylon`, branch `codex/households-and-homes`. Start
  every shell command with `cd` to it (or to its `rust/` directory). Never push. No secrets, no `.env`, no
  `babylon-data` here.
- One cargo or pytest process at a time, on the whole machine. Never pass `-j` or `--jobs`.
- A run that outlasts one command goes to the background with a log, ends with its own marker
  (`...; echo "exit=$?" >> <log>`), and is waited for on that marker. Never wait on the word `real`: this shell is zsh,
  whose `time` prints `total`. Leave no shell running when you report.
- **Scoped gate, run by every task before its last commit,** one leg at a time: from `rust/`, `mise exec -- cargo fmt
  --all -- --check`; `mise exec -- cargo clippy --workspace --all-targets --locked -- -D warnings -D
  clippy::cognitive_complexity`; the test binaries the task names with `mise run rust:test:q -- -p <crate> -E
  'binary(<name>)'`; `mise run rust:test:q -- -p <crate>` once for each crate the task changed; `mise run
  check:bsl-sentinels`. A task that touches Python adds `mise run test:q -- <its test files>`. The lead alone runs `mise
  run rust:check-no-docs`, after Task 6 and after Task 10. Every task that changes `babylon-kernel` or
  `babylon-persistence` also runs `binary(national_household_units)` of `babylon-persistence`: it holds the country
  bench's pins of the shipped world (`the_country_s_sizes`, `the_country_s_public_providers`, the seekers' rows), which
  a schema 7 path must keep.
- Commit one unit of work at a time: `git add <files>` then `PYTHONPATH=src mise exec -- git commit -q -F <message
  file>`; check that `git log --oneline -1` moved. The body ends with `Part of PER-371` and a `Co-Authored-By` line
  naming the model that wrote the commit. Never commit `uv.lock`.
- **Bytes.** A policy of schema 7 or earlier gives every byte it gives today: catalog, opening, foundation, configs.
  Task 0's pins and every existing test keep their values. If one must change, stop and tell the lead.
- No floating point. Money is `i128` millionths of a dollar (`Currency`). Quantities are `u64`. Each division names its
  rounding; every rounding here is down unless a step says otherwise.
- Every refusal is a typed error. No panic, no `unwrap` outside tests, no silent clamp.
- Functions stay under 100 lines and under a cognitive complexity of 25.
- A contract file under `contracts/` that changes gets its pinned digest updated in the same commit, if a test pins one
  (`contracts/economic_catalog_v1.yaml` has none today). A contract line that a task makes false is rewritten by that
  task, in the form "under schema 7 and earlier ...; under schema 8 ...".
- Markdown is wrapped at 120 columns, headings at 80. Refer to the player as "they".

## Review Focus

1. **A place with no observed pay** (Kalawao 15005 has no cohort group; a fallback workplace has no pay row). Expected:
   the place's average, then the state's, then the nation's; never a zero wage, never a refusal. Tests: Task 3
   `a_county_without_rows_takes_the_state_average`, Task 7 `a_fallback_workplace_pays_the_place_average`.
2. **A place whose pay rows for a trade hold no jobs** (every county's group withheld and placed at 0). Expected: the
   plain mean of the rows' own wages, not a division by zero. Test: Task 7 `place_wage_without_jobs_is_the_plain_mean`.
3. **A tiny county whose earning households are fewer than three.** Expected: empty bands make no account and no member
   row; the households that exist are counted once. Test: Task 9 `one_earning_household_makes_one_band`.
4. **Equal pay at a band's edge, and a workplace that straddles it.** Expected: ties go by site id; the straddling
   workplace has one member row in each band, in whole persons. Test: Task 10 `jobs_are_dealt_by_pay_in_whole_persons`.
5. **Two cuts under one name.** The review's "Next 40%" and the new better-paid account are different households.
   Expected: the player never sees one word for both. Test: Task 10 `the_review_and_the_accounts_use_their_own_words`.

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `rust/crates/babylon-persistence/tests/shipped_world_bytes.rs` | Today's bytes, pinned | 0 |
| `rust/crates/babylon-kernel/src/economic_identity.rs` | Two trades; `TradeSet` | 1 |
| `rust/crates/babylon-client/src/money_map/grouping.rs` | Two colors | 1 |
| `rust/crates/babylon-persistence/src/national_cohorts/{mapping,artifact,parse,tests}.rs` | Both mappings and tables | 2 |
| `rust/crates/babylon-persistence/src/national_trade_pay.rs` with `national_trade_pay/{artifact,parse,model,tests}.rs` | The pay table | 3 |
| `rust/crates/babylon-persistence/src/national_economy/policy/{admission,game}.rs` | Schema 8 | 4 |
| `rust/crates/babylon-persistence/tests/fixtures/national_twelve_trades.defines.toml` | The test scenario | 4 |
| `rust/crates/babylon-persistence/src/economic_catalog/{sources,preset,national,capture,codec,compile}.rs` | Sources, compiler | 5 |
| `rust/crates/babylon-persistence/src/national_economy/opening/{build,templates,external,financial}.rs`, `companies/capture.rs` | Trade set in the opening | 6 |
| `rust/crates/babylon-persistence/src/national_resident_allocation/allocation.rs` | Source bounds; county wage | 6, 7 |
| `rust/crates/babylon-persistence/src/national_economy/{grain/build.rs, opening/actors.rs}` | Wages in the opening | 7 |
| `rust/crates/babylon-persistence/src/national_economy/{county_review,city_pd}.rs` | The two figures | 8 |
| `rust/crates/babylon-persistence/src/national_household_allocation/{model,allocation,source}.rs` | Bands | 9 |
| `rust/crates/babylon-client/src/money_map/household.rs` | The accounts' words | 9 |
| `rust/crates/babylon-persistence/src/national_resident_allocation/households.rs` | Jobs dealt by pay | 10 |
| `rust/crates/babylon-persistence/tests/national_twelve_trades.rs` | The compiled test world | 5 to 10 |
| `contracts/economic_catalog_v1.yaml` | Compiler v13, source kind 37 | 5 |

---

### Task 0: Pin today's bytes

No test pins an absolute digest of the shipped world. The catalog digest covers only source blobs and the compiler
name (`captured_economic_catalog.rs:31-33`); a foundation digest pins the opening, and the campaign's also carries the
review's opening roster (`foundation.rs:146`). v7 to v11 and the `national-company-scale` compilers have no pin either,
though Tasks 4 and 6 touch their paths. The values are printed once, after the build order's plans have landed.

**Files:**
- Create: `rust/crates/babylon-persistence/tests/shipped_world_bytes.rs` (it may `#[path]` the existing
  `tests/fixtures/national_capture.rs` and `tests/support/company_scale.rs`)

**Interfaces:**
- Produces: the test binary `shipped_world_bytes`, which every later task runs before its last commit.

- [ ] **Step 1: Write the tests.** Each pins a literal printed by one run at the base commit:
  - `the_shipped_catalog_keeps_its_digest`: `CapturedEconomicCatalog::capture(national_catalog_input(), None)`; its
    compiler is `"national-world-v12"` and its catalog digest equals the literal.
  - `the_shipped_foundations_keep_their_digests`: the foundation digest of that catalog, and of
    `capture_national_campaign(national_catalog_input(), CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7036)))`,
    each made as `captured_economic_catalog.rs` makes it, equal their literals; so do
    `sha256(encode_county_review_config(config))` and `sha256(encode_city_pd_config(config))` of that campaign (both
    encoders are made by the `codec!` macro in `babylon-practice-contract/src/state_opponent_codec.rs`; the
    configs' own `content_digest` fields hash designed inputs only, `county_review.rs:357-385`, and are not enough).
  - `earlier_compilers_keep_their_digests`: the foundation digest of the shipped defines rewritten to
    `schema_version = 6` with its `[city_pd]` and `[county_review]` sections removed (compiler `national-world-v11`),
    and of the experiment input of `tests/support/company_scale.rs` (a `national-company-scale` compiler).
  - `the_shipped_opening_keeps_its_counts`: the opening's sites, household rows, staffing members, employment terms,
    ownership claims, recipes (9) and commodities (10) equal their literals. A drift then names the part that moved.
- [ ] **Step 2: Run** `-p babylon-persistence -E 'binary(shipped_world_bytes)'` twice. Expected: PASS, same values.
- [ ] **Step 3: Gate and commit** `test(persistence): pin the bytes of the shipped national world`.

### Task 1: Twelve trades in the kernel

**Files:**
- Modify: `rust/crates/babylon-kernel/src/economic_identity.rs`; `rust/crates/babylon-client/src/money_map/grouping.rs`
  (`industry_color`, exhaustive today at 104-118);
  `rust/crates/babylon-persistence/src/national_economy/policy/admission.rs` (`recipes` at 789, its guard at 798)
- Test: the kernel's `economic_identity.rs` tests; `grouping.rs` tests; `tests/national_game_policy.rs`

**Interfaces:**
- Produces:

```rust
// EconomicFunction gains, in alphabetical declaration order:
//   ConsumerGoods       after ConstructionHousing   (label "Consumer goods", key "consumer_goods")
//   LeisureHospitality  after HouseholdServices     (label "Leisure and hospitality", key "leisure_hospitality")
/// Which list of trades a scenario uses. Ten for schema 7 and earlier, twelve for schema 8.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum TradeSet { Ten, Twelve }
impl TradeSet {
    /// In `Ord` order. `Ten` is exactly today's `opening::FUNCTIONS`.
    #[must_use] pub const fn functions(self) -> &'static [EconomicFunction];
    #[must_use] pub fn contains(self, function: EconomicFunction) -> bool;
    /// `from_source_key`, then `None` for a trade outside the set.
    #[must_use] pub fn from_source_key(self, key: &str) -> Option<EconomicFunction>;
}
```

**Decisions:**
1. Why no schema 7 byte moves (checked twice on 20 November). `EconomicFunction` has no serde or strum derive, no
   `as u8`, no `ALL` constant and no wildcard match. A trade enters bytes only by its source key text (site ids,
   `identity.rs:76`, `:190`, `external.rs:78`; labels, `actors.rs:83`; journal keys, `labor_facts.rs:245`). The new
   variants sit between existing ones, so the derived `Ord` keeps the ten's order. Position is used only by
   `templates.rs:19`, `external.rs:75` and `:181` and the companies loop (`companies/capture.rs:71`); Task 6 moves
   them onto the set, which is `Ten` for schema 7.
2. `from_source_key` knows both new keys. Every reader of a policy uses `TradeSet::from_source_key` instead, so a schema
   7 file naming a new trade is refused as today. Readers of stored keys (journal, client) keep `from_source_key`.
3. Client colors: consumer goods `Color::srgb_u8(214, 112, 92)`, leisure and hospitality `Color::srgb_u8(236, 192, 98)`.
4. The doc comments go stale and are corrected: the enum's "`NationalQcewFunctionMappingV1`" names both mappings;
   capital goods loses "mixed consumer and capital uses" under twelve trades; household services loses "recreation".

- [ ] **Step 1: Write the failing tests.**
  - `twelve_trades_sort_where_the_builders_sort_them`: `TradeSet::Twelve.functions()` has 12 rows whose `source_key()`s
    are in strict lexical order and equal `["business_services", "capital_goods", "construction_housing",
    "consumer_goods", "distribution_transport", "energy_utilities", "extraction", "food", "household_services",
    "leisure_hospitality", "manufacturing", "public_provisioning"]`; the slice is strictly increasing in `Ord`.
  - `ten_trades_keep_their_order`: `TradeSet::Ten.functions()` equals today's ten, in today's order, and is strictly
    increasing in `Ord`; `Ten.contains(ConsumerGoods)` is false; `Ten.from_source_key("consumer_goods")` is `None`;
    `Twelve.from_source_key("consumer_goods")` is `Some(ConsumerGoods)`.
  - `new_trades_have_their_labels`: the two labels and keys in the comment of the Interfaces block.
  - `industry_colors_are_distinct_for_twelve_trades` (client): the twelve keys give twelve distinct colors, none `GRAY`.
  - `a_schema_7_recipe_for_a_new_trade_is_refused` (`national_game_policy.rs`): the shipped defines with
    `[process.capital_goods]` renamed `[process.consumer_goods]` give `Err(Recipe("consumer_goods"))`. This one passes
    at HEAD (the key is unknown there); it is a pin that must still pass after Step 3, when the key becomes known.
- [ ] **Step 2: Run them and see them fail.** `mise run rust:test:q -- -p babylon-kernel`. Expected: does not compile.
- [ ] **Step 3: Implement** the variants, `TradeSet`, the colors, the doc comments, and the guard in `recipes` (pass
  `TradeSet::Ten` until Task 4 gives the policy its set).
- [ ] **Step 4: Run** the kernel, `-p babylon-client`, `binary(national_game_policy)` and `binary(shipped_world_bytes)`.
  Expected: PASS, no pinned value changed.
- [ ] **Step 5: Gate and commit** `feat(kernel): name consumer goods and leisure, and the two sets of trades`.

### Task 2: The cohort reader holds both tables

**Files:**
- Modify: `rust/crates/babylon-persistence/src/national_cohorts/{mapping.rs, artifact.rs, parse.rs, tests.rs}`,
  `src/national_cohorts.rs` (re-exports); `tools/make_national_cohort_reference_v2.py` (`native_readers` becomes
  `["babylon-persistence::national_cohorts"]`) and its regenerated `national_cohort_reference_v2_2024.metadata.json`
  (the CSV must come out byte for byte the same)
- Test: `national_cohorts/tests.rs`; `tests/national_cohorts.rs`;
  `tests/unit/tools/test_national_cohort_reference_v2.py`

**Interfaces:**
- Consumes: `TradeSet`.
- Produces:

```rust
impl NationalCohortReference {   // decode_pinned and decode_captured keep their meaning: version 1
    /// The table and mapping that `set` names, each checked against its own pins.
    pub fn decode_captured_for(bytes: &[u8], mapping_bytes: &[u8], counties: &NationalCountyReference,
        set: TradeSet) -> Result<Self, NationalCohortReferenceError>;
    #[must_use] pub const fn trades(&self) -> TradeSet;
    #[must_use] pub const fn artifact_sha256(&self) -> [u8; 32];          // exists today; the decoded table's pin
    #[must_use] pub const fn function_mapping_sha256(&self) -> [u8; 32];  // exists today; the mapping's pin
}
/// The embedded twelve-trade table, decoded once.
pub fn national_cohort_reference_v2() -> Result<&'static NationalCohortReference, NationalCohortReferenceError>;
pub const LEAF_BASIS_SHA256: [u8; 32];      // unchanged: version 1's leaf parquet
pub const JOBS_BASIS_V2_SHA256: [u8; 32];   // version 2's parquet: leaves, parents, states and nation
pub(crate) const ARTIFACT_V2: &[u8];        // include_bytes! of national_cohort_reference_v2_2024.csv.gz
pub(crate) const MAPPING_V2: &[u8];         // include_bytes! of contracts/national_qcew_function_mapping_v2.json
```

**Decisions:**
1. One pin set per `TradeSet`: contract name, functions, member codes (with 99), table digest, groups, members and
   admitted. `Ten`: `NationalQcewFunctionMappingV1`, 10, 50, today's pins. `Twelve`: `NationalQcewFunctionMappingV2`,
   12, 64, stage 1's metadata (members 151,199, admitted 65,065). Both keep 16,384 bytes of mapping and 2,097,152 and
   8,388,608 bytes of table. The mapping reads ids with `set.from_source_key`, so version 1 cannot admit a new trade.
2. The parser is shared; only the pins differ. Group order is the derived `Ord` of `CohortKey`, which Task 1 keeps equal
   to the builder's lexical order for both sets. The binary carries both tables (1,756,290 bytes for version 1, about
   1,848,908 for version 2), both mappings, and from Task 3 the pay table.

- [ ] **Step 1: Write the failing tests.**
  - Keep `economic_function_display_labels_match_pinned_mapping` (tests.rs:138-160) for `Ten` against version 1, as it
    is; add `twelve_trade_labels_match_the_v2_mapping`: 12 functions, each id known to `TradeSet::Twelve`, each
    `label()` and `source_key()` equal to the v2 contract's label and id.
  - `the_v2_table_decodes_with_its_own_pins` (`tests/national_cohorts.rs`): `trades() == Twelve`; groups equal the v2
    metadata's coverage, admitted 65,065, members 151,199; every admitted group has a function; the group
    `(26163, ConsumerGoods, Private)` has `53_000 <= jobs_known < 54_000`; `artifact_sha256()` is the v2 metadata's.
  - `each_table_needs_its_own_mapping`: the v2 table with the v1 mapping, the v1 table with the v2 mapping, and the v2
    table decoded with `TradeSet::Ten` each give `Err(FunctionMapping)` or `Err(ArtifactDigest)`, never `Ok`.
  - The existing tests of the ten (`tests/national_cohorts.rs`: 59,058 groups, 57,238 admitted, 144,881 members, jobs
    140,452,919; `tests/captured_source_dependencies.rs`) stay unchanged and pass.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.** Then edit the builder's `native_readers`, rerun it (`UV_PROJECT_ENVIRONMENT=.venv mise exec
  -- uv run --frozen python tools/make_national_cohort_reference_v2.py`), and `cmp` the CSV with the committed one: it
  must not change.
- [ ] **Step 4: Run** `-p babylon-persistence -E 'binary(national_cohorts)'`, `binary(captured_source_dependencies)`,
  `binary(shipped_world_bytes)`, the crate, and the Python test file.
- [ ] **Step 5: Gate and commit** `feat(persistence): read the twelve-trade cohort table beside the ten`.

### Task 3: The pay table reader (rule O2)

**Files:**
- Create: `rust/crates/babylon-persistence/src/national_trade_pay.rs` and `national_trade_pay/{artifact.rs, parse.rs,
  model.rs, tests.rs}`; `rust/crates/babylon-persistence/tests/national_trade_pay.rs`
- Modify: `src/lib.rs` (module); `tools/make_national_trade_pay.py` (`native_readers`) and its regenerated metadata

**Interfaces:**
- Consumes: `NationalCohortReference` of `TradeSet::Twelve`; `NationalCountyReference`.
- Produces:

```rust
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum JobsRule { Published, Placed, Partial }
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum WageRule { County, State, Nation, NationAllOwnerships }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct TradePayRow {
    pub key: CohortKey,              // function is always Some
    pub jobs: u64, pub payroll_usd: u64, pub jobs_rule: JobsRule,
    pub wage_rule: WageRule, pub wage_jobs: u64, pub wage_payroll_usd: u64,
}
impl TradePayRow {
    /// floor(wage_payroll_usd x 1_000_000 / (wage_jobs x 2_080)), in millionths per hour.
    pub fn hourly_wage(&self) -> Result<Currency, NationalTradePayError>;
}
pub struct NationalTradePayReference { /* rows sorted by key; averages computed once */ }
impl NationalTradePayReference {
    pub fn decode_captured(bytes: &[u8], cohorts: &NationalCohortReference, counties: &NationalCountyReference)
        -> Result<Self, NationalTradePayError>;
    #[must_use] pub fn row(&self, key: CohortKey) -> Option<&TradePayRow>;
    /// All of a county's rows, all trades and ownerships: sum(payroll_usd) x 1_000_000 / (sum(jobs) x 2_080);
    /// a county whose rows hold no jobs takes its state's figure over all its counties, then the nation's.
    #[must_use] pub fn county_average(&self, county: CountyGeoid) -> Currency;
    /// The same sum over every row of the trade, all counties and ownerships.
    #[must_use] pub fn national_wage(&self, function: EconomicFunction) -> Currency;
    #[must_use] pub const fn artifact_sha256(&self) -> [u8; 32];
}
pub fn national_trade_pay_reference() -> Result<&'static NationalTradePayReference, NationalTradePayError>;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum NationalTradePayError { Bound, ArtifactDigest, Compression, Header, CsvShape, Function, Ownership,
    CountyIdentity, UnknownCounty, NumericValue, Rule, Wage, Order, Coverage }
```

**Decisions:**
1. **The lead's ruling A: where residents work stays as today.** The placing of withheld jobs in stage 1's table sets
   pay and nothing else; a source workplace's weight stays the cohort table's (`Peers::weight`) under both sets. The
   table's `jobs` and `payroll_usd` serve only wages and averages (Task 7), `wage_jobs` and `wage_payroll_usd` only a
   row's own wage. (The lead amends O2, call 12 and stage 1's plan to say so.)
2. The format is stage 1's Task 4: its nine-column header, ASCII, `\n` ends, canonical integers as in the cohort reader,
   the rule words `published`, `placed`, `partial`, `county`, `state`, `nation`, `nation_all_ownerships`; 2,097,152
   compressed and 8,388,608 decoded bytes; stage 1's digest and 65,065 rows, strictly sorted by `CohortKey` and equal to
   the v2 table's admitted keys (`Coverage`). The table already resolves a withheld wage; the reader never re-derives
   it.
3. `wage_jobs > 0`, `wage_payroll_usd > 0` and an hourly wage above 0, else `Wage`: stage 1 guarantees the first, and a
   placed group could get payroll 0 by rounding. A `county` wage rule needs `jobs_rule != Partial` and
   `(wage_jobs, wage_payroll_usd) == (jobs, payroll_usd)` (`Rule`). The catalog captures the bytes (Task 5).

- [ ] **Step 1: Write the failing tests** on hand-written rows (`tests.rs`), county 26163 unless named:
  - `a_county_row_pays_its_own_wage`: consumer goods own 5, 60,000 jobs, 6,000,000,000 USD, `published`, `county`:
    `hourly_wage()` is 48,076,923. Household services own 5, 100,000 jobs, 5,200,000,000 USD: 25,000,000.
  - `a_withheld_row_takes_the_state_pair`: leisure own 2, 0 jobs, 0 USD, `partial`, `state`, pair (48,138,
    4,997,065,672): `hourly_wage()` is 49,907,254.
  - `the_county_average_counts_its_own_jobs`: the three rows above give `county_average(26163)` 33,653,846 (the withheld
    row adds no jobs).
  - `a_county_without_rows_takes_the_state_average`: a fixture county of state 26 with no rows gets 33,653,846; a county
    of a state with no rows gets the nation's figure over all rows.
  - `national_wage_sums_every_place`: with only the first row of consumer goods, `national_wage(ConsumerGoods)` is
    48,076,923.
  - `bad_rows_are_refused`: a wrong header (`Header`); eight fields (`CsvShape`); `0042` (`NumericValue`); rule `mixed`
    (`Rule`); `wage_jobs` 0 (`Wage`); `wage_payroll_usd` 0 (`Wage`); two rows out of order (`Order`); a `county` row
    whose pair differs (`Rule`).
  - `the_committed_pay_table` (`tests/national_trade_pay.rs`, real tables): decodes against the v2 cohorts; 65,065
    rows, one for every admitted key; `row((26163, ConsumerGoods, Private))` has `jobs >= 53_000` and
    `WageRule::County`; every `county_average` of the 3,144 counties is above 0; a table with one row removed is
    `Coverage`.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.** Edit the builder's `native_readers` to `["babylon-persistence::national_trade_pay"]`, rerun
  it, check the CSV is unchanged.
- [ ] **Step 4: Run** the module's tests, `binary(national_trade_pay)`, the crate, and the pay table's Python test.
- [ ] **Step 5: Gate and commit** `feat(persistence): read the pay of each trade by place`.

### Task 4: The policy of schema 8 and the test scenario

**Files:**
- Modify: `rust/crates/babylon-persistence/src/national_economy/policy/{admission.rs, game.rs}`
- Create: `rust/crates/babylon-persistence/tests/fixtures/national_twelve_trades.defines.toml`
- Test: `rust/crates/babylon-persistence/tests/national_game_policy.rs`

**Interfaces:**
- Consumes: `TradeSet`.
- Produces (on `NationalGamePolicy`, `game.rs`):

```rust
pub trades: TradeSet,                 // Ten for schema 2..=7, Twelve for 8
pub wages: GameWages,                 // replaces `default_wage: Currency`
pub markets: GameMarketPolicy,        // gains `paying_order: Option<Vec<String>>`, Some only under schema 8
pub households: GameHouseholdPolicy,  // gains `next_forty_households_bps: Option<u16>`, Some only under schema 8
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameWages { Single(Currency), Observed }
impl GameWages { #[must_use] pub const fn single(self) -> Option<Currency>; }
// GameProfile: `wage_per_hour: Currency` becomes `wage: GameProfileWage`;
//              `function_weights_bps: [u16; 10]` becomes `Vec<u16>` of `trades.functions().len()` rows.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameProfileWage { PerHour(Currency), FractionOfUnitedStates { bps: u16 } }
```

**Decisions:**
1. `validate_globals` adds `(8, true, true, true, true, true)`. Schema 8: `default_wage_micros_per_hour` is refused (it
   gives `GameWages::Observed`; schema 7 and earlier require it and give `Single`); twelve commodities (today's ten,
   `consumer_goods` storable and `leisure` a service); eleven recipes, one per trade of the set but distribution; six
   household needs, as today; every counterpart and the dependency give `wage_fraction_bps` in `1..=10_000` in place of
   `wage_micros_per_hour`, and twelve function weights in `Ord` order of the twelve trades; `[households]
   next_forty_households_bps` in `1..=10_000` with `private_owner_households_bps + next_forty_households_bps < 10_000`
   (the bottom half exists); `[markets] paying_order`. Each of these keys under schema 7 or earlier is refused
   (`Shape`), and each missing under schema 8 is refused (`Shape`).
2. `GameMarketPolicy` derives `Copy` today (`game.rs:306`); its new `Vec` field drops `Copy`. Its readers that copy it
   take it by reference or clone it; none of them is on a hot path. `GameProfile` is already `Clone` only.
3. The order of paying (the price plan's Task 8, decision 1): refused (`Profile("paying order")`) for an unknown
   product, a product twice, a storable household need after a service or left out, `utility` after a local service, a
   product with no price. Consumer goods and leisure join it; their place among the tiers is stage 5's to compile.
4. The test scenario copies the shipped `defines.toml`; its first lines say it is a test fixture, not a playable
   scenario. Changes: `schema_version = 8`; no default wage; `next_forty_households_bps = 4000`; `paying_order =
   ["food", "materials", "consumer_goods", "utility", "housing", "household_services", "leisure", "business_services",
   "resources"]`; `[commodity.consumer_goods]` ("Consumer goods", "consumer goods bundle", storable, general, 5,000 g,
   240,000,000 / 60,000,000 / 960,000,000 / 6,000,000); `[commodity.leisure]` ("Leisure and hospitality", "person-period
   leisure", service, 300,000,000 / 75,000,000 / 1,200,000,000 / 7,500,000); `[process.consumer_goods]` (8 per batch, 16
   hours, materials 2, utility 1, business services 1); `[process.leisure_hospitality]` (output `leisure`, 16 per batch,
   160 hours, food 2, materials 1, utility 1); `wage_fraction_bps` = shipped wage over $24, rounded down (Canada 8333,
   Mexico 2916, China 4166, Russia 4583, India 2083, Japan 9166, and so on); twelve weights in `Ord` order, consumer
   goods taking half of capital goods' weight and leisure a quarter of household services', each rounded down to 50.
   These are a fixture's designed figures; the rebuilt numbers are stage 5's.

- [ ] **Step 1: Write the failing tests** in `national_game_policy.rs`:
  - `the_twelve_trade_fixture_parses`: `trades == Twelve`; 12 commodities; 11 recipes; 6 needs; `wages == Observed`;
    `next_forty_households_bps == Some(4000)`; `paying_order` has 9 rows in the fixture's order; Canada's wage is
    `FractionOfUnitedStates { bps: 8333 }` and its weights sum to 10,000 over 12 rows.
  - `the_shipped_policy_keeps_its_shape`: shipped `trades == Ten`, `wages == Single(24_000_000)`, `paying_order` and
    `next_forty_households_bps` are `None`, 10 commodities, 9 recipes (the existing pins stay as they are).
  - `schema_8_keys_are_refused_under_schema_7`: the shipped file plus `next_forty_households_bps = 4000`, and plus a
    `paying_order`, each give `Err(Shape)`.
  - `schema_8_needs_all_its_keys`: the fixture without `paying_order`, without `next_forty_households_bps`, with a
    `default_wage_micros_per_hour`, with ten weights for Canada, each give `Err(Shape)` or `Err(Profile(..))`.
  - `an_order_of_paying_is_refused_when_wrong`: the five refusals of decision 3.
  - `bands_need_a_bottom_half`: `private_owner_households_bps = 1000` with `next_forty_households_bps = 9000` gives
    `Err(Profile(..))`.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.** Readers of `default_wage` and `wage_per_hour` read `wages.single()` and `PerHour`, and
  refuse the other case with their own typed error until Tasks 7 and 8 give them the observed figure.
- [ ] **Step 4: Run** `binary(national_game_policy)`, `binary(national_company_capture)`, `binary(shipped_world_bytes)`,
  the crate.
- [ ] **Step 5: Gate and commit** `feat(economy): admit a national policy of twelve trades (schema 8)`.

### Task 5: The catalog captures the twelve-trade sources and names v13

**Files:**
- Modify: `rust/crates/babylon-persistence/src/economic_catalog/sources.rs` (`NationalTradePay = 37`, with its
  `TryFrom<u8>` arm; the kinds stop at 36 today); `preset.rs` (the input by policy; `NationalGraph::from_compiler`
  gains v13); `national.rs` (required sources by set; decode by set; the pay reference kept on `NationalSources`);
  `capture.rs` (`compiler_for`); `codec.rs` (`frames_county_review`); `model.rs` and `compile.rs` (`market_clearing`);
  `contracts/economic_catalog_v1.yaml`
- Test: `rust/crates/babylon-persistence/tests/national_twelve_trades.rs` (new)

**Interfaces:**
- Consumes: Tasks 2 to 4.
- Produces:

```rust
/// The national input for these defines: the version 1 or 2 cohort table and mapping as the policy's trade set
/// names them, and the pay table for the twelve. `national_catalog_input()` is this with the shipped defines.
/// # Errors
/// `Source(NationalGamePolicy)` for defines that do not parse.
pub fn national_catalog_input_for(defines: &[u8]) -> Result<EconomicCatalogInput, EconomicCatalogError>;
// NationalSources gains `pay: Option<NationalTradePayReference>` (Some exactly under TradeSet::Twelve),
// passed to `build_national_opening` beside `cohorts`.
// EconomicOpening gains `market_clearing: Option<MarketClearingPolicy>`, never encoded; the national opening sets it.
```

**Decisions:**
1. The source kinds stay `NationalCohorts = 6` and `CohortFunctionMapping = 11`; they hold the table and mapping of the
   policy's set. `NationalTradePay = 37` is required under `Twelve` and unexpected under `Ten`. The shipped input's
   rows, their order and their bytes are today's; the twelve-trade input appends kind 37 last.
2. `compiler_for`: a policy with `trades == Twelve` (it always has companies, `FirstApplicable` and the City PD) is
   `"national-world-v13"`, decided before the v12 arm; every other arm is unchanged. `frames_county_review` is true for
   v12 and v13. `NationalGraph::from_compiler` lists v13 as `Companies`.
3. `compile.rs` has no policy in hand (`empty_catalog`, line 74), so the national opening sets
   `EconomicOpening.market_clearing` from the policy and `compile.rs` copies it where `empty_catalog` writes `None`.
   The engine's `MarketClearingPolicy` has three more fields than `paying_order` since the six rules were built
   (`babylon-material-circuit/src/clearing/rule.rs`). The policy of schema 8 leaves them empty and false: no wants
   (stage 5), no plans from spare money, no adjustment rule. The country bench turns rules on itself (Task 8b).
4. The contract says: kind 37 is the pay table, captured only under schema 8; the compilers list gains v13; the county
   review footer is written "under national-world-v12 and v13".

- [ ] **Step 1: Write the failing tests** (`national_twelve_trades.rs`; the fixture is
  `include_bytes!("fixtures/national_twelve_trades.defines.toml")`):
  - `the_shipped_input_keeps_its_sources`: `national_catalog_input_for(shipped)` equals `national_catalog_input()` row
    for row (kind, bytes), with no kind 37.
  - `the_fixture_input_carries_the_v2_sources`: kinds 6 and 11 hold the v2 table and mapping (their digests equal the
    readers' pins); kind 37 holds the pay table; 17 rows.
  - `the_fixture_compiles_as_v13`: `compiler_for` (a crate-visible test in `capture.rs`) names `national-world-v13`;
    the shipped input still names v12.
  - `a_twelve_trade_policy_with_ten_trade_tables_is_refused`: the fixture's defines with the v1 table and mapping give
    `Err(Source(NationalCohorts))`; with no kind 37, `Err(Source(NationalTradePay))`.
  - `the_catalog_clears_by_price_under_schema_8`: a crate test gives nine `paying_order` rows in the fixture's order;
    the shipped policy gives `None`.
- [ ] **Step 2: Run them and see them fail.** (A full capture of the fixture fails until Task 7; these do not need it.)
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `binary(national_twelve_trades)`, `binary(captured_economic_catalog)`,
  `binary(shipped_world_bytes)`, the crate.
- [ ] **Step 5: Gate and commit** `feat(economy): capture the twelve-trade sources and compile them as v13`.

### Task 6: The opening runs on its trade set

**Files:**
- Modify: `rust/crates/babylon-persistence/src/national_economy/opening/build.rs` (remove `FUNCTIONS`);
  `opening/templates.rs` (`recipe_id`); `opening/external.rs` (`partition` over a slice); `companies/capture.rs:71`;
  `opening/financial.rs` (`foreign_claim` at 285-298); `national_resident_allocation/allocation.rs:242` (source bounds)
- Test: `national_twelve_trades.rs`; crate tests of `templates.rs` and `financial.rs`; `tests/resident_allocation.rs`

**Interfaces:**
- Consumes: `policy.trades`.
- Produces:

```rust
pub(super) fn recipe_id(trades: TradeSet, function: EconomicFunction) -> Result<RecipeTemplateId>; // position + 1
fn partition(persons: u64, weights: &[u16]) -> Result<Vec<u64>>;   // same rule, any length
/// The trade whose private plants in Wayne carry Japan's claim, and whose plants in Canada carry Wayne's.
pub(super) const fn claimed_plants(trades: TradeSet) -> EconomicFunction; // Ten: CapitalGoods; Twelve: ConsumerGoods
// national_resident_allocation:
pub(crate) const MAX_SOURCE_WORKPLACES: usize = 131_072;
pub(crate) const MAX_SOURCE_STAFFING_MEMBERS: usize = 262_144;
```

**Decisions:**
1. Every use of `FUNCTIONS` reads `policy.trades.functions()`; for `Ten` the recipe ids and foreign weights are today's.
   The two designed claims (O1) follow `claimed_plants(trades)`; under `Twelve` no capital goods site carries one.
2. **The source bound.** `allocate_home_county` checks its county-level list, before places are coarsened, against
   `MAX_MATERIAL_CIRCUIT_ROWS` (65,536) and `MAX_STAFFING_MEMBERS` (131,072). Today it has 60,454 workplaces
   (`tests/resident_allocation.rs:35`): 57,238 admitted groups, a household enterprise in 3,143 counties and 73
   fallbacks. The v2 table has 65,065 admitted groups, so about 68,281 workplaces, past the bound, and the compile is
   refused with `Bounds` (the second reader reproduced each figure). That list is never live: live rows are the folded
   sites (7,283 domestic and 180 abroad today, by the second reader; 216 abroad under twelve trades), still checked
   against the engine's bounds. So the source list takes its own bounds for both sets (60,454 passes either way).

- [ ] **Step 1: Write the failing tests.**
  - `recipe_ids_follow_the_set` (templates): `recipe_id(Ten, DistributionTransport)` is 4 and `(Ten,
    PublicProvisioning)` 10; `recipe_id(Twelve, ConsumerGoods)` is 4, `(Twelve, DistributionTransport)` 5, `(Twelve,
    PublicProvisioning)` 12; `recipe_id(Ten, ConsumerGoods)` is `Err(Policy)`.
  - `partition_keeps_its_rule`: `partition(1000, &[1200, 300, 1000, 1200, 800, 1800, 800, 2000, 600, 300])` equals
    today's `[u64; 10]` result for the same input, and a twelve-row call sums to its persons.
  - `the_car_plants_carry_the_claims` (financial): `claimed_plants(Ten) == CapitalGoods`, `(Twelve) == ConsumerGoods`.
  - `the_twelve_trade_source_allocation_fits_its_bounds` (`national_twelve_trades.rs`): `allocate_home_county` with the
    v2 cohorts and the fixture policy succeeds; its workplaces and members are under the two new bounds; pin both counts
    as the literals the first run prints (planning expects about 68,281 workplaces). `resident_allocation.rs`'s 60,454
    stays.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the crate's opening tests, `binary(national_twelve_trades)`, `binary(resident_allocation)`,
  `binary(national_opening)`, `binary(shipped_world_bytes)`, the crate.
- [ ] **Step 5: Gate and commit** `feat(economy): build the opening on the scenario's own set of trades`.

### Task 7: Each workplace pays the wage of its trade and place

**Files:**
- Modify: `rust/crates/babylon-persistence/src/national_economy/grain/build.rs` (`OpeningProductiveEndowment::source`
  and `accumulate` at 735-850; the coarsening at 974 records each destination's wage); `opening/actors.rs` (109 and
  144); `opening/external.rs` (91); `opening/build.rs` (`Builder` reads the wage map);
  `national_resident_allocation/allocation.rs` (the county-level wage on each workplace)
- Test: `national_twelve_trades.rs`; crate tests in `grain/tests.rs`

**Interfaces:**
- Consumes: `NationalTradePayReference` (`row`, `county_average`, `national_wage`), `GameWages`, `GameProfileWage`.
- Produces:

```rust
/// A county-level workplace's own wage: its pay row's wage for a source workplace; the county's average for a
/// fallback or a household enterprise. Used to rank that county's jobs (Task 10), never as a place's wage.
pub(crate) fn workplace_wage(pay: &NationalTradePayReference, target: &ResidentWorkplaceTarget)
    -> Result<Currency, AllocationError>;
// PendingWorkplace, PendingAssignedWorkplace and AssignedResidentWorkplace gain `county_wage: Option<Currency>`:
// Some under GameWages::Observed, set in allocate_home_county from `workplace_wage`; never hashed.
/// A place's wage for one trade and ownership, over the place's pay rows for them, each (jobs, payroll_usd, own wage):
/// floor(sum(payroll_usd) x 1_000_000 / (sum(jobs) x 2_080)); when the rows hold no jobs, floor(sum(own wage) / rows).
pub(crate) fn place_wage(rows: &[(u64, u64, Currency)]) -> Result<Currency, NationalGrainError>;
// NationalOpeningRoster gains `workplace_wages: BTreeMap<SiteId, Currency>`: empty under `GameWages::Single`,
// one entry per domestic site under `Observed`.
```

**Decisions:**
1. Under `Single(w)` every figure and every line of arithmetic is today's. The path below runs only under `Observed`.
2. **The lead's ruling B: the hub wage is the design's.** A place that stands for several counties pays, for each of
   its workplaces, the summed payroll over the summed jobs of the place's pay rows for that trade and ownership
   (`place_wage` over the counties of the site's source incidences), not a wage weighted by resident workers: a job
   centre at $40 with 100,000 jobs and 50,000 resident workers and a suburb at $30 with 20,000 jobs and 70,000 give
   $38.33 (38,333,333), not $34.17. Wayne and Cook, kept apart, pay their row's own wage. A fallback or
   household-enterprise site pays the place's average over all its rows.
3. **Cash after folding.** Cash is linear in employee persons (`OpeningProductiveEndowment::source`, `accumulate`), so
   under `Observed` `source` keeps employee persons and inputs' cash apart, and after folding the site's cash is
   `working_capital_periods x (employee persons x work_hours_per_person x place wage + inputs cost)`: payroll covered.
4. Each employee member's `LaborCompensation::Wage` is its site's `ActorContext.wage` (`actors.rs:144`); every payroll,
   cash floor and grant that reads it follows (`financial.rs:343` and `:386`, `markets.rs:759`, `equipment.rs:308`). The
   county-level wage lives only on the allocation's rows (`county_wage`), to rank jobs (Task 10).
5. A foreign region or dependency pays, in trade `f`, `floor(national_wage(f) x bps / 10_000)`; a result of 0 is
   `NationalOpeningError::Policy`.
6. **Prices (the seam with stage 5).** No opening price reads the wage but the retail handling charge
   (`markets.rs:457`), which now follows each retailer's own wage. Other prices stay the scenario's figures, so a seller
   whose pay exceeds what its price covers opens under its cost, as one can today. O5's price that follows its own wage,
   and its refusal, are stage 5's.

- [ ] **Step 1: Write the failing tests.**
  - `place_wage_sums_pay_over_jobs`: `[(100_000, 8_320_000_000, 40_000_000), (20_000, 1_248_000_000, 30_000_000)]`
    gives 38,333,333.
  - `place_wage_without_jobs_is_the_plain_mean`: `[(0, 0, 48_076_923), (0, 0, 25_000_000)]` gives 36,538,461; an empty
    slice is `Err(Arithmetic)`.
  - `cash_after_folding_covers_the_place_payroll` (grain): two county rows of 3 and 1 employee persons and inputs cash
    folded at a place wage give cash `periods x ((3 + 1) x 160 x wage + inputs)` exactly.
  - In `national_twelve_trades.rs`, on the captured fixture (`CapturedEconomicCatalog::capture(input, None)`):
    - `twelve_trades_open`: every trade of `Twelve` has a domestic site; consumer goods and leisure each have a site in
      Wayne; the catalog has 11 recipes and 12 commodities; its compiler is v13.
    - `wayne_car_plants_pay_their_observed_wage`: the site `site-26163-consumer-goods-5` exists; every employment term
      there is `Wage(r)` with `r == row((26163, ConsumerGoods, Private)).hourly_wage()`.
    - `wayne_car_plants_carry_the_two_claims`: that site has ownership claims to Japan's pooled account summing to the
      fixture's `cross_border_ownership_bps` (2,000) and to Wayne's owners summing to 8,000; Canada's consumer goods
      site has claims to Wayne's owners summing to 2,000; Wayne's and Canada's capital goods sites carry no foreign
      claim.
    - `a_place_pays_its_counties_pay_over_jobs`: for one coarsened site with two or more source counties, its wage
      equals `place_wage` over those counties' pay rows (recomputed in the test from the witness and the pay reference).
    - `a_fallback_workplace_pays_the_place_average`: a `resident-employer-*` site's wage is its place's average.
    - `foreign_plants_pay_a_fraction`: Canada's consumer goods wage is `floor(national_wage(ConsumerGoods) x 8333 /
      10_000)`.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `binary(national_twelve_trades)`, `binary(captured_economic_catalog)`, `binary(national_opening)`,
  `binary(shipped_world_bytes)`, the crate.
- [ ] **Step 5: Gate and commit** `feat(economy): pay each trade the observed wage of its place`.

### Task 8: The County Review's going wage and the City PD's payroll

**Files:**
- Modify: `rust/crates/babylon-persistence/src/national_economy/county_review.rs` (370 and 508);
  `national_economy/city_pd.rs` (`Books::of` at 230; `payroll_site` at 284)
- Test: `national_twelve_trades.rs`; `tests/national_county_review.rs` and `tests/national_city_pd_live.rs` unchanged

**Interfaces:**
- Consumes: `county_average`, the opening's employment terms.
- Produces: `fn going_wage(policy: &NationalGamePolicy, pay: Option<&NationalTradePayReference>) -> Result<i128>` in
  `county_review.rs` (it reads `policy.county_review.county`); `Books::of(wage: i128, policy, terms)`.

**Decisions:**
1. The going wage is only the session's floor today (`practice-contract/county_review/session.rs:467`: session hours
   times it is what a household's time is worth). It does not rank: the opening's roster ranks by people at work
   (`roster.rs:349`) and play by the wage tax each group paid. Under `Single(w)` it is `w`; under `Observed` it is
   `county_average` of the review's county, read from `policy.county_review.county`, never a literal. It is hashed into
   the review's content identity (`county_review.rs:370`). The floor follows: two hours (`session_hours = 2`) at Wayne's
   average pay, about $74 (at about $37.01, by the second reader), where the Director's ruling named $48.
2. **A call (ruling G): the City PD pays its payroll site's wage, one site, one rate.** The register refuses a visit
   whose rate differs from the config's (`babylon-tick/src/material_world/city_pd.rs:523`). The site is the one the code
   chooses today (Wayne's local-government public provisioning with most employees); its wage is read from its
   employees' terms (all equal by Task 7), then the books. O2's "Wayne's public workplaces" is read as that site.

- [ ] **Step 1: Write the failing tests** on `capture_national_campaign(national_catalog_input_for(fixture)?,
  campaign)`:
  - `the_going_wage_is_wayne_average_pay`: `county_review_config().going_wage_micros == county_average(26163)`.
  - `the_city_pd_pays_its_payroll_site`: the City PD config's `hourly_wage_micros` equals its payroll site's employment
    rate, and `payroll_micros == positions x 160 x that rate`.
  - The shipped campaign keeps 24,000,000 for both (`national_game_policy.rs:402-407` and Task 0's digests).
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `binary(national_twelve_trades)`, `binary(national_county_review)`,
  `binary(captured_national_organizer)`, `binary(shipped_world_bytes)`, the crate, `-p babylon-practice-contract`.
- [ ] **Step 5: Gate and commit** `feat(economy): give the county review and the City PD their own pay`.

### Task 8b: The country bench opens the twelve trades

Commit `test(persistence): the country bench opens the twelve-trade scenario`. Test code only.

**Why here.** After Task 8 the fixture captures the bench's own way (`capture_national_campaign`): before it the City
PD and the County Review refuse a policy with no default wage.

**Files:**
- Modify: `rust/crates/babylon-persistence/tests/national_household_units.rs` and its `tests/support/` files
  (`country_bench.rs`, `country_rules.rs`, `country_seekers.rs`, `country_sizes.rs`, `economy_health.rs`,
  `country_fund.rs`)
- Create: records under `reports/country-opening-2026-11/`. No log is committed: the repository ignores log files
  and its hygiene gate refuses a tracked file that it ignores.

**Decisions:**
1. **Which scenario.** A bench names its scenario: the shipped one (`economic_catalog::national_catalog_input()`, as
   today) or the twelve trades (`national_catalog_input_for` with this plan's fixture, included by `include_bytes!`).
   Both are captured by `capture_national_campaign(input, campaign())`. Every test and recorder that exists keeps the
   shipped scenario and every value it pins.
2. **Sizes first.** `the_twelve_trades_sizes` counts for the fixture what `the_country_s_sizes` counts for the shipped
   opening, filled from its first failing run, with the seekers' rows against `SEEKER_BOUND` (131,072). If the
   members with seekers do not fit, stop and report: nothing else of this task is built.
3. **The wage a seeker is offered.** As today, the highest wage among the pool's members paid a wage. A pool with none
   (working owners or unpaid family only) offers, for the twelve trades, its place's average wage: the sum of wage
   times employed persons over the place's members paid a wage, divided by the sum of those persons, rounded down.
   For the shipped scenario it stays $24.
4. **The cost of a batch's labor in the record.** For the shipped scenario, the default wage, as today. For the twelve
   trades, for each process: the sum of wage times employed persons over the members paid a wage at the process's
   sites, divided by the sum of those persons, rounded down. The record's legend says which it is.
5. **The order of paying** is the scenario's own when its opening carries one (`opening.market_clearing`), and the
   bench's seven products otherwise. For the twelve trades the baseline is the scenario as it ships, its own policy
   untouched; the `market` set would be the same run and is not recorded; the other sets add what they add today.
6. **The fund** is the bench's stand-in, as its plan's call 15 has it. Its head figures are computed for this
   opening, and the sentence about the reserve is written only when the two sums say so.
7. **The records.** One timed period of each set. Then 34 periods of the baseline, of all six rules and of all six
   with benefits, as `twelve-trades-<set>.json`. A refusal is written into its record and reported, never worked
   around. No conclusions: the lead reads the records. A committed file holds at most 1,048,576 bytes (the hygiene
   gate's budget; a record of 34 periods of the shipped opening holds about 870,000). A record over that is written
   whole to the build's temporary folder, as the long recorder writes its own, and its rows of periods 1, 2, 3, 4,
   5, 13 and 34 are committed as `twelve-trades-<set>-summary.json`.
8. **Nothing shipped moves:** not `the_country_s_sizes`, `the_country_s_public_providers`, the tick's three-period
   digest, nor the committed records of `reports/country-bench-2026-11-24/`.

- [ ] **Step 1: Write** `the_twelve_trades_sizes` with empty literals and `the_twelve_trades_open_on_the_bench` (the
  baseline closes one period; money, persons and the labor force are checked by the bench, as for the shipped
  scenario).
- [ ] **Step 2: Run them and see them fail.** Fill the sizes from what the failure prints. Check the seekers' fit.
- [ ] **Step 3: Implement** decisions 1 and 3 to 6.
- [ ] **Step 4: Run** one period of each set and write its time in the hand-off.
- [ ] **Step 5: Record** the three sets of 34 periods, in the background, one log each, outside the repository.
- [ ] **Step 6: Gate, run `mise run check:hygiene`, and commit** with the records. Hand over to the lead: the sizes,
  the times, each record's size in bytes, every refusal (period, stage and the engine's words) and each record's
  first and last row of jobs.

### Task 9: Three earning accounts in every county (rule O17)

**Built here, with three earning accounts.** The homes design of 21 November (ADR315) amends rule O17 to tenant and
owner groups in each band, and its build order holds "the two held tasks of the twelve trades plan" for its own first
step. The Director's ruling of 24 November (ADR324) is later: it orders the opening whole, these two tasks in it, and
puts no housing step before the pay fight. So Tasks 9 and 10 are built as written, and the homes plan's first step
later splits each band by tenure. This is the lead's reading of the two records, told to the Director on 25 November.

**Files:**
- Modify: `rust/crates/babylon-persistence/src/national_household_allocation/{model.rs, allocation.rs, source.rs}`;
  `national_resident_allocation/allocation.rs:173` (the cross-check of shares); `national_economy/opening/aid.rs:72`;
  `rust/crates/babylon-client/src/money_map/household.rs:279-290`
- Test: `national_household_allocation/tests.rs`; `national_twelve_trades.rs`; the client's `household.rs` tests

**Interfaces:**
- Produces:

```rust
// HouseholdBudgetKey gains, with explicit discriminants after today's six:
EarningLowerPaidHalf = 7,     // label "earning-lower-paid-half"
EarningBetterPaidForty = 8,   // label "earning-better-paid-forty"
// earning() covers EarningNonowner, EarningOwner and the two new keys; owner_exposure() is unchanged.
// NationalHouseholdAllocation gains `next_forty_households_bps: Option<u16>`.
pub(super) fn allocate_county(c: HouseholdCountyControls, owner_bps: u16, next_forty_bps: Option<u16>)
    -> Result<Vec<HouseholdBudgetAllocation>>;
```

**Decisions:**
1. **Keys and bytes.** `HouseholdBudgetKey` is `#[repr(u8)]` and `as u8` names a principal (`identity.rs:57`, `:212`),
   so today's six keep 1 to 6 and the new keys are 7 and 8, sorting last; they never occur under schema 7. Under schema
   8 the earning accounts are the two new keys and `EarningOwner`; `EarningNonowner` is not made. `EarningOwner` keeps
   its principal rule and its business shares (`financial.rs:307` gives shares to `owner_exposure()` keys). How shares
   are divided between bands is the Director's open question.
2. **Households, in each county.** With earning households `H`: `owners = ceil(H x owner_bps / 10_000)` (today's
   rule); `upper = ceil(H x (owner_bps + next_forty_bps) / 10_000)`; better-paid forty `= upper - owners`; lower-paid
   half `= H - upper`. Persons and employed follow today's code with three earning slots for two: working owners first
   to the owners; the employed shortfall over the three by households; the other persons over the five ordinary slots
   by households; the other employed by the three slots' persons, so in proportion to households (call 15) but for the
   owners' working owners. Other keys are unchanged; a place's accounts are the sums over its counties, as today.
3. **Words (the lead's ruling E).** The review's roster rule is not changed: its "Next 40%" is 4/9 of the non-owner
   households ranked by people at work (`roster.rs:345-420`), shown by `band_label` (`projection.rs:336`) and
   `band_words` (`client/organizer/county.rs:87`). The new accounts are another cut and take their own words: in the
   review their groups are named by `key.label()` ("earning-lower-paid-half", "earning-better-paid-forty",
   "earning-owner"); the money map's `opening_role` adds "Historical earnings · lower-paid half · no modeled business
   ownership" and "Historical earnings · better-paid 40% · no modeled business ownership".
4. `allocate_home_county` cross-checks the allocation's owner share against the policy (`allocation.rs:173`); it now
   checks `next_forty_households_bps` there too.
5. **The aid donor** (ruling F; the organizer's base is the lowest stratum) is carved from `EarningLowerPaidHalf` under
   schema 8 (`aid.rs:72`). `aid::retarget` (`aid.rs:251`) takes the lowest-id site that makes a storable good with an
   employee of the donor's parent, which is also the organizer's workplace (`organizer.rs:108`); under schema 8 it moves
   to a lower-paid-half site. `refine.rs` is unchanged: its only spec producer is the claimant (`claimant.rs:46`).
6. The engine's household lifecycle reads `HouseholdKind`, never the key. The observer report writes the new keys by
   their serde names; its `VERSION` stays 3, since schema 7 writes no new value.

- [ ] **Step 1: Write the failing tests.**
  - `a_county_splits_its_earners_in_three` (allocation): controls population 1,000, household persons 950, 300 with
    earnings, 100 without, 400 employed, 30 reserve, 20 working owners; `owner_bps` 1,000, `next_forty_bps` 4,000. Rows
    (households, persons, employed, reserve): `EarningOwner` 30, 73, 47, 1; `NoEarnerNonowner` 90, 196, 0, 10;
    `NoEarnerOwner` 10, 22, 0, 1; `CollectiveResidence` 0, 50, 20, 2; `EarningLowerPaidHalf` 150, 366, 185, 9;
    `EarningBetterPaidForty` 120, 293, 148, 7. Persons add to 1,000, employed to 400, reserve to 30.
  - `the_same_controls_under_schema_7_are_today`: with `None`, `EarningNonowner` 270, 659, 333, 16 and the other rows as
    above. So the two lower bands together are today's nonowner earners, and the owners are unchanged.
  - `one_earning_household_makes_one_band`: one earning household gives one owner household and no lower-paid or
    better-paid row.
  - `every_place_has_three_earning_accounts` (fixture): each domestic financial domain with earning households has
    accounts of the three keys, none of `EarningNonowner`, each the sum of its counties' rows.
  - `the_aid_donor_comes_from_the_lower_paid_half` (fixture): the donor's parent key is `EarningLowerPaidHalf` and its
    workplace is the organizer's.
  - `opening_roles_name_the_bands` (client): the two new strings, exactly.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the crate's allocation tests, `binary(national_twelve_trades)`,
  `binary(national_household_units)`, `binary(resident_allocation)`, `binary(shipped_world_bytes)`, the crate, `-p
  babylon-client`.
- [ ] **Step 5: Gate and commit** `feat(economy): split every county's earners into three bands`.

### Task 10: Each county's jobs are dealt to its bands by pay

**Files:**
- Modify: `rust/crates/babylon-persistence/src/national_resident_allocation/households.rs` (`partition`, `take`)
- Test: `national_resident_allocation` crate tests; `national_twelve_trades.rs`

**Interfaces:**
- Consumes: `county_wage` (Task 7) and the three band keys (Task 9).
- Produces: no new public name; `partition` keeps its place and signature, reading each row's `county_wage`.

**Decisions:**
1. **The lead's ruling C on O17's "a place's jobs are ranked by their pay": bands are dealt county by county.** Inside
   each county its jobs are ranked by pay and dealt to its three bands; a place's accounts are the sums over its
   counties. This is where people live, and it keeps `partition` where it is.
2. **Whole persons.** Under schema 8 the rows go: working owners first (owners' band first, as today), then employees by
   `county_wage` from highest, ties by site id, then unpaid family. Each row takes whole persons from the employed
   quotas in the order `EarningOwner`, `EarningBetterPaidForty`, `EarningLowerPaidHalf`, `CollectiveResidence`, filling
   each before the next; a row meeting a quota's end splits into one member row per band. Reserve follows today's rule.
3. **Bounds.** At most six domestic budgets a county; dealing splits at most one row at each band's edge, as today's
   key order does. Task 6's allocation test pins the member count again. The 79,489 accounts, 90,794 claims and 87,960
   needs of `material_circuit_v4.yaml:693-695` are the county-level census of 2 October, before folding, each under
   131,072;
   the live opening is far smaller. Stage 5's wants will meet the needs bound and must count it.

- [ ] **Step 1: Write the failing tests.**
  - `jobs_are_dealt_by_pay_in_whole_persons` (households): quotas owners 10, better-paid forty 40, lower-paid half 50,
    collective 5; employee rows A ($50, 30), B ($30, 40), C ($20, 35). Members: A owners 10 and better-paid 20; B
    better-paid 20 and lower-paid 20; C lower-paid 30 and collective 5. With B's wage set to $50 and its site id below
    A's, B is dealt first.
  - On the fixture world (`national_twelve_trades.rs`), on the county-level allocation:
    - `the_best_paid_jobs_go_to_the_owners`: in Wayne, and in one place of several counties for each of its counties,
      every employee member of the owners' band works at a workplace whose `county_wage` is at least that of every
      employee member of the better-paid forty, and so for the better-paid forty over the lower-paid half, except the
      one row split at each edge.
    - `the_county_review_sees_three_earning_groups`: the review config's groups include "earning-lower-paid-half",
      "earning-better-paid-forty", "earning-owner" and "earning-lower-paid-half (aid donors)"; the roster builds; every
      top 1% and next 9% row is in a group with ownership income.
    - `the_review_and_the_accounts_use_their_own_words`: in Wayne, the roster's "Next 40%" households and the
      better-paid account's households are both counted (pin the two literals the first run prints); no group label
      contains a word of `band_label` ("Top", "Next", "Bottom", "%"), and no `band_label` contains "paid".
    - `owners_keep_the_business_shares`: every ownership claim to a domestic household is held by an `EarningOwner` or
      `NoEarnerOwner` account; none by a lower-paid or better-paid account.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the crate's allocation tests, `binary(national_twelve_trades)`, `binary(national_county_review)`,
  `binary(resident_allocation)`, `binary(shipped_world_bytes)`, the crate.
- [ ] **Step 5: Gate and commit** `feat(economy): deal each county's jobs to its bands by pay`.

The lead then runs `mise run rust:check-no-docs` and `mise run check`, and plays the shipped world in Wayne.

### Task 10b: The bench's records with the bands

Commit `test(persistence): the country bench's records of the twelve trades with bands`. Test code only.

Tasks 9 and 10 change the household accounts, who holds which job, and so the seekers' rows and the fund's
recipients. `the_twelve_trades_sizes` is pinned again from a failing run, the seekers' fit first (decision 2 of Task
8b binds here too). One period of each set is timed, and the three sets of 34 periods are recorded again as
`bands-<set>.json` beside the three of Task 8b, which stay. Gate, commit, and hand over as in Task 8b.

**A note for the lead, not a change here.** The paused household-units plan still says a schema 7 optional section
compiles as v13 and stands on the shipped policy "with its `paying_order`" (its lines 309-310 and 1108). This plan
refuses that key under schema 7; that plan is corrected when it resumes.

## What the bands' records asked for (25 November, evening)

Tasks 0 to 10b are built. Task 10b's records brought three things, and Tasks 10c, 10d and 11 answer them, in this
order: an engine refusal in period 32 of the run with all six rules and benefits (Task 10c); no figure of a record
names a band, though the Director ruled the bands in so that the bench shows who holds the better-paid jobs (Task
10d); and the reviewers' small notes of the whole stage (Task 11).

### Task 10c: A raise of a resting price touches its own product only (the engine)

Commit `fix(material-circuit): raise a resting price on its own product only`.

**What broke.** With the bands, all six rules and benefits, the engine refused period 32 of the twelve-trade run:
`PurchaseInvariant` at the finish, and `bands-all-six-with-benefits.json` holds 31 rows. The lead replayed the run
with prints in the engine. At the close of period 32 a shop with two offers had its first good's resting price raised
from $86.432156 to its cost, $86.882156, and that price was written to BOTH its offers. Its second good stood at
$324.432156 with a minimum of $93.432156, so that offer left its own range and the next state's validation refused
it (`recurring/validation.rs`, the range check of a `Responsive` offer). In periods 27 to 32 of that run, 194 raises
were written at shops with two offers, and 32 of them overwrote a second good's price that differed from the first's.

**The defect.** In `adjustment/restart.rs`, `raise_resting_prices` gathers the SITES that have a resting-price
receipt, works out one raise from the product the restart reads the site by (`product_of`: a process's first output,
or the first good a merchant handles), caps it at the lowest `maximum` among ALL the site's offers
(`OfferTables::ceiling`), and `apply_lifts` writes it to every offer row, every price receipt row and every service
market row of the site. But a resting price is a seller's price of one product: `RestingPriceReceipt` names the good
and the unit. The small worlds' sellers have one product each, so no measured world shows it.

**Files:**
- Modify: `rust/crates/babylon-material-circuit/src/adjustment/restart.rs` (`OfferTables`, `raise_resting_prices`,
  `apply_lifts`, and its tests)
- Modify, if a digest moves: `rust/crates/babylon-persistence/tests/national_household_units.rs` (the pins of
  `the_bench_digests_before_the_squares`) and the records named in decision 7

**Decisions:**
1. **A raise is of a product.** A site is considered for a raise only when the product the restart reads it by
   (`product_of`) is itself named by one of the close's resting-price receipts (site, good, unit). A resting receipt
   for another good of the site raises nothing.
2. **It is capped by that product's own offer.** `OfferTables::ceiling` is keyed by product (site, good, unit): the
   lowest `maximum` among the offers of that product at that site whose pricing has a range.
3. **It is written to that product's rows only:** the site's offer rows, its price receipt rows
   (`transition.prices`) and its service market rows (`transition.service_markets`) whose good and unit are the
   product's. Every other row of the site keeps its price.
4. **The receipt keeps its shape:** `RestingPriceToCostReceipt { period, site_id, old, raised }`, one raise a site, of
   the site's product. No wire and no contract changes.
5. **Not built here:** a shop's other goods are still never raised to their own cost, because the restart reads a
   workplace by one product. Say so in the hand-off; it is the lead's to carry to the Director.
6. **Bytes.** A seller with one product behaves as today, so every measured small world keeps its bytes (the long
   `reproduces_` tests), and a catalog that does not ask for the owner's restart keeps every byte.
7. **The bench.** `baseline`, `market` and `no-seekers` have no restart: their digests and records must not move. The
   digests of `all-six` and `all-six-with-benefits` in `the_bench_digests_before_the_squares` may move. If they do:
   fill them again once from one failing run, put each old and new value into the hand-off, and record the shipped
   opening's sets again (`record_country_bench_sets`; the three sets without a restart must come out equal apart from
   the times). If they do not move, record nothing of the shipped opening. Then record the bands' two sets with the
   restart (`record_twelve_trades_sets` with `TWELVE_TRADES_SET=all-six`, then with `all-six-with-benefits`) and
   report how many periods each closes: the set with benefits is expected to close all 34 now, and if it is refused
   again, that is a result to report with its period, stage and the engine's words, not a thing to work around. The
   two summaries of 400 periods are the lead's to rerun, and no `README.md` under `reports/` is edited.

- [ ] **Step 1: Write the failing tests** in `restart.rs`'s test module, on a fixture of one merchant that handles two
  goods, A first and B second, each with a `Responsive` offer, and a close in which a resting-price receipt names
  what the test says:
  - `a_raise_leaves_the_other_goods_of_a_shop`: A rested and stands under its unit cost; B's price is above A's cost
    and B's `minimum` is above A's cost. After `raise_resting_prices`: A's offer and A's price receipt row are at A's
    cost; B's offer and B's price receipt row keep B's price; one `RestingPriceToCostReceipt` with A's old and new
    price; and the state passes `canonical_state` (today it is refused with `PurchaseInvariant`).
  - `a_resting_second_good_raises_nothing`: only B has a resting-price receipt. No offer moves and no
    `RestingPriceToCostReceipt` is written (today A is raised).
  - `a_raise_is_capped_by_its_own_offer`: A's `maximum` is above A's cost and B's `maximum` is below it. A is raised
    to its cost (today it is capped at B's maximum).
  - The existing tests of the restart keep their values.
- [ ] **Step 2: Run them and see each fail** for the reason given in brackets.
- [ ] **Step 3: Implement** decisions 1 to 3.
- [ ] **Step 4: Run** the crate (`mise run rust:test:q -- -p babylon-material-circuit`), `-p babylon-circuit-worlds`,
  and in the background the long tests (`--run-ignored only` with `test(/^reproduces_/) |
  test(hours_fold_every_reference_run)` on `babylon-material-circuit`). Expected: pass, no value changed.
- [ ] **Step 5: The bench.** `binary(national_household_units)`; then the ignored pin
  `the_bench_digests_before_the_squares` by name; then decision 7.
- [ ] **Step 6: Gate and commit** with the subject above. The gate's sentinel leg passes when `mise run
  check:bsl-sentinels` reports no E-SENTINEL, whatever the count of older W-SENTINEL warnings. Hand over: each test
  seen failing; whether a shipped digest moved, with old and new values; how many periods each of the bands' two sets
  closes; each re-recorded record's size in bytes; and decision 5's limit in one sentence.

What the player would see: a shop's second good no longer takes the first good's price when the owner's restart
raises a resting price.

### Task 10d: The bench reads the bands

Commit `test(persistence): the country bench reads each band's jobs, pay and money`. Test code only.

**Why.** The Director ruled the bands in now so that the country bench shows who holds the better-paid jobs in each
place (ADR325, N2). Tasks 9 and 10 make the three accounts and deal the jobs; Task 10b records the sets again. But
no figure of a record names a band, so nothing of the ruling can be read from the bench yet.

**Files:**
- Modify: `rust/crates/babylon-persistence/tests/national_household_units.rs` and its `tests/support/` files
  (`economy_health.rs`, `country_bench.rs`)
- Create (by the recorder): `reports/country-opening-2026-11/bands-opening.json`
- The three `bands-<set>.json` records gain a column. This task records the baseline (Step 4); the lead records
  the two sets with rules again at the stage's end.

**Decisions:**
1. **A band is a household account's budget key** (`HouseholdBudgetKey::label()`: "earning-lower-paid-half",
   "earning-better-paid-forty", "earning-owner", "no-earner-nonowner", "no-earner-owner", "collective-residence").
   The bench reads each domestic account's key from the capture's own generation witness
   (`catalog.national_generation()`: a `household_incidence` row's `destination` is the account and `margins.key` its
   key), as `every_place_has_three_earning_accounts` does. An account carved from another (the aid donor, the
   claimant) is counted under its parent's key. A domestic account whose key cannot be found is a typed `BenchError`,
   never skipped. Accounts abroad and in dependencies are not read.
2. **The opening by place and band** is one file, `bands-opening.json`, written once by `record_twelve_trades_sets`
   before the first set is played. For the nation and for each domestic place (keyed by the place's hub county
   geoid), for each key, in this order: `accounts`, `households`, `persons`, `employed_persons`,
   `looking_persons`, `wage_bill_micros`. The wage bill is one period's: the sum, over the account's members paid a
   wage, of the wage times the member's employed persons times the member's hours a person. The file's head gives
   the scenario, the compiler, the legend of the six figures in plain words, and the count of places. Rows are
   sorted by geoid and then by key. The reader derives a band's average hourly pay as the wage bill over its
   employed persons and hours.
3. **Each period by band, for the nation.** A period's row gains `earners`: for each key, `[at_work, looking,
   wages_received_micros, benefits_received_micros, money_micros]`: the persons at work and looking at the close
   (after the moves of people who look for work, as `jobs_after_moves` counts them), the wages the accounts were
   paid in the period, what the fund's programs paid them in the period, and their cash at the close. The record's
   `columns` gains the legend. It is written for the twelve-trade scenario only: a record of the shipped scenario
   keeps today's keys, so no committed shipped record goes out of date.
4. **Sums that must hold,** asserted by the bench every period (a failure is a `BenchError`, as its other checks
   are): the sum of `at_work` over the keys equals the domestic figure of `jobs_after_moves`, and so does `looking`;
   the sum of `money_micros` equals the record's own `households_domestic` money.
5. **Size.** The column adds about thirty figures a period. A record that passes 1,048,576 bytes with it follows Task
   8b's decision 7.
6. No pin of the shipped scenario moves, no shipped record is written, and no `README.md` under `reports/` is edited.

- [ ] **Step 1: Write the failing tests** in `national_household_units.rs`:
  - `the_opening_names_every_band` (the fixture): the nation's rows hold exactly the six keys above and no
    "earning-nonowner"; the sums over keys of `persons`, `employed_persons` and `looking_persons` equal the opening's
    domestic totals as the bench's census counts them; every place with an earning household has the three earning
    keys; in Wayne (26163) the average hourly pay of the owners' band is at least the better-paid forty's, and that
    at least the lower-paid half's (pin the three figures from the first run, in millionths of a dollar).
  - `a_period_names_every_band` (the fixture, one period of the baseline, as `the_twelve_trades_open_on_the_bench`
    plays it): the row has `earners` with the six keys, and decision 4's three sums hold.
  - `the_shipped_record_has_no_earners`: one period of the shipped baseline has no `earners` key.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement** decisions 1 to 4.
- [ ] **Step 4: Run** `binary(national_household_units)`, `binary(national_twelve_trades)`,
  `binary(shipped_world_bytes)`. Then run `record_twelve_trades_sets` with `TWELVE_TRADES_SET=baseline`, in the
  background, to write `bands-opening.json` and the baseline's record with the new column; check that the record
  differs from the committed one in the new column, the legend and the times only.
- [ ] **Step 5: Gate, run `mise run check:hygiene`, and commit** with `bands-opening.json` and the baseline's record.
  Hand over: the nation's six rows of `bands-opening.json` in full, Wayne's rows, the three pinned figures, each
  file's size in bytes, and the baseline's `earners` of periods 1, 2 and 34.

What the player would see: nothing yet. It lets the lead say, from the game's own opening, which band holds which
jobs at what pay, and on whom a layoff lands.

### Task 11: The reviews' small notes

Two commits, in this order: `refactor(economy): close the reviews' small notes on the twelve trades` (kernel,
persistence, tests, the register) and `refactor(material-circuit): test a workplace before reading its product`
(the engine's two items). No behaviour changes: every pin of the shipped world, of the twelve trades and of the
country bench keeps its value, and no record under `reports/` is written.

Each item below was raised by a task's reviewer and left for this piece. An item that turns out to be done already
is reported as done, with the commit that did it. An item that cannot be done without moving a pinned value is left
and reported with the reason.

**Tests that tighten (`rust/crates/babylon-persistence/tests/`).**
1. `shipped_world_bytes.rs`: where the version 11 input cuts the defines at the first `[city_pd]`, assert that what
   is cut holds exactly the two sections `[city_pd]` and `[county_review]`, so that a section added after them is not
   cut unseen.
2. `national_cohorts.rs`, `the_v2_table_decodes_with_its_own_pins`: compare all 32 bytes of `artifact_sha256()` and
   of `function_mapping_sha256()` with the hex in the committed metadata, not the first four bytes.
3. `national_twelve_trades.rs`: the fixture's weights test derives its twelve expected rows from the shipped defines
   (consumer goods' share taken out of capital goods, leisure's out of household services, as the plan's Task 4
   decision 4 has it) and compares the fixture's rows with them, where today it checks each row against itself.
4. `national_twelve_trades.rs`: `assert_eq!(pay.rows().len(), 65_065)` sits in a test it has nothing to do with (about
   L113). `national_trade_pay.rs` already holds that figure: drop the stray one.
5. `national_twelve_trades.rs`: the bounds are checked with `<=` where the plan's Task 6 says "under": use `<`.
6. `national_twelve_trades.rs`: the check that no foreign account holds a claim on Wayne's capital goods sites
   matches only each foreign counterpart's pooled principal: check the claim holder's location instead.
7. `national_twelve_trades.rs`: `a_representative_site_of_one_source_row_pays_the_place_wage` skips one-row sites with
   no jobs, so the branch of `place_wage` that takes the mean of the rows' own wages has no direct test. Add one, as
   a crate test beside `place_wage` if the fixture has no such site.

**Readers and refusals (`rust/crates/babylon-persistence/src/`).**
8. `national_cohorts/parse.rs` (about L74) and `national_cohorts/mapping.rs` (about L55) read a trade with
   `EconomicFunction::from_source_key`: read it with the table's own set (`TradeSet::from_source_key`). Add a test: a
   version 1 table that names `consumer_goods` is refused by the parser, before the mapping is asked.
9. `national_trade_pay/model.rs` (about L331): the nation's figure falls back to a zero `Currency` for an empty table.
   `from_rows` refuses an empty table with a typed error, with its test, so that no zero wage can be built.
10. `national_trade_pay/artifact.rs` (about L124-127): `national_trade_pay_reference` turns a county table failure into
    `UnknownCounty` and a version 2 cohort failure into `Coverage`, and the cause is lost. Give each its own variant
    that carries the cause, if that touches no caller's match beyond this crate; else leave it and say so.
11. `national_economy/policy/admission.rs`: under the twelve trades, `consumer_goods` must be a storable good and
    `leisure` a period service (of either stage); refuse the other kinds with the existing `Profile` error, with one
    test for each. Do not tie any other product to a stage: a scenario may place a service in either stage.
12. `economic_catalog/capture.rs` (about L503): a policy of twelve trades WITH an experiment would compile as a
    company-scale experiment. Refuse it with a typed error, with its test.
13. `economic_catalog/preset.rs`: add a test that `national_catalog_input()` equals
    `national_catalog_input_for(<the shipped defines>)` in every source's kind and bytes, so that the two cannot
    part unseen. Do not reshape the `let rows` block (the test `the_release_tool_can_read_the_national_rows` holds it).
14. `national_economy/opening/external.rs`, `partition`: `Vec::with_capacity(10)` becomes `weights.len()`.
15. `companies/capture.rs`, `from_workplaces`: a site whose trade is not in the set is left in `by_function` and
    dropped. Refuse with a typed error when anything but public provisioning is left over, with its test.
16. `national_economy/grain/build.rs`: move the wage pass of `coarsen_source_allocation` into a helper and drop that
    function's `too_many_lines` allow; `place_wage` sums with `checked_add` and a typed refusal (`Arithmetic`), where
    it has `saturating_add`; `place_average`'s doc comment also says "or whose rows hold no jobs"; `site_wages`' doc
    comment is wrapped at 100 columns.
17. `city_pd.rs`: `Books`' doc comment says each figure is worked out from the scenario's wage; under observed pay it
    is the payroll site's wage. Reword.
18. `county_review.rs`, `going_wage`: refuse a zero wage with a typed error, with its test, as Task 7's foreign
    fraction does.

7b. `national_twelve_trades.rs`, `every_place_has_three_earning_accounts`: assert that the set of counties in the
   household incidence equals `budgets.counties()`, so that a county missing from the incidence is seen; and replace
   the bound `places > 100` by the exact count of domains, pinned once from a run.
7c. `national_twelve_trades.rs` (about L23): `use babylon_practice_contract::{self, Band, Roster};` carries a redundant
   `self`. Drop it if `check:bsl-sentinels` then still reports no E-SENTINEL; else leave it and say so.

**The bench's helpers (`rust/crates/babylon-persistence/tests/`).**
19. `support/economy_health.rs`: `recipe_cost`'s doc comment says "at the default wage"; it uses `census.labor_wage`.
    `process_wages`: with no member paid a wage, refuse with a typed `BenchError` where `average` falls back to 0;
    use checked sums as `place_offer` does.
20a. `national_household_units.rs` (about L1221): the head of a record of the twelve trades names the baseline it is
    judged against as `twelve-trades-baseline.json`; the records with bands are judged against `bands-baseline.json`.
    Pass the baseline's file name into `scenario_header`. The lead records the three `bands-*` records again; do not
    run the recorders.
20. `national_household_units.rs`, `scenario_report`: when the benefit's due is within the public bodies' cash, leave
    the `fund_reserve` key out (Task 8b's decision 6). No committed record changes: both scenarios have the sentence.

**The register.**
21. `data-artifacts.yaml`: the `national_trade_pay_2024` entry says "no reader exists yet"; it has one,
    `babylon-persistence::national_trade_pay`. The version 2 cohort entry's "will parse" becomes "parses". Only the
    words change: `tools/make_data_artifacts.py --check` and `tests/unit/reference/test_data_artifacts.py` pass, and no
    table's bytes or metadata change. If the words are pinned anywhere, stop and report.

**The engine (`rust/crates/babylon-material-circuit/src/adjustment/restart.rs`), the second commit.**
22. `restart_stopped` reads `product_of` and `is_shared_service` for every workplace: test `tested` first, the same
    result with less work.
23. `a_workplace_of_a_shared_service_is_not_tested` asserts `raises == 0`, which cannot fail in its fixture. Drop that
    assertion; `a_shared_service_never_rests` already holds the line.

- [ ] **Step 1:** for each item that asks for a test, write it and see it fail (or, for a tightening of an existing
  test, see the tightened test pass and say that it could not have failed before).
- [ ] **Step 2: Implement** the items, one file at a time.
- [ ] **Step 3: Run** `binary(shipped_world_bytes)`, `binary(national_cohorts)`, `binary(national_trade_pay)`,
  `binary(national_twelve_trades)`, `binary(national_game_policy)`, `binary(national_county_review)`,
  `binary(national_household_units)`, the persistence crate, `-p babylon-material-circuit`, and the two Python files
  of item 21. Expected: pass, no pinned value moved, `git status` shows no change under `reports/`.
- [ ] **Step 4: Gate and commit** in the two commits above. The hand-off lists every item by its number: done, done
  already (with the commit), or left (with the reason).

## What the re-reading of 25 November changed

- **The bench.** This plan was written before the Director ruled that the country's opening is counted on the country
  bench as it is built (ADR324). Tasks 8b and 10b are new, and every task that changes the kernel or the persistence
  crate also runs the bench's binary.
- **Tasks 9 and 10 are built here.** The homes design had held them for tenure; the later ruling orders the opening
  whole (the note at Task 9).
- **The market policy** has three fields this plan did not know. Schema 8 leaves them empty and false (Task 5,
  decision 3).
- **Moved lines:** `opening/financial.rs` (285-298, 307, 343 and 386), `material_circuit_v4.yaml` (693-695),
  `admission.rs` (789 and 798), `city_pd.rs` (230 and 284), the cohort reader's test (138).
- **No log is committed, and a record keeps to the size budget** (Task 8b, decision 7; added after GitHub's hygiene
  check refused the country bench's logs on 25 November).
- **Silent, and left so:** what a working owner or an unpaid family member is paid (Task 7 pays employees only; they
  keep no wage, as ADR267 has it), the public provider with no worker and no grant, and the opening's own collapse in
  period 2 (stage 5 rebuilds the numbers). The bench's records of Tasks 8b and 10b will show each.
