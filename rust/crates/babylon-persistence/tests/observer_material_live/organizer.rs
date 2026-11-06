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
use babylon_persistence::runtime_session::OrganizerSnapshot;
use babylon_persistence::runtime_session::{
    OrganizerChoice, OrganizerCommand, OrganizerCommitment, OrganizerInquiry, OrganizerPauseReason,
    OrganizerReport, RuntimeSessionErrorCode,
};
use babylon_persistence::{
    ArchiveDossierProducer, ArchiveKnowledge, OrganizerDossierProducer, PendingArchiveReceipt,
    SemanticArchiveError,
};
use babylon_practice_contract::OrganizerAllocation;
use babylon_practice_contract::OrganizerPartnerPolicy;
use babylon_practice_contract::OrganizerPeriodJournalEntries;
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
        allocation: OrganizerAllocation::None,
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
        .organizer_journal()
        .expect("the fixture register carries organizer journal")
        .periods
        .iter()
        .flat_map(|entries| &entries.observations)
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
        .organizer_journal()
        .expect("the fixture register carries organizer journal")
        .periods
        .iter()
        .flat_map(OrganizerPeriodJournalEntries::receipts)
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

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and national source"]
fn organizer_body_projection_limits_disclosure() {
    use babylon_graph::stable_element::StableElementKey;
    use babylon_graph::substrate::GraphSubstrate;
    use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
    use babylon_persistence::economic_catalog::CapturedEconomicCatalog;
    use babylon_persistence::runtime_session::{OrganizerBodyDisclosure, OrganizerBodySource};

    let target = DisposableTarget::create();
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7033));
    let foundation = CapturedEconomicCatalog::capture_national_campaign(
        babylon_persistence::economic_catalog::national_catalog_input(),
        campaign,
    )
    .expect("national capture")
    .create_foundation(
        ReplaySessionId::try_from("national-body-projection").expect("session"),
        ReplaySeed::new(319),
    )
    .expect("national foundation");
    let digest = foundation.digest();
    let runtime = DurableMaterialRuntime::create(&target.writer, campaign, foundation)
        .expect("create campaign");
    let opening = runtime.organizer_snapshot().expect("opening status");
    assert_eq!(
        opening.body_scope.source,
        Some(OrganizerBodySource::Foundation {
            foundation_digest: digest
        })
    );
    let OrganizerBodyDisclosure::Partial(part) = &opening.body else {
        panic!("controlled body is disclosed")
    };
    let graph = runtime.session().graph_session();
    let resolver = graph.stable_resolver();
    let edge = resolver
        .hyperedge_handle_by_local_name(&part.local_name)
        .expect("actual body handle");
    assert_eq!(part.runtime_hyperedge_id, edge.0);
    assert_eq!(
        resolver.hyperedge_key(edge).expect("sealed body"),
        &StableElementKey::Hyperedge {
            scenario: part.scenario.clone(),
            local_name: part.local_name.clone()
        }
    );
    let members = graph.graph().members_of(edge).expect("body incidence");
    let mut expected = opening
        .view
        .positions
        .iter()
        .filter_map(|position| {
            let name = format!("organizer-contributor-{}", position.contributor_id);
            let node = resolver.node_handle_by_local_name(&name).ok()?;
            members.contains(&node).then_some(position.contributor_id)
        })
        .collect::<Vec<_>>();
    expected.sort_unstable();
    expected.dedup();
    assert_eq!(part.contributors, expected);
    assert_eq!(
        part.contributors.len(),
        1,
        "the collective and its contributor form the disclosed pair"
    );
    let stable_key = (part.scenario.clone(), part.local_name.clone());
    drop(runtime);
    let reopened = DurableMaterialRuntime::open(&target.writer, campaign, digest).expect("reopen");
    let snapshot = reopened.organizer_snapshot().expect("reopened status");
    let OrganizerBodyDisclosure::Partial(part) = &snapshot.body else {
        panic!("reopened body")
    };
    assert_eq!(
        (&part.scenario, &part.local_name),
        (&stable_key.0, &stable_key.1),
        "stable identity survives reopening"
    );
    assert_eq!(part.contributors, expected);

    let (original_policy, original_hidden_contributor, original_body) =
        inspect_hidden_partner(&reopened, &snapshot);
    drop(reopened);
    assert_changed_partner_is_private(
        &target,
        original_policy,
        original_hidden_contributor,
        &original_body,
    );
    assert_michigan_body_unavailable(&target);
}

fn inspect_hidden_partner(
    reopened: &DurableMaterialRuntime,
    snapshot: &OrganizerSnapshot,
) -> (OrganizerPartnerPolicy, u64, Vec<u8>) {
    use babylon_graph::substrate::GraphSubstrate;
    let config = reopened
        .session()
        .material()
        .organizer_config()
        .expect("national organizer");
    let partner = &config.aid_bindings[0].partner;
    let hidden = config
        .participants
        .iter()
        .find(|participant| {
            participant
                .commitments
                .iter()
                .any(|commitment| commitment.actor_id == partner.actor_id)
        })
        .expect("partner-only contributor");
    assert!(!snapshot
        .view
        .positions
        .iter()
        .any(|position| position.contributor_id == hidden.contributor_id));
    let graph = reopened.session().graph_session();
    let resolver = graph.stable_resolver();
    let partner_edge = resolver
        .hyperedge_handle_by_local_name(&format!("organizer-participant-body-{}", partner.actor_id))
        .expect("partner body");
    let partner_members = graph
        .graph()
        .members_of(partner_edge)
        .expect("partner incidence");
    let hidden_node = resolver
        .node_handle_by_local_name(&format!("organizer-contributor-{}", hidden.contributor_id))
        .expect("hidden contributor node");
    assert!(
        partner_members.contains(&hidden_node),
        "partner-only contributor exists in actual graph"
    );
    assert!(
        !partner_members.contains(
            &resolver
                .node_handle_by_local_name("wayne-organizing-collective")
                .expect("controlled node")
        ),
        "partner body is not the controlled body"
    );
    let original_policy = partner.policy;
    let original_hidden_contributor = hidden.contributor_id;
    let original_body = serde_json::to_vec(&snapshot.body).expect("body disclosure serializes");
    (original_policy, original_hidden_contributor, original_body)
}

fn assert_changed_partner_is_private(
    target: &DisposableTarget,
    original_policy: OrganizerPartnerPolicy,
    original_hidden_contributor: u64,
    original_body: &[u8],
) {
    use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
    use babylon_persistence::economic_catalog::{
        self, CapturedEconomicCatalog, SourceArtifact, SourceArtifactKind,
    };
    // Capture a second complete foundation with a changed private partner policy.
    // Its graph and organizer register are produced and admitted together.
    let changed_campaign = CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7034));
    let mut input = economic_catalog::national_catalog_input();
    let policy = input
        .sources
        .iter_mut()
        .find(|source| source.kind() == SourceArtifactKind::NationalGamePolicy)
        .expect("captured policy");
    let original = std::str::from_utf8(policy.bytes()).expect("policy text");
    let changed = original
        .replace(
            "local_policy = \"participate\"",
            "local_policy = \"refuse\"",
        )
        .replace(
            "local_recipient_contributor_id = 2616302",
            "local_recipient_contributor_id = 2616399",
        );
    assert_ne!(original, changed, "private partner policy changed");
    *policy = SourceArtifact::capture(SourceArtifactKind::NationalGamePolicy, changed.into_bytes());
    let changed_foundation =
        CapturedEconomicCatalog::capture_national_campaign(input, changed_campaign)
            .expect("capture changed source")
            .create_foundation(
                ReplaySessionId::try_from("national-body-projection").expect("session"),
                ReplaySeed::new(319),
            )
            .expect("changed foundation");
    let changed_runtime =
        DurableMaterialRuntime::create(&target.writer, changed_campaign, changed_foundation)
            .expect("admit changed foundation");
    let changed_config = changed_runtime
        .session()
        .material()
        .organizer_config()
        .expect("changed organizer");
    assert_ne!(
        changed_config.aid_bindings[0].partner.policy, original_policy,
        "private state actually differs"
    );
    assert_ne!(
        changed_config.aid_bindings[0].recipient_contributor_id, original_hidden_contributor,
        "hidden partner contributor actually differs"
    );
    let changed_snapshot = changed_runtime
        .organizer_snapshot()
        .expect("changed status");
    assert_eq!(
        serde_json::to_vec(&changed_snapshot.body).expect("changed body serializes"),
        original_body,
        "private source change cannot change disclosed body bytes"
    );
}

fn assert_michigan_body_unavailable(target: &DisposableTarget) {
    use babylon_persistence::runtime_session::OrganizerBodyDisclosure;
    // The supported Michigan organizer has no attributed national body source.
    let michigan_campaign = CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7035));
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../content/scenarios/michigan/defines.toml");
    let catalog =
        MichiganMaterialCatalog::load_for_preset(&path, MichiganDeliveryPreset::OrganizeInWayne)
            .expect("Michigan preset");
    let foundation = MichiganContentPreset::OrganizeInWayne
        .create_foundation_for_campaign(&catalog, michigan_campaign)
        .expect("Michigan foundation");
    let other = DurableMaterialRuntime::create(&target.writer, michigan_campaign, foundation)
        .expect("admit Michigan opening");
    assert_eq!(
        other.organizer_snapshot().expect("Michigan status").body,
        OrganizerBodyDisclosure::Unavailable,
        "an unattributed scenario is not known absent"
    );
}

pub(crate) mod state_opponent {
    use super::OrganizerSnapshot;
    use super::{
        support, CampaignId, DisposableTarget, DurableMaterialRuntime, OrganizerChoice, Uuid,
    };
    use babylon_kernel::currency::Currency;
    use babylon_material_circuit::PublicBudgetReceipt;
    use babylon_persistence::economic_catalog::{self, NationalOpponent};
    use babylon_persistence::observer_reader;
    use babylon_practice_contract::CityPdConfig;
    use babylon_tick::material_world::MaterialTickReceipts;
    use postgres::Client;
    use serde_json::Value;

    fn qualify_marker_tampering(
        runtime: &DurableMaterialRuntime,
        writer: &mut Client,
        campaign: CampaignId,
    ) {
        use super::RuntimeSessionErrorCode;
        let marker = writer.query_one("SELECT tick_content_hash,envelope_digest FROM babylon_state.tick_commit WHERE campaign_id=$1 AND resolve_tick=2", &[campaign.as_uuid()]).expect("P2 marker");
        let tick_hash: Vec<u8> = marker.get(0);
        let envelope_digest: Vec<u8> = marker.get(1);
        for column in ["tick_content_hash", "envelope_digest"] {
            writer.execute(&format!("UPDATE babylon_state.tick_commit SET {column}=decode(repeat('fd',32),'hex') WHERE campaign_id=$1 AND resolve_tick=2"), &[campaign.as_uuid()]).expect("tamper marker");
            assert_eq!(
                runtime.organizer_snapshot(),
                Err(RuntimeSessionErrorCode::StaleExpectedTail)
            );
            writer.execute("UPDATE babylon_state.tick_commit SET tick_content_hash=$2,envelope_digest=$3 WHERE campaign_id=$1 AND resolve_tick=2", &[campaign.as_uuid(), &tick_hash, &envelope_digest]).expect("restore marker");
        }
    }

    #[derive(Clone, Copy)]
    enum HistoricalChecks {
        Separate,
        Required,
    }

    fn assert_historical_refusal(checks: HistoricalChecks, refuses: &impl Fn() -> bool) {
        if matches!(checks, HistoricalChecks::Required) {
            assert!(refuses());
        }
    }

    fn qualify_encounter_tampering(
        runtime: &DurableMaterialRuntime,
        config: &postgres::Config,
        campaign: CampaignId,
        historical_checks: HistoricalChecks,
    ) {
        use super::{
            ArchiveDossierProducer, ArchiveKnowledge, NoTls, OrganizerDossierProducer,
            PendingArchiveReceipt, RuntimeSessionErrorCode, SemanticArchiveError,
        };
        let tail = runtime.tail().expect("P2 marker");
        let pending_receipt = PendingArchiveReceipt::try_new(
            tail.resolve_tick(),
            *tail.tick_content_hash().as_bytes(),
        )
        .expect("P2 Archive receipt");
        let producer = OrganizerDossierProducer::new(config);
        let knowledge = ArchiveKnowledge::try_new(Vec::new()).expect("empty input knowledge");
        if matches!(historical_checks, HistoricalChecks::Required) {
            producer
                .produce(*campaign.as_uuid(), &pending_receipt, &knowledge, 4)
                .expect("exact historical capture renders");
        }
        let history_refuses = || {
            matches!(
                producer.produce(*campaign.as_uuid(), &pending_receipt, &knowledge, 4),
                Err(SemanticArchiveError::StoredPageMismatch)
            )
        };
        let mut writer = config.connect(NoTls).expect("writer");
        qualify_marker_tampering(runtime, &mut writer, campaign);
        let row = writer.query_one("SELECT receipt_id,actor_id,subject_id,resolve_tick,encounter_bytes FROM babylon_state.organizer_encounter_v1 WHERE campaign_id=$1", &[campaign.as_uuid()]).expect("exact one encounter");
        let receipt: Vec<u8> = row.get(0);
        let actor: String = row.get(1);
        let subject: String = row.get(2);
        let period: i64 = row.get(3);
        let bytes: Vec<u8> = row.get(4);
        for assignment in [
            "actor_id=(actor_id::numeric+1)::text",
            "subject_id=(subject_id::numeric+1)::text",
            "receipt_id=decode(repeat('fe',32),'hex')",
            "encounter_bytes=encounter_bytes||decode('00','hex')",
        ] {
            writer.execute(&format!("UPDATE babylon_state.organizer_encounter_v1 SET {assignment} WHERE campaign_id=$1"), &[campaign.as_uuid()]).expect("tamper");
            assert_eq!(
                runtime.organizer_snapshot(),
                Err(RuntimeSessionErrorCode::StorageRefused)
            );
            assert_historical_refusal(historical_checks, &history_refuses);
            writer.execute("UPDATE babylon_state.organizer_encounter_v1 SET receipt_id=$2,actor_id=$3,subject_id=$4,resolve_tick=$5,encounter_bytes=$6 WHERE campaign_id=$1", &[campaign.as_uuid(), &receipt, &actor, &subject, &period, &bytes]).expect("restore");
        }
        writer
            .execute(
                "DELETE FROM babylon_state.organizer_encounter_v1 WHERE campaign_id=$1",
                &[campaign.as_uuid()],
            )
            .expect("delete");
        assert_eq!(
            runtime.organizer_snapshot(),
            Err(RuntimeSessionErrorCode::StorageRefused)
        );
        assert_historical_refusal(historical_checks, &history_refuses);
        writer.execute("INSERT INTO babylon_state.organizer_encounter_v1 (campaign_id,receipt_id,actor_id,subject_id,resolve_tick,encounter_bytes) VALUES ($1,$2,$3,$4,$5,$6)", &[campaign.as_uuid(), &receipt, &actor, &subject, &period, &bytes]).expect("restore");
        writer.execute("INSERT INTO babylon_state.organizer_encounter_v1 (campaign_id,receipt_id,actor_id,subject_id,resolve_tick,encounter_bytes) VALUES ($1,decode(repeat('fd',32),'hex'),$2,$3,$4,$5)", &[campaign.as_uuid(), &actor, &subject, &period, &bytes]).expect("insert extra row");
        assert_eq!(
            runtime.organizer_snapshot(),
            Err(RuntimeSessionErrorCode::StorageRefused)
        );
        assert_historical_refusal(historical_checks, &history_refuses);
        writer.execute("DELETE FROM babylon_state.organizer_encounter_v1 WHERE campaign_id=$1 AND receipt_id=decode(repeat('fd',32),'hex')", &[campaign.as_uuid()]).expect("remove extra row");
        let grant = writer.query_one("SELECT subject_kind,subject_id,grant_key,granted_tick,provenance_ref FROM babylon_meta.archive_knowledge_grant_v1 WHERE campaign_id=$1 AND grant_key LIKE 'city-pd-%'", &[campaign.as_uuid()]).expect("encounter grant");
        let kind: String = grant.get(0);
        let grant_subject: String = grant.get(1);
        let key: String = grant.get(2);
        let tick: i64 = grant.get(3);
        let provenance: i32 = grant.get(4);
        writer.execute("INSERT INTO babylon_meta.archive_knowledge_grant_v1 (campaign_id,subject_kind,subject_id,grant_key,granted_tick,provenance_ref) VALUES ($1,$2,$3,'city-pd-unexpected',$4,$5)", &[campaign.as_uuid(), &kind, &grant_subject, &tick, &provenance]).expect("extra grant");
        assert_eq!(
            runtime.organizer_snapshot(),
            Err(RuntimeSessionErrorCode::StorageRefused)
        );
        assert_historical_refusal(historical_checks, &history_refuses);
        writer.execute("DELETE FROM babylon_meta.archive_knowledge_grant_v1 WHERE campaign_id=$1 AND grant_key='city-pd-unexpected'", &[campaign.as_uuid()]).expect("remove extra grant");
        writer.execute("UPDATE babylon_meta.archive_knowledge_grant_v1 SET provenance_ref=(SELECT provenance_ref FROM babylon_meta.archive_knowledge_grant_v1 WHERE campaign_id=$1 AND grant_key='subject' LIMIT 1) WHERE campaign_id=$1 AND grant_key=$2", &[campaign.as_uuid(), &key]).expect("alter citation");
        assert_eq!(
            runtime.organizer_snapshot(),
            Err(RuntimeSessionErrorCode::StorageRefused)
        );
        assert_historical_refusal(historical_checks, &history_refuses);
        writer.execute("UPDATE babylon_meta.archive_knowledge_grant_v1 SET provenance_ref=$3 WHERE campaign_id=$1 AND grant_key=$2", &[campaign.as_uuid(), &key, &provenance]).expect("restore citation");
        writer.execute("DELETE FROM babylon_meta.archive_knowledge_grant_v1 WHERE campaign_id=$1 AND grant_key=$2", &[campaign.as_uuid(), &key]).expect("delete grant");
        assert_eq!(
            runtime.organizer_snapshot(),
            Err(RuntimeSessionErrorCode::StorageRefused)
        );
        assert_historical_refusal(historical_checks, &history_refuses);
        writer.execute("INSERT INTO babylon_meta.archive_knowledge_grant_v1 (campaign_id,subject_kind,subject_id,grant_key,granted_tick,provenance_ref) VALUES ($1,$2,$3,$4,$5,$6)", &[campaign.as_uuid(), &kind, &grant_subject, &key, &tick, &provenance]).expect("restore grant");
        assert_eq!(
            runtime
                .organizer_snapshot()
                .expect("exact projection")
                .city_pd_encounters
                .len(),
            1
        );
    }

    #[derive(Clone, Copy)]
    enum EncounterDisclosure {
        Visible,
        Hidden,
    }

    fn qualify_restricted_encounter_page(
        target: &mut DisposableTarget,
        campaign: CampaignId,
        workplace: u64,
        p1_hash: [u8; 32],
        disclosure: EncounterDisclosure,
    ) {
        use super::{
            ArchiveDossierBounds, ArchiveDossierState, ArchivePageRef, ArchiveSubjectKind,
            ArchiveWorker, OrganizerDossierProducer, SemanticArchiveReader,
        };
        use babylon_persistence::archive_revision::ArchiveReadScope;
        let expected_visit = matches!(disclosure, EncounterDisclosure::Visible);
        let mut writer = target.writer.connect(super::NoTls).expect("writer");
        let subject_grants: i64 = writer.query_one("SELECT count(*) FROM babylon_meta.archive_knowledge_grant_v1 WHERE campaign_id=$1 AND subject_kind='workplace' AND subject_id=$2 AND grant_key='subject'", &[campaign.as_uuid(), &workplace.to_string()]).expect("opening workplace grant").get(0);
        assert_eq!(subject_grants, 1);
        babylon_persistence::install_reader_role(&target.writer).expect("restricted reader role");
        let reader_config = target.login(
            "babylon_reader",
            if expected_visit {
                "citypd"
            } else {
                "citypdother"
            },
        );
        let reader = SemanticArchiveReader::new(&reader_config).expect("restricted reader");
        let mut worker = ArchiveWorker::new(&target.writer);
        let producer = OrganizerDossierProducer::new(&target.writer);
        for _ in 0..50 {
            if worker
                .sweep_once(campaign, &producer)
                .expect("Archive sweep")
                .verified_tick()
                >= 2
            {
                break;
            }
        }
        let status = reader
            .archive_verification_status(campaign)
            .expect("status")
            .expect("campaign");
        assert_eq!(status.processed_tick(), 2);
        let page = ArchivePageRef::try_new(ArchiveSubjectKind::Workplace, workplace.to_string())
            .expect("workplace");
        let bounds = ArchiveDossierBounds::try_new(100, None).expect("bounds");
        let current = support::current_archive_scope(&reader, campaign);
        let result = reader
            .dossier_as_of(&current, &page, &bounds)
            .expect("current dossier");
        let ArchiveDossierState::Ready {
            page: current_page, ..
        } = result.state
        else {
            panic!("current dossier not ready")
        };
        assert_eq!(
            current_page
                .markdown
                .contains("published check-in records a City PD visit"),
            expected_visit
        );
        let historical = ArchiveReadScope::committed(campaign, 1, p1_hash).expect("P1 scope");
        let result = reader
            .dossier_as_of(&historical, &page, &bounds)
            .expect("historical dossier");
        let ArchiveDossierState::Ready {
            page: prior_page, ..
        } = result.state
        else {
            panic!("historical dossier not ready")
        };
        assert!(!prior_page
            .markdown
            .contains("published check-in records a City PD visit"));
    }

    fn assert_paid_encounter(
        runtime: &DurableMaterialRuntime,
        contact: [u8; 32],
    ) -> OrganizerSnapshot {
        use babylon_material_circuit::AgencyAttendanceOutcome;
        let register = runtime.session().material();
        let pd = register.city_pd().expect("PD");
        let [attempt] = pd.attempts.as_slice() else {
            panic!("one P2 attempt")
        };
        assert_eq!(attempt.funding.outcome, AgencyAttendanceOutcome::Paid);
        assert_eq!(attempt.funding.paid.micro_units(), 24_000_000);
        assert_eq!(attempt.funding.attended_hours, 1);
        assert_eq!(attempt.receipt.acquired_public_fact_ids, vec![contact]);
        assert!(attempt.receipt.player_witness_evidence_id.is_some());
        let snapshot = runtime.organizer_snapshot().expect("P2 snapshot");
        let json = serde_json::to_value(&snapshot).expect("snapshot serializes");
        let encounters = json
            .get("city_pd_encounters")
            .and_then(Value::as_array)
            .expect("actor-safe encounters are present");
        assert_eq!(
            encounters.len(),
            1,
            "the player can read the paid public check-in"
        );
        assert_eq!(
            snapshot.city_pd_encounters[0].receipt_id,
            attempt.receipt.receipt_id
        );
        assert_eq!(
            snapshot.city_pd_encounters[0].subject_id,
            snapshot.view.workplace_id
        );
        assert_eq!(
            snapshot.city_pd_encounters[0].visitor_actor_id,
            pd.config.actor_id
        );
        assert_eq!(
            snapshot.city_pd_encounters[0].controlled_actor_id,
            snapshot.view.actor_id
        );
        snapshot
    }

    #[test]
    #[ignore = "requires the task-owned disposable PostgreSQL runtime and national source"]
    fn national_city_pd_committed_contact_and_paid_visit_survive_restart() {
        run_witnessed(HistoricalChecks::Separate);
    }

    #[test]
    #[ignore = "requires the task-owned disposable PostgreSQL runtime and national source"]
    fn national_city_pd_matched_budget_controls_commit() {
        use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
        use babylon_persistence::economic_catalog::CapturedEconomicCatalog;
        use babylon_persistence::observer_reader::{ObserverEconomyReader, ObserverVisibility};

        let input = economic_catalog::national_catalog_input();
        let campaign = CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7034));
        let mut prior: Option<(CityPdConfig, Currency)> = None;
        let mut pd_allocations = Vec::new();
        for opponent in [NationalOpponent::CityPd, NationalOpponent::None] {
            let mut target = DisposableTarget::create();
            let foundation = CapturedEconomicCatalog::capture_national_campaign_with_opponent(
                input.clone(),
                campaign,
                opponent,
            )
            .expect("matched national capture")
            .create_foundation(
                ReplaySessionId::try_from("national-city-pd-paired-pg").expect("session"),
                ReplaySeed::new(319),
            )
            .expect("matched foundation");
            let mut runtime = DurableMaterialRuntime::create(&target.writer, campaign, foundation)
                .expect("persist opening");
            let config = assert_paired_opening(&runtime, opponent, &mut prior);
            observer_reader::provision_observer_role(&target.writer).expect("observer role");
            let observer_config = target.login("babylon_observer", "pdpair");
            let observer =
                ObserverEconomyReader::connect(&observer_config, ObserverVisibility::FullObserver)
                    .expect("observer");
            let reinforce = super::command(&runtime, OrganizerChoice::Reinforce, 42);
            runtime
                .submit_organizer_command(&reinforce)
                .expect("admit matched command");
            for tick in 1..=2 {
                support::advance_material_period(&mut runtime);
                let committed = observer
                    .committed_material_receipts(campaign, tick)
                    .expect("authenticated committed accounting");
                crate::city_pd_acceptance::assert_receipts(
                    &config,
                    &committed.receipts,
                    opponent == NationalOpponent::CityPd,
                );
                compare_paired_allocations(
                    &committed.receipts,
                    &config,
                    &mut pd_allocations,
                    opponent,
                    tick,
                );
                assert_eq!(
                    runtime.tail().expect("committed marker").resolve_tick(),
                    tick
                );
            }
            let snapshot = runtime
                .organizer_snapshot()
                .expect("committed player projection");
            assert_eq!(
                snapshot.city_pd_encounters.len(),
                usize::from(opponent == NationalOpponent::CityPd)
            );
        }
    }

    fn assert_paired_opening(
        runtime: &DurableMaterialRuntime,
        opponent: NationalOpponent,
        prior: &mut Option<(CityPdConfig, Currency)>,
    ) -> CityPdConfig {
        use babylon_material_circuit::{
            AccountId, CircuitAccounting, OrganizationAccountId, PublicAccountId,
        };
        use babylon_practice_contract::CityPdDecision;
        let config = if opponent == NationalOpponent::CityPd {
            let pd = runtime.session().material().city_pd().expect("captured PD");
            assert!(matches!(
                pd.state
                    .last_decision
                    .as_ref()
                    .expect("P0 decision")
                    .decision,
                CityPdDecision::NoFunds {
                    available_micros: 0,
                    ..
                }
            ));
            pd.config.clone()
        } else {
            assert!(runtime.session().material().city_pd().is_none());
            prior.as_ref().expect("PD run first").0.clone()
        };
        let CircuitAccounting::Monetary(money) = &runtime.session().material().state().accounting
        else {
            panic!("monetary opening")
        };
        let public = AccountId::Public(PublicAccountId::from_bytes(config.public_account_id));
        let opening_cash = money.book.cash(public).expect("public opening");
        if opponent == NationalOpponent::CityPd {
            let agency = AccountId::Organization(OrganizationAccountId::from_bytes(
                config.agency_account_id,
            ));
            assert_eq!(
                money
                    .book
                    .cash(agency)
                    .expect("agency opening")
                    .micro_units(),
                0
            );
            *prior = Some((config.clone(), opening_cash));
        } else {
            assert_eq!(opening_cash, prior.as_ref().expect("PD opening").1);
        }
        config
    }

    fn compare_paired_allocations(
        receipts: &MaterialTickReceipts,
        config: &CityPdConfig,
        pd_allocations: &mut Vec<Vec<PublicBudgetReceipt>>,
        opponent: NationalOpponent,
        tick: u64,
    ) {
        use babylon_material_circuit::{AccountId, OrganizationAccountId, PublicAccountId};
        let agency =
            AccountId::Organization(OrganizationAccountId::from_bytes(config.agency_account_id));
        let mut allocations: Vec<_> = receipts
            .public_budgets
            .iter()
            .filter(|row| {
                row.public_account == PublicAccountId::from_bytes(config.public_account_id)
                    && row.recipient != agency
            })
            .cloned()
            .collect();
        allocations.sort_by_key(|row| (row.recipient, row.treatment, row.priority));
        if opponent == NationalOpponent::CityPd {
            pd_allocations.push(allocations);
        } else {
            let enabled = &pd_allocations[usize::try_from(tick - 1).expect("tick index")];
            assert_eq!(
                enabled.len(),
                allocations.len(),
                "same non-agency budget claims"
            );
            for (left, right) in enabled.iter().zip(&allocations) {
                assert_eq!(
                    (
                        left.recipient,
                        left.treatment,
                        left.priority,
                        left.requested
                    ),
                    (
                        right.recipient,
                        right.treatment,
                        right.priority,
                        right.requested
                    )
                );
                assert_eq!((left.paid, left.unfunded), (right.paid, right.unfunded));
                for row in [left, right] {
                    assert_eq!(
                        row.paid
                            .micro_units()
                            .checked_add(row.unfunded.micro_units()),
                        Some(row.requested.micro_units()),
                        "each allocation conserves its requested amount"
                    );
                }
            }
            let totals = |rows: &[PublicBudgetReceipt]| {
                rows.iter()
                    .try_fold((0_i128, 0_i128), |(paid, unfunded), row| {
                        Some((
                            paid.checked_add(row.paid.micro_units())?,
                            unfunded.checked_add(row.unfunded.micro_units())?,
                        ))
                    })
                    .expect("paired allocation totals fit i128")
            };
            let enabled_totals = totals(enabled);
            let control_totals = totals(&allocations);
            assert_eq!(enabled_totals, control_totals);
            assert_eq!(
                enabled_totals.1, 0,
                "the captured public budget has no unfunded competing claims"
            );
            eprintln!("paired P{tick} non-agency Wayne allocations paid/unfunded micros: PD={enabled_totals:?}, no-PD={control_totals:?}");
        }
    }

    pub(crate) fn qualify_historical_encounters() {
        run_witnessed(HistoricalChecks::Required);
    }

    fn qualify_empty_opening(
        runtime: &DurableMaterialRuntime,
        config: &postgres::Config,
        campaign: CampaignId,
    ) {
        assert!(runtime.tail().is_none());
        let mut writer = config.connect(super::NoTls).expect("writer");
        let marker_count: i64 = writer
            .query_one(
                "SELECT count(*) FROM babylon_state.tick_commit WHERE campaign_id=$1",
                &[campaign.as_uuid()],
            )
            .expect("P0 marker count")
            .get(0);
        assert_eq!(marker_count, 0);
        drop(writer);
        assert_eq!(
            runtime
                .organizer_snapshot()
                .expect("P0 status")
                .city_pd_encounters
                .len(),
            0
        );
    }

    fn run_witnessed(historical_checks: HistoricalChecks) {
        use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
        use babylon_persistence::economic_catalog::CapturedEconomicCatalog;
        use babylon_practice_contract::{CityPdDecision, PublicVenueRecordKind};

        let mut target = DisposableTarget::create();
        let campaign = CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7032));
        let foundation = CapturedEconomicCatalog::capture_national_campaign(
            babylon_persistence::economic_catalog::national_catalog_input(),
            campaign,
        )
        .expect("actual national capture")
        .create_foundation(
            ReplaySessionId::try_from("national-city-pd-pg").expect("session"),
            ReplaySeed::new(319),
        )
        .expect("actual national foundation");
        let digest = foundation.digest();
        let runtime = DurableMaterialRuntime::create(&target.writer, campaign, foundation)
            .expect("persist actual opening");
        assert!(matches!(
            runtime
                .session()
                .material()
                .city_pd()
                .expect("PD")
                .state
                .last_decision
                .as_ref()
                .expect("opening decision")
                .decision,
            CityPdDecision::NoFunds {
                available_micros: 0,
                ..
            }
        ));
        drop(runtime);
        let mut runtime = DurableMaterialRuntime::open(&target.writer, campaign, digest)
            .expect("P0 cold open authenticates the empty opening");
        qualify_empty_opening(&runtime, &target.writer, campaign);
        let reinforce = super::command(&runtime, OrganizerChoice::Reinforce, 42);
        runtime
            .submit_organizer_command(&reinforce)
            .expect("admit contact command");
        support::advance_material_period(&mut runtime);
        let p1 = runtime.session().material().canonical_bytes().to_vec();
        let p1_hash = *runtime
            .tail()
            .expect("P1 marker")
            .tick_content_hash()
            .as_bytes();
        let contact = runtime
            .session()
            .material()
            .public_venue()
            .expect("venue")
            .records
            .iter()
            .find(|record| {
                record.period == 1
                    && matches!(record.kind, PublicVenueRecordKind::ContactCompleted { .. })
            })
            .expect("committed P1 contact")
            .source_id;
        drop(runtime);
        let mut runtime = DurableMaterialRuntime::open(&target.writer, campaign, digest)
            .expect("cold open authenticates P1 contact and original debit");
        assert_eq!(runtime.session().material().canonical_bytes(), p1);
        support::advance_material_period(&mut runtime);
        let snapshot = assert_paid_encounter(&runtime, contact);
        let p2 = runtime.session().material().canonical_bytes().to_vec();
        if matches!(historical_checks, HistoricalChecks::Required) {
            qualify_encounter_tampering(&runtime, &target.writer, campaign, historical_checks);
            qualify_restricted_encounter_page(
                &mut target,
                campaign,
                snapshot.view.workplace_id,
                p1_hash,
                EncounterDisclosure::Visible,
            );
        }
        drop(runtime);
        let mut runtime = DurableMaterialRuntime::open(&target.writer, campaign, digest)
            .expect("cold open authenticates original P2 decision, payment and source");
        assert_eq!(runtime.session().material().canonical_bytes(), p2);
        support::advance_material_period(&mut runtime);
        assert_eq!(runtime.session().completed_tick(), 3);
    }

    pub(crate) fn qualify_paid_nonwitness(target: &mut DisposableTarget) {
        use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
        use babylon_material_circuit::AgencyAttendanceOutcome;
        use babylon_persistence::economic_catalog::{
            self, CapturedEconomicCatalog, SourceArtifact, SourceArtifactKind,
        };
        let campaign = CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7033));
        let mut input = economic_catalog::national_catalog_input();
        let source = input
            .sources
            .iter_mut()
            .find(|source| source.kind() == SourceArtifactKind::NationalGamePolicy)
            .expect("national policy source");
        let original = std::str::from_utf8(source.bytes()).expect("policy text");
        let changed = original.replace(
            "venue_log_reader = \"controlled_organizer\"",
            "venue_log_reader = \"workplace_committee\"",
        );
        assert_ne!(changed, original);
        *source =
            SourceArtifact::capture(SourceArtifactKind::NationalGamePolicy, changed.into_bytes());
        let foundation = CapturedEconomicCatalog::capture_national_campaign(input, campaign)
            .expect("capture alternate Designed reader")
            .create_foundation(
                ReplaySessionId::try_from("national-city-pd-nonwitness").expect("session"),
                ReplaySeed::new(319),
            )
            .expect("alternate foundation");
        let digest = foundation.digest();
        let mut runtime = DurableMaterialRuntime::create(&target.writer, campaign, foundation)
            .expect("persist alternate opening");
        let command = super::command(&runtime, OrganizerChoice::Reinforce, 43);
        runtime
            .submit_organizer_command(&command)
            .expect("admit contact");
        support::advance_material_period(&mut runtime);
        let p1_hash = *runtime
            .tail()
            .expect("P1 marker")
            .tick_content_hash()
            .as_bytes();
        support::advance_material_period(&mut runtime);
        let attempt = &runtime.session().material().city_pd().expect("PD").attempts[0];
        assert_eq!(attempt.funding.outcome, AgencyAttendanceOutcome::Paid);
        assert!(attempt.receipt.player_witness_evidence_id.is_none());
        assert!(runtime
            .session()
            .material()
            .public_venue()
            .expect("venue")
            .records
            .iter()
            .any(|record| matches!(
                record.kind,
                babylon_practice_contract::PublicVenueRecordKind::PaidVisit { .. }
            )));
        let mut writer = target.writer.connect(super::NoTls).expect("writer");
        let grant_count: i64 = writer.query_one("SELECT count(*) FROM babylon_meta.archive_knowledge_grant_v1 WHERE campaign_id=$1 AND grant_key LIKE 'city-pd-%'", &[campaign.as_uuid()]).expect("encounter grants").get(0);
        assert_eq!(grant_count, 0);
        let snapshot = runtime.organizer_snapshot().expect("non-witness status");
        assert_eq!(snapshot.city_pd_encounters.len(), 0);
        let workplace = snapshot.view.workplace_id;
        drop(runtime);
        let reopened = DurableMaterialRuntime::open(&target.writer, campaign, digest)
            .expect("non-witness cold open");
        assert_eq!(
            reopened
                .organizer_snapshot()
                .expect("reopened status")
                .city_pd_encounters
                .len(),
            0
        );
        qualify_restricted_encounter_page(
            target,
            campaign,
            workplace,
            p1_hash,
            EncounterDisclosure::Hidden,
        );
    }
}
