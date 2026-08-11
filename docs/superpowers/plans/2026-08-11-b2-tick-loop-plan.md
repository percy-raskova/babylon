# Program 28 B2 — The Tick Loop On Screen: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to execute this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** close Program 28 §7 criterion 3 — a person opens `babylon-client`, sees the county map
B1 rendered, presses a key to advance the tick, and watches real state change: a tick counter, a
deterministic state-hash readout, a live per-county legitimation overlay on the map, a state panel
for the hovered/selected county, and an event feed — all driven by the Rust engine through a new
persistent tick-loop seam, never a lookalike.

**Architecture:** Five phases in five PRs. Phase A opens a **persistent session** in
`babylon-tick` — `TickSession<G>`, additive, built by factoring the load half `run_once_into`
already does into a shared `prepare_rule` helper so the existing one-shot API moves not one byte.
Phase B authors the **demo content**: a twelve-real-FIPS-county scenario carrying the
already-conformance-tested `lifecycle/dpd-circuit` rule pack's four archetype value sets, so the
map has real counties to light up. Phase C **completes B1's still-unbuilt Phase C** (`lens.rs`,
`map/bands.rs`'s band table, `map/pick.rs`, `map/hud.rs`) but generalizes it to carry TWO lenses
side by side — ADR170's static Tension lens (ported unmodified) and a new, tick-live Legitimation
lens reading the field `lifecycle/dpd-circuit` writes every tick — with a lens-picker key so the
player can see the difference between "declared once" and "moves every tick" honestly. Phase D
wires the **loop UI**: the advance-tick input, the tick counter, the hash readout, the state
panel, the event feed. Phase E resurrects the **file-log sink** the deletion ceremony retired,
proves **determinism** end-to-end, and defines the **eyes-on gate**.

**Tech Stack:** Bevy 0.18.1 (unchanged from B1 — `pan_camera` feature already pinned), the same
`earcutr`/atlas/tessellate stack B1 built, `log4rs` 1.x (`default-features = false`, the exact
feature set the deleted `babylon-tui` crate used) resurrected for the client's own file sink,
`log` 0.4 as the facade that sink listens on — kept fully separate from Bevy's own `tracing`-based
`LogPlugin`, which keeps printing to the console exactly as `DefaultPlugins` already wires it.

**Source spec:** `docs/superpowers/specs/2026-08-10-program-28-bevy-cutover-roadmap-design.md`
(§4 client lane, §7 criterion 3, §8 open questions). **Predecessor plan:**
`docs/superpowers/plans/2026-08-10-b1-county-map-plan.md` (Phase A+B merged as PR #487/#490;
Phase C `lens.rs`/`map/pick.rs`/`map/hud.rs` and the `band_color` function in `map/bands.rs`
**were never built** — only `bands.rs`'s `PANEL` constant landed, pre-positioned there by a B1
adversarial-review fix (F4) specifically so "Task 9 finds one existing declaration to extend, not
a second one to reconcile." This plan is that extension, generalized — see the Sequencing
Decision below.

**Governing rulings this plan carries out and does not reopen:**

- **ADR170** — this plan transcribes the Tension lens formula (`phi = v/(v+s)`,
  `theta = sum(v)/sum(v+s)` as a ratio of sums, `w = (phi-theta)/(phi+theta)`) unchanged, wherever
  it touches it.
- **ADR191 R9/R10/R11** — the Director already settled the Iosevka Nerd Font choice, the
  cartographic insets, and the FOUR-BAND (not continuous-ramp) rendering of the Tension lens; this
  plan reuses R11's band table verbatim rather than re-deriving it.
- **ADR193** — `babylon-tick::run_once`/`run_once_into` now construct `HypergraphStore`, not
  `MemoryGraph`; `state_hash()` calls `encode_state()`, and ADR193 measures that call QUADRATIC in
  hyperedge count on `HypergraphStore` (22.59 ms at n=2,000 hyperedges; 1.92 s at n=20,000). **This
  plan's
  own demo scenario mints twelve `NodeType/TERRITORY` nodes and zero hyperedges** — the cliff does
  not bite; see the Scale Note below for the arithmetic.
- **Constitution III.7 (determinism)** and **III.11 (Loud Failure)** — the hash display exists
  because the hash IS the honesty proof; a county the demo scenario never minted stays `PANEL`,
  never a fabricated value.
- **R8/R9 (BSL-first porting, escape by proof)** — nothing in this plan adds Rust simulation logic;
  the only Rust code this plan writes is client/UI/seam code and a factored-out loader helper. All
  simulation content stays in the already-merged `lifecycle` rule pack.
- **No imposed functional forms (2026-07-29 standing ruling)** — the new Legitimation lens invents
  no threshold and no formula. It colors counties by the **categorical classification the
  `lifecycle` rule pack already computes and writes** (`territory/legitimation-crisis`: 0 = STABLE,
  1 = UNSTABLE, 2 = CRISIS), never a newly-derived cut point on the raw index.

## Global Constraints

- Branch from `dev`; conventional commits; every commit ends with
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Worktree execution recipe: symlink `.venv` from the main checkout, copy `data/`, commit with
  `PYTHONPATH="$PWD/src"` — this plan is docs-only (no Rust build), but a later executor of THIS
  plan's tasks needs the recipe, so this document carries it for them.
- Gates for the executing agent: `mise run rust:check` for any `rust/` change (clippy
  `-D warnings`, workspace, all targets, locked); `mise run check` for the repo-wide fast gate;
  `mise run qa:regression` and `mise run qa:vault-regression-ci` after any change touching
  `babylon-tick` — Phase A's refactor must move zero engine bytes, and Phase A Step 4's own test
  is the first proof of that, not the only one.
- Vale: `vale <file>` on every Markdown page touched, driven to 0.
- **CI reality (unchanged from B1):** `rust-gate` runs on `ubuntu-latest`, compile-time Bevy
  headers only, no display server, no GPU. Every headless test in this plan uses `MinimalPlugins`
  plus `AssetPlugin`, never `DefaultPlugins`, exactly as B1's `tests/map_mesh.rs` and
  `tests/map_camera.rs` already establish.
- **Palette canon** — reuse only already-declared `§9b` tokens (`palette.rs`) and the already-ruled
  ADR170 four-band table (`PANEL`, `CRIMSON`, `DIM`, `GOLD` from `map/bands.rs`); the new
  Legitimation lens's three colors (`GREEN_DARK`, `GOLD`, `CRIMSON`) are ALL pre-existing `§9b`
  tokens — this plan adds no new `Color::srgb_u8` literal anywhere, so
  `test_no_stray_color_literals_outside_palette_or_a_declared_exemption`'s sweep needs no new
  exemption entry.
- **No new babylon-bsl surface.** Every task in this plan reads through `GraphSubstrate`'s existing
  14 methods (`node_attribute`, `nodes`, …) and `CanonicalState`'s existing `state_hash`. The one
  API addition anywhere in this plan is `babylon-tick::TickSession` (Phase A) — flagged explicitly,
  additive only, `run_once`/`run_once_into`/`TickReport` keep their exact current signatures.
- **Scale note (ADR193 arithmetic, worked here so no task has to re-derive it):** the Phase B demo
  scenario mints exactly 12 `NodeType/TERRITORY` nodes and declares no `(edge …)`/`(hyperedge …)`
  forms, so `HypergraphStore::encode_state`'s hyperedge half walks **zero** hyperedges regardless
  of the measured quadratic constant — the ADR193 table's smallest measured point (n=2,000
  hyperedges, 22.59 ms) is already ~5,500x this plan's hyperedge count. `state_hash()` runs twice
  per `advance()` call (pre/post, per `TickSession::advance`, Phase A Task 2) against 12 nodes, ~50
  scalar attributes and 0 hyperedges — sub-millisecond on the dyadic-half code path both stores
  share (ADR193: "`nodes`/`edges`/`neighbors` show no consistent direction at any scale"). The
  cliff is a real, documented future cost (ADR193's own "3,222-US-county target… plausibly crosses
  10,000 hyperedges once county-level organizational and sector memberships exist") — it belongs to
  whichever later program mints those memberships, not to this one.

---

## Decision: B2 completes B1's Phase C, generalized to two lenses

**B1's own File Structure table already reserves four files for "Phase C — the lens lane":
`lens.rs`, `map/bands.rs`'s `band_color`/recolor-system additions, `map/pick.rs`, `map/hud.rs`.
None of the four landed** — `git log` shows B1 merged only Phase A (#487, the atlas artifact) and
Phase B (#490, atlas reader/tessellation/mesh/camera); `find rust/crates/babylon-client/src` today
shows `atlas.rs`, `engine_link.rs`, `lib.rs`, `main.rs`, `palette.rs`, `tessellate.rs`, and
`map/{bands,camera,mesh,mod}.rs` — `bands.rs` holds only the `PANEL` constant (parked there by a
B1 adversarial-review fix specifically so a later task would extend, not duplicate, its
declaration).

The roadmap spec's own B2 line is: *"tick advance, state panels, event feed — the scenario ->
tick -> hash seam that already runs headless, made visible and playable."* That line does not,
by itself, require the map to recolor from live ticks — the state panel alone could meet "watch
state change." But §7 criterion 3 says *"see the county map… and watch state change"* — read
together with the Director's own aesthetic-and-pedagogy line (*"what game mechanics are both
engaging AND instill education about the correct revolutionary theory?"*), a tick loop whose only
visible effect is a text panel while the map sits inert is a materially weaker demo than one where
the county the player is watching visibly changes color as the tick fires. The map is already
built (Phase B); Phase C's reserved files are the ONLY place the county-indexed
lens/hover/recolor/HUD plumbing this needs was ever going to live.

**Decision: this plan builds Phase C's four reserved files as part of its own task list — it does
not wait for a separate Phase C PR, and it does not duplicate Phase C's interfaces alongside new
ones.** Concretely:

1. `lens.rs` carries the ADR170 witness (`county_tension`, ported verbatim from the B1 plan's
   Task 8 spec, corrected for one thing the B1 plan text predates — see below) **and** a second,
   new witness (`county_legitimation`) reading the field the tick loop actually moves.
2. `map/bands.rs` gains B1 Task 9's `band_color` function and four-row table (ADR191 R11,
   unmodified) **and** a second, small three-row table for the Legitimation lens — both are pure
   presentation constants, no `GameDefines`/`defines_hash` ceremony, exactly as ADR191 R11 already
   ruled for the first table.
3. `map/pick.rs` and `map/hud.rs` are B1 Task 10's designs, unmodified, except the HUD now also
   names which of the two lenses is active (Task 9 below) — this plan adds that honesty rule
   because two lenses share the color CRIMSON for two different meanings (Tension's "Φ-source,
   bled" vs. the Legitimation lens's "CRISIS"), and nothing may let a player read one as the other.

**One correction to B1's plan text, made explicit so no one silently inherits it wrong:** B1's
Task 8 spec writes `pub fn county_tension(graph: &MemoryGraph) -> TensionLens`. ADR193 (merged the
same day, sequenced textually after B1's plan but landed at the same `dev`-branch tip this plan
reads) swapped the production substrate from `MemoryGraph` to `HypergraphStore` — `run_once_into`
and, after Phase A of this plan, `TickSession`, both hold a `HypergraphStore`. **This plan's
`lens.rs` takes `&dyn GraphSubstrate`, not `&MemoryGraph`** — the trait both stores carry,
matching what the client actually holds. `MemoryGraph` remains only as the differential-test
oracle (ADR193's own consequences section).

## Decision: the demo content set is the lifecycle rule pack, alone

Three merged rule packs exist: `fundamental-theorem` and `vitality` (both subject type
`social-class`) and `lifecycle` (subject type `territory` — the D-P-D' circuit, four bindings
into `NodeType/TERRITORY` fields, emitting `LIFECYCLE_TRANSITION`/`LEGITIMATION_CRISIS`/
`LEGITIMATION_RECOVERY` events). `lifecycle` alone, of the three, has a subject type matching
the map's native unit, and alone produces genuine tick-over-tick numeric change a player can watch
land on a specific county.

**Running more than one rule pack live in the same session is out of this plan's scope, and here
is the exact wall it hits:** `babylon-bsl::rule_pipeline::split_content` enforces, by construction
(`rule_pipeline.rs:299-308`), **exactly one `(rule …)` top-form per content set** —

```text
"a content set needs exactly one (rule …) top-form, found {N}
 (§2.2 — intrinsic declarations do not count; deffield/manifest/metric-decl
 top-forms are not yet split out by this function and would also land here)"
```

— an `E-LOAD` refusal, not a soft warning. `babylon-tick::run_once`/`run_once_into` (and this
plan's `TickSession`, which shares the same loader) each take ONE `rule_src` string and can run
ONE rule pack per session. Wiring `vitality` and `lifecycle` together needs BOTH (a) a
`babylon-tick` change accepting `Vec<LoadedRule>` and running each in turn against one shared
graph within one game-tick (their subject types are disjoint — `social-class` vs. `territory` — so
nothing about running both against one graph is unsound, only never built), and (b) one scenario
declaring BOTH subject types' fields, since today's conformance scenarios are single-purpose
(`two-classes.bscn` for social-class content, `lifecycle-conformance.bscn` for territory content).
**Both are real, scoped follow-up work someone can build later — flagged here as a deferral, not
attempted in this plan.** Record an issue against the client/engine lane at PR time (mirroring the
B1 Task 12
precedent of opening an issue rather than silently narrowing scope).

---

## File Structure

| Phase | File | Action | Responsibility |
|---|---|---|---|
| A | `rust/crates/babylon-tick/src/lib.rs` | Edit | Factor `prepare_rule` out of `run_once_into`; add `pub mod session;` |
| A | `rust/crates/babylon-tick/src/session.rs` | Create | `TickSession<G>` — load once, `advance()` many times |
| B | `rust/crates/babylon-client/tests/print_demo_counties.rs` | Create (throwaway aid) | One-shot atlas print, deleted after use |
| B | `rust/crates/babylon-tick/content/scenarios/us-counties-lifecycle-demo.bscn` | Create | 12 real-FIPS territory nodes, lifecycle fields |
| C | `rust/crates/babylon-client/src/lens.rs` | Create | `county_tension` (ADR170, ported) + `county_legitimation` (new) |
| C | `rust/crates/babylon-client/src/map/bands.rs` | Edit | ADR191 R11's `band_color` (Tension) + a new legitimation band function |
| C | `rust/crates/babylon-client/src/map/pick.rs` | Create | Uniform-grid hit test (B1 Task 10's design) |
| C | `rust/crates/babylon-client/src/map/hud.rs` | Create | Hover/selection readout, active-lens label, absence banner |
| C | `rust/crates/babylon-client/src/map/mod.rs` | Edit | Wire the three new modules + lens-picker input |
| D | `rust/crates/babylon-client/src/engine_link.rs` | Edit | `EngineSession` resource: `TickSession<HypergraphStore>` + `CollectingSink` + FIPS↔`NodeId` map |
| D | `rust/crates/babylon-client/src/main.rs` | Edit | Advance-tick input, tick counter, hash readout, event feed |
| E | `rust/crates/babylon-client/src/logging.rs` | Create | Resurrected `log4rs` file sink |
| E | `rust/crates/babylon-client/Cargo.toml` | Edit | `log`, `log4rs` deps |
| E | `rust/crates/babylon-client/tests/determinism.rs` | Create | Same-content, same-tick-count ⇒ same hash, end to end |
| E | `rust/crates/babylon-client/tests/eyes_on_smoke.rs` | Create | Headless proxy for the eyes-on gate |

---

## Phase A — The persistent tick session

### Task 1: Factor `prepare_rule` out of `run_once_into`

**Files:**

- Edit: `rust/crates/babylon-tick/src/lib.rs`

**Interfaces:**

- Produces: `pub(crate) struct PreparedRule { loaded: LoadedRule, types: TypeEnv, intrinsics:
  IntrinsicCosts, consts: HashMap<String, Value> }` and `pub(crate) fn prepare_rule<G:
  GraphSubstrate + CanonicalState>(scenario_src: &str, rule_src: &str, graph: &mut G) ->
  Result<PreparedRule, String>` — everything `run_once_into` currently does BEFORE its call to
  `run_tick`.
- Consumes (unchanged): `split_content`, `parse_intrinsic_decls`, `IntrinsicCosts::new`,
  `load_scenario`, `TypeEnv`, `BindingVocabulary`, `CardinalityCeilings`, `LoadContext`,
  `load_rule_form` — every import already at the top of `lib.rs` stays.

This is a **pure extraction, zero behavior change**: `run_once_into`'s existing 130-odd lines
split at exactly the point after `let loaded = load_rule_form(...)` — everything before that line
moves into `prepare_rule`, returning the four values it currently holds locally; everything from
`run_tick(...)` onward stays in `run_once_into`, now reading `prepared.loaded`,
`prepared.types`, and so on, instead of local bindings.

- [ ] **Step 1: Write the regression-proof test FIRST** (red only in the sense that it must stay
      green through the refactor — there is no new behavior to fail on). Confirm the two existing
      tests already cover this:

```rust
// already in lib.rs's #[cfg(test)] mod tests — read, do not duplicate:
//   run_once_is_deterministic (two-classes.bscn / the fundamental-theorem rule)
// already in tests/engine_link.rs (babylon-client):
//   startup_tick_matches_the_pinned_hash — hex(&report.after) ==
//   "783f651d04d32fffd0109e88423eb7a57b1e0836ed4a9f645d3a8a554e427679"
```

      Run both now, before touching any code: `cargo test -p babylon-tick` and
      `cargo test -p babylon-client --test engine_link` → both PASS. This is the baseline the
      refactor must not move.
- [ ] **Step 2: Extract `prepare_rule`.**

```rust
/// Everything `run_once_into` does before running a single tick: parse the
/// intrinsic declarations, load the scenario into `graph`, and load the
/// one `(rule …)` form against the vocabulary/types/ceilings that scenario
/// declared. Shared by `run_once_into` (which still runs exactly tick 1)
/// and `TickSession::new` (`session.rs`), which runs this ONCE and then
/// calls `run_tick` many times against the result — the split B2 needed
/// and `run_once_into`'s hardcoded tick number could not express.
pub(crate) struct PreparedRule {
    pub loaded: LoadedRule,
    pub types: TypeEnv,
    pub intrinsics: IntrinsicCosts,
    pub consts: HashMap<String, Value>,
}

pub(crate) fn prepare_rule<G: GraphSubstrate + CanonicalState>(
    scenario_src: &str,
    rule_src: &str,
    graph: &mut G,
) -> Result<PreparedRule, String> {
    let (intrinsic_forms, rule_form) = split_content(rule_src).map_err(|e| e.to_string())?;
    let declared = parse_intrinsic_decls(&intrinsic_forms).map_err(|e| e.to_string())?;
    let intrinsics = IntrinsicCosts::new(
        declared
            .into_iter()
            .map(|(name, decl)| (name, decl.cost))
            .collect(),
    );

    let scenario = load_scenario(scenario_src, graph).map_err(|e| e.to_string())?;

    let types = TypeEnv {
        fields: scenario.fields.clone(),
        exemptions: &[],
    };
    let vocabulary = BindingVocabulary {
        fields: scenario.fields.keys().cloned().collect(),
        consts: scenario.consts.keys().cloned().collect(),
        metrics: HashSet::new(),
    };
    let ceilings = CardinalityCeilings::new(
        scenario
            .node_types
            .iter()
            .map(|(member, count)| (format!("NodeType/{member}"), *count))
            .collect(),
        HashMap::new(),
    );
    let systems: HashSet<String> = HashSet::from([
        "economics".to_owned(),
        "vitality".to_owned(),
        "consciousness".to_owned(),
        "lifecycle".to_owned(),
    ]);

    let ctx = LoadContext {
        vocabulary: &vocabulary,
        types: &types,
        ceilings: &ceilings,
        intrinsics: &intrinsics,
        systems: &systems,
        vocabulary_registry: None,
        rule_file: "rule",
    };
    let loaded = load_rule_form(rule_form, &ctx).map_err(|e| format!("rule rejected: {e}"))?;

    Ok(PreparedRule {
        loaded,
        types,
        intrinsics,
        consts: scenario.consts,
    })
}
```

- [ ] **Step 3: Rewrite `run_once_into` to call it.**

```rust
pub fn run_once_into<G: GraphSubstrate + CanonicalState>(
    scenario_src: &str,
    rule_src: &str,
    graph: &mut G,
    sink: &mut CollectingSink,
) -> Result<TickReport, String> {
    let prepared = prepare_rule(scenario_src, rule_src, graph)?;

    let before = graph
        .state_hash()
        .map_err(|e| format!("pre-tick state: {}", e.message))?;

    let outcome = run_tick(
        &prepared.loaded,
        &prepared.types,
        &KernelIntrinsicHost,
        graph,
        sink,
        &prepared.intrinsics,
        &prepared.consts,
        1,
    )
    .map_err(|e| format!("tick failed: {e}"))?;

    let after = graph
        .state_hash()
        .map_err(|e| format!("post-tick state: {}", e.message))?;

    Ok(TickReport {
        before,
        after,
        fired: outcome.fired,
    })
}
```

      Note the pre-tick hash is now taken AFTER `prepare_rule` returns rather than immediately
      after `load_scenario` — this is the same point in program order (nothing between the old
      `load_scenario` call and the old `before` computation touches `graph`), so the hash value is
      identical; only the code that produces it moved.
- [ ] **Step 4:** Run both Step 1 tests again → PASS, byte-identical hash. `mise run rust:check` →
      green. `mise run qa:regression` and `mise run qa:vault-regression-ci` → byte-identical (this
      refactor is inside the engine crate; both gates must stay silent).
- [ ] **Step 5: Commit** (`refactor(rust): factor prepare_rule out of run_once_into — zero behavior
      change (B2)`).

### Task 2: `TickSession<G>` — load once, advance many times

**Files:**

- Create: `rust/crates/babylon-tick/src/session.rs`
- Edit: `rust/crates/babylon-tick/src/lib.rs` (`pub mod session;`, re-export)

**Interfaces:**

- Produces:

```rust
pub struct TickSession<G> { /* private: graph, prepared, tick */ }

impl<G: GraphSubstrate + CanonicalState> TickSession<G> {
    pub fn new(scenario_src: &str, rule_src: &str, graph: G) -> Result<Self, String>;
    pub fn advance(&mut self, sink: &mut CollectingSink) -> Result<TickReport, String>;
    pub fn tick(&self) -> i64;
    pub fn graph(&self) -> &G;
}
```

  Every later task in this plan (Phase C's lens producers, Phase D's UI) reads state through
  `session.graph()` and drives the loop through `session.advance(&mut sink)`. This is the ONE
  babylon-tick API addition this plan makes — `run_once`, `run_once_into` and `TickReport` are
  untouched (Task 1 proved that); a caller that only ever wants tick 1 still calls `run_once`.

- [ ] **Step 1: Write the failing tests.**

```rust
use crate::session::TickSession;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;

const SCENARIO: &str = include_str!("../content/scenarios/lifecycle-conformance.bscn");
const RULE: &str = include_str!("../content/rules/lifecycle.bsl");

#[test]
fn advance_numbers_ticks_starting_at_one() {
    let mut session = TickSession::new(SCENARIO, RULE, HypergraphStore::new()).expect("load");
    assert_eq!(session.tick(), 0);
    let mut sink = CollectingSink::default();
    session.advance(&mut sink).expect("tick 1");
    assert_eq!(session.tick(), 1);
    session.advance(&mut sink).expect("tick 2");
    assert_eq!(session.tick(), 2);
}

#[test]
fn advance_moves_state_and_each_tick_hashes_differently() {
    let mut session = TickSession::new(SCENARIO, RULE, HypergraphStore::new()).expect("load");
    let mut sink = CollectingSink::default();
    let t1 = session.advance(&mut sink).expect("tick 1");
    let t2 = session.advance(&mut sink).expect("tick 2");
    assert_ne!(t1.before, t1.after, "tick 1 must move state");
    assert_eq!(t1.after, t2.before, "tick 2 starts where tick 1 left off");
    assert_ne!(t2.before, t2.after, "tick 2 must move state too — not a one-shot");
}

#[test]
fn two_independent_sessions_over_the_same_content_hash_identically() {
    // The determinism guard this plan's own instructions require, at the
    // babylon-tick level — Phase E's test (tests/determinism.rs in
    // babylon-client) repeats this same property through the client's own
    // seam end to end.
    let mut a = TickSession::new(SCENARIO, RULE, HypergraphStore::new()).expect("load a");
    let mut b = TickSession::new(SCENARIO, RULE, HypergraphStore::new()).expect("load b");
    let mut sink_a = CollectingSink::default();
    let mut sink_b = CollectingSink::default();
    for _ in 0..5 {
        let ra = a.advance(&mut sink_a).expect("a advances");
        let rb = b.advance(&mut sink_b).expect("b advances");
        assert_eq!(ra.after, rb.after, "same content + same tick count must hash identically");
    }
}
```

- [ ] **Step 2:** `cargo test -p babylon-tick` → FAIL (`session` module does not exist).
- [ ] **Step 3: Write `session.rs`.**

```rust
//! `TickSession` — the persistent load-once, advance-many seam B2 needs.
//! `run_once`/`run_once_into` (`lib.rs`) model exactly one tick end to end
//! and hardcode `run_tick`'s tick argument to `1`; a player-driven loop
//! needs the split this type provides instead: parse and load cost paid
//! ONCE in `new`, the SAME `PreparedRule` and the SAME graph reused by
//! every `advance()` call, with `tick` incremented by this type rather
//! than by the caller re-guessing a number `run_tick` never exposed.

use crate::{prepare_rule, PreparedRule, TickReport};
use babylon_bsl::intrinsic_host::KernelIntrinsicHost;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_bsl::tick::run_tick;
use babylon_graph::state_hash::CanonicalState;
use babylon_graph::substrate::GraphSubstrate;

/// One content set, loaded once, advanced tick by tick against ONE held
/// graph. `G` is caller-supplied (same shape as `run_once_into`) so the
/// caller picks the substrate — production callers pass `HypergraphStore`
/// (ADR193).
pub struct TickSession<G> {
    graph: G,
    prepared: PreparedRule,
    tick: i64,
}

impl<G: GraphSubstrate + CanonicalState> TickSession<G> {
    /// Parse `rule_src` and load `scenario_src` into `graph` once.
    ///
    /// # Errors
    /// The same failure modes `run_once_into`'s load half has: an
    /// intrinsic declaration, a scenario load, or a rule load.
    pub fn new(scenario_src: &str, rule_src: &str, mut graph: G) -> Result<Self, String> {
        let prepared = prepare_rule(scenario_src, rule_src, &mut graph)?;
        Ok(Self {
            graph,
            prepared,
            tick: 0,
        })
    }

    /// Run one more tick against the held graph. The first call runs tick
    /// 1 (matching `run_once`'s own numbering), the second tick 2, and so
    /// on — `:tick`/`:tick-in-cycle` bindings (§2.5) now see a real,
    /// advancing count outside a test harness for the first time.
    ///
    /// # Errors
    /// The tick itself, or a pre/post state-hash failure.
    pub fn advance(&mut self, sink: &mut CollectingSink) -> Result<TickReport, String> {
        self.tick += 1;
        let before = self
            .graph
            .state_hash()
            .map_err(|e| format!("pre-tick state: {}", e.message))?;
        let outcome = run_tick(
            &self.prepared.loaded,
            &self.prepared.types,
            &KernelIntrinsicHost,
            &mut self.graph,
            sink,
            &self.prepared.intrinsics,
            &self.prepared.consts,
            self.tick,
        )
        .map_err(|e| format!("tick failed: {e}"))?;
        let after = self
            .graph
            .state_hash()
            .map_err(|e| format!("post-tick state: {}", e.message))?;
        Ok(TickReport {
            before,
            after,
            fired: outcome.fired,
        })
    }

    /// The current tick number — 0 before the first `advance()` call.
    #[must_use]
    pub fn tick(&self) -> i64 {
        self.tick
    }

    /// Read-only access to the held graph — the client's map lens and
    /// state panel project live state through this.
    #[must_use]
    pub fn graph(&self) -> &G {
        &self.graph
    }
}
```

      `lib.rs` needs `PreparedRule`/`prepare_rule` visible to `session.rs` (same crate,
      `pub(crate)` from Task 1 already covers this) plus `pub mod session;` and, for the client's
      convenience, `pub use session::TickSession;` alongside the existing `pub use` of `TickReport`.
- [ ] **Step 4:** `cargo test -p babylon-tick` → PASS (all three new tests, plus the two Task 1
      regression tests still green). `mise run rust:check` → green.
- [ ] **Step 5: Commit** (`feat(rust): TickSession — persistent load-once/advance-many tick loop
      seam (B2)`).

---

## Phase B — The demo content

### Task 3: Twelve real-FIPS demo counties

**Files:**

- Create (temporary aid, deleted at Step 4): `rust/crates/babylon-client/tests/print_demo_counties.rs`
- Create: `rust/crates/babylon-tick/content/scenarios/us-counties-lifecycle-demo.bscn`

**The point of this task:** `lifecycle-conformance.bscn`'s four territory nodes
(`core-county`/`growing-county`/`recovering-county`/`young-county`) carry proven-correct fixture
values (Task 2's tests already exercise them through the `lifecycle` rule pack) but carry synthetic local
names with no FIPS code, so `CountyAtlas::index_of_fips` cannot place them on the B1 map. This
task re-stamps the SAME four archetype value sets onto twelve REAL FIPS codes so the map has real
counties to light up, without inventing new numbers this plan's author cannot verify.

- [ ] **Step 1: Select the twelve FIPS, deterministically, from the committed atlas — never
      guessed.** B1 Task 1 Step 5 sorts the atlas's county table by FIPS ascending before writing,
      so atlas indices `0..12` are the twelve lowest-FIPS counties in the whole 3,222-county
      artifact, whatever they are. Print them:

```rust
// tests/print_demo_counties.rs — a one-shot reporting aid, not a permanent
// test. Delete this file in Step 4 once its output is transcribed below.
use babylon_client::atlas::CountyAtlas;

const ATLAS_BYTES: &[u8] = include_bytes!("../assets/map/county_atlas.bin");

#[test]
#[ignore = "one-shot reporting aid — run manually, transcribe, then this file is deleted"]
fn print_first_twelve() {
    let atlas = CountyAtlas::parse(ATLAS_BYTES).expect("committed atlas parses");
    for i in 0..12 {
        let c = atlas.county(i).expect("index within range");
        println!("{i}: fips={} name={}", c.fips, c.name);
    }
}
```

      Run: `cargo test -p babylon-client --test print_demo_counties -- --ignored --nocapture`.
      Record the twelve printed `(fips, name)` pairs in this task's commit body verbatim — this is
      the only place in this plan a FIPS code is fixed, and it is fixed by running code against the
      committed artifact, not by recall.
- [ ] **Step 2: Write the scenario.** Reuse the `lifecycle-conformance.bscn` header's `deffield`
      block and all 21 `defconst` rows byte-for-byte (same field types, same coefficient values,
      same `defines.yaml` line citations in the comments — this task changes WHICH nodes exist,
      never what the rule pack computes over them). Cycle the four archetype value sets from
      `lifecycle-conformance.bscn:80-124` across the twelve FIPS in order (indices 0-2 get the
      `core-county` values, 3-5 `growing-county`, 6-8 `recovering-county`, 9-11 `young-county`),
      naming each node `county-<fips>` (symbols must start with a lowercase letter — §1's
      `symbol ::= LOWER (LOWER | DIGIT | "-")*` — a bare FIPS like `06037` is not a legal symbol,
      `county-06037` is):

```text
(scenario lifecycle/us-counties-demo
  (deffield territory/pop-d int extensive)
  (deffield territory/pop-p int extensive)
  (deffield territory/pop-d-prime int extensive)
  (deffield territory/wealth-d-prime int extensive)
  (deffield territory/dependency-ratio int intensive)
  (deffield territory/legitimation-index int intensive)
  (deffield territory/legitimation-crisis int intensive)
  (deffield territory/transmitted-ideology int intensive)

  ; ... all 21 defconst rows, transcribed verbatim from
  ; lifecycle-conformance.bscn:56-76, same values, same :NNN citations ...

  ; county-<fips[0]>, county-<fips[1]>, county-<fips[2]>: the core-county
  ; archetype (DPDState docstring numbers, PRE-crisis STABLE).
  (node county-<fips[0]> NodeType/TERRITORY
    (territory/pop-d 2150) (territory/pop-p 6050) (territory/pop-d-prime 1800)
    (territory/wealth-d-prime 10000000) (territory/dependency-ratio 0)
    (territory/legitimation-index 0) (territory/legitimation-crisis 0)
    (territory/transmitted-ideology 0))
  ; ... repeated for fips[1], fips[2] with the same values ...

  ; county-<fips[3..6]>: the growing-county archetype (PRE-crisis UNSTABLE).
  ; county-<fips[6..9]>: the recovering-county archetype (PRE-crisis CRISIS,
  ;   fires LEGITIMATION_RECOVERY on tick 1 under these defconsts, same as
  ;   the conformance scenario).
  ; county-<fips[9..12]>: the young-county archetype (no D' cohort).
  )
```

      Write out all twelve `(node …)` forms in full — no ellipsis in the committed file, the
      ellipses above are this plan document's abbreviation only.
- [ ] **Step 3: A loading test.**

```rust
// rust/crates/babylon-tick/tests/us_counties_demo.rs (new file)
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_tick::TickSession;

const SCENARIO: &str = include_str!("../content/scenarios/us-counties-lifecycle-demo.bscn");
const RULE: &str = include_str!("../content/rules/lifecycle.bsl");

#[test]
fn the_demo_scenario_loads_and_ticks() {
    let mut session = TickSession::new(SCENARIO, RULE, HypergraphStore::new()).expect("load");
    let mut sink = CollectingSink::default();
    let report = session.advance(&mut sink).expect("tick 1");
    assert_ne!(report.before, report.after);
    // The recovering-county archetype fires LEGITIMATION_RECOVERY on tick 1
    // under these defconsts (matching lifecycle-conformance.bscn's own
    // documented behavior) — proves the twelve nodes really run the rule,
    // not just mint successfully.
    assert!(sink
        .events
        .iter()
        .any(|(name, _)| name == "EventType/LEGITIMATION_RECOVERY"));
}
```

      `cargo test -p babylon-tick --test us_counties_demo` → PASS.
- [ ] **Step 4:** Delete `tests/print_demo_counties.rs` — it has finished its job, and its own doc
      comment says so; a stale `#[ignore]`d test that prints fixed array indices against a file
      that could later change underneath is exactly the kind of orphan CLAUDE.md's Surgical
      Changes rule asks an author to clean up when a task's own steps create one.
- [ ] **Step 5: Commit** (`feat(content): twelve-real-FIPS lifecycle demo scenario for the B2 tick
      loop`), body carrying the Step 1 FIPS/name table.

---

## Phase C — The dual-lens map (completes B1 Phase C)

### Task 4: The Tension lens, ported and corrected for `HypergraphStore`

**Files:**

- Create: `rust/crates/babylon-client/src/lens.rs`
- Edit: `rust/crates/babylon-client/src/lib.rs` (`pub mod lens;`)

**Interfaces:**

- Produces:

```rust
pub struct LensReading {
    pub cells: Vec<(String, Option<f64>)>, // (fips, value) — shared shape both lenses return
    pub absent_reason: Option<String>,
}
pub fn county_tension(graph: &dyn GraphSubstrate) -> LensReading;
```

- [ ] **Step 1: Write the failing tests**, hand-building small `HypergraphStore`s (not
      `MemoryGraph` — the Sequencing Decision's correction applies here first): (a) two territories
      with clean stamps where `theta` (computed internally — `LensReading` carries only `w` per
      cell) differs from the mean of the two `phi`s; (b) a bled county scores
      `w < 0`, a bribed county `w > 0`; (c) a territory with `s > 0, e == 0` contributes nothing and
      reports `None`; (d) a graph with zero data-bearing territory nodes yields
      `absent_reason.is_some()` and every cell `None`; (e) every returned `w` lands in `[-1, 1]`.
- [ ] **Step 2:** FAIL, then write it — the ADR170 formula transcribed exactly as B1's Task 8
      specified (`phi = v/(v+s)`, `theta = sum(v)/sum(v+s)`, `w = (phi-theta)/(phi+theta)`,
      `phi+theta <= 1e-9` collapses to `0.0`), reading `graph.nodes("NodeType/TERRITORY")` and
      `graph.node_attribute(id, "...")` through `&dyn GraphSubstrate` rather than a concrete store.
- [ ] **Step 3:** `cargo test -p babylon-client` → PASS.
- [ ] **Step 4: Commit** (`feat(client): the ADR170 tension witness over &dyn GraphSubstrate (B2)`).

### Task 5: The Legitimation lens — live, categorical, zero new math

**Files:**

- Edit: `rust/crates/babylon-client/src/lens.rs`

**Interfaces:**

- Produces: `pub fn county_legitimation(graph: &dyn GraphSubstrate, node_by_fips: &[(String,
  NodeId)]) -> LensReading` and `pub enum LegitimationClass { Stable, Unstable, Crisis }` with
  `pub fn classify(raw: f64) -> LegitimationClass`.

**Why this reads a field instead of deriving one.** The `lifecycle` rule pack already computes and
writes `territory/legitimation-crisis` as an encoded classification (0 = STABLE, 1 = UNSTABLE,
2 = CRISIS — the rule pack's own header comment documents the encoding, quoted in
`lifecycle-conformance.bscn`'s comments). Coloring the map from THIS field, rather than re-deriving
a threshold on the raw `territory/legitimation-index`, adds no new cut point and no new math — this is a straight
categorical pass-through, consistent with the standing "no imposed functional forms" ruling.

- [ ] **Step 1: Write the failing tests.** A territory whose `legitimation-crisis` reads back
      `0.0`/`1.0`/`2.0` classifies to `Stable`/`Unstable`/`Crisis` respectively; a `node_by_fips`
      entry naming a `NodeId` the graph never minted (a coding error, not a real absence — the
      Phase B scenario controls the whole node set) surfaces as an `Err`, never a silent `None`,
      because unlike Tension's "this county may honestly have no data," a demo-scenario FIPS with
      no matching node is a wiring bug; only FIPS NOT in `node_by_fips` at all are the honest
      "outside the demo, no data this tick" absence.
- [ ] **Step 2:** FAIL, then write it: `classify` is a plain three-arm match on the encoded
      float (`0.0 => Stable`, `1.0 => Unstable`, `2.0 => Crisis`, anything else a loud panic — the
      encoding is a closed set the rule pack itself defines); `county_legitimation` reads
      `territory/legitimation-crisis` for every `(fips, id)` pair in `node_by_fips` and returns
      `Some(raw_class_as_f64)` per cell (kept as the raw encoded number in `LensReading.cells` so
      `map/bands.rs`'s consumer, not this module, owns the color mapping — matching the Tension
      lens's own separation of "compute the value" from "pick the color").
- [ ] **Step 3:** `cargo test -p babylon-client` → PASS.
- [ ] **Step 4: Commit** (`feat(client): the legitimation lens — live per-tick classification, zero
      new thresholds (B2)`).

### Task 6: Two band tables, one recolor system

**Files:**

- Edit: `rust/crates/babylon-client/src/map/bands.rs`

**Interfaces:**

- Produces: `pub fn tension_band_color(w: Option<f64>) -> Color` (ADR191 R11's table, exactly as
  the B1 plan's Task 9 specified — four rows, `<=` resolution, `PANEL` for absence) and `pub fn
  legitimation_band_color(class: Option<f64>) -> Color` (three rows: `Some(0.0) => GREEN_DARK`,
  `Some(1.0) => GOLD`, `Some(2.0) => CRIMSON`, `None => PANEL`) plus `pub enum ActiveLens { Tension,
  Legitimation }` and `#[derive(Event)] pub struct LensChanged;`.

- [ ] **Step 1: Write the failing tests** for both band functions — the exact `Srgba` byte
      assertions from the B1 Task 9 spec for `tension_band_color` (CRIMSON at `w <= -0.15`, DIM in
      `(-0.15, 0.15]`, GOLD above, PANEL for `None`) plus the three-plus-one assertions for
      `legitimation_band_color`. Assert `tension_band_color(Some(0.0)) != tension_band_color(None)`
      and the same non-confusion property for `legitimation_band_color` — absence must never read
      as the neutral/stable band in either lens.
- [ ] **Step 2:** FAIL, then write both as `const` tables resolved by the same `<=`-walk shape,
      matching `PANEL`'s existing declaration in this file.
- [ ] **Step 3: The recolor system.** One system, parameterized by `ActiveLens`:

```rust
pub(super) fn recolor_on_lens_changed(
    mut events: EventReader<LensChanged>,
    active: Res<ActiveLens>,
    lens_data: Res<CurrentLensData>, // holds both LensReading values, refreshed every advance
    surface: Res<MapSurface>,
    atlas_index: Res<FipsIndex>,     // fips -> atlas county index, from Task 9
    mut meshes: ResMut<Assets<Mesh>>,
) {
    if events.read().next().is_none() {
        return;
    }
    let reading = match *active {
        ActiveLens::Tension => &lens_data.tension,
        ActiveLens::Legitimation => &lens_data.legitimation,
    };
    let color_fn: fn(Option<f64>) -> Color = match *active {
        ActiveLens::Tension => tension_band_color,
        ActiveLens::Legitimation => legitimation_band_color,
    };
    let Some(mesh) = meshes.get_mut(&surface.fill_mesh) else {
        return;
    };
    let Some(colors) = mesh
        .attribute_mut(Mesh::ATTRIBUTE_COLOR)
        .and_then(|a| a.as_float3_mut())
    else {
        return;
    };
    for (fips, value) in &reading.cells {
        let Some(&county_idx) = atlas_index.by_fips.get(fips) else {
            continue;
        };
        let (start, end) = surface.tessellation.county_vertex_range[county_idx as usize];
        let rgba = color_fn(*value).to_linear().to_f32_array();
        for v in &mut colors[start as usize..end as usize] {
            *v = [rgba[0], rgba[1], rgba[2]];
        }
    }
}
```

      One pass, one buffer, matching B1 Task 9's own "no mesh rebuild" design — this is the same
      recolor shape B1's plan already specified, now parameterized over which lens is active
      instead of hardcoded to Tension alone.
- [ ] **Step 4: Headless test** — `MinimalPlugins` + `AssetPlugin`, install a `CurrentLensData`
      with one known Legitimation cell, set `ActiveLens::Legitimation`, fire `LensChanged`, `update()`,
      assert that county's vertex range shows `legitimation_band_color`'s output and every other
      county's colors held at `PANEL`.
- [ ] **Step 5: Commit** (`feat(client): two-lens band tables + a lens-parameterized recolor system
      (B2, completes B1 Phase C Task 9)`).

### Task 7: Hover, selection, the active-lens label

**Files:**

- Create: `rust/crates/babylon-client/src/map/pick.rs`, `rust/crates/babylon-client/src/map/hud.rs`

**Interfaces:**

- Produces: `pub struct CountyIndex; pub fn build(atlas: &CountyAtlas) -> CountyIndex; pub fn
  county_at(&self, p: Vec2) -> Option<usize>` (verbatim B1 Task 10 design — uniform grid over
  `world_bounds()`, even-odd ring crossing test, holes inverting membership); `HoveredCounty` and
  `SelectedCounty` resources; the HUD text, now carrying an explicit lens label.

- [ ] **Step 1: Write the failing tests** for `county_at` — the same three properties B1 Task 10
      specified: each county's own centroid resolves to itself (floor, not 100%, with exceptions
      listed by FIPS in the test comment); a point in the Gulf of Mexico gives `None`; a point
      inside a county's bounding box but outside its ring gives `None`; the index is identical
      across two builds.
- [ ] **Step 2:** FAIL, then write it: a 128x128 uniform grid, bounding-box candidate lists,
      even-odd crossing against the winning candidate's rings.
- [ ] **Step 3: Wire the interaction** — `Camera::viewport_to_world_2d` → `county_at` → `HoveredCounty`;
      click promotes to `SelectedCounty`; a GOLD outline at `z = 2.0` over the selection.
- [ ] **Step 4: The HUD**, extended past B1 Task 10's spec with the lens label this plan's honesty
      rule adds. Bottom-left, BONE text:

```text
<county name>, <state> (<FIPS>)
Lens: Tension — w = -0.42 (Φ-source, bled)          [if ActiveLens::Tension]
Lens: Legitimation — CRISIS (live, tick 7)          [if ActiveLens::Legitimation]
Lens: Tension — no data this tick                    [absence, either lens]
```

      Top-left banner whenever the active lens's `absent_reason.is_some()`, in CRIMSON. A
      persistent DIM footer names which lens is inactive and how to switch (Task 9): "Tab: switch
      to Legitimation lens" or vice versa — the map must never let a color mean two things without
      saying which one is live.
- [ ] **Step 5: Headless test** — hovering a known world point sets `HoveredCounty` to the expected
      FIPS, cursor position written directly to the resource (B1 Task 10's own precedent, not
      synthesized window events).
- [ ] **Step 6: Commit** (`feat(client): county hover, selection and the active-lens HUD (B2,
      completes B1 Phase C Task 10)`).

### Task 8: Wire `map/mod.rs` — the lens picker

**Files:**

- Edit: `rust/crates/babylon-client/src/map/mod.rs`

- [ ] **Step 1: Write the failing headless test** — `MinimalPlugins` + `AssetPlugin` +
      `babylon_client::map::MapPlugin`, press `Tab` (write directly into `ButtonInput<KeyCode>`,
      matching the input-resource-mutation pattern this plan's tests already use), `update()`,
      assert `ActiveLens` flipped and a `LensChanged` event fired.
- [ ] **Step 2:** FAIL, then add: `mod pick; mod hud;` (new modules from this task); `pub use
      bands::{ActiveLens, LensChanged};` alongside the existing `pub use bands::PANEL;` — the same
      re-export convention B1 already established for `PANEL`, extended to the two new types so
      `crate::map::ActiveLens`/`crate::map::LensChanged` (the paths Task 10's and Task 14's code
      use) resolve; `ActiveLens::Tension` inserted as the `Startup` default resource; an `Update`
      system reading `Tab` and toggling it plus sending `LensChanged`; Task 6's
      `recolor_on_lens_changed` system registered.
- [ ] **Step 3:** `cargo test -p babylon-client` → PASS. `mise run rust:check` → green.
- [ ] **Step 4: Commit** (`feat(client): wire the lens picker into MapPlugin (B2)`). Open the
      Phase C PR (`feat(client): B2 Phase C — the dual-lens map, completing B1's Phase C`);
      self-merge on green.

---

## Phase D — The loop UI

### Task 9: `EngineSession` — the client's held tick session

**Files:**

- Edit: `rust/crates/babylon-client/src/engine_link.rs`

**Interfaces:**

- Produces:

```rust
pub struct EngineSession {
    pub inner: TickSession<HypergraphStore>,
    pub sink: CollectingSink,
    pub node_by_fips: Vec<(String, NodeId)>,
}
impl EngineSession {
    pub fn start() -> Result<Self, String>;
    pub fn advance(&mut self) -> Result<TickReport, String>;
}
```

**Why `node_by_fips` is a plain `Vec`, not a `babylon-bsl` API addition.** `load_scenario`'s local
name -> `NodeId` map is deliberately load-time-only and does not outlive the call (`scenario.rs:188`'s
own comment). This plan does not widen that API. Instead: the Phase B scenario mints EXACTLY the
twelve `NodeType/TERRITORY` nodes, in file order, and no others; `GraphSubstrate::nodes()` returns
ascending `NodeId`s, which equal mint order because `NodeId` mints as a monotonic counter (ADR193).
Zipping `graph.nodes("NodeType/TERRITORY")` against a `const DEMO_FIPS: [&str; 12]` array **in
the same order as the `.bscn` file's twelve `(node …)` forms** recovers the fips↔id mapping with
no new babylon-bsl surface — fragile only in the sense that editing the `.bscn` file's node order
without updating `DEMO_FIPS` would silently mislabel a county, which Step 2's loud startup
assertion turns into an immediate panic instead.

- [ ] **Step 1: Write the failing test.**

```rust
#[test]
fn engine_session_starts_and_the_twelve_fips_resolve_on_the_real_atlas() {
    let session = EngineSession::start().expect("engine session starts");
    assert_eq!(session.node_by_fips.len(), 12);
    let atlas = CountyAtlas::parse(include_bytes!("../assets/map/county_atlas.bin")).unwrap();
    for (fips, _id) in &session.node_by_fips {
        assert!(
            atlas.index_of_fips(fips).is_some(),
            "demo FIPS {fips} must resolve on the committed atlas"
        );
    }
}

#[test]
fn engine_session_advance_moves_the_hash_and_the_tick_counter() {
    let mut session = EngineSession::start().expect("start");
    let r1 = session.advance().expect("tick 1");
    let r2 = session.advance().expect("tick 2");
    assert_eq!(session.inner.tick(), 2);
    assert_ne!(r1.after, r2.after);
}
```

- [ ] **Step 2:** FAIL, then write it:

```rust
const SCENARIO: &str =
    include_str!("../../babylon-tick/content/scenarios/us-counties-lifecycle-demo.bscn");
const RULE: &str = include_str!("../../babylon-tick/content/rules/lifecycle.bsl");

/// Same order as `us-counties-lifecycle-demo.bscn`'s twelve `(node …)`
/// forms — Task 3's Step 1 print output, transcribed. A loud startup
/// assertion (below) catches the two arrays ever drifting apart.
const DEMO_FIPS: [&str; 12] = [ /* the twelve FIPS from Task 3 Step 1, in file order */ ];

pub struct EngineSession {
    pub inner: TickSession<HypergraphStore>,
    pub sink: CollectingSink,
    pub node_by_fips: Vec<(String, NodeId)>,
}

impl EngineSession {
    pub fn start() -> Result<Self, String> {
        let mut graph = HypergraphStore::new();
        // Load through the same prepare path TickSession uses internally —
        // but we need the node ids BEFORE TickSession takes ownership of
        // the graph, so load once here to capture them, then hand a FRESH
        // graph to TickSession::new (it reloads the same scenario, which
        // is deterministic and mints the identical twelve ids — proven by
        // this task's own Step 1 test, which checks both independently).
        let scenario_nodes = babylon_bsl::scenario::load_scenario(SCENARIO, &mut graph)
            .map_err(|e| e.to_string())?;
        let _ = scenario_nodes; // node_count only; the ids come from nodes() below
        let ids = babylon_graph::substrate::GraphSubstrate::nodes(&graph, "NodeType/TERRITORY");
        if ids.len() != DEMO_FIPS.len() {
            panic!(
                "demo scenario minted {} NodeType/TERRITORY nodes, DEMO_FIPS names {} — \
                 the array drifted from the .bscn file, fix DEMO_FIPS",
                ids.len(),
                DEMO_FIPS.len()
            );
        }
        let node_by_fips: Vec<(String, NodeId)> = DEMO_FIPS
            .iter()
            .zip(ids.iter())
            .map(|(fips, id)| ((*fips).to_owned(), *id))
            .collect();

        let inner = TickSession::new(SCENARIO, RULE, HypergraphStore::new())
            .map_err(|e| format!("tick session: {e}"))?;

        Ok(Self {
            inner,
            sink: CollectingSink::default(),
            node_by_fips,
        })
    }

    pub fn advance(&mut self) -> Result<TickReport, String> {
        self.inner.advance(&mut self.sink)
    }
}
```

      Note the deliberate double-load (once to recover ids, once inside `TickSession::new`) rather
      than widening `TickSession` to expose its internal graph mutably before the first `advance` —
      it costs one extra scenario parse at startup (microseconds against a 12-node scenario) and
      keeps `TickSession`'s public surface exactly the four methods Task 2 specified.
- [ ] **Step 3:** `cargo test -p babylon-client` → PASS.
- [ ] **Step 4: Commit** (`feat(client): EngineSession — the client's held TickSession + fips↔id
      map (B2)`).

### Task 10: Advance-tick input, tick counter, hash readout

**Files:**

- Edit: `rust/crates/babylon-client/src/main.rs`

- [ ] **Step 1: Write the failing headless test.**

```rust
// tests/tick_loop.rs
use bevy::asset::AssetPlugin;
use bevy::prelude::*;

#[test]
fn pressing_space_advances_the_tick_and_updates_the_hash_text() {
    let mut app = App::new();
    app.add_plugins((MinimalPlugins, AssetPlugin::default(), InputPlugin));
    app.add_plugins(babylon_client::map::MapPlugin);
    app.add_plugins(babylon_client::loop_ui::TickLoopPlugin);
    app.update(); // Startup: EngineSession inserted, tick 0

    let counter = app.world().resource::<babylon_client::loop_ui::TickCounter>();
    assert_eq!(counter.0, 0);

    let mut input = app.world_mut().resource_mut::<ButtonInput<KeyCode>>();
    input.press(KeyCode::Space);
    app.update();

    let counter = app.world().resource::<babylon_client::loop_ui::TickCounter>();
    assert_eq!(counter.0, 1);
}
```

- [ ] **Step 2:** FAIL (`loop_ui` module does not exist).
- [ ] **Step 3: Write `src/loop_ui.rs`** (new module, `pub mod loop_ui;` in `lib.rs`):

```rust
//! The B2 tick loop's own UI plumbing: Space advances the tick, a text
//! node shows the counter and the deterministic hash — the honesty proof
//! (III.7) rendered where the player can see it move.

use crate::engine_link::EngineSession;
use bevy::prelude::*;

#[derive(Resource, Default)]
pub struct TickCounter(pub i64);

#[derive(Component)]
pub struct HashReadout;

#[derive(Component)]
pub struct TickCounterReadout;

pub struct TickLoopPlugin;

impl Plugin for TickLoopPlugin {
    fn build(&self, app: &mut App) {
        app.insert_resource(TickCounter::default());
        app.add_systems(Startup, spawn_engine_session_and_hud);
        app.add_systems(Update, (advance_on_space, refresh_readouts).chain());
    }
}

fn spawn_engine_session_and_hud(mut commands: Commands) {
    let session = EngineSession::start()
        .unwrap_or_else(|e| panic!("engine session failed to start: {e}"));
    commands.insert_resource(session);
    commands.spawn((
        Text::new("tick 0"),
        TextColor(crate::palette::BONE),
        Node {
            position_type: PositionType::Absolute,
            bottom: px(24),
            right: px(24),
            ..default()
        },
        TickCounterReadout,
    ));
    commands.spawn((
        Text::new("hash: (not yet run)"),
        TextColor(crate::palette::DIM),
        Node {
            position_type: PositionType::Absolute,
            bottom: px(4),
            right: px(24),
            ..default()
        },
        HashReadout,
    ));
}

fn advance_on_space(
    keys: Res<ButtonInput<KeyCode>>,
    mut session: ResMut<EngineSession>,
    mut counter: ResMut<TickCounter>,
    mut lens_changed: EventWriter<crate::map::LensChanged>,
) {
    if !keys.just_pressed(KeyCode::Space) {
        return;
    }
    session
        .advance()
        .unwrap_or_else(|e| panic!("tick advance failed: {e}"));
    counter.0 = session.inner.tick();
    lens_changed.write(crate::map::LensChanged);
}

fn refresh_readouts(
    counter: Res<TickCounter>,
    session: Res<EngineSession>,
    mut tick_text: Query<&mut Text, (With<TickCounterReadout>, Without<HashReadout>)>,
    mut hash_text: Query<&mut Text, With<HashReadout>>,
) {
    if !counter.is_changed() {
        return;
    }
    if let Ok(mut t) = tick_text.single_mut() {
        t.0 = format!("tick {}", counter.0);
    }
    if let Ok(mut h) = hash_text.single_mut() {
        // The last hash this session computed — sink carries no hash, so
        // read it back off the session's own last report by re-deriving
        // from the graph directly (state_hash is cheap at this scale, see
        // the Global Constraints Scale Note).
        if let Ok(hash) = babylon_graph::state_hash::CanonicalState::state_hash(session.inner.graph())
        {
            h.0 = format!("hash: {}", babylon_tick::hex(&hash));
        }
    }
}
```

      Wire `TickLoopPlugin` into `main.rs`'s `App::new()` chain, replacing B0/B1's
      `log_engine_link` Startup system (superseded — `EngineSession::start` now IS the engine link,
      and it panics loudly on failure exactly as `log_engine_link` did).
- [ ] **Step 4:** `cargo test -p babylon-client --test tick_loop` → PASS. `mise run rust:check` →
      green.
- [ ] **Step 5: Eyes-on:** `cargo run -p babylon-client` — press Space repeatedly, watch the tick
      counter and hash text change every press.
- [ ] **Step 6: Commit** (`feat(client): advance-tick input, tick counter, hash readout (B2)`).

### Task 11: The state panel and the event feed

**Files:**

- Edit: `rust/crates/babylon-client/src/loop_ui.rs`

- [ ] **Step 1: Write the failing headless test** — after two `advance()` calls with a county
      selected (write `SelectedCounty` directly, matching Task 7's pick-testing precedent), the
      state panel's text contains that county's live `pop-d`/`pop-p`/`pop-d-prime`/
      `legitimation-index` values read straight off the graph (not off the lens, which only carries
      the classification) — proving the panel and the map agree because both read the same graph.
- [ ] **Step 2:** FAIL, then write `spawn_state_panel`/`refresh_state_panel`. `SelectedCounty`
      (Task 7) wraps an ATLAS INDEX (`usize`), not a `NodeId` — the map's own vocabulary, matching
      `county_at`'s return type. Resolve the chain explicitly: atlas index -> `atlas.county(idx).fips`
      -> a linear scan of `session.node_by_fips` (twelve entries — a `HashMap` is not worth building
      for this size) for the matching FIPS -> its `NodeId`. A `SelectedCounty`/`HoveredCounty` whose
      atlas index resolves to a FIPS absent from `node_by_fips` (any of the 3,210 non-demo counties)
      renders the panel's honest "no data this tick" text, never a lookup panic — this is the same
      honest-absence shape Task 5's `LensReading` already establishes, applied here to the panel
      instead of the map. For a resolved `id`, read the four fields via
      `session.inner.graph().node_attribute(id, "...")` and render:

```text
<county name> (<fips>)
  pop-d:            2,150
  pop-p:            6,050
  pop-d-prime:      1,800
  legitimation:     STABLE (0)
```

- [ ] **Step 3: The event feed.** A scrolling text list, last 10 entries from
      `session.sink.events`, newest first, rendered as `<EventType> @ <county or n/a>` — reusing
      `CollectingSink`'s already-populated `events: Vec<(String, Vec<(String, Value)>)>` with no
      new sink type. Bounded to the last 10 by slicing, not by mutating `sink.events` (the sink
      accumulates the WHOLE session's history — acceptable at demo scale, a ring buffer is a
      documented future item if unbounded play sessions become a target, not built here).
- [ ] **Step 4: Headless test** for the event feed — after an `advance()` that fires
      `LEGITIMATION_RECOVERY` (Task 3's own recovering-county archetype guarantees this on tick 1),
      assert the feed's rendered text contains `"LEGITIMATION_RECOVERY"`.
- [ ] **Step 5:** `cargo test -p babylon-client` → PASS. Eyes-on: select a county, press Space,
      watch its panel numbers and the event feed both update.
- [ ] **Step 6: Commit** (`feat(client): the state panel and event feed (B2)`). Open the Phase D PR
      (`feat(client): B2 Phase D — the tick loop UI`); self-merge on green.

---

## Phase E — Logging, determinism, the eyes-on gate

### Task 12: Resurrect the client file-log sink

**Files:**

- Create: `rust/crates/babylon-client/src/logging.rs`
- Edit: `rust/crates/babylon-client/Cargo.toml`, `rust/crates/babylon-client/src/lib.rs`,
  `rust/crates/babylon-client/src/main.rs`

**Why resurrect rather than reinvent.** CLAUDE.md's client-logging directive: *"the deletion
ceremony retired `rust-client.log` (the Ratatui client's `log4rs` sink); the Bevy client's file
sink lands at milestone B2."* The deleted module (`git show
7d9f0d94^:rust/crates/babylon-tui/src/logging.rs`) carries proven, tested code that already solves
this problem — 10 MB size-triggered rotation, 5 fixed-window archives, file-only (never the
terminal, though Bevy has no alternate screen to corrupt the way the deleted Ratatui client did —
the constraint carries over anyway since a console `log4rs` sink would just duplicate Bevy's own
`tracing`-based `LogPlugin`, not harm it). **`log4rs` listens on the plain `log` facade; Bevy's own
console/dev logging runs on `tracing` via `bevy::log::LogPlugin`** — the two global dispatchers
(`log::set_logger` and `tracing::subscriber::set_global_default`) are independent slots, so both
coexist: Bevy's internals keep printing to the console through `tracing` exactly as
`DefaultPlugins` already wires it, and THIS crate's own `log::debug!`/`log::info!` calls (not
`bevy::log::info!`, which is `tracing`) go to the file sink only.

- [ ] **Step 1: Add dependencies**, the exact deleted feature set (`git show
      7d9f0d94^:rust/crates/babylon-tui/Cargo.toml` lines 36-42):

```toml
log = "0.4"
log4rs = { version = "1", default-features = false, features = [
    "rolling_file_appender",
    "compound_policy",
    "size_trigger",
    "fixed_window_roller",
    "pattern_encoder",
] }
```

- [ ] **Step 2: Resurrect the module**, transcribed from the deleted file with two changes: the
      sink filename `rust-client.log` → `babylon-client.log` (the retired name stays retired, per
      CLAUDE.md — this is a new client, not a relaunch of the old one) and the module doc's
      "terminal takeover" framing replaced with the Bevy-coexistence framing above.

```rust
//! File-only client logging (Director directive 2026-07-28; resurrected
//! for the Bevy client at Program 28 B2, per CLAUDE.md: "the Bevy client's
//! file sink lands at milestone B2"). Built on `log4rs` — the same crate
//! and the same rotation policy the deleted Ratatui client's
//! `babylon-tui::logging` used, transcribed here rather than reinvented.
//!
//! **Independent of Bevy's own logging.** `bevy::log::LogPlugin` runs on
//! `tracing` and keeps printing to stderr exactly as `DefaultPlugins`
//! wires it — untouched by this module. `log4rs` listens on the separate
//! `log` facade; this crate's OWN `log::debug!`/`log::info!` calls (never
//! `bevy::log::info!`, which is `tracing`) are what land in the file.
//!
//! **No wall-clock in client source.** Timestamps come from `log4rs`'s own
//! pattern encoder inside the appender.

use std::path::Path;
use std::sync::OnceLock;

use log::LevelFilter;
use log4rs::append::rolling_file::policy::compound::roll::fixed_window::FixedWindowRoller;
use log4rs::append::rolling_file::policy::compound::trigger::size::SizeTrigger;
use log4rs::append::rolling_file::policy::compound::CompoundPolicy;
use log4rs::append::rolling_file::RollingFileAppender;
use log4rs::config::{Appender, Config, Root};
use log4rs::encode::pattern::PatternEncoder;

const LOG_MAX_BYTES: u64 = 10 * 1024 * 1024;
const LOG_ARCHIVES: u32 = 5;

static INIT: OnceLock<()> = OnceLock::new();

/// `$XDG_DATA_HOME/babylon/logs` else `~/.local/share/babylon/logs` —
/// mirrors `src/babylon/config/paths.py::player_data_dir()` /
/// `src/babylon/config/base.py::LOG_DIR` exactly, transcribed rather than
/// re-derived (no PyO3 in the play path, Amendment AF, so this cannot call
/// the Python function — it reproduces its two-line rule instead).
#[must_use]
pub fn log_dir() -> std::path::PathBuf {
    let base = std::env::var_os("XDG_DATA_HOME")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|| {
            std::path::PathBuf::from(std::env::var_os("HOME").expect("HOME must be set"))
                .join(".local")
                .join("share")
        });
    base.join("babylon").join("logs")
}

/// Install the rolling-file logger writing `babylon-client.log` under
/// `log_dir`. `level` is one of `error|warn|info|debug|trace`.
///
/// # Errors
/// A config defect (bad level, non-UTF-8 log dir, log4rs init failure).
pub fn init_file_logging(log_dir: &Path, level: &str) -> Result<(), String> {
    let level_filter = parse_level(level)?;
    if INIT.get().is_some() {
        return Ok(());
    }
    let roll_pattern = log_dir.join("babylon-client.{}.log");
    let roller = FixedWindowRoller::builder()
        .build(
            roll_pattern
                .to_str()
                .ok_or_else(|| format!("log dir is not valid UTF-8: {}", log_dir.display()))?,
            LOG_ARCHIVES,
        )
        .map_err(|e| format!("log roller config: {e}"))?;
    let policy = CompoundPolicy::new(Box::new(SizeTrigger::new(LOG_MAX_BYTES)), Box::new(roller));
    let appender = RollingFileAppender::builder()
        .encoder(Box::new(PatternEncoder::new(
            "{d(%Y-%m-%dT%H:%M:%S%.3f)} [{l}] {t} — {m}{n}",
        )))
        .build(log_dir.join("babylon-client.log"), Box::new(policy))
        .map_err(|e| format!("log appender: {e}"))?;
    let config = Config::builder()
        .appender(Appender::builder().build("file", Box::new(appender)))
        .build(Root::builder().appender("file").build(level_filter))
        .map_err(|e| format!("log config: {e}"))?;
    log4rs::init_config(config).map_err(|e| format!("log init: {e}"))?;
    let _ = INIT.set(());
    install_panic_hook();
    Ok(())
}

fn parse_level(level: &str) -> Result<LevelFilter, String> {
    match level {
        "error" => Ok(LevelFilter::Error),
        "warn" => Ok(LevelFilter::Warn),
        "info" => Ok(LevelFilter::Info),
        "debug" => Ok(LevelFilter::Debug),
        "trace" => Ok(LevelFilter::Trace),
        other => Err(format!(
            "unknown log_level {other:?} (expected error|warn|info|debug|trace)"
        )),
    }
}

fn install_panic_hook() {
    let previous = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        log::error!(target: "panic", "client panic: {info}");
        log::logger().flush();
        previous(info);
    }));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn an_unknown_level_fails_loudly_even_after_init() {
        let err = init_file_logging(Path::new("/nonexistent"), "loudest").unwrap_err();
        assert!(err.contains("unknown log_level"));
    }

    #[test]
    fn init_writes_the_sink_and_reinit_is_a_noop_success() {
        let dir = std::env::temp_dir().join(format!("babylon-client-logtest-{}", std::process::id()));
        std::fs::create_dir_all(&dir).expect("test log dir");
        init_file_logging(&dir, "debug").expect("first init");
        log::debug!(target: "test", "sink probe line");
        log::logger().flush();
        let sink = dir.join("babylon-client.log");
        let written = std::fs::read_to_string(&sink).expect("sink exists");
        assert!(written.contains("sink probe line"));
        init_file_logging(&dir, "debug").expect("re-init is a no-op success");
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn log_dir_honors_xdg_data_home() {
        // SAFETY (single-threaded test process assumption noted, matching
        // the deleted module's own test posture): temporarily set the env
        // var, read log_dir(), restore it.
        let prior = std::env::var_os("XDG_DATA_HOME");
        std::env::set_var("XDG_DATA_HOME", "/tmp/xdg-probe");
        assert_eq!(log_dir(), std::path::PathBuf::from("/tmp/xdg-probe/babylon/logs"));
        match prior {
            Some(v) => std::env::set_var("XDG_DATA_HOME", v),
            None => std::env::remove_var("XDG_DATA_HOME"),
        }
    }
}
```

- [ ] **Step 3: Wire it in `main.rs`**, before `App::new()`:

```rust
fn main() {
    let log_dir = babylon_client::logging::log_dir();
    std::fs::create_dir_all(&log_dir).ok();
    if let Err(e) = babylon_client::logging::init_file_logging(&log_dir, "debug") {
        eprintln!("warning: client file logging did not start: {e}");
    }
    log::info!("babylon-client starting (B2 tick loop)");
    App::new()
        // ... unchanged ...
}
```

      A logging failure is a `warning`, not a panic — the game must still be playable with no
      writable log directory (a read-only filesystem, a sandboxed CI runner), which is exactly why
      Step 4's test needs no log directory to exist.
- [ ] **Step 4:** `cargo test -p babylon-client --lib logging` → PASS (all three tests). `mise run
      rust:check` → green. `cargo deny check` — `log4rs`/`log` are the same crates the deleted TUI
      already carried, and its `deny.toml`'s `allowlist` already names them; confirm rather than
      assume.
- [ ] **Step 5: Commit** (`feat(client): resurrect the log4rs file sink — babylon-client.log
      (B2)`).

### Task 13: End-to-end determinism guard

**Files:**

- Create: `rust/crates/babylon-client/tests/determinism.rs`

**Why this test exists separately from Task 2's `babylon-tick`-level version.** Task 2's test
proves `TickSession` itself is deterministic. This test proves the SAME property through the
client's own composed seam — `EngineSession::start` + repeated `advance()` — which is the actual
path a player's key presses drive, and the one the plan's own instructions ask to see "as a
committed test."

- [ ] **Step 1: Write the failing test.**

```rust
use babylon_client::engine_link::EngineSession;

#[test]
fn same_content_same_tick_count_yields_the_same_hash() {
    let mut a = EngineSession::start().expect("session a");
    let mut b = EngineSession::start().expect("session b");
    for tick in 1..=5 {
        let ra = a.advance().expect("a advances");
        let rb = b.advance().expect("b advances");
        assert_eq!(
            ra.after, rb.after,
            "tick {tick}: two independent EngineSessions over the same content must hash identically"
        );
    }
}

#[test]
fn five_ticks_produce_five_distinct_hashes() {
    // Regression guard against a driver that silently re-runs tick 1 —
    // exactly the bug TickSession's own tick-numbering (Task 2) exists to
    // prevent; this test watches for it at the client's seam too.
    let mut session = EngineSession::start().expect("session");
    let mut hashes = std::collections::HashSet::new();
    for _ in 0..5 {
        let report = session.advance().expect("advance");
        hashes.insert(report.after);
    }
    assert_eq!(hashes.len(), 5, "each tick must produce a distinct state hash");
}
```

- [ ] **Step 2:** FAIL until Task 9's `EngineSession` exists (this task can run any time after
      Task 9 — placed last only to sit beside Task 12's logging work in one PR).
- [ ] **Step 3:** `cargo test -p babylon-client --test determinism` → PASS.
- [ ] **Step 4: Commit** (`test(client): end-to-end determinism guard — same content, same tick
      count, same hash (B2)`).

### Task 14: The eyes-on gate

**Files:**

- Create: `rust/crates/babylon-client/tests/eyes_on_smoke.rs`
- Edit: `ai/state.yaml`

**Definition (replaces #262, per the roadmap spec §5's board-hygiene note).** A person satisfies
B2's eyes-on gate by:

1. Running `cargo run -p babylon-client`.
2. Seeing the county map render — the same borders and (now, Phase C) an initial band coloring on
   the twelve demo counties, everything else `PANEL`.
3. Pressing **Space** at least five times, and after each press observing every one of the
   following:
   - the tick counter (bottom-right) increments by exactly one;
   - the hash readout changes to a new hex string every press (never repeats — Task 13 proves this
     is a real property, not a hope);
   - at least one demo county's band color OR the selected/hovered county's state-panel numbers
     visibly changes (a tick where no county crosses a band boundary still moves the raw
     `pop-d`/`pop-p`/`pop-d-prime` numbers in the panel — "watch state change" needs no
     color flip on every single press);
   - the event feed grows (`LIFECYCLE_TRANSITION` alone fires every tick for every county).
4. Pressing **Tab**, confirming the active-lens label switches and the map recolors under the
   other lens's table.
5. Confirming the client wrote to `~/.local/share/babylon/logs/babylon-client.log` (or
   `$XDG_DATA_HOME/babylon/logs/`) after the run.

**The CI-safe proxy — everything from step 3 except the human's own eyes**, since no CI runner has
a display server or GPU (the same CI reality every headless test in this plan already works
inside):

```rust
// tests/eyes_on_smoke.rs — the scriptable half of the eyes-on gate. Never
// a replacement for the human pass above (nothing here can see a color on
// screen), but it proves every INPUT-DRIVEN, hash-provable claim that
// pass makes, so a future change that silently breaks the loop reds THIS
// gate in CI before a human ever has to notice by eye.
use bevy::asset::AssetPlugin;
use bevy::prelude::*;
use std::collections::HashSet;

#[test]
fn five_space_presses_advance_five_distinct_ticks_and_fire_lifecycle_events() {
    let mut app = App::new();
    app.add_plugins((MinimalPlugins, AssetPlugin::default(), InputPlugin));
    app.add_plugins(babylon_client::map::MapPlugin);
    app.add_plugins(babylon_client::loop_ui::TickLoopPlugin);
    app.update(); // Startup

    let mut hashes = HashSet::new();
    for _ in 0..5 {
        {
            let mut input = app.world_mut().resource_mut::<ButtonInput<KeyCode>>();
            input.press(KeyCode::Space);
        }
        app.update();
        {
            let mut input = app.world_mut().resource_mut::<ButtonInput<KeyCode>>();
            input.release(KeyCode::Space);
        }
        let session = app.world().resource::<babylon_client::engine_link::EngineSession>();
        hashes.insert(session.inner.graph().state_hash().expect("hash"));
    }
    assert_eq!(hashes.len(), 5, "five presses, five distinct hashes");

    let session = app.world().resource::<babylon_client::engine_link::EngineSession>();
    assert!(
        session
            .sink
            .events
            .iter()
            .any(|(name, _)| name == "EventType/LIFECYCLE_TRANSITION"),
        "the event feed must carry at least one real emitted event"
    );
}

#[test]
fn tab_flips_the_active_lens() {
    let mut app = App::new();
    app.add_plugins((MinimalPlugins, AssetPlugin::default(), InputPlugin));
    app.add_plugins(babylon_client::map::MapPlugin);
    app.update();

    let before = *app.world().resource::<babylon_client::map::ActiveLens>();
    {
        let mut input = app.world_mut().resource_mut::<ButtonInput<KeyCode>>();
        input.press(KeyCode::Tab);
    }
    app.update();
    let after = *app.world().resource::<babylon_client::map::ActiveLens>();
    assert_ne!(before, after, "Tab must flip the active lens");
}
```

- [ ] **Step 1:** Write both tests as shown, run against Phase C/D's finished code → FAIL until
      those phases land (this task sits last deliberately).
- [ ] **Step 2:** Once Phase C and Phase D land, both PASS. `mise run rust:check` → green.
- [ ] **Step 3:** Update `ai/state.yaml` — B2 reached: tick loop, dual-lens map, state panel, event
      feed, log sink, eyes-on gate defined and CI-proxied. Close #262 as "superseded — replaced by
      this gate" per the roadmap spec §5's own instruction, citing this plan document.
- [ ] **Step 4: Commit** (`test(client): the B2 eyes-on gate + its CI-safe proxy (B2)`).

### Task 15: Gates, docs, PR

- [ ] **Step 1:** `mise run rust:check` → green. `mise run check` → green.
- [ ] **Step 2:** `mise run qa:regression` and `mise run qa:vault-regression-ci` → byte-identical.
      Phase A's refactor is the only touch to `babylon-tick`'s existing behavior, and Task 1 Step 4
      already proved it moves nothing — this is the whole-repo confirmation.
- [ ] **Step 3:** Run `cargo test -p babylon-tick -p babylon-client` once more, full suite, to
      confirm every test across all five phases is green together, not just phase-by-phase.
- [ ] **Step 4:** Update `ai/state.yaml`'s Program 28 entry (B2 milestone reached — cite this plan
      document and the PR numbers) and the GitHub project board's client lane. Open the follow-up
      issue this plan's Sequencing/Content Decision sections defer (multi-rule-pack sessions;
      unbounded event-feed memory; the economics BSL port that would make the Tension lens tick-live
      too) — record it in the PR body per the B1 Task 12 precedent, don't silently drop it.
- [ ] **Step 5:** Open the PR (`feat(client): B2 — the tick loop on screen`), body carrying: the
      eyes-on human-pass screenshot/description, the Task 3 Step 1 FIPS table, the pinned
      determinism-guard output, and a link back to this plan document. Self-merge on green per the
      standing autonomy rulings.

---

## Open questions for the Director

1. **Does the new Legitimation lens need its own sign-off, the way ADR191 R11 ruled the Tension
   lens's four bands?** This plan's reasoning for proceeding without escalating: the Legitimation
   lens invents no new formula (it colors a categorical field the `lifecycle` rule pack already computes),
   uses only already-declared §9b palette tokens, and is additive to — never a replacement for —
   the Director-ruled Tension lens (a Tab key switches between them, both visible, neither hidden).
   But the Director has personally ruled every pixel-level choice on this map so far (font, insets,
   band count) — if that pattern is a standing expectation rather than a one-time settling of B1's
   specific open questions, this decision belongs to her, not to this plan's author. Recommend:
   proceed as specced (self-merge on green per the standing autonomy rulings), flag this plan
   document in the PR body, and let her veto after the fact if she intends that pattern to bind
   here too — cheaper than blocking a five-phase plan on a question this plan's own reasoning
   already answers defensibly.
2. **Should B2 defer multi-rule-pack sessions (running `vitality` and `lifecycle` together, live),
   or does the "watch state change" criterion implicitly want BOTH Material Base systems visible at
   once?** The Content Decision section above lays out the exact technical wall (`E-LOAD-001`, one
   `(rule …)` form per content set) and the two-part fix it would need. Recommend: defer, file the
   issue, proceed with the `lifecycle` rule pack alone — of the three merged packs, only its
   subject type matches the map's own unit, so it demonstrates the criterion fully on its own.
3. **This plan defers audio (SFX/soundtrack, ADR152/153) out of B2 entirely — it wires none of it,
   not even minimally.** Reasoning: R3's visual scope names "2D map game + panels and charts as the
   primary surface" with no audio obligation; wiring 39 SFX + 13 tracks properly (Bevy
   `AudioPlugin`, the `manifest.toml` trigger-mapping, mixing) is real, separately-scoped work, and
   B2 already carries five phases of new surface. This plan's author made this scope call rather
   than asking a question about it — this entry records the deferral so it stays visible rather
   than silent, per the Documentation philosophy's "immutability of history" discipline.
