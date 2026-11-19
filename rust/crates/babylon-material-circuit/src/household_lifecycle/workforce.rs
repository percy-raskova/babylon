use super::HouseholdLifecycleReceipt;
use crate::{
    FinalDemandPrincipalId, StaffingError, StaffingMemberId, StaffingMemberState, StaffingPoolId,
};
use std::collections::{BTreeMap, BTreeSet};
/// Removes labor-force persons only when a living household no longer backs their membership.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResidentWorkforceAttrition {
    pub principal_id: FinalDemandPrincipalId,
    pub pool_id: StaffingPoolId,
    pub member_id: StaffingMemberId,
    pub opening_employed: u64,
    pub opening_reserve: u64,
    pub employed_removed: u64,
    pub reserve_removed: u64,
}
impl ResidentWorkforceAttrition {
    /// # Errors
    /// Refuses impossible or empty losses.
    pub fn validate(&self) -> Result<(), StaffingError> {
        if self.employed_removed > self.opening_employed
            || self.reserve_removed > self.opening_reserve
            || (self.employed_removed == 0 && self.reserve_removed == 0)
        {
            return Err(StaffingError::PopulationInvariant);
        }
        Ok(())
    }
}
/// Compare existing graph memberships with next opening's entire 16+ population.
/// Existing job and reserve stocks share unavoidable attrition proportionally;
/// positive age transitions do not add membership or employment.
/// # Errors
/// Refuses repeated members/households, excess initial membership or overflow.
pub fn reconcile_resident_workforce(
    receipts: &[HouseholdLifecycleReceipt],
    members: &[(StaffingPoolId, StaffingMemberState)],
) -> Result<Vec<ResidentWorkforceAttrition>, StaffingError> {
    if members.len() > crate::MAX_STAFFING_MEMBERS
        || receipts.len() > crate::MAX_MATERIAL_CIRCUIT_ROWS
    {
        return Err(StaffingError::RowLimit);
    }
    let mut by_household = BTreeMap::<_, Vec<_>>::new();
    let mut seen = BTreeSet::new();
    for (pool, member) in members {
        if !seen.insert(member.binding().member_id()) {
            return Err(StaffingError::DuplicateMember);
        }
        by_household
            .entry(member.binding().household_id())
            .or_default()
            .push((*pool, member));
    }
    let mut loss = Vec::new();
    let mut principals = BTreeSet::new();
    for r in receipts {
        r.validate()
            .map_err(|_| StaffingError::PopulationInvariant)?;
        if !principals.insert(r.principal_id) {
            return Err(StaffingError::DuplicateMember);
        }
        let Some(group) = by_household.get_mut(&r.principal_id) else {
            continue;
        };
        group.sort_unstable_by_key(|(pool, m)| (*pool, m.binding().member_id()));
        let weights: Vec<_> = group
            .iter()
            .flat_map(|(_, m)| [m.employed(), m.reserve()])
            .collect();
        let force = weights.iter().try_fold(0u64, |n, p| {
            n.checked_add(*p).ok_or(StaffingError::Arithmetic)
        })?;
        if force
            > r.opening
                .eligible()
                .map_err(|_| StaffingError::Arithmetic)?
        {
            return Err(StaffingError::PopulationInvariant);
        }
        let excess = force.saturating_sub(
            r.closing
                .eligible()
                .map_err(|_| StaffingError::Arithmetic)?,
        );
        if excess == 0 {
            continue;
        }
        let shares = crate::staffing::proportional_shares(excess, &weights)?;
        for ((pool, m), share) in group.iter().zip(shares.as_chunks::<2>().0) {
            let (employed_removed, reserve_removed) = (share[0], share[1]);
            if employed_removed > 0 || reserve_removed > 0 {
                loss.push(ResidentWorkforceAttrition {
                    principal_id: r.principal_id,
                    pool_id: *pool,
                    member_id: m.binding().member_id(),
                    opening_employed: m.employed(),
                    opening_reserve: m.reserve(),
                    employed_removed,
                    reserve_removed,
                });
            }
        }
    }
    loss.sort_unstable_by_key(|r| (r.principal_id, r.pool_id, r.member_id));
    Ok(loss)
}
