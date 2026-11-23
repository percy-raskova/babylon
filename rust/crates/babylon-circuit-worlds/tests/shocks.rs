//! The shocks: figures of the catalog, struck and lifted between periods, and nothing else.

use babylon_circuit_worlds::doubled::{self, Figures};
use babylon_circuit_worlds::{
    Kind, Lasts, Place, Places, Runner, Shock, ShockError, Strike, Workplace,
};
use std::error::Error;

type TestResult = Result<(), Box<dyn Error>>;

fn run(periods: u64) -> Result<Runner, Box<dyn Error>> {
    let mut runner = Runner::open()?;
    step(&mut runner, periods)?;
    Ok(runner)
}

fn step(runner: &mut Runner, periods: u64) -> TestResult {
    for _ in 0..periods {
        runner.step()?;
    }
    Ok(())
}

fn figures_at(runner: &Runner, period: u64) -> Result<Figures, Box<dyn Error>> {
    let index = usize::try_from(period.checked_sub(1).ok_or("period 0")?)?;
    Ok(runner
        .history()
        .get(index)
        .ok_or("period not closed")?
        .figures)
}

fn made_at(runner: &Runner, period: u64, workplace: Workplace) -> Result<u64, Box<dyn Error>> {
    let index = usize::try_from(period.checked_sub(1).ok_or("period 0")?)?;
    Ok(runner
        .history()
        .get(index)
        .ok_or("period not closed")?
        .summary
        .made[workplace.index()])
}

const FARM_A: Workplace = Workplace {
    place: Place::A,
    kind: Kind::Farm,
};
const FARM_B: Workplace = Workplace {
    place: Place::B,
    kind: Kind::Farm,
};
const UTILITY_A: Workplace = Workplace {
    place: Place::A,
    kind: Kind::Utility,
};

#[test]
fn the_harvest_fails_in_place_a_from_the_next_period() -> TestResult {
    let mut runner = run(1)?;
    runner.strike(Shock::HarvestFails, Places::A, Lasts::UntilLifted)?;
    step(&mut runner, 1)?;
    assert_eq!(figures_at(&runner, 1)?, Figures::OPENING);
    let second = figures_at(&runner, 2)?;
    assert_eq!(second.farm_yield, [9, 10]);
    assert_eq!(made_at(&runner, 2, FARM_A)?, 36);
    assert_eq!(made_at(&runner, 2, FARM_B)?, 40);
    Ok(())
}

#[test]
fn a_ten_period_harvest_returns_on_the_eleventh() -> TestResult {
    let mut runner = run(2)?;
    runner.strike(Shock::HarvestFails, Places::A, Lasts::TenPeriods)?;
    step(&mut runner, 11)?;
    for period in 3..=12 {
        assert_eq!(figures_at(&runner, period)?.farm_yield[0], 9, "{period}");
    }
    assert_eq!(figures_at(&runner, 13)?.farm_yield[0], 10);
    assert_eq!(
        runner.shocks().strikes(),
        [Strike {
            shock: Shock::HarvestFails,
            place: Place::A,
            lasts: Lasts::TenPeriods,
            from: 3,
            until: Some(13),
        }]
    );
    Ok(())
}

#[test]
fn money_and_people_stay_exact_under_every_shock_for_60_periods() -> TestResult {
    for shock in Shock::ALL {
        for places in [Places::A, Places::B, Places::Both] {
            let mut runner = run(4)?;
            runner.strike(shock, places, Lasts::UntilLifted)?;
            step(&mut runner, 56)?;
            assert_eq!(runner.history().len(), 60);
        }
    }
    let mut harvest = run(4)?;
    harvest.strike(Shock::HarvestFails, Places::A, Lasts::UntilLifted)?;
    step(&mut harvest, 56)?;
    assert_eq!(figures_at(&harvest, 60)?.farm_yield[0], 9);
    assert_eq!(made_at(&harvest, 60, FARM_A)?, 36);
    let mut cut = run(4)?;
    cut.strike(Shock::PowerCut, Places::A, Lasts::UntilLifted)?;
    step(&mut cut, 56)?;
    // Measured: the quiet 120 holds to period 4; the cut's first period (5) and the next make
    // 108; by period 60 the utility makes 81.
    assert_eq!(made_at(&cut, 5, UTILITY_A)?, 108);
    assert_eq!(made_at(&cut, 6, UTILITY_A)?, 108);
    assert_eq!(made_at(&cut, 60, UTILITY_A)?, 81);
    Ok(())
}

#[test]
fn a_harvest_lifted_returns_from_the_next_period() -> TestResult {
    let mut runner = run(4)?;
    runner.strike(Shock::HarvestFails, Places::A, Lasts::UntilLifted)?;
    step(&mut runner, 16)?;
    runner.lift(Shock::HarvestFails, Place::A)?;
    step(&mut runner, 1)?;
    for period in 5..=20 {
        assert_eq!(figures_at(&runner, period)?.farm_yield[0], 9, "{period}");
    }
    assert_eq!(figures_at(&runner, 21)?.farm_yield[0], 10);
    assert_eq!(
        runner.shocks().strikes().first().map(|s| s.until),
        Some(Some(21))
    );
    Ok(())
}

#[test]
fn a_strike_lifted_before_it_holds_changes_nothing() -> TestResult {
    let mut one = run(3)?;
    let mut two = run(3)?;
    one.strike(Shock::HarvestFails, Places::A, Lasts::UntilLifted)?;
    one.lift(Shock::HarvestFails, Place::A)?;
    assert_eq!(one.shocks().strikes(), []);
    step(&mut one, 5)?;
    step(&mut two, 5)?;
    assert_eq!(one.history(), two.history());
    Ok(())
}

fn shocked() -> Result<Runner, Box<dyn Error>> {
    let mut runner = run(2)?;
    runner.strike(Shock::HarvestFails, Places::Both, Lasts::TenPeriods)?;
    step(&mut runner, 4)?;
    runner.strike(Shock::PowerCut, Places::B, Lasts::UntilLifted)?;
    step(&mut runner, 24)?;
    Ok(runner)
}

#[test]
fn the_same_shocked_steps_give_the_same_bytes_twice() -> TestResult {
    let (one, two) = (shocked()?, shocked()?);
    assert_eq!(one.history().len(), 30);
    assert_eq!(one.history(), two.history());
    Ok(())
}

#[test]
fn a_shock_that_holds_is_refused_again() -> TestResult {
    let mut runner = run(1)?;
    runner.strike(Shock::HarvestFails, Places::A, Lasts::UntilLifted)?;
    let book = runner.shocks().clone();
    let refusal = ShockError::AlreadyHolds {
        shock: Shock::HarvestFails,
        place: Place::A,
    };
    assert_eq!(
        runner.strike(Shock::HarvestFails, Places::Both, Lasts::TenPeriods),
        Err(refusal)
    );
    assert_eq!(runner.shocks(), &book);
    Ok(())
}

#[test]
fn lifting_what_does_not_hold_is_refused() -> TestResult {
    let mut runner = run(1)?;
    let refusal = ShockError::NotHolding {
        shock: Shock::HarvestFails,
        place: Place::B,
    };
    assert_eq!(runner.lift(Shock::HarvestFails, Place::B), Err(refusal));
    assert_eq!(runner.shocks().strikes(), []);
    Ok(())
}

#[test]
fn ten_periods_is_only_for_the_harvest() -> TestResult {
    let mut runner = run(1)?;
    assert_eq!(
        runner.strike(Shock::PowerCut, Places::A, Lasts::TenPeriods),
        Err(ShockError::TenPeriodsOnlyForTheHarvest)
    );
    assert_eq!(runner.shocks().strikes(), []);
    Ok(())
}

#[test]
fn the_power_cut_holds_until_the_run_is_started_over() -> TestResult {
    let mut runner = run(1)?;
    runner.strike(Shock::PowerCut, Places::A, Lasts::UntilLifted)?;
    let book = runner.shocks().clone();
    assert_eq!(
        runner.lift(Shock::PowerCut, Place::A),
        Err(ShockError::HoldsUntilStartOver)
    );
    step(&mut runner, 2)?;
    assert_eq!(
        runner.lift(Shock::PowerCut, Place::A),
        Err(ShockError::HoldsUntilStartOver)
    );
    assert_eq!(runner.shocks().strikes(), book.strikes());
    Ok(())
}

#[test]
fn a_stopped_run_takes_no_shock() -> TestResult {
    let mut runner = run(998)?;
    assert!(runner.step().is_err());
    assert_eq!(
        runner.strike(Shock::HarvestFails, Places::A, Lasts::UntilLifted),
        Err(ShockError::Stopped)
    );
    assert_eq!(
        runner.lift(Shock::HarvestFails, Place::A),
        Err(ShockError::Stopped)
    );
    Ok(())
}

#[test]
fn a_shocked_catalog_differs_only_in_its_figure() -> TestResult {
    let opening = doubled::catalog(&Figures::OPENING)?.into_definition();
    let mut harvest = Figures::OPENING;
    harvest.farm_yield[0] = 9;
    let mut expected = doubled::catalog(&harvest)?.into_definition();
    let farm_a = FARM_A.process_id().ok_or("no process")?;
    for row in &mut expected.process_outputs {
        if row.process_id == farm_a {
            row.quantity_per_batch = 10;
        }
    }
    assert_eq!(expected, opening);

    let mut cut = Figures::OPENING;
    cut.utility_hours_per_batch[1] = 10;
    cut.utility_output_per_batch[1] = 9;
    let mut expected = doubled::catalog(&cut)?.into_definition();
    let utility_b = Workplace {
        place: Place::B,
        kind: Kind::Utility,
    }
    .process_id()
    .ok_or("no process")?;
    for row in &mut expected.process_outputs {
        if row.process_id == utility_b {
            row.quantity_per_batch = 1;
        }
    }
    for row in &mut expected.labor_coefficients {
        if row.process_id == utility_b {
            row.quantity_per_batch = 1;
        }
    }
    assert_eq!(expected, opening);
    Ok(())
}

#[test]
fn the_shocks_have_their_words() {
    assert_eq!(Shock::HarvestFails.name(), "The harvest fails");
    assert_eq!(Shock::PowerCut.name(), "The power is cut");
    assert_eq!(
        Shock::HarvestFails.figure(),
        "a farm makes 9 food a batch, not 10"
    );
    assert_eq!(
        Shock::PowerCut.figure(),
        "a utility makes 9 power for 10 hours, not 10"
    );
    assert_eq!(Places::A.label(), "Place A");
    assert_eq!(Places::B.label(), "Place B");
    assert_eq!(Places::Both.label(), "both places");
    assert_eq!(Places::Both.places(), vec![Place::A, Place::B]);
    assert_eq!(Lasts::TenPeriods.label(), "for ten periods");
    assert_eq!(Lasts::UntilLifted.label(), "until lifted");
}
