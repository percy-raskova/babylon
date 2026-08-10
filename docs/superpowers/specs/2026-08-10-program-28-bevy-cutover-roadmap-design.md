# Program 28 — The Bevy Cutover: roadmap design

**Date:** 2026-08-10
**Status:** Director-approved in session (rulings R1–R7 below)
**Supersedes:** the Ratatui client lane (Amendment AC; Amendment AE clause xi) — pending
Amendment AF ratification
**Companions:** Program 27 Refoundation (continues unchanged on the engine side)

## 1. Where the project stands

- **P27 Phases 0 and 1 both closed.** Phase 0 cut the `p27-python-freeze` tag; the full BSL
  language stack (reader, §3.4 intensivity typechecker, §5 binary CAS, §3.7 fuel bound
  checker, §4 fuel-metered evaluator, structural verbs) lives in `rust/`.
- **P27 Phase 2 Slice 1 merged** (PR #461): `MemoryGraph` promoted, canonical state
  hash pinned byte-for-byte, scenario file → graph load path, and the Fundamental Theorem
  running end-to-end through the `babylon-tick` driver. The Rust engine runs its first tick.
- **The Director paused the hyperedge query lane** (directive 2026-07-31): the Slice 2
  evaluator proceeded dyadic-only. Substrate hyperedges stayed first-class per Amendment D.
- **hypergraph-rs xgi-compat parity completed 2026-08-04** (local main `ab558f0`,
  unpushed by policy): 316/492 honest conformance, 36 registered divergences. The Babylon
  swap (#282) awaits the Phase 2 substrate decision.
- **Seven director-gate ruling bundles** from the Game Design Standard §11 remain open
  (#376–#382). They gate content design.

## 2. Director rulings of 2026-08-10

| # | Ruling |
|---|--------|
| R1 | **Bevy replaces the Ratatui client outright** — Textual-deletion precedent: no deprecation window, no dual-client period. |
| R2 | **Parallel lanes** — the engine lane continues P27 Phase 2 while a new client lane scaffolds the Bevy app against the current engine seam (scenario load → tick → state hash). |
| R3 | **Visual scope at v1.0 = 2D map game + 3D moments** — county choropleth map, panels, and charts as the primary surface; selective 3D scenes (Patches the tutorial guide, the topology view) where they earn it. |
| R4 | **The shipped game is a pure Rust binary** — engine crates + Bevy client in one cargo workspace, no PyO3 in the play path. Python remains the offline data pipeline and the out-of-process AI observer, exactly where Amendment AE put it. |
| R5 | **All four side threads ride in the near-term roadmap**: the seven ruling bundles, the hypergraph-rs storage swap (ADR179 T3), the national incidence data program (#334), and **the hyperedge lane un-pauses** (lifts the 2026-07-31 hold). |
| R6 | **Ruling sessions start immediately on this doc's approval**, conducted interactively, while agents start the amendment + Bevy scaffold in parallel. |
| R7 | **First ruling bundle: #378 (strike & verb algebra)** — the verb algebra is the player's action surface and constrains doctrine (#377), pacing (#380), and what the client UI must present. |

## 3. Amendment AF — scope of the constitutional act

Nothing else may start until this lands: R1 contradicts two live clauses — AC's "the
Rust/Ratatui client IS v1.0's terminal client" and AE clause (xi), which requires
ratty + Ratatui as the in-game renderers. One docs PR, Director-ratified, covering:

1. **Bevy is the v1.0 client.** A standalone Bevy executable in the `rust/` cargo
   workspace; engine crates link in-process.
2. **Supersessions.** Amendment AC superseded in full; AE clause (xi) superseded; the
   glyph floor retired. The topology / hypergraph / Sankey visualization obligations
   transfer to Bevy scenes — the obligations survive, the renderer changes.
3. **Deletion ceremony.** The amendment deletes the Ratatui client (`rust/` TUI
   crates, the `babylon-tui` wheel) outright. The wheel leaves the default dependency
   set, so `uv sync` no longer requires cargo — which also removes the #463
   CI-timeout lane's trigger surface.
4. **Packaging.** The amendment retires `babylon play` (the Python CLI entry) from
   the play path; the game launches as a normal binary. The Python CLI survives only
   for the data-pipeline and observer periphery.
5. **Carried assets and contracts.** The crimson/gold/near-black aesthetic and Iosevka
   type direction; the SFX suite (39 CC0 sounds, ADR152) and soundtrack (13 CC0 tracks,
   ADR153) port to Bevy's audio/asset system; the ADR175 structured-JSONL engine log
   sink design stays as ruled; the client log contract re-points from
   `rust-client.log` to the Bevy client's log.
6. **Hyperedge formalism note.** Implementing `HyperedgeSet` / `NodeRef` / `EdgeRef` /
   `HyperedgeRef` in `BslType` mints no new mathematics — `bsl-language.rst` §2.6
   already specifies the element/result table — so it does not extend the
   formalism surface under Amendment AE. The amendment records this reading so the
   un-paused lane starts clean (closes the open question recorded on task #50).

## 4. The four lanes

```mermaid
flowchart LR
    AF[Amendment AF ratified] --> E & C & D & N
    subgraph E [Engine lane — P27 Phase 2 continuation]
        E1[Resume hyperedge queries + BslType refs] --> E2[Intrinsics under ADR176 r21] --> E3[hypergraph-rs storage swap ADR179 T3] --> E4[Content: BSL rules from ruled design]
    end
    subgraph C [Client lane — Program 28 Bevy]
        C1[B0 scaffold: window, palette, workspace] --> C2[B1 county map render] --> C3[B2 tick loop + panels] --> C4[B3 3D moments: Patches, topology]
    end
    subgraph D [Director lane]
        D1[Seven ruling sessions 378→377→376→379→380→381→382]
    end
    subgraph N [Data lane]
        N1[National incidence artifact #334]
    end
    D1 -.unblocks.-> E4
    E3 -.substrate stable.-> C3
```

### Engine lane (P27 Phase 2, continued)

1. **Un-pause the hyperedge query surface**: `hyperedges` / `members-of` /
   `hyperedges-of` query forms + the `HyperedgeSet` and ref types in `BslType`, per
   §2.6. Anti-Pattern VIII.9 still binds — a member list crosses whole, never C(n,2).
2. **Intrinsics** under ADR176 r21 ({exp, log} at most).
3. **The storage swap** (ADR179 T3): babylon-graph consumes hypergraph-rs as its
   storage backend behind the trait insulation layer, with the written capability
   delta the Director's caveat requires. The Aug 4 parity work (316/492, divergence
   registry) is the input; the byte-identical gate on Babylon's own goldens is the
   proof. Note: the frozen Python engine's XGI call sites are out of scope — the
   freeze supersedes #282's original Python-swap framing.
4. **Content encoding**: game rules land as BSL content as ruling bundles clear.

### Client lane (Program 28)

- **B0 — scaffold**: a `babylon-client` (name subject to the plan) Bevy crate in the
  `rust/` workspace; window opens; crimson/gold/near-black palette and type direction
  established; engine crates linked in-process.
- **B1 — the map**: county choropleth of real scenario data rendered as the primary
  surface. The spatial-adjacency lookup estate (Director ruling 2026-07-30) is the
  data source; the CSR-at-startup shape carries over.
- **B2 — the loop on screen**: tick advance, state panels, event feed — the
  scenario → tick → hash seam that already runs headless, made visible and playable.
- **B3 — 3D moments**: Patches the golden snub-nosed monkey as the tutorial guide
  (per the standing directive) and the topology view as 3D scenes inside the same app.

B0–B2 depend only on the merged Slice 1 seam; B3 waits for nothing on the engine side
but comes last because the 2D game must be playable first (R3).

### Director lane

The seven §11 ruling bundles, conducted interactively, in this order:
**#378** strike & verb algebra → **#377** doctrine surface → **#376** endings &
verdicts (already In Progress on the board) → **#379** multi-res & spatial (feeds the
map lane) → **#380** pacing, density & long-wave → **#381** narrator → **#382**
persistence & CI. Each session's rulings land as an ADR + issue closure with evidence.

### Data lane

The ADR171 national incidence artifact + data program (#334): agent work in the
Python data pipeline, producing the content the national-oppression axis needs.

## 5. Board hygiene Amendment AF triggers

- **Close as superseded:** #284 (kitty raster lane for the Map pane), #262 (eyes-on
  TUI campaign gate — the amendment deletes the client it would inspect; a Bevy
  eyes-on gate replaces it before v1.0).
- **Reshape:** #291 / #292 / #293 (installer + release trains) — a pure Rust binary
  ships as a normal game executable; the nix-bootstrap + wheel machinery in those
  trains shrinks accordingly. Rescope at plan time, do not close.
- **Re-scope:** #282 (Babylon swap) — becomes the engine-lane storage-swap task; the
  freeze supersedes its Python XGI-surface framing.

## 6. Non-goals

- No 3D globe or terrain-first presentation at v1.0 (R3 rejected it).
- No dual-client maintenance period (R1).
- No Python launcher for the game (R4).
- No new mathematics: the hyperedge types follow §2.6 as written; anything beyond
  it re-enters through the amendment process.
- No engine-lane pause for the client: the lanes are parallel by ruling (R2).

## 7. Success criteria

1. Amendment AF ratified and the constitutional docs swept (CONSTITUTION.md,
   CLAUDE.md, NORTH_STAR, architecture references).
2. The Ratatui estate deleted; `uv sync` completes without cargo; CI green without
   the wheel-build leg.
3. B2 reached: a person can open the Bevy app, see the county map, advance ticks,
   and watch state change — against the Rust engine, deterministic hash intact.
4. All seven ruling bundles closed with ADRs.
5. Hyperedge queries + storage swap merged with the byte-identical gate green.

## 8. Open questions (deferred to plan time)

- Bevy version pin and the plugin set (map rendering approach: custom mesh vs
  tilemap plugin) — resolve in the client-lane implementation plan with current docs.
- The Bevy eyes-on gate's definition (replaces #262).
- Whether the M1–M7 Ratatui estate's surface code (choropleth math, Sankey layout,
  chart estates) transplants into Bevy scenes or is rewritten — decide per-module at
  deletion time; the underlying data projections (`observe()` contract) carry regardless.
