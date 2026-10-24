use super::{Refusal, Result, Terms};
use crate::observer_reader::CommittedMaterialReceipts;
use crate::runtime_session::OrganizerSnapshot;

use babylon_material_circuit::{
    AccountId, AidOutcome, AidReceipt, FinalDemandPrincipalId, HouseholdContributionReceipt,
    HouseholdTimeReceipt, MoneyLocation, MoneyTransferPurpose,
};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::{BTreeMap, BTreeSet};

type Movement = (MoneyLocation, MoneyLocation, i128);
type Movements = BTreeMap<(u8, [u8; 32]), Movement>;

pub(super) fn check_period(receipts: &MaterialTickReceipts) -> Result<()> {
    check_cash(receipts)?;
    let mut gifts = BTreeMap::<AccountId, (i128, i128)>::new();
    let mut losses = BTreeMap::<AccountId, i128>::new();
    for row in &receipts.aid {
        let carrying = row.carrying_amount.micro_units();
        if carrying < 0
            || (matches!(row.outcome, AidOutcome::Requested | AidOutcome::Unshipped)
                && carrying != 0)
        {
            return Err(Refusal::Income);
        }
        if row.outcome == AidOutcome::Lost {
            super::cash(
                losses.entry(AccountId::Household(row.donor)).or_default(),
                carrying,
            )?;
        }
        if row.outcome != AidOutcome::Granted {
            continue;
        }
        let money = row.cash_amount.micro_units();
        gift(&mut gifts, AccountId::Household(row.donor), carrying, 0)?;
        gift(&mut gifts, row.payer, money, 0)?;
        gift(
            &mut gifts,
            AccountId::Household(row.recipient),
            0,
            carrying.checked_add(money).ok_or(Refusal::Overflow)?,
        )?;
        let consumption = super::one(
            receipts.household_consumption.iter().filter(|c| {
                c.principal_id == row.recipient
                    && c.good_id == row.good_id
                    && c.unit_id == row.unit_id
            }),
            Refusal::Consumption,
        )?;
        if consumption.period != receipts.resolve_tick
            || consumption
                .consumed_quantity
                .checked_add(consumption.unmet_quantity)
                != Some(consumption.required_quantity)
            || consumption
                .consumed_quantity
                .checked_add(consumption.closing_quantity)
                != Some(consumption.available_quantity)
            || consumption.available_quantity < row.quantity
        {
            return Err(Refusal::Consumption);
        }
    }
    for (account, (expense, income)) in gifts {
        let row = super::one(
            receipts.income.iter().filter(|r| r.account == account),
            Refusal::Income,
        )?;
        if row.period != receipts.resolve_tick
            || row.statement.gift_expense.micro_units() != expense
            || row.statement.gift_income.micro_units() != income
        {
            return Err(Refusal::Income);
        }
    }
    for (account, amount) in losses {
        let row = super::one(
            receipts.income.iter().filter(|r| r.account == account),
            Refusal::Income,
        )?;
        if row.period != receipts.resolve_tick
            || row.statement.freight_loss_expense.micro_units() != amount
        {
            return Err(Refusal::Income);
        }
    }
    Ok(())
}
fn gift(
    map: &mut BTreeMap<AccountId, (i128, i128)>,
    account: AccountId,
    expense: i128,
    income: i128,
) -> Result<()> {
    let row = map.entry(account).or_default();
    super::cash(&mut row.0, expense)?;
    super::cash(&mut row.1, income)
}
fn movement(
    map: &mut Movements,
    key: (u8, [u8; 32]),
    debit: MoneyLocation,
    credit: MoneyLocation,
    amount: i128,
) -> Result<()> {
    if amount < 0 {
        return Err(Refusal::Cash);
    }
    let entry = map.entry(key).or_insert((debit, credit, 0));
    if (entry.0, entry.1) != (debit, credit) {
        return Err(Refusal::Cash);
    }
    super::cash(&mut entry.2, amount)
}
fn check_cash(receipts: &MaterialTickReceipts) -> Result<()> {
    let mut expected = Movements::new();
    for row in &receipts.aid {
        let id = row.commitment_id;
        let amount = row.cash_amount.micro_units();
        if row.period == row.dispatch_period
            && matches!(
                row.outcome,
                AidOutcome::Dispatched | AidOutcome::Granted | AidOutcome::Unshipped
            )
        {
            movement(
                &mut expected,
                (1, id.as_bytes()),
                MoneyLocation::Cash(row.payer),
                MoneyLocation::AidReserve(id),
                amount,
            )?;
        }
        match row.outcome {
            AidOutcome::Granted => movement(
                &mut expected,
                (2, id.as_bytes()),
                MoneyLocation::AidReserve(id),
                MoneyLocation::Cash(AccountId::Household(row.recipient)),
                amount,
            )?,
            AidOutcome::Lost | AidOutcome::Unshipped => movement(
                &mut expected,
                (3, id.as_bytes()),
                MoneyLocation::AidReserve(id),
                MoneyLocation::Cash(row.payer),
                amount,
            )?,
            _ => {}
        }
    }
    // A zero-cash in-kind gift need not invent a zero-valued cash transfer.
    expected.retain(|_, row| row.2 != 0);
    let mut actual = Movements::new();
    for row in &receipts.money_transfers {
        let key = match row.purpose {
            MoneyTransferPurpose::AidReservation(id) => (1, id.as_bytes()),
            MoneyTransferPurpose::AidGrant(id) => (2, id.as_bytes()),
            MoneyTransferPurpose::AidRefund(id) => (3, id.as_bytes()),
            _ => continue,
        };
        let amount = row.credit.delta.micro_units();
        if amount <= 0
            || row.debit.delta.micro_units() != amount.checked_neg().ok_or(Refusal::Overflow)?
        {
            return Err(Refusal::Cash);
        }
        movement(
            &mut actual,
            key,
            row.debit.location,
            row.credit.location,
            amount,
        )?;
    }
    if actual != expected {
        return Err(Refusal::Cash);
    }
    Ok(())
}

pub(super) fn remaining(
    gross: &[HouseholdTimeReceipt],
    debits: &[HouseholdContributionReceipt],
    principal: FinalDemandPrincipalId,
    tick: u64,
    unit: [u8; 32],
) -> Result<u64> {
    let time = super::one(
        gross.iter().filter(|r| r.principal_id == principal),
        Refusal::Time,
    )?;
    time.validate().map_err(|_| Refusal::Time)?;
    if time.period != tick || time.labor_unit_id.as_bytes() != unit {
        return Err(Refusal::Time);
    }
    let mut total = 0;
    let mut seen = BTreeSet::new();
    for row in debits
        .iter()
        .filter(|r| r.contribution.principal_id == principal)
    {
        if row.period != tick
            || row.contribution.hours == 0
            || !seen.insert(row.contribution.use_id)
        {
            return Err(Refusal::Time);
        }
        super::add(&mut total, row.contribution.hours)?;
    }
    time.contribution_available_hours
        .checked_sub(total)
        .ok_or(Refusal::Time)
}
pub(super) fn check_time(
    admitted: &CommittedMaterialReceipts,
    row: &AidReceipt,
    terms: &Terms<'_>,
    after: &OrganizerSnapshot,
) -> Result<u64> {
    let unit = terms.mandate.labor_unit_id.as_bytes();
    let debits = &admitted.household_contributions;
    let matches = debits
        .iter()
        .filter(|d| d.contribution.use_id == row.commitment_id.as_bytes());
    if row.contribution_hours > 0 {
        let debit = super::one(matches, Refusal::Time)?;
        if debit.period != row.period
            || debit.contribution.principal_id != row.donor
            || debit.contribution.actor_id != terms.mandate.donor_actor
            || debit.contribution.contributor_id != terms.mandate.donor_contributor_id
            || debit.contribution.hours != row.contribution_hours
        {
            return Err(Refusal::Time);
        }
    } else if row.dispatch_period < row.period && matches.count() != 0 {
        return Err(Refusal::Time);
    }
    let remaining = remaining(
        &admitted.receipts.household_time,
        debits,
        row.donor,
        row.period,
        unit,
    )?;
    for time in after
        .aid
        .iter()
        .filter(|p| p.donor_id == row.donor.as_bytes())
        .filter_map(|p| p.time.as_ref())
    {
        if time.period != row.period
            || time.labor_unit_id != unit
            || time.remaining_hours != remaining
        {
            return Err(Refusal::Time);
        }
    }
    Ok(remaining)
}

#[cfg(test)]
mod controls {
    use super::*;
    use babylon_material_circuit::{HouseholdContributionUse, UnitId};
    fn gross() -> HouseholdTimeReceipt {
        HouseholdTimeReceipt {
            principal_id: FinalDemandPrincipalId::from_bytes([7; 32]),
            period: 3,
            labor_unit_id: UnitId::from_bytes([8; 32]),
            endowment_hours: 13,
            attended_hours: 2,
            protected_hours: 1,
            protected_unresolved_hours: 0,
            unpaid_requested_hours: 0,
            unpaid_allocated_hours: 0,
            unpaid_unresolved_hours: 0,
            contribution_available_hours: 10,
        }
    }
    fn debit(id: u8, actor: u64, contributor: u64, hours: u64) -> HouseholdContributionReceipt {
        HouseholdContributionReceipt {
            period: 3,
            contribution: HouseholdContributionUse {
                use_id: [id; 32],
                principal_id: gross().principal_id,
                actor_id: actor,
                contributor_id: contributor,
                hours,
            },
        }
    }
    #[test]
    fn household_aliases_share_one_finite_time_account() {
        let rows = [debit(1, 42, 70, 4), debit(2, 91, 71, 5)];
        assert_eq!(
            remaining(&[gross()], &rows, gross().principal_id, 3, [8; 32]),
            Ok(1)
        );
        let mut over = rows.to_vec();
        over.push(debit(3, 91, 71, 2));
        assert_eq!(
            remaining(&[gross()], &over, gross().principal_id, 3, [8; 32]),
            Err(Refusal::Time)
        );
        let duplicate = [rows[0].clone(), rows[0].clone()];
        assert_eq!(
            remaining(&[gross()], &duplicate, gross().principal_id, 3, [8; 32]),
            Err(Refusal::Time)
        );
        assert_eq!(
            remaining(&[gross()], &rows, gross().principal_id, 3, [9; 32]),
            Err(Refusal::Time)
        );
    }
}
