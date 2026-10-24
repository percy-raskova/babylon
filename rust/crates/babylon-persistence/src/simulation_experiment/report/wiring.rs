//! Captured selections and observed receipts, without inferring new mechanics.

#[cfg(test)]
mod tests;

#[path = "wiring/manifest.rs"]
mod manifest;

pub(super) use manifest::{capture, verify};
// Task 5 condition (b): the moved types stay reachable at their old wiring
// path even though this module is private and no in-tree caller names them yet.
#[allow(
    unused_imports,
    reason = "Task 5 condition (b): preserve the moved types' old module path"
)]
pub use manifest::{
    BslFamily, MaterialFamily, ReceiptCoverage, RuleAttribution, RuleExecution, WiringManifest,
};
