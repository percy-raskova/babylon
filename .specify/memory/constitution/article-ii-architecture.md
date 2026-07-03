# Article II: Architecture Principles

> Annex to [Babylon Constitution](../constitution.md). This file contains the full rationale, examples, and implementation details for each architecture principle.

### 1. Four-Node Recursive Pattern

The fundamental unit: {Core, Periphery} × {Bourgeoisie, Proletariat} = 4 nodes.

This pattern instantiates at ANY resolution level (fractal architecture):

- Global: Core nations vs Periphery nations
- National: Core (settler) vs internal colonies (New Afrika, First Nations, Chicano, etc.)
- Metropolitan: Gentrifying areas vs displacement zones
- Workplace: Management vs labor

The Core unfolds via fractal zoom into internal nations. Resolution determines which four-node pattern is active.

### 2. Primitives vs Derived

**Primitives** (stored, not computed):

- Concrete labor time (integer hours, typed by sector)
- Physical substrate (UseValues)
- Biological reproduction requirements
- Reproductive labor hours
- Social topology (the graph itself)

**Derived** (computed from ledger queries over ProductionEvents):

- SNLT (socially necessary labor time)
- Value, c (constant capital), v (variable capital), s (surplus value)
- Imperial rent (Φ)
- Profit rate (r)
- Exploitation rate (s/v)
- Organic composition of capital (OCC = c/v)

**Rule**: NEVER store derived quantities. Always recompute from primitives.

### 3. Graph as Discretized Manifold (rustworkx)

The graph is not merely a data structure—it is the discretized manifold on which fields propagate. Tensors are field values on nodes/edges.

Class position is derivable from:

1. The Reproduction Tensor (V_produced − V_reproduction balance)
1. Topological position in value chains (distance from extraction, proximity to realization)

The graph's connectivity determines information flow (consciousness transmission) and value flow (exploitation chains).

### 4. Quantities vs Coefficients

| Category         | Behavior                         | Examples                                        |
| ---------------- | -------------------------------- | ----------------------------------------------- |
| **Quantities**   | Flux per tick                    | Labor hours, production events, value transfers |
| **Coefficients** | Transform slowly via α-smoothing | Extraction efficiency, wage share, OCC          |

Coefficient update rates MUST derive empirically from autocorrelation in historical data.

**Crisis Definition**: A discontinuous coefficient reset (capital devaluation) when r < threshold. Crisis is NOT gradual coefficient drift—it is a phase transition.

### 5. AI Observes, Never Controls

The AI (LLM) layer generates narrative FROM state changes. It never determines mechanical outcomes.

**Separation of Concerns**:

- **Mechanics** (deterministic): Formulas, Systems, state transitions
- **Narrative** (generative): AI describes what happened, provides context, voices characters

**Implementation Requirements**:

1. **State changes are calculated, then narrated.** The engine computes `new_state = step(old_state)`. Only after this computation does the AI receive `(old_state, new_state)` for narrative generation.

1. **AI has read-only access.** The NarrativeDirector implements SimulationObserver—it receives state deltas but cannot modify them.

1. **Reproducibility is paramount.** Given identical inputs and random seeds, the simulation MUST produce identical outputs regardless of AI narrative content.

1. **AI failure is non-fatal.** If the LLM fails, times out, or produces garbage, the simulation continues. Narrative is optional; mechanics are not.

**Rationale**: Letting AI control mechanics makes the simulation non-deterministic, untestable, and unverifiable. The horror of the system is revealed through SHOWING what the math produces, not through AI-generated drama.

**See Also**: Article VII (Visual Design Principles) extends this observer pattern to the UI layer.

### 6. State is Data, Engine is Transformation

WorldState contains only data (Pydantic models). Engine contains only functions that transform state. They never mix.

**WorldState** (pure data):

- Immutable (frozen Pydantic model)
- Contains entities, relationships, tick count, events
- No methods that modify self
- All "changes" produce new instances via `model_copy(update={...})`

**Engine** (pure transformation):

- `step(state: WorldState, config: SimulationConfig) -> WorldState`
- Systems receive graph, mutate in place, return nothing
- No state stored in engine classes
- No business logic in data classes

**The Hydration Pattern**:

```
SQLite (cold) → hydrate → WorldState (warm) → to_graph → rustworkx (hot)
                                                              ↓
                                                         [Systems mutate]
                                                              ↓
SQLite (cold) ← dehydrate ← WorldState (warm) ← from_graph ← rustworkx (hot)
```

**Implementation Requirement**: NO database I/O during tick execution. The simulation runs entirely in RAM. Persistence happens before and after, never during.

**Rationale**: This separation enables deterministic testing, easy serialization, and clear reasoning about state transitions. When state and behavior are mixed, bugs hide in the interaction.

### 7. Edges vs Hyperedges (rustworkx + XGI)

The simulation uses two complementary graph structures. The decision rule is categorical:

- **If value, solidarity, or repression flows between two entities** → rustworkx edge
- **If multiple entities share membership in something** → XGI hyperedge

**rustworkx edges** (dyadic flows): Value extraction, solidarity transmission, repression, wages, tribute, tenancy, adjacency. These are directional relationships between exactly two entities. One entity acts on another. Edge modes (I.6) and contradiction internals (I.14) live here.

**XGI hyperedges** (n-ary membership): Community, identity category, organizational affiliation, shared designation. These are collective structures that agents belong to. A community is not a relationship between agents — it is a thing agents are part of. The FBI does not surveil individuals who happen to share attributes; it targets communities as units (COINTELPRO).

**The Distinction Is Ontological, Not Technical**:

| Relationship Type | Structure | Library | Example |
| ----------------------------------- | --------- | --------- | ------------------------------------ |
| A extracts value from B | Edge | rustworkx | Oakland County ← Wayne County |
| A and B share mutual aid | Edge | rustworkx | SOLIDARISTIC edge between nodes |
| A, B, C belong to community X | Hyperedge | XGI | Black church membership |
| State designates group as target | Hyperedge | XGI | "Black Nationalist Hate Groups" |

**Interaction Between Layers**: Hyperedge overlap creates solidarity *potential*. Pairwise edges realize solidarity *actuality*. Two agents sharing three community memberships have high overlap — but solidarity only becomes real when organizing work (a verb, V.1) creates or transforms a rustworkx edge between them.

**Update Frequencies**:

- Edges (rustworkx): Updated per tick (flows are dynamic)
- Hyperedges (XGI): Alpha-smoothed updates (identity and membership are stable)

**Implementation Requirements**:

1. **The two layers MUST remain separate data structures.** rustworkx for dyadic flows, XGI for membership topology. Do not flatten hyperedges into cliques of pairwise edges — this destroys the collective semantics.

1. **Membership queries MUST use XGI.** "Which agents belong to community X?" is a hyperedge incidence query, not a graph traversal.

1. **Flow queries MUST use rustworkx.** "How much value flows from A to B?" is an edge attribute lookup, not a hypergraph operation.

1. **Cross-layer computation is explicit.** When solidarity potential (derived from hyperedge overlap) informs edge creation or transformation, the computation MUST clearly bridge the two layers with documented functions.

**Rationale**: Collapsing community membership into pairwise edges loses the n-ary structure. A community of 50 members is one hyperedge, not 1,225 pairwise edges. More importantly, the state can target the hyperedge directly (surveil the community), which has no natural representation as operations on 1,225 individual edges. The ontological distinction — flows vs membership — maps cleanly to the technical distinction between graphs and hypergraphs.

**Three Hyperedge Categories**:

**Category 1 — Contradiction Pairs**: Both hegemonic and marginalized sides are real hyperedges with members, institutions, political projects, and material extraction flows between them.

| Hegemonic Hyperedge | Marginalized Hyperedge(s) | Material Basis of Extraction |
| ------------------- | ------------------------- | ---------------------------- |
| SETTLER | NEW_AFRIKAN, FIRST_NATIONS, CHICANO | Land, imperial rent, carceral labor, property value regimes |
| PATRIARCHAL | WOMEN, TRANS | Unwaged reproductive labor (Dept III), wage gap, care externalization |

SETTLER has institutions (HOAs, police unions, suburban school boards, border militias), material infrastructure (property value regimes, redlining legacies), and active political projects. It recruits, organizes, and defends its extraction position.

PATRIARCHAL has institutions (patriarchal family structure, gendered wage systems, religious hierarchies) and extracts reproductive labor (Federici). Trans men do not occupy the same material position in patriarchy as cis men — PATRIARCHAL membership is defined by material position in extraction, not gender identity.

**Category 2 — Institutional Exclusion**: Only the marginalized side exists as a real hyperedge. No paired oppressor community. Oppression flows through institutional defaults and resource allocation.

| Hyperedge | Material Basis | Why No Paired Oppressor |
| --------- | -------------- | ----------------------- |
| DISABLED | Built environment assumes able-bodiedness; higher reproduction costs | ABLED is absence of disability, not a political community |
| QUEER | Institutional heteronormativity; exclusion from protections | HETEROSEXUAL is unmarked default |
| UNDOCUMENTED | Legal exclusion from labor protections, healthcare, housing | CITIZEN is legal status, not solidarity community |
| INCARCERATED | Carceral system; sub-minimum labor extraction; civil death | FREE is absence of incarceration |

**Category 3 — Lifecycle Phases (D-P-D' Circuit)**: Temporal positions in the intergenerational lifecycle. NOT identity communities — structural phases with distinct material conditions.

| Hyperedge | D-P-D' Phase | Material Position |
| --------- | ------------ | ----------------- |
| YOUTH | D (Dependent) | Pre-productive. Cannot sell labor-power. Receives care, socialization, ideological transmission. |
| ADULT | P (Productive) | Sells labor-power. Where C-M-C and M-C-M' operate. |
| ELDER | D' (Dependent') | Post-productive. The D' promise (Social Security, pensions) is the legitimation bargain. |

Universal traversal, temporal permeability. Dependency ratio = (Pop_D + Pop_D') / Pop_P.

### 8. Client as Presentation Layer

The browser is a viewport into server-computed state, not a participant
in computation. The frontend receives game state as JSON, renders it,
and emits player intents as JSON. It never runs simulation logic, never
hydrates graphs, never resolves ticks. The Django REST API is the durable
contract; the frontend framework is disposable and replaceable without
affecting the engine, the API, or the database. JSON is the interchange
format at every system boundary.

**The Request Path**:

```
Player intent (click/input)
  → React component emits JSON action
    → Cloudflare (X.5: DNS, SSL, WAF)
      → Nginx (reverse proxy)
        → Gunicorn (WSGI)
          → Django REST API (durable contract)
            → Engine (rustworkx, Systems, Formulas)
              → Postgres (state persistence)
            ← Engine returns new state
          ← Django serializes to JSON
        ← Gunicorn returns response
      ← Nginx forwards
    ← Cloudflare forwards
  ← React renders new state
```

**Three Architectural Commitments**:

1. **The client is a viewport, not a brain.** The browser renders state
   received as JSON. It never runs simulation logic, never computes tick
   resolution, never touches the graph directly. If the frontend
   disappears, the engine still works. This is the client-side complement
   to II.5 (AI Observes, Never Controls) — the browser is a third
   observer alongside the AI narrative layer.

2. **JSON is the boundary contract.** React ↔ Django, Django ↔ Engine,
   Engine ↔ Postgres — JSON at every seam. Any layer can be replaced
   without touching the others. A `curl` and `jq` can inspect any
   boundary. This extends II.6 (State is Data) to the network boundary.

3. **The frontend is disposable.** The Django API is the durable surface.
   React today, Godot tomorrow, a CLI tool, a different web framework —
   all consume the same JSON contract. No frontend-specific logic leaks
   into the engine or the API.

**Why React (pragmatic, not aesthetic)**:

React is chosen for AI-assisted development reliability, not technical
merit. Svelte is arguably better for this use case (smaller bundles,
less boilerplate, simpler mental model). But React's dominance in
training data means higher vibe-coding reliability — AI tools produce
more correct React code more often. This is a pragmatic choice,
explicitly reversible, and documented as such.

**Relationship to VII.1**: Article VII principle 1 (UI Observes, Never
Controls) governs the visual design layer. II.8 governs the architectural
layer. VII.1 says the UI emits intents and never mutates state. II.8 says
the entire frontend is a replaceable viewport consuming a JSON contract.
They are complementary — VII.1 constrains what the UI does; II.8
constrains what the UI is.

**Frontend Investment Deferral**: Frontend development is deferred until
beta validates the engine. The engine, API, and database are the durable
investments. The frontend is the last layer built and the first layer
replaceable.
