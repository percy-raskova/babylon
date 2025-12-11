# Sprint 3.7: The Carceral Geography

## The Necropolitical Triad

The eviction pipeline in Layer 0 was incomplete. Displaced populations simply
"disappeared"—deleted from the simulation. But disappearance is not neutral.
The settler-colonial state has specific DESTINATIONS for surplus populations.

This sprint transforms the TerritorySystem into a **Settler-Colonial
Displacement Engine** by implementing the Necropolitical Triad: the three
fates awaiting those expelled from productive society.

## Theoretical Foundation

### Achille Mbembe's Necropolitics
> "The ultimate expression of sovereignty resides, to a large degree, in the
> power and the capacity to dictate who may live and who must die."

The state exercises "the right to kill" not just through execution but through
**differential allocation of death**:
- Some populations are marked for slow death (poverty, disease, neglect)
- Some for social death (incarceration, civic exclusion)
- Some for physical death (genocide, police violence, medical neglect)

### The Prison-Industrial Complex
Mass incarceration is not crime control—it's **population management**:
- Warehouse surplus labor (deindustrialization created "excess" workers)
- Extract value from prisoners (13th Amendment: "except as punishment")
- Break solidarity (atomize communities, destroy organizations)
- Generate terror (the threat keeps the "free" compliant)

### The Reservation System
Indigenous reservations are not "homelands"—they're **containment zones**:
- Confine populations to economically unproductive land
- Maintain legal fiction of "sovereignty" while extracting resources
- Slow genocide through neglect (no healthcare, no jobs, no infrastructure)
- Buffer zones between settler territory and Indigenous land

## The Three Territory Types (Sink Nodes)

### 1. RESERVATION (Containment)
- **Function:** Warehouse populations without labor value extraction
- **Mechanic:** High subsistence cost, population growth impossible
- **Historical Parallel:** Indian reservations, public housing projects
- **Game Effect:** Population remains alive but contributes nothing

### 2. PENAL_COLONY (Extraction)
- **Function:** Extract forced labor while breaking organization
- **Mechanic:** Generates value, suppresses Organization to zero
- **Historical Parallel:** Prison labor, ICE detention, workfare
- **Game Effect:** Population works but cannot organize

### 3. CONCENTRATION_CAMP (Elimination)
- **Function:** Eliminate populations through accelerated death
- **Mechanic:** Population decays 20% per tick
- **Historical Parallel:** Death camps, immigrant detention, medical neglect
- **Game Effect:** Population actively destroyed

## The Displacement Pipeline

When eviction occurs in a territory under HIGH_PROFILE heat:

```
Territory (heat >= 0.8)
    |
    | eviction triggered
    v
_find_sink_node()
    |
    | Priority routing:
    | 1. CONCENTRATION_CAMP (highest)
    | 2. PENAL_COLONY
    | 3. RESERVATION (lowest)
    v
Transfer population to sink
    |
    v
_process_necropolitics()
    |
    | For camps: population *= 0.8 (elimination)
    | For penal: organization = 0.0 (atomization)
    | For reservations: (containment, no effect)
    v
End of tick
```

## Dynamic Priority Modes (Sprint 3.7.1)

The priority order isn't static—it **emerges from material conditions**. The
state's routing logic evolves based on economic crisis and political tension:

### The Three Modes

| Mode | Priority Order | When | Historical Parallel |
|------|----------------|------|---------------------|
| **EXTRACTION** | Prison > Reservation > Camp | Labor is valuable | Mass incarceration, gulag |
| **CONTAINMENT** | Reservation > Prison > Camp | Crisis/transition | Ghettoization, internment |
| **ELIMINATION** | Camp > Prison > Reservation | Late fascism | Holocaust, Khmer Rouge |

### Mode Selection Logic

**EXTRACTION (Default):** "We need their labor."
- The prison-industrial complex logic
- Forced labor is profitable; elimination is wasteful
- Historical: American mass incarceration, Soviet gulag system

**CONTAINMENT:** "We need them out of the way but not dead yet."
- Activated when EITHER economic OR political crisis emerges
- Warehousing is cheaper than extraction during uncertainty
- Historical: Japanese internment, ghettoization before Holocaust

**ELIMINATION:** "We don't need them at all."
- Activated when BOTH economic collapse AND political crisis converge
- Neither condition alone triggers elimination logic
- Historical: Nazi death camps emerged only when war + ideology converged

### Threshold-Based Mode Switching (AUTO mode)

When `displacement_priority_mode: auto`, mode is computed dynamically:

```
rent_ratio = current_rent_pool / initial_rent_pool
avg_tension = mean(tensions across EXPLOITATION edges)

ELIMINATION requires: (rent_ratio < 0.1 AND avg_tension > 0.8)  # BOTH
CONTAINMENT requires: (rent_ratio < 0.3 OR avg_tension > 0.5)   # EITHER
EXTRACTION is: default when neither crisis active
```

### Why AND for Elimination, OR for Containment?

**ELIMINATION (AND logic):**
- Requires BOTH economic collapse AND political crisis
- Neither alone triggers elimination:
  - Economic crisis alone → reform, adjustment, NOT genocide
  - Political fascism alone → profitable extraction continues
- The state needs ideological justification AND material desperation

**CONTAINMENT (OR logic):**
- Either condition triggers intermediate measures
- Economic stress → concentrate populations (cheaper than extraction)
- Political tension → prepare for potential escalation
- Historical: Ghettoization preceded both reform AND elimination

### Configuration

```python
# Mode selection
displacement_priority_mode: DisplacementPriorityMode = EXTRACTION  # Default

# Thresholds for AUTO mode
elimination_rent_threshold: Coefficient = 0.1    # 10% of initial rent
elimination_tension_threshold: Coefficient = 0.8  # Near-rupture
containment_rent_threshold: Coefficient = 0.3    # 30% of initial rent
containment_tension_threshold: Coefficient = 0.5  # Moderate crisis
```

### Why EXTRACTION is Default

The current hardcoded ELIMINATION priority assumed late-stage fascism, but
**most gameplay occurs before that**. EXTRACTION as default reflects:

1. The normal operation of the carceral state (mass incarceration for profit)
2. Allows escalation through gameplay (EXTRACTION → CONTAINMENT → ELIMINATION)
3. More historically accurate for most of American history

## Legacy: Static Priority Logic

The original Sprint 3.7 implementation used static priority (ELIMINATION mode).
Sprint 3.7.1 makes this dynamic. If you want the original behavior:

```python
displacement_priority_mode: elimination  # Force ELIMINATION mode
```

4. **No sink (fallback):** Populations "disappear"—homelessness, exile, death
   outside the system's accounting.

## Implementation Details

### TerritoryType Enum
```python
class TerritoryType(StrEnum):
    CORE = "core"                    # Labor aristocracy destination
    PERIPHERY = "periphery"          # Source of cheap labor
    RESERVATION = "reservation"      # Containment
    PENAL_COLONY = "penal_colony"    # Forced labor
    CONCENTRATION_CAMP = "concentration_camp"  # Elimination
```

### is_sink_node Property
```python
@property
def is_sink_node(self) -> bool:
    return self.territory_type in {
        TerritoryType.RESERVATION,
        TerritoryType.PENAL_COLONY,
        TerritoryType.CONCENTRATION_CAMP,
    }
```

### Necropolitics Processing
```python
def _process_necropolitics(self, graph, services):
    for node_id, data in graph.nodes(data=True):
        if data.get("_node_type") != "territory":
            continue

        territory_type = data.get("territory_type")

        if territory_type == TerritoryType.CONCENTRATION_CAMP:
            # Elimination: 20% population loss per tick
            current_pop = data.get("population", 0)
            decay_rate = services.config.concentration_camp_decay_rate
            new_pop = int(current_pop * (1.0 - decay_rate))
            graph.nodes[node_id]["population"] = new_pop

        elif territory_type == TerritoryType.PENAL_COLONY:
            # Atomization: break all connected organizations
            self._suppress_organization(node_id, graph)
```

## Gameplay Implications

### For the Player
- **Defensive priority:** Prevent populations from reaching sink nodes
- **Rescue operations:** Can you extract people from camps/prisons?
- **Counter-infrastructure:** Build solidarity edges TO sink nodes
- **Liberation:** Convert sink nodes to PERIPHERY or liberated zones

### For the AI/State
- **Efficient repression:** Route to elimination when possible
- **Profit extraction:** Use penal labor when camps aren't available
- **Containment fallback:** Reservations as last resort

### Strategic Depth
The displacement pipeline creates strategic choices:
- **Block ADJACENCY edges** to prevent routing to camps
- **Liberate sink nodes** to rescue populations
- **Defensive terrain:** Make territories "dead ends" for displacement
- **Offensive terrain:** Create paths OUT of sink nodes

## Relation to Other Systems

### Eviction Pipeline (Layer 0)
The necropolitical triad extends the eviction pipeline. Instead of population
simply decreasing, it now FLOWS through the carceral geography.

### Solidarity System
PENAL_COLONY's organization suppression directly attacks the Solidarity
System's ability to build class consciousness. Breaking the strike.

### Consciousness System
Populations in sink nodes may have altered consciousness dynamics:
- Camps: consciousness becomes irrelevant (survival mode)
- Prisons: consciousness suppressed (atomization)
- Reservations: consciousness preserved but isolated

### Future: Liberation Mechanics
Sprint 3.8+ should implement:
- Converting sink nodes to liberated zones
- Extraction operations (breaking people out)
- Building solidarity infrastructure INTO sink nodes

## Test Coverage

### Sprint 3.7 Tests (14)
- 6 model tests (TerritoryType, is_sink_node)
- 8 system tests (routing, transfer, necropolitics)

### Sprint 3.7.1 Tests (8 new)
- test_extraction_mode_prioritizes_penal_colony
- test_containment_mode_prioritizes_reservation
- test_elimination_mode_prioritizes_concentration_camp
- test_find_sink_node_with_extraction_mode
- test_find_sink_node_with_containment_mode
- test_find_sink_node_with_elimination_mode
- test_find_sink_node_defaults_to_extraction_priority
- test_invalid_mode_falls_back_to_extraction

All tests pass. Total: 440 project tests.

## Commits

- `321a765` feat(engine): add Carceral Geography to TerritorySystem (Sprint 3.7)
- `36f8647` fix(__main__): update unpacking for create_two_node_scenario
- `2d66ff5` docs: add Carceral Geography documentation (Sprint 3.7)
- `a92fca7` feat(engine): add dynamic displacement priority modes (Sprint 3.7.1)
