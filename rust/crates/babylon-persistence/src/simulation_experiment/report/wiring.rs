//! Captured selections and observed receipts, without inferring new mechanics.

#[cfg(test)]
mod tests;

#[path = "wiring/manifest.rs"]
mod manifest;

#[cfg(test)]
use manifest::count;
pub(super) use manifest::{capture, verify};
pub use manifest::{ReceiptCoverage, RuleExecution, WiringManifest};

#[cfg(test)]
use super::{ExperimentError, StaffingEvidence};
#[cfg(test)]
use babylon_bsl::causal_contract::{EffectSignature, EvidenceClass};
#[cfg(test)]
use babylon_tick::material_staffing::STAFFING_FIELDS;
#[cfg(test)]
use babylon_tick::material_world::MaterialTickReceipts;
#[cfg(test)]
use babylon_tick::TickReport;
