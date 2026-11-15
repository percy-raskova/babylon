//! Whole residents advance between age bands after the present period's work and reproduction.
use crate::{FinalDemandPrincipalId, MaterialCircuitError, MAX_MATERIAL_CIRCUIT_ROWS};
use std::result::Result as StdResult;
pub(super) type Result<T> = StdResult<T, MaterialCircuitError>;
pub(super) const INVALID: MaterialCircuitError = MaterialCircuitError::HouseholdLifecycleInvariant;
pub(super) const RATE_SCALE: u32 = 1_000_000;
const PERIODS_PER_YEAR: u16 = 13;
pub(super) const BAND_PERIODS: [u16; 3] = [
    16 * PERIODS_PER_YEAR,
    2 * PERIODS_PER_YEAR,
    47 * PERIODS_PER_YEAR,
];
pub(crate) const MAX_BIRTHDAY_PERIODS: usize = 65 * 13;

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct ResidentAges {
    pub under_16: u64,
    pub age_16_17: u64,
    pub age_18_64: u64,
    pub age_65_plus: u64,
}
impl ResidentAges {
    pub(crate) const fn array(self) -> [u64; 4] {
        [
            self.under_16,
            self.age_16_17,
            self.age_18_64,
            self.age_65_plus,
        ]
    }
    pub(crate) const fn from_array(v: [u64; 4]) -> Self {
        Self {
            under_16: v[0],
            age_16_17: v[1],
            age_18_64: v[2],
            age_65_plus: v[3],
        }
    }
    /// # Errors
    /// Refuses an unrepresentable population.
    pub fn persons(self) -> Result<u64> {
        self.array().into_iter().try_fold(0u64, |a, b| {
            a.checked_add(b).ok_or(MaterialCircuitError::Arithmetic)
        })
    }
    /// The time-eligibility boundary includes residents aged 16–17 and 65+.
    /// # Errors
    /// Refuses an unrepresentable population.
    pub fn eligible(self) -> Result<u64> {
        self.persons().map(|n| n - self.under_16)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct HouseholdLifecycleRates {
    pub births_per_million_working_age_per_period: u32,
    pub deaths_per_million_per_period: [u32; 4],
}
impl HouseholdLifecycleRates {
    pub(crate) fn validate(self) -> Result<()> {
        if self.births_per_million_working_age_per_period > RATE_SCALE
            || self
                .deaths_per_million_per_period
                .iter()
                .any(|n| *n > RATE_SCALE)
        {
            return Err(INVALID);
        }
        Ok(())
    }
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HouseholdLifecyclePosition {
    pub principal_id: FinalDemandPrincipalId,
    pub ages: ResidentAges,
    pub(crate) previous: ResidentAges,
    pub(crate) previous_households: u64,
    pub(crate) birth_remainder: u32,
    pub(crate) death_remainders: [u32; 4],
    /// Original opening exposures, distributed evenly across the remaining birthdays in each band.
    pub(crate) initial: [u64; 3],
    /// Once their age is known, survivors with the same sixty-fifth birthday share one row.
    pub(crate) birthdays: Vec<(u64, u64)>,
}
impl HouseholdLifecyclePosition {
    /// Population and occupied households at the start of the retained close.
    #[must_use]
    pub const fn previous_opening(&self) -> (ResidentAges, u64) {
        (self.previous, self.previous_households)
    }
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HouseholdLifecycleBook {
    pub rates: HouseholdLifecycleRates,
    /// None preserves a fixed authored purchase envelope. National capture binds current need to this many periods.
    pub purchase_buffer_periods: Option<u64>,
    pub positions: Vec<HouseholdLifecyclePosition>,
}
impl HouseholdLifecycleBook {
    /// Capture positively identified age exposure; absent principals retain their frozen policy.
    /// # Errors
    /// Refuses duplicate principals, invalid rates, row bounds and population overflow.
    pub fn new(
        rates: HouseholdLifecycleRates,
        opening: Vec<(FinalDemandPrincipalId, ResidentAges)>,
    ) -> Result<Self> {
        rates.validate()?;
        if opening.is_empty() || opening.len() > MAX_MATERIAL_CIRCUIT_ROWS {
            return Err(INVALID);
        }
        let mut positions = opening
            .into_iter()
            .map(|(principal_id, ages)| {
                ages.persons()?;
                Ok(HouseholdLifecyclePosition {
                    principal_id,
                    ages,
                    previous: ages,
                    previous_households: 0,
                    birth_remainder: 0,
                    death_remainders: [0; 4],
                    initial: [ages.under_16, ages.age_16_17, ages.age_18_64],
                    birthdays: Vec::new(),
                })
            })
            .collect::<Result<Vec<_>>>()?;
        positions.sort_unstable_by_key(|p| p.principal_id);
        if positions
            .windows(2)
            .any(|p| p[0].principal_id == p[1].principal_id)
        {
            return Err(INVALID);
        }
        Ok(Self {
            rates,
            purchase_buffer_periods: None,
            positions,
        })
    }
    #[must_use]
    pub fn position(&self, id: FinalDemandPrincipalId) -> Option<&HouseholdLifecyclePosition> {
        self.positions
            .binary_search_by_key(&id, |p| p.principal_id)
            .ok()
            .map(|i| &self.positions[i])
    }
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HouseholdLifecycleReceipt {
    pub principal_id: FinalDemandPrincipalId,
    pub period: u64,
    pub opening: ResidentAges,
    pub closing: ResidentAges,
    pub births: u64,
    pub deaths: ResidentAges,
    pub reached_16: u64,
    pub reached_18: u64,
    pub reached_65: u64,
    pub opening_households: u64,
    pub closing_households: u64,
}
impl HouseholdLifecycleReceipt {
    /// Independently reconcile all five flows in whole persons against both openings.
    /// # Errors
    /// Refuses overspending an opening age band, nonconservation, and impossible occupied-household counts.
    pub fn validate(&self) -> Result<()> {
        if self.period == 0
            || self.opening_households > self.opening.persons()?
            || self.closing_households != self.opening_households.min(self.closing.persons()?)
        {
            return Err(INVALID);
        }
        let arrivals = [
            self.births,
            self.reached_16,
            self.reached_18,
            self.reached_65,
        ];
        let departures = [self.reached_16, self.reached_18, self.reached_65, 0];
        for i in 0..4 {
            if self.opening.array()[i]
                .checked_sub(self.deaths.array()[i])
                .and_then(|n| n.checked_sub(departures[i]))
                .and_then(|n| n.checked_add(arrivals[i]))
                != Some(self.closing.array()[i])
            {
                return Err(INVALID);
            }
        }
        Ok(())
    }
}
