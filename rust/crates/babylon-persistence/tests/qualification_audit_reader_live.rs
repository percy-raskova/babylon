//! Read-only regression against an explicitly selected, already committed national P1.
//! Run with `--ignored --exact standalone_material_read_retains_admission_through_serialization`.
//! `BABYLON_MATERIAL_AUDIT_FIXTURE` names the nonsecret JSON identity/policy fixture;
//! the two existing national storage DSN variables supply restricted credentials.
use babylon_persistence::identity::CampaignId;
use babylon_persistence::qualification_audit::policy;
use babylon_persistence::qualification_audit::policy::FrozenPolicy;
use babylon_persistence::qualification_audit::reader::{ReadSession, Request};
use postgres::Config;
use serde::Deserialize;
use serde_json::Value;
use std::path::PathBuf;
use uuid::Uuid;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Fixture {
    campaign: String,
    foundation_sha256: String,
    policy_path: PathBuf,
    policy_sha256: String,
    tick_content_hash: String,
    nominal_world_hash: String,
    canonical_receipt_sha256: String,
}

#[test]
#[ignore = "requires an explicitly selected committed national P1 and restricted observer/Archive DSNs; read only"]
fn standalone_material_read_retains_admission_through_serialization() {
    let path = std::env::var_os("BABYLON_MATERIAL_AUDIT_FIXTURE")
        .expect("explicit retained P1 fixture path required");
    let fixture: Fixture = serde_json::from_slice(
        &std::fs::read(path).expect("the nonsecret fixture file is readable"),
    )
    .expect("the fixture has the declared identity and policy fields");
    let policy = FrozenPolicy::open(
        &fixture.policy_path,
        policy::canonical_digest(&fixture.policy_sha256).expect("canonical policy hash"),
        1,
    )
    .expect("the fixture selects the unchanged qualification policy");
    let scope = policy.scope(
        CampaignId::from_uuid(Uuid::parse_str(&fixture.campaign).expect("canonical campaign UUID")),
        policy::canonical_digest(&fixture.foundation_sha256).expect("canonical foundation hash"),
    );
    let observer: Config = std::env::var("BABYLON_NATIONAL_STORAGE_OBSERVER_DSN")
        .expect("restricted observer DSN required")
        .parse()
        .expect("the observer DSN has valid configuration syntax");
    let archive = std::env::var("BABYLON_NATIONAL_STORAGE_READER_DSN")
        .expect("restricted Archive DSN required");
    let request = Request {
        version: 1,
        tick: 1,
        tick_content_hash: fixture.tick_content_hash.clone(),
    };
    let result = {
        let mut session = ReadSession::new(scope, &observer, &archive)
            .expect("the selected read-only session is admitted");
        session
            .read(&request)
            .expect("standalone material read must retain its admission through the audit")
    };
    // The public result owns everything needed by the operator's JSON boundary.
    let bytes = serde_json::to_vec(&result).expect("material facts serialize after session drop");
    let output: Value = serde_json::from_slice(&bytes).expect("valid facts JSON");
    let facts = &output["facts"];
    assert_eq!(facts["campaign"], fixture.campaign);
    assert_eq!(facts["foundation_sha256"], fixture.foundation_sha256);
    assert_eq!(facts["policy_sha256"], fixture.policy_sha256);
    assert_eq!(facts["tick"], 1);
    assert_eq!(facts["tick_content_hash"], fixture.tick_content_hash);
    assert_eq!(facts["nominal_world_hash"], fixture.nominal_world_hash);
    assert_eq!(
        facts["canonical_receipt_sha256"],
        fixture.canonical_receipt_sha256
    );
    for audit in ["economic", "trade"] {
        assert_eq!(facts[audit]["tick_content_hash"], fixture.tick_content_hash);
        assert_eq!(
            facts[audit]["canonical_receipt_sha256"],
            fixture.canonical_receipt_sha256
        );
    }
    assert_eq!(output["archive"]["durable_tick"], 1);
    assert_eq!(output["archive"]["processed_tick"], 1);
    assert_eq!(output["archive"]["pending_count"], 0);
    policy
        .verify()
        .expect("the selected policy remains unchanged");
}
