//! Exact resident staffing and attendance evidence in the existing tick envelope.

#[cfg(test)]
mod tests;

#[path = "workforce_receipt/codec.rs"]
mod codec;

pub(super) use codec::{
    decode_attendance, decode_staffing, encode_attendance, encode_staffing, validate_join,
    ATTENDANCE_BYTES, STAFFING_BYTES,
};

#[cfg(test)]
use babylon_kernel::currency::Currency;
#[cfg(test)]
use babylon_material_circuit::{
    FinalDemandPrincipalId, LaborCompensation, MemberLaborUseReceipt, SiteId,
    StaffingMemberBinding, StaffingMemberId, StaffingMemberReceipt, StaffingPoolId, UnitId,
};
