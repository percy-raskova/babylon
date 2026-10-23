//! Asset receipts reconcile physical instruments and work in progress with adjacent books.
//! This validates actual movements without choosing installation or investment policy.
mod decisions;

mod installation;

mod wear;

#[path = "equipment/facts.rs"]
mod facts;

#[allow(unused_imports)]
use facts::{
    add, add_cost, asset_book, validate_capacity, AssetBook, LaborKey, MaterialKey, Result,
};
#[allow(unused_imports)]
pub(super) use facts::{get, validate, Definitions, EquipmentFacts};

#[allow(unused_imports)]
use super::ProductionProjectionError;
#[allow(unused_imports)]
use babylon_kernel::currency::Currency;
#[allow(unused_imports)]
use babylon_material_circuit::{
    CapacitySupply, CircuitAccounting, EquipmentAssetId, EquipmentBinding, EquipmentDefinition,
    EquipmentDefinitionId, GoodId, MaterialCircuitState, ProcessId, ProductiveEquipment,
    RollingProcessSupply, SiteId, UnitId,
};
#[allow(unused_imports)]
use babylon_tick::material_world::MaterialTickReceipts;
#[allow(unused_imports)]
use std::collections::BTreeMap;
