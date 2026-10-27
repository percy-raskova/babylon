use super::runtime::{MaterialRuntimeError, MaterialRuntimeFoundation, StoredMaterialFoundation};
use crate::economic_catalog::CapturedEconomicCatalog;
use crate::foundation::{CampaignFoundation, FoundationContentBundle};
use crate::identity::CampaignId;
use crate::michigan_material::MichiganDeliveryPreset;
use crate::michigan_material::MichiganMaterialCatalog;
use crate::runtime;
use crate::simulation_experiment::SimulationExperimentV1;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::content_digest;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_practice_contract::OrganizerPeriodJournal;
use babylon_tick::material_replay::PreparedMaterialTick;
use babylon_tick::material_replay::{MaterialReplayError, MaterialReplaySession};
use babylon_tick::material_state::{MaterialGeography, MaterialState};
use babylon_tick::material_world::{MaterialWorldError, MaterialWorldRegister};
use babylon_tick::replay_session::{ReplayCommitDisposition, ReplayTickSession};
use std::path::Path;
use uuid::Uuid;

pub(crate) fn persisted_graph_copy(original: &CampaignFoundation) -> CampaignFoundation {
    let bundle = original.content_bundle();
    CampaignFoundation::from_persisted(
        original.stable_graph_bytes().to_vec(),
        original.world_register_bytes().to_vec(),
        original.resolver_manifest_bytes().to_vec(),
        original.prepared_environment_bytes().to_vec(),
        std::str::from_utf8(original.replay_session_identity().as_bytes())
            .expect("the fixture bytes came from a UTF-8 string"),
        i64::from_be_bytes(original.rng_seed().to_be_bytes()),
        original.content_digest().defines_hash,
        original.content_digest().rules_hash,
        *original.reference_digest().as_bytes(),
        bundle.canonical_bytes(),
        content_digest::sha256_of(original.canonical_bytes()),
    )
    .expect("the persisted content admits the value")
}

pub(super) fn stored_copy(original: &MaterialRuntimeFoundation) -> StoredMaterialFoundation {
    StoredMaterialFoundation {
        spec: original.spec.clone(),
        initial_register_bytes: original.register.canonical_bytes().to_vec(),
        foundation_digest: original.digest(),
        graph_foundation_digest: content_digest::sha256_of(
            original.graph_foundation.canonical_bytes(),
        ),
    }
}

#[test]
fn material_campaign_captures_authored_cycle_and_fires_it_once_per_period() {
    let foundation = crate::michigan_content::MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let rules = foundation
        .graph_foundation()
        .content_bundle()
        .rule_source_bytes();
    assert!(
        !rules.is_empty(),
        "a material campaign must capture its authored cycle rule"
    );
    let mut session = foundation
        .into_session()
        .expect("the fixture opens a session");
    let mut sink = CollectingSink::default();
    for tick in 1..=4 {
        let actions = OrderedPracticeActionBatch::empty(
            session.graph_session().session_identity().clone(),
            tick,
        )
        .expect("the empty authored batch constructs");
        let candidate = session
            .prepare_advance(&actions)
            .expect("the session prepares the authored advance");
        assert_eq!(
            candidate.graph_report().report().per_rule_fired,
            [("material/period".to_owned(), 1)],
            "the authored material cycle must execute exactly once in period {tick}"
        );
        session
            .commit_prepared_and_publish(&mut sink, candidate, |_, _| {
                Ok::<_, ()>(ReplayCommitDisposition::Committed)
            })
            .expect("the prepared period commits");
    }
}

#[test]
fn material_foundation_refuses_a_rule_bundle_different_from_its_captured_catalog() {
    let original = crate::michigan_content::MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let bundle = original.graph_foundation().content_bundle();
    let source = std::str::from_utf8(bundle.scenario_source_bytes())
        .expect("the fixture bytes came from a UTF-8 string");
    let changed_rules = format!(
        "; This source was not captured in the catalog.\n{}",
        std::str::from_utf8(bundle.rule_source_bytes())
            .expect("the fixture bytes came from a UTF-8 string")
    );
    let changed_bundle = FoundationContentBundle::try_new(
        source,
        None,
        &changed_rules,
        bundle.defines_bytes(),
        bundle.reference_bundle_manifest_bytes(),
    )
    .expect("the authored fixture satisfies the constructor invariants");
    assert_eq!(changed_bundle.content_digest(), bundle.content_digest());
    let changed_graph = ReplayTickSession::new(
        source,
        None,
        &changed_rules,
        HypergraphStore::new(),
        original
            .graph_foundation()
            .replay_session_identity()
            .clone(),
        original.graph_foundation().rng_seed(),
        changed_bundle.content_digest().clone(),
        changed_bundle.reference_digest(),
        MaterialState::try_from_geography(MaterialGeography::MichiganControl {
            local_detail: crate::michigan_dynamic_hex_foundation()
                .expect("the Michigan hex foundation builds"),
            reference_bundle_digest: *changed_bundle.reference_digest().as_bytes(),
        })
        .expect("the fixture input satisfies the fallible conversion"),
    )
    .expect("the constructor accepts the authored fixture arguments");
    assert!(matches!(
        MaterialRuntimeFoundation::capture(
            changed_graph,
            changed_bundle,
            original.initial_register().state().clone(),
            original.spec().clone(),
        ),
        Err(MaterialRuntimeError::FoundationMismatch)
    ));
}

fn alternate_foundation() -> MaterialRuntimeFoundation {
    let original = crate::michigan_content::MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    recapture_with_seed(&original, 9821)
        .expect("the fixture call `recapture_with_seed` succeeds for the authored inputs")
}

fn recapture_with_seed(
    original: &MaterialRuntimeFoundation,
    seed: i64,
) -> Result<MaterialRuntimeFoundation, MaterialRuntimeError> {
    let graph = original.graph_foundation();
    let captured = graph
        .content_bundle()
        .economic_catalog()
        .ok_or(MaterialRuntimeError::FoundationMismatch)?;
    let catalog = CapturedEconomicCatalog::decode(captured.canonical_bytes(), captured.digest())
        .map_err(|_| MaterialRuntimeError::FoundationMismatch)?;
    catalog.create_foundation(
        graph.replay_session_identity().clone(),
        ReplaySeed::new(seed),
    )
}

#[test]
fn typed_experiment_refuses_a_graph_seed_different_from_its_captured_input() {
    let experiment = SimulationExperimentV1::parse(include_bytes!(
        "../../../../../content/scenarios/michigan/diagnostic-sustained.json"
    ))
    .expect("the authored literal parses as the declared type");
    let original = experiment
        .create_foundation()
        .expect("the authored catalog builds the foundation");
    assert!(recapture_with_seed(&original, experiment.seed).is_ok());
    assert!(recapture_with_seed(&original, 9821).is_err());
}

#[test]
fn stored_content_reconstructs_exact_alternate_session_and_seed_without_factory_substitution() {
    let original = alternate_foundation();
    let stored = stored_copy(&original);
    let digest = original.digest();
    let reconstructed = super::reconstruct_material_foundation(
        stored,
        persisted_graph_copy(original.graph_foundation()),
        digest,
    )
    .expect("the fixture call `reconstruct_material_foundation` succeeds for the authored inputs");
    assert_eq!(
        reconstructed
            .export_canonical_bytes()
            .expect("the content exports its canonical bytes"),
        original
            .export_canonical_bytes()
            .expect("the content exports its canonical bytes")
    );
    assert_eq!(
        reconstructed.initial_register(),
        original.initial_register()
    );
    assert_eq!(reconstructed.spec(), original.spec());
    let uninterrupted = original
        .into_session()
        .expect("the fixture opens a session");
    let reopened = reconstructed
        .into_session()
        .expect("the fixture opens a session");
    assert_eq!(
        reopened.graph_session().session_identity(),
        uninterrupted.graph_session().session_identity()
    );
    let actions = OrderedPracticeActionBatch::empty(
        uninterrupted.graph_session().session_identity().clone(),
        1,
    )
    .expect("the empty authored batch constructs");
    let first = uninterrupted
        .prepare_advance(&actions)
        .expect("the session prepares the authored advance");
    let restored_first = reopened
        .prepare_advance(&actions)
        .expect("the session prepares the authored advance");
    assert_eq!(first.identity(), restored_first.identity());
    assert_eq!(
        first.material().register().canonical_bytes(),
        restored_first.material().register().canonical_bytes()
    );
    assert_eq!(
        first.material().receipt_bytes(),
        restored_first.material().receipt_bytes()
    );
}

#[test]
fn reconstruction_refuses_component_changes_and_an_unadmitted_expected_identity() {
    let original = crate::michigan_content::MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let expected = original.digest();
    for mutation in 0..5 {
        let mut stored = stored_copy(&original);
        match mutation {
            0 => stored.spec.content_digest[0] ^= 1,
            1 => stored.spec.preset_id.push_str("-changed"),
            2 => {
                stored.spec.duration =
                    babylon_kernel::clock::CampaignDuration::Finite { final_period: 17 }
            }
            3 => stored.foundation_digest[0] ^= 1,
            4 => stored.graph_foundation_digest[0] ^= 1,
            _ => unreachable!(),
        }
        assert!(matches!(
            super::reconstruct_material_foundation(
                stored,
                persisted_graph_copy(original.graph_foundation()),
                expected,
            ),
            Err(MaterialRuntimeError::FoundationMismatch)
        ));
    }
    assert!(matches!(
        super::reconstruct_material_foundation(
            stored_copy(&original),
            persisted_graph_copy(original.graph_foundation()),
            [0; 32],
        ),
        Err(MaterialRuntimeError::FoundationMismatch)
    ));
}

#[test]
fn reconstruction_rejects_a_different_valid_graph_and_a_nonzero_initial_register() {
    let original = crate::michigan_content::MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let alternate = alternate_foundation();
    let mut mixed = stored_copy(&original);
    mixed.graph_foundation_digest =
        content_digest::sha256_of(alternate.graph_foundation().canonical_bytes());
    assert!(matches!(
        super::reconstruct_material_foundation(
            mixed,
            persisted_graph_copy(alternate.graph_foundation()),
            original.digest(),
        ),
        Err(MaterialRuntimeError::FoundationMismatch)
    ));
    let mut stored = stored_copy(&original);
    let graph = persisted_graph_copy(original.graph_foundation());
    let expected = original.digest();
    let session = original
        .into_session()
        .expect("the fixture opens a session");
    let actions =
        OrderedPracticeActionBatch::empty(session.graph_session().session_identity().clone(), 1)
            .expect("the empty authored batch constructs");
    stored.initial_register_bytes = session
        .prepare_advance(&actions)
        .expect("the session prepares the authored advance")
        .material()
        .register()
        .canonical_bytes()
        .to_vec();
    assert!(matches!(
        super::reconstruct_material_foundation(stored, graph, expected),
        Err(MaterialRuntimeError::FoundationMismatch)
    ));
}

#[test]
fn large_stored_sources_reconstruct_the_same_circuit_without_factory_substitution() {
    let original = crate::michigan_content::MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    assert!(
        original
            .graph_foundation()
            .content_bundle()
            .scenario_source_bytes()
            .len()
            > 65_535
    );
    let restored = super::reconstruct_material_foundation(
        stored_copy(&original),
        persisted_graph_copy(original.graph_foundation()),
        original.digest(),
    )
    .expect("the fixture call `reconstruct_material_foundation` succeeds for the authored inputs");
    assert_eq!(
        restored
            .export_canonical_bytes()
            .expect("the content exports its canonical bytes"),
        original
            .export_canonical_bytes()
            .expect("the content exports its canonical bytes")
    );
    let continued = original
        .into_session()
        .expect("the fixture opens a session");
    let reopened = restored
        .into_session()
        .expect("the fixture opens a session");
    let actions =
        OrderedPracticeActionBatch::empty(continued.graph_session().session_identity().clone(), 1)
            .expect("the empty authored batch constructs");
    let left = continued
        .prepare_advance(&actions)
        .expect("the session prepares the authored advance");
    let right = reopened
        .prepare_advance(&actions)
        .expect("the session prepares the authored advance");
    assert_eq!(
        left.material().register().canonical_bytes(),
        right.material().register().canonical_bytes()
    );
    assert_eq!(left.identity(), right.identity());
}

#[test]
fn admitted_bundle_foundations_reconstruct_exactly_through_dispatch_transit_and_arrival() {
    use crate::michigan_content::MichiganContentPreset;
    for preset in [
        MichiganContentPreset::FourWeekStandard,
        MichiganContentPreset::FourWeekDelayed,
    ] {
        let original = preset
            .create_foundation(&crate::test_support::catalog())
            .expect("the authored catalog builds the foundation");
        let restored = super::reconstruct_material_foundation(
            stored_copy(&original),
            persisted_graph_copy(original.graph_foundation()),
            preset
                .admitted(&crate::test_support::catalog())
                .expect("the fixture admits the authored value")
                .digest(),
        )
        .expect(
            "the fixture call `reconstruct_material_foundation` succeeds for the authored inputs",
        );
        assert_eq!(
            restored
                .export_canonical_bytes()
                .expect("the content exports its canonical bytes"),
            original
                .export_canonical_bytes()
                .expect("the content exports its canonical bytes")
        );
        assert_eq!(
            restored.graph_foundation().content_bundle().defines_bytes(),
            original.graph_foundation().content_bundle().defines_bytes()
        );
        let mut continued = original
            .into_session()
            .expect("the fixture opens a session");
        let mut reopened = restored
            .into_session()
            .expect("the fixture opens a session");
        let mut left_sink = CollectingSink::default();
        let mut right_sink = CollectingSink::default();
        for period in 1..=6 {
            let actions = OrderedPracticeActionBatch::empty(
                continued.graph_session().session_identity().clone(),
                period,
            )
            .expect("the empty authored batch constructs");
            let left = continued
                .prepare_advance(&actions)
                .expect("the session prepares the authored advance");
            let right = reopened
                .prepare_advance(&actions)
                .expect("the session prepares the authored advance");
            assert_eq!(
                left.graph_report().successful_event_batch().events(),
                right.graph_report().successful_event_batch().events()
            );
            if period == 1 {
                assert_workforce_seed_evidence(&left);
            }
            if preset == MichiganContentPreset::FourWeekDelayed {
                assert_delayed_panel_retention(&left, period);
            }
            let checkpoint =
                matches!(period, 2..=4).then(|| reconstructed_checkpoint(preset, &left));
            assert_eq!(left.identity(), right.identity());
            assert_eq!(
                left.material().register().canonical_bytes(),
                right.material().register().canonical_bytes()
            );
            assert_eq!(
                left.material().receipt_bytes(),
                right.material().receipt_bytes()
            );
            continued
                .commit_prepared_and_publish(&mut left_sink, left, |_, _| {
                    Ok::<_, ()>(ReplayCommitDisposition::Committed)
                })
                .expect("the prepared period commits");
            reopened
                .commit_prepared_and_publish(&mut right_sink, right, |_, _| {
                    Ok::<_, ()>(ReplayCommitDisposition::Committed)
                })
                .expect("the prepared period commits");
            if let Some(checkpoint) = checkpoint {
                reopened = checkpoint;
            }
        }
    }
}

#[test]
fn bundle_reconstruction_refuses_alternate_content_and_individually_valid_changed_stock() {
    use crate::michigan_content::MichiganContentPreset;
    let preset = MichiganContentPreset::FourWeekStandard;
    let original = preset
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let expected = preset
        .admitted(&crate::test_support::catalog())
        .expect("the fixture admits the authored value")
        .digest();
    let previous = alternate_foundation();
    // A valid graph with a different seed/session cannot replace the admitted one.
    let mut changed = stored_copy(&original);
    changed.graph_foundation_digest =
        content_digest::sha256_of(previous.graph_foundation().canonical_bytes());
    assert!(matches!(
        super::reconstruct_material_foundation(
            changed,
            persisted_graph_copy(previous.graph_foundation()),
            expected
        ),
        Err(MaterialRuntimeError::FoundationMismatch)
    ));
    let mut changed = stored_copy(&original);
    let mut state = original.initial_register().state().clone();
    state.inventory[0].quantity += 1;
    changed.initial_register_bytes =
        MaterialWorldRegister::try_new(original.material_catalog(), 0, state)
            .expect("the authored fixture satisfies the constructor invariants")
            .canonical_bytes()
            .to_vec();
    assert!(matches!(
        super::reconstruct_material_foundation(
            changed,
            persisted_graph_copy(original.graph_foundation()),
            expected
        ),
        Err(MaterialRuntimeError::FoundationMismatch)
    ));
    // A whole valid bundle successor cannot nominate its own trust anchor.
    assert!(matches!(
        super::reconstruct_material_foundation(
            stored_copy(&original),
            persisted_graph_copy(original.graph_foundation()),
            previous.digest()
        ),
        Err(MaterialRuntimeError::FoundationMismatch)
    ));
}

fn assert_delayed_panel_retention(candidate: &PreparedMaterialTick<HypergraphStore>, period: u64) {
    use babylon_bsl::identity_codec::StableBslValue;
    use babylon_graph::stable_element::StableElementKey;
    let events = candidate.graph_report().successful_event_batch().events();
    assert_eq!(events.len(), 5);
    let panel_name = crate::test_support::catalog()
        .staffing()
        .pools
        .iter()
        .find(|seed| seed.key == "panel-forming")
        .expect("the fixture holds the searched element")
        .workplace_local_name();
    let panel = events.iter().find(|event| event.fields().iter().any(|(key,value)| {
        key == "subject" && matches!(value, StableBslValue::Node(StableElementKey::Node{local_name,..}) if *local_name == panel_name)
    })).expect("the fixture holds the searched element");
    let field = |name| match &panel
        .fields()
        .iter()
        .find(|(key, _)| key == name)
        .expect("the fixture holds the searched element")
        .1
    {
        StableBslValue::Int(value) => *value,
        _ => panic!("staffing evidence must be exact integer"),
    };
    assert_eq!(field("closing-employed") + field("closing-reserve"), 4);
    if period == 1 {
        assert_eq!(field("previous-unretained-hours"), 640);
        assert_eq!(field("current-unretained-hours"), 0);
        assert_eq!(field("closing-employed"), 4);
    } else if period == 2 {
        assert_eq!(field("previous-unretained-hours"), 0);
        assert_eq!(field("closing-employed"), 0);
        assert_eq!(field("separations"), 4);
    } else if period == 4 {
        assert_eq!(field("current-unretained-hours"), 640);
        assert_eq!(field("closing-employed"), 4);
        assert_eq!(field("hires"), 4);
    }
}

#[test]
fn unwrapped_definitions_and_changed_opening_workforce_are_not_scheduled_fallbacks() {
    let current = crate::michigan_content::MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let original = current.graph_foundation().content_bundle();
    let rules = std::str::from_utf8(original.rule_source_bytes())
        .expect("the fixture bytes came from a UTF-8 string");
    for change_seed in [false, true] {
        let source = std::str::from_utf8(original.scenario_source_bytes())
            .expect("the fixture bytes came from a UTF-8 string");
        let changed_source = source.replace(
            "(social-class/employed-population 20)",
            "(social-class/employed-population 19)",
        );
        let source = if change_seed {
            changed_source.as_str()
        } else {
            source
        };
        let defines = if change_seed {
            original.defines_bytes()
        } else {
            b"{}"
        };
        let bundle = FoundationContentBundle::try_new(
            source,
            None,
            rules,
            defines,
            original.reference_bundle_manifest_bytes(),
        )
        .expect("the authored fixture satisfies the constructor invariants");
        let graph = ReplayTickSession::new(
            source,
            None,
            rules,
            HypergraphStore::new(),
            ReplaySessionId::try_from("fixture/unsupported-authority")
                .expect("the fixture value fits the target range"),
            ReplaySeed::new(319),
            bundle.content_digest().clone(),
            bundle.reference_digest(),
            MaterialState::try_from_geography(MaterialGeography::MichiganControl {
                local_detail: crate::michigan_dynamic_hex_foundation()
                    .expect("the Michigan hex foundation builds"),
                reference_bundle_digest: *bundle.reference_digest().as_bytes(),
            })
            .expect("the fixture input satisfies the fallible conversion"),
        )
        .expect("the constructor accepts the authored fixture arguments");
        assert!(matches!(
            MaterialRuntimeFoundation::capture(
                graph,
                bundle,
                current.register.state().clone(),
                current.spec.clone()
            ),
            Err(MaterialRuntimeError::FoundationMismatch)
        ));
    }
}

fn reconstructed_checkpoint(
    preset: crate::michigan_content::MichiganContentPreset,
    candidate: &PreparedMaterialTick<HypergraphStore>,
) -> MaterialReplaySession<HypergraphStore> {
    let stored = preset
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let mut restored = super::reconstruct_material_foundation(
        stored_copy(&stored),
        persisted_graph_copy(stored.graph_foundation()),
        preset
            .admitted(&crate::test_support::catalog())
            .expect("the fixture admits the authored value")
            .digest(),
    )
    .expect("the fixture call `reconstruct_material_foundation` succeeds for the authored inputs")
    .into_session()
    .expect("the fixture opens a session");
    let graph = candidate.graph_report();
    restored
        .restore_full_checkpoint(
            graph.result_stable_graph(),
            graph.material_state_rows(),
            graph.result_registers().canonical_bytes(),
            MaterialWorldRegister::decode_external(
                restored.catalog(),
                candidate.material().register().canonical_bytes().to_vec(),
            )
            .expect("the committed canonical bytes decode"),
        )
        .expect("the committed checkpoint restores");
    restored
}

fn assert_workforce_seed_evidence(candidate: &PreparedMaterialTick<HypergraphStore>) {
    use babylon_bsl::identity_codec::StableBslValue;
    use babylon_graph::stable_element::StableElementKey;
    let catalog = crate::test_support::catalog();
    let events = candidate.graph_report().successful_event_batch().events();
    assert_eq!(events.len(), 5);
    for seed in &catalog.staffing().pools {
        let event = events.iter().find(|event| event.fields().iter().any(|(key,value)| {
            key == "subject" && matches!(value, StableBslValue::Node(StableElementKey::Node{local_name,..}) if *local_name == seed.workplace_local_name())
        })).expect("the fixture holds the searched element");
        for (field, value) in [
            ("opening-employed", seed.employed),
            ("opening-reserve", seed.reserve),
            ("previous-unretained-hours", seed.previous_unretained_hours),
        ] {
            assert!(event.fields().contains(&(
                field.to_owned(),
                StableBslValue::Int(
                    i64::try_from(value).expect("the fixture value fits the target range")
                )
            )));
        }
    }
}

#[test]
fn material_transition_failure_abandons_prepared_graph_and_identity() {
    let foundation = crate::michigan_content::MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let mut initial = foundation.initial_register().state().clone();
    let source = initial
        .production_commitments
        .iter()
        .find(|row| row.period == 1 && row.planned_batches > 0)
        .expect("the fixture holds the searched element");
    let output = foundation
        .material_catalog()
        .process_outputs
        .iter()
        .find(|row| row.process_id == source.process_id)
        .expect("the fixture holds the searched element")
        .clone();
    if let Some(stock) = initial.inventory.iter_mut().find(|row| {
        row.site_id == output.site_id
            && row.good_id == output.good_id
            && row.unit_id == output.unit_id
    }) {
        stock.quantity = u64::MAX;
    } else {
        initial
            .inventory
            .push(babylon_material_circuit::InventoryRow {
                site_id: output.site_id,
                good_id: output.good_id,
                unit_id: output.unit_id,
                quantity: u64::MAX,
            });
    }
    let catalog = foundation.material_catalog().clone();
    let register = MaterialWorldRegister::try_new(&catalog, 0, initial)
        .expect("the authored fixture satisfies the constructor invariants");
    let session = MaterialReplaySession::new(
        foundation.graph,
        register,
        catalog,
        [7; 32],
        babylon_kernel::clock::CampaignDuration::Finite { final_period: 16 },
        foundation.labor,
    )
    .expect("the constructor accepts the authored fixture arguments");
    let bytes = session.material().canonical_bytes().to_vec();
    let hash = session
        .current_world_hash()
        .expect("the committed session publishes a world hash");
    let actions =
        OrderedPracticeActionBatch::empty(session.graph_session().session_identity().clone(), 1)
            .expect("the empty authored batch constructs");
    assert!(matches!(
        session.prepare_advance(&actions),
        Err(MaterialReplayError::Graph(
            babylon_tick::replay_session::ReplayTickError::MaterialBase(
                babylon_tick::material_replay::MaterialBaseError::World(
                    MaterialWorldError::Circuit(
                        babylon_material_circuit::MaterialCircuitError::Arithmetic
                    )
                )
            )
        ))
    ));
    assert_eq!(session.completed_tick(), 0);
    assert_eq!(session.graph_session().completed_tick(), 0);
    assert_eq!(session.material().canonical_bytes(), bytes);
    assert_eq!(
        session
            .current_world_hash()
            .expect("the committed session publishes a world hash"),
        hash
    );
}

#[test]
fn captured_source_refuses_changed_tick_zero_organizer_agreements() {
    let catalog = MichiganMaterialCatalog::load_for_preset(
        &Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../../content/scenarios/michigan/defines.toml"),
        MichiganDeliveryPreset::OrganizeInWayne,
    )
    .expect("the preset content loads");
    let original = crate::michigan_content::MichiganContentPreset::OrganizeInWayne
        .create_foundation_for_campaign(&catalog, CampaignId::from_uuid(Uuid::from_u128(0x40_265)))
        .expect("the authored catalog builds the campaign foundation");
    let mut changed = original
        .initial_register()
        .organizer_state()
        .expect("the fixture register carries organizer state")
        .clone();
    assert_ne!(changed.agreements.len(), 0);
    changed.agreements.clear();
    let altered_register = MaterialWorldRegister::try_new(
        original.material_catalog(),
        0,
        original.initial_register().state().clone(),
    )
    .expect("the authored fixture satisfies the constructor invariants")
    .with_organizer(
        original.material_catalog(),
        original
            .initial_register()
            .organizer_config()
            .expect("the fixture register carries organizer config")
            .clone(),
        changed,
        OrganizerPeriodJournal::empty(),
    )
    .expect("the fixture builder accepts the authored options");
    let graph = runtime::reconstruct_graph_foundation_session(original.graph_foundation()).expect(
        "the fixture call `reconstruct_graph_foundation_session` succeeds for the authored inputs",
    );
    assert!(MaterialRuntimeFoundation::capture_register(
        graph,
        FoundationContentBundle::decode(
            original
                .graph_foundation()
                .content_bundle()
                .canonical_bytes(),
        )
        .expect("the committed canonical bytes decode"),
        altered_register,
        original.spec().clone(),
    )
    .is_err());
}

#[test]
fn single_owner_components_preserve_binary_export_and_reject_framing_damage() {
    let original = crate::michigan_content::MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let rebuilt = super::reconstruct_material_foundation(
        stored_copy(&original),
        persisted_graph_copy(original.graph_foundation()),
        original.digest(),
    )
    .expect("the fixture call `reconstruct_material_foundation` succeeds for the authored inputs");
    let exported = original
        .export_canonical_bytes()
        .expect("the content exports its canonical bytes");
    assert_eq!(
        original
            .canonical_len()
            .expect("the fixture call `canonical_len` succeeds for the authored inputs"),
        exported.len()
    );
    assert_eq!(original.digest(), content_digest::sha256_of(&exported));
    assert_eq!(
        rebuilt
            .export_canonical_bytes()
            .expect("the content exports its canonical bytes"),
        exported
    );
    assert_eq!(rebuilt.digest(), original.digest());
    assert_eq!(
        MaterialRuntimeFoundation::decode(&exported, original.digest())
            .expect("the committed canonical bytes decode")
            .export_canonical_bytes()
            .expect("the content exports its canonical bytes"),
        exported
    );
    let mut trailing = exported;
    trailing.push(0);
    assert!(matches!(
        MaterialRuntimeFoundation::decode(&trailing, content_digest::sha256_of(&trailing)),
        Err(MaterialRuntimeError::FoundationMismatch)
    ));
    let mut damaged = stored_copy(&original);
    damaged.initial_register_bytes.push(0);
    assert!(super::reconstruct_material_foundation(
        damaged,
        persisted_graph_copy(original.graph_foundation()),
        original.digest()
    )
    .is_err());
}
