//! The small world with a fund: a second public account beside the treasury. The record is
//! `reports/economy-repair-2026-11-20/small-world.md`, section "The fund".

use super::support::{self, Fund, World, UTILITY};
use babylon_material_circuit::{
    AccountId, CircuitAccounting, MaterialCatalog, MaterialCircuitError, MaterialCircuitState,
    MaterialCircuitTransition, PublicSpendingRule, TaxReceipt,
};

/// A fund that taxes at the given rates, holds no cash and pays nothing.
fn fund(wage_bps: u16, operating_bps: u16) -> Fund {
    Fund {
        wage_bps,
        operating_bps,
        opening_cash: support::dollars(0),
        per_person: None,
        after_layoff: None,
    }
}

/// The taxed world with the treasury's rates replaced and a fund beside it.
fn world(treasury_bps: u16, fund_bps: u16) -> World {
    let mut world = World::taxed();
    let taxes = world
        .taxes
        .as_mut()
        .expect("the taxed world has a treasury");
    taxes.wage_bps = treasury_bps;
    taxes.operating_bps = treasury_bps;
    world.with_fund(fund(fund_bps, fund_bps))
}

fn total(state: &MaterialCircuitState) -> i128 {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        panic!("the small world is monetary")
    };
    e.book
        .total_cash_and_reserves()
        .expect("the book totals")
        .micro_units()
}

/// Close period 1 and check that the book still holds what it opened with.
fn close_first(world: &World) -> (MaterialCatalog, MaterialCircuitTransition) {
    let (catalog, state) = world.build();
    let before = total(&state);
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("period 1 closes");
    assert_eq!(total(&closed.state), before, "money is conserved");
    (catalog, closed)
}

fn rows_of(closed: &MaterialCircuitTransition, payer: AccountId) -> Vec<&TaxReceipt> {
    closed
        .taxes
        .iter()
        .filter(|row| row.payer == payer)
        .collect()
}

/// Whole dollars as exact micro-units, so a sub-dollar difference cannot pass.
fn usd(whole: i128) -> i128 {
    support::dollars(whole).micro_units()
}

/// A payer's wage is taxed at two rates for two recipients: the sum is the one rate's tax.
#[test]
fn one_wage_tax_is_paid_to_two_public_accounts() {
    let (_, closed) = close_first(&world(500, 1_500));
    let w = AccountId::Household(support::worker(UTILITY));
    let wage = rows_of(&closed, w);
    assert_eq!(wage.len(), 2);
    assert!(
        wage[0].public_recipient < wage[1].public_recipient,
        "treasury, then fund"
    );
    let collected: Vec<_> = wage.iter().map(|r| r.collected.micro_units()).collect();
    assert_eq!(collected, [usd(60), usd(180)]);
    let s = AccountId::Site(support::site(UTILITY));
    let operating: Vec<_> = rows_of(&closed, s)
        .iter()
        .map(|r| r.collected.micro_units())
        .collect();
    assert_eq!(operating, [usd(12), usd(36)]);
    let sum: i128 = closed.taxes.iter().map(|r| r.collected.micro_units()).sum();
    assert_eq!(sum, usd(640), "the taxed run's total");
}

/// Rows collect in key order from one running balance: the second is short and nothing is
/// overdrawn.
#[test]
fn a_payer_short_of_cash_pays_its_rows_in_order() {
    let (_, closed) = close_first(&world(1_000, 1_500));
    let w = AccountId::Household(support::worker(UTILITY));
    let wage = rows_of(&closed, w);
    let assessed: Vec<_> = wage.iter().map(|r| r.assessed.micro_units()).collect();
    let collected: Vec<_> = wage.iter().map(|r| r.collected.micro_units()).collect();
    let uncollected: Vec<_> = wage.iter().map(|r| r.uncollected.micro_units()).collect();
    assert_eq!(assessed, [usd(120), usd(180)]);
    assert_eq!(collected, [usd(120), usd(120)]);
    assert_eq!(uncollected, [usd(0), usd(60)]);
    let CircuitAccounting::Monetary(e) = &closed.state.accounting else {
        panic!("the small world is monetary")
    };
    assert_eq!(e.book.cash(w).expect("the account exists").micro_units(), 0);
}

fn version(bytes: &[u8]) -> u16 {
    let at = babylon_material_circuit::MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES.len() + 1;
    u16::from_be_bytes([bytes[at], bytes[at + 1]])
}

#[test]
fn a_split_tax_writes_the_extended_state() {
    let (catalog, plain) = World::taxed().build();
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &plain)
        .expect("the taxed state encodes");
    assert_eq!(
        version(&bytes),
        22,
        "one row for each payer keeps today's version"
    );
    let (catalog, mut split) = world(500, 1_500).build();
    let CircuitAccounting::Monetary(e) = &mut split.accounting else {
        panic!("the small world is monetary")
    };
    let budget = e
        .financial
        .public_budgets
        .iter_mut()
        .find(|b| b.public_account == support::fund_account())
        .expect("the fund has a budget");
    budget.rule = PublicSpendingRule::CappedInOrder;
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &split)
        .expect("the split state encodes");
    assert_eq!(version(&bytes), 25);
    let restored = babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
        .expect("the split state decodes");
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &restored)
            .expect("it encodes again"),
        bytes
    );
}

#[test]
fn a_tax_row_repeated_for_one_recipient_is_refused() {
    let (catalog, mut state) = World::taxed().build();
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!("the small world is monetary")
    };
    let again = e.financial.taxes[0].clone();
    e.financial.taxes.push(again);
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state).err(),
        Some(MaterialCircuitError::DuplicateRow)
    );
}
