//! Current fixed-width actual collection evidence; no reconstructed account delta.
use super::{MaterialWorldError, ReceiptCursor};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, AidOutcome, AidReceipt, CashTransferPurpose, CircuitAccounting, CollectionOutcome,
    CollectionReceipt, FinalDemandPrincipalId, HouseholdTimeAccounting, HouseholdTimeReceipt,
    IncomeReceipt, MaterialCircuitState, MoneyLocation, MoneyTransferPurpose, MoneyTransferReceipt,
    OrganizationAccountId, UnitId,
};
use std::collections::BTreeMap;
pub(super) const ROW_BYTES: usize = 317;
type Result<T> = std::result::Result<T, MaterialWorldError>;
pub(super) fn encode(rows: &[CollectionReceipt], period: u64, bytes: &mut Vec<u8>) -> Result<()> {
    for row in rows {
        row.validate()?;
        if row.period != period {
            return Err(MaterialWorldError::Wire);
        }
        for value in [row.period, row.admitted_period] {
            bytes.extend_from_slice(&value.to_be_bytes());
        }
        bytes.extend_from_slice(&row.original_commitment_id);
        bytes.extend_from_slice(&row.command_nonce);
        bytes.extend_from_slice(&row.mandate_id);
        bytes.extend_from_slice(&row.source_hash);
        for value in [row.actor_id, row.contributor_id] {
            bytes.extend_from_slice(&value.to_be_bytes());
        }
        for value in [
            row.donor.as_bytes(),
            row.recipient.as_bytes(),
            row.labor_unit_id.as_bytes(),
        ] {
            bytes.extend_from_slice(&value);
        }
        for value in [row.requested, row.collected] {
            bytes.extend_from_slice(&value.micro_units().to_be_bytes());
        }
        bytes.extend_from_slice(&row.performed_hours.to_be_bytes());
        bytes.push(row.outcome as u8);
        bytes.extend_from_slice(&row.transfer_ordinal.unwrap_or(u32::MAX).to_be_bytes());
        bytes.extend_from_slice(&row.contribution_use_id);
    }
    Ok(())
}
pub(super) fn decode(cursor: &mut ReceiptCursor<'_>, period: u64) -> Result<CollectionReceipt> {
    let row = CollectionReceipt {
        period: cursor.u64()?,
        admitted_period: cursor.u64()?,
        original_commitment_id: cursor.take()?,
        command_nonce: cursor.take()?,
        mandate_id: cursor.take()?,
        source_hash: cursor.take()?,
        actor_id: cursor.u64()?,
        contributor_id: cursor.u64()?,
        donor: FinalDemandPrincipalId::from_bytes(cursor.take()?),
        recipient: OrganizationAccountId::from_bytes(cursor.take()?),
        labor_unit_id: UnitId::from_bytes(cursor.take()?),
        requested: Currency::from_micro_units(i128::from_be_bytes(cursor.take()?)),
        collected: Currency::from_micro_units(i128::from_be_bytes(cursor.take()?)),
        performed_hours: cursor.u64()?,
        outcome: CollectionOutcome::try_from(cursor.take::<1>()?[0])?,
        transfer_ordinal: match u32::from_be_bytes(cursor.take()?) {
            u32::MAX => None,
            index => Some(index),
        },
        contribution_use_id: cursor.take()?,
    };
    row.validate()?;
    if row.period != period {
        return Err(MaterialWorldError::Wire);
    }
    Ok(row)
}
pub(super) fn validate(
    rows: &[CollectionReceipt],
    money: &[MoneyTransferReceipt],
    time: &[HouseholdTimeReceipt],
    income: &[IncomeReceipt],
    aid: &[AidReceipt],
    period: u64,
) -> Result<()> {
    if rows.len() > 1 {
        return Err(MaterialWorldError::ByteLimit);
    }
    if rows.is_empty() {
        return Ok(());
    }
    for row in rows {
        row.validate()?;
        if row.period != period {
            return Err(MaterialWorldError::Wire);
        }
        let mut times = time.iter().filter(|time| time.principal_id == row.donor);
        let actual = times.next().ok_or(MaterialWorldError::Wire)?;
        if times.next().is_some()
            || actual.period != period
            || actual.labor_unit_id != row.labor_unit_id
            || actual.contribution_available_hours < row.performed_hours
        {
            return Err(MaterialWorldError::Wire);
        }
        if let Some(index) = row.transfer_ordinal {
            let movement = money
                .get(usize::try_from(index).map_err(|_| MaterialWorldError::ByteLimit)?)
                .ok_or(MaterialWorldError::Wire)?;
            let debit = row
                .collected
                .micro_units()
                .checked_neg()
                .ok_or(MaterialWorldError::Arithmetic)?;
            if movement.purpose != MoneyTransferPurpose::Cash(CashTransferPurpose::MutualAid)
                || movement.debit.location != MoneyLocation::Cash(AccountId::Household(row.donor))
                || movement.credit.location
                    != MoneyLocation::Cash(AccountId::Organization(row.recipient))
                || movement.debit.delta.micro_units() != debit
                || movement.credit.delta != row.collected
            {
                return Err(MaterialWorldError::Wire);
            }
        }
    }
    // Full gift statement joins, including independent actual aid grants.
    let mut expected = BTreeMap::<AccountId, (i128, i128)>::new();
    for movement in money
        .iter()
        .filter(|row| row.purpose == MoneyTransferPurpose::Cash(CashTransferPurpose::MutualAid))
    {
        let (MoneyLocation::Cash(sender), MoneyLocation::Cash(recipient)) =
            (movement.debit.location, movement.credit.location)
        else {
            return Err(MaterialWorldError::Wire);
        };
        add(
            &mut expected,
            sender,
            0,
            movement.credit.delta.micro_units(),
        )?;
        add(
            &mut expected,
            recipient,
            movement.credit.delta.micro_units(),
            0,
        )?;
    }
    for gift in aid.iter().filter(|row| row.outcome == AidOutcome::Granted) {
        add(
            &mut expected,
            AccountId::Household(gift.donor),
            0,
            gift.carrying_amount.micro_units(),
        )?;
        add(&mut expected, gift.payer, 0, gift.cash_amount.micro_units())?;
        add(
            &mut expected,
            AccountId::Household(gift.recipient),
            gift.carrying_amount
                .micro_units()
                .checked_add(gift.cash_amount.micro_units())
                .ok_or(MaterialWorldError::Arithmetic)?,
            0,
        )?;
    }
    for row in income {
        let (received, spent) = expected.remove(&row.account).unwrap_or_default();
        if row.statement.gift_income.micro_units() != received
            || row.statement.gift_expense.micro_units() != spent
        {
            return Err(MaterialWorldError::Wire);
        }
    }
    if !expected.is_empty() {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}
fn add(
    rows: &mut BTreeMap<AccountId, (i128, i128)>,
    account: AccountId,
    received: i128,
    spent: i128,
) -> Result<()> {
    if received < 0 || spent < 0 {
        return Err(MaterialWorldError::Wire);
    }
    if received == 0 && spent == 0 {
        return Ok(());
    }
    let value = rows.entry(account).or_default();
    value.0 = value
        .0
        .checked_add(received)
        .ok_or(MaterialWorldError::Arithmetic)?;
    value.1 = value
        .1
        .checked_add(spent)
        .ok_or(MaterialWorldError::Arithmetic)?;
    Ok(())
}
pub(super) fn validate_state(
    rows: &[CollectionReceipt],
    state: &MaterialCircuitState,
) -> Result<()> {
    if rows.is_empty() {
        return Ok(());
    }
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Err(MaterialWorldError::Wire);
    };
    let HouseholdTimeAccounting::Modeled(book) = &e.household_time else {
        return Err(MaterialWorldError::Wire);
    };
    for row in rows {
        row.validate()?;
        if let Some(usage) = row.contribution_use() {
            if book
                .contributions
                .iter()
                .filter(|actual| actual.period == row.period && actual.contribution == usage)
                .count()
                != 1
            {
                return Err(MaterialWorldError::Wire);
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_kernel::content_digest::sha256_of;

    fn hex_bytes(hex: &str) -> Vec<u8> {
        assert_eq!(hex.len() % 2, 0);
        hex.as_bytes()
            .chunks_exact(2)
            .map(|pair| u8::from_str_radix(std::str::from_utf8(pair).unwrap(), 16).unwrap())
            .collect()
    }

    #[test]
    fn retained_pre_cutover_full_and_refusal_rows_reencode_identical_bytes_and_hashes() {
        // Actual material close rows retained on 2026-10-05 before the partial
        // collection cutover. Organizer capture epochs are checked separately.
        for (outcome, hex, hash) in [
            (CollectionOutcome::Collected, "00000000000000010000000000000000681a2c027bbe814e01b17fa13612eb8a5835b099f4a8d7e8c3b3960984524cd1070707070707070707070707070707075d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e000000000000006500000000000000c9010101010101010101010101010101010101010101010101010101010101010160606060606060606060606060606060606060606060606060606060606060600202020202020202020202020202020202020202020202020202020202020202000000000000000000000000000000020000000000000000000000000000000200000000000000020100000006055767ce140947603c8546cbcc13229b359077078c2afee7177209a242683d3c", "7bd8f3376a5b48a7c69f43fb4a9a25ceb1ef20dd3dd0d21f8f8b89c6f2c585aa"),
            (CollectionOutcome::ProtectedClosingStockUnmet, "00000000000000010000000000000000681a2c027bbe814e01b17fa13612eb8a5835b099f4a8d7e8c3b3960984524cd1070707070707070707070707070707075d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e000000000000006500000000000000c90101010101010101010101010101010101010101010101010101010101010101606060606060606060606060606060606060606060606060606060606060606002020202020202020202020202020202020202020202020202020202020202020000000000000000000000000000000200000000000000000000000000000000000000000000000005ffffffff0000000000000000000000000000000000000000000000000000000000000000", "7ad0ba54644411bc61b010a40f9dc11d11eaab9336557d0b193e87cdff014bab"),
        ] {
            let bytes = hex_bytes(hex);
            assert_eq!(bytes.len(), ROW_BYTES);
            let expected_hash: [u8; 32] = hex_bytes(hash).try_into().unwrap();
            assert_eq!(sha256_of(&bytes), expected_hash);
            let mut cursor = ReceiptCursor { bytes: &bytes, position: 0 };
            let row = decode(&mut cursor, 1).unwrap();
            assert_eq!(cursor.position, ROW_BYTES);
            assert_eq!(row.outcome, outcome);
            let mut encoded = Vec::new();
            encode(std::slice::from_ref(&row), 1, &mut encoded).unwrap();
            assert_eq!(encoded, bytes);
            assert_eq!(sha256_of(&encoded), expected_hash);
            let mut unknown = bytes.clone();
            unknown[280] = 10;
            assert!(decode(&mut ReceiptCursor { bytes: &unknown, position: 0 }, 1).is_err());
        }
    }
}
