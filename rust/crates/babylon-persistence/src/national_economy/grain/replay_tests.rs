//! Resource deprivation reaches the real replay owner, alongside a funded control.
use crate::economic_catalog::{self, CapturedEconomicCatalog, EconomicOpening};
use crate::national_economy::NationalGamePolicy;
use crate::national_household_allocation::HouseholdBudgetKey;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::content_digest;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::{
    AccountId, FinalDemandPrincipalId, GoodId, PublicAccountId, SiteId,
};
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::material_replay::MaterialReplaySession;
use babylon_tick::material_world::{self, MaterialTickReceipts, MaterialWorldRegister};
use babylon_tick::replay_session::ReplayCommitDisposition;
use std::collections::{BTreeMap, BTreeSet};

type Session = MaterialReplaySession<HypergraphStore>;
fn controlled_session(opening: &EconomicOpening) -> Session {
    let foundation =
        CapturedEconomicCatalog::capture(economic_catalog::national_catalog_input(), None)
            .expect("control source capture")
            .create_foundation(
                ReplaySessionId::try_from("grain-domain-control").expect("identity"),
                ReplaySeed::new(319),
            )
            .expect("real graph foundation");
    let compiled = opening.compile().expect("controlled ordinary opening");
    let register = MaterialWorldRegister::try_new(&compiled.catalog, 0, compiled.state)
        .expect("controlled register");
    let digest = content_digest::sha256_of(register.canonical_bytes());
    let duration = foundation.spec().duration;
    MaterialReplaySession::new(
        foundation.graph,
        register,
        compiled.catalog,
        digest,
        duration,
        compiled.staffing,
    )
    .expect("actual controlled replay owner")
}
fn close(mut session: Session) -> MaterialTickReceipts {
    let before = session.material().canonical_bytes().to_vec();
    let actions =
        OrderedPracticeActionBatch::empty(session.graph_session().session_identity().clone(), 1)
            .expect("actions");
    let candidate = session
        .prepare_advance(&actions)
        .expect("valid controlled replay close");
    assert_eq!(
        session.material().canonical_bytes(),
        before,
        "detached candidate cannot publish early"
    );
    let receipts = material_world::decode_material_receipts(candidate.material().receipt_bytes())
        .expect("actual typed receipts");
    session
        .commit_prepared_and_publish(&mut CollectingSink::default(), candidate, |_, _| {
            Ok::<_, ()>(ReplayCommitDisposition::Committed)
        })
        .expect("atomic control commit");
    assert_eq!(session.completed_tick(), 1);
    receipts
}
fn pair(captured: &CapturedEconomicCatalog) -> (FinalDemandPrincipalId, FinalDemandPrincipalId) {
    let opening = captured.opening();
    let budgets: BTreeSet<_> = captured
        .national_generation()
        .expect("witness")
        .household_incidence
        .iter()
        .filter(|i| i.margins.key == HouseholdBudgetKey::NoEarnerNonowner)
        .map(|i| i.destination)
        .collect();
    let taxes: BTreeMap<_, _> = opening
        .institutions
        .taxes
        .iter()
        .map(|t| (t.payer, t.public_recipient))
        .collect();
    for a in &opening.households {
        if !budgets.contains(&a.principal_id) {
            continue;
        }
        if let Some(b) = opening.households.iter().find(|b| {
            b.location == a.location
                && budgets.contains(&b.principal_id)
                && taxes[&AccountId::Household(a.principal_id)]
                    != taxes[&AccountId::Household(b.principal_id)]
        }) {
            return (a.principal_id, b.principal_id);
        }
    }
    panic!("two actual same-hub positions with distinct household budgets")
}
fn public(opening: &EconomicOpening, household: FinalDemandPrincipalId) -> PublicAccountId {
    opening
        .institutions
        .taxes
        .iter()
        .find(|t| t.payer == AccountId::Household(household))
        .expect("domain tax")
        .public_recipient
}
fn employer(opening: &EconomicOpening, public: PublicAccountId) -> SiteId {
    let domains: BTreeMap<_, _> = opening
        .institutions
        .taxes
        .iter()
        .map(|t| (t.payer, t.public_recipient))
        .collect();
    opening
        .sites
        .iter()
        .filter(|site| {
            site.function == EconomicFunction::BusinessServices
                && domains[&AccountId::Site(site.site_id)] == public
        })
        .max_by_key(|site| site.opening_cash)
        .expect("same-position service employer")
        .site_id
}
#[test]
fn starving_position_cannot_spend_colocated_pantry_time_payroll_or_public_budget() {
    let captured =
        CapturedEconomicCatalog::capture(economic_catalog::national_catalog_input(), None)
            .expect("real national capture");
    let (a, b) = pair(&captured);
    let mut control = captured.opening().clone();
    let public_a = public(&control, a);
    let public_b = public(&control, b);
    assert_ne!(public_a, public_b);
    let employer_a = employer(&control, public_a);
    let employer_b = employer(&control, public_b);
    // Both controls isolate B's already-owned pantry from new purchases.
    for purchase in control
        .policies
        .household_purchases
        .iter_mut()
        .filter(|p| p.principal_id == b)
    {
        purchase.enabled = false;
    }
    let mut deprived = control.clone();
    let household = deprived
        .households
        .iter_mut()
        .find(|h| h.principal_id == a)
        .expect("A");
    household.opening_cash = Currency::from_micro_units(0);
    for stock in &mut household.opening_stock {
        stock.amount.quantity = 0;
        stock.total_cost = Currency::from_micro_units(0);
    }
    let households = household.households;
    let time = deprived
        .policies
        .household_time_policy
        .iter_mut()
        .find(|p| p.principal_id == a)
        .expect("A time");
    let endowment = time
        .eligible_persons
        .checked_mul(time.hours_per_eligible_person)
        .expect("time endowment");
    time.protected.hours_per_basis = endowment / households + 1;
    deprived
        .institutional_cash
        .iter_mut()
        .find(|c| c.id == AccountId::Public(public_a))
        .expect("A public")
        .cash = Currency::from_micro_units(0);
    deprived
        .sites
        .iter_mut()
        .find(|s| s.site_id == employer_a)
        .expect("A employer")
        .opening_cash = Currency::from_micro_units(0);
    let funded = close(controlled_session(&control));
    let scarce = close(controlled_session(&deprived));
    let food = NationalGamePolicy::parse(include_str!(
        "../../../../../../content/scenarios/national/defines.toml"
    ))
    .expect("captured food identity")
    .commodities["food"]
        .good_id;
    assert_pantry_and_purchase(&funded, &scarce, a, food);
    assert_owned_time_and_stock(&funded, &scarce, a, b);
    assert_owned_finance(&funded, &scarce, employer_a, employer_b, public_a, public_b);
}
fn assert_pantry_and_purchase(
    funded: &MaterialTickReceipts,
    scarce: &MaterialTickReceipts,
    a: FinalDemandPrincipalId,
    food: GoodId,
) {
    let a_food = scarce
        .household_consumption
        .iter()
        .find(|r| {
            r.principal_id == a
                && r.good_id == food
                && r.required_quantity > 0
                && r.unmet_quantity > 0
        })
        .expect("starving position retains unmet consumption");
    assert_eq!(a_food.available_quantity, 0, "B's pantry cannot satisfy A");
    assert_eq!(a_food.consumed_quantity, 0);
    let funded_food = funded
        .household_consumption
        .iter()
        .find(|r| r.principal_id == a && r.good_id == a_food.good_id)
        .expect("funded control");
    assert_eq!(
        funded_food.unmet_quantity, 0,
        "valid available control consumes its own stock"
    );
    let demand = scarce
        .household_demand
        .iter()
        .find(|r| r.principal_id == a && r.good_id == a_food.good_id)
        .expect("real purchase attempt");
    assert!(demand.desired_quantity > 0);
    assert_eq!(
        demand.admitted_quantity, 0,
        "B's cash cannot buy A's missing food"
    );
}
fn assert_owned_time_and_stock(
    funded: &MaterialTickReceipts,
    scarce: &MaterialTickReceipts,
    a: FinalDemandPrincipalId,
    b: FinalDemandPrincipalId,
) {
    let a_time = scarce
        .household_time
        .iter()
        .find(|r| r.principal_id == a)
        .expect("A time close");
    assert!(
        a_time.endowment_hours > 0,
        "actual labor eligibility remains captured"
    );
    assert_eq!(
        a_time.contribution_available_hours, 0,
        "another position cannot supply missing protected time"
    );
    assert!(a_time.protected_unresolved_hours + a_time.unpaid_unresolved_hours > 0);
    let b_time = scarce
        .household_time
        .iter()
        .find(|r| r.principal_id == b)
        .expect("B time close");
    assert_eq!(
        Some(b_time),
        funded.household_time.iter().find(|r| r.principal_id == b),
        "A cannot debit B's time"
    );
    assert!(b_time.endowment_hours > 0);
    let b_food: Vec<_> = scarce
        .household_consumption
        .iter()
        .filter(|r| r.principal_id == b)
        .collect();
    assert_eq!(
        b_food,
        funded
            .household_consumption
            .iter()
            .filter(|r| r.principal_id == b)
            .collect::<Vec<_>>(),
        "B's pantry close remains its own"
    );
}
fn assert_owned_finance(
    funded: &MaterialTickReceipts,
    scarce: &MaterialTickReceipts,
    employer_a: SiteId,
    employer_b: SiteId,
    public_a: PublicAccountId,
    public_b: PublicAccountId,
) {
    let wages = |r: &MaterialTickReceipts, site| {
        r.wage_accruals
            .iter()
            .filter(|w| w.employer == AccountId::Site(site))
            .map(|w| w.amount.micro_units())
            .sum::<i128>()
    };
    assert!(
        wages(funded, employer_a) > 0,
        "funded employer proves valid payroll demand"
    );
    assert_eq!(
        wages(scarce, employer_a),
        0,
        "A cannot reserve payroll from B's balance"
    );
    assert!(wages(scarce, employer_b) > 0, "B remains funded");
    assert!(
        scarce
            .public_budgets
            .iter()
            .any(|r| r.public_account == public_a && r.unfunded.micro_units() > 0),
        "A retains its own public shortfall"
    );
    assert!(
        scarce
            .public_budgets
            .iter()
            .any(|r| r.public_account == public_b && r.paid.micro_units() > 0),
        "B's funded budget is not pooled into A"
    );
}
