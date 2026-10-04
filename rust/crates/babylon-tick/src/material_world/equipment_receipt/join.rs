//! Evidence joins use present physical and monetary rows, never inferred absent state.
use super::{
    Currency, EquipmentWearReceipt, InstallationReceipt, InvestmentReceipt, MaterialWorldError,
};
use babylon_material_circuit::{
    AccountId, IncomeReceipt, MemberLaborUseReceipt, MoneyLocation, MoneyTransferPurpose,
    MoneyTransferReceipt, OutboundOrderId, ProductionReceipt, SiteId,
};
use std::collections::{BTreeMap, BTreeSet};
type Result<T> = std::result::Result<T, MaterialWorldError>;
type Work = BTreeMap<SiteId, (u64, Currency)>;
fn add(rows: &mut Work, site: SiteId, hours: u64, wages: Currency) -> Result<()> {
    let value = rows
        .entry(site)
        .or_insert((0, Currency::from_micro_units(0)));
    value.0 = value.0.checked_add(hours).ok_or(MaterialWorldError::Wire)?;
    value.1 = value
        .1
        .checked_add(wages)
        .map_err(|_| MaterialWorldError::Wire)?;
    Ok(())
}
pub(crate) fn validate_installation(
    rows: &[InstallationReceipt],
    members: &[MemberLaborUseReceipt],
    income: &[IncomeReceipt],
) -> Result<()> {
    let mut installed = Work::new();
    let mut attended = Work::new();
    for row in rows {
        add(
            &mut installed,
            row.site_id,
            row.used_hours,
            row.wages_capitalized,
        )?;
    }
    for row in members {
        add(
            &mut attended,
            row.site_id,
            row.installation_hours,
            row.installation_wages,
        )?;
    }
    installed.retain(|_, r| r.0 != 0 || r.1.micro_units() != 0);
    attended.retain(|_, r| r.0 != 0 || r.1.micro_units() != 0);
    if installed != attended {
        return Err(MaterialWorldError::Wire);
    }
    for row in income {
        let actual = if let AccountId::Site(site) = row.account {
            installed
                .get(&site)
                .map_or(Currency::from_micro_units(0), |r| r.1)
        } else {
            Currency::from_micro_units(0)
        };
        if row.statement.installation_labor_capitalized != actual {
            return Err(MaterialWorldError::Wire);
        }
    }
    Ok(())
}
pub(crate) fn validate_wear(
    rows: &[EquipmentWearReceipt],
    production: &[ProductionReceipt],
    income: &[IncomeReceipt],
) -> Result<()> {
    let mut used = BTreeMap::new();
    let mut cost = Work::new();
    let production: BTreeMap<_, _> = production
        .iter()
        .map(|r| ((r.site_id, r.process_id), r.produced_batches))
        .collect();
    for row in rows {
        let n = used.entry((row.site_id, row.process_id)).or_insert(0_u64);
        *n = n
            .checked_add(row.used_batches)
            .ok_or(MaterialWorldError::Wire)?;
        add(&mut cost, row.site_id, 0, row.carried_to_output)?;
    }
    if used.iter().any(|(k, v)| production.get(k) != Some(v)) {
        return Err(MaterialWorldError::Wire);
    }
    for row in income {
        let actual = if let AccountId::Site(site) = row.account {
            cost.get(&site)
                .map_or(Currency::from_micro_units(0), |r| r.1)
        } else {
            Currency::from_micro_units(0)
        };
        if row.statement.equipment_wear_capitalized != actual {
            return Err(MaterialWorldError::Wire);
        }
    }
    Ok(())
}
pub(crate) fn validate_investment(
    rows: &[InvestmentReceipt],
    money: &[MoneyTransferReceipt],
) -> Result<()> {
    let principals: BTreeSet<_> = rows.iter().map(|r| r.order_id).collect();
    let mut reservations = BTreeMap::new();
    for m in money {
        if let MoneyTransferPurpose::PurchaseReservation(OutboundOrderId::Delivery(id)) = m.purpose
        {
            if principals.contains(&id) && reservations.insert(id, m).is_some() {
                return Err(MaterialWorldError::Wire);
            }
        }
    }
    for r in rows {
        let amount = r
            .unit_price
            .micro_units()
            .checked_mul(i128::from(r.admitted_units))
            .ok_or(MaterialWorldError::Wire)?;
        if amount == 0 {
            if reservations.contains_key(&r.order_id) {
                return Err(MaterialWorldError::Wire);
            }
            continue;
        }
        let m = reservations
            .get(&r.order_id)
            .ok_or(MaterialWorldError::Wire)?;
        if m.debit.location != MoneyLocation::Cash(AccountId::Site(r.site_id))
            || m.credit.location
                != MoneyLocation::PurchaseReserve(OutboundOrderId::Delivery(r.order_id))
            || m.debit.delta.micro_units() != -amount
            || m.credit.delta.micro_units() != amount
        {
            return Err(MaterialWorldError::Wire);
        }
    }
    Ok(())
}
