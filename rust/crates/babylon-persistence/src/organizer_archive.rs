//! Period-specific organizer knowledge, inserted before the material tick marker.

use crate::{
    archive::{database, insert_grant_row},
    identity::CampaignId,
    material_runtime::MaterialRuntimeError,
    ArchiveCitation, ArchiveDirtyBatch, ArchiveDossierProducer, ArchiveKnowledge, ArchivePageInput,
    ArchiveProducerOutcome, ArchiveSignal, ArchiveSubject, ArchiveSubjectKind,
    PendingArchiveReceipt, SemanticArchiveError,
};
use babylon_practice_contract::{
    OrganizerChoice, OrganizerConfig, OrganizerInquiry, OrganizerObservation, OrganizerOutcome,
    OrganizerPartnerResponse, OrganizerReceipt, OrganizerReport,
};
use babylon_tick::material_world::MaterialWorldRegister;
use postgres::{GenericClient, NoTls};

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
        "committed-organizer-report-v1".into(),
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
    row: &postgres::Row,
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
    row: &postgres::Row,
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
    if state.period != 0 {
        validate_subjects(client, campaign, config)?;
    }
    let actor = config.controlled_actor_id.to_string();
    insert_subjects(client, campaign, config)?;
    for observation in &state.observations {
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
        insert_grant_row(
            client,
            campaign,
            "workplace",
            &observation.subject_id.to_string(),
            &format!("report-{}", hex(&observation.observation_id)),
            observation.acquired_period,
            &citation,
        )
        .map_err(archive_error)?;
    }
    for receipt in &state.receipts {
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
        insert_grant_row(
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
    validate_projection(client, campaign, register)
}

fn subject_definitions(config: &OrganizerConfig) -> [(ArchiveSubjectKind, u64, &str); 4] {
    [
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
    ]
}

fn validate_subjects(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    config: &OrganizerConfig,
) -> Result<(), MaterialRuntimeError> {
    let rows = client.query("SELECT actor_id,subject_kind,subject_id,title FROM babylon_state.organizer_subject_v1 WHERE campaign_id=$1", &[campaign.as_uuid()])?;
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
        insert_grant_row(
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
        OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost) => "Ask about work and output",
        OrganizerChoice::Inquiry(OrganizerInquiry::MaintenanceReceived) => "Ask about maintenance",
        OrganizerChoice::Reinforce => "Reinforce workplace contact",
        OrganizerChoice::Hold => "Keep current routine",
        OrganizerChoice::PauseStanding => "Pause neighborhood work",
        OrganizerChoice::ResumeStanding => "Resume neighborhood work",
    };
    let outcome = match receipt.outcome {
        OrganizerOutcome::EvidenceObtained => "Evidence obtained",
        OrganizerOutcome::EvidenceWithheld => "No report obtained",
        OrganizerOutcome::ContactCompleted => "Mutual contact completed",
        OrganizerOutcome::ContactUncompleted => "Contact attempt uncompleted",
        OrganizerOutcome::InsufficientTime => "Insufficient committed time",
        OrganizerOutcome::StandingPaused => "Standing work paused",
        OrganizerOutcome::StandingResumed => "Standing work resumed",
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
    config: postgres::Config,
}
impl OrganizerDossierProducer {
    /// Bind the writer connection used by the existing Archive worker.
    #[must_use]
    pub fn new(config: &postgres::Config) -> Self {
        Self {
            config: config.clone(),
        }
    }
}

pub(crate) fn archive_register_error(error: MaterialRuntimeError) -> SemanticArchiveError {
    match error {
        MaterialRuntimeError::Database(error)
        | MaterialRuntimeError::DatabaseLockRefused(error)
        | MaterialRuntimeError::DatabaseStatementCanceled(error) => {
            database("read organizer Archive register", &error)
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
        campaign: uuid::Uuid,
        receipt: &PendingArchiveReceipt,
        _knowledge: &ArchiveKnowledge,
        page_budget: usize,
    ) -> Result<ArchiveProducerOutcome, SemanticArchiveError> {
        let mut client = self
            .config
            .connect(NoTls)
            .map_err(|e| database("connect organizer Archive producer", &e))?;
        let mut transaction = client
            .build_transaction()
            .isolation_level(postgres::IsolationLevel::RepeatableRead)
            .read_only(true)
            .start()
            .map_err(|e| database("begin organizer Archive read", &e))?;
        let register = crate::material_runtime::read_archive_organizer_register(
            &mut transaction,
            CampaignId::from_uuid(campaign),
            receipt,
        )
        .map_err(archive_register_error)?;
        let Some(state) = register
            .as_ref()
            .and_then(MaterialWorldRegister::organizer_state)
        else {
            return Ok(ArchiveProducerOutcome::new(
                ArchiveDirtyBatch::try_new(
                    receipt.resolve_tick(),
                    *receipt.tick_content_hash(),
                    Vec::new(),
                )?,
                0,
            ));
        };
        let tick = i64::try_from(receipt.resolve_tick())
            .map_err(|_| SemanticArchiveError::InvalidVerifiedTick)?;
        let subjects = transaction.query("SELECT s.actor_id,s.subject_kind,s.subject_id,s.title FROM babylon_state.organizer_subject_v1 s WHERE campaign_id=$1 AND NOT EXISTS(SELECT 1 FROM babylon_meta.archive_page_revision_v2 p WHERE p.campaign_id=s.campaign_id AND p.subject_kind=s.subject_kind AND p.subject_id=s.subject_id AND p.effective_tick=$2) ORDER BY subject_kind,subject_id", &[&campaign,&tick]).map_err(|e|database("read organizer report subjects",&e))?;
        let total = subjects.len();
        let mut pages = Vec::new();
        let mut observations = state.observations.iter().collect::<Vec<_>>();
        observations.sort_by_key(|row| (row.acquired_period, row.observation_id));
        let mut receipts = state.receipts.iter().collect::<Vec<_>>();
        receipts.sort_by_key(|row| (row.period, row.receipt_id));
        for row in subjects.into_iter().take(page_budget) {
            let actor: String = row.get(0);
            let kind: String = row.get(1);
            let id: String = row.get(2);
            let title: String = row.get(3);
            let mut signals = Vec::new();
            if kind == "workplace" {
                for observation in observations.iter().copied().filter(|observation| {
                    observation.actor_id.to_string() == actor
                        && observation.subject_id.to_string() == id
                }) {
                    signals.push(observation_signal(observation)?);
                }
            } else {
                for value in receipts
                    .iter()
                    .copied()
                    .filter(|value| value.actor_id.to_string() == actor && actor == id)
                {
                    signals.push(practice_signal(value)?);
                }
            }
            let kind = crate::archive::decode_subject_kind(&kind)?;
            pages.push(ArchivePageInput::try_new(ArchiveSubject::try_new(kind,id,title)?,receipt.resolve_tick(),*receipt.tick_content_hash(),"Designed Wayne scenario: these fictional organizations and modeled workplace do not represent observed organizations or the whole workforce. What have we learned or performed, and which commitment should we review next?".into(),signals,Vec::new())?);
        }
        transaction
            .commit()
            .map_err(|e| database("finish organizer Archive read", &e))?;
        let remaining = total.saturating_sub(pages.len());
        Ok(ArchiveProducerOutcome::new(
            ArchiveDirtyBatch::try_new(
                receipt.resolve_tick(),
                *receipt.tick_content_hash(),
                pages,
            )?,
            remaining,
        ))
    }
}

fn observation_signal(
    observation: &OrganizerObservation,
) -> Result<ArchiveSignal, SemanticArchiveError> {
    ArchiveSignal::try_new(
        format!("report-{}", hex(&observation.observation_id)),
        format!(
            "Workplace evidence from period {}",
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

/// The derived SQL projection must equal the actor-safe portion of the sealed
/// register before a runtime restart or ambiguous commit can acknowledge it.
pub(crate) fn validate_projection(
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
    validate_subjects(client, campaign, config)?;
    let tick = i64::try_from(state.period).map_err(|_| MaterialRuntimeError::Bounds)?;
    let observed = client.query("SELECT observation_id,actor_id,subject_id,observed_period,acquired_period,observation_bytes FROM babylon_state.organizer_observation_v1 WHERE campaign_id=$1 AND acquired_period<=$2 ORDER BY observation_id", &[campaign.as_uuid(),&tick])?;
    let mut expected = state
        .observations
        .iter()
        .filter(|row| row.actor_id == config.controlled_actor_id)
        .collect::<Vec<_>>();
    expected.sort_by_key(|row| row.observation_id);
    if observed.len() != expected.len() {
        return Err(MaterialRuntimeError::OrganizerStorage);
    }
    for (row, expected) in observed.iter().zip(expected) {
        validate_observation_row(row, expected)?;
    }
    let receipts = client.query("SELECT receipt_id,actor_id,resolve_tick,receipt_bytes FROM babylon_state.organizer_receipt_v1 WHERE campaign_id=$1 AND resolve_tick<=$2 ORDER BY receipt_id", &[campaign.as_uuid(),&tick])?;
    let mut expected = state
        .receipts
        .iter()
        .filter(|row| row.actor_id == config.controlled_actor_id)
        .collect::<Vec<_>>();
    expected.sort_by_key(|row| row.receipt_id);
    if receipts.len() != expected.len() {
        return Err(MaterialRuntimeError::OrganizerStorage);
    }
    for (row, expected) in receipts.iter().zip(expected) {
        validate_receipt_row(row, expected)?;
    }
    Ok(())
}

#[cfg(test)]
mod projection_tests {
    use super::*;

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
        let signal = practice_signal(&receipt).unwrap();
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
        let signal = practice_signal(&receipt).unwrap();
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
        let signal = practice_signal(&receipt).unwrap();
        let text = signal.value();
        assert!(text.contains("Period 1: Pause neighborhood work"));
        assert!(text.contains("Result: Standing work paused"));
        assert!(text.contains("Independent partner: participation not requested"));

        receipt.standing_work = true;
        receipt.choice = OrganizerChoice::ResumeStanding;
        receipt.outcome = OrganizerOutcome::ContactUncompleted;
        receipt.hours_spent = 8;
        receipt.partner_response = OrganizerPartnerResponse::Refused;
        let signal = practice_signal(&receipt).unwrap();
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
        let bytes = serde_json::to_vec(&expected).unwrap();
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
        let bytes = serde_json::to_vec(&expected).unwrap();
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
