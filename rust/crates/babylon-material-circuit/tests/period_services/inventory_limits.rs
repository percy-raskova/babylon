use babylon_material_circuit::decode_material_circuit_state;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::CashAccount;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::CommodityDefinition;
use babylon_material_circuit::CommodityKind;
use babylon_material_circuit::CorridorId;
use babylon_material_circuit::FinalDemandPrincipal;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::GoodId;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::HouseholdNeed;
use babylon_material_circuit::HouseholdNeedBasis;
use babylon_material_circuit::HouseholdPurchasePolicy;
use babylon_material_circuit::HouseholdStock;
use babylon_material_circuit::InventoryRow;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MerchantHandling;
use babylon_material_circuit::MerchantHandlingCoefficient;
use babylon_material_circuit::MerchantRole;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::PricePolicy;
use babylon_material_circuit::SellerOffer;
use babylon_material_circuit::StockCarryingValue;
use babylon_material_circuit::MAX_CARRYING_STOCKS;
use babylon_material_circuit::MAX_INVENTORY_ROWS;
use std::collections::BTreeSet;

fn padded_goods_inventory(include_output: bool) -> (MaterialCatalog, MaterialCircuitState) {
    let (catalog, mut state) = crate::opening();
    state.inventory[0].quantity = 2;
    let mut state = crate::funded(&catalog, state);
    if !include_output {
        state.inventory.retain(|r| r.good_id != crate::good(3));
    }
    let missing = MAX_INVENTORY_ROWS - state.inventory.len();
    let mut catalog = catalog.into_definition();
    for index in 0..missing {
        let mut identity = [0; 32];
        identity[0] = 170;
        identity[24..].copy_from_slice(
            &u64::try_from(index / 3)
                .expect("the fixture value fits the target range")
                .to_be_bytes(),
        );
        let extra_good = GoodId::from_bytes(identity);
        if index % 3 == 0 {
            catalog.commodities.push(CommodityDefinition {
                good_id: extra_good,
                unit_id: crate::unit(4),
                kind: CommodityKind::Storable { grams_per_unit: 1 },
            });
        }
        state.inventory.push(InventoryRow {
            site_id: crate::site(
                u8::try_from(index % 3 + 1).expect("the fixture value fits the target range"),
            ),
            good_id: extra_good,
            unit_id: crate::unit(4),
            quantity: 1,
        });
    }

    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        unreachable!()
    };
    e.costs = HistoricalCostBook::open(
        &e.book,
        state
            .inventory
            .iter()
            .map(|row| StockCarryingValue {
                owner: AccountId::Site(row.site_id),
                good_id: row.good_id,
                unit_id: row.unit_id,
                amount: crate::money(0),
            })
            .collect(),
        vec![],
        vec![],
        vec![],
    )
    .expect("the fixture opens the authored source");
    (catalog, state)
}

#[test]
fn temporary_service_outputs_and_grants_do_not_consume_durable_stock_row_budget() {
    let (catalog, opening) = padded_goods_inventory(true);
    let opening_bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &opening)
        .expect("the canonical material state encodes");
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period");
    assert_eq!(closed.state.inventory.len(), MAX_INVENTORY_ROWS);
    assert_eq!(
        closed
            .production
            .iter()
            .map(|r| r.produced_batches)
            .collect::<Vec<_>>(),
        vec![2, 1, 1]
    );
    assert!(closed
        .state
        .inventory
        .iter()
        .all(|r| r.good_id != crate::good(1) && r.good_id != crate::good(2)));
    assert!(closed
        .service_performance
        .iter()
        .all(|r| r.performed_quantity == 1 && r.used_quantity == 1));
    assert_eq!(closed.state.service_orders.len(), 0);
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &closed.state)
        .expect("the canonical material state encodes");
    assert_eq!(
        decode_material_circuit_state(&catalog, &bytes)
            .expect("the canonical material bytes decode"),
        closed.state
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &opening)
            .expect("the canonical material state encodes"),
        opening_bytes
    );
}

#[test]
fn a_new_durable_stock_key_above_its_own_limit_still_refuses_the_successor() {
    let (catalog, opening) = padded_goods_inventory(false);
    let opening_bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &opening)
        .expect("the canonical material state encodes");
    let detached = babylon_material_circuit::close_material_period(&catalog, &opening)
        .expect("the material period closes");
    assert_eq!(detached.inventory().len(), MAX_INVENTORY_ROWS + 1);
    assert!(detached
        .inventory()
        .iter()
        .all(|r| r.good_id != crate::good(1) && r.good_id != crate::good(2)));
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &opening),
        Err(MaterialCircuitError::RowLimit)
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &opening)
            .expect("the canonical material state encodes"),
        opening_bytes
    );
}

#[allow(
    clippy::too_many_lines,
    reason = "a conformance scenario builds its whole fixture and asserts the full trajectory in one test"
)]
fn padded_durable_carrying_book() -> (MaterialCatalog, MaterialCircuitState) {
    let (catalog, state) = padded_goods_inventory(true);
    let (catalog, mut state) = super::service_cases::recurring((catalog, state));
    let other = FinalDemandPrincipalId::from_bytes([10; 32]);
    let location = state.final_demand_principals[0].location;
    state.final_demand_principals.push(FinalDemandPrincipal {
        id: other,
        location,
    });
    let mut catalog = catalog.into_definition();
    catalog.merchants.push(MerchantHandling {
        site_id: crate::site(3),
        location,
        role: MerchantRole::Retail,
        capacity_id: CorridorId::from_bytes([10; 32]),
        labor_unit_id: crate::unit(9),
    });
    let goods: Vec<_> = catalog
        .commodities
        .iter()
        .filter(|row| row.good_id.as_bytes()[0] == 170)
        .take(32_766)
        .map(|row| row.good_id)
        .collect();
    for commodity in &goods {
        catalog
            .handling_coefficients
            .push(MerchantHandlingCoefficient {
                site_id: crate::site(3),
                good_id: *commodity,
                unit_id: crate::unit(4),
                hours_per_unit: 1,
            });
    }
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        unreachable!()
    };
    let mut snapshot = e.book.snapshot();
    snapshot.accounts.push(CashAccount {
        id: AccountId::Household(other),
        cash: crate::money(0),
    });
    e.book = MonetaryBook::from_snapshot(snapshot).expect("the snapshot admits the derived value");
    let recurring = e
        .recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow");
    let mut cohort = recurring.households[0].clone();
    cohort.principal_id = other;
    recurring.households.push(cohort);
    for commodity in &goods {
        recurring.offers.push(SellerOffer {
            site_id: crate::site(3),
            good_id: *commodity,
            unit_id: crate::unit(4),
            unit_price: crate::money(1),
            pricing: PricePolicy::Fixed,
        });
    }
    for (principal, count) in [(crate::household(), 32_766), (other, 32_765)] {
        for commodity in goods.iter().take(count) {
            recurring.household_stocks.push(HouseholdStock {
                principal_id: principal,
                good_id: *commodity,
                unit_id: crate::unit(4),
                quantity: 1,
            });
            catalog.household_needs.push(HouseholdNeed {
                principal_id: principal,
                good_id: *commodity,
                unit_id: crate::unit(4),
                basis: HouseholdNeedBasis::Persons,
                units_per_basis: 1,
            });
            recurring.household_purchases.push(HouseholdPurchasePolicy {
                principal_id: principal,
                retailer_site_id: crate::site(3),
                good_id: *commodity,
                unit_id: crate::unit(4),
                target_closing_stock: 0,
                maximum_purchase: 0,
                enabled: false,
            });
        }
    }
    let stocks = state
        .inventory
        .iter()
        .map(|row| StockCarryingValue {
            owner: AccountId::Site(row.site_id),
            good_id: row.good_id,
            unit_id: row.unit_id,
            amount: crate::money(0),
        })
        .chain(
            recurring
                .household_stocks
                .iter()
                .map(|row| StockCarryingValue {
                    owner: AccountId::Household(row.principal_id),
                    good_id: row.good_id,
                    unit_id: row.unit_id,
                    amount: crate::money(0),
                }),
        )
        .collect();
    e.costs = HistoricalCostBook::open(&e.book, stocks, vec![], vec![], vec![])
        .expect("the fixture opens the authored source");
    assert_eq!(e.costs.snapshot().stocks.len(), MAX_CARRYING_STOCKS - 5);

    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    (catalog, state)
}

#[test]
fn paid_service_grants_cross_the_old_carrying_cap_and_expire_before_publication() {
    let (catalog, opening) = padded_durable_carrying_book();
    let opening_bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &opening)
        .expect("the canonical material state encodes");
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period");
    assert_eq!(closed.state.inventory.len(), MAX_INVENTORY_ROWS);
    assert!(closed
        .service_outputs
        .iter()
        .all(|row| row.produced_quantity > 0));
    assert!(closed
        .service_performance
        .iter()
        .filter(|row| row.admitted_quantity > 0)
        .all(|row| row.performed_quantity > 0));
    let transient: BTreeSet<_> = closed
        .service_outputs
        .iter()
        .map(|row| (AccountId::Site(row.site_id), row.good_id, row.unit_id))
        .chain(
            closed
                .service_performance
                .iter()
                .filter(|row| row.performed_quantity > 0)
                .map(|row| (row.buyer, row.good_id, row.unit_id)),
        )
        .collect();
    assert_eq!(transient.len(), 6);
    assert!(MAX_CARRYING_STOCKS - 5 + transient.len() > MAX_CARRYING_STOCKS);
    assert_eq!(closed.household_services[0].satisfied_quantity, 1);
    let CircuitAccounting::Monetary(e) = &closed.state.accounting else {
        unreachable!()
    };
    let stocks = e.costs.snapshot().stocks;
    assert_eq!(stocks.len(), MAX_CARRYING_STOCKS - 5);
    assert!(stocks
        .iter()
        .all(|row| row.good_id != crate::good(1) && row.good_id != crate::good(2)));
    assert_eq!(closed.state.service_orders.len(), 0);
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &closed.state)
        .expect("the canonical material state encodes");
    assert_eq!(
        decode_material_circuit_state(&catalog, &bytes)
            .expect("the canonical material bytes decode"),
        closed.state
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &opening)
            .expect("the canonical material state encodes"),
        opening_bytes
    );
}
