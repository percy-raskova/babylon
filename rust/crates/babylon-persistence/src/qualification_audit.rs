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

pub use audit::{
    county_roster, BoundaryFacts, CountyRoster, MaterialAudit, ReceiptFacts, Refusal, RenewalFacts,
    Scope,
};
#[allow(unused_imports)]
use audit::{hex, validate_production};

#[allow(unused_imports)]
use crate::{
    identity::CampaignId, observer_reader::CommittedMaterialObservation,
    production_observation::ProductionSnapshot,
};
#[allow(unused_imports)]
use babylon_kernel::economic_location::EconomicLocation;
#[allow(unused_imports)]
use babylon_tick::{
    material_replay::IdentifiedMaterialTick,
    material_world::{nominal_material_world_hash, MaterialWorldRegister},
};
#[allow(unused_imports)]
use serde::Serialize;
#[allow(unused_imports)]
use serde_json::Value;
#[allow(unused_imports)]
use sha2::{Digest, Sha256};
#[allow(unused_imports)]
use std::collections::BTreeSet;
