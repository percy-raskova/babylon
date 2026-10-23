//! Exact bounded equipment receipt families; no absent-state assumptions.

#[cfg(test)]
mod tests;

mod join;

pub(super) use join::{validate_installation, validate_investment, validate_wear};

#[path = "equipment_receipt/codec.rs"]
mod codec;

#[allow(unused_imports)]
pub(super) use codec::{
    decode_installation, decode_investment, decode_wear, encode_installation, encode_investment,
    encode_wear, validate_order, INSTALLATION_BYTES, INVESTMENT_BYTES, WEAR_BYTES,
};

#[allow(unused_imports)]
use super::{MaterialWorldError, ReceiptCursor};
#[allow(unused_imports)]
use babylon_kernel::currency::Currency;
#[allow(unused_imports)]
use babylon_material_circuit::{
    EquipmentCohortId, EquipmentWearReceipt, InstallationId, InstallationReceipt,
    InvestmentReceipt, OrderId, ProcessId, SiteId,
};
#[allow(unused_imports)]
use std::collections::BTreeSet;
