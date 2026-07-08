# Verified task tables for specs 031/032/033/034 (produced 2026-07-08 by verification agent; apply mechanically)

All task lines in all four files were `- [ ]` (unchecked); each verdict below was verified against code in the worktree.

## 031-organization-base-model — tally: done 34 / partial 1

T001 DONE src/babylon/organizations/__init__.py + tests/unit/organizations/conftest.py
T002 DONE tests/unit/organizations/test_enums.py:23
T003 DONE src/babylon/models/enums/social.py:86
T004 DONE src/babylon/organizations/types.py:15
T005 DONE src/babylon/config/defines/organizations.py:376 (registered defines/_assembler.py:160)
T006 PARTIAL — defines.yaml removed in refactor; org section YAML-loadable + Python defaults exist (src/babylon/config/defines/_assembler.py:292)
T007 DONE tests/constants.py:615
T008 DONE tests/unit/organizations/test_organization_model.py:24
T009 DONE tests/unit/organizations/test_subtypes.py:33
T010 DONE tests/unit/organizations/test_intel_methodology.py:19
T011 DONE src/babylon/models/entities/organization.py:114 (+IntelMethodology:33, KeyFigure:376)
T012 DONE src/babylon/models/entities/organization.py:228 (+union:369)
T013 DONE tests/unit/organizations/conftest.py
T014 DONE src/babylon/models/entities/__init__.py:58
T015 DONE src/babylon/models/components/organization.py:21
T016 DONE src/babylon/models/world_state.py:283 (+to_graph/from_graph:380)
T017 DONE tests/unit/organizations/test_composition.py:22
T018 DONE src/babylon/organizations/composition.py:60
T019 DONE src/babylon/organizations/composition.py:73 (+lifecycle:86)
T020 DONE tests/unit/organizations/test_consciousness_effect.py:36
T021 DONE src/babylon/organizations/consciousness.py:21
T022 DONE src/babylon/organizations/consciousness.py:71 (+aggregate:121)
T023 DONE tests/unit/organizations/test_intel_methodology.py:130
T024 DONE src/babylon/models/entities/organization.py:70
T025 DONE tests/unit/organizations/test_topology_classifier.py:16
T026 DONE tests/unit/organizations/test_key_figures.py:17
T027 DONE src/babylon/organizations/topology.py:56 (+cohesion_loss_on_removal:193)
T028 DONE tests/unit/organizations/test_composition.py:150
T029 DONE src/babylon/organizations/composition.py:99
T030 DONE tests/unit/organizations/test_migration.py:28
T031 DONE src/babylon/organizations/migration.py:54
T032 DONE src/babylon/organizations/__init__.py:47
T033 DONE tests/integration/test_organization_detroit.py
T034 DONE commit 3813447a
T035 DONE commit 3813447a

## 032-ooda-loop-system — tally: done 91 / partial 1 / notdone 14 / unverifiable 5

Critical confirmed: OODASystem.step() builds ActionResult(success=True) directly (src/babylon/engine/systems/ooda.py:214-240), never calls resolve_action/compute_action_cost/enforce_*/compute_lifecycle_modifier.

DONE: T001-T048 (see agent evidence: types.py:21/89/137/175/216/244; defines ooda.py:18 registered _assembler.py:162; eligibility action_eligibility.py:123/126; tests test_types.py 28, test_eligibility.py 29, conftest.py:11; __init__.py:54; cycle_time.py:17; initiative.py:22; layer0.py:21; npc_stub.py:55; engine/systems/ooda.py:37 name="ooda", :118 player_actions; simulation_engine.py:341 position 14; commit afefd01b; constraints tests test_constraints.py:33/83/124; constraints.py:18/54/92; commit 6e8d264c)
T049 NOT-DONE — step() never calls enforce_action_points/coordination_range
T050 DONE commit 6e8d264c
T051-T060 DONE (test_action_effects.py:101/291/476/525/388/203/601; action_effects.py:33/226/106; commit d285e193)
T061 NOT-DONE — RECRUIT/ORGANIZE/PROTEST/etc fall through to generic CI; no specialized resolvers
T062 NOT-DONE — step() builds blind ActionResult(success=True); resolve_action never called
T063 DONE commit d285e193
T064-T065 DONE test_action_costs.py:72/91
T066 PARTIAL — no dedicated EDUCATE cost+credibility-penalty test
T067 DONE action_costs.py:35
T068 DONE src/babylon/ooda/_helpers.py (moved)
T069 DONE action_costs.py:140 (local pairs)
T070 NOT-DONE — step() never calls compute_action_cost
T071 DONE commit af1fd046
T072 DONE test_lifecycle_capacity.py:52
T073 NOT-DONE — no youth-EDUCATE-targeting test
T074 DONE test_lifecycle_capacity.py:121
T075 DONE lifecycle_capacity.py:22
T076 DONE lifecycle_capacity.py:44
T077 NOT-DONE — no youth-institution EDUCATE logic in ooda package
T078 NOT-DONE — step() never calls compute_lifecycle_modifier
T079 DONE commit ae54d0cc
T080 NOT-DONE — superseded by Feature 034 (non-mutation tested instead)
T081 DONE test_layer3.py:99
T082 DONE test_layer3.py:151
T083 DONE test_layer3.py:181
T084 NOT-DONE — superseded by Feature 034
T085 DONE layer3.py:22
T086 NOT-DONE — _propagate_consciousness absent; superseded by Feature 034
T087 DONE layer3.py:57
T088 DONE layer3.py:103
T089 DONE layer3.py:140
T090 NOT-DONE — _propagate_contestation absent; superseded by Feature 034
T091 DONE engine/systems/ooda.py:144
T092 DONE commit 378c7053
T093 DONE tests/integration/test_ooda_detroit.py:113
T094 DONE :206
T095 DONE :285
T096 NOT-DONE — no church PROVIDE_SERVICE neutral-CI test
T097 DONE :274
T098 NOT-DONE — superseded (non-mutation asserted)
T099 NOT-DONE — no 20-tick faction-initiative-rise test
T100 UNVERIFIABLE — vague task, no durable artifact
T101 DONE commit 74f19108
T102-T104 UNVERIFIABLE — process gates, no durable record
T105-T107 DONE commit b562f65b
T108 UNVERIFIABLE
T109 DONE __init__.py:54
T110 DONE commit b562f65b

## 033-bifurcation-topology — tally: done 32 / partial 3 / unverifiable 2

T001 DONE src/babylon/bifurcation/__init__.py
T002 DONE src/babylon/models/enums/events.py:123
T003 DONE src/babylon/models/events/_legacy.py (BifurcationTendencyEvent)
T004 DONE tests/unit/topology/test_phase_transition.py:45
T005 DONE src/babylon/config/defines/consciousness.py:316 (registered _assembler.py:164)
T006 DONE src/babylon/bifurcation/types.py:108
T007 DONE src/babylon/engine/community_state_store.py:21 (+InMemory:33)
T008 DONE tests/unit/bifurcation/conftest.py:131
T009 DONE tests/unit/bifurcation/test_consciousness.py
T010 DONE bifurcation/consciousness.py:40
T011 DONE bifurcation/consciousness.py:112
T012 DONE tests/unit/bifurcation/test_axis.py
T013 DONE bifurcation/axis.py:67
T014 DONE axis.py:96
T015 DONE axis.py:150
T016 DONE tests/unit/bifurcation/test_bridges.py
T017 DONE bifurcation/bridges.py:73
T018 DONE tests/unit/bifurcation/test_resilience.py
T019 DONE resilience.py:37
T020 DONE resilience.py:67
T021 DONE resilience.py:106
T022 DONE resilience.py:132
T023 DONE resilience.py:184
T024 DONE tests/unit/bifurcation/test_ceiling.py
T025 DONE ceiling.py:35
T026 DONE tests/unit/bifurcation/test_legitimation.py
T027 DONE legitimation.py:36
T028 DONE tests/unit/bifurcation/test_analysis.py
T029 DONE analysis.py:53
T030 PARTIAL — membership collection in community.py:466, not a helper in analysis.py
T031 DONE analysis.py:405
T032 PARTIAL — src/babylon/engine/bifurcation_monitor.py:37 standalone class, not TopologyMonitor subclass; hypergraph passed in not rebuilt
T033 PARTIAL — monitor tested in unit test_monitor.py; no integration test at specified path
T034 DONE bifurcation/__init__.py:39
T035 DONE commit dd3f42f8
T036-T037 UNVERIFIABLE — process gates

## 034-ternary-consciousness — tally: done 32 / unverifiable 3

T001 UNVERIFIABLE — baseline run, no durable record
T002 DONE tests/unit/models/test_ternary_consciousness.py:19
T003 DONE :102
T004 DONE :329
T005 DONE src/babylon/models/entities/consciousness.py:35
T006 DONE consciousness.py:51
T007 DONE consciousness.py:294
T008 DONE consciousness.py:460
T009 DONE commit 1674d671
T010 DONE test_ternary_consciousness.py:188
T011 DONE src/babylon/models/entities/community.py:160
T012 DONE consciousness.py:85 (+alias:152)
T012b DONE community.py:303
T013 DONE community.py:238
T014 DONE src/babylon/engine/systems/community.py:98
T015 DONE commit 0d2719c8
T016 DONE tests/unit/formulas/test_consciousness_computation.py
T017 DONE (same file)
T018 DONE src/babylon/formulas/consciousness.py:29
T019 DONE engine/systems/community.py:445 (hypergraph:336)
T020 DONE src/babylon/ooda/layer3.py:46
T021 DONE commit 4d617bf9
T022 DONE test_ternary_consciousness.py:434
T023 DONE consciousness.py:356
T024 DONE formulas/consciousness.py:89 (lookup community.py:443)
T025 DONE commit 14b86abf
T026 DONE tests/unit/bifurcation/test_assimilation_trap.py
T027 DONE bifurcation/consciousness.py:163
T028 DONE bifurcation/types.py:160 (computed analysis.py:497)
T029 DONE commit a86fe6e4
T030 DONE src/babylon/persistence/migrations/0020_dynamic_consciousness_state.sql:32
T031 DONE src/babylon/persistence/postgres_runtime/_spec_062.py:94
T032 DONE bifurcation/consciousness.py:176
T033-T034 UNVERIFIABLE — process gates

## Headline notes
- 031: effectively complete; only T006 PARTIAL (defines.yaml removed in later refactor by design).
- 032: engine-consumer wiring NOT done — T049/T061/T062/T070/T078 NOT-DONE (this is exactly remediation Phase 2.4 verb-dispatch territory; annotate those as scheduled, do not check). T066 PARTIAL. T073/T077/T080/T084/T086/T090/T096/T098/T099 NOT-DONE or superseded by Feature 034 — annotate 'superseded by 034' where stated.
- 033: fully implemented; T030/T032/T033 PARTIAL (path/architecture drift, note where things actually live).
- 034: fully implemented; persistence landed as migration 0020 ideology_r/l/f rather than community_state columns.
