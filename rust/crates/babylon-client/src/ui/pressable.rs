//! The pressable control bundle the observer shell spawns.

use crate::ui::Interaction;
use bevy::ecs::bundle::Bundle;
use bevy::ui::FocusPolicy;
use bevy::ui_widgets::Button;

/// The bundle a pressable control needs while the shell runs the inherited
/// interaction state machine: Bevy 0.20's button marker contributes only
/// accessibility, so the interaction component and its blocking focus policy are
/// declared here explicitly (Bevy 0.18's `Button` required both).
pub(crate) fn pressable() -> impl Bundle {
    (Button, Interaction::default(), FocusPolicy::Block)
}
