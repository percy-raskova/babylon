//! Source-only economic authority, independently of the initial mutable checkpoint.
use std::collections::BTreeSet;

use babylon_graph::{stable_element::StableElementKey, stable_state::StableGraphStateRows};
use babylon_kernel::content_digest::sha256_of;
use babylon_persistence::economic_catalog::{
    CapturedEconomicCatalog, CatalogCapacity, SourceArtifact, SourceArtifactKind as Kind,
};

#[path = "fixtures/national_capture.rs"]
mod national_capture;
use national_capture::input;

#[test]
fn capture_retains_sources_once_and_regenerates_the_exact_native_opening() {
    let supplied = input();
    let source_bytes: usize = supplied.sources.iter().map(|row| row.bytes().len()).sum();
    let catalog = CapturedEconomicCatalog::capture(supplied, None).unwrap();
    // Framing holds only source identities, compiler selection and exact source blobs.
    // There is no per-firm or generated global-state serialization inside this envelope.
    assert!(catalog.canonical_bytes().len() < source_bytes + 4096);
    assert_eq!(catalog.digest(), sha256_of(catalog.canonical_bytes()));
    assert_eq!(catalog.compiler_version(), "national-world-v4");
    let mut obsolete = catalog.canonical_bytes().to_vec();
    let compiler = b"national-world-v4";
    let offset = obsolete
        .windows(compiler.len())
        .position(|s| s == compiler)
        .unwrap();
    obsolete[offset + compiler.len() - 1] = b'1';
    assert_eq!(
        CapturedEconomicCatalog::decode(&obsolete, sha256_of(&obsolete)),
        Err(babylon_persistence::economic_catalog::EconomicCatalogError::CompilerVersion)
    );
    assert_eq!(catalog.opening().sites.len(), 60_634);
    assert_eq!(
        catalog
            .opening()
            .households
            .iter()
            .filter(|h| matches!(
                h.location,
                babylon_kernel::economic_location::EconomicLocation::County(_)
            ))
            .map(|h| h.households)
            .sum::<u64>(),
        129_227_496
    );
    assert!(matches!(
        catalog.opening().capacity,
        CatalogCapacity::Rolling(babylon_material_circuit::RollingProcessSupply::Equipment(_))
    ));
    let aid = catalog.national_aid_capture().unwrap().clone();
    let catalog_bytes = catalog.canonical_bytes().len();
    let catalog_digest = catalog.digest();
    let expected_opening = catalog.opening().clone();
    let original = catalog
        .create_foundation(
            babylon_kernel::replay::ReplaySessionId::try_from("national-captured-contract")
                .unwrap(),
            babylon_kernel::replay::ReplaySeed::new(319),
        )
        .unwrap();
    let graph_bytes = original.graph_foundation().canonical_bytes().len();
    let graph_digest = sha256_of(original.graph_foundation().canonical_bytes());
    let original =
        babylon_persistence::economic_content::EconomicContentAdmission::from_foundation(original)
            .unwrap();
    let expected_nodes = 3_144
        + expected_opening.sites.len()
        + expected_opening.households.len()
        + expected_opening
            .staffing
            .iter()
            .map(|p| p.members.len())
            .sum::<usize>()
        + admitted_aid_class_count(&original, &aid);
    assert_eq!(
        original.foundation_graph().rows().nodes().len(),
        expected_nodes
    );
    eprintln!(
        "native foundation bytes: sources={source_bytes}, catalog={}, graph={}, register={}, complete={}, nodes={}",
        catalog_bytes,
        graph_bytes,
        original.initial_register().canonical_bytes().len(),
        original.canonical_len().unwrap(),
        original.foundation_graph().rows().nodes().len(),
    );
    eprintln!(
        "native foundation SHA256: catalog={catalog_digest:02x?}, graph={graph_digest:02x?}, register={:02x?}, complete={:02x?}",
        original.initial_register().digest(),
        original.digest(),
    );
    let restored = babylon_persistence::material_runtime::MaterialRuntimeFoundation::decode(
        &original.export_canonical_bytes().unwrap(),
        original.digest(),
    )
    .unwrap();
    assert_eq!(
        restored.export_canonical_bytes().unwrap(),
        original.export_canonical_bytes().unwrap()
    );
    assert_eq!(restored.initial_register(), original.initial_register());
    let catalog = restored
        .graph_foundation()
        .content_bundle()
        .economic_catalog()
        .unwrap();
    assert_eq!(catalog.opening(), &expected_opening);
}

// These Designed children refine captured household budgets. Recipient classes
// have no fabricated workplace; the employed donor reuses its staffing node.
fn admitted_aid_class_count(
    admitted: &babylon_persistence::economic_content::EconomicContentAdmission,
    aid: &babylon_persistence::national_economy::NationalAidCapture,
) -> usize {
    let opening = admitted.view().opening;
    let rows = admitted.foundation_graph().rows();
    let staffing: Vec<_> = opening.staffing.iter().flat_map(|p| &p.members).collect();
    let staffing_classes: BTreeSet<_> = staffing.iter().map(|m| node_name(&m.subject)).collect();
    let graph_classes: BTreeSet<_> = rows
        .nodes()
        .iter()
        .filter(|(_, kind)| kind == "SOCIAL_CLASS")
        .map(|(name, _)| name.as_str())
        .collect();
    let extra_classes: BTreeSet<_> = graph_classes
        .difference(&staffing_classes)
        .copied()
        .collect();
    let captured_extra: BTreeSet<_> = aid
        .children
        .iter()
        .filter(|c| !staffing_classes.contains(node_name(&c.class_subject)))
        .map(|c| node_name(&c.class_subject))
        .collect();
    assert_eq!(extra_classes, captured_extra);
    assert_eq!(
        extra_classes,
        BTreeSet::from([
            "wayne-aid-recipient-inactive",
            "cook-aid-recipient-inactive",
        ])
    );
    let mut donors = Vec::new();
    for child in &aid.children {
        let household = opening
            .households
            .iter()
            .find(|h| h.principal_id == child.principal)
            .unwrap();
        assert_eq!(household.subject, child.subject);
        assert_eq!(household.location, child.location);
        assert_eq!(
            (household.persons, household.households),
            (child.persons, child.households)
        );
        let class = node_name(&child.class_subject);
        assert!(graph_classes.contains(class));
        if let Some(member) = staffing.iter().find(|m| m.subject == child.class_subject) {
            assert_eq!(member.member.household_id(), child.principal);
            assert_eq!(
                (member.employed, member.reserve),
                (child.employed, child.reserve)
            );
            assert!(child.employed > 0);
            donors.push(child.principal);
        } else {
            assert_inactive_recipient(child, rows);
        }
    }
    assert_eq!(donors.len(), 1);
    assert!(aid.mandates.iter().all(|m| m.donor == donors[0]));
    let recipient_principals: BTreeSet<_> = aid
        .children
        .iter()
        .filter(|c| extra_classes.contains(node_name(&c.class_subject)))
        .map(|c| c.principal)
        .collect();
    assert_eq!(
        recipient_principals,
        aid.mandates.iter().map(|m| m.recipient).collect()
    );
    extra_classes.len()
}

fn assert_inactive_recipient(
    child: &babylon_persistence::national_economy::AidChildCapture,
    rows: &StableGraphStateRows,
) {
    let class = node_name(&child.class_subject);
    assert_eq!((child.employed, child.reserve), (0, 0));
    assert_eq!((child.persons, child.households, child.inactive), (4, 4, 4));
    let county = match class {
        "wayne-aid-recipient-inactive" => "26163",
        "cook-aid-recipient-inactive" => "17031",
        _ => panic!("unexpected captured recipient class"),
    };
    assert_eq!(
        child.location,
        babylon_kernel::economic_location::EconomicLocation::domestic_county(
            babylon_kernel::geography::CountyGeoid::try_from(county).unwrap()
        )
        .unwrap()
    );
    let attributes: BTreeSet<_> = rows
        .node_f64()
        .iter()
        .filter(|(name, _, _)| name == class)
        .map(|(_, name, bits)| (name.as_str(), *bits))
        .collect();
    assert_eq!(
        attributes,
        BTreeSet::from([
            ("social-class/employed-population", 0_f64.to_bits()),
            ("social-class/reserve-population", 0_f64.to_bits()),
        ])
    );
}

fn node_name(key: &StableElementKey) -> &str {
    match key {
        StableElementKey::Node {
            scenario,
            local_name,
        } => {
            assert_eq!(
                scenario,
                babylon_persistence::national_economy::NATIONAL_SCENARIO_ID
            );
            local_name
        }
        _ => panic!("expected a captured national node"),
    }
}

#[test]
fn absent_duplicate_or_forged_sources_never_fall_back_to_current_files() {
    let mut missing = input();
    missing
        .sources
        .retain(|source| source.kind() != Kind::NationalCohorts);
    assert!(CapturedEconomicCatalog::capture(missing, None).is_err());
    let mut absent_households = input();
    absent_households
        .sources
        .retain(|source| source.kind() != Kind::NationalHouseholds);
    assert!(CapturedEconomicCatalog::capture(absent_households, None).is_err());
    let mut duplicate = input();
    duplicate.sources.push(duplicate.sources[0].clone());
    assert!(CapturedEconomicCatalog::capture(duplicate, None).is_err());
    let mut changed = input();
    let index = changed
        .sources
        .iter()
        .position(|row| row.kind() == Kind::NationalCounties)
        .unwrap();
    let mut bytes = changed.sources[index].bytes().to_vec();
    bytes[20] ^= 1;
    changed.sources[index] = SourceArtifact::capture(Kind::NationalCounties, bytes);
    assert!(CapturedEconomicCatalog::capture(changed, None).is_err());
}
