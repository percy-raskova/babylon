# Data Model: Organization Base Model

**Feature**: 031-organization-base-model
**Date**: 2026-02-27

## Entity Definitions

### New Enums

```
OrgType (StrEnum)
├── STATE_APPARATUS    — Wields state violence/surveillance
├── BUSINESS           — Accumulates capital, employs labor
├── POLITICAL_FACTION  — Contests political power
└── CIVIL_SOCIETY      — Non-state, non-business collective

ClassCharacter (StrEnum)
├── BOURGEOIS          — Serves bourgeois class interests
├── PETTY_BOURGEOIS    — Serves petty bourgeois class interests
├── LABOR_ARISTOCRATIC — Serves labor aristocracy interests
├── PROLETARIAN        — Serves proletarian class interests
├── LUMPEN             — Serves lumpenproletariat interests
└── CONTESTED          — Class character actively contested

TopologyType (StrEnum) — COMPUTED classification, NOT a stored field.
│   Derived from COMMAND edge subgraph analysis. The graph speaks the truth.
├── STAR       — Centralized around single leader (efficient, fragile)
├── HIERARCHY  — Multi-level command chain (scalable, vulnerable at branch points)
├── MESH       — Fully connected peers (resilient, slow to coordinate)
└── CELL       — Isolated cells connected by cutouts (resilient, compartmentalized)

LegalStanding (StrEnum)
├── SOVEREIGN    — State itself (government agencies)
├── CHARTERED    — State-authorized entity (corporations, licensed orgs)
├── REGISTERED   — Officially registered (nonprofits, registered parties)
├── INFORMAL     — No legal registration (neighborhood groups, informal networks)
└── UNDERGROUND  — Explicitly illegal (banned organizations, clandestine cells)

JurisdictionLevel (StrEnum)
├── NATIONAL   — Federal jurisdiction
├── STATE      — State-level jurisdiction
├── COUNTY     — County-level jurisdiction
└── MUNICIPAL  — City/municipal jurisdiction

ServiceType (StrEnum)
├── RELIGIOUS     — Churches, mosques, temples
├── EDUCATIONAL   — Schools, universities, training programs
├── HEALTHCARE    — Hospitals, clinics, health collectives
├── LEGAL_AID     — Legal defense, bail funds
├── MUTUAL_AID    — Direct material support networks
├── CULTURAL      — Arts, cultural preservation organizations
├── MEDIA         — News, broadcasting, publishing
└── LABOR         — Unions, worker centers, cooperatives
```

### Extended EdgeType Values

```
EdgeType (StrEnum) — ADDITIONS to existing enum:
├── MEMBERSHIP   — Organization → SocialClass (weighted: population count)
├── RECRUITMENT  — Organization → SocialClass (active pipeline)
├── EMPLOYMENT   — Business → SocialClass (employer relationship)
├── COMMAND      — KeyFigure → KeyFigure (internal hierarchy)
└── PRESENCE     — Organization → Territory (operational footprint)
```

### Organization (Base Entity)

The foundational agent entity. All subtypes inherit these fields.

| Field | Type | Default | Constraint | Description |
|-------|------|---------|------------|-------------|
| `id` | str | *required* | unique | Organization identifier |
| `name` | str | *required* | non-empty | Human-readable name |
| `org_type` | OrgType | *required* | enum | Discriminator for subtype dispatch |
| `class_character` | ClassCharacter | *required* | enum | Which class this org serves (may differ from composition) |
| `cohesion` | Probability | 0.1 | [0, 1] | Internal unity and coordination |
| `cadre_level` | Probability | 0.0 | [0, 1] | Leadership quality |
| `budget` | Currency | 0.0 | [0, inf) | Available resources |
| `legal_standing` | LegalStanding | REGISTERED | enum | Legal status of the organization |
| `consciousness_tendency` | ConsciousnessTendency | LIBERAL | enum | Ideological tendency pushed on communities |
| `territory_ids` | list[str] | [] | valid territory IDs | Territories where org operates |
| `headquarters_id` | str or None | None | valid territory ID | Primary location |
| `heat` | Probability | 0.0 | [0, 1] | State attention level |
| `is_institution` | bool | False | — | Has crystallized into institution (I.16) |
| `institutional_persistence` | float or None | None | [0, 1] if set | Resistance to dissolution (institutions only) |
| `member_node_ids` | list[str] | [] | valid node IDs | Individual Key Figures and cadre (hybrid membership) |

**Immutability**: `model_config = ConfigDict(frozen=True)`. All mutations produce new instances via `model_copy(update={...})`.

**Discriminated Union**: `org_type` serves as the Pydantic discriminator field. Each subtype declares `org_type: Literal[OrgType.X]`.

**Topology is Emergent**: There is no `internal_topology` field. Topology is a computed classification derived from the COMMAND edges between member nodes via `classify_topology(org, graph) -> TopologyClassification`.

### StateApparatus (Subtype)

Inherits all Organization base fields. `org_type: Literal[OrgType.STATE_APPARATUS]`.

| Field | Type | Default | Constraint | Description |
|-------|------|---------|------------|-------------|
| `jurisdiction` | JurisdictionLevel | *required* | enum | Scope of authority |
| `violence_capacity` | Probability | 0.0 | [0, 1] | Capacity for coercive force |
| `surveillance_capacity` | Probability | 0.0 | [0, 1] | Capacity for surveillance |
| `legal_authority` | list[str] | [] | — | Specific authorities wielded |
| `intel_methodology` | IntelMethodology | *factory* | — | Sparrow-grounded intelligence capabilities |

**Defaults**: `legal_standing=SOVEREIGN`, `consciousness_tendency=LIBERAL` (shifts toward FASCIST at high heat, per clarification Q5).

### Business (Subtype)

Inherits all Organization base fields. `org_type: Literal[OrgType.BUSINESS]`.

| Field | Type | Default | Constraint | Description |
|-------|------|---------|------------|-------------|
| `sector` | str | *required* | — | NAICS sector description |
| `employment_count` | int | 0 | [0, inf) | Number of employees |
| `surplus_extraction_rate` | Coefficient | 0.0 | [0, 1] | Rate of surplus value extraction |
| `revenue` | Currency | 0.0 | [0, inf) | Annual revenue |

**Defaults**: `consciousness_tendency` derived from sector — high-tech/international trends LIBERAL, extractive/autarkic trends FASCIST (per clarification Q5). Configurable per instance.

### PoliticalFaction (Subtype)

Inherits all Organization base fields. `org_type: Literal[OrgType.POLITICAL_FACTION]`.

| Field | Type | Default | Constraint | Description |
|-------|------|---------|------------|-------------|
| `ideology` | str | *required* | — | Ideological label (e.g., "Marxism-Leninism") |
| `is_player` | bool | False | — | Is this the player's faction? |
| `relationship_to_player` | str | "neutral" | — | Relationship state |

**Note**: `consciousness_tendency` is the primary gameplay-relevant field (renamed to `consciousness_strategy` in spec for semantic clarity, but uses the same ConsciousnessTendency enum value from the base class).

### CivilSocietyOrg (Subtype)

Inherits all Organization base fields. `org_type: Literal[OrgType.CIVIL_SOCIETY]`.

| Field | Type | Default | Constraint | Description |
|-------|------|---------|------------|-------------|
| `service_type` | ServiceType | *required* | enum | Domain of service provision |
| `legitimacy` | Probability | 0.5 | [0, 1] | Community trust/credibility |

**Note**: `legitimacy` doubles as the `credibility` factor in the consciousness effect formula for this subtype.

### IntelMethodology (Supporting Model)

| Field | Type | Default | Constraint | Description |
|-------|------|---------|------------|-------------|
| `centrality_analysis` | bool | False | — | Can identify hub nodes and bridges |
| `equivalence_analysis` | bool | False | — | Can find structurally equivalent positions (Sparrow 1993) |
| `template_matching` | bool | False | — | Can match against known org templates |
| `temporal_analysis` | bool | False | — | Can detect activation pattern changes over time |
| `observation_ceiling` | Probability | 0.2 | [0, 1] | Max fraction of true topology observable |

**Frozen**: `ConfigDict(frozen=True)`.

**Preset configurations** (factory methods or tunable defaults):

| Agency Type | centrality | equivalence | template | temporal | ceiling |
|-------------|-----------|-------------|----------|----------|---------|
| Local PD | True | False | False | False | 0.2 |
| Fusion Center | True | False | False | True | 0.5 |
| FBI | True | True | True | True | 0.4 |

### KeyFigure (Entity)

Individual node within organizational topology. Stored as separate graph node (`_node_type="key_figure"`).

| Field | Type | Default | Constraint | Description |
|-------|------|---------|------------|-------------|
| `id` | str | *required* | unique | Key figure identifier |
| `name` | str | *required* | non-empty | Name |
| `organization_id` | str | *required* | valid org ID | Parent organization |
| `role` | str | *required* | — | Position title/function |
| `structural_importance` | Probability | 0.5 | [0, 1] | Topological criticality (computed) |
| `is_singleton` | bool | False | — | No structural equivalent (Sparrow) |

**Frozen**: `ConfigDict(frozen=True)`.

### OrganizationDefines (GameDefines Category)

All tunable coefficients for the organization system.

| Field | Type | Default | Provenance | Description |
|-------|------|---------|------------|-------------|
| `elder_capacity_factor` | float | 0.2 | BLS 65+ LFPR | D'-phase capacity scalar |
| `tendency_modifier_revolutionary` | float | 0.15 | Game design | CI delta for REVOLUTIONARY |
| `tendency_modifier_liberal` | float | -0.05 | Game design | CI delta for LIBERAL |
| `tendency_modifier_fascist` | float | 0.10 | Game design | Tendency pressure for FASCIST |
| `observation_ceiling_local_pd` | float | 0.2 | Sparrow calibration | Local PD ceiling |
| `observation_ceiling_fusion` | float | 0.5 | Sparrow calibration | Fusion center ceiling |
| `observation_ceiling_fbi` | float | 0.4 | Sparrow calibration | FBI ceiling |
| `cohesion_loss_per_key_figure` | float | 0.2 | Game design | Cohesion drop per KF removal |
| `min_cohesion_threshold` | float | 0.05 | Game design | Floor cohesion |
| `credibility_default_faction` | float | 0.5 | Game design | Default PoliticalFaction credibility |
| `credibility_sovereign` | float | 0.8 | Game design | SOVEREIGN standing credibility |
| `credibility_chartered` | float | 0.6 | Game design | CHARTERED standing credibility |
| `violence_capacity_default` | float | 0.5 | Game design (pending Phase 2/3) | Default StateApparatus violence capacity |
| `surveillance_capacity_default` | float | 0.3 | Game design (pending Phase 2/3 attention threads) | Default StateApparatus surveillance capacity |

### Computed Types (Calculator Results)

**TopologyClassification** (frozen):
- `topology_type`: TopologyType — Classified topology (STAR/HIERARCHY/MESH/CELL)
- `articulation_points`: list[str] — Node IDs that are articulation points
- `component_count`: int — Number of connected components in COMMAND subgraph
- `is_connected`: bool — Whether the COMMAND subgraph is connected

TopologyType is NEVER stored on the Organization model. It is computed from the COMMAND edges between member nodes (KeyFigures and cadre) by analyzing the graph structure. Classification algorithm:
- **STAR**: Single node with degree ≥ (N-1), all other nodes degree 1
- **HIERARCHY**: Tree structure (connected, N-1 edges, acyclic)
- **MESH**: Near-complete graph (edge density > threshold, e.g. 0.6)
- **CELL**: Multiple connected components linked by bridge nodes (cutouts)
- **Unclassified**: Graph doesn't match any canonical pattern (returns None)

**ConsciousnessDelta** (frozen):
- `collective_identity_delta`: float — Change to target community's CI
- `tendency_pressure`: ConsciousnessTendency — Direction of pressure
- `tendency_magnitude`: float — Strength of tendency pressure
- `source_org_id`: str — Which organization caused this

**AggregatedEffect** (frozen):
- `total_ci_delta`: float — Sum of all organization CI deltas (may be positive or negative)
- `dominant_tendency`: ConsciousnessTendency | None — Tendency with strongest weighted presence (None if tied and no change)
- `tendency_weights`: dict[ConsciousnessTendency, float] — Magnitude per tendency for tie analysis
- `new_ci`: float — Clamped [0, 1] result after applying total_ci_delta to current CI

**CompositionResult** (frozen):
- `distribution`: dict[str, float] — Proportional breakdown (key depends on axis)
- `total_members`: float — Total membership count (from both block edges and individual nodes)
- `axis`: str — "class" | "community" | "lifecycle"

## Relationships

```
Organization ──MEMBERSHIP──► SocialClass (weighted by population count)
Organization ──RECRUITMENT──► SocialClass (active pipeline)
Organization ──PRESENCE──► Territory (operational footprint)
Business ──EMPLOYMENT──► SocialClass (employer relationship)
KeyFigure ──COMMAND──► KeyFigure (internal hierarchy)
KeyFigure ──belongs to──► Organization (via organization_id field)
Organization ──acts on──► CommunityState (via consciousness effect, not a stored edge)
```

## Validation Rules

1. **Organization.territory_ids**: All IDs must reference existing Territory nodes in the graph.
2. **Organization.headquarters_id**: If set, must be in territory_ids.
3. **Organization.institutional_persistence**: Must be None if is_institution is False.
4. **Organization.member_node_ids**: All IDs must reference existing KeyFigure or cadre nodes.
5. **StateApparatus.legal_standing**: Should be SOVEREIGN (soft constraint — warning, not error).
6. **Business.employment_count**: Must be non-negative integer.
7. **ClassDistribution constraint**: class_composition proportions sum to 1.0 (±0.01 tolerance).
8. **Lifecycle constraint**: lifecycle_composition proportions sum to 1.0 (±0.01 tolerance).
9. **KeyFigure.organization_id**: Must reference existing Organization node.
10. **Consciousness effect bounds**: collective_identity_delta clamped to keep CI in [0, 1] after application.

## State Transitions

Phase 1 scope is limited — organizations are data models, not autonomous actors. State changes happen through external system calls producing new frozen instances:

1. **Cohesion change**: Key figure removal → new Organization with reduced cohesion (via model_copy).
2. **Heat change**: State attention events → new Organization with updated heat.
3. **Budget change**: Resource transfer events → new Organization with updated budget.
4. **Membership change**: Recruitment/attrition → new MEMBERSHIP edges, updated member_node_ids.
5. **Legal standing change**: State action (ban, charter) → new Organization with new legal_standing.

All transitions deferred to Phase 2 (OODA) for autonomous execution. Phase 1 provides the data structure; external test code or future systems drive state changes.
