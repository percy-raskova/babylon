use super::*;
use crate::national_counties::{national_county_reference, ObservationStatus};
use babylon_kernel::geography::CountyGeoid;

type Error = HouseholdReferenceError;

fn source() -> String {
    decode(ARTIFACT).unwrap()
}
fn parse(text: &str) -> Result<NationalHouseholdReference, Error> {
    parse::capture(text, national_county_reference().unwrap())
}
fn edit_first(text: &str, edit: impl FnOnce(&mut Vec<String>)) -> String {
    let mut lines: Vec<_> = text.lines().map(str::to_owned).collect();
    let mut fields = lines[1].split(',').map(str::to_owned).collect();
    edit(&mut fields);
    lines[1] = fields.join(",");
    lines.join("\n") + "\n"
}
fn cell(fields: &mut [String], offset: usize, margin: bool, parts: [&str; 3]) {
    let start = 1 + offset * 6 + usize::from(margin) * 3;
    for (field, token) in fields[start..start + 3].iter_mut().zip(parts) {
        *field = token.to_owned();
    }
}
fn increment(fields: &mut [String], offset: usize, extra: u64) {
    let value = (fields[1 + offset * 6].parse::<u64>().unwrap() + extra).to_string();
    cell(fields, offset, false, [&value, &value, "published"]);
}

#[test]
fn national_households_preserve_four_separate_margins_and_population_residual() {
    let reference = national_household_reference().unwrap();
    assert_eq!(reference.counties().len(), 3144);
    let mut totals = [0; 4];
    for row in reference.counties() {
        let households = row.total_households().estimate.value().unwrap();
        assert_eq!(
            HouseholdType::ALL
                .into_iter()
                .map(|kind| row.households(kind).estimate.value().unwrap())
                .sum::<u64>(),
            households
        );
        assert_eq!(
            IncomeBand::ALL
                .into_iter()
                .map(|band| row.income_households(band).estimate.value().unwrap())
                .sum::<u64>(),
            households
        );
        let people = row.persons_in_households().estimate.value().unwrap();
        let residual = row.derived_group_quarters_persons().unwrap();
        assert_eq!(
            people + residual,
            row.population_persons().estimate.value().unwrap()
        );
        totals[0] += households;
        totals[1] += people;
        totals[2] += residual;
        totals[3] += row.population_persons().estimate.value().unwrap();
    }
    assert_eq!(totals, [129_227_496, 326_722_431, 8_200_068, 334_922_499]);
    let reopened =
        NationalHouseholdReference::decode_captured(ARTIFACT, national_county_reference().unwrap())
            .unwrap();
    assert_eq!(&reopened, reference);
}

#[test]
fn separate_margins_do_not_impose_a_fabricated_integer_family_joint() {
    let row = national_household_reference()
        .unwrap()
        .county(CountyGeoid::try_from("15005").unwrap())
        .unwrap();
    // Published independent margins: five married households, nine persons.
    // Admission must not invent a tenth person or remove a household.
    assert_eq!(
        row.households(HouseholdType::MarriedCoupleFamily)
            .estimate
            .value(),
        Some(5)
    );
    assert_eq!(
        row.person_source_observations()[2].estimate.value(),
        Some(9)
    );
    let published_zero = &row
        .households(HouseholdType::MaleHouseholderFamily)
        .estimate;
    assert_eq!(published_zero.value(), Some(0));
    assert_eq!(published_zero.raw(), "0");
    assert_eq!(published_zero.status(), ObservationStatus::Published);
    assert_eq!(
        row.households(HouseholdType::LivingAlone).estimate.value(),
        Some(32)
    );
    assert_eq!(
        row.households(HouseholdType::NonfamilyNotAlone)
            .estimate
            .value(),
        Some(3)
    );
    assert_eq!(
        row.person_source_observations()[11].estimate.value(),
        Some(37)
    );
    assert_eq!(
        IncomeBand::Under10000.annual_usd_bounds(),
        (None, Some(10_000))
    );
    assert_eq!(
        IncomeBand::AtLeast200000.annual_usd_bounds(),
        (Some(200_000), None)
    );
}

#[test]
fn controlled_margin_retains_literal_without_claiming_zero_uncertainty() {
    let reference = national_household_reference().unwrap();
    let controlled: Vec<_> = reference
        .counties()
        .iter()
        .flat_map(CountyHouseholdMargins::person_source_observations)
        .filter(|cell| cell.margin_of_error.status() == ObservationStatus::ControlledEstimate)
        .collect();
    assert_eq!(controlled.len(), 1);
    assert_eq!(controlled[0].margin_of_error.raw(), "-555555555");
    assert_eq!(controlled[0].margin_of_error.value(), None);
    assert!(controlled[0].estimate.value().is_some());
}

#[test]
fn source_digest_and_compression_are_exact_and_bounded() {
    let mut changed = ARTIFACT.to_vec();
    changed[20] ^= 1;
    assert_eq!(
        NationalHouseholdReference::decode_pinned(&changed),
        Err(Error::ArtifactDigest)
    );
    assert_eq!(
        NationalHouseholdReference::decode_pinned(&vec![0; MAX_COMPRESSED_BYTES + 1]),
        Err(Error::Bound)
    );
    assert_eq!(
        decode(&ARTIFACT[..ARTIFACT.len() - 8]),
        Err(Error::Compression)
    );
    let mut trailing = ARTIFACT.to_vec();
    trailing.push(0);
    assert_eq!(decode(&trailing), Err(Error::Compression));
    assert_eq!(parse(&"x".repeat(MAX_DECODED_BYTES + 1)), Err(Error::Bound));
}

#[test]
fn missing_duplicate_reordered_and_foreign_counties_are_refused() {
    let text = source();
    let mut lines: Vec<_> = text.lines().map(str::to_owned).collect();
    lines[2] = lines[1].clone();
    assert_eq!(parse(&(lines.join("\n") + "\n")), Err(Error::CountyOrder));
    let mut lines: Vec<_> = text.lines().map(str::to_owned).collect();
    lines.swap(1, 2);
    assert_eq!(parse(&(lines.join("\n") + "\n")), Err(Error::CountyOrder));
    lines.remove(1);
    assert_eq!(parse(&(lines.join("\n") + "\n")), Err(Error::Coverage));
    let foreign = edit_first(&text, |fields| fields[0] = "72001".into());
    assert_eq!(
        parse(&foreign),
        Err(Error::UnknownCounty(
            CountyGeoid::try_from("72001").unwrap()
        ))
    );
}

#[test]
fn headers_shapes_and_status_value_forgery_are_refused() {
    let text = source();
    assert_eq!(
        parse(&text.replacen("B11001_E001_value", "B11002_E001_value", 1)),
        Err(Error::Header)
    );
    assert_eq!(parse(text.trim_end()), Err(Error::CsvShape));
    assert_eq!(
        parse(&edit_first(&text, |fields| {
            fields.pop();
        })),
        Err(Error::CsvShape)
    );
    let forged = edit_first(&text, |fields| {
        cell(
            fields,
            25,
            false,
            ["0", "-999999999", "insufficient_sample_cases"],
        );
    });
    assert!(matches!(parse(&forged), Err(Error::CountySource(_))));
    let overflow = edit_first(&text, |fields| {
        cell(
            fields,
            25,
            false,
            ["9223372036854775808", "9223372036854775808", "published"],
        );
    });
    assert!(matches!(parse(&overflow), Err(Error::CountySource(_))));
}

#[test]
fn each_table_partition_is_checked_without_summing_margins() {
    for offset in [2, 12, 22, 39] {
        let changed = edit_first(&source(), |fields| increment(fields, offset, 1));
        assert_eq!(parse(&changed), Err(Error::Partition));
    }
}

#[test]
fn controls_reject_consistent_but_wrong_household_and_income_totals() {
    let households = edit_first(&source(), |fields| {
        for offset in [0, 1, 2] {
            increment(fields, offset, 1);
        }
    });
    assert_eq!(parse(&households), Err(Error::HouseholdControl));
    let income = edit_first(&source(), |fields| {
        for offset in [21, 22] {
            increment(fields, offset, 1);
        }
    });
    assert_eq!(parse(&income), Err(Error::IncomeControl));
    let people = edit_first(&source(), |fields| {
        for offset in [9, 20] {
            increment(fields, offset, 1_000_000);
        }
    });
    assert_eq!(parse(&people), Err(Error::PopulationControl));
}

#[test]
fn missing_cells_preserve_both_literals_and_propagate_to_derived_residual() {
    for raw in ["", "null"] {
        let changed = edit_first(&source(), |fields| {
            cell(fields, 9, false, ["", raw, "missing"]);
        });
        let reference = parse(&changed).unwrap();
        let row = &reference.counties()[0];
        assert_eq!(row.persons_in_households().estimate.raw(), raw);
        assert_eq!(
            row.persons_in_households().estimate.status(),
            ObservationStatus::Missing
        );
        assert_eq!(row.derived_group_quarters_persons(), None);
    }
}

#[test]
fn missing_estimates_and_margin_only_sentinels_are_not_interchangeable() {
    let changed = edit_first(&source(), |fields| {
        cell(
            fields,
            25,
            false,
            ["", "-999999999", "insufficient_sample_cases"],
        );
    });
    let reference = parse(&changed).unwrap();
    assert_eq!(
        reference.counties()[0].income_source_observations()[4]
            .estimate
            .value(),
        None
    );
    let wrong = edit_first(&source(), |fields| {
        cell(fields, 25, false, ["", "-555555555", "controlled_estimate"]);
    });
    assert_eq!(parse(&wrong), Err(Error::SentinelRole));
    let wrong = edit_first(&source(), |fields| {
        cell(
            fields,
            25,
            true,
            ["", "-666666666", "estimate_not_computable"],
        );
    });
    assert_eq!(parse(&wrong), Err(Error::SentinelRole));
}

#[test]
fn an_unavailable_parent_cannot_hide_overflowing_available_children() {
    let changed = edit_first(&source(), |fields| {
        cell(fields, 21, false, ["", "null", "missing"]);
        for offset in [22, 23] {
            cell(
                fields,
                offset,
                false,
                ["9223372036854775807", "9223372036854775807", "published"],
            );
        }
    });
    assert_eq!(parse(&changed), Err(Error::Arithmetic));
}

#[test]
fn historical_earnings_are_a_separate_household_margin_not_current_workers() {
    let reference = national_household_reference().unwrap();
    let mut with_earnings = 0;
    let mut no_earnings = 0;
    for row in reference.counties() {
        let with = row
            .historical_earnings_households(HistoricalEarnings::WithEarnings)
            .estimate
            .value()
            .unwrap();
        let without = row
            .historical_earnings_households(HistoricalEarnings::NoEarnings)
            .estimate
            .value()
            .unwrap();
        assert_eq!(
            with + without,
            row.total_households().estimate.value().unwrap()
        );
        assert_eq!(
            row.earnings_source_observations()[0].estimate.value(),
            Some(with + without)
        );
        with_earnings += with;
        no_earnings += without;
    }
    assert_eq!((with_earnings, no_earnings), (100_097_816, 29_129_680));
    let changed = edit_first(&source(), |fields| {
        for offset in [38, 39] {
            increment(fields, offset, 1);
        }
    });
    assert_eq!(parse(&changed), Err(Error::EarningsControl));
}
