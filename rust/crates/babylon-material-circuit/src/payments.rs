//! Funded attendance and physical delivery share the material close.

mod attendance;

pub(crate) use attendance::{fund_attendance, AttendanceLedger, LaborUse};

pub use attendance::{
    member_shift_id, EmploymentTerms, LaborCompensation, LaborUseReceipt, MemberLaborUseReceipt,
};

#[path = "payments/settlement.rs"]
mod settlement;

pub use settlement::{
    admit_material_purchase, CircuitAccounting, MaterialPurchase, MonetaryCircuit,
    MAX_MONEY_TRANSFERS_PER_PERIOD,
};
pub(crate) use settlement::{canonicalize, conserved, settle_deliveries, validate};
