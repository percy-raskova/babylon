//! Resident partitions of the one aggregate staffing decision.
use super::{StaffingError, StaffingPoolId, StaffingReceipt};
use crate::{FinalDemandPrincipalId, SiteId, UnitId};
use babylon_kernel::economic_location::EconomicLocation;

crate::model::identity_type!(StaffingMemberId);

/// Sparse member ceiling; independent from the number of workplace pools.
pub const MAX_STAFFING_MEMBERS: usize = 131_072;

/// Captured membership, without a second mutable population register.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StaffingMemberBinding {
    member_id: StaffingMemberId,
    household_id: FinalDemandPrincipalId,
    residence: EconomicLocation,
    labor_force: u64,
}
impl StaffingMemberBinding {
    /// Admit an explicit resident partition. Political class is not inferred.
    /// # Errors
    /// Refuses empty membership.
    pub fn try_new(
        member_id: StaffingMemberId,
        household_id: FinalDemandPrincipalId,
        residence: EconomicLocation,
        labor_force: u64,
    ) -> Result<Self, StaffingError> {
        if labor_force == 0 {
            return Err(StaffingError::PopulationInvariant);
        }
        Ok(Self {
            member_id,
            household_id,
            residence,
            labor_force,
        })
    }
    #[must_use]
    pub const fn member_id(&self) -> StaffingMemberId {
        self.member_id
    }
    #[must_use]
    pub const fn household_id(&self) -> FinalDemandPrincipalId {
        self.household_id
    }
    #[must_use]
    pub const fn residence(&self) -> EconomicLocation {
        self.residence
    }
    #[must_use]
    pub const fn labor_force(&self) -> u64 {
        self.labor_force
    }
}

/// Transient projection of graph-owned member stocks.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StaffingMemberState {
    binding: StaffingMemberBinding,
    employed: u64,
    reserve: u64,
}
impl StaffingMemberState {
    /// Read a conserved partition; this type owns no durable state.
    /// # Errors
    /// Refuses overflow or a population mismatch.
    pub fn try_new(
        binding: StaffingMemberBinding,
        employed: u64,
        reserve: u64,
    ) -> Result<Self, StaffingError> {
        if employed
            .checked_add(reserve)
            .ok_or(StaffingError::Arithmetic)?
            != binding.labor_force
        {
            return Err(StaffingError::PopulationInvariant);
        }
        Ok(Self {
            binding,
            employed,
            reserve,
        })
    }
    #[must_use]
    pub const fn binding(&self) -> &StaffingMemberBinding {
        &self.binding
    }
    #[must_use]
    pub const fn employed(&self) -> u64 {
        self.employed
    }
    #[must_use]
    pub const fn reserve(&self) -> u64 {
        self.reserve
    }
}

/// Derived hours for a member in an explicit period. Persons remain graph-owned.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MemberLaborCapacityRow {
    pub member_id: StaffingMemberId,
    pub period: u64,
    pub available_hours: u64,
}

/// Exact member share of a completed pool transition.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StaffingMemberReceipt {
    pub period: u64,
    pub pool_id: StaffingPoolId,
    pub site_id: SiteId,
    pub unit_id: UnitId,
    pub member: StaffingMemberBinding,
    pub hours_per_person: u64,
    pub opening_employed: u64,
    pub opening_reserve: u64,
    pub hires: u64,
    pub separations: u64,
    pub closing_employed: u64,
    pub closing_reserve: u64,
    pub next_opening_hours: u64,
}
impl StaffingMemberReceipt {
    /// Check conservation independently of the allocation policy.
    /// # Errors
    /// Refuses zero periods/schedules or any inconsistent population/hour flow.
    pub fn validate(&self) -> Result<(), StaffingError> {
        if self.period == 0
            || self.hours_per_person == 0
            || self.opening_employed.checked_add(self.opening_reserve)
                != Some(self.member.labor_force)
            || self.closing_employed.checked_add(self.closing_reserve)
                != Some(self.member.labor_force)
            || self.opening_employed.checked_add(self.hires)
                != self.closing_employed.checked_add(self.separations)
            || self.opening_reserve.checked_add(self.separations)
                != self.closing_reserve.checked_add(self.hires)
            || (self.hires != 0 && self.separations != 0)
            || self.closing_employed.checked_mul(self.hours_per_person)
                != Some(self.next_opening_hours)
        {
            return Err(StaffingError::PopulationInvariant);
        }
        Ok(())
    }
}

/// Allocate at most the available total with exact largest remainders.
/// Caller order resolves equal remainders; callers supply canonical identities.
pub(crate) fn proportional_shares(total: u64, weights: &[u64]) -> Result<Vec<u64>, StaffingError> {
    let sum = weights.iter().try_fold(0_u64, |n, w| {
        n.checked_add(*w).ok_or(StaffingError::Arithmetic)
    })?;
    if total > sum {
        return Err(StaffingError::PopulationInvariant);
    }
    let mut result = vec![0; weights.len()];
    if total == 0 {
        return Ok(result);
    }
    let mut remainders = Vec::with_capacity(weights.len());
    let mut assigned = 0_u64;
    for (index, weight) in weights.iter().enumerate() {
        let numerator = u128::from(total) * u128::from(*weight);
        let share =
            u64::try_from(numerator / u128::from(sum)).map_err(|_| StaffingError::Arithmetic)?;
        result[index] = share;
        assigned = assigned
            .checked_add(share)
            .ok_or(StaffingError::Arithmetic)?;
        remainders.push((numerator % u128::from(sum), index));
    }
    remainders.sort_unstable_by(|a, b| b.0.cmp(&a.0).then_with(|| a.1.cmp(&b.1)));
    let left = usize::try_from(total - assigned).map_err(|_| StaffingError::Arithmetic)?;
    for (_, index) in remainders.into_iter().take(left) {
        result[index] += 1;
    }
    Ok(result)
}

/// Partition one existing staffing result; never chooses another target.
/// # Errors
/// Refuses duplicate members, mismatched opening totals, row bounds or overflow.
pub fn distribute_staffing_members(
    receipt: &StaffingReceipt,
    members: &[StaffingMemberState],
) -> Result<Vec<StaffingMemberReceipt>, StaffingError> {
    if members.is_empty() && receipt.binding().labor_force() == 0 {
        return Ok(vec![]);
    }
    if members.is_empty() || members.len() > MAX_STAFFING_MEMBERS {
        return Err(StaffingError::RowLimit);
    }
    let mut members = members.iter().collect::<Vec<_>>();
    members.sort_unstable_by_key(|m| m.binding.member_id);
    if members
        .windows(2)
        .any(|p| p[0].binding.member_id == p[1].binding.member_id)
    {
        return Err(StaffingError::DuplicateMember);
    }
    let employed = members.iter().try_fold(0_u64, |n, m| {
        n.checked_add(m.employed).ok_or(StaffingError::Arithmetic)
    })?;
    let reserve = members.iter().try_fold(0_u64, |n, m| {
        n.checked_add(m.reserve).ok_or(StaffingError::Arithmetic)
    })?;
    if employed != receipt.opening_employed() || reserve != receipt.opening_reserve() {
        return Err(StaffingError::PopulationInvariant);
    }
    let hiring = receipt.hires() != 0;
    let weights = members
        .iter()
        .map(|m| if hiring { m.reserve } else { m.employed })
        .collect::<Vec<_>>();
    let shares = proportional_shares(
        if hiring {
            receipt.hires()
        } else {
            receipt.separations()
        },
        &weights,
    )?;
    members
        .into_iter()
        .zip(shares)
        .map(|(m, share)| {
            let (hires, separations) = if hiring { (share, 0) } else { (0, share) };
            let closing_employed = m
                .employed
                .checked_add(hires)
                .and_then(|n| n.checked_sub(separations))
                .ok_or(StaffingError::Arithmetic)?;
            let closing_reserve = m
                .reserve
                .checked_add(separations)
                .and_then(|n| n.checked_sub(hires))
                .ok_or(StaffingError::Arithmetic)?;
            let row = StaffingMemberReceipt {
                period: receipt.period(),
                pool_id: receipt.binding().pool_id(),
                site_id: receipt.binding().site_id(),
                unit_id: receipt.binding().unit_id(),
                member: m.binding.clone(),
                hours_per_person: receipt.binding().policy().hours_per_person(),
                opening_employed: m.employed,
                opening_reserve: m.reserve,
                hires,
                separations,
                closing_employed,
                closing_reserve,
                next_opening_hours: closing_employed
                    .checked_mul(receipt.binding().policy().hours_per_person())
                    .ok_or(StaffingError::Arithmetic)?,
            };
            row.validate()?;
            Ok(row)
        })
        .collect()
}
