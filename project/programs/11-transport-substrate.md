# Program 11 — The Transport Substrate (Constitution II.13)

**Status:** RATIFIED 2026-07-08 (owner directive, evening session). Charter for **spec-108**.
**Owner framing:** "part of the game is about how capital not only is produced, but also how
value flows and is valorized and circulated. volume 2 stuff… this should be the last thing
we need" — the final NEW feature of the current game vision; everything after is wiring,
performance, and record repair.

## Owner rulings (2026-07-08)

1. **Res-8 hexes are the underlying engine, NOT a visualization layer.** They program
   connectivity and transport invisibly; nothing in `web/` needs to render them.
2. **The AI must be able to construct new roads and repair existing ones** (state apparatus
   and organizations, via the OODA action path).
3. **A primitive degradation mechanic is required** — infrastructure condition decays.
4. **Repair/reconstruct/rebuild after damage** — player attacks, protests/riots, and
   uprisings damage infrastructure; actors can restore it.
5. Slime-mold routing is confirmed as the intended emergent-routing mechanism (per
   Constitution II.13 and M1 below).

## Why (theory)

Capital Volume II: surplus value produced is nothing until **realized**; commodities and
labor-power must physically MOVE through circulation, and circulation time gates turnover
and therefore the annual rate of surplus value. Transport is the material substrate of
realization — where it is cut, value is stranded (realization crisis); where it is dense,
turnover accelerates. Crises of disproportionality propagate along its topology. The
substrate also makes political action economically real: severing a corridor (riot, strike,
sabotage, state siege) strands value; rebuilding it is a class act with a class character.
Companion axis: Program 10's spectrum σ says which way value flows (up-gradient); this
program supplies the CHANNELS it flows through.

## Constitutional mandate (already ratified — II.13 "Transport Substrate")

Constitution `.specify/memory/constitution.md:194` mandates exactly this, with two
mechanisms: **min-cost flow** (deterministic routing: roads, rail, shipping lanes) and
**slime-mold conductivity** (emergent routing: informal supply chains, migration routes).
Transport edge types: `AIR_LINK`, `SHIPPING_LANE`, `ROAD`, `RAIL`. Declared a Volume II/III
mechanic mediating production and realization, whose topology determines where crises of
disproportionality and realization propagate.

## Design canon (M1, `07-chat-corpus-alignment.md:121` — Percy's own recorded design)

Per-tick `min_cost_flow` of firm orders over (hex × SCTG commodity) O-D pairs;
`effective_capacity = capacity × condition`; severed edges → 0; **unrouted demand →
unrealized value → realization crisis**; per-edge conductivity EMA
`D(t+1) = (1−α)·D + α·|Q|` so corridors form and decay. Percy requested the spec-kit
prompt herself (2026-04-21 ×2, 2026-05-03). M1 status was [E] (not built), Wave 3.

## As-built inventory (verified in-code 2026-07-08)

| Component | Status | Evidence |
|---|---|---|
| **Res-8 substrate** — `R8CellState` validated at H3 res-8; `R8FeatureType` HIGHWAY/ARTERIAL/LOCAL_ROAD; R7→R8 mesh via `h3.cell_to_children(r7, 8)`; NE-roads→feature pipeline (Interstate/Federal→HIGHWAY); R8→R7 aggregation | **BUILT + TESTED, engine-orphaned** | `src/babylon/infrastructure/` (16 modules: `r8_types.py`, `r8_mesh.py`, `r8_pipeline.py`, `r8_aggregation.py`, `snapping.py`, `capacity.py`, `nonlocal_edges.py`…); 10+ unit files + `tests/contract/test_infrastructure_contracts.py`. Imported outside the package by only 3 modules (`core/protocol_kit.py`, `config/defines/territory.py`, `hex_graph_bridge.py` type-only) — **no engine system consumes it at runtime** |
| **Roads + railways + airports readers** | BUILT | `natural_earth_reader.py` loads roads AND railroads (`RailroadFeature`, `load_railroads()` global + NA supplement, :83,:272) + lakes/regions from `natural-earth/packages/natural_earth_vector.sqlite`; `nonlocal_edges.py` has `JunctionType.AIRPORT` cascade |
| **Terrain classification** | BUILT but COARSE | `terrain.py` `DefaultTerrainClassifier`: hex ∩ NE polygons → **LAND / WATER / RESOURCE only**; `BiocapacityStore` stocks (FRESHWATER/FISHERY/SHIPPING_ACCESS/MINERAL/TIMBER/HYDROELECTRIC). **No mountain/swamp/desert/forest classes, no traversal-cost or impassability encoding anywhere** |
| **Min-cost-flow half of II.13** | **SHIPPING NOW** (spec-063, remediation lane 6.2) | `engine/systems/vol2_circulation.py` — Vol II circulation as ImperialRentSystem sub-stage 5c, LODES CSR matrix-vector per tick, deterministic; docstring: "Slime-mold conductivity (the emergent component of II.13) is out of scope"; spec-063 defers it to "a future spec that will treat the LODES OD matrix as a base layer and add conductivity as an overlay" (`specs/063…/spec.md:185`) |
| **Slime-mold conductivity** | **DOES NOT EXIST** | zero implementation; references only in constitution/M1/spec-063 deferrals |
| **Attack/repair seams** | PARTIAL | `ActionType.ATTACK_INFRASTRUCTURE` exists (`models/enums/actions.py`); `ooda/layer3.py:51 _propagate_infrastructure()` applies per-tick infrastructure deltas from ActionResults; `calculate_infrastructure_decay` in the formula registry (community-scoped, reusable). **No BUILD/REPAIR actions, no road-condition variable, no engine-side attack resolver yet** (that resolver arrives with remediation 2.4) |

## Data contract (verified on disk 2026-07-08)

| Ingredient | Source | Status |
|---|---|---|
| Road network + class | NE 10m roads (read by `r8_pipeline`) + **DOT HPMS** `dot/HPMS_Spatial_All_Sections_-_2024.csv` | PRESENT |
| **Road condition (calibrates degradation!)** | HPMS pavement/section attributes | PRESENT (loader needed) |
| Railways | NE 10m railroads (reader built) | PRESENT |
| Airports / intermodal / marine RoRo | `dot/NTAD_Aviation_Facilities_*.geodatabase`, `NTAD_Intermodal_Freight_*` ×2 | PRESENT (loader needed) |
| Freight commodity O-D by SCTG | **FAF5** `freight/faf/` (FAF5.7.1 State 2018–2024 CSV + county-level estimates + rail/pipeline factors) | PRESENT (loader needed) |
| Labor O-D | LODES `fact_lodes_commuter_flow` (2.6M rows, 2010–21) | **LOADED** |
| County/hex geometry | TIGER (res-7 pipeline `tools/ingest_tiger_geometry.py`) | LOADED |
| Terrain polygons | NE physical layers in `natural_earth_vector.sqlite` | PRESENT (taxonomy extension needed) |
| Commodity structure fallback | BEA I-O USE/TOTAL_REQ `fact_bea_io_coefficient` | LOADED |

Loaders live in the **babylon-data repo** per the standing owner ruling.

## Spec-108 charter (author via speckit; this is the scope contract)

- **US1 — Corridor mesh (engine-only):** a SPARSE res-8 corridor graph — R8 cells touched
  by NE/HPMS/NTAD features plus junction cells — NEVER a full national res-8 tiling
  (≈11M cells; violates the spec-087/089 storage regime). Per-edge state:
  `{edge_type: ROAD|RAIL|AIR_LINK|SHIPPING_LANE, capacity, condition ∈ [0,1],
  conductivity D}`. Terrain taxonomy extension (mountain/wetland/desert/forest/water
  classes from NE physical polygons) + a traversal-cost table in defines; impassability =
  cost → ∞. Aggregates to per-R7-pair connectivity coefficients consumed by the economic
  layer (pattern: existing `r8_aggregation.py`).
- **US2 — Routing:** min-cost flow over the mesh for goods (FAF5 O-D by SCTG; BEA I-O
  fallback) composing with the LODES labor base layer already live in
  `vol2_circulation.py`; slime-mold conductivity overlay `D(t+1)=(1−α)D+α|Q|`,
  `effective_capacity = capacity × condition`; unrouted demand emits an
  unrealized-value event → realization-crisis coupling (spec-018/023 machinery).
  Deterministic (III.7): no RNG anywhere in the update.
- **US3 — Degradation:** `condition` decays with flux + time, calibrated against the HPMS
  condition distribution; maintenance spend (state budget, faux frais of circulation)
  offsets decay; disused corridors lose conductivity (routes die back — the slime-mold
  decay term IS the disuse mechanic).
- **US4 — Construction / repair / destruction:** engine-side resolvers in the 2.4
  `VERB_RESOLVERS` registry: reuse `ATTACK_INFRASTRUCTURE` (player + org attacks lower
  `condition`/sever edges); add BUILD and REPAIR actions (new `ActionType`s or mapped —
  spec decision) usable by the state apparatus AI (spec-039) and organizations; riot/
  uprising events (StruggleSystem `UPRISING`, `EXCESSIVE_FORCE` aftermath) damage
  condition via the existing `layer3._propagate_infrastructure` delta seam.
- **Constraints:** defines-gated (`TransportDefines`, default OFF → baselines
  byte-identical; R-PROOF proof.md on activation); II.12 authoring API; III.7
  determinism A/B; C.1 round-trip for any new node/edge attrs; storage-budget gates
  (5.4's Gate C) must cover any new tables; **no visualization work** (res-8 never
  reaches the frontend; the existing res-7/6/3 map zooms are unaffected).

## Scheduling (synergistic slot)

Prerequisites: **6.2** (spec-063 tail — in flight, provides the LODES base layer),
**2.4** (verb dispatch registry — the resolver seam), **5.2 Batch C** (circulation
services wiring). Recommended: author spec-108 immediately after spec-107, implement as
the **Phase 6 feature slice** (after 6.2/6.3, alongside spec-106 perf work so the corridor
mesh is profiled from birth), exhibited in the 105 national capstone: routed circulation,
a corridor severed by an uprising stranding value, and a state-AI repair response.

## Open questions for Percy (answer async; none block spec authoring)

1. **Ownership/class character:** are corridors owned (state vs capital), and do tolls/
   freight rates extract rent along them (a spectrum-σ coupling)?
2. **Informal routes:** do slime-mold-only paths (migration, informal economy, smuggling —
   conductivity without built substrate) ship in slice 1 or as the follow-up?
3. **BUILD/REPAIR:** new `ActionType`s (cleanest; touches the 25×4 eligibility matrix) or
   mapped onto existing types?
4. **Waterways/ports:** NTAD marine data is present — in slice 1 (SHIPPING_LANE edges) or
   deferred with AIR_LINK to slice 2?

## Reading list

Capital Volume II (`Capital-Volume-II.pdf`, repo root — chs. on circulation time +
costs of circulation); Constitution II.13 (`.specify/memory/constitution.md:194`); M1
(`07-chat-corpus-alignment.md:121`); spec-036 (`specs/…` infrastructure topology — the
substrate builder); spec-063 (`specs/063-vol-ii-circulation/` — the min-cost-flow half,
esp. spec.md:185 deferral); Program 10 (the spectrum — value's direction; this program is
value's channels).
