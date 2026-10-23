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

#[allow(unused_imports)]
use evidence::{
    bound, canonicalize_production, check_bound, diagnostic_add_field, diagnostic_cardinalities,
    diagnostic_encoded_size, diagnostic_field_sizes, diagnostic_production_fields,
    diagnostic_validation, diagnostic_validation_refusal, diagnostic_value_bytes, encode_evidence,
    unique, validate_account_rows, validate_collection_bounds, validate_goods_prices,
    validate_household_services, validate_households, validate_identities, validate_maintenance,
    validate_member_identities, validate_route_identities, validate_source_contexts, BoundReason,
    CountingEvidenceWriter, EvidenceByteCounter, EvidenceScope, EvidenceWriter, Result, DOMAIN,
    MAX_EVIDENCE_BYTES, MAX_PHYSICAL_ROWS, MAX_ROWS, VERSION,
};
pub use evidence::{ProductionEvidenceDigest, ProductionEvidenceError};

#[allow(unused_imports)]
use crate::production_projection::diagnostics::{Stage, Timing};
#[allow(unused_imports)]
use crate::{
    observer_reader::ObserverEconomySnapshot, observer_reader::ObserverVisibility,
    production_observation::ProductionSnapshot,
};
#[allow(unused_imports)]
use serde::Serialize;
#[allow(unused_imports)]
use sha2::{Digest as _, Sha256};
#[allow(unused_imports)]
use std::{
    collections::BTreeSet,
    io::{self, BufWriter, Write},
};
