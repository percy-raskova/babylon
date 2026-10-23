//! Captured selections and observed receipts, without inferring new mechanics.

#[cfg(test)]
mod tests;

#[path = "wiring/manifest.rs"]
mod manifest;

#[allow(unused_imports)]
use manifest::{
    attribution, audit_coverage, count, counters, effect_name, evidence_name, material_families,
    role_name, selected_families,
};
#[allow(unused_imports)]
pub(super) use manifest::{capture, verify};
#[allow(unused_imports)]
pub use manifest::{
    BslFamily, MaterialFamily, ReceiptCoverage, RuleAttribution, RuleExecution, WiringManifest,
};

#[allow(unused_imports)]
use super::{ExperimentError, Result, StaffingEvidence};
#[allow(unused_imports)]
use crate::material_runtime::MaterialRuntimeFoundation;
#[allow(unused_imports)]
use babylon_bsl::causal_contract::{
    check_rule_contract, effect_footprint, EffectSignature, EvidenceClass, RuleRole, ShapeVerb,
    GOVERNED_RULE_ATTRIBUTIONS,
};
#[allow(unused_imports)]
use babylon_bsl::rule_pipeline::split_content;
#[allow(unused_imports)]
use babylon_graph::stable_element::StableElementKey;
#[allow(unused_imports)]
use babylon_material_circuit::SupplierTransport;
#[allow(unused_imports)]
use babylon_tick::{
    material_staffing::{STAFFING_COMPOSITION_ID, STAFFING_FIELDS},
    material_world::MaterialTickReceipts,
    TickReport,
};
#[allow(unused_imports)]
use serde::Serialize;
#[allow(unused_imports)]
use std::collections::BTreeMap;
