//! Period-specific organizer knowledge, inserted before the material tick marker.

use crate::economic_content::{EconomicAdmissionOwner, EconomicContentHandle};
use crate::identity::CampaignId;
use crate::material_runtime::MaterialRuntimeError;
use crate::organizer_runtime::CityPdEncounter;
use crate::organizer_runtime::OrganizerFoodDelivery;
use crate::{
    ArchiveCitation, ArchiveDirtyBatch, ArchiveDossierProducer, ArchiveKnowledge, ArchivePageInput,
    ArchiveProducerOutcome, ArchiveSignal, ArchiveSubject, ArchiveSubjectKind,
    PendingArchiveReceipt, SemanticArchiveError,
};
use babylon_practice_contract::OrganizerPeriodJournalEntries;
use babylon_practice_contract::{OrganizerAidCashStatus, OrganizerPeriodJournal};

use crate::archive;
use crate::material_runtime::ArchiveFoundationCandidate;
use crate::material_runtime::CapturedArchiveOrganizerRegister;
use crate::production_projection::diagnostics::Stage;
use crate::production_projection::diagnostics::Timing;
use crate::CampaignFoundation;
use babylon_practice_contract::OrganizerCollectionResolution;
use babylon_practice_contract::{
    OrganizerAidMaterialPostings, OrganizerAidResolutionReceipt, OrganizerChoice, OrganizerConfig,
    OrganizerInquiry, OrganizerObservation, OrganizerOutcome, OrganizerPartnerResponse,
    OrganizerReceipt, OrganizerReport,
};
use babylon_tick::material_world::MaterialWorldRegister;
use postgres::Config;
use postgres::IsolationLevel;
use postgres::Row;
use postgres::{GenericClient, NoTls};
use std::collections::BTreeMap;
use std::sync::Mutex;
use uuid::Uuid;

fn hex(bytes: &[u8; 32]) -> String {
    crate::michigan_economy::digest_hex(bytes)
}
fn citation(
    actor: u64,
    observed: u64,
    acquired: u64,
    id: &[u8; 32],
) -> Result<ArchiveCitation, SemanticArchiveError> {
    ArchiveCitation::try_new(
        "committed-organizer-report-v1".into(),
        format!(
            "source-actor/{actor}/observed-period/{observed}/acquired-period/{acquired}/receipt/{}",
            hex(id)
        ),
    )
}
fn observation_citation(
    observation: &OrganizerObservation,
) -> Result<ArchiveCitation, SemanticArchiveError> {
    ArchiveCitation::try_new(
        match &observation.report {
            OrganizerReport::Partner { .. } => "derived-scoped-partner-report-v1",
            _ => "committed-organizer-report-v1",
        }.into(),
        format!(
            "source-actor/{}/observed-period/{}/acquired-period/{}/observation/{}/action-receipt/{}",
            observation.source_actor_id,
            observation.observed_period,
            observation.acquired_period,
            hex(&observation.observation_id),
            observation
                .receipt_id
                .as_ref()
                .map_or_else(|| "automatic-report".into(), hex),
        ),
    )
}

fn archive_error(_: SemanticArchiveError) -> MaterialRuntimeError {
    MaterialRuntimeError::OrganizerStorage
}

fn validate_observation_columns(
    expected: &OrganizerObservation,
    observation_id: &[u8],
    actor_id: &str,
    subject_id: &str,
    periods: (i64, i64),
    bytes: &[u8],
) -> Result<(), MaterialRuntimeError> {
    if observation_id != expected.observation_id
        || actor_id != expected.actor_id.to_string()
        || subject_id != expected.subject_id.to_string()
        || u64::try_from(periods.0).ok() != Some(expected.observed_period)
        || u64::try_from(periods.1).ok() != Some(expected.acquired_period)
        || bytes
            != serde_json::to_vec(expected).map_err(|_| MaterialRuntimeError::OrganizerStorage)?
    {
        return Err(MaterialRuntimeError::OrganizerStorage);
    }
    Ok(())
}

fn validate_observation_row(
    row: &Row,
    expected: &OrganizerObservation,
) -> Result<(), MaterialRuntimeError> {
    validate_observation_columns(
        expected,
        &row.get::<_, Vec<u8>>("observation_id"),
        &row.get::<_, String>("actor_id"),
        &row.get::<_, String>("subject_id"),
        (row.get("observed_period"), row.get("acquired_period")),
        &row.get::<_, Vec<u8>>("observation_bytes"),
    )
}

fn validate_receipt_columns(
    expected: &OrganizerReceipt,
    receipt_id: &[u8],
    actor_id: &str,
    resolve_tick: i64,
    bytes: &[u8],
) -> Result<(), MaterialRuntimeError> {
    if receipt_id != expected.receipt_id
        || actor_id != expected.actor_id.to_string()
        || u64::try_from(resolve_tick).ok() != Some(expected.period)
        || bytes
            != serde_json::to_vec(expected).map_err(|_| MaterialRuntimeError::OrganizerStorage)?
    {
        return Err(MaterialRuntimeError::OrganizerStorage);
    }
    Ok(())
}

fn validate_receipt_row(
    row: &Row,
    expected: &OrganizerReceipt,
) -> Result<(), MaterialRuntimeError> {
    validate_receipt_columns(
        expected,
        &row.get::<_, Vec<u8>>("receipt_id"),
        &row.get::<_, String>("actor_id"),
        row.get("resolve_tick"),
        &row.get::<_, Vec<u8>>("receipt_bytes"),
    )
}

fn report_subject_kind(observation: &OrganizerObservation) -> ArchiveSubjectKind {
    match &observation.report {
        OrganizerReport::Partner { .. } => ArchiveSubjectKind::Organization,
        _ => ArchiveSubjectKind::Workplace,
    }
}

fn report_rows<'a>(
    config: &'a OrganizerConfig,
    journal: &'a OrganizerPeriodJournal,
) -> impl Iterator<Item = &'a OrganizerObservation> {
    config.initial_observations.iter().chain(
        journal
            .periods
            .iter()
            .flat_map(|entries| &entries.observations),
    )
}

pub(crate) fn insert_projection(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    register: &MaterialWorldRegister,
) -> Result<(), MaterialRuntimeError> {
    let Some(config) = register.organizer_config() else {
        return Ok(());
    };
    let state = register
        .organizer_state()
        .ok_or(MaterialRuntimeError::OrganizerStorage)?;
    let journal = register
        .organizer_journal()
        .ok_or(MaterialRuntimeError::OrganizerStorage)?;
    if state.period != 0 {
        validate_subjects(client, campaign, config)?;
    }
    let actor = config.controlled_actor_id.to_string();
    insert_subjects(client, campaign, config)?;
    for observation in report_rows(config, journal) {
        if observation.actor_id != config.controlled_actor_id {
            continue;
        }
        let bytes =
            serde_json::to_vec(observation).map_err(|_| MaterialRuntimeError::OrganizerStorage)?;
        let observed =
            i64::try_from(observation.observed_period).map_err(|_| MaterialRuntimeError::Bounds)?;
        let acquired =
            i64::try_from(observation.acquired_period).map_err(|_| MaterialRuntimeError::Bounds)?;
        let count = client.execute("INSERT INTO babylon_state.organizer_observation_v1 (campaign_id,observation_id,actor_id,subject_id,observed_period,acquired_period,observation_bytes) VALUES ($1,$2,$3,$4,$5,$6,$7) ON CONFLICT DO NOTHING", &[campaign.as_uuid(),&&observation.observation_id[..],&actor,&observation.subject_id.to_string(),&observed,&acquired,&bytes])?;
        if count == 0 {
            let stored = client.query_one("SELECT observation_id,actor_id,subject_id,observed_period,acquired_period,observation_bytes FROM babylon_state.organizer_observation_v1 WHERE campaign_id=$1 AND observation_id=$2", &[campaign.as_uuid(),&&observation.observation_id[..]])?;
            validate_observation_row(&stored, observation)?;
        }
        let citation = observation_citation(observation).map_err(archive_error)?;
        archive::insert_grant_row(
            client,
            campaign,
            report_subject_kind(observation).as_str(),
            &observation.subject_id.to_string(),
            &format!("report-{}", hex(&observation.observation_id)),
            observation.acquired_period,
            &citation,
        )
        .map_err(archive_error)?;
    }
    let organizer_receipts = journal
        .periods
        .iter()
        .flat_map(OrganizerPeriodJournalEntries::receipts);
    for receipt in organizer_receipts {
        if receipt.actor_id != config.controlled_actor_id {
            continue;
        }
        let bytes =
            serde_json::to_vec(receipt).map_err(|_| MaterialRuntimeError::OrganizerStorage)?;
        let tick = i64::try_from(receipt.period).map_err(|_| MaterialRuntimeError::Bounds)?;
        let count = client.execute("INSERT INTO babylon_state.organizer_receipt_v1 (campaign_id,receipt_id,actor_id,resolve_tick,receipt_bytes) VALUES ($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING", &[campaign.as_uuid(),&&receipt.receipt_id[..],&actor,&tick,&bytes])?;
        if count == 0 {
            let stored = client.query_one("SELECT receipt_id,actor_id,resolve_tick,receipt_bytes FROM babylon_state.organizer_receipt_v1 WHERE campaign_id=$1 AND receipt_id=$2", &[campaign.as_uuid(),&&receipt.receipt_id[..]])?;
            validate_receipt_row(&stored, receipt)?;
        }
        let citation = citation(
            receipt.actor_id,
            receipt.period,
            receipt.period,
            &receipt.receipt_id,
        )
        .map_err(archive_error)?;
        archive::insert_grant_row(
            client,
            campaign,
            "organization",
            &actor,
            &format!("practice-{}", hex(&receipt.receipt_id)),
            receipt.period,
            &citation,
        )
        .map_err(archive_error)?;
    }
    insert_encounters(client, campaign, register)?;
    validate_projection(client, campaign, register)
}

fn encounter_key(value: &CityPdEncounter) -> String {
    format!("city-pd-{}", hex(&value.receipt_id))
}

fn encounter_citation(value: &CityPdEncounter) -> Result<ArchiveCitation, SemanticArchiveError> {
    ArchiveCitation::try_new(
        "committed-public-venue-check-in-v1".into(),
        format!(
            "actor/{}/workplace/{}/period/{}/source/{}/receipt/{}",
            value.controlled_actor_id,
            value.subject_id,
            value.resolve_period,
            hex(&value.venue_source_id),
            hex(&value.receipt_id)
        ),
    )
}

fn insert_encounters(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    register: &MaterialWorldRegister,
) -> Result<(), MaterialRuntimeError> {
    for value in crate::organizer_runtime::encounter::projections(register)? {
        let bytes = crate::organizer_runtime::encounter::canonical_bytes(&value)?;
        let actor = value.controlled_actor_id.to_string();
        let subject = value.subject_id.to_string();
        let tick = i64::try_from(value.resolve_period).map_err(|_| MaterialRuntimeError::Bounds)?;
        let count = client.execute("INSERT INTO babylon_state.organizer_encounter_v1 (campaign_id,receipt_id,actor_id,subject_id,resolve_tick,encounter_bytes) VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT DO NOTHING", &[campaign.as_uuid(), &&value.receipt_id[..], &actor, &subject, &tick, &bytes])?;
        if count == 0 {
            let row = client.query_one("SELECT receipt_id,actor_id,subject_id,resolve_tick,encounter_bytes FROM babylon_state.organizer_encounter_v1 WHERE campaign_id=$1 AND receipt_id=$2", &[campaign.as_uuid(), &&value.receipt_id[..]])?;
            validate_encounter_row(&row, &value)?;
        }
        archive::insert_grant_row(
            client,
            campaign,
            "workplace",
            &subject,
            &encounter_key(&value),
            value.resolve_period,
            &encounter_citation(&value).map_err(archive_error)?,
        )
        .map_err(archive_error)?;
    }
    Ok(())
}

fn validate_encounter_row(row: &Row, value: &CityPdEncounter) -> Result<(), MaterialRuntimeError> {
    if row.get::<_, Vec<u8>>("receipt_id") != value.receipt_id
        || row.get::<_, String>("actor_id") != value.controlled_actor_id.to_string()
        || row.get::<_, String>("subject_id") != value.subject_id.to_string()
        || u64::try_from(row.get::<_, i64>("resolve_tick")).ok() != Some(value.resolve_period)
        || row.get::<_, Vec<u8>>("encounter_bytes")
            != crate::organizer_runtime::encounter::canonical_bytes(value)?
    {
        return Err(MaterialRuntimeError::OrganizerStorage);
    }
    Ok(())
}

fn validate_encounter_grant(
    row: &Row,
    value: &CityPdEncounter,
) -> Result<(), MaterialRuntimeError> {
    let citation = encounter_citation(value).map_err(archive_error)?;
    if row.get::<_, String>("subject_kind") != "workplace"
        || row.get::<_, String>("subject_id") != value.subject_id.to_string()
        || row.get::<_, String>("grant_key") != encounter_key(value)
        || u64::try_from(row.get::<_, i64>("granted_tick")).ok() != Some(value.resolve_period)
        || row.get::<_, String>("provenance_source_id") != citation.source_id()
        || row.get::<_, String>("provenance_locator") != citation.locator()
    {
        return Err(MaterialRuntimeError::OrganizerStorage);
    }
    Ok(())
}

fn encounter_signal(value: &CityPdEncounter) -> Result<ArchiveSignal, SemanticArchiveError> {
    ArchiveSignal::try_new(
        encounter_key(value),
        format!("Public venue check-in in period {}", value.resolve_period),
        format!("The venue's published check-in records a City PD visit by organization {} at this workplace. This log does not establish personal attendance by the organizer.", value.visitor_actor_id),
        encounter_citation(value)?,
    )
}

fn subject_definitions(config: &OrganizerConfig) -> Vec<(ArchiveSubjectKind, u64, &str)> {
    let mut subjects: Vec<(ArchiveSubjectKind, u64, &str)> = vec![
        (
            ArchiveSubjectKind::Workplace,
            config.workplace_id,
            &config.workplace_label,
        ),
        (
            ArchiveSubjectKind::Organization,
            config.controlled_actor_id,
            &config.organization_label,
        ),
        (
            ArchiveSubjectKind::Organization,
            config.workplace_partner.actor_id,
            &config.workplace_partner.label,
        ),
        (
            ArchiveSubjectKind::Organization,
            config.neighborhood_partner.actor_id,
            &config.neighborhood_partner.label,
        ),
    ];
    subjects.extend(config.aid_bindings.iter().map(|b| {
        (
            ArchiveSubjectKind::Organization,
            b.partner.actor_id,
            b.partner.label.as_str(),
        )
    }));
    subjects
}

fn validate_subjects(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    config: &OrganizerConfig,
) -> Result<(), MaterialRuntimeError> {
    let rows = capture_subjects(client, campaign)?;
    validate_captured_subjects(&rows, config)
}

fn capture_subjects(
    client: &mut impl GenericClient,
    campaign: CampaignId,
) -> Result<Vec<Row>, MaterialRuntimeError> {
    Ok(client.query("SELECT actor_id,subject_kind,subject_id,title FROM babylon_state.organizer_subject_v1 WHERE campaign_id=$1", &[campaign.as_uuid()])?)
}

fn validate_captured_subjects(
    rows: &[Row],
    config: &OrganizerConfig,
) -> Result<(), MaterialRuntimeError> {
    let expected = subject_definitions(config);
    let actor = config.controlled_actor_id.to_string();
    if rows.len() != expected.len()
        || rows.iter().any(|row| {
            row.get::<_, String>("actor_id") != actor
                || !expected.iter().any(|(kind, id, label)| {
                    row.get::<_, String>("subject_kind") == kind.as_str()
                        && row.get::<_, String>("subject_id") == id.to_string()
                        && row.get::<_, String>("title") == *label
                })
        })
    {
        return Err(MaterialRuntimeError::OrganizerStorage);
    }
    Ok(())
}

fn insert_subjects(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    config: &OrganizerConfig,
) -> Result<(), MaterialRuntimeError> {
    let actor = config.controlled_actor_id.to_string();
    let initial_citation = ArchiveCitation::try_new(
        "designed-wayne-organizer-v1".into(),
        format!(
            "campaign/{}/content/{}",
            campaign.as_uuid(),
            hex(&config.content_digest)
        ),
    )
    .map_err(archive_error)?;
    for (kind, id, label) in subject_definitions(config) {
        client.execute("INSERT INTO babylon_state.organizer_subject_v1 (campaign_id,actor_id,subject_kind,subject_id,title) VALUES ($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING", &[campaign.as_uuid(),&actor,&kind.as_str(),&id.to_string(),&label])?;
        archive::insert_grant_row(
            client,
            campaign,
            kind.as_str(),
            &id.to_string(),
            "subject",
            0,
            &initial_citation,
        )
        .map_err(archive_error)?;
    }
    Ok(())
}

fn report_text(observation: &OrganizerObservation) -> String {
    let detail = match &observation.report {
        OrganizerReport::Partner { facts, .. } => facts.detail(),
        OrganizerReport::ReducedWork {
            previous_labor_hours,
            performed_labor_hours,
        } => format!(
            "Performed modeled work decreased from {previous_labor_hours} to {performed_labor_hours} labor-hours. Actual shift schedules and wages are not modeled."
        ),
        OrganizerReport::Work {
            performed_labor_hours,
            output_kg,
            previous_labor_hours,
            previous_output_kg,
        } => format!(
            "{performed_labor_hours} performed labor-hours; {output_kg} kg output. Previous report: {} labor-hours, {} kg.",
            previous_labor_hours.map_or_else(|| "unknown".into(), |value| value.to_string()),
            previous_output_kg.map_or_else(|| "unknown".into(), |value| value.to_string())
        ),
        OrganizerReport::Maintenance {
            enabled_batches,
            consumed_batches,
            expired_batches,
        } => format!(
            "Workplace maintenance availability: {enabled_batches} enabled batches; {consumed_batches} consumed; {expired_batches} expired. Provider-private accounts remain withheld."
        ),
    };
    format!(
        "Observed period {}; acquired period {}. {detail}",
        observation.observed_period, observation.acquired_period
    )
}
fn receipt_text(receipt: &OrganizerReceipt) -> String {
    let practice = match receipt.choice {
        OrganizerChoice::Collect => "Collect a voluntary contribution",
        OrganizerChoice::LocalAid => "Local aid",
        OrganizerChoice::RemoteAid => "Cross-region support",
        OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost) => "Ask about work and output",
        OrganizerChoice::Inquiry(OrganizerInquiry::MaintenanceReceived) => "Ask about maintenance",
        OrganizerChoice::Reinforce => "Reinforce workplace contact",
        OrganizerChoice::Hold => "Keep current routine",
        OrganizerChoice::PauseStanding => "Pause neighborhood work",
        OrganizerChoice::ResumeStanding => "Resume neighborhood work",
    };
    let outcome = match receipt.outcome {
        OrganizerOutcome::CollectionCompleted => {
            "Voluntary contribution collected; funds available for later aid"
        }
        OrganizerOutcome::CollectionRefused => "Collection refused; no standing fallback",
        OrganizerOutcome::AidScheduled => "Support committed for material resolution",
        OrganizerOutcome::AidAwaitingSupport => "Support remains in transit",
        OrganizerOutcome::NoQualifyingSupport => "Support did not qualify joint work",
        OrganizerOutcome::AidPracticeCompleted => "Independent aid practice completed",
        OrganizerOutcome::AidPracticeUncompleted => "Independent aid practice uncompleted",
        OrganizerOutcome::EvidenceObtained => "Evidence obtained",
        OrganizerOutcome::EvidenceWithheld => "No report obtained",
        OrganizerOutcome::ContactCompleted => "Mutual contact completed",
        OrganizerOutcome::ContactUncompleted => "Contact attempt uncompleted",
        OrganizerOutcome::InsufficientTime => "Insufficient committed time",
        OrganizerOutcome::StandingPaused => "Standing work paused",
        OrganizerOutcome::StandingResumed => "Standing work resumed",
        OrganizerOutcome::AidResponseRetained => "Earlier coordination response retained",
        OrganizerOutcome::NoAuthorizedPractice => "No authorized practice",
    };
    let response = match receipt.partner_response {
        OrganizerPartnerResponse::Participated => "participated",
        OrganizerPartnerResponse::Refused => "refused",
        OrganizerPartnerResponse::NoResponse => "no response",
        OrganizerPartnerResponse::UnableToParticipate => "unable to participate",
        OrganizerPartnerResponse::NotRequested => "participation not requested",
    };
    let source = if receipt.commitment_id.is_some() {
        if receipt.standing_work {
            "specific ruling · saved routine"
        } else {
            "specific ruling"
        }
    } else {
        "saved routine"
    };
    format!(
        "Period {}: {practice}\nSource: {source}\nResult: {outcome}\nTime spent: {} organizer-hours\nIndependent partner: {response}\nFactory recovery is a separate material result.",
        receipt.period, receipt.hours_spent
    )
}

/// Existing Archive-worker producer for committed, period-specific organizer evidence.
pub struct OrganizerDossierProducer {
    config: Config,
    foundation: EconomicAdmissionOwner,
    cold_foundation: Mutex<Option<(CampaignId, CampaignFoundation)>>,
}
impl OrganizerDossierProducer {
    /// Bind the writer connection used by the existing Archive worker.
    #[must_use]
    pub fn new(config: &Config) -> Self {
        Self {
            config: config.clone(),
            foundation: EconomicAdmissionOwner::default(),
            cold_foundation: Mutex::new(None),
        }
    }

    pub(crate) fn from_captured(
        config: &Config,
        campaign: CampaignId,
        foundation: CampaignFoundation,
    ) -> Self {
        Self {
            config: config.clone(),
            foundation: EconomicAdmissionOwner::default(),
            cold_foundation: Mutex::new(Some((campaign, foundation))),
        }
    }
}

pub(crate) fn archive_register_error(error: MaterialRuntimeError) -> SemanticArchiveError {
    match error {
        MaterialRuntimeError::Database(error)
        | MaterialRuntimeError::DatabaseLockRefused(error)
        | MaterialRuntimeError::DatabaseStatementCanceled(error) => {
            archive::database("read organizer Archive register", &error)
        }
        MaterialRuntimeError::Graph(
            crate::RustPersistenceRuntimeError::Database {
                operation,
                diagnostic: Some(diagnostic),
            }
            | crate::RustPersistenceRuntimeError::TerritoryCountyMap(
                crate::territory_county_map::TerritoryCountyMapError::Database {
                    operation,
                    diagnostic: Some(diagnostic),
                },
            ),
        ) => SemanticArchiveError::Database {
            operation,
            diagnostic,
        },
        _ => SemanticArchiveError::StoredPageMismatch,
    }
}

impl ArchiveDossierProducer for OrganizerDossierProducer {
    fn produce(
        &self,
        campaign: Uuid,
        receipt: &PendingArchiveReceipt,
        _knowledge: &ArchiveKnowledge,
        page_budget: usize,
    ) -> Result<ArchiveProducerOutcome, SemanticArchiveError> {
        let mut config = self.config.clone();
        let options = format!(
            "{} -c idle_in_transaction_session_timeout=5000ms",
            config.get_options().unwrap_or("")
        );
        config.options(&options);
        let mut client = config
            .connect(NoTls)
            .map_err(|e| archive::database("connect organizer Archive producer", &e))?;
        let mut transaction = client
            .build_transaction()
            .isolation_level(IsolationLevel::RepeatableRead)
            .read_only(true)
            .start()
            .map_err(|e| archive::database("begin organizer Archive read", &e))?;
        let captured = capture_organizer_pages(&mut transaction, campaign, receipt, page_budget)?;
        transaction
            .commit()
            .map_err(|e| archive::database("finish organizer Archive capture", &e))?;
        drop(client);
        let campaign = CampaignId::from_uuid(campaign);
        let candidate = self
            .foundation
            .candidate(campaign)
            .map_err(|_| SemanticArchiveError::StoredPageMismatch)?
            .map(ArchiveFoundationCandidate::Admitted);
        let candidate = if candidate.is_some() || captured.register.is_none() {
            candidate
        } else {
            let mut cold = self
                .cold_foundation
                .lock()
                .map_err(|_| SemanticArchiveError::StoredPageMismatch)?;
            if cold.as_ref().is_some_and(|(bound, _)| *bound != campaign) {
                return Err(SemanticArchiveError::StoredPageMismatch);
            }
            cold.take()
                .map(|(_, graph)| ArchiveFoundationCandidate::Graph(Box::new(graph)))
        };
        let (outcome, admitted) = captured.admit_and_render(candidate)?;
        if let Some(admitted) = admitted {
            self.foundation
                .publish(campaign, admitted)
                .map_err(|_| SemanticArchiveError::StoredPageMismatch)?;
        }
        Ok(outcome)
    }
}

/// Owns only exact snapshot rows; detached admission and rendering cannot query SQL.
pub(crate) struct CapturedOrganizerPages {
    tick: u64,
    content_hash: [u8; 32],
    page_budget: usize,
    subjects: Vec<Row>,
    register: Option<CapturedArchiveOrganizerRegister>,
}

pub(crate) fn capture_organizer_pages(
    client: &mut impl GenericClient,
    campaign: Uuid,
    receipt: &PendingArchiveReceipt,
    page_budget: usize,
) -> Result<CapturedOrganizerPages, SemanticArchiveError> {
    let tick = i64::try_from(receipt.resolve_tick())
        .map_err(|_| SemanticArchiveError::InvalidVerifiedTick)?;
    let subjects = client.query("SELECT s.actor_id,s.subject_kind,s.subject_id,s.title FROM babylon_state.organizer_subject_v1 s WHERE campaign_id=$1 AND NOT EXISTS(SELECT 1 FROM babylon_meta.archive_page_revision_v2 p WHERE p.campaign_id=s.campaign_id AND p.subject_kind=s.subject_kind AND p.subject_id=s.subject_id AND p.effective_tick=$2) ORDER BY subject_kind,subject_id", &[&campaign,&tick]).map_err(|e|archive::database("read organizer report subjects",&e))?;
    let register = if subjects.is_empty() || page_budget == 0 {
        None
    } else {
        Some(
            crate::material_runtime::capture_archive_organizer_register(
                client,
                CampaignId::from_uuid(campaign),
                receipt,
            )
            .map_err(archive_register_error)?
            .ok_or(SemanticArchiveError::StoredPageMismatch)?,
        )
    };
    Ok(CapturedOrganizerPages {
        tick: receipt.resolve_tick(),
        content_hash: *receipt.tick_content_hash(),
        page_budget,
        subjects,
        register,
    })
}

impl CapturedOrganizerPages {
    #[allow(
        clippy::too_many_lines,
        reason = "one ordered render joins every retained organizer evidence family into its page batch"
    )]
    pub(crate) fn admit_and_render(
        self,
        cached: Option<ArchiveFoundationCandidate>,
    ) -> Result<(ArchiveProducerOutcome, Option<EconomicContentHandle>), SemanticArchiveError> {
        let receipt = PendingArchiveReceipt::try_new(self.tick, self.content_hash)?;
        let page_budget = self.page_budget;
        let Some(captured) = self.register else {
            return Ok((
                ArchiveProducerOutcome::new(
                    ArchiveDirtyBatch::try_new(
                        receipt.resolve_tick(),
                        *receipt.tick_content_hash(),
                        Vec::new(),
                    )?,
                    self.subjects.len(),
                ),
                None,
            ));
        };
        let (register, admitted) = captured.admit(cached).map_err(archive_register_error)?;
        let _render_timing = Timing::start(Stage::ArchiveOrganizerRendering, self.tick);
        let subjects = self.subjects;
        if register.organizer_state().is_none() {
            return Ok((
                ArchiveProducerOutcome::new(
                    ArchiveDirtyBatch::try_new(
                        receipt.resolve_tick(),
                        *receipt.tick_content_hash(),
                        Vec::new(),
                    )?,
                    0,
                ),
                Some(admitted),
            ));
        }
        let total = subjects.len();
        let mut pages = Vec::new();
        let journal = register
            .organizer_journal()
            .ok_or(SemanticArchiveError::StoredPageMismatch)?;
        let config = register
            .organizer_config()
            .ok_or(SemanticArchiveError::StoredPageMismatch)?;
        let mut observations = report_rows(config, journal).collect::<Vec<_>>();
        observations.sort_by_key(|row| (row.acquired_period, row.observation_id));
        let mut receipts = journal
            .periods
            .iter()
            .flat_map(OrganizerPeriodJournalEntries::receipts)
            .collect::<Vec<_>>();
        receipts.sort_by_key(|row| (row.period, row.receipt_id));
        let aid_by_receipt: BTreeMap<_, _> = journal
            .periods
            .iter()
            .flat_map(|entries| entries.aid_receipts.iter())
            .map(|row| (row.practice.receipt_id, row))
            .collect();
        let collection_by_receipt: BTreeMap<_, _> = journal
            .periods
            .iter()
            .flat_map(|entries| entries.collection_receipts.iter())
            .map(|row| (row.practice.receipt_id, row))
            .collect();
        let encounters = crate::organizer_runtime::encounter::projections(&register)
            .map_err(archive_register_error)?;
        for row in subjects.into_iter().take(page_budget) {
            let actor: String = row.get(0);
            let kind: String = row.get(1);
            let id: String = row.get(2);
            let title: String = row.get(3);
            let mut signals = Vec::new();
            for observation in observations.iter().copied().filter(|observation| {
                observation.actor_id.to_string() == actor
                    && report_subject_kind(observation).as_str() == kind
                    && observation.acquired_period <= self.tick
                    && observation.subject_id.to_string() == id
            }) {
                signals.push(PageEvidence::Report(observation));
            }
            if kind == "workplace" {
                for encounter in encounters.iter().filter(|value| {
                    value.controlled_actor_id.to_string() == actor
                        && value.subject_id.to_string() == id
                        && value.resolve_period <= self.tick
                }) {
                    signals.push(PageEvidence::Encounter(encounter));
                }
            } else {
                let matching_receipts = receipts
                    .iter()
                    .copied()
                    .filter(|value| value.actor_id.to_string() == actor && actor == id);
                for value in matching_receipts {
                    if let Some(collection) = collection_by_receipt.get(&value.receipt_id) {
                        signals.push(PageEvidence::Collection(collection));
                        continue;
                    }
                    let aid = aid_by_receipt.get(&value.receipt_id);
                    signals.push(match aid {
                        Some(row) => PageEvidence::Aid(row),
                        None => PageEvidence::Practice(value),
                    });
                }
            }
            let kind = crate::archive::decode_subject_kind(&kind)?;
            pages.push(organizer_page(
                ArchiveSubject::try_new(kind, id, title)?,
                &receipt,
                signals,
            )?);
        }
        let remaining = total.saturating_sub(pages.len());
        Ok((
            ArchiveProducerOutcome::new(
                ArchiveDirtyBatch::try_new(
                    receipt.resolve_tick(),
                    *receipt.tick_content_hash(),
                    pages,
                )?,
                remaining,
            ),
            Some(admitted),
        ))
    }
}

enum PageEvidence<'a> {
    Report(&'a OrganizerObservation),
    Encounter(&'a CityPdEncounter),
    Practice(&'a OrganizerReceipt),
    Collection(&'a OrganizerCollectionResolution),
    Aid(&'a OrganizerAidResolutionReceipt),
}

impl PageEvidence<'_> {
    fn period(&self) -> u64 {
        match self {
            Self::Report(r) => r.acquired_period,
            Self::Encounter(r) => r.resolve_period,
            Self::Practice(r) => r.period,
            Self::Collection(r) => r.practice.period,
            Self::Aid(r) => r.practice.period,
        }
    }
    fn signal(&self) -> Result<ArchiveSignal, SemanticArchiveError> {
        match self {
            Self::Report(r) => observation_signal(r),
            Self::Encounter(r) => encounter_signal(r),
            Self::Practice(r) => practice_signal(r),
            Self::Collection(r) => collection_signal(r),
            Self::Aid(r) => aid_signal(r),
        }
    }
}

fn organizer_page(
    subject: ArchiveSubject,
    receipt: &PendingArchiveReceipt,
    mut evidence: Vec<PageEvidence<'_>>,
) -> Result<ArchivePageInput, SemanticArchiveError> {
    evidence.retain(|e| e.period() <= receipt.resolve_tick());
    // Each earlier receipt keeps its own revision. Select this receipt's newest
    // eligible facts before building text, retaining canonical order within ties.
    let skip = evidence.len().saturating_sub(archive::MAX_SIGNALS);
    if skip > 0 {
        evidence.sort_by_key(PageEvidence::period);
    }
    let signals = evidence
        .iter()
        .skip(skip)
        .map(PageEvidence::signal)
        .collect::<Result<Vec<_>, _>>()?;
    ArchivePageInput::try_new(subject,receipt.resolve_tick(),*receipt.tick_content_hash(),"Designed Wayne scenario: these fictional organizations and modeled workplace do not represent observed organizations or the whole workforce. What have we learned or performed, and which commitment should we review next?".into(),signals,Vec::new())
}

fn observation_signal(
    observation: &OrganizerObservation,
) -> Result<ArchiveSignal, SemanticArchiveError> {
    ArchiveSignal::try_new(
        format!("report-{}", hex(&observation.observation_id)),
        format!(
            "{} from period {}",
            match &observation.report {
                OrganizerReport::Partner { facts, .. } => facts.title(),
                _ => "Workplace evidence",
            },
            observation.observed_period
        ),
        report_text(observation),
        observation_citation(observation)?,
    )
}

fn practice_signal(receipt: &OrganizerReceipt) -> Result<ArchiveSignal, SemanticArchiveError> {
    ArchiveSignal::try_new(
        format!("practice-{}", hex(&receipt.receipt_id)),
        format!("Practice in period {}", receipt.period),
        receipt_text(receipt),
        citation(
            receipt.actor_id,
            receipt.period,
            receipt.period,
            &receipt.receipt_id,
        )?,
    )
}

// Only public support facts are selected from the authenticated full row.
// Policy, authority digests, household IDs and private account balances stay absent.
struct AidSupportEvidence<'a> {
    admission: u64,
    dispatch: u64,
    resolution: u64,
    original_commitment: &'a [u8; 32],
    material_commitment: &'a [u8; 32],
    good: &'a [u8; 32],
    unit: &'a [u8; 32],
    status: OrganizerFoodDelivery,
    cash_status: OrganizerAidCashStatus,
    material_postings: &'a OrganizerAidMaterialPostings,
}

fn aid_support_text(evidence: &AidSupportEvidence<'_>) -> String {
    let support = match evidence.status {
        OrganizerFoodDelivery::NotRequested => "No food selected; cash is adjudicated independently.".into(),
        OrganizerFoodDelivery::AwaitingDelivery =>
            "Pending: surviving freight remains in transit.".into(),
        OrganizerFoodDelivery::ReceivingRefused => "Food receiving was refused; cash settles independently.".into(),
        OrganizerFoodDelivery::TerminalFailure =>
            "Terminal food failure: no food was granted in this period; no surviving food delivery remains.".into(),
        OrganizerFoodDelivery::Granted { granted_quantity } => format!(
            "Granted quantity: {granted_quantity}. The partner decides independently whether to participate."
        ),
    };
    format!(
        "Original human admission period: {}\nMaterial dispatch period: {}\nActual support resolution period: {}\nOriginal commitment: {}\nMaterial commitment: {}\nGood: {}; unit: {}\n{support}\nActual material postings in period {}: Dispatched food: {} units; donor household fulfillment: {} hours. Aid payer cash: gift paid {} micro-units; fulfillment is separate from independent coordination. Cash outcome: {} at original dispatch. Freight loss: {} units in this period.\nDesigned eligibility requires positive cash settled at original dispatch or a food grant with positive bounded same-period consumption credit. It does not prove donated units caused additional consumption or released time; receiving support does not authorize agreement or participation.",
        evidence.admission,
        evidence.dispatch,
        evidence.resolution,
        hex(evidence.original_commitment),
        hex(evidence.material_commitment),
        hex(evidence.good),
        hex(evidence.unit),
        evidence.resolution,
        evidence.material_postings.dispatched_quantity,
        evidence.material_postings.fulfillment_hours,
        evidence.material_postings.payer_cash_granted_micros,
        evidence.cash_status.label(),
        evidence.material_postings.lost_quantity
    )
}

fn aid_signal(row: &OrganizerAidResolutionReceipt) -> Result<ArchiveSignal, SemanticArchiveError> {
    let evidence = AidSupportEvidence {
        admission: row.authorization.gift.commitment.command.expected_period,
        dispatch: row.authorization.dispatch_period,
        resolution: row.support.period,
        original_commitment: &row.authorization.gift.commitment.commitment_id,
        material_commitment: &row.support.material_commitment_id,
        good: &row.support.good_id,
        unit: &row.support.unit_id,
        status: row.support.status.into(),
        cash_status: row.support.cash_status,
        material_postings: &row.support.material_postings,
    };
    // Keep the existing actor-scoped grant and receipt citation. The producer
    // obtained this full row from the authenticated period register, not SQL text.
    let request = match row.authorization.gift.commitment.command.allocation {
        babylon_practice_contract::OrganizerAllocation::Aid {
            food_quantity,
            cash_micros,
        } => format!(" Original request {food_quantity} food units and {cash_micros} cash micros."),
        _ => return Err(SemanticArchiveError::StoredPageMismatch),
    };
    ArchiveSignal::try_new(
        format!("practice-{}", hex(&row.practice.receipt_id)),
        format!(
            "Aid support and independent practice in period {}",
            row.practice.period
        ),
        format!(
            "{}\n{}{request}",
            receipt_text(&row.practice),
            aid_support_text(&evidence)
        ),
        citation(
            row.practice.actor_id,
            row.practice.period,
            row.practice.period,
            &row.practice.receipt_id,
        )?,
    )
}

/// The derived SQL projection must equal the actor-safe portion of the sealed
/// register before a runtime restart or ambiguous commit can acknowledge it.
pub(crate) fn validate_projection(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    register: &MaterialWorldRegister,
) -> Result<(), MaterialRuntimeError> {
    if register.organizer_config().is_none() {
        return Ok(());
    }
    let state = register
        .organizer_state()
        .ok_or(MaterialRuntimeError::OrganizerStorage)?;
    capture_projection(client, campaign, state.period)?.validate(register)
}

/// Exact mutable organizer projection rows, owned by the short capture snapshot.
pub(crate) struct CapturedOrganizerProjection {
    subjects: Vec<Row>,
    observations: Vec<Row>,
    receipts: Vec<Row>,
    encounters: Vec<Row>,
    encounter_grants: Vec<Row>,
    report_grants: Vec<Row>,
}

pub(crate) fn capture_projection(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: u64,
) -> Result<CapturedOrganizerProjection, MaterialRuntimeError> {
    let tick = i64::try_from(tick).map_err(|_| MaterialRuntimeError::Bounds)?;
    let subjects = capture_subjects(client, campaign)?;
    let observations = client.query("SELECT observation_id,actor_id,subject_id,observed_period,acquired_period,observation_bytes FROM babylon_state.organizer_observation_v1 WHERE campaign_id=$1 AND acquired_period<=$2 ORDER BY observation_id", &[campaign.as_uuid(),&tick])?;
    let receipts = client.query("SELECT receipt_id,actor_id,resolve_tick,receipt_bytes FROM babylon_state.organizer_receipt_v1 WHERE campaign_id=$1 AND resolve_tick<=$2 ORDER BY receipt_id", &[campaign.as_uuid(),&tick])?;
    let bound = i64::try_from(babylon_practice_contract::CITY_PD_MAX_ROWS + 1)
        .map_err(|_| MaterialRuntimeError::Bounds)?;
    let encounters = client.query("SELECT receipt_id,actor_id,subject_id,resolve_tick,encounter_bytes FROM babylon_state.organizer_encounter_v1 WHERE campaign_id=$1 AND resolve_tick<=$2 ORDER BY receipt_id LIMIT $3", &[campaign.as_uuid(), &tick, &bound])?;
    let encounter_grants = client.query("SELECT subject_kind,subject_id,grant_key,granted_tick,provenance_source_id,provenance_locator FROM babylon_meta.archive_knowledge_grant_witness_v1 WHERE campaign_id=$1 AND grant_key LIKE 'city-pd-%' AND granted_tick<=$2 ORDER BY grant_key LIMIT $3", &[campaign.as_uuid(), &tick, &bound])?;
    let report_grants = client.query("SELECT subject_kind,subject_id,grant_key,granted_tick,provenance_source_id,provenance_locator FROM babylon_meta.archive_knowledge_grant_witness_v1 WHERE campaign_id=$1 AND grant_key LIKE 'report-%' AND granted_tick<=$2 ORDER BY grant_key", &[campaign.as_uuid(),&tick])?;
    Ok(CapturedOrganizerProjection {
        subjects,
        observations,
        receipts,
        encounters,
        encounter_grants,
        report_grants,
    })
}

impl CapturedOrganizerProjection {
    pub(crate) fn validate(
        &self,
        register: &MaterialWorldRegister,
    ) -> Result<(), MaterialRuntimeError> {
        let Some(config) = register.organizer_config() else {
            return Ok(());
        };
        let journal = register
            .organizer_journal()
            .ok_or(MaterialRuntimeError::OrganizerStorage)?;
        validate_captured_subjects(&self.subjects, config)?;
        let observed = &self.observations;
        let mut expected = report_rows(config, journal)
            .filter(|row| row.actor_id == config.controlled_actor_id)
            .collect::<Vec<_>>();
        expected.sort_by_key(|row| row.observation_id);
        if observed.len() != expected.len() || self.report_grants.len() != expected.len() {
            return Err(MaterialRuntimeError::OrganizerStorage);
        }
        for (row, observation) in self.report_grants.iter().zip(&expected) {
            let citation = observation_citation(observation).map_err(archive_error)?;
            if row.get::<_, String>("subject_kind") != report_subject_kind(observation).as_str()
                || row.get::<_, String>("subject_id") != observation.subject_id.to_string()
                || row.get::<_, String>("grant_key")
                    != format!("report-{}", hex(&observation.observation_id))
                || u64::try_from(row.get::<_, i64>("granted_tick")).ok()
                    != Some(observation.acquired_period)
                || row.get::<_, String>("provenance_source_id") != citation.source_id()
                || row.get::<_, String>("provenance_locator") != citation.locator()
            {
                return Err(MaterialRuntimeError::OrganizerStorage);
            }
        }
        for (row, expected) in observed.iter().zip(expected) {
            validate_observation_row(row, expected)?;
        }
        let receipts = &self.receipts;
        let mut expected = journal
            .periods
            .iter()
            .flat_map(OrganizerPeriodJournalEntries::receipts)
            .filter(|row| row.actor_id == config.controlled_actor_id)
            .collect::<Vec<_>>();
        expected.sort_by_key(|row| row.receipt_id);
        if receipts.len() != expected.len() {
            return Err(MaterialRuntimeError::OrganizerStorage);
        }
        for (row, expected) in receipts.iter().zip(expected) {
            validate_receipt_row(row, expected)?;
        }
        let mut expected = crate::organizer_runtime::encounter::projections(register)?;
        expected.sort_by_key(|value| value.receipt_id);
        if self.encounters.len() != expected.len() || self.encounter_grants.len() != expected.len()
        {
            return Err(MaterialRuntimeError::OrganizerStorage);
        }
        for (row, value) in self.encounters.iter().zip(&expected) {
            validate_encounter_row(row, value)?;
        }
        for (row, value) in self.encounter_grants.iter().zip(&expected) {
            validate_encounter_grant(row, value)?;
        }
        Ok(())
    }
}

fn collection_signal(
    row: &OrganizerCollectionResolution,
) -> Result<ArchiveSignal, SemanticArchiveError> {
    let receipt = &row.practice;
    let text = format!(
        "{}\nOriginal collection admission {}; actual resolution {}. Requested {} cash micros; collected {}; performed {} shared material hours. Collection result: {:?}. This original ruling replaces standing work once; refusal has no standing fallback. A successful gift funds later aid; no membership, agreement or additional time is credited.",
        receipt_text(receipt),
        row.fact.admitted_period,
        row.fact.period,
        row.fact.requested_cash_micros,
        row.fact.collected_cash_micros,
        row.fact.performed_hours,
        row.fact.outcome
    );
    ArchiveSignal::try_new(
        format!("practice-{}", hex(&receipt.receipt_id)),
        format!("Collection in period {}", receipt.period),
        text,
        citation(
            receipt.actor_id,
            receipt.period,
            receipt.period,
            &receipt.receipt_id,
        )?,
    )
}

#[cfg(test)]
mod projection_tests {
    use super::*;
    use crate::{ArchiveKnowledgeGrant, FogSafeArchiveRenderer};

    fn observation() -> OrganizerObservation {
        OrganizerObservation {
            observation_id: [1; 32],
            actor_id: 101,
            subject_id: 104,
            source_actor_id: 102,
            observed_period: 2,
            acquired_period: 3,
            receipt_id: Some([2; 32]),
            report: OrganizerReport::Work {
                performed_labor_hours: 0,
                output_kg: 0,
                previous_labor_hours: Some(960),
                previous_output_kg: Some(960),
            },
        }
    }

    #[test]
    fn scoped_archive_bounds_partner_revisions_and_retains_earlier_acquisition() {
        use crate::runtime_session::OrganizerSnapshot;
        let captured: OrganizerSnapshot = serde_json::from_str(include_str!(
            "../tests/fixtures/national_organizer_pending_v18.json"
        ))
        .expect("real national topics");
        let partner = &captured.view.aid_partners[0];
        let observations: Vec<_> = captured
            .view
            .observations
            .iter()
            .filter(|r| r.subject_id == partner.actor_id)
            .collect();
        let seed = observations
            .iter()
            .find(|r| r.acquired_period == 0)
            .expect("opening");
        let mut rows = vec![(**seed).clone()];
        for period in 1..=86 {
            for (i, report) in observations
                .iter()
                .filter(|r| r.acquired_period == 1)
                .enumerate()
            {
                let mut row = (**report).clone();
                row.observed_period = period;
                row.acquired_period = period;
                row.observation_id[..8].copy_from_slice(&period.to_be_bytes());
                row.observation_id[8] = u8::try_from(i).expect("bounded topics");
                rows.push(row);
            }
        }
        assert_eq!(rows.len(), 259);
        let revision = |period| {
            let subject = ArchiveSubject::try_new(
                ArchiveSubjectKind::Organization,
                partner.actor_id.to_string(),
                partner.label.clone(),
            )
            .expect("known partner");
            let receipt =
                PendingArchiveReceipt::try_new(period, [1; 32]).expect("committed boundary");
            organizer_page(
                subject,
                &receipt,
                rows.iter().map(PageEvidence::Report).collect(),
            )
            .expect("bounded partner publication")
        };
        let earlier = revision(85);
        let later = revision(86);
        assert_eq!((earlier.signals().len(), later.signals().len()), (256, 256));
        let early_id = observation_signal(&rows[1]).expect("early signal");
        let future_id = observation_signal(rows.last().expect("future row")).expect("later signal");
        assert!(earlier.signals().contains(&early_id));
        assert!(!earlier.signals().contains(&future_id));
        assert!(!later.signals().contains(&early_id));
        assert!(later.signals().contains(&future_id));
        let page = earlier.subject().page_ref();
        let grant = |key: &str, tick, citation: ArchiveCitation| {
            ArchiveKnowledgeGrant::try_new(page.clone(), key.into(), tick, citation)
                .expect("exact grant")
        };
        let knowledge = ArchiveKnowledge::try_new(vec![
            grant(
                "subject",
                0,
                ArchiveCitation::try_new(
                    "captured-organizer".into(),
                    "disclosed-organization".into(),
                )
                .expect("identity citation"),
            ),
            grant(early_id.grant_key(), 1, early_id.citation().clone()),
        ])
        .expect("historical knowledge");
        let renderer = FogSafeArchiveRenderer::new().expect("Archive renderer");
        let historical = renderer
            .render(&revision(rows[1].acquired_period), &knowledge)
            .expect("earned earlier revision");
        assert!(historical.citations().contains(early_id.citation()));
        assert!(!historical.citations().contains(future_id.citation()));
        let current = renderer
            .render(&later, &knowledge)
            .expect("same restricted reader");
        assert!(!current.citations().contains(future_id.citation()));
        assert!(!current.citations().contains(early_id.citation()));
    }

    #[test]
    fn scoped_archive_records_cash_disposition_and_loss_on_the_actual_support_signal() {
        use crate::organizer_aid_fixture as fixture;
        use babylon_practice_contract::{OrganizerAidCashStatus, OrganizerAllocation};
        let config = fixture::config();
        let session = fixture::authored_session(
            crate::michigan_dynamic_hex_foundation().expect("foundation"),
            config,
            false,
            false,
        );
        let command = fixture::commitment_with_allocation(
            &session,
            OrganizerChoice::LocalAid,
            OrganizerAllocation::Aid {
                food_quantity: 1,
                cash_micros: 3,
            },
        );
        let candidate = fixture::prepare(&session, Some(&command));
        let mut row = candidate
            .material()
            .register()
            .organizer_journal()
            .expect("journal")
            .latest()
            .expect("dated entry")
            .aid_receipts[0]
            .clone();
        row.support.material_postings.payer_cash_granted_micros = 0;
        row.support.cash_status = OrganizerAidCashStatus::Unfunded;
        let unfunded = aid_signal(&row).expect("unfunded signal");
        row.support.cash_status = OrganizerAidCashStatus::ReceivingRefused;
        let refused = aid_signal(&row).expect("refused signal");
        assert!(unfunded.value().contains("Cash outcome: unfunded"));
        assert!(refused.value().contains("Cash outcome: receiving refused"));
        assert_ne!(unfunded.value(), refused.value());
        row.support.material_postings.lost_quantity = 1;
        let lost = aid_signal(&row).expect("positive freight loss");
        assert!(lost.value().contains("Freight loss: 1"));
        assert!(!refused.value().contains("household_consumed_quantity"));
    }

    #[test]
    fn aid_evidence_preserves_original_dates_and_distinguishes_support_from_consumption() {
        let status = OrganizerFoodDelivery::Granted {
            granted_quantity: 2,
        };
        let material_postings = OrganizerAidMaterialPostings {
            dispatched_quantity: 0,
            fulfillment_hours: 0,
            payer_cash_granted_micros: 6,
            lost_quantity: 0,
        };
        let mut evidence = AidSupportEvidence {
            admission: 0,
            dispatch: 1,
            resolution: 3,
            original_commitment: &[1; 32],
            material_commitment: &[2; 32],
            good: &[3; 32],
            unit: &[4; 32],
            status,
            cash_status: OrganizerAidCashStatus::Granted,
            material_postings: &material_postings,
        };
        let text = aid_support_text(&evidence);
        assert!(text.contains("admission period: 0"));
        assert!(text.contains("dispatch period: 1"));
        assert!(text.contains("resolution period: 3"));
        assert!(text.contains("Actual material postings in period 3"));
        assert!(text.contains("Dispatched food: 0 units; donor household fulfillment: 0 hours"));
        assert!(text.contains("Aid payer cash: gift paid 6 micro-units"));
        assert!(text.contains("fulfillment is separate from independent coordination"));
        assert!(text.contains(&hex(&[2; 32])));
        assert!(text.contains("Granted quantity: 2"));
        assert!(!text.contains("recipient total consumption"));
        assert!(!text.contains("Bounded credit for this original"));
        assert!(text.contains("partner decides independently"));
        let waiting = OrganizerFoodDelivery::AwaitingDelivery;
        let empty_postings = OrganizerAidMaterialPostings {
            dispatched_quantity: 0,
            fulfillment_hours: 0,
            payer_cash_granted_micros: 0,
            lost_quantity: 0,
        };
        evidence.material_postings = &empty_postings;
        evidence.status = waiting;
        let text = aid_support_text(&evidence);
        assert!(text.contains("Pending: surviving freight"));
        assert!(text.contains("Aid payer cash: gift paid 0 micro-units"));
        assert!(!text.contains("Granted quantity"));
        let failed = OrganizerFoodDelivery::TerminalFailure;
        evidence.status = failed;
        let text = aid_support_text(&evidence);
        assert!(text.contains("Terminal food failure: no food was granted"));
        assert!(!text.contains("no support was granted"));
        assert!(text.contains("donor household fulfillment: 0 hours"));
        assert!(text.contains("gift paid 0"));
        assert!(!text.contains("Pending:"));
        let cash_only = OrganizerAidMaterialPostings {
            payer_cash_granted_micros: 6,
            ..empty_postings
        };
        evidence.material_postings = &cash_only;
        let text = aid_support_text(&evidence);
        assert!(text.contains("Terminal food failure"));
        assert!(text.contains("gift paid 6 micro-units"));
        assert!(!text.contains("no support was granted"));
    }

    #[test]
    fn missing_report_does_not_attribute_withholding_to_a_participating_partner() {
        let mut receipt = OrganizerReceipt {
            receipt_id: [2; 32],
            commitment_id: Some([3; 32]),
            actor_id: 101,
            period: 1,
            choice: OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost),
            standing_work: false,
            outcome: OrganizerOutcome::EvidenceWithheld,
            hours_spent: 12,
            partner_actor_id: Some(102),
            partner_response: OrganizerPartnerResponse::Participated,
            observation_ids: vec![],
            contact_product_id: None,
            time_use: vec![],
        };
        let signal = practice_signal(&receipt)
            .expect("the fixture call `practice_signal` succeeds for the authored inputs");
        let text = signal.value();
        assert!(text.contains("Period 1: Ask about work and output"));
        assert!(text.contains("Result: No report obtained"));
        assert!(text.contains("Independent partner: participated"));
        assert!(text.contains("Time spent: 12 organizer-hours"));
        assert!(text.contains("Source: specific ruling"));
        assert!(!text.contains("withheld"));
        receipt.standing_work = true;
        receipt.commitment_id = None;
        receipt.choice = OrganizerChoice::Hold;
        receipt.outcome = OrganizerOutcome::ContactCompleted;
        receipt.hours_spent = 8;
        let signal = practice_signal(&receipt)
            .expect("the fixture call `practice_signal` succeeds for the authored inputs");
        let text = signal.value();
        assert!(text.contains("Period 1: Keep current routine"));
        assert!(text.contains("Result: Mutual contact completed"));
        assert!(text.contains("Source: saved routine"));

        receipt.commitment_id = Some([3; 32]);
        receipt.standing_work = false;
        receipt.choice = OrganizerChoice::PauseStanding;
        receipt.outcome = OrganizerOutcome::StandingPaused;
        receipt.hours_spent = 0;
        receipt.partner_response = OrganizerPartnerResponse::NotRequested;
        let signal = practice_signal(&receipt)
            .expect("the fixture call `practice_signal` succeeds for the authored inputs");
        let text = signal.value();
        assert!(text.contains("Period 1: Pause neighborhood work"));
        assert!(text.contains("Result: Standing work paused"));
        assert!(text.contains("Independent partner: participation not requested"));

        receipt.standing_work = true;
        receipt.choice = OrganizerChoice::ResumeStanding;
        receipt.outcome = OrganizerOutcome::ContactUncompleted;
        receipt.hours_spent = 8;
        receipt.partner_response = OrganizerPartnerResponse::Refused;
        let signal = practice_signal(&receipt)
            .expect("the fixture call `practice_signal` succeeds for the authored inputs");
        let text = signal.value();
        assert!(text.contains("Period 1: Resume neighborhood work"));
        assert!(text.contains("Source: specific ruling · saved routine"));
        assert!(text.contains("Result: Contact attempt uncompleted"));
        assert!(text.contains("Independent partner: refused"));
        assert!(!text.contains("Result: Standing work resumed"));
    }

    #[test]
    fn observation_projection_refuses_changed_keys_subject_or_periods_with_unchanged_bytes() {
        let expected = observation();
        let bytes =
            serde_json::to_vec(&expected).expect("the value serializes to canonical JSON bytes");
        assert!(
            validate_observation_columns(&expected, &[1; 32], "101", "104", (2, 3), &bytes).is_ok()
        );
        for (key, actor, subject, periods) in [
            ([9; 32], "101", "104", (2, 3)),
            ([1; 32], "102", "104", (2, 3)),
            ([1; 32], "101", "105", (2, 3)),
            ([1; 32], "101", "104", (1, 3)),
            ([1; 32], "101", "104", (2, 2)),
        ] {
            assert!(matches!(
                validate_observation_columns(&expected, &key, actor, subject, periods, &bytes),
                Err(MaterialRuntimeError::OrganizerStorage)
            ));
        }
        let mut malformed = bytes;
        malformed.push(b' ');
        assert!(matches!(
            validate_observation_columns(&expected, &[1; 32], "101", "104", (2, 3), &malformed),
            Err(MaterialRuntimeError::OrganizerStorage)
        ));
    }

    #[test]
    fn receipt_projection_refuses_changed_key_actor_or_period_with_unchanged_bytes() {
        let expected = OrganizerReceipt {
            receipt_id: [2; 32],
            commitment_id: Some([3; 32]),
            actor_id: 101,
            period: 3,
            choice: OrganizerChoice::PauseStanding,
            standing_work: false,
            outcome: OrganizerOutcome::StandingPaused,
            hours_spent: 0,
            partner_actor_id: None,
            partner_response: OrganizerPartnerResponse::NotRequested,
            observation_ids: vec![],
            contact_product_id: None,
            time_use: vec![],
        };
        let bytes =
            serde_json::to_vec(&expected).expect("the value serializes to canonical JSON bytes");
        assert!(validate_receipt_columns(&expected, &[2; 32], "101", 3, &bytes).is_ok());
        for (key, actor, period) in [
            ([9; 32], "101", 3),
            ([2; 32], "102", 3),
            ([2; 32], "101", 2),
        ] {
            assert!(matches!(
                validate_receipt_columns(&expected, &key, actor, period, &bytes),
                Err(MaterialRuntimeError::OrganizerStorage)
            ));
        }
        let mut malformed = bytes;
        malformed.push(b' ');
        assert!(matches!(
            validate_receipt_columns(&expected, &[2; 32], "101", 3, &malformed),
            Err(MaterialRuntimeError::OrganizerStorage)
        ));
    }
}
