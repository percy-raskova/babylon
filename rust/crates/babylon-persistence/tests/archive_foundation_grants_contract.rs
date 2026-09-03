//! Pure contract checks for PER-23 foundation knowledge-grant seeding.

use babylon_persistence::{
    glossary_concepts_v1, seed_foundation_grants_v1, CampaignId, FoundationGrantsErrorV1,
    FOUNDATION_CONCEPT_GRANT_KEYS_V1, FOUNDATION_COUNTY_GRANT_KEYS_V1,
    FOUNDATION_COUNTY_LOCATOR_PREFIX_V1, FOUNDATION_COUNTY_SOURCE_ID_V1, FOUNDATION_GRANT_TICK_V1,
    FOUNDATION_PLACE_CONTAINMENT_LOCATOR_PREFIX_V1, FOUNDATION_PLACE_CONTAINMENT_SOURCE_ID_V1,
    FOUNDATION_PLACE_GRANT_KEYS_V1, FOUNDATION_PLACE_IDENTITY_LOCATOR_PREFIX_V1,
    FOUNDATION_PLACE_IDENTITY_SOURCE_ID_V1, GLOSSARY_CONCEPTS_FIXTURE_PATH_V1,
    PINNED_GLOSSARY_CONCEPTS_SHA256_V1,
};

const EXPECTED_COUNTIES: usize = 83;
const EXPECTED_PLACES: usize = 745;
const EXPECTED_CONCEPTS: usize = 8;

#[test]
fn glossary_concepts_parse_to_the_pinned_corpus() {
    let concepts = glossary_concepts_v1().expect("pinned glossary corpus parses");

    assert_eq!(concepts.concepts().len(), EXPECTED_CONCEPTS);
    let semantic = hex_lower(&concepts.semantic_sha256());
    assert_eq!(
        semantic,
        "d296f02168c66199168f732388abfeaf06d03932f784885884b82382b9454ebe"
    );
    let ids = concepts
        .concepts()
        .iter()
        .map(babylon_persistence::GlossaryConceptV1::concept_id)
        .collect::<Vec<_>>();
    assert_eq!(
        ids,
        [
            "census-identity",
            "class-composition",
            "containment",
            "employment",
            "existence",
            "identity",
            "median-wage",
            "phi-hour",
        ]
    );
    let median_wage = concepts
        .concepts()
        .iter()
        .find(|concept| concept.concept_id() == "median-wage")
        .expect("median-wage concept");
    assert_eq!(median_wage.display_label(), "Median wage");
    let phi_hour = concepts
        .concepts()
        .iter()
        .find(|concept| concept.concept_id() == "phi-hour")
        .expect("phi-hour concept");
    assert_eq!(phi_hour.display_label(), "Imperial rent Φ");
}

#[test]
fn pinned_products_cover_every_public_reference_subject() {
    let cohort =
        babylon_persistence::representative_h3_reference_cohort_v1().expect("pinned cohort");
    let products = babylon_persistence::michigan_spatial_reference_products_v1(cohort)
        .expect("pinned products");

    let michigan_counties = products
        .counties()
        .iter()
        .filter(|county| county.county_geoid().starts_with("26") && county.county_fips() != "999")
        .count();
    assert_eq!(michigan_counties, EXPECTED_COUNTIES);
    assert_eq!(products.counties().len(), 3285);
    assert_eq!(products.places().len(), EXPECTED_PLACES);
    assert!(products
        .counties()
        .iter()
        .filter(|county| {
            county.county_geoid().starts_with("26") && county.county_fips() != "999"
        })
        .all(|county| county.county_geoid().starts_with("26")));
    assert!(products
        .places()
        .iter()
        .all(|place| place.place_geoid().starts_with("26")));
}

#[test]
fn foundation_citation_identities_are_stable() {
    assert_eq!(FOUNDATION_GRANT_TICK_V1, 0);
    assert_eq!(FOUNDATION_COUNTY_SOURCE_ID_V1, "h3-estate-contract-v1");
    assert_eq!(
        FOUNDATION_COUNTY_LOCATOR_PREFIX_V1,
        "dim_county.parquet#fips="
    );
    assert_eq!(
        FOUNDATION_PLACE_IDENTITY_SOURCE_ID_V1,
        "census-place-authority-v1"
    );
    assert_eq!(
        FOUNDATION_PLACE_IDENTITY_LOCATOR_PREFIX_V1,
        "census_place_identity_mi_2023.csv.gz#place_geoid="
    );
    assert_eq!(
        FOUNDATION_PLACE_CONTAINMENT_SOURCE_ID_V1,
        "county-place-h3-overlap-v1"
    );
    assert_eq!(
        FOUNDATION_PLACE_CONTAINMENT_LOCATOR_PREFIX_V1,
        "census_county_place_h3_land_overlap_mi_2023.parquet#place_geoid="
    );
    assert_eq!(
        FOUNDATION_COUNTY_GRANT_KEYS_V1,
        ["subject", "identity", "containment"]
    );
    assert_eq!(
        FOUNDATION_PLACE_GRANT_KEYS_V1,
        ["subject", "identity", "containment"]
    );
    assert_eq!(FOUNDATION_CONCEPT_GRANT_KEYS_V1, ["subject", "identity"]);
    assert_eq!(
        GLOSSARY_CONCEPTS_FIXTURE_PATH_V1,
        "contracts/fixtures/glossary_concepts_v1.jsonl"
    );
    let hex = hex_lower(&PINNED_GLOSSARY_CONCEPTS_SHA256_V1);
    assert_eq!(
        hex,
        "f47e289dc4e7a11c595f0e42643e352e255775c77dde3a7ed35a91de8d84d85a"
    );
}

#[test]
fn magnitude_grant_keys_stay_ungranted_at_foundation() {
    for key in ["median-wage", "phi-hour", "class-composition", "employment"] {
        assert!(!FOUNDATION_COUNTY_GRANT_KEYS_V1.contains(&key));
        assert!(!FOUNDATION_PLACE_GRANT_KEYS_V1.contains(&key));
        assert!(!FOUNDATION_CONCEPT_GRANT_KEYS_V1.contains(&key));
    }
}

#[test]
fn seeding_needs_no_foundation_argument() {
    // The grant census derives entirely from pinned global artifacts, never
    // from scenario-authored grant lists (ADR249 R3), so the seeder takes no
    // foundation input: the signature binds one client and one campaign.
    let bound: fn(
        &mut postgres::Client,
        CampaignId,
    )
        -> Result<babylon_persistence::FoundationGrantReportV1, FoundationGrantsErrorV1> =
        seed_foundation_grants_v1;
    let _ = bound;
}

fn hex_lower(bytes: &[u8]) -> String {
    use std::fmt::Write as _;
    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(&mut output, "{byte:02x}").expect("writing to String cannot fail");
    }
    output
}
