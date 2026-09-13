//! The admitted native command crosses the atomic register, Archive and restart path.
use super::*;
use babylon_persistence::{
    michigan_material::MichiganMaterialCatalog, runtime_session::*, ArchiveDossierProducer,
    ArchiveKnowledge, OrganizerDossierProducer, PendingArchiveReceipt, SemanticArchiveError,
};

fn command(
    runtime: &DurableMaterialRuntime,
    choice: OrganizerChoice,
    nonce: u8,
) -> OrganizerCommand {
    let snapshot = runtime.organizer_snapshot().unwrap();
    OrganizerCommand {
        campaign_id: *runtime.campaign_id().canonical_bytes(),
        actor_id: snapshot.view.actor_id,
        authority_id: snapshot.view.authority_id,
        expected_period: snapshot.view.period,
        content_digest: snapshot.view.content_digest,
        resource_digest: snapshot.view.resource_digest,
        nonce: [nonce; 16],
        choice,
    }
}
fn counts(config: &Config, campaign: CampaignId) -> Vec<i64> {
    let mut client = config.connect(NoTls).unwrap();
    let mut counts: Vec<i64> = [
        "tick_commit",
        "organizer_receipt_v1",
        "organizer_observation_v1",
        "organizer_subject_v1",
        "material_tick_v3",
    ]
    .into_iter()
    .map(|table| {
        client
            .query_one(
                &format!("SELECT count(*) FROM babylon_state.{table} WHERE campaign_id=$1"),
                &[campaign.as_uuid()],
            )
            .unwrap()
            .get(0)
    })
    .collect();
    counts.push(
        client
            .query_one(
                "SELECT count(*) FROM babylon_meta.archive_knowledge_grant_v1 WHERE campaign_id=$1",
                &[campaign.as_uuid()],
            )
            .unwrap()
            .get(0),
    );
    counts
}
fn qualify_durable_admission(
    runtime: &DurableMaterialRuntime,
    config: &Config,
) -> OrganizerCommitment {
    let campaign = runtime.campaign_id();
    let initial = runtime.organizer_snapshot().unwrap();
    assert_eq!(
        (
            initial.view.available_hours,
            initial.view.inquiry_hours,
            initial.view.contact_hours
        ),
        (16, 12, 8)
    );
    let hold = command(runtime, OrganizerChoice::Hold, 1);
    let accepted = runtime.submit_organizer_command(&hold).unwrap();
    assert_eq!(runtime.session().completed_tick(), 0);
    assert_eq!(runtime.submit_organizer_command(&hold).unwrap(), accepted);
    let mut reused = hold.clone();
    reused.choice = OrganizerChoice::Reinforce;
    assert_eq!(
        runtime.submit_organizer_command(&reused),
        Err(RuntimeSessionErrorCode::OrganizerNonceConflict)
    );
    let mut wrong = hold.clone();
    wrong.nonce = [2; 16];
    wrong.authority_id = [4; 16];
    assert_eq!(
        runtime.submit_organizer_command(&wrong),
        Err(RuntimeSessionErrorCode::OrganizerRefused)
    );
    // A malformed durable row must not masquerade as the accepted ruling.
    let mut writer = config.connect(NoTls).unwrap();
    writer.execute("UPDATE babylon_state.organizer_command_v1 SET commitment_sha256=$2 WHERE campaign_id=$1", &[campaign.as_uuid(), &&[0_u8;32][..]]).unwrap();
    assert_eq!(
        runtime.organizer_snapshot(),
        Err(RuntimeSessionErrorCode::StorageRefused)
    );
    writer.execute("UPDATE babylon_state.organizer_command_v1 SET commitment_sha256=$2 WHERE campaign_id=$1", &[campaign.as_uuid(), &&accepted.commitment_id[..]]).unwrap();
    accepted
}

fn qualify_failed_inquiry(
    runtime: &mut DurableMaterialRuntime,
    config: &Config,
) -> OrganizerCommand {
    let campaign = runtime.campaign_id();
    let concern = runtime.organizer_snapshot().unwrap();
    assert!(concern
        .view
        .observations
        .iter()
        .any(|row| matches!(row.report, OrganizerReport::ReducedWork { .. })));
    let inquiry = command(
        runtime,
        OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost),
        3,
    );
    let accepted = runtime.submit_organizer_command(&inquiry).unwrap();
    let before = runtime.session().material().canonical_bytes().to_vec();
    let before_counts = counts(config, campaign);
    let mut blocker = config.connect(NoTls).unwrap();
    let mut lock = blocker.transaction().unwrap();
    lock.batch_execute("LOCK TABLE babylon_state.organizer_observation_v1 IN SHARE MODE")
        .unwrap();
    let actions = runtime.next_action_batch().unwrap();
    assert!(matches!(
        runtime.advance_and_commit(&mut CollectingSink::default(), &actions),
        Err(babylon_persistence::material_runtime::MaterialRuntimeError::DatabaseLockRefused(_))
    ));
    assert_eq!(runtime.session().material().canonical_bytes(), before);
    assert_eq!(counts(config, campaign), before_counts);
    assert_eq!(
        runtime.organizer_snapshot().unwrap().pending,
        Some(accepted)
    );
    lock.rollback().unwrap();
    inquiry
}

fn qualify_earned_observation(
    runtime: &DurableMaterialRuntime,
    known: &ObserverEconomyReader,
    inquiry: &OrganizerCommand,
) -> u64 {
    let campaign = runtime.campaign_id();
    assert_eq!(
        runtime
            .submit_organizer_command(inquiry)
            .unwrap()
            .resolves_period,
        3,
        "lost acknowledgement retry survives resolution"
    );
    let after = runtime.organizer_snapshot().unwrap();
    let earned = after
        .view
        .observations
        .iter()
        .find(|row| row.acquired_period == 3 && matches!(row.report, OrganizerReport::Work { .. }))
        .unwrap();
    assert_eq!(earned.observed_period, 2);
    assert!(after.pending.is_none());
    assert!(known.snapshot(campaign, 3).unwrap().production.is_none());
    after.view.workplace_id
}

fn qualify_archive_history(
    config: &Config,
    reader: &SemanticArchiveReader,
    campaign: CampaignId,
    workplace_id: u64,
    held_scope: &ArchiveReadScope,
) {
    let mut worker = ArchiveWorker::new(config);
    let producer = CompositeArchiveDossierProducer::new(vec![
        Box::new(OrganizerDossierProducer::new(config)),
        Box::new(CountyDossierProducer::try_new(config).unwrap()),
        Box::new(PlaceDossierProducer::try_new(config).unwrap()),
    ]);
    for _ in 0..50 {
        if worker
            .sweep_once(campaign, &producer)
            .unwrap()
            .verified_tick()
            >= 3
        {
            break;
        }
    }
    assert_eq!(
        reader
            .archive_verification_status(campaign)
            .unwrap()
            .unwrap()
            .processed_tick(),
        3
    );
    let page_ref =
        ArchivePageRef::try_new(ArchiveSubjectKind::Workplace, workplace_id.to_string()).unwrap();
    let scope = current_archive_scope(reader, campaign);
    let reading = reader
        .dossier_as_of(
            &scope,
            &page_ref,
            &ArchiveDossierBounds::try_new(100, None).unwrap(),
        )
        .unwrap();
    let ArchiveDossierState::Ready { page, .. } = reading.state else {
        panic!("earned dossier is not ready")
    };
    assert!(page
        .markdown
        .contains("Observed period 2; acquired period 3"));
    assert!(!page.markdown.contains("provider inventory"));
    assert!(page.atoms.iter().any(|atom| atom.signal_key() == "subject"
        && atom.evidence_class() == ArchiveEvidenceClass::Designed));
    let historical = reader
        .dossier_as_of(
            held_scope,
            &page_ref,
            &ArchiveDossierBounds::try_new(100, None).unwrap(),
        )
        .unwrap();
    let ArchiveDossierState::Ready {
        page: historical, ..
    } = historical.state
    else {
        panic!("held organizer evidence is not ready")
    };
    assert!(!historical.markdown.contains("acquired period 3"));
    assert!(historical.markdown.contains("decreased"));
}

fn qualify_contact_and_pause(runtime: &mut DurableMaterialRuntime) {
    let reinforce = command(runtime, OrganizerChoice::Reinforce, 4);
    runtime.submit_organizer_command(&reinforce).unwrap();
    advance_material_period(runtime);
    let product = runtime
        .organizer_snapshot()
        .unwrap()
        .view
        .receipts
        .iter()
        .find(|receipt| receipt.period == 4)
        .unwrap()
        .contact_product_id
        .unwrap();
    advance_material_period(runtime);
    assert!(
        runtime
            .organizer_snapshot()
            .unwrap()
            .view
            .agreements
            .iter()
            .any(|row| row.source_product_id == Some(product)),
        "later agreement consumes the completed contact product"
    );
    let pause = command(runtime, OrganizerChoice::PauseStanding, 6);
    runtime.submit_organizer_command(&pause).unwrap();
    advance_material_period(runtime);
    assert_eq!(
        runtime
            .organizer_snapshot()
            .unwrap()
            .view
            .standing
            .paused_reason,
        Some(OrganizerPauseReason::Explicit)
    );
}

fn qualify_resume_and_horizon(runtime: &mut DurableMaterialRuntime, inquiry: &OrganizerCommand) {
    let resume = command(runtime, OrganizerChoice::ResumeStanding, 7);
    runtime.submit_organizer_command(&resume).unwrap();
    advance_material_period(runtime);
    assert!(
        runtime
            .organizer_snapshot()
            .unwrap()
            .view
            .standing
            .authorized
    );
    while runtime.session().completed_tick() < runtime.session().horizon() {
        advance_material_period(runtime);
    }
    let final_command = command(runtime, OrganizerChoice::Hold, 17);
    assert_eq!(
        runtime.preview_organizer_command(&final_command),
        Err(RuntimeSessionErrorCode::HorizonComplete)
    );
    assert_eq!(
        runtime.submit_organizer_command(&final_command),
        Err(RuntimeSessionErrorCode::HorizonComplete)
    );
    assert_eq!(
        runtime
            .submit_organizer_command(inquiry)
            .unwrap()
            .resolves_period,
        3
    );
    assert!(runtime.organizer_snapshot().unwrap().pending.is_none());
}

fn assert_projection_metadata_refused(
    runtime: &mut DurableMaterialRuntime,
    config: &Config,
    digest: [u8; 32],
    retry_tick: bool,
) {
    let campaign = runtime.campaign_id();
    let tail = runtime.tail().unwrap();
    let pending =
        PendingArchiveReceipt::try_new(tail.resolve_tick(), *tail.tick_content_hash().as_bytes())
            .unwrap();
    assert!(
        matches!(
            OrganizerDossierProducer::new(config).produce(
                *campaign.as_uuid(),
                &pending,
                &ArchiveKnowledge::try_new(Vec::new()).unwrap(),
                4,
            ),
            Err(SemanticArchiveError::StoredPageMismatch)
        ),
        "the Archive producer must refuse altered metadata before any restart"
    );
    assert!(
        matches!(
            DurableMaterialRuntime::open(config, campaign, digest),
            Err(babylon_persistence::material_runtime::MaterialRuntimeError::OrganizerStorage)
        ),
        "unchanged encoded bytes must not authenticate altered SQL metadata"
    );
    if retry_tick {
        let before = runtime.session().material().canonical_bytes().to_vec();
        let before_counts = counts(config, campaign);
        let actions = runtime.next_action_batch().unwrap();
        assert!(matches!(
            runtime.advance_and_commit(&mut CollectingSink::default(), &actions),
            Err(babylon_persistence::material_runtime::MaterialRuntimeError::OrganizerStorage)
        ));
        assert_eq!(runtime.session().material().canonical_bytes(), before);
        assert_eq!(
            counts(config, campaign),
            before_counts,
            "a changed key must not silently create a replacement row"
        );
    }
}

fn qualify_subject_metadata(
    runtime: &mut DurableMaterialRuntime,
    config: &Config,
    digest: [u8; 32],
) {
    let campaign = runtime.campaign_id();
    let organizer = runtime.session().material().organizer_config().unwrap();
    let actor = organizer.controlled_actor_id.to_string();
    let subject = organizer.workplace_id.to_string();
    let title = organizer.workplace_label.clone();
    let mut writer = config.connect(NoTls).unwrap();
    for (assignment, changed_title) in [
        ("actor_id=(actor_id::numeric+1)::text", title.clone()),
        ("subject_kind='organization'", title.clone()),
        ("subject_id=(subject_id::numeric+1)::text", title.clone()),
        ("title=title||' altered'", format!("{title} altered")),
    ] {
        assert_eq!(writer.execute(&format!("UPDATE babylon_state.organizer_subject_v1 SET {assignment} WHERE campaign_id=$1 AND subject_kind='workplace' AND subject_id=$2"), &[campaign.as_uuid(), &subject]).unwrap(), 1);
        assert_projection_metadata_refused(runtime, config, digest, true);
        assert_eq!(writer.execute("UPDATE babylon_state.organizer_subject_v1 SET actor_id=$2,subject_kind='workplace',subject_id=$3,title=$4 WHERE campaign_id=$1 AND title=$5", &[campaign.as_uuid(), &actor, &subject, &title, &changed_title]).unwrap(), 1);
    }
    assert_eq!(writer.execute("DELETE FROM babylon_state.organizer_subject_v1 WHERE campaign_id=$1 AND subject_kind='workplace' AND subject_id=$2", &[campaign.as_uuid(), &subject]).unwrap(), 1);
    assert_projection_metadata_refused(runtime, config, digest, true);
    writer.execute("INSERT INTO babylon_state.organizer_subject_v1 (campaign_id,actor_id,subject_kind,subject_id,title) VALUES ($1,$2,'workplace',$3,$4)", &[campaign.as_uuid(), &actor, &subject, &title]).unwrap();
    assert_eq!(writer.execute("INSERT INTO babylon_state.organizer_subject_v1 (campaign_id,actor_id,subject_kind,subject_id,title) VALUES ($1,($2::text::numeric+1)::text,'workplace',$3,$4)", &[campaign.as_uuid(), &actor, &subject, &title]).unwrap(), 1);
    assert_projection_metadata_refused(runtime, config, digest, true);
    writer
        .execute(
            "DELETE FROM babylon_state.organizer_subject_v1 WHERE campaign_id=$1 AND actor_id<>$2",
            &[campaign.as_uuid(), &actor],
        )
        .unwrap();
    let reopened = DurableMaterialRuntime::open(config, campaign, digest).unwrap();
    assert_eq!(
        reopened.session().material().canonical_bytes(),
        runtime.session().material().canonical_bytes()
    );
}

fn qualify_observation_metadata(
    runtime: &mut DurableMaterialRuntime,
    config: &Config,
    digest: [u8; 32],
) {
    let campaign = runtime.campaign_id();
    let observation = runtime
        .session()
        .material()
        .organizer_state()
        .unwrap()
        .observations
        .iter()
        .find(|row| row.acquired_period == 3)
        .unwrap()
        .clone();
    let bytes = serde_json::to_vec(&observation).unwrap();
    let mut writer = config.connect(NoTls).unwrap();
    for (assignment, retry_tick) in [
        ("subject_id=(subject_id::numeric+1)::text", true),
        ("observed_period=observed_period-1", false),
        ("acquired_period=acquired_period-1", false),
        ("observation_id=decode(repeat('fe',32),'hex')", true),
        (
            "observation_id=decode(repeat('fc',32),'hex'),actor_id=(actor_id::numeric+1)::text",
            true,
        ),
    ] {
        assert_eq!(writer.execute(&format!("UPDATE babylon_state.organizer_observation_v1 SET {assignment} WHERE campaign_id=$1 AND observation_bytes=$2"), &[campaign.as_uuid(), &bytes]).unwrap(), 1);
        assert_projection_metadata_refused(runtime, config, digest, retry_tick);
        let observed = i64::try_from(observation.observed_period).unwrap();
        let acquired = i64::try_from(observation.acquired_period).unwrap();
        writer.execute("UPDATE babylon_state.organizer_observation_v1 SET observation_id=$2,actor_id=$3,subject_id=$4,observed_period=$5,acquired_period=$6 WHERE campaign_id=$1 AND observation_bytes=$7", &[campaign.as_uuid(), &&observation.observation_id[..], &observation.actor_id.to_string(), &observation.subject_id.to_string(), &observed, &acquired, &bytes]).unwrap();
        let reopened = DurableMaterialRuntime::open(config, campaign, digest).unwrap();
        assert_eq!(
            reopened.session().material().canonical_bytes(),
            runtime.session().material().canonical_bytes()
        );
    }
}

fn qualify_receipt_metadata(
    runtime: &mut DurableMaterialRuntime,
    config: &Config,
    digest: [u8; 32],
) {
    let campaign = runtime.campaign_id();
    let receipt = runtime
        .session()
        .material()
        .organizer_state()
        .unwrap()
        .receipts
        .last()
        .unwrap()
        .clone();
    let bytes = serde_json::to_vec(&receipt).unwrap();
    let mut writer = config.connect(NoTls).unwrap();
    for (assignment, retry_tick) in [
        ("resolve_tick=resolve_tick-1", true),
        ("actor_id=(actor_id::numeric+1)::text", false),
        ("receipt_id=decode(repeat('fd',32),'hex')", true),
        (
            "receipt_id=decode(repeat('fb',32),'hex'),actor_id=(actor_id::numeric+1)::text",
            true,
        ),
    ] {
        assert_eq!(writer.execute(&format!("UPDATE babylon_state.organizer_receipt_v1 SET {assignment} WHERE campaign_id=$1 AND receipt_bytes=$2"), &[campaign.as_uuid(), &bytes]).unwrap(), 1);
        assert_projection_metadata_refused(runtime, config, digest, retry_tick);
        let period = i64::try_from(receipt.period).unwrap();
        writer.execute("UPDATE babylon_state.organizer_receipt_v1 SET receipt_id=$2,actor_id=$3,resolve_tick=$4 WHERE campaign_id=$1 AND receipt_bytes=$5", &[campaign.as_uuid(), &&receipt.receipt_id[..], &receipt.actor_id.to_string(), &period, &bytes]).unwrap();
        let reopened = DurableMaterialRuntime::open(config, campaign, digest).unwrap();
        assert_eq!(
            reopened.session().material().canonical_bytes(),
            runtime.session().material().canonical_bytes()
        );
    }
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and qualified statewide sources"]
fn organizer_durable_ruling_failure_retry_earned_history_and_contact_recovery() {
    let mut target = DisposableTarget::create();
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x9_26163));
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../content/scenarios/michigan/defines.toml");
    let catalog =
        MichiganMaterialCatalog::load_for_preset(&path, MichiganDeliveryPreset::OrganizeInWayne)
            .unwrap();
    let foundation = MichiganContentPreset::OrganizeInWayne
        .create_foundation_for_campaign(&catalog, campaign)
        .unwrap();
    let digest = foundation.digest();
    let mut runtime = DurableMaterialRuntime::create(&target.writer, campaign, foundation).unwrap();
    install_reader_role(&target.writer).unwrap();
    provision_observer_role(&target.writer).unwrap();
    let reader_config = target.login("babylon_reader", "organizer");
    let reader = SemanticArchiveReader::new(&reader_config).unwrap();
    let known =
        ObserverEconomyReader::connect(&reader_config, ObserverVisibility::KnownPreview).unwrap();
    assert!(known.snapshot(campaign, 0).unwrap().production.is_none());
    let accepted = qualify_durable_admission(&runtime, &target.writer);
    drop(runtime);
    runtime = DurableMaterialRuntime::open(&target.writer, campaign, digest).unwrap();
    assert_eq!(
        runtime.organizer_snapshot().unwrap().pending,
        Some(accepted)
    );
    advance_material_period(&mut runtime);
    advance_material_period(&mut runtime);
    let held_scope = current_archive_scope(&reader, campaign);
    let inquiry = qualify_failed_inquiry(&mut runtime, &target.writer);
    drop(runtime);
    runtime = DurableMaterialRuntime::open(&target.writer, campaign, digest).unwrap();
    advance_material_period(&mut runtime);
    let workplace_id = qualify_earned_observation(&runtime, &known, &inquiry);
    qualify_observation_metadata(&mut runtime, &target.writer, digest);
    qualify_receipt_metadata(&mut runtime, &target.writer, digest);
    qualify_subject_metadata(&mut runtime, &target.writer, digest);
    qualify_archive_history(&target.writer, &reader, campaign, workplace_id, &held_scope);
    qualify_contact_and_pause(&mut runtime);
    let saved = runtime.session().material().canonical_bytes().to_vec();
    drop(runtime);
    runtime = DurableMaterialRuntime::open(&target.writer, campaign, digest).unwrap();
    assert_eq!(runtime.session().material().canonical_bytes(), saved);
    qualify_resume_and_horizon(&mut runtime, &inquiry);
}
