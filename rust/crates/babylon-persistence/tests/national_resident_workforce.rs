use babylon_kernel::geography::CountyGeoid;
use babylon_persistence::{
    national_counties::{national_county_reference, ObservationStatus},
    national_resident_workforce::{
        national_resident_workforce_reference, NationalResidentWorkforceReference,
        ResidentWorkforceReferenceError, SourceSex, WorkerClass,
    },
};

#[test]
fn resident_classes_partition_existing_county_people_without_adding_source_subtotals() {
    let reference = national_resident_workforce_reference().unwrap();
    let counties = national_county_reference().unwrap();
    assert_eq!(reference.counties().len(), 3144);
    let mut total = 0_u64;
    for row in reference.counties() {
        let employed = counties
            .county(row.geoid())
            .unwrap()
            .residents()
            .civilian_employed_persons
            .estimate
            .value()
            .unwrap();
        assert_eq!(row.total().estimate.value(), Some(employed));
        assert_eq!(
            WorkerClass::ALL
                .into_iter()
                .map(|class| row.persons(class).unwrap())
                .sum::<u64>(),
            employed
        );
        total += employed;
    }
    assert_eq!(total, 161_297_155);
}

#[test]
fn self_employment_and_unpaid_family_are_distinct_residents_not_suppressed_jobs() {
    let reference = national_resident_workforce_reference().unwrap();
    for (class, expected) in [
        (WorkerClass::IncorporatedSelfEmployed, 6_410_561),
        (WorkerClass::UnincorporatedSelfEmployed, 9_642_196),
        (WorkerClass::UnpaidFamilyWorker, 301_690),
    ] {
        assert_eq!(
            reference
                .counties()
                .iter()
                .map(|row| row.persons(class).unwrap())
                .sum::<u64>(),
            expected
        );
    }
    let kalawao = reference
        .county(CountyGeoid::try_from("15005").unwrap())
        .unwrap();
    assert_eq!(kalawao.total().estimate.value(), Some(49));
    assert_eq!(
        kalawao.persons(WorkerClass::UnincorporatedSelfEmployed),
        Some(3)
    );
    let observation = kalawao.observation(WorkerClass::UnincorporatedSelfEmployed, SourceSex::Male);
    assert_eq!(observation.estimate.raw(), "3");
    assert_eq!(observation.margin_of_error.value(), Some(3));
    assert_eq!(observation.estimate.status(), ObservationStatus::Published);
}

#[test]
fn changed_source_bytes_and_foreign_counties_refuse_without_partial_capture() {
    let mut bytes = include_bytes!(
        "../../../../src/babylon/data/reference/economy/national_resident_workforce_2024.csv.gz"
    )
    .to_vec();
    bytes[20] ^= 1;
    assert_eq!(
        NationalResidentWorkforceReference::decode_pinned(&bytes),
        Err(ResidentWorkforceReferenceError::ArtifactDigest)
    );
    assert!(national_resident_workforce_reference()
        .unwrap()
        .county(CountyGeoid::try_from("72001").unwrap())
        .is_err());
}
