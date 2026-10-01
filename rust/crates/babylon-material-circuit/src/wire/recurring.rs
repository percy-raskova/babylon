//! Exact captured needs, stocks and decision policies; no default on old bytes.
use super::{append_rows, decode_rows, Cursor};
use crate::{
    AttendancePlan, FinalDemandPrincipalId, GoodId, HouseholdCohort, HouseholdNeed,
    HouseholdPurchasePolicy, HouseholdStock, MaterialCircuitError, PricePolicy, ProcessId,
    ProductionDemandPolicy, RecurringEconomy, ReplenishmentPolicy, SellerOffer, SiteId, UnitId,
};
use babylon_kernel::currency::Currency;

pub(super) fn append(
    output: &mut Vec<u8>,
    recurring: Option<&RecurringEconomy>,
) -> Result<(), MaterialCircuitError> {
    let Some(rows) = recurring else {
        output.push(0);
        return Ok(());
    };
    output.push(1);
    output.extend_from_slice(&rows.last_household_admission_period.to_be_bytes());
    output.extend_from_slice(&rows.last_household_consumption_period.to_be_bytes());
    append_rows(output, &rows.households, |bytes, row| {
        bytes.extend_from_slice(&row.principal_id.as_bytes());
        bytes.extend_from_slice(&row.households.to_be_bytes());
        bytes.extend_from_slice(&row.persons.to_be_bytes());
    })?;
    append_rows(output, &rows.household_stocks, |bytes, row| {
        bytes.extend_from_slice(&row.principal_id.as_bytes());
        bytes.extend_from_slice(&row.good_id.as_bytes());
        bytes.extend_from_slice(&row.unit_id.as_bytes());
        bytes.extend_from_slice(&row.quantity.to_be_bytes());
    })?;
    append_rows(output, &rows.household_needs, |bytes, row| {
        bytes.extend_from_slice(&row.principal_id.as_bytes());
        bytes.extend_from_slice(&row.good_id.as_bytes());
        bytes.extend_from_slice(&row.unit_id.as_bytes());
        bytes.extend_from_slice(&row.units_per_person.to_be_bytes());
    })?;
    append_rows(output, &rows.household_purchases, |bytes, row| {
        bytes.extend_from_slice(&row.principal_id.as_bytes());
        bytes.extend_from_slice(&row.retailer_site_id.as_bytes());
        bytes.extend_from_slice(&row.good_id.as_bytes());
        bytes.extend_from_slice(&row.unit_id.as_bytes());
        bytes.extend_from_slice(&row.target_closing_stock.to_be_bytes());
        bytes.extend_from_slice(&row.maximum_purchase.to_be_bytes());
        bytes.push(u8::from(row.enabled));
    })?;
    append_rows(output, &rows.offers, |bytes, row| {
        bytes.extend_from_slice(&row.site_id.as_bytes());
        bytes.extend_from_slice(&row.good_id.as_bytes());
        bytes.extend_from_slice(&row.unit_id.as_bytes());
        bytes.extend_from_slice(&row.unit_price.micro_units().to_be_bytes());
        match row.pricing {
            PricePolicy::Fixed => bytes.push(1),
            PricePolicy::Responsive {
                minimum,
                maximum,
                step,
                target_stock,
            } => {
                bytes.push(2);
                for amount in [minimum, maximum, step] {
                    bytes.extend_from_slice(&amount.micro_units().to_be_bytes());
                }
                bytes.extend_from_slice(&target_stock.to_be_bytes());
            }
        }
    })?;
    append_rows(output, &rows.replenishment, |bytes, row| {
        bytes.extend_from_slice(&row.buyer_site_id.as_bytes());
        bytes.extend_from_slice(&row.supplier_site_id.as_bytes());
        bytes.extend_from_slice(&row.good_id.as_bytes());
        bytes.extend_from_slice(&row.unit_id.as_bytes());
        bytes.extend_from_slice(&row.target_stock.to_be_bytes());
        bytes.extend_from_slice(&row.maximum_purchase.to_be_bytes());
        bytes.extend_from_slice(&row.cash_floor.micro_units().to_be_bytes());
    })?;
    append_rows(output, &rows.production, |bytes, row| {
        bytes.extend_from_slice(&row.process_id.as_bytes());
        bytes.extend_from_slice(&row.site_id.as_bytes());
        bytes.extend_from_slice(&row.output_buffer.to_be_bytes());
        bytes.extend_from_slice(&row.planned_batches.to_be_bytes());
    })?;
    append_rows(output, &rows.attendance, |bytes, row| {
        bytes.extend_from_slice(&row.site_id.as_bytes());
        bytes.extend_from_slice(&row.unit_id.as_bytes());
        bytes.extend_from_slice(&row.period.to_be_bytes());
        bytes.extend_from_slice(&row.planned_hours.to_be_bytes());
    })?;
    Ok(())
}

fn currency(bytes: &mut Cursor<'_>) -> Result<Currency, MaterialCircuitError> {
    Ok(Currency::from_micro_units(i128::from_be_bytes(
        bytes.array()?,
    )))
}

fn pricing(bytes: &mut Cursor<'_>) -> Result<PricePolicy, MaterialCircuitError> {
    match bytes.u8()? {
        1 => Ok(PricePolicy::Fixed),
        2 => Ok(PricePolicy::Responsive {
            minimum: currency(bytes)?,
            maximum: currency(bytes)?,
            step: currency(bytes)?,
            target_stock: bytes.u64()?,
        }),
        _ => Err(MaterialCircuitError::WireEnum),
    }
}

pub(super) fn decode(
    cursor: &mut Cursor<'_>,
) -> Result<Option<Box<RecurringEconomy>>, MaterialCircuitError> {
    match cursor.u8()? {
        0 => return Ok(None),
        1 => {}
        _ => return Err(MaterialCircuitError::WireEnum),
    }
    Ok(Some(Box::new(RecurringEconomy {
        last_household_admission_period: cursor.u64()?,
        last_household_consumption_period: cursor.u64()?,
        households: decode_rows(cursor, |bytes| {
            Ok(HouseholdCohort {
                principal_id: FinalDemandPrincipalId::from_bytes(bytes.array()?),
                households: bytes.u64()?,
                persons: bytes.u64()?,
            })
        })?,
        household_stocks: decode_rows(cursor, |bytes| {
            Ok(HouseholdStock {
                principal_id: FinalDemandPrincipalId::from_bytes(bytes.array()?),
                good_id: GoodId::from_bytes(bytes.array()?),
                unit_id: UnitId::from_bytes(bytes.array()?),
                quantity: bytes.u64()?,
            })
        })?,
        household_needs: decode_rows(cursor, |bytes| {
            Ok(HouseholdNeed {
                principal_id: FinalDemandPrincipalId::from_bytes(bytes.array()?),
                good_id: GoodId::from_bytes(bytes.array()?),
                unit_id: UnitId::from_bytes(bytes.array()?),
                units_per_person: bytes.u64()?,
            })
        })?,
        household_purchases: decode_rows(cursor, |bytes| {
            Ok(HouseholdPurchasePolicy {
                principal_id: FinalDemandPrincipalId::from_bytes(bytes.array()?),
                retailer_site_id: SiteId::from_bytes(bytes.array()?),
                good_id: GoodId::from_bytes(bytes.array()?),
                unit_id: UnitId::from_bytes(bytes.array()?),
                target_closing_stock: bytes.u64()?,
                maximum_purchase: bytes.u64()?,
                enabled: match bytes.u8()? {
                    0 => false,
                    1 => true,
                    _ => return Err(MaterialCircuitError::WireEnum),
                },
            })
        })?,
        offers: decode_rows(cursor, |bytes| {
            Ok(SellerOffer {
                site_id: SiteId::from_bytes(bytes.array()?),
                good_id: GoodId::from_bytes(bytes.array()?),
                unit_id: UnitId::from_bytes(bytes.array()?),
                unit_price: currency(bytes)?,
                pricing: pricing(bytes)?,
            })
        })?,
        replenishment: decode_rows(cursor, |bytes| {
            Ok(ReplenishmentPolicy {
                buyer_site_id: SiteId::from_bytes(bytes.array()?),
                supplier_site_id: SiteId::from_bytes(bytes.array()?),
                good_id: GoodId::from_bytes(bytes.array()?),
                unit_id: UnitId::from_bytes(bytes.array()?),
                target_stock: bytes.u64()?,
                maximum_purchase: bytes.u64()?,
                cash_floor: currency(bytes)?,
            })
        })?,
        production: decode_rows(cursor, |bytes| {
            Ok(ProductionDemandPolicy {
                process_id: ProcessId::from_bytes(bytes.array()?),
                site_id: SiteId::from_bytes(bytes.array()?),
                output_buffer: bytes.u64()?,
                planned_batches: bytes.u64()?,
            })
        })?,
        attendance: decode_rows(cursor, |bytes| {
            Ok(AttendancePlan {
                site_id: SiteId::from_bytes(bytes.array()?),
                unit_id: UnitId::from_bytes(bytes.array()?),
                period: bytes.u64()?,
                planned_hours: bytes.u64()?,
            })
        })?,
    })))
}
