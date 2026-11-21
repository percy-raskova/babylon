//! The county's stored state and the canonical, domain-framed bytes of its values.
//!
//! The bytes are the domain, a zero byte and canonical JSON, as the City PD's are. Money is a
//! decimal string. A value decodes only from its own canonical bytes.
use babylon_kernel::content_digest;
use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};

use super::roster;
use super::session::SessionRecord;
use super::types::{
    CountyPeriodFacts, CountyReviewConfig, CountyReviewError, Roster, COUNTY_REVIEW_MAX_ROWS,
    COUNTY_REVIEW_SCHEMA_VERSION,
};

/// Largest encoding, in bytes.
const MAX_BYTES: usize = 8 * 1024 * 1024;
const CONFIG_DOMAIN: &[u8] = b"babylon.county-review-config.v1";
const STATE_DOMAIN: &[u8] = b"babylon.county-review-state.v1";

/// What the campaign keeps of the County Review between periods.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CountyReviewState {
    /// Wire schema.
    pub schema_version: u32,
    /// The roster, rolled forward to the next period's opening.
    pub roster: Roster,
    /// The facts of the last close the player has seen.
    pub last_facts: Option<CountyPeriodFacts>,
    /// The last session held. A period before the first session leaves it as it was.
    pub last_session: Option<SessionRecord>,
}

/// Checks the stored state against the configuration: the schema, the roster, the facts' shape and
/// the last session's rows, which must follow one another by key.
///
/// # Errors
///
/// `UnsupportedSchema`, the refusals of the configuration and the roster, `FactsShape`,
/// `StateShape` for a session with no facts, `SizeLimit` and `RosterNotCanonical` for a session
/// with too many or unsorted rows, and `UnknownGroup` for a row outside the configuration.
pub fn validate_county_review_state(
    config: &CountyReviewConfig,
    state: &CountyReviewState,
) -> Result<(), CountyReviewError> {
    if state.schema_version != COUNTY_REVIEW_SCHEMA_VERSION {
        return Err(CountyReviewError::UnsupportedSchema);
    }
    roster::validate_county_review_config(config)?;
    roster::validate_roster(config, &state.roster)?;
    if let Some(facts) = &state.last_facts {
        roster::check_facts_shape(config, facts)?;
    }
    let Some(session) = &state.last_session else {
        return Ok(());
    };
    if state.last_facts.is_none() {
        return Err(CountyReviewError::StateShape);
    }
    if session.rows.len() > COUNTY_REVIEW_MAX_ROWS {
        return Err(CountyReviewError::SizeLimit);
    }
    if !session
        .rows
        .windows(2)
        .all(|pair| pair[0].key < pair[1].key)
    {
        return Err(CountyReviewError::RosterNotCanonical);
    }
    let in_range = session
        .rows
        .iter()
        .all(|row| usize::try_from(row.key.group).is_ok_and(|g| g < config.groups.len()));
    if in_range {
        Ok(())
    } else {
        Err(CountyReviewError::UnknownGroup)
    }
}

fn canonical<T: Serialize>(domain: &[u8], value: &T) -> Result<Vec<u8>, CountyReviewError> {
    let mut bytes = domain.to_vec();
    bytes.push(0);
    serde_json::to_writer(&mut bytes, value).map_err(|_| CountyReviewError::Codec)?;
    if bytes.len() > MAX_BYTES {
        return Err(CountyReviewError::SizeLimit);
    }
    Ok(bytes)
}

fn decode<T: Serialize + DeserializeOwned>(
    domain: &[u8],
    bytes: &[u8],
) -> Result<T, CountyReviewError> {
    if bytes.len() > MAX_BYTES {
        return Err(CountyReviewError::SizeLimit);
    }
    let payload = bytes
        .strip_prefix(domain)
        .and_then(|rest| rest.strip_prefix(&[0]))
        .ok_or(CountyReviewError::Codec)?;
    let value: T = serde_json::from_slice(payload).map_err(|_| CountyReviewError::Codec)?;
    if canonical(domain, &value)? != bytes {
        return Err(CountyReviewError::NonCanonical);
    }
    Ok(value)
}

/// The canonical bytes of a validated configuration.
///
/// # Errors
///
/// The refusals of the configuration, `Codec` and `SizeLimit`.
pub fn encode_county_review_config(c: &CountyReviewConfig) -> Result<Vec<u8>, CountyReviewError> {
    roster::validate_county_review_config(c)?;
    canonical(CONFIG_DOMAIN, c)
}

/// Reads a configuration from its canonical bytes.
///
/// # Errors
///
/// `SizeLimit`, `Codec` for another domain or malformed JSON, `NonCanonical` for bytes that are
/// not the canonical form, and the refusals of the configuration.
pub fn decode_county_review_config(bytes: &[u8]) -> Result<CountyReviewConfig, CountyReviewError> {
    let config: CountyReviewConfig = decode(CONFIG_DOMAIN, bytes)?;
    roster::validate_county_review_config(&config)?;
    Ok(config)
}

/// The canonical bytes of a state. Checks the schema only: a state is validated against its
/// configuration by `validate_county_review_state`.
///
/// # Errors
///
/// `UnsupportedSchema`, `Codec` and `SizeLimit`.
pub fn encode_county_review_state(s: &CountyReviewState) -> Result<Vec<u8>, CountyReviewError> {
    if s.schema_version != COUNTY_REVIEW_SCHEMA_VERSION {
        return Err(CountyReviewError::UnsupportedSchema);
    }
    canonical(STATE_DOMAIN, s)
}

/// Reads a state from its canonical bytes.
///
/// # Errors
///
/// `SizeLimit`, `Codec` for another domain or malformed JSON, `NonCanonical` for bytes that are
/// not the canonical form, and `UnsupportedSchema`.
pub fn decode_county_review_state(bytes: &[u8]) -> Result<CountyReviewState, CountyReviewError> {
    let state: CountyReviewState = decode(STATE_DOMAIN, bytes)?;
    if state.schema_version != COUNTY_REVIEW_SCHEMA_VERSION {
        return Err(CountyReviewError::UnsupportedSchema);
    }
    Ok(state)
}

/// The identity of a configuration: the SHA-256 of its canonical bytes.
///
/// # Errors
///
/// The refusals of `encode_county_review_config`.
pub fn county_review_config_digest(c: &CountyReviewConfig) -> Result<[u8; 32], CountyReviewError> {
    Ok(content_digest::sha256_of(&encode_county_review_config(c)?))
}
