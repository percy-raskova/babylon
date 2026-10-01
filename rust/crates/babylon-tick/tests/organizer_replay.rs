//! A small Designed maintenance workplace crosses the real BSL/tick boundary.

#[allow(dead_code, reason = "reuse the checked Michigan foundation loader")]
#[path = "../../babylon-persistence/src/michigan_dynamic_hex_foundation.rs"]
mod michigan_dynamic_hex_foundation;

use babylon_bsl::canonical_ast::rules_hash_of;
use babylon_bsl::rule_pipeline::split_content;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::stable_element::StableElementKey;
use babylon_graph::state_hash::CanonicalState;
use babylon_kernel::content_digest::{sha256_of, ContentDigest};
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_kernel::tick_content_hash::RefDigest;
use babylon_material_circuit::*;
use babylon_practice_contract::*;
use babylon_tick::material_replay::{
    MaterialCommitError, MaterialReplayError, MaterialReplaySession, PreparedMaterialTick,
};
use babylon_tick::material_staffing::{StaffingComposition, StaffingNodeBinding};
use babylon_tick::material_state::MaterialState;
use babylon_tick::material_world::{decode_material_receipts, MaterialWorldRegister};
use babylon_tick::replay_session::{ReplayCommitDisposition, ReplayTickSession};

type Session = MaterialReplaySession<HypergraphStore>;
type Candidate = PreparedMaterialTick<HypergraphStore>;

const SCENARIO: &str = r"
(scenario organizer/replay
  (deffield social-class/employed-population int extensive)
  (deffield social-class/reserve-population int extensive)
  (deffield social-class/previous-unretained-labor-hours int extensive)
  (node consumers NodeType/SOCIAL_CLASS
    (social-class/employed-population 8)
    (social-class/reserve-population 0)
    (social-class/previous-unretained-labor-hours 1280))
  (node maintainers NodeType/SOCIAL_CLASS
    (social-class/employed-population 0)
    (social-class/reserve-population 1)
    (social-class/previous-unretained-labor-hours 0)))
";

const MATERIAL: &str = r#"
(rule material/period
  :role mechanic :evidence designed
  :material-basis "Close the checked fixture material circuit and workforce"
  :fuel 1000000
  (anchor :after metabolism)
  (material-cycle))
"#;

const PRODUCTS: &str = r#"
(rule organizer/organizer-products
  :role mechanic :evidence designed
  :material-basis "Consume committed contact products and produce scoped material reports"
  :fuel 1000000
  (anchor :before ooda)
  (organizer-products))
"#;

const PRACTICE: &str = r#"
(rule organizer/organizer-practice
  :role intent :evidence designed
  :material-basis "Execute the accepted ruling or authorized routine through committed time"
  :fuel 1000000
  (anchor :after ooda)
  (organizer-practice))
"#;

fn site(id: u8) -> SiteId {
    SiteId::from_bytes([id; 32])
}
fn good(id: u8) -> GoodId {
    GoodId::from_bytes([id; 32])
}
fn unit(id: u8) -> UnitId {
    UnitId::from_bytes([id; 32])
}
fn process() -> ProcessId {
    ProcessId::from_bytes([1; 32])
}

fn opening() -> MaterialCircuitState {
    MaterialCircuitState {
        period: 1,
        site_logistics_nodes: (1..=2)
            .map(|id| SiteLogisticsNode {
                site_id: site(id),
                node_id: LogisticsNodeId::from_bytes([id; 32]),
            })
            .collect(),
        process_outputs: vec![ProcessOutput {
            process_id: process(),
            site_id: site(1),
            good_id: good(2),
            unit_id: unit(1),
            quantity_per_batch: 60,
        }],
        input_coefficients: vec![InputOutputCoefficient {
            process_id: process(),
            good_id: good(1),
            unit_id: unit(1),
            quantity_per_batch: 80,
        }],
        labor_coefficients: vec![LaborCoefficient {
            process_id: process(),
            unit_id: unit(2),
            quantity_per_batch: 60,
        }],
        freight_mass_coefficients: vec![FreightMassCoefficient {
            good_id: good(2),
            unit_id: unit(1),
            grams_per_unit: 1000,
        }],
        supplier_routes: vec![],
        route_stages: vec![],
        route_stage_capacities: vec![],
        inventory: vec![
            InventoryRow {
                site_id: site(1),
                good_id: good(1),
                unit_id: unit(1),
                quantity: 2560,
            },
            InventoryRow {
                site_id: site(2),
                good_id: good(2),
                unit_id: unit(1),
                quantity: 256,
            },
        ],
        orders: vec![],
        backlog: vec![],
        freight: vec![],
        corridor_capacities: vec![],
        capacities: (1..=8)
            .map(|period| CapacityRow {
                process_id: process(),
                site_id: site(1),
                period,
                available_batches: 16,
            })
            .collect(),
        labor: vec![
            LaborCapacityRow {
                site_id: site(1),
                unit_id: unit(2),
                period: 1,
                available: 1280,
            },
            LaborCapacityRow {
                site_id: site(2),
                unit_id: unit(2),
                period: 1,
                available: 0,
            },
        ],
        production_commitments: vec![ProductionCommitment {
            process_id: process(),
            site_id: site(1),
            period: 1,
            planned_batches: 16,
        }],
        merchants: vec![],
        handling_coefficients: vec![],
        final_demand_principals: vec![],
        final_demand_orders: vec![],
        accounting: babylon_material_circuit::CircuitAccounting::PhysicalControl,
        maintenance_binding: Some(MaintenanceBinding {
            provider_site_id: site(2),
            consumer_process_id: process(),
            spare_good_id: good(2),
            spare_unit_id: unit(1),
            labor_unit_id: unit(2),
            spare_units_per_job: 1,
            labor_units_per_job: 10,
            enabled_batches_per_job: 1,
            maximum_jobs_per_period: 16,
        }),
        maintenance_service: Some(MaintenanceService {
            period: 1,
            available_batches: 16,
        }),
    }
}

fn config() -> OrganizerConfig {
    OrganizerConfig {
        schema_version: ORGANIZER_SCHEMA_VERSION,
        campaign_id: [1; 16],
        controlled_actor_id: 101,
        input_authority_id: [2; 16],
        organization_label: "Fixture organizing collective".into(),
        workplace_id: 104,
        workplace_process_id: process().as_bytes(),
        workplace_label: "Fixture metal-parts workplace".into(),
        workplace_partner: OrganizerPartner {
            actor_id: 102,
            authority_id: [3; 16],
            label: "Fixture workplace committee".into(),
            policy: OrganizerPartnerPolicy::Participate,
            permits_work_report: true,
            permits_maintenance_report: true,
        },
        neighborhood_partner: OrganizerPartner {
            actor_id: 103,
            authority_id: [4; 16],
            label: "Fixture neighborhood group".into(),
            policy: OrganizerPartnerPolicy::Participate,
            permits_work_report: false,
            permits_maintenance_report: false,
        },
        participants: [(201, 101, 16), (202, 102, 8), (203, 103, 8)]
            .into_iter()
            .map(|(contributor_id, actor_id, hours)| OrganizerParticipant {
                contributor_id,
                label: format!("Fixture participant {contributor_id}"),
                available_hours: hours,
                commitments: vec![OrganizerContribution { actor_id, hours }],
                concern: "Explain lost work".into(),
                objection: "Respect promised time".into(),
                review_condition: "Review next period".into(),
            })
            .collect(),
        inquiry_hours: 12,
        contact_hours: 8,
        partner_response_hours: 2,
        initial_agreement_through_period: 3,
        contact_renewal_periods: 2,
        content_digest: [5; 32],
        initial_observations: vec![],
    }
}

fn staffing() -> StaffingComposition {
    StaffingComposition::try_new(
        [
            (1, "consumers", 8, StaffingWorkSource::Production(process())),
            (
                2,
                "maintainers",
                1,
                StaffingWorkSource::Maintenance(site(2)),
            ),
        ]
        .into_iter()
        .map(|(id, name, people, source)| {
            StaffingNodeBinding::try_new(
                StableElementKey::Node {
                    scenario: "organizer/replay".into(),
                    local_name: name.into(),
                },
                StaffingPoolBinding::try_new(
                    StaffingPoolId::from_bytes([id; 32]),
                    site(id),
                    unit(2),
                    people,
                    StaffingPolicy::one_period(160).unwrap(),
                    vec![source],
                )
                .unwrap(),
            )
            .unwrap()
        })
        .collect(),
    )
    .unwrap()
}

fn try_session(
    rules: &str,
    material: MaterialCircuitState,
) -> Result<Session, MaterialReplayError> {
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation().unwrap();
    let (_, parsed) = split_content(rules).unwrap();
    let forms = parsed.into_iter().map(|rule| rule.form).collect::<Vec<_>>();
    let graph = ReplayTickSession::new(
        SCENARIO,
        None,
        rules,
        HypergraphStore::new(),
        ReplaySessionId::try_from("organizer/replay-session").unwrap(),
        ReplaySeed::new(40),
        ContentDigest {
            defines_hash: [40; 32],
            rules_hash: rules_hash_of(&forms).unwrap(),
        },
        RefDigest::from_bytes(foundation.reference_bundle_digest()),
        MaterialState::try_new(foundation).unwrap(),
    )
    .map_err(MaterialReplayError::Graph)?;
    let config = config();
    let state = initial_organizer_state(&config).unwrap();
    let material = MaterialWorldRegister::try_new(0, material)
        .unwrap()
        .with_organizer(config, state)
        .unwrap();
    MaterialReplaySession::new(
        graph,
        material,
        sha256_of(b"organizer-replay-fixture-foundation"),
        8,
        staffing(),
    )
}

fn session() -> Session {
    try_session(&format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"), opening()).unwrap()
}

fn commitment(session: &Session, choice: OrganizerChoice) -> OrganizerCommitment {
    let config = session.material().organizer_config().unwrap();
    let state = session.material().organizer_state().unwrap();
    admit_organizer(
        config,
        state,
        &OrganizerCommand {
            campaign_id: config.campaign_id,
            actor_id: config.controlled_actor_id,
            authority_id: config.input_authority_id,
            expected_period: state.period,
            content_digest: config.content_digest,
            resource_digest: organizer_resource_digest().unwrap(),
            nonce: [7; 16],
            choice,
        },
    )
    .unwrap()
}

fn prepare(session: &Session, accepted: Option<&OrganizerCommitment>) -> Candidate {
    let actions = organizer_action_batch(
        session.material().organizer_config().unwrap(),
        session.material().organizer_state().unwrap(),
        accepted,
        session.graph_session().session_identity().clone(),
    )
    .unwrap();
    session
        .prepare_advance_with_organizer(&actions, accepted)
        .unwrap()
}

fn commit(session: &mut Session, sink: &mut CollectingSink, candidate: Candidate) {
    session
        .commit_prepared_and_publish(sink, candidate, |_| {
            Ok::<_, &'static str>(ReplayCommitDisposition::Committed)
        })
        .unwrap();
}

fn advance(session: &mut Session, sink: &mut CollectingSink) {
    let candidate = prepare(session, None);
    commit(session, sink, candidate);
}

#[test]
fn idle_workplace_without_a_production_commitment_closes_and_reports_zero_work() {
    let mut session = session();
    let mut sink = CollectingSink::default();
    advance(&mut session, &mut sink);
    assert_eq!(
        session
            .material()
            .organizer_state()
            .unwrap()
            .last_workplace_facts
            .as_ref()
            .unwrap()
            .output_kg,
        960
    );
    assert!(
        session.material().state().production_commitments.is_empty(),
        "expired opening service prevents another committed batch"
    );
    let second = prepare(&session, None);
    assert!(decode_material_receipts(second.material().receipt_bytes())
        .unwrap()
        .production
        .is_empty());
    let organizer = second.material().register().organizer_state().unwrap();
    let facts = organizer.last_workplace_facts.as_ref().unwrap();
    assert_eq!(
        (facts.period, facts.output_kg, facts.performed_labor_hours),
        (2, 0, 0)
    );
    assert!(matches!(
        organizer.observations.last().unwrap().report,
        OrganizerReport::ReducedWork {
            previous_labor_hours: 960,
            performed_labor_hours: 0
        }
    ));
    commit(&mut session, &mut sink, second);
    let inquiry = commitment(
        &session,
        OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost),
    );
    let third = prepare(&session, Some(&inquiry));
    let organizer = third.material().register().organizer_state().unwrap();
    let observed = organizer.observations.last().unwrap();
    assert_eq!((observed.observed_period, observed.acquired_period), (2, 3));
    assert!(matches!(
        observed.report,
        OrganizerReport::Work {
            output_kg: 0,
            performed_labor_hours: 0,
            ..
        }
    ));
    assert_eq!(
        organizer.last_workplace_facts.as_ref().unwrap().output_kg,
        960,
        "real maintenance staffing recovers production"
    );
}

#[test]
fn organizer_register_requires_both_authored_role_separated_operations() {
    for rules in [
        MATERIAL.to_owned(),
        format!("{MATERIAL}\n{PRODUCTS}"),
        format!("{MATERIAL}\n{PRACTICE}"),
    ] {
        let error = try_session(&rules, opening())
            .err()
            .expect("missing organizer operation must refuse before gameplay");
        assert!(error.to_string().contains("organizer"), "{error}");
    }
}

#[test]
fn distinct_rulings_change_organizer_receipts_and_preserve_identical_material_results() {
    let choices = [
        OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost),
        OrganizerChoice::Reinforce,
        OrganizerChoice::Hold,
        OrganizerChoice::PauseStanding,
    ];
    let candidates = choices.map(|choice| {
        let mut session = session();
        let mut sink = CollectingSink::default();
        advance(&mut session, &mut sink);
        advance(&mut session, &mut sink);
        let accepted = commitment(&session, choice);
        let actions = organizer_action_batch(
            session.material().organizer_config().unwrap(),
            session.material().organizer_state().unwrap(),
            Some(&accepted),
            session.graph_session().session_identity().clone(),
        )
        .unwrap();
        let candidate = session
            .prepare_advance_with_organizer(&actions, Some(&accepted))
            .unwrap();
        (actions.canonical_bytes().to_vec(), candidate)
    });
    for pair in candidates.windows(2) {
        assert_ne!(pair[0].0, pair[1].0);
        let left = pair[0].1.material();
        let right = pair[1].1.material();
        assert_eq!(left.register().state(), right.register().state());
        assert_eq!(left.receipt_bytes(), right.receipt_bytes());
        assert_ne!(
            left.register().organizer_state(),
            right.register().organizer_state()
        );
        assert_ne!(pair[0].1.identity(), pair[1].1.identity());
    }
    let costs = candidates
        .iter()
        .map(|(_, row)| {
            row.material()
                .register()
                .organizer_state()
                .unwrap()
                .receipts
                .last()
                .unwrap()
                .hours_spent
        })
        .collect::<Vec<_>>();
    assert_eq!(costs, [12, 8, 8, 0]);
}

#[test]
fn rejected_commit_publishes_nothing_and_identical_pending_input_retries_deterministically() {
    let mut session = session();
    let mut sink = CollectingSink::default();
    let accepted = commitment(&session, OrganizerChoice::Reinforce);
    let accepted_before = accepted.clone();
    let before_material = session.material().canonical_bytes().to_vec();
    let before_graph = session
        .graph_session()
        .graph()
        .encode_state()
        .unwrap()
        .as_bytes()
        .to_vec();
    let before_hash = session.current_world_hash().unwrap();
    let candidate = prepare(&session, Some(&accepted));
    let expected_identity = *candidate.identity();
    let result = session.commit_prepared_and_publish(&mut sink, candidate, |_| {
        Err::<ReplayCommitDisposition, _>("injected durable failure")
    });
    assert!(matches!(
        result,
        Err(MaterialCommitError::Commit("injected durable failure"))
    ));
    assert_eq!(session.material().canonical_bytes(), before_material);
    assert_eq!(
        session
            .graph_session()
            .graph()
            .encode_state()
            .unwrap()
            .as_bytes(),
        before_graph
    );
    assert_eq!(session.current_world_hash().unwrap(), before_hash);
    assert_eq!(session.completed_tick(), 0);
    assert_eq!(session.graph_session().completed_tick(), 0);
    assert!(sink.events.is_empty());
    assert_eq!(accepted, accepted_before);
    let retry = prepare(&session, Some(&accepted));
    assert_eq!(*retry.identity(), expected_identity);
    commit(&mut session, &mut sink, retry);
    assert_eq!(session.completed_tick(), 1);
    assert_eq!(
        session.material().organizer_state().unwrap().receipts.len(),
        1
    );
    assert_eq!(
        session.material().organizer_state().unwrap().receipts[0].hours_spent,
        8
    );
}
