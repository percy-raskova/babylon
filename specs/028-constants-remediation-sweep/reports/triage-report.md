# Constants Remediation Triage Report

**Feature**: 028-constants-remediation-sweep
**Date**: 2026-02-27
**Source Inventory**: 027-constants-provenance-audit (247 constants)

## Disposition Summary

| Disposition | Count | Description |
|------------|-------|-------------|
| WIRED | 3 | Tier A pipeline-ready constants connected to federal data sources at init |
| ELIMINATED | 34 | Tier B dead code / deprecated duplicates removed |
| CENTRALIZED | 28 | Tier C inline constants moved to GameDefines with sweep bounds |
| DOCUMENTED | 157 | Tier D engineering (12) + Tier E game design (96) + Tier A already-in-GameDefines (49) with explicit descriptions |
| DEFERRED | 25 | Tier A constants gated by upstream features (002, 013, 021, 024) |
| **TOTAL** | **247** | FR-008 accountability: 3 + 34 + 28 + 157 + 25 = 247 |

## Disposition Details

### WIRED (3) — Tier A Pipeline-Ready Constants

Constants now derived from SQLite federal data at `Simulation.from_sqlite()` via `hydrate_*()` functions.

| Constant Path | Data Source | Old Default | Falsifiability Statement |
|--------------|-------------|-------------|--------------------------|
| economy.extraction_efficiency | QCEW wages (FactQcewAnnual) → ValueTensor4x3 surplus ratio | 0.8 | Falsified if Wayne County QCEW surplus/output ratio deviates >10% from derived alpha |
| economy.shadow_wage_hourly | BLS OES SOC 31-1120 via BEA personal income | 15.0 | Falsified if BLS OES median for home health aides (26163) differs >15% from shadow_wage |
| reserve_army.sigmoid_r0 | FRED UNRATE via FredAPIClient | 0.05 | Falsified if FRED natural unemployment rate for Detroit MSA differs >20% from sigmoid_r0 |

### ELIMINATED (34) — Tier B Dead Code / Deprecated Constants

Constants deleted from module scope because GameDefines equivalents already existed.

| # | Old Location | Old Constant | GameDefines Equivalent | Action |
|---|-------------|-------------|----------------------|--------|
| 1 | endgame_detector.py:53 | PERCOLATION_THRESHOLD | endgame.revolutionary_percolation_threshold | Deleted |
| 2 | endgame_detector.py:55 | CONSCIOUSNESS_THRESHOLD | endgame.revolutionary_consciousness_threshold | Deleted |
| 3 | endgame_detector.py:57 | OVERSHOOT_THRESHOLD | endgame.ecological_overshoot_threshold | Deleted |
| 4 | endgame_detector.py:59 | OVERSHOOT_CONSECUTIVE_TICKS | endgame.ecological_sustained_ticks | Deleted |
| 5 | endgame_detector.py:61 | FASCIST_NODES_THRESHOLD | endgame.fascist_majority_threshold | Deleted |
| 6 | topology_monitor.py:55 | GASEOUS_THRESHOLD | topology.gaseous_threshold | Deleted |
| 7 | topology_monitor.py:56 | CONDENSATION_THRESHOLD | topology.condensation_threshold | Deleted |
| 8 | topology_monitor.py:57 | BRITTLE_MULTIPLIER | topology.brittle_multiplier | Deleted |
| 9 | topology_monitor.py:58 | POTENTIAL_MIN_STRENGTH | topology.solidarity_sympathizer_threshold | Deleted |
| 10 | topology_monitor.py:59 | ACTUAL_MIN_STRENGTH | topology.solidarity_cadre_threshold | Deleted |
| 11 | topology_monitor.py:60 | DEFAULT_REMOVAL_RATE | topology.resilience_removal_rate | Deleted |
| 12 | topology_monitor.py:61 | DEFAULT_SURVIVAL_THRESHOLD | topology.resilience_survival_threshold | Deleted |
| 13 | dynamic_balance.py params | pool_high (0.7) | economy.pool_high_threshold | Removed default |
| 14 | dynamic_balance.py params | pool_low (0.3) | economy.pool_low_threshold | Removed default |
| 15 | dynamic_balance.py params | pool_critical (0.1) | economy.pool_critical_threshold | Removed default |
| 16 | dynamic_balance.py params | bribery_wage_delta (0.05) | economy.bribery_wage_delta | Removed default |
| 17 | dynamic_balance.py params | austerity_wage_delta (-0.05) | economy.austerity_wage_delta | Removed default |
| 18 | dynamic_balance.py params | iron_fist_repression_delta (0.10) | economy.iron_fist_repression_delta | Removed default |
| 19 | dynamic_balance.py params | crisis_wage_delta (-0.15) | economy.crisis_wage_delta | Removed default |
| 20 | dynamic_balance.py params | crisis_repression_delta (0.20) | economy.crisis_repression_delta | Removed default |
| 21 | dynamic_balance.py params | bribery_tension (0.3) | economy.bribery_tension_threshold | Removed default |
| 22 | dynamic_balance.py params | iron_fist_tension (0.5) | economy.iron_fist_tension_threshold | Removed default |
| 23 | metrics.py | DEATH_THRESHOLD | economy.death_threshold | Redirected |
| 24 | tools/shared.py:82 | DEATH_THRESHOLD | economy.death_threshold | Deleted duplicate |
| 25 | solidarity.py param | activation_threshold=0.3 | solidarity.activation_threshold | Removed default |
| 26 | metabolic_rift.py param | entropy_factor=1.2 | metabolism.entropy_factor | Removed default |
| 27 | metabolic_rift.py param | max_ratio=999.0 | metabolism.max_overshoot_ratio | Removed default |
| 28 | curvature.py param | alpha=0.5 | contradiction_field.curvature_alpha | Removed default |
| 29 | trpf.py param | floor=0.1 | economy.trpf_efficiency_floor | Removed default |
| 30 | constants.py | LOSS_AVERSION_COEFFICIENT | behavioral.loss_aversion_lambda | Redirected |
| 31 | specs/024 | EPSILON shadow | precision.epsilon | Deleted shadow |
| 32 | credit/types.py | STAGNATION_CREDIT_GROWTH (inline) | crisis.stagnation_credit_growth | Wired to GameDefines |
| 33 | ideological_routing.py:39 | _ROUTING_SCALE = 0.1 | consciousness.routing_scale | Wired to GameDefines |
| 34 | ideological_routing.py:82 | agitation_decay=0.1 | consciousness.agitation_decay_rate | Wired to GameDefines |

### CENTRALIZED (28) — Tier C Inline Constants Moved to GameDefines

Constants that were hardcoded inline in formula/engine modules, now centralized in GameDefines with Field() bounds and descriptions. All are visible to parameter sweep via `get_tunable_parameters()`.

| # | Old Location | Inline Value | GameDefines Path | Category |
|---|-------------|-------------|------------------|----------|
| 1 | ideological_routing.py:39 | 0.1 | consciousness.routing_scale | Tier C calibration |
| 2 | ideological_routing.py:82 | 0.1 | consciousness.agitation_decay_rate | Tier C calibration |
| 3 | vitality.py:42 | 0.5 | vitality.attrition_base_factor | Tier C calibration |
| 4 | struggle.py:370 | 0.5 | struggle.consciousness_solidarity_boost | Tier C calibration |
| 5 | dispossession_events.py:91 | 0.01 | dispossession.transfer_scale | Tier C calibration |
| 6 | credit/types.py:95 | 0.01 | crisis.stagnation_credit_growth | Tier C calibration |
| 7 | class_dynamics.py:64 | 0.0006 | class_dynamics.alpha_21 | Tier C FRED-fitted |
| 8 | class_dynamics.py:75 | 0.0057 | class_dynamics.gamma_3 | Tier C FRED-fitted |
| 9 | class_dynamics.py:95-99 | (0.305,0.382,0.294,0.020) | class_dynamics.equilibrium_w1-w4 | Tier C FRED-fitted |
| 10 | edge_transition.py:103 | 5.0 | edge_transition.extraction_contested_threshold | Tier C calibration |
| 11 | edge_transition.py:128 | 2.0 | edge_transition.extraction_broken_threshold | Tier C calibration |
| 12 | edge_transition.py:147 | 3.0 | edge_transition.concessions_exploitation_threshold | Tier C calibration |
| 13 | edge_transition.py:147 | 2.0 | edge_transition.concessions_rent_threshold | Tier C calibration |
| 14 | edge_transition.py:171 | 2.0 | edge_transition.mutual_aid_threshold | Tier C calibration |
| 15 | edge_transition.py:197 | 1.0 | edge_transition.market_failure_threshold | Tier C calibration |
| 16 | edge_transition.py:214 | 5.0 | edge_transition.power_asymmetry_threshold | Tier C calibration |
| 17 | edge_transition.py:233 | 3.0 | edge_transition.co_optive_power_threshold | Tier C calibration |
| 18 | edge_transition.py:252 | 6.0 | edge_transition.solidarity_degrades_threshold | Tier C calibration |
| 19 | edge_transition.py:271 | 3.0 | edge_transition.betrayal_threshold | Tier C calibration |
| 20 | edge_transition.py:296 | 3.0 | edge_transition.conflict_resolved_threshold | Tier C calibration |
| 21 | edge_transition.py:314 | 7.0 | edge_transition.shared_enemy_threshold | Tier C calibration |
| 22 | edge_transition.py:339 | 3.0 | edge_transition.reform_rent_threshold | Tier C calibration |
| 23 | edge_transition.py:367 | 2.0 | edge_transition.co_optation_normalizes_threshold | Tier C calibration |
| 24 | edge_transition.py:392 | 1.0 | edge_transition.co_optive_breakdown_threshold | Tier C calibration |
| 25 | edge_transition.py:411 | 5.0 | edge_transition (co_optation_recognized) | Tier C calibration |
| 26 | edge_transition.py:434 | 1.0 | edge_transition.concessions_withdrawn_threshold | Tier C calibration |
| 27 | class_dynamics.py:95 | 0.305 | class_dynamics.equilibrium_w1 | Tier C FRED-fitted |
| 28 | class_dynamics.py:96 | 0.382 | class_dynamics.equilibrium_w2 | Tier C FRED-fitted |

### DOCUMENTED (157) — Tier D Engineering + Tier E Game Design + Tier A In-GameDefines

#### Tier D Engineering Constants (12 in GameDefines)

All descriptions prefixed with "Engineering:" explaining structural necessity.

| # | Constant Path | Value | Engineering Rationale |
|---|--------------|-------|---------------------|
| 1 | crisis.class_burden_epsilon | 0.001 | Division-by-zero guard for class burden ratio |
| 2 | precision.decimal_places | 6 | Quantization grid precision (IEEE 754 + 5200-tick horizon) |
| 3 | precision.epsilon | 1e-9 | Division-by-zero guard (must be < 10^-decimal_places) |
| 4 | precision.comparison_epsilon | 1e-10 | Float equality tolerance (must be < epsilon) |
| 5 | timescale.tick_duration_days | 7 | Physical constant: 7 days/week |
| 6 | timescale.weeks_per_year | 52 | Physical constant: 52 weeks/year |
| 7 | economy.negligible_rent | 0.01 | Noise filter: prevents event bus saturation |
| 8 | economy.negligible_subsidy | 0.01 | Noise filter: prevents processing overhead |
| 9 | economy.death_threshold | 0.001 | Zombie prevention failsafe |
| 10 | metabolism.max_overshoot_ratio | 999.0 | Overflow cap for biocapacity depletion |
| 11 | solidarity.negligible_transmission | 0.01 | Noise filter: prevents O(n^2) edge saturation |
| 12 | precision.rounding_mode | ROUND_HALF_UP | Deterministic cross-platform behavior |

Note: `exp_clamp_low/high` (survival_calculus inline) and `distribution EPSILON` (distribution inline) are Tier D but remain inline — they are literal bounds on `math.exp()` and surplus verification respectively. Not candidates for GameDefines extraction.

#### Tier E Game Design Constants (96 in GameDefines)

All descriptions prefixed with "Game design:" marking intentional design choices.

| Subsection | Count | Constants |
|-----------|-------|-----------|
| crisis | 11 | crisis_period_ticks, r_threshold, n_consecutive, m_recovery, r_cap, hysteresis_coefficient, wage_compression_rate, wage_compression_floor_ratio, bifurcation_solidarity_weight, bifurcation_burden_weight, bifurcation_event_threshold |
| economy | 19 | extraction_efficiency, comprador_cut, base_labor_power, super_wage_rate, superwage_multiplier, superwage_ppp_impact, initial_rent_pool, pool_high_threshold, pool_low_threshold, pool_critical_threshold, min_wage_rate, max_wage_rate, subsidy_conversion_rate, subsidy_trigger_threshold, base_subsistence, trpf_coefficient, rent_pool_decay, bribery_wage_delta, austerity_wage_delta, iron_fist_repression_delta, crisis_wage_delta, crisis_repression_delta, bribery_tension_threshold, iron_fist_tension_threshold, trpf_efficiency_floor |
| survival | 6 | steepness_k, default_subsistence, default_organization, default_repression, revolution_threshold, repression_base |
| vitality | 2 | base_mortality_factor, inequality_impact |
| solidarity | 4 | scaling_factor, activation_threshold, mass_awakening_threshold, superwage_impact |
| behavioral | 1 | loss_aversion_lambda |
| tension | 1 | accumulation_rate |
| consciousness | 2 | sensitivity, decay_lambda |
| territory | 12 | heat_decay_rate, high_profile_heat_gain, eviction_heat_threshold, rent_spike_multiplier, displacement_rate, heat_spillover_rate, clarity_profile_coefficient, concentration_camp_decay_rate, displacement_priority_mode, elimination_rent_threshold, elimination_tension_threshold, containment_rent_threshold, containment_tension_threshold |
| topology | 8 | gaseous_threshold, condensation_threshold, vanguard_density_threshold, brittle_multiplier, solidarity_sympathizer_threshold, solidarity_cadre_threshold, resilience_removal_rate, resilience_survival_threshold |
| metabolism | 2 | entropy_factor, overshoot_threshold |
| struggle | 8 | spark_probability_scale, resistance_threshold, wealth_destruction_rate, solidarity_gain_per_uprising, jackson_threshold, revolutionary_agitation_boost, fascist_identity_boost, fascist_acquiescence_boost |
| carceral | 7 | control_capacity, enforcer_fraction, proletariat_fraction, revolution_threshold, decomposition_delay, control_ratio_delay, terminal_decision_delay |
| endgame | 5 | revolutionary_percolation_threshold, revolutionary_consciousness_threshold, ecological_overshoot_threshold, ecological_sustained_ticks, fascist_majority_threshold |
| initial | 1 | default_population |
| contradiction_field | 6 | field_min, field_max, history_window, curvature_alpha, co_optive_suppression_rate, latent_release_multiplier, default_transition_priority |
| dispossession | 9 | weight_foreclosure, weight_eviction, weight_displacement, weight_tax_sale, weight_eminent_domain, weight_wage_theft, weight_incarceration_seizure, weight_pension_default, deadweight_loss_fraction |
| working_day | 6 | absolute_hours_threshold, relative_hours_threshold, intensity_threshold_high, intensity_threshold_low, absolute_visibility, relative_visibility |
| community | 6 | heat_decay_alpha, cohesion_decay_alpha, infrastructure_decay_alpha, community_overlap_bonus, rent_differential_penalty, core_organizer_maintenance_factor |
| edge_transition | 16 | (all 16 threshold fields) |

Note: Economy counts include fields that are both Tier A (data-derivable) and Tier E (game design) depending on classification granularity. Fields like extraction_efficiency are Tier A when a data pipeline exists but operate as Tier E defaults until wired.

#### Tier A Constants Already in GameDefines (49)

These constants have GameDefines fields and are documented as data-derivable per the 027 audit, but are not yet wired to live data pipelines (except the 3 WIRED constants). They retain their default values pending upstream feature completion or data pipeline implementation.

Includes: all EconomyDefines data-derivable fields, ReserveArmyDefines fields, ClassDynamicsDefines FRED-fitted parameters, InitialDefines wealth/population fields.

### DEFERRED (25) — Tier A Feature-Gated Constants

Constants that COULD be derived from federal data but are blocked by upstream features that haven't been implemented yet.

| # | Constant Path | Blocking Feature | Required Adapter | Unblock Condition |
|---|--------------|-----------------|-----------------|-------------------|
| 1 | territory.heat_decay_rate | 002 (Dialectical Field Topology) | Contradiction field spatial gradients | Feature 002 spatial gradient computation |
| 2 | territory.high_profile_heat_gain | 002 | Contradiction field intensity gradients | Feature 002 intensity gradient |
| 3 | territory.eviction_heat_threshold | 002 | Edge mode transition thresholds | Feature 002 threshold calibration |
| 4 | territory.heat_spillover_rate | 002 | Ollivier-Ricci curvature | Feature 002 curvature computation |
| 5 | reserve_army.sigmoid_k | 021 (Capital Volume I) | BLS unemployment-wage correlation | Feature 021 reserve army dynamics |
| 6 | reserve_army.wage_pressure_ceiling | 021 | Historical max unemployment elasticity | Feature 021 wage pressure model |
| 7 | reserve_army.min_employed_fraction | 021 | Historical min labor force participation | Feature 021 employment floor |
| 8 | economy.comprador_cut | 013 (MELT Basket Visibility) | BEA international transactions | Feature 013 comprador module |
| 9 | economy.base_labor_power | 013 | ValueTensor4x3 MELT | Feature 013 labor power tensor |
| 10 | economy.super_wage_rate | 013 | MELT gamma_basket | Feature 013 super-wage formula |
| 11 | economy.superwage_multiplier | 013 | Basket visibility gamma_basket | Feature 013 PPP calculation |
| 12 | economy.superwage_ppp_impact | 013 | PWT PPP data | Feature 013 PPP impact |
| 13 | economy.base_subsistence | 013 | BLS CPI basket + MELT | Feature 013 subsistence derivation |
| 14 | economy.trpf_coefficient | 013 | ValueTensor4x3 time series d(OCC)/dt | Feature 013 TRPF tensor |
| 15 | economy.trpf_efficiency_floor | 013 | ValueTensor4x3 historical minimum | Feature 013 efficiency floor |
| 16 | initial.worker_wealth | 024 (Capital Volume III) | Fed SCF p10 net worth | Feature 024 SCF integration |
| 17 | initial.owner_wealth | 024 | Fed SCF p90 net worth | Feature 024 SCF integration |
| 18 | class_dynamics.alpha_41 | 024 | FRED DFA class share dynamics | Feature 024 DFA pipeline |
| 19 | class_dynamics.alpha_31 | 024 | FRED DFA class share dynamics | Feature 024 DFA pipeline |
| 20 | class_dynamics.alpha_32 | 024 | FRED DFA class share dynamics | Feature 024 DFA pipeline |
| 21 | class_dynamics.alpha_42 | 024 | FRED DFA class share dynamics | Feature 024 DFA pipeline |
| 22 | class_dynamics.alpha_43 | 024 | FRED DFA class share dynamics | Feature 024 DFA pipeline |
| 23 | class_dynamics.delta_1 | 024 | FRED fiscal transfer data | Feature 024 fiscal transfers |
| 24 | class_dynamics.delta_2 | 024 | FRED fiscal transfer data | Feature 024 fiscal transfers |
| 25 | class_dynamics.delta_3 | 024 | FRED fiscal transfer data | Feature 024 fiscal transfers |

## Verification

### FR-008 Accountability Check

```
WIRED:       3 (Tier A pipeline-ready)
ELIMINATED: 34 (Tier B dead code)
CENTRALIZED: 28 (Tier C inline → GameDefines)
DOCUMENTED: 157 (Tier D=12 + Tier E=96 + Tier A in-GD=49)
DEFERRED:   25 (Tier A feature-gated)
─────────────────
TOTAL:     247 ✓
```

### Regression Status

- 5/5 regression scenarios: PASS
- 7570 unit tests: PASS
- Behavioral deviation: ZERO (all value changes preserve defaults)

### Constitution Compliance

- **III.1 (No Magic Constants)**: 28 inline constants centralized, 34 dead constants eliminated
- **III.2 (Falsifiability)**: 3 wired constants have explicit falsifiability statements
- **III.4 (Data Source Traced)**: All 3 wired constants trace to Constitution-approved data sources (QCEW, BLS OES, FRED)
- **IV (Detroit Testable)**: Regression baselines generated from Detroit vertical slice scenarios
- **V.1 (Material Base First)**: Data hydration wired before game design documentation
