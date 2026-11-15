//! Conditional state payload for whole-person demographic positions.
use super::Cursor;
use crate::{
    FinalDemandPrincipalId, HouseholdLifecycleBook, HouseholdLifecyclePosition,
    HouseholdLifecycleRates, MaterialCircuitError, ResidentAges,
};
use std::result::Result as StdResult;
type Result<T> = StdResult<T, MaterialCircuitError>;

fn append_ages(bytes: &mut Vec<u8>, ages: ResidentAges) {
    for n in ages.array() {
        bytes.extend_from_slice(&n.to_be_bytes());
    }
}
fn ages(c: &mut Cursor<'_>) -> Result<ResidentAges> {
    Ok(ResidentAges::from_array([
        c.u64()?,
        c.u64()?,
        c.u64()?,
        c.u64()?,
    ]))
}
pub(super) fn append(out: &mut Vec<u8>, book: &HouseholdLifecycleBook) -> Result<()> {
    book.rates.validate()?;
    let length_offset = out.len();
    out.extend_from_slice(&[0; 4]);
    let payload = out.len();
    out.extend_from_slice(
        &book
            .rates
            .births_per_million_working_age_per_period
            .to_be_bytes(),
    );
    for r in book.rates.deaths_per_million_per_period {
        out.extend_from_slice(&r.to_be_bytes());
    }
    match book.purchase_buffer_periods {
        None => out.push(0),
        Some(periods) => {
            out.push(1);
            out.extend_from_slice(&periods.to_be_bytes());
        }
    }
    super::append_rows(out, &book.positions, |buf, p| {
        buf.extend_from_slice(&p.principal_id.as_bytes());
        append_ages(buf, p.ages);
        append_ages(buf, p.previous);
        buf.extend_from_slice(&p.previous_households.to_be_bytes());
        buf.extend_from_slice(&p.birth_remainder.to_be_bytes());
        for n in p.death_remainders {
            buf.extend_from_slice(&n.to_be_bytes());
        }
        for n in p.initial {
            buf.extend_from_slice(&n.to_be_bytes());
        }
        let count = u16::try_from(p.birthdays.len())
            .expect("validated at most sixty-five years of birthday periods");
        buf.extend_from_slice(&count.to_be_bytes());
        for (birth, n) in &p.birthdays {
            buf.extend_from_slice(&birth.to_be_bytes());
            buf.extend_from_slice(&n.to_be_bytes());
        }
    })?;
    let length = u32::try_from(out.len() - payload).map_err(|_| MaterialCircuitError::WireLimit)?;
    out[length_offset..payload].copy_from_slice(&length.to_be_bytes());
    Ok(())
}
pub(super) fn decode(source: &mut Cursor<'_>) -> Result<HouseholdLifecycleBook> {
    let size = usize::try_from(source.u32()?).map_err(|_| MaterialCircuitError::WireLimit)?;
    let mut payload = Cursor::new(source.take(size)?);
    let c = &mut payload;
    let rates = HouseholdLifecycleRates {
        births_per_million_working_age_per_period: c.u32()?,
        deaths_per_million_per_period: [c.u32()?, c.u32()?, c.u32()?, c.u32()?],
    };
    rates.validate()?;
    let purchase_buffer_periods = match c.u8()? {
        0 => None,
        1 => Some(c.u64()?),
        _ => return Err(MaterialCircuitError::WireEnum),
    };
    let positions = super::decode_rows(c, |c| {
        let principal_id = FinalDemandPrincipalId::from_bytes(c.array()?);
        let ages_now = ages(c)?;
        let previous = ages(c)?;
        let previous_households = c.u64()?;
        let birth_remainder = c.u32()?;
        let death_remainders = [c.u32()?, c.u32()?, c.u32()?, c.u32()?];
        let initial = [c.u64()?, c.u64()?, c.u64()?];
        let length = usize::from(c.u16()?);
        if length > crate::household_lifecycle::MAX_BIRTHDAY_PERIODS {
            return Err(MaterialCircuitError::WireLimit);
        }
        let birthdays = (0..length)
            .map(|_| Ok((c.u64()?, c.u64()?)))
            .collect::<Result<Vec<_>>>()?;
        Ok(HouseholdLifecyclePosition {
            principal_id,
            ages: ages_now,
            previous,
            previous_households,
            birth_remainder,
            death_remainders,
            initial,
            birthdays,
        })
    })?;
    payload.finish()?;
    super::accounting::ordered_rows(&positions, |r| r.principal_id)?;
    Ok(HouseholdLifecycleBook {
        rates,
        purchase_buffer_periods,
        positions,
    })
}
