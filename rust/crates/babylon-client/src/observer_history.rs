//! Bounded, capability-scoped history. Charts never recompute a transition.

mod delivery_groups;

#[path = "observer_history/panel.rs"]
mod panel;

pub use panel::ObserverHistoryPlugin;
