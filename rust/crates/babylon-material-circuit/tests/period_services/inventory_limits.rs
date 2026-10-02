use super::*;

fn padded_goods_inventory(include_output: bool) -> MaterialCircuitState {
    let mut state = opening();
    state.inventory[0].quantity = 2;
    let mut state = funded(state);
    if !include_output {
        state.inventory.retain(|r| r.good_id != good(3));
    }
    let missing = MAX_INVENTORY_ROWS - state.inventory.len();
    for index in 0..missing {
        let mut identity = [0; 32];
        identity[0] = 170;
        identity[24..].copy_from_slice(&u64::try_from(index / 3).unwrap().to_be_bytes());
        let extra_good = GoodId::from_bytes(identity);
        if index % 3 == 0 {
            state.commodities.push(CommodityDefinition {
                good_id: extra_good,
                unit_id: unit(4),
                kind: CommodityKind::Storable { grams_per_unit: 1 },
            });
        }
        state.inventory.push(InventoryRow {
            site_id: site(u8::try_from(index % 3 + 1).unwrap()),
            good_id: extra_good,
            unit_id: unit(4),
            quantity: 1,
        });
    }
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
                amount: money(0),
            })
            .collect(),
        vec![],
        vec![],
        vec![],
    )
    .unwrap();
    state
}

#[test]
fn temporary_service_outputs_and_grants_do_not_consume_durable_stock_row_budget() {
    let opening = padded_goods_inventory(true);
    let opening_bytes = encode_material_circuit_state(&opening).unwrap();
    let closed = advance_material_circuit(&opening).unwrap();
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
        .all(|r| r.good_id != good(1) && r.good_id != good(2)));
    assert!(closed
        .service_performance
        .iter()
        .all(|r| r.performed_quantity == 1 && r.used_quantity == 1));
    assert!(closed.state.service_orders.is_empty());
    let bytes = encode_material_circuit_state(&closed.state).unwrap();
    assert_eq!(decode_material_circuit_state(&bytes).unwrap(), closed.state);
    assert_eq!(
        encode_material_circuit_state(&opening).unwrap(),
        opening_bytes
    );
}

#[test]
fn a_new_durable_stock_key_above_its_own_limit_still_refuses_the_successor() {
    let opening = padded_goods_inventory(false);
    let opening_bytes = encode_material_circuit_state(&opening).unwrap();
    let detached = close_material_period(&opening).unwrap();
    assert_eq!(detached.inventory().len(), MAX_INVENTORY_ROWS + 1);
    assert!(detached
        .inventory()
        .iter()
        .all(|r| r.good_id != good(1) && r.good_id != good(2)));
    assert_eq!(
        advance_material_circuit(&opening),
        Err(MaterialCircuitError::RowLimit)
    );
    assert_eq!(
        encode_material_circuit_state(&opening).unwrap(),
        opening_bytes
    );
}

fn padded_durable_carrying_book() -> MaterialCircuitState {
    let mut state = super::service_cases::recurring(padded_goods_inventory(true));
    let other = FinalDemandPrincipalId::from_bytes([10; 32]);
    let location = state.final_demand_principals[0].location;
    state.final_demand_principals.push(FinalDemandPrincipal {
        id: other,
        location,
    });
    state.merchants.push(MerchantHandling {
        site_id: site(3),
        location,
        role: MerchantRole::Retail,
        capacity_id: CorridorId::from_bytes([10; 32]),
        labor_unit_id: unit(9),
    });
    let goods: Vec<_> = state
        .commodities
        .iter()
        .filter(|row| row.good_id.as_bytes()[0] == 170)
        .take(32_766)
        .map(|row| row.good_id)
        .collect();
    for commodity in &goods {
        state
            .handling_coefficients
            .push(MerchantHandlingCoefficient {
                site_id: site(3),
                good_id: *commodity,
                unit_id: unit(4),
                hours_per_unit: 1,
            });
    }
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        unreachable!()
    };
    let mut snapshot = e.book.snapshot();
    snapshot.accounts.push(CashAccount {
        id: AccountId::Household(other),
        cash: money(0),
    });
    e.book = MonetaryBook::from_snapshot(snapshot).unwrap();
    let recurring = e.recurring.as_mut().unwrap();
    let mut cohort = recurring.households[0].clone();
    cohort.principal_id = other;
    recurring.households.push(cohort);
    for commodity in &goods {
        recurring.offers.push(SellerOffer {
            site_id: site(3),
            good_id: *commodity,
            unit_id: unit(4),
            unit_price: money(1),
            pricing: PricePolicy::Fixed,
        });
    }
    for (principal, count) in [(household(), 32_766), (other, 32_765)] {
        for commodity in goods.iter().take(count) {
            recurring.household_stocks.push(HouseholdStock {
                principal_id: principal,
                good_id: *commodity,
                unit_id: unit(4),
                quantity: 1,
            });
            recurring.household_needs.push(HouseholdNeed {
                principal_id: principal,
                good_id: *commodity,
                unit_id: unit(4),
                basis: HouseholdNeedBasis::Persons,
                units_per_basis: 1,
            });
            recurring.household_purchases.push(HouseholdPurchasePolicy {
                principal_id: principal,
                retailer_site_id: site(3),
                good_id: *commodity,
                unit_id: unit(4),
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
            amount: money(0),
        })
        .chain(
            recurring
                .household_stocks
                .iter()
                .map(|row| StockCarryingValue {
                    owner: AccountId::Household(row.principal_id),
                    good_id: row.good_id,
                    unit_id: row.unit_id,
                    amount: money(0),
                }),
        )
        .collect();
    e.costs = HistoricalCostBook::open(&e.book, stocks, vec![], vec![], vec![]).unwrap();
    assert_eq!(e.costs.snapshot().stocks.len(), MAX_CARRYING_STOCKS - 5);
    state
}

#[test]
fn paid_service_grants_cross_the_old_carrying_cap_and_expire_before_publication() {
    let opening = padded_durable_carrying_book();
    let opening_bytes = encode_material_circuit_state(&opening).unwrap();
    let closed = advance_material_circuit(&opening).unwrap();
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
    let transient: std::collections::BTreeSet<_> = closed
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
        .all(|row| row.good_id != good(1) && row.good_id != good(2)));
    assert!(closed.state.service_orders.is_empty());
    let bytes = encode_material_circuit_state(&closed.state).unwrap();
    assert_eq!(decode_material_circuit_state(&bytes).unwrap(), closed.state);
    assert_eq!(
        encode_material_circuit_state(&opening).unwrap(),
        opening_bytes
    );
}
