//! Post-aid integration counterexamples through the ordinary opening consumers.
use super::{aid, Builder, NationalOpening};
use crate::national_cohorts;
use crate::national_counties;
use crate::national_economy;
use crate::national_economy::grain::{CatchmentReason, ContributionDestination};
use crate::national_economy::{NationalGamePolicy, ResidentWorkplaceSource};
use crate::national_household_allocation::{self, HouseholdBudgetKey, NationalHouseholdAllocation};
use crate::national_household_refinement;
use crate::national_household_time_allocation::{self, NationalHouseholdTimeAllocation};
use crate::national_households;
use crate::national_resident_allocation::{self, ResidentWorkplaceAllocation};
use crate::national_resident_workforce;
use crate::national_transport;
use crate::world_reference;
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::geography::CountyGeoid;
use babylon_material_circuit::{
    CommodityKind, EquipmentAssetId, FinalDemandPrincipalId, HouseholdNeedBasis,
};
use std::collections::{BTreeMap, BTreeSet};

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

/// Separate coordinates keep unlike accounting units from cancelling each other.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
struct HouseholdAccountingMargins {
    persons: u64,
    households: u64,
    employed: u64,
    reserve: u64,
    eligible: u64,
}
impl HouseholdAccountingMargins {
    fn accumulate(&mut self, other: Self) {
        self.persons = self.persons.checked_add(other.persons).expect("person sum");
        self.households = self
            .households
            .checked_add(other.households)
            .expect("household sum");
        self.employed = self
            .employed
            .checked_add(other.employed)
            .expect("employed sum");
        self.reserve = self
            .reserve
            .checked_add(other.reserve)
            .expect("reserve sum");
        self.eligible = self
            .eligible
            .checked_add(other.eligible)
            .expect("eligible sum");
    }
}

/// This second map groups immutable accounting results, never live owners.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
enum HouseholdAccountingBin {
    Detailed(FinalDemandPrincipalId),
    Background {
        state: [u8; 2],
        budget: HouseholdBudgetKey,
    },
}
#[derive(Clone, Copy)]
struct SourceHouseholdAccounting {
    principal: FinalDemandPrincipalId,
    bin: HouseholdAccountingBin,
    margins: HouseholdAccountingMargins,
}
fn source_household_accounting(
    policy: &NationalGamePolicy,
    budgets: &NationalHouseholdAllocation,
    time: &NationalHouseholdTimeAllocation,
) -> BTreeMap<(CountyGeoid, HouseholdBudgetKey), SourceHouseholdAccounting> {
    assert_eq!(
        budgets.counties().len(),
        3144,
        "full admitted domestic source roster"
    );
    let mut source = BTreeMap::new();
    let mut principals = BTreeSet::new();
    for county in budgets.counties() {
        let location = EconomicLocation::domestic_county(county.county()).expect("source county");
        let ages = time
            .county(county.county())
            .expect("independent source time");
        for budget in county.budgets() {
            let eligible = ages
                .budgets()
                .iter()
                .find(|row| row.key == budget.key)
                .expect("same independent source budget")
                .eligible_16_plus;
            let principal = national_economy::household_principal(location, budget.key);
            assert!(
                principals.insert(principal),
                "source principal appears once"
            );
            let bin = if policy.grain.protected_counties.contains(&county.county()) {
                HouseholdAccountingBin::Detailed(principal)
            } else {
                HouseholdAccountingBin::Background {
                    state: county.county().state_fips(),
                    budget: budget.key,
                }
            };
            assert!(source
                .insert(
                    (county.county(), budget.key),
                    SourceHouseholdAccounting {
                        principal,
                        bin,
                        margins: HouseholdAccountingMargins {
                            persons: budget.persons,
                            households: budget.households,
                            employed: budget.employed,
                            reserve: budget.reserve,
                            eligible,
                        },
                    },
                )
                .is_none());
        }
    }
    source
}

fn live_household_accounting(
    opening: &NationalOpening,
) -> BTreeMap<FinalDemandPrincipalId, HouseholdAccountingMargins> {
    let households: BTreeMap<_, _> = opening
        .opening
        .households
        .iter()
        .map(|row| (row.principal_id, row))
        .collect();
    assert_eq!(households.len(), opening.opening.households.len());
    let time: BTreeMap<_, _> = opening
        .opening
        .policies
        .household_time_policy
        .iter()
        .map(|row| (row.principal_id, row.eligible_persons))
        .collect();
    assert_eq!(
        time.len(),
        opening.opening.policies.household_time_policy.len()
    );
    assert_eq!(
        households.keys().collect::<Vec<_>>(),
        time.keys().collect::<Vec<_>>()
    );
    let mut live: BTreeMap<_, _> = households
        .iter()
        .map(|(principal, row)| {
            (
                *principal,
                HouseholdAccountingMargins {
                    persons: row.persons,
                    households: row.households,
                    eligible: time[principal],
                    ..HouseholdAccountingMargins::default()
                },
            )
        })
        .collect();
    for pool in &opening.opening.staffing {
        for row in &pool.members {
            let principal = row.member.household_id();
            assert_eq!(households[&principal].location, row.member.residence());
            live.get_mut(&principal)
                .expect("every actual worker has a household")
                .accumulate(HouseholdAccountingMargins {
                    employed: row.employed,
                    reserve: row.reserve,
                    ..HouseholdAccountingMargins::default()
                });
        }
    }
    let mut children = BTreeSet::new();
    assert!(
        !opening.aid.children.is_empty(),
        "protected split is exercised"
    );
    for child in &opening.aid.children {
        assert!(children.insert(child.principal), "restore each child once");
        assert_ne!(child.principal, child.parent);
        assert_eq!(households[&child.principal].location, child.location);
        assert_eq!(households[&child.parent].location, child.location);
        let actual = live
            .remove(&child.principal)
            .expect("actual protected child");
        assert_eq!(
            actual,
            HouseholdAccountingMargins {
                persons: child.persons,
                households: child.households,
                employed: child.employed,
                reserve: child.reserve,
                eligible: child.eligible,
            },
            "protected child identities and all five actual margins"
        );
        live.get_mut(&child.parent)
            .expect("actual protected parent")
            .accumulate(actual);
    }
    live.retain(|principal, _| {
        matches!(households[principal].location, EconomicLocation::County(_))
    });
    live
}

fn actual_household_accounting_bins(
    policy: &NationalGamePolicy,
    opening: &NationalOpening,
) -> BTreeMap<FinalDemandPrincipalId, HouseholdAccountingBin> {
    let background: BTreeMap<_, _> = opening
        .detail
        .background_households()
        .iter()
        .map(|row| (row.key.principal, row.key))
        .collect();
    assert_eq!(
        background.len(),
        opening.detail.background_households().len()
    );
    let children: BTreeSet<_> = opening
        .aid
        .children
        .iter()
        .map(|row| row.principal)
        .collect();
    let mut bins = BTreeMap::new();
    for household in &opening.opening.households {
        let EconomicLocation::County(county) = household.location else {
            continue;
        };
        if children.contains(&household.principal_id) {
            continue;
        }
        let bin = if policy.grain.protected_counties.contains(&county.geoid()) {
            HouseholdAccountingBin::Detailed(household.principal_id)
        } else {
            let key = background[&household.principal_id];
            assert_eq!(key.location, household.location, "actual retained location");
            HouseholdAccountingBin::Background {
                state: county.geoid().state_fips(),
                budget: key.budget,
            }
        };
        assert!(bins.insert(household.principal_id, bin).is_none());
    }
    bins
}

fn assert_household_accounting_composition(
    policy: &NationalGamePolicy,
    budgets: &NationalHouseholdAllocation,
    time: &NationalHouseholdTimeAllocation,
    opening: &NationalOpening,
) {
    // C is the independent source roster; q is the shipped household incidence.
    let source = source_household_accounting(policy, budgets, time);
    let incidence: BTreeMap<_, _> = opening
        .representation
        .household_incidence
        .iter()
        .map(|row| ((row.county, row.margins.key), row))
        .collect();
    assert_eq!(
        incidence.len(),
        opening.representation.household_incidence.len()
    );
    assert_eq!(
        source.keys().collect::<Vec<_>>(),
        incidence.keys().collect::<Vec<_>>()
    );
    let michigan_nonowner = HouseholdAccountingBin::Background {
        state: *b"26",
        budget: HouseholdBudgetKey::EarningNonowner,
    };
    let michigan_owner = HouseholdAccountingBin::Background {
        state: *b"26",
        budget: HouseholdBudgetKey::EarningOwner,
    };
    let mut direct = BTreeMap::<_, HouseholdAccountingMargins>::new();
    let mut expected_live = BTreeMap::<_, HouseholdAccountingMargins>::new();
    // r comes independently from actual live locations and retained budget keys.
    let regroup = actual_household_accounting_bins(policy, opening);
    let mut positive_sources = BTreeMap::<_, usize>::new();
    for (key, row) in &source {
        let assignment = incidence[key];
        assert_eq!(row.principal, assignment.source, "source identity joins q");
        if let HouseholdAccountingBin::Detailed(principal) = row.bin {
            assert_eq!(assignment.destination, principal, "detail is never pooled");
        }
        assert_eq!(regroup[&assignment.destination], row.bin, "g(c) = r(q(c))");
        direct.entry(row.bin).or_default().accumulate(row.margins);
        expected_live
            .entry(assignment.destination)
            .or_default()
            .accumulate(row.margins);
        if row.bin == michigan_nonowner && row.margins.persons > 0 {
            *positive_sources.entry(assignment.destination).or_default() += 1;
        }
    }
    assert!(
        positive_sources.len() >= 2,
        "r merges positive actual live principals"
    );
    assert!(
        positive_sources.values().any(|count| *count >= 2),
        "q merges positive sources"
    );
    assert!(direct.len() > 2);
    assert!(direct[&michigan_nonowner].persons > 0 && direct[&michigan_owner].persons > 0);
    for county in ["26163", "17031"] {
        let key = (
            CountyGeoid::try_from(county).expect("detailed county"),
            HouseholdBudgetKey::EarningNonowner,
        );
        assert!(direct.contains_key(&HouseholdAccountingBin::Detailed(source[&key].principal)));
    }
    // Read q_*v from actual ordinary consumers, restoring each protected child once.
    let live = live_household_accounting(opening);
    assert!(
        live.keys().eq(expected_live.keys()),
        "actual parent roster equals q destinations"
    );
    for (principal, expected) in &expected_live {
        assert_eq!(
            live[principal], *expected,
            "all five margins agree at actual q destination {principal:?}"
        );
    }
    let mut composed = BTreeMap::<_, HouseholdAccountingMargins>::new();
    let mut source_total = HouseholdAccountingMargins::default();
    let mut live_total = HouseholdAccountingMargins::default();
    for row in source.values() {
        source_total.accumulate(row.margins);
    }
    for (principal, margins) in live {
        composed
            .entry(regroup[&principal])
            .or_default()
            .accumulate(margins);
        live_total.accumulate(margins);
    }
    assert_eq!(
        composed, direct,
        "r_*(q_*v) = (r o q)_*v coordinate by coordinate"
    );
    assert_eq!(live_total, source_total, "global five-margin conservation");
}

#[test]
fn household_accounting_composes_and_complete_opening_ignores_source_traversal() {
    let policy = policy();
    let (builder, allocation, budgets, time) = prepared(&policy);
    let (reverse_builder, mut reversed, reverse_budgets, reverse_time) = prepared(&policy);
    assert!(
        allocation == reversed,
        "paired ordinary post-aid input capture"
    );
    assert_eq!(budgets, reverse_budgets);
    assert_eq!(time, reverse_time);
    assert!(allocation.counties.len() > 1 && allocation.workplaces.len() > 1);
    assert!(allocation
        .workplaces
        .iter()
        .any(|row| row.members.len() > 1));
    reversed.counties.reverse();
    reversed.workplaces.reverse();
    for workplace in &mut reversed.workplaces {
        workplace.members.reverse();
    }
    assert_ne!(
        allocation, reversed,
        "the mutable input traversal actually changes"
    );
    let forward = finish(builder, allocation, &budgets, &time);
    assert_household_accounting_composition(&policy, &budgets, &time, &forward);
    let backward = finish(reverse_builder, reversed, &reverse_budgets, &reverse_time);
    assert!(
        forward.representation == backward.representation,
        "complete typed witness"
    );
    assert!(
        forward.aid == backward.aid,
        "protected child and mandate capture"
    );
    assert!(
        forward.detail == backward.detail,
        "foreground and background partition"
    );
    assert!(
        forward.opening == backward.opening,
        "all actual opening consumer rows"
    );
    assert!(
        forward == backward,
        "complete NationalOpening without normalization"
    );
    let (catalog, staffing, bytes) = {
        let compiled = forward
            .opening
            .compile()
            .expect("forward ordinary compilation");
        let bytes = babylon_material_circuit::encode_material_circuit_state(
            &compiled.catalog,
            &compiled.state,
        )
        .expect("forward production canonical bytes");
        (compiled.catalog, compiled.staffing, bytes)
        // The first compiled state is dropped before constructing the second.
    };
    let compiled = backward
        .opening
        .compile()
        .expect("reversed ordinary compilation");
    assert!(
        catalog == compiled.catalog,
        "complete admitted material definitions"
    );
    assert!(
        staffing == compiled.staffing,
        "actual compiled staffing composition"
    );
    let reverse_bytes =
        babylon_material_circuit::encode_material_circuit_state(&compiled.catalog, &compiled.state)
            .expect("reversed production canonical bytes");
    assert!(
        bytes == reverse_bytes,
        "complete existing material codec bytes"
    );
}
