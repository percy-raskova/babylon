use babylon_persistence::{
    national_counties::national_county_reference,
    national_household_allocation::allocate_households,
    national_household_refinement::refine_households,
    national_household_time_allocation::allocate_household_time,
    national_households::national_household_reference,
    national_resident_workforce::national_resident_workforce_reference,
};

#[test]
fn empty_refinements_preserve_every_source_budget_and_identity() {
    let counties = national_county_reference().unwrap();
    let households = allocate_households(
        counties,
        national_household_reference().unwrap(),
        national_resident_workforce_reference().unwrap(),
        1000,
    )
    .unwrap();
    let time = allocate_household_time(counties, &households).unwrap();
    let leaves = refine_households(&households, &time, &[]).unwrap();
    assert_eq!(
        leaves.leaves().len(),
        households
            .counties()
            .iter()
            .map(|row| row.budgets().len())
            .sum::<usize>()
    );
    for county in households.counties() {
        for parent in county.budgets() {
            let rows = leaves.parent_leaves(county.county(), parent.key);
            assert_eq!(rows.len(), 1);
            assert_eq!(rows[0].child_tag, None);
            assert_eq!(rows[0].margins.persons, parent.persons);
            assert_eq!(rows[0].margins.households, parent.households);
            assert_eq!(rows[0].margins.employed, parent.employed);
            assert_eq!(rows[0].margins.reserve, parent.reserve);
        }
    }
}

#[test]
fn designed_wayne_child_preserves_source_margins_and_sparse_workplace_mode_totals() {
    use babylon_persistence::{
        national_cohorts::national_cohort_reference,
        national_economy::NationalGamePolicy,
        national_household_allocation::HouseholdBudgetKey,
        national_household_refinement::{
            HouseholdLeafMargins, HouseholdRefinementError, HouseholdRefinementSpec,
        },
        national_resident_allocation::allocate_home_county,
    };
    let counties = national_county_reference().unwrap();
    let workforce = national_resident_workforce_reference().unwrap();
    let budgets = allocate_households(
        counties,
        national_household_reference().unwrap(),
        workforce,
        1000,
    )
    .unwrap();
    let time = allocate_household_time(counties, &budgets).unwrap();
    let county = "26163".parse().unwrap();
    let spec = HouseholdRefinementSpec {
        county,
        parent_key: HouseholdBudgetKey::EarningNonowner,
        child_tag: [1; 32],
        margins: HouseholdLeafMargins {
            persons: 3,
            households: 1,
            employed: 1,
            reserve: 1,
            eligible_16_plus: 2,
            armed_forces: 0,
            inactive: 0,
            under_16: 1,
        },
    };
    let leaves = refine_households(&budgets, &time, std::slice::from_ref(&spec)).unwrap();
    let empty = refine_households(&budgets, &time, &[]).unwrap();
    assert_eq!(leaves.leaves().len(), empty.leaves().len() + 1);
    assert_eq!(
        refine_households(&budgets, &time, &[spec.clone(), spec.clone()]),
        Err(HouseholdRefinementError::Duplicate)
    );
    let mut zero = spec.clone();
    zero.child_tag = [0; 32];
    assert_eq!(
        refine_households(&budgets, &time, &[zero]),
        Err(HouseholdRefinementError::Identity)
    );
    let mut owner = spec.clone();
    owner.parent_key = HouseholdBudgetKey::EarningOwner;
    assert_eq!(
        refine_households(&budgets, &time, &[owner]),
        Err(HouseholdRefinementError::ParentScope)
    );
    let mut unknown = spec.clone();
    unknown.county = "72001".parse().unwrap();
    assert_eq!(
        refine_households(&budgets, &time, &[unknown]),
        Err(HouseholdRefinementError::SourceRoster)
    );
    let policy = NationalGamePolicy::parse(include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../content/scenarios/national/defines.toml"
    )))
    .unwrap();
    let base = allocate_home_county(
        counties,
        national_cohort_reference().unwrap(),
        workforce,
        &budgets,
        &empty,
        &policy,
    )
    .unwrap();
    let refined = allocate_home_county(
        counties,
        national_cohort_reference().unwrap(),
        workforce,
        &budgets,
        &leaves,
        &policy,
    )
    .unwrap();
    let other_budgets = allocate_households(
        counties,
        national_household_reference().unwrap(),
        workforce,
        2000,
    )
    .unwrap();
    let mut other_policy = policy.clone();
    other_policy.households.private_owner_households_bps = 2000;
    assert_eq!(
        allocate_home_county(
            counties,
            national_cohort_reference().unwrap(),
            workforce,
            &other_budgets,
            &leaves,
            &other_policy
        ),
        Err(babylon_persistence::national_resident_allocation::AllocationError::SourceScope)
    );
    let child = leaves.parent_leaves(county, spec.parent_key)[0].principal_id;
    let mut child_totals = (0, 0);
    for (before, after) in base.workplaces.iter().zip(&refined.workplaces) {
        assert_eq!(before.target, after.target);
        for mode in [
            babylon_persistence::national_resident_allocation::ResidentAttendanceMode::Employee,
            babylon_persistence::national_resident_allocation::ResidentAttendanceMode::WorkingOwner,
            babylon_persistence::national_resident_allocation::ResidentAttendanceMode::UnpaidFamily,
        ] {
            let totals=|rows:&[babylon_persistence::national_resident_allocation::AssignedResidentMember]| rows.iter()
                .filter(|row|row.mode==mode).fold((0,0),|(e,r),row|(e+row.seed.employed,r+row.seed.reserve));
            assert_eq!(totals(&before.members), totals(&after.members));
        }
        for row in &after.members {
            assert!(row.seed.employed + row.seed.reserve > 0);
            if row.seed.member.household_id() == child {
                child_totals.0 += row.seed.employed;
                child_totals.1 += row.seed.reserve;
            }
        }
    }
    assert_eq!(child_totals, (1, 1));
    let before_count = base
        .workplaces
        .iter()
        .map(|row| row.members.len())
        .sum::<usize>();
    let after_count = refined
        .workplaces
        .iter()
        .map(|row| row.members.len())
        .sum::<usize>();
    assert!(after_count <= before_count + 2);
}
