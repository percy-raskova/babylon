use super::*;
use crate::{
    national_counties::{acs_cell, national_county_reference, ObservationStatus},
    national_household_allocation::{HouseholdBudgetAllocation, HouseholdBudgetKey},
};

fn county() -> CountyGeoid {
    CountyGeoid::try_from("26001").unwrap()
}

fn budget(
    key: HouseholdBudgetKey,
    persons: u64,
    households: u64,
    employed: u64,
    reserve: u64,
) -> HouseholdBudgetAllocation {
    HouseholdBudgetAllocation {
        key,
        persons,
        households,
        employed,
        reserve,
    }
}

fn values(row: &HouseholdTimeAllocation) -> [u64; 4] {
    [
        row.eligible_16_plus,
        row.armed_forces,
        row.inactive,
        row.under_16,
    ]
}

#[test]
fn inactive_residents_remain_eligible_without_any_workforce_member() {
    let controls = CountyTimeControls {
        population: 8,
        households: 3,
        eligible_16_plus: 5,
        employed: 0,
        reserve: 0,
        armed_forces: 1,
        inactive: 4,
    };
    let budgets = [
        budget(HouseholdBudgetKey::NoEarnerNonowner, 6, 2, 0, 0),
        budget(HouseholdBudgetKey::NoEarnerOwner, 2, 1, 0, 0),
    ];
    let result = allocate_county(county(), controls, &budgets).unwrap();
    assert_eq!(
        result.budgets().iter().map(values).collect::<Vec<_>>(),
        [[4, 1, 3, 2], [1, 0, 1, 1]]
    );
    assert!(budgets
        .iter()
        .all(|row| row.employed == 0 && row.reserve == 0));
}

#[test]
fn zero_eligible_people_keep_all_persons_without_inventing_time_or_workers() {
    let controls = CountyTimeControls {
        population: 4,
        households: 2,
        eligible_16_plus: 0,
        employed: 0,
        reserve: 0,
        armed_forces: 0,
        inactive: 0,
    };
    let result = allocate_county(
        county(),
        controls,
        &[budget(HouseholdBudgetKey::NoEarnerNonowner, 4, 2, 0, 0)],
    )
    .unwrap();
    assert_eq!(result.budgets().len(), 1);
    assert_eq!(values(&result.budgets()[0]), [0, 0, 0, 4]);
}

fn mixed_controls() -> CountyTimeControls {
    CountyTimeControls {
        population: 12,
        households: 4,
        eligible_16_plus: 9,
        employed: 4,
        reserve: 1,
        armed_forces: 1,
        inactive: 3,
    }
}

fn mixed_budgets() -> Vec<HouseholdBudgetAllocation> {
    vec![
        budget(HouseholdBudgetKey::EarningNonowner, 5, 2, 4, 0),
        budget(HouseholdBudgetKey::NoEarnerNonowner, 5, 2, 0, 1),
        budget(HouseholdBudgetKey::CollectiveResidence, 2, 0, 0, 0),
    ]
}

#[test]
fn remaining_person_capacities_bound_each_allocation_including_sparse_collective_residence() {
    let budgets = mixed_budgets();
    let result = allocate_county(county(), mixed_controls(), &budgets).unwrap();
    assert_eq!(
        result.budgets().iter().map(values).collect::<Vec<_>>(),
        [[5, 0, 1, 0], [3, 1, 1, 2], [1, 0, 1, 1],]
    );
    assert_eq!(
        result.budgets()[2].key,
        HouseholdBudgetKey::CollectiveResidence
    );
    assert_eq!(budgets[2].households, 0);
}

#[test]
fn equal_remainders_follow_budget_identity_not_caller_order() {
    let controls = CountyTimeControls {
        population: 3,
        households: 3,
        eligible_16_plus: 2,
        employed: 0,
        reserve: 0,
        armed_forces: 1,
        inactive: 1,
    };
    let budgets = [
        budget(HouseholdBudgetKey::EarningNonowner, 1, 1, 0, 0),
        budget(HouseholdBudgetKey::NoEarnerNonowner, 1, 1, 0, 0),
        budget(HouseholdBudgetKey::NoEarnerOwner, 1, 1, 0, 0),
    ];
    let result = allocate_county(county(), controls, &budgets).unwrap();
    assert_eq!(
        result.budgets().iter().map(values).collect::<Vec<_>>(),
        [[1, 1, 0, 0], [1, 0, 1, 0], [0, 0, 0, 1],]
    );
    let mut reversed = budgets;
    reversed.reverse();
    assert_eq!(
        result,
        allocate_county(county(), controls, &reversed).unwrap()
    );
}

#[test]
fn impossible_county_and_budget_margins_refuse_instead_of_moving_workers() {
    let controls = mixed_controls();
    let mut invalid = controls;
    invalid.eligible_16_plus = 13;
    assert!(matches!(
        allocate_county(county(), invalid, &mixed_budgets()),
        Err(HouseholdTimeAllocationError::CountyMargin { .. })
    ));
    invalid = controls;
    invalid.inactive += 1;
    assert!(matches!(
        allocate_county(county(), invalid, &mixed_budgets()),
        Err(HouseholdTimeAllocationError::CountyMargin { .. })
    ));
    let mut rows = mixed_budgets();
    rows[0].employed = 6;
    assert!(matches!(
        allocate_county(county(), controls, &rows),
        Err(HouseholdTimeAllocationError::BudgetMargin { .. })
    ));
    rows = mixed_budgets();
    rows[0].employed -= 1;
    assert!(matches!(
        allocate_county(county(), controls, &rows),
        Err(HouseholdTimeAllocationError::BudgetMargin { .. })
    ));
    rows = mixed_budgets();
    rows[0].households -= 1;
    assert!(matches!(
        allocate_county(county(), controls, &rows),
        Err(HouseholdTimeAllocationError::BudgetMargin { .. })
    ));
}

#[test]
fn duplicate_or_external_budget_identity_cannot_absorb_domestic_people() {
    let mut rows = mixed_budgets();
    rows[1].key = rows[0].key;
    assert!(matches!(
        allocate_county(county(), mixed_controls(), &rows),
        Err(HouseholdTimeAllocationError::BudgetIdentity { .. })
    ));
    rows = mixed_budgets();
    rows[2].key = HouseholdBudgetKey::PooledExternal;
    assert!(matches!(
        allocate_county(county(), mixed_controls(), &rows),
        Err(HouseholdTimeAllocationError::BudgetIdentity { .. })
    ));
}

#[test]
fn unavailable_estimate_retains_exact_sentinel_and_status_in_the_refusal() {
    for (raw, label, status) in [
        ("", "missing", ObservationStatus::Missing),
        ("null", "missing", ObservationStatus::Missing),
        (
            "-666666666",
            "estimate_not_computable",
            ObservationStatus::EstimateNotComputable,
        ),
        (
            "-999999999",
            "insufficient_sample_cases",
            ObservationStatus::InsufficientSampleCases,
        ),
        (
            "-888888888",
            "not_applicable_or_available",
            ObservationStatus::NotApplicableOrAvailable,
        ),
    ] {
        let cell = acs_cell(&["", raw, label]).unwrap();
        assert_eq!(
            observation(county(), HouseholdTimeMeasure::Eligible16Plus, &cell),
            Err(HouseholdTimeAllocationError::UnavailableObservation {
                county: county(),
                measure: HouseholdTimeMeasure::Eligible16Plus,
                status,
                raw: raw.to_owned(),
            })
        );
    }
    let zero = acs_cell(&["0", "0", "published"]).unwrap();
    assert_eq!(
        observation(county(), HouseholdTimeMeasure::Eligible16Plus, &zero),
        Ok(0)
    );
}

#[test]
fn omitted_duplicated_or_dependency_county_refuses_the_exact_roster_join() {
    let source = national_county_reference().unwrap();
    let keys: Vec<_> = source
        .counties()
        .iter()
        .map(crate::national_counties::CountyReference::geoid)
        .collect();
    assert_eq!(validate_roster(source, keys.iter().copied()), Ok(()));
    assert_eq!(
        validate_roster(source, keys[1..].iter().copied()),
        Err(HouseholdTimeAllocationError::CountyRoster)
    );
    let mut duplicated = keys.clone();
    duplicated[1] = duplicated[0];
    assert_eq!(
        validate_roster(source, duplicated.into_iter()),
        Err(HouseholdTimeAllocationError::CountyRoster)
    );
    let mut foreign = keys;
    foreign[0] = CountyGeoid::try_from("72001").unwrap();
    assert_eq!(
        validate_roster(source, foreign.into_iter()),
        Err(HouseholdTimeAllocationError::CountyRoster)
    );
}

#[test]
fn source_and_budget_arithmetic_cannot_wrap_into_a_feasible_margin() {
    let controls = CountyTimeControls {
        population: u64::MAX,
        households: 1,
        eligible_16_plus: u64::MAX,
        employed: u64::MAX,
        reserve: 1,
        armed_forces: 0,
        inactive: 0,
    };
    let rows = [budget(
        HouseholdBudgetKey::EarningNonowner,
        u64::MAX,
        1,
        u64::MAX,
        1,
    )];
    assert_eq!(
        allocate_county(county(), controls, &rows),
        Err(HouseholdTimeAllocationError::Arithmetic { county: county() })
    );
}

#[test]
fn allocation_provenance_refuses_different_county_or_workforce_capture() {
    let counties = national_county_reference().unwrap();
    let households = crate::national_household_allocation::allocate_households(
        counties,
        crate::national_households::national_household_reference().unwrap(),
        crate::national_resident_workforce::national_resident_workforce_reference().unwrap(),
        1_000,
    )
    .unwrap();
    for change_county in [true, false] {
        let mut wrong = households.clone();
        if change_county {
            wrong.county_source_sha256[0] ^= 1;
        } else {
            wrong.classes_source_sha256[0] ^= 1;
        }
        assert_eq!(
            allocate_household_time(counties, &wrong),
            Err(HouseholdTimeAllocationError::SourceDigest)
        );
    }
}
