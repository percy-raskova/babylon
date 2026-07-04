# DRAFT — Article VII Amendment: Cold Collapse Visual Canon

**Status**: DRAFT — proposed by spec-090 (Program 09, Lane W). **Ratification is the BD's** (Percy
Raskova, @percy-raskova), queued at spec-090 PR review. This file does NOT edit
`.specify/memory/constitution.md`; per R-VII (`project/09-program-full-game.md` §1) the token swap
must not merge to `dev` until this amendment is ratified.

**Proposed amendment letter**: **M** (next free after L). **Proposed version bump**: MINOR →
**v2.8.0** (material expansion of Article VII; per Governance IX versioning). The BD may instead
classify it PATCH if considered non-semantic; the version is the BD's call.

**Provenance of the canon**: Percy ratified the Cold Collapse palette as "official babylon canon"
in-chat 2026-05-17; the token file is `design/mockups/colors_and_type.css`
(`design/mockups/PROVENANCE.md`). Percy's 2026-07-03 palette ruling ("AI discretion, impress me")
delegates design judgment but does not bypass this constitutional process.

---

## Why an amendment is required

The ratified Cold Collapse canon conflicts with the **letter** of three Article VII clauses. Each
conflict is named below with the current text and a proposed reconciling replacement. The amendment
preserves every Article VII *principle* (color = meaning, luminosity = magnitude, data-ink
maximization, no chartjunk); it revises only the specific palette/typography/texture bindings those
principles were expressed through.

---

## Conflict 1 — Palette (VII.2 "Color as Data")

**Current text (constitution.md VII.2)**:

> **2. Color as Data** — BLOOD_VOID, BLACK, CRIMSON (power), GOLD (action/solidarity), SILVER (mass),
> ASH (muted). Luminosity = magnitude. All via palette tokens.

**Conflict**: Cold Collapse makes **spire cyan `#4dd9e6`** the primary agency accent, moves
**solidarity to green `#5fbf7a`** (mass-line growth), reserves **laser red `#ff3344`** for the
empire's threat/violence, and demotes **gold to the scarce `rupture #d4a02c`** — used rarely, only for
the revolutionary breakthrough. The old "GOLD (action/solidarity)" binding is superseded.

**Proposed replacement text (VII.2)**:

> **2. Color as Data** — The Cold Collapse token set (`design/mockups/colors_and_type.css`): a
> concrete-bunker substrate (VOID → RUST) under cool emissions (BONE → SHROUD). Each semantic accent
> encodes a *verb, not a vibe*:
> - **SPIRE** cyan `#4dd9e6` — primary: your agency, infrastructure online.
> - **LASER** `#ff3344` — the empire's violence, hostile action (threat).
> - **THERMAL** `#b8321f` — critical system stress.
> - **RUPTURE** bronze-gold `#d4a02c` — revolutionary breakthrough; **scarce, earned** (gold retained
>   only here — philosophically continuous with the old "gold = action": the decisive action is the
>   rupture).
> - **CADRE** `#6b8fb5` — labor aristocracy / info. **SOLIDARITY** `#5fbf7a` — mass-line growth.
>   **RENT** `#8b4d9e` — imperial extraction. **HEAT** `#d97a2c` — surveillance pressure.
>   **POPULATION** `#7a6db8` — demographic scale.
>
> Luminosity = magnitude (unchanged). All color via palette tokens; no hardcoded colors in components
> (unchanged). Print/cover "Luxe Gothic" chromatics are walled off from the web UI and bridge to it
> only via RUPTURE. The pre-Cold-Collapse names (CRIMSON/GOLD/SILVER as bound above) are retired;
> where legacy tokens survive during migration they are aliases onto this set (spec-090/091).

**Cartographic ramps (expansion of VII.3 Data-Ink / VII.7 Smallest Effective Difference)**:

> The six map layers use **luminance-monotonic single-hue ramps** (`colors-data.html`): heat,
> consciousness, rent, wealth, population (sequential; lightness encodes magnitude) and biocapacity
> (diverging: collapse ↔ regenerate). Rainbow scales (`dark-purple → crimson → gold`) are prohibited.
> Semantic **alarm terminals** (heat → laser, rent → thermal) may sacrifice strict top-end luminance
> monotonicity for danger signalling; this is an intentional, bounded exception, not a rainbow.

---

## Conflict 2 — Typography (VII.9)

**Current text (constitution.md VII.9)**:

> **9. Typography** — Monospace dominant. Max two typeface families.

**Conflict**: Cold Collapse uses a **four-family functional stack** (plus a system font for the Qt
Synopticon), each family doing exactly one job. "Max two typeface families" is exceeded.

**Proposed replacement text (VII.9)**:

> **9. Typography** — **Monospace-dominant for data** (JetBrains Mono). A **functional-role type
> stack**, self-hosted, no runtime web-font fetch: **JetBrains Mono** (data/terminal), **Space
> Grotesk** (chrome/sans), **Redaction 35** (display/epigraph), **Departure Mono** (pixel/readout);
> **DIN Alternate** as the Qt-Synopticon system font. Each family serves ONE role — role separation,
> not decoration, is what bounds the count. No family may be introduced without a distinct functional
> role. The old "max two families" cap is replaced by this role-discipline rule.

**Rationale**: The two-family cap existed to prevent decorative typographic sprawl. The Cold Collapse
stack is disciplined by *function* (data / chrome / display / pixel), which serves the same anti-sprawl
intent while carrying the distinctions the design encodes (a tick readout is not chrome; an epigraph
is not data).

---

## Conflict 3 — Texture (VII.10 Prohibitions / VIII.8 Decorative Visualization) — the R-CRT clause

**Current text (constitution.md VII.10)**:

> **10. Prohibitions** — No decorative glow, hardcoded colors, chartjunk, hidden state, gratuitous
> animation, corner legends, context-dependent color, mood over meaning.

**Current text (constitution.md VIII.8)**:

> **8. Decorative Visualization** — See VII.10.

**Conflict**: The ratified canon includes CRT texture — scanlines, vignette, film grain, phosphor
bloom/glow, flicker (`design/mockups/preview/effects-crt.html`). Read literally, "no decorative glow"
and "no chartjunk" forbid it.

**Proposed replacement text (VII.10, amended clause + R-CRT rider)**:

> **10. Prohibitions** — No hardcoded colors, chartjunk, hidden state, gratuitous animation, corner
> legends, context-dependent color, mood over meaning.
>
> **R-CRT — Diegetic texture, bounded (rider to VII.10 / VIII.8).** CRT texture (scanlines, vignette,
> grain, phosphor bloom, flicker, cursor blink) is permitted as **diegetic chrome** — on frames,
> headers, empty states, terminal shells, the Wire's samizdat surfaces — where it reads as the world's
> "concrete bunker monitor," not as data ornament. It is **forbidden inside any data-encoding surface**:
> chart plot areas, map fills, ramps, sparklines, and any element where color = meaning and the
> luminance-monotonic ramps bind absolutely. Texture that touches a data surface is chartjunk and
> prohibited. Playwright visual baselines pin both sides of this line.

**Rationale**: The prohibition's intent is that decoration must never corrupt data reading. R-CRT
preserves that intent exactly — texture is walled off from every surface where color/luminance carries
meaning — while permitting the ratified atmosphere on non-data chrome. "Decorative glow" becomes
"diegetic chrome texture, never on data."

---

## Invariance argument (Governance IX.2)

Each replacement is **at least as constrained** as its predecessor on the principle it serves:

| Principle | Old constraint | New constraint | At least as strong? |
|-----------|----------------|----------------|----------------------|
| Color = meaning | 6 fixed hues, gold=action | Full token set, each accent = one verb; components hardcode nothing | Yes — strictly more semantic bindings, still token-only |
| Luminosity = magnitude | asserted | asserted + six ramps operationalize it; rainbows explicitly banned | Yes — now enforceable in code |
| Typographic restraint | ≤2 families | role-discipline: one family per function, none without a role | Yes — bounded by function, not looser |
| No decoration-on-data | blanket "no glow/chartjunk" | texture allowed ONLY off data surfaces; forbidden on all data surfaces + baseline-pinned | Yes — data surfaces strictly protected; chrome carve-out is explicit and testable |

No principle is weakened; each binding is made more specific and more testable. No amendment in the
series is skipped (this is a self-contained Article VII revision; it does not depend on the pending
Amendments B/C/D).

## Artifacts to update on ratification (BD action, not spec-090)

1. `.specify/memory/constitution.md` — VII.2, VII.3/VII.7 (ramp rider), VII.9, VII.10/VIII.8 (R-CRT
   rider); Governance amendment list (add **Amendment M — Cold Collapse Visual Canon**); version →
   v2.8.0 (or as the BD classifies); Sync Impact header.
2. `ai-docs/decisions/` — ADR recording the palette/typography/texture ratification.
3. (Already done by spec-090) `web/frontend/src/index.css` carries the token swap on the branch,
   pending this ratification before merge.

## What spec-090 does NOT do

- Does not edit `constitution.md` (that is ratification, the BD's act).
- Does not merge the branch to `dev`/`main`.
- Does not gate its own token/font/ramp deliverables on ratification — the branch carries the full
  swap so the BD reviews working code; only the **merge** waits on the amendment.
