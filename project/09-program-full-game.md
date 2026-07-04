# 09 — Program: Full-Game Build (MASTER PLAN, agent-executable)

**Ratified**: 2026-07-03 (Percy Raskova, BD). **Author**: Claude Fable 5,
from three deep exploration reports + a design pass, all facts verified
in-repo that day. **Status**: ACTIVE — this is the execution program for
Percy's 2026-07-03 directive. Read `00-mission.md` and
`01-state-of-the-world.md` first; this file third; then your spec.

______________________________________________________________________

## §0 Authority & end state

Percy's directive (2026-07-03, evening session), five parts:

1. Build out the **React UI and its Django components** in accordance
   with the claude.ai design chats (the canon is now staged in-repo —
   `design/mockups/`, see §5).
1. A **debug dashboard**: a GUI to analyze time-series economic data
   "and everything" straight from the simulation database, for
   development troubleshooting.
1. An **international-trade MVP built on trade blocs** (geographic
   regions with resources).
1. **Expand simulation scope to nationwide.**
1. "The desired end state is a full game, with all of the features —
   and that's what we're trying to build."

Point 5 is the frame for the other four: **the destination is the
COMPLETE GAME** — the 27-spec catalog (audit Part 3, Waves 2–7) plus the
chat-corpus surface (`07` M1–M12 mechanics + X1–X9 experience layer).
"The game works locally" (00's near goal) is a milestone on the way,
not the destination. No track in this program is an endpoint; each is a
tributary of the full game.

**Owner decisions ratified 2026-07-03 for this program** (via
AskUserQuestion, recorded verbatim in intent):

| #   | Question                  | Ruling                                                                                                               |
| --- | ------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| P1  | Sequencing vs spec-071    | **Parallel lanes** — web + data/trade lanes run alongside 071; 071 stays next on the engine lane                     |
| P2  | Debug dashboard placement | **In-app dev section** (`/observatory` route group + Django second-DB alias)                                         |
| P3  | Trade-bloc set            | **The canonical 8** external nodes already in the engine                                                             |
| P4  | Nationwide meaning        | **Sim-side first** — national res-7 validation; Michigan stays the daily gate; playable-nationwide UI follows on top |

**Execution model**: this program is written to be executed by
subagents (Claude Opus or peers) with NO access to the originating
session. Each spec below is self-contained: scope, files, dependencies,
gates. The per-spec protocol is §4. If anything here contradicts the
Constitution (`.specify/memory/constitution.md`, v2.7.0), the
Constitution wins; if it contradicts observed code, STOP and re-verify
before proceeding (this file was accurate 2026-07-03).

______________________________________________________________________

## §1 Program rulings (read before scoping any spec)

**R-MVP — the no-MVP rule and the trade "MVP".** The standing rule
(`00-mission.md` working agreements; memory `feedback_full_vision_no_mvps`)
bars MVP/Phase-1 splits of features that ALREADY HAVE a full spec. The
international layer (M9) had no spec — Percy's scoping instruction is
the act that creates its first spec set. Specs 100–103 collectively ARE
M9's first specification; they must never describe themselves as
"phase 1" or "MVP" of some larger unwritten spec. The full M9 vision
(Layer-0 background metabolism as a permanent world-system substrate)
remains the Wave-7 horizon and is reached BY these specs, not deferred
around them.

**R-AMEND — non-agentic blocs need no constitutional amendment.** `07`
§2 M9 carried "needs constitutional amendment (recursion currently
terminates at national scale)". Verified 2026-07-03: the external-node
and boundary-flow-register machinery (spec-062) is ALREADY sanctioned,
shipped constitution-clean, and persists 9 externals per tick. Blocs
that remain **non-agentic Layer-0 register-pattern machinery** (drain,
trade, exogenous scheduled shocks) require no amendment. The amendment
trigger, recorded here so nobody relitigates: **blocs become agentic
(make decisions) or recursive (grow internal hex/class structure)** —
that future spec files the amendment first.

**R-VII — Cold Collapse requires an Article VII amendment.** The
palette Percy ratified in-chat ("official babylon canon", 2026-05-17)
moves solidarity to green `#5fbf7a` and demotes gold to the scarce
`rupture #d4a02c`. Constitution Article VII currently binds
"GOLD (action/solidarity)". These conflict. spec-090 DRAFTS the Article
VII token-clause amendment (Cold Collapse set; gold→RUPTURE reserved
for revolutionary action — philosophically continuous with "gold =
action") and Percy ratifies it BEFORE the tokens land in
`web/frontend/src/index.css`. Until ratified, no production palette
change. Percy's 2026-07-03 palette ruling ("AI discretion, impress me")
delegates design judgment; it does not bypass constitutional process.

**R-CRT — texture vs chartjunk.** Constitution VII bans decorative
glow/chartjunk; the ratified canon includes CRT texture (scanlines,
grain, vignette — see `design/mockups/preview/effects-crt.html`).
Ruling: diegetic texture is permitted on **chrome** (frames, headers,
empty states, the Wire's samizdat shell) and **forbidden inside any
data-encoding surface** (chart plot areas, map fills, ramps,
sparklines) where color=meaning and luminance-monotonic ramps bind
absolutely. Playwright visual baselines pin both sides of the line.

**R-CONS — "build endpoints WITH the consumer" is satisfied, not
repealed.** `05`'s rule stands. The empty bridge dashboard methods now
have scheduled consumers: `get_journal`/`get_alerts` → 092,
`get_economy` → 093, trade sections → 103, Observatory endpoints →
096/099 (consumer = the Observatory pages, same spec). Nothing gets
built without its page; nothing waits for a page that's now scheduled.

**R-042 — spec-042 is audited, then closed as superseded.** 042
(Vic3 UI overhaul) is formally 0/49 but its artifacts partially shipped
via specs 051/061 and the course-correction. Spec-091 opens with an
evidence audit of the 49 tasks (done-with-evidence / superseded /
residual→assigned to 092/093/095). 042 is never executed as-written.

**R-SYN — the Synopticon is OUT of this program.** The in-game
state-surveillance dashboard (mockups staged at
`design/mockups/synopticon/`) hard-depends on catalog specs 078
(Repression Logic) + 079 (Panopticon Economy) for real data. Building
it now would recreate the Wayne-fixture debt this program is retiring.
It ships WITH 078/079 in Wave 3, porting the staged mockups then.

**R-NARR — the Wire ships with a deterministic narrator.** The
Workers-AI/LoRA stack (Percy's narrator ruling) is M8/Wave-6
infrastructure. Spec-094 ships the Wire on the designed
template/deterministic fallback behind a `NarratorProvider` interface;
the Workers-AI provider is a drop-in later spec. Constitution III (AI
observes, never controls) is structural: the narrator consumes the
event stream out-of-tick and writes only presentation content — it can
never touch determinism.

**R-PROOF — one open proof window at a time.** Any spec that changes
canonical dynamics re-baselines via the III.7 written-proof path
(ADR051/ADR053 precedent). The engine lane is strictly serialized;
101+102 share ONE proof window; no second dynamics-changing spec starts
while a proof window is open.

______________________________________________________________________

## §2 Spec catalog

Numbers are provisional per the first-come rule (`00`): at start time,
take the next free number in `specs/` and note this program's number in
the spec header. **071–085 stay reserved for the catalog** (taking them
corrupts every kit cross-reference); 097/098 are consumed/reserved.
Free at time of writing: 090–096, 099+. Sprint ≈ 150k tokens.

### Lane W — web product (React + Django), per design canon

______________________________________________________________________

**spec-090 — Cold Collapse design-system migration** (~1 sprint)

Replace the pre-ratification token set with the ratified canon.

- **Scope**: port `design/mockups/colors_and_type.css` (the
  "Constitution VIII — Cold Collapse" canon file) into
  `web/frontend/src/index.css` Tailwind v4 `@theme` tokens; typography
  swap to JetBrains Mono / Space Grotesk / Redaction / Departure Mono
  (self-hosted — no Google Fonts at runtime; Inter + Roboto Mono
  removed); wire the six luminance-monotonic data ramps into
  `web/frontend/src/lib/lensDefinitions.ts` + `theme/colors.ts`;
  **draft the Article VII amendment** (R-VII) as part of plan.md and
  obtain Percy's ratification before merging the token swap.
- **Files**: `web/frontend/src/index.css`, `web/frontend/index.html`,
  `web/frontend/src/theme/colors.ts`,
  `web/frontend/src/lib/lensDefinitions.ts`, font assets, plus the
  constitution amendment text (owner-ratified).
- **Deps**: none. Gates ALL other UI specs (they consume tokens).
- **TDD**: red-first Vitest token-contract test (computed custom
  properties match canon values; banned fonts absent), then migrate;
  Playwright visual baselines regenerated as the green gate and
  reviewed against `design/mockups/preview/*.html`.
- **Gate**: `mise run web:check` green;
  `rg -i 'roboto mono|inter' web/frontend/src/index.css` empty;
  amendment ratified and committed.

______________________________________________________________________

**spec-091 — Frontend consolidation + Django debt** (~1–2 sprints)

One codebase, one data path, no legacy siblings.

- **Scope**: (1) the **042 evidence audit** (R-042); (2) verify and
  finish the course-correction phases
  (`docs/agents/babylon-frontend-paradox-course-correction.md` —
  phases 4/6/7 acceptance criteria vs code; `lib/selectors/`,
  `lib/verbs/`, `BreakdownTooltip`, `VerbShell` already exist);
  (3) delete legacy siblings: `components/ActionPage.tsx`,
  `GameView.tsx`, `HexMap.tsx` (+ react-leaflet dependency),
  `IntelPage.tsx`, `OrganizationsPage.tsx`, `OrgDashboard.tsx`,
  `TimeSeriesPanel.tsx` (verify each is unrouted first);
  (4) promote the map to a first-class in-game presence (today it
  renders only via `/dev/hexmap` DevHarness — decide placement per the
  16-route architecture: persistent component on Briefing);
  (5) Django debt: `accounts` app initial migration (has NO
  migrations/ dir — `PlayerProfile` table is never created),
  `game` app `makemigrations` for pending model changes,
  `django.contrib.gis` added to `INSTALLED_APPS`
  (`web/babylon_web/settings/base.py` — engine is postgis but the app
  is absent).
- **Deps**: 090.
- **TDD**: red store/selector tests before consolidation; migration
  smoke test (`mise run web:migrate` on a fresh DB).
- **Gate**: Vitest ≥310 green; all 8 Playwright suites green;
  `rg leaflet web/frontend/src` empty;
  `poetry run pytest tests/unit/web/` green; 042 audit table committed
  and 042 marked superseded.

______________________________________________________________________

**spec-092 — Event Log + Tick Resolution surfaces** (~1–2 sprints)

- **Scope**: replace the `/games/:id/log` stub (App.tsx renders
  "coming soon") with the real Event Log page over the classified
  event stream (`lib/eventClassifier.ts` exists); build the Tick
  Resolution screen (port
  `design/mockups/ui_kits/webapp/TickResolution.jsx` +
  `EventLog.jsx`); implement `EngineBridge.get_journal` and
  `get_alerts` (today `{}` returns in `web/game/engine_bridge.py`)
  WITH these consumers.
- **Deps**: 090, 091.
- **TDD**: MSW contract tests red-first for both endpoints; backend
  pytest red-first for the bridge methods.
- **Gate**: `/log` renders live events from a seeded game
  (`seed_initial_game`); journal/alerts schemas pinned by contract
  tests; one Playwright flow: end turn → tick resolution → log entry.

______________________________________________________________________

**spec-093 — Territory Detail, Org Detail, map lens set** (~2 sprints)

- **Scope**: the two detail screens
  (`design/mockups/ui_kits/webapp/TerritoryDetail.jsx`,
  `OrgDetail.jsx`) as intel sub-routes; the Map upgrade from
  `design/mockups/themap/` — state outlines, faction-influence
  concentric rings, heat overlay, CLAIMS hulls, ColonialStance
  Blood/Blue/Phosphor encoding, lens modes, Collapse-Moment mode
  (all over spec-070 balkanization data, which is LIVE);
  `BreakdownTooltip` provenance on every displayed number; implement
  `get_economy` WITH Territory Detail's economic panel; **de-fixture
  the five hardcoded verb-target endpoints** (`get_educate_targets`,
  `get_aid_targets`, `get_mobilize_targets`, `get_attack_targets`,
  `get_reproduce_targets` in `web/game/engine_bridge.py` return Wayne
  County fixtures) with real engine queries; build the
  state→BEA-EA→county LOD *mechanism* at Michigan scope
  (`specs/040-michigan-statewide-scope` is the BEA-EA authority) —
  national framing flips on after 105.
- **Deps**: 090, 091. Constitution VIII.9 binds hyperedge rendering
  (choropleth/badges/UpSet — never pairwise fans, never spatial hulls
  on the geographic map).
- **TDD**: contract + selector tests red-first; VIII.9 rendering
  assertions in Vitest.
- **Gate**: Playwright lens-cycling suite; `get_economy` contract
  test; `rg '26163' web/game/engine_bridge.py` shows no fixture
  blocks (only real query parameters, if any).

______________________________________________________________________

**spec-094 — The Wire (4-tab window, deterministic narrator)** (~2 sprints)

- **Scope**: port `design/mockups/wire/` — the 4-tab window (WIRE
  triptych Corporate/Liberated/Intel with euphemism sync-highlight;
  WIRE INDEX; PATTERNS — the Manufacturing-Consent dashboard; CORPUS
  browser) — fed by REAL event/economy state through a
  `NarratorProvider` interface whose first implementation is the
  designed deterministic/template narrator (same events →
  byte-identical copy). Hegemony-driven visibility hooks land as
  no-op pass-throughs until spec-077 supplies the mechanic (077's
  display surface IS the Wire — `05` Wave 3). Workers-AI/LoRA
  provider is a later M8 spec (R-NARR).
- **Deps**: 090, 092 (event stream).
- **TDD**: narrator-determinism test red-first; euphemism-sync unit
  tests; MSW contracts for the wire feed endpoint.
- **Gate**: Wire renders a live 50-tick game; provider-swap test
  (interface honored); assertion that narrator output writes no
  engine state (Article III structural test).

______________________________________________________________________

**spec-095 — Endgame chronicle + Journal + Dialectic screen** (~1–2 sprints)

- **Scope**: the ruled victory-UX (chronicle end-screen + Vic3-style
  Journal objectives — `07` §1 decision 4) + Rupture/Defeat screens
  (`design/mockups/ui_kits/webapp/EndState.jsx`) + the Dialectic
  screen (`DialecticSpread.jsx`) visualizing the LIVE contradiction
  layer (ADR051: OppositionRegistry defects, `contradiction_field`
  rows, `dialectical_regime`, level lattices / Aufhebung events).
  Bridge grows a contradiction-snapshot section. NOTE: this
  partial-forwards an 081 deliverable (chronicle) — 081 later
  enriches content; flagged in §6.
- **Deps**: 090, 091, 092.
- **TDD**: contradiction-snapshot contract tests; the EndgameDetector
  priority discrepancy (docstring says REVOLUTIONARY_VICTORY-first,
  FR-033 code checks it last — `01` known non-blockers) gets its red
  test HERE since this spec is its first consumer; resolve per spec
  decision with Percy.
- **Gate**: Playwright drives a seeded game to a terminal outcome and
  asserts the chronicle renders; dialectic screen shows live
  opposition defects.

______________________________________________________________________

**spec-103 — Trade surfaces in the product UI** (~1 sprint)

- **Scope**: per the ratified trade-UI decision (blocs are background
  noise; **no interactive world map**; CONUS stays primary): Wire
  INDEX gains per-bloc price/flow lines; Territory Detail gains an
  import-exposure provenance breakdown (BabylonScriptValue over
  spec-100 weights + live `boundary_flow_register` flows); Analysis
  page gains a trade panel. Bridge trade sections built WITH these
  panels.
- **Deps**: 101 (real flows), 093 (Territory Detail), 094 (INDEX).
- **Gate**: Playwright — a county's import exposure renders with a
  drill-down provenance chain ending at reference-data citations.

### Lane O — the Observatory (Percy's debug dashboard)

______________________________________________________________________

**spec-096 — Observatory foundation** (~1–2 sprints)

The dev-facing GUI over the SIMULATION database. Heritage:
`specs/007-god-mode-dashboard` (the God-Mode wish, PyQt6 incarnation
deleted 2026-05-10); this is its web-native successor.

- **Scope**: new Django app `web/observatory/` + a second database
  alias `DATABASES["sim"]` reading the runtime Postgres (DSN from
  `BABYLON_PG_DSN`, default `localhost:5433/babylon_test` — the
  `tools/tick_probe.py` pattern). A DB router that (a) returns
  `allow_migrate=False` for the alias — the headless runner's
  idempotent migrations are the SOLE schema owner of `dynamic_*` —
  and (b) opens connections `default_transaction_read_only=on`.
  Endpoints under `/api/observatory/`: session list (from partitioned
  tables / `game_session`), tick ranges, time-series over
  `v_county_value_aggregate` / `v_state_value_aggregate` /
  `v_national_value_aggregate`, `tick_commit` chain summary
  (tick/hash/hex_rows_written/is_checkpoint), `v_hex_state_asof`
  point queries. React `/observatory` route group: lazy chunk,
  enabled by `OBSERVATORY_ENABLED` (default True in
  `settings/development.py`, False in `production.py`; precedent:
  `/dev/hexmap` DevHarness ships today). Pages: session picker,
  series browser (Recharts `TimeSeries` reuse), CSV export. Document
  the **two-DB alias map** in `web/HOW-TO-LOCAL-DEV.md` (default =
  5432/babylon product spec-037 tables; sim = 5433/babylon_test
  runner `dynamic_*`) — this split is the most confusing fact an
  incoming agent hits.
- **Deps**: none — the views/tables exist (specs 062/087–089).
- **TDD**: everything (no mockup ports): pytest against a seeded sim
  DB fixture; router tests proving migration/write refusal; MSW
  contract tests.
- **Gate**: with a live canonical run in progress
  (`mise run sim:e2e-bg`), `/observatory` plots national/state/county
  series for the session; product test suites untouched-green.

______________________________________________________________________

**spec-099 — Observatory deep panes** (~1–2 sprints)

- **Scope**: boundary-flow explorer over `boundary_flow_register`
  (DRAIN_EDGE / TRADE_EDGE / COMMUTE_OUT; ships against
  empty-state + any COMMUTE rows first — becomes Track T's human
  verification surface when 101 lands); `tick_commit` hash-chain
  verification pane (recompute/compare); conservation-audit browser
  (`conservation_audit_log`); two-session diff; **archived-session
  reading via DuckDB** over `BABYLON_ARCHIVE_ROOT` Parquet
  (layout per `tools/archive_sessions.py` + `sim:archive`), exposed
  as `source=live|archive` on the same endpoints. `duckdb` (^1.4.4)
  and `pyarrow` (^23.0.1) are ALREADY in pyproject — no new deps.
- **Deps**: 096.
- **Gate**: archive a session (`mise run sim:archive -- archive --session <id>`), then browse it read-only from `/observatory`;
  chain pane agrees with `mise run sim:probe` output.

### Lane D — data (babylon-data repo + reference schema)

______________________________________________________________________

**spec-100 — County-exposure loader (BEA I-O imports × QCEW shares)** —
**DONE 2026-07-04** (branch `100-county-exposure`; two repos)

- **Result**: `specs/100-county-exposure/` (speckit specify→plan→tasks→implement).
  Two NEW SQLite reference tables (additive to `src/babylon/reference/schema.py`):
  `fact_county_exposure_by_external` (384,200 rows = 8 blocs × ~3204 counties ×
  15 yrs) + `fact_bilateral_trade_annual` (120 rows). Loader in babylon-data
  `src/babylon_data/exposure/` (compute/writer/audit/validation/`__main__`) +
  `src/babylon_data/trade/bilateral.py`; `mise run data:exposure`. All gates
  green on the real DB: per-(bloc,year) weights sum to 1.0 (120/120),
  weight-conservation invariant ±2% (internal consistency, NOT external
  reconciliation — none exists for this measure), `logical_table_hash` reproduces
  run-to-run (H1==H2), schema-valid audit artifact. Coverage 15–21% (goods-biased
  `bridge_naics_bea` concordance → tradeable-goods import exposure; documented,
  not a stub). 38 loader tests + 7 schema tests. Zero engine-dynamics change.

- **Notes for spec-101** (in the spec's research.md): the 8 `dim_country`
  is_region blocs (EU/ATP/NA/Europe/Africa/Pacific Rim/Asia/Australia) differ
  from the engine's 8 external node_ids (canada/china/eu/…) — but the exposure
  distribution is bloc-invariant (no bloc×industry data in the DB), so spec-101
  may broadcast one map to all nodes. Trade agg is USD → feeds
  `bilateral_trade_value`, NOT `bilateral_trade_tons` (needs FAF freight, out
  of scope). `world_system_tier` is NULL for all 8 blocs by loader design.

- **Scope**: build the never-computed `county_exposure_by_external`
  weight map — the exact formula named in
  `src/babylon/engine/systems/phi_distribution.py`'s docstring: per
  external bloc, county weights from `fact_bea_io_coefficient`
  import coefficients × QCEW county industry shares. Persist as a
  new reference table (SQLAlchemy class added to
  `src/babylon/reference/schema.py`; loader + audit live in
  babylon-data per the 086 pattern: staged rebuild, atomic swap,
  audit contract, `logical_table_hash`). Also: bloc-year
  `bilateral_trade_tons` aggregation from `fact_trade_monthly`
  (44,808 rows, loaded; babylon-data has a `trade/` module to
  extend). The 8 blocs key to `dim_country` rows with `is_region=1`
  (+ `world_system_tier` core/semi_periphery/periphery). USGS
  minerals ("regions with resources" — `fact_state_minerals`,
  `fact_mineral_production`, `dim_import_source` all exist at 0
  rows) is a FLAGGED STRETCH, not folded in (§6).

- **Files**: babylon-data `src/babylon_data/exposure/` (new),
  `src/babylon/reference/schema.py` (additive),
  `.mise.toml` (`data:exposure` task).

- **Deps**: none. Zero engine-dynamics change, zero baseline churn.

- **TDD**: 086's fixture pattern (CSV builders, in-memory ORM
  seeding); weight-conservation invariant ±2% (Σ raw exposure vs Σ covered
  BEA import coefficient — an INTERNAL consistency invariant, since no
  independent published import total exists in the DB for this measure;
  corrected from the original "reconciliation against published totals"
  wording per the spec-100 adversarial review).

- **Gate**: `mise run data:exposure` green with audit artifact;
  per-bloc weights sum to 1.0; table hash reproduces run-to-run.

______________________________________________________________________

**098-LODES slice — hex-level OD matrix** (existing program `04`, prioritized; ~1–2 sprints)

- **Scope**: FIRST slice of the spec-098 loader-rebuild program:
  finish `babylon-data src/babylon_data/lodes/loader_od.py` (exists;
  `mise run data:lodes-od` exists, Michigan default) so
  `immutable_reference_lodes_od_matrix` hydrates (Michigan first,
  then national). Clears the ~34 `tests/integration/economics/`
  NoDataSentinel failures; unblocks the Vol-II COMMUTE_OUT emission
  path. Executes under `project/04-data-program-098.md` governance —
  no new spec number.
- **Gate**: NoDataSentinel count in that suite → 0 (Michigan scope);
  commute-emission integration test green at tri-county.

______________________________________________________________________

**068 completion slice — BEA national I-O** (≤1 sprint)

- **Scope**: reopen `specs/068-bea-national-io-ingest/` (~60/77
  done): finish remaining tasks incl. the deferred hex_hydrator
  wiring T056–T058 so the Leontief per-county rent path serves
  `--scope=national` without fallback.
- **Gate**: 068 tasks.md fully checked; hydrator integration test at
  national scope.

### Lane E — engine (serialized; baseline authority)

______________________________________________________________________

**spec-071 — Reactionary Subject** — **IMPLEMENTED 2026-07-04 (ADR054), in review**

Per `03-next-spec-071.md`. First in the lane; both foundations
(ADR051 dialectics, ADR052 substrate) landed 2026-07-03. Branch
`071-reactionary-subject`. FascistFactionSystem @17.4
(pipeline 25→26); entitlement/volatility/fascist_alignment/aligned_faction_id
on SocialClass; chauvinism/defection/RED_BROWN_COUP; L_u SPONTANEOUS_RIOT;
POGROM/LOCKOUT/VIGILANTISM OODA verbs; carceral create-on-demand; RLF
simplex helpers; ReactionaryDefines. **Proof window CLOSED byte-identical**
(tri-county 5-tick gate total_v Δ=0.000%, liveness 3/3 — the always-on
system is dormant during the pacified decade, agitation crisis-gated), so no
re-baseline was required. Canonical 520-tick relaunched at close-out.
101 may open once the BD merges. Awaiting BD merge to dev.

______________________________________________________________________

**spec-101 — Trade activation: boundary flows live** (~1–2 sprints)

> **STATUS: CODE DONE 2026-07-04** (branch `101-trade-activation`, ADR055,
> unmerged; opens the shared 101+102 proof window). Boundary flows populate
> every tick. **Deviation from scope (repo-verified, program §0 "repo wins")**:
> (a) the hydrated external nodes carried Φ=0 (Hickel is a single national
> aggregate, no per-bloc resolution), so spec-101 ATTRIBUTES the national Φ to
> blocs by bilateral-trade share via an injective node→bloc crosswalk — **#1
> owner-review item**; (b) `vol2_step` TRADE_EDGE is NOT wired — it is
> inseparable from COMMUTE_OUT and both need LODES (098-LODES), and the program
> directs COMMUTE_OUT stays gated; (c) `bilateral_trade_value` (not `_tons`)
> populated per spec-100 R8. Conservation `Σ DRAIN_EDGE ≡ Φ_week` per bloc gated
> (relative residual; migration 0031). See `specs/101-trade-activation/`.

- **Scope**: populate the dormant TickContext keys in the runner
  tick loop. Verified state 2026-07-03: `runner.py:311` builds
  `TickContext(tick=tick)` only, while
  `src/babylon/engine/systems/economic.py`
  `_invoke_phi_distribution_if_wired` (lines ~103–151) silently
  no-ops without `boundary_flow_register`, `session_id`,
  `external_nodes_phi`, `county_exposure_by_external` — and the
  `BoundaryFlowRegister` is ALREADY constructed at `runner.py:603`
  as `services.boundary_register`. Wire: session_id + register into
  context; `external_nodes_phi` from the hydrated external nodes
  (Hickel `phi_year_inflow`); `county_exposure_by_external` loaded
  from spec-100's table; `vol2_step` TRADE_EDGE path on
  (COMMUTE_OUT stays gated until 098-LODES). Populate
  `bilateral_trade_tons` on external-node rows (hardcoded 0.0
  today) from spec-100 data. Extend the conservation auditor:
  Σ DRAIN_EDGE credits ≡ Φ_week inflow per bloc within epsilon.
- **Files**: `src/babylon/engine/headless_runner/runner.py`,
  `src/babylon/persistence/postgres_initialization.py`,
  `src/babylon/persistence/external_node.py`, conservation audit,
  new `tests/integration/` trade-circuit suite.
- **Deps**: 100 (S1). Engine lane: starts only after 071's proof
  window closes.
- **TDD**: red integration test asserting per-tick DRAIN_EDGE rows
  for all 8 blocs with nonzero Φ + conservation identity — observe
  today's silent-no-op RED first, then wire.
- **Gate**: `boundary_flow_register` populates every tick;
  `mise run qa:e2e-regression` green against the NEW proven
  baseline (shared window with 102); canonical
  `mise run sim:e2e-bg` passes liveness 83/83.

______________________________________________________________________

**spec-102 — Gamma hydration + scheduled bloc shocks** (~1–2 sprints, same proof window as 101)

- **Scope**: kill the hardcoded seam in
  `src/babylon/economics/melt/basket_visibility.py` (lines ~24–26:
  import share α≈0.25, γ_import≈0.35, placeholder γ_basket=0.68) —
  the `get_gamma_basket(year, alpha, gamma_import)` API is already
  parameterized; hydrate per-year α and trade-weighted γ_import from
  spec-100 exposure + `fact_hickel_erdi_annual` (satisfies III.1
  no-magic-numbers). Add **exogenous scheduled bloc shocks**:
  scenario-config declares (tick, bloc, φ/trade multiplier) events;
  deterministic (no RNG), applied to external-node inputs. Blocs stay
  non-agentic (R-AMEND).
- **Deps**: 100, 101.
- **TDD**: red test that hydrated runs return
  `is_mvp_fallback=False`; shock determinism test (same config twice
  → identical `tick_commit` hash chain).
- **Gate**: ONE canonical re-baseline covers 101+102 (R-PROOF;
  ADR053 program-branch precedent); a shock scenario visibly bends
  the Φ trajectory in the Observatory.

______________________________________________________________________

**spec-104 — National tick-compute profile + budget** (~1–2 sprints)

- **Scope**: the first national-scale COMPUTE measurement
  (persistence side is known: 3.17M-hex checkpoint frame = 629 MiB
  @ 54 s; nothing measures the tick loop at 3,156 counties).
  Run `--scope=national` ~20 ticks under `mise run sim:profile`;
  produce a per-system wallclock budget table
  (`PerformanceBreakdown.per_system_ms` exists in
  `headless_runner/models.py` but is empty — wire it); fix top
  hotspots; add a `qa:tick-budget` gate vs a ratified budget
  (number set AFTER first measurement — §6). Close the
  DecompositionSystem carceral-enforcer no-op
  (`02-engine-truths.md` §on enforcers) required for long crisis
  runs.
- **Deps**: 098-LODES (commute on), 101/102 preferably merged so the
  profile includes trade.
- **Constraint**: pure-perf refactors keep determinism hashes
  byte-identical; anything reordering float math takes the
  written-proof path (R-PROOF).
- **Gate**: national 20-tick run inside budget; tri-county hash
  unchanged (or proven).

______________________________________________________________________

**spec-105 — National canonical acceptance** (~1–2 sprints, mostly runtime)

- **Scope**: the nationwide milestone (P4): a multi-hundred-tick
  detached `--scope=national` run (~3,156 counties + blocs) on the
  full storage stack (delta persistence, partitioning, budget gate);
  storage verified inside the 6.8–22.7 GiB projection; liveness
  gates generalized from the Michigan-constant 83
  (`counties_with_population == counties_alive == N_scope`);
  **the Observatory is the verification surface** (096/099 pay for
  themselves here); archive via `mise run sim:archive` on
  completion; commit the national baseline bundle (`--no-verify`
  artifact precedent).
- **Deps**: 098-LODES, 068-completion, 104, 101/102, 096.
- **Gate**: bundle + `qa:storage-budget` green + Observatory
  renders the full run; THEN 093's national map framing flips on.

______________________________________________________________________

### Catalog continuation (unchanged authority)

After 071 (and the trade window), Lane E continues the catalog per
`05`: Wave 2 (072–074) → Wave 3 (075–079 + M1 slime-mold + M2/M3
verb-input + X2 Wire-hegemony + Synopticon w/ 078/079) → Waves 4–7.
This program does not reorder the catalog; it runs beside it and
feeds it (092–095 build the surfaces Wave-3 specs animate).

______________________________________________________________________

## §3 Lanes, dependency graph, kickoff

### Lane definitions + file ownership (collision law)

| Lane              | Specs (order)                             | Owns (writes)                                                                                            | Never touches                         |
| ----------------- | ----------------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| **E** engine      | 071 → 101 → 102 → 104 → 105               | `src/babylon/**`, `tests/`, baselines                                                                    | `web/**`                              |
| **W** web         | 090 → 091 → {092 ∥ 093} → 094 → 095 → 103 | `web/**` (product), `design/mockups` READ-ONLY                                                           | `src/babylon/**`                      |
| **D** data        | 100 ∥ 098-LODES ∥ 068-slice               | babylon-data repo; `src/babylon/reference/schema.py` (additive only)                                     | engine systems, `web/**`              |
| **O** observatory | 096 → 099                                 | `web/observatory/**`, `web/frontend/src/observatory/**`, ONE route line in `App.tsx`, settings additions | `web/game/**` logic, `src/babylon/**` |

Shared hot file: `web/game/engine_bridge.py` — Lane W only, and W's
specs are already serialized. Lane O deliberately BYPASSES the bridge
(raw read-only queries against runner-owned tables). `App.tsx` single
route-line overlap between W and O merges trivially.

### Kickoff (P1 ruling: parallel lanes)

Start concurrently, four agents:

```text
[E: 071]   [W: 090 → 091]   [D: 100 ∥ 098-LODES]   [O: 096]
```

### Sync points

- **S1**: 100 merges → 101 may start (needs the exposure table).
- **S2**: 101+102 merge under ONE proof window → 103 (trade UI) and
  099's flow pane get real flows.
- **S3**: 098-LODES merges → COMMUTE emission testable → 104 profiles
  the full pipeline; ~34 integration failures clear.
- **S4**: 104 + trade merged → 105 national acceptance → 093's
  national framing enabled.
- **S5**: 092 (event stream endpoints) → 094 (Wire consumes).
- **S6**: (done 2026-07-03) mockups staged at `design/mockups/`.

### Branching

Per-spec branches off `dev` (`feature/090-cold-collapse`, etc.), PR to
`dev`; BD merges. Never commit to `dev`/`main` directly. Engine-lane
specs that open a proof window keep ONE program branch until the
window closes (ADR053 precedent: 087–089 landed as one branch).

______________________________________________________________________

## §4 Per-spec execution protocol (for the implementing agent)

1. **Bootstrap read** (in order): `project/00-mission.md`,
   `project/01-state-of-the-world.md`, THIS FILE (§0–§3 + your spec's
   entry), then your lane's context docs:
   W → `docs/agents/babylon-frontend-reset-prompt.md` +
   `docs/agents/babylon-frontend-paradox-course-correction.md` +
   `design/mockups/PROVENANCE.md`;
   E → `project/02-engine-truths.md` + `project/08-graph-substrate.md`;
   D → `project/04-data-program-098.md`;
   O → `web/HOW-TO-LOCAL-DEV.md` + `tools/tick_probe.py`.
1. **Take the next free spec number** in `specs/` (071–085 reserved);
   note this program's provisional number in the spec header.
1. **Speckit lifecycle**: `specify → plan → tasks → implement`.
   plan.md includes the Constitution gate checklist (v2.7.0: III.1
   no-magic-numbers, III.7 determinism/frozen models, III.8
   data-grounding, II.11, II.12 authoring API, I.20, IV; Amendment K
   dialectics + L rustworkx bind engine work; Article VII/VIII.9 bind
   UI work).
1. **TDD is mandatory** (Red → Green → Refactor; `@pytest.mark.red_phase`
   for intentional-fail commits). For mockup ports the DESIGN comes
   from `design/mockups/` but the CODE is written fresh against
   contract tests — mockups are reference, not source (they're
   standalone JSX/HTML, not project code).
1. **Dynamics changes** (engine lane): follow R-PROOF. Byte-identity
   check first (`mise run qa:e2e-regression`); if outputs move, write
   the proof (what changed, why it's correct, magnitude), regenerate
   baselines, commit proof + baselines together (ADR051/052/053
   precedent).
1. **Commit discipline**: conventional commits after each unit via
   `mise run commit -- "type(scope): msg"` (hook-safe: pre-runs hooks,
   re-stages fixes, verifies HEAD moved). Artifacts (baselines,
   bundles, canon files) use `--no-verify` per precedent.
1. **Storage hygiene**: after every canonical run,
   `mise run sim:archive -- archive --session <id>` (or `--all`).
   Never leave finished sessions hot. `mise run sim:status` to watch.
1. **Verification loop** (every engine-touching spec):
   `mise run check` →
   `poetry run pytest tests/integration/test_bridge_income_circuit.py -q` →
   `mise run qa:e2e-regression`; before merging dynamics changes:
   `mise run sim:e2e-bg` + liveness check. Web specs:
   `mise run web:check` + Playwright suites.
1. **Close-out**: update `project/01-state-of-the-world.md` (status),
   this file's §2 entry (mark DONE + actual spec number),
   `ai-docs/state.yaml`; ADR if an architectural decision was made;
   owner-review items go to Percy — do not merge to dev yourself.

______________________________________________________________________

## §5 Design-canon mockups (staged 2026-07-03)

`design/mockups/` — 66 files, 643 KiB, extracted from
`/home/user/projects/claude-chats/design_chats/` by chronological
replay of `write_file`/`str_replace_edit`/`delete_file` tool-call
payloads across the 7 core design chats (global message-timestamp
order; platform-errored calls skipped). Full recipe + fidelity caveats:
`design/mockups/PROVENANCE.md`; per-file source chat + last-write
timestamp: `design/mockups/manifest.json`.

| Path                         | What it is                                                                                                                                                                                   | Consumed by                                  |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| `colors_and_type.css`        | THE canon: "Constitution VIII — Cold Collapse" tokens + type stack                                                                                                                           | 090                                          |
| `preview/*.html` (17 files)  | Token sheets, ramps, component previews, CRT effects, type specimens                                                                                                                         | 090 (visual reference)                       |
| `ui_kits/webapp/` (15 files) | The 13-screen mock-game kit (Login → GameList → Briefing → GameShell → Action → TerritoryDetail → OrgDetail → Topology → TickResolution → EventLog → DialecticSpread → EndState) + mock-data | 091–095                                      |
| `themap/` (4 files)          | The Map: CONUS, influence rings, CLAIMS hulls, stance encoding, lenses, Collapse-Moment                                                                                                      | 093                                          |
| `wire/` (9 files)            | The Wire 4-tab window (triptych, INDEX, PATTERNS, CORPUS)                                                                                                                                    | 094, 103                                     |
| `synopticon/` (9 files)      | State-surveillance dashboard (PANOPTICON/DOSSIERS/GOSPEL/DOCTRINE)                                                                                                                           | Wave-3 w/ 078/079 (R-SYN — NOT this program) |
| `community/` (9 files)       | Hypergraph views: choropleth, UpSet, BubbleSets topology, co-occurrence matrix, inspector                                                                                                    | 093/095 + Wave-3                             |

Design decisions of record (mined + verified 2026-07-03): Cold
Collapse ratified ("official babylon canon") — supersedes `07` §1's
"may be drift" caveat; typography JetBrains Mono / Space Grotesk /
Redaction / Departure Mono (Inter + Roboto Mono rejected); multi-page
16-route architecture (god-page banned); trade UI = background noise,
no world map; map hierarchy CONUS → BEA Economic Areas (~300) →
counties; Paradox provenance-breakdown tooltips everywhere.

______________________________________________________________________

## §6 Open items for Percy (owner decisions, not blockers to kickoff)

1. **Article VII amendment** (R-VII): ratify the Cold Collapse token
   clause when spec-090 presents it. Until then the product keeps the
   old palette.
1. **DB convergence**: retire the separate product Postgres
   (5432/babylon) into the compose-managed PG16 instance as a second
   database? Attractive under the single-Postgres ruling; OUT of this
   program's scope; needs an owner call + migration spec.
1. **095 partial-forward**: the chronicle end-screen is formally an
   081 (Warlord) deliverable; 095 builds the surface early against
   the 5-outcome enum. Confirm or re-scope at 095's plan gate.
1. **National tick budget**: ratify the `qa:tick-budget` number after
   104's first measurement (do not guess one now).
1. **USGS minerals stretch** ("regions with resources"): the resource
   tables exist empty; loading USGS MCS is a 098-family slice. Say
   the word and it slots into Lane D after 100.
1. **EndgameDetector priority**: docstring vs FR-033 order — 095
   forces the decision; pick doc or code.

______________________________________________________________________

*This program was authored under Percy's 2026-07-03 directive to spend
Fable-5 context on a plan precise enough for other models to execute.
When a fact here disagrees with the repo, the repo has moved: verify,
update this file, keep going.*
