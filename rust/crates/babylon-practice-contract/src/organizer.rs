//! Bounded, captured organizer practices and period-specific earned knowledge.
//!
//! This module is a pure transition. Durable admission and atomic publication
//! belong to the runtime. No practice changes factory production or staffing.

use serde::{Deserialize, Serialize};

mod contract;
mod transition;
pub use contract::*;
pub use transition::*;

/// Current organizer representation. Older representations are unsupported.
pub const ORGANIZER_SCHEMA_VERSION: u16 = 1;

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

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerState {
    pub schema_version: u16,
    pub period: u64,
    pub standing: OrganizerStandingWork,
    pub agreements: Vec<OrganizerAgreement>,
    pub observations: Vec<OrganizerObservation>,
    pub receipts: Vec<OrganizerReceipt>,
    pub contact_products: Vec<OrganizerContactProduct>,
    pub consumed_product_ids: Vec<[u8; 32]>,
    pub last_workplace_facts: Option<OrganizerWorkplaceFacts>,
}

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
    pub observations: Vec<OrganizerObservation>,
    pub receipts: Vec<OrganizerReceipt>,
    pub positions: Vec<OrganizerPosition>,
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
    Arithmetic,
    PeriodMismatch,
    Refused(OrganizerRefusal),
    ResourceAllocation,
    Codec,
    NonCanonical,
    SizeLimit,
}

impl std::fmt::Display for OrganizerError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "organizer contract: {self:?}")
    }
}

impl std::error::Error for OrganizerError {}
