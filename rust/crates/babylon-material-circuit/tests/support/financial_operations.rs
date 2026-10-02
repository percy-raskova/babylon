use super::*;
fn service_opening(cash: [i128; 5]) -> MaterialCircuitState {
    let mut state = opening(cash);
    let process = ProcessId::from_bytes([1; 32]);
    let service = GoodId::from_bytes([1; 32]);
    let input = GoodId::from_bytes([2; 32]);
    let native = UnitId::from_bytes([1; 32]);
    let hours = UnitId::from_bytes([9; 32]);
    state.commodities = vec![
        CommodityDefinition {
            good_id: service,
            unit_id: native,
            kind: CommodityKind::PeriodService {
                stage: ServiceStage::UtilityProvision,
            },
        },
        CommodityDefinition {
            good_id: input,
            unit_id: native,
            kind: CommodityKind::Storable { grams_per_unit: 1 },
        },
    ];
    state.inventory = vec![InventoryRow {
        site_id: site(),
        good_id: input,
        unit_id: native,
        quantity: 1,
    }];
    state.process_outputs = vec![ProcessOutput {
        process_id: process,
        site_id: site(),
        good_id: service,
        unit_id: native,
        quantity_per_batch: 1,
    }];
    state.input_coefficients = vec![InputOutputCoefficient {
        process_id: process,
        good_id: input,
        unit_id: native,
        quantity_per_batch: 1,
    }];
    state.labor_coefficients = vec![LaborCoefficient {
        process_id: process,
        unit_id: hours,
        quantity_per_batch: 1,
    }];
    state.capacities = vec![CapacityRow {
        period: 1,
        process_id: process,
        site_id: site(),
        available_batches: 1,
    }];
    state.labor = vec![LaborCapacityRow {
        site_id: site(),
        unit_id: hours,
        period: 1,
        available: 1,
    }];
    state.production_commitments = vec![ProductionCommitment {
        process_id: process,
        site_id: site(),
        period: 1,
        planned_batches: 1,
    }];
    state.service_connections = vec![ServiceConnection {
        provider_site_id: site(),
        buyer: AccountId::Household(household()),
        good_id: service,
        unit_id: native,
    }];
    configure_service_money(
        economy_mut(&mut state),
        process,
        service,
        input,
        native,
        hours,
    );
    state
}
fn configure_service_money(
    e: &mut MonetaryCircuit,
    process: ProcessId,
    service: GoodId,
    input: GoodId,
    native: UnitId,
    hours: UnitId,
) {
    let member_id = StaffingMemberId::from_bytes(site().as_bytes());
    e.member_labor = vec![MemberLaborCapacityRow {
        member_id,
        period: 1,
        available_hours: 1,
    }];
    e.employment = vec![EmploymentTerms {
        member_id,
        site_id: site(),
        unit_id: hours,
        payee: household(),
        compensation: LaborCompensation::Wage(money(2)),
    }];
    e.costs = HistoricalCostBook::open(
        &e.book,
        vec![StockCarryingValue {
            owner: AccountId::Site(site()),
            good_id: input,
            unit_id: native,
            amount: money(4),
        }],
        vec![],
        e.costs.snapshot().equity,
        vec![],
    )
    .unwrap();
    e.recurring = Some(Box::new(RecurringEconomy {
        service_inputs: vec![],
        households: vec![HouseholdCohort {
            principal_id: household(),
            households: 1,
            persons: 1,
        }],
        household_stocks: vec![],
        household_needs: vec![HouseholdNeed {
            principal_id: household(),
            good_id: service,
            unit_id: native,
            basis: HouseholdNeedBasis::Persons,
            units_per_basis: 1,
        }],
        household_purchases: vec![HouseholdPurchasePolicy {
            principal_id: household(),
            retailer_site_id: site(),
            good_id: service,
            unit_id: native,
            target_closing_stock: 0,
            maximum_purchase: 1,
            enabled: true,
        }],
        offers: vec![SellerOffer {
            site_id: site(),
            good_id: service,
            unit_id: native,
            unit_price: money(15),
            pricing: PricePolicy::Fixed,
        }],
        replenishment: vec![],
        production: vec![ProductionDemandPolicy {
            process_id: process,
            site_id: site(),
            output_buffer: 0,
            planned_batches: 1,
        }],
        attendance: vec![AttendancePlan {
            site_id: site(),
            unit_id: hours,
            period: 1,
            planned_hours: 1,
        }],
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    }));
}
fn income(t: &MaterialCircuitTransition, account: AccountId) -> &IncomeReceipt {
    t.income.iter().find(|r| r.account == account).unwrap()
}
#[test]
fn operating_income_tax_and_foreign_owner_payout_match_independent_journal() {
    let mut state = service_opening([2, 13, 0, 0, 0]);
    let f = &mut economy_mut(&mut state).financial;
    f.taxes.push(TaxPolicy {
        payer: AccountId::Site(site()),
        public_recipient: treasury(),
        basis: TaxBasis::PositiveOperatingIncome,
        rate_bps: 2500,
        cash_floor: money(0),
    });
    f.distributions.push(DistributionPolicy {
        issuer_site_id: site(),
        earnings_fraction_bps: 10000,
        period_cap: money(100),
        cash_floor: money(0),
    });
    let t = advance_material_circuit(&state).unwrap();
    let issuer = income(&t, AccountId::Site(site()));
    assert_eq!(issuer.statement.sales, money(15));
    assert_eq!(issuer.statement.cost_of_goods_sold, money(6));
    assert_eq!(issuer.statement.operating_income().unwrap(), money(9));
    assert_eq!(issuer.statement.tax_expense, money(2));
    assert_eq!(issuer.net_income, money(7));
    assert_eq!(issuer.distributions_paid, money(7));
    assert_eq!(issuer.closing_retained_earnings, money(0));
    assert_eq!(income(&t, owner(2)).statement.distribution_income, money(3));
    assert_eq!(income(&t, owner(3)).statement.distribution_income, money(4));
    assert_eq!(
        income(&t, AccountId::Household(household()))
            .statement
            .wage_income,
        money(2)
    );
    assert_eq!(
        income(&t, AccountId::Household(household()))
            .statement
            .consumption_expense,
        money(15)
    );
    for (id, expected) in [
        (AccountId::Site(site()), 6),
        (AccountId::Household(household()), 0),
        (owner(2), 3),
        (owner(3), 4),
        (AccountId::Public(treasury()), 2),
    ] {
        assert_eq!(economy(&t.state).book.cash(id).unwrap(), money(expected));
    }
    assert_eq!(
        t.money_transfers
            .iter()
            .filter(|r| r.purpose
                == MoneyTransferPurpose::Cash(CashTransferPurpose::OwnershipDistribution))
            .count(),
        2
    );
    assert_eq!(
        economy(&t.state).book.total_cash_and_reserves().unwrap(),
        money(15)
    );
}
#[test]
fn public_provider_funding_reaches_actual_work_and_service_and_withdrawal_severs_it() {
    let mut state = service_opening([0, 13, 0, 0, 2]);
    let f = &mut economy_mut(&mut state).financial;
    f.public_budgets.push(PublicBudget {
        public_account: treasury(),
        period_cap: money(2),
        cash_floor: money(0),
    });
    f.public_allocations.push(PublicAllocation {
        public_account: treasury(),
        recipient: AccountId::Site(site()),
        treatment: PublicTransferTreatment::ProviderOperatingGrant,
        priority: 0,
        amount_per_period: money(2),
    });
    let funded = advance_material_circuit(&state).unwrap();
    assert_eq!(funded.production[0].produced_batches, 1);
    assert_eq!(funded.household_services[0].satisfied_quantity, 1);
    assert_eq!(
        income(&funded, AccountId::Site(site()))
            .statement
            .public_transfer_income,
        money(2)
    );
    economy_mut(&mut state).financial.public_budgets[0].period_cap = money(0);
    let withdrawn = advance_material_circuit(&state).unwrap();
    assert_eq!(withdrawn.production[0].produced_batches, 0);
    assert_eq!(withdrawn.household_services[0].unmet_quantity, 1);
    assert_eq!(withdrawn.public_budgets[0].unfunded, money(2));
    assert_eq!(
        economy(&withdrawn.state)
            .book
            .total_cash_and_reserves()
            .unwrap(),
        money(15)
    );
}
#[test]
fn tax_shortfall_records_current_uncollected_amount_without_minting_debt() {
    let mut state = service_opening([2, 13, 0, 0, 0]);
    economy_mut(&mut state).financial.taxes.push(TaxPolicy {
        payer: AccountId::Site(site()),
        public_recipient: treasury(),
        basis: TaxBasis::PositiveOperatingIncome,
        rate_bps: 10000,
        cash_floor: money(14),
    });
    let t = advance_material_circuit(&state).unwrap();
    assert_eq!(t.taxes[0].assessed, money(9));
    assert_eq!(t.taxes[0].collected, money(1));
    assert_eq!(t.taxes[0].uncollected, money(8));
    assert_eq!(
        income(&t, AccountId::Public(treasury()))
            .statement
            .tax_income,
        money(1)
    );
    assert_eq!(
        income(&t, AccountId::Site(site())).statement.tax_expense,
        money(1)
    );
    assert!(economy(&t.state).book.snapshot().shifts.is_empty());
    assert_eq!(
        economy(&t.state).book.total_cash_and_reserves().unwrap(),
        money(15)
    );
}
#[test]
fn late_financial_overflow_leaves_all_opening_cash_and_equity_unchanged() {
    let mut state = opening([0, 0, 1, 0, 0]);
    let e = economy_mut(&mut state);
    let mut values = e.costs.snapshot();
    values.equity[0].amount = money(i128::MAX - 1);
    values
        .accounts
        .iter_mut()
        .find(|r| r.account == owner(2))
        .unwrap()
        .opening_capital = money(i128::MAX);
    values
        .accounts
        .iter_mut()
        .find(|r| r.account == AccountId::Site(site()))
        .unwrap()
        .contributed_capital = money(i128::MAX);
    values
        .accounts
        .iter_mut()
        .find(|r| r.account == AccountId::Site(site()))
        .unwrap()
        .retained_earnings = money(-i128::MAX);
    e.costs = HistoricalCostBook::from_snapshot(values).unwrap();
    e.financial.contributions.push(CapitalContributionOrder {
        id: ContributionId::from_bytes([2; 32]),
        due_period: 1,
        contributor: owner(2),
        issuer_site_id: site(),
        amount: money(1),
    });
    let before = encode_material_circuit_state(&state).unwrap();
    assert_eq!(
        advance_material_circuit(&state),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(encode_material_circuit_state(&state).unwrap(), before);
}
