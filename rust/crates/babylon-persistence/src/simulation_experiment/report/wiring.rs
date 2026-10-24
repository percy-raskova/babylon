//! Captured selections and observed receipts, without inferring new mechanics.

#[cfg(test)]
mod tests;

#[path = "wiring/manifest.rs"]
mod manifest;

pub(super) use manifest::{capture, verify};
pub use manifest::{ReceiptCoverage, RuleExecution, WiringManifest};
