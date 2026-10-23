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
#[allow(unused_imports)]
pub(crate) use settlement::{canonicalize, conserved, settle_deliveries, validate};
#[allow(unused_imports)]
use settlement::{
    labor_principals, validate_member_budgets, validate_opening_shifts, validate_purchase,
    validate_service_purchases,
};

#[allow(unused_imports)]
use crate::{
    AccountId, BacklogRow, FinalDemandOrder, MaterialCircuitError, MaterialCircuitState,
    MonetaryBook, MonetaryError, MoneyTransferReceipt, OrderRow, OutboundOrderId, PurchaseEscrow,
    ShiftState, SiteId, UnitId, MAX_MATERIAL_CIRCUIT_ROWS,
};
#[allow(unused_imports)]
use babylon_kernel::currency::Currency;
#[allow(unused_imports)]
use std::collections::BTreeSet;
