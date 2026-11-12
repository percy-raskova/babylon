pub(crate) fn install_national_opening(app: &mut App) {
    use babylon_persistence::runtime_session::OrganizerSnapshot;
    let snapshot: OrganizerSnapshot = serde_json::from_str(include_str!(
        "../../../babylon-persistence/tests/fixtures/national_organizer_opening_v19.json"
    ))
    .expect("national opening");
    install_captured_opening(app, snapshot);
}

fn install_captured_opening(app: &mut App, snapshot: OrganizerSnapshot) {
    use babylon_persistence::runtime_session::OrganizerBodySource;
    let campaign = Uuid::from_bytes(snapshot.body_scope.campaign_id);
    let mut session = ObserverSession::new(CampaignId::from_uuid(campaign));
    session.connected_fixture();
    session.ready(0, None);
    session.organizer_enabled = true;
    if let Some(OrganizerBodySource::Foundation { foundation_digest }) = &snapshot.body_scope.source
    {
        session.foundation_digest = Some(crate::dossier::hex_bytes(*foundation_digest));
    }
    let context = session.context();
    assert!(session.installed(&context));
    let mut client = OrganizerClient::default();
    client.admitted(campaign);
    client.draft = Some(OrganizerDraft::captured(&snapshot));
    client.draft_writable = true;
    client.queue(&mut session, RequestKind::Status, None);
    let Some(RuntimeSessionRequest::OrganizerStatus { request_id, .. }) = client.outbox.take()
    else {
        panic!("requested status")
    };
    client
        .status(request_id, snapshot, &mut session)
        .expect("admitted national opening");
    app.insert_resource(session).insert_resource(client);
}

pub(crate) fn allocation_opening() -> (App, Entity) {
    let (mut app, window, _, _) = focused_organizer(false);
    install_national_opening(&mut app);
    app.update();
    (app, window)
}

fn ordinary(app: &mut App, action: OrganizerAction) {
    app.world_mut().write_message(action);
    app.update();
    app.update();
}

#[test]
fn allocation_keyboard_invalidates_review_and_confirms_only_the_edited_basket() {
    let (mut app, window) = allocation_opening();
    ordinary(
        &mut app,
        OrganizerAction::Inspect(OrganizerInspector::Practices),
    );
    ordinary(&mut app, OrganizerAction::Choose(OrganizerChoice::LocalAid));
    assert_eq!(
        app.world().resource::<OrganizerClient>().choice(),
        OrganizerChoice::LocalAid
    );
    ordinary(&mut app, OrganizerAction::FocusAmount(AmountField::Cash));
    review_selected(&mut app);
    assert!(confirmation_enabled(&app));
    // Ordinary end/backspace replaces the initial zero. Intermediate empty text has no command.
    typing_key(&mut app, window, KeyCode::Backspace, "");
    let client = app.world().resource::<OrganizerClient>();
    assert!(
        client.reviewed_command.is_none() && client.preview.is_none() && client.outbox.is_none()
    );
    typing_key(&mut app, window, KeyCode::Minus, "-");
    typing_key(&mut app, window, KeyCode::Digit3, "3");
    assert!(app
        .world()
        .resource::<OrganizerClient>()
        .message
        .contains("whole number"));
    ordinary(
        &mut app,
        OrganizerAction::Choose(OrganizerChoice::RemoteAid),
    );
    assert!(
        app.world()
            .resource::<OrganizerClient>()
            .message
            .contains("whole number"),
        "switching recipients must keep the shared field's validation visible"
    );
    assert!(!enabled(
        OrganizerAction::Review,
        app.world().resource::<OrganizerClient>(),
        app.world().resource::<ObserverSession>()
    ));
    ordinary(&mut app, OrganizerAction::FocusAmount(AmountField::Cash));
    typing_key(&mut app, window, KeyCode::Backspace, "");
    typing_key(&mut app, window, KeyCode::Backspace, "");
    typing_key(&mut app, window, KeyCode::Digit3, "3");
    typing_key(&mut app, window, KeyCode::Digit7, "7");
    ordinary(&mut app, OrganizerAction::FocusAmount(AmountField::Food));
    typing_key(&mut app, window, KeyCode::Backspace, "");
    typing_key(&mut app, window, KeyCode::Digit2, "2");
    let basket = OrganizerAllocation::Aid {
        food_quantity: 2,
        cash_micros: 37_000_000,
    };
    assert_eq!(
        app.world()
            .resource::<OrganizerClient>()
            .draft
            .as_ref()
            .expect("draft")
            .aid_allocation,
        basket
    );
    ordinary(&mut app, OrganizerAction::Review);
    let command = app
        .world_mut()
        .resource_scope(|world, mut client: Mut<OrganizerClient>| {
            let RuntimeSessionRequest::PreviewOrganizer {
                request_id,
                command,
                ..
            } = client.outbox.take().expect("review")
            else {
                panic!("preview required")
            };
            assert_eq!(command.allocation, basket);
            assert_eq!(command.choice, OrganizerChoice::RemoteAid);
            client
                .previewed(
                    request_id,
                    preview_for(&command),
                    &mut world.resource_mut::<ObserverSession>(),
                )
                .expect("matched review");
            command
        });
    // Personal persistence is checked by draft round-trip tests. This UI test never writes a user file.
    app.world_mut()
        .resource_mut::<OrganizerClient>()
        .draft_dirty = false;
    ordinary(&mut app, OrganizerAction::Confirm);
    assert!(
        matches!(app.world().resource::<OrganizerClient>().outbox,Some(RuntimeSessionRequest::SubmitOrganizer{command:ref actual,..}) if actual==&command)
    );
}

#[test]
fn allocation_change_while_preview_is_in_flight_blocks_the_old_response() {
    let (mut app, window) = allocation_opening();
    ordinary(
        &mut app,
        OrganizerAction::Inspect(OrganizerInspector::Practices),
    );
    ordinary(&mut app, OrganizerAction::Choose(OrganizerChoice::Collect));
    ordinary(&mut app, OrganizerAction::Review);
    let Some(RuntimeSessionRequest::PreviewOrganizer {
        command,
        request_id,
        ..
    }) = app
        .world_mut()
        .resource_mut::<OrganizerClient>()
        .outbox
        .take()
    else {
        panic!("preview queued")
    };
    ordinary(&mut app, OrganizerAction::CloseInspector);
    ordinary(
        &mut app,
        OrganizerAction::FocusAmount(AmountField::Contribution),
    );
    typing_key(&mut app, window, KeyCode::Backspace, "");
    app.world_mut()
        .resource_scope(|world, mut client: Mut<OrganizerClient>| {
            let mut session = world.resource_mut::<ObserverSession>();
            client
                .previewed(request_id, preview_for(&command), &mut session)
                .expect("stale reply consumed");
            assert!(client.preview.is_none() && client.reviewed_command.is_none());
            assert_eq!(
                client.draft.as_ref().expect("draft").collection_allocation,
                OrganizerAllocation::Collection {
                    target_cash_micros: 28_000_000
                }
            );
        });
}

#[test]
fn invalid_typing_while_preview_pending_never_restores_confirm() {
    let (mut app, window) = allocation_opening();
    ordinary(
        &mut app,
        OrganizerAction::Inspect(OrganizerInspector::Practices),
    );
    ordinary(&mut app, OrganizerAction::Choose(OrganizerChoice::LocalAid));
    ordinary(&mut app, OrganizerAction::Review);
    let Some(RuntimeSessionRequest::PreviewOrganizer {
        command,
        request_id,
        ..
    }) = app
        .world_mut()
        .resource_mut::<OrganizerClient>()
        .outbox
        .take()
    else {
        panic!("preview queued")
    };
    ordinary(&mut app, OrganizerAction::CloseInspector);
    ordinary(&mut app, OrganizerAction::FocusAmount(AmountField::Cash));
    typing_key(&mut app, window, KeyCode::Minus, "-");
    app.world_mut()
        .resource_scope(|world, mut client: Mut<OrganizerClient>| {
            assert_eq!(
                client.draft.as_ref().expect("saved basket").aid_allocation,
                command.allocation
            );
            let mut session = world.resource_mut::<ObserverSession>();
            client
                .previewed(request_id, preview_for(&command), &mut session)
                .expect("discard stale authentication");
            assert!(
                client.preview.is_none()
                    && client.review_context.is_none()
                    && client.reviewed_command.is_none()
            );
        });
    ordinary(
        &mut app,
        OrganizerAction::Choose(OrganizerChoice::RemoteAid),
    );
    assert!(!confirmation_enabled(&app));
    assert_eq!(
        AmountField::Cash.text(app.world().resource::<OrganizerClient>()),
        "0-"
    );
}

#[test]
fn report_proposal_keeps_known_subject_citation_and_personal_draft_without_a_command() {
    let (mut app, window) = allocation_opening();
    ordinary(
        &mut app,
        OrganizerAction::Inspect(OrganizerInspector::Practices),
    );
    ordinary(&mut app, OrganizerAction::Choose(OrganizerChoice::LocalAid));
    replace_digit(&mut app, window, AmountField::Food, "0");
    let partner = app
        .world()
        .resource::<OrganizerClient>()
        .view
        .as_ref()
        .expect("view")
        .aid_partners[1]
        .actor_id;
    // The test subject is established through the captured view; the actual gallery
    // and Archive targets have independent full body-scope navigation coverage.
    ordinary(
        &mut app,
        OrganizerAction::SelectSubject(OrganizerSubject::AidPartner(partner)),
    );
    ordinary(&mut app, OrganizerAction::InspectSubjectEvidence);
    let before = app.world().resource::<OrganizerClient>();
    let id = before
        .selected_evidence_id(0)
        .expect("partner opening evidence");
    let prior = before.draft.clone().expect("draft");
    ordinary(&mut app, OrganizerAction::DraftFromReport);
    let after = app.world().resource::<OrganizerClient>();
    let draft = after.draft.as_ref().expect("cited ordinary draft");
    assert_eq!(draft.selected_reference, Some(id));
    assert_eq!(draft.notes, prior.notes);
    assert_eq!(draft.aid_allocation, prior.aid_allocation);
    assert_eq!(draft.choice, OrganizerChoice::RemoteAid);
    assert_eq!(
        after.selected_subject,
        Some(OrganizerSubject::AidPartner(partner))
    );
    assert!(after.outbox.is_none() && after.preview.is_none() && after.commitment.is_none());
    let reason = amount_editor::allocation(after).expect_err("retained zero basket");
    assert!(
        after.message.contains("Report cited") && after.message.contains(&reason),
        "{}",
        after.message
    );
    assert!(!enabled(
        OrganizerAction::Review,
        after,
        app.world().resource::<ObserverSession>()
    ));
    replace_digit(&mut app, window, AmountField::Food, "2");
    let corrected = app.world().resource::<OrganizerClient>();
    assert!(!corrected.message.contains(&reason));
    assert!(enabled(
        OrganizerAction::Review,
        corrected,
        app.world().resource::<ObserverSession>()
    ));
    assert_eq!(
        corrected
            .draft
            .as_ref()
            .expect("corrected draft")
            .selected_reference,
        Some(id)
    );
    ordinary(&mut app, OrganizerAction::Review);
    assert!(matches!(app.world().resource::<OrganizerClient>().outbox,
        Some(RuntimeSessionRequest::PreviewOrganizer { ref command, .. })
        if command.choice == OrganizerChoice::RemoteAid && command.allocation == OrganizerAllocation::Aid { food_quantity: 2, cash_micros: 0 }));
}

#[test]
fn keyboard_currency_and_parcel_bounds_use_the_captured_terms_without_clamping() {
    use bevy::input::keyboard::Key;
    let (mut app, window) = allocation_opening();
    ordinary(
        &mut app,
        OrganizerAction::Inspect(OrganizerInspector::Practices),
    );
    ordinary(&mut app, OrganizerAction::Choose(OrganizerChoice::Collect));
    ordinary(
        &mut app,
        OrganizerAction::FocusAmount(AmountField::Contribution),
    );
    for (candidate, valid) in [
        ("1", true),
        ("1450", true),
        ("1451", false),
        ("0", false),
        ("-1", false),
        ("3.5", false),
        ("280", true),
    ] {
        for state in [ButtonState::Pressed, ButtonState::Released] {
            app.world_mut().write_message(KeyboardInput {
                window,
                key_code: KeyCode::ControlLeft,
                logical_key: Key::Control,
                state,
                text: None,
                repeat: false,
            });
            app.update();
            if state == ButtonState::Pressed {
                typing_key(&mut app, window, KeyCode::KeyA, "a");
            }
        }
        typing_key(&mut app, window, KeyCode::Digit1, candidate);
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(AmountField::Contribution.text(client), candidate);
        assert_eq!(
            amount_editor::allocation(client).is_ok(),
            valid,
            "{candidate}"
        );
        assert!(client.outbox.is_none());
    }
    ordinary(
        &mut app,
        OrganizerAction::Inspect(OrganizerInspector::Practices),
    );
    ordinary(&mut app, OrganizerAction::Choose(OrganizerChoice::LocalAid));
    ordinary(&mut app, OrganizerAction::FocusAmount(AmountField::Food));
    typing_key(&mut app, window, KeyCode::Backspace, "");
    typing_key(&mut app, window, KeyCode::Digit4, "4");
    assert!(amount_editor::allocation(app.world().resource::<OrganizerClient>()).is_ok());
    typing_key(&mut app, window, KeyCode::Digit5, "5");
    assert!(amount_editor::allocation(app.world().resource::<OrganizerClient>()).is_err());
    assert_eq!(
        app.world()
            .resource::<OrganizerClient>()
            .draft
            .as_ref()
            .expect("last valid basket")
            .aid_allocation,
        OrganizerAllocation::Aid {
            food_quantity: 4,
            cash_micros: 0
        }
    );
}

fn single_leg_opening(capture: &str, choice: OrganizerChoice) -> (App, Entity) {
    use serde_json::Value;
    let raw: Value = serde_json::from_str(capture).expect("producer");
    let snapshot = serde_json::from_value(raw["snapshot"].clone()).expect("snapshot");
    let (mut app, window, _, _) = focused_organizer(false);
    install_captured_opening(&mut app, snapshot);
    app.update();
    ordinary(
        &mut app,
        OrganizerAction::Inspect(OrganizerInspector::Practices),
    );
    ordinary(&mut app, OrganizerAction::Choose(choice));
    (app, window)
}

fn replace_digit(app: &mut App, window: Entity, field: AmountField, value: &str) {
    use bevy::input::keyboard::Key;
    use bevy::input::ButtonState;
    ordinary(app, OrganizerAction::FocusAmount(field));
    for state in [ButtonState::Pressed, ButtonState::Released] {
        app.world_mut().write_message(KeyboardInput {
            window,
            key_code: KeyCode::ControlLeft,
            logical_key: Key::Control,
            state,
            text: None,
            repeat: false,
        });
        app.update();
        if state == ButtonState::Pressed {
            typing_key(app, window, KeyCode::KeyA, "a");
        }
    }
    typing_key(app, window, KeyCode::Digit1, value);
}

#[test]
fn repaired_positive_absent_leg_blocks_review_and_zero_unselected_leg_allows_it() {
    for (capture, choice, absent, reason) in [
        (
            include_str!("../../../babylon-persistence/tests/fixtures/food_only_no_payer_v19.json"),
            OrganizerChoice::LocalAid,
            AmountField::Cash,
            "cash payer",
        ),
        (
            include_str!("../../../babylon-persistence/tests/fixtures/cash_only_no_food_v19.json"),
            OrganizerChoice::RemoteAid,
            AmountField::Food,
            "food terms",
        ),
    ] {
        let (mut app, window) = single_leg_opening(capture, choice);
        if absent == AmountField::Food {
            replace_digit(&mut app, window, AmountField::Cash, "1");
        }
        replace_digit(&mut app, window, absent, "1");
        let client = app.world().resource::<OrganizerClient>();
        assert!(
            client.message.to_lowercase().contains(reason),
            "{}",
            client.message
        );
        assert!(!enabled(
            OrganizerAction::Review,
            client,
            app.world().resource::<ObserverSession>()
        ));
        ordinary(&mut app, OrganizerAction::Review);
        let client = app.world().resource::<OrganizerClient>();
        assert!(
            client.message.to_lowercase().contains(reason),
            "{:?}: {}",
            absent,
            client.message
        );
        assert_ne!(client.inspector, OrganizerInspector::Review);
        assert!(client.outbox.is_none());
        replace_digit(&mut app, window, absent, "0");
        ordinary(&mut app, OrganizerAction::Review);
        assert!(matches!(
            app.world().resource::<OrganizerClient>().outbox,
            Some(RuntimeSessionRequest::PreviewOrganizer { .. })
        ));
    }
}

#[test]
fn private_payers_review_the_same_basket_with_identical_terms_and_controls() {
    use babylon_practice_contract::{OrganizerConfig, OrganizerState};
    #[derive(serde::Deserialize)]
    struct Pair {
        config: OrganizerConfig,
        state: OrganizerState,
        openings: [OrganizerSnapshot; 2],
    }
    let pair: Pair = serde_json::from_str(include_str!(
        "../../tests/fixtures/wayne_private_funding_v19.json"
    ))
    .expect("independently captured public openings");
    let [low, high] = pair.openings.map(|opening| {
        let (mut app, window, _, _) = focused_organizer(false);
        install_captured_opening(&mut app, opening);
        app.update();
        ordinary(
            &mut app,
            OrganizerAction::Inspect(OrganizerInspector::Practices),
        );
        ordinary(&mut app, OrganizerAction::Choose(OrganizerChoice::LocalAid));
        replace_digit(&mut app, window, AmountField::Food, "0");
        let reviewable = enabled(
            OrganizerAction::Review,
            app.world().resource::<OrganizerClient>(),
            app.world().resource::<ObserverSession>(),
        );
        assert!(reviewable);
        ordinary(&mut app, OrganizerAction::Review);
        app.world_mut()
            .resource_scope(|world, mut client: Mut<OrganizerClient>| {
                let Some(RuntimeSessionRequest::PreviewOrganizer {
                    request_id,
                    command,
                    ..
                }) = client.outbox.take()
                else {
                    panic!("ordinary player Review")
                };
                assert_eq!(
                    command.allocation,
                    OrganizerAllocation::Aid {
                        food_quantity: 0,
                        cash_micros: 3_000_000
                    }
                );
                let ruling = babylon_practice_contract::preview_organizer(
                    &pair.config,
                    &pair.state,
                    &command,
                )
                .expect("authenticated Review");
                assert!(ruling.refusal.is_none());
                client
                    .previewed(
                        request_id,
                        ruling,
                        &mut world.resource_mut::<ObserverSession>(),
                    )
                    .expect("matching Review reply");
            });
        app.update();
        let review = painted_text(&mut app, false);
        let detail = painted_text(&mut app, true);
        let painted = format!("{review}\n{detail}");
        assert!(
            painted.contains("Selected: 0 food parcels and $3.00"),
            "{painted}"
        );
        assert!(painted.contains("payer balance is private"), "{painted}");
        assert!(confirmation_enabled(&app));
        let world = app.world_mut();
        let mut controls = world.query::<(&ActionButton, &Node, &UiGlobalTransform)>();
        let mut buttons = controls
            .iter(world)
            .map(|(action, node, transform)| {
                (
                    format!("{:?}", action.0),
                    node.clone(),
                    transform.affine().to_cols_array(),
                    enabled(
                        action.0,
                        world.resource::<OrganizerClient>(),
                        world.resource::<ObserverSession>(),
                    ),
                )
            })
            .collect::<Vec<_>>();
        buttons.sort_by(|a, b| a.0.cmp(&b.0));
        assert!(controls
            .iter(world)
            .any(|(button, _, _)| button.0 == OrganizerAction::Confirm));
        (review, detail, buttons, relationship_targets(&mut app))
    });
    assert_eq!(low, high);
}

fn two_cap_opening() -> (
    babylon_practice_contract::OrganizerConfig,
    OrganizerSnapshot,
) {
    use babylon_practice_contract::OrganizerConfig;
    #[derive(serde::Deserialize)]
    struct CapturedOpening {
        config: OrganizerConfig,
        snapshot: OrganizerSnapshot,
    }
    let CapturedOpening {
        config: cfg,
        snapshot,
    } = serde_json::from_str(include_str!(
        "../../tests/fixtures/wayne_two_cap_opening_v19.json"
    ))
    .expect("opening captured from the admitted material register");
    for (kind, cap) in [(OrganizerAidKind::Local, 2), (OrganizerAidKind::Remote, 4)] {
        let binding = cfg
            .aid_bindings
            .iter()
            .find(|binding| binding.kind == kind)
            .expect("configured recipient");
        assert_eq!(binding.maximum_food_quantity, cap);
        let material = snapshot
            .aid
            .iter()
            .find(|terms| terms.kind == kind)
            .expect("disclosed material mandate");
        assert_eq!(
            (
                material.mandate_id,
                material.recipient_actor_id,
                material.maximum_quantity
            ),
            (binding.mandate_id, binding.partner.actor_id, cap)
        );
    }
    (cfg, snapshot)
}

#[test]
fn repaired_recipient_switch_reconciles_valid_raw_basket_with_cards_and_original_command() {
    use babylon_practice_contract::OrganizerPeriodJournal;
    let (cfg, snapshot) = two_cap_opening();
    let state = babylon_practice_contract::initial_organizer_state(&cfg)
        .expect("valid two-cap configuration");
    let mut disclosed = babylon_practice_contract::organizer_view(
        &cfg,
        &state,
        &OrganizerPeriodJournal::empty(),
        cfg.controlled_actor_id,
    )
    .expect("authenticated view");
    // The runtime additionally decorates the public workplace contact on this view.
    disclosed.public_workplace_contact = snapshot.view.public_workplace_contact;
    assert_eq!(snapshot.view, disclosed);
    let (mut app, window, _, _) = focused_organizer(false);
    install_captured_opening(&mut app, snapshot);
    app.update();
    ordinary(
        &mut app,
        OrganizerAction::Inspect(OrganizerInspector::Practices),
    );
    ordinary(&mut app, OrganizerAction::Choose(OrganizerChoice::LocalAid));
    replace_digit(&mut app, window, AmountField::Food, "3");
    assert!(amount_editor::allocation(app.world().resource::<OrganizerClient>()).is_err());
    ordinary(
        &mut app,
        OrganizerAction::Choose(OrganizerChoice::RemoteAid),
    );
    let basket = OrganizerAllocation::Aid {
        food_quantity: 3,
        cash_micros: 0,
    };
    let client = app.world().resource::<OrganizerClient>();
    assert_eq!(amount_editor::allocation(client), Ok(basket));
    assert_eq!(
        client
            .draft
            .as_ref()
            .expect("captured personal draft")
            .aid_allocation,
        basket,
        "retained personal basket"
    );
    let session = app.world().resource::<ObserverSession>();
    let pair = workspace::comparison(client, session).expect("live comparison");
    assert!(pair
        .alternatives
        .iter()
        .all(|card| card.allocation == basket));
    ordinary(&mut app, OrganizerAction::Review);
    let command = app
        .world_mut()
        .resource_scope(|world, mut client: Mut<OrganizerClient>| {
            let Some(RuntimeSessionRequest::PreviewOrganizer {
                request_id,
                command,
                ..
            }) = client.outbox.take()
            else {
                panic!("ordinary Review request")
            };
            assert_eq!(command.allocation, basket);
            let preview = babylon_practice_contract::preview_organizer(&cfg, &state, &command)
                .expect("real mandate preview");
            assert_eq!(preview.allocation, basket);
            assert!(preview.refusal.is_none());
            client
                .previewed(
                    request_id,
                    preview,
                    &mut world.resource_mut::<ObserverSession>(),
                )
                .expect("matching authenticated preview");
            command
        });
    app.world_mut()
        .resource_mut::<OrganizerClient>()
        .draft_dirty = false;
    ordinary(&mut app, OrganizerAction::Confirm);
    let accepted =
        babylon_practice_contract::admit_organizer(&cfg, &state, &command).expect("real admission");
    assert!(
        matches!(&app.world().resource::<OrganizerClient>().outbox,Some(RuntimeSessionRequest::SubmitOrganizer{command:submitted,..}) if *submitted==accepted.command)
    );
}
