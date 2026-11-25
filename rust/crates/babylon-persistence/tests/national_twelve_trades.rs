//! The twelve-trade national scenario (policy schema 8): its sources, its compiler and, in later tasks, its world.
use babylon_persistence::economic_catalog::{
    self, CapturedEconomicCatalog, EconomicCatalogError, EconomicCatalogInput, SourceArtifact,
    SourceArtifactKind as Kind,
};
use babylon_persistence::{national_cohorts, national_trade_pay};

const SHIPPED: &[u8] = include_bytes!("../../../../content/scenarios/national/defines.toml");
const FIXTURE: &[u8] = include_bytes!("fixtures/national_twelve_trades.defines.toml");
const COHORTS_V1: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../src/babylon/data/reference/economy/national_cohort_reference_2024.csv.gz"
));
const MAPPING_V1: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../contracts/national_qcew_function_mapping_v1.json"
));

fn row(input: &EconomicCatalogInput, kind: Kind) -> Option<&SourceArtifact> {
    input.sources.iter().find(|row| row.kind() == kind)
}

fn replace(input: &mut EconomicCatalogInput, kind: Kind, bytes: &[u8]) {
    let slot = input
        .sources
        .iter_mut()
        .find(|row| row.kind() == kind)
        .expect("the row exists");
    *slot = SourceArtifact::capture(kind, bytes.to_vec());
}

#[test]
fn the_shipped_input_keeps_its_sources() {
    let shipped = economic_catalog::national_catalog_input();
    let again =
        economic_catalog::national_catalog_input_for(SHIPPED).expect("the shipped defines parse");
    assert_eq!(shipped.sources.len(), 16);
    assert_eq!(again.sources.len(), shipped.sources.len());
    for (a, b) in shipped.sources.iter().zip(&again.sources) {
        assert_eq!((a.kind(), a.bytes()), (b.kind(), b.bytes()));
    }
    assert!(row(&again, Kind::NationalTradePay).is_none());
}

#[test]
fn the_fixture_input_carries_the_v2_sources() {
    let input = economic_catalog::national_catalog_input_for(FIXTURE).expect("the fixture parses");
    assert_eq!(input.sources.len(), 17);
    let cohorts = national_cohorts::national_cohort_reference_v2().expect("v2 cohorts");
    let pay = national_trade_pay::national_trade_pay_reference().expect("pay table");
    let digest = |kind| row(&input, kind).expect("the row exists").digest();
    assert_eq!(digest(Kind::NationalCohorts), cohorts.artifact_sha256());
    assert_eq!(
        digest(Kind::CohortFunctionMapping),
        cohorts.function_mapping_sha256()
    );
    assert_eq!(digest(Kind::NationalTradePay), pay.artifact_sha256());
    assert_eq!(
        row(&input, Kind::NationalGamePolicy)
            .expect("policy")
            .bytes(),
        FIXTURE
    );
    assert_eq!(
        input.sources.last().map(SourceArtifact::kind),
        Some(Kind::NationalTradePay)
    );
}

#[test]
fn a_twelve_trade_policy_with_ten_trade_tables_is_refused() {
    let mut input =
        economic_catalog::national_catalog_input_for(FIXTURE).expect("the fixture parses");
    replace(&mut input, Kind::NationalCohorts, COHORTS_V1);
    replace(&mut input, Kind::CohortFunctionMapping, MAPPING_V1);
    assert_eq!(
        CapturedEconomicCatalog::capture(input, None).err(),
        Some(EconomicCatalogError::Source(Kind::NationalCohorts))
    );
    let mut input =
        economic_catalog::national_catalog_input_for(FIXTURE).expect("the fixture parses");
    input
        .sources
        .retain(|row| row.kind() != Kind::NationalTradePay);
    assert_eq!(
        CapturedEconomicCatalog::capture(input, None).err(),
        Some(EconomicCatalogError::Source(Kind::NationalTradePay))
    );
}

#[test]
fn a_ten_trade_policy_refuses_the_pay_table() {
    let mut input = economic_catalog::national_catalog_input();
    let pay = national_trade_pay::national_trade_pay_reference().expect("pay table");
    assert_eq!(pay.rows().len(), 65_065);
    input.sources.push(SourceArtifact::capture(
        Kind::NationalTradePay,
        b"not the pay table".to_vec(),
    ));
    assert_eq!(
        CapturedEconomicCatalog::capture(input, None).err(),
        Some(EconomicCatalogError::UnexpectedSource(
            Kind::NationalTradePay
        ))
    );
}
