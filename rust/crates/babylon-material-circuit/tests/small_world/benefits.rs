//! The small world with a fund: a second public account beside the treasury. The record is
//! `reports/economy-repair-2026-11-20/small-world.md`, section "The fund".

use super::support::{self, Fund, Snapshot, World, LAID_OFF, NO_EARNER, UTILITY};
use babylon_material_circuit::{
    AccountId, CircuitAccounting, LayoffRecord, MaterialCatalog, MaterialCircuitError,
    MaterialCircuitState, MaterialCircuitTransition, MonetaryCircuit, PublicProgram,
    PublicProgramKey, PublicProgramTerms, PublicSpendingRule, PublicTransferTreatment,
    StaffingMemberBinding, TaxReceipt,
};

/// The benefits world with the fund's per-person benefit alone: no after-layoff program, which the
/// plain finishes refuse.
fn per_person_fund() -> World {
    let mut world = World::benefits();
    world.fund.as_mut().expect("a fund").after_layoff = None;
    world
}

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

fn economy_mut(state: &mut MaterialCircuitState) -> &mut MonetaryCircuit {
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!("the small world is monetary")
    };
    e
}

/// The fund pays 480 a period to the account that does not work; the world is as still as the taxed
/// one, with the support shared between the treasury and the fund.
#[test]
fn the_fund_pays_each_person_and_the_world_is_still() {
    let world = per_person_fund();
    let first = support::assert_still(&world);
    assert_eq!(first.employed, [12, 4, 4, 4]);
    assert_eq!(first.public_receipts, 640);
    assert_eq!(first.public_payments, 640);
    assert_eq!(first.cash["fund"], 960);
    assert_eq!(first.cash["public"], 160);
    let key = (NO_EARNER.to_owned(), "supported");
    assert_eq!(first.program_due[&key], usd(480));
    assert_eq!(first.program_paid[&key], usd(480));
    assert_eq!(first.covered["supported"], 8);
}

fn set_supported_persons(state: &mut MaterialCircuitState, persons: u64) {
    let cohort = economy_mut(state)
        .recurring
        .as_mut()
        .expect("the world is recurring")
        .households
        .iter_mut()
        .find(|h| h.principal_id == support::supported())
        .expect("the supported account has a cohort");
    cohort.persons = persons;
}

/// A per-person benefit reads the persons of the cohort as the period opens.
#[test]
fn per_person_reads_the_persons_of_the_cohort() {
    let (catalog, mut state) = per_person_fund().build();
    set_supported_persons(&mut state, 6);
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("period 1 closes");
    let [row] = closed.public_programs.as_slice() else {
        panic!("one program and one recipient give one receipt")
    };
    assert_eq!(row.covered_persons, 6);
    assert_eq!(row.due.micro_units(), usd(360));
    assert_eq!(row.paid.micro_units(), usd(360));
}

/// The treasury is paid as today whatever the fund does: a fund with no cash pays nothing, and the
/// treasury's receipt is the one it has without the fund's program and budget.
#[test]
fn the_place_pays_as_today_beside_the_funds_program() {
    let mut world = per_person_fund();
    world.fund.as_mut().expect("a fund").opening_cash = support::dollars(0);
    let (catalog, closed) = close_first(&world);
    let [row] = closed.public_programs.as_slice() else {
        panic!("one program and one recipient give one receipt")
    };
    assert_eq!(row.due.micro_units(), usd(480));
    assert_eq!(row.paid.micro_units(), 0);
    assert_eq!(row.unfunded.micro_units(), usd(480));
    let amounts: Vec<_> = closed
        .public_budgets
        .iter()
        .map(|r| {
            (
                r.requested.micro_units(),
                r.paid.micro_units(),
                r.unfunded.micro_units(),
            )
        })
        .collect();
    assert_eq!(amounts, [(usd(160), usd(160), 0)]);
    let (_, mut state) = world.build();
    let fund = support::fund_account();
    let e = economy_mut(&mut state);
    e.financial.programs.clear();
    e.financial
        .public_budgets
        .retain(|b| b.public_account != fund);
    let control = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the control closes");
    assert_eq!(closed.public_budgets, control.public_budgets);
}

/// A standing row and a program of one rank draw on one budget and are cut together.
#[test]
fn a_program_and_a_standing_row_of_one_rank_are_cut_together() {
    let mut world = per_person_fund();
    world.fund.as_mut().expect("a fund").opening_cash = support::dollars(480);
    let (catalog, mut state) = world.build();
    economy_mut(&mut state).financial.public_allocations.push(
        babylon_material_circuit::PublicAllocation {
            public_account: support::fund_account(),
            recipient: AccountId::Household(support::supported()),
            treatment: PublicTransferTreatment::HouseholdIncomeSupport,
            priority: 0,
            amount_per_period: support::dollars(480),
        },
    );
    let before = total(&state);
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("period 1 closes");
    assert_eq!(total(&closed.state), before, "money is conserved");
    let fund_row = closed
        .public_budgets
        .iter()
        .find(|r| r.public_account == support::fund_account())
        .expect("the standing row has a receipt");
    assert_eq!(fund_row.paid.micro_units(), usd(240));
    assert_eq!(closed.public_programs[0].paid.micro_units(), usd(240));
}

fn refused(mutate: impl FnOnce(&mut MaterialCircuitState)) {
    let (catalog, mut state) = per_person_fund().build();
    mutate(&mut state);
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state).err(),
        Some(MaterialCircuitError::PublicProgramInvariant)
    );
}

fn first_program(state: &mut MaterialCircuitState) -> &mut PublicProgram {
    &mut economy_mut(state).financial.programs[0]
}

#[test]
fn bad_programs_are_refused() {
    for text in [
        "No-earner",
        "",
        "1earner",
        "a_very_long_key_of_more_than_32_bytes",
    ] {
        assert_eq!(
            PublicProgramKey::new(text),
            Err(MaterialCircuitError::PublicProgramInvariant),
            "{text:?}"
        );
    }
    refused(|state| {
        let again = first_program(state).clone();
        economy_mut(state).financial.programs.push(again);
    });
    refused(|state| first_program(state).payer = support::treasury());
    refused(|state| {
        economy_mut(state)
            .recurring
            .as_mut()
            .expect("recurring")
            .households
            .retain(|h| h.principal_id != support::supported());
    });
    refused(|state| {
        first_program(state).terms = PublicProgramTerms::PerPerson {
            amount_per_person: support::dollars(0),
        };
    });
    refused(|state| first_program(state).recipients = vec![support::supported(); 2]);
}

fn two_programs() -> (MaterialCatalog, MaterialCircuitState) {
    let (catalog, mut state) = per_person_fund().build();
    let programs = &mut economy_mut(&mut state).financial.programs;
    let mut first = programs[0].clone();
    first.key = PublicProgramKey::new("aa_prog").expect("a key");
    let mut second = first.clone();
    second.key = PublicProgramKey::new("bb_prog").expect("a key");
    *programs = vec![first, second];
    (catalog, state)
}

#[test]
fn a_program_writes_the_extended_state_and_round_trips() {
    let (catalog, state) = per_person_fund().build();
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the state encodes");
    assert_eq!(version(&bytes), 25);
    let restored = babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
        .expect("the state decodes");
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &restored)
            .expect("it encodes again"),
        bytes
    );
    // Two programs written out of order: decode refuses them.
    let (catalog, state) = two_programs();
    let mut bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("two programs encode");
    let find = |bytes: &[u8], key: &[u8]| {
        let mut needle = vec![u8::try_from(key.len()).expect("short")];
        needle.extend_from_slice(key);
        bytes
            .windows(needle.len())
            .position(|w| w == needle)
            .expect("the key is in the bytes")
    };
    let (a, b) = (find(&bytes, b"aa_prog"), find(&bytes, b"bb_prog"));
    let row = b - a;
    let first = bytes[a..b].to_vec();
    let second = bytes[b..b + row].to_vec();
    bytes[a..b].copy_from_slice(&second);
    bytes[b..b + row].copy_from_slice(&first);
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes).err(),
        Some(MaterialCircuitError::WireNoncanonical)
    );
}

/// The benefits world with the fund holding $10,000 unless a test says otherwise.
fn rich_fund() -> World {
    let mut world = World::benefits();
    world.fund.as_mut().expect("a fund").opening_cash = support::dollars(10_000);
    world
}

fn laid_off(row: &Snapshot) -> (i128, i128, u64) {
    let key = (LAID_OFF.to_owned(), "w_utility");
    (
        row.program_due[&key],
        row.program_paid[&key],
        row.covered["w_utility"],
    )
}

#[test]
fn the_fund_with_both_programs_is_still() {
    let world = World::benefits();
    let mut records = 0;
    let rows = support::run_observed(&world, &mut |_, closed| {
        records += economy_ref(&closed.state).financial.layoffs.len();
    });
    assert_eq!(records, 0, "nobody was laid off");
    let first = support::assert_still_rows(&world, &rows);
    for account in ["w_utility", "w_farm", "w_clinic", "w_shop"] {
        let key = (LAID_OFF.to_owned(), account);
        assert_eq!(first.program_due[&key], 0, "{account}");
        assert_eq!(first.program_paid[&key], 0, "{account}");
    }
    let key = (NO_EARNER.to_owned(), "supported");
    assert_eq!(first.program_due[&key], usd(480));
}

fn economy_ref(state: &MaterialCircuitState) -> &MonetaryCircuit {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        panic!("the small world is monetary")
    };
    e
}

/// Utility sheds two people after period 1; the rest stay as they are.
fn utility_at(persons: u64) -> [u64; 4] {
    [persons, 4, 4, 4]
}

/// Two people laid off at $10 an hour for 10 hours, at half pay: $50 each in a period, for six
/// periods, and $25 in the seventh.
#[test]
fn a_layoff_is_paid_half_pay_for_six_and_a_half_periods() {
    let rows = support::run_driven(&rich_fund(), |_| utility_at(10));
    assert_eq!(laid_off(&rows[0]), (0, 0, 0));
    let expected = [100, 100, 100, 100, 100, 100, 50, 0];
    let covered = [2, 2, 2, 2, 2, 2, 2, 0];
    for (k, (due, persons)) in expected.into_iter().zip(covered).enumerate() {
        let row = &rows[k + 1];
        assert_eq!(row.period, k as u64 + 2);
        assert_eq!(
            laid_off(row),
            (usd(due), usd(due), persons),
            "period {}",
            row.period
        );
    }
}

/// Three more are laid off in the second period and four go back in the third: the newest cohort
/// goes first, then one of the oldest.
#[test]
fn the_last_laid_off_go_back_first() {
    let rows = support::run_driven(&rich_fund(), |p| match p {
        1 => utility_at(10),
        2 => utility_at(7),
        _ => utility_at(11),
    });
    let due: Vec<_> = rows[1..9].iter().map(|r| laid_off(r).0).collect();
    let expected: Vec<_> = [100, 250, 50, 50, 50, 50, 25, 0].map(usd).to_vec();
    assert_eq!(due, expected);
}

/// The state after period 1 of a hand-staffed run, with two laid off.
fn after_a_layoff() -> (MaterialCatalog, MaterialCircuitState) {
    let world = rich_fund();
    let (catalog, _) = world.build();
    let mut kept = None;
    support::run_staffed(&world, Some(&|_| utility_at(10)), &mut |period, closed| {
        if period == 1 {
            kept = Some(closed.state.clone());
        }
    });
    (catalog, kept.expect("period 1 finished"))
}

#[test]
fn finishing_without_the_member_receipts_is_refused() {
    let world = rich_fund();
    let (catalog, state) = world.build();
    let closed =
        babylon_material_circuit::close_material_period(&catalog, &state).expect("period 1 closes");
    assert_eq!(
        closed.finish_with_workforce(&catalog, vec![], vec![]).err(),
        Some(MaterialCircuitError::PublicProgramInvariant)
    );
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state).err(),
        Some(MaterialCircuitError::PublicProgramInvariant)
    );
    // A member that holds a record needs its receipt.
    let (catalog, state) = after_a_layoff();
    let closed =
        babylon_material_circuit::close_material_period(&catalog, &state).expect("period 2 closes");
    let mut staffed = support::staff_by_hand(&world, 2, utility_at(10), utility_at(10));
    staffed
        .receipts
        .retain(|r| r.member.member_id() != support::member(UTILITY));
    assert_eq!(
        closed
            .finish_with_staffing(&catalog, staffed.labor, vec![], &staffed.receipts)
            .err(),
        Some(MaterialCircuitError::PublicProgramInvariant)
    );
}

#[test]
fn a_member_receipt_for_another_household_is_refused() {
    let world = rich_fund();
    let (catalog, state) = world.build();
    let closed =
        babylon_material_circuit::close_material_period(&catalog, &state).expect("period 1 closes");
    let mut staffed = support::staff_by_hand(&world, 1, world.workers, world.workers);
    let wrong = &mut staffed.receipts[UTILITY];
    wrong.member = StaffingMemberBinding::from_living_force(
        wrong.member.member_id(),
        support::supported(),
        wrong.member.residence(),
        wrong.member.labor_force(),
    );
    assert_eq!(
        closed
            .finish_with_staffing(&catalog, staffed.labor, vec![], &staffed.receipts)
            .err(),
        Some(MaterialCircuitError::PublicProgramInvariant)
    );
}

#[test]
fn a_dropped_recipient_leaves_a_readable_state() {
    let (catalog, mut state) = after_a_layoff();
    assert_eq!(economy_ref(&state).financial.layoffs.len(), 1);
    let program = economy_mut(&mut state)
        .financial
        .programs
        .iter_mut()
        .find(|p| p.key.as_str() == LAID_OFF)
        .expect("the layoff program");
    program
        .recipients
        .retain(|r| *r != support::worker(UTILITY));
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the state encodes");
    let restored = babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
        .expect("the state decodes");
    assert_eq!(restored, state);
    let closed =
        babylon_material_circuit::close_material_period(&catalog, &state).expect("period 2 closes");
    let world = rich_fund();
    let staffed = support::staff_by_hand(&world, 2, utility_at(10), utility_at(10));
    let members = staffed.member_labor();
    let next = closed
        .finish_with_staffing(&catalog, staffed.labor, members, &staffed.receipts)
        .expect("period 2 finishes");
    assert!(
        next.public_programs
            .iter()
            .all(|r| r.recipient != support::worker(UTILITY)),
        "it is owed nothing"
    );
    assert_eq!(economy_ref(&next.state).financial.layoffs.len(), 0);
}

#[test]
fn a_household_in_two_after_layoff_programs_is_refused() {
    let (catalog, mut state) = World::benefits().build();
    let programs = &mut economy_mut(&mut state).financial.programs;
    let mut again = programs
        .iter()
        .find(|p| p.key.as_str() == LAID_OFF)
        .expect("the layoff program")
        .clone();
    again.key = PublicProgramKey::new("laid_off_again").expect("a key");
    programs.push(again);
    assert_eq!(
        babylon_material_circuit::close_material_period(&catalog, &state).err(),
        Some(MaterialCircuitError::PublicProgramInvariant)
    );
}

#[test]
fn without_an_after_layoff_program_both_finishes_agree() {
    let world = World::taxed();
    let (catalog, state) = world.build();
    let staffed = support::staff_by_hand(&world, 1, world.workers, world.workers);
    let by_workforce = babylon_material_circuit::close_material_period(&catalog, &state)
        .expect("period 1 closes")
        .finish_with_workforce(&catalog, staffed.labor.clone(), staffed.member_labor())
        .expect("it finishes");
    let by_staffing = babylon_material_circuit::close_material_period(&catalog, &state)
        .expect("period 1 closes")
        .finish_with_staffing(
            &catalog,
            staffed.labor.clone(),
            staffed.member_labor(),
            &staffed.receipts,
        )
        .expect("it finishes");
    assert_eq!(by_staffing, by_workforce);
}

#[test]
fn a_record_of_layoffs_round_trips_and_a_bad_one_is_refused() {
    let (catalog, state) = after_a_layoff();
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the state encodes");
    assert_eq!(version(&bytes), 25);
    let restored = babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
        .expect("the state decodes");
    assert_eq!(restored, state);
    let record = economy_ref(&state).financial.layoffs[0].clone();
    assert_eq!(
        (
            record.member_id,
            record.hours_per_person,
            record.cohorts.as_slice()
        ),
        (support::member(UTILITY), 10, &[2][..])
    );
    let bad: [fn(&mut LayoffRecord); 4] = [
        |r| r.cohorts = vec![],
        |r| r.cohorts = vec![1, 0],
        |r| r.cohorts = vec![1; 14],
        |r| r.hours_per_person = 0,
    ];
    for mutate in bad {
        let mut state = state.clone();
        mutate(&mut economy_mut(&mut state).financial.layoffs[0]);
        assert_eq!(
            babylon_material_circuit::close_material_period(&catalog, &state).err(),
            Some(MaterialCircuitError::PublicProgramInvariant)
        );
    }
}
