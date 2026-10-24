//! National county authority never implies Michigan fine geometry.
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::content_digest::ContentDigest;
use babylon_kernel::geography::{CountyGeoid, NationalCountyRoster};
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_kernel::tick_content_hash::RefDigest;

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_kernel::H3CellId;
use babylon_persistence::national_counties;
use babylon_persistence::national_counties::CountyReference;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::material_state::{GeographicScope, MaterialGeography, MaterialState};
use babylon_tick::replay_session::ReplayTickSession;

#[test]
fn only_the_pinned_county_roster_establishes_national_membership() {
    let source =
        national_counties::national_county_reference().expect("the county reference fixture loads");
    let counties: Vec<_> = source
        .counties()
        .iter()
        .map(CountyReference::geoid)
        .collect();
    let roster = NationalCountyRoster::try_new(counties.clone())
        .expect("the authored fixture satisfies the constructor invariants");
    assert_eq!(roster.counties().len(), 3144);
    assert!(roster.contains(
        CountyGeoid::try_from("15005").expect("the fixture value fits the target range")
    ));
    assert!(!roster.contains(
        CountyGeoid::try_from("26999").expect("the fixture value fits the target range")
    ));
    let mut invented = counties.clone();
    let michigan = invented
        .iter()
        .position(|row| row.as_str() == "26163")
        .expect("the fixture sequence holds the addressed position");
    invented[michigan] =
        CountyGeoid::try_from("26999").expect("the fixture value fits the target range");
    invented.sort();
    assert!(NationalCountyRoster::try_new(invented).is_err());
    let mut duplicate = counties.clone();
    duplicate[1] = duplicate[0];
    assert!(NationalCountyRoster::try_new(duplicate).is_err());
    assert!(NationalCountyRoster::try_new(counties[1..].to_vec()).is_err());
}

fn national_session() -> ReplayTickSession<HypergraphStore> {
    let source =
        national_counties::national_county_reference().expect("the county reference fixture loads");
    let reference = RefDigest::from_bytes([0x91; 32]);
    let material = MaterialState::try_from_geography(MaterialGeography::NationalCounties {
        roster: source.roster(),
        reference_bundle_digest: *reference.as_bytes(),
        local_detail: None,
    })
    .expect("the fixture input satisfies the fallible conversion");
    let rules_hash =
        babylon_bsl::canonical_ast::rules_hash_of(&[]).expect("the rule set has a canonical hash");
    ReplayTickSession::new(
        "(scenario capture/county-geography (defvocabulary NodeType (TERRITORY)))",
        None,
        "",
        HypergraphStore::new(),
        ReplaySessionId::try_from("capture/county-geography")
            .expect("the fixture value fits the target range"),
        ReplaySeed::new(1),
        ContentDigest {
            defines_hash: [0x81; 32],
            rules_hash,
        },
        reference,
        material,
    )
    .expect("the constructor accepts the authored fixture arguments")
}

#[test]
fn national_replay_has_explicit_county_authority_and_no_invented_hex_rows() {
    let mut session = national_session();
    let actions = OrderedPracticeActionBatch::empty(session.session_identity().clone(), 1)
        .expect("the empty authored batch constructs");
    let report = session
        .advance(&mut CollectingSink::default(), &actions)
        .expect("the fixture advances the authored period");
    assert_eq!(
        report.material_state_rows().dynamic_hexes().source_count(),
        0
    );
    assert_eq!(session.completed_tick(), 1);
    assert_eq!(
        session.material_state().geographic_scope(),
        GeographicScope::NationalCounties
    );
    assert_eq!(
        session
            .material_state()
            .county_roster()
            .expect("the fixture call `county_roster` succeeds for the authored inputs")
            .counties()
            .len(),
        3144
    );
    assert!(!session.material_state().has_michigan_local_detail());

    let mut reopened = national_session();
    reopened
        .restore_full_checkpoint(
            1,
            report.result_stable_graph(),
            report.material_state_rows(),
            report.result_registers().canonical_bytes(),
        )
        .expect("the committed checkpoint restores");
    assert_eq!(reopened.material_state(), session.material_state());
    let actions = OrderedPracticeActionBatch::empty(session.session_identity().clone(), 2)
        .expect("the empty authored batch constructs");
    let mut sink = CollectingSink::default();
    let continuous = session
        .advance(&mut sink, &actions)
        .expect("the fixture advances the authored period");
    let resumed = reopened
        .advance(&mut sink, &actions)
        .expect("the fixture advances the authored period");
    assert_eq!(continuous.result_world(), resumed.result_world());
    assert_eq!(
        continuous.material_state_rows(),
        resumed.material_state_rows()
    );
}

#[test]
fn county_only_checkpoint_refuses_injected_local_geometry_atomically() {
    use babylon_bsl::identity_codec::StableBslValue;
    use babylon_tick::h3_runtime::MichiganDynamicHexValueBits;
    use babylon_tick::material_state::{
        DynamicHexStateRow, MaterialStateRows, MaterialStateRowsInput, WorldRegisterRow,
    };

    let mut original = national_session();
    let actions = OrderedPracticeActionBatch::empty(original.session_identity().clone(), 1)
        .expect("the empty authored batch constructs");
    let report = original
        .advance(&mut CollectingSink::default(), &actions)
        .expect("the fixture advances the authored period");
    let invented = DynamicHexStateRow::try_new(
        H3CellId::try_from(0x0872_8308_28ff_ffff_u64)
            .expect("the fixture value fits the target range"),
        MichiganDynamicHexValueBits {
            c: 0,
            v: 0,
            s: 0,
            k: 0,
            biocapacity_stock: 0,
            energy_stock: 0,
            raw_material_stock: 0,
            internet_access_pct: 0,
            surveillance_coupling: 0,
        },
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let wrong_rows = MaterialStateRows::try_from_rows(MaterialStateRowsInput {
        world_registers: vec![WorldRegisterRow::try_new(
            "world/completed-tick".to_owned(),
            StableBslValue::Int(1),
        )
        .expect("the authored fixture satisfies the constructor invariants")],
        territories: vec![],
        dynamic_hexes: vec![invented],
        organizations: vec![],
    })
    .expect("the fixture input satisfies the fallible conversion");
    let mut reopened = national_session();
    let error = reopened
        .restore_full_checkpoint(
            1,
            report.result_stable_graph(),
            &wrong_rows,
            report.result_registers().canonical_bytes(),
        )
        .expect_err("the fixture call `restore_full_checkpoint` fails for the authored inputs");
    assert!(matches!(
        error,
        babylon_tick::replay_session::ReplayTickError::MaterialState(
            babylon_tick::material_state::MaterialStateError::SourceRowOrder {
                family: "uncaptured dynamic hex checkpoint identity"
            }
        )
    ));
    assert_eq!(reopened.completed_tick(), 0);
    assert!(!reopened.material_state().has_michigan_local_detail());
}
