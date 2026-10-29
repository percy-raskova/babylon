//! Private City PD selection over captured beliefs and cash only.
use babylon_graph::{
    capacity::{Candidate, Capacity},
    dossier::Dossier,
    substrate::NodeId,
};
use babylon_kernel::{content_digest::sha256_of, currency::Currency};
use babylon_practice_contract::{
    city_pd_config_digest, city_pd_decision_id, city_pd_intent_id, validate_city_pd_case,
    validate_city_pd_config, CityPdCase, CityPdCaseStatus, CityPdConfig, CityPdDecision,
    CityPdDecisionReceipt, CityPdError, CityPdIntent, CITY_PD_MAX_ROWS, CITY_PD_SCHEMA_VERSION,
};
use std::collections::{BTreeMap, BTreeSet};

/// The agency's private belief and retained last decision.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CityPdState {
    pub dossier: Dossier,
    pub cases: Vec<CityPdCase>,
    pub last_decision: Option<CityPdDecisionReceipt>,
}
/// Choose at most one visit from validated private inputs.
///
/// # Errors
/// Returns the specific validation, arithmetic, or capacity error for invalid inputs.
pub fn decide_city_pd(
    config: &CityPdConfig,
    state: &CityPdState,
    available: Currency,
    period: u64,
) -> Result<CityPdDecisionReceipt, CityPdError> {
    validate_city_pd_config(config)?;
    if state.dossier.owner() != NodeId(config.actor_id) {
        return Err(CityPdError::WrongOwner);
    }
    let balance = available.micro_units();
    if balance < 0 {
        return Err(CityPdError::NegativeBalance);
    }
    if state.cases.len() > CITY_PD_MAX_ROWS {
        return Err(CityPdError::SizeLimit);
    }
    let mut case_ids = BTreeSet::new();
    let mut targets = BTreeMap::new();
    let mut ordered = BTreeMap::new();
    for case in &state.cases {
        validate_city_pd_case(case)?;
        if case.actor_id != config.actor_id {
            return Err(CityPdError::WrongOwner);
        }
        if case.county != config.county {
            return Err(CityPdError::CountyMismatch);
        }
        if !state.dossier.knows_node(NodeId(case.subject_id)) {
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
                .entry(NodeId(case.subject_id))
                .and_modify(|id: &mut [u8; 32]| *id = (*id).min(case.case_id))
                .or_insert(case.case_id);
        }
    }
    let digest = city_pd_config_digest(config)?;
    let basis = decision_basis(
        digest,
        config.actor_id,
        period,
        balance,
        &state.dossier,
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
        let selected = select_target(config.actor_id, config.visit_cost_micros, balance, &targets)?;
        let mut intent = CityPdIntent {
            intent_id: [0; 32],
            schema_version: CITY_PD_SCHEMA_VERSION,
            campaign_id: config.campaign_id,
            actor_id: config.actor_id,
            authority_id: config.authority_id,
            config_digest: digest,
            decision_basis_digest: basis,
            case_id: targets[&selected],
            subject_id: selected.0,
            source_period: period,
            resolve_period,
            cost_micros: config.visit_cost_micros,
        };
        intent.intent_id = city_pd_intent_id(&intent)?;
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
    receipt.decision_id = city_pd_decision_id(&receipt)?;
    Ok(receipt)
}

fn decision_basis(
    digest: [u8; 32],
    actor_id: u64,
    period: u64,
    balance: i128,
    dossier: &Dossier,
    ordered: &BTreeMap<[u8; 32], &CityPdCaseStatus>,
) -> Result<[u8; 32], CityPdError> {
    let mut bytes = b"babylon.city-pd-decision-basis.v1\0".to_vec();
    bytes.extend_from_slice(&digest);
    bytes.extend_from_slice(&actor_id.to_be_bytes());
    bytes.extend_from_slice(&period.to_be_bytes());
    bytes.extend_from_slice(&balance.to_be_bytes());
    let scope = dossier.scope();
    bytes.extend_from_slice(
        &u32::try_from(scope.len())
            .map_err(|_| CityPdError::SizeLimit)?
            .to_be_bytes(),
    );
    for node in scope {
        bytes.extend_from_slice(&node.0.to_be_bytes());
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
    Ok(sha256_of(&bytes))
}

fn select_target(
    actor_id: u64,
    cost: i128,
    balance: i128,
    targets: &BTreeMap<NodeId, [u8; 32]>,
) -> Result<NodeId, CityPdError> {
    let actor = NodeId(actor_id);
    let instrument = "city-pd-observation";
    let mut capacity = Capacity::new(actor);
    capacity
        .replenish(instrument, Currency::from_micro_units(balance.min(cost)))
        .map_err(|_| CityPdError::Capacity)?;
    let candidates: Vec<_> = targets
        .keys()
        .map(|target| Candidate {
            actor,
            instrument: instrument.to_owned(),
            mode: "OBSERVE_PUBLIC_ACTIVITY".to_owned(),
            target: *target,
            expected_yield: 1.0,
            cost: Currency::from_micro_units(cost),
        })
        .collect();
    let allocations = capacity
        .allocate(&candidates)
        .map_err(|_| CityPdError::Capacity)?;
    let selected = allocations
        .funded
        .first()
        .ok_or(CityPdError::Capacity)?
        .candidate
        .target;
    Ok(selected)
}
