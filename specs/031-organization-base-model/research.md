# Research: Organization Base Model

**Feature**: 031-organization-base-model
**Date**: 2026-02-27

## R1: Pydantic Inheritance Pattern for Organization Subtypes

**Decision**: Discriminated union via `org_type` literal discriminator.

**Rationale**: Pydantic 2.x supports discriminated unions natively. Each subtype declares `org_type: Literal[OrgType.STATE_APPARATUS]` (etc.), and the base uses `Annotated[Union[...], Field(discriminator="org_type")]` for deserialization. This gives:
- Automatic JSON serialization/deserialization based on type tag
- Shared base fields inherited without duplication
- Type-safe access to subtype-specific fields after narrowing
- Frozen model compatibility (all subtypes use `ConfigDict(frozen=True)`)

**Alternatives considered**:
- Separate classes with shared Protocol: More flexible but no DRY on shared fields. Rejected — 13 shared fields would be duplicated 4x.
- Composition (base + details union): Awkward access pattern (`org.details.violence_capacity`). Rejected.

**Pattern from codebase**: No existing discriminated union in the models, but Pydantic 2.x supports this cleanly. The `EventTemplate` model uses union types for preconditions — closest existing pattern.

## R2: Graph Node Representation

**Decision**: Organizations stored as graph nodes with `_node_type="organization"`. Key Figures stored as separate nodes with `_node_type="key_figure"`.

**Rationale**: Follows the existing `to_graph()`/`from_graph()` pattern in WorldState. SocialClass nodes use `_node_type="social_class"`, Territory nodes use `_node_type="territory"`. Adding `_node_type="organization"` is a natural extension.

**Integration points**:
- `WorldState.organizations: dict[str, Organization]` — new field
- `WorldState.to_graph()` — serialize org nodes with `_node_type="organization"`
- `WorldState.from_graph()` — dispatch on `_node_type` to reconstruct org entities
- `organization_excluded` set for fields systems write but `Organization.__init__` doesn't accept

**Alternatives considered**:
- Org as graph-level metadata (`G.graph["organizations"]`): Loses node-edge connectivity. Rejected.
- Org as attribute on SocialClass nodes: Conflates entity types. Rejected.

## R3: New EdgeType Values

**Decision**: Add 5 new EdgeType values to `enums.py`.

| Value | Source → Target | Semantics |
|-------|----------------|-----------|
| `MEMBERSHIP` | Organization → SocialClass | Weighted edge: population count from that class block |
| `RECRUITMENT` | Organization → SocialClass | Active recruitment pipeline from population |
| `EMPLOYMENT` | Business → SocialClass | Employer-employee relationship (distinct from WAGES which is payment flow) |
| `COMMAND` | KeyFigure → KeyFigure | Internal hierarchy within org topology |
| `PRESENCE` | Organization → Territory | Org operates in this territory |

**Rationale**: Existing EdgeType values (EXPLOITATION, SOLIDARITY, WAGES, etc.) describe class-to-class or territory relations. Organization-specific relationships need distinct types for:
- Composition queries (filter by MEMBERSHIP edges)
- Internal topology analysis (traverse COMMAND edges)
- Spatial footprint (PRESENCE edges)

**Alternatives considered**:
- Reuse WAGES for EMPLOYMENT: WAGES is a payment flow (Currency), not a structural relationship. Rejected.
- Reuse TENANCY for PRESENCE: TENANCY implies rent payment, not operational presence. Rejected.

## R4: New Enum Definitions

**Decision**: 6 new StrEnum classes in `enums.py`.

| Enum | Values | Notes |
|------|--------|-------|
| `OrgType` | STATE_APPARATUS, BUSINESS, POLITICAL_FACTION, CIVIL_SOCIETY | Discriminator for org subtypes |
| `ClassCharacter` | BOURGEOIS, PETTY_BOURGEOIS, LABOR_ARISTOCRATIC, PROLETARIAN, LUMPEN, CONTESTED | Which class the org serves (not composition) |
| `TopologyType` | STAR, HIERARCHY, MESH, CELL | Classification output (computed from COMMAND edges, NOT stored) |
| `LegalStanding` | SOVEREIGN, CHARTERED, REGISTERED, INFORMAL, UNDERGROUND | Distinct from LegalStatus (community-level) |
| `JurisdictionLevel` | NATIONAL, STATE, COUNTY, MUNICIPAL | StateApparatus jurisdiction scope |
| `ServiceType` | RELIGIOUS, EDUCATIONAL, HEALTHCARE, LEGAL_AID, MUTUAL_AID, CULTURAL, MEDIA, LABOR | CivilSocietyOrg service domain |

**Naming note**: `LegalStanding` (org-level) is intentionally distinct from existing `LegalStatus` (community-level: LEGAL/SURVEILLED/DESIGNATED_EXTREMIST/etc.). Different concepts at different scales.

## R5: Key Figure Identification Algorithm

**Decision**: Use articulation point detection for key figure identification. Singletons (structurally unique nodes in Sparrow equivalence sense) are identified as nodes whose removal increases the number of connected components.

**Algorithm by topology type**:
- **STAR**: Center node is the sole articulation point → singleton key figure.
- **HIERARCHY**: Root and branch-point nodes are articulation points → multiple key figures.
- **MESH**: Fully connected (or near-complete) graphs have no articulation points → no key figures.
- **CELL**: Only inter-cell connector nodes (cutouts) are articulation points → key figures at cell boundaries.

**Data source**: Sparrow, Malcolm K. (1991). "The application of network analysis to criminal intelligence." *Social Networks* 13(3):251-274. Sparrow (1993) for structural equivalence.

**Implementation**: NetworkX provides `nx.articulation_points(G)` for undirected graphs. For directed COMMAND graphs, compute on the undirected projection. Cohesion loss proportional to: (components_after_removal - 1) / total_nodes.

## R6: Consciousness Effect Formula Derivation

**Decision**: Five-factor product formula as specified in clarifications:

```
consciousness_delta = action_base[action_type] × tendency_modifier[consciousness_tendency] × cadre_level × cohesion × credibility
```

**Phase 1 simplification**: `action_base` defaults to 1.0 (all action types equivalent). Formula reduces to:

```
consciousness_delta = tendency_modifier[tendency] × cadre_level × cohesion × credibility
```

**tendency_modifier values** (tunable in OrganizationDefines):
- REVOLUTIONARY: +0.15 (positive — raises collective_identity)
- LIBERAL: -0.05 (small negative — slightly erodes oppositional consciousness)
- FASCIST: +0.10 applied to tendency pressure toward FASCIST (not to collective_identity directly)

**Rationale for default magnitudes**:
- Revolutionary organizing is harder but more effective per cadre-hour than liberal service provision
- Liberal effect is small but pervasive (default institutional behavior)
- Fascist mobilization leverages existing resentment (effective but less than revolutionary education)

**credibility derivation** (Phase 1 default): `legitimacy` field for CivilSocietyOrg, `0.5` default for PoliticalFaction (must earn credibility), `legal_standing_credibility[legal_standing]` mapping for StateApparatus (SOVEREIGN=0.8, CHARTERED=0.6, etc.), `employment_share` for Business (proportion of local workforce employed).

**Concurrent effects**: Sum all org deltas (each pre-weighted by their five factors), clamp result to [0, 1] for collective_identity. For dominant_tendency pressure, use strongest weighted tendency (not sum — tendency is categorical, not scalar).

## R7: Sparrow Intelligence Methodology Mapping

**Decision**: Map Sparrow's network analysis capabilities to four boolean fields representing fundamentally different intelligence approaches.

| Capability | What It Reveals | Who Has It |
|-----------|----------------|-----------|
| `centrality_analysis` | Hub nodes, bridges, degree distribution | All agencies (basic) |
| `equivalence_analysis` | Structurally equivalent positions (Sparrow 1993) — finds replaceable vs irreplaceable members | FBI, NSA |
| `template_matching` | Pattern recognition against known org templates (star, cell, etc.) | FBI ("Big Floyd" program) |
| `temporal_analysis` | Communication frequency changes, activation patterns over time | FBI, fusion centers |

**Observation ceiling semantics**: Fraction of true edges visible. ceiling=0.4 means the agency sees at most 40% of real connections. Which 40% depends on capability mix — centrality-only sees high-degree nodes first; temporal sees recently-active edges first.

**Source**: Sparrow 1991 §3-4 for capability taxonomy. Ceiling values are game design estimates, not empirical — exposed as tunable parameters.

## R8: Migration Strategy from Legacy Schemas

**Decision**: One-time migration script. No runtime backward compatibility layer.

**Mapping**:

| Legacy Entity | → Unified Subtype | Key Transformations |
|--------------|-------------------|---------------------|
| F001 "National Revival Movement" (Fascism) | PoliticalFaction | ideology→IdeologicalProfile, consciousness_strategy=FASCIST |
| F002 "Liberal Democratic Alliance" | PoliticalFaction | consciousness_strategy=LIBERAL |
| F003 "Revolutionary Workers Party" (ML) | PoliticalFaction | consciousness_strategy=REVOLUTIONARY |
| F004 "People's Liberation Front" (MLM) | PoliticalFaction | consciousness_strategy=REVOLUTIONARY |
| Inst001 "Systemic Racism" (Social) | *Drop* — not an organization, it's a social relation |
| Inst002 "Policing" (Legal) | StateApparatus | jurisdiction=NATIONAL/STATE (parametric) |
| Inst003 "Mass Media" (Cultural) | CivilSocietyOrg | service_type=MEDIA, tendency=LIBERAL |
| Inst004 "Labor Unions" (Economic) | CivilSocietyOrg | service_type=LABOR, tendency=LIBERAL (per VIII.2) |
| Inst005 "Military" (State) | StateApparatus | jurisdiction=NATIONAL |
| Inst006 "Religious Institutions" (Religious) | CivilSocietyOrg | service_type=RELIGIOUS |
| Inst007 "Higher Education" (Educational) | CivilSocietyOrg | service_type=EDUCATIONAL |

**Note on Inst001 (Systemic Racism)**: This is not an organization — it's a social relation crystallized as an institution. Constitution I.16: "Institution = crystallized social relations." It belongs in the contradiction/community layer, not the organization model. Migration drops it from organization data with a documented rationale.

**OrganizationComponent deprecation**: Add `warnings.warn("OrganizationComponent is deprecated. Use Organization from babylon.models.entities.organization.", DeprecationWarning)` to `__init__` of OrganizationComponent. Keep for backward compatibility through one release cycle. Test suite migrated to test new Organization model.

## R9: WorldState Integration

**Decision**: Add `organizations: dict[str, Organization]` and `key_figures: dict[str, KeyFigure]` to WorldState.

**to_graph() additions**:
```python
for org_id, org in self.organizations.items():
    G.add_node(org_id, _node_type="organization", **org.model_dump())
for kf_id, kf in self.key_figures.items():
    G.add_node(kf_id, _node_type="key_figure", **kf.model_dump())
```

**from_graph() dispatch**:
```python
elif node_type == "organization":
    organizations[node_id] = _reconstruct_organization(data)
elif node_type == "key_figure":
    key_figures[node_id] = KeyFigure(**filtered_data)
```

**Exclusion set**: `organization_excluded = {"effective_capacity", "composition_cache"}` — fields systems compute and write to graph but Organization model doesn't accept.

## R10: OrganizationDefines Parameter Set

**Decision**: New `OrganizationDefines` category in GameDefines with 12 parameters.

| Parameter | Default | Provenance | Description |
|-----------|---------|------------|-------------|
| `elder_capacity_factor` | 0.2 | BLS 65+ LFPR | D'-phase capacity reduction |
| `tendency_modifier_revolutionary` | 0.15 | Game design | Consciousness delta for REVOLUTIONARY |
| `tendency_modifier_liberal` | -0.05 | Game design | Consciousness delta for LIBERAL |
| `tendency_modifier_fascist` | 0.10 | Game design | Tendency pressure for FASCIST |
| `observation_ceiling_local_pd` | 0.2 | Sparrow 1991 (game design calibration) | Local PD intel limit |
| `observation_ceiling_fusion` | 0.5 | Sparrow 1991 (game design calibration) | Fusion center intel limit |
| `observation_ceiling_fbi` | 0.4 | Sparrow 1991 (game design calibration) | FBI intel limit |
| `cohesion_loss_per_key_figure` | 0.2 | Game design | Cohesion drop per removed key figure |
| `min_cohesion_threshold` | 0.05 | Game design | Floor cohesion after all key figures removed |
| `credibility_default_faction` | 0.5 | Game design | Default credibility for PoliticalFaction |
| `credibility_sovereign` | 0.8 | Game design | StateApparatus SOVEREIGN credibility |
| `credibility_chartered` | 0.6 | Game design | StateApparatus CHARTERED credibility |

All exposed in `defines.yaml` under `organization:` key. Loaded via `GameDefines._from_yaml_dict()`.

## R11: Topology as Emergent Property

**Decision**: `internal_topology` is NOT a stored field on Organization. TopologyType is a computed classification derived from the COMMAND edge subgraph.

**Rationale**: You can't declare a topology into existence — the graph speaks the truth. The COMMAND edges between KeyFigures and cadre nodes define the actual network structure. A topology classifier analyzes this structure and returns a TopologyType classification.

**Algorithm**: `classify_topology(org_id, graph) -> TopologyClassification`
1. Extract the COMMAND edge subgraph for nodes in `org.member_node_ids`.
2. Compute on the undirected projection (COMMAND edges are directed, but topology classification uses connectivity).
3. Classify based on structural properties:
   - **STAR**: Single hub node (degree ≥ N-1), all others degree 1.
   - **HIERARCHY**: Tree structure — connected, exactly N-1 edges, acyclic.
   - **MESH**: Near-complete graph — edge density above configurable threshold (default: 0.6).
   - **CELL**: Multiple components linked by bridge nodes (cutouts). Components ≥ 2, bridges exist.
   - **None**: Graph doesn't match any canonical pattern.

**Implications**:
- Organization creation does NOT require topology declaration. Topology emerges after COMMAND edges are established.
- Key figure identification uses the same COMMAND subgraph analysis — it naturally reads the emergent topology.
- An organization with no COMMAND edges has no classifiable topology (returns None).
- Topology can change over time as COMMAND edges are added/removed — this is emergent evolution, not state mutation.

**Alternatives rejected**:
- Stored enum field: Violates materialist principle — declares structure rather than letting it emerge from graph. Rejected per user direction.
- Topology inferred at creation time only: Would miss structural evolution. Rejected.

## R12: Expanded ClassCharacter Enum

**Decision**: ClassCharacter expanded from 3 to 6 values: BOURGEOIS, PETTY_BOURGEOIS, LABOR_ARISTOCRATIC, PROLETARIAN, LUMPEN, CONTESTED.

**Rationale**: A three-value classification (bourgeois/proletarian/contested) collapses intermediate class positions that have materially distinct interests and organizational behaviors:
- **PETTY_BOURGEOIS**: Small business owners, independent professionals — organizations serving their interests (chambers of commerce, small business associations) behave differently from large bourgeois organizations.
- **LABOR_ARISTOCRATIC**: Workers in core imperialist economies receiving imperial rent — their organizations (mainstream trade unions per VIII.2) defend privileges rather than fighting exploitation.
- **LUMPEN**: Street organizations, prison gangs, survival networks — organizations serving lumpen interests have distinctive material basis and tactical repertoire.

**Mapping to existing codebase**: The `ClassPosition` enum in `enums.py` already distinguishes these class positions at the individual/population level. ClassCharacter at the organizational level should mirror the same distinctions.

**Alternatives rejected**:
- Three-value classification: Too coarse. A labor aristocratic union (UAW) and a revolutionary workers' party serve fundamentally different class interests despite both being "working class" organizations. Rejected.
