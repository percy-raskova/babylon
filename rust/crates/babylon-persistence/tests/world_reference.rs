//! World source admission cannot double-count reporting areas or invent missing people.

use babylon_kernel::economic_location::{ForeignCounterpart, UsDependency};
use babylon_persistence::world_reference::{
    world_reference, PopulationStatus, UsRelationship, WorldReference, WorldReferenceError,
    WorldScope,
};

#[test]
fn pinned_world_members_have_one_scope_and_nonduplicated_population() {
    let reference = world_reference().unwrap();
    assert_eq!(reference.members().len(), 252);
    assert_eq!(reference.counterparts().len(), 12);
    assert_eq!(reference.known_population_persons(), 8_161_972_576);
    assert_eq!(
        reference
            .counterpart(ForeignCounterpart::Canada)
            .population()
            .known_persons(),
        39_742_430
    );
    assert_eq!(
        reference
            .counterpart(ForeignCounterpart::EuropeanUnion)
            .population()
            .known_persons(),
        450_228_882
    );
    assert_eq!(
        reference
            .counterpart(ForeignCounterpart::RemainingEurope)
            .population()
            .known_persons(),
        151_518_908
    );
    assert_eq!(
        reference.member("m49:840").unwrap().scope(),
        WorldScope::DomesticContext
    );
    assert_eq!(
        reference.member("m49:010").unwrap().scope(),
        WorldScope::Nonmarket
    );
    assert_eq!(
        reference.member("m49:583").unwrap().scope(),
        WorldScope::Foreign(ForeignCounterpart::RemainingAsiaPacific)
    );
    assert_eq!(
        reference.member("m49:583").unwrap().us_relationship(),
        UsRelationship::FreelyAssociatedState
    );
}

#[test]
fn dependency_missingness_and_designed_scope_remain_visible() {
    let reference = world_reference().unwrap();
    let unknown = reference.dependency(UsDependency::MinorOutlyingIslands);
    assert_eq!(
        unknown.population().status(),
        PopulationStatus::NotPublished
    );
    assert_eq!(unknown.population().persons(), None);
    assert_eq!(
        reference
            .dependency(UsDependency::PuertoRico)
            .population()
            .persons(),
        Some(3_242_204)
    );
    let aland = reference.member("m49:248").unwrap();
    assert_eq!(
        aland.population().status(),
        PopulationStatus::DesignedScopeApportionment
    );
    assert_eq!(aland.population().persons(), Some(30_654));
    assert_eq!(
        reference
            .member("m49:246")
            .unwrap()
            .population()
            .source_thousands_raw(),
        Some("5617.31")
    );
    assert!(reference
        .counterpart(ForeignCounterpart::RemainingAsiaPacific)
        .population()
        .missing_identities()
        .contains(&"m49:612".to_owned()));
}

#[test]
fn parent_populations_and_trade_children_remain_separate_measures() {
    let reference = world_reference().unwrap();
    let gaza = reference.member("census:5082").unwrap();
    assert_eq!(gaza.population().status(), PopulationStatus::TradeOnly);
    assert_eq!(gaza.population().persons(), None);
    assert_eq!(gaza.population().accounted_in_identity(), Some("m49:275"));
    assert_eq!(
        gaza.goods_trade().us_imports_annual_millions_raw(),
        Some("0.20487")
    );
    assert_eq!(
        gaza.goods_trade().us_exports_annual_millions_raw(),
        Some("0.559747")
    );
    assert_eq!(
        reference.member("m49:275").unwrap().population().persons(),
        Some(5_495_443)
    );
    assert_eq!(
        reference
            .member("m49:275")
            .unwrap()
            .goods_trade()
            .us_imports_annual_millions_raw(),
        None
    );
    let christmas = reference.member("m49:162").unwrap();
    assert_eq!(
        christmas.population().status(),
        PopulationStatus::IncludedInParent
    );
    assert_eq!(
        christmas.population().accounted_in_identity(),
        Some("m49:036")
    );
    assert!(reference.member("m49:999").is_none());
}

#[test]
fn changing_a_source_cannot_silently_reclassify_or_repopulate_the_world() {
    let population = include_bytes!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../src/babylon/data/reference/economy/world_population_reference_2024.csv.gz"
    ));
    let trade = include_bytes!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../../src/babylon/data/reference/economy/international_counterpart_reference_2024.csv.gz"));
    assert!(WorldReference::decode_pinned(population, trade).is_ok());
    let mut changed = population.to_vec();
    changed[100] ^= 1;
    assert_eq!(
        WorldReference::decode_pinned(&changed, trade),
        Err(WorldReferenceError::ArtifactDigest)
    );
    let mut changed = trade.to_vec();
    changed.push(0);
    assert_eq!(
        WorldReference::decode_pinned(population, &changed),
        Err(WorldReferenceError::ArtifactDigest)
    );
}
