# Program 28 B1 — The County Map: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to execute this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `babylon-client` draws the 3,222-county map of the United States as its primary
surface — real TIGER geometry, the ADR170 `county_extraction` tension lens on the crimson/gold
diverging channel, pan and zoom, and county hover with a readout — and every projection,
tessellation and hit-test decision holds up under a headless CI test.

**Architecture:** Four phases in four PRs. Phase A builds the **county atlas**: a Python
build-time tool that turns the sha-pinned `dim_county_geometry` artifact plus the committed
`county_adjacency.json` into one small, content-hashed binary the client loads with no parsing
dependencies and no drive access. Phase B stands up the **render lane** — atlas to triangulated
`Mesh2d` with per-vertex colors, a border mesh, and a bounded pan/zoom camera. Phase C wires the
**lens lane** — the ADR170 witness computed over live `MemoryGraph` territory nodes, the
diverging ramp, honest absence, and hover/selection through a startup-built spatial index.
Phase D bundles the OFL Iosevka face, runs the gates, and lands the milestone.

**Tech Stack:** Bevy **0.18.1** (`rust/Cargo.lock` pins it; the B0 pin holds — B1 adds only the
`pan_camera` feature), `earcutr` 0.5 (ISC, which `rust/deny.toml` already permits) for polygon
tessellation, Python 3.12 with shapely/pyproj/pyarrow (all existing project dependencies) for the
build tool.

**Source spec:** `docs/superpowers/specs/2026-08-10-program-28-bevy-cutover-roadmap-design.md`
(Director-approved, rulings R1–R10). **Predecessor plan:**
`docs/superpowers/plans/2026-08-10-program-28-kickoff-amendment-af-bevy-b0.md` (B0, merged as
PR #478).

**Governing rulings this plan carries out and does not reopen:**

- **ADR170** (2026-07-28) — the map tension lens IS `county_extraction`; `w = (phi - theta) /
  (phi + theta)` in `[-1, 1]`; theta is a US-internal **ratio of sums**, never a mean; the
  rendering is the **diverging channel**, crimson (Phi-source, bled) to gold (Phi-recipient,
  bribed), dropping the Lenin damping factor; the national-oppression overlay ships **declared
  absent**.
- **ADR179 T1 and the Director's 2026-07-30 spatial-adjacency ruling** — invariant spatial
  relations live in **static per-resolution lookup tables**, never in per-tick state; Rust
  assembles CSR at startup.
- **Amendment AF (i) and (iv)** — the shipped game runs as a pure Rust binary. Nothing links PyO3
  into the play path, so the deleted Ratatui client's "ask Python for WKT over FFI" geometry seam
  no longer exists. Geometry must arrive as a build-time artifact.
- **Constitution III.11 (Loud Failure)** — a county carrying no honest data this tick renders as
  **absence**, never as a fabricated zero on the ramp.

## Global Constraints

- Branch from `dev`; conventional commits; every commit ends with
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Worktree execution recipe (scar class #2): symlink `.venv` from the main checkout, copy `data/`
  and `.env`, commit with `PYTHONPATH="$PWD/src"`.
- Gates: `mise run check` for every phase; `mise run rust:check` for any `rust/` change (it runs
  `cargo clippy --workspace --all-targets --locked -- -D warnings`, so a `dead_code` or
  `too_many_arguments` warning reds the gate). Phase A also runs `mise run qa:regression` — the
  atlas tool must not move engine bytes.
- Vale: run `vale <file>` on every Markdown page you touch; drive the errors to 0. The house bar
  here really is zero — the B0 plan and the roadmap spec both score clean.
- **Palette canon (§9b, source of truth `src/babylon/render/tiers.py::TRUECOLOR_PALETTE`, mirrored
  in `rust/crates/babylon-client/src/palette.rs`):** FIELD `#1a0000`, BONE `#e8e8e8`, CRIMSON
  `#dc143c`, GOLD `#ffd700`, DIM `#404040`, MUTED_DARK `#202020`, ROYAL `#4169e1`, GREEN_DARK
  `#228b22`. The Python parity guard `tests/unit/render/test_rust_theme_parity.py` parses
  `palette.rs`'s `Color::srgb_u8(r, g, b)` literals — **keep every constant on one line**.
- **`PANEL` is not a §9b token.** The deleted client declared `PANEL = Rgb(32, 4, 4)` (`#200404`)
  locally, with a comment recording that it deliberately misses `MUTED_DARK`. B1 carries the same
  constant with the same honesty note, in a separate `map_palette` module, so the parity guard's
  table stays exactly the §9b eight.
- **No new mathematics.** The atlas projection uses closed-form cartography that runs at BUILD time
  and bakes into the artifact — no transcendental crosses the language boundary at runtime, so the
  CLAUDE.md libm-reproducibility hazard never arises. The lens formula is ADR170's, transcribed,
  not re-derived.
- **Power-of-10 rule 2 (statically bounded loops).** Every loop in the atlas reader walks a count
  the reader already checked against the buffer length. Check first, then iterate: no loop may take
  its bound from an unchecked number read out of a file.
- **CI reality.** `rust-gate` runs on `ubuntu-latest` with only compile-time Bevy headers present
  (`libasound2-dev libudev-dev libwayland-dev libxkbcommon-dev`). No display server, no GPU.
  Nothing in this plan may need `DefaultPlugins`, a window, or a wgpu device inside a test.
- **The repository carries the atlas; CI never builds it.** Its generator reads
  `dist/data-artifacts/` or the babylon-data drive; CI and the test suite read only the committed
  binary. That follows the standing rule that CI never touches the drive, and it copies the
  precedent `src/babylon/data/game/county_adjacency.json` already set.

---

## Decision: custom mesh, not a tilemap plugin

**Decided: build the map as Bevy `Mesh2d` geometry the client tessellates from real county
polygons.** `bevy_ecs_tilemap` loses for the county surface.

### Evidence

| Question | Finding | Source |
|---|---|---|
| What shapes can `bevy_ecs_tilemap` draw? | `TilemapType` offers `Square`, `Hex`, `Isometric` — **three fixed grid geometries**. A tile is a quad sampled from a texture atlas at a lattice position (`TilePos`, `TileTextureIndex`). No arbitrary-polygon tile exists, and no API accepts one. | `docs.rs/bevy_ecs_tilemap` — `map::TilemapType`; `tiles::{TilePos, TileTextureIndex}` |
| Can it recolor a tile per tick? | Yes — `TileColor(pub Color)` tints a tile, and the crate registers it as a reflected component. This half of the job it does well. | `docs.rs/bevy_ecs_tilemap` — `tiles::TileColor` |
| Does a 0.18-compatible release exist? | Yes: `bevy_ecs_tilemap` 0.18.1 (2026-01-16) tracks Bevy 0.18; 0.19.0 (2026-07-04) needs `bevy ^0.19.0`. Availability is not the blocker. | crates.io `bevy_ecs_tilemap` versions plus the 0.19.0 dependency list |
| What does the county geometry actually look like? | 3,222 rows of full-resolution TIGER/Line 2024 WKT — **8,245,427 vertices across 3,388 rings** — irregular, non-convex, wildly unequal in area, and adjacent along shared boundaries. | measured directly from `dim_county_geometry.parquet` (3,222 rows, zero null WKT) with shapely |
| Can Bevy draw one merged mesh with per-vertex color? | Yes. `Mesh::ATTRIBUTE_COLOR` on a `Mesh2d` with a plain `ColorMaterial::default()` tints per vertex — Bevy's own `mesh2d_vertex_color_texture` example does exactly this. | `docs.rs/bevy` — `Mesh2d`, `mesh2d_vertex_color_texture` |
| Does the 2D pipeline accept a line mesh for borders? | Yes. `Mesh2dPipelineKey::from_primitive_topology` handles `LineList` and `LineStrip` alongside the triangle topologies. | `bevy_sprite_render-0.18.1/src/mesh2d/mesh.rs:473–489` |
| Does a first-party bounded pan/zoom camera exist? | Yes, in 0.18.1: `bevy::camera_controller::pan_camera::{PanCamera, PanCameraPlugin}` with `min_zoom`/`max_zoom`/`pan_speed`/`mouse_pan_settings`, behind the non-default `pan_camera` feature. | `docs.rs/bevy/0.18.1` index; `bevy-0.18.1/Cargo.toml` (`pan_camera = ["bevy_internal/pan_camera"]`; `default = ["2d", "3d", "ui"]`) |

### Why the tilemap loses

A county is not a tile. Using `bevy_ecs_tilemap` would force us to **snap** 3,222 irregular
polygons onto a square or hex lattice — not a rendering choice but a data transformation that
destroys the boundaries. Three costs make that disqualifying:

1. **It falsifies the substrate.** The Constitution holds the spatial substrate immutable and
   makes every formal construct trace to a material relation. A county's *boundary* IS the
   material relation — `county_adjacency.json`'s 9,477 pairs come from it directly ("unordered
   pairs whose polygons intersect"). A lattice approximation would put an adjacency on screen
   that disagrees with the adjacency the engine reasons over.
2. **It cannot show the size range honestly.** The largest county runs roughly four orders of
   ten thousand times the smallest independent city. Any lattice fine enough to keep the small ones
   costs millions of tile entities; any lattice coarse enough to run fast deletes them. The
   intensive-aggregation discipline this project already enforces — never an unweighted mean
   across unequal units — has a visual twin here, and the lattice breaks it.
3. **The plugin's strengths do not apply.** Chunked rendering, GPU tile animation and
   texture-array atlases optimise a *lattice of textured quads redrawn every frame*. Our surface
   holds static geometry that recolors on a discrete, player-driven tick — the opposite workload.

**Where the tilemap stays a live candidate:** the H3 hex layer. `bridge_county_h3` (48,764 res-7
cells) and the Phase 0-D `h3_res7_*` products form a genuine hex lattice, and `TilemapType::Hex`
is the right tool the day a hex-resolution overlay gets specced. Ruling the plugin out for
**counties** does not rule it out for the project.

### Rejected alternatives, recorded

- **`bevy_ecs_tilemap` for the county surface** — rejected above. Recorded so a later reader does
  not re-litigate it without new evidence. Only one finding reopens it — arbitrary-polygon tile
  support, which the crate lacks and does not aim to grow.
- **One `Mesh2d` entity per county (3,222 entities, one `ColorMaterial` each).** Rejected. Bevy 2D
  batches by (mesh handle, material handle), so 3,222 distinct mesh handles cost 3,222 draw calls
  every frame, and a per-tick recolor churns 3,222 material assets. The merged-mesh design costs
  one draw call and one buffer write. Recorded because this is the obvious first instinct and it
  looks simpler right up until you count draw calls.
- **`MeshPickingPlugin` for county hover.** Rejected — see Task 10. It would work: the ray cast
  filters on `Or<(With<Mesh3d>, With<Mesh2d>, ...)>`, and `RayMeshHit` even carries
  `triangle_index`, which would name the county through a triangle-to-county table. But against
  ONE merged mesh the AABB cull degenerates to a whole-map hit, and `ray_mesh_intersection` then
  walks every triangle — roughly 357,000 Möller–Trumbore tests per pointer event. Task 10's
  startup-built grid index answers in constant time, needs no renderer, and so survives in CI
  where the picking backend cannot run. `MeshPickingPlugin` remains right for B3's 3D scenes.
- **A custom `Material2d` with a WGSL `shader` sampling a per-county value texture.** Deferred,
  not rejected. It would shrink the per-tick upload from a vertex-color buffer to a 3 KB data
  texture, which matters only if the tick rate climbs far past the player-driven 1 Hz this game
  runs at. It also adds a `shader` estate whose compilation no GPU-less runner can exercise.
  Revisit if profiling ever puts the color upload on the frame budget.
- **Baking triangle indices into the atlas instead of tessellating at startup.** Rejected on size:
  indices dominate, so baking them roughly quadruples the artifact, pushing a committed binary from
  about 1.6 MB toward 6 MB and into Git LFS territory — and this repository has already worn the
  LFS-pointer scar. Running `earcutr` at startup costs a one-time tessellation whose output Task 13's
  render digest pins anyway.

---

## File Structure

| Phase | File | Action | Responsibility |
|---|---|---|---|
| A | `tools/build_county_atlas.py` | Create | TIGER WKT plus adjacency to `county_atlas.bin` |
| A | `rust/crates/babylon-client/assets/map/county_atlas.bin` | Create | The committed, content-hashed artifact |
| A | `tests/unit/data/test_county_atlas_artifact.py` | Create | Hash and shape guard on the committed artifact |
| A | `.mise.toml` | Edit | `data:county-atlas` regeneration task |
| B | `rust/crates/babylon-client/src/atlas.rs` | Create | Dependency-free reader plus checks |
| B | `rust/crates/babylon-client/src/tessellate.rs` | Create | Rings to triangles (`earcutr`), triangle-to-county table |
| B | `rust/crates/babylon-client/src/map/mod.rs`, `map/mesh.rs`, `map/camera.rs` | Create | `MapPlugin`, mesh build, bounded pan/zoom |
| B | `rust/crates/babylon-client/Cargo.toml`, `rust/Cargo.lock` | Edit | `pan_camera` feature, `earcutr` dependency |
| C | `rust/crates/babylon-client/src/lens.rs` | Create | ADR170 witness over `MemoryGraph` |
| C | `rust/crates/babylon-client/src/map/ramp.rs` | Create | Diverging crimson-to-gold ramp plus `PANEL` absence |
| C | `rust/crates/babylon-client/src/map/pick.rs` | Create | Uniform-grid index plus point-in-ring hit test |
| C | `rust/crates/babylon-client/src/map/hud.rs` | Create | Hover readout and absence banner |
| C | `rust/crates/babylon-tick/content/scenarios/us-counties.bscn` | Create | Real territory scenario (fallback in Task 12) |
| D | `rust/crates/babylon-client/assets/fonts/` | Create | OFL Iosevka plus license |
| D | `ai/state.yaml`, `ai/decisions/` | Edit | Milestone record |

---

## Phase A — The county atlas artifact

### Task 1: The atlas format and its generator

**Files:**

- Create: `tools/build_county_atlas.py`

**Interfaces:**

- Consumes: `dist/data-artifacts/dim_county_geometry.parquet` (sha256
  `b838852e16175628e397a8f23fa178fd769f1aaf565f144cda63fbd6fe0d16ee`, 3,222 rows: `county_id`,
  `centroid_lat`, `centroid_lon`, `area_sq_km`, `geometry_wkt`), `dim_county.parquet` (3,285 rows,
  source of `fips`, `county_name`, `state_id`), and `src/babylon/data/game/county_adjacency.json`
  (303,790 bytes, 9,477 pairs, `content_hash`
  `5c71bbdaf30038e1d2dc5d30dd753b70c3e183c0618b53ff1d0c0dbdbe9bb197`).
- Produces: `rust/crates/babylon-client/assets/map/county_atlas.bin` — the single artifact every
  later task in this plan reads.

**Measured budget (do not re-derive; check against it).** Parsing all 3,222 WKT polygons with
shapely yields **8,245,427 vertices across 3,388 rings** at full TIGER resolution.
Douglas–Peucker with `preserve_topology=True`:

| tolerance | metres | vertices | rings | u16 position bytes |
|---|---|---|---|---|
| 0.0005° | 56 | 572,318 | 3,388 | 2.29 MB |
| **0.001°** | **111** | **363,513** | **3,388** | **1.45 MB** |
| 0.002° | 222 | 224,506 | 3,388 | 0.90 MB |
| 0.005° | 555 | 115,538 | 3,388 | 0.46 MB |

**Take 0.001° (about 111 m).** It sits at the knee: half the vertices of 0.0005° for a tolerance
still far below the smallest county's scale, and it holds the committed artifact near 1.6 MB —
under the size where Git LFS earns its keep.

- [ ] **Step 1: Write the format down first, in the tool's module `docstring`.** All integers
      little-endian. The reader checks every offset and count against the file length before any
      loop uses it (Global Constraints, Power-of-10 rule 2).

```text
header (fixed 128 bytes)
  magic        [u8; 8]   b"BABCTY\0\x01"
  version      u32       = 1
  flags        u32       = 0
  content_hash [u8; 32]  sha256 of every byte AFTER this field
  origin_x     f64       Albers metres of quantization grid origin
  origin_y     f64
  scale        f64       metres per quantization unit
  county_count u32
  ring_count   u32
  vertex_count u32
  csr_nnz      u32       directed adjacency entries (= 2 x pair count)
  source_hash  [u8; 32]  county_adjacency.json's content_hash, for lineage
  reserved     [u8; ..]  zero-filled to 128

county table    (county_count x 28 bytes)
  fips        [u8; 5]    ASCII, zero-padded
  pad         [u8; 1]
  ring_start  u32        index into the ring table
  ring_count  u16
  flags       u16        bit 0 = has adjacency row
  bbox        [u16; 4]   min_x, min_y, max_x, max_y in grid units
  centroid    [u16; 2]   grid units
ring table      (ring_count x 12 bytes)
  vertex_start u32,  vertex_count u32,  is_hole u8,  pad [u8; 3]
vertex array    (vertex_count x 4 bytes)   x u16, y u16
csr_offsets     ((county_count + 1) x u32)
csr_neighbors   (csr_nnz x u32)            county indices, ascending per row
name blob       u32 length, then UTF-8 "<county_name>, <state_abbrev>\n" per county in order
```

- [ ] **Step 2: Projection.** CONUS goes EPSG:4269 to **EPSG:5070** (NAD83 `Albers` for the lower 48) through
      `pyproj.Transformer`. Alaska (state FIPS `02`) uses EPSG:3338, Hawaii (`15`) EPSG:2782,
      Puerto Rico (`72`) EPSG:32161; each then scales and translates into an inset below and left
      of CONUS. Write the four affine triples into the tool as named constants, with a comment
      saying they carry cartographic placement rather than measurement — an inset is a declared lie
      about position that every US map tells, and the code should say so out loud. The projection
      runs **at build time only**; nothing transcendental crosses the language boundary at runtime.

- [ ] **Step 3: Simplify, quantize, assert.** Simplify at 0.001° **before** the projection step
      (the tolerance table above reads in degrees). After projecting, compute the composite
      bounding box, derive `scale = max(width, height) / 65535`, quantize, and **assert the worst
      round-trip error stays below 111 m** — quantization must never exceed the simplification it
      rides on. Fail loudly if it does; never quietly widen the tolerance.

- [ ] **Step 4: Adjacency to CSR.** Load `county_adjacency.json` and confirm its `content_hash` by
      recomputation — call `src/babylon/domain/geography/adjacency.py::load_adjacency_pairs` rather
      than writing that check twice. Map both FIPS of each pair to county indices, emit both
      directions, and sort each row ascending. A pair naming a FIPS with no geometry row counts as
      a **gap**, not an error: drop it and list it in Step 6's report. Counties with no adjacency
      row get `csr_offsets[i] == csr_offsets[i + 1]` and a clear `flags` bit 0 — an empty row is a
      real answer (island counties exist), and the flag separates "no neighbours" from "absent
      from the adjacency dataset".

- [ ] **Step 5: Determinism.** Sort counties by FIPS ascending before writing; order rings
      exterior-first, then holes in input order; never iterate a Python `set`, nor a dict whose
      insertion order follows parquet row groups. Then prove it: build twice into two temp files
      and assert the bytes match.

- [ ] **Step 6: Report on stdout** — county count, ring count, vertex count, byte size, worst
      quantization error, the dropped-pair gap list, and any county whose `area_sq_km` disagrees
      with its tessellated area by more than 2% (a simplification sanity check). This report goes
      into the Task 3 commit body.

- [ ] **Step 7: Commit** (`feat(tools): county atlas builder — TIGER geometry + CSR adjacency to a
      content-hashed binary`).

### Task 2: Generate and commit the artifact

**Files:**

- Create: `rust/crates/babylon-client/assets/map/county_atlas.bin`
- Edit: `.mise.toml` (new `data:county-atlas` task)

- [ ] **Step 1:** Confirm the inputs exist. A fresh clone lacks `dist/data-artifacts/` (`.gitignore`
      covers it and nothing has built it yet) — rebuild with `mise run data:artifacts`, or read the
      drive snapshot at `/media/user/data/babylon-data/backups/data-artifacts-v7/`. **Record in the
      commit body which input you used and its sha256.**
- [ ] **Step 2:** Run the tool; check the reported size against the 1.6 MB budget. If it passes
      3 MB, STOP and report — never quietly coarsen the tolerance, because the tolerance is now a
      recorded number that later drift measures against.
- [ ] **Step 3:** Add the `.mise.toml` task beside the other `data:` tasks:

```toml
[tasks."data:county-atlas"]
description = "Rebuild the committed county atlas the Bevy client renders (needs dist/data-artifacts or the babylon-data drive; CI never builds it)"
run = "uv run python tools/build_county_atlas.py"
```

- [ ] **Step 4:** Confirm no `.gitignore` rule catches the artifact
      (`git check-ignore -v rust/crates/babylon-client/assets/map/county_atlas.bin` finds nothing)
      and that Git LFS does not claim it (`git check-attr filter -- <path>` reports `unspecified`).
      A silent LFS pointer would hand the Rust reader 130 bytes of text where it expects geometry.
- [ ] **Step 5: Commit** (`feat(data): commit the county atlas artifact (3,222 counties, TIGER 2024)`)
      carrying the Task 1 Step 6 report in the body.

### Task 3: The artifact guard test

**Files:**

- Create: `tests/unit/data/test_county_atlas_artifact.py`

**Interfaces:**

- Consumes: the committed artifact. Produces: the tripwire that catches a hand-edited or
  half-regenerated atlas before the Rust reader ever sees it.

- [ ] **Step 1: Write the failing test** — parse the 128-byte header with `struct`, then assert:
      magic and version; `content_hash` matches a recomputation over the remaining bytes;
      `county_count == 3222`; `csr_nnz` equals `2 * 9477` less any dropped pairs, pinned to the
      exact number the Task 2 run reported; `source_hash` matches `county_adjacency.json`'s live
      `content_hash` (the cross-artifact lineage tripwire — regenerating adjacency without
      regenerating the atlas reds the gate); and the file length matches exactly what the header's
      counts imply, with no trailing bytes.
- [ ] **Step 2:** Run `mise run test:q -- tests/unit/data/test_county_atlas_artifact.py` → PASS.
- [ ] **Step 3:** `mise run check` and `mise run qa:regression` → green and byte-identical. The
      atlas tool reads reference data and writes a client asset; it must not move one engine byte.
- [ ] **Step 4: Commit**; open the Phase A PR
      (`feat(data): the county atlas — TIGER geometry and CSR adjacency as one pinned artifact`).
      Self-merge on green.

---

## Phase B — The render lane

### Task 4: The atlas reader

**Files:**

- Create: `rust/crates/babylon-client/src/atlas.rs`
- Edit: `rust/crates/babylon-client/src/lib.rs` (`pub mod atlas;`)

**Interfaces:**

- Produces:

```rust
pub struct CountyAtlas { /* owned decoded arrays */ }
pub struct County<'a> { pub fips: &'a str, pub name: &'a str,
                        pub rings: &'a [Ring], pub bbox: Bbox, pub centroid: Vec2 }

impl CountyAtlas {
    pub fn parse(bytes: &[u8]) -> Result<Self, AtlasError>;
    pub fn len(&self) -> usize;
    pub fn county(&self, index: usize) -> Option<County<'_>>;
    pub fn index_of_fips(&self, fips: &str) -> Option<usize>;
    pub fn neighbors(&self, index: usize) -> &[u32];   // the CSR row
    pub fn world_bounds(&self) -> Rect;                // for the camera clamp
}
```

Every later task consumes exactly this. `parse` takes `&[u8]` rather than a path, so tests can
feed it crafted bytes.

- [ ] **Step 1: Write the failing tests** in `atlas.rs`'s `#[cfg(test)]` module against
      `include_bytes!("../assets/map/county_atlas.bin")`: the atlas parses; `len() == 3222`;
      `index_of_fips("01001")` resolves and its `name` starts with `"Autauga County"`;
      `neighbors()` of that index comes back non-empty, ascending, and **symmetric** (every
      neighbour lists it back — a real property of the pair-derived CSR, and the one that catches
      an off-by-one in the offsets); `world_bounds()` comes back finite and non-degenerate.
      Then the **rejection** tests, one per failure mode, each asserting its own `AtlasError`
      variant: truncated file, wrong magic, wrong version, tampered byte (hash mismatch), a
      `ring_start` past the ring table, a `vertex_start + vertex_count` past the vertex array, and
      a `csr_offsets` row that runs backwards. A reader that accepts any of these commits the
      silent-corruption sin III.11 forbids.
- [ ] **Step 2:** `cargo test -p babylon-client` → FAIL.
- [ ] **Step 3: Write the reader** as **check-then-decode**: read the header, confirm the magic and
      version, verify the sha256, then test every count and offset against `bytes.len()` and
      against each other, and only after those checks walk the tables. Use `u32::from_le_bytes` on
      fixed slices; add no serialization dependency. Turn grid units back into `Vec2` world metres
      as `origin + grid_units * scale`.
      For the hash, `babylon-client` does not yet depend on `sha2` — first check whether
      `babylon-kernel` already exposes the sha256 behind `content_digest.rs` and reuse it instead
      of standing up a second one (DRY: search before adding).
- [ ] **Step 4:** `cargo test -p babylon-client` → PASS. `mise run rust:check` → green (clippy
      pedantic does not cover this crate, but `-D warnings` does).
- [ ] **Step 5: Commit** (`feat(client): county atlas reader with check-then-decode (B1)`).

### Task 5: Tessellation

**Files:**

- Create: `rust/crates/babylon-client/src/tessellate.rs`
- Edit: `rust/crates/babylon-client/Cargo.toml` (`earcutr = "0.5"`), `rust/Cargo.lock`

**Interfaces:**

- Produces:

```rust
pub struct Tessellation {
    pub positions: Vec<[f32; 3]>,   // z = 0.0
    pub indices: Vec<u32>,
    pub vertex_county: Vec<u32>,    // per vertex -> county index (drives per-vertex color)
    pub county_vertex_range: Vec<(u32, u32)>,  // per county -> [start, end) into positions
}
pub fn tessellate(atlas: &CountyAtlas) -> Tessellation;
```

`vertex_county` and `county_vertex_range` turn a per-tick recolor into an O(vertices) write across
one buffer instead of a mesh rebuild.

- [ ] **Step 1: Write the failing tests.** On a hand-built two-county fixture atlas — a unit square
      and a square with a square hole, with the bytes assembled inside the test rather than in a
      fixture file: the square yields 2 triangles; the holed square's triangle count equals
      `n - 2` for its combined ring vertex count; every index lands in range;
      `county_vertex_range` partitions `positions` contiguously with no gap and no overlap; and
      each county's summed signed triangle area matches its polygon area within 1e-6. Then against
      the real atlas: total triangles land near `vertex_count - 2 * ring_count`, and **no county
      tessellates to zero triangles** (a county that vanishes marks a simplification bug that would
      render as a hole in the map).
- [ ] **Step 2:** `cargo test -p babylon-client` → FAIL.
- [ ] **Step 3: Write it** on `earcutr::earcut(&flat_coords, &hole_indices, 2)`, per county:
      exterior ring first, then each hole's start index. Offset the returned indices by the
      county's vertex base. `earcutr` ships under ISC and `rust/deny.toml`'s `allowlist` already
      carries ISC — so no `deny.toml` edit, but run `cargo deny check` to confirm rather than
      assume.
- [ ] **Step 4:** `cargo test -p babylon-client` → PASS. Log the wall-clock of a full-atlas
      tessellation in the test output; if it passes 500 ms, note the number in the commit body as a
      startup-budget item (this cost lands once at startup, so slow-but-correct is fine here — just
      say the number out loud).
- [ ] **Step 5: Commit** (`feat(client): earcut tessellation of the county atlas (B1)`).

### Task 6: The map mesh

**Files:**

- Create: `rust/crates/babylon-client/src/map/mod.rs`, `rust/crates/babylon-client/src/map/mesh.rs`

**Interfaces:**

- Produces: `MapPlugin`; the `MapSurface` resource holding the fill-mesh and border-mesh handles
  plus the `Tessellation`; marker components `MapFill` and `MapBorders`.

- [ ] **Step 1: Write the failing headless test** in `tests/map_mesh.rs`. This is the CI-shaped
      pattern for the whole milestone — **`MinimalPlugins` plus `AssetPlugin`, never
      `DefaultPlugins`**:

```rust
use bevy::prelude::*;
use bevy::asset::AssetPlugin;

#[test]
fn map_plugin_builds_the_fill_mesh_headless() {
    let mut app = App::new();
    app.add_plugins((MinimalPlugins, AssetPlugin::default()));
    app.add_plugins(babylon_client::map::MapPlugin);
    app.update();

    let world = app.world_mut();
    let handle = world
        .query_filtered::<&Mesh2d, With<babylon_client::map::MapFill>>()
        .single(world)
        .expect("exactly one map fill entity");
    let meshes = world.resource::<Assets<Mesh>>();
    let mesh = meshes.get(&handle.0).expect("fill mesh is registered");
    assert_eq!(mesh.primitive_topology(), bevy::mesh::PrimitiveTopology::TriangleList);
    assert!(mesh.attribute(Mesh::ATTRIBUTE_COLOR).is_some(), "choropleth needs vertex colors");
    assert_eq!(
        mesh.count_vertices(),
        babylon_client::map::EXPECTED_VERTEX_COUNT,
    );
}
```

- [ ] **Step 2:** `cargo test -p babylon-client` → FAIL.
- [ ] **Step 3: Write `MapPlugin`.** A `Startup` system parses the embedded atlas
      (`include_bytes!`), tessellates, and spawns two entities:
      - **fill** — `Mesh2d` plus `MeshMaterial2d(ColorMaterial::default())` at `z = 0.0`, carrying
        `Mesh::ATTRIBUTE_POSITION`, `Mesh::ATTRIBUTE_COLOR` (every vertex starting at `PANEL` —
        the map opens honestly empty), and `Indices::U32` under
        `PrimitiveTopology::TriangleList`. Leave `RenderAssetUsages` at its default (main world
        **and** render world): a `RENDER_WORLD`-only mesh admits no recolor from a system, which
        is the whole point.
      - **borders** — `Mesh2d` under `PrimitiveTopology::LineList` over every ring's edges, one
        shared `ColorMaterial` in `DIM`, at `z = 1.0`.
      Panicking on an atlas failure is right here — a client that opens without its map is the
      loud-failure case, the same posture B0 took with the engine link.
- [ ] **Step 4:** `cargo test -p babylon-client` → PASS.
- [ ] **Step 5:** Eyes-on: `cargo run -p babylon-client` shows the United States in `PANEL` on the
      `#1a0000` field with `DIM` county borders. If the border mesh refuses to render, fall back to
      a build-time thin-quad border strip inside the fill mesh — record which one you used and why.
- [ ] **Step 6: Commit** (`feat(client): render the county surface as a merged Mesh2d (B1)`).

### Task 7: The camera

**Files:**

- Create: `rust/crates/babylon-client/src/map/camera.rs`
- Edit: `rust/crates/babylon-client/Cargo.toml`
  (`bevy = { version = "0.18", features = ["pan_camera"] }`),
  `rust/crates/babylon-client/src/main.rs` (drop B0's bare `spawn_camera`)

**Interfaces:**

- Produces: the camera bundle, plus the **pure function** `clamp_camera(translation: Vec2, zoom:
  f32, viewport: Vec2, bounds: Rect) -> Vec2` that this task's tests exercise with no renderer.

- [ ] **Step 1: Write the failing unit tests** for `clamp_camera`: fully zoomed out, the camera
      centres on `bounds.center()`; panned past the east edge, it clamps so the visible rect stays
      inside `bounds` grown by 10%; zoom clamps into `[MIN_ZOOM, MAX_ZOOM]`, where `MAX_ZOOM` means
      "one median county fills a third of the `viewport`" — compute the median county bounding-box
      diagonal from the atlas rather than guessing a magic number, and name the constant after what
      it means.
- [ ] **Step 2:** FAIL, then write it.
- [ ] **Step 3: Wire the camera.** `Camera2d` plus `Projection::Orthographic(OrthographicProjection {
      scaling_mode: ScalingMode::WindowSize, ..OrthographicProjection::default_2d() })` plus
      `PanCamera { min_zoom, max_zoom, rotation_speed: 0.0, key_rotate_ccw: None,
      key_rotate_cw: None, ..default() }` — **rotation off**: a rotated map disorients the player,
      and no ruling asks for one. Add an `Update` system applying `clamp_camera` after
      `PanCameraPlugin`'s own systems.
      Adding the `pan_camera` feature changes `rust/Cargo.lock`; refresh it with
      `mise run rust:lock-refresh` and confirm the diff only ADDS entries.
- [ ] **Step 4:** `mise run rust:check` → green. Eyes-on: drag to pan, wheel to zoom, and confirm
      nothing can push the map off screen.
- [ ] **Step 5:** `cargo deny check` — `pan_camera` lives inside Bevy, so expect no new licenses;
      if any turn up, add each to `deny.toml` with a one-line reason, never a blanket allow.
- [ ] **Step 6: Commit** (`feat(client): bounded pan/zoom map camera (B1)`). Open the Phase B PR
      (`feat(client): B1 render lane — atlas, tessellation, map mesh, camera`); self-merge on green.

---

## Phase C — The lens lane

### Task 8: The ADR170 witness over the graph

**Files:**

- Create: `rust/crates/babylon-client/src/lens.rs`

**Interfaces:**

- Produces:

```rust
pub struct CountyCell { pub fips: String, pub w: Option<f64> }
pub struct TensionLens {
    pub cells: Vec<CountyCell>,
    pub theta: Option<f64>,
    pub absent_reason: Option<String>,
}
pub fn county_tension(graph: &MemoryGraph) -> TensionLens;
```

- Consumes: `NodeType/TERRITORY` nodes in the live `MemoryGraph`.

**This task transcribes a ruled formula; it derives nothing new.** The reference implementation
sits at `src/babylon/projection/topology/tension.py` (148 lines, ADR170). Carry its semantics over
exactly:

```text
phi   = v / (v + s)               the county wage share
theta = sum(v) / sum(v + s)       RATIO OF SUMS over US counties, never a mean
w     = (phi - theta) / (phi + theta)      in [-1, 1]
```

Recover `v` as `s / e` from the two per-county stamps, where a contribution demands **both
`s > 0` and `e > 0`** (the un-hydrated fallback writes `0.0` to both, and a fabricated zero is
exactly what III.11 forbids). Let `phi + theta <= 1e-9` collapse `w` to `0.0` as the honest
all-bled-dry degeneracy, and let a graph holding **no** data-bearing county yield `absent_reason:
Some(...)` with every cell `None` — no norm exists, so the whole lens goes absent.

- [ ] **Step 1: Write the failing tests.** Build small `MemoryGraph`s by hand:
      (a) two territories with clean stamps, where `theta` equals the ratio of sums and **differs
      from** the mean of the two `phi`s (assert the difference — this catches the single most
      likely transcription slip); (b) the bled county scores `w < 0` and the bribed county
      `w > 0`; (c) a territory with `s > 0, e == 0` contributes nothing and reports `w: None`;
      (d) a graph with zero territory nodes yields `absent_reason.is_some()` and all-`None`;
      (e) every returned `w` lands inside `[-1, 1]`.
- [ ] **Step 2:** FAIL, then write it. The territory nodes' field names must agree with whatever
      Task 12's scenario declares — declare them as `const` strings in one place that both use.
- [ ] **Step 3:** `cargo test -p babylon-client` → PASS.
- [ ] **Step 4: Commit** (`feat(client): the ADR170 county_extraction witness over the live graph (B1)`).

### Task 9: The diverging ramp

**Files:**

- Create: `rust/crates/babylon-client/src/map/ramp.rs`

**Interfaces:**

- Produces: `pub fn ramp(w: Option<f64>) -> Color` and `pub const PANEL: Color`.

**The ruled rendering runs continuous, not banded.** ADR170 rules that "the lens value is `w`
itself on a crimson (Phi-source, bled) to gold (Phi-recipient, bribed) ramp", and it drops the
Lenin damping factor precisely so the raw value reaches the player. The deleted client's four-row
`TENSION_BANDS` table was a 16-colour terminal's compromise, and the M5 spec files those band
thresholds under **presentation constants** rather than engine data. Bevy carries no such
constraint, so B1 draws the ruled thing: a continuous ramp. The old thresholds survive as **legend
tick marks** at `w = -0.15` and `w = +0.15`, never as quantization.

- [ ] **Step 1: Write the failing tests** with exact `Srgba` byte assertions: `ramp(Some(-1.0))`
      gives CRIMSON `#dc143c`; `ramp(Some(1.0))` gives GOLD `#ffd700`; `ramp(Some(0.0))` gives BONE
      `#e8e8e8`; `ramp(None)` gives `PANEL` `#200404`; the ramp runs monotone — assert the red
      channel falls and the green channel rises across a sweep of 21 samples from −1 to +1; and
      `ramp(Some(0.0)) != ramp(None)` (nothing may confuse absence with the neutral midpoint —
      this assertion is what keeps the map from lying).
- [ ] **Step 2:** FAIL, then write it: blend CRIMSON to BONE for `w < 0` and BONE to GOLD for
      `w >= 0` through `Mix::mix` in `Oklab` (`Color::mix` blends in the working colour space; pick
      it on purpose and say why in a comment — a perceptual midpoint, not RGB mud). Clamp inputs
      outside `[-1, 1]` rather than extrapolating, and add a `debug_assert!` on the range so a
      formula bug shouts during development.
- [ ] **Step 3:** Add the recolor system: on a `LensChanged` event, walk `vertex_county` and write
      `ramp(cells[county].w)` into `Mesh::ATTRIBUTE_COLOR` through `Assets<Mesh>::get_mut`. One
      pass, one buffer, no mesh rebuild.
- [ ] **Step 4: Headless test** — build the app with `MinimalPlugins` plus `AssetPlugin`, install a
      lens holding a known cell, fire `LensChanged`, call `app.update()`, then assert every vertex
      colour inside that county's `county_vertex_range` equals `ramp(w)` and that another county's
      colours held still.
- [ ] **Step 5: Commit** (`feat(client): the crimson-to-gold diverging choropleth ramp (B1)`).

### Task 10: Hover, selection and the honesty banner

**Files:**

- Create: `rust/crates/babylon-client/src/map/pick.rs`, `rust/crates/babylon-client/src/map/hud.rs`

**Interfaces:**

- Produces: `pub struct CountyIndex; pub fn build(atlas: &CountyAtlas) -> CountyIndex;
  pub fn county_at(&self, p: Vec2) -> Option<usize>`; the `HoveredCounty` and `SelectedCounty`
  resources; the HUD text.

- [ ] **Step 1: Write the failing tests** for `county_at` — pure, no Bevy app: each county's own
      centroid resolves to itself across all 3,222, asserted as a **floor on the hit rate rather
      than 100%** (a centroid can legitimately fall outside a crescent-shaped county, so measure
      the real number, pin it, and list the exceptions by FIPS in the test's comment — an honest
      number beats a rounded-up claim); a point in the Gulf of Mexico gives `None`; a point inside
      a county's bounding box but outside its ring gives `None` (the test proving this is more than
      a bounding-box lookup); and the index comes out identical across two builds.
- [ ] **Step 2:** FAIL, then write it: a uniform grid over `world_bounds()` (start at 128×128
      cells — measure the mean candidate-list length and record it) mapping cell to candidate
      county indices by bounding-box overlap, then an even-odd crossing test against the
      candidate's rings, with holes inverting membership.
- [ ] **Step 3: Wire the interaction.** An `Update` system reads the cursor through
      `Camera::viewport_to_world_2d`, calls `county_at`, and sets `HoveredCounty`; a click promotes
      it to `SelectedCounty`. Selection draws a GOLD outline: reuse the border mesh path over the
      selected county's rings, at `z = 2.0`.
- [ ] **Step 4: The HUD.** Bottom-left text in BONE (the palette's own token): county name, state,
      FIPS, and either the `w` value to three decimals with its side named in words
      ("Φ-source (bled)" or "Φ-recipient (bribed)") or the literal string **"no data this tick"**.
      Top-left banner whenever `absent_reason.is_some()`: the reason string in CRIMSON. Carry the
      ADR170 national-oppression note as a persistent, quiet `DIM` footer too — the ruling says the
      map "ships with the absence declared", and an absence nobody ever sees is not a declared one.
- [ ] **Step 5: Headless test** proving that hovering a known world point sets `HoveredCounty` to
      the expected FIPS, driven by writing the cursor position resource directly rather than
      synthesizing window events.
- [ ] **Step 6: Commit** (`feat(client): county hover, selection and the absence banner (B1)`).

### Task 11: Feed the lens from the engine

**Files:**

- Edit: `rust/crates/babylon-client/src/engine_link.rs`, `src/main.rs`

- [ ] **Step 1:** Extend `engine_link` so the `MemoryGraph` the tick ran against outlives the call
      instead of dying inside `run_once`. Prefer adding `run_once_with_graph` to `babylon-tick`,
      returning `(TickReport, MemoryGraph)`, and re-expressing `run_once` through it — **never
      fork the tick flow**. B0's whole point was that the client and the CLI share one code path,
      and a second copy would quietly undo that.
- [ ] **Step 2:** After the startup tick, call `lens::county_tension(&graph)`, store the result as
      the `CurrentLens` resource, and fire `LensChanged`.
- [ ] **Step 3: Test** that B0's pinned hash assertion still passes untouched — this refactor must
      not move the engine.
- [ ] **Step 4: Commit** (`refactor(rust): expose the post-tick graph to the client lens (B1)`).

### Task 12: A real county scenario, with a declared fallback

**Files:**

- Create: `rust/crates/babylon-tick/content/scenarios/us-counties.bscn`, plus the generator step in
  `tools/build_county_atlas.py` or a sibling tool

**The point of this task: the map must show something true.** A scenario holds *initial material
conditions*, so baking real per-county quantities into `NodeType/TERRITORY` nodes is exactly what
a scenario is for — and it means the lens reads live graph state, which the engine will later
move, rather than a pre-computed picture.

- [ ] **Step 1: Check coverage before building anything.** The candidate inputs are
      `fact_qcew_county_rollup.parquet` (county wage totals, giving `v`) and
      `fact_bea_county_gdp.parquet` (county value added, giving `v + s`), both present in the
      artifact set. Load both, join to the 3,222 atlas counties, and **report the coverage count
      and the gap list**. Do not proceed on a guess: this plan's author confirmed these files
      exist, not that they cover every county.
- [ ] **Step 2 (if coverage holds up):** Emit `us-counties.bscn` declaring the territory fields and
      one node per covered county carrying its FIPS and the two quantities. **Omit** counties
      without data rather than zero-filling them, and put the omission count in the commit body.
      Point the client's startup at this scenario.
- [ ] **Step 2b (declared fallback, if coverage falls short):** Ship
      `content/scenarios/counties-lens-smoke.bscn` — a hand-written dozen counties with real FIPS
      and hand-set quantities that straddle theta — and leave the national map on the
      honest-absence path (all-`PANEL`, banner showing). **This counts as a legitimate B1 outcome,
      not a failure.** Record it in the PR body and open an issue against the data lane. Never
      manufacture national numbers to make the screenshot prettier; that is the exact failure
      ADR170 names when it says the map must not lie to the player.
- [ ] **Step 3:** Whichever branch you took, add a test asserting the scenario loads, mints the
      expected node count, and produces a lens whose `theta` is finite and whose cells straddle
      both signs.
- [ ] **Step 4: Commit** (`feat(content): county territory scenario for the map lens (B1)`).

---

## Phase D — Type, gates, milestone

### Task 13: The render digest — the milestone's byte contract

**Files:**

- Create: `rust/crates/babylon-client/tests/render_digest.rs`

**Why not a screenshot golden.** The CI runner offers no GPU and no display server, so a
screenshot golden would need a software `rasterizer` this repository does not carry, and it would
pin anti-aliasing noise rather than meaning. The GPU-free counterpart is a **digest over the
buffers the GPU would have received**. That follows the same instinct as III.12's text-assertion
medium, and it reds for exactly the reasons a screenshot would: geometry moved, colours moved, the
lens moved.

- [ ] **Step 1: Write the test** — build the app headless, run the startup tick, fire the lens,
      then sha256 over, in order: the quantized positions (rounded to whole metres, so a
      floating-point last-bit difference across machines cannot red the gate falsely), the index
      buffer, and the vertex colour buffer as `u8` quadruples. Assert against a pinned hex string.
- [ ] **Step 2: Capture the digest** from the first green run and pin it. Comment it exactly as B0
      commented its hash: a move here means the ATLAS, the tessellation, or the LENS moved —
      investigate before re-pinning, and record any deliberate move's drift in the commit body.
- [ ] **Step 3:** Run it twice in one session and again on a second `cargo test` invocation to prove
      stability, then `mise run rust:check`.
- [ ] **Step 4: Commit** (`test(client): render digest golden for the county map (B1)`).

### Task 14: Bundle the OFL Iosevka face

**Files:**

- Create: `rust/crates/babylon-client/assets/fonts/IosevkaTerm-Regular.ttf`,
  `IosevkaTerm-Bold.ttf`, `OFL.txt`, `README.md`
- Edit: `rust/crates/babylon-client/src/main.rs`, `src/map/hud.rs`

**Why this rates a task and not a footnote.** B0 shipped Bevy's built-in font and said so in its
module `docstring`, because this build machine carries **only Nerd Font patched Iosevka**
(`~/.fonts/Iosevka Terminal/`, 81 files, all `IosevkaTermNerdFont*`) **with no license file beside
them**. This repository does not ship a font whose license text it lacks.

- [ ] **Step 1: Fetch the upstream OFL build** — the `be5invis/Iosevka` release carries
      `IosevkaTerm-Regular.ttf` and `-Bold.ttf` alongside the SIL OFL 1.1 text. Copy both faces and
      the license into `assets/fonts/`, and write a short `README.md` beside them naming the
      release version, the source URL, and the license — matching the provenance discipline
      `src/assets/README.md` already sets for the SFX and soundtrack estates.
- [ ] **Step 2:** Load through `AssetServer` in `main.rs` and `hud.rs`
      (`assets.load("fonts/IosevkaTerm-Regular.ttf")`), replacing the built-in default in B0's
      title and driving the HUD readout. Bold is the ladder's emphasis face; never synthesize a
      bold by scaling.
- [ ] **Step 3:** Eyes-on that the title and HUD render in Iosevka. Glyph rendering needs the asset
      pipeline, so **skip any headless test asserting glyph output** — assert only that the handle
      resolves to a loaded `Font` asset, which `AssetPlugin` alone can prove.
- [ ] **Step 4:** `cargo deny check` — a bundled font is data, not a dependency, so the `allowlist`
      stays put; the license file in the asset directory carries the record.
- [ ] **Step 5: Commit** (`feat(client): bundle the OFL Iosevka Term face for the client type ladder`).

**If this machine cannot reach the upstream release:** leave B0's built-in font in place, land the
rest of the task as a no-op, and put the question to the Director (see Open Questions).
**Never ship the Nerd Font files without their license.** A missing font is a cosmetic gap; an
unlicensed asset inside a shipped binary is not.

### Task 15: Gates, state, PR

- [ ] **Step 1:** `mise run rust:check` → green. `mise run check` → green.
- [ ] **Step 2:** `mise run qa:regression` and `mise run qa:vault-regression-ci` → byte-identical.
      B1 touches no engine code beyond Task 11's refactor, and that refactor must move nothing.
- [ ] **Step 3:** Note the CI cost: `rust-gate` now compiles Bevy plus `earcutr` and links a 1.6 MB
      asset into the test binary. Its cargo cache keys on `rust/Cargo.lock`, which this milestone
      changes twice (Tasks 5 and 7) — expect two cold runs.
- [ ] **Step 4:** Update `ai/state.yaml` (B1 reached: county map, lens, hover) and the GitHub
      project board's Program 28 client lane. Add an ADR only if a Director ruling lands against
      the Open Questions below; the rendering decision itself is an engineering choice recorded in
      **this document**, which is where the roadmap spec §8 sent it.
- [ ] **Step 5:** Open the PR (`feat(client): B1 — the county map, tension lens and hover`), body
      carrying the eyes-on screenshot, the atlas report from Task 1 Step 6, the Task 12 branch you
      took, and the pinned render digest. Self-merge on green per the standing autonomy rulings.

---

## Open questions — Director-level only

1. **Which Iosevka build ships inside the binary?** The aesthetic line names "Iosevka Term".
   Upstream offers plain **Iosevka Term** (OFL 1.1, clean) and the **Nerd Font patched** build
   (icon glyphs for UI chrome, but a license the patch project assembles from more than one
   upstream). This machine holds only the patched build, without its license file. B1 defaults to
   plain OFL Iosevka Term Regular plus Bold; confirm, or name the variant and weight ladder you
   want. **Nothing blocks on this** — B1 lands on Bevy's built-in font if the file never arrives,
   and swapping a font file later costs one line.

2. **Do the Alaska, Hawaii and Puerto Rico insets need Director sign-off?** An inset states a
   declared cartographic fiction: Alaska sits at roughly a third of true scale, below and left of
   the continental map. For a game whose whole subject is the geography of imperial rent, "how the
   map places the periphery relative to the core" arguably makes a political statement rather than
   a layout choice — Puerto Rico especially, given ADR171's national-question line. B1 builds the
   conventional composite and flags it. **Nothing blocks on this**, but a ruling would be worth
   having before players see the map.

3. **Continuous ramp against the inherited four bands.** B1 reads ADR170 literally ("the lens value
   is `w` itself on a crimson to gold ramp") and draws a continuous diverging ramp, treating the
   deleted client's `TENSION_BANDS` as the terminal-era compromise the M5 spec files under
   presentation constants. Flagged rather than assumed, because it changes what the player
   perceives about size. **Nothing blocks on this** — Task 9's ramp is one function, and banding it
   again is a small local change if the Director prefers the discrete reading.
