# Bevy visual assets — `Design`

<!-- vale off -->
<!-- Art-direction vocabulary intentionally exceeds the procedural STE lexicon. -->

**Status:** Approved in chat on 2026-08-22
**License:** AGPL-3.0-or-later
**Scope:** A broad, reusable art direction and runtime asset foundation for `babylon-client`

## Purpose

Babylon's Bevy client currently has one compiled data asset, the county atlas, and no image-loading
surface. This change gives the game a recognizable face: hero art, banners, concept art, a title
mark, and reusable interface graphics. It changes presentation only. Engine state, rules, tick
ordering, and deterministic hashes remain untouched.

The direction deliberately combines three compatible modes:

- **The Red Apparatus** supplies monumental constructivist key art: hard diagonals, massed civic
  architecture, broken infrastructure, and crimson pressure moving through gold relation lines.
- **Empire Anatomized** supplies diagrammatic concept art: logistics, finance, policing, extraction,
  labor, and land shown as one material system rather than isolated spectacle.
- **The Bunker Oracle** supplies in-game atmosphere: damp concrete, repaired instruments, engraved
  plates, map tables, and a private intelligence room built to decode a collapsing order.

These modes are a family, not three competing themes. Illustrations may use material neutrals,
smoke, rust, paper, and concrete beyond the strict UI palette. Data-bearing surfaces continue to
use the existing Bevy role colors and must remain legible.

## Deliverable

The first visual-development suite contains sixteen Bevy-ready raster assets.

### Illustration set

- `hero-red-apparatus.webp` — 1536 by 864, the primary landscape key art.
- `hero-empire-anatomized.webp` — 1536 by 864, a second landscape key art with a systemic cutaway.
- `concept-bunker-oracle.webp` — 1024 by 1024, the intelligence-room environment plate.
- `concept-living-map.webp` — 1024 by 1024, the county map as a tactile relation instrument.
- `concept-carceral-circuit.webp` — 1024 by 1024, a carceral logistics and extraction plate.
- `concept-metabolic-rift.webp` — 1024 by 1024, extraction, transport, consumption, and ecological
  damage shown as one circuit.
- `banner-counties.webp` — 1536 by 384, a wide story banner for the county atlas.
- `banner-carceral.webp` — 1536 by 384, a wide story banner for the carceral story.
- `banner-topology.webp` — 1536 by 384, a wide banner for graph and flow surfaces.
- `banner-collapse.webp` — 1536 by 384, a wide banner for collapse and end-state presentation.

The illustrations do not depict a canonical victory, named faction, doctrine emblem, or new ending.
They reveal material relations and atmosphere without deciding gameplay or the ideological line.

### Interface set

- `title-mark.png` — 768 by 192, a Babylon tower-and-dialectical-split mark with transparent
  background.
- `interface-atlas.png` — 512 by 512, a 4-by-4 atlas of play, pause, step, speed, lens, map, story,
  beat, roster, material, topology, flow, pin, inspect, warning, and close symbols.
- `marker-atlas.png` — 384 by 256, a 3-by-2 atlas of hover, selection, pin, event, origin, and target
  map markers.
- `provenance-atlas.png` — 256 by 256, a 2-by-2 atlas for material, absent, not-computed, and
  redacted states.
- `frame-atlas.png` — 256 by 64, four 64-by-64 nine-slice cells for neutral, selected, critical,
  and absent frames.
- `surface-atlas.png` — 384 by 128, three 128-by-128 tiles for concrete, hatch, and paper surfaces.

Every interface raster has an editable SVG master. AI-generated illustration sources are preserved
by their exact prompt records and committed raster output; no attempt is made to trace them into
fake vector masters.

## Visual rules

- The county map and all live charts remain clean data surfaces. Illustration and texture sit in
  story cards, menus, loading surfaces, gallery views, and other non-data negative space.
- Interface graphics use the current Bevy palette from `palette.rs`. Illustrations are
  palette-led, not palette-imprisoned: near-black, crimson, gold, bone, rust, smoke, concrete, and
  desaturated earth tones are welcome.
- Geometry is sharp, structural, and asymmetrical. Hard diagonals, crop marks, registration marks,
  engraved grids, and purposeful negative space are encouraged.
- Avoid generic neon cyberpunk, glossy sci-fi dashboards, rounded cards, empty telemetry, and
  triumphalist propaganda poses.
- Text is never baked into AI-generated art. Bevy supplies readable labels so localization and
  accessibility remain possible.
- Color is never the only meaning channel for controls, map markers, or provenance states.
- Motion can be added later only when driven by a real tick, event, selection, or transition.

## Source and runtime layout

Editable and provenance material lives under `design/bevy-assets/`:

- `sources/` contains SVG interface masters.
- `prompts/` contains one Markdown prompt record for each AI-generated illustration.
- `manifest.toml` records every runtime asset ID, source record, runtime path, category,
  dimensions, sampler, atlas layout when present, SHA-256 digest, and license.
- `PROVENANCE.md` records tool, date, authorship, curation, and the absence of copied third-party
  artwork.
- `README.md` is the small review index and records deterministic rasterization and optimization
  commands.

Runtime assets live under `rust/crates/babylon-client/src/visual_assets/embedded/`. Bevy 0.18.1's
`embedded_asset!` macro compiles them into the executable, avoiding a new install-time asset-root
contract. PNG is used for transparent interface art; WebP is enabled on the existing Bevy
dependency for compact opaque illustrations. No SVG loader or additional crate is introduced.

Every file remains below the repository's 1 MiB blob limit. The manifest pins the selected outputs
byte-for-byte; regenerating or replacing an image requires updating its digest and provenance.

## Bevy loading contract

`VisualAssetsPlugin` registers all sixteen raster files. A typed `VisualAssets` resource owns named
image handles and texture-atlas layouts. Typed enums expose atlas indices, so gameplay code does not
use magic numbers or string paths.

The plugin also owns two conservative production uses:

- it renders the title mark beside the existing readable `BABYLON` text; and
- it renders the appropriate counties or carceral banner behind the tick-0 story card, hiding the
  banner whenever the card is dismissed.

The remaining hero art, concept plates, and banners are immediately available through the typed
resource and appear in a Bevy `visual_assets` gallery example. They do not cover the live county map
or change any engine-facing module.

An asset-load failure is loud. Tests wait for Bevy's loaded state with a fixed polling bound and
report the failing typed asset ID. No unrelated fallback art or transparent placeholder is used.

## Behavioral contracts

Implementation follows red, green, refactor.

The static asset contract verifies:

- the manifest and runtime directory contain exactly the same sixteen raster assets;
- every SVG master is well-formed and every prompt record is present;
- every PNG or WebP decodes with the declared dimensions and color mode;
- every SHA-256 digest and category count matches;
- every file remains below 1 MiB;
- interface SVG colors belong to the current Bevy role palette; and
- every asset declares `AGPL-3.0-or-later` provenance.

The Rust contract verifies:

- all embedded images reach Bevy's loaded state within a fixed polling bound;
- the typed catalog contains sixteen images and the declared atlas cell counts;
- every typed atlas index stays within its layout;
- the title mark retains a readable `BABYLON` text sibling;
- story selection chooses the counties or carceral banner and story-card dismissal hides it;
- the gallery creates one labeled display entry per asset; and
- adding `VisualAssetsPlugin` leaves the engine tick and deterministic hash byte-identical.

GPU screenshots are review evidence, not CI goldens, because backend and font rasterization vary by
machine. The source files, manifest dimensions, and selected raster bytes are the durable contract.

## Success criteria

The work is complete when all sixteen assets exist with recorded provenance, the two hero pieces,
four concept plates, and four banners form one recognizable visual family, all files load through
the typed Bevy resource, the production title and story card use the appropriate art without
covering live data after dismissal, the gallery exposes the complete suite, and scoped plus
repository-wide verification remains green.

<!-- vale on -->
