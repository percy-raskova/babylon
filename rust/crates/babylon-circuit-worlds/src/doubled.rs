//! The doubled fund world: two places of four workplaces, one treasury and one fund.

pub mod catalog;
pub mod figures;
pub mod opening;
pub mod staffing;

pub use catalog::catalog;
pub use figures::{Figures, HORIZON, HOURS_PER_PERSON, OPENING_MONEY, PERSONS};
pub use opening::opening_state;
pub use staffing::{member, staffing};
