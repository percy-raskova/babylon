//! Personal single-line allocation inputs. Only the reviewed command can leave the client.
use super::editor::{FocusState, NoteEditor};
use super::ui::{ActionButton, OrganizerAction, Scope};
use super::OrganizerClient;
use super::RequestKind;
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer::SessionPhase;
use crate::observer::{ObservationContext, ObserverSession};
use crate::observer_focus::ObserverFocusTarget;
use crate::observer_io::ObserverSet;
use crate::observer_theme as theme;
use crate::ui;
use babylon_persistence::runtime_session::{OrganizerAllocation, OrganizerChoice};
use bevy::input::keyboard::{Key, KeyboardInput};
use bevy::input::ButtonState;
use bevy::input_focus::{FocusedInput, InputFocus};
use bevy::prelude::*;
use serde::{Deserialize, Serialize};

const MICROS: i128 = 1_000_000;

#[derive(Component, Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum AmountField {
    Contribution,
    Food,
    Cash,
}

impl AmountField {
    const fn index(self) -> usize {
        self as usize
    }
    const fn label(self) -> &'static str {
        match self {
            Self::Contribution => "Contribution target · $",
            Self::Food => "Food parcels",
            Self::Cash => "Cash gift · $",
        }
    }
    pub(super) fn applies(self, choice: OrganizerChoice) -> bool {
        match self {
            Self::Contribution => choice == OrganizerChoice::Collect,
            Self::Food | Self::Cash => matches!(
                choice,
                OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid
            ),
        }
    }
    fn bound(self, client: &OrganizerClient) -> Option<i128> {
        match self {
            Self::Contribution => Some(client.collection_preview()?.maximum_cash_micros / MICROS),
            Self::Food => Some(i128::from(
                client.aid_preview(client.choice())?.maximum_quantity,
            )),
            Self::Cash => Some(client.aid_preview(client.choice())?.maximum_cash_micros / MICROS),
        }
    }
    fn initial_text(self, client: &OrganizerClient) -> Option<String> {
        let draft = client.draft.as_ref()?;
        let micros = match (self, draft.collection_allocation, draft.aid_allocation) {
            (Self::Contribution, OrganizerAllocation::Collection { target_cash_micros }, _) => {
                target_cash_micros
            }
            (Self::Food, _, OrganizerAllocation::Aid { food_quantity, .. }) => {
                return Some(food_quantity.to_string())
            }
            (Self::Cash, _, OrganizerAllocation::Aid { cash_micros, .. }) => cash_micros,
            _ => return None,
        };
        if micros % MICROS == 0 {
            return Some((micros / MICROS).to_string());
        }
        // A captured fractional amount is visible and fails whole-dollar editing until replaced.
        Some(crate::human_numbers::currency(micros).replace(['$', ','], ""))
    }
    fn initial(self, client: &OrganizerClient) -> NoteEditor {
        let text = self.initial_text(client).unwrap_or_default();
        NoteEditor {
            cursor: text.len(),
            text,
            selected_all: false,
        }
    }
    pub(super) fn text(self, client: &OrganizerClient) -> String {
        client.amounts.raw[self.index()]
            .as_ref()
            .map_or_else(|| self.initial(client).text, |v| v.text.clone())
    }
    fn parsed(self, client: &OrganizerClient) -> Result<i128, String> {
        if let Some(message) = client.amounts.rejected[self.index()] {
            return Err(message.to_owned());
        }
        let text = self.text(client);
        let min = i128::from(self == Self::Contribution);
        let max = self
            .bound(client)
            .ok_or_else(|| "Current allocation terms unavailable.".to_owned())?;
        let value = text.parse::<i128>().ok();
        if !text.is_empty() && text.bytes().all(|b| b.is_ascii_digit()) {
            if let Some(valid) = value.filter(|v| (min..=max).contains(v)) {
                return Ok(valid);
            }
        }
        Err(format!(
            "{} needs a whole number from {min} to {max}.",
            self.label()
        ))
    }
}

#[derive(Default)]
pub(super) struct AmountEdits {
    raw: [Option<NoteEditor>; 3],
    rejected: [Option<&'static str>; 3],
    expected_input: Option<(Entity, ObservationContext, KeyboardInput)>,
}

pub(super) fn allocation(client: &OrganizerClient) -> Result<OrganizerAllocation, String> {
    match client.choice() {
        OrganizerChoice::Collect => Ok(OrganizerAllocation::Collection {
            target_cash_micros: AmountField::Contribution
                .parsed(client)?
                .checked_mul(MICROS)
                .ok_or("Contribution exceeds currency capacity.")?,
        }),
        OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid => {
            let food_quantity = u64::try_from(AmountField::Food.parsed(client)?)
                .map_err(|_| "Food quantity is too large.")?;
            let cash_micros = AmountField::Cash
                .parsed(client)?
                .checked_mul(MICROS)
                .ok_or("Cash exceeds currency capacity.")?;
            let terms = client
                .aid_preview(client.choice())
                .ok_or("Current aid terms unavailable.")?;
            if food_quantity > 0 && terms.food.is_none() {
                return Err(
                    "Food terms are unavailable for this partner. Set food parcels to zero.".into(),
                );
            }
            if cash_micros > 0 && terms.payer_cash.is_none() {
                return Err(
                    "No cash payer is available for this offer. Set the cash gift to zero.".into(),
                );
            }
            if food_quantity == 0 && cash_micros == 0 {
                return Err("Choose at least one food parcel or a positive cash gift.".into());
            }
            Ok(OrganizerAllocation::Aid {
                food_quantity,
                cash_micros,
            })
        }
        _ => Ok(OrganizerAllocation::None),
    }
}

/// Install only the entire basket currently valid for the selected recipient.
pub(super) fn reconcile(client: &mut OrganizerClient) -> Result<(), String> {
    let selected = allocation(client)?;
    let draft = client.draft.as_mut().ok_or("Personal draft unavailable.")?;
    match selected {
        OrganizerAllocation::Aid { .. } => draft.aid_allocation = selected,
        OrganizerAllocation::Collection { .. } => draft.collection_allocation = selected,
        OrganizerAllocation::None => {}
    }
    Ok(())
}

pub(super) fn editing_allowed(client: &OrganizerClient, session: &ObserverSession) -> bool {
    let preview_pending = client
        .pending
        .as_ref()
        .is_some_and(|p| p.kind == RequestKind::Preview)
        && session.organizer_enabled
        && session.phase == SessionPhase::Ready
        && !session.advance_pending()
        && !session.lifecycle_pending()
        && session.viewed_tick == session.durable_tick
        && client
            .view
            .as_ref()
            .is_some_and(|v| v.period == session.durable_tick);
    client.draft_writable
        && (client.available(session) || preview_pending)
        && client.commitment.is_none()
}

#[derive(Component)]
struct FieldValue(AmountField);

pub(super) fn spawn(parent: &mut ChildSpawnerCommands) {
    parent
        .spawn(Node {
            column_gap: px(10),
            flex_shrink: 0.0,
            ..default()
        })
        .with_children(|row| {
            for field in [
                AmountField::Contribution,
                AmountField::Food,
                AmountField::Cash,
            ] {
                row.spawn((
                    ui::pressable(),
                    field,
                    ActionButton(OrganizerAction::FocusAmount(field)),
                    ObserverFocusTarget::text_input(None),
                    Node {
                        padding: UiRect::axes(px(8), px(3)),
                        border: UiRect::bottom(px(2)),
                        ..default()
                    },
                    BackgroundColor(theme::INK),
                    BorderColor::all(theme::COPPER),
                    DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
                ))
                .with_child((super::ui::text("", 15.0, theme::PAPER), FieldValue(field)));
            }
        });
}

fn paint(
    scope: Scope,
    focus: Res<InputFocus>,
    mut values: Query<(&FieldValue, &ChildOf, &mut Text)>,
) {
    if !(scope.client.is_changed()
        || scope.session.is_changed()
        || scope.ui.is_changed()
        || scope.view.is_changed()
        || focus.is_changed())
    {
        return;
    }
    for (field, parent, mut text) in &mut values {
        if !super::ui::visible(
            OrganizerAction::FocusAmount(field.0),
            &scope.client,
            &scope.session,
            &scope.ui,
            *scope.view,
        ) {
            text.set_if_neq(Text::new(""));
            continue;
        }
        let editor = scope.client.amounts.raw[field.0.index()]
            .clone()
            .unwrap_or_else(|| field.0.initial(&scope.client));
        let shown = editor.display(if focus.get() == Some(parent.parent()) {
            FocusState::Focused
        } else {
            FocusState::Unfocused
        });
        let shown = if focus.get() == Some(parent.parent()) {
            shown
        } else {
            field
                .0
                .parsed(&scope.client)
                .ok()
                .and_then(|v| u128::try_from(v).ok())
                .map_or(shown, crate::human_numbers::grouped)
        };
        let display: String = shown.chars().take(15).collect();
        text.set_if_neq(Text::new(format!(
            "{}  {display}{}",
            field.0.label(),
            if display.len() < shown.len() {
                "…"
            } else {
                ""
            }
        )));
    }
}

fn edit_key(
    editor: &mut NoteEditor,
    input: &KeyboardInput,
    keys: &ButtonInput<KeyCode>,
) -> Result<(), &'static str> {
    let control = [
        KeyCode::ControlLeft,
        KeyCode::ControlRight,
        KeyCode::SuperLeft,
        KeyCode::SuperRight,
    ]
    .into_iter()
    .any(|key| keys.pressed(key));
    match input.key_code {
        KeyCode::KeyA if control => editor.selected_all = true,
        KeyCode::ArrowLeft => editor.left(),
        KeyCode::ArrowRight => editor.right(),
        KeyCode::Home => editor.home(),
        KeyCode::End => editor.end(),
        KeyCode::Backspace => editor.backspace(),
        KeyCode::Delete => editor.delete(),
        KeyCode::Enter | KeyCode::NumpadEnter => {}
        _ if !control => {
            let typed = input.text.as_deref().or_else(|| match &input.logical_key {
                Key::Character(s) => Some(s.as_str()),
                _ => None,
            });
            if let Some(s) = typed {
                if s.chars().any(char::is_control) {
                    return Err("Enter the amount on one line using digits.");
                }
                let existing = if editor.selected_all {
                    0
                } else {
                    editor.text.len()
                };
                if s.len().saturating_add(existing) > super::editor::MAX_NOTE_BYTES {
                    return Err("Amount text is too long. Select it and enter whole digits.");
                }
                editor.insert(s);
            }
        }
        _ => {}
    }
    Ok(())
}

fn input(
    mut event: On<FocusedInput<KeyboardInput>>,
    fields: Query<(&AmountField, &ObserverFocusTarget)>,
    focus: Res<InputFocus>,
    keys: Res<ButtonInput<KeyCode>>,
    mut client: ResMut<OrganizerClient>,
    session: Res<ObserverSession>,
    time: Res<Time>,
) {
    let Some(entity) = focus.get() else { return };
    let Ok((&field, target)) = fields.get(entity) else {
        return;
    };
    if event.original_event_target() != entity
        || event.input.state != ButtonState::Pressed
        || event.input.key_code == KeyCode::Tab
        || !target.available
        || target.context != Some(session.context())
        || !field.applies(client.choice())
        || !editing_allowed(&client, &session)
    {
        return;
    }
    event.propagate(false);
    let mut editor = client.amounts.raw[field.index()]
        .take()
        .unwrap_or_else(|| field.initial(&client));
    let old = editor.text.clone();
    let error = edit_key(&mut editor, &event.input, &keys).err();
    let changed = old != editor.text || error.is_some();
    if changed {
        client.amounts.rejected[field.index()] = error;
    }
    client.amounts.raw[field.index()] = Some(editor);
    if client
        .amounts
        .expected_input
        .as_ref()
        .is_some_and(|(target, context, key)| {
            *target == entity && *context == session.context() && *key == event.input
        })
    {
        client.amounts.expected_input = None;
    }
    if !changed {
        return;
    }
    client.clear_review();
    match reconcile(&mut client) {
        Ok(()) => {
            client.dirty(time.elapsed_secs_f64());
            client.message.clear();
        }
        Err(message) => client.message = message,
    }
}

/// Synchronously deliver the same focused keyboard event Bevy dispatches for a physical key.
pub(super) fn deliver_key(
    world: &mut World,
    target: Entity,
    context: ObservationContext,
    key: KeyboardInput,
) -> bool {
    if world.resource::<InputFocus>().get() != Some(target)
        || world.resource::<ObserverSession>().context() != context
    {
        return false;
    }
    let window = key.window;
    world
        .resource_mut::<OrganizerClient>()
        .amounts
        .expected_input = Some((target, context, key.clone()));
    world.trigger(FocusedInput::new(target, key.clone(), window));
    let handled = world
        .resource_mut::<OrganizerClient>()
        .amounts
        .expected_input
        .take()
        .is_none();
    world.trigger(FocusedInput::new(
        target,
        KeyboardInput {
            state: ButtonState::Released,
            text: None,
            ..key
        },
        window,
    ));
    handled
}

pub(super) fn install(app: &mut App) {
    app.add_observer(input)
        .add_systems(Update, paint.in_set(ObserverSet::Paint));
}
