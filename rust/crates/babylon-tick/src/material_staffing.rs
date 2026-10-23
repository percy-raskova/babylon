//! The admitted G4 workforce composition's exact graph effects.
//!
//! Staffing state is a transient projection of the supplied detached graph.
//! This module neither owns durable state nor publishes a tick. A caller must
//! discard its entire candidate if an effect or a later tick stage refuses.

mod bindings;

pub use bindings::{StaffingComposition, StaffingMemberNodeBinding, StaffingNodeBinding};

#[cfg(test)]
mod tests;

#[path = "material_staffing/composition.rs"]
mod composition;

pub use composition::{
    apply_material_staffing, validate_opening_labor, MaterialStaffingError, StaffingEffectContext,
    StaffingEffects, EMPLOYED_POPULATION, MAX_EXACT_STAFFING_INTEGER, PREVIOUS_UNRETAINED_HOURS,
    RESERVE_POPULATION, STAFFING_COMPOSITION_ID, STAFFING_FIELDS,
};
#[allow(unused_imports)]
use composition::{
    exact_real, prepare_effects, read_opening, read_stock, reserved, resolve_node, staffing_event,
    typed_write, validate_fields, OpeningStaffing, PreparedEffects,
};

#[allow(unused_imports)]
use crate::committed_event::CommittedEvent;
#[allow(unused_imports)]
use babylon_bsl::causal_contract::{
    reduce_audit_receipts, AuditReceipt, ContractError, EvidenceClass, RuleContract, RuleRole,
};
#[allow(unused_imports)]
use babylon_bsl::evaluator::{EvalCode, EvalError, Value};
#[allow(unused_imports)]
use babylon_bsl::identity_codec::{project_stored_field_value, IdentityCodecError, StableBslValue};
#[allow(unused_imports)]
use babylon_bsl::structural_verbs::{
    EffectExecutor, PendingWrite, UpdateOp, WriteOperand, WriteTarget,
};
#[allow(unused_imports)]
use babylon_bsl::typecheck::TypeEnv;
#[allow(unused_imports)]
use babylon_bsl::types::{BslType, EnumRegistry, FieldKind};
#[allow(unused_imports)]
use babylon_bsl::write_log::{CollectingWriteLog, WriteRecord};
#[allow(unused_imports)]
use babylon_graph::stable_element::{StableElementKey, StableElementResolver, StableIdentityError};
#[allow(unused_imports)]
use babylon_graph::substrate::{GraphError, GraphSubstrate, NodeId};
#[allow(unused_imports)]
use babylon_material_circuit::{
    advance_staffing, distribute_staffing_members, LaborCapacityRow, MemberLaborCapacityRow,
    StaffingError, StaffingMemberReceipt, StaffingMemberState, StaffingPoolState, StaffingReceipt,
    StaffingState, StaffingWorkRequest,
};
#[allow(unused_imports)]
use std::collections::BTreeMap;
