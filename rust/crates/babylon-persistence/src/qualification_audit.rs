//! Independent material evidence from the confined observer, never a game writer.
//! Each fold consumes the same authenticated receipts. Complete snapshots remain
//! with the caller and are borrowed, rather than retained or reconstructed here.

pub mod aid;

pub mod economic;

pub mod policy;

pub mod production_renewal;

pub mod reader;

pub mod trade;

#[cfg(test)]
mod tests;

#[path = "qualification_audit/audit.rs"]
mod audit;

use audit::hex;
pub use audit::{
    county_roster, BoundaryFacts, CountyRoster, MaterialAudit, ReceiptFacts, Refusal, RenewalFacts,
    Scope,
};
