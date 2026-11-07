//! Actual national source, optional organizer authority and cold foundation admission.

use babylon_kernel::content_digest::sha256_of;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::AccountId;
use babylon_material_circuit::OrganizationAccountId;
use babylon_material_circuit::PublicAccountId;
use babylon_practice_contract::OrganizerAllocation;

use babylon_persistence::economic_catalog::{
    CapturedEconomicCatalog, NationalOpponent, SourceArtifactKind as Kind,
};
use babylon_persistence::economic_content::EconomicContentAdmission;
use babylon_persistence::identity::CampaignId;
use babylon_persistence::material_runtime::MaterialRuntimeFoundation;

use babylon_practice_contract::OrganizerConfig;
use babylon_practice_contract::{
    OrganizerChoice, OrganizerCommand, OrganizerError, OrganizerRefusal, OrganizerTimeBindingMode,
    PracticeId,
};
use babylon_tick::material_world::MaterialWorldRegister;
use uuid::Uuid;
#[path = "fixtures/national_capture.rs"]
mod national_capture;

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "`actual_national_playable_source_and_cold_foundation_preserve_one_opening` keeps one authored boundary's fixture and assertions together"
)]
fn actual_national_playable_source_and_cold_foundation_preserve_one_opening() {
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7031));
    let raw = CapturedEconomicCatalog::capture(national_capture::input(), None)
        .expect("the fixture captures the authored state");
    assert_eq!(raw.compiler_version(), "national-world-v6");
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
    let city_pd_rules = include_bytes!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../content/scenarios/national/state-opponent-cycle.bsl"
    ));
    assert_eq!(
        raw.source(Kind::Rules)
            .expect("the fixture call `source` succeeds for the authored inputs"),
        material_rules
    );
    let playable =
        CapturedEconomicCatalog::capture_national_campaign(national_capture::input(), campaign)
            .expect("the fixture captures the authored state");
    assert_agency_opening(&raw, &playable);
    let playable_rules = playable.source(Kind::Rules).expect("captured rules");
    assert!(
        playable_rules
            .windows(b"state-opponent/observe-public-activity".len())
            .any(|rule| rule == b"state-opponent/observe-public-activity"),
        "the normal national campaign must capture its scheduled City PD rule"
    );
    let policy = include_bytes!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../content/scenarios/national/defines.toml"
    ));
    assert_eq!(
        raw.source(Kind::NationalGamePolicy)
            .expect("the fixture call `source` succeeds for the authored inputs"),
        policy
    );
    assert_eq!(
        playable
            .source(Kind::NationalGamePolicy)
            .expect("the fixture call `source` succeeds for the authored inputs"),
        policy
    );
    assert_eq!(raw.national_aid_capture(), playable.national_aid_capture());
    assert_ne!(raw.digest(), playable.digest());
    let raw_frame_size = raw.canonical_bytes().len();
    drop(raw);
    assert_no_opponent_route(&playable, campaign);
    let mut rules = material_rules.to_vec();
    rules.push(b'\n');
    rules.extend_from_slice(organizer_rules);
    rules.push(b'\n');
    rules.extend_from_slice(city_pd_rules);
    assert_eq!(
        playable
            .source(Kind::Rules)
            .expect("the fixture call `source` succeeds for the authored inputs"),
        rules
    );
    let catalog_digest = playable.digest();
    assert_eq!(catalog_digest, sha256_of(playable.canonical_bytes()));
    let session_id = ReplaySessionId::try_from("national-organizer-cold-control")
        .expect("the fixture value fits the target range");
    let foundation = playable
        .create_foundation(session_id.clone(), ReplaySeed::new(319))
        .expect("the authored catalog builds the foundation");
    let expected_config =
        assert_admitted_inputs(foundation.initial_register(), campaign, session_id, policy);
    let register_digest = foundation.initial_register().digest();
    let foundation_digest = foundation.digest();
    let cold = MaterialRuntimeFoundation::decode(
        &foundation
            .export_canonical_bytes()
            .expect("the content exports its canonical bytes"),
        foundation_digest,
    )
    .expect("the committed canonical bytes decode");
    assert_eq!(
        cold.export_canonical_bytes()
            .expect("the content exports its canonical bytes"),
        foundation
            .export_canonical_bytes()
            .expect("the content exports its canonical bytes")
    );
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
        .expect("the fixture call `economic_catalog` succeeds for the authored inputs");
    assert_eq!(cold_catalog.digest(), catalog_digest);
    assert_eq!(
        cold_catalog
            .source(Kind::NationalGamePolicy)
            .expect("the fixture call `source` succeeds for the authored inputs"),
        policy
    );
    let targets = assert_source_bindings(
        cold_catalog,
        &expected_config,
        raw_frame_size,
        organizer_rules.len() + 1 + city_pd_rules.len(),
    );
    // Actual native session admission validates the captured organizer rules.
    let session = foundation
        .into_session()
        .expect("the fixture opens a session");
    assert_eq!(session.completed_tick(), 0);
    assert_eq!(
        session.material().organizer_config(),
        Some(&expected_config)
    );
    drop(session);
    let admitted = EconomicContentAdmission::from_foundation(cold)
        .expect("the foundation admits the derived value");
    admitted
        .validate_header(admitted.duration(), &catalog_digest, &foundation_digest, 0)
        .expect("the authored fixture satisfies the rule");
    assert_native_bindings(&admitted, &expected_config, &targets);
}

fn assert_agency_opening(raw: &CapturedEconomicCatalog, playable: &CapturedEconomicCatalog) {
    // The agency's future appropriation must not finance its own opening or
    // change the pre-existing public cash reserve.
    let before = raw.opening();
    let after = playable.opening();
    let pd = playable.city_pd_config().expect("national agency captured");
    let agency = AccountId::Organization(OrganizationAccountId::from_bytes(pd.agency_account_id));
    assert_eq!(
        after.institutional_cash.len(),
        before.institutional_cash.len() + 1
    );
    assert_eq!(
        &after.institutional_cash[..before.institutional_cash.len()],
        &before.institutional_cash
    );
    let agency_cash = after.institutional_cash.last().expect("agency cash");
    assert_eq!(agency_cash.id, agency);
    assert_eq!(agency_cash.cash.micro_units(), 0);
    let public = PublicAccountId::from_bytes(pd.public_account_id);
    let old_budget = before
        .institutions
        .public_budgets
        .iter()
        .find(|row| row.public_account == public)
        .expect("Wayne public budget");
    let new_budget = after
        .institutions
        .public_budgets
        .iter()
        .find(|row| row.public_account == public)
        .expect("Wayne public budget");
    assert_eq!(
        new_budget.period_cap.micro_units(),
        old_budget.period_cap.micro_units() + 24_000_000
    );
    assert!(after
        .institutions
        .public_allocations
        .iter()
        .any(|row| row.public_account == public
            && row.recipient == agency
            && row.amount_per_period.micro_units() == 24_000_000
            && row.priority == 0
            && row.treatment
                == babylon_material_circuit::PublicTransferTreatment::AgencyAppropriation));
    assert_eq!(before.households, after.households);
    assert_eq!(before.employment, after.employment);
    assert_eq!(before.staffing, after.staffing);
    assert_eq!(before.sites, after.sites);
    assert_eq!(before.policies, after.policies);
}

fn assert_no_opponent_route(playable: &CapturedEconomicCatalog, campaign: CampaignId) {
    let control = CapturedEconomicCatalog::capture_national_campaign_with_opponent(
        national_capture::input(),
        campaign,
        NationalOpponent::None,
    )
    .expect("the no-PD control captures the same organizer route");
    assert!(control.city_pd_config().is_none());
    assert_eq!(control.organizer_config(), playable.organizer_config());
    assert!(!control
        .source(Kind::Rules)
        .expect("control rules")
        .windows(b"city-pd-observe".len())
        .any(|row| row == b"city-pd-observe"));
}

#[allow(
    clippy::too_many_lines,
    reason = "one captured national input control retains authority, allocation and action-identity assertions together"
)]
fn assert_admitted_inputs(
    initial: &MaterialWorldRegister,
    campaign: CampaignId,
    session_id: ReplaySessionId,
    policy: &[u8],
) -> OrganizerConfig {
    assert_eq!(initial.completed_tick(), 0);
    let config = initial
        .organizer_config()
        .expect("the fixture register carries organizer config");
    let state = initial
        .organizer_state()
        .expect("the fixture register carries organizer state");
    assert_eq!(config.campaign_id, *campaign.canonical_bytes());
    assert!(
        matches!(&config.time_binding, OrganizerTimeBindingMode::Household{bindings} if bindings.len()==3)
    );
    assert_eq!(config.aid_bindings.len(), 2);
    let collection = config
        .collection
        .as_ref()
        .expect("national contribution terms");
    assert_eq!(collection.initial_cash_micros, 280_000_000);
    assert_eq!(collection.maximum_cash_micros, 1_450_000_000);
    assert_eq!(collection.collection_hours, 2);
    let journal = initial
        .organizer_journal()
        .expect("the fixture register carries organizer journal");
    assert!(journal.periods.is_empty() && state.pending_aid.is_empty());
    assert!(state.contact_products.is_empty() && state.learned_authority_index.is_empty());
    let command = |choice, nonce| OrganizerCommand {
        allocation: if choice == OrganizerChoice::Collect {
            OrganizerAllocation::Collection {
                target_cash_micros: config
                    .collection
                    .as_ref()
                    .expect("captured collection")
                    .initial_cash_micros,
            }
        } else if matches!(
            choice,
            OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid
        ) {
            OrganizerAllocation::Aid {
                food_quantity: 1,
                cash_micros: 0,
            }
        } else {
            OrganizerAllocation::None
        },
        campaign_id: config.campaign_id,
        actor_id: config.controlled_actor_id,
        authority_id: config.input_authority_id,
        expected_period: 0,
        content_digest: config.content_digest,
        resource_digest: babylon_practice_contract::organizer_resource_digest()
            .expect("the organizer resource set has a digest"),
        nonce: [nonce; 16],
        choice,
    };
    let ordinary = babylon_practice_contract::admit_organizer(
        config,
        state,
        &command(OrganizerChoice::Hold, 1),
    )
    .expect("the fixture admits the organizer actor");
    let ordinary_batch = babylon_practice_contract::organizer_action_batch(
        config,
        state,
        Some(&ordinary),
        session_id.clone(),
    )
    .expect("the authored action batch builds");
    assert_ne!(ordinary_batch.items().len(), 0);
    let gift = babylon_practice_contract::admit_organizer(
        config,
        state,
        &command(OrganizerChoice::RemoteAid, 2),
    )
    .expect("the fixture admits the organizer actor");
    let gift_capture = babylon_practice_contract::organizer_aid_commitment(config, state, &gift)
        .expect("the authored aid commitment builds");
    let aid_batch =
        babylon_practice_contract::organizer_action_batch(config, state, Some(&gift), session_id)
            .expect("the authored action batch builds");
    assert!(aid_batch
        .items()
        .iter()
        .all(|row| row.intent().practice_id == PracticeId::MutualAid));
    assert_eq!(gift.resolves_period, 1);
    assert_eq!(gift_capture.source_hash, sha256_of(policy));
    // Admission authorizes an input only: no gift, practice or contact is credited.
    assert!(journal
        .periods
        .iter()
        .all(|entries| entries.aid_receipts.is_empty()));
    assert_eq!(state.pending_aid.len(), 0);
    let mut stale_command = command(OrganizerChoice::RemoteAid, 3);
    stale_command.expected_period = 1;
    assert_eq!(
        babylon_practice_contract::admit_organizer(config, state, &stale_command),
        Err(OrganizerError::Refused(OrganizerRefusal::StalePeriod))
    );
    let mut forged = command(OrganizerChoice::RemoteAid, 4);
    forged.content_digest[0] ^= 1;
    assert_eq!(
        babylon_practice_contract::admit_organizer(config, state, &forged),
        Err(OrganizerError::Refused(OrganizerRefusal::ContentChanged))
    );
    config.clone()
}

fn assert_native_bindings(
    admitted: &EconomicContentAdmission,
    expected_config: &OrganizerConfig,
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
        let row = bodies
            .iter()
            .find(|(id, _, _)| id == &name)
            .expect("the fixture holds the searched element");
        assert_eq!(row.1, "ORGANIZATION_BODY");
        assert_eq!(row.2.len(), 2);
    }
}

fn assert_source_bindings(
    catalog: &CapturedEconomicCatalog,
    config: &OrganizerConfig,
    raw_frame_size: usize,
    organizer_rule_size: usize,
) -> Vec<String> {
    let config_bytes = babylon_practice_contract::encode_organizer_config(config)
        .expect("the fixture value encodes to its canonical bytes");
    let pd_bytes = babylon_practice_contract::encode_city_pd_config(
        catalog.city_pd_config().expect("national agency captured"),
    )
    .expect("agency terms encode");
    assert_eq!(
        catalog.canonical_bytes().len(),
        raw_frame_size + 1 + organizer_rule_size + config_bytes.len() + pd_bytes.len()
    );
    let marker = catalog.canonical_bytes().len() - pd_bytes.len() - 5 - config_bytes.len() - 5;
    assert_eq!(catalog.canonical_bytes()[marker], 1);
    assert_eq!(
        &catalog.canonical_bytes()[marker + 5..marker + 5 + config_bytes.len()],
        config_bytes
    );
    assert_eq!(
        catalog.canonical_bytes()[marker + 5 + config_bytes.len()],
        1
    );
    assert_eq!(
        &catalog.canonical_bytes()[marker + 10 + config_bytes.len()..],
        pd_bytes
    );
    let aid = catalog
        .national_aid_capture()
        .expect("the fixture call `national_aid_capture` succeeds for the authored inputs");
    config
        .aid_bindings
        .iter()
        .zip(&aid.children[1..])
        .map(|(binding, child)| {
            assert_eq!(binding.recipient_principal_id, child.principal.as_bytes());
            assert_eq!(
                binding.social_class_target,
                sha256_of(
                    &child
                        .class_subject
                        .canonical_bytes()
                        .expect("the graph value exposes canonical bytes")
                )
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
