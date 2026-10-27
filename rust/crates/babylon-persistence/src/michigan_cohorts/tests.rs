use crate::michigan_economy;
use std::collections::{BTreeMap, BTreeSet};

use babylon_bsl::structural_verbs::CollectingSink;

use babylon_graph::stable_state::StableGraphState;
use babylon_graph::substrate::GraphSubstrate;

use babylon_kernel::content_digest::ContentDigest;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_kernel::tick_content_hash::RefDigest;

use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::material_state::MaterialState;
use babylon_tick::replay_session::IdentifiedTickReport;

use super::build;
use super::build::{
    build_cohorts, michigan_business_subject, michigan_sector_subject, BUSINESS_FIELDS,
    MICHIGAN_COHORT_SCENARIO,
};
use crate::michigan_economy::digest_hex;
use crate::michigan_sectors;
use crate::michigan_sectors::MichiganSectorDisclosure;
use crate::michigan_sectors::MichiganSectorDisposition;
use crate::{CampaignFoundation, FoundationContentBundle};
use babylon_bsl::scenario;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::content_digest;
use babylon_tick::replay_session::ReplayTickSession;

fn stable_graph() -> StableGraphState {
    build::michigan_cohort_foundation()
        .expect("the Michigan cohort foundation builds")
        .0
        .stable_graph_state()
        .expect("the fixture graph has a stable state")
}

#[test]
fn generated_source_loads_only_observed_cohorts_and_native_sector_hyperedges() {
    let cohorts = build::michigan_cohorts().expect("the Michigan cohort fixture builds");
    assert_eq!(
        &build_cohorts()
            .expect("the fixture call `build_cohorts` succeeds for the authored inputs"),
        cohorts
    );
    let mut graph = HypergraphStore::new();
    let loaded = scenario::load_scenario(cohorts.scenario_source(), &mut graph)
        .expect("the authored scenario compiles");
    assert_eq!(loaded.id, MICHIGAN_COHORT_SCENARIO);
    assert_eq!(loaded.node_count, 83 + 1_603);
    assert_eq!(graph.nodes("TERRITORY").len(), 83);
    assert_eq!(graph.nodes("ORGANIZATION").len(), 1_603);
    assert_eq!(
        loaded.edge_count, 0,
        "no inferred employment, ownership, or supply edges"
    );
    assert_eq!(loaded.hyperedge_types.get("ECONOMIC_SECTOR"), Some(&19));
    assert_eq!(loaded.hyperedge_types.len(), 1);
    let actual = stable_graph();
    assert_eq!(actual.scenario_scope(), MICHIGAN_COHORT_SCENARIO);
    assert_eq!(
        actual
            .rows()
            .hyperedges()
            .iter()
            .map(|row| row.2.len())
            .sum::<usize>(),
        1_522
    );
    assert_eq!(actual.rows().edges().len(), 0);
}

#[test]
fn classified_memberships_preserve_composite_codes_and_exclude_unclassified_cells() {
    let graph = stable_graph();
    let actual: BTreeMap<_, _> = graph
        .rows()
        .hyperedges()
        .iter()
        .map(|(name, kind, members)| {
            assert_eq!(kind, "ECONOMIC_SECTOR");
            (
                name.as_str(),
                members.iter().map(String::as_str).collect::<BTreeSet<_>>(),
            )
        })
        .collect();
    let sectors =
        michigan_sectors::michigan_county_sectors().expect("the Michigan county sectors build");
    let mut memberships = 0;
    for row in sectors.rows() {
        let local_name = build::michigan_business_local_name(row);
        let count = actual
            .values()
            .filter(|members| members.contains(local_name.as_str()))
            .count();
        if row.sector_code().disposition() == MichiganSectorDisposition::Unclassified {
            assert_eq!(count, 0);
            assert_eq!(michigan_sector_subject(row.sector_code()), None);
        } else {
            assert_eq!(count, 1);
            assert!(
                actual[format!("sector-{}", row.sector_code().as_str()).as_str()]
                    .contains(local_name.as_str())
            );
            memberships += count;
        }
        assert_eq!(
            michigan_business_subject(row),
            StableElementKey::Node {
                scenario: MICHIGAN_COHORT_SCENARIO.to_owned(),
                local_name,
            }
        );
    }
    assert_eq!(memberships, 1_522);
    for code in ["31-33", "44-45", "48-49"] {
        assert!(actual.contains_key(format!("sector-{code}").as_str()));
        assert!(graph
            .rows()
            .nodes()
            .iter()
            .any(|(name, _)| name == &format!("business-26163-{code}")));
    }
    assert!(!actual.contains_key("sector-31"));
    assert!(!actual.contains_key("sector-99"));
}

fn integer_bits(value: u64) -> u64 {
    value
        .to_string()
        .parse::<f64>()
        .expect("the fixture world holds the addressed component")
        .to_bits()
}

#[test]
fn exact_source_cells_are_not_duplicated_and_suppression_is_absence() {
    let graph = stable_graph();
    let attributes: BTreeMap<_, _> = graph
        .rows()
        .node_f64()
        .iter()
        .map(|(name, field, bits)| ((name.as_str(), field.as_str()), *bits))
        .collect();
    let sectors =
        michigan_sectors::michigan_county_sectors().expect("the Michigan county sectors build");
    let mut expected = BTreeMap::new();
    let mut suppressed = 0;
    for row in sectors.rows() {
        let name = build::michigan_business_local_name(row);
        assert!(row.annual_avg_estabs_count() > 0);
        assert!(expected
            .insert(name.clone(), integer_bits(row.annual_avg_estabs_count()))
            .is_none());
        assert_eq!(
            attributes[&(name.as_str(), "organization/kind")],
            1.0_f64.to_bits()
        );
        let values = [
            Some(row.annual_avg_estabs_count()),
            row.annual_avg_emplvl(),
            row.total_annual_wages(),
            row.annual_avg_wkly_wage(),
        ];
        for (key, value) in BUSINESS_FIELDS.iter().zip(values) {
            assert_eq!(
                attributes
                    .get(&(name.as_str(), format!("organization/{key}").as_str()))
                    .copied(),
                value.map(integer_bits)
            );
        }
        if row.disclosure() == MichiganSectorDisclosure::Suppressed {
            suppressed += 1;
        }
    }
    let actual: BTreeMap<_, _> = graph
        .rows()
        .node_f64()
        .iter()
        .filter(|(_, field, _)| field == "organization/qcew-establishments")
        .map(|(name, _, bits)| (name.clone(), *bits))
        .collect();
    assert_eq!(
        actual, expected,
        "one organization observation per source cell; county totals remain separate"
    );
    assert_eq!(suppressed, 416);
    assert_eq!(graph.rows().nodes().len(), 83 + expected.len());
}

fn advance(session: &mut ReplayTickSession<HypergraphStore>) -> IdentifiedTickReport {
    let actions = OrderedPracticeActionBatch::empty(
        session.session_identity().clone(),
        u64::try_from(session.completed_tick() + 1)
            .expect("the fixture value fits the target range"),
    )
    .expect("the empty authored batch constructs");
    let mut sink = CollectingSink::default();
    let report = session
        .advance(&mut sink, &actions)
        .expect("the fixture advances the authored period");
    assert_eq!(report.report().fired, 0);
    assert_eq!(sink.events.len(), 0);
    report
}

#[test]
fn full_foundation_and_checkpoint_roundtrip_preserve_memberships_and_identity() {
    let (mut continued, bundle) =
        build::michigan_cohort_foundation().expect("the Michigan cohort foundation builds");
    let (mut reopened, twin_bundle) =
        build::michigan_cohort_foundation().expect("the Michigan cohort foundation builds");
    let (old, old_bundle) = michigan_economy::michigan_observer_foundation()
        .expect("the Michigan observer foundation builds");
    assert_eq!(
        bundle.reference_bundle_manifest_bytes(),
        old_bundle.reference_bundle_manifest_bytes()
    );
    assert_eq!(continued.material_state(), old.material_state());
    let graph = continued
        .stable_graph_state()
        .expect("the fixture graph has a stable state");
    let county_attributes: Vec<_> = graph
        .rows()
        .node_f64()
        .iter()
        .filter(|(name, _, _)| name.starts_with("county-"))
        .cloned()
        .collect();
    assert_eq!(
        county_attributes,
        old.stable_graph_state()
            .expect("the fixture graph has a stable state")
            .rows()
            .node_f64()
    );
    assert_ne!(continued.session_identity(), old.session_identity());
    assert_eq!(bundle.rule_source_bytes().len(), 0);
    assert_eq!(
        CampaignFoundation::capture(&continued, bundle)
            .expect("the fixture captures the authored state")
            .canonical_bytes(),
        CampaignFoundation::capture(&reopened, twin_bundle)
            .expect("the fixture captures the authored state")
            .canonical_bytes()
    );
    let first = advance(&mut continued);
    reopened
        .restore_full_checkpoint(
            1,
            first.result_stable_graph(),
            first.material_state_rows(),
            first.result_registers().canonical_bytes(),
        )
        .expect("the committed checkpoint restores");
    let next = advance(&mut continued);
    let resumed = advance(&mut reopened);
    assert_eq!(next.tick_content_hash(), resumed.tick_content_hash());
    assert_eq!(next.result_stable_graph(), resumed.result_stable_graph());
    assert_eq!(next.result_stable_graph().rows().hyperedges().len(), 19);
    assert_eq!(next.material_state_rows().territories().rows().len(), 83);
}

/// Reproduce the pre-extraction constructor independently to protect V1 saves.
fn explicit_observer_constructor() -> (ReplayTickSession<HypergraphStore>, FoundationContentBundle)
{
    let source = michigan_economy::michigan_economy()
        .expect("the Michigan economy fixture builds")
        .scenario_source();
    assert_eq!(source.len(), 21_279);
    assert_eq!(
        digest_hex(&content_digest::sha256_of(source.as_bytes())),
        "84650f5a5ab3a6913eb125def04b606653217a50eaf67f515f148fb37283d1fa"
    );
    let defines = format!(
        "{{\"qcew_vintage\":2024,\"tick_duration_days\":{}}}",
        babylon_kernel::clock::DAYS_PER_TICK
    );
    let defines = defines.as_bytes();
    let content = ContentDigest {
        defines_hash: content_digest::sha256_of(defines),
        rules_hash: babylon_bsl::canonical_ast::rules_hash_of(&[])
            .expect("the rule set has a canonical hash"),
    };
    let material =
        crate::michigan_dynamic_hex_foundation().expect("the Michigan hex foundation builds");
    let mut manifest = b"babylon.h3.reference-bundle-composite.v1\0".to_vec();
    manifest.extend_from_slice(&material.base_reference_cohort_digest());
    manifest.extend_from_slice(&material.r8_section_digest());
    assert_eq!(
        content_digest::sha256_of(&manifest),
        material.reference_bundle_digest()
    );
    let session = ReplayTickSession::new(
        source,
        None,
        "",
        HypergraphStore::new(),
        ReplaySessionId::try_from("g4/michigan-observer-v1")
            .expect("the fixture value fits the target range"),
        ReplaySeed::new(319),
        content,
        RefDigest::from_bytes(material.reference_bundle_digest()),
        MaterialState::try_new(material)
            .expect("the authored fixture satisfies the constructor invariants"),
    )
    .expect("the constructor accepts the authored fixture arguments");
    let bundle = FoundationContentBundle::try_new(source, None, "", defines, &manifest)
        .expect("the authored fixture satisfies the constructor invariants");
    (session, bundle)
}

#[test]
fn shared_constructor_matches_explicit_current_interval_foundation() {
    let (expected, expected_bundle) = explicit_observer_constructor();
    let (actual, actual_bundle) = michigan_economy::michigan_observer_foundation()
        .expect("the Michigan observer foundation builds");
    assert_eq!(
        CampaignFoundation::capture(&actual, actual_bundle)
            .expect("the fixture captures the authored state")
            .canonical_bytes(),
        CampaignFoundation::capture(&expected, expected_bundle)
            .expect("the fixture captures the authored state")
            .canonical_bytes()
    );
}
