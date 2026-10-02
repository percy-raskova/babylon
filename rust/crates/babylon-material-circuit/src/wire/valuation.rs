//! Exact current historical-cost book, with no implicit missing-value convention.
use super::accounting::{append_account, decode_account, decode_currency, ordered_rows};
use super::{append_rows, decode_rows, Cursor};
use crate::{
    CapitalAccount, EquityCarryingValue, FreightCarryingValue, FreightLotId, GoodId,
    HistoricalCostBook, HistoricalCostSnapshot, MaterialCircuitError, SiteId, StockCarryingValue,
    UnitId, MAX_CARRYING_STOCKS,
};

pub(super) fn append(
    out: &mut Vec<u8>,
    book: &HistoricalCostBook,
) -> Result<(), MaterialCircuitError> {
    let rows = book.snapshot();
    append_rows(out, &rows.accounts, |b, r| {
        append_account(b, r.account);
        b.extend_from_slice(&r.opening_capital.micro_units().to_be_bytes());
        b.extend_from_slice(&r.contributed_capital.micro_units().to_be_bytes());
        b.extend_from_slice(&r.retained_earnings.micro_units().to_be_bytes());
    })?;
    out.extend_from_slice(
        &u32::try_from(rows.stocks.len())
            .map_err(|_| MaterialCircuitError::WireLimit)?
            .to_be_bytes(),
    );
    for r in rows.stocks {
        append_account(out, r.owner);
        out.extend_from_slice(&r.good_id.as_bytes());
        out.extend_from_slice(&r.unit_id.as_bytes());
        out.extend_from_slice(&r.amount.micro_units().to_be_bytes());
    }
    append_rows(out, &rows.freight, |b, r| {
        b.extend_from_slice(&r.lot_id.as_bytes());
        b.extend_from_slice(&r.owner.as_bytes());
        b.extend_from_slice(&r.amount.micro_units().to_be_bytes());
    })?;
    append_rows(out, &rows.equity, |b, r| {
        append_account(b, r.owner);
        b.extend_from_slice(&r.issuer_site_id.as_bytes());
        b.extend_from_slice(&r.amount.micro_units().to_be_bytes());
    })?;
    out.extend_from_slice(
        &u32::try_from(rows.equipment.len())
            .map_err(|_| MaterialCircuitError::WireLimit)?
            .to_be_bytes(),
    );
    for r in rows.equipment {
        match r.asset {
            crate::EquipmentAssetId::Installation(id) => {
                out.push(0);
                out.extend_from_slice(&id.as_bytes());
            }
            crate::EquipmentAssetId::Installed(id) => {
                out.push(1);
                out.extend_from_slice(&id.as_bytes());
            }
        }
        out.extend_from_slice(&r.owner.as_bytes());
        out.extend_from_slice(&r.amount.micro_units().to_be_bytes());
    }
    Ok(())
}

pub(super) fn decode(cursor: &mut Cursor<'_>) -> Result<HistoricalCostBook, MaterialCircuitError> {
    let accounts = decode_rows(cursor, |b| {
        Ok(CapitalAccount {
            account: decode_account(b)?,
            opening_capital: decode_currency(b)?,
            contributed_capital: decode_currency(b)?,
            retained_earnings: decode_currency(b)?,
        })
    })?;
    let count = usize::try_from(cursor.u32()?).map_err(|_| MaterialCircuitError::WireLimit)?;
    if count > MAX_CARRYING_STOCKS {
        return Err(MaterialCircuitError::WireLimit);
    }
    let mut stocks = Vec::with_capacity(count);
    for _ in 0..count {
        stocks.push(StockCarryingValue {
            owner: decode_account(cursor)?,
            good_id: GoodId::from_bytes(cursor.array()?),
            unit_id: UnitId::from_bytes(cursor.array()?),
            amount: decode_currency(cursor)?,
        });
    }
    let freight = decode_rows(cursor, |b| {
        Ok(FreightCarryingValue {
            lot_id: FreightLotId::from_bytes(b.array()?),
            owner: SiteId::from_bytes(b.array()?),
            amount: decode_currency(b)?,
        })
    })?;
    let equity = decode_rows(cursor, |b| {
        Ok(EquityCarryingValue {
            owner: decode_account(b)?,
            issuer_site_id: SiteId::from_bytes(b.array()?),
            amount: decode_currency(b)?,
        })
    })?;
    let count = usize::try_from(cursor.u32()?).map_err(|_| MaterialCircuitError::WireLimit)?;
    if count > 2 * crate::MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(MaterialCircuitError::WireLimit);
    }
    let mut equipment = Vec::with_capacity(count);
    for _ in 0..count {
        let asset = match cursor.u8()? {
            0 => crate::EquipmentAssetId::Installation(crate::InstallationId::from_bytes(
                cursor.array()?,
            )),
            1 => crate::EquipmentAssetId::Installed(crate::EquipmentCohortId::from_bytes(
                cursor.array()?,
            )),
            _ => return Err(MaterialCircuitError::WireEnum),
        };
        equipment.push(crate::EquipmentCarryingValue {
            asset,
            owner: SiteId::from_bytes(cursor.array()?),
            amount: decode_currency(cursor)?,
        });
    }
    ordered_rows(&equipment, |r| r.asset)?;
    ordered_rows(&equity, |r| (r.owner, r.issuer_site_id))?;
    ordered_rows(&accounts, |r| r.account)?;
    ordered_rows(&stocks, |r| (r.owner, r.good_id, r.unit_id))?;
    ordered_rows(&freight, |r| r.lot_id)?;
    HistoricalCostBook::from_snapshot(HistoricalCostSnapshot {
        accounts,
        stocks,
        freight,
        equity,
        equipment,
    })
}
