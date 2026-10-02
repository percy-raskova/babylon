use babylon_kernel::{
    currency::Currency,
    economic_location::{EconomicLocation, ForeignCounterpart},
};
use babylon_material_circuit::*;

fn money(n: i128) -> Currency {
    Currency::from_micro_units(n)
}
fn site() -> SiteId {
    SiteId::from_bytes([1; 32])
}
fn household() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([9; 32])
}
fn owner(n: u8) -> AccountId {
    AccountId::Organization(OrganizationAccountId::from_bytes([n; 32]))
}
fn treasury() -> PublicAccountId {
    PublicAccountId::from_bytes([8; 32])
}
fn financial() -> FinancialInstitutions {
    FinancialInstitutions {
        locations: vec![
            InstitutionLocation {
                account: owner(2),
                location: EconomicLocation::Foreign(ForeignCounterpart::China),
            },
            InstitutionLocation {
                account: owner(3),
                location: EconomicLocation::Foreign(ForeignCounterpart::Canada),
            },
            InstitutionLocation {
                account: AccountId::Public(treasury()),
                location: EconomicLocation::Foreign(ForeignCounterpart::Canada),
            },
        ],
        ownership: vec![
            OwnershipClaim {
                issuer_site_id: site(),
                beneficiary: owner(2),
                shares: 1,
            },
            OwnershipClaim {
                issuer_site_id: site(),
                beneficiary: owner(3),
                shares: 2,
            },
        ],
        distributions: vec![],
        taxes: vec![],
        public_budgets: vec![],
        public_allocations: vec![],
        contributions: vec![],
    }
}
fn opening(cash: [i128; 5]) -> MaterialCircuitState {
    let book = MonetaryBook::open(
        [
            AccountId::Site(site()),
            AccountId::Household(household()),
            owner(2),
            owner(3),
            AccountId::Public(treasury()),
        ]
        .into_iter()
        .zip(cash)
        .map(|(id, n)| CashAccount { id, cash: money(n) })
        .collect(),
    )
    .unwrap();
    let costs = HistoricalCostBook::open(
        &book,
        vec![],
        vec![],
        vec![
            EquityCarryingValue {
                owner: owner(2),
                issuer_site_id: site(),
                amount: money(0),
            },
            EquityCarryingValue {
                owner: owner(3),
                issuer_site_id: site(),
                amount: money(0),
            },
        ],
    )
    .unwrap();
    MaterialCircuitState {
        capacity_supply: CapacitySupply::FiniteSchedule,
        period: 1,
        accounting: CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
            book,
            costs,
            recurring: None,
            employment: vec![],
            financial: financial(),
        })),
        site_logistics_nodes: vec![SiteLogisticsNode {
            site_id: site(),
            node_id: LogisticsNodeId::from_bytes([1; 32]),
        }],
        process_outputs: vec![],
        input_coefficients: vec![],
        labor_coefficients: vec![],
        commodities: vec![],
        service_connections: vec![],
        service_orders: vec![],
        supplier_routes: vec![],
        route_stages: vec![],
        route_stage_capacities: vec![],
        inventory: vec![],
        orders: vec![],
        backlog: vec![],
        freight: vec![],
        corridor_capacities: vec![],
        capacities: vec![],
        labor: vec![],
        production_commitments: vec![],
        merchants: vec![],
        handling_coefficients: vec![],
        final_demand_principals: vec![FinalDemandPrincipal {
            id: household(),
            location: EconomicLocation::Foreign(ForeignCounterpart::Canada),
        }],
        final_demand_orders: vec![],
        maintenance_binding: None,
        maintenance_service: None,
    }
}
fn economy(state: &MaterialCircuitState) -> &MonetaryCircuit {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        panic!("paid")
    };
    e
}
fn economy_mut(state: &mut MaterialCircuitState) -> &mut MonetaryCircuit {
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!("paid")
    };
    e
}
#[test]
fn ownership_distributes_retained_cash_once_with_exact_remainder_and_restart() {
    let mut state = opening([7, 0, 0, 0, 0]);
    let e = economy_mut(&mut state);
    let mut costs = e.costs.snapshot();
    let capital = costs
        .accounts
        .iter_mut()
        .find(|r| r.account == AccountId::Site(site()))
        .unwrap();
    capital.opening_capital = money(0);
    capital.retained_earnings = money(7);
    e.costs = HistoricalCostBook::from_snapshot(costs).unwrap();
    e.financial.distributions.push(DistributionPolicy {
        issuer_site_id: site(),
        earnings_fraction_bps: 10_000,
        period_cap: money(7),
        cash_floor: money(0),
    });
    let t = advance_material_circuit(&state).unwrap();
    assert_eq!(economy(&t.state).book.cash(owner(2)).unwrap(), money(3));
    assert_eq!(economy(&t.state).book.cash(owner(3)).unwrap(), money(4));
    assert_eq!(
        t.distributions
            .iter()
            .map(|r| r.paid.micro_units())
            .sum::<i128>(),
        7
    );
    let issuer = t
        .income
        .iter()
        .find(|r| r.account == AccountId::Site(site()))
        .unwrap();
    assert_eq!(issuer.net_income, money(0));
    assert_eq!(issuer.distributions_paid, money(7));
    assert_eq!(issuer.closing_retained_earnings, money(0));
    assert_eq!(
        economy(&t.state).book.total_cash_and_reserves().unwrap(),
        money(7)
    );
    let next = advance_material_circuit(&t.state).unwrap();
    let restored =
        decode_material_circuit_state(&encode_material_circuit_state(&t.state).unwrap()).unwrap();
    assert_eq!(next, advance_material_circuit(&restored).unwrap());
    assert!(next.distributions.iter().all(|r| r.paid == money(0)));
}
#[test]
fn capital_contribution_swaps_cash_for_equity_without_income_or_equipment() {
    let mut state = opening([0, 0, 5, 0, 0]);
    economy_mut(&mut state)
        .financial
        .contributions
        .push(CapitalContributionOrder {
            id: ContributionId::from_bytes([1; 32]),
            due_period: 1,
            contributor: owner(2),
            issuer_site_id: site(),
            amount: money(5),
        });
    let t = advance_material_circuit(&state).unwrap();
    assert_eq!(
        economy(&t.state)
            .book
            .cash(AccountId::Site(site()))
            .unwrap(),
        money(5)
    );
    assert_eq!(
        economy(&t.state)
            .costs
            .snapshot()
            .equity
            .iter()
            .find(|r| r.owner == owner(2))
            .unwrap()
            .amount,
        money(5)
    );
    assert_eq!(
        economy(&t.state)
            .costs
            .snapshot()
            .accounts
            .iter()
            .find(|r| r.account == AccountId::Site(site()))
            .unwrap()
            .contributed_capital,
        money(5)
    );
    assert!(t.income.iter().all(|r| r.net_income == money(0)));
    assert!(economy(&t.state).financial.contributions.is_empty());
    assert_eq!(t.state.capacity_supply, state.capacity_supply);
    assert_eq!(
        economy(&t.state).book.total_cash_and_reserves().unwrap(),
        money(5)
    );
}
#[test]
fn public_support_records_unfunded_budget_without_creating_cash_or_consumption() {
    let mut state = opening([0, 0, 0, 0, 3]);
    let f = &mut economy_mut(&mut state).financial;
    f.public_budgets.push(PublicBudget {
        public_account: treasury(),
        period_cap: money(5),
        cash_floor: money(0),
    });
    f.public_allocations.push(PublicAllocation {
        public_account: treasury(),
        recipient: AccountId::Household(household()),
        treatment: PublicTransferTreatment::HouseholdIncomeSupport,
        priority: 0,
        amount_per_period: money(5),
    });
    let t = advance_material_circuit(&state).unwrap();
    assert_eq!(t.public_budgets[0].requested, money(5));
    assert_eq!(t.public_budgets[0].paid, money(3));
    assert_eq!(t.public_budgets[0].unfunded, money(2));
    assert_eq!(
        economy(&t.state)
            .book
            .cash(AccountId::Household(household()))
            .unwrap(),
        money(3)
    );
    assert!(t.household_consumption.is_empty());
    assert_eq!(
        economy(&t.state).book.total_cash_and_reserves().unwrap(),
        money(3)
    );
}
#[path = "support/financial_edges.rs"]
mod edges;
#[path = "support/financial_operations.rs"]
mod operations;
