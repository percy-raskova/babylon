use babylon_persistence::runtime_session::{
    OrganizerAidFoodPreview, OrganizerCollectionPreview, OrganizerCommitment,
};

#[test]
fn aid_map_frames_the_disclosed_counties_and_opens_the_selected_recipients_offer() {
    use crate::observer_map3d::FrameOrganizerCounties;

    #[derive(Resource, Default)]
    struct Framed(Vec<Vec<String>>);
    let (mut app, _) = allocation_opening();
    {
        let world = app.world_mut();
        let dock = world
            .query::<(&ActionButton, &ChildOf)>()
            .iter(world)
            .find_map(|(button, parent)| {
                (button.0 == OrganizerAction::ShowAidPartners).then_some(parent.parent())
            })
            .expect("Places dock");
        assert!(world
            .get::<crate::observer_map3d::symbols::MapObstruction>(dock)
            .is_some());
        assert!(world.get::<Visibility>(dock).is_some());
    }
    app.init_resource::<Framed>().add_observer(
        |event: On<FrameOrganizerCounties>, mut frames: ResMut<Framed>| {
            frames
                .0
                .push(event.0.iter().map(ToString::to_string).collect());
        },
    );
    let (recipient, previous_choice) = {
        let client = app.world().resource::<OrganizerClient>();
        let partner = client
            .known_aid_partners(app.world().resource::<ObserverSession>())
            .iter()
            .find(|partner| partner.kind == OrganizerAidKind::Remote)
            .expect("known remote partner");
        (partner.actor_id, client.choice())
    };
    ordinary(&mut app, OrganizerAction::ShowAidPartners);
    assert_eq!(app.world().resource::<Framed>().0[0], ["26163", "17031"]);
    let session = app.world().resource::<ObserverSession>();
    let marker = OrganizerAction::Follow(DatedLink::new(
        session,
        session.viewed_tick,
        Destination::Subject(OrganizerSubject::AidPartner(recipient)),
    ));
    ordinary(&mut app, marker);
    let cook = app
        .world()
        .resource::<CountyAtlas>()
        .index_of_fips("17031")
        .expect("Cook County in atlas");
    assert_eq!(app.world().resource::<SelectedCounty>().0, Some(cook));
    assert_eq!(app.world().resource::<Framed>().0[1], ["17031"]);
    assert_eq!(
        app.world().resource::<OrganizerClient>().choice(),
        previous_choice,
        "inspecting preserves the draft"
    );
    ordinary(&mut app, OrganizerAction::PreparePartnerOffer);
    assert_eq!(
        app.world().resource::<OrganizerClient>().choice(),
        OrganizerChoice::RemoteAid
    );
    let workplace = app
        .world()
        .resource::<OrganizerClient>()
        .view
        .as_ref()
        .expect("admitted view")
        .workplace_id;
    ordinary(
        &mut app,
        OrganizerAction::SelectSubject(OrganizerSubject::Workplace(workplace)),
    );
    assert_eq!(
        app.world().resource::<Framed>().0[2],
        ["26163"],
        "selecting the local workplace after Cook reframes Wayne"
    );
    app.world_mut().resource_mut::<ObserverSession>().generation += 1;
    app.world_mut()
        .resource_mut::<OrganizerClient>()
        .selected_subject = None;
    ordinary(&mut app, marker);
    assert!(
        app.world()
            .resource::<OrganizerClient>()
            .selected_subject
            .is_none(),
        "old marker clicks cannot open a new session's dossier"
    );
    ordinary(&mut app, OrganizerAction::ShowAidPartners);
    assert_eq!(
        app.world().resource::<Framed>().0.len(),
        3,
        "stale disclosure cannot frame partner locations"
    );
}

#[test]
fn aid_cards_show_what_each_partner_shared_before_choosing_a_gift() {
    use babylon_persistence::runtime_session::{OrganizerPartnerFacts, OrganizerReport};

    let (mut app, _) = allocation_opening();
    ordinary(
        &mut app,
        OrganizerAction::Inspect(OrganizerInspector::Practices),
    );
    assert!(panel_has_visible_text(
        &mut app,
        true,
        "Wayne Local Aid Partners\nP0 pantry report · 0 parcels on hand, 4 needed"
    ));
    ordinary(
        &mut app,
        OrganizerAction::Choose(OrganizerChoice::RemoteAid),
    );
    assert!(panel_has_visible_text(&mut app, false,
        "Cook Independent Solidarity Partners · freight · delay and loss possible\nP0 pantry report · 0 parcels on hand, 4 needed\n1 parcel + $0.00"));

    let (local, remote) = install_dated_food_reports(&mut app);
    app.update();
    assert!(panel_has_visible_text(&mut app, false,
        "Wayne Local Aid Partners · local handoff\nP2 food report (received P3) · ate 0 of 4 parcels needed"));
    assert!(panel_has_visible_text(&mut app, false,
        "Cook Independent Solidarity Partners · freight · delay and loss possible\nP3 food report · ate 4 of 4 parcels needed"));

    let mut client = app.world_mut().resource_mut::<OrganizerClient>();
    let view = client.view.as_mut().expect("admitted view");
    for row in view
        .observations
        .iter_mut()
        .filter(|r| r.subject_id == remote)
    {
        let OrganizerReport::Partner { facts, .. } = &mut row.report else {
            continue;
        };
        match (row.observed_period, facts) {
            (0, OrganizerPartnerFacts::OpeningAssessment { commodity, .. }) => {
                commodity.good_id = [99; 32];
            }
            (1, OrganizerPartnerFacts::FoodProvision { commodity, .. }) => {
                commodity.unit_id = [99; 32];
            }
            (2, _) => row.actor_id = remote,
            (3, _) => row.source_actor_id = local,
            _ => {}
        }
    }
    app.update();
    assert!(panel_has_visible_text(&mut app, false,
        "Cook Independent Solidarity Partners · freight · delay and loss possible\nNo food report available."));
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .viewed_tick = 1;
    app.update();
    assert!(!panel_has_visible_text(&mut app, false, "P2 food report"));
}

fn install_dated_food_reports(app: &mut App) -> (u64, u64) {
    use babylon_persistence::runtime_session::{
        OrganizerPartnerFacts, OrganizerReport, OrganizerView,
    };

    #[derive(serde::Deserialize)]
    struct Period {
        view: OrganizerView,
    }

    let periods: Vec<Period> = serde_json::from_str(include_str!(
        "../../tests/fixtures/wayne_public_developments_v20.json"
    ))
    .expect("completed Wayne and Cook disclosures");
    let mut view = periods.into_iter().last().expect("period three").view;
    let local = view
        .aid_options
        .iter()
        .find(|o| o.kind == OrganizerAidKind::Local)
        .expect("local recipient")
        .partner_actor_id;
    let remote = view
        .aid_options
        .iter()
        .find(|o| o.kind == OrganizerAidKind::Remote)
        .expect("remote recipient")
        .partner_actor_id;
    // Wayne's P3 report arrives next period. Its P2 report arrived this period.
    // Cook shared the distinct synthetic case of every required parcel eaten.
    for row in &mut view.observations {
        if let OrganizerReport::Partner {
            facts:
                OrganizerPartnerFacts::FoodProvision {
                    required,
                    consumed,
                    unmet,
                    ..
                },
            ..
        } = &mut row.report
        {
            if row.subject_id == local && row.observed_period >= 2 {
                row.acquired_period = row.observed_period + 1;
            } else if row.subject_id == remote && row.observed_period == 3 {
                *consumed = *required;
                *unmet = 0;
            }
        }
    }
    {
        let mut client = app.world_mut().resource_mut::<OrganizerClient>();
        for terms in &mut client.aid {
            terms.period = view.period;
        }
        client.view = Some(view);
    }
    {
        let mut session = app.world_mut().resource_mut::<ObserverSession>();
        session.viewed_tick = 3;
        session.durable_tick = 3;
    }
    (local, remote)
}

#[test]
fn aid_cards_wait_for_current_terms_after_advancing_past_the_installed_view() {
    let (mut app, _) = allocation_opening();
    ordinary(
        &mut app,
        OrganizerAction::Inspect(OrganizerInspector::Practices),
    );
    install_dated_food_reports(&mut app);
    app.update();
    assert!(panel_has_visible_text(
        &mut app,
        true,
        "Recipient: Wayne Local Aid Partners\nP2 food report"
    ));

    let mut session = app.world_mut().resource_mut::<ObserverSession>();
    session.viewed_tick = 4;
    session.durable_tick = 4;
    app.update();
    assert!(!panel_has_visible_text(
        &mut app,
        true,
        "Recipient: Wayne Local Aid Partners"
    ));
    assert!(panel_has_visible_text(
        &mut app,
        true,
        "Awaiting current terms"
    ));
}

fn aid_review_fixture(kind: OrganizerAidKind, label: &str, active: bool) -> App {
    use babylon_persistence::runtime_session::{
        OrganizerAidFunding, OrganizerAidOption, OrganizerAidRouteStage,
        OrganizerAidTransportPreview, OrganizerMaterialAidPreview,
    };
    let (mut app, _) = admitted_scene_fixture();
    {
        let mut client = app.world_mut().resource_mut::<OrganizerClient>();
        let view = client.view.as_mut().expect("view");
        view.standing.authorized = active;
        view.aid_options.push(OrganizerAidOption {
            kind,
            partner_actor_id: 95,
            partner_label: label.into(),
            coordination_hours: 3,
            receiving_consent: OrganizerGiftConsent::Accept,
        });
        client.aid.push(OrganizerMaterialAidPreview {
            initial_food_quantity: 1,
            initial_cash_micros: 0,
            cash_receiving_consent: OrganizerGiftConsent::Accept,
            kind,
            mandate_id: [1; 32],
            period: 3,
            donor_id: [2; 32],
            recipient_actor_id: 95,
            good_id: [4; 32],
            unit_id: [5; 32],
            food: Some(OrganizerAidFoodPreview {
                donor_stock: 12,
                own_need: 4,
                grams_per_unit: 1000,
                ordinary_offer: None,
                labor_unit_id: [6; 32],
                fulfillment_hours_per_unit: 2,
                time: None,
                transport: if kind == OrganizerAidKind::Local {
                    OrganizerAidTransportPreview::Local
                } else {
                    OrganizerAidTransportPreview::Routed {
                        route_id: [7; 32],
                        from_node_id: [8; 32],
                        to_node_id: [9; 32],
                        stages: vec![OrganizerAidRouteStage {
                            stage_index: 0,
                            from_node_id: [8; 32],
                            to_node_id: [9; 32],
                            travel_periods: 2,
                            loss_ppm: 0,
                            departure_period: 4,
                            capacities: vec![],
                        }],
                    }
                },
            }),
            funding: OrganizerAidFunding::Organization { cash_micros: 120 },
            maximum_quantity: 8,
            maximum_cash_micros: 10,
            coordination_hours: 3,
            receiving_consent: OrganizerGiftConsent::Accept,
        });
        client.draft.as_mut().expect("draft").aid_allocation = OrganizerAllocation::Aid {
            food_quantity: 1,
            cash_micros: 0,
        };
    }
    app
}

fn assert_aid_review_attribution_and_acceptance(app: &mut App, label: &str) {
    {
        let mut client = app.world_mut().resource_mut::<OrganizerClient>();
        let options = &mut client.view.as_mut().expect("view").aid_options;
        options.push(options[0].clone());
    }
    app.update();
    let ambiguous = painted_text(app, false);
    assert!(
        ambiguous.contains("Recipient attribution unavailable"),
        "{ambiguous}"
    );
    assert!(!ambiguous.contains(label), "{ambiguous}");
    assert!(ambiguous.contains("cannot be confirmed"), "{ambiguous}");
    assert!(!confirmation_enabled(app));
    app.world_mut()
        .resource_mut::<OrganizerClient>()
        .view
        .as_mut()
        .expect("view")
        .aid_options
        .pop();
    app.update();
    assert!(confirmation_enabled(app));
    {
        let mut client = app.world_mut().resource_mut::<OrganizerClient>();
        client.commitment = Some(OrganizerCommitment {
            command: client.reviewed_command.clone().expect("reviewed command"),
            resolves_period: 4,
            commitment_id: [8; 32],
        });
    }
    app.update();
    let accepted = painted_text(app, false);
    assert!(
        accepted.contains(label) && accepted.contains("8 food units"),
        "{accepted}"
    );
    app.world_mut().resource_mut::<OrganizerClient>().aid[0].period = 2;
    app.update();
    let stale = painted_text(app, false);
    assert!(stale.contains("UNAVAILABLE"), "{stale}");
    assert!(!stale.contains(label), "{stale}");
}

#[test]
fn aid_review_names_captured_terms_and_routine_after_selection_changes() {
    for (choice, kind, label, button_label) in [
        (
            OrganizerChoice::LocalAid,
            OrganizerAidKind::Local,
            "Fixture local recipient",
            "Organize local aid",
        ),
        (
            OrganizerChoice::RemoteAid,
            OrganizerAidKind::Remote,
            "Fixture remote recipient",
            "Organize remote solidarity",
        ),
    ] {
        for active in [true, false] {
            let mut app = aid_review_fixture(kind, label, active);
            press_named(&mut app, button_label);
            assert_eq!(app.world().resource::<OrganizerClient>().choice(), choice);
            review_selected(&mut app);
            {
                let mut client = app.world_mut().resource_mut::<OrganizerClient>();
                let preview = client.preview.as_mut().expect("review");
                preview.required_hours = 3;
                preview.replaces_standing_work = active;
            }
            app.world_mut()
                .write_message(OrganizerAction::SelectSubject(
                    OrganizerSubject::NeighborhoodGroup(93),
                ));
            app.update();
            let review = painted_text(&mut app, false);
            for term in [
                label,
                "8 food units",
                "Independent cash cap: $0.00001 currency",
                "0.00012 currency",
                "2 household hours",
                "3 hours",
            ] {
                assert!(review.contains(term), "missing {term:?}: {review}");
            }
            assert!(review.contains("consent: accepted"), "{review}");
            assert!(
                review.contains("material resolution") && review.contains("period 4"),
                "{review}"
            );
            assert!(
                review.contains("no cash, food, freight or time is reserved"),
                "{review}"
            );
            assert!(
                review.contains(if active {
                    "Replaces neighborhood work once"
                } else {
                    "neighborhood routine remains paused"
                }),
                "{review}"
            );
            assert!(
                review.contains("separate") && review.contains("independent"),
                "{review}"
            );
            assert!(!review.contains("card above"), "{review}");
            assert_eq!(
                app.world().resource::<OrganizerClient>().selected_subject,
                Some(OrganizerSubject::NeighborhoodGroup(93))
            );
            assert_aid_review_attribution_and_acceptance(&mut app, label);
        }
    }
}

#[test]
fn collection_review_names_captured_gift_and_paused_or_displaced_routine() {
    for active in [true, false] {
        let (mut app, _) = admitted_scene_fixture();
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            client.view.as_mut().expect("view").standing.authorized = active;
            client.collection = Some(OrganizerCollectionPreview {
                period: 3,
                mandate_id: [8; 32],
                actor_id: 90,
                contributor_id: 1,
                contributor_label: "Fixture contributor".into(),
                source_hash: [16; 32],
                cash_consent: OrganizerGiftConsent::Accept,
                initial_cash_micros: 280_000_000,
                maximum_cash_micros: 280_000_000,
                protected_cash_floor_micros: 0,
                collection_hours: 2,
                organization_cash_micros: 1_000_000,
            });
        }
        press_named(&mut app, "Collect a voluntary contribution");
        review_selected(&mut app);
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            let preview = client.preview.as_mut().expect("review");
            preview.required_hours = 2;
            preview.available_hours = 7;
            preview.replaces_standing_work = active;
        }
        app.world_mut()
            .write_message(OrganizerAction::SelectSubject(
                OrganizerSubject::NeighborhoodGroup(93),
            ));
        app.update();
        let review = painted_text(&mut app, false);
        for term in [
            "Fixture contributor",
            "up to $280.00 currency",
            "2 shared material hours",
            "consent: accepted",
            "Protected consumption",
            "If a fully funded essential need remains unmet, the household keeps its refund",
            "An unmet service without full funding blocks the gift",
            "No cash or time is reserved",
            "period 4",
        ] {
            assert!(review.contains(term), "missing {term:?}: {review}");
        }
        assert!(
            !review.contains("Cost: 2 of 7 organizer-hours"),
            "shared material work must not be divided by organizer pledges: {review}"
        );
        assert!(
            review.contains(if active {
                "Replaces neighborhood work once"
            } else {
                "neighborhood routine remains paused"
            }),
            "{review}"
        );
        assert_eq!(
            app.world().resource::<OrganizerClient>().selected_subject,
            Some(OrganizerSubject::NeighborhoodGroup(93))
        );
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            client.commitment = Some(OrganizerCommitment {
                command: client.reviewed_command.clone().expect("reviewed command"),
                resolves_period: 4,
                commitment_id: [8; 32],
            });
        }
        app.update();
        let accepted = painted_text(&mut app, false);
        assert!(
            accepted.contains("Fixture contributor") && accepted.contains("up to $280.00 currency"),
            "{accepted}"
        );
        assert!(
            accepted.contains(if active {
                "Replaces neighborhood work once"
            } else {
                "neighborhood routine remains paused"
            }),
            "{accepted}"
        );
    }
}

#[test]
fn native_collection_card_is_reachable_and_history_navigation_cannot_act() {
    let (mut app, _) = reviewed_period_three();
    {
        let mut client = app.world_mut().resource_mut::<OrganizerClient>();
        client.clear_review();
        client
            .draft
            .as_mut()
            .expect("personal draft")
            .collection_allocation = OrganizerAllocation::Collection {
            target_cash_micros: 280_000_000,
        };
        client.collection = Some(OrganizerCollectionPreview {
            period: 3,
            mandate_id: [8; 32],
            actor_id: client
                .view
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .actor_id,
            contributor_id: 1,
            contributor_label: "Fixture contributor".into(),
            source_hash: [16; 32],
            cash_consent: OrganizerGiftConsent::Accept,
            initial_cash_micros: 280_000_000,
            maximum_cash_micros: 280_000_000,
            protected_cash_floor_micros: 0,
            collection_hours: 2,
            organization_cash_micros: 1_000_000,
        });
    }
    app.update();
    press_named(&mut app, "All practices");
    assert_eq!(
        app.world().resource::<OrganizerClient>().inspector,
        OrganizerInspector::Practices
    );
    press_named(&mut app, "Collect a voluntary contribution");
    assert_eq!(
        app.world().resource::<OrganizerClient>().choice(),
        OrganizerChoice::Collect
    );
    let card = app
        .world_mut()
        .query::<(&TextPart, &Text)>()
        .iter(app.world())
        .find_map(|(part, text)| {
            matches!(part, TextPart::Approach(OrganizerChoice::Collect)).then(|| text.0.clone())
        })
        .expect("the fixture yields the searched value");
    assert!(card.contains("up to $280.00 currency; 2 shared material hours"));
    assert!(card.contains(
        "If a fully funded essential need remains unmet, the household keeps its refund"
    ));
    review_selected(&mut app);
    // Paint the reviewed model before inspecting the actual native text.
    app.update();
    assert!(confirmation_enabled(&app));
    assert!(painted_text(&mut app, false)
        .to_lowercase()
        .contains("protected consumption"));
    inspect_period(&mut app, 2);
    app.update();
    assert!(!confirmation_enabled(&app));
    press_named(&mut app, "Confirm ruling");
    assert!(app.world().resource::<OrganizerClient>().outbox.is_none());
    press_named(&mut app, "Practice history");
    assert_eq!(
        app.world().resource::<OrganizerClient>().inspector,
        OrganizerInspector::Receipts
    );
    press_named(&mut app, "Our practice Archive");
    assert_eq!(
        app.world().resource::<ArchiveRequests>().0,
        [OrganizerArchiveTarget::Collective]
    );
    assert!(app.world().resource::<OrganizerClient>().outbox.is_none());
}

#[test]
fn pending_route_navigation_keeps_the_draft_and_pause_needs_its_own_review() {
    let mut app = aid_review_fixture(OrganizerAidKind::Remote, "Remote recipient", true);
    let mut snapshot: OrganizerSnapshot = serde_json::from_str(include_str!(
        "../../../babylon-persistence/tests/fixtures/national_organizer_pending_v20.json"
    ))
    .expect("actual pending remote support");
    {
        let mut client = app.world_mut().resource_mut::<OrganizerClient>();
        client.pending_aid.push(snapshot.pending_aid.remove(0));
        let draft = client.draft.as_mut().expect("saved draft");
        draft.choice = OrganizerChoice::RemoteAid;
        draft.aid_allocation = OrganizerAllocation::Aid {
            food_quantity: 2,
            cash_micros: 7,
        };
    }
    app.update();
    let before = app.world().resource::<OrganizerClient>().draft.clone();
    {
        let client = app.world().resource::<OrganizerClient>();
        let session = app.world().resource::<ObserverSession>();
        assert!(
            !enabled(OrganizerAction::Review, client, session),
            "only the pending route remains blocked"
        );
        assert!(!confirmation_enabled(&app));
    }
    press_named(&mut app, "Direction / routine");
    assert_eq!(
        app.world().resource::<OrganizerClient>().inspector,
        OrganizerInspector::Direction
    );
    assert_eq!(
        app.world().resource::<OrganizerClient>().draft,
        before,
        "navigation preserves draft and amounts"
    );
    press_named(&mut app, "Pause neighborhood work");
    {
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.choice(), OrganizerChoice::PauseStanding);
        assert_eq!(
            client.draft.as_ref().expect("draft").aid_allocation,
            before.as_ref().expect("prior draft").aid_allocation
        );
        assert!(
            client.commitment.is_none() && client.pending.is_none(),
            "choosing Pause submits nothing"
        );
        assert!(
            !confirmation_enabled(&app),
            "authenticated Review is still required"
        );
    }
    press_named(&mut app, "Review choice");
    app.world_mut()
        .resource_scope(|world, mut client: Mut<OrganizerClient>| {
            let Some(RuntimeSessionRequest::PreviewOrganizer {
                request_id,
                command,
                ..
            }) = client.outbox.take()
            else {
                panic!("Review requests an authenticated preview");
            };
            let mut session = world.resource_mut::<ObserverSession>();
            client
                .previewed(request_id, preview_for(&command), &mut session)
                .expect("matching authenticated preview reply");
        });
    app.update();
    assert!(confirmation_enabled(&app));
    assert!(
        app.world()
            .resource::<OrganizerClient>()
            .commitment
            .is_none(),
        "Review does not Confirm"
    );
    press_named(&mut app, "Confirm ruling");
    let client = app.world().resource::<OrganizerClient>();
    assert!(
        client
            .pending
            .as_ref()
            .is_some_and(|pending| pending.kind == RequestKind::Submit),
        "Confirm alone requests durable admission"
    );
    assert!(
        client.commitment.is_none(),
        "no acceptance is invented before runtime replies"
    );
    assert_eq!(
        app.world().resource::<ObserverSession>().durable_tick,
        3,
        "navigation, Review and Confirm never Advance"
    );
}
