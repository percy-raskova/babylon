//! Client-local, descriptor-only navigation between the existing native reading surfaces.

mod controls;
mod history;
pub(crate) mod position;
mod runtime;

#[cfg(test)]
pub(crate) use controls::NavigationButton;
pub(crate) use controls::{spawn, NavigationAction, NavigationRegion};
pub(crate) use history::NavigationHistory;
pub(crate) use runtime::NavigationPlugin;
