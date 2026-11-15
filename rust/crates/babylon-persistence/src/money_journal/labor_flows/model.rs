//! Exact recorded time and unresolved prehistory in immediate movements from the trace.
use serde::{Deserialize, Serialize};

/// A recorded part and the number of transfers that also contain unknown earlier work.
/// Positive movement counts can have zero recorded hours.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LaborAmount {
    pub recorded_micro_hours: String,
    pub unknown_basis_movements: String,
    pub movement_count: String,
}

/// An immediate transfer contributes to each external endpoint and once inside a known group.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LaborDirections {
    pub inbound: LaborAmount,
    pub outbound: LaborAmount,
    pub within: LaborAmount,
    /// The signed difference of recorded components. Missing prehistory can affect either side.
    pub net_recorded_micro_hours: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LaborFlowRow {
    pub key: Option<String>,
    pub label: Option<String>,
    pub rank: Option<u64>,
    pub groups: u64,
    pub current: LaborDirections,
    pub comparison: Option<LaborDirections>,
    pub net_change_recorded_micro_hours: Option<String>,
}

/// Recorded labor held at a single period boundary. Earlier unmeasured labor is never assigned hours.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct LaborCarryAmount {
    pub recorded_micro_hours: u128,
    pub positions: u64,
    pub unknown_positions: u64,
}

/// Distinct boundary balances across all holdings with this captured county location.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct CountyLaborCarry {
    pub opening: LaborCarryAmount,
    pub closing: LaborCarryAmount,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LaborFlowPage {
    /// Available with a single-period, county-focused observer frame, independently of its ranked movements.
    #[serde(skip)]
    pub county_carry: Option<CountyLaborCarry>,
    pub groups: Vec<LaborFlowRow>,
    pub remainder: LaborFlowRow,
    pub total: LaborFlowRow,
}
