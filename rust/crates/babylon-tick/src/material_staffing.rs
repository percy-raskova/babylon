//! The admitted G4 workforce composition's exact graph effects.
//!
//! Staffing state is a transient projection of the supplied detached graph.
//! This module neither owns durable state nor publishes a tick. A caller must
//! discard its entire candidate if an effect or a later tick stage refuses.

use std::collections::BTreeMap;

use babylon_bsl::causal_contract::{
    reduce_audit_receipts, AuditReceipt, ContractError, EvidenceClass, RuleContract, RuleRole,
};
use babylon_bsl::evaluator::{EvalCode, EvalError, Value};
use babylon_bsl::identity_codec::{project_stored_field_value, IdentityCodecError, StableBslValue};
use babylon_bsl::structural_verbs::{
    EffectExecutor, PendingWrite, UpdateOp, WriteOperand, WriteTarget,
};
use babylon_bsl::typecheck::TypeEnv;
use babylon_bsl::types::{BslType, EnumRegistry, FieldKind};
use babylon_bsl::write_log::{CollectingWriteLog, WriteRecord};
use babylon_graph::stable_element::{StableElementKey, StableElementResolver, StableIdentityError};
use babylon_graph::substrate::{GraphError, GraphSubstrate, NodeId};
use babylon_material_circuit::{
    advance_staffing, distribute_staffing_members, LaborCapacityRow, MemberLaborCapacityRow,
    StaffingError, StaffingMemberReceipt, StaffingMemberState, StaffingPoolState, StaffingReceipt,
    StaffingState, StaffingWorkRequest,
};

use crate::committed_event::CommittedEvent;

/// This identity's placement and content must be independently admitted by the caller.
pub const STAFFING_COMPOSITION_ID: &str = "g4-workforce-staffing";
/// Graph fields retain exact integers only through this inclusive boundary.
pub const MAX_EXACT_STAFFING_INTEGER: u64 = 1_u64 << 53;
/// Exact employed persons in the modeled site-bound pool.
pub const EMPLOYED_POPULATION: &str = "social-class/employed-population";
/// Exact reserve persons in that same closed pool.
pub const RESERVE_POPULATION: &str = "social-class/reserve-population";
/// Last period's actual unretained work request, never its retained maximum.
pub const PREVIOUS_UNRETAINED_HOURS: &str = "business/previous-unretained-labor-hours";
/// The composition's complete owned field set; member writes follow canonical identities.
pub const STAFFING_FIELDS: [&str; 3] = [
    EMPLOYED_POPULATION,
    RESERVE_POPULATION,
    PREVIOUS_UNRETAINED_HOURS,
];

/// Closed composition, graph projection and effect refusals.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MaterialStaffingError {
    EmptyBindings,
    InventoryHasLabor,
    NodeBinding,
    NodeOwner,
    DuplicateNode,
    ExactInteger,
    EvidenceInteger,
    FieldDeclaration(&'static str),
    FieldRead {
        field: &'static str,
        source: GraphError,
    },
    Graph(GraphError),
    Stable(StableIdentityError),
    StoredValue(IdentityCodecError),
    Core(StaffingError),
    Effect {
        code: Option<EvalCode>,
        message: String,
    },
    Audit(ContractError),
    Allocation,
    OpeningLabor,
}

impl std::fmt::Display for MaterialStaffingError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "material staffing refused: {self:?}")
    }
}
impl std::error::Error for MaterialStaffingError {}
impl From<StaffingError> for MaterialStaffingError {
    fn from(error: StaffingError) -> Self {
        Self::Core(error)
    }
}
impl From<StableIdentityError> for MaterialStaffingError {
    fn from(error: StableIdentityError) -> Self {
        Self::Stable(error)
    }
}
impl From<EvalError> for MaterialStaffingError {
    fn from(error: EvalError) -> Self {
        Self::Effect {
            code: error.code,
            message: error.message,
        }
    }
}

mod bindings;
pub use bindings::{StaffingComposition, StaffingMemberNodeBinding, StaffingNodeBinding};

/// Exact registries already owned by the prepared replay environment.
#[derive(Clone, Copy)]
pub struct StaffingEffectContext<'a> {
    pub types: &'a TypeEnv,
    pub enums: &'a EnumRegistry,
    pub resolver: &'a StableElementResolver,
}

/// Completed effects and evidence. Next labor rows remain a transient physical input.
#[derive(Debug)]
pub struct StaffingEffects {
    staffing_receipts: Vec<StaffingReceipt>,
    member_receipts: Vec<StaffingMemberReceipt>,
    next_member_labor: Vec<MemberLaborCapacityRow>,
    next_labor: Vec<LaborCapacityRow>,
    writes: Vec<WriteRecord>,
    audit_receipts: Vec<AuditReceipt>,
    committed_events: Vec<CommittedEvent>,
}
impl StaffingEffects {
    #[must_use]
    pub fn staffing_receipts(&self) -> &[StaffingReceipt] {
        &self.staffing_receipts
    }
    #[must_use]
    pub fn member_receipts(&self) -> &[StaffingMemberReceipt] {
        &self.member_receipts
    }
    #[must_use]
    pub fn next_member_labor(&self) -> &[MemberLaborCapacityRow] {
        &self.next_member_labor
    }
    #[must_use]
    pub fn next_labor(&self) -> &[LaborCapacityRow] {
        &self.next_labor
    }
    #[must_use]
    pub fn writes(&self) -> &[WriteRecord] {
        &self.writes
    }
    #[must_use]
    pub fn audit_receipts(&self) -> &[AuditReceipt] {
        &self.audit_receipts
    }
    /// Derive sink records from these events; never append a second independently built batch.
    #[must_use]
    pub fn committed_events(&self) -> &[CommittedEvent] {
        &self.committed_events
    }
}

fn reserved<T>(count: usize) -> Result<Vec<T>, MaterialStaffingError> {
    let mut values = Vec::new();
    values
        .try_reserve_exact(count)
        .map_err(|_| MaterialStaffingError::Allocation)?;
    Ok(values)
}

fn validate_fields(context: StaffingEffectContext<'_>) -> Result<(), MaterialStaffingError> {
    for field in STAFFING_FIELDS {
        if !context.types.fields.get(field).is_some_and(|declaration| {
            declaration.ty == BslType::Int && declaration.kind == FieldKind::Extensive
        }) {
            return Err(MaterialStaffingError::FieldDeclaration(field));
        }
    }
    Ok(())
}

fn resolve_node(
    graph: &impl GraphSubstrate,
    context: StaffingEffectContext<'_>,
    subject: &StableElementKey,
    kind: &str,
) -> Result<NodeId, MaterialStaffingError> {
    if !context.resolver.sealed_node_has_type(subject, kind)? {
        return Err(MaterialStaffingError::NodeOwner);
    }
    let StableElementKey::Node { local_name, .. } = subject else {
        return Err(MaterialStaffingError::NodeBinding);
    };
    let node = context.resolver.node_handle_by_local_name(local_name)?;
    if context.resolver.node_key(node)? != subject {
        return Err(MaterialStaffingError::NodeBinding);
    }
    if graph
        .node_type_of(node)
        .map_err(MaterialStaffingError::Graph)?
        != kind
    {
        return Err(MaterialStaffingError::NodeOwner);
    }
    Ok(node)
}

fn read_stock(
    graph: &impl GraphSubstrate,
    node: NodeId,
    field: &'static str,
    context: &StaffingEffectContext<'_>,
) -> Result<u64, MaterialStaffingError> {
    let declaration = context
        .types
        .fields
        .get(field)
        .ok_or(MaterialStaffingError::FieldDeclaration(field))?;
    let value = graph
        .node_attribute(node, field)
        .map_err(|source| MaterialStaffingError::FieldRead { field, source })?;
    let stable =
        project_stored_field_value(declaration, Some(value.to_bits()), None, context.enums)
            .map_err(MaterialStaffingError::StoredValue)?;
    let StableBslValue::Int(value) = stable else {
        return Err(MaterialStaffingError::FieldDeclaration(field));
    };
    u64::try_from(value).map_err(|_| MaterialStaffingError::ExactInteger)
}

fn exact_real(value: u64) -> Result<f64, MaterialStaffingError> {
    if value > MAX_EXACT_STAFFING_INTEGER {
        return Err(MaterialStaffingError::ExactInteger);
    }
    // Two exact u32 conversions avoid an unchecked integer-to-binary64 cast.
    let high = u32::try_from(value >> 32).map_err(|_| MaterialStaffingError::ExactInteger)?;
    let low = u32::try_from(value & u64::from(u32::MAX))
        .map_err(|_| MaterialStaffingError::ExactInteger)?;
    Ok(f64::from(high) * 4_294_967_296.0 + f64::from(low))
}

struct OpeningStaffing {
    state: StaffingState,
    workplaces: Vec<NodeId>,
    members: Vec<Vec<StaffingMemberState>>,
    member_nodes: Vec<Vec<NodeId>>,
}

fn read_opening(
    graph: &impl GraphSubstrate,
    context: StaffingEffectContext<'_>,
    composition: &StaffingComposition,
    period: u64,
) -> Result<OpeningStaffing, MaterialStaffingError> {
    if !composition.bindings().is_empty() {
        validate_fields(context)?;
    }
    let mut pools = reserved(composition.bindings().len())?;
    let mut workplaces = reserved(composition.bindings().len())?;
    let mut members = reserved(composition.bindings().len())?;
    let mut member_nodes = reserved(composition.bindings().len())?;
    for row in composition.bindings() {
        let workplace = resolve_node(graph, context, row.subject(), "BUSINESS")?;
        let mut states = reserved(row.members().len())?;
        let mut nodes = reserved(row.members().len())?;
        let (mut employed, mut reserve) = (0_u64, 0_u64);
        for member in row.members() {
            let node = resolve_node(graph, context, member.subject(), "SOCIAL_CLASS")?;
            let state = StaffingMemberState::try_new(
                member.member().clone(),
                read_stock(graph, node, EMPLOYED_POPULATION, &context)?,
                read_stock(graph, node, RESERVE_POPULATION, &context)?,
            )?;
            employed = employed
                .checked_add(state.employed())
                .ok_or(StaffingError::Arithmetic)?;
            reserve = reserve
                .checked_add(state.reserve())
                .ok_or(StaffingError::Arithmetic)?;
            states.push(state);
            nodes.push(node);
        }
        pools.push(StaffingPoolState::try_new(
            row.pool().clone(),
            employed,
            reserve,
            read_stock(graph, workplace, PREVIOUS_UNRETAINED_HOURS, &context)?,
        )?);
        workplaces.push(workplace);
        members.push(states);
        member_nodes.push(nodes);
    }
    Ok(OpeningStaffing {
        state: StaffingState::try_new(period, pools)?,
        workplaces,
        members,
        member_nodes,
    })
}

/// Authenticate material budgets against graph-owned opening people before cash moves.
/// # Errors
/// Refuses any aggregate/member hour mismatch, missing payee, or residence mismatch.
pub fn validate_opening_labor(
    graph: &impl GraphSubstrate,
    context: StaffingEffectContext<'_>,
    composition: &StaffingComposition,
    material: &babylon_material_circuit::MaterialCircuitState,
) -> Result<(), MaterialStaffingError> {
    use babylon_material_circuit::CircuitAccounting;
    let opening = read_opening(graph, context, composition, material.period)?;
    let mut expected = BTreeMap::new();
    let mut member_hours = BTreeMap::new();
    let mut member_bindings = BTreeMap::new();
    for (pool, members) in opening.state.pools().iter().zip(&opening.members) {
        let hours = pool
            .employed()
            .checked_mul(pool.binding().policy().hours_per_person())
            .ok_or(StaffingError::Arithmetic)?;
        expected.insert((pool.binding().site_id(), pool.binding().unit_id()), hours);
        for member in members {
            let id = member.binding().member_id();
            member_hours.insert(
                id,
                member
                    .employed()
                    .checked_mul(pool.binding().policy().hours_per_person())
                    .ok_or(StaffingError::Arithmetic)?,
            );
            member_bindings.insert(id, (pool.binding(), member.binding()));
        }
    }
    let actual: BTreeMap<_, _> = material
        .labor
        .iter()
        .filter(|r| r.period == material.period)
        .map(|r| ((r.site_id, r.unit_id), r.available))
        .collect();
    if expected != actual {
        return Err(MaterialStaffingError::OpeningLabor);
    }
    if let CircuitAccounting::Monetary(economy) = &material.accounting {
        let actual: BTreeMap<_, _> = economy
            .member_labor
            .iter()
            .filter(|r| r.period == material.period)
            .map(|r| (r.member_id, r.available_hours))
            .collect();
        if actual != member_hours || economy.employment.len() != member_bindings.len() {
            return Err(MaterialStaffingError::OpeningLabor);
        }
        let residents: BTreeMap<_, _> = material
            .final_demand_principals
            .iter()
            .map(|r| (r.id, r.location))
            .collect();
        for terms in &economy.employment {
            let (pool, member) = member_bindings
                .get(&terms.member_id)
                .ok_or(MaterialStaffingError::OpeningLabor)?;
            if (terms.site_id, terms.unit_id, terms.payee)
                != (pool.site_id(), pool.unit_id(), member.household_id())
                || residents.get(&terms.payee) != Some(&member.residence())
            {
                return Err(MaterialStaffingError::OpeningLabor);
            }
        }
    }
    Ok(())
}

fn staffing_event(
    node: NodeId,
    receipt: &StaffingReceipt,
) -> Result<CommittedEvent, MaterialStaffingError> {
    let fields = [
        ("period", receipt.period()),
        ("opening-employed", receipt.opening_employed()),
        ("opening-reserve", receipt.opening_reserve()),
        (
            "previous-unretained-hours",
            receipt.previous_unretained_hours(),
        ),
        (
            "current-unretained-hours",
            receipt.current_unretained_hours(),
        ),
        ("retained-hours", receipt.retained_hours()),
        ("target-employed", receipt.target_employed()),
        ("hires", receipt.hires()),
        ("separations", receipt.separations()),
        ("closing-employed", receipt.closing_employed()),
        ("closing-reserve", receipt.closing_reserve()),
        ("next-opening-hours", receipt.next_opening_hours()),
    ];
    let mut payload = reserved(fields.len() + 1)?;
    // This is a sealed reference, never an integer encoding of an allocation handle.
    // The normal replay event codec projects it through the same resolver.
    payload.push(("subject".to_owned(), Value::NodeRef(node)));
    for (name, value) in fields {
        payload.push((
            name.to_owned(),
            Value::Int(i64::try_from(value).map_err(|_| MaterialStaffingError::EvidenceInteger)?),
        ));
    }
    Ok(CommittedEvent::new(
        STAFFING_COMPOSITION_ID.to_owned(),
        None,
        "WORKFORCE_STAFFING".to_owned(),
        payload,
    ))
}

struct PreparedEffects {
    writes: Vec<PendingWrite>,
    events: Vec<CommittedEvent>,
    members: Vec<StaffingMemberReceipt>,
    next_member_labor: Vec<MemberLaborCapacityRow>,
}
fn prepare_effects(
    opening: &OpeningStaffing,
    receipts: &[StaffingReceipt],
) -> Result<PreparedEffects, MaterialStaffingError> {
    if opening.workplaces.len() != receipts.len() {
        return Err(MaterialStaffingError::NodeBinding);
    }
    let mut result = PreparedEffects {
        writes: vec![],
        events: vec![],
        members: vec![],
        next_member_labor: vec![],
    };
    for (index, receipt) in receipts.iter().enumerate() {
        result.writes.push(typed_write(
            opening.workplaces[index],
            PREVIOUS_UNRETAINED_HOURS,
            receipt.current_unretained_hours(),
        )?);
        result
            .events
            .push(staffing_event(opening.workplaces[index], receipt)?);
        let members = distribute_staffing_members(receipt, &opening.members[index])?;
        for (node, member) in opening.member_nodes[index].iter().zip(&members) {
            result.writes.push(typed_write(
                *node,
                EMPLOYED_POPULATION,
                member.closing_employed,
            )?);
            result.writes.push(typed_write(
                *node,
                RESERVE_POPULATION,
                member.closing_reserve,
            )?);
            result.next_member_labor.push(MemberLaborCapacityRow {
                member_id: member.member.member_id(),
                period: member
                    .period
                    .checked_add(1)
                    .ok_or(StaffingError::Arithmetic)?,
                available_hours: member.next_opening_hours,
            });
        }
        result.members.extend(members);
    }
    result
        .next_member_labor
        .sort_unstable_by_key(|r| (r.period, r.member_id));
    Ok(result)
}
fn typed_write(
    node: NodeId,
    field: &str,
    value: u64,
) -> Result<PendingWrite, MaterialStaffingError> {
    Ok(PendingWrite {
        target: WriteTarget::Node(node),
        field: field.to_owned(),
        op: UpdateOp::Set,
        operand: WriteOperand::Real(exact_real(value)?),
    })
}

/// Apply one workplace request-memory write and each member's two person-stock writes.
///
/// Every source read, core transition and output conversion finishes before the first write.
/// The caller must supply a detached candidate and discard it on any returned error. This
/// function makes no publication or durability claim and returns no persistent staffing owner.
/// # Errors
/// Refuses invalid declarations, ownership, numeric values, requests, core transitions or effects.
pub fn apply_material_staffing(
    graph: &mut impl GraphSubstrate,
    context: StaffingEffectContext<'_>,
    composition: &StaffingComposition,
    period: u64,
    requests: &[StaffingWorkRequest],
) -> Result<StaffingEffects, MaterialStaffingError> {
    let opening = read_opening(graph, context, composition, period)?;
    let transition = advance_staffing(&opening.state, requests)?;
    let prepared = prepare_effects(&opening, transition.receipts())?;
    let pending = prepared.writes;
    let committed_events = prepared.events;
    let mut staffing_receipts = reserved(transition.receipts().len())?;
    staffing_receipts.extend_from_slice(transition.receipts());
    let mut next_labor = reserved(transition.next_labor().len())?;
    next_labor.extend_from_slice(transition.next_labor());
    let mut log = CollectingWriteLog::new();
    log.records
        .try_reserve_exact(pending.len())
        .map_err(|_| MaterialStaffingError::Allocation)?;
    {
        let mut executor = EffectExecutor::observed(
            context.types,
            context.enums,
            STAFFING_COMPOSITION_ID,
            &mut log,
        );
        for write in &pending {
            executor
                .apply_pending_write(write, graph)
                .map_err(MaterialStaffingError::from)?;
        }
    }
    let event_types = committed_events
        .iter()
        .map(|event| event.event_type().to_owned())
        .collect::<Vec<_>>();
    let contract = RuleContract {
        rule_id: STAFFING_COMPOSITION_ID.to_owned(),
        role: RuleRole::Mechanic,
        evidence: EvidenceClass::Designed,
    };
    let audit_receipts = reduce_audit_receipts(&contract, &event_types, &log.records)
        .map_err(MaterialStaffingError::Audit)?;
    Ok(StaffingEffects {
        staffing_receipts,
        member_receipts: prepared.members,
        next_member_labor: prepared.next_member_labor,
        next_labor,
        writes: log.records,
        audit_receipts,
        committed_events,
    })
}

#[cfg(test)]
mod tests;
