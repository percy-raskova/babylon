//! Captured public workplace-contact desk terms and bounded publications.
//!
//! These wire contracts validate identity and syntax, not whether an occurrence
//! happened. The tick host must authenticate occurrence-specific material proof.
use babylon_kernel::content_digest;
use serde::{Deserialize, Serialize};
use std::fmt::{Display, Formatter, Result as FmtResult};

/// Current canonical public venue representation; older forms are unsupported.
pub const PUBLIC_VENUE_SCHEMA_VERSION: u32 = 1;
/// Maximum bytes accepted for a single canonical record or policy.
pub const PUBLIC_VENUE_MAX_BYTES: usize = 8192;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PublicVenueError {
    InvalidId,
    UnsupportedSchema,
    InvalidIdentity,
    InvalidRecord,
    SizeLimit,
    Codec,
    NonCanonical,
}
impl Display for PublicVenueError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        write!(f, "public venue: {self:?}")
    }
}
impl std::error::Error for PublicVenueError {}

fn identity<T: Serialize>(domain: &[u8], value: &T) -> Result<[u8; 32], PublicVenueError> {
    let bytes = serde_json::to_vec(value).map_err(|_| PublicVenueError::Codec)?;
    if bytes.len() > PUBLIC_VENUE_MAX_BYTES {
        return Err(PublicVenueError::SizeLimit);
    }
    let mut input = domain.to_vec();
    input.push(0);
    input.extend_from_slice(&bytes);
    Ok(content_digest::sha256_of(&input))
}

/// Designed venue, publisher, disclosed readers and source terms captured at start.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PublicVenuePolicy {
    pub schema_version: u32,
    pub campaign_id: [u8; 16],
    pub workplace_id: u64,
    pub controlled_actor_id: u64,
    pub committee_actor_id: u64,
    pub committee_authority_id: [u8; 16],
    pub agency_reader_actor_id: u64,
    pub player_reader_actor_id: u64,
    pub organizer_content_digest: [u8; 32],
    pub source_terms_digest: [u8; 32],
    pub venue_id: [u8; 32],
    pub policy_id: [u8; 32],
}
impl PublicVenuePolicy {
    /// Capture the authored desk and explicit publication and reader terms.
    ///
    /// # Errors
    /// Refuses zero identities and unrepresentable terms.
    #[allow(
        clippy::too_many_arguments,
        reason = "each captured authority is explicit"
    )]
    pub fn new(
        campaign_id: [u8; 16],
        workplace_id: u64,
        controlled_actor_id: u64,
        committee_actor_id: u64,
        committee_authority_id: [u8; 16],
        agency_reader_actor_id: u64,
        player_reader_actor_id: u64,
        organizer_content_digest: [u8; 32],
        source_terms_digest: [u8; 32],
    ) -> Result<Self, PublicVenueError> {
        let mut policy = Self {
            schema_version: PUBLIC_VENUE_SCHEMA_VERSION,
            campaign_id,
            workplace_id,
            controlled_actor_id,
            committee_actor_id,
            committee_authority_id,
            agency_reader_actor_id,
            player_reader_actor_id,
            organizer_content_digest,
            source_terms_digest,
            venue_id: [0; 32],
            policy_id: [0; 32],
        };
        policy.validate_terms()?;
        policy.venue_id = identity(b"babylon.public-venue.venue.v1", &policy)?;
        policy.policy_id = identity(b"babylon.public-venue.policy.v1", &policy)?;
        Ok(policy)
    }
    fn validate_terms(&self) -> Result<(), PublicVenueError> {
        if self.schema_version != PUBLIC_VENUE_SCHEMA_VERSION {
            return Err(PublicVenueError::UnsupportedSchema);
        }
        if self.campaign_id == [0; 16]
            || self.workplace_id == 0
            || self.controlled_actor_id == 0
            || self.committee_actor_id == 0
            || self.committee_authority_id == [0; 16]
            || self.agency_reader_actor_id == 0
            || self.player_reader_actor_id == 0
            || self.organizer_content_digest == [0; 32]
            || self.source_terms_digest == [0; 32]
        {
            return Err(PublicVenueError::InvalidId);
        }
        Ok(())
    }
    /// Verify that identities are exactly those of the captured terms.
    ///
    /// # Errors
    /// Refuses malformed or modified policy.
    pub fn validate(&self) -> Result<(), PublicVenueError> {
        self.validate_terms()?;
        let expected = Self::new(
            self.campaign_id,
            self.workplace_id,
            self.controlled_actor_id,
            self.committee_actor_id,
            self.committee_authority_id,
            self.agency_reader_actor_id,
            self.player_reader_actor_id,
            self.organizer_content_digest,
            self.source_terms_digest,
        )?;
        if *self != expected {
            return Err(PublicVenueError::InvalidIdentity);
        }
        Ok(())
    }
}

/// Publicly disclosable event kind. Source identifiers do not authenticate proof.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum PublicVenueRecordKind {
    /// Designed opening notice of the desk, not a performed contact.
    AuthoredInitialNotice,
    /// Minimal contact publication; private time and command content stay outside.
    ContactCompleted {
        organizer_receipt_id: [u8; 32],
        contact_product_id: [u8; 32],
    },
    /// Public check-in publication for an independently authenticated paid visit.
    PaidVisit { visit_core_id: [u8; 32] },
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PublicVenueRecord {
    pub schema_version: u32,
    pub campaign_id: [u8; 16],
    pub venue_id: [u8; 32],
    pub policy_id: [u8; 32],
    pub workplace_id: u64,
    pub controlled_actor_id: u64,
    pub publisher_actor_id: u64,
    pub publisher_authority_id: [u8; 16],
    pub agency_reader_actor_id: u64,
    pub player_reader_actor_id: u64,
    pub period: u64,
    pub source_id: [u8; 32],
    pub kind: PublicVenueRecordKind,
}
impl PublicVenueRecord {
    /// Form a candidate public record; occurrence proof is checked separately.
    ///
    /// # Errors
    /// Refuses malformed policy or publication fields.
    pub fn from_policy(
        policy: &PublicVenuePolicy,
        period: u64,
        kind: PublicVenueRecordKind,
    ) -> Result<Self, PublicVenueError> {
        policy.validate()?;
        let mut record = Self {
            schema_version: PUBLIC_VENUE_SCHEMA_VERSION,
            campaign_id: policy.campaign_id,
            venue_id: policy.venue_id,
            policy_id: policy.policy_id,
            workplace_id: policy.workplace_id,
            controlled_actor_id: policy.controlled_actor_id,
            publisher_actor_id: policy.committee_actor_id,
            publisher_authority_id: policy.committee_authority_id,
            agency_reader_actor_id: policy.agency_reader_actor_id,
            player_reader_actor_id: policy.player_reader_actor_id,
            period,
            source_id: [0; 32],
            kind,
        };
        record.validate_shape()?;
        record.source_id = identity(b"babylon.public-venue.record.v1", &record)?;
        Ok(record)
    }
    fn validate_shape(&self) -> Result<(), PublicVenueError> {
        if self.schema_version != PUBLIC_VENUE_SCHEMA_VERSION {
            return Err(PublicVenueError::UnsupportedSchema);
        }
        if self.campaign_id == [0; 16]
            || self.venue_id == [0; 32]
            || self.policy_id == [0; 32]
            || self.workplace_id == 0
            || self.controlled_actor_id == 0
            || self.publisher_actor_id == 0
            || self.publisher_authority_id == [0; 16]
            || self.agency_reader_actor_id == 0
            || self.player_reader_actor_id == 0
        {
            return Err(PublicVenueError::InvalidId);
        }
        match &self.kind {
            PublicVenueRecordKind::AuthoredInitialNotice if self.period == 0 => Ok(()),
            PublicVenueRecordKind::ContactCompleted {
                organizer_receipt_id,
                contact_product_id,
            } if self.period > 0
                && *organizer_receipt_id != [0; 32]
                && *contact_product_id != [0; 32] =>
            {
                Ok(())
            }
            PublicVenueRecordKind::PaidVisit { visit_core_id }
                if self.period > 0 && *visit_core_id != [0; 32] =>
            {
                Ok(())
            }
            _ => Err(PublicVenueError::InvalidRecord),
        }
    }
    /// Validate exact policy binding and record identity; not occurrence proof.
    ///
    /// # Errors
    /// Refuses altered, foreign, or invalid records.
    pub fn validate(&self, policy: &PublicVenuePolicy) -> Result<(), PublicVenueError> {
        let expected = Self::from_policy(policy, self.period, self.kind.clone())?;
        if *self != expected {
            return Err(PublicVenueError::InvalidIdentity);
        }
        Ok(())
    }
}
/// Authored initial desk notice. This does not represent a completed action.
///
/// # Errors
/// Refuses malformed policy.
pub fn initial_public_venue_notice(
    policy: &PublicVenuePolicy,
) -> Result<PublicVenueRecord, PublicVenueError> {
    PublicVenueRecord::from_policy(policy, 0, PublicVenueRecordKind::AuthoredInitialNotice)
}
/// Encode one validated canonical publication.
///
/// # Errors
/// Refuses foreign, modified, or oversized publication.
pub fn encode_public_venue_record(
    policy: &PublicVenuePolicy,
    record: &PublicVenueRecord,
) -> Result<Vec<u8>, PublicVenueError> {
    record.validate(policy)?;
    let mut bytes = b"babylon.public-venue.record.v1\0".to_vec();
    serde_json::to_writer(&mut bytes, record).map_err(|_| PublicVenueError::Codec)?;
    if bytes.len() > PUBLIC_VENUE_MAX_BYTES {
        return Err(PublicVenueError::SizeLimit);
    }
    Ok(bytes)
}
/// Decode only the exact current canonical publication encoding.
///
/// # Errors
/// Refuses old, foreign, modified, malformed, or noncanonical bytes.
pub fn decode_public_venue_record(
    policy: &PublicVenuePolicy,
    bytes: &[u8],
) -> Result<PublicVenueRecord, PublicVenueError> {
    if bytes.len() > PUBLIC_VENUE_MAX_BYTES {
        return Err(PublicVenueError::SizeLimit);
    }
    let data = bytes
        .strip_prefix(b"babylon.public-venue.record.v1\0")
        .ok_or(PublicVenueError::Codec)?;
    let record: PublicVenueRecord =
        serde_json::from_slice(data).map_err(|_| PublicVenueError::Codec)?;
    if encode_public_venue_record(policy, &record)? != bytes {
        return Err(PublicVenueError::NonCanonical);
    }
    Ok(record)
}

/// Maximum public records retained in one bounded history.
pub const PUBLIC_VENUE_MAX_RECORDS: usize = 4096;
const HISTORY_DOMAIN: &[u8] = b"babylon.public-venue.history.v1\0";
// Each fixed-shape record is bounded separately; commas and the policy/frame
// account for the remaining bytes. This is a representation limit, not a host budget.
const MAX_HISTORY_BYTES: usize = PUBLIC_VENUE_MAX_RECORDS * (PUBLIC_VENUE_MAX_BYTES + 1)
    + PUBLIC_VENUE_MAX_BYTES
    + HISTORY_DOMAIN.len()
    + 32;

/// Public data only; historical occurrence proofs must be retained separately.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PublicVenueHistory {
    pub policy: PublicVenuePolicy,
    pub records: Vec<PublicVenueRecord>,
}
impl PublicVenueHistory {
    /// Validate public shape and ordering, without authenticating occurrences.
    ///
    /// # Errors
    /// Refuses foreign, duplicate, unordered, missing or oversized records.
    pub fn validate(&self) -> Result<(), PublicVenueError> {
        self.policy.validate()?;
        if self.records.len() > PUBLIC_VENUE_MAX_RECORDS {
            return Err(PublicVenueError::SizeLimit);
        }
        if self.records.first() != Some(&initial_public_venue_notice(&self.policy)?) {
            return Err(PublicVenueError::InvalidRecord);
        }
        for record in &self.records {
            record.validate(&self.policy)?;
        }
        if !self
            .records
            .windows(2)
            .all(|pair| (pair[0].period, pair[0].source_id) < (pair[1].period, pair[1].source_id))
        {
            return Err(PublicVenueError::NonCanonical);
        }
        Ok(())
    }
}
/// Encode bounded public history; no private occurrence proof is included.
///
/// # Errors
/// Refuses malformed, duplicate or oversized history.
pub fn encode_public_venue_history(
    history: &PublicVenueHistory,
) -> Result<Vec<u8>, PublicVenueError> {
    history.validate()?;
    let mut bytes = HISTORY_DOMAIN.to_vec();
    serde_json::to_writer(&mut bytes, history).map_err(|_| PublicVenueError::Codec)?;
    if bytes.len() > MAX_HISTORY_BYTES {
        return Err(PublicVenueError::SizeLimit);
    }
    Ok(bytes)
}
/// Decode exact canonical public history; occurrence evidence remains separate.
///
/// # Errors
/// Refuses old, malformed, duplicate, or noncanonical history.
pub fn decode_public_venue_history(bytes: &[u8]) -> Result<PublicVenueHistory, PublicVenueError> {
    if bytes.len() > MAX_HISTORY_BYTES {
        return Err(PublicVenueError::SizeLimit);
    }
    let data = bytes
        .strip_prefix(HISTORY_DOMAIN)
        .ok_or(PublicVenueError::Codec)?;
    let history: PublicVenueHistory =
        serde_json::from_slice(data).map_err(|_| PublicVenueError::Codec)?;
    if encode_public_venue_history(&history)? != bytes {
        return Err(PublicVenueError::NonCanonical);
    }
    Ok(history)
}
