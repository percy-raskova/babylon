//! Canonical material receipt framing selected by the captured company policies.
use super::financial_receipt;
use super::register;
use super::register::{RECEIPT_DOMAIN, RECEIPT_FAMILY_COUNT, RECEIPT_ROW_BYTES};
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MaterialReceiptFormat {
    Site,
    Company,
}
const COMPANY_WIDTHS: [usize; RECEIPT_FAMILY_COUNT + 2] = {
    let mut result = [0; RECEIPT_FAMILY_COUNT + 2];
    let mut i = 0;
    while i < RECEIPT_FAMILY_COUNT {
        result[i] = RECEIPT_ROW_BYTES[i];
        i += 1;
    }
    result[RECEIPT_FAMILY_COUNT] = financial_receipt::COMPANY_BYTES;
    result[RECEIPT_FAMILY_COUNT + 1] = super::basis_receipt::WIDTH;
    result
};
impl MaterialReceiptFormat {
    #[must_use]
    pub const fn domain(self) -> &'static [u8] {
        match self {
            Self::Site => RECEIPT_DOMAIN,
            Self::Company => b"babylon.material-tick-receipts.v21\0",
        }
    }
    #[must_use]
    pub const fn version(self) -> u32 {
        match self {
            Self::Site => 20,
            Self::Company => 21,
        }
    }
    #[must_use]
    pub const fn widths(self) -> &'static [usize] {
        match self {
            Self::Site => &RECEIPT_ROW_BYTES,
            Self::Company => &COMPANY_WIDTHS,
        }
    }
    #[must_use]
    pub const fn maximum_bytes(self) -> usize {
        match self {
            Self::Site => register::maximum_material_receipt_bytes(),
            Self::Company => register::MAX_MATERIAL_TICK_RECEIPT_BYTES,
        }
    }
    #[must_use]
    pub fn identify(bytes: &[u8]) -> Option<Self> {
        [Self::Site, Self::Company]
            .into_iter()
            .find(|format| bytes.starts_with(format.domain()))
    }
}
