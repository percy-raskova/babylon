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

### Epoch 1 Completion Criteria

- [ ] 4-node Imperial Circuit running in dashboard
- [ ] MetabolismSystem depletes biocapacity over time
- [ ] ECOLOGICAL_OVERSHOOT fires at ~30-50 ticks
- [ ] Dashboard shows rift widening visually
- [ ] Endgame screen displays outcome based on solidarity
- [ ] All tests pass (target: 2300+)

---

## Epoch 2: The Game (FUTURE)

**Thesis:** *"The player has agency. Decisions matter. Multiple endings."*

**Status:** PLANNED

### Slices

| Slice | Name | Description |
|-------|------|-------------|
| 2.1 | Demographic Resolution | Full necropolitics vs redistribution mechanics |
| 2.2a | Strategy Layer (External) | Resource traps: Liberal, Ultra-Left, Rightist |
| 2.2b | The Vanguard (Internal) | Cohesion, entropy, organizational dynamics |
| 2.3 | Reproductive Labor | L_restore, regeneration via care work |
| 2.4 | The Wire (Narrative Warfare) | Hegemony mechanics, propaganda actions |
| 2.5 | The Resource Economy | Cadre Labor, Sympathizer Labor, Reputation |
| 2.6 | Kinetic Warfare | Asymmetric logistics, system disruption |
| 2.7 | Multiple Scenarios | Historical scenarios, custom setups |
| 2.8 | The Panopticon | State attention economy, surveillance costs |

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

Intra-organizational mechanics based on the Iron Law of Oligarchy:
- **The Transmission Law:** `Effective_Transmission = min(Solidarity, Cohesion)`
- **The Scale Law:** Growth automatically degrades Cohesion (entropy accumulation)
- **Fail State:** Low cohesion during crisis triggers ORGANIZATIONAL_SPLIT

Actions: Mass Recruitment (bloating trap), Rectification (painful surgery), Political Education (sustainable path)

Resources: Cohesion, Entropy, Cadre Ratio

This is where organizational health determines whether external actions succeed or fail.

### Slice 2.4: The Wire (Narrative Warfare)

**Spec:** `ai-docs/gramscian-wire-vision.yaml`

Full interactive narrative control system based on Gramscian hegemony:
- **Hegemony Resource:** Determines which narrative is "mainstream"
- **Three Channels:** Corporate Feed (hegemonic), Liberated Signal (counter-hegemonic), Intel Stream (raw data)
- **Player Actions:** `jam_signal`, `distribute_samizdat`, `capture_media_node`, `viral_campaign`

This builds on the Gramscian Wire MVP from Epoch 1 (dual narrative display) by adding player agency over narrative terrain. "The War of Position" becomes playable.

### Slice 2.5: The Resource Economy

**Spec:** `ai-docs/vanguard-economy.yaml`

The "Vanguard Efficiency Equation" - materialist resource model:
- **Three Currencies:** Cadre Labor (quality), Sympathizer Labor (quantity), Reputation (multiplier)
- **Transmission Belt:** Coherence Factor = sigmoid(Cadre/Sympathizer/K)
- **The Influencer Trap:** High Rep + Low Cadre = uncontrollable mobs
- **The Reading Group Trap:** High Cadre + Low SL = irrelevant precision

This is where "What Is To Be Done?" becomes gameplay. Players must balance quality and quantity - neither extreme wins.

### Slice 2.6: Kinetic Warfare

**Spec:** `ai-docs/kinetic-warfare.yaml`

The "Asymmetric Logistics Engine" - combat as system disruption:
- **Target Triad:** Extraction (correct), Circulation (trap), Realization (suicide)
- **The Blowback Formula:** Collateral damage alienates masses
- **Ultra-Left Deviation:** Game over state from political failure despite military success
- **Integration:** Cohesion affects attack quality, Wire frames outcomes

This is where the "Ultra-Left Trap" from the Strategy Layer becomes mechanically realized. Players learn that winning battles while losing hearts is the path to defeat.

### Slice 2.8: The Panopticon

**Spec:** `ai-docs/state-attention-economy.yaml`

The "State Attention Economy" - enemy AI as information processing:
- **Threads (Θ):** Integer limit of concurrent State operations per tick
- **Expansion Costs:** Surveillance increases Agitation, Algorithms drop Legitimacy
- **DDoS Strategy:** Saturate State attention with noise, execute in blind spots
- **Police State Spiral:** More surveillance → more resistance → more surveillance

This is where the enemy becomes exploitable. The State can see everything but process only fragments. The player wins by overwhelming cognition, not defeating force.

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
| `ai-docs/demographics-spec.yaml` | Slice 2.1 spec |
| `ai-docs/architecture.yaml` | System architecture |
| `ai-docs/formulas-spec.yaml` | Formula inventory |

---

*Document created: 2025-12-26*
*Model: Epoch + Slice (supersedes Phase model)*
