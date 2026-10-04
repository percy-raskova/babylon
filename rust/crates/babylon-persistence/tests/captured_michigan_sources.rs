//! Michigan control source admission uses its captured inputs on reopening.
use babylon_persistence::{
    michigan_economy::{michigan_economy, MichiganEconomy},
    michigan_sectors::{michigan_county_sectors, MichiganCountySectors},
};

const COUNTIES: &[u8] = include_bytes!(
    "../../../../src/babylon/data/reference/economy/qcew_county_economics_mi_2024.csv.gz"
);
const SECTORS: &[u8] = include_bytes!(
    "../../../../src/babylon/data/reference/economy/qcew_county_sectors_mi_2024.csv.gz"
);
const MANIFEST: &[u8] =
    include_bytes!("../../../../tools/qcew_county_economics_v1_source_manifest.json");

#[test]
fn captured_michigan_source_bytes_reproduce_explicit_control_evidence() {
    let economy = MichiganEconomy::decode_captured(COUNTIES).unwrap();
    let sectors = MichiganCountySectors::decode_captured(SECTORS, MANIFEST).unwrap();
    assert_eq!(economy.counties().len(), 83);
    assert_eq!(economy.counties(), michigan_economy().unwrap().counties());
    assert_eq!(sectors.rows().len(), 1603);
    assert_eq!(sectors.rows(), michigan_county_sectors().unwrap().rows());
}

#[test]
fn missing_or_altered_control_sources_do_not_reacquire_compiled_defaults() {
    assert!(MichiganEconomy::decode_captured(b"").is_err());
    let mut changed_counties = COUNTIES.to_vec();
    changed_counties.push(0);
    assert!(MichiganEconomy::decode_captured(&changed_counties).is_err());
    assert!(MichiganCountySectors::decode_captured(SECTORS, b"{}").is_err());
    assert!(MichiganCountySectors::decode_captured(b"", MANIFEST).is_err());
    let mut changed_manifest = MANIFEST.to_vec();
    changed_manifest.push(b'\n');
    assert!(MichiganCountySectors::decode_captured(SECTORS, &changed_manifest).is_err());
}
