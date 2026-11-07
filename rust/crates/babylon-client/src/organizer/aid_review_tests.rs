use babylon_persistence::runtime_session::{
    OrganizerAidFoodPreview, OrganizerCollectionPreview, OrganizerCommitment,
};
fn aid_review_fixture(kind: OrganizerAidKind, label: &str, active: bool) -> App {
    use babylon_persistence::runtime_session::{
        OrganizerAidOption, OrganizerAidRouteStage, OrganizerAidTransportPreview,
        OrganizerMaterialAidPreview,
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
            payer_cash: Some(120),
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
    assert!(
        painted_text(&mut app, false)
            .to_lowercase()
            .contains("protected consumption")
    );
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
