//! Pure checked `ActionBudget` storage and transition math.

use crate::{
    OrganizationBudgetDelta, PracticeBudgetTerms, PracticeContractError, PracticeId,
    PracticeTargetDomain, SolidarityFootprintEdge, MAX_ORG_SOLIDARITY_EDGES_PER_ORG,
};

/// Convert one canonical binary64 `ActionBudget` storage value to `u32`.
///
/// # Errors
///
/// Returns the exact governed storage refusal for non-finite, negative,
/// fractional, out-of-range, or non-canonical storage.
pub fn read_action_budget(storage: f64) -> Result<u32, PracticeContractError> {
    if !storage.is_finite() {
        return Err(PracticeContractError::PracticeBudgetNonfinite);
    }
    if storage < 0.0 {
        return Err(PracticeContractError::PracticeBudgetNegative);
    }
    if storage.fract() != 0.0 {
        return Err(PracticeContractError::PracticeBudgetFractional);
    }
    if storage > f64::from(u32::MAX) {
        return Err(PracticeContractError::PracticeBudgetRange);
    }
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    let value = storage as u32;
    if storage.to_bits() != f64::from(value).to_bits() {
        return Err(PracticeContractError::PracticeBudgetRoundtrip);
    }
    Ok(value)
}

/// Convert one `u32` `ActionBudget` to its exact canonical binary64 storage.
#[must_use]
pub fn write_action_budget(value: u32) -> f64 {
    f64::from(value)
}

fn governed_cost(
    practice: Option<PracticeId>,
    organize_cost: u32,
    agitate_cost: u32,
    mutual_aid_cost: u32,
) -> Result<u32, PracticeContractError> {
    Ok(match practice {
        None => 0,
        Some(PracticeId::Organize) => organize_cost,
        Some(PracticeId::Agitate) => agitate_cost,
        Some(PracticeId::MutualAid) => mutual_aid_cost,
        Some(
            PracticeId::Strike
            | PracticeId::Blockade
            | PracticeId::Occupation
            | PracticeId::Damage
            | PracticeId::CapitalStrike
            | PracticeId::Investigate,
        ) => return Err(PracticeContractError::PracticeBudgetUnpriced),
    })
}

fn validate_footprint(
    actor_node_id: u64,
    footprint_edges: &[SolidarityFootprintEdge],
) -> Result<u32, PracticeContractError> {
    if footprint_edges.len() > MAX_ORG_SOLIDARITY_EDGES_PER_ORG {
        return Err(PracticeContractError::PracticeFootprintLimit);
    }
    let mut previous: Option<(u64, u64)> = None;
    for edge in footprint_edges
        .iter()
        .take(MAX_ORG_SOLIDARITY_EDGES_PER_ORG + 1)
    {
        let current = (edge.source_org_node_id_u64, edge.target_class_node_id_u64);
        if previous == Some(current) {
            return Err(PracticeContractError::PracticeFootprintDuplicate);
        }
        if previous.is_some_and(|prior| current < prior) {
            return Err(PracticeContractError::PracticeFootprintOrder);
        }
        if edge.source_org_node_id_u64 != actor_node_id {
            return Err(PracticeContractError::PracticeFootprintSource);
        }
        match edge.target_domain_u8 {
            PracticeTargetDomain::SocialClass => {}
        }
        let strength = f64::from_bits(edge.strength_f64_bits_u64);
        if !strength.is_finite() {
            return Err(PracticeContractError::PracticeFootprintStrengthNonfinite);
        }
        if strength <= 0.0 {
            return Err(PracticeContractError::PracticeFootprintStrengthNonpositive);
        }
        previous = Some(current);
    }
    u32::try_from(footprint_edges.len()).map_err(|_| PracticeContractError::PracticeFootprintLimit)
}

/// Compute one detached checked `ActionBudget` transition.
///
/// This function derives both the governed cost and footprint credit. It does
/// not inspect a graph, decide eligibility, authorize execution, or write state.
///
/// # Errors
///
/// Returns an exact footprint, insufficient-budget, or arithmetic refusal.
// The language-neutral contract fixes `terms` as a by-value record argument.
#[allow(clippy::needless_pass_by_value)]
pub fn compute_budget_delta(
    tick: u64,
    actor_node_id: u64,
    pre_action_world_hash: [u8; 32],
    budget_before: u32,
    practice: Option<PracticeId>,
    footprint_edges: &[SolidarityFootprintEdge],
    terms: PracticeBudgetTerms,
) -> Result<OrganizationBudgetDelta, PracticeContractError> {
    let footprint_count = validate_footprint(actor_node_id, footprint_edges)?;
    let PracticeBudgetTerms {
        initial: _,
        period_credit_cap,
        storage_ceiling,
        organize_cost,
        agitate_cost,
        mutual_aid_cost,
    } = terms;
    let cost = governed_cost(practice, organize_cost, agitate_cost, mutual_aid_cost)?;
    if budget_before < cost {
        return Err(PracticeContractError::PracticeBudgetInsufficient);
    }
    let after_cost = budget_before
        .checked_sub(cost)
        .ok_or(PracticeContractError::PracticeBudgetInsufficient)?;
    let credited_credit = footprint_count.min(period_credit_cap);
    let before_ceiling = after_cost
        .checked_add(credited_credit)
        .ok_or(PracticeContractError::PracticeBudgetArithmetic)?;
    let budget_after = before_ceiling.min(storage_ceiling);
    Ok(OrganizationBudgetDelta {
        schema_version: 1,
        tick,
        actor_node_id,
        pre_action_world_hash,
        budget_before,
        governed_cost: cost,
        footprint_count,
        raw_credit: footprint_count,
        credited_credit,
        ceiling_bound: before_ceiling > storage_ceiling,
        budget_after,
    })
}

/// SHA-256 of the exact language-neutral budget and topology contract.
pub const PRACTICE_BUDGET_TOPOLOGY_SOURCE_SHA256: [u8; 32] = [
    0xae, 0x26, 0xe0, 0xe9, 0x34, 0x5f, 0x26, 0xc2, 0x59, 0x50, 0xf8, 0xf5, 0xe1, 0xf7, 0x46, 0xb5,
    0xad, 0x46, 0xcf, 0x1b, 0x04, 0x0d, 0x58, 0xd2, 0x09, 0xa1, 0xdf, 0xf3, 0x22, 0x7b, 0x64, 0xc1,
];
/// Designed terms for the declared three-practice `ActionBudget` contract.
pub const DEFAULT_PRACTICE_BUDGET_TERMS: PracticeBudgetTerms = PracticeBudgetTerms {
    initial: 1,
    period_credit_cap: 1,
    storage_ceiling: 4,
    organize_cost: 1,
    agitate_cost: 1,
    mutual_aid_cost: 1,
};
