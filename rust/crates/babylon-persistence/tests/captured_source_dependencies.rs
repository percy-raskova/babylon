//! Reopening admits supplied artifacts and dependencies, without reacquiring files.
use babylon_persistence::{
    national_cohorts::NationalCohortReference, national_counties::NationalCountyReference,
    national_resident_workforce::NationalResidentWorkforceReference,
    national_transport::NationalTransportReference, world_reference::WorldReference,
};

const COUNTIES: &[u8] = include_bytes!(
    "../../../../src/babylon/data/reference/economy/national_county_reference_2024.csv.gz"
);
const COHORTS: &[u8] = include_bytes!(
    "../../../../src/babylon/data/reference/economy/national_cohort_reference_2024.csv.gz"
);
const RESIDENTS: &[u8] = include_bytes!(
    "../../../../src/babylon/data/reference/economy/national_resident_workforce_2024.csv.gz"
);
const TRANSPORT: &[u8] = include_bytes!(
    "../../../../src/babylon/data/reference/transport/national_transport_reference_2024.json.gz"
);
const TRADE: &[u8] = include_bytes!("../../../../src/babylon/data/reference/economy/international_counterpart_reference_2024.csv.gz");
const POPULATION: &[u8] = include_bytes!(
    "../../../../src/babylon/data/reference/economy/world_population_reference_2024.csv.gz"
);
const MAPPING: &[u8] =
    include_bytes!("../../../../contracts/national_qcew_function_mapping_v1.json");
const MEMBERSHIP: &[u8] =
    include_bytes!("../../../../contracts/international_counterpart_membership_v1.json");
const POPULATION_SCOPE: &[u8] =
    include_bytes!("../../../../contracts/world_population_scope_v1.json");
const TRANSPORT_POLICY: &[u8] =
    include_bytes!("../../../../contracts/national_transport_policy_v1.json");
const TRANSPORT_SOURCES: &[u8] =
    include_bytes!("../../../../tools/national_transport_2024_sources.json");

#[test]
fn explicit_captured_dependencies_reproduce_all_current_source_dimensions() {
    let counties = NationalCountyReference::decode_pinned(COUNTIES).unwrap();
    let cohorts = NationalCohortReference::decode_captured(COHORTS, MAPPING, &counties).unwrap();
    let residents =
        NationalResidentWorkforceReference::decode_captured(RESIDENTS, &counties).unwrap();
    let world =
        WorldReference::decode_captured(POPULATION, TRADE, MEMBERSHIP, POPULATION_SCOPE).unwrap();
    let transport = NationalTransportReference::decode_captured(
        TRANSPORT,
        TRANSPORT_POLICY,
        TRANSPORT_SOURCES,
        &counties,
    )
    .unwrap();
    assert_eq!(counties.counties().len(), 3144);
    assert_eq!(cohorts.groups().len(), 59058);
    assert_eq!(cohorts.admitted_cohorts().count(), 57238);
    assert_eq!(residents.counties().len(), 3144);
    assert_eq!(world.counterparts().len(), 12);
    assert_eq!(transport.county_access().len(), 3144);
    assert_eq!(transport.links().len(), 6870);
}

#[test]
fn changed_or_absent_captured_policy_never_uses_compiled_defaults() {
    let counties = NationalCountyReference::decode_pinned(COUNTIES).unwrap();
    assert!(NationalCohortReference::decode_captured(COHORTS, b"{}", &counties).is_err());
    assert!(WorldReference::decode_captured(POPULATION, TRADE, b"{}", POPULATION_SCOPE).is_err());
    assert!(WorldReference::decode_captured(POPULATION, TRADE, MEMBERSHIP, b"{}").is_err());
    assert!(NationalTransportReference::decode_captured(
        TRANSPORT,
        b"{}",
        TRANSPORT_SOURCES,
        &counties,
    )
    .is_err());
    assert!(NationalTransportReference::decode_captured(
        TRANSPORT,
        TRANSPORT_POLICY,
        b"{}",
        &counties,
    )
    .is_err());
    // Equal parsed source rows are insufficient: retain the exact provenance bytes.
    let mut altered_manifest = TRANSPORT_SOURCES.to_vec();
    altered_manifest.push(b'\n');
    assert!(NationalTransportReference::decode_captured(
        TRANSPORT,
        TRANSPORT_POLICY,
        &altered_manifest,
        &counties,
    )
    .is_err());
}
