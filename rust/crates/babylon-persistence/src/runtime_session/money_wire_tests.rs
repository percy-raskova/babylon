use super::{RuntimeSessionResponse, RuntimeSessionScope};
use crate::organizer_runtime::{
    OrganizerAidOrdinaryOffer, OrganizerAidTransportPreview, OrganizerBodyDisclosure,
    OrganizerBodyScope, OrganizerCollectionPreview, OrganizerMaterialAidPreview, OrganizerSnapshot,
};
use babylon_kernel::clock::CampaignDuration;
use babylon_practice_contract::{
    OrganizerAidKind, OrganizerGiftConsent, OrganizerStandingWork, OrganizerView,
};
use serde_json::Value;
use uuid::Uuid;

fn reply(payer: i128, gift: i128, price: i128) -> RuntimeSessionResponse {
    RuntimeSessionResponse::OrganizerStatus {
        request_id: 2,
        scope: RuntimeSessionScope {
            epoch: 1,
            campaign_id: Some(Uuid::from_u128(1).to_string()),
        },
        snapshot: Box::new(OrganizerSnapshot {
            body: OrganizerBodyDisclosure::Unavailable,
            body_scope: OrganizerBodyScope {
                campaign_id: *Uuid::from_u128(1).as_bytes(),
                actor_id: 1,
                period: 0,
                content_digest: [2; 32],
                source: None,
            },
            city_pd_encounters: Vec::new(),
            view: OrganizerView {
                period: 0,
                actor_id: 1,
                authority_id: [1; 16],
                organization_label: "Aid circle".into(),
                workplace_id: 2,
                workplace_label: "Works".into(),
                workplace_partner_id: 3,
                workplace_partner_label: "Partner".into(),
                neighborhood_partner_id: 4,
                neighborhood_partner_label: "Neighbors".into(),
                available_hours: 16,
                inquiry_hours: 1,
                contact_hours: 2,
                public_workplace_contact: false,
                content_digest: [2; 32],
                resource_digest: [3; 32],
                standing: OrganizerStandingWork {
                    partner_actor_id: 3,
                    authorized: true,
                    paused_reason: None,
                },
                agreements: vec![],
                total_observation_count: 0,
                observations: vec![],
                total_receipt_count: 0,
                receipts: vec![],
                positions: vec![],
                aid_options: vec![],
            },
            pending: None,
            duration: CampaignDuration::Continuous,
            aid: vec![OrganizerMaterialAidPreview {
                initial_food_quantity: 1,
                initial_cash_micros: 0,
                cash_receiving_consent: OrganizerGiftConsent::Accept,
                kind: OrganizerAidKind::Local,
                mandate_id: [1; 32],
                period: 0,
                donor_id: [2; 32],
                recipient_actor_id: 3,
                good_id: [4; 32],
                unit_id: [5; 32],
                food: Some(crate::runtime_session::OrganizerAidFoodPreview {
                    donor_stock: 10,
                    own_need: 2,
                    grams_per_unit: 100,
                    ordinary_offer: Some(OrganizerAidOrdinaryOffer {
                        seller_id: [6; 32],
                        unit_price: price,
                    }),
                    labor_unit_id: [7; 32],
                    fulfillment_hours_per_unit: 1,
                    time: None,
                    transport: OrganizerAidTransportPreview::Local,
                }),
                payer_cash: Some(payer),
                maximum_quantity: 3,
                maximum_cash_micros: gift,
                coordination_hours: 1,
                receiving_consent: OrganizerGiftConsent::Accept,
            }],
            pending_aid: vec![],
            aid_resolutions: vec![],
            collection: None,
            collection_resolutions: vec![],
        }),
    }
}

#[test]
fn tagged_organizer_money_roundtrips_exact_full_i128() {
    for (payer, gift, price) in [
        (42, 3, 7),
        (0, 0, 0),
        (i128::MAX, i128::MIN, i128::from(i64::MAX) + 1),
        (i128::MIN, i128::MAX, -i128::from(u64::MAX) - 1),
    ] {
        let expected = reply(payer, gift, price);
        let encoded =
            serde_json::to_vec(&expected).expect("the value serializes to canonical JSON bytes");
        let decoded: RuntimeSessionResponse = serde_json::from_slice(&encoded)
            .expect("actual internally tagged reply preserves typed money");
        assert_eq!(decoded, expected);
        let wire: Value =
            serde_json::from_slice(&encoded).expect("the authored bytes match the declared schema");
        let aid = &wire["snapshot"]["aid"][0];
        assert_eq!(aid["payer_cash"], payer.to_string());
        assert_eq!(aid["maximum_cash_micros"], gift.to_string());
        assert_eq!(
            aid["food"]["ordinary_offer"]["unit_price"],
            price.to_string()
        );
    }
}

#[test]
fn organizer_body_fields_are_required_in_current_wire_and_fixtures() {
    let valid = serde_json::to_value(reply(42, 3, 7)).expect("wire value");
    for field in ["body", "body_scope"] {
        let mut missing = valid.clone();
        missing["snapshot"]
            .as_object_mut()
            .expect("snapshot object")
            .remove(field);
        assert!(
            serde_json::from_value::<RuntimeSessionResponse>(missing).is_err(),
            "missing {field} is refused"
        );
    }
    for bytes in [
        include_str!("../../tests/fixtures/national_organizer_opening_v17.json"),
        include_str!("../../tests/fixtures/national_organizer_pending_v17.json"),
    ] {
        let snapshot: OrganizerSnapshot =
            serde_json::from_str(bytes).expect("current fixture is complete");
        assert_eq!(snapshot.body, OrganizerBodyDisclosure::Unavailable);
        assert_eq!(snapshot.body_scope.period, snapshot.view.period);
        assert_eq!(snapshot.body_scope.actor_id, snapshot.view.actor_id);
        assert_eq!(
            snapshot.body_scope.content_digest,
            snapshot.view.content_digest
        );
    }
}

#[test]
fn tagged_organizer_money_refuses_noncanonical_numeric_and_overflow_values() {
    let valid = serde_json::to_value(reply(42, 3, 7)).expect("the value serializes to JSON");
    let bad = [
        serde_json::json!(42),
        serde_json::json!(1.5),
        serde_json::json!(true),
        Value::Null,
        serde_json::json!(""),
        serde_json::json!("+1"),
        serde_json::json!("01"),
        serde_json::json!("-0"),
        serde_json::json!("-01"),
        serde_json::json!(" 1"),
        serde_json::json!("1 "),
        serde_json::json!("1e3"),
        serde_json::json!("1.0"),
        serde_json::json!("170141183460469231731687303715884105728"),
        serde_json::json!("-170141183460469231731687303715884105729"),
        serde_json::json!("99999999999999999999999999999999999999999"),
    ];
    for field in ["payer_cash", "maximum_cash_micros", "unit_price"] {
        for value in &bad {
            if field == "payer_cash" && value.is_null() {
                continue;
            }
            let mut changed = valid.clone();
            let aid = &mut changed["snapshot"]["aid"][0];
            if field == "unit_price" {
                aid["food"]["ordinary_offer"][field] = value.clone();
            } else {
                aid[field] = value.clone();
            }
            assert!(
                serde_json::from_slice::<RuntimeSessionResponse>(
                    &serde_json::to_vec(&changed)
                        .expect("the value serializes to canonical JSON bytes")
                )
                .is_err(),
                "refuse {field}={value}"
            );
        }
    }
}

#[test]
fn collection_snapshot_requires_evidence_and_exact_cash_strings() {
    let mut expected = reply(42, 3, 7);
    let RuntimeSessionResponse::OrganizerStatus { snapshot, .. } = &mut expected else {
        unreachable!()
    };
    snapshot.collection = Some(OrganizerCollectionPreview {
        period: 0,
        mandate_id: [8; 32],
        actor_id: snapshot.view.actor_id,
        contributor_id: 1,
        contributor_label: "Fixture contributor".into(),
        source_hash: [16; 32],
        cash_consent: OrganizerGiftConsent::Accept,
        initial_cash_micros: i128::MAX,
        maximum_cash_micros: i128::MAX,
        protected_cash_floor_micros: 0,
        collection_hours: 2,
        organization_cash_micros: i128::MAX,
    });
    let wire = serde_json::to_value(&expected).expect("the value serializes to JSON");
    assert_eq!(
        wire["snapshot"]["collection"]["maximum_cash_micros"],
        i128::MAX.to_string()
    );
    let decoded: RuntimeSessionResponse =
        serde_json::from_value(wire.clone()).expect("the JSON value matches the declared type");
    assert_eq!(decoded, expected);
    for bad in [
        serde_json::json!(400_000),
        serde_json::json!("-1"),
        serde_json::json!("0400000"),
        serde_json::json!("+400000"),
        serde_json::json!("170141183460469231731687303715884105728"),
    ] {
        let mut altered = wire.clone();
        altered["snapshot"]["collection"]["maximum_cash_micros"] = bad;
        assert!(serde_json::from_value::<RuntimeSessionResponse>(altered).is_err());
    }
    for field in ["collection", "collection_resolutions"] {
        let mut missing = wire.clone();
        missing["snapshot"]
            .as_object_mut()
            .expect("the JSON fixture field is an object")
            .remove(field);
        assert!(
            serde_json::from_value::<RuntimeSessionResponse>(missing).is_err(),
            "{field}"
        );
    }
    for field in [
        "initial_cash_micros",
        "actor_id",
        "contributor_id",
        "contributor_label",
        "source_hash",
    ] {
        let mut missing = wire.clone();
        missing["snapshot"]["collection"]
            .as_object_mut()
            .expect("the JSON fixture field is an object")
            .remove(field);
        assert!(
            serde_json::from_value::<RuntimeSessionResponse>(missing).is_err(),
            "collection attribution: {field}"
        );
    }
    let mut absent = wire;
    absent["snapshot"]["collection"] = Value::Null;
    assert!(serde_json::from_value::<RuntimeSessionResponse>(absent).is_ok());
}

#[test]
fn unavailable_preview_legs_are_explicit_required_nulls() {
    let valid = serde_json::to_value(reply(42, 3, 7)).expect("wire value");
    for field in ["food", "payer_cash"] {
        let mut unavailable = valid.clone();
        unavailable["snapshot"]["aid"][0][field] = Value::Null;
        let decoded: RuntimeSessionResponse =
            serde_json::from_value(unavailable.clone()).expect("explicit unavailable leg");
        assert_eq!(serde_json::to_value(decoded).expect("wire"), unavailable);
        unavailable["snapshot"]["aid"][0]
            .as_object_mut()
            .expect("offer")
            .remove(field);
        assert!(
            serde_json::from_value::<RuntimeSessionResponse>(unavailable).is_err(),
            "missing {field} is not unavailable"
        );
    }
}
