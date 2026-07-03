# Article VII: Visual Design Principles

> Annex to [Babylon Constitution](../constitution.md). This file contains the full visual design system, palette definitions, and implementation requirements.

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

The graph is the core visual. Node position, size, and connection density ARE the data. Decoration is prohibited. If a node has a border, the border encodes something.

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
