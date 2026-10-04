use super::*;
use crate::{
    national_counties::national_county_reference,
    national_households::{national_household_reference, HistoricalEarnings},
    national_resident_workforce::national_resident_workforce_reference,
};

#[test]
fn every_county_preserves_people_households_and_current_workforce_once() {
    let counties = national_county_reference().unwrap();
    let margins = national_household_reference().unwrap();
    let allocation = allocate_households(
        counties,
        margins,
        national_resident_workforce_reference().unwrap(),
        1_000,
    )
    .unwrap();
    assert_eq!(allocation.counties().len(), 3144);
    assert_eq!(
        allocation.household_source_sha256(),
        margins.artifact_sha256()
    );
    let mut totals = [0_u64; 5];
    let mut collective_count = 0;
    for row in allocation.counties() {
        let source = margins.county(row.county()).unwrap();
        let control = counties.county(row.county()).unwrap().residents();
        assert!((1..=5).contains(&row.budgets().len()));
        let sum = |value: fn(&HouseholdBudgetAllocation) -> u64| {
            row.budgets().iter().map(value).sum::<u64>()
        };
        assert_eq!(
            sum(|r| r.persons),
            control.population_persons.estimate.value().unwrap()
        );
        assert_eq!(
            sum(|r| r.households),
            control.households.estimate.value().unwrap()
        );
        assert_eq!(
            sum(|r| r.employed),
            control.civilian_employed_persons.estimate.value().unwrap()
        );
        assert_eq!(
            sum(|r| r.reserve),
            control
                .civilian_unemployed_persons
                .estimate
                .value()
                .unwrap()
        );
        for group in row.budgets() {
            assert!(group.persons > 0);
            assert!(group.employed + group.reserve <= group.persons);
            totals[0] += group.persons;
            totals[1] += group.households;
            totals[2] += group.employed;
            totals[3] += group.reserve;
            if matches!(
                group.key,
                HouseholdBudgetKey::NoEarnerNonowner | HouseholdBudgetKey::NoEarnerOwner
            ) {
                assert_eq!(group.employed, 0);
            }
            if group.key == HouseholdBudgetKey::CollectiveResidence {
                collective_count += 1;
                assert_eq!(group.households, 0);
                assert_eq!(
                    group.persons,
                    source.derived_group_quarters_persons().unwrap()
                );
                totals[4] += group.persons;
            }
        }
        assert_historical_margins(row, source);
    }
    assert_eq!(collective_count, 3099);
    assert_eq!(
        totals,
        [334_922_499, 129_227_496, 161_297_155, 8_902_365, 8_200_068]
    );
    assert_eq!(
        allocation,
        allocate_households(
            counties,
            margins,
            national_resident_workforce_reference().unwrap(),
            1_000
        )
        .unwrap()
    );
}

#[test]
fn current_workers_fit_without_rewriting_historical_household_margins() {
    let controls = HouseholdCountyControls {
        population: 20,
        household_persons: 16,
        with_historical_earnings_households: 2,
        without_historical_earnings_households: 6,
        employed: 12,
        reserve: 3,
        working_owners: 1,
    };
    let rows = allocate_county(controls, 1_000).unwrap();
    let earning = rows
        .iter()
        .find(|r| r.key == HouseholdBudgetKey::EarningNonowner)
        .unwrap();
    let no_earner = rows
        .iter()
        .find(|r| r.key == HouseholdBudgetKey::NoEarnerNonowner)
        .unwrap();
    let collective = rows
        .iter()
        .find(|r| r.key == HouseholdBudgetKey::CollectiveResidence)
        .unwrap();
    assert_eq!((earning.households, no_earner.households), (1, 5));
    assert_eq!(no_earner.employed, 0);
    assert!(no_earner.reserve > 0);
    assert!(earning.persons >= earning.employed);
    let owner = rows
        .iter()
        .find(|r| r.key == HouseholdBudgetKey::EarningOwner)
        .unwrap();
    assert!(owner.employed >= controls.working_owners);
    assert_eq!((collective.persons, collective.households), (4, 0));
    assert_eq!(rows.iter().map(|r| r.employed).sum::<u64>(), 12);
    assert_eq!(rows.iter().map(|r| r.reserve).sum::<u64>(), 3);
    assert_eq!(rows.iter().map(|r| r.persons).sum::<u64>(), 20);
}

#[test]
fn empty_source_groups_create_no_zero_person_budget_or_fake_household() {
    let rows = allocate_county(
        HouseholdCountyControls {
            population: 4,
            household_persons: 0,
            with_historical_earnings_households: 0,
            without_historical_earnings_households: 0,
            employed: 2,
            reserve: 1,
            working_owners: 0,
        },
        1_000,
    )
    .unwrap();
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0].key, HouseholdBudgetKey::CollectiveResidence);
    assert_eq!(
        (
            rows[0].persons,
            rows[0].households,
            rows[0].employed,
            rows[0].reserve
        ),
        (4, 0, 2, 1)
    );
    let rows = allocate_county(
        HouseholdCountyControls {
            population: 8,
            household_persons: 8,
            with_historical_earnings_households: 3,
            without_historical_earnings_households: 0,
            employed: 4,
            reserve: 1,
            working_owners: 0,
        },
        1_000,
    )
    .unwrap();
    assert_eq!(rows.len(), 2);
    assert!(rows.iter().all(|r| matches!(
        r.key,
        HouseholdBudgetKey::EarningNonowner | HouseholdBudgetKey::EarningOwner
    )));
}

#[test]
fn infeasible_designed_joint_refuses_without_reclassifying_source_households() {
    let controls = HouseholdCountyControls {
        population: 10,
        household_persons: 10,
        with_historical_earnings_households: 1,
        without_historical_earnings_households: 8,
        employed: 3,
        reserve: 0,
        working_owners: 0,
    };
    assert_eq!(
        allocate_county(controls, 1_000),
        Err(HouseholdAllocationError::DesignedAllocationInfeasible)
    );
    let invalid = HouseholdCountyControls {
        population: u64::MAX,
        household_persons: u64::MAX,
        with_historical_earnings_households: u64::MAX,
        without_historical_earnings_households: 1,
        employed: 0,
        reserve: 0,
        working_owners: 0,
    };
    assert_eq!(
        allocate_county(invalid, 1_000),
        Err(HouseholdAllocationError::Arithmetic)
    );
}

#[test]
fn sparse_workplace_members_pay_the_exact_allocated_resident_budgets() {
    use crate::{
        national_cohorts::national_cohort_reference,
        national_economy::{household_principal, NationalGamePolicy},
        national_resident_allocation::allocate_home_county,
    };
    use babylon_kernel::economic_location::EconomicLocation;
    use std::collections::{BTreeMap, BTreeSet};

    let counties = national_county_reference().unwrap();
    let classes = national_resident_workforce_reference().unwrap();
    let household_allocation = allocate_households(
        counties,
        national_household_reference().unwrap(),
        classes,
        1_000,
    )
    .unwrap();
    let policy = NationalGamePolicy::parse(include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../content/scenarios/national/defines.toml"
    )))
    .unwrap();
    let workplaces = allocate_home_county(
        counties,
        national_cohort_reference().unwrap(),
        classes,
        &household_allocation,
        &policy,
    )
    .unwrap();
    let mut actual = BTreeMap::new();
    let mut identities = BTreeSet::new();
    let mut divided_workplaces = 0;
    for workplace in workplaces.workplaces {
        let mut recipients = BTreeSet::new();
        for assigned in workplace.members {
            let row = assigned.seed;
            assert_eq!(row.member.residence(), workplace.target.location);
            assert_eq!(row.employed + row.reserve, row.member.labor_force());
            assert!(row.member.labor_force() > 0);
            assert!(identities.insert(row.member.member_id()));
            recipients.insert(row.member.household_id());
            let totals = actual
                .entry((workplace.target.location, row.member.household_id()))
                .or_insert((0_u64, 0_u64));
            totals.0 += row.employed;
            totals.1 += row.reserve;
        }
        divided_workplaces += usize::from(recipients.len() > 1);
    }
    assert!(divided_workplaces > 0);
    let mut aggregate = (0_u64, 0_u64);
    for county in household_allocation.counties() {
        let location = EconomicLocation::domestic_county(county.county()).unwrap();
        for budget in county.budgets() {
            let principal = household_principal(location, budget.key);
            let workforce = actual.remove(&(location, principal)).unwrap_or_default();
            assert_eq!(workforce, (budget.employed, budget.reserve));
            assert!(workforce.0 + workforce.1 <= budget.persons);
            aggregate.0 += workforce.0;
            aggregate.1 += workforce.1;
        }
    }
    assert!(actual.is_empty());
    assert_eq!(aggregate, (161_297_155, 8_902_365));
}

fn assert_historical_margins(
    row: &CountyHouseholdAllocation,
    source: &crate::national_households::CountyHouseholdMargins,
) {
    for (source_kind, keys) in [
        (
            HistoricalEarnings::WithEarnings,
            [
                HouseholdBudgetKey::EarningNonowner,
                HouseholdBudgetKey::EarningOwner,
            ],
        ),
        (
            HistoricalEarnings::NoEarnings,
            [
                HouseholdBudgetKey::NoEarnerNonowner,
                HouseholdBudgetKey::NoEarnerOwner,
            ],
        ),
    ] {
        let observed = source
            .historical_earnings_households(source_kind)
            .estimate
            .value()
            .unwrap();
        assert_eq!(
            row.budgets()
                .iter()
                .filter(|g| keys.contains(&g.key))
                .map(|g| g.households)
                .sum::<u64>(),
            observed
        );
        let owner = row.budgets().iter().find(|g| g.key == keys[1]).unwrap();
        assert_eq!(owner.households, observed.div_ceil(10));
    }
}
