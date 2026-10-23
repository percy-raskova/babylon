//! Post-opening produced food reaches paid donor provision before real authorized aid.
// Shared fixture module contains helpers used by other integration targets.
#[allow(dead_code)]
#[path = "../../babylon-persistence/src/michigan_dynamic_hex_foundation.rs"]
mod michigan_dynamic_hex_foundation;
// This target uses the market-derived session, preserving the other aid fixtures.
#[allow(dead_code)]
#[path = "support/organizer_aid_fixture.rs"]
mod organizer_aid_fixture;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_material_circuit::*;
use babylon_practice_contract::{OrganizerChoice, OrganizerOutcome};
use babylon_tick::material_world::{
    decode_material_receipts, MaterialTickReceipts, MaterialWorldRegister,
};
use organizer_aid_fixture::*;

fn paid_handoff(rows: &MaterialTickReceipts, d: &HouseholdDemandReceipt) -> u64 {
    let actual = rows
        .local_fulfillments
        .iter()
        .find(|r| r.order_id == d.order_id);
    if d.fulfilled_quantity == 0 {
        assert!(actual.is_none());
        return 0;
    }
    let actual = actual.unwrap();
    assert_eq!(
        (
            actual.retailer_site_id,
            actual.demand_principal_id,
            actual.good_id,
            actual.unit_id,
            actual.quantity
        ),
        (
            d.retailer_site_id,
            d.principal_id,
            d.good_id,
            d.unit_id,
            d.fulfilled_quantity
        )
    );
    let order = OutboundOrderId::LocalFinalDemand(d.order_id);
    let paid = paid_amount(
        rows,
        MoneyTransferPurpose::DeliverySettlement(order),
        MoneyLocation::PurchaseReserve(order),
        AccountId::Site(d.retailer_site_id),
    );
    assert_eq!(
        paid,
        i128::from(actual.quantity)
            .checked_mul(d.unit_price.micro_units())
            .unwrap()
    );
    actual.quantity
}
fn paid_amount(
    rows: &MaterialTickReceipts,
    purpose: MoneyTransferPurpose,
    reserve: MoneyLocation,
    seller: AccountId,
) -> i128 {
    rows.money_transfers
        .iter()
        .filter(|r| r.purpose == purpose)
        .map(|r| {
            assert_eq!(r.debit.location, reserve);
            assert_eq!(r.credit.location, MoneyLocation::Cash(seller));
            assert_eq!(
                r.debit.delta.micro_units().checked_neg(),
                Some(r.credit.delta.micro_units())
            );
            r.credit.delta.micro_units()
        })
        .try_fold(0_i128, i128::checked_add)
        .unwrap()
}
fn exact_paid_handoff(rows: &MaterialTickReceipts) -> u64 {
    rows.household_demand
        .iter()
        .filter(|r| r.principal_id == household() && r.good_id == good(2))
        .map(|d| paid_handoff(rows, d))
        .try_fold(0_u64, u64::checked_add)
        .unwrap()
}

#[derive(Default)]
struct Provision {
    produced: u64,
    supplier_paid: u64,
    donor_paid: u64,
    donor_consumed: u64,
}

fn produced_food(rows: &MaterialTickReceipts, state: &MaterialCircuitState) -> u64 {
    rows.production
        .iter()
        .filter(|r| r.site_id == site(2))
        .map(|r| {
            let recipe = state
                .process_outputs
                .iter()
                .find(|o| o.process_id == r.process_id && o.site_id == r.site_id)
                .unwrap();
            assert_eq!(
                (recipe.good_id, recipe.unit_id),
                (good(2), UnitId::from_bytes([1; 32]))
            );
            r.produced_batches
                .checked_mul(recipe.quantity_per_batch)
                .unwrap()
        })
        .try_fold(0_u64, u64::checked_add)
        .unwrap()
}
fn paid_supply(rows: &MaterialTickReceipts, state: &MaterialCircuitState) -> u64 {
    rows.deliveries
        .iter()
        .map(|delivered| {
            let order = state
                .orders
                .iter()
                .find(|r| r.order_id == delivered.order_id)
                .unwrap();
            if order.supplier_site_id != site(2) || order.buyer_site_id != site(3) {
                return 0;
            }
            assert_eq!(
                (order.good_id, order.unit_id),
                (good(2), UnitId::from_bytes([1; 32]))
            );
            assert!(rows
                .arrivals
                .iter()
                .any(|r| r.order_id == order.order_id && r.quantity == delivered.quantity));
            assert!(rows
                .realizations
                .iter()
                .any(|r| r.order_id == order.order_id && r.quantity == delivered.quantity));
            let id = OutboundOrderId::Delivery(order.order_id);
            let purchase = match &state.accounting {
                CircuitAccounting::Monetary(e) => e.book.purchase(id).unwrap(),
                CircuitAccounting::PhysicalControl => unreachable!(),
            };
            let paid = paid_amount(
                rows,
                MoneyTransferPurpose::DeliverySettlement(id),
                MoneyLocation::PurchaseReserve(id),
                AccountId::Site(site(2)),
            );
            assert_eq!(
                paid,
                i128::from(delivered.quantity)
                    .checked_mul(purchase.unit_price.micro_units())
                    .unwrap()
            );
            delivered.quantity
        })
        .try_fold(0_u64, u64::checked_add)
        .unwrap()
}
fn read_provision(
    rows: &MaterialTickReceipts,
    state: &MaterialCircuitState,
    proof: &mut Provision,
) {
    assert!(
        rows.aid.is_empty(),
        "no aid input during the market preparation closes"
    );
    proof.produced = proof
        .produced
        .checked_add(produced_food(rows, state))
        .unwrap();
    proof.supplier_paid = proof
        .supplier_paid
        .checked_add(paid_supply(rows, state))
        .unwrap();
    proof.donor_paid = proof
        .donor_paid
        .checked_add(exact_paid_handoff(rows))
        .unwrap();
    let used = rows
        .household_consumption
        .iter()
        .filter(|r| r.principal_id == household() && r.good_id == good(2))
        .map(|r| r.consumed_quantity)
        .try_fold(0_u64, u64::checked_add)
        .unwrap();
    proof.donor_consumed = proof.donor_consumed.checked_add(used).unwrap();
}
fn market_preparation(session: &mut Session, sink: &mut CollectingSink, cut: MarketProvisionCut) {
    let mut proof = Provision::default();
    for _ in 0..2 {
        let candidate = prepare(session, None);
        let rows = decode_material_receipts(candidate.material().receipt_bytes()).unwrap();
        read_provision(&rows, session.material().state(), &mut proof);
        commit(session, sink, candidate);
    }
    if matches!(cut, MarketProvisionCut::None) {
        assert!(proof.produced >= proof.supplier_paid && proof.supplier_paid >= proof.donor_paid);
        let retained = proof.donor_paid.checked_sub(proof.donor_consumed).unwrap();
        assert!(retained >= 1 && proof.donor_consumed > 0);
        let CircuitAccounting::Monetary(e) = &session.material().state().accounting else {
            unreachable!()
        };
        let pantry = e
            .recurring
            .as_ref()
            .unwrap()
            .household_stocks
            .iter()
            .find(|r| r.principal_id == household() && r.good_id == good(2))
            .unwrap();
        assert_eq!(pantry.quantity, retained);
    } else {
        assert_eq!(proof.donor_paid, 0, "{cut:?}");
    }
}
fn actual_gift(rows: &MaterialTickReceipts, positive: bool) {
    let granted: Vec<_> = rows
        .aid
        .iter()
        .filter(|r| r.outcome == AidOutcome::Granted && r.quantity > 0)
        .collect();
    if !positive {
        assert!(granted.is_empty());
        return;
    }
    assert_eq!(granted.len(), 1);
    let gift = granted[0];
    assert_eq!(
        (
            gift.donor,
            gift.recipient,
            gift.good_id,
            gift.unit_id,
            gift.quantity
        ),
        (
            household(),
            recipient(),
            good(2),
            UnitId::from_bytes([1; 32]),
            1
        )
    );
    assert_eq!((gift.cash_amount, gift.contribution_hours), (money(3), 2));
    assert_eq!(gift.payer, AccountId::Household(household()));
    assert_eq!((gift.mandate_id, gift.period), ([91; 32], 3));
    assert_eq!(gift.commitment_id, aid_commitment_id([91; 32], 3));
    assert_eq!(
        paid_amount(
            rows,
            MoneyTransferPurpose::AidGrant(gift.commitment_id),
            MoneyLocation::AidReserve(gift.commitment_id),
            AccountId::Household(recipient())
        ),
        3
    );
    let consumed = rows
        .household_consumption
        .iter()
        .find(|r| r.principal_id == recipient())
        .unwrap();
    assert_eq!(
        (
            consumed.good_id,
            consumed.unit_id,
            consumed.consumed_quantity
        ),
        (gift.good_id, gift.unit_id, 1)
    );
}

fn market_then_aid(cut: MarketProvisionCut) {
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation().unwrap();
    let state = market_aid_opening(cut);
    assert!(state
        .inventory
        .iter()
        .filter(|r| r.good_id == good(2))
        .all(|r| r.quantity == 0));
    assert!(state.orders.is_empty() && state.freight.is_empty());
    let mut config = config();
    config.aid_bindings[0].coordination_hours = 1;
    let mut session = try_session(
        foundation,
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        state,
        config,
    )
    .unwrap();
    let mut sink = CollectingSink::default();
    // Designed three-close witness: one-period market route, then separately authorized local gift.
    market_preparation(&mut session, &mut sink, cut);
    let positive = matches!(cut, MarketProvisionCut::None);
    let accepted = commitment(&session, OrganizerChoice::LocalAid);
    let candidate = prepare(&session, Some(&accepted));
    let rows = decode_material_receipts(candidate.material().receipt_bytes()).unwrap();
    actual_gift(&rows, positive);
    commit(&mut session, &mut sink, candidate);
    let organizer = session.material().organizer_state().unwrap();
    assert_eq!(
        organizer.aid_receipts.last().unwrap().practice.outcome,
        if positive {
            OrganizerOutcome::AidPracticeCompleted
        } else {
            OrganizerOutcome::AidNotProvisioned
        }
    );
    let restored = MaterialWorldRegister::decode(session.material().canonical_bytes()).unwrap();
    assert_eq!(restored, *session.material());
    let CircuitAccounting::Monetary(e) = &session.material().state().accounting else {
        unreachable!()
    };
    assert_eq!(e.book.total_cash_and_reserves().unwrap(), money(100));
}

#[test]
fn produced_paid_food_provisions_real_later_authorized_aid() {
    market_then_aid(MarketProvisionCut::None);
}
#[test]
fn severed_donor_purchase_prevents_new_provision_and_aid() {
    market_then_aid(MarketProvisionCut::Purchase);
}
#[test]
fn severed_market_route_prevents_new_provision_and_aid() {
    market_then_aid(MarketProvisionCut::SupplyRoute);
}
#[test]
fn absent_food_production_prevents_new_provision_and_aid() {
    market_then_aid(MarketProvisionCut::Production);
}

fn process(id: u8) -> ProcessId {
    ProcessId::from_bytes([id; 32])
}
fn corridor(id: u8) -> CorridorId {
    CorridorId::from_bytes([id; 32])
}

/// Designed finite control inputs; all market and aid outcomes remain engine-owned.
#[derive(Clone, Copy, Debug)]
enum MarketProvisionCut {
    None,
    Purchase,
    SupplyRoute,
    Production,
}

fn market_aid_opening(cut: MarketProvisionCut) -> MaterialCircuitState {
    let mut state = aid_opening(false);
    state
        .inventory
        .iter_mut()
        .filter(|r| r.good_id == good(2))
        .for_each(|r| r.quantity = 0);
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        unreachable!()
    };
    let rows = e.recurring.as_mut().unwrap();
    rows.household_stocks
        .iter_mut()
        .for_each(|r| r.quantity = 0);
    rows.household_purchases
        .iter_mut()
        .find(|r| r.principal_id == household())
        .unwrap()
        .enabled = !matches!(cut, MarketProvisionCut::Purchase);
    rows.household_purchases
        .iter_mut()
        .find(|r| r.principal_id == household())
        .unwrap()
        .target_closing_stock = 2;
    rows.household_needs
        .iter_mut()
        .find(|r| r.principal_id == household())
        .unwrap()
        .basis = HouseholdNeedBasis::Households;
    let mut stocks = e.costs.snapshot().stocks;
    stocks
        .iter_mut()
        .filter(|r| r.good_id == good(2))
        .for_each(|r| r.amount = money(0));
    // Finite Designed opening funding, never a mid-run subsidy (total100 micros).
    e.book = MonetaryBook::open(
        [
            (AccountId::Site(site(1)), 4),
            (AccountId::Site(site(2)), 32),
            (AccountId::Site(site(3)), 32),
            (AccountId::Household(household()), 32),
            (AccountId::Household(recipient()), 0),
        ]
        .into_iter()
        .map(|(id, amount)| CashAccount {
            id,
            cash: money(amount),
        })
        .collect(),
    )
    .unwrap();
    e.costs = HistoricalCostBook::open(&e.book, stocks, vec![], vec![], vec![]).unwrap();
    e.aid.mandates[0].maximum_quantity = 1;
    if matches!(cut, MarketProvisionCut::SupplyRoute) {
        state
            .corridor_capacities
            .iter_mut()
            .filter(|r| r.corridor_id == corridor(2))
            .for_each(|r| r.available_grams = 0);
    }
    if matches!(cut, MarketProvisionCut::Production) {
        state
            .capacities
            .iter_mut()
            .filter(|r| r.process_id == process(2))
            .for_each(|r| r.available_batches = 0);
    }
    state
}
