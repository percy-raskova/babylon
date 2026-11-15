//! Restricted credentials must refuse site books before any connection or data read.
use babylon_material_circuit::SiteId;
use babylon_persistence::identity::CampaignId;
use babylon_persistence::observer_reader::{
    ObserverEconomyError, ObserverEconomyReader, ObserverVisibility,
};
use babylon_persistence::site_financial_statements::SiteStatementsError;
use postgres::Config;
use uuid::Uuid;

#[test]
fn restricted_site_statements_refuse_before_connecting() {
    let mut config = Config::new();
    config
        .host("127.0.0.1")
        .port(1)
        .user("babylon_reader")
        .dbname("absent");
    let reader = ObserverEconomyReader::connect(&config, ObserverVisibility::KnownPreview)
        .expect("loopback configuration is admitted without connecting");
    assert_eq!(
        reader.site_financial_statements(
            CampaignId::from_uuid(Uuid::from_u128(1)),
            0,
            SiteId::from_bytes([1; 32])
        ),
        Err(SiteStatementsError::Read(ObserverEconomyError::Authority))
    );
}
