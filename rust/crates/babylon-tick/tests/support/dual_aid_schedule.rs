//! Designed finite opening for competing and separated aid practices.
use super::organizer_aid_fixture;
use super::organizer_aid_fixture::{Session, MATERIAL, PRACTICE, PRODUCTS};
use babylon_material_circuit::{
    AccountId, CashAccount, CircuitAccounting, FinalDemandPrincipal, FinalDemandPrincipalId,
    HistoricalCostBook, HouseholdTimeAccounting, MaterialCircuitState, MonetaryBook,
    StockCarryingValue,
};
use babylon_practice_contract::{
    OrganizerAidKind, OrganizerConfig, OrganizerHouseholdBinding, OrganizerPartnerPolicy,
    OrganizerTimeBindingMode,
};

fn remote_principal() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([77; 32])
}

fn opening() -> MaterialCircuitState {
    let mut state = organizer_aid_fixture::aid_opening(false);
    let remote = remote_principal();
    state.final_demand_principals.push(FinalDemandPrincipal {
        id: remote,
        location: state.final_demand_principals[0].location,
    });
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        unreachable!()
    };
    let rows = e.recurring.as_mut().unwrap();
    let mut cohort = rows
        .households
        .iter()
        .find(|r| r.principal_id == organizer_aid_fixture::recipient())
        .unwrap()
        .clone();
    cohort.principal_id = remote;
    rows.households.push(cohort);
    let mut stock = rows
        .household_stocks
        .iter()
        .find(|r| r.principal_id == organizer_aid_fixture::recipient())
        .unwrap()
        .clone();
    stock.principal_id = remote;
    rows.household_stocks.push(stock);
    let mut need = rows
        .household_needs
        .iter()
        .find(|r| r.principal_id == organizer_aid_fixture::recipient())
        .unwrap()
        .clone();
    need.principal_id = remote;
    rows.household_needs.push(need);
    let mut purchase = rows
        .household_purchases
        .iter()
        .find(|r| r.principal_id == organizer_aid_fixture::recipient())
        .unwrap()
        .clone();
    purchase.principal_id = remote;
    rows.household_purchases.push(purchase);
    rows.household_stocks
        .iter_mut()
        .find(|r| r.principal_id == organizer_aid_fixture::household())
        .unwrap()
        .quantity = 32;
    let HouseholdTimeAccounting::Modeled(time) = &mut e.household_time else {
        unreachable!()
    };
    let mut policy = time
        .policies
        .iter()
        .find(|r| r.principal_id == organizer_aid_fixture::recipient())
        .unwrap()
        .clone();
    policy.principal_id = remote;
    time.policies.push(policy);
    e.aid.mandates[0].maximum_quantity = 1;
    let mut remote_mandate = organizer_aid_fixture::mandate(true);
    remote_mandate.id = [93; 32];
    remote_mandate.source_hash = [94; 32];
    remote_mandate.recipient = remote;
    remote_mandate.recipient_actor = 121;
    remote_mandate.maximum_quantity = 1;
    e.aid.mandates.push(remote_mandate);
    let mut stocks = e.costs.snapshot().stocks;
    stocks
        .iter_mut()
        .find(|r| {
            r.owner == AccountId::Household(organizer_aid_fixture::household())
                && r.good_id == organizer_aid_fixture::good(2)
        })
        .unwrap()
        .amount = organizer_aid_fixture::money(128);
    stocks.push(StockCarryingValue {
        owner: AccountId::Household(remote),
        good_id: organizer_aid_fixture::good(2),
        unit_id: organizer_aid_fixture::units(),
        amount: organizer_aid_fixture::money(0),
    });
    // Finite100 micros and32 donor units; no later injection or protected-floor exemption.
    e.book = MonetaryBook::open(
        [
            (AccountId::Site(organizer_aid_fixture::site(1)), 4),
            (AccountId::Site(organizer_aid_fixture::site(2)), 32),
            (AccountId::Site(organizer_aid_fixture::site(3)), 32),
            (AccountId::Household(organizer_aid_fixture::household()), 32),
            (AccountId::Household(organizer_aid_fixture::recipient()), 0),
            (AccountId::Household(remote), 0),
        ]
        .into_iter()
        .map(|(id, cash)| CashAccount {
            id,
            cash: organizer_aid_fixture::money(cash),
        })
        .collect(),
    )
    .unwrap();
    e.costs = HistoricalCostBook::open(&e.book, stocks, vec![], vec![], vec![]).unwrap();
    state
}

fn organizer(refuses_remote: bool) -> OrganizerConfig {
    let mut cfg = organizer_aid_fixture::config();
    let controlled = cfg
        .participants
        .iter_mut()
        .find(|r| r.contributor_id == 201)
        .unwrap();
    controlled.available_hours = 8;
    controlled.commitments[0].hours = 2;
    cfg.contact_hours = 2;
    cfg.aid_bindings[0].coordination_hours = 2;
    let mut participant = cfg
        .participants
        .iter()
        .find(|r| r.contributor_id == 204)
        .unwrap()
        .clone();
    participant.contributor_id = 205;
    participant.commitments[0].actor_id = 121;
    cfg.participants.push(participant);
    let OrganizerTimeBindingMode::Household { bindings } = &mut cfg.time_binding else {
        unreachable!()
    };
    bindings.push(OrganizerHouseholdBinding {
        contributor_id: 205,
        principal_id: remote_principal().as_bytes(),
    });
    let mut binding = cfg.aid_bindings[0].clone();
    binding.kind = OrganizerAidKind::Remote;
    binding.mandate_id = [93; 32];
    binding.source_hash = [94; 32];
    binding.recipient_contributor_id = 205;
    binding.recipient_principal_id = remote_principal().as_bytes();
    binding.social_class_target = [98; 32];
    binding.partner.actor_id = 121;
    binding.partner.authority_id = [21; 16];
    if refuses_remote {
        binding.partner.policy = OrganizerPartnerPolicy::Refuse;
    }
    cfg.aid_bindings.push(binding);
    cfg
}

pub(super) fn session(refuses_remote: bool) -> Session {
    organizer_aid_fixture::try_session(
        crate::michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation().unwrap(),
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        opening(),
        organizer(refuses_remote),
    )
    .unwrap()
}
