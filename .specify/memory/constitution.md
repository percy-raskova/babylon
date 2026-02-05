<!--
================================================================================
SYNC IMPACT REPORT
================================================================================
Version Change: 1.3.0 → 1.3.1
Bump Rationale: Added data sources to III.4 table - PATCH

Modified Principles:
  - III.4 Data Source Traceability: Added PWT and Census Trade to approved sources

Added Sections: None

Removed Sections: None

Renamed Sections: None

Templates Requiring Updates:
  ✅ No template changes needed (data source table is reference, not structural)

Follow-up TODOs: None

Previous Version History:
  1.3.0 (2026-01-31): Added VIII. Visual Design Principles (new article)
  1.2.0 (2026-01-30): Added I.8-I.11 (Tragedy, Metabolic Rift, Terminal Crisis, Pedagogy),
                      II.5-II.6 (AI Observes, State/Engine separation)
  1.1.0 (2026-01-30): Added I.7 Quantitative Accumulation → Qualitative Transformation
  1.0.0 (2026-01-30): Initial ratification with 6 theoretical commitments,
                      4 architecture principles, 5 methodological constraints
================================================================================
-->

# Babylon Constitution

A governing document for the political simulation engine testing MLM-TW political economy against empirical data.

## I. Theoretical Commitments

### 1. Settler-Colonial Frame

Settler colonialism serves as the explanatory frame; gentrification represents internal colonization post-frontier. The principal contradiction within U.S. borders is between imperialism and oppressed nations, NOT capital versus labor.

**Rationale**: Class analysis without colonial analysis misreads the U.S. formation. The white working class occupies a structurally different position than colonized nations within U.S. borders.

### 2. Imperial Rent (Φ)

Value transfers from periphery to core through price mechanisms that do not reflect actual labor-time ratios. Φ comprises three components:

1. **Unequal Exchange** (Emmanuel-Amin): Price differentials between core and periphery commodities
1. **Externalized Reproductive Labor** (Meillassoux): Periphery bears costs of labor power reproduction
1. **Domestic Shadow Labor** (Fortunati): Unwaged reproductive work within core households

Φ explains core working class pacification—this is the labor aristocracy mechanism. When W_c > V_c (core wages exceed value produced), the difference is imperial rent extracted from periphery.

**Rationale**: Without Φ, the relative quiescence of core proletariats is inexplicable. Φ provides the material basis for labor aristocracy.

### 3. TRPF with Counter-Tendencies

The tendency of the rate of profit to fall (TRPF) operates continuously; counter-tendencies (especially imperial extraction) offset it. Piketty's stable r ≈ 4-5% is the NET result of tendency plus counter-tendency, not absence of tendency.

**Implementation Requirement**: The simulation MUST model both the falling tendency AND counter-tendencies separately, then compute net r. A stable r MUST emerge from the interaction, not be assumed.

### 4. George Jackson Bifurcation

Crisis produces either fascist OR revolutionary outcomes depending on network topology. Agitation without solidarity organization produces fascism. The key variable: whether solidaristic edges cross the colonial/racial divide.

**Formula**: When wages fall and P(S|A) drops, agitation energy routes to either:

- Fascism (+1 ideology drift) if solidarity edges are absent
- Revolution (-1 ideology drift) if solidarity edges connect across the colonial divide

**Rationale**: Jackson's analysis from prison: white workers lacking solidarity connections with colonized workers default to fascism under economic stress.

**Corollary (Warsaw Ghetto Dynamic)**: When genocide becomes certain, P(S|A) → 0 regardless of material conditions. Compliance offers no survival when elimination is the policy. Even atomized populations with zero solidarity infrastructure revolt when facing certain death—not because revolution offers good odds, but because acquiescence offers none.

**Hegemonic Function**: A primary purpose of ideological hegemony is to prevent and delay the masses from realizing P(S|A) → 0. The system maintains the illusion that compliance offers survival—"work will set you free," "just follow the rules," "this is temporary"—precisely because the moment this illusion breaks, revolt becomes the only rational choice regardless of organization level. Ideology is not false consciousness for its own sake; it is a load-bearing structure preventing the Warsaw Ghetto Dynamic from triggering.

Historical examples: Warsaw Ghetto Uprising (1943), Sobibor revolt (1943), Treblinka revolt (1943), Auschwitz Sonderkommando revolt (1944).

### 5. Department III (Reproductive Labor)

Feminist Marxist correction to Marx's two-department reproduction schema. Reproductive labor produces labor power itself but is systematically priced at zero (g₃₃ → 0).

**Crisis Mechanism**: As reproductive labor becomes visible (g₃₃ → 1), the shadow subsidy collapses, compressing profit rates. This is structural crisis independent of TRPF.

**Implementation Requirement**: The reproduction tensor MUST include Department III. Scenarios where g₃₃ rises MUST produce profit compression.

### 6. Solidarity as Edge Mode

Solidarity is NOT a quantity you accumulate; it is a qualitative relationship type. Four edge modes define class relationships:

| Mode          | Description                                         |
| ------------- | --------------------------------------------------- |
| EXTRACTIVE    | Value flows unilaterally (exploitation)             |
| TRANSACTIONAL | Exchange at approximate equivalence                 |
| SOLIDARISTIC  | Mutual aid, shared risk, consciousness transmission |
| ANTAGONISTIC  | Active opposition, repression, violence             |

Organizing transforms edge TYPES, not weights. A transactional relationship becoming solidaristic is a qualitative phase transition, not a quantitative increment.

### 7. Quantitative Accumulation → Qualitative Transformation

State changes follow the dialectical law: gradual quantitative change produces sudden qualitative transformation at threshold crossing. This is NOT continuous gradation—it is phase transition.

**Quantities accumulate:**

- Resilience on edges (organizing work adds increments)
- Material pressure on nodes (exploitation, immiseration)
- Crisis intensity (systemic stress buildup)
- Consciousness coordinates (drift toward attractors)

**Qualities transform discretely:**

- Edge modes: TRANSACTIONAL → SOLIDARISTIC (via sustained mutual aid)
- Edge modes: SOLIDARISTIC → ANTAGONISTIC (via betrayal, not decay)
- Class position: Labor Aristocracy → Lumpen (when V_produced < V_reproduction)
- System phase: Accommodation-viable → Rupture (when P(S|R) > P(S|A))

**Implementation Requirements:**

1. **Thresholds must be explicit.** Every qualitative transformation has a triggering condition. Document the threshold and what crosses it.

1. **Transformations are discrete events.** When resilience exceeds crisis_intensity, the edge HOLDS (no change). When it doesn't, the edge DEGRADES (mode shift). There is no "partially degraded" state.

1. **Hysteresis may apply.** The threshold for transformation in one direction may differ from the reverse. Building solidarity is harder than breaking it. This asymmetry is real, not a modeling convenience.

1. **No continuous quality gradients.** An edge is SOLIDARISTIC or it is not. A class position is Proletarian or it is not. Representing qualities as floats on a spectrum is a category error. Use enums for qualities, floats for quantities.

**Rationale:** This principle prevents two errors:

- **Economism** — treating qualitative relationships as automatically determined by quantitative conditions (solidarity as f(wage_gap) without organizing)
- **Voluntarism** — treating qualitative transformations as possible without quantitative preconditions (solidarity without material basis)

Material conditions constrain; they do not determine. Organizing work accumulates quantitatively until conditions permit qualitative transformation. Neither alone suffices.

### 8. Tragedy of Inevitability

The simulation asks "How does the empire die?" not "Can the empire survive?" Collapse is the default state. Stability is temporary deviation enabled by imperial extraction and ecological drawdown.

**Core Doctrine**: Entropy is irreversible. The player cannot "win" in the traditional sense.

**Player Agency** consists of:

- Accelerating collapse through revolutionary action
- Decelerating collapse through system maintenance (only delays the inevitable)
- Shaping the CHARACTER of collapse (revolutionary vs fascist resolution)

**Implementation Requirements**:

1. **Existence costs calories.** `base_subsistence > 0.0` always. Free existence creates "zombie states" where entities survive indefinitely with near-zero wealth.

1. **Earth remembers wounds.** Extraction causes permanent damage to biocapacity. There is no "renewable extraction" under capitalism—only slower depletion.

1. **Death is real.** When wealth falls below consumption needs, entities die. Population decline is the mechanism by which the system eventually stabilizes (if it does).

**Banned Concepts**:

- Infinite biocapacity (violates thermodynamics)
- Regeneration > Extraction (not possible under capitalism)
- Equilibrium stability (violates TRPF)
- Player "victory" through imperial survival (wrong teleology)

**Rationale**: Without this frame, the simulation becomes an optimization game where sufficiently clever play preserves empire indefinitely. This contradicts both MLM-TW theory and historical materialism.

### 9. Metabolic Rift

Capital accumulation is fundamentally incompatible with ecological sustainability. The "metabolic rift" (Marx, Foster) describes how capitalism systematically extracts more than can be renewed.

**Formula**: ΔBiocapacity = Regeneration - (Extraction × Entropy_Factor)

Where Entropy_Factor > 1.0 reflects thermodynamic inefficiency—extraction always costs more than it yields.

**Overshoot Ratio**: O = Consumption / Biocapacity. When O > 1.0, the system is in ecological overshoot, consuming more than exists.

**Crisis Mechanism**: Unlike TRPF (which operates on profit rates), metabolic rift operates on physical substrate. When biocapacity approaches zero:

- Production becomes impossible (no inputs)
- Subsistence becomes impossible (no calories)
- System collapse is physical, not merely economic

**Implementation Requirement**: The simulation MUST track biocapacity as a depletable resource. Extraction MUST permanently reduce maximum biocapacity (hysteresis). Ecological crisis MUST be an independent collapse vector alongside TRPF.

**Rationale**: TRPF alone allows indefinite extraction if counter-tendencies are strong enough. Metabolic rift provides the physical limit that TRPF cannot escape.

### 10. Terminal Crisis Arc

When peripheral extraction fails and internal extraction proves insufficient, imperial systems face a terminal bifurcation between revolutionary transformation and genocidal stabilization.

**The Arc**: Plantation → Prison → Concentration Camp → Death Camp

| Stage              | Function                  | Value Extracted        | Population Status     |
| ------------------ | ------------------------- | ---------------------- | --------------------- |
| Plantation         | Extract labor             | High                   | Asset (labor power)   |
| Prison             | Extract labor + warehouse | Medium                 | Break-even            |
| Concentration Camp | Pure warehousing          | Zero                   | Liability (pure cost) |
| Death Camp         | Elimination               | Negative (saves costs) | Eliminated            |

**Transition Logic**: Each stage transition occurs when the previous stage becomes unprofitable:

- Plantation → Prison: When labor power costs exceed value extracted
- Prison → Camp: When prison labor is unprofitable
- Camp → Death Camp: When warehousing costs exceed tolerance AND organization < threshold

**The Genocidal Logic**:

```
if cost_of_warehousing > value_of_labor:
    if risk_of_revolt > acceptable_threshold:
        if organization < revolution_threshold:
            decision = GENOCIDE
```

**Implementation Requirement**: The simulation MUST model the carceral turn as a response to imperial rent exhaustion. Labor aristocracy decomposition MUST produce enforcers + internal proletariat. Control ratio (guards:prisoners) MUST be tracked as a crisis indicator.

**Rationale**: Without this arc, the simulation cannot model fascism as a systemic response to imperial decline. The Holocaust was not an aberration—it was the logical endpoint of a system that could no longer exploit profitably.

### 11. Emergent Pedagogy

The game does not prescribe the correct path. The simulation reveals consequences. Revolutionary theory emerges from gameplay, not from lectures.

**Design Principles**:

1. **All strategies are playable.** The player can pursue reformism, adventurism, economism, ultra-leftism, or decolonial revolution. The game does not prevent "incorrect" choices.

1. **The simulation shows why strategies fail.** When the player pursues reformism and the system absorbs their gains, this is not a scripted failure—it is the mathematics of P(S|A) and imperial rent working as designed.

1. **History punishes opportunism.** Short-term tactical gains that compromise long-term revolutionary potential manifest as vulnerabilities during crisis. The player experiences this as gameplay, not as moralizing.

1. **Let players fail, then explain why.** When players fail, they should think "I made a mistake" not "the game cheated." The system is learnable and fair.

1. **Decolonial revolution is the only true victory—but this is emergent, not enforced.** The reason land-back and anti-imperialism are prerequisites for genuine victory is not a design constraint imposed on the game. It is a natural consequence of the theory and the numbers. The player who ignores colonial dynamics wins the revolution and watches the planet continue dying ("You cannot build socialism on stolen land").

**Implementation Requirements**:

1. **No hidden win conditions.** The player can declare victory at any point. The game provides metrics (habitability, exploitation levels, consciousness, control ratios) to evaluate what "victory" means.

1. **All deviations have consequences, not punishments.** Reformism doesn't trigger a "you lose" screen—it produces a scenario where gains are absorbed by the system. The player sees WHY reformism fails.

1. **Theory references follow experience.** Tooltips and theory citations appear AFTER the player has felt the dynamic, not before. "Oh, that's what Lenin meant" not "Lenin said this, now watch."

**Rationale**: The simulation's pedagogical power comes from showing, not telling. A teenager who has never read Marx plays this game and starts asking the right questions—because they watched the imperial circuit consume itself, not because someone told them it would.

## II. Architecture Principles

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

### 3. NetworkX as Discretized Manifold

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

**See Also**: Article VIII (Visual Design Principles) extends this observer pattern to the UI layer.

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
SQLite (cold) → hydrate → WorldState (warm) → to_graph → NetworkX (hot)
                                                              ↓
                                                         [Systems mutate]
                                                              ↓
SQLite (cold) ← dehydrate ← WorldState (warm) ← from_graph ← NetworkX (hot)
```

**Implementation Requirement**: NO database I/O during tick execution. The simulation runs entirely in RAM. Persistence happens before and after, never during.

**Rationale**: This separation enables deterministic testing, easy serialization, and clear reasoning about state transitions. When state and behavior are mixed, bugs hide in the interaction.

## III. Methodological Constraints

### 1. No Magic Constants

Every number MUST trace to either:

- Primitives (concrete labor time, physical quantities)
- Real data sources (see Section III.4)

If a constant cannot be grounded, it does not belong in the simulation. Constants without provenance MUST be flagged and removed.

### 2. Falsifiability Required

Every theoretical claim MUST generate predictions distinguishable from the null hypothesis.

**Before implementing any formula**: Define:

1. What the formula predicts
1. What the null hypothesis predicts
1. What observable difference distinguishes them
1. What data would falsify the formula

Unfalsifiable claims are theoretical assertions, not simulation mechanics.

### 3. Physics Cosplay Prohibition

Tensor notation MUST earn its keep through actual invariance properties.

**Reject if**:

- "Curvature of value-space" without demonstrated coordinate invariance
- "Distance in monetary manifold" without metric tensor justification
- Differential geometry vocabulary without transformation laws

**Accept if**:

- Tensor transforms correctly under basis change
- Geometric structure has economic interpretation
- Notation simplifies rather than obscures

Flag and reject physics cosplay. Mathematical formalism without mathematical content is worse than plain prose.

### 4. Data Source Traceability

Every derived quantity MUST trace to specific federal data sources:

| Source      | Data                                          |
| ----------- | --------------------------------------------- |
| QCEW        | Labor hours by industry/county                |
| Census/ACS  | Demographics, income distribution             |
| BEA         | GDP, input-output tables                      |
| FRED        | Macro indicators, time series                 |
| HIFLD       | Infrastructure, critical facilities           |
| BTS         | Freight flows, transportation                 |
| FCC         | Communications infrastructure                 |
| ATUS        | Time use (reproductive labor proxy)           |
| CDC WONDER  | Mortality (structural violence proxy)         |
| Piketty/WID | Coefficient calibration (wealth distribution) |
| PWT         | ERDI, PPP conversion factors (unequal exchange) |
| Census Trade | Import shares by country of origin              |

New data sources require explicit addition to this list with justification.

### 5. Empirical vs Strategic Separation

**Material conditions** (from data):

- Node attributes (wealth, population, industry composition)
- Constraints (subsistence requirements, ecological limits)
- Extractive edges (derived from input-output flows)

**Strategic intervention** (NOT from data):

- Solidaristic edge existence
- Organizing effects
- Consciousness-raising outcomes

Strategic space is where movement knowledge enters. Statistics cannot tell you where solidarity exists—only where material conditions make it possible or necessary.

## IV. Test Case: Metro Detroit (2010-2025)

### Scope

Wayne County (Detroit proper) vs Oakland County (suburban)

### Timeframe

2010-2025: One complete cycle

### Cycle Phases

1. **Crisis** (2008-2012): Auto industry collapse, mortgage crisis
1. **Devaluation** (2013-2016): Detroit bankruptcy, asset stripping
1. **Recolonization** (2017-2020): Gentrification begins, Quicken Loans HQ
1. **Displacement** (2021-2025): Rising rents, eviction wave

### Validation Targets

| Prediction                     | Observable                             |
| ------------------------------ | -------------------------------------- |
| Wayne = Black internal colony  | Demographic composition, wealth ratios |
| Oakland = white settler suburb | Same metrics, inverse pattern          |
| LA → Lumpen transition         | QCEW employment loss, SNAP enrollment  |
| Gentrification trajectory      | Rent indices, demographic shift        |

### Success Criteria

The model MUST reproduce observed class transitions and gentrification trajectory using only:

- QCEW/Census data as inputs
- Theoretical mechanisms from Section I
- Architecture from Section II

If the model cannot reproduce Detroit 2010-2025, the theory or implementation is wrong.

## V. Scope Control

### 1. Material Base First

Superstructure mechanics (state repression, ideological capture) DEPEND on economic dynamics working correctly.

**Sequence**:

1. Economic extraction (TRPF, Φ)
1. Class formation (survival calculus)
1. Solidarity networks (edge type transformation)
1. THEN repression mechanics

Do NOT implement repression until solidarity networks emerge from class dynamics.

### 2. Zoom Where Data Exists

Fractal architecture allows detailed modeling where data is rich (Detroit) while staying abstract elsewhere.

**Rule**: Resolution level MUST match data availability. Do not over-specify where you cannot validate.

### 3. Flag Scope Creep

Before implementing any proposed feature, verify:

1. Does it trace to a testable prediction against the Detroit case?
1. Does it improve falsifiability?

If neither: DEFER. The feature may be theoretically interesting but is not currently testable.

## VI. Visual Design Principles

This article governs all visual and interaction design decisions. The aesthetic lineage is Constructivist information design—form follows function, art as tool for analysis. We are closer to Bloomberg Terminal than to cyberpunk mood board.

### 1. UI Observes, Never Controls

The UI is a passive observer. It listens for events from the simulation engine and renders them. The UI MUST NOT mutate simulation state directly—it emits intents that the engine processes.

**Implementation Requirements**:

1. **UI runs in main thread, simulation ticks independently.** Use async patterns to ensure UI remains responsive and does not block the simulation loop.

1. **State changes propagate via event bus.** The UI subscribes to relevant events and re-renders affected components. This enables replay, debugging, and the "God Mode" dashboard.

1. **Decoupling is mandatory.** UI components receive WorldState snapshots. They never hold references to mutable engine state.

**Rationale**: This is the visual-layer extension of II.5 (AI Observes, Never Controls). Both narrative and visualization are read-only observers of the mechanical simulation.

### 2. Color as Data

Color encodes meaning. Decorative use is prohibited.

**The Primary Palette** (fixed semantic meaning):

| Token      | Hex     | Semantic Role                     |
| ---------- | ------- | --------------------------------- |
| BLOOD_VOID | #1a0000 | Primary background                |
| BLACK      | #000000 | Deepest background, true absence  |
| CRIMSON    | #dc143c | Power, extraction, bourgeoisie    |
| GOLD       | #ffd700 | Action, solidarity, player agency |
| SILVER     | #c0c0c0 | Mass, proletariat, default text   |
| ASH        | #606060 | Muted, inactive, structural       |

**Semantic Bindings**:

| Element             | Color   | Rationale                   |
| ------------------- | ------- | --------------------------- |
| Bourgeoisie nodes   | CRIMSON | They hold power             |
| Proletariat nodes   | SILVER  | The many, the default       |
| Extraction edges    | CRIMSON | Value flowing to capital    |
| Solidarity edges    | GOLD    | What the player builds      |
| Player actions      | GOLD    | Agency, the active verb     |
| System alerts       | GOLD    | Demands attention           |
| Critical state      | CRIMSON | Threshold breach            |

**Luminosity Encodes Magnitude**: Brighter = more value flow, more labor hours, higher tension. Ambient glow is prohibited unless intensity maps to a quantitative variable.

**Implementation Requirement**: All colors via palette tokens. Hardcoded hex values are prohibited.

### 3. Data-Ink Maximization

Every pixel of luminosity MUST encode data or enable navigation. Erase non-data-ink.

**Escaping Flatland**: The simulation is multivariate. The UI MUST increase dimensionality on the 2D screen through:

- Position (spatial relationships in the graph)
- Size (magnitude)
- Color (class, edge type)
- Saturation (core/periphery position)
- Opacity (activity level)
- Connection density (network topology)

**Micro/Macro Readings**: The user MUST see panorama (whole network topology) and detail (specific node attributes) simultaneously. Possible implementations:

- Overview + detail panels
- Semantic zoom (detail emerges on hover/focus)
- Persistent summary statistics alongside graph view

**Small Multiples for Time**: Prefer static comparison over animation. Show the Detroit trajectory as panels (one per year) rather than a movie. Comparison reveals trend; animation entertains.

When animation is used, it MUST show *process*—value flowing along edges, not just state transitions.

### 4. The Graph Is Primary

The NetworkX graph is the core visual. Node position, size, and connection density ARE the data. Decoration is prohibited. If a node has a border, the border encodes something.

**Verbs Over Nouns**: Babylon models process: extraction, accumulation, crisis, recomposition. The UI MUST visualize verbs (flows, transfers, decay) not just nouns (current wealth).

When displaying the "Shock Doctrine" pattern, visually link cause (crash) to effect (radicalization). Causality MUST be legible.

**Topology Is Visible**: The user MUST be able to perceive:

- Percolation ratio (solidarity network connectivity)
- Clustering (who is connected to whom)
- Bottlenecks (critical nodes whose removal fragments the network)
- The George Jackson bifurcation conditions (solidarity topology vs. agitation level)

### 5. Signifier Legibility

If a node can be inspected, it MUST indicate this on hover (subtle GOLD border or brightness increase). If a territory permits an action, the interface MUST signify the capability.

**No Hidden Verbs**: Every interactive element MUST have a visible affordance. The player should never discover functionality by accident.

**Implementation Requirement**: All clickable/hoverable elements MUST have explicit visual feedback states.

### 6. Semantic Invariance

Visual vocabulary is invariant. If CRIMSON edges mean extraction in one view, they mean extraction in every view.

**No Context-Dependent Color Semantics**: A color binding established in VI.2 applies to all views, all dashboards, all panels. Redefining color meaning per-context is prohibited.

**Rationale**: Semantic drift creates cognitive load. The player learns the visual language once; it stays consistent.

### 7. Smallest Effective Difference

Use the minimum visual distinction necessary.

- Dormant edges: low opacity
- Active solidarity edges: full GOLD
- Transactional edges: ASH

Do NOT use garish distinctions where subtle ones suffice. Visual hierarchy should guide attention, not overwhelm.

**Rationale**: Tufte's principle—maximize data-ink, minimize chart-junk. Subtle distinctions that communicate effectively are preferable to loud distinctions that distract.

### 8. Feedback and Feedforward

**Feedback**: Every state change requires visual confirmation. When the player funds a solidarity network, show the resulting change in percolation ratio. When extraction occurs, show value flowing along CRIMSON edges.

Feedback is immediate. The user MUST never wonder "did that work?"

**Feedforward**: Before committing an action, show what will happen. If eviction will fragment a network, preview the fragmentation. The conceptual model of the simulation MUST be externalized in the interface.

**Continuous Legibility**: Critical system state is always visible:

- Imperial Rent Pool (the "gas tank")
- Repression Level (the "heat")
- Profit rate trajectory
- Solidarity percolation ratio

These are NOT hidden in menus. They are persistent.

### 9. Typography

**Monospace Dominates**: Primary typefaces: Roboto Mono, Source Code Pro. This reinforces that Babylon is analytical infrastructure, not consumer software.

**Hierarchy**:

- Node labels: Monospace, SILVER
- Active/selected labels: Monospace, GOLD
- System alerts: Geometric sans-serif (Futura or equivalent), GOLD
- Axis labels and annotations: Monospace, ASH

**Annotation Over Decoration**: If something needs explanation, label it directly on the graphic. Avoid legends in corners. Direct labeling reduces eye movement and cognitive load.

**Implementation Requirement**: No more than two typeface families. Monospace + one sans-serif for alerts.

### 10. Visual Prohibitions

The following are explicitly forbidden:

1. **Decorative glow or bloom** — unless luminosity encodes a variable
1. **Hardcoded colors** — all colors via palette tokens
1. **Chartjunk** — decorative elements carrying no data
1. **Hidden state** — critical variables MUST be persistently visible
1. **Animation for its own sake** — animation MUST show process
1. **Legends in corners** — prefer direct annotation
1. **Context-dependent color meaning** — semantic invariance required
1. **Mood over meaning** — aesthetic choices MUST be semantically grounded

## VII. Anti-Patterns

The following patterns MUST be rejected upon detection:

### 1. Solidarity as Scalar

**Wrong**: `solidarity_points += organizing_action`

**Right**: Edge type transforms from TRANSACTIONAL to SOLIDARISTIC

Solidarity is relational, not quantitative.

### 2. Union Density as Revolutionary Indicator

US unions are largely labor aristocracy institutions. High union density in the core correlates with imperial rent distribution, not revolutionary potential.

Union presence MAY correlate with organizational capacity but NOT with revolutionary consciousness without examining edge types.

### 3. Determinism from Material Conditions

Material conditions CONSTRAIN; they do not DETERMINE.

**Wrong**: `if material_conditions_x: revolution()`

**Right**: Material conditions set P(S|A) and P(S|R). Outcomes depend on strategic choices within those constraints.

### 4. Ungrounded Tensor Notation

See Section III.3. Tensor formalism without transformation laws is rejected.

### 5. Claims Without Falsifiability

See Section III.2. Theoretical assertions without testable predictions are not simulation mechanics.

### 6. Constants Without Data Sources

See Section III.1 and III.4. Every number must trace to primitives or data.

### 7. Superstructure Before Base

See Section V.1. Implement material dynamics before ideological or repressive mechanics.

### 8. Decorative Visualization

See Section VI.10. Visual elements that carry no data are prohibited. Every visual choice MUST encode meaning or enable navigation.

## VIII. Governance

### Amendment Procedure

1. Propose amendment with rationale
1. Demonstrate consistency with existing principles or explicit supersession
1. Update dependent artifacts (templates, specs)
1. Increment version per semantic versioning

### Version Policy

| Change Type                       | Version Increment |
| --------------------------------- | ----------------- |
| Principle removal or redefinition | MAJOR             |
| New principle or section          | MINOR             |
| Clarification, wording fix        | PATCH             |

### Compliance Review

All features, formulas, and systems MUST be verifiable against this constitution.

**Review triggers**:

- New system implementation
- Formula modification
- Data source addition
- Scope expansion
- **UI component implementation** (must verify against Article VI)

Non-compliant code MUST be flagged and corrected before merge.

______________________________________________________________________

**Version**: 1.3.1 | **Ratified**: 2026-01-30 | **Last Amended**: 2026-02-05
