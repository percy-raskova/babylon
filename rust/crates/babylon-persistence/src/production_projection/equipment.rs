//! Asset receipts reconcile physical instruments and work in progress with adjacent books.
//! This validates actual movements without choosing installation or investment policy.
mod decisions;

mod installation;

mod wear;

#[path = "equipment/facts.rs"]
mod facts;

use facts::{add, add_cost, AssetBook, Result};
pub(super) use facts::{get, validate, Definitions, EquipmentFacts};

use super::ProductionProjectionError;
use babylon_material_circuit::{MaterialCircuitState, ProductiveEquipment};
use babylon_tick::material_world::MaterialTickReceipts;
