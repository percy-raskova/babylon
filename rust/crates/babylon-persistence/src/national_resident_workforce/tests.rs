use super::*;
use crate::national_counties::ObservationStatus;

type Error = ResidentWorkforceReferenceError;
fn source() -> String {
    decode(ARTIFACT).unwrap()
}
fn parse(text: &str) -> Result<NationalResidentWorkforceReference, Error> {
    parse::capture(text, national_county_reference().unwrap())
}
fn edit_first(text: &str, edit: impl FnOnce(&mut Vec<String>)) -> String {
    let mut lines: Vec<_> = text.lines().map(str::to_owned).collect();
    let mut fields = lines[1].split(',').map(str::to_owned).collect();
    edit(&mut fields);
    lines[1] = fields.join(",");
    lines.join("\n") + "\n"
}
fn replace_cell(fields: &mut [String], line: usize, margin: bool, cell: [&str; 3]) {
    let start = 1 + (line - 1) * 6 + usize::from(margin) * 3;
    for (field, token) in fields[start..start + 3].iter_mut().zip(cell) {
        *field = token.to_owned();
    }
}

#[test]
fn nested_controls_and_existing_resident_control_are_independent_checks() {
    let original = source();
    let wrong_leaf = edit_first(&original, |fields| {
        replace_cell(fields, 4, false, ["0", "0", "published"]);
    });
    assert_eq!(parse(&wrong_leaf), Err(Error::Partition));
    let wrong_total = edit_first(&original, |fields| {
        for line in [1, 2, 3, 4] {
            let index = 1 + (line - 1) * 6;
            let increment = (fields[index].parse::<u64>().unwrap() + 1).to_string();
            replace_cell(fields, line, false, [&increment, &increment, "published"]);
        }
    });
    assert_eq!(parse(&wrong_total), Err(Error::ResidentControl));
}

#[test]
fn unavailable_leaf_keeps_raw_status_and_cannot_be_replaced_with_zero() {
    let changed = edit_first(&source(), |fields| {
        replace_cell(
            fields,
            10,
            false,
            ["", "-999999999", "insufficient_sample_cases"],
        );
        replace_cell(fields, 10, true, ["", "-555555555", "controlled_estimate"]);
    });
    let reference = parse(&changed).unwrap();
    let row = &reference.counties()[0];
    assert_eq!(row.persons(WorkerClass::UnincorporatedSelfEmployed), None);
    let observation = row.observation(WorkerClass::UnincorporatedSelfEmployed, SourceSex::Male);
    assert_eq!(observation.estimate.raw(), "-999999999");
    assert_eq!(
        observation.margin_of_error.status(),
        ObservationStatus::ControlledEstimate
    );
    let forged = edit_first(&changed, |fields| {
        replace_cell(
            fields,
            10,
            false,
            ["0", "-999999999", "insufficient_sample_cases"],
        );
    });
    assert!(matches!(parse(&forged), Err(Error::CountySource(_))));
}

#[test]
fn margin_sentinels_cannot_be_used_as_estimates() {
    let wrong = edit_first(&source(), |fields| {
        replace_cell(fields, 10, false, ["", "-555555555", "controlled_estimate"]);
    });
    assert_eq!(parse(&wrong), Err(Error::SentinelRole));
    let wrong = edit_first(&source(), |fields| {
        replace_cell(
            fields,
            10,
            true,
            ["", "-666666666", "estimate_not_computable"],
        );
    });
    assert_eq!(parse(&wrong), Err(Error::SentinelRole));
}

#[test]
fn missing_duplicate_and_reordered_counties_refuse_capture() {
    let text = source();
    let mut lines: Vec<_> = text.lines().map(str::to_owned).collect();
    lines[2] = lines[1].clone();
    assert_eq!(parse(&(lines.join("\n") + "\n")), Err(Error::CountyOrder));
    let mut lines: Vec<_> = text.lines().map(str::to_owned).collect();
    lines.swap(1, 2);
    assert_eq!(parse(&(lines.join("\n") + "\n")), Err(Error::CountyOrder));
    lines.remove(1);
    assert_eq!(parse(&(lines.join("\n") + "\n")), Err(Error::Coverage));
}
