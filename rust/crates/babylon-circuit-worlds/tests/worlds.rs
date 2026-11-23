//! The bench's worlds: the plain world, the national figures, the six pushes of the opening, and
//! the seekers' rows every world carries.

use babylon_circuit_worlds::doubled::{self, Economy, Figures, OpeningPush, Pushed, Scale, World};
use babylon_circuit_worlds::ids;
use babylon_circuit_worlds::{
    Household, Kind, Place, Places, Runner, Shock, ShockError, Workplace, WorldError,
};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CircuitAccounting, LaborCompensation, MaterialCircuitState, MonetaryCircuit,
    PricePolicy, StaffingMemberReceipt,
};
use std::error::Error;

type TestResult = Result<(), Box<dyn Error>>;

const WORLDS: [(Economy, Scale); 4] = [
    (Economy::Plain, Scale::Small),
    (Economy::Plain, Scale::National),
    (Economy::Fund, Scale::Small),
    (Economy::Fund, Scale::National),
];

fn dollars(value: i128) -> Currency {
    Currency::from_micro_units(value * 1_000_000)
}

fn world(economy: Economy, scale: Scale) -> World {
    World {
        economy,
        scale,
        pushed: None,
    }
}

fn pushed(economy: Economy, push: OpeningPush, places: Places) -> World {
    World {
        economy,
        scale: Scale::Small,
        pushed: Some(Pushed { push, places }),
    }
}

fn monetary(state: &MaterialCircuitState) -> Result<&MonetaryCircuit, WorldError> {
    match &state.accounting {
        CircuitAccounting::Monetary(circuit) => Ok(&**circuit),
        CircuitAccounting::PhysicalControl => Err(WorldError::Arithmetic),
    }
}

fn monetary_mut(state: &mut MaterialCircuitState) -> Result<&mut MonetaryCircuit, WorldError> {
    match &mut state.accounting {
        CircuitAccounting::Monetary(circuit) => Ok(&mut **circuit),
        CircuitAccounting::PhysicalControl => Err(WorldError::Arithmetic),
    }
}

fn cash(state: &MaterialCircuitState, account: AccountId) -> Result<Currency, Box<dyn Error>> {
    Ok(monetary(state)?.book.cash(account)?)
}

fn site(place: Place, kind: Kind) -> AccountId {
    AccountId::Site(Workplace { place, kind }.site_id())
}

fn total(state: &MaterialCircuitState) -> Result<i128, Box<dyn Error>> {
    Ok(monetary(state)?
        .book
        .total_cash_and_reserves()?
        .micro_units())
}

#[test]
fn the_plain_world_opens_with_10320_dollars_and_eighty_people() -> TestResult {
    let plain = world(Economy::Plain, Scale::Small);
    let households = plain.households();
    assert_eq!(households.len(), 10);
    assert!(households
        .iter()
        .all(|h| !matches!(h, Household::Supported(_))));
    let state = doubled::opening_state_of(&plain)?;
    let circuit = monetary(&state)?;
    let recurring = circuit.recurring.as_ref().ok_or("no recurring economy")?;
    for place in Place::ALL {
        let cohorts: Vec<u64> = [Kind::Utility, Kind::Farm, Kind::Clinic, Kind::Shop]
            .iter()
            .map(|&kind| {
                let id = Household::Workers(Workplace { place, kind }).principal();
                recurring
                    .households
                    .iter()
                    .find(|c| c.principal_id == id)
                    .map(|c| c.persons)
                    .ok_or("a workers cohort is missing")
            })
            .collect::<Result<_, _>>()?;
        let owner = recurring
            .households
            .iter()
            .find(|c| c.principal_id == Household::Owner(place).principal())
            .map(|c| c.persons)
            .ok_or("an owner cohort is missing")?;
        assert_eq!(
            [cohorts[0], cohorts[1], cohorts[2], cohorts[3], owner],
            [15, 5, 5, 5, 10]
        );
        assert_eq!(
            cash(
                &state,
                AccountId::Household(Household::Owner(place).principal())
            )?,
            dollars(800)
        );
    }
    assert_eq!(recurring.households.len(), 10);
    assert!(circuit
        .book
        .cash_accounts()
        .all(|(id, _)| !matches!(id, AccountId::Public(_))));
    let f = &circuit.financial;
    assert!(f.taxes.is_empty() && f.public_budgets.is_empty());
    assert!(f.public_allocations.is_empty() && f.programs.is_empty() && f.locations.is_empty());
    let (bindings, _) = doubled::staffing_of(&plain)?;
    for binding in &bindings {
        assert_eq!(binding.policy().hours_per_person(), 8);
    }
    let mut hours = [0_u64; 8];
    for row in &state.labor {
        hours[Workplace::from_site(row.site_id)
            .ok_or("unknown site")?
            .index()] = row.available;
    }
    assert_eq!(hours, [120, 40, 40, 40, 120, 40, 40, 40]);
    let catalog = doubled::catalog_of(&plain, &Figures::OPENING)?;
    assert_eq!(catalog.household_needs.len(), 30);
    let policy = catalog.market_clearing.as_ref().ok_or("no market")?;
    assert_eq!(policy.household_wants.len(), 30);
    assert_eq!(total(&state)?, 10_320_000_000);
    Ok(())
}

#[test]
fn the_national_figures_step_by_a_fortieth_and_double_the_site_cash() -> TestResult {
    let national = world(Economy::Fund, Scale::National);
    let state = doubled::opening_state_of(&national)?;
    let circuit = monetary(&state)?;
    let recurring = circuit.recurring.as_ref().ok_or("no recurring economy")?;
    for offer in &recurring.offers {
        let workplace = Workplace::from_site(offer.site_id).ok_or("unknown site")?;
        let want = [300_000, 625_000, 750_000, 950_000][workplace.kind.index()];
        let (minimum, maximum, step) = match offer.pricing {
            PricePolicy::Responsive {
                minimum,
                maximum,
                step,
                ..
            }
            | PricePolicy::ServiceResponsive {
                minimum,
                maximum,
                step,
            } => (minimum, maximum, step),
            PricePolicy::Fixed => return Err("a fixed price".into()),
        };
        assert_eq!(step, Currency::from_micro_units(want), "{workplace:?}");
        assert_eq!(minimum, Currency::from_micro_units(1_000_000));
        assert_eq!(maximum, Currency::from_micro_units(1_000_000_000));
    }
    for place in Place::ALL {
        for (kind, want) in [
            (Kind::Utility, 2_400),
            (Kind::Farm, 1_760),
            (Kind::Clinic, 1_760),
            (Kind::Shop, 2_800),
        ] {
            assert_eq!(cash(&state, site(place, kind))?, dollars(want));
        }
    }
    assert_eq!(total(&state)?, 20_960_000_000);
    let plain = doubled::opening_state_of(&world(Economy::Plain, Scale::National))?;
    assert_eq!(total(&plain)?, 19_040_000_000);
    Ok(())
}

/// The state with the parts a push moves set aside, so that the rest can be compared whole.
fn rest(
    state: &MaterialCircuitState,
    quiet: &MaterialCircuitState,
    set_aside: impl Fn(&mut MonetaryCircuit),
) -> Result<MaterialCircuitState, Box<dyn Error>> {
    let mut rest = state.clone();
    let circuit = monetary_mut(&mut rest)?;
    circuit.book = monetary(quiet)?.book.clone();
    circuit.costs = monetary(quiet)?.costs.clone();
    set_aside(circuit);
    Ok(rest)
}

fn owner_cohorts(circuit: &MonetaryCircuit) -> Vec<u64> {
    circuit
        .recurring
        .as_ref()
        .map(|r| {
            r.households
                .iter()
                .filter(|c| {
                    matches!(
                        Household::from_principal(c.principal_id),
                        Some(Household::Owner(_))
                    )
                })
                .map(|c| c.persons)
                .collect()
        })
        .unwrap_or_default()
}

fn blank_owner_cohorts(circuit: &mut MonetaryCircuit) {
    if let Some(recurring) = circuit.recurring.as_mut() {
        for cohort in &mut recurring.households {
            if matches!(
                Household::from_principal(cohort.principal_id),
                Some(Household::Owner(_))
            ) {
                cohort.persons = 0;
            }
        }
    }
}

fn blank_wages(circuit: &mut MonetaryCircuit) {
    for row in &mut circuit.employment {
        row.compensation = LaborCompensation::Wage(dollars(10));
    }
}

fn blank_fund_rates(circuit: &mut MonetaryCircuit) {
    for row in &mut circuit.financial.taxes {
        row.rate_bps = 0;
    }
}

fn wages_of(circuit: &MonetaryCircuit, workplace: Workplace) -> Vec<LaborCompensation> {
    circuit
        .employment
        .iter()
        .filter(|row| row.site_id == workplace.site_id())
        .map(|row| row.compensation)
        .collect()
}

#[test]
fn each_opening_push_moves_only_its_figure() -> TestResult {
    let quiet = doubled::opening_state_of(&World::scene())?;
    let quiet_total = total(&quiet)?;
    assert_eq!(quiet_total, 12_240_000_000);
    let both = Places::Both;

    // P1 and P7: the owner cohorts; stocks and purchase limits stay.
    for (push, want) in [(OpeningPush::LessDemand, 4), (OpeningPush::MoreMouths, 12)] {
        let state = doubled::opening_state_of(&pushed(Economy::Fund, push, both))?;
        assert_eq!(owner_cohorts(monetary(&state)?), [want, want], "{push:?}");
        assert_eq!(
            rest(&state, &quiet, blank_owner_cohorts)?,
            rest(&quiet, &quiet, blank_owner_cohorts)?,
            "{push:?}"
        );
    }

    // P3: the shop opens with half its cash.
    let state = doubled::opening_state_of(&pushed(Economy::Fund, OpeningPush::LessMoney, both))?;
    for place in Place::ALL {
        assert_eq!(cash(&state, site(place, Kind::Shop))?, dollars(700));
    }
    assert_eq!(total(&state)?, 10_840_000_000);
    assert_eq!(rest(&state, &quiet, |_| {})?, rest(&quiet, &quiet, |_| {})?);

    // P4: the four rows at each clinic's site pay $11, and nothing else does.
    let state = doubled::opening_state_of(&pushed(Economy::Fund, OpeningPush::HigherPay, both))?;
    for place in Place::ALL {
        let clinic = Workplace {
            place,
            kind: Kind::Clinic,
        };
        let rows = wages_of(monetary(&state)?, clinic);
        assert_eq!(rows.len(), 4);
        assert!(rows
            .iter()
            .all(|r| *r == LaborCompensation::Wage(dollars(11))));
    }
    assert_eq!(
        monetary(&state)?
            .employment
            .iter()
            .filter(|r| r.compensation == LaborCompensation::Wage(dollars(11)))
            .count(),
        8
    );
    assert_eq!(
        rest(&state, &quiet, blank_wages)?,
        rest(&quiet, &quiet, blank_wages)?
    );

    // P4a: only clinic A's four rows.
    let state =
        doubled::opening_state_of(&pushed(Economy::Fund, OpeningPush::HigherPay, Places::A))?;
    let high: Vec<_> = monetary(&state)?
        .employment
        .iter()
        .filter(|r| r.compensation == LaborCompensation::Wage(dollars(11)))
        .map(|r| r.site_id)
        .collect();
    let clinic_a = Workplace {
        place: Place::A,
        kind: Kind::Clinic,
    }
    .site_id();
    assert_eq!(high.len(), 4);
    assert!(high.iter().all(|s| *s == clinic_a));

    // P5: the 16 fund rows at 1,125 bps and the 16 treasury rows at 500.
    let state =
        doubled::opening_state_of(&pushed(Economy::Fund, OpeningPush::LowerFundTaxes, both))?;
    let taxes = &monetary(&state)?.financial.taxes;
    assert_eq!(taxes.len(), 32);
    for row in taxes {
        let want = if row.public_recipient == ids::treasury() {
            500
        } else {
            1_125
        };
        assert_eq!(row.rate_bps, want);
    }
    assert_eq!(
        rest(&state, &quiet, blank_fund_rates)?,
        rest(&quiet, &quiet, blank_fund_rates)?
    );
    Ok(())
}

#[test]
fn the_power_cut_at_the_opening_plans_in_ten_hour_batches() -> TestResult {
    let cut = pushed(Economy::Fund, OpeningPush::PowerCut, Places::Both);
    let state = doubled::opening_state_of(&cut)?;
    let utility = |place| Workplace {
        place,
        kind: Kind::Utility,
    };
    for place in Place::ALL {
        let site_id = utility(place).site_id();
        let commitments: Vec<u64> = state
            .production_commitments
            .iter()
            .filter(|c| c.site_id == site_id)
            .map(|c| c.planned_batches)
            .collect();
        assert_eq!(commitments, [12]);
        let rows: Vec<u64> = state
            .capacities
            .iter()
            .filter(|c| c.site_id == site_id)
            .map(|c| c.available_batches)
            .collect();
        assert_eq!(rows.len(), 1_000);
        assert!(rows.iter().all(|&batches| batches == 12));
        let hours = state
            .labor
            .iter()
            .find(|row| row.site_id == site_id)
            .map(|row| row.available);
        assert_eq!(hours, Some(120));
    }
    let mut runner = Runner::open_world(&cut)?;
    for place in Place::ALL {
        assert!(runner.shocks().holds(Shock::PowerCut, place, 1));
        assert_eq!(
            runner.lift(Shock::PowerCut, place),
            Err(ShockError::HoldsUntilStartOver)
        );
    }
    let first = runner.step()?;
    assert_eq!(first.figures, cut.opening_figures());
    assert_eq!(first.figures.utility_hours_per_batch, [10, 10]);

    // P6a: place A only; place B is as quiet.
    let cut_a = pushed(Economy::Fund, OpeningPush::PowerCut, Places::A);
    let state = doubled::opening_state_of(&cut_a)?;
    let quiet = doubled::opening_state_of(&World::scene())?;
    let batches = |state: &MaterialCircuitState, place| -> Vec<u64> {
        state
            .production_commitments
            .iter()
            .filter(|c| c.site_id == utility(place).site_id())
            .map(|c| c.planned_batches)
            .collect()
    };
    assert_eq!(batches(&state, Place::A), [12]);
    assert_eq!(batches(&state, Place::B), batches(&quiet, Place::B));
    let runner = Runner::open_world(&cut_a)?;
    assert!(runner.shocks().holds(Shock::PowerCut, Place::A, 1));
    assert!(!runner.shocks().holds(Shock::PowerCut, Place::B, 1));
    Ok(())
}

#[test]
fn a_push_the_world_cannot_take_is_refused() {
    let plain = pushed(Economy::Plain, OpeningPush::LowerFundTaxes, Places::Both);
    assert_eq!(
        doubled::opening_state_of(&plain),
        Err(WorldError::PushNotInThisWorld)
    );
    let one_place = pushed(Economy::Fund, OpeningPush::LowerFundTaxes, Places::A);
    assert_eq!(
        doubled::opening_state_of(&one_place),
        Err(WorldError::PushOnOnePlace)
    );
}

#[test]
fn the_scene_world_is_the_runner_s_opening() -> TestResult {
    let mut one = Runner::open()?;
    let mut two = Runner::open_world(&World::scene())?;
    for _ in 0..3 {
        one.step()?;
        two.step()?;
    }
    assert_eq!(one.history(), two.history());
    assert_eq!(one.state(), two.state());
    assert_eq!(two.world(), &World::scene());
    Ok(())
}

#[test]
fn every_world_authors_the_seekers_rows() -> TestResult {
    for (economy, scale) in WORLDS {
        let state = doubled::opening_state_of(&world(economy, scale))?;
        let circuit = monetary(&state)?;
        assert_eq!(circuit.employment.len(), 32, "{economy:?} {scale:?}");
        assert_eq!(circuit.member_labor.len(), 32);
        let mut pairs = 0;
        for place in Place::ALL {
            let mut in_place = 0;
            for (home, host) in Workplace::pairs().filter(|(h, _)| h.place == place) {
                let id = host.pair_member_id(home);
                let row = circuit
                    .employment
                    .iter()
                    .find(|row| row.member_id == id)
                    .ok_or("a pair row is missing")?;
                let own = circuit
                    .employment
                    .iter()
                    .find(|row| row.member_id == host.member_id())
                    .ok_or("an own row is missing")?;
                assert_eq!(row.site_id, host.site_id());
                assert_eq!(row.compensation, own.compensation);
                assert_eq!(row.payee, home.workers().principal());
                let hours = circuit
                    .member_labor
                    .iter()
                    .find(|row| row.member_id == id)
                    .ok_or("a pair member has no hours row")?;
                assert_eq!((hours.period, hours.available_hours), (1, 0));
                assert_eq!(host.place, home.place);
                in_place += 1;
            }
            assert_eq!(in_place, 12);
            pairs += in_place;
        }
        assert_eq!(pairs, 24);
        let mut ids: Vec<_> = circuit.employment.iter().map(|r| r.member_id).collect();
        ids.sort();
        ids.dedup();
        assert_eq!(ids.len(), 32);
    }
    Ok(())
}

fn is_zero(receipt: &StaffingMemberReceipt) -> bool {
    [
        receipt.opening_employed,
        receipt.opening_reserve,
        receipt.hires,
        receipt.separations,
        receipt.closing_employed,
        receipt.closing_reserve,
        receipt.next_opening_hours,
    ]
    .iter()
    .all(|&n| n == 0)
}

#[test]
fn the_pair_rows_take_nothing() -> TestResult {
    let mut runner = Runner::open()?;
    for _ in 0..34 {
        runner.step()?;
    }
    for result in runner.history() {
        assert_eq!(result.members.len(), 32, "period {}", result.period);
        assert_eq!(result.receipts.member_labor_use.len(), 32);
        for workplace in Workplace::ALL {
            let own = workplace.member_id();
            let pool: Vec<_> = result
                .members
                .iter()
                .filter(|m| Workplace::from_site(m.site_id) == Some(workplace))
                .collect();
            assert_eq!(pool.len(), 4);
            for receipt in pool {
                if receipt.member.member_id() == own {
                    assert_eq!(
                        receipt.opening_employed,
                        workplace.workers().opening_persons()
                    );
                } else {
                    assert!(is_zero(receipt), "period {} {receipt:?}", result.period);
                }
            }
            for row in result
                .receipts
                .member_labor_use
                .iter()
                .filter(|row| row.site_id == workplace.site_id() && row.member_id != own)
            {
                assert_eq!(
                    [
                        row.available_hours,
                        row.planned_hours,
                        row.unplanned_hours,
                        row.attended_hours,
                        row.unattended_hours,
                        row.production_hours,
                        row.handling_hours,
                        row.maintenance_hours,
                        row.installation_hours,
                        row.idle_hours,
                    ],
                    [0; 10]
                );
                assert_eq!(row.accrued_wages, Currency::from_micro_units(0));
            }
        }
    }
    Ok(())
}

#[test]
fn every_world_and_push_steps_with_money_and_people_kept() -> TestResult {
    let mut worlds: Vec<World> = WORLDS.iter().map(|&(e, s)| world(e, s)).collect();
    for push in [
        OpeningPush::LessDemand,
        OpeningPush::LessMoney,
        OpeningPush::HigherPay,
        OpeningPush::LowerFundTaxes,
        OpeningPush::PowerCut,
        OpeningPush::MoreMouths,
    ] {
        for places in [Places::Both, Places::A] {
            for economy in [Economy::Plain, Economy::Fund] {
                let candidate = pushed(economy, push, places);
                if doubled::opening_state_of(&candidate).is_ok() {
                    worlds.push(candidate);
                }
            }
        }
    }
    for world in &worlds {
        let mut runner = Runner::open_world(world)?;
        for _ in 0..4 {
            runner.step()?;
        }
        assert!(runner.catalog().is_some());
    }
    Ok(())
}
