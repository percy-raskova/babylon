//! Pinned ACS resident worker classes, separate from workplace jobs and payroll.
//!
//! The eight disjoint B24080 classes reconcile to the existing B23025 employed
//! resident control. Original sex-specific estimates and margins remain intact;
//! summing two estimates does not invent a combined margin of error.

mod model;
mod parse;
#[cfg(test)]
mod tests;
pub use model::*;

use crate::national_counties::{national_county_reference, NationalCountyReferenceError};
use babylon_kernel::{content_digest::sha256_of, geography::CountyGeoid};
use std::{io::Read, sync::OnceLock};

const ARTIFACT: &[u8] = include_bytes!(
    "../../../../src/babylon/data/reference/economy/national_resident_workforce_2024.csv.gz"
);
const MAX_COMPRESSED_BYTES: usize = 524_288;
const MAX_DECODED_BYTES: usize = 4_194_304;
const COUNTY_COUNT: usize = 3144;
const ARTIFACT_SHA256: [u8; 32] = [
    79, 210, 211, 37, 203, 173, 116, 66, 76, 194, 194, 15, 55, 5, 199, 110, 210, 220, 3, 75, 208,
    56, 99, 125, 181, 119, 199, 218, 139, 231, 192, 160,
];
const COUNTY_REFERENCE_SHA256: [u8; 32] = [
    40, 173, 132, 164, 97, 240, 12, 18, 72, 155, 17, 224, 215, 112, 173, 113, 188, 63, 9, 25, 13,
    188, 53, 119, 77, 114, 95, 194, 51, 63, 236, 142,
];
static REFERENCE: OnceLock<
    Result<NationalResidentWorkforceReference, ResidentWorkforceReferenceError>,
> = OnceLock::new();

/// Immutable county observations, not an allocation of persons to game workplaces.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NationalResidentWorkforceReference {
    counties: Box<[ResidentWorkerClasses]>,
}
impl NationalResidentWorkforceReference {
    /// Admit the exact qualified artifact and reconcile its county resident controls.
    /// # Errors
    /// Refuses changed bytes, malformed cells, missing counties or contradictory counts.
    pub fn decode_pinned(bytes: &[u8]) -> Result<Self, ResidentWorkforceReferenceError> {
        if bytes.len() > MAX_COMPRESSED_BYTES {
            return Err(ResidentWorkforceReferenceError::Bound);
        }
        if sha256_of(bytes) != ARTIFACT_SHA256 {
            return Err(ResidentWorkforceReferenceError::ArtifactDigest);
        }
        let counties =
            national_county_reference().map_err(ResidentWorkforceReferenceError::CountySource)?;
        if counties.artifact_sha256() != COUNTY_REFERENCE_SHA256 {
            return Err(ResidentWorkforceReferenceError::CountyDigest);
        }
        parse::capture(&decode(bytes)?, counties)
    }
    /// All domestic county observations in ascending GEOID order.
    #[must_use]
    pub fn counties(&self) -> &[ResidentWorkerClasses] {
        &self.counties
    }
    /// Find a county in the captured domestic roster.
    /// # Errors
    /// Refuses identities outside the captured roster.
    pub fn county(
        &self,
        id: CountyGeoid,
    ) -> Result<&ResidentWorkerClasses, ResidentWorkforceReferenceError> {
        self.counties
            .binary_search_by_key(&id, ResidentWorkerClasses::geoid)
            .map(|index| &self.counties[index])
            .map_err(|_| ResidentWorkforceReferenceError::UnknownCounty(id))
    }
    /// Exact compressed artifact digest for consuming campaign provenance.
    #[must_use]
    pub const fn artifact_sha256(&self) -> [u8; 32] {
        ARTIFACT_SHA256
    }
}

/// Specific source refusals; unavailable counts never become numeric zero.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ResidentWorkforceReferenceError {
    /// Compressed, decoded or row bounds were exceeded.
    Bound,
    /// Bytes differ from the qualified source artifact.
    ArtifactDigest,
    /// Invalid gzip, UTF-8 or trailing compressed bytes.
    Compression,
    /// Column identity or order differs from the contract.
    Header,
    /// Malformed record or wrong field count.
    CsvShape,
    /// Malformed county identity.
    CountyIdentity,
    /// Counties are repeated or out of order.
    CountyOrder,
    /// A lookup or source row lies outside the captured domestic roster.
    UnknownCounty(CountyGeoid),
    /// The county control artifact differs from the captured source dependency.
    CountyDigest,
    /// The shared county control or source-cell contract refused input.
    CountySource(NationalCountyReferenceError),
    /// The exact domestic roster is incomplete.
    Coverage,
    /// An estimate uses a margin-only sentinel, or conversely.
    SentinelRole,
    /// Available source cells contradict a disjoint partition.
    Partition,
    /// Available employed residents differ from the B23025 county control.
    ResidentControl,
    /// An exact subtotal exceeds the signed-64-bit source quantity bound.
    Arithmetic,
}
impl std::fmt::Display for ResidentWorkforceReferenceError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "resident workforce reference refused: {self:?}")
    }
}
impl std::error::Error for ResidentWorkforceReferenceError {}

/// Load the source once without creating workforce pools, wages or game persons.
/// # Errors
/// Returns the exact source-admission refusal without partial capture.
pub fn national_resident_workforce_reference(
) -> Result<&'static NationalResidentWorkforceReference, ResidentWorkforceReferenceError> {
    REFERENCE
        .get_or_init(|| NationalResidentWorkforceReference::decode_pinned(ARTIFACT))
        .as_ref()
        .map_err(Clone::clone)
}

fn decode(bytes: &[u8]) -> Result<String, ResidentWorkforceReferenceError> {
    let mut decoder = flate2::bufread::GzDecoder::new(bytes);
    let mut text = String::new();
    decoder
        .by_ref()
        .take((MAX_DECODED_BYTES + 1) as u64)
        .read_to_string(&mut text)
        .map_err(|_| ResidentWorkforceReferenceError::Compression)?;
    if text.len() > MAX_DECODED_BYTES {
        return Err(ResidentWorkforceReferenceError::Bound);
    }
    if !decoder.into_inner().is_empty() {
        return Err(ResidentWorkforceReferenceError::Compression);
    }
    Ok(text)
}
