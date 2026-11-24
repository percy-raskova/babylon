//! The fold's phases one by one, for the stored records' inner tests.
pub use crate::auxiliary::{
    aid_arrivals, aid_dispatch, installation, maintenance_and_installation, maintenance_close,
    productive_assets,
};
pub use crate::circulation::{consume, freight_arrivals, outbound};
pub use crate::household_work::{agency_observations, collections};
pub use crate::production::execute;
pub use crate::services::{finish, handoff};
