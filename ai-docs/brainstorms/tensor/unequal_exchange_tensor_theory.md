# The Gamma Tensor: Visibility Coefficients in Value-Price Transformation

**Status**: Theoretical Foundation Document
**Related**: `tensor_hierarchy.md`, `department_iii_formalization.md`
**Principle**: γ measures the fraction of labor-time that survives transformation to price-space

---

## 1. Theoretical Motivation

### 1.1 The Problem

Marxian value theory measures economic activity in labor-time. Bourgeois economics measures it in prices. The transformation between these spaces is not uniform—some labor "counts" more than others in the price system.

Two distinct mechanisms produce this distortion:

**Mechanism A: Naturalization (Domestic)**
Reproductive labor is ideologically positioned as "not real work." A mother raising a child performs labor that produces the commodity labor-power, but this labor registers as zero in GDP. The work is invisible because it is *naturalized*—treated as a free gift of nature rather than social production.

**Mechanism B: Unequal Exchange (Imperial)**
Peripheral labor is devalued through the price system. A Congolese miner's hour produces value, but when that value crosses into the core via commodity exchange, PPP differentials compress it. An hour of Congolese labor might exchange for 0.1 hours of American labor in the price system, despite being equivalent in the labor-time system.

Both mechanisms produce the same formal effect: labor-time that exists but doesn't fully register in prices. The Gamma tensor captures this.

### 1.2 Why a Separate Tensor

The ValueTensor4x3 (T^μ_ν) measures value in labor-hours across departments (μ) and components (ν ∈ {c, v, s}). These are *extensive* quantities—they sum under aggregation.

Visibility is *intensive*—a dimensionless ratio that must be weighted-averaged, not summed, under aggregation. Concatenating γ as a fourth column of T would break the tensor's transformation properties.

The rigorous structure is two objects that compose via multiplication:

```
T^μ_ν         # ValueTensor (4×3), extensive
γ_μ           # GammaTensor (4×1), intensive
T_price^μ_ν = γ_μ · T^μ_ν    # Price-visible value
```

---

## 2. Definition

### 2.1 Index Structure

```
γ_μ[fips, year] where μ ∈ {I, IIa, IIb, III}
```

**Index spaces:**
- Geographic: 5-digit FIPS code (3,143 US counties)
- Temporal: Year
- Department: 4 Marxian departments

**Range:** γ_μ ∈ [0, 1] for each department

**Interpretation:**
- γ = 1: All labor in this department registers fully in prices
- γ = 0: Labor in this department is completely invisible to the price system
- γ ∈ (0, 1): Partial visibility

### 2.2 Formal Definition by Department

**Department III (Reproductive Labor):**

```
γ_III = paid_hours / (paid_hours + unpaid_hours)
```

Where:
- `paid_hours` = QCEW employment in care sectors (NAICS 624, 814, portions of 62)
- `unpaid_hours` = ATUS unpaid household/care labor

This measures what fraction of reproductive labor is commodified.

**Departments I, IIa, IIb (Production of Means of Production, Wage Goods, Luxury Goods):**

```
γ_μ = Σ_i (input_share_i × g_origin_i)
```

Where:
- `input_share_i` = fraction of department μ's inputs sourced from origin i
- `g_origin_i` = visibility coefficient at origin (PPP_rate / market_exchange_rate for international; wage_ratio proxy for domestic)

This measures how much embedded labor survives the commodity chain.

---

## 3. Transformation Properties

### 3.1 Under Geographic Aggregation

γ does NOT sum. Under county → state aggregation:

```
γ_μ[state] = Σ_county (T^μ_total[county] × γ_μ[county]) / Σ_county T^μ_total[county]
```

Visibility is weighted by the value it applies to. A state's γ is the value-weighted average of its counties' γ values.

### 3.2 Under Temporal Aggregation

Same principle—value-weighted averaging:

```
γ_μ[year] = Σ_quarter (T^μ_total[quarter] × γ_μ[quarter]) / Σ_quarter T^μ_total[quarter]
```

### 3.3 Composition with ValueTensor

Price-visible value for department μ, component ν:

```
T_price^μ_ν[fips, year] = γ_μ[fips, year] × T^μ_ν[fips, year]
```

Total shadow value (value produced but not priced):

```
S^μ_ν = (1 - γ_μ) × T^μ_ν
```

Total shadow subsidy to capital:

```
Φ_shadow = Σ_μ Σ_ν S^μ_ν = Σ_μ (1 - γ_μ) × T^μ_total
```

---

## 4. The Two Mechanisms in Detail

### 4.1 Naturalization (Department III)

Reproductive labor is spatially constrained—it must be performed where the labor-power is consumed. You cannot outsource raising a child to another continent (mail-order brides and migrant domestic workers are the exceptions that prove the rule by *importing the worker*).

Because the labor cannot be arbitraged spatially, capital extracts value through ideological naturalization: domestic labor is "what women naturally do," not work deserving wages.

**Data flow:**
```
ATUS (unpaid hours by activity) + QCEW (paid care employment)
    ↓
γ_III = paid / (paid + unpaid)
```

**Geographic variation:** γ_III varies by:
- Labor force participation rates (more dual-income households → more commodified care)
- Availability of paid care infrastructure
- Demographic composition (immigrant domestic workers carry lower γ from origin)

### 4.2 Unequal Exchange (Departments I, IIa, IIb)

Commodity value flows through supply chains. At each edge, PPP differentials compress peripheral labor-time into fewer core labor-time equivalents.

Consider the semiconductor chain:

| Node | Labor contributed | Cumulative γ |
|------|-------------------|--------------|
| Congo (mining) | 100 hours | 1.0 |
| → China (refining) | +50 hours | 0.85 (Congo labor now at 0.7 visibility) |
| → Taiwan (fab) | +30 hours | 0.75 |
| → Vietnam (assembly) | +20 hours | 0.70 |
| → USA (integration) | +10 hours | 0.65 |

The 100 hours of Congolese labor now registers as ~15 hours in the final US price. The 200 total hours register as ~65. The difference (135 hours) is imperial rent—value that exists in the labor-time metric but vanishes in the price metric.

**The path integral problem:**

Rigorous calculation requires tracking visibility along every path through the supply graph:

```
γ_embedded[k] = Σ_paths (path_probability × ∏_edges γ_edge)
```

This is computationally intractable for full supply chains.

**The trade-exposure approximation:**

For practical implementation, approximate γ for Departments I/II using trade exposure:

```
γ_μ[fips] ≈ Σ_origin (import_share[fips, origin] × γ_country[origin])
```

Where:
- `import_share` = fraction of inputs from each origin (BEA I-O + trade data)
- `γ_country` = national visibility coefficient (Penn World Tables PPP / exchange rate)

This collapses the path integral into a single-step weighted average, losing precision but remaining tractable.

---

## 5. Node vs Edge: The Architectural Subtlety

### 5.1 Department III: γ Lives on Nodes (Persons)

Reproductive labor visibility attaches to the *worker*, not the flow. A Filipina domestic worker in Los Angeles carries her origin γ with her. The shadow extraction happens at the point of employment, not along a supply chain.

Formally: γ_III[fips] is a weighted average over the demographic composition of reproductive workers at that location.

```
γ_III[fips] = Σ_d (worker_share[fips, d] × γ_origin[d])
```

Where d indexes demographic groups by national origin / racialization.

### 5.2 Departments I, IIa, IIb: γ Emerges from Edges (Flows)

Production visibility attaches to *commodity flows*, not locations. The same factory has different effective γ depending on its supply chain.

Formally: γ_μ[fips] is derived from the flow-weighted visibility of incoming edges.

```
γ_μ[fips] = f(GeographicFlow[*, fips], γ_edge[*, fips])
```

### 5.3 Implementation Consequence

The Gamma tensor as stored (node-indexed, 4×1 per fips/year) is a *reduced representation*. The underlying structure is:

- **Department III:** Node attributes (demographic composition) → γ_III
- **Departments I/II:** Edge attributes (flow × PPP) → aggregate to γ_μ at destination

The spec must distinguish between:
1. **γ_raw** — the edge/demographic level visibility coefficients
2. **γ_μ** — the node-level aggregate suitable for composition with T^μ_ν

---

## 6. Data Sources

### 6.1 Department III

| Source | Provides | Resolution |
|--------|----------|------------|
| ATUS | Unpaid labor hours by activity, demographics | National, annual |
| QCEW | Paid employment in care sectors | County, quarterly |
| ACS | Demographic composition (nativity, race) | County, annual |

**Gap:** ATUS is national-level. Allocating to counties requires demographic proxying via ACS.

### 6.2 Departments I, IIa, IIb

| Source | Provides | Resolution |
|--------|----------|------------|
| Penn World Tables | PPP vs exchange rates by country | National, annual |
| BEA I-O Tables | Industry input requirements | National, annual |
| Census Trade Data | Import origins by commodity | National, monthly |
| BTS FAF | Domestic freight flows | State-to-state, periodic |

**Gap:** Connecting international trade data to county-level consumption requires BEA I-O allocation assumptions.

---

## 7. Derived Quantities

### 7.1 Shadow Subsidy

Total value produced but not compensated:

```
Φ_shadow[fips, year] = Σ_μ (1 - γ_μ) × T^μ_total
```

This is capital's "free lunch"—value extracted without equivalent payment.

### 7.2 Imperial Rent (Revised)

Previously defined as the antisymmetric part of geographic flows. With γ, we can decompose further:

```
Φ_imperial[fips] = Σ_origin (inflow[origin, fips] × (1 - γ_edge[origin, fips]))
```

Imperial rent is specifically the value lost to PPP compression on incoming flows.

### 7.3 Domestic Rent (Department III)

```
Φ_domestic[fips] = (1 - γ_III) × T^III_total
```

The reproductive labor subsidy, distinct from imperial extraction.

### 7.4 Total Extraction

```
Φ_total = Φ_imperial + Φ_domestic
```

The full value transfer invisible to the price system.

---

## 8. Validation Criteria

### 8.1 Internal Consistency

**Bound check:** γ_μ ∈ [0, 1] always. Any computation yielding γ outside this range indicates an error.

**Aggregation invariance:** National γ computed via two paths should match:
- Path A: Aggregate T to national, compute γ from national ATUS/trade data
- Path B: Compute county γ, value-weight average to national

Discrepancy indicates data inconsistency.

### 8.2 Empirical Predictions

| Prediction | Test |
|------------|------|
| γ_III < γ_I for all fips | Direct computation—reproductive labor less commodified than industrial |
| γ correlates negatively with periphery status | Regress γ against per-capita income |
| Φ_shadow correlates with profit rate | Higher shadow extraction → higher apparent profitability |
| γ_III varies by gender composition of workforce | Counties with more female labor force participation have higher γ_III |

### 8.3 Falsification Conditions

The Gamma tensor framework is falsified if:

1. Shadow subsidy (Φ_shadow) shows no correlation with profitability
2. γ_III shows no variation across demographic compositions
3. PPP-derived γ for trade flows fails to predict wage differentials
4. Aggregation paths produce systematically different results (transformation property failure)

---

## 9. Relation to Existing Literature

### 9.1 Fortunati (The Arcane of Reproduction)

Fortunati's "rate of exploitation of the houseworker" maps directly to:

```
e_domestic = (1 - γ_III) / γ_III
```

When γ_III → 0, exploitation rate → ∞ (total naturalization).

### 9.2 Emmanuel / Amin (Unequal Exchange)

Emmanuel's "transfer of value" through trade corresponds to:

```
V_transfer = Σ_flows (labor_content × (1 - γ_edge))
```

The Gamma tensor formalizes Emmanuel's mechanism without requiring the problematic assumption of international wage equalization.

### 9.3 Hickel et al. (Quantifying Imperial Drain)

Hickel's estimates of North-South value transfer can be derived from:

```
Φ_imperial[North] = Σ_South Σ_commodity (flow[South→North] × (1 - γ[South→North]))
```

The Gamma tensor provides the micro-foundation for Hickel's macro measurements.

---

## 10. Summary

The Gamma tensor (γ_μ) completes the value-price transformation by specifying *how much* labor-time survives the passage into price-space.

**Key properties:**
- Intensive (dimensionless ratio), not extensive
- Weighted-averages under aggregation, does not sum
- Distinct mechanisms by department: naturalization (III) vs unequal exchange (I, IIa, IIb)
- Composes multiplicatively with ValueTensor4x3

**Architectural implication:**
- Stored as 4×1 vector per fips/year
- Computed from edge-level (trade) and node-level (demographic) raw data
- Distinct from T^μ_ν but always used in conjunction with it

**Theoretical payoff:**
- Unifies reproductive labor invisibility and imperial rent extraction in single formalism
- Makes "shadow value" precisely measurable
- Connects Marx (value theory) ↔ Fortunati (domestic labor) ↔ Emmanuel (unequal exchange) ↔ Hickel (empirical measurement)
