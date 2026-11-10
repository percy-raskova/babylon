//! Post-aid integration counterexamples through the ordinary opening consumers.
use super::{aid, Builder, NationalOpening};
use crate::national_cohorts;
use crate::national_counties;
use crate::national_economy::grain::{CatchmentReason, ContributionDestination};
use crate::national_economy::{NationalGamePolicy, ResidentWorkplaceSource};
use crate::national_household_allocation::{self, NationalHouseholdAllocation};
use crate::national_household_refinement;
use crate::national_household_time_allocation::{self, NationalHouseholdTimeAllocation};
use crate::national_households;
use crate::national_resident_allocation::{self, ResidentWorkplaceAllocation};
use crate::national_resident_workforce;
use crate::national_transport;
use crate::world_reference;
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_kernel::geography::CountyGeoid;
use babylon_material_circuit::{CommodityKind, EquipmentAssetId, HouseholdNeedBasis};
use std::collections::BTreeMap;

fn policy() -> NationalGamePolicy {
    NationalGamePolicy::parse(include_str!(
        "../../../../../../content/scenarios/national/defines.toml"
    ))
    .expect("authored policy")
}
fn prepared(
    policy: &NationalGamePolicy,
) -> (
    Builder<'_>,
    ResidentWorkplaceAllocation,
    NationalHouseholdAllocation,
    NationalHouseholdTimeAllocation,
) {
    let counties = national_counties::national_county_reference().expect("counties");
    let residents =
        national_resident_workforce::national_resident_workforce_reference().expect("residents");
    let budgets = national_household_allocation::allocate_households(
        counties,
        national_households::national_household_reference().expect("households"),
        residents,
        policy.households.private_owner_households_bps,
    )
    .expect("household allocation");
    let time = national_household_time_allocation::allocate_household_time(counties, &budgets)
        .expect("time");
    let leaves = national_household_refinement::refine_households(&budgets, &time, &[])
        .expect("source leaves");
    let mut allocation = national_resident_allocation::allocate_home_county(
        counties,
        national_cohorts::national_cohort_reference().expect("cohorts"),
        residents,
        &budgets,
        &leaves,
        policy,
    )
    .expect("source allocation");
    let mut builder = Builder::new(
        policy,
        national_transport::national_transport_reference().expect("transport"),
    )
    .expect("builder");
    aid::prepare(
        &mut builder,
        &budgets,
        &time,
        &mut allocation,
        policy.source_digest,
    )
    .expect("exact aid preparation");
    (builder, allocation, budgets, time)
}
fn finish(
    builder: Builder<'_>,
    allocation: ResidentWorkplaceAllocation,
    budgets: &NationalHouseholdAllocation,
    time: &NationalHouseholdTimeAllocation,
) -> NationalOpening {
    builder
        .finish(
            national_counties::national_county_reference().expect("counties"),
            world_reference::world_reference().expect("world"),
            allocation,
            budgets,
            time,
        )
        .expect("ordinary post-aid opening construction")
}
fn finite_opening(persons: [u64; 2]) -> NationalOpening {
    let mut policy = policy();
    let need = policy
        .household_needs
        .iter_mut()
        .find(|n| n.key == "food")
        .expect("food need");
    need.basis = HouseholdNeedBasis::Persons;
    need.units_per_basis = 1;
    policy.commodities.get_mut("food").expect("food").kind = CommodityKind::Storable {
        grams_per_unit: 14_000,
    };
    policy
        .recipes
        .get_mut(&EconomicFunction::Food)
        .expect("food recipe")
        .labor_hours_per_batch = 1_000_000_000_000;
    let (builder, mut allocation, mut budgets, mut time) = prepared(&policy);
    for (county, persons) in ["26001", "26003"].into_iter().zip(persons) {
        let county = CountyGeoid::try_from(county).expect("county");
        let control = allocation
            .counties
            .iter_mut()
            .find(|c| c.county == county)
            .expect("source control");
        let children = persons
            .checked_sub(control.population)
            .expect("only add designed fixture children");
        control.population = persons;
        control.younger_than_sixteen += children;
        budgets.add_fixture_children(county, children);
        time.add_fixture_children(county, children);
    }
    finish(builder, allocation, &budgets, &time)
}
#[test]
fn post_aid_food_demand_cannot_merge_two_individually_sufficient_lanes() {
    let opening = finite_opening([1_000_000, 1_000_000]);
    let witness = &opening.representation;
    let cells: Vec<_> = ["26001", "26003"]
        .iter()
        .map(|c| {
            let county = CountyGeoid::try_from(*c).expect("county");
            witness
                .catchments
                .iter()
                .find(|cell| cell.members.contains(&county))
                .expect("one membership")
        })
        .collect();
    assert_ne!(
        cells[0].id, cells[1].id,
        "28 billion grams cannot share one original 20 billion gram lane"
    );
    for cell in cells {
        assert_eq!(cell.capacity_grams, Some(20_000_000_000));
        assert_eq!(
            cell.optimistic_output, 0,
            "captured recipe has no full labor batch"
        );
        assert!(
            cell.essential_import_grams >= 14_000_000_000
                && cell.essential_import_grams <= 20_000_000_000
        );
        assert_eq!(cell.reason, CatchmentReason::CapacitySubdivision);
    }
    assert_eq!(witness.counties.len(), 3144);
    for child in &opening.aid.children {
        assert!(opening
            .opening
            .households
            .iter()
            .any(|h| h.principal_id == child.principal && h.persons == child.persons));
    }
    opening
        .opening
        .compile()
        .expect("finite fixture ordinary compiler");
}
#[test]
fn post_aid_preexisting_access_deficit_remains_a_scarce_singleton() {
    let opening = finite_opening([2_000_000, 1_000_000]);
    let county = CountyGeoid::try_from("26001").expect("county");
    let cell = opening
        .representation
        .catchments
        .iter()
        .find(|cell| cell.members.contains(&county))
        .expect("membership");
    assert_eq!(cell.members, vec![county]);
    assert_eq!(
        cell.reason,
        CatchmentReason::PreExistingEssentialAccessDeficit
    );
    assert_eq!(cell.essential_import_grams, 28_000_000_000);
    assert_eq!(cell.capacity_grams, Some(20_000_000_000));
}
#[test]
fn source_floors_reach_live_installations_stock_and_equipment() {
    let mut policy = policy();
    policy
        .recipes
        .get_mut(&EconomicFunction::Food)
        .expect("food")
        .labor_hours_per_batch = 300;
    let (builder, allocation, budgets, time) = prepared(&policy);
    let source_hours: BTreeMap<_, _> = allocation
        .workplaces
        .iter()
        .map(|row| {
            (
                row.target.site_id,
                row.members
                    .iter()
                    .map(|m| m.seed.employed * policy.work_hours_per_person)
                    .sum::<u64>(),
            )
        })
        .collect();
    let opening = finish(builder, allocation, &budgets, &time);
    let sites: BTreeMap<_, _> = opening
        .opening
        .sites
        .iter()
        .map(|s| (s.site_id, s))
        .collect();
    let mut sums = BTreeMap::<_, (u64, u64, u64, u64, i128)>::new();
    for incidence in &opening.representation.source_incidence {
        if sites[&incidence.destination_site].function != EconomicFunction::Food
            || incidence.source_site == incidence.destination_site
        {
            continue;
        }
        let total = sums.entry(incidence.destination_site).or_default();
        total.0 += source_hours[&incidence.source_site];
        total.1 += source_hours[&incidence.source_site] / 300;
        total.2 += incidence.endowment.equipment_units;
        total.3 += incidence.endowment.equipment_service_batches;
        total.4 += incidence.endowment.equipment_carrying_micros;
    }
    assert!(
        sums.values().any(|t| t.0 / 300 > t.1),
        "real nondivisible source controls expose floor-after-sum inflation"
    );
    let food = &policy.commodities["food"];
    for (site_id, (_, batches, units, service, carrying)) in sums {
        let site = sites[&site_id];
        let process = &site.processes[0];
        assert_eq!(
            process.planned_batches, batches,
            "ordinary installation consumes source floors"
        );
        let stock = site
            .opening_stock
            .iter()
            .find(|s| s.amount.good_id == food.good_id)
            .expect("food output stock");
        assert_eq!(
            stock.amount.quantity,
            batches * policy.recipes[&EconomicFunction::Food].output_units_per_batch
        );
        let cohort = opening
            .opening
            .equipment_position
            .cohorts
            .iter()
            .find(|c| c.process_id == process.process_id);
        if units == 0 {
            assert!(cohort.is_none());
            continue;
        }
        let cohort = cohort.expect("finite equipment");
        assert_eq!(
            (cohort.units, cohort.remaining_service_batches),
            (units, service)
        );
        let value = opening
            .opening
            .equipment
            .iter()
            .find(|e| e.asset == EquipmentAssetId::Installed(cohort.id))
            .expect("carrying value");
        assert_eq!(value.amount.micro_units(), carrying);
    }
    opening
        .opening
        .compile()
        .expect("floor-preserving opening compiles");
}
#[test]
fn designed_background_keeps_each_retained_source_ownership_axis() {
    let policy = policy();
    let (builder, allocation, budgets, time) = prepared(&policy);
    let opening = finish(builder, allocation, &budgets, &time);
    let detail: BTreeMap<_, _> = opening
        .detail
        .background_workplaces()
        .iter()
        .map(|row| (row.site_id, &row.key))
        .collect();
    let mut compared = 0;
    for source in &opening.representation.source_incidence {
        let ResidentWorkplaceSource::Qcew(key) = source.source else {
            continue;
        };
        if source.source_site == source.destination_site {
            continue;
        }
        assert_eq!(
            detail[&source.destination_site].ownership,
            Some(key.ownership),
            "Designed live representative retains typed source ownership"
        );
        compared += 1;
    }
    assert!(compared > 100, "many actual source groups checked");
    assert!(opening.representation.counties.iter().any(|c| matches!(
        c.destination,
        ContributionDestination::Representative { .. }
    )));
}
