//! Check the captured NAICS cells against independently summed QCEW source rows.
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_persistence::national_cohorts;

#[test]
fn food_source_has_disjoint_codes_and_retains_suppressed_and_reported_cells() {
    let reference = national_cohorts::national_cohort_reference().expect("pinned QCEW source");
    let composition = reference
        .industry_composition(EconomicFunction::Food)
        .expect("checked job subtotals");
    assert_eq!(composition.artifact_sha256, reference.artifact_sha256());
    assert_eq!(
        composition.mapping_sha256,
        reference.function_mapping_sha256()
    );
    let codes: Vec<_> = composition.rows.iter().map(|r| r.naics.as_str()).collect();
    assert_eq!(codes, ["111", "112", "114", "1151", "1152", "311", "3121"]);
    let row = &composition.rows[5];
    assert_eq!(
        (row.known_jobs, row.published_cells, row.suppressed_cells),
        (1_446_647, 1_317, 1_332)
    );
}

#[test]
fn restricted_credentials_refuse_both_source_disclosures_before_database_access() {
    use babylon_material_circuit::SiteId;
    use babylon_persistence::identity::CampaignId;
    use babylon_persistence::observer_reader::{
        ObserverEconomyError, ObserverEconomyReader, ObserverVisibility,
    };
    use postgres::Config;
    use uuid::Uuid;

    let mut config = Config::new();
    config
        .host("127.0.0.1")
        .port(1)
        .user("babylon_reader")
        .dbname("absent");
    let reader = ObserverEconomyReader::connect(&config, ObserverVisibility::KnownPreview)
        .expect("bounded loopback target");
    let campaign = CampaignId::from_uuid(Uuid::from_u128(1));
    assert_eq!(
        reader.industry_source_composition(campaign, "absent", EconomicFunction::Food),
        Err(ObserverEconomyError::Authority)
    );
    assert_eq!(
        reader.site_source_member_codes(campaign, "absent", SiteId::from_bytes([1; 32])),
        Err(ObserverEconomyError::Authority)
    );
}
