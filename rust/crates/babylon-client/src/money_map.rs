//! Settled payments and recorded labor crossing the selected geographic boundary.

#[cfg(test)]
#[path = "money_map/tests.rs"]
mod tests;

#[path = "money_map/books.rs"]
mod books;
#[path = "money_map/compare.rs"]
mod compare;
#[path = "money_map/geometry.rs"]
mod geometry;
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

pub(crate) use state::MoneyRail;
pub(super) use state::{install, MoneyView};
