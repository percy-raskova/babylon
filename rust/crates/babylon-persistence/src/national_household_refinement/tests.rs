use super::refine;
use super::refine::{HouseholdLeafMargins, HouseholdRefinementError, HouseholdRefinementSpec};
use crate::national_economy::household_principal;
use crate::national_household_allocation::HouseholdBudgetKey;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::geography::CountyGeoid;
fn county() -> CountyGeoid {
    CountyGeoid::try_from("26163").expect("the fixture value fits the target range")
}
fn margins() -> HouseholdLeafMargins {
    HouseholdLeafMargins {
        persons: 20,
        households: 8,
        employed: 8,
        reserve: 2,
        eligible_16_plus: 16,
        armed_forces: 1,
        inactive: 5,
        under_16: 4,
    }
}
fn child(tag: u8) -> HouseholdRefinementSpec {
    HouseholdRefinementSpec {
        county: county(),
        parent_key: HouseholdBudgetKey::EarningNonowner,
        child_tag: [tag; 32],
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
    }
}
#[test]
fn exact_eight_margins_and_identity_survive_reordered_children_and_count_changes() {
    let first = child(1);
    let second = child(2);
    let forward =
        refine::refine_parent(county(), first.parent_key, margins(), vec![&first, &second])
            .expect("the fixture call `refine_parent` succeeds for the authored inputs");
    let backward =
        refine::refine_parent(county(), first.parent_key, margins(), vec![&second, &first])
            .expect("the fixture call `refine_parent` succeeds for the authored inputs");
    assert_eq!(forward, backward);
    for index in 0..8 {
        assert_eq!(
            forward
                .iter()
                .map(|row| row.margins.values()[index])
                .sum::<u64>(),
            margins().values()[index]
        );
    }
    let mut changed = first.clone();
    changed.margins.persons += 1;
    changed.margins.under_16 += 1;
    let altered = refine::refine_parent(
        county(),
        first.parent_key,
        margins(),
        vec![&changed, &second],
    )
    .expect("the fixture call `refine_parent` succeeds for the authored inputs");
    assert_eq!(
        forward
            .iter()
            .map(|row| row.principal_id)
            .collect::<Vec<_>>(),
        altered
            .iter()
            .map(|row| row.principal_id)
            .collect::<Vec<_>>()
    );
    assert_eq!(
        forward
            .last()
            .expect("the fixture sequence is non-empty")
            .principal_id,
        household_principal(
            EconomicLocation::domestic_county(county())
                .expect("the fixture geoid names a domestic county"),
            first.parent_key
        )
    );
}
#[test]
fn inconsistent_child_excess_and_empty_ordinary_residual_are_refused() {
    let mut invalid = child(1).margins;
    invalid.eligible_16_plus = 0;
    assert_eq!(
        invalid.validate(false),
        Err(HouseholdRefinementError::Margin)
    );
    invalid = margins();
    invalid.employed = u64::MAX;
    assert_eq!(
        invalid.validate(false),
        Err(HouseholdRefinementError::Margin)
    );
    let mut excessive = child(1);
    excessive.margins = margins();
    excessive.margins.persons += 1;
    excessive.margins.under_16 += 1;
    assert_eq!(
        refine::refine_parent(county(), excessive.parent_key, margins(), vec![&excessive]),
        Err(HouseholdRefinementError::Excess)
    );
    excessive.margins = margins();
    assert_eq!(
        refine::refine_parent(county(), excessive.parent_key, margins(), vec![&excessive]),
        Err(HouseholdRefinementError::Margin)
    );
}
#[test]
fn collective_residence_keeps_positive_people_without_fabricating_households() {
    let mut collective = margins();
    collective.households = 0;
    let rows = refine::refine_parent(
        county(),
        HouseholdBudgetKey::CollectiveResidence,
        collective,
        vec![],
    )
    .expect("the fixture call `refine_parent` succeeds for the authored inputs");
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0].margins, collective);
    assert_eq!(
        collective.validate(false),
        Err(HouseholdRefinementError::Margin)
    );
}
