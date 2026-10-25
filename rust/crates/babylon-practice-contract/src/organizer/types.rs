//! Leaf implementation for the parent module; public paths stay on the parent.

use super::{
    OrganizerAidBinding, OrganizerAidOption, OrganizerAidResolutionReceipt, OrganizerAidSupport,
    OrganizerCollectionFact, OrganizerCollectionMandate, OrganizerCollectionResolution,
    OrganizerPendingAidPractice,
};

use super::collection;

use serde::{Deserialize, Serialize};
use std::fmt::Formatter;
use std::fmt::Result as FmtResult;

/// Current organizer representation. Older representations are unsupported.
pub const ORGANIZER_SCHEMA_VERSION: u16 = 8;

/// Whole organizer-hours are Designed participant time commitments, not jobs.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerContribution {
    pub actor_id: u64,
    pub hours: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerParticipant {
    pub contributor_id: u64,
    pub label: String,
    pub available_hours: u64,
    pub commitments: Vec<OrganizerContribution>,
    pub concern: String,
    pub objection: String,
    pub review_condition: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrganizerPartnerPolicy {
    Participate,
    Refuse,
    NoResponse,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerPartner {
    pub actor_id: u64,
    pub authority_id: [u8; 16],
    pub label: String,
    pub policy: OrganizerPartnerPolicy,
    pub permits_work_report: bool,
    pub permits_maintenance_report: bool,
}

/// Captured identity only; the material host validates household existence and units.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerHouseholdBinding {
    pub contributor_id: u64,
    pub principal_id: [u8; 32],
}

/// Required captured source of time; no implicit fixed supply for household work.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case", deny_unknown_fields)]
pub enum OrganizerTimeBindingMode {
    FixedTimeControl,
    Household {
        bindings: Vec<OrganizerHouseholdBinding>,
    },
}

/// Captured scenario content. All quantities and political actors are Designed.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerConfig {
    pub schema_version: u16,
    pub campaign_id: [u8; 16],
    pub controlled_actor_id: u64,
    pub input_authority_id: [u8; 16],
    pub organization_label: String,
    pub workplace_id: u64,
    pub workplace_process_id: [u8; 32],
    pub workplace_label: String,
    pub workplace_partner: OrganizerPartner,
    pub neighborhood_partner: OrganizerPartner,
    pub participants: Vec<OrganizerParticipant>,
    pub time_binding: OrganizerTimeBindingMode,
    #[serde(deserialize_with = "collection::required_terms")]
    pub collection: Option<OrganizerCollectionMandate>,
    pub aid_bindings: Vec<OrganizerAidBinding>,
    pub inquiry_hours: u64,
    pub contact_hours: u64,
    pub partner_response_hours: u64,
    pub initial_agreement_through_period: u64,
    pub contact_renewal_periods: u64,
    pub content_digest: [u8; 32],
    pub initial_observations: Vec<OrganizerObservation>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrganizerInquiry {
    WorkLost,
    MaintenanceReceived,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrganizerChoice {
    Inquiry(OrganizerInquiry),
    Collect,
    LocalAid,
    RemoteAid,
    Reinforce,
    Hold,
    PauseStanding,
    ResumeStanding,
}

/// A command binds a ruling to the exact current campaign and contracts.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerCommand {
    pub campaign_id: [u8; 16],
    pub actor_id: u64,
    pub authority_id: [u8; 16],
    pub expected_period: u64,
    pub content_digest: [u8; 32],
    pub resource_digest: [u8; 32],
    pub nonce: [u8; 16],
    pub choice: OrganizerChoice,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerCommitment {
    pub command: OrganizerCommand,
    pub resolves_period: u64,
    pub commitment_id: [u8; 32],
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrganizerRefusal {
    WrongCampaign,
    WrongAuthority,
    StalePeriod,
    ContentChanged,
    ResourceContractChanged,
    InsufficientCommittedTime,
    StandingWorkPaused,
    StandingWorkAlreadyActive,
    InvalidCommand,
    CollectionUnavailable,
    CollectionCashRefused,
    AidUnavailable,
    AidReceivingRefused,
    PendingAidConflict,
    /// This household hour identity was already debited in the witnessed period.
    HouseholdTimeAlreadySpent,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerPreview {
    pub choice: OrganizerChoice,
    pub current_period: u64,
    pub resolves_period: u64,
    pub available_hours: u64,
    pub required_hours: u64,
    pub replaces_standing_work: bool,
    pub refusal: Option<OrganizerRefusal>,
    pub observations: Vec<OrganizerObservation>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrganizerPauseReason {
    Explicit,
    InsufficientCommittedTime,
    InsufficientAvailableTime,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerStandingWork {
    pub partner_actor_id: u64,
    pub authorized: bool,
    pub paused_reason: Option<OrganizerPauseReason>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerAgreement {
    pub actor_id: u64,
    pub partner_actor_id: u64,
    pub valid_from_period: u64,
    pub valid_through_period: u64,
    pub source_product_id: Option<[u8; 32]>,
}

/// The entire permitted workplace record surface. No provider-private fields.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerWorkplaceFacts {
    pub period: u64,
    pub workplace_id: u64,
    pub performed_labor_hours: u64,
    pub output_kg: u64,
    pub maintenance_enabled_batches: u64,
    pub maintenance_consumed_batches: u64,
    pub maintenance_expired_batches: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum OrganizerReport {
    ReducedWork {
        previous_labor_hours: u64,
        performed_labor_hours: u64,
    },
    Work {
        performed_labor_hours: u64,
        output_kg: u64,
        previous_labor_hours: Option<u64>,
        previous_output_kg: Option<u64>,
    },
    Maintenance {
        enabled_batches: u64,
        consumed_batches: u64,
        expired_batches: u64,
    },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerObservation {
    pub observation_id: [u8; 32],
    pub actor_id: u64,
    pub subject_id: u64,
    pub source_actor_id: u64,
    pub observed_period: u64,
    pub acquired_period: u64,
    pub receipt_id: Option<[u8; 32]>,
    pub report: OrganizerReport,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrganizerPartnerResponse {
    Participated,
    Refused,
    NoResponse,
    UnableToParticipate,
    NotRequested,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrganizerOutcome {
    EvidenceObtained,
    EvidenceWithheld,
    ContactCompleted,
    ContactUncompleted,
    CollectionCompleted,
    CollectionRefused,
    AidScheduled,
    AidAwaitingSupport,
    AidNotProvisioned,
    AidPracticeCompleted,
    AidPracticeUncompleted,
    InsufficientTime,
    StandingPaused,
    StandingResumed,
    NoAuthorizedPractice,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerContactProduct {
    pub product_id: [u8; 32],
    pub receipt_id: [u8; 32],
    pub actor_id: u64,
    pub partner_actor_id: u64,
    pub produced_period: u64,
}

/// Compact current learned-authority index, one row per subject/source/report.
///
/// Exact observations remain in the permanent journal; this row keeps only the
/// causal value a later inquiry needs without retaining the observation vector.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerLearnedAuthority {
    pub observation_id: [u8; 32],
    pub receipt_id: Option<[u8; 32]>,
    pub subject_id: u64,
    pub source_actor_id: u64,
    pub observed_period: u64,
    pub acquired_period: u64,
    pub report: OrganizerReport,
}

impl OrganizerLearnedAuthority {
    /// Rebuild the exact observation this compact row stands for.
    #[must_use]
    pub fn observation(&self, actor_id: u64) -> OrganizerObservation {
        OrganizerObservation {
            observation_id: self.observation_id,
            actor_id,
            subject_id: self.subject_id,
            source_actor_id: self.source_actor_id,
            observed_period: self.observed_period,
            acquired_period: self.acquired_period,
            receipt_id: self.receipt_id,
            report: self.report.clone(),
        }
    }

    /// Stable report kind, used to deduplicate the current index.
    #[must_use]
    pub const fn report_kind(&self) -> u8 {
        match self.report {
            OrganizerReport::Work { .. } => 0,
            OrganizerReport::ReducedWork { .. } => 1,
            OrganizerReport::Maintenance { .. } => 2,
        }
    }
}

/// Exact household-hour debit witness for the last resolved period.
///
/// The contribution-use identities are the same identities the material time
/// book charges, so a replay that would spend an already-committed household
/// hour can be refused even after the original receipts leave live state.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerPeriodTimeWitness {
    pub period: u64,
    pub contribution_use_ids: Vec<[u8; 32]>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerTimeUse {
    pub contributor_id: u64,
    pub actor_id: u64,
    pub hours: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerReceipt {
    pub receipt_id: [u8; 32],
    pub commitment_id: Option<[u8; 32]>,
    pub actor_id: u64,
    pub period: u64,
    pub choice: OrganizerChoice,
    pub standing_work: bool,
    pub outcome: OrganizerOutcome,
    pub hours_spent: u64,
    pub partner_actor_id: Option<u64>,
    pub partner_response: OrganizerPartnerResponse,
    pub observation_ids: Vec<[u8; 32]>,
    pub contact_product_id: Option<[u8; 32]>,
    pub time_use: Vec<OrganizerTimeUse>,
}

/// Causal current authority. Historical evidence lives in the period journal.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerState {
    pub schema_version: u16,
    pub period: u64,
    pub standing: OrganizerStandingWork,
    pub agreements: Vec<OrganizerAgreement>,
    pub pending_aid: Vec<OrganizerPendingAidPractice>,
    pub contact_products: Vec<OrganizerContactProduct>,
    /// Durable compact anti-double-spend tombstones; creations may be gone.
    pub consumed_product_ids: Vec<[u8; 32]>,
    pub last_workplace_facts: Option<OrganizerWorkplaceFacts>,
    pub learned_authority_index: Vec<OrganizerLearnedAuthority>,
    pub last_period_time_witness: Option<OrganizerPeriodTimeWitness>,
}

/// Exact evidence produced by one resolved organizer period.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerPeriodJournalEntries {
    pub period: u64,
    pub observations: Vec<OrganizerObservation>,
    pub receipts: Vec<OrganizerReceipt>,
    pub collection_receipts: Vec<OrganizerCollectionResolution>,
    pub aid_receipts: Vec<OrganizerAidResolutionReceipt>,
}

impl OrganizerPeriodJournalEntries {
    /// Empty evidence for the supplied period.
    #[must_use]
    pub const fn new(period: u64) -> Self {
        Self {
            period,
            observations: vec![],
            receipts: vec![],
            collection_receipts: vec![],
            aid_receipts: vec![],
        }
    }

    /// Ordinary and aid-resolution receipts in production order.
    pub fn receipts(&self) -> impl Iterator<Item = &OrganizerReceipt> {
        self.receipts
            .iter()
            .chain(self.aid_receipts.iter().map(|row| &row.practice))
    }

    /// Whether this period's evidence is empty.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.observations.is_empty()
            && self.receipts.is_empty()
            && self.collection_receipts.is_empty()
            && self.aid_receipts.is_empty()
    }

    /// Merge two evidence sets for the same period in causal execution order.
    ///
    /// # Errors
    ///
    /// Returns [`OrganizerError::PeriodMismatch`] when the periods differ.
    pub fn extend(&mut self, other: Self) -> Result<(), OrganizerError> {
        if self.period != other.period {
            return Err(OrganizerError::PeriodMismatch);
        }
        self.observations.extend(other.observations);
        self.receipts.extend(other.receipts);
        self.collection_receipts.extend(other.collection_receipts);
        self.aid_receipts.extend(other.aid_receipts);
        Ok(())
    }
}

/// Retained organizer evidence ordered by strictly increasing period.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerPeriodJournal {
    pub periods: Vec<OrganizerPeriodJournalEntries>,
}

impl OrganizerPeriodJournal {
    /// Empty journal window.
    #[must_use]
    pub const fn empty() -> Self {
        Self { periods: vec![] }
    }

    /// Append one resolved period, refusing to rewrite an existing period.
    ///
    /// # Errors
    ///
    /// Returns [`OrganizerError::PeriodMismatch`] when the new period does not
    /// extend the strictly increasing retained sequence.
    pub fn append(&mut self, entries: OrganizerPeriodJournalEntries) -> Result<(), OrganizerError> {
        if self
            .periods
            .last()
            .is_some_and(|row| row.period >= entries.period)
        {
            return Err(OrganizerError::PeriodMismatch);
        }
        self.periods.push(entries);
        Ok(())
    }

    /// Latest retained period evidence.
    #[must_use]
    pub fn latest(&self) -> Option<&OrganizerPeriodJournalEntries> {
        self.periods.last()
    }
}

/// One resolved organizer period: compact causal authority plus exact evidence.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ResolvedOrganizerPeriod {
    pub state: OrganizerState,
    pub journal: OrganizerPeriodJournalEntries,
}

impl std::ops::Deref for ResolvedOrganizerPeriod {
    type Target = OrganizerState;

    fn deref(&self) -> &OrganizerState {
        &self.state
    }
}

/// Designed presentation bounds; canonical organizer history remains complete.
pub const ORGANIZER_RECENT_RECEIPTS: usize = 8;

pub const ORGANIZER_RECENT_OBSERVATIONS: usize = 8;

/// The runtime/client response surface deliberately omits hidden input state.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerView {
    pub period: u64,
    pub actor_id: u64,
    pub authority_id: [u8; 16],
    pub organization_label: String,
    pub workplace_id: u64,
    pub workplace_label: String,
    pub workplace_partner_id: u64,
    pub workplace_partner_label: String,
    pub neighborhood_partner_id: u64,
    pub neighborhood_partner_label: String,
    pub available_hours: u64,
    pub inquiry_hours: u64,
    pub contact_hours: u64,
    pub content_digest: [u8; 32],
    pub resource_digest: [u8; 32],
    pub standing: OrganizerStandingWork,
    pub agreements: Vec<OrganizerAgreement>,
    /// Derived count of all actor observations in the canonical register.
    pub total_observation_count: u32,
    pub observations: Vec<OrganizerObservation>,
    /// Derived count of all actor ordinary receipts in the canonical register.
    pub total_receipt_count: u32,
    pub receipts: Vec<OrganizerReceipt>,
    pub positions: Vec<OrganizerPosition>,
    pub aid_options: Vec<OrganizerAidOption>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerPosition {
    pub contributor_id: u64,
    pub label: String,
    pub promised_hours: u64,
    pub concern: String,
    pub objection: String,
    pub review_condition: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrganizerError {
    UnsupportedSchema,
    InvalidConfig,
    InvalidState,
    InvalidCommitment,
    CollectionSupportMissing,
    CollectionSupportMismatch,
    AidSupportMissing,
    AidSupportMismatch,
    Arithmetic,
    PeriodMismatch,
    Refused(OrganizerRefusal),
    ResourceAllocation,
    TimeBindingMismatch,
    TimeCapacityMissing,
    TimeCapacityDuplicate,
    TimeCapacityScope,
    TimeUnitMismatch,
    TimePeriodMismatch,
    Codec,
    NonCanonical,
    SizeLimit,
}

impl std::fmt::Display for OrganizerError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> FmtResult {
        write!(formatter, "organizer contract: {self:?}")
    }
}

impl std::error::Error for OrganizerError {}

/// Borrowed material evidence for this exact resolving period.
/// Collection is an original acknowledgment, not another time allocator.
#[derive(Debug, Clone, Copy)]
pub struct OrganizerMaterialSupport<'a> {
    pub aid: &'a [OrganizerAidSupport],
    pub collection: Option<&'a OrganizerCollectionFact>,
}
