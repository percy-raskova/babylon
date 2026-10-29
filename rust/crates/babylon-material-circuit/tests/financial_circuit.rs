use babylon_kernel::currency::Currency;
use babylon_kernel::economic_location::{EconomicLocation, ForeignCounterpart};
use babylon_material_circuit::AccountId;
use babylon_material_circuit::AidBook;
use babylon_material_circuit::CapacityReservations;
use babylon_material_circuit::CapacitySupply;
use babylon_material_circuit::CapitalContributionOrder;
use babylon_material_circuit::CashAccount;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::ContributionId;
use babylon_material_circuit::DistributionPolicy;
use babylon_material_circuit::EquityCarryingValue;
use babylon_material_circuit::FinalDemandPrincipal;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::FinancialInstitutions;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::HouseholdTimeAccounting;
use babylon_material_circuit::InstitutionLocation;
use babylon_material_circuit::LogisticsNodeId;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCatalogDefinition;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::MonetaryCircuit;
use babylon_material_circuit::OrganizationAccountId;
use babylon_material_circuit::OwnershipClaim;
use babylon_material_circuit::PublicAccountId;
use babylon_material_circuit::PublicAllocation;
use babylon_material_circuit::PublicBudget;
use babylon_material_circuit::PublicTransferTreatment;
use babylon_material_circuit::SiteId;
use babylon_material_circuit::SiteLogisticsNode;

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
fn opening(cash: [i128; 5]) -> (MaterialCatalog, MaterialCircuitState) {
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
    .expect("the fixture opens the authored source");
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
        vec![],
    )
    .expect("the fixture opens the authored source");
    let catalog = MaterialCatalogDefinition {
        capacity_policy: CapacitySupply::FiniteSchedule,
        site_logistics_nodes: vec![SiteLogisticsNode {
            site_id: site(),
            node_id: LogisticsNodeId::from_bytes([1; 32]),
        }],
        process_outputs: vec![],
        input_coefficients: vec![],
        labor_coefficients: vec![],
        commodities: vec![],
        supplier_routes: vec![],
        route_stages: vec![],
        merchants: vec![],
        handling_coefficients: vec![],
        maintenance_binding: None,
        aid_mandates: vec![],
        household_time_policy: vec![],
        service_inputs: vec![],
        household_needs: vec![],
    };
    let state = MaterialCircuitState {
        period: 1,
        accounting: CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
            aid: AidBook::default(),

            household_time: HouseholdTimeAccounting::NotModeled,
            member_labor: vec![],
            book,
            costs,
            recurring: None,
            employment: vec![],
            financial: financial(),
        })),
        service_connections: vec![],
        service_orders: vec![],
        route_stage_capacities: vec![],
        inventory: vec![],
        orders: vec![],
        freight: vec![],
        corridor_capacities: vec![],
        capacities: vec![],
        labor: vec![],
        production_commitments: vec![],
        final_demand_principals: vec![FinalDemandPrincipal {
            id: household(),
            location: EconomicLocation::Foreign(ForeignCounterpart::Canada),
        }],
        final_demand_orders: vec![],
        maintenance_service: None,
        capacity_reservations: CapacityReservations::default(),
    };
    (
        MaterialCatalog::try_new(catalog).expect("the authored fixture catalog is valid"),
        state,
    )
}
fn resealed(
    catalog: MaterialCatalog,
    mutate: impl FnOnce(&mut MaterialCatalogDefinition),
) -> MaterialCatalog {
    let mut catalog = catalog.into_definition();
    mutate(&mut catalog);

    MaterialCatalog::try_new(catalog).expect("the rebuilt fixture catalog is valid")
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
    let (catalog, mut state) = opening([7, 0, 0, 0, 0]);
    let e = economy_mut(&mut state);
    let mut costs = e.costs.snapshot();
    let capital = costs
        .accounts
        .iter_mut()
        .find(|r| r.account == AccountId::Site(site()))
        .expect("the fixture holds the searched element");
    capital.opening_capital = money(0);
    capital.retained_earnings = money(7);
    e.costs =
        HistoricalCostBook::from_snapshot(costs).expect("the snapshot admits the derived value");
    e.financial.distributions.push(DistributionPolicy {
        issuer_site_id: site(),
        earnings_fraction_bps: 10_000,
        period_cap: money(7),
        cash_floor: money(0),
    });
    let t = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(
        economy(&t.state)
            .book
            .cash(owner(2))
            .expect("the fixture book holds the payer account"),
        money(3)
    );
    assert_eq!(
        economy(&t.state)
            .book
            .cash(owner(3))
            .expect("the fixture book holds the payer account"),
        money(4)
    );
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
        .expect("the fixture holds the searched element");
    assert_eq!(issuer.net_income, money(0));
    assert_eq!(issuer.distributions_paid, money(7));
    assert_eq!(issuer.closing_retained_earnings, money(0));
    assert_eq!(
        economy(&t.state)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        money(7)
    );
    let next = babylon_material_circuit::advance_material_circuit(&catalog, &t.state)
        .expect("the authored material state advances one period");
    let restored = babylon_material_circuit::decode_material_circuit_state(
        &catalog,
        &babylon_material_circuit::encode_material_circuit_state(&catalog, &t.state)
            .expect("the canonical material state encodes"),
    )
    .expect("the canonical material bytes decode");
    assert_eq!(
        next,
        babylon_material_circuit::advance_material_circuit(&catalog, &restored)
            .expect("the authored material state advances one period")
    );
    assert!(next.distributions.iter().all(|r| r.paid == money(0)));
}
#[test]
fn capital_contribution_swaps_cash_for_equity_without_income_or_equipment() {
    let (catalog, mut state) = opening([0, 0, 5, 0, 0]);
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
    let t = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(
        economy(&t.state)
            .book
            .cash(AccountId::Site(site()))
            .expect("the fixture book holds the payer account"),
        money(5)
    );
    assert_eq!(
        economy(&t.state)
            .costs
            .snapshot()
            .equity
            .iter()
            .find(|r| r.owner == owner(2))
            .expect("the fixture holds the searched element")
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
            .expect("the fixture holds the searched element")
            .contributed_capital,
        money(5)
    );
    assert!(t.income.iter().all(|r| r.net_income == money(0)));
    assert_eq!(economy(&t.state).financial.contributions.len(), 0);
    assert_eq!(
        economy(&t.state)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        money(5)
    );
}
#[test]
fn public_support_records_unfunded_budget_without_creating_cash_or_consumption() {
    let (catalog, mut state) = opening([0, 0, 0, 0, 3]);
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
    let t = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(t.public_budgets[0].requested, money(5));
    assert_eq!(t.public_budgets[0].paid, money(3));
    assert_eq!(t.public_budgets[0].unfunded, money(2));
    assert_eq!(
        economy(&t.state)
            .book
            .cash(AccountId::Household(household()))
            .expect("the fixture book holds the payer account"),
        money(3)
    );
    assert_eq!(t.household_consumption.len(), 0);
    assert_eq!(
        economy(&t.state)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        money(3)
    );
}
#[path = "support/financial_edges.rs"]
mod edges;
#[path = "support/financial_operations.rs"]
mod operations;

#[path = "support/household_policy_bounds.rs"]
mod household_policy_bounds;

fn appropriation_state(
    cash: i128,
    floor: i128,
    cap: i128,
    agency_priority: u32,
) -> (MaterialCatalog, MaterialCircuitState) {
    let (catalog, mut state) = opening([0, 0, 0, 0, cash]);
    let f = &mut economy_mut(&mut state).financial;
    f.public_budgets.push(PublicBudget {
        public_account: treasury(),
        period_cap: money(cap),
        cash_floor: money(floor),
    });
    f.public_allocations.extend([
        PublicAllocation {
            public_account: treasury(),
            recipient: owner(2),
            treatment: PublicTransferTreatment::AgencyAppropriation,
            priority: agency_priority,
            amount_per_period: money(20),
        },
        PublicAllocation {
            public_account: treasury(),
            recipient: AccountId::Household(household()),
            treatment: PublicTransferTreatment::HouseholdIncomeSupport,
            priority: 1 - agency_priority,
            amount_per_period: money(20),
        },
    ]);
    (catalog, state)
}

#[test]
fn agency_appropriation_uses_ordered_opening_cash_and_reconciles_income() {
    for agency_priority in [0, 1] {
        let (catalog, state) = appropriation_state(30, 0, 40, agency_priority);
        let result = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("funded opening advances");
        assert_eq!(
            result
                .public_budgets
                .iter()
                .map(|r| (r.paid, r.unfunded))
                .collect::<Vec<_>>(),
            [(money(20), money(0)), (money(10), money(10))]
        );
        let agency_paid = if agency_priority == 0 {
            money(20)
        } else {
            money(10)
        };
        assert_eq!(
            economy(&result.state)
                .book
                .cash(owner(2))
                .expect("the authored fixture is valid"),
            agency_paid
        );
        assert_eq!(
            economy(&result.state)
                .book
                .cash(AccountId::Public(treasury()))
                .expect("the authored fixture is valid"),
            money(0)
        );
        assert_eq!(
            economy(&result.state)
                .book
                .total_cash_and_reserves()
                .expect("the authored fixture is valid"),
            money(30)
        );
        let public = result
            .income
            .iter()
            .find(|r| r.account == AccountId::Public(treasury()))
            .expect("the authored fixture is valid");
        let agency = result
            .income
            .iter()
            .find(|r| r.account == owner(2))
            .expect("the authored fixture is valid");
        assert_eq!(public.statement.public_transfer_expense, money(30));
        assert_eq!(agency.statement.public_transfer_income, agency_paid);
        assert_eq!(agency.net_income, agency_paid);
        assert_eq!(public.net_income, money(-30));
        assert_eq!(result.household_consumption.len(), 0);
        assert_eq!(
            economy(&result.state).employment,
            economy(&state).employment
        );
        let bytes =
            babylon_material_circuit::encode_material_circuit_state(&catalog, &result.state)
                .expect("the authored fixture is valid");
        let restored = babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
            .expect("the authored fixture is valid");
        assert_eq!(restored, result.state);
        let next = babylon_material_circuit::advance_material_circuit(&catalog, &restored)
            .expect("the authored fixture is valid");
        assert_eq!(next.public_budgets.len(), 2);
        assert!(next
            .public_budgets
            .iter()
            .all(|r| r.paid == money(0) && r.unfunded == money(20)));
        let mut reversed = state.clone();
        economy_mut(&mut reversed)
            .financial
            .public_allocations
            .reverse();
        assert_eq!(
            result,
            babylon_material_circuit::advance_material_circuit(&catalog, &reversed)
                .expect("the authored fixture is valid")
        );
        assert_eq!(
            babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
                .expect("the authored fixture is valid"),
            babylon_material_circuit::encode_material_circuit_state(&catalog, &reversed)
                .expect("the authored fixture is valid")
        );
    }
}

#[test]
fn agency_appropriation_respects_cash_floor_and_cap() {
    for (cash, floor, cap, paid) in [(0, 0, 40, 0), (30, 25, 40, 5), (30, 0, 7, 7)] {
        let (catalog, state) = appropriation_state(cash, floor, cap, 0);
        let result = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored fixture is valid");
        assert_eq!(result.public_budgets[0].paid, money(paid));
        assert_eq!(result.public_budgets[0].unfunded, money(20 - paid));
        assert_eq!(result.public_budgets[1].paid, money(0));
        assert_eq!(
            economy(&result.state)
                .book
                .total_cash_and_reserves()
                .expect("the authored fixture is valid"),
            money(cash)
        );
    }
}

#[test]
fn agency_appropriation_rejects_invalid_inputs_without_mutating_opening() {
    use babylon_material_circuit::MaterialCircuitError;
    let (catalog, valid) = appropriation_state(30, 0, 40, 0);
    for recipient in [
        AccountId::Household(household()),
        AccountId::Site(site()),
        AccountId::Public(treasury()),
    ] {
        let mut invalid = valid.clone();
        economy_mut(&mut invalid).financial.public_allocations[0].recipient = recipient;
        let before = invalid.clone();
        assert_eq!(
            babylon_material_circuit::advance_material_circuit(&catalog, &invalid),
            Err(MaterialCircuitError::FinancialInvariant)
        );
        assert_eq!(invalid, before);
    }
    for treatment in [
        PublicTransferTreatment::HouseholdIncomeSupport,
        PublicTransferTreatment::ProviderOperatingGrant,
    ] {
        let mut invalid = valid.clone();
        economy_mut(&mut invalid).financial.public_allocations[0].treatment = treatment;
        assert_eq!(
            babylon_material_circuit::advance_material_circuit(&catalog, &invalid),
            Err(MaterialCircuitError::FinancialInvariant)
        );
    }
    let mut duplicate = valid.clone();
    let row = economy(&duplicate).financial.public_allocations[0].clone();
    economy_mut(&mut duplicate)
        .financial
        .public_allocations
        .push(row);
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &duplicate),
        Err(MaterialCircuitError::DuplicateRow)
    );
    let mut missing_budget = valid.clone();
    economy_mut(&mut missing_budget)
        .financial
        .public_budgets
        .clear();
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &missing_budget),
        Err(MaterialCircuitError::FinancialInvariant)
    );
    let mut missing_location = valid.clone();
    economy_mut(&mut missing_location)
        .financial
        .locations
        .retain(|r| r.account != owner(2));
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &missing_location),
        Err(MaterialCircuitError::FinancialInvariant)
    );
}

#[test]
fn appropriation_state_wire_rejects_unknown_treatment_and_missing_account() {
    use babylon_material_circuit::MaterialCircuitError;
    let (catalog, mut state) = appropriation_state(30, 0, 40, 0);
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the authored fixture is valid");
    let mut needle = Vec::new();
    needle.extend_from_slice(&treasury().as_bytes());
    needle.push(3);
    needle.extend_from_slice(&[2; 32]);
    needle.push(3);
    needle.extend_from_slice(&0_u32.to_be_bytes());
    needle.extend_from_slice(&20_i128.to_be_bytes());
    let locations: Vec<_> = bytes
        .windows(needle.len())
        .enumerate()
        .filter_map(|(i, w)| (w == needle).then_some(i))
        .collect();
    assert_eq!(locations.len(), 1);
    let mut malformed = bytes;
    malformed[locations[0] + 65] = 9;
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&catalog, &malformed),
        Err(MaterialCircuitError::WireEnum)
    );
    economy_mut(&mut state).financial.public_allocations[0].recipient = owner(99);
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state),
        Err(MaterialCircuitError::MonetaryInvariant)
    );
}
