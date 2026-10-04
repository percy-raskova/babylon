//! Actual national source, optional organizer authority and cold foundation admission.
use babylon_kernel::{
    content_digest::sha256_of,
    replay::{ReplaySeed, ReplaySessionId},
};
use babylon_persistence::{
    economic_catalog::{CapturedEconomicCatalog, SourceArtifactKind as Kind},
    economic_content::EconomicContentAdmission,
    identity::CampaignId,
    material_runtime::MaterialRuntimeFoundation,
};
use babylon_practice_contract::{
    admit_organizer, organizer_action_batch, organizer_aid_commitment, OrganizerChoice,
    OrganizerCommand, OrganizerError, OrganizerRefusal, OrganizerTimeBindingMode, PracticeId,
};
#[path = "fixtures/national_capture.rs"]
mod national_capture;

#[test]
fn actual_national_playable_source_and_cold_foundation_preserve_one_opening() {
    let campaign = CampaignId::from_uuid(uuid::Uuid::from_u128(0x0026_1631_7031));
    let raw = CapturedEconomicCatalog::capture(national_capture::input(), None).unwrap();
    assert_eq!(raw.compiler_version(), "national-world-v4");
    assert_eq!(
        &raw.canonical_bytes()[raw.canonical_bytes().len() - 5..],
        &[0; 5]
    );
    let material_rules = include_bytes!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../content/scenarios/national/material-cycle.bsl"
    ));
    let organizer_rules = include_bytes!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../content/scenarios/national/organizer-cycle.bsl"
    ));
    assert_eq!(raw.source(Kind::Rules).unwrap(), material_rules);
    let playable =
        CapturedEconomicCatalog::capture_national_campaign(national_capture::input(), campaign)
            .unwrap();
    // One complete comparison, without cloning a second expected national opening.
    // This includes every stock, cash, workforce and modeled household-time policy.
    assert_eq!(raw.opening(), playable.opening());
    let policy = include_bytes!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../content/scenarios/national/defines.toml"
    ));
    assert_eq!(raw.source(Kind::NationalGamePolicy).unwrap(), policy);
    assert_eq!(playable.source(Kind::NationalGamePolicy).unwrap(), policy);
    assert_eq!(raw.national_aid_capture(), playable.national_aid_capture());
    assert_ne!(raw.digest(), playable.digest());
    let raw_frame_size = raw.canonical_bytes().len();
    drop(raw);
    let mut rules = material_rules.to_vec();
    rules.push(b'\n');
    rules.extend_from_slice(organizer_rules);
    assert_eq!(playable.source(Kind::Rules).unwrap(), rules);
    let catalog_digest = playable.digest();
    assert_eq!(catalog_digest, sha256_of(playable.canonical_bytes()));
    let session_id = ReplaySessionId::try_from("national-organizer-cold-control").unwrap();
    let foundation = playable
        .create_foundation(session_id.clone(), ReplaySeed::new(319))
        .unwrap();
    let expected_config =
        assert_admitted_inputs(foundation.initial_register(), campaign, session_id, policy);
    let register_digest = foundation.initial_register().digest();
    let foundation_digest = foundation.digest();
    let cold =
        MaterialRuntimeFoundation::decode(foundation.canonical_bytes(), foundation_digest).unwrap();
    assert_eq!(cold.canonical_bytes(), foundation.canonical_bytes());
    assert_eq!(cold.initial_register().digest(), register_digest);
    assert_eq!(
        cold.initial_register().organizer_config(),
        Some(&expected_config)
    );
    assert_eq!(cold.spec().content_digest, catalog_digest);
    assert_eq!(
        cold.graph_foundation().content_bundle().rule_source_bytes(),
        rules
    );
    let cold_catalog = cold
        .graph_foundation()
        .content_bundle()
        .economic_catalog()
        .unwrap();
    assert_eq!(cold_catalog.digest(), catalog_digest);
    assert_eq!(
        cold_catalog.source(Kind::NationalGamePolicy).unwrap(),
        policy
    );
    let targets = assert_source_bindings(
        cold_catalog,
        &expected_config,
        raw_frame_size,
        organizer_rules.len(),
    );
    // Actual native session admission validates the captured organizer rules.
    let session = foundation.into_session().unwrap();
    assert_eq!(session.completed_tick(), 0);
    assert_eq!(
        session.material().organizer_config(),
        Some(&expected_config)
    );
    drop(session);
    let admitted = EconomicContentAdmission::from_foundation(cold).unwrap();
    admitted
        .validate_header(admitted.duration(), &catalog_digest, &foundation_digest, 0)
        .unwrap();
    assert_native_bindings(&admitted, &expected_config, &targets);
}

fn assert_admitted_inputs(
    initial: &babylon_tick::material_world::MaterialWorldRegister,
    campaign: CampaignId,
    session_id: ReplaySessionId,
    policy: &[u8],
) -> babylon_practice_contract::OrganizerConfig {
    assert_eq!(initial.completed_tick(), 0);
    let config = initial.organizer_config().unwrap();
    let state = initial.organizer_state().unwrap();
    assert_eq!(config.campaign_id, *campaign.canonical_bytes());
    assert!(
        matches!(&config.time_binding, OrganizerTimeBindingMode::Household{bindings} if bindings.len()==3)
    );
    assert_eq!(config.aid_bindings.len(), 2);
    assert!(
        state.receipts.is_empty() && state.aid_receipts.is_empty() && state.pending_aid.is_empty()
    );
    assert!(state.contact_products.is_empty() && state.observations.is_empty());
    let command = |choice, nonce| OrganizerCommand {
        campaign_id: config.campaign_id,
        actor_id: config.controlled_actor_id,
        authority_id: config.input_authority_id,
        expected_period: 0,
        content_digest: config.content_digest,
        resource_digest: babylon_practice_contract::organizer_resource_digest().unwrap(),
        nonce: [nonce; 16],
        choice,
    };
    let ordinary = admit_organizer(config, state, &command(OrganizerChoice::Hold, 1)).unwrap();
    let ordinary_batch =
        organizer_action_batch(config, state, Some(&ordinary), session_id.clone()).unwrap();
    assert!(!ordinary_batch.items().is_empty());
    let gift = admit_organizer(config, state, &command(OrganizerChoice::RemoteAid, 2)).unwrap();
    let gift_capture = organizer_aid_commitment(config, state, &gift).unwrap();
    let aid_batch = organizer_action_batch(config, state, Some(&gift), session_id).unwrap();
    assert!(aid_batch
        .items()
        .iter()
        .all(|row| row.intent().practice_id == PracticeId::MutualAid));
    assert_eq!(gift.resolves_period, 1);
    assert_eq!(gift_capture.source_hash, sha256_of(policy));
    // Admission authorizes an input only: no gift, practice or contact is credited.
    assert!(state.aid_receipts.is_empty() && state.pending_aid.is_empty());
    let mut stale_command = command(OrganizerChoice::RemoteAid, 3);
    stale_command.expected_period = 1;
    assert_eq!(
        admit_organizer(config, state, &stale_command),
        Err(OrganizerError::Refused(OrganizerRefusal::StalePeriod))
    );
    let mut forged = command(OrganizerChoice::RemoteAid, 4);
    forged.content_digest[0] ^= 1;
    assert_eq!(
        admit_organizer(config, state, &forged),
        Err(OrganizerError::Refused(OrganizerRefusal::ContentChanged))
    );
    config.clone()
}

fn assert_native_bindings(
    admitted: &EconomicContentAdmission,
    expected_config: &babylon_practice_contract::OrganizerConfig,
    targets: &[String],
) {
    let nodes = admitted.foundation_graph().rows().nodes();
    for name in [
        "wayne-organizing-collective",
        "wayne-workplace-committee",
        "wayne-neighborhood-contact-group",
        "wayne-local-aid-partners",
        "cook-independent-solidarity-partners",
    ] {
        assert!(
            nodes
                .iter()
                .any(|(id, kind)| id == name && kind == "ORGANIZATION"),
            "missing native organization {name}"
        );
    }
    assert_eq!(
        nodes
            .iter()
            .filter(|(_, kind)| kind == "PARTICIPANT_BODY")
            .count(),
        3
    );
    for target in targets {
        assert!(nodes
            .iter()
            .any(|(id, kind)| id == target && kind == "SOCIAL_CLASS"));
    }
    let bodies = admitted.foundation_graph().rows().hyperedges();
    for actor in [
        expected_config.controlled_actor_id,
        expected_config.workplace_partner.actor_id,
        expected_config.neighborhood_partner.actor_id,
        expected_config.aid_bindings[0].partner.actor_id,
        expected_config.aid_bindings[1].partner.actor_id,
    ] {
        let name = format!("organizer-participant-body-{actor}");
        let row = bodies.iter().find(|(id, _, _)| id == &name).unwrap();
        assert_eq!(row.1, "ORGANIZATION_BODY");
        assert_eq!(row.2.len(), 2);
    }
}

fn assert_source_bindings(
    catalog: &CapturedEconomicCatalog,
    config: &babylon_practice_contract::OrganizerConfig,
    raw_frame_size: usize,
    organizer_rule_size: usize,
) -> Vec<String> {
    let config_bytes = babylon_practice_contract::encode_organizer_config(config).unwrap();
    assert_eq!(
        catalog.canonical_bytes().len(),
        raw_frame_size + 1 + organizer_rule_size + config_bytes.len()
    );
    let marker = catalog.canonical_bytes().len() - config_bytes.len() - 5;
    assert_eq!(catalog.canonical_bytes()[marker], 1);
    assert_eq!(&catalog.canonical_bytes()[marker + 5..], config_bytes);
    let mut basis = catalog.canonical_bytes()[..marker].to_vec();
    basis.extend_from_slice(&[0; 5]);
    assert_eq!(config.content_digest, sha256_of(&basis));
    let aid = catalog.national_aid_capture().unwrap();
    config
        .aid_bindings
        .iter()
        .zip(&aid.children[1..])
        .map(|(binding, child)| {
            assert_eq!(binding.recipient_principal_id, child.principal.as_bytes());
            assert_eq!(
                binding.social_class_target,
                sha256_of(&child.class_subject.canonical_bytes().unwrap())
            );
            let babylon_graph::stable_element::StableElementKey::Node { local_name, .. } =
                &child.class_subject
            else {
                panic!("captured aid class must be a native node");
            };
            local_name.clone()
        })
        .collect()
}
