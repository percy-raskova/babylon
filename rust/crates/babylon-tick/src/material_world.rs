//! Exact successor world-register ownership for the routed material circuit.
//!
//! An active register contains the complete current opening state, never an economic
//! summary or a second inventory ledger. The graph-only digest stays unchanged.

mod agency_paid_receipt;
mod city_pd;
pub(crate) mod city_pd_execution;
mod county_review;
pub(crate) mod county_review_execution;
#[cfg(test)]
mod county_review_tests;

mod aid_receipt;

mod collection_receipt;

mod equipment_receipt;

mod basis_receipt;
mod financial_receipt;

mod household_time_receipt;
mod lifecycle_receipt;

#[cfg(test)]
mod household_time_tests;

mod income_receipt;

mod installation_decision;

mod maintenance_receipt;

mod monetary_receipt;

pub(crate) mod organizer_collection;

mod organizer_reports;
mod organizer_support;

mod organizer_time;

mod recurring_receipt;

mod service_receipt;

mod workforce_receipt;

#[cfg(test)]
mod tests;

mod receipt_format;
pub use receipt_format::MaterialReceiptFormat;
mod register;

pub use agency_paid_receipt::{validate_committed_nonpaid, AgencyPaidReceipt};
pub use city_pd::{
    CityPdAttempt, CityPdRegister, CityPdRegisterError, DecodedCityPdAttemptEvidence,
};
pub use county_review::{
    CountyGroupLabor, CountyLaborFacts, CountyReviewRegister, CountyReviewRegisterError,
};
use register::ReceiptCursor;
#[cfg(test)]
use register::{bounded_bytes, RECEIPT_DOMAIN};
pub use register::{
    decode_city_pd_attempt_evidence, decode_material_organizer_evidence, decode_material_receipts,
    encode_material_receipts, nominal_material_world_hash,
    nominal_material_world_hash_from_register_digest, receipt_row_limit,
    validate_retained_collection, DecodedMaterialOrganizerEvidence, MaterialReceiptHandle,
    MaterialTickReceipts, MaterialWorldError, MaterialWorldRegister, PreparedMaterialWorld,
    SharedCanonicalBytes, MAX_MATERIAL_TICK_RECEIPT_BYTES, MAX_MATERIAL_WORLD_REGISTER_BYTES,
    RECEIPT_FAMILY_COUNT, RECEIPT_ROW_BYTES,
};
