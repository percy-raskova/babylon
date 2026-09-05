use std::{process::Command, sync::OnceLock};

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_practice_contract::ordered_action_v1::OrderedPracticeActionBatchV1;
use babylon_tick::{
    material_replay::MaterialReplaySessionV3, material_world::decode_material_receipts_v3,
    replay_session::ReplayCommitDispositionV1,
};
use serde_json::Value;

use super::*;
use crate::{
    material_envelope::CommittedMaterialTickEnvelopeV3,
    material_runtime::michigan_material_runtime_foundation_v2,
    michigan_economy::{digest_hex, michigan_observer_foundation_v1},
    michigan_material::MichiganDeliveryPresetV1,
    production_projection::project_material_observation_v1,
    runtime::prepare_committed_tick_v2,
    CampaignId,
};

/// Exercises the existing engine, canonical envelope, publication and projector.
/// The commit callback is an in-memory sink; this is not live-Postgres evidence.
fn published_observations() -> &'static [ObserverEconomySnapshotV1] {
    static OBSERVATIONS: OnceLock<Vec<ObserverEconomySnapshotV1>> = OnceLock::new();
    OBSERVATIONS.get_or_init(|| {
        let preset = MichiganDeliveryPresetV1::Standard;
        let foundation = michigan_material_runtime_foundation_v2(preset).unwrap();
        let (graph, _) = michigan_observer_foundation_v1().unwrap();
        let mut session = MaterialReplaySessionV3::new(
            graph,
            foundation.initial_register().clone(),
            foundation.digest(),
            preset.horizon_ticks(),
        )
        .unwrap();
        let campaign = CampaignId::from_uuid(uuid::Uuid::from_u128(293));
        let mut observation = ObserverEconomySnapshotV1 {
            campaign_id: campaign.as_uuid().to_string(),
            resolve_tick: 0,
            foundation_digest: digest_hex(&foundation.digest()),
            nominal_world_hash: None,
            tick_content_hash: None,
            envelope_digest: None,
            visibility: ObserverVisibilityV1::FullObserver,
            counties: vec![],
            production: Some(
                project_material_observation_v1(preset, session.material(), &[]).unwrap(),
            ),
        };
        let mut result = vec![observation.clone()];
        let mut history = Vec::new();
        let mut sink = CollectingSink::default();
        for tick in 1..=3 {
            let actions = OrderedPracticeActionBatchV1::empty(
                session.graph_session().session_identity().clone(),
                tick,
            )
            .unwrap();
            let prepared = session.prepare_advance(&actions).unwrap();
            let identity = *prepared.identity();
            let receipt = decode_material_receipts_v3(prepared.material().receipt_bytes()).unwrap();
            let families = prepare_committed_tick_v2(prepared.graph_report())
                .unwrap()
                .into_material_families(identity.tick_content_hash())
                .unwrap();
            let envelope = CommittedMaterialTickEnvelopeV3::compose(
                campaign,
                &identity,
                families,
                prepared.material().register().canonical_bytes(),
                prepared.material().receipt_bytes(),
            )
            .unwrap();
            let (ack, _) = session
                .commit_prepared_and_publish(&mut sink, prepared, |_| {
                    Ok::<_, ()>(ReplayCommitDispositionV1::Committed)
                })
                .unwrap();
            history.push((receipt, ack.receipt_digest()));
            observation.resolve_tick = ack.resolve_tick();
            observation.tick_content_hash = Some(digest_hex(ack.tick_content_hash().as_bytes()));
            observation.envelope_digest = Some(digest_hex(&envelope.digest()));
            observation.nominal_world_hash = Some(digest_hex(&ack.result_world_hash()));
            observation.production = Some(
                project_material_observation_v1(preset, session.material(), &history).unwrap(),
            );
            result.push(observation.clone());
        }
        result
    })
}

fn committed() -> ObserverEconomySnapshotV1 {
    published_observations()[1].clone()
}

fn reverse_unordered(snapshot: &mut ProductionSnapshotV1) {
    snapshot.sites.reverse();
    snapshot.routes.reverse();
    snapshot.freight.reverse();
    snapshot.provenance.reverse();
    for site in &mut snapshot.sites {
        site.inventory.reverse();
        site.inputs.reverse();
        site.labor.reverse();
        for input in &mut site.inputs {
            input.supplier_site_ids.reverse();
        }
    }
    for event in &mut snapshot.events {
        event.subject_site_ids.reverse();
    }
}

#[test]
fn published_replay_and_insertion_order_twins_have_the_same_evidence() {
    for original in published_observations() {
        let before = original.clone();
        let mut twin = original.clone();
        reverse_unordered(twin.production.as_mut().unwrap());
        assert_eq!(
            original.production_evidence_digest(),
            twin.production_evidence_digest()
        );
        let decoded: ObserverEconomySnapshotV1 =
            serde_json::from_slice(&serde_json::to_vec(original).unwrap()).unwrap();
        assert_eq!(
            original.production_evidence_digest(),
            decoded.production_evidence_digest()
        );
        assert_eq!(
            original, &before,
            "canonicalization cannot mutate the observation"
        );
    }
    let digests: std::collections::HashSet<_> = published_observations()
        .iter()
        .map(ObserverEconomySnapshotV1::production_evidence_digest)
        .collect();
    assert_eq!(
        digests.len(),
        4,
        "each published scope has a distinct identity"
    );
}

#[test]
fn nested_rows_exact_units_and_duplicate_multiplicity_are_preserved() {
    let mut original = committed();
    let site = &mut original.production.as_mut().unwrap().sites[0];
    let mut stock = site.inventory[0].clone();
    stock.unit_id.push_str("-different-unit");
    stock.quantity = u64::MAX;
    site.inventory.push(stock);
    let mut input = site.inputs[0].clone();
    input.good_id.push_str("-different-good");
    input.supplier_site_ids = vec!["supplier-z".to_owned(), "supplier-a".to_owned()];
    site.inputs.push(input);
    let mut labor = site.labor[0].clone();
    labor.unit.push_str("-different-unit");
    site.labor.push(labor);
    let mut twin = original.clone();
    reverse_unordered(twin.production.as_mut().unwrap());
    assert_eq!(
        original.production_evidence_digest(),
        twin.production_evidence_digest()
    );

    let site = &mut twin.production.as_mut().unwrap().sites[0];
    site.inventory.push(site.inventory[0].clone());
    assert_ne!(
        original.production_evidence_digest(),
        twin.production_evidence_digest(),
        "sorting must not discard duplicate rows"
    );
}

#[test]
fn scope_and_committed_identity_changes_are_bound() {
    let original = committed();
    let mut changed = serde_json::to_value(&original).unwrap();
    for field in [
        "campaign_id",
        "foundation_digest",
        "tick_content_hash",
        "envelope_digest",
        "nominal_world_hash",
    ] {
        changed[field] = Value::String("different-identity".to_owned());
        let twin: ObserverEconomySnapshotV1 = serde_json::from_value(changed.clone()).unwrap();
        assert_ne!(
            original.production_evidence_digest(),
            twin.production_evidence_digest(),
            "{field}"
        );
        changed = serde_json::to_value(&original).unwrap();
    }
    let mut twin = original.clone();
    twin.resolve_tick += 1;
    assert_ne!(
        original.production_evidence_digest(),
        twin.production_evidence_digest()
    );
    twin = original.clone();
    twin.visibility = ObserverVisibilityV1::KnownPreview;
    assert_ne!(
        original.production_evidence_digest(),
        twin.production_evidence_digest()
    );
}

#[test]
fn meaningful_event_order_remains_bound() {
    let original = committed();
    let mut twin = original.clone();
    let production = twin.production.as_mut().unwrap();
    assert!(production.events.len() > 1);
    production.events.reverse();
    assert_ne!(
        original.production_evidence_digest(),
        twin.production_evidence_digest()
    );
}

#[test]
fn missing_production_and_foundation_absence_do_not_masquerade_as_zero() {
    let mut known = committed();
    known.visibility = ObserverVisibilityV1::KnownPreview;
    known.production = None;
    known.nominal_world_hash = None;
    assert_eq!(known.production_evidence_digest(), None);

    let foundation = &published_observations()[0];
    let mut invented_zero = foundation.clone();
    invented_zero.production.as_mut().unwrap().sites[0].produced_batches = Some(0);
    assert_ne!(
        foundation.production_evidence_digest(),
        invented_zero.production_evidence_digest()
    );
    let mut invented_identity = foundation.clone();
    invented_identity.tick_content_hash = Some(String::new());
    assert_ne!(
        foundation.production_evidence_digest(),
        invented_identity.production_evidence_digest()
    );
}

/// Independent traversal through the public serde schema catches a newly added
/// scalar field that the fixed evidence encoder accidentally omits.
fn scalar_paths(value: &Value, prefix: &str, result: &mut Vec<String>) {
    match value {
        Value::Object(fields) => {
            for (key, value) in fields {
                scalar_paths(value, &format!("{prefix}/{key}"), result);
            }
        }
        Value::Array(rows) => {
            for (index, value) in rows.iter().enumerate() {
                scalar_paths(value, &format!("{prefix}/{index}"), result);
            }
        }
        _ => result.push(prefix.to_owned()),
    }
}

#[test]
fn every_disclosed_production_scalar_including_catalog_provenance_is_bound() {
    let original = committed();
    let value = serde_json::to_value(original.production.as_ref().unwrap()).unwrap();
    let mut paths = Vec::new();
    scalar_paths(&value, "", &mut paths);
    assert!(paths.iter().any(|path| path.starts_with("/freight/")));
    assert!(paths.iter().any(|path| path.starts_with("/provenance/")));
    for path in paths {
        let mut changed = value.clone();
        let field = changed.pointer_mut(&path).unwrap();
        *field = match &*field {
            Value::String(text) => Value::String(format!("{text}\0altered")),
            Value::Number(number) => Value::from(number.as_u64().unwrap() + 1),
            Value::Null => Value::from(0),
            other => panic!("unexpected scalar {other:?}"),
        };
        let mut twin = original.clone();
        twin.production = Some(serde_json::from_value(changed).unwrap());
        assert_ne!(
            original.production_evidence_digest(),
            twin.production_evidence_digest(),
            "{path}"
        );
    }
}

#[test]
fn presentation_identity_does_not_alias_world_or_envelope_identity() {
    let snapshot = committed();
    let digest = snapshot.production_evidence_digest().unwrap();
    assert_eq!(digest.as_bytes().len(), 32);
    let hex = digest.to_hex();
    assert_eq!(hex.len(), 64);
    assert!(hex
        .bytes()
        .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte)));
    assert_ne!(Some(&hex), snapshot.nominal_world_hash.as_ref());
    assert_ne!(Some(&hex), snapshot.envelope_digest.as_ref());
    assert_ne!(Some(&hex), snapshot.tick_content_hash.as_ref());
}

#[test]
fn digest_is_identical_in_two_fresh_processes() {
    const ENV: &str = "BABYLON_PRODUCTION_EVIDENCE_PROCESS";
    const MARKER: &str = "production-observation-evidence:";
    if let Some(order) = std::env::var_os(ENV) {
        let mut observation = committed();
        if order == "reverse" {
            reverse_unordered(observation.production.as_mut().unwrap());
        }
        println!(
            "{MARKER}{}",
            observation.production_evidence_digest().unwrap().to_hex()
        );
        return;
    }
    let executable = std::env::current_exe().unwrap();
    let run_child = |order| {
        let output = Command::new(&executable)
            .args([
                "--exact",
                "production_evidence::tests::digest_is_identical_in_two_fresh_processes",
                "--nocapture",
            ])
            .env(ENV, order)
            .output()
            .unwrap();
        assert!(output.status.success(), "{output:?}");
        String::from_utf8(output.stdout)
            .unwrap()
            .lines()
            .find_map(|line| line.strip_prefix(MARKER).map(str::to_owned))
            .unwrap()
    };
    let forward = run_child("forward");
    assert_eq!(forward, run_child("reverse"));
    assert_eq!(
        forward,
        committed().production_evidence_digest().unwrap().to_hex()
    );
}
