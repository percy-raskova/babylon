//! The full generated opening preserves actual resident partitions and finite relations.
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{
    CommodityKind, EquipmentAssetId, RollingProcessSupply, StaffingWorkSource, SupplierTransport,
};
use babylon_persistence::{
    economic_catalog::{CatalogCapacity, EconomicOpening},
    national_cohorts::national_cohort_reference,
    national_counties::national_county_reference,
    national_economy::{build_national_opening, NationalGamePolicy},
    national_resident_workforce::national_resident_workforce_reference,
    national_transport::national_transport_reference,
    world_reference::world_reference,
};
use std::collections::{BTreeMap, BTreeSet};

#[path = "support/national_household_controls.rs"]
mod household_controls;

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
    let opening = build_national_opening(
        counties,
        cohorts,
        residents,
        babylon_persistence::national_households::national_household_reference().unwrap(),
        world,
        transport,
        &policy,
    )
    .unwrap();
    eprintln!("native opening generation: {:?}", start.elapsed());
    household_controls::assert_people(&opening, &policy);
    household_controls::assert_endowments_and_ownership(&opening, &policy);
    assert_markets(&opening, &policy);
    assert_routes(&opening);
    assert_unique_principals(&opening, &policy);
    assert_missing_retail_fallback(&opening);
    census(&opening);
    assert_managed_equipment(&opening);
    household_controls::assert_admitted_state(&opening);
}

fn assert_managed_equipment(opening: &EconomicOpening) {
    let CatalogCapacity::Rolling(RollingProcessSupply::Equipment(equipment)) = &opening.capacity
    else {
        panic!("national play requires managed equipment, not permanent nameplate capacity");
    };
    assert!(equipment.pending.is_empty());
    assert_eq!(
        equipment.bindings.len(),
        opening
            .sites
            .iter()
            .map(|s| s.processes.len())
            .sum::<usize>()
    );
    let carrying: BTreeMap<_, _> = opening.equipment.iter().map(|r| (r.asset, r)).collect();
    let bindings: BTreeMap<_, _> = equipment
        .bindings
        .iter()
        .map(|b| (b.process_id, b))
        .collect();
    let definitions: BTreeMap<_, _> = equipment.definitions.iter().map(|d| (d.id, d)).collect();
    let pools: BTreeMap<_, _> = opening
        .staffing
        .iter()
        .map(|s| (s.pool.site_id(), &s.pool))
        .collect();
    for policy in &equipment.installation_policies {
        let pool = pools[&bindings[&policy.process_id].site_id];
        assert!(pool
            .work_sources()
            .contains(&StaffingWorkSource::Installation(policy.process_id)));
        assert!(policy.maximum_hours_per_period <= pool.labor_force() * 160);
    }
    assert_eq!(carrying.len(), equipment.cohorts.len());
    for cohort in &equipment.cohorts {
        let value = carrying[&EquipmentAssetId::Installed(cohort.id)];
        let owner = bindings[&cohort.process_id].site_id;
        assert_eq!(value.owner, owner);
        assert!(value.amount.micro_units() > 0);
        assert!(cohort.units > 0 && cohort.remaining_service_batches > 0);
        assert_eq!(cohort.usable_from_period, 1);
    }
    let routes: BTreeSet<_> = opening
        .logistics
        .supplier_routes
        .iter()
        .map(|r| (r.buyer_site_id, r.supplier_site_id, r.good_id, r.unit_id))
        .collect();
    for policy in &equipment.investment_policies {
        let binding = bindings[&policy.process_id];
        let definition = definitions[&binding.definition_id];
        assert!(routes.contains(&(
            binding.site_id,
            policy.supplier_site_id,
            definition.equipment_good_id,
            definition.equipment_unit_id
        )));
        assert!(policy.maximum_purchase_per_period > 0);
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
            if household.kind == babylon_material_circuit::HouseholdKind::CollectiveResidence
                && need.basis == babylon_material_circuit::HouseholdNeedBasis::Households
            {
                continue;
            }
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
    let templates: BTreeMap<_, _> = opening
        .household_templates
        .iter()
        .map(|t| (t.id, t.needs.len()))
        .collect();
    let needs = opening
        .households
        .iter()
        .map(|h| templates[&h.template])
        .sum::<usize>();
    eprintln!("household census: templates={templates:?} needs={needs} purchases={} pantry_rows={} claims={} tax_policies={} public_allocations={}",
        opening.policies.household_purchases.len(), opening.households.iter().map(|h| h.opening_stock.len()).sum::<usize>(),
        opening.institutions.ownership.len(), opening.institutions.taxes.len(), opening.institutions.public_allocations.len());
    eprintln!("opening census: sites={} households={} staffing_pools={} staffing_members={} stocks={} inputs={} offers={} procurement={} service_inputs={} connections={} supplier_routes={} stages={} memberships={} cash_accounts={}",
        opening.sites.len(),opening.households.len(),opening.staffing.len(),opening.staffing.iter().map(|s|s.members.len()).sum::<usize>(),
        opening.sites.iter().map(|s|s.opening_stock.len()).sum::<usize>(),opening.sites.iter().map(|s|s.processes.iter().map(|p| opening.recipes.iter().find(|r|r.id==p.recipe).unwrap().inputs.len()).sum::<usize>()).sum::<usize>(),
        opening.policies.offers.len(),opening.policies.replenishment.len(),opening.policies.service_inputs.len(),opening.policies.service_connections.len(),
        opening.logistics.supplier_routes.len(),opening.logistics.route_stages.len(),opening.logistics.memberships.len(),
        opening.sites.len()+opening.households.len()+opening.institutional_cash.len());
}
