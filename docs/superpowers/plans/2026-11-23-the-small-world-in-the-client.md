# The Small World in the Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** A person opens the Bevy client, picks the small world, and sees the doubled test economy (two places, eight
workplaces, eighty people, one treasury, one fund) drawn by its ties. They step it, play it, replay a period, start
over, and strike it with a labelled shock in Place A, in Place B or in both. Hours and money are read side by side.

**Architecture:** A new ordinary crate, `babylon-circuit-worlds`, holds the doubled fund world (catalog, opening state,
staffing), its shocks as changes of the catalog, and a `Runner` that steps it by the engine's own period. The client
gains a third mode, `--small-world`, that runs that `Runner` in its own process with no runtime, pipe or database. A
pure reading turns each period's receipts into hours, goods and payments; a pure frame builder turns those into the
hypergraph library's `FieldFrame`, bodies with two rings, and a table. The library's `FieldPlugin` draws particles,
membranes and the three beats of marks. One button on the title screen starts the same mode as a second process.

**Tech Stack:** Rust 1.99.1; `babylon-material-circuit` (engine, public API only); Bevy 0.20.1; `hypergraph-rs` and
`hypergraph-rs-bevy` pinned by git revision; serde_json for the script.

**Spec:** `docs/superpowers/specs/2026-11-23-the-small-world-in-the-client-design.md` (sections 6 and 7);
`ai/decisions/ADR320_screen_first_the_small_world_in_the_client.yaml`; the look:
`docs/superpowers/specs/2026-11-21-field-and-particles-design.md` sections 2, 6.1, 6.2, 6.4, 6.5, 6.7, 6.9, and
`ai/decisions/ADR317_field_and_particles.yaml`. The prototype is the scratch branch `spike/r10-P` (head `3944ee9f3`),
`rust/crates/babylon-material-circuit/tests/small_world/support.rs`, read only with `git show spike/r10-P:<path>`.
Readers' notes, in the folder `NOTES` (the lead gives its path in each task's brief): `notes-world.md` before Tasks
1 to 3; `notes-client.md` before Tasks 4 and 6 to 9; `notes-library.md` before Tasks 5 to 7.

## Where the plan departs from the design

1. **Two of the four shocks are left out.** "Pay rises at the clinic" is `EmploymentTerms.compensation` and "the
   fund's taxes are cut" is `TaxPolicy.rate_bps` of `FinancialInstitutions.taxes`. Both live in the state, not in the
   catalog (`MaterialCatalogDefinition`, `src/catalog.rs:25-47`, has no wage and no tax field; game branch). By the
   design's own rule (6.4, last bullet) they are left out. The scene offers the harvest and the power cut.
2. **The power cut cannot be lifted, and its first period has a seam** (the lead's answer of 23 November). The quiet
   world's utility works in batches of 1 hour and 1 unit. The cut is the catalog's 10 hours and 9 units a batch, so it
   changes the size of a batch. The state's plans are counted in batches. Struck mid-run, the first period under the
   cut still holds a plan in the old unit; the hours at hand then set what is made, which is the shock itself, and
   Task 3 pins what that period does. Lifted mid-run, the plan made under the cut (about a tenth as many batches)
   would be read in the old unit for one period, and power would fall to about a tenth for a reason that is no part
   of the economy. So the power cut holds until the run is started over, and the scene says so. The harvest changes
   only the yield of a batch and has no seam. If the engine refuses the swap, Task 3 leaves the power cut out and
   reports.
3. **The scripted check cannot assert that the farm's hours fall in Place A.** On the bench, with the harvest failed
   in A only, farm A attended 40 hours in each of the first 46 periods; the fall showed in the clinic and the utility
   (`/media/user/dev-ssd/babylon-bench/restoring-forces/out/r10-P-down-ref-none-400/fund-P2a.tsv`, column
   `hours_attended_farm_a`). Task 9 asserts what the catalog makes certain (farm A makes 36 food a period while farm
   B makes 40) and records every workplace's hours in A and in B as the client reports them.
4. **The title button starts a second process.** The window cannot open without a campaign identity
   (`cli.rs` `windowed_target` 463-512), and almost every observer system takes a non-optional
   `Res<ObserverSession>`; the observer's plugins cannot be removed at runtime. So the button runs the client's own
   executable with `--small-world`, stdin, stdout and stderr null, and the observer window stays as it was.
5. **The scene is a sixth declared surface** (the lead's answer of 23 November). The client's rule is that every
   shipped `Text`, `ImageNode`, `Mesh2d` and `Mesh3d` belongs to a surface of the manifest
   (`src/decision_surface.rs`), and the manifest's closed set is pinned by
   `tests/decision_surface_contract.rs` so that a new surface is added on purpose. The scene is shipped, so it is
   declared: `SurfaceId::SmallWorld`, an `AdminDebug` surface whose fog line is the manifest's own "unfogged material
   truth; no player knowledge state". The pinned set changes on purpose, in Task 7: the observer's composition
   shows the five it showed, the scene's composition shows the sixth, and the two together are `SurfaceId::ALL`.
6. **The frame time is measured with the library's `FrameWindows`, at the client's figures.** The client's
   `FrameSampler` (`observer_performance.rs`) takes the observer's session resources as parameters and cannot run
   here. The scene uses 300 intervals after 2 s of settling (the client's `SAMPLE_COUNT` and `SETTLE_SECONDS`) and
   writes the client's `frame_perf` log line with `view=small_world`.
7. **The frame builder reads one period's result.** Nothing in the picture needs the period before: the library eases
   particles and swaps sets between frames itself, and tells changes of membership (`SetChanged`).
8. **The table has a fifth column, "paid, not used",** for idle hours, as ADR317's ruling 17 requires ("Idle hours on
   the clock are drawn apart and have their own column").
9. **The world is built for 998 periods.** Capacity is a finite schedule (`src/model.rs:471`); the opening writes rows
   to period 1,000, as the bench wrote `periods + 2`. A step past period 998 is refused on screen. The runner never
   adds rows to the state.
10. **"Every period equal to the first" is judged on a summary,** not on state bytes, because the state carries its
    period number: hours attended, made, employed, every account's cash, posted prices, total money and persons.
11. **The owner's own household needs a number** to be inside its owner set. It is the household's own book capital
    (its `CapitalAccount`), the same figure as the workplaces' (Task 6).
12. **A control for still marks.** The field design's 6.4 rules that reduced motion shows still paths. The client's
    reduced-motion setting lives in the observer's `ObserverUiState`, absent here, so the scene has its own switch.

## Global Constraints

- The plan was read against `codex/households-and-homes` at `3b0b02383` (the design and ADR320 amended: the scene
  opens on household groups, people behind a switch with a standing line; engine and client as at `d0a99eb98`).
- Work only in `/media/user/dev-ssd/worktrees/households-homes/babylon` on branch `codex/households-and-homes`. Start
  every shell command with `cd` to it or to its `rust/`. Never push. No `.env`, no `uv.lock`: never commit `uv.lock`.
- One cargo, mise or test process at a time on the whole machine. Never pass `-j`. Only `mise exec -- cargo ...` and
  `mise run ...`.
- No pinned value of an existing test changes and no assertion is loosened, with two exceptions that are named:
  Task 1 adds the new crate's name to a list of the workspace's crates and nothing else, and Task 7 adds the scene's
  surface to the surface contract's closed set (Departure 5) and nothing else.
- Money is `i128` millionths of a dollar (`Currency::micro_units`); quantities and hours are `u64`. Arithmetic is
  checked (`checked_add`, `checked_mul`, `try_from`), and a failure is a typed error, never a panic or a wrap.
- Hours and money never meet in one expression: no sum, ratio, scale or position mixes the two.
- **Looked at before it is built on.** No number of the scene's look (a position, a size, a width, a colour, the
  view) is final until the lead has seen it in a capture of the real window. Task 7 ends with that look and Task 8
  starts after it. A builder changes none of these numbers by taste: where one cannot be reached, report it.
- Functions under 100 lines and cognitive complexity at most 25 (`rust/clippy.toml`). No `unwrap`; every `#[allow]`
  or `#[expect]` carries `reason = "..."`. Import a type and use its bare name (bsl-lint `google-rust-style`); one
  module per `use`; no glob import but `use bevy::prelude::*` in the client and `use super::*` in a test module.
  No `mod.rs`; a module with children holds only `mod` and `pub use` lines.
- No `HashMap` or `HashSet` whose order decides an output; use `BTreeMap`/`BTreeSet` or sorted `Vec`s.
- Client tests are unit tests in `src/` (inline `#[cfg(test)] mod tests` or a sibling `*_tests.rs` file included with
  `#[cfg(test)] #[path = ...]`). The dev gate runs only two of the client's integration targets
  (`tools/rust_test_report.py` `DEV_INTEGRATION_TARGETS`), so a new file under `babylon-client/tests/` would not run.
- The scratch branch `spike/...` is never merged, cherry-picked or switched to in this checkout. Read it with
  `git show spike/r10-P:<path>` only. Nothing of its `src/spike_*.rs` is brought over.
- Every line number is a hint; find each place by its text.
- **Scoped gate, before a task's last commit,** one leg at a time, from `rust/`:
  `mise exec -- cargo fmt --all -- --check`; `mise exec -- cargo clippy --workspace --all-targets --locked --
  -D warnings -D clippy::cognitive_complexity`; `mise run rust:test:q -- -p <each crate the task touched>`;
  `mise run check:bsl-sentinels`. Whenever a task changes anything under `tools/`, `tests/unit`, `.mise.toml` or
  `.github/`, also from the repository root: `env -u PYTHONPATH mise exec -- uv run --inexact --no-sync pytest
  tests/unit/tools tests/unit/test_mise_tasks.py -o addopts="" -q`.
- Commit: `git add <files>`; message in a file; `PYTHONPATH=src mise exec -- git commit -q -F <file>`; then check
  `git log --oneline -1` (a hook can abort silently). The body ends with `Part of PER-371` and a `Co-Authored-By`
  line naming the model that wrote the commit.

## Review Focus

1. **A figure on screen the engine did not produce.** Every number drawn or printed comes from a `PeriodResult`
   (Task 2) through `read_period` (Task 4). A table sum is the sum of its rows. Pinned by Task 4's
   `every_payment_of_the_quiet_period_is_read_once` and `a_workplace_pays_out_what_it_takes_in_a_still_world`.
2. **Hours meet money.** Work flows, the hours ring and the hours bars are `u64` hours with their own scale; payments,
   the money ring, the money bars and the placement weights are money with theirs. A reviewer reads every expression
   of `frame.rs`, `layout.rs` and `table.rs` for a mix. Pinned in part by Task 6's
   `each_stream_draws_and_counts_exactly_its_own_total`.
3. **The scene edits the engine's state.** A shock swaps the catalog for the next close and nothing else. Pinned by
   Task 3's `a_strike_lifted_before_it_holds_changes_nothing` and by the runner's own money and person checks.
4. **A payment counted twice.** A wage is a reservation then a payment; a purchase a reservation, a settlement and
   perhaps a refund. Only the payment and the settlement count. Pinned by Task 4's totals.
5. **The launcher's world reached from the scene.** The small-world composition adds none of the observer's
   plugins. Pinned by Task 7's `the_small_world_composition_has_no_campaign_session`.
6. **Two copies of the library.** Both `hypergraph-rs` lines and the `hypergraph-rs-bevy` line name the same URL and
   revision, or the lock holds two `hypergraph-rs` packages whose types do not match. Checked in Task 5's steps.
7. **The quiet world moves on the game's engine.** The doubled treasury under `CashInProportion` with standing
   allocations is a shape the engine's own tests do not run (notes-world 2.4). Task 1's first test closes a period.

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `rust/crates/babylon-circuit-worlds/Cargo.toml`, `src/lib.rs`, `src/error.rs` | The crate, `WorldError` | 1 |
| `rust/crates/babylon-circuit-worlds/src/ids.rs` | `Place`, `Kind`, `Workplace`, `Household`, `Good`, identities | 1 |
| `rust/crates/babylon-circuit-worlds/src/doubled.rs` and `src/doubled/{figures,catalog,opening,staffing}.rs` | The doubled fund world | 1, 3 |
| `rust/crates/babylon-circuit-worlds/src/runner.rs` and `src/runner/{run,result,error}.rs` | `Runner`, `PeriodResult` | 2, 3 |
| `rust/crates/babylon-circuit-worlds/src/shocks.rs` | `Shock`, `Places`, `Lasts`, `Strike`, `ShockBook` | 3 |
| `rust/crates/babylon-circuit-worlds/tests/{doubled,runner,shocks}.rs` | The crate's tests | 1, 2, 3 |
| `rust/Cargo.toml`, `rust/Cargo.lock` | Member; lock entries | 1, 4, 5 |
| `tests/unit/test_mise_tasks.py`, `tools/postgres_national_lifecycle.sh` | Lists of crates | 1 |
| `rust/crates/babylon-graph/Cargo.toml`, `rust/crates/babylon-client/Cargo.toml` | The library's pin; Bevy 0.20.1 | 4, 5 |
| `rust/crates/babylon-client/src/small_world.rs` | `mod` and `pub use` only | 4 |
| `rust/crates/babylon-client/src/small_world/{reading,table}.rs` | Receipts to hours, goods, payments; the table | 4 |
| `rust/crates/babylon-client/src/small_world/{layout,frame}.rs` | Positions; the picture; styles | 6 |
| `rust/crates/babylon-client/src/small_world/{scene,controls}.rs` | The plugin, runner resource, commands, camera | 7, 8 |
| `rust/crates/babylon-client/src/small_world/{panel,inspect}.rs` | Table panel, inspector, shock list | 8 |
| `rust/crates/babylon-client/src/small_world/{script,frame_time}.rs` | Script file, pictures, frame time | 9 |
| `rust/crates/babylon-client/src/{cli,app,main,lib,observer_title,observer_ui}.rs` | Flag, mode, button, `apply_fonts` | 7 |

---

### Task 1: The crate of small worlds and the doubled world's opening

**Files:**
- Create: `rust/crates/babylon-circuit-worlds/Cargo.toml` (`publish = false`; `version.workspace`, `edition.workspace`,
  `rust-version.workspace` and `license.workspace` all `= true`, as `babylon-graph/Cargo.toml` 4-7;
  `[lints] workspace = true`; `[dependencies]` `babylon-kernel` and `babylon-material-circuit` by path, nothing
  else); `src/lib.rs`; `src/error.rs`; `src/ids.rs`; `src/doubled.rs`; `src/doubled/figures.rs`;
  `src/doubled/catalog.rs`; `src/doubled/opening.rs`; `src/doubled/staffing.rs`; `tests/doubled.rs`.
- Modify: `rust/Cargo.toml` (`members` gains `"crates/babylon-circuit-worlds"`); `rust/Cargo.lock` (written offline:
  `mise exec -- cargo metadata --offline --format-version 1 > /dev/null` from `rust/`);
  `tests/unit/test_mise_tasks.py` (`PEDANTIC_RUST_PACKAGES` gains `"babylon-circuit-worlds",` between
  `"babylon-bsl",` and `"babylon-client",`); `tools/postgres_national_lifecycle.sh` (`national_source_paths`: the
  `for` list near line 457 and the `case` list near line 463 each gain `babylon-circuit-worlds`, because the client
  takes it as a path dependency in Task 4 and line 464 dies on an unlisted one).

**Interfaces:**

```rust
// src/error.rs
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WorldError {
    Engine(MaterialCircuitError),       // a constructor of the engine refused
    Staffing(StaffingError),
    Location(String),                   // EconomicLocation::from_str refused "county:26163"
    Arithmetic,                         // a checked sum or product overflowed
}
impl Display for WorldError; impl Error for WorldError; // Engine: "the engine refused the world: {e:?}"
// src/ids.rs
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)] pub enum Place { A, B }
impl Place { pub const ALL: [Place; 2]; pub const fn index(self) -> usize; pub const fn label(self) -> &'static str }
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)] pub enum Kind { Utility, Farm, Clinic, Shop }
impl Kind { pub const ALL: [Kind; 4]; pub const fn index(self) -> usize; pub const fn label(self) -> &'static str }
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct Workplace { pub place: Place, pub kind: Kind }
impl Workplace {
    pub const ALL: [Workplace; 8];                       // A's four in Kind order, then B's
    pub const fn index(self) -> usize;                   // 4 * place + kind
    pub fn from_site(site: SiteId) -> Option<Workplace>;
    pub const fn site_id(self) -> SiteId;                // byte index + 1
    pub const fn process_id(self) -> Option<ProcessId>;  // byte index + 1; None for a shop
    pub const fn pool_id(self) -> StaffingPoolId;        // = site bytes
    pub const fn member_id(self) -> StaffingMemberId;    // = site bytes
    pub const fn workers(self) -> Household;
    pub fn label(self) -> String;                        // "Place A farm"
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Household { Workers(Workplace), Owner(Place), Supported(Place) }
impl Household {
    pub const ALL: [Household; 12];                      // in principal byte order 11..=18, 20..=23
    pub const fn principal(self) -> FinalDemandPrincipalId;
    pub fn from_principal(id: FinalDemandPrincipalId) -> Option<Household>;
    pub const fn place(self) -> Place;
    pub const fn opening_persons(self) -> u64;           // 12/4/4/4 workers, 8 owner, 8 supported
    pub fn label(self) -> String;   // "Place A farm workers", "Place A owners", "Place A supported"
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)] pub enum Good { Food, Power, Care }
impl Good { pub const ALL: [Good; 3]; pub const fn good_id(self) -> GoodId;
            pub fn from_good(id: GoodId) -> Option<Good> }
pub const fn treasury() -> PublicAccountId;   pub const fn fund() -> PublicAccountId;
pub const fn goods_unit() -> UnitId;          pub const fn hours_unit() -> UnitId;
pub const fn route(place: Place) -> RouteId;  pub const fn corridor(place: Place) -> CorridorId;
pub fn location() -> Result<EconomicLocation, WorldError>;   // "county:26163" for both places
// src/doubled/figures.rs
pub const HORIZON: u64 = 1_000;               // capacity rows are written for periods 1..=HORIZON
pub const HOURS_PER_PERSON: u64 = 10;
pub const PERSONS: u64 = 80;
pub const OPENING_MONEY: i128 = 12_240_000_000;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Figures { pub farm_yield: [u64; 2], pub utility_hours_per_batch: [u64; 2],
                     pub utility_output_per_batch: [u64; 2] }
impl Figures { pub const OPENING: Figures; }  // [10, 10], [1, 1], [1, 1], indexed by Place::index
// src/doubled/catalog.rs
pub fn catalog(figures: &Figures) -> Result<MaterialCatalog, WorldError>;
// src/doubled/opening.rs
pub fn opening_state() -> Result<MaterialCircuitState, WorldError>;
// src/doubled/staffing.rs
pub fn staffing() -> Result<(Vec<StaffingPoolBinding>, StaffingState), WorldError>;
pub fn member(workplace: Workplace, employed: u64) -> Result<StaffingMemberState, WorldError>;
```

**Decisions:**
1. **What to copy.** The spike's builder is `tests/small_world/support.rs` at `spike/r10-P`: identities 202-270 and
   1661-1674, `World::plain` 1821, `taxed` 1868, `benefits` 1886, `with_tiers` 1993, `doubled` 1790, `batches` 2021,
   `site_hours` 2044, `households` 2062, `definition` 2088-2285, `recurring` 2286-2460, `financial` 2461-2538,
   `add_fund` 2539-2593, `all_support`/`basket`/`support_payment` 2594-2623, `state` 2624-2853, `connections`
   2863-2897, `staffing` 2900-2942, `member_state` 3360. The world on screen is `World::benefits().with_tiers()
   .doubled()` with every environment variable unset (notes-world part 1). Port it as free functions over these
   fixed figures: no `World` struct, no `twin`, no `part(c)`; loop over `Place::ALL` where the spike loops copies.
2. **What to drop.** Every environment read (`SPIKE_*`), the globals `two()`, `copies()`, `n_sites()`,
   `site_index()`, `spike_a4()` and its cross-place routes, `spike_w_mark_raw`, `lend_pairs`, `seek`, the bank, the
   pay, lending and d2 fields. `opening_cash_periods()` is 1; `seekers_at_opening()` is 0; every price step is $1.
3. **One change from the spike:** `MarketClearingPolicy` gains `plans_from_spare_money: true` on the game's engine
   (`src/clearing/rule.rs:11-19`); the closest form's base asks for rule A6.
4. **The horizon:** capacity and corridor rows for periods 1 to `HORIZON` (the spike's `periods + 2`).
5. **Errors:** every engine constructor's refusal is returned as `WorldError`, never `expect`ed. The `# Errors`
   section of each `pub fn` names what it returns. If a function goes over 100 lines, split it by part of the state
   (book, costs, recurring, financial, staffing), as the spike's own functions are split.
6. **The opening figures are the prototype's,** listed in notes-world 1.2 to 1.7. The later plan of the closest form
   proves this same world against measured rows; nothing here is tuned.

- [ ] **Step 1: Write the failing tests** in `tests/doubled.rs`:
  - `the_engine_closes_the_first_period_of_the_doubled_world`: `close_material_period(&catalog(&Figures::OPENING)?,
    &opening_state()?)` is `Ok`, and its `staffing_requests` with `staffing()`'s bindings is `Ok`.
  - `identities_are_the_prototypes`: every id is 32 copies of one byte: sites 1..=8 in `Workplace::ALL` order;
    processes 1, 2, 3, 5, 6, 7 and none for the shops; workers of utility A 11, utility B 12, farm A 13, farm B 14,
    clinic A 15, clinic B 16, shop A 17, shop B 18; owners 20, 21; supported 22, 23; treasury 30; fund 31; routes
    2, 6; corridors 4, 8; food 1, power 2, care 3; goods unit 1; hours unit 2. `from_principal` and `from_site`
    invert them; byte 19 and 24 give `None`.
  - `the_opening_holds_eighty_people_and_12240_dollars`: the recurring cohorts' persons sum to 80 (12, 4, 4, 4, 8, 8
    a place); `total_cash_and_reserves` is 12,240,000,000; cash is $1,200 / $880 / $880 / $1,400 at each place's
    utility, farm, clinic and shop, $640 at each owner, $0 at every worker and supported household, $320 at the
    treasury and $1,920 at the fund.
  - `the_opening_figures_are_the_measured_ones`: offers $12 / $25 / $30 / $38 a place; inventory 40 food at each
    farm and each shop; labor rows 120 / 40 / 40 / 40 hours a place for period 1; commitments 120 / 4 / 40 batches;
    8 employment rows at `Wage($10)`; 32 tax rows at 500 (treasury) and 1,500 (fund) bps; programs `laid_off`
    (`AfterLayoff` 5,000 bps, 13 half periods, 8 recipients) and `no_earner` ($60 a person, 2 recipients); 2
    allocations of $160 to the supported households; both budgets `CashInProportion` with cap $0; 8 ownership claims
    of 1 share, owner A sites 1-4, owner B sites 5-8; 8 distributions at 10,000 bps; capacity rows 6 a period and
    corridor rows 2 a period for periods 1 to 1,000, nameplates utility 120, farm 8, clinic 40 batches.
  - `the_catalog_asks_for_the_market_and_plans_from_spare_money`: `market_clearing` is `Some`, paying order food,
    power, care, 36 wants, `plans_from_spare_money` true; 6 process outputs with farm yield 10 and utility 1 unit a
    batch; 6 labor coefficients (utility 1, farm 10, clinic 1 hour a batch).
  - `the_staffing_opens_with_every_worker_employed`: 8 pools, employed 12 / 4 / 4 / 4 a place, reserve 0;
    `member(w, employed)` gives household `w.workers()`.
- [ ] **Step 2: Run them and see them fail.** `mise run rust:test:q -- -p babylon-circuit-worlds`. Expected: does
  not compile (no crate content).
- [ ] **Step 3: Implement** the crate, the four list edits and the lock.
- [ ] **Step 4: Run** the crate's tests, then the Python unit tests of the Global Constraints. Expected: all pass;
  `test_single_clippy_pass_preserves_the_existing_pedantic_package_boundary` passes with the new name.
- [ ] **Run the gate. Commit** `feat(circuit-worlds): a crate of small worlds with the doubled fund world`.

### Task 2: The runner, and the quiet world stays still

**Files:**
- Create: `src/runner.rs`, `src/runner/run.rs`, `src/runner/result.rs`, `src/runner/error.rs`, `tests/runner.rs`
  (all under `rust/crates/babylon-circuit-worlds/`).

**Interfaces:**

```rust
// src/runner/result.rs. All derive Debug, Clone, PartialEq, Eq.
pub struct PeriodResult {
    pub period: u64,
    pub figures: Figures,                      // the catalog's figures this period closed under
    pub receipts: PeriodReceipts,
    pub members: Vec<StaffingMemberReceipt>,   // from distribute_staffing_members; the transition's own is empty
    pub closing: Closing,
    pub summary: PeriodSummary,
    /// material_circuit_state_digest(the catalog this period closed under, the next state)
    pub state_digest: [u8; 32],
}
/// The receipts the scene reads, moved out of the MaterialCircuitTransition (all its fields are pub).
pub struct PeriodReceipts {
    pub member_labor_use: Vec<MemberLaborUseReceipt>, pub labor_use: Vec<LaborUseReceipt>,
    pub production: Vec<ProductionReceipt>, pub service_outputs: Vec<ServiceOutputReceipt>,
    pub service_performance: Vec<ServicePerformanceReceipt>, pub household_services: Vec<HouseholdServiceReceipt>,
    pub handling: Vec<MerchantHandlingReceipt>, pub local_transfers: Vec<LocalTransferReceipt>,
    pub local_fulfillments: Vec<LocalRetailFulfillmentReceipt>, pub procurement: Vec<ProcurementReceipt>,
    pub household_demand: Vec<HouseholdDemandReceipt>, pub household_consumption: Vec<HouseholdConsumptionReceipt>,
    pub money_transfers: Vec<MoneyTransferReceipt>, pub wage_accruals: Vec<WageAccrualReceipt>,
    pub taxes: Vec<TaxReceipt>, pub public_programs: Vec<PublicProgramReceipt>,
    pub public_budgets: Vec<PublicBudgetReceipt>, pub distributions: Vec<DistributionReceipt>,
    pub income: Vec<IncomeReceipt>, pub prices: Vec<PriceReceipt>, pub service_markets: Vec<ServiceMarketReceipt>,
    pub market_clearings: Vec<MarketClearingReceipt>,
}
/// Read from the next state before it is carried on.
pub struct Closing {
    pub cash: Vec<(AccountId, Currency)>,      // book.cash_accounts(), in the book's order
    pub capital: Vec<CapitalAccount>,          // costs.capital_accounts()
    pub ownership: Vec<OwnershipClaim>,        // financial.ownership
    pub households: Vec<HouseholdCohort>,      // recurring.households
    pub employed: [u64; 8], pub reserve: [u64; 8],   // the carried StaffingState, by Workplace::index
}
pub struct PeriodSummary {
    pub hours_attended: [u64; 8], pub made: [u64; 8], pub employed: [u64; 8],
    pub cash: Vec<(AccountId, i128)>, pub prices: Vec<(SiteId, GoodId, i128)>,  // posted offers at the close
    pub total_money: i128, pub persons: u64,
}
// src/runner/error.rs
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Stage { Close, StaffingRequests, AdvanceStaffing, DistributeMembers, Finish, Digest, Read }
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RunnerError {
    Engine { period: u64, stage: Stage, error: MaterialCircuitError },
    Staffing { period: u64, stage: Stage, error: StaffingError },
    World(WorldError),
    MoneyNotConserved { period: u64, opening: i128, closing: i128 },
    PersonsNotConserved { period: u64, opening: u64, closing: u64 },
    PastHorizon { period: u64 },
    Stopped,
}
impl Display for RunnerError; impl Error for RunnerError;
// src/runner/run.rs
pub struct Runner { /* private: base_state for start-over is not kept; see decision 5 */ }
impl Runner {
    pub fn open() -> Result<Self, RunnerError>;
    pub fn next_period(&self) -> u64;
    pub fn step(&mut self) -> Result<&PeriodResult, RunnerError>;
    pub fn history(&self) -> &[PeriodResult];
    pub fn stopped(&self) -> Option<&RunnerError>;
}
```

**Decisions:**
1. **One period is the engine's own,** in the order of the game branch's `run_staffed`
   (`babylon-material-circuit/tests/small_world/support.rs` 1406-1469): `close_material_period(&catalog, &state)`;
   `closed.staffing_requests(&catalog, &bindings)`; `advance_staffing(&staffing, &requests)`; for each
   `staffed.receipts()`, `distribute_staffing_members(receipt, &[member(w, receipt.opening_employed())?])`;
   `labor = staffed.next_labor().to_vec()`; `staffing = staffed.into_state()`; one `MemberLaborCapacityRow
   { member_id: w.member_id(), period: row.period, available_hours: row.available }` per labor row;
   `closed.finish_with_staffing(&catalog, labor, member_labor, &member_receipts)`. `finish_with_staffing` is the only
   finish the fund's after-layoff program admits. The runner carries `transition.state` and the `StaffingState`.
2. **The catalog of a period** is `catalog(&figures)` for the figures of that period (Task 3 makes them move; here
   always `Figures::OPENING`). The runner keeps one built catalog per distinct `Figures` it has seen, in a
   `BTreeMap`-free `Vec<(Figures, MaterialCatalog)>`, so a step does not rebuild an unchanged catalog.
3. **Checks after each finish:** `total_cash_and_reserves` of the next state equals `OPENING_MONEY`, else
   `MoneyNotConserved`; persons (the cohorts' sum) equal `PERSONS` and every pool's employed plus reserve equals its
   workers' persons, else `PersonsNotConserved`. A failed check is recorded like a refusal; the result is not kept.
4. **The horizon:** a step of period `p` with `p + 2 > HORIZON` is `PastHorizon { period: p }` (last period 998).
5. **A refusal stops the run.** The first error is kept (`stopped`) and every later `step` returns `Stopped`. Start
   over is a new `Runner::open()`; the client replaces its resource.
6. **What is kept:** every period's `PeriodResult`, never the state (one state holds about 8,000 capacity rows).
   `made` is units: the farm's `produced_batches` times that period's yield; the utility's and clinic's
   `ServiceOutputReceipt.produced_quantity`; the shop's `handled_quantity` summed over all
   its `MerchantHandlingReceipt`s (one an order, `model.rs` 405-412). If a service also has a
   `ProductionReceipt`, it is counted once, from `service_outputs`.
7. **The words** (`Display`): `Engine`: "Period {p}: the engine refused {stage}: {error:?} (code {error as u16})",
   stage words "the close", "the requests for staff", "the staffing", "the members' shares", "the finish", "the
   digest", "the reading"; `Staffing`: "Period {p}: {error}" (the engine's own "staffing refused: ..."); `World`:
   its own; `MoneyNotConserved`: "Period {p}: money is not conserved: {opening} millionths at the opening,
   {closing} now"; `PersonsNotConserved` likewise in persons; `PastHorizon`: "Period {p}: this test economy is built
   for 998 periods"; `Stopped`: "The run stopped at an earlier refusal. Start over to run again."

- [ ] **Step 1: Write the failing tests** in `tests/runner.rs`:
  - `the_quiet_world_stays_still_for_34_periods`: 34 steps all `Ok`; every `summary` equals period 1's; in each,
    `hours_attended` is [120, 40, 40, 40, 120, 40, 40, 40] (sum 480), `made` the same figures, `employed`
    [12, 4, 4, 4, 12, 4, 4, 4], `total_money` 12,240,000,000, `persons` 80.
  - `the_same_steps_give_the_same_bytes_twice`: two runners, 34 steps each: equal `state_digest` in every period
    and equal histories.
  - `the_runner_keeps_the_member_receipts`: period 1 has 8 member receipts, `opening_employed` 12 / 4 / 4 / 4 a
    place, and its `receipts.member_labor_use` has 8 rows whose payees are the 8 worker households.
  - `the_run_stops_at_its_horizon`: 998 steps `Ok`; the 999th is `PastHorizon { period: 999 }`; the next is
    `Stopped`; `history().len()` is 998 and `stopped()` is the first error.
  - `a_refusal_is_worded_as_the_engine_words_it`: the `Display` of `Engine { period: 7, stage: Stage::Close,
    error: MaterialCircuitError::PublicProgramInvariant }` is "Period 7: the engine refused the close:
    PublicProgramInvariant (code 39)".
- [ ] **Step 2: Run them and see them fail** (`-p babylon-circuit-worlds`): `Runner` not found.
- [ ] **Step 3: Implement.** If the quiet world is not still on the game's engine, stop and report the first period
  and figure that moved: it is a finding for the lead, not a figure to tune.
- [ ] **Step 4: Run them and see them pass.** Write the wall time of the 998-period test in your report.
- [ ] **Run the gate. Commit** `feat(circuit-worlds): step the doubled world by the engine's own period`.

### Task 3: The shocks

**Files:**
- Create: `src/shocks.rs`, `tests/shocks.rs`. Modify: `src/runner/run.rs`, `src/lib.rs` (under
  `rust/crates/babylon-circuit-worlds/`).

**Interfaces:**

```rust
// src/shocks.rs
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)] pub enum Shock { HarvestFails, PowerCut }
impl Shock {
    pub const ALL: [Shock; 2];
    pub const fn name(self) -> &'static str;     // "The harvest fails" | "The power is cut"
    pub const fn figure(self) -> &'static str;   // "a farm makes 9 food a batch, not 10"
                                                 // | "a utility makes 9 power for 10 hours, not 10"
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum Places { A, B, Both }
impl Places { pub fn places(self) -> Vec<Place>; pub const fn label(self) -> &'static str }
// labels: "Place A" | "Place B" | "both places"
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum Lasts { TenPeriods, UntilLifted }
impl Lasts { pub const fn label(self) -> &'static str }     // "for ten periods" | "until lifted"
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Strike { pub shock: Shock, pub place: Place, pub lasts: Lasts, pub from: u64, pub until: Option<u64> }
// `from`: the first period closed under the shock. `until`: the first period back at the opening's figure.
#[derive(Clone, Debug, Default, PartialEq, Eq)] pub struct ShockBook { /* private: Vec<Strike> in the order struck */ }
impl ShockBook {
    pub fn strikes(&self) -> &[Strike];
    pub fn holds(&self, shock: Shock, place: Place, period: u64) -> bool;
    pub fn figures(&self, period: u64) -> Figures;
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ShockError { AlreadyHolds { shock: Shock, place: Place }, NotHolding { shock: Shock, place: Place },
                      TenPeriodsOnlyForTheHarvest, HoldsUntilStartOver, Stopped }
// src/runner/run.rs, Runner gains:
pub fn strike(&mut self, shock: Shock, places: Places, lasts: Lasts) -> Result<(), ShockError>;
pub fn lift(&mut self, shock: Shock, place: Place) -> Result<(), ShockError>;
pub fn shocks(&self) -> &ShockBook;
```

**Decisions:**
1. **A shock is a figure of the catalog and nothing else.** The harvest: `farm_yield[place] = 9`, the
   `ProcessOutput.quantity_per_batch` of the farm's process. The power cut: `utility_hours_per_batch[place] = 10`
   and `utility_output_per_batch[place] = 9`, the utility's `LaborCoefficient` and `ProcessOutput`. Both edit the
   catalog's definition by process id and leave every id, row set and row order as they were (notes-world 3.3).
   The state is never touched.
2. **From the next period on.** A strike made when `next_period()` is `n` has `from = n`; the period that closed keeps
   its catalog. `TenPeriods` sets `until = Some(n + 10)` (periods `n` to `n + 9` poor, as the spike's
   `HARVEST_RETURNS = 11` for a strike before period 1). `lift` sets `until = Some(next_period())`; a strike whose
   `from` is the next period is removed instead (it never held). `Places::Both` makes one `Strike` a place, with
   the same `from`. A strike in a place where the same shock holds or is waiting is `AlreadyHolds`, and nothing of
   that call is struck; a lift where nothing holds is `NotHolding`; `TenPeriods` with the power cut is
   `TenPeriodsOnlyForTheHarvest`; a lift of the power cut is `HoldsUntilStartOver` (Departure 2), also when its
   strike has not yet held; any of them after a refusal is `Stopped`.
3. `ShockBook::figures(p)` starts from `Figures::OPENING` and applies every strike with `from <= p` and (`until`
   `None` or `p < until`). The runner calls it for each step and records the result in `PeriodResult.figures`.
4. **The power cut's first period** (Departure 2) is not smoothed, and the cut is never lifted. If the engine
   refuses a mid-run swap of the power cut, remove `PowerCut` from `Shock` and its tests, and report the refusal
   word for word to the lead.

- [ ] **Step 1: Write the failing tests** in `tests/shocks.rs`:
  - `the_harvest_fails_in_place_a_from_the_next_period`: step 1; strike `(HarvestFails, A, UntilLifted)`; period 1's
    `figures` are `OPENING`; step; period 2's `farm_yield` is [9, 10]; `made` farm A 36, farm B 40.
  - `a_ten_period_harvest_returns_on_the_eleventh`: step 2; strike `(HarvestFails, Places::A, TenPeriods)`; step 11;
    `farm_yield[0]` is 9 in periods 3 to 12 and 10 in period 13; the strike reads `from: 3, until: Some(13)`.
  - `money_and_people_stay_exact_under_every_shock_for_60_periods`: for each shock and each of A, B and both: strike
    after 4 steps (`UntilLifted`, never lifted); 60 steps, every one `Ok` (the runner's checks are the assertion).
    Pinned from the first run, by name: under the harvest in A, `history()[59].figures.farm_yield[0] == 9` and
    `history()[59].summary.made[Workplace { place: Place::A, kind: Kind::Farm }.index()]` equal to the value it gives
    (period 60); under the power cut in A, utility A's `summary.made` in periods 5, 6 and 60 (`history()[4]`, `[5]`,
    `[59]`): the first period of Departure 2 and what follows, as measured.
  - `a_harvest_lifted_returns_from_the_next_period`: the harvest in A `UntilLifted` after 4 steps, lifted after 20:
    `farm_yield[0]` is 9 in periods 5 to 20 and 10 from period 21; the strike reads `until: Some(21)`.
  - `a_strike_lifted_before_it_holds_changes_nothing`: two runners step 3; one strikes and lifts the harvest in A
    before stepping; both step 5 more; equal histories.
  - `the_same_shocked_steps_give_the_same_bytes_twice`: two runners, the harvest for ten periods in both places
    after 2 steps and the power cut in B after 6; 30 steps each; equal histories.
  - `a_shock_that_holds_is_refused_again`, `lifting_what_does_not_hold_is_refused`,
    `ten_periods_is_only_for_the_harvest`, `the_power_cut_holds_until_the_run_is_started_over`: the four
    `ShockError`s, and the book unchanged after each.
  - `a_shocked_catalog_differs_only_in_its_figure`: `catalog(&f)?.into_definition()` with the harvest in A equals
    the opening's with `process_outputs` of process 2 set back to 10; likewise the power cut in B with process 5's
    output and labor coefficient set back to 1.
- [ ] **Step 2: Run them and see them fail** (`-p babylon-circuit-worlds`): `Shock` not found.
- [ ] **Step 3: Implement**, run once for the pins of the 60-period test, write them in.
- [ ] **Step 4: Run** `mise run rust:test:q -- -p babylon-circuit-worlds`. Expected: all pass.
- [ ] **Run the gate. Commit** `feat(circuit-worlds): labelled shocks as figures of the catalog`.

### Task 4: The period read as hours, goods and payments, and the table

**Files:**
- Modify: `rust/crates/babylon-client/Cargo.toml` (`[dependencies]` gains `babylon-circuit-worlds = { path =
  "../babylon-circuit-worlds" }`); `rust/Cargo.lock` (offline, as Task 1); `src/lib.rs` (`pub mod small_world;`).
- Create: `src/small_world.rs` (`mod` and `pub use` only); `src/small_world/reading.rs`; `src/small_world/table.rs`,
  each with its tests.

**Interfaces:**

```rust
// src/small_world/reading.rs
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Party { Workplace(Workplace), Household(Household), Treasury, Fund }
impl Party { pub fn from_account(account: AccountId) -> Option<Party>; pub fn label(self) -> String }
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum PaymentKind { Wages, Purchases, Taxes, Benefits, Profit }   // ALL: [PaymentKind; 5]; label()
#[derive(Clone, Debug, PartialEq, Eq)] pub struct WorkFlow { pub household: Household, pub workplace: Workplace,
    pub given: u64, pub idle: u64 }   // given = production + handling + maintenance + installation hours
#[derive(Clone, Debug, PartialEq, Eq)] pub struct GoodsMove { pub good: Good, pub from: Party, pub to: Party,
    pub quantity: u64 }
#[derive(Clone, Debug, PartialEq, Eq)] pub struct Payment { pub kind: PaymentKind, pub payer: Party,
    pub payee: Party, pub amount: i128 }
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PeriodReading { pub period: u64, pub work: Vec<WorkFlow>, pub goods: Vec<GoodsMove>,
    pub payments: Vec<Payment> }      // each sorted by its fields' order
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ReadingError { UnknownParty(String), UnpairedPayment(String), UnexpectedPayment(String), Arithmetic }
pub fn read_period(result: &PeriodResult) -> Result<PeriodReading, ReadingError>;
// src/small_world/table.rs
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum Grouping { Workplace, Class, Place }  // default Workplace
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TableRow { pub label: String, pub members: usize, pub work_given: u64, pub paid_not_used: u64,
    pub money_in: i128, pub money_out: i128 }     // "stored work got back" is a column with no figure
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Table { pub grouping: Grouping, pub period: u64, pub rows: Vec<TableRow>,
    pub hours_scale: u64, pub money_scale: i128 }   // the largest hours figure; the largest money figure
pub const NOT_MEASURED: &str = "not measured yet";
pub fn table(reading: &PeriodReading, grouping: Grouping) -> Result<Table, ReadingError>;
```

**Decisions:**
1. **Work:** one `WorkFlow` per `MemberLaborUseReceipt` (payee to `Household`, site to `Workplace`). Its law
   (`payments/attendance.rs:96-101`) is attended = given + idle; a row that breaks it is `Arithmetic`.
2. **Goods:** `ServicePerformanceReceipt` (provider site to buyer, `performed_quantity`), `LocalTransferReceipt`
   (supplier to buyer site), `LocalRetailFulfillmentReceipt` (retailer to household). Rows of quantity 0 are dropped.
3. **Payments** from `money_transfers`: `WagePayment(s)` is a wage of the credit's amount, its payer the
   `Cash(site)` debited by `ShiftReservation(s)`; `DeliverySettlement(o)` is a purchase of the credit's amount, its
   payer the `Cash(buyer)` debited by `PurchaseReservation(o)`; `Cash(Tax)` taxes, `Cash(PublicTransfer)` benefits,
   `Cash(OwnershipDistribution)` profit, each with its two cash ends. Reservations, refunds and cancellations move
   money into and out of escrow and are not payments. A payment with no matching reservation is `UnpairedPayment`;
   any other `Cash(..)` purpose is `UnexpectedPayment` (the world has none); an account of no party is
   `UnknownParty`. Each error names the receipt with `{:?}`.
4. **The table.** By workplace: the 8 workplaces (work given and idle are the hours that reached it; money in is
   what it was paid, money out what it paid). By class: "Owners who earn" (no household in this world: `members` 0
   and zeros), "Owners who do not earn" (the owner households), "Earners who do not own" (the worker households),
   "Neither owner nor earner" (the supported households); for households, work given is the hours they gave. By
   place: "Place A", "Place B" (money: the sum of the rows of its workplaces and households; hours: the hours that
   reached its workplaces, counted once, since the same hours are the households' work given) and "Shared: treasury
   and fund". Apart from a place's hours, a group's sum is the sum of its members' own figures. The scales are the
   largest hours figure and the largest money figure among the rows shown: two scales, never one.

- [ ] **Step 1: Write the failing tests** (each from `Runner::open()` and one or two steps; money in millionths):
  - `every_payment_of_the_quiet_period_is_read_once`: period 1 has 8 wage payments summing 4,800,000,000;
    purchases summing 10,320,000,000; taxes 1,280,000,000; benefits 1,280,000,000; profit 1,280,000,000.
  - `the_quiet_period_gives_480_hours_and_no_idle_hour`: 8 work flows, given 120 / 40 / 40 / 40 a place, idle 0.
  - `goods_move_along_their_own_paths`: power: 16 moves summing 240 (utility to its farm 40, its clinic 40, each of
    its 6 households its persons); care: 12 moves summing 80; food: 14 moves summing 160 (2 farm-to-shop moves of
    40, one `LocalTransferReceipt` a place; 12 shop-to-household moves, of 12, 4, 4, 4, 8 and 8 in each place; no
    luxury food is bought in the quiet world, bench `fund-quiet.tsv` period 1 `want_luxury_bought` 0). No move
    between the places.
  - `a_workplace_pays_out_what_it_takes_in_a_still_world`: by workplace, Place A's utility, farm, clinic and shop
    take in $1,440 / $1,000 / $1,200 / $1,520 and pay out the same; work given 120 / 40 / 40 / 40.
  - `the_classes_and_places_sum_their_members`: by class: earners 8 members, work 480, in $4,800, out $4,800; owners
    who do not earn 2, in and out $1,280; neither 2, in and out $1,280; owners who earn 0 members and zeros. By
    place: Place A work 240, in and out $8,840; Place B the same; shared in $1,280, out $1,280.
  - `a_receipt_of_no_party_is_refused`: two altered copies of period 1's `PeriodResult`, each read on its own. In
    the first, the credit of one `WagePayment` transfer is moved to
    `MoneyLocation::Cash(AccountId::Household(FinalDemandPrincipalId::from_bytes([99; 32])))`: `UnknownParty`, whose
    words name that receipt. In the second, one transfer's purpose is `Cash(CashTransferPurpose::MutualAid)`:
    `UnexpectedPayment`. (The reading never reads `wage_accruals`, so an altered accrual would prove nothing.)
  The money figures are the opening's arithmetic (notes-world 1.4 and the bench's quiet rows, `wage_bill` 4,800,
  `taxes_collected` 1,280, `public_paid` 1,280). A figure the first run does not give is a finding to report, never
  bent.
- [ ] **Step 2: Run them and see them fail.** `mise run rust:test:q -- -p babylon-client -E 'test(small_world)'`.
- [ ] **Step 3: Implement.** **Step 4: Run them and see them pass.**
- [ ] **Run the gate. Commit** `feat(client): read the small world's period as hours, goods and payments`.

### Task 5: The library's pin and Bevy 0.20.1

**Files:**
- Modify: `rust/crates/babylon-graph/Cargo.toml` (line 17: `rev` becomes `LIBRARY_REV`; URL spelling and
  `default-features = false` unchanged); `rust/crates/babylon-client/Cargo.toml` (`bevy` `"0.20.0"` becomes
  `"0.20.1"`, features unchanged; gains `hypergraph-rs = { git = "https://github.com/percy-raskova/hypergraph-rs.git",
  rev = "LIBRARY_REV", default-features = false, features = ["geometry"] }` and `hypergraph-rs-bevy = { git =
  "https://github.com/percy-raskova/hypergraph-rs.git", rev = "LIBRARY_REV" }`); `rust/Cargo.lock`; the client's
  `src/small_world/frame.rs` (created here with one test only; Task 6 fills it).

`LIBRARY_REV` is given in this task's brief by the lead: a pushed commit of the library's branch `feat/bevy-crate`
that holds the mend named below. The pin is raised again when the library's own plan has closed (its tasks 12 and
13 and its loose ends) and when the Director has ordered its merge. On 2026-11-23 the library's frame-time
trial showed that plain marks, one entity a mark, are far over budget, so its Task 12 is built: with full motion the
marks of one stream are one mesh moved by a shader, and no entity carries `MarkOf` a mark. Tasks 6 to 9 read the
library's code at `LIBRARY_REV`, not this plan's memory of it. `LIBRARY_REV` also holds the library's mend of 23
November: a scene's first frame stands from its first beat (before it, the particles and sets of the first period
shown appeared only in its last beat, so the first marks flew to places where nothing stood).

**Decisions:**
1. **One revision for both packages,** or the lock holds two `hypergraph-rs` and their types do not match
   (notes-library 5.4). The bevy crate does not re-export `Positions`, `OutlineParams` or `Outline`, so the client
   names the core itself with `geometry`.
2. **The Bevy move and the lock:** edit the manifests (Bevy `"0.20.1"`, the two git lines), then from `rust/` one
   `mise exec -- cargo metadata --format-version 1 > /dev/null` (no `--offline`): it resolves, fetches the git
   revision and writes `rust/Cargo.lock` without a build, and the `bevy` 0.20.1 requirement moves the family. Do not
   pass several `-p` to `cargo update --precise` (cargo takes one package with `--precise`; from memory, not run).
   If Step 3's read shows a `bevy*` package still at 0.20.0, run `mise exec -- cargo update -p <it> --precise
   0.20.1`, one package a command. `mise run rust:lock-refresh` is `cargo build --workspace` (`.mise.toml`
   1080-1083), a full build that holds the machine's one build slot: not needed here. Cargo needs network access to
   github.com to fetch the revision; if `LIBRARY_REV` is not on GitHub, stop and tell the lead.
3. **The gates of dependencies:** `rust/deny.toml` allows the repository (line 74, `allow-git`) and the library's
   BSD-3-Clause; no edit. If `cargo-deny --log-level warn --manifest-path rust/Cargo.toml --all-features check
   advisories bans licenses sources` (the CI step, `ci.yml` 210-215) refuses a source, a licence or an advisory,
   stop: report to the lead and change no allow list. If `cargo-deny` is not installed here, say so; CI runs it.
4. Keep the dependency in `babylon-graph` with its URL spelled as today: `tests/unit/tools/test_repo_hygiene.py`
   (188-196) and `babylon-graph/tests/covenants.rs` (80-92) read that line.

- [ ] **Step 1: Write the failing test** in `src/small_world/frame.rs`: `the_library_plugin_runs_in_the_client`
  builds an `App` as the library's `tests/common/mod.rs` `field_app` does (`MinimalPlugins`,
  `AssetPlugin::default()`, `init_asset` of `Mesh`, `Image`, `StandardMaterial`, `TimeUpdateStrategy::ManualDuration`
  of 10 ms), adds `FieldPlugin::new(FieldConfig::three_beats(Duration::from_millis(1_000)), styles, palette)` with one
  particle style and one stream, writes one `ShowPeriod` of one particle and one flow, updates 3 times: no
  `FrameRefused`, `FlowReport.period` is `Some(1)`, one entity with `ParticleId("p")`.
- [ ] **Step 2: Run it and see it fail** (`-p babylon-client -E 'test(library_plugin)'`): no `hypergraph_rs_bevy`.
- [ ] **Step 3: Edit the manifests, move the lock** (decision 2). Check by reading `rust/Cargo.lock`: exactly one
  `name = "hypergraph-rs"` package, at `LIBRARY_REV`; one `hypergraph-rs-bevy`; every `bevy` and `bevy_*` package at
  0.20.1 but `bevy_mikktspace` 1.0.0; no `bevy*` 0.20.0 left (`rg -c 'version = "0.20.0"'` after each `bevy` name).
- [ ] **Step 4: Run** `mise run rust:test:q -- -p babylon-graph`, then `-p babylon-client`, then the scoped gate;
  `cargo-deny` as decision 3. Expected: every test of both crates passes on Bevy 0.20.1, the covenants included.
- [ ] **Run the gate** (with the Python unit tests: `test_repo_hygiene.py` reads the manifest). **Commit**
  `build(deps): pin the hypergraph library's Bevy crate and move Bevy to 0.20.1`.

### Task 6: The frame builder

**Files:**
- Create: `src/small_world/layout.rs` with its tests. Modify: `src/small_world/frame.rs` (under
  `rust/crates/babylon-client/`), `src/small_world.rs`.

**Interfaces:**

```rust
// src/small_world/layout.rs: every number of the scene's plane. Plan units; the scene is plan_to_scene(p, h).
pub const WORKPLACE_X: [f64; 8] = [-11.0, -8.2, -5.4, -2.6, 2.6, 5.4, 8.2, 11.0];   // by Workplace::index, y 0
pub const TREASURY_AT: Point = (-2.2, 11.2);  pub const FUND_AT: Point = (2.2, 11.2);
pub const WAGE_ANCHOR_Y: f64 = 3.3;      // a particle paid wages by a workplace leans to (x, 3.3): above it
pub const PROFIT_ANCHOR_Y: f64 = -2.4;   // a particle paid profit by a workplace leans to (x, -2.4): below it
pub const TREASURY_ANCHOR: Point = (-2.2, 8.3); pub const FUND_ANCHOR: Point = (2.2, 8.3);
pub const BENEFIT_LEAN: [f64; 2] = [-1.0, 1.0];   // a household paid benefits leans to its own place's side
pub const HOME: [Point; 2] = [(-7.0, 6.0), (7.0, 6.0)];   // where a group paid by nobody this period stands
pub const GROUP_SPREAD: (f64, u32) = (1.6, 8);  pub const PERSON_SPREAD: (f64, u32) = (0.4, 8); // min distance, steps
pub const SPREAD_BOUNDS: Rect = (-12.8, -4.2, 12.8, 12.6);
pub const PLANE: Rect = (-13.2, -4.6, 13.2, 13.1);   // what the view is fitted to: 26.4 wide, 17.7 deep
pub const PERSON_COLUMNS: usize = 4;  pub const PERSON_STEP: f64 = 0.45;   // a cluster of persons, rows going +y
// OutlineParams::new(reach, cell, share) of a workforce, an owner, the fund. An owner's workplaces stand 2.8
// apart: at a reach of 1.0 its set drew as five separate loops; at 2.3 it is one outline with no notch, inside
// the plane. The fund's reach is 1.3, clear of the fund's label.
pub const OUTLINE: [(f64, f64, f64); 3] = [(1.0, 0.2, 0.92), (2.3, 0.2, 0.92), (1.3, 0.2, 0.92)];
pub const PARTICLE_Y: f32 = 0.10; pub const MARK_Y: f32 = 0.15; pub const HOURS_RING_Y: f32 = 0.03;
pub const MONEY_RING_Y: f32 = 0.035; pub const SET_Y: [f32; 3] = [0.02, 0.04, 0.06]; // workforces, owners, fund
// src/small_world/frame.rs
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)] pub enum ParticleMode { #[default] Groups, People }
#[derive(Clone, Debug, PartialEq)]
pub struct BodyPicture { pub party: Party, pub id: String, pub at: Point, pub hours_ring: Option<f32>,
    pub money_ring: Option<f32>, pub made: Option<u64> }   // rings only on workplaces
#[derive(Debug, PartialEq)]   // no Clone: hypergraph_rs::Hypergraph has none (it has copy())
pub struct Picture { pub frame: FieldFrame, pub bodies: Vec<BodyPicture>, pub positions: Positions,
    pub sets: SetGraphs, pub reading: PeriodReading, pub mode: ParticleMode }
#[derive(Debug, PartialEq)]
pub struct SetGraphs { pub workforces: Hypergraph<(), (), u64>, pub owners: Hypergraph<(), (), i128>,
    pub fund: Hypergraph<(), (), i128> }
#[derive(Debug, Clone, PartialEq)]
pub enum FrameError { Reading(ReadingError), Field(FieldError), Geometry(GeometryError), Edge(String), Arithmetic }
pub fn build_picture(result: &PeriodResult, mode: ParticleMode) -> Result<Picture, FrameError>;
pub fn field_config() -> FieldConfig; pub fn field_styles() -> FieldStyles; pub fn field_palette() -> Palette;
pub const STREAM_WORK: u16 = 0; pub const STREAM_GOODS: [u16; 3] = [1, 2, 3];   // food, power, care
pub const STREAM_MONEY: [u16; 5] = [4, 5, 6, 7, 8];  // wages, purchases, taxes, benefits, profit
pub const HOURS_PER_MARK: u64 = 2; pub const UNITS_PER_MARK: u64 = 4; pub const MONEY_PER_MARK: u64 = 80_000_000;
```

**Decisions:**
1. **Ids.** Nodes: `"household:{byte}"`, `"person:{byte}:{k}"` (k from 0), `"workplace:{a|b}:{kind}"`,
   `"treasury"`, `"fund"`. Edges: `"workforce:{a|b}:{kind}"`, `"owner:{a|b}"`, `"fund"`. Particles carry node ids.
2. **Where a particle stands** (field design 6.7). A household group stands at `barycentre` of the anchors of the
   bodies that paid it this period (wages from a workplace at `(WORKPLACE_X, WAGE_ANCHOR_Y)`, profit from a
   workplace at `(WORKPLACE_X, PROFIT_ANCHOR_Y)`, benefits from the treasury and fund anchors), weighted by the
   money each paid it; a group paid by nobody stands at its place's `HOME`. So workers stand above their workplace
   and an owner below the four it holds. Then `spread` once over all groups with `GROUP_SPREAD` and
   `SPREAD_BOUNDS`, in `Household::ALL` order.
   People mode: a worker household's first `opening_employed` persons (its member receipt) cluster at its
   workplace's wage anchor; its other persons cluster at the group's point computed from its benefits alone, or
   `HOME`;
   owner and supported persons cluster at their group's point. A cluster of `n` puts person `k` at
   `(cx + (k % 4 - (min(n, 4) - 1) / 2) * 0.45, cy + (k / 4) * 0.45)`; then `spread` over all persons with
   `PERSON_SPREAD`. Money weights are dollars as `f64` (`micro_units as f64 / 1e6`, an allowed `cast_precision_loss`
   with a reason); no hour enters a position.
3. **Sets** (D7 of the brief), each by `add_node_to_edge_with_data`, then `set_frames` once per kind with its height
   and its own weight closure (`h as f64`; dollars as above), with that kind's `OUTLINE`:
   - A workforce: its workers' node (Groups) with the hours given to it this period, or (People) its persons in
     order, each at work given `HOURS_PER_PERSON` until the given hours run out, the next the rest, every other 0 (on
     the bench a clinic gave 2 hours with 4 employed: `fund-P2a.tsv` period 14, so the first person gets 2).
   - An owner: the owner's household (Groups) or each of its persons with an equal share (People; in millionths,
     the remainder to the first person), with its own book capital; and its four workplaces' body nodes, each with
     the capital the owner has in it: the workplace's `CapitalAccount` at the close
     (`opening_capital + contributed_capital + retained_earnings`) times the owner's
     `OwnershipClaim.shares` over the site's total shares. Negative capital counts 0.
   - The fund: every recipient of a `PublicProgramReceipt` whose `public_account` is the fund, with its `paid`; in
     People mode spread equally over the household's persons not at work (all its persons if none is out of work),
     in millionths, the remainder to the first of them.
   Zero members stay in the edge and are outside the outline (notes-library 2.5).
4. **Flows.** Work: from the household's point to the workplace's body; idle hours as a hollow flow ending at the
   body's edge (0.7 short of its centre, toward the household). Goods: hollow (ruling 18), one stream a good, from
   the seller's point to the buyer's. Money: one stream a kind, payer to payee. A household's point in People mode is
   the mean of its persons' points. Ends are `plan_to_scene(p, 0.15)`. Amounts are `u64` (money by `u64::try_from`).
5. **Rings** of a workplace: hours `0.42 + 0.22 * min(hours reached / 120, 2)` (reached: given and idle); money
   `0.52 + 0.22 * min(money in / $1,500, 2)`; `None` when the figure is 0. Two expressions, two constants, never
   one. Both stay inside an owner's outline, which passes about 1.5 from a workplace.
6. **Styles and palette.** Swatches: 0 `BONE`, 1 `CRIMSON`, 2 `GOLD`, 3 `DIM` (the client's `palette.rs`). A glyph's
   size is its radius in plan units. Particles: 0 a group of up to 4 persons (`Disc`, 0.30, swatch 0), 1 a person
   (`Disc`, 0.13, swatch 0), 2 a group of 5 to 8 (`Disc`, 0.42, swatch 0), 3 a group of 9 or more (`Disc`, 0.52,
   swatch 0): a dot's area tells its people. Sets: 0 workforce (swatch 0, line 0.05, hatch `Deg45` spacing 0.30
   width 0.025), 1 owner (swatch 2, line 0.056, hatch `Deg135` 0.42 / 0.025), 2 fund (swatch 2, line 0.056 dashed
   (0.28, 0.14), hatch `Deg0` 0.34 / 0.025). Streams: work (beat 0, unit `HOURS_PER_MARK`, `Disc` / `Ring`, size
   0.11, swatch 0); food, power, care (beat 1, unit `UNITS_PER_MARK`, `Square` / `SquareFrame`, 0.13, swatch 1);
   five money streams (beat 2, unit `MONEY_PER_MARK`, `Streak` / `Streak`, 0.34, swatch 2: a streak is a thin line
   and needs three times a disc's size to be seen); every stream `share_drawn` 0.95 (field design 6.2) and
   `max_marks` 300. Config: `FieldConfig::three_beats(Duration::from_millis(1_000))`. Ramp and no-reading colours
   are `DIM` (the scene has no ground). Every number of decisions 5 and 6 and of `layout.rs` was set by eye from a
   mock in the real renderer ("What the lead's look changed", below) and is tuned again from the real scene after
   Task 7.

- [ ] **Step 1: Write the failing tests** (quiet period 1, Groups, unless named):
  - `the_quiet_period_stands_by_its_ties`: 12 particles; each worker group at `(WORKPLACE_X[i], 3.3)`, style 3 for
    the two groups of 12 and style 0 for the six of 4; owner A at (-7.08, -2.4) and owner B at (6.52, -2.4)
    (profit 192 / 96 / 256 / 96 a place), style 2; the two supported groups (style 2) stand side by side, Place
    A's left of Place B's, 2.0 apart, with their midpoint at (1.1, 8.3) within 1e-9; `at` is
    `plan_to_scene(p, 0.10)`.
  - `an_owner_s_set_is_one_outline`: each owner's `SetFrame` has an outline of exactly one closed path that holds
    the plan points of its household and of its four workplaces (the fault the first numbers had: five loops).
  - `the_three_kinds_of_sets_are_real_hyperedges`: 11 sets: 8 workforces, each one member at 120 / 40 / 40 / 40
    hours with a `Ring` outline; 2 owners of 5 members (the household and its four workplaces), the workplaces'
    numbers their book capital at the close (expected $1,200 / $1,760 / $880 / $2,400 and the household $944, the
    opening's net assets; a difference is a finding to report); 1 fund set whose members above zero are the two
    supported households at $480 each, and the 8 worker households at 0.
  - `each_stream_draws_and_counts_exactly_its_own_total`: `select_flows(&frame.flows, &field_styles().streams)`:
    for every stream and variant, `drawn + not_drawn == total`, and the totals equal the reading's (work full 480,
    hollow 0; food, power, care hollow 160, 240, 80; money by kind 4,800 / 10,320 / 1,280 / 1,280 / 1,280 dollars in
    millionths). Work: drawn 480, 240 marks. Food: drawn 152, not drawn 8. Power: drawn 228, not drawn 12. Care: drawn
    76, not drawn 4. Every goods flow hollow; no full goods flow.
  - `people_stand_in_their_membranes`: People: 80 particles; workforce of utility A has 12 members at 10 hours; the
    fund set's members above zero are the 16 supported persons at $60 each.
  - `the_harvest_failed_in_a_shows_in_the_next_period`: strike the harvest in A after period 1; period 2's picture:
    farm A's body `made` is 36, farm B's 40; work total 480.
  - `the_same_steps_give_the_same_frames_twice`: 12 periods with the harvest in B for ten periods from period 3,
    in both modes, built twice: equal `Picture`s.
  - `the_plugin_accepts_every_quiet_frame`: the app of Task 5's test with `field_config()`, `field_styles()`,
    `field_palette()`; `ShowPeriod` of period 1's frame in each mode: no `FrameRefused`.
- [ ] **Step 2: Run them and see them fail** (`-p babylon-client -E 'test(small_world)'`).
- [ ] **Step 3: Implement.** **Step 4: Run them and see them pass.**
- [ ] **Run the gate. Commit** `feat(client): build the small world's picture from a period's result`.

### Task 7: The scene, its mode, its flag and its button

**Files:**
- Create: `src/small_world/scene.rs`, `src/small_world/controls.rs` (under `rust/crates/babylon-client/`).
- Modify: `src/cli.rs` (flag, `CliRequest::SmallWorld`, help); `src/main.rs`; `src/app.rs` (`AppMode::SmallWorld`,
  its branch); `src/observer_title.rs` (one `TitleAction`, one button); `src/observer_ui.rs` (`apply_fonts` becomes
  `pub(crate)`, nothing else); `src/small_world.rs`; `src/decision_surface.rs` (the sixth surface);
  `tests/decision_surface_contract.rs` (the closed set, Departure 5).

**Interfaces:**

```rust
// src/cli.rs
const SMALL_WORLD_FLAG: &str = "--small-world";
const SMALL_WORLD_SCRIPT_FLAG: &str = "--small-world-script";   // an absolute, normalized path (control_path's rule)
CliRequest::SmallWorld { script: Option<PathBuf> }
// src/app.rs
AppMode::SmallWorld { script: Option<PathBuf> }
// src/small_world/scene.rs
pub struct SmallWorldPlugin { pub script: Option<PathBuf> }
pub fn install_scene(app: &mut App, script: Option<PathBuf>) -> Result<(), String>; // all but Bevy's (decision 2)
#[derive(Resource)] pub struct SceneRunner { pub runner: Runner, pub mode: ParticleMode, pub shown: Option<u64> }
#[derive(Resource, Default, Clone, Debug, PartialEq, Eq)]
pub struct SceneStatus { pub playing: bool, pub refusal: Option<String> }
#[derive(Message, Clone, Debug, PartialEq, Eq)]
pub enum SceneCommand { Step, Play, Pause, Again, StartOver, Particles(ParticleMode), Marks(Motion),
    Strike(Shock, Places, Lasts), Lift(Shock, Place), Grouping(Grouping), TablePeriod(Option<u64>) }
#[derive(SystemSet, Debug, Clone, Copy, PartialEq, Eq, Hash)] pub enum SceneSet { Input, Run, Paint }
pub fn status_after(step: &Result<&PeriodResult, RunnerError>) -> SceneStatus;   // pure
pub const PLAY_INTERVAL: Duration = Duration::from_millis(3_500);
// src/observer_title.rs
TitleAction::SmallWorld        // caption "A test economy · the small world", after "Michigan · organizer control"
#[derive(Event, Clone, Copy, Debug)] pub(crate) struct OpenSmallWorld;   // an Event, as ContinueTitle (line 53)
pub(crate) struct TitleInput<'w, 's> { /* the four fields as today, plus */ world: Commands<'w, 's> }
#[derive(Resource, Default)] pub(crate) struct SmallWorldProcess { child: Option<Child>, failure: Option<String> }
pub(crate) fn small_world_command(exe: &Path) -> Command;   // exe --small-world, stdin/stdout/stderr null
// src/decision_surface.rs
SurfaceId::SmallWorld          // Display "small-world"; `ALL` becomes `[Self; 6]`, the new one last
// its manifest row: admin_surface(SurfaceId::SmallWorld, SMALL_WORLD_SIGNALS, SMALL_WORLD_UNCERTAINTY)
const SMALL_WORLD_SIGNALS: &[&str] = &["the test economy's workplaces, household groups and sets",
    "the work, goods and payments of the period shown", "the shocks struck and when"];
const SMALL_WORLD_UNCERTAINTY: &[&str] = &["the hours stored in goods are not measured here"];
```

**Decisions:**
1. **The flag.** `--small-world` alone, or with `--small-world-script <abs path>`. With `--campaign`,
   `--new-campaign`, `--preset`, `--headless`, `--qualification-control` or a bare word it is refused, worded as the
   other refusals at `cli.rs` 327-345 with `concat!(file!(), ":", line!())`. `--small-world-script` without
   `--small-world` is refused. Parsed before `windowed_target`, which needs a campaign. `TOP_LEVEL_HELP` gains one
   line: "--small-world  open a test economy in this window; not Wayne, not saved".
2. **The composition** (`build_app`'s new branch) is exactly three things: `DefaultPlugins` with the same
   `LogPlugin` and a `WindowPlugin` of 1366 x 768, centred, title "Babylon — a test economy",
   `close_when_requested` left at its default (true): no observer handles a close here; then
   `install_window_camera_coherence(&mut app)` (`app.rs` 190-211, as the windowed observer calls it: the scene has a
   viewport camera and a UI camera in a window that can be resized; its one qualification system,
   `observe_window_after_last`, returns at once without `Controls`); then `install_scene(&mut app, script)?`.
   `install_scene` adds everything else: `VisualAssetsPlugin` (fonts), `apply_fonts` in `PostUpdate`
   `.before(UiSystems::Content)` as `ObserverShellPlugin` schedules it, `MeshPickingPlugin` (only if not yet
   added, as `observer_map3d.rs` 822-823), `FieldPlugin::new(field_config(), field_styles(), field_palette())`
   with its `FieldError` mapped to the `String` refusal "the scene's field refused its styles: {error:?}",
   `ClearColor(FIELD)`, and the scene's own resources and systems. So a test of `install_scene` covers every plugin
   the branch adds beyond Bevy's own and the camera coherence. It adds none of
   `ObserverIoPlugin`, `CampaignBrowserPlugin`, `OrganizerPlugin`, `ProductionPlugin`, `ObserverMap3dPlugin`,
   `ObserverHistoryPlugin`, `DossierCardPlugin`, `ObserverShellPlugin`, `OpeningPlugin`, `ObserverWarningPlugin`,
   `SessionLogPlugin`, `ObserverAudioPlugin`, `ObserverPerformancePlugin`, `ObserverFocusPlugin`, and no session,
   pipe or reader: `start_pipe` never runs and `LAUNCHER_REQUIRED` cannot show.
3. **The button.** `TitleAction::SmallWorld` is visible on the title's home page and enabled unless a quit is
   asked (its arm in `action_enabled` after the `quit_requested` check). `TitleInput::activate` fires it with
   `self.world.trigger(OpenSmallWorld)`; `TitleInput` gains the one `Commands` field and the lifetime `'s`
   (`impl TitleInput<'_, '_>`). `OpenSmallWorld` is an `Event`, not a `Message`, so the bare test apps of
   `observer_title.rs` (580-602 and 650-680), which register only `ObserverCommand` and add `focused_action`, still
   validate `TitleInput`, and a trigger with no observer does nothing there: no existing test changes.
   `ObserverTitlePlugin::build` adds `init_resource::<SmallWorldProcess>()`, an observer on `On<OpenSmallWorld>`
   that spawns `small_world_command(current_exe()?)` and keeps the `Child`, and a system in `ObserverSet::Input`
   that reaps it each frame with `try_wait`. A spawn that fails keeps "The test economy could not start: {error}" in
   `SmallWorldProcess.failure`; `paint` (which rewrites the `TitleStatus` text every frame, 501-525) takes
   `Option<Res<SmallWorldProcess>>` and shows that failure when its own caption is empty. The observer, its pipe and
   its window are untouched.
4. **Order in `Update`:** `SceneSet::Input` (buttons, script) then `SceneSet::Run` (one command at a time on the
   `Runner`; a step builds the picture and writes `ShowPeriod`), `.before(FieldSystems::Install)`; `SceneSet::Paint`
   (labels, rings, panels) `.after(FieldSystems::Animate)`.
5. **Commands.** `Step`: `runner.step()`, then `build_picture` and `ShowPeriod`; `status_after` sets `refusal` to
   the error's `Display` and stops play. `Play` shows the next period at once and then one every
   `PLAY_INTERVAL` of `Time` (three beats of 1 s and half a second at rest) until `Pause` or a refusal. `Again`
   writes `ReplayPeriod`. `StartOver` replaces the runner with `Runner::open()`, clears `refusal`, despawns nothing
   of the library's (the next `ShowPeriod` replaces it) and shows no period until the next step. A frame the
   library refuses (`FrameRefused`) is shown as the refusal too, in its own words, and stops play. `Particles` and
   `Marks` (Task 8) rebuild the shown period's picture.
6. **Camera and bodies.** One `Camera3d`, order 0, no `RenderLayers` (layer 0, where the library's entities are),
   looking straight down with no perspective: `Transform::from_translation(m + Vec3::Y * 40.0).looking_at(m,
   Vec3::NEG_Z)`, `m` the middle of `PLANE` in the scene, and `Projection::Orthographic` with
   `ScalingMode::AutoMin { min_width: 26.4, min_height: 17.7 }` (`PLANE`'s size), so the whole plane shows at any
   window shape and a disc stays round; `Tonemapping::None` (the palette's colours reach the screen as they are, and
   it needs no LUT), `Msaa::Sample4`, viewport x 0 to width - 400,
   y 48 to height - 72 (logical px times the window's scale factor), set by a system from the primary window
   whenever its size or scale changes; with no primary window (the headless tests) that system does nothing and the
   viewport stays `None`. One `Camera2d`, order 10,
   `ClearColorConfig::None`, `IsDefaultUiCamera`, `RenderLayers::layer(31)`. A body is flat, unlit and in the
   palette: a workplace is a centre disc (`Circle` of radius 0.2, `GOLD`, at `plan_to_scene(at, 0.05)`) with its two
   rings; the treasury and the fund are the library's `glyph_mesh(Glyph::SquareFrame, 16)` scaled 0.6, `GOLD`, with
   the same centre disc. Under each body lies its pick plate, a `Circle` of radius 0.95 in `FIELD` at height 0.01:
   that is what a click on a body hits. The plate carries `SceneBody(pub Party)` (a `Component`); the centre disc,
   the frame and the rings are its children. Rings: `outline_paths` of `Outline::Ring` (48 segments), the hours ring
   `dashed(.., Some((0.18, 0.12)))` `ribbon_mesh` width 0.055 of `BONE`, the money ring solid width 0.055 of `GOLD`,
   at their heights; redrawn when a picture is shown.
   Marks, path lines and rings get `Pickable::IGNORE` (an observer on `Add` of `MarkOf`, of
   `PathLines` and of whatever component the library's one-mesh marks of a stream carry at `LIBRARY_REV`: read its
   `src/plugin/marks.rs` there); bodies, particles and set meshes stay pickable.
8. **The surface** (Departure 5). Every entity of the scene with a `Text`, an `ImageNode`, a `Mesh2d` or a `Mesh3d`
   carries `DeclaredSurface::new(SurfaceId::SmallWorld)`: the scene's own entities where they are spawned, and the
   library's (it knows nothing of the client) by one observer on `Add` of `Mesh3d` that the scene installs, which
   inserts the marker on any mesh entity that has none. In `tests/decision_surface_contract.rs`,
   `every_shipped_visual_entity_declares_a_manifest_surface` keeps its five for the observer's composition, drops
   the line that equates the observer's set with `SurfaceId::ALL`, builds the scene's composition beside it (the
   headless base of this task's `scene_app`, written out in the test file, then `install_scene`, one `Step` and
   three updates), asserts that its visual surface ids are exactly `SmallWorld` by the same `visual_surface_ids`
   (which fails on any undeclared visual entity), and asserts that the two sets together equal `SurfaceId::ALL`.
   Every other test of that file passes unchanged; if another one counts the surfaces, give it the sixth and say so
   in the report.
7. **Words and layout** (logical px at 1366 x 768, `observer_theme` colours, `ObserverFontRole` faces). Header: top,
   height 48, full width, `PANEL`, padding 16: "ADMIN · MATERIAL TRUTH · UNFOGGED" (Display 20, `RED`), under it
   "A test economy. Not Wayne. Not saved." (Body 14, `PAPER`); at the right "Period {n}" (Display 20, `PAPER`), and
   "Playing" or "Stopped by the engine" (Body 14). Control bar: bottom, height 72, `PANEL`, padding 8, two rows of
   32 with a gap of 8; buttons height 28, min width 96, border 1 `PAPER`, Body 14, gap 8: row 1 "Step", "Play" /
   "Pause", "Again", "Start over" (row 2 and the right rail are Task 8's). A refusal is a banner at the top of the
   viewport (x 16, y 56, width viewport - 32, `PANEL`, border 2 `RED`, Body 14 `PAPER`) with the error's words; while
   it shows, Step and Play are disabled. Body labels: Body 12 `PAPER` on a plate of `FIELD` at 0.82 (so a
   label reads over a hatch), centred under the body, 10 px below the projected lowest point of its outer ring or of
   its frame (`Camera::world_to_viewport`), text `Party::label`. Standing line at the viewport's bottom left (x 16,
   8 above the control bar, Body 13 `PAPER`): "Place A and Place B are copies of one test economy, not real places."
   While no period has been shown, a second line in the middle of the viewport (Body 14 `PAPER`): "Nothing has run
   yet. Press Step."

- [ ] **Step 1: Write the failing tests:**
  - In `cli.rs`'s tests: `the_small_world_flag_opens_a_test_economy` (`--small-world` gives `SmallWorld { script:
    None }`; with `--small-world-script /abs/run.jsonl`, `Some`); `the_small_world_refuses_a_campaign` (with each of
    the five other flags: `Err`); `a_script_needs_the_small_world` and `a_relative_script_is_refused`.
  - In `scene.rs`, every test on one helper `scene_app(script: Option<PathBuf>)`: `MinimalPlugins`,
    `AssetPlugin::default()`, `ImagePlugin::default()`, `TextPlugin`, `TexturePlugin` (the headless base of
    `visual_assets/plugin.rs` 458-465), `init_asset` of `Mesh` and `StandardMaterial`,
    `TimeUpdateStrategy::ManualDuration` of 10 ms, then `install_scene(&mut app, script)` (no `FieldPlugin` of its
    own: `install_scene` adds it, and a second would panic).
    If `MeshPickingPlugin` needs Bevy's picking plugins headless, `scene_app` adds the ones its panic names (not
    run). Tasks 8 and 9 use the same helper.
    `the_small_world_composition_has_no_campaign_session` (no `ObserverSession`, no `RuntimePipe`; `is_plugin_added`
    false for every plugin decision 2 names; `FieldPlugin` and `VisualAssetsPlugin` added; `SceneRunner` present at
    period 1); `a_step_shows_the_next_period`
    (one `Step`, 3 updates: history 1, `FlowReport.period` `Some(1)`); `again_replays_without_stepping`;
    `start_over_rebuilds_the_opening` (3 steps and a strike, then `StartOver`: history 0, no strike, next period 1);
    `play_steps_at_once_and_then_on_its_timer` (`Play`: 1 period at once; 3.5 s of manual time on: 2; 7.0 s: 3;
    `Pause`: no more); `the_window_can_open_on_its_first_period` (with `open_on_first_period`: nothing and no
    "press Step" line at 0.5 s, period 1 once after 1.5 s, not playing; a run started over waits and says so);
    `a_refusal_is_shown_in_the_engine_s_words` (`status_after(&Err(RunnerError::PastHorizon { period: 999 }))` has
    `refusal` "Period 999: this test economy is built for 998 periods" and `playing` false);
    `the_unfogged_words_are_on_screen` (the header's two `Text`s read exactly as decision 7 has them);
    `an_empty_scene_says_so` (before any step the line "Nothing has run yet. Press Step." is on screen; after one
    `Step` it is gone; after `StartOver` it is back);
    `every_visual_entity_of_the_scene_declares_the_small_world` (one `Step`, 3 updates: every entity with a `Text`,
    an `ImageNode`, a `Mesh2d` or a `Mesh3d` has `DeclaredSurface { id: SurfaceId::SmallWorld }`, the library's
    particles, sets and marks among them).
  - In `decision_surface.rs`'s tests or the contract test, wherever the manifest's rows are checked today: the new
    row validates, is `AdminDebug`, and does not satisfy the gameplay gate.
  - In `observer_title.rs`'s tests: `the_title_offers_the_small_world` (the bare app of 580-602, plus an observer on
    `On<OpenSmallWorld>` that counts into a test resource; `ObserverKeyboardActivate` on the `TitleAction::SmallWorld`
    entity: the count is 1 and `Messages<ObserverCommand>` is empty); `the_small_world_starts_as_its_own_process`
    (`small_world_command(Path::new("/x/b"))` has program `/x/b` and args `["--small-world"]`).
- [ ] **Step 2: Run them and see them fail** (`-p babylon-client -E 'test(small_world)'`).
- [ ] **Step 3: Implement.** **Step 4: Run** `mise run rust:test:q -- -p babylon-client`: every existing test passes
  unchanged but the one edit of decision 8 in `decision_surface_contract`.
- [ ] **Run the gate. Commit** `feat(client): a scene of the small world, opened by a flag or from the title`.
- [ ] **Step 6 (the lead's, not the builder's): look.** The lead runs the real client with `--small-world`, steps
  three periods, captures the client's own window in each beat and in People mode, and puts the captures beside the
  mock's. The lead then tunes `layout.rs` and decisions 5 and 6 of Task 6 by eye, decides whether the scene should
  play its first period by itself when it opens, and shows the Director the pictures. Task 8 starts after this.

### Task 8: Shocks, the particle switch, the table and what a pick shows

**Files:**
- Create: `src/small_world/panel.rs`, `src/small_world/inspect.rs`. Modify: `src/small_world/controls.rs`,
  `src/small_world/scene.rs`, `src/small_world.rs` (under `rust/crates/babylon-client/`).

**Interfaces:**

```rust
// src/small_world/inspect.rs
#[derive(Clone, Debug, PartialEq, Eq)] pub enum Pick { Body(Party), Particle(String), Set(String) }
#[derive(Resource, Clone, Debug, Default, PartialEq, Eq)] pub struct ScenePick(pub Option<Pick>);
pub fn inspect(picture: &Picture, result: &PeriodResult, pick: &Pick) -> Result<Vec<(String, String)>, FrameError>;
// src/small_world/panel.rs
#[derive(Resource, Clone, Debug, PartialEq, Eq)]
pub struct PanelView { pub grouping: Grouping, pub period: Option<u64> }
pub fn shock_rows(book: &ShockBook, next_period: u64) -> Vec<ShockRow>;    // pure
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ShockRow { pub text: String, pub holding: bool, pub lift: Option<(Shock, Place)> }
pub fn not_drawn_line(report: &FlowReport) -> String;                      // pure
```

**Decisions:**
1. **Shock controls** (control bar, row 2): for each `Shock`, a tag "SHOCK" (Display 14, `RED`), the shock's name,
   its figure (Body 14), then place buttons "Place A", "Place B", "Both", then for the harvest "for ten periods" and
   "until lifted", then "Strike". The choices are held in a resource until "Strike" writes
   `SceneCommand::Strike`. A refused strike shows the `ShockError` under the row for 4 s: "Already holds in Place
   A", "Nothing to lift in Place B", "Ten periods is only for the harvest", "A power cut holds until you start
   over".
2. **The list of what was struck** (right rail, last section, title "Shocks"): one row a `Strike`, in the order
   struck: "SHOCK · The harvest fails in Place A · a farm makes 9 food a batch, not 10 · from period 3" and then
   "· until period 13", "· lifted at period 20", or "· holds" with a "Lift" button while it holds or waits. A power
   cut's row ends "· holds until you start over" and has no "Lift" button (Departure 2); under the power cut's
   controls a standing line says: "A power cut changes the size of a batch, so it holds until you start over."
3. **The particle switch** (row 1, after "Start over"): "Household groups" and "People", the shown one marked by a
   `YELLOW` left border of 3 px; default "Household groups". While "People" shows, a standing line: "One dot is one
   person. The record counts people; it does not follow a person, and the people of one group share one purse."
4. **Marks** (row 1, last): "Moving" and "Still", setting `FieldConfig.motion` to `Motion::Full` or
   `Motion::Reduced`.
5. **Standing lines** (with Task 7's): "One dot: 2 hours of work. One square: 4 units of a good. One streak: $80.
   Hours and money are two scales." (its three figures are built from `HOURS_PER_MARK`, `UNITS_PER_MARK` and
   `MONEY_PER_MARK`, not written out; the look of 23 November changed them from 10, 4 and $40, and this sentence
   had kept the old ones); "A hollow dot: hours paid and not used."; "Goods are drawn hollow: the hours
   stored in goods are not measured here until this world runs on the tick's records."; "An outline holds nine
   tenths of its set's number."; and `not_drawn_line`: "Not drawn: {h} hours; food {f}, power {p}, care {c} units;
   wages ${w}, purchases ${u}, taxes ${t}, benefits ${b}, profit ${r}", every figure from `FlowReport`, hours and
   units by `human_numbers::grouped` (it takes `u128`: widen with `u128::from`), money by `human_numbers::currency`
   (`i128` millionths); both are `pub(crate)`, which the client's own module may call.
6. **The table** (right rail, top; rail x width - 400 to width, y 48 to height - 72, `PANEL`, padding 12): three
   tabs "By workplace", "By class", "By place" (height 28); a pager "‹", "Period {n}", "›", "Latest" over the kept
   history; columns "Work given", "Paid, not used", "Stored work got back", "Money in", "Money out"; rows height 22,
   label Body 13, figures Exact 13 (`grouped` for hours, `currency` for money); "Stored work got back" reads
   `NOT_MEASURED` in every row. Under the hours figures a bar of height 6 in `BONE`, width `value / hours_scale` of
   the column; under the money figures a bar in `GOLD`, width `value / money_scale`. The two scales never meet.
7. **Picking.** A click (`PointerClick`, primary button) on a body (`SceneBody`), a particle (`ParticleId`) or a set
   (`SetId` on the entity or its `ChildOf` parent) sets `ScenePick`; a click on empty space clears it. The inspector
   (right rail, middle, title the pick's label) shows `inspect`'s rows for the shown period:
   - a workplace: hours given to it, paid not used, workers employed and in reserve (its member receipt), made,
     money in and out by kind, cash at the close, posted price; the treasury or fund: money in and out by kind,
     cash at the close;
   - a household group: persons, at work, hours given, money in by kind, money out by kind, cash at the close; a
     person: "one person of {group}" and the group's rows;
   - a set: its kind, each member above zero with its number (hours, or dollars), `held_share` as a percentage.
8. **History.** The pager changes only the table and the inspector; the scene shows the latest period.

- [ ] **Step 1: Write the failing tests:**
  - `shock_rows_tell_what_was_struck_and_when`: a book with the harvest in A for ten periods from 3 and the power cut
    in B from 6, at next period 12: two rows, texts as decision 2; the first is holding and has a lift; the second
    is holding, ends "· holds until you start over" and has no lift.
  - `a_strike_from_the_controls_holds_from_the_next_period` (`scene_app(None)`: one step, choose harvest, Place A, until
    lifted, Strike: the runner's book has `from: 2`; one step more: period 2's `figures.farm_yield` [9, 10]).
  - `the_particle_switch_shows_people`: after one step, `Particles(People)`: the next `ShowPeriod` has 80 particles,
    and the people line shows; back to groups: 12.
  - `the_table_switches_its_grouping_and_period` (two steps; "By class" then "‹": the rows are period 1's class rows
    of Task 4).
  - `a_pick_shows_its_own_figures`: trigger `PointerClick` on farm A's body: the inspector reads "Hours given" 40,
    "Made" 40; on the particle "household:13": "Persons" 4; on a child mesh of the set `"workforce:a:farm"`: one
    member at 40 hours, held 100 %.
  - `not_drawn_line_prints_the_report`: the quiet period's report gives "Not drawn: 0 hours; food 8, power 12, care
    4 units; wages $0.00, " and then the other four money figures as the first run gives them, pinned.
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement.** **Step 4: Run them and see them pass.**
- [ ] **Run the gate. Commit** `feat(client): shocks, people, the table and what a pick shows in the small world`.

### Task 9: Drive the real client by script, keep a picture, measure the frame time

**Files:**
- Create: `src/small_world/script.rs`, `src/small_world/frame_time.rs` (under `rust/crates/babylon-client/`).
- Modify: `src/small_world/scene.rs`, `src/small_world.rs`; `.mise.toml` (one task); `README.md` and
  `docs/agents/commands.md` (one line each, beside `mise run play`).

**Interfaces:**

```rust
// src/small_world/script.rs
#[derive(Deserialize, Clone, Debug, PartialEq, Eq)] #[serde(rename_all = "snake_case", deny_unknown_fields)]
pub enum ScriptCommand { Step(u32), Strike { shock: String, places: String, lasts: String },
    Lift { shock: String, place: String }, Particles(String), Capture(String), Report(String), WaitFrames(u32), Quit }
pub fn parse_script(text: &str) -> Result<Vec<ScriptCommand>, ScriptError>;   // one JSON value a line
#[derive(Debug, Clone, PartialEq, Eq)] pub enum ScriptError { Line { line: usize, reason: String } }
#[derive(Serialize, Clone, Debug, PartialEq)]
pub struct ScriptReport { pub period: u64, pub hours_given: Vec<(String, Vec<u64>)>, pub made: Vec<(String, Vec<u64>)>,
    pub shocks: Vec<String>, pub frame: Option<FrameTime>, pub refusal: Option<String> }  // per workplace, per period
// src/small_world/frame_time.rs
#[derive(Serialize, Clone, Copy, Debug, PartialEq)]
pub struct FrameTime { pub median_ms: f64, pub p95_ms: f64, pub window: usize }
#[derive(Resource)]
pub struct SceneFrameTimes { /* FrameWindows::new(300, Duration::from_secs(2)); last: Option<FrameTime> */ }
pub fn frame_time(stats: &WindowStats) -> FrameTime;   // milliseconds, window 300
```

**Decisions:**
1. **The script is a file** given by `--small-world-script`; the socket channel of `--qualification-control` is bound
   to a campaign, a tick and a closed `Action` enum, and is not used. Shock, place and lasts names: `harvest_fails`,
   `power_cut`; `a`, `b`, `both`; `ten_periods`, `until_lifted`. Particles: `groups`, `people`. A parse failure
   refuses the whole file before the window opens (`build_app` returns the error; `main` exits 2).
2. **Running it.** One command at a time, the next only when the library's `BeatClock` phase is `Resting` and no
   step is pending: each command writes the same `SceneCommand` a button writes. `Step(n)` is n steps, each waiting
   for rest. After each command one line is appended to `replies.jsonl` in the script's folder: `{"line": k,
   "event": "done"}` or `{"line": k, "event": "refused", "reason": "..."}`. A refusal of the engine ends the script:
   the report is written with `refusal`, then the app exits with `AppExit::Error(2)`.
3. **Pictures.** `Capture(name)` writes `<script folder>/<name>.png`, opened with `create_new` (an existing file is a
   refusal), from `Screenshot::primary_window()` and a `ScreenshotCaptured` observer that saves
   `try_into_dynamic()?.to_rgb8()` as PNG: the shape of `organizer/qualification_input.rs` `request_frame`
   (1465-1492). The reply waits for the file.
4. **Reports.** `Report(name)` writes `<name>.json` (`serde_json::to_string_pretty`): every kept period's hours
   given and made by workplace label, the shock rows' texts, the last `FrameTime` and the refusal.
5. **Frame time.** In `Last`, push `Time<Real>::delta()` into `FrameWindows` while the primary window has focus; on
   each full window log `frame_perf view=small_world mode={groups|people} period={n} median_ms={:.3} p95_ms={:.3}`
   with `log::info!` (the client's log file) and keep it as `last`. `WaitFrames(n)` waits n frames.
6. **One command for a person** (the lead's addition of 23 November): a mise task `play:small-world`, described
   "Open the small test economy in the client: not Wayne, not saved (ADR320)", that runs the client with
   `--small-world` from `rust/` through the managed cargo, with `--locked`, as the repository's other cargo tasks
   are written. It takes no arguments and starts no runtime and no database. `README.md` and
   `docs/agents/commands.md` gain one line each beside `mise run play`. The Python unit tests of the Global
   Constraints read `.mise.toml`: run them, and give them whatever they ask of a new task (a description, a row in
   a list of tasks), reporting each edit.
7. **The proof script** (`proof.jsonl`): `{"step":1}`, `{"strike":{"shock":"harvest_fails","places":"a",
   "lasts":"ten_periods"}}`, `{"step":10}`, `{"capture":"after-ten"}`, `{"report":"after-ten"}`,
   `{"wait_frames":600}`, `{"report":"frame-time"}`, `"quit"`. The check (Departure 3): in `after-ten.json`, farm A
   makes 36 in periods 2 to 11 and farm B 40; every workplace's hours in A and in B are written into the task's
   report as the client gave them, and the first period, if any, where a workplace of A attended fewer hours than
   its twin in B.

- [ ] **Step 1: Write the failing tests:** `the_script_reads_one_command_a_line` (the proof script parses to 8
  commands); `an_unknown_command_refuses_the_whole_script` (`{"jump":1}` on line 3 is `Line { line: 3, .. }`);
  `a_script_presses_the_same_controls` (`scene_app(Some(path))` with a two-line script `{"step":1}` and the strike:
  after enough updates the runner has 1 period and the strike, and `replies.jsonl` in a temporary folder has two "done"
  lines); `a_capture_is_saved_as_a_png` (trigger `ScreenshotCaptured` by hand with a 2 x 2 image, as
  `qualification_input.rs` 3479-3512 does: the file exists and is 2 x 2);
  `the_scene_times_its_frames_as_the_client_does`
  (`frame_time` of the `WindowStats` that 300 intervals of 10 ms give after the settle: median 10.0, p95 10.0, window
  300).
- [ ] **Step 2: Run them and see them fail.** **Step 3: Implement.** **Step 4: Run them and see them pass.**
- [ ] **Step 5: Run the real client** on this machine's display, once, from `rust/`, with a folder made by
  `mktemp -d` holding `proof.jsonl`: `mise exec -- cargo run -p babylon-client -- --small-world
  --small-world-script <folder>/proof.jsonl`. Read `after-ten.json` and `frame-time.json`; look at `after-ten.png`.
  If no display is available (no `DISPLAY` or `WAYLAND_DISPLAY`, or the window fails to open), do not try another
  way: hand the lead the exact command above and the proof script, and say so in your report. Then run
  `mise run play:small-world` once, see the window open, and close it.
- [ ] **Step 6: Report** the check of decision 7, the picture's path, and the frame time (median and p95, window of
  300, mode, period) with the window's size.
- [ ] **Run the gate. Commit** `feat(client): drive the small world by script, keep its picture, time its frames`.

## Self-review notes

- **The design's section 7, line by line:** stillness for 34 periods (Task 2,
  `the_quiet_world_stays_still_for_34_periods`); every shock in one place and in both for 60 periods (Task 3,
  `money_and_people_stay_exact_under_every_shock_for_60_periods`; two shocks, Departure 1); exact figures of the
  quiet first period, drawn plus not drawn equal to the period's own (Task 6,
  `each_stream_draws_and_counts_exactly_its_own_total`, on Task 4's totals); the same frames twice (Task 6, and the
  bytes in Tasks 2 and 3); the real client driven by script with a picture kept (Task 9 steps 5 and 6, the check
  changed by Departure 3); the frame time stated (Task 9 step 6).
- **The brief:** D2 in Tasks 1 to 3; D3 in Task 2; D4 in Task 5, after four tasks that need no library; D5 and D6
  in Task 6; D7 in Task 6 decision 3; D8 in Tasks 6 and 8; D9 in Tasks 7 and 8; D10 in Task 9; D11 in the Global
  Constraints.
- **Names across tasks:** `Workplace`, `Household`, `Place`, `Good`, `Figures` (Task 1); `PeriodResult`,
  `RunnerError` (2); `Shock`, `Places`, `Lasts`, `ShockBook` (3); `PeriodReading`, `Party`, `Grouping`, `Table` (4);
  `Picture`, `ParticleMode`, `FrameError`, `field_styles` (6); `SceneCommand`, `SceneRunner`, `SceneStatus` (7).
  Each is defined once, in the task that names it in its Interfaces.
- **What the closest form's plan inherits:** its Task 1 takes the doubled world from this crate, but this crate
  holds only the fund world at fixed small figures, as free functions, with `HORIZON` 1,000. The plain world, the
  national figures, the opening pushes and the bench's 402-period horizon are not here. It inherits the identities,
  the fund world and the runner's loop, and little else.
- **Outside D1:** nothing is built of the closest form, the bridge, the tick, persistence, stored views or saved
  campaigns. The engine is not changed (no constructor or accessor was found missing: notes-world 1.8 and 5h). The
  engine's own small world is not moved. Existing screens gain one title button; `apply_fonts` becomes `pub(crate)`.
- **First to fail, because only read:** the doubled treasury under `CashInProportion` (Task 1); stillness on the
  game's engine (Task 2); the mid-run power cut (Task 3); the owner sets' capital figures (Task 6); the library on
  Rust 1.99.1 and the Bevy lock move (Task 5).

## What the lead's look changed (23 November 2026)

On 23 November the Director watched the hypergraph library's timing example open and called it bizarre. It was:
ten tasks had been built and reviewed and nobody had looked at the window. So before Task 6 fixed this scene's
numbers in code, the lead drew its layout, view and sizes with the real renderer (a throwaway example beside the
library's own, never committed) and looked.

With the numbers this plan first had:

- The picture was a thin band in the middle of the window, under a slanted view that skewed every box.
- The bodies were dark blue-grey boxes on the red-black field, inside rings that overlapped their neighbours.
- The marks of all three beats were too small to see. A streak of size 0.10 is under one pixel wide.
- An owner's set drew as five separate loops, one a member, because its members stand 3 apart and a member's
  reach was 1. It tied nothing together.

What changed, in Tasks 5, 6 and 7 above:

1. The view looks straight down with no perspective and is fitted to the plane. The picture fills the viewport.
2. The two places stand apart: 5 between them, 3 between workplaces. The treasury and the fund stand together at
   the top.
3. Workers stand above their workplace and an owner below the four it holds. Wages and profit lean to different
   anchors. An owner's outline has a reach of 2.2 and is one outline round its four workplaces.
4. A body is a gold centre disc with its rings, not a box. The rings are smaller and stay inside the owner's
   outline. The treasury and the fund are gold frames.
5. A group's dot grows with its people.
6. Marks are larger, and a streak is three times a disc. One mark is 2 hours or 80 dollars, so the three beats of
   a quiet period carry about the same number of marks.
7. A body's label sits on a plate of the field's colour.
8. The library showed the first period's dots only in its last beat. That is mended there before this scene pins
   it.

The mock's source and its captures are kept in the lead's session folder, not in the repository.

### The second look, at the real window (after Task 7)

The lead ran the real client with `--small-world`, captured its window in each beat and in the People view, and put
the captures beside the mock's. The scene matched the mock in its parts and its sizes. What was changed by eye, in
the commit after Task 7's:

- **The households the fund pays stand side by side.** Both places' supported households are paid alike, so they
  stood on one point, the spread parted them on a slant, and their outline covered the fund's label. A household
  paid benefits now leans 1.0 to its own place's side (`BENEFIT_LEAN`), and the fund's outline has a reach of 1.3.
- **An owner's outline had a notch** beside its weakest workplace, and at a larger reach it ran past the plane's
  edge. The workplaces now stand 2.8 apart (`WORKPLACE_X`), the owner's reach is 2.3 and profit leans to y -2.4.
- **Play shows the next period at once,** then one every `PLAY_INTERVAL`. Before, a press of Play showed nothing
  for 3.5 s.
- **The window opens on its first period.** `open_on_first_period` shows period 1 once, 1.5 s after the scene
  opens (`OPENING_DELAY`). In its first moments a window draws nothing of the plane, and a period begun at once
  lost its first beat. The line "Nothing has run yet" is left out while that period is pending. A run started over
  waits for the player's step, as before. A scripted run (`--small-world-script`) opens on nothing: its script
  starts the run.
- **Accepted as built:** the header's padding is 16 across and 2 down (16 all round does not hold two lines in 48
  px); a frame the library refuses reads "Period {p}: the picture was refused: {error}".
- **For Task 8:** the scene's command handler has an arm that does nothing for `Particles`, `Marks`, `Strike`,
  `Lift`, `Grouping` and `TablePeriod`; Task 8 fills it. The right 400 px of the window stay empty until Task 8's
  rail. The lead looks again when the rail and the controls are in, before the six rules get their switches.

The Director saw the captures the same afternoon and answered "Yes, go on" (ADR321, K4): the look stands.

The Director saw the mock's pictures that morning and answered three questions (ADR320, S2, S8 and S9): the look
is the one to build; the scene opens on household groups; and after this plan the six rules of the closest form
are built, each with its own switch in this scene, before the bridge.

## The lead's answers to the plan's questions (23 November 2026)

1. **The surface** (Departure 5): the scene is declared as a sixth surface, and the contract's closed set gains
   it on purpose. A rule that every shipped visual belongs to a declared surface is not kept by building the
   scene where the test does not look.
2. **The library's revision** (Task 5): named when Task 5 starts, after the library's own plan has closed. The
   frame-time trial of 23 November sent the library to its Task 12 (marks moved by one shader a stream).
3. **The power cut** (Departure 2): it is offered, it is never lifted in this build, and the scene says why.
4. **A command for a person** (Task 9): `mise run play:small-world`.
5. **Two shocks, not four** (Departure 1): pay at the clinic and the fund's taxes live in the state, so by the
   design's own rule they are left out. The two that remain are the two the Director named.

## What the check changed

- Task 4 `a_receipt_of_no_party_is_refused`: alters a `WagePayment` credit (which the reading reads), not a wage
  accrual (which it never reads); the `MutualAid` transfer is a second, separate copy.
- Task 4 `goods_move_along_their_own_paths`: food is 14 moves summing 160 (2 farm to shop of 40; 12 shop to
  household of 12, 4, 4, 4, 8, 8 a place), not 16.
- Task 7: `OpenSmallWorld` is an `Event` fired by a `Commands` added to `TitleInput`, observed in
  `ObserverTitlePlugin`; no existing title test changes; the Task 7 test observes the event.
- Task 7: a spawn failure is kept in `SmallWorldProcess` and shown by `paint`, which rewrites `TitleStatus` each frame.
- Task 7: `build_app`'s branch is `DefaultPlugins`, `install_window_camera_coherence` and `install_scene`; all else is
  in `install_scene`, so its test covers the branch; one `scene_app(script)` helper with no second `FieldPlugin`.
- Task 7: `FieldPlugin::new`'s `FieldError` maps to the `String` refusal; the viewport is `None` without a window.
- Task 6: `Picture` and `SetGraphs` drop `Clone` (`Hypergraph` has none).
- Task 6: People mode has remainder rules: hours fill persons 10 at a time, the next gets the rest; money's remainder
  in millionths goes to the first person.
- Task 5: the lock moves by one `cargo metadata` after the manifest edit; no multi-package `--precise`; no
  `rust:lock-refresh` (a full build).
- Task 3: the 60-period pins are named by index and field; the harvest's `Lasts` is stated.
- Task 2: `made` of a shop sums `handled_quantity` over its receipts; the digest names its catalog.
- Task 1: the manifest takes `version`, `edition`, `rust-version` and `license` from the workspace.
- Task 8: `grouped` takes `u128`; hours are widened with `u128::from`.
- Departure 5 states that the passing surface test is no answer; the Global Constraints cite `3b0b02383`.
- Self-review: one line on what the closest form's plan inherits from this crate, and what it does not.
