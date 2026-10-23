//! Read mechanical receipts, verify replay/accounting, and emit evaluator inputs.

mod wiring;

pub use wiring::{ReceiptCoverage, RuleExecution, WiringManifest};

#[path = "report/model.rs"]
mod model;

use model::total;
pub use model::{
    date_after, historical_freight_good, run, CapturedSetup, EmploymentObservation,
    ExperimentMetadata, ExperimentRun, ExperimentTrajectory, FreightObservation, PeriodEvidence,
    ProductionEvidence, StaffingEvidence,
};
#[cfg(test)]
use model::{prepare, staffing};

use super::{sum, ExperimentError, Result};
