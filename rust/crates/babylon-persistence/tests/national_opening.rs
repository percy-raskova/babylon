//! The full generated opening preserves actual resident partitions and finite relations.
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{CommodityKind, SupplierTransport};
use babylon_persistence::{
    economic_catalog::EconomicOpening,
    national_cohorts::national_cohort_reference,
    national_counties::national_county_reference,
    national_economy::{build_national_opening, NationalGamePolicy},
    national_resident_workforce::national_resident_workforce_reference,
    national_transport::national_transport_reference,
    world_reference::world_reference,
};
use std::collections::{BTreeMap, BTreeSet};

#[test]
fn full_opening_conserves_counted_households_and_uses_finite_connected_accounts() {
    let policy = NationalGamePolicy::parse(include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../content/scenarios/national/defines.toml"
    )))
    .unwrap();
    let counties = national_county_reference().unwrap();
    let cohorts = national_cohort_reference().unwrap();
    let residents = national_resident_workforce_reference().unwrap();
    let world = world_reference().unwrap();
    let transport = national_transport_reference().unwrap();
    let start = std::time::Instant::now();
    let opening =
        build_national_opening(counties, cohorts, residents, world, transport, &policy).unwrap();
    eprintln!("native opening generation: {:?}", start.elapsed());
    assert_people(&opening);
    assert_markets(&opening, &policy);
    assert_routes(&opening);
    assert_unique_principals(&opening, &policy);
    assert_missing_retail_fallback(&opening);
    census(&opening);
}

fn assert_people(opening: &EconomicOpening) {
    let domestic: Vec<_> = opening
        .households
        .iter()
        .filter(|r| matches!(r.location, EconomicLocation::County(_)))
        .collect();
    assert_eq!(domestic.len(), 3_144);
    assert_eq!(domestic.iter().map(|r| r.persons).sum::<u64>(), 334_922_499);
    assert_eq!(opening.households.len(), 3_162);
    let members: Vec<_> = opening
        .staffing
        .iter()
        .flat_map(|r| &r.members)
        .filter(|m| matches!(m.member.residence(), EconomicLocation::County(_)))
        .collect();
    assert_eq!(members.len(), 62_745);
    assert_eq!(members.iter().map(|m| m.employed).sum::<u64>(), 161_297_155);
    assert_eq!(members.iter().map(|m| m.reserve).sum::<u64>(), 8_902_365);
    assert_eq!(opening.sites.len(), 60_634);
    assert!(opening.orders.goods.is_empty() && opening.orders.final_demand.is_empty());
    assert_eq!(opening.recipes.len(), 9);
    assert_eq!(opening.household_templates.len(), 1);
    let residents: BTreeMap<_, _> = opening
        .households
        .iter()
        .map(|r| (r.principal_id, r))
        .collect();
    for row in &opening.staffing {
        assert!(row.workplace.canonical_bytes().is_ok());
        for m in &row.members {
            assert!(m.subject.canonical_bytes().is_ok());
            assert_eq!(m.employed + m.reserve, m.member.labor_force());
            assert_eq!(
                residents[&m.member.household_id()].location,
                m.member.residence()
            );
        }
    }
}

fn assert_markets(opening: &EconomicOpening, policy: &NationalGamePolicy) {
    let sites: BTreeMap<_, _> = opening.sites.iter().map(|s| (s.site_id, s)).collect();
    let service_keys: BTreeSet<_> = policy
        .commodities
        .values()
        .filter(|g| matches!(g.kind, CommodityKind::PeriodService { .. }))
        .map(|g| (g.good_id, g.unit_id))
        .collect();
    let purchases: BTreeMap<_, _> = opening
        .policies
        .household_purchases
        .iter()
        .map(|p| ((p.principal_id, p.good_id, p.unit_id), p))
        .collect();
    for household in &opening.households {
        assert!(household.subject.canonical_bytes().is_ok());
        for need in &policy.household_needs {
            let good = &policy.commodities[&need.key];
            let purchase = purchases[&(household.principal_id, good.good_id, good.unit_id)];
            assert!(purchase.enabled && purchase.maximum_purchase > 0);
            if matches!(good.kind, CommodityKind::Storable { .. }) {
                assert_eq!(
                    sites[&purchase.retailer_site_id].location,
                    household.location
                );
                assert!(sites[&purchase.retailer_site_id].merchant.is_some());
            }
        }
        assert!(household
            .opening_stock
            .iter()
            .all(|s| !service_keys.contains(&(s.amount.good_id, s.amount.unit_id))));
    }
}

fn assert_routes(opening: &EconomicOpening) {
    let sites: BTreeMap<_, _> = opening.sites.iter().map(|s| (s.site_id, s)).collect();
    assert!(opening.logistics.supplier_routes.iter().any(|r| matches!(
        sites[&r.buyer_site_id].location,
        EconomicLocation::County(_)
    ) && matches!(
        sites[&r.supplier_site_id].location,
        EconomicLocation::Foreign(_)
    )));
    assert!(opening.logistics.supplier_routes.iter().any(|r| matches!(
        sites[&r.buyer_site_id].location,
        EconomicLocation::Foreign(_)
    ) && matches!(
        sites[&r.supplier_site_id].location,
        EconomicLocation::County(_)
    )));
    let stages: BTreeSet<_> = opening
        .logistics
        .route_stages
        .iter()
        .map(|r| (r.route_id, r.stage_index))
        .collect();
    let capacities: BTreeSet<_> = opening
        .logistics
        .shared_capacity
        .iter()
        .map(|r| r.corridor_id)
        .collect();
    for row in &opening.logistics.supplier_routes {
        if row.transport_kind == SupplierTransport::Staged {
            assert!(stages.contains(&(row.route_id, 0)));
        }
    }
    for row in &opening.logistics.memberships {
        assert!(stages.contains(&(row.route_id, row.stage_index)));
        assert!(capacities.contains(&row.corridor_id));
    }
}

fn assert_unique_principals(opening: &EconomicOpening, policy: &NationalGamePolicy) {
    let service_keys: BTreeSet<_> = policy
        .commodities
        .values()
        .filter(|g| matches!(g.kind, CommodityKind::PeriodService { .. }))
        .map(|g| (g.good_id, g.unit_id))
        .collect();
    for site in &opening.sites {
        assert!(site.opening_cash.micro_units() >= 0);
        let keys: BTreeSet<_> = site
            .opening_stock
            .iter()
            .map(|s| (s.amount.good_id, s.amount.unit_id))
            .collect();
        assert_eq!(keys.len(), site.opening_stock.len());
        assert!(keys.is_disjoint(&service_keys));
    }
    let procurement_keys: BTreeSet<_> = opening
        .policies
        .replenishment
        .iter()
        .map(|r| (r.buyer_site_id, r.supplier_site_id, r.good_id, r.unit_id))
        .collect();
    assert_eq!(procurement_keys.len(), opening.policies.replenishment.len());
    let offer_keys: BTreeSet<_> = opening
        .policies
        .offers
        .iter()
        .map(|r| (r.site_id, r.good_id, r.unit_id))
        .collect();
    assert_eq!(offer_keys.len(), opening.policies.offers.len());
}

fn assert_missing_retail_fallback(opening: &EconomicOpening) {
    // This real county has no captured QCEW distribution cohort. Retail work
    // must reuse its four already-accounted sites and finite workforce.
    let kalawao: EconomicLocation = "county:15005".parse().unwrap();
    let kalawao_sites: Vec<_> = opening
        .sites
        .iter()
        .filter(|s| s.location == kalawao)
        .collect();
    assert_eq!(kalawao_sites.len(), 4);
    assert_eq!(
        kalawao_sites
            .iter()
            .filter(|s| s.merchant.is_some())
            .count(),
        1
    );
    let kalawao_pool = opening
        .staffing
        .iter()
        .find(|s| {
            s.pool.site_id()
                == kalawao_sites
                    .iter()
                    .find(|s| s.merchant.is_some())
                    .unwrap()
                    .site_id
        })
        .unwrap();
    assert!(kalawao_pool.pool.work_sources().len() >= 2);
    assert!(
        kalawao_pool
            .members
            .iter()
            .map(|m| m.employed + m.reserve)
            .sum::<u64>()
            > 0
    );
}

fn census(opening: &EconomicOpening) {
    eprintln!("opening census: sites={} households={} staffing_pools={} staffing_members={} stocks={} inputs={} offers={} procurement={} service_inputs={} connections={} supplier_routes={} stages={} memberships={} cash_accounts={}",
        opening.sites.len(),opening.households.len(),opening.staffing.len(),opening.staffing.iter().map(|s|s.members.len()).sum::<usize>(),
        opening.sites.iter().map(|s|s.opening_stock.len()).sum::<usize>(),opening.sites.iter().map(|s|s.processes.iter().map(|p| opening.recipes.iter().find(|r|r.id==p.recipe).unwrap().inputs.len()).sum::<usize>()).sum::<usize>(),
        opening.policies.offers.len(),opening.policies.replenishment.len(),opening.policies.service_inputs.len(),opening.policies.service_connections.len(),
        opening.logistics.supplier_routes.len(),opening.logistics.route_stages.len(),opening.logistics.memberships.len(),
        opening.sites.len()+opening.households.len()+opening.institutional_cash.len());
}
