//! Today's bytes of the shipped national world, pinned before schema 8 is built.
//!
//! Every path of schema 7 and earlier must keep these values: the catalog digest, the foundation digests,
//! the two State-opponent configs of the campaign, the digests of the two earlier compiler paths, and the
//! counts of the opening's parts. A drift in a count names the part that moved.
use babylon_kernel::content_digest;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_persistence::economic_catalog::{
    CapturedEconomicCatalog, EconomicCatalogInput, SourceArtifact, SourceArtifactKind,
};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::qualification_audit::trade;
use uuid::Uuid;

#[path = "fixtures/national_capture.rs"]
mod national_capture;

const CATALOG_DIGEST: &str = "76056c10d5496cbd6f81cd976c55227bc3e8d6acbbc6603cc2b4fb30a87cc6bc";
const FOUNDATION_DIGEST: &str = "e0f19783e01d5b5a5ed897324ecc05d9fab253dff9fd05552abc8522d90b56db";
const CAMPAIGN_CATALOG_DIGEST: &str =
    "f4874970ee1742a0caa8dddfd82a52d5485643856a8d852a8ad35c91f3e2bd2a";
const CAMPAIGN_FOUNDATION_DIGEST: &str =
    "3d6b120871e3243ef9db49859016d4d4da76117c85814ea0f95069a8401423e0";
const COUNTY_REVIEW_CONFIG_DIGEST: &str =
    "a7bdd3748e0d465f9108f49fea7e27c9db6158e44dc8d402a8a1c9707e4304f7";
const CITY_PD_CONFIG_DIGEST: &str =
    "0d7d0028e23d009bacb83c014ae4659067c1b98b4b5dd3389abe8e1ca657cb4d";
const V11_FOUNDATION_DIGEST: &str =
    "4046433a31ba861f5813e993b9a2c1731b11d553b63a7b8407bcfa38ca1b8008";
const COMPANY_SCALE_FOUNDATION_DIGEST: &str =
    "62e8efc50d126d692ea22b1ae3e2e083692e701f9649341f4657814b92225851";

fn foundation_digest(catalog: CapturedEconomicCatalog) -> String {
    let foundation = catalog
        .create_foundation(
            ReplaySessionId::try_from("shipped-world-bytes")
                .expect("the fixture value fits the target range"),
            ReplaySeed::new(319),
        )
        .expect("the authored catalog builds the foundation");
    trade::hex(&foundation.digest())
}

fn campaign() -> CampaignId {
    CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7036))
}

fn with_policy(mut text_change: impl FnMut(&mut String)) -> EconomicCatalogInput {
    let mut input = national_capture::input();
    let policy = input
        .sources
        .iter_mut()
        .find(|s| s.kind() == SourceArtifactKind::NationalGamePolicy)
        .expect("the roster holds the policy");
    let mut text = std::str::from_utf8(policy.bytes())
        .expect("the authored policy is text")
        .to_owned();
    text_change(&mut text);
    *policy = SourceArtifact::capture(SourceArtifactKind::NationalGamePolicy, text.into_bytes());
    input
}

#[test]
fn the_shipped_catalog_keeps_its_digest() {
    let catalog = CapturedEconomicCatalog::capture(national_capture::input(), None)
        .expect("the shipped roster captures");
    assert_eq!(catalog.compiler_version(), "national-world-v12");
    assert_eq!(
        catalog.digest(),
        content_digest::sha256_of(catalog.canonical_bytes())
    );
    assert_eq!(trade::hex(&catalog.digest()), CATALOG_DIGEST);
}

#[test]
fn the_shipped_foundations_keep_their_digests() {
    let catalog = CapturedEconomicCatalog::capture(national_capture::input(), None)
        .expect("the shipped roster captures");
    let foundation = foundation_digest(catalog);
    let campaign_catalog =
        CapturedEconomicCatalog::capture_national_campaign(national_capture::input(), campaign())
            .expect("the shipped campaign captures");
    let county_review = content_digest::sha256_of(
        &babylon_practice_contract::encode_county_review_config(
            campaign_catalog
                .county_review_config()
                .expect("the campaign holds the county review"),
        )
        .expect("the county review config encodes"),
    );
    let city_pd = content_digest::sha256_of(
        &babylon_practice_contract::encode_city_pd_config(
            campaign_catalog
                .city_pd_config()
                .expect("the campaign holds the City PD"),
        )
        .expect("the City PD config encodes"),
    );
    let campaign_catalog_digest = trade::hex(&campaign_catalog.digest());
    let campaign_foundation = foundation_digest(campaign_catalog);
    assert_eq!(foundation, FOUNDATION_DIGEST);
    assert_eq!(campaign_catalog_digest, CAMPAIGN_CATALOG_DIGEST);
    assert_eq!(campaign_foundation, CAMPAIGN_FOUNDATION_DIGEST);
    assert_eq!(trade::hex(&county_review), COUNTY_REVIEW_CONFIG_DIGEST);
    assert_eq!(trade::hex(&city_pd), CITY_PD_CONFIG_DIGEST);
}

#[test]
fn earlier_compilers_keep_their_digests() {
    // Schema 6 without its City PD and County Review sections: compiler `national-world-v11`.
    let v11 = CapturedEconomicCatalog::capture(
        with_policy(|text| {
            *text = text.replacen("schema_version = 7", "schema_version = 6", 1);
            let cut = text
                .find("[city_pd]")
                .expect("the shipped policy holds [city_pd]");
            // What is cut holds exactly the two sections, so that a section added after them
            // is not cut unseen.
            let sections: Vec<&str> = text[cut..]
                .lines()
                .filter(|line| line.starts_with('['))
                .collect();
            assert_eq!(sections, ["[city_pd]", "[county_review]"]);
            text.truncate(cut);
        }),
        None,
    )
    .expect("the schema 6 policy captures");
    assert_eq!(v11.compiler_version(), "national-world-v11");
    let v11_digest = foundation_digest(v11);

    // The experiment input of the company-scale experiment (300 controllers).
    let mut scale = with_policy(|text| {
        *text = text.replacen(
            "[companies]",
            "[companies]\nexperiment_controller_count = 300",
            1,
        );
    });
    "national-company-scale-experiment".clone_into(&mut scale.preset_id);
    let scale =
        CapturedEconomicCatalog::capture(scale, None).expect("the experiment input captures");
    assert_eq!(scale.compiler_version(), "national-company-scale-v4");
    let scale_digest = foundation_digest(scale);
    assert_eq!(v11_digest, V11_FOUNDATION_DIGEST);
    assert_eq!(scale_digest, COMPANY_SCALE_FOUNDATION_DIGEST);
}

#[test]
fn the_shipped_opening_keeps_its_counts() {
    let catalog = CapturedEconomicCatalog::capture(national_capture::input(), None)
        .expect("the shipped roster captures");
    let opening = catalog.opening();
    let members: usize = opening.staffing.iter().map(|p| p.members.len()).sum();
    assert_eq!(opening.sites.len(), 7_463, "sites");
    assert_eq!(opening.households.len(), 1_602, "household rows");
    assert_eq!(members, 21_062, "staffing members");
    assert_eq!(opening.employment.len(), 21_062, "employment terms");
    assert_eq!(
        opening.institutions.ownership.len(),
        7_782,
        "ownership claims"
    );
    assert_eq!(opening.recipes.len(), 9, "recipes");
    assert_eq!(opening.commodities.len(), 10, "commodities");
}
