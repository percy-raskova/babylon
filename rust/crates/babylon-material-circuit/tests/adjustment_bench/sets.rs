// The sets of the bench: the quick test, the long tests and the helper that makes the fixtures. Included
// into the root of the test binary, so the tests keep their bare names (`reproduces_*`).

use babylon_circuit_worlds::Scale;
use rows::TurnedOn;
use runs::Form;

/// Periods of a long test.
const PERIODS_LONG: u64 = 400;
/// Periods of the quick test.
const PERIODS_QUICK: u64 = 34;

/// The fixtures: 25 lines `<run> <sha256>` of each reference file, projected.
const PC_A6_400: &str = include_str!("digests/pc-a6-400.txt");
const PC_A6_NAT_400: &str = include_str!("digests/pc-a6-nat-400.txt");

fn produce(form: Form, scale: Scale, periods: u64) -> Vec<(&'static str, String)> {
    runs::runs(form, scale)
        .iter()
        .map(|run| (run.name, rows::rows(run, periods)))
        .collect()
}

fn field(line: &str, index: usize) -> &str {
    line.split('\t').nth(index).unwrap_or("")
}

#[test]
fn the_doubled_quiet_world_is_still_for_34_periods() {
    for scale in [Scale::Small, Scale::National] {
        for run in runs::runs(Form::A6, scale)
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

/// Prints the fixture lines of both sets from the reference rows on the bench's drive. Run once with
/// `--run-ignored only -E 'test(print_reference_digests)' --no-capture` and commit what it printed.
#[test]
#[ignore = "reads the reference rows from the bench's drive; makes the fixtures"]
fn print_reference_digests() {
    for (set, scale) in [
        ("pc-a6-400", Scale::Small),
        ("pc-a6-nat-400", Scale::National),
    ] {
        println!("== {set}");
        for run in runs::runs(Form::A6, scale) {
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
