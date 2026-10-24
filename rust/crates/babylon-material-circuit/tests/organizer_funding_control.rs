//! PER-345's retained four-period accounting capsule through the shared close.
//!
//! Source capsule: reports/test-results/per345-funding/2026-10-04/
//! four-period-paper-control on the retained PER-343 worktree. This bounded
//! Designed component control proves accounting and canonical re-execution;
//! Retained control.json SHA-256:
//! 5eb13e470f1b7ba3aa90a03b97608267fb9021c47c98fb0b446fffc956a4dcca.
//! Organizer command admission and atomic campaign publication have separate
//! `MaterialReplaySession` controls. It is not national play qualification.
use crate::control::cash;
use crate::control::money;
use crate::control::public;
use crate::control::remaining;
use crate::control::stock;
use crate::control::COLLECTION;
use crate::control::EMPLOYER;
use crate::control::FOOD;
use crate::control::MATERIALS;
use crate::control::PAPER_CASH;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::AidOutcome;
use babylon_material_circuit::AidResolveInput;
use babylon_material_circuit::CashTransferPurpose;
use babylon_material_circuit::CollectionOutcome;
use babylon_material_circuit::CollectionReceipt;
use babylon_material_circuit::CollectionResolveInput;
use babylon_material_circuit::HouseholdCohort;
use babylon_material_circuit::IncomeReceipt;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MaterialCircuitTransition;
use babylon_material_circuit::MoneyLocation;
use babylon_material_circuit::MoneyTransferPurpose;
#[path = "support/organizer_funding_control.rs"]
mod control;

#[derive(Clone, Copy)]
struct PeriodExpectation {
    period: u64,
    expected_cash: i128,
    expected_organization: i128,
    expected_food: u64,
    donor_hours: u64,
    recipient_hours: u64,
    purchase_payment: i128,
}

#[derive(Clone, Copy, Default)]
struct ControlTotals {
    donor_net: i128,
    organization_gifts: i128,
    recipient_gifts: i128,
    selected_food_consumed: u64,
    selected_materials_consumed: u64,
    supplier_food_consumed: u64,
    total_tax: i128,
}

#[test]
fn four_period_collection_aid_savings_and_protected_service_control() {
    let mut state = control::opening();
    let original_cohorts = assert_opening_accounting(&state);
    let mut totals = ControlTotals::default();
    for (
        period,
        expected_cash,
        expected_organization,
        expected_food,
        donor_hours,
        recipient_hours,
        purchase_payment,
    ) in [
        (1, 26_983_600_000, 400_000, 8, 766, 432, 13_928_000_000),
        (2, 26_111_600_000, 0, 4, 758, 510, 13_928_000_000),
        (3, 11_063_200_000, 400_000, 8, 1406, 432, 15_048_000_000),
        (4, 135_200_000, 400_000, 8, 1408, 432, 10_928_000_000),
    ] {
        state = control::controlled_opening(state);
        assert_eq!(state.period, period);
        let gifts = if period == 2 {
            vec![control::aid(period)]
        } else {
            vec![]
        };
        let collections = if period == 2 {
            vec![]
        } else {
            vec![control::collection(period)]
        };
        let completed = close_and_reexecute(&state, &gifts, &collections);
        let expected = PeriodExpectation {
            period,
            expected_cash,
            expected_organization,
            expected_food,
            donor_hours,
            recipient_hours,
            purchase_payment,
        };
        assert_selected_balances_and_hours(&completed, &expected, &original_cohorts);
        assert_conserved_transfers_and_purchases(&completed, expected.purchase_payment);
        let expected_wages = assert_funded_attendance(&completed, period);
        assert_settled_wage_claims(&completed, period, expected_wages);
        totals.total_tax += assert_taxes_and_closed_reserves(&completed, period, expected_wages);
        reconcile_income(&completed, &mut totals);
        assert_household_reproduction_and_finite_support(&completed, period, &mut totals);
        if period == 2 {
            assert_aid_grant_and_gift_accounts(&completed);
        } else {
            assert_collection_identity_and_outcome(&completed, &collections, period);
        }
        assert_canonical_closed_state(&completed);
        state = completed.state;
    }
    assert_four_period_reconciliation(&state, &totals);
}

fn assert_opening_accounting(state: &MaterialCircuitState) -> Vec<HouseholdCohort> {
    assert_eq!(
        control::economy(state)
            .book
            .total_cash_and_reserves()
            .unwrap(),
        money(PAPER_CASH)
    );
    let cohorts = &control::economy(state)
        .recurring
        .as_ref()
        .unwrap()
        .households;
    assert_eq!(
        cohorts
            .iter()
            .filter(|r| r.principal_id != control::suppliers())
            .map(|r| r.persons)
            .sum::<u64>(),
        12
    );
    assert_eq!(cohorts.iter().map(|r| r.persons).sum::<u64>(), 17);
    assert_eq!(stock(state, control::donor(), FOOD) + 36, 44);
    assert_eq!(stock(state, control::donor(), MATERIALS) + 16, 20);
    assert_eq!(stock(state, control::suppliers(), FOOD), 20);
    cohorts.clone()
}

fn close_and_reexecute(
    state: &MaterialCircuitState,
    gifts: &[AidResolveInput],
    collections: &[CollectionResolveInput],
) -> MaterialCircuitTransition {
    let period = state.period;
    let before = babylon_material_circuit::encode_material_circuit_state(state).unwrap();
    let mut completed = control::close(state, gifts, collections).unwrap();

    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(state).unwrap(),
        before
    );
    let decoded = babylon_material_circuit::decode_material_circuit_state(&before).unwrap();
    let mut repeated = control::close(&decoded, gifts, collections).unwrap();
    if period == 2 {
        control::coordinate(&mut completed);
        control::coordinate(&mut repeated);
    }
    assert_eq!(repeated, completed);

    completed
}

fn assert_selected_balances_and_hours(
    completed: &MaterialCircuitTransition,
    expected: &PeriodExpectation,
    original_cohorts: &[HouseholdCohort],
) {
    let PeriodExpectation {
        period,
        expected_cash,
        expected_organization,
        expected_food,
        donor_hours,
        recipient_hours,
        ..
    } = *expected;
    assert_eq!(
        cash(&completed.state, AccountId::Household(control::donor())),
        expected_cash,
        "donor P{period}"
    );
    assert_eq!(
        cash(&completed.state, control::organization()),
        expected_organization,
        "organization P{period}"
    );
    assert_eq!(
        stock(&completed.state, control::donor(), FOOD),
        expected_food
    );
    assert_eq!(stock(&completed.state, control::donor(), MATERIALS), 4);
    assert_eq!(
        remaining(&completed.state, control::donor()),
        donor_hours,
        "donor hours P{period}"
    );
    assert_eq!(
        remaining(&completed.state, control::recipient()),
        recipient_hours,
        "recipient hours P{period}"
    );
    assert_eq!(
        control::economy(&completed.state)
            .recurring
            .as_ref()
            .unwrap()
            .households
            .as_slice(),
        original_cohorts
    );
}

fn assert_conserved_transfers_and_purchases(
    completed: &MaterialCircuitTransition,
    purchase_payment: i128,
) {
    assert_eq!(
        control::economy(&completed.state)
            .book
            .total_cash_and_reserves()
            .unwrap(),
        money(PAPER_CASH)
    );
    for transfer in &completed.money_transfers {
        assert_eq!(
            transfer
                .debit
                .delta
                .checked_add(transfer.credit.delta)
                .unwrap(),
            money(0)
        );
        assert!(transfer.debit.delta.micro_units() < 0);
        assert!(transfer.credit.delta.micro_units() > 0);
    }
    let spending = completed
        .money_transfers
        .iter()
        .filter(|r| {
            matches!(r.purpose, MoneyTransferPurpose::DeliverySettlement(_))
                && matches!(r.credit.location, MoneyLocation::Cash(AccountId::Site(_)))
        })
        .map(|r| r.credit.delta.micro_units())
        .sum::<i128>();
    assert_eq!(spending, purchase_payment);
}

fn assert_funded_attendance(completed: &MaterialCircuitTransition, period: u64) -> i128 {
    let labor = completed
        .member_labor_use
        .iter()
        .find(|r| r.site_id == control::site(EMPLOYER))
        .unwrap();
    let expected_wages = if period <= 2 { 15_360_000_000 } else { 0 };
    let expected_attendance = if period <= 2 { 640 } else { 0 };
    assert_eq!(labor.attended_hours, expected_attendance);
    assert_eq!(labor.accrued_wages.micro_units(), expected_wages);
    assert_eq!(labor.idle_wages.micro_units(), expected_wages);
    assert_eq!(
        cash(&completed.state, AccountId::Site(control::site(EMPLOYER))),
        if period == 1 { 15_360_000_000 } else { 0 }
    );
    assert!(!completed
        .production
        .iter()
        .any(|r| r.site_id == control::site(EMPLOYER) && r.produced_batches > 0));
    assert_eq!(
        labor.production_hours
            + labor.handling_hours
            + labor.maintenance_hours
            + labor.installation_hours,
        0
    );

    expected_wages
}

fn assert_settled_wage_claims(
    completed: &MaterialCircuitTransition,
    period: u64,
    expected_wages: i128,
) {
    let expected_attendance = if period <= 2 { 640 } else { 0 };
    let wages = completed
        .wage_accruals
        .iter()
        .filter(|r| r.payee == AccountId::Household(control::donor()))
        .collect::<Vec<_>>();
    assert_eq!(
        wages.iter().map(|r| r.obligated_hours).sum::<u64>(),
        expected_attendance
    );
    assert_eq!(
        wages.iter().map(|r| r.amount.micro_units()).sum::<i128>(),
        expected_wages
    );
    assert_eq!(
        completed
            .money_transfers
            .iter()
            .filter(|r| matches!(r.purpose, MoneyTransferPurpose::WagePayment(_)))
            .map(|r| r.credit.delta.micro_units())
            .sum::<i128>(),
        expected_wages
    );
}

fn assert_taxes_and_closed_reserves(
    completed: &MaterialCircuitTransition,
    period: u64,
    expected_wages: i128,
) -> i128 {
    let tax = completed
        .taxes
        .iter()
        .find(|r| r.payer == AccountId::Household(control::donor()))
        .unwrap();
    assert_eq!(tax.taxable_amount.micro_units(), expected_wages);
    assert_eq!(
        tax.assessed.micro_units(),
        if period <= 2 { 2_304_000_000 } else { 0 }
    );
    assert_eq!(tax.collected, tax.assessed);
    assert_eq!(tax.uncollected, money(0));
    let books = control::economy(&completed.state).book.snapshot();
    assert!(books
        .purchases
        .iter()
        .all(|r| r.reserved_amount().unwrap() == money(0)));
    assert!(books
        .shifts
        .iter()
        .all(|r| r.reserved_amount().unwrap() == money(0)
            && r.outstanding_wages().unwrap() == money(0)));
    assert!(books
        .aid
        .iter()
        .all(|r| r.reserved_amount().unwrap() == money(0)));

    tax.collected.micro_units()
}

fn reconcile_income(completed: &MaterialCircuitTransition, totals: &mut ControlTotals) {
    let donor_income = completed
        .income
        .iter()
        .find(|r| r.account == AccountId::Household(control::donor()))
        .unwrap();
    let organization_income = completed
        .income
        .iter()
        .find(|r| r.account == control::organization())
        .unwrap();
    let recipient_income = completed
        .income
        .iter()
        .find(|r| r.account == AccountId::Household(control::recipient()))
        .unwrap();
    totals.donor_net += donor_income.net_income.micro_units();
    totals.organization_gifts += organization_income.statement.gift_income.micro_units();
    totals.recipient_gifts += recipient_income.statement.gift_income.micro_units();
    assert_eq!(donor_income.statement.public_transfer_income, money(0));
    assert_eq!(donor_income.statement.distribution_income, money(0));
}

fn assert_household_reproduction_and_finite_support(
    completed: &MaterialCircuitTransition,
    period: u64,
    totals: &mut ControlTotals,
) {
    let recipient_consumption = completed
        .household_consumption
        .iter()
        .find(|r| r.principal_id == control::recipient())
        .unwrap();
    assert_eq!(
        recipient_consumption.consumed_quantity,
        if period == 2 { 4 } else { 0 }
    );
    totals.selected_food_consumed += completed
        .household_consumption
        .iter()
        .filter(|r| r.principal_id != control::suppliers() && r.good_id == control::good(FOOD))
        .map(|r| r.consumed_quantity)
        .sum::<u64>();
    totals.selected_materials_consumed += completed
        .household_consumption
        .iter()
        .filter(|r| r.good_id == control::good(MATERIALS))
        .map(|r| r.consumed_quantity)
        .sum::<u64>();
    let supplementary = completed
        .household_consumption
        .iter()
        .find(|r| r.principal_id == control::suppliers())
        .unwrap();
    assert_eq!(
        (
            supplementary.consumed_quantity,
            supplementary.unmet_quantity
        ),
        (5, 0)
    );
    totals.supplier_food_consumed += supplementary.consumed_quantity;
    for receipt in &completed.service_outputs {
        assert!(
            receipt.produced_quantity
                <= if receipt.good_id == control::good(5) {
                    4
                } else {
                    8
                }
        );
        assert_eq!(receipt.direct_cost, money(0)); // Explicit WorkingOwner support.
    }
}

fn income(completed: &MaterialCircuitTransition, account: AccountId) -> &IncomeReceipt {
    completed
        .income
        .iter()
        .find(|r| r.account == account)
        .unwrap()
}

fn assert_aid_grant_and_gift_accounts(completed: &MaterialCircuitTransition) {
    let donor_income = income(completed, AccountId::Household(control::donor()));
    let organization_income = income(completed, control::organization());
    let recipient_income = income(completed, AccountId::Household(control::recipient()));
    assert!(completed.collections.is_empty());
    let grant = completed
        .aid
        .iter()
        .find(|r| r.outcome == AidOutcome::Granted)
        .unwrap();
    assert_eq!(
        (
            grant.quantity,
            grant.cash_amount,
            grant.carrying_amount,
            grant.contribution_hours
        ),
        (4, money(COLLECTION), money(1_120_000_000), 8)
    );
    assert_eq!(
        organization_income.statement.gift_expense,
        money(COLLECTION)
    );
    assert_eq!(donor_income.statement.gift_expense, money(1_120_000_000));
    assert_eq!(recipient_income.statement.gift_income, money(1_120_400_000));
}

fn assert_collection_identity_and_outcome(
    completed: &MaterialCircuitTransition,
    collections: &[CollectionResolveInput],
    period: u64,
) {
    let result = &completed.collections[0];

    assert_eq!(
        result.original_commitment_id,
        collections[0].original_commitment_id
    );
    assert_eq!(result.command_nonce, collections[0].command_nonce);
    assert_eq!(result.admitted_period, period - 1);
    assert_eq!(result.requested, money(COLLECTION));
    assert_eq!(result.source_hash, collections[0].source_hash);

    if period == 4 {
        assert_protected_service_refusal(completed, collections, result);
    } else {
        assert_full_collection(completed, result);
    }
    result.validate().unwrap();
}

fn assert_protected_service_refusal(
    completed: &MaterialCircuitTransition,
    collections: &[CollectionResolveInput],
    result: &CollectionReceipt,
) {
    assert_eq!(result.outcome, CollectionOutcome::ProtectedServiceUnmet);
    assert_eq!(result.collected, money(0));
    assert_eq!(result.performed_hours, 0);
    assert_eq!(result.transfer_ordinal, None);
    assert_eq!(result.contribution_use_id, [0; 32]);
    let services = completed
        .household_services
        .iter()
        .find(|r| r.principal_id == control::donor() && r.good_id == control::good(6))
        .unwrap();
    assert_eq!(
        (
            services.required_quantity,
            services.satisfied_quantity,
            services.unmet_quantity
        ),
        (8, 3, 5)
    );
    assert!(cash(&completed.state, AccountId::Household(control::donor())) > COLLECTION);
    assert!(remaining(&completed.state, control::donor()) > collections[0].collection_hours);
}

fn assert_full_collection(completed: &MaterialCircuitTransition, result: &CollectionReceipt) {
    let donor_income = income(completed, AccountId::Household(control::donor()));
    let organization_income = income(completed, control::organization());
    assert_eq!(result.outcome, CollectionOutcome::Collected);
    assert_eq!(result.collected, money(COLLECTION));
    assert_eq!(result.performed_hours, 2);
    let transfer = &completed.money_transfers[result.transfer_ordinal.unwrap() as usize];
    assert_eq!(
        transfer.purpose,
        MoneyTransferPurpose::Cash(CashTransferPurpose::MutualAid)
    );
    assert_eq!(
        transfer.debit.location,
        MoneyLocation::Cash(AccountId::Household(control::donor()))
    );
    assert_eq!(
        transfer.credit.location,
        MoneyLocation::Cash(control::organization())
    );
    assert_eq!(transfer.credit.delta, result.collected);
    assert_eq!(donor_income.statement.gift_expense, result.collected);
    assert_eq!(organization_income.statement.gift_income, result.collected);
}

fn assert_canonical_closed_state(completed: &MaterialCircuitTransition) {
    let saved = babylon_material_circuit::encode_material_circuit_state(&completed.state).unwrap();
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&saved).unwrap(),
        completed.state
    );
}

fn assert_four_period_reconciliation(state: &MaterialCircuitState, totals: &ControlTotals) {
    let ControlTotals {
        donor_net,
        organization_gifts,
        recipient_gifts,
        selected_food_consumed,
        selected_materials_consumed,
        supplier_food_consumed,
        total_tax,
    } = *totals;
    assert_eq!(donor_net, -27_720_800_000);
    assert_eq!(organization_gifts, 800_000);
    assert_eq!(recipient_gifts, 1_120_400_000);
    assert_eq!(total_tax, 4_608_000_000);
    assert_eq!(cash(state, public()), total_tax);
    assert_eq!(
        cash(state, AccountId::Household(control::recipient())),
        COLLECTION
    );
    assert_eq!(
        (
            selected_food_consumed,
            selected_materials_consumed,
            supplier_food_consumed
        ),
        (36, 16, 20)
    );
    assert_eq!(stock(state, control::suppliers(), FOOD), 0);
    assert_eq!(stock(state, control::recipient(), FOOD), 0);
    assert!(state.inventory.iter().all(|r| r.quantity == 0));
    let accounts = control::economy(state).costs.snapshot().accounts;
    let account = accounts
        .iter()
        .find(|r| r.account == AccountId::Household(control::donor()))
        .unwrap();
    assert_eq!(account.opening_capital, money(30_576_000_000));
    assert_eq!(account.retained_earnings, money(donor_net));
    assert_eq!(
        account
            .opening_capital
            .checked_add(account.retained_earnings)
            .unwrap(),
        money(2_855_200_000)
    );
}

#[test]
fn removing_first_collection_severs_later_aid_from_empty_organization() {
    let first = control::close(&control::opening(), &[], &[]).unwrap();
    assert_eq!(cash(&first.state, control::organization()), 0);
    let second = control::close(
        &control::controlled_opening(first.state),
        &[control::aid(2)],
        &[],
    )
    .unwrap();
    assert!(!second
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::Granted && r.quantity > 0));
    assert!(second
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::Requested && r.quantity == 4));
    assert_eq!(stock(&second.state, control::donor(), FOOD), 8);
    assert_eq!(remaining(&second.state, control::recipient()), 432);
    assert_eq!(
        cash(&second.state, AccountId::Household(control::recipient())),
        0
    );
    assert_eq!(
        second
            .household_consumption
            .iter()
            .find(|r| r.principal_id == control::recipient())
            .unwrap()
            .consumed_quantity,
        0
    );
}

#[test]
fn invalid_late_collection_keeps_opening_and_exact_retry_unchanged() {
    let state = control::opening();
    let before = babylon_material_circuit::encode_material_circuit_state(&state).unwrap();
    let mut invalid = control::collection(1);
    invalid.source_hash = [0; 32];
    assert_eq!(
        control::close(&state, &[], &[invalid]),
        Err(MaterialCircuitError::CollectionInvariant)
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&state).unwrap(),
        before
    );
    let accepted = control::collection(1);
    let expected = control::close(&state, &[], std::slice::from_ref(&accepted)).unwrap();
    assert_eq!(
        control::close(
            &babylon_material_circuit::decode_material_circuit_state(&before).unwrap(),
            &[],
            &[accepted]
        )
        .unwrap(),
        expected
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&state).unwrap(),
        before
    );
}
