//! Exact resident staffing and attendance evidence in the existing tick envelope.

#[cfg(test)]
mod tests;

#[path = "workforce_receipt/codec.rs"]
mod codec;

#[allow(unused_imports)]
use codec::{add_hours, add_member, currency, empty_aggregate, validate_wage};
#[allow(unused_imports)]
pub(super) use codec::{
    decode_attendance, decode_staffing, encode_attendance, encode_staffing, validate_join,
    ATTENDANCE_BYTES, STAFFING_BYTES,
};

#[allow(unused_imports)]
use super::{MaterialWorldError, ReceiptCursor};
#[allow(unused_imports)]
use babylon_kernel::{currency::Currency, economic_location::EconomicLocation};
#[allow(unused_imports)]
use babylon_material_circuit::{
    FinalDemandPrincipalId, LaborCompensation, MemberLaborUseReceipt, SiteId,
    StaffingMemberBinding, StaffingMemberId, StaffingMemberReceipt, StaffingPoolId, UnitId,
};
