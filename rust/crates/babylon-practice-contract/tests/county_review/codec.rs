//! The canonical bytes of the County Review's configuration and state.
use babylon_practice_contract as practice_contract;
use babylon_practice_contract::{
    CountyReviewError, CountyReviewState, SessionRow, COUNTY_REVIEW_MAX_ROWS,
};

use super::support;
use super::support::D;

const STATE_DOMAIN: &[u8] = b"babylon.county-review-state.v1\0";
const CONFIG_DOMAIN: &[u8] = b"babylon.county-review-config.v1\0";
const MAX_BYTES: usize = 8 * 1024 * 1024;

#[test]
fn a_state_survives_encode_and_decode() {
    let (_, state) = support::state_after_contact();
    assert!(state.last_facts.is_some() && state.last_session.is_some());
    let bytes = practice_contract::encode_county_review_state(&state).expect("the state encodes");
    assert!(bytes.starts_with(STATE_DOMAIN));
    assert_eq!(
        practice_contract::decode_county_review_state(&bytes),
        Ok(state)
    );
    let (_, bare) = support::state_before_contact();
    let bytes = practice_contract::encode_county_review_state(&bare).expect("the state encodes");
    assert_eq!(
        practice_contract::decode_county_review_state(&bytes),
        Ok(bare)
    );
}

#[test]
fn a_configuration_survives_encode_and_decode_and_has_a_stable_digest() {
    let (config, _) = support::state_before_contact();
    let bytes = practice_contract::encode_county_review_config(&config).expect("it encodes");
    assert!(bytes.starts_with(CONFIG_DOMAIN));
    let text = String::from_utf8_lossy(&bytes);
    assert!(
        text.contains("\"unit_price_micros\":\"280000000\""),
        "money is a decimal string"
    );
    assert_eq!(
        practice_contract::decode_county_review_config(&bytes),
        Ok(config.clone())
    );
    let digest = practice_contract::county_review_config_digest(&config).expect("it digests");
    assert_eq!(
        practice_contract::county_review_config_digest(&config),
        Ok(digest)
    );
    let mut other = config;
    other.administration_label.push('!');
    assert_ne!(
        practice_contract::county_review_config_digest(&other),
        Ok(digest)
    );
}

#[test]
fn a_flipped_byte_never_decodes_to_noncanonical_bytes() {
    let (_, state) = support::state_after_contact();
    let bytes = practice_contract::encode_county_review_state(&state).expect("the state encodes");
    let payload_start = STATE_DOMAIN.len();
    let mut refused = 0_u32;
    for index in payload_start..bytes.len() {
        let mut flipped = bytes.clone();
        flipped[index] ^= 0x01;
        match practice_contract::decode_county_review_state(&flipped) {
            Ok(decoded) => assert_eq!(
                practice_contract::encode_county_review_state(&decoded),
                Ok(flipped),
                "a state that decodes is the canonical form of its bytes"
            ),
            Err(error) => {
                assert!(
                    matches!(
                        error,
                        CountyReviewError::Codec
                            | CountyReviewError::NonCanonical
                            | CountyReviewError::UnsupportedSchema
                    ),
                    "{error:?}"
                );
                refused += 1;
            }
        }
    }
    assert!(refused > 0, "some flips are refused");
}

#[test]
fn bytes_that_are_valid_json_but_not_canonical_are_refused() {
    let (_, state) = support::state_before_contact();
    let bytes = practice_contract::encode_county_review_state(&state).expect("the state encodes");
    let mut spaced = STATE_DOMAIN.to_vec();
    spaced.push(b' ');
    spaced.extend_from_slice(&bytes[STATE_DOMAIN.len()..]);
    assert_eq!(
        practice_contract::decode_county_review_state(&spaced),
        Err(CountyReviewError::NonCanonical)
    );
}

#[test]
fn bytes_in_another_domain_are_refused() {
    let (config, state) = support::state_before_contact();
    let config_bytes = practice_contract::encode_county_review_config(&config).expect("it encodes");
    assert_eq!(
        practice_contract::decode_county_review_state(&config_bytes),
        Err(CountyReviewError::Codec)
    );
    let state_bytes = practice_contract::encode_county_review_state(&state).expect("it encodes");
    assert_eq!(
        practice_contract::decode_county_review_config(&state_bytes),
        Err(CountyReviewError::Codec)
    );
}

#[test]
fn another_schema_version_is_refused() {
    let (_, state) = support::state_before_contact();
    let bytes = practice_contract::encode_county_review_state(&state).expect("the state encodes");
    let text = String::from_utf8(bytes).expect("canonical JSON is text");
    let changed = text.replacen("\"schema_version\":1", "\"schema_version\":2", 1);
    assert_ne!(text, changed);
    assert_eq!(
        practice_contract::decode_county_review_state(changed.as_bytes()),
        Err(CountyReviewError::UnsupportedSchema)
    );
    let other = CountyReviewState {
        schema_version: 2,
        ..state
    };
    assert_eq!(
        practice_contract::encode_county_review_state(&other),
        Err(CountyReviewError::UnsupportedSchema)
    );
}

#[test]
fn a_roster_with_unsorted_rows_is_refused_by_validation() {
    let (config, mut state) = support::state_after_contact();
    assert_eq!(
        practice_contract::validate_county_review_state(&config, &state),
        Ok(())
    );
    state.roster.rows.swap(0, 1);
    assert_eq!(
        practice_contract::validate_county_review_state(&config, &state),
        Err(CountyReviewError::RosterNotCanonical)
    );
}

#[test]
fn a_session_without_the_facts_it_was_held_from_is_refused_by_validation() {
    let (config, mut state) = support::state_after_contact();
    state.last_facts = None;
    assert_eq!(
        practice_contract::validate_county_review_state(&config, &state),
        Err(CountyReviewError::StateShape)
    );
}

#[test]
fn a_session_with_unsorted_rows_is_refused_by_validation() {
    let (config, mut state) = support::state_after_contact();
    let session = state.last_session.as_mut().expect("a session is held");
    session.rows.swap(0, 1);
    assert_eq!(
        practice_contract::validate_county_review_state(&config, &state),
        Err(CountyReviewError::RosterNotCanonical)
    );
}

#[test]
fn facts_that_do_not_fit_the_configuration_are_refused_by_validation() {
    let (config, mut state) = support::state_after_contact();
    state
        .last_facts
        .as_mut()
        .expect("the facts are held")
        .crews
        .pop();
    assert_eq!(
        practice_contract::validate_county_review_state(&config, &state),
        Err(CountyReviewError::FactsShape)
    );
}

#[test]
fn the_size_limit_is_eight_mebibytes() {
    let (_, mut state) = support::state_after_contact();
    let row: SessionRow = state
        .last_session
        .as_ref()
        .expect("a session is held")
        .rows
        .iter()
        .find(|r| r.key == D)
        .expect("D is in the record")
        .clone();
    let session = state.last_session.as_mut().expect("a session is held");
    session.rows = vec![row; COUNTY_REVIEW_MAX_ROWS + 1];
    assert_eq!(
        practice_contract::encode_county_review_state(&state),
        Err(CountyReviewError::SizeLimit)
    );
    let too_big = vec![0_u8; MAX_BYTES + 1];
    assert_eq!(
        practice_contract::decode_county_review_state(&too_big),
        Err(CountyReviewError::SizeLimit)
    );
    assert_eq!(
        practice_contract::decode_county_review_config(&too_big),
        Err(CountyReviewError::SizeLimit)
    );
}
