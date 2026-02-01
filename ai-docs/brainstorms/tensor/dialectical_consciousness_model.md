# Dialectical Consciousness Model

## From Magic Numbers to Material Derivation

**Status**: Design Document
**Supersedes**: Ad-hoc consciousness parameters in `defines.py`
**Principle**: Every quantity must trace to the primitive tensor or graph topology

---

## 1. The Problem

The current `defines.py` contains dozens of "magic numbers" governing consciousness dynamics:

```yaml
consciousness:
  sensitivity: 0.5
  decay_lambda: 0.1
solidarity:
  activation_threshold: 0.3
  mass_awakening_threshold: 0.6
```

These parameters have two fatal flaws:

1. **No derivation** — Where does 0.5 come from? Why not 0.4?
2. **Category error** — Consciousness is represented as a float (`consciousness: Probability`), violating the dialectical principle that qualities are discrete, not continuous.

When we write `consciousness = 0.73`, we claim someone is "73% class conscious." This is incoherent. You either understand your class position or you don't. You either see the system as natural or as constructed. These are qualitative states, not positions on a gradient.

---

## 2. The Dialectical Principle

From the project's constitutional principles:

> **Quantities accumulate; qualities transform discretely.**
>
> An edge is SOLIDARISTIC or it is not. A class position is Proletarian or it is not. Representing qualities as floats on a spectrum is a category error. Use enums for qualities, floats for quantities.

This prevents two errors:

- **Economism** — treating qualitative relationships as automatically determined by quantitative conditions (solidarity as `f(wage_gap)` without organizing)
- **Voluntarism** — treating qualitative transformations as possible without quantitative preconditions (solidarity without material basis)

Material conditions constrain; they do not determine. Quantities accumulate until conditions permit qualitative transformation. Neither alone suffices.

---

## 3. What Actually Produces Consciousness Transformation

Consciousness doesn't change because someone explained class to you. It changes when lived experience contradicts hegemonic narrative so severely that the narrative fails to make sense of your life.

The 4×3 value tensor **directly captures** this contradiction.

### 3.1 The Exploitation Ratio

```
contradiction_intensity = V_produced / V_reproduction
```

When this ratio ≈ 1.0, the system "works" — you work, you survive, the narrative holds.

When it diverges significantly (you work full time and can't make rent), the narrative fails. That failure is the crack through which consciousness transforms.

### 3.2 The Visibility Gap (Department III)

The tensor's g₃₃ visibility metric captures another contradiction:

```
shadow_labor = Dept_III.total_value × (1 - g₃₃)
```

If you perform 40 hours of reproductive labor that doesn't register as "work," that's a contradiction between your exhaustion and the ideology that only waged labor counts.

### 3.3 Imperial Rent as Geographic Contradiction

For peripheral workers, Φ itself is the contradiction:

```
Φ = V_core - V_periphery
```

Experienced as: "Why does my labor buy less than equivalent labor elsewhere?" This is felt through PPP differentials, resource extraction, the inexplicable cheapness of peripheral life.

---

## 4. The Accumulation Model

### 4.1 What Accumulates

Not "organizing hours" or "education exposure." The tensor values themselves, integrated over time:

```python
class MaterialContradiction(BaseModel):
    """Quantities that accumulate toward qualitative transformation."""

    cumulative_extraction: Currency = Field(default=0.0)
    """Integral of surplus value taken over time."""

    cumulative_invisibility: float = Field(default=0.0)
    """Integral of unrecognized reproductive labor."""

    cumulative_immiseration: Currency = Field(default=0.0)
    """Integral of reproduction shortfall (when V_repro > wages)."""

    def accumulate(
        self,
        tensor: ValueTensor4x3,
        reproduction_cost: Currency,
        dt: float,
    ) -> None:
        """Each tick, material conditions either reinforce or erode hegemony."""

        # Extraction experienced
        self.cumulative_extraction += tensor.total_s * dt

        # Shadow labor performed but unrecognized
        shadow = tensor.dept_III.total_value * (1 - tensor.visibility_g33)
        self.cumulative_invisibility += shadow * dt

        # Reproduction gap
        gap = reproduction_cost - tensor.total_v
        if gap > 0:
            self.cumulative_immiseration += gap * dt
```

### 4.2 What Transforms Discretely

Consciousness is an enumerated state, not a float:

```python
class ConsciousnessState(StrEnum):
    """Qualitative states — discrete, not continuous."""

    HEGEMONIC = "hegemonic"
    """System appears natural/inevitable."""

    CONTRADICTED = "contradicted"
    """Noticed gaps between ideology and experience."""

    CRITICAL = "critical"
    """Actively questioning legitimacy."""

    CLASS_CONSCIOUS = "class_conscious"
    """Understands structural position and collective interest."""

    REVOLUTIONARY = "revolutionary"
    """Committed to systemic transformation."""

    # The bifurcation outcome when solidarity is absent
    NATIONAL_CHAUVINIST = "national_chauvinist"
    """Crisis interpreted through national/racial lens."""
```

---

## 5. The Role of Organizing (Corrected)

Initial (wrong) framing: "Organizing exposure" as a float measuring hours of political education.

This is idealist nonsense — measuring superstructure as if it causes itself.

### 5.1 Organizing as Department III Labor

Organizing **is** reproductive labor. Its product is not a commodity but a social relation — the solidarity edge.

```python
def organizing_as_reproduction(
    labor_hours: float,
    source_node: str,
    target_node: str,
    graph: nx.DiGraph,
) -> None:
    """Organizing IS reproductive labor producing social relations.

    Department III labor performed outside capital's circuit.
    Its product is topology change, not commodities.
    """
    if graph.has_edge(source_node, target_node):
        edge = graph.edges[source_node, target_node]
        if edge["edge_type"] == EdgeType.SOLIDARITY:
            edge["resilience"] += labor_hours * SOLIDARITY_LABOR_COEFFICIENT
    else:
        graph.add_edge(
            source_node,
            target_node,
            edge_type=EdgeType.SOLIDARITY,
            resilience=labor_hours * SOLIDARITY_LABOR_COEFFICIENT,
        )
```

### 5.2 The Graph IS the Accumulated Organizing

The solidarity topology **is** the materialized accumulation of organizing work. No separate counter needed. Edge weights and network structure encode the history of relationship-building labor.

---

## 6. The Transformation Function

Consciousness transformation requires the **unity of opposites**:

1. **Tensor** → Contradiction intensity (objective material position)
2. **Graph** → Solidarity topology (objective social relations)
3. **Threshold** → When contradiction exceeds hegemonic capacity AND solidarity edges exist to route the rupture

```python
def check_consciousness_rupture(
    contradiction: MaterialContradiction,
    solidarity_graph: nx.Graph,
    node_id: str,
    current_state: ConsciousnessState,
    thresholds: RuptureThresholds,
) -> ConsciousnessState | None:
    """Qualitative transformation at the unity of opposites.

    Neither contradiction alone (economism) nor solidarity alone (voluntarism)
    produces transformation. Both must coincide.
    """
    # Is contradiction severe enough to crack hegemony?
    hegemony_stress = (
        contradiction.cumulative_extraction +
        contradiction.cumulative_immiseration
    )

    if hegemony_stress < thresholds.rupture:
        return None  # Hegemony holds

    # Contradiction exists — but where does it route?
    # This is George Jackson's question.

    solidarity_degree = solidarity_graph.degree(node_id)

    if solidarity_degree == 0:
        # Atomized — contradiction routes to national identity
        return ConsciousnessState.NATIONAL_CHAUVINIST

    # Solidarity exists — can contradiction become class consciousness?
    # Only if enough of your network shares the contradiction.

    neighbors = list(solidarity_graph.neighbors(node_id))
    shared_contradiction = sum(
        1 for n in neighbors
        if get_contradiction(n).cumulative_immiseration > thresholds.shared
    ) / max(1, len(neighbors))

    if shared_contradiction > thresholds.collective:
        # Contradiction recognized as SHARED, not individual
        # Transformation from "my problem" to "our condition"
        return ConsciousnessState.CLASS_CONSCIOUS

    return None  # Conditions not yet sufficient
```

---

## 7. The George Jackson Bifurcation (Reformulated)

The current model has `national_identity: float` and `class_consciousness: float` as independent dimensions that receive "routed agitation."

The corrected model:

```python
class IdeologicalState(StrEnum):
    """Discrete routing outcome — where does crisis-energy go?"""

    QUIESCENT = "quiescent"
    """No active ideological mobilization."""

    CLASS_ORIENTED = "class_oriented"
    """Crisis interpreted through class lens."""

    NATION_ORIENTED = "nation_oriented"
    """Crisis interpreted through national/racial lens."""
```

The bifurcation is **discrete**, not a continuous routing between two floats:

```python
def jackson_bifurcation(
    agitation: float,
    solidarity_topology: nx.Graph,
    node_id: str,
    threshold: float,
) -> IdeologicalState:
    """The discrete routing decision at moment of crisis.

    Germany 1933: Crisis + atomized workers → Fascism
    Russia 1917: Crisis + organized workers → Revolution
    """
    if agitation < threshold:
        return IdeologicalState.QUIESCENT

    # The bifurcation — discrete, not gradual
    if solidarity_topology.degree(node_id) >= JACKSON_THRESHOLD:
        return IdeologicalState.CLASS_ORIENTED
    else:
        return IdeologicalState.NATION_ORIENTED
```

---

## 8. Constants Taxonomy

### 8.1 Eliminated (Derived from Tensor/Graph)

| Former Constant | Replaced By |
|-----------------|-------------|
| `consciousness_sensitivity` | Tensor integration over time |
| `consciousness_decay_lambda` | Reproduction success resets immiseration accumulator |
| `activation_threshold` | Hegemony stress computed from tensor integrals |
| `organizing_exposure` | Solidarity edge count/weight (already in graph) |
| `solidarity_scaling` | Edge resilience (already in graph) |
| `superwage_impact` | Computed from tensor: `Φ = W_core - V_core` |

### 8.2 Retained (Genuinely Require Calibration)

| Constant | Meaning | Calibration Source |
|----------|---------|-------------------|
| `RUPTURE_THRESHOLD` | How much accumulated contradiction before hegemony fails | Historical: exploitation integral at revolutionary moments vs stable periods |
| `SHARED_THRESHOLD` | What fraction of network must share contradiction for collective recognition | Network studies of movement emergence |
| `COLLECTIVE_THRESHOLD` | Proportion for transformation from individual to collective consciousness | Same as above |
| `SOLIDARITY_LABOR_COEFFICIENT` | How much Dept III labor-time strengthens an edge | Empirical: organizing hour → relationship durability |
| `JACKSON_THRESHOLD` | Minimum solidarity degree for class-oriented routing | Historical: network density in successful vs failed movements |

### 8.3 Primitives (Irreducible)

| Constant | Nature |
|----------|--------|
| `loss_aversion_lambda` (2.25) | External empirical finding (Kahneman-Tversky) |
| `decimal_places`, `epsilon` | Engineering/precision choices |
| `tick_duration_days` | Modeling resolution choice |

---

## 9. Implementation Path

### Phase 1: Add Discrete States

```python
# New enums
class ConsciousnessState(StrEnum): ...
class IdeologicalState(StrEnum): ...

# New accumulation model
class MaterialContradiction(BaseModel): ...
```

### Phase 2: Refactor Entity Model

```python
class Entity(BaseModel):
    # OLD
    consciousness: Probability  # DELETE
    national_identity: Probability  # DELETE

    # NEW
    contradiction: MaterialContradiction
    consciousness_state: ConsciousnessState
    ideological_state: IdeologicalState
```

### Phase 3: Update Tick Logic

Replace continuous drift formulas with:

1. Accumulate tensor values into `MaterialContradiction`
2. Check transformation thresholds
3. Apply discrete state transitions when thresholds crossed

### Phase 4: Clean Up defines.py

Remove all consciousness "modifier" parameters. Retain only the threshold values that govern discrete transformations.

---

## 10. Theoretical Summary

| Aspect | Old Model (Wrong) | New Model (Correct) |
|--------|-------------------|---------------------|
| Consciousness | Float ∈ [0,1] | Enum with discrete states |
| Change mechanism | Continuous drift via sensitivity parameter | Discrete transformation at threshold crossing |
| Organizing | "Exposure hours" counter | Dept III labor producing topology |
| Accumulated quantity | Abstract "consciousness level" | Tensor integrals (extraction, invisibility, immiseration) |
| Bifurcation | Continuous routing between two floats | Discrete state based on solidarity topology at crisis moment |
| Parameters | Behavioral psychology imports | Thresholds calibrated from historical tensor data |

**The dialectical law holds**: Quantitative changes (tensor accumulation) produce qualitative transformation (state transition) at threshold crossing. The transformation is discrete, not continuous. Material conditions (tensor) and social relations (graph) must both be present — neither economism nor voluntarism alone suffices.
