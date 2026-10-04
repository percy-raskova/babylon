use babylon_persistence::{
    national_counties::national_county_reference,
    national_household_allocation::{
        allocate_households, HouseholdBudgetAllocation, HouseholdBudgetKey,
    },
    national_household_time_allocation::{allocate_household_time, HouseholdTimeAllocation},
    national_households::national_household_reference,
    national_resident_workforce::national_resident_workforce_reference,
};

#[test]
fn all_counties_account_for_eligible_nonworkers_without_creating_workers() {
    let counties = national_county_reference().unwrap();
    let household_source = national_household_reference().unwrap();
    let workforce_source = national_resident_workforce_reference().unwrap();
    let households =
        allocate_households(counties, household_source, workforce_source, 1_000).unwrap();
    let before = households.clone();
    let time = allocate_household_time(counties, &households).unwrap();
    assert_eq!(time.counties().len(), 3_144);
    assert_eq!(time.county_source_sha256(), counties.artifact_sha256());
    assert_eq!(
        time.household_source_sha256(),
        household_source.artifact_sha256()
    );
    assert_eq!(
        time.resident_workforce_source_sha256(),
        workforce_source.artifact_sha256()
    );
    let mut totals = [0_u64; 4];
    let mut collective_count = 0;
    let mut eligible_without_workers = 0;
    for county in time.counties() {
        let controls = households.county(county.county()).unwrap();
        let source = counties.county(county.county()).unwrap().residents();
        assert_eq!(time.county(county.county()).unwrap(), county);
        assert_eq!(county.budgets().len(), controls.budgets().len());
        let mut county_totals = [0_u64; 4];
        for (row, budget) in county.budgets().iter().zip(controls.budgets()) {
            assert_eq!(row.key, budget.key);
            let force = budget.employed + budget.reserve;
            assert!(force <= row.eligible_16_plus && row.eligible_16_plus <= budget.persons);
            assert_eq!(
                row.eligible_16_plus,
                force + row.armed_forces + row.inactive
            );
            assert_eq!(budget.persons, row.eligible_16_plus + row.under_16);
            let (collective, nonworkers) = classify_budget(row, budget);
            collective_count += collective;
            eligible_without_workers += nonworkers;
            for (total, value) in county_totals.iter_mut().zip([
                row.eligible_16_plus,
                row.armed_forces,
                row.inactive,
                row.under_16,
            ]) {
                *total += value;
            }
        }
        assert_eq!(
            county_totals[0],
            source.age_16_plus_persons.estimate.value().unwrap()
        );
        assert_eq!(
            county_totals[1],
            source.armed_forces_persons.estimate.value().unwrap()
        );
        assert_eq!(
            county_totals[2],
            source.not_in_labor_force_persons.estimate.value().unwrap()
        );
        assert_eq!(
            county_totals[0] + county_totals[3],
            source.population_persons.estimate.value().unwrap()
        );
        for (total, value) in totals.iter_mut().zip(county_totals) {
            *total += value;
        }
    }
    // Independently summed from the pinned county CSV, including every admitted GEOID.
    assert_eq!(totals, [270_181_636, 1_293_765, 98_688_351, 64_740_863]);
    assert_eq!(collective_count, 3_099);
    assert!(eligible_without_workers > 0);
    assert_eq!(households, before);
    assert_eq!(
        time,
        allocate_household_time(counties, &households).unwrap()
    );
}

fn classify_budget(
    row: &HouseholdTimeAllocation,
    budget: &HouseholdBudgetAllocation,
) -> (usize, usize) {
    let collective = usize::from(row.key == HouseholdBudgetKey::CollectiveResidence);
    if collective == 1 {
        assert_eq!(budget.households, 0);
    }
    let nonworkers = usize::from(budget.employed + budget.reserve == 0 && row.eligible_16_plus > 0);
    (collective, nonworkers)
}
