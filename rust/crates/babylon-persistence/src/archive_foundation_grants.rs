//! Foundation knowledge-grant seeding (ADR249 R3).
//!
//! At campaign foundation every public-reference subject — all 83 Michigan
//! counties and all 745 Michigan Census places from the pinned spatial
//! reference products, plus every glossary concept from the pinned fixture —
//! receives the cursory public-record grant keys at tick 0: `subject`,
//! `identity`, and `containment` for geography, `subject` and `identity`
//! for concepts. Compositional and magnitude keys stay ungranted; they are
//! earned, never seeded (ADR182).

use postgres::GenericClient;

use crate::archive::{insert_grant_row_v1, ArchiveCitationV1, SemanticArchiveErrorV1};
use crate::glossary_concepts::{glossary_concepts_v1, GlossaryConceptsErrorV1};
use crate::h3_reference_cohort::{representative_h3_reference_cohort_v1, H3ReferenceCohortError};
use crate::identity::CampaignId;
use crate::spatial_reference_products::{
    michigan_spatial_reference_products_v1, SpatialReferenceProductsError,
};

/// The foundation grant stamp: knowledge granted before any committed tick.
pub const FOUNDATION_GRANT_TICK_V1: u64 = 0;

/// Source identity of the pinned `dim_county` artifact behind county grants.
pub const FOUNDATION_COUNTY_SOURCE_ID_V1: &str = "h3-estate-contract-v1";
/// Locator prefix pinning one county identity row in `dim_county.parquet`.
pub const FOUNDATION_COUNTY_LOCATOR_PREFIX_V1: &str = "dim_county.parquet#fips=";
/// Source identity of the pinned place identity contract artifact.
pub const FOUNDATION_PLACE_IDENTITY_SOURCE_ID_V1: &str = "census-place-authority-v1";
/// Locator prefix pinning one place identity row.
pub const FOUNDATION_PLACE_IDENTITY_LOCATOR_PREFIX_V1: &str =
    "census_place_identity_mi_2023.csv.gz#place_geoid=";
/// Source identity of the pinned county/place overlap contract artifact.
pub const FOUNDATION_PLACE_CONTAINMENT_SOURCE_ID_V1: &str = "county-place-h3-overlap-v1";
/// Locator prefix pinning one place containment row in the overlap artifact.
pub const FOUNDATION_PLACE_CONTAINMENT_LOCATOR_PREFIX_V1: &str =
    "census_county_place_h3_land_overlap_mi_2023.parquet#place_geoid=";

/// Cursory public-record keys granted to every county at foundation.
pub const FOUNDATION_COUNTY_GRANT_KEYS_V1: [&str; 3] = ["subject", "identity", "containment"];
/// Cursory public-record keys granted to every place at foundation.
pub const FOUNDATION_PLACE_GRANT_KEYS_V1: [&str; 3] = ["subject", "identity", "containment"];
/// Cursory public-record keys granted to every glossary concept at foundation.
pub const FOUNDATION_CONCEPT_GRANT_KEYS_V1: [&str; 2] = ["subject", "identity"];

/// Census GEOID prefix of Michigan; only Michigan counties are
/// public-reference subjects in the v1 game world.
pub const MICHIGAN_GEOID_PREFIX_V1: &str = "26";

/// The `999` county FIPS is a statewide residual pseudo-county in the pinned
/// `dim_county` artifact, not a public-reference county subject.
pub const STATEWIDE_RESIDUAL_COUNTY_FIPS_V1: &str = "999";

/// Closed refusal taxonomy for foundation grant seeding.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum FoundationGrantsErrorV1 {
    /// The pinned H3 reference cohort fixture drifted.
    Cohort(H3ReferenceCohortError),
    /// The pinned spatial reference products fixture drifted.
    Spatial(SpatialReferenceProductsError),
    /// The pinned glossary concept fixture drifted.
    Concepts(GlossaryConceptsErrorV1),
    /// One grant row refused validation, conflicted, or hit a database error.
    Archive(SemanticArchiveErrorV1),
}

impl From<H3ReferenceCohortError> for FoundationGrantsErrorV1 {
    fn from(error: H3ReferenceCohortError) -> Self {
        Self::Cohort(error)
    }
}

impl From<SpatialReferenceProductsError> for FoundationGrantsErrorV1 {
    fn from(error: SpatialReferenceProductsError) -> Self {
        Self::Spatial(error)
    }
}

impl From<GlossaryConceptsErrorV1> for FoundationGrantsErrorV1 {
    fn from(error: GlossaryConceptsErrorV1) -> Self {
        Self::Concepts(error)
    }
}

impl From<SemanticArchiveErrorV1> for FoundationGrantsErrorV1 {
    fn from(error: SemanticArchiveErrorV1) -> Self {
        Self::Archive(error)
    }
}

impl std::fmt::Display for FoundationGrantsErrorV1 {
    fn fmt(&self, formatter: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(formatter, "foundation grants refusal: {self:?}")
    }
}

impl std::error::Error for FoundationGrantsErrorV1 {}

/// Exact foundation-seed census for one campaign.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct FoundationGrantReportV1 {
    counties: usize,
    places: usize,
    concepts: usize,
    grant_rows: usize,
}

impl FoundationGrantReportV1 {
    /// Number of county subjects granted.
    #[must_use]
    pub const fn counties(&self) -> usize {
        self.counties
    }

    /// Number of place subjects granted.
    #[must_use]
    pub const fn places(&self) -> usize {
        self.places
    }

    /// Number of glossary concept subjects granted.
    #[must_use]
    pub const fn concepts(&self) -> usize {
        self.concepts
    }

    /// Total immutable grant rows asserted.
    #[must_use]
    pub const fn grant_rows(&self) -> usize {
        self.grant_rows
    }
}

fn county_citation(county_geoid: &str) -> ArchiveCitationV1 {
    ArchiveCitationV1::try_new(
        FOUNDATION_COUNTY_SOURCE_ID_V1.to_owned(),
        format!("{FOUNDATION_COUNTY_LOCATOR_PREFIX_V1}{county_geoid}"),
    )
    .expect("bounded county locator")
}

fn place_identity_citation(place_geoid: &str) -> ArchiveCitationV1 {
    ArchiveCitationV1::try_new(
        FOUNDATION_PLACE_IDENTITY_SOURCE_ID_V1.to_owned(),
        format!("{FOUNDATION_PLACE_IDENTITY_LOCATOR_PREFIX_V1}{place_geoid}"),
    )
    .expect("bounded place identity locator")
}

fn place_containment_citation(place_geoid: &str) -> ArchiveCitationV1 {
    ArchiveCitationV1::try_new(
        FOUNDATION_PLACE_CONTAINMENT_SOURCE_ID_V1.to_owned(),
        format!("{FOUNDATION_PLACE_CONTAINMENT_LOCATOR_PREFIX_V1}{place_geoid}"),
    )
    .expect("bounded place containment locator")
}

/// Seed the foundation knowledge grants for one campaign.
///
/// Every insert is idempotent with an exact-reconcile refusal, so an exact
/// retry reports the same census and a drifted row refuses loudly. The whole
/// seed runs inside the caller's open transaction, preserving whole-tick
/// atomic publication (ADR223).
///
/// # Errors
/// Refuses pinned-fixture drift, a malformed subject, a conflicting prior
/// grant row, or database failure.
pub fn seed_foundation_grants_v1(
    client: &mut impl GenericClient,
    campaign_id: CampaignId,
) -> Result<FoundationGrantReportV1, FoundationGrantsErrorV1> {
    let cohort = representative_h3_reference_cohort_v1()?;
    let products = michigan_spatial_reference_products_v1(cohort)?;
    let concepts = glossary_concepts_v1()?;
    let mut grant_rows = 0usize;
    for county in products.counties().iter().filter(|county| {
        county.county_geoid().starts_with(MICHIGAN_GEOID_PREFIX_V1)
            && county.county_fips() != STATEWIDE_RESIDUAL_COUNTY_FIPS_V1
    }) {
        let citation = county_citation(county.county_geoid());
        for key in FOUNDATION_COUNTY_GRANT_KEYS_V1 {
            insert_grant_row_v1(
                client,
                campaign_id,
                "county",
                county.county_geoid(),
                key,
                FOUNDATION_GRANT_TICK_V1,
                &citation,
            )?;
            grant_rows += 1;
        }
    }
    for place in products.places() {
        let identity = place_identity_citation(place.place_geoid());
        let containment = place_containment_citation(place.place_geoid());
        for key in FOUNDATION_PLACE_GRANT_KEYS_V1 {
            let citation = if key == "containment" {
                &containment
            } else {
                &identity
            };
            insert_grant_row_v1(
                client,
                campaign_id,
                "place",
                place.place_geoid(),
                key,
                FOUNDATION_GRANT_TICK_V1,
                citation,
            )?;
            grant_rows += 1;
        }
    }
    for concept in concepts.concepts() {
        for key in FOUNDATION_CONCEPT_GRANT_KEYS_V1 {
            insert_grant_row_v1(
                client,
                campaign_id,
                "concept",
                concept.concept_id(),
                key,
                FOUNDATION_GRANT_TICK_V1,
                concept.citation(),
            )?;
            grant_rows += 1;
        }
    }
    let counties = products
        .counties()
        .iter()
        .filter(|county| {
            county.county_geoid().starts_with(MICHIGAN_GEOID_PREFIX_V1)
                && county.county_fips() != STATEWIDE_RESIDUAL_COUNTY_FIPS_V1
        })
        .count();
    Ok(FoundationGrantReportV1 {
        counties,
        places: products.places().len(),
        concepts: concepts.concepts().len(),
        grant_rows,
    })
}
