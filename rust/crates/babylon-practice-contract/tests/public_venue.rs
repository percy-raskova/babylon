use babylon_practice_contract as practice_contract;
use babylon_practice_contract::{PublicVenueHistory, PublicVenuePolicy};

#[test]
fn authored_notice_is_stable_and_bound_to_policy_terms() {
    let policy = PublicVenuePolicy::new([1; 16], 2, 3, 4, [5; 16], 6, 3, [7; 32], [8; 32])
        .expect("public venue fixture supplies valid evidence");
    let first = practice_contract::initial_public_venue_notice(&policy)
        .expect("public venue fixture supplies valid evidence");
    let second = practice_contract::initial_public_venue_notice(&policy)
        .expect("public venue fixture supplies valid evidence");
    assert_eq!(first, second);
    assert_eq!(first.period, 0);
    assert_eq!(first.venue_id, policy.venue_id);
    assert_ne!(first.source_id, [0; 32]);
    let different = PublicVenuePolicy::new([1; 16], 2, 3, 4, [5; 16], 6, 3, [7; 32], [9; 32])
        .expect("public venue fixture supplies valid evidence");
    assert_ne!(
        first.source_id,
        practice_contract::initial_public_venue_notice(&different)
            .expect("public venue fixture supplies valid evidence")
            .source_id
    );
}

#[test]
fn history_refuses_duplicate_records_and_noncanonical_bytes() {
    let policy = PublicVenuePolicy::new([1; 16], 2, 3, 4, [5; 16], 6, 3, [7; 32], [8; 32])
        .expect("public venue fixture supplies valid evidence");
    let notice = practice_contract::initial_public_venue_notice(&policy)
        .expect("public venue fixture supplies valid evidence");
    let duplicated = PublicVenueHistory {
        policy: policy.clone(),
        records: vec![notice.clone(), notice.clone()],
    };
    assert!(practice_contract::encode_public_venue_history(&duplicated).is_err());
    let history = PublicVenueHistory {
        policy,
        records: vec![notice],
    };
    let bytes = practice_contract::encode_public_venue_history(&history)
        .expect("public venue fixture supplies valid evidence");
    assert_eq!(
        practice_contract::decode_public_venue_history(&bytes)
            .expect("public venue fixture supplies valid evidence"),
        history
    );
    let mut trailing = bytes;
    trailing.push(b' ');
    assert!(practice_contract::decode_public_venue_history(&trailing).is_err());
}

#[test]
fn individual_record_has_a_versioned_domain_and_rejects_foreign_bytes() {
    let policy = PublicVenuePolicy::new([1; 16], 2, 3, 4, [5; 16], 6, 3, [7; 32], [8; 32])
        .expect("public venue fixture supplies valid evidence");
    let notice = practice_contract::initial_public_venue_notice(&policy)
        .expect("public venue fixture supplies valid evidence");
    let bytes = practice_contract::encode_public_venue_record(&policy, &notice)
        .expect("public venue fixture supplies valid evidence");
    assert!(bytes.starts_with(b"babylon.public-venue.record.v1\0"));
    assert_eq!(
        practice_contract::decode_public_venue_record(&policy, &bytes)
            .expect("public venue fixture supplies valid evidence"),
        notice
    );
    let mut old = bytes.clone();
    old["babylon.public-venue.record.v".len()] = b'0';
    assert!(practice_contract::decode_public_venue_record(&policy, &old).is_err());
    let mut changed = notice.clone();
    changed.period = 1;
    assert!(practice_contract::encode_public_venue_record(&policy, &changed).is_err());
    let mut trailing = bytes;
    trailing.push(b' ');
    assert!(practice_contract::decode_public_venue_record(&policy, &trailing).is_err());
}

#[test]
fn organizer_identity_helpers_preserve_existing_receipt_and_product_bytes() {
    let commitment = [
        103, 153, 56, 40, 70, 167, 1, 91, 168, 253, 143, 189, 133, 58, 180, 99, 206, 153, 255, 167,
        99, 83, 159, 102, 246, 104, 73, 112, 210, 22, 208, 136,
    ];
    let expected_receipt = [
        150, 51, 167, 26, 122, 161, 207, 221, 116, 101, 187, 83, 81, 199, 254, 16, 36, 221, 42, 28,
        42, 22, 138, 101, 14, 183, 167, 211, 6, 119, 110, 243,
    ];
    let expected_product = [
        167, 204, 80, 255, 59, 205, 98, 13, 247, 123, 11, 141, 35, 197, 116, 100, 215, 99, 150, 76,
        208, 173, 88, 110, 236, 208, 62, 222, 112, 232, 152, 48,
    ];
    assert_eq!(
        practice_contract::organizer_receipt_id([1; 16], 101, 1, commitment)
            .expect("public venue fixture supplies valid evidence"),
        expected_receipt
    );
    assert_eq!(
        practice_contract::organizer_contact_product_id(expected_receipt, 101, 102, 1)
            .expect("public venue fixture supplies valid evidence"),
        expected_product
    );
}
