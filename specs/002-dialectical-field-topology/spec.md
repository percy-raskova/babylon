# Feature Specification: Dialectical Field Topology

**Feature Branch**: `002-dialectical-field-topology`
**Created**: 2026-02-25
**Status**: Draft
**Input**: Spec prompt `ai-docs/spec-prompts/spec-019-dialectical-field-topology.md`, `ai-docs/spec-prompts/edge-mode-completeness-analysis.md`
**Dependencies**: Feature 017 (Tick Dynamics), Feature 018 (Crisis/Devaluation), Feature 016 (Class Dynamics)

---

## Problem Statement

Babylon's simulation currently treats node-level quantities (exploitation rate, immiseration, imperial rent) and discrete state transitions (edge mode changes, consciousness shifts, crisis triggers) as separate systems with ad hoc coupling. The tick loop updates quantities then checks thresholds, but lacks a unified framework connecting *where* contradictions concentrate, *how* they propagate across the graph, and *why* qualitative transitions occur at specific nodes and not others.

The theoretical foundation exists: Mao's *On Contradiction* establishes that quantitative accumulation gives rise to qualitative change, that every process contains a principal contradiction, and that the character of a contradiction (tending toward or away from antagonism) determines outcomes. What is missing is the formal machinery to compute these concepts on the graph as field operations (gradients, Laplacians, curvature) unified with the existing categorical edge mode system and tick-keyed temporal history.

## Core Insight

The dialectical categories (quantity, quality, character of contradiction, principal vs. secondary contradiction, antagonistic vs. non-antagonistic) are recoverable from a single time series and its spatial/temporal derivatives:

- **Magnitude of contradiction** = field value f(i, t) at node i, tick t
- **Character** = temporal first derivative df/dt (intensifying or being sublated)
- **Tendency toward antagonism** = temporal second derivative d2f/dt2 (accelerating or decelerating)
- **Spatial concentration** = graph Laplacian Lf(i) (pressure peak or trough relative to neighbors)
- **Topological character** = Ollivier-Ricci curvature k(i) (bottleneck vs. resilient neighborhood structure)
- **Qualitative transition** = discrete state change when threshold conditions on the above are met

Quantities flux continuously. States transition discretely. The transition conditions incorporate both magnitude *and* trajectory (derivatives), grounded in the topology (curvature). This is the architectural principle.

---

## Clarifications

### Session 2026-02-25

- Q: What computational criterion determines whether antagonism from CO-OPTIVE breakdown is directed "upward" (revolutionary) or "laterally" (fascist)? → A: Solidarity magnitude comparison — antagonism is directed upward if total solidarity strength across the colonial divide exceeds total within-group solidarity strength at the co-opted node; lateral (fascist) otherwise.
- Q: Which contradiction fields does a CO-OPTIVE edge suppress? → A: Per-edge configurable — each CO-OPTIVE edge specifies which contradiction fields it suppresses (e.g., imperial rent edge suppresses exploitation + immiseration; welfare edge suppresses immiseration only).
- Q: Is the set of contradiction fields fixed at four or extensible? → A: Open set — core computation (gradient, Laplacian, derivatives, principal contradiction) is field-name-agnostic. New fields can be registered without changing computation logic. Four initial fields ship with the feature.

---

## User Scenarios & Testing

### User Story 1 - Contradiction Field Computation (Priority: P1)

As a simulation researcher, I want every social-class node to carry named contradiction fields computed each tick from existing economic outputs, so that I can track where contradictions concentrate and how their magnitude evolves over time.

**Why this priority**: Without contradiction fields defined and computed per tick, no spatial or temporal analysis is possible. This is the foundational data layer upon which all other stories depend.

**Independent Test**: Can be fully tested by running a 10-tick simulation and querying field values at each node per tick. Delivers the ability to see contradiction magnitude across the graph.

**Acceptance Scenarios**:

1. **Given** a simulation with the Detroit metro graph, **When** a 10-tick run completes, **Then** every social-class node has a defined value for all four contradiction fields (exploitation, immiseration, imperial rent, displacement) at every tick, with no undefined values after tick 0.
2. **Given** economic calculator outputs for a node, **When** the contradiction field layer computes exploitation contradiction, **Then** the value is derived from the exploitation rate (e = s/v) without duplicating the economic calculation.
3. **Given** a node with known economic conditions, **When** the field layer computes displacement contradiction, **Then** the value is derived from the population change rate.

______________________________________________________________________

### User Story 2 - Spatial and Temporal Derivatives (Priority: P1)

As a simulation researcher, I want spatial derivatives (gradient along edges, Laplacian at nodes) and temporal derivatives (first and second) computed each tick, so that I can understand the rate, direction, and acceleration of contradiction dynamics.

**Why this priority**: Derivatives are the core analytical tool that transforms raw field values into actionable dialectical categories (character, tendency, spatial concentration). Without them, the system cannot determine whether contradictions are intensifying or being sublated.

**Independent Test**: Can be fully tested by setting up a graph with known field values and verifying gradients, Laplacian values, and temporal finite differences match analytically expected results.

**Acceptance Scenarios**:

1. **Given** two connected nodes with exploitation contradiction values f(i) and f(j), **When** the gradient is computed, **Then** the result equals f(j) - f(i) and is signed/directional.
2. **Given** a high-exploitation node (Wayne County proletariat), **When** the graph Laplacian is computed, **Then** the value is negative (pressure peak relative to neighbors).
3. **Given** a test case with known linear field growth over 3 ticks, **When** temporal derivatives are computed, **Then** df/dt matches the analytically expected value (error < 1e-6).
4. **Given** only 1 tick of history, **When** d2f/dt2 is requested, **Then** the result is reported as undefined (not zero).

______________________________________________________________________

### User Story 3 - Principal Contradiction Identification (Priority: P2)

As a simulation researcher, I want the system to identify the principal contradiction at each tick (the field with the largest maximum absolute first derivative), so that I can understand which contradiction is driving the dynamics at any given moment.

**Why this priority**: Identifying the principal contradiction is a core theoretical requirement from Mao's *On Contradiction*. It enables researchers to track which force is dominant and when dominance shifts, which is essential for understanding qualitative transitions.

**Independent Test**: Can be fully tested by configuring a scenario where one field has the largest absolute df/dt, then switching which field dominates, and verifying the system correctly identifies the switch.

**Acceptance Scenarios**:

1. **Given** a simulation where exploitation has the largest |df/dt| at tick 5, **When** the tick summary is queried, **Then** exploitation is identified as the principal contradiction.
2. **Given** a scenario where the principal contradiction switches from exploitation to immiseration at tick 8, **When** the tick summaries are compared, **Then** the switch is recorded as a significant event.
3. **Given** two fields with identical maximum |df/dt|, **When** principal contradiction is determined, **Then** the field with the larger total magnitude across all nodes is selected. If still tied, exploitation is preferred.

______________________________________________________________________

### User Story 4 - Compound State Transition Predicates (Priority: P2)

As a developer extending Babylon, I want to specify discrete state transition conditions (edge mode changes, consciousness shifts, crisis triggers) as declarative predicates over field values and their derivatives, so that I can add new transition types without modifying tick-loop logic.

**Why this priority**: Declarative predicates decouple transition logic from the execution engine, enabling extensibility and testability. This replaces ad hoc threshold checks with a unified framework.

**Independent Test**: Can be fully tested by defining a compound predicate (e.g., f > 0.7 AND df/dt > 0 AND Lf < 0 AND k < -0.1), registering it for an edge transition, and verifying it fires only when all conjuncts are satisfied.

**Acceptance Scenarios**:

1. **Given** a predicate defined as `f > 0.7 AND df/dt > 0 AND Lf < 0 AND k < -0.1`, **When** registered as the condition for EXTRACTIVE to ANTAGONISTIC transition, **Then** the transition fires at the correct tick when all conditions converge.
2. **Given** a predicate where the curvature condition is unmet but all others are met, **When** the tick advances, **Then** no transition fires.
3. **Given** a predicate referencing d2f/dt2 at tick 1 (insufficient history), **When** evaluated, **Then** the derivative conjunct evaluates to False and the predicate does not fire.

______________________________________________________________________

### User Story 5 - Continuity Accounting (Priority: P3)

As a political economy theorist, I want a per-tick continuity residual computed for each contradiction field, so that I can test the displacement hypothesis (contradiction displaced rather than resolved) against Detroit data.

**Why this priority**: Continuity accounting validates the theoretical integrity of the simulation. It is a diagnostic tool, not a hard constraint, and is needed for empirical validation but not for core simulation execution.

**Independent Test**: Can be fully tested by running a closed system (no source/sink mechanisms) and verifying that total contradiction is conserved across all nodes, or by running an open scenario and verifying that non-zero residuals are flagged with named mechanisms.

**Acceptance Scenarios**:

1. **Given** a closed test scenario with no source/sink mechanisms, **When** the exploitation field evolves for 10 ticks, **Then** the total contradiction across all nodes remains constant within floating-point tolerance.
2. **Given** a run where Wayne County exploitation contradiction decreases between tick 10 and 20, **When** continuity residuals are summed, **Then** unaccounted residuals are flagged with diagnostics identifying which nodes gained or lost contradiction without a named mechanism.
3. **Given** a node where contradiction decreases with a named mechanism (e.g., "wage increase"), **When** the residual is computed, **Then** the named mechanism accounts for the decrease and the residual is near zero.

______________________________________________________________________

### User Story 6 - Ollivier-Ricci Curvature as Structural Context (Priority: P3)

As a simulation researcher, I want Ollivier-Ricci curvature computed for each edge as a structural property (recomputed only when topology changes), so that I can understand how graph structure affects gradient persistence and dissipation.

**Why this priority**: Curvature provides the topological context that determines whether contradictions persist (bottleneck topology) or dissipate (redundant topology). It is valuable but computed infrequently (only on topology change), making it lower urgency than per-tick computations.

**Independent Test**: Can be fully tested by computing curvature on a known graph topology and comparing against previously validated values from the project's Ricci analysis dataset.

**Acceptance Scenarios**:

1. **Given** graphs with analytically known curvature (complete graph K4, path graph P4, star graph S4), **When** Ollivier-Ricci curvature is computed, **Then** values match analytically expected curvature within floating-point tolerance (positive for complete graphs, negative for bridge edges in path graphs).
2. **Given** no topology changes between ticks 5 and 10, **When** curvature is queried at tick 10, **Then** the cached values from tick 5 are returned without recomputation.
3. **Given** a node added to the graph at tick 7, **When** the next curvature computation runs, **Then** all affected edges have updated curvature values.

______________________________________________________________________

### User Story 7 - Detroit Metro Empirical Validation (Priority: P3)

As an empirical researcher, I want to compare computed field values and gradients against QCEW-derived quantities for Metro Detroit (2010-2025), so that I can assess whether the field framework reproduces known economic geography.

**Why this priority**: Empirical validation is essential for theoretical credibility but depends on all prior stories being functional. It is the capstone validation, not a foundational requirement.

**Independent Test**: Can be fully tested by loading QCEW data for Wayne and Oakland counties and verifying that exploitation gradients and temporal derivative patterns match known economic geography.

**Acceptance Scenarios**:

1. **Given** QCEW data loaded for Wayne and Oakland counties, **When** the exploitation field is computed, **Then** Wayne County nodes consistently show higher exploitation values than Oakland County nodes.
2. **Given** the same data, **When** the exploitation field gradient along the Wayne-to-Oakland edge is computed, **Then** the gradient is negative (exploitation decreasing from periphery to core).
3. **Given** Wayne County temporal derivatives for 2010-2014 (post-crisis recovery), **When** d2f/dt2 is computed, **Then** it is positive (accelerating contradiction), and for 2018-2022 it is negative (decelerating), consistent with the gentrification timeline.

______________________________________________________________________

### User Story 8 - CO-OPTIVE Edge Mode and the George Jackson Bifurcation (Priority: P2)

As a simulation researcher, I want CO-OPTIVE edges to model relationships where a more powerful party offers material concessions in exchange for political quiescence (imperial rent to labor aristocracy, welfare state to working class, reform as fascist mechanism), so that I can trace how the breakdown of co-optation produces either revolutionary or fascist outcomes depending on solidarity topology.

**Why this priority**: The CO-OPTIVE mode is the primary mechanism through which the George Jackson bifurcation is determined *before* crisis arrives. Without it, the model cannot distinguish between a stable pre-crisis period (co-optation intact) and an unstable one (co-optation eroding), and cannot predict when the bifurcation becomes active. It is essential for the field dynamics to be theoretically complete but depends on the field computation infrastructure (US1, US2) being functional.

**Independent Test**: Can be fully tested by configuring a graph with CO-OPTIVE edges, verifying that df/dt suppression operates correctly during stable co-optation, then triggering co-optation breakdown and verifying the latent contradiction release produces a df/dt spike that correctly routes through the bifurcation based on solidarity topology.

**Acceptance Scenarios**:

1. **Given** a CO-OPTIVE edge from imperial system to core working class with material concessions flowing, **When** the exploitation contradiction field is computed at the co-opted node, **Then** df/dt is suppressed proportional to the concession magnitude compared to the same node without co-optation.
2. **Given** stable co-optation suppressing exploitation df/dt, **When** the principal contradiction is identified, **Then** the principal contradiction is something other than exploitation (e.g., displacement or immiseration) because exploitation's derivative is suppressed.
3. **Given** a crisis event that erodes the material basis for co-optation (declining imperial rent), **When** the CO-OPTIVE edge transitions to ANTAGONISTIC, **Then** the latent contradiction is released as a spike in exploitation df/dt, and exploitation reasserts itself as the principal contradiction.
4. **Given** CO-OPTIVE breakdown where the co-opted node's total solidarity strength across the colonial divide exceeds its within-group solidarity strength, **When** the resulting ANTAGONISTIC edge is evaluated, **Then** antagonism is directed upward (revolutionary potential).
5. **Given** CO-OPTIVE breakdown where the co-opted node's within-group solidarity strength exceeds its cross-divide solidarity strength, **When** the resulting ANTAGONISTIC edge is evaluated, **Then** antagonism is directed laterally (fascist potential).

______________________________________________________________________

### Edge Cases

- **EC-001: Insufficient history for derivatives.** At ticks 0 and 1, second derivatives are undefined. The system returns None (not 0.0) for d2f/dt2 and compound predicates requiring d2f/dt2 cannot fire. Predicates referencing undefined derivatives evaluate to False for that conjunct.
- **EC-002: Isolated nodes.** A node with no edges has an undefined Laplacian (no neighbors to sum over). The system returns 0.0 for Lf at isolated nodes and logs a warning. Predicates referencing Lf at isolated nodes use 0.0.
- **EC-003: Simultaneous transition eligibility.** If multiple edge mode transitions are eligible at the same tick for the same edge, priority is determined by the transition topology's priority ordering. Transitions driven by crisis events take priority over transitions driven by organizing events.
- **EC-004: Principal contradiction tie.** If two contradiction fields have identical maximum |df/dt|, the field with the larger total magnitude across all nodes is selected. If still tied, exploitation is preferred by default (structural primacy per Marx).
- **EC-005: Curvature on single-edge nodes.** Nodes connected by a single edge have only one curvature value. Mean curvature equals that value. This is topologically degenerate (no redundancy), and curvature will typically be strongly negative (bottleneck).
- **EC-006: Division by zero in Ollivier-Ricci.** If a node has degree 1, the Wasserstein distance computation requires a uniform distribution over the single neighbor plus the node itself. The implementation handles this per the standard Ollivier formulation with self-loop probability alpha.
- **EC-007: Field value explosion.** If any contradiction accumulator exceeds a configurable maximum bound (default: 10.0 on normalized scale), a diagnostic is logged and the value is clamped. This indicates a modeling error or runaway feedback loop.
- **EC-008: CO-OPTIVE breakdown latent contradiction spike.** When a CO-OPTIVE edge transitions away, the accumulated latent contradiction (suppressed df/dt over the duration of co-optation) is released. The resulting df/dt spike may temporarily exceed the normal range. The system MUST handle this spike without triggering field value explosion (EC-007) by accounting for the latent release as a named mechanism in continuity accounting.
- **EC-009: Multiple CO-OPTIVE edges at one node.** A node may be co-opted by multiple parties simultaneously (e.g., receiving both imperial rent and welfare state benefits). The total suppression effect is the sum of individual CO-OPTIVE edge suppressions. When one CO-OPTIVE edge breaks down but others remain, only the portion of latent contradiction attributable to the broken edge is released.
- **EC-010: CO-OPTIVE edge without distributable surplus.** If the co-opting party's surplus falls to zero, the CO-OPTIVE edge cannot be maintained. The system MUST transition the edge to another mode (EXTRACTIVE if power asymmetry remains, ANTAGONISTIC if the co-opted party resists). A CO-OPTIVE edge with zero material flow is an invalid state.

---

## Requirements

### Functional Requirements

#### Contradiction Field

- **FR-001**: System MUST define an extensible set of named contradiction fields, each computed as a scalar value at every social-class node per tick. The field set is open — core computation logic (gradient, Laplacian, temporal derivatives, principal contradiction identification) MUST be field-name-agnostic, allowing new fields to be registered without modifying computation code. Initial fields shipping with this feature: exploitation contradiction (from exploitation rate e = s/v), immiseration contradiction (from real wage trajectory), imperial rent contradiction (from imperial rent differential to graph mean), and displacement contradiction (from population change rate).
- **FR-002**: Each contradiction field value MUST be persisted in tick-keyed history, enabling retrieval of f(i, t) for any node i at any historical tick t within the simulation run.

#### Spatial Derivatives

- **FR-003**: System MUST compute the gradient of each contradiction field along every edge per tick, defined as grad_f(i,j) = f(j) - f(i). The gradient is signed and directional (positive means field increases from source to target).
- **FR-004**: System MUST compute the graph Laplacian of each contradiction field at every node per tick, defined as Lf(i) = sum over neighbors j of [f(j) - f(i)]. Negative Laplacian indicates a local pressure peak; positive indicates a pressure trough.
- **FR-005**: System MUST compute Ollivier-Ricci curvature for each edge. Curvature is a structural property recomputed only when graph topology changes (node/edge addition/removal), not every tick. Values MUST be cached on edge attributes.

#### Temporal Derivatives

- **FR-006**: System MUST compute the first temporal derivative df/dt at each node using backward finite differences from tick-keyed history: df/dt = f(i,t) - f(i,t-1). The second temporal derivative d2f/dt2 = f(i,t) - 2*f(i,t-1) + f(i,t-2). Minimum 2 ticks required for df/dt, 3 ticks for d2f/dt2. Prior to sufficient history, derivatives MUST be reported as undefined (None), not zero.

#### State Transition Predicates

- **FR-007**: Discrete state transitions (edge mode changes, consciousness state changes, crisis triggers) MUST be governed by compound threshold predicates that may reference any combination of: field magnitude f(i,t), first temporal derivative df/dt, second temporal derivative d2f/dt2, graph Laplacian Lf(i), Ollivier-Ricci curvature k of adjacent edges, and edge mode of adjacent edges. Predicates MUST be declaratively specified.

#### Principal Contradiction

- **FR-008**: At each tick, the system MUST identify the principal contradiction: the field whose maximum absolute first derivative |df/dt|_max across all nodes is greatest. The identity MUST be recorded in the tick summary. Changes in principal contradiction between ticks MUST be logged as significant events.

#### Continuity Accounting

- **FR-009**: For each contradiction field, the system MUST compute a per-tick continuity residual at each node: the change in field value minus the net flow implied by gradients along adjacent edges. Non-zero residuals (above configurable threshold) indicate either a named local source/sink mechanism or an unaccounted transfer. Residuals MUST be persisted in tick history.

#### Edge Mode Transition Topology

- **FR-010**: Permissible edge mode transitions MUST be defined as a directed state machine across five modes: EXTRACTIVE, TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC, and CO-OPTIVE. The initial transitions:
  - EXTRACTIVE to ANTAGONISTIC: extraction contested (exploitation contradiction at source exceeds threshold AND df/dt > 0)
  - EXTRACTIVE to TRANSACTIONAL: extraction broken (organizing success event)
  - EXTRACTIVE to CO-OPTIVE: concessions offered to prevent resistance (extracted party's antagonism accumulator exceeds threshold AND extracting party has distributable surplus)
  - TRANSACTIONAL to SOLIDARISTIC: mutual aid established (organizing work event with sustained duration)
  - TRANSACTIONAL to ANTAGONISTIC: market failure (crisis event)
  - TRANSACTIONAL to EXTRACTIVE: power asymmetry emerges (wealth differential exceeds threshold)
  - TRANSACTIONAL to CO-OPTIVE: one party gains enough power to offer above-market benefits for loyalty (power asymmetry increases past threshold)
  - SOLIDARISTIC to TRANSACTIONAL: solidarity degrades under pressure (crisis intensity > edge resilience)
  - SOLIDARISTIC to ANTAGONISTIC: betrayal (betrayal event)
  - ANTAGONISTIC to TRANSACTIONAL: conflict resolved (negotiation or exhaustion event)
  - ANTAGONISTIC to SOLIDARISTIC: shared enemy produces alliance (united front event — requires common external antagonist AND pre-existing transactional edges between parties)
  - ANTAGONISTIC to ANTAGONISTIC: conflict persists (default when no resolution met)
  - ANTAGONISTIC to CO-OPTIVE: conflict resolved through concession rather than victory (negotiation event with asymmetric outcome — one party gives more than it gains). This is "reform" — resolving antagonism through co-optation rather than structural change.
  - CO-OPTIVE to TRANSACTIONAL: co-optation normalizes into pure market relations (concessions become expected "market rate" rather than political pacification). This is successful hegemony — co-optation becomes invisible.
  - CO-OPTIVE to ANTAGONISTIC: **the critical transition** — material basis for co-optation erodes (crisis, declining imperial rent, austerity). Whether resulting antagonism is directed upward (revolutionary) or laterally (fascist) depends on solidarity topology. This is the George Jackson bifurcation operating on CO-OPTIVE breakdown.
  - CO-OPTIVE to SOLIDARISTIC: the rarest and most strategically important transition — co-opted party recognizes co-optation *as such* and chooses class solidarity over material benefit. Requires both political education (recognizing co-optation) and existing solidaristic edges across the colonial divide (having somewhere to go).
  - CO-OPTIVE to EXTRACTIVE: concessions withdrawn but power asymmetry remains (relationship reverts to pure extraction without ameliorating material flows)
  - Transitions not listed (e.g., EXTRACTIVE to SOLIDARISTIC directly) are prohibited; they require passing through intermediate states.

#### CO-OPTIVE Field Dynamics

- **FR-014**: Each CO-OPTIVE edge MUST declare which contradiction fields it suppresses (one or more of: exploitation, immiseration, imperial rent, displacement). The suppression applies to the temporal derivative df/dt of the declared fields at the co-opted node. For example, an imperial rent CO-OPTIVE edge suppresses exploitation and immiseration, while a welfare state CO-OPTIVE edge suppresses immiseration only. The suppression factor MUST be proportional to the material magnitude of concessions flowing along the CO-OPTIVE edge. When the CO-OPTIVE edge degrades or transitions to another mode, the suppression lifts and the affected contradiction accumulators resume their trajectories.
- **FR-015**: CO-OPTIVE edges MUST be a named mechanism in the continuity accounting system (FR-009). The continuity residual at a co-opted node MUST show the difference between the expected contradiction (based on material conditions) and the observed contradiction (suppressed by co-optation). This residual is the "latent contradiction" — contradiction that is suppressed in expression but not resolved in substance. When co-optation breaks down, the latent contradiction MUST be released, producing a spike in df/dt.
- **FR-016**: During periods of stable co-optation, the principal contradiction identification (FR-008) MUST account for the fact that co-optation suppresses df/dt of the exploitation field. The principal contradiction may appear to be something other than exploitation precisely because co-optation has suppressed exploitation's first derivative. When co-optation breaks down, exploitation's df/dt spikes and it reasserts itself as principal. This "return of the repressed" dynamic MUST be observable in the tick summaries.

#### CO-OPTIVE Edge Classification

- **FR-017**: The CO-OPTIVE edge mode MUST represent asymmetric, bidirectional value flow where the more powerful party offers material concessions to the less powerful party in exchange for political quiescence, loyalty, or non-opposition. The five-mode system is:

  | Mode | Direction | Value Flow | Political Content | Stability |
  |------|-----------|------------|-------------------|-----------|
  | EXTRACTIVE | Unidirectional | From exploited to exploiter | Produces resistance | Unstable (generates antagonism) |
  | TRANSACTIONAL | Bidirectional, symmetric | Market exchange | Politically neutral | Stable until disrupted |
  | SOLIDARISTIC | Bidirectional, mutual | Shared reproduction | Builds collective power | Stable under pressure (tested by crisis) |
  | ANTAGONISTIC | Oppositional | Contested/destroyed | Open conflict | Unstable (resolves toward new arrangement) |
  | CO-OPTIVE | Bidirectional, asymmetric | Concessions for quiescence | Prevents resistance | Stable while material basis persists; fragile to crisis |

#### Contradiction Internals (Constitution I.14)

- **FR-018**: Every edge MUST carry a `contradiction_character` flag with value `ANTAGONISTIC` or `NON_ANTAGONISTIC`, independent of its edge mode. The flag determines which qualitative leap occurs when an accumulator crosses a threshold. For example, a TRANSACTIONAL edge with ANTAGONISTIC character contains systematic exploitation wearing a commercial mask and is closer to rupture than a TRANSACTIONAL edge with NON_ANTAGONISTIC character. The flag is writable via `graph.update_edge()` and readable by compound predicates (FR-007).
- **FR-019**: Aspect reversal — when the dominant side of a contradiction switches (e.g., the exploited party gains power over the formerly exploiting party) — MUST be recorded as a distinct event type (`ASPECT_REVERSAL`). This is a phase transition where the same contradiction persists but with poles reversed. The event MUST include the edge identifier and the new dominant party.

#### Integration

- **FR-011**: The contradiction field layer MUST read from existing economic calculator outputs (exploitation rate, profit rate, imperial rent, wage levels). It MUST NOT duplicate economic calculations.
- **FR-012**: Temporal derivatives MUST be computed from tick-keyed history tables established by Feature 017 (Tick Dynamics). No new persistence mechanism is introduced.
- **FR-013**: Ollivier-Ricci curvature computation MUST use optimal transport (Wasserstein-1 distance between neighborhood probability distributions). Correctness MUST be validated against graphs with analytically known curvature (complete graphs, path graphs, star graphs), not against external data files.

### Key Entities

- **Contradiction Field**: A named scalar field defined at every social-class node per tick. The set of fields is extensible (open registry); four ship initially (exploitation, immiseration, imperial rent, displacement). Each has a value and associated spatial/temporal derivatives. Derived from economic calculator outputs.
- **Field Derivatives**: Spatial (gradient per edge, Laplacian per node) and temporal (first and second derivative per node). Computed each tick from field values and history. Undefined when insufficient history exists.
- **Compound Predicate**: A declarative conjunction of threshold conditions over field values and derivatives. Governs discrete state transitions. Each conjunct specifies a field, a derivative order, and a threshold comparison.
- **Edge Mode Transition**: A permitted discrete change between edge modes (EXTRACTIVE, TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC, CO-OPTIVE) governed by compound predicates. Defined as a directed state machine with named conditions.
- **CO-OPTIVE Edge**: An asymmetric, bidirectional relationship where the more powerful party offers material concessions (imperial rent, welfare, reform) to the less powerful party in exchange for political quiescence. Each CO-OPTIVE edge declares which contradiction fields it suppresses (per-edge configurable). Stable while material basis persists; fragile to crisis. Its breakdown is the trigger for the George Jackson bifurcation.
- **Latent Contradiction**: The difference between expected contradiction (based on material conditions alone) and observed contradiction (suppressed by co-optation). Accumulated over the duration of co-optation and released when co-optation breaks down. Tracked via the continuity accounting system as a named mechanism.
- **Principal Contradiction**: The contradiction field with the largest maximum absolute first derivative across all nodes at a given tick. Changes in principal contradiction are significant events.
- **Continuity Residual**: The per-node, per-tick accounting of contradiction change minus gradient-implied flow. Non-zero residuals indicate sources, sinks, or unaccounted displacement.
- **Ollivier-Ricci Curvature**: A structural property of each edge measuring bottleneck vs. redundancy in the local topology. Computed via optimal transport. Cached and recomputed only on topology change.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Given a 10-tick simulation of the Detroit metro graph, every social-class node has a defined value for all four contradiction fields at every tick, with no undefined values after tick 0.
- **SC-002**: The graph Laplacian at a high-exploitation node (Wayne County proletariat) is negative (pressure peak), while the Laplacian at a low-exploitation node (Oakland County petit bourgeoisie) is positive or near-zero, consistent with the empirical exploitation differential.
- **SC-003**: Temporal derivatives df/dt computed from tick history match analytically expected values for a test case with known linear field growth (error < 1e-6).
- **SC-004**: Ollivier-Ricci curvature values match analytically expected values for known graph topologies (complete graph K4: positive curvature, path graph P4: negative curvature at bridge edges, star graph S4: known hub curvature) within floating-point tolerance.
- **SC-005**: A compound threshold predicate referencing field magnitude AND first derivative AND Laplacian correctly triggers a state transition when all conditions are met, and does not trigger when any single condition is unmet.
- **SC-006**: Principal contradiction identification correctly switches between exploitation and immiseration fields when the scenario is configured to make one then the other have the largest absolute df/dt.
- **SC-007**: Continuity residuals for a closed system (no named source/sink mechanisms active) sum to zero across all nodes within floating-point tolerance.
- **SC-008**: For the Detroit test case (2010-2025 QCEW data), the exploitation field gradient along the Wayne-to-Oakland edge is negative (exploitation decreasing from periphery to core), consistent with empirical wage and employment differentials.
- **SC-009**: CO-OPTIVE edges suppress df/dt at the co-opted node by at least 50% compared to the same material conditions without co-optation, and this suppression is released as a measurable df/dt spike when co-optation breaks down.
- **SC-010**: During stable co-optation, the principal contradiction at co-opted nodes is correctly identified as something other than exploitation (reflecting suppressed exploitation df/dt), and after co-optation breakdown, exploitation reasserts as principal within 1-2 ticks.
- **SC-011**: The George Jackson bifurcation outcome (revolutionary vs. fascist) is correctly determined by solidarity magnitude comparison: CO-OPTIVE breakdown produces upward-directed antagonism when the co-opted node's total solidarity strength across the colonial divide exceeds its within-group solidarity strength, and lateral antagonism otherwise.

---

## Scope

### In Scope

- Contradiction field definition and per-tick computation on nodes
- Spatial derivative operators (gradient on edges, graph Laplacian on nodes)
- Temporal derivative computation from tick-keyed history (finite differences)
- Ollivier-Ricci curvature as per-edge structural invariant (recomputed on topology change only)
- Compound threshold predicates incorporating field value, derivatives, Laplacian, and curvature
- Principal contradiction identification per tick
- Continuity accounting: per-tick balance sheet for contradiction flow
- Edge mode transition state machine with declarative conditions (five modes including CO-OPTIVE)
- CO-OPTIVE edge mode with derivative suppression, latent contradiction tracking, and bifurcation dynamics
- Validation against Detroit metro data (Wayne/Oakland, 2010-2025)

### Out of Scope

- GUI visualization of fields or gradients (deferred to dashboard features)
- Full differential geometry beyond graph Laplacian and Ollivier-Ricci (no Riemann tensors, connection coefficients, or parallel transport)
- Continuous edge weights replacing categorical edge modes (the five-mode system is retained)
- Climate or environmental fields (deferred)
- Inter-metro or international graph edges (Detroit test case only)
- Edge-weighted graph Laplacian (different edge modes contributing differently to spatial derivatives)
- Vector-valued or tensor-valued contradiction fields
- Ricci flow (dynamically evolving graph topology based on curvature)
- Path integral computation for multi-hop contradiction flow tracing

---

## Assumptions

- **A-001**: Contradiction fields are scalar-valued at nodes. Vector-valued or tensor-valued contradiction fields are deferred.
- **A-002**: The graph Laplacian is unweighted (all edges contribute equally). Edge-weighted Laplacians are a future extension.
- **A-003**: Temporal derivatives use unit time steps (dt = 1 tick). The current architecture assumes fixed tick duration per Feature 017.
- **A-004**: Ollivier-Ricci curvature uses the standard formulation with self-loop probability alpha = 0.5. Validated against analytically known graph topologies.
- **A-005**: The continuity equation is a diagnostic tool, not a hard constraint. Real contradictions can be genuinely created (new exploitation established) or genuinely resolved (exploitation abolished).
- **A-006**: Field values are normalized to [0.0, 10.0] for cross-field comparability. The normalization preserves relative ordering and derivative signs.

---

## Dependencies

- **DEP-001**: Feature 017 (Tick Dynamics) for tick-keyed history tables enabling temporal derivative computation.
- **DEP-002**: Feature 016 (Class Dynamics) for class position assignments used in node stratification.
- **DEP-003**: Feature 018 (Crisis/Devaluation) for crisis events that trigger edge mode transitions and field discontinuities.
- **DEP-004**: Existing economic calculators (exploitation rate, profit rate, imperial rent) providing the source values from which contradiction fields are derived.
- **DEP-005**: Existing graph structure with categorical edge modes (EXTRACTIVE, TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC), extended to include CO-OPTIVE per the edge mode completeness analysis.
- **DEP-006**: Ollivier-Ricci curvature methodology validated against analytically known graph topologies (complete, path, star graphs).

---

## Theoretical Predictions (Falsifiable Hypotheses)

The following predictions follow from the field framework and are testable against Detroit data:

- **P-001**: Wayne County's exploitation field Laplacian is consistently negative (pressure peak) across 2010-2025, reflecting its structural position as the high-exploitation node in the metro graph.
- **P-002**: The exploitation gradient along the Wayne-to-Oakland edge correlates negatively with gentrification indicators (rising Oakland property values, declining Wayne population) as the gradient steepens, displacement intensifies.
- **P-003**: The temporal second derivative d2f/dt2 for the exploitation field at Wayne County changes sign between 2013-2016, corresponding to the transition from post-crisis intensification to gentrification-driven partial displacement.
- **P-004**: Edges with negative Ollivier-Ricci curvature (bottleneck topology) sustain steeper contradiction gradients than edges with positive curvature (redundant topology), when controlling for field magnitude.
- **P-005**: The principal contradiction in the Detroit metro graph shifts from exploitation (2010-2014, post-crisis austerity) to displacement (2015-2020, gentrification period), identifiable by the crossover in maximum |df/dt| between the two fields.
- **P-006**: The transition from CO-OPTIVE to ANTAGONISTIC in the Detroit metro graph correlates with austerity indicators (declining public employment, reduced social services, foreclosure crisis) in Wayne County, 2008-2012. The breakdown of co-optation (withdrawal of New Deal-era labor compromises, public sector austerity, foreclosure wave) precedes the spike in exploitation df/dt that reasserts exploitation as the principal contradiction.
