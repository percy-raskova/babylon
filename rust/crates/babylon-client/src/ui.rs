//! Fog-safe Archive dossier presentation.

pub mod dossier_card;
pub mod dossier_compose;

mod pressable;

/// The tri-state UI interaction component the observer shell observes.
///
/// Bevy 0.20 inherits this type as `DeprecatedInteraction` and deprecates the
/// `Interaction` alias in favour of picking's `Hovered` plus `ui::Pressed`.
/// `ui_focus_system` still writes this component, and every pressable control in
/// the shell reads it, so the migration to the picking model is a deliberate
/// follow-up rather than a rename: the replacement has no single tri-state
/// equivalent for the hover/press painting these systems do.
pub(crate) use bevy::ui::DeprecatedInteraction as Interaction;
pub(crate) use pressable::pressable;
