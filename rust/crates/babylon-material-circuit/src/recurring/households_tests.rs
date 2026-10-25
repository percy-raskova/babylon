use crate::AccountId;
use crate::AidBook;
use crate::AttendancePlan;
use crate::CapacityReservations;
use crate::CapacitySupply;
use crate::CashAccount;
use crate::CircuitAccounting;
use crate::CommodityDefinition;
use crate::CorridorId;
use crate::EmploymentTerms;
use crate::FinalDemandOrder;
use crate::FinalDemandPrincipal;
use crate::FinalDemandPrincipalId;
use crate::FinancialInstitutions;
use crate::GoodId;
use crate::HistoricalCostBook;
use crate::HouseholdCohort;
use crate::HouseholdNeed;
use crate::HouseholdNeedBasis;
use crate::HouseholdPurchasePolicy;
use crate::HouseholdStock;
use crate::HouseholdTimeAccounting;
use crate::InventoryRow;
use crate::LaborCapacityRow;
use crate::LocalRetailFulfillmentReceipt;
use crate::LogisticsNodeId;
use crate::MaterialCatalog;
use crate::MaterialCircuitError;
use crate::MaterialCircuitState;
use crate::MerchantHandling;
use crate::MerchantHandlingCoefficient;
use crate::MerchantRole;
use crate::MonetaryBook;
use crate::MonetaryCircuit;
use crate::OrderId;
use crate::OutboundOrderId;
use crate::PricePolicy;
use crate::PurchaseEscrow;
use crate::RecurringEconomy;
use crate::SellerOffer;
use crate::SiteId;
use crate::SiteLogisticsNode;
use crate::StockCarryingValue;
use crate::UnitId;
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
        service_inputs: vec![],
        households: vec![HouseholdCohort {
            kind: crate::HouseholdKind::Ordinary,
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
            basis: HouseholdNeedBasis::Persons,
            units_per_basis: 1,
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

fn opening_economy(household_cash: i128, stock: u64) -> MonetaryCircuit {
    let book = MonetaryBook::open(vec![
        CashAccount {
            id: AccountId::Site(s()),
            cash: cash(16),
        },
        CashAccount {
            id: AccountId::Household(h()),
            cash: cash(household_cash),
        },
    ])
    .expect("the fixture opens the authored source");
    MonetaryCircuit {
        aid: AidBook::default(),

        household_time: HouseholdTimeAccounting::NotModeled,
        financial: FinancialInstitutions::empty(),
        member_labor: vec![crate::MemberLaborCapacityRow {
            member_id: crate::StaffingMemberId::from_bytes(s().as_bytes()),
            period: 1,
            available_hours: 4,
        }],
        costs: HistoricalCostBook::open(
            &book,
            [AccountId::Site(s()), AccountId::Household(h())]
                .into_iter()
                .map(|owner| StockCarryingValue {
                    owner,
                    good_id: g(),
                    unit_id: u(),
                    amount: cash(0),
                })
                .collect(),
            vec![],
            vec![],
            vec![],
        )
        .expect("the fixture opens the authored source"),
        book,
        employment: vec![EmploymentTerms {
            member_id: crate::StaffingMemberId::from_bytes((s()).as_bytes()),
            site_id: s(),
            unit_id: hours(),
            payee: h(),
            compensation: crate::LaborCompensation::Wage(cash(4)),
        }],
        recurring: Some(Box::new(recurring(stock))),
    }
}

fn opening(household_cash: i128, stock: u64) -> (MaterialCatalog, MaterialCircuitState) {
    let state = MaterialCircuitState {
        period: 1,
        accounting: CircuitAccounting::Monetary(Box::new(opening_economy(household_cash, stock))),
        service_connections: vec![],
        service_orders: vec![],
        route_stage_capacities: vec![],
        inventory: vec![InventoryRow {
            site_id: s(),
            good_id: g(),
            unit_id: u(),
            quantity: 8,
        }],
        orders: vec![],
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
        final_demand_principals: vec![FinalDemandPrincipal {
            id: h(),
            location: "county:26163"
                .parse()
                .expect("the authored literal parses as the declared type"),
        }],
        final_demand_orders: vec![],
        maintenance_service: None,
        capacity_reservations: CapacityReservations::default(),
    };
    fixture(
        MaterialCatalog {
            capacity_policy: CapacitySupply::FiniteSchedule,
            site_logistics_nodes: vec![SiteLogisticsNode {
                site_id: s(),
                node_id: LogisticsNodeId::from_bytes([2; 32]),
            }],
            process_outputs: vec![],
            input_coefficients: vec![],
            labor_coefficients: vec![],
            commodities: vec![CommodityDefinition {
                good_id: g(),
                unit_id: u(),
                kind: crate::CommodityKind::Storable { grams_per_unit: 1 },
            }],
            supplier_routes: vec![],
            route_stages: vec![],
            merchants: vec![MerchantHandling {
                site_id: s(),
                location: "county:26163"
                    .parse()
                    .expect("the authored literal parses as the declared type"),
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
            maintenance_binding: None,
            aid_mandates: Vec::new(),
            household_time_policy: Vec::new(),
            service_inputs: Vec::new(),
            household_needs: Vec::new(),
            catalog_digest: crate::UNSEALED_CATALOG_DIGEST,
        },
        state,
    )
}

fn economy(state: &mut MaterialCircuitState) -> &mut MonetaryCircuit {
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("monetary fixture");
    };
    economy
}
fn household_rows(state: &mut MaterialCircuitState) -> &mut RecurringEconomy {
    economy(state)
        .recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
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
        .expect("the fixture holds the searched element");
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

fn fixture(
    mut catalog: MaterialCatalog,
    state: MaterialCircuitState,
) -> (MaterialCatalog, MaterialCircuitState) {
    if let crate::CircuitAccounting::Monetary(economy) = &state.accounting {
        if let Some(recurring) = &economy.recurring {
            catalog.service_inputs.clone_from(&recurring.service_inputs);
            catalog
                .household_needs
                .clone_from(&recurring.household_needs);
        }
        catalog.aid_mandates.clone_from(&economy.aid.mandates);
    }
    catalog.catalog_digest = crate::UNSEALED_CATALOG_DIGEST;
    let catalog = MaterialCatalog::try_new(catalog).expect("the authored fixture catalog is valid");
    (catalog, state)
}

#[test]
fn only_paid_current_cash_admits_household_orders() {
    let (catalog, mut unpaid) = opening(0, 0);
    let mut transfers = vec![];
    let requests = crate::admit_household_orders(&catalog, &mut unpaid, &mut transfers)
        .expect("the fixture admits the household orders");
    assert_eq!(
        (
            requests[0].required_quantity,
            requests[0].requested_quantity,
            requests[0].admitted_quantity
        ),
        (4, 4, 0)
    );
    assert!(unpaid.final_demand_orders.is_empty() && transfers.is_empty());
    let (catalog, mut paid) = opening(0, 0);
    crate::payments::fund_attendance(&mut paid, &mut transfers, &mut vec![])
        .expect("the fixture funds the authored attendance");
    let requests = crate::admit_household_orders(&catalog, &mut paid, &mut transfers)
        .expect("the fixture admits the household orders");
    assert_eq!(requests[0].admitted_quantity, 4);
    assert_eq!(
        economy(&mut paid)
            .book
            .cash(AccountId::Household(h()))
            .expect("the fixture book holds the payer account"),
        cash(0)
    );
    assert_eq!(
        economy(&mut paid)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        cash(16)
    );
    assert_eq!(
        economy(&mut paid)
            .book
            .purchase(OutboundOrderId::LocalFinalDemand(requests[0].order_id))
            .expect("the fixture purchase is present")
            .reserved_amount()
            .expect("the fixture reservation exists"),
        cash(16)
    );
}

#[test]
fn fulfillment_credits_stock_expiry_refunds_and_consumption_preserves_need() {
    let (catalog, mut state) = opening(16, 0);
    let mut transfers = vec![];
    let mut demands = crate::admit_household_orders(&catalog, &mut state, &mut transfers)
        .expect("the fixture admits the household orders");
    let receipt = handoff(&mut state, demands[0].order_id, 2);
    crate::complete_household_orders(&mut state, &mut demands, &[receipt], &mut transfers)
        .expect("the fixture completes the authored orders");
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
            .expect("the fixture book holds the payer account"),
        cash(8)
    );
    assert_eq!(
        economy(&mut state)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        cash(32)
    );
    let consumed = crate::consume_household_needs(&mut state)
        .expect("the fixture households consume their authored needs");
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
        household_rows(&mut state).household_needs[0].units_per_basis,
        1
    );
    let closed = state.clone();
    assert_eq!(
        crate::consume_household_needs(&mut state),
        Err(MaterialCircuitError::PeriodInvariant)
    );
    assert_eq!(state, closed);
}

#[test]
fn withdrawn_orders_do_not_erase_unemployed_residents_needs() {
    let (catalog, mut state) = opening(0, 2);
    state.labor[0].available = 0;
    economy(&mut state).member_labor[0].available_hours = 0;
    household_rows(&mut state).household_purchases[0].enabled = false;
    let demands = crate::admit_household_orders(&catalog, &mut state, &mut vec![])
        .expect("the fixture admits the household orders");
    assert_eq!(
        (
            demands[0].required_quantity,
            demands[0].desired_quantity,
            demands[0].requested_quantity,
            demands[0].admitted_quantity
        ),
        (4, 2, 0, 0)
    );
    let consumed = crate::consume_household_needs(&mut state)
        .expect("the fixture households consume their authored needs");
    assert_eq!(
        (consumed[0].consumed_quantity, consumed[0].unmet_quantity),
        (2, 2)
    );
    assert_eq!(household_rows(&mut state).households[0].persons, 4);
}

#[test]
fn regenerated_orders_have_new_ids_and_same_period_retry_is_refused() {
    let (catalog, mut state) = opening(16, 0);
    let mut transfers = vec![];
    let mut first = crate::admit_household_orders(&catalog, &mut state, &mut transfers)
        .expect("the fixture admits the household orders");
    let admitted = state.clone();
    assert_eq!(
        crate::admit_household_orders(&catalog, &mut state, &mut transfers),
        Err(MaterialCircuitError::PeriodInvariant)
    );
    assert_eq!(state, admitted);
    crate::complete_household_orders(&mut state, &mut first, &[], &mut transfers)
        .expect("the fixture completes the authored orders");
    crate::consume_household_needs(&mut state)
        .expect("the fixture households consume their authored needs");
    state.period = 2;
    household_rows(&mut state).attendance[0].period = 2;
    let second = crate::admit_household_orders(&catalog, &mut state, &mut transfers)
        .expect("the fixture admits the household orders");
    assert_ne!(first[0].order_id, second[0].order_id);
    assert_eq!(second[0].admitted_quantity, 4);
}

#[test]
fn malformed_or_repeated_handoffs_cannot_credit_stock_or_move_money() {
    let (catalog, mut state) = opening(16, 0);
    let mut transfers = vec![];
    let mut demands = crate::admit_household_orders(&catalog, &mut state, &mut transfers)
        .expect("the fixture admits the household orders");
    let receipt = handoff(&mut state, demands[0].order_id, 2);
    let before = (state.clone(), demands.clone(), transfers.clone());
    let mut wrong = receipt.clone();
    wrong.quantity = 3;
    assert!(
        crate::complete_household_orders(&mut state, &mut demands, &[wrong], &mut transfers)
            .is_err()
    );
    assert_eq!((state.clone(), demands.clone(), transfers.clone()), before);
    assert!(crate::complete_household_orders(
        &mut state,
        &mut demands,
        &[receipt.clone(), receipt.clone()],
        &mut transfers
    )
    .is_err());
    assert_eq!((state.clone(), demands.clone(), transfers.clone()), before);
    crate::complete_household_orders(
        &mut state,
        &mut demands,
        std::slice::from_ref(&receipt),
        &mut transfers,
    )
    .expect("the fixture completes the authored orders");
    let after = (state.clone(), demands.clone(), transfers.clone());
    assert!(
        crate::complete_household_orders(&mut state, &mut demands, &[receipt], &mut transfers)
            .is_err()
    );
    assert_eq!((state, demands, transfers), after);
}

#[test]
fn finite_preexisting_household_order_is_credited_but_not_expired() {
    let (catalog, mut state) = opening(16, 0);
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
            .expect("the constructor accepts the authored fixture arguments"),
        )
        .expect("the fixture reserve admits the purchase");
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
    let mut demands = crate::admit_household_orders(&catalog, &mut state, &mut transfers)
        .expect("the fixture admits the household orders");
    assert_eq!(demands[0].admitted_quantity, 2);
    let old = handoff(&mut state, id, 1);
    let new = handoff(&mut state, demands[0].order_id, 1);
    crate::complete_household_orders(&mut state, &mut demands, &[old, new], &mut transfers)
        .expect("the fixture completes the authored orders");
    assert_eq!(household_rows(&mut state).household_stocks[0].quantity, 2);
    assert_eq!(state.final_demand_orders.len(), 1);
    assert_eq!(state.final_demand_orders[0].order_id, id);
    assert_eq!(
        economy(&mut state)
            .book
            .purchase(OutboundOrderId::LocalFinalDemand(id))
            .expect("the fixture purchase is present")
            .reserved_amount()
            .expect("the fixture reservation exists"),
        cash(4)
    );
}

#[test]
fn missing_or_overflowing_needs_and_invalid_prices_are_refused() {
    let (catalog, mut state) = opening(16, 0);
    super::validate(&catalog, &state).expect("the authored fixture passes validation");
    household_rows(&mut state).household_needs[0].units_per_basis = u64::MAX;
    assert_eq!(
        super::validate(&catalog, &state),
        Err(MaterialCircuitError::Arithmetic)
    );
    let before = state.clone();
    assert_eq!(
        crate::admit_household_orders(&catalog, &mut state, &mut vec![]),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(state, before);
    let (catalog, mut state) = opening(16, 0);
    household_rows(&mut state).offers[0].unit_price = cash(0);
    assert_eq!(
        super::validate(&catalog, &state),
        Err(MaterialCircuitError::PurchaseInvariant)
    );
    let (catalog, mut state) = opening(16, 0);
    household_rows(&mut state).household_stocks.clear();
    assert_eq!(
        super::validate(&catalog, &state),
        Err(MaterialCircuitError::FinalDemandInvariant)
    );
}

#[test]
fn one_household_budget_is_shared_in_canonical_need_order() {
    let (mut catalog, mut state) = opening(4, 0);
    let other = GoodId::from_bytes([33; 32]);
    catalog.commodities.push(CommodityDefinition {
        good_id: other,
        unit_id: u(),
        kind: crate::CommodityKind::Storable { grams_per_unit: 1 },
    });
    catalog
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
        basis: HouseholdNeedBasis::Persons,
        units_per_basis: 1,
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
    crate::canonicalize(household_rows(&mut reordered));
    let first = crate::admit_household_orders(&catalog, &mut state, &mut vec![])
        .expect("the fixture admits the household orders");
    let second = crate::admit_household_orders(&catalog, &mut reordered, &mut vec![])
        .expect("the fixture admits the household orders");
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
            .expect("the fixture book holds the payer account"),
        cash(0)
    );
}

#[test]
fn consumption_cannot_skip_an_unresolved_generated_order() {
    let (catalog, mut state) = opening(16, 0);
    crate::admit_household_orders(&catalog, &mut state, &mut vec![])
        .expect("the fixture admits the household orders");
    let before = state.clone();
    assert_eq!(
        crate::consume_household_needs(&mut state),
        Err(MaterialCircuitError::PurchaseInvariant)
    );
    assert_eq!(state, before);
}
