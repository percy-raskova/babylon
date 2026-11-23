//! What a step of the runner refuses with, in words a person can read.

use crate::WorldError;
use babylon_material_circuit::{MaterialCircuitError, StaffingError};
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
            Self::Finish => "the finish",
            Self::Digest => "the digest",
            Self::Read => "the reading",
        }
    }
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
