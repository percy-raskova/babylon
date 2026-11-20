# The County Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the County Review playable in a Wayne campaign: each period the county ranks
households by the wage tax they paid, the player's organizer reaches one household in a named
position, reached households ask for or defend relief units, and next period's support lines follow
the county's list.

**Architecture:** The rules are pure, exact functions in `babylon-practice-contract`
(`county_review`): a roster of household positions, the county's list, the session, a preview and a
fogged projection. `babylon-tick` hands those functions the labor and tax facts of the close, keeps
the roster in a new optional section of the material world register, and writes next period's
support lines and the hours spent. A fifth native rule operation, `county-review`, runs the session
after the organizer's practice. `babylon-persistence` captures the county's configuration and
opening roster, and adds the projection to the organizer snapshot. `babylon-client` shows four views
and one new organizer choice.

**Tech Stack:** Rust (workspace `rust/crates`, Bevy 0.20 client), BSL rule files, PostgreSQL
runtime, Python 3 tools, TOML scenario defines.

**Spec:** `docs/superpowers/specs/2026-11-19-county-review-design.md` (sixth draft, amended the same
day for the Director's direction on who works). Section numbers below refer to it. Read sections 7.1
to 7.6, 7.11 to 7.13 and Appendix D before any task.

**Build order:** Tasks 1, 2, 3, 4, 5, 6, 8, 7, 9, 10, 11. Task 8 is built before Task 7: the
operation and its rule exist first, so the county section has a real caller the moment it is built.
Tasks 5 to 11 were checked against the code before they were built, and their text carries what that
check found.

## Global Constraints

- Work only in `/media/user/dev-ssd/worktrees/PER-366/babylon`, branch
  `codex/PER-366-population-classes`. Start every shell command with `cd` to it. Never push. Never
  open a pull request.
- The disk is unencrypted: no secrets, no `.env`, no `babylon-data` there.
- Cargo runs at most 4 jobs. Never pass `-j`. One cargo or pytest process at a time. Use `mise exec
  -- cargo ...` and `mise run rust:test:q -- -p <crate> -E '<filter>'` for scoped tests.
- The Rust gate has two forms. The whole gate is `mise run rust:check-no-docs`. It rebuilds and runs
  every crate's tests and takes over half an hour, so it is started in the background with its
  output in a log file, and nothing else uses cargo until it ends. The scoped gate is four legs, run
  one at a time: from `rust/`, `mise exec -- cargo fmt --all -- --check` and `mise exec -- cargo
  clippy --workspace --all-targets --locked -- -D warnings -D clippy::cognitive_complexity`; then
  `mise run rust:test:q -- -p <crate>` for each crate the task changed; then `mise run
  check:bsl-sentinels`. Tasks 3, 4, 5 and 10 change one crate and no type that another crate already
  uses, so they run the scoped gate, and the lead runs the whole gate when their phase ends. Every
  other task runs the whole gate.
- Python runs as `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONPATH="$PWD/src" mise exec -- uv run
  --frozen pytest ...`.
- Commit one task at a time: `git add <files>` then `PYTHONPATH=src mise exec -- git commit -F -`
  with the message on stdin. Check `git log --oneline -1` moved. The body ends with `Part of
  PER-366` and `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never commit `uv.lock`.
- A commit that changes a file under `tests/baselines/` carries the trailer `Baselines:
  blessed(per-366-county-review)`.
- No rule reads an identifier to settle a tie or to order an outcome. Identifiers order encodings
  only.
- No rule uses floating point. Money is `i128` millionths of a dollar. Counts are `u64`. Places are
  exact fractions.
- No rule reads the average of a group. A rule decides for a position from that position's own
  figures (spec 7.2, Amendment AM).
- A household's band is its place in the Director's rule of thirds at the opening: the top 1%, the
  next 9%, the next 40% or the bottom 50% (spec 7.2). Task 3's opening rules set it once, and the
  household keeps it. No rule reads a band, except as the last tie of an exact split. Views show it
  and count by it.
- Every refusal is a typed error or a typed outcome with a reason. No panic, no `unwrap` outside
  tests, no silent clamp.
- Scenario numbers stay in `content/scenarios/national/defines.toml`: unit price is derived from the
  opening ($280 in Wayne), session 2 hours, bringing 2 hours, first session in period 4, wage $24,
  City PD 3,529 positions at 160 hours.
- On-screen text never calls a position "workers", "proletariat" or "the base". Every view of this
  slice carries the line: "This slice has no nation, no solidarity and no consciousness. Households
  act on their own money only." Nation shows as "pending".
- Earned figures (a position's dollar figures, its households, its reached households, why its
  households stayed home) are shown only for a position the player has contacted. The list's order
  and units paid and unpaid are public (spec 7.11).
- Markdown is wrapped at 120 columns, headings at 80. Refer to the player as "they".
- The first class, the spending limit and tax rates are never written by this slice.
- Registers, snapshots and fixtures with no county section keep their bytes.

## Review Focus

1. **The roster moved between the player's choice and the contact landing.** The named position no
   longer exists, or every household in it is already reached. Expected: the turn commits, the
   organizer's hours are spent, and the session record says `no_such_position` or `nobody_left`.
   Tests in Tasks 4 and 7.
2. **The county has no money for relief.** Cash is below the first class, or the spending limit is.
   Expected: every household line is removed (no zero-amount line reaches the engine), nobody is
   paid, every reached household on the roll comes if it has hours, and no division by zero. Tests
   in Tasks 4 and 7.
3. **A campaign or fixture that has no county section.** Expected: registers decode and re-encode to
   the same bytes, the snapshot has no `county_review` field, the client shows the four views as
   unavailable with a reason, and no existing test changes. Tests in Tasks 7, 9 and 10.
4. **A crew with nobody at work, a group with no taxed wages, or a group with no free hours.**
   Expected: place zero with no division, "no time" recorded, no underflow. Tests in Task 4.
5. **The player looks at a past period, or at a position they have not contacted.** Expected: the
   roster's choose buttons are disabled with a stated reason on a past period, and the amounts of an
   uncontacted position are hidden with the remedy stated. Tests in Tasks 5 and 10.

---

### Task 1: The City PD's books

Spec 7.3 and 7.13. One constant is the wage, the visit price and the appropriation. Separate them,
and record the force's payroll on the public workplace that employs it. No engine line and no worker
changes.

**Files:**
- Modify: `rust/crates/babylon-practice-contract/src/state_opponent.rs` (`CityPdConfig`,
  `validate_city_pd_config`, `CITY_PD_SCHEMA_VERSION`, `CityPdError`)
- Modify: `rust/crates/babylon-practice-contract/src/state_opponent_codec.rs` (config domain to
  `babylon.city-pd-config.v2`)
- Modify: `rust/crates/babylon-persistence/src/national_economy/city_pd.rs` (remove `AMOUNT`;
  `assemble`; `add_opening`)
- Modify: `rust/crates/babylon-persistence/src/national_economy/policy/admission.rs`,
  `policy/game.rs`, `policy.rs` (new `[city_pd]` table; schema 7)
- Modify: `content/scenarios/national/defines.toml` (`schema_version = 7`; `[city_pd]`)
- Modify: `rust/crates/babylon-tick/src/material_world/city_pd.rs` (`CityPdRegister::validate`)
- Modify: every fixture that builds a `CityPdConfig` (find with `rg -l 'CityPdConfig \{'
  rust/crates`)
- Modify: `rust/crates/babylon-persistence/src/economic_catalog/preset.rs`, `capture.rs`,
  `contracts/economic_catalog_v1.yaml` and the tests that pin `national-world-v11` (compiler string
  becomes `national-world-v12`, once for this branch)
- Test: `rust/crates/babylon-practice-contract/tests/state_opponent.rs`,
  `rust/crates/babylon-persistence/tests/national_game_policy.rs`, the inline tests of
  `babylon-tick/src/material_world/city_pd.rs`

**Interfaces:**
- Produces, in `CityPdConfig` (after `appropriation_priority`): `pub payroll_site_account_id: [u8;
  32]`, `pub payroll_positions: u64`, `pub payroll_hours_per_position: u64`, `pub payroll_micros:
  i128` (decimal-string serde like the other amounts), `pub visits_per_period: u64`.
  `CITY_PD_SCHEMA_VERSION = 2`. New `CityPdError::InvalidPayroll`.
- Produces: `pub struct GameCityPdPolicy { pub positions: u64, pub positions_source: String, pub
  visits_per_period: u64, pub visit_hours: u64 }` on `NationalGamePolicy` as `city_pd`, parsed from
  `[city_pd]` with `evidence_class = "Designed"`. Schema 7 requires it.
- Later tasks read `payroll_site_account_id`, `payroll_positions` and `payroll_micros` for the
  county ledger.

- [ ] **Step 1: Write the failing contract tests** in `tests/state_opponent.rs`, using that file's
  existing config helper:

```rust
#[test]
fn config_carries_a_payroll_worked_out_from_positions_hours_and_wage() {
    let mut c = config();
    c.payroll_positions = 3_529;
    c.payroll_hours_per_position = 160;
    c.payroll_micros = 13_551_360_000_000;
    assert_eq!(validate_city_pd_config(&c), Ok(()));
    c.payroll_micros += 1;
    assert_eq!(validate_city_pd_config(&c), Err(CityPdError::InvalidPayroll));
}

#[test]
fn a_wage_other_than_24_dollars_is_accepted() {
    let mut c = config();
    c.hourly_wage_micros = 30_000_000;
    c.visit_cost_micros = 30_000_000;
    c.appropriation_micros = 30_000_000;
    c.payroll_micros = 3_529 * 160 * 30_000_000;
    assert_eq!(validate_city_pd_config(&c), Ok(()));
}

#[test]
fn the_appropriation_is_the_visits_allowed_times_the_price_of_a_visit() {
    let mut c = config();
    c.appropriation_micros = 2 * c.visit_cost_micros;
    assert_eq!(validate_city_pd_config(&c), Err(CityPdError::InvalidPrice));
    c.visits_per_period = 2;
    assert_eq!(validate_city_pd_config(&c), Ok(()));
}
```

- [ ] **Step 2: Run them.** `mise run rust:test:q -- -p babylon-practice-contract -E
  'binary(state_opponent)'`. Expected: compile failure on the missing fields.
- [ ] **Step 3: Add the fields, the version and the validation.** `payroll_micros ==
  payroll_positions * payroll_hours_per_position * hourly_wage_micros` with checked arithmetic, else
  `InvalidPayroll`. `appropriation_micros == visits_per_period * visit_cost_micros`, else
  `InvalidPrice`. A zero site id, zero positions, zero hours or zero visits is refused.
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Write the failing policy test** in `tests/national_game_policy.rs`: the shipped
  `defines.toml` parses, `policy.city_pd.positions == 3_529`, `visits_per_period == 1`, `visit_hours
  == 1`; a schema-7 file without `[city_pd]` is refused; a file whose `default_wage_micros_per_hour`
  is `30000000` is accepted by `national_economy::city_pd` (today it is refused at
  `city_pd.rs:104`).
- [ ] **Step 6: Implement the policy table and the capture.** In `city_pd.rs`: wage is
  `policy.default_wage`; visit cost is `visit_hours` times the wage; appropriation is
  `visits_per_period` times the visit cost; the budget cap rises by the appropriation, as today. The
  payroll site is the opening's actor with `function == PublicProvisioning`, local-government
  ownership, in county `26163`. Refuse with a named error when it is missing, when its
  `employee_persons < positions`, or when its provider grant is smaller than the payroll. Add to
  `defines.toml`:

```toml
[city_pd]
evidence_class = "Designed"
positions = 3529
positions_source = "City of Detroit, City Council Legislative Policy Division, budget analysis of 21 March 2025: Police Department, adopted positions, fiscal year 2025"
visits_per_period = 1
visit_hours = 1
```

- [ ] **Step 7: Tick validation.** `CityPdRegister::validate` also requires a
  `ProviderOperatingGrant` line from `public_account_id` to
  `AccountId::Site(payroll_site_account_id)` whose amount is at least `payroll_micros`. Add an
  inline test that a register whose grant is one micro-unit short is refused.
- [ ] **Step 8: Update fixtures and pins,** then run `mise run rust:test:q -- -p
  babylon-practice-contract -p babylon-tick -E 'test(city_pd) | test(state_opponent) |
  test(public_venue)'` and `mise run rust:test:q -- -p babylon-persistence -E 'test(city_pd) |
  test(policy) | test(catalog)'`. Expected: PASS. Then `mise run rust:check-no-docs`. Expected: no
  warnings.
- [ ] **Step 9: Commit** as `feat(state-opponent): separate the City PD's three numbers and record
  its payroll`.

### Task 2: Decision records

Spec section 8. Write the records the code will cite. They record the Director's rulings in the
Director's words (spec section 2) and mark every author's call as a call.

**Files:**
- Create: `ai/decisions/ADR301_county_review_session.yaml` (spec records 1 to 7 and 12)
- Create: `ai/decisions/ADR302_household_roster_and_counting.yaml` (record 8)
- Create: `ai/decisions/ADR303_county_review_dispositions.yaml` (records 9, 10 and 11)
- Create: `ai/decisions/ADR304_city_pd_payroll.yaml` (record 13)
- Create: `ai/decisions/ADR305_rule_of_thirds_anchoring_law.yaml` (record 15)
- Modify: `ai/decisions/index.yaml`

**Interfaces:**
- Produces: the ids `ADR301` (cited by the rule's attribution and allowance rows in Task 8),
  `ADR302`, `ADR303`, `ADR304`, `ADR305`.

- [ ] **Step 1: Read the format** in `ai/decisions/ADR299_wayne_relief_hearing.yaml`, `ADR291*.yaml`
  and `ADR300_amendment_am_no_imposed_functional_form.yaml`, and the index entries for them.
- [ ] **Step 2: Write the five records.** Status `accepted`, date `2026-11-19`. Each has an
  `authority` block that quotes the Director's ruling from spec section 2 word for word, a
  `decision` block with numbered rulings, a `calls` block listing each author's call with the spec
  section that holds it, `alternatives_rejected` from spec section 6, and `related`. ADR301 states
  the Article III reading of spec 7.5 and names the two open questions of spec section 12. ADR303
  gives the aid road's roll the disposition CHARTER and the graph payload the disposition BLOCKED on
  PER-44 and hypergraph-rs issue 2. ADR305 quotes both of the Director's directions on the rule of
  thirds from spec section 2. It states what binds this slice (the bands on the roster and the two
  opening checks) and what waits for the next (the shares of wealth). ADR302 records how the bands
  are sized and filled.
- [ ] **Step 3: Verify.** `mise run check:adr-catalog` prints `"status":"ok"`. `mise run
  check:governance-mass` prints `governance-mass: ok`. `PYTHONPATH=src mise exec -- uv run --frozen
  pre-commit run --files ai/decisions/ADR30[1-5]*.yaml ai/decisions/index.yaml` passes.
- [ ] **Step 4: Commit** as `docs(decisions): record the County Review rulings (ADR301 to ADR305)`.

### Task 3: Kernel: exact splits and the roster

Spec 7.2 and Appendix D.3. Pure code, no engine types.

**Files:**
- Create: `rust/crates/babylon-practice-contract/src/county_review.rs` (module root and re-exports)
- Create: `rust/crates/babylon-practice-contract/src/county_review/types.rs`, `split.rs`,
  `roster.rs`
- Modify: `rust/crates/babylon-practice-contract/src/lib.rs` (`mod county_review; pub use
  county_review::*;`)
- Test: `rust/crates/babylon-practice-contract/tests/county_review.rs` with
  `tests/county_review/support.rs`, `split.rs`, `roster.rs`

**Interfaces:**
- Produces, in `types.rs` (all `Serialize`, `Deserialize`, `deny_unknown_fields`; amounts with the
  decimal-string serde used in `state_opponent`):

```rust
pub const COUNTY_REVIEW_SCHEMA_VERSION: u32 = 1;
pub const COUNTY_REVIEW_MAX_ROWS: usize = 65_536;

pub enum PayMode { Wage, WorkingOwner, UnpaidFamily }
pub enum GroupKind { Ordinary, CollectiveResidence }

/// A household's band in the rule of thirds at the opening. Declared lowest first: an exact tie falls on the lower band.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Band { Bottom50, Next40, Next9, Top1 }

/// A position. `group` and `crew` index the config's tables. Rows sort by the fields in this order.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct PositionKey { pub group: u32, pub band: Band, pub crew: Option<u32>, pub at_work: u16, pub seeking: u16, pub units: u16 }

/// Who works in one band: county totals worked out from the roster.
pub struct BandCount {
    pub band: Band, pub households: u64,
    pub with_work: u64, pub seeking_only: u64, pub outside_labor_force: u64,   // households; the three add to `households`
    pub people_at_work: u64, pub people_seeking: u64, pub units: u64,           // sums of at_work, seeking and units times households
}

pub struct CountyReviewGroup {
    pub group_id: [u8; 32], pub label: String, pub kind: GroupKind,
    pub opening_households: u64, pub roll_units: u64,
    pub has_ownership_income: bool, pub receives_mutual_aid: bool,
}
pub struct CountyReviewCrew {
    pub crew_id: [u8; 32], pub group: u32, pub site_id: [u8; 32], pub unit_id: [u8; 32],
    pub workplace_label: String, pub pay_mode: PayMode,
}
pub struct CountyReviewConfig {
    pub schema_version: u32, pub campaign_id: [u8; 16], pub actor_id: u64, pub authority_id: [u8; 16],
    pub county: [u8; 5], pub administration_label: String,
    pub claimants_body_label: String, pub aid_body_label: String,
    pub public_account_id: [u8; 32],
    pub unit_price_micros: i128, pub going_wage_micros: i128,
    pub session_hours: u64, pub bring_hours: u64, pub first_session_period: u64,
    pub groups: Vec<CountyReviewGroup>,   // sorted by group_id, unique
    pub crews: Vec<CountyReviewCrew>,     // sorted by crew_id, unique
    pub content_digest: [u8; 32], pub policy_source_digest: [u8; 32],
}
pub struct RosterRow { pub key: PositionKey, pub households: u64, pub reached: u64 }
pub struct RosterGroup { pub households: u64, pub departed_units: u64 }   // one per config group, same order
pub struct Roster { pub period: u64, pub groups: Vec<RosterGroup>, pub rows: Vec<RosterRow> } // rows sorted by key, unique, households > 0

pub struct CrewPeriodFacts {
    pub crew: u32, pub accrued_wages_micros: i128,
    pub opening_at_work: u64, pub opening_seeking: u64,
    pub left_at_work: u64, pub left_seeking: u64, pub hires: u64, pub separations: u64,
    pub closing_at_work: u64, pub closing_seeking: u64,
}
pub struct GroupPeriodFacts {
    pub group: u32, pub taxed_wages_micros: i128, pub wage_tax_collected_micros: i128,
    pub ownership_income_micros: i128, pub support_income_micros: i128, pub aid_income_micros: i128,
    pub free_hours: u64, pub closing_households: u64,
}
pub struct CountyPeriodFacts {
    pub period: u64, pub crews: Vec<CrewPeriodFacts>, pub groups: Vec<GroupPeriodFacts>,
    pub cash_micros: i128, pub cash_floor_micros: i128, pub spending_limit_micros: i128, pub first_class_micros: i128,
}
pub enum CountyReviewError { /* one variant per refusal named in this plan, plus Arithmetic, Codec, SizeLimit, NonCanonical */ }
```

- Produces, in `split.rs`:

```rust
pub enum Ties { Withhold, InOrder }
pub struct Apportionment { pub shares: Vec<u64>, pub withheld: u64 }
pub fn apportion(total: u64, weights: &[u64], ties: Ties) -> Result<Apportionment, CountyReviewError>;
/// Splits `total` in the ratio `upper : lower`. The household left over goes to the larger remainder, and to `lower` on an exact tie.
pub fn ratio_split(total: u64, upper: u64, lower: u64) -> Result<(u64, u64), CountyReviewError>;
```

- Produces, in `roster.rs`:

```rust
pub struct OpeningCrew { pub crew: u32, pub at_work: u64, pub seeking: u64 }
/// One line of the opening placement, before bands are given.
pub struct PlacedRow { pub group: u32, pub crew: Option<u32>, pub at_work: u16, pub seeking: u16, pub units: u16, pub households: u64 }
pub fn opening_placement(config: &CountyReviewConfig, crews: &[OpeningCrew]) -> Result<Vec<PlacedRow>, CountyReviewError>;   // sorted, unique
pub fn validate_county_review_config(config: &CountyReviewConfig) -> Result<(), CountyReviewError>;
pub fn opening_roster(config: &CountyReviewConfig, crews: &[OpeningCrew], opening_reach: &[(u32, u64)]) -> Result<Roster, CountyReviewError>;
pub fn validate_roster(config: &CountyReviewConfig, roster: &Roster) -> Result<(), CountyReviewError>;
pub fn roll_forward(config: &CountyReviewConfig, roster: &Roster, facts: &CountyPeriodFacts) -> Result<Roster, CountyReviewError>;
/// The declared placement, or one of its other bounds (spec 7.2). Production code passes `Declared`.
pub enum Placement { Declared, HoldersFirst, HoldersLast }
pub fn roll_forward_with(config: &CountyReviewConfig, roster: &Roster, facts: &CountyPeriodFacts,
                         placement: Placement) -> Result<Roster, CountyReviewError>;
impl Roster {
    pub fn crew_at_work(&self, crew: u32) -> u64;   // sum of at_work * households over the crew's rows
    pub fn crew_seeking(&self, crew: u32) -> u64;
    pub fn group_units(&self, group: u32) -> u64;   // sum of units * households over the group's rows
    pub fn band_counts(&self) -> Vec<BandCount>;    // four entries, top first; with_work: at_work >= 1; seeking_only: at_work == 0 && seeking >= 1
}
```

**The algorithms** (Appendix D.3 is the source; this is the exact form).

`apportion`: require `total <= sum(weights)`, else `SplitExceedsWeights`. With `W = sum(weights)`,
part `i` gets `total * w_i / W` rounded down (in `u128`), and the remainder `total * w_i % W` is
kept. The units left over go one each to the largest remainders. If the cut falls inside a run of
equal remainders: `InOrder` gives them to the earlier indices; `Withhold` gives none of that run
anything and reports the units as `withheld`. `W == 0` returns all zeros.

`opening_placement`, for each ordinary group with `H` households and its crews `(E, S)`, `L = E +
S`, skipping crews with `L == 0`:

1. If `sum(L) < H`: each crew gets `E` households at `(crew, 1, 0, 0)` and `S` at `(crew, 0, 1, 1)`;
   the other `H - sum(L)` households are `(None, 0, 0, 0)`.
2. Otherwise: more crews than households is `MoreCrewsThanHouseholds`. Each crew gets one household
   plus its share of `H - crews` from `apportion(H - crews, [L - 1], Withhold)`. Withheld households
   are `(None, 0, 0, 0)`.
3. In a crew with `h` households: `q = E / h`, `r = E % h`. `h - r` households have `q` at work and
   `r` have `q + 1`. With `sq = S / h` and `sr = S % h`, every household has `sq` job-seekers, and
   the first `sr` households have one more, counting the households with `q` at work first. `units`
   equals the job-seekers placed.
4. The units placed in a group must equal its `roll_units`, else `RollMismatch`.

A collective-residence group has no rows. Its `RosterGroup.households` is 0.

`opening_roster` runs `opening_placement`, then gives every placed household a band, then places the
opening reach. The bands follow spec 7.2, rules 7 and 8, and Appendix D.3.

1. *Sizes.* `ratio_split(total, upper, lower)` gives `total * upper / (upper + lower)` and `total *
   lower / (upper + lower)`, each rounded down. If one household is left over it goes to the part
   with the larger remainder, and to `lower` on an exact tie. `O` is the households of the ordinary
   groups with `has_ownership_income`, and `N` the households of the other ordinary groups. The top
   1% needs the first part of `ratio_split(O, 1, 9)`. The next 40% needs the first part of
   `ratio_split(N, 4, 5)`.
2. *The top 1%* is taken from the owner groups' placed rows with `crew: None`. If those rows hold
   fewer households than it needs: `TopBandInLaborForce`. Otherwise `apportion(needed, [households],
   Withhold)` over those rows. The households taken are `Top1`. Every other owner household is
   `Next9`.
3. *The next 40%* is taken from the other groups' placed rows that are in the labor force (`crew` is
   `Some`). Rows with equal `at_work` form a level, whatever their job-seekers and units, and levels
   are ordered by more at work first. So the last level is the households that are only looking for
   work. A level that fits in what is still needed is taken whole. The first level that does not fit
   gives `apportion(still_needed, [households], Withhold)` over its rows, and the walk ends. If the
   levels run out first: `WageBandOutsideLaborForce`. The households taken are `Next40`, and each
   keeps its job-seekers and units: the next 40% can have unemployment too (the Director, 19
   November). Every other household of those groups is `Bottom50`.
4. Withheld households stay in the lower band, so a band can open a few households short. Under
   `Withhold` the order of the rows does not matter.
5. Opening reach `(group, n)` is placed last, on the group's roster rows, with `apportion(n,
   [households], Withhold)`; anything withheld is `OpeningReachNotPlaceable`.

`roll_forward`, for each crew in `facts.crews`: require `roster.crew_at_work == opening_at_work` and
`roster.crew_seeking == opening_seeking`, else `RosterEngineMismatch`. A household keeps its band in
every step. Then, in this order:

1. `left_at_work` people: repeatedly take households from the rows with the largest `at_work`; each
   becomes `(k - 1, s, u)`.
2. `left_seeking` people: the same on the largest `seeking`; each becomes `(k, s - 1, u)`.
3. `hires`: take households from rows with `seeking >= 1`, smallest `at_work` first; each becomes
   `(k + 1, s - 1, u)`.
4. `separations`: take households from rows with `at_work >= 1`, largest `at_work` first; each
   becomes `(k - 1, s + 1, u)`.

"Take `n` households from the candidate rows": if the candidates hold `n` or fewer, take them all
and continue with the next level. Otherwise `apportion(n, [households], InOrder)` with the candidate
rows ordered by `(units, seeking, at_work, band)` ascending. The level is found again after each
take: a household that has moved can be taken again at its new level. Inside a row that gives up `t`
of its households, `apportion(t, [households - reached, reached], InOrder)` says how many of them
are unreached and reached, and they keep that status in the row they join. After each crew, a row
with `at_work == 0 && seeking == 0` is re-keyed to `crew: None`, rows with equal keys are merged,
and empty rows are dropped. Then require the crew's sums to equal `closing_at_work` and
`closing_seeking`.

`HoldersFirst` and `HoldersLast` change one thing: among candidate rows at one level, rows with
`units >= 1` are taken before, or after, rows with none, instead of in proportion with them.
`roll_forward` is `roll_forward_with(.., Placement::Declared)`.

The facts hold one entry for every configured crew and every configured group, in the config's
order.

Then for each group: `closing_households` above the roster's count is `RosterEngineMismatch`. If it
is lower by `d`, take `d` households from the group's rows `(None, 0, 0, u)` with `apportion(d,
[households], InOrder)` in ascending `(units, band)`, add `u` times the households taken to
`departed_units`, and if those rows hold fewer than `d` return `HouseholdsBelowLaborHouseholds`.
Finally `period += 1`.

- [ ] **Step 1: Write the failing split tests** in `tests/county_review/split.rs`:

```rust
#[test]
fn equal_remainders_at_the_cut_are_withheld_or_go_in_order() {
    assert_eq!(apportion(5, &[2, 2, 2], Ties::Withhold).unwrap(), Apportionment { shares: vec![1, 1, 1], withheld: 2 });
    assert_eq!(apportion(5, &[2, 2, 2], Ties::InOrder).unwrap(), Apportionment { shares: vec![2, 2, 1], withheld: 0 });
    assert_eq!(apportion(3, &[1, 2, 3], Ties::Withhold).unwrap(), Apportionment { shares: vec![0, 1, 1], withheld: 1 });
    assert_eq!(apportion(3, &[1, 2, 3], Ties::InOrder).unwrap(), Apportionment { shares: vec![1, 1, 1], withheld: 0 });
}

#[test]
fn a_split_with_no_tie_adds_back_exactly() {
    assert_eq!(apportion(7, &[10, 20, 30], Ties::Withhold).unwrap(), Apportionment { shares: vec![1, 2, 4], withheld: 0 });
    assert_eq!(apportion(0, &[0, 0], Ties::Withhold).unwrap(), Apportionment { shares: vec![0, 0], withheld: 0 });
    assert_eq!(apportion(4, &[1, 2], Ties::InOrder), Err(CountyReviewError::SplitExceedsWeights));
}
```

- [ ] **Step 2: Run them.** `mise run rust:test:q -- -p babylon-practice-contract -E
  'binary(county_review)'`. Expected: compile failure.
- [ ] **Step 3: Implement `types.rs` and `split.rs`.** Run again. Expected: PASS.
- [ ] **Step 4: Write the failing roster tests** in `tests/county_review/roster.rs`. `support.rs`
  gives `config(groups: &[(u64 /*households*/, u64 /*roll units*/, bool /*has ownership income*/)],
  crews: &[u32 /*group*/])` with price 280_000_000, wage 24_000_000, 2 and 2 hours, first session 1;
  `placed(&[PlacedRow]) -> Vec<((u32, Option<u32>, u16, u16, u16), u64)>`; `rows(&Roster) ->
  Vec<((u32, Band, Option<u32>, u16, u16, u16), u64, u64)>`; and the short names `T1`, `N9`, `N40`
  and `B50` for `Band::Top1`, `Next9`, `Next40` and `Bottom50`.

The placement, before bands:

```rust
#[test]
fn fewer_people_than_households_gives_each_person_a_household() {
    let c = config(&[(10, 2, false)], &[0]);
    let p = opening_placement(&c, &[OpeningCrew { crew: 0, at_work: 3, seeking: 2 }]).unwrap();
    assert_eq!(placed(&p), vec![((0, None, 0, 0, 0), 5), ((0, Some(0), 0, 1, 1), 2), ((0, Some(0), 1, 0, 0), 3)]);
}

#[test]
fn more_people_than_households_spreads_work_evenly_and_seekers_to_the_fewest_at_work() {
    let c = config(&[(4, 3, false)], &[0]);
    let p = opening_placement(&c, &[OpeningCrew { crew: 0, at_work: 6, seeking: 3 }]).unwrap();
    assert_eq!(placed(&p), vec![((0, Some(0), 1, 1, 1), 2), ((0, Some(0), 2, 0, 0), 1), ((0, Some(0), 2, 1, 1), 1)]);
}

#[test]
fn two_crews_with_equal_claims_leave_the_tied_household_with_no_crew() {
    let c = config(&[(5, 2, false)], &[0, 0]);
    let open = [OpeningCrew { crew: 0, at_work: 4, seeking: 0 }, OpeningCrew { crew: 1, at_work: 2, seeking: 2 }];
    let p = opening_placement(&c, &open).unwrap();
    assert_eq!(placed(&p), vec![((0, None, 0, 0, 0), 1), ((0, Some(0), 2, 0, 0), 2), ((0, Some(1), 1, 1, 1), 2)]);
}

#[test]
fn more_seekers_than_households_gives_a_household_two_or_three_units() {
    let c = config(&[(2, 5, false)], &[0]);
    let p = opening_placement(&c, &[OpeningCrew { crew: 0, at_work: 1, seeking: 5 }]).unwrap();
    assert_eq!(placed(&p), vec![((0, Some(0), 0, 3, 3), 1), ((0, Some(0), 1, 2, 2), 1)]);
}

#[test]
fn more_crews_than_households_is_refused() {
    let c = config(&[(1, 0, false)], &[0, 0]);
    let open = [OpeningCrew { crew: 0, at_work: 1, seeking: 0 }, OpeningCrew { crew: 1, at_work: 1, seeking: 0 }];
    assert_eq!(opening_placement(&c, &open), Err(CountyReviewError::MoreCrewsThanHouseholds));
}
```

The bands:

```rust
#[test]
fn the_next_forty_are_taken_by_the_number_at_work_and_bring_their_seekers() {
    let c = config(&[(9, 2, false)], &[0]);          // the next 40% needs 4 of the 9
    let r = opening_roster(&c, &[OpeningCrew { crew: 0, at_work: 10, seeking: 2 }], &[]).unwrap();
    // the household with 2 at work first; then 3 of the 8 with 1 at work, in proportion 6 : 2, so one of them has a job-seeker and a unit
    assert_eq!(rows(&r), vec![((0, B50, Some(0), 1, 0, 0), 4, 0), ((0, B50, Some(0), 1, 1, 1), 1, 0),
                              ((0, N40, Some(0), 1, 0, 0), 2, 0), ((0, N40, Some(0), 1, 1, 1), 1, 0), ((0, N40, Some(0), 2, 0, 0), 1, 0)]);
}

#[test]
fn a_unit_does_not_keep_a_household_out_of_the_next_forty() {
    let c = config(&[(4, 3, false)], &[0]);          // the next 40% needs 2 of the 4: the two households with 2 at work
    let r = opening_roster(&c, &[OpeningCrew { crew: 0, at_work: 6, seeking: 3 }], &[]).unwrap();
    assert_eq!(rows(&r), vec![((0, B50, Some(0), 1, 1, 1), 2, 0), ((0, N40, Some(0), 2, 0, 0), 1, 0), ((0, N40, Some(0), 2, 1, 1), 1, 0)]);
}

#[test]
fn households_only_looking_for_work_come_last_and_those_outside_the_labor_force_never() {
    let c = config(&[(9, 3, false)], &[0]);          // the next 40% needs 4: 2 at work, then 2 of the 3 that are only looking
    let r = opening_roster(&c, &[OpeningCrew { crew: 0, at_work: 2, seeking: 3 }], &[]).unwrap();
    assert_eq!(rows(&r), vec![((0, B50, None, 0, 0, 0), 4, 0), ((0, B50, Some(0), 0, 1, 1), 1, 0),
                              ((0, N40, Some(0), 0, 1, 1), 2, 0), ((0, N40, Some(0), 1, 0, 0), 2, 0)]);
}

#[test]
fn the_top_hundredth_has_nobody_in_the_labor_force() {
    let c = config(&[(20, 2, true)], &[0]);          // owners: the top 1% needs 2 of the 20
    let r = opening_roster(&c, &[OpeningCrew { crew: 0, at_work: 5, seeking: 2 }], &[]).unwrap();
    assert_eq!(rows(&r), vec![((0, N9, None, 0, 0, 0), 11, 0), ((0, N9, Some(0), 0, 1, 1), 2, 0),
                              ((0, N9, Some(0), 1, 0, 0), 5, 0), ((0, T1, None, 0, 0, 0), 2, 0)]);
}

#[test]
fn an_exact_tie_at_a_bands_line_stays_in_the_lower_band() {
    let c = config(&[(16, 0, false)], &[0, 0]);      // the next 40% needs 7; two equal crews tie for the seventh
    let open = [OpeningCrew { crew: 0, at_work: 8, seeking: 0 }, OpeningCrew { crew: 1, at_work: 8, seeking: 0 }];
    let r = opening_roster(&c, &open, &[]).unwrap();
    assert_eq!(rows(&r), vec![((0, B50, Some(0), 1, 0, 0), 5, 0), ((0, B50, Some(1), 1, 0, 0), 5, 0),
                              ((0, N40, Some(0), 1, 0, 0), 3, 0), ((0, N40, Some(1), 1, 0, 0), 3, 0)]);
}

#[test]
fn an_opening_that_cannot_obey_the_law_is_refused_by_name() {
    let owners = config(&[(10, 0, true)], &[0]);     // every owner household has someone at work
    assert_eq!(opening_roster(&owners, &[OpeningCrew { crew: 0, at_work: 10, seeking: 0 }], &[]),
               Err(CountyReviewError::TopBandInLaborForce));
    let others = config(&[(9, 0, false)], &[0]);     // the next 40% needs 4 households in the labor force; there are 2
    assert_eq!(opening_roster(&others, &[OpeningCrew { crew: 0, at_work: 2, seeking: 0 }], &[]),
               Err(CountyReviewError::WageBandOutsideLaborForce));
}

#[test]
fn ratio_split_gives_the_odd_household_to_the_larger_remainder() {
    assert_eq!(ratio_split(70_060, 1, 9).unwrap(), (7_006, 63_054));
    assert_eq!(ratio_split(630_523, 4, 5).unwrap(), (280_232, 350_291));
    assert_eq!(ratio_split(15, 1, 9).unwrap(), (1, 14));      // an exact tie goes to the lower part
    assert_eq!(ratio_split(4, 4, 5).unwrap(), (2, 2));
}
```

Roll-forward tests start from the banded roster of the second band test above (4 households, `E =
6`, `S = 3`): `(B50, 1, 1, 1) x 2`, `(N40, 2, 0, 0) x 1`, `(N40, 2, 1, 1) x 1`. `facts(crew_changes,
households)` in `support.rs` fills the opening and closing sums from the roster and the changes.
`after(changes)` rolls that roster forward and returns `rows`.

```rust
#[test]
fn a_hire_takes_a_seeker_from_the_households_with_the_fewest_at_work() {
    assert_eq!(after(hires(1)), vec![((0, B50, Some(0), 1, 1, 1), 1, 0), ((0, B50, Some(0), 2, 0, 1), 1, 0),
                                      ((0, N40, Some(0), 2, 0, 0), 1, 0), ((0, N40, Some(0), 2, 1, 1), 1, 0)]);
}

#[test]
fn a_layoff_takes_from_the_most_at_work_and_a_tie_goes_to_fewer_units() {
    // separations = 1: (2, 0, 0) and (2, 1, 1) tie; the one with no unit goes
    assert_eq!(after(separations(1)), vec![((0, B50, Some(0), 1, 1, 1), 2, 0), ((0, N40, Some(0), 1, 1, 0), 1, 0), ((0, N40, Some(0), 2, 1, 1), 1, 0)]);
    // separations = 2: both go
    assert_eq!(after(separations(2)), vec![((0, B50, Some(0), 1, 1, 1), 2, 0), ((0, N40, Some(0), 1, 1, 0), 1, 0), ((0, N40, Some(0), 1, 2, 1), 1, 0)]);
}

#[test]
fn a_seeker_who_leaves_the_labor_force_keeps_the_households_unit() {
    // left_seeking = 1: weights 2 and 1; the larger remainder is the (B50, 1, 1, 1) row
    assert_eq!(after(left_seeking(1)), vec![((0, B50, Some(0), 1, 0, 1), 1, 0), ((0, B50, Some(0), 1, 1, 1), 1, 0),
                                             ((0, N40, Some(0), 2, 0, 0), 1, 0), ((0, N40, Some(0), 2, 1, 1), 1, 0)]);
}

#[test]
fn a_household_keeps_its_band_and_an_exact_tie_between_bands_falls_on_the_lower() {
    // a roster written by hand: (B50, Some(0), 1, 0, 0) x 3 and (N40, Some(0), 1, 0, 0) x 3; separations = 1
    // the two rows tie for it, and the lower band gives it
    assert_eq!(rows(&rolled), vec![((0, B50, Some(0), 0, 1, 0), 1, 0), ((0, B50, Some(0), 1, 0, 0), 2, 0), ((0, N40, Some(0), 1, 0, 0), 3, 0)]);
}

#[test]
fn a_household_left_with_nobody_in_the_labor_force_has_no_crew_and_can_leave_with_its_unit() {
    // 9 households, 2 units, E = 4, S = 2 opens as (B50, None, 0, 0, 0) x 3, (B50, Some(0), 0, 1, 1) x 2, (N40, Some(0), 1, 0, 0) x 4
    // left_seeking = 1 makes one (0, 1, 1) household (B50, None, 0, 0, 1)
    // closing_households = 8: one household leaves, in proportion 3 : 1, so it is one with no unit, and departed_units stays 0
    // closing_households = 5: all four leave, and departed_units becomes 1
    // closing_households = 4: HouseholdsBelowLaborHouseholds
}

#[test]
fn a_moved_household_stays_reached_or_unreached() {
    // (B50, 1, 1, 1) x 2 with 1 reached, hires = 1: the unreached household moves
    // afterwards (B50, 1, 1, 1) x 1 has 1 reached and (B50, 2, 0, 1) x 1 has none
}

#[test]
fn sums_that_do_not_match_the_engine_are_refused() {
    // opening_at_work = 7 against a roster that holds 6
    assert_eq!(roll_forward(&c, &r, &bad), Err(CountyReviewError::RosterEngineMismatch));
}
```

Write the commented tests in full with the same helpers, one assertion for each commented line.

- [ ] **Step 5: Run them.** Expected: FAIL (missing functions).
- [ ] **Step 6: Implement `roster.rs`.** `validate_roster` checks: rows sorted and unique, no empty
  row, `reached <= households`, every index in range, a row with `crew: None` has `at_work == 0 &&
  seeking == 0`, a `Top1` row has `crew: None`, a row's crew belongs to its group, and each ordinary
  group's rows sum to its `RosterGroup.households`.
- [ ] **Step 7: Add a property test** `rolling_forward_keeps_every_total` in `roster.rs` tests: with
  a small xorshift generator written in the test file, build 200 random openings that the law
  accepts (1 to 3 groups, some with ownership income, 1 to 4 crews, up to 40 households; draw again
  when `opening_roster` refuses) and apply 6 random periods of departures and hires or layoffs that
  the sums allow. After every period assert: each group's households, each crew's two sums,
  `sum(reached) ` unchanged, `group_units + departed_units == roll units placed at the opening`,
  each band's households unchanged except by the households that left, and no `Top1` row with a
  crew.
- [ ] **Step 8: Run.** Expected: PASS. Then the scoped gate (Global Constraints).
- [ ] **Step 9: Commit** as `feat(county-review): exact splits and the household roster`.

### Task 4: Kernel: places, the list and the session

Spec 7.1, 7.4, 7.5, 7.6 and 7.13.

**Files:**
- Create: `rust/crates/babylon-practice-contract/src/county_review/place.rs`, `session.rs`
- Modify: `rust/crates/babylon-practice-contract/src/county_review.rs`
- Test: `rust/crates/babylon-practice-contract/tests/county_review/session.rs`

**Interfaces:**
- Consumes: Task 3's types, `apportion`, `Roster`.
- Produces:

```rust
/// An exact, non-negative fraction. Ordered by cross-multiplication in 256 bits.
pub struct Place { /* numerator: u128, denominator: u128 (never zero) */ }
impl Place { pub const ZERO: Place; pub fn is_zero(&self) -> bool; }
pub fn place(at_work: u16, crew_wages_micros: i128, crew_at_work: u64,
             group_tax_collected_micros: i128, group_taxed_wages_micros: i128) -> Result<Place, CountyReviewError>;

pub enum ContactOutcome { Reached, NobodyLeft, NoSuchPosition }
pub struct SessionRow {
    pub key: PositionKey, pub rank: u32, pub households: u64, pub reached: u64,
    pub units_listed: u64, pub units_paid: u64, pub units_unpaid: u64,
    pub asked: u64, pub asked_paid: u64, pub asked_no_place: u64, pub asked_no_time: u64,
    pub losers: u64, pub losers_reached: u64,
    pub came_from_roll: u64, pub roll_no_time: u64, pub nothing_at_stake: u64, pub not_worth_time: u64,
    pub brought: u64, pub hours_in_room: u64, pub hours_bringing: u64,
}
pub struct SupportLine { pub group: u32, pub units: u64, pub amount_micros: i128 }
pub struct HourCharge { pub group: u32, pub hours: u64 }
pub struct SessionRecord {
    pub period: u64, pub cash_micros: i128, pub spending_limit_micros: i128, pub first_class_micros: i128,
    pub roll_total_micros: i128, pub relief_micros: i128,
    pub collective_lines: Vec<SupportLine>, pub household_units_listed: u64, pub household_units_payable: u64,
    pub kept_back_units: u64, pub contact: Option<(PositionKey, ContactOutcome)>,
    pub rows: Vec<SessionRow>, pub lines: Vec<SupportLine>,
    pub claimants_roll_households: u64, pub aid_roll_households: u64,
}
pub struct SessionOutcome { pub record: SessionRecord, pub roster: Roster, pub hour_charges: Vec<HourCharge> }
pub fn hold_session(config: &CountyReviewConfig, roster: &Roster, facts: &CountyPeriodFacts,
                    contact: Option<PositionKey>) -> Result<SessionOutcome, CountyReviewError>;
```

`SessionOutcome.roster` carries the new reach (the contact and the households brought). It is not
rolled forward. `rank` is 1 for the highest place; equal places share a rank; rows with place zero
share the last rank.

**The algorithm of `hold_session`.**

1. *Check.* Each crew's sums in the roster equal `opening_at_work` and `opening_seeking` in the
   facts, else `RosterEngineMismatch`.
2. *The contact.* A key with no row: `NoSuchPosition`. A row whose households are all reached:
   `NobodyLeft`. Otherwise `reached += 1` and `Reached`.
3. *The money.* `listed` is the sum of `units * households` over all rows. Each collective-residence
   group adds `roll_units`. `roll_total` is all of those times the unit price. `budget =
   min(spending_limit, cash - cash_floor)`, not below zero. `relief = min(max(budget - first_class,
   0), roll_total)`. If `relief == roll_total`, every collective line is whole and `payable =
   listed`. Otherwise each collective group's line is `relief * its_total / roll_total` rounded down
   to a micro-unit, and `payable` is what is left divided by the unit price, rounded down.
4. *Places.* A row's place is `place(key.at_work, wages of its crew, roster.crew_at_work(crew), tax
   collected from its group, taxed wages of its group)`. No crew means zero. `place` returns zero
   when any factor is zero, reduces `wages / at_work` and `collected / taxed` by their greatest
   common divisors, and returns `Arithmetic` if a product still overflows `u128`.
5. *Who asks.* The floor is `session_hours * going_wage_micros`. For a row with `units == 0` and
   `reached > 0`: if the unit price is below the floor, all its reached households are
   `not_worth_time`. Otherwise they want to ask. Each group's hours start at `free_hours`. Take the
   group's asking rows by place, highest first; rows at one place form a pool; the pool may ask with
   `min(pool, hours / session_hours)` households, shared with `apportion(.., Withhold)`; the hours
   are set aside. The others are `asked_no_time`.
6. *The list.* Group rows by place, highest first. In each class, first the rows that hold units: if
   `payable` covers the class's `units_listed`, all are paid; otherwise `apportion(payable,
   [units_listed], Withhold)`, the withheld units add to `kept_back_units`, and `payable` becomes
   zero. Then the rows that asked, in the same way on `asked`.
7. *Askers.* `asked_no_place = asked - asked_paid`, and their hours are given back to the group.
   Paid askers come.
8. *Losers.* A row with `units_unpaid > 0` has `losers = ceil(units_unpaid / units)` households.
   `apportion(losers, [households - reached, reached], InOrder)` gives `losers_reached`. A reached
   loser comes if what it loses is at least the floor and its group has `session_hours` left. Hours
   go by place, highest first, pooled at one place with `Withhold`. If `units_unpaid % units != 0`
   the household that loses fewer than all its units is an unreached one when the row has an
   unreached loser. Reached households of a row with units that lose nothing are `nothing_at_stake`.
9. *The spread.* A row brings `min(came, households - reached)` households, where `came = asked_paid
   + came_from_roll`, if its group has `bring_hours` for each; hours go as in step 8. `reached`
   rises by `brought`.
10. *Lines.* A group's units are the sum of `units_paid + asked_paid` over its rows. A group with no
    unit has no line.
11. *Charges.* For each group, `session_hours * came + bring_hours * brought`, omitted when zero.

Every reached household of a row is counted once: `reached == asked_paid + asked_no_place +
asked_no_time + came_from_roll + roll_no_time + nothing_at_stake + not_worth_time`, with `reached`
taken after step 2.

- [ ] **Step 1: Write the failing tests** in `tests/county_review/session.rs`. `support.rs` gains
  `world()`: the worked example of spec 7.7. Group 0 has crews 0 and 1; group 1 has crew 2. Rows,
  with the band after the group: `A = (0, B50, Some(0), 1, 1, 1) x 2`, `D = (0, N40, Some(0), 1, 0,
  0) x 1`, `B = (0, B50, Some(1), 1, 1, 1) x 1`, `C = (1, B50, Some(2), 0, 1, 1) x 2`. The world is
  built by hand, not by `opening_roster`. Crew 0 was paid 11_520_000_000 with 3 at work; crew 1 was
  paid 1_920_000_000 with 1 at work; crew 2 was paid nothing with nobody at work. Group 0: taxed
  wages 13_440_000_000, collected 2_016_000_000, 100 free hours. Group 1: nothing taxed, 100 free
  hours. Cash 10_000_000_000, limit 10_000_000_000, floor 0, first class 0.
  `balanced(&SessionRecord)` asserts every identity of spec 7.13 that the record can show.

```rust
#[test]
fn the_worked_example_of_the_design() {
    let (c, mut r, f) = world();
    reach(&mut r, D, 1);
    let out = hold_session(&c, &r, &f, None).unwrap();
    let rec = &out.record;
    assert_eq!(rec.household_units_payable, 5);
    assert_eq!(row(rec, A).units_paid, 2);
    assert_eq!((row(rec, D).asked, row(rec, D).asked_paid), (1, 1));
    assert_eq!(row(rec, B).units_paid, 1);
    assert_eq!((row(rec, C).units_paid, row(rec, C).units_unpaid, row(rec, C).losers, row(rec, C).losers_reached), (1, 1, 1, 0));
    assert_eq!((row(rec, A).rank, row(rec, D).rank, row(rec, B).rank, row(rec, C).rank), (1, 1, 2, 3));
    assert_eq!(rec.lines, vec![SupportLine { group: 0, units: 4, amount_micros: 1_120_000_000 },
                               SupportLine { group: 1, units: 1, amount_micros: 280_000_000 }]);
    assert_eq!(out.hour_charges, vec![HourCharge { group: 0, hours: 2 }]);
    assert_eq!((rec.aid_roll_households, rec.claimants_roll_households, rec.kept_back_units), (1, 0, 0));
    balanced(rec);
}
```

The roll holds 5 units and `world()` has cash for all of them. `short(&mut f, n)` in `support.rs`
sets the cash so that `household_units_payable` is `n`. Write these further tests, each ending in
`balanced`. They are also the sever tests of spec section 9: say in a comment on each which link it
cuts.

- `ties_keep_the_holder`: with the roll whole and only `A` and `D` in group 0 at one place, and no
  lower holder, `D` asks and finds no place: `asked_no_place == 1`, no hour is charged.
- `a_household_with_no_wage_takes_nothing`: reach one household of a row `(1, B50, None, 0, 0, 0)`;
  it asks, `asked_no_place == 1`.
- `a_short_county_pays_from_the_top`: payable 3 with nobody reached: `A` 2 paid, `B` 1 paid, `C` 0
  paid, and `lines` has no entry for group 1.
- `no_money_for_relief_removes_every_line`: cash 0: `relief_micros == 0`, `lines` empty, every unit
  unpaid, a reached household of `A` comes from the roll.
- `an_exact_tie_between_positions_is_paid_to_nobody`: two rows at one place in different crews, one
  unit each, payable covers one: both unpaid, `kept_back_units == 1`.
- `a_reached_household_whose_unit_is_unpaid_comes_and_brings_one`: reach one of `C`'s two households
  and make both of `C`'s units unpaid: `came_from_roll == 1`, `brought == 1`, hours `2 + 2` for
  group 1, and the returned roster has `C` fully reached.
- `one_reached_household_among_many_is_not_the_loser`: `C` with 2 households, 1 reached, 1 unit
  unpaid: `losers_reached == 0`, `nothing_at_stake == 1`.
- `no_free_hours_records_no_time`: group 0 with 0 free hours: `D` is `asked_no_time`, and the list
  is as if nobody asked.
- `a_unit_below_the_floor_keeps_everyone_home`: unit price 40_000_000: `not_worth_time` for `D`, and
  for a reached loser.
- `a_crew_with_nobody_at_work_or_a_group_with_no_taxed_wages_stands_at_nothing`: no panic, rank is
  the last.
- `the_contact_lands_before_the_list`: `contact = Some(D)` with `D` unreached gives `Reached` and
  `asked_paid == 1`; a key with no row gives `NoSuchPosition`; a fully reached row gives
  `NobodyLeft`.
- `swapping_the_pay_of_two_crews_reverses_who_loses`: swap the wages of crews 0 and 1; group totals
  are unchanged; with payable 4 the unpaid holder is now in `A`.
- `a_group_average_would_give_another_answer`: recompute with every row of group 0 given one shared
  place; assert the record differs from the real one. This is the mutation Amendment AM asks for.
- `renaming_crews_changes_no_count`: build the same world with crews 0 and 1 exchanged in the
  config; map the keys back; every row is equal.
- `splitting_a_crew_that_pays_alike_moves_at_most_one_unit`: split crew 0 into two crews with wages
  and people in proportion; summed over the two, every count differs by at most 1.
- `two_units_are_lost_a_household_at_a_time`: a row with nobody at work, 2 job-seekers and 2 units,
  `x 2`, with 3 units unpaid has `losers == 2`.
- `the_band_changes_no_outcome`: give `D` the band `B50`, and then give every row the band `N9`;
  after mapping the keys back, every count of the record is the same each time. No rule of the
  session reads a band.

- [ ] **Step 2: Run them.** Expected: compile failure.
- [ ] **Step 3: Implement `place.rs`.** `Ord` multiplies in 256 bits with two `u128` limbs. Test
  `place(1, 11_520_000_000, 3, 2_016_000_000, 13_440_000_000)` equals `place(2, 576_000_000, 1, 1,
  2)` and is above `place(1, 1_920_000_000, 1, 2_016_000_000, 13_440_000_000)`.
- [ ] **Step 4: Implement `session.rs`.** One function for each numbered step.
- [ ] **Step 5: Run.** Expected: PASS. Then the scoped gate (Global Constraints).
- [ ] **Step 6: Add a property test** `every_session_balances`: 300 random small worlds from the
  generator of Task 3, random reach and random cash; assert `balanced`, `sum(lines) +
  sum(collective_lines) <= relief_micros`, and that no hour charge exceeds its group's `free_hours`.
- [ ] **Step 7: Commit** as `feat(county-review): the county's list and the session`.

### Task 5: Kernel: preview, projection and codec

Spec 7.10, 7.11 and 7.12.

**Files:**
- Create: `rust/crates/babylon-practice-contract/src/county_review/preview.rs`, `projection.rs`,
  `codec.rs`
- Modify: `rust/crates/babylon-practice-contract/src/county_review.rs`
- Test: `rust/crates/babylon-practice-contract/tests/county_review/projection.rs`, `codec.rs`

**Interfaces:**
- Consumes: Tasks 3 and 4.
- Produces:

```rust
pub struct CountyReviewState {
    pub schema_version: u32, pub roster: Roster,
    pub last_facts: Option<CountyPeriodFacts>, pub last_session: Option<SessionRecord>,
}
pub fn validate_county_review_state(config: &CountyReviewConfig, state: &CountyReviewState) -> Result<(), CountyReviewError>;
pub fn encode_county_review_config(c: &CountyReviewConfig) -> Result<Vec<u8>, CountyReviewError>;   // "babylon.county-review-config.v1"
pub fn decode_county_review_config(bytes: &[u8]) -> Result<CountyReviewConfig, CountyReviewError>;
pub fn encode_county_review_state(s: &CountyReviewState) -> Result<Vec<u8>, CountyReviewError>;     // "babylon.county-review-state.v1"
pub fn decode_county_review_state(bytes: &[u8]) -> Result<CountyReviewState, CountyReviewError>;
pub fn county_review_config_digest(c: &CountyReviewConfig) -> Result<[u8; 32], CountyReviewError>;

pub struct ContactPreview {
    pub key: PositionKey, pub basis_period: u64, pub outcome: ContactOutcome,
    pub asks: bool, pub place_open: bool, pub taken_from: Vec<PositionKey>, pub then_at_stake: Vec<PositionKey>,
}
pub fn preview_contact(config: &CountyReviewConfig, state: &CountyReviewState, key: PositionKey)
    -> Result<Option<ContactPreview>, CountyReviewError>;   // None before any close has been seen

pub enum LedgerLineKind { PublicWorkplace, CityPdPayroll, CityPdVisits, HouseholdSupport, CollectiveResidence }
pub struct LedgerLine { pub kind: LedgerLineKind, pub label: String, pub amount_micros: i128, pub first_class: bool }
pub struct LedgerInput {
    pub cash_micros: i128, pub spending_limit_micros: i128,
    pub lines: Vec<LedgerLine>,                       // the engine's lines in pay order, before the payroll is named
    pub city_pd_payroll: Option<(String /* workplace label */, u64 /* positions */, i128 /* payroll */)>,
}
pub struct PositionEarned {
    pub households: u64, pub reached: u64,
    pub wage_micros_per_household: i128, pub wage_tax_micros_per_household: i128, pub stake_micros: i128,
    pub group_ownership_income_micros: i128, pub group_support_income_micros: i128, pub group_aid_income_micros: i128,
    pub asked: u64, pub asked_no_place: u64, pub asked_no_time: u64,
    pub roll_no_time: u64, pub nothing_at_stake: u64, pub not_worth_time: u64, pub brought: u64,
}
pub struct PositionView {
    pub key: PositionKey, pub group_label: String, pub workplace_label: Option<String>, pub pay_mode: Option<PayMode>,
    pub rank: Option<u32>, pub has_wages: bool, pub has_ownership_income: bool, pub has_support: bool, pub has_mutual_aid: bool,
    pub units_listed: u64, pub units_paid: u64, pub units_unpaid: u64, pub asked_paid: u64, pub came_from_roll: u64,
    pub contacted: bool, pub earned: Option<PositionEarned>,
}
pub struct CountyReviewProjection {
    pub county: [u8; 5], pub administration_label: String, pub claimants_body_label: String, pub aid_body_label: String,
    pub roster_period: u64, pub first_session_period: u64, pub session_period: Option<u64>,
    pub unit_price_micros: i128, pub cash_micros: i128, pub spending_limit_micros: i128,
    pub ledger: Vec<LedgerLine>, pub first_class_micros: i128,
    pub relief_micros: Option<i128>, pub household_units_payable: Option<u64>, pub kept_back_units: Option<u64>,
    pub roll: Vec<(String, u64)>,                     // group label, units on the roll
    pub bands: Vec<BandCount>,                        // who works in each band: four entries, top first; public
    pub claimants_roll_households: Option<u64>, pub aid_roll_households: Option<u64>,
    pub contact: Option<(PositionKey, ContactOutcome)>,
    pub positions: Vec<PositionView>,                 // in the order of the list, then by key
}
pub fn project(config: &CountyReviewConfig, state: &CountyReviewState, ledger: &LedgerInput,
               contacted: &[PositionKey]) -> Result<CountyReviewProjection, CountyReviewError>;
```

`project` names the City PD's payroll: the workplace line with that label is reduced by the payroll,
and a `CityPdPayroll` line of the payroll follows it; the agency line is `CityPdVisits`. A position
is `contacted` when `contacted` holds its key. Wage and wage tax "per household" are rounded down to
a micro-unit for display. They are never used to rank. `preview_contact` runs `hold_session` twice,
without and with the contact, on `state.roster` and on a copy of `state.last_facts` whose crews'
`opening_at_work` and `opening_seeking` are set to `state.roster.crew_at_work(crew)` and
`state.roster.crew_seeking(crew)`. The stored roster has already been rolled forward to the next
opening, so the last close's own opening counts no longer match it, and `hold_session`'s first check
would refuse every preview after a period with a hire, a separation or a departure. The wages,
taxes, cash and hours stay those of the last close, and `basis_period` is its period. It compares:
`place_open` is whether the contacted row's `asked_paid` rose; `taken_from` lists rows whose
`units_unpaid` rose; `then_at_stake` lists rows whose `losers` rose. It reads nothing earned.
`project` fills `bands` from `state.roster.band_counts()`. They are county totals and are shown
whether or not the player has contacted anyone.

- [ ] **Step 1: Write the failing tests.** In `projection.rs`, on `world()` after a session with `D`
  reached and contacted:

```rust
#[test]
fn amounts_are_shown_only_for_a_contacted_position() {
    let p = project(&c, &state, &ledger(), &[D]).unwrap();
    assert!(view(&p, D).earned.is_some() && view(&p, D).contacted);
    for key in [A, B, C] { assert!(view(&p, key).earned.is_none() && !view(&p, key).contacted); }
    assert_eq!((view(&p, C).units_listed, view(&p, C).units_unpaid), (2, 1));   // the list is public
    assert_eq!(view(&p, D).earned.as_ref().unwrap().wage_tax_micros_per_household, 576_000_000);
}

#[test]
fn the_ledger_names_the_city_pd_payroll_inside_the_workplace_grant() {
    let input = LedgerInput { lines: vec![workplace("County public workplace", 20_000_000_000_000), agency(24_000_000)],
        city_pd_payroll: Some(("County public workplace".into(), 3_529, 13_551_360_000_000)), ..ledger() };
    let p = project(&c, &state, &input, &[]).unwrap();
    assert_eq!(amounts(&p.ledger), vec![(LedgerLineKind::PublicWorkplace, 6_448_640_000_000),
        (LedgerLineKind::CityPdPayroll, 13_551_360_000_000), (LedgerLineKind::CityPdVisits, 24_000_000)]);
    assert_eq!(p.first_class_micros, 20_000_024_000_000);
}

#[test]
fn the_preview_reads_only_the_public_record() {
    let pv = preview_contact(&c, &state_before_any_contact, D).unwrap().unwrap();
    assert_eq!((pv.outcome, pv.asks, pv.place_open), (ContactOutcome::Reached, true, true));
    assert_eq!(pv.taken_from, vec![C]);
    assert_eq!(preview_contact(&c, &state_with_no_close_yet, D).unwrap(), None);
}
```

Also in `projection.rs`:

```rust
#[test]
fn who_works_in_each_band_is_a_public_county_total() {
    let p = project(&c, &state, &ledger(), &[]).unwrap();
    let got: Vec<_> = p.bands.iter().map(|b| (b.band, b.households, b.with_work, b.seeking_only, b.outside_labor_force,
                                              b.people_at_work, b.people_seeking, b.units)).collect();
    assert_eq!(got, vec![(Band::Top1, 0, 0, 0, 0, 0, 0, 0), (Band::Next9, 0, 0, 0, 0, 0, 0, 0),
                         (Band::Next40, 1, 1, 0, 0, 1, 0, 0), (Band::Bottom50, 5, 3, 2, 0, 3, 5, 5)]);
}
```

Also in `projection.rs`, `the_preview_after_a_roll_forward_with_hires_still_answers`: on `world()`
after a session and a `roll_forward` in which one crew hires one person, `preview_contact` returns
`Some(..)` (not `RosterEngineMismatch`) and its `basis_period` is the session's period.

Every type in this task's Interfaces except `LedgerInput` derives `Debug, Clone, PartialEq, Eq,
Serialize, Deserialize`, and every struct has `#[serde(deny_unknown_fields)]`, because
`OrganizerSnapshot` and `OrganizerPreview`, which hold `CountyReviewProjection` and `ContactPreview`
from Task 9 on, derive all six and deny unknown fields. Money fields serialize through
`super::decimal`, as Task 3's do. The workspace denies `unwrap` in tests: where a sketch here says
`unwrap`, write `expect` with a reason.

In `codec.rs`: a state survives `decode(encode(state))`; a byte flipped in the payload is
`NonCanonical` or `Codec`; a roster with unsorted rows is refused by `validate_county_review_state`;
the size limit is 8 MiB.

- [ ] **Step 2: Run.** Expected: compile failure.
- [ ] **Step 3: Implement** the three files, following `state_opponent_codec.rs` for the
  domain-framed canonical JSON.
- [ ] **Step 4: Run.** Expected: PASS. Then the scoped gate (Global Constraints).
- [ ] **Step 5: Commit** as `feat(county-review): preview, fogged projection and codec`.

### Task 6: The review contact

Spec 7.6 and section 8, record 7. A tenth organizer choice. Commit `9406851c6` (the relief hearing)
and its two lint follow-ups `cd002aef1` and `13044e13e` are the template.

**Files:**
- Modify: `rust/crates/babylon-practice-contract/src/organizer/types.rs`, `contract.rs`,
  `transition.rs`, `time_resources.rs`, `src/intent.rs`
- Modify: `contracts/organizer_practice_v1.yaml`, `contracts/practice_intent.yaml`
- Modify: `rust/crates/babylon-persistence/src/organizer_archive.rs` (`receipt_text`: the practice
  line "County review contact", and for `ReviewContactMade` the result "Reached out to one household
  for the county review."), `runtime_session/protocol.rs`
- Modify: every struct literal of `OrganizerConfig`, which gains `review: None`:
  `rust/crates/babylon-persistence/src/organizer_content.rs`, `national_economy/organizer.rs`,
  `rust/crates/babylon-tick/tests/organizer_replay.rs`, `tests/support/organizer_aid_fixture.rs`,
  `rust/crates/babylon-practice-contract/tests/organizer/support.rs`
- Modify: `rust/crates/babylon-client/src/organizer/` wherever a `match` on the choice, the outcome
  or the refusal must stay exhaustive (`presentation.rs`, `workspace.rs`, `client.rs`,
  `amount_editor.rs`, `qualification_input.rs`). Text only in this task; the views are Task 10.
  `ALL_PRACTICES` leaves the review contact out, as it leaves the hearing out.
- Modify: `tools/run_observer_session.py` and `tests/unit/tools/test_run_observer_session.py`
  (protocol 22), `tools/devtools/national_windowed_qualification.py` (`"review_unavailable"` in
  `Preview.refusal`)
- Test: `rust/crates/babylon-practice-contract/tests/organizer/review.rs` (new, added to
  `tests/organizer.rs`)

**Interfaces:**
- Consumes: `PositionKey`, `county_review_config_digest`.
- Produces:

```rust
// types.rs
pub enum OrganizerChoice { /* existing nine */ ReviewContact(PositionKey) }
pub enum OrganizerOutcome { /* existing */ ReviewContactMade }
pub enum OrganizerRefusal { /* existing */ ReviewUnavailable }
pub struct OrganizerReviewConfig { pub county_geoid: String, pub first_session_period: u64, pub county_config_digest: [u8; 32] }
// OrganizerConfig gains, after `hearing`, with serde default and skip-if-none: pub review: Option<OrganizerReviewConfig>
// transition.rs
fn position_target_identity(key: PositionKey) -> [u8; 32];
```

`ORGANIZER_SCHEMA_VERSION` stays 12 and no organizer domain string changes. `review` is added the
way the hearing commit added `hearing`, with `#[serde(default, skip_serializing_if =
"Option::is_none")]`, so every existing config, state, journal and fixture keeps its bytes, and no
fixture file is added or renamed. Only `RUNTIME_SESSION_PROTOCOL_VERSION` is raised, from 21 to 22.

The contact costs `config.contact_hours`, allocated the way `allocate_hearing_hours` allocates a
single actor's hours. Like the hearing invitation it replaces the standing routine for its period:
add `OrganizerChoice::ReviewContact(_)` to the `replaces_standing_work` list in `preview_organizer`,
to the `None` arm of `partner_for_choice` and to the `InvalidCommitment` arm of `execute_practice`,
and resolve it in its own branch beside the `InviteToHearing` branch, before the `committed_hours`
check. `validate_organizer_receipt` refuses `ReviewContactMade` on any other choice.

Its intent is the hearing's tuple, `PracticeId::Organize` with `PracticeTargetTag::Organization`,
and control parameter 9, named `review_contact` in `practice_intent.yaml`. `Organize` is the wire
name of mobilize by canvass (`contracts/practice_budget_topology.yaml`), the cell ADR301 gives the
contact. The target id is the SHA-256 of the domain `babylon.organizer-review-position.v1` followed
by the key's 16 fixed bytes, hashed the way `target_identity` hashes a domain and an id: `group` as
u32 big-endian; `band` as one byte (Bottom50 0, Next40 1, Next9 2, Top1 3); `crew` as one tag byte
(0 for `None`, 1 for `Some`) and then the u32 big-endian (zero when `None`); then `at_work`,
`seeking` and `units`, each as u16 big-endian. In `intent.rs` widen the admitted control values from
`[1..=8]` to `[1..=9]` and re-pin `PRACTICE_INTENT_SOURCE_SHA256` to the SHA-256 of the edited
`contracts/practice_intent.yaml`.

A preview is refused with `ReviewUnavailable` when `config.review` is `None` or when `state.period +
1 < first_session_period`. Put that test in a helper `fn review_open(config: &OrganizerConfig,
resolves_period: u64) -> bool` beside `hearing_resolves_in` and call it from one condition in
`preview_organizer`, so that function stays within Clippy's cognitive-complexity limit of 25. The
receipt's outcome is `ReviewContactMade`, or `InsufficientTime` as for the hearing invitation. The
contract does not know the roster: whether a household was reached is the session's record (Task 7).

- [ ] **Step 1: Write the failing tests** in `tests/organizer/review.rs`, on `aid::captured()` with
  `review: Some(..)` and `first_session_period = 4`:

```rust
#[test]
fn a_review_contact_costs_the_contact_hours_and_resolves_one_period_later() {
    let key = PositionKey { group: 0, band: Band::Next40, crew: Some(0), at_work: 1, seeking: 0, units: 0 };
    let (config, state) = at_period(3);
    let command = command(&config, &state, OrganizerChoice::ReviewContact(key));
    let preview = preview_organizer(&config, &state, &command).unwrap();
    assert_eq!((preview.refusal, preview.required_hours, preview.resolves_period), (None, config.contact_hours, 4));
    let receipt = resolve(&config, &state, &command);
    assert_eq!((receipt.choice, receipt.outcome, receipt.hours_spent),
               (OrganizerChoice::ReviewContact(key), OrganizerOutcome::ReviewContactMade, config.contact_hours));
}

#[test]
fn a_contact_that_would_land_before_the_first_session_is_refused() {
    let (config, state) = at_period(2);
    let preview = preview_organizer(&config, &state, &command(&config, &state, OrganizerChoice::ReviewContact(KEY))).unwrap();
    assert_eq!(preview.refusal, Some(OrganizerRefusal::ReviewUnavailable));
}

#[test]
fn a_campaign_with_no_review_refuses_the_choice() { /* review: None gives ReviewUnavailable */ }

#[test]
fn a_review_contact_intent_carries_control_parameter_nine() {
    /* organizer_practice_intent on the admitted commitment: PracticeId::Organize, PracticeTargetTag::Organization,
       one parameter with key 2, kind 1, length 1 and value [9] */
}

#[test]
fn two_keys_give_two_target_ids() { /* and the same key gives the same id twice */ }

#[test]
fn a_review_contact_replaces_the_standing_routine() { /* as the hearing invitation's preview and receipt say it does */ }

#[test]
fn a_review_contact_made_on_another_choice_is_refused() { /* validate_organizer_receipt */ }
```

- [ ] **Step 2: Run.** `mise run rust:test:q -- -p babylon-practice-contract -E
  'binary(organizer)'`. Expected: compile failure.
- [ ] **Step 3: Implement the contract side.** Then fix every exhaustive `match` in the workspace.
  Client text for the choice is "County review contact"; its preview and receipt wording is finished
  in Task 10.
- [ ] **Step 4: Raise the protocol pins:** `runtime_session/protocol.rs` (the constant and its
  test), `runtime_session/coordinator/tests/lifecycle.rs`, `contracts/organizer_practice_v1.yaml`
  (`runtime_session_protocol_version`), `tools/run_observer_session.py` and
  `tests/unit/tools/test_run_observer_session.py` (the admitted version moves to 22 and the refused
  versions follow, as the hearing commit moved them). `contracts/practice_intent_vectors.jsonl`
  holds no organizer control value and does not change.
- [ ] **Step 5: Run.** The scoped tests above, then `mise run rust:test:q -- -p
  babylon-practice-contract`, `-p babylon-tick -E 'test(organizer)'`, `-p babylon-persistence -E
  'test(organizer) & not test(live)'`, `-p babylon-client -E 'test(organizer::)'`, the Python unit
  tests `tests/unit/tools/test_run_observer_session.py
  tests/unit/tools/test_national_windowed_qualification.py`, and then the whole gate (Global
  Constraints). Expected: PASS.
- [ ] **Step 6: Commit** as `feat(organizer): the review contact choice`.

### Task 7: Tick: labor facts, the county section and the write-back

Spec 7.12. `material_world/city_pd.rs` and `city_pd_execution.rs` are the templates. This task is
built after Task 8: the operation, its rule and the session check already exist, and this task gives
them a county section to run on. Nothing here is added before something calls it.

**Files:**
- Create: `rust/crates/babylon-tick/src/material_world/county_review.rs` (register section, facts),
  `county_review_execution.rs` (one period)
- Modify: `rust/crates/babylon-tick/src/material_world/register.rs` (`PreparedMaterialWorld`,
  `prepare_transition`, `RegisterSections`, `assemble`, `decode_canonical`, `rebuild_binding`,
  `register_version`, `take_company_frame` and its four callers, and every `set_*` rebuild),
  `material_world.rs` (the module list)
- Modify: `rust/crates/babylon-tick/src/tick_runner.rs` (the operation's arm now runs the period),
  `material_replay.rs` (the session check reads the section)
- Modify: `contracts/material_world_register_v7.yaml`, `contracts/committed_material_tick_v3.yaml`
  (the payload's name admits version 9)
- Modify: `rust/crates/babylon-persistence/src/state_storage/schema.rs` (`sections` admits a version
  9 register)
- Test: `rust/crates/babylon-tick/src/material_world/county_review_tests.rs` (declared
  `#[cfg(test)]`), `rust/crates/babylon-tick/tests/county_review_replay.rs` (created by Task 8,
  extended here), and a unit test beside the version 8 test of `sections` in
  `state_storage/schema.rs`

**Interfaces:**
- Consumes: Tasks 3 to 6 and Task 8.
- Produces:

```rust
// county_review.rs
pub struct CountyReviewRegister { /* config: CountyReviewConfig, state: CountyReviewState */ }
impl CountyReviewRegister {
    pub fn try_new(config: CountyReviewConfig, state: CountyReviewState) -> Result<Self, MaterialWorldError>;
    pub fn config(&self) -> &CountyReviewConfig;
    pub fn state(&self) -> &CountyReviewState;
}
pub struct CountyLaborFacts { /* per staffing member and per household principal, from the transition */ }

// register.rs
impl MaterialWorldRegister {
    pub fn with_county_review(self, catalog: &MaterialCatalog, register: CountyReviewRegister,
                              resolver: Option<&StableElementResolver>) -> Result<Self, MaterialWorldError>;
    pub fn county_review(&self) -> Option<&CountyReviewRegister>;
}
impl PreparedMaterialWorld {
    pub fn county_labor_facts(&self) -> Option<&CountyLaborFacts>;
    pub(crate) fn county_review_opening(&self) -> Option<&CountyReviewRegister>;   // the section as the period opened
    pub(crate) fn set_county_review(&mut self, catalog: &MaterialCatalog, next: CountyReviewState,
        lines: &[SupportLine], collective_lines: &[SupportLine], hours: &[HourCharge],
        write_lines: bool, resolver: &StableElementResolver) -> Result<(), MaterialWorldError>;
}

// county_review_execution.rs
pub(crate) fn resolve(candidate: &mut PreparedMaterialWorld, catalog: &MaterialCatalog,
                      resolver: &StableElementResolver) -> Result<(), MaterialWorldError>;
```

`MaterialWorldError` is a closed `Copy` enum. Give it fieldless variants for the county's refusals,
or one variant that carries a small `Copy` code. Do not change its derives.

Decisions:

- *The section across a close.* `prepare_transition` rebuilds the register from the candidate and
  keeps only the company portfolios; the City PD survives the close through `city_pd_opening`. Do
  the same: `PreparedMaterialWorld` carries `county_review_opening`, filled in `prepare_transition`
  from the opening register's section, and `resolve` starts from it. `RegisterSections` gains
  `county_review`. `set_organizer_with_household_time`, `set_organizer`, `set_public_venue` and
  `set_city_pd` carry the candidate register's county section unchanged. Only `set_county_review`
  writes it.
- *The facts.* `prepare_transition` builds `CountyLaborFacts` only when the register has a county
  section. A crew is the staffing member whose `StaffingMemberId` bytes equal `crew_id`. Its group
  is the principal whose id bytes equal `group_id`: the member binding's `household_id()`, and the
  `payee` of its `EmploymentTerms`. For each staffing member of a configured crew the facts keep:
  `accrued_wages` from `transition.member_labor_use`; `hires`, `separations`, and the closing counts
  from `transition.staffing_members`; `employed_removed` and `reserve_removed` from
  `transition.resident_workforce_attrition`. The engine removes people before it hires or lays off
  (`material_staffing/composition.rs`: `apply_resident_attrition` runs before `advance_staffing`),
  so a staffing receipt's opening counts are the counts after the removal. The kernel's opening
  counts are the counts before it: the staffing receipt's opening counts plus the people removed,
  which `ResidentWorkforceAttrition` also carries. The kernel's `RosterEngineMismatch` check catches
  a wrong reading. For each configured household principal the facts keep: `taxable_amount` and
  `collected` from its `TaxReceipt` with `TaxBasis::WageIncome`; from its `IncomeReceipt` statement,
  ownership income (`distribution_income`), support income (`public_transfer_income`) and aid income
  (`gift_income`); and `closing_households` from its lifecycle receipt, or the cohort's households
  when there is none. A crew with no staffing receipt in the period keeps its counts. Its wages are
  read from its labor-use receipt all the same, when the engine wrote one: a wage the engine accrued
  is a wage, and the list ranks on it. (Lead's ruling of 20 November on a review note: the first
  form said such a crew has no wages; the code reads them, and the code is right.) A principal with
  no receipt of a kind has zero for that figure.
- *The rest of the facts* is read from the candidate's state when `resolve` runs: the public
  account's cash, its `PublicBudget` cap and floor, the sum of its lines that are not
  `HouseholdIncomeSupport`, and each group's free hours. Free hours are
  `contribution_available_hours` of the group's `HouseholdTimeReceipt` less the hours of the book's
  contributions for that principal whose `actor_id` is not the county's `config.actor_id`. Leaving
  the county's own charges out makes a second resolve of the same period read the same facts. No
  time receipt means zero hours.
- *The contact* is the `ReviewContact` key of this period's organizer receipt whose outcome is
  `ReviewContactMade`, read from the latest period of the register's organizer journal.
- *One period.* If the completed period is at least `first_session_period`: `hold_session`, then
  `roll_forward` on the outcome's roster, then `set_county_review` with `write_lines = true`. Before
  that period: only `roll_forward`, and `write_lines = false`. Both keep `last_facts`. A period with
  no session keeps `last_session` as it was.
- *The arm.* Task 8 left the operation's arm in `execute_prepared_rules` refusing every run. It now
  refuses with "County review must run once after organizer practice" when the operation has already
  run this period or the organizer's practice has not; refuses with "County review needs a captured
  county administration" when `county_review_opening()` is `None`; and otherwise calls
  `county_review_execution::resolve` and pushes one audit receipt with
  `EffectSignature::CountyReview`. `MaterialReplaySession::new` now passes
  `material.county_review().is_some()` to `validate_county_review_cycle`. If the arm takes
  `execute_prepared_rules` over Clippy's cognitive-complexity limit of 25, move the arm into a
  helper.
- *The write-back* follows `set_organizer_with_household_time`: clone the state; replace the public
  account's `HouseholdIncomeSupport` rows for the configured groups with the given lines at priority
  1 (a group with no line has no row, because every amount must be above zero); call
  `babylon_material_circuit::consume_household_contributions` with one use for each charge, whose
  `use_id` is the SHA-256 of `babylon.county-review-hours.v1`, the campaign, the period and the
  group id, with `actor_id = config.actor_id` and a non-zero `contributor_id` taken from the group's
  index plus one; rebuild the register. No other row of the state changes.
- *The section's bytes.* When the county is absent no frame is written, and a register of version 7
  or 8 keeps its bytes. When it is present, the leading domain is
  `babylon.material-world-register.v9\0`, the same length as the version 7 and 8 domains, with
  version 9. After the City PD frame comes the company frame exactly when
  `catalog.company_portfolios.is_some() && completed_tick > 0`, as today, and then a length-prefixed
  county frame: the domain `babylon.material-world-register.county-review.v1\0`, then the
  length-prefixed bytes of `encode_county_review_config` and of `encode_county_review_state`. The
  county frame has no presence byte. `register_version` and `take_company_frame` change so that
  `decode_canonical`, `validate_city_pd_resolver`, `decode_material_organizer_evidence` and
  `decode_city_pd_attempt_evidence` all accept version 9. In `babylon-persistence`, `sections` in
  `state_storage/schema.rs` admits the version 9 domain and version, reads the optional company
  frame by its domain prefix and then the county frame by its domain, and keeps both inside the
  section the company frame is in today. Document the frame in
  `contracts/material_world_register_v7.yaml` and name version 9 in
  `contracts/committed_material_tick_v3.yaml`. If a contract file's digest is pinned, re-pin it.
- *Validation* against the world, at `with_county_review` and at every rebuild: the public account
  exists; every configured ordinary group is a household cohort whose households equal the roster's;
  every crew is an employment row of its group (an entry of `MonetaryCircuit.employment` with the
  crew's member, site and unit and the group as payee); at period 0 each group's opening support
  line equals `roll_units * unit_price_micros`.

- [ ] **Step 1: Write the failing section tests** in `county_review_tests.rs`, on the hand-built
  monetary world `agency_control`
  (`rust/crates/babylon-material-circuit/tests/support/organizer_funding_control.rs`, which
  `material_world/tests.rs` already includes), extended as needed to two household groups, two crews
  and a public account with one grant and two support lines. Build its roster with `opening_roster`:
  neither group has ownership income, and at least four ninths of the households must be in the
  labor force, or the opening is refused (Task 3):

```rust
#[test]
fn a_register_without_a_county_section_keeps_its_bytes() {
    let before = register().canonical_bytes().to_vec();          // built as today
    let decoded = MaterialWorldRegister::decode_external(&catalog(), before.clone()).unwrap();
    assert_eq!(decoded.canonical_bytes(), before.as_slice());
    assert!(decoded.county_review().is_none());
}

#[test]
fn a_county_section_round_trips_and_changes_the_digest() {
    let with = register().with_county_review(&catalog(), county(), None).unwrap();
    assert_ne!(with.digest(), register().digest());
    let decoded = MaterialWorldRegister::decode_external(&catalog(), with.canonical_bytes().to_vec()).unwrap();
    assert_eq!(decoded.county_review().unwrap().state(), county().state());
    /* and the leading domain and version are the version 9 ones */
}

#[test]
fn a_roster_that_disagrees_with_the_cohorts_is_refused() { /* households off by one */ }

#[test]
fn a_county_register_carries_the_company_frame_only_when_a_register_today_would() {
    /* a catalog with company portfolios: no company frame at tick 0, one after it; both decode with the county section */
}

#[test]
fn every_other_writer_carries_the_county_section() {
    /* after set_organizer, set_public_venue and set_city_pd on a prepared world whose register has the section, it is still there and equal */
}

#[test]
fn cutting_the_tax_receipt_changes_the_list() {
    /* the sever test: with the gaining group's wage-tax entry zeroed in the labor facts no unit moves; with it in place one moves */
}

#[test]
fn resolving_a_period_twice_changes_nothing() { /* resolve twice on one prepared world: the same register digest, one use for each charge */ }
```

- [ ] **Step 2: Run.** `mise run rust:test:q -- -p babylon-tick -E 'test(county_review)'`. Expected:
  compile failure.
- [ ] **Step 3: Implement the section, its bytes and the facts.** Run. Expected: the section tests
  PASS.
- [ ] **Step 4: Write the failing period tests** in `tests/county_review_replay.rs`, through the
  real rule: a hand-built world with an organizer section and the county section, whose session
  rules are the organizer's rules and `county-review-cycle.bsl`, driven with
  `prepare_advance_with_organizer` and `commit_prepared_and_publish` as `tests/organizer_replay.rs`
  drives its world. The world must be staffed, because staffing and attrition receipts exist only on
  the staffed path, with wage income, a wage-tax receipt, household time receipts and a public
  account with household support lines. Start from the richest world the organizer replay tests
  build (`tests/support/organizer_aid_fixture.rs`) and say which you used.

  - `before_the_first_session_only_the_roster_moves`: lines and hours are untouched; the roster's
    period advanced; `last_facts` is set.
  - `without_a_contact_the_lines_are_the_rolls_own`: two periods of sessions; every support row
    equals its opening row; no hour is charged.
  - `a_contact_moves_a_unit_and_the_next_close_pays_the_line_in_full`: reach a household with a wage
    and no unit; the next period's `PublicBudgetReceipt` for the gaining group shows `paid ==
    requested == ` the new line, and the losing group's line is one unit lower. This is "the county
    keeps its word".
  - `a_contact_on_a_position_that_is_gone_spends_the_hours_and_commits`: the session record holds
    `NoSuchPosition`; the turn commits.
  - `a_county_with_no_cash_for_relief_has_no_household_line`: set the account's cash below its first
    class; after the session no `HouseholdIncomeSupport` row remains for the configured groups, and
    the state still validates.
  - `the_first_class_and_the_limit_are_never_written`: after every period the grant rows, the agency
    row and the `PublicBudget` are byte-equal to the opening's.
  - `hours_are_charged_to_the_households_group`: the book's contributions hold one use for each
    charged group, under the county's actor.
  - `the_rule_runs_once_after_the_organizers_practice`: in the period's audit receipts the county's
    receipt follows the organizer practice's, and the City PD's when the world has one.
  - `replay_gives_the_same_bytes`: run three periods twice from the same opening; the registers'
    digests are equal period by period.

- [ ] **Step 5: Implement `county_review_execution.rs`, `set_county_review` and the arm.** Run.
  Expected: PASS.
- [ ] **Step 6: Run** `mise run rust:test:q -- -p babylon-tick`, `mise run rust:test:q -- -p
  babylon-persistence -E 'test(state_storage) | test(schema)'`, and the whole gate (Global
  Constraints). Expected: PASS, and no existing test changed.
- [ ] **Step 7: Commit** as `feat(tick): the county section, its labor facts and the support-line
  write-back`.

### Task 8: The native operation and the rule

Spec 7.12 ("Where the rules live"). The City PD's operation `city-pd-observe` is the template in
every file, and commit `ac649361d` shows every list it touched. This task is built before Task 7.
After it the operation and its rule exist, and a campaign that carries the rule is refused, because
no register can carry a county section yet.

**Files:**
- Create: `content/scenarios/national/county-review-cycle.bsl`
- Modify: `rust/crates/babylon-bsl/src/rule_pipeline.rs` (`RuleExecution::CountyReview`),
  `native_cycle.rs` (the classify match and the `find_operation` pattern), `tick.rs`,
  `causal_contract.rs` (`EffectSignature`, `AllowedEffect`, `AllowedEffect::matches`, the footprint
  walker, one allowance row, one attribution row in sorted rule-id position), `identity_codec.rs`
  (the tag `0x0a`), `sfs_profile.rs` (`effect_row`), `error_identity.rs`
- Modify: the four pins that follow the source of `sfs_profile.rs`, as commit `ac649361d` moved
  them: `rust/crates/babylon-bsl/tests/fixtures/sfs_profile/sfs_audit_source_manifest_v1.txt` (the
  new SHA-256 of `sfs_profile.rs`), `rust/crates/babylon-bsl/tests/sfs_profile_contract.rs`
  (`AUDIT_SOURCE_MANIFEST_HEX`), `rust/crates/babylon-evidence/tests/synthetic_proof_harness.rs`
  (the same value) and `rust/crates/babylon-evidence/tests/fixtures/sfs_synthetic_profile.txt` (the
  proof-profile line, from the value `assert_profile_fixture` prints)
- Modify: `rust/crates/babylon-persistence/src/simulation_experiment/report/wiring/manifest.rs`
  (`effect_name`)
- Modify: `rust/crates/babylon-tick/src/tick_runner.rs` (an arm for the operation in
  `execute_prepared_rules`), `replay_session.rs` (`validate_county_review_cycle`),
  `material_replay.rs` (call it)
- Modify: the tests that pin the closed lists: `rust/crates/babylon-bsl/src/causal_contract.rs` (its
  tests), `rust/crates/babylon-tick/tests/causal_contract_conformance.rs`,
  `rust/crates/babylon-bsl/tests/organizer_cycle.rs`, `tick_identity_contract.rs`
- Test: the files above, unit tests in `replay_session.rs`, and
  `rust/crates/babylon-tick/tests/county_review_replay.rs` (new)

**Interfaces:**
- Consumes: `ADR301` (Task 2).
- Produces: the operation name `county-review`; `RuleExecution::CountyReview`;
  `EffectSignature::CountyReview`, with identity tag `0x0a`; `AllowedEffect::CountyReview`;
  `validate_county_review_cycle(active: bool)` beside `validate_city_pd_cycle`; and the rule

```
(rule welfare/county-review-session
  :role intent
  :evidence designed
  :material-basis "After the organizer's practice, rank the county's household positions by the wage tax each paid, pay next period's relief units down that list, record who came and whom each brought, and bring the roster up to date."
  :fuel 1000000
  (anchor :after ooda)
  (county-review))
```

Rules at one anchor run in the byte order of their ids (`babylon-tick/src/phase_order.rs`). The
order of files, and of rules in a file, is never observable. The county's session must follow
`organizer/organizer-practice` and `state-opponent/observe-public-activity`, so its id sorts after
both: `welfare/county-review-session`.

The attribution row is `Intent`, `Designed`, owner `Director`, date `2026-11-19`, `ADR301`. The
allowance row is `AllowedEffect::CountyReview`, `AllowanceKind::NextWeekIntent`, reason "set next
period's household support lines from the county's list and record who came". These rows are the
direct-write audit of spec section 9: no other rule is allowed this effect.

`validate_county_review_cycle(active)` follows `validate_city_pd_cycle`. With `active` false the
rule must be absent, and its presence is refused with "County review needs a captured county
administration". With `active` true there must be exactly one such rule, placed after the
organizer's practice, and after the City PD's observation when that is present, or the session is
refused with "County review must run once after organizer practice". `MaterialReplaySession::new`
calls it with `false` in this task: no register can carry a county section until Task 7. The
operation's arm in `execute_prepared_rules` refuses every run with "County review needs a captured
county administration" in this task; Task 7 gives it the period to run. The national capture does
not select the rule until Task 9, so no captured campaign changes here.

- [ ] **Step 1: Write the failing tests.**

  - In the tests of `causal_contract.rs`: the counts (allowances 8 to 9, attributions 74 to 75,
    Intent 2 to 3, Mechanic stays 69, Recognizer stays 3); `welfare/county-review-session` is
    governed with the rows above; and the rule's own branch (Designed, 2026-11-19, ADR301,
    `AllowedEffect::CountyReview`) in
    `effect_allowances_name_matching_pinned_restricted_assignments`,
    `governed_allowance_rows_carry_the_required_provenance` and
    `governed_attribution_rows_carry_the_required_provenance`.
  - In `causal_contract_conformance.rs`: `national.join("county-review-cycle.bsl")` in the
    production file list, and a `CountyReview` arm in `StaticEffect`, `footprint_effect` and
    `allowed_effect`.
  - In `organizer_cycle.rs`: the operation classifies as `(CountyReview, Some("intent"), "after",
    "ooda")`.
  - In `tick_identity_contract.rs`: `EffectSignature::CountyReview` encodes as `0x0a`.
  - In `replay_session.rs`, beside
    `city_pd_host_refuses_a_missing_rule_but_inactive_host_accepts_none`:
    `a_county_rule_without_a_county_section_is_refused_by_name`, and
    `an_active_county_needs_one_rule_after_the_organizers_practice` (the check called with `true` on
    a rule set with no county rule, on one with the rule, and on one whose county rule has an id
    that sorts before `organizer/`).
  - In `tests/county_review_replay.rs`:
    `a_campaign_with_the_rule_and_no_county_section_is_refused_by_name`, on the hand-built organizer
    world of `tests/organizer_replay.rs` with `county-review-cycle.bsl` added to its rules by
    `include_str!`: `MaterialReplaySession::new` refuses with that text.

- [ ] **Step 2: Run.** `mise run rust:test:q -- -p babylon-bsl -E 'test(causal) |
  binary(organizer_cycle) | binary(tick_identity_contract)'`. Expected: FAIL.
- [ ] **Step 3: Implement** the operation in every closed list, the rule file, the session check and
  the runner's arm. The operation's row in `sfs_profile.rs` is `county-review`.
- [ ] **Step 4: Move the four source pins** of `sfs_profile.rs`.
- [ ] **Step 5: Run** the scoped tests, then `mise run rust:test:q -- -p babylon-bsl`, `-p
  babylon-evidence`, `-p babylon-tick`, and the whole gate (Global Constraints). Expected: PASS.
- [ ] **Step 6: Commit** as `feat(bsl): the county-review native operation and its rule`.

### Task 9: Persistence: capture, runtime, snapshot, preview and archive

Spec 7.3, 7.11 and 7.12.

**Files:**
- Create: `rust/crates/babylon-persistence/src/national_economy/county_review.rs`
- Modify: `rust/crates/babylon-persistence/src/national_economy.rs` (module list),
  `policy/admission.rs`, `policy/game.rs`, `policy.rs` (`[county_review]`, required by schema 7),
  `opening/financial.rs` (expose the support amount for one job-seeking person), `organizer.rs`
  (fill `OrganizerConfig.review`)
- Modify: `content/scenarios/national/defines.toml`
- Modify: `rust/crates/babylon-persistence/src/economic_catalog/model.rs`, `codec.rs`, `capture.rs`,
  `session.rs` (carry the county opening beside the City PD's), `preset.rs`
  (`national_county_review_rules`: the City PD's rules and `county-review-cycle.bsl`), `national.rs`
  (the `expected_rules` branch for an input that carries the county), `foundation.rs`
  (`initial_county_review` beside `initial_city_pd`)
- Modify: `rust/crates/babylon-persistence/src/material_runtime/runtime.rs` (where the register is
  built with `with_organizer`, `with_public_venue` and `with_city_pd`, in
  `capture_economic_opening`, and the equality check in `from_parts`)
- Modify: `rust/crates/babylon-persistence/src/organizer_runtime/snapshot.rs`
  (`captured_organizer_snapshot`, `review_preview` and
  `DurableMaterialRuntime::preview_organizer_command`), `organizer_runtime.rs`
- Modify: `rust/crates/babylon-persistence/src/runtime_session/protocol.rs`:
  `RUNTIME_SESSION_MAX_LINE_BYTES` from 131,072 to 1,048,576, and re-export from
  `babylon_practice_contract`, beside the hearing re-exports, the types the client names:
  `CountyReviewProjection, PositionKey, Band, BandCount, PayMode, GroupKind, ContactPreview,
  ContactOutcome, LedgerLine, LedgerLineKind, PositionView, PositionEarned`
- Modify: `rust/crates/babylon-practice-contract/src/organizer/types.rs` (`OrganizerPreview.review`)
- Modify: every struct literal of `OrganizerPreview` (`review: None`) and of `OrganizerSnapshot`
  (`county_review: None`): `rust/crates/babylon-practice-contract/src/organizer/contract.rs`
  (`preview_organizer`), `rust/crates/babylon-client/src/organizer.rs`, `organizer/presentation.rs`,
  `organizer/ui.rs`, `organizer/workspace.rs`, `organizer/playback_tests.rs`,
  `organizer/qualification_input.rs`, `observer_io/qualification/aid.rs`, and
  `rust/crates/babylon-persistence/tests/national_aid_accounting.rs`. Text and views stay in Task
  10.
- Modify: `rust/crates/babylon-persistence/src/organizer_archive.rs` (a signal for each session,
  after `hearing_evidence` and `hearing_signal`)
- Modify: `contracts/economic_catalog_v1.yaml` (a `county_review_footer` beside `city_pd_footer`,
  written only under `national-world-v12`)
- Test: `rust/crates/babylon-persistence/tests/national_county_review.rs` (new),
  `src/organizer_runtime/county_review_tests.rs` (new, crate-internal),
  `tests/national_game_policy.rs`, `tests/captured_national_organizer.rs`

**Interfaces:**
- Consumes: Tasks 1 and 3 to 8.
- Produces:

```rust
pub struct GameCountyReviewPolicy {
    pub county: CountyGeoid, pub first_session_period: u64, pub session_hours: u64, pub bring_hours: u64,
    pub administration_label: String, pub claimants_body_label: String, pub aid_body_label: String,
}
// national_economy/county_review.rs
pub(crate) struct CountyReviewOpening { pub config: CountyReviewConfig, pub state: CountyReviewState }
pub(crate) fn assemble(campaign: &CampaignId, opening: /* the finished opening */, policy: &GamePolicy,
                       aid: /* the aid capture */, claimant: /* the claimant capture */, hearing: /* the hearing capture */)
    -> Result<CountyReviewOpening, /* the module's capture error */>;
// organizer_runtime/snapshot.rs
pub(crate) fn review_preview(register: &MaterialWorldRegister, command: &OrganizerCommand)
    -> Result<Option<ContactPreview>, RuntimeSessionErrorCode>;
// OrganizerSnapshot gains: #[serde(default, skip_serializing_if = "Option::is_none")] pub county_review: Option<CountyReviewProjection>
// OrganizerPreview gains:  #[serde(default, skip_serializing_if = "Option::is_none")] pub review: Option<ContactPreview>
```

Decisions:

- `defines.toml` gains:

```toml
[county_review]
evidence_class = "Designed"
county = "26163"
first_session_period = 4
session_hours = 2
bring_hours = 2
administration_label = "Wayne County administration"
claimants_body_label = "Wayne Relief Claimants Assembly"
aid_body_label = "Wayne Local Aid Partners"
```

  The two body labels must equal the labels the hearing's capture already uses: the claimants' is
  `hearing.claimant_label` and the partner's is `policy.organizer.local_partner_label`. Read them
  from there, and keep the table's values only as a check. Append the table after `[city_pd]`, at
  the end of the file: the older-schema tests cut the file at a table's heading.

- *Groups* are the household cohorts located in the county, ordinary and collective, sorted by
  principal id. A group's `roll_units` is its opening support line divided by the unit price; a
  remainder is a named error. The unit price is the opening's support for one job-seeking person
  (280,000,000 in Wayne: every support line is persons times that amount). `going_wage_micros` is
  the policy's `default_wage_micros_per_hour` (24,000,000). `has_ownership_income` is true when the
  opening holds an ownership row (`opening.institutions.ownership`) whose beneficiary is the
  principal. `receives_mutual_aid` is true for the local aid recipients. Group labels are
  `HouseholdBudgetKey::label()`, which the observer's household labels use.
- *Crews* are the staffing members whose household is one of the ordinary groups, sorted by member
  id. A collective-residence group has no crew: its `roll_units` still come from its support line,
  and Task 7's facts read no staffing receipt for it. Without this, every collective-residence
  staffing member would be a configured crew with no roster rows, and the first session of a real
  campaign would refuse the close with `RosterEngineMismatch`. A crew's pay mode is the member's
  `EmploymentTerms.compensation`, and its workplace label is the site's `EconomicSiteSeed.label`. A
  crew's `crew_id` is its member's `StaffingMemberId` bytes, a group's `group_id` is its household
  principal's id bytes, and `site_id` and `unit_id` are those of the member's employment row. Task 7
  joins the engine's receipts to the config on these ids.
- *The bands* come from `opening_roster`. `TopBandInLaborForce` and `WageBandOutsideLaborForce`
  become capture errors that name the band and give the households needed and found.
- *The opening roster* is `opening_roster` on the members' opening `employed` and `reserve`. The
  opening reach is the number of authorizing households of each hearing delegation: the claimants'
  on the claimant group, the partner's on the local aid recipients.
- *The administration* is a register actor with its own `actor_id` and `authority_id`, made the way
  the City PD's are in `national_economy/city_pd.rs` (`actor_key`, `actor_id`, `authority_id`). It
  is not a graph node in this slice.
- *Assembly order.* `county_review::assemble` does not read the City PD's config. It reads only
  cohorts, staffing, employment, ownership and the household-support lines, which
  `city_pd::add_opening` leaves unchanged. The county is captured exactly when the City PD is.
  `capture_national_campaign_with_opponent` assembles the organizer with `review: None`, then the
  City PD, then the county, and then sets `organizer.review` from the county config (its digest is
  `county_review_config_digest`). In `capture()`, `source_only.county_review = None` beside the
  lines that clear `organizer` and `city_pd`, and the organizer check compares against the assembled
  config with `review` taken from `input.county_review`. The guard of
  `capture_national_campaign_with_opponent` that refuses an input already carrying a City PD also
  refuses one already carrying a county. In
  `tests/captured_national_organizer.rs::assert_no_opponent_route`, compare the two organizer
  configs with `review` cleared, and assert that the control's `review` is `None`.
- *The rule set.* A captured national campaign carries the county's rule exactly when it carries the
  county section. Where the capture swaps in `national_city_pd_rules` it swaps in
  `national_county_review_rules` when the county is captured, and `national.rs` expects the same.
  `validate_county_review_cycle` refuses either without the other. The county opening is encoded
  only under the compiler `national-world-v12`, which Task 1 introduced for this branch, as a
  trailing frame after the City PD's (u8 tag, u32 length, bytes); a catalog of an earlier compiler
  keeps its bytes and has no county. The pins that move: the captured national rule bytes and the
  trailing bytes in `tests/captured_national_organizer.rs` (its zero tail and
  `assert_source_bindings`), and the codec unit vector in `codec.rs`.
- *The snapshot.* `captured_organizer_snapshot` builds the `LedgerInput` from the register's state
  (the county account's lines in the engine's pay order, its cash and cap, and the City PD's payroll
  from its config) and the `contacted` keys from every `ReviewContactMade` receipt in the organizer
  journal (the journal keeps every period), and calls `project`. A `PublicWorkplace` line's label is
  the `workplace_label` of a configured crew whose `site_id` is the line's recipient, else "County
  public workplace". The City PD payroll's label is found by the same rule from
  `CityPdConfig.payroll_site_account_id`, and the capture refuses a campaign whose payroll site
  employs no configured crew.
- *The preview.* `review_preview` returns `Some` only for a `ReviewContact(key)` command on a
  register with a county section: `preview_contact` on the committed register's county config and
  state. `DurableMaterialRuntime::preview_organizer_command` sets `preview.review` from it. An error
  from `preview_contact` is a typed refusal, never a silent `None`. The contract's own
  `preview_organizer` leaves `review` as `None`.
- *The archive.* Each held session adds one signal, "County review session, period N", to the
  organization's page, read from the archived tick's register
  (`county_review().state().last_session` whose period is that tick's). Its text is the public
  record only and at most 4,096 bytes, the archive's text limit: the money for relief, units payable
  and kept back, how many positions were paid in full, in part and not at all, and the ranks and
  units of the first positions on the list up to that bound. The Archive emits a page signal only
  when the page holds a knowledge grant with the signal's key (`archive.rs`, the loop over
  `input.signals` that skips a signal `knowledge.knows_field` does not know), so
  `organizer_archive::insert_projection` also inserts, in the tick the session is held, one grant
  row on the organization's page: key `county-review-{period}`, `granted_tick` the session's period,
  and the signal's own citation. `capture_projection` and `CapturedOrganizerProjection::validate`
  check the newest such row against the register's `last_session`, and that there is none while no
  session has been held. (Lead's ruling of 19 November. This bullet first said that no grant row is
  added, which left the signal built and never shown, against the client's own line "Past sessions
  are in the Archive.")
- *The line bound.* The whole snapshot travels in one `OrganizerStatus` line, and the roster can
  hold hundreds of positions, so `RUNTIME_SESSION_MAX_LINE_BYTES` rises from 131,072 to 1,048,576. A
  line at or past the bound still fails as it does today. The client and the session read the same
  constant, and the tests that build an over-long line from it follow it. If Wayne's opening line is
  not below half of the new bound, report blocked with its size and its number of positions: whether
  the roster then travels folded or by pages is a design choice, and the bound does not rise again.

- [ ] **Step 1: Write the failing policy and capture tests.** Policy: the shipped file parses to
  `first_session_period == 4`, `session_hours == 2`, `bring_hours == 2`; a schema-7 file without the
  table is refused. Capture, in `tests/national_county_review.rs` on `national_capture::input()`,
  with three helpers written in the test file: `national_opening()` is
  `CapturedEconomicCatalog::capture_national_campaign(national_capture::input(), campaign)`;
  `county_review_of(..)` reads `create_foundation(..).initial_register().county_review()`;
  `snapshot(..)` is
  `babylon_persistence::qualification_audit::aid::material_disclosure(session.catalog(),
  session.material(), session.duration())`. The workspace denies `unwrap` in tests: where a sketch
  says `unwrap`, write `expect` with a reason.

```rust
#[test]
fn wayne_is_captured_with_a_roster_that_adds_back() {
    let opening = county_review_of(&national_opening());
    let config = &opening.config;
    assert_eq!((config.county, config.unit_price_micros, config.first_session_period), (*b"26163", 280_000_000, 4));
    assert_eq!(config.going_wage_micros, 24_000_000);
    assert!(config.crews.iter().all(|c| config.groups[c.group as usize].kind == GroupKind::Ordinary));
    validate_county_review_config(config).unwrap();
    validate_roster(config, &opening.state.roster).unwrap();
    for (index, group) in config.groups.iter().enumerate() {
        if group.kind == GroupKind::Ordinary {
            assert_eq!(opening.state.roster.groups[index].households, group.opening_households);
            assert_eq!(opening.state.roster.group_units(index as u32), group.roll_units);
        }
    }
    let reached: u64 = opening.state.roster.rows.iter().map(|row| row.reached).sum();
    assert_eq!(reached, 5);   // 2 claimant households and 3 of the aid partners' 4
}

#[test]
fn wayne_opens_with_the_directors_bands() {
    let opening = county_review_of(&national_opening());
    let ordinary = |owner: bool| -> u64 {
        opening.config.groups.iter().filter(|g| g.kind == GroupKind::Ordinary && g.has_ownership_income == owner).map(|g| g.opening_households).sum()
    };
    let (owners, others) = (ordinary(true), ordinary(false));
    let b = opening.state.roster.band_counts();                          // top 1%, next 9%, next 40%, bottom 50%
    assert_eq!(b[0].households + b[1].households, owners);
    assert_eq!(b[2].households + b[3].households, others);
    assert!(b[0].households <= owners / 10 + 1 && b[0].households + 8 >= owners / 10);
    assert!(b[2].households <= others * 4 / 9 + 1 && b[2].households + 64 >= others * 4 / 9);
    assert_eq!(b[0].with_work + b[0].seeking_only, 0);                   // the top 1% do not work
    assert_eq!(b[2].outside_labor_force, 0);                             // the next 40% are all in the labor force
    assert!(b[2].people_seeking > 0);                                    // and they have unemployment too
    assert!(b[3].units > b[2].units && b[3].units > b[1].units);         // most relief sits with the bottom 50%
    // a larger share of the bottom 50%'s labor force is looking for work than of the next 40%'s
    assert!(b[3].people_seeking * (b[2].people_at_work + b[2].people_seeking) > b[2].people_seeking * (b[3].people_at_work + b[3].people_seeking));
    assert!(opening.state.roster.rows.iter().filter(|r| r.reached > 0).all(|r| r.key.band == Band::Bottom50));
}

#[test]
fn the_snapshot_at_the_opening_shows_the_ledger_and_hides_every_amount() {
    let view = snapshot(&national_opening()).county_review.unwrap();
    assert!(view.positions.iter().all(|p| p.earned.is_none()));
    assert!(view.ledger.iter().any(|l| l.kind == LedgerLineKind::CityPdPayroll && l.amount_micros == 13_551_360_000_000));
    assert_eq!(view.session_period, None);
}

#[test]
fn the_wayne_status_line_fits_the_protocol() {
    /* serialize RuntimeSessionResponse::OrganizerStatus for the opening snapshot of a Wayne campaign, as the
       session writes it, and assert it is below RUNTIME_SESSION_MAX_LINE_BYTES / 2 */
}
```

Also: `a_snapshot_of_a_register_with_no_county_section_has_no_county_field` (its JSON has no
`county_review` key, and every committed `*_v20.json` fixture still deserializes);
`the_largest_session_text_fits_the_archive` (the signal text for the Wayne opening's full roster is
at most 4,096 bytes); and, in `src/organizer_runtime/county_review_tests.rs` on the register of a
captured national foundation, `review_preview_answers_only_a_review_contact` (`Some` for a
`ReviewContact` once a close has been seen, `None` for every other choice and for a register with no
county section). The preview is tested through `review_preview`, not through the handler, which
opens PostgreSQL.

- [ ] **Step 2: Run.** `mise run rust:test:q -- -p babylon-persistence -E
  'binary(national_county_review) | binary(national_game_policy) | test(county_review_tests)'`.
  Expected: FAIL.
- [ ] **Step 3: Implement** the policy table, the capture, the catalog fields, the runtime wiring,
  the snapshot, the preview, the archive signal and the line bound.
- [ ] **Step 4: Print the opening for the record.** Add an ignored test `print_wayne_opening_roster`
  that writes, for each group, its households, its units, its crews and its rows, the count of who
  works in each band, the number of positions, and the encoded size in bytes of the opening's
  `OrganizerStatus` line, to `reports/county-review-2026-11-19/wayne-opening-roster.json`. Run it
  once and keep the file. It replaces the counts the design could not give (spec section 3).
- [ ] **Step 5: Run** the scoped tests, `mise run rust:test:q -- -p babylon-persistence -E 'not
  test(live)'`, `-p babylon-client -E 'test(organizer::)'`, and the whole gate (Global Constraints).
  Raise the catalog pins the new rule file and the new capture move. Existing JSON fixtures must
  still deserialize unchanged. Expected: PASS.
- [ ] **Step 6: Commit** as `feat(persistence): capture the county review and project it to the
  organizer`.

### Task 10: Client: four views, the contact and the preview

Spec 7.10 and 7.11. `organizer/hearing.rs` and `hearing_tests.rs` are the templates.

**Files:**
- Create: `rust/crates/babylon-client/src/organizer/county.rs` (text builders, the roster page and
  `spawn_roster`), `organizer/county_tests.rs` (declared in `ui.rs` beside `hearing_tests`:
  `#[cfg(test)] #[path = "county_tests.rs"] mod county_tests;`, so its tests are
  `organizer::ui::county_tests::*` and reach the `pub(super)` helpers of `organizer::ui::tests`)
- Modify: `rust/crates/babylon-client/src/organizer.rs` (module list)
- Modify: `organizer/client.rs`: `OrganizerInspector`; two fields of `OrganizerClient`,
  `county_review: Option<CountyReviewProjection>` installed in `status()` beside `collection`, and
  `roster_page: usize`, reset to 0 when the projection's `roster_period` changes;
  `choice_available`, `make_command`, the refresh comparison, and a `county_update` notice in a
  helper like `hearing_update`, so `status` stays within Clippy's cognitive-complexity limit of 25
- Modify: `organizer/ui.rs`: `OrganizerAction`; `TextPart::RosterLine(u8)`; `visible` (the slot and
  page buttons get their own arm, true when the inspector is `CountyRoster`; today's fall-through
  shows a button only while the inspector is closed); `enabled` and `perform_action` (both
  exhaustive on the action); `choose_approach` (it closes `CountyRoster` as it closes `Practices`
  and `Hearing`); `button_selected`; `history_inspector_allowed`; `paint_text`; `paint_buttons` (the
  slot and page actions join the list whose Display it toggles)
- Modify: `organizer/board.rs` (`dispatch_panel`), `organizer/report_view.rs` (call
  `county::spawn_roster(body)` after `hearing::spawn_choices(body)`), `presentation.rs` (`choice`,
  `flavor`, `refusal`, `practice_summary`, `preview_review`, `preview_routine`, `outcome`,
  `inspector`), `workspace.rs` (`availability` only: `ReviewContact(_)` returns
  `Refused(OrganizerRefusal::ReviewUnavailable)` when `!client.choice_available(choice)`, beside the
  `InviteToHearing` check; `ALL_PRACTICES` stays nine and gains no card), `workspace_copy.rs`
- Modify: `rust/crates/babylon-client/src/observer_performance.rs` (four `RenderMode` variants,
  labelled `organizer-county-ledger`, `organizer-county-roster`, `organizer-county-session` and
  `organizer-food-run`)
- Modify: `rust/crates/babylon-client/src/decision_surface.rs` (the `OrganizerWorkspace` row)
- Modify: `rust/crates/babylon-client/src/organizer/qualification_input.rs` (`Action`,
  `Action::organizer`, `presentation_applied` and `Pending::new`)
- Test: `organizer/county_tests.rs`,
  `rust/crates/babylon-client/tests/decision_surface_contract.rs`, the render-geometry tests
  (`render_geometry_tests.rs`)

**Interfaces:**
- Consumes: `OrganizerSnapshot.county_review` and `OrganizerPreview.review` (Task 9),
  `OrganizerChoice::ReviewContact` (Task 6). The client names the county types through
  `babylon_persistence::runtime_session`, which re-exports them as it re-exports the hearing types
  (Task 9). babylon-client keeps babylon-practice-contract a dev-dependency.
- Produces:

```rust
// client.rs
pub enum OrganizerInspector { /* existing */ CountyLedger, CountyRoster, CountySession, FoodRun }
// ui.rs
pub enum OrganizerAction { /* existing */ RosterPage(i8), ChooseRosterSlot(u8) }
// county.rs
pub(super) const ROSTER_PAGE_ROWS: usize = 8;
pub(super) enum CountyUnavailable { NoReview, PastPeriod, BeforeFirstSession { first_session_period: u64 }, AlreadyChosen }
pub(super) fn ledger(view: &CountyReviewProjection) -> String;
pub(super) fn who_works(view: &CountyReviewProjection) -> String;
pub(super) fn roster_page(view: &CountyReviewProjection, page: usize) -> Vec<String>;
pub(super) fn slot_key(view: &CountyReviewProjection, page: usize, slot: u8) -> Option<PositionKey>;
pub(super) fn session(view: &CountyReviewProjection, viewed_tick: u64) -> String;
pub(super) fn food_run(client: &OrganizerClient) -> String;
pub(super) fn preview(preview: Option<&ContactPreview>, view: &CountyReviewProjection) -> String;
pub(super) fn unavailable(reason: CountyUnavailable) -> String;
pub(super) fn spawn_roster(body: &mut ChildSpawnerCommands);   // the type `hearing::spawn_choices` takes
// qualification_input.rs, snake_case on the wire
pub enum Action { /* existing */ InspectCountyLedger, InspectCountyRoster, InspectCountySession, InspectFoodRun,
                  RosterNextPage, RosterPreviousPage, ChooseRosterSlot { slot: u8 } }
```

Decisions:

- Four entry buttons in the dispatch panel: "County ledger", "Household roster", "County session",
  "Food run". They sit in one `ui::row()` (it wraps) under the "Wayne hearing" button, and the
  period dispatch below them keeps at least 60 px of height at the 1366x768 fit; a render-geometry
  test checks it. Each opens an inspector.
- The roster shows eight positions a page, with "Previous" and "Next" and one button for each slot,
  reading "Reach a household here (N)" for N from 1 to 8. The slots are fixed nodes spawned by
  `county::spawn_roster` and painted each frame through `TextPart::RosterLine(slot)`, as the rest of
  the workspace is. Buttons are made with `ui::button` and text with `ui::text`, which add the focus
  target and the `DeclaredSurface` that `tests/decision_surface_contract.rs` requires; never spawn a
  raw `Text::new`. Each slot button's accessibility label names its position and is updated each
  frame, as `map_network_peers.rs` updates its labels.
- A slot's button is disabled with a stated reason. The reason is painted as one line of the roster
  inspector, above the slots; `unavailable_message` is not changed. The texts: `PastPeriod`, "Past
  period: reading only. Return Live before changing the organization's commitments.";
  `BeforeFirstSession`, "The county holds its first session in period N. A contact can be made from
  period N-1." (with the numbers); `AlreadyChosen`, "A ruling is already accepted for this period.";
  `NoReview`, "This campaign has no county review."
- Choosing a slot sets the draft to `ReviewContact(key)` through `choose_approach`, which closes the
  roster inspector, so "Review choice" and the comparison card show the contact on the board. The
  existing Review then Confirm flow follows. The review text comes from `presentation::review`
  through `preview_review`, whose hearing branch is the template, and is painted as the Review text
  part. It states the cost in hours, the period it lands, the period the preview is based on
  (`basis_period`), and one of: "A place is open. The unit would come from: <position>."; "No place
  is open: every unit below this household is held by a household that pays the same or more.";
  "Nobody is left to reach here." (`NobodyLeft`); "This position is no longer on the roster."
  (`NoSuchPosition`); "A reached household here would not ask: it already holds its units or a unit
  is worth less than its time." (`asks == false`); and, when `OrganizerPreview.review` is `None`,
  "No session has closed yet, so there is nothing to preview."
- Above the positions the roster shows a block headed "Who works", from `view.bands`: one line for
  each band with its households, those with someone at work, those only looking for work, those with
  nobody in the labor force, its people at work, its people looking for work, and its units. Beside
  each band are the Director's words for it, marked "Designed": Top 1%: "Does not work. Lives
  entirely off investments." Next 9%: "Some work. Some live off investments or are retired." Next
  40%: "Lives by selling wage labor. Must work. Can be out of work and looking." Bottom 50%: "Works,
  but is more likely to receive welfare and to need aid. Does not own a home." The block ends:
  "Bands are set at the opening. Homes and wealth are not in this slice." It is shown whether or not
  the player has contacted anyone.
- A position's line starts with its band ("Top 1%", "Next 9%", "Next 40%" or "Bottom 50%") and shows
  its structure always: its group, its workplace and pay mode or, with no crew, "no wage · no one in
  the labor force", people at work, people looking for work, units held, its rank, and its units
  paid and unpaid at the last session. Amounts are shown when `earned` is present. Otherwise the
  line ends: "Amounts are earned by contact. Reach a household here." Positions are shown in the
  projection's order: the last list's ranks first, then, by key, the positions that have no rank.
  After a session has been held, a position with no rank is one whose households moved there since
  that session (the roll-forward made its key), and its line says "Not on the last list: its
  households moved here since the last session." Before the first session no position has a rank,
  and the roster says once, above the positions, "The county has not held a session yet."
- Beside each income source the class reading of spec 7.10 is shown word for word, marked
  "Designed". Nation shows "pending". Every one of the four inspectors ends with the standing line
  of the Global Constraints.
- The session inspector shows the county's money for relief, units payable and kept back, each
  body's roll, the player's contact, then a block "What this session changed": one sentence, naming
  the position, for each position where a household asked and was paid, households came from the
  roll, a unit was left unpaid, or an earned position has a reason to show. Then the list in rank
  order, holding only the positions with a unit listed or a line in that block, and one closing line
  that counts the rest ("N other positions hold no unit; nobody there asked."). The remedy for
  hidden reasons is written once under the list's heading, not under every row. It shows a session
  only when `session_period <= viewed_tick`. (Lead's amendment of 20 November, from the play check:
  the first form listed all 131 positions, 84 of them empty, and the position that lost a unit was
  several screens down.)
- On a past period (`viewed_tick != durable_tick`) each county view opens with the line "These
  figures are period P, the live period. Past sessions are in the Archive." (P is `roster_period`).
  The client holds only the live period's projection, so the line is what keeps a past period's
  heading honest.
- The food run inspector shows what the client already holds: parcels the organization's households
  can spare, parcels delivered and eaten at the last run, and the hours each side was charged.
- A session record the player has a reason to read pauses playback with a notice, as the hearing's
  notices do: the county's first session ("The county's session record arrived."), a session that
  carries the player's contact ("... arrived: your contact was heard."), and a session that changes
  how the county's money stands against the roll, by the projection's own figures: from every
  listed unit paid to fewer ("... the county could not pay every unit."), from some to none ("...
  the county paid no household unit."), or back ("... the county can pay every unit again."). Any
  other session installs silently and playback goes on. (Lead's amendment of 20 November, from the
  play check: the county holds a session every period from period 4, so the first form stopped
  playback at every period.)
- The `OrganizerWorkspace` manifest row gains the action `review-contact`, the signals and
  uncertainty of the four views, their receipts and their Archive subjects.
- Scripted input. `Action::organizer` maps `ChooseRosterSlot { slot }` to
  `OrganizerAction::ChooseRosterSlot(slot)` and the two page actions to `RosterPage(1)` and
  `RosterPage(-1)`. `presentation_applied` treats a slot action as applied when `client.choice() ==
  OrganizerChoice::ReviewContact(k)`, where `k` is the `slot_key` that `Pending::new` captured
  before the action ran, and a page action as applied when `client.roster_page` equals the page
  `Pending::new` captured, moved by one step. Without this the scripted run answers
  "ordinary_handler_refused" for actions the handler applied.

- [ ] **Step 1: Write the failing tests** in `county_tests.rs`, on `tests::admitted_scene_fixture()`
  with `client.county_review = Some(fixture())`. `fixture()` is a `CountyReviewProjection` struct
  literal written in the test file (every field is public): at least one position with no crew, one
  contacted position with `earned: Some(..)`, four `bands` rows and `first_session_period = 4`. Add
  no feature to any crate. Write the helpers `app_with_roster`, `assert_preview_request`,
  `feed_preview` (it takes `tests::preview_for(&command)`, sets `review: Some(..)` and calls
  `client.previewed`) and `assert_submit_request` in `county_tests.rs`, after the steps of
  `hearing_tests.rs`'s `review_and_confirm_invitation`. The workspace denies `unwrap` in tests too:
  use `expect` with a reason.

```rust
#[test]
fn an_uncontacted_position_shows_structure_and_hides_amounts() {
    let lines = roster_page(&fixture(), 0);
    let line = lines.iter().find(|l| l.contains("no wage")).expect("the fixture has a position with no wage");
    assert!(line.contains("Amounts are earned by contact"));
    assert!(!line.contains('$'));
}

#[test]
fn choosing_a_slot_reviews_and_confirms_a_review_contact() {
    let (mut app, key) = app_with_roster();
    tests::press_named(&mut app, "Household roster");
    tests::press_named(&mut app, "Reach a household here (1)");
    tests::press_named(&mut app, "Review choice");
    assert_preview_request(&mut app, OrganizerChoice::ReviewContact(key));
    feed_preview(&mut app, place_open_preview(key));
    assert!(tests::painted_text(&mut app, false).contains("A place is open."));
    tests::press_named(&mut app, "Confirm ruling");
    assert_submit_request(&mut app, OrganizerChoice::ReviewContact(key));
}

#[test]
fn the_roster_counts_who_works_in_each_band_and_names_each_positions_band() {
    let text = who_works(&fixture());
    assert!(text.contains("Who works") && text.contains("Next 40%") && text.contains("Bottom 50%"));
    assert!(text.contains("Homes and wealth are not in this slice."));
    assert!(roster_page(&fixture(), 0).iter().all(|line| ["Top 1%", "Next 9%", "Next 40%", "Bottom 50%"].iter().any(|band| line.starts_with(band))));
}

#[test]
fn a_past_period_disables_the_slots_with_a_reason() {
    /* viewed_tick != durable_tick: the slots are disabled, the roster shows the PastPeriod line,
       and every county view opens with "These figures are period 3, the live period." */
}

#[test]
fn a_campaign_with_no_county_review_says_so_in_all_four_views() { /* county_review: None */ }

#[test]
fn every_county_view_ends_with_the_standing_line() { /* ledger, roster, session, food run */ }

#[test]
fn no_county_text_names_a_class() { /* no "workers", "proletariat", "the base" in any builder's output */ }

#[test]
fn every_contact_preview_has_its_own_text() {
    /* Reached with a place, Reached with no place, NobodyLeft, NoSuchPosition, asks == false, and None */
}
```

- [ ] **Step 2: Run.** `mise run rust:test:q -- -p babylon-client -E
  'test(organizer::ui::county_tests)'`. Expected: compile failure. (A filter that selects nothing
  makes nextest exit 4, not 0.)
- [ ] **Step 3: Implement** the builders, the inspectors, the actions, the manifest row and the
  scripted actions.
- [ ] **Step 4: Run** the scoped tests, `mise run rust:test:q -- -p babylon-client -E
  'test(organizer::) | binary(decision_surface_contract) | test(render_geometry)'` and the scoped
  gate (Global Constraints). Expected: PASS.
- [ ] **Step 5: Commit** as `feat(client): the county ledger, roster, session and food run views`.

### Task 11: Scripted input, recorded playthroughs and the how-to

Spec section 9 ("Play proof").

**Files:**
- Modify: `tools/devtools/national_windowed_qualification.py` and
  `tests/unit/tools/test_national_windowed_qualification.py`: the seven new `UnitAction` names of
  Task 10, with `{"choose_roster_slot": {"slot": n}}` as a record in `Action`; a
  `ReviewContactChoice` (`review_contact`: group, band, crew, at_work, seeking and units, with the
  exact serde names of Task 3's `PositionKey` and `Band`) in `Choice`; a `ContactPreview` model and
  `review: ContactPreview | None` on `Preview`; `"review_contact"` with `page` and `slot` in
  `PlannedChoice`, its validator branch and the driver's action map. Every model is a `FrozenRecord`
  (`extra="forbid"`), so a reply the Rust client emits after a slot is chosen fails to parse until
  these exist. The unit tests check each model against a reply the Rust client emits.
- Modify: `tools/run_rust_postgres.sh`: a new live focus `county_review`, added to the focus `case`
  and as a branch of the per-focus `case` that runs `run_phase county_review_playthroughs 3600 cargo
  test -p babylon-persistence --test observer_material_live county_review_playthroughs:: --locked --
  --ignored --nocapture --test-threads=1`. It is local only, so `tools/ci_scope.py` and its test do
  not change.
- Create:
  `rust/crates/babylon-persistence/tests/observer_material_live/county_review_playthroughs.rs`
  (ignored; declared in `observer_material_live.rs`; it uses that binary's
  `support::DisposableTarget` and its runtime-session support)
- Modify, if the driver is shared:
  `rust/crates/babylon-persistence/tests/support/national_playable.rs` (see the driver decision
  below)
- Create: `reports/county-review-2026-11-19/README.md` and one JSON record for each playthrough
- Modify: `docs/how-to/organize-in-wayne.rst` (a section "Take a household to the county review";
  rstcheck and doc8 with lines of at most 100)
- Modify: `docs/superpowers/specs/2026-11-19-county-review-design.md` (section 3 and 7.7 take the
  recorded figures)
- Test: the files above

**Interfaces:**
- Consumes: everything.
- Produces: four recorded playthroughs from one opening, each a seed, an action log and a result: no
  contact; one position, contacted in period 3 and never again; two positions, the same and from
  period 10 a second; food runs only, a local aid run every period.

Decisions:

- *One opening.* Every run, and the replay, uses the same `CampaignId`, each in its own disposable
  database (`DisposableTarget::create()`), as `national_city_pd_matched_budget_controls_commit` in
  `tests/observer_material_live/organizer.rs` does. The campaign id is bound into the organizer's
  and the county's configs, so four `New` campaigns in one database would be four openings. The seed
  is the `Ready` foundation digest, which must be equal in all five. To share work, the opening may
  be persisted once and its database cloned for each run (`CREATE DATABASE ... TEMPLATE`).
- *The driver.* The runs send the requests the client sends (`OrganizerStatus`, `PreviewOrganizer`,
  `SubmitOrganizer`, `Advance`) through a runtime session, as `national_playable.rs`'s `Session`
  does (start, status, accept with a nonce, advance, stop). That module belongs to another binary
  and needs that binary's environment, and its `Session::accept` panics on a choice it does not
  schedule. Either move `Session` into a shared file that both binaries use whole, or write a driver
  in the new module with only what it uses. A shared item one binary leaves unused fails `-D
  warnings`: do not add `allow(dead_code)`. Submit a review contact with the nonce path, not
  `accept`.
- *What the snapshot does not carry.* Tax rates, the wage tax collected, the lines paid and each
  period's county state are read through the full observer
  (`observer_reader::provision_observer_role` and an `ObserverEconomyReader` login, as
  `organizer.rs` does): `committed_material_receipts(campaign, tick)` for `TaxReceipt.rate_bps` and
  `.collected` and the `PublicBudgetReceipt`s, and the observer cursor's `current_register()` then
  `.county_review()` for `last_facts`, `last_session` and `roster`. Each period's register digest is
  the committed `RuntimeSessionTail` (`tick_content_hash` and `world_hash`).
- *The positions.* Each contacted position is chosen by the county's own preview. The first is the
  first position, in the period-3 snapshot's list order, whose `PreviewOrganizer` reply for
  `ReviewContact(key)` has `review.outcome` reached, `review.asks` true and `review.place_open`
  true. The second is the first such position of the period-10 snapshot whose `key.crew` differs
  from the first's. Each preview goes into the action log. (Lead's amendment of 20 November, from
  the play check. The first form took the first position with `has_wages`, no unit and households
  left to reach; in a real campaign the first seven positions of the period-3 list had no open place
  or would not ask, and the eighth, a household at work at "Wayne County: extraction (5)" in the
  bottom 50%, had one.)
- *How long.* "Short" means a session with `relief_micros < roll_total_micros`. Each run stops at
  period 34 or two periods after its first short session, whichever is later, and never past period
  40. If the county is not short by period 40, the record says so. (In the recorded run of 14
  November relief was full through period 29 and nothing from period 30.)
- *Food runs.* When a period's `LocalAid` preview is refused, the record logs the refusal and that
  period runs the standing routine.
- *Time.* Each session advances without waiting for Archive catch-up and without a cold reopen each
  period; one reopen at the end of the one-position run is enough. Expect about 7 to 10 s a close
  and 1 to 2 minutes an opening, so about 40 minutes for the five sessions under the 3,600 s phase
  limit. Run the sessions one at a time: a national runtime peaks near 4 GB.
- *The records.* A record holds, for each period, a summary: the county's cash, the money for relief
  and the roll's total, units payable and kept back, the four bands' counts of who works, the hour
  charges, the contacted positions' own rows, the register digest, and `last_facts` with the contact
  keys (Step 4 replays from them). It does not hold each period's full projection. Each record file
  stays under 1 MiB (the repository's blob limit) and ends with a newline.

- [ ] **Step 1: Write the failing playthrough test.** It drives the four runs and the replay, writes
  the records, and asserts:

  - no contact: until the county is short, every period's household lines equal the roll's own and
    no hour is charged;
  - one position: a unit moves in the first session after the contact; the number of households that
    came doubles each session until the position is full or no unit is left below it; after the
    county's money for relief ends nobody is paid;
  - the first-class lines, the spending limit and the tax rates are identical in all four runs in
    every period;
  - in every period of every run each band's households are its opening households less those that
    left, no household of the top 1% is in the labor force, and the count of who works in each band
    is written to the record;
  - the four final records differ, and the test prints the difference in the county's cash and tax
    receipts between the first two;
  - replaying the "one position" run gives the same register digest in every period.

- [ ] **Step 2: Run it.** `BABYLON_POSTGRES_LIVE_FOCUS=county_review mise run test:rust-postgres`.
  Expected: FAIL before the test is complete, PASS after. Record each turn's wall time in the
  README.
- [ ] **Step 3: The windowed models.** Extend the windowed models and their unit tests (Files). The
  windowed run itself needs a released native profile that reaches the close of period 4 with a
  review contact in period 3. Neither `smoke-01` (2 periods) nor `walk-01` (10 periods, pinned
  decisions) does, and `--wayne-native-pair` refuses outside the released checkout. Record the
  refusal text of `tools/run_rust_postgres.sh --wayne-native-pair smoke-01` run from this worktree
  in the README, and do not promise a `native-controls.json`.
- [ ] **Step 4: The other bounds.** From the "one position" run's recorded opening roster and its
  recorded facts for each period, replay the sessions in the kernel under `Placement::HoldersFirst`
  and `Placement::HoldersLast`, and write to the README, for each period, the units held by
  households with no wage under the three placements. This is a report for the Director. It is not a
  pass or a fail.
- [ ] **Step 5: Write the how-to section and the README.** The README states what each playthrough
  shows, with figures read from its record, and what was not shown. It gives who works in each band
  at the opening and in each period of the "no contact" run, beside the Director's words for each
  band.
- [ ] **Step 6: Put the recorded figures into the design** in place of the withdrawn tables of
  sections 3 and 7.7, and in place of the worked "Who works" table of section 3, wrap it at 100
  columns, and run the markdown hooks.
- [ ] **Step 7: Run every gate.** `mise run rust:check-no-docs` (in the background, logged, as the
  Global Constraints say), then `mise run check` and `mise run check:ceremony`. Expected: PASS. A
  failure that this branch did not cause is listed in the README with its evidence and is not fixed
  here.
- [ ] **Step 8: Commit** as `test(county-review): recorded playthroughs and the how-to`.
