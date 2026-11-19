//! Due capital, actual purchases and rejected alternatives on the equipment fixture.
use babylon_material_circuit::{
    AccountId, CashAccount, CompanyConditionOrder, CompanyId, CompanyPayoutPolicy,
    CompanyPortfolio, CompanyPortfolioPolicy, CompanyPortfolioRegister, CompanyPortfolioSelection,
    DistributionPolicy, EquityCarryingValue, HistoricalCostBook, LaborCapacityRow, MaterialCatalog,
    MaterialCircuitError, MaterialCircuitState, MaterialCircuitTransition, MemberLaborCapacityRow,
    MonetaryBook, OwnershipClaim, StaffingMemberId,
};
fn company_equipment() -> (MaterialCatalog, MaterialCircuitState, CompanyId) {
    let (mut catalog, mut start) = super::opening();
    super::configure_investment(&mut catalog, &mut start, 2, 0);
    let id = CompanyId::from_bytes([9; 32]);
    let owner = AccountId::Company(id);
    let mut d = catalog.into_definition();
    d.company_portfolios = Some(CompanyPortfolioPolicy {
        condition_order: CompanyConditionOrder::FirstApplicable,
        rows: [
            [70, 30, 0, 0],
            [10, 70, 15, 5],
            [60, 25, 15, 0],
            [10, 10, 60, 20],
        ],
        high_utilization_bps: 8000,
        history_periods: 3,
        modest_expansion_bps: 5000,
    });
    d.company_payouts = vec![CompanyPayoutPolicy {
        company: id,
        earnings_bps: 0,
        claims: vec![(AccountId::Household(super::household()), 1)],
    }];
    for r in &mut start.labor {
        r.available = u64::from(r.period == 1);
    }
    let m = super::economy_mut(&mut start);
    for r in &mut m.member_labor {
        r.available_hours = u64::from(r.period == 1);
    }
    m.recurring
        .as_mut()
        .expect("monetary buying policy")
        .attendance[0]
        .planned_hours = 1;
    let mut cash = m.book.snapshot();
    cash.accounts.push(CashAccount {
        id: owner,
        cash: super::money(20),
    });
    m.book = MonetaryBook::from_snapshot(cash).expect("one opening treasury");
    let costs = m.costs.snapshot();
    let value = costs
        .accounts
        .iter()
        .find(|r| r.account == AccountId::Site(super::site()))
        .expect("operating site")
        .opening_capital;
    m.costs = HistoricalCostBook::open(
        &m.book,
        costs.stocks,
        costs.freight,
        vec![EquityCarryingValue {
            owner,
            issuer_site_id: super::site(),
            amount: value,
        }],
        costs.equipment,
    )
    .expect("parent held equity and treasury");
    m.financial.ownership = vec![OwnershipClaim {
        issuer_site_id: super::site(),
        beneficiary: owner,
        shares: 1,
    }];
    m.financial.distributions = vec![DistributionPolicy {
        issuer_site_id: super::site(),
        earnings_fraction_bps: 0,
        period_cap: super::money(0),
        cash_floor: super::money(0),
    }];
    (
        MaterialCatalog::try_new(d).expect("captured company limits"),
        start,
        id,
    )
}
fn selected(
    catalog: &MaterialCatalog,
    opening: &MaterialCircuitState,
    register: &CompanyPortfolioRegister,
    selections: &[CompanyPortfolioSelection],
) -> Result<MaterialCircuitTransition, MaterialCircuitError> {
    let close = babylon_material_circuit::close_material_period_with_portfolios(
        catalog,
        opening,
        &[],
        &[],
        &[],
        Some(register),
        selections,
    )?;
    let period = close.next_period();
    close.finish_with_workforce(
        catalog,
        vec![LaborCapacityRow {
            site_id: super::site(),
            unit_id: super::hours(),
            period,
            available: 0,
        }],
        vec![MemberLaborCapacityRow {
            member_id: StaffingMemberId::from_bytes([1; 32]),
            period,
            available_hours: 0,
        }],
    )
}
#[test]
fn selected_company_capital_becomes_next_period_cash_and_purchase_after_restart() {
    let (catalog, start, company) = company_equipment();
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &start)
        .expect("company founding defers before a sample");
    assert_eq!(first.investment[0].admitted_units, 0);
    let observed = CompanyPortfolioRegister::observe(&catalog, &start, &first, None)
        .expect("completed material observations");
    let data = observed
        .canonical_bytes(&catalog, &first.state, 1)
        .expect("sealed observations");
    let restored = CompanyPortfolioRegister::decode(&catalog, &first.state, 1, &data)
        .expect("restore the full row and action limits");
    assert_eq!(restored, observed);
    assert_eq!(restored.companies[0].history, vec![super::money(-2)]);
    assert_eq!(restored.companies[0].weights, [70, 30, 0, 0]);
    let replace = CompanyPortfolioSelection {
        company,
        evidence_period: 1,
        portfolio: CompanyPortfolio::ReplacementOnly,
    };
    assert_eq!(
        selected(&catalog, &first.state, &observed, &[]),
        Err(MaterialCircuitError::CompanyPortfolioSelection)
    );
    assert_eq!(
        selected(
            &catalog,
            &first.state,
            &observed,
            &[CompanyPortfolioSelection {
                portfolio: CompanyPortfolio::LargerExpansion,
                ..replace
            }]
        ),
        Err(MaterialCircuitError::CompanyPortfolioSelection)
    );
    let bought = selected(&catalog, &first.state, &restored, &[replace])
        .expect("fund eligible replacement in next period");
    assert_eq!(
        bought,
        selected(&catalog, &first.state, &observed, &[replace]).expect("uninterrupted")
    );
    assert_eq!(bought.contributions.len(), 1);
    assert_eq!(
        bought.contributions[0].contributor,
        AccountId::Company(company)
    );
    assert_eq!(bought.contributions[0].paid, super::money(20));
    assert_eq!(bought.investment[0].admitted_units, 1);
    assert_eq!(bought.state.orders.len(), 1);
    assert_eq!(bought.state.capacity_reservations.equipment.cohorts, []);
    assert_eq!(
        super::economy(&bought.state)
            .book
            .cash(AccountId::Company(company))
            .expect("the buying company has a treasury account"),
        super::money(0)
    );
    let deferred = selected(
        &catalog,
        &first.state,
        &restored,
        &[CompanyPortfolioSelection {
            portfolio: CompanyPortfolio::Defer,
            ..replace
        }],
    )
    .expect("defer");
    assert_eq!(deferred.contributions, []);
    assert_eq!(deferred.investment[0].admitted_units, 0);
}
