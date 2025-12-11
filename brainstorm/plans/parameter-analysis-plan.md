# Parameter Analysis Plan

> **Status:** PLANNED
> **Created:** 2025-12-11
> **Spec:** ai-docs/parameter-analysis.yaml

## The Problem

Current `tune_parameters.py` only tells us "periphery died at tick 27". We discovered
the **Imperial Collapse Dynamic** (greedy empires die faster) by accident. We need
systematic observation to find more emergent behaviors.

## The Insight

We're not just tuning numbers - we're **validating theory**. The simulation should
produce dynamics that match MLM-TW predictions:

- Imperial rent creates labor aristocracy
- Over-extraction collapses the system
- Solidarity enables revolutionary transmission
- Absence of solidarity produces fascism

If the model doesn't produce these dynamics, either the parameters are wrong or
the formulas need adjustment.

## Proposed Tool: `tools/parameter_analysis.py`

### Three Commands

| Command | What It Does | Output |
|---------|--------------|--------|
| `trace` | Single sim, full time-series | CSV: every tick, all states |
| `sweep` | Vary one parameter | CSV: outcomes per value |
| `grid` | Vary two parameters | CSV: heatmap data |

### Usage Examples

```bash
# Deep dive into extraction=0.2
python tools/parameter_analysis.py trace \
  --param economy.extraction_efficiency=0.2 \
  --ticks 50 \
  --csv results/trace_0.2.csv

# Find extraction boundary with rich data
python tools/parameter_analysis.py sweep \
  --param economy.extraction_efficiency \
  --start 0.1 --end 0.5 --step 0.05 \
  --csv results/extraction_sweep.csv

# Find extraction × super_wage interaction
python tools/parameter_analysis.py grid \
  --param1 economy.extraction_efficiency --range1 0.1,0.4,0.1 \
  --param2 economy.super_wage_rate --range2 0.1,0.5,0.1 \
  --csv results/grid_search.csv
```

## Data We Want to Capture

### Per Entity (every tick)

| Entity | Metrics |
|--------|---------|
| Periphery Worker (P_w) | wealth, consciousness, organization, P(S\|A), P(S\|R) |
| Comprador (P_c) | wealth |
| Core Bourgeoisie (C_b) | wealth, tribute_inflow |
| Labor Aristocracy (C_w) | wealth, consciousness, wages_received |

### Per Edge (every tick)

| Edge | Metrics |
|------|---------|
| EXPLOITATION | tension, rent_extracted |
| TRIBUTE | value_transferred |
| WAGES | wages_paid |
| SOLIDARITY | strength, transmission_delta |

### Derived Metrics

- `crossover_tick` - when P(S|R) > P(S|A) (revolution becomes rational)
- `imperial_rent_cumulative` - total extraction over simulation
- `system_wealth_total` - conservation check
- `labor_aristocracy_ratio` - W/V for core workers

## Research Questions

### Imperial Dynamics

1. **At what extraction rate does C_b start LOSING wealth?**
   - Hypothesis: High extraction kills host before rent accumulates
   - Already found: Imperial Collapse Dynamic

2. **Is there a "Goldilocks zone"?**
   - Some rate where periphery barely survives indefinitely
   - Empire stable but tension building

3. **How does super_wage_rate affect stability?**
   - Higher wages = more loyal C_w but faster C_b drain
   - Grid search to find interaction

### Consciousness Dynamics

4. **When does Labor Aristocracy consciousness rise?**
   - Hypothesis: Only when super-wages drop below value produced
   - Track c_w_consciousness vs c_w_wages over time

5. **What triggers revolutionary crossover?**
   - P(S|R) > P(S|A) requires low wealth AND high organization
   - Track crossover_tick vs initial organization

### Fascist Bifurcation

6. **Does absent solidarity produce fascism?**
   - Same crisis, different outcomes
   - Compare solidarity=0 vs solidarity>0 scenarios
   - Validates ADR016

## Implementation Phases

### Phase 1: Trace Command (First)
- Single simulation with full CSV output
- Track all 4 entities + key edges
- Calculate derived metrics
- TDD: tests first

### Phase 2: Sweep Enhancement
- Richer metrics than current tune_parameters.py
- Crossover tick detection
- Peak consciousness tracking

### Phase 3: Grid Search
- 2D parameter space exploration
- Heatmap-ready output
- Find interaction effects

### Phase 4: Analysis Sprint
- Run comprehensive sweeps
- Document findings in balance-tuning.yaml
- Validate theoretical predictions
- Identify parameter interactions

## Key Discoveries So Far

### Imperial Collapse Dynamic (2025-12-11)

- **Observation:** Higher extraction → lower max tension
- **Initial interpretation:** Bug - tension should rise with exploitation
- **Correct interpretation:** Feature - greedy empires collapse faster
- **Implication:** Strategic depth (burn bright vs sustain)

This was discovered accidentally. Systematic analysis will find more.

## Success Criteria

1. Tool produces clean, analyzable CSV data
2. Can answer all research questions with data
3. Findings documented in balance-tuning.yaml
4. Theory predictions validated or contradicted with evidence
5. Optimal parameter ranges identified for playability

## Related Files

- `ai-docs/parameter-analysis.yaml` - Full specification
- `ai-docs/balance-tuning.yaml` - Findings registry
- `ai-docs/formulas-spec.yaml` - Formula definitions
- `tools/tune_parameters.py` - Existing simple sweep tool
