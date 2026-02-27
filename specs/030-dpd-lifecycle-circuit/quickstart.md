# Quickstart: D-P-D' Lifecycle Circuit Integration Tests

**Feature**: 030-dpd-lifecycle-circuit | **Date**: 2026-02-27

## Overview

These scenarios define end-to-end integration tests for the LifecycleSystem. Each scenario is independently executable and maps to a user story from the specification.

## Scenario 1: Basic Population Flow (US1)

**Goal**: Verify cohort transitions conserve population.

**Setup**:
```
County: FIPS "99001"
Initial: pop_D=2150, pop_P=6050, pop_D_prime=1800 (total=10000)
Rates: birth=0.0107, D→P=0.0556, P→D'=0.0213, D'→death=0.039
```

**Run**: 1 tick of LifecycleSystem

**Verify**:
- Births ≈ 0.0107 × 6050 ≈ 64.7
- D→P flow ≈ 0.0556 × 2150 ≈ 119.5
- P→D' flow ≈ 0.0213 × 6050 ≈ 128.9
- Deaths ≈ 0.039 × 1800 ≈ 70.2
- Population conservation: |total[t1] - total[t0] - births + deaths| / total[t0] < 0.001
- All populations non-negative

## Scenario 2: Legitimation Index Computation (US2)

**Goal**: Verify weighted legitimation index and crisis classification.

**Setup**:
```
County: FIPS "99002"
Legitimation components:
  pension_coverage = 0.73
  ss_replacement = 0.43
  healthcare_security = 0.60
  home_ownership = 0.66
  retirement_confidence = 0.50
```

**Run**: Compute legitimation index

**Verify**:
- Index = 0.25×0.73 + 0.25×0.43 + 0.25×0.60 + 0.15×0.66 + 0.10×0.50
- Index = 0.1825 + 0.1075 + 0.15 + 0.099 + 0.05 = 0.589
- Classification = "STABLE" (>= 0.5)

**Degradation Test**:
```
Set all components to 0.2:
  Index = 0.25×0.2 + 0.25×0.2 + 0.25×0.2 + 0.15×0.2 + 0.10×0.2 = 0.2
  Classification = "CRISIS" (< 0.3)
```

## Scenario 3: Inheritance with Pareto Distribution (US3)

**Goal**: Verify Pareto-distributed inheritance at D' terminus.

**Setup**:
```
County: FIPS "99003"
D' population: 1000 familial units
D' aggregate wealth: Currency(10_000_000)
Deaths this tick: 39 (3.9% mortality)
Care cost fraction: 0.4
Pareto alpha: 1.5
```

**Run**: Compute inheritance flow

**Verify**:
- Wealth of dying cohort ≈ 39/1000 × 10_000_000 = 390_000
- Care consumed ≈ 0.4 × 390_000 = 156_000
- Net inheritance ≈ 390_000 - 156_000 = 234_000
- Gini(inheritance) computed from Pareto(α=1.5) ≈ 1/(2×1.5 - 1) = 0.5
- Verify SC-003: inheritance_gini > income_gini for same county

## Scenario 4: Legitimation → Bifurcation Feed (US4)

**Goal**: Verify legitimation index propagates to bifurcation risk metric.

**Setup**:
```
County: FIPS "99004"
Legitimation index: 0.25 (CRISIS)
Existing agitation: 0.6
Blend weight (w): 0.6
```

**Run**: Compute blended legitimation for bifurcation

**Verify**:
- Structural index = 0.25
- Agitation inverse = 1 - 0.6 = 0.4
- Blended = 0.6 × 0.25 + 0.4 × 0.4 = 0.15 + 0.16 = 0.31
- This low legitimation should amplify bifurcation risk
- Dampening: raw_risk × (1.0 - 0.31) = raw_risk × 0.69

## Scenario 5: Differential Transition Rates (US5)

**Goal**: Verify racial/carceral modifiers affect transition rates.

**Setup**:
```
County: FIPS "99005"
Base rate_P_to_D_prime: 0.0213
Black early_mortality_modifier: 1.24
Black carceral_modifier: 2.8 (affects P→D' via incarceration)
```

**Run**: Compute differential rates

**Verify**:
- Black P→D' rate > White P→D' rate
- Black rate includes carceral premature exit from P phase
- Ratio of Black/White P→D' approximately reflects Chetty mortality gap
- Over 10 ticks, Black pop_P depletes faster than White pop_P (SC-008)

## Scenario 6: Ideology Transmission at D→P (US6)

**Goal**: Verify ideology blending during lifecycle phase transition.

**Setup**:
```
County: FIPS "99006"
Caregiver ideology (D phase): 0.3 (moderate consciousness)
Institutional hegemony: 0.8 (strong hegemonic pressure)
Caregiver weight: 0.7
Institutional weight: 0.3
```

**Run**: Compute P-phase entry ideology

**Verify**:
- Transmitted ideology = 0.7 × 0.3 + 0.3 × 0.8 = 0.21 + 0.24 = 0.45
- Workers entering P phase start with ideology ≈ 0.45
- This is between caregiver influence and institutional hegemony
- Over multiple generations, the blend should drift toward hegemony if no organizing occurs

## Scenario 7: Dual Circuit Interference (US7)

**Goal**: Verify resource competition between D-P-D' and P-D-P' circuits.

**Setup**:
```
County: FIPS "99007"
P-phase worker with:
  wage = Currency(50_000)
  D' parent care cost = Currency(15_000)
  D child investment = Currency(12_000)
  subsistence = Currency(30_000)
Legitimation index: 0.35 (UNSTABLE)
```

**Run**: Compute sandwich squeeze and resource competition

**Verify**:
- Total demands on P worker = 30_000 + 15_000 + 12_000 = 57_000
- Wage shortfall = 50_000 - 57_000 = -7_000 (squeeze active)
- Low legitimation → worker prioritizes self over D' (SC-011)
- Shadow subsidy = value of P_g2 labor-power - wages paid to P_g1 for D_g2 investment > 0 (SC-014)

## Scenario 8: Multi-Tick Steady State (Integration)

**Goal**: Verify system reaches demographic steady state over many ticks.

**Setup**:
```
County: FIPS "99008"
Initial: Default population distribution from LifecycleDefines
All rates at defaults
No external shocks
```

**Run**: 100 ticks

**Verify**:
- Population proportions converge to a steady state (FR-014)
- Dependency ratio stabilizes (not monotonically increasing or decreasing)
- Legitimation index is stable if no economic shocks
- No population goes negative at any tick
- Conservation holds at every tick (cumulative drift < 1%)

## Scenario 9: Dispossession Short-Circuit (US7)

**Goal**: Verify dispossession event affects both circuits simultaneously.

**Setup**:
```
County: FIPS "99009"
P-phase household:
  home_equity = Currency(200_000)
  dispossession_event = True (foreclosure)
```

**Run**: Apply dispossession, then compute dual circuit effects

**Verify**:
- D-P-D' effect: D' security reduced (home_ownership_rate decreases)
- P-D-P' effect: Inheritance pathway severed (home equity transferred to capital)
- Both effects from single dispossession event (SC-012)
- Legitimation index decreases after dispossession
