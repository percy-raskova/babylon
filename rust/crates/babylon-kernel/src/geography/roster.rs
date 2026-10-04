//! Exact source-vintage membership, independent of county syntax.
use super::{CountyGeoid, CountyJurisdiction};
use crate::content_digest::sha256_of;
use std::sync::Arc;

/// The qualified TIGER2024 fifty-state/DC county and county-equivalent count.
pub const NATIONAL_COUNTY_COUNT: usize = 3144;
// SHA-256 of the strictly ordered five-byte GEOIDs, each followed by LF.
const ROSTER_SHA256: [u8; 32] = [
    242, 101, 30, 198, 169, 55, 84, 118, 227, 255, 9, 239, 180, 194, 166, 153, 205, 86, 144, 255,
    211, 240, 201, 130, 174, 172, 173, 150, 124, 33, 194, 65,
];

/// An immutable, cheap-to-share proof of exact current domestic county membership.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NationalCountyRoster(Arc<[CountyGeoid]>);

/// Membership failures never repair, sort or invent a county.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum NationalCountyRosterError {
    /// The exact current roster is incomplete or oversized.
    Count {
        /// Supplied source row count.
        actual: usize,
    },
    /// Repeated or nonascending source identities.
    Order,
    /// A dependency or unknown jurisdiction was presented as domestic.
    Jurisdiction(CountyGeoid),
    /// The same-size roster differs from the independently pinned vintage.
    Digest,
}
impl NationalCountyRoster {
    /// Admit the exact ordered source roster, not merely valid GEOID syntax.
    /// # Errors
    /// Refuses incomplete, repeated, reordered, non-domestic or invented counties.
    pub fn try_new(counties: Vec<CountyGeoid>) -> Result<Self, NationalCountyRosterError> {
        if counties.len() != NATIONAL_COUNTY_COUNT {
            return Err(NationalCountyRosterError::Count {
                actual: counties.len(),
            });
        }
        if counties.windows(2).any(|pair| pair[0] >= pair[1]) {
            return Err(NationalCountyRosterError::Order);
        }
        let mut bytes = Vec::with_capacity(NATIONAL_COUNTY_COUNT * 6);
        for county in &counties {
            if !matches!(
                county.jurisdiction(),
                CountyJurisdiction::State | CountyJurisdiction::DistrictOfColumbia
            ) {
                return Err(NationalCountyRosterError::Jurisdiction(*county));
            }
            bytes.extend_from_slice(&county.as_bytes());
            bytes.push(b'\n');
        }
        if sha256_of(&bytes) != ROSTER_SHA256 {
            return Err(NationalCountyRosterError::Digest);
        }
        Ok(Self(counties.into()))
    }
    /// Borrow all admitted identities in exact source order.
    #[must_use]
    pub fn counties(&self) -> &[CountyGeoid] {
        &self.0
    }
    /// Test actual membership, independently of the caller's syntactic identity.
    #[must_use]
    pub fn contains(&self, county: CountyGeoid) -> bool {
        self.0.binary_search(&county).is_ok()
    }
    /// Exact semantic source-roster digest, distinct from any artifact gzip digest.
    #[must_use]
    pub const fn digest(&self) -> [u8; 32] {
        ROSTER_SHA256
    }
}
impl std::fmt::Display for NationalCountyRosterError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "national county roster refused: {self:?}")
    }
}
impl std::error::Error for NationalCountyRosterError {}
