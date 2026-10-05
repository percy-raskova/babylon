//! PER-345's retained four-period accounting capsule through the shared close.
//!
//! Source capsule: reports/test-results/per345-funding/2026-10-04/
//! four-period-paper-control on the retained PER-343 worktree. This bounded
//! Designed component control proves accounting and canonical re-execution;
//! Retained control.json SHA-256:
//! 5eb13e470f1b7ba3aa90a03b97608267fb9021c47c98fb0b446fffc956a4dcca.
//! Organizer command admission and atomic campaign publication have separate
//! MaterialReplaySession controls. It is not national play qualification.
#[path = "support/organizer_funding_control.rs"]
mod control;

use babylon_material_circuit::*;
use control::*;

#[test]
fn four_period_collection_aid_savings_and_protected_service_control() {
    let mut state = opening();
    assert_eq!(
        economy(&state).book.total_cash_and_reserves().unwrap(),
        money(PAPER_CASH)
    );
    let cohorts = &economy(&state).recurring.as_ref().unwrap().households;
    assert_eq!(
        cohorts
            .iter()
            .filter(|r| r.principal_id != suppliers())
            .map(|r| r.persons)
            .sum::<u64>(),
        12
    );
    assert_eq!(cohorts.iter().map(|r| r.persons).sum::<u64>(), 17);
    assert_eq!(stock(&state, donor(), FOOD) + 36, 44);
    assert_eq!(stock(&state, donor(), MATERIALS) + 16, 20);
    assert_eq!(stock(&state, suppliers(), FOOD), 20);
    let original_cohorts = cohorts.clone();
    let mut donor_net = 0_i128;
    let mut organization_gifts = 0_i128;
    let mut recipient_gifts = 0_i128;
    let mut selected_food_consumed = 0_u64;
    let mut selected_materials_consumed = 0_u64;
    let mut supplier_food_consumed = 0_u64;
    let mut total_tax = 0_i128;
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
        state = controlled_opening(state);
        assert_eq!(state.period, period);
        let before = encode_material_circuit_state(&state).unwrap();
        let gifts = if period == 2 {
            vec![aid(period)]
        } else {
            vec![]
        };
        let collections = if period == 2 {
            vec![]
        } else {
            vec![collection(period)]
        };
        let mut completed = close(&state, &gifts, &collections).unwrap();
        assert_eq!(encode_material_circuit_state(&state).unwrap(), before);
        let decoded = decode_material_circuit_state(&before).unwrap();
        let mut repeated = close(&decoded, &gifts, &collections).unwrap();
        if period == 2 {
            coordinate(&mut completed);
            coordinate(&mut repeated);
        }
        assert_eq!(repeated, completed);
        assert_eq!(
            cash(&completed.state, AccountId::Household(donor())),
            expected_cash,
            "donor P{period}"
        );
        assert_eq!(
            cash(&completed.state, organization()),
            expected_organization,
            "organization P{period}"
        );
        assert_eq!(stock(&completed.state, donor(), FOOD), expected_food);
        assert_eq!(stock(&completed.state, donor(), MATERIALS), 4);
        assert_eq!(
            remaining(&completed.state, donor()),
            donor_hours,
            "donor hours P{period}"
        );
        assert_eq!(
            remaining(&completed.state, recipient()),
            recipient_hours,
            "recipient hours P{period}"
        );
        assert_eq!(
            economy(&completed.state)
                .recurring
                .as_ref()
                .unwrap()
                .households,
            original_cohorts
        );
        assert_eq!(
            economy(&completed.state)
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
        let wages = completed
            .wage_accruals
            .iter()
            .filter(|r| r.payee == AccountId::Household(donor()))
            .collect::<Vec<_>>();
        let labor = completed
            .member_labor_use
            .iter()
            .find(|r| r.site_id == site(EMPLOYER))
            .unwrap();
        let expected_wages = if period <= 2 { 15_360_000_000 } else { 0 };
        let expected_attendance = if period <= 2 { 640 } else { 0 };
        assert_eq!(labor.attended_hours, expected_attendance);
        assert_eq!(labor.accrued_wages.micro_units(), expected_wages);
        assert_eq!(labor.idle_wages.micro_units(), expected_wages);
        assert_eq!(
            cash(&completed.state, AccountId::Site(site(EMPLOYER))),
            if period == 1 { 15_360_000_000 } else { 0 }
        );
        assert!(!completed
            .production
            .iter()
            .any(|r| r.site_id == site(EMPLOYER) && r.produced_batches > 0));
        assert_eq!(
            labor.production_hours
                + labor.handling_hours
                + labor.maintenance_hours
                + labor.installation_hours,
            0
        );
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
        let tax = completed
            .taxes
            .iter()
            .find(|r| r.payer == AccountId::Household(donor()))
            .unwrap();
        assert_eq!(tax.taxable_amount.micro_units(), expected_wages);
        assert_eq!(
            tax.assessed.micro_units(),
            if period <= 2 { 2_304_000_000 } else { 0 }
        );
        assert_eq!(tax.collected, tax.assessed);
        assert_eq!(tax.uncollected, money(0));
        total_tax += tax.collected.micro_units();
        let books = economy(&completed.state).book.snapshot();
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
        let donor_income = completed
            .income
            .iter()
            .find(|r| r.account == AccountId::Household(donor()))
            .unwrap();
        let organization_income = completed
            .income
            .iter()
            .find(|r| r.account == organization())
            .unwrap();
        let recipient_income = completed
            .income
            .iter()
            .find(|r| r.account == AccountId::Household(recipient()))
            .unwrap();
        donor_net += donor_income.net_income.micro_units();
        organization_gifts += organization_income.statement.gift_income.micro_units();
        recipient_gifts += recipient_income.statement.gift_income.micro_units();
        assert_eq!(donor_income.statement.public_transfer_income, money(0));
        assert_eq!(donor_income.statement.distribution_income, money(0));
        let recipient_consumption = completed
            .household_consumption
            .iter()
            .find(|r| r.principal_id == recipient())
            .unwrap();
        assert_eq!(
            recipient_consumption.consumed_quantity,
            if period == 2 { 4 } else { 0 }
        );
        selected_food_consumed += completed
            .household_consumption
            .iter()
            .filter(|r| r.principal_id != suppliers() && r.good_id == good(FOOD))
            .map(|r| r.consumed_quantity)
            .sum::<u64>();
        selected_materials_consumed += completed
            .household_consumption
            .iter()
            .filter(|r| r.good_id == good(MATERIALS))
            .map(|r| r.consumed_quantity)
            .sum::<u64>();
        let supplementary = completed
            .household_consumption
            .iter()
            .find(|r| r.principal_id == suppliers())
            .unwrap();
        assert_eq!(
            (
                supplementary.consumed_quantity,
                supplementary.unmet_quantity
            ),
            (5, 0)
        );
        supplier_food_consumed += supplementary.consumed_quantity;
        for receipt in &completed.service_outputs {
            assert!(receipt.produced_quantity <= if receipt.good_id == good(5) { 4 } else { 8 });
            assert_eq!(receipt.direct_cost, money(0)); // Explicit WorkingOwner support.
        }
        if period == 2 {
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
        } else {
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
                assert_eq!(result.outcome, CollectionOutcome::ProtectedServiceUnmet);
                assert_eq!(result.collected, money(0));
                assert_eq!(result.performed_hours, 0);
                assert_eq!(result.transfer_ordinal, None);
                assert_eq!(result.contribution_use_id, [0; 32]);
                let services = completed
                    .household_services
                    .iter()
                    .find(|r| r.principal_id == donor() && r.good_id == good(6))
                    .unwrap();
                assert_eq!(
                    (
                        services.required_quantity,
                        services.satisfied_quantity,
                        services.unmet_quantity
                    ),
                    (8, 3, 5)
                );
                assert!(cash(&completed.state, AccountId::Household(donor())) > COLLECTION);
                assert!(remaining(&completed.state, donor()) > collections[0].collection_hours);
            } else {
                assert_eq!(result.outcome, CollectionOutcome::Collected);
                assert_eq!(result.collected, money(COLLECTION));
                assert_eq!(result.performed_hours, 2);
                let transfer =
                    &completed.money_transfers[result.transfer_ordinal.unwrap() as usize];
                assert_eq!(
                    transfer.purpose,
                    MoneyTransferPurpose::Cash(CashTransferPurpose::MutualAid)
                );
                assert_eq!(
                    transfer.debit.location,
                    MoneyLocation::Cash(AccountId::Household(donor()))
                );
                assert_eq!(
                    transfer.credit.location,
                    MoneyLocation::Cash(organization())
                );
                assert_eq!(transfer.credit.delta, result.collected);
                assert_eq!(donor_income.statement.gift_expense, result.collected);
                assert_eq!(organization_income.statement.gift_income, result.collected);
            }
            result.validate().unwrap();
        }
        let saved = encode_material_circuit_state(&completed.state).unwrap();
        assert_eq!(
            decode_material_circuit_state(&saved).unwrap(),
            completed.state
        );
        state = completed.state;
    }
    assert_eq!(donor_net, -27_720_800_000);
    assert_eq!(organization_gifts, 800_000);
    assert_eq!(recipient_gifts, 1_120_400_000);
    assert_eq!(total_tax, 4_608_000_000);
    assert_eq!(cash(&state, public()), total_tax);
    assert_eq!(cash(&state, AccountId::Household(recipient())), COLLECTION);
    assert_eq!(
        (
            selected_food_consumed,
            selected_materials_consumed,
            supplier_food_consumed
        ),
        (36, 16, 20)
    );
    assert_eq!(stock(&state, suppliers(), FOOD), 0);
    assert_eq!(stock(&state, recipient(), FOOD), 0);
    assert!(state.inventory.iter().all(|r| r.quantity == 0));
    let accounts = economy(&state).costs.snapshot().accounts;
    let account = accounts
        .iter()
        .find(|r| r.account == AccountId::Household(donor()))
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
    let first = close(&opening(), &[], &[]).unwrap();
    assert_eq!(cash(&first.state, organization()), 0);
    let second = close(&controlled_opening(first.state), &[aid(2)], &[]).unwrap();
    assert!(!second
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::Granted && r.quantity > 0));
    assert!(second
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::Requested && r.quantity == 4));
    assert_eq!(stock(&second.state, donor(), FOOD), 8);
    assert_eq!(remaining(&second.state, recipient()), 432);
    assert_eq!(cash(&second.state, AccountId::Household(recipient())), 0);
    assert_eq!(
        second
            .household_consumption
            .iter()
            .find(|r| r.principal_id == recipient())
            .unwrap()
            .consumed_quantity,
        0
    );
}

#[test]
fn invalid_late_collection_keeps_opening_and_exact_retry_unchanged() {
    let state = opening();
    let before = encode_material_circuit_state(&state).unwrap();
    let mut invalid = collection(1);
    invalid.source_hash = [0; 32];
    assert_eq!(
        close(&state, &[], &[invalid]),
        Err(MaterialCircuitError::CollectionInvariant)
    );
    assert_eq!(encode_material_circuit_state(&state).unwrap(), before);
    let accepted = collection(1);
    let expected = close(&state, &[], std::slice::from_ref(&accepted)).unwrap();
    assert_eq!(
        close(
            &decode_material_circuit_state(&before).unwrap(),
            &[],
            &[accepted]
        )
        .unwrap(),
        expected
    );
    assert_eq!(encode_material_circuit_state(&state).unwrap(), before);
}
