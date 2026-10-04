use super::*;
use serde_json::{json, Value};

fn document() -> Value {
    serde_json::from_str(&decode_gzip(ARTIFACT).unwrap()).unwrap()
}
fn refused(value: &Value) -> NationalTransportError {
    parse(&serde_json::to_string(value).unwrap()).unwrap_err()
}
#[test]
fn malformed_mode_and_bulk_air_are_refused() {
    let mut value = document();
    let row = value["links"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|row| row["mode"] == "air")
        .unwrap();
    row["cargo"] = json!(["dry_bulk", "general"]);
    assert_eq!(refused(&value), NationalTransportError::ModeCargo);
    value["links"][0]["mode"] = json!("teleport");
    assert_eq!(refused(&value), NationalTransportError::Json);
}
#[test]
fn duplicate_nonroster_and_missing_pool_are_refused() {
    let mut value = document();
    let repeated = value["nodes"][0].clone();
    value["nodes"].as_array_mut().unwrap().push(repeated);
    assert_eq!(refused(&value), NationalTransportError::Node);
    let mut value = document();
    value["nodes"][0]["location"] = json!("county:99999");
    assert_eq!(refused(&value), NationalTransportError::County);
    let mut value = document();
    value["links"][0]["pools"] = json!(["missing"]);
    assert_eq!(refused(&value), NationalTransportError::Pool);
}
#[test]
fn finite_policy_and_audit_claims_cannot_drift() {
    let mut value = document();
    value["policy"]["service_profiles"]["air_feeder"]["capacity_grams"] = json!(0);
    assert_eq!(refused(&value), NationalTransportError::Policy);
    let mut value = document();
    value["audit"]["general_diameter"] = json!(1);
    assert_eq!(refused(&value), NationalTransportError::Audit);
}
#[test]
fn island_lost_path_cannot_pass_reachability() {
    let mut value = document();
    value["links"]
        .as_array_mut()
        .unwrap()
        .retain(|row| row["from"] != "airport:LUP" || row["mode"] != "air");
    assert_eq!(refused(&value), NationalTransportError::Reachability);
}
#[test]
fn decimal_and_compression_refuse_nonfinite_overflow_and_trailing_members() {
    for token in ["NaN", "inf", "-1", "1E99999", "1E-32768"] {
        assert_eq!(
            validate::decimal(token),
            Err(NationalTransportError::Decimal)
        );
    }
    for token in ["0", "0.000000", "100.000001", "1E-12"] {
        validate::decimal(token).unwrap();
    }
    let mut bytes = ARTIFACT.to_vec();
    bytes.extend_from_slice(ARTIFACT);
    assert_eq!(
        decode_gzip(&bytes),
        Err(NationalTransportError::Compression)
    );
}

#[test]
fn island_ground_shortcut_and_foreign_flow_relabel_are_refused() {
    let mut value = document();
    let row = value["links"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|row| row["from"] == "airport:LUP" && row["mode"] == "air")
        .unwrap();
    row["mode"] = json!("truck");
    row["profile"] = json!("local_road");
    assert_eq!(refused(&value), NationalTransportError::Access);
    let mut value = document();
    value["flows"]["foreign"][0]["key"][1] = json!("china");
    assert_eq!(refused(&value), NationalTransportError::Flow);
    let mut value = document();
    value["flows"]["source_rows"] = json!(1);
    assert_eq!(refused(&value), NationalTransportError::Flow);
}
