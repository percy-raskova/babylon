//! Qualification rejects presence, promises and unmatched payments as trade evidence.
#[path = "support/national_trade_accounting.rs"]
mod national_trade_accounting;

use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    recurring_procurement_order_id, AccountId, DeliveryReceipt, FreightLossReceipt, FreightLotId,
    GoodId, MoneyLocation, MoneyPosting, MoneyTransferPurpose, MoneyTransferReceipt,
    OutboundOrderId, ProcessId, ProcurementReceipt, ProductionReceipt, RealizationReceipt, RouteId,
    SiteId, UnitId,
};
use babylon_persistence::production_observation::ProductionSite;
use babylon_tick::material_world::MaterialTickReceipts;
use national_trade_accounting::{Audit, Refusal};

fn site(id: u8, location: &str) -> ProductionSite {
    ProductionSite {
        id: national_trade_accounting::hex(&[id; 32]),
        location: location.parse().unwrap(),
        name: location.into(),
        industry_code: None,
        observed_employment: None,
        roles: vec![],
        sector_code: None,
        function: "manufacturing".into(),
        processes: vec![],
        inventory: vec![],
    }
}
fn sites() -> Vec<ProductionSite> {
    vec![site(1, "county:26163"), site(2, "foreign:canada")]
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
fn procurement(period: u64, supplier: u8, buyer: u8) -> ProcurementReceipt {
    let supplier_site_id = SiteId::from_bytes([supplier; 32]);
    let buyer_site_id = SiteId::from_bytes([buyer; 32]);
    let good_id = GoodId::from_bytes([3; 32]);
    let unit_id = UnitId::from_bytes([4; 32]);
    ProcurementReceipt {
        period,
        order_id: recurring_procurement_order_id(
            period,
            buyer_site_id,
            supplier_site_id,
            good_id,
            unit_id,
        ),
        buyer_site_id,
        supplier_site_id,
        good_id,
        unit_id,
        on_hand: 0,
        outstanding_inbound: 0,
        target_stock: 5,
        desired_quantity: 5,
        admitted_quantity: 5,
        unit_price: Currency::from_micro_units(7),
    }
}
fn settle(rows: &mut MaterialTickReceipts, order: &ProcurementReceipt, quantity: u64) {
    rows.deliveries.push(DeliveryReceipt {
        order_id: order.order_id,
        quantity,
    });
    rows.realizations.push(RealizationReceipt {
        order_id: order.order_id,
        quantity,
    });
    let amount = i128::from(quantity) * order.unit_price.micro_units();
    let id = OutboundOrderId::Delivery(order.order_id);
    rows.money_transfers.push(MoneyTransferReceipt {
        purpose: MoneyTransferPurpose::DeliverySettlement(id),
        debit: MoneyPosting {
            location: MoneyLocation::PurchaseReserve(id),
            delta: Currency::from_micro_units(-amount),
        },
        credit: MoneyPosting {
            location: MoneyLocation::Cash(AccountId::Site(order.supplier_site_id)),
            delta: Currency::from_micro_units(amount),
        },
    });
}
fn admit(rows: &mut MaterialTickReceipts, order: ProcurementReceipt) {
    if order.admitted_quantity > 0 {
        let amount = i128::from(order.admitted_quantity) * order.unit_price.micro_units();
        let id = OutboundOrderId::Delivery(order.order_id);
        rows.money_transfers.push(MoneyTransferReceipt {
            purpose: MoneyTransferPurpose::PurchaseReservation(id),
            debit: MoneyPosting {
                location: MoneyLocation::Cash(AccountId::Site(order.buyer_site_id)),
                delta: Currency::from_micro_units(-amount),
            },
            credit: MoneyPosting {
                location: MoneyLocation::PurchaseReserve(id),
                delta: Currency::from_micro_units(amount),
            },
        });
    }
    rows.procurement.push(order);
}
fn lose(rows: &mut MaterialTickReceipts, order: &ProcurementReceipt, quantity: u64) {
    rows.losses.push(FreightLossReceipt {
        lot_id: FreightLotId::from_bytes([9; 32]),
        order_id: order.order_id,
        route_id: RouteId::from_bytes([10; 32]),
        stage_index: 0,
        quantity,
    });
    let amount = i128::from(quantity) * order.unit_price.micro_units();
    let id = OutboundOrderId::Delivery(order.order_id);
    rows.money_transfers.push(MoneyTransferReceipt {
        purpose: MoneyTransferPurpose::PurchaseRefund(id),
        debit: MoneyPosting {
            location: MoneyLocation::PurchaseReserve(id),
            delta: Currency::from_micro_units(-amount),
        },
        credit: MoneyPosting {
            location: MoneyLocation::Cash(AccountId::Site(order.buyer_site_id)),
            delta: Currency::from_micro_units(amount),
        },
    });
}
fn awaiting_import() -> (Audit, ProcurementReceipt) {
    let mut audit = Audit::default();
    let import = procurement(1, 2, 1);
    let mut opening = receipts(1);
    admit(&mut opening, import.clone());
    foreign_production(&mut opening);
    audit.read(&opening, &sites()).unwrap();
    (audit, import)
}
fn foreign_production(rows: &mut MaterialTickReceipts) {
    rows.production.push(ProductionReceipt {
        process_id: ProcessId::from_bytes([8; 32]),
        site_id: SiteId::from_bytes([2; 32]),
        planned_batches: 1,
        produced_batches: 1,
    });
}

#[test]
fn settled_bidirectional_trade_and_actual_foreign_production_are_required() {
    let mut audit = Audit::default();
    let import = procurement(1, 2, 1);
    let export = procurement(1, 1, 2);
    let mut opening = receipts(1);
    admit(&mut opening, import.clone());
    admit(&mut opening, export.clone());
    foreign_production(&mut opening);
    audit.read(&opening, &sites()).unwrap();
    assert_eq!(audit.report()["status"], "incomplete");
    let mut arrival = receipts(2);
    settle(&mut arrival, &import, 2);
    audit.read(&arrival, &sites()).unwrap();
    assert_eq!(audit.report()["status"], "incomplete");
    let mut later = receipts(3);
    settle(&mut later, &export, 5);
    settle(&mut later, &import, 3);
    audit.read(&later, &sites()).unwrap();
    let report = audit.report();
    assert_eq!(report["status"], "passed");
    assert_eq!(report["imports"]["settled_deliveries"], 2);
    assert_eq!(report["exports"]["settled_deliveries"], 1);
    assert_eq!(report["imports"]["settled_cash_micros"], "35");
    assert_eq!(report["exports"]["settled_cash_micros"], "35");
    assert_eq!(report["unresolved_trade_orders"], 0);
}

#[test]
fn counterpart_presence_and_planned_production_are_not_execution() {
    let mut audit = Audit::default();
    let mut period = receipts(1);
    foreign_production(&mut period);
    period.production[0].produced_batches = 0;
    audit.read(&period, &sites()).unwrap();
    assert_eq!(audit.report()["status"], "incomplete");
    assert_eq!(audit.report()["positive_foreign_production_receipts"], 0);
    assert_eq!(audit.report()["imports"]["settled_deliveries"], 0);
    assert_eq!(audit.report()["exports"]["settled_deliveries"], 0);
}

#[test]
fn stocked_trade_in_both_directions_cannot_substitute_for_foreign_production() {
    let mut audit = Audit::default();
    let import = procurement(1, 2, 1);
    let export = procurement(1, 1, 2);
    let mut opening = receipts(1);
    admit(&mut opening, import.clone());
    admit(&mut opening, export.clone());
    audit.read(&opening, &sites()).unwrap();
    let mut arrival = receipts(2);
    settle(&mut arrival, &import, 5);
    settle(&mut arrival, &export, 5);
    audit.read(&arrival, &sites()).unwrap();
    let report = audit.report();
    assert_eq!(report["imports"]["settled_deliveries"], 1);
    assert_eq!(report["exports"]["settled_deliveries"], 1);
    assert_eq!(report["positive_foreign_production_receipts"], 0);
    assert_eq!(report["status"], "incomplete");
}

#[test]
fn balanced_but_wrong_price_account_or_realization_cannot_count_as_trade() {
    let (mut audit, import) = awaiting_import();
    let before = audit.report();
    let mut valid = receipts(2);
    settle(&mut valid, &import, 2);
    let mut wrong_price = valid.clone();
    wrong_price.money_transfers[0].credit.delta = Currency::from_micro_units(13);
    wrong_price.money_transfers[0].debit.delta = Currency::from_micro_units(-13);
    let mut wrong_account = valid.clone();
    wrong_account.money_transfers[0].credit.location =
        MoneyLocation::Cash(AccountId::Site(import.buyer_site_id));
    let mut unbalanced = valid.clone();
    unbalanced.money_transfers[0].debit.delta = Currency::from_micro_units(-13);
    let mut missing_payment = valid.clone();
    missing_payment.money_transfers.clear();
    let mut duplicated_payment = valid.clone();
    duplicated_payment
        .money_transfers
        .push(duplicated_payment.money_transfers[0].clone());
    let mut missing_realization = valid.clone();
    missing_realization.realizations.clear();
    for (bad, error) in [
        (wrong_price, Refusal::Settlement),
        (wrong_account, Refusal::Settlement),
        (unbalanced, Refusal::Settlement),
        (missing_payment, Refusal::Settlement),
        (duplicated_payment, Refusal::Settlement),
        (missing_realization, Refusal::Quantity),
    ] {
        assert_eq!(audit.read(&bad, &sites()), Err(error));
        assert_eq!(
            audit.report(),
            before,
            "failed audit cannot publish partial evidence"
        );
    }
    audit.read(&valid, &sites()).unwrap();
    assert_eq!(audit.report()["imports"]["settled_cash_micros"], "14");
}

#[test]
fn new_orders_require_real_reservations_and_keep_their_admission_price() {
    let import = procurement(1, 2, 1);
    let mut opening = receipts(1);
    admit(&mut opening, import.clone());
    let mut missing = opening.clone();
    missing.money_transfers.clear();
    assert_eq!(
        Audit::default().read(&missing, &sites()),
        Err(Refusal::Reservation)
    );
    let mut audit = Audit::default();
    audit.read(&opening, &sites()).unwrap();
    let mut later = receipts(2);
    let mut changed_quote = import.clone();
    changed_quote.unit_price = Currency::from_micro_units(9);
    settle(&mut later, &changed_quote, 1);
    assert_eq!(audit.read(&later, &sites()), Err(Refusal::Settlement));
    later = receipts(2);
    settle(&mut later, &import, 1);
    audit.read(&later, &sites()).unwrap();
    assert_eq!(audit.report()["imports"]["settled_cash_micros"], "7");
}

#[test]
fn partial_delivery_and_loss_refund_retire_terms_without_counting_refunds_as_sales() {
    let (mut audit, import) = awaiting_import();
    let before = audit.report();
    let mut arrival = receipts(2);
    settle(&mut arrival, &import, 2);
    lose(&mut arrival, &import, 3);
    let mut wrong_refund = arrival.clone();
    wrong_refund.money_transfers[1].credit.location =
        MoneyLocation::Cash(AccountId::Site(import.supplier_site_id));
    assert_eq!(audit.read(&wrong_refund, &sites()), Err(Refusal::Refund));
    assert_eq!(audit.report(), before);
    let mut missing_refund = arrival.clone();
    missing_refund.money_transfers.pop();
    assert_eq!(audit.read(&missing_refund, &sites()), Err(Refusal::Refund));
    assert_eq!(audit.report(), before);
    audit.read(&arrival, &sites()).unwrap();
    assert_eq!(audit.report()["imports"]["settled_cash_micros"], "14");
    assert_eq!(audit.report()["unresolved_trade_orders"], 0);
}

#[test]
fn wholly_lost_goods_never_qualify_as_delivered_trade() {
    let (mut audit, import) = awaiting_import();
    let mut period = receipts(2);
    lose(&mut period, &import, 5);
    audit.read(&period, &sites()).unwrap();
    assert_eq!(audit.report()["imports"]["settled_deliveries"], 0);
    assert_eq!(audit.report()["imports"]["settled_cash_micros"], "0");
    assert_eq!(audit.report()["unresolved_trade_orders"], 0);
    assert_eq!(audit.report()["status"], "incomplete");
}

#[test]
fn zero_admissions_remain_unfunded_and_duplicate_or_retired_ids_are_refused() {
    let mut zero = procurement(1, 2, 1);
    zero.admitted_quantity = 0;
    let mut empty = receipts(1);
    admit(&mut empty, zero.clone());
    let mut audit = Audit::default();
    audit.read(&empty, &sites()).unwrap();
    assert_eq!(audit.report()["unresolved_trade_orders"], 0);
    empty.procurement.push(zero);
    assert_eq!(
        Audit::default().read(&empty, &sites()),
        Err(Refusal::DuplicateOrder)
    );
    let (mut audit, import) = awaiting_import();
    let mut arrival = receipts(2);
    settle(&mut arrival, &import, 5);
    audit.read(&arrival, &sites()).unwrap();
    let mut stale = receipts(3);
    let mut replayed = import;
    replayed.period = 3;
    admit(&mut stale, replayed);
    assert_eq!(
        audit.read(&stale, &sites()),
        Err(Refusal::ProcurementIdentity)
    );
    assert_eq!(audit.report()["periods"], 2);
    assert_eq!(audit.report()["unresolved_trade_orders"], 0);
}

#[test]
fn conflicting_admissions_and_unexplained_refunds_or_topups_are_refused() {
    let import = procurement(1, 2, 1);
    let mut conflict = receipts(1);
    admit(&mut conflict, import.clone());
    let mut repriced = import.clone();
    repriced.unit_price = Currency::from_micro_units(8);
    admit(&mut conflict, repriced);
    assert_eq!(
        Audit::default().read(&conflict, &sites()),
        Err(Refusal::DuplicateOrder)
    );
    let (mut audit, import) = awaiting_import();
    let before = audit.report();
    let mut unexplained = receipts(2);
    lose(&mut unexplained, &import, 1);
    unexplained.losses.clear();
    assert_eq!(audit.read(&unexplained, &sites()), Err(Refusal::Refund));
    assert_eq!(audit.report(), before);
    let mut topup = receipts(2);
    admit(&mut topup, import);
    topup.procurement.clear();
    assert_eq!(audit.read(&topup, &sites()), Err(Refusal::Reservation));
    assert_eq!(audit.report(), before);
}

#[test]
fn dependencies_and_unknown_or_duplicate_sites_cannot_become_foreign_trade() {
    let mut period = receipts(1);
    let import = procurement(1, 2, 1);
    admit(&mut period, import);
    foreign_production(&mut period);
    let dependent = vec![site(1, "county:26163"), site(2, "dependency:630")];
    let mut audit = Audit::default();
    audit.read(&period, &dependent).unwrap();
    assert_eq!(audit.report()["positive_foreign_production_receipts"], 0);
    assert_eq!(audit.report()["unresolved_trade_orders"], 0);
    let mut audit = Audit::default();
    assert_eq!(
        audit.read(&period, &[site(1, "county:26163")]),
        Err(Refusal::MissingSite)
    );
    let mut duplicate = sites();
    duplicate.push(duplicate[0].clone());
    assert_eq!(audit.read(&period, &duplicate), Err(Refusal::SiteIdentity));
    assert_eq!(audit.report()["periods"], 0);
}

#[test]
fn excessive_delivery_overflow_and_skipped_periods_leave_evidence_unchanged() {
    let (mut audit, import) = awaiting_import();
    let before = audit.report();
    let mut excess = receipts(2);
    settle(&mut excess, &import, 6);
    assert_eq!(audit.read(&excess, &sites()), Err(Refusal::Quantity));
    assert_eq!(audit.report(), before);
    assert_eq!(audit.read(&receipts(3), &sites()), Err(Refusal::Period));
    assert_eq!(audit.report(), before);
    let mut overflow = receipts(1);
    admit(&mut overflow, procurement(1, 2, 1));
    overflow.procurement[0].unit_price = Currency::from_micro_units(i128::MAX);
    assert_eq!(
        Audit::default().read(&overflow, &sites()),
        Err(Refusal::Overflow)
    );
}
