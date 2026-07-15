# Wave 3 — The Weather Layer (implementation map)

**Source:** owner request 2026-07-14 ("consider implementing `ai/_inbox/lawvere-visualization.md`
and `ai/_inbox/weather-visualization.md` for our frontend as part of our workflow"), following
Wave 2's close (`reports/wave2-implementation-map.md`, all 3 rounds landed on
`feature/epochs-wave1-spine`, full `mise run check` 9786 green).

**Thesis of the two briefs, merged:** the Lawvere brief supplies a *visual grammar* (rendering
rules that ARE the physics); the weather brief supplies the *instruments*, mapped onto the
System-18/19/20 field stack. Babylon already computes fields, gradients, Laplacians, temporal
derivatives, regimes, and rupture criteria every tick — the gap is almost entirely the seam
(serialize → lens), the same "computed but never shown" pattern Waves 1–2 attacked. This map is
the verified version: every claim in both briefs was checked against code by three read-only
sweeps on 2026-07-14 before scoping. Corrections are recorded below so the briefs' errors don't
become our roadmap.

## Verified-reality census

| Brief claim | Verdict | Evidence |
|---|---|---|
| Systems 19/20 compute per-node fields, edge gradients, Laplacians, df/dt, principal-field competition every tick | **CONFIRMED** (unconditional, positions 19–20) | `simulation_engine.py:395-396`; `contradiction_field.py:134-198`; `field_derivative.py:118-358` |
| "Five contradiction fields" | **CORRECTED: two** — production computes only `exploitation` (per-node, spatially varying) + `atomization` (global scalar broadcast); the richer `field_registry` path is test-only, unwired | `contradiction_field.py:149-198`; zero production `field_registry` wiring |
| Edge gradient = f(target) − f(source) is the value-transfer direction | **CONFIRMED** formula; **CORRECTED** scope: computed over ALL edges whose endpoints are both social_class nodes, not a curated EXPLOITATION/TRIBUTE/WAGES set | `field_derivative.py:146`, `:128-139` |
| `field_derivatives` "mostly unserialized" | **UNDERSTATED: fully unserialized** — zero hits in `web/`. ⚠ Naming trap: the existing `contradiction_field` table + `GET /contradiction/` endpoint carry **System-18 opposition gap/rate snapshots**, not the 19/20 field stack. New serialization must use a distinct name (`field_state`) | `engine_bridge.py:185-225`, `:2762-2849`; `api.py:644-659` |
| RUPTURE = gap > threshold AND rate rising; Mao score = gap·(1 + w·\|rate\|) | **CONFIRMED verbatim** | `contradiction.py:284-306`; `opposition.py:453-455` |
| Regime classifier reproduction/crisis/sublation | **CONFIRMED** — and already written per tick as graph attr `dialectical_regime` | `regime.py:38-86`; `contradiction.py:312-379` |
| UPRISING payload (node_id, trigger, p_acq/p_rev, agitation…) | **CONFIRMED**, richer than the brief says | `struggle.py:338-406` |
| Feb field-theory spec deferred GUI viz | **CONFIRMED verbatim** | `specs/002-dialectical-field-topology/spec.md:321` |
| Fronts from `derived_class_cell` disagreement + `side_flips` turbulence | **BRANCH-GATED** — Program 19 shadow attrs/sentinel exist only on unmerged `feature/19-emergent-class-partition` | agent sweep, `git show 89d26c59` |
| "κ is recomputed on topology change"; curvature-colored terrain edges | **FALSE** — real Ollivier-Ricci math exists (`formulas/curvature.py:32`) but has zero production callers; `persist_contradiction_fields(tick, fields, [], …)` hardcodes an empty curvature list; `edge_curvature` Postgres table exists, forever empty | `headless_runner/bridge.py:631`; `postgres_schema.py:198` |
| Π₀/β₀ George Jackson bifurcation number "already computed" | **DORMANT** — `bifurcation_tendency()` computes β₀/β₁ but its only caller (`BifurcationMonitor`) is never instantiated in production. A *different* live signal exists and is already serialized: per-county `bifurcation_score` (−1 rev / +1 fascist sign convention, solidarity-*density*-based) | `bifurcation/analysis.py:405`; `crisis/bifurcation.py:40`; `engine_bridge.py:6428` |
| Per-node fascist/revolution routing by SOLIDARITY edges | **CONFIRMED engine-side** (`fascist_alignment` node attr written every tick, FASCIST_DRIFT events) — **not serialized** to any endpoint | `reactionary.py:73-136` |
| XGI hull / community hyperedges organization gauge | **BLOCKED ON DATA** — CommunitySystem is real+registered but `community_memberships` is never assigned by any scenario builder (engine bridge docstring says so itself); snapshot ships `"hyperedges": []` stubs. 🐛 Bonus bug: `GET /hypergraph/communities/` calls `bridge.get_hypergraph_communities`, **a method that does not exist** → guaranteed AttributeError 500 | `community.py:277-302`; `engine_bridge.py:1388-1399`, `:6628`; `api.py:785` |
| g₃₃ opacity for Dept-III flows | **PARTLY** — national g₃₃ scalar conditionally computed (falls back to hardcoded 0.33 when gamma_calculator unwired); `ValueTensor4x3.visibility_g33` never set from it; snapshot `dept_iii_visibility: {}` is a hardcoded stub | `tick/system/__init__.py:490-511`; `tensor.py:277`; `engine_bridge.py:6634` |
| "Bondi repression doc" / state's-view spec | **DOES NOT EXIST** in repo (closest analog: Sparrow `G_observed` centrality, spec-039) | rg: 1 hit = the brief itself |
| M/L/E simplex phase panel | **DEFERRED BY OWNER** already (energy-labor-money research program, 2026-07-14 ruling) | memory: direction-energy-labor-money-simplex |
| Frontend: vector/particle lens needs new deps | **FALSE — zero new deps.** ArcLayer/LineLayer/PathLayer/TripsLayer/PathStyleExtension all installed, unimported. But it IS a new lens *kind* (union has exactly ramp + categorical today) touching ~8 files, and the map renders **no** edge/flow geometry today | agent sweep; `package.json`; `lens.ts:114-118` |
| Radar loop "just built" | **HALF-TRUE** — class_snapshot history is live (W2 R3); there is **no hex-history endpoint** (`inspectorTerritoryHistory` is an Untyped consumer-less stub) and **no playback/scrubber UI** anywhere. Postgres has the data (`v_hex_state_asof`; never `WHERE tick=N` on the sparse table) | `endpoints.ts:148-155`; spec-089 gotcha |
| Forecast from determinism | **CONFIRMED in principle**; today's preview returns two graph-wide scalars + affected ids — no per-territory magnitudes. A real forecast needs an N-tick lookahead run on a discarded graph copy | `types/game.ts:600-607` |

## The grammar (adopt as binding design law — Round 0)

1. **Extensive renders as stuff, intensive renders as color.** Flows/masses → particles, flux
   width, volume; rates → hex fill and edge hue only. Zoom-merge then visibly sums stuff and
   re-renders color — conservation made perceptible.
2. **Quantities flow, qualities cut.** Continuous animation only for field evolution/value flows;
   every enum flip (regime, phase, edge mode) is a hard cut, no tweening.
3. **One motion budget per tick.** Only the principal contradiction (max |df/dt| — already
   computed as `principal_field`) pulses; all else static between ticks.
4. **Curvature is terrain, not decoration** — geometry deforms only when someone acts.
   (Held until κ actually exists — see Deferred.)

These are data-free presentation policy; they go in `DESIGN_BIBLE` and govern every Wave-3 round.

## Execution rounds (single-writer on engine_bridge.py; all agents Sonnet; TDD; qa:regression 5/5 or STOP)

- **Round 0 — grammar + record (docs, cheap):** grammar laws into DESIGN_BIBLE §weather; census
  corrections into this map (done); state.yaml.
- **Round 1 — light the field seam (backend, byte-identical-safe by construction):** serialize
  the System-19/20 stack under a **new, distinct name** (`field_state`, avoiding the
  `contradiction_field` System-18 collision): per-node `contradiction_fields` +
  `field_derivatives` (gradients, laplacian, df_dt), graph `principal_field` +
  `dialectical_regime`, per-node `fascist_alignment`. Class-graph → territory projection via the
  existing tenancy resolution (gradients live on class-class edges; the map needs
  territory-anchored arcs). Seam registry rows + coverage sentinel green. RUPTURE/UPRISING
  already cross via the W1.1 journal whitelist — verify, don't rebuild.
- **Round 2 — the instruments (frontend):**
  - *Vector lens kind* — the grammar's first extensive citizen: animated flow along projected
    gradient arcs (LineLayer/TripsLayer + PathStyleExtension, zero new deps; follow
    `criticalPulse.ts` transitions + prefers-reduced-motion convention). New `kind` touches:
    lens.ts union, mapLensLayers (LensLayerResult gains edge geometry), regionFill, registry +
    groups, MapLegend branch, DeckGLMap layer builder, colors.ts ramp.
  - *Storm markers* — RUPTURE (gap/rate payload) + UPRISING(revolutionary_pressure) as map-anchored
    cells, intensity = Mao score; hard-cut on appearance (law 2).
  - *Front lines v1* — hex-boundary strokes where neighboring `field_state` Laplacians spike /
    regime differs. (Front lines v2 from `derived_class_cell` disagreement + `side_flips`
    turbulence ride AFTER Program 19 merges.)
  - *Bifurcation gauge v1* — fixed HUD position: per-county `bifurcation_score` (already live) +
    cross-divide SOLIDARITY edge count (endgame detector already computes this predicate) +
    per-node `fascist_alignment` from Round 1. Honest label: density-based, not yet Π₀-based.
- **Round 3 — radar loop:** backend hex-history endpoint reading `v_hex_state_asof` (sparse-table
  gotcha) + the W2 class_snapshot table; type + consume the stub `inspectorTerritoryHistory`;
  frontend tick scrubber replaying any lens (one-shot fetch idiom, then scrub client-side).
- **Round 4 — forecast overlay (OWNER RULING NEEDED before build):** deterministic N-tick
  lookahead endpoint (deep-copy graph, run engine, discard — never persist), translucent future
  field + per-verb ensemble spread. Decisions: tick horizon, compute budget per request, cache
  key. Engine-adjacent; the only round with any goldens-adjacent risk surface.

## Deferred / blocked (recorded, not lost)

- **Organization gauge (hull/ghost edges):** blocked on `community_memberships` never being
  seeded — needs its own data program first. Prereq bugfix regardless: the dead
  `get_hypergraph_communities` route (500 by construction) should be fixed or removed.
- **κ terrain:** κ is never computed live. Cheapest honest path when wanted: bridge-altitude
  Ollivier-Ricci on the SOLIDARITY subgraph, computed presentation-side on topology change —
  no engine mutation, no goldens risk. Not in Wave 3 rounds.
- **g₃₃ opacity:** surface the national scalar first (cheap, honest); per-flow visibility needs
  economics wiring (`visibility_g33` is never set) — Program-10/MELT territory.
- **State's-view toggle:** greenfield (no repression doc exists); Sparrow `G_observed` is the
  seed when picked up. Post-Wave-3.
- **M/L/E simplex panel:** rides the deferred energy-labor-money research program; when it lands,
  custom-SVG ternary per the DuelSparkline/ImperialCircuitFlow no-new-deps convention.

## Owner-triage flags (discovered during verification, independent of Wave 3)

1. 🐛 `GET /api/games/{id}/hypergraph/communities/` → `bridge.get_hypergraph_communities` does
   not exist on either bridge — guaranteed 500 (`web/game/api.py:785`).
2. ⚠ `contradiction_field` naming collision (System-18 data under a System-19 name) — any new
   field serialization must not deepen it.
3. `persist_contradiction_fields(…, [], …)` hardcoded empty curvature list + forever-empty
   `edge_curvature` table (`headless_runner/bridge.py:631`).
4. `sigma`/`graphology` npm deps installed since scaffold, zero imports; typed `orgNetwork`
   endpoint has no consumer — pre-provisioned rails for a future topology view (Wave-2 backlog
   already lists get_org_network).
