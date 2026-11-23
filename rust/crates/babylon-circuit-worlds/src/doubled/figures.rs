//! The figures of the doubled world that a shock may move, and the ones that never move.

use crate::{Household, Place, WorldError};

/// Capacity and corridor rows are written for periods 1 to `HORIZON`.
pub const HORIZON: u64 = 1_000;
/// Hours a person works in a period.
pub const HOURS_PER_PERSON: u64 = 10;
/// Persons of the world.
pub const PERSONS: u64 = 80;
/// Money at the opening, in millionths of a dollar ($12,240).
pub const OPENING_MONEY: i128 = 12_240_000_000;

/// What the catalog says of production in each place, indexed by `Place::index`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Figures {
    /// Food a farm batch makes.
    pub farm_yield: [u64; 2],
    /// Hours a utility batch takes.
    pub utility_hours_per_batch: [u64; 2],
    /// Units of power a utility batch makes.
    pub utility_output_per_batch: [u64; 2],
}

impl Figures {
    /// The opening's: a farm batch makes 10 food; a utility batch is 1 hour and 1 unit.
    pub const OPENING: Figures = Figures {
        farm_yield: [10, 10],
        utility_hours_per_batch: [1, 1],
        utility_output_per_batch: [1, 1],
    };
}

/// Persons of one place: the households' opening persons, which are the same in both places.
///
/// # Errors
/// `WorldError::Arithmetic` when the sum overflows.
pub(crate) fn place_persons() -> Result<u64, WorldError> {
    Household::ALL
        .iter()
        .filter(|h| h.place() == Place::A)
        .try_fold(0_u64, |sum, h| sum.checked_add(h.opening_persons()))
        .ok_or(WorldError::Arithmetic)
}
