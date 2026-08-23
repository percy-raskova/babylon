<!-- vale off -->
<!-- Legal terms, license identifiers, and repository paths use required technical vocabulary. -->

# Licensing

Babylon splits its license by kind of content, not by directory tree shape:

- **Code: AGPL-3.0-or-later.** Full text: [`LICENSE`](LICENSE) (verified
  byte-identical to the FSF canonical text at
  `https://www.gnu.org/licenses/agpl-3.0.txt`).
- **Shipped creative assets: CC0-1.0.** Full text:
  [`LICENSE-ASSETS`](LICENSE-ASSETS) — a two-line pointer header followed
  by the Creative Commons canonical text
  (`https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt`),
  verified byte-identical from the legal text's first line onward.

This file states which directories fall under which license and flags the
ones that are not yet decided. It does not restate either license's legal
text — read `LICENSE` or `LICENSE-ASSETS` for that.

## AGPL-3.0-or-later (code)

Everything that is source, configuration, or docs-as-code, including:

- `src/babylon/**` — the Python engine (package root; see `pyproject.toml`'s
  `license` field).
- `rust/crates/**` — all five in-tree crates (`babylon-kernel`,
  `babylon-tick`, `babylon-bsl`, `babylon-graph`, `babylon-client`), via
  `rust/Cargo.toml`'s workspace `license` field and each crate's
  `license.workspace = true`. This includes `babylon-bsl`'s BSL rule
  content — BSL is executable rules-as-content (Constitution Amendment AE),
  not a creative asset, so it is code for licensing purposes.
- `design/bevy-assets/**` — original SVG interface masters, OpenAI image-generation prompt records,
  the asset manifest, and the authoritative provenance record.
- `rust/crates/babylon-client/src/visual_assets/embedded/**` — the Bevy interface PNG files and
  generated illustration WebP files listed in `design/bevy-assets/manifest.toml`.
- `tests/`, `tools/`, `scripts/`, `docs/` (the reStructuredText/Markdown
  sources, not any rendered build output), `data-artifacts.yaml`,
  `data-catalog.yaml`, and project TOML/YAML configuration.
- `.design-sync/**` (the project's own design-sync tooling and generated
  previews) — **except** the one vendored binary described below.
- `design/mockups/**` and `design/ui_kits/webapp_v2/` (JSX/HTML/CSS/MD/JSON
  markup and code) — **except** the one binary image described below.

## CC0-1.0 (shipped creative assets)

- `src/assets/sfx/` — the 39-sound interface SFX suite (ADR152). Also
  carries its own `src/assets/LICENSE` (identical CC0-1.0 text) and states
  "License: CC0-1.0" in `src/assets/README.md`.
- `src/assets/music/` — the 13-track soundtrack (ADR153). Same
  `src/assets/LICENSE` and README statement as above.

The new Bevy image estate described above does not change the CC0-1.0 classification of these
audio estates.

## Third-party, not relicensed

- `.design-sync/fonts-nerd/iosevka-nerd-mono.woff` — Iosevka Nerd Font,
  ships under its own upstream license (SIL OFL 1.1). This repository does
  not hold copyright over this file and does not relicense it AGPL or CC0.

## Known gaps — flagged, not yet decided

The following tracked paths are not covered by either license statement
above because their provenance or intended disposition has not been ruled
on. They are listed here rather than silently omitted so nobody assumes an
absence of a rule means "AGPL by default":

- **`assets/music/`** (legacy: `crisis/`, `fascist/`, `revolutionary/`
  suites + `babylon_theme_panopticon.mid` / `babylon_theme_phi.mid`, 32
  tracked files). Predates the `src/assets/` CC0 estates by about seven
  months and was never folded into ADR152/ADR153's CC0 dedication.
  Believed to be original project composition (same generator-script
  authorship pattern as the later CC0 estates) but unconfirmed — pending
  Director sign-off.
- **`assets/images/generated-image-cover-art-1769575216094.jpg`** —
  filename pattern suggests AI-image-tool output of unstated provenance;
  pending Director confirmation of tool/ToS before any license is applied.
- **`design/ui_kits/webapp_v2/assets/cover-art.jpg`** — same open question
  as the item above; unclear whether it is the same asset relocated or a
  distinct file.
- **`docs/examples/ck-intrigue-1.png`, `-2.png`, `-3.png`** — unreferenced
  anywhere in `docs/`; filenames suggest third-party reference screenshots
  (not Babylon's copyright to license either way). Pending a Director
  decision to delete or keep with an explicit third-party/fair-use note.
- **Reference/data estates** (`src/babylon/data/reference/*.csv`, the built
  `data/sqlite/marxist-data-3NF.sqlite`) derived from Census ACS, BEA, BLS
  QCEW, LODES, IRS SOI, and similar sources. Out of scope for this split —
  neither "code" nor "creative asset" in the sense this document addresses;
  a future issue should decide whether a source-attribution `NOTICE` is
  needed.

`assets/audio/**` (MP3 renders) and the gitignored files under
`assets/images/` (`fascist_flag.png`, `ff-template.zip`, `prolewiki.zip`,
`templates.zip`) are excluded from this document because they are not
tracked in git and are never shipped.

<!-- vale on -->
