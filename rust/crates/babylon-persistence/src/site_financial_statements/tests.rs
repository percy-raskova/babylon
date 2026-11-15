//! Exact joins that distinguish book equity, income and spendable cash.
use super::projection;
use super::{SiteBalanceSheet, SiteStatementsError};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CapitalAccount, CashAccount, CashTransferPurpose, CircuitAccounting,
    EquipmentAssetId, EquipmentCarryingValue, EquipmentCohortId, EquityCarryingValue,
    FreightCarryingValue, FreightLotId, FundedShift, GoodId, HistoricalCostBook,
    HistoricalCostSnapshot, IncomeReceipt, IncomeStatement, InvestmentReceipt, MonetaryBook,
    MonetaryBookSnapshot, MoneyLocation, MoneyPosting, MoneyTransferPurpose, MoneyTransferReceipt,
    OrderId, OutboundOrderId, ProcessId, PurchaseEscrow, ShiftId, ShiftState, SiteId,
    StockCarryingValue, UnitId,
};
use babylon_tick::material_world::MaterialTickReceipts;
fn money(value: i128) -> Currency {
    Currency::from_micro_units(value)
}
fn site() -> SiteId {
    SiteId::from_bytes([1; 32])
}
fn other() -> AccountId {
    AccountId::Site(SiteId::from_bytes([2; 32]))
}
fn statement() -> IncomeStatement {
    IncomeStatement {
        sales: money(10),
        wage_income: money(0),
        cost_of_goods_sold: money(7),
        productive_labor_capitalized: money(0),
        installation_labor_capitalized: money(0),
        equipment_wear_capitalized: money(0),
        idle_labor_expense: money(0),
        handling_expense: money(0),
        maintenance_labor_expense: money(0),
        maintenance_material_expense: money(0),
        freight_loss_expense: money(0),
        consumption_expense: money(0),
        final_demand_outlay: money(0),
        unused_service_expense: money(0),
        tax_income: money(0),
        tax_expense: money(0),
        public_transfer_income: money(0),
        public_transfer_expense: money(0),
        distribution_income: money(0),
        gift_income: money(0),
        gift_expense: money(0),
        agency_observation_labor_expense: money(0),
    }
}
fn balance(cash: i128, contributed: i128, retained: i128) -> SiteBalanceSheet {
    let cash_book = MonetaryBookSnapshot {
        accounts: vec![CashAccount {
            id: AccountId::Site(site()),
            cash: money(cash),
        }],
        purchases: vec![],
        shifts: vec![],
    };
    let costs = HistoricalCostSnapshot {
        accounts: vec![CapitalAccount {
            account: AccountId::Site(site()),
            opening_capital: money(100),
            contributed_capital: money(contributed),
            retained_earnings: money(retained),
        }],
        stocks: vec![],
        freight: vec![],
        equity: vec![],
        equipment: vec![],
    };
    projection::balance(site(), &cash_book, &costs).expect("authored books balance")
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
fn period() -> MaterialTickReceipts {
    let account = AccountId::Site(site());
    let mut receipts = crate::test_support::material_receipts(1);
    receipts.income.push(IncomeReceipt {
        account,
        period: 1,
        opening_capital: money(100),
        opening_retained_earnings: money(0),
        opening_contributed_capital: money(0),
        contributions_received: money(20),
        closing_contributed_capital: money(20),
        distributions_paid: money(5),
        statement: statement(),
        net_income: money(3),
        closing_retained_earnings: money(-2),
    });
    let cash = MoneyLocation::Cash(account);
    let reserve = OutboundOrderId::Delivery(OrderId::from_bytes([4; 32]));
    receipts.money_transfers = vec![
        transfer(
            MoneyTransferPurpose::DeliverySettlement(reserve),
            MoneyLocation::PurchaseReserve(reserve),
            cash,
            10,
        ),
        transfer(
            MoneyTransferPurpose::Cash(CashTransferPurpose::TransportService),
            cash,
            MoneyLocation::Cash(other()),
            7,
        ),
        transfer(
            MoneyTransferPurpose::Cash(CashTransferPurpose::CapitalContribution),
            MoneyLocation::Cash(other()),
            cash,
            20,
        ),
        transfer(
            MoneyTransferPurpose::Cash(CashTransferPurpose::OwnershipDistribution),
            cash,
            MoneyLocation::Cash(other()),
            5,
        ),
    ];
    receipts
}
#[test]
fn complete_income_cash_and_equity_join_without_counting_contributions_as_income() {
    let receipts = period();
    let activity = projection::activity(
        site(),
        &balance(100, 0, 0),
        &balance(118, 20, -2),
        &receipts,
    )
    .expect("all three statements reconcile");
    assert_eq!(activity.income.net_income, money(3));
    assert_eq!(activity.change_in_equity, money(18));
    assert_eq!(activity.cash_flow.operating, money(3));
    assert_eq!(activity.cash_flow.financing, money(15));
    assert_eq!(activity.cash_flow.net_change_in_cash, money(18));
    assert_eq!(activity.cash_flow.transfers.len(), 4);
    assert_eq!(activity.cash_flow.transfers[3].receipt_index, 3);
    assert_eq!(activity.income.statement, statement());
}
#[test]
fn missing_duplicate_or_disconnected_receipt_refuses_the_statement() {
    let opening = balance(100, 0, 0);
    let closing = balance(118, 20, -2);
    let mut receipts = period();
    receipts.income.push(receipts.income[0].clone());
    assert_eq!(
        projection::activity(site(), &opening, &closing, &receipts),
        Err(SiteStatementsError::IncomeReceiptMismatch)
    );
    receipts.income.pop();
    receipts.money_transfers.pop();
    assert_eq!(
        projection::activity(site(), &opening, &closing, &receipts),
        Err(SiteStatementsError::CashReconciliationMismatch)
    );
    receipts.income[0].opening_retained_earnings = money(1);
    receipts.income[0].closing_retained_earnings = money(-1);
    assert_eq!(
        projection::activity(site(), &opening, &closing, &receipts),
        Err(SiteStatementsError::IncomeReceiptMismatch)
    );
    receipts.income.clear();
    assert_eq!(
        projection::activity(site(), &opening, &closing, &receipts),
        Err(SiteStatementsError::IncomeReceiptMismatch)
    );
}
#[test]
fn reserves_and_all_carrying_assets_balance_with_accrued_wage_liabilities() {
    let account = AccountId::Site(site());
    let order = OutboundOrderId::Delivery(OrderId::from_bytes([4; 32]));
    let mut shift = FundedShift::new(
        ShiftId::from_bytes([5; 32]),
        account,
        other(),
        1,
        2,
        money(3),
    )
    .expect("funded shift");
    shift.state = ShiftState::Accrued;
    let money_book = MonetaryBook::from_snapshot(MonetaryBookSnapshot {
        accounts: vec![
            CashAccount {
                id: account,
                cash: money(100),
            },
            CashAccount {
                id: other(),
                cash: money(0),
            },
        ],
        purchases: vec![
            PurchaseEscrow::new(order, account, other(), 2, money(10)).expect("purchase reserve")
        ],
        shifts: vec![shift],
    })
    .expect("book");
    let costs = HistoricalCostBook::open(
        &money_book,
        vec![StockCarryingValue {
            owner: account,
            good_id: GoodId::from_bytes([6; 32]),
            unit_id: UnitId::from_bytes([7; 32]),
            amount: money(8),
        }],
        vec![FreightCarryingValue {
            lot_id: FreightLotId::from_bytes([8; 32]),
            owner: account,
            amount: money(9),
        }],
        vec![EquityCarryingValue {
            owner: account,
            issuer_site_id: SiteId::from_bytes([2; 32]),
            amount: money(12),
        }],
        vec![EquipmentCarryingValue {
            asset: EquipmentAssetId::Installed(EquipmentCohortId::from_bytes([9; 32])),
            owner: site(),
            amount: money(15),
        }],
    )
    .expect("captured carrying basis");
    let balance =
        projection::balance(site(), &money_book.snapshot(), &costs.snapshot()).expect("balanced");
    assert_eq!(balance.total_assets, money(170));
    assert_eq!(balance.wage_payables, money(6));
    assert_eq!(balance.total_equity, money(164));
    assert_eq!(balance.equity_investments, money(12));
    assert_eq!(balance.equipment, money(15));
}
#[test]
fn exact_reserve_component_preserves_ambiguous_purchase_and_payroll_uses() {
    let opening = balance(100, 0, 0);
    let mut closing = opening.clone();
    closing.cash = money(70);
    closing.purchase_reserves = money(20);
    closing.payroll_reserves = money(10);
    let cash = MoneyLocation::Cash(AccountId::Site(site()));
    let order = OutboundOrderId::Delivery(OrderId::from_bytes([4; 32]));
    let shift = ShiftId::from_bytes([5; 32]);
    let mut receipts = crate::test_support::material_receipts(1);
    receipts.money_transfers = vec![
        transfer(
            MoneyTransferPurpose::PurchaseReservation(order),
            cash,
            MoneyLocation::PurchaseReserve(order),
            20,
        ),
        transfer(
            MoneyTransferPurpose::ShiftReservation(shift),
            cash,
            MoneyLocation::PayrollReserve(shift),
            10,
        ),
    ];
    let flow = projection::cash_flow(site(), &opening, &closing, &receipts)
        .expect("reserve movement is identified");
    assert_eq!(flow.operating, money(0));
    assert_eq!(flow.investing, money(0));
    assert_eq!(flow.reserve_reclassification, money(-30));
    assert_eq!(flow.net_change_in_cash, money(-30));
    assert_eq!(flow.change_in_purchase_reserves, money(20));
    assert_eq!(flow.change_in_payroll_reserves, money(10));
    receipts.money_transfers[0].purpose = MoneyTransferPurpose::ShiftReservation(shift);
    assert_eq!(
        projection::cash_flow(site(), &opening, &closing, &receipts),
        Err(SiteStatementsError::InvalidTransfer)
    );
}
#[test]
fn unknown_account_unavailable_money_and_overflow_are_explicit() {
    let book = MonetaryBook::open(vec![CashAccount {
        id: AccountId::Site(site()),
        cash: money(i128::MAX),
    }])
    .expect("bounded cash");
    let mut costs = HistoricalCostBook::open(&book, vec![], vec![], vec![], vec![])
        .expect("opening capital")
        .snapshot();
    costs.accounts[0].contributed_capital = money(1);
    assert_eq!(
        projection::balance(site(), &book.snapshot(), &costs),
        Err(SiteStatementsError::Arithmetic)
    );
    assert_eq!(
        projection::balance(SiteId::from_bytes([9; 32]), &book.snapshot(), &costs),
        Err(SiteStatementsError::SiteAbsent)
    );
    assert_eq!(
        projection::project(site(), None, &CircuitAccounting::PhysicalControl, None),
        Err(SiteStatementsError::MonetaryBooksUnavailable)
    );
}
#[test]
fn foundation_has_no_period_flows_and_preserves_ownership_without_inventing_control() {
    use babylon_material_circuit::{
        AidBook, FinancialInstitutions, HouseholdTimeAccounting, MonetaryCircuit, OwnershipClaim,
    };
    let book = MonetaryBook::open(vec![
        CashAccount {
            id: AccountId::Site(site()),
            cash: money(100),
        },
        CashAccount {
            id: other(),
            cash: money(0),
        },
    ])
    .expect("cash");
    let costs = HistoricalCostBook::open(&book, vec![], vec![], vec![], vec![]).expect("capital");
    let mut financial = FinancialInstitutions::empty();
    financial.ownership.push(OwnershipClaim {
        issuer_site_id: site(),
        beneficiary: other(),
        shares: 12,
    });
    let accounting = CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
        aid: AidBook::default(),
        household_time: HouseholdTimeAccounting::NotModeled,
        financial,
        costs,
        recurring: None,
        book,
        employment: vec![],
        member_labor: vec![],
    }));
    let statements =
        projection::project(site(), None, &accounting, None).expect("foundation statements");
    assert!(statements.opening.is_none());
    assert!(statements.activity.is_none());
    assert_eq!(statements.closing.cash, money(100));
    assert_eq!(statements.ownership_claims[0].shares, 12);
    assert_eq!(
        statements.planning_control,
        super::PlanningControl::NotCaptured
    );
}
#[test]
fn equity_acquisition_is_investing_cash_and_invalid_purpose_cannot_fill_the_split() {
    let opening = balance(100, 0, 0);
    let mut closing = opening.clone();
    closing.cash = money(80);
    closing.equity_investments = money(20);
    let mut receipts = crate::test_support::material_receipts(1);
    receipts.money_transfers = vec![transfer(
        MoneyTransferPurpose::Cash(CashTransferPurpose::CapitalContribution),
        MoneyLocation::Cash(AccountId::Site(site())),
        MoneyLocation::Cash(other()),
        20,
    )];
    let flow = projection::cash_flow(site(), &opening, &closing, &receipts)
        .expect("identified equity acquisition");
    assert_eq!(flow.investing, money(-20));
    assert_eq!(flow.financing, money(0));
    receipts.money_transfers[0].purpose = MoneyTransferPurpose::DeliverySettlement(
        OutboundOrderId::Delivery(OrderId::from_bytes([4; 32])),
    );
    assert_eq!(
        projection::cash_flow(site(), &opening, &closing, &receipts),
        Err(SiteStatementsError::InvalidTransfer)
    );
}
#[test]
fn investment_reservation_joins_exact_order_amount_without_counting_settlement_twice() {
    let opening = balance(100, 0, 0);
    let mut closing = opening.clone();
    closing.cash = money(80);
    closing.purchase_reserves = money(20);
    let account = MoneyLocation::Cash(AccountId::Site(site()));
    let order_id = OrderId::from_bytes([4; 32]);
    let order = OutboundOrderId::Delivery(order_id);
    let mut receipts = crate::test_support::material_receipts(1);
    receipts.investment.push(InvestmentReceipt {
        period: 1,
        order_id,
        process_id: ProcessId::from_bytes([9; 32]),
        site_id: site(),
        supplier_site_id: SiteId::from_bytes([2; 32]),
        installed_units: 0,
        pending_units: 0,
        on_hand_units: 0,
        outstanding_inbound_units: 0,
        captured_plan_batches: 1,
        accepted_output_orders: 1,
        output_stock: 0,
        output_buffer: 0,
        replacement_requested_units: 2,
        expansion_requested_units: 0,
        admitted_units: 2,
        unit_price: money(10),
        free_cash: money(100),
        earnings_budget: money(0),
    });
    receipts.money_transfers = vec![
        transfer(
            MoneyTransferPurpose::PurchaseReservation(order),
            account,
            MoneyLocation::PurchaseReserve(order),
            20,
        ),
        transfer(
            MoneyTransferPurpose::DeliverySettlement(order),
            MoneyLocation::PurchaseReserve(order),
            MoneyLocation::Cash(other()),
            20,
        ),
    ];
    let flow = projection::cash_flow(site(), &opening, &closing, &receipts)
        .expect("identified equipment funding");
    assert_eq!(flow.investing, money(-20));
    assert_eq!(flow.reserve_reclassification, money(0));
    assert_eq!(
        flow.transfers.len(),
        1,
        "reserve settlement has no second spendable cash posting"
    );
    assert_eq!(
        flow.transfers[0].category,
        super::CashFlowCategory::Investing
    );
    receipts.investment[0].unit_price = money(9);
    assert_eq!(
        projection::cash_flow(site(), &opening, &closing, &receipts),
        Err(SiteStatementsError::InvestmentReceiptMismatch)
    );
    receipts.investment[0].order_id = OrderId::from_bytes([8; 32]);
    let unknown = projection::cash_flow(site(), &opening, &closing, &receipts)
        .expect("unjoined reserve is separately identified");
    assert_eq!(unknown.investing, money(0));
    assert_eq!(unknown.reserve_reclassification, money(-20));
    receipts
        .money_transfers
        .push(receipts.money_transfers[0].clone());
    assert_eq!(
        projection::cash_flow(site(), &opening, &closing, &receipts),
        Err(SiteStatementsError::CashReconciliationMismatch)
    );
}

#[test]
fn period_summary_connects_every_site_and_preserves_physical_stock_identity() {
    use babylon_tick::material_world::{self, MaterialWorldRegister};
    use std::collections::BTreeSet;

    let (catalog, state) = crate::production_projection::recurring_fixture::materials();
    let opening = MaterialWorldRegister::try_new(&catalog, 0, state).expect("paid opening");
    let next = opening.prepare_next(&catalog).expect("paid period");
    let rows = material_world::decode_material_receipts(next.receipt_bytes())
        .expect("complete period receipts");
    let before = opening.state();
    let after = next.register().state();
    let period = super::project_period(before, after, &rows).expect("complete site period");
    let statements = period.statements.as_ref().expect("monetary site books");
    assert_eq!(statements.len(), 3);
    for row in statements {
        let selected = projection::project(
            row.site_id,
            Some(&before.accounting),
            &after.accounting,
            Some(&rows),
        )
        .expect("selected site statement");
        let activity = selected.activity.expect("selected activity");
        assert_eq!(Some(&row.opening), selected.opening.as_ref());
        assert_eq!(row.closing, selected.closing);
        assert_eq!(row.income, activity.income);
        assert_eq!(row.change_in_equity, activity.change_in_equity);
        assert_eq!(row.cash_flow.operating, activity.cash_flow.operating);
        assert_eq!(row.cash_flow.investing, activity.cash_flow.investing);
        assert_eq!(row.cash_flow.financing, activity.cash_flow.financing);
        assert_eq!(
            row.cash_flow.reserve_reclassification,
            activity.cash_flow.reserve_reclassification
        );
    }
    assert!(period
        .stocks
        .iter()
        .any(|row| row.opening.is_none() && row.closing.is_some()));
    let expected_keys: BTreeSet<_> = before
        .inventory
        .iter()
        .chain(&after.inventory)
        .map(|row| (row.site_id, row.good_id, row.unit_id))
        .collect();
    assert_eq!(
        period
            .stocks
            .iter()
            .map(|row| (row.site_id, row.good_id, row.unit_id))
            .collect::<Vec<_>>(),
        expected_keys.into_iter().collect::<Vec<_>>()
    );
    for stock in &period.stocks {
        for (state, point) in [(before, &stock.opening), (after, &stock.closing)] {
            let key = (stock.site_id, stock.good_id, stock.unit_id);
            let inventory = state
                .inventory
                .iter()
                .find(|r| (r.site_id, r.good_id, r.unit_id) == key);
            assert_eq!(
                point.as_ref().map(|p| p.quantity),
                inventory.map(|r| r.quantity)
            );
            let CircuitAccounting::Monetary(economy) = &state.accounting else {
                panic!("paid fixture")
            };
            let cost = economy.costs.snapshot().stocks.into_iter().find(|r| {
                (r.owner, r.good_id, r.unit_id) == (AccountId::Site(key.0), key.1, key.2)
            });
            assert_eq!(
                point.as_ref().and_then(|p| p.carrying_cost),
                cost.map(|r| r.amount)
            );
        }
    }
    let mut corrupted = after.clone();
    corrupted.inventory.remove(0);
    assert_eq!(
        super::project_period(before, &corrupted, &rows),
        Err(SiteStatementsError::StockBasisMismatch)
    );
}

#[test]
fn physical_control_preserves_absent_and_explicit_zero_positions_without_imputing_cost() {
    let (_, mut before) = crate::production_projection::recurring_fixture::materials();
    before.accounting = CircuitAccounting::PhysicalControl;
    let mut after = before.clone();
    after.period += 1;
    let removed = after.inventory.remove(0);
    after.inventory[0].quantity = 0;
    let mut evidence = period();
    evidence.income.clear();
    evidence.money_transfers.clear();
    let period =
        super::project_period(&before, &after, &evidence).expect("physical stock positions");
    assert!(period.statements.is_none());
    let stock = period
        .stocks
        .iter()
        .find(|row| row.site_id == removed.site_id)
        .expect("retired site stock");
    assert!(stock.closing.is_none());
    assert_eq!(
        stock.opening,
        Some(super::SiteStockPosition {
            quantity: removed.quantity,
            carrying_cost: None
        })
    );
    assert!(period.stocks.iter().any(|r| r.closing
        == Some(super::SiteStockPosition {
            quantity: 0,
            carrying_cost: None
        })));
}
