//! The runner: the quiet doubled world stays still, byte for byte, and stops where it must.

use babylon_circuit_worlds::{
    PeriodResult, RuleError, Runner, RunnerError, Stage, Switch, Workplace, WorldError,
};
use babylon_material_circuit::AdjustmentRule::{
    GoodsStepDown, HiringWithinMeans, OwnerRestart, RestingPrice, SeekingInPlace, StopWithoutPay,
};
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
    assert_eq!(first.members.len(), 32);
    let opening: Vec<u64> = Workplace::ALL
        .iter()
        .map(|w| {
            first
                .members
                .iter()
                .find(|m| m.member.member_id() == w.member_id())
                .map(|m| m.opening_employed)
                .ok_or("a workplace without a member receipt")
        })
        .collect::<Result<_, _>>()?;
    assert_eq!(opening, [12, 4, 4, 4, 12, 4, 4, 4]);
    let rows = &first.receipts.member_labor_use;
    assert_eq!(rows.len(), 32);
    for workplace in Workplace::ALL {
        let row = rows
            .iter()
            .find(|row| row.member_id == workplace.member_id())
            .ok_or("a workplace without a member labor row")?;
        assert_eq!(row.payee, workplace.workers().principal());
        assert_eq!(row.site_id, workplace.site_id());
    }
    for (home, host) in Workplace::pairs() {
        let row = rows
            .iter()
            .find(|row| row.member_id == host.pair_member_id(home))
            .ok_or("a pair without a member labor row")?;
        assert_eq!(row.payee, home.workers().principal());
        assert_eq!(row.attended_hours, 0);
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
    assert_eq!(runner.turn_on(HiringWithinMeans), Err(RuleError::Stopped));
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

#[test]
fn a_rule_not_yet_built_is_refused_by_turn_on() -> TestResult {
    let mut asked = Runner::open()?;
    let mut twin = Runner::open()?;
    for runner in [&mut asked, &mut twin] {
        runner.step()?;
        runner.step()?;
    }
    let refusal = asked.turn_on(GoodsStepDown);
    assert!(
        matches!(
            refusal,
            Err(RuleError::Refused {
                rule: GoodsStepDown,
                error: WorldError::Engine(MaterialCircuitError::MarketClearingInvariant)
            })
        ),
        "{refusal:?}"
    );
    assert_eq!(asked.rules(), []);
    assert_eq!(asked.switch(GoodsStepDown), Switch::Ready);
    for _ in 0..5 {
        asked.step()?;
        twin.step()?;
    }
    assert_eq!(asked.history(), twin.history());
    Ok(())
}

#[test]
fn a_switch_says_what_it_waits_for() -> TestResult {
    let mut runner = Runner::open()?;
    assert_eq!(
        runner.switch(StopWithoutPay),
        Switch::Waits {
            needs: vec![SeekingInPlace]
        }
    );
    assert_eq!(
        runner.turn_on(StopWithoutPay),
        Err(RuleError::Waits {
            rule: StopWithoutPay,
            needs: vec![SeekingInPlace]
        })
    );
    assert_eq!(
        runner.switch(OwnerRestart { outlay_periods: 1 }),
        Switch::Waits {
            needs: vec![HiringWithinMeans, StopWithoutPay, RestingPrice]
        }
    );
    assert_eq!(runner.switch(HiringWithinMeans), Switch::Ready);
    Ok(())
}

#[test]
fn each_period_says_its_rules() -> TestResult {
    let runner = run(3)?;
    assert_eq!(runner.history().len(), 3);
    for result in runner.history() {
        assert!(result.rules.is_empty(), "period {}", result.period);
    }
    Ok(())
}

#[test]
fn a_refusal_of_a_rule_is_worded_for_the_scene() {
    assert_eq!(RuleError::Stopped.to_string(), "the run is stopped");
    assert_eq!(
        RuleError::AlreadyOn {
            rule: RestingPrice,
            from: 4
        }
        .to_string(),
        "A resting price is on from period 4 and holds until you start over"
    );
    assert_eq!(
        RuleError::Waits {
            rule: OwnerRestart { outlay_periods: 1 },
            needs: vec![HiringWithinMeans, StopWithoutPay]
        }
        .to_string(),
        "The owner restarts a stopped workplace waits for a bound on hiring and no money, no work"
    );
    assert_eq!(
        RuleError::Refused {
            rule: GoodsStepDown,
            error: WorldError::Engine(MaterialCircuitError::MarketClearingInvariant)
        }
        .to_string(),
        "the engine refused a goods price steps down: MarketClearingInvariant"
    );
    assert_eq!(
        RunnerError::Rule(RuleError::Stopped).to_string(),
        "the world's rules: the run is stopped"
    );
}
