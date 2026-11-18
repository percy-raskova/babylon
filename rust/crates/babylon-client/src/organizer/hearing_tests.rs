//! Native hearing choices and their dated reports.
use super::super::workspace::DispatchDestination;
use super::super::workspace_copy::{DatedLink, Destination};
use super::super::{client, hearing, OrganizerClient, OrganizerInspector};
use super::{tests, OrganizerAction};
use crate::observer::ObserverSession;
use babylon_persistence::runtime_session::{
    OrganizerAidKind, OrganizerAllocation, OrganizerChoice, RuntimeSessionRequest,
};
use bevy::prelude::Mut;

#[test]
fn hearing_notice_orders_reviewed_terms_and_reports_only_the_committed_period() {
    use babylon_persistence::runtime_session::{
        OrganizerHearingDelegation, OrganizerHearingMandate, OrganizerHearingNotice,
        OrganizerHearingOffer, OrganizerHearingOutcome, OrganizerHearingReceipt,
        OrganizerHearingResponse, OrganizerHearingReview, OrganizerHearingSeat,
        OrganizerHearingTestimony, OrganizerKnownAidPartner,
    };
    let (mut app, _) = tests::admitted_scene_fixture();
    {
        let mut session = app.world_mut().resource_mut::<ObserverSession>();
        session.ready(1, None);
        let context = session.context();
        assert!(session.installed(&context));
    }
    let claimant = OrganizerHearingSeat {
        actor_id: 93,
        authority_id: [1; 16],
        label: "Standing claimant".into(),
        claim: "Keep the existing distribution point".into(),
        delegation: OrganizerHearingDelegation {
            delegate_label: "Claimants’ delegate".into(),
            authorizing_households: 2,
        },
        response: OrganizerHearingResponse::Attended,
        mandate: Some(OrganizerHearingMandate::Settle(
            OrganizerHearingOffer::JointMinutes,
        )),
    };
    let partner = OrganizerHearingSeat {
        actor_id: 95,
        authority_id: [2; 16],
        label: "Wayne Local Aid Partners".into(),
        claim: "Hear the residents excluded from distribution".into(),
        delegation: OrganizerHearingDelegation {
            delegate_label: "Relief group delegate".into(),
            authorizing_households: 3,
        },
        response: OrganizerHearingResponse::Attended,
        mandate: Some(OrganizerHearingMandate::Settle(
            OrganizerHearingOffer::JointMinutes,
        )),
    };
    {
        let mut client = app.world_mut().resource_mut::<OrganizerClient>();
        let view = client.view.as_mut().expect("fixture status");
        view.period = 1;
        view.aid_partners.push(OrganizerKnownAidPartner {
            kind: OrganizerAidKind::Local,
            actor_id: partner.actor_id,
            label: partner.label.clone(),
            location: None,
        });
        view.hearing = Some(OrganizerHearingNotice {
            county_geoid: "26163".into(),
            period: 2,
            review_period: 3,
            claimant_actor_id: claimant.actor_id,
            claimant_label: claimant.label.clone(),
            claimant_claim: claimant.claim.clone(),
            claimant_delegation: claimant.delegation.clone(),
            partner_delegation: partner.delegation.clone(),
            partner_claim: partner.claim.clone(),
            attendance_hours: 3,
        });
        view.hearing_receipt = Some(OrganizerHearingReceipt {
            receipt_id: [21; 32],
            county_geoid: "26163".into(),
            invitation_commitment_id: Some([22; 32]),
            time_use: vec![],
            period: 2,
            review_period: 3,
            offer: Some(OrganizerHearingOffer::JointMinutes),
            review_access_actor_ids: vec![claimant.actor_id, partner.actor_id],
            testimony: [&claimant, &partner]
                .into_iter()
                .map(|seat| OrganizerHearingTestimony {
                    actor_id: seat.actor_id,
                    period: 2,
                    delegate_label: seat.delegation.delegate_label.clone(),
                    claim: seat.claim.clone(),
                })
                .collect(),
            claimant,
            partner,
            outcome: OrganizerHearingOutcome::Settled,
        });
        view.hearing_review = view
            .hearing_receipt
            .as_ref()
            .map(OrganizerHearingReview::from);
    }
    let session = app.world().resource::<ObserverSession>();
    let dated = DatedLink::new(
        session,
        1,
        Destination::Detail(DispatchDestination::Inspector(OrganizerInspector::Hearing)),
    );
    app.world_mut()
        .write_message(OrganizerAction::Follow(dated));
    app.update();
    let notice = tests::painted_text(&mut app, true);
    assert!(notice.contains("Hearing in period 2"));
    assert!(notice.contains("Standing claimant"));
    assert!(notice.contains("authorized by 2 households"));
    assert!(notice.contains("authorized by 3 households"));
    assert!(!notice.contains("Wayne hearing minutes"));
    assert!(!notice.contains("County review report back"));

    tests::press_named(&mut app, "Invite with joint minutes");
    assert_eq!(
        app.world().resource::<OrganizerClient>().choice(),
        OrganizerChoice::InviteToHearing(OrganizerHearingOffer::JointMinutes),
    );
    assert!(app.world().resource::<OrganizerClient>().outbox.is_none());
    tests::press_named(&mut app, "Review choice");
    let client = app.world().resource::<OrganizerClient>();
    assert!(matches!(
        &client.outbox,
        Some(RuntimeSessionRequest::PreviewOrganizer { command, .. })
            if command.choice == OrganizerChoice::InviteToHearing(OrganizerHearingOffer::JointMinutes)
                && command.expected_period == 1
                && command.allocation == OrganizerAllocation::None
    ));

    app.world_mut()
        .resource_scope(|world, mut client: Mut<OrganizerClient>| {
            let mut session = world.resource_mut::<ObserverSession>();
            let Some(RuntimeSessionRequest::PreviewOrganizer {
                request_id,
                command,
                ..
            }) = client.outbox.take()
            else {
                panic!("the choice queued a review request")
            };
            let mut preview = tests::preview_for(&command);
            preview.required_hours = 3;
            client
                .previewed(request_id, preview, &mut session)
                .expect("matching preview response");
        });
    app.update();
    assert!(tests::painted_text(&mut app, false)
        .contains("Cost to issue the invitation: 3 of 16 organizer-hours"));
    tests::press_named(&mut app, "Confirm ruling");
    let client = app.world().resource::<OrganizerClient>();
    assert!(matches!(
        &client.outbox,
        Some(RuntimeSessionRequest::SubmitOrganizer { command, .. })
            if command.choice == OrganizerChoice::InviteToHearing(OrganizerHearingOffer::JointMinutes)
    ));

    let view = client.view.as_ref().expect("fixture status");
    let mut closed_hearing = view.clone();
    closed_hearing.period = 2;
    closed_hearing.hearing = None;
    let mut closed_review = closed_hearing.clone();
    closed_review.period = 3;
    let minutes = hearing::notice(&closed_review, 2, false);
    assert!(minutes.contains("Period 2 · Wayne hearing minutes"));
    assert!(minutes.contains("Demand entered in the period 2 minutes · Relief group delegate"));
    assert!(minutes.contains("Hear the residents excluded from distribution"));
    assert!(minutes.contains("Agreed speaking turns for the period 3 review"));
    assert!(minutes.contains("Reply · Wayne Local Aid Partners"));
    assert!(!minutes.contains("County review report back"));

    let report = hearing::notice(&closed_review, 3, true);
    assert!(report.contains("Period 3 · County review report back"));
    assert!(report.contains("Opening · Standing claimant"));
    assert!(report.contains("Reply · Wayne Local Aid Partners"));
    assert!(!report.contains("Agreed speaking turns"));

    // Testimony comes from the minutes, independently of seat attendance.
    closed_hearing
        .hearing_receipt
        .as_mut()
        .expect("minutes")
        .testimony
        .pop();
    let minutes = hearing::notice(&closed_hearing, 2, true);
    assert!(minutes.contains("Invitation seat · Wayne Local Aid Partners"));
    assert!(!minutes.contains("Hear the residents excluded from distribution"));

    assert!(client::hearing_update(None, view)
        .is_some_and(|text| text.starts_with("Invitation window")));
    assert!(client::hearing_update(Some(view), view).is_none());
    assert!(client::hearing_update(Some(view), &closed_hearing)
        .is_some_and(|text| text.starts_with("Wayne hearing minutes")));
    assert!(client::hearing_update(Some(&closed_hearing), &closed_hearing).is_none());
    // Install P2 with its actual committed testimony and without a future report.
    let mut committed_p2 = closed_review.clone();
    committed_p2.period = 2;
    committed_p2.hearing_review = None;
    assert!(client::hearing_update(Some(&committed_p2), &closed_review)
        .is_some_and(|text| text.starts_with("The county review report")));
    assert!(client::hearing_update(Some(&closed_review), &closed_review).is_none());
}
