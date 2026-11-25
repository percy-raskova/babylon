//! Native capture preserves sparse workplace evidence without allocating persons.
use babylon_kernel::economic_identity::{EconomicFunction, QcewOwnership, TradeSet};
use babylon_kernel::geography::CountyGeoid;
use babylon_persistence::national_cohorts;
use babylon_persistence::national_cohorts::{
    CohortKey, NationalCohortReference, NationalCohortReferenceError,
};
use babylon_persistence::national_counties;

#[test]
fn every_source_member_is_preserved_with_explicit_admission() {
    let reference =
        national_cohorts::national_cohort_reference().expect("the cohort reference fixture loads");
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
    let kalawao = CountyGeoid::try_from("15005").expect("the fixture value fits the target range");
    assert_eq!(
        reference
            .groups_in_county(kalawao)
            .expect("the fixture call `groups_in_county` succeeds for the authored inputs")
            .len(),
        0
    );
    assert!(reference
        .groups_in_county(
            CountyGeoid::try_from("26999").expect("the fixture value fits the target range")
        )
        .is_err());
}

#[test]
fn suppression_and_rounded_zero_remain_distinct() {
    let reference =
        national_cohorts::national_cohort_reference().expect("the cohort reference fixture loads");
    assert!(reference.admitted_cohorts().any(|row| {
        row.establishments().known_subtotal() == 0
            && (row.jobs().known_subtotal() > 0 || row.annual_payroll_usd().known_subtotal() > 0)
    }));
    let partial = reference
        .groups()
        .iter()
        .find(|row| row.jobs().complete_total().is_none())
        .expect("the fixture holds the searched element");
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

const V2_TABLE: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../src/babylon/data/reference/economy/national_cohort_reference_v2_2024.csv.gz"
));
const V1_TABLE: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../src/babylon/data/reference/economy/national_cohort_reference_2024.csv.gz"
));
const V1_MAPPING: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../contracts/national_qcew_function_mapping_v1.json"
));
const V2_MAPPING: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../contracts/national_qcew_function_mapping_v2.json"
));

#[test]
fn the_v2_table_decodes_with_its_own_pins() {
    let reference = national_cohorts::national_cohort_reference_v2()
        .expect("the twelve-trade cohort table decodes");
    assert_eq!(reference.trades(), TradeSet::Twelve);
    assert_eq!(reference.groups().len(), 66_920);
    assert_eq!(reference.admitted_cohorts().count(), 65_065);
    assert_eq!(
        reference
            .groups()
            .iter()
            .map(|row| row.members().len())
            .sum::<usize>(),
        151_199
    );
    assert!(reference
        .admitted_cohorts()
        .all(|row| row.key().function.is_some()));
    let wayne = reference
        .group(CohortKey {
            county: CountyGeoid::try_from("26163").expect("Wayne is a county"),
            function: Some(EconomicFunction::ConsumerGoods),
            ownership: QcewOwnership::Private,
        })
        .expect("Wayne has a private consumer goods group");
    let jobs = wayne.jobs().known_subtotal();
    assert!((53_000..54_000).contains(&jobs), "jobs {jobs}");
    // The decoded table's pin is stage 1's metadata digest, hex 09ff8909...4d12.
    assert_eq!(&reference.artifact_sha256()[..4], &[0x09, 0xff, 0x89, 0x09]);
    assert_eq!(
        &reference.function_mapping_sha256()[..4],
        &[0x8b, 0x5f, 0x22, 0xd9]
    );
    // Version 1 keeps its meaning.
    let ten = national_cohorts::national_cohort_reference().expect("the ten-trade table decodes");
    assert_eq!(ten.trades(), TradeSet::Ten);
}

#[test]
fn each_table_needs_its_own_mapping() {
    let counties = national_counties::national_county_reference().expect("the counties decode");
    let refusals = [
        NationalCohortReference::decode_captured_for(
            V2_TABLE,
            V1_MAPPING,
            counties,
            TradeSet::Twelve,
        ),
        NationalCohortReference::decode_captured_for(V1_TABLE, V2_MAPPING, counties, TradeSet::Ten),
        NationalCohortReference::decode_captured_for(V2_TABLE, V2_MAPPING, counties, TradeSet::Ten),
        NationalCohortReference::decode_captured_for(
            V1_TABLE,
            V1_MAPPING,
            counties,
            TradeSet::Twelve,
        ),
        NationalCohortReference::decode_captured_for(
            V1_TABLE,
            V2_MAPPING,
            counties,
            TradeSet::Twelve,
        ),
    ];
    for refusal in refusals {
        assert!(
            matches!(
                refusal,
                Err(NationalCohortReferenceError::FunctionMapping
                    | NationalCohortReferenceError::ArtifactDigest)
            ),
            "{refusal:?}"
        );
    }
}
