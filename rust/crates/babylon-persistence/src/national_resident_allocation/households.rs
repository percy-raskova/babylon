//! Consume fixed county budget quotas without a workplace × household Cartesian product.
use super::{
    AllocationError, AssignedResidentWorkplace, CountyHouseholdAllocation,
    PendingAssignedWorkplace, PendingResidentMember, ResidentAttendanceMode, Result,
};
use crate::national_household_allocation::HouseholdBudgetKey;
use crate::national_household_refinement::NationalHouseholdLeafRoster;

use babylon_kernel::currency::Currency;
use babylon_material_circuit::{FinalDemandPrincipalId, SiteId};
use std::cmp::Reverse;
use std::collections::BTreeMap;

struct Quota {
    key: HouseholdBudgetKey,
    employed: u64,
    reserve: u64,
}

pub(super) fn partition(
    pending: &[PendingAssignedWorkplace],
    budgets: &CountyHouseholdAllocation,
    roster: &NationalHouseholdLeafRoster,
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
    let mut leaves = leaf_quotas(budgets, roster)?;
    let mut output: Vec<_> = pending
        .iter()
        .map(|row| AssignedResidentWorkplace {
            target: row.target.clone(),
            weight: row.weight.clone(),
            members: vec![],
            county_wage: row.county_wage,
        })
        .collect();
    let mut rows: Vec<_> = pending
        .iter()
        .enumerate()
        .flat_map(|(i, w)| w.members.iter().copied().map(move |m| (i, m)))
        .collect();
    rows.sort_by_key(|(i, m)| {
        row_order(m.mode, pending[*i].county_wage, pending[*i].target.site_id)
    });
    for (index, row) in rows {
        let shares = take(&mut quotas, row)?;
        for (key, (employed, reserve)) in shares {
            if employed == 0 && reserve == 0 {
                continue;
            }
            let target = &pending[index].target;
            let quotas = leaves
                .get_mut(&key)
                .ok_or(AllocationError::PopulationControl)?;
            for (principal, (employed, reserve)) in take_leaves(quotas, employed, reserve)? {
                output[index].members.push(super::member(
                    target, row.mode, principal, employed, reserve,
                )?);
            }
        }
    }
    if quotas.iter().any(|q| q.employed != 0 || q.reserve != 0)
        || leaves
            .values()
            .flatten()
            .any(|q| q.employed != 0 || q.reserve != 0)
    {
        return Err(AllocationError::PopulationControl);
    }
    for row in &mut output {
        row.members
            .sort_unstable_by_key(|m| m.seed.member.member_id());
    }
    Ok(output)
}
struct LeafQuota {
    principal: FinalDemandPrincipalId,
    employed: u64,
    reserve: u64,
}
fn leaf_quotas(
    budgets: &CountyHouseholdAllocation,
    roster: &NationalHouseholdLeafRoster,
) -> Result<BTreeMap<HouseholdBudgetKey, Vec<LeafQuota>>> {
    let mut result = BTreeMap::new();
    for parent in budgets.budgets() {
        let leaves = roster.parent_leaves(budgets.county(), parent.key);
        let totals =
            leaves
                .iter()
                .try_fold((0_u64, 0_u64), |(e, r), leaf| -> Result<(u64, u64)> {
                    Ok((
                        e.checked_add(leaf.margins.employed)
                            .ok_or(AllocationError::Arithmetic)?,
                        r.checked_add(leaf.margins.reserve)
                            .ok_or(AllocationError::Arithmetic)?,
                    ))
                })?;
        if leaves.is_empty() || totals != (parent.employed, parent.reserve) {
            return Err(AllocationError::PopulationControl);
        }
        result.insert(
            parent.key,
            leaves
                .iter()
                .map(|leaf| LeafQuota {
                    principal: leaf.principal_id,
                    employed: leaf.margins.employed,
                    reserve: leaf.margins.reserve,
                })
                .collect(),
        );
    }
    Ok(result)
}
fn take_leaves(
    quotas: &mut [LeafQuota],
    mut employed: u64,
    mut reserve: u64,
) -> Result<BTreeMap<FinalDemandPrincipalId, (u64, u64)>> {
    let mut result = BTreeMap::<FinalDemandPrincipalId, (u64, u64)>::new();
    for quota in quotas.iter_mut() {
        let amount = quota.employed.min(employed);
        quota.employed -= amount;
        employed -= amount;
        if amount > 0 {
            result.insert(quota.principal, (amount, 0));
        }
    }
    // Route reserve through the same canonical stream, preferring a used leaf.
    let mut indices: Vec<_> = (0..quotas.len()).collect();
    indices.sort_by_key(|i| (!result.contains_key(&quotas[*i].principal), *i));
    for index in indices {
        let quota = &mut quotas[index];
        let amount = quota.reserve.min(reserve);
        quota.reserve -= amount;
        reserve -= amount;
        if amount > 0 {
            let used = &mut result.entry(quota.principal).or_default().1;
            *used = used
                .checked_add(amount)
                .ok_or(AllocationError::Arithmetic)?;
        }
    }
    if employed != 0 || reserve != 0 {
        return Err(AllocationError::PopulationControl);
    }
    Ok(result)
}
/// The order jobs are dealt in: working owners, then employees from the best pay down (ties by
/// site id), then unpaid family. Without observed pay every wage is `None` and site id decides.
fn row_order(
    mode: ResidentAttendanceMode,
    wage: Option<Currency>,
    site: SiteId,
) -> (u8, Reverse<Option<Currency>>, SiteId) {
    let wage = if mode == ResidentAttendanceMode::Employee {
        wage
    } else {
        None
    };
    (priority(mode), Reverse(wage), site)
}
/// The order a row fills quotas in. Schema 7 keys keep their own order; under schema 8 the owners
/// come first, then the better-paid forty, the lower-paid half and the collective residences.
const fn deal_rank(key: HouseholdBudgetKey) -> u8 {
    match key {
        HouseholdBudgetKey::EarningNonowner => 0,
        HouseholdBudgetKey::EarningOwner => 1,
        HouseholdBudgetKey::EarningBetterPaidForty => 2,
        HouseholdBudgetKey::EarningLowerPaidHalf => 3,
        HouseholdBudgetKey::NoEarnerNonowner => 4,
        HouseholdBudgetKey::NoEarnerOwner => 5,
        HouseholdBudgetKey::CollectiveResidence => 6,
        HouseholdBudgetKey::PooledExternal => 7,
    }
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
            deal_rank(quotas[*i].key),
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

#[cfg(test)]
mod tests {
    use super::*;
    use HouseholdBudgetKey::{
        CollectiveResidence, EarningBetterPaidForty, EarningLowerPaidHalf, EarningOwner,
    };

    fn quota(key: HouseholdBudgetKey, employed: u64) -> Quota {
        Quota {
            key,
            employed,
            reserve: 0,
        }
    }
    fn site(n: u8) -> SiteId {
        SiteId::from_bytes([n; 32])
    }
    /// Deal employee rows `(site, wage in dollars, persons)` and name each row's shares.
    fn deal(rows: &[(u8, i128, u64)]) -> Vec<(u8, Vec<(HouseholdBudgetKey, u64)>)> {
        let mut quotas = vec![
            quota(EarningLowerPaidHalf, 50),
            quota(EarningOwner, 10),
            quota(CollectiveResidence, 5),
            quota(EarningBetterPaidForty, 40),
        ];
        let mut order: Vec<_> = rows.to_vec();
        order.sort_by_key(|(n, wage, _)| {
            row_order(
                ResidentAttendanceMode::Employee,
                Some(Currency::from_micro_units(wage * 1_000_000)),
                site(*n),
            )
        });
        order
            .into_iter()
            .map(|(n, _, persons)| {
                let row = PendingResidentMember {
                    mode: ResidentAttendanceMode::Employee,
                    employed: persons,
                    reserve: 0,
                };
                let shares = take(&mut quotas, row).expect("the quotas cover the row");
                let mut shares: Vec<_> = shares.into_iter().map(|(k, (e, _))| (k, e)).collect();
                shares.sort_by_key(|(k, _)| deal_rank(*k));
                (n, shares)
            })
            .collect()
    }

    #[test]
    fn jobs_are_dealt_by_pay_in_whole_persons() {
        // A pays $50, B $30, C $20.
        let dealt = deal(&[(1, 50, 30), (2, 30, 40), (3, 20, 35)]);
        assert_eq!(
            dealt,
            vec![
                (1, vec![(EarningOwner, 10), (EarningBetterPaidForty, 20)]),
                (
                    2,
                    vec![(EarningBetterPaidForty, 20), (EarningLowerPaidHalf, 20)]
                ),
                (
                    3,
                    vec![(EarningLowerPaidHalf, 30), (CollectiveResidence, 5)]
                ),
            ]
        );
        // B at $50 with a site id below A's is dealt first.
        let dealt = deal(&[(2, 50, 30), (1, 50, 40), (3, 20, 35)]);
        assert_eq!(dealt[0].0, 1);
        assert_eq!(
            dealt[0].1,
            vec![(EarningOwner, 10), (EarningBetterPaidForty, 30)]
        );
    }
}
