# Babylon Gameplay Vision & Late-Empire Collapse Implementation Plan (Post-PER-354)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (with `model: "deepseek/deepseek-flash#high"`) to implement this plan task-by-task in waves once `PER-354` (embedded SQLite campaign owner) lands. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Babylon's ratified Porch 01 + Porch 02 gameplay design into the Rust runtime and Bevy client—delivering the 6-screen interface (Topology, Electoral, Physical Map, Ticker, Wiki, Line/Doctrine), the 3-resource Vanguard Economy, the state-snapshot `33/33/33/0` wealth and Imperial Rent ($\Phi$) differential equations, the 15-cell Caesarist/Bonapartist State Automaton (including NSA, CIA, and the fractal Department of War across National Guard / Reserves / Active Duty), Dual Power, and the 20-year (260-period) Vanguard Party clock.

**Architecture:** All mechanical judgment lives in deterministic integer/fixed-point Rust (`babylon-kernel`, `babylon-graph`, `babylon-material-circuit`, `babylon-bsl`, `babylon-tick`, `babylon-persistence`, `babylon-client`) backed by the single-owner embedded SQLite 3.53.1 campaign store (`ADR287`). Non-player state agencies, corporate blocs, and military sub-cells execute as synchronous `BTreeMap`-ordered cellular automata (`Capacity::allocate` over each cell's private belief `Dossier` $L_c$ and nested fiscal pool). The LLM (`Liberated Signal`, `Corporate Feed`, `Wiki/Chronicle`) holds god-mode read permissions fenced by the player's `acquired_period` knowledge boundary and markdown-only write permissions.

**Tech Stack:** Rust 1.91.1 (`babylon-kernel`, `babylon-graph`, `babylon-material-circuit`, `babylon-bsl`, `babylon-tick`, `babylon-persistence`, `babylon-client`), SQLite `3.53.1`, Python 3.12.14 offline reference-artifact extractors (`tools/`), `cargo-nextest`, `bsl-lint google-rust-style`.

**Spec:** `docs/gameplay/2026-10-25-porch-01.md`, `docs/gameplay/2026-10-25-porch-02.md`, and `docs/gameplay/research/01`–`25`.

## Global Constraints

- **Subagent Model Mandate:** Dispatch all implementer and reviewer subagents with `model: "deepseek/deepseek-flash#high"` (DeepSeek V4.1 Flash 1017). Never dispatch expensive frontier models as subagents.
- **Theoretical & Constitutional Guardrails (`CONSTITUTION.md` v4.3.0):**
  - **No Trotsky:** Trotskyism is modeled strictly as an opportunist/wrecker (`ProtestCircuitTrotskyist`) or class-reductionist ("workers unite") failure trap, never as a source of mechanics.
  - **Canonical *Michael Scott Communism* Lexicon (`/home/user/Documents/substack/The Topology of Dialectics - Michael Scott Communism.pdf`):** Screen 6 (Line/Doctrine), Wiki Vigilance Case Files, and Decision Ceremonies must use the canonical terms **`Michael Scott Communism`** (*"I DECLARE REVOLUTION!"*, the 3 substitutions: declaration for practice / *The News Herald Tribune Gazette Drop*, personality for organization / *Charismatic Guruism — "Tony Soprano with a Longer Reading List"*, spectatorship for participation / *"Fuck a Social Media. It's Narcissism Fuel" + NSPM-7*), **`KKKommunities of KKKare`** & **`"Just Rally the Folx" Akkktivist Subkkkulture`**, **`The Queer Qlux Qlan` (`QQQ`)**, and **`The Magical Power of Pancakes`** (*"Replaced the Guru with a Nonprofit Executive Director"*).
  - **No Magic Constants or Sigmoids:** Every rate of change $\Delta y / \Delta t$ and leverage weight is a ratio or coupled difference equation over the live period-$t$ integer snapshot or an offline-extracted empirical table (`Observed` / `Derived` / `Calibrated` from `/media/user/data/babylon-data/`). S-curves emerge from integrating within-class distributions against thresholds (`ADR173`).
  - **Mao Treatise Visibility Rule:** Never display internal engine multipliers, probabilities, `heat` floats, or `legitimacy` scalars on player surfaces. Show only countable world-facts (members, votes, dollars, hours, arrests, shipments) and named qualitative states (`holds / dislodged / broken`). Enemy formulas appear only inside leaked SOP documents in the Wiki.
  - **LLM Fence:** The LLM describes and never modifies (`markdown-only writes`). All narrator frames are filtered through the player's `(graph, intel_ledger, knowledge_seq, veil_tier)` serialization boundary before reaching the model or template renderer.
- **Google Rust Style (`PER-350`):** Obey `docs/agents/rust-style.md` (`EXC-01` to `EXC-05`): no `mod.rs`, module-qualified free function calls, no new `Arc`/`Rc`, no `.unwrap()`, pass `cargo run -p bsl-lint --locked -- all`.

## Review Focus

- **Unindexed spontaneity & analog edges leaking into `L_NSA` / `L_FBI`:** A spontaneous mass event with no `Organization` node (February 1917) or an edge with `EdgeMedium::Courier | FaceToFace` must never enter `L_NSA` (`ceiling = 0.00`) or generate a `Candidate` for `Capacity::allocate`.
- **Conservation of $\Phi$ and Active Duty garrisons across the external boundary:** Reassigning an `ActiveDuty` brigade from `ExternalGarrison` to `DomesticSiege` must reduce external enforcement and $\Phi$ inflow in the same period without creating or destroying manpower or money (`I1`–`I6` identities in `research/15`).
- **False-positive / Desert dossier masking (`M_r < 0.2`):** Querying a `Desert` territory with an active cadre report or a CIA/FBI-compromised node must return deterministic, plausible masked values (`Suburban Ambush`) without leaking the true state in the serialized `PlayerQuery` payload.
- **20-Year (260-period) Party Clock & Minsk 1898 / Michael Scott false start:** Calling `constitute_party()` without all 4 constitutional assets must produce the `PaperPartyMinsk1898` (*Michael Scott Communism: "I DECLARE REVOLUTION!"*) state without starting the 260-period clock; calling it with all 4 assets + Key B recognition starts the 260-period `survival_interest` clock and records `PartyCalcifiedFailure` at `t_constituted + 260` without halting the campaign loop.
- **Constant-capital ($K$) destruction colliding Finance-Capital against the Department of War:** High-CDE `AirGospel` or `GroundManeuver` strikes in an urban county must deduct from county constant capital $K$ and real-estate collateral in `MaterialCircuitState`, causing the `FinanceCapital` faction cell to withdraw credit/support from `SecurityState` in the next period's appropriation settlement.
- **George Jackson "Life Raft" Bifurcation & Warlord Flip (`research/20`):** Squeezed $C_{pb}/C_{la}$ cohorts default to `DsaSocialFascistBuffer` and `FascistMilitia` when $\mathrm{LR} = 0$, and flip to the player's Base Area iff $\mathrm{LR}\cdot O > R \cdot \#\{i : w_i + \max(b_i^{\text{DSA}}, b_i^{\text{Militia}}) \ge s_i\}$ with $S > 0$ (survived a State/militia strike). County Warlord Trajectory activates iff `captive_revenue > tax_revenue`.
- **Carceral Pipeline & `PrisonAdmin` Partial Derivative (`research/22`):** Street arrests must route through County Jail / Bail / DA Charging into rural `Prison` nodes (`fact_coercive_infrastructure`) without invoking `territory/p4-penal-suppression`'s per-tick organization zeroing, and `PrisonAdmin` must price `GangAssassination` ("getting merked"), `NarcoticsRot`, and `InformantFlipOnRelease` via $\partial B_{\text{prison}} / \partial \text{Assaults} = \gamma > 0$ until countered by `PrisonSolidarityPact`.
- **False Summits (`AOC Presidency` & `RED_OGV` Red-Settler Trap, `research/24`):** Winning the federal executive without smashing the state forces the closed four-payer fiscal fork (Social-Imperialist Navy deployment to preserve $\Phi$ vs. Caesarist `autonomy(c) > 0.40` coup), and winning insurrection with observed `extraction_intensity > 1/60` triggers `FalseSummitRedSettler` (New Afrika/Aztlán/Indigenous secession + `max-biocapacity` ratchet decay).

---

## Execution Waves Overview

- **Wave 1 (Empirical Reference Extractors & Zero-Magic-Number State Tables — Tasks 1–2):** Extract `< 1 MB` fixed-point tables from `/media/user/data/babylon-data/` (`piketty/` WID + FRED `33/33/33/0` flow matrix, Hickel/Ricci $\Phi$, CCC repression regimes, ATUS/QCEW/LODES 168-hour exhaustion, and the Trade Blocs + China/Russia/Iran/Israel counterpart table) and wire the 7 coupled difference equations (`research/13`–`15`).
- **Wave 2 (Epistemic Boundary: Two-Stroke Maturity, Lying Dossiers & The Three-Author Narrator — Tasks 3–4):** Wire Study (conceptual veil tiers) vs. Practice/Investigation (graph population), Desert/informant dossier masking, and the fenced `Corporate Feed` / `Liberated Signal` / `Intel Stream` + Wiki vigilance case files.
- **Wave 3 (The 15-Cell Bonapartist Automaton: Local PD, FBI, NSA, CIA & Fractal Department of War — Tasks 5–7):** Activate `babylon-graph`'s `capacity/dossier/exposure/backfire/induced` estate across the 12 municipal/state/federal cells + **NSA** (`EdgeMedium` digital panopticon + parallel construction) + **CIA** (`GladioFalseFlag`, `ContraFlood`, `CulturalFront`, `DeniableLiquidation`) + **US Department of War** (`NationalGuard` / `Reserves` / `ActiveDuty` + `AirGospel` / `GroundManeuver` / `Jsoc` / `DefensePrimes` + Finance-vs-Pentagon $K$-destruction fracture).
- **Wave 4 (Vanguard Economy, Dialectical Node Physics, Dual Power & The 260-Period Party Clock — Tasks 8–9):** Wire the 3 resources (`CadreLabor`, `Money`, `SupporterLabor`), node internal contradictions (`Shift / Split / Flip`), `Divide` & `Blockade` verbs, the Two-Key Party Lock (`Minsk 1898` vs. `Prague 1912`), the 260-period `survival_interest` clock, and Dual Power (QRF + Goods test).
- **Wave 5 (The Six Screens & Split-Pane Decision Ceremony in Bevy — Tasks 10–11):** Wire the 6 canonical screens (**Topology**, **Electoral**, **Physical Map**, **Ticker**, **Wiki**, **Line/Doctrine**) and the HOI4-style split-pane **Decision Ceremony** (`Seal -> Reckoning -> Long Tail`) in `babylon-client`.

---

### Task 1 (`W1a`): Offline Empirical Table Extractor (`33/33/33/0` Wealth Flow, $\Phi$, ATUS/LODES Exhaustion & Trade Blocs + China/Russia/Iran/Israel)

**Files:**
- Create: `tools/extract_gameplay_reference_tables.py`
- Modify: `tools/build_reference_db.py`
- Test: `tests/unit/reference/test_gameplay_reference_tables.py`

**Interfaces:**
- Consumes: `/media/user/data/babylon-data/` (`sqlite/marxist-data-3NF.sqlite`, `piketty/`, `babylon_hickel_final.csv`, `babylon_ricci_final.csv`, `ccc_protests/`, `atus/seed_data.yaml`)
- Produces: Deterministic, hash-pinned integer tables in the reference artifact: `wealth_flow_quarters` (59 transitions × 4 classes reproducing the `32.6% / 34.5% / 29.3% / 3.6%` flow shares and `90.1 / 8.3 / 1.6` inversion), `household_exhaustion_baseline` ($E = (T_{\text{wage}} + T_{\text{repro}} + T_{\text{commute}})/168$), and `external_counterpart_profiles` (the Regional Trade Blocs + standalone **China**, **Russia**, **Iran**, and **Israel** with `ColonialFranchise` dependency edge to US).

- [ ] **Step 1.1: Write the failing test in `tests/unit/reference/test_gameplay_reference_tables.py`** asserting that:
  1. `invert_wealth_to_population` on the extracted 2024Q4 knots equals `(9018, 825, 157)` in basis points (`90.18% / 8.25% / 1.57%`).
  2. All wealth flow rows conserve $\sum_i \Delta W_i = \Delta W_{\text{total}}$ with zero negative-$\Phi$ counties.
  3. The external counterpart table contains standalone entries for `china`, `russia`, `iran`, and `israel` (with `israel.parent_metropole == "US"` and `role == "settler_colonial_franchise"`).
- [ ] **Step 1.2: Run `mise run test:q -- tests/unit/reference/test_gameplay_reference_tables.py` and verify it fails.**
- [ ] **Step 1.3: Implement `tools/extract_gameplay_reference_tables.py`** using integer parts-per-billion / basis-point arithmetic (fixing the 5 heap defects noted in `research/13` §5.3 and `research/14` §6).
- [ ] **Step 1.4: Re-run the test and `mise run check` to verify green.**

---

### Task 2 (`W1b`): Coupled State-Snapshot Difference Equations in `babylon-material-circuit` & `babylon-bsl`

**Files:**
- Create: `rust/crates/babylon-material-circuit/src/wealth_dynamics.rs`
- Create: `rust/crates/babylon-material-circuit/src/imperial_rent_residual.rs`
- Modify: `rust/crates/babylon-material-circuit/src/lib.rs`
- Test: `rust/crates/babylon-material-circuit/src/wealth_dynamics_tests.rs`

**Interfaces:**
- Consumes: `MaterialCatalog`, `MaterialCircuitState`, `RoutedFreightLot`, `OwnershipClaim`
- Produces:
  - `wealth_dynamics::step_period(catalog: &MaterialCatalog, state: &mut MaterialCircuitState) -> WealthPeriodReceipt` (computing $q_t = K_t/V_t$, $e_t = s_t/V_t$, $r_t = e_t/(q_t+1)$, real vs. fictitious valuation $V^{\text{fic}}/V^{\text{real}}$, household exhaustion $E_t$, and both distribution-measure cuts: subsistence $P(S\mid A)_t = \frac{1}{N}\sum \mathbf{1}[w_i \ge s_i]$ and MIM labor-aristocracy share $a_t = \frac{1}{N}\sum \mathbf{1}[w_i > v_i]$).
  - `imperial_rent_residual::compute_period_phi(state: &MaterialCircuitState) -> PhiResidualReceipt` (enforcing identities `I1`–`I6` from `research/15` §7).

- [ ] **Step 2.1: Write failing unit tests in `wealth_dynamics_tests.rs`** verifying:
  1. Zero `sigmoid` or `f64` calls exist; both $P(S\mid A)$ and labor-aristocracy share $a_t$ are computed by exact integer CDF fold over `F_t(w)`.
  2. A pure valuation shock ($\Delta \rho < 0$ with $V^{\text{real}}$ constant) snaps back within 3 periods on liquidity restoration, while a real flow shock shifts the 90–99% bracket permanently (`research/13` §1.2, §3.5).
  3. $\Phi_{\text{core}} + \sum \Phi_{\text{counterpart}} == 0$ (exact conservation).
- [ ] **Step 2.2: Run `cargo test -p babylon-material-circuit --locked` and verify failure.**
- [ ] **Step 2.3: Implement `wealth_dynamics.rs` and `imperial_rent_residual.rs`.**
- [ ] **Step 2.4: Verify `cargo test -p babylon-material-circuit --locked` and `cargo run -p bsl-lint --locked -- all` pass.**

---

### Task 3 (`W2`): Two-Stroke Epistemic Veil (*On Practice*) & Lying Dossiers (`Desert` / Informant Masking)

**Files:**
- Create: `rust/crates/babylon-persistence/src/sqlite_store/epistemic_fence.rs`
- Modify: `rust/crates/babylon-persistence/src/sqlite_store/query.rs`
- Test: `rust/crates/babylon-persistence/src/sqlite_store/epistemic_fence_tests.rs`

**Interfaces:**
- Consumes: `PlayerQuery`, `Dossier`, `knowledge_grant` (`observed_period`, `acquired_period`)
- Produces: `epistemic_fence::project_player_view(store: &SqliteCampaignStore, period: PeriodId, knowledge_seq: u64) -> FencedPlayerView` enforcing:
  1. **Conceptual Veil (Indirect Experience / Study):** `VeilTier::T0PricesOnly`, `T1ExploitationVisible`, `T2MarketScissors`, and `PoliticalMaturityTier::LiberalFiction` vs. `StructuralStateView`.
  2. **Spatial & Relational Fog (Direct Experience / Practice):**
     - No contact $\rightarrow$ `FieldState::HonestUnknown { investigate_hint }`.
     - Contact in `Desert` ($M_r < 2000\text{ bps}$) or via a node with an active `Malinovsky` / `CIA` informant edge $\rightarrow$ `FieldState::ApparentValue(masked_value)` (renders indistinguishable from solid `Water` text on the client while storing the true value only in engine state!).

- [ ] **Step 3.1: Write failing tests in `epistemic_fence_tests.rs`** for (a) *The Suburban Ambush* (`M_r = 45 bps` returns calm `agitation = 1000 bps` when true agitation is `9000 bps` with an active militia), (b) backdated knowledge (`observed_period = 4, acquired_period = 9` is invisible at `period = 4` query), and (c) `LiberalFiction` hiding $\Theta$ threads behind generic police compliance text until `Study` unlocks `StructuralStateView`.
- [ ] **Step 3.2: Implement `epistemic_fence.rs` and wire into `query.rs`.**
- [ ] **Step 3.3: Verify tests and `bsl-lint` pass.**

---

### Task 4 (`W3a`): The 14-Cell Caesarist / Bonapartist State Automaton (`Local PD`, `Sheriff`, `Fusion`, `FBI`, `NSA`, `CIA`)

**Files:**
- Create: `rust/crates/babylon-graph/src/bonapartist_automaton.rs`
- Create: `rust/crates/babylon-graph/src/intelligence_triad.rs`
- Modify: `rust/crates/babylon-graph/src/lib.rs`
- Test: `rust/crates/babylon-graph/src/bonapartist_automaton_tests.rs`

**Interfaces:**
- Consumes: `capacity::Capacity`, `dossier::Dossier`, `exposure::decapitation_value`, `backfire::Backfire`, `induced::co_projected_peers`
- Produces:
  - `EdgeMedium { Digital, FinancialWire, Courier, FaceToFace, Printed }`
  - `AgencyCellKind` (the 12 cells of `research/17` §4.7 + `NsaSignals` + `CiaClandestine`)
  - `bonapartist_automaton::step_all_cells(cells: &mut BTreeMap<NodeId, AgencyCell>, pools: &mut BTreeMap<FiscalPoolId, FiscalPool>, graph: &MemoryGraph, rng_seed: u64) -> AutomatonPeriodReport`

- [ ] **Step 4.1: Write failing tests in `bonapartist_automaton_tests.rs`** proving:
  1. **Disagreement on belief (`RED` test from `17` §4.10):** Given different dossiers $L_{\text{PD}}$ and $L_{\text{FBI}}$ over the same true graph, `CityPd` and `FbiFieldOffice` rank different targets first, and `FbiFieldOffice` withholds `Malinovsky` nodes from `CityPd`.
  2. **NSA digital panopticon vs. analog blindness:** `NsaSignals` resolves 95% of `EdgeMedium::Digital` edges nationwide, resolves **0%** of `EdgeMedium::Courier | FaceToFace` edges, has zero kinetic candidates in its mandate, and emits `ParallelConstructionReferral` (without provenance) to `FbiFieldOffice`.
  3. **CIA dirty repertoire & Hoover–Dulles collision:** `CiaClandestine` prices `GladioFalseFlag`, `ContraFlood`, `CulturalFront`, and `DeniableLiquidation`; if `FbiFieldOffice` or player `Investigate` resolves a CIA domestic cutout edge, `ChurchCommitteeCrisis` fires and freezes the CIA's domestic mandate.
  4. **February 1917 (`candidates ⊆ L`):** A territory spontaneous upsurge with no `Organization` node in $L_c$ generates zero candidates for `CityPd`, `FbiFieldOffice`, `NsaSignals`, and `CiaClandestine`.
  5. **Bonapartist fiscal emergence:** Shrinking a `FiscalPool` during crisis cuts service-keyed shares and raises `threat_keyed_share`, pushing `autonomy(c)` above `4000 bps` with no scripted event.
- [ ] **Step 4.2: Implement `bonapartist_automaton.rs` and `intelligence_triad.rs`.**
- [ ] **Step 4.3: Verify `cargo test -p babylon-graph --locked` and `bsl-lint` pass.**

---

### Task 5 (`W3b`): The US Department of War Fractal Meta-Cell (`Guard / Reserves / Active Duty` + `Gaza-in-Chicago` Fracture)

**Files:**
- Create: `rust/crates/babylon-graph/src/department_of_war.rs`
- Modify: `rust/crates/babylon-material-circuit/src/recurring/firms.rs`
- Test: `rust/crates/babylon-graph/src/department_of_war_tests.rs`

**Interfaces:**
- Consumes: `AgencyCell`, `CorridorCapacity`, `MaterialCircuitState`, `ForeignCounterpart`
- Produces:
  - `ManpowerTier { NationalGuard { title_10_federalized: GuardControl }, Reserves, ActiveDuty }`
  - `PentagonSubCell { AirGospelCommand, HeavyGroundManeuver, JsocSpecialOps, DefenseIndustrialPrimes }`
  - `department_of_war::step_behemoth(...) -> BehemothPeriodReport`

- [ ] **Step 5.1: Write failing tests in `department_of_war_tests.rs`** verifying:
  1. **The Imperial Boomerang conservation law:** Moving one `ActiveDuty` division from `ExternalGarrison` to `DomesticSiege` reduces external enforcement on the 12 Trade Blocs + Israel and accelerates peripheral delinking / $\Phi$ contraction in the same period.
  2. **Guard & Reserves economic coupling:** Activating `NationalGuard` deducts labor hours directly from local county QCEW cohorts and has the highest leak/mutiny rate; activating `Reserves` deducts national transport/medical hours and staffs military `CorridorCapacity` convoys; severing `CorridorCapacity` via `PracticeId::Blockade` drops `HeavyGroundManeuver` mobility and offensive capacity to `0`.
  3. **Gaza-in-Chicago ($K$-destruction $\rightarrow$ Wall Street vs. Pentagon fracture):** High-CDE `AirGospelCommand` strikes in an urban county destroy constant capital $K$ in `MaterialCircuitState`, expand boundary-of-the-cut `Backfire`, and cause `FinanceCapital` to withdraw credit from `SecurityState`.
- [ ] **Step 5.2: Implement `department_of_war.rs` and wire the labor/capital couplings.**
- [ ] **Step 5.3: Verify tests and `bsl-lint` pass.**

---

### Task 6 (`W3c`): Reactionary Militias, The George Jackson "Life Raft" Bifurcation, The Warlord Flip & The Opportunist Zoo (`research/20`, `21`, `25`)

**Files:**
- Create: `rust/crates/babylon-graph/src/reactionary_and_opportunist_zoo.rs`
- Create: `rust/crates/babylon-graph/src/life_raft_bifurcation.rs`
- Test: `rust/crates/babylon-graph/src/reactionary_and_opportunist_zoo_tests.rs`

**Interfaces:**
- Consumes: `AgencyCell`, `Capacity`, `Dossier`, `MaterialCircuitState`, `HouseholdTimeReceipt`
- Produces:
  - `ReactionaryCellKind { FascistMilitia, RevanchistSheriffPosse, DsaSocialFascistBuffer, QueerQluxQlanPinkwash, KkkommunitiesOfKkkareSwamp }`
  - `OpportunistCellKind { MoralistAdventurist, StrasseriteGrifter, DoctrinalSect { strain: McuOrRga }, ProtestCircuitTrotskyist, SpectacleInfluencer }`
  - `life_raft_bifurcation::evaluate_county_raft(...) -> LifeRaftBifurcationReceipt` enforcing $\mathrm{LR}\cdot O > R \cdot \#\{i : w_i + \max(b_i^{\text{DSA}}, b_i^{\text{Militia}}) \ge s_i\}$ with Hunan durability clause $S > 0, S^{\text{fail}} = 0$, plus the county Warlord flip `captive_revenue > tax_revenue`.
  - EROL `slogan_collision` (matching demand strings with a `FascistMilitia` or `StrasseriteGrifter` in the same media market) and `rival_gain` (chauvinist doctrine choices writing `MassLink` directly into rival nodes).

- [ ] **Step 6.1: Write failing tests in `reactionary_and_opportunist_zoo_tests.rs`** verifying:
  1. At $\mathrm{LR} = 0$, $\Phi$ contraction routes squeezed $C_{pb}/C_{la}$ households to `DsaSocialFascistBuffer` and `FascistMilitia`; running `Agitation` with $\mathrm{LR} = 0$ raises $R$ and increases militia recruitment.
  2. An untested mutual-aid node ($S = 0$) leaves $\mathrm{LR} = 0$; surviving a State/militia strike ($S > 0, S^{\text{fail}} = 0$) crosses $\Lambda > 1$ and triggers the endogenous defection cascade that starves the militia subscription pool.
  3. `captive_revenue > tax_revenue` flips the county into `WarlordTrajectory` and detaches the Sheriff cell from Governor/Mayor fiscal discipline.
  4. `SpectacleInfluencer` subtracts $T^{\text{consume}}$ from the 672-hour household residual before `SupporterLabor` forms and cannot be killed by `PoliticalExposure`; `DoctrinalSect` flips from `StrainA_McuLaborAristocracy` to `StrainB_RgaUltraLeftCult` when $n < O/d$; `MoralistAdventurist` ratchets permanent federal counter-terror appropriations whose splash hits the player iff a resolved edge exists in $L_c$.
- [ ] **Step 6.2: Implement `reactionary_and_opportunist_zoo.rs` and `life_raft_bifurcation.rs`.**
- [ ] **Step 6.3: Verify `cargo test -p babylon-graph --locked` and `bsl-lint` pass.**

---

### Task 7 (`W4a`): The Carceral Pipeline, Prison Organizing, Yard Hazards, Solidarity Pact & Revolutionary Metabolism Sinks (`research/22`, `23`)

**Files:**
- Create: `rust/crates/babylon-graph/src/carceral_pipeline.rs`
- Create: `rust/crates/babylon-material-circuit/src/revolutionary_metabolism.rs`
- Modify: `content/rules/control_ratio.bsl`
- Test: `rust/crates/babylon-graph/src/carceral_pipeline_tests.rs`

**Interfaces:**
- Consumes: `fact_coercive_infrastructure` (109 MI county jails / 31 state prisons), `HouseholdTimeReceipt`, `AgencyCell` (`PrisonAdmin`)
- Produces:
  - `CarceralStage { CountyJailLockup { bail_cost: Currency }, RuralStatePrison { prison_node: NodeId } }`
  - `PrisonAdmin` partial-derivative allocator ($B_{\text{prison}} = \pi\cdot\text{occupied} + \gamma\cdot\text{assaults} + \omega\cdot\text{guard\_wages}, \;\partial B/\partial A = \gamma > 0$) pricing `GangAssassination` ("getting merked" by Nazi/comprador gangs, ranked by `decapitation_value`), `NarcoticsRot` (fentanyl/K2 floods), `InformantFlipOnRelease` (SHU torture $\rightarrow$ early release as a `Malinovsky` mole), and `MailLockdown`.
  - `PrisonSolidarityPact` (the 5-plank UFPP / Pelican Bay Agreement to End Hostilities) neutralizing yard stabbings by pact-covered headcount and converting captive `L_u -> CadreLabor` (without triggering `territory/p4-penal-suppression`'s per-tick zeroing).
  - `revolutionary_metabolism::settle_period_sinks(...)` enforcing: (a) the `HouseholdTimeReceipt` 672-hour burnout cliff (`protected_unresolved_hours != 0 => contribution_available = 0`), (b) the single wage-ladder poach (unions/NGOs hiring cadres whose household falls below $w_i < s_i$), (c) Mao's 1945 underground cash sink vs. legal surface `survival_interest`, and (d) the 4 `Money` provenance books (`Rule1Dues`, `CodedCoupons`, `FoundationGrants`, and `TiflisExpropriations` with self-accelerating banditry ratio `share_kept_by_cell / total_take`).

- [ ] **Step 7.1: Write failing tests in `carceral_pipeline_tests.rs`** covering the `Arrest -> Bail/DA -> RuralPrison` transfer, `PrisonAdmin` pricing `GangAssassination` when $\gamma > 0$, `InformantFlipOnRelease` inserting a `Malinovsky` mole back into the urban chapter, `PrisonSolidarityPact` blocking yard assassinations and feeding `c04-terminal`, and the 672-hour `protected_unresolved_hours` cliff.
- [ ] **Step 7.2: Implement `carceral_pipeline.rs` and `revolutionary_metabolism.rs`.**
- [ ] **Step 7.3: Verify tests and `bsl-lint` pass.**

---

### Task 8 (`W4b`): Collective Node Contradictions (`Shift / Split / Flip`), *Michael Scott Communism*, Dual Power, The 260-Period Party Clock & The Four Endgames (`research/12`, `16`, `24`)

**Files:**
- Create: `rust/crates/babylon-graph/src/contradiction_barrier.rs`
- Create: `rust/crates/babylon-graph/src/party_constitution_clock.rs`
- Create: `rust/crates/babylon-graph/src/endgame_summits.rs`
- Modify: `rust/crates/babylon-practice-contract/src/intent.rs`
- Test: `rust/crates/babylon-graph/src/party_constitution_clock_tests.rs`

**Interfaces:**
- Consumes: `CadreLabor`, `Money`, `SupporterLabor`, `MemoryGraph`, `MaterialCircuitState`
- Produces:
  - `BarrierResolution { QualitativeShift, AntagonisticSplit { breakaway_node: NodeId }, WinnerTakeAllFlip }`
  - `PracticeId::Divide { target_a: NodeId, target_b: NodeId }` and `PracticeId::ConstituteParty`
  - `MichaelScottCommunismDiagnostic`:
    - *Substitution 1 (`NewsHeraldTribuneGazetteDrop`):* `DistributeNewspaper` with zero relationship edges yields `100 papers distributed` on the Seal and `+0` contacts/receptivity/cadres at Period Close.
    - *Substitution 2 (`CharismaticGuruSingleton`):* `signature_class_size(leader) == 1` flags *"Tony Soprano with a Longer Reading List / A Personality with a Mailing List"*—leader removal or burnout zeroes node capacity.
    - *Substitution 3 (`SpectatorshipNspm7Trap`):* High `Digital` reach with `CL == 0` triggers `NSPM-7` federal indictment referrals from `L_NSA`.
    - *The Antidote Split (`MagicalPowerOfPancakes` vs. `SelfReproducingMassProgram`):* Top-down service nodes lower $E_t$ but produce `0` `CadreLabor`; participatory mass-line governance produces `signature_class_size >= 2` cadre twins.
  - `PartyConstitutionState`: Two-Key Lock (`KeyA` + `KeyB`). Calling `ConstituteParty` without `KeyA` produces `PaperPartyMinsk1898` (*"I DECLARE REVOLUTION!"*); calling with `KeyA + KeyB` starts the **260-period `survival_interest` SPD calcification clock**.
  - `DualPowerState`: derived per zone when `(cheapest_state_entry == QrfOperation && qrf_unfunded_this_period) && independent_institutions_cover_goods_and_justice`.
  - `EndgameSummitState`:
    1. `FalseSummitDsaPresidency` (winning Congress + Presidency without smashing the state forces the closed four-payer fiscal fork: Social-Imperialist Navy deployment to preserve $\Phi$ vs. Chile-1973 Pentagon/Finance Caesarist coup when `autonomy(c) > 4000 bps`).
    2. `FalseSummitRedSettler` (`RED_OGV`: winning insurrection while observed `extraction_intensity > 1/60` and `ColonialStance::Ignore` ratchets `max-biocapacity` down and triggers New Afrika / Aztlán / Indigenous Dual Power secession against the player's new state).
    3. `WarlordArchipelago` ($\Phi$ collapse + federal insolvency + county `captive_revenue > tax_revenue`).
    4. `TrueLiberation` (smashing the state machine + Three-Strand Line + `ColonialStance::Abolish` with `extraction_intensity <= 1/60` + global anti-imperialist delinking).

- [ ] **Step 8.1: Write failing tests in `party_constitution_clock_tests.rs`** covering all 4 *Michael Scott Communism* diagnostics, `PaperPartyMinsk1898`, `Prague1912` ratification, the 260-period `survival_interest` calcification, `DualPowerState` emergence, and all 4 `EndgameSummitState` transitions (`FalseSummitDsaPresidency` Fork 1 & Fork 2, `FalseSummitRedSettler`, `WarlordArchipelago`, `TrueLiberation`).
- [ ] **Step 8.2: Implement `contradiction_barrier.rs`, `party_constitution_clock.rs`, and `endgame_summits.rs`.**
- [ ] **Step 8.3: Verify tests and `bsl-lint` pass.**

---

### Task 9 (`W5`): The Six Canonical Screens & Split-Pane Decision Ceremony in `babylon-client`

**Files:**
- Modify: `rust/crates/babylon-client/src/decision_surface.rs`
- Create: `rust/crates/babylon-client/src/ceremony_modal.rs`
- Test: `rust/crates/babylon-client/src/decision_surface_tests.rs`

**Interfaces:**
- Consumes: `FencedPlayerView`, `PracticeId`, `BarrierResolution`, `MichaelScottCommunismDiagnostic`, `EndgameSummitState`
- Produces:
  - The 6 canonical gameplay surfaces in `decision_surface.rs`: `TopologyScreen`, `ElectoralScreen`, `PhysicalMapScreen`, `TickerScreen`, `WikiScreen`, `LineDoctrineScreen`.
  - `DecisionCeremonyModal`: split-pane event presentation (summarizing options by *meaning*, never *yield*, with zero `%` or multiplier readouts) and the three-layer answer pipeline (`SealReceiptStub` at click $\rightarrow$ story-first `PeriodCloseReckoning` $\rightarrow$ backdated `LongTailDiscovery`), including canonical Vigilance Case Files for `Michael Scott Communism`, `KKKommunities of KKKare`, `The Queer Qlux Qlan`, and `The Magical Power of Pancakes`.

- [ ] **Step 9.1: Write failing contract tests in `decision_surface_tests.rs`** asserting that all 6 screens register with a decision question, visible signals, and visible uncertainty, and that any string containing a raw multiplier (`"x"`, `"%"` probability, `"heat"`, `"legitimacy"`) outside a leaked-SOP Wiki artifact is rejected at compile/contract time.
- [ ] **Step 9.2: Implement the 6-screen manifest update and `ceremony_modal.rs`.**
- [ ] **Step 9.3: Verify `cargo test -p babylon-client --locked` and `bsl-lint` pass.**
