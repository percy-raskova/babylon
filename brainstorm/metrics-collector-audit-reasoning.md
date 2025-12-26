# MetricsCollector Audit: Sequential Reasoning Process

**Date:** 2025-12-25
**Context:** Comprehensive audit of MetricsCollector against codebase
**Method:** 9-step sequential thinking analysis

---

## Thought 1: Scoping the Audit

Starting a comprehensive audit of MetricsCollector metrics coverage. I need to compare what the collector gathers against what actually exists in the codebase. The key sources to examine are:

1. MetricsCollector itself (what it collects)
2. SocialClass entity model (what entity data exists)
3. Relationship entity model (what edge data exists)
4. WorldState model (what global state exists)
5. EconomyState model (what economy data exists)
6. Parameter analysis tool (what the sweeper collects - should align)
7. Dashboard components (what UI needs)
8. Event types (should events be tracked as metrics?)

My hypothesis is there may be gaps in:
- Territory/spatial metrics (we have TerritorySystem)
- Event counts per tick
- Solidarity network metrics (percolation ratio, component counts)
- Heat dynamics from carceral geography

Let me systematically gather the facts before drawing conclusions.

---

## Thought 2: Analyzing SocialClass and Relationship Models

Analyzing the data models. SocialClass has these fields that could be metrics:

**FROM SocialClass (entity):**
- wealth: Currency ✓ (collector has)
- ideology.class_consciousness: Probability ✓ (collector has)
- ideology.national_identity: Probability ✓ (collector has)
- ideology.agitation: Probability ✓ (collector has)
- p_acquiescence: Probability ✓ (collector has)
- p_revolution: Probability ✓ (collector has)
- organization: Probability ✓ (collector has)
- subsistence_threshold: Currency ✗ MISSING
- repression_faced: Probability ✗ MISSING
- effective_wealth: Currency ✗ MISSING (PPP)
- unearned_increment: Currency ✗ MISSING (PPP)
- ppp_multiplier: float ✗ MISSING (PPP)

**FROM Relationship (edge):**
- value_flow: Currency (via exploitation_rent) ✓
- tension: Intensity ✓ (via exploitation_tension)
- subsidy_cap: Currency ✗ MISSING
- solidarity_strength: Coefficient ✓ (collector has)

But EdgeMetrics only tracks ONE of each edge type. If there are multiple EXPLOITATION edges, only the last one is captured.

**FROM WorldState:**
- tick: int ✓
- territories: dict ✗ NOT TRACKED AT ALL
- event_log: list[str] ✗ NOT TRACKED
- events: list[SimulationEvent] ✗ NOT TRACKED
- economy: GlobalEconomy ✗ NEED TO CHECK THIS

I need to see GlobalEconomy and Territory models.

---

## Thought 3: Comparing with parameter_analysis.py

Comparing MetricsCollector with parameter_analysis.py:

**PARAMETER_ANALYSIS.PY COLLECTS (collect_tick_data):**
- tick ✓
- p_w_wealth, p_w_consciousness, p_w_national_identity, p_w_agitation, p_w_psa, p_w_psr, p_w_organization ✓
- p_c_wealth ✓ (just wealth for Comprador)
- c_b_wealth ✓ (just wealth for Core Bourgeoisie)
- c_w_wealth, c_w_consciousness, c_w_national_identity, c_w_agitation ✓
- exploitation_tension, exploitation_rent, tribute_flow, wages_paid, solidarity_strength ✓

**METRICS_COLLECTOR COLLECTS (compare to above):**
- tick ✓
- EntityMetrics for p_w (C001): wealth, consciousness, national_identity, agitation, p_acquiescence, p_revolution, organization ✓
- EntityMetrics for p_c (C002): same fields... but wait!

**DISCREPANCY FOUND:**
- parameter_analysis.py only collects p_c.wealth (not full EntityMetrics)
- parameter_analysis.py only collects c_b.wealth (not full EntityMetrics)
- parameter_analysis.py collects c_w.wealth + consciousness + national_identity + agitation (but NOT p_acquiescence, p_revolution, organization)

MetricsCollector gives FULL EntityMetrics to all 4 classes (p_w, p_c, c_b, c_w).

This is actually BETTER than parameter_analysis.py! MetricsCollector has MORE data.

But let me check to_csv_rows() in MetricsCollector to see if it properly flattens...

---

## Thought 4: Comprehensive Gap Analysis

Now I have comprehensive data. Let me create a full audit matrix.

### WHAT METRICS_COLLECTOR CURRENTLY TRACKS

**EntityMetrics (per entity: p_w, p_c, c_b, c_w)**
- wealth ✓
- consciousness (class_consciousness) ✓
- national_identity ✓
- agitation ✓
- p_acquiescence ✓
- p_revolution ✓
- organization ✓

**EdgeMetrics**
- exploitation_tension ✓
- exploitation_rent ✓
- tribute_flow ✓
- wages_paid ✓
- solidarity_strength ✓

**TickMetrics**
- tick ✓
- imperial_rent_pool ✓
- global_tension ✓

### WHAT EXISTS IN CODEBASE BUT IS NOT TRACKED

**SocialClass fields MISSING:**
1. subsistence_threshold - important for survival calculus understanding
2. repression_faced - state violence level against each class
3. effective_wealth - PPP-adjusted wealth (material basis of labor aristocracy)
4. unearned_increment - PPP bonus (exploitation benefit)
5. ppp_multiplier - PPP adjustment factor

**Relationship fields MISSING:**
1. subsidy_cap - for CLIENT_STATE edges
2. Other edge-specific tensions (only EXPLOITATION tension tracked, what about tension on other edges?)

**GlobalEconomy fields MISSING:**
1. current_super_wage_rate - dynamic wage rate
2. current_repression_level - system-wide repression

**Territory system COMPLETELY MISSING:**
1. heat (state attention level)
2. rent_level
3. population
4. under_eviction flag
5. sector_type, territory_type, profile
6. is_sink_node derived property

**TopologyMonitor metrics MISSING:**
1. num_components
2. max_component_size (L_max)
3. percolation_ratio
4. potential_liquidity
5. actual_liquidity
6. cadre_density
7. is_resilient

**Event tracking MISSING:**
1. Event count per tick
2. Event types that occurred
3. Specific event data (could track ECONOMIC_CRISIS, UPRISING, etc.)

**Derived/Computed metrics MISSING:**
1. consciousness_gap = p_w.consciousness - c_w.consciousness (important differential)
2. wealth_gap = c_b.wealth - p_w.wealth (exploitation indicator)
3. crossover_approaching = (p_revolution - p_acquiescence) as ratio approaches 0

---

## Thought 5: Priority Analysis

**PRIORITY ANALYSIS - Which gaps matter most?**

### CRITICAL GAPS (Dashboard needs these NOW)
1. **GlobalEconomy.current_super_wage_rate** - Core driver of labor aristocracy dynamics
2. **GlobalEconomy.current_repression_level** - Core driver of P(S|R)
3. **TopologyMonitor.percolation_ratio** - Key phase transition indicator
4. **TopologyMonitor.cadre_density** - Vanguard vs mass movement

These 4 metrics are CRUCIAL for understanding the 4-node Imperial Circuit.
Without wage rate and repression level, you can't see why bourgeoisie decisions matter.
Without percolation/cadre, you can't see revolutionary potential.

### HIGH PRIORITY GAPS (Enhance analysis significantly)
5. **Derived: consciousness_gap** (p_w.consciousness - c_w.consciousness)
6. **Derived: wealth_gap** (c_b.wealth - p_w.wealth)
7. **Entity: repression_faced** (per-class state violence)
8. **TopologyMonitor.num_components** (movement fragmentation)
9. **Event counts** (how many CRISIS, UPRISING per tick)

### MEDIUM PRIORITY (Nice for deep analysis)
10. **Entity: subsistence_threshold** (survival calculus input)
11. **PPP fields** (effective_wealth, unearned_increment)
12. **Territory metrics** (heat, population, eviction status)
13. **TopologyMonitor.is_resilient** (Sword of Damocles)

### LOW PRIORITY (Rarely needed in dashboard)
14. **Relationship.subsidy_cap** - static parameter, not dynamic metric
15. **Edge tensions on non-EXPLOITATION edges** - usually 0

### ALIGNMENT CHECK: MetricsCollector vs parameter_analysis.py

**GOOD NEWS:** MetricsCollector's to_csv_rows() doesn't align perfectly!

Looking at to_csv_rows() lines 117-157:
- It exports p_w: full 7 fields ✓
- It exports p_c: only wealth (intentionally sparse) ✓
- It exports c_b: only wealth (intentionally sparse) ✓
- It exports c_w: wealth + consciousness + national_identity + agitation ✓

But wait - this is LESS than what TickMetrics stores!
TickMetrics stores FULL EntityMetrics for all 4 entities.
But to_csv_rows() only exports a SUBSET for p_c and c_b.

This is a BUG or design decision? Let me check if it matches parameter_analysis.py...

---

## Thought 6: Verifying CSV Export Alignment

Checking to_csv_rows() alignment with parameter_analysis.py:

**PARAMETER_ANALYSIS.PY collect_tick_data():**
- p_w: wealth, consciousness, national_identity, agitation, psa, psr, organization (7 fields) ✓
- p_c: wealth only (1 field) ✓
- c_b: wealth only (1 field) ✓
- c_w: wealth, consciousness, national_identity, agitation (4 fields) ✓
- edges: exploitation_tension, exploitation_rent, tribute_flow, wages_paid, solidarity_strength ✓

**METRICS_COLLECTOR to_csv_rows():**
- p_w: wealth, consciousness, national_identity, agitation, psa, psr, organization (7 fields) ✓
- p_c: wealth only (1 field) ✓
- c_b: wealth only (1 field) ✓
- c_w: wealth, consciousness, national_identity, agitation (4 fields) ✓
- edges: exploitation_tension, exploitation_rent, tribute_flow, wages_paid, solidarity_strength ✓

**PERFECT MATCH!** The to_csv_rows() intentionally sparsely exports to match parameter_analysis.py.

But the TickMetrics model itself stores FULL EntityMetrics for all 4 entities (7 fields each).
This is GOOD - the model is MORE CAPABLE than what's exported to CSV.
The dashboard can access full data via collector.latest.p_c.consciousness etc.

### DESIGN INSIGHT
The sparse CSV export is correct for:
- Comprador (p_c): Bourgeois class, consciousness not relevant to revolution
- Core Bourgeoisie (c_b): Same - their ideology is fixed at capitalist
- Labor Aristocracy (c_w): Their consciousness IS relevant (can break from imperialism)
- Periphery Worker (p_w): MOST relevant - revolutionary subject

### ACTUAL GAPS SUMMARY

The MetricsCollector is well-aligned with parameter_analysis.py.
But both are MISSING important metrics:

**CRITICAL MISSING FROM BOTH:**
1. GlobalEconomy.current_super_wage_rate
2. GlobalEconomy.current_repression_level
3. TopologyMonitor metrics (percolation_ratio, cadre_density, etc.)

These aren't just "nice to have" - they're core to understanding the 4-node model!

---

## Thought 7: Creating the Complete Audit Matrix

**SYNTHESIS: Final Audit Matrix**

### CURRENT STATE
- MetricsCollector is the ONLY observer registered with dashboard Simulation
- NarrativeDirector is searched for but may not be present
- TopologyMonitor is NOT registered - percolation metrics unavailable

### COMPLETE GAPS ANALYSIS

#### A. ENTITY METRICS GAPS (SocialClass fields not in EntityMetrics)
| Field | Type | Importance | Why |
|-------|------|------------|-----|
| subsistence_threshold | Currency | Medium | Input to survival calculus |
| repression_faced | Probability | HIGH | State violence per class |
| effective_wealth | Currency | Medium | PPP-adjusted (labor aristocracy) |
| unearned_increment | Currency | Medium | Exploitation benefit |
| ppp_multiplier | float | Low | Usually static |

#### B. GLOBAL ECONOMY GAPS (not tracked at all)
| Field | Type | Importance | Why |
|-------|------|------------|-----|
| current_super_wage_rate | Coefficient | CRITICAL | Drives C_w loyalty |
| current_repression_level | Probability | CRITICAL | Systemic P(S|R) factor |

#### C. TOPOLOGY METRICS GAPS (TopologyMonitor not integrated)
| Field | Type | Importance | Why |
|-------|------|------------|-----|
| percolation_ratio | Probability | CRITICAL | Phase transition indicator |
| cadre_density | float | CRITICAL | Vanguard vs mass movement |
| num_components | int | High | Movement fragmentation |
| max_component_size | int | High | Giant component size |
| is_resilient | bool | Medium | Sword of Damocles |
| potential_liquidity | int | Medium | Sympathizer count |
| actual_liquidity | int | Medium | Cadre count |

#### D. DERIVED METRICS GAPS (not computed)
| Metric | Formula | Importance | Why |
|--------|---------|------------|-----|
| consciousness_gap | p_w.consciousness - c_w.consciousness | HIGH | Revolutionary divergence |
| wealth_gap | c_b.wealth - p_w.wealth | HIGH | Exploitation intensity |
| crossover_delta | p_revolution - p_acquiescence | HIGH | Rupture proximity |

#### E. EVENT METRICS GAPS
| Metric | Type | Importance | Why |
|--------|------|------------|-----|
| event_count | int | Medium | Activity level per tick |
| event_types | list[EventType] | Medium | What happened |

#### F. TERRITORY METRICS GAPS (completely untracked)
| Field | Type | Importance | Why |
|-------|------|------------|-----|
| heat (avg) | Intensity | Medium | State attention level |
| population (total) | int | Medium | Human shield count |
| eviction_count | int | Medium | Active evictions |

### RECOMMENDATIONS

**PHASE 1 (Critical - without these dashboard is incomplete):**
1. Add GlobalEconomy metrics (super_wage_rate, repression_level)
2. Add topology summary metrics (percolation_ratio, cadre_density)
3. Add derived differentials (consciousness_gap, wealth_gap)

**PHASE 2 (High - significantly improves analysis):**
4. Add repression_faced to EntityMetrics
5. Add num_components to understand fragmentation
6. Add event_count tracking

**PHASE 3 (Medium - nice to have):**
7. Territory aggregate metrics
8. Full TopologySnapshot history
9. PPP fields

---

## Thought 8: Implementation Issues Found

**IMPLEMENTATION ISSUES FOUND**

### 1. Edge Metrics Only Track LAST Edge of Each Type
In _extract_edge_metrics(), when iterating over relationships:
```python
for rel in state.relationships:
    if rel.edge_type == EdgeType.EXPLOITATION:
        exploitation_tension = float(rel.tension)  # OVERWRITES!
```
If there are multiple EXPLOITATION edges (e.g., P_w→C_b AND P_w→P_c), only the LAST one is captured.

**IMPACT:** Medium. Current 4-node model has one EXPLOITATION edge (P_w→P_c).
But if we expand to multi-exploitation scenarios, this will fail.

### 2. global_tension Averaging Issue
```python
def _compute_global_tension(self, state: WorldState) -> float:
    total_tension = sum(float(rel.tension) for rel in state.relationships)
    return total_tension / len(state.relationships)
```
This averages tension across ALL edge types including SOLIDARITY, WAGES, TRIBUTE, etc.
Most of those have tension=0.0 by default, diluting the meaningful EXPLOITATION tension.

**IMPACT:** The global_tension metric is artificially low and misleading.
Should probably only average EXPLOITATION edge tensions.

### 3. No Integration with TopologyMonitor
The dashboard creates a Simulation with only MetricsCollector.
TopologyMonitor has rich percolation metrics but they're not exposed.

**SOLUTION:** Either:
- Add TopologyMonitor to dashboard observers list
- Or have MetricsCollector compute topology metrics itself
- Or create a TopologyMetrics model and integrate

### 4. No GlobalEconomy Access
MetricsCollector only accesses state.economy.imperial_rent_pool
But GlobalEconomy has current_super_wage_rate and current_repression_level
that are not captured.

### FINAL VERDICT

The MetricsCollector is a GOOD START but has significant gaps:
- Missing CRITICAL economy driver metrics (wage rate, repression)
- Missing CRITICAL topology metrics (percolation, cadre density)
- Edge metrics may fail with multiple edges of same type
- global_tension calculation is misleading

The current implementation covers ~60% of what a comprehensive metrics system needs.

---

## Thought 9: Final Recommendations with Implementation Details

**FINAL RECOMMENDATIONS WITH IMPLEMENTATION DETAILS**

### PRIORITY 1: Add Economy Driver Metrics to TickMetrics

**Location:** src/babylon/models/metrics.py (TickMetrics class)

Add fields:
```python
current_super_wage_rate: Coefficient = Field(
    default=0.20,
    ge=0.0,
    description="Dynamic wage rate from GlobalEconomy"
)
current_repression_level: Probability = Field(
    default=0.5,
    ge=0.0,
    le=1.0,
    description="System-wide repression modifier from GlobalEconomy"
)
```

**Location:** src/babylon/engine/observers/metrics.py (_record_snapshot method)

Add extraction:
```python
current_super_wage_rate = 0.20
current_repression_level = 0.5
if state.economy is not None:
    current_super_wage_rate = float(state.economy.current_super_wage_rate)
    current_repression_level = float(state.economy.current_repression_level)
```

### PRIORITY 2: Add Topology Summary Metrics

Add new model to metrics.py:
```python
class TopologySummary(BaseModel):
    percolation_ratio: Probability
    cadre_density: float
    num_components: int
    phase: str  # "gaseous", "transitional", "liquid", "solid"
```

Add to TickMetrics:
```python
topology: TopologySummary | None = Field(default=None)
```

In MetricsCollector, compute these inline or integrate with TopologyMonitor.

### PRIORITY 3: Fix global_tension Calculation

**Current (wrong):**
```python
total_tension = sum(float(rel.tension) for rel in state.relationships)
return total_tension / len(state.relationships)
```

**Fixed:**
```python
exploitation_edges = [r for r in state.relationships if r.edge_type == EdgeType.EXPLOITATION]
if not exploitation_edges:
    return 0.0
return sum(float(r.tension) for r in exploitation_edges) / len(exploitation_edges)
```

### PRIORITY 4: Add Derived Metrics

Add to TickMetrics:
```python
consciousness_gap: float | None = Field(default=None, description="p_w.consciousness - c_w.consciousness")
wealth_gap: Currency | None = Field(default=None, description="c_b.wealth - p_w.wealth")
```

Compute in _record_snapshot after entity extraction.

### SUMMARY

- **Tests needed:** ~30-40 new tests for new metrics
- **Effort:** Medium (2-3 hours of TDD work)
- **Impact:** HIGH - transforms dashboard from "interesting" to "insightful"

---

## Conclusion

The MetricsCollector audit revealed that while the current implementation correctly tracks entity and edge metrics aligned with parameter_analysis.py, it is missing critical "driver" metrics from GlobalEconomy and "phase state" metrics from TopologyMonitor.

The dashboard currently shows **effects** (wealth changes, tension levels) but not **causes** (wage rate decisions, repression levels) or **phase state** (revolutionary organization level).

Fixing these gaps would transform the dashboard from a passive display into an insightful analytical tool that shows the full causal chain of the Imperial Circuit model.
