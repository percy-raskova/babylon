//! People looking for work at the other workplaces of their place (A14 of ADR314).

use std::collections::{BTreeMap, BTreeSet};

use super::{
    StaffingError, StaffingMemberBinding, StaffingMemberState, StaffingPoolBinding, StaffingPoolId,
    StaffingPoolState, StaffingReceipt, StaffingState, StaffingTransition,
};
use crate::financial::LayoffRecord;
use crate::{
    FinalDemandPrincipalId, LaborCapacityRow, MaterialCircuitError, MemberLaborCapacityRow,
    PlaceMoveReceipt, SiteId, StaffingMemberId, StaffingMemberReceipt, StaffingWorkRequest,
    StopReceipt, WorkplaceStanding,
};

/// The pools whose people look for work at one another: one place.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StaffingPlace {
    /// The pools of the place, in site order.
    pub pools: Vec<StaffingPoolId>,
}

/// A pool's members: one for each household of its place, in member order.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PoolMembers {
    /// The pool.
    pub pool_id: StaffingPoolId,
    /// Its members.
    pub members: Vec<StaffingMemberState>,
}

/// The staffing of a closed period by the rules of the catalog.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PlaceStaffing {
    /// The staffing of the next period, each pool with the labor force it has after the moves.
    pub state: StaffingState,
    /// Every pool's members after the moves, in the order they were given.
    pub members: Vec<PoolMembers>,
    /// The hours of each pool in the next period: its employed persons at its hours a person.
    pub labor: Vec<LaborCapacityRow>,
    /// The hours of each member in the next period.
    pub member_labor: Vec<MemberLaborCapacityRow>,
    /// The engine's own decision, pool by pool and member by member, before any move.
    pub receipts: Vec<StaffingReceipt>,
    /// The engine's own decision for each member, before any move.
    pub member_receipts: Vec<StaffingMemberReceipt>,
    /// Every move of persons from one pool's reserve to a host.
    pub moves: Vec<PlaceMoveReceipt>,
    /// What the rules remember of each workplace after this close; the standing given, unchanged, when the
    /// catalog does not ask for the stop rule.
    pub standing: WorkplaceStanding,
    /// What the stop rule decided of each workplace, in site order; empty when the catalog does not ask.
    pub(crate) stops: Vec<StopReceipt>,
    /// The receipts the record of layoffs advances from: the decision with each move written as the hire or
    /// departure it amounts to. Built and used inside the close; not published.
    pub(crate) record_receipts: Vec<StaffingMemberReceipt>,
    /// The record of layoffs each member must hold after the close (the non-empty ones), when a program
    /// that pays after a layoff has recipients.
    pub(crate) records: Option<Vec<(StaffingMemberId, Vec<u64>)>>,
}

/// Why `staff_in_places` refused: the circuit's own refusal or the staffing's.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum PlaceStaffingError {
    /// The circuit refused.
    Circuit(MaterialCircuitError),
    /// The staffing refused.
    Staffing(StaffingError),
}
impl From<MaterialCircuitError> for PlaceStaffingError {
    fn from(error: MaterialCircuitError) -> Self {
        Self::Circuit(error)
    }
}
impl From<StaffingError> for PlaceStaffingError {
    fn from(error: StaffingError) -> Self {
        Self::Staffing(error)
    }
}

/// What the closed state says about pay and layoffs.
pub(crate) struct PlaceRules<'a> {
    /// The households that a program pays after a layoff.
    pub(crate) recipients: &'a BTreeSet<FinalDemandPrincipalId>,
    /// The members that can hold a record of layoffs: paid a wage by a recipient household.
    pub(crate) holders: &'a BTreeSet<StaffingMemberId>,
    /// The periods a record of layoffs keeps; 0 when no program pays after a layoff.
    pub(crate) window: usize,
    /// The records of layoffs at the close.
    pub(crate) records: &'a [LayoffRecord],
    /// The largest wage of each site's employment terms, in millionths of a dollar.
    pub(crate) wages: &'a BTreeMap<SiteId, i128>,
    /// The most persons each limited workplace may employ after the close (the stop rule).
    pub(crate) limits: &'a BTreeMap<SiteId, u64>,
}

/// One member of one pool, through the engine's decision and the moves.
struct Slot {
    /// The engine's own decision for the member.
    engine: StaffingMemberReceipt,
    /// The people looking for work that no record of layoffs covers, still there to be taken.
    uncovered: u64,
    /// The people the record covers, by the periods since they were laid off, still there to be taken.
    covered: Vec<u64>,
    /// The persons of this household that the pool took on from another pool.
    gained: u64,
    /// Uncovered persons taken by another pool.
    left_uncovered: u64,
    /// Covered persons taken by another pool.
    left_covered: u64,
}

/// One pool through the period.
struct PoolWork {
    receipt: StaffingReceipt,
    /// Its place and its position in it.
    place: usize,
    position: usize,
    slots: Vec<Slot>,
    /// How many persons it lacks for the hours it asked for.
    need: u64,
}

fn refuse(error: StaffingError) -> PlaceStaffingError {
    PlaceStaffingError::Staffing(error)
}

/// Where each pool of the opening stands: its place and its position there. A pool in no place, in two, or a
/// place's pool the state does not hold is refused.
fn positions(
    opening: &StaffingState,
    places: &[StaffingPlace],
) -> Result<BTreeMap<StaffingPoolId, (usize, usize)>, PlaceStaffingError> {
    let mut at = BTreeMap::new();
    for (place, row) in places.iter().enumerate() {
        for (position, pool) in row.pools.iter().enumerate() {
            if at.insert(*pool, (place, position)).is_some() {
                return Err(refuse(StaffingError::DuplicatePool));
            }
        }
    }
    let known: BTreeSet<StaffingPoolId> = opening
        .pools()
        .iter()
        .map(|pool| pool.binding().pool_id())
        .collect();
    if at.len() != known.len() || at.keys().any(|pool| !known.contains(pool)) {
        return Err(refuse(StaffingError::PopulationInvariant));
    }
    Ok(at)
}

/// One slot for each member of a pool, in member order, from the engine's decision for the pool.
fn slots_of(
    receipt: &StaffingReceipt,
    members: &[StaffingMemberState],
    rules: &PlaceRules<'_>,
) -> Result<Vec<Slot>, PlaceStaffingError> {
    let rows = super::distribute_staffing_members(receipt, members)?;
    let mut slots = Vec::with_capacity(rows.len());
    for engine in rows {
        let covered = if rules.window > 0 && rules.holders.contains(&engine.member.member_id()) {
            let held = rules
                .records
                .iter()
                .find(|record| record.member_id == engine.member.member_id())
                .map_or(&[][..], |record| record.cohorts.as_slice());
            crate::financial::advance_layoffs(held, rules.window, &engine)?
        } else {
            Vec::new()
        };
        let looking_covered = covered.iter().try_fold(0_u64, |n, c| {
            n.checked_add(*c).ok_or(StaffingError::Arithmetic)
        })?;
        let uncovered = engine
            .closing_reserve
            .checked_sub(looking_covered)
            .ok_or_else(|| refuse(StaffingError::PopulationInvariant))?;
        slots.push(Slot {
            engine,
            uncovered,
            covered,
            gained: 0,
            left_uncovered: 0,
            left_covered: 0,
        });
    }
    Ok(slots)
}

/// Every pool through the engine's decision, with who looks for work and who is lacking.
fn pools_decided(
    decided: &[StaffingReceipt],
    members: &[PoolMembers],
    at: &BTreeMap<StaffingPoolId, (usize, usize)>,
    rules: &PlaceRules<'_>,
) -> Result<Vec<PoolWork>, PlaceStaffingError> {
    if members.len() != decided.len() {
        return Err(refuse(StaffingError::PopulationInvariant));
    }
    let mut pools = Vec::with_capacity(decided.len());
    for receipt in decided {
        let binding = receipt.binding();
        let row = members
            .iter()
            .find(|row| row.pool_id == binding.pool_id())
            .ok_or_else(|| refuse(StaffingError::PopulationInvariant))?;
        let (place, position) = *at
            .get(&binding.pool_id())
            .ok_or_else(|| refuse(StaffingError::PopulationInvariant))?;
        let hours = binding.policy().hours_per_person();
        let asked = receipt.current_unretained_hours();
        let mut people = asked
            .div_ceil(hours)
            .saturating_sub(receipt.closing_employed());
        if let Some(limit) = rules.limits.get(&binding.site_id()) {
            people = people.min(limit.saturating_sub(receipt.closing_employed()));
        }
        pools.push(PoolWork {
            receipt: receipt.clone(),
            place,
            position,
            slots: slots_of(receipt, &row.members, rules)?,
            need: people,
        });
    }
    Ok(pools)
}

/// The pools of one place, in site order, as indices of `pools`.
fn place_pools(pools: &[PoolWork], place: usize) -> Vec<usize> {
    let mut row: Vec<usize> = (0..pools.len())
        .filter(|&index| pools[index].place == place)
        .collect();
    row.sort_by_key(|&index| pools[index].position);
    row
}

/// What one host took, and from whom.
struct Taking<'a> {
    period: u64,
    host: usize,
    host_pools: &'a [usize],
}

impl Taking<'_> {
    /// Move `persons` of source slot `(from, slot)` to the host's member of their household.
    fn take(
        &self,
        pools: &mut [PoolWork],
        from: (usize, usize),
        persons: u64,
        age: Option<usize>,
    ) -> Result<PlaceMoveReceipt, PlaceStaffingError> {
        let source = &mut pools[from.0].slots[from.1];
        let household = source.engine.member.household_id();
        let from_member = source.engine.member.member_id();
        let from_pool = source.engine.pool_id;
        match age {
            None => {
                source.uncovered -= persons;
                source.left_uncovered += persons;
            }
            Some(age) => {
                source.covered[age] -= persons;
                source.left_covered += persons;
            }
        }
        let host = &mut pools[self.host];
        let slot = host
            .slots
            .iter_mut()
            .find(|slot| slot.engine.member.household_id() == household)
            .ok_or_else(|| refuse(StaffingError::PopulationInvariant))?;
        slot.gained += persons;
        Ok(PlaceMoveReceipt {
            period: self.period,
            host_pool: host.receipt.binding().pool_id(),
            host_member: slot.engine.member.member_id(),
            from_pool,
            from_member,
            household_id: household,
            persons,
            covered_age: age.and_then(|age| u8::try_from(age).ok()),
        })
    }

    /// Fill the host's lack: the uncovered first, pool by pool and member by member, then the covered by the
    /// periods since they were laid off, the newest first.
    fn fill(
        &self,
        pools: &mut [PoolWork],
        window: usize,
    ) -> Result<Vec<PlaceMoveReceipt>, PlaceStaffingError> {
        let mut left = pools[self.host].need;
        let mut moves = Vec::new();
        let sources: Vec<(usize, usize)> = self
            .host_pools
            .iter()
            .filter(|&&pool| pool != self.host)
            .flat_map(|&pool| (0..pools[pool].slots.len()).map(move |slot| (pool, slot)))
            .collect();
        for &(pool, slot) in &sources {
            let persons = left.min(pools[pool].slots[slot].uncovered);
            if persons > 0 {
                moves.push(self.take(pools, (pool, slot), persons, None)?);
                left -= persons;
            }
        }
        for age in 0..window {
            for &(pool, slot) in &sources {
                let held = pools[pool].slots[slot]
                    .covered
                    .get(age)
                    .copied()
                    .unwrap_or(0);
                let persons = left.min(held);
                if persons > 0 {
                    moves.push(self.take(pools, (pool, slot), persons, Some(age))?);
                    left -= persons;
                }
            }
        }
        pools[self.host].need = left;
        Ok(moves)
    }
}

/// The receipt the record of layoffs advances from, for one member after the moves.
///
/// A member that took persons on records them as hires from its reserve. A member that lost persons records
/// the uncovered ones who left its opening reserve as having left it before the decision, and the others
/// (the covered) as hires back, which draw the newest cohorts down.
fn record_receipt(slot: &Slot) -> Result<StaffingMemberReceipt, StaffingError> {
    let e = &slot.engine;
    let arithmetic = StaffingError::Arithmetic;
    let (gained, uncovered, covered) = (slot.gained, slot.left_uncovered, slot.left_covered);
    if gained > 0 && uncovered + covered > 0 {
        return Err(StaffingError::PopulationInvariant);
    }
    let receipt = if gained > 0 {
        if e.separations != 0 {
            return Err(StaffingError::PopulationInvariant);
        }
        let force = e
            .member
            .labor_force()
            .checked_add(gained)
            .ok_or(arithmetic)?;
        let closing_employed = e.closing_employed.checked_add(gained).ok_or(arithmetic)?;
        StaffingMemberReceipt {
            member: StaffingMemberBinding::from_living_force(
                e.member.member_id(),
                e.member.household_id(),
                e.member.residence(),
                force,
            ),
            opening_reserve: e.opening_reserve.checked_add(gained).ok_or(arithmetic)?,
            hires: e.hires.checked_add(gained).ok_or(arithmetic)?,
            closing_employed,
            next_opening_hours: closing_employed
                .checked_mul(e.hours_per_person)
                .ok_or(arithmetic)?,
            ..e.clone()
        }
    } else if uncovered + covered > 0 {
        let left_reserve = uncovered.min(e.opening_reserve);
        let pseudo = (uncovered - left_reserve) + covered;
        let (hires, separations) = if e.hires > 0 {
            (e.hires + pseudo, 0)
        } else if pseudo <= e.separations {
            (0, e.separations - pseudo)
        } else {
            (pseudo - e.separations, 0)
        };
        let force = e.member.labor_force() - left_reserve;
        let closing_employed = (e.opening_employed + hires)
            .checked_sub(separations)
            .ok_or(arithmetic)?;
        StaffingMemberReceipt {
            member: e.member.with_living_force(force)?,
            opening_reserve: e.opening_reserve - left_reserve,
            hires,
            separations,
            closing_employed,
            closing_reserve: force.checked_sub(closing_employed).ok_or(arithmetic)?,
            next_opening_hours: closing_employed
                .checked_mul(e.hours_per_person)
                .ok_or(arithmetic)?,
            ..e.clone()
        }
    } else {
        e.clone()
    };
    receipt.validate()?;
    Ok(receipt)
}

/// A member's persons after the period, with the moves.
fn member_after(slot: &Slot) -> Result<StaffingMemberState, StaffingError> {
    let e = &slot.engine;
    let employed = e
        .closing_employed
        .checked_add(slot.gained)
        .ok_or(StaffingError::Arithmetic)?;
    let reserve = e
        .closing_reserve
        .checked_sub(slot.left_uncovered)
        .and_then(|n| n.checked_sub(slot.left_covered))
        .ok_or(StaffingError::PopulationInvariant)?;
    let binding = StaffingMemberBinding::from_living_force(
        e.member.member_id(),
        e.member.household_id(),
        e.member.residence(),
        employed + reserve,
    );
    StaffingMemberState::try_new(binding, employed, reserve)
}

/// Staff a closed period whose people look for work in their place: the engine's decision first, then the
/// moves.
///
/// # Errors
/// `Staffing(..)` for a pool in no place or in two, members that are not the pool's people, or arithmetic;
/// the circuit's refusal of a record of layoffs.
pub(crate) fn staff_places(
    opening: &StaffingState,
    requests: &[StaffingWorkRequest],
    members: &[PoolMembers],
    places: &[StaffingPlace],
    rules: &PlaceRules<'_>,
) -> Result<PlaceStaffing, PlaceStaffingError> {
    let at = positions(opening, places)?;
    let decided = super::advance_staffing_limited(opening, requests, rules.limits)?;
    let mut pools = pools_decided(decided.receipts(), members, &at, rules)?;
    let mut hosts: Vec<usize> = (0..pools.len()).filter(|&i| pools[i].need > 0).collect();
    let wage = |pool: &PoolWork| {
        rules
            .wages
            .get(&pool.receipt.binding().site_id())
            .copied()
            .unwrap_or(0)
    };
    hosts.sort_by_key(|&i| {
        (
            std::cmp::Reverse(wage(&pools[i])),
            std::cmp::Reverse(pools[i].need),
            pools[i].place,
            pools[i].position,
        )
    });
    let mut moves = Vec::new();
    for host in hosts {
        if pools[host].receipt.closing_reserve() != 0 {
            return Err(refuse(StaffingError::PopulationInvariant));
        }
        let row = place_pools(&pools, pools[host].place);
        let taking = Taking {
            period: opening.period(),
            host,
            host_pools: &row,
        };
        moves.extend(taking.fill(&mut pools, rules.window)?);
    }
    conclude(&decided, members, &pools, moves, rules)
}

/// The next period's staffing, hours and receipts, after the moves.
fn conclude(
    decided: &StaffingTransition,
    members: &[PoolMembers],
    pools: &[PoolWork],
    moves: Vec<PlaceMoveReceipt>,
    rules: &PlaceRules<'_>,
) -> Result<PlaceStaffing, PlaceStaffingError> {
    let next = decided.state().period();
    let mut states = Vec::with_capacity(pools.len());
    let mut labor = Vec::with_capacity(pools.len());
    let mut member_labor = Vec::new();
    let mut after: BTreeMap<StaffingPoolId, Vec<StaffingMemberState>> = BTreeMap::new();
    let mut member_receipts = Vec::new();
    let mut record_receipts = Vec::new();
    let mut records = Vec::new();
    for (work, closing) in pools.iter().zip(decided.state().pools()) {
        let binding = work.receipt.binding();
        let hours = binding.policy().hours_per_person();
        let mut rows = Vec::with_capacity(work.slots.len());
        for slot in &work.slots {
            let state = member_after(slot)?;
            member_labor.push(MemberLaborCapacityRow {
                member_id: slot.engine.member.member_id(),
                period: next,
                available_hours: state
                    .employed()
                    .checked_mul(hours)
                    .ok_or(StaffingError::Arithmetic)?,
            });
            member_receipts.push(slot.engine.clone());
            record_receipts.push(record_receipt(slot)?);
            let mut record = slot.covered.clone();
            while record.last() == Some(&0) {
                record.pop();
            }
            if !record.is_empty() {
                records.push((slot.engine.member.member_id(), record));
            }
            rows.push(state);
        }
        let employed: u64 = rows.iter().map(StaffingMemberState::employed).sum();
        let force: u64 = rows.iter().map(|row| row.employed() + row.reserve()).sum();
        let rebound = StaffingPoolBinding::try_new(
            binding.pool_id(),
            binding.site_id(),
            binding.unit_id(),
            force,
            binding.policy(),
            binding.work_sources().to_vec(),
        )?;
        states.push(StaffingPoolState::try_new(
            rebound,
            employed,
            force - employed,
            closing.previous_unretained_hours(),
        )?);
        labor.push(LaborCapacityRow {
            site_id: binding.site_id(),
            unit_id: binding.unit_id(),
            period: next,
            available: employed
                .checked_mul(hours)
                .ok_or(StaffingError::Arithmetic)?,
        });
        after.insert(binding.pool_id(), rows);
    }
    labor.sort_unstable_by_key(|row| (row.site_id, row.unit_id));
    records.sort_by_key(|row: &(StaffingMemberId, Vec<u64>)| row.0);
    let kept = members
        .iter()
        .map(|row| {
            let rows = after
                .remove(&row.pool_id)
                .ok_or(StaffingError::PopulationInvariant)?;
            Ok(PoolMembers {
                pool_id: row.pool_id,
                members: rows,
            })
        })
        .collect::<Result<Vec<_>, StaffingError>>()?;
    Ok(PlaceStaffing {
        state: StaffingState::try_new(next, states)?,
        members: kept,
        labor,
        member_labor,
        receipts: decided.receipts().to_vec(),
        member_receipts,
        moves,
        standing: WorkplaceStanding::opening(),
        stops: Vec::new(),
        record_receipts,
        records: (rules.window > 0 && !rules.recipients.is_empty()).then_some(records),
    })
}

#[cfg(test)]
mod tests {
    use super::{
        staff_places, PlaceRules, PlaceStaffing, PlaceStaffingError, PoolMembers, StaffingPlace,
    };
    use crate::adjustment::{self, SiteTest, StopHold};
    use crate::financial::LayoffRecord;
    use crate::{
        FinalDemandPrincipalId, SiteId, StaffingError, StaffingMemberBinding, StaffingMemberId,
        StaffingMemberState, StaffingPolicy, StaffingPoolBinding, StaffingPoolId,
        StaffingPoolState, StaffingState, StaffingWorkRequest, StaffingWorkSource, UnitId,
    };
    use std::collections::{BTreeMap, BTreeSet};

    const PERIOD: u64 = 5;
    const HPP: u64 = 10;

    fn site(pool: u8) -> SiteId {
        SiteId::from_bytes([pool; 32])
    }
    fn pool_id(pool: u8) -> StaffingPoolId {
        StaffingPoolId::from_bytes([pool; 32])
    }
    fn household(h: u8) -> FinalDemandPrincipalId {
        FinalDemandPrincipalId::from_bytes([100 + h; 32])
    }
    /// The member of household `h` at pool `pool`; the pool's own household has the same number.
    fn member_id(pool: u8, h: u8) -> StaffingMemberId {
        StaffingMemberId::from_bytes([if pool == h { pool } else { 50 + 8 * h + pool }; 32])
    }

    /// One person-holding member: `employed` at work and `reserve` looking.
    fn member(pool: u8, h: u8, employed: u64, reserve: u64) -> StaffingMemberState {
        let binding = StaffingMemberBinding::from_living_force(
            member_id(pool, h),
            household(h),
            "county:26163".parse().expect("a county"),
            employed + reserve,
        );
        StaffingMemberState::try_new(binding, employed, reserve).expect("a member")
    }

    /// A pool of the given members, which together are its people. `previous` is the hours it asked before.
    fn pool(
        pool: u8,
        members: &[(u8, u64, u64)],
        previous: u64,
    ) -> (StaffingPoolState, PoolMembers) {
        let rows: Vec<StaffingMemberState> = members
            .iter()
            .map(|&(h, employed, reserve)| member(pool, h, employed, reserve))
            .collect();
        let employed: u64 = members.iter().map(|m| m.1).sum();
        let force: u64 = members.iter().map(|m| m.1 + m.2).sum();
        let binding = StaffingPoolBinding::try_new(
            pool_id(pool),
            site(pool),
            UnitId::from_bytes([200; 32]),
            force,
            StaffingPolicy::one_period(HPP).expect("a schedule"),
            vec![StaffingWorkSource::MerchantHandling(site(pool))],
        )
        .expect("a binding");
        let state = StaffingPoolState::try_new(binding, employed, force - employed, previous)
            .expect("pool");
        (
            state,
            PoolMembers {
                pool_id: pool_id(pool),
                members: rows,
            },
        )
    }

    fn request(pool: u8, hours: u64) -> StaffingWorkRequest {
        StaffingWorkRequest::new(
            PERIOD,
            pool_id(pool),
            StaffingWorkSource::MerchantHandling(site(pool)),
            site(pool),
            UnitId::from_bytes([200; 32]),
            hours,
        )
    }

    /// A pool's number, its members as (household, employed, reserve), the hours it asks and asked before.
    type PoolRow<'a> = (u8, &'a [(u8, u64, u64)], u64, u64);

    struct Case {
        state: StaffingState,
        members: Vec<PoolMembers>,
        requests: Vec<StaffingWorkRequest>,
        places: Vec<StaffingPlace>,
        recipients: BTreeSet<FinalDemandPrincipalId>,
        wages: BTreeMap<SiteId, i128>,
        limits: BTreeMap<SiteId, u64>,
        records: Vec<LayoffRecord>,
    }

    /// `pools` as `(number, members as (household, employed, reserve), hours asked, hours asked before)`.
    fn case(pools: &[PoolRow<'_>], places: &[&[u8]]) -> Case {
        let mut states = Vec::new();
        let mut members = Vec::new();
        let mut requests = Vec::new();
        for &(number, rows, asked, previous) in pools {
            let (state, pool_members) = pool(number, rows, previous);
            states.push(state);
            members.push(pool_members);
            requests.push(request(number, asked));
        }
        Case {
            state: StaffingState::try_new(PERIOD, states).expect("a state"),
            members,
            requests,
            places: places
                .iter()
                .map(|numbers| StaffingPlace {
                    pools: numbers.iter().map(|&n| pool_id(n)).collect(),
                })
                .collect(),
            recipients: BTreeSet::new(),
            wages: BTreeMap::new(),
            limits: BTreeMap::new(),
            records: Vec::new(),
        }
    }

    fn run(case: &Case) -> Result<PlaceStaffing, PlaceStaffingError> {
        // Every member of a recipient household is paid a wage here.
        let holders: BTreeSet<StaffingMemberId> = case
            .members
            .iter()
            .flat_map(|pool| pool.members.iter())
            .filter(|m| case.recipients.contains(&m.binding().household_id()))
            .map(|m| m.binding().member_id())
            .collect();
        let rules = PlaceRules {
            recipients: &case.recipients,
            holders: &holders,
            window: if case.recipients.is_empty() { 0 } else { 7 },
            records: &case.records,
            wages: &case.wages,
            limits: &case.limits,
        };
        staff_places(
            &case.state,
            &case.requests,
            &case.members,
            &case.places,
            &rules,
        )
    }

    fn force(state: &StaffingState) -> u64 {
        state
            .pools()
            .iter()
            .map(|p| p.binding().labor_force())
            .sum()
    }

    /// The persons of every pool are the persons of its members, and no person was made or lost.
    fn assert_kept(case: &Case, placed: &PlaceStaffing) {
        assert_eq!(force(&case.state), force(&placed.state), "people are kept");
        for pool in placed.state.pools() {
            let members = placed
                .members
                .iter()
                .find(|m| m.pool_id == pool.binding().pool_id())
                .expect("the pool's members");
            let employed: u64 = members
                .members
                .iter()
                .map(StaffingMemberState::employed)
                .sum();
            let reserve: u64 = members
                .members
                .iter()
                .map(StaffingMemberState::reserve)
                .sum();
            assert_eq!(employed, pool.employed(), "the members' employed");
            assert_eq!(reserve, pool.reserve(), "the members' reserve");
            assert_eq!(employed + reserve, pool.binding().labor_force());
        }
    }

    /// Households 1 and 2 are the places' two households. Pool 1 (a host: seven people at work, asks for 100
    /// hours, so lacks 3); pool 2 holds 2 of household 2 looking for work (uncovered) and 4 of household 1
    /// who have just been let go (covered, age 0).
    fn takes_case() -> Case {
        let mut case = case(
            &[
                (1, &[(1, 7, 0), (2, 0, 0)], 100, 100),
                (2, &[(2, 0, 2), (1, 4, 0)], 0, 0),
            ],
            &[&[1, 2]],
        );
        case.recipients.insert(household(1));
        case
    }

    #[test]
    fn a_host_takes_the_uncovered_first() {
        let case = takes_case();
        let placed = run(&case).expect("the place staffs");
        let moves: Vec<_> = placed
            .moves
            .iter()
            .map(|m| (m.from_pool, m.household_id, m.persons, m.covered_age))
            .collect();
        assert_eq!(
            moves,
            [
                (pool_id(2), household(2), 2, None),
                (pool_id(2), household(1), 1, Some(0)),
            ]
        );
        assert!(placed.moves.iter().all(|m| m.host_pool == pool_id(1)));
        assert_eq!(placed.moves[0].host_member, member_id(1, 2));
        assert_eq!(placed.moves[1].host_member, member_id(1, 1));
        assert_eq!(placed.moves[0].from_member, member_id(2, 2));
        assert_eq!(placed.moves[1].from_member, member_id(2, 1));
        let host = &placed.state.pools()[0];
        assert_eq!((host.employed(), host.binding().labor_force()), (10, 10));
        let source = &placed.state.pools()[1];
        assert_eq!((source.employed(), source.reserve()), (0, 3));
        assert_kept(&case, &placed);
    }

    #[test]
    fn the_highest_wage_is_served_first() {
        let mut case = case(
            &[
                (1, &[(1, 5, 0), (2, 0, 0), (3, 0, 0)], 70, 70),
                (2, &[(2, 5, 0), (1, 0, 0), (3, 0, 0)], 70, 70),
                (3, &[(3, 0, 3), (1, 0, 0), (2, 0, 0)], 0, 0),
            ],
            &[&[1, 2, 3]],
        );
        case.wages.insert(site(1), 10_000_000);
        case.wages.insert(site(2), 11_000_000);
        let placed = run(&case).expect("the place staffs");
        let taken = |host: u8| -> u64 {
            placed
                .moves
                .iter()
                .filter(|m| m.host_pool == pool_id(host))
                .map(|m| m.persons)
                .sum()
        };
        assert_eq!((taken(2), taken(1)), (2, 1));
        assert_kept(&case, &placed);
    }

    #[test]
    fn a_seeker_stays_in_their_place() {
        let case = case(
            &[(1, &[(1, 5, 0)], 70, 70), (2, &[(2, 0, 3)], 0, 0)],
            &[&[1], &[2]],
        );
        let placed = run(&case).expect("the places staff");
        assert_eq!(placed.moves.len(), 0);
        assert_eq!(placed.state.pools()[0].employed(), 5);
        assert_eq!(placed.state.pools()[1].reserve(), 3);
        assert_kept(&case, &placed);
    }

    #[test]
    fn a_move_keeps_every_person() {
        let case = takes_case();
        let placed = run(&case).expect("the place staffs");
        assert_kept(&case, &placed);
        assert_eq!(
            placed
                .member_receipts
                .iter()
                .map(|r| r.closing_employed + r.closing_reserve)
                .sum::<u64>(),
            force(&case.state),
            "the engine's own decision before any move"
        );
    }

    #[test]
    fn a_pool_in_no_place_is_refused() {
        let case = case(
            &[(1, &[(1, 5, 0)], 70, 70), (2, &[(2, 0, 3)], 0, 0)],
            &[&[1]],
        );
        assert_eq!(
            run(&case),
            Err(PlaceStaffingError::Staffing(
                StaffingError::PopulationInvariant
            ))
        );
    }

    #[test]
    fn a_pool_in_two_places_is_refused() {
        let case = case(
            &[(1, &[(1, 5, 0)], 70, 70), (2, &[(2, 0, 3)], 0, 0)],
            &[&[1, 2], &[2]],
        );
        assert_eq!(
            run(&case),
            Err(PlaceStaffingError::Staffing(StaffingError::DuplicatePool))
        );
    }

    #[test]
    fn a_limit_caps_what_a_host_takes() {
        let mut case = takes_case();
        // Pool 1 employs 7 and lacks 3; with room for one more person it takes one.
        case.limits.insert(site(1), 8);
        let placed = run(&case).expect("the place staffs");
        let taken: u64 = placed.moves.iter().map(|m| m.persons).sum();
        assert_eq!(taken, 1);
        assert_eq!(placed.state.pools()[0].employed(), 8);
        assert_kept(&case, &placed);
    }

    #[test]
    fn a_limit_below_the_employed_lets_people_go_to_the_reserve() {
        let mut case = case(&[(1, &[(1, 7, 0)], 70, 70)], &[&[1]]);
        case.limits.insert(site(1), 3);
        let placed = run(&case).expect("the place staffs");
        let pool = &placed.state.pools()[0];
        assert_eq!((pool.employed(), pool.reserve()), (3, 4));
        assert_kept(&case, &placed);
    }

    fn test_of(attended: u64, unattended: u64) -> SiteTest {
        SiteTest {
            available: attended + unattended,
            attended,
            unattended,
            bill: 0,
            cash: 0,
            employed: 5,
            hours_per_person: 8,
            rate: 10_000_000,
        }
    }

    #[test]
    fn a_workplace_that_could_not_pay_keeps_whom_it_paid() {
        let verdict = adjustment::judge(StopHold::Free, &test_of(20, 20)).expect("a verdict");
        assert!(verdict.could_not_pay);
        assert_eq!(verdict.hold, StopHold::Held);
        assert_eq!(verdict.limit, Some(3));
    }

    #[test]
    fn a_held_workplace_that_paid_everyone_is_free() {
        let verdict = adjustment::judge(StopHold::Held, &test_of(40, 0)).expect("a verdict");
        assert!(!verdict.could_not_pay);
        assert_eq!(verdict.hold, StopHold::Free);
        assert_eq!(verdict.limit, None);
    }

    #[test]
    fn a_held_workplace_hires_only_as_far_as_its_money() {
        let test = SiteTest {
            available: 0,
            bill: 400_000_000,
            cash: 500_000_000,
            ..test_of(0, 0)
        };
        let verdict = adjustment::judge(StopHold::Held, &test).expect("a verdict");
        assert!(!verdict.could_not_pay);
        assert_eq!(verdict.hold, StopHold::Held);
        assert_eq!(verdict.limit, Some(6));
    }

    #[test]
    fn a_free_workplace_that_paid_has_no_limit() {
        let verdict = adjustment::judge(StopHold::Free, &test_of(40, 0)).expect("a verdict");
        assert_eq!(verdict.hold, StopHold::Free);
        assert_eq!(verdict.limit, None);
    }

    #[test]
    fn a_held_workplace_that_owes_its_own_wages_hires_nobody() {
        let test = SiteTest {
            available: 0,
            bill: 600_000_000,
            cash: 500_000_000,
            ..test_of(0, 0)
        };
        let verdict = adjustment::judge(StopHold::Held, &test).expect("a verdict");
        assert_eq!(verdict.limit, Some(5));
    }
}
