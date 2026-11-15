//! Dated birthdays of living cohorts, including evenly distributed unknown opening ages.
use super::model::{
    HouseholdLifecyclePosition, HouseholdLifecycleRates, HouseholdLifecycleReceipt, ResidentAges,
    Result, BAND_PERIODS, INVALID, MAX_BIRTHDAY_PERIODS, RATE_SCALE,
};
use crate::MaterialCircuitError;

// Remaining four-week periods from birth, age 16 and age 18 to the 65th birthday.
const UNTIL_65: [u64; 3] = [65 * 13, 49 * 13, 47 * 13];

fn band(remaining: u64) -> usize {
    if remaining > UNTIL_65[1] {
        0
    } else if remaining > UNTIL_65[2] {
        1
    } else {
        2
    }
}

// The initial age distribution uses nearest-integer cumulative counts. Each opening
// resident's first birthday has one of the band's finite remaining dates.
fn original_due_later(original: u64, span: u16, completed: u64) -> u64 {
    let span = u64::from(span);
    if completed >= span {
        return 0;
    }
    let crossed =
        (u128::from(original) * u128::from(completed) + u128::from(span / 2)) / u128::from(span);
    original - u64::try_from(crossed).expect("a partial cohort cannot exceed its original")
}

fn first_birthday(surviving: u64, initial: u64, span: u16, period: u64) -> Result<u64> {
    let previous = original_due_later(initial, span, period - 1);
    if surviving > previous {
        return Err(INVALID);
    }
    if surviving == 0 {
        return Ok(0);
    }
    let later = original_due_later(initial, span, period);
    let due = previous - later;
    // Mortality removes whole people from the original schedule. Split remaining
    // survivors proportionally between those due now and those due later.
    let share =
        (u128::from(surviving) * u128::from(due) + u128::from(previous / 2)) / u128::from(previous);
    u64::try_from(share).map_err(|_| MaterialCircuitError::Arithmetic)
}
fn fraction(population: u64, numerator: u32, denominator: u32, carry: u32) -> Result<(u64, u32)> {
    if carry >= denominator {
        return Err(INVALID);
    }
    let n = u128::from(population) * u128::from(numerator) + u128::from(carry);
    let d = u128::from(denominator);
    Ok((
        u64::try_from(n / d).map_err(|_| MaterialCircuitError::Arithmetic)?,
        u32::try_from(n % d).map_err(|_| MaterialCircuitError::Arithmetic)?,
    ))
}
impl HouseholdLifecyclePosition {
    pub(crate) fn validate(&self, period: u64) -> Result<()> {
        let completed = period.checked_sub(1).ok_or(INVALID)?;
        if self.birth_remainder >= RATE_SCALE
            || self.death_remainders.iter().any(|r| *r >= RATE_SCALE)
            || self.birthdays.len() > MAX_BIRTHDAY_PERIODS
            || self.birthdays.windows(2).any(|pair| pair[0].0 >= pair[1].0)
        {
            return Err(INVALID);
        }
        let mut tracked = [0u64; 3];
        for &(due, count) in &self.birthdays {
            let remaining = due.checked_sub(completed).ok_or(INVALID)?;
            if count == 0 || remaining == 0 || remaining > UNTIL_65[0] || due <= UNTIL_65[2] {
                return Err(INVALID);
            }
            let i = band(remaining);
            tracked[i] = tracked[i]
                .checked_add(count)
                .ok_or(MaterialCircuitError::Arithmetic)?;
        }
        for (i, n) in tracked.into_iter().enumerate() {
            let initial_surviving = self.ages.array()[i].checked_sub(n).ok_or(INVALID)?;
            if initial_surviving > original_due_later(self.initial[i], BAND_PERIODS[i], completed) {
                return Err(INVALID);
            }
        }
        self.ages.persons()?;
        if self.previous_households > self.previous.persons()? {
            return Err(INVALID);
        }
        Ok(())
    }

    fn dated_survivors(
        &mut self,
        completed: u64,
        opening: ResidentAges,
        deaths: [u64; 4],
    ) -> Result<[u64; 3]> {
        let mut totals = [0; 3];
        for (i, total) in totals.iter_mut().enumerate() {
            let start = self
                .birthdays
                .partition_point(|(due, _)| band(*due - completed) > i);
            let end = self.birthdays[start..]
                .partition_point(|(due, _)| band(*due - completed) == i)
                + start;
            let rows = &mut self.birthdays[start..end];
            let tracked = rows.iter().try_fold(0_u64, |sum, (_, n)| {
                sum.checked_add(*n).ok_or(MaterialCircuitError::Arithmetic)
            })?;
            *total = tracked;
            if tracked > 0 && deaths[i] > 0 {
                let mixed = opening.array()[i].checked_sub(tracked).ok_or(INVALID)?;
                let weights = std::iter::once(mixed)
                    .chain(rows.iter().map(|r| r.1))
                    .collect::<Vec<_>>();
                let losses = crate::staffing::proportional_shares(deaths[i], &weights)
                    .map_err(|_| INVALID)?;
                for (row, n) in rows.iter_mut().zip(&losses[1..]) {
                    row.1 -= n;
                    *total -= n;
                }
            }
        }
        Ok(totals)
    }

    fn schedule(&mut self, period: u64, remaining: u64, count: u64) -> Result<()> {
        if count == 0 {
            return Ok(());
        }
        let due = period
            .checked_add(remaining)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        match self.birthdays.binary_search_by_key(&due, |r| r.0) {
            Ok(i) => {
                self.birthdays[i].1 = self.birthdays[i]
                    .1
                    .checked_add(count)
                    .ok_or(MaterialCircuitError::Arithmetic)?;
            }
            Err(i) => self.birthdays.insert(i, (due, count)),
        }
        Ok(())
    }

    fn birthdays(
        &mut self,
        period: u64,
        alive: [u64; 4],
        tracked: [u64; 3],
        births: u64,
    ) -> Result<[u64; 3]> {
        let mut ages = [0; 3];
        for i in 0..3 {
            let mixed = alive[i].checked_sub(tracked[i]).ok_or(INVALID)?;
            ages[i] = first_birthday(mixed, self.initial[i], BAND_PERIODS[i], period)?;
        }
        let first = ages;
        for (count, offset) in ages.iter_mut().zip([UNTIL_65[1], UNTIL_65[2], 0]) {
            if let Some(due) = period.checked_add(offset) {
                if let Ok(i) = self.birthdays.binary_search_by_key(&due, |r| r.0) {
                    *count = count
                        .checked_add(self.birthdays[i].1)
                        .ok_or(MaterialCircuitError::Arithmetic)?;
                }
            }
        }
        self.birthdays.retain(|(due, n)| *n > 0 && *due > period);
        self.schedule(period, UNTIL_65[0], births)?;
        self.schedule(period, UNTIL_65[1], first[0])?;
        self.schedule(period, UNTIL_65[2], first[1])?;
        Ok(ages)
    }
    pub(super) fn next(
        &mut self,
        rates: HouseholdLifecycleRates,
        period: u64,
        households: u64,
    ) -> Result<HouseholdLifecycleReceipt> {
        self.validate(period)?;
        let opening = self.ages;
        let (births, birth_remainder) = fraction(
            opening.age_18_64,
            rates.births_per_million_working_age_per_period,
            RATE_SCALE,
            self.birth_remainder,
        )?;
        let mut alive = opening.array();
        let mut deaths = [0; 4];
        for (i, n) in alive.iter_mut().enumerate() {
            (deaths[i], self.death_remainders[i]) = fraction(
                *n,
                rates.deaths_per_million_per_period[i],
                RATE_SCALE,
                self.death_remainders[i],
            )?;
            *n -= deaths[i];
        }
        let tracked = self.dated_survivors(period - 1, opening, deaths)?;
        let ages = self.birthdays(period, alive, tracked, births)?;
        let incoming = [births, ages[0], ages[1], ages[2]];
        for i in 0..4 {
            alive[i] = alive[i]
                .checked_sub(ages.get(i).copied().unwrap_or(0))
                .and_then(|n| n.checked_add(incoming[i]))
                .ok_or(MaterialCircuitError::Arithmetic)?;
        }
        let closing = ResidentAges::from_array(alive);
        let row = HouseholdLifecycleReceipt {
            principal_id: self.principal_id,
            period,
            opening,
            closing,
            births,
            deaths: ResidentAges::from_array(deaths),
            reached_16: ages[0],
            reached_18: ages[1],
            reached_65: ages[2],
            opening_households: households,
            closing_households: households.min(closing.persons()?),
        };
        row.validate()?;
        self.previous = opening;
        self.previous_households = households;
        self.ages = closing;
        self.birth_remainder = birth_remainder;
        Ok(row)
    }
}
