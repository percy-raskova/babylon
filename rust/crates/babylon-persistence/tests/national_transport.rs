use babylon_kernel::economic_location::{EconomicLocation, ForeignCounterpart, UsDependency};
use babylon_kernel::geography::CountyGeoid;

use babylon_persistence::national_transport;
use babylon_persistence::national_transport::{
    AllocationMode, CargoClass, NationalTransportReference, TransportMode,
};
use std::collections::BTreeMap;

#[test]
fn national_source_keeps_every_county_and_explicit_island_access() {
    let source = national_transport::national_transport_reference()
        .expect("the transport reference fixture loads");
    assert_eq!(source.county_access().len(), 3144);
    assert_eq!(source.period_days(), 28);
    let kalawao = EconomicLocation::domestic_county(
        CountyGeoid::try_from("15005").expect("the fixture value fits the target range"),
    )
    .expect("the fixture geoid names a domestic county");
    assert_eq!(
        source
            .location_node(kalawao)
            .expect("the fixture call `location_node` succeeds for the authored inputs")
            .id(),
        "county:15005"
    );
    for counterpart in ForeignCounterpart::ALL {
        assert!(source
            .location_node(EconomicLocation::Foreign(counterpart))
            .is_some());
    }
    for dependency in UsDependency::ALL {
        assert!(source
            .location_node(EconomicLocation::Dependency(dependency))
            .is_some());
    }
    assert!(source
        .links()
        .iter()
        .filter(|row| row.mode() == TransportMode::Air)
        .all(|row| row.cargo() == [CargoClass::General]));
    assert!(source.general_diameter() <= 16);
    assert!(!source.unavailable_bulk_access().is_empty());
}

#[test]
fn native_capture_refuses_changed_and_oversized_bytes() {
    assert!(NationalTransportReference::decode_pinned(&[]).is_err());
    assert!(NationalTransportReference::decode_pinned(&vec![0; 2_097_153]).is_err());
    let mut bytes = include_bytes!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../src/babylon/data/reference/transport/national_transport_reference_2024.json.gz"
    ))
    .to_vec();
    bytes[20] ^= 1;
    assert!(NationalTransportReference::decode_pinned(&bytes).is_err());
}

#[test]
fn source_modes_keep_distinct_county_zone_allocations() {
    let source = national_transport::national_transport_reference()
        .expect("the transport reference fixture loads");
    let access: BTreeMap<_, _> = source
        .county_access()
        .iter()
        .map(|row| (row.county, row.zone.as_str()))
        .collect();
    let differences: Vec<_> = source
        .county_factors()
        .iter()
        .filter(|row| access[&row.county] != row.zone)
        .collect();
    assert_eq!(differences.len(), 12);
    assert!(differences
        .iter()
        .all(|row| row.mode == AllocationMode::Pipeline && row.county.state_fips() == *b"09"));
    assert!(differences.iter().any(|row| row.county.as_str() == "09140"
        && row.zone == "091"
        && access[&row.county] == "092"));
}
