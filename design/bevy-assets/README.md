<!-- vale ste.UnapprovedWords = NO -->

# Bevy visual assets

This directory is the review index for Babylon's sixteen embedded Bevy images. `manifest.toml` is
the byte-level catalog, and `PROVENANCE.md` is the authoritative origin and license record.

## Asset families

### Interface

This family contains the title mark and five atlases. Original SVG masters live in `sources/`.
Transparent PNG exports live in the Bevy asset directory.

### Red Apparatus

This family supplies monumental key art and the counties and collapse banners.

### Empire Anatomized

This family supplies systemic cutaways, the Living Map, the `Carceral Circuit`, the Metabolic Rift,
and the topology banner.

### Bunker Oracle

This family supplies the intelligence-room plate and the shared material atmosphere.

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

The OpenAI tool writes a selected source PNG outside the repository. Replace `selected-source.png`
with its path. Use these exact commands to resize, crop, and encode each size class.

Heroes:

```bash
magick selected-source.png -resize '1536x864^' -gravity center -extent 1536x864 /tmp/babylon-asset.png
cwebp -quiet -q 82 -m 6 /tmp/babylon-asset.png -o rust/crates/babylon-client/src/visual_assets/embedded/hero-red-apparatus.webp
```

After you process the next selected source, change the output name to
`hero-empire-anatomized.webp`.

Concept plates:

```bash
magick selected-source.png -resize '1024x1024^' -gravity center -extent 1024x1024 /tmp/babylon-asset.png
cwebp -quiet -q 82 -m 6 /tmp/babylon-asset.png -o rust/crates/babylon-client/src/visual_assets/embedded/concept-bunker-oracle.webp
```

After you process each selected source, change the output name to `concept-living-map.webp`,
`concept-carceral-circuit.webp`, or `concept-metabolic-rift.webp`.

Banners:

```bash
magick selected-source.png -resize '1536x384^' -gravity center -extent 1536x384 /tmp/babylon-asset.png
cwebp -quiet -q 82 -m 6 /tmp/babylon-asset.png -o rust/crates/babylon-client/src/visual_assets/embedded/banner-counties.webp
```

After you process each selected source, change the output name to `banner-carceral.webp`,
`banner-topology.webp`, or `banner-collapse.webp`. Update the SHA-256 digest in `manifest.toml` when
a runtime file changes.
