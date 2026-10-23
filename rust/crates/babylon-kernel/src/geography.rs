//! Source geographic identities. Syntax and jurisdiction do not establish roster membership.

mod roster;

pub use roster::{NationalCountyRoster, NationalCountyRosterError, NATIONAL_COUNTY_COUNT};

#[path = "geography/geoid.rs"]
mod geoid;

pub use geoid::{CountyGeoid, CountyGeoidError, CountyJurisdiction};
