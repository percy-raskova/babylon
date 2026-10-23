use super::*;

fn reply(payer: i128, gift: i128, price: i128) -> RuntimeSessionResponse {
    RuntimeSessionResponse::OrganizerStatus {
        request_id: 2,
        scope: RuntimeSessionScope {
            epoch: 1,
            campaign_id: Some(uuid::Uuid::from_u128(1).to_string()),
        },
        snapshot: Box::new(OrganizerSnapshot {
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
            duration: babylon_kernel::clock::CampaignDuration::Continuous,
            aid: vec![OrganizerMaterialAidPreview {
                kind: OrganizerAidKind::Local,
                mandate_id: [1; 32],
                period: 0,
                donor_id: [2; 32],
                recipient_id: [3; 32],
                good_id: [4; 32],
                unit_id: [5; 32],
                donor_stock: 10,
                own_need: 2,
                grams_per_unit: 100,
                payer_cash: payer,
                ordinary_offer: Some(OrganizerAidOrdinaryOffer {
                    seller_id: [6; 32],
                    unit_price: price,
                }),
                maximum_quantity: 3,
                gift_cash_per_unit: gift,
                labor_unit_id: [7; 32],
                fulfillment_hours_per_unit: 1,
                coordination_hours: 1,
                receiving_consent: OrganizerGiftConsent::Accept,
                time: None,
                transport: OrganizerAidTransportPreview::Local,
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
        let encoded = serde_json::to_vec(&expected).unwrap();
        let decoded: RuntimeSessionResponse = serde_json::from_slice(&encoded)
            .expect("actual internally tagged reply preserves typed money");
        assert_eq!(decoded, expected);
        let wire: serde_json::Value = serde_json::from_slice(&encoded).unwrap();
        let aid = &wire["snapshot"]["aid"][0];
        assert_eq!(aid["payer_cash"], payer.to_string());
        assert_eq!(aid["gift_cash_per_unit"], gift.to_string());
        assert_eq!(aid["ordinary_offer"]["unit_price"], price.to_string());
    }
}

#[test]
fn tagged_organizer_money_refuses_noncanonical_numeric_and_overflow_values() {
    let valid = serde_json::to_value(reply(42, 3, 7)).unwrap();
    let bad = [
        serde_json::json!(42),
        serde_json::json!(1.5),
        serde_json::json!(true),
        serde_json::Value::Null,
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
    for field in ["payer_cash", "gift_cash_per_unit", "unit_price"] {
        for value in &bad {
            let mut changed = valid.clone();
            let aid = &mut changed["snapshot"]["aid"][0];
            if field == "unit_price" {
                aid["ordinary_offer"][field] = value.clone();
            } else {
                aid[field] = value.clone();
            }
            assert!(
                serde_json::from_slice::<RuntimeSessionResponse>(
                    &serde_json::to_vec(&changed).unwrap()
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
        maximum_cash_micros: i128::MAX,
        protected_cash_floor_micros: 0,
        collection_hours: 2,
        organization_cash_micros: i128::MAX,
    });
    let wire = serde_json::to_value(&expected).unwrap();
    assert_eq!(
        wire["snapshot"]["collection"]["maximum_cash_micros"],
        i128::MAX.to_string()
    );
    let decoded: RuntimeSessionResponse = serde_json::from_value(wire.clone()).unwrap();
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
        missing["snapshot"].as_object_mut().unwrap().remove(field);
        assert!(
            serde_json::from_value::<RuntimeSessionResponse>(missing).is_err(),
            "{field}"
        );
    }
    for field in [
        "actor_id",
        "contributor_id",
        "contributor_label",
        "source_hash",
    ] {
        let mut missing = wire.clone();
        missing["snapshot"]["collection"]
            .as_object_mut()
            .unwrap()
            .remove(field);
        assert!(
            serde_json::from_value::<RuntimeSessionResponse>(missing).is_err(),
            "collection attribution: {field}"
        );
    }
    let mut absent = wire;
    absent["snapshot"]["collection"] = serde_json::Value::Null;
    assert!(serde_json::from_value::<RuntimeSessionResponse>(absent).is_ok());
}
