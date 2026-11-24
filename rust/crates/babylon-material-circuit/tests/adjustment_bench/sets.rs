// The sets of the bench: the quick test, the long tests and the helper that makes the fixtures. Included
// into the root of the test binary, so the tests keep their bare names (`reproduces_*`).

use babylon_circuit_worlds::{doubled, Runner, Scale, World};
use babylon_material_circuit::{self as engine, MaterialCircuitError, PlaceStaffingError};
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
fn reproduces_pc_bound_nat_400() {
    let produced = produce(Form::Bound, Scale::National, PERIODS_LONG);
    compare::assert_set("pc-bound-nat-400", &produced, PC_BOUND_NAT_400);
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
