//! Serialization controls use actual adjudicated identities, without claiming
//! national coverage or Archive admission from this small accounting fixture.
use super::audit::{BoundaryFacts, ReceiptFacts, RenewalFacts};
use super::{audit, economic, production_renewal, reader, trade};
use crate::michigan_content::MichiganContentPreset;
use crate::michigan_material::MichiganMaterialCatalog;
use crate::production_observation::ProductionSite;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::material_world;
use babylon_tick::replay_session::ReplayCommitDisposition;
use sha2::Digest;
use sha2::Sha256;
use uuid::Uuid;

fn sites(catalog: &MichiganMaterialCatalog) -> Vec<ProductionSite> {
    catalog
        .sites()
        .iter()
        .map(|site| ProductionSite {
            id: audit::hex(&site.id().as_bytes()),
            location: format!("county:{}", site.county_geoid)
                .parse()
                .expect("the authored literal parses as the declared type"),
            name: site.label.clone(),
            industry_code: Some(site.naics.clone()),
            observed_employment: None,
            roles: vec![],
            sector_code: Some(site.sector_code.clone()),
            function: "manufacturing".into(),
            processes: vec![],
            inventory: vec![],
        })
        .collect()
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "`serialized_boundary_binds_every_fold_to_seed_and_current_receipt` keeps one authored boundary's fixture and assertions together"
)]
fn serialized_boundary_binds_every_fold_to_seed_and_current_receipt() {
    let catalog = crate::test_support::catalog();
    let sites = sites(&catalog);
    let mut session = MichiganContentPreset::FourWeekStandard
        .create_foundation(&catalog)
        .expect("the authored catalog builds the foundation")
        .into_session()
        .expect("the fixture opens a session");
    let mut economic = economic::Audit::default();
    let mut trade = trade::Audit::default();
    let mut renewal = None;
    let mut previous = None;
    for tick in 1..=2 {
        let actions = OrderedPracticeActionBatch::empty(
            session.graph_session().session_identity().clone(),
            tick,
        )
        .expect("the empty authored batch constructs");
        let prepared = session
            .prepare_advance(&actions)
            .expect("the session prepares the authored advance");
        let identity = prepared.identity();
        let receipts =
            material_world::decode_material_receipts(prepared.material().receipt_bytes())
                .expect("the canonical bytes decode into the declared type");
        let register = prepared.material().register();
        assert_eq!(
            identity.receipt_digest().as_slice(),
            Sha256::digest(prepared.material().receipt_bytes()).as_slice()
        );
        let renewal_evidence = if tick == 1 {
            let audit = production_renewal::Audit::seed(register.state(), tick, register.digest())
                .expect("the fixture seeds the authored rows");
            let evidence = audit
                .evidence()
                .expect("the fixture call `evidence` succeeds for the authored inputs");
            renewal = Some(audit);
            evidence
        } else {
            renewal
                .as_mut()
                .expect("the fixture set the optional field before this borrow")
                .read(&receipts)
                .expect("the fixture reader returns its authored facts")
        };
        let facts = BoundaryFacts {
            version: 1,
            campaign: Uuid::from_u128(342).to_string(),
            foundation_sha256: audit::hex(&identity.foundation_digest()),
            policy_sha256: audit::hex(&[1; 32]),
            tick,
            tick_content_hash: audit::hex(identity.tick_content_hash().as_bytes()),
            envelope_digest: audit::hex(&[2; 32]),
            canonical_receipt_sha256: audit::hex(&identity.receipt_digest()),
            nominal_world_hash: audit::hex(&identity.result_world_hash()),
            material_register_sha256: audit::hex(&register.digest()),
            material_register_bytes: register.canonical_bytes().len(),
            production_evidence_sha256: audit::hex(&[3; 32]),
            production_evidence_body_bytes: 1,
            county_roster_sha256: audit::hex(&[4; 32]),
            economic: ReceiptFacts::new(
                economic
                    .read(&receipts)
                    .expect("the fixture reader returns its authored facts"),
                identity,
            ),
            trade: ReceiptFacts::new(
                trade
                    .read(&receipts, &sites)
                    .expect("the fixture reader returns its authored facts"),
                identity,
            ),
            production_renewal: Some(RenewalFacts::new(renewal_evidence, identity)),
        };
        let read = reader::BoundaryRead {
            version: 1,
            scope: "authenticated_material_and_archive_facts_only",
            archive: reader::ArchiveFacts {
                expected_tick: tick,
                durable_tick: tick,
                processed_tick: tick,
                pending_count: 0,
                pending_scope: "requested_prefix",
                observation_mode: "live_latest",
                captured_tail_tick: tick,
                captured_tail_tick_content_hash: facts.tick_content_hash.clone(),
                dossier_sha256: audit::hex(&[5; 32]),
            },
            facts,
            production_read_elapsed_ns: 0,
            audit_elapsed_ns: 0,
        };
        let encoded = serde_json::to_value(read).expect("the value serializes to JSON");
        let facts = &encoded["facts"];
        for fold in ["economic", "trade", "production_renewal"] {
            let key = if fold == "production_renewal" {
                "through_tick_content_hash"
            } else {
                "tick_content_hash"
            };
            assert_eq!(facts[fold][key], facts["tick_content_hash"], "{fold}");
            assert_eq!(
                facts[fold]["canonical_receipt_sha256"], facts["canonical_receipt_sha256"],
                "{fold}"
            );
        }
        assert_eq!(facts["production_renewal"]["through_period"], tick);
        if let Some(prior) = previous.replace(facts["tick_content_hash"].clone()) {
            assert_ne!(facts["tick_content_hash"], prior);
        }
        session
            .commit_prepared_and_publish(&mut CollectingSink::default(), prepared, |_| {
                Ok::<_, ()>(ReplayCommitDisposition::Committed)
            })
            .expect("the prepared period commits");
    }
}
