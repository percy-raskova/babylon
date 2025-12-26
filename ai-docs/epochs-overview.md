# Babylon Epochs Overview

> "Build the demonstration first. Then build the game. Finally, build the platform."

---

## The Model: Epochs + Slices

Babylon uses a two-dimensional organizational model:

| Dimension | Definition | Example |
|-----------|------------|---------|
| **Epoch** | A playable checkpoint - the game is shippable at this state | Epoch 1: The Demonstration |
| **Slice** | A complete vertical feature within an Epoch | Slice 1.4: The Rift |

**Numbering:** `Epoch.Slice` (e.g., "1.4" = Epoch 1, Slice 4)

### Why This Model?

The previous "Phase" model conflated vertical layers (bedrock → interface) with horizontal features (metabolism, demographics). This led to:
- Sub-sub-numbering chaos (Phase 4.1A, 4.1B, 4.1C)
- MVP-critical features labeled as "future" (metabolism was Phase 5)
- No clear definition of "done" for any milestone

The Epoch + Slice model fixes this:
- Each **Epoch** is a playable state with a clear thesis
- Each **Slice** is a complete vertical cut (formulas → system → events → UI)
- Work is prioritized by what advances the current Epoch's thesis

---

## Epoch 0: The Kernel (COMPLETE)

**Thesis:** *"The math works. The tests pass."*

**Status:** COMPLETE (2248 tests passing)

### What's Included
- Pure MLM-TW formulas (`src/babylon/systems/formulas.py`)
- Constrained types: `Probability`, `Currency`, `Ideology`
- `SimulationEngine` with System-based architecture
- `NetworkX` graph topology integration
- `ServiceContainer` dependency injection
- TDD infrastructure: `DomainFactory`, `BabylonAssert`

### Completion Criteria
- [x] All formulas implemented and tested
- [x] Type constraints enforce valid state
- [x] Engine runs without UI
- [x] Tests prove mathematical correctness

---

## Epoch 1: The Demonstration (CURRENT)

**Thesis:** *"The player watches the Imperial Circuit consume itself and sees the Fascist Bifurcation."*

**Status:** IN PROGRESS

**Target:** A playable demo where:
1. The Imperial Circuit extracts rent (visible)
2. The metabolic rift widens (visible)
3. Crisis arrives at ~30-50 ticks (event fires)
4. Outcome depends on solidarity (win/lose display)

### Slices

| Slice | Name | Status | Description |
|-------|------|--------|-------------|
| 1.1 | The Circuit | COMPLETE | ImperialRentSystem, SolidaritySystem, 4-node scenario |
| 1.2 | The Struggle | COMPLETE | StruggleSystem, TerritorySystem, George Floyd Dynamic |
| 1.3 | The Observer | COMPLETE | TopologyMonitor, MetricsCollector, 11 EventTypes |
| 1.4 | The Rift | IN_PROGRESS | MetabolismSystem, biocapacity, ECOLOGICAL_OVERSHOOT |
| 1.5 | The Dashboard | PARTIAL | NiceGUI layout, meaningful metrics, metabolic gauge |
| 1.6 | The Endgame | NOT_STARTED | Win/lose display, Bondi Algorithm narration |
| 1.7 | The Graph Bridge | PLANNED | GraphProtocol, NetworkX Adapter, Epoch 2 preparation |

### Slice 1.1: The Circuit (COMPLETE)

**Files:**
- `src/babylon/engine/systems/economic.py` - ImperialRentSystem
- `src/babylon/engine/systems/solidarity.py` - SolidaritySystem
- `src/babylon/engine/scenarios.py` - create_imperial_circuit_scenario()

**Edges:** EXPLOITATION, TRIBUTE, WAGES, CLIENT_STATE, SOLIDARITY

**Nodes:** P_w (Periphery Worker), P_c (Comprador), C_b (Core Bourgeoisie), C_w (Labor Aristocracy)

### Slice 1.2: The Struggle (COMPLETE)

**Files:**
- `src/babylon/engine/systems/struggle.py` - StruggleSystem
- `src/babylon/engine/systems/territory.py` - TerritorySystem

**Mechanics:**
- George Floyd Dynamic: EXCESSIVE_FORCE → UPRISING → SOLIDARITY_SPIKE
- Carceral Geography: heat dynamics, eviction pipeline
- Necropolitical Triad: RESERVATION, PENAL_COLONY, CONCENTRATION_CAMP

### Slice 1.3: The Observer (COMPLETE)

**Files:**
- `src/babylon/engine/observer.py` - SimulationObserver protocol
- `src/babylon/engine/topology_monitor.py` - TopologyMonitor
- `src/babylon/engine/observers/metrics.py` - MetricsCollector

**Events:** 11 EventTypes (SURPLUS_EXTRACTION, UPRISING, PHASE_TRANSITION, etc.)

### Slice 1.4: The Rift (IN PROGRESS)

**Spec:** `ai-docs/metabolic-slice.yaml`

**Files (to create):**
- `src/babylon/engine/systems/metabolism.py` - MetabolismSystem
- Territory model updates (biocapacity, regeneration_rate)
- SocialClass model updates (s_bio, s_class, consumption_needs)

**Formula:** `ΔB = Regeneration - (Extraction × Entropy_Factor)`

**Event:** ECOLOGICAL_OVERSHOOT (when consumption > biocapacity)

### Slice 1.5: The Dashboard (PARTIAL)

**Files:**
- `src/babylon/ui/main.py` - NiceGUI application

**Remaining Work:**
- Wire 4-node scenario (currently 2-node)
- 4 wealth lines color-coded by class
- Consciousness gap (P_w - C_w)
- Metabolic gauge showing overshoot_ratio
- Rift trend chart
- **Gramscian Wire MVP** - Dual narrative display (see below)

#### Gramscian Wire MVP (Slice 1.5 Integration)

**Spec:** `ai-docs/gramscian-wire-mvp.yaml`

Demonstrates thesis "Neutrality is Hegemony" through dual narrative display:
- **The State (Corporate Feed):** "Officers restored order amid disturbances"
- **The Underground (Liberated Signal):** ">>> STATE VIOLENCE - SOLIDARITY REQUIRED <<<"

Same event, two framings. Side-by-side display teaches Gramsci without mechanics.
No interactive hegemony system yet—that comes in Epoch 2 (see `gramscian-wire-vision.yaml`).

### Slice 1.6: The Endgame (NOT STARTED)

**Mechanics:**
- Detect ECOLOGICAL_OVERSHOOT event
- Check solidarity_strength at crisis moment
- Win: solidarity > threshold → "Revolutionary Path"
- Lose: solidarity < threshold → "Fascist Path"
- Bondi Algorithm narration of outcome

### Slice 1.7: The Graph Bridge (PLANNED)

**Spec:** `ai-docs/graph-abstraction-spec.yaml`

**Status:** PLANNED

**Purpose:** Graph Abstraction Layer, Protocol definition, NetworkX Adapter.

**Rationale:** Prepares architecture for Epoch 2 scale (Franchise Model) without breaking Epoch 1 demo. Creates the interface boundary between Game Loop and Graph Engine.

**Components:**
- `GraphProtocol` interface (16 methods: CRUD, traversal, set operations)
- `GraphNode`, `GraphEdge` Pydantic models (frozen, type-safe)
- `NetworkXAdapter` reference implementation (InMemoryAdapter)
- `TraversalQuery`/`TraversalResult` for percolation analysis

**Epoch 2 Bridge:**
- Defines Franchise Schema node types: `OrganizationUnit`, `PopFragment`, `Territory`
- Defines new edge types: `COMMAND`, `OPERATES_IN`, `INFLUENCES`, `RESIDES_IN`
- Documents Action Flow: Agent → Signal → OrganizationUnit → Effect → Graph
- DuckDB-ready interface (set-oriented queries, SQL translation examples)

**Files (to create):**
- `src/babylon/models/graph.py` - GraphNode, GraphEdge, TraversalQuery
- `src/babylon/engine/graph_protocol.py` - GraphProtocol interface
- `src/babylon/engine/adapters/inmemory_adapter.py` - NetworkXAdapter

### Epoch 1 Completion Criteria

- [ ] 4-node Imperial Circuit running in dashboard
- [ ] MetabolismSystem depletes biocapacity over time
- [ ] ECOLOGICAL_OVERSHOOT fires at ~30-50 ticks
- [ ] Dashboard shows rift widening visually
- [ ] Endgame screen displays outcome based on solidarity
- [ ] GraphProtocol defined and implemented via NetworkXAdapter
- [ ] All tests pass (target: 2300+)

---

## Epoch 2: The Game (FUTURE)

**Thesis:** *"The player has agency. Decisions matter. Multiple endings."*

**Status:** PLANNED

### Sub-Epoch Model

Epoch 2 is divided into **four sub-epochs** for staged delivery:

| Sub-Epoch | Name | Focus | Slices |
|-----------|------|-------|--------|
| **2A** | Core Agency | Basic player actions & resources | 2.1, 2.2a, 2.6 |
| **2B** | Organization | Internal dynamics & class struggle | 2.2b, 2.3, 2.8 |
| **2C** | Information | Narrative warfare & intelligence | 2.5, 2.9, 2.10 |
| **2D** | Combat | Kinetic operations | 2.7 |

**Rationale:** Each sub-epoch delivers a playable increment:
- **2A** gives players meaningful choices within 3 slices
- **2B** adds organizational complexity once basics work
- **2C** adds information warfare as late-game depth
- **2D** adds combat last (combat systems are notoriously difficult to balance)

**Deferrals:**
- Slice 2.4 (Reproductive Labor) → Epoch 2.5 or 3 (needs more design work)
- Slice 2.11 (Multiple Scenarios) → Epoch 3 (platform work)

### All Slices Overview

| Slice | Name | Sub-Epoch | Status | Description |
|-------|------|-----------|--------|-------------|
| 2.1 | Demographic Resolution | 2A | PLANNED | Full necropolitics vs redistribution mechanics |
| 2.2a | Strategy Layer (External) | 2A | PLANNED | Resource traps: Liberal, Ultra-Left, Rightist |
| 2.2b | The Vanguard (Internal) | 2B | PLANNED | Cohesion, entropy, organizational dynamics |
| 2.3 | The Reactionary Subject | 2B | PLANNED | Class basis of fascism, organizational traps |
| 2.4 | Reproductive Labor | DEFERRED | CONCEPTUAL | L_restore, regeneration via care work |
| 2.5 | The Wire (Narrative Warfare) | 2C | PLANNED | Hegemony mechanics, propaganda actions |
| 2.6 | The Resource Economy | 2A | PLANNED | Cadre Labor, Sympathizer Labor, Reputation |
| 2.7 | Kinetic Warfare | 2D | PLANNED | Asymmetric logistics, system disruption |
| 2.8 | The Doctrine System | 2B | PLANNED | Ideological tech tree, line struggle, traps |
| 2.9 | The Panopticon | 2C | PLANNED | State attention economy, surveillance costs |
| 2.10 | The Epistemic Horizon | 2C | PLANNED | Fog of war, Fish in Water intel system |
| 2.11 | Multiple Scenarios | DEFERRED | CONCEPTUAL | Historical scenarios, custom setups |

---

## Sub-Epoch 2A: Core Agency

**Thesis:** *"The player can act. Resources constrain choices. Traps are visible."*

**Status:** PLANNED

**Dependencies:** Epoch 1 complete

**Target:** A playable game where:
1. Player allocates resources (CL, SL, Reputation)
2. Player chooses actions (Electoralism, Adventurism, Economism)
3. Demographics resolve through player choices
4. Traps become obvious through failure

### 2A Slices

| Slice | Name | Priority | Description |
|-------|------|----------|-------------|
| 2.1 | Demographic Resolution | P0 | Population metabolism, resolution pathways |
| 2.2a | Strategy Layer | P0 | External actions, resource traps |
| 2.6 | Resource Economy | P0 | CL/SL/Reputation currencies |

### 2A Completion Criteria

- [ ] Player can spend CL/SL/Reputation on actions
- [ ] Three resource traps are functional (Liberal, Ultra-Left, Rightist)
- [ ] Demographics respond to player choices
- [ ] Multiple endings based on action patterns
- [ ] Tests pass (target: +300 from Epoch 1)

### Slice 2.1: Demographic Resolution

**Spec:** `ai-docs/demographics-spec.yaml`

The full demographic engine with:
- S_bio vs S_class consumption distinction
- Resolution pathways: Fascist, Socialist, Imperial
- Population dynamics (growth, decline, migration)

This is where the ECOLOGICAL_OVERSHOOT from Epoch 1 gets RESOLVED, not just detected.

### Slice 2.2: Player Controls (Strategy Layer + Vanguard)

Player agency consists of two complementary systems:

#### 2.2a: External Actions (Strategy Layer)

**Spec:** `ai-docs/strategy-layer.yaml`

Player choices with meaningful but dangerous traps:
- **The Liberal Trap (Electoralism):** Run candidates, lower repression, lose revolutionary pressure
- **The Ultra-Left Trap (Adventurism):** Kinetic strikes, halt extraction, risk network collapse
- **The Rightist Trap (Economism):** Wage strikes, improve conditions, become labor aristocracy

#### 2.2b: Internal Dynamics (The Vanguard)

**Spec:** `ai-docs/cohesion-mechanic.yaml`

**Architecture:** Uses the **Franchise Model** defined in Slice 1.7 (`ai-docs/graph-abstraction-spec.yaml`):
- Player's organization is an **Agent** (external to the graph)
- Chapters, Cells, Brigades are **OrganizationUnits** (graph nodes)
- Actions flow: Agent → Signal → OrganizationUnit → Effect → Graph

Intra-organizational mechanics based on the Iron Law of Oligarchy:
- **The Transmission Law:** `Effective_Transmission = min(Solidarity, Cohesion)`
- **The Scale Law:** Growth automatically degrades Cohesion (entropy accumulation)
- **Fail State:** Low cohesion during crisis triggers ORGANIZATIONAL_SPLIT

Actions: Mass Recruitment (bloating trap), Rectification (painful surgery), Political Education (sustainable path)

Resources: Cohesion, Entropy, Cadre Ratio

This is where organizational health determines whether external actions succeed or fail.

### Slice 2.3: The Reactionary Subject

**Spec:** `ai-docs/reactionary-subject.yaml`

The "Class Basis of Fascism" - foundational understanding of allies and enemies:
- **Fascist Base:** Petty Bourgeoisie (C_pb) + Labor Aristocracy (C_la), driven by "Status Anxiety"
- **Revolutionary Base:** Proletariat (P_w) + Lumpenproletariat (L_u), driven by "Survival"
- **The Lumpen Distinction:** L_u are NOT the fascist base (George Jackson model)
- **Organizational Trap:** Recruiting C_la brings resources but Chauvinism debuff

Key mechanics:
- **Entitlement metric:** Investment in status quo (high for C_la/C_pb, low for P_w/L_u)
- **Chauvinism accumulation:** C_la recruits carry debuff that triggers defection during crisis
- **Fascist Actions:** Pogrom, Lockout, Vigilantism (Strategy of Tension)
- **RED_BROWN_COUP:** When Chauvinism > Discipline, coalition members defect to fascists

This is foundational because you cannot make strategic decisions about WHO to organize without understanding the class basis of both revolution AND fascism. "Agitation without solidarity produces fascism, not revolution."

### Slice 2.4: Reproductive Labor

**Spec:** *Not yet created*

L_restore mechanics and regeneration via care work. Care labor as the hidden foundation of all economic activity.

### Slice 2.5: The Wire (Narrative Warfare)

**Spec:** `ai-docs/gramscian-wire-vision.yaml`

Full interactive narrative control system based on Gramscian hegemony:
- **Hegemony Resource:** Determines which narrative is "mainstream"
- **Three Channels:** Corporate Feed (hegemonic), Liberated Signal (counter-hegemonic), Intel Stream (raw data)
- **Player Actions:** `jam_signal`, `distribute_samizdat`, `capture_media_node`, `viral_campaign`

This builds on the Gramscian Wire MVP from Epoch 1 (dual narrative display) by adding player agency over narrative terrain. "The War of Position" becomes playable.

### Slice 2.6: The Resource Economy

**Spec:** `ai-docs/vanguard-economy.yaml`

The "Vanguard Efficiency Equation" - materialist resource model:
- **Three Currencies:** Cadre Labor (quality), Sympathizer Labor (quantity), Reputation (multiplier)
- **Transmission Belt:** Coherence Factor = sigmoid(Cadre/Sympathizer/K)
- **The Influencer Trap:** High Rep + Low Cadre = uncontrollable mobs
- **The Reading Group Trap:** High Cadre + Low SL = irrelevant precision

This is where "What Is To Be Done?" becomes gameplay. Players must balance quality and quantity - neither extreme wins.

### Slice 2.7: Kinetic Warfare

**Spec:** `ai-docs/kinetic-warfare.yaml`

The "Asymmetric Logistics Engine" - combat as system disruption:
- **Target Triad:** Extraction (correct), Circulation (trap), Realization (suicide)
- **The Blowback Formula:** Collateral damage alienates masses
- **Ultra-Left Deviation:** Game over state from political failure despite military success
- **Integration:** Cohesion affects attack quality, Wire frames outcomes

This is where the "Ultra-Left Trap" from the Strategy Layer becomes mechanically realized. Players learn that winning battles while losing hearts is the path to defeat.

### Slice 2.8: The Doctrine System

**Spec:** `ai-docs/doctrine-tree.yaml`

The "Ideological Line Struggle" - tech tree with mutually exclusive splits:
- **Four Trunks:** Reformist, Insurrectionist, Autonomist, Scientific (Leninist/Maoist)
- **Tag System:** LEGALITY, MILITANCY, MASS_LINK, SECRECY, NATIONALISM, CLASS_ANALYSIS
- **Trap Endings:** Liquidationism, Adventurism, Dissociation
- **Degeneration Path:** PatSoc → National Syndicalism → Strasserism (Fascism)

This is where ideology becomes gameplay. The player chooses a line and lives its consequences. "The correctness of the ideological line decides everything."

### Slice 2.9: The Panopticon

**Spec:** `ai-docs/state-attention-economy.yaml`

The "State Attention Economy" - enemy AI as information processing:
- **Threads (Θ):** Integer limit of concurrent State operations per tick
- **Expansion Costs:** Surveillance increases Agitation, Algorithms drop Legitimacy
- **DDoS Strategy:** Saturate State attention with noise, execute in blind spots
- **Police State Spiral:** More surveillance → more resistance → more surveillance

This is where the enemy becomes exploitable. The State can see everything but process only fragments. The player wins by overwhelming cognition, not defeating force.

### Slice 2.10: The Epistemic Horizon

**Spec:** `ai-docs/fog-of-war.yaml`

The "Fish in Water" intelligence system - dialectical fog of war:
- **Core Thesis:** Intelligence flows through social relationships, not technical means
- **Mass Receptivity:** Willingness of locals to share info = f(desperation, alignment, class)
- **Three Vision States:** Desert (hostile, masked data), Mud (contested, approximate), Water (base area, full intel)
- **The Trap:** In hostile territory, data may be FALSIFIED - you walk into ambushes

Key mechanics:
- **Intel Formula:** `Confidence = Base_Observation + (Cadre_Presence × Mass_Receptivity)`
- **Mass Work Prerequisite:** You cannot scout, you must WORK to earn intel
- **Fish Out of Water:** Cadre in hostile territory generate State Attention and risk capture
- **Intel Decay:** Information becomes stale faster in hostile territory

This complements the Panopticon (Slice 2.9): State sees everywhere but understands nothing; Player understands but only where they've built relationships. "Win the people, know the terrain."

---

## Sub-Epoch 2B: Organization

**Thesis:** *"The party can fail from within. Cohesion matters. Class composition determines destiny."*

**Status:** PLANNED

**Dependencies:**
- Sub-Epoch 2A complete
- Slice 1.7 (GraphProtocol) complete - required for Franchise Model
- DuckDB / DuckPGQ integration (optional but recommended for scale)

**Target:** A playable game where:
1. Organizational health affects action success
2. Wrong class composition leads to betrayal
3. Doctrine choices create path dependencies
4. Iron Law of Oligarchy becomes visceral

### 2B Slices

| Slice | Name | Priority | Description |
|-------|------|----------|-------------|
| 2.2b | The Vanguard | P0 | Cohesion, entropy, internal dynamics |
| 2.3 | Reactionary Subject | P0 | Class basis of fascism, chauvinism |
| 2.8 | Doctrine System | P1 | Ideological tech tree (SIMPLIFIED for 2B) |

### 2B Completion Criteria

- [ ] Cohesion affects transmission of consciousness
- [ ] Entropy accumulates with growth
- [ ] Class composition affects organizational behavior
- [ ] Chauvinism triggers RED_BROWN_COUP during crisis
- [ ] Doctrine tree with 2-3 trunks functional (full 8 trunks deferred)
- [ ] Tests pass (target: +250 from 2A)

### 2B Scope Notes

**Doctrine Simplification for 2B:**
- Implement 3 trunks only: Scientific (correct), Reformist (trap), Insurrectionist (trap)
- Defer synthesis trunks (Autonomist-Scientific, etc.) to 2B.5
- Defer degeneration paths (PatSoc Pipeline) to 2B.5
- Focus on core tag mechanics: LEGALITY, MILITANCY, MASS_LINK

---

## Sub-Epoch 2C: Information

**Thesis:** *"Win the narrative, know the terrain. The State sees everything but understands nothing."*

**Status:** PLANNED

**Dependencies:** Sub-Epoch 2B complete

**Target:** A playable game where:
1. Hegemony is a contestable resource
2. State attention is finite and exploitable
3. Intelligence requires social relationships
4. Information asymmetry creates strategic depth

### 2C Slices

| Slice | Name | Priority | Description |
|-------|------|----------|-------------|
| 2.5 | The Wire | P0 | Narrative warfare, hegemony mechanics |
| 2.9 | The Panopticon | P0 | State attention economy, Thread allocation |
| 2.10 | Epistemic Horizon | P1 | Fog of war, Fish in Water intel |

### 2C Completion Criteria

- [ ] Hegemony resource affects narrative framing
- [ ] State allocates Threads based on threat assessment
- [ ] Player can saturate State attention (DDoS strategy)
- [ ] Intel quality depends on mass relationships
- [ ] Hostile territories can provide FALSIFIED intel
- [ ] Tests pass (target: +300 from 2B)

### 2C Scope Notes

**State AI Decision Logic (Critical Gap):**
Before implementing 2C, must define:
- Thread allocation algorithm (utility function or weighted random)
- Expansion trigger conditions (when does State upgrade?)
- Threat assessment heuristics

**Fog of War Simplification for 2C:**
- Start with simple vision states (Desert/Mud/Water)
- Defer intel falsification mechanics to 2C.5
- Focus on Mass Receptivity formula

---

## Sub-Epoch 2D: Combat

**Thesis:** *"Violence is the continuation of politics. Win the people before the battle."*

**Status:** PLANNED

**Dependencies:** Sub-Epoch 2C complete (requires Wire for outcome framing, Panopticon for State response)

**Target:** A playable game where:
1. Kinetic actions have political consequences
2. Blowback alienates masses
3. Ultra-Left deviation leads to defeat despite military success
4. Combat integrates with all previous systems

### 2D Slices

| Slice | Name | Priority | Description |
|-------|------|----------|-------------|
| 2.7 | Kinetic Warfare | P0 | Asymmetric logistics, target selection |

### 2D Completion Criteria

- [ ] Three target types functional (Extraction, Circulation, Realization)
- [ ] Blowback formula affects mass support
- [ ] Cohesion affects attack quality
- [ ] Wire frames combat outcomes
- [ ] State responds via Panopticon Thread allocation
- [ ] Ultra-Left deviation is achievable game-over state
- [ ] Tests pass (target: +150 from 2C)

### 2D Scope Notes

**Why Combat is Last:**
1. Combat systems are notoriously difficult to balance
2. Combat outcomes must integrate with Cohesion (2B), Wire (2C), Panopticon (2C)
3. Political consequences require all other systems functional
4. Players should learn "politics first" before having combat as an option

---

## Epoch 3: The Platform (FUTURE)

**Thesis:** *"Others can build on this. Modding, custom scenarios, educational tools."*

**Status:** CONCEPTUAL

### Slices

| Slice | Name | Description |
|-------|------|-------------|
| 3.1 | Liberation Mechanics | Reversing carceral geography |
| 3.2 | Scenario Editor | Custom scenario creation |
| 3.3 | Modding API | External system integration |

---

## Historical Note: Phase Numbering

Prior to 2025-12-26, Babylon used a "Phase" numbering system:
- Phase 0: Bedrock
- Phase 1: Material Base
- Phase 2: Observer
- Phase 3: Narrator
- Phase 4: Interface
- Phase 5: Horizontal Expansion

This is superseded by the Epoch + Slice model. Historical commits and some documentation may reference the old Phase numbers. The mapping is approximately:

| Old Phase | New Location |
|-----------|--------------|
| Phase 0-2 | Epoch 0 (Kernel) |
| Phase 3-4 | Epoch 1 (Demonstration) |
| Phase 5 | Epochs 2-3 (Game, Platform) |

---

## Working in This Model

### Adding New Work

1. Identify which Epoch it belongs to (playable checkpoint)
2. Is it a new Slice or part of an existing Slice?
3. If new Slice, assign next number (e.g., 1.7)
4. Create spec in `ai-docs/` with `epoch` and `slice` in meta
5. Add to this document

### Prioritization

Work is prioritized by:
1. **Current Epoch completion** - finish Epoch 1 before Epoch 2
2. **Thesis advancement** - does this work make the thesis demonstrable?
3. **Dependencies** - some Slices depend on others

### Definition of Done

An Epoch is COMPLETE when:
- All Slices are COMPLETE
- The thesis is demonstrable
- All tests pass
- Documentation is updated

A Slice is COMPLETE when:
- Formulas implemented and tested
- System implemented and tested
- Events emitting correctly
- Metrics exposed to MetricsCollector
- UI displays the feature (if applicable)

---

## Cross-References

| Document | Purpose |
|----------|---------|
| `ai-docs/state.yaml` | Current implementation status |
| `ai-docs/metabolic-slice.yaml` | Slice 1.4 spec |
| `ai-docs/graph-abstraction-spec.yaml` | Slice 1.7 spec (Graph Bridge) |
| `ai-docs/demographics-spec.yaml` | Slice 2.1 spec |
| `ai-docs/architecture.yaml` | System architecture |
| `ai-docs/formulas-spec.yaml` | Formula inventory |

---

*Document created: 2025-12-26*
*Model: Epoch + Slice (supersedes Phase model)*
