# Babylon Frontend Course-Correction Prompt

## Purpose

This prompt exists because the current frontend implementation collapsed the agreed-upon multi-page architecture into a single god-page "War Room" — the exact anti-pattern that was explicitly rejected across the March and April 2026 design discussions. This document re-establishes the vision, names what went wrong, and gives a concrete extraction path back to the plan.

Hand this to any Claude instance (or a developer) picking up the frontend work. Do not deviate from the structure below without an explicit architectural conversation.

______________________________________________________________________

## Project Context (minimum viable)

Babylon is a Marxist-Leninist-Maoist Third Worldist political simulation of imperial collapse, calibrated against federal statistical data (QCEW, BEA, Census, FRED), validated on Metro Detroit as a test case. It is simultaneously a falsifiable scientific model and a turn-based strategy game.

The application is a Django + Postgres + Gunicorn server with a React client. The simulation runs server-side; the React app is a presentation layer, never a computation layer. NetworkX handles dyadic graphs (value flow, solidarity, repression); XGI handles n-ary hyperedges (community membership — NEW_AFRIKAN, SETTLER, WOMEN, INCARCERATED, etc.). The two graph layers stay architecturally separate.

Player acts through Organizations (not individuals, not demographic blocks). Nine player verbs — Educate, Aid, Attack, Mobilize, Campaign, Move, Investigate, Reproduce, Negotiate — each mapping to exactly one graph operation per tick.

The full project context lives in the Constitution (nine articles, versioned, authoritative). The Constitution overrides everything in this document if they conflict.

______________________________________________________________________

## The Vision: 16 Pages, Not One War Room

The frontend is a **multi-page React Router application**, not a single-page dashboard. This was settled in the March 7 and April 2 conversations and elaborated April 6 and April 10.

### Route inventory

**Pre-game (2 routes)**

1. `/login` — Auth only. No game chrome, no visualization libraries loaded.
1. `/games` — Lobby. List of sessions (active, paused, completed). New Game with scenario selection. Simple list page; fast, low-memory.

**Core game loop (4 routes)**

3. `/games/:id` — **Briefing.** The "newspaper" landing page after tick resolution. Narrative text, NPC actions summary, events, consciousness shifts. This is the first thing opened each turn.
1. `/games/:id/orgs` — **Organizations.** Player's orgs with OODA state, budget, cohesion, membership, edge relationships as categorical badges. The 3×3 verb grid lives here as navigation links. "End Turn" button.
1. `/games/:id/intel/:target_type/:target_id` — **Intel/Inspector.** Context-sensitive detail for a clicked entity (territory, org, edge, community). This is where enemy orgs (State Apparatus, reactionary factions) show up — never in the player's own org dashboard.
1. `/games/:id/results` — **Results.** Mechanical detail of tick resolution (distinct from Briefing's narrative framing).

**Verb pages (9 routes)**

7. `/games/:id/actions/educate` — target: community hyperedge
1. `/games/:id/actions/aid` — target: org or territory
1. `/games/:id/actions/attack` — target: org or territory
1. `/games/:id/actions/mobilize` — target: community hyperedge
1. `/games/:id/actions/campaign` — target: territory or community
1. `/games/:id/actions/move` — target: territory
1. `/games/:id/actions/investigate` — target: org, edge, or territory
1. `/games/:id/actions/reproduce` — target: org (organizational reproduction)
1. `/games/:id/actions/negotiate` — target: org

Each verb page has its own target type, its own form, its own API endpoint, its own mock fixture, its own contract parity test. **The target list is not a single dropdown of all possible targets** — it is gated by the verb's target type. Conflating them collapses the dyadic/n-ary distinction the dual-graph architecture depends on.

**Analysis / narrative (post-MVP, 2 routes)**

16. `/games/:id/analysis` — Full-screen analytics workspace. Full-size time series (not sparklines), UpSet intersection plot at readable size, tick scrubber with proper timeline. Read-only; no action composer.

(The "FBI file" narrative page at `/games/:id/narrative` is the 17th, listed as post-MVP.)

### Why multi-page, not SPA panels

The lobby doesn't need a hex map loaded. The analysis view doesn't need the action composer. The login screen needs none of it. Different pages have different data requirements, different cognitive modes, different performance envelopes. Code-splitting per route keeps initial load fast and keeps each page's data contract tight.

Within `/games/:id` (the Briefing and the verb pages), the map/graph/inspector stay synchronized through a shared Zustand store. **Synchronization is not monolithic layout.** The map component is a shared, persistent React component that renders on whichever page currently includes it — it is not the entire application.

______________________________________________________________________

## What Went Wrong

The current implementation (screenshot dated April 16, 2026) is a single-route god-page with:

- All 9 verbs crammed into a right-rail accordion under invented tabs ("BUILD ORG / PROJECT PWR / MANAGE RES") that don't match the constitution's verb taxonomy.
- A single target list showing only hyperedges, regardless of which verb is selected — wrong for Move, Aid, Attack, Negotiate, Investigate.
- A full Organization dashboard in the same right rail, listing enemy orgs (State Apparatus, Detroit Finance Bloc, Settler Militia) alongside the player's own orgs. Enemy orgs belong in Intel, not in the player's action-taking surface.
- A mini org-network graph in the left panel that duplicates the right rail's org list.
- A bottom panel with three full-size time series simultaneously — that was supposed to be the `/analysis` page.
- Two competing framing selectors: LAYER (Heat/Consciousness/Wealth/Rent/Biocapacity/Population) at the top of the map and LENS (Economic/Political/Social/Strategic) at the bottom. Layer is a gameplay-mode concept; Lens is an analysis-mode concept. They should not both exist on the same page.
- An "AVG ORGANIZATION 0.50" metric in the top bar, averaging an attribute that doesn't meaningfully average across discrete organization agents.

This is the exact "War Room as god-page" pattern the April 6 conversation rejected. The decomposition discipline ("build each component as its own page with its own route, its own API endpoint, its own mock fixture, its own contract parity test — then compose them into the War Room layout after all contracts are proven") was not followed.

______________________________________________________________________

## Constitution Non-Negotiables (do not regress)

These are copied from the Constitution and cannot be amended without formal process.

**Article III — AI Observes, Never Controls.** The LLM layer generates narrative FROM state changes. It never determines mechanical outcomes. Any frontend feature that lets the player write prose directly into tick inputs must go through a server-side parse step that produces a frozen, schema-validated vector; ticks remain deterministic and replayable.

**Article IV — Dual Graph Architecture.** NetworkX for dyadic relationships, XGI for hyperedges. The frontend must not collapse these into a single target picker. Hyperedges are first-class targets for Educate/Mobilize/Campaign. Orgs and territories are first-class targets for Aid/Attack/Move/Negotiate. Investigate can take either, but the UI must disambiguate.

**Article V — Action Vocabulary.** Nine player verbs, atomic, one graph mutation per tick per organization. All nine always available; the UI models consequences, never restricts choices. No invented verb categories or phase-gated tabs.

**Article VII — Visual Design.**

- Color encodes meaning (class, extraction, edge type, state), not mood.
- Luminosity encodes magnitude.
- No decorative glow, no chartjunk, no legends-in-corners when direct annotation is possible.
- CRIMSON/SAFFRON/GREY/BLACK palette is binding for semantic core; extended palette allowed for cartography.

**Article VIII.9 — Community membership is a hyperedge.** Do not render it as pairwise edges between an org and every member of a community. Do not render it as a spatial hull on the map (hypergraphs aren't spatial). Render as choropleth on hexes by dominant composition, badges on inspector panels, UpSet plots for intersection analysis.

**Anti-Pattern: God-page.** Seven-plus components needing different data, all cross-linked, in one route. The War Room is a *composition* of proven-contract components, not a starting point.

______________________________________________________________________

## Extraction Plan (ordered, concrete)

Do these in order. Do not skip ahead. Each step produces a working page with its own contract; composition comes last.

**Step 1 — Extract the Organizations page.**
Move the org dashboard to `/games/:id/orgs`. Include only player-controlled orgs. Enemy orgs get removed entirely from this surface — they reappear in Intel. Endpoint: `GET /api/games/{id}/organizations/?player_only=true`. Mock fixture with 3 player orgs. Contract parity test: page renders from mock, matches API schema.

**Step 2 — Extract one verb page as the template.**
Pick Educate (simplest target type: community hyperedge). Create `/games/:id/actions/educate`. Target selector shows only community hyperedges with membership-overlap dropdown. Endpoint: `GET /api/games/{id}/verbs/educate/targets/?org_id=...`. Submit: `POST /api/games/{id}/actions/` with `{verb: "educate", target_id, params}`. Mock fixture, contract parity test. This becomes the template for the other eight.

**Step 3 — Replicate for the other eight verbs.**
Each gets its own route, its own target type, its own form schema, its own fixture. Resist the urge to generalize prematurely — nine simple pages beat one complex conditional UI.

**Step 4 — Extract Intel.**
Move all enemy-org detail, edge detail, territory detail, community detail to `/games/:id/intel/:target_type/:target_id`. This is where "click a hex on the map" navigates to. Remove the inline inspector popup on the map; the popup becomes a click-through.

**Step 5 — Strip the Briefing route.**
What remains at `/games/:id` is: the map (persistent component, H3 layer with ONE framing selector — either Layer or Lens, pick one), a sparkline strip (three small charts, not full-size), the tick narrative text, and "End Turn" nav to the verb pages. No org dashboard. No full-size time series. No verb accordion.

**Step 6 — Defer Analysis.**
`/games/:id/analysis` gets the full-size time series, the UpSet plot, the scrubber. This is post-MVP. Do not build it into the Briefing page.

**Step 7 — Compose the War Room layout (optional, last).**
Only after all contracts are proven — all fixtures render, all parity tests pass — consider whether to compose some routes into a side-by-side layout for power users. This is an optimization, not a starting point. If you can't articulate which contracts the composition depends on, you aren't ready to compose.

______________________________________________________________________

## Evaluation Criteria (drift detection)

After any frontend change, ask:

- Did this add a new concept to an existing route, or did it go to its own route? (New concepts → new routes, default.)
- Does any route now have more than three primary components? (If yes, decompose.)
- Does the verb picker show targets of different types in a single list? (If yes, the target-type gating is broken.)
- Do enemy orgs appear anywhere the player is selecting an actor-org? (If yes, cut them out.)
- Is there more than one framing/lens/layer selector visible at once? (If yes, one of them belongs on a different route.)
- Is the LLM on the hot path of tick resolution? (If yes, stop — Article III violation.)
- Is a hyperedge being rendered as pairwise edges or a spatial hull? (If yes, Article VIII.9 violation.)

Any "yes" is a stop-work condition. Name the violation, cite the article, propose the fix.

______________________________________________________________________

## Style Notes for the Implementer

- Use React Router's `createBrowserRouter` with lazy-loaded route components for code splitting.
- Zustand stores stay at three: game (server-authoritative, replaced wholesale per tick), UI (ephemeral client state), map (deck.gl viewport).
- Tailwind theme tokens map to constitution palette; semantic CSS custom properties consumed by both Tailwind and viz libraries.
- Cytoscape.js for graph views (dyadic + BubbleSets for hyperedge hulls in topological mode). deck.gl + MapLibre for geographic views. Don't mix.
- Contract parity tests compare frontend mock fixtures against live API schema — if they drift, CI fails.

______________________________________________________________________

## Open Questions

These are not blockers but will need resolution:

- Does the Investigate verb get one page with a target-type selector, or three sub-routes (investigate-org, investigate-edge, investigate-territory)? Leaning toward one page with a discriminator.
- Does the War Room composition (Step 7) actually ship, or does the multi-page structure remain the whole UX? Decide after verbs 1–9 are done.
- Where does the AI-generated narrative display — inline on Briefing, or its own `/narrative` route? April 2 discussion left this unresolved.
- Keyboard navigation: does `g` + verb-initial jump to a verb page? Mobile responsiveness?

These get answered with data from playtesting, not architectural speculation.

______________________________________________________________________

*End of prompt. The Constitution is the authority where this document is silent.*
