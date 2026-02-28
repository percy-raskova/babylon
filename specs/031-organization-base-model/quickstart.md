# Quickstart: Organization Base Model Integration Tests

**Feature**: 031-organization-base-model
**Date**: 2026-02-27

## Purpose

Nine integration test scenarios that validate the Organization Base Model end-to-end. Each scenario provides exact inputs, expected outputs, and the user story it validates. These scenarios form the acceptance test suite.

---

## Scenario 1: Detroit PD as StateApparatus (US1, SC-001)

**Goal**: Instantiate a StateApparatus with Sparrow-grounded intelligence methodology.

**Input**:
```python
detroit_pd = StateApparatus(
    id="org_detroit_pd",
    name="Detroit Police Department",
    org_type=OrgType.STATE_APPARATUS,
    class_character=ClassCharacter.BOURGEOIS,
    # NOTE: internal_topology is NOT set here — it is emergent from COMMAND edges
    cohesion=0.7,
    cadre_level=0.5,
    budget=Currency(300_000_000.0),
    legal_standing=LegalStanding.SOVEREIGN,
    consciousness_tendency=ConsciousnessTendency.LIBERAL,
    territory_ids=["territory_detroit"],
    headquarters_id="territory_detroit",
    heat=Probability(0.0),
    jurisdiction=JurisdictionLevel.MUNICIPAL,
    violence_capacity=Probability(0.7),
    surveillance_capacity=Probability(0.4),
    legal_authority=["arrest", "search_warrant", "civil_asset_forfeiture"],
    intel_methodology=IntelMethodology(
        centrality_analysis=True,
        equivalence_analysis=False,
        template_matching=False,
        temporal_analysis=False,
        observation_ceiling=Probability(0.2),
    ),
)
```

**Expected**:
- `detroit_pd.org_type == OrgType.STATE_APPARATUS`
- `detroit_pd.legal_standing == LegalStanding.SOVEREIGN`
- `detroit_pd.intel_methodology.observation_ceiling == 0.2`
- `detroit_pd.intel_methodology.centrality_analysis is True`
- `detroit_pd.intel_methodology.equivalence_analysis is False`
- Instance is frozen: `detroit_pd.heat = 0.5` raises `ValidationError`.

---

## Scenario 2: Ford Motor as Business (US1, SC-001)

**Goal**: Instantiate a Business with QCEW-derived employment data.

**Input**:
```python
ford = Business(
    id="org_ford",
    name="Ford Motor Company",
    org_type=OrgType.BUSINESS,
    class_character=ClassCharacter.BOURGEOIS,
    # NOTE: internal_topology is NOT set here — it is emergent from COMMAND edges
    cohesion=0.8,
    cadre_level=0.2,
    budget=Currency(158_000_000_000.0),
    legal_standing=LegalStanding.CHARTERED,
    consciousness_tendency=ConsciousnessTendency.LIBERAL,
    territory_ids=["territory_detroit", "territory_dearborn"],
    headquarters_id="territory_dearborn",
    heat=Probability(0.0),
    sector="Motor Vehicle Manufacturing",
    employment_count=31_000,
    surplus_extraction_rate=Coefficient(0.45),
    revenue=Currency(158_000_000_000.0),
)
```

**Expected**:
- `ford.org_type == OrgType.BUSINESS`
- `ford.employment_count == 31_000`
- `ford.surplus_extraction_rate == 0.45`
- `ford.consciousness_tendency == ConsciousnessTendency.LIBERAL`

---

## Scenario 3: Revolutionary Workers Party as PoliticalFaction (US1, SC-001)

**Goal**: Instantiate the player's revolutionary faction.

**Input**:
```python
rwp = PoliticalFaction(
    id="org_rwp",
    name="Revolutionary Workers Party",
    org_type=OrgType.POLITICAL_FACTION,
    class_character=ClassCharacter.PROLETARIAN,
    # NOTE: internal_topology is NOT set here — it is emergent from COMMAND edges
    cohesion=0.6,
    cadre_level=0.7,
    budget=Currency(5_000.0),
    legal_standing=LegalStanding.REGISTERED,
    consciousness_tendency=ConsciousnessTendency.REVOLUTIONARY,
    territory_ids=["territory_detroit"],
    headquarters_id="territory_detroit",
    heat=Probability(0.3),
    ideology="Marxism-Leninism",
    is_player=True,
    relationship_to_player="self",
)
```

**Expected**:
- `rwp.org_type == OrgType.POLITICAL_FACTION`
- `rwp.consciousness_tendency == ConsciousnessTendency.REVOLUTIONARY`
- `rwp.is_player is True`
- Topology is computed from COMMAND edges, not stored on the model

---

## Scenario 4: Mainstream Church as CivilSocietyOrg (US1, SC-001)

**Goal**: Instantiate a liberal civil society organization.

**Input**:
```python
church = CivilSocietyOrg(
    id="org_first_baptist",
    name="First Baptist Church of Detroit",
    org_type=OrgType.CIVIL_SOCIETY,
    class_character=ClassCharacter.CONTESTED,
    # NOTE: internal_topology is NOT set here — it is emergent from COMMAND edges
    cohesion=0.8,
    cadre_level=0.3,
    budget=Currency(500_000.0),
    legal_standing=LegalStanding.REGISTERED,
    consciousness_tendency=ConsciousnessTendency.LIBERAL,
    territory_ids=["territory_detroit"],
    headquarters_id="territory_detroit",
    heat=Probability(0.0),
    service_type=ServiceType.RELIGIOUS,
    legitimacy=Probability(0.7),
)
```

**Expected**:
- `church.org_type == OrgType.CIVIL_SOCIETY`
- `church.service_type == ServiceType.RELIGIOUS`
- `church.legitimacy == 0.7`
- `church.consciousness_tendency == ConsciousnessTendency.LIBERAL`

---

## Scenario 5: Class Composition (US2, SC-002)

**Goal**: Calculate proportional class breakdown of an organization's membership.

**Setup**: Organization "org_rwp" has MEMBERSHIP edges:
- `org_rwp → proletariat_industrial` (weight=500)
- `org_rwp → proletariat_service` (weight=300)
- `org_rwp → petty_bourgeoisie` (weight=50)

**Call**:
```python
result = class_composition(org_rwp, graph)
```

**Expected**:
```python
result.distribution == {
    "proletariat_industrial": pytest.approx(500 / 850),   # ~0.588
    "proletariat_service": pytest.approx(300 / 850),      # ~0.353
    "petty_bourgeoisie": pytest.approx(50 / 850),         # ~0.059
}
result.total_members == pytest.approx(850.0)
result.axis == "class"
# Proportions sum to 1.0 (±0.01)
assert abs(sum(result.distribution.values()) - 1.0) < 0.01
```

---

## Scenario 6: Lifecycle Composition (US2, SC-002)

**Goal**: Calculate D/P/D' distribution within an organization's membership.

**Setup**: Organization "org_first_baptist" has MEMBERSHIP edges to SocialClass nodes whose `lifecycle_phase` attributes are:
- D-phase (youth): 200 members
- P-phase (adult): 600 members
- D'-phase (elder): 200 members

**Call**:
```python
result = lifecycle_composition(org_first_baptist, graph)
```

**Expected**:
```python
result.distribution == {
    "D": pytest.approx(200 / 1000),    # 0.2
    "P": pytest.approx(600 / 1000),    # 0.6
    "D_prime": pytest.approx(200 / 1000),  # 0.2
}
result.total_members == pytest.approx(1000.0)
result.axis == "lifecycle"
```

---

## Scenario 7: Consciousness Effect — Revolutionary Faction (US3, SC-003)

**Goal**: Revolutionary org with high cadre raises collective_identity.

**Setup**:
```python
rwp = PoliticalFaction(
    consciousness_tendency=ConsciousnessTendency.REVOLUTIONARY,
    cadre_level=0.7,
    cohesion=0.6,
    ...  # other fields as Scenario 3
)
defines = OrganizationDefines()  # default parameters
```

**Call**:
```python
delta = consciousness_effect(rwp, target_community="territory_detroit", defines=defines)
```

**Expected**:
```python
# tendency_modifier[REVOLUTIONARY] = 0.15
# credibility for PoliticalFaction = 0.5 (default)
# ci_delta = 0.15 × 0.7 × 0.6 × 0.5 = 0.0315
delta.collective_identity_delta == pytest.approx(0.0315)
delta.tendency_pressure == ConsciousnessTendency.REVOLUTIONARY
delta.tendency_magnitude == pytest.approx(0.0315)
delta.source_org_id == "org_rwp"
```

---

## Scenario 8: Key Figure Identification (US5, SC-005)

**Goal**: Identify structurally critical nodes from COMMAND edge analysis.

**Setup**: Organization "org_first_baptist" with COMMAND edges forming a star pattern:
- Center node: `kf_pastor` (Pastor)
- Leaf nodes: `kf_deacon_1`, `kf_deacon_2`, `kf_deacon_3`
- COMMAND edges: `kf_pastor → kf_deacon_1`, `kf_pastor → kf_deacon_2`, `kf_pastor → kf_deacon_3`

**Call**:
```python
# First classify the emergent topology
topo = classify_topology(org_first_baptist, graph)
assert topo.topology_type == TopologyType.STAR

# Then identify key figures
key_figures = identify_key_figures(org_first_baptist, graph)
```

**Expected**:
```python
# In emergent STAR topology, center is the sole articulation point
assert len(key_figures) == 1
assert key_figures[0].id == "kf_pastor"
assert key_figures[0].is_singleton is True
assert key_figures[0].structural_importance > 0.8  # High criticality
```

**Cohesion Effect of Removal**:
```python
# Removing the pastor from STAR topology
# cohesion_loss = defines.cohesion_loss_per_key_figure = 0.2
# But STAR center removal is catastrophic — could lose more
new_cohesion = max(
    church.cohesion - defines.cohesion_loss_per_key_figure,
    defines.min_cohesion_threshold
)
# new_cohesion = max(0.8 - 0.2, 0.05) = 0.6
assert new_cohesion == pytest.approx(0.6)
```

---

## Scenario 9: Graph Round-Trip (US1, SC-001/SC-007)

**Goal**: Organization survives WorldState serialization round-trip.

**Setup**: Create a WorldState with one organization of each subtype:
```python
world = WorldState(
    organizations={
        "org_detroit_pd": detroit_pd,   # StateApparatus
        "org_ford": ford,               # Business
        "org_rwp": rwp,                 # PoliticalFaction
        "org_first_baptist": church,    # CivilSocietyOrg
    },
    key_figures={
        "kf_pastor": pastor_figure,
        "kf_deacon_1": deacon_1,
    },
    ...  # other WorldState fields
)
```

**Round-Trip**:
```python
graph = world.to_graph()
reconstructed = WorldState.from_graph(graph)
```

**Expected**:
```python
# All organizations survive
assert len(reconstructed.organizations) == 4

# Correct subtypes reconstructed
assert isinstance(reconstructed.organizations["org_detroit_pd"], StateApparatus)
assert isinstance(reconstructed.organizations["org_ford"], Business)
assert isinstance(reconstructed.organizations["org_rwp"], PoliticalFaction)
assert isinstance(reconstructed.organizations["org_first_baptist"], CivilSocietyOrg)

# Field fidelity
assert reconstructed.organizations["org_ford"].employment_count == 31_000
assert reconstructed.organizations["org_detroit_pd"].intel_methodology.observation_ceiling == 0.2
assert reconstructed.organizations["org_rwp"].is_player is True
assert reconstructed.organizations["org_first_baptist"].legitimacy == 0.7

# Key figures survive
assert len(reconstructed.key_figures) == 2
assert reconstructed.key_figures["kf_pastor"].organization_id == "org_first_baptist"

# Graph node types
assert graph.nodes["org_detroit_pd"]["_node_type"] == "organization"
assert graph.nodes["kf_pastor"]["_node_type"] == "key_figure"
```

---

## Coverage Matrix

| Scenario | User Story | Success Criteria | Org Subtype |
|----------|-----------|------------------|-------------|
| 1. Detroit PD | US1 | SC-001 | StateApparatus |
| 2. Ford Motor | US1 | SC-001 | Business |
| 3. Revolutionary Workers Party | US1 | SC-001 | PoliticalFaction |
| 4. Mainstream Church | US1 | SC-001 | CivilSocietyOrg |
| 5. Class Composition | US2 | SC-002 | (any) |
| 6. Lifecycle Composition | US2 | SC-002 | (any) |
| 7. Consciousness Effect | US3 | SC-003 | PoliticalFaction |
| 8. Key Figure ID | US5 | SC-005 | CivilSocietyOrg |
| 9. Graph Round-Trip | US1 | SC-001, SC-007 | All four |
