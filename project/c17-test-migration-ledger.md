# C1.7 — Dormant Dialectics Test-Migration Ledger

Companion to `project/06-lawverian-dialectics.md` §5 item 6. Catalogues every
one of the **224** tests in the retired `tests/unit/engine/dialectics/` suite
(14 files) that exercised the dormant `babylon.engine.dialectics` package, with
the behavioural intent each pinned and its disposition under the Lawverian
rewrite.

## Why almost everything is obsolete-by-design

The dormant package implemented a **different contradiction architecture** that
the contract retires wholesale:

- a `Dialectic[A, B]` base primitive — two typed poles plus a scalar `weight`
  ∈ [−1, 1] and `step()` / `observe()` / `invariants()` / `sublate()`;
- a `World` of dialectics wired by typed `Morphism` edges + `WorldEvent`s;
- a pure `tick()` stepping function and a `SublationRule` Aufhebung lifecycle;
- a `DialecticRegistry` type registry (JSONB deserialization for the retired
  `/v2` web surface — see scope B);
- ~19 concrete dialectics wrapping the `babylon.economics` Capital kernels
  (Commodity, Production, Wage, Accumulation, Circulation, TRPF, Credit, …).

Contract §3 + §5 replace the scalar `weight` model with the
`OppositionRegistry`'s measured **gap / rate / leading_pole**, mapped onto the
**existing** `Contradiction` model (§3: "do NOT duplicate it"). §9.2 explicitly
**defers** the composition algebra, the typed coupling graph (the `Morphism`
relations), and the sublation lineage (`parent_id → successor_id`,
Class→Party containment) as future amendments — "deferred OK, record now". §7
places levels + Aufhebung (the `SublationRule` machinery) in **Phase E**.

So the default disposition is **OBSOLETE** (architecture retired). Individual
behavioural intents that survive in the registry are upgraded to **COVERED**
(an existing new test pins the same behaviour) or **MIGRATED** (an equivalent
test written this session).

## Disposition counts

| Disposition | Count   | Meaning                                                  |
| ----------- | ------- | -------------------------------------------------------- |
| COVERED     | 17      | Intent already pinned by a new suite (test named below). |
| MIGRATED    | 20      | Equivalent written this session (→ 22 new tests).        |
| OBSOLETE    | 187     | Behaviour deliberately retired (contract section cited). |
| **Total**   | **224** | All dormant tests accounted for.                         |

**Migrated realisation (20 dormant intents → 22 new tests):**

- 15 `economics.value` pole-validation intents → `tests/unit/economics/test_value.py`
  (15 tests). The four pole types (`UseValue`, `ExchangeValue`, `ConcreteLabor`,
  `AbstractLabor`) live on in `babylon.economics.value` and had **no other
  coverage**; migrating preserves it. (`babylon.economics.value` is now
  orphaned by production code — flagged for the owner, not deleted: out of
  scope.)
- 5 Grundrisse cyclical-arc intents → `tests/integration/test_grundrisse_cycle.py`
  (7 tests): multi-tick step, gap/rate evolution, previous-tick reading
  (Picard fixed point), principal selection, rupture gating (§9.4).

## Legend for covering / migrated tests

- **OR** = `tests/unit/dialectics/test_opposition_registry.py`
- **CS** = `tests/unit/engine/systems/test_contradiction_system.py`
- **VAL** = `tests/unit/economics/test_value.py` (written this session)
- **GC** = `tests/integration/test_grundrisse_cycle.py` (written this session)

## test_base.py (25) — the retired `Dialectic[A, B]` primitive

| Test                                                                  | Intent                                 | Disposition                                                                       |
| --------------------------------------------------------------------- | -------------------------------------- | --------------------------------------------------------------------------------- |
| TestDialecticConstruction::test_construct_with_valid_poles_and_weight | Build a dialectic from poles + weight. | OBSOLETE (§5.6: primitive retired; new identity = `OppositionSpec`)               |
| TestDialecticConstruction::test_id_is_uuid                            | `.id` is a UUID.                       | OBSOLETE (§5.6)                                                                   |
| TestDialecticConstruction::test_id_unique_per_instance                | UUIDs unique per instance.             | OBSOLETE (§5.6)                                                                   |
| TestDialecticConstruction::test_explicit_id_preserved                 | Explicit id kept.                      | OBSOLETE (§5.6)                                                                   |
| TestDialecticConstruction::test_parent_id_default_none                | `parent_id` defaults None.             | OBSOLETE (§9.2: sublation lineage deferred)                                       |
| TestDialecticConstruction::test_parent_id_tracks_lineage              | `parent_id` records lineage.           | OBSOLETE (§9.2: sublation lineage deferred)                                       |
| TestDialecticConstruction::test_type_tag_set_by_subclass              | Subclass sets `type_tag`.              | OBSOLETE (§5.6)                                                                   |
| TestDialecticImmutability::test_frozen_weight_mutation_raises         | Frozen weight raises.                  | OBSOLETE (§5.6; frozen carries into `OppositionState`/`Spec`)                     |
| TestDialecticImmutability::test_frozen_pole_mutation_raises           | Frozen pole raises.                    | OBSOLETE (§5.6; frozen carries structurally)                                      |
| TestDialecticWeightBounds::test_weight_zero_valid                     | weight 0 valid.                        | COVERED (OR::TestValidation::test_gap_reading_bounds_enforced — Balance ∈ [−1,1]) |
| TestDialecticWeightBounds::test_weight_one_valid                      | weight 1 valid.                        | COVERED (OR::test_gap_reading_bounds_enforced)                                    |
| TestDialecticWeightBounds::test_weight_negative_one_valid             | weight −1 valid.                       | COVERED (OR::test_gap_reading_bounds_enforced)                                    |
| TestDialecticWeightBounds::test_weight_below_negative_one_raises      | weight < −1 raises.                    | COVERED (OR::test_gap_reading_bounds_enforced)                                    |
| TestDialecticWeightBounds::test_weight_above_one_raises               | weight > 1 raises.                     | COVERED (OR::test_gap_reading_bounds_enforced)                                    |
| TestDialecticStep::test_step_returns_new_instance                     | step returns new instance.             | OBSOLETE (§5.6; determinism → OR::test_purity)                                    |
| TestDialecticStep::test_step_preserves_id                             | step preserves id.                     | OBSOLETE (§5.6)                                                                   |
| TestDialecticSublation::test_default_sublate_returns_none             | default sublate None.                  | OBSOLETE (§7 Phase E / §9.2)                                                      |
| TestDialecticObservation::test_observe_returns_dict                   | observe returns dict.                  | OBSOLETE (§9.2: observation-relativity deferred)                                  |
| TestDialecticObservation::test_observe_principal_aspect_a             | weight < 0 → aspect A.                 | COVERED (OR::TestLeadingPole::test_sign_of_balance_selects_pole)                  |
| TestDialecticObservation::test_observe_principal_aspect_b             | weight > 0 → aspect B.                 | COVERED (OR::TestLeadingPole::test_sign_of_balance_selects_pole)                  |
| TestDialecticObservation::test_observe_includes_id                    | observe carries id.                    | OBSOLETE (§9.2)                                                                   |
| TestDialecticInvariants::test_default_invariants_empty                | base invariants empty.                 | OBSOLETE (invariants now in tests/property specs 053–060)                         |
| TestTickInputsAndWorldView::test_tick_inputs_construction             | Build `TickInputs`.                    | OBSOLETE (§5.6; new input carrier = `GraphInputs`)                                |
| TestTickInputsAndWorldView::test_world_view_construction              | Build `WorldView`.                     | OBSOLETE (§5.6)                                                                   |
| TestTickInputsAndWorldView::test_world_view_provides_read_access      | WorldView read access.                 | OBSOLETE (§5.6)                                                                   |

## test_world.py (15) — `World` / `Morphism` / `WorldEvent`

| Test                                                        | Intent                                            | Disposition                                           |
| ----------------------------------------------------------- | ------------------------------------------------- | ----------------------------------------------------- |
| TestMorphism::test_construction                             | Build a typed morphism.                           | OBSOLETE (§9.2: typed coupling graph deferred)        |
| TestMorphism::test_valid_relations                          | feeds/constrains/transforms/contains/antagonizes. | OBSOLETE (§9.2: typed morphisms deferred)             |
| TestMorphism::test_has_id                                   | morphism has id.                                  | OBSOLETE (§9.2)                                       |
| TestWorldEvent::test_construction                           | Build a WorldEvent.                               | OBSOLETE (§5.6; events now via EventBus/EventType)    |
| TestWorldEvent::test_narrative_optional                     | narrative optional.                               | OBSOLETE (§5.6)                                       |
| TestWorldEvent::test_narrative_present                      | narrative present.                                | OBSOLETE (§5.6)                                       |
| TestWorldConstruction::test_empty_world                     | empty World.                                      | OBSOLETE (§5.6; container retired)                    |
| TestWorldConstruction::test_world_with_dialectics           | World holds dialectics.                           | OBSOLETE (§5.6)                                       |
| TestWorldConstruction::test_world_with_morphisms            | World holds morphisms.                            | OBSOLETE (§9.2)                                       |
| TestWorldGetByType::test_get_by_type_returns_matching       | Filter by type_tag.                               | OBSOLETE (§5.6; lookup = `registry.spec_for`/`keys`)  |
| TestWorldGetByType::test_get_by_type_empty_for_unknown      | Unknown type → empty.                             | OBSOLETE (§5.6)                                       |
| TestWorldGetInputsFor::test_inputs_from_feeds_morphism      | Inputs from morphism graph.                       | OBSOLETE (§9.2; inputs = pre-extracted `GraphInputs`) |
| TestWorldGetInputsFor::test_no_inputs_when_no_morphisms     | No morphisms → no inputs.                         | OBSOLETE (§9.2)                                       |
| TestWorldGetLiveDialectics::test_all_live_when_no_sublation | All live w/o sublation.                           | OBSOLETE (§9.2: sublation lineage deferred)           |
| TestWorldGetLiveDialectics::test_sublated_excluded          | Sublated predecessors excluded.                   | OBSOLETE (§9.2)                                       |

## test_tick.py (7) — the pure `tick()` function

| Test                                                           | Intent                       | Disposition                                                                                          |
| -------------------------------------------------------------- | ---------------------------- | ---------------------------------------------------------------------------------------------------- |
| TestTickFunction::test_empty_world_increments_tick             | tick increments empty world. | OBSOLETE (§5.6; engine drives ticks)                                                                 |
| TestTickFunction::test_steps_all_dialectics                    | Every dialectic stepped.     | COVERED (CS::TestRegistryStash::test_opposition_states_written_to_graph_attr — all bindings stepped) |
| TestTickFunction::test_deterministic                           | Same inputs → same outputs.  | COVERED (OR::TestStep::test_purity)                                                                  |
| TestTickFunction::test_morphism_feeds_input                    | feeds morphism plumbs input. | OBSOLETE (§9.2)                                                                                      |
| TestTickFunction::test_invariant_violations_recorded_as_events | Violations → events.         | OBSOLETE (§5.6; invariants in tests/property)                                                        |
| TestTickFunction::test_world_tick_incremented                  | tick counter advances.       | OBSOLETE (§5.6)                                                                                      |
| TestTickSublation::test_no_sublation_preserves_all             | No sublation preserves all.  | OBSOLETE (§7 / §9.2)                                                                                 |

## test_core_abstractions.py (12) — WorldView.previous / get_one_or_none / find_successor

| Test                                                                 | Intent                       | Disposition                                                                                                                   |
| -------------------------------------------------------------------- | ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| TestWorldViewPrevious::test_previous_defaults_to_none                | previous defaults None.      | COVERED (CS::TestRegistryStash::test_rate_carried_across_ticks_via_graph_attr; GC::test_rate_is_gap_delta_from_previous_tick) |
| TestWorldViewPrevious::test_previous_carries_prior_state             | previous carries prior tick. | COVERED (CS::test_rate_carried_across_ticks_via_graph_attr)                                                                   |
| TestWorldViewPrevious::test_previous_is_read_only                    | previous frozen.             | COVERED (CS::test_rate_carried_across_ticks_via_graph_attr — snapshot dict is re-read, not mutated)                           |
| TestWorldGetOneOrNone::test_returns_dialectic_when_one_exists        | get_one_or_none hit.         | OBSOLETE (§5.6; lookup = `registry.spec_for`)                                                                                 |
| TestWorldGetOneOrNone::test_returns_none_when_none_exist             | get_one_or_none miss.        | OBSOLETE (§5.6)                                                                                                               |
| TestWorldGetOneOrNone::test_returns_first_when_multiple_exist        | get_one_or_none first.       | OBSOLETE (§5.6)                                                                                                               |
| TestWorldViewFindSuccessor::test_returns_none_when_no_successor      | No successor → None.         | OBSOLETE (§9.2: lineage deferred)                                                                                             |
| TestWorldViewFindSuccessor::test_finds_successor_by_parent_id        | Find successor by parent_id. | OBSOLETE (§9.2)                                                                                                               |
| TestWorldViewFindSuccessor::test_returns_none_when_id_not_found      | Missing id → None.           | OBSOLETE (§9.2)                                                                                                               |
| TestTickStepsAllDialectics::test_sublated_dialectic_still_stepped    | Sublated still stepped.      | OBSOLETE (§9.2: sublation-containment deferred)                                                                               |
| TestTickStepsAllDialectics::test_sublated_and_live_both_stepped      | Both advance.                | OBSOLETE (§9.2)                                                                                                               |
| TestTickPassesPreviousWorldView::test_worldview_has_previous_in_step | step sees previous.          | COVERED (GC::test_rate_is_gap_delta_from_previous_tick)                                                                       |

## test_grundrisse_cycle.py (13) — the 4-cycle arc (migrated to GC)

| Test                                                                                      | Intent                             | Disposition                                                                                                                                             |
| ----------------------------------------------------------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TestGrundrisseCycle::test_cycle_runs_10_ticks_without_violations                          | 10-tick arc, no pathology.         | MIGRATED (GC::TestGrundrisseArc::test_ten_tick_cycle_keeps_five_oppositions_and_one_principal + test_gap_develops_and_stays_off_the_saturating_ceiling) |
| TestGrundrisseCycle::test_all_dialectics_stepped_each_tick                                | All stepped each tick.             | MIGRATED (GC::test_ten_tick_cycle_keeps_five_oppositions_and_one_principal)                                                                             |
| TestGrundrisseCycle::test_cycle_reaches_consistent_state                                  | Bounded / convergent.              | MIGRATED (GC::test_gap_develops_and_stays_off_the_saturating_ceiling — bounded, non-saturating)                                                         |
| TestGrundrisseCycle::test_production_reads_previous_consumption                           | Reads prior tick (fixed point).    | MIGRATED (GC::TestNonRatchetAndPreviousReading::test_rate_is_gap_delta_from_previous_tick)                                                              |
| TestGrundrisseCycle::test_worldview_previous_populated                                    | previous threaded across ticks.    | MIGRATED (GC::test_rate_is_gap_delta_from_previous_tick)                                                                                                |
| TestProductionReadsConsumption::test_production_reads_prior_mp_renewed                    | Production reads consumption obs.  | OBSOLETE (§5.6; economics kernels covered in tests/unit/economics)                                                                                      |
| TestProductionReadsConsumption::test_production_step_uses_previous_world                  | No violations over 2 ticks.        | OBSOLETE (§5.6)                                                                                                                                         |
| TestConsumptionEmitsRenewalOutputs::test_consumption_observe_includes_mp_renewed          | observe emits mp_renewed.          | OBSOLETE (§5.6; dialectic observe() plumbing retired)                                                                                                   |
| TestConsumptionEmitsRenewalOutputs::test_consumption_observe_includes_labor_power_renewed | observe emits labor_power_renewed. | OBSOLETE (§5.6)                                                                                                                                         |
| TestDistributionEmitsOutputs::test_distribution_observe_includes_wages                    | observe emits wages_paid.          | OBSOLETE (§5.6)                                                                                                                                         |
| TestDistributionEmitsOutputs::test_distribution_observe_includes_surplus_distributed      | observe emits surplus.             | OBSOLETE (§5.6)                                                                                                                                         |
| TestCirculationEmitsOutputs::test_circulation_observe_includes_total_capital              | observe emits total_capital.       | OBSOLETE (§5.6)                                                                                                                                         |
| TestCirculationEmitsOutputs::test_circulation_observe_includes_realized_money             | observe emits realized_money.      | OBSOLETE (§5.6)                                                                                                                                         |

## test_registry.py (6) — `DialecticRegistry` (JSONB type registry)

| Test                                                      | Intent                         | Disposition                                                  |
| --------------------------------------------------------- | ------------------------------ | ------------------------------------------------------------ |
| TestDialecticRegistry::test_register_and_lookup           | Register + lookup a class.     | OBSOLETE (§5.6/scope B; was for `/v2` JSONB deserialization) |
| TestDialecticRegistry::test_lookup_unknown_raises         | Unknown tag raises.            | OBSOLETE (§5.6)                                              |
| TestDialecticRegistry::test_duplicate_registration_raises | Duplicate registration raises. | COVERED (OR::TestValidation::test_duplicate_keys_rejected)   |
| TestDialecticRegistry::test_registered_types              | List registered types.         | OBSOLETE (§5.6)                                              |
| TestDialecticRegistry::test_empty_registry                | Empty registry.                | OBSOLETE (§5.6)                                              |
| TestDialecticRegistry::test_default_registry_includes_v1  | Default registry has V1.       | OBSOLETE (§5.6)                                              |

## test_sublation_rule.py (11) — `SublationRule` (Aufhebung → Phase E)

| Test                                                                     | Intent                          | Disposition                           |
| ------------------------------------------------------------------------ | ------------------------------- | ------------------------------------- |
| TestSublationRuleConstruction::test_construct_with_weight_threshold      | Build rule w/ weight threshold. | OBSOLETE (§7 Phase E)                 |
| TestSublationRuleConstruction::test_construct_with_custom_predicate      | Build rule w/ custom predicate. | OBSOLETE (§7 Phase E)                 |
| TestSublationThreshold::test_below_threshold_returns_false               | Below threshold → False.        | OBSOLETE (§7 Phase E)                 |
| TestSublationThreshold::test_above_threshold_returns_true                | Above threshold → True.         | OBSOLETE (§7 Phase E)                 |
| TestSublationSuccessorFactory::test_successor_has_parent_id              | Successor wired to parent.      | OBSOLETE (§9.2: lineage deferred)     |
| TestSublationSuccessorFactory::test_successor_type_matches               | Successor type correct.         | OBSOLETE (§7 Phase E)                 |
| TestDialecticDelegatesToRule::test_no_rules_returns_none                 | No rules → None.                | OBSOLETE (§7 Phase E)                 |
| TestDialecticDelegatesToRule::test_rule_triggers_sublation               | Rule triggers sublation.        | OBSOLETE (§7 Phase E)                 |
| TestDialecticDelegatesToRule::test_first_matching_rule_wins              | First match wins.               | OBSOLETE (§7 Phase E)                 |
| TestSublationRuleInTick::test_tick_triggers_sublation_via_rule           | tick fires sublation event.     | OBSOLETE (§7 Phase E)                 |
| TestSublationRuleInTick::test_sublated_dialectic_still_stepped_with_rule | Sublated still stepped.         | OBSOLETE (§9.2: containment deferred) |

## test_invariants_v2.py (4) — `check_universal` / `check_all_invariants`

| Test                                                             | Intent                 | Disposition                                               |
| ---------------------------------------------------------------- | ---------------------- | --------------------------------------------------------- |
| TestCheckUniversalInvariants::test_valid_dialectic_no_violations | Valid dialectic clean. | OBSOLETE (invariants now in tests/property specs 053–060) |
| TestCheckUniversalInvariants::test_weight_at_boundary_valid      | Weight boundary valid. | COVERED (OR::test_gap_reading_bounds_enforced)            |
| TestCheckAllInvariants::test_valid_world_no_violations           | Valid World clean.     | OBSOLETE (§5.6)                                           |
| TestCheckAllInvariants::test_empty_world_no_violations           | Empty World clean.     | OBSOLETE (§5.6)                                           |

## test_consciousness.py (2) — `ClassConsciousnessDialectic`

| Test                                        | Intent                         | Disposition                                                             |
| ------------------------------------------- | ------------------------------ | ----------------------------------------------------------------------- |
| test_consciousness_equilibrium              | r/l/f still without agitation. | OBSOLETE (§5.6; ConsciousnessSystem + ternary formulas retain coverage) |
| test_consciousness_agitation_and_solidarity | Agitation+solidarity → r.      | OBSOLETE (§5.6; §8 crisis-gating owned by ConsciousnessSystem)          |

## test_commodity.py (18) — `CommodityDialectic` + economics.value poles

| Test                                                                     | Intent                    | Disposition                                                                                                |
| ------------------------------------------------------------------------ | ------------------------- | ---------------------------------------------------------------------------------------------------------- |
| TestUseValue::test_default_construction                                  | UseValue defaults.        | MIGRATED (VAL::TestUseValue::test_default_construction)                                                    |
| TestUseValue::test_custom_values                                         | UseValue custom.          | MIGRATED (VAL::TestUseValue::test_custom_values)                                                           |
| TestUseValue::test_utility_bounded_0_1                                   | utility ∈ [0,1].          | MIGRATED (VAL::TestUseValue::test_utility_bounded_0_1)                                                     |
| TestExchangeValue::test_default_construction                             | ExchangeValue defaults.   | MIGRATED (VAL::TestExchangeValue::test_default_construction)                                               |
| TestExchangeValue::test_custom_values                                    | ExchangeValue custom.     | MIGRATED (VAL::TestExchangeValue::test_custom_values)                                                      |
| TestExchangeValue::test_snlt_non_negative                                | snlt ≥ 0.                 | MIGRATED (VAL::TestExchangeValue::test_snlt_non_negative)                                                  |
| TestExchangeValue::test_price_non_negative                               | price ≥ 0.                | MIGRATED (VAL::TestExchangeValue::test_price_non_negative)                                                 |
| TestCommodityDialecticConstruction::test_type_tag                        | Commodity type_tag.       | OBSOLETE (§5.6)                                                                                            |
| TestCommodityDialecticConstruction::test_poles_accessible                | Poles accessible.         | OBSOLETE (§5.6)                                                                                            |
| TestCommodityDialecticStep::test_production_input_shifts_toward_exchange | Production → exchange.    | OBSOLETE (§5.6; use/exchange not a Phase-C bound opposition)                                               |
| TestCommodityDialecticStep::test_consumption_input_shifts_toward_use     | Consumption → use.        | OBSOLETE (§5.6)                                                                                            |
| TestCommodityDialecticStep::test_no_input_preserves_weight               | No input → unchanged.     | COVERED (CS::TestFreshEdgeTension::test_tension_is_not_accumulated_across_ticks — static graph idempotent) |
| TestCommodityDialecticStep::test_step_updates_tick_updated               | step advances tick.       | OBSOLETE (§5.6)                                                                                            |
| TestCommodityDialecticStep::test_weight_clamped_at_negative_one          | Clamp ≥ −1.               | COVERED (OR::test_gap_reading_bounds_enforced)                                                             |
| TestCommodityDialecticStep::test_weight_clamped_at_positive_one          | Clamp ≤ 1.                | COVERED (OR::test_gap_reading_bounds_enforced)                                                             |
| TestCommodityDialecticObserve::test_observe_includes_commodity_fields    | observe commodity fields. | OBSOLETE (§5.6)                                                                                            |
| TestCommodityDialecticSublation::test_sublate_returns_none               | Commodity no sublate.     | OBSOLETE (§7 Phase E)                                                                                      |
| TestCommodityDialecticInvariants::test_valid_state_no_violations         | Valid state clean.        | OBSOLETE (§5.6)                                                                                            |

## test_production.py (62) — V1 production dialectics + economics.value labor poles

| Test                                                                       | Intent                       | Disposition                                                                                                |
| -------------------------------------------------------------------------- | ---------------------------- | ---------------------------------------------------------------------------------------------------------- |
| TestConcreteLabor::test_default_construction                               | ConcreteLabor defaults.      | MIGRATED (VAL::TestConcreteLabor::test_default_construction)                                               |
| TestConcreteLabor::test_custom_values                                      | ConcreteLabor custom.        | MIGRATED (VAL::TestConcreteLabor::test_custom_values)                                                      |
| TestConcreteLabor::test_skill_bounded                                      | skill ∈ [0,1].               | MIGRATED (VAL::TestConcreteLabor::test_skill_bounded)                                                      |
| TestConcreteLabor::test_intensity_bounded                                  | intensity ∈ [0,1].           | MIGRATED (VAL::TestConcreteLabor::test_intensity_bounded)                                                  |
| TestAbstractLabor::test_default_construction                               | AbstractLabor defaults.      | MIGRATED (VAL::TestAbstractLabor::test_default_construction)                                               |
| TestAbstractLabor::test_custom_values                                      | AbstractLabor custom.        | MIGRATED (VAL::TestAbstractLabor::test_custom_values)                                                      |
| TestAbstractLabor::test_snlt_non_negative                                  | snlt ≥ 0.                    | MIGRATED (VAL::TestAbstractLabor::test_snlt_non_negative)                                                  |
| TestAbstractLabor::test_productivity_must_be_positive                      | productivity > 0.            | MIGRATED (VAL::TestAbstractLabor::test_productivity_must_be_positive)                                      |
| TestLaborProcessDialectic::test_type_tag                                   | LaborProcess type_tag.       | OBSOLETE (§5.6)                                                                                            |
| TestLaborProcessDialectic::test_step_returns_same_type                     | step returns same type.      | OBSOLETE (§5.6)                                                                                            |
| TestLaborProcessDialectic::test_no_input_identity                          | No input identity.           | OBSOLETE (§5.6)                                                                                            |
| TestLaborProcessDialectic::test_tick_updated                               | tick advances.               | OBSOLETE (§5.6)                                                                                            |
| TestLaborProcessDialectic::test_competitive_pressure_shifts_positive       | Competitive pressure → +.    | OBSOLETE (§5.6)                                                                                            |
| TestLaborProcessDialectic::test_weight_clamped_positive                    | Clamp ≤ 1.                   | COVERED (OR::test_gap_reading_bounds_enforced)                                                             |
| TestLaborProcessDialectic::test_weight_clamped_negative                    | Clamp ≥ −1.                  | COVERED (OR::test_gap_reading_bounds_enforced)                                                             |
| TestLaborProcessDialectic::test_observe_includes_labor_fields              | observe labor fields.        | OBSOLETE (§5.6)                                                                                            |
| TestProductionDialectic::test_type_tag                                     | Production type_tag.         | OBSOLETE (§5.6)                                                                                            |
| TestProductionDialectic::test_step_returns_same_type                       | step returns same type.      | OBSOLETE (§5.6)                                                                                            |
| TestProductionDialectic::test_ch9_surplus_value_formula                    | s = v·e.                     | OBSOLETE (§5.6; economics.tensor/formulas cover s=v·e)                                                     |
| TestProductionDialectic::test_ch8_value_conservation                       | c+v+s conservation.          | OBSOLETE (§5.6; tests/unit/economics + tests/property conservation)                                        |
| TestProductionDialectic::test_ch9_yarn_example                             | Marx yarn example.           | OBSOLETE (§5.6)                                                                                            |
| TestProductionDialectic::test_observe_returns_value_tensor                 | observe [l,c,v,s,r].         | OBSOLETE (§5.6; value tensor covered in tests/unit/economics/tensor)                                       |
| TestProductionDialectic::test_observe_organic_composition                  | OCC = c/v.                   | OBSOLETE (§5.6; formulas/trpf covers OCC)                                                                  |
| TestProductionDialectic::test_invariant_surplus_non_negative               | s ≥ 0.                       | OBSOLETE (§5.6)                                                                                            |
| TestProductionDialectic::test_step_updates_weight                          | High e → weight +.           | OBSOLETE (§5.6)                                                                                            |
| TestValueOfLaborPower::test_default_construction                           | Pole defaults.               | OBSOLETE (§5.6; pole lives in retired volume_1)                                                            |
| TestValueOfLaborPower::test_custom_values                                  | Pole custom.                 | OBSOLETE (§5.6)                                                                                            |
| TestPriceOfLaborPower::test_default_construction                           | Pole defaults.               | OBSOLETE (§5.6)                                                                                            |
| TestPriceOfLaborPower::test_custom_values                                  | Pole custom.                 | OBSOLETE (§5.6)                                                                                            |
| TestPriceOfLaborPower::test_relative_wage_bounded                          | relative_wage ∈ [0,1].       | OBSOLETE (§5.6)                                                                                            |
| TestWageDialectic::test_type_tag                                           | Wage type_tag.               | OBSOLETE (§5.6)                                                                                            |
| TestWageDialectic::test_step_returns_same_type                             | step returns same type.      | OBSOLETE (§5.6)                                                                                            |
| TestWageDialectic::test_ch19_value_neq_price                               | value ≠ price of labor.      | OBSOLETE (§5.6; wage opposition rebinds Phase D §6)                                                        |
| TestWageDialectic::test_reserve_army_shifts_weight_positive                | Reserve army → +.            | OBSOLETE (§5.6; ReserveArmySystem owns this)                                                               |
| TestWageDialectic::test_negative_weight_is_buy_market                      | weight < 0 → A.              | COVERED (OR::TestLeadingPole::test_sign_of_balance_selects_pole)                                           |
| TestWageDialectic::test_positive_weight_is_sell_market                     | weight > 0 → B.              | COVERED (OR::TestLeadingPole::test_sign_of_balance_selects_pole)                                           |
| TestWageDialectic::test_observe_includes_wage_fields                       | observe wage fields.         | OBSOLETE (§5.6)                                                                                            |
| TestConcentrationOfCapital::test_default_construction                      | Pole defaults.               | OBSOLETE (§5.6)                                                                                            |
| TestConcentrationOfCapital::test_custom_values                             | Pole custom.                 | OBSOLETE (§5.6)                                                                                            |
| TestReserveArmyExpansion::test_default_construction                        | Pole defaults.               | OBSOLETE (§5.6)                                                                                            |
| TestReserveArmyExpansion::test_custom_values                               | Pole custom.                 | OBSOLETE (§5.6)                                                                                            |
| TestAccumulationDialectic::test_type_tag                                   | Accumulation type_tag.       | OBSOLETE (§5.6)                                                                                            |
| TestAccumulationDialectic::test_step_returns_same_type                     | step returns same type.      | OBSOLETE (§5.6)                                                                                            |
| TestAccumulationDialectic::test_observe_includes_reserve_army_fields       | observe reserve-army fields. | OBSOLETE (§5.6)                                                                                            |
| TestAccumulationDialectic::test_rising_occ_displaces_workers               | Rising OCC displaces.        | OBSOLETE (§5.6; ReserveArmySystem/DecompositionSystem)                                                     |
| TestAccumulationDialectic::test_no_input_identity                          | No input identity.           | OBSOLETE (§5.6)                                                                                            |
| TestColonialExpropriation::test_default_construction                       | Pole defaults.               | OBSOLETE (§5.6)                                                                                            |
| TestColonialExpropriation::test_custom_values                              | Pole custom.                 | OBSOLETE (§5.6)                                                                                            |
| TestColonialExpropriation::test_expropriation_rate_bounded                 | rate ∈ [0,1].                | OBSOLETE (§5.6)                                                                                            |
| TestSettlerFormation::test_default_construction                            | Pole defaults.               | OBSOLETE (§5.6)                                                                                            |
| TestSettlerFormation::test_custom_values                                   | Pole custom.                 | OBSOLETE (§5.6)                                                                                            |
| TestSettlerFormation::test_labor_aristocracy_above_one_is_valid            | LAR > 1 valid.               | OBSOLETE (§5.6; formulas/fundamental_theorem covers LAR)                                                   |
| TestPrimitiveAccumulationDialectic::test_type_tag                          | PrimAccum type_tag.          | OBSOLETE (§5.6)                                                                                            |
| TestPrimitiveAccumulationDialectic::test_step_returns_same_type            | step returns same type.      | OBSOLETE (§5.6)                                                                                            |
| TestPrimitiveAccumulationDialectic::test_observe_includes_settler_fields   | observe settler fields.      | OBSOLETE (§5.6)                                                                                            |
| TestPrimitiveAccumulationDialectic::test_negative_weight_is_raw_violence   | weight < 0 → A.              | COVERED (OR::TestLeadingPole::test_sign_of_balance_selects_pole)                                           |
| TestPrimitiveAccumulationDialectic::test_positive_weight_is_mature_settler | weight > 0 → B.              | COVERED (OR::TestLeadingPole::test_sign_of_balance_selects_pole)                                           |
| TestPrimitiveAccumulationDialectic::test_no_input_identity                 | No input identity.           | OBSOLETE (§5.6)                                                                                            |
| TestPrimitiveAccumulationDialectic::test_weight_clamped                    | Clamp ∈ [−1,1].              | COVERED (OR::test_gap_reading_bounds_enforced)                                                             |
| TestDialecticCoupling::test_five_dialectic_world_10_ticks_no_violations    | 5-node 10-tick arc clean.    | MIGRATED (GC::TestGrundrisseArc::test_ten_tick_cycle_keeps_five_oppositions_and_one_principal)             |
| TestDialecticCoupling::test_all_weights_remain_bounded                     | Weights bounded 10 ticks.    | COVERED (OR::test_gap_reading_bounds_enforced; GC::test_gap_develops_and_stays_off_the_saturating_ceiling) |
| TestDialecticCoupling::test_all_dialectics_stepped                         | All stepped after 1 tick.    | COVERED (CS::TestRegistryStash::test_opposition_states_written_to_graph_attr)                              |

## test_higher_order.py (16) — Transformation / Class / Party (Phase E territory)

| Test                                                                | Intent                      | Disposition                                           |
| ------------------------------------------------------------------- | --------------------------- | ----------------------------------------------------- |
| TestTransformationDialectic::test_type_tag                          | Transformation type_tag.    | OBSOLETE (§5.6; value→price covered in economics)     |
| TestTransformationDialectic::test_observe_emits_average_profit_rate | observe avg profit rate.    | OBSOLETE (§5.6)                                       |
| TestTransformationDialectic::test_transform_value_to_price          | price = cost·(1+r̄).         | OBSOLETE (§5.6; §9.2 observation-relativity deferred) |
| TestTransformationDialectic::test_step_updates_tick                 | tick advances.              | OBSOLETE (§5.6)                                       |
| TestTransformationDialectic::test_step_reads_upstream_profit_rates  | Reads upstream.             | OBSOLETE (§9.2)                                       |
| TestClassDialectic::test_type_tag                                   | Class type_tag.             | OBSOLETE (§5.6)                                       |
| TestClassDialectic::test_step_advances_tick                         | tick advances.              | OBSOLETE (§5.6)                                       |
| TestClassDialectic::test_no_sublation_below_threshold               | No sublate below threshold. | OBSOLETE (§7 Phase E)                                 |
| TestClassDialectic::test_sublation_to_party                         | Class → Party.              | OBSOLETE (§9.2: Class→Party containment deferred)     |
| TestClassDialectic::test_observe_emits_consciousness_metrics        | observe consciousness.      | OBSOLETE (§5.6)                                       |
| TestClassDialectic::test_step_reads_successor_when_sublated         | Governed by successor.      | OBSOLETE (§9.2: sublation-containment deferred)       |
| TestPartyDialectic::test_type_tag                                   | Party type_tag.             | OBSOLETE (§5.6)                                       |
| TestPartyDialectic::test_step_advances_tick                         | tick advances.              | OBSOLETE (§5.6)                                       |
| TestPartyDialectic::test_observe_emits_directive                    | observe directive.          | OBSOLETE (§5.6)                                       |
| TestSublationGovernance::test_class_sublates_and_party_governs      | Sublation governance arc.   | OBSOLETE (§9.2 / §7 Phase E)                          |
| TestSublationGovernance::test_sublated_class_still_stepped          | Sublated ≠ destroyed.       | OBSOLETE (§9.2)                                       |

## test_volume_2.py (8) — Circulation / Turnover / Reproduction dialectics

| Test                                                               | Intent               | Disposition                                                                        |
| ------------------------------------------------------------------ | -------------------- | ---------------------------------------------------------------------------------- |
| TestCirculationDialectic::test_construction_and_poles              | Build + poles.       | OBSOLETE (§5.6; economics.circulation covered in tests/unit/economics/circulation) |
| TestCirculationDialectic::test_step_advances_circuit               | M→P circuit advance. | OBSOLETE (§5.6)                                                                    |
| TestCirculationDialectic::test_sublation_to_realization_crisis     | Overhang → crisis.   | OBSOLETE (§7 Phase E)                                                              |
| TestTurnoverDialectic::test_construction                           | Build turnover.      | OBSOLETE (§5.6)                                                                    |
| TestTurnoverDialectic::test_observe_yields_annual_surplus_value    | Annual S/V.          | OBSOLETE (§5.6; economics.circulation turnover covered)                            |
| TestReproductionDialectic::test_construction_and_poles             | Build + poles.       | OBSOLETE (§5.6)                                                                    |
| TestReproductionDialectic::test_step_enforces_reproduction_balance | Dept I/II balance.   | OBSOLETE (§5.6; reproduction covered in economics)                                 |
| TestReproductionDialectic::test_sublation_to_crisis                | Imbalance → crisis.  | OBSOLETE (§7 Phase E)                                                              |

## test_volume_3.py (25) — Distribution / TRPF / Credit / Rent / Imperial dialectics

| Test                                                                         | Intent                       | Disposition                                                               |
| ---------------------------------------------------------------------------- | ---------------------------- | ------------------------------------------------------------------------- |
| TestSurplusDistributionDialectic::test_construction_and_poles                | Build + poles.               | OBSOLETE (§5.6; economics.distribution covered)                           |
| TestSurplusDistributionDialectic::test_observe_emits_distribution_components | observe p/i/r/t.             | OBSOLETE (§5.6)                                                           |
| TestSurplusDistributionDialectic::test_step_shifts_weight_on_profit_squeeze  | Profit squeeze → weight.     | OBSOLETE (§5.6)                                                           |
| TestSurplusDistributionDialectic::test_invariant_accounting_identity         | s = p+i+r+t.                 | OBSOLETE (§5.6; conservation in tests/property)                           |
| TestSurplusDistributionDialectic::test_sublation_to_debt_spiral              | Claims > surplus → crisis.   | OBSOLETE (§7 Phase E)                                                     |
| TestTRPFDialectic::test_construction_and_poles                               | Build + poles.               | OBSOLETE (§5.6; formulas/trpf + economics.counter_tendencies covered)     |
| TestTRPFDialectic::test_observe_emits_net_counter_tendency                   | observe net CT.              | OBSOLETE (§5.6)                                                           |
| TestTRPFDialectic::test_step_updates_weight_from_net_ct                      | Net CT → weight.             | OBSOLETE (§5.6)                                                           |
| TestTRPFDialectic::test_no_sublation                                         | TRPF structural, no sublate. | OBSOLETE (§5.6)                                                           |
| TestCreditDialectic::test_construction_and_poles                             | Build + poles.               | OBSOLETE (§5.6; economics.credit covered)                                 |
| TestCreditDialectic::test_observe_emits_financialization_index               | observe financialization.    | OBSOLETE (§5.6)                                                           |
| TestCreditDialectic::test_step_advances_credit_state                         | Credit state advance.        | OBSOLETE (§5.6)                                                           |
| TestCreditDialectic::test_sublation_to_financial_crisis                      | Bubble → crisis.             | OBSOLETE (§7 Phase E)                                                     |
| TestCreditDialectic::test_no_sublation_below_threshold                       | Below threshold no sublate.  | OBSOLETE (§7 Phase E)                                                     |
| TestRentDialectic::test_construction_and_poles                               | Build + poles.               | OBSOLETE (§5.6; tenancy opposition covered in CS + economics.rent)        |
| TestRentDialectic::test_observe_emits_rent_components                        | observe rent components.     | OBSOLETE (§5.6)                                                           |
| TestRentDialectic::test_step_updates_weight                                  | Rent share → weight.         | OBSOLETE (§5.6)                                                           |
| TestRentDialectic::test_invariant_rent_non_negative                          | rent ≥ 0.                    | OBSOLETE (§5.6)                                                           |
| TestImperialDialectic::test_construction_and_poles                           | Build + poles.               | OBSOLETE (§5.6; imperial = null-measure spec Phase C, rebinds Phase D §6) |
| TestImperialDialectic::test_observe_emits_lar                                | observe LAR.                 | OBSOLETE (§5.6; formulas/fundamental_theorem covers LAR)                  |
| TestImperialDialectic::test_step_adjusts_weight_from_lar                     | LAR → weight.                | OBSOLETE (§5.6)                                                           |
| TestDebtSpiralCrisisDialectic::test_construction                             | Build crisis.                | OBSOLETE (§7 Phase E)                                                     |
| TestDebtSpiralCrisisDialectic::test_step_passthrough                         | step passthrough.            | OBSOLETE (§7 Phase E)                                                     |
| TestFinancialCrisisDialectic::test_construction                              | Build crisis.                | OBSOLETE (§7 Phase E)                                                     |
| TestFinancialCrisisDialectic::test_step_passthrough                          | step passthrough.            | OBSOLETE (§7 Phase E)                                                     |
