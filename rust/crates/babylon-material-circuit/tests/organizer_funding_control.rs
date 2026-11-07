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
use babylon_material_circuit::CircuitAccounting;
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
use babylon_material_circuit::OutboundOrderId;
use babylon_material_circuit::{MaterialCatalog, MaterialPurchase, OrderId, ServiceOrder};
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
    let (mut catalog, mut state) = control::opening();
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
        (catalog, state) = control::controlled_opening(catalog, state);
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
        let completed = close_and_reexecute(&catalog, &state, &gifts, &collections);
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
        assert_canonical_closed_state(&catalog, &completed);
        state = completed.state;
    }
    assert_four_period_reconciliation(&state, &totals);
}

fn assert_opening_accounting(state: &MaterialCircuitState) -> Vec<HouseholdCohort> {
    assert_eq!(
        control::economy(state)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        control::money(PAPER_CASH)
    );
    let cohorts = &control::economy(state)
        .recurring
        .as_ref()
        .expect("the fixture set the optional field before this read")
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
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    gifts: &[AidResolveInput],
    collections: &[CollectionResolveInput],
) -> MaterialCircuitTransition {
    let period = state.period;
    let before = babylon_material_circuit::encode_material_circuit_state(catalog, state)
        .expect("the canonical material state encodes");
    let mut completed = control::close(catalog, state, gifts, collections)
        .expect("the fixture call `close` succeeds for the authored inputs");

    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(catalog, state)
            .expect("the canonical material state encodes"),
        before
    );
    let decoded = babylon_material_circuit::decode_material_circuit_state(catalog, &before)
        .expect("the canonical material bytes decode");
    let mut repeated = control::close(catalog, &decoded, gifts, collections)
        .expect("the fixture call `close` succeeds for the authored inputs");
    if period == 2 {
        control::coordinate(catalog, &mut completed);
        control::coordinate(catalog, &mut repeated);
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
            .expect("the fixture set the optional field before this read")
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
            .expect("the fixture book totals without overflow"),
        control::money(PAPER_CASH)
    );
    for transfer in &completed.money_transfers {
        assert_eq!(
            transfer
                .debit
                .delta
                .checked_add(transfer.credit.delta)
                .expect("the fixture arithmetic stays in range"),
            control::money(0)
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
        .expect("the fixture holds the searched element");
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
        .expect("the fixture holds the searched element");
    assert_eq!(tax.taxable_amount.micro_units(), expected_wages);
    assert_eq!(
        tax.assessed.micro_units(),
        if period <= 2 { 2_304_000_000 } else { 0 }
    );
    assert_eq!(tax.collected, tax.assessed);
    assert_eq!(tax.uncollected, control::money(0));
    let books = control::economy(&completed.state).book.snapshot();
    assert!(books
        .purchases
        .iter()
        .all(
            |r| r.reserved_amount().expect("the fixture reservation exists") == control::money(0)
        ));
    assert!(books.shifts.iter().all(|r| r
        .reserved_amount()
        .expect("the fixture reservation exists")
        == control::money(0)
        && r.outstanding_wages()
            .expect("the fixture payroll carries its authored wages")
            == control::money(0)));
    assert!(
        control::economy(&completed.state).aid.freight.is_empty(),
        "this local gift leaves no pending physical principal"
    );

    tax.collected.micro_units()
}

fn reconcile_income(completed: &MaterialCircuitTransition, totals: &mut ControlTotals) {
    let donor_income = completed
        .income
        .iter()
        .find(|r| r.account == AccountId::Household(control::donor()))
        .expect("the fixture holds the searched element");
    let organization_income = completed
        .income
        .iter()
        .find(|r| r.account == control::organization())
        .expect("the fixture holds the searched element");
    let recipient_income = completed
        .income
        .iter()
        .find(|r| r.account == AccountId::Household(control::recipient()))
        .expect("the fixture holds the searched element");
    totals.donor_net += donor_income.net_income.micro_units();
    totals.organization_gifts += organization_income.statement.gift_income.micro_units();
    totals.recipient_gifts += recipient_income.statement.gift_income.micro_units();
    assert_eq!(
        donor_income.statement.public_transfer_income,
        control::money(0)
    );
    assert_eq!(
        donor_income.statement.distribution_income,
        control::money(0)
    );
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
        .expect("the fixture holds the searched element");
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
        .expect("the fixture holds the searched element");
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
        assert_eq!(receipt.direct_cost, control::money(0)); // Explicit WorkingOwner support.
    }
}

fn income(completed: &MaterialCircuitTransition, account: AccountId) -> &IncomeReceipt {
    completed
        .income
        .iter()
        .find(|r| r.account == account)
        .expect("the fixture holds the searched element")
}

fn assert_aid_grant_and_gift_accounts(completed: &MaterialCircuitTransition) {
    let donor_income = income(completed, AccountId::Household(control::donor()));
    let organization_income = income(completed, control::organization());
    let recipient_income = income(completed, AccountId::Household(control::recipient()));
    assert_eq!(completed.collections.len(), 0);
    let grant = completed
        .aid
        .iter()
        .find(|r| r.outcome == AidOutcome::Granted)
        .expect("the fixture holds the searched element");
    assert_eq!(
        (
            grant.quantity,
            grant.cash_amount,
            grant.carrying_amount,
            grant.contribution_hours
        ),
        (4, control::money(0), control::money(1_120_000_000), 8)
    );
    assert!(completed
        .aid
        .iter()
        .any(|row| row.outcome == AidOutcome::CashGranted
            && row.quantity == 0
            && row.cash_amount == control::money(COLLECTION)));
    assert_eq!(
        organization_income.statement.gift_expense,
        control::money(COLLECTION)
    );
    assert_eq!(
        donor_income.statement.gift_expense,
        control::money(1_120_000_000)
    );
    assert_eq!(
        recipient_income.statement.gift_income,
        control::money(1_120_400_000)
    );
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
    assert_eq!(result.requested, control::money(COLLECTION));
    assert_eq!(result.source_hash, collections[0].source_hash);

    if period == 4 {
        assert_protected_service_refusal(completed, collections, result);
    } else {
        assert_full_collection(completed, result);
    }
    result
        .validate()
        .expect("the authored fixture passes validation");
}

fn assert_protected_service_refusal(
    completed: &MaterialCircuitTransition,
    collections: &[CollectionResolveInput],
    result: &CollectionReceipt,
) {
    assert_eq!(result.outcome, CollectionOutcome::ProtectedServiceUnmet);
    assert_eq!(result.collected, control::money(0));
    assert_eq!(result.performed_hours, 0);
    assert_eq!(result.transfer_ordinal, None);
    assert_eq!(result.contribution_use_id, [0; 32]);
    let services = completed
        .household_services
        .iter()
        .find(|r| r.principal_id == control::donor() && r.good_id == control::good(6))
        .expect("the fixture holds the searched element");
    assert_eq!(
        (
            services.required_quantity,
            services.satisfied_quantity,
            services.unmet_quantity
        ),
        (8, 3, 5)
    );
    let order = completed
        .service_performance
        .iter()
        .find(|row| {
            row.buyer == AccountId::Household(control::donor()) && row.good_id == control::good(6)
        })
        .expect("the P4 household-service order reports its actual admission");
    assert_eq!(
        (
            order.requested_quantity,
            order.admitted_quantity,
            order.performed_quantity
        ),
        (8, 3, 3)
    );
    assert!(cash(&completed.state, AccountId::Household(control::donor())) > COLLECTION);
    assert!(remaining(&completed.state, control::donor()) > collections[0].collection_hours);
}

fn assert_full_collection(completed: &MaterialCircuitTransition, result: &CollectionReceipt) {
    let donor_income = income(completed, AccountId::Household(control::donor()));
    let organization_income = income(completed, control::organization());
    assert_eq!(result.outcome, CollectionOutcome::Collected);
    assert_eq!(result.collected, control::money(COLLECTION));
    assert_eq!(result.performed_hours, 2);
    let transfer = &completed.money_transfers[result
        .transfer_ordinal
        .expect("the fixture value `transfer_ordinal` is present before this read")
        as usize];
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

fn assert_canonical_closed_state(catalog: &MaterialCatalog, completed: &MaterialCircuitTransition) {
    let saved = babylon_material_circuit::encode_material_circuit_state(catalog, &completed.state)
        .expect("the canonical material state encodes");
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(catalog, &saved)
            .expect("the canonical material bytes decode"),
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
        .expect("the fixture holds the searched element");
    assert_eq!(account.opening_capital, control::money(30_576_000_000));
    assert_eq!(account.retained_earnings, control::money(donor_net));
    assert_eq!(
        account
            .opening_capital
            .checked_add(account.retained_earnings)
            .expect("the fixture arithmetic stays in range"),
        control::money(2_855_200_000)
    );
}

#[test]
fn removing_first_collection_severs_cash_but_preserves_independent_food() {
    let (catalog, opening) = control::opening();
    let first = control::close(&catalog, &opening, &[], &[])
        .expect("the fixture call `close` succeeds for the authored inputs");
    assert_eq!(cash(&first.state, control::organization()), 0);
    let (catalog, controlled) = control::controlled_opening(catalog, first.state);
    let second = control::close(&catalog, &controlled, &[control::aid(2)], &[])
        .expect("the fixture call `close` succeeds for the authored inputs");
    assert!(second.aid.iter().any(|r| r.outcome == AidOutcome::Granted
        && r.quantity == 4
        && r.cash_amount == control::money(0)));
    assert!(second
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::CashUnfunded && r.cash_amount == control::money(0)));
    assert!(second
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::Requested && r.quantity == 4));
    assert_eq!(stock(&second.state, control::donor(), FOOD), 4);
    // This negative control closes material support without calling coordinate:
    // four consumed parcels release 80 hours from 432, with no political debit.
    assert_eq!(remaining(&second.state, control::recipient()), 512);
    assert_eq!(
        cash(&second.state, AccountId::Household(control::recipient())),
        0
    );
    assert_eq!(
        second
            .household_consumption
            .iter()
            .find(|r| r.principal_id == control::recipient())
            .expect("the fixture holds the searched element")
            .consumed_quantity,
        4
    );
}

#[test]
fn invalid_late_collection_keeps_opening_and_exact_retry_unchanged() {
    let (catalog, state) = control::opening();
    let before = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
    let mut invalid = control::collection(1);
    invalid.source_hash = [0; 32];
    assert_eq!(
        control::close(&catalog, &state, &[], &[invalid]),
        Err(MaterialCircuitError::CollectionInvariant)
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
            .expect("the canonical material state encodes"),
        before
    );
    let accepted = control::collection(1);
    let expected = control::close(&catalog, &state, &[], std::slice::from_ref(&accepted))
        .expect("the fixture call `close` succeeds for the authored inputs");
    assert_eq!(
        control::close(
            &catalog,
            &babylon_material_circuit::decode_material_circuit_state(&catalog, &before)
                .expect("the canonical material bytes decode"),
            &[],
            &[accepted]
        )
        .expect("the fixture call `close` succeeds for the authored inputs"),
        expected
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
            .expect("the canonical material state encodes"),
        before
    );
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "one paired three-close control proves real collection, unchanged gift-close needs and later ordinary settlement"
)]
fn collected_cash_only_changes_next_ordinary_food_purchase_in_finite_control() {
    // Designed finite paper economy with national $280 parcel price; this is a
    // phase/accounting control, not evidence that the normal national donor can collect.
    let (catalog, mut opening) = control::opening();
    let CircuitAccounting::Monetary(economy) = &mut opening.accounting else {
        panic!("monetary control");
    };
    economy
        .recurring
        .as_mut()
        .expect("households")
        .household_purchases
        .iter_mut()
        .find(|row| row.principal_id == control::recipient())
        .expect("recipient policy")
        .enabled = true;
    let mut contribution = control::collection(1);
    contribution.requested = control::money(1_450_000_000);
    let collected =
        control::close(&catalog, &opening, &[], &[contribution]).expect("lawful contribution");
    assert_eq!(
        collected.collections[0].collected,
        control::money(1_450_000_000)
    );
    assert_eq!(
        cash(&collected.state, control::organization()),
        1_450_000_000
    );
    assert_eq!(
        control::economy(&collected.state)
            .book
            .total_cash_and_reserves()
            .expect("cash sum"),
        control::money(PAPER_CASH)
    );
    let (catalog, opening) = control::controlled_opening(catalog, collected.state);
    let ordinary = control::close(&catalog, &opening, &[], &[]).expect("ordinary close");
    let mut gift = control::aid(2);
    gift.quantity = 0;
    gift.cash = control::money(1_450_000_000);
    let aided = control::close(&catalog, &opening, &[gift], &[]).expect("cash-only close");
    assert_eq!(aided.household_consumption, ordinary.household_consumption);
    assert_eq!(aided.household_services, ordinary.household_services);
    assert_eq!(aided.household_time, ordinary.household_time);
    assert_eq!(aided.aid_contributions.len(), 0);
    assert_eq!(cash(&aided.state, control::organization()), 0);
    assert_eq!(
        cash(&aided.state, AccountId::Household(control::recipient())),
        1_450_000_000
    );
    assert_eq!(
        income(&aided, control::organization())
            .statement
            .gift_expense,
        control::money(1_450_000_000)
    );
    assert_eq!(
        income(&aided, AccountId::Household(control::recipient()))
            .statement
            .gift_income,
        control::money(1_450_000_000)
    );
    let saved = babylon_material_circuit::encode_material_circuit_state(&catalog, &aided.state)
        .expect("saved gift");
    let reopened = babylon_material_circuit::decode_material_circuit_state(&catalog, &saved)
        .expect("reopened gift");
    let (_, ordinary_opening) = control::controlled_opening(catalog.clone(), ordinary.state);
    let (catalog, aided_opening) = control::controlled_opening(catalog, reopened);
    let ordinary =
        control::close(&catalog, &ordinary_opening, &[], &[]).expect("ordinary next close");
    let aided = control::close(&catalog, &aided_opening, &[], &[]).expect("funded next close");
    let consumed = |close: &MaterialCircuitTransition| {
        close
            .household_consumption
            .iter()
            .find(|row| {
                row.principal_id == control::recipient() && row.good_id == control::good(FOOD)
            })
            .expect("food need")
            .consumed_quantity
    };
    assert_eq!(consumed(&ordinary), 0);
    assert_eq!(consumed(&aided), 4);
    assert_eq!(
        cash(&aided.state, AccountId::Household(control::recipient())),
        330_000_000
    );
    assert_eq!(remaining(&ordinary.state, control::recipient()), 432);
    assert_eq!(remaining(&aided.state, control::recipient()), 512);
    assert!(
        aided.aid.is_empty(),
        "ordinary purchasing is not another gift"
    );
    assert_eq!(
        control::economy(&aided.state)
            .book
            .total_cash_and_reserves()
            .expect("cash sum"),
        control::money(PAPER_CASH)
    );
    let demand = aided
        .household_demand
        .iter()
        .find(|row| row.principal_id == control::recipient() && row.good_id == control::good(FOOD))
        .expect("ordinary recipient order");
    assert_eq!(demand.unit_price, control::money(280_000_000));
    assert_eq!(demand.fulfilled_quantity, 4);
    let order = OutboundOrderId::LocalFinalDemand(demand.order_id);
    let payment = aided
        .money_transfers
        .iter()
        .find(|row| row.purpose == MoneyTransferPurpose::DeliverySettlement(order))
        .expect("actual ordinary settlement");
    assert_eq!(
        payment.debit.location,
        MoneyLocation::PurchaseReserve(order)
    );
    assert_eq!(
        payment.credit.location,
        MoneyLocation::Cash(AccountId::Site(demand.retailer_site_id))
    );
    assert_eq!(payment.debit.delta, control::money(-4 * 280_000_000));
    assert_eq!(payment.credit.delta, control::money(4 * 280_000_000));
}

#[test]
fn funded_utility_shortfall_keeps_refund_and_floor_before_partial_gift() {
    for capacity in [7, 0] {
        let (catalog, mut state) = control::opening();
        state
            .production_commitments
            .iter_mut()
            .find(|row| row.site_id == control::site(3))
            .expect("utility production commitment")
            .planned_batches = capacity;
        state
            .production_commitments
            .retain(|row| row.planned_batches > 0);
        let donor = AccountId::Household(control::donor());
        let baseline = control::close(&catalog, &state, &[], &[]).expect("ordinary close");
        let performance = baseline
            .service_performance
            .iter()
            .find(|row| row.buyer == donor && row.good_id == control::good(3))
            .expect("donor's utility order");
        assert_eq!(
            (
                performance.requested_quantity,
                performance.admitted_quantity,
                performance.performed_quantity
            ),
            (8, 8, capacity)
        );
        let expected_refund = i128::from(8 - capacity) * 75_000_000;
        let id = OutboundOrderId::Service(performance.order_id);
        let refund = baseline
            .money_transfers
            .iter()
            .find(|row| row.purpose == MoneyTransferPurpose::PurchaseRefund(id))
            .expect("cash returned to donor");
        assert_eq!(refund.credit.location, MoneyLocation::Cash(donor));
        assert_eq!(refund.credit.delta.micro_units(), expected_refund);
        let opening_eligible_balance = control::cash(&baseline.state, donor);
        let mut input = control::collection(1);
        let floor = opening_eligible_balance - expected_refund - 100_001;
        input.protected_cash_floor = control::money(floor);
        let completed = close_and_reexecute(&catalog, &state, &[], std::slice::from_ref(&input));
        let receipt = &completed.collections[0];
        assert_eq!(receipt.outcome, CollectionOutcome::PartiallyCollected);
        assert_eq!(receipt.collected.micro_units(), 100_001);
        assert_eq!(receipt.performed_hours, 2);
        assert_eq!(
            control::cash(&completed.state, donor),
            floor + expected_refund
        );
        assert_eq!(
            control::cash(&completed.state, control::organization())
                - control::cash(&baseline.state, control::organization()),
            100_001
        );
        assert_eq!(completed.household_services, baseline.household_services);
        input.protected_cash_floor = control::money(opening_eligible_balance - expected_refund);
        let protected = control::close(&catalog, &state, &[], &[input])
            .expect("floor and refund consume the full remaining balance");
        let refused = &protected.collections[0];
        assert_eq!(
            (
                refused.outcome,
                refused.collected,
                refused.performed_hours,
                refused.transfer_ordinal
            ),
            (
                CollectionOutcome::InsufficientCash,
                control::money(0),
                0,
                None
            )
        );
        assert_eq!(
            control::cash(&protected.state, donor),
            opening_eligible_balance
        );
    }
}

#[test]
fn carried_service_reserve_and_current_topup_join_their_own_prices() {
    let (catalog, mut opening) = control::opening();
    opening
        .production_commitments
        .retain(|row| row.site_id != control::site(3));
    let donor = AccountId::Household(control::donor());
    let carried_id = OrderId::from_bytes([29; 32]);
    let (state, opening_reservation) = babylon_material_circuit::admit_material_purchase(
        &catalog,
        &opening,
        MaterialPurchase::Service(ServiceOrder {
            order_id: carried_id,
            performance_period: 1,
            provider_site_id: control::site(3),
            buyer: donor,
            good_id: control::good(3),
            unit_id: control::unit(3),
            quantity: 3,
        }),
        control::money(12_345),
    )
    .expect("distinct three-unit commitment at accepted price");
    assert_eq!(opening_reservation.credit.delta.micro_units(), 37_035);
    let routine = control::close(&catalog, &state, &[], &[]).expect("ordinary close");
    let mut input = control::collection(1);
    let refunded = 37_035 + 5 * 75_000_000;
    input.protected_cash_floor =
        control::money(control::cash(&routine.state, donor) - refunded - 11);
    let closed = close_and_reexecute(&catalog, &state, &[], &[input]);
    assert_eq!(closed.collections[0].collected, control::money(11));
    assert_eq!(
        closed.collections[0].outcome,
        CollectionOutcome::PartiallyCollected
    );
    let carried = OutboundOrderId::Service(carried_id);
    assert!(!closed
        .money_transfers
        .iter()
        .any(|m| m.purpose == MoneyTransferPurpose::PurchaseReservation(carried)));
    assert!(closed.money_transfers.iter().any(|m| m.purpose
        == MoneyTransferPurpose::PurchaseRefund(carried)
        && m.credit.delta.micro_units() == 37_035));
}

#[test]
fn under_requested_essential_service_still_blocks_cash_and_hours() {
    for maximum in [0, 7] {
        let (catalog, mut opening) = control::opening();
        let CircuitAccounting::Monetary(economy) = &mut opening.accounting else {
            panic!("monetary paper economy");
        };
        let policy = economy
            .recurring
            .as_mut()
            .expect("recurring purchases")
            .household_purchases
            .iter_mut()
            .find(|p| p.principal_id == control::donor() && p.good_id == control::good(3))
            .expect("utility purchase policy");
        policy.enabled = maximum != 0;
        if maximum != 0 {
            policy.maximum_purchase = maximum;
        }
        let result = close_and_reexecute(&catalog, &opening, &[], &[control::collection(1)]);
        let row = &result.collections[0];
        assert_eq!(
            (row.outcome, row.collected, row.performed_hours),
            (
                CollectionOutcome::ProtectedServiceUnmet,
                control::money(0),
                0
            )
        );
    }
}
