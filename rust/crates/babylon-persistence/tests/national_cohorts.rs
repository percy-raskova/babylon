//! Native capture preserves sparse workplace evidence without allocating persons.
use babylon_kernel::geography::CountyGeoid;
use babylon_persistence::national_cohorts::{
    national_cohort_reference, NationalCohortReference, NationalCohortReferenceError,
};

#[test]
fn every_source_member_is_preserved_with_explicit_admission() {
    let reference = national_cohort_reference().unwrap();
    assert_eq!(reference.groups().len(), 59_058);
    assert_eq!(reference.admitted_cohorts().count(), 57_238);
    assert_eq!(
        reference
            .groups()
            .iter()
            .map(|row| row.members().len())
            .sum::<usize>(),
        144_881
    );
    assert_eq!(
        reference
            .groups()
            .iter()
            .filter(|row| row.key().function.is_none())
            .count(),
        1_711
    );
    assert!(reference
        .admitted_cohorts()
        .all(|row| row.key().function.is_some()));
    let kalawao = CountyGeoid::try_from("15005").unwrap();
    assert!(reference.groups_in_county(kalawao).unwrap().is_empty());
    assert!(reference
        .groups_in_county(CountyGeoid::try_from("26999").unwrap())
        .is_err());
}

#[test]
fn suppression_and_rounded_zero_remain_distinct() {
    let reference = national_cohort_reference().unwrap();
    assert!(reference.admitted_cohorts().any(|row| {
        row.establishments().known_subtotal() == 0
            && (row.jobs().known_subtotal() > 0 || row.annual_payroll_usd().known_subtotal() > 0)
    }));
    let partial = reference
        .groups()
        .iter()
        .find(|row| row.jobs().complete_total().is_none())
        .unwrap();
    assert!(partial.establishments().complete_total().is_some());
    assert!(partial.jobs().missing_members() > 0);
    assert_eq!(
        reference
            .groups()
            .iter()
            .map(|row| row.jobs().known_subtotal())
            .sum::<u64>(),
        140_452_919
    );
    assert_eq!(
        reference
            .groups()
            .iter()
            .map(|row| row.annual_payroll_usd().known_subtotal())
            .sum::<u64>(),
        10_475_977_086_096
    );
}

#[test]
fn source_bytes_cannot_be_replaced_or_extended() {
    let bytes = include_bytes!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../src/babylon/data/reference/economy/national_cohort_reference_2024.csv.gz"
    ));
    assert!(NationalCohortReference::decode_pinned(bytes).is_ok());
    let mut altered = bytes.to_vec();
    altered[100] ^= 1;
    assert_eq!(
        NationalCohortReference::decode_pinned(&altered),
        Err(NationalCohortReferenceError::ArtifactDigest)
    );
    altered = bytes.to_vec();
    altered.push(0);
    assert_eq!(
        NationalCohortReference::decode_pinned(&altered),
        Err(NationalCohortReferenceError::ArtifactDigest)
    );
}
