# Feature Specification: Bifurcation Topology Analysis

**Feature Branch**: `033-bifurcation-topology`
**Created**: 2026-03-01
**Status**: Draft
**Input**: User description: "Bifurcation Topology Analysis — the George Jackson model, extended with community consciousness weighting"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consciousness-Weighted Solidarity (Priority: P1)

As a simulation designer, I need solidarity edges weighted by the consciousness of the communities involved, so that assimilationist solidarity is correctly identified as fragile and non-revolutionary — distinct from solidarity built on acknowledged structural opposition.

The central insight: a SOLIDARITY edge between agents whose communities have high collective_identity carries revolutionary potential. The same edge between agents whose communities have low collective_identity (assimilated, "we're all Americans") carries no revolutionary content and breaks under crisis stress. This is the Democratic Party coalition problem — high cross-line edge density with near-zero oppositional consciousness.

**Why this priority**: Without consciousness weighting, the simulation cannot distinguish revolutionary solidarity from assimilationist solidarity. Every subsequent computation depends on this distinction.

**Independent Test**: Can be tested by constructing a graph with SOLIDARITY edges between agents in marginalized communities at varying collective_identity levels, and verifying that the weighted solidarity values correctly reflect consciousness quality — not just edge count.

**Acceptance Scenarios**:

1. **Given** a SOLIDARITY edge between a NEW_AFRIKAN worker (collective_identity=0.8) and a SETTLER worker, **When** consciousness-weighted solidarity is computed, **Then** the result reflects high revolutionary potential (weighted value near the edge's raw resilience).
2. **Given** a SOLIDARITY edge between a NEW_AFRIKAN worker (collective_identity=0.1, assimilated) and a SETTLER worker, **When** consciousness-weighted solidarity is computed, **Then** the result reflects near-zero revolutionary potential despite the edge existing.
3. **Given** a SOLIDARITY edge between two agents who share no marginalized community memberships, **When** consciousness-weighted solidarity is computed, **Then** the result is zero (no marginalized consciousness to weight).
4. **Given** an agent belonging to multiple marginalized communities with different collective_identity levels, **When** consciousness-weighted solidarity is computed, **Then** the weighting uses the mean collective_identity across their marginalized community memberships.

______________________________________________________________________

### User Story 2 - Per-Axis Contradiction Analysis (Priority: P2)

As a simulation designer, I need to analyze each contradiction axis independently — colonial (SETTLER vs colonized nations) and patriarchal (PATRIARCHAL vs WOMEN/TRANS) — computing the balance between consciousness-weighted cross-line solidarity and lateral antagonism along each axis.

Each axis where lateral antagonism dominates represents one more dimension toward fascism. The state activates multiple axes simultaneously (racial panic + gender panic + immigration panic).

**Why this priority**: The per-axis analysis is the building block for the full bifurcation computation. It must correctly identify whether solidarity or antagonism dominates along each structural divide.

**Independent Test**: Can be tested by constructing graphs with varying solidarity/antagonism balances along each axis and verifying correct tendency classification per axis.

**Acceptance Scenarios**:

1. **Given** a graph where consciousness-weighted cross-line solidarity across the colonial axis exceeds lateral antagonism, **When** per-axis tendency is computed for the colonial axis, **Then** the axis tendency value is greater than 1.0 (solidarity-dominant).
2. **Given** a graph where lateral antagonism dominates across the patriarchal axis, **When** per-axis tendency is computed for the patriarchal axis, **Then** the axis tendency value is less than 1.0 (antagonism-dominant).
3. **Given** a graph where both axes show antagonism-dominant tendencies, **When** per-axis tendencies are computed, **Then** both axes independently register as fascist-tending, reinforcing the overall fascist tendency.
4. **Given** an edge between two agents, **When** checking whether it crosses a contradiction axis, **Then** the system correctly identifies whether the source and target are on opposite sides of that axis (one hegemonic-community member, one marginalized-community member).

______________________________________________________________________

### User Story 3 - Community Bridge Detection (Priority: P3)

As a simulation designer, I need to detect communities that span contradiction axes — the intersectional bridges — and weight their bridge potential by collective_identity. A DISABLED community with high collective_identity (disability justice framework) actively bridges divides. The same community with low collective_identity (assimilated, "we're all just people") provides no bridge.

**Why this priority**: Community bridges are a distinct contribution to revolutionary potential beyond individual solidarity edges. They represent collective organizational infrastructure that connects otherwise separated groups.

**Independent Test**: Can be tested by constructing a hypergraph with institutional exclusion communities spanning contradiction axes at varying collective_identity levels, and verifying that bridge potential activates only above a meaningful consciousness threshold.

**Acceptance Scenarios**:

1. **Given** a DISABLED community (institutional exclusion category) whose members span the colonial axis, with collective_identity=0.8, **When** community bridges are detected, **Then** the DISABLED community is identified as an active bridge with high weighted potential.
2. **Given** a DISABLED community whose members span the colonial axis, with collective_identity=0.1, **When** community bridges are detected, **Then** the community is identified as a potential bridge but with near-zero weighted potential (assimilated consciousness does not bridge).
3. **Given** an INCARCERATED community whose members span both colonial AND patriarchal axes, **When** community bridges are detected, **Then** the community is identified as spanning multiple axes (double bridge-building duty), with weighted potential proportional to its collective_identity.
4. **Given** a lifecycle-phase community (YOUTH, ADULT, ELDER), **When** community bridges are detected, **Then** lifecycle communities are excluded from bridge analysis (they are not structural contradiction bridges).

______________________________________________________________________

### User Story 4 - Topological Resilience Metrics (Priority: P4)

As a simulation designer, I need topological resilience metrics — Betti numbers (connected components, cycles), equivalence classes, and targeted purge resilience — computed on the consciousness-weighted solidarity subgraph. A star topology (one hub) has low resilience; a mesh topology has high resilience. Large equivalence classes indicate redundancy.

**Why this priority**: Resilience metrics determine whether the solidarity network survives state repression (targeted removal of key nodes). This is structurally independent of the consciousness-weighting computation but essential for the full bifurcation result.

**Independent Test**: Can be tested by constructing known graph topologies (star, mesh, ring, disconnected) and verifying correct Betti number computation and resilience scores.

**Acceptance Scenarios**:

1. **Given** a star-topology solidarity subgraph (one central node connected to all others), **When** topological resilience is computed, **Then** beta_0 is 1 (one component), beta_1 is 0 (no cycles), and targeted purge resilience is low (removing the hub fragments the graph).
2. **Given** a mesh-topology solidarity subgraph (every node connected to every other), **When** topological resilience is computed, **Then** beta_0 is 1, beta_1 is high (many independent cycles), and targeted purge resilience is high.
3. **Given** a disconnected solidarity subgraph with 3 isolated components, **When** topological resilience is computed, **Then** beta_0 is 3, indicating fragmentation.
4. **Given** a solidarity subgraph, **When** equivalence classes are computed, **Then** nodes with identical connectivity patterns are grouped together, and the distribution of class sizes is reported.
5. **Given** a solidarity subgraph, **When** critical singletons are identified, **Then** the system reports nodes whose removal increases beta_0 (articulation points / cut vertices).

______________________________________________________________________

### User Story 5 - Full Bifurcation Computation (Priority: P5)

As a simulation designer, I need a unified bifurcation analysis that combines per-axis tendency, community bridge potential, legitimation crisis intensity, and topological resilience into a single BifurcationResult — classifying the overall tendency as "revolutionary", "fascist", or "indeterminate".

The critical validation: a graph with high cross-line solidarity density but low collective_identity (the assimilation trap) MUST classify as fascist-tending, not revolutionary. This is the core theoretical contribution.

**Why this priority**: This is the capstone integration that produces the simulation's central prediction. It depends on all previous user stories.

**Independent Test**: Can be tested by constructing complete test scenarios (graph + hypergraph + consciousness state) and verifying that the overall classification matches theoretical predictions across all validation criteria.

**Acceptance Scenarios**:

1. **Given** a graph with only within-group solidarity (no cross-line edges), **When** bifurcation tendency is computed, **Then** the overall tendency is "fascist".
2. **Given** a graph with cross-line solidarity where all marginalized communities have high collective_identity (>=0.7), **When** bifurcation tendency is computed, **Then** the overall tendency is "revolutionary".
3. **Given** a graph with high cross-line solidarity density but all marginalized communities have low collective_identity (<=0.2) — the assimilation trap, **When** bifurcation tendency is computed, **Then** the overall tendency is "fascist" despite the high edge density.
4. **Given** a graph where the colonial axis is solidarity-dominant but the patriarchal axis is antagonism-dominant, **When** bifurcation tendency is computed, **Then** the per-axis tendencies reflect this split, and the overall tendency accounts for both axes.
5. **Given** two identical solidarity topologies differing only in legitimation index (one high, one in crisis), **When** bifurcation tendency is computed for each, **Then** the low-legitimation scenario shows amplified crisis intensity.

______________________________________________________________________

### User Story 6 - Material Solidarity Ceiling (Priority: P6)

As a simulation designer, I need material constraints on solidarity formation — wage gap ratios, geographic proximity, shared exploitation sources, and shared community membership — that impose ceilings on new solidarity edge strength. These ceilings apply only to FORMING new solidarity edges. Existing edges' revolutionary content is determined by consciousness, not material ceilings.

**Why this priority**: Material constraints ground solidarity formation in economic reality rather than allowing arbitrary cross-class solidarity that ignores material conditions. This is important but secondary to the analysis functions.

**Independent Test**: Can be tested by computing solidarity ceilings for agent pairs with known wage gaps, geographic relationships, and community memberships.

**Acceptance Scenarios**:

1. **Given** two agents with a wage gap ratio greater than 10, **When** the solidarity ceiling is computed, **Then** the ceiling is at most 0.3 (material conditions severely limit cross-class solidarity).
2. **Given** two agents with a wage gap ratio less than 2, **When** the solidarity ceiling is computed, **Then** the ceiling is at most 0.9 (similar material conditions allow strong solidarity).
3. **Given** two agents who share a common exploitation source, **When** the solidarity ceiling is computed, **Then** the ceiling receives a +0.2 bonus (shared enemy raises potential).
4. **Given** two agents who share community membership, **When** the solidarity ceiling is computed, **Then** the ceiling is raised (shared community infrastructure facilitates solidarity).

______________________________________________________________________

### User Story 7 - Legitimation Crisis Amplifier (Priority: P7)

As a simulation designer, I need the existing DPD legitimation index integrated into the bifurcation computation as a crisis amplifier. When the D-P-D' social contract breaks down (pension coverage collapses, home ownership drops, retirement confidence evaporates), crisis intensity amplifies — the bifurcation becomes sharper and faster.

**Why this priority**: This connects the bifurcation analysis to the existing DPD lifecycle system (Feature 030), creating a feedback loop where demographic-economic collapse drives political crisis.

**Independent Test**: Can be tested by computing legitimation index from known DPD states and verifying that low legitimation amplifies crisis intensity in bifurcation results.

**Acceptance Scenarios**:

1. **Given** territories with high legitimation indices (stable pensions, high home ownership), **When** the legitimation index is aggregated, **Then** the crisis amplifier is near 1.0 (no amplification).
2. **Given** territories with legitimation indices below 0.3 (CRISIS classification), **When** the legitimation index is aggregated, **Then** the crisis amplifier is significantly greater than 1.0 (amplified crisis).
3. **Given** a bifurcation computation with identical solidarity topology but different legitimation states, **When** results are compared, **Then** the low-legitimation scenario shows a more decisive (less "indeterminate") bifurcation tendency.

______________________________________________________________________

### Edge Cases

- What happens when no SOLIDARITY edges exist in the graph? (Trivially fascist — no solidarity network to analyze.)
- What happens when no marginalized communities exist in the hypergraph? (Consciousness weighting returns zero for all edges — degenerate case, should produce "indeterminate".)
- What happens when a community has zero members on one side of an axis it supposedly spans? (Not a bridge — bridge detection must verify actual membership on both sides.)
- What happens when the hypergraph is empty (no communities built this tick)? (Graceful degradation — return unweighted analysis with a warning flag.)
- What happens when all communities have collective_identity exactly at 0.5? (Ambiguous zone — should produce "indeterminate" tendency, not collapse to either attractor.)
- What happens when wage gap ratio is exactly at a threshold boundary (e.g., exactly 2.0 or exactly 10.0)? (Boundary belongs to the lower tier — use inclusive comparison for the lower bound.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compute consciousness-weighted solidarity for any SOLIDARITY edge by applying a nonlinear transform (sigmoid or similar with a breakage cliff) to the minimum collective_identity across the connected agents' marginalized community memberships, then combining with edge resilience. The transform must create a sharp drop below a consciousness threshold, modeling the phase transition between solidarity that holds under crisis stress and assimilated solidarity that shatters.
- **FR-002**: System MUST distinguish between cross-line solidarity (agents on opposite sides of a contradiction axis) and within-line solidarity (agents on the same side), using the existing ContradictionAxis definitions.
- **FR-003**: System MUST compute per-axis tendency as the ratio of consciousness-weighted cross-line solidarity to lateral antagonism for each defined contradiction axis.
- **FR-004**: System MUST detect communities spanning contradiction axes (bridges) and weight their bridge potential by collective_identity, excluding lifecycle-phase communities from bridge analysis.
- **FR-005**: System MUST compute Betti numbers beta_0 (connected components) and beta_1 (independent cycles) using a two-pass approach: once on the raw solidarity subgraph (all SOLIDARITY edges) and once on the consciousness-filtered subgraph (only edges above consciousness-weighted threshold). Both sets of metrics MUST be reported in BifurcationResult. The bifurcation classification uses the consciousness-filtered metrics. The gap between raw and filtered metrics exposes the assimilation trap (high raw beta_1, low filtered beta_1 = fragile network masquerading as robust). Standard graph algorithms only (no external persistent homology libraries).
- **FR-006**: System MUST compute equivalence classes on the solidarity subgraph by grouping nodes with identical neighbor sets, and report the size distribution.
- **FR-007**: System MUST identify critical singletons (articulation points whose removal increases beta_0) and critical cutsets (minimal edge sets whose removal disconnects components).
- **FR-008**: System MUST compute a unified bifurcation tendency using a weakest-link model: if any contradiction axis is antagonism-dominant, overall tendency cannot be "revolutionary." The distinction between "indeterminate" and "fascist" depends on the severity of the weakest axis's antagonism-dominance and whether community bridges and topological resilience provide sufficient counterpressure. A barely-antagonistic axis with strong cross-axis solidarity and active bridges = "indeterminate"; a deeply antagonistic axis = "fascist" regardless of other axes. "Revolutionary" requires all axes solidarity-dominant.
- **FR-009**: System MUST classify a graph with high cross-line solidarity density but low collective_identity as fascist-tending (the assimilation trap), NOT revolutionary.
- **FR-010**: System MUST compute material solidarity ceilings based on wage gap ratio, geographic proximity, shared exploitation source, and shared community membership — applying these ceilings only to new solidarity edge formation, not to consciousness weighting of existing edges.
- **FR-011**: System MUST integrate the existing DPD legitimation index as a crisis amplifier in the bifurcation computation, where low legitimation amplifies crisis intensity.
- **FR-012**: System MUST produce a complete BifurcationResult containing: overall tendency, per-axis tendencies, raw edge counts (cross-line, within-line, lateral antagonism, upward antagonism), consciousness-weighted metrics, community bridge metrics, legitimation index, both raw AND consciousness-filtered Betti numbers, both raw AND consciousness-filtered resilience metrics, equivalence class distribution, critical singletons, and critical cutsets.
- **FR-013**: System MUST treat consciousness weighting as a qualitative filter using a nonlinear transform with a breakage cliff — not a simple scalar multiplication. The transform must produce near-zero output for assimilated consciousness (low collective_identity) and near-full output for oppositional consciousness (high collective_identity), with a sharp transition zone modeling the phase boundary.
- **FR-015**: Bifurcation analysis MUST be integrated as an extension of the existing TopologyMonitor, adding bifurcation metrics to the topology snapshot cycle rather than running as a separate engine System.
- **FR-016**: System MUST emit a simulation event when the overall bifurcation tendency changes between ticks (analogous to the existing PhaseTransitionEvent). The system MUST NOT write bifurcation results to graph node/edge attributes — it operates as a read-only observer.
- **FR-014**: System MUST gracefully handle degenerate cases: no solidarity edges, no marginalized communities, empty hypergraph, and zero-member bridge communities — returning appropriate default results without errors.

### Key Entities

- **BifurcationResult**: The complete output of bifurcation analysis — overall tendency classification, per-axis tendency scores, raw and weighted solidarity counts, bridge metrics, legitimation state, and topological resilience measures.
- **AxisTendency**: Per-contradiction-axis analysis — the ratio of consciousness-weighted cross-line solidarity to lateral antagonism, indicating whether solidarity or antagonism dominates along that structural divide.
- **BridgeInfo**: A community spanning a contradiction axis with its weighted bridge potential — combining the community's infrastructure with its collective_identity to determine actual bridging capacity.
- **SolidarityCeiling**: Material constraints on solidarity formation between two agents — derived from wage gap, geography, exploitation source, and community membership.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The assimilation trap test passes — a graph with 20+ cross-line solidarity edges but collective_identity below 0.2 across all marginalized communities classifies as "fascist", not "revolutionary".
- **SC-002**: Pure within-group solidarity (zero cross-line edges) always classifies as "fascist" regardless of collective_identity levels.
- **SC-003**: Cross-line solidarity with collective_identity above 0.7 across marginalized communities classifies as "revolutionary" when resilience_under_targeted_purge >= 0.5 (mesh topology, not star).
- **SC-004**: Removing a single hub node from a star-topology solidarity network drops resilience below 0.3; removing any single node from a mesh-topology network keeps resilience above 0.7.
- **SC-005**: Bridge potential for a community with collective_identity=0.1 is less than 15% of the same community's bridge potential at collective_identity=0.8.
- **SC-006**: Lowering legitimation index from 0.8 to 0.2 shifts the overall tendency from "indeterminate" toward "fascist" or "revolutionary" (exits the dead zone), or if already outside the dead zone, increases the weakest axis's antagonism-dominance ratio by at least 0.3.
- **SC-007**: All analysis functions execute within the existing tick budget — the full bifurcation computation adds no more than 10% overhead to an average simulation tick.
- **SC-008**: Per-axis analysis correctly identifies antagonism-dominant vs solidarity-dominant for each contradiction axis independently, verified across at least 5 distinct graph configurations per axis.

## Clarifications

### Session 2026-03-01

- Q: When does bifurcation analysis run — new System, event-triggered, or TopologyMonitor extension? → A: Extension of existing TopologyMonitor (adds bifurcation analysis to snapshot cycle).
- Q: Is the min(source_ci, target_ci) formula sufficient or should consciousness weighting use a nonlinear transform? → A: Nonlinear transform. Use a sigmoid (or similar) that sharply drops below a threshold, creating a natural breakage cliff. This captures the qualitative distinction: there's a phase transition between "enough oppositional consciousness to hold solidarity under stress" and "assimilated consciousness that shatters." The exact sigmoid parameters are a planning-phase decision.
- Q: Does BifurcationResult feed back into simulation state or is it read-only? → A: Emit simulation event on tendency change (like PhaseTransitionEvent), but no graph attribute writes. Bifurcation analysis remains a read-only observer consistent with the project's observer architecture.
- Q: Does the solidarity subgraph for Betti numbers/resilience include all SOLIDARITY edges or only consciousness-weighted ones? → A: Two-pass. Compute both raw topology metrics (all SOLIDARITY edges) and consciousness-filtered metrics (only edges above consciousness-weighted threshold). Report both in BifurcationResult. The bifurcation classification uses the consciousness-filtered metrics; the raw metrics expose the assimilation trap gap (high raw beta_1, low filtered beta_1 = fragile network that looks robust).
- Q: How do per-axis tendencies, bridges, resilience, and legitimation combine into the overall classification? → A: Weakest-link model. If any axis is antagonism-dominant, overall tendency cannot be "revolutionary." The distinction between "indeterminate" and "fascist" depends on how antagonism-dominant the weakest axis is and whether bridges and resilience provide enough counterpressure. A barely-antagonistic axis with strong cross-axis solidarity and active community bridges = "indeterminate" (vulnerable but holding). A deeply antagonistic axis = "fascist" regardless of other axes.

## Assumptions

- The existing `ContradictionAxis` definitions (COLONIAL_AXIS, PATRIARCHAL_AXIS) in `CONTRADICTION_AXES` are authoritative and complete for the current simulation scope. New axes can be added by extending this list without modifying bifurcation analysis logic.
- Lateral antagonism is identified through edges of type EXPLOITATION, REPRESSION, or COMPETITION between agents on the same side of a contradiction axis, plus any ANTAGONISTIC-mode edges. The exact edge types constituting "antagonism" will be refined during planning.
- Upward antagonism (directed at hegemonic community members) is tracked separately from lateral antagonism in the BifurcationResult but both contribute to the per-axis tendency computation.
- Beta_1 (independent cycles) is computed via the cycle rank formula (edges - nodes + components) from graph theory, not via persistent homology. Beta_2 is excluded from the core implementation.
- The "indeterminate" classification applies when the overall tendency score falls within a configurable dead zone around the bifurcation threshold.
- Geographic proximity for solidarity ceiling computation uses existing ADJACENCY edges between territories, not geographic distance calculations.
- The legitimation index aggregation across territories uses a population-weighted mean of per-territory legitimation indices computed by the existing DPD lifecycle system.
