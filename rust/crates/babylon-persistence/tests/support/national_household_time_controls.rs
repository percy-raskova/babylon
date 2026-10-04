//! Source age controls reach the admitted material account, not only authoring text.
use super::*;
use babylon_material_circuit::{CircuitAccounting, HouseholdNeedBasis, HouseholdTimeAccounting};

pub(super) fn assert_time(opening: &EconomicOpening, policy: &NationalGamePolicy) {
    let compiled = opening.compile().unwrap();
    let CircuitAccounting::Monetary(economy) = &compiled.state.accounting else {
        panic!("national play needs funded household accounts");
    };
    let HouseholdTimeAccounting::Modeled(book) = &economy.household_time else {
        panic!("captured national time controls must reach the material engine");
    };
    assert!(book.receipts.is_empty() && book.contributions.is_empty());
    assert_eq!(book.policies.len(), opening.households.len());
    assert!(book
        .policies
        .windows(2)
        .all(|pair| pair[0].principal_id < pair[1].principal_id));
    let residents: BTreeMap<_, _> = opening
        .households
        .iter()
        .map(|household| (household.principal_id, household))
        .collect();
    let mut workforce = BTreeMap::<_, u64>::new();
    for workplace in &opening.staffing {
        for member in &workplace.members {
            let count = workforce.entry(member.member.household_id()).or_default();
            *count = count.checked_add(member.member.labor_force()).unwrap();
        }
    }
    let mut domestic_eligible = 0_u64;
    let mut domestic_locations = BTreeSet::new();
    let mut external = 0;
    for time in &book.policies {
        let household = residents[&time.principal_id];
        let counted_force = workforce
            .get(&time.principal_id)
            .copied()
            .unwrap_or_default();
        assert_household_time(time, household, counted_force, policy);
        if matches!(household.location, EconomicLocation::County(_)) {
            domestic_eligible = domestic_eligible
                .checked_add(time.eligible_persons)
                .unwrap();
            domestic_locations.insert(household.location);
        } else {
            external += 1;
            let designed = u64::try_from(
                u128::from(household.persons)
                    * u128::from(policy.household_time.external_eligible_persons_bps)
                    / 10_000,
            )
            .unwrap();
            assert_eq!(time.eligible_persons, designed.max(counted_force));
        }
    }
    assert_eq!(domestic_eligible, 270_181_636);
    assert_eq!(domestic_locations.len(), 3_144);
    assert_eq!(external, 18);
}

fn assert_household_time(
    time: &babylon_material_circuit::HouseholdTimePolicy,
    household: &babylon_persistence::economic_catalog::EconomicHouseholdSeed,
    counted_force: u64,
    policy: &NationalGamePolicy,
) {
    assert!(time.eligible_persons <= household.persons);
    assert!(counted_force <= time.eligible_persons);
    assert_eq!(
        time.hours_per_eligible_person,
        policy.household_time.hours_per_eligible_person
    );
    assert!(
        counted_force
            .checked_mul(policy.work_hours_per_person)
            .unwrap()
            <= time
                .eligible_persons
                .checked_mul(time.hours_per_eligible_person)
                .unwrap()
    );
    let collective = household.households == 0;
    assert_eq!(
        time.protected.basis,
        if collective {
            HouseholdNeedBasis::Persons
        } else {
            HouseholdNeedBasis::Households
        }
    );
    assert_eq!(time.routine_provisioning.basis, time.protected.basis);
    assert_eq!(
        time.protected.hours_per_basis,
        if collective {
            32
        } else {
            policy.household_time.ordinary_protected_hours_per_household
        }
    );
    assert_eq!(
        time.routine_provisioning.hours_per_basis,
        if collective {
            64
        } else {
            policy
                .household_time
                .ordinary_provisioning_hours_per_household
        }
    );
    let food = &policy.commodities["food"];
    assert_eq!(time.unmet_burdens.len(), 1);
    assert_eq!(
        (time.unmet_burdens[0].good_id, time.unmet_burdens[0].unit_id),
        (food.good_id, food.unit_id)
    );
    assert_eq!(time.unmet_burdens[0].hours_per_unmet_unit, 20);
}
