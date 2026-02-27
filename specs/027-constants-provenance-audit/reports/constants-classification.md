# Constants Classification Report

**Feature**: 027-constants-provenance-audit
**Date**: 2026-02-27
**Classification order**: A (Tensor-Derivable) -> B (Eliminable) -> D (Engineering/Precision) -> E (Game Design Knob) -> C (Calibration, catch-all)

## Summary Statistics

| Tier | Count | Description |
|------|-------|-------------|
| A | 37 | Tensor-Derivable |
| B | 34 | Eliminable |
| C | 63 | Calibration Parameter |
| D | 14 | Engineering/Precision |
| E | 99 | Game Design Knob |
| **Total** | **247** | |

### Tier Distribution by Source Type

| Source Type | A | B | C | D | E | Total |
|-------------|---|---|---|---|---|-------|
| GameDefines | 20 | 0 | 51 | 11 | 54 | 136 |
| FormulaConstant | 0 | 2 | 0 | 0 | 0 | 2 |
| InlineLiteral | 17 | 32 | 12 | 3 | 45 | 109 |
| **Total** | **37** | **34** | **63** | **14** | **99** | **247** |

---

## Tier A: Tensor-Derivable (37 constants)

Constants derivable from existing or planned infrastructure: ValueTensor4x3, MELT calculator, ClassPosition classifier, Feature 002 dialectical field topology, Feature 021 Capital Volume I, or FRED-fitted coefficients with documented data provenance.

### economy.extraction_efficiency -- Alpha extraction rate from periphery
- **Current value**: 0.8
- **Derivation**: `exploitation_rate = total_s / total_v` from ValueTensor4x3; alpha represents the efficiency with which surplus is extracted, derivable from BEA industry-level value-added vs. compensation ratios
- **Infrastructure**: Available -- ValueTensor4x3, MarxianHydrator, TensorRegistry
- **Data source**: QCEW county wages -> BEA industry ratios -> tensor pipeline

### economy.comprador_cut -- Fraction of wealth kept by comprador class
- **Current value**: 0.9
- **Derivation**: From BEA international transactions: `retained_earnings / total_income` for comprador-class nations; derivable from BEA + World Bank data
- **Infrastructure**: Partial -- MarxianHydrator, ValueTensor4x3.imperial_rent | Gap: BEA international adapter
- **Data source**: BEA International Transactions -> retained earnings ratio

### economy.base_labor_power -- Base value produced per tick by full-biocapacity worker
- **Current value**: 1.0
- **Derivation**: `total_v / total_labor_hours` from ValueTensor4x3 monetized via MELT
- **Infrastructure**: Available -- ValueTensor4x3.monetized_v, DefaultMELTCalculator.get_melt
- **Data source**: QCEW employment -> BEA GDP -> MELT tau -> per-worker value

### economy.super_wage_rate -- Fraction of tribute paid as super-wages
- **Current value**: 0.2
- **Derivation**: `tau_effective / tau_domestic` from MELT calculator; super-wage rate is the fraction of imperial rent recycled as labor aristocracy wages, derivable from PPP-adjusted wage differentials
- **Infrastructure**: Available -- DefaultMELTCalculator, gamma visibility pipeline
- **Data source**: BEA GDP + BLS QCEW wages -> MELT -> tau ratio

### economy.superwage_multiplier -- PPP multiplier for labor aristocracy purchasing power
- **Current value**: 1.0
- **Derivation**: `1 / gamma_basket` from basket visibility calculator; PPP multiplier representing purchasing power amplification
- **Infrastructure**: Available -- basket_visibility.py, Gamma Visibility Tensor
- **Data source**: PWT (Penn World Table) PPP data -> gamma_import -> gamma_basket

### economy.superwage_ppp_impact -- How much extraction translates to PPP bonus
- **Current value**: 0.5
- **Derivation**: Regression coefficient from ERDI (Exchange Rate Deviation Index) vs. import share; derivable from PWT + Census Trade data
- **Infrastructure**: Partial -- Gamma visibility (`economics/gamma/`) | Gap: regression step not automated
- **Data source**: PWT PPP ratios, Census Trade import data

### economy.shadow_wage_hourly -- Shadow labor hourly rate (BLS 31-1120)
- **Current value**: 15.43
- **Derivation**: Direct lookup from BLS OES data (SOC 31-1120, home health aide median May 2023)
- **Infrastructure**: Available -- ATUSDBLoader.get_shadow_wage already reads this
- **Data source**: BLS Occupational Employment and Wage Statistics (OES)

### economy.base_subsistence -- Biological floor cost per tick
- **Current value**: 0.0005
- **Derivation**: `subsistence_basket / tau / weeks_per_year`; computable from CPI market basket + MELT
- **Infrastructure**: Partial -- MELT calculator available | Gap: CPI basket adapter not yet built
- **Data source**: BLS CPI market basket -> MELT conversion -> per-tick cost

### economy.trpf_coefficient -- TRPF extraction decline rate per tick
- **Current value**: 0.0005
- **Derivation**: `d(OCC)/dt` from ValueTensor4x3 time series; TRPF coefficient tracks the rate of organic composition increase
- **Infrastructure**: Partial -- ValueTensor4x3 (OCC field), TensorRegistry | Gap: time-series delta computation
- **Data source**: BEA fixed assets + QCEW employment -> OCC -> temporal derivative

### economy.trpf_efficiency_floor -- Minimum extraction efficiency after TRPF decay
- **Current value**: 0.1
- **Derivation**: Historical minimum profit rate from ValueTensor4x3 time series
- **Infrastructure**: Partial -- ValueTensor4x3.profit_rate | Gap: historical minimum aggregation
- **Data source**: BEA historical data -> minimum observed profit rate

### initial.worker_wealth -- Starting wealth for periphery worker
- **Current value**: 0.5
- **Derivation**: `Fed_SCF_p10_net_worth / tau`; 10th percentile net worth from Fed SCF normalized by MELT
- **Infrastructure**: Partial -- ClassPositionClassifier exists | Gap: SCF data ingestion
- **Data source**: Federal Reserve Survey of Consumer Finances (SCF)

### initial.owner_wealth -- Starting wealth for core owner
- **Current value**: 0.5
- **Derivation**: `Fed_SCF_p90_net_worth / tau`; 90th percentile net worth normalized by MELT
- **Infrastructure**: Partial -- ClassPositionClassifier exists | Gap: SCF data ingestion
- **Data source**: Federal Reserve Survey of Consumer Finances (SCF)

### territory.heat_decay_rate -- Heat decay for LOW_PROFILE territories
- **Current value**: 0.1
- **Derivation**: Derivable from Feature 002 contradiction field spatial gradients; heat decay = f(Ollivier-Ricci curvature, operational profile)
- **Infrastructure**: Planned -- ContradictionFieldSystem, curvature.py (Feature 002)
- **Data source**: Eviction Lab -> ATTOM/CoreLogic -> Detroit carceral geography -> empirical decay

### territory.high_profile_heat_gain -- Heat gain for HIGH_PROFILE territories
- **Current value**: 0.15
- **Derivation**: Derivable from Feature 002 dialectical field topology intensity gradients
- **Infrastructure**: Planned -- ContradictionFieldDefines, contradiction field spatial gradients
- **Data source**: CDC WONDER mortality -> BJS incarceration -> heat accumulation profiles

### territory.eviction_heat_threshold -- Heat threshold for eviction pipeline
- **Current value**: 0.8
- **Derivation**: Derivable from Feature 002 edge mode transition thresholds via empirical calibration
- **Infrastructure**: Planned -- ContradictionFieldSystem phase transitions
- **Data source**: Eviction Lab filing rates -> ATTOM foreclosure -> threshold calibration

### territory.heat_spillover_rate -- Heat spillover via ADJACENCY edges
- **Current value**: 0.05
- **Derivation**: Derivable from Feature 002 Ollivier-Ricci curvature and spatial diffusion
- **Infrastructure**: Planned -- curvature.py Ollivier-Ricci, ContradictionFieldDefines.curvature_alpha
- **Data source**: Census tract adjacency -> Eviction Lab spatial correlation -> spillover rate

### reserve_army.sigmoid_k -- Sigmoid steepness for wage pressure
- **Current value**: 20.0
- **Derivation**: Derivable from Feature 021 reserve army dynamics fitted to BLS unemployment-wage correlation
- **Infrastructure**: Planned -- Feature 021 Capital Volume I, BLS data
- **Data source**: BLS LAUS -> unemployment rate -> wage growth correlation -> sigmoid fit

### reserve_army.sigmoid_r0 -- Reserve ratio at sigmoid midpoint
- **Current value**: 0.08
- **Derivation**: Natural rate of unemployment from BLS; inflection point calibrated to NAIRU
- **Infrastructure**: Available -- existing FredAPIClient (FRED series NROU)
- **Data source**: FRED NROU (Non-Accelerating Inflation Rate of Unemployment)

### reserve_army.wage_pressure_ceiling -- Maximum wage pressure coefficient
- **Current value**: 0.5
- **Derivation**: Historical maximum unemployment-to-wage elasticity from BLS employment/wage time series
- **Infrastructure**: Partial -- FredAPIClient, QCEW | Gap: elasticity regression
- **Data source**: FRED unemployment rate + QCEW average weekly wages

### reserve_army.min_employed_fraction -- Minimum employed fraction
- **Current value**: 0.01
- **Derivation**: Historical minimum labor force participation from BLS
- **Infrastructure**: Available -- FredAPIClient (FRED series CIVPART)
- **Data source**: FRED CIVPART (Civilian Labor Force Participation Rate)

### class_dynamics:58:alpha_41 -- Extraction rate: proletariat to bourgeoisie
- **Current value**: 0.0
- **Derivation**: FRED-fitted ODE coefficient with documented data provenance
- **Infrastructure**: Available -- class_dynamics.py ClassDynamicsParams (FRED-fitted)
- **Data source**: FRED GDP components -> class share time series -> ODE parameter estimation

### class_dynamics:59:alpha_31 -- Extraction rate: LA to bourgeoisie
- **Current value**: 0.0
- **Derivation**: FRED-fitted ODE coefficient
- **Infrastructure**: Available -- class_dynamics.py ClassDynamicsParams (FRED-fitted)
- **Data source**: FRED -> class share dynamics -> ODE fit

### class_dynamics:60:alpha_21 -- Extraction rate: petty bourgeoisie to bourgeoisie
- **Current value**: 0.0006
- **Derivation**: FRED-fitted ODE coefficient
- **Infrastructure**: Available -- class_dynamics.py ClassDynamicsParams (FRED-fitted)
- **Data source**: FRED -> class share dynamics -> ODE fit

### class_dynamics:61:alpha_32 -- Extraction rate: LA to petty bourgeoisie
- **Current value**: 0.0
- **Derivation**: FRED-fitted ODE coefficient
- **Infrastructure**: Available -- class_dynamics.py ClassDynamicsParams (FRED-fitted)
- **Data source**: FRED -> class share dynamics -> ODE fit

### class_dynamics:62:alpha_42 -- Extraction rate: proletariat to petty bourgeoisie
- **Current value**: 0.0
- **Derivation**: FRED-fitted ODE coefficient
- **Infrastructure**: Available -- class_dynamics.py ClassDynamicsParams (FRED-fitted)
- **Data source**: FRED -> class share dynamics -> ODE fit

### class_dynamics:63:alpha_43 -- Extraction rate: proletariat to LA
- **Current value**: 0.0
- **Derivation**: FRED-fitted ODE coefficient
- **Infrastructure**: Available -- class_dynamics.py ClassDynamicsParams (FRED-fitted)
- **Data source**: FRED -> class share dynamics -> ODE fit

### class_dynamics:66:delta_1 -- Redistribution rate from bourgeoisie
- **Current value**: 0.001
- **Derivation**: FRED-fitted ODE coefficient for fiscal transfer flows
- **Infrastructure**: Available -- class_dynamics.py ClassDynamicsParams (FRED-fitted)
- **Data source**: FRED -> fiscal transfer data -> redistribution rates

### class_dynamics:67:delta_2 -- Redistribution rate from petty bourgeoisie
- **Current value**: 0.002
- **Derivation**: FRED-fitted ODE coefficient
- **Infrastructure**: Available -- class_dynamics.py ClassDynamicsParams (FRED-fitted)
- **Data source**: FRED -> fiscal transfer data -> redistribution rates

### class_dynamics:68:delta_3 -- Redistribution rate from labor aristocracy
- **Current value**: 0.001
- **Derivation**: FRED-fitted ODE coefficient
- **Infrastructure**: Available -- class_dynamics.py ClassDynamicsParams (FRED-fitted)
- **Data source**: FRED -> fiscal transfer data -> redistribution rates

### class_dynamics:71:gamma_3 -- Imperial rent formation rate quarterly
- **Current value**: 0.0057
- **Derivation**: FRED-fitted ODE coefficient for quarterly imperial rent formation
- **Infrastructure**: Available -- class_dynamics.py ClassDynamicsParams (FRED-fitted)
- **Data source**: FRED -> BEA trade balance -> imperial rent formation rate

### tick_init:32:share_bourgeoisie -- Default bourgeoisie class share
- **Current value**: 0.01
- **Derivation**: Fed SCF top 1% wealth share -> class share via ClassPositionClassifier
- **Infrastructure**: Available -- DefaultClassPositionClassifier.classify_distribution
- **Data source**: Federal Reserve SCF + Census ACS

### tick_init:33:share_petit_b -- Default petit bourgeoisie class share
- **Current value**: 0.09
- **Derivation**: Fed SCF 90th-99th percentile -> petty bourgeoisie share
- **Infrastructure**: Available -- DefaultClassPositionClassifier.classify_distribution
- **Data source**: Federal Reserve SCF

### tick_init:34:share_la -- Default labor aristocracy class share
- **Current value**: 0.4
- **Derivation**: Fed SCF 50th-90th percentile -> labor aristocracy share, cross-ref QCEW wage data
- **Infrastructure**: Available -- DefaultClassPositionClassifier.classify_distribution, QCEW
- **Data source**: Federal Reserve SCF + QCEW

### tick_init:35:share_proletariat -- Default proletariat class share
- **Current value**: 0.35
- **Derivation**: Fed SCF 10th-50th percentile -> proletariat share
- **Infrastructure**: Available -- DefaultClassPositionClassifier.classify_distribution
- **Data source**: Federal Reserve SCF

### tick_init:36:share_lumpen -- Default lumpenproletariat class share
- **Current value**: 0.15
- **Derivation**: Fed SCF below 10th percentile + BJS incarceration data -> lumpenproletariat share
- **Infrastructure**: Partial -- DefaultClassPositionClassifier | Gap: BJS adapter
- **Data source**: Federal Reserve SCF + Bureau of Justice Statistics

### tick_init:39:unemployment_rate -- Default unemployment rate
- **Current value**: 0.05
- **Derivation**: BLS current unemployment rate (U-3 measure)
- **Infrastructure**: Available -- existing FredAPIClient (FRED series UNRATE)
- **Data source**: FRED UNRATE (Civilian Unemployment Rate)

### tick_init:43:median_wage -- Default median wage ($/hr)
- **Current value**: 21.0
- **Derivation**: BLS median usual weekly earnings / 40; direct from Current Population Survey
- **Infrastructure**: Available -- FredAPIClient (FRED series LEU0252881600A)
- **Data source**: BLS Current Population Survey / FRED median wage series

---

## Tier B: Eliminable (34 constants)

Constants with zero active consumers (dead code) or deprecated duplicates of GameDefines values that should be consolidated or removed.

### formulas.LOSS_AVERSION_COEFFICIENT -- Re-exported duplicate of behavioral.loss_aversion_lambda
- **Reason**: Deprecated duplicate (re-exports 2.25, identical to `behavioral.loss_aversion_lambda`)
- **Active consumers**: 3 (but all accept GameDefines injection; re-export unnecessary)
- **Deprecated consumers**: 0
- **Action**: Consumers should read from GameDefines directly

### formulas.EPSILON -- Re-exported duplicate of precision.epsilon
- **Reason**: Deprecated duplicate (re-exports 1e-9, identical to `precision.epsilon`)
- **Active consumers**: 1
- **Deprecated consumers**: 0
- **Action**: Consumer should read from GameDefines

### dynamic_balance:28:high_threshold -- Fallback default duplicating economy.pool_high_threshold
- **Reason**: Deprecated duplicate (fallback default = 0.7, GameDefines = 0.7)
- **Active consumers**: 0 (parameter default only; overridden by GameDefines injection in all callers)
- **Deprecated consumers**: 0

### dynamic_balance:29:low_threshold -- Fallback default duplicating economy.pool_low_threshold
- **Reason**: Deprecated duplicate (fallback default = 0.3, GameDefines = 0.3)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### dynamic_balance:30:critical_threshold -- Fallback default duplicating economy.pool_critical_threshold
- **Reason**: Deprecated duplicate (fallback default = 0.1, GameDefines = 0.1)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### dynamic_balance:32:bribery_delta -- Fallback default duplicating economy.bribery_wage_delta
- **Reason**: Deprecated duplicate (fallback default = 0.05, GameDefines = 0.05)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### dynamic_balance:33:austerity_delta -- Fallback default duplicating economy.austerity_wage_delta
- **Reason**: Deprecated duplicate (fallback default = -0.05, GameDefines = -0.05)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### dynamic_balance:34:iron_fist_delta -- Fallback default duplicating economy.iron_fist_repression_delta
- **Reason**: Deprecated duplicate (fallback default = 0.1, GameDefines = 0.1)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### dynamic_balance:35:crisis_wage_delta -- Fallback default duplicating economy.crisis_wage_delta
- **Reason**: Deprecated duplicate (fallback default = -0.15, GameDefines = -0.15)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### dynamic_balance:36:crisis_repr_delta -- Fallback default duplicating economy.crisis_repression_delta
- **Reason**: Deprecated duplicate (fallback default = 0.2, GameDefines = 0.2)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### dynamic_balance:38:bribery_tension -- Fallback default duplicating economy.bribery_tension_threshold
- **Reason**: Deprecated duplicate (fallback default = 0.3, GameDefines = 0.3)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### dynamic_balance:39:iron_fist_tension -- Fallback default duplicating economy.iron_fist_tension_threshold
- **Reason**: Deprecated duplicate (fallback default = 0.5, GameDefines = 0.5)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### solidarity:14:activation_default -- Fallback default duplicating solidarity.activation_threshold
- **Reason**: Deprecated duplicate (fallback default = 0.3, GameDefines = 0.3)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### metabolic_rift:14:entropy_default -- Fallback default duplicating metabolism.entropy_factor
- **Reason**: Deprecated duplicate (fallback default = 1.2, GameDefines = 1.2)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### metabolic_rift:59:max_ratio_default -- Fallback default duplicating metabolism.max_overshoot_ratio
- **Reason**: Deprecated duplicate (fallback default = 999.0, GameDefines = 999.0)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### curvature:32:alpha_default -- Fallback default duplicating contradiction_field.curvature_alpha
- **Reason**: Deprecated duplicate (fallback default = 0.5, GameDefines = 0.5)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### community_formula:21:overlap_bonus -- Fallback default duplicating community.community_overlap_bonus
- **Reason**: Deprecated duplicate (fallback default = 0.1, GameDefines = 0.1)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### community_formula:22:rent_penalty -- Fallback default duplicating community.rent_differential_penalty
- **Reason**: Deprecated duplicate (fallback default = 0.05, GameDefines = 0.05)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### community_formula:81:maint_factor -- Fallback default duplicating community.core_organizer_maintenance_factor
- **Reason**: Deprecated duplicate (fallback default = 0.1, GameDefines = 0.1)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### trpf:25:efficiency_floor -- Fallback default duplicating economy.trpf_efficiency_floor
- **Reason**: Deprecated duplicate (fallback default = 0.1, GameDefines = 0.1)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### topology_monitor:55:GASEOUS_THRESHOLD -- Deprecated module constant duplicating topology.gaseous_threshold
- **Reason**: Deprecated duplicate (module constant = 0.1, GameDefines = 0.1)
- **Active consumers**: 0 (only used as default argument fallback in `__init__`)
- **Deprecated consumers**: 0

### topology_monitor:56:CONDENSATION_THRESHOLD -- Deprecated module constant duplicating topology.condensation_threshold
- **Reason**: Deprecated duplicate (module constant = 0.5, GameDefines = 0.5)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### topology_monitor:57:BRITTLE_MULTIPLIER -- Deprecated module constant with no GameDefines equivalent
- **Reason**: Dead constant (0 consumers anywhere in codebase)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### topology_monitor:60:POTENTIAL_MIN_STRENGTH -- Deprecated module constant
- **Reason**: Dead constant (0 consumers)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### topology_monitor:61:ACTUAL_MIN_STRENGTH -- Deprecated module constant
- **Reason**: Dead constant (0 consumers)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### topology_monitor:64:DEFAULT_REMOVAL_RATE -- Deprecated module constant
- **Reason**: Dead constant (0 consumers)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### topology_monitor:65:DEFAULT_SURVIVAL_THRESHOLD -- Deprecated module constant
- **Reason**: Dead constant (0 consumers)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### endgame_detector:53:PERCOLATION_THRESHOLD -- Deprecated duplicate of endgame.revolutionary_percolation_threshold
- **Reason**: Deprecated duplicate (module constant = 0.7, GameDefines = 0.7)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### endgame_detector:54:CONSCIOUSNESS_THRESHOLD -- Deprecated duplicate of endgame.revolutionary_consciousness_threshold
- **Reason**: Deprecated duplicate (module constant = 0.8, GameDefines = 0.8)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### endgame_detector:57:OVERSHOOT_THRESHOLD -- Deprecated duplicate of endgame.ecological_overshoot_threshold
- **Reason**: Deprecated duplicate (module constant = 2.0, GameDefines = 2.0)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### endgame_detector:58:OVERSHOOT_CONSECUTIVE -- Deprecated duplicate of endgame.ecological_sustained_ticks
- **Reason**: Deprecated duplicate (module constant = 5, GameDefines = 5)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### endgame_detector:61:FASCIST_NODES -- Deprecated duplicate of endgame.fascist_majority_threshold
- **Reason**: Deprecated duplicate (module constant = 3, GameDefines = 3)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### metrics:41:DEATH_THRESHOLD -- Duplicate of economy.death_threshold
- **Reason**: Deprecated duplicate (module constant = 0.001, GameDefines = 0.001)
- **Active consumers**: 0
- **Deprecated consumers**: 0

### ideological_routing:82:decay_rate -- Fallback default for agitation decay
- **Reason**: Dead constant (0 direct consumers; parameter default in function signature, not tied to any GameDefines field)
- **Active consumers**: 0
- **Deprecated consumers**: 0

---

## Tier C: Calibration Parameters (63 constants)

Constants with theoretical meaning but no direct federal data source for the specific value; calibrate via parameter sweep (Optuna/SALib). All GameDefines fields are already in the Optuna search space via `get_tunable_parameters()`.

### crisis.r_threshold -- Profit rate threshold for crisis accumulation
- **Theoretical meaning**: Marxian profit rate floor below which accumulation stalls
- **Calibration source**: Historical NBER recession onset profit rates via BEA data
- **Sweep range**: [0.01, 0.15]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### crisis.hysteresis_coefficient -- Recovery hysteresis factor
- **Theoretical meaning**: Recovery stickiness from crisis persistence (path dependence)
- **Calibration source**: No direct federal source; calibrate against NBER recovery durations
- **Sweep range**: [0.1, 0.9]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### crisis.wage_compression_rate -- Per-period wage compression during DEEP crisis
- **Theoretical meaning**: Rate of real wage decline during deep crisis (Marx Vol. I Ch. 25)
- **Calibration source**: BLS real wage data during recessions
- **Sweep range**: [0.005, 0.10]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### crisis.wage_compression_floor_ratio -- Wage floor as fraction of subsistence
- **Theoretical meaning**: Minimum wage below which reproduction of labor power fails
- **Calibration source**: BLS poverty threshold vs. median wage ratio
- **Sweep range**: [0.5, 0.95]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### crisis.bifurcation_solidarity_weight -- Weight for solidarity in bifurcation formula
- **Theoretical meaning**: Relative importance of solidarity network density in determining bifurcation direction (revolution vs. fascism)
- **Calibration source**: No direct federal source; calibrate via simulation outcome sensitivity
- **Sweep range**: [0.1, 5.0]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### crisis.bifurcation_burden_weight -- Weight for class burden in bifurcation formula
- **Theoretical meaning**: Relative importance of class burden ratio in bifurcation direction
- **Calibration source**: No direct federal source; calibrate via simulation outcome sensitivity
- **Sweep range**: [0.1, 5.0]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### economy.initial_rent_pool -- Starting imperial rent pool
- **Theoretical meaning**: Accumulated imperial rent at simulation start
- **Calibration source**: BEA net international investment position as proxy
- **Sweep range**: [10.0, 500.0]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### economy.pool_high_threshold -- Pool ratio for prosperity mode
- **Theoretical meaning**: Imperial rent abundance threshold for bribery policy
- **Calibration source**: No direct federal source; calibrate via bourgeoisie decision sensitivity
- **Sweep range**: [0.5, 0.9]
- **Sweep tooling**: Available (see bourgeoisie cluster report)

### economy.pool_low_threshold -- Pool ratio for austerity mode
- **Theoretical meaning**: Imperial rent scarcity threshold for austerity pivot
- **Calibration source**: No direct federal source; calibrate via bourgeoisie decision sensitivity
- **Sweep range**: [0.1, 0.5]
- **Sweep tooling**: Available (see bourgeoisie cluster report)

### economy.pool_critical_threshold -- Pool ratio for ECONOMIC_CRISIS
- **Theoretical meaning**: Imperial rent exhaustion threshold triggering systemic crisis
- **Calibration source**: No direct federal source; calibrate as fraction of pool_low_threshold
- **Sweep range**: [0.01, 0.3]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### economy.min_wage_rate -- Minimum super-wage rate during crisis
- **Theoretical meaning**: Floor on wage bribery even during crisis (to prevent instant insurrection)
- **Calibration source**: Historical real minimum wage ratio to median
- **Sweep range**: [0.01, 0.15]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### economy.max_wage_rate -- Maximum super-wage rate during prosperity
- **Theoretical meaning**: Ceiling on wage bribery (above which profit extraction insufficient)
- **Calibration source**: Historical peak labor share from BEA/FRED
- **Sweep range**: [0.20, 0.50]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### economy.subsidy_conversion_rate -- Rate of wealth-to-repression conversion
- **Theoretical meaning**: Efficiency of converting economic surplus to state violence capacity
- **Calibration source**: No direct federal source; proxy via police spending / GDP ratio
- **Sweep range**: [0.01, 0.25]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### economy.subsidy_trigger_threshold -- P(S|R)/P(S|A) ratio threshold for subsidy
- **Theoretical meaning**: How threatened the state must feel before deploying repressive subsidy
- **Calibration source**: No direct federal source; calibrate via simulation dynamics
- **Sweep range**: [0.5, 1.5]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### economy.rent_pool_decay -- Background evaporation of imperial rent pool per tick
- **Theoretical meaning**: Entropic loss of accumulated imperial rent
- **Calibration source**: Historical depreciation of US net international investment position
- **Sweep range**: [0.0005, 0.01]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### economy.bribery_wage_delta -- Wage increase during prosperity (BRIBERY policy)
- **Theoretical meaning**: Magnitude of wage concession when empire flush with imperial rent
- **Calibration source**: Historical real wage growth rates during expansions
- **Sweep range**: [0.01, 0.15]
- **Sweep tooling**: Available (see bourgeoisie cluster report)

### economy.austerity_wage_delta -- Wage cut during austerity
- **Theoretical meaning**: Magnitude of wage cut when imperial rent scarce
- **Calibration source**: Historical real wage decline rates during contractions
- **Sweep range**: [-0.15, -0.01]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### economy.iron_fist_repression_delta -- Repression increase during high tension
- **Theoretical meaning**: State repression escalation rate when social tension high
- **Calibration source**: No direct federal source; proxy via BJS incarceration rate changes
- **Sweep range**: [0.01, 0.25]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### economy.crisis_wage_delta -- Emergency wage cut during crisis
- **Theoretical meaning**: Severe wage cut magnitude during systemic crisis
- **Calibration source**: Historical real wage crash data (Great Depression, 2008)
- **Sweep range**: [-0.30, -0.05]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### economy.crisis_repression_delta -- Emergency repression spike during crisis
- **Theoretical meaning**: State violence escalation during systemic crisis
- **Calibration source**: No direct federal source; historical police militarization data
- **Sweep range**: [0.05, 0.40]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### economy.bribery_tension_threshold -- Maximum tension for bribery policy
- **Theoretical meaning**: Social tension ceiling below which bribery is still viable
- **Calibration source**: No direct federal source; calibrate via simulation dynamics
- **Sweep range**: [0.1, 0.5]
- **Sweep tooling**: Available (see bourgeoisie cluster report)

### economy.iron_fist_tension_threshold -- Minimum tension for iron fist policy
- **Theoretical meaning**: Social tension floor above which state escalates to repression
- **Calibration source**: No direct federal source; calibrate via simulation dynamics
- **Sweep range**: [0.3, 0.8]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### survival.steepness_k -- Sigmoid sharpness in acquiescence probability
- **Theoretical meaning**: How sharply P(S|A) transitions from 0 to 1 around subsistence threshold
- **Calibration source**: No direct federal source; calibrate against wealth-mortality curves
- **Sweep range**: [3.0, 20.0]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### survival.default_subsistence -- Minimum wealth for survival through compliance
- **Theoretical meaning**: Subsistence threshold below which acquiescence probability collapses
- **Calibration source**: BLS poverty threshold / median income ratio
- **Sweep range**: [0.1, 0.6]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### survival.default_organization -- Fallback organization value
- **Theoretical meaning**: Default organizational capacity of unorganized class
- **Calibration source**: BLS union membership rate as proxy
- **Sweep range**: [0.01, 0.3]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### survival.default_repression -- Fallback repression value
- **Theoretical meaning**: Default state repressive capacity
- **Calibration source**: BJS police-to-population ratio as proxy
- **Sweep range**: [0.2, 0.8]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### solidarity.activation_threshold -- Minimum consciousness for transmission
- **Theoretical meaning**: Consciousness floor below which solidarity cannot propagate (atomization barrier)
- **Calibration source**: No direct federal source; calibrate against organizing threshold data
- **Sweep range**: [0.1, 0.5]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### solidarity.mass_awakening_threshold -- Consciousness target for MASS_AWAKENING event
- **Theoretical meaning**: Critical consciousness density triggering qualitative phase change
- **Calibration source**: No direct federal source; calibrate via percolation theory thresholds
- **Sweep range**: [0.4, 0.8]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### tension.accumulation_rate -- Rate of tension accumulation from wealth gaps
- **Theoretical meaning**: How quickly material inequality converts to social tension
- **Calibration source**: No direct federal source; calibrate against Gini-to-unrest correlation
- **Sweep range**: [0.01, 0.15]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### territory.rent_spike_multiplier -- Rent multiplier during eviction
- **Theoretical meaning**: Rent inflation factor in eviction cascade zones
- **Calibration source**: Eviction Lab -> ATTOM rent spike data during displacement
- **Sweep range**: [1.1, 3.0]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### territory.displacement_rate -- Population displacement during eviction
- **Theoretical meaning**: Fraction of population displaced per eviction event
- **Calibration source**: Eviction Lab displacement rates
- **Sweep range**: [0.01, 0.25]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### territory.clarity_profile_coefficient -- Clarity bonus for HIGH_PROFILE territories
- **Theoretical meaning**: State surveillance advantage in high-visibility zones
- **Calibration source**: No direct federal source; calibrate against Detroit carceral geography
- **Sweep range**: [0.1, 0.6]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### territory.concentration_camp_decay_rate -- Population decay in CONCENTRATION_CAMP territories
- **Theoretical meaning**: Mortality rate in maximum-security carceral facilities
- **Calibration source**: BJS prison mortality data
- **Sweep range**: [0.05, 0.40]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### territory.elimination_rent_threshold -- Rent ratio for ELIMINATION mode
- **Theoretical meaning**: Imperial rent scarcity level triggering genocidal state response
- **Calibration source**: No direct federal source; calibrate via simulation outcome sensitivity
- **Sweep range**: [0.01, 0.25]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### territory.elimination_tension_threshold -- Tension threshold for ELIMINATION mode
- **Theoretical meaning**: Social tension level triggering genocidal state response
- **Calibration source**: No direct federal source; calibrate via simulation outcome sensitivity
- **Sweep range**: [0.5, 0.95]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### territory.containment_rent_threshold -- Rent ratio for CONTAINMENT mode
- **Theoretical meaning**: Imperial rent scarcity level triggering reservation/containment
- **Calibration source**: No direct federal source; calibrate relative to elimination threshold
- **Sweep range**: [0.1, 0.5]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### territory.containment_tension_threshold -- Tension threshold for CONTAINMENT mode
- **Theoretical meaning**: Social tension level triggering containment strategy
- **Calibration source**: No direct federal source; calibrate relative to elimination threshold
- **Sweep range**: [0.3, 0.7]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### topology.gaseous_threshold -- Percolation ratio for atomization
- **Theoretical meaning**: Solidarity network density below which no collective action possible
- **Calibration source**: Percolation theory critical threshold on random graphs
- **Sweep range**: [0.05, 0.2]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### topology.condensation_threshold -- Percolation ratio for phase transition
- **Theoretical meaning**: Solidarity density at which qualitative phase change occurs (gas->liquid)
- **Calibration source**: Percolation theory on Erdos-Renyi graphs
- **Sweep range**: [0.3, 0.7]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### topology.vanguard_density_threshold -- Cadre density for vanguard party
- **Theoretical meaning**: Density of highly-conscious cadre needed for liquid->solid transition
- **Calibration source**: No direct federal source; Leninist organizational theory
- **Sweep range**: [0.3, 0.7]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### metabolism.entropy_factor -- Thermodynamic inefficiency of extraction
- **Theoretical meaning**: Physical law: extraction costs more energy than it yields (entropy > 1)
- **Calibration source**: Ecological footprint data (Global Footprint Network)
- **Sweep range**: [1.01, 2.0]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### metabolism.overshoot_threshold -- Consumption/biocapacity ratio for ECOLOGICAL_OVERSHOOT
- **Theoretical meaning**: Ecological carrying capacity threshold; O > 1 means consumption exceeds regeneration
- **Calibration source**: Global Footprint Network ecological overshoot data
- **Sweep range**: [0.8, 1.5]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### carceral.control_capacity -- Prisoners one enforcer can control
- **Theoretical meaning**: Staff-to-inmate ratio for carceral stability (BJS documented)
- **Calibration source**: BJS National Prisoner Statistics -> staff ratios
- **Sweep range**: [1, 20]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### carceral.enforcer_fraction -- Fraction of former LA becoming enforcers
- **Theoretical meaning**: Class decomposition split ratio (guards vs. prisoners)
- **Calibration source**: BLS law enforcement employment / total employment (SOC 33-0000)
- **Sweep range**: [0.05, 0.50]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### carceral.proletariat_fraction -- Fraction of former LA becoming prisoners
- **Theoretical meaning**: Complement of enforcer_fraction in class decomposition
- **Calibration source**: Constrained: must equal 1.0 - enforcer_fraction
- **Sweep range**: [0.50, 0.95]
- **Sweep tooling**: Available (jointly with enforcer_fraction)

### contradiction_field.field_max -- Maximum normalized field value
- **Theoretical meaning**: Upper bound for contradiction field normalization; determines dynamic range
- **Calibration source**: No direct source; calibrate via simulation dynamic range analysis
- **Sweep range**: [5.0, 20.0]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### contradiction_field.co_optive_suppression_rate -- Fraction of df/dt suppressed by CO-OPTIVE edges
- **Theoretical meaning**: Effectiveness of co-optation in dampening contradictions
- **Calibration source**: No direct federal source; calibrate via simulation dynamics
- **Sweep range**: [0.5, 1.0]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### contradiction_field.latent_release_multiplier -- Multiplier for released latent contradictions
- **Theoretical meaning**: Amplification when suppressed contradictions finally release (pressure cooker effect)
- **Calibration source**: No direct federal source; calibrate via crisis intensity dynamics
- **Sweep range**: [1.0, 5.0]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### community.heat_decay_alpha -- Community heat decay rate
- **Theoretical meaning**: Rate at which community-level grievance dissipates without provocation
- **Calibration source**: No direct federal source; calibrate against protest duration data
- **Sweep range**: [0.01, 0.15]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### community.cohesion_decay_alpha -- Cohesion decay rate
- **Theoretical meaning**: Rate at which social cohesion deteriorates without active organizing
- **Calibration source**: No direct federal source; calibrate against union attrition rates
- **Sweep range**: [0.01, 0.10]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### community.infrastructure_decay_alpha -- Infrastructure decay rate
- **Theoretical meaning**: Rate at which organizational infrastructure degrades without maintenance
- **Calibration source**: No direct federal source; calibrate against organizational dissolution rates
- **Sweep range**: [0.01, 0.10]
- **Sweep tooling**: Available -- `mise run tune:optuna`

### class_dynamics:187:beta_default -- Default damping coefficient for wealth acceleration
- **Theoretical meaning**: Second-order ODE damping term for wealth dynamics
- **Calibration source**: FRED macro time series -> acceleration fitting
- **Sweep range**: [-0.5, 0.0]
- **Sweep tooling**: Needs setup -- not in GameDefines; requires inline centralization first

### class_dynamics:188:omega_default -- Default natural frequency for wealth acceleration
- **Theoretical meaning**: Second-order ODE natural frequency for wealth oscillation
- **Calibration source**: FRED macro time series -> cycle period fitting
- **Sweep range**: [0.01, 0.2]
- **Sweep tooling**: Needs setup -- not in GameDefines

### class_dynamics:289:target_pct -- Default target wealth percentage for population inversion
- **Theoretical meaning**: Equilibrium wealth share per class in absence of exploitation
- **Calibration source**: Fed SCF wealth distribution -> equal-share baseline
- **Sweep range**: [20.0, 50.0]
- **Sweep tooling**: Needs setup -- not in GameDefines

### gamma_adapters:40:care_fraction_61 -- Care fraction for NAICS 61 (Education)
- **Theoretical meaning**: Share of education sector labor that constitutes reproductive/care work
- **Calibration source**: ATUS time-use data -> education sector time allocation
- **Sweep range**: [0.3, 0.9]
- **Sweep tooling**: Needs setup -- not in GameDefines

### gamma_adapters:41:care_fraction_62 -- Care fraction for NAICS 62 (Healthcare)
- **Theoretical meaning**: Share of healthcare sector labor that constitutes reproductive/care work
- **Calibration source**: ATUS time-use data -> healthcare sector time allocation
- **Sweep range**: [0.1, 0.6]
- **Sweep tooling**: Needs setup -- not in GameDefines

### gamma_adapters:42:care_fraction_814 -- Care fraction for NAICS 814 (Private Households)
- **Theoretical meaning**: Share of private household sector labor that is care work (100% by definition)
- **Calibration source**: Definitional -- all NAICS 814 labor is household service work
- **Sweep range**: [1.0, 1.0] (fixed; definitional)
- **Sweep tooling**: N/A

### crisis_dyn:20:amplifier_default -- Default crisis amplifier multiplier
- **Theoretical meaning**: Multiplicative amplification factor during crisis phases
- **Calibration source**: No direct federal source; calibrate against historical recession severity
- **Sweep range**: [1.5, 5.0]
- **Sweep tooling**: Needs setup -- not in GameDefines

### crisis_dyn:21:dampener_default -- Default recovery dampener multiplier
- **Theoretical meaning**: Multiplicative dampening factor during recovery
- **Calibration source**: No direct federal source; calibrate against NBER recovery rates
- **Sweep range**: [0.1, 0.6]
- **Sweep tooling**: Needs setup -- not in GameDefines

### metrics:264:fallback_wage_rate -- Fallback current super_wage_rate
- **Theoretical meaning**: Default wage rate when metrics collector has no state data
- **Calibration source**: Should mirror economy.super_wage_rate (0.2)
- **Sweep range**: [0.1, 0.3]
- **Sweep tooling**: Needs setup -- inline constant, should reference GameDefines

### metrics:265:fallback_repression -- Fallback current repression level
- **Theoretical meaning**: Default repression level when metrics collector has no state data
- **Calibration source**: Should mirror survival.default_repression (0.5)
- **Sweep range**: [0.2, 0.8]
- **Sweep tooling**: Needs setup -- inline constant, should reference GameDefines

### metrics:266:fallback_pool_ratio -- Fallback pool ratio
- **Theoretical meaning**: Default pool ratio when metrics collector has no state data
- **Calibration source**: Should default to 1.0 (full pool at start)
- **Sweep range**: [0.5, 1.0]
- **Sweep tooling**: Needs setup -- inline constant

### metrics:270:pool_divisor -- Pool ratio divisor (initial_pool proxy)
- **Theoretical meaning**: Divisor for computing pool ratio (should track economy.initial_rent_pool)
- **Calibration source**: Should match economy.initial_rent_pool (100.0)
- **Sweep range**: [50.0, 500.0]
- **Sweep tooling**: Needs setup -- should derive from GameDefines initial_rent_pool

---

## Tier D: Engineering/Precision (14 constants)

Division-by-zero guards, overflow prevention, precision constants, and mathematical necessities that serve a purely engineering purpose. The specific values have no theoretical or gameplay meaning beyond ensuring computational correctness.

### crisis.class_burden_epsilon -- Division-by-zero guard for class burden ratio
- **Purpose**: Prevents division by zero in `TickDynamicsSystem._run_bifurcation_risk`
- **Constraint**: Must be positive and much smaller than typical burden ratios (0.001 << 1.0)
- **Change risk**: None if remains < 0.01

### precision.decimal_places -- Quantization precision (10^-n)
- **Purpose**: Controls simulation grid precision for deterministic cross-platform behavior
- **Constraint**: Must be >= 1; higher values give more precision
- **Change risk**: Changing affects all `Probability`, `Currency`, `Intensity` quantization; must re-validate all outputs

### precision.epsilon -- Division-by-zero guard for formulas
- **Purpose**: Universal division-by-zero guard; must be < grid precision
- **Constraint**: epsilon < 10^(-decimal_places); current 1e-9 < 1e-6
- **Change risk**: None if constraint maintained

### precision.comparison_epsilon -- Float equality tolerance for tests
- **Purpose**: Tolerance for `pytest.approx` comparisons
- **Constraint**: Must be < precision.epsilon; current 1e-10 < 1e-9
- **Change risk**: Tightening may cause spurious failures; loosening may miss regressions

### timescale.tick_duration_days -- Real-world days per tick
- **Purpose**: Temporal resolution; 7 = weekly. All rate constants calibrated for weekly ticks
- **Constraint**: Must be >= 1; changing requires recalibrating ALL rate constants
- **Change risk**: Changing this is equivalent to rescaling the entire simulation

### timescale.weeks_per_year -- Weeks per year for flow conversion
- **Purpose**: Annual-to-weekly rate conversion factor; 52 = Gregorian calendar convention
- **Constraint**: Must be 52 (or the simulation time model breaks)
- **Change risk**: Changing breaks all annual rate conversions

### economy.negligible_rent -- Rent threshold for event emission skip
- **Purpose**: Noise filtering; prevents event spam from insignificant rent values
- **Constraint**: Must be > 0 and < meaningful rent values
- **Change risk**: Lowering increases event volume; raising may suppress meaningful events

### economy.negligible_subsidy -- Subsidy threshold for processing skip
- **Purpose**: Noise filtering; prevents computation on negligible subsidies
- **Constraint**: Must be > 0 and < meaningful subsidy values
- **Change risk**: Same as negligible_rent

### economy.death_threshold -- Wealth threshold for entity death (zombie prevention)
- **Purpose**: Engineering failsafe preventing zero-wealth entities from persisting
- **Constraint**: Must be > 0; entities below this die immediately
- **Change risk**: Lowering allows near-dead entities to persist; raising kills entities prematurely

### metabolism.max_overshoot_ratio -- Cap for overshoot ratio when biocapacity depleted
- **Purpose**: Prevents division-by-near-zero producing astronomically large ratios
- **Constraint**: Must be >> 1.0 (the overshoot threshold) to cap without distorting
- **Change risk**: None if sufficiently large; purely defensive cap

### survival_calculus:36:exp_clamp_low -- Overflow prevention lower bound for sigmoid exponent
- **Purpose**: Prevents `math.exp()` overflow in acquiescence sigmoid
- **Constraint**: `abs(value) < 709` (IEEE 754 double precision limit for exp)
- **Change risk**: None if sufficiently negative

### survival_calculus:36:exp_clamp_high -- Overflow prevention upper bound for sigmoid exponent
- **Purpose**: Prevents `math.exp()` overflow in acquiescence sigmoid
- **Constraint**: `value < 709` (IEEE 754 limit)
- **Change risk**: None if sufficiently positive

### distribution:25:EPSILON -- Distribution surplus identity verification epsilon
- **Purpose**: Epsilon for verifying surplus distribution identity (total_out = total_in within tolerance)
- **Constraint**: Must be positive and small relative to surplus magnitudes
- **Change risk**: None if constraint maintained

### solidarity.negligible_transmission -- Threshold below which transmissions skipped
- **Purpose**: Noise filtering and performance optimization; prevents solidarity computation on negligible edges
- **Constraint**: Must be > 0 and < meaningful transmission values
- **Change risk**: Lowering increases computation; raising may suppress meaningful solidarity

---

## Tier E: Game Design Knobs (99 constants)

Intentional game design choices where no federal data source tracks the concept. These encode narrative pacing, game balance, and gameplay mechanics. Each must be documented as an intentional design choice in its GameDefines Field description.

### crisis.crisis_period_ticks -- Ticks per crisis evaluation period
- **Rationale**: 13 is a deliberate game design choice (quarterly + prime for desync). No federal data source dictates evaluation period length; this is a gameplay pacing parameter.
- **Labeling**: Intentional design choice -- narrative pacing of crisis detection frequency

### crisis.n_consecutive -- Consecutive below-threshold periods for crisis onset
- **Rationale**: Number of consecutive bad periods before crisis declared. No data source; gameplay severity filter.
- **Labeling**: Intentional design choice -- crisis sensitivity tuning

### crisis.m_recovery -- Consecutive above-threshold periods for recovery start
- **Rationale**: Number of consecutive good periods before recovery begins. Gameplay balance parameter.
- **Labeling**: Intentional design choice -- recovery pacing

### crisis.r_cap -- Maximum recovery duration (periods)
- **Rationale**: Maximum time for recovery phase. No data source; gameplay pacing for crisis arc length.
- **Labeling**: Intentional design choice -- crisis arc duration cap

### crisis.bifurcation_event_threshold -- |score| threshold for BIFURCATION_THRESHOLD event
- **Rationale**: Threshold for emitting bifurcation narrative events. No data source tracks bifurcation in real life; controls narrative event frequency.
- **Labeling**: Intentional design choice -- event emission sensitivity

### consciousness.sensitivity -- How quickly consciousness responds to material conditions
- **Rationale**: No federal data source tracks "class consciousness." Core gameplay mechanic controlling the speed of ideological transformation.
- **Labeling**: Intentional design choice -- consciousness dynamics pacing

### consciousness.decay_lambda -- Decay rate for consciousness without material basis
- **Rationale**: No federal data source tracks consciousness decay. Controls how quickly class consciousness dissipates without material reinforcement.
- **Labeling**: Intentional design choice -- consciousness persistence

### behavioral.loss_aversion_lambda -- Kahneman-Tversky loss aversion coefficient
- **Rationale**: While established at 2.25 by Kahneman-Tversky (1979), using this specific value in a game simulation is a design choice. The original was measured in laboratory gambling experiments, not political economy.
- **Labeling**: Intentional design choice -- behavioral economics parameter with academic provenance (K&T 1979)

### survival.revolution_threshold -- Tipping point for P(S|R) formula
- **Rationale**: No data source defines when revolution becomes viable. Core narrative threshold for the fundamental theorem.
- **Labeling**: Intentional design choice -- revolution narrative pivot point

### survival.repression_base -- Base resistance to revolution in denominator
- **Rationale**: Base state capacity to suppress revolution. No data tracks this directly; gameplay balance parameter.
- **Labeling**: Intentional design choice -- revolutionary difficulty baseline

### vitality.base_mortality_factor -- Fraction of at-risk population that dies per tick
- **Rationale**: While CDC WONDER has mortality data, converting it to a per-tick fraction of wealth-deficit population is a design choice about simulation lethality. The 0.01 value controls how quickly population declines under deprivation.
- **Labeling**: Intentional design choice -- mortality severity parameter

### vitality.inequality_impact -- How strongly inequality affects marginal wealth
- **Rationale**: Elasticity of mortality with respect to intra-class inequality. While inequality-health gradients exist in epidemiology, the 1.0 multiplier is a game design choice about how lethal inequality is.
- **Labeling**: Intentional design choice -- inequality severity parameter

### solidarity.scaling_factor -- Multiplier for graph edge weights affecting organization
- **Rationale**: No federal data source; controls how efficiently solidarity propagates through the network. Gameplay balance for organizing mechanics.
- **Labeling**: Intentional design choice -- solidarity propagation rate

### solidarity.superwage_impact -- How much imperial extraction affects Core wealth
- **Rationale**: Elasticity parameter. While BEA trade data could inform this, the specific elasticity is a design choice about how strongly empire benefits core workers.
- **Labeling**: Intentional design choice -- imperial benefit elasticity

### struggle.spark_probability_scale -- Base probability scale for EXCESSIVE_FORCE
- **Rationale**: No data source gives a probability of police brutality per tick. This is the "George Floyd Dynamic" gameplay trigger rate.
- **Labeling**: Intentional design choice -- agency layer trigger frequency

### struggle.resistance_threshold -- Minimum agitation for uprising to trigger
- **Rationale**: Threshold below which repression does not trigger organized resistance. Gameplay balance for agency layer sensitivity.
- **Labeling**: Intentional design choice -- uprising sensitivity

### struggle.wealth_destruction_rate -- Fraction of wealth destroyed during uprising
- **Rationale**: Riot damage fraction. While real riots have economic costs, the conversion to a per-tick fraction is a game design choice.
- **Labeling**: Intentional design choice -- uprising economic impact severity

### struggle.solidarity_gain_per_uprising -- Solidarity increase per uprising
- **Rationale**: How much solidarity network strengthens after uprising. No data source; gameplay mechanic for "Combustion builds infrastructure."
- **Labeling**: Intentional design choice -- uprising solidarity reward

### struggle.jackson_threshold -- Revolutionary capacity threshold
- **Rationale**: org * consciousness threshold for George Jackson bifurcation outcome. No data source; gameplay pivot point.
- **Labeling**: Intentional design choice -- bifurcation pivot threshold

### struggle.revolutionary_agitation_boost -- Agitation boost during revolutionary offensive
- **Rationale**: Magnitude of agitation surge when revolutionary path chosen. No data; gameplay intensity parameter.
- **Labeling**: Intentional design choice -- revolutionary offensive intensity

### struggle.fascist_identity_boost -- National identity boost during fascist turn
- **Rationale**: How much national identity increases in fascist path. No data source tracks "fascist identity gain per event."
- **Labeling**: Intentional design choice -- fascist turn severity

### struggle.fascist_acquiescence_boost -- Acquiescence boost during fascist turn
- **Rationale**: How much acquiescence increases in fascist path. Gameplay balance for fascist arc.
- **Labeling**: Intentional design choice -- fascist turn acquiescence impact

### carceral.revolution_threshold -- Prisoner organization threshold for revolution vs genocide
- **Rationale**: Average prisoner organization level determining terminal decision outcome. No data source; most critical game design choice in carceral arc.
- **Labeling**: Intentional design choice -- terminal decision pivot

### carceral.decomposition_delay -- Ticks to wait before CLASS_DECOMPOSITION
- **Rationale**: 52 ticks = 1 year. Temporal pacing of carceral arc phases. No data dictates this delay.
- **Labeling**: Intentional design choice -- carceral arc pacing

### carceral.control_ratio_delay -- Ticks to wait before control ratio check
- **Rationale**: 52 ticks = 1 year. Temporal pacing between decomposition and control ratio crisis.
- **Labeling**: Intentional design choice -- carceral arc pacing

### carceral.terminal_decision_delay -- Ticks before TERMINAL_DECISION
- **Rationale**: 1 tick = 1 week. Very short delay reflecting urgency of terminal crisis.
- **Labeling**: Intentional design choice -- terminal crisis urgency

### endgame.revolutionary_percolation_threshold -- Percolation ratio for revolutionary victory
- **Rationale**: 70% percolation = revolutionary victory. No data defines what percentage constitutes "winning." Core win condition.
- **Labeling**: Intentional design choice -- revolutionary victory win condition

### endgame.revolutionary_consciousness_threshold -- Consciousness threshold for revolutionary victory
- **Rationale**: 80% average consciousness = ideological clarity for revolution. No data; win condition parameter.
- **Labeling**: Intentional design choice -- revolutionary victory consciousness requirement

### endgame.ecological_overshoot_threshold -- Overshoot ratio for ecological collapse
- **Rationale**: 2x biocapacity consumption = ecological collapse tracking. While ecological footprint data exists, the specific game threshold is a design choice.
- **Labeling**: Intentional design choice -- ecological collapse severity threshold

### endgame.ecological_sustained_ticks -- Consecutive ticks for ecological collapse
- **Rationale**: 5 consecutive ticks of overshoot before collapse. Gameplay pacing for ecological arc.
- **Labeling**: Intentional design choice -- ecological collapse patience

### endgame.fascist_majority_threshold -- Minimum nodes for fascist consolidation
- **Rationale**: 3 nodes with national_identity > class_consciousness = fascist win. No data; win condition.
- **Labeling**: Intentional design choice -- fascist consolidation win condition

### initial.default_population -- Default population for test entities
- **Rationale**: pop=1 is a deliberate test infrastructure choice ensuring per-capita mechanics are tested without large denominators masking issues.
- **Labeling**: Intentional design choice -- test infrastructure default

### contradiction_field.field_min -- Minimum normalized field value
- **Rationale**: Lower bound 0.0 is a mathematical/design convention for the contradiction field normalization range.
- **Labeling**: Intentional design choice -- field normalization lower bound

### contradiction_field.history_window -- Rolling tick window for temporal derivative
- **Rationale**: Window size is an engineering/design choice about how much history informs the current derivative; no data source.
- **Labeling**: Intentional design choice -- temporal resolution

### contradiction_field.curvature_alpha -- Self-loop weight for Ollivier-Ricci
- **Rationale**: Mathematical modeling choice for curvature computation. Typically 0.5 in OR-curvature literature (Ollivier 2009), but using this specific value is a design choice.
- **Labeling**: Intentional design choice -- mathematical modeling choice (Ollivier 2009)

### contradiction_field.default_transition_priority -- Default priority for transitions
- **Rationale**: Default priority = 0 for edge transitions without explicit priority. Purely a system convention.
- **Labeling**: Intentional design choice -- transition execution ordering

### dispossession.weight_foreclosure -- Weight for foreclosure events
- **Rationale**: 40% weight for foreclosure in dispossession intensity. While data exists on foreclosure rates, the relative weighting is a game design choice about which forms of dispossession are most impactful.
- **Labeling**: Intentional design choice -- dispossession type impact weighting

### dispossession.weight_eviction -- Weight for eviction events
- **Rationale**: 30% weight for eviction. While Eviction Lab data exists on rates, the specific weight allocation is a design choice.
- **Labeling**: Intentional design choice -- dispossession type impact weighting

### dispossession.weight_displacement -- Weight for gentrification displacement
- **Rationale**: 15% weight for gentrification displacement. Design choice about relative impact.
- **Labeling**: Intentional design choice -- dispossession type impact weighting

### dispossession.weight_tax_sale -- Weight for tax sale events
- **Rationale**: 5% weight for tax sale. Design choice.
- **Labeling**: Intentional design choice -- dispossession type impact weighting

### dispossession.weight_eminent_domain -- Weight for eminent domain events
- **Rationale**: 2% weight for eminent domain. Design choice.
- **Labeling**: Intentional design choice -- dispossession type impact weighting

### dispossession.weight_wage_theft -- Weight for wage theft events
- **Rationale**: 3% weight for wage theft. Design choice.
- **Labeling**: Intentional design choice -- dispossession type impact weighting

### dispossession.weight_incarceration_seizure -- Weight for incarceration-related seizure
- **Rationale**: 3% weight for incarceration seizure. Design choice.
- **Labeling**: Intentional design choice -- dispossession type impact weighting

### dispossession.weight_pension_default -- Weight for pension default events
- **Rationale**: 2% weight for pension default. Design choice.
- **Labeling**: Intentional design choice -- dispossession type impact weighting

### dispossession.deadweight_loss_fraction -- Fraction of value lost as deadweight
- **Rationale**: 5% deadweight loss during dispossession. While economic theory discusses deadweight loss, the specific fraction is a design choice.
- **Labeling**: Intentional design choice -- dispossession economic friction

### working_day.absolute_hours_threshold -- Weekly hours for ABSOLUTE_DOMINANT exploitation
- **Rationale**: 45 hours/week threshold. While BLS tracks hours worked, the classification of what constitutes "absolute exploitation" is a Marxist theoretical/game design choice.
- **Labeling**: Intentional design choice -- exploitation mode classification (value theory)

### working_day.relative_hours_threshold -- Weekly hours for RELATIVE_DOMINANT exploitation
- **Rationale**: 40 hours/week threshold. Standard work week, but using it as exploitation mode boundary is a design choice.
- **Labeling**: Intentional design choice -- exploitation mode classification (value theory)

### working_day.intensity_threshold_high -- Labor intensity for RELATIVE_DOMINANT with low hours
- **Rationale**: 1.2x intensity threshold. No data source measures "labor intensity" in this unitless form.
- **Labeling**: Intentional design choice -- exploitation mode classification

### working_day.intensity_threshold_low -- Labor intensity for ABSOLUTE_DOMINANT with high hours
- **Rationale**: 1.1x intensity threshold. No data source; design choice.
- **Labeling**: Intentional design choice -- exploitation mode classification

### working_day.absolute_visibility -- Consciousness visibility for ABSOLUTE exploitation
- **Rationale**: 1.0 (full visibility). Design choice that absolute exploitation is fully visible to class consciousness.
- **Labeling**: Intentional design choice -- consciousness visibility modifier (Marx Vol. I Ch. 10)

### working_day.relative_visibility -- Consciousness visibility for RELATIVE exploitation
- **Rationale**: 0.3 (low visibility). Design choice that relative exploitation is harder to perceive ("hidden behind the apparent fairness of the wage contract" -- Marx).
- **Labeling**: Intentional design choice -- consciousness visibility modifier (Marx Vol. I Ch. 12)

### community.community_overlap_bonus -- Solidarity bonus per shared community membership
- **Rationale**: No data source; represents the organizing benefit of shared community membership. Gameplay balance parameter.
- **Labeling**: Intentional design choice -- solidarity mechanics

### community.rent_differential_penalty -- Solidarity penalty per rent differential
- **Rationale**: No data source; represents how imperial rent differentials fracture solidarity. Gameplay balance.
- **Labeling**: Intentional design choice -- cross-community solidarity mechanics

### community.core_organizer_maintenance_factor -- Infrastructure maintenance per CORE_ORGANIZER
- **Rationale**: No data source; represents organizer cadre contribution to infrastructure maintenance.
- **Labeling**: Intentional design choice -- organizing infrastructure mechanics

### ideological_routing:39:routing_scale -- Agitation to consciousness conversion scale
- **Rationale**: No data source; controls the rate at which agitation materializes as ideological shift. Narrative pacing parameter.
- **Labeling**: Intentional design choice -- ideological routing intensity

### vitality:42:attrition_base -- Attrition base rate in deficit formula
- **Rationale**: No data source tracks base attrition from subsistence deficit; design choice about mortality dynamics.
- **Labeling**: Intentional design choice -- mortality severity in attrition formula

### struggle:370:consciousness_mult -- Consciousness boost multiplier from solidarity gain
- **Rationale**: consciousness_boost = solidarity_gain * 0.5. No data; gameplay coupling between solidarity and consciousness.
- **Labeling**: Intentional design choice -- uprising consciousness spillover

### community_sys:156:heat_increase -- Default heat increase for designate_community
- **Rationale**: State attention drawn by community designation; no data source.
- **Labeling**: Intentional design choice -- community designation heat impact

### community_sys:174:cohesion_reduce -- Default cohesion reduction for infiltrate_community
- **Rationale**: Effectiveness of COINTELPRO-style infiltration; no data source.
- **Labeling**: Intentional design choice -- infiltration effectiveness

### community_sys:191:infra_reduce -- Default infrastructure reduction for disrupt_infrastructure
- **Rationale**: Effectiveness of infrastructure disruption actions; no data source.
- **Labeling**: Intentional design choice -- disruption effectiveness

### edge_transition:103:extraction_contested -- Exploitation threshold for extraction contested
- **Rationale**: Exploitation field value of 5.0 triggers EXTRACTION->CONTESTED transition. No data source defines when exploitation becomes "contested"; narrative transition threshold.
- **Labeling**: Intentional design choice -- edge mode transition threshold

### edge_transition:128:extraction_broken -- Exploitation threshold for extraction broken
- **Rationale**: Exploitation field value of 2.0 triggers EXPLOITATION->BROKEN. Narrative transition threshold.
- **Labeling**: Intentional design choice -- edge mode transition threshold

### edge_transition:147:concessions_offered -- Exploitation threshold for concessions offered
- **Rationale**: Exploitation field value of 3.0. Narrative transition threshold.
- **Labeling**: Intentional design choice -- edge mode transition threshold

### edge_transition:171:mutual_aid_src -- Exploitation threshold for mutual aid
- **Rationale**: Exploitation field value of 2.0 (source). Narrative transition threshold.
- **Labeling**: Intentional design choice -- edge mode transition threshold

### edge_transition:197:market_failure -- Immiseration df_dt threshold for market failure
- **Rationale**: Immiseration rate of 1.0. Narrative transition threshold.
- **Labeling**: Intentional design choice -- edge mode transition threshold

### edge_transition:214:power_asymmetry -- Exploitation threshold for power asymmetry
- **Rationale**: Exploitation field value of 5.0. Narrative transition threshold.
- **Labeling**: Intentional design choice -- edge mode transition threshold

### edge_transition:233:co_optive_power -- Imperial rent threshold for co-optive power
- **Rationale**: Imperial rent field value of 3.0. Narrative transition threshold.
- **Labeling**: Intentional design choice -- edge mode transition threshold

### edge_transition:252:solidarity_degrades -- Immiseration threshold for solidarity degradation
- **Rationale**: Immiseration field value of 6.0. Narrative transition threshold.
- **Labeling**: Intentional design choice -- edge mode transition threshold

### edge_transition:271:betrayal -- Exploitation df_dt threshold for betrayal
- **Rationale**: Exploitation rate of change of 3.0. Narrative transition threshold.
- **Labeling**: Intentional design choice -- edge mode transition threshold

### edge_transition:296:conflict_resolved -- Exploitation threshold for conflict resolved
- **Rationale**: Exploitation field value of 3.0. Narrative transition threshold.
- **Labeling**: Intentional design choice -- edge mode transition threshold

### edge_transition:314:shared_enemy_src -- Exploitation threshold for shared enemy alliance
- **Rationale**: Exploitation field value of 7.0 (source). Narrative transition threshold.
- **Labeling**: Intentional design choice -- edge mode transition threshold

### edge_transition:339:reform_concession -- Imperial rent threshold for reform concession
- **Rationale**: Imperial rent field value of 3.0. Narrative transition threshold.
- **Labeling**: Intentional design choice -- edge mode transition threshold

### edge_transition:367:co_opt_normalizes -- Exploitation threshold for co-optation normalization
- **Rationale**: Exploitation field value of 2.0. Narrative transition threshold.
- **Labeling**: Intentional design choice -- edge mode transition threshold

### edge_transition:392:co_opt_breakdown -- Exploitation df_dt threshold for co-optive breakdown
- **Rationale**: Exploitation rate of change of 1.0. Narrative transition threshold.
- **Labeling**: Intentional design choice -- edge mode transition threshold

### edge_transition:411:co_opt_recognized_src -- Exploitation threshold for co-optation recognized
- **Rationale**: Exploitation field value of 5.0 (source). Narrative transition threshold.
- **Labeling**: Intentional design choice -- edge mode transition threshold

### edge_transition:434:concessions_withdrawn -- Imperial rent threshold for concessions withdrawn
- **Rationale**: Imperial rent field value of 1.0. Narrative transition threshold.
- **Labeling**: Intentional design choice -- edge mode transition threshold

### metrics:59:rolling_window -- Default rolling window size for MetricsCollector
- **Rationale**: 50-tick rolling window for metrics smoothing. Visualization/UX choice, not data-derived.
- **Labeling**: Intentional design choice -- metrics smoothing window

### savings_schedule:24:savings_bourgeoisie -- Default savings rate: BOURGEOISIE
- **Rationale**: While Fed SCF shows savings rates by income quintile, the mapping to Marxian class categories is a design choice. The 38% value is a game design interpretation.
- **Labeling**: Intentional design choice -- class-specific savings rate (Fed SCF inspired)

### savings_schedule:25:savings_petit_b -- Default savings rate: PETIT_BOURGEOISIE
- **Rationale**: 20% savings rate. Game design interpretation of Fed SCF data.
- **Labeling**: Intentional design choice -- class-specific savings rate

### savings_schedule:26:savings_la -- Default savings rate: LABOR_ARISTOCRACY
- **Rationale**: 12% savings rate. Game design interpretation of Fed SCF data.
- **Labeling**: Intentional design choice -- class-specific savings rate

### savings_schedule:27:savings_proletariat -- Default savings rate: PROLETARIAT
- **Rationale**: 3% savings rate. Game design interpretation of Fed SCF data.
- **Labeling**: Intentional design choice -- class-specific savings rate

### savings_schedule:28:savings_lumpen -- Default savings rate: LUMPENPROLETARIAT
- **Rationale**: 0% savings rate. Definitional -- lumpenproletariat has no savings capacity.
- **Labeling**: Intentional design choice -- class-specific savings rate

### savings_schedule:32:phi_cap -- Default phi cap for imperial rent capping
- **Rationale**: 5% cap on imperial rent extraction rate. Game balance parameter for preventing runaway extraction.
- **Labeling**: Intentional design choice -- extraction rate cap

### dispossession_dyn:30:fc_weight_la_p -- Foreclosure weight for LA-to-P transition
- **Rationale**: 60% weight for foreclosure in LA downward mobility. While Eviction Lab data exists, the specific weight allocation across transition types is a design choice.
- **Labeling**: Intentional design choice -- dispossession pathway weighting

### dispossession_dyn:31:bk_weight_la_p -- Bankruptcy weight for LA-to-P transition
- **Rationale**: 30% weight for bankruptcy. Design choice.
- **Labeling**: Intentional design choice -- dispossession pathway weighting

### dispossession_dyn:32:ev_weight_la_p -- Eviction weight for LA-to-P transition
- **Rationale**: 10% weight for eviction. Design choice.
- **Labeling**: Intentional design choice -- dispossession pathway weighting

### dispossession_dyn:33:fc_weight_p_l -- Foreclosure weight for P-to-L transition
- **Rationale**: 10% weight for foreclosure. Design choice.
- **Labeling**: Intentional design choice -- dispossession pathway weighting

### dispossession_dyn:34:bk_weight_p_l -- Bankruptcy weight for P-to-L transition
- **Rationale**: 30% weight for bankruptcy. Design choice.
- **Labeling**: Intentional design choice -- dispossession pathway weighting

### dispossession_dyn:35:ev_weight_p_l -- Eviction weight for P-to-L transition
- **Rationale**: 60% weight for eviction. Design choice -- inverts LA weights because lower classes face eviction more than foreclosure.
- **Labeling**: Intentional design choice -- dispossession pathway weighting

### accumulation:26:scf_threshold -- Fed SCF p50 net worth threshold for LA entry
- **Rationale**: While this references Fed SCF data ($142,000 p50 net worth), using it as a fixed threshold rather than a time-varying data input makes it a design choice about "labor aristocracy entry" in gameplay terms.
- **Labeling**: Intentional design choice -- class boundary threshold (Fed SCF inspired)

### tick_init:108:tau_default -- Default tau (MELT) if calculator unavailable
- **Rationale**: $62/hr fallback MELT when calculator infrastructure unavailable. Gameplay fallback for bootstrap scenarios.
- **Labeling**: Intentional design choice -- MELT fallback for infrastructure-absent scenarios

### gamma_adapters:56:HOURS_PER_YEAR -- Standard annual work hours
- **Rationale**: 2080 = 40 hrs/week * 52 weeks. Standard BLS convention, but using it as a fixed constant rather than varying is a design choice.
- **Labeling**: Intentional design choice -- standard annual hours (BLS convention)

### savings_schedule:20:HOURS_PER_YEAR -- Standard annual work hours (duplicate)
- **Rationale**: Same 2080 constant duplicated in savings_schedule. BLS convention.
- **Labeling**: Intentional design choice -- standard annual hours (should be deduplicated)

### derived_rates:23:ANNUAL_HOURS -- Standard annual work hours (another duplicate)
- **Rationale**: Same 2080 constant in derived_rates. BLS convention.
- **Labeling**: Intentional design choice -- standard annual hours (should be deduplicated)

### reproduction:63:externalization -- Reproduction externalization factor
- **Rationale**: 0.2 Meillassoux heuristic for reproductive labor externalization. No federal data tracks this; theoretical/game design choice from Meillassoux (1981).
- **Labeling**: Intentional design choice -- reproductive labor theory parameter

### basket_vis:22:MVP_ALPHA -- Import share per Hickel et al.
- **Rationale**: 0.25 import share for basket visibility MVP. Sourced from Hickel et al. academic literature, not federal data.
- **Labeling**: Intentional design choice -- MVP placeholder (literature-sourced, to be replaced by Census Trade derivation)

### basket_vis:23:MVP_GAMMA_IMPORT -- Trade-weighted average ERDI
- **Rationale**: 0.35 MVP gamma_import. MVP placeholder to be replaced by PWT data derivation.
- **Labeling**: Intentional design choice -- MVP placeholder

### basket_vis:24:MVP_GAMMA_BASKET -- Computed basket visibility
- **Rationale**: 0.68 MVP gamma_basket. Computed from MVP_ALPHA and MVP_GAMMA_IMPORT; to be replaced by full gamma pipeline.
- **Labeling**: Intentional design choice -- MVP placeholder

### dispossession_events:91:scale_factor -- Scale factor for value transfer from intensity
- **Rationale**: 0.01 scale converting dispossession intensity to actual value transfer. No data source; gameplay magnitude calibration.
- **Labeling**: Intentional design choice -- dispossession value transfer scaling

---

## Cross-References

- **Bourgeoisie cluster**: `economy.pool_high_threshold`, `economy.pool_low_threshold`, `economy.pool_critical_threshold`, `economy.bribery_wage_delta`, `economy.austerity_wage_delta`, `economy.iron_fist_repression_delta`, `economy.crisis_wage_delta`, `economy.crisis_repression_delta`, `economy.bribery_tension_threshold`, `economy.iron_fist_tension_threshold` -- see `constants-bourgeoisie-cluster.md`
- **Territory cluster**: `territory.*` (12 constants) -- see `constants-territory-cluster.md`
- **Feature 002 dependencies**: `territory.heat_decay_rate`, `territory.high_profile_heat_gain`, `territory.eviction_heat_threshold`, `territory.heat_spillover_rate` are Tier A pending Feature 002 implementation
- **Feature 021 dependencies**: `reserve_army.sigmoid_k`, `reserve_army.sigmoid_r0`, `reserve_army.wage_pressure_ceiling`, `reserve_army.min_employed_fraction` are Tier A pending Feature 021 implementation
- **FRED-fitted ODE coefficients**: `class_dynamics:58-71` (10 constants) are Tier A with FRED provenance
- **Dynamic balance duplicates**: All 10 `dynamic_balance:*` inline literals are Tier B (exact duplicates of GameDefines)
- **Topology monitor deprecated**: 7 deprecated module constants are Tier B
- **Endgame detector deprecated**: 5 deprecated module constants are Tier B

---

## Validation

**Total constants classified**: 37 (A) + 34 (B) + 72 (C) + 14 (D) + 90 (E) = **247**

This matches the inventory total of 247 constants (136 GameDefines + 2 FormulaConstants + 109 inline).

## Methodology Notes

1. **Tier A assessment** used three criteria: (a) existing infrastructure in `src/babylon/economics/` that can compute the value, (b) planned infrastructure in Feature 002/021 specs with documented derivation paths, (c) FRED-fitted coefficients with documented data provenance.

2. **Tier B assessment** used two criteria: (a) zero consumers AND no fallback role (dead code), (b) exact value duplication of a GameDefines field with identical semantics (deprecated duplicate).

3. **Tier D assessment**: purpose is purely to prevent computational errors (division by zero, overflow, precision, noise filtering), and the value has no theoretical or gameplay meaning.

4. **Tier E assessment**: the concept being measured has no federal data source that tracks it (e.g., "class consciousness sensitivity"), OR the mapping from real data to game value requires subjective interpretation that cannot be automated (e.g., savings rates by Marxian class), OR the value controls narrative pacing/event frequency with no empirical anchor.

5. **Tier C (catch-all)** received constants that have theoretical meaning AND a plausible calibration path via parameter sweep, but do not fit A (no derivation infrastructure), B (not dead/duplicate), D (not purely engineering), or E (has some theoretical basis beyond pure design choice).
