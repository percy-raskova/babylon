//! A record of layoffs is held only by a member paid a wage, in both of the engine's counts: the keeper
//! (`advance_records`) and the staffing in places (`slots_of`) stand on one rule.
//!
//! The fixture is the doubled world with its fund (a program that pays after a layoff, whose recipients are
//! the workers' households) and the six rules, opened and then changed by the test so that the first close
//! separates the people of two workplaces, the clinic of place A and the clinic of place B, from their work: their
//! planned production is set to nothing and the opening's retained hours of their pools are taken away (the
//! staffing retains the previous period's hours for one period, so without that nobody is separated at the
//! first close). The clinic's own member then has its employment term's compensation changed as each case
//! needs; place B's clinic's own member stays paid a wage and is the control.

use babylon_circuit_worlds::doubled::{self, Figures};
use babylon_circuit_worlds::{Kind, Place, ShockBook, Workplace, World};
use babylon_material_circuit::{
    self as engine, CircuitAccounting, LaborCompensation, MaterialCircuitError,
    MaterialCircuitState, MaterialCircuitTransition, PlaceStaffing, StaffingMemberId,
    StaffingPoolState, StaffingState, WorkplaceStanding,
};

fn workplace(place: Place, kind: Kind) -> Workplace {
    Workplace { place, kind }
}

/// Open the doubled world with its six rules, lay off the people of the two clinics at the first
/// close, give the clinic's own member `changed` as its compensation (when given), and close period 1 the
/// way the runner does for a world whose people look for work in their place. Returns the clinic's own
/// member, the control clinic's own member, the persons of the clinic's own member that the staffing
/// separated from their work at the close, and the close.
fn close_first_period(
    changed: Option<LaborCompensation>,
) -> (
    StaffingMemberId,
    StaffingMemberId,
    u64,
    Result<MaterialCircuitTransition, MaterialCircuitError>,
) {
    let mut world = World::scene();
    world.rules = World::switches_at(world.scale).to_vec();
    let figures: Figures = ShockBook::default().figures(1);
    let catalog = doubled::catalog_of(&world, &figures, &world.rules).expect("the catalog");
    let mut state: MaterialCircuitState = doubled::opening_state_of(&world).expect("the opening");
    let laid_off = [
        workplace(Place::A, Kind::Clinic),
        workplace(Place::B, Kind::Clinic),
    ];
    let sites: Vec<_> = laid_off.iter().map(|w| w.site_id()).collect();
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("the opening is monetary");
    };
    if let Some(compensation) = changed {
        for terms in economy
            .employment
            .iter_mut()
            .filter(|terms| terms.member_id == laid_off[0].member_id())
        {
            terms.compensation = compensation;
        }
    }
    let members: Vec<_> = economy
        .employment
        .iter()
        .filter(|terms| sites.contains(&terms.site_id))
        .map(|terms| terms.member_id)
        .collect();
    for row in economy
        .member_labor
        .iter_mut()
        .filter(|row| members.contains(&row.member_id))
    {
        row.available_hours = 0;
    }
    let recurring = economy.recurring.as_mut().expect("a recurring economy");
    for row in recurring
        .attendance
        .iter_mut()
        .filter(|row| sites.contains(&row.site_id))
    {
        row.planned_hours = 0;
    }
    for w in laid_off {
        let process = w.process_id().expect("a process");
        for row in recurring
            .production
            .iter_mut()
            .filter(|row| row.process_id == process)
        {
            row.planned_batches = 0;
        }
    }
    for row in state
        .labor
        .iter_mut()
        .filter(|row| sites.contains(&row.site_id))
    {
        row.available = 0;
    }
    let opened = doubled::staffing_of(&world).expect("staffing").1;
    let pools_of: Vec<_> = opened
        .pools()
        .iter()
        .map(|pool| {
            let previous = if sites.contains(&pool.binding().site_id()) {
                0
            } else {
                pool.previous_unretained_hours()
            };
            StaffingPoolState::try_new(
                pool.binding().clone(),
                pool.employed(),
                pool.reserve(),
                previous,
            )
            .expect("a pool")
        })
        .collect();
    let staffing = StaffingState::try_new(opened.period(), pools_of).expect("a state");
    let pools = doubled::pool_members_of(&world).expect("members");
    let closed = engine::close_material_period_with_standing(
        &catalog,
        &state,
        &WorkplaceStanding::opening(),
    )
    .expect("the close");
    let placed = closed
        .staff_in_places(&catalog, &staffing, &pools, &doubled::places())
        .expect("staffing in places");
    let clinic = laid_off[0].member_id();
    let separated = separations_of(&placed, clinic);
    (
        clinic,
        laid_off[1].member_id(),
        separated,
        closed.finish_with_place_staffing(&catalog, &placed),
    )
}

/// The persons of `member` that the staffing's own decision separated from their work at the close.
fn separations_of(placed: &PlaceStaffing, member: StaffingMemberId) -> u64 {
    placed
        .member_receipts
        .iter()
        .filter(|row| row.member.member_id() == member)
        .map(|row| row.separations)
        .sum()
}

fn records(closed: &MaterialCircuitTransition) -> Vec<(StaffingMemberId, Vec<u64>)> {
    let CircuitAccounting::Monetary(economy) = &closed.state.accounting else {
        panic!("monetary");
    };
    economy
        .financial
        .layoffs
        .iter()
        .map(|r| (r.member_id, r.cohorts.clone()))
        .collect()
}

#[test]
fn a_working_owner_who_loses_their_work_holds_no_record() {
    let (clinic, control, separated, closed) =
        close_first_period(Some(LaborCompensation::WorkingOwner));
    let closed = closed.expect("the period closes");
    let all = records(&closed);
    assert!(separated > 0, "the owner lost work at this close");
    assert!(
        all.iter().all(|(m, _)| *m != clinic),
        "no record for the owner"
    );
    assert!(
        all.iter().any(|(m, _)| *m == control),
        "a member paid a wage and laid off at the same close has a record"
    );
}

#[test]
fn an_unpaid_family_member_who_loses_their_work_holds_no_record() {
    let (clinic, control, separated, closed) =
        close_first_period(Some(LaborCompensation::UnpaidFamily));
    let closed = closed.expect("the period closes");
    let all = records(&closed);
    assert!(separated > 0, "the member lost work at this close");
    assert!(
        all.iter().all(|(m, _)| *m != clinic),
        "no record for the member"
    );
    assert!(
        all.iter().any(|(m, _)| *m == control),
        "a member paid a wage and laid off at the same close has a record"
    );
}

#[test]
fn a_wage_member_who_loses_their_work_holds_a_record_as_before() {
    let (clinic, control, separated, closed) = close_first_period(None);
    let closed = closed.expect("the period closes");
    assert!(separated > 0, "the member lost work at this close");
    let all = records(&closed);
    assert_eq!(all, vec![(clinic, vec![2]), (control, vec![2])]);
}
