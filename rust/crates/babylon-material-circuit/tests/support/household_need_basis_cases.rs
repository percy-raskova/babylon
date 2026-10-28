//! A home and a person are distinct requirement bases, not interchangeable counts.
use crate::money;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::HouseholdNeedBasis;
use babylon_material_circuit::MaterialCatalog;

#[test]
fn resident_and_household_bases_drive_real_consumption_without_changing_counts() {
    for (basis, expected) in [
        (HouseholdNeedBasis::Persons, 8),
        (HouseholdNeedBasis::Households, 4),
    ] {
        let (catalog, mut state) = crate::opening();
        let mut catalog = catalog.into_definition();
        let recurring = crate::recurring_mut(&mut state);
        recurring.household_purchases[0].enabled = false;
        catalog.household_needs[0].basis = basis;
        catalog.household_needs[0].units_per_basis = 2;
        let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
        let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
            .expect("the canonical material state encodes");
        let restored = babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
            .expect("the canonical material bytes decode");
        let close = babylon_material_circuit::advance_material_circuit(&catalog, &restored)
            .expect("the authored material state advances one period");
        assert_eq!(close.household_consumption[0].required_quantity, expected);
        assert_eq!(close.household_consumption[0].consumed_quantity, expected);
        let CircuitAccounting::Monetary(economy) = &close.state.accounting else {
            panic!("the close lost its monetary authority");
        };
        let cohort = &economy
            .recurring
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .households[0];
        assert_eq!((cohort.persons, cohort.households), (4, 2));
        assert_eq!(
            economy
                .book
                .total_cash_and_reserves()
                .expect("the fixture book totals without overflow"),
            money(24)
        );
    }
}
