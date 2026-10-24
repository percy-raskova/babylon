use crate::economy;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::AttendancePlan;
use babylon_material_circuit::CapacityRow;
use babylon_material_circuit::CapitalContributionOrder;
use babylon_material_circuit::CashTransferPurpose;
use babylon_material_circuit::CommodityDefinition;
use babylon_material_circuit::CommodityKind;
use babylon_material_circuit::ContributionId;
use babylon_material_circuit::DistributionPolicy;
use babylon_material_circuit::EmploymentTerms;
use babylon_material_circuit::GoodId;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::HouseholdCohort;
use babylon_material_circuit::HouseholdNeed;
use babylon_material_circuit::HouseholdNeedBasis;
use babylon_material_circuit::HouseholdPurchasePolicy;
use babylon_material_circuit::IncomeReceipt;
use babylon_material_circuit::InputOutputCoefficient;
use babylon_material_circuit::InventoryRow;
use babylon_material_circuit::LaborCapacityRow;
use babylon_material_circuit::LaborCoefficient;
use babylon_material_circuit::LaborCompensation;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MaterialCircuitTransition;
use babylon_material_circuit::MemberLaborCapacityRow;
use babylon_material_circuit::MonetaryCircuit;
use babylon_material_circuit::MoneyTransferPurpose;
use babylon_material_circuit::PricePolicy;
use babylon_material_circuit::ProcessId;
use babylon_material_circuit::ProcessOutput;
use babylon_material_circuit::ProductionCommitment;
use babylon_material_circuit::ProductionDemandPolicy;
use babylon_material_circuit::PublicAllocation;
use babylon_material_circuit::PublicBudget;
use babylon_material_circuit::PublicTransferTreatment;
use babylon_material_circuit::RecurringEconomy;
use babylon_material_circuit::SellerOffer;
use babylon_material_circuit::ServiceConnection;
use babylon_material_circuit::ServiceStage;
use babylon_material_circuit::StaffingMemberId;
use babylon_material_circuit::StockCarryingValue;
use babylon_material_circuit::TaxBasis;
use babylon_material_circuit::TaxPolicy;
use babylon_material_circuit::UnitId;
fn service_opening(cash: [i128; 5]) -> MaterialCircuitState {
    let mut state = crate::opening(cash);
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
        site_id: crate::site(),
        good_id: input,
        unit_id: native,
        quantity: 1,
    }];
    state.process_outputs = vec![ProcessOutput {
        process_id: process,
        site_id: crate::site(),
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
        site_id: crate::site(),
        available_batches: 1,
    }];
    state.labor = vec![LaborCapacityRow {
        site_id: crate::site(),
        unit_id: hours,
        period: 1,
        available: 1,
    }];
    state.production_commitments = vec![ProductionCommitment {
        process_id: process,
        site_id: crate::site(),
        period: 1,
        planned_batches: 1,
    }];
    state.service_connections = vec![ServiceConnection {
        provider_site_id: crate::site(),
        buyer: AccountId::Household(crate::household()),
        good_id: service,
        unit_id: native,
    }];
    configure_service_money(
        crate::economy_mut(&mut state),
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
    let member_id = StaffingMemberId::from_bytes(crate::site().as_bytes());
    e.member_labor = vec![MemberLaborCapacityRow {
        member_id,
        period: 1,
        available_hours: 1,
    }];
    e.employment = vec![EmploymentTerms {
        member_id,
        site_id: crate::site(),
        unit_id: hours,
        payee: crate::household(),
        compensation: LaborCompensation::Wage(crate::money(2)),
    }];
    e.costs = HistoricalCostBook::open(
        &e.book,
        vec![StockCarryingValue {
            owner: AccountId::Site(crate::site()),
            good_id: input,
            unit_id: native,
            amount: crate::money(4),
        }],
        vec![],
        e.costs.snapshot().equity,
        vec![],
    )
    .expect("the fixture opens the authored source");
    e.recurring = Some(Box::new(RecurringEconomy {
        service_inputs: vec![],
        households: vec![HouseholdCohort {
            kind: babylon_material_circuit::HouseholdKind::Ordinary,
            principal_id: crate::household(),
            households: 1,
            persons: 1,
        }],
        household_stocks: vec![],
        household_needs: vec![HouseholdNeed {
            principal_id: crate::household(),
            good_id: service,
            unit_id: native,
            basis: HouseholdNeedBasis::Persons,
            units_per_basis: 1,
        }],
        household_purchases: vec![HouseholdPurchasePolicy {
            principal_id: crate::household(),
            retailer_site_id: crate::site(),
            good_id: service,
            unit_id: native,
            target_closing_stock: 0,
            maximum_purchase: 1,
            enabled: true,
        }],
        offers: vec![SellerOffer {
            site_id: crate::site(),
            good_id: service,
            unit_id: native,
            unit_price: crate::money(15),
            pricing: PricePolicy::Fixed,
        }],
        replenishment: vec![],
        production: vec![ProductionDemandPolicy {
            process_id: process,
            site_id: crate::site(),
            output_buffer: 0,
            planned_batches: 1,
        }],
        attendance: vec![AttendancePlan {
            site_id: crate::site(),
            unit_id: hours,
            period: 1,
            planned_hours: 1,
        }],
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    }));
}
fn income(t: &MaterialCircuitTransition, account: AccountId) -> &IncomeReceipt {
    t.income
        .iter()
        .find(|r| r.account == account)
        .expect("the fixture holds the searched element")
}
#[test]
fn operating_income_tax_and_foreign_owner_payout_match_independent_journal() {
    let mut state = service_opening([2, 13, 0, 0, 0]);
    let f = &mut crate::economy_mut(&mut state).financial;
    f.taxes.push(TaxPolicy {
        payer: AccountId::Site(crate::site()),
        public_recipient: crate::treasury(),
        basis: TaxBasis::PositiveOperatingIncome,
        rate_bps: 2500,
        cash_floor: crate::money(0),
    });
    f.distributions.push(DistributionPolicy {
        issuer_site_id: crate::site(),
        earnings_fraction_bps: 10000,
        period_cap: crate::money(100),
        cash_floor: crate::money(0),
    });
    let t = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
    let issuer = income(&t, AccountId::Site(crate::site()));
    assert_eq!(issuer.statement.sales, crate::money(15));
    assert_eq!(issuer.statement.cost_of_goods_sold, crate::money(6));
    assert_eq!(
        issuer
            .statement
            .operating_income()
            .expect("the fixture book balances"),
        crate::money(9)
    );
    assert_eq!(issuer.statement.tax_expense, crate::money(2));
    assert_eq!(issuer.net_income, crate::money(7));
    assert_eq!(issuer.distributions_paid, crate::money(7));
    assert_eq!(issuer.closing_retained_earnings, crate::money(0));
    assert_eq!(
        income(&t, crate::owner(2)).statement.distribution_income,
        crate::money(3)
    );
    assert_eq!(
        income(&t, crate::owner(3)).statement.distribution_income,
        crate::money(4)
    );
    assert_eq!(
        income(&t, AccountId::Household(crate::household()))
            .statement
            .wage_income,
        crate::money(2)
    );
    assert_eq!(
        income(&t, AccountId::Household(crate::household()))
            .statement
            .consumption_expense,
        crate::money(15)
    );
    for (id, expected) in [
        (AccountId::Site(crate::site()), 6),
        (AccountId::Household(crate::household()), 0),
        (crate::owner(2), 3),
        (crate::owner(3), 4),
        (AccountId::Public(crate::treasury()), 2),
    ] {
        assert_eq!(
            economy(&t.state)
                .book
                .cash(id)
                .expect("the fixture book holds the payer account"),
            crate::money(expected)
        );
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
        economy(&t.state)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        crate::money(15)
    );
}
#[test]
fn public_provider_funding_reaches_actual_work_and_service_and_withdrawal_severs_it() {
    let mut state = service_opening([0, 13, 0, 0, 2]);
    let f = &mut crate::economy_mut(&mut state).financial;
    f.public_budgets.push(PublicBudget {
        public_account: crate::treasury(),
        period_cap: crate::money(2),
        cash_floor: crate::money(0),
    });
    f.public_allocations.push(PublicAllocation {
        public_account: crate::treasury(),
        recipient: AccountId::Site(crate::site()),
        treatment: PublicTransferTreatment::ProviderOperatingGrant,
        priority: 0,
        amount_per_period: crate::money(2),
    });
    let funded = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
    assert_eq!(funded.production[0].produced_batches, 1);
    assert_eq!(funded.household_services[0].satisfied_quantity, 1);
    assert_eq!(
        income(&funded, AccountId::Site(crate::site()))
            .statement
            .public_transfer_income,
        crate::money(2)
    );
    crate::economy_mut(&mut state).financial.public_budgets[0].period_cap = crate::money(0);
    let withdrawn = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
    assert_eq!(withdrawn.production[0].produced_batches, 0);
    assert_eq!(withdrawn.household_services[0].unmet_quantity, 1);
    assert_eq!(withdrawn.public_budgets[0].unfunded, crate::money(2));
    assert_eq!(
        economy(&withdrawn.state)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        crate::money(15)
    );
}
#[test]
fn tax_shortfall_records_current_uncollected_amount_without_minting_debt() {
    let mut state = service_opening([2, 13, 0, 0, 0]);
    crate::economy_mut(&mut state)
        .financial
        .taxes
        .push(TaxPolicy {
            payer: AccountId::Site(crate::site()),
            public_recipient: crate::treasury(),
            basis: TaxBasis::PositiveOperatingIncome,
            rate_bps: 10000,
            cash_floor: crate::money(14),
        });
    let t = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
    assert_eq!(t.taxes[0].assessed, crate::money(9));
    assert_eq!(t.taxes[0].collected, crate::money(1));
    assert_eq!(t.taxes[0].uncollected, crate::money(8));
    assert_eq!(
        income(&t, AccountId::Public(crate::treasury()))
            .statement
            .tax_income,
        crate::money(1)
    );
    assert_eq!(
        income(&t, AccountId::Site(crate::site()))
            .statement
            .tax_expense,
        crate::money(1)
    );
    assert!(economy(&t.state).book.snapshot().shifts.is_empty());
    assert_eq!(
        economy(&t.state)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        crate::money(15)
    );
}
#[test]
fn late_financial_overflow_leaves_all_opening_cash_and_equity_unchanged() {
    let mut state = crate::opening([0, 0, 1, 0, 0]);
    let e = crate::economy_mut(&mut state);
    let mut values = e.costs.snapshot();
    values.equity[0].amount = crate::money(i128::MAX - 1);
    values
        .accounts
        .iter_mut()
        .find(|r| r.account == crate::owner(2))
        .expect("the fixture holds the searched element")
        .opening_capital = crate::money(i128::MAX);
    values
        .accounts
        .iter_mut()
        .find(|r| r.account == AccountId::Site(crate::site()))
        .expect("the fixture holds the searched element")
        .contributed_capital = crate::money(i128::MAX);
    values
        .accounts
        .iter_mut()
        .find(|r| r.account == AccountId::Site(crate::site()))
        .expect("the fixture holds the searched element")
        .retained_earnings = crate::money(-i128::MAX);
    e.costs =
        HistoricalCostBook::from_snapshot(values).expect("the snapshot admits the derived value");
    e.financial.contributions.push(CapitalContributionOrder {
        id: ContributionId::from_bytes([2; 32]),
        due_period: 1,
        contributor: crate::owner(2),
        issuer_site_id: crate::site(),
        amount: crate::money(1),
    });
    let before = babylon_material_circuit::encode_material_circuit_state(&state)
        .expect("the canonical material state encodes");
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&state),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&state)
            .expect("the canonical material state encodes"),
        before
    );
}
