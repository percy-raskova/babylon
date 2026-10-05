//! Explicit control import contracts through the common source authority.
use super::*;
use crate::economic_catalog::{CapturedEconomicCatalog, SourceArtifactKind};
use std::collections::BTreeMap;

#[test]
fn captured_rule_source_survives_restart_without_reopening_current_authored_rules() {
    use crate::economic_content::admit_economic_content;
    use crate::michigan_content::MichiganContentPreset;
    let original = crate::test_support::catalog();
    let mut control = original.capture.clone();
    control.rule_source = format!("; Captured campaign source.\n{}", control.rule_source);
    let rules = control.rule_source.as_bytes().to_vec();
    let mut changed = original.keep_sources(MichiganMaterialCatalog::capture(control).unwrap());
    changed.replace_source(SourceArtifactKind::Rules, rules);
    let preset = MichiganContentPreset::FourWeekStandard;
    let original_foundation = preset.create_foundation(&original).unwrap();
    let restored_foundation = preset.create_foundation(&changed).unwrap();
    assert_ne!(original_foundation.digest(), restored_foundation.digest());
    assert_eq!(
        original_foundation
            .graph_foundation()
            .content_digest()
            .rules_hash,
        restored_foundation
            .graph_foundation()
            .content_digest()
            .rules_hash,
        "comments change captured bytes but not the canonical rule"
    );
    assert_eq!(
        original_foundation.initial_register(),
        restored_foundation.initial_register()
    );
    assert_eq!(
        restored_foundation
            .graph_foundation()
            .content_bundle()
            .rule_source_bytes(),
        changed.rule_source().as_bytes()
    );
    assert!(admit_economic_content(
        preset.id(),
        restored_foundation.spec().duration,
        &restored_foundation.spec().content_digest,
        &restored_foundation.digest(),
        0,
        &restored_foundation.export_canonical_bytes().unwrap()
    )
    .is_ok());
}

#[test]
fn captured_material_content_refuses_missing_rules_and_a_graph_only_rule_set() {
    let original = crate::test_support::catalog();
    for rules in ["", "; no executable material cycle\n"] {
        let mut control = original.capture.clone();
        control.rule_source = rules.to_owned();
        let changed = MichiganMaterialCatalog::capture(control);
        if rules.is_empty() {
            assert!(changed.is_err());
        } else {
            let mut changed = original.keep_sources(changed.unwrap());
            changed.replace_source(SourceArtifactKind::Rules, rules.as_bytes().to_vec());
            assert!(
                crate::michigan_content::MichiganContentPreset::FourWeekStandard
                    .create_foundation(&changed)
                    .is_err()
            );
        }
    }
}

#[test]
fn normalized_permutations_and_preset_round_trips_preserve_common_authority() {
    let original = crate::test_support::catalog();
    let mut control = original.capture.clone();
    control.normalized.sites.reverse();
    control.normalized.processes.reverse();
    control.normalized.goods.reverse();
    control.normalized.owners.reverse();
    control.normalized.industry.reverse();
    control.normalized.staffing.pools.reverse();
    control.interventions.reverse();
    let reordered = original.keep_sources(MichiganMaterialCatalog::capture(control).unwrap());
    let original_capture = CapturedEconomicCatalog::from_michigan(&original).unwrap();
    let reordered_capture = CapturedEconomicCatalog::from_michigan(&reordered).unwrap();
    assert_eq!(
        original_capture.canonical_bytes(),
        reordered_capture.canonical_bytes()
    );
    let constrained = original
        .with_preset(MichiganDeliveryPreset::SharedFreightConstrained)
        .unwrap();
    let captured = CapturedEconomicCatalog::from_michigan(&constrained).unwrap();
    let restored =
        CapturedEconomicCatalog::decode(captured.canonical_bytes(), captured.digest()).unwrap();
    assert_eq!(captured.opening(), restored.opening());
    assert_ne!(original_capture.digest(), captured.digest());
    assert_eq!(
        original,
        constrained
            .with_preset(MichiganDeliveryPreset::Standard)
            .unwrap()
    );
    assert!(constrained
        .with_preset(MichiganDeliveryPreset::StatewideBoth)
        .is_err());
}

fn merchant_fixture() -> MichiganMaterialCatalog {
    let original = MichiganMaterialCatalog::from_defines_toml(include_str!(
        "../../../../../content/scenarios/michigan/defines.toml"
    ))
    .unwrap();
    let mut c = original.capture.normalized;
    let mut second = c
        .processes
        .iter()
        .find(|p| p.key == "panel-forming")
        .unwrap()
        .clone();
    second.key = "second-panel-process".to_owned();
    second.inputs.push(MichiganMaterialInput {
        good_key: "meal".to_owned(),
        quantity_per_batch: 1,
        opening_quantity: 5,
    });
    c.staffing
        .pools
        .iter_mut()
        .find(|p| p.site_key == second.site_key)
        .unwrap()
        .process_keys
        .push(second.key.clone());
    c.processes.push(second);
    append_fixture_merchants(&mut c);
    let supplier = c
        .processes
        .iter()
        .find(|p| p.key == "sheet-rolling")
        .unwrap()
        .site_key
        .clone();
    for (key, supplier, buyer) in [
        ("fixture-purchase", supplier, "fixture-42".to_owned()),
        (
            "fixture-resale",
            "fixture-42".to_owned(),
            "fixture-44-45".to_owned(),
        ),
    ] {
        c.routes.push(MichiganMaterialRoute {
            key: key.to_owned(),
            supplier_site_key: supplier,
            buyer_site_key: buyer,
            good_key: "sheet".to_owned(),
            ordered_quantity: 20,
            path: MichiganMaterialPath::Local,
        });
    }
    c.final_demands.push(MichiganFinalDemand {
        key: "fixture-final".to_owned(),
        retailer_site_key: "fixture-44-45".to_owned(),
        county_geoid: "26163".to_owned(),
        good_key: "sheet".to_owned(),
        ordered_quantity: 20,
    });
    MichiganMaterialCatalog::from_normalized(
        original.capture.defines,
        c,
        MichiganDeliveryPreset::Standard,
        Vec::new(),
    )
    .unwrap()
}
#[test]
fn normalized_multi_input_owners_share_inventory_and_labor_and_merchants_have_no_fake_road() {
    let c = merchant_fixture();
    let state = crate::economic_catalog::import_michigan_opening(&c)
        .unwrap()
        .compile()
        .unwrap()
        .state;
    let p = c
        .processes()
        .iter()
        .find(|p| p.key == "second-panel-process")
        .unwrap();
    assert_eq!(
        state
            .input_coefficients
            .iter()
            .filter(|r| r.process_id == p.id())
            .count(),
        2
    );
    assert_eq!(
        state
            .labor
            .iter()
            .filter(|r| r.site_id == p.site_id())
            .count(),
        1
    );
    assert_eq!(
        state
            .inventory
            .iter()
            .filter(|r| r.site_id == p.site_id() && r.good_id == c.good("sheet").unwrap().id())
            .count(),
        1
    );
    assert_eq!(state.merchants.len(), 2);
    assert_eq!(state.final_demand_orders.len(), 1);
    assert_eq!(state.supplier_routes.len(), 5);
    assert_eq!(state.route_stages.len(), 3);
    assert!(state.freight.is_empty());
    for route in state
        .supplier_routes
        .iter()
        .filter(|r| r.transport_kind == babylon_material_circuit::SupplierTransport::Local)
    {
        assert!(!state
            .route_stages
            .iter()
            .any(|s| s.route_id == route.route_id));
    }
}
#[test]
fn observed_suppression_remains_absent_and_zero_employment_can_recover_from_reserve() {
    let c = merchant_fixture();
    let mut capture = c.capture;
    let row = &mut capture.normalized.industry[0];
    row.disclosure_code = "N".to_owned();
    row.annual_avg_emplvl = None;
    row.total_annual_wages = None;
    row.annual_avg_wkly_wage = None;
    let pool = &mut capture.normalized.staffing.pools[0];
    pool.employed = 0;
    pool.reserve = 5;
    pool.previous_unretained_hours = 0;
    let accepted = MichiganMaterialCatalog::capture(capture.clone()).unwrap();
    assert_eq!(
        accepted.capture.normalized.industry[0].annual_avg_emplvl,
        None
    );
    capture.normalized.industry[0].annual_avg_emplvl = Some(0);
    assert!(MichiganMaterialCatalog::capture(capture).is_err());
}
#[test]
fn complete_statewide_workforce_graph_stays_inside_the_source_bound() {
    let seeds = (0..397)
        .map(|n| MichiganWorkforceSeed {
            key: format!("owner-{:05}-31-33", 26001 + n),
            site_key: format!("owner-{n}"),
            process_keys: Vec::new(),
            merchant_handling: true,
            maintenance: false,
            employed: 20,
            reserve: 4,
            previous_unretained_hours: 3200,
        })
        .collect::<Vec<_>>();
    let source = crate::michigan_cohorts::michigan_staffed_scenario(&seeds).unwrap();
    assert!(source.len() < 1_048_576);
    eprintln!("397-pool observed graph source: {} bytes", source.len());
}

fn append_fixture_merchants(c: &mut MichiganNormalizedContent) {
    for (sector, role) in [
        ("42", MichiganSiteRole::Wholesale),
        ("44-45", MichiganSiteRole::Retail),
    ] {
        let source =
            regional::owner_source("26163", sector, MICHIGAN_INDUSTRY_BASELINE_SHA256).unwrap();
        let key = format!("fixture-{sector}");
        c.industry.push(MichiganIndustryBaselineRow {
            area_fips: "26163".to_owned(),
            area_title: "Wayne County, Michigan".to_owned(),
            industry_code: sector.to_owned(),
            industry_title: source.sector_title.clone(),
            own_code: "5".to_owned(),
            agglvl_code: "74".to_owned(),
            disclosure_code: source.disclosure_code.clone(),
            annual_avg_estabs_count: source.annual_avg_estabs_count,
            annual_avg_emplvl: source.annual_avg_emplvl,
            total_annual_wages: source.total_annual_wages,
            annual_avg_wkly_wage: source.annual_avg_wkly_wage,
            source_file: source.county_source_file.clone(),
            source_sha256: source.county_source_sha256.clone(),
        });
        c.owners.push(source);
        c.sites.push(MichiganMaterialSite {
            key: key.clone(),
            label: format!("Synthetic local {sector} fixture"),
            county_geoid: "26163".to_owned(),
            naics: sector.to_owned(),
            sector_code: sector.to_owned(),
            role,
        });
        c.staffing.pools.push(MichiganWorkforceSeed {
            key: key.clone(),
            site_key: key.clone(),
            process_keys: Vec::new(),
            merchant_handling: true,
            maintenance: false,
            employed: 1,
            reserve: 0,
            previous_unretained_hours: 160,
        });
        let capacity_key = format!("handling-{sector}");
        c.corridors.push(MichiganMaterialCorridor {
            key: capacity_key.clone(),
            label: format!("Synthetic {sector} handling"),
            capacity_grams_per_period: 1_000_000,
        });
        c.merchants.push(MichiganMerchant {
            site_key: key,
            capacity_key,
            handling_hours_per_unit: BTreeMap::from([("sheet".to_owned(), 1)]),
        });
    }
}
