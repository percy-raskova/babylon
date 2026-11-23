//! The shocks: labelled changes of a figure of the catalog, struck and lifted between periods.
//! A shock never touches the engine's state; the runner builds the catalog the book names.

use crate::doubled::Figures;
use crate::Place;
use std::error::Error;
use std::fmt::{Display, Formatter, Result as FmtResult};

/// A shock the scene offers.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Shock {
    /// A farm batch makes 9 food, not 10.
    HarvestFails,
    /// A utility batch takes 10 hours and makes 9 units, not 1 hour and 1 unit.
    PowerCut,
}

impl Shock {
    /// Every shock, in the order the scene lists them.
    pub const ALL: [Shock; 2] = [Shock::HarvestFails, Shock::PowerCut];

    /// The shock's name.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::HarvestFails => "The harvest fails",
            Self::PowerCut => "The power is cut",
        }
    }

    /// The figure that changes.
    #[must_use]
    pub const fn figure(self) -> &'static str {
        match self {
            Self::HarvestFails => "a farm makes 9 food a batch, not 10",
            Self::PowerCut => "a utility makes 9 power for 10 hours, not 10",
        }
    }
}

/// Where a shock is struck.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Places {
    /// Place A.
    A,
    /// Place B.
    B,
    /// Both.
    Both,
}

impl Places {
    /// The places, in order.
    #[must_use]
    pub fn places(self) -> Vec<Place> {
        match self {
            Self::A => vec![Place::A],
            Self::B => vec![Place::B],
            Self::Both => vec![Place::A, Place::B],
        }
    }

    /// The choice in words.
    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::A => "Place A",
            Self::B => "Place B",
            Self::Both => "both places",
        }
    }
}

/// How long a shock lasts.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Lasts {
    /// Ten periods, then the opening's figure returns.
    TenPeriods,
    /// Until it is lifted.
    UntilLifted,
}

impl Lasts {
    /// The choice in words.
    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::TenPeriods => "for ten periods",
            Self::UntilLifted => "until lifted",
        }
    }
}

/// One shock in one place.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Strike {
    /// What was struck.
    pub shock: Shock,
    /// Where.
    pub place: Place,
    /// How long it was struck for.
    pub lasts: Lasts,
    /// The first period closed under the shock.
    pub from: u64,
    /// The first period back at the opening's figure, if it is known.
    pub until: Option<u64>,
}

impl Strike {
    fn holds_at(&self, period: u64) -> bool {
        self.from <= period && self.until.is_none_or(|until| period < until)
    }

    /// Holds now or is waiting to hold: not yet over at `next`.
    fn is_live(&self, next: u64) -> bool {
        self.until.is_none_or(|until| next < until)
    }
}

/// The strikes of a run, in the order struck.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct ShockBook {
    strikes: Vec<Strike>,
}

impl ShockBook {
    /// Every strike, in the order struck.
    #[must_use]
    pub fn strikes(&self) -> &[Strike] {
        &self.strikes
    }

    /// Whether the shock holds in the place at the period.
    #[must_use]
    pub fn holds(&self, shock: Shock, place: Place, period: u64) -> bool {
        self.strikes
            .iter()
            .any(|s| s.shock == shock && s.place == place && s.holds_at(period))
    }

    /// The catalog's figures for the period.
    #[must_use]
    pub fn figures(&self, period: u64) -> Figures {
        let mut figures = Figures::OPENING;
        for strike in self.strikes.iter().filter(|s| s.holds_at(period)) {
            let i = strike.place.index();
            match strike.shock {
                Shock::HarvestFails => figures.farm_yield[i] = 9,
                Shock::PowerCut => {
                    figures.utility_hours_per_batch[i] = 10;
                    figures.utility_output_per_batch[i] = 9;
                }
            }
        }
        figures
    }

    pub(crate) fn live(&self, shock: Shock, place: Place, next: u64) -> Option<usize> {
        self.strikes
            .iter()
            .position(|s| s.shock == shock && s.place == place && s.is_live(next))
    }

    pub(crate) fn strike(
        &mut self,
        shock: Shock,
        places: Places,
        lasts: Lasts,
        next: u64,
    ) -> Result<(), ShockError> {
        if shock == Shock::PowerCut && lasts == Lasts::TenPeriods {
            return Err(ShockError::TenPeriodsOnlyForTheHarvest);
        }
        let places = places.places();
        for &place in &places {
            if self.live(shock, place, next).is_some() {
                return Err(ShockError::AlreadyHolds { shock, place });
            }
        }
        let until = match lasts {
            Lasts::TenPeriods => Some(next.checked_add(10).ok_or(ShockError::Stopped)?),
            Lasts::UntilLifted => None,
        };
        for place in places {
            self.strikes.push(Strike {
                shock,
                place,
                lasts,
                from: next,
                until,
            });
        }
        Ok(())
    }

    pub(crate) fn lift(&mut self, shock: Shock, place: Place, next: u64) -> Result<(), ShockError> {
        let Some(index) = self.live(shock, place, next) else {
            return Err(ShockError::NotHolding { shock, place });
        };
        if shock == Shock::PowerCut {
            return Err(ShockError::HoldsUntilStartOver);
        }
        let from = self.strikes.get(index).map(|s| s.from);
        if from.is_some_and(|from| from >= next) {
            self.strikes.remove(index);
        } else if let Some(strike) = self.strikes.get_mut(index) {
            strike.until = Some(next);
        }
        Ok(())
    }
}

/// Why a strike or a lift was refused.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ShockError {
    /// The shock already holds, or is waiting to hold, in the place.
    AlreadyHolds {
        /// The shock.
        shock: Shock,
        /// The place.
        place: Place,
    },
    /// The shock is not holding in the place.
    NotHolding {
        /// The shock.
        shock: Shock,
        /// The place.
        place: Place,
    },
    /// Only the harvest can be struck for ten periods.
    TenPeriodsOnlyForTheHarvest,
    /// The power cut holds until the run is started over.
    HoldsUntilStartOver,
    /// The run is stopped.
    Stopped,
}

impl Display for ShockError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::AlreadyHolds { shock, place } => {
                write!(f, "{} already holds in {}", shock.name(), place.label())
            }
            Self::NotHolding { shock, place } => {
                write!(f, "{} is not holding in {}", shock.name(), place.label())
            }
            Self::TenPeriodsOnlyForTheHarvest => {
                write!(f, "only the harvest can fail for ten periods")
            }
            Self::HoldsUntilStartOver => {
                write!(f, "the power cut holds until the run is started over")
            }
            Self::Stopped => write!(f, "the run is stopped"),
        }
    }
}

impl Error for ShockError {}
