//! Leaf implementation for the parent module; public paths stay on the parent.

use super::michigan_dynamic_hex_foundation;
use babylon_material_circuit::MaterialCatalogDefinition;

use babylon_bsl::causal_contract::{EffectSignature, EvidenceClass, RuleRole};

use babylon_bsl::evaluator::Value;

use babylon_bsl::identity_codec::StableBslValue;

use babylon_bsl::structural_verbs::CollectingSink;

use babylon_graph::hypergraph_store::HypergraphStore;

use babylon_graph::stable_element::StableElementKey;

use babylon_graph::state_hash::CanonicalState;

use babylon_graph::substrate::GraphSubstrate;

use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};

use babylon_kernel::tick_content_hash::RefDigest;

use babylon_kernel::content_digest::ContentDigest;

use babylon_material_circuit::{
    CapacityRow, CommodityDefinition, CorridorCapacity, CorridorId, GoodId, InputOutputCoefficient,
    InventoryRow, LaborCapacityRow, LaborCoefficient, LogisticsNodeId, MaterialCatalog,
    MaterialCircuitState, OrderAccessMode, OrderId, OrderRow, ProcessId, ProcessOutput, RouteId,
    RouteStage, RouteStageCapacity, SiteId, SiteLogisticsNode, StaffingPolicy, StaffingPoolBinding,
    StaffingPoolId, StaffingWorkSource, SupplierRoute, SupplierTransport, UnitId,
};

use babylon_practice_contract::OrderedPracticeActionBatch;

use babylon_tick::h3_runtime::MichiganDynamicHexValueBits;

use babylon_tick::material_replay::{
    IdentifiedMaterialTick, MaterialBaseError, MaterialCommitError, MaterialReplayError,
    MaterialReplaySession, PreparedMaterialTick,
};

use babylon_tick::material_staffing::{
    StaffingComposition, StaffingMemberNodeBinding, StaffingNodeBinding, EMPLOYED_POPULATION,
    PREVIOUS_UNRETAINED_HOURS, RESERVE_POPULATION, STAFFING_COMPOSITION_ID, STAFFING_FIELDS,
};

use babylon_tick::material_state::{
    DynamicHexStateRow, MaterialState, MaterialStateRows, MaterialStateRowsInput,
    OrganizationStateRow, TerritoryStateRow, WorldRegisterRow,
};

use babylon_tick::material_world::{MaterialTickReceipts, MaterialWorldRegister};

use babylon_bsl::canonical_ast;
use babylon_bsl::rule_pipeline;
use babylon_kernel::content_digest;
use babylon_material_circuit::AidBook;
use babylon_material_circuit::CapacityReservations;
use babylon_material_circuit::CapacitySupply;
use babylon_material_circuit::FinancialInstitutions;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::HouseholdTimeAccounting;
use babylon_tick::material_world;
use babylon_tick::replay_session::{ReplayCommitDisposition, ReplayTickError, ReplayTickSession};

pub(crate) type Session = MaterialReplaySession<HypergraphStore>;

pub(crate) type Candidate = PreparedMaterialTick<HypergraphStore>;

pub(crate) const SCENARIO: &str = r"
(scenario staffing/replay
  (deffield social-class/employed-population int extensive)
  (deffield social-class/reserve-population int extensive)
  (deffield business/previous-unretained-labor-hours int extensive)
  (deffield business/probability probability intensive)
  (deffield social-class/seen-employed int extensive)
  (deffield social-class/probability probability intensive)
  (node workers NodeType/SOCIAL_CLASS
    (social-class/employed-population 1)
    (social-class/reserve-population 0)
    (social-class/seen-employed 1)
    (social-class/probability 0.9p))
  (node workplace NodeType/BUSINESS
    (business/previous-unretained-labor-hours 160)
    (business/probability 0.9p)))
";

pub(crate) const MATERIAL_CYCLE: &str = r#"
(rule material/period
  :role mechanic :evidence designed
  :material-basis "Close the existing physical circuit and conserved workforce once per period"
  :fuel 1000000
  (anchor :after metabolism)
  (material-cycle))
"#;

// The common after-metabolism boundary orders this explicit later rule after
// the native g4-workforce-staffing composition by the governed rule-ID bytes.
pub(crate) const WITNESS: &str = r#"
(rule zz-staffing/witness
  :role mechanic :evidence designed
  :material-basis "fixture observes the graph workforce after native staffing"
  :fuel 64
  (anchor :after metabolism)
  (bindings (binding employed :field social-class/employed-population))
  (when #t)
  (effects
    (update-node self social-class/seen-employed (set employed))
    (emit EventType/STAFFING_WITNESS (subject self) (employed employed))))
"#;

pub(crate) const FAILURE: &str = r#"
(rule zzz-staffing/failure
  :role mechanic :evidence designed
  :material-basis "fixture invalid write after staffing must abort the whole candidate"
  :fuel 64
  (anchor :after metabolism)
  (bindings
    (binding requested :field business/previous-unretained-labor-hours)
    (binding probability :field business/probability))
  (when (> requested 0))
  (effects
    (emit EventType/STAFFING_ABORT)
    (update-node self business/probability (add 0.4i))))
"#;

pub(crate) fn subject() -> StableElementKey {
    StableElementKey::Node {
        scenario: "staffing/replay".to_owned(),
        local_name: "workplace".to_owned(),
    }
}

pub(crate) fn site(value: u8) -> SiteId {
    SiteId::from_bytes([value; 32])
}

pub(crate) fn good(value: u8) -> GoodId {
    GoodId::from_bytes([value; 32])
}

pub(crate) fn unit(value: u8) -> UnitId {
    UnitId::from_bytes([value; 32])
}

pub(crate) fn process() -> ProcessId {
    ProcessId::from_bytes([1; 32])
}

pub(crate) fn labor(period: u64, available: u64) -> LaborCapacityRow {
    LaborCapacityRow {
        site_id: site(1),
        unit_id: unit(1),
        period,
        available,
    }
}

/// One authored definition set and its opening quantities.
pub(crate) struct Materials {
    pub(crate) catalog: MaterialCatalogDefinition,
    pub(crate) state: MaterialCircuitState,
}

pub(crate) fn opening() -> Materials {
    let catalog = MaterialCatalogDefinition {
        capacity_policy: CapacitySupply::FiniteSchedule,
        site_logistics_nodes: [1, 2]
            .map(|id| SiteLogisticsNode {
                site_id: site(id),
                node_id: LogisticsNodeId::from_bytes([id; 32]),
            })
            .to_vec(),
        process_outputs: vec![ProcessOutput {
            process_id: process(),
            site_id: site(1),
            good_id: good(2),
            unit_id: unit(2),
            quantity_per_batch: 5,
        }],
        input_coefficients: vec![InputOutputCoefficient {
            process_id: process(),
            good_id: good(1),
            unit_id: unit(2),
            quantity_per_batch: 2,
        }],
        labor_coefficients: vec![LaborCoefficient {
            process_id: process(),
            unit_id: unit(1),
            quantity_per_batch: 40,
        }],
        commodities: [1, 2]
            .map(|id| CommodityDefinition {
                good_id: good(id),
                unit_id: unit(2),
                kind: babylon_material_circuit::CommodityKind::Storable {
                    grams_per_unit: 1000,
                },
            })
            .to_vec(),
        supplier_routes: Vec::new(),
        route_stages: Vec::new(),
        merchants: Vec::new(),
        handling_coefficients: Vec::new(),
        maintenance_binding: None,
        aid_mandates: Vec::new(),
        household_time_policy: Vec::new(),
        service_inputs: Vec::new(),
        household_needs: Vec::new(),
    };
    let mut state = MaterialCircuitState {
        period: 1,
        route_stage_capacities: Vec::new(),
        service_connections: vec![],
        service_orders: vec![],
        inventory: vec![InventoryRow {
            site_id: site(2),
            good_id: good(1),
            unit_id: unit(2),
            quantity: 4,
        }],
        orders: Vec::new(),
        freight: Vec::new(),
        corridor_capacities: Vec::new(),
        capacities: (1..=8)
            .map(|period| CapacityRow {
                process_id: process(),
                site_id: site(1),
                period,
                available_batches: 1,
            })
            .collect(),
        labor: vec![labor(1, 160)],
        production_commitments: Vec::new(),
        final_demand_principals: Vec::new(),
        final_demand_orders: Vec::new(),
        accounting: babylon_material_circuit::CircuitAccounting::PhysicalControl,
        maintenance_service: None,
        capacity_reservations: CapacityReservations::default(),
    };
    let mut catalog = catalog;
    install_freight(&mut catalog, &mut state);
    Materials { catalog, state }
}

pub(crate) fn install_freight(
    catalog: &mut MaterialCatalogDefinition,
    state: &mut MaterialCircuitState,
) {
    let route = RouteId::from_bytes([1; 32]);
    let corridor = CorridorId::from_bytes([1; 32]);
    let order = OrderId::from_bytes([1; 32]);
    catalog.supplier_routes.push(SupplierRoute {
        transport_kind: SupplierTransport::Staged,
        buyer_site_id: site(1),
        supplier_site_id: site(2),
        good_id: good(1),
        unit_id: unit(2),
        route_id: route,
    });
    catalog.route_stages.push(RouteStage {
        route_id: route,
        stage_index: 0,
        from_node_id: LogisticsNodeId::from_bytes([2; 32]),
        to_node_id: LogisticsNodeId::from_bytes([1; 32]),
        travel_periods: 2,
        loss_ppm: 0,
    });
    state.route_stage_capacities.push(RouteStageCapacity {
        route_id: route,
        stage_index: 0,
        corridor_id: corridor,
    });
    state.orders.push(OrderRow {
        order_id: order,
        access_mode: OrderAccessMode::CommoditySale,
        buyer_site_id: site(1),
        supplier_site_id: site(2),
        good_id: good(1),
        unit_id: unit(2),
        ordered: 4,
        shipped: 0,
        lost: 0,
        delivered: 0,
        realized: 0,
    });
    state.corridor_capacities.push(CorridorCapacity {
        corridor_id: corridor,
        period: 1,
        available_grams: 4000,
    });
}

pub(crate) fn resident_member(pool: &StaffingPoolBinding) -> StaffingMemberNodeBinding {
    use babylon_material_circuit::{
        FinalDemandPrincipalId, StaffingMemberBinding, StaffingMemberId,
    };
    StaffingMemberNodeBinding::try_new(
        StableElementKey::Node {
            scenario: "staffing/replay".to_owned(),
            local_name: "workers".to_owned(),
        },
        StaffingMemberBinding::try_new(
            StaffingMemberId::from_bytes(pool.site_id().as_bytes()),
            FinalDemandPrincipalId::from_bytes([30; 32]),
            "county:26163"
                .parse()
                .expect("the authored literal parses as the declared type"),
            pool.labor_force(),
        )
        .expect("the authored fixture satisfies the constructor invariants"),
    )
    .expect("the authored fixture satisfies the constructor invariants")
}

pub(crate) fn staffed_labor() -> StaffingComposition {
    let pool = StaffingPoolBinding::try_new(
        StaffingPoolId::from_bytes([1; 32]),
        site(1),
        unit(1),
        1,
        StaffingPolicy::one_period(160).expect("the one-period fixture advances"),
        vec![StaffingWorkSource::Production(process())],
    )
    .expect("the authored fixture satisfies the constructor invariants");
    StaffingComposition::try_new(vec![StaffingNodeBinding::try_new(
        subject(),
        pool.clone(),
        vec![resident_member(&pool)],
    )
    .expect("the authored fixture satisfies the constructor invariants")])
    .expect("the authored fixture satisfies the constructor invariants")
}

pub(crate) fn try_session_with_authored_rules(
    rules: &str,
    labor: StaffingComposition,
) -> Result<Session, MaterialReplayError> {
    try_session_with_material(rules, labor, opening())
}

pub(crate) fn try_session_with_material(
    rules: &str,
    labor: StaffingComposition,
    material: Materials,
) -> Result<Session, MaterialReplayError> {
    let Materials { catalog, state } = material;
    let catalog = MaterialCatalog::try_new(catalog)
        .expect("the authored definitions canonicalize before admission");
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
        ReplaySessionId::try_from("staffing/replay-session")
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
    MaterialReplaySession::new(
        graph,
        MaterialWorldRegister::try_new(&catalog, 0, state)
            .expect("the authored fixture satisfies the constructor invariants"),
        catalog,
        content_digest::sha256_of(b"staffed-replay-fixture-foundation"),
        babylon_kernel::clock::CampaignDuration::Finite { final_period: 7 },
        labor,
    )
}

pub(crate) fn session(rules: &str) -> Session {
    try_session(rules, staffed_labor()).expect("the fixture opens a session")
}

pub(crate) fn paid_material() -> Materials {
    use babylon_kernel::currency::Currency;
    use babylon_material_circuit::{
        AccountId, CashAccount, CircuitAccounting, EmploymentTerms, FinalDemandPrincipal,
        FinalDemandPrincipalId, MonetaryBook, MonetaryCircuit, OutboundOrderId, PurchaseEscrow,
    };
    let Materials { catalog, mut state } = opening();
    let material = &mut state;
    let household = FinalDemandPrincipalId::from_bytes([30; 32]);
    material.final_demand_principals.push(FinalDemandPrincipal {
        id: household,
        location: "county:26163"
            .parse()
            .expect("the authored literal parses as the declared type"),
    });
    let mut book = MonetaryBook::open(vec![
        CashAccount {
            id: AccountId::Site(site(1)),
            cash: Currency::from_micro_units(1000),
        },
        CashAccount {
            id: AccountId::Site(site(2)),
            cash: Currency::from_micro_units(0),
        },
        CashAccount {
            id: AccountId::Household(household),
            cash: Currency::from_micro_units(0),
        },
    ])
    .expect("the fixture opens the authored source");
    for order in &material.orders {
        book.reserve_purchase(
            PurchaseEscrow::new(
                OutboundOrderId::Delivery(order.order_id),
                AccountId::Site(order.buyer_site_id),
                AccountId::Site(order.supplier_site_id),
                order.ordered,
                Currency::from_micro_units(2),
            )
            .expect("the constructor accepts the authored fixture arguments"),
        )
        .expect("the fixture reserve admits the purchase");
    }
    material.accounting = CircuitAccounting::Monetary(Box::new({
        let book = book;
        MonetaryCircuit {
            aid: AidBook::default(),
            household_time: HouseholdTimeAccounting::NotModeled,
            financial: FinancialInstitutions::empty(),
            member_labor: material
                .labor
                .iter()
                .map(|row| babylon_material_circuit::MemberLaborCapacityRow {
                    member_id: babylon_material_circuit::StaffingMemberId::from_bytes(
                        row.site_id.as_bytes(),
                    ),
                    period: row.period,
                    available_hours: row.available,
                })
                .collect(),
            costs: HistoricalCostBook::open(
                &book,
                material
                    .inventory
                    .iter()
                    .map(|row| babylon_material_circuit::StockCarryingValue {
                        owner: AccountId::Site(row.site_id),
                        good_id: row.good_id,
                        unit_id: row.unit_id,
                        amount: Currency::from_micro_units(0),
                    })
                    .collect(),
                vec![],
                vec![],
                vec![],
            )
            .expect("the fixture opens the authored source"),
            book,
            recurring: None,
            employment: vec![EmploymentTerms {
                member_id: babylon_material_circuit::StaffingMemberId::from_bytes(
                    (site(1)).as_bytes(),
                ),
                site_id: site(1),
                unit_id: unit(1),
                payee: household,
                compensation: babylon_material_circuit::LaborCompensation::Wage(
                    Currency::from_micro_units(1),
                ),
            }],
        }
    }));
    Materials { catalog, state }
}

pub(crate) fn paid_session() -> Session {
    try_session_with_material(MATERIAL_CYCLE, staffed_labor(), paid_material())
        .expect("the fixture opens a session with material")
}

pub(crate) fn try_session(
    additional_rules: &str,
    labor: StaffingComposition,
) -> Result<Session, MaterialReplayError> {
    try_session_with_authored_rules(&format!("{MATERIAL_CYCLE}\n{additional_rules}"), labor)
}

#[test]
pub(crate) fn material_session_requires_an_authored_cycle() {
    assert!(
        try_session_with_authored_rules("", staffed_labor()).is_err(),
        "a material campaign must not run an unauthored native fallback"
    );
}

#[test]
pub(crate) fn authored_cycle_fires_once_and_retains_the_current_physical_result() {
    let session = try_session_with_authored_rules(MATERIAL_CYCLE, staffed_labor())
        .expect("the authored cycle must bind to the current material runtime");
    let candidate = prepare(&session);
    let report = candidate.graph_report().report();
    assert_eq!(
        report.per_rule_considered,
        [("material/period".to_owned(), 1)]
    );
    assert_eq!(report.per_rule_fired, [("material/period".to_owned(), 1)]);
    assert_eq!(candidate.material().register().completed_tick(), 1);
    assert_eq!(staffing_field(&candidate, "closing-employed"), 1);
    assert_eq!(session.completed_tick(), 0, "preparation must not publish");
}

#[test]
pub(crate) fn duplicate_authored_cycles_refuse_in_both_source_orders() {
    let duplicate = MATERIAL_CYCLE.replace("material/period", "campaign/second-cycle");
    for source in [
        format!("{MATERIAL_CYCLE}\n{duplicate}"),
        format!("{duplicate}\n{MATERIAL_CYCLE}"),
    ] {
        let error = try_session_with_authored_rules(&source, staffed_labor())
            .err()
            .expect("two authored invocations must not close two periods");
        assert!(
            error.to_string().contains("only one material-cycle"),
            "{error}"
        );
    }
}

#[test]
pub(crate) fn source_order_cannot_change_material_execution_or_joint_identity() {
    let mut sessions = [
        format!("{MATERIAL_CYCLE}\n{WITNESS}"),
        format!("{WITNESS}\n{MATERIAL_CYCLE}"),
    ]
    .map(|rules| {
        try_session_with_authored_rules(&rules, staffed_labor())
            .expect("the fixture opens a session with authored rules")
    });
    for _ in 0..4 {
        let [first, second] = &mut sessions;
        let left = prepare(first);
        let right = prepare(second);
        assert_eq!(left.identity(), right.identity());
        assert_eq!(
            left.graph_report().result_stable_graph(),
            right.graph_report().result_stable_graph()
        );
        assert_eq!(
            left.material().receipt_bytes(),
            right.material().receipt_bytes()
        );
        assert_eq!(
            left.graph_report().report().audit_receipts,
            right.graph_report().report().audit_receipts
        );
        commit(first, &mut CollectingSink::default(), left);
        commit(second, &mut CollectingSink::default(), right);
    }
}

#[test]
pub(crate) fn graph_diagnostic_refuses_material_execution_but_reports_its_fuel() {
    let rows = babylon_tick::fuel_bound_report(SCENARIO, None, MATERIAL_CYCLE)
        .expect("the fixture call `fuel_bound_report` succeeds for the authored inputs");
    assert_eq!(rows.len(), 1);
    assert_eq!((rows[0].declared, rows[0].computed), (1_000_000, 1_000_000));
    let error = babylon_tick::run_once(SCENARIO, MATERIAL_CYCLE)
        .expect_err("a graph diagnostic has no material register");
    assert!(
        error.contains("requires one bound material host"),
        "{error}"
    );
}

pub(crate) fn prepare(session: &Session) -> Candidate {
    let actions = OrderedPracticeActionBatch::empty(
        session.graph_session().session_identity().clone(),
        session.completed_tick() + 1,
    )
    .expect("the empty authored batch constructs");
    session
        .prepare_advance(&actions)
        .expect("the session prepares the authored advance")
}

pub(crate) fn commit(
    session: &mut Session,
    sink: &mut CollectingSink,
    candidate: Candidate,
) -> IdentifiedMaterialTick {
    session
        .commit_prepared_and_publish(sink, candidate, |_, _| {
            Ok::<_, &'static str>(ReplayCommitDisposition::Committed)
        })
        .expect("the prepared period commits")
        .0
}

pub(crate) fn advance(session: &mut Session, sink: &mut CollectingSink) -> MaterialTickReceipts {
    let candidate = prepare(session);
    let receipts = material_world::decode_material_receipts(candidate.material().receipt_bytes())
        .expect("the canonical bytes decode into the declared type");
    commit(session, sink, candidate);
    receipts
}

pub(crate) fn assert_stock(session: &Session, field: &str, expected: f64) {
    let graph = session.graph_session().graph();
    let nodes = graph.nodes(if field == PREVIOUS_UNRETAINED_HOURS {
        "BUSINESS"
    } else {
        "SOCIAL_CLASS"
    });
    assert_eq!(nodes.len(), 1);
    assert_eq!(
        graph
            .node_attribute(nodes[0], field)
            .expect("the fixture node carries the authored attribute")
            .to_bits(),
        expected.to_bits(),
        "{field}"
    );
}

pub(crate) fn assert_people(session: &Session, employed: f64, reserve: f64, previous: f64) {
    assert_eq!((employed + reserve).to_bits(), 1.0_f64.to_bits());
    assert_stock(session, EMPLOYED_POPULATION, employed);
    assert_stock(session, RESERVE_POPULATION, reserve);
    assert_stock(session, PREVIOUS_UNRETAINED_HOURS, previous);
}

pub(crate) fn staffing_field(candidate: &Candidate, name: &str) -> i64 {
    let events = candidate.graph_report().successful_event_batch().events();
    let event = events
        .iter()
        .find(|event| event.emitting_rule() == STAFFING_COMPOSITION_ID)
        .expect("the fixture holds the searched element");
    let (_, value) = event
        .fields()
        .iter()
        .find(|(field, _)| field == name)
        .expect("the fixture holds the searched element");
    let StableBslValue::Int(value) = value else {
        panic!("staffing receipt field {name} must be exact int");
    };
    *value
}

#[derive(Debug, PartialEq)]
pub(crate) struct LiveState {
    graph: Vec<u8>,
    graph_material: MaterialState,
    registers: Vec<u8>,
    physical: Vec<u8>,
    world_hash: [u8; 32],
    tick: u64,
    events: Vec<(String, Vec<(String, Value)>)>,
}

pub(crate) fn live(session: &Session, sink: &CollectingSink) -> LiveState {
    let graph = session.graph_session();
    // These fixture rules change only social-class attributes. Compare the
    // complete live H3 owner to a separately constructed checked foundation;
    // it deliberately offers no unchecked Clone or arbitrary-state constructor.
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
        .expect("the Michigan hex foundation builds");
    let graph_material = MaterialState::try_new(foundation)
        .expect("the authored fixture satisfies the constructor invariants");
    assert_eq!(graph.material_state(), &graph_material);
    LiveState {
        graph: graph
            .graph()
            .encode_state()
            .expect("the graph encodes its canonical state")
            .as_bytes()
            .to_vec(),
        graph_material,
        registers: graph
            .world_registers()
            .expect("the fixture call `world_registers` succeeds for the authored inputs")
            .canonical_bytes()
            .to_vec(),
        physical: session.material().canonical_bytes().to_vec(),
        world_hash: session
            .current_world_hash()
            .expect("the committed session publishes a world hash"),
        tick: session.completed_tick(),
        events: sink.events.clone(),
    }
}

pub(crate) fn owned_checkpoint_rows(rows: &MaterialStateRows) -> MaterialStateRows {
    let owned = MaterialStateRows::try_from_rows(MaterialStateRowsInput {
        world_registers: rows.world_registers().rows().iter().map(|row| {
            WorldRegisterRow::try_new(row.qname().to_owned(), row.value().clone()).expect("the authored fixture satisfies the constructor invariants")
        }).collect(),
        territories: rows.territories().rows().iter().map(|row| {
            TerritoryStateRow::try_new(row.territory_id().clone(), row.ordered_fields().to_vec()).expect("the authored fixture satisfies the constructor invariants")
        }).collect(),
        dynamic_hexes: rows.dynamic_hexes().rows().iter().map(|row| {
            let [c, v, s, k, biocapacity_stock, energy_stock, raw_material_stock,
                internet_access_pct, surveillance_coupling] = row.value_bits();
            DynamicHexStateRow::try_new(row.cell_id(), MichiganDynamicHexValueBits {
                c, v, s, k, biocapacity_stock, energy_stock, raw_material_stock,
                internet_access_pct, surveillance_coupling,
            }).expect("the authored fixture satisfies the constructor invariants")
        }).collect(),
        organizations: rows.organizations().rows().iter().map(|row| {
            OrganizationStateRow::try_new(
                row.organization_id().clone(), row.organization_kind().clone(),
                row.ordered_territory_ids().to_vec(), row.ordered_fields().to_vec(),
            ).expect("the authored fixture satisfies the constructor invariants")
        }).collect(),
    }).expect("the fixture input satisfies the fallible conversion");
    assert_eq!(owned.canonical_bytes(), rows.canonical_bytes());
    owned
}

#[test]
pub(crate) fn one_empty_period_holds_then_releases_and_real_arrival_rehires_for_next_period() {
    let mut session = session("");
    let mut sink = CollectingSink::default();
    let first = prepare(&session);
    assert_eq!(staffing_field(&first, "current-unretained-hours"), 0);
    assert_eq!(staffing_field(&first, "retained-hours"), 160);
    assert_eq!(staffing_field(&first, "separations"), 0);
    let receipts = material_world::decode_material_receipts(first.material().receipt_bytes())
        .expect("the canonical bytes decode into the declared type");
    assert_eq!(
        (
            receipts.dispatches[0].quantity,
            receipts.dispatches[0].final_arrival_period
        ),
        (4, 3)
    );
    commit(&mut session, &mut sink, first);
    assert_people(&session, 1.0, 0.0, 0.0);
    assert_eq!(session.material().state().labor, vec![labor(2, 160)]);

    let second = prepare(&session);
    assert_eq!(staffing_field(&second, "separations"), 1);
    assert_eq!(staffing_field(&second, "retained-hours"), 0);
    commit(&mut session, &mut sink, second);
    assert_people(&session, 0.0, 1.0, 0.0);
    assert_eq!(session.material().state().labor, vec![labor(3, 0)]);
    assert_eq!(session.material().state().production_commitments.len(), 0);

    let arrival = prepare(&session);
    assert_eq!(staffing_field(&arrival, "current-unretained-hours"), 40);
    assert_eq!(staffing_field(&arrival, "hires"), 1);
    let receipts = material_world::decode_material_receipts(arrival.material().receipt_bytes())
        .expect("the canonical bytes decode into the declared type");
    assert_eq!(receipts.arrivals.len(), 1);
    assert_eq!(receipts.arrivals[0].quantity, 4);
    assert_eq!(receipts.production.len(), 0);
    assert_eq!(
        arrival.material().register().state().production_commitments[0].planned_batches,
        1
    );
    commit(&mut session, &mut sink, arrival);
    assert_people(&session, 1.0, 0.0, 40.0);
    assert_eq!(session.material().state().labor, vec![labor(4, 160)]);

    let fourth = advance(&mut session, &mut sink);
    let fifth = advance(&mut session, &mut sink);
    assert_eq!(fourth.production[0].produced_batches, 1);
    assert_eq!(fifth.production[0].produced_batches, 1);
    assert_eq!(
        session.material().state().inventory,
        vec![
            InventoryRow {
                site_id: site(1),
                good_id: good(1),
                unit_id: unit(2),
                quantity: 0
            },
            InventoryRow {
                site_id: site(1),
                good_id: good(2),
                unit_id: unit(2),
                quantity: 10
            },
            InventoryRow {
                site_id: site(2),
                good_id: good(1),
                unit_id: unit(2),
                quantity: 0
            },
        ]
    );
    let order = &session.material().state().orders[0];
    assert_eq!(
        (order.shipped, order.delivered, order.realized, order.lost),
        (4, 4, 4, 0)
    );
    assert_eq!(session.material().state().freight.len(), 0);
    assert_eq!(
        session
            .material()
            .state()
            .derived_backlog()
            .expect("the admitted orders keep an exact backlog"),
        vec![babylon_material_circuit::BacklogRow {
            order_id: OrderId::from_bytes([1; 32]),
            quantity: 0,
        }]
    );
    assert_people(&session, 1.0, 0.0, 0.0);
    advance(&mut session, &mut sink);
    assert_people(&session, 0.0, 1.0, 0.0);
    assert_eq!(session.material().state().labor, vec![labor(7, 0)]);
}

#[test]
pub(crate) fn prepared_and_failed_commit_publish_nothing_and_retry_has_identical_joint_identity() {
    let mut session = session("");
    let mut sink = CollectingSink::default();
    advance(&mut session, &mut sink);
    let before = live(&session, &sink);
    let candidate = prepare(&session);
    assert_eq!(staffing_field(&candidate, "separations"), 1);
    assert_eq!(live(&session, &sink), before);
    let expected = *candidate.identity();
    let expected_graph = candidate.graph_report().result_stable_graph().clone();
    let expected_physical = candidate.material().register().clone();
    let error = session.commit_prepared_and_publish(&mut sink, candidate, |identity, _| {
        assert_eq!(identity, &expected);
        Err::<ReplayCommitDisposition, _>("durable commit refused")
    });
    assert!(matches!(
        error,
        Err(MaterialCommitError::Commit("durable commit refused"))
    ));
    assert_eq!(live(&session, &sink), before);

    let retry = prepare(&session);
    assert_eq!(retry.identity(), &expected);
    assert_eq!(retry.graph_report().result_stable_graph(), &expected_graph);
    assert_eq!(retry.material().register(), &expected_physical);
    let identity = commit(&mut session, &mut sink, retry);
    assert_eq!(identity, expected);
    assert_eq!(session.material(), &expected_physical);
    assert_eq!(
        session
            .graph_session()
            .stable_graph_state()
            .expect("the fixture graph has a stable state"),
        expected_graph
    );
    assert_eq!(session.completed_tick(), 2);
    assert_eq!(session.graph_session().completed_tick(), 2);
    assert_eq!(sink.events.len(), before.events.len() + 1);
    assert_eq!(&sink.events[..before.events.len()], before.events);
    assert_people(&session, 0.0, 1.0, 0.0);
}

#[test]
pub(crate) fn wage_and_dispatch_candidate_is_atomic_and_restarts_through_paid_arrival() {
    use babylon_kernel::currency::Currency;
    use babylon_material_circuit::{AccountId, CircuitAccounting};
    let mut session = paid_session();
    let mut sink = CollectingSink::default();
    let before = live(&session, &sink);
    let candidate = prepare(&session);
    let receipts = material_world::decode_material_receipts(candidate.material().receipt_bytes())
        .expect("the canonical bytes decode into the declared type");
    assert_eq!(receipts.wage_accruals.len(), 1);
    assert_eq!(
        receipts.wage_accruals[0].amount,
        Currency::from_micro_units(160)
    );
    assert_eq!(receipts.labor_use[0].paid_idle_hours, 160);
    let employer = receipts
        .income
        .iter()
        .find(|row| row.account == AccountId::Site(site(1)))
        .expect("the fixture holds the searched element");
    assert_eq!(
        employer.statement.idle_labor_expense,
        Currency::from_micro_units(160)
    );
    assert_eq!(employer.net_income, Currency::from_micro_units(-160));
    let household = receipts
        .income
        .iter()
        .find(|row| matches!(row.account, AccountId::Household(_)))
        .expect("the fixture holds the searched element");
    assert_eq!(
        household.statement.wage_income,
        Currency::from_micro_units(160)
    );
    assert_eq!(household.net_income, Currency::from_micro_units(160));
    assert_eq!(receipts.money_transfers.len(), 2);
    let expected = *candidate.identity();
    let refused = session.commit_prepared_and_publish(&mut sink, candidate, |_, _| {
        Err::<ReplayCommitDisposition, _>("paid commit refused")
    });
    assert!(matches!(
        refused,
        Err(MaterialCommitError::Commit("paid commit refused"))
    ));
    assert_eq!(live(&session, &sink), before);
    let retry = prepare(&session);
    assert_eq!(*retry.identity(), expected);
    let graph = retry.graph_report().result_stable_graph().clone();
    let graph_material = owned_checkpoint_rows(retry.graph_report().material_state_rows());
    let registers = retry
        .graph_report()
        .result_registers()
        .canonical_bytes()
        .to_vec();
    let material = retry.material().register().canonical_bytes().to_vec();
    commit(&mut session, &mut sink, retry);
    let mut restored = paid_session();
    restored
        .restore_full_checkpoint(
            &graph,
            &graph_material,
            &registers,
            MaterialWorldRegister::decode_external(session.catalog(), material.clone())
                .expect("the committed canonical bytes decode"),
        )
        .expect("the committed checkpoint restores");
    let mut restored_sink = CollectingSink::default();
    for _ in 2..=4 {
        let next = prepare(&session);
        let replay = prepare(&restored);
        assert_eq!(replay.identity(), next.identity());
        assert_eq!(
            replay.material().receipt_bytes(),
            next.material().receipt_bytes()
        );
        commit(&mut session, &mut sink, next);
        commit(&mut restored, &mut restored_sink, replay);
    }
    assert_eq!(session.material(), restored.material());
    let CircuitAccounting::Monetary(economy) = &restored.material().state().accounting else {
        panic!("paid circuit")
    };
    assert_eq!(
        economy
            .book
            .cash(AccountId::Site(site(2)))
            .expect("the fixture book holds the payer account"),
        Currency::from_micro_units(8)
    );
    assert_eq!(
        economy
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        Currency::from_micro_units(1000)
    );
}

#[test]
pub(crate) fn successful_acknowledgement_publishes_stable_staffing_and_identity_free_audit_evidence(
) {
    let mut session = session("");
    let mut sink = CollectingSink::default();
    advance(&mut session, &mut sink);
    let candidate = prepare(&session);
    let report = candidate.graph_report();
    let events = report.successful_event_batch().events();
    assert_eq!(events.len(), 1);
    assert_eq!(events[0].event_type(), "WORKFORCE_STAFFING");
    assert_eq!(events[0].emitting_rule(), STAFFING_COMPOSITION_ID);
    assert_eq!(events[0].choice_receipt(), None);
    assert!(events[0]
        .fields()
        .contains(&("subject".to_owned(), StableBslValue::Node(subject()))));
    for (name, expected) in [
        ("period", 2),
        ("opening-employed", 1),
        ("opening-reserve", 0),
        ("closing-employed", 0),
        ("closing-reserve", 1),
        ("separations", 1),
        ("hires", 0),
        ("next-opening-hours", 0),
    ] {
        assert_eq!(staffing_field(&candidate, name), expected);
    }
    let audit = &report.report().audit_receipts;
    assert_eq!(audit.len(), 5);
    assert_eq!(audit[0].rule_id, "material/period");
    assert_eq!(audit[0].ordinal, 0);
    assert_eq!(audit[0].effect, EffectSignature::MaterialCycle);
    let audit = &audit[1..];
    assert!(audit
        .iter()
        .all(|row| row.rule_id == STAFFING_COMPOSITION_ID
            && row.role == RuleRole::Mechanic
            && row.evidence == EvidenceClass::Designed));
    assert_eq!(
        audit.iter().map(|row| row.ordinal).collect::<Vec<_>>(),
        [0, 1, 2, 3]
    );
    assert_eq!(
        audit[0].effect,
        EffectSignature::Event("EventType/WORKFORCE_STAFFING".to_owned())
    );
    assert_eq!(
        audit[1..].iter().map(|row| &row.effect).collect::<Vec<_>>(),
        [
            &EffectSignature::NodeField(PREVIOUS_UNRETAINED_HOURS.to_owned()),
            &EffectSignature::NodeField(EMPLOYED_POPULATION.to_owned()),
            &EffectSignature::NodeField(RESERVE_POPULATION.to_owned()),
        ]
    );
    assert_eq!(
        candidate.identity().graph_tick_content_hash(),
        report.tick_content_hash()
    );
    assert_eq!(
        candidate.identity().receipt_digest(),
        content_digest::sha256_of(candidate.material().receipt_bytes())
    );
    let expected_event = report.report().committed_events[0].clone();
    commit(&mut session, &mut sink, candidate);
    assert_eq!(
        sink.events
            .last()
            .expect("the fixture sequence is non-empty"),
        &(
            expected_event.event_type().to_owned(),
            expected_event.payload().to_vec(),
        )
    );
    assert_people(&session, 0.0, 1.0, 0.0);
    assert_eq!(session.material().state().labor, vec![labor(3, 0)]);
}

#[test]
pub(crate) fn later_anchored_rule_reads_this_candidates_staffing_before_graph_finalization() {
    let mut session = session(WITNESS);
    let mut sink = CollectingSink::default();
    advance(&mut session, &mut sink);
    assert_stock(&session, "social-class/seen-employed", 1.0);
    let candidate = prepare(&session);
    let events = candidate.graph_report().successful_event_batch().events();
    assert_eq!(
        events
            .iter()
            .map(babylon_tick::replay_session::SuccessfulEvent::emitting_rule)
            .collect::<Vec<_>>(),
        [STAFFING_COMPOSITION_ID, "zz-staffing/witness"]
    );
    assert!(events[1].fields().contains(&(
        "employed".to_owned(),
        StableBslValue::RealBits(0.0_f64.to_bits()),
    )));
    // Preparation has exposed the changed stock only to the detached later rule.
    assert_stock(&session, "social-class/seen-employed", 1.0);
    assert_people(&session, 1.0, 0.0, 0.0);
    commit(&mut session, &mut sink, candidate);
    assert_stock(&session, "social-class/seen-employed", 0.0);
    assert_people(&session, 0.0, 1.0, 0.0);
}

#[test]
pub(crate) fn failing_later_rule_aborts_staffing_physical_close_events_and_both_clocks() {
    let mut session = session(&format!("{WITNESS}\n{FAILURE}"));
    let mut sink = CollectingSink::default();
    advance(&mut session, &mut sink);
    advance(&mut session, &mut sink);
    assert_people(&session, 0.0, 1.0, 0.0);
    assert_eq!(session.material().state().freight[0].quantity, 4);
    let before = live(&session, &sink);
    let actions =
        OrderedPracticeActionBatch::empty(session.graph_session().session_identity().clone(), 3)
            .expect("the empty authored batch constructs");
    for _ in 0..2 {
        let result = session.prepare_advance(&actions);
        let Err(MaterialReplayError::Graph(ReplayTickError::Execution { message })) = result else {
            panic!("the later domain-invalid write must abort replay execution");
        };
        assert!(message.contains("zzz-staffing/failure"), "{message}");
        assert_eq!(live(&session, &sink), before);
    }
    assert_people(&session, 0.0, 1.0, 0.0);
    assert_stock(&session, "social-class/seen-employed", 0.0);
    assert_eq!(session.material().state().labor, vec![labor(3, 0)]);
}

#[test]
pub(crate) fn same_version_checkpoint_restores_retention_and_replays_arrival_with_identical_evidence(
) {
    let mut uninterrupted = session(WITNESS);
    let mut original_sink = CollectingSink::default();
    advance(&mut uninterrupted, &mut original_sink);
    let second = prepare(&uninterrupted);
    let graph = second.graph_report().result_stable_graph().clone();
    let graph_material = owned_checkpoint_rows(second.graph_report().material_state_rows());
    let registers = second
        .graph_report()
        .result_registers()
        .canonical_bytes()
        .to_vec();
    let physical = second.material().register().canonical_bytes().to_vec();
    commit(&mut uninterrupted, &mut original_sink, second);

    let mut restored = session(WITNESS);
    restored
        .restore_full_checkpoint(
            &graph,
            &graph_material,
            &registers,
            MaterialWorldRegister::decode_external(restored.catalog(), physical.clone())
                .expect("the committed canonical bytes decode"),
        )
        .expect("the committed checkpoint restores");
    assert_people(&restored, 0.0, 1.0, 0.0);
    assert_eq!(
        restored
            .current_world_hash()
            .expect("the committed session publishes a world hash"),
        uninterrupted
            .current_world_hash()
            .expect("the committed session publishes a world hash")
    );
    let mut restored_sink = CollectingSink::default();
    let original_event_count = original_sink.events.len();
    for _ in 3..=5 {
        let next = prepare(&uninterrupted);
        let replay = prepare(&restored);
        assert_eq!(replay.identity(), next.identity());
        assert_eq!(
            replay.graph_report().successful_event_batch(),
            next.graph_report().successful_event_batch()
        );
        assert_eq!(
            replay.graph_report().report().audit_receipts,
            next.graph_report().report().audit_receipts
        );
        assert_eq!(
            replay.material().receipt_bytes(),
            next.material().receipt_bytes()
        );
        commit(&mut uninterrupted, &mut original_sink, next);
        commit(&mut restored, &mut restored_sink, replay);
    }
    assert_eq!(restored.material(), uninterrupted.material());
    assert_eq!(
        restored
            .graph_session()
            .stable_graph_state()
            .expect("the fixture graph has a stable state"),
        uninterrupted
            .graph_session()
            .stable_graph_state()
            .expect("the fixture graph has a stable state")
    );
    assert_eq!(
        restored_sink.events,
        original_sink.events[original_event_count..]
    );
}

#[test]
pub(crate) fn staffed_admission_refuses_every_native_field_in_early_late_and_untaken_writes() {
    for field in STAFFING_FIELDS {
        for (anchor, guard) in [
            ("before vitality", "#t"),
            ("after metabolism", "#t"),
            ("after metabolism", "#f"),
        ] {
            let source = format!(
                r#"
(rule zz-staffing/foreign-writer
  :role mechanic :evidence designed
  :material-basis "fixture exercises declared ownership even when the branch is untaken"
  :fuel 64
  (anchor :{anchor})
  (bindings (binding employed :field social-class/employed-population))
  (when #t)
  (effects (guard {guard} (update-node self {field} (set 9)))))
"#
            );
            let error = try_session(&source, staffed_labor())
                .err()
                .unwrap_or_else(|| {
                    panic!("Staffed accepted {anchor} write to {field}, guard {guard}")
                });
            let MaterialReplayError::Graph(ReplayTickError::MaterialBase(
                MaterialBaseError::StaffingFieldOwner {
                    rule_id,
                    field: actual,
                },
            )) = &error
            else {
                panic!("Staffed must refuse {anchor} write to {field}, guard {guard}: {error:?}");
            };
            assert_eq!(rule_id, "zz-staffing/foreign-writer");
            assert_eq!(actual, field);
        }
    }
}

#[test]
pub(crate) fn removing_the_staffed_subject_is_refused_by_the_existing_shape_verb_loader() {
    let source = r#"
(rule zz-staffing/remove-owner
  :role mechanic :evidence designed
  :material-basis "fixture preserves the existing graph-shape loading boundary"
  :fuel 64
  (anchor :after metabolism)
  (bindings (binding employed :field social-class/employed-population))
  (when #t)
  (effects (remove-node self)))
"#;
    {
        let labor = staffed_labor();
        let result = try_session(source, labor);
        let Err(MaterialReplayError::Graph(ReplayTickError::Preparation { message })) = result
        else {
            panic!("the existing shape-verb gate must refuse before a session is created");
        };
        assert!(message.contains("remove-node"), "{message}");
        assert!(message.contains("graph-shape verbs"), "{message}");
    }
}

#[test]
pub(crate) fn admitted_checkpoint_refusal_preserves_both_owners_and_valid_retry_replays() {
    let mut original = session(WITNESS);
    let mut original_sink = CollectingSink::default();
    let candidate = prepare(&original);
    let graph = candidate.graph_report();
    let registers = graph.result_registers().canonical_bytes();
    let mut damaged_registers = registers.to_vec();
    damaged_registers[0] ^= 1;
    let admitted = MaterialWorldRegister::decode_external(
        original.catalog(),
        candidate.material().register().canonical_bytes().to_vec(),
    )
    .expect("the committed canonical bytes decode");
    let mut resumed = session(WITNESS);
    let resumed_sink = CollectingSink::default();
    let before = live(&resumed, &resumed_sink);

    assert!(matches!(
        resumed.restore_full_checkpoint(
            graph.result_stable_graph(),
            graph.material_state_rows(),
            &damaged_registers,
            admitted,
        ),
        Err(MaterialReplayError::Graph(
            ReplayTickError::CheckpointMismatch {
                section: "world registers",
            }
        ))
    ));
    assert_eq!(live(&resumed, &resumed_sink), before);

    let opening = MaterialWorldRegister::decode_external(
        resumed.catalog(),
        resumed.material().canonical_bytes().to_vec(),
    )
    .expect("the committed canonical bytes decode");
    assert!(matches!(
        resumed.restore_full_checkpoint(
            graph.result_stable_graph(),
            graph.material_state_rows(),
            registers,
            opening,
        ),
        Err(MaterialReplayError::Horizon)
    ));
    assert_eq!(live(&resumed, &resumed_sink), before);

    let admitted = MaterialWorldRegister::decode_external(
        original.catalog(),
        candidate.material().register().canonical_bytes().to_vec(),
    )
    .expect("the committed canonical bytes decode");
    resumed
        .restore_full_checkpoint(
            graph.result_stable_graph(),
            graph.material_state_rows(),
            registers,
            admitted,
        )
        .expect("the committed checkpoint restores");
    assert_eq!(
        resumed
            .current_world_hash()
            .expect("the committed session publishes a world hash"),
        candidate.identity().result_world_hash()
    );
    commit(&mut original, &mut original_sink, candidate);
    let continued = prepare(&original);
    let replayed = prepare(&resumed);
    assert_eq!(replayed.identity(), continued.identity());
    assert_eq!(
        replayed.material().receipt_bytes(),
        continued.material().receipt_bytes()
    );
}
