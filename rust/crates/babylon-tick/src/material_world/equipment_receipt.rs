//! Exact bounded equipment receipt families; no absent-state assumptions.

#[cfg(test)]
mod tests;

mod join;

pub(super) use join::{validate_installation, validate_investment, validate_wear};

#[path = "equipment_receipt/codec.rs"]
mod codec;

pub(super) use codec::{
    decode_installation, decode_investment, decode_wear, encode_installation, encode_investment,
    encode_wear, validate_order, INSTALLATION_BYTES, INVESTMENT_BYTES, WEAR_BYTES,
};

use super::MaterialWorldError;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{EquipmentWearReceipt, InstallationReceipt, InvestmentReceipt};
