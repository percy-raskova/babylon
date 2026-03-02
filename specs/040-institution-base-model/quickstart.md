# Quickstart: Institution Base Model

## Creating an Institution

```python
from babylon.models.entities.institution import (
    Institution,
    InternalBalanceOfForces,
    ReproductionMechanism,
    InstitutionOrgRelation,
    SpawningBlueprint,
)
from babylon.models.enums import (
    ApparatusType,
    SocialFunction,
    ClassInscription,
    RulingClassFraction,
    LifecyclePhase,
    OrgType,
    ClassCharacter,
)

# DOJ as RSA_JUDICIAL institution
doj = Institution(
    id="doj",
    name="Department of Justice",
    apparatus_type=ApparatusType.RSA_JUDICIAL,
    social_function=SocialFunction.ADJUDICATION,
    class_inscription=ClassInscription.BOURGEOIS,
    internal_balance=InternalBalanceOfForces(
        liberal_technocratic=0.5,
        revanchist_fascist=0.3,
        institutionalist_bonapartist=0.2,
        internal_contestation=0.3,
    ),
    budget=1_000_000.0,
    legal_authorities=frozenset(["federal_prosecution", "civil_rights_enforcement"]),
    personnel_capacity=500,
    formalization_level=0.95,
    institutional_inertia=0.8,
    legitimacy=0.7,
    housed_org_ids=["fbi"],
    territory_ids=["us_national"],
    jurisdiction=frozenset(["national"]),
    reproduction=ReproductionMechanism(
        recruitment_pipeline=True,
        training_program=True,
        succession_protocol=True,
        budget_independence=0.8,
        legal_self_perpetuation=True,
    ),
    spawning_blueprints=[
        SpawningBlueprint(
            org_type=OrgType.STATE_APPARATUS,
            default_class_character=ClassCharacter.BOURGEOIS,
            base_attributes={"jurisdiction": "national", "violence_capacity": 0.3},
        ),
    ],
)

# Detroit Public Schools as ISA_EDUCATIONAL
dps = Institution(
    id="detroit_public_schools",
    name="Detroit Public Schools",
    apparatus_type=ApparatusType.ISA_EDUCATIONAL,
    social_function=SocialFunction.EDUCATION,
    class_inscription=ClassInscription.CONTESTED,
    internal_balance=InternalBalanceOfForces(
        liberal_technocratic=0.6,
        revanchist_fascist=0.2,
        institutionalist_bonapartist=0.2,
    ),
    budget=500_000.0,
    personnel_capacity=3000,
    legitimacy=0.5,
    territory_ids=["detroit_h3_001", "detroit_h3_002"],
    lifecycle_function=LifecyclePhase.D_DEPENDENT,
    reproduction=ReproductionMechanism(
        recruitment_pipeline=True,
        training_program=True,
        succession_protocol=True,
        budget_independence=0.3,
        legal_self_perpetuation=True,
    ),
)
```

## Querying Internal Balance

```python
# Check hegemonic fraction
assert doj.internal_balance.hegemonic_fraction == RulingClassFraction.LIBERAL_TECHNOCRATIC

# Check reproduction capacity
assert doj.reproduction.reproduction_capacity > 0.8
```

## Updating Balance (Pure Function)

```python
from babylon.models.entities.institution import update_internal_balance

new_balance, events = update_internal_balance(
    balance=doj.internal_balance,
    crisis_intensity=0.8,
    legitimacy=0.3,
    external_threat=0.5,
)

# Balance shifted toward revanchist under crisis
assert new_balance.revanchist_fascist > doj.internal_balance.revanchist_fascist

# Check if hegemonic fraction changed
for event in events:
    print(f"Event: {event.type} - {event.payload}")
```

## Structural Selectivity

```python
from babylon.models.entities.institution import structural_selectivity
from babylon.models.enums import ActionType

# University makes EDUCATE cheap, REPRESS expensive
educate_cost = structural_selectivity(dps, ActionType.EDUCATE, defaults)
repress_cost = structural_selectivity(dps, ActionType.REPRESS, defaults)

assert educate_cost < 1.0  # Cheaper
assert repress_cost > 1.0  # More expensive
```

## Graph Integration

```python
from babylon.models.world_state import WorldState

state = WorldState(
    institutions={"doj": doj, "detroit_public_schools": dps},
    # ... other fields
)

G = state.to_graph()
# Institutions are now graph nodes with _node_type="institution"

# Query all institutions
from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter
adapter = NetworkXAdapter.wrap(G)
institutions = list(adapter.query_nodes(node_type="institution"))
assert len(institutions) == 2
```
