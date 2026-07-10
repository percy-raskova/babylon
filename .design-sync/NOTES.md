# design-sync NOTES — babylon-cockpit → claude.ai/design "Babylon Cockpit"

Repo-specific gotchas for future syncs. One bullet per fact.

## Setup facts

- The cockpit is an **app, not a library** — no `dist/` entry, no shipped `.d.ts`.
  The sync entry is the hand-curated barrel `src/frontend/design-sync.entry.tsx`
  (must live under `src/frontend/` so the converter's package.json walk-up finds
  `babylon-cockpit`; it is outside tsconfig `include`/vite/eslint/pre-commit scope,
  so no app tooling ever touches it). Component list = the full `componentSrcMap`
  enumeration in config.json (49 entries) — with no `.d.ts` tree that map IS the
  discovery, so **a new component must be added to BOTH the barrel and the map**.
- `cfg.tsconfig` points at `.design-sync/tsconfig.esbuild.json`, NOT the repo
  tsconfig: the converter's paths plugin probes extensions with `''` first and
  `existsSync()` accepts directories, so bare `@/*` resolves directory imports
  (`@/store`, `@/components/bbl`, `@/lib/verbs`, `@/lib/selectors`,
  `@/store/slices/panels`) to the directory itself and esbuild dies with
  "is a directory". The esbuild tsconfig lists each directory-alias exactly,
  ahead of the wildcard. A new directory-style alias import in app code will
  reproduce the failure — add an exact entry there.
- `cssEntry` is `src/frontend/.ds-css/compiled.css` (gitignored), produced by
  `buildCmd` (vite build + `cat dist/assets/*.css`). Tailwind 4 utilities only
  exist after the app build — re-run `buildCmd` before the converter whenever
  component classes or `src/index.css` change.
- Fonts: the app's `@font-face` rules use absolute `/fonts/...` URLs (vite
  public/), which the scrape can't resolve — `.design-sync/fonts.css` redeclares
  all 10 faces with relative paths into `src/frontend/public/fonts/` and ships
  via `extraFonts`. Keep it in lockstep with `src/frontend/src/index.css`.
- Converter deps pinned in `.ds-sync/` (gitignored, reinstall per clone):
  `esbuild ts-morph @types/react playwright@1.58.2 typescript@5.7.3`.
  - playwright **1.58.2** pins chromium **1208**, which is already in
    `~/.cache/ms-playwright/` — no browser download.
  - typescript must stay **5.x**: 7.x (tsgo) lacks the `createSourceFile` JS API
    package-validate's `.d.ts` parse check needs (it fails silently to
    "skipped" otherwise).
- `useStore` (the one zustand store) is exported from the barrel so authored
  previews can seed realistic world state with `useStore.setState(...)` before
  rendering store-coupled components. It is camelCase so it never gets a card.
- Scope: 44 `src/components/**` components + 5 observatory UI components.
  `ObservatoryRoute`, `main.tsx`, `App`, `routes/`, `mocks/` are deliberately
  out — route/mount machinery must never execute in previews.

## Tailwind vocabulary facts (hard-won)

- **JIT gap**: the app build only generates utilities the sources use — the
  design agent composes NEW layouts, so `.design-sync/ds-tailwind-entry.css`
  safelists the full Cold Collapse vocabulary via `@source inline()` and is
  what `buildCmd` compiles into `cssEntry` (via `npx @tailwindcss/cli@4.3.2`,
  pinned to the installed tailwindcss version).
- The `:root` type/tracking/spacing scale (`--text-md`, `--tracking-label`…)
  is **vars-only, NOT `@theme`** — no `text-md`/`tracking-label` utilities
  exist. The components' real idiom is arbitrary pixels (`text-[10px]`);
  `text-xs`-style utilities would silently be Tailwind's default rem scale, so
  they are deliberately NOT safelisted (loud absence beats quiet wrongness) and
  conventions.md teaches the pixel idiom. *Owner suggestion (not applied): move
  the scale into `@theme` in `src/frontend/src/index.css` to make `text-xs`
  = 10px real — an app-visible change, Percy's call.*
- `@source inline()` brace expansion cannot carry bracketed candidates
  (`text-{[8px],…}` generates nothing) — one `inline()` per arbitrary value.
- `@import "tailwindcss"` resolves relative to the IMPORTING file — the entry
  works because it imports `src/frontend/src/index.css`, which sits above
  `src/frontend/node_modules`. A test css outside the package tree fails.

## Preview-authoring patterns (folded from the 6-lane wave, 2026-07-10)

- **Store-driven components**: seed inside each cell's wrapper via
  `useStore.setState((s) => ({slice: {...s.slice, ...patch}}))`; cells sharing
  the singleton store need `cardMode: "single"` (or the component is
  pure-props and needs nothing).
- **Mount-fetch clobbering**: `panels.*` hooks fire `fetch(gameId)`
  unconditionally on mount; the harness 404s fast, and error text can replace
  seeded state (`EndStateScreen` pending branch, `DialecticSpread`'s
  unconditional error banner, timeseries/objectives). Two sanctioned fixes:
  pass `gameId=""` (hook guard suppresses the fetch) or seed
  `fetch: async () => {}` + `setMounted: () => {}` on the panel.
- **Frames**: use inline `style={{width, height}}` for pixel dims. Arbitrary
  classes compile now (previews are a Tailwind `@source`), but height-critical
  chains (recharts `ResponsiveContainer`, deck.gl `height:"100%"`) still need
  a REAL pixel height on an ancestor.
- **Capture harness**: default viewport 900×700 with 24px body padding
  (~852×652 usable); `cardMode`/`viewport` overrides are config-level.
  Verify raw PNGs, not the scaled sheet, for anything wider than ~850px;
  a cell's differentiator must be visible above the fold (`overflow-y: auto`
  hides silently). Viewport override changes re-stamp the contract — full
  `package-build.mjs` required, the targeted loop refuses with
  `[CONFIG_STALE]`.
- **WebGL components**: multi-cell map previews can lose basemap tiles on the
  3rd-4th sequential `?story=` reload (context churn — deterministic,
  byte-identical on re-capture); deck.gl's own layers survive. Grade on the
  data content. AppShell's composite capture shows the same tile absence.
- **Fixed-inset overlays** (`TakeoverOverlay`): wrap the cell in its own
  `<div className="h-screen w-full" style={{transform:"translateZ(0)"}}>` so
  `inset-0` resolves against a definite box.
- **DialecticSpread labels at most 2 oppositions** (frame.principal/secondary)
  — author exactly 2; a 3rd renders raw keys (type-vs-render contract
  disagreement, queued for Percy).
- The whole preview suite shares one fiction: tick 104, Wayne County FIPS
  26163, org-uaw-local-600, the WCLF-hall raid story — keep new previews in
  that world.

## Known render warns (triaged legitimate)

- `[FONT_MISSING]` for **"IBM Plex Mono", "Major Mono Display", "VT323",
  "DIN Alternate", "DIN Next"** — all are **fallback stack entries** behind
  self-hosted primaries that DO ship (JetBrains Mono, Redaction 35,
  Departure Mono, Space Grotesk); the DIN pair is `--font-system`'s
  intentionally-system stack. Nothing to source; the list grew when the
  safelist started generating `font-display`/`font-pixel`/`font-system`
  utilities (their full stacks became referenced).

## Re-sync risks (watch-list for the next run)

- `compiled.css` is generated state — always re-run `buildCmd` before the
  converter; the CLI version (4.3.2) is pinned to the installed `tailwindcss`
  and must be bumped in lockstep.
- **Store-slice refactors can silently stale the seeded previews**: a slice
  field rename re-keys only components whose own source changed — an authored
  preview seeding the old shape may render the empty state and still carry a
  `good` grade. After any store refactor, spot-check store-driven components
  (`--spot-check-components`).
- `ObservatoryPage` has exactly one statically-reachable state (backend-gated
  "unavailable") — its single-cell card is by design, not laziness.
- The exemplar fiction (tick 104 / FIPS 26163) spans many files — a lore
  change (e.g. renaming the raid story) means touching every wire preview.
- `GameSnapshot.endgame` (types/game.ts) is a dead field with zero readers —
  the real endgame path is `panels.endgame` reading `types/dialectic.ts`.
  Don't "fix" previews toward the dead field.
