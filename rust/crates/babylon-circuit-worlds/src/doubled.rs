//! The doubled world: two places of four workplaces, in the bench's two worlds and two scales.

pub mod catalog;
pub mod figures;
pub mod opening;
pub mod staffing;
pub mod world;

pub use catalog::{catalog, catalog_of};
pub use figures::{Figures, HORIZON, HOURS_PER_PERSON, OPENING_MONEY, PERSONS};
pub use opening::{opening_state, opening_state_of};
pub use staffing::{member, member_of, members_of, staffing, staffing_of};
pub use world::{Economy, OpeningPush, Pushed, Scale, World};
