use super::*;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::*;
fn money(n: i128) -> Currency {
    Currency::from_micro_units(n)
}
fn financial_session() -> Session {
    let mut state = paid_material();
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!("paid")
    };
    let household = AccountId::Household(FinalDemandPrincipalId::from_bytes([30; 32]));
    let treasury = PublicAccountId::from_bytes([8; 32]);
    let mut book = e.book.snapshot();
    book.accounts.push(CashAccount {
        id: AccountId::Public(treasury),
        cash: money(0),
    });
    e.book = MonetaryBook::from_snapshot(book).unwrap();
    e.costs = HistoricalCostBook::open(
        &e.book,
        e.costs.snapshot().stocks,
        vec![],
        vec![EquityCarryingValue {
            owner: household,
            issuer_site_id: site(2),
            amount: money(0),
        }],
        vec![],
    )
    .unwrap();
    e.financial = FinancialInstitutions {
        locations: vec![InstitutionLocation {
            account: AccountId::Public(treasury),
            location: "county:26163".parse().unwrap(),
        }],
        ownership: vec![OwnershipClaim {
            issuer_site_id: site(2),
            beneficiary: household,
            shares: 1,
        }],
        distributions: vec![DistributionPolicy {
            issuer_site_id: site(2),
            earnings_fraction_bps: 10000,
            period_cap: money(100),
            cash_floor: money(0),
        }],
        taxes: vec![TaxPolicy {
            payer: household,
            public_recipient: treasury,
            basis: TaxBasis::WageIncome,
            rate_bps: 2500,
            cash_floor: money(0),
        }],
        public_budgets: vec![PublicBudget {
            public_account: treasury,
            period_cap: money(10),
            cash_floor: money(0),
        }],
        public_allocations: vec![PublicAllocation {
            public_account: treasury,
            recipient: household,
            treatment: PublicTransferTreatment::HouseholdIncomeSupport,
            priority: 0,
            amount_per_period: money(10),
        }],
        contributions: vec![CapitalContributionOrder {
            id: ContributionId::from_bytes([7; 32]),
            due_period: 2,
            contributor: household,
            issuer_site_id: site(2),
            amount: money(5),
        }],
    };
    try_session_with_material(MATERIAL_CYCLE, staffed_labor(), state).unwrap()
}
#[test]
fn public_ownership_receipts_survive_failed_commit_and_staffed_checkpoint_replay() {
    let mut session = financial_session();
    let mut sink = CollectingSink::default();
    let before = live(&session, &sink);
    let candidate = prepare(&session);
    let receipts = decode_material_receipts(candidate.material().receipt_bytes()).unwrap();
    assert_eq!(receipts.taxes[0].collected, money(40));
    assert_eq!(receipts.public_budgets[0].unfunded, money(10));
    let identity = *candidate.identity();
    assert!(session
        .commit_prepared_and_publish(&mut sink, candidate, |_| Err::<ReplayCommitDisposition, _>(
            "financial refusal"
        ))
        .is_err());
    assert_eq!(live(&session, &sink), before);
    let retry = prepare(&session);
    assert_eq!(*retry.identity(), identity);
    let graph = retry.graph_report().result_stable_graph().clone();
    let graph_material = owned_checkpoint_rows(retry.graph_report().material_state_rows());
    let registers = retry
        .graph_report()
        .result_registers()
        .canonical_bytes()
        .to_vec();
    let material = retry.material().register().canonical_bytes().to_vec();
    commit(&mut session, &mut sink, retry);
    let mut restored = financial_session();
    restored
        .restore_full_checkpoint(&graph, &graph_material, &registers, &material)
        .unwrap();
    let mut restored_sink = CollectingSink::default();
    let mut contributed = 0;
    let mut distributed = 0;
    for _ in 2..=4 {
        let next = prepare(&session);
        let replay = prepare(&restored);
        assert_eq!(next.identity(), replay.identity());
        assert_eq!(
            next.material().receipt_bytes(),
            replay.material().receipt_bytes()
        );
        let r = decode_material_receipts(next.material().receipt_bytes()).unwrap();
        contributed += r
            .contributions
            .iter()
            .map(|r| r.paid.micro_units())
            .sum::<i128>();
        distributed += r
            .distributions
            .iter()
            .map(|r| r.paid.micro_units())
            .sum::<i128>();
        commit(&mut session, &mut sink, next);
        commit(&mut restored, &mut restored_sink, replay);
    }
    assert_eq!(contributed, 5);
    assert_eq!(distributed, 8);
    assert_eq!(session.material(), restored.material());
    let CircuitAccounting::Monetary(e) = &session.material().state().accounting else {
        panic!("paid")
    };
    assert_eq!(e.book.total_cash_and_reserves().unwrap(), money(1000));
}
