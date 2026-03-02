# Implementation Plan: Ternary Consciousness Model

**Branch**: `034-ternary-consciousness` | **Date**: 2026-03-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/034-ternary-consciousness/spec.md`

## Summary

Replace the stipulated scalar `CommunityConsciousness` model (3 stored fields: `collective_identity`, `dominant_tendency`, `ideological_contestation`) with a ternary 2-simplex model `TernaryConsciousness` where coordinates `(r, l, f)` are derived from the organizational landscape operating within each community hyperedge. The ternary model preserves backward compatibility by exposing the old fields as computed properties. A substrate floor per community type sets a minimum revolutionary consciousness that persists even when all organizations are destroyed.

## Technical Context

**Language/Version**: Python 3.12+ (existing project stack)
**Primary Dependencies**: Pydantic 2.x (frozen models, validators), NetworkX 3.x (graph queries), XGI 0.10 (hypergraph memberships)
**Storage**: In-memory via GraphProtocol. Postgres schema migration for persistence (r, l, f columns). No new database tables.
**Testing**: pytest with `@pytest.mark.unit` and `@pytest.mark.math` markers
**Target Platform**: Linux server (simulation engine)
**Project Type**: Single project — `src/babylon/`, `tests/`
**Performance Goals**: Ternary computation adds < 1ms per tick per community (14 communities in Detroit test case = < 14ms total)
**Constraints**: Simplex constraint `r + l + f = 1.0` enforced at type level. All existing consumers of `collective_identity`, `dominant_tendency`, `ideological_contestation` MUST continue to work without modification.
**Scale/Scope**: 14 community types, ~50 organizations in Detroit test case, per-tick recomputation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I.6 Solidarity as Edge Mode | PASS | Ternary model does not change edge mode mechanics; consciousness is orthogonal to edge type |
| I.7 Quantitative → Qualitative | PASS | r, l, f are quantities (floats). dominant_tendency is quality (enum). Threshold is argmax. |
| I.12 Catastrophe Surface | PASS | Assimilation trap is a fold geometry — high solidarity + low r routes to fascism, not revolution |
| II.2 Primitives vs Derived | PASS | Ternary coordinates are DERIVED from organizational membership (a primitive). Not stored as independent state. |
| II.5 AI Observes, Never Controls | PASS | No AI involvement in consciousness computation |
| II.6 State is Data, Engine is Transformation | PASS | TernaryConsciousness is frozen Pydantic. Computation is a pure function. |
| II.7 Edges vs Hyperedges | PASS | Communities remain XGI hyperedges. Org-community connections are NetworkX edges. Layers separate. |
| III.1 No Magic Constants | PASS | Substrate floor traced to Vera incarceration data + Chetty mobility. SYNTHETIC provenance flagged. |
| III.2 Falsifiability Required | PASS | Prediction: removing all orgs drops r to substrate floor, not zero. Falsifiable via test. |
| III.4 Data Source Traceability | PARTIAL | BJS/Vera and Chetty are documented. ACLED and SPLC deferred to post-MVP. |
| VI.1 Material Base First | PASS | Consciousness derived from organizational landscape (material), not stipulated |
| VIII.1 Solidarity as Scalar | PASS | Solidarity remains edge mode (qualitative). Consciousness is the separate quantity. |

**Post-design re-check**: All gates pass. III.4 is PARTIAL because ACLED/SPLC data sources are deferred per the spec's MVP data strategy — this is an acknowledged scope choice, not a violation.

## Project Structure

### Documentation (this feature)

```text
specs/034-ternary-consciousness/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research findings
├── data-model.md        # Entity definitions and migration table
├── quickstart.md        # Dev setup and verification
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/
├── models/entities/
│   ├── consciousness.py     # NEW: TernaryConsciousness, SubstrateFloor, ProvenanceLevel
│   └── community.py         # MODIFIED: CommunityState.consciousness type change
├── formulas/
│   └── consciousness.py     # NEW: compute_ternary_consciousness() pure function
├── engine/systems/
│   └── community.py         # MODIFIED: call ternary computation in step()
├── bifurcation/
│   └── consciousness.py     # UNCHANGED: reads r via collective_identity property
├── ooda/
│   └── layer3.py            # MODIFIED: remove direct CI writes, rely on org landscape
├── persistence/
│   ├── postgres_schema.py   # MODIFIED: add r, l, f columns
│   └── postgres_runtime.py  # MODIFIED: read/write ternary columns

tests/
├── unit/models/
│   └── test_ternary_consciousness.py  # NEW: model tests
├── unit/formulas/
│   └── test_consciousness_computation.py  # NEW: computation tests
├── unit/models/
│   └── test_community_models.py       # EXISTING: must pass unchanged
├── unit/engine/systems/
│   └── test_community_system.py       # EXISTING: must pass unchanged
├── unit/formulas/
│   └── test_community_formulas.py     # EXISTING: must pass unchanged
└── unit/bifurcation/
    └── test_monitor.py                # EXISTING: must pass unchanged
```

**Structure Decision**: Single project layout matching existing codebase. New models go in `models/entities/consciousness.py` (not inline in community.py) to keep community.py from growing further. New formula goes in `formulas/consciousness.py` following the existing one-module-per-formula pattern.

## Implementation Strategy

### Phase 1: TernaryConsciousness Model (US3 backward compat, P1)

1. Create `TernaryConsciousness` frozen Pydantic model with r, l, f fields
2. Add simplex validator (`r + l + f ≈ 1.0`)
3. Add computed properties: `collective_identity` → r, `dominant_tendency` → argmax, `ideological_contestation` → Shannon entropy, `assimilation_ratio` → f/(l+f)
4. Create `SubstrateFloor` model with provenance metadata
5. Create `ProvenanceLevel` enum
6. Write tests: simplex constraint, backward-compat properties, edge cases
7. **Verify**: All new model tests pass

### Phase 2: CONSCIOUSNESS_DEFAULTS Migration (US3 continuation, P1)

1. Create ternary versions of all 14 CONSCIOUSNESS_DEFAULTS entries
2. Verify backward-compatible derivations match old values within tolerance
3. Replace `CommunityState.consciousness` type from `CommunityConsciousness` to `TernaryConsciousness`
4. Update import-time exhaustiveness check
5. **Verify**: All existing test_community_models.py tests pass unchanged

### Phase 3: Ternary Computation Function (US1, P1)

1. Create `compute_ternary_consciousness()` pure function in `formulas/consciousness.py`
2. Input: community_type, org landscape (list of org data with tendency + membership density + budget), substrate floor
3. Algorithm:
   - Sum weighted org contributions per tendency: `w_i = membership_density_i * capacity_factor_i`
   - Unorganized fraction defaults to liberal: `unorg = 1.0 - sum(membership_densities)`
   - Raw r = sum of revolutionary org weights + substrate floor
   - Raw l = sum of liberal org weights + unorganized fraction
   - Raw f = sum of fascist org weights
   - Apply substrate floor: `r = max(r_raw, substrate_floor)`
   - Normalize to simplex
4. Write tests: all 6 acceptance scenarios from US1, edge cases
5. **Verify**: Computation tests pass, doctests pass

### Phase 4: CommunitySystem Integration (US1 continuation, P1)

1. Wire `compute_ternary_consciousness()` into `CommunitySystem.step()` after building hypergraph
2. For each community: query org-community MEMBERSHIP overlaps, call computation, update CommunityState
3. Remove direct consciousness mutation in OODA layer3.py (the org landscape mutation already handles this — EDUCATE/AGITATE/ORGANIZE actions change membership and edge types, which the ternary computation reads)
4. **Verify**: test_community_system.py passes unchanged, new integration tests pass

### Phase 5: Substrate Floor with Empirical Proxies (US2, P2)

1. Create `SUBSTRATE_FLOOR_DEFAULTS` dict with provenance
2. Implement substrate floor computation from Vera incarceration data + Chetty mobility data
3. Wire into ternary computation
4. **Verify**: Substrate floor tests pass, COINTELPRO scenario (US1-AS4) confirmed

### Phase 6: Bifurcation Integration (US5, P2)

1. Add `assimilation_ratio` consumption to bifurcation analysis
2. Add crisis-fragile marker on low-r solidarity edges
3. Test assimilation trap scenario: high solidarity + low r → fascist outcome
4. **Verify**: All bifurcation tests pass, assimilation trap distinguished from revolution

### Phase 7: Persistence Migration (cross-cutting)

1. Add r, l, f columns to postgres_schema.py community_state DDL
2. Update postgres_runtime.py INSERT/UPDATE/SELECT for ternary columns
3. **Verify**: Persistence contract tests pass

### Phase 8: Observation Gap Anisotropy (FR-009, P2)

1. Model anisotropic observation error: higher error on r than on l/f ratio
2. Integrate with state AttentionThread intelligence estimates
3. **Verify**: State underestimates r more than l/f position

## Key Design Decisions

### D1: Spec Correction — resource_base → budget

The spec references `resource_base` as a field on Organization. This field does not exist. The correct field is `budget: Currency`. The capacity factor in the consciousness computation uses `float(org.budget)` normalized against a reference budget value, or alternatively uses `cadre_level * cohesion * legitimacy` as the capacity multiplier (which is the existing pattern in `organizations/consciousness.py:71-118`).

**Recommendation**: Use the existing consciousness delta formula's capacity factors (`cadre_level * cohesion * credibility`) rather than raw budget. This reuses proven code and avoids introducing a new normalization constant.

### D2: Two Consciousness Representations → One

Currently, consciousness exists in two forms: Pydantic model (`CommunityState.consciousness`) and raw graph dict (`graph.nodes[community_id]["collective_identity"]`). The ternary model unifies these by making consciousness a derived quantity. The graph dict representation becomes the source during OODA processing (orgs mutate membership/edges), and the Pydantic model is recomputed from the graph at the end of each tick.

### D3: OODA Consciousness Mutation Path

The current OODA layer writes `collective_identity_delta` directly to graph nodes (layer3.py:89-91). Under the ternary model, OODA actions (EDUCATE, AGITATE, ORGANIZE) modify the organizational landscape (membership edges, edge types, org resources) instead of directly writing CI. The ternary computation then reads these changes and produces updated consciousness. This is a design improvement — consciousness becomes a derived quantity with no independent mutation path.

### D4: Org Capacity Factor

For the organizational landscape contribution weight, use:
`w_i = (membership_in_community_i / community_population) * cadre_level_i * cohesion_i`

This reuses existing org attributes without introducing new fields. `budget` is excluded from the initial formula because it requires a normalization constant (what is "1.0 budget"?). Can be added during calibration if needed.

## Complexity Tracking

No constitution violations. No complexity justifications needed.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| OODA layer3.py direct CI writes conflict with ternary computation | HIGH | MEDIUM | Phase 4 removes direct writes; org landscape mutations are the path |
| Backward-compat property derivation doesn't match old defaults | MEDIUM | HIGH | Migration table verified in Phase 2 with tolerance checks |
| Substrate floor empirical data unavailable for some community types | HIGH | LOW | SYNTHETIC provenance with logged warnings; 0.0 default is safe |
| Performance: per-tick graph queries for 14 communities | LOW | LOW | Detroit test case is small; graph queries are O(edges) per community |
