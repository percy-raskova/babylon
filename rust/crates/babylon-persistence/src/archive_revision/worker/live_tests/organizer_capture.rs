//! The real organizer SQL capture ends before slow admission and rendering.
use super::*;
use crate::organizer_archive::capture_organizer_pages;
use crate::{ArchiveKnowledge, OrganizerDossierProducer};
use babylon_practice_contract::{OrganizerChoice, OrganizerCommand};

#[test]
#[ignore = "requires task-owned disposable PostgreSQL runtime and Wayne source artifacts"]
fn organizer_owned_capture_survives_short_idle_and_preserves_historical_proofs() {
    let base = validated_base_config();
    let template = validated_template_name();
    let database = TestDatabase::create_from_template(&base, &template, "organizercapture");
    let config = database.config(&base);
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x341_26163));
    let (runtime, receipt, later) = committed_organizer_periods(&config, campaign);
    let mut bounded = config.clone();
    bounded.options("-c idle_in_transaction_session_timeout=5000ms");
    let mut client = bounded.connect(NoTls).unwrap();
    let pid: i32 = client
        .query_one("SELECT pg_backend_pid()", &[])
        .unwrap()
        .get(0);
    let mut inspector = config.connect(NoTls).unwrap();
    let mut tx = client
        .build_transaction()
        .isolation_level(postgres::IsolationLevel::RepeatableRead)
        .read_only(true)
        .start()
        .unwrap();
    let captured = capture_organizer_pages(&mut tx, *campaign.as_uuid(), &receipt, 4).unwrap();
    tx.commit().unwrap();
    let idle: bool = inspector
        .query_one(
            "SELECT xact_start IS NULL FROM pg_stat_activity WHERE pid=$1",
            &[&pid],
        )
        .unwrap()
        .get(0);
    assert!(
        idle,
        "slow detached admission must start with no SQL transaction"
    );
    std::thread::sleep(std::time::Duration::from_millis(5100));
    client.simple_query("SELECT 1").unwrap();
    let (outcome, _) = captured.admit_and_render(None).unwrap();
    assert_eq!(outcome.batch().resolve_tick(), 1);
    assert_eq!(outcome.batch().pages().len(), 4);
    assert_eq!(outcome.remaining(), 0);

    // The mutable private command ledger is part of the requested-period proof.
    inspector.execute("UPDATE babylon_state.organizer_command_v1 SET consumed_period=NULL WHERE campaign_id=$1 AND nonce=$2", &[campaign.as_uuid(), &&[34_u8;16][..]]).unwrap();
    let mut tx = client.transaction().unwrap();
    let captured =
        crate::material_runtime::capture_archive_organizer_register(&mut tx, campaign, &receipt)
            .unwrap()
            .unwrap();
    tx.commit().unwrap();
    assert!(captured.admit(None).is_err());
    inspector.execute("UPDATE babylon_state.organizer_command_v1 SET consumed_period=1 WHERE campaign_id=$1 AND nonce=$2", &[campaign.as_uuid(), &&[34_u8;16][..]]).unwrap();

    let mut publisher = SemanticArchiveStore::new(&config)
        .connect("connect canonical capture control publication")
        .unwrap();
    let producer = OrganizerDossierProducer::new(&config);
    crate::archive_revision::publication::with_campaign_lock(&mut publisher, campaign, |client| {
        super::super::sweep_locked(
            client,
            campaign,
            &producer,
            &crate::ArchiveWorkerCancellation::default(),
            1,
        )
    })
    .unwrap();
    let original: Vec<u8> = inspector.query_one("SELECT initial_register_bytes FROM babylon_state.material_campaign_foundation_v3 WHERE campaign_id=$1", &[campaign.as_uuid()]).unwrap().get(0);
    inspector.execute("UPDATE babylon_state.material_campaign_foundation_v3 SET initial_register_bytes=$2 WHERE campaign_id=$1", &[campaign.as_uuid(), &vec![0_u8]]).unwrap();
    let knowledge = ArchiveKnowledge::try_new(Vec::new()).unwrap();
    let empty = producer
        .produce(*campaign.as_uuid(), &receipt, &knowledge, 4)
        .unwrap();
    assert!(empty.batch().pages().is_empty());
    assert_eq!(empty.remaining(), 0);
    assert!(
        producer
            .produce(*campaign.as_uuid(), &later, &knowledge, 4)
            .is_err(),
        "new work must still authenticate its foundation"
    );
    inspector.execute("UPDATE babylon_state.material_campaign_foundation_v3 SET initial_register_bytes=$2 WHERE campaign_id=$1", &[campaign.as_uuid(), &original]).unwrap();
    let recovered = producer
        .produce(*campaign.as_uuid(), &later, &knowledge, 4)
        .unwrap();
    assert_eq!(recovered.batch().pages().len(), 4);
    assert_eq!(recovered.batch().resolve_tick(), 2);
    // An admitted source never stands in for fresh campaign geography witnesses.
    inspector.execute("UPDATE babylon_state.campaign SET geography_scope='national-counties' WHERE campaign_id=$1", &[campaign.as_uuid()]).unwrap();
    let changed_geography = producer.produce(*campaign.as_uuid(), &later, &knowledge, 4);
    inspector.execute("UPDATE babylon_state.campaign SET geography_scope='michigan-control' WHERE campaign_id=$1", &[campaign.as_uuid()]).unwrap();
    assert!(matches!(
        changed_geography,
        Err(SemanticArchiveError::StoredPageMismatch)
    ));
    assert_eq!(
        producer
            .produce(*campaign.as_uuid(), &later, &knowledge, 4)
            .unwrap()
            .batch()
            .pages(),
        recovered.batch().pages(),
        "failed reuse must retain the last valid immutable source"
    );
    inspector.execute("UPDATE babylon_state.organizer_subject_v1 SET title=title || ' altered' WHERE campaign_id=$1", &[campaign.as_uuid()]).unwrap();
    assert!(
        matches!(
            producer.produce(*campaign.as_uuid(), &later, &knowledge, 4),
            Err(SemanticArchiveError::StoredPageMismatch)
        ),
        "new pages must refuse changed mutable subject metadata"
    );
    drop(runtime);
    drop(publisher);
    drop(client);
    drop(inspector);
    database.cleanup();
}

fn committed_organizer_periods(
    config: &Config,
    campaign: CampaignId,
) -> (
    DurableMaterialRuntime,
    PendingArchiveReceipt,
    PendingArchiveReceipt,
) {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../content/scenarios/michigan/defines.toml");
    let catalog = michigan_material::MichiganMaterialCatalog::load_for_preset(
        &path,
        michigan_material::MichiganDeliveryPreset::OrganizeInWayne,
    )
    .unwrap();
    let foundation = michigan_content::MichiganContentPreset::OrganizeInWayne
        .create_foundation_for_campaign(&catalog, campaign)
        .unwrap();
    let mut runtime = DurableMaterialRuntime::create(config, campaign, foundation).unwrap();
    let snapshot = runtime.organizer_snapshot().unwrap();
    runtime
        .submit_organizer_command(&OrganizerCommand {
            campaign_id: *campaign.canonical_bytes(),
            actor_id: snapshot.view.actor_id,
            authority_id: snapshot.view.authority_id,
            expected_period: snapshot.view.period,
            content_digest: snapshot.view.content_digest,
            resource_digest: snapshot.view.resource_digest,
            nonce: [34; 16],
            choice: OrganizerChoice::Hold,
        })
        .unwrap();
    let actions = runtime.next_action_batch().unwrap();
    let first = runtime
        .advance_and_commit(&mut CollectingSink::default(), &actions)
        .unwrap();
    let receipt =
        PendingArchiveReceipt::try_new(first.resolve_tick(), *first.tick_content_hash().as_bytes())
            .unwrap();
    let actions = runtime.next_action_batch().unwrap();
    let second = runtime
        .advance_and_commit(&mut CollectingSink::default(), &actions)
        .unwrap();
    let later = PendingArchiveReceipt::try_new(
        second.resolve_tick(),
        *second.tick_content_hash().as_bytes(),
    )
    .unwrap();
    (runtime, receipt, later)
}
