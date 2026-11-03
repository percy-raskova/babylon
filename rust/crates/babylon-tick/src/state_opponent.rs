//! Private City PD selection over captured beliefs and cash only.
use babylon_graph::capacity::{Candidate, Capacity};
use babylon_graph::dossier::Dossier;
use babylon_graph::stable_element::{StableElementKey, StableElementResolver};
use babylon_graph::substrate::NodeId;
use babylon_kernel::content_digest;
use babylon_kernel::currency::Currency;
use babylon_practice_contract as practice_contract;
use babylon_practice_contract::{
    CityPdCase, CityPdCaseStatus, CityPdConfig, CityPdDecision, CityPdDecisionReceipt, CityPdError,
    CityPdIntent, CITY_PD_MAX_ROWS, CITY_PD_SCHEMA_VERSION,
};
use std::collections::{BTreeMap, BTreeSet};

/// The agency's private belief and retained last decision.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CityPdState {
    pub dossier: Dossier,
    pub cases: Vec<CityPdCase>,
    pub last_decision: Option<CityPdDecisionReceipt>,
}

/// Choose at most one visit from validated private inputs and captured bindings.
/// The campaign host authenticates the supplied semantic bindings.
///
/// # Errors
/// Returns a validation, identity, arithmetic, or capacity error for invalid inputs.
pub fn decide_city_pd(
    config: &CityPdConfig,
    state: &CityPdState,
    resolver: &StableElementResolver,
    bindings: &[(u64, StableElementKey)],
    available: Currency,
    period: u64,
) -> Result<CityPdDecisionReceipt, CityPdError> {
    practice_contract::validate_city_pd_config(config)?;
    let balance = available.micro_units();
    if balance < 0 {
        return Err(CityPdError::NegativeBalance);
    }
    if state.cases.len() > CITY_PD_MAX_ROWS {
        return Err(CityPdError::SizeLimit);
    }
    let bound_nodes = resolve_bindings(config.actor_id, &state.cases, resolver, bindings)?;
    let actor = bound_nodes[&config.actor_id].0;
    if state.dossier.owner() != actor {
        return Err(CityPdError::WrongOwner);
    }
    let mut case_ids = BTreeSet::new();
    let mut targets = BTreeMap::new();
    let mut ordered = BTreeMap::new();
    for case in &state.cases {
        practice_contract::validate_city_pd_case(case)?;
        if case.actor_id != config.actor_id {
            return Err(CityPdError::WrongOwner);
        }
        if case.county != config.county {
            return Err(CityPdError::CountyMismatch);
        }
        let (handle, key) = &bound_nodes[&case.subject_id];
        if !state.dossier.knows_node(*handle) {
            return Err(CityPdError::UnknownSubject);
        }
        if case.acquired_period > period {
            return Err(CityPdError::InvalidTiming);
        }
        if !case_ids.insert(case.case_id) {
            return Err(CityPdError::DuplicateCase);
        }
        ordered.insert(case.case_id, &case.status);
        if case.status == CityPdCaseStatus::Open {
            targets
                .entry(key.clone())
                .and_modify(|row: &mut (NodeId, u64, [u8; 32])| row.2 = row.2.min(case.case_id))
                .or_insert((*handle, case.subject_id, case.case_id));
        }
    }
    let digest = practice_contract::city_pd_config_digest(config)?;
    let basis = decision_basis(
        digest,
        config.actor_id,
        period,
        balance,
        &state.dossier,
        resolver,
        &ordered,
    )?;
    let decision = if targets.is_empty() {
        CityPdDecision::NoCases
    } else if balance < config.visit_cost_micros {
        CityPdDecision::NoFunds {
            available_micros: balance,
            required_micros: config.visit_cost_micros,
        }
    } else {
        let resolve_period = period.checked_add(1).ok_or(CityPdError::Arithmetic)?;
        let &(target, subject_id, case_id) =
            targets.values().next().ok_or(CityPdError::Capacity)?;
        select_target(actor, target, config.visit_cost_micros, balance)?;
        let mut intent = CityPdIntent {
            intent_id: [0; 32],
            schema_version: CITY_PD_SCHEMA_VERSION,
            campaign_id: config.campaign_id,
            actor_id: config.actor_id,
            authority_id: config.authority_id,
            config_digest: digest,
            decision_basis_digest: basis,
            case_id,
            subject_id,
            source_period: period,
            resolve_period,
            cost_micros: config.visit_cost_micros,
        };
        intent.intent_id = practice_contract::city_pd_intent_id(&intent)?;
        CityPdDecision::Selected(intent)
    };
    let mut receipt = CityPdDecisionReceipt {
        decision_id: [0; 32],
        campaign_id: config.campaign_id,
        actor_id: config.actor_id,
        period,
        decision_basis_digest: basis,
        decision,
    };
    receipt.decision_id = practice_contract::city_pd_decision_id(&receipt)?;
    Ok(receipt)
}
type BoundNodes = BTreeMap<u64, (NodeId, Vec<u8>)>;

fn resolve_bindings(
    actor_id: u64,
    cases: &[CityPdCase],
    resolver: &StableElementResolver,
    bindings: &[(u64, StableElementKey)],
) -> Result<BoundNodes, CityPdError> {
    let mut relevant = BTreeSet::from([actor_id]);
    relevant.extend(cases.iter().map(|case| case.subject_id));
    let mut bound_nodes = BTreeMap::new();
    let mut handles = BTreeMap::new();
    for (id, key) in bindings {
        if !relevant.contains(id) {
            continue;
        }
        resolver
            .validate_sealed_key(key)
            .map_err(|_| CityPdError::InvalidIdentity)?;
        let StableElementKey::Node { local_name, .. } = key else {
            return Err(CityPdError::InvalidIdentity);
        };
        let handle = resolver
            .node_handle_by_local_name(local_name)
            .map_err(|_| CityPdError::InvalidIdentity)?;
        let bytes = key
            .canonical_bytes()
            .map_err(|_| CityPdError::InvalidIdentity)?;
        if let Some(existing) = bound_nodes.get(id) {
            if existing != &(handle, bytes.clone()) {
                return Err(CityPdError::InvalidIdentity);
            }
        } else {
            if handles.insert(handle, *id).is_some() {
                return Err(CityPdError::InvalidIdentity);
            }
            bound_nodes.insert(*id, (handle, bytes));
        }
    }
    if bound_nodes.len() != relevant.len() {
        return Err(CityPdError::InvalidIdentity);
    }
    Ok(bound_nodes)
}
fn decision_basis(
    digest: [u8; 32],
    actor_id: u64,
    period: u64,
    balance: i128,
    dossier: &Dossier,
    resolver: &StableElementResolver,
    ordered: &BTreeMap<[u8; 32], &CityPdCaseStatus>,
) -> Result<[u8; 32], CityPdError> {
    let mut bytes = b"babylon.city-pd-decision-basis.v2\0".to_vec();
    bytes.extend_from_slice(&digest);
    bytes.extend_from_slice(&actor_id.to_be_bytes());
    bytes.extend_from_slice(&period.to_be_bytes());
    bytes.extend_from_slice(&balance.to_be_bytes());
    let mut scope = BTreeSet::new();
    for node in dossier.scope() {
        let key = resolver
            .node_key(node)
            .map_err(|_| CityPdError::InvalidIdentity)?;
        resolver
            .validate_sealed_key(key)
            .map_err(|_| CityPdError::InvalidIdentity)?;
        scope.insert(
            key.canonical_bytes()
                .map_err(|_| CityPdError::InvalidIdentity)?,
        );
    }
    bytes.extend_from_slice(
        &u32::try_from(scope.len())
            .map_err(|_| CityPdError::SizeLimit)?
            .to_be_bytes(),
    );
    for key in scope {
        bytes.extend_from_slice(
            &u32::try_from(key.len())
                .map_err(|_| CityPdError::SizeLimit)?
                .to_be_bytes(),
        );
        bytes.extend_from_slice(&key);
    }
    bytes.extend_from_slice(
        &u32::try_from(ordered.len())
            .map_err(|_| CityPdError::SizeLimit)?
            .to_be_bytes(),
    );
    for (id, status) in ordered {
        bytes.extend_from_slice(id);
        bytes.push(match *status {
            CityPdCaseStatus::Open => 1,
            CityPdCaseStatus::Closed => 2,
        });
    }
    Ok(content_digest::sha256_of(&bytes))
}
fn select_target(
    actor: NodeId,
    target: NodeId,
    cost: i128,
    balance: i128,
) -> Result<(), CityPdError> {
    let instrument = "city-pd-observation";
    let mut capacity = Capacity::new(actor);
    capacity
        .replenish(instrument, Currency::from_micro_units(balance.min(cost)))
        .map_err(|_| CityPdError::Capacity)?;
    let candidate = Candidate {
        actor,
        instrument: instrument.to_owned(),
        mode: "OBSERVE_PUBLIC_ACTIVITY".to_owned(),
        target,
        expected_yield: 1.0,
        cost: Currency::from_micro_units(cost),
    };
    let allocations = capacity
        .allocate(&[candidate])
        .map_err(|_| CityPdError::Capacity)?;
    if allocations
        .funded
        .first()
        .is_none_or(|allocation| allocation.candidate.target != target)
    {
        return Err(CityPdError::Capacity);
    }
    Ok(())
}
