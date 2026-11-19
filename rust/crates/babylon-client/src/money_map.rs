//! Settled payments and recorded labor crossing the selected geographic boundary.

#[cfg(test)]
#[path = "money_map/tests.rs"]
mod tests;

#[path = "money_map/books.rs"]
mod books;
#[path = "money_map/company.rs"]
mod company;
#[path = "money_map/compare.rs"]
mod compare;
#[path = "money_map/freight.rs"]
mod freight;
#[path = "money_map/freight_plot.rs"]
mod freight_plot;
#[path = "money_map/freight_rail.rs"]
mod freight_rail;
#[path = "money_map/geographic_legs.rs"]
mod geographic_legs;
#[path = "money_map/geometry.rs"]
mod geometry;
#[path = "money_map/grouping.rs"]
mod grouping;
#[path = "money_map/household.rs"]
pub(crate) mod household;
#[path = "money_map/industry.rs"]
mod industry;
#[path = "money_map/publication.rs"]
mod publication;
#[path = "money_map/rail.rs"]
mod rail;

#[path = "money_map/sankey.rs"]
mod sankey;
#[path = "money_map/sankey_image.rs"]
mod sankey_image;
#[path = "money_map/sankey_layout.rs"]
mod sankey_layout;

#[path = "money_map/state.rs"]
mod state;

pub(super) use geometry::frame_bounds;
pub(super) use state::install;
pub(crate) use state::{MoneyRail, MoneyView};
