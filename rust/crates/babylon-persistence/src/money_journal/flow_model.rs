//! Version-one reporting interface for settled money. Missing dimension keys are explicit.
use super::JournalError;
use serde::{Deserialize, Serialize};
use std::cmp::Ordering;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum FlowGroup {
    Account,
    Location,
    Catchment,
    Industry,
}
impl FlowGroup {
    #[must_use]
    pub(super) const fn key(self) -> &'static str {
        match self {
            Self::Account => "account",
            Self::Location => "location",
            Self::Catchment => "catchment",
            Self::Industry => "industry",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct PeriodWindow {
    pub first: u64,
    pub last: u64,
}
impl PeriodWindow {
    pub(super) fn bounds(self) -> Result<(i64, i64), JournalError> {
        if self.first == 0 || self.last < self.first {
            return Err(JournalError::Range);
        }
        Ok((
            i64::try_from(self.first).map_err(|_| JournalError::Range)?,
            i64::try_from(self.last).map_err(|_| JournalError::Range)?,
        ))
    }
}

/// NAD83 longitude and latitude bounds. West greater than east crosses the date line.
#[derive(Debug, Clone, Copy, PartialEq, Serialize)]
pub struct FlowViewport {
    pub west: f64,
    pub south: f64,
    pub east: f64,
    pub north: f64,
}
impl FlowViewport {
    pub(super) fn coordinates(self) -> Result<Vec<f64>, JournalError> {
        if !(-180.0..=180.0).contains(&self.west)
            || !(-180.0..=180.0).contains(&self.east)
            || !(-90.0..=90.0).contains(&self.south)
            || !(-90.0..=90.0).contains(&self.north)
            || self.west.partial_cmp(&self.east) == Some(Ordering::Equal)
            || self.south >= self.north
        {
            return Err(JournalError::Range);
        }
        Ok(vec![self.west, self.south, self.east, self.north])
    }
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct FlowQuery {
    pub window: PeriodWindow,
    pub comparison: Option<PeriodWindow>,
    pub group: FlowGroup,
    /// When present, display counterparties of this grouping key.
    pub focus: Option<String>,
    /// Zero-based rank of the first group on this page of twenty.
    pub offset: u64,
    pub viewport_4269: Option<FlowViewport>,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
pub struct FlowAmounts {
    pub inflow_micros: String,
    pub outflow_micros: String,
    pub internal_micros: String,
    pub net_micros: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
pub struct FlowRow {
    pub key: Option<String>,
    pub label: Option<String>,
    pub rank: Option<u64>,
    /// Number of rank groups represented by this row, including an empty remainder.
    pub groups: u64,
    pub current: FlowAmounts,
    pub comparison: Option<FlowAmounts>,
    pub net_change_micros: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
pub struct FlowPage {
    pub groups: Vec<FlowRow>,
    pub remainder: FlowRow,
    pub total: FlowRow,
}
