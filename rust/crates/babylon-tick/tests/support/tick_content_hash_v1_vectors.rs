//! Independent semantic reconstruction for the shared PER-60 vector corpus.

use std::cmp::Ordering;

use babylon_kernel::sha256_of;
use serde_json::Value;

use super::{
    hex_bytes, integer, row_by_id, text, unsigned, verify_fixed_tags, TagRefusal, VectorRow,
    MAX_ROWS,
};

pub(super) fn canonical(row: &VectorRow, rows: &[VectorRow]) -> Option<Vec<u8>> {
    let data = &row.data;
    match row.kind.as_str() {
        "replay_session" => Some(str16(text(data, "session"))),
        "replay_seed" => Some(integer(data, "seed").to_be_bytes().to_vec()),
        "stable_element" => Some(stable_element(data)),
        "carrier_segment" => Some(carrier_segment(data)),
        "stable_carrier_key" => Some(stable_carrier_key(data, rows)),
        "resolver_manifest" => Some(resolver_manifest(data)),
        "stable_graph" => Some(stable_graph(data)),
        "action_id" => Some(action_id(data)),
        "ordered_action_batch" => Some(ordered_action_batch(data)),
        "bsl_discriminant" if data.get("governance_utf8").is_some() => {
            let mut output = Vec::new();
            push_str32(&mut output, text(data, "governance_utf8"));
            Some(output)
        }
        "bsl_discriminant" if data.get("vocabulary").is_some() => {
            Some(vocabulary(&data["vocabulary"]))
        }
        "bsl_discriminant" if data.get("bsl_type").is_some() => Some(bsl_type(&data["bsl_type"])),
        "bsl_discriminant" if data.get("bsl_value").is_some() => {
            Some(bsl_value(&data["bsl_value"]))
        }
        "bsl_discriminant" if data.get("effect").is_some() => Some(effect(&data["effect"])),
        "bsl_discriminant" if data.get("shape_verb").is_some() => Some(vec![tag(
            text(data, "shape_verb"),
            &[
                "add_node",
                "remove_node",
                "add_edge",
                "remove_edge",
                "add_hyperedge",
                "remove_hyperedge",
            ],
        )]),
        "bsl_discriminant" if data.get("field_kind").is_some() => Some(vec![tag(
            text(data, "field_kind"),
            &["intensive", "extensive", "not_applicable"],
        )]),
        "bsl_discriminant" if data.get("rule_role").is_some() => Some(vec![tag(
            text(data, "rule_role"),
            &["mechanic", "recognizer", "external_event", "intent"],
        )]),
        "bsl_discriminant" if data.get("evidence_class").is_some() => Some(vec![tag(
            text(data, "evidence_class"),
            &["observed", "derived", "calibrated", "designed"],
        )]),
        "prepared_environment" => Some(prepared_environment(data, rows)),
        "register_manifest" => Some(register_manifest(data)),
        "register_set" => Some(register_set(data, rows)),
        "stable_world" => Some(stable_world(data, rows)),
        "tick_payload" => Some(tick_payload(data)),
        "tick_content_hash" => Some(tick_content(data, rows)),
        _ => None,
    }
}

fn str16(value: &str) -> Vec<u8> {
    let mut output = Vec::new();
    output.extend_from_slice(
        &u16::try_from(value.len())
            .expect("bounded str16")
            .to_be_bytes(),
    );
    output.extend_from_slice(value.as_bytes());
    output
}

fn push_str32(output: &mut Vec<u8>, value: &str) {
    output.extend_from_slice(
        &u32::try_from(value.len())
            .expect("bounded str32")
            .to_be_bytes(),
    );
    output.extend_from_slice(value.as_bytes());
}

fn stable_element(data: &Value) -> Vec<u8> {
    let mut output = b"babylon.stable-element\0".to_vec();
    output.extend_from_slice(&1u32.to_be_bytes());
    match text(data, "element_kind") {
        "node" => {
            output.push(1);
            push_str32(&mut output, text(data, "scenario"));
            push_str32(&mut output, text(data, "local_name"));
        }
        "edge" => {
            output.push(2);
            for name in [
                "scenario",
                "edge_type",
                "source_local_name",
                "target_local_name",
            ] {
                push_str32(&mut output, text(data, name));
            }
        }
        "hyperedge" => {
            output.push(3);
            push_str32(&mut output, text(data, "scenario"));
            push_str32(&mut output, text(data, "local_name"));
        }
        _ => panic!("closed stable element kind"),
    }
    output
}

fn carrier_segment(data: &Value) -> Vec<u8> {
    let mut output = Vec::new();
    for (index, segment) in data["segments"]
        .as_array()
        .expect("carrier segments")
        .iter()
        .take(258)
        .enumerate()
    {
        if index > 0 {
            output.push(b'|');
        }
        let segment = segment.as_str().expect("carrier segment text");
        output.extend_from_slice(segment.len().to_string().as_bytes());
        output.push(b':');
        output.extend_from_slice(segment.as_bytes());
    }
    output
}

fn stable_carrier_key(data: &Value, rows: &[VectorRow]) -> Vec<u8> {
    let active = data["active_segment_ids"]
        .as_array()
        .expect("active stable carrier segments");
    assert!(
        active.len() <= 256,
        "bounded active stable carrier segments"
    );
    let mut segment_ids = Vec::with_capacity(active.len() + 1);
    segment_ids.push(text(data, "subject_segment_id"));
    for id in active.iter().take(256) {
        segment_ids.push(id.as_str().expect("active carrier segment id"));
    }
    let mut segments = Vec::with_capacity(segment_ids.len() + 1);
    for id in segment_ids.iter().take(257) {
        let linked = row_by_id(rows, id);
        assert_eq!(
            linked.kind, "carrier_segment",
            "graph-owned carrier segment"
        );
        segments.push(carrier_segment(&linked.data));
    }
    segments.push(integer(data, "draw_slot").to_string().into_bytes());
    let mut output = Vec::new();
    for (index, segment) in segments.iter().take(258).enumerate() {
        if index > 0 {
            output.push(b'|');
        }
        output.extend_from_slice(segment.len().to_string().as_bytes());
        output.push(b':');
        output.extend_from_slice(segment);
    }
    assert!(output.len() <= 131_072, "bounded final stable carrier");
    output
}

fn resolver_manifest(data: &Value) -> Vec<u8> {
    let mut output = b"babylon.stable-element-resolver\0".to_vec();
    output.extend_from_slice(&1u32.to_be_bytes());
    output.push(1);
    push_str32(&mut output, text(data, "scenario"));
    let mut nodes = sorted_rows(&data["nodes"], &["local_name"]);
    output.push(2);
    output.extend_from_slice(
        &u32::try_from(nodes.len())
            .expect("node count")
            .to_be_bytes(),
    );
    for node in nodes.drain(..).take(65_536) {
        push_str32(&mut output, text(node, "local_name"));
        push_str32(&mut output, text(node, "node_type"));
    }
    let mut hyperedges = sorted_rows(&data["hyperedges"], &["local_name"]);
    output.push(3);
    output.extend_from_slice(
        &u32::try_from(hyperedges.len())
            .expect("hyperedge count")
            .to_be_bytes(),
    );
    for hyperedge in hyperedges.drain(..).take(65_536) {
        push_str32(&mut output, text(hyperedge, "local_name"));
        push_str32(&mut output, text(hyperedge, "hyperedge_type"));
    }
    output
}

fn stable_graph(data: &Value) -> Vec<u8> {
    let mut output = b"babylon.stable-graph\0".to_vec();
    output.extend_from_slice(&1u32.to_be_bytes());
    output.push(1);
    push_str32(&mut output, text(data, "scenario"));
    append_stable_nodes(&mut output, data);
    append_stable_node_f64(&mut output, data);
    append_stable_edges(&mut output, data);
    append_stable_hyperedges(&mut output, data);
    append_stable_edge_f64(&mut output, data);
    append_stable_currency(&mut output, data);
    append_stable_hyperedge_f64(&mut output, data);
    output
}

fn append_count(output: &mut Vec<u8>, tag: u8, count: usize) {
    output.push(tag);
    output.extend_from_slice(&u32::try_from(count).expect("section count").to_be_bytes());
}

fn append_stable_nodes(output: &mut Vec<u8>, data: &Value) {
    let rows = sorted_rows(&data["nodes"], &["local_name"]);
    append_count(output, 2, rows.len());
    for row in rows.into_iter().take(65_536) {
        push_str32(output, text(row, "local_name"));
        push_str32(output, text(row, "node_type"));
    }
}

fn append_stable_node_f64(output: &mut Vec<u8>, data: &Value) {
    let rows = sorted_rows(&data["node_f64"], &["local_name", "qname"]);
    append_count(output, 3, rows.len());
    for row in rows.into_iter().take(1_048_576) {
        push_str32(output, text(row, "local_name"));
        push_str32(output, text(row, "qname"));
        output.extend_from_slice(&f64_bits(text(row, "value_bits_hex")));
    }
}

fn append_stable_edges(output: &mut Vec<u8>, data: &Value) {
    let rows = sorted_rows(&data["edges"], &["edge_type", "source", "target"]);
    append_count(output, 4, rows.len());
    for row in rows.into_iter().take(65_536) {
        for name in ["edge_type", "source", "target"] {
            push_str32(output, text(row, name));
        }
        output.extend_from_slice(&f64_bits(text(row, "strength_bits_hex")));
    }
}

fn append_stable_hyperedges(output: &mut Vec<u8>, data: &Value) {
    let rows = sorted_rows(&data["hyperedges"], &["local_name"]);
    append_count(output, 5, rows.len());
    for row in rows.into_iter().take(65_536) {
        push_str32(output, text(row, "local_name"));
        push_str32(output, text(row, "hyperedge_type"));
        let mut members: Vec<&str> = row["members"]
            .as_array()
            .expect("hyperedge members")
            .iter()
            .map(|value| value.as_str().expect("member text"))
            .collect();
        members.sort_unstable_by(|left, right| left.as_bytes().cmp(right.as_bytes()));
        output.extend_from_slice(
            &u32::try_from(members.len())
                .expect("member count")
                .to_be_bytes(),
        );
        for member in members.into_iter().take(65_536) {
            push_str32(output, member);
        }
    }
}

fn append_stable_edge_f64(output: &mut Vec<u8>, data: &Value) {
    let names = ["edge_type", "source", "target", "qname"];
    let rows = sorted_rows(&data["edge_f64"], &names);
    append_count(output, 6, rows.len());
    for row in rows.into_iter().take(1_048_576) {
        for name in names {
            push_str32(output, text(row, name));
        }
        output.extend_from_slice(&f64_bits(text(row, "value_bits_hex")));
    }
}

fn append_stable_currency(output: &mut Vec<u8>, data: &Value) {
    let rows = sorted_rows(&data["node_currency"], &["local_name", "qname"]);
    append_count(output, 7, rows.len());
    for row in rows.into_iter().take(1_048_576) {
        push_str32(output, text(row, "local_name"));
        push_str32(output, text(row, "qname"));
        let value: i128 = text(row, "micro_units").parse().expect("i128 micro-units");
        output.extend_from_slice(&value.to_be_bytes());
    }
}

fn append_stable_hyperedge_f64(output: &mut Vec<u8>, data: &Value) {
    let rows = sorted_rows(&data["hyperedge_f64"], &["local_name", "qname"]);
    append_count(output, 8, rows.len());
    for row in rows.into_iter().take(1_048_576) {
        push_str32(output, text(row, "local_name"));
        push_str32(output, text(row, "qname"));
        output.extend_from_slice(&f64_bits(text(row, "value_bits_hex")));
    }
}

fn f64_bits(value: &str) -> [u8; 8] {
    let raw: [u8; 8] = hex_bytes(value).try_into().expect("binary64 bits");
    let bits = u64::from_be_bytes(raw);
    if bits << 1 == 0 {
        0u64.to_be_bytes()
    } else {
        bits.to_be_bytes()
    }
}

fn sorted_rows<'a>(value: &'a Value, fields: &[&str]) -> Vec<&'a Value> {
    let mut rows: Vec<_> = value.as_array().expect("semantic rows").iter().collect();
    rows.sort_unstable_by(|left, right| compare_fields(left, right, fields));
    rows
}

fn compare_fields(left: &Value, right: &Value, fields: &[&str]) -> Ordering {
    for field in fields.iter().take(4) {
        let order = text(left, field)
            .as_bytes()
            .cmp(text(right, field).as_bytes());
        if order != Ordering::Equal {
            return order;
        }
    }
    Ordering::Equal
}

fn action_id(data: &Value) -> Vec<u8> {
    let intent = hex_bytes(text(data, "intent_bytes_hex"));
    let intent_digest = sha256_of(&intent);
    assert_eq!(intent_digest, super::hex32(text(data, "intent_digest_hex")));
    action_preimage(text(data, "session"), &intent_digest)
}

fn action_preimage(session: &str, intent_digest: &[u8; 32]) -> Vec<u8> {
    let mut output = b"babylon.practice-action-id.v1\0".to_vec();
    output.extend_from_slice(&1u16.to_be_bytes());
    output.extend_from_slice(&str16(session));
    output.extend_from_slice(&2u16.to_be_bytes());
    output.extend_from_slice(intent_digest);
    output
}

fn ordered_action_batch(data: &Value) -> Vec<u8> {
    let mut output = b"babylon.ordered-practice-action-batch.v1\0".to_vec();
    output.extend_from_slice(&1u16.to_be_bytes());
    output.extend_from_slice(&str16(text(data, "session")));
    output.extend_from_slice(&unsigned(data, "resolve_tick").to_be_bytes());
    let items = data["items"].as_array().expect("ordered action items");
    output.extend_from_slice(
        &u16::try_from(items.len())
            .expect("action count")
            .to_be_bytes(),
    );
    for (index, item) in items.iter().take(4_096).enumerate() {
        assert_eq!(unsigned(item, "ordinal"), index as u64);
        let intent = hex_bytes(text(item, "intent_bytes_hex"));
        let action = sha256_of(&action_preimage(text(data, "session"), &sha256_of(&intent)));
        output.extend_from_slice(&u16::try_from(index).expect("action ordinal").to_be_bytes());
        output.extend_from_slice(&action);
        output.extend_from_slice(
            &u16::try_from(intent.len())
                .expect("intent length")
                .to_be_bytes(),
        );
        output.extend_from_slice(&intent);
    }
    output
}

fn vocabulary(data: &Value) -> Vec<u8> {
    if !data["present"].as_bool().expect("vocabulary presence") {
        return vec![0];
    }
    let mut output = vec![1];
    for (index, name) in ["node_type", "edge_type", "hyperedge_type", "event_type"]
        .iter()
        .enumerate()
    {
        let row = &data["kinds"][name];
        let present = row["present"].as_bool().expect("kind presence");
        output.extend_from_slice(&[
            u8::try_from(index + 1).expect("kind tag"),
            u8::from(present),
        ]);
        if present {
            let mut members: Vec<&str> = row["members"]
                .as_array()
                .expect("vocabulary members")
                .iter()
                .map(|value| value.as_str().expect("member text"))
                .collect();
            members.sort_unstable_by(|left, right| left.as_bytes().cmp(right.as_bytes()));
            output.extend_from_slice(
                &u32::try_from(members.len())
                    .expect("member count")
                    .to_be_bytes(),
            );
            for member in members.into_iter().take(1_048_576) {
                push_str32(&mut output, member);
            }
        }
    }
    output
}

fn prepared_environment(data: &Value, rows: &[VectorRow]) -> Vec<u8> {
    let mut output = b"babylon.prepared-environment\0".to_vec();
    output.extend_from_slice(&1u32.to_be_bytes());
    output.push(1);
    output.extend_from_slice(&hex_bytes(text(data, "rules_hash_hex")));
    output.push(2);
    output.extend_from_slice(
        &u32::try_from(unsigned(data, "phase_schedule_layout"))
            .expect("layout")
            .to_be_bytes(),
    );
    output.extend_from_slice(&hex_bytes(text(data, "phase_schedule_digest_hex")));
    append_prepared_rules(&mut output, data);
    append_prepared_fields(&mut output, data);
    append_prepared_intrinsics(&mut output, data);
    append_prepared_constants(&mut output, data);
    append_prepared_enums(&mut output, data);
    output.push(8);
    output.extend_from_slice(&vocabulary(&data["vocabulary"]));
    output.push(9);
    output.extend_from_slice(&1u32.to_be_bytes());
    output.extend_from_slice(&digest_by_id(rows, text(data, "resolver_manifest_id")));
    output.push(10);
    output.extend_from_slice(&1u32.to_be_bytes());
    output.extend_from_slice(&digest_by_id(rows, text(data, "register_manifest_id")));
    output
}

fn append_prepared_rules(output: &mut Vec<u8>, data: &Value) {
    let rules = data["rule_order"].as_array().expect("prepared rules");
    append_count(output, 3, rules.len());
    for rule in rules.iter().take(65_536) {
        push_str32(output, rule.as_str().expect("rule text"));
    }
}

fn append_prepared_fields(output: &mut Vec<u8>, data: &Value) {
    output.push(4);
    let rows = sorted_rows(&data["fields"], &["qname"]);
    output.extend_from_slice(
        &u32::try_from(rows.len())
            .expect("field count")
            .to_be_bytes(),
    );
    for row in rows.into_iter().take(65_536) {
        push_str32(output, text(row, "qname"));
        output.extend_from_slice(&bsl_type(&row["type"]));
        output.push(match text(row, "field_kind") {
            "intensive" => 1,
            "extensive" => 2,
            "not_applicable" => 3,
            _ => panic!("closed field kind"),
        });
    }
    let names = ["field", "reason", "owner", "date"];
    let exemptions = sorted_rows(&data["exemptions"], &names);
    output.extend_from_slice(
        &u32::try_from(exemptions.len())
            .expect("exemption count")
            .to_be_bytes(),
    );
    for row in exemptions.into_iter().take(64) {
        for name in names {
            push_str32(output, text(row, name));
        }
    }
}

fn append_prepared_intrinsics(output: &mut Vec<u8>, data: &Value) {
    output.push(5);
    let rows = sorted_rows(&data["intrinsics"], &["name"]);
    output.extend_from_slice(
        &u32::try_from(rows.len())
            .expect("intrinsic count")
            .to_be_bytes(),
    );
    for row in rows.into_iter().take(64) {
        push_str32(output, text(row, "name"));
        output.extend_from_slice(&unsigned(row, "cost").to_be_bytes());
    }
}

fn append_prepared_constants(output: &mut Vec<u8>, data: &Value) {
    output.push(6);
    let rows = sorted_rows(&data["constants"], &["qname"]);
    output.extend_from_slice(
        &u32::try_from(rows.len())
            .expect("constant count")
            .to_be_bytes(),
    );
    for row in rows.into_iter().take(65_536) {
        push_str32(output, text(row, "qname"));
        output.extend_from_slice(&bsl_value(&row["value"]));
    }
}

fn append_prepared_enums(output: &mut Vec<u8>, data: &Value) {
    output.push(7);
    let rows = sorted_rows(&data["enum_types"], &["name"]);
    output.extend_from_slice(&u32::try_from(rows.len()).expect("enum count").to_be_bytes());
    for row in rows.into_iter().take(65_536) {
        push_str32(output, text(row, "name"));
        let members = row["members"].as_array().expect("enum members");
        output.extend_from_slice(
            &u32::try_from(members.len())
                .expect("member count")
                .to_be_bytes(),
        );
        for member in members.iter().take(1_048_576) {
            push_str32(output, member.as_str().expect("member text"));
        }
    }
}

fn bsl_type(data: &Value) -> Vec<u8> {
    let kind = text(data, "kind");
    let tag = match kind {
        "probability" => 1,
        "intensity" => 2,
        "coefficient" => 3,
        "currency" => 4,
        "real" => 5,
        "int" => 6,
        "bool" => 7,
        "enum" => 8,
        "node_set" => 9,
        "edge_set" => 10,
        _ => panic!("closed BSL type"),
    };
    let mut output = vec![tag];
    if matches!(kind, "enum" | "node_set" | "edge_set") {
        push_str32(&mut output, text(data, "name"));
    }
    output
}

fn bsl_value(data: &Value) -> Vec<u8> {
    let mut output = Vec::new();
    match text(data, "kind") {
        "int" => {
            output.push(1);
            output.extend_from_slice(&integer(data, "value").to_be_bytes());
        }
        "currency" => {
            output.push(2);
            let value: i128 = text(data, "micro_units").parse().expect("Currency value");
            output.extend_from_slice(&value.to_be_bytes());
        }
        "real" => {
            output.push(3);
            output.extend_from_slice(&f64_bits(text(data, "value_bits_hex")));
        }
        "ratio" => append_ratio(&mut output, data),
        "bool" => output.extend_from_slice(&[5, u8::from(data["value"].as_bool().expect("bool"))]),
        "enum" => {
            output.push(6);
            push_str32(&mut output, text(data, "enum_type"));
            push_str32(&mut output, text(data, "member"));
        }
        "node_ref" | "hyperedge_ref" | "edge_ref" => append_reference(&mut output, data),
        _ => panic!("closed ValueV1 kind"),
    }
    output
}

fn append_ratio(output: &mut Vec<u8>, data: &Value) {
    output.push(4);
    output.extend_from_slice(&f64_bits(text(data, "value_bits_hex")));
    for name in ["floor_bits_hex", "cap_bits_hex"] {
        if data[name].is_null() {
            output.push(0);
        } else {
            output.push(1);
            output.extend_from_slice(&f64_bits(text(data, name)));
        }
    }
}

fn append_reference(output: &mut Vec<u8>, data: &Value) {
    let (tag, kind) = match text(data, "kind") {
        "node_ref" => (7, "node"),
        "hyperedge_ref" => (8, "hyperedge"),
        "edge_ref" => (9, "edge"),
        _ => unreachable!(),
    };
    let mut element = data["element"].clone();
    element["element_kind"] = Value::String(kind.to_owned());
    output.push(tag);
    output.extend_from_slice(&stable_element(&element));
}

fn register_manifest(data: &Value) -> Vec<u8> {
    let mut output = b"babylon.world-register-manifest\0".to_vec();
    output.extend_from_slice(&1u32.to_be_bytes());
    let entries = data["entries"].as_array().expect("register entries");
    output.extend_from_slice(
        &u32::try_from(entries.len())
            .expect("entry count")
            .to_be_bytes(),
    );
    for entry in entries.iter().take(1_048_576) {
        push_str32(&mut output, text(entry, "name"));
        output.extend_from_slice(
            &u32::try_from(unsigned(entry, "layout"))
                .expect("layout")
                .to_be_bytes(),
        );
    }
    output
}

fn register_set(data: &Value, rows: &[VectorRow]) -> Vec<u8> {
    let mut output = b"babylon.world-register-set\0".to_vec();
    output.extend_from_slice(&1u32.to_be_bytes());
    output.push(1);
    output.extend_from_slice(&1u32.to_be_bytes());
    output.extend_from_slice(&digest_by_id(rows, text(data, "register_manifest_id")));
    output.push(2);
    let entries = data["entries"].as_array().expect("register entries");
    output.extend_from_slice(
        &u32::try_from(entries.len())
            .expect("entry count")
            .to_be_bytes(),
    );
    for entry in entries.iter().take(1_048_576) {
        push_str32(&mut output, text(entry, "name"));
        output.extend_from_slice(
            &u32::try_from(unsigned(entry, "layout"))
                .expect("layout")
                .to_be_bytes(),
        );
        output.extend_from_slice(&8u32.to_be_bytes());
        output.extend_from_slice(&integer(entry, "completed_tick").to_be_bytes());
    }
    output
}

fn stable_world(data: &Value, rows: &[VectorRow]) -> Vec<u8> {
    let mut output = b"babylon.stable-world\0".to_vec();
    output.extend_from_slice(&1u32.to_be_bytes());
    output.push(1);
    output.extend_from_slice(&1u32.to_be_bytes());
    output.extend_from_slice(&digest_by_id(rows, text(data, "stable_graph_id")));
    output.push(2);
    output.extend_from_slice(&1u32.to_be_bytes());
    output.extend_from_slice(&digest_by_id(rows, text(data, "register_set_id")));
    output
}

fn tick_payload(data: &Value) -> Vec<u8> {
    let mut output = b"babylon.tick-payload\0".to_vec();
    output.extend_from_slice(&1u32.to_be_bytes());
    append_payload_outcomes(&mut output, data);
    append_payload_events(&mut output, data);
    append_payload_receipts(&mut output, data);
    output.extend_from_slice(&[4, 0, 0]);
    output
}

fn append_payload_outcomes(output: &mut Vec<u8>, data: &Value) {
    let rows = data["rule_outcomes"].as_array().expect("rule outcomes");
    append_count(output, 1, rows.len());
    for row in rows.iter().take(65_536) {
        push_str32(output, text(row, "rule"));
        output.extend_from_slice(&unsigned(row, "fired").to_be_bytes());
    }
}

fn append_payload_events(output: &mut Vec<u8>, data: &Value) {
    let rows = data["events"].as_array().expect("events");
    append_count(output, 2, rows.len());
    for row in rows.iter().take(1_048_576) {
        push_str32(output, text(row, "event"));
        let payload = row["payload"].as_array().expect("payload items");
        output.extend_from_slice(
            &u32::try_from(payload.len())
                .expect("payload count")
                .to_be_bytes(),
        );
        for item in payload.iter().take(1_048_576) {
            push_str32(output, text(item, "label"));
            output.extend_from_slice(&bsl_value(&item["value"]));
        }
    }
}

fn append_payload_receipts(output: &mut Vec<u8>, data: &Value) {
    let rows = data["receipts"].as_array().expect("receipts");
    append_count(output, 3, rows.len());
    for row in rows.iter().take(1_048_576) {
        push_str32(output, text(row, "rule"));
        output.push(tag(
            text(row, "role"),
            &["mechanic", "recognizer", "external_event", "intent"],
        ));
        output.push(tag(
            text(row, "evidence"),
            &["observed", "derived", "calibrated", "designed"],
        ));
        output.extend_from_slice(
            &u32::try_from(unsigned(row, "ordinal"))
                .expect("ordinal")
                .to_be_bytes(),
        );
        output.extend_from_slice(&effect(&row["effect"]));
    }
}

fn effect(data: &Value) -> Vec<u8> {
    let kind = text(data, "kind");
    if let Some(index) = ["node_field", "edge_field", "hyperedge_field"]
        .iter()
        .position(|value| *value == kind)
    {
        let mut output = vec![u8::try_from(index + 1).expect("effect tag")];
        push_str32(&mut output, text(data, "qname"));
        return output;
    }
    if kind == "event" {
        let mut output = vec![4];
        push_str32(&mut output, text(data, "event"));
        return output;
    }
    vec![
        5,
        tag(
            text(data, "verb"),
            &[
                "add_node",
                "remove_node",
                "add_edge",
                "remove_edge",
                "add_hyperedge",
                "remove_hyperedge",
            ],
        ),
    ]
}

fn tag(value: &str, choices: &[&str]) -> u8 {
    u8::try_from(
        choices
            .iter()
            .position(|choice| *choice == value)
            .expect("closed tag")
            + 1,
    )
    .expect("u8 tag")
}

fn tick_content(data: &Value, rows: &[VectorRow]) -> Vec<u8> {
    validate_outer_action_link(data, rows).expect("exact-empty runtime action link");
    let mut output = b"babylon.tick-content\0".to_vec();
    output.extend_from_slice(&layout(data, "outer", 1).to_be_bytes());
    output.push(1);
    output.extend_from_slice(&layout(data, "session", 1).to_be_bytes());
    output.extend_from_slice(&str16(text(data, "session")));
    output.push(2);
    output.extend_from_slice(&unsigned(data, "resolve_tick").to_be_bytes());
    output.push(3);
    output.extend_from_slice(&layout(data, "seed", 1).to_be_bytes());
    output.extend_from_slice(&layout(data, "rng", 2).to_be_bytes());
    output.extend_from_slice(&integer(data, "seed").to_be_bytes());
    output.push(4);
    output.extend_from_slice(&layout(data, "content", 1).to_be_bytes());
    output.extend_from_slice(&hex_bytes(text(data, "defines_digest_hex")));
    output.extend_from_slice(&hex_bytes(text(data, "rules_digest_hex")));
    for (tag, name) in [
        "reference",
        "prepared",
        "prior_world",
        "actions",
        "result_world",
        "payload",
    ]
    .iter()
    .enumerate()
    {
        output.push(u8::try_from(tag + 5).expect("outer tag"));
        output.extend_from_slice(&layout(data, name, 1).to_be_bytes());
        output.extend_from_slice(&outer_digest(data, rows, name));
    }
    output
}

fn validate_outer_action_link(data: &Value, rows: &[VectorRow]) -> Result<(), &'static str> {
    let action = row_by_id(rows, text(data, "actions_id"));
    if action.kind != "ordered_action_batch" {
        return Err("runtime_actions_link");
    }
    let action_data = &action.data;
    if !action_data["items"]
        .as_array()
        .ok_or("runtime_actions_link")?
        .is_empty()
    {
        return Err("nonempty_runtime_actions");
    }
    if text(action_data, "session") != text(data, "session") {
        return Err("action_session_mismatch");
    }
    if unsigned(action_data, "resolve_tick") != unsigned(data, "resolve_tick") {
        return Err("action_tick_mismatch");
    }
    Ok(())
}

fn layout(data: &Value, name: &str, default: u32) -> u32 {
    data["layout_overrides"][name]
        .as_u64()
        .map_or(default, |value| u32::try_from(value).expect("layout u32"))
}

fn outer_digest(data: &Value, rows: &[VectorRow], name: &str) -> [u8; 32] {
    let direct = format!("{name}_digest_hex");
    if let Some(value) = data[&direct].as_str() {
        return super::hex32(value);
    }
    let linked = format!("{name}_id");
    digest_by_id(rows, text(data, &linked))
}

fn digest_by_id(rows: &[VectorRow], id: &str) -> [u8; 32] {
    let row = row_by_id(rows, id);
    let canonical = hex_bytes(text(&row.data, "canonical_hex"));
    sha256_of(&canonical)
}

pub(super) fn verify_every_canonical_row(rows: &[VectorRow]) {
    for row in rows.iter().take(MAX_ROWS) {
        if matches!(row.kind.as_str(), "mutation" | "refusal") {
            continue;
        }
        let Some(expected) = row.data["canonical_hex"].as_str() else {
            continue;
        };
        let actual =
            canonical(row, rows).unwrap_or_else(|| panic!("{} needs a semantic builder", row.id));
        assert_eq!(actual, hex_bytes(expected), "{}", row.id);
    }
}

pub(super) fn verify_every_outer_mutation(rows: &[VectorRow]) {
    for mutation in rows
        .iter()
        .take(MAX_ROWS)
        .filter(|row| row.kind == "mutation")
    {
        let data = &mutation.data;
        let base = row_by_id(rows, text(data, "base_id"));
        let mut changed = base.data.clone();
        let field = text(data, "field");
        if let Some(name) = field.strip_prefix("layout_overrides.") {
            changed["layout_overrides"][name] = data["replacement"].clone();
        } else {
            changed[field] = data["replacement"].clone();
            if let Some(name) = field.strip_suffix("_digest_hex") {
                changed
                    .as_object_mut()
                    .expect("outer data mapping")
                    .remove(&format!("{name}_id"));
            }
        }
        if let Some(actions_id) = data["derived_actions_id"].as_str() {
            changed["actions_id"] = Value::String(actions_id.to_owned());
        }
        let actual = tick_content(&changed, rows);
        assert_ne!(actual, tick_content(&base.data, rows), "{}", mutation.id);
        assert_eq!(
            sha256_of(&actual),
            super::hex32(text(data, "after_digest_hex")),
            "{}",
            mutation.id
        );
    }
}

pub(super) fn verify_every_refusal(rows: &[VectorRow]) {
    let refusals: Vec<_> = rows
        .iter()
        .take(MAX_ROWS)
        .filter(|row| row.kind == "refusal")
        .collect();
    assert!(!refusals.is_empty(), "shared refusal rows");
    for row in refusals.into_iter().take(MAX_ROWS) {
        verify_refusal(row, rows);
    }
}

fn verify_refusal(row: &VectorRow, rows: &[VectorRow]) {
    let data = &row.data;
    match text(data, "operation") {
        "session" => assert_eq!(
            session_refusal(text(data, "value")),
            text(data, "expected_code")
        ),
        "bsl_value" => assert_eq!(
            bsl_value_refusal(&data["value"]),
            text(data, "expected_code")
        ),
        "option_byte" => {
            assert_eq!(unsigned(data, "value"), 2);
            assert_eq!(text(data, "expected_code"), "invalid_option");
        }
        "ordered_tags" => verify_tag_refusal(data),
        "outer_action_link" => {
            let mut outer = row_by_id(rows, text(data, "outer_id")).data.clone();
            outer["actions_id"] = Value::String(text(data, "actions_id").to_owned());
            assert_eq!(
                validate_outer_action_link(&outer, rows),
                Err(text(data, "expected_code")),
                "{}",
                row.id
            );
        }
        "bound_case" => verify_bound_case(data),
        operation => panic!("unexecuted shared refusal operation {operation}"),
    }
}

fn session_refusal(value: &str) -> &'static str {
    if !value.is_ascii() {
        return "non_ascii";
    }
    if value.len() > 256 {
        return "string_too_long";
    }
    if value.is_empty() || value.bytes().any(|byte| !(0x21..=0x7e).contains(&byte)) {
        return "non_graphic_ascii";
    }
    "missing_refusal"
}

fn bsl_value_refusal(value: &Value) -> &'static str {
    if text(value, "kind") == "bool" && value["value"].as_bool().is_none() {
        return "noncanonical_boolean";
    }
    let bits = u64::from_be_bytes(
        hex_bytes(text(value, "value_bits_hex"))
            .try_into()
            .expect("binary64 refusal bits"),
    );
    if bits & 0x7ff0_0000_0000_0000 == 0x7ff0_0000_0000_0000 {
        "non_finite"
    } else {
        "missing_refusal"
    }
}

fn verify_tag_refusal(data: &Value) {
    let expected: Vec<u8> = data["expected_tags"]
        .as_array()
        .expect("expected tags")
        .iter()
        .take(10)
        .map(|value| u8::try_from(value.as_u64().expect("tag")).expect("u8 tag"))
        .collect();
    let actual = verify_fixed_tags(
        &hex_bytes(text(data, "canonical_hex")),
        &expected,
        usize::try_from(unsigned(data, "payload_bytes")).expect("payload bytes"),
    );
    let expected = match text(data, "expected_code") {
        "unknown_tag" => TagRefusal::Unknown,
        "truncated" => TagRefusal::Truncated,
        "trailing_bytes" => TagRefusal::Trailing,
        "tag_order" => TagRefusal::Order,
        code => panic!("unknown tag refusal code {code}"),
    };
    assert_eq!(actual, Err(expected));
}

fn verify_bound_case(data: &Value) {
    let name = text(data, "bound");
    let (input, maximum, expected_code) = bound_contract(name);
    assert_eq!(text(data, "expected_code"), expected_code);
    let accepted = unsigned(&data["accepted_input"], input);
    let refused = unsigned(&data["refused_input"], input);
    assert_eq!(accepted, maximum, "{name} accepted maximum");
    assert_eq!(refused, maximum + 1, "{name} refused maximum plus one");
    assert_eq!(check_bound(accepted, maximum, expected_code), Ok(()));
    assert_eq!(
        check_bound(refused, maximum, expected_code),
        Err(expected_code)
    );
}

const fn check_bound(
    actual: u64,
    maximum: u64,
    expected_code: &'static str,
) -> Result<(), &'static str> {
    if actual <= maximum {
        Ok(())
    } else {
        Err(expected_code)
    }
}

fn bound_contract(name: &str) -> (&'static str, u64, &'static str) {
    match name {
        "vector_rows" => ("vector_file_rows", 256, "too_many_rows"),
        "vector_line_bytes" => ("vector_line_bytes", 262_144, "invalid_line_length"),
        "replay_session_bytes" => ("replay_session_bytes", 256, "string_too_long"),
        "rng_domain_bytes" => ("rng_domain_bytes", 128, "rng_domain_length"),
        "rng_domain_segments" => ("rng_domain_segments", 4, "rng_domain_segments"),
        "symbol_bytes" => ("symbol_bytes", 64, "invalid_symbol"),
        "qname_bytes" => ("qname_bytes", 128, "invalid_qname"),
        "qname_segments" => ("qname_segments", 4, "invalid_qname"),
        "structural_type_bytes" => ("structural_type_bytes", 128, "invalid_structural_type"),
        "intrinsic_identity_bytes" => {
            ("intrinsic_identity_bytes", 96, "invalid_intrinsic_identity")
        }
        "enum_type_bytes" => ("enum_type_bytes", 64, "invalid_enum_type"),
        "enum_member_bytes" => ("enum_member_bytes", 64, "invalid_enum_member"),
        "governance_utf8_bytes" => (
            "governance_utf8_bytes",
            4_194_304,
            "governance_string_too_long",
        ),
        "stable_carrier_active_elements" => (
            "stable_carrier_active_elements",
            256,
            "active_element_limit",
        ),
        "stable_carrier_bytes" => ("stable_carrier_bytes", 131_072, "byte_limit"),
        "resolver_rows" => ("resolver_rows", 65_536, "row_limit"),
        "resolver_hyperedge_members" => ("resolver_hyperedge_members", 65_536, "hyperedge_members"),
        "resolver_fact_units" => ("resolver_fact_units", 1_048_576, "aggregate_row_limit"),
        "resolver_manifest_bytes" => ("resolver_manifest_bytes", 16_777_216, "byte_limit"),
        "stable_graph_elements" => ("stable_graph_elements", 65_536, "row_limit"),
        "stable_graph_attribute_rows" => ("stable_graph_attribute_rows", 1_048_576, "row_limit"),
        "stable_graph_hyperedge_members" => (
            "stable_graph_hyperedge_members",
            65_536,
            "hyperedge_members",
        ),
        "stable_graph_fact_units" => ("stable_graph_fact_units", 1_048_576, "aggregate_row_limit"),
        "stable_graph_bytes" => ("stable_graph_bytes", 67_108_864, "byte_limit"),
        "ordered_action_items" => ("ordered_action_items", 4_096, "row_limit"),
        "practice_intent_bytes" => ("practice_intent_bytes", 16_384, "intent_length"),
        "ordered_action_batch_bytes" => ("ordered_action_batch_bytes", 67_256_631, "byte_limit"),
        "prepared_rows" => ("prepared_rows", 65_536, "row_limit"),
        "prepared_small_rows" => ("prepared_small_rows", 64, "row_limit"),
        "identity_members" => ("identity_members", 1_048_576, "row_limit"),
        "identity_aggregate_rows" => ("identity_aggregate_rows", 1_048_576, "aggregate_row_limit"),
        "identity_section_bytes" => ("identity_section_bytes", 67_108_864, "byte_limit"),
        "tick_rule_outcomes" => ("tick_rule_outcomes", 65_536, "row_limit"),
        "tick_rows" => ("tick_rows", 1_048_576, "row_limit"),
        _ => panic!("unknown bound refusal {name}"),
    }
}
