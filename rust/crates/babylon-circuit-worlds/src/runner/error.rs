//! What a step of the runner refuses with, in words a person can read.

use crate::runner::rules::RuleError;
use crate::Household;
use crate::{ShockError, WorldError};
use babylon_material_circuit::{MaterialCircuitError, StaffingError};
use babylon_recorded_labor::{ClaimError, RecordedLaborError};
use std::error::Error;
use std::fmt::{Display, Formatter, Result as FmtResult};

/// The part of a period in which the engine refused.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Stage {
    /// `close_material_period`.
    Close,
    /// `staffing_requests`.
    StaffingRequests,
    /// `advance_staffing`.
    AdvanceStaffing,
    /// `distribute_staffing_members`.
    DistributeMembers,
    /// `staff_in_places`.
    StaffInPlaces,
    /// `finish_with_staffing`.
    Finish,
    /// `material_circuit_state_digest`.
    Digest,
    /// Reading the closed period.
    Read,
}

impl Stage {
    /// The stage in words, after "the engine refused ".
    #[must_use]
    pub const fn words(self) -> &'static str {
        match self {
            Self::Close => "the close",
            Self::StaffingRequests => "the requests for staff",
            Self::AdvanceStaffing => "the staffing",
            Self::DistributeMembers => "the members' shares",
            Self::StaffInPlaces => "the staffing of each place",
            Self::Finish => "the finish",
            Self::Digest => "the digest",
            Self::Read => "the reading",
        }
    }
}

/// Which of the two folds refused.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum HoursRun {
    /// The fold in hours of work.
    Hours,
    /// The fold in units of opening stock.
    OpeningUnits,
}

/// A refusal of a step. The first one stops the run.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RunnerError {
    /// The engine refused.
    Engine {
        /// The period being closed.
        period: u64,
        /// Where in the period.
        stage: Stage,
        /// The engine's refusal.
        error: MaterialCircuitError,
    },
    /// The staffing refused.
    Staffing {
        /// The period being closed.
        period: u64,
        /// Where in the period.
        stage: Stage,
        /// The staffing's refusal.
        error: StaffingError,
    },
    /// The world's own builder refused.
    World(WorldError),
    /// A shock the world opens with was refused by the book.
    Shock(ShockError),
    /// `open_world` could not turn on a rule of the world.
    Rule(RuleError),
    /// The money of the world changed.
    MoneyNotConserved {
        /// The period being closed.
        period: u64,
        /// Millionths of a dollar at the opening.
        opening: i128,
        /// Millionths of a dollar after the period.
        closing: i128,
    },
    /// The persons of the world changed.
    PersonsNotConserved {
        /// The period being closed.
        period: u64,
        /// Persons at the opening.
        opening: u64,
        /// Persons after the period.
        closing: u64,
    },
    /// The hours ledger refused the period: a movement it has never seen, or closing stocks that differ.
    HoursRefused {
        /// The period being closed.
        period: u64,
        /// Which of the two folds refused.
        run: HoursRun,
        /// The ledger's refusal.
        error: RecordedLaborError,
    },
    /// The two runs of the hours ledger handed over different moves.
    HoursRunsDiffer {
        /// The period being closed.
        period: u64,
    },
    /// A receipt the hours record cannot place: an agency row, or an account or site of no party of the world.
    HoursUnplaced {
        /// The period being closed.
        period: u64,
        /// What could not be placed.
        what: String,
    },
    /// The purses could not follow the period's money.
    ClaimRefused {
        /// The period being closed.
        period: u64,
        /// The purses' refusal.
        error: ClaimError,
    },
    /// The kinds of a household's purse and its reserves are not its cash and reserves in the book.
    PurseNotBook {
        /// The period being closed.
        period: u64,
        /// The difference found.
        error: ClaimError,
    },
    /// The splits of a group's back do not add up to its back.
    ClaimsNotBack {
        /// The period being closed.
        period: u64,
        /// The group.
        household: Household,
        /// Micro-hours that reached its home.
        back: u128,
        /// Micro-hours in the four claims.
        claims: u128,
    },
    /// The test economy has no rows past its horizon.
    PastHorizon {
        /// The period that was asked for.
        period: u64,
    },
    /// An earlier refusal stopped the run.
    Stopped,
}

impl Display for RunnerError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::Engine {
                period,
                stage,
                error,
            } => write!(
                f,
                "Period {period}: the engine refused {}: {error:?} (code {})",
                stage.words(),
                *error as u16
            ),
            Self::Staffing { period, error, .. } => write!(f, "Period {period}: {error}"),
            Self::World(error) => write!(f, "{error}"),
            Self::Shock(error) => write!(f, "{error}"),
            Self::Rule(error) => write!(f, "the world's rules: {error}"),
            Self::MoneyNotConserved {
                period,
                opening,
                closing,
            } => write!(
                f,
                "Period {period}: money is not conserved: {opening} millionths at the opening, {closing} now"
            ),
            Self::PersonsNotConserved {
                period,
                opening,
                closing,
            } => write!(
                f,
                "Period {period}: persons are not conserved: {opening} at the opening, {closing} now"
            ),
            Self::HoursRefused { period, run, error } => match run {
                HoursRun::Hours => write!(f, "Period {period}: the hours ledger refused it: {error}"),
                HoursRun::OpeningUnits => write!(
                    f,
                    "Period {period}: the hours ledger refused it (opening units): {error}"
                ),
            },
            Self::HoursRunsDiffer { period } => write!(
                f,
                "Period {period}: the two runs of the hours ledger handed over different moves"
            ),
            Self::HoursUnplaced { period, what } => {
                write!(f, "Period {period}: the hours ledger cannot place {what}")
            }
            Self::ClaimRefused { period, error } => {
                write!(f, "Period {period}: the purses could not follow the money: {error}")
            }
            Self::PurseNotBook { period, error } => write!(
                f,
                "Period {period}: the kinds of money are not the book's money: {error}"
            ),
            Self::ClaimsNotBack {
                period,
                household,
                back,
                claims,
            } => write!(
                f,
                "Period {period}: {household:?}'s back is {back} micro-hours, its claims add up to {claims}"
            ),
            Self::PastHorizon { period } => {
                write!(f, "Period {period}: this test economy is built for 998 periods")
            }
            Self::Stopped => write!(
                f,
                "The run stopped at an earlier refusal. Start over to run again."
            ),
        }
    }
}

impl Error for RunnerError {}

impl From<WorldError> for RunnerError {
    fn from(error: WorldError) -> Self {
        Self::World(error)
    }
}

impl From<ShockError> for RunnerError {
    fn from(error: ShockError) -> Self {
        Self::Shock(error)
    }
}

impl From<RuleError> for RunnerError {
    fn from(error: RuleError) -> Self {
        Self::Rule(error)
    }
}
