# Babylon UI Constitution

This document governs all visual and interaction design decisions for the Babylon simulation engine. It serves as binding precedent for human designers and LLM agents alike.

## Preamble: What This Interface Is

Babylon is analytical infrastructure for understanding imperial political economy. The interface communicates: "This is how extraction actually works, and here's the math." The rebellion is in what the tool reveals, not in how it looks.

The aesthetic lineage is Constructivist information design — form follows function, art as tool for the movement. We are closer to Bloomberg Terminal than to cyberpunk mood board.

______________________________________________________________________

## Article I: Color as Data

**§1.1 The Primary Palette**

The primary palette carries fixed semantic meaning throughout the interface. These colors are the default vocabulary.

| Token      | Hex     | Semantic Role                     |
| ---------- | ------- | --------------------------------- |
| BLOOD_VOID | #1a0000 | Primary background                |
| BLACK      | #000000 | Deepest background, true absence  |
| CRIMSON    | #dc143c | Power, extraction, bourgeoisie    |
| GOLD       | #ffd700 | Action, solidarity, player agency |
| SILVER     | #c0c0c0 | Mass, proletariat, default text   |
| ASH        | #606060 | Muted, inactive, structural       |

**§1.2 The Extended Palette**

The extended palette is available when the primary palette is insufficient — cartographic rendering, differentiating multiple data series, or encoding dimensions beyond the primary semantic categories. Extended colors must not contradict primary semantics.

| Token  | Hex     | Permitted Uses                                    |
| ------ | ------- | ------------------------------------------------- |
| FOREST | #228b22 | Geographic (vegetation, land use), positive delta |
| LIME   | #32cd32 | Geographic (highlight), success state             |
| STEEL  | #4169e1 | Geographic (water, infrastructure), properties    |
| SKY    | #6495ed | Geographic (water highlight), secondary info      |
| VIOLET | #8b008b | Differentiation, import/export flows              |
| ORCHID | #da70d6 | Differentiation, constants, magnitude             |
| TEAL   | #00ced1 | Geographic (water), type/class indicators         |
| RUST   | #b8860b | Annotations, decorators, historical               |
| EMBER  | #ff6b6b | Error states, warnings, bright accent             |

**§1.3 Palette Hierarchy**

1. Primary palette is always preferred
1. Extended palette requires justification (the primary palette cannot express the needed distinction)
1. No colors outside these two palettes without constitutional amendment
1. When primary and extended colors appear together, primary colors dominate visual weight

**§1.2 Semantic Bindings**

Color encodes meaning. Decorative use is prohibited.

| Element             | Color              | Rationale                   |
| ------------------- | ------------------ | --------------------------- |
| Bourgeoisie nodes   | CRIMSON            | They hold power             |
| Proletariat nodes   | SILVER             | The many, the default       |
| Extraction edges    | CRIMSON            | Value flowing to capital    |
| Solidarity edges    | GOLD               | What the player builds      |
| Transactional edges | ASH                | Neutral exchange            |
| Antagonistic edges  | CRIMSON            | Conflict, active opposition |
| Core regions        | Full saturation    | Center of accumulation      |
| Periphery regions   | Reduced saturation | Margins of extraction       |
| Player actions      | GOLD               | Agency, the active verb     |
| System alerts       | GOLD               | Demands attention           |
| Critical state      | CRIMSON            | Threshold breach            |

**§1.3 Luminosity Encodes Magnitude**

Brightness is not decoration. Brighter = more value flow, more labor hours, higher tension. Ambient glow is prohibited unless intensity maps to a quantitative variable.

**§1.4 Smallest Effective Difference**

Use the minimum visual distinction necessary. Dormant edges: low opacity. Active solidarity edges: full GOLD. Do not use garish distinctions where subtle ones suffice.

______________________________________________________________________

## Article II: Information Density

**§2.1 Data-Ink Maximization**

Every pixel of luminosity must encode data or enable navigation. Erase non-data-ink. If a grid is used, it must be implicit (low contrast) so it does not compete with data.

**§2.2 Escaping Flatland**

The simulation is multivariate. The UI must increase dimensionality on the 2D screen through:

- Position (spatial relationships in the graph)
- Size (magnitude)
- Color (class, edge type)
- Saturation (core/periphery position)
- Opacity (activity level)
- Connection density (network topology)

**§2.3 Micro/Macro Readings**

The user must see panorama (whole network topology) and detail (specific node attributes) simultaneously. This is non-negotiable. Possible implementations:

- Overview + detail panels
- Semantic zoom (detail emerges on hover/focus)
- Persistent summary statistics alongside graph view

**§2.4 Small Multiples for Time**

Prefer static comparison over animation. Show the Detroit trajectory as panels (one per year) rather than a movie. Comparison reveals trend; animation entertains.

When animation is used, it must show *process* — value flowing along edges, not just state transitions.

______________________________________________________________________

## Article III: The Graph Is Primary

**§3.1 Nodes and Edges Are Data**

The NetworkX graph is the core visual. Node position, size, and connection density *are* the data. Decoration is prohibited. If a node has a border, the border encodes something.

**§3.2 Verbs Over Nouns**

Babylon models process: extraction, accumulation, crisis, recomposition. The UI must visualize verbs (flows, transfers, decay) not just nouns (current wealth).

When displaying the "Shock Doctrine" pattern, visually link cause (crash) to effect (radicalization). Causality must be legible.

**§3.3 Topology Is Visible**

The user must be able to perceive:

- Percolation ratio (solidarity network connectivity)
- Clustering (who is connected to whom)
- Bottlenecks (critical nodes whose removal fragments the network)
- The George Jackson bifurcation conditions (solidarity topology vs. agitation level)

______________________________________________________________________

## Article IV: Interaction

**§4.1 Signifiers**

If a node can be inspected, it must indicate this on hover (subtle GOLD border or brightness increase). If a territory permits an action, the interface must signify the capability. No hidden verbs.

**§4.2 Feedback**

Every state change requires visual confirmation. When the player funds a solidarity network, show the resulting change in percolation ratio. When extraction occurs, show value flowing along CRIMSON edges.

Feedback is immediate. The user must never wonder "did that work?"

**§4.3 Feedforward**

Before committing an action, show what will happen. If eviction will fragment a network, preview the fragmentation. The conceptual model of the simulation must be externalized in the interface.

**§4.4 Continuous Legibility**

Critical system state is always visible:

- Imperial Rent Pool (the "gas tank")
- Repression Level (the "heat")
- Profit rate trajectory
- Solidarity percolation ratio

These are not hidden in menus. They are persistent.

______________________________________________________________________

## Article V: Typography

**§5.1 Monospace Dominates**

Primary typefaces: Roboto Mono, Source Code Pro. This reinforces that Babylon is analytical infrastructure, not consumer software.

**§5.2 Hierarchy**

- Node labels: Monospace, SILVER
- Active/selected labels: Monospace, GOLD
- System alerts: Geometric sans-serif (Futura or equivalent), GOLD
- Axis labels and annotations: Monospace, ASH

**§5.3 Annotation Over Decoration**

If something needs explanation, label it directly on the graphic. Avoid legends in corners. Direct labeling reduces eye movement and cognitive load.

______________________________________________________________________

## Article VI: Architecture

**§6.1 Observer Pattern**

The UI is a passive observer. It listens for events from the simulation engine and renders them. The UI does not mutate simulation state directly — it emits intents that the engine processes.

**§6.2 Decoupling**

The UI runs in the main thread (PyQt6). The simulation ticks independently. Use async patterns to ensure the UI remains responsive and does not block the simulation loop.

**§6.3 Strict Typing**

All data passed to UI renderers must be validated Pydantic models (SocialClass, Territory, Relationship). Untyped dictionaries are prohibited at the render boundary.

**§6.4 Event Bus**

State changes propagate via event bus. The UI subscribes to relevant events and re-renders affected components. This enables replay, debugging, and the "God Mode" dashboard.

______________________________________________________________________

## Article VII: Meaningful Play

**§7.1 Discernability**

When the player takes an action, the outcome must be visible in the UI. If funding a solidarity network, show the topology change. If extraction increases, show the flow.

**§7.2 Integration**

Player actions must affect the global system in legible ways. No actions without consequences. No consequences invisible to the player.

**§7.3 The State Knows Where You Are**

High-profile activities increase "heat" on territory nodes. This must be visually apparent — the player should feel surveillance as a mechanic, not discover it through failure.

**§7.4 Systemic Consistency**

Visual vocabulary is invariant. If CRIMSON edges mean extraction in one view, they mean extraction in every view. No context-dependent color semantics.

______________________________________________________________________

## Article VIII: Prohibitions

The following are explicitly forbidden:

1. **Decorative glow or bloom** — unless luminosity encodes a variable
1. **Hardcoded colors** — all colors via palette tokens
1. **Chartjunk** — decorative elements carrying no data
1. **Hidden state** — critical variables must be persistently visible
1. **Untyped data at render boundary** — Pydantic models only
1. **Animation for its own sake** — animation must show process
1. **Legends in corners** — prefer direct annotation
1. **Context-dependent color meaning** — CRIMSON always means the same thing
1. **More than two typeface families** — monospace + one sans-serif for alerts
1. **Mood over meaning** — aesthetic choices must be semantically grounded

______________________________________________________________________

## Amendments

This constitution may be amended when:

- Empirical user testing reveals a principle harms usability
- New simulation mechanics require visual vocabulary expansion
- The color palette proves insufficient for required distinctions

Amendments require explicit rationale documenting why the original principle failed and how the amendment resolves the failure without violating other articles.
