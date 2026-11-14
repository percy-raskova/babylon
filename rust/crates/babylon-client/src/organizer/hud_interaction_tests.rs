//! Practice disclosure and pointer-state contracts through actual organizer controls.

use super::tests;
use super::{ActionButton, DetailControls, OrganizerAction, TextPart};
use crate::observer::ObserverSession;
use crate::observer_theme as theme;
use crate::organizer::{OrganizerClient, OrganizerInspector};
use crate::ui::Interaction;
use babylon_persistence::runtime_session::{OrganizerChoice, OrganizerInquiry};
use bevy::prelude::*;

fn practice_button(app: &mut App, choice: OrganizerChoice) -> Entity {
    let world = app.world_mut();
    world
        .query::<(Entity, &ActionButton, &ChildOf)>()
        .iter(world)
        .find_map(|(entity, button, parent)| {
            (button.0 == OrganizerAction::Choose(choice)
                && world
                    .get::<DetailControls>(parent.parent())
                    .is_some_and(|section| section.0 == OrganizerInspector::Practices))
            .then_some(entity)
        })
        .expect("the all-practices list exposes this choice")
}

#[test]
fn all_practices_expands_only_selected_details_and_keeps_unavailable_choices_inert() {
    let (mut app, _) = tests::admitted_scene_fixture();
    app.world_mut()
        .write_message(OrganizerAction::Inspect(OrganizerInspector::Practices));
    app.update();
    let inquiry = OrganizerChoice::Inquiry(OrganizerInquiry::MaintenanceReceived);
    let selected = practice_button(&mut app, inquiry);
    *app.world_mut()
        .get_mut::<Interaction>(selected)
        .expect("pointer state") = Interaction::Pressed;
    app.update();
    let client = app.world().resource::<OrganizerClient>();
    assert_eq!(
        client.choice(),
        inquiry,
        "the available choice updates only the personal draft"
    );
    assert_eq!(
        client.inspector,
        OrganizerInspector::Closed,
        "selection returns to the decision and its amount controls"
    );
    assert!(
        client.outbox.is_none() && client.preview.is_none(),
        "expanding a draft must not request authority or commit it"
    );
    app.world_mut()
        .write_message(OrganizerAction::Inspect(OrganizerInspector::Practices));
    app.update();
    let world = app.world_mut();
    let mut expanded = 0;
    let mut compact = 0;
    for (part, text) in world.query::<(&TextPart, &Text)>().iter(world) {
        if let TextPart::Approach(choice) = part {
            if *choice == inquiry {
                expanded += usize::from(text.0.contains("Details · selected draft"));
                assert!(
                    text.0.contains("Fixture workplace contacts"),
                    "selected details retain the captured partner"
                );
            } else {
                compact += 1;
                assert!(
                    !text.0.contains("Details ·"),
                    "unselected practices do not produce walls of explanation"
                );
                assert!(
                    text.0.lines().count() <= 2,
                    "collapsed practice retains a short cost and attribution summary"
                );
            }
        }
    }
    assert_eq!(
        (expanded, compact),
        (1, 8),
        "exactly one of nine practices is expanded"
    );
    *app.world_mut()
        .get_mut::<Interaction>(selected)
        .expect("pointer state") = Interaction::None;
    let unavailable = practice_button(&mut app, OrganizerChoice::RemoteAid);
    *app.world_mut()
        .get_mut::<Interaction>(unavailable)
        .expect("pointer state") = Interaction::Pressed;
    app.update();
    let client = app.world().resource::<OrganizerClient>();
    assert_eq!(
        client.choice(),
        inquiry,
        "undisclosed aid terms cannot replace the selected draft"
    );
    assert!(
        client.outbox.is_none(),
        "disabled selection must not submit an engine request"
    );
}

#[test]
fn selected_hover_and_disabled_states_keep_selection_and_explain_pending_authority() {
    let (mut app, _) = tests::admitted_scene_fixture();
    app.world_mut()
        .write_message(OrganizerAction::Inspect(OrganizerInspector::Practices));
    app.update();
    let choice = app.world().resource::<OrganizerClient>().choice();
    let button = practice_button(&mut app, choice);
    let selected_color = app
        .world()
        .get::<BackgroundColor>(button)
        .expect("selected surface")
        .0;
    *app.world_mut()
        .get_mut::<Interaction>(button)
        .expect("pointer state") = Interaction::Hovered;
    app.update();
    assert_ne!(
        app.world()
            .get::<BackgroundColor>(button)
            .expect("hover surface")
            .0,
        selected_color,
        "hover is visible without changing which draft is selected"
    );
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .set_organizer_control_pending(true);
    app.update();
    assert_eq!(
        app.world()
            .get::<BackgroundColor>(button)
            .expect("disabled surface")
            .0,
        theme::INK,
        "pending authority uses the disabled surface even for a hovered selected choice"
    );
    assert_eq!(
        app.world().resource::<OrganizerClient>().choice(),
        choice,
        "disabled hover preserves the draft"
    );
    let world = app.world_mut();
    let marker = world
        .query::<(&TextPart, &Text)>()
        .iter(world)
        .find_map(|(part, text)| {
            matches!(part, TextPart::ChoiceMarker(current) if *current == choice).then_some(&text.0)
        })
        .expect("selection and availability marker");
    assert!(
        marker.contains("SELECTED DRAFT") && marker.contains("Awaiting committed state"),
        "the pending reason stays visible beside selection: {marker}"
    );
}

#[test]
fn failed_pending_advance_keeps_its_actual_error_visible_without_resubmitting() {
    let (mut app, _) = tests::admitted_scene_fixture();
    {
        let mut session = app.world_mut().resource_mut::<ObserverSession>();
        assert!(
            session.begin_advance().is_some(),
            "the fixture submits one real pending advance"
        );
        session.fail("Saved-period connection failed; reopen to reconcile.".into());
    }
    app.update();
    let world = app.world_mut();
    let messages: Vec<_> = world
        .query::<(&TextPart, &Text)>()
        .iter(world)
        .filter_map(|(part, text)| matches!(part, TextPart::Message).then_some(text.0.as_str()))
        .collect();
    assert!(messages.iter().all(|message| message.contains("Saved-period connection failed")),
        "the actual failure replaces awaiting-commit prose on both workspace and inspector: {messages:?}");
    assert!(
        world.resource::<ObserverSession>().advance_pending(),
        "failure retains uncertainty until reconciliation"
    );
    assert!(
        world.resource::<OrganizerClient>().outbox.is_none(),
        "displaying an error cannot retry the advance"
    );
}

fn composite(foreground: Color, background: Color) -> Color {
    let foreground = foreground.to_linear();
    let background = background.to_linear();
    let remaining = 1.0 - foreground.alpha;
    Color::linear_rgb(
        foreground.red * foreground.alpha + background.red * remaining,
        foreground.green * foreground.alpha + background.green * remaining,
        foreground.blue * foreground.alpha + background.blue * remaining,
    )
}

fn painted_background(world: &World, entity: Entity) -> Color {
    let mut layers = Vec::new();
    let mut current = entity;
    loop {
        if let Some(background) = world.get::<BackgroundColor>(current) {
            layers.push(background.0);
            if background.0.to_linear().alpha >= 1.0 {
                break;
            }
        }
        current = world
            .get::<ChildOf>(current)
            .expect("practice text has an opaque inspector backdrop")
            .parent();
    }
    let mut result = layers
        .pop()
        .expect("the painted practice includes a background");
    for layer in layers.into_iter().rev() {
        result = composite(layer, result);
    }
    result
}

fn text_contrast(foreground: Color, background: Color) -> f32 {
    fn luminance(color: Color) -> f32 {
        let color = color.to_linear();
        0.2126 * color.red + 0.7152 * color.green + 0.0722 * color.blue
    }
    let ink = luminance(composite(foreground, background));
    let surface = luminance(background);
    (ink.max(surface) + 0.05) / (ink.min(surface) + 0.05)
}

fn assert_painted_practice_contrast(
    app: &App,
    button: Entity,
    choice: OrganizerChoice,
    interaction: Interaction,
) {
    let world = app.world();
    let background = painted_background(world, button);
    let mut copy_checked = false;
    for child in world
        .get::<Children>(button)
        .expect("actual practice-card text")
    {
        let Some(text) = world.get::<Text>(*child).filter(|text| !text.0.is_empty()) else {
            continue;
        };
        let foreground = world
            .get::<TextColor>(*child)
            .expect("painted text color")
            .0;
        let ratio = text_contrast(foreground, background);
        assert!(ratio >= 4.5,
            "{choice:?} {interaction:?} text must remain readable on its actual composited surface: contrast={ratio}, foreground={foreground:?}, background={background:?}, text={}", text.0);
        if matches!(world.get::<TextPart>(*child), Some(TextPart::Approach(current)) if *current == choice)
        {
            assert!(
                text.0.contains("Cost:"),
                "the contrast check includes the actual cost and explanatory body"
            );
            copy_checked = true;
        }
    }
    assert!(
        copy_checked,
        "the test measures actual practice details, not just the action label"
    );
}

#[test]
fn practice_costs_and_details_keep_contrast_in_selected_hover_and_pressed_states() {
    use bevy::ecs::system::RunSystemOnce as _;
    for choice in [
        OrganizerChoice::Hold,
        OrganizerChoice::Reinforce,
        OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost),
        OrganizerChoice::Collect,
        OrganizerChoice::LocalAid,
    ] {
        let mut app = if matches!(choice, OrganizerChoice::Collect | OrganizerChoice::LocalAid) {
            tests::allocation_opening().0
        } else {
            tests::admitted_scene_fixture().0
        };
        let button = practice_button(&mut app, choice);
        for selected in [
            choice,
            if choice == OrganizerChoice::Hold {
                OrganizerChoice::Reinforce
            } else {
                OrganizerChoice::Hold
            },
        ] {
            {
                let mut client = app.world_mut().resource_mut::<OrganizerClient>();
                client.draft.as_mut().expect("personal draft").choice = selected;
                client.inspector = OrganizerInspector::Practices;
            }
            assert!(
                super::enabled(
                    OrganizerAction::Choose(choice),
                    app.world().resource::<OrganizerClient>(),
                    app.world().resource::<ObserverSession>()
                ),
                "the {choice:?} fixture measures enabled semantic accents"
            );
            for interaction in [
                Interaction::None,
                Interaction::Hovered,
                Interaction::Pressed,
            ] {
                *app.world_mut()
                    .get_mut::<Interaction>(button)
                    .expect("real interaction state") = interaction;
                // Invoke the actual painter without dispatching a Pressed gameplay action.
                app.world_mut()
                    .run_system_once(super::paint)
                    .expect("the normal organizer painter accepts the admitted fixture");
                assert_painted_practice_contrast(&app, button, choice, interaction);
            }
        }
    }
}
