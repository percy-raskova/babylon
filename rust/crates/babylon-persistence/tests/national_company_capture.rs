//! A company-enabled capture overlays the same generated economic workplaces and workforce.
use babylon_graph::stable_element::StableElementKey;
use babylon_graph::substrate::GraphSubstrate;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_location::{EconomicLocation, ForeignCounterpart};
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::{AccountId, CircuitAccounting, MaterialCircuitState, SiteId};
use babylon_persistence::company_statements;
use babylon_persistence::economic_catalog::{
    self, CapturedEconomicCatalog, EconomicCatalogInput, EconomicSiteSeed,
    ResidentStaffingPoolSeed, SourceArtifact, SourceArtifactKind,
};
use babylon_persistence::national_economy::companies::{CompanyCapture, CompanyFinances};
use babylon_tick::company_graph;

use std::collections::{BTreeMap, BTreeSet};

/// Recover the exact pre-company source to compare physical workplace, claim and employment identities.
fn pre_company_input(mut input: EconomicCatalogInput) -> EconomicCatalogInput {
    input
        .sources
        .retain(|source| source.kind() != SourceArtifactKind::NationalAges);
    for source in &mut input.sources {
        let bytes = match source.kind() {
            SourceArtifactKind::NationalGamePolicy => {
                let text = std::str::from_utf8(source.bytes()).expect("current admitted policy");
                let (previous, _) = text
                    .split_once("\n[companies]")
                    .expect("captured company table");
                previous
                    .replacen("schema_version = 6", "schema_version = 2", 1)
                    .into_bytes()
            }
            SourceArtifactKind::Rules => {
                include_bytes!("../../../../content/scenarios/national/material-cycle.bsl").to_vec()
            }
            SourceArtifactKind::GraphDeclarations => {
                include_bytes!("../../../../content/scenarios/national/structure.bscn").to_vec()
            }
            _ => continue,
        };
        *source = SourceArtifact::capture(source.kind(), bytes);
    }
    input
}

#[test]
fn captured_99_company_roster_preserves_sites_and_employment_and_reopens() {
    let mut input = economic_catalog::national_catalog_input();
    let original = original_sites(input.clone());
    // Compare the unchanged pre-claimant company opening to its pre-company source.
    let source = input
        .sources
        .iter_mut()
        .find(|source| source.kind() == SourceArtifactKind::NationalGamePolicy)
        .expect("current national policy");
    let previous = std::str::from_utf8(source.bytes())
        .expect("policy text")
        .split_once(
            "\n# Separate no-earner nonowner households drawn from Wayne's reserve residents.",
        )
        .expect("current claimant policy starts after the previous source")
        .0
        .replacen("schema_version = 6", "schema_version = 5", 1);
    *source = SourceArtifact::capture(source.kind(), previous.into_bytes());
    let capture =
        CapturedEconomicCatalog::capture(input, None).expect("company-enabled national opening");
    assert_eq!(capture.compiler_version(), "national-world-v10");
    assert!(capture.national_support_claimant().is_none());
    let finances = capture
        .national_company_finances()
        .expect("source-bound treasury");
    check_member_cash_and_claims(&capture, finances, original);
    check_treasuries(&capture, finances);
    let plan = capture
        .national_companies()
        .expect("new source records occupied companies");
    check_employment(&capture, plan);
    let finances = finances.clone();
    let plan = plan.clone();
    let bytes = capture.canonical_bytes().to_owned();
    let digest = capture.digest();
    drop(capture);
    let restored =
        CapturedEconomicCatalog::decode(&bytes, digest).expect("restore company-enabled capture");
    assert_eq!(restored.national_companies(), Some(&plan));
    assert_eq!(restored.national_company_finances(), Some(&finances));
    check_graph(restored, &plan);
}

struct OriginalSites {
    sites: Vec<EconomicSiteSeed>,
    staffing: Vec<ResidentStaffingPoolSeed>,
    claims: BTreeMap<(SiteId, AccountId), u64>,
    capital: BTreeMap<SiteId, i128>,
    floors: BTreeMap<SiteId, Currency>,
}

fn original_sites(input: EconomicCatalogInput) -> OriginalSites {
    let legacy = CapturedEconomicCatalog::capture(pre_company_input(input), None)
        .expect("existing national capture");
    assert_eq!(legacy.compiler_version(), "national-world-v7");
    assert!(legacy.national_companies().is_none());
    let opening = legacy.opening();
    let source_claims: BTreeMap<_, _> = opening
        .institutions
        .ownership
        .iter()
        .map(|r| ((r.issuer_site_id, r.beneficiary), r.shares))
        .collect();
    let mut source_capital: BTreeMap<_, _> = opening
        .sites
        .iter()
        .map(|s| {
            let cost: i128 = s
                .opening_stock
                .iter()
                .map(|r| r.total_cost.micro_units())
                .sum();
            (s.site_id, s.opening_cash.micro_units() + cost)
        })
        .collect();
    for row in &opening.equipment {
        *source_capital.get_mut(&row.owner).expect("equipment owner") += row.amount.micro_units();
    }
    assert!(opening.equity.iter().all(|r| r.amount.micro_units() == 0));
    OriginalSites {
        sites: opening.sites.clone(),
        staffing: opening.staffing.clone(),
        claims: source_claims,
        capital: source_capital,
        floors: opening
            .institutions
            .distributions
            .iter()
            .map(|policy| (policy.issuer_site_id, policy.cash_floor))
            .collect(),
    }
}

fn check_member_cash_and_claims(
    capture: &CapturedEconomicCatalog,
    finances: &CompanyFinances,
    original: OriginalSites,
) {
    let OriginalSites {
        mut sites,
        staffing,
        claims: prior_claims,
        capital: prior_capital,
        floors,
    } = original;
    assert_eq!(finances.sweep_bps, 1000);
    assert_eq!(finances.treasuries.len(), 99);
    let prior_cash: i128 = sites
        .iter()
        .map(|site| site.opening_cash.micro_units())
        .sum();
    let auditors: BTreeMap<_, _> = finances.members.iter().map(|r| (r.site, r)).collect();
    for site in &mut sites {
        if let Some(entry) = auditors.get(&site.site_id) {
            assert_eq!(entry.original_cash, site.opening_cash);
            let floor = floors
                .get(&site.site_id)
                .expect("source distribution policy");
            assert_eq!(entry.cash_floor, *floor);
            let excess = (site.opening_cash.micro_units() - floor.micro_units()).max(0);
            assert_eq!(entry.swept.micro_units(), excess / 10);
            assert_eq!(
                entry.remaining_cash.micro_units(),
                site.opening_cash.micro_units() - excess / 10
            );
            site.opening_cash = entry.remaining_cash;
        }
    }
    let transferred: BTreeMap<_, _> = finances
        .sources
        .iter()
        .map(|r| {
            assert_eq!(prior_capital.get(&r.site), Some(&r.capital.micro_units()));
            assert_eq!(r.site_total_shares, 10_000);
            assert_eq!(r.original_carrying_value.micro_units(), 0);
            ((r.site, r.beneficiary), r.original_shares)
        })
        .collect();
    let expected: BTreeMap<_, _> = prior_claims
        .into_iter()
        .filter(|((site, _), _)| auditors.contains_key(site))
        .collect();
    assert_eq!(transferred, expected);
    let japan: BTreeSet<_> = capture
        .opening()
        .households
        .iter()
        .filter(|h| {
            matches!(
                h.location,
                EconomicLocation::Foreign(ForeignCounterpart::Japan)
            )
        })
        .map(|h| AccountId::Household(h.principal_id))
        .collect();
    assert!(finances
        .claims
        .iter()
        .any(|r| japan.contains(&r.beneficiary) && r.weight > 0));
    let subsidiary_cash: i128 = sites
        .iter()
        .map(|site| site.opening_cash.micro_units())
        .sum();
    let central_cash: i128 = finances
        .treasuries
        .iter()
        .map(|r| r.cash.micro_units())
        .sum();
    assert!(central_cash > 0);
    assert_eq!(prior_cash, subsidiary_cash + central_cash);
    assert_eq!(sites, capture.opening().sites);
    eprintln!("v8 national company opening in micros: original site cash {prior_cash}, remaining site cash {subsidiary_cash}, central cash {central_cash}; {} member sites and {} source claims",finances.members.len(),finances.sources.len());
    assert_eq!(staffing, capture.opening().staffing);
}

fn check_consolidated(
    capture: &CapturedEconomicCatalog,
    state: &MaterialCircuitState,
    finances: &CompanyFinances,
) {
    let consolidated = company_statements::project_opening(capture, state)
        .expect("the legal books reconcile at their common foundation");
    assert_eq!(consolidated.len(), 99);
    for group in &consolidated {
        let original_cash: i128 = finances
            .members
            .iter()
            .filter(|m| m.company == group.company)
            .map(|m| m.original_cash.micro_units())
            .sum();
        let original_equity: i128 = finances
            .members
            .iter()
            .filter(|m| m.company == group.company)
            .map(|m| m.original_capital.micro_units())
            .sum();
        assert_eq!(group.consolidated.cash.micro_units(), original_cash);
        assert_eq!(group.consolidated.equity.micro_units(), original_equity);
        assert_eq!(
            group.eliminated_member_investment,
            group.subsidiaries.equity
        );
        assert_eq!(group.parent.investments, group.eliminated_member_investment);
        assert_eq!(
            group.consolidated.assets.micro_units(),
            group.parent.assets.micro_units() + group.subsidiaries.assets.micro_units()
                - group.eliminated_member_investment.micro_units()
        );
    }
}

fn check_treasuries(capture: &CapturedEconomicCatalog, finances: &CompanyFinances) {
    let opening = capture
        .opening()
        .compile()
        .expect("typed company accounts admitted");
    check_consolidated(capture, &opening.state, finances);
    let CircuitAccounting::Monetary(economy) = opening.state.accounting else {
        panic!("monetary national foundation")
    };
    let equity: BTreeMap<_, _> = economy
        .costs
        .snapshot()
        .equity
        .into_iter()
        .map(|r| ((r.owner, r.issuer_site_id), r.amount))
        .collect();
    let account_capital: BTreeMap<_, _> = economy
        .costs
        .capital_accounts()
        .map(|r| (r.account, r.opening_capital))
        .collect();
    for row in &finances.treasuries {
        let company = AccountId::Company(row.company);
        assert_eq!(economy.book.cash(company).expect("central cash"), row.cash);
        assert_eq!(account_capital.get(&company), Some(&row.original_capital));
        assert_eq!(
            row.original_capital.micro_units(),
            row.cash.micro_units() + row.subsidiary_capital.micro_units()
        );
        let total: u128 = finances
            .claims
            .iter()
            .filter(|c| c.company == row.company)
            .map(|c| c.weight)
            .sum();
        assert_eq!(total, row.total_weight);
        assert_eq!(
            total,
            u128::try_from(row.original_capital.micro_units()).expect("positive capital")
                * row.common_denominator
        );
    }
    for row in &finances.members {
        assert_eq!(
            account_capital.get(&AccountId::Site(row.site)),
            Some(&row.remaining_capital)
        );
        assert_eq!(
            equity.get(&(AccountId::Company(row.company), row.site)),
            Some(&row.remaining_capital)
        );
    }
}

fn check_employment(capture: &CapturedEconomicCatalog, plan: &CompanyCapture) {
    assert_eq!(plan.companies.len(), 99);
    assert!(plan.companies.iter().all(|c| c.employed > 0));
    assert_eq!(plan.cells.len(), 81);
    let mut employment = BTreeMap::new();
    for pool in &capture.opening().staffing {
        let quantity: u64 = pool.members.iter().map(|m| m.employed).sum();
        let row = employment.entry(pool.pool.site_id()).or_insert(0_u64);
        *row += quantity;
    }
    let admitted: u64 = plan
        .members
        .iter()
        .map(|row| {
            assert_eq!(
                row.employed,
                employment.get(&row.site).copied().unwrap_or(0)
            );
            row.employed
        })
        .sum();
    assert_eq!(
        admitted,
        plan.cells.iter().map(|c| c.eligible_employed).sum::<u64>()
    );
    assert_eq!(
        admitted,
        plan.companies.iter().map(|c| c.employed).sum::<u64>()
    );
}

fn check_graph(restored: CapturedEconomicCatalog, plan: &CompanyCapture) {
    let session = restored
        .create_foundation(
            ReplaySessionId::try_from("company/registry").expect("session id"),
            ReplaySeed::new(7),
        )
        .expect("company-enabled graph and material capture")
        .into_session()
        .expect("restore authoritative session");
    let graph = session.graph_session();
    let resolver = graph.stable_resolver();
    for row in &plan.companies {
        let key = company_graph::company_key("economy/national-world", row.key.id());
        assert!(resolver
            .sealed_node_has_type(&key, "COMPANY")
            .expect("registered company principal"));
        let StableElementKey::Node { local_name, .. } = &key else {
            panic!("company is a node")
        };
        let handle = resolver
            .node_handle_by_local_name(local_name)
            .expect("sealed company node");
        assert_eq!(resolver.node_key(handle).expect("round trip"), &key);
        for field in company_graph::FIELDS {
            assert_eq!(
                graph
                    .graph()
                    .node_attribute(handle, field)
                    .expect("initialized company field"),
                0.0
            );
        }
    }
}
