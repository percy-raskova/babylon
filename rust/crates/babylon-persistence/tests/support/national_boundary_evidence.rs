//! Complete real reader proofs at the same committed national boundary.
use babylon_kernel::economic_location::EconomicLocation;
use babylon_persistence::{
    archive_revision::{ArchiveDossierBounds, ArchiveDossierState, ArchiveReadScope},
    identity::CampaignId,
    observer_reader::CommittedMaterialObservation,
    ArchivePageRef, ArchiveSubjectKind, SemanticArchiveReader,
};
use babylon_tick::material_replay::IdentifiedMaterialTick;
use postgres::{Config, NoTls};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{collections::BTreeSet, path::PathBuf, time::Duration};

pub(super) struct Limits {
    pub archive: Duration,
    pub production: Duration,
    pub policy_sha256: String,
}

pub(super) fn limits() -> Limits {
    let directory = PathBuf::from(std::env::var("BABYLON_STORAGE_REPORT_DIRECTORY").unwrap());
    let bytes = std::fs::read(directory.join("policy.json")).unwrap();
    limits_from_bytes(&bytes)
}

fn limits_from_bytes(bytes: &[u8]) -> Limits {
    let policy: Value = serde_json::from_slice(bytes).expect("captured qualification policy JSON");
    assert_eq!(
        policy["version"].as_u64(),
        Some(3),
        "unsupported captured qualification policy version"
    );
    assert_eq!(
        policy["name"].as_str(),
        Some("national_storage_qualification_v3"),
        "unsupported captured qualification policy identity"
    );
    assert_eq!(
        policy["storage_charge_method"].as_str(),
        Some("positive_growth_by_component_and_boundary_v1"),
        "unsupported captured qualification storage charge method"
    );
    assert_eq!(policy["county_count"].as_u64(), Some(3_144));
    let seconds = |key: &str| {
        let value = policy[key].as_u64().expect("captured exact phase budget");
        assert!(
            value > 0 && i64::try_from(value).is_ok(),
            "captured phase budget must be a positive signed-range integer"
        );
        Duration::from_secs(value)
    };
    Limits {
        archive: seconds("maximum_archive_catchup_seconds"),
        production: seconds("maximum_production_read_seconds"),
        policy_sha256: hex(&Sha256::digest(bytes)),
    }
}

#[cfg(test)]
mod policy_tests {
    use super::{hex, limits_from_bytes};
    use serde_json::{json, Value};
    use sha2::{Digest, Sha256};
    use std::time::Duration;

    const CURRENT_POLICY: &[u8] =
        include_bytes!("../../../../../contracts/national_storage_qualification_v3.json");

    #[test]
    fn captured_qualification_policy_reads_current_contract() {
        let limits = limits_from_bytes(CURRENT_POLICY);
        assert_eq!(limits.archive, Duration::from_secs(180));
        assert_eq!(limits.production, Duration::from_secs(180));
        assert_eq!(limits.policy_sha256, hex(&Sha256::digest(CURRENT_POLICY)));
    }

    #[test]
    fn captured_qualification_policy_uses_captured_overrides_and_byte_hash() {
        let mut policy: Value = serde_json::from_slice(CURRENT_POLICY).unwrap();
        policy["maximum_archive_catchup_seconds"] = json!(75);
        policy["maximum_production_read_seconds"] = json!(120);
        let bytes = serde_json::to_vec(&policy).unwrap();
        let limits = limits_from_bytes(&bytes);
        assert_eq!(limits.archive, Duration::from_secs(75));
        assert_eq!(limits.production, Duration::from_secs(120));
        assert_eq!(limits.policy_sha256, hex(&Sha256::digest(&bytes)));
        let mut differently_spaced = bytes.clone();
        differently_spaced.push(b'\n');
        assert_eq!(
            limits_from_bytes(&differently_spaced).archive,
            limits.archive
        );
        assert_ne!(
            limits_from_bytes(&differently_spaced).policy_sha256,
            limits.policy_sha256
        );
    }

    #[test]
    fn captured_qualification_policy_refuses_unsupported_identity_and_budgets() {
        for (key, invalid) in [
            ("version", json!(1)),
            ("version", json!(2)),
            ("version", json!(4)),
            ("version", Value::Null),
            ("name", json!("national_storage_qualification_v2")),
            ("storage_charge_method", json!("net_growth")),
            ("county_count", json!(3_143)),
            ("maximum_archive_catchup_seconds", json!(0)),
            ("maximum_archive_catchup_seconds", json!(-1)),
            ("maximum_production_read_seconds", json!(1.5)),
            ("maximum_production_read_seconds", json!(u64::MAX)),
        ] {
            let mut policy: Value = serde_json::from_slice(CURRENT_POLICY).unwrap();
            policy[key] = invalid.clone();
            let bytes = serde_json::to_vec(&policy).unwrap();
            assert!(
                std::panic::catch_unwind(|| limits_from_bytes(&bytes)).is_err(),
                "unsupported captured policy admitted: {key}={invalid}"
            );
        }
    }
}

pub(super) fn hex(bytes: &[u8]) -> String {
    use std::fmt::Write;
    let mut result = String::with_capacity(bytes.len().checked_mul(2).unwrap());
    for byte in bytes {
        write!(&mut result, "{byte:02x}").unwrap();
    }
    result
}

pub(super) fn archive_boundary(
    writer: &Config,
    campaign: CampaignId,
    tick: u64,
    expected_hash: &str,
) -> Value {
    let reader = SemanticArchiveReader::from_dsn(
        &std::env::var("BABYLON_NATIONAL_STORAGE_READER_DSN")
            .expect("separate confined Archive reader required"),
    )
    .unwrap();
    let marker = reader.committed_tick_status(campaign).unwrap().unwrap();
    assert_eq!(marker.resolve_tick(), tick);
    assert_eq!(hex(marker.tick_content_hash()), expected_hash);
    let progress = reader
        .archive_verification_status(campaign)
        .unwrap()
        .unwrap();
    assert_eq!(progress.durable_tick(), tick);
    assert_eq!(progress.processed_tick(), tick);
    let scope = ArchiveReadScope::committed(campaign, tick, *marker.tick_content_hash()).unwrap();
    let mut dossier_bytes = Vec::new();
    for subject in [
        ArchivePageRef::try_new(ArchiveSubjectKind::County, "26163".into()).unwrap(),
        ArchivePageRef::try_new(ArchiveSubjectKind::Organization, "2616301".into()).unwrap(),
    ] {
        let read = reader
            .dossier_as_of(&scope, &subject, &ArchiveDossierBounds::default())
            .unwrap();
        assert_eq!(read.scope, scope);
        assert_eq!(read.subject, subject);
        assert_eq!(read.durable_tick, tick);
        assert_eq!(read.processed_tick, tick);
        let ArchiveDossierState::Ready {
            page,
            verified_through_tick,
        } = read.state
        else {
            panic!("committed boundary requires ready county and organizer dossiers")
        };
        assert_eq!(verified_through_tick, tick);
        assert!(page.content_source.tick() <= tick);
        assert!(!page.markdown.is_empty());
        assert!(!page.citations.is_empty());
        dossier_bytes.extend_from_slice(&page.revision_id);
        dossier_bytes.extend_from_slice(&page.content_sha256);
        dossier_bytes.extend_from_slice(&Sha256::digest(page.markdown.as_bytes()));
    }
    let tick_sql = i64::try_from(tick).unwrap();
    let pending: i64 = writer
        .connect(NoTls)
        .unwrap()
        .query_one(
            "SELECT count(*) FROM babylon_state.archive_dirty_receipt_v1 r \
         WHERE r.campaign_id=$1 AND r.resolve_tick<=$2 AND NOT EXISTS \
         (SELECT 1 FROM babylon_meta.archive_receipt_consumption_v1 c \
          WHERE c.campaign_id=r.campaign_id AND c.resolve_tick=r.resolve_tick)",
            &[campaign.as_uuid(), &tick_sql],
        )
        .unwrap()
        .get(0);
    assert_eq!(pending, 0);
    json!({"processed_tick":progress.processed_tick(),"durable_tick":progress.durable_tick(),
        "expected_tick":tick,"pending_count":pending,"dossier_sha256":hex(&Sha256::digest(dossier_bytes))})
}

pub(super) fn production_boundary(
    observation: &CommittedMaterialObservation,
    campaign: CampaignId,
    tick: u64,
    foundation: &str,
    admitted: &IdentifiedMaterialTick,
) -> (Value, Vec<String>) {
    let snapshot = &observation.snapshot;
    let world = hex(&admitted.result_world_hash());
    assert_eq!(snapshot.campaign_id, campaign.as_uuid().to_string());
    assert_eq!(snapshot.resolve_tick, tick);
    assert_eq!(admitted.resolve_tick(), tick);
    assert_eq!(snapshot.foundation_digest, foundation);
    assert_eq!(hex(&admitted.foundation_digest()), foundation);
    assert_eq!(snapshot.nominal_world_hash.as_deref(), Some(world.as_str()));
    assert_eq!(
        snapshot.tick_content_hash.as_deref(),
        Some(hex(admitted.tick_content_hash().as_bytes()).as_str())
    );
    let counties: BTreeSet<_> = snapshot
        .counties
        .iter()
        .map(|c| c.county_geoid.clone())
        .collect();
    let reference = babylon_persistence::national_counties::national_county_reference().unwrap();
    let expected: BTreeSet<_> = reference
        .counties()
        .iter()
        .map(|c| c.geoid().to_string())
        .collect();
    assert_eq!(snapshot.counties.len(), 3_144);
    assert_eq!(
        counties, expected,
        "exact captured national county identity"
    );
    let production = snapshot
        .production
        .as_ref()
        .expect("complete production required");
    assert!(!production.household_accounts.is_empty());
    assert!(production.material_balance.is_some());
    let foreign: BTreeSet<_> = production
        .sites
        .iter()
        .filter_map(|site| match site.location {
            EconomicLocation::Foreign(counterpart) => Some(counterpart),
            _ => None,
        })
        .collect();
    let dependencies: BTreeSet<_> = production
        .sites
        .iter()
        .filter_map(|site| match site.location {
            EconomicLocation::Dependency(dependency) => Some(dependency),
            _ => None,
        })
        .collect();
    assert_eq!(foreign.len(), 12);
    assert_eq!(dependencies.len(), 6);
    let digest = &observation.production_evidence;
    let geoids: Vec<_> = counties.into_iter().collect();
    let roster_digest = hex(&Sha256::digest(serde_json::to_vec(&geoids).unwrap()));
    (
        json!({"tick":tick,"nominal_world_hash":world,"snapshot_sha256":digest.to_hex(),
        "county_roster_sha256":roster_digest}),
        geoids,
    )
}

pub(super) fn boundary(
    writer: &Config,
    campaign: CampaignId,
    tick: u64,
    foundation: &str,
    admitted: &IdentifiedMaterialTick,
    archive: &Value,
    production: &Value,
) -> Value {
    let tick_sql = i64::try_from(tick).unwrap();
    let row = writer.connect(NoTls).unwrap().query_one(
        "SELECT encode(t.tick_content_hash,'hex'),encode(t.envelope_digest,'hex'), \
         encode(sha256(m.register_storage_bytes),'hex'),encode(sha256(m.receipt_storage_bytes),'hex'), \
         encode(sha256(m.lookup_delta_bytes),'hex') FROM babylon_state.tick_commit t \
         JOIN babylon_state.material_tick_v3 m USING(campaign_id,resolve_tick) \
         WHERE t.campaign_id=$1 AND t.resolve_tick=$2",
        &[campaign.as_uuid(), &tick_sql],
    ).unwrap();
    let tick_hash: String = row.get(0);
    assert_eq!(tick_hash, hex(admitted.tick_content_hash().as_bytes()));
    json!({"tick":tick,"campaign":campaign.as_uuid().to_string(),"foundation_sha256":foundation,
        "tick_content_hash":tick_hash,"envelope_digest":row.get::<_,String>(1),
        "register_storage_sha256":row.get::<_,String>(2),"receipt_storage_sha256":row.get::<_,String>(3),
        "lookup_storage_sha256":row.get::<_,String>(4),"canonical_receipt_sha256":hex(&admitted.receipt_digest()),
        "nominal_world_hash":hex(&admitted.result_world_hash()),"archive":archive,"production":production})
}
