//! What a small world's builder refuses with.

use babylon_material_circuit::{MaterialCircuitError, StaffingError};
use std::error::Error;
use std::fmt::{Display, Formatter, Result as FmtResult};

/// A refusal while a small world is built.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WorldError {
    /// A constructor of the engine refused.
    Engine(MaterialCircuitError),
    /// A staffing constructor of the engine refused.
    Staffing(StaffingError),
    /// The location text did not parse.
    Location(String),
    /// A checked sum or product overflowed.
    Arithmetic,
}

impl Display for WorldError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::Engine(error) => write!(f, "the engine refused the world: {error:?}"),
            Self::Staffing(error) => write!(f, "{error}"),
            Self::Location(text) => write!(f, "the place {text:?} is not a location"),
            Self::Arithmetic => write!(f, "a sum or product in the world's opening overflowed"),
        }
    }
}

impl Error for WorldError {}

impl From<MaterialCircuitError> for WorldError {
    fn from(error: MaterialCircuitError) -> Self {
        Self::Engine(error)
    }
}

impl From<StaffingError> for WorldError {
    fn from(error: StaffingError) -> Self {
        Self::Staffing(error)
    }
}
