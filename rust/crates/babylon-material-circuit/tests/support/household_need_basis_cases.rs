//! A home and a person are distinct requirement bases, not interchangeable counts.
use super::*;

#[test]
fn resident_and_household_bases_drive_real_consumption_without_changing_counts() {
    for (basis, expected) in [
        (HouseholdNeedBasis::Persons, 8),
        (HouseholdNeedBasis::Households, 4),
    ] {
        let mut state = opening();
        let recurring = recurring_mut(&mut state);
        recurring.household_needs[0].basis = basis;
        recurring.household_needs[0].units_per_basis = 2;
        recurring.household_purchases[0].enabled = false;
        let bytes = encode_material_circuit_state(&state).unwrap();
        let restored = decode_material_circuit_state(&bytes).unwrap();
        let close = advance_material_circuit(&restored).unwrap();
        assert_eq!(close.household_consumption[0].required_quantity, expected);
        assert_eq!(close.household_consumption[0].consumed_quantity, expected);
        let CircuitAccounting::Monetary(economy) = &close.state.accounting else {
            panic!("the close lost its monetary authority");
        };
        let cohort = &economy.recurring.as_ref().unwrap().households[0];
        assert_eq!((cohort.persons, cohort.households), (4, 2));
        assert_eq!(economy.book.total_cash_and_reserves().unwrap(), money(24));
    }
}
