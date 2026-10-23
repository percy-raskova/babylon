//! Original accepted offers joined to authenticated material and practice evidence.
//! This observer cannot admit actions or infer political agreement from a gift.
#[cfg(test)]
mod controls;

mod postings;

mod practice;

pub use babylon_tick::material_world::MaterialWorldRegister;

#[path = "aid/audit.rs"]
mod audit;

use audit::{add, cash, one, Result, Terms};
pub use audit::{material_disclosure, Accepted, Audit, Boundary, Refusal, Summary};

#[cfg(test)]
use crate::observer_reader::CommittedMaterialReceipts;
#[cfg(test)]
use crate::runtime_session::OrganizerSnapshot;
#[cfg(test)]
use babylon_material_circuit::CircuitAccounting;
#[cfg(test)]
use babylon_practice_contract::{
    OrganizerAidKind, OrganizerChoice, OrganizerCommitment, OrganizerPreview,
};
