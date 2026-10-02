//! Pinned, disjoint world reporting scopes and explicitly qualified source measures.
//!
//! Population projections and annual goods-trade dollars create no labor supply,
//! inventories, productive capacity, purchasing power or automatic demand.

mod model;
mod parse;
#[cfg(test)]
mod tests;
pub use model::*;

use babylon_kernel::{
    content_digest::sha256_of,
    economic_location::{ForeignCounterpart, UsDependency},
};
use std::{io::Read, sync::OnceLock};

const POPULATION: &[u8] = include_bytes!(
    "../../../../src/babylon/data/reference/economy/world_population_reference_2024.csv.gz"
);
const TRADE: &[u8] = include_bytes!("../../../../src/babylon/data/reference/economy/international_counterpart_reference_2024.csv.gz");
const MEMBERSHIP: &[u8] =
    include_bytes!("../../../../contracts/international_counterpart_membership_v1.json");
const SCOPE_POLICY: &[u8] = include_bytes!("../../../../contracts/world_population_scope_v1.json");
const MAX_COMPRESSED_BYTES: usize = 65_536;
const MAX_DECODED_BYTES: usize = 262_144;
const MEMBER_COUNT: usize = 252;
static REFERENCE: OnceLock<Result<WorldReference, WorldReferenceError>> = OnceLock::new();

/// Four independent source pins captured by a campaign that consumes this reference.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct WorldSourceDigests {
    /// Qualified world population gzip.
    pub population: [u8; 32],
    /// Qualified bilateral goods-trade reporting gzip.
    pub trade: [u8; 32],
    /// Disjoint reporting-identity membership policy.
    pub membership: [u8; 32],
    /// Source scope qualifications and Designed allocation policy.
    pub population_scope: [u8; 32],
}

const DIGESTS: WorldSourceDigests = WorldSourceDigests {
    population: [
        110, 198, 48, 158, 135, 182, 29, 57, 3, 133, 25, 223, 120, 129, 179, 169, 220, 88, 175,
        160, 48, 70, 143, 51, 212, 255, 37, 191, 109, 194, 220, 141,
    ],
    trade: [
        101, 143, 169, 4, 193, 196, 37, 94, 219, 100, 226, 21, 29, 154, 34, 188, 217, 106, 215, 74,
        76, 243, 125, 198, 59, 108, 176, 95, 204, 19, 91, 83,
    ],
    membership: [
        11, 221, 84, 63, 205, 197, 149, 3, 241, 3, 122, 81, 42, 252, 113, 95, 89, 20, 35, 191, 225,
        25, 56, 165, 95, 219, 54, 248, 100, 26, 8, 47,
    ],
    population_scope: [
        53, 76, 199, 174, 120, 2, 40, 255, 40, 65, 167, 90, 170, 212, 139, 76, 20, 197, 61, 136,
        174, 166, 58, 184, 95, 142, 163, 98, 248, 166, 138, 209,
    ],
};

/// Immutable source capture with all 252 reporting identities and twelve counterparts.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct WorldReference {
    members: Vec<WorldMember>,
    counterparts: Vec<CounterpartReference>,
    known_persons: u64,
}
impl WorldReference {
    /// Admit only the qualified source artifacts and policy bytes.
    ///
    /// # Errors
    /// Refuses changed bytes, malformed records, scope overlap or contradictory populations.
    pub fn decode_pinned(population: &[u8], trade: &[u8]) -> Result<Self, WorldReferenceError> {
        Self::decode_captured(population, trade, MEMBERSHIP, SCOPE_POLICY)
    }
    /// Admit the four explicitly supplied captured artifacts without policy fallback.
    /// # Errors
    /// Refuses any changed source/policy bytes or inconsistent scope and measures.
    pub fn decode_captured(
        population: &[u8],
        trade: &[u8],
        membership: &[u8],
        scope_policy: &[u8],
    ) -> Result<Self, WorldReferenceError> {
        if [
            population.len(),
            trade.len(),
            membership.len(),
            scope_policy.len(),
        ]
        .into_iter()
        .any(|length| length > MAX_COMPRESSED_BYTES)
        {
            return Err(WorldReferenceError::Bound);
        }
        if sha256_of(population) != DIGESTS.population
            || sha256_of(trade) != DIGESTS.trade
            || sha256_of(membership) != DIGESTS.membership
            || sha256_of(scope_policy) != DIGESTS.population_scope
        {
            return Err(WorldReferenceError::ArtifactDigest);
        }
        parse::capture(&decode(population)?, &decode(trade)?, membership)
    }
    /// Every source identity in canonical source order, including context and missing rows.
    #[must_use]
    pub fn members(&self) -> &[WorldMember] {
        &self.members
    }
    /// Exact lookup; unknown reporting identities are not inferred or aliased.
    #[must_use]
    pub fn member(&self, identity: &str) -> Option<&WorldMember> {
        self.members
            .binary_search_by(|row| row.identity().cmp(identity))
            .ok()
            .map(|index| &self.members[index])
    }
    /// The twelve counterparts in stable identity order.
    #[must_use]
    pub fn counterparts(&self) -> &[CounterpartReference] {
        &self.counterparts
    }
    /// One closed counterpart's known source quantities.
    /// # Panics
    /// Only if the private complete-counterpart construction invariant is violated.
    #[must_use]
    pub fn counterpart(&self, id: ForeignCounterpart) -> &CounterpartReference {
        self.counterparts
            .iter()
            .find(|row| row.id() == id)
            .expect("all twelve counterparts were admitted")
    }
    /// A dependency stays explicit even when its population is missing.
    /// # Panics
    /// Only if the private six-dependency construction invariant is violated.
    #[must_use]
    pub fn dependency(&self, id: UsDependency) -> &WorldMember {
        self.members
            .iter()
            .find(|row| row.scope() == WorldScope::Dependency(id))
            .expect("all six dependencies were admitted")
    }
    /// All known independent source persons, including the US context (not runtime ACS).
    #[must_use]
    pub const fn known_population_persons(&self) -> u64 {
        self.known_persons
    }
    /// Exact source pins; runtime approximations require their own captured policy.
    #[must_use]
    pub const fn source_digests(&self) -> WorldSourceDigests {
        DIGESTS
    }
}

/// Specific source admission refusals; there is no partial-world fallback.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WorldReferenceError {
    /// A compressed/decompressed/row bound was exceeded.
    Bound,
    /// Qualified source or policy bytes changed.
    ArtifactDigest,
    /// Gzip, UTF-8 or trailing compressed bytes are invalid.
    Compression,
    /// CSV column names or ordering changed.
    Header,
    /// A source record has malformed CSV or the wrong number of fields.
    CsvShape,
    /// Membership policy shape or identity is invalid.
    Membership,
    /// A row is duplicated, missing or outside strict source order.
    Coverage,
    /// A source membership or relationship is inconsistent.
    Scope,
    /// Population status, quantity or projection receipt is contradictory.
    Population,
    /// A parent is missing, non-independent or in another economic scope.
    ParentRelation,
    /// A trade direction's annual token contradicts its availability.
    Trade,
    /// An exact source subtotal cannot fit its numeric type.
    Arithmetic,
}
impl std::fmt::Display for WorldReferenceError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "world reference refused: {self:?}")
    }
}
impl std::error::Error for WorldReferenceError {}

/// Load the qualified source once; this does not initialize or fund foreign economies.
/// # Errors
/// Returns the exact source-admission failure without inferred replacements.
pub fn world_reference() -> Result<&'static WorldReference, WorldReferenceError> {
    REFERENCE
        .get_or_init(|| WorldReference::decode_pinned(POPULATION, TRADE))
        .as_ref()
        .map_err(|error| *error)
}

fn decode(bytes: &[u8]) -> Result<String, WorldReferenceError> {
    let mut decoder = flate2::bufread::GzDecoder::new(bytes);
    let mut text = String::new();
    decoder
        .by_ref()
        .take((MAX_DECODED_BYTES + 1) as u64)
        .read_to_string(&mut text)
        .map_err(|_| WorldReferenceError::Compression)?;
    if text.len() > MAX_DECODED_BYTES {
        return Err(WorldReferenceError::Bound);
    }
    if !decoder.into_inner().is_empty() {
        return Err(WorldReferenceError::Compression);
    }
    Ok(text)
}
