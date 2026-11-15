//! Physical identities and exact lower-bound labor amounts for one authenticated close.
use super::identities::RecordedAsset;
use babylon_material_circuit::{
    EquipmentCohortId, FinalDemandPrincipalId, FreightLotId, GoodId, InstallationId, ProcessId,
    SiteId, UnitId,
};
use serde::{Serialize, Serializer};
use std::fmt::{Display, Formatter, Result as FmtResult};

pub const MICROS_PER_HOUR: u128 = 1_000_000;

pub(super) fn decimal<T: Display, S: Serializer>(
    value: &T,
    serializer: S,
) -> Result<S::Ok, S::Error> {
    serializer.collect_str(value)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RecordedLaborError {
    FoundationRequired,
    CheckpointBinding,
    CheckpointDigest,
    CheckpointFormat,
    CheckpointVersion,
    DiscontinuousPeriod,
    InvalidAttendance,
    UnknownProcess,
    ReceiptMismatch(&'static str),
    QuantityMismatch,
    OpeningPositionMismatch,
    ClosingPositionMismatch,
    Conservation,
    Arithmetic,
}
impl Display for RecordedLaborError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        write!(f, "recorded labor projection refused: {self:?}")
    }
}
impl std::error::Error for RecordedLaborError {}

/// A positive foundation stock can contain additional hours of unknown provenance.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct LaborBasis {
    #[serde(serialize_with = "decimal")]
    pub recorded_micro_hours: u128,
    pub unknown_opening: bool,
}
impl LaborBasis {
    pub(super) fn add(self, rhs: Self) -> Result<Self, RecordedLaborError> {
        Ok(Self {
            recorded_micro_hours: self
                .recorded_micro_hours
                .checked_add(rhs.recorded_micro_hours)
                .ok_or(RecordedLaborError::Arithmetic)?,
            unknown_opening: self.unknown_opening || rhs.unknown_opening,
        })
    }
}

/// Exact engine identity rendered as canonical lower-case hex.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct LaborId(pub [u8; 32]);
impl Serialize for LaborId {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(&crate::michigan_economy::digest_hex(&self.0))
    }
}

/// Canonical array containing the source row. The ordinal refers to the authenticated period.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum LaborReceiptFamily {
    Production,
    Maintenance,
    Installation,
    EquipmentWear,
    Handling,
    Aid,
    Dispatches,
    Arrivals,
    Losses,
    LocalFulfillments,
    LocalTransfers,
    ServiceOutputs,
    ServicePerformance,
    HouseholdConsumption,
    HouseholdServices,
    HouseholdTime,
    MemberLaborUse,
    AgencyPaid,
    Collections,
}

/// A recorded terminal use or loss of physical carrying hours.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum LaborDisposition {
    AgencyObservation,
    AidFreightLoss,
    FinalDemandOutlay,
    FreightLoss,
    HouseholdConsumption,
    HouseholdServiceUse,
    MaintenanceExpiry,
    OrganizerCashCollection,
    UnallocatedServiceExpiry,
    UnusedServiceExpiry,
}

/// Employment relation captured in the attendance receipt.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RecordedCompensation {
    Wage,
    WorkingOwner,
    UnpaidFamily,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum LaborNode {
    SiteStock {
        site: LaborId,
        good: LaborId,
        unit: LaborId,
    },
    HouseholdStock {
        household: LaborId,
        good: LaborId,
        unit: LaborId,
    },
    Freight {
        lot: LaborId,
    },
    Equipment {
        cohort: LaborId,
    },
    Installation {
        installation: LaborId,
    },
    Process {
        process: LaborId,
    },
    Work {
        site: LaborId,
        unit: LaborId,
    },
    Maintenance {
        process: LaborId,
    },
    HouseholdWork {
        household: LaborId,
        unit: LaborId,
    },
    Sink {
        purpose: LaborDisposition,
    },
}
impl LaborNode {
    pub(super) fn site(site: SiteId, good: GoodId, unit: UnitId) -> Self {
        Self::SiteStock {
            site: LaborId(site.as_bytes()),
            good: LaborId(good.as_bytes()),
            unit: LaborId(unit.as_bytes()),
        }
    }
    pub(super) fn household(household: FinalDemandPrincipalId, good: GoodId, unit: UnitId) -> Self {
        Self::HouseholdStock {
            household: LaborId(household.as_bytes()),
            good: LaborId(good.as_bytes()),
            unit: LaborId(unit.as_bytes()),
        }
    }
    pub(super) fn process(id: ProcessId) -> Self {
        Self::Process {
            process: LaborId(id.as_bytes()),
        }
    }
    pub(super) fn work(site: SiteId, unit: UnitId) -> Self {
        Self::Work {
            site: LaborId(site.as_bytes()),
            unit: LaborId(unit.as_bytes()),
        }
    }
    pub(super) fn freight(id: FreightLotId) -> Self {
        Self::Freight {
            lot: LaborId(id.as_bytes()),
        }
    }
    pub(super) fn installation(id: InstallationId) -> Self {
        Self::Installation {
            installation: LaborId(id.as_bytes()),
        }
    }
    pub(super) fn equipment(id: EquipmentCohortId) -> Self {
        Self::Equipment {
            cohort: LaborId(id.as_bytes()),
        }
    }
    pub(super) fn maintenance(id: ProcessId) -> Self {
        Self::Maintenance {
            process: LaborId(id.as_bytes()),
        }
    }
    pub(super) fn household_work(id: FinalDemandPrincipalId, unit: UnitId) -> Self {
        Self::HouseholdWork {
            household: LaborId(id.as_bytes()),
            unit: LaborId(unit.as_bytes()),
        }
    }
    pub(super) fn sink(purpose: LaborDisposition) -> Self {
        Self::Sink { purpose }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct ReceiptRef {
    pub family: LaborReceiptFamily,
    pub ordinal: usize,
}
impl ReceiptRef {
    pub(super) fn new(family: LaborReceiptFamily, ordinal: usize) -> Self {
        Self { family, ordinal }
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct LaborEdge {
    pub source: LaborNode,
    pub destination: LaborNode,
    /// Native units of the source stock or hours for a direct-work posting.
    #[serde(serialize_with = "decimal")]
    pub quantity: u64,
    pub basis: LaborBasis,
    pub receipt: ReceiptRef,
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

/// A positive physical opening or closing balance. Site, household and freight quantities use
/// native goods units. Equipment and maintenance use remaining service batches. An installation
/// uses equipment units in progress.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct RecordedLaborPosition {
    pub node: LaborNode,
    #[serde(serialize_with = "decimal")]
    pub quantity: u64,
    pub basis: LaborBasis,
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
