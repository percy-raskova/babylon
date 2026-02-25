# Research: Hypergraph Community Layer

**Phase 0 Output** | **Date**: 2026-02-25

## Research Findings

### R1: XGI Hypergraph API for Community Membership

**Decision**: Use XGI 0.10 `Hypergraph` with string-keyed hyperedge IDs matching `CommunityType` enum values.

**Rationale**: XGI is already a project dependency (`xgi = "^0.10"` in pyproject.toml). The API provides native n-ary membership queries (`H.nodes.memberships()`), incidence matrix computation (`xgi.incidence_matrix()`), and hyperedge attributes — exactly what the spec requires. Performance is trivial at our scale (1000 nodes, 50 hyperedges — all operations <10ms).

**Key API patterns**:
- `H.add_edge(members, idx=community_type.value, **state_attrs)` — use `idx` not `id` (breaking change in v0.9)
- `H.nodes.memberships(agent_id)` → `set[str]` of community IDs containing that agent
- `xgi.incidence_matrix(H, sparse=True)` → `csr_array` (nodes x edges)
- `I @ I.T` → sparse overlap matrix (nodes x nodes), `O[i,j]` = shared community count
- Hyperedge attributes: `H.edges[edge_id]["heat"]` for read/write

**Alternatives considered**: Bipartite graph in NetworkX (rejected — loses community-as-unit semantics, Constitution VIII.9). Custom adjacency dict (rejected — reinvents XGI poorly).

### R2: Integration with Existing Solidarity System

**Decision**: New `CommunitySystem` runs at position 6 in `_DEFAULT_SYSTEMS` (before `SolidaritySystem` at position 7). It computes solidarity potential from community overlap and writes an amplified `solidarity_strength` onto existing SOLIDARITY edges.

**Rationale**: `solidarity_potential` does not exist in the codebase — only in spec documents. `solidarity_strength` on `Relationship` model is the realized scalar that `SolidaritySystem` and `ConsciousnessSystem` already consume. The cleanest integration: `CommunitySystem` amplifies `solidarity_strength` based on community overlap, then `SolidaritySystem` transmits consciousness using the amplified value.

**Integration flow**:
```
CommunitySystem.step()
  ├── Alpha-smooth community state (heat, cohesion, infrastructure decay)
  ├── Compute overlap matrix (cached, rebuilt only on membership change)
  ├── For each SOLIDARITY edge: amplify solidarity_strength by community infrastructure multiplier
  └── Compute threat scores and write to node attributes
        ↓
SolidaritySystem.step()
  └── Reads amplified solidarity_strength → transmits consciousness as before
```

**Alternatives considered**: New formula in `FormulaRegistry` (rejected — solidarity potential is a system-level computation, not a single formula). Modifying `SolidaritySystem` directly (rejected — violates single responsibility; community logic is a separate concern).

### R3: Reproduction Cost Modifier Integration

**Decision**: Community reproduction cost modifiers are applied to `SocialClass.subsistence_multiplier` at entity initialization and on membership change events (between ticks). Not computed per-tick.

**Rationale**: `VitalitySystem` runs at position 1 — before any community system could modify costs. But community membership is rare-event (FR-013: changes processed between ticks), so the modifiers can be pre-baked into entity state. `SocialClass.subsistence_multiplier` (line 375 of social_class.py) already exists and is read by `VitalitySystem._calculate_deaths()`. The compound modifier is: `base_multiplier × Π(community.reproduction_cost_modifier for community in memberships)`.

**Extension point**: `SocialClass.subsistence_multiplier` field at social_class.py:375. Currently auto-assigned from `SocialRole` in `_set_subsistence_multiplier_from_role()`. We add a `community_cost_modifier: float = 1.0` field that multiplies with the role-based multiplier.

**Alternatives considered**: Per-tick `s_bio`/`s_class` override in CommunitySystem (rejected — VitalitySystem runs first; would require reordering the entire pipeline). New field on SocialClass replacing `subsistence_multiplier` (rejected — breaks existing role-based subsistence logic).

### R4: System Registration and Ordering

**Decision**: `CommunitySystem` at position 6 in `_DEFAULT_SYSTEMS`, between `ReserveArmySystem` (5) and `SolidaritySystem` (currently 6, becomes 7).

**Rationale**: CommunitySystem must run before SolidaritySystem so that solidarity_strength amplification is visible to solidarity transmission. It does not need to run before VitalitySystem because reproduction cost modifiers are pre-baked at initialization. The alpha-smoothing of community state (heat decay, infrastructure decay) is independent of production/extraction systems and can run anywhere before solidarity.

**Materialist causality**: Reserve army dynamics (position 5) determine class composition → community system reads class positions and computes solidarity potential → solidarity system (position 7) transmits consciousness using amplified strength.

### R5: Codebase Convention Compliance

**Decision**: Follow all existing patterns exactly.

| Convention | Implementation |
|-----------|---------------|
| Enums | New enums in `enums.py` inheriting `StrEnum`, lowercase `snake_case` values |
| Models | `ConfigDict(frozen=True)` for `CommunityState`, `CommunityMembership` |
| Constrained types | `Probability` for heat/cohesion/infrastructure/visibility, `Coefficient` for modifiers |
| System protocol | `name: str` class attribute + `step(graph, services, context)` with auto-wrap guard |
| ServiceContainer | Add `community_hypergraph: Any = field(default=None)` optional field |
| Formula registration | Register `solidarity_potential`, `threat_score`, `infrastructure_decay` in `FormulaRegistry.default()` |
| GraphProtocol | Read/write via `graph.get_node()`, `graph.update_node()`, `graph.query_edges()` |
| Testing | `@pytest.mark.unit` for models/formulas, `@pytest.mark.topology` for integration |

### R6: Hypergraph Lifecycle and Caching

**Decision**: Build hypergraph at simulation initialization. Cache overlap matrix. Rebuild both only on membership change events.

**Rationale**: FR-013 requires membership changes between ticks, not during. The hypergraph and overlap matrix are expensive to rebuild (relative to per-tick operations) but change rarely. Caching the overlap matrix avoids recomputing `I @ I.T` every tick when membership hasn't changed.

**Implementation**: `CommunitySystem` stores `_cached_overlap_matrix` and a `_membership_version` counter. When a membership change event is detected (via event bus or context flag), the system rebuilds the hypergraph and overlap matrix. Otherwise, it reuses the cache.
