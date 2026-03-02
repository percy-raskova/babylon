# Institution Module Contract

**Module**: `src/babylon/models/entities/institution.py`

## Public API

### Models (frozen Pydantic)

```python
class Institution(BaseModel):
    """Third-layer entity: agent-generating substrate."""
    model_config = ConfigDict(frozen=True)
    # See data-model.md for full field specification

class InternalBalanceOfForces(BaseModel):
    """Factional weight distribution across three ruling-class fractions."""
    model_config = ConfigDict(frozen=True)
    # Validator: weights sum to 1.0 (±0.01)
    # Computed: hegemonic_fraction -> RulingClassFraction

class ReproductionMechanism(BaseModel):
    """Self-perpetuation capacity of an institution."""
    model_config = ConfigDict(frozen=True)
    # Computed: reproduction_capacity -> float

class InstitutionOrgRelation(BaseModel):
    """Relationship between institution and housed Organization."""
    model_config = ConfigDict(frozen=True)

class SpawningBlueprint(BaseModel):
    """Template for replacement Organization creation."""
    model_config = ConfigDict(frozen=True)
```

### Pure Functions

```python
def update_internal_balance(
    balance: InternalBalanceOfForces,
    crisis_intensity: float,
    legitimacy: float,
    external_threat: float,
    alpha: float = 0.05,
) -> tuple[InternalBalanceOfForces, list[Event]]:
    """Update factional balance given material conditions.

    Returns new balance and any triggered events (faction shift, Bonapartist mode).
    Does NOT mutate input. Does NOT interact with EventBus.
    """

def structural_selectivity(
    institution: Institution,
    action_type: ActionType,
    defaults: dict[str, dict[str, float]],
) -> float:
    """Compute action cost modifier for an Organization housed in this institution.

    Returns float multiplier: < 1.0 = cheaper, > 1.0 = more expensive, 1.0 = no effect.
    Checks institution.action_modifiers first, falls back to apparatus-type defaults.
    """

def hegemonic_fraction_effect(
    fraction: RulingClassFraction,
) -> dict[str, Any]:
    """Compute OODA modifier hints based on hegemonic fraction.

    Returns dict with keys like 'preferred_actions', 'escalation_reluctance'.
    Does NOT modify OODAProfile directly — caller interprets hints.
    """

def community_embeddedness(
    institution: Institution,
    graph: GraphProtocol,
) -> dict[str, float]:
    """Compute institution's embeddedness in community hyperedges.

    Returns dict mapping CommunityType string -> embeddedness score [0, 1].
    """
```

### Enums (in `src/babylon/models/enums.py`)

```python
class ApparatusType(StrEnum): ...     # 15 values (5 RSA, 7 ISA, 3 Economic)
class SocialFunction(StrEnum): ...    # 12 values
class ClassInscription(StrEnum): ...  # 3 values (BOURGEOIS, PROLETARIAN, CONTESTED)
class RulingClassFraction(StrEnum): ...  # 3 values
class LifecyclePhase(StrEnum): ...    # 3 values (D, P, D')
```

### EventTypes (appended to existing `EventType` enum)

```python
INSTITUTION_FACTION_SHIFT = "institution_faction_shift"
INSTITUTION_REPRODUCTION = "institution_reproduction"
INSTITUTION_BONAPARTIST_MODE = "institution_bonapartist_mode"
```

## Invariants

1. `InternalBalanceOfForces` weights always sum to 1.0 (±0.01)
2. `action_modifiers` values are always > 0.0
3. `Institution` is frozen — all mutations return new instances via `model_copy()`
4. `update_internal_balance` is pure — no side effects, no EventBus dependency
5. `reproduction_capacity` is always in [0.0, 1.0]
6. Destroying all housed Organizations degrades but does not destroy the Institution

## Integration Points

| System | Integration | Direction |
|--------|-------------|-----------|
| WorldState | `institutions` dict field, to_graph/from_graph | Bidirectional |
| GraphProtocol | `_node_type="institution"` nodes | Storage |
| OODA System | `hegemonic_fraction_effect()` hints | Read-only |
| CommunitySystem | `community_embeddedness()` queries | Read-only |
| GameDefines | `InstitutionDefines` section in defines.yaml | Config |
