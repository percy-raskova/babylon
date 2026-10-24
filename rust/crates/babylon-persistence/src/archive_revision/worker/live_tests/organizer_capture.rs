//! The real organizer SQL capture ends before slow admission and rendering.
use super::support;
use super::support::TestDatabase;
use crate::archive_worker::ArchiveDossierProducer;
use crate::identity::CampaignId;
use crate::material_runtime::ArchiveFoundationCandidate;
use crate::material_runtime::DurableMaterialRuntime;
use crate::organizer_archive;
use crate::ArchiveProducerOutcome;
use crate::ArchiveWorkerCancellation;
use crate::{
    michigan_content, michigan_material, PendingArchiveReceipt, SemanticArchiveError,
    SemanticArchiveStore,
};
use crate::{ArchiveKnowledge, OrganizerDossierProducer};
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_practice_contract::{OrganizerChoice, OrganizerCommand};
use michigan_content::MichiganContentPreset;
use michigan_material::MichiganDeliveryPreset;
use michigan_material::MichiganMaterialCatalog;
use postgres::Client;
use postgres::IsolationLevel;
use postgres::{Config, NoTls};
use std::path::Path;
use std::time::Duration;
use uuid::Uuid;

#[test]
#[ignore = "requires task-owned disposable PostgreSQL runtime and Wayne source artifacts"]
fn organizer_owned_capture_survives_short_idle_and_preserves_historical_proofs() {
    let base = support::validated_base_config();
    let template = support::validated_template_name();
    let database = TestDatabase::create_from_template(&base, &template, "organizercapture");
    let config = database.config(&base);
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x341_26163));
    let (runtime, receipt, later) = committed_organizer_periods(&config, campaign);
    let graph = crate::hydrate_campaign_foundation(&config, campaign).unwrap();
    let graph_bytes = graph.canonical_bytes().as_ptr();
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
        .isolation_level(IsolationLevel::RepeatableRead)
        .read_only(true)
        .start()
        .unwrap();
    let captured =
        organizer_archive::capture_organizer_pages(&mut tx, *campaign.as_uuid(), &receipt, 4)
            .unwrap();
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
    std::thread::sleep(Duration::from_millis(5100));
    client.simple_query("SELECT 1").unwrap();
    let (outcome, admitted) = captured
        .admit_and_render(Some(ArchiveFoundationCandidate::Graph(Box::new(graph))))
        .unwrap();
    assert_eq!(
        admitted
            .unwrap()
            .foundation()
            .graph_foundation()
            .canonical_bytes()
            .as_ptr(),
        graph_bytes,
        "cold factory source must move into material admission without decoding a second copy"
    );
    assert_eq!(outcome.batch().resolve_tick(), 1);
    assert_eq!(outcome.batch().pages().len(), 4);
    assert_eq!(outcome.remaining(), 0);
    cold_graph_candidate_checks_fresh_components_and_geography(&config, campaign, &receipt);

    assert_detached_capture_refuses_unconsumed_command(
        &mut client,
        &mut inspector,
        campaign,
        &receipt,
    );

    assert_published_work_reauthenticates_fresh_source(
        &config,
        campaign,
        &receipt,
        &later,
        &mut inspector,
    );
    drop(runtime);
    drop(client);
    drop(inspector);
    database.cleanup();
}

fn assert_published_work_reauthenticates_fresh_source(
    config: &postgres::Config,
    campaign: CampaignId,
    receipt: &PendingArchiveReceipt,
    later: &PendingArchiveReceipt,
    inspector: &mut Client,
) {
    let mut publisher = SemanticArchiveStore::new(config)
        .connect("connect canonical capture control publication")
        .unwrap();
    let producer = OrganizerDossierProducer::new(config);
    crate::archive_revision::publication::with_campaign_lock(&mut publisher, campaign, |client| {
        super::super::sweep_locked(
            client,
            campaign,
            &producer,
            &ArchiveWorkerCancellation::default(),
            1,
        )
    })
    .unwrap();
    let original: Vec<u8> = inspector.query_one("SELECT initial_register_bytes FROM babylon_state.material_campaign_foundation_v3 WHERE campaign_id=$1", &[campaign.as_uuid()]).unwrap().get(0);
    inspector.execute("UPDATE babylon_state.material_campaign_foundation_v3 SET initial_register_bytes=$2 WHERE campaign_id=$1", &[campaign.as_uuid(), &vec![0_u8]]).unwrap();
    let knowledge = ArchiveKnowledge::try_new(Vec::new()).unwrap();
    let empty = producer
        .produce(*campaign.as_uuid(), receipt, &knowledge, 4)
        .unwrap();
    assert!(empty.batch().pages().is_empty());
    assert_eq!(empty.remaining(), 0);
    assert!(
        producer
            .produce(*campaign.as_uuid(), later, &knowledge, 4)
            .is_err(),
        "new work must still authenticate its foundation"
    );
    inspector.execute("UPDATE babylon_state.material_campaign_foundation_v3 SET initial_register_bytes=$2 WHERE campaign_id=$1", &[campaign.as_uuid(), &original]).unwrap();
    let recovered = producer
        .produce(*campaign.as_uuid(), later, &knowledge, 4)
        .unwrap();
    assert_eq!(recovered.batch().pages().len(), 4);
    assert_eq!(recovered.batch().resolve_tick(), 2);
    assert_fresh_geography_and_subject_data(
        inspector, &producer, campaign, later, &knowledge, &recovered,
    );
}

fn assert_detached_capture_refuses_unconsumed_command(
    client: &mut Client,
    inspector: &mut Client,
    campaign: CampaignId,
    receipt: &PendingArchiveReceipt,
) {
    // The mutable private command ledger is part of the requested-period proof.
    inspector.execute("UPDATE babylon_state.organizer_command_v1 SET consumed_period=NULL WHERE campaign_id=$1 AND nonce=$2", &[campaign.as_uuid(), &&[34_u8;16][..]]).unwrap();
    let mut tx = client.transaction().unwrap();
    let captured =
        crate::material_runtime::capture_archive_organizer_register(&mut tx, campaign, receipt)
            .unwrap()
            .unwrap();
    tx.commit().unwrap();
    assert!(captured.admit(None).is_err());
    inspector.execute("UPDATE babylon_state.organizer_command_v1 SET consumed_period=1 WHERE campaign_id=$1 AND nonce=$2", &[campaign.as_uuid(), &&[34_u8;16][..]]).unwrap();
}

fn cold_graph_candidate_checks_fresh_components_and_geography(
    config: &postgres::Config,
    campaign: CampaignId,
    receipt: &PendingArchiveReceipt,
) {
    // Both refusals compare a fresh SQL capture with the same immutable source.
    // Hydrate that source once; move it into the final refusal after its first copy.
    let mut original_graph = Some(crate::hydrate_campaign_foundation(config, campaign).unwrap());
    for changed_geography in [false, true] {
        let graph = if changed_geography {
            original_graph.take().unwrap()
        } else {
            crate::material_runtime::persisted_graph_copy(original_graph.as_ref().unwrap())
        };
        let mut client = config.connect(NoTls).unwrap();
        let original: Vec<u8> = client
            .query_one(
                "SELECT content_bundle_bytes FROM babylon_state.campaign_foundation WHERE campaign_id=$1",
                &[campaign.as_uuid()],
            )
            .unwrap()
            .get(0);
        if changed_geography {
            client.execute("UPDATE babylon_state.campaign SET geography_scope='national-counties' WHERE campaign_id=$1", &[campaign.as_uuid()]).unwrap();
        } else {
            let mut changed = original.clone();
            changed.push(0);
            client.execute("UPDATE babylon_state.campaign_foundation SET content_bundle_bytes=$2 WHERE campaign_id=$1", &[campaign.as_uuid(), &changed]).unwrap();
        }
        let mut tx = client
            .build_transaction()
            .isolation_level(IsolationLevel::RepeatableRead)
            .read_only(true)
            .start()
            .unwrap();
        let captured =
            organizer_archive::capture_organizer_pages(&mut tx, *campaign.as_uuid(), receipt, 4)
                .unwrap();
        tx.commit().unwrap();
        let result =
            captured.admit_and_render(Some(ArchiveFoundationCandidate::Graph(Box::new(graph))));
        if changed_geography {
            client.execute("UPDATE babylon_state.campaign SET geography_scope='michigan-control' WHERE campaign_id=$1", &[campaign.as_uuid()]).unwrap();
        } else {
            client.execute("UPDATE babylon_state.campaign_foundation SET content_bundle_bytes=$2 WHERE campaign_id=$1", &[campaign.as_uuid(), &original]).unwrap();
        }
        assert!(
            matches!(result, Err(SemanticArchiveError::StoredPageMismatch)),
            "cold source sharing cannot substitute an old source for a changed fresh capture"
        );
    }
}

fn assert_fresh_geography_and_subject_data(
    inspector: &mut Client,
    producer: &OrganizerDossierProducer,
    campaign: CampaignId,
    later: &PendingArchiveReceipt,
    knowledge: &ArchiveKnowledge,
    recovered: &ArchiveProducerOutcome,
) {
    // An admitted source never stands in for fresh campaign geography witnesses.
    inspector.execute("UPDATE babylon_state.campaign SET geography_scope='national-counties' WHERE campaign_id=$1", &[campaign.as_uuid()]).unwrap();
    let changed_geography = producer.produce(*campaign.as_uuid(), later, knowledge, 4);
    inspector.execute("UPDATE babylon_state.campaign SET geography_scope='michigan-control' WHERE campaign_id=$1", &[campaign.as_uuid()]).unwrap();
    assert!(matches!(
        changed_geography,
        Err(SemanticArchiveError::StoredPageMismatch)
    ));
    assert_eq!(
        producer
            .produce(*campaign.as_uuid(), later, knowledge, 4)
            .unwrap()
            .batch()
            .pages(),
        recovered.batch().pages(),
        "failed reuse must retain the last valid immutable source"
    );
    inspector.execute("UPDATE babylon_state.organizer_subject_v1 SET title=title || ' altered' WHERE campaign_id=$1", &[campaign.as_uuid()]).unwrap();
    assert!(
        matches!(
            producer.produce(*campaign.as_uuid(), later, knowledge, 4),
            Err(SemanticArchiveError::StoredPageMismatch)
        ),
        "new pages must refuse changed mutable subject metadata"
    );
}

fn committed_organizer_periods(
    config: &Config,
    campaign: CampaignId,
) -> (
    DurableMaterialRuntime,
    PendingArchiveReceipt,
    PendingArchiveReceipt,
) {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../content/scenarios/michigan/defines.toml");
    let catalog =
        MichiganMaterialCatalog::load_for_preset(&path, MichiganDeliveryPreset::OrganizeInWayne)
            .unwrap();
    let foundation = MichiganContentPreset::OrganizeInWayne
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
