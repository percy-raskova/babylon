//! Physical identities and exact lower-bound labor amounts for one authenticated close.
use babylon_material_circuit::{
    EquipmentCohortId, FinalDemandPrincipalId, FreightLotId, GoodId, InstallationId, ProcessId,
    SiteId, UnitId,
};
use serde::{Serialize, Serializer};
use std::fmt::{Display, Formatter, Result as FmtResult, Write};

pub const MICROS_PER_HOUR: u128 = 1_000_000;
/// One unit of opening stock in the second run, as hours are counted: a millionth is the smallest share.
pub const MICROS_PER_UNIT: u128 = 1_000_000;

fn decimal<T: Display, S: Serializer>(value: &T, serializer: S) -> Result<S::Ok, S::Error> {
    serializer.collect_str(value)
}

fn digest_hex(bytes: &[u8]) -> String {
    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(&mut output, "{byte:02x}").expect("String write");
    }
    output
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
    /// The sum of two bases; unknown if either is.
    ///
    /// # Errors
    /// `Arithmetic` when the hours overflow.
    #[allow(
        clippy::should_implement_trait,
        reason = "the sum can fail, so it is not `std::ops::Add`"
    )]
    pub fn add(self, rhs: Self) -> Result<Self, RecordedLaborError> {
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
        serializer.serialize_str(&digest_hex(&self.0))
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
    #[must_use]
    pub fn site(site: SiteId, good: GoodId, unit: UnitId) -> Self {
        Self::SiteStock {
            site: LaborId(site.as_bytes()),
            good: LaborId(good.as_bytes()),
            unit: LaborId(unit.as_bytes()),
        }
    }
    #[must_use]
    pub fn household(household: FinalDemandPrincipalId, good: GoodId, unit: UnitId) -> Self {
        Self::HouseholdStock {
            household: LaborId(household.as_bytes()),
            good: LaborId(good.as_bytes()),
            unit: LaborId(unit.as_bytes()),
        }
    }
    #[must_use]
    pub fn process(id: ProcessId) -> Self {
        Self::Process {
            process: LaborId(id.as_bytes()),
        }
    }
    #[must_use]
    pub fn work(site: SiteId, unit: UnitId) -> Self {
        Self::Work {
            site: LaborId(site.as_bytes()),
            unit: LaborId(unit.as_bytes()),
        }
    }
    #[must_use]
    pub fn freight(id: FreightLotId) -> Self {
        Self::Freight {
            lot: LaborId(id.as_bytes()),
        }
    }
    #[must_use]
    pub fn installation(id: InstallationId) -> Self {
        Self::Installation {
            installation: LaborId(id.as_bytes()),
        }
    }
    #[must_use]
    pub fn equipment(id: EquipmentCohortId) -> Self {
        Self::Equipment {
            cohort: LaborId(id.as_bytes()),
        }
    }
    #[must_use]
    pub fn maintenance(id: ProcessId) -> Self {
        Self::Maintenance {
            process: LaborId(id.as_bytes()),
        }
    }
    #[must_use]
    pub fn household_work(id: FinalDemandPrincipalId, unit: UnitId) -> Self {
        Self::HouseholdWork {
            household: LaborId(id.as_bytes()),
            unit: LaborId(unit.as_bytes()),
        }
    }
    #[must_use]
    pub fn sink(purpose: LaborDisposition) -> Self {
        Self::Sink { purpose }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct ReceiptRef {
    pub family: LaborReceiptFamily,
    pub ordinal: usize,
}
impl ReceiptRef {
    #[must_use]
    pub fn new(family: LaborReceiptFamily, ordinal: usize) -> Self {
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
