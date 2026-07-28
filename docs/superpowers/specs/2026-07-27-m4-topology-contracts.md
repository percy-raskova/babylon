# M4 — Topology + the 3D lane: seam contracts

**Status:** PINNED before any Task 30–36 code (the M1–M3 contract-pin-first
discipline). Sources: the six-scout recon sweep `wf_dd434169-695`
(2026-07-27; every claim below carries a scout-verified file:line
provenance in that run's journal), the plan
(`docs/superpowers/plans/2026-07-26-ratatui-client.md` Tasks 30–36), ADR150
BD-3/BD-4, ADR097 D4, ADR099.

This document RULES the design forks the recon surfaced. Deviations found
during implementation get recorded here in §9, the M1–M3 convention.

---

## 1. `topology_json(args_json)` — call1 (host), Task 30

Python: `RustClientHost.topology_json(self, args_json: str) -> str`.
`args_json` = `{"kind": "...", "focus": str | null}` (field order pinned).
No session bound → the string `null` (house read-path convention).

**Kind vocabulary (RULED):** `"paoh" | "egotree" | "incidence" |
"adjacency"` — four kinds, one envelope each.
- `egotree`, NOT `levi`: the codebase already declared the
  `TopologyKind` Literal (`shell/views/topology_view.py:17`); we do not
  invent a second name for the same concept.
- `incidence` and `adjacency` are SEPARATE kinds, not a combined
  envelope: `incidence.py` produces two mutually-incompatible frozen
  models and Textual renders them with two distinct renderers; one kind
  per renderer keeps the Rust dispatch 1:1.

**Per-kind envelopes (hand-built dicts — there is deliberately no shared
discriminated union; `LeviEgoTree` documents it is not a
`ProjectionRecord` member):**

```json
{"kind": "paoh",
 "verified_tick": 500,
 "nodes": ["C001", "C002"],
 "edges": [{"community_id": "union_local", "formation_tick": null,
            "members": ["C001", "C002"]}],
 "layout": {"C001": [0.0, 1.0], "C002": [0.9510, 0.3090]}}
```
```json
{"kind": "egotree", "verified_tick": 500,
 "root_id": "C001", "root_side": "member",
 "children": [{"node_id": "union_local", "neighbors": ["C002"]}]}
```
```json
{"kind": "incidence", "verified_tick": 500,
 "nodes": ["C001"], "hyperedges": ["union_local"], "cells": [[true]]}
```
```json
{"kind": "adjacency", "verified_tick": 500,
 "nodes": ["C001", "C002"], "cells": [[false, true], [true, false]]}
```

- `members` serializes SORTED (frozenset → sorted list; determinism).
- `edges` keep `paoh_ordering`'s order (formation_tick asc, None last,
  community_id tiebreak). `nodes` keep its lexicographic order.
- **`focus` for `egotree` is REQUIRED (RULED):** `focus: null` or an
  unknown root for `kind="egotree"` returns the string `null` — honest
  absence, never a propagated `ValueError` (the recon's panic risk:
  a stale focus after a tick must not kill the client). The
  `levi_ego_tree` `ValueError` is caught at the `GameSession` seam and
  mapped to `None`. A recognized root with zero bipartite edges (the
  projection's own `None`) is the same `null`.
- `focus` is IGNORED for the other three kinds (documented, not an error).

**Aggregation (RULED):** `GameSession.topology_view` builds ONE
`WorldState.from_graph(self.graph, tick=self.tick)` and loops
`sorted(CommunityType)` (14 members) calling `project_community` once
each — extracted as a small shared helper (`_community_views`) rather
than duplicated inline, since `paoh`/`incidence`/`adjacency` all need it.
Fresh every call, no cache (the `subject_view` pattern).

**Layout (RULED — the recon's biggest fork):** the S9 canon stands: the
ordering modules stay ordering. Positions live in a NEW module
`src/babylon/projection/topology/layout.py` that maps an ordering to
**closed-form deterministic coordinates** — NO iterative spring layout
(float-iteration convergence is a determinism hazard for zero benefit at
these node counts):
- `paoh`/hypergraph 3D: **bipartite shell** — member nodes on an outer
  circle (unit radius, angle = index/len · 2π over the lexicographic
  order), community nodes on an inner circle (radius 0.45, same rule
  over the sorted community ids). Pure trigonometry over sorted inputs;
  byte-stable given the same payload.
- The `layout` map ships INSIDE the `paoh` envelope (node id → `[x, y]`,
  both node and community ids present). `egotree`/`incidence`/
  `adjacency` carry NO layout (their renderers are text-grid, not
  spatial).
- rustworkx layout functions stay unused for now — closed-form beats
  seeded-iterative on the determinism budget; revisit only if a future
  graph outgrows the shell (recorded as a non-goal here).

## 2. `field_state_json()` — call0 (host), Task 30

`GameSession.field_state_view()` calls
`project_field_state("USA", graph=self.graph, tick=self.tick)`
**directly on the live graph** — NEVER through `WorldState.from_graph`
(the round-trip drops the field-stack attrs; the projection module's own
docstring forbids it). Serializes `FieldStateView.model_dump_json()`;
no session → `null`. Distinct from the baked `field_state/USA.md` page
(same projection, different serialization target).

**The (x,y) join for Task 34 (RULED):** `FieldStateView` carries no
coordinates and is NOT extended (T3's dossier shape is frozen). The
surface builder joins by `node_id` against the same closed-form circle
used for member nodes in §1's layout (unit circle over the sorted
`nodes[].node_id` list — computed CLIENT-side in Rust from the
field-state payload itself, no second host call). The visualized scalar
defaults to `fields[principal_field.field_name]` per node; the client
cycles available field names as camera-adjacent view state (`f` key,
§6). `df_dt`/`laplacian` selection is the same cycle, prefixed
(`∂` / `Δ` in the HUD line).

## 3. Rust seams (Tasks 30/31/33/34 wiring)

- `Host` trait (`host.rs`): `topology_json(&self, args_json: &str) ->
  String` (default `"null"`), `field_state_json(&self) -> String`
  (default `"null"`). `RecordingHost` passthrough; PyO3 `call1`/`call0`
  arms in `babylon-tui-python`.
- New `views/topology.rs`: `TopologyView` is **chrome-owned** (like
  watchlist — pane switching is chrome-internal state, not a view-stack
  push), holding `kind`, `focus`, the parsed payload, and the camera.
- `app.rs` `Pane::Topology` match arm replaces
  `render_pane_absence(..., TOPOLOGY_FENCE)`; `refresh_after_tick`
  gains a topology branch (re-pull the current `(kind, focus)`) — the
  recon's stale-pane trap.
- `Pane::Map` stays a fence until M5 — Task 34's surface renders inside
  the TOPOLOGY pane (kind cycle includes the field surface: the `s` key
  toggles hypergraph ↔ surface; both are this pane's 3D lane).

## 4. 2D glyph floor (Task 31) — visual contracts

Byte-faithful ports of the three Textual renderers (glyph-for-glyph;
colors mapped through the parity-guarded tokens):
- PAOH (`directives.py:122-149`): header `tX` ticks; `●` bold GOLD
  member, `│` CRIMSON span-fill, `·` panel-muted absent; 4-char cells;
  10-char row labels BONE.
- Ego-tree (`topology/egotree.py:84-109`): root bold GOLD + `(side)`
  DIM; `├──`/`└──` CRIMSON depth-1; `│   ` panel-muted depth-2 with
  DIM ids. Depth hard-capped 2 (bipartite shape; Power-of-10 rule 2).
- Incidence/adjacency (`topology/matrix.py:57-121`): `●` bold GOLD, `·`
  panel-muted, `—` DIM diagonal (adjacency); empty → header +
  "no incidence data"/"no adjacency data" DIM.

**`$panel` color (RULED):** Python's `PANEL = #200404` is NOT a §9b
token. Per the AMBER precedent, it becomes a module-local
`const PANEL: Color = Color::Rgb(32, 4, 4);` in `views/topology.rs`
with a doc comment citing `babylon/tui/theme.py`'s hardcode — NEVER
added to `theme.rs` (the parity guard's regex owns that file).

**Golden strategy (RULED, from the harness scout):** structured 2D
renderers use explicit substring/field asserts over `buffer_text`
(the wiki_view convention); raw 3D frames use
`insta::assert_snapshot!("{buf:?}")` (the raster_skeleton convention),
fixture-named `<scene>_{front,3q}` matching hypergraph-rs's own
vocabulary. Insta cannot assert color — color pins ride the explicit-
assert lane. Fixture inputs: the `test_egotree_directive.py` /
`test_matrix_directive.py` fixture bodies, ported verbatim.

## 5. Raster pipeline (Tasks 32–34)

- `raster_bridge::blit` widens to `blit_rect(grid, buf, area: Rect)`
  (the current fn hardcodes `buf.area` origin); `blit` stays as the
  full-area convenience.
- Task 33 builder (in babylon-tui, NOT the dep):
  `hypergraph_scene(nodes: &[(id, [x,y], radius, Rgb)], hulls: &[(members, Rgb)], struts: &[(a, b)]) -> SceneGraph3D`
  — z from a fixed member/community plane split (members z=0, communities
  z=0.6), hulls fan-triangulated (the cylinder.rs pattern), positions
  from §1's layout. **BANNED:** `hypergraph_rs::raster::instruments::*`,
  `::deck::*`, `::ingest::*` — enforced by a Python-side sentinel test
  (grep over `rust/crates/babylon-tui/src/`, the check:vocabulary
  precedent), since Cargo features cannot gate them out.
- Task 34 builder: `field_surface(samples: &[(x, y, scalar)], grid: (u16,u16)) -> SceneGraph3D`
  reusing `idw_height`'s formula (reimplemented locally — EPS=0.02
  smoothing, tmax normalization; terrain.rs's `agent_tension` and
  DeckWorld driver are the coupling stripped). Heat color ramp over
  §9b: DIM → GREEN_DARK → GOLD → CRIMSON by normalized height.
- `SceneGraph3D.labeled_scalars()`/metadata banner reused unmodified.

**Feature gates (RULED — three verified holes closed in Task 32):**
1. `rust:check` gains `cargo clippy -p babylon-tui --all-targets
   --features raster --locked -- -D warnings` and `cargo test -p
   babylon-tui --features raster --locked` legs (today the whole lane
   compiles to zero code under the gate).
2. `babylon-tui-python` forwards the feature UNCONDITIONALLY
   (`babylon-tui = { path = "../babylon-tui", features = ["raster"] }`)
   — the 3D lane is release-blocking; the wheel always carries it.
3. Task 35 adds `"raster-png"` to the git-dep features when (and only
   when) the pixel tier lands (`render_pixels` lives behind it).

## 6. Camera (Task 32) — client state, deterministic

`Camera{ry, rx, dist, fov}` constructed fresh each frame from a
`CameraState` on the TopologyView; `(scene, camera, cols, rows) → frame`
stays pure. **No clock, no rand, no easing** — discrete per-keypress
steps only (the crate is currently 100% clock/RNG-free; stays that way).

Keys (chrome.pane == Topology guard, inserted BEFORE the WikiView
fallthrough — the match-arm-order trap the recon flagged):
`←`/`→` ry ∓ 15°, `↑`/`↓` rx ∓ 10°, `+`/`-` dist ∓ 0.5 (clamped
[1.5, 12.0]), `0` reset to front, `s` hypergraph ↔ surface, `f` cycle
field, `Tab`/digits/Esc unchanged (chrome-global keys win). Steps are
named constants in `views/topology.rs` (display constants, not
GameDefines — no gameplay meaning, the PAGE_SCROLL precedent).

## 7. Pixel tier (Task 35) — the two §11 opens RESOLVED at kickoff

**GO, with one prerequisite gap.** Rulings from the verified
ratatui-image 11.0.6 API (docs.rs cross-checked):
- Construction path: `StatefulProtocol::new(image, font_size, None,
  protocol_type)` — public, non-deprecated, ZERO terminal queries —
  driven entirely by the recorded `[render]` config (ADR097 D4
  verbatim: probe once in `babylon doctor`, runtime honors config).
- **BAN:** `Picker::from_query_stdio`/`from_query_stdio_with_options`
  anywhere in the shipped client — added to the same sentinel as the
  DeckWorld ban.
- **Prerequisite:** `CapabilityReport` + the `[render]` TOML table +
  a new host method (`render_config_json`, call0) gain the terminal
  **cell pixel dimensions (FontSize)** — without it the no-re-probe
  promise only holds for Halfblocks. Recorded `pixel_protocol="sixel"`
  DEGRADES to the glyph floor explicitly (ADR099: sixel is not a
  target) — never a `StatefulProtocolType::Sixel` construction.
- tmux/SSH: kitty is tmux-tolerant per the crate's own docs; Halfblocks
  is the universal floor; no SSH-specific defect documented. The
  owner-terminal live smoke remains an explicit Task 35 sub-item
  (non-blocking for the build, blocking for calling the tier DONE).

## 8. Expected drift (declared up front)

Landing the real topology pane flips, BY DESIGN: the harness's
`test_pane_fences_render_under_the_strip` topology case (drop that
parametrization), and the `wayne_opening_arc.json` transcript golden
(regen via `BABYLON_REGEN_TRANSCRIPT=1` — wheel rebuild FIRST, the
twice-bitten gotcha). This is planned drift, not regression.

## 9. Deviations discovered during implementation

(append here)
