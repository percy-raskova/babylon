use super::kind::Claim;
use super::mix::Mix;
use super::purses::ClaimError;

/// Hours split by kind, in micro-hours.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct ClaimHours {
    /// Hours that came through wages.
    pub work: u128,
    /// Hours that came through profit.
    pub owning: u128,
    /// Hours that came through benefits and public payments.
    pub support: u128,
    /// Hours that came through money held at the opening.
    pub not_recorded: u128,
}

impl ClaimHours {
    fn slots(&self) -> [u128; 4] {
        [self.work, self.owning, self.support, self.not_recorded]
    }

    fn from_slots(slots: [u128; 4]) -> Self {
        Self {
            work: slots[Claim::Work.index()],
            owning: slots[Claim::Owning.index()],
            support: slots[Claim::Support.index()],
            not_recorded: slots[Claim::NotRecorded.index()],
        }
    }

    /// The four together.
    ///
    /// # Errors
    /// `Arithmetic` on overflow.
    pub fn total(&self) -> Result<u128, ClaimError> {
        self.slots()
            .iter()
            .try_fold(0_u128, |sum, hours| sum.checked_add(*hours))
            .ok_or(ClaimError::Arithmetic)
    }

    /// Put another split in.
    ///
    /// # Errors
    /// `Arithmetic` on overflow; the split is then unchanged.
    pub fn add(&mut self, other: ClaimHours) -> Result<(), ClaimError> {
        let mut next = self.slots();
        for (slot, add) in next.iter_mut().zip(other.slots()) {
            *slot = slot.checked_add(add).ok_or(ClaimError::Arithmetic)?;
        }
        *self = Self::from_slots(next);
        Ok(())
    }
}

/// Split `micro_hours` by the shares of `paid`, the mix of the money that paid for them: each kind its floor
/// share, the rest to the last kind in order that holds money. The one place where hours and money meet.
///
/// # Errors
/// `Unpaid` (`paid` totals 0 and `micro_hours` is above 0); `Arithmetic`.
pub fn split_hours(micro_hours: u128, paid: &Mix) -> Result<ClaimHours, ClaimError> {
    if micro_hours == 0 {
        return Ok(ClaimHours::default());
    }
    let total = u128::try_from(paid.total()?).map_err(|_| ClaimError::Arithmetic)?;
    if total == 0 {
        return Err(ClaimError::Unpaid);
    }
    let mut slots = [0_u128; 4];
    let mut given = 0_u128;
    let mut last = None;
    for claim in Claim::ALL {
        let share = u128::try_from(paid.amount(claim)).map_err(|_| ClaimError::Arithmetic)?;
        if share > 0 {
            last = Some(claim.index());
        }
        let whole = (share / total)
            .checked_mul(micro_hours)
            .ok_or(ClaimError::Arithmetic)?;
        let part = (share % total)
            .checked_mul(micro_hours)
            .ok_or(ClaimError::Arithmetic)?
            / total;
        let hours = whole.checked_add(part).ok_or(ClaimError::Arithmetic)?;
        slots[claim.index()] = hours;
        given = given.checked_add(hours).ok_or(ClaimError::Arithmetic)?;
    }
    let rest = micro_hours
        .checked_sub(given)
        .ok_or(ClaimError::Arithmetic)?;
    let last = last.ok_or(ClaimError::Unpaid)?;
    slots[last] = slots[last]
        .checked_add(rest)
        .ok_or(ClaimError::Arithmetic)?;
    Ok(ClaimHours::from_slots(slots))
}
