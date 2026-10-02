//! Source-only economic authority, independently of the initial mutable checkpoint.
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
    assert_eq!(catalog.compiler_version(), "national-world-v1");
    assert_eq!(catalog.opening().sites.len(), 60_634);
    assert_eq!(catalog.opening().households.len(), 3_162);
    assert!(matches!(
        catalog.opening().capacity,
        CatalogCapacity::Rolling(babylon_material_circuit::RollingProcessSupply::Equipment(_))
    ));
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
    assert_eq!(original.foundation_graph().rows().nodes().len(), 129_865);
    eprintln!(
        "native foundation bytes: sources={source_bytes}, catalog={}, graph={}, register={}, complete={}, nodes={}",
        catalog_bytes,
        graph_bytes,
        original.initial_register().canonical_bytes().len(),
        original.canonical_bytes().len(),
        original.foundation_graph().rows().nodes().len(),
    );
    eprintln!(
        "native foundation SHA256: catalog={catalog_digest:02x?}, graph={graph_digest:02x?}, register={:02x?}, complete={:02x?}",
        original.initial_register().digest(),
        original.digest(),
    );
    let restored = babylon_persistence::material_runtime::MaterialRuntimeFoundation::decode(
        original.canonical_bytes(),
        original.digest(),
    )
    .unwrap();
    assert_eq!(restored.canonical_bytes(), original.canonical_bytes());
    assert_eq!(restored.initial_register(), original.initial_register());
    let catalog = restored
        .graph_foundation()
        .content_bundle()
        .economic_catalog()
        .unwrap();
    assert_eq!(catalog.opening(), &expected_opening);
}

#[test]
fn absent_duplicate_or_forged_sources_never_fall_back_to_current_files() {
    let mut missing = input();
    missing
        .sources
        .retain(|source| source.kind() != Kind::NationalCohorts);
    assert!(CapturedEconomicCatalog::capture(missing, None).is_err());
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
