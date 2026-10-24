//! The admitted native command crosses the atomic register, Archive and restart path.
use super::support;
use super::support::DisposableTarget;
use crate::ArchiveDossierBounds;
use crate::ArchiveDossierState;
use crate::ArchiveEvidenceClass;
use crate::ArchivePageRef;
use crate::ArchiveSubjectKind;
use crate::ArchiveWorker;
use crate::CampaignId;
use crate::CompositeArchiveDossierProducer;
use crate::CountyDossierProducer;
use crate::DurableMaterialRuntime;
use crate::MichiganContentPreset;
use crate::MichiganDeliveryPreset;
use crate::ObserverEconomyReader;
use crate::ObserverVisibility;
use crate::PlaceDossierProducer;
use crate::SemanticArchiveReader;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_persistence::archive_revision::ArchiveReadScope;
use babylon_persistence::michigan_material::MichiganMaterialCatalog;
use babylon_persistence::runtime_session::{
    OrganizerChoice, OrganizerCommand, OrganizerCommitment, OrganizerInquiry, OrganizerPauseReason,
    OrganizerReport, RuntimeSessionErrorCode,
};
use babylon_persistence::{
    ArchiveDossierProducer, ArchiveKnowledge, OrganizerDossierProducer, PendingArchiveReceipt,
    SemanticArchiveError,
};
use postgres::{Config, NoTls};
use std::path::Path;
use uuid::Uuid;

fn command(
    runtime: &DurableMaterialRuntime,
    choice: OrganizerChoice,
    nonce: u8,
) -> OrganizerCommand {
    let snapshot = runtime
        .organizer_snapshot()
        .expect("the fixture snapshot builds");
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
    let mut client = config
        .connect(NoTls)
        .expect("the test database accepts the connection");
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
            .expect("the seeded row is present exactly once")
            .get(0)
    })
    .collect();
    counts.push(
        client
            .query_one(
                "SELECT count(*) FROM babylon_meta.archive_knowledge_grant_v1 WHERE campaign_id=$1",
                &[campaign.as_uuid()],
            )
            .expect("the seeded row is present exactly once")
            .get(0),
    );
    counts
}
fn qualify_durable_admission(
    runtime: &DurableMaterialRuntime,
    config: &Config,
) -> OrganizerCommitment {
    let campaign = runtime.campaign_id();
    let initial = runtime
        .organizer_snapshot()
        .expect("the fixture snapshot builds");
    assert_eq!(
        (
            initial.view.available_hours,
            initial.view.inquiry_hours,
            initial.view.contact_hours
        ),
        (16, 12, 8)
    );
    let hold = command(runtime, OrganizerChoice::Hold, 1);
    let accepted = runtime
        .submit_organizer_command(&hold)
        .expect("the fixture submits the organizer command");
    assert_eq!(runtime.session().completed_tick(), 0);
    assert_eq!(
        runtime
            .submit_organizer_command(&hold)
            .expect("the fixture submits the organizer command"),
        accepted
    );
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
    let mut writer = config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    writer.execute("UPDATE babylon_state.organizer_command_v1 SET commitment_sha256=$2 WHERE campaign_id=$1", &[campaign.as_uuid(), &&[0_u8;32][..]]).expect("the test database applies the setup statement");
    assert_eq!(
        runtime.organizer_snapshot(),
        Err(RuntimeSessionErrorCode::StorageRefused)
    );
    writer.execute("UPDATE babylon_state.organizer_command_v1 SET commitment_sha256=$2 WHERE campaign_id=$1", &[campaign.as_uuid(), &&accepted.commitment_id[..]]).expect("the test database applies the setup statement");
    accepted
}

fn qualify_failed_inquiry(
    runtime: &mut DurableMaterialRuntime,
    config: &Config,
) -> OrganizerCommand {
    let campaign = runtime.campaign_id();
    let concern = runtime
        .organizer_snapshot()
        .expect("the fixture snapshot builds");
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
    let accepted = runtime
        .submit_organizer_command(&inquiry)
        .expect("the fixture submits the organizer command");
    let before = runtime.session().material().canonical_bytes().to_vec();
    let before_counts = counts(config, campaign);
    let mut blocker = config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let mut lock = blocker
        .transaction()
        .expect("the test database opens a transaction");
    lock.batch_execute("LOCK TABLE babylon_state.organizer_observation_v1 IN SHARE MODE")
        .expect("the test database applies the schema statements");
    let actions = runtime
        .next_action_batch()
        .expect("the fixture call `next_action_batch` succeeds for the authored inputs");
    assert!(matches!(
        runtime.advance_and_commit(&mut CollectingSink::default(), &actions),
        Err(babylon_persistence::material_runtime::MaterialRuntimeError::DatabaseLockRefused(_))
    ));
    assert_eq!(runtime.session().material().canonical_bytes(), before);
    assert_eq!(counts(config, campaign), before_counts);
    assert_eq!(
        runtime
            .organizer_snapshot()
            .expect("the fixture snapshot builds")
            .pending,
        Some(accepted)
    );
    lock.rollback().expect("the open transaction rolls back");
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
            .expect("the fixture submits the organizer command")
            .resolves_period,
        3,
        "lost acknowledgement retry survives resolution"
    );
    let after = runtime
        .organizer_snapshot()
        .expect("the fixture snapshot builds");
    let earned = after
        .view
        .observations
        .iter()
        .find(|row| row.acquired_period == 3 && matches!(row.report, OrganizerReport::Work { .. }))
        .expect("the fixture holds the searched element");
    assert_eq!(earned.observed_period, 2);
    assert!(after.pending.is_none());
    assert!(known
        .snapshot(campaign, 3)
        .expect("the fixture captures a consistent snapshot")
        .production
        .is_none());
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
        Box::new(
            CountyDossierProducer::try_new(config)
                .expect("the authored fixture satisfies the constructor invariants"),
        ),
        Box::new(
            PlaceDossierProducer::try_new(config)
                .expect("the authored fixture satisfies the constructor invariants"),
        ),
    ]);
    for _ in 0..50 {
        if worker
            .sweep_once(campaign, &producer)
            .expect("the fixture sweep completes")
            .verified_tick()
            >= 3
        {
            break;
        }
    }
    assert_eq!(
        reader
            .archive_verification_status(campaign)
            .expect(
                "the fixture call `archive_verification_status` succeeds for the authored inputs"
            )
            .expect("the nested fixture result is present")
            .processed_tick(),
        3
    );
    let page_ref = ArchivePageRef::try_new(ArchiveSubjectKind::Workplace, workplace_id.to_string())
        .expect("the authored fixture satisfies the constructor invariants");
    let scope = support::current_archive_scope(reader, campaign);
    let reading = reader
        .dossier_as_of(
            &scope,
            &page_ref,
            &ArchiveDossierBounds::try_new(100, None)
                .expect("the authored fixture satisfies the constructor invariants"),
        )
        .expect("the fixture dossier exists at the authored period");
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
            &ArchiveDossierBounds::try_new(100, None)
                .expect("the authored fixture satisfies the constructor invariants"),
        )
        .expect("the fixture dossier exists at the authored period");
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
    runtime
        .submit_organizer_command(&reinforce)
        .expect("the fixture submits the organizer command");
    support::advance_material_period(runtime);
    let product = runtime
        .organizer_snapshot()
        .expect("the fixture snapshot builds")
        .view
        .receipts
        .iter()
        .find(|receipt| receipt.period == 4)
        .expect("the fixture holds the searched element")
        .contact_product_id
        .expect("the fixture value `contact_product_id` is present before this read");
    support::advance_material_period(runtime);
    assert!(
        runtime
            .organizer_snapshot()
            .expect("the fixture snapshot builds")
            .view
            .agreements
            .iter()
            .any(|row| row.source_product_id == Some(product)),
        "later agreement consumes the completed contact product"
    );
    let pause = command(runtime, OrganizerChoice::PauseStanding, 6);
    runtime
        .submit_organizer_command(&pause)
        .expect("the fixture submits the organizer command");
    support::advance_material_period(runtime);
    assert_eq!(
        runtime
            .organizer_snapshot()
            .expect("the fixture snapshot builds")
            .view
            .standing
            .paused_reason,
        Some(OrganizerPauseReason::Explicit)
    );
}

fn qualify_resume_and_continuation(
    runtime: &mut DurableMaterialRuntime,
    inquiry: &OrganizerCommand,
) {
    let resume = command(runtime, OrganizerChoice::ResumeStanding, 7);
    runtime
        .submit_organizer_command(&resume)
        .expect("the fixture submits the organizer command");
    support::advance_material_period(runtime);
    assert!(
        runtime
            .organizer_snapshot()
            .expect("the fixture snapshot builds")
            .view
            .standing
            .authorized
    );
    assert_eq!(
        runtime.session().duration(),
        babylon_kernel::clock::CampaignDuration::Continuous
    );
    while runtime.session().completed_tick() < 17 {
        support::advance_material_period(runtime);
    }
    let final_command = command(runtime, OrganizerChoice::Hold, 17);
    assert!(runtime.preview_organizer_command(&final_command).is_ok());
    let admitted = runtime
        .submit_organizer_command(&final_command)
        .expect("the fixture submits the organizer command");
    assert_eq!(admitted.resolves_period, 18);
    assert_eq!(
        runtime
            .submit_organizer_command(inquiry)
            .expect("the fixture submits the organizer command")
            .resolves_period,
        3
    );
    assert_eq!(
        runtime
            .organizer_snapshot()
            .expect("the fixture snapshot builds")
            .pending,
        Some(admitted)
    );
}

fn assert_projection_metadata_refused(
    runtime: &mut DurableMaterialRuntime,
    config: &Config,
    digest: [u8; 32],
    retry_tick: bool,
) {
    let campaign = runtime.campaign_id();
    let tail = runtime
        .tail()
        .expect("the fixture sequence holds more than one row");
    let pending =
        PendingArchiveReceipt::try_new(tail.resolve_tick(), *tail.tick_content_hash().as_bytes())
            .expect("the authored fixture satisfies the constructor invariants");
    assert!(
        matches!(
            OrganizerDossierProducer::new(config).produce(
                *campaign.as_uuid(),
                &pending,
                &ArchiveKnowledge::try_new(Vec::new())
                    .expect("the authored fixture satisfies the constructor invariants"),
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
        let actions = runtime
            .next_action_batch()
            .expect("the fixture call `next_action_batch` succeeds for the authored inputs");
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
    let organizer = runtime
        .session()
        .material()
        .organizer_config()
        .expect("the fixture register carries organizer config");
    let actor = organizer.controlled_actor_id.to_string();
    let subject = organizer.workplace_id.to_string();
    let title = organizer.workplace_label.clone();
    let mut writer = config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    for (assignment, changed_title) in [
        ("actor_id=(actor_id::numeric+1)::text", title.clone()),
        ("subject_kind='organization'", title.clone()),
        ("subject_id=(subject_id::numeric+1)::text", title.clone()),
        ("title=title||' altered'", format!("{title} altered")),
    ] {
        assert_eq!(writer.execute(&format!("UPDATE babylon_state.organizer_subject_v1 SET {assignment} WHERE campaign_id=$1 AND subject_kind='workplace' AND subject_id=$2"), &[campaign.as_uuid(), &subject]).expect("the test database applies the setup statement"), 1);
        assert_projection_metadata_refused(runtime, config, digest, true);
        assert_eq!(writer.execute("UPDATE babylon_state.organizer_subject_v1 SET actor_id=$2,subject_kind='workplace',subject_id=$3,title=$4 WHERE campaign_id=$1 AND title=$5", &[campaign.as_uuid(), &actor, &subject, &title, &changed_title]).expect("the test database applies the setup statement"), 1);
    }
    assert_eq!(writer.execute("DELETE FROM babylon_state.organizer_subject_v1 WHERE campaign_id=$1 AND subject_kind='workplace' AND subject_id=$2", &[campaign.as_uuid(), &subject]).expect("the test database applies the setup statement"), 1);
    assert_projection_metadata_refused(runtime, config, digest, true);
    writer.execute("INSERT INTO babylon_state.organizer_subject_v1 (campaign_id,actor_id,subject_kind,subject_id,title) VALUES ($1,$2,'workplace',$3,$4)", &[campaign.as_uuid(), &actor, &subject, &title]).expect("the test database applies the setup statement");
    assert_eq!(writer.execute("INSERT INTO babylon_state.organizer_subject_v1 (campaign_id,actor_id,subject_kind,subject_id,title) VALUES ($1,($2::text::numeric+1)::text,'workplace',$3,$4)", &[campaign.as_uuid(), &actor, &subject, &title]).expect("the test database applies the setup statement"), 1);
    assert_projection_metadata_refused(runtime, config, digest, true);
    writer
        .execute(
            "DELETE FROM babylon_state.organizer_subject_v1 WHERE campaign_id=$1 AND actor_id<>$2",
            &[campaign.as_uuid(), &actor],
        )
        .expect("the test database applies the setup statement");
    let reopened = DurableMaterialRuntime::open(config, campaign, digest)
        .expect("the fixture opens the authored source");
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
        .expect("the fixture register carries organizer state")
        .observations
        .iter()
        .find(|row| row.acquired_period == 3)
        .expect("the fixture holds the searched element")
        .clone();
    let bytes =
        serde_json::to_vec(&observation).expect("the value serializes to canonical JSON bytes");
    let mut writer = config
        .connect(NoTls)
        .expect("the test database accepts the connection");
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
        assert_eq!(writer.execute(&format!("UPDATE babylon_state.organizer_observation_v1 SET {assignment} WHERE campaign_id=$1 AND observation_bytes=$2"), &[campaign.as_uuid(), &bytes]).expect("the test database applies the setup statement"), 1);
        assert_projection_metadata_refused(runtime, config, digest, retry_tick);
        let observed = i64::try_from(observation.observed_period)
            .expect("the fixture value fits the target range");
        let acquired = i64::try_from(observation.acquired_period)
            .expect("the fixture value fits the target range");
        writer.execute("UPDATE babylon_state.organizer_observation_v1 SET observation_id=$2,actor_id=$3,subject_id=$4,observed_period=$5,acquired_period=$6 WHERE campaign_id=$1 AND observation_bytes=$7", &[campaign.as_uuid(), &&observation.observation_id[..], &observation.actor_id.to_string(), &observation.subject_id.to_string(), &observed, &acquired, &bytes]).expect("the test database applies the setup statement");
        let reopened = DurableMaterialRuntime::open(config, campaign, digest)
            .expect("the fixture opens the authored source");
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
        .expect("the fixture register carries organizer state")
        .receipts
        .last()
        .expect("the fixture sequence is non-empty")
        .clone();
    let bytes = serde_json::to_vec(&receipt).expect("the value serializes to canonical JSON bytes");
    let mut writer = config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    for (assignment, retry_tick) in [
        ("resolve_tick=resolve_tick-1", true),
        ("actor_id=(actor_id::numeric+1)::text", false),
        ("receipt_id=decode(repeat('fd',32),'hex')", true),
        (
            "receipt_id=decode(repeat('fb',32),'hex'),actor_id=(actor_id::numeric+1)::text",
            true,
        ),
    ] {
        assert_eq!(writer.execute(&format!("UPDATE babylon_state.organizer_receipt_v1 SET {assignment} WHERE campaign_id=$1 AND receipt_bytes=$2"), &[campaign.as_uuid(), &bytes]).expect("the test database applies the setup statement"), 1);
        assert_projection_metadata_refused(runtime, config, digest, retry_tick);
        let period =
            i64::try_from(receipt.period).expect("the fixture value fits the target range");
        writer.execute("UPDATE babylon_state.organizer_receipt_v1 SET receipt_id=$2,actor_id=$3,resolve_tick=$4 WHERE campaign_id=$1 AND receipt_bytes=$5", &[campaign.as_uuid(), &&receipt.receipt_id[..], &receipt.actor_id.to_string(), &period, &bytes]).expect("the test database applies the setup statement");
        let reopened = DurableMaterialRuntime::open(config, campaign, digest)
            .expect("the fixture opens the authored source");
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
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../content/scenarios/michigan/defines.toml");
    let catalog =
        MichiganMaterialCatalog::load_for_preset(&path, MichiganDeliveryPreset::OrganizeInWayne)
            .expect("the preset content loads");
    let foundation = MichiganContentPreset::OrganizeInWayne
        .create_foundation_for_campaign(&catalog, campaign)
        .expect("the authored catalog builds the campaign foundation");
    let digest = foundation.digest();
    let mut runtime = DurableMaterialRuntime::create(&target.writer, campaign, foundation)
        .expect("the test database creates the fixture campaign");
    babylon_persistence::install_reader_role(&target.writer)
        .expect("the test database installs the reader role");
    babylon_persistence::observer_reader::provision_observer_role(&target.writer)
        .expect("the test database provisions the observer role");
    let reader_config = target.login("babylon_reader", "organizer");
    let reader = SemanticArchiveReader::new(&reader_config)
        .expect("the constructor accepts the authored fixture arguments");
    let known = ObserverEconomyReader::connect(&reader_config, ObserverVisibility::KnownPreview)
        .expect("the test database accepts the connection");
    assert!(known
        .snapshot(campaign, 0)
        .expect("the fixture captures a consistent snapshot")
        .production
        .is_none());
    let accepted = qualify_durable_admission(&runtime, &target.writer);
    drop(runtime);
    runtime = DurableMaterialRuntime::open(&target.writer, campaign, digest)
        .expect("the fixture opens the authored source");
    assert_eq!(
        runtime
            .organizer_snapshot()
            .expect("the fixture snapshot builds")
            .pending,
        Some(accepted)
    );
    support::advance_material_period(&mut runtime);
    support::advance_material_period(&mut runtime);
    let held_scope = support::current_archive_scope(&reader, campaign);
    let inquiry = qualify_failed_inquiry(&mut runtime, &target.writer);
    drop(runtime);
    runtime = DurableMaterialRuntime::open(&target.writer, campaign, digest)
        .expect("the fixture opens the authored source");
    support::advance_material_period(&mut runtime);
    let workplace_id = qualify_earned_observation(&runtime, &known, &inquiry);
    qualify_observation_metadata(&mut runtime, &target.writer, digest);
    qualify_receipt_metadata(&mut runtime, &target.writer, digest);
    qualify_subject_metadata(&mut runtime, &target.writer, digest);
    qualify_archive_history(&target.writer, &reader, campaign, workplace_id, &held_scope);
    qualify_contact_and_pause(&mut runtime);
    let saved = runtime.session().material().canonical_bytes().to_vec();
    drop(runtime);
    runtime = DurableMaterialRuntime::open(&target.writer, campaign, digest)
        .expect("the fixture opens the authored source");
    assert_eq!(runtime.session().material().canonical_bytes(), saved);
    qualify_resume_and_continuation(&mut runtime, &inquiry);
}
