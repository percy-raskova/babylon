# Phase 1 Data Model: Cold Collapse Design-System Migration

This is a presentation-layer feature; the "data model" is the set of design tokens, ramps, and font
assets. No database, no runtime entities.

## Entity: Design Token

A named CSS custom property with a canon value.

| Field | Type | Notes |
|-------|------|-------|
| `name` | string | e.g. `--babylon-spire`, `--font-mono`, `--space-4` |
| `value` | string | hex / stack / length; byte-identical to canon |
| `layer` | enum | `theme` (Tailwind `@theme`) \| `root` (`:root` alias/const) |
| `role` | enum | substrate \| emission \| accent \| alias \| typography \| spacing \| elevation \| crt |

**Validation**: every token's `value` MUST equal the corresponding value in
`design/mockups/colors_and_type.css`. Source of truth is the canon file.

**Canonical token groups** (from `colors_and_type.css`):
- Substrate: `void #06070b`, `tar #0d1016`, `concrete #11141c`, `rebar #1a1f2a`, `wet-steel #28303d`, `rust #3a3530`
- Emissions: `bone #d8dce0`, `fog #8a93a0`, `ash #5e6470`, `shroud #3d4250`
- Accents (each = a verb): `spire #4dd9e6` (primary/agency), `spire-dim #2a8a93`, `laser #ff3344` (threat), `thermal #b8321f` (critical), `rupture #d4a02c` (revolution, scarce), `cadre #6b8fb5` (info), `solidarity #5fbf7a` (mass-line), `rent #8b4d9e`, `heat #d97a2c`, `population #7a6db8`
- Luxe (print/cover ONLY, bridges to web only via `--babylon-rupture`): `pitch #120004`, `arterial #8b0a1a`, `vellum #f4ece0`, `buried-hope #1a3a1a`, `forest-dim #2a6b2a`
- Type stack: `--font-mono` JetBrains Mono, `--font-sans` Space Grotesk, `--font-display` Redaction 35, `--font-pixel` Departure Mono, `--font-system` DIN Alternate
- Scales: type xs..3xl, weights 400/500/600/700, tracking, leading, spacing 1..16, radius sm..full, shadows, glows, CRT constants

## Entity: Data Ramp

An ordered hex-stop list for a map layer; lightness encodes magnitude.

| Field | Type | Notes |
|-------|------|-------|
| `layer` | enum | heat \| consciousness \| rent \| biocapacity \| wealth \| population |
| `stops` | string[] | 5–6 hex stops, canon order |
| `kind` | enum | sequential \| diverging (biocapacity is diverging) |
| `terminal` | enum | glow \| alarm \| scarcity \| plain — semantic end-stop flavour |

**Validation**:
- `stops` MUST equal the canon stops in `design/mockups/preview/colors-data.html`.
- Sequential ramps start at the darkest substrate (`#0d1016`).
- Single hue family per ramp (no `crimson→gold` rainbow interior).
- Diverging (biocapacity): darkest at neutral centre, brightening to both ends.
- NOT asserted: global strict luminance monotonicity (alarm terminals + diverging break it by design — see research R3).

## Entity: Font Asset

A self-hosted binary + its license.

| Field | Type | Notes |
|-------|------|-------|
| `family` | string | JetBrains Mono \| Space Grotesk \| Redaction 35 \| Departure Mono |
| `weight` | int | 400 / 500 / 600 / 700 |
| `path` | string | `web/frontend/public/fonts/<family-slug>/<file>.woff2` |
| `format` | const | `woff2` |
| `license` | string | sibling `OFL.txt` / `LICENSE` |

**Validation**: every `@font-face` `src` in `index.css` MUST resolve to a committed local file; no
`src` may point at a remote host. Each family MUST have a committed license file.

## Entity: Article VII Amendment (draft)

A review artifact (Markdown), not code. See `article-vii-amendment.md`.

| Field | Type | Notes |
|-------|------|-------|
| `conflict` | enum | palette (VII.2) \| typography (VII.9) \| texture (VII.10/VIII.8) |
| `current_text` | quote | the clause as it stands in `constitution.md` |
| `proposed_text` | draft | the reconciling replacement |
| `status` | const | `draft` — awaiting BD ratification at PR |

**Validation**: draft exists, referenced by `plan.md`; `.specify/memory/constitution.md` unchanged on branch.
