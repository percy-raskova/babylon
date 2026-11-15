//! Replay native funded production, intercompany freight and an outside retailer.
use super::{CompanyBooks, CompanyCarryingLedger};
use crate::identity::CampaignId;
use crate::production_projection::recurring_fixture;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::DistributionPolicy;
use babylon_material_circuit::{
    self, AccountId, CapitalContributionOrder, CashAccount, CircuitAccounting, CompanyId,
    CompanyPayoutPolicy, ContributionId, EquityCarryingValue, FinalDemandPrincipalId,
    HistoricalCostBook, MaterialCatalog, MaterialCircuitState, MonetaryBook, OwnershipClaim,
    SiteId,
};
use babylon_tick::material_world;
use std::collections::BTreeMap;
use uuid::Uuid;
fn fixture() -> (MaterialCatalog, MaterialCircuitState, CompanyBooks) {
    let (catalog, mut state) = recurring_fixture::materials();
    let mut definition = catalog.into_definition();
    let company = CompanyId::from_bytes([9; 32]);
    let treasury = AccountId::Company(company);
    let household = AccountId::Household(FinalDemandPrincipalId::from_bytes([1; 32]));
    let members: BTreeMap<_, _> = [1, 2]
        .into_iter()
        .map(|n| (SiteId::from_bytes([n; 32]), company))
        .collect();
    definition.company_payouts.push(CompanyPayoutPolicy {
        company,
        earnings_bps: 5000,
        claims: vec![(household, 1)],
    });
    let CircuitAccounting::Monetary(m) = &mut state.accounting else {
        panic!("funded fixture");
    };
    let mut money = m.book.snapshot();
    for a in &mut money.accounts {
        if matches!(a.id, AccountId::Site(_)) {
            a.cash = Currency::from_micro_units(100);
        }
    }
    money.accounts.push(CashAccount {
        id: treasury,
        cash: Currency::from_micro_units(20),
    });
    m.book = MonetaryBook::from_snapshot(money).expect("funded treasury");
    let costs = m.costs.snapshot();
    let standalone =
        HistoricalCostBook::open(&m.book, costs.stocks.clone(), vec![], vec![], vec![])
            .expect("member books");
    let mut equity = Vec::new();
    for row in standalone.capital_accounts() {
        if let AccountId::Site(site) = row.account {
            if members.contains_key(&site) {
                m.financial.ownership.push(OwnershipClaim {
                    issuer_site_id: site,
                    beneficiary: treasury,
                    shares: 1,
                });
                equity.push(EquityCarryingValue {
                    owner: treasury,
                    issuer_site_id: site,
                    amount: row.opening_capital,
                });
            }
        }
    }
    m.costs = HistoricalCostBook::open(&m.book, costs.stocks, vec![], equity, vec![])
        .expect("group legal books");
    m.financial.distributions.push(DistributionPolicy {
        issuer_site_id: SiteId::from_bytes([1; 32]),
        earnings_fraction_bps: 5000,
        period_cap: Currency::from_micro_units(100),
        cash_floor: Currency::from_micro_units(0),
    });
    m.financial.contributions.push(CapitalContributionOrder {
        id: ContributionId::from_bytes([8; 32]),
        due_period: 1,
        contributor: treasury,
        issuer_site_id: SiteId::from_bytes([2; 32]),
        amount: Currency::from_micro_units(10),
    });
    let recurring = m.recurring.as_mut().expect("recurring demand");
    recurring.offers[0].unit_price = Currency::from_micro_units(2);
    let books = CompanyBooks {
        members,
        carry: CompanyCarryingLedger::default(),
        next: 1,
    };
    (
        MaterialCatalog::try_new(definition).expect("typed captured companies"),
        state,
        books,
    )
}
#[test]
fn native_freight_sales_and_parent_funding_reconcile_at_every_close() {
    let (catalog, mut state, mut books) = fixture();
    let mut internal = false;
    let mut released = false;
    let mut dividend = false;
    let mut resumed = None;
    let campaign = CampaignId::from_uuid(Uuid::from_u128(99));

    for tick in 1..=6 {
        let t = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("funded native close");
        let wire = material_world::encode_material_receipts(&catalog, tick, &t)
            .expect("seal native order costs");
        let evidence =
            material_world::decode_material_receipts(&wire).expect("read versioned evidence");
        assert_eq!(evidence.company_basis, t.company_basis);
        let rows = books
            .close(&state, &t.state, &evidence)
            .expect("all three legal and group statements reconcile");
        if let Some(prior) = &mut resumed {
            let recovered: &mut CompanyBooks = prior;
            assert_eq!(
                recovered
                    .close(&state, &t.state, &evidence)
                    .expect("recovered company ledger"),
                rows
            );
        }
        let r = &rows[0];
        if resumed.is_none() && r.eliminations.closing_unrealized_margin.micro_units() != 0 {
            let (_, _, mut recovered) = fixture();
            let (mut bytes, hash) = books
                .checkpoint(campaign, [1; 32], [2; 32])
                .expect("close seed with unreleased margin");
            assert!(recovered
                .restore(campaign, [9; 32], [2; 32], tick + 1, &bytes, hash)
                .is_err());
            bytes.push(0);
            assert!(recovered
                .restore(campaign, [1; 32], [2; 32], tick + 1, &bytes, hash)
                .is_err());
            bytes.pop();
            recovered
                .restore(campaign, [1; 32], [2; 32], tick + 1, &bytes, hash)
                .expect("exact seed");
            resumed = Some(recovered);
        }
        if tick == 1 {
            assert_eq!(r.eliminations.contributions.micro_units(), 10);
            assert_eq!(r.consolidated.income.contributions.micro_units(), 0);
        }
        internal |= r.eliminations.margin_created.micro_units() > 0;
        dividend |= r.eliminations.distributions.micro_units() > 0;
        released |= r.eliminations.margin_realized.micro_units() > 0;
        assert_eq!(
            r.consolidated.closing.cash.micro_units(),
            r.parent.closing.cash.micro_units() + r.subsidiaries.closing.cash.micro_units()
        );
        state = t.state;
    }
    assert!(
        internal && released && dividend && resumed.is_some(),
        "native internal margin must reach the outside retailer after transit and processing"
    );
}
