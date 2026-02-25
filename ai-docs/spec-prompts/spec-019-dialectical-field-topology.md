# Feature 019: Dialectical Field Topology

**Spec ID**: `019-dialectical-field-topology`
**Created**: 2026-02-24
**Status**: Draft
**Dependencies**: Feature 017 (Tick Dynamics), Feature 018 (Crisis/Devaluation), Feature 016 (Class Dynamics)

---

## Feature Overview

### Problem Statement

Babylon's simulation currently treats node-level quantities (exploitation rate, immiseration, imperial rent) and discrete state transitions (edge mode changes, consciousness shifts, crisis triggers) as separate systems with ad hoc coupling. The tick loop updates quantities, then checks thresholds, but lacks a unified framework connecting *where* contradictions concentrate, *how* they propagate across the graph, and *why* qualitative transitions occur at specific nodes and not others.

The theoretical foundation exists: Mao's *On Contradiction* establishes that quantitative accumulation gives rise to qualitative change, that every process contains a principal contradiction, and that the character of a contradiction (tending toward or away from antagonism) determines outcomes. What's missing is the formal machinery to compute these concepts on the NetworkX graph as field operations — gradients, Laplacians, curvature — unified with the existing categorical edge mode system and the tick-keyed temporal history.

### Core Insight

The dialectical categories — quantity, quality, character of contradiction, principal vs. secondary contradiction, antagonistic vs. non-antagonistic — are recoverable from a single time series and its spatial/temporal derivatives:

- **Magnitude of contradiction** = field value f(i, t) at node i, tick t
- **Character** = temporal first derivative ∂f/∂t (intensifying or being sublated)
- **Tendency toward antagonism** = temporal second derivative ∂²f/∂t² (accelerating or decelerating)
- **Spatial concentration** = graph Laplacian Δf(i) (pressure peak or trough relative to neighbors)
- **Topological character** = Ollivier-Ricci curvature κ(i) (bottleneck vs. resilient neighborhood structure)
- **Qualitative transition** = discrete state change when threshold conditions on the above are met

Quantities flux continuously. States transition discretely. The transition conditions incorporate both magnitude *and* trajectory (derivatives), grounded in the topology (curvature). This is the architectural principle.

### What This Feature Provides

A field-theoretic layer on the NetworkX graph that:

1. Defines contradiction accumulators as fields on nodes, computed from existing economic calculators
2. Computes spatial derivatives (gradients along edges, Laplacian at nodes) each tick
3. Computes temporal derivatives from tick-keyed history
4. Uses Ollivier-Ricci curvature as structural context for how gradients persist or dissipate
5. Expresses threshold conditions for discrete state transitions (edge mode, consciousness, crisis) as compound predicates over field values and their derivatives
6. Identifies the principal contradiction at each tick as the one with the largest absolute first derivative
7. Enforces a continuity equation: contradiction that decreases at one node must be accounted for by flow along edges or by a named resolution mechanism

---

## Scope

### In Scope

- Contradiction field definition and per-tick computation on nodes
- Spatial derivative operators (coboundary/gradient on edges, graph Laplacian on nodes)
- Temporal derivative computation from tick-keyed SQLite history (finite differences)
- Integration of Ollivier-Ricci curvature as per-edge structural invariant (recomputed on topology change only, not per tick)
- Compound threshold predicates incorporating field value, first derivative, second derivative, Laplacian, and curvature
- Principal contradiction identification per tick
- Continuity accounting: per-tick balance sheet for contradiction flow
- Validation against Detroit metro data (Wayne/Oakland, 2010-2025)

### Out of Scope

- GUI visualization of fields or gradients (deferred to dashboard features)
- Full differential geometry beyond graph Laplacian and Ollivier-Ricci (no Riemann tensors, connection coefficients, or parallel transport)
- Continuous edge weights replacing categorical edge modes (the four-mode system is retained)
- Climate or environmental fields (deferred)
- Inter-metro or international graph edges (Detroit test case only)

---

## Theoretical Grounding

### Mao's *On Contradiction* as Architectural Constraint

The following principles from *On Contradiction* are formalized as computational requirements, not treated as metaphor:

**Universality of contradiction.** Every node in the graph carries at least one contradiction accumulator. There are no contradiction-free zones. (FR-001)

**Quantitative change gives rise to qualitative change.** Contradiction accumulators update continuously (per-tick). State transitions are discrete and occur only when threshold conditions on the accumulator and its derivatives are satisfied. There is no gradual blending between states. (FR-006, FR-007)

**Principal contradiction.** At every tick, exactly one contradiction is identified as principal across the graph — the one driving the dynamics. Secondary contradictions are "determined or influenced by" the principal one. The principal contradiction can change between ticks. (FR-008)

**Character of contradiction.** Whether a contradiction tends toward antagonism or is being managed is not a separate variable — it is the first and second temporal derivatives of the accumulator. Positive ∂f/∂t with positive ∂²f/∂t² = accelerating toward antagonism. Negative ∂²f/∂t² = counter-tendencies gaining ground. (FR-004)

**Antagonistic vs. non-antagonistic contradiction.** The same contradiction can be antagonistic or non-antagonistic depending on conditions (Mao: town/countryside under capitalism vs. socialism). This maps to edge mode: the same node pair can have an EXTRACTIVE or TRANSACTIONAL edge, and the field derivatives determine which transition is imminent. (FR-007)

**Internal contradiction as basis of change.** External causes operate through internal causes. The graph Laplacian captures this: a node's field value is influenced by neighbors (external), but the transition depends on the node's own accumulator state (internal). Contagion occurs through the Laplacian, but the qualitative leap requires internal threshold crossing. (FR-003)

### Continuity and Conservation

Contradiction is not created from nothing or destroyed into nothing. When a contradiction accumulator decreases at node i without a named resolution mechanism (wage increase, political victory, repression success), the decrease must be accounted for by flow to adjacent nodes along gradient-directed edges. This is the displacement hypothesis: gentrification doesn't resolve the contradiction at Wayne County, it displaces it along the graph.

This is formalized as a per-tick continuity check (FR-009), not a hard conservation law. Contradiction *can* be genuinely created (new exploitation relationship established) or destroyed (exploitation relationship dissolved). But unaccounted disappearance is flagged as a diagnostic — either the model is missing a mechanism, or displacement is occurring and should be tracked.

---

## Functional Requirements

### Contradiction Field

**FR-001**: The system shall define a set of named contradiction fields, each computed as a scalar value at every social-class node per tick. Initial fields: exploitation contradiction (derived from exploitation rate e = s/v), immiseration contradiction (derived from real wage trajectory), imperial rent contradiction (derived from Φ differential to graph mean), and displacement contradiction (derived from population change rate).

**FR-002**: Each contradiction field value shall be persisted in tick-keyed history tables, enabling retrieval of f(i, t) for any node i at any historical tick t within the simulation run.

### Spatial Derivatives

**FR-003**: The system shall compute the **gradient** of each contradiction field along every edge per tick, defined as ∇f(i,j) = f(j) - f(i) for edge (i, j). The gradient is signed and directional — positive means the field increases from source to target.

**FR-004**: The system shall compute the **graph Laplacian** of each contradiction field at every node per tick, defined as Δf(i) = Σ_{j ∈ neighbors(i)} [f(j) - f(i)]. A negative Laplacian indicates the node is a local pressure peak (higher contradiction than its neighborhood). A positive Laplacian indicates a pressure trough.

**FR-005**: The system shall compute **Ollivier-Ricci curvature** for each edge. Curvature is a structural property of the graph topology, not of the field, and shall be recomputed only when the graph topology changes (node or edge addition/removal), not on every tick. Curvature values shall be cached on edge attributes.

### Temporal Derivatives

**FR-006**: The system shall compute the first temporal derivative ∂f/∂t at each node for each contradiction field using backward finite differences from tick-keyed history: ∂f/∂t ≈ f(i, t) - f(i, t-1). The second temporal derivative ∂²f/∂t² shall be computed as ∂²f/∂t² ≈ f(i, t) - 2·f(i, t-1) + f(i, t-2). Computation requires a minimum of 2 ticks of history for ∂f/∂t and 3 ticks for ∂²f/∂t²; prior to that, derivatives are reported as undefined (not zero).

### State Transition Predicates

**FR-007**: Discrete state transitions (edge mode changes, consciousness state changes, crisis triggers) shall be governed by **compound threshold predicates** that may reference any combination of: field magnitude f(i,t), first temporal derivative ∂f/∂t, second temporal derivative ∂²f/∂t², graph Laplacian Δf(i), Ollivier-Ricci curvature κ of adjacent edges, and edge mode of adjacent edges. A transition fires when all conjuncts of its predicate are satisfied. Predicates shall be declaratively specified, not hardcoded in tick-loop logic.

### Principal Contradiction

**FR-008**: At each tick, the system shall identify the **principal contradiction** across the graph. The principal contradiction is defined as the contradiction field whose maximum absolute first derivative |∂f/∂t|_max across all nodes is greatest. The identity of the principal contradiction shall be recorded in the tick summary. When the principal contradiction changes between ticks, this shall be logged as a significant event.

### Continuity Accounting

**FR-009**: For each contradiction field, the system shall compute a per-tick **continuity residual** at each node: the change in field value minus the net flow implied by gradients along adjacent edges. A residual significantly different from zero (threshold configurable) indicates either a local source/sink mechanism (which must be named — e.g., "wage increase," "displacement inflow," "crisis devaluation") or an unaccounted transfer that should be investigated. Residuals shall be persisted in tick history for diagnostic queries.

### Edge Mode Transition Topology

**FR-010**: The permissible edge mode transitions shall be defined as a directed graph (state machine) with named conditions for each transition. Not all 16 possible transitions (4 modes × 4 modes) are valid. The initial transition topology:

- EXTRACTIVE → ANTAGONISTIC (extraction contested; condition: exploitation contradiction at source exceeds threshold AND ∂f/∂t > 0)
- EXTRACTIVE → TRANSACTIONAL (extraction broken; condition: organizing success event)
- TRANSACTIONAL → SOLIDARISTIC (mutual aid established; condition: organizing work event with sustained duration)
- TRANSACTIONAL → ANTAGONISTIC (market failure; condition: crisis event)
- TRANSACTIONAL → EXTRACTIVE (power asymmetry emerges; condition: wealth differential exceeds threshold)
- SOLIDARISTIC → TRANSACTIONAL (solidarity degrades under pressure; condition: crisis_intensity > edge resilience)
- SOLIDARISTIC → ANTAGONISTIC (betrayal; condition: betrayal event)
- ANTAGONISTIC → TRANSACTIONAL (conflict resolved; condition: negotiation event or exhaustion)
- ANTAGONISTIC → ANTAGONISTIC (conflict persists; default when no resolution condition met)

Transitions not listed (e.g., EXTRACTIVE → SOLIDARISTIC directly) are prohibited — they require passing through intermediate states.

### Integration with Existing Systems

**FR-011**: The contradiction field layer shall read from existing economic calculator outputs (exploitation rate, profit rate, imperial rent Φ, wage levels) via the ServiceContainer. It shall not duplicate economic calculations.

**FR-012**: Temporal derivatives shall be computed from tick-keyed history tables established by Feature 017 (Tick Dynamics). No new persistence mechanism is introduced — the field layer writes to the same history tables using additional columns or a linked table.

**FR-013**: Ollivier-Ricci curvature computation shall use the existing NetworkX graph structure. The computation shall be performed using optimal transport (Wasserstein-1 distance between neighborhood probability distributions), consistent with the Ricci analysis already performed in the project (babylon_ricci_final.csv).

---

## Success Criteria

**SC-001**: Given a 10-tick simulation of the Detroit metro graph, every social-class node has a defined value for all four contradiction fields at every tick, with no NaN or undefined values after tick 0 (tick 0 is initialization).

**SC-002**: The graph Laplacian at a high-exploitation node (Wayne County proletariat) is negative (pressure peak), while the Laplacian at a low-exploitation node (Oakland County petit bourgeoisie) is positive or near-zero, consistent with the empirical exploitation differential.

**SC-003**: Temporal derivatives ∂f/∂t computed from tick history match the analytically expected values for a test case with known linear field growth (error < 1e-6).

**SC-004**: Ollivier-Ricci curvature values computed by the system match previously validated values from babylon_ricci_final.csv for the same graph topology (within floating-point tolerance).

**SC-005**: A compound threshold predicate referencing field magnitude AND first derivative AND Laplacian can be specified declaratively and correctly triggers a state transition in a test scenario where all three conditions are met, while not triggering when any single condition is unmet.

**SC-006**: The principal contradiction identification correctly switches between exploitation and immiseration fields when the test scenario is configured to make one then the other have the largest absolute ∂f/∂t.

**SC-007**: Continuity residuals for a closed system (no named source/sink mechanisms active) sum to zero across all nodes within floating-point tolerance, confirming that field changes are fully accounted for by inter-node flow.

**SC-008**: For the Detroit test case (2010-2025 QCEW data), the exploitation field gradient along the Wayne→Oakland edge is negative (exploitation decreasing from periphery to core), consistent with the empirical wage and employment differential.

---

## User Stories

### US1: Simulation Researcher — Diagnosing Contradiction Dynamics

*As a simulation researcher, I want to query the contradiction field state at any node and tick so that I can understand where contradictions concentrate, how they propagate, and why transitions occur where they do.*

**Acceptance Scenarios:**

1. **Given** a completed simulation run, **when** I query node "wayne_proletariat" at tick 15, **then** I receive: exploitation contradiction value, its ∂f/∂t, its ∂²f/∂t², the Laplacian Δf, and the mean Ollivier-Ricci curvature of adjacent edges.

2. **Given** a completed run, **when** I query the gradient along edge "wayne_proletariat → oakland_proletariat" at tick 15, **then** I receive the signed gradient value and the edge's Ricci curvature.

3. **Given** a completed run with a principal contradiction switch at tick 8, **when** I query the tick summary for tick 8, **then** it identifies the switch from exploitation to immiseration as the principal contradiction and logs the event.

### US2: Theorist — Validating the Continuity Hypothesis

*As a political economy theorist, I want to verify whether contradiction is conserved or displaced rather than resolved, so that I can test the displacement hypothesis against Detroit data.*

**Acceptance Scenarios:**

1. **Given** a run where Wayne County exploitation contradiction decreases between tick 10 and tick 20, **when** I sum continuity residuals for the exploitation field across all nodes for those ticks, **then** unaccounted residuals are flagged with diagnostics identifying which nodes gained or lost contradiction without a named mechanism.

2. **Given** a closed test scenario with no source/sink mechanisms, **when** the exploitation field is initialized with a gradient and allowed to evolve for 10 ticks, **then** the total contradiction across all nodes remains constant (conservation verified).

### US3: Developer — Specifying Transition Predicates

*As a developer extending Babylon, I want to specify new state transition conditions as declarative predicates over field values and derivatives, so that I can add new transition types without modifying the tick loop.*

**Acceptance Scenarios:**

1. **Given** a predicate defined as `f > 0.7 AND ∂f/∂t > 0 AND Δf < 0 AND κ < -0.1`, **when** I register it as the condition for an EXTRACTIVE → ANTAGONISTIC edge transition, **then** the transition fires at the correct tick in a test run where these conditions converge.

2. **Given** a predicate where the curvature condition is unmet but all others are met, **when** the tick advances, **then** no transition fires, confirming that all conjuncts are required.

### US4: Empirical Validator — Detroit Field Analysis

*As a researcher validating against real data, I want to compare computed field values and gradients against QCEW-derived quantities for Metro Detroit, so that I can assess whether the field framework reproduces known economic geography.*

**Acceptance Scenarios:**

1. **Given** QCEW data loaded for Wayne and Oakland counties (2010-2025), **when** the exploitation field is hydrated from exploitation rate calculations, **then** Wayne County nodes consistently show higher exploitation values than Oakland County nodes across the time series.

2. **Given** the same data, **when** temporal derivatives are computed for Wayne County, **then** the period 2010-2014 (post-crisis recovery) shows positive ∂²f/∂t² (accelerating contradiction) and the period 2018-2022 shows negative ∂²f/∂t² (decelerating), consistent with the gentrification timeline.

---

## Edge Cases

**EC-001**: **Insufficient history for derivatives.** At ticks 0 and 1, second derivatives are undefined. The system returns None (not 0.0) for ∂²f/∂t² and compound predicates requiring ∂²f/∂t² cannot fire. Predicates referencing undefined derivatives evaluate to False for that conjunct.

**EC-002**: **Isolated nodes.** A node with no edges has an undefined Laplacian (no neighbors to sum over). The system returns 0.0 for Δf at isolated nodes and logs a warning. Predicates referencing Δf at isolated nodes use 0.0.

**EC-003**: **Simultaneous transition eligibility.** If multiple edge mode transitions are eligible at the same tick for the same edge (e.g., both TRANSACTIONAL → SOLIDARISTIC and TRANSACTIONAL → ANTAGONISTIC conditions are met), priority is determined by the transition topology's priority ordering, not by arbitrary selection. Transitions driven by crisis events take priority over transitions driven by organizing events.

**EC-004**: **Principal contradiction tie.** If two contradiction fields have identical maximum |∂f/∂t| values, the system selects the one with the larger total field magnitude (Σ_i |f(i)|) as principal. If still tied, exploitation is preferred by default (as the contradiction between productive forces and relations of production is structurally primary per Marx).

**EC-005**: **Curvature on single-edge nodes.** Nodes connected by a single edge have only one curvature value. Mean curvature equals that value. This is a degenerate case topologically (no redundancy), and the curvature will typically be strongly negative (bottleneck).

**EC-006**: **Division by zero in Ollivier-Ricci.** If a node's neighborhood probability distribution is degenerate (node has degree 1), the Wasserstein distance computation requires a uniform distribution over the single neighbor plus the node itself. The implementation shall handle this case per the standard Ollivier formulation with self-loop probability α.

**EC-007**: **Field value explosion.** If any contradiction accumulator exceeds a configurable maximum bound (default: 10.0 on normalized scale), a diagnostic is logged and the value is clamped. This indicates either a modeling error or a runaway feedback loop requiring investigation.

---

## Assumptions

**A-001**: Contradiction fields are scalar-valued at nodes. Vector-valued or tensor-valued contradiction fields are deferred (no need for directional contradiction at a single node in the current architecture).

**A-002**: The graph Laplacian is unweighted (all edges contribute equally to the sum). Edge-weighted Laplacians (where EXTRACTIVE edges might contribute differently than SOLIDARISTIC edges) are a future extension.

**A-003**: Temporal derivatives use unit time steps (Δt = 1 tick). If tick duration varies, derivatives must be normalized by tick duration. The current architecture assumes fixed tick duration per Feature 017.

**A-004**: Ollivier-Ricci curvature uses the standard formulation with self-loop probability α = 0.5 (equal weight to staying vs. moving to neighbor). This is the most common default in the literature and matches the existing babylon_ricci_final.csv analysis.

**A-005**: The continuity equation is a diagnostic tool, not a hard constraint. The simulation does not enforce conservation of contradiction — it reports violations for investigation. This is deliberate: real contradictions can be genuinely created (new exploitation established) or genuinely resolved (exploitation abolished).

**A-006**: Field values are normalized to [0.0, 10.0] for cross-field comparability. The normalization preserves relative ordering and derivative signs. The specific normalization scheme (min-max, z-score, or domain-specific) is an implementation decision.

---

## Dependencies

**DEP-001**: Feature 017 (Tick Dynamics) — tick-keyed history tables for temporal derivative computation.

**DEP-002**: Feature 016 (Class Dynamics) — class position assignments for node stratification.

**DEP-003**: Feature 018 (Crisis/Devaluation) — crisis events that trigger edge mode transitions and field discontinuities.

**DEP-004**: Existing economic calculators (exploitation rate, profit rate, imperial rent Φ) via ServiceContainer — field values are derived from these, not computed independently.

**DEP-005**: Existing NetworkX graph structure with categorical edge modes (EXTRACTIVE, TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC) per solidarity_edge_formalization.md.

**DEP-006**: Existing Ollivier-Ricci curvature methodology validated in babylon_ricci_final.csv.

---

## Deferred

**FE-001**: Edge-weighted graph Laplacian (different edge modes contribute differently to spatial derivatives).

**FE-002**: Vector-valued contradiction fields (directional contradiction at a single node).

**FE-003**: Parallel transport of field values along paths (full differential geometry machinery).

**FE-004**: Automated principal contradiction cascade (secondary contradictions being quantitatively influenced by changes in the principal contradiction).

**FE-005**: GUI visualization of field gradients, Laplacian heatmaps, and curvature overlays on the hex map.

**FE-006**: Path integral computation for multi-hop contradiction flow tracing (computationally expensive; the single-hop Laplacian is sufficient for current resolution).

**FE-007**: Ricci flow — dynamically evolving the graph topology based on curvature. Ricci curvature is currently treated as a diagnostic, not as a force that reshapes the graph.

---

## Theoretical Predictions (Falsifiable Hypotheses)

The following predictions follow from the field framework and are testable against Detroit data:

**P-001**: Wayne County's exploitation field Laplacian is consistently negative (pressure peak) across 2010-2025, reflecting its structural position as the high-exploitation node in the metro graph.

**P-002**: The exploitation gradient along the Wayne→Oakland edge correlates negatively with gentrification indicators (rising Oakland property values, declining Wayne population) — as the gradient steepens, displacement intensifies.

**P-003**: The temporal second derivative ∂²f/∂t² for the exploitation field at Wayne County changes sign between 2013-2016, corresponding to the transition from post-crisis intensification to gentrification-driven partial displacement.

**P-004**: Edges with negative Ollivier-Ricci curvature (bottleneck topology) sustain steeper contradiction gradients than edges with positive curvature (redundant topology), when controlling for field magnitude.

**P-005**: The principal contradiction in the Detroit metro graph shifts from exploitation (2010-2014, post-crisis austerity period) to displacement (2015-2020, gentrification period), identifiable by the crossover in maximum |∂f/∂t| between the two fields.
