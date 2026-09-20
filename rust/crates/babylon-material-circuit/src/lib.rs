//! Exact conserved production, inventory, order, and realization transitions.
//!
//! One transition closes one four-week period. Period ordinals advance by one;
//! content supplies capacities and labor schedules for the entire interval.
//! Inventories, people, order principals and per-batch recipes retain their units.
#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

mod accounts;
mod inventory;
mod maintenance;
mod model;
mod payments;
mod production;
mod staffing;
mod transition;
mod wire;

pub use accounts::{
    AccountId, CashAccount, CashTransferPurpose, FundedShift, MonetaryBook, MonetaryBookSnapshot,
    MonetaryError, MoneyLocation, MoneyPosting, MoneyTransferPurpose, MoneyTransferReceipt,
    OrganizationAccountId, PublicAccountId, PurchaseEscrow, PurchaseMovementReceipt, ShiftId,
    ShiftState, WageAccrualReceipt,
};
pub use model::*;
pub use payments::{
    admit_material_purchase, CircuitAccounting, EmploymentTerms, LaborUseReceipt, MaterialPurchase,
    MonetaryCircuit, MAX_MONEY_TRANSFERS_PER_PERIOD,
};
pub use staffing::{
    advance_staffing, StaffingError, StaffingPolicy, StaffingPoolBinding, StaffingPoolId,
    StaffingPoolState, StaffingReceipt, StaffingState, StaffingTransition, StaffingWorkRequest,
    StaffingWorkSource,
};

pub use transition::{advance_material_circuit, close_material_period, ClosedMaterialPeriod};
pub use wire::{
    decode_material_circuit_state, encode_material_circuit_state, material_circuit_state_digest,
    MATERIAL_CIRCUIT_SOURCE_SHA256, MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES,
};
