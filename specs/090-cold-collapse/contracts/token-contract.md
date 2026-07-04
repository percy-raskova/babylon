# Contract: Token-Contract Test

The token-contract test (`web/frontend/src/theme/tokens.contract.test.ts`) is the executable contract
between the shipped `index.css` / `theme/colors.ts` and the ratified canon. It is written **red-first**.

## C1 — Palette tokens present in `index.css`

For each canon token below, `index.css` MUST contain `--<name>: <value>` (case-insensitive hex).
Source: `design/mockups/colors_and_type.css`.

```
--babylon-void        #06070b     --babylon-bone        #d8dce0
--babylon-tar         #0d1016     --babylon-fog         #8a93a0
--babylon-concrete    #11141c     --babylon-ash         #5e6470
--babylon-rebar       #1a1f2a     --babylon-shroud      #3d4250
--babylon-wet-steel   #28303d     --babylon-spire       #4dd9e6   (PRIMARY)
--babylon-rust        #3a3530     --babylon-spire-dim   #2a8a93
--babylon-laser       #ff3344     --babylon-thermal     #b8321f
--babylon-rupture     #d4a02c     --babylon-cadre       #6b8fb5
--babylon-solidarity  #5fbf7a     --babylon-rent        #8b4d9e
--babylon-heat        #d97a2c     --babylon-population   #7a6db8
```

## C2 — Type stack tokens

`index.css` MUST name each canon primary family in its font stack:
- `--font-mono` contains `JetBrains Mono`
- `--font-sans` contains `Space Grotesk`
- `--font-display` contains `Redaction 35`
- `--font-pixel` contains `Departure Mono`

## C3 — Banned fonts absent

`index.css` MUST NOT contain (case-insensitive): `Inter`, `Roboto Mono`.
(Mirrors the CLI gate `rg -i 'roboto mono|inter' web/frontend/src/index.css` → empty.)

## C4 — Self-hosted `@font-face`

`index.css` MUST declare `@font-face` for the four families whose `src` references
`/fonts/…woff2` (local). No `@font-face`/`@import`/`url()` may reference `fonts.googleapis.com` or
`fonts.gstatic.com`.

## C5 — Data ramps (import `DATA_RAMPS` from `theme/colors.ts`)

Each ramp's stops MUST equal the canon (`design/mockups/preview/colors-data.html`):

```
heat          #0d1016 #3a3530 #7a4720 #b8581f #d97a2c #ff3344
consciousness #0d1016 #1f2c3d #345670 #4a86a0 #6bbcc8 #4dd9e6
rent          #0d1016 #2e2236 #56356b #8b4d9e #a83a78 #b8321f
biocapacity   #b8321f #7a3525 #3d4250 #3a6b48 #5fbf7a
wealth        #0d1016 #2a251f #4d3f28 #8a6a2a #d4a02c
population    #0d1016 #23223a #3d3868 #5a4f95 #7a6db8 #a89dd0
```

Plus: `getColorScale(layer)` returns a function for all 11 `MapLayer` values; `rgbaToCss` behaviour
unchanged (existing `colors.test.ts` assertions still pass).

## C6 — Lens ramp wiring (`lensDefinitions.ts`)

`getLensRampStops(lensId)` (or `LENS_RAMP_STOPS[lensId]`) MUST equal `DATA_RAMPS[lens.primaryLayer]`
for all four lenses (economic→rent, political→consciousness, social→heat, strategic→consciousness).

## Expected lifecycle

1. Test committed → run → **RED** (current `index.css` has gold/Inter; `DATA_RAMPS` absent).
2. Migration lands → run → **GREEN**.
3. `mise run web:check` green overall; Vitest total ≥ 310 (this adds cases, never removes).
