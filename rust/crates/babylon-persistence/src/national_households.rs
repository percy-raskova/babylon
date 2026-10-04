//! Pinned ACS household, household-person, income and earnings margins for 3,144 counties.
//!
//! These are separate 2020–2024 five-year marginal estimates, with original
//! 90-percent margins of error. They establish no joint household profiles,
//! workplace allocation, class, wages, wealth, domestic labor or game time.
//! Raw annotations are unavailable in the source bulk files, not empty strings.

mod model;
mod parse;
#[cfg(test)]
mod tests;
pub use model::*;

use crate::national_counties::{
    national_county_reference, NationalCountyReference, NationalCountyReferenceError,
};
use babylon_kernel::{
    content_digest::sha256_of,
    geography::{CountyGeoid, NATIONAL_COUNTY_COUNT},
};
use std::{io::Read, sync::OnceLock};

const ARTIFACT: &[u8] = include_bytes!(
    "../../../../src/babylon/data/reference/economy/national_household_reference_2024.csv.gz"
);
const MAX_COMPRESSED_BYTES: usize = 1_048_576;
const MAX_DECODED_BYTES: usize = 8_388_608;
const COUNTY_COUNT: usize = NATIONAL_COUNTY_COUNT;
const ARTIFACT_SHA256: [u8; 32] = [
    141, 227, 137, 13, 218, 70, 137, 46, 213, 58, 159, 218, 9, 48, 117, 160, 206, 150, 47, 147, 18,
    28, 103, 5, 213, 223, 29, 252, 90, 74, 101, 130,
];
const COUNTY_REFERENCE_SHA256: [u8; 32] = [
    40, 173, 132, 164, 97, 240, 12, 18, 72, 155, 17, 224, 215, 112, 173, 113, 188, 63, 9, 25, 13,
    188, 53, 119, 77, 114, 95, 194, 51, 63, 236, 142,
];
static REFERENCE: OnceLock<Result<NationalHouseholdReference, HouseholdReferenceError>> =
    OnceLock::new();

/// Immutable county observations. Construction verifies source and county pins.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NationalHouseholdReference {
    counties: Box<[CountyHouseholdMargins]>,
}
impl NationalHouseholdReference {
    /// Admit only qualified source bytes and reconcile captured county controls.
    /// # Errors
    /// Refuses changed bytes, missing counties, malformed or contradictory cells.
    pub fn decode_pinned(bytes: &[u8]) -> Result<Self, HouseholdReferenceError> {
        let counties =
            national_county_reference().map_err(HouseholdReferenceError::CountySource)?;
        Self::decode_captured(bytes, counties)
    }
    /// Reopen supplied captured bytes with their exact checked county foundation.
    /// # Errors
    /// Refuses changed source/control bytes and contradictory available margins.
    pub fn decode_captured(
        bytes: &[u8],
        counties: &NationalCountyReference,
    ) -> Result<Self, HouseholdReferenceError> {
        if bytes.len() > MAX_COMPRESSED_BYTES {
            return Err(HouseholdReferenceError::Bound);
        }
        if sha256_of(bytes) != ARTIFACT_SHA256 {
            return Err(HouseholdReferenceError::ArtifactDigest);
        }
        if counties.artifact_sha256() != COUNTY_REFERENCE_SHA256 {
            return Err(HouseholdReferenceError::CountyDigest);
        }
        parse::capture(&decode(bytes)?, counties)
    }
    /// County observations in ascending domestic GEOID order.
    #[must_use]
    pub fn counties(&self) -> &[CountyHouseholdMargins] {
        &self.counties
    }
    /// Find a captured residence county without a geographic fallback.
    /// # Errors
    /// Refuses county identities outside the exact domestic roster.
    pub fn county(
        &self,
        id: CountyGeoid,
    ) -> Result<&CountyHouseholdMargins, HouseholdReferenceError> {
        self.counties
            .binary_search_by_key(&id, CountyHouseholdMargins::geoid)
            .map(|index| &self.counties[index])
            .map_err(|_| HouseholdReferenceError::UnknownCounty(id))
    }
    /// Exact compressed artifact digest for source provenance.
    #[must_use]
    pub const fn artifact_sha256(&self) -> [u8; 32] {
        ARTIFACT_SHA256
    }
}

/// Exact refusal boundaries for source capture; missing values never become zero.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum HouseholdReferenceError {
    /// Compressed, decoded or row bound exceeded.
    Bound,
    /// Artifact differs from the qualified compressed bytes.
    ArtifactDigest,
    /// Invalid gzip, UTF-8, truncation or trailing compressed bytes.
    Compression,
    /// Column identity or order differs from the contract.
    Header,
    /// Wrong field count, record delimiter or missing final newline.
    CsvShape,
    /// Malformed county identity.
    CountyIdentity,
    /// Counties repeat or are out of canonical order.
    CountyOrder,
    /// County lies outside the exact captured domestic roster.
    UnknownCounty(CountyGeoid),
    /// County foundation differs from the pinned dependency.
    CountyDigest,
    /// Shared county or observed-cell contract refused input.
    CountySource(NationalCountyReferenceError),
    /// The captured domestic roster is incomplete.
    Coverage,
    /// A margin-only sentinel was used for an estimate, or conversely.
    SentinelRole,
    /// Available source estimates contradict a within-table partition.
    Partition,
    /// B11001 total differs from the captured household control.
    HouseholdControl,
    /// B19001 households differ from the B11001 total.
    IncomeControl,
    /// B19051 historical household total differs from B11001.
    EarningsControl,
    /// Persons in households exceed the captured B01003 population.
    PopulationControl,
    /// A subtotal exceeds the signed-64-bit source quantity bound.
    Arithmetic,
}
impl std::fmt::Display for HouseholdReferenceError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "household reference refused: {self:?}")
    }
}
impl std::error::Error for HouseholdReferenceError {}

/// Load immutable evidence once; no household/game population is allocated here.
/// # Errors
/// Returns the exact source-admission refusal without partial capture.
pub fn national_household_reference(
) -> Result<&'static NationalHouseholdReference, HouseholdReferenceError> {
    REFERENCE
        .get_or_init(|| NationalHouseholdReference::decode_pinned(ARTIFACT))
        .as_ref()
        .map_err(Clone::clone)
}

fn decode(bytes: &[u8]) -> Result<String, HouseholdReferenceError> {
    let mut decoder = flate2::bufread::GzDecoder::new(bytes);
    let mut text = String::new();
    decoder
        .by_ref()
        .take((MAX_DECODED_BYTES + 1) as u64)
        .read_to_string(&mut text)
        .map_err(|_| HouseholdReferenceError::Compression)?;
    if text.len() > MAX_DECODED_BYTES {
        return Err(HouseholdReferenceError::Bound);
    }
    if !decoder.into_inner().is_empty() {
        return Err(HouseholdReferenceError::Compression);
    }
    Ok(text)
}
