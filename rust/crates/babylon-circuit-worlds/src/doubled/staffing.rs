//! The staffing of a doubled world: one pool for each workplace, and the members of each pool.

use crate::doubled::opening;
use crate::doubled::world::World;
use crate::ids;
use crate::{Kind, Place, Workplace, WorldError};
use babylon_material_circuit::{
    PoolMembers, StaffingMemberBinding, StaffingMemberState, StaffingPlace, StaffingPolicy,
    StaffingPoolBinding, StaffingPoolState, StaffingState, StaffingWorkSource,
};

/// The scene's pool bindings, and the state that opens with every worker employed and none in reserve.
///
/// # Errors
/// As `staffing_of`.
pub fn staffing() -> Result<(Vec<StaffingPoolBinding>, StaffingState), WorldError> {
    staffing_of(&World::scene())
}

/// The pool bindings of a world, and the state that opens with every worker employed and none in
/// reserve.
///
/// # Errors
/// `WorldError::Staffing` when the engine refuses a pool, `WorldError::Arithmetic` when an opening
/// figure overflows.
pub fn staffing_of(world: &World) -> Result<(Vec<StaffingPoolBinding>, StaffingState), WorldError> {
    let hours = opening::site_hours(world)?;
    let mut bindings = Vec::new();
    let mut pools = Vec::new();
    for w in Workplace::ALL {
        let source = match w.process_id() {
            Some(process) if w.kind != Kind::Shop => StaffingWorkSource::Production(process),
            _ => StaffingWorkSource::MerchantHandling(w.site_id()),
        };
        let workers = world.persons(w.workers());
        let binding = StaffingPoolBinding::try_new(
            w.pool_id(),
            w.site_id(),
            ids::hours_unit(),
            workers,
            StaffingPolicy::one_period(world.hours_per_person())?,
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

/// The one member of a workplace's pool in the scene's world, with `employed` of its persons at work.
///
/// # Errors
/// As `member_of`.
pub fn member(workplace: Workplace, employed: u64) -> Result<StaffingMemberState, WorldError> {
    member_of(&World::scene(), workplace, employed)
}

/// The workplace's own member, with `employed` of its persons at work.
///
/// # Errors
/// `WorldError::Arithmetic` when `employed` is more than the workplace's persons;
/// `WorldError::Staffing` when the engine refuses the member;
/// `WorldError::Location` when the place does not parse.
pub fn member_of(
    world: &World,
    workplace: Workplace,
    employed: u64,
) -> Result<StaffingMemberState, WorldError> {
    let force = world.persons(workplace.workers());
    let binding = StaffingMemberBinding::from_living_force(
        workplace.member_id(),
        workplace.workers().principal(),
        ids::location()?,
        force,
    );
    let reserve = force.checked_sub(employed).ok_or(WorldError::Arithmetic)?;
    Ok(StaffingMemberState::try_new(binding, employed, reserve)?)
}

/// Every pool's members at the opening, by `Workplace::index`: the workplace's own member with all its
/// people, and one member for each other workplace of its place (`pair_member_id`), with nobody.
///
/// # Errors
/// As `member_of`.
pub fn members_of(world: &World) -> Result<Vec<Vec<StaffingMemberState>>, WorldError> {
    let mut pools = Vec::new();
    for host in Workplace::ALL {
        let own = world.persons(host.workers());
        let mut members = vec![member_of(world, host, own)?];
        for (home, _) in Workplace::pairs().filter(|&(_, pair_host)| pair_host == host) {
            let binding = StaffingMemberBinding::from_living_force(
                host.pair_member_id(home),
                home.workers().principal(),
                ids::location()?,
                0,
            );
            members.push(StaffingMemberState::try_new(binding, 0, 0)?);
        }
        pools.push(members);
    }
    Ok(pools)
}

/// Each place's pools: place A's four, then place B's, each in site order.
#[must_use]
pub fn places() -> Vec<StaffingPlace> {
    Place::ALL
        .iter()
        .map(|&place| StaffingPlace {
            pools: Workplace::ALL
                .iter()
                .filter(|workplace| workplace.place == place)
                .map(|workplace| workplace.pool_id())
                .collect(),
        })
        .collect()
}

/// Every pool's members at the opening, as `members_of`: one `PoolMembers` for each pool, in pool order.
///
/// # Errors
/// As `member_of`.
pub fn pool_members_of(world: &World) -> Result<Vec<PoolMembers>, WorldError> {
    Ok(Workplace::ALL
        .iter()
        .zip(members_of(world)?)
        .map(|(workplace, members)| PoolMembers {
            pool_id: workplace.pool_id(),
            members,
        })
        .collect())
}
