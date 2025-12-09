# Deferred Ideas Parking Lot

**Purpose:** This is where good ideas come to WAIT, not die. Everything here is valuable but NOT part of the current sprint.

**Rule:** If you're tempted to implement something from this list, ask: "Does it help pass the current failing test?"

---

## Phase 2: Topological Engine

These ideas require the Phase 1 foundation to be complete first.

### ~~Ideological Drift Formula~~ IMPLEMENTED
**Source:** `notes/manifesto.md`
**Equation:** `dΨc/dt = k(1 - Wc/Vc) - λΨc`
**Status:** Implemented in Sprint 7.5 via `_update_consciousness_drift()` in simulation_engine.py
**Tests:** 7 new tests in TestStepConsciousnessDrift (325 total passing)

### Full Imperial Rent Function
**Source:** `notes/manifesto.md`
**Equation:** `Φ(Wp, Ψp) = α·Wp·(1 - Ψp)`
**What it does:** Makes imperial rent depend on periphery consciousness - as they radicalize, rent extraction becomes harder
**Why wait:** Need basic rent formula working first

### The Update Loop (Tick Function)
**What it does:** `new_state = tick(old_state)` - advances simulation one turn
**Why wait:** Need entities and formulas to have something to tick

---

## Phase 3: AI Observer Layer

These ideas require the engine to be running and generating events.

### RAG as Semantic Firewall (Input Validation)
**Source:** `brainstorm/rag-input-validation.md`, `ai-docs/rag-architecture.yaml`
**What it does:** Uses RAG collections as permission system - semantic distance determines if player action is valid
**Key insight:** If input has no semantic neighbors in corpus, it doesn't exist in this material world
**Components:**
- `actions` collection: ~200-500 canonical game verbs
- `entities` collection: ~1000+ game nouns
- `anti_patterns` collection: injection patterns, fantasy terms
- 6-stage validation pipeline: structural → semantic gate → action mapper → context builder → LLM → output validator
**Why it matters:** Prevents prompt injection AND thematic violations with single architecture
**Status:** Brainstorm complete, ready for Phase 3 implementation

### RAG Collections Population
**Source:** `ai-docs/rag-architecture.yaml`
**What it does:** Extract actions from game mechanics, entities from JSON data, curate anti_patterns
**Dependencies:** Needs Observer Pattern infrastructure first
**Why wait:** Phase 3 work, requires semantic validation architecture

### Sanity Spies (The Babylon Protocol)
**Source:** `brainstorm/babylon-protocol-verification.md`
**What it does:** Runtime observers that validate invariants (conservation laws, P(S) calculus, topology integrity, determinism)
**Why it matters:** Distinguishes "Holy Shit" (emergence) from "Absolute Nonsense" (bugs)
**Why wait:** Requires event system and observer pattern infrastructure

### Loss Aversion Coefficient
**Source:** `notes/manifesto.md`
**Constant:** `LAMBDA_LOSS = 2.25` (Kahneman/Tversky)
**What it does:** People fight 2.25x harder to keep what they have than to gain what they lack
**Why wait:** Refinement of P(S|A), not foundation

### Bell Curve Class Distributions
**Source:** `notes/diamat.md`
**What it does:** Instead of class having single ideology, has mean + variance (Gaussian)
**Why wait:** Enables outliers (Engels, fascist workers) but requires population modeling

### Ideological Rotation Matrix
**Source:** `notes/manifesto.md`
**What it does:** Rotates anger vector from "system" to "scapegoat" based on ideology
**Why wait:** Sophisticated mechanic for Phase 3+ narrative

### Avatar System ("Face of the Crowd")
**Source:** `notes/avatars.md`
**What it does:** Named characters represent class statistics, generate dialogue
**Why wait:** Narrative layer, needs AI integration

### "Letters from Home" Mechanic
**Source:** `notes/avatars.md`
**What it does:** Personal messages between turns showing human cost of policy
**Why wait:** Narrative/emotional engagement, Phase 3+

---

## Phase 4+: Control Room & Beyond

### God Mode (Chaos Testing)
**Source:** Good Idea Fairy 2025-12-08
**What it does:** Bypasses semantic validation - anything goes. Sorcery, aliens, prompt injection experiments.
**Use cases:**
- Chaos testing the LLM integration
- Exploring edge cases without restrictions
- Just for shits and giggles
- Testing what happens when validation is OFF
**Implementation:** Flag in SimulationConfig that disables Stage 2 (Semantic Gate) validation
**Why wait:** Requires validation pipeline to exist first (Phase 3), then we can add the bypass

### Gramscian Wiki Engine
**Source:** `brainstorm/gramscian-wiki-engine.md`
**What it does:** Hegemony as factional control over in-game encyclopedia
**Why wait:** Major feature requiring full game loop

### Dynamic Character Portraits
**Source:** `notes/avatars.md`
**What it does:** Stable Diffusion generates avatars based on economic state
**Why wait:** Way beyond scope, nice-to-have for polish

### Sankey Diagram for Value Flows
**Source:** `notes/manifesto.md`
**What it does:** Visualize imperial rent as flowing from periphery to core
**Why wait:** UI polish, needs NiceGUI dashboard first

### Phase Portrait Visualization
**Source:** `notes/manifesto.md`
**What it does:** 2D plot showing class position in Deprivation × Repression space
**Why wait:** Requires working topological engine

---

## Explicitly NOT Doing

These ideas are interesting but would fundamentally change the architecture. Reject them.

### Real-time multiplayer
**Why reject:** Adds networking complexity, destroys local-first architecture

### 3D graphics / Unity integration
**Why reject:** We're building a simulation engine, not a AAA game

### Mobile app
**Why reject:** Focus on desktop CLI/NiceGUI first

### Procedural map generation
**Why reject:** Phase 1 is two nodes, not a world

---

## How to Use This Document

1. **When the Good Idea Fairy visits:** Write one sentence here, tag with phase
2. **When starting a sprint:** Check if anything here is now relevant
3. **When feeling tempted:** Re-read the "Explicitly NOT Doing" section
4. **When promoting:** Move to a brainstorm file with full detail

**The Mantra:** Two nodes. One edge. Passing tests. Ship.
