//! Deterministic extraction of player-referenced permanent-journal records.
//!
//! One period's organizer evidence is retained exactly. Material receipt
//! families keep every row that names a player principal, commitment, or earned
//! observation; every family also publishes a compact, content-hashed summary of
//! its exact canonical frame so background rows stay byte-bound without being
//! copied into the journal.

use serde::Serialize;

use babylon_kernel::content_digest;
use babylon_material_circuit::AidReceipt;
use babylon_material_circuit::CollectionReceipt;
use babylon_material_circuit::HouseholdConsumptionReceipt;
use babylon_material_circuit::HouseholdDemandReceipt;
use babylon_material_circuit::HouseholdServiceReceipt;
use babylon_material_circuit::HouseholdTimeReceipt;
use babylon_practice_contract::OrganizerAidResolutionReceipt;
use babylon_practice_contract::OrganizerCollectionResolution;
use babylon_practice_contract::OrganizerConfig;
use babylon_practice_contract::OrganizerObservation;
use babylon_practice_contract::OrganizerPeriodJournalEntries;
use babylon_practice_contract::OrganizerReceipt;
use babylon_practice_contract::OrganizerTimeBindingMode;
use babylon_tick::material_world;
use babylon_tick::material_world::MaterialTickReceipts;

use super::chunks::JournalKind;
use super::chunks::SubjectKind;
use super::SaveError;

/// Domain separator for extracted record content identities.
const RECORD_DOMAIN: &[u8] = b"babylon.permanent-journal-record.v1\0";

/// Domain separator for background family summaries.
const SUMMARY_DOMAIN: &[u8] = b"babylon.permanent-journal-family.v1\0";

/// Default ceiling on player-referenced records in one period.
pub const MAX_EXTRACTED_RECORDS: usize = 4_096;

/// Closed receipt-family count: 36 disposition families.
pub const RECEIPT_FAMILIES: u8 = 36;

/// Who and what this extraction treats as the player's causal evidence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExtractionPolicy {
    /// Controlled player actor.
    pub actor_id: u64,
    /// Contributors whose household hours belong to the player.
    pub contributor_ids: Vec<u64>,
    /// Household principals whose material receipts belong to the player.
    pub principal_ids: Vec<[u8; 32]>,
    /// Maximum retained records in one period.
    pub max_records: usize,
}

impl ExtractionPolicy {
    /// Bind the player identity from one captured organizer config.
    #[must_use]
    pub fn for_organizer(config: &OrganizerConfig) -> Self {
        let mut contributor_ids = Vec::new();
        let mut principal_ids = Vec::new();
        if let OrganizerTimeBindingMode::Household { bindings } = &config.time_binding {
            for binding in bindings {
                contributor_ids.push(binding.contributor_id);
                principal_ids.push(binding.principal_id);
            }
        }
        contributor_ids.sort_unstable();
        contributor_ids.dedup();
        principal_ids.sort_unstable();
        principal_ids.dedup();
        Self {
            actor_id: config.controlled_actor_id,
            contributor_ids,
            principal_ids,
            max_records: MAX_EXTRACTED_RECORDS,
        }
    }

    fn owns_principal(&self, principal: [u8; 32]) -> bool {
        self.principal_ids.binary_search(&principal).is_ok()
    }

    fn owns_contributor(&self, contributor: u64) -> bool {
        self.contributor_ids.binary_search(&contributor).is_ok()
    }
}

/// One typed subject identity for a journal record.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExtractedSubject {
    /// Closed subject kind.
    pub kind: SubjectKind,
    /// Exact identity bytes.
    pub id: Vec<u8>,
}

/// One retained journal record with its own content identity.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExtractedJournalRecord {
    /// Closed journal record kind.
    pub kind: JournalKind,
    /// Optional typed subject.
    pub subject: Option<ExtractedSubject>,
    /// Optional canonical idempotency key.
    pub record_key: Option<Vec<u8>>,
    /// Optional durable actor identity.
    pub actor_id: Option<[u8; 8]>,
    /// Opaque canonical payload bytes.
    pub payload: Vec<u8>,
    /// Content identity of the payload and subject.
    pub content_hash: [u8; 32],
}

/// One content-hashed summary of an entire receipt family.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ExtractedFamilySummary {
    /// Closed family tag, 1..=36.
    pub family: u8,
    /// Exact committed row count.
    pub rows: u32,
    /// Digest of the family tag, row count, and exact canonical family frame.
    pub content_hash: [u8; 32],
}

/// One period's deterministic permanent-journal extraction.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExtractedPeriodJournal {
    /// Completed period.
    pub period: u64,
    /// Player-referenced records, ordered by closed identity.
    pub records: Vec<ExtractedJournalRecord>,
    /// Every closed receipt family's content-hashed summary.
    pub summaries: Vec<ExtractedFamilySummary>,
    /// Digest binding the period, records, and summaries.
    pub content_hash: [u8; 32],
}

/// Extract one completed period's player evidence and background summaries.
///
/// The result is a pure function of the supplied period, policy, committed
/// material receipts, and exact organizer journal entries.
///
/// # Errors
///
/// Refuses a zero or mismatched period, a policy with unsorted identities, a
/// record ceiling breach, an unencodable organizer payload, or a family encoder
/// fault.
#[allow(
    clippy::too_many_lines,
    reason = "one ordered pass extracts every closed evidence family beside its content-hashed summary"
)]
pub fn extract_permanent_journal_entries(
    period: u64,
    policy: &ExtractionPolicy,
    receipts: &MaterialTickReceipts,
    organizer_entries: &OrganizerPeriodJournalEntries,
) -> Result<ExtractedPeriodJournal, SaveError> {
    if period == 0 || receipts.resolve_tick != period || organizer_entries.period != period {
        return Err(SaveError::InvalidField {
            table: "permanent_journal",
            field: "period",
            reason: "the extracted period must match every supplied fact",
        });
    }
    if policy.max_records == 0 {
        return Err(SaveError::InvalidField {
            table: "permanent_journal",
            field: "max_records",
            reason: "the extraction policy retains no records",
        });
    }
    let mut records = Vec::new();
    for observation in &organizer_entries.observations {
        records.push(observation_record(policy, observation)?);
    }
    for receipt in &organizer_entries.receipts {
        if touches_receipt(policy, receipt) {
            records.push(receipt_record(policy, receipt)?);
        }
    }
    for row in &organizer_entries.collection_receipts {
        if touches_collection(policy, row) {
            records.push(collection_record(policy, row)?);
        }
    }
    for row in &organizer_entries.aid_receipts {
        if touches_aid_resolution(policy, row) {
            records.push(aid_resolution_record(policy, row)?);
        }
    }
    for row in &receipts.household_time {
        if policy.owns_principal(row.principal_id.as_bytes()) {
            records.push(material_record(
                policy,
                SubjectKind::Player,
                policy.actor_id.to_be_bytes().to_vec(),
                household_time_row(policy, row),
                &row.principal_id.as_bytes(),
                row.period,
            ));
        }
    }
    for row in &receipts.household_demand {
        if policy.owns_principal(row.principal_id.as_bytes()) {
            records.push(material_record(
                policy,
                SubjectKind::Player,
                policy.actor_id.to_be_bytes().to_vec(),
                household_demand_row(policy, row),
                &row.principal_id.as_bytes(),
                row.period,
            ));
        }
    }
    for row in &receipts.household_consumption {
        if policy.owns_principal(row.principal_id.as_bytes()) {
            records.push(material_record(
                policy,
                SubjectKind::Player,
                policy.actor_id.to_be_bytes().to_vec(),
                household_consumption_row(policy, row),
                &row.principal_id.as_bytes(),
                row.period,
            ));
        }
    }
    for row in &receipts.household_services {
        if policy.owns_principal(row.principal_id.as_bytes()) {
            records.push(material_record(
                policy,
                SubjectKind::Player,
                policy.actor_id.to_be_bytes().to_vec(),
                household_service_row(policy, row),
                &row.principal_id.as_bytes(),
                row.period,
            ));
        }
    }
    for row in &receipts.aid {
        if policy.owns_principal(row.donor.as_bytes())
            || policy.owns_principal(row.recipient.as_bytes())
        {
            records.push(material_record(
                policy,
                SubjectKind::Commitment,
                row.commitment_id.as_bytes().to_vec(),
                aid_row(policy, row),
                &row.mandate_id,
                row.period,
            ));
        }
    }
    for row in &receipts.collections {
        if policy.owns_principal(row.donor.as_bytes()) || row.actor_id == policy.actor_id {
            records.push(material_record(
                policy,
                SubjectKind::Commitment,
                row.original_commitment_id.to_vec(),
                collection_row(policy, row),
                &row.mandate_id,
                row.period,
            ));
        }
    }
    if records.len() > policy.max_records {
        return Err(SaveError::PayloadTooLarge {
            table: "permanent_journal",
            limit: policy.max_records,
            actual: records.len(),
        });
    }
    records.sort_by_key(|record| {
        (
            record.kind.code(),
            record
                .subject
                .as_ref()
                .map_or(0, |subject| subject.kind.code()),
            record
                .subject
                .as_ref()
                .map(|subject| subject.id.clone())
                .unwrap_or_default(),
            record.record_key.clone().unwrap_or_default(),
        )
    });
    let mut summaries = Vec::new();
    for family in 1..=RECEIPT_FAMILIES {
        let rows = material_world::receipt_family_rows(receipts, family);
        let bytes =
            material_world::receipt_family_bytes(period, receipts, family).map_err(|_| {
                SaveError::CorruptPayload {
                    table: "permanent_journal",
                    reason: "the receipt family frame does not encode",
                }
            })?;
        let mut identity = Vec::from(SUMMARY_DOMAIN);
        identity.push(family);
        identity.extend_from_slice(
            &u64::try_from(rows)
                .map_err(|_| SaveError::Arithmetic {
                    field: "receipt family row count",
                })?
                .to_be_bytes(),
        );
        identity.extend_from_slice(&bytes);
        summaries.push(ExtractedFamilySummary {
            family,
            rows: u32::try_from(rows).map_err(|_| SaveError::Arithmetic {
                field: "receipt family row count",
            })?,
            content_hash: content_digest::sha256_of(&identity),
        });
    }
    let mut identity = Vec::new();
    identity.extend_from_slice(RECORD_DOMAIN);
    identity.extend_from_slice(&period.to_be_bytes());
    for record in &records {
        identity.extend_from_slice(&record.content_hash);
    }
    for summary in &summaries {
        identity.push(summary.family);
        identity.extend_from_slice(&summary.content_hash);
    }
    Ok(ExtractedPeriodJournal {
        period,
        records,
        summaries,
        content_hash: content_digest::sha256_of(&identity),
    })
}

fn touches_receipt(policy: &ExtractionPolicy, receipt: &OrganizerReceipt) -> bool {
    receipt.actor_id == policy.actor_id
        || receipt
            .time_use
            .iter()
            .any(|row| policy.owns_contributor(row.contributor_id))
}

fn touches_collection(policy: &ExtractionPolicy, row: &OrganizerCollectionResolution) -> bool {
    row.practice.actor_id == policy.actor_id || row.fact.actor_id == policy.actor_id
}

fn touches_aid_resolution(policy: &ExtractionPolicy, row: &OrganizerAidResolutionReceipt) -> bool {
    row.practice.actor_id == policy.actor_id
        || row.authorization.gift.donor_actor_id == policy.actor_id
        || policy.owns_principal(row.authorization.gift.donor_principal_id)
        || policy.owns_principal(row.authorization.gift.recipient_principal_id)
}

fn observation_record(
    policy: &ExtractionPolicy,
    observation: &OrganizerObservation,
) -> Result<ExtractedJournalRecord, SaveError> {
    let payload = encode_payload(observation)?;
    let subject = ExtractedSubject {
        kind: SubjectKind::Observation,
        id: observation.observation_id.to_vec(),
    };
    let content_hash = record_hash(JournalKind::PlayerReceipt, Some(&subject), &payload);
    Ok(ExtractedJournalRecord {
        kind: JournalKind::PlayerReceipt,
        subject: Some(subject),
        record_key: Some(observation.observation_id.to_vec()),
        actor_id: Some(policy.actor_id.to_be_bytes()),
        payload,
        content_hash,
    })
}

fn receipt_record(
    policy: &ExtractionPolicy,
    receipt: &OrganizerReceipt,
) -> Result<ExtractedJournalRecord, SaveError> {
    let payload = encode_payload(receipt)?;
    let subject = match receipt.commitment_id {
        Some(id) => ExtractedSubject {
            kind: SubjectKind::Commitment,
            id: id.to_vec(),
        },
        None => ExtractedSubject {
            kind: SubjectKind::Player,
            id: policy.actor_id.to_be_bytes().to_vec(),
        },
    };
    let content_hash = record_hash(JournalKind::PlayerReceipt, Some(&subject), &payload);
    Ok(ExtractedJournalRecord {
        kind: JournalKind::PlayerReceipt,
        subject: Some(subject),
        record_key: Some(receipt.receipt_id.to_vec()),
        actor_id: Some(policy.actor_id.to_be_bytes()),
        payload,
        content_hash,
    })
}

fn collection_record(
    policy: &ExtractionPolicy,
    row: &OrganizerCollectionResolution,
) -> Result<ExtractedJournalRecord, SaveError> {
    let payload = encode_payload(row)?;
    let subject = ExtractedSubject {
        kind: SubjectKind::Commitment,
        id: row.commitment.commitment_id.to_vec(),
    };
    let content_hash = record_hash(JournalKind::PlayerReceipt, Some(&subject), &payload);
    Ok(ExtractedJournalRecord {
        kind: JournalKind::PlayerReceipt,
        subject: Some(subject),
        record_key: Some(row.practice.receipt_id.to_vec()),
        actor_id: Some(policy.actor_id.to_be_bytes()),
        payload,
        content_hash,
    })
}

fn aid_resolution_record(
    policy: &ExtractionPolicy,
    row: &OrganizerAidResolutionReceipt,
) -> Result<ExtractedJournalRecord, SaveError> {
    let payload = encode_payload(row)?;
    let subject = ExtractedSubject {
        kind: SubjectKind::Commitment,
        id: row.authorization.gift.commitment.commitment_id.to_vec(),
    };
    let content_hash = record_hash(JournalKind::PlayerReceipt, Some(&subject), &payload);
    Ok(ExtractedJournalRecord {
        kind: JournalKind::PlayerReceipt,
        subject: Some(subject),
        record_key: Some(row.practice.receipt_id.to_vec()),
        actor_id: Some(policy.actor_id.to_be_bytes()),
        payload,
        content_hash,
    })
}

fn material_record(
    policy: &ExtractionPolicy,
    kind: SubjectKind,
    id: Vec<u8>,
    payload: Vec<u8>,
    salt: &[u8],
    _period: u64,
) -> ExtractedJournalRecord {
    let mut payload = payload;
    payload.extend_from_slice(salt);
    let subject = ExtractedSubject { kind, id };
    let content_hash = record_hash(JournalKind::PlayerReceipt, Some(&subject), &payload);
    ExtractedJournalRecord {
        kind: JournalKind::PlayerReceipt,
        subject: Some(subject),
        record_key: Some(content_hash.to_vec()),
        actor_id: Some(policy.actor_id.to_be_bytes()),
        payload,
        content_hash,
    }
}

fn record_hash(kind: JournalKind, subject: Option<&ExtractedSubject>, payload: &[u8]) -> [u8; 32] {
    let mut identity = Vec::from(RECORD_DOMAIN);
    identity.push(u8::try_from(kind.code()).unwrap_or(u8::MAX));
    if let Some(subject) = subject {
        identity.push(u8::try_from(subject.kind.code()).unwrap_or(u8::MAX));
        identity.extend_from_slice(&subject.id);
    }
    identity.extend_from_slice(payload);
    content_digest::sha256_of(&identity)
}

fn encode_payload<T: Serialize>(value: &T) -> Result<Vec<u8>, SaveError> {
    serde_json::to_vec(value).map_err(|_| SaveError::InvalidField {
        table: "permanent_journal",
        field: "payload",
        reason: "the organizer evidence does not encode",
    })
}

fn household_time_row(policy: &ExtractionPolicy, row: &HouseholdTimeReceipt) -> Vec<u8> {
    let mut bytes = Vec::new();
    bytes.extend_from_slice(&row.principal_id.as_bytes());
    bytes.extend_from_slice(&row.labor_unit_id.as_bytes());
    bytes.extend_from_slice(&policy.actor_id.to_be_bytes());
    bytes.extend_from_slice(&row.period.to_be_bytes());
    for value in [
        row.endowment_hours,
        row.attended_hours,
        row.protected_hours,
        row.protected_unresolved_hours,
        row.unpaid_requested_hours,
        row.unpaid_allocated_hours,
        row.unpaid_unresolved_hours,
        row.contribution_available_hours,
    ] {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
    bytes
}

fn household_demand_row(policy: &ExtractionPolicy, row: &HouseholdDemandReceipt) -> Vec<u8> {
    let mut bytes = Vec::new();
    bytes.extend_from_slice(&row.principal_id.as_bytes());
    bytes.extend_from_slice(&policy.actor_id.to_be_bytes());
    bytes.extend_from_slice(&row.period.to_be_bytes());
    for id in [
        row.retailer_site_id.as_bytes(),
        row.good_id.as_bytes(),
        row.unit_id.as_bytes(),
        row.order_id.as_bytes(),
    ] {
        bytes.extend_from_slice(&id);
    }
    for value in [
        row.opening_stock,
        row.required_quantity,
        row.desired_quantity,
        row.requested_quantity,
        row.admitted_quantity,
        row.fulfilled_quantity,
        row.expired_quantity,
    ] {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
    bytes.extend_from_slice(&row.unit_price.micro_units().to_be_bytes());
    bytes
}

fn household_consumption_row(
    policy: &ExtractionPolicy,
    row: &HouseholdConsumptionReceipt,
) -> Vec<u8> {
    let mut bytes = Vec::new();
    bytes.extend_from_slice(&row.principal_id.as_bytes());
    bytes.extend_from_slice(&policy.actor_id.to_be_bytes());
    bytes.extend_from_slice(&row.period.to_be_bytes());
    bytes.extend_from_slice(&row.good_id.as_bytes());
    bytes.extend_from_slice(&row.unit_id.as_bytes());
    for value in [
        row.required_quantity,
        row.available_quantity,
        row.consumed_quantity,
        row.unmet_quantity,
        row.closing_quantity,
    ] {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
    bytes
}

fn household_service_row(policy: &ExtractionPolicy, row: &HouseholdServiceReceipt) -> Vec<u8> {
    let mut bytes = Vec::new();
    bytes.extend_from_slice(&row.principal_id.as_bytes());
    bytes.extend_from_slice(&policy.actor_id.to_be_bytes());
    bytes.extend_from_slice(&row.period.to_be_bytes());
    bytes.extend_from_slice(&row.good_id.as_bytes());
    bytes.extend_from_slice(&row.unit_id.as_bytes());
    for value in [
        row.required_quantity,
        row.performed_quantity,
        row.satisfied_quantity,
        row.unmet_quantity,
        row.unused_quantity,
    ] {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
    bytes
}

fn aid_row(policy: &ExtractionPolicy, row: &AidReceipt) -> Vec<u8> {
    let mut bytes = Vec::new();
    bytes.extend_from_slice(&policy.actor_id.to_be_bytes());
    bytes.extend_from_slice(&row.period.to_be_bytes());
    bytes.extend_from_slice(&row.dispatch_period.to_be_bytes());
    bytes.extend_from_slice(&row.commitment_id.as_bytes());
    bytes.extend_from_slice(&row.mandate_id);
    bytes.extend_from_slice(&row.donor.as_bytes());
    bytes.extend_from_slice(&row.recipient.as_bytes());
    bytes.extend_from_slice(&row.good_id.as_bytes());
    bytes.extend_from_slice(&row.unit_id.as_bytes());
    bytes.push(row.outcome as u8);
    bytes.extend_from_slice(&row.quantity.to_be_bytes());
    bytes.extend_from_slice(&row.carrying_amount.micro_units().to_be_bytes());
    bytes.extend_from_slice(&row.cash_amount.micro_units().to_be_bytes());
    bytes.extend_from_slice(&row.contribution_hours.to_be_bytes());
    bytes
}

fn collection_row(policy: &ExtractionPolicy, row: &CollectionReceipt) -> Vec<u8> {
    let mut bytes = Vec::new();
    bytes.extend_from_slice(&policy.actor_id.to_be_bytes());
    bytes.extend_from_slice(&row.period.to_be_bytes());
    bytes.extend_from_slice(&row.admitted_period.to_be_bytes());
    bytes.extend_from_slice(&row.original_commitment_id);
    bytes.extend_from_slice(&row.command_nonce);
    bytes.extend_from_slice(&row.mandate_id);
    bytes.extend_from_slice(&row.source_hash);
    bytes.extend_from_slice(&row.actor_id.to_be_bytes());
    bytes.extend_from_slice(&row.contributor_id.to_be_bytes());
    bytes.extend_from_slice(&row.donor.as_bytes());
    bytes.extend_from_slice(&row.recipient.as_bytes());
    bytes.extend_from_slice(&row.labor_unit_id.as_bytes());
    bytes.extend_from_slice(&row.requested.micro_units().to_be_bytes());
    bytes.extend_from_slice(&row.collected.micro_units().to_be_bytes());
    bytes.extend_from_slice(&row.performed_hours.to_be_bytes());
    bytes.push(row.outcome as u8);
    bytes.extend_from_slice(&row.transfer_ordinal.unwrap_or(u32::MAX).to_be_bytes());
    bytes.extend_from_slice(&row.contribution_use_id);
    bytes
}

#[cfg(test)]
mod tests {
    use super::*;

    use babylon_material_circuit::FinalDemandPrincipalId;
    use babylon_material_circuit::HouseholdTimeReceipt;
    use babylon_material_circuit::UnitId;
    use babylon_practice_contract::OrganizerObservation;
    use babylon_practice_contract::OrganizerPeriodJournalEntries;
    use babylon_practice_contract::OrganizerReport;

    fn empty_receipts(period: u64) -> MaterialTickReceipts {
        MaterialTickReceipts {
            household_time: vec![],
            aid: vec![],
            collections: vec![],
            installation: vec![],
            installation_decisions: vec![],
            equipment_wear: vec![],
            investment: vec![],
            staffing_members: vec![],
            member_labor_use: vec![],
            public_budgets: vec![],
            taxes: vec![],
            distributions: vec![],
            contributions: vec![],
            service_performance: vec![],
            household_services: vec![],
            service_markets: vec![],
            service_outputs: vec![],
            income: vec![],
            resolve_tick: period,
            household_demand: vec![],
            household_consumption: vec![],
            procurement: vec![],
            production_plans: vec![],
            prices: vec![],
            money_transfers: vec![],
            wage_accruals: vec![],
            labor_use: vec![],
            production: vec![],
            dispatches: vec![],
            losses: vec![],
            arrivals: vec![],
            deliveries: vec![],
            realizations: vec![],
            handling: vec![],
            local_fulfillments: vec![],
            local_transfers: vec![],
            maintenance: None,
        }
    }

    fn policy() -> ExtractionPolicy {
        ExtractionPolicy {
            actor_id: 101,
            contributor_ids: vec![201],
            principal_ids: vec![[7; 32]],
            max_records: MAX_EXTRACTED_RECORDS,
        }
    }

    fn observation(period: u64) -> OrganizerObservation {
        OrganizerObservation {
            observation_id: [5; 32],
            actor_id: 101,
            subject_id: 104,
            source_actor_id: 102,
            observed_period: period - 1,
            acquired_period: period,
            receipt_id: Some([6; 32]),
            report: OrganizerReport::Work {
                performed_labor_hours: 160,
                output_kg: 960,
                previous_labor_hours: None,
                previous_output_kg: None,
            },
        }
    }

    fn household_time(principal: [u8; 32], period: u64) -> HouseholdTimeReceipt {
        HouseholdTimeReceipt {
            principal_id: FinalDemandPrincipalId::from_bytes(principal),
            period,
            labor_unit_id: UnitId::from_bytes([3; 32]),
            endowment_hours: 8,
            attended_hours: 0,
            protected_hours: 0,
            protected_unresolved_hours: 0,
            unpaid_requested_hours: 0,
            unpaid_allocated_hours: 0,
            unpaid_unresolved_hours: 0,
            contribution_available_hours: 8,
        }
    }

    #[test]
    fn extraction_is_deterministic_and_covers_every_closed_family() {
        let receipts = empty_receipts(3);
        let entries = OrganizerPeriodJournalEntries::new(3);
        let first = extract_permanent_journal_entries(3, &policy(), &receipts, &entries)
            .expect("the empty period extracts deterministically");
        let second = extract_permanent_journal_entries(3, &policy(), &receipts, &entries)
            .expect("the empty period extracts deterministically");
        assert_eq!(first, second);
        assert!(first.records.is_empty());
        assert_eq!(first.summaries.len(), usize::from(RECEIPT_FAMILIES));
        for (index, summary) in first.summaries.iter().enumerate() {
            assert_eq!(usize::from(summary.family), index + 1);
            assert_eq!(summary.rows, 0);
        }
        assert_ne!(first.content_hash, [0; 32]);
    }

    #[test]
    fn earned_observation_is_retained_with_its_exact_identity() {
        let mut entries = OrganizerPeriodJournalEntries::new(3);
        entries.observations.push(observation(3));
        let extracted =
            extract_permanent_journal_entries(3, &policy(), &empty_receipts(3), &entries)
                .expect("the earned observation extracts");
        assert_eq!(extracted.records.len(), 1);
        let record = &extracted.records[0];
        assert_eq!(record.kind, JournalKind::PlayerReceipt);
        let subject = record
            .subject
            .as_ref()
            .expect("the record names its subject");
        assert_eq!(subject.kind, SubjectKind::Observation);
        assert_eq!(subject.id, [5; 32].to_vec());
        assert_eq!(record.record_key, Some([5; 32].to_vec()));
        assert_eq!(record.actor_id, Some(101_u64.to_be_bytes()));
        assert!(!record.payload.is_empty());
    }

    #[test]
    fn owned_principal_row_is_retained_and_background_rows_are_content_hashed() {
        let mut receipts = empty_receipts(3);
        receipts.household_time.push(household_time([7; 32], 3));
        receipts.household_time.push(household_time([9; 32], 3));
        let entries = OrganizerPeriodJournalEntries::new(3);
        let extracted = extract_permanent_journal_entries(3, &policy(), &receipts, &entries)
            .expect("the household rows extract");
        assert_eq!(extracted.records.len(), 1);
        assert_eq!(
            extracted.records[0].subject.as_ref().map(|row| row.kind),
            Some(SubjectKind::Player)
        );
        assert_eq!(extracted.summaries[33].family, 34);
        assert_eq!(extracted.summaries[33].rows, 2);
        let mut changed = receipts.clone();
        changed.household_time[1].attended_hours = 1;
        changed.household_time[1].contribution_available_hours = 7;
        let altered = extract_permanent_journal_entries(3, &policy(), &changed, &entries)
            .expect("the changed household rows extract");
        assert_ne!(
            altered.summaries[33].content_hash,
            extracted.summaries[33].content_hash
        );
        assert_ne!(altered.content_hash, extracted.content_hash);
    }

    #[test]
    fn mismatched_or_missing_period_is_refused() {
        let entries = OrganizerPeriodJournalEntries::new(2);
        assert!(matches!(
            extract_permanent_journal_entries(3, &policy(), &empty_receipts(3), &entries),
            Err(SaveError::InvalidField {
                field: "period",
                ..
            })
        ));
        assert!(matches!(
            extract_permanent_journal_entries(3, &policy(), &empty_receipts(4), &entries),
            Err(SaveError::InvalidField {
                field: "period",
                ..
            })
        ));
        assert!(matches!(
            extract_permanent_journal_entries(0, &policy(), &empty_receipts(0), &entries),
            Err(SaveError::InvalidField {
                field: "period",
                ..
            })
        ));
    }

    #[test]
    fn record_ceiling_refuses_rather_than_truncating() {
        let mut entries = OrganizerPeriodJournalEntries::new(3);
        let mut first = observation(3);
        first.observation_id = [1; 32];
        let mut second = observation(3);
        second.observation_id = [2; 32];
        entries.observations.push(first);
        entries.observations.push(second);
        let mut limited = policy();
        limited.max_records = 1;
        assert!(matches!(
            extract_permanent_journal_entries(3, &limited, &empty_receipts(3), &entries),
            Err(SaveError::PayloadTooLarge {
                table: "permanent_journal",
                limit: 1,
                actual: 2
            })
        ));
    }
}
