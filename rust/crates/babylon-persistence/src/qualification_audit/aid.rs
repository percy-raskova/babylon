//! Original accepted offers joined to authenticated material and practice evidence.
//! This observer cannot admit actions or infer political agreement from a gift.
#[cfg(test)]
mod controls;

mod postings;

mod practice;

pub use babylon_tick::material_world::MaterialWorldRegister;

#[path = "aid/audit.rs"]
mod audit;

#[allow(unused_imports)]
use audit::{add, cash, check_material, kind, one, terms, total, Result, Terms, Totals};
pub use audit::{material_disclosure, Accepted, Audit, Boundary, Refusal, Summary};

#[allow(unused_imports)]
use crate::{
    observer_reader::CommittedMaterialReceipts,
    runtime_session::{OrganizerMaterialAidPreview, OrganizerSnapshot},
};
#[allow(unused_imports)]
use babylon_material_circuit::{AidMandate, AidOutcome, AidReceipt, CircuitAccounting};
#[allow(unused_imports)]
use babylon_practice_contract::{
    organizer_resource_digest, validate_organizer_commitment, OrganizerAidBinding,
    OrganizerAidKind, OrganizerChoice, OrganizerCommitment, OrganizerConfig, OrganizerGiftConsent,
    OrganizerPreview,
};
#[allow(unused_imports)]
use babylon_tick::material_world::nominal_material_world_hash;
#[allow(unused_imports)]
use serde::Serialize;
#[allow(unused_imports)]
use serde_json::{json, Value};
#[allow(unused_imports)]
use std::collections::{BTreeMap, BTreeSet};
