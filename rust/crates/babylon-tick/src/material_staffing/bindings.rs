//! Immutable resident-to-workplace joins; mutable people live only in the graph.
use super::{exact_real, MaterialStaffingError};
use babylon_graph::stable_element::StableElementKey;
use babylon_material_circuit::{
    StaffingError, StaffingMemberBinding, StaffingPoolBinding, MAX_MATERIAL_CIRCUIT_ROWS,
    MAX_STAFFING_MEMBERS,
};
use std::collections::BTreeSet;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StaffingMemberNodeBinding {
    subject: StableElementKey,
    member: StaffingMemberBinding,
}
impl StaffingMemberNodeBinding {
    /// Bind one graph member to its immutable resident account.
    /// # Errors
    /// Refuses non-node keys or inexact population controls.
    pub fn try_new(
        subject: StableElementKey,
        member: StaffingMemberBinding,
    ) -> Result<Self, MaterialStaffingError> {
        admit_key(&subject)?;
        exact_real(member.labor_force())?;
        Ok(Self { subject, member })
    }
    #[must_use]
    pub const fn subject(&self) -> &StableElementKey {
        &self.subject
    }
    #[must_use]
    pub const fn member(&self) -> &StaffingMemberBinding {
        &self.member
    }
}

/// One BUSINESS workplace owns memory; its resident SOCIAL_CLASS members own E/R.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StaffingNodeBinding {
    subject: StableElementKey,
    pool: StaffingPoolBinding,
    members: Vec<StaffingMemberNodeBinding>,
}
impl StaffingNodeBinding {
    /// Capture a complete conserved member partition.
    /// # Errors
    /// Refuses malformed/duplicate members, row bounds or inconsistent force.
    pub fn try_new(
        subject: StableElementKey,
        pool: StaffingPoolBinding,
        mut members: Vec<StaffingMemberNodeBinding>,
    ) -> Result<Self, MaterialStaffingError> {
        admit_key(&subject)?;
        exact_real(pool.labor_force())?;
        if (members.is_empty() && pool.labor_force() != 0) || members.len() > MAX_STAFFING_MEMBERS {
            return Err(StaffingError::RowLimit.into());
        }
        members.sort_unstable_by_key(|m| m.member.member_id());
        if members
            .windows(2)
            .any(|p| p[0].member.member_id() == p[1].member.member_id())
        {
            return Err(StaffingError::DuplicateMember.into());
        }
        let force = members.iter().try_fold(0_u64, |n, m| {
            n.checked_add(m.member.labor_force())
                .ok_or(StaffingError::Arithmetic)
        })?;
        if force != pool.labor_force() {
            return Err(StaffingError::PopulationInvariant.into());
        }
        Ok(Self {
            subject,
            pool,
            members,
        })
    }
    #[must_use]
    pub const fn subject(&self) -> &StableElementKey {
        &self.subject
    }
    #[must_use]
    pub const fn pool(&self) -> &StaffingPoolBinding {
        &self.pool
    }
    #[must_use]
    pub fn members(&self) -> &[StaffingMemberNodeBinding] {
        &self.members
    }
}
fn admit_key(subject: &StableElementKey) -> Result<(), MaterialStaffingError> {
    if !matches!(subject, StableElementKey::Node { .. }) {
        return Err(MaterialStaffingError::NodeBinding);
    }
    subject.canonical_bytes()?;
    Ok(())
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StaffingComposition {
    bindings: Vec<StaffingNodeBinding>,
}
impl StaffingComposition {
    /// One workplace memory, one owner for each member, and one unit per site.
    /// # Errors
    /// Refuses empty, excessive or overlapping ownership.
    pub fn try_new(mut bindings: Vec<StaffingNodeBinding>) -> Result<Self, MaterialStaffingError> {
        if bindings.is_empty() {
            return Err(MaterialStaffingError::EmptyBindings);
        }
        if bindings.len() > MAX_MATERIAL_CIRCUIT_ROWS {
            return Err(StaffingError::RowLimit.into());
        }
        bindings.sort_unstable_by_key(|b| b.pool.pool_id());
        let mut nodes = BTreeSet::new();
        let mut pools = BTreeSet::new();
        let mut sites = BTreeSet::new();
        let mut members = BTreeSet::new();
        let mut work_sources = BTreeSet::new();
        for row in &bindings {
            if !nodes.insert(row.subject.canonical_bytes()?) {
                return Err(MaterialStaffingError::DuplicateNode);
            }
            if !pools.insert(row.pool.pool_id()) {
                return Err(StaffingError::DuplicatePool.into());
            }
            // One scalar workplace memory cannot represent two different labor units.
            if !sites.insert(row.pool.site_id()) {
                return Err(StaffingError::DuplicateSiteUnit.into());
            }
            for member in &row.members {
                if !nodes.insert(member.subject.canonical_bytes()?) {
                    return Err(MaterialStaffingError::DuplicateNode);
                }
                if !members.insert(member.member.member_id()) {
                    return Err(StaffingError::DuplicateMember.into());
                }
            }
            for source in row.pool.work_sources() {
                if !work_sources.insert(*source) {
                    return Err(StaffingError::DuplicateWorkSource.into());
                }
            }
            if members.len() > MAX_STAFFING_MEMBERS
                || work_sources.len() > MAX_MATERIAL_CIRCUIT_ROWS
            {
                return Err(StaffingError::RowLimit.into());
            }
        }
        Ok(Self { bindings })
    }
    /// Admit a deliberately unstaffed inventory boundary.
    /// # Errors
    /// Refuses any labor-consuming material activity or budget.
    pub fn inventory_only(
        state: &babylon_material_circuit::MaterialCircuitState,
    ) -> Result<Self, MaterialStaffingError> {
        if !state.process_outputs.is_empty()
            || !state.input_coefficients.is_empty()
            || !state.labor_coefficients.is_empty()
            || !state.capacities.is_empty()
            || !state.production_commitments.is_empty()
            || !state.labor.is_empty()
            || !state.merchants.is_empty()
            || !state.handling_coefficients.is_empty()
            || state.maintenance_binding.is_some()
            || state.maintenance_service.is_some()
        {
            return Err(MaterialStaffingError::InventoryHasLabor);
        }
        Ok(Self { bindings: vec![] })
    }
    #[must_use]
    pub fn bindings(&self) -> &[StaffingNodeBinding] {
        &self.bindings
    }
}
