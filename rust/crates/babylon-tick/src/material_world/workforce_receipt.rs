//! Exact resident staffing and attendance evidence in the existing tick envelope.
use super::{MaterialWorldError, ReceiptCursor};
use babylon_kernel::{currency::Currency, economic_location::EconomicLocation};
use babylon_material_circuit::{
    FinalDemandPrincipalId, LaborCompensation, MemberLaborUseReceipt, SiteId,
    StaffingMemberBinding, StaffingMemberId, StaffingMemberReceipt, StaffingPoolId, UnitId,
};

pub(super) const STAFFING_BYTES: usize = 246;
pub(super) const ATTENDANCE_BYTES: usize = 329;

pub(super) fn encode_staffing(
    row: &StaffingMemberReceipt,
    period: u64,
    bytes: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    row.validate().map_err(|_| MaterialWorldError::Wire)?;
    if row.period != period {
        return Err(MaterialWorldError::Wire);
    }
    for id in [
        row.pool_id.as_bytes(),
        row.site_id.as_bytes(),
        row.unit_id.as_bytes(),
        row.member.member_id().as_bytes(),
        row.member.household_id().as_bytes(),
    ] {
        bytes.extend_from_slice(&id);
    }
    bytes.extend_from_slice(&row.member.residence().canonical_bytes());
    for value in [
        row.period,
        row.member.labor_force(),
        row.hours_per_person,
        row.opening_employed,
        row.opening_reserve,
        row.hires,
        row.separations,
        row.closing_employed,
        row.closing_reserve,
        row.next_opening_hours,
    ] {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
    Ok(())
}
pub(super) fn decode_staffing(
    cursor: &mut ReceiptCursor<'_>,
    period: u64,
) -> Result<StaffingMemberReceipt, MaterialWorldError> {
    let pool_id = StaffingPoolId::from_bytes(cursor.take()?);
    let site_id = SiteId::from_bytes(cursor.take()?);
    let unit_id = UnitId::from_bytes(cursor.take()?);
    let member_id = StaffingMemberId::from_bytes(cursor.take()?);
    let household_id = FinalDemandPrincipalId::from_bytes(cursor.take()?);
    let residence = EconomicLocation::from_canonical_bytes(cursor.take()?)
        .map_err(|_| MaterialWorldError::Wire)?;
    let row_period = cursor.u64()?;
    let member = StaffingMemberBinding::try_new(member_id, household_id, residence, cursor.u64()?)
        .map_err(|_| MaterialWorldError::Wire)?;
    let row = StaffingMemberReceipt {
        period: row_period,
        pool_id,
        site_id,
        unit_id,
        member,
        hours_per_person: cursor.u64()?,
        opening_employed: cursor.u64()?,
        opening_reserve: cursor.u64()?,
        hires: cursor.u64()?,
        separations: cursor.u64()?,
        closing_employed: cursor.u64()?,
        closing_reserve: cursor.u64()?,
        next_opening_hours: cursor.u64()?,
    };
    row.validate().map_err(|_| MaterialWorldError::Wire)?;
    if row.period != period {
        return Err(MaterialWorldError::Wire);
    }
    Ok(row)
}

pub(super) fn encode_attendance(
    row: &MemberLaborUseReceipt,
    period: u64,
    bytes: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    row.validate().map_err(|_| MaterialWorldError::Wire)?;
    if row.period != period {
        return Err(MaterialWorldError::Wire);
    }
    for id in [
        row.member_id.as_bytes(),
        row.site_id.as_bytes(),
        row.unit_id.as_bytes(),
        row.payee.as_bytes(),
    ] {
        bytes.extend_from_slice(&id);
    }
    bytes.push(match row.compensation {
        LaborCompensation::Wage(_) => 1,
        LaborCompensation::WorkingOwner => 2,
        LaborCompensation::UnpaidFamily => 3,
    });
    bytes.extend_from_slice(&row.compensation.wage_rate().micro_units().to_be_bytes());
    for value in [
        row.period,
        row.available_hours,
        row.planned_hours,
        row.unplanned_hours,
        row.attended_hours,
        row.unattended_hours,
        row.production_hours,
        row.handling_hours,
        row.maintenance_hours,
        row.installation_hours,
        row.idle_hours,
    ] {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
    for value in [
        row.accrued_wages,
        row.production_wages,
        row.handling_wages,
        row.maintenance_wages,
        row.installation_wages,
        row.idle_wages,
    ] {
        bytes.extend_from_slice(&value.micro_units().to_be_bytes());
    }
    Ok(())
}
pub(super) fn decode_attendance(
    cursor: &mut ReceiptCursor<'_>,
    period: u64,
) -> Result<MemberLaborUseReceipt, MaterialWorldError> {
    let member_id = StaffingMemberId::from_bytes(cursor.take()?);
    let site_id = SiteId::from_bytes(cursor.take()?);
    let unit_id = UnitId::from_bytes(cursor.take()?);
    let payee = FinalDemandPrincipalId::from_bytes(cursor.take()?);
    let tag = cursor.take::<1>()?[0];
    let rate = currency(cursor)?;
    let compensation = match tag {
        1 if rate.micro_units() > 0 => LaborCompensation::Wage(rate),
        2 if rate.micro_units() == 0 => LaborCompensation::WorkingOwner,
        3 if rate.micro_units() == 0 => LaborCompensation::UnpaidFamily,
        _ => return Err(MaterialWorldError::Wire),
    };
    let row = MemberLaborUseReceipt {
        member_id,
        site_id,
        unit_id,
        payee,
        compensation,
        period: cursor.u64()?,
        available_hours: cursor.u64()?,
        planned_hours: cursor.u64()?,
        unplanned_hours: cursor.u64()?,
        attended_hours: cursor.u64()?,
        unattended_hours: cursor.u64()?,
        production_hours: cursor.u64()?,
        handling_hours: cursor.u64()?,
        maintenance_hours: cursor.u64()?,
        installation_hours: cursor.u64()?,
        idle_hours: cursor.u64()?,
        accrued_wages: currency(cursor)?,
        production_wages: currency(cursor)?,
        handling_wages: currency(cursor)?,
        maintenance_wages: currency(cursor)?,
        installation_wages: currency(cursor)?,
        idle_wages: currency(cursor)?,
    };
    row.validate().map_err(|_| MaterialWorldError::Wire)?;
    if row.period != period {
        return Err(MaterialWorldError::Wire);
    }
    Ok(row)
}
fn currency(cursor: &mut ReceiptCursor<'_>) -> Result<Currency, MaterialWorldError> {
    Ok(Currency::from_micro_units(i128::from_be_bytes(
        cursor.take()?,
    )))
}

pub(super) fn validate_join(
    staffing: &[StaffingMemberReceipt],
    members: &[MemberLaborUseReceipt],
    labor: &[babylon_material_circuit::LaborUseReceipt],
    wages: &[babylon_material_circuit::WageAccrualReceipt],
) -> Result<(), MaterialWorldError> {
    use std::collections::{BTreeMap, BTreeSet};
    if staffing
        .windows(2)
        .any(|p| (p[0].pool_id, p[0].member.member_id()) >= (p[1].pool_id, p[1].member.member_id()))
        || members.windows(2).any(|p| {
            (p[0].site_id, p[0].unit_id, p[0].member_id)
                >= (p[1].site_id, p[1].unit_id, p[1].member_id)
        })
    {
        return Err(MaterialWorldError::Wire);
    }
    let staff: BTreeMap<_, _> = staffing.iter().map(|r| (r.member.member_id(), r)).collect();
    let mut actual: BTreeMap<_, _> = wages.iter().map(|r| (r.shift, r)).collect();
    if staff.len() != staffing.len()
        || actual.len() != wages.len()
        || (!staff.is_empty() && !members.is_empty() && staff.len() != members.len())
    {
        return Err(MaterialWorldError::Wire);
    }
    let mut ids = BTreeSet::new();
    let mut aggregates = BTreeMap::new();
    for row in members {
        row.validate().map_err(|_| MaterialWorldError::Wire)?;
        if !ids.insert(row.member_id) {
            return Err(MaterialWorldError::Wire);
        }
        if !staff.is_empty() {
            let claim = staff.get(&row.member_id).ok_or(MaterialWorldError::Wire)?;
            if (claim.site_id, claim.unit_id, claim.member.household_id())
                != (row.site_id, row.unit_id, row.payee)
                || claim.opening_employed.checked_mul(claim.hours_per_person)
                    != Some(row.available_hours)
            {
                return Err(MaterialWorldError::Wire);
            }
        }
        add_member(
            aggregates
                .entry((row.site_id, row.unit_id))
                .or_insert_with(|| empty_aggregate(row)),
            row,
        )?;
        if matches!(row.compensation, LaborCompensation::Wage(_)) && row.attended_hours > 0 {
            let terms = babylon_material_circuit::EmploymentTerms {
                member_id: row.member_id,
                site_id: row.site_id,
                unit_id: row.unit_id,
                payee: row.payee,
                compensation: row.compensation,
            };
            let wage = actual
                .remove(&babylon_material_circuit::member_shift_id(
                    row.period, &terms,
                ))
                .ok_or(MaterialWorldError::Wire)?;
            validate_wage(row, wage)?;
        }
    }
    if !actual.is_empty() || aggregates.into_values().collect::<Vec<_>>() != labor {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

fn validate_wage(
    row: &MemberLaborUseReceipt,
    wage: &babylon_material_circuit::WageAccrualReceipt,
) -> Result<(), MaterialWorldError> {
    use babylon_material_circuit::AccountId;
    if (
        wage.employer,
        wage.payee,
        wage.period,
        wage.obligated_hours,
        wage.amount,
    ) != (
        AccountId::Site(row.site_id),
        AccountId::Household(row.payee),
        row.period,
        row.attended_hours,
        row.accrued_wages,
    ) {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

fn empty_aggregate(row: &MemberLaborUseReceipt) -> babylon_material_circuit::LaborUseReceipt {
    babylon_material_circuit::LaborUseReceipt {
        site_id: row.site_id,
        unit_id: row.unit_id,
        period: row.period,
        available_hours: 0,
        planned_hours: 0,
        unplanned_hours: 0,
        funded_hours: 0,
        unfunded_hours: 0,
        non_wage_hours: 0,
        used_hours: 0,
        paid_idle_hours: 0,
        unpaid_idle_hours: 0,
    }
}

fn add_member(
    aggregate: &mut babylon_material_circuit::LaborUseReceipt,
    row: &MemberLaborUseReceipt,
) -> Result<(), MaterialWorldError> {
    if aggregate.period != row.period {
        return Err(MaterialWorldError::Wire);
    }
    add_hours(&mut aggregate.available_hours, row.available_hours)?;
    add_hours(&mut aggregate.planned_hours, row.planned_hours)?;
    add_hours(&mut aggregate.unplanned_hours, row.unplanned_hours)?;
    add_hours(
        &mut aggregate.used_hours,
        row.attended_hours - row.idle_hours,
    )?;
    match row.compensation {
        LaborCompensation::Wage(_) => {
            add_hours(&mut aggregate.funded_hours, row.attended_hours)?;
            add_hours(&mut aggregate.unfunded_hours, row.unattended_hours)?;
            add_hours(&mut aggregate.paid_idle_hours, row.idle_hours)?;
        }
        LaborCompensation::WorkingOwner | LaborCompensation::UnpaidFamily => {
            add_hours(&mut aggregate.non_wage_hours, row.attended_hours)?;
            add_hours(&mut aggregate.unpaid_idle_hours, row.idle_hours)?;
        }
    }
    Ok(())
}

fn add_hours(total: &mut u64, amount: u64) -> Result<(), MaterialWorldError> {
    *total = total
        .checked_add(amount)
        .ok_or(MaterialWorldError::Arithmetic)?;
    Ok(())
}

#[cfg(test)]
mod tests;
