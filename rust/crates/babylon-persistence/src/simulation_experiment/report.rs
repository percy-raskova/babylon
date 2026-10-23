//! Read mechanical receipts, verify replay/accounting, and emit evaluator inputs.

mod wiring;

pub use wiring::{ReceiptCoverage, RuleExecution, WiringManifest};

#[path = "report/model.rs"]
mod model;

#[allow(unused_imports)]
use model::{
    captured_employment_subjects, captured_process_keys, initial_report, mass, month_days,
    observations, period_evidence, prepare, publish, qualify_activity, staffing, total,
};
pub use model::{
    date_after, historical_freight_good, run, CapturedSetup, EmploymentObservation,
    ExperimentMetadata, ExperimentRun, ExperimentTrajectory, FreightObservation, PeriodEvidence,
    ProductionEvidence, StaffingEvidence,
};

#[allow(unused_imports)]
use super::{
    hex, product, sum, ExperimentError, ExperimentProfile, Result, SimulationExperimentV1,
    StartingSnapshot,
};
#[allow(unused_imports)]
use babylon_bsl::{identity_codec::StableBslValue, structural_verbs::CollectingSink};
#[allow(unused_imports)]
use babylon_graph::{hypergraph_store::HypergraphStore, stable_element::StableElementKey};
#[allow(unused_imports)]
use babylon_material_circuit::{GoodId, MaterialCircuitState, ProcessId};
#[allow(unused_imports)]
use babylon_practice_contract::OrderedPracticeActionBatch;
#[allow(unused_imports)]
use babylon_tick::{
    material_replay::{MaterialReplaySession, PreparedMaterialTick},
    material_world::{decode_material_receipts, MaterialWorldRegister},
    replay_session::ReplayCommitDisposition,
};
#[allow(unused_imports)]
use serde::Serialize;
#[allow(unused_imports)]
use std::collections::BTreeMap;
