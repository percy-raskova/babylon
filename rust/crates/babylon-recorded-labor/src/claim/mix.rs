use super::kind::Claim;
use super::purses::ClaimError;

/// Money in millionths of a dollar by kind, in the order of `Claim::ALL`; every amount at least 0.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Mix {
    amounts: [i128; 4],
}

impl Mix {
    /// An amount of one kind.
    #[must_use]
    pub const fn of(claim: Claim, amount: i128) -> Self {
        let mut amounts = [0; 4];
        amounts[claim.index()] = amount;
        Self { amounts }
    }

    /// What it holds of one kind.
    #[must_use]
    pub const fn amount(&self, claim: Claim) -> i128 {
        self.amounts[claim.index()]
    }

    /// All kinds together.
    ///
    /// # Errors
    /// `Arithmetic` on overflow.
    pub fn total(&self) -> Result<i128, ClaimError> {
        self.amounts
            .iter()
            .try_fold(0_i128, |sum, amount| sum.checked_add(*amount))
            .ok_or(ClaimError::Arithmetic)
    }

    /// Put another mix in.
    ///
    /// # Errors
    /// `Arithmetic` on overflow; the mix is then unchanged.
    pub fn add(&mut self, other: Mix) -> Result<(), ClaimError> {
        let mut next = self.amounts;
        for (slot, add) in next.iter_mut().zip(other.amounts) {
            *slot = slot.checked_add(add).ok_or(ClaimError::Arithmetic)?;
        }
        self.amounts = next;
        Ok(())
    }

    /// Take `amount` out by the average rule: each kind gives its floor share, `amount * k / total` in the
    /// ledger's form `(k / total) * amount + ((k % total) * amount) / total`; the rest (fewer units than there
    /// are kinds) is taken from the kinds in the order of `Claim::ALL`, each as far as it still holds. A draw of
    /// the whole takes every kind whole. The mix is unchanged on an error.
    ///
    /// # Errors
    /// `Overdrawn` above the total or below 0; `Arithmetic`.
    pub fn draw(&mut self, amount: i128) -> Result<Mix, ClaimError> {
        let total = self.total()?;
        if amount < 0 || amount > total {
            return Err(ClaimError::Overdrawn);
        }
        if amount == total {
            let taken = *self;
            self.amounts = [0; 4];
            return Ok(taken);
        }
        let mut taken = [0_i128; 4];
        let mut given = 0_i128;
        for (slot, held) in taken.iter_mut().zip(self.amounts) {
            let whole = (held / total)
                .checked_mul(amount)
                .ok_or(ClaimError::Arithmetic)?;
            let part = (held % total)
                .checked_mul(amount)
                .ok_or(ClaimError::Arithmetic)?
                / total;
            *slot = whole.checked_add(part).ok_or(ClaimError::Arithmetic)?;
            given = given.checked_add(*slot).ok_or(ClaimError::Arithmetic)?;
        }
        let mut rest = amount.checked_sub(given).ok_or(ClaimError::Arithmetic)?;
        for (slot, held) in taken.iter_mut().zip(self.amounts) {
            let more = rest.min(held - *slot);
            *slot += more;
            rest -= more;
        }
        if rest != 0 {
            return Err(ClaimError::Arithmetic);
        }
        let mut left = self.amounts;
        for (slot, took) in left.iter_mut().zip(taken) {
            *slot -= took;
        }
        self.amounts = left;
        Ok(Mix { amounts: taken })
    }
}
