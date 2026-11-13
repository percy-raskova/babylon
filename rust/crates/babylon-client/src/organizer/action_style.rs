//! Semantic action accents with separate disabled, selected and pointer states.

use super::resource_hud;
use super::ui::OrganizerAction;
use crate::observer_theme as theme;
use babylon_persistence::runtime_session::OrganizerChoice;
use bevy::prelude::Color;

pub(super) fn choice(choice: OrganizerChoice) -> Color {
    match choice {
        OrganizerChoice::Inquiry(_) => resource_hud::CYAN,
        OrganizerChoice::Reinforce => resource_hud::VIOLET,
        OrganizerChoice::Collect | OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid => {
            resource_hud::GREEN
        }
        OrganizerChoice::Hold
        | OrganizerChoice::PauseStanding
        | OrganizerChoice::ResumeStanding => theme::GRAY,
    }
}

pub(super) fn accent(action: OrganizerAction) -> Color {
    match action {
        OrganizerAction::Choose(selected) => choice(selected),
        OrganizerAction::Confirm | OrganizerAction::Review => resource_hud::GREEN,
        OrganizerAction::Advance => resource_hud::GOLD,
        _ => theme::GRAY,
    }
}
