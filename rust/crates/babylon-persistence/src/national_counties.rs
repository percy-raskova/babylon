//! Immutable capture of the pinned 2024 national county reference artifact.
//!
//! TIGER supplies the 3,144-county fifty-state/DC roster. ACS supplies 2020–2024
//! five-year resident estimates and 90-percent margins of error. QCEW supplies
//! 2024 covered workplace jobs and payroll. These observations allocate no game
//! persons, households, labor pools, firms, money or production capacity.

use babylon_kernel::{
    content_digest::sha256_of,
    geography::{CountyGeoid, CountyGeoidError, NationalCountyRoster, NATIONAL_COUNTY_COUNT},
};
use std::{io::Read, sync::OnceLock};
mod parse;
#[cfg(test)]
mod tests;
pub(crate) use parse::acs_cell;
use parse::parse_csv;
#[cfg(test)]
use parse::qcew;

const ARTIFACT: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../src/babylon/data/reference/economy/national_county_reference_2024.csv.gz"
));
const MAX_COMPRESSED_BYTES: usize = 1_048_576;
const MAX_CSV_BYTES: usize = 2_097_152;
const COUNTY_COUNT: usize = NATIONAL_COUNTY_COUNT;
// Exact gzip SHA-256 from national_county_reference_2024.metadata.json.
pub(crate) const ARTIFACT_SHA256: [u8; 32] = [
    40, 173, 132, 164, 97, 240, 12, 18, 72, 155, 17, 224, 215, 112, 173, 113, 188, 63, 9, 25, 13,
    188, 53, 119, 77, 114, 95, 194, 51, 63, 236, 142,
];
static REFERENCE: OnceLock<Result<NationalCountyReference, NationalCountyReferenceError>> =
    OnceLock::new();

/// Source availability or sentinel interpretation; no status implies a zero value.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ObservationStatus {
    /// A usable published nonnegative integer.
    Published,
    /// QCEW withheld the observation; its literal placeholder is retained.
    Suppressed,
    /// No selected source row was published.
    NotPublished,
    /// Supplied ACS cell is empty or null; its exact literal is retained.
    Missing,
    /// ACS estimate could not be computed.
    EstimateNotComputable,
    /// ACS sample cases were insufficient.
    InsufficientSampleCases,
    /// ACS observation was not applicable or available.
    NotApplicableOrAvailable,
    /// ACS margin of error could not be computed.
    MoeNotComputable,
    /// ACS open-ended median prevents this margin of error.
    MoeOpenEndedMedian,
    /// ACS controlled-estimate sentinel; a missing margin is not zero uncertainty.
    ControlledEstimate,
}

/// One exact usable value, its original source token and interpreted status.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SourceCell {
    value: Option<u64>,
    raw: String,
    status: ObservationStatus,
}
impl SourceCell {
    /// Usable value in the explicitly named parent measure's units.
    #[must_use]
    pub const fn value(&self) -> Option<u64> {
        self.value
    }
    /// Original token, including sentinel or suppressed placeholder.
    #[must_use]
    pub fn raw(&self) -> &str {
        &self.raw
    }
    /// Availability, distinct from the numeric value and raw token.
    #[must_use]
    pub const fn status(&self) -> ObservationStatus {
        self.status
    }
}

/// An ACS 2020–2024 five-year estimate with its published 90-percent margin.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AcsEstimate {
    /// Estimate in persons or households, as named by the parent field.
    pub estimate: SourceCell,
    /// Margin of error in the same units; never an invented zero.
    pub margin_of_error: SourceCell,
}

/// Resident observations, never a conversion from workplace jobs.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ResidentEstimates {
    /// All resident persons (B01003).
    pub population_persons: AcsEstimate,
    /// Households, not persons (B11001).
    pub households: AcsEstimate,
    /// Resident persons age sixteen and over (B23025).
    pub age_16_plus_persons: AcsEstimate,
    /// Resident labor-force persons, including armed forces.
    pub labor_force_persons: AcsEstimate,
    /// Resident civilian labor-force persons.
    pub civilian_labor_force_persons: AcsEstimate,
    /// Resident civilian employed persons, not jobs or worksite allocation.
    pub civilian_employed_persons: AcsEstimate,
    /// Resident civilian unemployed persons.
    pub civilian_unemployed_persons: AcsEstimate,
    /// Resident armed-forces persons.
    pub armed_forces_persons: AcsEstimate,
    /// Resident persons age sixteen and over outside the labor force.
    pub not_in_labor_force_persons: AcsEstimate,
}

/// County-only QCEW 2024 observations; domestic unallocated jobs are not allocated here.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct WorkplaceObservations {
    status: ObservationStatus,
    disclosure_code: String,
    /// Annual-average statistical establishments, not named employers or sites.
    pub establishments: SourceCell,
    /// Annual-average covered workplace jobs, not distinct resident workers.
    pub jobs: SourceCell,
    /// Calendar-year total payroll in USD; not inferred from rounded jobs or wages.
    pub annual_payroll_usd: SourceCell,
    /// Published annual-average weekly USD per employee, not annual payroll.
    pub mean_weekly_wage_usd: SourceCell,
}
impl WorkplaceObservations {
    /// Availability of the selected source row.
    #[must_use]
    pub const fn status(&self) -> ObservationStatus {
        self.status
    }
    /// Exact source disclosure code: blank or `N`.
    #[must_use]
    pub fn disclosure_code(&self) -> &str {
        &self.disclosure_code
    }
}

/// Published TIGER internal point with exact signed seven-decimal-degree text.
/// It is neither a computed centroid nor a boundary.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct InternalPoint {
    latitude: String,
    longitude: String,
}
impl InternalPoint {
    /// Original latitude text, validated within ninety degrees.
    #[must_use]
    pub fn latitude(&self) -> &str {
        &self.latitude
    }
    /// Original longitude text, validated within one hundred eighty degrees.
    #[must_use]
    pub fn longitude(&self) -> &str {
        &self.longitude
    }
}

/// One admitted county with geography, resident estimates and workplace observations.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CountyReference {
    geoid: CountyGeoid,
    name: String,
    land_square_metres: u64,
    water_square_metres: u64,
    internal_point: InternalPoint,
    residents: ResidentEstimates,
    workplaces: WorkplaceObservations,
}
impl CountyReference {
    /// Exact membership identity in the pinned 2024 roster.
    #[must_use]
    pub const fn geoid(&self) -> CountyGeoid {
        self.geoid
    }
    /// Published TIGER county/equivalent name.
    #[must_use]
    pub fn name(&self) -> &str {
        &self.name
    }
    /// Published land area; does not imply usable production capacity.
    #[must_use]
    pub const fn land_square_metres(&self) -> u64 {
        self.land_square_metres
    }
    /// Published water area in square metres.
    #[must_use]
    pub const fn water_square_metres(&self) -> u64 {
        self.water_square_metres
    }
    /// Published point retained without rounding or reprojection.
    #[must_use]
    pub const fn internal_point(&self) -> &InternalPoint {
        &self.internal_point
    }
    /// Resident person/household evidence and source uncertainty.
    #[must_use]
    pub const fn residents(&self) -> &ResidentEstimates {
        &self.residents
    }
    /// Workplace evidence, distinct from resident persons.
    #[must_use]
    pub const fn workplaces(&self) -> &WorkplaceObservations {
        &self.workplaces
    }
}

/// Immutable ordered capture. Construction requires the exact artifact and roster pins.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NationalCountyReference {
    roster: NationalCountyRoster,
    counties: Box<[CountyReference]>,
}
impl NationalCountyReference {
    /// Decode only the qualified artifact, with bounded decompression and strict values.
    ///
    /// # Errors
    /// Refuses changed bytes, malformed CSV, changed county coverage or contradictory cells.
    pub fn decode_pinned(bytes: &[u8]) -> Result<Self, NationalCountyReferenceError> {
        if bytes.len() > MAX_COMPRESSED_BYTES {
            return Err(NationalCountyReferenceError::Bound);
        }
        if sha256_of(bytes) != ARTIFACT_SHA256 {
            return Err(NationalCountyReferenceError::ArtifactDigest);
        }
        parse_csv(&decode_gzip(bytes)?)
    }
    /// Exact checked domestic membership, shareable without copying observations.
    #[must_use]
    pub const fn roster(&self) -> &NationalCountyRoster {
        &self.roster
    }
    /// Read every county in ascending GEOID order; no mutable collection is exposed.
    #[must_use]
    pub fn counties(&self) -> &[CountyReference] {
        &self.counties
    }
    /// Look up an admitted county. Syntactic validity alone does not authorize membership.
    ///
    /// # Errors
    /// Returns `UnknownCounty` for dependencies, invented codes or counties outside this vintage.
    pub fn county(
        &self,
        id: CountyGeoid,
    ) -> Result<&CountyReference, NationalCountyReferenceError> {
        self.counties
            .binary_search_by_key(&id, CountyReference::geoid)
            .map(|index| &self.counties[index])
            .map_err(|_| NationalCountyReferenceError::UnknownCounty(id))
    }
    /// SHA-256 of the exact compressed artifact used for this capture.
    #[must_use]
    pub const fn artifact_sha256(&self) -> [u8; 32] {
        ARTIFACT_SHA256
    }
}

/// Specific admission failures; no fallback to a partial roster or inferred value.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum NationalCountyReferenceError {
    /// Compressed bytes, decompressed bytes or row count exceeded the bound.
    Bound,
    /// Compressed bytes differ from the one qualified artifact.
    ArtifactDigest,
    /// Gzip, UTF-8 or trailing compressed data was invalid.
    Compression,
    /// Column names/order differ from the source contract.
    Header,
    /// CSV quotes, delimiters or field count are invalid.
    CsvShape,
    /// The identity is not exactly five ASCII decimal digits.
    CountyIdentity(CountyGeoidError),
    /// Separate state/county components, name or point are invalid.
    Geography,
    /// This prefix lies outside the fifty-state/DC county scope.
    OutsideDomesticScope(CountyGeoid),
    /// The same county occurs twice.
    DuplicateCounty(CountyGeoid),
    /// Counties are not in strict source order.
    CountyOrder,
    /// The roster is not the exact 3,144-county TIGER2024 roster.
    RosterDigest,
    /// A token is not a canonical nonnegative signed-64-bit source integer.
    NumericValue,
    /// Value, raw token, disclosure and availability contradict each other.
    Observation,
    /// Available resident counts violate their published partition identities.
    ResidentPartition,
    /// A lookup requested a county outside this captured roster.
    UnknownCounty(CountyGeoid),
}
impl std::fmt::Display for NationalCountyReferenceError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "national county reference refused: {self:?}")
    }
}
impl std::error::Error for NationalCountyReferenceError {}

/// Load the embedded qualified artifact once; this is evidence capture, not campaign integration.
///
/// # Errors
/// Returns the exact pinned-artifact or source-admission failure without a fallback.
pub fn national_county_reference(
) -> Result<&'static NationalCountyReference, NationalCountyReferenceError> {
    REFERENCE
        .get_or_init(|| NationalCountyReference::decode_pinned(ARTIFACT))
        .as_ref()
        .map_err(Clone::clone)
}

// Same bounded single-member gzip pattern used by michigan_sectors; it accepts
// neither appended gzip members nor unconsumed bytes after the stream.
fn decode_gzip(bytes: &[u8]) -> Result<String, NationalCountyReferenceError> {
    let mut decoder = flate2::bufread::GzDecoder::new(bytes);
    let mut text = String::new();
    decoder
        .by_ref()
        .take((MAX_CSV_BYTES + 1) as u64)
        .read_to_string(&mut text)
        .map_err(|_| NationalCountyReferenceError::Compression)?;
    if text.len() > MAX_CSV_BYTES {
        return Err(NationalCountyReferenceError::Bound);
    }
    if !decoder.into_inner().is_empty() {
        return Err(NationalCountyReferenceError::Compression);
    }
    Ok(text)
}
