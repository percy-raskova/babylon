//! Exact captured needs, stocks and decision policies; no default on old bytes.
use super::{append_bounded_rows, append_rows, decode_bounded_rows, decode_rows, Cursor};
use crate::{
    AttendancePlan, FinalDemandPrincipalId, GoodId, HouseholdCohort, HouseholdNeed,
    HouseholdNeedBasis, HouseholdPurchasePolicy, HouseholdStock, MaterialCircuitError, PricePolicy,
    ProcessId, ProductionDemandPolicy, RecurringEconomy, ReplenishmentPolicy, SellerOffer, SiteId,
    UnitId,
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
        bytes.push(row.basis as u8);
        bytes.extend_from_slice(&row.units_per_basis.to_be_bytes());
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
            PricePolicy::ServiceResponsive {
                minimum,
                maximum,
                step,
            } => {
                bytes.push(3);
                for amount in [minimum, maximum, step] {
                    bytes.extend_from_slice(&amount.micro_units().to_be_bytes());
                }
            }
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
    append_replenishment(output, &rows.replenishment)?;
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
    append_rows(output, &rows.service_inputs, |b, r| {
        b.extend_from_slice(&r.buyer_site_id.as_bytes());
        b.extend_from_slice(&r.provider_site_id.as_bytes());
        b.extend_from_slice(&r.good_id.as_bytes());
        b.extend_from_slice(&r.unit_id.as_bytes());
        b.extend_from_slice(&r.quantity_per_period.to_be_bytes());
        b.extend_from_slice(&r.maximum_purchase.to_be_bytes());
        b.extend_from_slice(&r.cash_floor.micro_units().to_be_bytes());
    })?;
    Ok(())
}

fn append_replenishment(
    output: &mut Vec<u8>,
    rows: &[ReplenishmentPolicy],
) -> Result<(), MaterialCircuitError> {
    append_bounded_rows(
        output,
        rows,
        crate::MAX_REPLENISHMENT_POLICIES,
        |bytes, row| {
            bytes.extend_from_slice(&row.buyer_site_id.as_bytes());
            bytes.extend_from_slice(&row.supplier_site_id.as_bytes());
            bytes.extend_from_slice(&row.good_id.as_bytes());
            bytes.extend_from_slice(&row.unit_id.as_bytes());
            bytes.extend_from_slice(&row.target_stock.to_be_bytes());
            bytes.extend_from_slice(&row.maximum_purchase.to_be_bytes());
            bytes.extend_from_slice(&row.cash_floor.micro_units().to_be_bytes());
        },
    )
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
        3 => Ok(PricePolicy::ServiceResponsive {
            minimum: currency(bytes)?,
            maximum: currency(bytes)?,
            step: currency(bytes)?,
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
                basis: match bytes.u8()? {
                    1 => HouseholdNeedBasis::Persons,
                    2 => HouseholdNeedBasis::Households,
                    _ => return Err(MaterialCircuitError::WireEnum),
                },
                units_per_basis: bytes.u64()?,
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
        replenishment: decode_bounded_rows(cursor, crate::MAX_REPLENISHMENT_POLICIES, |bytes| {
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
        service_inputs: decode_rows(cursor, |b| {
            Ok(crate::ServiceInputPolicy {
                buyer_site_id: SiteId::from_bytes(b.array()?),
                provider_site_id: SiteId::from_bytes(b.array()?),
                good_id: GoodId::from_bytes(b.array()?),
                unit_id: UnitId::from_bytes(b.array()?),
                quantity_per_period: b.u64()?,
                maximum_purchase: b.u64()?,
                cash_floor: currency(b)?,
            })
        })?,
    })))
}
