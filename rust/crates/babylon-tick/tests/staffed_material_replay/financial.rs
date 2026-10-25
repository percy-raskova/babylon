use crate::site;
use crate::CollectingSink;
use crate::MaterialWorldRegister;
use crate::ReplayCommitDisposition;
use crate::Session;
use crate::MATERIAL_CYCLE;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::CapitalContributionOrder;
use babylon_material_circuit::CashAccount;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::ContributionId;
use babylon_material_circuit::DistributionPolicy;
use babylon_material_circuit::EquityCarryingValue;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::FinancialInstitutions;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::InstitutionLocation;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::OwnershipClaim;
use babylon_material_circuit::PublicAccountId;
use babylon_material_circuit::PublicAllocation;
use babylon_material_circuit::PublicBudget;
use babylon_material_circuit::PublicTransferTreatment;
use babylon_material_circuit::TaxBasis;
use babylon_material_circuit::TaxPolicy;
fn money(n: i128) -> Currency {
    Currency::from_micro_units(n)
}
fn financial_session() -> Session {
    let crate::Materials { catalog, mut state } = crate::paid_material();
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
    e.book = MonetaryBook::from_snapshot(book).expect("the snapshot admits the derived value");
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
    .expect("the fixture opens the authored source");
    e.financial = FinancialInstitutions {
        locations: vec![InstitutionLocation {
            account: AccountId::Public(treasury),
            location: "county:26163"
                .parse()
                .expect("the authored literal parses as the declared type"),
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
    crate::try_session_with_material(
        MATERIAL_CYCLE,
        crate::staffed_labor(),
        crate::Materials { catalog, state },
    )
    .expect("the fixture opens a session with material")
}
#[test]
fn public_ownership_receipts_survive_failed_commit_and_staffed_checkpoint_replay() {
    let mut session = financial_session();
    let mut sink = CollectingSink::default();
    let before = crate::live(&session, &sink);
    let candidate = crate::prepare(&session);
    let receipts = crate::decode_material_receipts(candidate.material().receipt_bytes())
        .expect("the canonical bytes decode into the declared type");
    assert_eq!(receipts.taxes[0].collected, money(40));
    assert_eq!(receipts.public_budgets[0].unfunded, money(10));
    let identity = *candidate.identity();
    assert!(session
        .commit_prepared_and_publish(
            &mut sink,
            candidate,
            |_, _| Err::<ReplayCommitDisposition, _>("financial refusal")
        )
        .is_err());
    assert_eq!(crate::live(&session, &sink), before);
    let retry = crate::prepare(&session);
    assert_eq!(*retry.identity(), identity);
    let graph = retry.graph_report().result_stable_graph().clone();
    let graph_material = crate::owned_checkpoint_rows(retry.graph_report().material_state_rows());
    let registers = retry
        .graph_report()
        .result_registers()
        .canonical_bytes()
        .to_vec();
    let material = retry.material().register().canonical_bytes().to_vec();
    crate::commit(&mut session, &mut sink, retry);
    let mut restored = financial_session();
    restored
        .restore_full_checkpoint(
            &graph,
            &graph_material,
            &registers,
            MaterialWorldRegister::decode_external(session.catalog(), material.clone())
                .expect("the committed canonical bytes decode"),
        )
        .expect("the committed checkpoint restores");
    let mut restored_sink = CollectingSink::default();
    let mut contributed = 0;
    let mut distributed = 0;
    for _ in 2..=4 {
        let next = crate::prepare(&session);
        let replay = crate::prepare(&restored);
        assert_eq!(next.identity(), replay.identity());
        assert_eq!(
            next.material().receipt_bytes(),
            replay.material().receipt_bytes()
        );
        let r = crate::decode_material_receipts(next.material().receipt_bytes())
            .expect("the canonical bytes decode into the declared type");
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
        crate::commit(&mut session, &mut sink, next);
        crate::commit(&mut restored, &mut restored_sink, replay);
    }
    assert_eq!(contributed, 5);
    assert_eq!(distributed, 8);
    assert_eq!(session.material(), restored.material());
    let CircuitAccounting::Monetary(e) = &session.material().state().accounting else {
        panic!("paid")
    };
    assert_eq!(
        e.book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        money(1000)
    );
}
