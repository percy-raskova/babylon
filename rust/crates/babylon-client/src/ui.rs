//! Fog-safe Archive dossier presentation.

pub mod dossier_card;
pub mod dossier_compose;

/// The tri-state UI interaction component the observer shell observes.
///
/// Bevy 0.20 inherits this type as `DeprecatedInteraction` and deprecates the
/// `Interaction` alias in favour of picking's `Hovered` plus `ui::Pressed`.
/// `ui_focus_system` still writes this component, and every pressable control in
/// the shell reads it, so the migration to the picking model is a deliberate
/// follow-up rather than a rename: the replacement has no single tri-state
/// equivalent for the hover/press painting these systems do.
pub(crate) use bevy::ui::DeprecatedInteraction as Interaction;

/// The bundle a pressable control needs while the shell runs the inherited
/// interaction state machine: Bevy 0.20's button marker contributes only
/// accessibility, so the interaction component and its blocking focus policy are
/// declared here explicitly (Bevy 0.18's `Button` required both).
pub(crate) fn pressable() -> impl bevy::ecs::bundle::Bundle {
    (
        bevy::ui_widgets::Button,
        Interaction::default(),
        bevy::ui::FocusPolicy::Block,
    )
}
