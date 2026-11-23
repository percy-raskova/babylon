//! The runner: the quiet doubled world stays still, byte for byte, and stops where it must.

use babylon_circuit_worlds::{PeriodResult, Runner, RunnerError, Stage, Workplace};
use babylon_material_circuit::MaterialCircuitError;
use std::error::Error;
use std::time::Instant;

type TestResult = Result<(), Box<dyn Error>>;

fn run(periods: u64) -> Result<Runner, Box<dyn Error>> {
    let mut runner = Runner::open()?;
    for _ in 0..periods {
        runner.step()?;
    }
    Ok(runner)
}

#[test]
fn the_quiet_world_stays_still_for_34_periods() -> TestResult {
    let runner = run(34)?;
    let history = runner.history();
    assert_eq!(history.len(), 34);
    let first = history.first().ok_or("no first period")?;
    for result in history {
        assert_eq!(result.summary, first.summary, "period {}", result.period);
    }
    let summary = &first.summary;
    assert_eq!(summary.hours_attended, [120, 40, 40, 40, 120, 40, 40, 40]);
    assert_eq!(summary.made, [120, 40, 40, 40, 120, 40, 40, 40]);
    assert_eq!(summary.employed, [12, 4, 4, 4, 12, 4, 4, 4]);
    assert_eq!(summary.total_money, 12_240_000_000);
    assert_eq!(summary.persons, 80);
    Ok(())
}

#[test]
fn the_same_steps_give_the_same_bytes_twice() -> TestResult {
    let one = run(34)?;
    let two = run(34)?;
    for (a, b) in one.history().iter().zip(two.history()) {
        assert_eq!(a.state_digest, b.state_digest, "period {}", a.period);
    }
    assert_eq!(one.history(), two.history());
    Ok(())
}

#[test]
fn the_runner_keeps_the_member_receipts() -> TestResult {
    let runner = run(1)?;
    let first: &PeriodResult = runner.history().first().ok_or("no first period")?;
    assert_eq!(first.members.len(), 8);
    let opening: Vec<u64> = Workplace::ALL
        .iter()
        .map(|w| {
            first
                .members
                .iter()
                .find(|m| Workplace::from_site(m.site_id) == Some(*w))
                .map(|m| m.opening_employed)
                .ok_or("a workplace without a member receipt")
        })
        .collect::<Result<_, _>>()?;
    assert_eq!(opening, [12, 4, 4, 4, 12, 4, 4, 4]);
    let rows = &first.receipts.member_labor_use;
    assert_eq!(rows.len(), 8);
    for workplace in Workplace::ALL {
        let row = rows
            .iter()
            .find(|row| row.site_id == workplace.site_id())
            .ok_or("a workplace without a member labor row")?;
        assert_eq!(row.payee, workplace.workers().principal());
    }
    Ok(())
}

#[test]
fn the_run_stops_at_its_horizon() -> TestResult {
    let started = Instant::now();
    let mut runner = run(998)?;
    eprintln!("998 periods took {:?}", started.elapsed());
    let refusal = RunnerError::PastHorizon { period: 999 };
    assert_eq!(runner.step().err(), Some(refusal.clone()));
    assert_eq!(runner.step().err(), Some(RunnerError::Stopped));
    assert_eq!(runner.history().len(), 998);
    assert_eq!(runner.stopped(), Some(&refusal));
    Ok(())
}

#[test]
fn a_refusal_is_worded_as_the_engine_words_it() {
    let error = RunnerError::Engine {
        period: 7,
        stage: Stage::Close,
        error: MaterialCircuitError::PublicProgramInvariant,
    };
    assert_eq!(
        error.to_string(),
        "Period 7: the engine refused the close: PublicProgramInvariant (code 39)"
    );
}
