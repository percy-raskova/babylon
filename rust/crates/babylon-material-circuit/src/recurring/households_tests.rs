use super::*;
use crate::*;
use babylon_kernel::currency::Currency;

fn cash(n: i128) -> Currency {
    Currency::from_micro_units(n)
}
fn h() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([1; 32])
}
fn s() -> SiteId {
    SiteId::from_bytes([2; 32])
}
fn g() -> GoodId {
    GoodId::from_bytes([3; 32])
}
fn u() -> UnitId {
    UnitId::from_bytes([4; 32])
}
fn hours() -> UnitId {
    UnitId::from_bytes([5; 32])
}

fn recurring(stock: u64) -> RecurringEconomy {
    RecurringEconomy {
        households: vec![HouseholdCohort {
            principal_id: h(),
            households: 1,
            persons: 4,
        }],
        household_stocks: vec![HouseholdStock {
            principal_id: h(),
            good_id: g(),
            unit_id: u(),
            quantity: stock,
        }],
        household_needs: vec![HouseholdNeed {
            principal_id: h(),
            good_id: g(),
            unit_id: u(),
            units_per_person: 1,
        }],
        household_purchases: vec![HouseholdPurchasePolicy {
            principal_id: h(),
            retailer_site_id: s(),
            good_id: g(),
            unit_id: u(),
            target_closing_stock: 0,
            maximum_purchase: 4,
            enabled: true,
        }],
        offers: vec![SellerOffer {
            site_id: s(),
            good_id: g(),
            unit_id: u(),
            unit_price: cash(4),
            pricing: PricePolicy::Fixed,
        }],
        replenishment: vec![],
        production: vec![],
        attendance: vec![AttendancePlan {
            site_id: s(),
            unit_id: hours(),
            period: 1,
            planned_hours: 4,
        }],
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    }
}

fn opening(household_cash: i128, stock: u64) -> MaterialCircuitState {
    MaterialCircuitState {
        period: 1,
        accounting: CircuitAccounting::Monetary(MonetaryCircuit {
            book: MonetaryBook::open(vec![
                CashAccount {
                    id: AccountId::Site(s()),
                    cash: cash(16),
                },
                CashAccount {
                    id: AccountId::Household(h()),
                    cash: cash(household_cash),
                },
            ])
            .unwrap(),
            employment: vec![EmploymentTerms {
                site_id: s(),
                unit_id: hours(),
                payee: h(),
                hourly_rate: cash(4),
            }],
            recurring: Some(Box::new(recurring(stock))),
        }),
        site_logistics_nodes: vec![SiteLogisticsNode {
            site_id: s(),
            node_id: LogisticsNodeId::from_bytes([2; 32]),
        }],
        process_outputs: vec![],
        input_coefficients: vec![],
        labor_coefficients: vec![],
        freight_mass_coefficients: vec![FreightMassCoefficient {
            good_id: g(),
            unit_id: u(),
            grams_per_unit: 1,
        }],
        supplier_routes: vec![],
        route_stages: vec![],
        route_stage_capacities: vec![],
        inventory: vec![InventoryRow {
            site_id: s(),
            good_id: g(),
            unit_id: u(),
            quantity: 8,
        }],
        orders: vec![],
        backlog: vec![],
        freight: vec![],
        corridor_capacities: vec![],
        capacities: vec![],
        labor: vec![LaborCapacityRow {
            site_id: s(),
            unit_id: hours(),
            period: 1,
            available: 4,
        }],
        production_commitments: vec![],
        merchants: vec![MerchantHandling {
            site_id: s(),
            county_geoid: *b"26163",
            role: MerchantRole::Retail,
            capacity_id: CorridorId::from_bytes([6; 32]),
            labor_unit_id: hours(),
        }],
        handling_coefficients: vec![MerchantHandlingCoefficient {
            site_id: s(),
            good_id: g(),
            unit_id: u(),
            hours_per_unit: 1,
        }],
        final_demand_principals: vec![FinalDemandPrincipal {
            id: h(),
            county_geoid: *b"26163",
        }],
        final_demand_orders: vec![],
        maintenance_binding: None,
        maintenance_service: None,
    }
}

fn economy(state: &mut MaterialCircuitState) -> &mut MonetaryCircuit {
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("monetary fixture");
    };
    economy
}
fn household_rows(state: &mut MaterialCircuitState) -> &mut RecurringEconomy {
    economy(state).recurring.as_mut().unwrap()
}
fn handoff(
    state: &mut MaterialCircuitState,
    id: OrderId,
    quantity: u64,
) -> LocalRetailFulfillmentReceipt {
    let row = state
        .final_demand_orders
        .iter_mut()
        .find(|r| r.order_id == id)
        .unwrap();
    row.fulfilled += quantity;
    state.inventory[0].quantity -= quantity;
    LocalRetailFulfillmentReceipt {
        order_id: id,
        retailer_site_id: row.retailer_site_id,
        demand_principal_id: row.demand_principal_id,
        good_id: row.good_id,
        unit_id: row.unit_id,
        quantity,
    }
}

#[test]
fn only_paid_current_cash_admits_household_orders() {
    let mut unpaid = opening(0, 0);
    let mut transfers = vec![];
    let requests = admit_household_orders(&mut unpaid, &mut transfers).unwrap();
    assert_eq!(
        (
            requests[0].required_quantity,
            requests[0].requested_quantity,
            requests[0].admitted_quantity
        ),
        (4, 4, 0)
    );
    assert!(unpaid.final_demand_orders.is_empty() && transfers.is_empty());
    let mut paid = opening(0, 0);
    crate::payments::fund_attendance(&mut paid, &mut transfers, &mut vec![]).unwrap();
    let requests = admit_household_orders(&mut paid, &mut transfers).unwrap();
    assert_eq!(requests[0].admitted_quantity, 4);
    assert_eq!(
        economy(&mut paid)
            .book
            .cash(AccountId::Household(h()))
            .unwrap(),
        cash(0)
    );
    assert_eq!(
        economy(&mut paid).book.total_cash_and_reserves().unwrap(),
        cash(16)
    );
    assert_eq!(
        economy(&mut paid)
            .book
            .purchase(OutboundOrderId::LocalFinalDemand(requests[0].order_id))
            .unwrap()
            .reserved_amount()
            .unwrap(),
        cash(16)
    );
}

#[test]
fn fulfillment_credits_stock_expiry_refunds_and_consumption_preserves_need() {
    let mut state = opening(16, 0);
    let mut transfers = vec![];
    let mut demands = admit_household_orders(&mut state, &mut transfers).unwrap();
    let receipt = handoff(&mut state, demands[0].order_id, 2);
    complete_household_orders(&mut state, &mut demands, &[receipt], &mut transfers).unwrap();
    assert_eq!(
        (demands[0].fulfilled_quantity, demands[0].expired_quantity),
        (2, 2)
    );
    assert_eq!(household_rows(&mut state).household_stocks[0].quantity, 2);
    assert!(state.final_demand_orders.is_empty());
    assert!(economy(&mut state).book.snapshot().purchases.is_empty());
    assert_eq!(
        economy(&mut state)
            .book
            .cash(AccountId::Household(h()))
            .unwrap(),
        cash(8)
    );
    assert_eq!(
        economy(&mut state).book.total_cash_and_reserves().unwrap(),
        cash(32)
    );
    let consumed = consume_household_needs(&mut state).unwrap();
    assert_eq!(
        (
            consumed[0].required_quantity,
            consumed[0].available_quantity,
            consumed[0].consumed_quantity,
            consumed[0].unmet_quantity,
            consumed[0].closing_quantity
        ),
        (4, 2, 2, 2, 0)
    );
    assert_eq!(
        household_rows(&mut state).household_needs[0].units_per_person,
        1
    );
    let closed = state.clone();
    assert_eq!(
        consume_household_needs(&mut state),
        Err(MaterialCircuitError::PeriodInvariant)
    );
    assert_eq!(state, closed);
}

#[test]
fn withdrawn_orders_do_not_erase_unemployed_residents_needs() {
    let mut state = opening(0, 2);
    state.labor[0].available = 0;
    household_rows(&mut state).household_purchases[0].enabled = false;
    let demands = admit_household_orders(&mut state, &mut vec![]).unwrap();
    assert_eq!(
        (
            demands[0].required_quantity,
            demands[0].desired_quantity,
            demands[0].requested_quantity,
            demands[0].admitted_quantity
        ),
        (4, 2, 0, 0)
    );
    let consumed = consume_household_needs(&mut state).unwrap();
    assert_eq!(
        (consumed[0].consumed_quantity, consumed[0].unmet_quantity),
        (2, 2)
    );
    assert_eq!(household_rows(&mut state).households[0].persons, 4);
}

#[test]
fn regenerated_orders_have_new_ids_and_same_period_retry_is_refused() {
    let mut state = opening(16, 0);
    let mut transfers = vec![];
    let mut first = admit_household_orders(&mut state, &mut transfers).unwrap();
    let admitted = state.clone();
    assert_eq!(
        admit_household_orders(&mut state, &mut transfers),
        Err(MaterialCircuitError::PeriodInvariant)
    );
    assert_eq!(state, admitted);
    complete_household_orders(&mut state, &mut first, &[], &mut transfers).unwrap();
    consume_household_needs(&mut state).unwrap();
    state.period = 2;
    household_rows(&mut state).attendance[0].period = 2;
    let second = admit_household_orders(&mut state, &mut transfers).unwrap();
    assert_ne!(first[0].order_id, second[0].order_id);
    assert_eq!(second[0].admitted_quantity, 4);
}

#[test]
fn malformed_or_repeated_handoffs_cannot_credit_stock_or_move_money() {
    let mut state = opening(16, 0);
    let mut transfers = vec![];
    let mut demands = admit_household_orders(&mut state, &mut transfers).unwrap();
    let receipt = handoff(&mut state, demands[0].order_id, 2);
    let before = (state.clone(), demands.clone(), transfers.clone());
    let mut wrong = receipt.clone();
    wrong.quantity = 3;
    assert!(complete_household_orders(&mut state, &mut demands, &[wrong], &mut transfers).is_err());
    assert_eq!((state.clone(), demands.clone(), transfers.clone()), before);
    assert!(complete_household_orders(
        &mut state,
        &mut demands,
        &[receipt.clone(), receipt.clone()],
        &mut transfers
    )
    .is_err());
    assert_eq!((state.clone(), demands.clone(), transfers.clone()), before);
    complete_household_orders(
        &mut state,
        &mut demands,
        std::slice::from_ref(&receipt),
        &mut transfers,
    )
    .unwrap();
    let after = (state.clone(), demands.clone(), transfers.clone());
    assert!(
        complete_household_orders(&mut state, &mut demands, &[receipt], &mut transfers).is_err()
    );
    assert_eq!((state, demands, transfers), after);
}

#[test]
fn finite_preexisting_household_order_is_credited_but_not_expired() {
    let mut state = opening(16, 0);
    let id = OrderId::from_bytes([90; 32]);
    economy(&mut state)
        .book
        .reserve_purchase(
            PurchaseEscrow::new(
                OutboundOrderId::LocalFinalDemand(id),
                AccountId::Household(h()),
                AccountId::Site(s()),
                2,
                cash(4),
            )
            .unwrap(),
        )
        .unwrap();
    state.final_demand_orders.push(FinalDemandOrder {
        order_id: id,
        retailer_site_id: s(),
        demand_principal_id: h(),
        good_id: g(),
        unit_id: u(),
        ordered: 2,
        fulfilled: 0,
    });
    let mut transfers = vec![];
    let mut demands = admit_household_orders(&mut state, &mut transfers).unwrap();
    assert_eq!(demands[0].admitted_quantity, 2);
    let old = handoff(&mut state, id, 1);
    let new = handoff(&mut state, demands[0].order_id, 1);
    complete_household_orders(&mut state, &mut demands, &[old, new], &mut transfers).unwrap();
    assert_eq!(household_rows(&mut state).household_stocks[0].quantity, 2);
    assert_eq!(state.final_demand_orders.len(), 1);
    assert_eq!(state.final_demand_orders[0].order_id, id);
    assert_eq!(
        economy(&mut state)
            .book
            .purchase(OutboundOrderId::LocalFinalDemand(id))
            .unwrap()
            .reserved_amount()
            .unwrap(),
        cash(4)
    );
}

#[test]
fn missing_or_overflowing_needs_and_invalid_prices_are_refused() {
    let mut state = opening(16, 0);
    validate(&state).unwrap();
    household_rows(&mut state).household_needs[0].units_per_person = u64::MAX;
    assert_eq!(validate(&state), Err(MaterialCircuitError::Arithmetic));
    let before = state.clone();
    assert_eq!(
        admit_household_orders(&mut state, &mut vec![]),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(state, before);
    let mut state = opening(16, 0);
    household_rows(&mut state).offers[0].unit_price = cash(0);
    assert_eq!(
        validate(&state),
        Err(MaterialCircuitError::PurchaseInvariant)
    );
    let mut state = opening(16, 0);
    household_rows(&mut state).household_stocks.clear();
    assert_eq!(
        validate(&state),
        Err(MaterialCircuitError::FinalDemandInvariant)
    );
}

#[test]
fn one_household_budget_is_shared_in_canonical_need_order() {
    let mut state = opening(4, 0);
    let other = GoodId::from_bytes([33; 32]);
    state
        .freight_mass_coefficients
        .push(FreightMassCoefficient {
            good_id: other,
            unit_id: u(),
            grams_per_unit: 1,
        });
    state
        .handling_coefficients
        .push(MerchantHandlingCoefficient {
            site_id: s(),
            good_id: other,
            unit_id: u(),
            hours_per_unit: 1,
        });
    let rows = household_rows(&mut state);
    rows.household_stocks.push(HouseholdStock {
        principal_id: h(),
        good_id: other,
        unit_id: u(),
        quantity: 0,
    });
    rows.household_needs.push(HouseholdNeed {
        principal_id: h(),
        good_id: other,
        unit_id: u(),
        units_per_person: 1,
    });
    rows.household_purchases.insert(
        0,
        HouseholdPurchasePolicy {
            principal_id: h(),
            retailer_site_id: s(),
            good_id: other,
            unit_id: u(),
            target_closing_stock: 0,
            maximum_purchase: 4,
            enabled: true,
        },
    );
    rows.offers.push(SellerOffer {
        site_id: s(),
        good_id: other,
        unit_id: u(),
        unit_price: cash(4),
        pricing: PricePolicy::Fixed,
    });
    let mut reordered = state.clone();
    canonicalize(household_rows(&mut reordered));
    let first = admit_household_orders(&mut state, &mut vec![]).unwrap();
    let second = admit_household_orders(&mut reordered, &mut vec![]).unwrap();
    assert_eq!(first, second);
    assert_eq!(
        first
            .iter()
            .map(|r| (r.good_id, r.admitted_quantity))
            .collect::<Vec<_>>(),
        vec![(g(), 1), (other, 0)]
    );
    assert_eq!(
        economy(&mut state)
            .book
            .cash(AccountId::Household(h()))
            .unwrap(),
        cash(0)
    );
}

#[test]
fn consumption_cannot_skip_an_unresolved_generated_order() {
    let mut state = opening(16, 0);
    admit_household_orders(&mut state, &mut vec![]).unwrap();
    let before = state.clone();
    assert_eq!(
        consume_household_needs(&mut state),
        Err(MaterialCircuitError::PurchaseInvariant)
    );
    assert_eq!(state, before);
}
