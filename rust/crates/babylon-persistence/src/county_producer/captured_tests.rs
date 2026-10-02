//! Current county selection must use the captured campaign roster.
use super::*;

#[test]
fn captured_national_counties_select_current_ct_and_island_identities_without_fake_detail() {
    let counties = crate::national_counties::NationalCountyReference::decode_pinned(
        include_bytes!("../../../../../src/babylon/data/reference/economy/national_county_reference_2024.csv.gz"),
    ).unwrap();
    let source = CountySource::national(&counties, None).unwrap();
    let mapping = counties
        .counties()
        .iter()
        .map(|county| {
            let geoid = county.geoid().to_string();
            (geoid.clone(), format!("county-{geoid}"))
        })
        .collect();
    let pages = source.plans(mapping, &BTreeMap::new()).unwrap();
    assert_eq!(pages.len(), 3_144);
    for selected in ["06037", "09110", "15005"] {
        assert!(pages.iter().any(|page| page.county_geoid() == selected));
    }
    for page in &pages {
        let geoid = babylon_kernel::geography::CountyGeoid::try_from(page.county_geoid()).unwrap();
        assert_eq!(page.title(), counties.county(geoid).unwrap().name());
        assert!(page.place_links().is_empty());
        assert!(page
            .decision_question()
            .contains("local place detail unavailable"));
        assert_eq!(page.signals().len(), 1);
        assert_eq!(page.signals()[0].grant_key(), "identity");
        assert_eq!(page.signals()[0].value(), page.county_geoid());
    }
    assert!(source
        .plans(
            vec![("09001".into(), "old-connecticut".into())],
            &BTreeMap::new()
        )
        .is_err());
    let mut forged = CommittedTerritoryFields::default();
    forged
        .insert_stored("qcew-employment", 1, None, Some(10))
        .unwrap();
    let forged = BTreeMap::from([("county-15005".into(), forged)]);
    assert!(source
        .plans(vec![("15005".into(), "county-15005".into())], &forged)
        .is_err());
}

#[test]
fn captured_county_identity_citation_round_trips_and_remains_grant_bound() {
    let counties = crate::national_counties::NationalCountyReference::decode_pinned(
        include_bytes!("../../../../../src/babylon/data/reference/economy/national_county_reference_2024.csv.gz"),
    ).unwrap();
    let source = CountySource::national(&counties, None).unwrap();
    let page = source
        .plans(
            vec![("15005".into(), "county-15005".into())],
            &BTreeMap::new(),
        )
        .unwrap()
        .remove(0);
    let citation = signal_citation(&page, &page.signals()[0], 3).unwrap();
    assert_eq!(citation.source_id(), "national-county-reference-2024-v1");
    assert!(citation
        .locator()
        .starts_with("national_county_reference_2024.csv.gz#county_geoid=15005&sha256="));
    let bullet = format!(
        "- **{}:** {} — {}; {}",
        page.signals()[0].label(),
        page.signals()[0].value(),
        citation.source_id(),
        citation.locator()
    );
    assert!(parse_signal_bullet(&bullet, 3).is_some());
    assert!(parse_signal_bullet(&bullet.replace("sha256=", "sha256=0"), 3).is_none());
    let keys = ["subject", "identity"];
    let index = CountyGrantIndex::try_from_rows(keys.map(|key| {
        (
            ArchiveSubjectKind::County,
            "15005".to_owned(),
            key.to_owned(),
        )
    }))
    .unwrap();
    let knowledge = crate::ArchiveKnowledge::try_new(
        keys.map(|key| {
            crate::ArchiveKnowledgeGrant::try_new(
                ArchivePageRef::try_new(ArchiveSubjectKind::County, "15005".to_owned()).unwrap(),
                key.to_owned(),
                1,
                citation.clone(),
            )
            .unwrap()
        })
        .into(),
    )
    .unwrap();
    let rendered = crate::FogSafeArchiveRenderer::new()
        .unwrap()
        .render(&county_page_input(&page, 3, [7; 32]).unwrap(), &knowledge)
        .unwrap();
    assert_eq!(
        parse_stored_county_page("15005", page.title(), rendered.markdown()),
        Some(desired_county_projection(&page, &index).unwrap())
    );
    let hidden = CountyGrantIndex::default();
    assert!(desired_county_projection(&page, &hidden)
        .unwrap()
        .signals()
        .is_empty());
}

#[test]
fn captured_spatial_detail_uses_supplied_bytes_and_refuses_source_drift() {
    let bytes = [
        include_bytes!("../fixtures/spatial_reference_products_v1.part-00.bin").as_slice(),
        include_bytes!("../fixtures/spatial_reference_products_v1.part-01.bin").as_slice(),
        include_bytes!("../fixtures/spatial_reference_products_v1.part-02.bin").as_slice(),
    ]
    .concat();
    let detail = crate::decode_michigan_dynamic_hex_foundation(
        &crate::michigan_dynamic_hex_foundation_fixture_parts().concat(),
    )
    .unwrap();
    let products = SpatialReferenceProducts::decode_captured(&bytes, &detail).unwrap();
    assert_eq!(products.places().len(), 745);
    assert_eq!(products.land_fractions().len(), 45_572);
    let pages = CountySource::Michigan(products)
        .plans(vec![("26163".into(), "wayne".into())], &BTreeMap::new())
        .unwrap();
    assert!(!pages[0].place_links().is_empty());
    assert!(pages[0]
        .place_links()
        .windows(2)
        .all(|pair| pair[0].place_geoid() < pair[1].place_geoid()));
    assert_eq!(pages[0].decision_question(), COUNTY_DECISION_QUESTION);
    assert!(SpatialReferenceProducts::decode_captured(&[], &detail).is_err());
    let mut changed = bytes;
    changed[52] ^= 1;
    assert!(SpatialReferenceProducts::decode_captured(&changed, &detail).is_err());
}
