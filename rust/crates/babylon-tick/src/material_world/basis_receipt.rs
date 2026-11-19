//! Fixed-width native valuation movements. List order preserves the native close schedule.
use super::{monetary_receipt, MaterialWorldError, ReceiptCursor};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    CompanyBasisAsset, CompanyBasisMovement, CompanySale, EquipmentCohortId, FreightLotId, GoodId,
    InstallationId, OrderId, OutboundOrderId, ProcessId, SiteId, UnitId,
};
use babylon_material_circuit::{IncomeReceipt, MoneyTransferReceipt};
use std::result::Result as StdResult;
type Result<T> = StdResult<T, MaterialWorldError>;
const ASSET_BYTES: usize = 97;
const SALE_BYTES: usize = 82;
pub(super) const WIDTH: usize = 2 * ASSET_BYTES + SALE_BYTES + 32;

fn order_parts(order: OutboundOrderId) -> (u8, OrderId) {
    match order {
        OutboundOrderId::Delivery(id) => (1, id),
        OutboundOrderId::LocalFinalDemand(id) => (2, id),
        OutboundOrderId::Service(id) => (3, id),
    }
}
fn order(tag: u8, id: [u8; 32]) -> Result<OutboundOrderId> {
    let id = OrderId::from_bytes(id);
    match tag {
        1 => Ok(OutboundOrderId::Delivery(id)),
        2 => Ok(OutboundOrderId::LocalFinalDemand(id)),
        3 => Ok(OutboundOrderId::Service(id)),
        _ => Err(MaterialWorldError::Wire),
    }
}
fn write_asset(node: Option<CompanyBasisAsset>, bytes: &mut Vec<u8>) {
    let Some(node) = node else {
        bytes.extend_from_slice(&[0; ASSET_BYTES]);
        return;
    };
    let (tag, id, unit) = match node {
        CompanyBasisAsset::Stock(_, g, u) => (1, g.as_bytes(), u.as_bytes()),
        CompanyBasisAsset::Freight(_, id) => (2, id.as_bytes(), [0; 32]),
        CompanyBasisAsset::Process(_, id) => (3, id.as_bytes(), [0; 32]),
        CompanyBasisAsset::Installation(_, id) => (4, id.as_bytes(), [0; 32]),
        CompanyBasisAsset::Equipment(_, id) => (5, id.as_bytes(), [0; 32]),
        CompanyBasisAsset::Handoff(_, o) => {
            let (tag, id) = order_parts(o);
            (5 + tag, id.as_bytes(), [0; 32])
        }
    };
    bytes.push(tag);
    bytes.extend_from_slice(&node.site().as_bytes());
    bytes.extend_from_slice(&id);
    bytes.extend_from_slice(&unit);
}
fn read_asset(c: &mut ReceiptCursor<'_>) -> Result<Option<CompanyBasisAsset>> {
    let [tag] = c.take()?;
    let site = c.take()?;
    let id = c.take()?;
    let unit = c.take()?;
    if tag != 1 && unit != [0; 32] {
        return Err(MaterialWorldError::Wire);
    }
    if tag == 0 && site == [0; 32] && id == [0; 32] {
        return Ok(None);
    }
    let s = SiteId::from_bytes(site);
    Ok(Some(match tag {
        1 => CompanyBasisAsset::Stock(s, GoodId::from_bytes(id), UnitId::from_bytes(unit)),
        2 => CompanyBasisAsset::Freight(s, FreightLotId::from_bytes(id)),
        3 => CompanyBasisAsset::Process(s, ProcessId::from_bytes(id)),
        4 => CompanyBasisAsset::Installation(s, InstallationId::from_bytes(id)),
        5 => CompanyBasisAsset::Equipment(s, EquipmentCohortId::from_bytes(id)),
        6..=8 => CompanyBasisAsset::Handoff(s, order(tag - 5, id)?),
        _ => return Err(MaterialWorldError::Wire),
    }))
}
pub(super) fn encode(rows: &[CompanyBasisMovement], out: &mut Vec<u8>) -> Result<()> {
    for row in rows {
        row.released(row.opening)
            .map_err(|_| MaterialWorldError::Wire)?;
        write_asset(Some(row.source), out);
        write_asset(row.destination, out);
        if let Some(sale) = row.sale {
            let (tag, id) = order_parts(sale.order);
            out.push(tag);
            out.extend_from_slice(&id.as_bytes());
            let (tag, buyer) = monetary_receipt::account_parts(sale.buyer);
            out.push(tag);
            out.extend_from_slice(&buyer);
            out.extend_from_slice(&sale.proceeds.micro_units().to_be_bytes());
        } else {
            out.extend_from_slice(&[0; SALE_BYTES]);
        }
        out.extend_from_slice(&row.opening.micro_units().to_be_bytes());
        out.extend_from_slice(&row.available.to_be_bytes());
        out.extend_from_slice(&row.quantity.to_be_bytes());
    }
    Ok(())
}
pub(super) fn decode(c: &mut ReceiptCursor<'_>) -> Result<CompanyBasisMovement> {
    let source = read_asset(c)?.ok_or(MaterialWorldError::Wire)?;
    let destination = read_asset(c)?;
    let [tag] = c.take()?;
    let id = c.take()?;
    let [account] = c.take()?;
    let buyer = c.take()?;
    let proceeds = Currency::from_micro_units(i128::from_be_bytes(c.take()?));
    let sale = if tag == 0
        && id == [0; 32]
        && account == 0
        && buyer == [0; 32]
        && proceeds.micro_units() == 0
    {
        None
    } else {
        Some(CompanySale {
            order: order(tag, id)?,
            buyer: monetary_receipt::account(account, buyer)?,
            proceeds,
        })
    };
    let row = CompanyBasisMovement {
        source,
        destination,
        sale,
        opening: Currency::from_micro_units(i128::from_be_bytes(c.take()?)),
        available: c.u64()?,
        quantity: c.u64()?,
    };
    row.released(row.opening)
        .map_err(|_| MaterialWorldError::Wire)?;
    Ok(row)
}

/// Each sale joins the exact order settlement, legal seller and native historical COGS.
pub(super) fn validate(
    rows: &[CompanyBasisMovement],
    income: &[IncomeReceipt],
    transfers: &[MoneyTransferReceipt],
) -> Result<()> {
    use babylon_material_circuit::{AccountId, MoneyLocation, MoneyTransferPurpose};
    use std::collections::BTreeMap;
    let mut proceeds = BTreeMap::<(OutboundOrderId, SiteId), i128>::new();
    let mut profits = BTreeMap::<SiteId, (i128, i128)>::new();
    for row in rows {
        if let Some(s) = row.sale {
            let site = row.source.site();
            let amount = s.proceeds.micro_units();
            let cost = row
                .released(row.opening)
                .map_err(|_| MaterialWorldError::Wire)?
                .micro_units();
            let entry = proceeds.entry((s.order, site)).or_default();
            *entry = entry
                .checked_add(amount)
                .ok_or(MaterialWorldError::Arithmetic)?;
            let pair = profits.entry(site).or_default();
            pair.0 = pair
                .0
                .checked_add(amount)
                .ok_or(MaterialWorldError::Arithmetic)?;
            pair.1 = pair
                .1
                .checked_add(cost)
                .ok_or(MaterialWorldError::Arithmetic)?;
        }
    }
    for t in transfers {
        if let MoneyTransferPurpose::DeliverySettlement(id) = t.purpose {
            let MoneyLocation::Cash(AccountId::Site(site)) = t.credit.location else {
                return Err(MaterialWorldError::Wire);
            };
            let total = proceeds
                .get_mut(&(id, site))
                .ok_or(MaterialWorldError::Wire)?;
            if t.credit.delta.micro_units() <= 0
                || t.debit.location != MoneyLocation::PurchaseReserve(id)
                || t.debit
                    .delta
                    .checked_add(t.credit.delta)
                    .map_err(|_| MaterialWorldError::Arithmetic)?
                    .micro_units()
                    != 0
            {
                return Err(MaterialWorldError::Wire);
            }
            *total = total
                .checked_sub(t.credit.delta.micro_units())
                .ok_or(MaterialWorldError::Arithmetic)?;
        }
    }
    for r in income {
        if let AccountId::Site(site) = r.account {
            if profits.remove(&site).unwrap_or_default()
                != (
                    r.statement.sales.micro_units(),
                    r.statement.cost_of_goods_sold.micro_units(),
                )
            {
                return Err(MaterialWorldError::Wire);
            }
        }
    }
    if !profits.is_empty() || proceeds.values().any(|&remaining| remaining != 0) {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}
