//! Physical identities and exact lower-bound labor amounts for one authenticated close.
use super::identities::RecordedAsset;
use super::{LaborEdge, LaborId, ReceiptRef, RecordedLaborError, RecordedLaborPosition};
use serde::{Serialize, Serializer};
use std::fmt::Display;
use std::result::Result as StdResult;

/// A stored record's answer: its value or the ledger's refusal.
pub(super) type Result<T> = StdResult<T, RecordedLaborError>;

pub(super) fn decimal<T: Display, S: Serializer>(
    value: &T,
    serializer: S,
) -> StdResult<S::Ok, S::Error> {
    serializer.collect_str(value)
}

/// Employment relation captured in the attendance receipt.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RecordedCompensation {
    Wage,
    WorkingOwner,
    UnpaidFamily,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct RecordedAttendance {
    pub member: LaborId,
    pub site: LaborId,
    pub unit: LaborId,
    pub compensation: RecordedCompensation,
    #[serde(serialize_with = "decimal")]
    pub attended_hours: u64,
    #[serde(serialize_with = "decimal")]
    pub production_hours: u64,
    #[serde(serialize_with = "decimal")]
    pub maintenance_hours: u64,
    #[serde(serialize_with = "decimal")]
    pub handling_hours: u64,
    #[serde(serialize_with = "decimal")]
    pub installation_hours: u64,
    #[serde(serialize_with = "decimal")]
    pub idle_hours: u64,
    pub receipt: ReceiptRef,
}
/// Opening recorded hours plus direct work equal closing recorded hours plus releases.
/// Edges describe successive physical postings and should not be summed as new work.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct RecordedLaborPeriod {
    #[serde(serialize_with = "decimal")]
    pub period: u64,
    #[serde(serialize_with = "decimal")]
    pub opening_recorded_micro_hours: u128,
    #[serde(serialize_with = "decimal")]
    pub closing_recorded_micro_hours: u128,
    #[serde(serialize_with = "decimal")]
    pub direct_micro_hours: u128,
    #[serde(serialize_with = "decimal")]
    pub released_micro_hours: u128,
    pub opening_positions: Vec<RecordedLaborPosition>,
    pub closing_positions: Vec<RecordedLaborPosition>,
    pub assets: Vec<RecordedAsset>,
    pub edges: Vec<LaborEdge>,
    pub attendance: Vec<RecordedAttendance>,
    pub household_time: Vec<RecordedHouseholdTime>,
}

/// Captured household time partition. Unresolved time is a claim. Allocated routine work
/// has no product identified in the register, so it is reported separately from stock hours.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct RecordedHouseholdTime {
    pub household: LaborId,
    pub unit: LaborId,
    #[serde(serialize_with = "decimal")]
    pub endowment_hours: u64,
    #[serde(serialize_with = "decimal")]
    pub attended_hours: u64,
    #[serde(serialize_with = "decimal")]
    pub protected_hours: u64,
    #[serde(serialize_with = "decimal")]
    pub protected_unresolved_hours: u64,
    #[serde(serialize_with = "decimal")]
    pub unpaid_requested_hours: u64,
    #[serde(serialize_with = "decimal")]
    pub unpaid_allocated_hours: u64,
    #[serde(serialize_with = "decimal")]
    pub unpaid_unresolved_hours: u64,
    #[serde(serialize_with = "decimal")]
    pub contribution_available_hours: u64,
    pub receipt: ReceiptRef,
}
