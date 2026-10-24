//! Focused joins reject promises, crossed units and unmatched cash.
use babylon_kernel::currency::Currency;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::GoodId;
use babylon_material_circuit::OrderId;
use babylon_material_circuit::ProcessId;
use babylon_material_circuit::SiteId;
use babylon_material_circuit::UnitId;
use babylon_material_circuit::{
    AccountId, ArrivalReceipt, CapitalContributionReceipt, CashTransferPurpose, ContributionId,
    DeliveryReceipt, DistributionReceipt, EquipmentCohortId, EquipmentWearReceipt,
    HouseholdConsumptionReceipt, HouseholdDemandReceipt, InstallationId, InstallationReceipt,
    InvestmentReceipt, LocalRetailFulfillmentReceipt, LocalTransferReceipt, MoneyLocation,
    MoneyPosting, MoneyTransferPurpose, MoneyTransferReceipt, OutboundOrderId, ProcurementReceipt,
    ProductionReceipt, RealizationReceipt, ShiftId, WageAccrualReceipt,
};
use babylon_persistence::qualification_audit::economic;
use babylon_tick::material_world::MaterialTickReceipts;
use economic::{Audit, Refusal};
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
        order_id: babylon_material_circuit::recurring_procurement_order_id(
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

fn money(n: i128) -> Currency {
    Currency::from_micro_units(n)
}
fn transfer(
    purpose: MoneyTransferPurpose,
    from: MoneyLocation,
    to: MoneyLocation,
    amount: i128,
) -> MoneyTransferReceipt {
    MoneyTransferReceipt {
        purpose,
        debit: MoneyPosting {
            location: from,
            delta: money(-amount),
        },
        credit: MoneyPosting {
            location: to,
            delta: money(amount),
        },
    }
}
fn investment(
    period: u64,
    site: SiteId,
    supplier: SiteId,
    process: ProcessId,
    order_id: OrderId,
) -> InvestmentReceipt {
    InvestmentReceipt {
        period,
        order_id,
        process_id: process,
        site_id: site,
        supplier_site_id: supplier,
        installed_units: 0,
        pending_units: 0,
        on_hand_units: 0,
        outstanding_inbound_units: 0,
        captured_plan_batches: 1,
        accepted_output_orders: 1,
        output_stock: 0,
        output_buffer: 0,
        replacement_requested_units: 1,
        expansion_requested_units: 0,
        admitted_units: 1,
        unit_price: money(7),
        free_cash: money(7),
        earnings_budget: money(0),
    }
}
fn installed(
    period: u64,
    id: InstallationId,
    site: SiteId,
    process: ProcessId,
) -> InstallationReceipt {
    InstallationReceipt {
        period,
        id,
        process_id: process,
        site_id: site,
        units: 1,
        started: true,
        opening_hours: 2,
        used_hours: 2,
        remaining_hours: 0,
        usable_from_period: period + 1,
        opening_carrying: money(0),
        materials_capitalized: money(7),
        wages_capitalized: money(2),
        closing_carrying: money(9),
    }
}
fn worked(
    period: u64,
    id: InstallationId,
    site: SiteId,
    process: ProcessId,
) -> MaterialTickReceipts {
    let mut r = receipts(period);
    r.equipment_wear.push(EquipmentWearReceipt {
        period,
        cohort_id: EquipmentCohortId::from_bytes(id.as_bytes()),
        process_id: process,
        site_id: site,
        opening_service_batches: 2,
        used_batches: 1,
        remaining_service_batches: 1,
        opening_carrying: money(9),
        carried_to_output: money(4),
        closing_carrying: money(5),
    });
    r.production.push(ProductionReceipt {
        process_id: process,
        site_id: site,
        planned_batches: 1,
        produced_batches: 1,
    });
    r
}
fn wages() -> MaterialTickReceipts {
    let mut r = receipts(1);
    let shift = ShiftId::from_bytes([7; 32]);
    let employer = AccountId::Site(SiteId::from_bytes([1; 32]));
    let payee = AccountId::Household(FinalDemandPrincipalId::from_bytes([2; 32]));
    r.money_transfers.push(transfer(
        MoneyTransferPurpose::ShiftReservation(shift),
        MoneyLocation::Cash(employer),
        MoneyLocation::PayrollReserve(shift),
        10,
    ));
    r.wage_accruals.push(WageAccrualReceipt {
        shift,
        employer,
        payee,
        period: 1,
        obligated_hours: 2,
        amount: money(10),
    });
    r.money_transfers.push(transfer(
        MoneyTransferPurpose::WagePayment(shift),
        MoneyLocation::PayrollReserve(shift),
        MoneyLocation::Cash(payee),
        10,
    ));
    r
}
#[test]
fn exact_wage_join_retires_and_missing_or_wrong_payment_is_not_evidence() {
    let r = wages();
    let mut audit = Audit::default();
    let f = audit.read(&r).unwrap();
    assert_eq!(f.funded_wages_paid_micros, "10");
    assert_eq!(f.pending_wages, 0);
    let mut changed = r.clone();
    changed.money_transfers[1].credit.location =
        MoneyLocation::Cash(AccountId::Site(SiteId::from_bytes([9; 32])));
    let mut a = Audit::default();
    assert_eq!(a.read(&changed), Err(Refusal::Wage));
    assert_eq!(a.summary().periods, 0);
    let mut no_reserve = r.clone();
    no_reserve.money_transfers.remove(0);
    assert_eq!(Audit::default().read(&no_reserve), Err(Refusal::Wage));
    let mut missing = r;
    missing.money_transfers.pop();
    let f = Audit::default().read(&missing).unwrap();
    assert_eq!(f.funded_wages_paid_micros, "0");
    assert_eq!(f.pending_wages, 1);
}
#[test]
fn procurement_requires_reserved_price_and_arrival_realization_settlement() {
    let mut r = receipts(1);
    let p = procurement(1, 1, 2);
    let order = OutboundOrderId::Delivery(p.order_id);
    r.procurement.push(p.clone());
    assert_eq!(Audit::default().read(&r), Err(Refusal::Payment));
    r.money_transfers.push(transfer(
        MoneyTransferPurpose::PurchaseReservation(order),
        MoneyLocation::Cash(AccountId::Site(p.buyer_site_id)),
        MoneyLocation::PurchaseReserve(order),
        35,
    ));
    let mut a = Audit::default();
    assert_eq!(a.read(&r).unwrap().pending_procurement, 1);
    let mut next = receipts(2);
    next.arrivals.push(ArrivalReceipt {
        order_id: p.order_id,
        quantity: 5,
    });
    next.deliveries.push(DeliveryReceipt {
        order_id: p.order_id,
        quantity: 5,
    });
    next.realizations.push(RealizationReceipt {
        order_id: p.order_id,
        quantity: 5,
    });
    assert_eq!(a.read(&next), Err(Refusal::Payment));
    assert_eq!(a.summary().periods, 1);
    next.money_transfers.push(transfer(
        MoneyTransferPurpose::DeliverySettlement(order),
        MoneyLocation::PurchaseReserve(order),
        MoneyLocation::Cash(AccountId::Site(p.supplier_site_id)),
        35,
    ));
    let f = a.read(&next).unwrap();
    assert_eq!(f.settled_procurement_orders, 1);
    assert_eq!(f.pending_procurement, 0);
}

#[test]
fn local_procurement_uses_its_exact_handoff_without_freight_receipts() {
    let p = procurement(1, 1, 2);
    let order = OutboundOrderId::Delivery(p.order_id);
    let mut opening = receipts(1);
    opening.procurement.push(p.clone());
    opening.money_transfers.push(transfer(
        MoneyTransferPurpose::PurchaseReservation(order),
        MoneyLocation::Cash(AccountId::Site(p.buyer_site_id)),
        MoneyLocation::PurchaseReserve(order),
        35,
    ));
    let mut pending = Audit::default();
    pending.read(&opening).unwrap();
    let mut delivered = receipts(2);
    delivered.local_transfers.push(LocalTransferReceipt {
        order_id: p.order_id,
        supplier_site_id: p.supplier_site_id,
        buyer_site_id: p.buyer_site_id,
        good_id: p.good_id,
        unit_id: p.unit_id,
        quantity: 5,
    });
    delivered.money_transfers.push(transfer(
        MoneyTransferPurpose::DeliverySettlement(order),
        MoneyLocation::PurchaseReserve(order),
        MoneyLocation::Cash(AccountId::Site(p.supplier_site_id)),
        35,
    ));
    let mut missing = delivered.clone();
    missing.local_transfers.clear();
    assert_eq!(pending.clone().read(&missing), Err(Refusal::Payment));
    let mut crossed = delivered.clone();
    crossed.local_transfers[0].unit_id = UnitId::from_bytes([9; 32]);
    assert_eq!(pending.clone().read(&crossed), Err(Refusal::Unit));
    let fact = pending.read(&delivered).unwrap();
    assert_eq!(fact.settled_procurement_orders, 1);
    assert_eq!(fact.pending_procurement, 0);
}
#[test]
fn ownership_requires_exact_beneficiary_and_amount() {
    let mut r = receipts(1);
    let issuer = SiteId::from_bytes([1; 32]);
    let beneficiary = AccountId::Household(FinalDemandPrincipalId::from_bytes([2; 32]));
    r.distributions.push(DistributionReceipt {
        period: 1,
        issuer_site_id: issuer,
        beneficiary,
        shares: 1,
        total_shares: 1,
        eligible_earnings: money(4),
        declared_total: money(4),
        paid: money(4),
    });
    assert_eq!(Audit::default().read(&r), Err(Refusal::Ownership));
    r.money_transfers.push(transfer(
        MoneyTransferPurpose::Cash(CashTransferPurpose::OwnershipDistribution),
        MoneyLocation::Cash(AccountId::Site(issuer)),
        MoneyLocation::Cash(beneficiary),
        4,
    ));
    assert_eq!(
        Audit::default().read(&r).unwrap().ownership_paid_micros,
        "4"
    );
    r.money_transfers[0].credit.location =
        MoneyLocation::Cash(AccountId::Site(SiteId::from_bytes([9; 32])));
    assert_eq!(Audit::default().read(&r), Err(Refusal::Ownership));
}

#[test]
fn capital_funding_does_not_count_as_profit_distribution() {
    let contributor = AccountId::Household(FinalDemandPrincipalId::from_bytes([1; 32]));
    let issuer = SiteId::from_bytes([2; 32]);
    let mut r = receipts(1);
    r.contributions.push(CapitalContributionReceipt {
        period: 1,
        id: ContributionId::from_bytes([3; 32]),
        contributor,
        issuer_site_id: issuer,
        requested: money(9),
        paid: money(7),
        unfunded: money(2),
    });
    r.money_transfers.push(transfer(
        MoneyTransferPurpose::Cash(CashTransferPurpose::CapitalContribution),
        MoneyLocation::Cash(contributor),
        MoneyLocation::Cash(AccountId::Site(issuer)),
        7,
    ));
    let mut audit = Audit::default();
    let fact = audit.read(&r).unwrap();
    assert_eq!(fact.ownership_paid_micros, "0");
    assert_eq!(audit.summary().ownership_payment_periods, 0);
    r.money_transfers[0].credit.delta = money(8);
    r.money_transfers[0].debit.delta = money(-8);
    assert_eq!(Audit::default().read(&r), Err(Refusal::Ownership));
}
#[test]
fn equipment_future_usability_and_real_work_are_required_without_forcing_investment() {
    let mut r = receipts(1);
    let z = money(0);
    r.installation.push(InstallationReceipt {
        period: 1,
        id: InstallationId::from_bytes([1; 32]),
        process_id: ProcessId::from_bytes([2; 32]),
        site_id: SiteId::from_bytes([3; 32]),
        units: 1,
        started: true,
        opening_hours: 2,
        used_hours: 2,
        remaining_hours: 0,
        usable_from_period: 1,
        opening_carrying: z,
        materials_capitalized: z,
        wages_capitalized: z,
        closing_carrying: z,
    });
    assert_eq!(Audit::default().read(&r), Err(Refusal::Equipment));
    r.installation[0].usable_from_period = 2;
    let mut a = Audit::default();
    assert_eq!(a.read(&r).unwrap().completed_equipment_paths, 0);
    assert_eq!(a.summary().equipment_status, "not_observed");
}
#[test]
fn crossed_retail_units_cannot_count_as_purchase_consumption() {
    let mut r = receipts(1);
    let principal = FinalDemandPrincipalId::from_bytes([1; 32]);
    let retailer = SiteId::from_bytes([2; 32]);
    let good = GoodId::from_bytes([3; 32]);
    let unit = UnitId::from_bytes([4; 32]);
    let order = babylon_material_circuit::recurring_household_order_id(1, (principal, good, unit));
    r.household_demand.push(HouseholdDemandReceipt {
        period: 1,
        principal_id: principal,
        retailer_site_id: retailer,
        good_id: good,
        unit_id: unit,
        order_id: order,
        opening_stock: 0,
        required_quantity: 2,
        desired_quantity: 2,
        requested_quantity: 2,
        admitted_quantity: 2,
        fulfilled_quantity: 2,
        expired_quantity: 0,
        unit_price: money(1),
    });
    r.household_consumption.push(HouseholdConsumptionReceipt {
        period: 1,
        principal_id: principal,
        good_id: good,
        unit_id: unit,
        required_quantity: 2,
        available_quantity: 2,
        consumed_quantity: 2,
        unmet_quantity: 0,
        closing_quantity: 0,
    });
    let outbound = OutboundOrderId::LocalFinalDemand(order);
    let reserve = MoneyLocation::PurchaseReserve(outbound);
    r.money_transfers.push(transfer(
        MoneyTransferPurpose::PurchaseReservation(outbound),
        MoneyLocation::Cash(AccountId::Household(principal)),
        reserve,
        2,
    ));
    r.money_transfers.push(transfer(
        MoneyTransferPurpose::DeliverySettlement(outbound),
        reserve,
        MoneyLocation::Cash(AccountId::Site(retailer)),
        2,
    ));
    r.local_fulfillments.push(LocalRetailFulfillmentReceipt {
        order_id: order,
        retailer_site_id: retailer,
        demand_principal_id: principal,
        good_id: good,
        unit_id: UnitId::from_bytes([9; 32]),
        quantity: 2,
    });
    assert_eq!(Audit::default().read(&r), Err(Refusal::Unit));
    r.local_fulfillments[0].unit_id = unit;
    let f = Audit::default().read(&r).unwrap();
    assert_eq!(f.households[0].purchased_consumption_lower_bound, 2);
}
#[test]
fn funded_equipment_arrives_installs_then_its_exact_cohort_performs_later_work() {
    let site = SiteId::from_bytes([1; 32]);
    let supplier = SiteId::from_bytes([2; 32]);
    let process = ProcessId::from_bytes([3; 32]);
    let id = InstallationId::from_bytes([4; 32]);
    let order_id = OrderId::from_bytes([5; 32]);
    let order = OutboundOrderId::Delivery(order_id);
    let reserve = MoneyLocation::PurchaseReserve(order);
    let mut first = receipts(1);
    first
        .investment
        .push(investment(1, site, supplier, process, order_id));
    first.money_transfers.push(transfer(
        MoneyTransferPurpose::PurchaseReservation(order),
        MoneyLocation::Cash(AccountId::Site(site)),
        reserve,
        7,
    ));
    let mut a = Audit::default();
    assert_eq!(a.read(&first).unwrap().completed_equipment_paths, 0);
    let mut second = receipts(2);
    second.arrivals.push(ArrivalReceipt {
        order_id,
        quantity: 1,
    });
    second.deliveries.push(DeliveryReceipt {
        order_id,
        quantity: 1,
    });
    second.realizations.push(RealizationReceipt {
        order_id,
        quantity: 1,
    });
    second.money_transfers.push(transfer(
        MoneyTransferPurpose::DeliverySettlement(order),
        reserve,
        MoneyLocation::Cash(AccountId::Site(supplier)),
        7,
    ));
    second.installation.push(installed(2, id, site, process));
    assert_eq!(a.read(&second).unwrap().completed_equipment_paths, 0);
    let mut third = worked(3, id, site, process);
    third.production.clear();
    assert_eq!(a.read(&third), Err(Refusal::Equipment));
    assert_eq!(a.summary().periods, 2);
    third.production.push(ProductionReceipt {
        process_id: process,
        site_id: site,
        planned_batches: 1,
        produced_batches: 1,
    });
    let f = a.read(&third).unwrap();
    assert_eq!(f.completed_equipment_paths, 1);
    assert_eq!(f.pending_equipment, 0);
}

#[test]
fn local_equipment_received_after_installation_cannot_fund_that_installation() {
    let site = SiteId::from_bytes([1; 32]);
    let supplier = SiteId::from_bytes([2; 32]);
    let process = ProcessId::from_bytes([3; 32]);
    let opening_id = InstallationId::from_bytes([4; 32]);
    let purchased_id = InstallationId::from_bytes([6; 32]);
    let order_id = OrderId::from_bytes([5; 32]);
    let order = OutboundOrderId::Delivery(order_id);
    let reserve = MoneyLocation::PurchaseReserve(order);
    let mut first = receipts(1);
    first
        .investment
        .push(investment(1, site, supplier, process, order_id));
    first.money_transfers.push(transfer(
        MoneyTransferPurpose::PurchaseReservation(order),
        MoneyLocation::Cash(AccountId::Site(site)),
        reserve,
        7,
    ));
    let mut audit = Audit::default();
    audit.read(&first).unwrap();
    let mut second = receipts(2);
    second
        .installation
        .push(installed(2, opening_id, site, process));
    second.local_transfers.push(LocalTransferReceipt {
        order_id,
        supplier_site_id: supplier,
        buyer_site_id: site,
        good_id: GoodId::from_bytes([7; 32]),
        unit_id: UnitId::from_bytes([8; 32]),
        quantity: 1,
    });
    second.money_transfers.push(transfer(
        MoneyTransferPurpose::DeliverySettlement(order),
        reserve,
        MoneyLocation::Cash(AccountId::Site(supplier)),
        7,
    ));
    audit.read(&second).unwrap();
    let mut third = worked(3, opening_id, site, process);
    third
        .installation
        .push(installed(3, purchased_id, site, process));
    let fact = audit.read(&third).unwrap();
    assert_eq!(fact.completed_equipment_paths, 0);
    assert_eq!(fact.pending_equipment, 1);
    let fourth = worked(4, purchased_id, site, process);
    let fact = audit.read(&fourth).unwrap();
    assert_eq!(fact.completed_equipment_paths, 1);
    assert_eq!(fact.pending_equipment, 0);
}
