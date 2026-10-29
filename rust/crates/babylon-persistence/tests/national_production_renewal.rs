//! Conservative terminal-window witness controls; these do not change mechanics.
use babylon_kernel::currency::Currency;
use babylon_material_circuit::CapacityReservations;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::FreightLotId;
use babylon_material_circuit::GoodId;
use babylon_material_circuit::LaborCoefficient;
use babylon_material_circuit::OrderId;
use babylon_material_circuit::ProcessId;
use babylon_material_circuit::RouteId;
use babylon_material_circuit::SiteId;
use babylon_material_circuit::UnitId;
use babylon_material_circuit::{
    AccountId, AidBook, AidOutcome, AidReceipt, AidTransport, ArrivalReceipt, CapacitySupply,
    CashAccount, CircuitAccounting, CommodityDefinition, CommodityKind, DeliveryReceipt,
    FinancialInstitutions, HistoricalCostBook, HouseholdConsumptionReceipt, HouseholdDemandReceipt,
    HouseholdPurchasePolicy, HouseholdStock, HouseholdTimeAccounting, InventoryRow,
    LocalRetailFulfillmentReceipt, LocalTransferReceipt, MaterialCatalog, MaterialCircuitState,
    MonetaryBook, MonetaryCircuit, MoneyLocation, MoneyPosting, MoneyTransferPurpose,
    MoneyTransferReceipt, OrderAccessMode, OrderRow, OutboundOrderId, ProcessOutput,
    ProcurementReceipt, ProductionReceipt, PurchaseEscrow, RealizationReceipt, RecurringEconomy,
    ReplenishmentPolicy, RoutedFreightLot,
};
use babylon_persistence::qualification_audit::production_renewal as national_production_renewal;
use babylon_tick::material_world::MaterialTickReceipts;
use national_production_renewal::{Audit, Refusal};
fn site(n: u8) -> SiteId {
    SiteId::from_bytes([n; 32])
}
fn good() -> GoodId {
    GoodId::from_bytes([3; 32])
}
fn unit() -> UnitId {
    UnitId::from_bytes([4; 32])
}
fn household() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([5; 32])
}
fn process() -> ProcessId {
    ProcessId::from_bytes([6; 32])
}
fn money(n: i128) -> Currency {
    Currency::from_micro_units(n)
}
fn receipts(period: u64) -> MaterialTickReceipts {
    MaterialTickReceipts {
        household_time: vec![],
        aid: vec![],
        collections: vec![],
        installation: vec![],
        installation_decisions: vec![],
        equipment_wear: vec![],
        investment: vec![],
        staffing_members: vec![],
        member_labor_use: vec![],
        public_budgets: vec![],
        taxes: vec![],
        distributions: vec![],
        contributions: vec![],
        service_performance: vec![],
        household_services: vec![],
        service_markets: vec![],
        service_outputs: vec![],
        income: vec![],
        resolve_tick: period,
        household_demand: vec![],
        household_consumption: vec![],
        procurement: vec![],
        production_plans: vec![],
        prices: vec![],
        money_transfers: vec![],
        wage_accruals: vec![],
        labor_use: vec![],
        production: vec![],
        dispatches: vec![],
        losses: vec![],
        arrivals: vec![],
        deliveries: vec![],
        realizations: vec![],
        handling: vec![],
        local_fulfillments: vec![],
        local_transfers: vec![],
        maintenance: None,
    }
}
fn recurring(retailer: u8) -> RecurringEconomy {
    RecurringEconomy {
        households: vec![],
        household_stocks: vec![],
        household_purchases: vec![HouseholdPurchasePolicy {
            principal_id: household(),
            retailer_site_id: site(retailer),
            good_id: good(),
            unit_id: unit(),
            target_closing_stock: 0,
            maximum_purchase: 100,
            enabled: true,
        }],
        offers: vec![],
        replenishment: vec![ReplenishmentPolicy {
            buyer_site_id: site(retailer),
            supplier_site_id: site(1),
            good_id: good(),
            unit_id: unit(),
            target_stock: 10,
            maximum_purchase: 100,
            cash_floor: money(0),
        }],
        production: vec![],
        attendance: vec![],
        last_household_admission_period: 39,
        last_household_consumption_period: 39,
    }
}
fn accounting(retailer: u8) -> CircuitAccounting {
    let book = MonetaryBook::open(
        [
            AccountId::Site(site(1)),
            AccountId::Site(site(2)),
            AccountId::Site(site(3)),
            AccountId::Household(household()),
        ]
        .into_iter()
        .map(|id| CashAccount {
            id,
            cash: money(100),
        })
        .collect(),
    )
    .expect("the fixture opens the authored source");
    let costs = HistoricalCostBook::open(&book, vec![], vec![], vec![], vec![])
        .expect("the fixture opens the authored source");
    CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
        aid: AidBook::default(),
        household_time: HouseholdTimeAccounting::NotModeled,
        financial: FinancialInstitutions::empty(),
        member_labor: vec![],
        costs,
        book,
        recurring: Some(Box::new(recurring(retailer))),
        employment: vec![],
    }))
}
fn seed(retailer: u8, opening: u64) -> (MaterialCatalog, MaterialCircuitState) {
    let catalog = MaterialCatalog::try_new(babylon_material_circuit::MaterialCatalogDefinition {
        capacity_policy: CapacitySupply::FiniteSchedule,
        site_logistics_nodes: vec![],
        process_outputs: vec![ProcessOutput {
            process_id: process(),
            site_id: site(1),
            good_id: good(),
            unit_id: unit(),
            quantity_per_batch: 1,
        }],
        input_coefficients: vec![],
        labor_coefficients: vec![LaborCoefficient {
            process_id: process(),
            unit_id: unit(),
            quantity_per_batch: 1,
        }],
        commodities: vec![CommodityDefinition {
            good_id: good(),
            unit_id: unit(),
            kind: CommodityKind::Storable { grams_per_unit: 1 },
        }],
        supplier_routes: vec![],
        route_stages: vec![],
        merchants: vec![],
        handling_coefficients: vec![],
        maintenance_binding: None,
        aid_mandates: vec![],
        household_time_policy: vec![],
        service_inputs: vec![],
        household_needs: vec![],
    })
    .expect("the fixture catalog canonicalizes");
    let state = MaterialCircuitState {
        period: 40,
        accounting: accounting(retailer),
        service_connections: vec![],
        service_orders: vec![],
        route_stage_capacities: vec![],
        inventory: vec![InventoryRow {
            site_id: site(1),
            good_id: good(),
            unit_id: unit(),
            quantity: opening,
        }],
        orders: vec![],
        freight: vec![],
        corridor_capacities: vec![],
        capacities: vec![],
        labor: vec![],
        production_commitments: vec![],
        final_demand_principals: vec![],
        final_demand_orders: vec![],
        maintenance_service: None,
        capacity_reservations: CapacityReservations::default(),
    };
    (catalog, state)
}
fn transfer(
    r: &mut MaterialTickReceipts,
    purpose: MoneyTransferPurpose,
    from: MoneyLocation,
    to: MoneyLocation,
    q: u64,
) {
    if q == 0 {
        return;
    }
    r.money_transfers.push(MoneyTransferReceipt {
        purpose,
        debit: MoneyPosting {
            location: from,
            delta: money(-i128::from(q)),
        },
        credit: MoneyPosting {
            location: to,
            delta: money(i128::from(q)),
        },
    });
}
fn purchase(
    r: &mut MaterialTickReceipts,
    id: OutboundOrderId,
    buyer: AccountId,
    seller: AccountId,
    q: u64,
) {
    let reserve = MoneyLocation::PurchaseReserve(id);
    transfer(
        r,
        MoneyTransferPurpose::PurchaseReservation(id),
        MoneyLocation::Cash(buyer),
        reserve,
        q,
    );
    transfer(
        r,
        MoneyTransferPurpose::DeliverySettlement(id),
        reserve,
        MoneyLocation::Cash(seller),
        q,
    );
}
fn retail(r: &mut MaterialTickReceipts, retailer: u8, q: u64) {
    let order_id = babylon_material_circuit::recurring_household_order_id(
        r.resolve_tick,
        (household(), good(), unit()),
    );
    r.household_demand.push(HouseholdDemandReceipt {
        period: r.resolve_tick,
        principal_id: household(),
        retailer_site_id: site(retailer),
        good_id: good(),
        unit_id: unit(),
        order_id,
        opening_stock: 0,
        required_quantity: q,
        desired_quantity: q,
        requested_quantity: q,
        admitted_quantity: q,
        fulfilled_quantity: q,
        expired_quantity: 0,
        unit_price: money(1),
    });
    r.local_fulfillments.push(LocalRetailFulfillmentReceipt {
        order_id,
        retailer_site_id: site(retailer),
        demand_principal_id: household(),
        good_id: good(),
        unit_id: unit(),
        quantity: q,
    });
    r.household_consumption.push(HouseholdConsumptionReceipt {
        period: r.resolve_tick,
        principal_id: household(),
        good_id: good(),
        unit_id: unit(),
        required_quantity: q,
        available_quantity: q,
        consumed_quantity: q,
        unmet_quantity: 0,
        closing_quantity: 0,
    });
    purchase(
        r,
        OutboundOrderId::LocalFinalDemand(order_id),
        AccountId::Household(household()),
        AccountId::Site(site(retailer)),
        q,
    );
}
fn output(r: &mut MaterialTickReceipts, q: u64) {
    r.production.push(ProductionReceipt {
        process_id: process(),
        site_id: site(1),
        planned_batches: q,
        produced_batches: q,
    });
}
fn supply(r: &mut MaterialTickReceipts, supplier: u8, q: u64, local: bool) {
    let order_id = babylon_material_circuit::recurring_procurement_order_id(
        r.resolve_tick,
        site(2),
        site(supplier),
        good(),
        unit(),
    );
    r.procurement.push(ProcurementReceipt {
        period: r.resolve_tick,
        order_id,
        buyer_site_id: site(2),
        supplier_site_id: site(supplier),
        good_id: good(),
        unit_id: unit(),
        on_hand: 0,
        outstanding_inbound: 0,
        target_stock: q,
        desired_quantity: q,
        admitted_quantity: q,
        unit_price: money(1),
    });
    if local {
        r.local_transfers.push(LocalTransferReceipt {
            order_id,
            supplier_site_id: site(supplier),
            buyer_site_id: site(2),
            good_id: good(),
            unit_id: unit(),
            quantity: q,
        });
    } else {
        r.arrivals.push(ArrivalReceipt {
            order_id,
            quantity: q,
        });
        r.deliveries.push(DeliveryReceipt {
            order_id,
            quantity: q,
        });
        r.realizations.push(RealizationReceipt {
            order_id,
            quantity: q,
        });
    }
    purchase(
        r,
        OutboundOrderId::Delivery(order_id),
        AccountId::Site(site(2)),
        AccountId::Site(site(supplier)),
        q,
    );
}
#[test]
fn opening_stock_only_has_no_production_renewal() {
    let mut audit = Audit::seed(&seed(1, 10).0, &seed(1, 10).1, 39, [7; 32])
        .expect("the fixture seeds the authored rows");
    let mut r = receipts(40);
    retail(&mut r, 1, 10);
    let e = audit
        .read(&r)
        .expect("the fixture reader returns its authored facts");
    assert_eq!(e.proven_consumed, 0);
    assert_eq!(e.status, "incomplete");
}
#[test]
fn renewed_output_reaches_paid_households_through_local_and_routed_supply() {
    for local in [true, false] {
        let mut audit = Audit::seed(&seed(2, 0).0, &seed(2, 0).1, 39, [7; 32])
            .expect("the fixture seeds the authored rows");
        let mut r = receipts(40);
        output(&mut r, 10);
        supply(&mut r, 1, 10, local);
        assert_eq!(
            audit
                .read(&r)
                .expect("the fixture reader returns its authored facts")
                .proven_consumed,
            0
        );
        let mut next = receipts(41);
        retail(&mut next, 2, 10);
        let e = audit
            .read(&next)
            .expect("the fixture reader returns its authored facts");
        assert_eq!(e.proven_consumed, 10);
        assert_eq!(e.pending_orders, 0);
        assert_eq!((e.seed_period, e.through_period), (39, 41));
    }
}
#[test]
fn receipt_order_does_not_attribute_lots_or_change_window_bound() {
    let (catalog, state) = seed(2, 0);
    let mut a =
        Audit::seed(&catalog, &state, 39, [7; 32]).expect("the fixture seeds the authored rows");
    let mut b = a.clone();
    let mut r = receipts(40);
    output(&mut r, 10);
    supply(&mut r, 1, 10, true);
    supply(&mut r, 3, 4, false);
    retail(&mut r, 2, 10);
    let expected = a
        .read(&r)
        .expect("the fixture reader returns its authored facts");
    r.procurement.reverse();
    r.money_transfers.reverse();
    r.deliveries.reverse();
    assert_eq!(
        b.read(&r)
            .expect("the fixture reader returns its authored facts"),
        expected
    );
    assert_eq!(expected.proven_consumed, 6);
}
#[test]
fn unknown_incoming_stock_cannot_supply_a_positive_production_claim() {
    let mut audit = Audit::seed(&seed(2, 0).0, &seed(2, 0).1, 39, [7; 32])
        .expect("the fixture seeds the authored rows");
    let mut r = receipts(40);
    output(&mut r, 10);
    supply(&mut r, 1, 10, true);
    supply(&mut r, 3, 10, false);
    retail(&mut r, 2, 10);
    assert_eq!(
        audit
            .read(&r)
            .expect("the fixture reader returns its authored facts")
            .proven_consumed,
        0
    );
}
#[test]
fn payment_and_crossed_units_refuse_without_publishing_candidate() {
    let (catalog, state) = seed(2, 0);
    let mut audit =
        Audit::seed(&catalog, &state, 39, [7; 32]).expect("the fixture seeds the authored rows");
    let before = audit
        .evidence()
        .expect("the fixture call `evidence` succeeds for the authored inputs");
    let mut r = receipts(40);
    output(&mut r, 10);
    supply(&mut r, 1, 10, true);
    retail(&mut r, 2, 10);
    r.local_transfers[0].unit_id = UnitId::from_bytes([9; 32]);
    assert_eq!(
        audit
            .read(&r)
            .expect_err("the malformed read request is refused"),
        Refusal::Unit
    );
    assert_eq!(
        audit
            .evidence()
            .expect("the fixture call `evidence` succeeds for the authored inputs"),
        before
    );
    r.local_transfers[0].unit_id = unit();
    r.money_transfers.pop();
    assert_eq!(
        audit
            .read(&r)
            .expect_err("the malformed read request is refused"),
        Refusal::Payment
    );
    assert_eq!(
        audit
            .evidence()
            .expect("the fixture call `evidence` succeeds for the authored inputs"),
        before
    );
}
#[test]
fn no_usable_producer_is_explicitly_incomplete() {
    let (catalog, state) = seed(2, 0);
    let mut catalog = catalog.into_definition();
    catalog.process_outputs.clear();
    catalog.labor_coefficients.clear();
    let catalog = MaterialCatalog::try_new(catalog).expect("valid definitions");
    assert_eq!(
        Audit::seed(&catalog, &state, 39, [7; 32])
            .expect("the fixture seeds the authored rows")
            .evidence()
            .expect("the fixture call `evidence` succeeds for the authored inputs")
            .status,
        "no_usable_chain"
    );
}

#[test]
fn aid_and_initial_household_stock_are_unproven_consumption_allowances() {
    let (catalog, mut state) = seed(1, 0);
    let CircuitAccounting::Monetary(book) = &mut state.accounting else {
        panic!("monetary fixture");
    };
    book.recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .household_stocks
        .push(HouseholdStock {
            principal_id: household(),
            good_id: good(),
            unit_id: unit(),
            quantity: 4,
        });
    let mut audit =
        Audit::seed(&catalog, &state, 39, [7; 32]).expect("the fixture seeds the authored rows");
    let mut r = receipts(40);
    output(&mut r, 10);
    retail(&mut r, 1, 10);
    r.aid.push(AidReceipt {
        commitment_id: OrderId::from_bytes([8; 32]),
        mandate_id: [8; 32],
        period: 40,
        dispatch_period: 40,
        transport: AidTransport::Local,
        payer: AccountId::Household(household()),
        donor: FinalDemandPrincipalId::from_bytes([8; 32]),
        recipient: household(),
        good_id: good(),
        unit_id: unit(),
        outcome: AidOutcome::Granted,
        quantity: 6,
        carrying_amount: money(0),
        cash_amount: money(0),
        contribution_hours: 0,
    });
    let e = audit
        .read(&r)
        .expect("the fixture reader returns its authored facts");
    assert_eq!(e.proven_consumed, 0);
    assert_eq!(e.household_unproven_allowance, 10);
}
#[test]
fn direct_producer_retailer_needs_paid_handoff_and_actual_consumption() {
    let (catalog, state) = seed(1, 3);
    let mut audit =
        Audit::seed(&catalog, &state, 39, [7; 32]).expect("the fixture seeds the authored rows");
    let mut r = receipts(40);
    output(&mut r, 10);
    retail(&mut r, 1, 10);
    let e = audit
        .read(&r)
        .expect("the fixture reader returns its authored facts");
    assert_eq!(e.proven_consumed, 7);
    assert!(
        e.selection
            .expect("the fixture observation carries its selection")
            .direct_producer_retailer
    );
}

#[test]
fn seed_transit_is_an_allowance_once() {
    let (catalog, mut state) = seed(2, 0);
    let id = babylon_material_circuit::recurring_procurement_order_id(
        39,
        site(2),
        site(3),
        good(),
        unit(),
    );
    let CircuitAccounting::Monetary(book) = &mut state.accounting else {
        panic!("monetary fixture");
    };
    book.book
        .reserve_purchase(
            PurchaseEscrow::new(
                OutboundOrderId::Delivery(id),
                AccountId::Site(site(2)),
                AccountId::Site(site(3)),
                10,
                money(1),
            )
            .expect("the constructor accepts the authored fixture arguments"),
        )
        .expect("the fixture reserve admits the purchase");
    state.orders.push(OrderRow {
        order_id: id,
        access_mode: OrderAccessMode::CommoditySale,
        buyer_site_id: site(2),
        supplier_site_id: site(3),
        good_id: good(),
        unit_id: unit(),
        ordered: 10,
        shipped: 10,
        lost: 0,
        delivered: 0,
        realized: 0,
    });
    state.freight.push(RoutedFreightLot {
        lot_id: FreightLotId::from_bytes([9; 32]),
        order_id: id,
        route_id: RouteId::from_bytes([9; 32]),
        dispatch_period: 39,
        current_stage_index: 0,
        stage_arrival_period: 40,
        source_site_id: site(3),
        destination_site_id: site(2),
        good_id: good(),
        unit_id: unit(),
        quantity: 10,
    });
    let mut audit =
        Audit::seed(&catalog, &state, 39, [7; 32]).expect("the fixture seeds the authored rows");
    let mut r = receipts(40);
    output(&mut r, 20);
    supply(&mut r, 1, 20, true);
    retail(&mut r, 2, 30);
    r.arrivals.push(ArrivalReceipt {
        order_id: id,
        quantity: 10,
    });
    r.deliveries.push(DeliveryReceipt {
        order_id: id,
        quantity: 10,
    });
    r.realizations.push(RealizationReceipt {
        order_id: id,
        quantity: 10,
    });
    transfer(
        &mut r,
        MoneyTransferPurpose::DeliverySettlement(OutboundOrderId::Delivery(id)),
        MoneyLocation::PurchaseReserve(OutboundOrderId::Delivery(id)),
        MoneyLocation::Cash(AccountId::Site(site(3))),
        10,
    );
    let e = audit
        .read(&r)
        .expect("the fixture reader returns its authored facts");
    assert_eq!(e.retailer_unproven_allowance, 10);
    assert_eq!(e.proven_consumed, 20);
}
#[test]
fn noncontiguous_period_and_checked_overflow_refuse_atomically() {
    let (catalog, state) = seed(1, 0);
    let mut catalog = catalog.into_definition();
    catalog.process_outputs[0].quantity_per_batch = 2;
    let catalog = MaterialCatalog::try_new(catalog).expect("valid definitions");
    let mut audit =
        Audit::seed(&catalog, &state, 39, [7; 32]).expect("the fixture seeds the authored rows");
    let before = audit
        .evidence()
        .expect("the fixture call `evidence` succeeds for the authored inputs");
    assert_eq!(
        audit
            .read(&receipts(41))
            .expect_err("the malformed read request is refused"),
        Refusal::Period
    );
    let mut r = receipts(40);
    output(&mut r, u64::MAX);
    assert_eq!(
        audit
            .read(&r)
            .expect_err("the malformed read request is refused"),
        Refusal::Overflow
    );
    assert_eq!(
        audit
            .evidence()
            .expect("the fixture call `evidence` succeeds for the authored inputs"),
        before
    );
}

#[test]
fn omitted_ninth_output_cannot_borrow_later_retained_production() {
    let (catalog, state) = seed(1, 0);
    let mut catalog = catalog.into_definition();
    catalog.process_outputs = (1..=9)
        .map(|id| ProcessOutput {
            process_id: ProcessId::from_bytes([id; 32]),
            site_id: site(1),
            good_id: good(),
            unit_id: unit(),
            quantity_per_batch: 1,
        })
        .collect();
    catalog.labor_coefficients = catalog
        .process_outputs
        .iter()
        .map(|row| LaborCoefficient {
            process_id: row.process_id,
            unit_id: unit(),
            quantity_per_batch: 1,
        })
        .collect();
    let catalog = MaterialCatalog::try_new(catalog).expect("valid definitions");
    let mut audit =
        Audit::seed(&catalog, &state, 39, [7; 32]).expect("the fixture seeds the authored rows");
    let mut sold = receipts(40);
    sold.production.push(ProductionReceipt {
        process_id: ProcessId::from_bytes([9; 32]),
        site_id: site(1),
        planned_batches: 1,
        produced_batches: 1,
    });
    retail(&mut sold, 1, 1);
    assert_eq!(
        audit
            .read(&sold)
            .expect("the fixture reader returns its authored facts")
            .proven_consumed,
        0
    );
    let mut retained = receipts(41);
    retained.production.push(ProductionReceipt {
        process_id: ProcessId::from_bytes([1; 32]),
        site_id: site(1),
        planned_batches: 1,
        produced_batches: 1,
    });
    let e = audit
        .read(&retained)
        .expect("the fixture reader returns its authored facts");
    assert_eq!(e.proven_consumed, 0);
    assert_eq!(e.status, "no_usable_chain");
    assert!(e.selection.is_none());
    assert_eq!(e.through_period, 41);
}
