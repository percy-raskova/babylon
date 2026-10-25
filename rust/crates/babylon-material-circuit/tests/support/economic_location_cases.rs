//! Shared paid controls must admit real market locations without fictional GEOIDs.

use babylon_kernel::economic_location::{EconomicLocation, ForeignCounterpart, UsDependency};
use babylon_kernel::geography::CountyGeoid;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::CashAccount;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::FinalDemandPrincipal;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::HouseholdCohort;
use babylon_material_circuit::HouseholdKind;
use babylon_material_circuit::HouseholdNeed;
use babylon_material_circuit::HouseholdNeedBasis;
use babylon_material_circuit::HouseholdPurchasePolicy;
use babylon_material_circuit::HouseholdStock;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::StockCarryingValue;
use babylon_material_circuit::MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES;

fn place(
    catalog: &mut MaterialCatalog,
    state: &mut MaterialCircuitState,
    location: EconomicLocation,
) {
    for row in &mut catalog.merchants {
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
        .map(|key| {
            EconomicLocation::domestic_county(
                CountyGeoid::try_from(key).expect("the fixture value fits the target range"),
            )
            .expect("the fixture geoid names a domestic county")
        })
        .chain(ForeignCounterpart::ALL.map(EconomicLocation::Foreign))
        .chain(UsDependency::ALL.map(EconomicLocation::Dependency));
    for location in locations {
        let (mut catalog, mut state) = crate::opening();
        place(&mut catalog, &mut state, location);
        catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
        let encoded = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
            .expect("the canonical material state encodes");
        let restored = babylon_material_circuit::decode_material_circuit_state(&catalog, &encoded)
            .expect("the canonical material bytes decode");
        assert_eq!(restored.final_demand_principals[0].location, location);
        let close = babylon_material_circuit::advance_material_circuit(&catalog, &restored)
            .expect("the authored material state advances one period");
        assert_eq!(close.household_consumption[0].consumed_quantity, 4);
        let CircuitAccounting::Monetary(economy) = &close.state.accounting else {
            panic!("the shared close lost its monetary authority");
        };
        assert_eq!(
            economy
                .book
                .total_cash_and_reserves()
                .expect("the fixture book totals without overflow"),
            crate::money(24)
        );
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
    let (mut catalog, mut state) = crate::opening();
    place(&mut catalog, &mut state, location);
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
        cash: crate::money(8),
    });
    let mut stocks = economy.costs.snapshot().stocks;
    stocks.push(StockCarryingValue {
        owner: AccountId::Household(second),
        good_id: crate::good(2),
        unit_id: crate::units(),
        amount: crate::money(0),
    });
    economy.book = MonetaryBook::open(accounts).expect("the fixture opens the authored source");
    economy.costs = HistoricalCostBook::open(&economy.book, stocks, vec![], vec![], vec![])
        .expect("the fixture opens the authored source");
    let recurring = economy
        .recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow");
    // One cohort consumes its own pantry while its neighbor buys from the store.
    recurring.household_purchases[0].enabled = false;
    recurring.households.push(HouseholdCohort {
        kind: HouseholdKind::Ordinary,
        principal_id: second,
        households: 1,
        persons: 1,
    });
    recurring.household_stocks.push(HouseholdStock {
        principal_id: second,
        good_id: crate::good(2),
        unit_id: crate::units(),
        quantity: 0,
    });
    let need = HouseholdNeed {
        principal_id: second,
        good_id: crate::good(2),
        unit_id: crate::units(),
        basis: HouseholdNeedBasis::Persons,
        units_per_basis: 1,
    };
    recurring.household_needs.push(need.clone());
    catalog.household_needs.push(need);
    recurring.household_purchases.push(HouseholdPurchasePolicy {
        principal_id: second,
        retailer_site_id: crate::site(3),
        good_id: crate::good(2),
        unit_id: crate::units(),
        target_closing_stock: 0,
        maximum_purchase: 1,
        enabled: true,
    });
    catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    let close = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
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
    assert_eq!(
        economy
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        crate::money(32)
    );
}

#[test]
fn a_local_retail_order_cannot_skip_an_international_delivery() {
    let (catalog, mut state) = crate::opening();
    state.final_demand_principals[0].location =
        EconomicLocation::Foreign(ForeignCounterpart::Canada);
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect_err("the invalid material state is refused"),
        MaterialCircuitError::FinalDemandInvariant
    );
}

#[test]
fn material_wire_refuses_invalid_locations_and_the_previous_state_format() {
    let (catalog, state) = crate::opening();
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
    let pattern = state.final_demand_principals[0].location.canonical_bytes();
    let offsets: Vec<_> = bytes
        .windows(pattern.len())
        .enumerate()
        .filter_map(|(index, value)| (value == pattern).then_some(index))
        .collect();
    assert_eq!(
        offsets.len(),
        1,
        "the compact state carries only the demand principal's location"
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
                babylon_material_circuit::decode_material_circuit_state(&catalog, &changed)
                    .expect_err("`decode_material_circuit_state` rejects the malformed bytes"),
                MaterialCircuitError::WireEnum
            );
        }
    }
    let mut previous = bytes;
    let version = MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES.len() + 1;
    assert_eq!(&previous[version..version + 2], &20_u16.to_be_bytes());
    for unsupported in [14_u16, 15, 16, 17, 18, 19] {
        previous[version..version + 2].copy_from_slice(&unsupported.to_be_bytes());
        assert_eq!(
            babylon_material_circuit::decode_material_circuit_state(&catalog, &previous),
            Err(MaterialCircuitError::WireVersion)
        );
    }
}
