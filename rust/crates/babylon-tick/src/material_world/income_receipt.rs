//! Historical-cost income equations; state-backed asset reconciliation stays in the engine.
use super::monetary_receipt::{account, account_parts};
use super::{MaterialWorldError, ReceiptCursor};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{IncomeReceipt, IncomeStatement};

pub(super) const ROW_BYTES: usize = 505;

pub(super) fn validate_order(rows: &[IncomeReceipt]) -> Result<(), MaterialWorldError> {
    if rows
        .windows(2)
        .any(|pair| pair[0].account >= pair[1].account)
    {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

pub(super) fn encode(
    rows: &[IncomeReceipt],
    tick: u64,
    bytes: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    for row in rows {
        encode_row(row, tick, bytes)?;
    }
    Ok(())
}

fn encode_row(
    row: &IncomeReceipt,
    tick: u64,
    bytes: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    row.validate().map_err(|_| MaterialWorldError::Wire)?;
    if row.period != tick {
        return Err(MaterialWorldError::Wire);
    }
    let (tag, id) = account_parts(row.account);
    bytes.push(tag);
    bytes.extend_from_slice(&id);
    bytes.extend_from_slice(&row.period.to_be_bytes());
    let s = &row.statement;
    for value in [
        row.opening_capital,
        row.opening_retained_earnings,
        row.opening_contributed_capital,
        row.contributions_received,
        row.closing_contributed_capital,
        row.distributions_paid,
        s.sales,
        s.wage_income,
        s.cost_of_goods_sold,
        s.productive_labor_capitalized,
        s.installation_labor_capitalized,
        s.equipment_wear_capitalized,
        s.idle_labor_expense,
        s.handling_expense,
        s.maintenance_labor_expense,
        s.maintenance_material_expense,
        s.freight_loss_expense,
        s.consumption_expense,
        s.final_demand_outlay,
        s.unused_service_expense,
        s.tax_income,
        s.tax_expense,
        s.public_transfer_income,
        s.public_transfer_expense,
        s.distribution_income,
        s.gift_income,
        s.gift_expense,
        row.net_income,
        row.closing_retained_earnings,
    ] {
        bytes.extend_from_slice(&value.micro_units().to_be_bytes());
    }
    Ok(())
}

fn money(cursor: &mut ReceiptCursor<'_>) -> Result<Currency, MaterialWorldError> {
    Ok(Currency::from_micro_units(i128::from_be_bytes(
        cursor.take()?,
    )))
}

pub(super) fn decode(
    cursor: &mut ReceiptCursor<'_>,
    tick: u64,
) -> Result<IncomeReceipt, MaterialWorldError> {
    let [tag] = cursor.take()?;
    let id = account(tag, cursor.take()?)?;
    let row = IncomeReceipt {
        account: id,
        period: cursor.u64()?,
        opening_capital: money(cursor)?,
        opening_retained_earnings: money(cursor)?,
        opening_contributed_capital: money(cursor)?,
        contributions_received: money(cursor)?,
        closing_contributed_capital: money(cursor)?,
        distributions_paid: money(cursor)?,
        statement: IncomeStatement {
            sales: money(cursor)?,
            wage_income: money(cursor)?,
            cost_of_goods_sold: money(cursor)?,
            productive_labor_capitalized: money(cursor)?,
            installation_labor_capitalized: money(cursor)?,
            equipment_wear_capitalized: money(cursor)?,
            idle_labor_expense: money(cursor)?,
            handling_expense: money(cursor)?,
            maintenance_labor_expense: money(cursor)?,
            maintenance_material_expense: money(cursor)?,
            freight_loss_expense: money(cursor)?,
            consumption_expense: money(cursor)?,
            final_demand_outlay: money(cursor)?,
            unused_service_expense: money(cursor)?,
            tax_income: money(cursor)?,
            tax_expense: money(cursor)?,
            public_transfer_income: money(cursor)?,
            public_transfer_expense: money(cursor)?,
            distribution_income: money(cursor)?,
            gift_income: money(cursor)?,
            gift_expense: money(cursor)?,
        },
        net_income: money(cursor)?,
        closing_retained_earnings: money(cursor)?,
    };
    row.validate().map_err(|_| MaterialWorldError::Wire)?;
    if row.period != tick {
        return Err(MaterialWorldError::Wire);
    }
    Ok(row)
}
