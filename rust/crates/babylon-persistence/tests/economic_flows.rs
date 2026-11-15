//! Economic counterparties are restricted to the complete observer capability.
use babylon_persistence::identity::CampaignId;
use babylon_persistence::observer_reader::{
    ObserverEconomyError, ObserverEconomyReader, ObserverVisibility,
};
use postgres::Config;
use uuid::Uuid;

#[test]
fn restricted_economic_payments_refuse_before_connecting() {
    let mut config = Config::new();
    config
        .host("127.0.0.1")
        .port(1)
        .user("babylon_reader")
        .dbname("absent");
    let reader = ObserverEconomyReader::connect(&config, ObserverVisibility::KnownPreview)
        .expect("bounded loopback target");
    let mut cursor = None;
    assert_eq!(
        reader.committed_economic_payments_with_cursor(
            CampaignId::from_uuid(Uuid::from_u128(1)),
            1,
            &mut cursor
        ),
        Err(ObserverEconomyError::Authority),
    );
    assert!(cursor.is_none());
}
