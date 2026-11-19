//! Recorded labor in installed assets, maintenance and household aid.
mod aid;
#[cfg(test)]
mod aid_tests;
mod assets;
#[cfg(test)]
mod tests;

pub(super) use aid::{aid_arrivals, aid_dispatch};
pub(super) use assets::{maintenance_and_installation, productive_assets};
