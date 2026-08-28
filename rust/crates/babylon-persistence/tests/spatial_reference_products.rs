//! Pure contracts for the bounded PER-278 reference-product bundle.

use babylon_kernel::tick_content_hash::RefDigestV1;
use babylon_persistence::{
    build_representative_h3_cohort_v1, michigan_spatial_reference_products_v1, CountyH3LandAreaRow,
    CountyPlaceH3LandAreaRow, H3CellId, H3CountRow, ReferenceProduct,
};

const SOURCE_FIXTURE: &[u8] = include_bytes!("fixtures/h3_reference_source_v1.bin");
const SOURCE_DOMAIN: &[u8] = b"babylon.h3.reference-source.v1\0";
const ARTIFACT_DIGEST: [u8; 32] = [
    0xe6, 0x0d, 0x93, 0xa4, 0x3d, 0x6c, 0x66, 0xe8, 0x4f, 0x1e, 0x53, 0xec, 0xaf, 0x63, 0x3a, 0xf5,
    0x91, 0x1b, 0xd5, 0xb4, 0x8b, 0x0e, 0xf0, 0xad, 0x6a, 0x01, 0x2f, 0x6d, 0x9f, 0x5b, 0x13, 0xa9,
];

#[test]
fn checked_bundle_has_exact_governed_products_and_counts() {
    let cohort = cohort();
    let bundle = michigan_spatial_reference_products_v1(&cohort)
        .expect("checked PER-278 fixture must validate");

    assert_eq!(bundle.ref_digest(), cohort.receipt().ref_digest());
    assert_eq!(bundle.products().len(), 7);
    assert_eq!(bundle.counties().len(), 3_285);
    assert_eq!(bundle.places().len(), 745);
    assert_eq!(bundle.land_fractions().len(), 45_572);
    assert_eq!(bundle.population_counts().len(), 22_509);
    assert_eq!(bundle.workplace_counts().len(), 11_833);
    assert_eq!(bundle.county_land_areas().len(), 31_881);
    assert_eq!(bundle.county_place_land_areas().len(), 4_813);

    let codes = bundle
        .products()
        .iter()
        .map(ReferenceProduct::code)
        .collect::<Vec<_>>();
    assert_eq!(
        codes,
        [
            "census_county_h3_land_overlap_mi_2023",
            "census_county_place_h3_land_overlap_mi_2023",
            "census_place_identity_mi_2023",
            "dim_county",
            "h3_res7_land_mask",
            "h3_res7_population",
            "h3_res7_workplace",
        ]
    );
}

#[test]
fn checked_bundle_preserves_measure_and_absence_law() {
    let cohort = cohort();
    let bundle = michigan_spatial_reference_products_v1(&cohort).unwrap();

    assert_eq!(
        bundle
            .county_land_areas()
            .iter()
            .map(CountyH3LandAreaRow::land_area_m2)
            .sum::<u64>(),
        146_426_246_267
    );
    assert_eq!(
        bundle
            .county_place_land_areas()
            .iter()
            .map(CountyPlaceH3LandAreaRow::place_land_area_m2)
            .sum::<u64>(),
        7_689_548_061
    );
    assert_eq!(
        bundle
            .population_counts()
            .iter()
            .map(H3CountRow::count)
            .sum::<u64>(),
        10_066_869
    );
    assert_eq!(
        bundle
            .workplace_counts()
            .iter()
            .map(H3CountRow::count)
            .sum::<u64>(),
        3_931_809
    );
    assert!(bundle
        .land_fractions()
        .iter()
        .any(|row| row.parts_per_million() == 0));
    assert!(bundle.population_counts().iter().all(|row| row.count() > 0));
    assert!(bundle.workplace_counts().iter().all(|row| row.count() > 0));
}

fn cohort() -> babylon_persistence::H3ReferenceCohort {
    build_representative_h3_cohort_v1(RefDigestV1::from_bytes(ARTIFACT_DIGEST), &source_cells())
        .unwrap()
}

fn source_cells() -> Vec<H3CellId> {
    assert!(SOURCE_FIXTURE.starts_with(SOURCE_DOMAIN));
    let count_offset = SOURCE_DOMAIN.len();
    let payload_offset = count_offset + 8;
    let count = usize::try_from(u64::from_be_bytes(
        SOURCE_FIXTURE[count_offset..payload_offset]
            .try_into()
            .expect("fixture count has exactly eight bytes"),
    ))
    .unwrap();
    assert_eq!(SOURCE_FIXTURE.len(), payload_offset + count * 8);
    SOURCE_FIXTURE[payload_offset..]
        .chunks_exact(8)
        .map(|chunk| {
            let raw = u64::from_be_bytes(chunk.try_into().unwrap());
            H3CellId::try_from(raw).expect("fixture identities must validate")
        })
        .collect()
}
