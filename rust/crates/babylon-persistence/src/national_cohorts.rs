//! Bounded, immutable capture of disjoint 2024 QCEW county observation groups.
//!
//! Known subtotals are not complete totals when a member is suppressed. QCEW
//! workplace jobs are not distinct resident persons. Eligibility here allocates
//! no game firms, labor, recipes, stocks, capacities or monetary balances.

use crate::national_counties::{national_county_reference, NationalCountyReferenceError};
use babylon_kernel::{
    content_digest::sha256_of,
    geography::{CountyGeoid, CountyGeoidError},
};
use std::{io::Read, sync::OnceLock};
mod mapping;
mod model;
mod parse;
#[cfg(test)]
mod tests;
pub use model::{CohortKey, CohortReference, KnownSubtotal, QcewDisclosure, SourceMember};

const ARTIFACT: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../src/babylon/data/reference/economy/national_cohort_reference_2024.csv.gz"
));
const MAX_COMPRESSED_BYTES: usize = 2_097_152;
const MAX_CSV_BYTES: usize = 8_388_608;
const GROUP_COUNT: usize = 59_058;
const MEMBER_COUNT: usize = 144_881;
const ADMITTED_COUNT: usize = 57_238;
// Exact deterministic gzip digest recorded by the source builder.
const ARTIFACT_SHA256: [u8; 32] = [
    28, 150, 63, 107, 112, 156, 49, 247, 152, 37, 62, 65, 102, 38, 25, 163, 42, 211, 29, 69, 50, 2,
    41, 49, 57, 44, 242, 251, 215, 142, 180, 151,
];
/// Exact source Parquet basis digest, before lossless compact grouping.
pub const LEAF_BASIS_SHA256: [u8; 32] = [
    223, 123, 105, 55, 84, 10, 14, 106, 250, 179, 52, 222, 20, 108, 130, 41, 250, 196, 134, 88, 41,
    52, 127, 143, 202, 55, 200, 108, 154, 5, 109, 124,
];
static REFERENCE: OnceLock<Result<NationalCohortReference, NationalCohortReferenceError>> =
    OnceLock::new();

/// All admitted and context groups, sorted by county, optional function and ownership.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NationalCohortReference {
    groups: Box<[CohortReference]>,
}
impl NationalCohortReference {
    /// Capture only the qualified source artifact; changed bytes require qualification.
    ///
    /// # Errors
    /// Refuses altered bytes, bounds, malformed records or inconsistent source measures.
    pub fn decode_pinned(bytes: &[u8]) -> Result<Self, NationalCohortReferenceError> {
        if bytes.len() > MAX_COMPRESSED_BYTES {
            return Err(NationalCohortReferenceError::Bound);
        }
        if sha256_of(bytes) != ARTIFACT_SHA256 {
            return Err(NationalCohortReferenceError::ArtifactDigest);
        }
        let counties =
            national_county_reference().map_err(NationalCohortReferenceError::CountyReference)?;
        let mapping = mapping::FunctionMapping::load()?;
        let groups = parse::parse_csv(&decode_gzip(bytes)?, &mapping, counties)?;
        Ok(Self {
            groups: groups.into_boxed_slice(),
        })
    }
    /// Every captured observation group, including unknown activity and code 99 context.
    #[must_use]
    pub fn groups(&self) -> &[CohortReference] {
        &self.groups
    }
    /// Mapped groups with any positive source-supported establishments, jobs or payroll.
    pub fn admitted_cohorts(&self) -> impl Iterator<Item = &CohortReference> {
        self.groups.iter().filter(|row| row.is_admitted())
    }
    /// Exact group lookup; an absent source cell is not an observed zero.
    #[must_use]
    pub fn group(&self, key: CohortKey) -> Option<&CohortReference> {
        self.groups
            .binary_search_by_key(&key, CohortReference::key)
            .ok()
            .map(|index| &self.groups[index])
    }
    /// All groups for a roster-admitted county. An empty slice is explicit absence.
    ///
    /// # Errors
    /// Refuses a syntactically valid county not present in the pinned domestic roster.
    pub fn groups_in_county(
        &self,
        county: CountyGeoid,
    ) -> Result<&[CohortReference], NationalCohortReferenceError> {
        national_county_reference()
            .map_err(NationalCohortReferenceError::CountyReference)?
            .county(county)
            .map_err(|_| NationalCohortReferenceError::UnknownCounty(county))?;
        let start = self.groups.partition_point(|row| row.key().county < county);
        let end = self
            .groups
            .partition_point(|row| row.key().county <= county);
        Ok(&self.groups[start..end])
    }
    /// SHA-256 of the exact compact gzip bytes captured here.
    #[must_use]
    pub const fn artifact_sha256(&self) -> [u8; 32] {
        ARTIFACT_SHA256
    }
    /// SHA-256 of the Designed function mapping, separate from observed values.
    #[must_use]
    pub const fn function_mapping_sha256(&self) -> [u8; 32] {
        mapping::MAPPING_SHA256
    }
}

/// Specific source refusals; no repair, zero fill or partial capture fallback.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum NationalCohortReferenceError {
    /// Compressed bytes, decoded bytes, rows or members exceed the bound.
    Bound,
    /// Compact bytes differ from the qualified source artifact.
    ArtifactDigest,
    /// Gzip, UTF-8 or trailing compressed bytes are invalid.
    Compression,
    /// The exact header or canonical line shape differs.
    Header,
    /// Record field count or delimiter use differs from the contract.
    CsvShape,
    /// The pinned Designed mapping digest or membership contract differs.
    FunctionMapping,
    /// A source function key is unknown.
    Function,
    /// An ownership code is unknown or an aggregate control.
    Ownership,
    /// The county identity is not exactly five ASCII digits.
    CountyIdentity(CountyGeoidError),
    /// The independently pinned county capture was refused.
    CountyReference(NationalCountyReferenceError),
    /// A county lies outside the exact domestic roster.
    UnknownCounty(CountyGeoid),
    /// A source integer is noncanonical, negative or outside the signed-64-bit bound.
    NumericValue,
    /// A member is outside the disjoint source cut or assigned to the wrong function.
    MemberIdentity,
    /// Members are duplicated or not in strict lexical order.
    MemberOrder,
    /// Declared and actual member counts differ.
    MemberCount,
    /// Publication/suppression and measure availability contradict each other.
    Disclosure,
    /// A measure's known subtotal or publication count differs from its members.
    Subtotal,
    /// Admission disagrees with the explicit positive-source-activity rule.
    Admission,
    /// Groups are duplicated or not in strict canonical order.
    GroupOrder,
    /// Source-wide row, member or admission counts differ from the qualified artifact.
    Coverage,
}
impl std::fmt::Display for NationalCohortReferenceError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "national cohort reference refused: {self:?}")
    }
}
impl std::error::Error for NationalCohortReferenceError {}

/// Capture embedded source evidence once. This function does not initialize a campaign.
///
/// # Errors
/// Returns the exact pinned-artifact or source-admission failure without a fallback.
pub fn national_cohort_reference(
) -> Result<&'static NationalCohortReference, NationalCohortReferenceError> {
    REFERENCE
        .get_or_init(|| NationalCohortReference::decode_pinned(ARTIFACT))
        .as_ref()
        .map_err(Clone::clone)
}
fn decode_gzip(bytes: &[u8]) -> Result<String, NationalCohortReferenceError> {
    let mut decoder = flate2::bufread::GzDecoder::new(bytes);
    let mut text = String::new();
    decoder
        .by_ref()
        .take((MAX_CSV_BYTES + 1) as u64)
        .read_to_string(&mut text)
        .map_err(|_| NationalCohortReferenceError::Compression)?;
    if text.len() > MAX_CSV_BYTES {
        return Err(NationalCohortReferenceError::Bound);
    }
    if !decoder.into_inner().is_empty() {
        return Err(NationalCohortReferenceError::Compression);
    }
    Ok(text)
}
