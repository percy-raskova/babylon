use babylon_rtd::{
    canonical_draft_bytes, parse_draft_json, parse_vector_corpus, projection_hash, seal_draft,
    RtdDossierDraftV1, RtdVectorCaseV1, RTD_V1_ERROR_REGISTRY,
};

const CORPUS: &str =
    include_str!("../../../../contracts/relational_territory_dossier_v1_vectors.jsonl");

fn hex(bytes: &[u8]) -> String {
    use std::fmt::Write;
    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(output, "{byte:02x}").expect("writing to String cannot fail");
    }
    output
}

#[test]
fn shared_valid_vectors_pin_bytes_and_hashes() {
    let cases = parse_vector_corpus(CORPUS.as_bytes()).expect("checked corpus parses");
    let mut minimal_bytes = None;
    let mut minimal_hash = None;
    for case_index in 0..256_usize {
        if case_index == cases.len() {
            break;
        }
        let case = &cases[case_index];
        if let RtdVectorCaseV1::Valid {
            case_id,
            draft_json,
            canonical_utf8_hex,
            projection_hash: expected_hash,
            ..
        } = case
        {
            let draft = parse_draft_json(draft_json).expect("valid vector draft");
            assert_eq!(
                hex(&canonical_draft_bytes(&draft).expect("canonical bytes")),
                *canonical_utf8_hex
            );
            assert_eq!(
                hex(&projection_hash(&draft).expect("projection hash")),
                *expected_hash
            );
            assert_eq!(
                seal_draft(draft).expect("sealed draft").projection_hash,
                *expected_hash
            );
            if case_id == "minimal-admin" {
                minimal_bytes = Some(canonical_utf8_hex.clone());
                minimal_hash = Some(expected_hash.clone());
            } else if case_id == "permuted-focus" {
                assert_eq!(minimal_bytes.as_ref(), Some(canonical_utf8_hex));
                assert_eq!(minimal_hash.as_ref(), Some(expected_hash));
            } else if case_id == "semantic-mutation" {
                assert_ne!(minimal_hash.as_ref(), Some(expected_hash));
            }
        }
    }
}

#[test]
fn shared_semantic_invalid_vectors_pin_refusals() {
    let cases = parse_vector_corpus(CORPUS.as_bytes()).expect("checked corpus parses");
    let reader_only = ["RTD_JSON_DEPTH", "RTD_VECTOR_LIMIT", "RTD_CANONICAL_SIZE"];
    let mut seen = [false; 20];
    for case_index in 0..256_usize {
        if case_index == cases.len() {
            break;
        }
        if let RtdVectorCaseV1::Invalid {
            draft_json, error, ..
        } = &cases[case_index]
        {
            for error_index in 0..20_usize {
                if RTD_V1_ERROR_REGISTRY[error_index] == error {
                    seen[error_index] = true;
                    break;
                }
            }
            if reader_only.contains(&error.as_str()) {
                continue;
            }
            assert_eq!(
                parse_draft_json(draft_json)
                    .expect_err("invalid vector must refuse")
                    .to_string(),
                *error
            );
        }
    }
    assert_eq!(seen, [true; 20]);
}

#[test]
fn vector_reader_refuses_raw_line_count_and_line_size_limits() {
    assert_eq!(
        parse_vector_corpus(&vec![b'x'; 1_048_577])
            .expect_err("raw corpus limit")
            .to_string(),
        "RTD_VECTOR_LIMIT"
    );
    assert_eq!(
        parse_vector_corpus(&vec![b'x'; 262_145])
            .expect_err("line limit")
            .to_string(),
        "RTD_VECTOR_LIMIT"
    );
    let mut lines = Vec::new();
    for index in 0..257_usize {
        lines.extend_from_slice(
            format!(
                "{{\"case_id\":\"case-{index}\",\"kind\":\"invalid\",\"draft\":{{}},\"error\":\"RTD_JSON\"}}\n"
            )
            .as_bytes(),
        );
    }
    assert_eq!(
        parse_vector_corpus(&lines)
            .expect_err("line count limit")
            .to_string(),
        "RTD_VECTOR_LIMIT"
    );
}

#[test]
#[allow(clippy::needless_range_loop)] // fixed six-case envelope contract
fn vector_reader_refuses_closed_envelope_and_depth_violations() {
    let too_long_id = "x".repeat(129);
    let witnesses = [
        format!(
            "{{\"case_id\":\"{too_long_id}\",\"kind\":\"invalid\",\"draft\":{{}},\"error\":\"RTD_JSON\"}}\n"
        ),
        "{\"case_id\":\"a\",\"kind\":\"other\",\"draft\":{},\"error\":\"RTD_JSON\"}\n".to_owned(),
        "{\"case_id\":\"a\",\"kind\":\"invalid\",\"draft\":{},\"error\":\"RTD_JSON\",\"extra\":0}\n".to_owned(),
        "{\"case_id\":\"a\",\"kind\":\"invalid\",\"draft\":{},\"error\":\"RTD_JSON\"} trailing\n".to_owned(),
        "{\"case_id\":\"a\",\"case_id\":\"b\",\"kind\":\"invalid\",\"draft\":{},\"error\":\"RTD_JSON\"}\n".to_owned(),
        "{\"case_id\":\"e\\u0301\",\"kind\":\"invalid\",\"draft\":{},\"error\":\"RTD_JSON\"}\n".to_owned(),
    ];
    for index in 0..6_usize {
        assert!(parse_vector_corpus(witnesses[index].as_bytes()).is_err());
    }
    let line = b"{\"case_id\":\"a\",\"kind\":\"invalid\",\"draft\":{},\"error\":\"RTD_JSON\"}\n";
    assert_eq!(
        parse_vector_corpus(&[line.as_slice(), line.as_slice()].concat())
            .expect_err("duplicate case")
            .to_string(),
        "RTD_DUPLICATE_KEY"
    );
    let nested = format!(
        "{{\"case_id\":\"a\",\"kind\":\"invalid\",\"draft\":{}0{},\"error\":\"RTD_JSON\"}}\n",
        "{\"x\":".repeat(32),
        "}".repeat(32)
    );
    assert_eq!(
        parse_vector_corpus(nested.as_bytes())
            .expect_err("depth 33")
            .to_string(),
        "RTD_JSON_DEPTH"
    );
}

#[test]
fn direct_draft_negative_zero_is_normalized_before_sealing() {
    let cases = parse_vector_corpus(CORPUS.as_bytes()).expect("checked corpus parses");
    for case_index in 0..256_usize {
        if case_index == cases.len() {
            break;
        }
        if let RtdVectorCaseV1::Valid {
            case_id,
            draft_json,
            projection_hash: expected,
            ..
        } = &cases[case_index]
        {
            if case_id != "negative-zero-normalizes" {
                continue;
            }
            let raw = serde_json::from_slice::<RtdDossierDraftV1>(draft_json)
                .expect("generated draft structure");
            assert_eq!(
                raw.scale_memberships[0].weight_bits_or_null.as_deref(),
                Some("8000000000000000")
            );
            let sealed = seal_draft(raw).expect("negative zero seals");
            assert_eq!(
                sealed.scale_memberships[0].weight_bits_or_null.as_deref(),
                Some("0000000000000000")
            );
            assert_eq!(&sealed.projection_hash, expected);
            return;
        }
    }
    panic!("negative-zero-normalizes vector is required");
}
