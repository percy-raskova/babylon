//! Shared paid controls must admit real market locations without fictional GEOIDs.

use super::*;
use babylon_kernel::{
    economic_location::{EconomicLocation, ForeignCounterpart, UsDependency},
    geography::CountyGeoid,
};

fn place(state: &mut MaterialCircuitState, location: EconomicLocation) {
    for row in &mut state.merchants {
        row.location = location;
    }
    for row in &mut state.final_demand_principals {
        row.location = location;
    }
}

#[test]
fn national_foreign_and_dependency_locations_use_the_same_paid_consumption_close() {
    let locations = ["01001", "02013", "15005", "11001"]
        .into_iter()
        .map(|key| EconomicLocation::domestic_county(CountyGeoid::try_from(key).unwrap()).unwrap())
        .chain(ForeignCounterpart::ALL.map(EconomicLocation::Foreign))
        .chain(UsDependency::ALL.map(EconomicLocation::Dependency));
    for location in locations {
        let mut state = opening();
        place(&mut state, location);
        let encoded = encode_material_circuit_state(&state).unwrap();
        let restored = decode_material_circuit_state(&encoded).unwrap();
        assert_eq!(restored.final_demand_principals[0].location, location);
        let close = advance_material_circuit(&restored).unwrap();
        assert_eq!(close.household_consumption[0].consumed_quantity, 4);
        let CircuitAccounting::Monetary(economy) = &close.state.accounting else {
            panic!("the shared close lost its monetary authority");
        };
        assert_eq!(economy.book.total_cash_and_reserves().unwrap(), money(24));
        assert_eq!(
            close
                .wage_accruals
                .iter()
                .map(|r| r.obligated_hours)
                .sum::<u64>(),
            16
        );
    }
}

#[test]
fn separately_accounted_household_cohorts_can_share_one_market_location() {
    let location = EconomicLocation::Foreign(ForeignCounterpart::Canada);
    let mut state = opening();
    place(&mut state, location);
    let second = FinalDemandPrincipalId::from_bytes([2; 32]);
    state.final_demand_principals.push(FinalDemandPrincipal {
        id: second,
        location,
    });
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("the fixture must explicitly fund both household accounts");
    };
    let mut accounts = economy.book.snapshot().accounts;
    accounts.push(CashAccount {
        id: AccountId::Household(second),
        cash: money(8),
    });
    let mut stocks = economy.costs.snapshot().stocks;
    stocks.push(StockCarryingValue {
        owner: AccountId::Household(second),
        good_id: good(2),
        unit_id: units(),
        amount: money(0),
    });
    economy.book = MonetaryBook::open(accounts).unwrap();
    economy.costs = HistoricalCostBook::open(&economy.book, stocks, vec![], vec![]).unwrap();
    let recurring = economy.recurring.as_mut().unwrap();
    // One cohort consumes its own pantry while its neighbor buys from the store.
    recurring.household_purchases[0].enabled = false;
    recurring.households.push(HouseholdCohort {
        principal_id: second,
        households: 1,
        persons: 1,
    });
    recurring.household_stocks.push(HouseholdStock {
        principal_id: second,
        good_id: good(2),
        unit_id: units(),
        quantity: 0,
    });
    recurring.household_needs.push(HouseholdNeed {
        principal_id: second,
        good_id: good(2),
        unit_id: units(),
        basis: babylon_material_circuit::HouseholdNeedBasis::Persons,
        units_per_basis: 1,
    });
    recurring.household_purchases.push(HouseholdPurchasePolicy {
        principal_id: second,
        retailer_site_id: site(3),
        good_id: good(2),
        unit_id: units(),
        target_closing_stock: 0,
        maximum_purchase: 1,
        enabled: true,
    });
    let close = advance_material_circuit(&state).unwrap();
    assert_eq!(close.household_consumption.len(), 2);
    assert_eq!(
        close
            .household_consumption
            .iter()
            .map(|r| r.required_quantity)
            .sum::<u64>(),
        5
    );
    assert_eq!(
        close
            .household_consumption
            .iter()
            .map(|r| r.consumed_quantity)
            .sum::<u64>(),
        5
    );
    let CircuitAccounting::Monetary(economy) = &close.state.accounting else {
        panic!("the shared close lost its monetary authority");
    };
    assert_eq!(economy.book.total_cash_and_reserves().unwrap(), money(32));
}

#[test]
fn a_local_retail_order_cannot_skip_an_international_delivery() {
    let mut state = opening();
    state.final_demand_principals[0].location =
        EconomicLocation::Foreign(ForeignCounterpart::Canada);
    assert_eq!(
        advance_material_circuit(&state).unwrap_err(),
        MaterialCircuitError::FinalDemandInvariant
    );
}

#[test]
fn material_wire_refuses_invalid_locations_and_the_previous_state_format() {
    let state = opening();
    let bytes = encode_material_circuit_state(&state).unwrap();
    let pattern = state.final_demand_principals[0].location.canonical_bytes();
    let offsets: Vec<_> = bytes
        .windows(pattern.len())
        .enumerate()
        .filter_map(|(index, value)| (value == pattern).then_some(index))
        .collect();
    assert_eq!(
        offsets.len(),
        2,
        "the control has one merchant and one buyer"
    );
    for offset in offsets {
        for malformed in [
            [0, b'7', b'2', b'0', b'0', b'1'],
            [1, 13, 0, 0, 0, 0],
            [2, 7, 0, 0, 0, 0],
        ] {
            let mut changed = bytes.clone();
            changed[offset..offset + 6].copy_from_slice(&malformed);
            assert_eq!(
                decode_material_circuit_state(&changed).unwrap_err(),
                MaterialCircuitError::WireEnum
            );
        }
    }
    let mut previous = bytes;
    let version = MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES.len() + 1;
    assert_eq!(&previous[version..version + 2], &13_u16.to_be_bytes());
    previous[version..version + 2].copy_from_slice(&11_u16.to_be_bytes());
    assert!(decode_material_circuit_state(&previous).is_err());
}
