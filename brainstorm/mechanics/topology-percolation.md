# Topology & Percolation Theory in Babylon

**Status:** Implemented
**Phase:** 3.1
**Created:** 2025-12-11
**Core Insight:** Revolutionary organization forms via percolation phase transitions on solidarity graphs

---

## The Problem

How do we model the emergence of revolutionary organization from atomized individuals?

Traditional approaches treat class consciousness as an aggregate property—a percentage bar that fills up. But this misses the *structural* nature of organization. A movement isn't just individuals with high consciousness; it's individuals *connected* to each other through organizational infrastructure.

**The key insight**: Revolution requires not just radicalized workers, but radicalized workers who can *coordinate*. The graph structure matters as much as the node properties.

---

## The Graph Structure

### The Embedded Trinity

Babylon uses a typed multigraph `G = (V, E)` with two node layers:

**Layer 1: Social Classes** (`_node_type="social_class"`)
- Proletariat, bourgeoisie, labor aristocracy, etc.
- Carry state vectors: wealth, consciousness, ideology, organization

**Layer 2: Territories** (`_node_type="territory"`)
- Spatial substrate for TENANCY and ADJACENCY relationships
- Not used in percolation analysis (filtered out)

### Edge Types

Nine edge types model different relationships:

| Edge Type | Direction | Semantics |
|-----------|-----------|-----------|
| SOLIDARITY | Periphery → Core | Consciousness transmission infrastructure |
| EXPLOITATION | Worker → Owner | Imperial rent extraction |
| WAGES | Bourgeoisie → Worker | Super-wage payments |
| REPRESSION | State → Class | Violence accumulation |
| TRIBUTE | Comprador → Core | Value flow via intermediary |
| CLIENT_STATE | Core → Periphery | Imperial subsidy for stability |
| COMPETITION | Class ↔ Class | Market rivalry |
| TENANCY | Class → Territory | Occupancy |
| ADJACENCY | Territory ↔ Territory | Spatial proximity |

### The Solidarity Skeleton

For percolation analysis, we extract the **solidarity subgraph**:

```
G_σ = (V_class, E_solidarity)
```

Where:
- Only `social_class` nodes (territories filtered out)
- Only `SOLIDARITY` edges above strength threshold
- Treated as **undirected** (solidarity is reciprocal infrastructure)

---

## Percolation Theory

### Why Percolation?

Percolation theory studies how connectivity emerges in random graphs. The classic result: in Erdős–Rényi graphs `G(n,p)`, there's a sharp phase transition at `p_c = 1/n` where a "giant component" suddenly spans the network.

We apply this to revolutionary organization:
- **Below threshold**: Many isolated cells, easily purged
- **Above threshold**: Giant component forms, movement becomes resilient

### The Percolation Ratio

$$p = \frac{L_{\max}}{N}$$

Where:
- $L_{\max}$ = size of largest connected component
- $N$ = total number of social class nodes

### Phase States

| State | Condition | Physical Meaning |
|-------|-----------|------------------|
| **Gaseous** | $p < 0.1$ | Atomized. Many isolated cells. Vulnerable to purge. |
| **Condensing** | $0.1 \leq p < 0.5$ | Coalescing. Cells beginning to link. |
| **Liquid** | $p \geq 0.5$ | Condensed. Giant component dominates. Vanguard formed. |

The crossing of $p = 0.5$ is the **condensation phase transition**—the moment organizational infrastructure achieves critical mass.

### Liquidity Metrics

Not all solidarity edges are equal. We distinguish:

- **Potential Liquidity**: Edges with `solidarity_strength > 0.1` (sympathizers)
- **Actual Liquidity**: Edges with `solidarity_strength > 0.5` (committed cadre)

When `potential >> actual × 2`, the movement is **brittle**: broad but lacking disciplined core.

---

## Resilience Testing (Sword of Damocles)

### The Test

Can the organization survive targeted repression?

```
1. Extract solidarity subgraph G_σ
2. Record original L_max
3. Remove 20% of nodes (simulating purge)
4. Calculate post-purge L_max
5. Resilient if: post_L_max ≥ 0.4 × original_L_max
```

### Network Topologies

**Star Topology** (Fragile):
- Single hub connects all nodes
- Hub removal destroys giant component
- `is_resilient = False`

**Mesh Topology** (Resilient):
- Multiple redundant paths
- No single point of failure
- `is_resilient = True`

The "Sword of Damocles" alert triggers when `is_resilient = False`—the network can be destroyed by targeting key members.

---

## The Fascist Bifurcation

### The Core Insight

> "Agitation without solidarity produces fascism, not revolution."

This encodes the historical comparison:
- **Russia 1917**: Solidarity infrastructure existed → Revolution
- **Germany 1933**: Atomized working class → Fascism

### The Bifurcation Formula

When wages fall ($\dot{W} < 0$), crisis creates "agitation energy":

$$E = \kappa |\dot{W}|$$

Where $\kappa = 2.25$ (Kahneman-Tversky loss aversion).

This energy must route somewhere:

```
                    σ > 0 (solidarity present)
                         ↗
    Wage Crisis  →  Bifurcation Point
                         ↘
                    σ = 0 (no solidarity)
```

**With solidarity** ($\sigma > 0$):
- Energy channels to class consciousness
- Workers blame capital
- Revolutionary drift: $\Delta\Psi = +E \cdot \sigma$

**Without solidarity** ($\sigma = 0$):
- Energy channels to national identity
- Workers blame foreigners/immigrants
- Fascist drift: $\Delta\nu = +E$

### Catastrophe Theory Connection

This is a **cusp catastrophe** in Thom's classification:
- Control parameters: $(\dot{W}, \sigma)$
- State variable: $\Psi$ (consciousness)
- Two stable equilibria separated by bifurcation surface

---

## Consciousness Dynamics

### The ODE System

Each social class evolves according to:

$$\frac{d\Psi_i}{dt} = k\left(1 - \frac{W_i}{V_i}\right) - \lambda \Psi_i + \sum_{j \to i} \sigma_{ji}(\Psi_j - \Psi_i) + B_i$$

Where:
- $W_i/V_i$: wage-to-value ratio (material conditions)
- $\lambda$: decay coefficient (consciousness fades without basis)
- $\sigma_{ji}$: solidarity strength on edge $j \to i$
- $B_i$: bifurcation term (see above)

### Solidarity Transmission

The transmission term is a **discrete Laplacian diffusion**:

$$\Delta_\sigma \Psi = \sum_{j \sim i} \sigma_{ij}(\Psi_j - \Psi_i)$$

Key constraint: transmission only occurs when:
1. Source consciousness > activation threshold (0.3)
2. Solidarity strength > 0

This enables the Fascist Bifurcation: periphery can revolt, but without solidarity infrastructure, core workers stay passive.

---

## Implementation Notes

### Key Files

| File | Purpose |
|------|---------|
| `src/babylon/engine/topology_monitor.py` | TopologyMonitor observer, percolation functions |
| `src/babylon/systems/formulas.py` | Consciousness drift, bifurcation formulas |
| `src/babylon/models/topology_metrics.py` | TopologySnapshot, ResilienceResult models |
| `src/babylon/engine/systems/solidarity.py` | SolidaritySystem transmission logic |

### Constants

```python
# topology_monitor.py
GASEOUS_THRESHOLD = 0.1
CONDENSATION_THRESHOLD = 0.5
BRITTLE_MULTIPLIER = 2
POTENTIAL_MIN_STRENGTH = 0.1
ACTUAL_MIN_STRENGTH = 0.5
DEFAULT_REMOVAL_RATE = 0.2
DEFAULT_SURVIVAL_THRESHOLD = 0.4

# formulas.py
LOSS_AVERSION_COEFFICIENT = 2.25
```

### Test Coverage

- 34 unit tests in `tests/unit/topology/test_topology_monitor.py`
- 21 integration tests in `tests/integration/test_topology_integration.py`

---

## Historical-Materialist Interpretation

The topology system encodes a key MLM-TW insight: **the organizational question is primary**.

A working class with high consciousness but no organizational infrastructure is not a revolutionary force—it's kindling for fascism. The solidarity graph is not just bookkeeping; it's the material substrate that determines which equilibrium the system reaches.

> "The vanguard party is not born; it is built."

Building solidarity edges through shared struggle is the strategic imperative. Without them, crisis energy routes to reaction.
