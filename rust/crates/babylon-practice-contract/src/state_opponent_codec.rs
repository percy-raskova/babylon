//! Canonical domain-framed City PD identities.
use crate::state_opponent;
use crate::state_opponent::{
    CityPdCase, CityPdConfig, CityPdDecisionReceipt, CityPdError, CityPdIntent, CityPdReceipt,
};
use babylon_kernel::content_digest;
use serde::de::DeserializeOwned;
use serde::Serialize;
const MAX_BYTES: usize = 1024 * 1024;
const CONFIG: &[u8] = b"babylon.city-pd-config.v1";
const CASE: &[u8] = b"babylon.city-pd-case.v1";
const INTENT: &[u8] = b"babylon.city-pd-intent.v1";
const DECISION: &[u8] = b"babylon.city-pd-decision.v1";
const RECEIPT: &[u8] = b"babylon.city-pd-receipt.v1";
fn canonical<T: Serialize>(domain: &[u8], value: &T) -> Result<Vec<u8>, CityPdError> {
    let mut bytes = domain.to_vec();
    bytes.push(0);
    serde_json::to_writer(&mut bytes, value).map_err(|_| CityPdError::Codec)?;
    if bytes.len() > MAX_BYTES {
        return Err(CityPdError::SizeLimit);
    }
    Ok(bytes)
}
fn decode<T: Serialize + DeserializeOwned>(domain: &[u8], bytes: &[u8]) -> Result<T, CityPdError> {
    if bytes.len() > MAX_BYTES {
        return Err(CityPdError::SizeLimit);
    }
    let payload = bytes
        .strip_prefix(domain)
        .and_then(|v| v.strip_prefix(&[0]))
        .ok_or(CityPdError::Codec)?;
    let value = serde_json::from_slice(payload).map_err(|_| CityPdError::Codec)?;
    if canonical(domain, &value)? != bytes {
        return Err(CityPdError::NonCanonical);
    }
    Ok(value)
}
// The identity field is first and the mutable case status is last.
fn identity<T: Serialize>(
    domain: &[u8],
    value: &T,
    id_name: &str,
    case: bool,
) -> Result<[u8; 32], CityPdError> {
    let bytes = canonical(domain, value)?;
    let payload =
        std::str::from_utf8(&bytes[domain.len() + 1..]).map_err(|_| CityPdError::Codec)?;
    let marker = format!("{{\"{id_name}\":[");
    let rest = payload.strip_prefix(&marker).ok_or(CityPdError::Codec)?;
    let (_, rest) = rest.split_once("],").ok_or(CityPdError::Codec)?;
    let body = if case {
        rest.rsplit_once(",\"status\":")
            .ok_or(CityPdError::Codec)?
            .0
            .to_owned()
            + "}"
    } else {
        rest.to_owned()
    };
    let mut result = domain.to_vec();
    result.extend_from_slice(b"\0{");
    result.extend_from_slice(body.as_bytes());
    Ok(content_digest::sha256_of(&result))
}
/// Derive the canonical identity.
///
/// # Errors
/// Returns an error if the value cannot be canonically encoded within its bound.
pub fn city_pd_config_digest(c: &CityPdConfig) -> Result<[u8; 32], CityPdError> {
    Ok(content_digest::sha256_of(&encode_city_pd_config(c)?))
}
/// Derive the canonical identity.
///
/// # Errors
/// Returns an error if the value cannot be canonically encoded within its bound.
pub fn city_pd_case_id(c: &CityPdCase) -> Result<[u8; 32], CityPdError> {
    identity(CASE, c, "case_id", true)
}
/// Derive the canonical identity.
///
/// # Errors
/// Returns an error if the value cannot be canonically encoded within its bound.
pub fn city_pd_intent_id(i: &CityPdIntent) -> Result<[u8; 32], CityPdError> {
    identity(INTENT, i, "intent_id", false)
}
/// Derive the canonical identity.
///
/// # Errors
/// Returns an error if the value cannot be canonically encoded within its bound.
pub fn city_pd_decision_id(d: &CityPdDecisionReceipt) -> Result<[u8; 32], CityPdError> {
    identity(DECISION, d, "decision_id", false)
}
/// Derive the canonical identity.
///
/// # Errors
/// Returns an error if the value cannot be canonically encoded within its bound.
pub fn city_pd_receipt_id(r: &CityPdReceipt) -> Result<[u8; 32], CityPdError> {
    identity(RECEIPT, r, "receipt_id", false)
}
macro_rules! codec {
    ($encode:ident, $decode:ident, $ty:ty, $domain:ident, $validate:path) => {
        /// Encode a validated value in its canonical domain.
        ///
        /// # Errors
        /// Returns an error for invalid fields, identities, or an oversized encoding.
        pub fn $encode(value: &$ty) -> Result<Vec<u8>, CityPdError> {
            $validate(value)?;
            canonical($domain, value)
        }
        /// Decode and validate canonical domain-framed bytes.
        ///
        /// # Errors
        /// Returns an error for malformed, noncanonical, or invalid input.
        pub fn $decode(bytes: &[u8]) -> Result<$ty, CityPdError> {
            let value = decode($domain, bytes)?;
            $validate(&value)?;
            Ok(value)
        }
    };
}
codec!(
    encode_city_pd_config,
    decode_city_pd_config,
    CityPdConfig,
    CONFIG,
    state_opponent::validate_city_pd_config
);
codec!(
    encode_city_pd_case,
    decode_city_pd_case,
    CityPdCase,
    CASE,
    state_opponent::validate_city_pd_case
);
codec!(
    encode_city_pd_intent,
    decode_city_pd_intent,
    CityPdIntent,
    INTENT,
    state_opponent::validate_city_pd_intent
);
codec!(
    encode_city_pd_decision,
    decode_city_pd_decision,
    CityPdDecisionReceipt,
    DECISION,
    state_opponent::validate_city_pd_decision
);
codec!(
    encode_city_pd_receipt,
    decode_city_pd_receipt,
    CityPdReceipt,
    RECEIPT,
    state_opponent::validate_city_pd_receipt
);
