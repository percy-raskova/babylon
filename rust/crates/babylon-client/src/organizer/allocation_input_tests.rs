pub(crate) fn install_national_opening(app: &mut App) {
    use babylon_persistence::runtime_session::{OrganizerBodySource, OrganizerSnapshot};
    let snapshot: OrganizerSnapshot = serde_json::from_str(include_str!(
        "../../../babylon-persistence/tests/fixtures/national_organizer_opening_v18.json"
    ))
    .expect("national opening");
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
    let collection = snapshot.collection.as_ref().expect("opening terms");
    let aid = &snapshot.aid[0];
    client.draft = Some(OrganizerDraft::new(
        snapshot.view.workplace_id,
        OrganizerAllocation::Collection {
            target_cash_micros: collection.initial_cash_micros,
        },
        OrganizerAllocation::Aid {
            food_quantity: aid.initial_food_quantity,
            cash_micros: aid.initial_cash_micros,
        },
    ));
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
    assert!(
        app.world()
            .resource::<OrganizerClient>()
            .message
            .contains("whole number")
    );
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
    let (mut app, _) = allocation_opening();
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
