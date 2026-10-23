//! V17 identity of an already-authorized production presentation.
//!
//! Scope and the complete typed DTO are serialized as canonical JSON after the
//! fixed domain/version. True multisets sort; events, geometry vertices and each
//! route's physical edge sequence retain their semantic order. Serialization
//! streams into the hash with an explicit byte ceiling. V17 also binds residence
//! kinds without inventing ordinary households for collective residents, household
//! service needs and satisfaction, installation materials and work, and per-good
//! quotes with committed direct costs. It also binds household stocks, consumption,
//! bounded order history and resident staffing.
//! Locations keep their exact county, counterpart or dependency scope.
//! Household gift inflows, outflows and shared freight reservations stay separate
//! from purchases and commercial supplier orders.

#[cfg(test)]
mod tests;

#[path = "production_evidence/evidence.rs"]
mod evidence;

#[cfg(test)]
use evidence::{
    canonicalize_production, diagnostic_field_sizes, diagnostic_production_fields,
    diagnostic_value_bytes, encode_evidence, EvidenceScope, EvidenceWriter, DOMAIN,
    MAX_EVIDENCE_BYTES, MAX_ROWS, VERSION,
};
pub use evidence::{ProductionEvidenceDigest, ProductionEvidenceError};

#[cfg(test)]
use crate::observer_reader::{ObserverEconomySnapshot, ObserverVisibility};
#[cfg(test)]
use sha2::{Digest as _, Sha256};
#[cfg(test)]
use std::io::{self, Write};
