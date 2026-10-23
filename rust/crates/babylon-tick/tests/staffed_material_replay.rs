//! Graph-owned people and physical hours cross one real replay publication boundary.
//! This is a Designed circuit fixture, not admission of current Michigan content.

#[allow(
    dead_code,
    reason = "reuse the checked foundation loader, as replay_session does"
)]
#[path = "../../babylon-persistence/src/michigan_dynamic_hex_foundation.rs"]
mod michigan_dynamic_hex_foundation;

#[path = "staffed_material_replay/recurring.rs"]
mod recurring;

#[path = "staffed_material_replay/financial.rs"]
mod financial;

#[path = "staffed_material_replay/support.rs"]
mod support;

#[allow(unused_imports)]
use support::{
    admitted_checkpoint_refusal_preserves_both_owners_and_valid_retry_replays, advance,
    assert_people, assert_stock, authored_cycle_fires_once_and_retains_the_current_physical_result,
    commit, duplicate_authored_cycles_refuse_in_both_source_orders,
    failing_later_rule_aborts_staffing_physical_close_events_and_both_clocks, good,
    graph_diagnostic_refuses_material_execution_but_reports_its_fuel, install_freight, labor,
    later_anchored_rule_reads_this_candidates_staffing_before_graph_finalization, live,
    material_session_requires_an_authored_cycle,
    one_empty_period_holds_then_releases_and_real_arrival_rehires_for_next_period, opening,
    owned_checkpoint_rows, paid_material, paid_session, prepare,
    prepared_and_failed_commit_publish_nothing_and_retry_has_identical_joint_identity, process,
    removing_the_staffed_subject_is_refused_by_the_existing_shape_verb_loader, resident_member,
    same_version_checkpoint_restores_retention_and_replays_arrival_with_identical_evidence,
    session, site, source_order_cannot_change_material_execution_or_joint_identity,
    staffed_admission_refuses_every_native_field_in_early_late_and_untaken_writes, staffed_labor,
    staffing_field, subject,
    successful_acknowledgement_publishes_stable_staffing_and_identity_free_audit_evidence,
    try_session, try_session_with_authored_rules, try_session_with_material, unit,
    wage_and_dispatch_candidate_is_atomic_and_restarts_through_paid_arrival, Candidate, LiveState,
    Session, FAILURE, MATERIAL_CYCLE, SCENARIO, WITNESS,
};

#[allow(unused_imports)]
use babylon_bsl::canonical_ast::rules_hash_of;
#[allow(unused_imports)]
use babylon_bsl::causal_contract::{EffectSignature, EvidenceClass, RuleRole};
#[allow(unused_imports)]
use babylon_bsl::evaluator::Value;
#[allow(unused_imports)]
use babylon_bsl::identity_codec::StableBslValue;
#[allow(unused_imports)]
use babylon_bsl::rule_pipeline::split_content;
#[allow(unused_imports)]
use babylon_bsl::structural_verbs::CollectingSink;
#[allow(unused_imports)]
use babylon_graph::hypergraph_store::HypergraphStore;
#[allow(unused_imports)]
use babylon_graph::stable_element::StableElementKey;
#[allow(unused_imports)]
use babylon_graph::state_hash::CanonicalState;
#[allow(unused_imports)]
use babylon_graph::substrate::GraphSubstrate;
#[allow(unused_imports)]
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
#[allow(unused_imports)]
use babylon_kernel::tick_content_hash::RefDigest;
#[allow(unused_imports)]
use babylon_kernel::{content_digest::sha256_of, content_digest::ContentDigest};
#[allow(unused_imports)]
use babylon_material_circuit::{
    BacklogRow, CapacityRow, CommodityDefinition, CorridorCapacity, CorridorId, GoodId,
    InputOutputCoefficient, InventoryRow, LaborCapacityRow, LaborCoefficient, LogisticsNodeId,
    MaterialCircuitState, OrderAccessMode, OrderId, OrderRow, ProcessId, ProcessOutput, RouteId,
    RouteStage, RouteStageCapacity, SiteId, SiteLogisticsNode, StaffingPolicy, StaffingPoolBinding,
    StaffingPoolId, StaffingWorkSource, SupplierRoute, SupplierTransport, UnitId,
};
#[allow(unused_imports)]
use babylon_practice_contract::OrderedPracticeActionBatch;
#[allow(unused_imports)]
use babylon_tick::h3_runtime::MichiganDynamicHexValueBits;
#[allow(unused_imports)]
use babylon_tick::material_replay::{
    IdentifiedMaterialTick, MaterialBaseError, MaterialCommitError, MaterialReplayError,
    MaterialReplaySession, PreparedMaterialTick,
};
#[allow(unused_imports)]
use babylon_tick::material_staffing::{
    StaffingComposition, StaffingMemberNodeBinding, StaffingNodeBinding, EMPLOYED_POPULATION,
    PREVIOUS_UNRETAINED_HOURS, RESERVE_POPULATION, STAFFING_COMPOSITION_ID, STAFFING_FIELDS,
};
#[allow(unused_imports)]
use babylon_tick::material_state::{
    DynamicHexStateRow, MaterialState, MaterialStateRows, MaterialStateRowsInput,
    OrganizationStateRow, TerritoryStateRow, WorldRegisterRow,
};
#[allow(unused_imports)]
use babylon_tick::material_world::{
    decode_material_receipts, MaterialTickReceipts, MaterialWorldRegister,
};
#[allow(unused_imports)]
use babylon_tick::replay_session::{ReplayCommitDisposition, ReplayTickError, ReplayTickSession};
