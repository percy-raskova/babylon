# Babylon Tensor Hierarchy

## From Primitive to Derived: A Rigorous Foundation

**Status**: Design Document
**Principle**: "Tensor" is earned through transformation properties, not awarded for being multi-dimensional

---

## 1. What Earns the Name "Tensor"

A tensor has **transformation properties** — it changes in specific, predictable ways under coordinate changes. An array that happens to have multiple indices is not a tensor; it's just an array.

The question for Babylon: What coordinate systems matter, and what transforms meaningfully under them?

### 1.1 Coordinate Systems That Matter

| Coordinate System | Transformation | Example |
|-------------------|----------------|---------|
| Geographic aggregation | County → State → Nation → World | Summing county values to state totals |
| Temporal resolution | Weekly → Monthly → Annual | Aggregating tick values to year values |
| Currency/value basis | Dollars → Labor-time (via SNLT) | Converting monetary flows to labor-hours |
| Class decomposition | 4-class → 6-class → finer | Splitting Labor Aristocracy into sub-positions |
| Industry aggregation | 6-digit NAICS → 2-digit → Sector | Combining detailed industries to departments |

### 1.2 The Test

For quantity Q to be a tensor:

1. **Specify the index space** — What are the coordinates? (counties, industries, classes, etc.)
2. **Define the transformation rule** — How does Q change under aggregation/disaggregation?
3. **Verify consistency** — Does aggregating then transforming equal transforming then aggregating?

If you can't answer these, you have an array, not a tensor.

---

## 2. Level 0: The Primitive

### ValueTensor4x3

```
T^μ_ν[fips, year] where μ ∈ {I, IIa, IIb, III}, ν ∈ {c, v, s}
```

**Index spaces:**
- Geographic: 5-digit FIPS (3,143 counties)
- Temporal: Year (1975-present for QCEW)
- Department: 4 Marxian departments (production output)
- Value component: 3 categories (c, v, s)

**Transformation properties:**
- Geographic aggregation: Sums correctly (county → state → nation)
- Temporal aggregation: Sums correctly (week → year)
- Currency → labor-time: Scales uniformly via SNLT conversion factor

**Data source:** QCEW wages (v) + BEA ratios (c/v, s/v)

**Already implemented:** `src/babylon/economics/tensor.py`

---

## 3. Level 1: Direct from External Data

These tensors come directly from federal statistical sources with minimal transformation.

### 3.1 Inter-Industry Flow Matrix

```
A^i_j = dollars of industry i output required per $1 of industry j output
```

**Index space:** ~70 BEA industries × ~70 BEA industries

**Transformation properties:**
- Industry aggregation: Transforms via weighted sum (weight = industry output share)
- Currency → labor-time: Each element scales by SNLT

**Data source:** BEA Input-Output Tables (annual, public)

**What it captures:** The technical structure of production — how industries depend on each other. Steel needs coal needs transportation needs steel (cycles in the production graph).

**File format:** BEA releases as flat CSV. ~70 "summary" industries or ~400 "detailed" industries.

```python
class InterIndustryFlow(BaseModel):
    """BEA Input-Output coefficient matrix."""

    year: int
    industries: list[str]  # BEA industry codes
    A: np.ndarray  # Shape: (n_industries, n_industries)

    def aggregate_to_departments(
        self,
        mapping: dict[str, Department],
    ) -> np.ndarray:
        """Aggregate ~70 industries to 4 departments."""
        ...
```

### 3.2 Geographic Flow Tensor

```
F^{ab} = value flowing from county a to county b (annual)
```

**Index space:** 3,143 counties × 3,143 counties (sparse — most pairs have zero flow)

**Transformation properties:**
- Geographic aggregation: Sums correctly
- Decomposes into symmetric (exchange) + antisymmetric (net extraction) parts

**Data sources:**
- BTS Freight Analysis Framework: Physical commodity flows by origin-destination-commodity
- BEA Regional Income: Factor payments (wages, profits, rents) crossing state lines
- Census County Business Patterns: Establishment locations (proxy for where value lands)

**What it captures:** The spatial structure of value transfer. Imperial rent is the **antisymmetric part**:

```python
def imperial_rent_by_county(F: np.ndarray) -> np.ndarray:
    """Net extraction = row sum - column sum.

    Positive = net recipient (core)
    Negative = net donor (periphery)
    """
    inflow = F.sum(axis=0)   # What flows TO each county
    outflow = F.sum(axis=1)  # What flows FROM each county
    return inflow - outflow
```

**Implementation note:** This matrix is huge (3143² ≈ 10M entries) but extremely sparse. Store as `scipy.sparse.csr_matrix`.

### 3.3 Class Transition Matrix

```
P^{c'}_c = P(class = c' at t+1 | class = c at t)
```

**Index space:** n_classes × n_classes (stochastic matrix: rows sum to 1)

**Transformation properties:**
- Composes via matrix multiplication: P(t+2|t) = P × P
- Stationary distribution is dominant eigenvector
- Class aggregation: Block-sum preserves stochasticity

**Data source:** Panel Study of Income Dynamics (PSID)

PSID tracks ~5,000 families since 1968. By linking income/occupation across waves, we can estimate transition probabilities.

**What it captures:** Class reproduction vs mobility. Diagonal dominance = class positions are sticky.

```python
class ClassTransitionMatrix(BaseModel):
    """Empirical class mobility from PSID."""

    period: tuple[int, int]  # (start_year, end_year)
    classes: list[SocialRole]
    P: np.ndarray  # Shape: (n_classes, n_classes), rows sum to 1

    @computed_field
    def stationary_distribution(self) -> np.ndarray:
        """Long-run class distribution if transitions continue."""
        eigenvalues, eigenvectors = np.linalg.eig(self.P.T)
        # Find eigenvector for eigenvalue ≈ 1
        idx = np.argmin(np.abs(eigenvalues - 1.0))
        stationary = np.real(eigenvectors[:, idx])
        return stationary / stationary.sum()

    @computed_field
    def lumpenization_rate(self) -> float:
        """P(LA → Lumpen) per period."""
        la_idx = self.classes.index(SocialRole.LABOR_ARISTOCRACY)
        lumpen_idx = self.classes.index(SocialRole.LUMPEN)
        return self.P[la_idx, lumpen_idx]
```

**Access note:** PSID public-use files are free but require registration. Geocoded versions are restricted.

### 3.4 Visibility Metric

```
g_μν = diag(g₁₁, g₂₂ₐ, g₂₂ᵦ, g₃₃)
```

**Index space:** 4 departments × 4 departments (diagonal)

**Transformation properties:**
- Defines inner product on labor-space: price = g_μν × labor^μ
- When g₃₃ → 0, reproductive labor has zero "length" in price-space

**Data sources:**
- QCEW: Paid employment by industry
- ATUS: Unpaid labor hours by activity category

**What it captures:** How much of each department's labor registers in the monetary economy.

```python
def compute_visibility(
    qcew_hours: dict[Department, float],
    atus_unpaid_hours: dict[Department, float],
) -> np.ndarray:
    """Visibility = paid / (paid + unpaid) for each department.

    Departments I, IIa, IIb are mostly visible (g ≈ 1).
    Department III has substantial shadow labor (g << 1).
    """
    g = np.zeros(4)
    for i, dept in enumerate(Department):
        paid = qcew_hours.get(dept, 0.0)
        unpaid = atus_unpaid_hours.get(dept, 0.0)
        total = paid + unpaid
        g[i] = paid / total if total > 0 else 1.0
    return np.diag(g)
```

**Why this is a metric tensor:**

The "length" of a labor vector in price-space:

```
||L||²_price = L^μ g_μν L^ν = Σ_μ g_μμ (L^μ)²
```

When g₃₃ = 0, reproductive labor contributes zero to price-measured output despite existing in labor-measured output. This is the formal expression of "shadow labor."

### 3.5 Reproduction Requirements Tensor

```
C^{cd}_u = quantity of use-value u from department d required to reproduce class c
L^{cc'}_t = hours of labor type t performed by class c' to reproduce class c
```

**Index spaces:**
- C: classes × departments × use-values
- L: classes × classes × labor-types

**Data sources:**
- Consumer Expenditure Survey (CEX): Spending by category by income quintile
- ATUS: Time use by activity by demographic

**What it captures:** The material requirements for class reproduction. The gap between production (ValueTensor4x3) and reproduction requirements (C, L) is the contradiction that accumulates.

```python
class ReproductionRequirements(BaseModel):
    """What each class needs to reproduce."""

    year: int

    # Consumption requirements: C[class, dept, use_value] = quantity
    consumption: dict[SocialRole, dict[Department, dict[UseValue, float]]]

    # Reproductive labor: L[reproduced_class, laborer_class, labor_type] = hours
    reproductive_labor: dict[SocialRole, dict[SocialRole, dict[LaborType, float]]]

    def total_reproduction_cost(
        self,
        social_class: SocialRole,
        snlt: float,
    ) -> Currency:
        """V_reproduction in labor-time units."""
        # Sum consumption requirements converted via SNLT
        consumption_cost = sum(
            qty * snlt
            for dept in self.consumption[social_class].values()
            for qty in dept.values()
        )
        # Add reproductive labor (already in hours)
        labor_cost = sum(
            hours
            for laborer in self.reproductive_labor[social_class].values()
            for hours in laborer.values()
        )
        return Currency(consumption_cost + labor_cost)
```

---

## 4. Level 2: Derived via Mathematical Transformation

These tensors are computed from Level 1 tensors using well-defined operations.

### 4.1 Leontief Inverse

```
L = (I - A)^{-1}
```

**Derivation:** Matrix inverse of (Identity - InterIndustryFlow)

**What it captures:** Total requirements (direct + indirect) for production. If auto needs steel and steel needs coal and coal needs transportation, the Leontief inverse captures the full chain.

```python
def leontief_inverse(A: np.ndarray) -> np.ndarray:
    """Total requirements matrix.

    L[i,j] = total output of industry i required (directly + indirectly)
             to deliver $1 of industry j to final demand.
    """
    n = A.shape[0]
    return np.linalg.inv(np.eye(n) - A)
```

**Application:** Total labor embodied in a commodity:

```python
def total_labor_coefficients(
    leontief: np.ndarray,
    direct_labor: np.ndarray,  # Labor per $ output by industry
) -> np.ndarray:
    """Total labor (direct + indirect) per $ of final demand."""
    return leontief.T @ direct_labor
```

### 4.2 Imperial Rent Field

```
Φ_a = Σ_b F^{ba} - Σ_b F^{ab}  (net inflow to county a)
```

**Derivation:** Antisymmetric part of GeographicFlow, summed over partner counties.

**What it captures:** Net value extraction by geography. The scalar field Φ over county-space.

```python
def imperial_rent_field(F: sparse.csr_matrix) -> np.ndarray:
    """Imperial rent by county.

    Φ > 0: Net recipient (core behavior)
    Φ < 0: Net donor (periphery behavior)
    Φ ≈ 0: Balanced exchange or autarky
    """
    inflow = np.array(F.sum(axis=0)).flatten()
    outflow = np.array(F.sum(axis=1)).flatten()
    return inflow - outflow
```

**Validation:** Sum over all counties should ≈ 0 (closed system, value conserved).

### 4.3 Stationary Class Distribution

```
π = eigenvector(P) with eigenvalue 1
```

**Derivation:** Dominant eigenvector of ClassTransitionMatrix

**What it captures:** Long-run class composition if current mobility patterns continue indefinitely.

```python
def stationary_distribution(P: np.ndarray) -> np.ndarray:
    """Where the class structure converges."""
    eigenvalues, eigenvectors = np.linalg.eig(P.T)
    idx = np.argmin(np.abs(eigenvalues - 1.0))
    pi = np.real(eigenvectors[:, idx])
    return pi / pi.sum()  # Normalize to probability distribution
```

**Application:** Compare stationary distribution to current distribution. Divergence indicates the system is in transition.

### 4.4 Shadow Subsidy

```
S = T³_total × (1 - g₃₃)
```

**Derivation:** Department III value × invisibility fraction

**What it captures:** The value produced by reproductive labor that doesn't register in the price system — the "free gift" to capital.

```python
def shadow_subsidy(
    tensor: ValueTensor4x3,
    visibility: np.ndarray,
) -> Currency:
    """Uncompensated reproductive labor in value terms."""
    g_33 = visibility[3, 3]  # Dept III visibility
    return tensor.dept_III.total_value * (1 - g_33)
```

---

## 5. Level 3: Derived from Model Dynamics

These tensors come from the simulation's own equations, not external data.

### 5.1 The Jacobian

If the dynamical system is:

```
dx/dt = f(x, params)
```

Then the Jacobian:

```
J_ij = ∂f_i / ∂x_j
```

**What it captures:** Local linearization of dynamics. Eigenvalues determine stability:
- All eigenvalues have negative real part → stable equilibrium
- Any eigenvalue has positive real part → unstable (runaway or collapse)
- Eigenvalue crosses zero → bifurcation (qualitative change)

```python
def compute_jacobian(
    f: Callable[[np.ndarray], np.ndarray],
    x: np.ndarray,
    epsilon: float = 1e-6,
) -> np.ndarray:
    """Numerical Jacobian via finite differences."""
    n = len(x)
    J = np.zeros((n, n))
    f_x = f(x)
    for j in range(n):
        x_plus = x.copy()
        x_plus[j] += epsilon
        J[:, j] = (f(x_plus) - f_x) / epsilon
    return J


def analyze_stability(J: np.ndarray) -> dict:
    """Stability analysis from Jacobian."""
    eigenvalues = np.linalg.eigvals(J)
    return {
        "eigenvalues": eigenvalues,
        "stable": all(ev.real < 0 for ev in eigenvalues),
        "max_real_part": max(ev.real for ev in eigenvalues),
        "oscillatory": any(abs(ev.imag) > 1e-10 for ev in eigenvalues),
    }
```

### 5.2 Bifurcation Surface

```
B = {params : det(J(params)) = 0}
```

**What it captures:** The parameter values where qualitative behavior changes. Crossing this surface transforms the system (e.g., from stable to unstable, from one attractor to another).

```python
def find_bifurcation(
    f: Callable[[np.ndarray, dict], np.ndarray],
    x_eq: Callable[[dict], np.ndarray],  # Equilibrium as function of params
    param_name: str,
    param_range: tuple[float, float],
    base_params: dict,
    resolution: int = 100,
) -> list[float]:
    """Find parameter values where det(J) ≈ 0."""
    bifurcation_points = []
    prev_sign = None

    for val in np.linspace(*param_range, resolution):
        params = {**base_params, param_name: val}
        x = x_eq(params)
        J = compute_jacobian(lambda y: f(y, params), x)
        det = np.linalg.det(J)

        if prev_sign is not None and np.sign(det) != prev_sign:
            bifurcation_points.append(val)
        prev_sign = np.sign(det)

    return bifurcation_points
```

**Application:** The George Jackson bifurcation should appear as a surface in (contradiction, solidarity) space where the system switches between CLASS_ORIENTED and NATION_ORIENTED attractors.

---

## 6. What's NOT a Tensor

Despite sometimes being called tensors or having multiple indices, these are just scalars or arrays:

| Name | Why Not a Tensor |
|------|------------------|
| `consciousness: float` | Scalar with no index structure |
| `solidarity_strength: float` | Scalar edge attribute |
| `agitation: float` | Scalar node attribute |
| `wealth: Currency` | Scalar (though it does transform under currency change) |
| `EdgeType: Enum` | Categorical, not numerical — no transformation rule |

These quantities may be *derived from* tensors, but they are not themselves tensors.

---

## 7. Integration Roadmap

### 7.1 Priority by Value/Effort Ratio

| Tensor | Value | Effort | Priority |
|--------|-------|--------|----------|
| Inter-Industry (BEA I-O) | High — unlocks supply chain analysis | Medium — annual flat files | **1** |
| Visibility Metric (ATUS) | High — formalizes shadow labor | Medium — need ATUS loader | **2** |
| Geographic Flow (BTS FAF) | High — empirical imperial rent | Medium-High — large O-D data | **3** |
| Reproduction Req (CEX) | Medium — refines V_reproduction | Medium — microdata | **4** |
| Class Transition (PSID) | Medium — validates mobility model | High — restricted, panel | **5** |

### 7.2 Loader Specifications Needed

```
src/babylon/data/
├── bea/
│   ├── io_loader.py      # Input-Output tables (NEW)
│   └── ...
├── bts/
│   └── faf_loader.py     # Freight Analysis Framework (NEW)
├── bls/
│   ├── atus_loader.py    # American Time Use Survey (NEW)
│   ├── cex_loader.py     # Consumer Expenditure Survey (NEW)
│   └── qcew/             # (EXISTS)
└── psid/
    └── loader.py         # Panel Study of Income Dynamics (NEW, restricted)
```

### 7.3 Schema Extensions

```sql
-- Inter-industry flows (Level 1)
CREATE TABLE bea_io_coefficients (
    year INTEGER,
    source_industry TEXT,
    target_industry TEXT,
    coefficient REAL,
    PRIMARY KEY (year, source_industry, target_industry)
);

-- Geographic flows (Level 1)
CREATE TABLE bts_commodity_flows (
    year INTEGER,
    origin_fips TEXT,
    dest_fips TEXT,
    commodity_sctg TEXT,
    value_millions REAL,
    tons_thousands REAL,
    PRIMARY KEY (year, origin_fips, dest_fips, commodity_sctg)
);

-- Time use (Level 1)
CREATE TABLE atus_time_use (
    year INTEGER,
    activity_code TEXT,
    demographic_group TEXT,  -- income quintile, gender, etc.
    avg_hours_per_day REAL,
    PRIMARY KEY (year, activity_code, demographic_group)
);

-- Derived: Imperial rent by county (Level 2)
CREATE VIEW imperial_rent_by_county AS
SELECT
    dest_fips as fips,
    year,
    SUM(value_millions) as inflow,
    (SELECT SUM(value_millions) FROM bts_commodity_flows b
     WHERE b.origin_fips = a.dest_fips AND b.year = a.year) as outflow,
    SUM(value_millions) - outflow as net_rent
FROM bts_commodity_flows a
GROUP BY dest_fips, year;
```

---

## 8. Theoretical Summary

```
PRIMITIVE (from QCEW + BEA ratios)
    │
    ▼
ValueTensor4x3[fips, year, dept, component]
    │
    ├──────────────────────────────────────────────┐
    │                                              │
    ▼                                              ▼
LEVEL 1: Direct from Federal Data          LEVEL 1: Direct from Federal Data
    │                                              │
    ├─ InterIndustryFlow[i,j] ◄─── BEA I-O        ├─ VisibilityMetric[μ,ν] ◄─── ATUS/QCEW
    ├─ GeographicFlow[a,b] ◄────── BTS FAF        ├─ ReproductionReq[c,d,u] ◄── CEX/ATUS
    └─ ClassTransition[c,c'] ◄──── PSID           │
                                                   │
    ┌──────────────────────────────────────────────┘
    │
    ▼
LEVEL 2: Mathematical Transformation
    │
    ├─ LeontiefInverse = (I - A)^{-1}
    ├─ ImperialRentField = antisym(GeographicFlow)
    ├─ StationaryClass = eigenvector(ClassTransition)
    └─ ShadowSubsidy = Dept_III × (1 - g₃₃)
    │
    ▼
LEVEL 3: From Model Dynamics
    │
    ├─ Jacobian = ∂f/∂x
    └─ BifurcationSurface = {params : det(J) = 0}
```

Every arrow is either:
- **Data loading** (federal statistics → tensor)
- **Mathematical operation** (tensor → derived tensor)
- **Model equation** (state → derivative)

No magic numbers. No behavioral psychology imports. Every quantity traces to either the primitive tensor or documented federal data.

---

## 9. Validation Strategy

Each tensor has empirical predictions that can be checked:

| Tensor | Prediction | Test |
|--------|------------|------|
| InterIndustryFlow | Leontief inverse predicts output multipliers | Compare to BEA published multipliers |
| GeographicFlow | ImperialRentField correlates with income levels | Regress Φ against per-capita income by county |
| ClassTransition | Stationary dist ≈ observed class distribution | Compare π to current Census class proxies |
| VisibilityMetric | g₃₃ < g₁₁ (reproductive labor less visible) | Direct computation from ATUS/QCEW |
| Jacobian | Stability predicts crisis timing | Backtest against historical crises |

If any of these fail, we've learned something — the model is falsifiable, not merely interpretive.
