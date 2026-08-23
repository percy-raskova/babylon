<!-- vale off -->
<!-- Asset names, commands, and provenance terms use required technical vocabulary. -->

# Bevy visual assets

This directory is the review index for Babylon's sixteen embedded Bevy images. `manifest.toml` is
the byte-level catalog, and `PROVENANCE.md` is the authoritative origin and license record.

## Asset families

- The interface family contains the title mark and five atlases. Original SVG masters live in
  `sources/`, and transparent PNG exports live in the Bevy embedded-asset directory.
- The Red Apparatus family supplies monumental key art and the counties and collapse banners.
- Empire Anatomized supplies systemic cutaways, the living map, the carceral circuit, the metabolic
  rift, and the topology banner.
- The Bunker Oracle supplies the intelligence-room environment plate and the shared material
  atmosphere.

The ten generated illustrations use exact final prompts from `prompts/`. Their selected WebP files
are opaque, use linear sampling, and remain below the repository's 1 MiB file limit.

## Interface exports

Run these commands from the repository root:

```bash
inkscape design/bevy-assets/sources/title-mark.svg --export-type=png --export-filename=rust/crates/babylon-client/src/visual_assets/embedded/title-mark.png
inkscape design/bevy-assets/sources/interface-atlas.svg --export-type=png --export-filename=rust/crates/babylon-client/src/visual_assets/embedded/interface-atlas.png
inkscape design/bevy-assets/sources/marker-atlas.svg --export-type=png --export-filename=rust/crates/babylon-client/src/visual_assets/embedded/marker-atlas.png
inkscape design/bevy-assets/sources/provenance-atlas.svg --export-type=png --export-filename=rust/crates/babylon-client/src/visual_assets/embedded/provenance-atlas.png
inkscape design/bevy-assets/sources/frame-atlas.svg --export-type=png --export-filename=rust/crates/babylon-client/src/visual_assets/embedded/frame-atlas.png
inkscape design/bevy-assets/sources/surface-atlas.svg --export-type=png --export-filename=rust/crates/babylon-client/src/visual_assets/embedded/surface-atlas.png
```

## Illustration exports

The OpenAI tool writes a selected source PNG outside the repository. Substitute its path for
`selected-source.png`. Use the following exact resize, crop, and encoding commands for each size
class.

Heroes:

```bash
magick selected-source.png -resize '1536x864^' -gravity center -extent 1536x864 /tmp/babylon-asset.png
cwebp -quiet -q 82 -m 6 /tmp/babylon-asset.png -o rust/crates/babylon-client/src/visual_assets/embedded/hero-red-apparatus.webp
```

Repeat the second command with `hero-empire-anatomized.webp` after processing that selected source.

Concept plates:

```bash
magick selected-source.png -resize '1024x1024^' -gravity center -extent 1024x1024 /tmp/babylon-asset.png
cwebp -quiet -q 82 -m 6 /tmp/babylon-asset.png -o rust/crates/babylon-client/src/visual_assets/embedded/concept-bunker-oracle.webp
```

Repeat the second command with `concept-living-map.webp`, `concept-carceral-circuit.webp`, and
`concept-metabolic-rift.webp` after processing each matching selected source.

Banners:

```bash
magick selected-source.png -resize '1536x384^' -gravity center -extent 1536x384 /tmp/babylon-asset.png
cwebp -quiet -q 82 -m 6 /tmp/babylon-asset.png -o rust/crates/babylon-client/src/visual_assets/embedded/banner-counties.webp
```

Repeat the second command with `banner-carceral.webp`, `banner-topology.webp`, and
`banner-collapse.webp` after processing each matching selected source. Update the corresponding
SHA-256 digest in `manifest.toml` whenever a runtime file changes.

<!-- vale on -->
