//! The staffing of the doubled world: one pool and one member for each workplace.

use crate::doubled::figures::HOURS_PER_PERSON;
use crate::doubled::opening;
use crate::ids;
use crate::{Kind, Workplace, WorldError};
use babylon_material_circuit::{
    StaffingMemberBinding, StaffingMemberState, StaffingPolicy, StaffingPoolBinding,
    StaffingPoolState, StaffingState, StaffingWorkSource,
};

/// The pool bindings, and the state that opens with every worker employed and none in reserve.
///
/// # Errors
/// `WorldError::Staffing` when the engine refuses a pool, `WorldError::Arithmetic` when an opening
/// figure overflows.
pub fn staffing() -> Result<(Vec<StaffingPoolBinding>, StaffingState), WorldError> {
    let hours = opening::site_hours()?;
    let mut bindings = Vec::new();
    let mut pools = Vec::new();
    for w in Workplace::ALL {
        let source = match w.process_id() {
            Some(process) if w.kind != Kind::Shop => StaffingWorkSource::Production(process),
            _ => StaffingWorkSource::MerchantHandling(w.site_id()),
        };
        let workers = w.workers().opening_persons();
        let binding = StaffingPoolBinding::try_new(
            w.pool_id(),
            w.site_id(),
            ids::hours_unit(),
            workers,
            StaffingPolicy::one_period(HOURS_PER_PERSON)?,
            vec![source],
        )?;
        pools.push(StaffingPoolState::try_new(
            binding.clone(),
            workers,
            0,
            hours[w.index()],
        )?);
        bindings.push(binding);
    }
    Ok((bindings, StaffingState::try_new(1, pools)?))
}

/// The one member of a workplace's pool, with `employed` of its persons at work.
///
/// # Errors
/// `WorldError::Staffing` when `employed` is more than the workplace's persons;
/// `WorldError::Location` when the place does not parse.
pub fn member(workplace: Workplace, employed: u64) -> Result<StaffingMemberState, WorldError> {
    let force = workplace.workers().opening_persons();
    let binding = StaffingMemberBinding::from_living_force(
        workplace.member_id(),
        workplace.workers().principal(),
        ids::location()?,
        force,
    );
    let reserve = force.checked_sub(employed).ok_or(WorldError::Arithmetic)?;
    Ok(StaffingMemberState::try_new(binding, employed, reserve)?)
}
