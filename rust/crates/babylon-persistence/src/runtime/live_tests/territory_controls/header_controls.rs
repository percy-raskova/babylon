use crate::runtime::RustPersistenceRuntimeError;
use babylon_kernel::content_digest::sha256_of;

fn header_savepoint(tx: &mut Transaction<'_>) {
    tx.batch_execute("SAVEPOINT territory_header_corruption; ALTER TABLE babylon_state.territory_definition_v1 DISABLE TRIGGER territory_definition_immutable_v1").unwrap();
}

fn enable_header_guard(tx: &mut Transaction<'_>) {
    tx.batch_execute("ALTER TABLE babylon_state.territory_definition_v1 ENABLE TRIGGER territory_definition_immutable_v1").unwrap();
}

fn restored_header(tx: &mut Transaction<'_>, campaign: CampaignId, expected: &[TerritoryStateRow]) {
    tx.batch_execute("ROLLBACK TO SAVEPOINT territory_header_corruption; RELEASE SAVEPOINT territory_header_corruption").unwrap();
    let canonical: Vec<_> = expected
        .iter()
        .map(|row| row.canonical_bytes().to_vec())
        .collect();
    for source in [
        StoredTickReadSource::Runtime,
        StoredTickReadSource::FullObserver,
    ] {
        assert_eq!(
            canonical_rows(tx, source, campaign, 1),
            canonical,
            "savepoint restores healthy canonical rows and trigger catalog"
        );
    }
    let enabled: String = tx.query_one("SELECT tgenabled::text FROM pg_catalog.pg_trigger WHERE tgrelid='babylon_state.territory_definition_v1'::regclass AND tgname='territory_definition_immutable_v1'", &[]).unwrap().try_get(0).unwrap();
    assert_eq!(enabled, "O");
}

fn assert_both_header_readers_refuse(tx: &mut Transaction<'_>, campaign: CampaignId) {
    for source in [
        StoredTickReadSource::Runtime,
        StoredTickReadSource::FullObserver,
    ] {
        assert!(
            matches!(
                CapturedMaterialRows::capture(tx, source, campaign, 1)
                    .and_then(CapturedMaterialRows::admit),
                Err(RustPersistenceRuntimeError::CampaignConflict)
            ),
            "{source:?} must authenticate count and canonical SHA outside envelope framing"
        );
    }
}

fn assert_header_corruption_refused(
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
    original: &[TerritoryStateRow],
    changed: &[TerritoryStateRow],
) {
    // Clear only this table's pending completeness/FK events before owner ALTER.
    // All target marker rows exist inside this rollback-only positive fixture.
    tx.batch_execute("SET CONSTRAINTS babylon_state.territory_definition_complete_v1, babylon_state.territory_definition_marker_v1 IMMEDIATE").unwrap();
    let digest = sha256_of(original[1].canonical_bytes());
    let id: i64 = tx.query_one("SELECT definition_id FROM babylon_state.territory_definition_v1 WHERE campaign_id=$1 AND canonical_sha256=$2", &[campaign.as_uuid(),&&digest[..]]).unwrap().try_get(0).unwrap();
    assert_ne!(digest, [0; 32]);
    header_savepoint(tx);
    tx.execute("UPDATE babylon_state.territory_definition_v1 SET canonical_sha256=$3 WHERE campaign_id=$1 AND definition_id=$2", &[campaign.as_uuid(),&id,&&[0_u8;32][..]]).unwrap();
    enable_header_guard(tx);
    assert_both_header_readers_refuse(tx, campaign);
    restored_header(tx, campaign, original);

    header_savepoint(tx);
    tx.execute("UPDATE babylon_state.territory_definition_v1 SET field_count=field_count+1 WHERE campaign_id=$1 AND definition_id=$2", &[campaign.as_uuid(),&id]).unwrap();
    enable_header_guard(tx);
    assert_both_header_readers_refuse(tx, campaign);
    restored_header(tx, campaign, original);

    // Lie that stored zero has the requested nonzero row's hash, without changing fields.
    // Digest bucket equality is only an accelerator; module must verify exact body.
    let claimed = sha256_of(changed[1].canonical_bytes());
    assert_ne!(digest, claimed);
    header_savepoint(tx);
    tx.execute("UPDATE babylon_state.territory_definition_v1 SET canonical_sha256=$3 WHERE campaign_id=$1 AND definition_id=$2", &[campaign.as_uuid(),&id,&&claimed[..]]).unwrap();
    enable_header_guard(tx);
    assert!(matches!(
        insert(tx, campaign, 5, changed),
        Err(RustPersistenceRuntimeError::TerritoryStorage(
            crate::territory_storage::Error::DefinitionDigest
        ))
    ));
    restored_header(tx, campaign, original);
}
