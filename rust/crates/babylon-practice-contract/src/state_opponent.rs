//! Captured, private City PD decisions and resolution evidence.
use std::fmt::{Display, Formatter, Result as FormatResult};

use babylon_kernel::geography::CountyGeoid;

use crate::state_opponent_codec;
use serde::{Deserialize, Serialize};

/// Current wire schema.
pub const CITY_PD_SCHEMA_VERSION: u32 = 1;
/// Maximum retained case or acquired-fact count.
pub const CITY_PD_MAX_ROWS: usize = 4096;
/// Largest exactly rankable Capacity price.
pub const CITY_PD_MAX_COST: i128 = 1_i128 << 53;

/// A malformed or noncanonical City PD contract.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CityPdError {
    UnsupportedSchema,
    InvalidId,
    InvalidCounty,
    InvalidPrice,
    Arithmetic,
    InvalidProvenance,
    InvalidTiming,
    InvalidReceipt,
    InvalidIdentity,
    SizeLimit,
    Codec,
    NonCanonical,
    WrongOwner,
    CountyMismatch,
    UnknownSubject,
    DuplicateCase,
    NegativeBalance,
    Capacity,
}
impl Display for CityPdError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "City PD contract: {self:?}")
    }
}
impl std::error::Error for CityPdError {}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CityPdConfig {
    pub schema_version: u32,
    pub campaign_id: [u8; 16],
    pub actor_id: u64,
    pub authority_id: [u8; 16],
    pub county: [u8; 5],
    pub public_account_id: [u8; 32],
    pub agency_account_id: [u8; 32],
    pub investigator_household_account_id: [u8; 32],
    pub investigator_entitlement_id: [u8; 32],
    pub labor_unit_id: [u8; 32],
    pub visit_hours: u64,
    #[serde(with = "super::state_opponent_decimal")]
    pub hourly_wage_micros: i128,
    #[serde(with = "super::state_opponent_decimal")]
    pub visit_cost_micros: i128,
    #[serde(with = "super::state_opponent_decimal")]
    pub appropriation_micros: i128,
    pub appropriation_priority: u32,
    pub content_digest: [u8; 32],
    pub policy_source_digest: [u8; 32],
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CityPdCaseSource {
    CapturedPublicRecord,
    ObservedOrganizerReceipt,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CityPdCaseStatus {
    Open,
    Closed,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CityPdCase {
    pub case_id: [u8; 32],
    pub actor_id: u64,
    pub subject_id: u64,
    pub county: [u8; 5],
    pub public_venue_id: [u8; 32],
    pub source_id: [u8; 32],
    pub source_kind: CityPdCaseSource,
    pub source_receipt_id: Option<[u8; 32]>,
    pub case_source_witness_id: Option<[u8; 32]>,
    pub observed_period: u64,
    pub acquired_period: u64,
    pub status: CityPdCaseStatus,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CityPdIntent {
    pub intent_id: [u8; 32],
    pub schema_version: u32,
    pub campaign_id: [u8; 16],
    pub actor_id: u64,
    pub authority_id: [u8; 16],
    pub config_digest: [u8; 32],
    pub decision_basis_digest: [u8; 32],
    pub case_id: [u8; 32],
    pub subject_id: u64,
    pub source_period: u64,
    pub resolve_period: u64,
    #[serde(with = "super::state_opponent_decimal")]
    pub cost_micros: i128,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum CityPdDecision {
    NoCases,
    NoFunds {
        #[serde(with = "super::state_opponent_decimal")]
        available_micros: i128,
        #[serde(with = "super::state_opponent_decimal")]
        required_micros: i128,
    },
    Selected(CityPdIntent),
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CityPdDecisionReceipt {
    pub decision_id: [u8; 32],
    pub campaign_id: [u8; 16],
    pub actor_id: u64,
    pub period: u64,
    pub decision_basis_digest: [u8; 32],
    pub decision: CityPdDecision,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CityPdOutcome {
    Completed,
    InsufficientFunds,
    InsufficientTime,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CityPdReceipt {
    pub receipt_id: [u8; 32],
    pub campaign_id: [u8; 16],
    pub actor_id: u64,
    pub case_id: [u8; 32],
    pub intent_id: [u8; 32],
    pub resolve_period: u64,
    pub outcome: CityPdOutcome,
    pub attendance_hours: u64,
    #[serde(with = "super::state_opponent_decimal")]
    pub wage_micros: i128,
    pub shift_receipt_id: Option<[u8; 32]>,
    pub payment_receipt_id: Option<[u8; 32]>,
    pub acquired_public_fact_ids: Vec<[u8; 32]>,
    pub case_source_evidence_id: Option<[u8; 32]>,
    pub player_witness_evidence_id: Option<[u8; 32]>,
}

/// Check captured arithmetic, identity, and county syntax.
///
/// # Errors
/// Returns the specific contract error for an invalid field, identity, or bound.
pub fn validate_city_pd_config(c: &CityPdConfig) -> Result<(), CityPdError> {
    if c.schema_version != CITY_PD_SCHEMA_VERSION {
        return Err(CityPdError::UnsupportedSchema);
    }
    if c.campaign_id == [0; 16]
        || c.actor_id == 0
        || c.authority_id == [0; 16]
        || [
            c.public_account_id,
            c.agency_account_id,
            c.investigator_household_account_id,
            c.investigator_entitlement_id,
            c.labor_unit_id,
            c.content_digest,
            c.policy_source_digest,
        ]
        .contains(&[0; 32])
    {
        return Err(CityPdError::InvalidId);
    }
    county(c.county)?;
    if c.visit_hours == 0
        || c.hourly_wage_micros <= 0
        || c.visit_cost_micros <= 0
        || c.appropriation_micros <= 0
        || c.visit_cost_micros > CITY_PD_MAX_COST
    {
        return Err(CityPdError::InvalidPrice);
    }
    if i128::from(c.visit_hours)
        .checked_mul(c.hourly_wage_micros)
        .ok_or(CityPdError::Arithmetic)?
        != c.visit_cost_micros
    {
        return Err(CityPdError::InvalidPrice);
    }
    Ok(())
}
fn county(value: [u8; 5]) -> Result<(), CityPdError> {
    CountyGeoid::try_from(value)
        .map(|_| ())
        .map_err(|_| CityPdError::InvalidCounty)
}
fn optional_id(id: Option<[u8; 32]>) -> bool {
    id.is_none_or(|v| v != [0; 32])
}
/// Validate a case's identity and intrinsic source shape; caller checks the decision period.
///
/// # Errors
/// Returns the specific contract error for an invalid field, identity, or bound.
pub fn validate_city_pd_case(c: &CityPdCase) -> Result<(), CityPdError> {
    if c.actor_id == 0
        || c.subject_id == 0
        || c.case_id == [0; 32]
        || c.public_venue_id == [0; 32]
        || c.source_id == [0; 32]
        || !optional_id(c.source_receipt_id)
        || !optional_id(c.case_source_witness_id)
    {
        return Err(CityPdError::InvalidId);
    }
    county(c.county)?;
    match c.source_kind {
        CityPdCaseSource::CapturedPublicRecord
            if c.source_receipt_id.is_none() && c.case_source_witness_id.is_none() => {}
        CityPdCaseSource::ObservedOrganizerReceipt
            if c.source_receipt_id.is_some() && c.case_source_witness_id.is_some() => {}
        _ => return Err(CityPdError::InvalidProvenance),
    }
    if c.observed_period > c.acquired_period {
        return Err(CityPdError::InvalidTiming);
    }
    if state_opponent_codec::city_pd_case_id(c)? != c.case_id {
        return Err(CityPdError::InvalidIdentity);
    }
    Ok(())
}
/// Validate the intent's intrinsic shape and identity.
///
/// # Errors
/// Returns the specific contract error for an invalid field, identity, or bound.
pub fn validate_city_pd_intent(i: &CityPdIntent) -> Result<(), CityPdError> {
    if i.schema_version != CITY_PD_SCHEMA_VERSION {
        return Err(CityPdError::UnsupportedSchema);
    }
    if i.intent_id == [0; 32]
        || i.campaign_id == [0; 16]
        || i.actor_id == 0
        || i.authority_id == [0; 16]
        || i.config_digest == [0; 32]
        || i.decision_basis_digest == [0; 32]
        || i.case_id == [0; 32]
        || i.subject_id == 0
    {
        return Err(CityPdError::InvalidId);
    }
    if i.cost_micros <= 0 || i.cost_micros > CITY_PD_MAX_COST {
        return Err(CityPdError::InvalidPrice);
    }
    if i.source_period
        .checked_add(1)
        .ok_or(CityPdError::Arithmetic)?
        != i.resolve_period
    {
        return Err(CityPdError::InvalidTiming);
    }
    if state_opponent_codec::city_pd_intent_id(i)? != i.intent_id {
        return Err(CityPdError::InvalidIdentity);
    }
    Ok(())
}
/// Validate the decision and its embedded intent binding.
///
/// # Errors
/// Returns the specific contract error for an invalid field, identity, or bound.
pub fn validate_city_pd_decision(d: &CityPdDecisionReceipt) -> Result<(), CityPdError> {
    if d.decision_id == [0; 32]
        || d.campaign_id == [0; 16]
        || d.actor_id == 0
        || d.decision_basis_digest == [0; 32]
    {
        return Err(CityPdError::InvalidId);
    }
    match &d.decision {
        CityPdDecision::NoCases => (),
        CityPdDecision::NoFunds {
            available_micros,
            required_micros,
        } if *available_micros >= 0
            && *required_micros > 0
            && *required_micros <= CITY_PD_MAX_COST
            && available_micros < required_micros => {}
        CityPdDecision::NoFunds { .. } => return Err(CityPdError::InvalidPrice),
        CityPdDecision::Selected(intent) => {
            validate_city_pd_intent(intent)?;
            if intent.campaign_id != d.campaign_id
                || intent.actor_id != d.actor_id
                || intent.source_period != d.period
                || intent.decision_basis_digest != d.decision_basis_digest
            {
                return Err(CityPdError::InvalidIdentity);
            }
        }
    }
    if state_opponent_codec::city_pd_decision_id(d)? != d.decision_id {
        return Err(CityPdError::InvalidIdentity);
    }
    Ok(())
}
/// Validate resolution shape only; no underlying posting or witness is authenticated.
///
/// # Errors
/// Returns the specific contract error for an invalid field, identity, or bound.
pub fn validate_city_pd_receipt(r: &CityPdReceipt) -> Result<(), CityPdError> {
    if r.receipt_id == [0; 32]
        || r.campaign_id == [0; 16]
        || r.actor_id == 0
        || r.case_id == [0; 32]
        || r.intent_id == [0; 32]
        || !optional_id(r.shift_receipt_id)
        || !optional_id(r.payment_receipt_id)
        || !optional_id(r.case_source_evidence_id)
        || !optional_id(r.player_witness_evidence_id)
    {
        return Err(CityPdError::InvalidId);
    }
    if r.acquired_public_fact_ids.len() > CITY_PD_MAX_ROWS {
        return Err(CityPdError::SizeLimit);
    }
    if r.acquired_public_fact_ids.contains(&[0; 32])
        || !r.acquired_public_fact_ids.windows(2).all(|v| v[0] < v[1])
    {
        return Err(CityPdError::InvalidReceipt);
    }
    match r.outcome {
        CityPdOutcome::Completed if r.attendance_hours > 0 && r.wage_micros > 0 => (),
        CityPdOutcome::InsufficientFunds | CityPdOutcome::InsufficientTime
            if r.attendance_hours == 0
                && r.wage_micros == 0
                && r.acquired_public_fact_ids.is_empty()
                && r.player_witness_evidence_id.is_none()
                && r.payment_receipt_id.is_none() => {}
        _ => return Err(CityPdError::InvalidReceipt),
    }
    if state_opponent_codec::city_pd_receipt_id(r)? != r.receipt_id {
        return Err(CityPdError::InvalidIdentity);
    }
    Ok(())
}

/// Canonicalize a draft's facts and derive its identity before publication.
/// This validates wire shape, but does not authenticate the underlying evidence.
///
/// # Errors
/// Returns the specific contract error for an invalid field, identity, or bound.
pub fn finalize_city_pd_receipt(mut receipt: CityPdReceipt) -> Result<CityPdReceipt, CityPdError> {
    if receipt.acquired_public_fact_ids.len() > CITY_PD_MAX_ROWS {
        return Err(CityPdError::SizeLimit);
    }
    receipt.acquired_public_fact_ids.sort_unstable();
    receipt.acquired_public_fact_ids.dedup();
    receipt.receipt_id = state_opponent_codec::city_pd_receipt_id(&receipt)?;
    validate_city_pd_receipt(&receipt)?;
    Ok(receipt)
}
