// The sets of the bench: the quick test, the long tests and the helper that makes the fixtures. Included
// into the root of the test binary, so the tests keep their bare names (`reproduces_*`).

use babylon_circuit_worlds::{doubled, PeriodHours, Runner, Scale, World};
use babylon_material_circuit::{
    self as engine, MaterialCircuitError, PlaceStaffingError, WorkplaceStanding,
};
use rows::TurnedOn;
use runs::Form;

/// Periods of a long test.
const PERIODS_LONG: u64 = 400;
/// Periods of the quick test.
const PERIODS_QUICK: u64 = 34;

/// The fixtures: 25 lines `<run> <sha256>` of each reference file, projected.
const PC_A6_400: &str = include_str!("digests/pc-a6-400.txt");
const PC_A6_NAT_400: &str = include_str!("digests/pc-a6-nat-400.txt");
const PC_SEEK_400: &str = include_str!("digests/pc-seek-400.txt");
const PC_SEEK_NAT_400: &str = include_str!("digests/pc-seek-nat-400.txt");
const PC_BOUND_400: &str = include_str!("digests/pc-bound-400.txt");
const PC_BOUND_NAT_400: &str = include_str!("digests/pc-bound-nat-400.txt");
const PC_STOP_400: &str = include_str!("digests/pc-stop-400.txt");
const PC_STOP_NAT_400: &str = include_str!("digests/pc-stop-nat-400.txt");
const PC_REST_400: &str = include_str!("digests/pc-rest-400.txt");
const PC_REST_NAT_400: &str = include_str!("digests/pc-rest-nat-400.txt");
const PC_RESTART_400: &str = include_str!("digests/pc-restart-400.txt");
const PC_RESTART_NAT_400: &str = include_str!("digests/pc-restart-nat-400.txt");
const PC_DOWN_400: &str = include_str!("digests/pc-down-400.txt");
const PC_DOWN_NAT_400: &str = include_str!("digests/pc-down-nat-400.txt");

fn produce(form: Form, scale: Scale, periods: u64) -> Vec<(&'static str, String)> {
    runs::runs(form, scale)
        .iter()
        .map(|run| (run.name, rows::rows(run, periods)))
        .collect()
}

fn field(line: &str, index: usize) -> &str {
    line.split('\t').nth(index).unwrap_or("")
}

/// The quiet runs of a form stay still for 34 periods: every column but the period is that of period 1.
fn assert_quiet(form: Form) {
    for scale in [Scale::Small, Scale::National] {
        for run in runs::runs(form, scale)
            .iter()
            .filter(|run| run.name.ends_with("-quiet"))
        {
            let text = rows::rows(run, PERIODS_QUICK);
            let mut lines = text.lines();
            let header = lines.next().unwrap_or("");
            let column = header
                .split('\t')
                .position(|name| name == "hours_attended")
                .unwrap_or_else(|| panic!("the rows have an hours_attended column"));
            let body: Vec<&str> = lines.collect();
            assert_eq!(body.len(), 34, "{} {scale:?}: 34 periods", run.name);
            let first = body[0];
            for (index, line) in body.iter().enumerate() {
                let rest = |s: &str| s.split_once('\t').map(|(_, rest)| rest.to_owned());
                assert_eq!(
                    rest(line),
                    rest(first),
                    "{} {scale:?}: period {} moved",
                    run.name,
                    index + 1
                );
                assert_eq!(field(line, column), "480", "{} {scale:?}: hours", run.name);
            }
        }
    }
}

#[test]
fn the_doubled_quiet_world_is_still_for_34_periods() {
    assert_quiet(Form::A6);
}

#[test]
fn the_quiet_world_with_seekers_is_still_for_34_periods() {
    assert_quiet(Form::Seek);
    let runs = runs::runs(Form::Seek, Scale::Small);
    let run = runs
        .iter()
        .find(|run| run.name == "fund-quiet")
        .expect("the fund world's quiet run");
    let text = rows::rows(run, 2);
    let header = text.lines().next().unwrap_or("");
    for name in ["seekers_a", "people_b", "parked_shop_b", "pair_looking_farm_a_from_clinic_a"] {
        assert!(header.split('\t').any(|column| column == name), "{name}");
    }
}

#[test]
fn the_quiet_world_with_the_bound_is_still_for_34_periods() {
    assert_quiet(Form::Bound);
    let runs = runs::runs(Form::Bound, Scale::Small);
    let run = runs
        .iter()
        .find(|run| run.name == "fund-quiet")
        .expect("the fund world's quiet run");
    let text = rows::rows(run, 2);
    let header = text.lines().next().unwrap_or("");
    for name in ["bound_hours_utility_a", "bound_by_shop_b"] {
        assert!(header.split('\t').any(|column| column == name), "{name}");
    }
    assert_eq!(
        header.split('\t').next_back(),
        Some("bound_by_shop_b"),
        "the bound's columns come last"
    );
}

#[test]
fn the_quiet_world_with_the_stop_rule_is_still_for_34_periods() {
    assert_quiet(Form::Stop);
    let runs = runs::runs(Form::Stop, Scale::Small);
    let run = runs
        .iter()
        .find(|run| run.name == "fund-quiet")
        .expect("the fund world's quiet run");
    let text = rows::rows(run, 2);
    let header: Vec<&str> = text.lines().next().unwrap_or("").split('\t').collect();
    let position = |name: &str| header.iter().position(|column| *column == name);
    let parked = position("parked_shop_b").expect("parked");
    let stopped = position("stopped_utility_a").expect("stopped");
    assert_eq!(stopped, parked + 1, "the stopped columns follow the parked ones");
    for line in text.lines().skip(1) {
        for site in ["utility_a", "shop_b"] {
            let at = position(&format!("stopped_{site}")).expect("stopped");
            assert_eq!(field(line, at), "0", "a quiet workplace is not stopped");
        }
    }
}

#[test]
fn the_quiet_world_with_the_resting_price_is_still_for_34_periods() {
    assert_quiet(Form::Rest);
}

#[test]
fn the_quiet_world_with_the_restart_is_still_for_34_periods() {
    assert_quiet(Form::Restart);
    let runs = runs::runs(Form::Restart, Scale::Small);
    let run = runs
        .iter()
        .find(|run| run.name == "fund-quiet")
        .expect("the fund world's quiet run");
    let text = rows::rows(run, 6);
    let header: Vec<&str> = text.lines().next().unwrap_or("").split('\t').collect();
    let position = |name: &str| header.iter().position(|column| *column == name);
    for name in [
        "restart_test_utility_a",
        "stopped_since_shop_b",
        "restart_inputs_clinic_a",
        "owner_spare_b",
    ] {
        assert!(position(name).is_some(), "{name}");
    }
    for line in text.lines().skip(1) {
        for site in ["utility_a", "shop_b"] {
            let at = position(&format!("restart_test_{site}")).expect("restart test");
            assert_eq!(field(line, at), "0", "a quiet workplace is not tested");
        }
    }
}

#[test]
fn opening_with_a_form_is_turning_its_rules_on_first() {
    for form in Form::ALL {
        for scale in [Scale::Small, Scale::National] {
            for run in runs::runs(form, scale).iter().filter(|run| {
                ["fund-quiet", "fund-P2", "fund-P6", "plain-P2"].contains(&run.name)
            }) {
                let (opened, opened_digests) = rows::rows_and_digests(run, PERIODS_QUICK, TurnedOn::AtOpening);
                let (late, late_digests) = rows::rows_and_digests(run, PERIODS_QUICK, TurnedOn::AfterStrikes);
                assert_eq!(
                    opened_digests, late_digests,
                    "{form:?} {} {scale:?}: state digests",
                    run.name
                );
                assert_eq!(
                    opened, late,
                    "{form:?} {} {scale:?}: projected rows",
                    run.name
                );
            }
        }
    }
}

#[test]
fn a_late_turn_on_keeps_money_and_people() {
    for form in Form::ALL.into_iter().filter(|form| *form != Form::A6) {
        for scale in [Scale::Small, Scale::National] {
            for run in runs::runs(form, scale).iter().filter(|run| {
                ["fund-quiet", "fund-P2", "fund-P6", "plain-P2"].contains(&run.name)
            }) {
                let mut world = run.world.clone();
                let rules = std::mem::take(&mut world.rules);
                let mut runner = Runner::open_world(&world)
                    .unwrap_or_else(|error| panic!("{} opens: {error:?}", run.name));
                for (shock, places, lasts) in &run.strikes {
                    runner
                        .strike(*shock, *places, *lasts)
                        .unwrap_or_else(|error| panic!("{} strikes: {error:?}", run.name));
                }
                for step in 0..60 {
                    if step == 20 {
                        for rule in &rules {
                            runner.turn_on(*rule).unwrap_or_else(|error| {
                                panic!("{} turns on {rule:?}: {error}", run.name)
                            });
                        }
                    }
                    let result = runner.step().unwrap_or_else(|error| {
                        panic!("{form:?} {} {scale:?} step {}: {error:?}", run.name, step + 1)
                    });
                    if result.period <= 20 {
                        assert!(result.rules.is_empty(), "{} period {}", run.name, result.period);
                    }
                }
            }
        }
    }
}

#[test]
fn the_old_finish_refuses_a_catalog_that_asks_for_seekers() {
    let asking = World {
        rules: Form::Seek.rules(Scale::Small),
        ..World::scene()
    };
    let mut seeking = Runner::open_world(&asking).expect("the world opens");
    seeking.step().expect("a period closes");
    let catalog = seeking.catalog().expect("a catalog closed the period");
    let closed = engine::close_material_period(catalog, seeking.state()).expect("a close");
    assert_eq!(
        closed
            .finish_with_staffing(catalog, Vec::new(), Vec::new(), &[])
            .err(),
        Some(MaterialCircuitError::MarketClearingInvariant)
    );
    let mut plain = Runner::open().expect("the scene opens");
    plain.step().expect("a period closes");
    let catalog = plain.catalog().expect("a catalog closed the period");
    let closed = engine::close_material_period(catalog, plain.state()).expect("a close");
    assert_eq!(
        closed
            .staff_in_places(catalog, plain.staffing(), plain.members(), &doubled::places())
            .err(),
        Some(PlaceStaffingError::Circuit(
            MaterialCircuitError::MarketClearingInvariant
        ))
    );
}

#[test]
fn the_old_entry_refuses_the_stop_rule() {
    let asking = World {
        rules: Form::Stop.rules(Scale::Small),
        ..World::scene()
    };
    let mut runner = Runner::open_world(&asking).expect("the world opens");
    runner.step().expect("a period closes");
    let catalog = runner.catalog().expect("a catalog closed the period");
    assert_eq!(
        engine::close_material_period(catalog, runner.state()).err(),
        Some(MaterialCircuitError::MarketClearingInvariant)
    );
    assert!(engine::close_material_period_with_standing(
        catalog,
        runner.state(),
        runner.standing()
    )
    .is_ok());
}

#[test]
fn the_new_entry_with_an_empty_standing_is_the_opening_s() {
    let asking = World {
        rules: Form::Stop.rules(Scale::Small),
        ..World::scene()
    };
    let mut runner = Runner::open_world(&asking).expect("the world opens");
    runner.step().expect("a period closes");
    let kept = runner.standing().clone();
    assert_eq!(kept.rows().len(), 8, "every site has a row after a close");
    assert!(kept
        .rows()
        .iter()
        .all(|row| row.hold == engine::StopHold::Free));
    let catalog = runner.catalog().expect("a catalog closed the period");
    let finish = |standing: &WorkplaceStanding| {
        let closed =
            engine::close_material_period_with_standing(catalog, runner.state(), standing)
                .expect("a close");
        let placed = closed
            .staff_in_places(
                catalog,
                runner.staffing(),
                runner.members(),
                &doubled::places(),
            )
            .expect("places staff");
        let after = placed.standing.clone();
        let transition = closed
            .finish_with_place_staffing(catalog, &placed)
            .expect("a finish");
        (after, transition)
    };
    let (empty_after, empty) = finish(&WorkplaceStanding::opening());
    let (free_after, with_rows) = finish(&kept);
    assert_eq!(empty_after, free_after);
    assert_eq!(empty, with_rows);
}

#[test]
#[ignore = "25 runs of 400 periods; run in the background"]
fn reproduces_pc_a6_400() {
    let produced = produce(Form::A6, Scale::Small, PERIODS_LONG);
    compare::assert_set("pc-a6-400", &produced, PC_A6_400);
}

#[test]
#[ignore = "25 runs of 400 periods; run in the background"]
fn reproduces_pc_a6_nat_400() {
    let produced = produce(Form::A6, Scale::National, PERIODS_LONG);
    compare::assert_set("pc-a6-nat-400", &produced, PC_A6_NAT_400);
}

#[test]
#[ignore = "25 runs of 400 periods; run in the background"]
fn reproduces_pc_seek_400() {
    let produced = produce(Form::Seek, Scale::Small, PERIODS_LONG);
    compare::assert_set("pc-seek-400", &produced, PC_SEEK_400);
}

#[test]
#[ignore = "25 runs of 400 periods; run in the background"]
fn reproduces_pc_seek_nat_400() {
    let produced = produce(Form::Seek, Scale::National, PERIODS_LONG);
    compare::assert_set("pc-seek-nat-400", &produced, PC_SEEK_NAT_400);
}

#[test]
#[ignore = "25 runs of 400 periods; run in the background"]
fn reproduces_pc_bound_400() {
    let produced = produce(Form::Bound, Scale::Small, PERIODS_LONG);
    compare::assert_set("pc-bound-400", &produced, PC_BOUND_400);
}

#[test]
#[ignore = "25 runs of 400 periods; run in the background"]
fn reproduces_pc_stop_400() {
    let produced = produce(Form::Stop, Scale::Small, PERIODS_LONG);
    compare::assert_set("pc-stop-400", &produced, PC_STOP_400);
}

#[test]
#[ignore = "25 runs of 400 periods; run in the background"]
fn reproduces_pc_stop_nat_400() {
    let produced = produce(Form::Stop, Scale::National, PERIODS_LONG);
    compare::assert_set("pc-stop-nat-400", &produced, PC_STOP_NAT_400);
}

#[test]
#[ignore = "25 runs of 400 periods; run in the background"]
fn reproduces_pc_rest_400() {
    let produced = produce(Form::Rest, Scale::Small, PERIODS_LONG);
    compare::assert_set("pc-rest-400", &produced, PC_REST_400);
}

#[test]
#[ignore = "25 runs of 400 periods; run in the background"]
fn reproduces_pc_rest_nat_400() {
    let produced = produce(Form::Rest, Scale::National, PERIODS_LONG);
    compare::assert_set("pc-rest-nat-400", &produced, PC_REST_NAT_400);
}

#[test]
#[ignore = "25 runs of 400 periods; run in the background"]
fn reproduces_pc_restart_400() {
    let produced = produce(Form::Restart, Scale::Small, PERIODS_LONG);
    compare::assert_set("pc-restart-400", &produced, PC_RESTART_400);
}

#[test]
#[ignore = "25 runs of 400 periods; run in the background"]
fn reproduces_pc_restart_nat_400() {
    let produced = produce(Form::Restart, Scale::National, PERIODS_LONG);
    compare::assert_set("pc-restart-nat-400", &produced, PC_RESTART_NAT_400);
}

#[test]
#[ignore = "25 runs of 400 periods; run in the background"]
fn reproduces_pc_down_400() {
    let produced = produce(Form::Down, Scale::Small, PERIODS_LONG);
    compare::assert_set("pc-down-400", &produced, PC_DOWN_400);
}

#[test]
#[ignore = "25 runs of 400 periods; run in the background"]
fn reproduces_pc_down_nat_400() {
    let produced = produce(Form::Down, Scale::National, PERIODS_LONG);
    compare::assert_set("pc-down-nat-400", &produced, PC_DOWN_NAT_400);
}

#[test]
fn the_quiet_world_with_the_step_down_is_still_for_34_periods() {
    assert_quiet(Form::Down);
    let runs = runs::runs(Form::Down, Scale::Small);
    let run = runs
        .iter()
        .find(|run| run.name == "fund-quiet")
        .expect("the fund world's quiet run");
    let text = rows::rows(run, 2);
    let header: Vec<&str> = text.lines().next().unwrap_or("").split('\t').collect();
    let names = [
        "unsold_farm_a",
        "turned_payers_farm_a",
        "unsold_shop_a",
        "turned_payers_shop_a",
        "unsold_farm_b",
        "turned_payers_farm_b",
        "unsold_shop_b",
        "turned_payers_shop_b",
    ];
    assert_eq!(
        &header[header.len() - names.len()..],
        &names,
        "the step down's columns come last, farms and shops by copy"
    );
}

#[test]
fn the_restart_waits_for_its_rules() {
    use engine::AdjustmentRule::{
        HiringWithinMeans, OwnerRestart, RestingPrice, SeekingInPlace, StopWithoutPay,
    };
    use babylon_circuit_worlds::{RuleError, Switch};
    let restart = OwnerRestart { outlay_periods: 1 };
    let mut runner = Runner::open().expect("the scene opens");
    runner.turn_on(SeekingInPlace).expect("the seekers turn on");
    runner.turn_on(StopWithoutPay).expect("the stop rule turns on");
    let needs = vec![HiringWithinMeans, RestingPrice];
    assert_eq!(
        runner.switch(restart),
        Switch::Waits {
            needs: needs.clone()
        }
    );
    assert_eq!(
        runner.turn_on(restart),
        Err(RuleError::Waits {
            rule: restart,
            needs
        })
    );
}

#[test]
#[ignore = "25 runs of 400 periods; run in the background"]
fn reproduces_pc_bound_nat_400() {
    let produced = produce(Form::Bound, Scale::National, PERIODS_LONG);
    compare::assert_set("pc-bound-nat-400", &produced, PC_BOUND_NAT_400);
}

/// The laws of one period's hours, as the hours test of the runner keeps them: both ledgers close,
/// `direct` is a million times what the households gave, and each place's identity holds.
fn assert_hours_laws(hours: &PeriodHours) -> Result<(), String> {
    for (name, totals) in [("hours", &hours.hours), ("opening units", &hours.opening_units)] {
        if totals.opening + totals.direct != totals.closing + totals.released {
            return Err(format!("the {name} ledger does not close: {totals:?}"));
        }
    }
    let given: u128 = hours.households.iter().map(|(_, h)| u128::from(h.given)).sum();
    if hours.hours.direct != 1_000_000 * given {
        return Err(format!("direct {} is not 1,000,000 x given {given}", hours.hours.direct));
    }
    for (place, p) in &hours.places {
        if p.back_micro_hours + p.held_closing + p.left_micro_hours
            != p.given_micro_hours + p.held_opening
        {
            return Err(format!("the identity of place {place:?} fails: {p:?}"));
        }
    }
    Ok(())
}

/// Every reference run of every form and both scales, folded twice a period for 400 periods: every step is
/// `Ok` and every period keeps the laws. Not a `reproduces_` test: the bench's rows never fold.
#[test]
#[ignore = "350 runs of 400 periods, each folded twice; run in the background"]
fn hours_fold_every_reference_run() {
    for form in Form::ALL {
        for scale in [Scale::Small, Scale::National] {
            for run in runs::runs(form, scale) {
                let mut runner = Runner::open_world_with_hours(&run.world)
                    .unwrap_or_else(|error| panic!("{form:?} {scale:?} {} opens: {error}", run.name));
                for (shock, places, lasts) in &run.strikes {
                    runner.strike(*shock, *places, *lasts).unwrap_or_else(|error| {
                        panic!("{form:?} {scale:?} {} strikes: {error}", run.name)
                    });
                }
                // Over the run so far, each household group's hours back for work and its hours on the
                // clock (the bribe, ADR322 H4): the first never passes a million micro-hours per hour of
                // the second.
                let mut back_for_work: Vec<u128> = Vec::new();
                let mut on_the_clock: Vec<u128> = Vec::new();
                for period in 1..=PERIODS_LONG {
                    let result = runner.step().unwrap_or_else(|error| {
                        panic!("{form:?} {scale:?} {} period {period}: {error}", run.name)
                    });
                    let hours = result.hours.as_ref().unwrap_or_else(|| {
                        panic!("{form:?} {scale:?} {} period {period}: no hours", run.name)
                    });
                    if let Err(law) = assert_hours_laws(hours) {
                        panic!("{form:?} {scale:?} {} period {period}: {law}", run.name);
                    }
                    back_for_work.resize(hours.households.len(), 0);
                    on_the_clock.resize(hours.households.len(), 0);
                    for (at, (household, row)) in hours.households.iter().enumerate() {
                        back_for_work[at] += row.claims.work;
                        on_the_clock[at] += u128::from(row.clock);
                        assert!(
                            back_for_work[at] <= on_the_clock[at] * 1_000_000,
                            "{form:?} {scale:?} {} period {period} {household:?}: back for work {} micro-hours, clock {} hours",
                            run.name,
                            back_for_work[at],
                            on_the_clock[at]
                        );
                    }
                }
            }
        }
    }
}

/// Prints the fixture lines of every set from the reference rows on the bench's drive. Run once with
/// `--run-ignored only -E 'test(print_reference_digests)' --no-capture` and commit what it printed.
#[test]
#[ignore = "reads the reference rows from the bench's drive; makes the fixtures"]
fn print_reference_digests() {
    for (set, form, scale) in [
        ("pc-a6-400", Form::A6, Scale::Small),
        ("pc-a6-nat-400", Form::A6, Scale::National),
        ("pc-seek-400", Form::Seek, Scale::Small),
        ("pc-seek-nat-400", Form::Seek, Scale::National),
        ("pc-bound-400", Form::Bound, Scale::Small),
        ("pc-bound-nat-400", Form::Bound, Scale::National),
        ("pc-stop-400", Form::Stop, Scale::Small),
        ("pc-stop-nat-400", Form::Stop, Scale::National),
        ("pc-rest-400", Form::Rest, Scale::Small),
        ("pc-rest-nat-400", Form::Rest, Scale::National),
        ("pc-restart-400", Form::Restart, Scale::Small),
        ("pc-restart-nat-400", Form::Restart, Scale::National),
        ("pc-down-400", Form::Down, Scale::Small),
        ("pc-down-nat-400", Form::Down, Scale::National),
    ] {
        println!("== {set}");
        for run in runs::runs(form, scale) {
            let path = format!("{}/{set}/{}.tsv", compare::REFERENCE_DIR, run.name);
            let text = std::fs::read_to_string(&path)
                .unwrap_or_else(|error| panic!("read {path}: {error}"));
            println!(
                "{} {}",
                run.name,
                compare::digest_hex(&compare::project(&text))
            );
        }
    }
}
