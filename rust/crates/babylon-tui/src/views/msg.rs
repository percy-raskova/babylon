//! Events views emit for the app shell to route (plan Task 19).

/// A view-level intent for the app shell.
///
/// Views never mutate app state directly: key/mouse handlers return an
/// `AppEvent` and the shell routes it (push/pop the view stack, call the
/// host, or quit).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AppEvent {
    /// Load the selected campaign into the Archive (M1: read-only browse).
    LoadCampaign(String),
    /// Begin the new-campaign flow (M2 wires the write path).
    NewCampaign,
    /// Navigate to a wiki subject (an entity id or redlink target).
    OpenSubject(String),
    /// Pop the current view from the stack.
    Back,
    /// Quit the client.
    Quit,
}
