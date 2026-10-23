//! Exact physical citations preserve logical disclosure and typed decoding.
use super::*;

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_existing_page_provenance_resolves_without_writes_or_locks() {
    let target = LiveWorkerTarget::create("provenanceread", 0x34333, 1);
    let campaign = target.campaign_id;
    let mut client = target.config.connect(NoTls).unwrap();
    let first = ArchiveCitation::try_new("page-read".to_owned(), "first".to_owned()).unwrap();
    let second = ArchiveCitation::try_new("page-read".to_owned(), "second".to_owned()).unwrap();
    let refs =
        [&first, &second].map(|citation| seed_page_citation(&mut client, campaign, citation));
    let foreign = CampaignId::from_uuid(Uuid::from_u128(0x34334));
    client.execute(
        "INSERT INTO babylon_meta.campaign(campaign_id,slug,engine_version,defines_hash) \
         SELECT $1,'foreign-page-citation',engine_version,defines_hash FROM babylon_meta.campaign WHERE campaign_id=$2",
        &[foreign.as_uuid(), campaign.as_uuid()],
    ).unwrap();
    let foreign_citation =
        ArchiveCitation::try_new("page-read".to_owned(), "foreign".to_owned()).unwrap();
    seed_page_citation(&mut client, foreign, &foreign_citation);
    let before: i64 = client
        .query_one(
            "SELECT count(*) FROM babylon_meta.archive_provenance_v1",
            &[],
        )
        .unwrap()
        .get(0);
    let mut transaction = client.build_transaction().read_only(true).start().unwrap();
    let resolved = crate::archive_provenance::resolve_ordered(
        &mut transaction,
        campaign,
        &[&second, &first, &second],
    )
    .unwrap();
    assert_eq!(
        resolved,
        vec![refs[1], refs[0], refs[1]],
        "exact position and multiplicity survive"
    );
    let locks: i64 = transaction
        .query_one(
            "SELECT count(*) FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='advisory'",
            &[],
        )
        .unwrap()
        .get(0);
    assert_eq!(
        locks, 0,
        "resolving existing frozen citations takes no write lock"
    );
    let missing = ArchiveCitation::try_new("page-read".to_owned(), "missing".to_owned()).unwrap();
    for unavailable in [&missing, &foreign_citation] {
        assert!(matches!(
            crate::archive_provenance::resolve_ordered(
                &mut transaction,
                campaign,
                &[&first, unavailable],
            ),
            Err(SemanticArchiveError::StoredPageMismatch)
        ));
    }
    assert_eq!(
        crate::archive_provenance::resolve_ordered(&mut transaction, campaign, &[]).unwrap(),
        Vec::<i32>::new()
    );
    let after: i64 = transaction
        .query_one(
            "SELECT count(*) FROM babylon_meta.archive_provenance_v1",
            &[],
        )
        .unwrap()
        .get(0);
    assert_eq!(
        after, before,
        "unresolved frozen citations never create definitions"
    );
    transaction.rollback().unwrap();
    assert_duplicate_cannot_mask_missing_citation(&mut client, campaign, &first, &missing);
    drop(client);
    target.finish();
}

fn assert_duplicate_cannot_mask_missing_citation(
    client: &mut postgres::Client,
    campaign: CampaignId,
    existing: &ArchiveCitation,
    missing: &ArchiveCitation,
) {
    let mut transaction = client.transaction().unwrap();
    transaction.batch_execute("ALTER TABLE babylon_meta.archive_provenance_v1 DISABLE TRIGGER archive_provenance_guard_v1").unwrap();
    transaction
        .execute(
            "INSERT INTO babylon_meta.archive_provenance_v1 \
         SELECT campaign_id,max(provenance_ref)+1,$2,$3 FROM babylon_meta.archive_provenance_v1 \
         WHERE campaign_id=$1 GROUP BY campaign_id",
            &[
                campaign.as_uuid(),
                &existing.source_id(),
                &existing.locator(),
            ],
        )
        .unwrap();
    assert!(matches!(
        crate::archive_provenance::resolve_ordered(
            &mut transaction,
            campaign,
            &[existing, missing],
        ),
        Err(SemanticArchiveError::StoredPageMismatch)
    ));
    transaction.rollback().unwrap();
}

fn seed_page_citation(
    client: &mut postgres::Client,
    campaign: CampaignId,
    citation: &ArchiveCitation,
) -> i32 {
    client
        .query_one(
            "SELECT babylon_meta.archive_provenance_intern_v1($1::uuid,$2::text,$3::text)",
            &[
                campaign.as_uuid(),
                &citation.source_id(),
                &citation.locator(),
            ],
        )
        .unwrap()
        .get(0)
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_provenance_lookup_preserves_exact_frozen_witnesses_and_atomic_retry() {
    let target = LiveWorkerTarget::create("provenance", 0x34331, 1);
    let mut client = target.config.connect(NoTls).unwrap();
    let campaign = target.campaign_id;
    let distinct = assert_exact_interning_and_retry(&mut client, campaign);
    let other = CampaignId::from_uuid(Uuid::from_u128(0x34332));
    assert_missing_and_foreign_references(&mut client, campaign, other);
    install_reader_role(&target.config).unwrap();
    assert_private_definitions(&mut client);
    ArchiveWorker::new(&target.config)
        .sweep_once(campaign, &StubPageProducer)
        .unwrap();
    let healthy: i64 = client
        .query_one(
            "SELECT count(*) FROM public.v_archive_revision_known_v2 WHERE campaign_id=$1",
            &[campaign.as_uuid()],
        )
        .unwrap()
        .get(0);
    assert_eq!(healthy, 1);
    for mutation in [
        "UPDATE babylon_meta.archive_knowledge_grant_v1 SET provenance_ref=$2 WHERE campaign_id=$1 AND grant_key='subject'",
        "UPDATE babylon_meta.archive_page_revision_v2 SET grant_provenance_refs[1]=$2 WHERE campaign_id=$1",
    ] {
        let mut transaction = client.transaction().unwrap();
        assert!(transaction.execute(mutation, &[campaign.as_uuid(), &distinct]).unwrap() > 0);
        transaction.batch_execute("SET ROLE babylon_reader").unwrap();
        let withheld: i64 = transaction.query_one("SELECT count(*) FROM public.v_archive_revision_known_v2 WHERE campaign_id=$1", &[campaign.as_uuid()]).unwrap().get(0);
        assert_eq!(withheld, 0, "changed current or frozen citation withholds the body");
        transaction.batch_execute("RESET ROLE").unwrap();
        transaction.rollback().unwrap();
    }
    let mut transaction = client.transaction().unwrap();
    let failure = transaction.execute("UPDATE babylon_meta.archive_page_revision_v2 SET grant_provenance_refs[1]=$2 WHERE campaign_id=$1", &[campaign.as_uuid(), &i32::MAX]).unwrap_err();
    assert_eq!(
        failure.code(),
        Some(&postgres::error::SqlState::FOREIGN_KEY_VIOLATION)
    );
    transaction.rollback().unwrap();
    let retry = ArchiveWorker::new(&target.config)
        .sweep_once(campaign, &StubPageProducer)
        .unwrap();
    assert_eq!(retry.verified_tick(), 1);
    assert_eq!(receipt_consumption_count(&target.config, campaign), 1);
    with_reader(&target.config, |reader| {
        let scope = scope_at(&target.config, campaign, 1);
        let dossier = reader
            .dossier_as_of(
                &scope,
                &stub_subject_spec(1).page_ref,
                &ArchiveDossierBounds::default(),
            )
            .unwrap();
        assert!(
            matches!(dossier.state, ArchiveDossierState::Ready { .. }),
            "actual typed read reconstructs canonical citations"
        );
    });
    drop(client);
    target.finish();
}

fn assert_exact_interning_and_retry(client: &mut postgres::Client, campaign: CampaignId) -> i32 {
    let intern_sql = "SELECT babylon_meta.archive_provenance_intern_v1($1::uuid,$2::text,$3::text)";
    let exact: i32 = client
        .query_one(
            intern_sql,
            &[campaign.as_uuid(), &"provenance-screen", &"exact/locator"],
        )
        .unwrap()
        .get(0);
    let repeat: i32 = client
        .query_one(
            intern_sql,
            &[campaign.as_uuid(), &"provenance-screen", &"exact/locator"],
        )
        .unwrap()
        .get(0);
    assert_eq!(
        exact, repeat,
        "equal complete strings resolve to one definition"
    );
    let distinct: i32 = client
        .query_one(
            intern_sql,
            &[campaign.as_uuid(), &"provenance-screen", &"exact/locator-2"],
        )
        .unwrap()
        .get(0);
    assert_ne!(
        exact, distinct,
        "a changed locator remains a distinct exact definition"
    );
    assert_eq!(distinct, exact + 1, "campaign references are dense");
    let rolled_back: i32 = {
        let mut transaction = client.transaction().unwrap();
        let value = transaction
            .query_one(
                intern_sql,
                &[campaign.as_uuid(), &"rollback-source", &"rollback-locator"],
            )
            .unwrap()
            .get(0);
        transaction.rollback().unwrap();
        value
    };
    let retried: i32 = client
        .query_one(
            intern_sql,
            &[campaign.as_uuid(), &"retry-source", &"retry-locator"],
        )
        .unwrap()
        .get(0);
    assert_eq!(
        rolled_back, retried,
        "rollback consumes no reference or definition"
    );
    for mutation in [
        "UPDATE babylon_meta.archive_provenance_v1 SET locator='mutated' WHERE campaign_id=$1 AND provenance_ref=$2",
        "DELETE FROM babylon_meta.archive_provenance_v1 WHERE campaign_id=$1 AND provenance_ref=$2",
    ] {
        let mut transaction = client.transaction().unwrap();
        let failure = transaction.execute(mutation, &[campaign.as_uuid(), &exact]).unwrap_err();
        assert_eq!(failure.code(), Some(&postgres::error::SqlState::OBJECT_NOT_IN_PREREQUISITE_STATE));
        transaction.rollback().unwrap();
    }
    distinct
}

fn assert_missing_and_foreign_references(
    client: &mut postgres::Client,
    campaign: CampaignId,
    other: CampaignId,
) {
    // Foreign references must exist in this database, so the failure proves
    // campaign qualification rather than absence in an unrelated clone.
    assert_eq!(client.execute(
        "INSERT INTO babylon_meta.campaign(campaign_id,slug,engine_version,defines_hash) \
         SELECT $1,'foreign-provenance',engine_version,defines_hash FROM babylon_meta.campaign WHERE campaign_id=$2",
        &[other.as_uuid(), campaign.as_uuid()],
    ).unwrap(), 1);
    let intern_sql = "SELECT babylon_meta.archive_provenance_intern_v1($1::uuid,$2::text,$3::text)";
    let largest: i32 = client.query_one("SELECT max(provenance_ref) FROM babylon_meta.archive_provenance_v1 WHERE campaign_id=$1", &[campaign.as_uuid()]).unwrap().get(0);
    let mut foreign_only = 0;
    for sequence in 0..=largest {
        foreign_only = client
            .query_one(
                intern_sql,
                &[
                    other.as_uuid(),
                    &"foreign-source",
                    &format!("foreign-locator-{sequence}"),
                ],
            )
            .unwrap()
            .get(0);
        if foreign_only > largest {
            break;
        }
    }
    assert!(
        foreign_only > largest,
        "the reference exists solely in the other campaign"
    );
    for invalid in [i32::MAX, foreign_only] {
        let mut transaction = client.transaction().unwrap();
        let failure = transaction.execute(
            "UPDATE babylon_meta.archive_knowledge_grant_v1 SET provenance_ref=$2 WHERE campaign_id=$1",
            &[campaign.as_uuid(), &invalid],
        ).unwrap_err();
        assert_eq!(
            failure.code(),
            Some(&postgres::error::SqlState::FOREIGN_KEY_VIOLATION)
        );
        transaction.rollback().unwrap();
    }
}

fn assert_private_definitions(client: &mut postgres::Client) {
    client.batch_execute("SET ROLE babylon_reader").unwrap();
    for relation in [
        "archive_provenance_v1",
        "archive_atom_witness_v1",
        "archive_knowledge_grant_witness_v1",
    ] {
        let failure = client
            .query(&format!("SELECT * FROM babylon_meta.{relation}"), &[])
            .unwrap_err();
        assert_eq!(
            failure.code(),
            Some(&postgres::error::SqlState::INSUFFICIENT_PRIVILEGE)
        );
    }
    client.batch_execute("RESET ROLE").unwrap();
}
