# Feature Specification: Ternary Consciousness Model

**Spec ID**: `034-ternary-consciousness`
**Feature Branch**: `034-ternary-consciousness`
**Created**: 2026-03-01
**Status**: Draft
**Depends On**: 029-community-hyperedge-upgrade, 033-bifurcation-topology, 031-ooda-loop-system (for Organization consciousness_tendency)

---

## Theoretical Foundation

### The Problem with Stipulated Consciousness

Feature 029 introduced `CommunityConsciousness` with three scalar fields: `collective_identity` (float), `dominant_tendency` (enum), and `ideological_contestation` (float). These are SYNTHETIC values — stipulated defaults with no data path and no derivation from simulation primitives. The enum collapses critical information: a community that is 10% revolutionary, 80% liberal, 10% fascist occupies a completely different position than one that is 10% revolutionary, 45% liberal, 45% fascist. Both have the same `collective_identity` and the same `dominant_tendency`. But the second is on the verge of a fascist flip that the first is not. The current model cannot distinguish these cases.

More fundamentally, consciousness as a stipulated scalar violates the project's core principle: no magic constants. If `collective_identity = 0.5`, 0.5 of *what*? There is no material referent. The number is not derived from primitives, not traceable to data, and not falsifiable.

### Jackson's Framework: Two Kinds of Hierarchy, One Kind of Liberation

George Jackson's *Blood in My Eye* provides the theoretical grounding for a consciousness model that IS traceable to material conditions. Jackson identifies that there are "only two ways by which societies can ever be governed and organized for production of their needs: the various types of totalitarian methods represented by assorted capitalist and fascist arrangements, and the egalitarian method." This is a binary: hierarchy (in its various faces) vs. egalitarianism.

Jackson further identifies that reform IS fascism — that "economic reform comes very close to a working definition of fascist motive forces." Liberal reform and overt fascism are not opposites but two tactical faces of the same ruling-class project of preserving property relations. The electoral choice between them is, in Jackson's words, "choosing which way one wishes to die."

This maps onto a ternary structure where the revolutionary vertex is qualitatively different from the liberal-fascist spectrum:

- **Height above the base** = distance from assimilation = revolutionary consciousness. This is the only axis of qualitative change. It measures the degree to which a community recognizes its interests as structurally opposed to the hegemonic order and organizes accordingly.
- **Position along the base** = which tactical face of hierarchy currently dominates. Liberal (expand the definition, let us in) vs. fascist (shrink the definition, exclude the others). Both are assimilationist — both preserve existing property relations. The state slides communities along this axis depending on conditions.

The vanguard's task is to move communities *perpendicular* to the base — upward toward the revolutionary vertex. Jackson's critique of the old left's failure in the 1930s maps precisely: conditions were favorable, but the vanguard allowed crisis-driven movement to go SIDEWAYS (from rightward panic to leftward New Deal reform) instead of UPWARD. The community's position slid along the base of the triangle instead of lifting off it.

### Consciousness as Derived Quantity: Organizations Are the Agents

The ternary coordinates `(r, l, f)` where `r + l + f = 1.0` must not be stipulated scalars any more than the old model was. They must be DERIVED from material conditions already present in the simulation.

The derivation follows from Babylon's core architectural insight: **organizations are the agents**. A community's consciousness is not an abstract property of its members' heads — it is the projection of the organizational landscape onto the community hyperedge. Consciousness is read off the pattern of which organizations are active in a community, what tendencies those organizations hold, how much capacity they have relative to community population, and what resources they control.

This means consciousness changes through organizational dynamics that already exist in the simulation: organizations recruit members, build capacity, provide services, educate, agitate. Each of these actions changes the organizational landscape. The ternary coordinates are recomputed each tick from that landscape. No separate "consciousness update" mechanic is needed — consciousness dynamics ARE organizational dynamics viewed from the community's perspective.

The critical design choice: **unorganized population defaults to liberal**. Jackson provides the theoretical basis: the fascists have "deliberately manufactured a false sense of security" through bread and circuses. People who are not organized by anyone default to passive acceptance of the existing order, which is liberal hegemony. The ternary diagram starts with every community pinned to the bottom-left vertex (pure liberal) and only moves as organizations do work. The ruling class does not need to actively organize liberal consciousness — it is the DEFAULT produced by the absence of revolutionary organizing. This is why Jackson insists the vanguard must "manufacture" revolutionary conditions rather than wait for them.

### The Substrate Floor: Consciousness That Survives Organization Destruction

There is a residual that organizational membership alone cannot capture. Jackson describes consciousness that lives in the community substrate — the grandmother teaching her grandchild not to talk to cops, survival knowledge transmitted through D-phase socialization, the cultural memory of resistance accumulated over generations of struggle. This substrate consciousness is not organized by any extant organization. It persists even when organizations are destroyed, which is why COINTELPRO could not kill Black revolutionary consciousness even after destroying every Black revolutionary organization of the 1960s-70s.

The substrate floor is a slow-moving component (changes on generational timescale, transmitted through the D-P-D' lifecycle circuit) that sets a minimum revolutionary consciousness for communities with historical resistance traditions. It must be empirically proxied, not stipulated.

### The Ternary Diagram as Soil Triangle

The visualization analogy is the soil composition triangle (sand/silt/clay), where any point represents a mixture that sums to unity. The consciousness triangle (revolutionary/liberal/fascist) works identically: any community occupies a single point in the 2-simplex, and that point is fully determined by measurable organizational composition plus substrate floor.

---

## User Scenarios & Testing

### User Story 1 — Compute Ternary Consciousness from Organizational Landscape (Priority: P1)

A simulation researcher needs each community hyperedge's consciousness to be computed from the organizations operating within that community, weighted by organizational capacity relative to community population, so that consciousness is a derived quantity with a material referent rather than a stipulated scalar.

**Why this priority**: This is the foundation — every other feature in this spec depends on consciousness being computable from the organizational landscape. Without it, the ternary model is just three stipulated scalars instead of one.

**Independent Test**: Seed a community with known organizations of known tendencies and known membership counts. Verify computed ternary coordinates match expected values. Remove all organizations. Verify community reverts to liberal default (plus substrate floor if applicable).

**Acceptance Scenarios**:

1. **Given** a community with population 1000, one revolutionary organization with 100 members and resource base 1.0, and one liberal organization with 200 members and resource base 1.0, **When** ternary consciousness is computed, **Then** r = 0.1, l = 0.9 (0.2 organized liberal + 0.7 unorganized default), f = 0.0 (after normalization to simplex).

2. **Given** a community with NO organizations present, **When** ternary consciousness is computed, **Then** r = substrate_floor (community-specific), l = 1.0 - substrate_floor, f = 0.0 — pure liberal default plus substrate.

3. **Given** a community where a revolutionary organization doubles its membership between tick N and tick N+1, **When** ternary consciousness is recomputed, **Then** r increases proportionally and l decreases, with no direct manipulation of consciousness scalars.

4. **Given** a community where all revolutionary organizations are destroyed (COINTELPRO scenario), **When** ternary consciousness is recomputed, **Then** r drops to substrate_floor (not to zero) — substrate consciousness persists without organizational carriers.

5. **Given** two communities with identical organizational landscapes but different substrate floors (NEW_AFRIKAN with historical resistance tradition vs. SETTLER with no substrate revolutionary consciousness), **When** ternary consciousness is computed, **Then** r differs by exactly the substrate floor differential.

6. **Given** the existing CommunityConsciousness model fields, **When** ternary consciousness is computed, **Then** backward-compatible properties (collective_identity, dominant_tendency, ideological_contestation) are derivable from the ternary coordinates without loss of existing functionality.

______________________________________________________________________

### User Story 2 — Substrate Floor from Empirical Proxies (Priority: P2)

A simulation researcher needs the substrate floor (minimum revolutionary consciousness persisting in a community independent of organizational activity) to be derived from traceable empirical proxies rather than stipulated, so that the model has no magic constants.

**Why this priority**: Without the substrate floor, destroying organizations reduces consciousness to zero, which is empirically false. Without an empirical proxy, the floor is a magic constant. This story grounds the floor in data.

**Independent Test**: Compute substrate floor for a community using proxy data. Verify value is reproducible from input data alone. Verify value changes when proxy data changes (e.g., different county with different incarceration rate).

**Acceptance Scenarios**:

1. **Given** a NEW_AFRIKAN community in Wayne County with historical incarceration rate, protest event density, and intergenerational wealth destruction rate available, **When** substrate floor is computed, **Then** the value is higher than for a SETTLER community in Oakland County (reflecting differential exposure to state violence and failed assimilation bargain).

2. **Given** proxy data sources (incarceration rate from BJS/Vera, protest density from ACLED/Crowd Counting Consortium, intergenerational wealth mobility from Chetty Opportunity Atlas), **When** substrate floor is computed, **Then** every input traces to a named data source with documented provenance.

3. **Given** a community type where no substrate proxy data exists, **When** substrate floor is computed, **Then** the floor defaults to 0.0 with a logged warning flagging the gap — no silent magic constants.

4. **Given** substrate floor proxy data for the Detroit test case (Wayne and Oakland Counties, 2010-2025), **When** floors are computed for NEW_AFRIKAN, SETTLER, INCARCERATED, and FIRST_NATIONS communities, **Then** INCARCERATED and NEW_AFRIKAN have the highest floors, SETTLER has the lowest, and all values trace to documented proxy computations.

______________________________________________________________________

### User Story 3 — Backward Compatibility with CommunityConsciousness (Priority: P1)

A simulation researcher needs the ternary model to replace the internal representation of CommunityConsciousness while preserving all existing computed fields and downstream consumers, so that specs 029, 031, 032, and 033 continue to function without modification.

**Why this priority**: The existing codebase has consumers of collective_identity, dominant_tendency, and ideological_contestation. Breaking these is unacceptable.

**Independent Test**: Run all existing community consciousness tests after replacing the internal model. All must pass unchanged.

**Acceptance Scenarios**:

1. **Given** the ternary model replacing the scalar model, **When** collective_identity is accessed, **Then** it returns the r component (revolutionary share) — semantically identical to the original field.

2. **Given** the ternary model, **When** dominant_tendency is accessed, **Then** it returns the ConsciousnessTendency corresponding to the largest component (argmax of r, l, f) — semantically identical to the original field.

3. **Given** the ternary model, **When** ideological_contestation is accessed, **Then** it returns the normalized Shannon entropy of the (r, l, f) distribution — higher entropy means more contested ideological terrain, consistent with the original field's semantics.

4. **Given** the infiltration_resistance computed field on CommunityState, **When** computed from the ternary model, **Then** results are identical to the scalar model because infiltration_resistance depends on collective_identity which equals r.

5. **Given** CONSCIOUSNESS_DEFAULTS for all 14 community types, **When** each default is loaded, **Then** the ternary coordinates produce backward-compatible collective_identity, dominant_tendency, and ideological_contestation values that match the existing defaults within tolerance.

6. **Given** all existing tests in test_community_models.py, test_community_system.py, and test_community_formulas.py, **When** run against the ternary model, **Then** all pass without modification.

______________________________________________________________________

### User Story 4 — Ternary Visualization for God Mode Dashboard (Priority: P3)

A simulation researcher needs each community's consciousness to be visualizable as a point in a ternary diagram (analogous to a soil composition triangle), so that the ideological trajectory of communities can be observed over simulation ticks.

**Why this priority**: The ternary diagram is the primary diagnostic tool for the George Jackson bifurcation — the researcher can literally see whether communities are drifting rightward along the base (fascism winning) or lifting off the base (revolution building). Lower priority because it depends on all computational stories being complete.

**Independent Test**: Generate ternary coordinates for multiple communities over multiple ticks. Verify all points fall within the 2-simplex. Verify visualization renders without error.

**Acceptance Scenarios**:

1. **Given** ternary coordinates for a community, **When** plotted in the 2-simplex, **Then** the point falls within the triangle (r + l + f = 1.0 within floating-point tolerance, all components non-negative).

2. **Given** a time series of ternary coordinates over 100 ticks, **When** plotted as a trajectory, **Then** the path shows the community's ideological drift (sideways along base = assimilation trap; upward = revolutionary organizing working; downward = state ASSIMILATE succeeding).

3. **Given** multiple communities plotted simultaneously, **When** a crisis event occurs, **Then** the visualization shows divergent trajectories — some communities moving up (revolution), others moving right (fascism) — making the George Jackson bifurcation visually legible.

4. **Given** the ternary diagram, **When** the researcher examines the bottom edge, **Then** communities near the bottom are identifiable as stuck in the assimilation trap regardless of their l/f ratio — Jackson's "choosing which way to die."

______________________________________________________________________

### User Story 5 — Consciousness-Weighted Bifurcation Integration (Priority: P2)

A simulation researcher needs the bifurcation topology analysis (spec 033) to consume the ternary model's richer information — specifically the assimilation_ratio and the distinction between high-r and low-r solidarity — so that the assimilation trap is detectable: high cross-line solidarity with low revolutionary consciousness produces fascism under crisis, not revolution.

**Why this priority**: This is the payoff — the ternary model exists to make the bifurcation analysis more accurate. The current scalar model cannot detect the assimilation trap (high solidarity + low consciousness = still fascist). The ternary model can.

**Independent Test**: Construct two scenarios with identical cross-line solidarity density but different r values. Verify the bifurcation analysis produces different outcomes.

**Acceptance Scenarios**:

1. **Given** a graph with high cross-line solidarity density AND high r (revolutionary consciousness) in connected communities, **When** bifurcation is computed, **Then** outcome tends revolutionary.

2. **Given** a graph with high cross-line solidarity density AND low r (assimilated communities, Democratic Party coalition pattern), **When** bifurcation is computed, **Then** outcome tends fascist despite the solidarity density — the assimilation trap.

3. **Given** the existing consciousness_weighted_solidarity formula from spec 033, **When** the ternary model is used, **Then** the formula uses r (collective_identity) as the weighting factor, producing identical results to the scalar model for the same effective collective_identity values.

4. **Given** a community with r = 0.1 but high l and strong liberal organizational infrastructure, **When** crisis hits and solidarity edges are stress-tested, **Then** the edges built on liberal (assimilationist) solidarity break because they deny the contradiction that crisis exposes — while edges built on revolutionary solidarity (high r on both endpoints) survive.

5. **Given** the assimilation_ratio (f / (l + f)) property, **When** a community has high assimilation_ratio AND low r, **Then** the bifurcation analysis identifies this as fascist-vulnerable — the community is not just unrevolutionary but specifically trending toward fascist mobilization.

______________________________________________________________________

### Edge Cases

**Single-tendency dominance**: A community where one organization completely dominates (e.g., a company town with only the company union). The ternary point is pinned near one vertex. Contestation is near zero. This is accurate — monopoly control over organizational landscape means monopoly control over consciousness.

**Rapid organizational destruction**: Multiple organizations destroyed in one tick (mass arrests, RICO prosecution). Consciousness drops toward substrate floor. The floor prevents unrealistic instant amnesia. Recovery depends on rebuilding organizational capacity.

**Organizations spanning multiple communities**: An organization active in both NEW_AFRIKAN and SETTLER communities contributes to both computations, weighted by its membership in each. This is correct — the NAACP shifts consciousness in every community where it operates, proportional to its presence.

**Substrate floor exceeding organizational computation**: If substrate floor (e.g., 0.15 for NEW_AFRIKAN) exceeds the r computed from organizational landscape (e.g., 0.05 from a single small org), the floor dominates. This is correct — substrate consciousness is a MINIMUM, not an additive component.

**Zero-population community**: A community with no members has undefined consciousness. Return (0, 1, 0) — liberal default — with a logged warning. This should be rare in practice.

**Hegemonic communities**: SETTLER and PATRIARCHAL hyperedges also have ternary consciousness, but the semantics differ: r measures conscious defense of extraction position (white nationalism), l measures passive beneficiary default, f measures active exclusionary mobilization. The computation is identical — organizational landscape projection — but the interpretation of the revolutionary vertex is inverted. Flag this semantic inversion in documentation.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST compute a community's consciousness as a point in the 2-simplex `(r, l, f)` where `r + l + f = 1.0`, derived from the organizations active within that community. The computation MUST weight each organization's contribution by its membership density in the community (members in community / community population) multiplied by the organization's resource base. Unorganized population fraction MUST default to the liberal component. The substrate floor MUST set a minimum on the revolutionary component.

- **FR-002**: System MUST compute a per-community substrate floor for the revolutionary component. The floor MUST be derived from empirical proxy data (incarceration rate, protest event density, intergenerational wealth destruction) where available. Where proxy data is unavailable, the floor MUST default to 0.0 with a logged provenance gap warning. The floor MUST be a slow-moving value (generational timescale, updated at most once per simulation year) distinct from the fast-moving organizational computation (per tick).

- **FR-003**: All ternary coordinates MUST satisfy `r + l + f = 1.0` within floating-point tolerance and `r >= 0, l >= 0, f >= 0`. The system MUST normalize after computation to enforce the constraint. Violation of the constraint after normalization MUST raise a validation error.

- **FR-004**: System MUST provide computed fields that are backward-compatible with the existing CommunityConsciousness interface: `collective_identity` (returns r), `dominant_tendency` (returns argmax ConsciousnessTendency), and `ideological_contestation` (returns normalized Shannon entropy of the distribution). All existing consumers of these fields MUST function without modification.

- **FR-005**: System MUST compute `assimilation_ratio = f / (l + f)` as a derived property. This captures how much of the non-revolutionary consciousness is fascist vs. liberal — the position along the bottom edge of the triangle. When `l + f` is near zero (fully revolutionary community), the ratio is undefined and MUST return 0.5 (neutral).

- **FR-006**: Ternary consciousness MUST be recomputed each tick from the current organizational landscape. The system MUST NOT store ternary coordinates as persistent state that requires its own update dynamics. What is stored is the organizational membership data and substrate floor. The ternary point is derived.

- **FR-007**: Each substrate floor value MUST carry provenance metadata: the data source(s) used, the proxy computation method, and a confidence level (HIGH if derived from multiple independent proxies, MEDIUM if from one proxy, LOW if estimated, SYNTHETIC if stipulated as placeholder). Substrate floors with SYNTHETIC provenance MUST be flagged at initialization with a logged warning.

- **FR-008**: The bifurcation topology's consciousness_weighted_solidarity function MUST consume the ternary model's `r` component as its weighting factor. Solidarity edges between communities with low r MUST be marked as crisis-fragile (assimilation trap indicator) regardless of edge density.

- **FR-009**: The state's ability to estimate a community's consciousness position MUST be anisotropic: position along the liberal-fascist axis (l/f ratio) is more observable (voting patterns, public discourse, media consumption) than the revolutionary component (r). The system MUST model this as a higher observation error on the r component than on the l/f ratio for state AttentionThread intelligence estimates.

- **FR-010**: Existing CONSCIOUSNESS_DEFAULTS for all 14 community types MUST be migrated to ternary coordinates that produce backward-compatible derived fields. The migration MUST be documented as a mapping table showing old scalar values and new ternary coordinates with verification that derived fields match.

### Key Entities

- **TernaryConsciousness**: Frozen model representing a point in the 2-simplex with r, l, f components and derived backward-compatible fields
- **SubstrateFloor**: Per-community-type minimum revolutionary consciousness with provenance metadata
- **ConsciousnessComputation**: Pure function computing ternary coordinates from organizational landscape and substrate floor
- **AssimilationRatio**: Derived property measuring position along the liberal-fascist base

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: For the Detroit test case, ternary consciousness computed from seeded organizational landscape produces r values within 0.05 of the backward-compatible collective_identity for all 14 community types — demonstrating migration correctness.

- **SC-002**: Removing all organizations from a community causes r to drop to the substrate floor (not to zero) and l to rise to 1.0 minus substrate floor — demonstrating the substrate persistence property.

- **SC-003**: Doubling a revolutionary organization's membership in a community produces a proportional increase in r and decrease in l — demonstrating the material derivation property.

- **SC-004**: Two communities with identical organizational landscapes but different substrate floors produce different r values differing by exactly the floor differential — demonstrating substrate floor independence from organizational dynamics.

- **SC-005**: All existing tests in test_community_models.py, test_community_system.py, and test_community_formulas.py pass without modification after the ternary model replaces the scalar model — demonstrating backward compatibility.

- **SC-006**: The assimilation trap scenario (high cross-line solidarity, low r) produces fascist bifurcation outcome in spec 033, while the same solidarity density with high r produces revolutionary outcome — demonstrating the ternary model's discriminative power over the scalar model.

- **SC-007**: Substrate floor values for the Detroit test case trace to documented data sources (BJS incarceration data, ACLED protest data, Chetty mobility data) with no SYNTHETIC provenance flags — demonstrating empirical grounding.

- **SC-008**: All ternary coordinates satisfy the simplex constraint (r + l + f = 1.0 +/- 1e-6, all components >= 0) at every tick in a 100-tick test run — demonstrating numerical stability.

---

## Data Requirements

### Substrate Floor Proxy Data

| Proxy | Data Source | Measures | Maps To |
|-------|------------|----------|---------|
| Incarceration rate by race by county | BJS National Prisoner Statistics, Vera Institute | Exposure to state violence; failed assimilation bargain | Higher incarceration -> higher substrate floor |
| Protest event density by county | ACLED US, Crowd Counting Consortium | Historical organizational presence, even if current orgs are gone | Higher protest history -> higher substrate floor |
| Intergenerational wealth mobility by race | Chetty Opportunity Atlas (tract-level, aggregated to county) | Failed class ascendancy promise; broken assimilation bargain | Lower upward mobility -> higher substrate floor |
| Union density by county | BLS, QCEW (already ingested) | Organized labor presence (primarily liberal but carries organizational memory) | Used for liberal organizational capacity, not substrate floor |
| SPLC hate group presence by county | SPLC Hate Map | Fascist organizational capacity | Used for fascist organizational capacity computation |
| Nonprofit density by type by county | IRS 990 / NCCS | Liberal organizational infrastructure | Used for liberal organizational capacity computation |

### MVP Data Strategy

For MVP, use incarceration rate (available from Vera, county-level) as the primary substrate floor proxy. This is the strongest single proxy because incarceration is direct, measurable state violence exposure. Supplement with Chetty mobility data (already available). Defer ACLED and SPLC data to post-MVP.

For organizational landscape seeding, use union density (from QCEW, already ingested) for liberal capacity and SPLC county data for fascist capacity. Revolutionary capacity has no clean federal data source — seed from manual research on known organizations in Detroit metro for the test case, flagged as SYNTHETIC.

---

## Assumptions

- **A-001**: Unorganized population defaults to liberal consciousness. This is a theoretical commitment grounded in Jackson's analysis, not an empirical claim. If challenged, the default could be made community-specific (e.g., unorganized population in a community with high substrate floor might default partially to revolutionary). Deferred to calibration.

- **A-002**: Organizational resource base is a meaningful multiplier on consciousness influence. An organization with 50 members and $1M in assets has more consciousness-shaping capacity than one with 50 members and no assets. The resource_base field exists on Organization models from spec 031.

- **A-003**: The substrate floor changes on a generational timescale (updated at most yearly in the simulation). This means it is effectively constant for short-run dynamics and only matters for multi-generational DPD' analysis.

- **A-004**: Incarceration rate is a valid proxy for substrate revolutionary consciousness. The mechanism: incarceration exposes individuals and families to the adversarial nature of the state, producing survival knowledge that transmits intergenerationally. This is consistent with Jackson's own trajectory (radicalized through incarceration) and with the broader pattern of prison as a site of revolutionary consciousness formation.

- **A-005**: The ConsciousnessTendency enum (LIBERAL, FASCIST, REVOLUTIONARY) in the existing codebase maps directly to the ternary vertices. No new enum values are needed. The `ASSIMILATIONIST_` prefix from some earlier design documents was not implemented and is not needed — the ternary structure itself captures that liberal and fascist are both assimilationist (they share the bottom edge).

- **A-006**: Organizations classify into exactly one consciousness tendency. An organization that is "liberal on racial issues but fascist on gender" is not modeled at this resolution — it is classified by its dominant tendency. Finer-grained organizational ideology is deferred.

---

## Boundary / Out of Scope

- Organization-level consciousness dynamics (how orgs change tendency) — deferred
- Territory-level consciousness geography (consciousness varying spatially within a community) — deferred to org-topology Phase 6
- Individual-level consciousness (each agent having their own ternary position) — explicitly rejected; consciousness is a community-level property
- Dynamic substrate floor updates (floor changing in response to events like police killings) — deferred to post-MVP; for now, floor is static per simulation run
- International consciousness dynamics (peripheral communities outside US) — deferred
- Ternary visualization implementation (the God Mode dashboard rendering) — deferred to dashboard spec; this spec defines the data model only
- Media/propaganda modeling (how mass media shifts consciousness independent of organizational presence) — deferred; for now, media effects are modeled as liberal organizational capacity
- Religious institution classification (which denominations map to which tendency) — deferred; requires its own research task
- Formal algebraic topology of the 2-simplex (persistent homology, etc.) — explicitly excluded; the simplex is used as a compositional model, not a topological space requiring homological analysis

---

## Dependencies

- **Requires**: Feature 029 (Community Hyperedge Upgrade) — provides CommunityConsciousness, CommunityState, ConsciousnessTendency, CONSCIOUSNESS_DEFAULTS
- **Requires**: Feature 031 (OODA Loop System) — provides Organization.consciousness_tendency and organization-community relationship edges
- **Requires**: Feature 033 (Bifurcation Topology) — provides consciousness_weighted_solidarity that this spec upgrades
- **Required By**: Org-topology Phase 3 (Attention Thread System) — observation gap anisotropy (FR-009) feeds state intelligence model
- **Required By**: Org-topology Phase 4 (Bifurcation Topology upgrade) — assimilation trap detection (US5)
- **Required By**: God Mode Dashboard — ternary visualization (US4)
- **Required By**: DPD' Lifecycle Circuit — substrate floor transmitted through D-phase socialization

---

## What This Spec Does NOT Include

- Prescribing the exact weight formula for organizational capacity contribution (that is an implementation decision subject to calibration)
- Defining how the OODA system's EDUCATE/AGITATE/ASSIMILATE actions modify consciousness (those actions modify the organizational landscape, which is already their defined behavior; this spec computes consciousness FROM that landscape)
- Creating new data ingestion pipelines (uses existing QCEW, BJS/Vera, Chetty data sources)
- Modifying the ConsciousnessTendency enum or any existing enums
- Changing how organizations are classified by tendency (that is spec 031's domain)
