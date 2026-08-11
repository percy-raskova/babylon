# Program 28 B2 — The Tick Loop On Screen: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to execute this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** close Program 28 §7 criterion 3 — a person opens `babylon-client`, sees the county map
B1 rendered, presses a key to advance the tick, and watches real state change: a tick counter, a
deterministic state-hash readout, a live per-county legitimation overlay on the map, a state panel
for the hovered/selected county, and an event feed — all driven by the Rust engine through a new
persistent tick-loop seam running TWO Material Base systems together, never a lookalike.

**Amendment record (2026-08-11, Director interactive ruling batch, this plan's own open
questions).** The first cut of this plan closed with three open questions. The Director ruled all
three, interactively, options quoted verbatim as presented and selected — the same citation
discipline ADR194 uses:

1. **Legitimation lens color mapping: APPROVED, reuse the band palette.** Selected option, quoted:
   *"CRISIS → crimson, UNSTABLE → dim gray, STABLE → gold's absence (panel dark) — reuses the
   ruled four-band vocabulary so the two lenses share one visual language. No new colors enter the
   game."*
2. **Demo content set: MULTI-RULE DRIVER FIRST — the Director OVERRULED this plan's single-pack
   recommendation.** Selected option, quoted: *"Build the multi-rule content-set evolution into B2
   itself so the demo runs vitality+lifecycle together from day one. Bigger B2, later criterion-3
   close, but a richer first demo."*
3. **Audio: DEFERRED out of B2**, per this plan's own recommendation — no change.

Ruling 2 is load-bearing: it reopens what the first cut called "Decision: the demo content set is
the lifecycle rule pack, alone" and inserts a new, genuinely non-trivial engine-lane evolution
(Phase A, Tasks 2–5 below) ahead of the demo-scenario task. This document renumbers and amends
every task list, file structure entry and cross-reference below to carry that decision out. The
three rulings'
full record, with reasoning, sits in the amended "Open questions for the Director" section at the
end — kept, not deleted, per the Documentation philosophy's immutability-of-history discipline;
what changed is that each question now carries its ruling instead of standing open.

**Architecture:** Five phases in five PRs, Phase A now doing two jobs. Phase A opens a
**persistent session** in `babylon-tick` — `TickSession<G>` — AND, ahead of that, widens the
content-set loader to admit **more than one `(rule …)` form**, in declaration order, the way
`bsl-language.rst` §2.2's grammar always admitted and `babylon-bsl`'s driver-level loader never
implemented. Phase B authors the **demo content**: eighteen subjects across two node types — twelve
real-FIPS territories carrying the already-conformance-tested `lifecycle` rule pack's four
archetype value sets, and six social classes carrying the already-conformance-tested `vitality`
rule pack's own fixture verbatim — so the demo runs two Material Base systems together from the
first tick. Phase C **completes B1's still-unbuilt Phase C** (`lens.rs`, `map/bands.rs`'s band
table, `map/pick.rs`, `map/hud.rs`) but generalizes it to carry TWO lenses side by side — ADR170's
static Tension lens (ported unmodified) and a new, tick-live Legitimation lens reading the field
`lifecycle` writes every tick, colored per the Director's ruling above — with a lens-picker key so
the player can see the difference between "declared once" and "moves every tick" honestly. Phase D
wires the **loop UI**: the advance-tick input, the tick counter, the hash readout, the state panel,
the event feed (now carrying both packs' events). Phase E resurrects the **file-log sink** the
deletion ceremony retired, proves **determinism** end-to-end, and defines the **eyes-on gate**.

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
  plan reuses R11's band table verbatim rather than re-deriving it, and (per this amendment's
  ruling 1) points the Legitimation lens at the SAME three of its four colors.
- **ADR193** — `babylon-tick::run_once`/`run_once_into` now construct `HypergraphStore`, not
  `MemoryGraph`; `state_hash()` calls `encode_state()`, and ADR193 measures that call QUADRATIC in
  hyperedge count on `HypergraphStore` (22.59 ms at n=2,000 hyperedges; 1.92 s at n=20,000). **This
  plan's own demo scenario mints eighteen nodes (twelve `NodeType/TERRITORY`, six
  `NodeType/SOCIAL_CLASS`) and zero hyperedges** — the cliff does not bite; see the Scale Note
  below for the arithmetic.
- **D96 (ADR191 R2)** — "a scenario is a canonical committed artifact and its declaration order is
  part of its identity" for NODE declarations; this plan's multi-rule evolution extends the same
  PRINCIPLE one level up, to RULE declarations within a content set (Phase A, Tasks 2–5) — it does
  not reopen D96 itself, which stays about node mint order.
- **Constitution III.7 (determinism)** and **III.11 (Loud Failure)** — the hash display exists
  because the hash IS the honesty proof; a county the demo scenario never minted stays `PANEL`,
  never a fabricated value.
- **R8/R9 (BSL-first porting, escape by proof)** — nothing in this plan adds Rust simulation logic;
  the only Rust code this plan writes is client/UI/seam code, a loader-widening change that makes
  the driver honor grammar §2.2 already admits (not a new primitive), and a factored-out loader
  helper. All simulation content stays in the already-merged `vitality` and `lifecycle` rule packs.
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
  `babylon-bsl`/`babylon-tick` — Phase A's Task 1 refactor and Task 4 widening must each move zero
  engine bytes on every EXISTING single-rule content set, and each task's own regression test is
  the first proof of that, not the only one.
- Vale: `vale <file>` on every Markdown page touched, driven to 0.
- **CI reality (unchanged from B1):** `rust-gate` runs on `ubuntu-latest`, compile-time Bevy
  headers only, no display server, no GPU. Every headless test in this plan uses `MinimalPlugins`
  plus `AssetPlugin`, never `DefaultPlugins`, exactly as B1's `tests/map_mesh.rs` and
  `tests/map_camera.rs` already establish.
- **Palette canon** — reuse only already-declared `§9b` tokens (`palette.rs`) and the already-ruled
  ADR170 four-band table (`PANEL`, `CRIMSON`, `DIM`, `GOLD` from `map/bands.rs`); per this
  amendment's ruling 1, the Legitimation lens's three colors are `PANEL` (STABLE — "gold's
  absence"), `DIM` (UNSTABLE), `CRIMSON` (CRISIS), reusing three of the FOUR already-declared
  `map/bands.rs` constants and minting none — GOLD is deliberately unused by this lens. This plan
  adds no new `Color::srgb_u8` literal anywhere, so
  `test_no_stray_color_literals_outside_palette_or_a_declared_exemption`'s sweep needs no new
  exemption entry.
- **The babylon-bsl surface this plan touches, stated exactly.** Every task reads live state
  through `GraphSubstrate`'s existing 14 methods and `CanonicalState`'s existing `state_hash` —
  unchanged. Two things ARE new, both flagged explicitly, both machinery rather than new
  mathematics or a new primitive (Amendment AE's test): (1) `babylon-tick::TickSession`, additive,
  `run_once`/`run_once_into` keep their exact current signatures; (2)
  `babylon-bsl::rule_pipeline::split_content` widens from "exactly one `(rule …)` top-form" to
  "one or more, in declaration order, duplicate ids refused" — closing a gap between the DRIVER's
  own historical restriction and what `bsl-language.rst` §2.2's grammar (`<top-form>*`) and prose
  ("Duplicate rule ids… across the content set are `E-LOAD-001`") always admitted. See the
  Multi-Rule Decision section below for the full design and why this is a driver fix, not a spec
  change.
- **Scale note (ADR193 arithmetic, worked here so no task has to re-derive it):** the Phase B demo
  scenario mints exactly 18 nodes (12 `NodeType/TERRITORY`, 6 `NodeType/SOCIAL_CLASS`) and declares
  no `(edge …)`/`(hyperedge …)` forms, so `HypergraphStore::encode_state`'s hyperedge half walks
  **zero** hyperedges regardless of the measured quadratic constant — the ADR193 table's smallest
  measured point (n=2,000 hyperedges, 22.59 ms) is already ~5,500x this plan's largest node count.
  `state_hash()` runs twice per `advance()` call (pre/post, per `TickSession::advance`), now
  bracketing TWO `run_tick` calls instead of one, against 18 nodes, ~90 scalar attributes and 0
  hyperedges — still sub-millisecond on the dyadic-half code path both stores share (ADR193:
  "`nodes`/`edges`/`neighbors` show no consistent direction at any scale"). The cliff is a real,
  documented future cost (ADR193's own "3,222-US-county target… plausibly crosses 10,000
  hyperedges once county-level organizational and sector memberships exist") — it belongs to
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
   unmodified) **and** a second, small three-row table for the Legitimation lens, colored per this
   amendment's ruling 1 — both are pure presentation constants, no `GameDefines`/`defines_hash`
   ceremony, exactly as ADR191 R11 already ruled for the first table.
3. `map/pick.rs` and `map/hud.rs` are B1 Task 10's designs, unmodified, except the HUD now also
   names which of the two lenses is active — this plan adds that honesty rule because two lenses
   share the color CRIMSON for two different meanings (Tension's "Φ-source, bled" vs. the
   Legitimation lens's "CRISIS"), and nothing may let a player read one as the other.

**One correction to B1's plan text, made explicit so no one silently inherits it wrong:** B1's
Task 8 spec writes `pub fn county_tension(graph: &MemoryGraph) -> TensionLens`. ADR193 (merged the
same day, sequenced textually after B1's plan but landed at the same `dev`-branch tip this plan
reads) swapped the production substrate from `MemoryGraph` to `HypergraphStore` — `run_once_into`
and, after Phase A of this plan, `TickSession`, both hold a `HypergraphStore`. **This plan's
`lens.rs` takes `&dyn GraphSubstrate`, not `&MemoryGraph`** — the trait both stores carry,
matching what the client actually holds. `MemoryGraph` remains only as the differential-test
oracle (ADR193's own consequences section).

## Decision: the demo content set runs `vitality` AND `lifecycle`, together, in declaration order

**Superseded by this amendment.** The first cut of this plan recommended running `lifecycle`
alone, citing a real technical wall: `babylon-bsl::rule_pipeline::split_content` enforces, by
construction (`rule_pipeline.rs:299-308`), exactly one `(rule …)` top-form per content set. The
Director overruled that recommendation (ruling 2, quoted above): B2 builds the multi-rule
evolution now. This section is the design that discharges that ruling, and it replaces the old
"Decision: the demo content set is the lifecycle rule pack, alone" section outright — the
technical-wall description below stays, because it remains the reason the evolution is real
engineering work and not a one-line flag flip.

### What §2.2 already admits, and what the driver never implemented

`bsl-language.rst` §2.2's own grammar has never limited a content set to one rule:

```text
<file>        ::= <top-form>*
<top-form>    ::= <rule> | <deffield> | <intrinsic-decl> | <manifest> | <metric-decl>
```

and its prose says, in the same section: *"A content set is the union of all files under the
declared content roots. File boundaries and file names carry no semantics… Duplicate rule ids,
duplicate field declarations, duplicate intrinsic declarations… across the content set are
`E-LOAD-001`."* Nothing there says "exactly one" — the grammar's `<top-form>*` is zero-or-more, and
the prose's whole framing (naming DUPLICATE ids as the violation) presupposes a content set can
legally hold two or more rules with DISTINCT ids. The current refusal text —

```text
"a content set needs exactly one (rule …) top-form, found {N}
 (§2.2 — intrinsic declarations do not count; deffield/manifest/metric-decl
 top-forms are not yet split out by this function and would also land here)"
```

— is `babylon-bsl::rule_pipeline::split_content`'s OWN cardinality check; the spec never demanded
it. This plan's evolution makes the driver honor what the grammar already admitted, which is why R8/R9
(BSL-first, escape by proof) and Amendment AE's "mints no new mathematics" test both read this as
machinery, not a new primitive needing a constitutional amendment.

### Execution order: declaration order in the concatenated content set (D96, extended)

D96 (ADR191 R2) ruled that a scenario's NODE declaration order is part of its identity — no test
may assert that shuffling `node` forms leaves the tick hash unchanged, because `NodeId` mints top
to bottom and "a reordered scenario is a different scenario." This plan's multi-rule driver applies
the SAME principle one level up: **the rules in a content set run in the order their `(rule …)`
forms appear in the string the driver reads**, and no test in this plan may assert that reordering
those forms leaves the tick hash — or, more precisely, `TickReport.per_rule_fired`'s own order —
unchanged. Concretely: `TickSession`/`run_once_into` build `rule_src` as ONE string (unchanged
signature — the caller concatenates whatever `.bsl` files it wants, in the order it wants them to
run), `split_content` parses every `(rule …)` top-form via the existing reader in the order it
encounters them (a plain sequential parse — no new ordering machinery), and the driver runs each
`LoadedRule` to completion, in that order, against the SAME graph, before moving to the next.

**Why NOT the formal `:anchor` mechanism.** `bsl-language.rst` §2.3 already specifies
`<anchor> ::= "(" "anchor" ( ":after" | ":before" ) <symbol> ")"` and a default ("a rule with no
`<anchor>` belongs to the system named by the first segment of its rule id and takes that system's
declared position") — this READS like the "real" answer to inter-rule ordering, and this plan's
author checked it first. It does not work here: `mod_anchors.rs`'s own module doc
says outright, *"this module validates the DECLARATION — shape, and the `E-LOAD-002` no-system
case. Resolving anchors into a total order belongs to `babylon-engine`'s anchor-based registry
(Phase 3)… deferred with a name, not silently."* `check_anchor` runs inside `load_rule_form` today
(`rule_pipeline.rs:245`) and stores the result on `LoadedRule.anchor` — but nothing anywhere reads
that field for ordering; no system-position registry exists to resolve `:after`/`:before` against.
Building that registry sits explicitly outside this plan's scope (a Phase 3 BSL-track milestone, not
a B2 client-lane task) and would be a large, separate undertaking. **Declaration order in the
concatenated content string is the right-sized INTERIM this specific milestone owns —
not a replacement for the eventual anchor-resolution engine, and not a claim that one will not
supersede it.** The `(anchor …)` forms Task 5 adds below remain purely declarative under this
plan — parsed, validated, and inert for ordering, exactly as they are for every other content set
in this repo today.

### The two rules' domains are disjoint — a subtlety worth stating precisely

`vitality/subsistence-and-death`'s bindings read/write only `social-class/*` fields and `economy/*`
constants; `lifecycle/dpd-circuit`'s bindings read/write only `territory/*` fields and `lifecycle/*`
constants (both verified by reading each rule's full `(bindings …)` block). Neither rule's subject
type, field reads, or field writes touch the other's. Two consequences follow, and BOTH matter to
how Task 5 builds its conformance test:

1. **The final canonical state hash is order-invariant for THIS pair, specifically**, because
   `CanonicalState::encode_state` sorts every section before hashing (ADR193) and the two rules'
   write-sets never overlap or interact — running vitality-then-lifecycle or lifecycle-then-vitality
   produces the identical SET of (node, attribute, value) triples, and a canonical sort of an
   identical set hashes identically either way. **This is an accident of this specific pair's
   disjoint domains, not a property of the multi-rule mechanism in general** — a future pair that
   shares a node type or cross-reads a field would NOT enjoy this invariance, and the driver must
   not (and does not) assume it does.
2. **Because of (1), a test that only asserts the final hash would NOT catch an order bug in this
   specific pair.** The load-bearing order-proof has to be something order actually moves:
   `TickReport.per_rule_fired`'s own sequence (Task 4) and the emitted event stream's sequence.
   Task 5's conformance test asserts on `per_rule_fired`'s order directly, and separately proves
   the mechanism reacts to a declaration-order flip, precisely because the hash offers no such
   guarantee here.

### Field and local-name collisions — checked, none found

The union scenario (Phase B) mints social-class nodes (`vitality`'s fixture) and territory nodes
(`lifecycle`'s fixture) side by side. Checked explicitly, not assumed:

- **`deffield` qnames**: `vitality-conformance.bscn` declares `social-class/{active, population,
  wealth, subsistence-multiplier, s-bio, s-class, inequality}` (7 fields, the 7th unread by the
  rule but seeded for fixture parity). `lifecycle-conformance.bscn` declares `territory/{pop-d,
  pop-p, pop-d-prime, wealth-d-prime, dependency-ratio, legitimation-index, legitimation-crisis,
  transmitted-ideology}` (8 fields). The owning node type prefixes every qname, per the
  language's own convention (§2.9) — the two sets share zero names by construction, not by luck.
- **`defconst` qnames**: `vitality` declares `economy/{base-subsistence, death-threshold}` (2).
  `lifecycle` declares 21 `lifecycle/*`-prefixed constants. Zero overlap.
- **Local node names**: `vitality`'s six fixture nodes carry the names `core`, `bourgeoisie`,
  `hermit`, `last-worker`, `remnant`, `dissolved`. `lifecycle`'s twelve demo nodes carry the names
  `county-<fips>` (Phase B, Task 7). Zero overlap — `load_scenario`'s duplicate-local-name
  check (`scenario.rs`) never fires.
- **`CardinalityCeilings`**: `prepare_rule`'s existing ceiling-building code
  (`scenario.node_types.iter().map(...)`) is already generic over any number of distinct
  `NodeType` members a scenario mints — verified by reading it; no change needed for two node
  types instead of one, and Task 6 keeps this code path unmodified.
- **`systems` registry**: the existing fixed `HashSet` in `prepare_rule`/`prepare_rules`
  already contains both `"vitality"` and `"lifecycle"` (it has since the lifecycle port merged) —
  no change needed there either.

---

## File Structure

| Phase | File | Action | Responsibility |
|---|---|---|---|
| A | `rust/crates/babylon-tick/src/lib.rs` | Edit | Factor `prepare_rule` out of `run_once_into`; later widen to `prepare_rules`; add `pub mod session;` |
| A | `rust/crates/babylon-bsl/src/rule_pipeline.rs` | Edit | `split_content` admits more than one `(rule …)` form, duplicate-id check |
| A | `docs/reference/bsl-language.rst` | Edit | New D-row (D99) documenting the widened driver + declaration-order semantics |
| A | `rust/crates/babylon-tick/content/rules/lifecycle.bsl` | Edit | Add `(anchor :after vitality)` — declarative only, inert for ordering today |
| A | `rust/crates/babylon-tick/content/scenarios/vitality-lifecycle-combined-conformance.bscn` | Create | The 10-node conformance fixture (6 vitality + 4 lifecycle, verbatim) |
| A | `rust/crates/babylon-tick/tests/multi_rule_conformance.rs` | Create | Declaration-order-reproduces-engine-order proof |
| A | `rust/crates/babylon-tick/src/session.rs` | Create | `TickSession<G>` — load once, `advance()` many times, now multi-rule |
| B | `rust/crates/babylon-client/tests/print_demo_counties.rs` | Create (throwaway aid) | One-shot atlas print, deleted after use |
| B | `rust/crates/babylon-tick/content/scenarios/us-counties-lifecycle-demo.bscn` | Create | 18-node demo: 12 real-FIPS territories + 6 social classes |
| C | `rust/crates/babylon-client/src/lens.rs` | Create | `county_tension` (ADR170, ported) + `county_legitimation` (new) |
| C | `rust/crates/babylon-client/src/map/bands.rs` | Edit | ADR191 R11's `band_color` (Tension) + legitimation band function (Director ruling 1) |
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

## Phase A — The persistent tick session, and the multi-rule content-set evolution

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

**Deliberately single-rule.** This task's `PreparedRule`/`prepare_rule` hold exactly ONE
`LoadedRule`, matching `split_content`'s CURRENT (pre-Task-2) one-rule cardinality — the smallest,
safest first step, proven against the existing single-rule goldens before Task 2 widens the loader
underneath it. Task 4 renames and widens this to `PreparedRules`/`prepare_rules`; this task's job
is only to prove the pure-extraction refactor is behavior-preserving in isolation first.

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
/// and, from Task 4 on, `prepare_rules`'s multi-rule successor.
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
        per_rule_fired: vec![(prepared.loaded_rule_id.clone(), outcome.fired)],
    })
}
```

      Note the pre-tick hash is now taken AFTER `prepare_rule` returns rather than immediately
      after `load_scenario` — this is the same point in program order (nothing between the old
      `load_scenario` call and the old `before` computation touches `graph`), so the hash value is
      identical; only the code that produces it moved. **`per_rule_fired` does not exist yet at
      this step** — Task 4 adds `TickReport.per_rule_fired` and the `loaded_rule_id` field this
      line anticipates; write `run_once_into` WITHOUT that line for this task (`fired:
      outcome.fired` only, matching today's struct), and let Task 4 add the field and this line
      together. Flagged here so the two tasks' interfaces read as one coherent design, not two
      that happen to agree.
- [ ] **Step 4:** Run both Step 1 tests again → PASS, byte-identical hash. `mise run rust:check` →
      green. `mise run qa:regression` and `mise run qa:vault-regression-ci` → byte-identical (this
      refactor is inside the engine crate; both gates must stay silent).
- [ ] **Step 5: Commit** (`refactor(rust): factor prepare_rule out of run_once_into — zero behavior
      change (B2)`).

### Task 2: Widen `split_content` to admit more than one `(rule …)` form

**Files:**

- Edit: `rust/crates/babylon-bsl/src/rule_pipeline.rs`

**Interfaces:**

- Produces: `pub fn split_content(source: &str) -> Result<(Vec<SExpr>, Vec<SExpr>), LoadError>` —
  the SAME function name, now returning the intrinsic-decl forms plus a **non-empty, ordered**
  `Vec<SExpr>` of every `(rule …)` top-form, duplicate ids refused. **Signature change**:
  the second element of the tuple was `SExpr` (exactly one), is now `Vec<SExpr>` (one or more, in
  source order) — every caller (`prepare_rule` today, `prepare_rules` from Task 4) updates in the
  same PR.
- Also produces: `fn rule_id(rule: &SExpr) -> Result<String, LoadError>` — a small new helper
  reading a `(rule …)` form's `<qname>` (the second list element, per §2.3's grammar), used by the
  duplicate-id check and reusable wherever a caller needs a rule's own id without re-parsing.

- [ ] **Step 1: Write the failing tests.** In `rule_pipeline.rs`'s existing `#[cfg(test)] mod
      tests`:

```rust
#[test]
fn split_content_admits_two_rules_in_source_order() {
    let source = r"
(rule a/first :material-basis "x" :fuel 10
  (bindings (binding v :field a/v))
  (effects (update-node self a/v (set v))))
(rule b/second :material-basis "y" :fuel 10
  (bindings (binding v :field b/v))
  (effects (update-node self b/v (set v))))
";
    let (_intrinsics, rules) = split_content(source).expect("two distinct rule ids load");
    assert_eq!(rules.len(), 2);
    assert_eq!(rule_id(&rules[0]).unwrap(), "a/first");
    assert_eq!(rule_id(&rules[1]).unwrap(), "b/second");
}

#[test]
fn split_content_still_admits_exactly_one_rule() {
    // The pre-Task-2 shape stays legal — this widening is additive, never
    // a floor raise. Every existing single-rule content set in the repo
    // must keep loading unchanged.
    let source = r#"(rule a/only :material-basis "x" :fuel 10
  (bindings (binding v :field a/v))
  (effects (update-node self a/v (set v))))"#;
    let (_intrinsics, rules) = split_content(source).expect("one rule still loads");
    assert_eq!(rules.len(), 1);
}

#[test]
fn split_content_refuses_zero_rules() {
    let err = split_content("").unwrap_err();
    assert!(err.to_string().contains("found 0"));
}

#[test]
fn a_duplicate_rule_id_across_the_content_set_is_e_load_001() {
    let source = r#"
(rule a/dup :material-basis "x" :fuel 10
  (bindings (binding v :field a/v))
  (effects (update-node self a/v (set v))))
(rule a/dup :material-basis "y" :fuel 10
  (bindings (binding v :field a/v2))
  (effects (update-node self a/v2 (set v))))
"#;
    let err = split_content(source).unwrap_err();
    assert!(err.to_string().contains("E-LOAD-001"));
    assert!(err.to_string().contains("a/dup"));
}
```

- [ ] **Step 2:** `cargo test -p babylon-bsl` → FAIL (the current `<[SExpr; 1]>::try_from` cardinality
      check refuses two rules; the return type does not compile against `Vec<SExpr>` callers yet).
- [ ] **Step 3: Widen the function.** Replace the current

```rust
match <[SExpr; 1]>::try_from(rule_forms) {
    Ok([rule]) => Ok((intrinsic_forms, rule)),
    Err(rule_forms) => Err(LoadError::Content(format!(
        "a content set needs exactly one (rule …) top-form, found {} …",
        rule_forms.len()
    ))),
}
```

      with:

```rust
if rule_forms.is_empty() {
    return Err(LoadError::Content(
        "a content set needs at least one (rule …) top-form, found 0 \
         (§2.2 — intrinsic declarations do not count; deffield/manifest/metric-decl \
         top-forms are not yet split out by this function and would also land here)"
            .to_owned(),
    ));
}
let mut seen: HashMap<String, ()> = HashMap::with_capacity(rule_forms.len());
for form in &rule_forms {
    let id = rule_id(form)?;
    if seen.contains_key(&id) {
        return Err(LoadError::Content(format!(
            "E-LOAD-001: duplicate rule id: {id} (§2.2 — rule ids must be \
             content-set-unique, the same duplicate-name discipline \
             parse_intrinsic_decls already enforces for intrinsic \
             declarations)"
        )));
    }
    seen.insert(id, ());
}
Ok((intrinsic_forms, rule_forms))
```

      matching the EXACT `HashMap::contains_key`-before-insert pattern
      `declarations::parse_intrinsic_decls` already uses for duplicate intrinsic names (same file
      family, same §2.2 duplicate-name discipline) — reused, not reinvented, per DRY. Add `rule_id`:

```rust
/// A `(rule …)` form's own `<qname>` — the second list element, per §2.3's
/// `<rule> ::= "(" "rule" <qname> …`. Used by the duplicate-id check and by
/// any caller (Task 4's `prepare_rules`) that needs a rule's id without
/// re-parsing its surface.
fn rule_id(rule: &SExpr) -> Result<String, LoadError> {
    let SExpr::List(items) = rule else {
        return Err(LoadError::Content(format!(
            "expected a (rule …) form, found {rule:?}"
        )));
    };
    match items.get(1) {
        Some(SExpr::Atom(Atom::Symbol(id))) => Ok(id.clone()),
        other => Err(LoadError::Content(format!(
            "a (rule …) form's second element must be its qname, found {other:?}"
        ))),
    }
}
```

- [ ] **Step 4:** `cargo test -p babylon-bsl` → PASS (all four new tests; every EXISTING
      `split_content`/`load_rule_form` test in the crate still green — this is additive, not a
      behavior change for single-rule content). Update `prepare_rule` (Task 1) to destructure the
      now-`Vec<SExpr>` second element as `rule_forms[0].clone()` (still one rule at this point in
      the plan; Task 4 removes the `[0]` indexing when it widens to multi-rule) — a small,
      mechanical signature-follow, not a behavior change.
- [ ] **Step 5:** `mise run rust:check` → green (workspace-wide — this crate's callers in
      `babylon-tick` must still compile). `mise run qa:regression` → byte-identical.
- [ ] **Step 6: Commit** (`feat(rust): split_content admits more than one (rule …) form, duplicate ids
      refused (B2) — honors §2.2's already-ratified grammar`).

### Task 3: The D99 spec row — documenting the widened driver

**Files:**

- Edit: `docs/reference/bsl-language.rst`

**Why this is a task, not a footnote.** The D-row discipline (D80…D98 already in the table) is
this document's own normative-home rule: a workforce reading that changes what the DRIVER accepts,
even when the change is "honor what the grammar already said," gets its own row so a future reader
does not have to reconstruct the reasoning from a Rust doc comment. This follows D97/D98's own
precedent — "a Phase-1-review reading… open to correction, not a Director ruling" — the same
posture this row takes.

- [ ] **Step 1: Add D99** to the D-row list-table (after D98, following the exact three-column
      format every row above it uses):

```rst
   * - D99
     - §2.2, §2.3, §5.5
     - **The content-set loader admits more than one ``(rule …)`` top-form, in
       declaration order, duplicate ids refused** — a driver-level fix
       (Program 28 B2), not a spec change. §2.2's grammar (``<top-form>*``)
       and prose ("Duplicate rule ids… across the content set are
       ``E-LOAD-001``") never limited a content set to one rule;
       ``babylon-bsl::rule_pipeline::split_content`` did, by an
       implementation-level cardinality check with no textual basis in this
       section. This row lifts that check to match the grammar it was
       always supposed to implement. **Execution order is declaration
       order in the content set the driver reads** — the same principle
       D96 states for node declarations, applied one level up to rule
       declarations: no test may assert that reordering a content set's
       ``(rule …)`` forms leaves ``TickReport.per_rule_fired``'s own order
       unchanged, because it is not meant to. **This is NOT the ``:anchor``
       mechanism** (§2.3's ``<anchor>``) resolved into a total order —
       ``mod_anchors.rs``'s own scope note defers anchor RESOLUTION to a
       future ``babylon-engine`` anchor-based registry (Phase 3), which
       does not exist yet; ``(anchor …)`` forms remain parseable and
       validated (``check_anchor``, unchanged) but inert for ordering under
       this row, exactly as before it. §5.5's ``rules_hash`` stays
       file-boundary- and (for CAS/identity purposes) order-insensitive —
       that is a claim about content IDENTITY, separate from the EXECUTION
       order this row rules on, and the two do not conflict.
       Reference implementation: ``rule_pipeline::split_content``,
       ``rule_pipeline::rule_id`` (Program 28 B2, `docs/superpowers/plans/
       2026-08-11-b2-tick-loop-plan.md` Phase A Tasks 2–4).
```

- [ ] **Step 2: Sync `bsl.ebnf` if it encodes a rule-cardinality constraint.** Grep it for any
      `<file>`/`<top-form>` production carrying an explicit "exactly one rule" note; §2.2's own
      grammar block above (the normative one) never had one, so this step is almost certainly a no-op —
      confirm rather than assume, per the D95/D98 precedent of keeping the appendix and the section
      text in the same commit when they diverge.
- [ ] **Step 3:** `vale docs/reference/bsl-language.rst` → 0 (this file already carries a project
      vocabulary; this row's prose should clear it without a new exemption).
- [ ] **Step 4: Commit** (`docs(bsl): D99 — the content-set loader honors §2.2's multi-rule grammar
      (B2)`), sequenced right after Task 2 since it documents exactly that change.

### Task 4: `prepare_rule` → `prepare_rules`; `run_once_into` runs every rule in order

**Files:**

- Edit: `rust/crates/babylon-tick/src/lib.rs`

**Interfaces:**

- Produces: `pub(crate) struct PreparedRules { rules: Vec<(String, LoadedRule)>, types: TypeEnv,
  intrinsics: IntrinsicCosts, consts: HashMap<String, Value> }` (each entry pairs a rule's own id
  with its `LoadedRule`, in DECLARATION order) and `pub(crate) fn prepare_rules<G: GraphSubstrate +
  CanonicalState>(scenario_src: &str, rule_src: &str, graph: &mut G) -> Result<PreparedRules,
  String>` — `prepare_rule`'s direct successor, same shape, now walking every rule `split_content`
  returns instead of indexing `[0]`.
- **`TickReport` gains one field, existing fields UNCHANGED in type** — this is the compatibility
  design this task commits to, checked against every current reader of `.fired`:

```rust
pub struct TickReport {
    pub before: [u8; 32],
    pub after: [u8; 32],
    /// The TOTAL fired-subject count across every rule this tick ran —
    /// unchanged in meaning and type for a single-rule content set (today
    /// every existing caller: `run_once`, the CLI, B0's engine-link probe,
    /// every `*_conformance.rs` test). For a multi-rule tick this is the
    /// SUM across rules — kept a plain `usize` rather than widened to
    /// `Vec<usize>` specifically so `report.fired == N` assertions in
    /// `tests/vitality_conformance.rs`, `tests/lifecycle_conformance.rs`,
    /// `tests/lifecycle_crisis_conformance.rs` and
    /// `tests/floor_intrinsic_e2e.rs` (five call sites, grepped and
    /// confirmed) keep compiling and keep passing unmodified.
    pub fired: usize,
    /// Per-rule detail, in DECLARATION/EXECUTION order — `(rule_id,
    /// fired)`. Length 1 for every existing single-rule content set
    /// (`fired == per_rule_fired[0].1` always holds); length N for an
    /// N-rule content set. This is what Task 5's conformance test and
    /// Phase D's event feed actually need — a summed `fired` alone cannot
    /// tell "5 subjects fired" from "vitality fired on 3, lifecycle on 2".
    pub per_rule_fired: Vec<(String, usize)>,
}
```

- [ ] **Step 1: Write the failing regression tests FIRST**, proving the additive-field design holds
      for every EXISTING single-rule caller before writing the multi-rule path:

```rust
// lib.rs's existing #[cfg(test)] mod tests, extended:
#[test]
fn single_rule_content_still_reports_fired_and_a_one_entry_per_rule_fired() {
    let report = run_once(SCENARIO, RULE).expect("single-rule run");
    assert_eq!(report.per_rule_fired.len(), 1);
    assert_eq!(report.per_rule_fired[0].1, report.fired);
}
```

      Also re-run, unmodified, the five existing `.fired`-reading tests named in the doc comment
      above (`tests/vitality_conformance.rs`, `tests/lifecycle_conformance.rs`,
      `tests/lifecycle_crisis_conformance.rs`, `tests/floor_intrinsic_e2e.rs` ×2 assertions) —
      these must compile and pass with ZERO edits, since `fired`'s type did not change.
- [ ] **Step 2:** `cargo test -p babylon-tick -p babylon-bsl` → FAIL (`per_rule_fired` field does
      not exist; `prepare_rules` does not exist).
- [ ] **Step 3: Widen `prepare_rule` into `prepare_rules`.**

```rust
pub(crate) struct PreparedRules {
    pub rules: Vec<(String, LoadedRule)>,
    pub types: TypeEnv,
    pub intrinsics: IntrinsicCosts,
    pub consts: HashMap<String, Value>,
}

pub(crate) fn prepare_rules<G: GraphSubstrate + CanonicalState>(
    scenario_src: &str,
    rule_src: &str,
    graph: &mut G,
) -> Result<PreparedRules, String> {
    let (intrinsic_forms, rule_forms) = split_content(rule_src).map_err(|e| e.to_string())?;
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

    // ONE shared LoadContext for every rule in the content set — the
    // vocabulary/types/ceilings come from the SCENARIO, not from any one
    // rule, and each rule's own load only reads the subset its bindings
    // reference (verified: no cross-rule interference for vitality +
    // lifecycle, whose bindings are wholly disjoint — see the Multi-Rule
    // Decision section's domain-disjointness note).
    let ctx = LoadContext {
        vocabulary: &vocabulary,
        types: &types,
        ceilings: &ceilings,
        intrinsics: &intrinsics,
        systems: &systems,
        vocabulary_registry: None,
        rule_file: "rule",
    };

    // rule_forms is already in DECLARATION order (split_content, Task 2) —
    // load_rule_form runs once per form, in that same order, and this loop
    // preserves it into `rules`.
    let mut rules = Vec::with_capacity(rule_forms.len());
    for form in rule_forms {
        let id = rule_pipeline::rule_id(&form).map_err(|e| e.to_string())?;
        let loaded = load_rule_form(form, &ctx)
            .map_err(|e| format!("rule {id} rejected: {e}"))?;
        rules.push((id, loaded));
    }

    Ok(PreparedRules {
        rules,
        types,
        intrinsics,
        consts: scenario.consts,
    })
}
```

      `rule_id` needs `pub(crate)` visibility from Task 2 (it was `fn`, private to
      `rule_pipeline.rs`, in babylon-bsl — a different crate from babylon-tick, so it must be
      `pub` there, not merely `pub(crate)`; correct Task 2's visibility to `pub fn rule_id` if this
      step needs it externally, which it does).
- [ ] **Step 4: Rewrite `run_once_into` to loop.**

```rust
pub fn run_once_into<G: GraphSubstrate + CanonicalState>(
    scenario_src: &str,
    rule_src: &str,
    graph: &mut G,
    sink: &mut CollectingSink,
) -> Result<TickReport, String> {
    let prepared = prepare_rules(scenario_src, rule_src, graph)?;

    let before = graph
        .state_hash()
        .map_err(|e| format!("pre-tick state: {}", e.message))?;

    let mut per_rule_fired = Vec::with_capacity(prepared.rules.len());
    for (id, loaded) in &prepared.rules {
        let outcome = run_tick(
            loaded,
            &prepared.types,
            &KernelIntrinsicHost,
            graph,
            sink,
            &prepared.intrinsics,
            &prepared.consts,
            1,
        )
        .map_err(|e| format!("tick failed in rule {id}: {e}"))?;
        per_rule_fired.push((id.clone(), outcome.fired));
    }
    let fired = per_rule_fired.iter().map(|(_, n)| n).sum();

    let after = graph
        .state_hash()
        .map_err(|e| format!("post-tick state: {}", e.message))?;

    Ok(TickReport {
        before,
        after,
        fired,
        per_rule_fired,
    })
}
```

      Every rule in `prepared.rules` runs to COMPLETION (every matching subject) before the next
      rule starts — never interleaved — against the SAME `graph`, so a later rule sees an EARLIER
      rule's writes from the SAME tick, matching the frozen engine's own in-place, strict-order
      mutation semantics (CLAUDE.md: "Systems mutate the shared graph in-place in strict order…
      each system sees prior systems' mutations") for free, with no new mechanism — this falls out
      of calling `run_tick` sequentially against one `&mut G`.
- [ ] **Step 5:** `cargo test -p babylon-tick` → PASS (the new regression test; all five
      externally-grepped `.fired` call sites still green, unmodified). `mise run rust:check` →
      green. `mise run qa:regression` and `mise run qa:vault-regression-ci` → byte-identical (this
      widening must move zero bytes for every EXISTING single-rule content set — the whole point of
      the additive-field design).
- [ ] **Step 6: Commit** (`feat(rust): prepare_rules — the multi-rule content-set loader, per-rule
      fired detail (B2)`).

### Task 5: The multi-rule conformance vector — declaration order reproduces engine order

**Files:**

- Create: `rust/crates/babylon-tick/content/scenarios/vitality-lifecycle-combined-conformance.bscn`
- Create: `rust/crates/babylon-tick/content/scenarios/vitality_lifecycle_combined_conformance.py`
- Create: `rust/crates/babylon-tick/tests/multi_rule_conformance.rs`
- Edit: `rust/crates/babylon-tick/content/rules/lifecycle.bsl` (one line: `(anchor :after
  vitality)`)

**The point of this task.** Proves the mechanism Tasks 2 and 4 built actually reproduces the frozen
engine's own two-systems-in-order behavior (`VitalitySystem` @1, `LifecycleSystem` @7) — the
conformance approach the Director's ruling called for — and, because the two rules' domains are
disjoint (Multi-Rule Decision section), proves it with the RIGHT assertion (`per_rule_fired`'s
order), not the assertion that would silently pass even with a broken driver (the final hash).

- [ ] **Step 1: The declarative anchor.** Add `(anchor :after vitality)` to `lifecycle.bsl`'s
      `(rule lifecycle/dpd-circuit …)` form, between its `:fuel` keyword and its `(bindings …)`
      form, matching §2.3's grammar position (`<domain>? <anchor>? <bindings>`). This is inert for
      ordering today (Task 4's driver does not read `.anchor`; no test may assert it does) —
      forward-documentation for the eventual Phase 3 anchor-resolution registry, landed now while
      the fact ("lifecycle runs after vitality") is fresh, cheap to state, and already true by
      construction of this task's own content-string ordering. Confirm `check_anchor` still
      accepts the form (`cargo test -p babylon-bsl` — the existing `lifecycle.bsl` parse/load
      tests must stay green; adding a valid, well-formed anchor changes nothing else about the
      rule's load).
- [ ] **Step 2: The 10-node combined-conformance scenario.** Union `vitality-conformance.bscn`'s
      six social-class nodes (`core`, `bourgeoisie`, `hermit`, `last-worker`, `remnant`,
      `dissolved`, every field value transcribed byte-for-byte) and `lifecycle-conformance.bscn`'s
      four territory nodes (`core-county`, `growing-county`, `recovering-county`, `young-county`,
      same transcription discipline) into ONE `.bscn` file, combining the `deffield`/`defconst`
      blocks (21 + 7 declarations — the Multi-Rule Decision section's collision check already confirms
      zero name overlap so this is a straight concatenation, not a merge requiring judgment calls).
      Name it `vitality-lifecycle-combined-conformance.bscn`; a dedicated, small, ALREADY-PROVEN
      fixture, kept separate from Phase B's larger, real-FIPS-flavored demo scenario — this task's
      job is proving the MECHANISM, Phase B's is building the PLAYABLE world, and conflating them
      would make a mechanism bug harder to isolate from a demo-content bug.
- [ ] **Step 3: The combined Python reference script.** `vitality_lifecycle_combined_conformance.py`
      mirrors the calling convention `vitality_conformance.py` and `lifecycle_conformance.py`
      already establish (both exist in this same directory — read them first, match their
      structure, do not invent a new one): build ONE `WorldState`/graph carrying all ten fixture
      nodes (the Step 2 values), then call `VitalitySystem().step(state)` FOLLOWED BY
      `LifecycleSystem().step(state)` — matching the frozen engine's own tick-position order
      (Vitality @1, Lifecycle @7) — and print every post-tick field this task's Rust test needs to
      pin, for BOTH the six social-class nodes and the four territory nodes.
- [ ] **Step 4: Write the failing Rust test.**

```rust
// tests/multi_rule_conformance.rs
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_tick::{run_once_into, hex};

const SCENARIO: &str =
    include_str!("../content/scenarios/vitality-lifecycle-combined-conformance.bscn");
const VITALITY: &str = include_str!("../content/rules/vitality.bsl");
const LIFECYCLE: &str = include_str!("../content/rules/lifecycle.bsl");

#[test]
fn declaration_order_matching_engine_order_reproduces_the_frozen_engine() {
    // vitality text FIRST, lifecycle text SECOND — Vitality @1 before
    // Lifecycle @7, the frozen engine's own tick-position order.
    let rule_src = format!("{VITALITY}\n{LIFECYCLE}");
    let mut graph = HypergraphStore::new();
    let mut sink = CollectingSink::default();
    let report = run_once_into(SCENARIO, &rule_src, &mut graph, &mut sink).expect("tick");

    // THE ORDER PROOF — per Multi-Rule Decision, the final hash would NOT
    // catch an order bug for this disjoint-domain pair, so this is the
    // load-bearing assertion, not the hash.
    assert_eq!(report.per_rule_fired.len(), 2);
    assert_eq!(report.per_rule_fired[0].0, "vitality/subsistence-and-death");
    assert_eq!(report.per_rule_fired[1].0, "lifecycle/dpd-circuit");
    // Exact counts pinned from Step 3's printed Python reference —
    // transcribe the real numbers here once the script has run; both
    // vitality-conformance.bscn (5 of 6 subjects pass the guard, per the
    // existing pinned test) and lifecycle-conformance.bscn's own fixture
    // are individually proven, so these counts should match those
    // existing pins exactly, unchanged by union.
    assert_eq!(report.per_rule_fired[0].1, /* vitality fired count */ 0);
    assert_eq!(report.per_rule_fired[1].1, /* lifecycle fired count */ 0);

    // Per-node field values match the Step 3 combined Python reference —
    // both halves, transcribed from its printed output.
    // (concrete node_attribute assertions per Step 3's script output)
}

#[test]
fn flipping_declaration_order_flips_per_rule_fired_order() {
    // The mechanism proof: swap which text comes first, and the ORDER
    // Task 4's loop reports flips with it — a hash-based assertion could
    // not show this for a disjoint pair (Multi-Rule Decision section), so
    // this test exists specifically to prove the mechanism, not the
    // content.
    let rule_src = format!("{LIFECYCLE}\n{VITALITY}");
    let mut graph = HypergraphStore::new();
    let mut sink = CollectingSink::default();
    let report = run_once_into(SCENARIO, &rule_src, &mut graph, &mut sink).expect("tick");
    assert_eq!(report.per_rule_fired[0].0, "lifecycle/dpd-circuit");
    assert_eq!(report.per_rule_fired[1].0, "vitality/subsistence-and-death");
    // The FINAL state hash, by contrast, is expected to be IDENTICAL to
    // the previous test's — documenting the domain-disjointness finding
    // as a live, checked property rather than an assertion left silent.
}
```

- [ ] **Step 5:** Run the Python script, transcribe its printed values into Step 4's placeholder
      assertions and node-attribute checks (never leave a placeholder number in the committed
      test — this step exists precisely to replace them with the real, printed values). `cargo
      test -p babylon-tick --test multi_rule_conformance` → PASS.
- [ ] **Step 6:** `mise run rust:check` → green. `mise run qa:regression` → byte-identical (this
      task adds content and a test; it must not move any existing engine byte).
- [ ] **Step 7: Commit** (`test(content): multi-rule conformance — vitality+lifecycle in
      declaration order reproduces the frozen engine (B2)`).

### Task 6: `TickSession<G>` — load once, advance many times, now multi-rule

**Files:**

- Create: `rust/crates/babylon-tick/src/session.rs`
- Edit: `rust/crates/babylon-tick/src/lib.rs` (`pub mod session;`, re-export)

**Interfaces:**

- Produces:

```rust
pub struct TickSession<G> { /* private: graph, prepared: PreparedRules, tick */ }

impl<G: GraphSubstrate + CanonicalState> TickSession<G> {
    pub fn new(scenario_src: &str, rule_src: &str, graph: G) -> Result<Self, String>;
    pub fn advance(&mut self, sink: &mut CollectingSink) -> Result<TickReport, String>;
    pub fn tick(&self) -> i64;
    pub fn graph(&self) -> &G;
}
```

  Same four-method public surface as the first cut of this plan — the multi-rule widening is
  entirely internal (`PreparedRule` → `PreparedRules`, one `run_tick` call → a loop). Every later
  task in this plan (Phase C's lens producers, Phase D's UI) reads state through `session.graph()`
  and drives the loop through `session.advance(&mut sink)`, unchanged. This is the ONE
  `babylon-tick` API addition this plan makes on top of the language-crate widening — `run_once`,
  `run_once_into` keep their exact current signatures; `TickReport` gains the additive
  `per_rule_fired` field (Task 4), which every reader of `.fired` ignores without needing to change.

- [ ] **Step 1: Write the failing tests.**

```rust
use crate::session::TickSession;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;

const SCENARIO: &str =
    include_str!("../content/scenarios/vitality-lifecycle-combined-conformance.bscn");
const VITALITY: &str = include_str!("../content/rules/vitality.bsl");
const LIFECYCLE: &str = include_str!("../content/rules/lifecycle.bsl");

fn rule_src() -> String {
    format!("{VITALITY}\n{LIFECYCLE}")
}

#[test]
fn advance_numbers_ticks_starting_at_one_over_a_two_rule_session() {
    let mut session =
        TickSession::new(SCENARIO, &rule_src(), HypergraphStore::new()).expect("load");
    assert_eq!(session.tick(), 0);
    let mut sink = CollectingSink::default();
    let r1 = session.advance(&mut sink).expect("tick 1");
    assert_eq!(session.tick(), 1);
    assert_eq!(r1.per_rule_fired.len(), 2);
    session.advance(&mut sink).expect("tick 2");
    assert_eq!(session.tick(), 2);
}

#[test]
fn advance_moves_state_and_each_tick_hashes_differently() {
    let mut session =
        TickSession::new(SCENARIO, &rule_src(), HypergraphStore::new()).expect("load");
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
    let mut a = TickSession::new(SCENARIO, &rule_src(), HypergraphStore::new()).expect("load a");
    let mut b = TickSession::new(SCENARIO, &rule_src(), HypergraphStore::new()).expect("load b");
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
//! `TickSession` — the persistent load-once, advance-many seam B2 needs,
//! now multi-rule (Phase A, Tasks 2-4). `run_once`/`run_once_into`
//! (`lib.rs`) model one tick end to end and hardcode `run_tick`'s tick
//! argument to `1` for every rule the content set holds; a player-driven
//! loop needs the split this type provides instead: parse and load cost
//! paid ONCE in `new`, the SAME `PreparedRules` and the SAME graph reused
//! by every `advance()` call, every rule in the content set run once per
//! call, in declaration order, with `tick` incremented by this type.

use crate::{prepare_rules, PreparedRules, TickReport};
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
    prepared: PreparedRules,
    tick: i64,
}

impl<G: GraphSubstrate + CanonicalState> TickSession<G> {
    /// Parse `rule_src` (one or more `(rule …)` forms, in declaration
    /// order) and load `scenario_src` into `graph` once.
    ///
    /// # Errors
    /// The same failure modes `run_once_into`'s load half has: an
    /// intrinsic declaration, a scenario load, or a rule load — named to
    /// its own rule id when more than one rule is present.
    pub fn new(scenario_src: &str, rule_src: &str, mut graph: G) -> Result<Self, String> {
        let prepared = prepare_rules(scenario_src, rule_src, &mut graph)?;
        Ok(Self {
            graph,
            prepared,
            tick: 0,
        })
    }

    /// Run one more tick against the held graph: every rule in the
    /// content set, in DECLARATION order, each to completion before the
    /// next starts, against the SAME graph — so a later rule sees an
    /// earlier rule's writes from this same tick (the frozen engine's own
    /// in-place strict-order semantics, inherited for free from calling
    /// `run_tick` sequentially against one `&mut G`). The first call runs
    /// tick 1 (matching `run_once`'s own numbering), the second tick 2,
    /// and so on.
    ///
    /// # Errors
    /// The tick itself (named to its own rule id), or a pre/post
    /// state-hash failure.
    pub fn advance(&mut self, sink: &mut CollectingSink) -> Result<TickReport, String> {
        self.tick += 1;
        let before = self
            .graph
            .state_hash()
            .map_err(|e| format!("pre-tick state: {}", e.message))?;
        let mut per_rule_fired = Vec::with_capacity(self.prepared.rules.len());
        for (id, loaded) in &self.prepared.rules {
            let outcome = run_tick(
                loaded,
                &self.prepared.types,
                &KernelIntrinsicHost,
                &mut self.graph,
                sink,
                &self.prepared.intrinsics,
                &self.prepared.consts,
                self.tick,
            )
            .map_err(|e| format!("tick failed in rule {id}: {e}"))?;
            per_rule_fired.push((id.clone(), outcome.fired));
        }
        let fired = per_rule_fired.iter().map(|(_, n)| n).sum();
        let after = self
            .graph
            .state_hash()
            .map_err(|e| format!("post-tick state: {}", e.message))?;
        Ok(TickReport {
            before,
            after,
            fired,
            per_rule_fired,
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

      `lib.rs` needs `PreparedRules`/`prepare_rules` visible to `session.rs` (same crate,
      `pub(crate)` already covers this) plus `pub mod session;` and, for the client's convenience,
      `pub use session::TickSession;` alongside the existing `pub use` of `TickReport`.
- [ ] **Step 4:** `cargo test -p babylon-tick` → PASS (all three tests above, plus Task 4's
      regression tests and Task 5's conformance tests still green). `mise run rust:check` → green.
- [ ] **Step 5: Commit** (`feat(rust): TickSession — persistent load-once/advance-many multi-rule
      tick loop seam (B2)`).

---

## Phase B — The demo content

### Task 7: The eighteen-subject demo world — twelve real-FIPS counties, six social classes

**Files:**

- Create (temporary aid, deleted at Step 4): `rust/crates/babylon-client/tests/print_demo_counties.rs`
- Create: `rust/crates/babylon-tick/content/scenarios/us-counties-lifecycle-demo.bscn`

**The point of this task:** `lifecycle-conformance.bscn`'s four territory nodes
(`core-county`/`growing-county`/`recovering-county`/`young-county`) carry proven-correct fixture
values but carry synthetic local names with no FIPS code, so `CountyAtlas::index_of_fips` cannot
place them on the B1 map. `vitality-conformance.bscn`'s six social-class nodes have no territorial
binding at all — by construction (Multi-Rule Decision section), vitality's contribution to this
demo is INVISIBLE on the map surface itself; it shows up only in the event feed
(`ENTITY_DEATH`-family events) and, if a future task adds a class-scoped panel, in state readouts —
stated here plainly rather than implied, since "richer demo" should not quietly promise a
map-visible effect vitality's own subject type cannot honestly produce. This task re-stamps the
lifecycle archetype value sets onto twelve REAL FIPS codes AND mints the vitality fixture verbatim
alongside them, in ONE scenario, without inventing new numbers this plan's author cannot verify.

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
- [ ] **Step 2: Write the scenario.** ONE `.bscn` file, two node-type halves:
      - **Territory half.** Reuse the `lifecycle-conformance.bscn` header's `deffield` block and
        all 21 `defconst` rows byte-for-byte. Cycle the four archetype value sets from
        `lifecycle-conformance.bscn:80-124` across the twelve FIPS in order (indices 0-2 get the
        `core-county` values, 3-5 `growing-county`, 6-8 `recovering-county`, 9-11 `young-county`),
        naming each node `county-<fips>` (symbols must start with a lowercase letter — §1's
        `symbol ::= LOWER (LOWER | DIGIT | "-")*` — a bare FIPS like `06037` is not a legal symbol,
        `county-06037` is).
      - **Social-class half.** Reuse `vitality-conformance.bscn`'s `deffield` block (7 fields,
        `social-class/inequality` included though no rule reads it, for fixture parity with the
        frozen engine per that file's own comment) and its 2 `defconst` rows, and its six nodes'
        values, byte-for-byte, keeping the SAME local names (`core`, `bourgeoisie`, `hermit`,
        `last-worker`, `remnant`, `dissolved` — the Multi-Rule Decision section's collision check
        already confirms these never collide with `county-<fips>`).

```text
(scenario lifecycle/us-counties-demo
  ; --- territory half (lifecycle) ---
  (deffield territory/pop-d int extensive)
  (deffield territory/pop-p int extensive)
  (deffield territory/pop-d-prime int extensive)
  (deffield territory/wealth-d-prime int extensive)
  (deffield territory/dependency-ratio int intensive)
  (deffield territory/legitimation-index int intensive)
  (deffield territory/legitimation-crisis int intensive)
  (deffield territory/transmitted-ideology int intensive)

  ; --- social-class half (vitality) ---
  (deffield social-class/active int extensive)
  (deffield social-class/population int extensive)
  (deffield social-class/wealth int extensive)
  (deffield social-class/subsistence-multiplier int intensive)
  (deffield social-class/s-bio int intensive)
  (deffield social-class/s-class int intensive)
  (deffield social-class/inequality int intensive)

  ; ... all 21 lifecycle/* defconst rows, transcribed verbatim from
  ; lifecycle-conformance.bscn:56-76, same values, same :NNN citations ...
  ; ... both economy/* defconst rows, transcribed verbatim from
  ; vitality-conformance.bscn:43-44 ...

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

  ; The six vitality-conformance.bscn nodes, values transcribed verbatim
  ; (fed core, standard-of-living-scaled bourgeoisie, surviving hermit,
  ; starving last-worker, zombie-failsafe remnant, already-dissolved).
  (node core NodeType/SOCIAL_CLASS
    (social-class/active 1) (social-class/population 100) (social-class/wealth 1000)
    (social-class/subsistence-multiplier 1) (social-class/s-bio 1) (social-class/s-class 1)
    (social-class/inequality 0))
  ; ... bourgeoisie, hermit, last-worker, remnant, dissolved, same values ...
  )
```

      Write out all eighteen `(node …)` forms in full — no ellipsis in the committed file, the
      ellipses above are this plan document's abbreviation only.
- [ ] **Step 3: A loading test.**

```rust
// rust/crates/babylon-tick/tests/us_counties_demo.rs (new file)
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_tick::TickSession;

const SCENARIO: &str = include_str!("../content/scenarios/us-counties-lifecycle-demo.bscn");
const VITALITY: &str = include_str!("../content/rules/vitality.bsl");
const LIFECYCLE: &str = include_str!("../content/rules/lifecycle.bsl");

#[test]
fn the_demo_scenario_loads_and_ticks_both_packs() {
    let rule_src = format!("{VITALITY}\n{LIFECYCLE}");
    let mut session =
        TickSession::new(SCENARIO, &rule_src, HypergraphStore::new()).expect("load");
    let mut sink = CollectingSink::default();
    let report = session.advance(&mut sink).expect("tick 1");
    assert_ne!(report.before, report.after);
    assert_eq!(report.per_rule_fired.len(), 2);
    assert_eq!(report.per_rule_fired[0].0, "vitality/subsistence-and-death");
    assert_eq!(report.per_rule_fired[1].0, "lifecycle/dpd-circuit");
    // The recovering-county archetype fires LEGITIMATION_RECOVERY on tick 1
    // under these defconsts (matching lifecycle-conformance.bscn's own
    // documented behavior) — proves the twelve territory nodes really run
    // lifecycle, not just mint successfully.
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
- [ ] **Step 5: Commit** (`feat(content): the eighteen-subject B2 demo world — twelve real-FIPS
      counties + six social classes`), body carrying the Step 1 FIPS/name table.

---

## Phase C — The dual-lens map (completes B1 Phase C)

### Task 8: The Tension lens, ported and corrected for `HypergraphStore`

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
      `graph.node_attribute(id, "...")` through `&dyn GraphSubstrate` rather than a concrete store
      — note this graph, from Task 7 on, ALSO holds six `NodeType/SOCIAL_CLASS` nodes; `nodes()`'s
      own type filter (verified in `memory.rs`/`hypergraph_store.rs`) already excludes them, so
      this task's logic needs no change — confirmed by reading, recorded here rather than assumed.
- [ ] **Step 3:** `cargo test -p babylon-client` → PASS.
- [ ] **Step 4: Commit** (`feat(client): the ADR170 tension witness over &dyn GraphSubstrate (B2)`).

### Task 9: The Legitimation lens — live, categorical, zero new math

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
a threshold on the raw `territory/legitimation-index`, adds no new cut point and no new math — this
is a straight categorical pass-through, consistent with the standing "no imposed functional forms"
ruling. **This module produces the raw classification number only** — Task 10's `bands.rs` owns
the color mapping (Director ruling 1), matching the Tension lens's own separation of "compute the
value" from "pick the color."

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
      `Some(raw_class_as_f64)` per cell.
- [ ] **Step 3:** `cargo test -p babylon-client` → PASS.
- [ ] **Step 4: Commit** (`feat(client): the legitimation lens — live per-tick classification, zero
      new thresholds (B2)`).

### Task 10: Two band tables, one recolor system

**Files:**

- Edit: `rust/crates/babylon-client/src/map/bands.rs`

**Interfaces:**

- Produces: `pub fn tension_band_color(w: Option<f64>) -> Color` (ADR191 R11's table, exactly as
  the B1 plan's Task 9 specified — four rows, `<=` resolution, `PANEL` for absence) and `pub fn
  legitimation_band_color(class: Option<f64>) -> Color` (per this amendment's Director ruling 1:
  three rows, `Some(0.0) => PANEL`, `Some(1.0) => DIM`, `Some(2.0) => CRIMSON`, `None => PANEL`)
  plus `pub enum ActiveLens { Tension, Legitimation }` and `#[derive(Event)] pub struct
  LensChanged;`.

**Director ruling 1, applied exactly.** Selected option, quoted: *"CRISIS → crimson, UNSTABLE →
dim gray, STABLE → gold's absence (panel dark) — reuses the ruled four-band vocabulary so the two
lenses share one visual language. No new colors enter the game."* This REPLACES the first cut's
design (which had invented `GREEN_DARK`/`GOLD` mappings for STABLE/UNSTABLE — neither ships).
**STABLE and "no data this tick" render the SAME color, `PANEL`, on purpose** — a deliberate
INVERSION of the Tension lens's own rule (ADR191 R11, carried unmodified in `tension_band_color`):
"nothing may confuse absence with the neutral band" there means Tension's neutral band is `DIM`,
distinct from `PANEL`. Here, the Director's own ruling makes STABLE deliberately indistinguishable
from absence BY COLOR — "gold's absence" reads as "nothing here needs your attention," which is
thematically apt for a stable county fading into the background. The HUD (Task 11) is, as a
result, the ONLY channel that can tell a player "this county is STABLE" from "this county has no data" —
its literal text label carries weight the color alone cannot, and Task 11's steps make that
explicit.

- [ ] **Step 1: Write the failing tests** for both band functions — the exact `Srgba` byte
      assertions from the B1 Task 9 spec for `tension_band_color` (CRIMSON at `w <= -0.15`, DIM in
      `(-0.15, 0.15]`, GOLD above, PANEL for `None`; `tension_band_color(Some(0.0)) !=
      tension_band_color(None)`, the Tension lens's OWN non-confusion property, unchanged) plus,
      for `legitimation_band_color`: `Some(0.0)` and `None` BOTH give `PANEL` (the intentional
      equality Director ruling 1 creates — assert them EQUAL, not distinct, and comment why,
      citing this ruling by name so a future reader does not "fix" it back to the first cut's
      design); `Some(1.0)` gives `DIM`; `Some(2.0)` gives `CRIMSON`.
- [ ] **Step 2:** FAIL, then write both as `const` tables resolved by the same `<=`-walk shape,
      matching `PANEL`'s existing declaration in this file. `legitimation_band_color` needs no new
      color constant — it imports `PANEL`, `DIM`, `CRIMSON`, all already declared in this file or
      `crate::palette`.
- [ ] **Step 3: The recolor system.** One system, parameterized by `ActiveLens`:

```rust
pub(super) fn recolor_on_lens_changed(
    mut events: EventReader<LensChanged>,
    active: Res<ActiveLens>,
    lens_data: Res<CurrentLensData>, // holds both LensReading values, refreshed every advance
    surface: Res<MapSurface>,
    atlas_index: Res<FipsIndex>,     // fips -> atlas county index, from Task 12
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
      instead of fixed to Tension alone.
- [ ] **Step 4: Headless test** — `MinimalPlugins` + `AssetPlugin`, install a `CurrentLensData`
      with one known Legitimation cell, set `ActiveLens::Legitimation`, fire `LensChanged`, `update()`,
      assert that county's vertex range shows `legitimation_band_color`'s output and every other
      county's colors held at `PANEL`. Add a SPECIFIC regression case: a `Some(0.0)` (STABLE) cell
      and a genuinely-absent cell (a FIPS with no `LensReading` entry at all) produce the SAME
      vertex color — proving the intentional merge, not just the function's return value in
      isolation.
- [ ] **Step 5: Commit** (`feat(client): two-lens band tables — legitimation reuses PANEL/DIM/
      CRIMSON per Director ruling 1 (B2, completes B1 Phase C Task 9)`).

### Task 11: Hover, selection, the active-lens label

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
      rule adds — and, under the Legitimation lens specifically, carrying MORE weight than usual
      per Task 10's finding that STABLE and absence share a color:

```text
<county name>, <state> (<FIPS>)
Lens: Tension — w = -0.42 (Φ-source, bled)          [if ActiveLens::Tension]
Lens: Legitimation — CRISIS (live, tick 7)          [if ActiveLens::Legitimation, class 2]
Lens: Legitimation — STABLE (live, tick 7)          [class 0 — SAME map color as absence;
                                                       this line is the only place a player
                                                       can tell the two apart]
Lens: Tension — no data this tick                    [absence, either lens]
```

      Top-left banner whenever the active lens's `absent_reason.is_some()`, in CRIMSON. A
      persistent DIM footer names which lens is inactive and how to switch (Task 12): "Tab: switch
      to Legitimation lens" or vice versa — the map must never let a color mean two things without
      saying which one is live, and (per Task 10) a STABLE county must never let its color alone
      be mistaken for "no data."
- [ ] **Step 5: Headless test** — hovering a known world point sets `HoveredCounty` to the expected
      FIPS, cursor position written directly to the resource (B1 Task 10's own precedent, not
      synthesized window events). Add a case hovering a STABLE demo county and asserting the HUD
      text renders the literal string `"STABLE"` (not merely a color check, since Task 10
      established the color cannot carry this distinction alone).
- [ ] **Step 6: Commit** (`feat(client): county hover, selection and the active-lens HUD (B2,
      completes B1 Phase C Task 10)`).

### Task 12: Wire `map/mod.rs` — the lens picker

**Files:**

- Edit: `rust/crates/babylon-client/src/map/mod.rs`

- [ ] **Step 1: Write the failing headless test** — `MinimalPlugins` + `AssetPlugin` +
      `babylon_client::map::MapPlugin`, press `Tab` (write directly into `ButtonInput<KeyCode>`,
      matching the input-resource-mutation pattern this plan's tests already use), `update()`,
      assert `ActiveLens` flipped and a `LensChanged` event fired.
- [ ] **Step 2:** FAIL, then add: `mod pick; mod hud;` (new modules from this task); `pub use
      bands::{ActiveLens, LensChanged};` alongside the existing `pub use bands::PANEL;` — the same
      re-export convention B1 already established for `PANEL`, extended to the two new types so
      `crate::map::ActiveLens`/`crate::map::LensChanged` (the paths Task 14's and Task 18's code
      use) resolve; `ActiveLens::Tension` inserted as the `Startup` default resource; an `Update`
      system reading `Tab` and toggling it plus sending `LensChanged`; Task 10's
      `recolor_on_lens_changed` system registered.
- [ ] **Step 3:** `cargo test -p babylon-client` → PASS. `mise run rust:check` → green.
- [ ] **Step 4: Commit** (`feat(client): wire the lens picker into MapPlugin (B2)`). Open the
      Phase C PR (`feat(client): B2 Phase C — the dual-lens map, completing B1's Phase C`);
      self-merge on green.

---

## Phase D — The loop UI

### Task 13: `EngineSession` — the client's held tick session

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
name -> `NodeId` map is deliberately load-time-only and does not outlive the call (`scenario.rs`'s
own comment). This plan does not widen that API. Instead: the Phase B scenario mints EXACTLY the
twelve `NodeType/TERRITORY` nodes and six `NodeType/SOCIAL_CLASS` nodes, in file order, and no
others; `GraphSubstrate::nodes("NodeType/TERRITORY")` filters BY TYPE and returns ascending
`NodeId`s among territory nodes only, which equal territory-mint order because `NodeId` mints as a
GLOBAL monotonic counter across the whole scenario (ADR193) and the type filter preserves relative
order within the filtered subset — verified by reading both `nodes()` implementations
(`memory.rs`/`hypergraph_store.rs`), not assumed: interleaving social-class and territory node
declarations in the `.bscn` file changes the ABSOLUTE `NodeId` values but not their RELATIVE order
among same-typed nodes, so this zip is correct regardless of how the two halves interleave in the
file. Zipping `graph.nodes("NodeType/TERRITORY")` against a `const DEMO_FIPS: [&str; 12]` array
**in the same order as the `.bscn` file's twelve territory `(node …)` forms** recovers the
fips↔id mapping with no new babylon-bsl surface — fragile only in the sense that editing the
`.bscn` file's territory node order without updating `DEMO_FIPS` would silently mislabel a county,
which Step 2's loud startup assertion turns into an immediate panic instead. **Social-class nodes
get no matching index** — the event feed (Task 15) reads `sink.events` generically and needs no
per-class lookup; a class-scoped state panel sits outside this task's scope (noted, not built).

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
fn engine_session_advance_moves_the_hash_and_runs_both_rules_every_tick() {
    let mut session = EngineSession::start().expect("start");
    let r1 = session.advance().expect("tick 1");
    let r2 = session.advance().expect("tick 2");
    assert_eq!(session.inner.tick(), 2);
    assert_ne!(r1.after, r2.after);
    assert_eq!(r1.per_rule_fired.len(), 2, "both packs run every tick");
}
```

- [ ] **Step 2:** FAIL, then write it:

```rust
const SCENARIO: &str =
    include_str!("../../babylon-tick/content/scenarios/us-counties-lifecycle-demo.bscn");
const VITALITY: &str = include_str!("../../babylon-tick/content/rules/vitality.bsl");
const LIFECYCLE: &str = include_str!("../../babylon-tick/content/rules/lifecycle.bsl");

/// Same order as `us-counties-lifecycle-demo.bscn`'s twelve territory
/// `(node …)` forms — Task 7's Step 1 print output, transcribed. A loud
/// startup assertion (below) catches the two arrays ever drifting apart.
const DEMO_FIPS: [&str; 12] = [ /* the twelve FIPS from Task 7 Step 1, in file order */ ];

pub struct EngineSession {
    pub inner: TickSession<HypergraphStore>,
    pub sink: CollectingSink,
    pub node_by_fips: Vec<(String, NodeId)>,
}

impl EngineSession {
    pub fn start() -> Result<Self, String> {
        let mut graph = HypergraphStore::new();
        // Load through the same load path TickSession uses internally —
        // but we need the territory node ids BEFORE TickSession takes
        // ownership of the graph, so load once here to capture them, then
        // hand a FRESH graph to TickSession::new (it reloads the same
        // scenario, which is deterministic and mints the identical
        // eighteen ids — proven by this task's own Step 1 test, which
        // checks both independently).
        babylon_bsl::scenario::load_scenario(SCENARIO, &mut graph).map_err(|e| e.to_string())?;
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

        // vitality text FIRST, lifecycle text SECOND — Vitality @1 before
        // Lifecycle @7, per the Multi-Rule Decision section's declaration-
        // order design (Phase A, Tasks 2-6).
        let rule_src = format!("{VITALITY}\n{LIFECYCLE}");
        let inner = TickSession::new(SCENARIO, &rule_src, HypergraphStore::new())
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

      Note the deliberate double-load (once to recover territory ids, once inside
      `TickSession::new`) rather than widening `TickSession` to expose its internal graph mutably
      before the first `advance` — it costs one extra scenario parse at startup (still
      microseconds against an 18-node scenario) and keeps `TickSession`'s public surface exactly
      the four methods Task 6 specified.
- [ ] **Step 3:** `cargo test -p babylon-client` → PASS.
- [ ] **Step 4: Commit** (`feat(client): EngineSession — the client's held two-rule TickSession +
      fips↔id map (B2)`).

### Task 14: Advance-tick input, tick counter, hash readout

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
        // the Global Constraints Scale Note — 18 nodes, 0 hyperedges).
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

### Task 15: The state panel and the event feed

**Files:**

- Edit: `rust/crates/babylon-client/src/loop_ui.rs`

- [ ] **Step 1: Write the failing headless test** — after two `advance()` calls with a county
      selected (write `SelectedCounty` directly, matching Task 11's pick-testing precedent), the
      state panel's text contains that county's live `pop-d`/`pop-p`/`pop-d-prime`/
      `legitimation-index` values read straight off the graph (not off the lens, which only carries
      the classification) — proving the panel and the map agree because both read the same graph.
- [ ] **Step 2:** FAIL, then write `spawn_state_panel`/`refresh_state_panel`. `SelectedCounty`
      (Task 11) wraps an ATLAS INDEX (`usize`), not a `NodeId` — the map's own vocabulary, matching
      `county_at`'s return type. Resolve the chain explicitly: atlas index -> `atlas.county(idx).fips`
      -> a linear scan of `session.node_by_fips` (twelve entries — a `HashMap` is not worth building
      for this size) for the matching FIPS -> its `NodeId`. A `SelectedCounty`/`HoveredCounty` whose
      atlas index resolves to a FIPS absent from `node_by_fips` (any of the 3,210 non-demo counties)
      renders the panel's honest "no data this tick" text, never a lookup panic — this is the same
      honest-absence shape Task 8's `LensReading` already establishes, applied here to the panel
      instead of the map. For a resolved `id`, read the four fields via
      `session.inner.graph().node_attribute(id, "...")` and render:

```text
<county name> (<fips>)
  pop-d:            2,150
  pop-p:            6,050
  pop-d-prime:      1,800
  legitimation:     STABLE (0)
```

- [ ] **Step 3: The event feed — now genuinely two-pack.** A scrolling text list, last 10 entries
      from `session.sink.events`, newest first, rendered as `<EventType> @ <county or n/a>` —
      reusing `CollectingSink`'s already-populated `events: Vec<(String, Vec<(String, Value)>)>`
      with no new sink type. Because `EngineSession` (Task 13) now runs vitality THEN lifecycle
      every tick, `sink.events` genuinely mixes BOTH packs' emissions in execution order:
      `vitality`'s `EventType/ENTITY_DEATH` (its own payload carries `entity-id`, no county
      binding — rendered as `@ n/a`) alongside `lifecycle`'s
      `LIFECYCLE_TRANSITION`/`LEGITIMATION_CRISIS`/`LEGITIMATION_RECOVERY` (county-bound, rendered
      with the county's name where the payload's `entity-id` resolves through `node_by_fips`) —
      this IS the "richer first demo" the Director's ruling asked for, concretely: the feed is
      where the vitality half of the demo becomes visible at all, since Task 7 already established
      it has no map-color counterpart. Bounded to the last 10 by slicing, not by mutating
      `sink.events` (the sink accumulates the WHOLE session's history — acceptable at demo scale, a
      ring buffer is a documented future item if unbounded play sessions become a target, not built
      here).
- [ ] **Step 4: Headless test** for the event feed — after an `advance()` that fires
      `LEGITIMATION_RECOVERY` (Task 7's own recovering-county archetype guarantees this on tick 1),
      assert the feed's rendered text contains `"LEGITIMATION_RECOVERY"`. Add a second assertion
      proving the two-pack mix specifically: over enough ticks for the fixture's `last-worker`
      subject to starve (its own conformance fixture already proves this fires within a handful of
      ticks — `vitality-conformance.bscn`'s own comment names it "Starvation"), the feed also
      contains `"ENTITY_DEATH"` — both event families visible in one feed, not merely present in
      the sink.
- [ ] **Step 5:** `cargo test -p babylon-client` → PASS. Eyes-on: select a county, press Space,
      watch its panel numbers and the event feed both update, and confirm `ENTITY_DEATH` events
      appear alongside the lifecycle events over a longer run.
- [ ] **Step 6: Commit** (`feat(client): the state panel and event feed — now two packs deep (B2)`).
      Open the Phase D PR (`feat(client): B2 Phase D — the tick loop UI`); self-merge on green.

---

## Phase E — Logging, determinism, the eyes-on gate

### Task 16: Resurrect the client file-log sink

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

### Task 17: End-to-end determinism guard

**Files:**

- Create: `rust/crates/babylon-client/tests/determinism.rs`

**Why this test exists separately from Task 6's `babylon-tick`-level version.** Task 6's test
proves `TickSession` itself is deterministic across a multi-rule content set. This test proves the
SAME property through the client's own composed seam — `EngineSession::start` + repeated
`advance()` — which is the actual path a player's key presses drive, and the one the plan's own
instructions ask to see "as a committed test."

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
        assert_eq!(
            ra.per_rule_fired, rb.per_rule_fired,
            "tick {tick}: per-rule detail must also match — the order proof, not just the hash"
        );
    }
}

#[test]
fn five_ticks_produce_five_distinct_hashes() {
    // Regression guard against a driver that silently re-runs tick 1 —
    // exactly the bug TickSession's own tick-numbering exists to prevent;
    // this test watches for it at the client's seam too.
    let mut session = EngineSession::start().expect("session");
    let mut hashes = std::collections::HashSet::new();
    for _ in 0..5 {
        let report = session.advance().expect("advance");
        hashes.insert(report.after);
    }
    assert_eq!(hashes.len(), 5, "each tick must produce a distinct state hash");
}
```

- [ ] **Step 2:** FAIL until Task 13's `EngineSession` exists (this task can run any time after
      Task 13 — placed last only to sit beside Task 16's logging work in one PR).
- [ ] **Step 3:** `cargo test -p babylon-client --test determinism` → PASS.
- [ ] **Step 4: Commit** (`test(client): end-to-end determinism guard — same content, same tick
      count, same hash and same per-rule order (B2)`).

### Task 18: The eyes-on gate

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
   - the hash readout changes to a new hex string every press (never repeats — Task 17 proves this
     is a real property, not a hope);
   - at least one demo county's band color OR the selected/hovered county's state-panel numbers
     visibly changes (a tick where no county crosses a band boundary still moves the raw
     `pop-d`/`pop-p`/`pop-d-prime` numbers in the panel — "watch state change" needs no
     color flip on every single press);
   - the event feed grows, carrying BOTH event families over a long-enough run —
     `LIFECYCLE_TRANSITION` fires every tick for every county, and `ENTITY_DEATH` fires at least
     once by the tick the fixture's `last-worker` subject starves (Task 15's own conformance
     citation).
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
fn five_space_presses_advance_five_distinct_ticks_and_fire_both_packs_events() {
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
        "the event feed must carry lifecycle's own emitted events"
    );
    assert!(
        session
            .sink
            .events
            .iter()
            .any(|(name, _)| name == "EventType/ENTITY_DEATH"),
        "the event feed must carry vitality's own emitted events too — \
         proving both packs actually ran, not just lifecycle"
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
- [ ] **Step 3:** Update `ai/state.yaml` — B2 reached: multi-rule tick loop (vitality + lifecycle),
      dual-lens map, state panel, event feed, log sink, eyes-on gate defined and CI-proxied. Close
      #262 as "superseded — replaced by this gate" per the roadmap spec §5's own instruction,
      citing this plan document.
- [ ] **Step 4: Commit** (`test(client): the B2 eyes-on gate + its CI-safe proxy (B2)`).

### Task 19: Gates, docs, PR

- [ ] **Step 1:** `mise run rust:check` → green. `mise run check` → green.
- [ ] **Step 2:** `mise run qa:regression` and `mise run qa:vault-regression-ci` → byte-identical.
      Phase A's Task 1 refactor and Task 4 widening are the only touches to `babylon-bsl`'s and
      `babylon-tick`'s existing behavior, and each task's own regression test already proved it
      moves nothing for existing single-rule content — this is the whole-repo confirmation.
- [ ] **Step 3:** Run `cargo test -p babylon-bsl -p babylon-tick -p babylon-client` once more, full
      suite, to confirm every test across all five phases is green together, not just
      phase-by-phase.
- [ ] **Step 4:** Update `ai/state.yaml`'s Program 28 entry (B2 milestone reached — cite this plan
      document and the PR numbers) and the GitHub project board's client lane. Open the follow-up
      issue this plan's own sections defer (the Phase 3 anchor-resolution registry the Multi-Rule
      Decision section names explicitly; unbounded event-feed memory; the economics BSL port that
      would make the Tension lens tick-live too) — record it in the PR body per the B1 Task 12
      precedent, don't silently drop it.
- [ ] **Step 5:** Open the PR (`feat(client): B2 — the tick loop on screen, two packs deep`), body
      carrying: the eyes-on human-pass screenshot/description, the Task 7 Step 1 FIPS table, the
      pinned multi-rule conformance output (Task 5), the pinned determinism-guard output, and a
      link back to this plan document. Self-merge on green per the standing autonomy rulings.

---

## Open questions for the Director

**All three ruled, 2026-08-11, interactive batch — full record.** This document's Amendment
record (top of file) quotes the rulings verbatim and applies them throughout the task list above; this
section keeps each original question's full reasoning intact per the Documentation philosophy's
immutability-of-history discipline, and appends what the ruling actually changed.

1. **Does the new Legitimation lens need its own sign-off, the way ADR191 R11 ruled the Tension
   lens's four bands? — RULED: APPROVED, reuse the band palette.** This plan's original reasoning
   for proceeding without escalating: the Legitimation lens invents no new formula (it colors a
   categorical field the `lifecycle` rule pack already computes), uses only already-declared §9b
   palette tokens, and is additive to — never a replacement for — the Director-ruled Tension lens
   (a Tab key switches between them, both visible, neither hidden). The Director ruled rather than
   letting the recommendation stand by default, selecting: *"CRISIS → crimson, UNSTABLE → dim
   gray, STABLE → gold's absence (panel dark) — reuses the ruled four-band vocabulary so the two
   lenses share one visual language. No new colors enter the game."* Task 10 carries this exactly —
   `legitimation_band_color` maps `{0.0: PANEL, 1.0: DIM, 2.0: CRIMSON}`, replacing this plan's
   first-cut `GREEN_DARK`/`GOLD` invention outright. Task 11 carries the consequence: STABLE and
   "no data" now share a map color on purpose, so the HUD's literal text is the only channel that
   distinguishes them.
2. **Should B2 defer multi-rule-pack sessions, or does "watch state change" implicitly want BOTH
   Material Base systems visible at once? — RULED: MULTI-RULE DRIVER FIRST, this plan's
   recommendation OVERRULED.** This plan's original recommendation was to defer, run `lifecycle`
   alone, and file an issue — reasoning: `lifecycle` alone, of the three merged packs, has a
   subject type matching the map's own unit, so it demonstrates the criterion fully on its own; the
   technical wall (`E-LOAD-001`, `split_content`'s "exactly one rule" cardinality check) is real
   engineering work, not a flag flip. The Director selected the larger option instead, quoted:
   *"Build the multi-rule content-set evolution into B2 itself so the demo runs vitality+lifecycle
   together from day one. Bigger B2, later criterion-3 close, but a richer first demo."* This
   ruling is what reshapes the entire plan above: Phase A gained four tasks (2–5) widening
   `split_content`, `prepare_rules`, `TickReport`, and proving a conformance vector against the
   frozen engine's own vitality-then-lifecycle tick order; Phase B's demo scenario grew from
   twelve territory nodes to eighteen (twelve territory + six social-class); Phase D's event feed
   and Phase E's eyes-on gate both now assert on BOTH packs' events, not just the lifecycle rule
   pack's. The Multi-Rule Decision section (above the File Structure table) is the full design this
   ruling required, including the finding — checked, not assumed — that vitality's own subject type
   has no territorial binding, so the "richer demo" ruling 2 asked for is genuinely richer in the
   event feed and the state panel, not on the map surface itself, which only the lifecycle rule
   pack paints.
3. **Audio (SFX/soundtrack, ADR152/153) — RULED: DEFERRED out of B2, per this plan's own
   recommendation.** No change from the first cut: R3's visual scope names "2D map game + panels
   and charts as the primary surface" with no audio obligation; wiring 39 SFX + 13 tracks properly
   is real, separately-scoped work, and B2 already carries five phases (now nineteen tasks) of new
   surface.
