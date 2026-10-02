//! Consume fixed county budget quotas without a workplace × household Cartesian product.
use super::{
    AllocationError, AssignedResidentWorkplace, CountyHouseholdAllocation,
    PendingAssignedWorkplace, PendingResidentMember, ResidentAttendanceMode, Result,
};
use crate::{
    national_economy::household_principal, national_household_allocation::HouseholdBudgetKey,
};
use std::collections::BTreeMap;

struct Quota {
    key: HouseholdBudgetKey,
    employed: u64,
    reserve: u64,
}

pub(super) fn partition(
    pending: &[PendingAssignedWorkplace],
    budgets: &CountyHouseholdAllocation,
) -> Result<Vec<AssignedResidentWorkplace>> {
    let mut quotas: Vec<_> = budgets
        .budgets()
        .iter()
        .map(|r| Quota {
            key: r.key,
            employed: r.employed,
            reserve: r.reserve,
        })
        .collect();
    let mut output: Vec<_> = pending
        .iter()
        .map(|row| AssignedResidentWorkplace {
            target: row.target.clone(),
            weight: row.weight.clone(),
            members: vec![],
        })
        .collect();
    let mut rows: Vec<_> = pending
        .iter()
        .enumerate()
        .flat_map(|(i, w)| w.members.iter().copied().map(move |m| (i, m)))
        .collect();
    rows.sort_by_key(|(i, m)| (priority(m.mode), pending[*i].target.site_id));
    for (index, row) in rows {
        let shares = take(&mut quotas, row)?;
        for (key, (employed, reserve)) in shares {
            if employed == 0 && reserve == 0 {
                continue;
            }
            let target = &pending[index].target;
            output[index].members.push(super::member(
                target,
                row.mode,
                household_principal(target.location, key),
                employed,
                reserve,
            )?);
        }
    }
    if quotas.iter().any(|q| q.employed != 0 || q.reserve != 0) {
        return Err(AllocationError::PopulationControl);
    }
    for row in &mut output {
        row.members
            .sort_unstable_by_key(|m| m.seed.member.member_id());
    }
    Ok(output)
}
fn priority(mode: ResidentAttendanceMode) -> u8 {
    match mode {
        ResidentAttendanceMode::WorkingOwner => 0,
        ResidentAttendanceMode::Employee => 1,
        ResidentAttendanceMode::UnpaidFamily => 2,
    }
}
fn take(
    quotas: &mut [Quota],
    row: PendingResidentMember,
) -> Result<BTreeMap<HouseholdBudgetKey, (u64, u64)>> {
    let mut result = BTreeMap::new();
    let mut indices: Vec<_> = (0..quotas.len()).collect();
    indices.sort_by_key(|i| {
        (
            row.mode == ResidentAttendanceMode::WorkingOwner && !quotas[*i].key.owner_exposure(),
            quotas[*i].key,
        )
    });
    let mut employed = row.employed;
    for i in &indices {
        let amount = quotas[*i].employed.min(employed);
        quotas[*i].employed -= amount;
        employed -= amount;
        if amount > 0 {
            result.insert(quotas[*i].key, (amount, 0));
        }
    }
    // Prefer an already used payee when its captured reserve quota permits it.
    indices.sort_by_key(|i| (!result.contains_key(&quotas[*i].key), quotas[*i].key));
    let mut reserve = row.reserve;
    for i in indices {
        let amount = quotas[i].reserve.min(reserve);
        quotas[i].reserve -= amount;
        reserve -= amount;
        if amount > 0 {
            result.entry(quotas[i].key).or_default().1 = amount;
        }
    }
    if employed != 0 || reserve != 0 {
        return Err(AllocationError::PopulationControl);
    }
    Ok(result)
}
