//! A small Designed maintenance workplace crosses the real BSL/tick boundary.

#[allow(dead_code, reason = "reuse the checked Michigan foundation loader")]
#[path = "../../babylon-persistence/src/michigan_dynamic_hex_foundation.rs"]
mod michigan_dynamic_hex_foundation;

use babylon_bsl::canonical_ast;
use babylon_bsl::rule_pipeline;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::stable_element::StableElementKey;
use babylon_graph::state_hash::CanonicalState;
use babylon_kernel::content_digest;
use babylon_kernel::content_digest::ContentDigest;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_kernel::tick_content_hash::RefDigest;
use babylon_material_circuit::CapacityReservations;
use babylon_material_circuit::CapacityRow;
use babylon_material_circuit::CapacitySupply;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::CommodityDefinition;
use babylon_material_circuit::GoodId;
use babylon_material_circuit::InputOutputCoefficient;
use babylon_material_circuit::InventoryRow;
use babylon_material_circuit::LaborCapacityRow;
use babylon_material_circuit::LaborCoefficient;
use babylon_material_circuit::LogisticsNodeId;
use babylon_material_circuit::MaintenanceBinding;
use babylon_material_circuit::MaintenanceService;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::ProcessId;
use babylon_material_circuit::ProcessOutput;
use babylon_material_circuit::ProductionCommitment;
use babylon_material_circuit::SiteId;
use babylon_material_circuit::SiteLogisticsNode;
use babylon_material_circuit::StaffingPolicy;
use babylon_material_circuit::StaffingPoolBinding;
use babylon_material_circuit::StaffingPoolId;
use babylon_material_circuit::StaffingWorkSource;
use babylon_material_circuit::UnitId;
use babylon_practice_contract::OrganizerChoice;
use babylon_practice_contract::OrganizerCommand;
use babylon_practice_contract::OrganizerCommitment;
use babylon_practice_contract::OrganizerConfig;
use babylon_practice_contract::OrganizerContribution;
use babylon_practice_contract::OrganizerInquiry;
use babylon_practice_contract::OrganizerParticipant;
use babylon_practice_contract::OrganizerPartner;
use babylon_practice_contract::OrganizerPartnerPolicy;
use babylon_practice_contract::OrganizerPeriodJournal;
use babylon_practice_contract::OrganizerReport;
use babylon_practice_contract::OrganizerTimeBindingMode;
use babylon_practice_contract::ORGANIZER_SCHEMA_VERSION;
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
  (deffield business/previous-unretained-labor-hours int extensive)
  (node consumers NodeType/SOCIAL_CLASS
    (social-class/employed-population 8)
    (social-class/reserve-population 0))
  (node consumers-workplace NodeType/BUSINESS
    (business/previous-unretained-labor-hours 1280))
  (node maintainers NodeType/SOCIAL_CLASS
    (social-class/employed-population 0)
    (social-class/reserve-population 1))
  (node maintainers-workplace NodeType/BUSINESS
    (business/previous-unretained-labor-hours 0)))
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

#[allow(
    clippy::too_many_lines,
    reason = "a conformance scenario builds its whole fixture and asserts the full trajectory in one test"
)]
fn opening() -> (MaterialCatalog, MaterialCircuitState) {
    let catalog = MaterialCatalog::try_new(MaterialCatalog {
        capacity_policy: CapacitySupply::FiniteSchedule,
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
        commodities: [1, 2]
            .into_iter()
            .map(|id| CommodityDefinition {
                good_id: good(id),
                unit_id: unit(1),
                kind: babylon_material_circuit::CommodityKind::Storable {
                    grams_per_unit: 1000,
                },
            })
            .collect(),
        supplier_routes: vec![],
        route_stages: vec![],
        merchants: vec![],
        handling_coefficients: vec![],
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
        aid_mandates: vec![],
        household_time_policy: vec![],
        service_inputs: vec![],
        household_needs: vec![],
        catalog_digest: babylon_material_circuit::UNSEALED_CATALOG_DIGEST,
    })
    .expect("the fixture catalog canonicalizes");
    let state = MaterialCircuitState {
        period: 1,
        service_connections: vec![],
        service_orders: vec![],
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
        final_demand_principals: vec![],
        final_demand_orders: vec![],
        accounting: CircuitAccounting::PhysicalControl,
        maintenance_service: Some(MaintenanceService {
            period: 1,
            available_batches: 16,
        }),
        capacity_reservations: CapacityReservations::default(),
    };
    (catalog, state)
}

fn config() -> OrganizerConfig {
    OrganizerConfig {
        aid_bindings: vec![],
        schema_version: ORGANIZER_SCHEMA_VERSION,
        collection: None,
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
        time_binding: OrganizerTimeBindingMode::FixedTimeControl,
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
                    local_name: format!("{name}-workplace"),
                },
                StaffingPoolBinding::try_new(
                    StaffingPoolId::from_bytes([id; 32]),
                    site(id),
                    unit(2),
                    people,
                    StaffingPolicy::one_period(160).expect("the one-period fixture advances"),
                    vec![source],
                )
                .expect("the authored fixture satisfies the constructor invariants"),
                vec![
                    babylon_tick::material_staffing::StaffingMemberNodeBinding::try_new(
                        StableElementKey::Node {
                            scenario: "organizer/replay".into(),
                            local_name: name.into(),
                        },
                        babylon_material_circuit::StaffingMemberBinding::try_new(
                            babylon_material_circuit::StaffingMemberId::from_bytes([id; 32]),
                            babylon_material_circuit::FinalDemandPrincipalId::from_bytes([id; 32]),
                            "county:26163"
                                .parse()
                                .expect("the authored literal parses as the declared type"),
                            people,
                        )
                        .expect("the authored fixture satisfies the constructor invariants"),
                    )
                    .expect("the authored fixture satisfies the constructor invariants"),
                ],
            )
            .expect("the authored fixture satisfies the constructor invariants")
        })
        .collect(),
    )
    .expect("the authored fixture satisfies the constructor invariants")
}

fn try_session(
    rules: &str,
    material: (MaterialCatalog, MaterialCircuitState),
) -> Result<Session, MaterialReplayError> {
    let (catalog, material_state) = material;
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
        .expect("the Michigan hex foundation builds");
    let (_, parsed) =
        rule_pipeline::split_content(rules).expect("the authored content splits into its sections");
    let forms = parsed.into_iter().map(|rule| rule.form).collect::<Vec<_>>();
    let graph = ReplayTickSession::new(
        SCENARIO,
        None,
        rules,
        HypergraphStore::new(),
        ReplaySessionId::try_from("organizer/replay-session")
            .expect("the fixture value fits the target range"),
        ReplaySeed::new(40),
        ContentDigest {
            defines_hash: [40; 32],
            rules_hash: canonical_ast::rules_hash_of(&forms)
                .expect("the rule set has a canonical hash"),
        },
        RefDigest::from_bytes(foundation.reference_bundle_digest()),
        MaterialState::try_new(foundation)
            .expect("the authored fixture satisfies the constructor invariants"),
    )
    .map_err(MaterialReplayError::Graph)?;
    let config = config();
    let state = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let material = MaterialWorldRegister::try_new(&catalog, 0, material_state)
        .expect("the authored fixture satisfies the constructor invariants")
        .with_organizer(&catalog, config, state, OrganizerPeriodJournal::empty())
        .expect("the fixture builder accepts the authored options");
    MaterialReplaySession::new(
        graph,
        material,
        catalog,
        content_digest::sha256_of(b"organizer-replay-fixture-foundation"),
        babylon_kernel::clock::CampaignDuration::Finite { final_period: 8 },
        staffing(),
    )
}

fn session() -> Session {
    try_session(&format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"), opening())
        .expect("the fixture opens a session")
}

fn commitment(session: &Session, choice: OrganizerChoice) -> OrganizerCommitment {
    let config = session
        .material()
        .organizer_config()
        .expect("the fixture register carries organizer config");
    let state = session
        .material()
        .organizer_state()
        .expect("the fixture register carries organizer state");
    babylon_practice_contract::admit_organizer(
        config,
        state,
        &OrganizerCommand {
            campaign_id: config.campaign_id,
            actor_id: config.controlled_actor_id,
            authority_id: config.input_authority_id,
            expected_period: state.period,
            content_digest: config.content_digest,
            resource_digest: babylon_practice_contract::organizer_resource_digest()
                .expect("the organizer resource set has a digest"),
            nonce: [7; 16],
            choice,
        },
    )
    .expect("the fixture admits the organizer actor")
}

fn prepare(session: &Session, accepted: Option<&OrganizerCommitment>) -> Candidate {
    let actions = babylon_practice_contract::organizer_action_batch(
        session
            .material()
            .organizer_config()
            .expect("the fixture register carries organizer config"),
        session
            .material()
            .organizer_state()
            .expect("the fixture register carries organizer state"),
        accepted,
        session.graph_session().session_identity().clone(),
    )
    .expect("the authored action batch builds");
    session
        .prepare_advance_with_organizer(&actions, accepted)
        .expect("the session prepares the authored organizer advance")
}

fn commit(session: &mut Session, sink: &mut CollectingSink, candidate: Candidate) {
    session
        .commit_prepared_and_publish(sink, candidate, |_, _| {
            Ok::<_, &'static str>(ReplayCommitDisposition::Committed)
        })
        .expect("the prepared period commits");
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
            .expect("the fixture register carries organizer state")
            .last_workplace_facts
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .output_kg,
        960
    );
    assert!(
        session.material().state().production_commitments.is_empty(),
        "expired opening service prevents another committed batch"
    );
    let second = prepare(&session, None);
    assert_eq!(
        decode_material_receipts(second.material().receipt_bytes())
            .expect("the canonical bytes decode into the declared type")
            .production
            .len(),
        0
    );
    let organizer = second
        .material()
        .register()
        .organizer_state()
        .expect("the fixture register carries organizer state");
    let facts = organizer
        .last_workplace_facts
        .as_ref()
        .expect("the fixture set the optional field before this read");
    assert_eq!(
        (facts.period, facts.output_kg, facts.performed_labor_hours),
        (2, 0, 0)
    );
    assert!(matches!(
        second
            .material()
            .register()
            .organizer_journal()
            .and_then(|journal| journal.latest())
            .and_then(|entries| entries.observations.last())
            .expect("the fixture sequence is non-empty")
            .report,
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
    let organizer = third
        .material()
        .register()
        .organizer_state()
        .expect("the fixture register carries organizer state");
    let observed = third
        .material()
        .register()
        .organizer_journal()
        .and_then(|journal| journal.latest())
        .and_then(|entries| entries.observations.last())
        .expect("the fixture sequence is non-empty");
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
        organizer
            .last_workplace_facts
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .output_kg,
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
        let actions = babylon_practice_contract::organizer_action_batch(
            session
                .material()
                .organizer_config()
                .expect("the fixture register carries organizer config"),
            session
                .material()
                .organizer_state()
                .expect("the fixture register carries organizer state"),
            Some(&accepted),
            session.graph_session().session_identity().clone(),
        )
        .expect("the authored action batch builds");
        let candidate = session
            .prepare_advance_with_organizer(&actions, Some(&accepted))
            .expect("the session prepares the authored organizer advance");
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
                .organizer_journal()
                .and_then(|journal| journal.latest())
                .and_then(|entries| entries.receipts.last())
                .expect("the fixture sequence is non-empty")
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
        .expect("the graph encodes its canonical state")
        .as_bytes()
        .to_vec();
    let before_hash = session
        .current_world_hash()
        .expect("the committed session publishes a world hash");
    let candidate = prepare(&session, Some(&accepted));
    let expected_identity = *candidate.identity();
    let result = session.commit_prepared_and_publish(&mut sink, candidate, |_, _| {
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
            .expect("the graph encodes its canonical state")
            .as_bytes(),
        before_graph
    );
    assert_eq!(
        session
            .current_world_hash()
            .expect("the committed session publishes a world hash"),
        before_hash
    );
    assert_eq!(session.completed_tick(), 0);
    assert_eq!(session.graph_session().completed_tick(), 0);
    assert_eq!(sink.events.len(), 0);
    assert_eq!(accepted, accepted_before);
    let retry = prepare(&session, Some(&accepted));
    assert_eq!(*retry.identity(), expected_identity);
    commit(&mut session, &mut sink, retry);
    assert_eq!(session.completed_tick(), 1);
    let journal = session
        .material()
        .organizer_journal()
        .expect("the fixture register carries organizer journal");
    let receipts = journal
        .latest()
        .expect("the fixture resolves one period")
        .receipts
        .clone();
    assert_eq!(receipts.len(), 1);
    assert_eq!(receipts[0].hours_spent, 8);
}
