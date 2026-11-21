//! The small world with a fund: a second public account beside the treasury. The record is
//! `reports/economy-repair-2026-11-20/small-world.md`, section "The fund".

use super::support::{self, Fund, Push, Snapshot, World, LAID_OFF, NO_EARNER, UTILITY};
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

/// What the record names of one run of the fund's world: the first period of a layoff and of a cut,
/// the first period each site's output is 0, the first layoff cohort that is not taken back (its
/// account, first period, and for each period up to 8 the due in micro-units and the persons
/// covered), and the measures at period 34.
struct Pin {
    first_layoff: Option<u64>,
    first_cut: Option<u64>,
    first_zero: [Option<u64>; 4],
    cohort: Option<Cohort>,
    output: [u64; 4],
    unmet: [u64; 3],
    fund_cash: i128,
}

struct Cohort {
    account: &'static str,
    from: u64,
    rows: &'static [(i128, u64)],
}

const WORKERS: [&str; 4] = ["w_utility", "w_farm", "w_clinic", "w_shop"];

fn assert_pin(rows: &[Snapshot], pin: &Pin) {
    let due_of = |row: &Snapshot, account: &str| row.program_due[&(LAID_OFF.to_owned(), account)];
    let first_layoff = rows
        .iter()
        .find(|row| WORKERS.iter().any(|a| due_of(row, a) > 0))
        .map(|row| row.period);
    assert_eq!(first_layoff, pin.first_layoff, "first layoff");
    let first_cut = rows
        .iter()
        .find(|row| {
            row.program_paid.values().sum::<i128>() < row.program_due.values().sum::<i128>()
        })
        .map(|row| row.period);
    assert_eq!(first_cut, pin.first_cut, "first cut");
    for site in 0..4 {
        let zero = rows.iter().find(|row| row.output[site] == 0);
        assert_eq!(
            zero.map(|row| row.period),
            pin.first_zero[site],
            "site {site}"
        );
    }
    if let Some(cohort) = &pin.cohort {
        for (k, (due, persons)) in cohort.rows.iter().enumerate() {
            let row = &rows[usize::try_from(cohort.from - 1).expect("a small period") + k];
            assert_eq!(
                (due_of(row, cohort.account), row.covered[cohort.account]),
                (*due, *persons),
                "{} at period {}",
                cohort.account,
                row.period
            );
        }
        let first = usize::try_from(cohort.from - 1).expect("a small period");
        let before = first
            .checked_sub(1)
            .expect("a cohort starts after period 1, so a period precedes it");
        assert_eq!(
            due_of(&rows[before], cohort.account),
            0,
            "the cohort is the first of its account's run"
        );
    }
    let last = rows.last().expect("34 periods");
    assert_eq!(last.period, support::PERIODS);
    assert_eq!(last.output, pin.output);
    assert_eq!(last.unmet, pin.unmet);
    assert_eq!(last.cash["fund"], pin.fund_cash);
}

fn fund_cash(state: &MaterialCircuitState) -> i128 {
    economy_ref(state)
        .book
        .cash(AccountId::Public(support::fund_account()))
        .expect("the fund has an account")
        .micro_units()
}

/// The fund's world with each of the five pushes, form (a): taxed, no market policy.
fn pushed(push: Push) -> World {
    World::benefits().pushed(push)
}

/// Form (b): the same fund under the market policy with tiers.
fn pushed_with_tiers(push: Push) -> World {
    World::benefits().with_tiers().pushed(push)
}

/// P1 on the fund, no market policy: runs away as P1 does without one. The owner buys half; the
/// farm, clinic and shop stop (periods 18, 19, 18) and the fund, paid by the taxes of a world
/// that is shrinking, is cut from period 6. Nobody is laid off in play: no site sheds a person,
/// so the half pay is never owed.
#[test]
fn p1_with_a_fund_runs_away_until_the_farm_the_clinic_and_the_shop_stop() {
    let rows = support::run(&pushed(Push::LessDemand));
    assert_pin(
        &rows,
        &Pin {
            first_layoff: None,
            first_cut: Some(6),
            first_zero: [None, Some(18), Some(19), Some(18)],
            cohort: None,
            output: [28, 0, 0, 0],
            unmet: [36, 8, 36],
            fund_cash: 46,
        },
    );
}

/// P2 on the fund: runs away as without it, the clinic stopping at period 14. The fund is cut
/// from period 9, and the first layoff in play comes at period 28, when the shop lets one
/// person go: half pay for six and a half periods, cut to a quarter of its due by the fund's
/// short purse.
#[test]
fn p2_with_a_fund_runs_away_until_the_clinic_stops() {
    let rows = support::run(&pushed(Push::LessSupply));
    assert_pin(
        &rows,
        &Pin {
            first_layoff: Some(28),
            first_cut: Some(9),
            first_zero: [None, None, Some(14), None],
            cohort: Some(Cohort {
                account: "w_shop",
                from: 28,
                rows: &[
                    (50_000_000, 1),
                    (50_000_000, 1),
                    (50_000_000, 1),
                    (50_000_000, 1),
                    (50_000_000, 1),
                    (50_000_000, 1),
                    (25_000_000, 1),
                ],
            }),
            output: [21, 9, 0, 22],
            unmet: [18, 29, 40],
            fund_cash: 121,
        },
    );
}

/// P4 on the fund: runs away; the farm, clinic and shop stop (periods 24, 14, 24). The fund is
/// cut from period 11; one shop worker is laid off at 27, and the layoff is paid, in the two
/// steps, at a few dollars of its $50 because the fund has little cash.
#[test]
fn p4_with_a_fund_runs_away_until_the_farm_the_clinic_and_the_shop_stop() {
    let rows = support::run(&pushed(Push::HigherPay));
    assert_pin(
        &rows,
        &Pin {
            first_layoff: Some(27),
            first_cut: Some(11),
            first_zero: [None, Some(24), Some(14), Some(24)],
            cohort: Some(Cohort {
                account: "w_shop",
                from: 27,
                rows: &[
                    (50_000_000, 1),
                    (50_000_000, 1),
                    (50_000_000, 1),
                    (50_000_000, 1),
                    (50_000_000, 1),
                    (50_000_000, 1),
                    (25_000_000, 1),
                    (0, 0),
                ],
            }),
            output: [25, 0, 0, 0],
            unmet: [40, 15, 40],
            fund_cash: 57,
        },
    );
}

/// P5 on the fund: the fund collects 360 against 480 and its reserve is spent by period 6, when
/// the first cut falls on the only program with a claim (480 due, 360 paid). The world then
/// runs away: the farm, clinic and shop stop (periods 26, 15, 26).
#[test]
fn p5_with_a_fund_runs_away_after_the_fund_runs_short() {
    let rows = support::run(&pushed(Push::LowerFundTaxes));
    assert_pin(
        &rows,
        &Pin {
            first_layoff: Some(20),
            first_cut: Some(6),
            first_zero: [None, Some(26), Some(15), Some(26)],
            cohort: Some(Cohort {
                account: "w_shop",
                from: 28,
                rows: &[
                    (50_000_000, 1),
                    (50_000_000, 1),
                    (50_000_000, 1),
                    (50_000_000, 1),
                    (50_000_000, 1),
                    (50_000_000, 1),
                    (25_000_000, 1),
                ],
            }),
            output: [16, 0, 0, 0],
            unmet: [40, 24, 40],
            fund_cash: 25,
        },
    );
}

/// P3 on the fund: settles at once. The shop holds $700; every period equals the first; no one is
/// laid off and the fund is never cut.
#[test]
fn p3_with_a_fund_settles_at_once_with_the_shop_at_half_its_cash() {
    let world = pushed(Push::LessMoney);
    let rows = support::run(&world);
    let first = support::assert_still_rows(&world, &rows);
    assert_eq!(first.cash["shop"], 700);
    assert_pin(
        &rows,
        &Pin {
            first_layoff: None,
            first_cut: None,
            first_zero: [None, None, None, None],
            cohort: None,
            output: [120, 40, 40, 40],
            unmet: [0, 0, 0],
            fund_cash: 960,
        },
    );
}

/// The fund's world under the market policy with tiers, unpushed, is exactly still. The wage tax
/// is ahead of the comforts and luxuries (rule O8): a worker account's purse at its moments of sale
/// holds the gross wage, and the tax it is about to pay is held back from every want, so each
/// account's room for wants is what its needs and its tax leave, $0. Nothing is bought but needs,
/// the public accounts collect the 640 they assess, the fund pays its 480 from what it collects and
/// holds $960 at every close. (Before this was so, the workers spent their tax on comforts in period
/// 1 and the quiet run cycled in a narrow band: see "Form (b) before".)
#[test]
fn the_fund_with_tiers_is_still_the_wage_tax_is_ahead_of_the_wants() {
    let first = support::assert_still(&World::benefits().with_tiers());
    assert_eq!(first.public_receipts, 640);
    assert_eq!(first.public_payments, 640);
    assert_eq!(first.cash["fund"], 960);
    assert_eq!(first.cash["public"], 160);
    let key = (NO_EARNER.to_owned(), "supported");
    assert_eq!(first.program_due[&key], usd(480));
    assert_eq!(first.program_paid[&key], usd(480));
}

/// Every period of `rows` is the first, and the first closes with the opening cash.
fn assert_returns_to_opening_cash(world: &World, rows: &[Snapshot]) {
    let first = rows[0].clone();
    assert_eq!(first.cash, support::opening_cash(world), "period 1");
    for row in rows {
        let mut same = row.clone();
        same.period = first.period;
        assert_eq!(same, first, "period {} moved", row.period);
    }
}

/// P1 on the fund under tiers: returns to its opening state, as P1 with tiers and no tax does.
/// The owner buys only what its own freed money allows ($120 of comforts and $200 of luxuries in
/// every period), no tax is spent first, no site is laid off and every period equals the first.
#[test]
fn p1_with_a_fund_and_tiers_returns_to_its_opening_state() {
    let world = pushed_with_tiers(Push::LessDemand);
    let rows = support::run(&world);
    assert_returns_to_opening_cash(&world, &rows);
    assert_pin(
        &rows,
        &Pin {
            first_layoff: None,
            first_cut: None,
            first_zero: [None, None, None, None],
            cohort: None,
            output: [120, 40, 40, 40],
            unmet: [0, 0, 0],
            fund_cash: 960,
        },
    );
}

/// P2 on the fund under tiers: cycles in a depressed band, no site stopping. The layoffs in play
/// come in waves from period 11 (the clinic, then the utility), and the fund's first cut falls at
/// period 9.
#[test]
fn p2_with_a_fund_and_tiers_cycles_in_a_depressed_band() {
    let rows = support::run(&pushed_with_tiers(Push::LessSupply));
    assert_pin(
        &rows,
        &Pin {
            first_layoff: Some(11),
            first_cut: Some(9),
            first_zero: [None, None, None, None],
            cohort: Some(Cohort {
                account: "w_clinic",
                from: 11,
                rows: &[
                    (100_000_000, 2),
                    (50_000_000, 1),
                    (50_000_000, 1),
                    (100_000_000, 2),
                    (50_000_000, 1),
                    (50_000_000, 1),
                    (25_000_000, 1),
                    (0, 0),
                ],
            }),
            output: [92, 36, 18, 36],
            unmet: [6, 8, 30],
            fund_cash: 279,
        },
    );
}

/// P3 on the fund under tiers: the quiet run of the same world, exactly still, the shop holding
/// $700 where the quiet run holds $1,400.
#[test]
fn p3_with_a_fund_and_tiers_is_still_with_the_shop_at_half_its_cash() {
    let world = pushed_with_tiers(Push::LessMoney);
    let rows = support::run(&world);
    assert_returns_to_opening_cash(&world, &rows);
    assert_eq!(rows[0].cash["shop"], 700);
    assert_pin(
        &rows,
        &Pin {
            first_layoff: None,
            first_cut: None,
            first_zero: [None, None, None, None],
            cohort: None,
            output: [120, 40, 40, 40],
            unmet: [0, 0, 0],
            fund_cash: 960,
        },
    );
}

/// P4 on the fund under tiers: cycles in a band, no site stopping and nobody laid off in play. The
/// fund's first cut falls at period 4, and the clinic ends at 39 units.
#[test]
fn p4_with_a_fund_and_tiers_cycles_with_no_layoff_in_play() {
    let rows = support::run(&pushed_with_tiers(Push::HigherPay));
    assert_pin(
        &rows,
        &Pin {
            first_layoff: None,
            first_cut: Some(4),
            first_zero: [None, None, None, None],
            cohort: None,
            output: [116, 40, 39, 40],
            unmet: [2, 5, 9],
            fund_cash: 233,
        },
    );
}

/// P5 on the fund under tiers: cycles in a band. Nobody is laid off in play and the fund, cut from
/// period 5, is never empty: it holds $171 at period 34.
#[test]
fn p5_with_a_fund_and_tiers_cycles_with_the_fund_holding_a_reserve() {
    let rows = support::run(&pushed_with_tiers(Push::LowerFundTaxes));
    assert_pin(
        &rows,
        &Pin {
            first_layoff: None,
            first_cut: Some(5),
            first_zero: [None, None, None, None],
            cohort: None,
            output: [112, 40, 31, 40],
            unmet: [4, 5, 15],
            fund_cash: 171,
        },
    );
}

/// Every cut is in proportion. In each period of P5 where the fund is short, with `total` the
/// rank's dues and `budget` the fund's cash as the period opens, each rank-0 receipt pays
/// `floor(due x budget / total)` or that plus one, and the paid amounts add to the budget. Both
/// forms run: the taxed world without a market policy and the one with tiers.
#[test]
fn every_cut_is_in_proportion() {
    for world in [
        pushed(Push::LowerFundTaxes),
        pushed_with_tiers(Push::LowerFundTaxes),
    ] {
        let (_, opening) = world.build();
        let mut budget = fund_cash(&opening);
        let mut cuts = 0;
        support::run_observed(&world, &mut |period, closed| {
            let rows: Vec<_> = closed
                .public_programs
                .iter()
                .filter(|row| row.public_account == support::fund_account() && row.rank == 0)
                .collect();
            let total: i128 = rows.iter().map(|row| row.due.micro_units()).sum();
            let paid: i128 = rows.iter().map(|row| row.paid.micro_units()).sum();
            if total > budget {
                cuts += 1;
                assert_eq!(paid, budget, "period {period}: the budget is paid out");
                for row in rows {
                    let (due, got) = (row.due.micro_units(), row.paid.micro_units());
                    let floor = due * budget / total;
                    assert!(
                        got == floor || got == floor + 1,
                        "period {period}: {due} of {total} from {budget} paid {got}"
                    );
                    assert!(got <= due, "period {period}");
                }
            } else {
                assert_eq!(paid, total, "period {period}: paid in full");
            }
            budget = fund_cash(&closed.state);
        });
        assert!(cuts > 0, "the fund is short in some period");
    }
}
