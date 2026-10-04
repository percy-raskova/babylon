//! Shared real material/organizer replay fixture; no duplicate transition controls.

use babylon_bsl::canonical_ast::rules_hash_of;
use babylon_bsl::rule_pipeline::split_content;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::content_digest::{sha256_of, ContentDigest};
use babylon_kernel::currency::Currency;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_kernel::tick_content_hash::RefDigest;
use babylon_material_circuit::*;
use babylon_practice_contract::*;
use babylon_tick::h3_runtime::MichiganDynamicHexFoundation;
use babylon_tick::material_replay::{
    MaterialReplayError, MaterialReplaySession, PreparedMaterialTick,
};
use babylon_tick::material_staffing::{StaffingComposition, StaffingNodeBinding};
use babylon_tick::material_state::MaterialState;
use babylon_tick::material_world::MaterialWorldRegister;
use babylon_tick::replay_session::{ReplayCommitDisposition, ReplayTickSession};

pub(crate) type Session = MaterialReplaySession<HypergraphStore>;
pub(crate) type Candidate = PreparedMaterialTick<HypergraphStore>;

const SCENARIO: &str = r"
(scenario organizer/replay
  (deffield social-class/employed-population int extensive)
  (deffield social-class/reserve-population int extensive)
  (deffield business/previous-unretained-labor-hours int extensive)
  (node consumers NodeType/SOCIAL_CLASS
    (social-class/employed-population 1)
    (social-class/reserve-population 0))
  (node consumers-workplace NodeType/BUSINESS
    (business/previous-unretained-labor-hours 4))
  (node maintainers NodeType/SOCIAL_CLASS
    (social-class/employed-population 2)
    (social-class/reserve-population 0))
  (node maintainers-workplace NodeType/BUSINESS
    (business/previous-unretained-labor-hours 8))
  (node merchants NodeType/SOCIAL_CLASS (social-class/employed-population 1) (social-class/reserve-population 0))
  (node merchants-workplace NodeType/BUSINESS (business/previous-unretained-labor-hours 4)))
";

pub(crate) const MATERIAL: &str = r#"
(rule material/period
  :role mechanic :evidence designed
  :material-basis "Close the checked fixture material circuit and workforce"
  :fuel 1000000
  (anchor :after metabolism)
  (material-cycle))
"#;

pub(crate) const PRODUCTS: &str = r#"
(rule organizer/organizer-products
  :role mechanic :evidence designed
  :material-basis "Consume committed contact products and produce scoped material reports"
  :fuel 1000000
  (anchor :before ooda)
  (organizer-products))
"#;

pub(crate) const PRACTICE: &str = r#"
(rule organizer/organizer-practice
  :role intent :evidence designed
  :material-basis "Execute the accepted ruling or authorized routine through committed time"
  :fuel 1000000
  (anchor :after ooda)
  (organizer-practice))
"#;

pub(crate) fn site(id: u8) -> SiteId {
    SiteId::from_bytes([id; 32])
}
fn node(id: u8) -> LogisticsNodeId {
    LogisticsNodeId::from_bytes([id; 32])
}
pub(crate) fn good(id: u8) -> GoodId {
    GoodId::from_bytes([id; 32])
}
fn process(id: u8) -> ProcessId {
    ProcessId::from_bytes([id; 32])
}
fn corridor(id: u8) -> CorridorId {
    CorridorId::from_bytes([id; 32])
}
fn route(id: u8) -> RouteId {
    RouteId::from_bytes([id; 32])
}
pub(crate) fn household() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([1; 32])
}
fn units() -> UnitId {
    UnitId::from_bytes([1; 32])
}
fn hours() -> UnitId {
    UnitId::from_bytes([2; 32])
}
pub(crate) fn money(value: i128) -> Currency {
    Currency::from_micro_units(value)
}
fn inventory(owner: u8, commodity: u8, quantity: u64) -> InventoryRow {
    InventoryRow {
        site_id: site(owner),
        good_id: good(commodity),
        unit_id: units(),
        quantity,
    }
}

fn recurring() -> RecurringEconomy {
    let offers = [(1, 1, 1), (2, 2, 3), (3, 2, 4)]
        .into_iter()
        .map(|(owner, commodity, price)| SellerOffer {
            site_id: site(owner),
            good_id: good(commodity),
            unit_id: units(),
            unit_price: money(price),
            pricing: PricePolicy::Fixed,
        })
        .collect();
    RecurringEconomy {
        service_inputs: vec![],
        households: vec![HouseholdCohort {
            kind: babylon_material_circuit::HouseholdKind::Ordinary,
            principal_id: household(),
            households: 2,
            persons: 4,
        }],
        household_stocks: vec![HouseholdStock {
            principal_id: household(),
            good_id: good(2),
            unit_id: units(),
            quantity: 8,
        }],
        household_needs: vec![HouseholdNeed {
            principal_id: household(),
            good_id: good(2),
            unit_id: units(),
            basis: babylon_material_circuit::HouseholdNeedBasis::Persons,
            units_per_basis: 1,
        }],
        household_purchases: vec![HouseholdPurchasePolicy {
            principal_id: household(),
            retailer_site_id: site(3),
            good_id: good(2),
            unit_id: units(),
            target_closing_stock: 8,
            maximum_purchase: 4,
            enabled: true,
        }],
        offers,
        replenishment: [(2, 1, 1), (3, 2, 2)]
            .into_iter()
            .map(|(buyer, supplier, commodity)| ReplenishmentPolicy {
                buyer_site_id: site(buyer),
                supplier_site_id: site(supplier),
                good_id: good(commodity),
                unit_id: units(),
                target_stock: 4,
                maximum_purchase: 4,
                cash_floor: money(0),
            })
            .collect(),
        production: [1, 2]
            .into_iter()
            .map(|owner| ProductionDemandPolicy {
                process_id: process(owner),
                site_id: site(owner),
                output_buffer: 0,
                planned_batches: 4,
            })
            .collect(),
        attendance: [(1, 4), (2, 8), (3, 4)]
            .into_iter()
            .map(|(owner, planned_hours)| AttendancePlan {
                site_id: site(owner),
                unit_id: hours(),
                period: 1,
                planned_hours,
            })
            .collect(),
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    }
}

fn accounting(recurring: RecurringEconomy) -> CircuitAccounting {
    CircuitAccounting::Monetary(Box::new({
        let book = MonetaryBook::open(vec![
            CashAccount {
                id: AccountId::Site(site(1)),
                cash: money(4),
            },
            CashAccount {
                id: AccountId::Site(site(2)),
                cash: money(12),
            },
            CashAccount {
                id: AccountId::Site(site(3)),
                cash: money(8),
            },
            CashAccount {
                id: AccountId::Household(household()),
                cash: money(0),
            },
        ])
        .unwrap();
        MonetaryCircuit {
            aid: AidBook::default(),

            household_time: babylon_material_circuit::HouseholdTimeAccounting::NotModeled,
            financial: babylon_material_circuit::FinancialInstitutions::empty(),
            member_labor: (1..=9)
                .flat_map(|period| {
                    [(1, 4), (2, 8), (3, 4)]
                        .into_iter()
                        .map(move |(owner, available_hours)| {
                            babylon_material_circuit::MemberLaborCapacityRow {
                                member_id: babylon_material_circuit::StaffingMemberId::from_bytes(
                                    site(owner).as_bytes(),
                                ),
                                period,
                                available_hours,
                            }
                        })
                })
                .collect(),
            costs: HistoricalCostBook::open(
                &book,
                [
                    (AccountId::Site(site(1)), good(0), 0),
                    (AccountId::Site(site(2)), good(1), 4),
                    (AccountId::Site(site(3)), good(2), 12),
                    (AccountId::Household(household()), good(2), 32),
                ]
                .into_iter()
                .map(|(owner, good_id, value)| StockCarryingValue {
                    owner,
                    good_id,
                    unit_id: units(),
                    amount: money(value),
                })
                .collect(),
                vec![],
                vec![],
                vec![],
            )
            .unwrap(),
            book,
            recurring: Some(Box::new(recurring)),
            employment: [1, 2, 3]
                .into_iter()
                .map(|owner| EmploymentTerms {
                    member_id: babylon_material_circuit::StaffingMemberId::from_bytes(
                        (site(owner)).as_bytes(),
                    ),
                    site_id: site(owner),
                    unit_id: hours(),
                    payee: household(),
                    compensation: babylon_material_circuit::LaborCompensation::Wage(money(1)),
                })
                .collect(),
        }
    }))
}

fn process_outputs() -> Vec<ProcessOutput> {
    [1, 2]
        .into_iter()
        .map(|owner| ProcessOutput {
            process_id: process(owner),
            site_id: site(owner),
            good_id: good(owner),
            unit_id: units(),
            quantity_per_batch: 1,
        })
        .collect()
}

fn input_coefficients() -> Vec<InputOutputCoefficient> {
    [1, 2]
        .into_iter()
        .map(|owner| InputOutputCoefficient {
            process_id: process(owner),
            good_id: good(owner - 1),
            unit_id: units(),
            quantity_per_batch: 1,
        })
        .collect()
}

fn labor_coefficients() -> Vec<LaborCoefficient> {
    [(1, 1), (2, 2)]
        .into_iter()
        .map(|(owner, quantity_per_batch)| LaborCoefficient {
            process_id: process(owner),
            unit_id: hours(),
            quantity_per_batch,
        })
        .collect()
}

fn supplier_routes() -> Vec<SupplierRoute> {
    [(1, 2, 1), (2, 3, 2)]
        .into_iter()
        .map(|(supplier, buyer, commodity)| SupplierRoute {
            buyer_site_id: site(buyer),
            supplier_site_id: site(supplier),
            good_id: good(commodity),
            unit_id: units(),
            route_id: route(supplier),
            transport_kind: SupplierTransport::Staged,
        })
        .collect()
}

fn route_stages() -> Vec<RouteStage> {
    [(1, 2), (2, 3)]
        .into_iter()
        .map(|(source, destination)| RouteStage {
            route_id: route(source),
            stage_index: 0,
            from_node_id: node(source),
            to_node_id: node(destination),
            travel_periods: 1,
            loss_ppm: 0,
        })
        .collect()
}

fn route_stage_capacities() -> Vec<RouteStageCapacity> {
    [1, 2]
        .into_iter()
        .map(|id| RouteStageCapacity {
            route_id: route(id),
            stage_index: 0,
            corridor_id: corridor(id),
        })
        .collect()
}

pub(crate) fn opening() -> MaterialCircuitState {
    let recurring = recurring();
    MaterialCircuitState {
        capacity_supply: babylon_material_circuit::CapacitySupply::FiniteSchedule,
        period: 1,
        accounting: accounting(recurring),
        site_logistics_nodes: [1, 2, 3]
            .into_iter()
            .map(|owner| SiteLogisticsNode {
                site_id: site(owner),
                node_id: node(owner),
            })
            .collect(),
        process_outputs: process_outputs(),
        input_coefficients: input_coefficients(),
        labor_coefficients: labor_coefficients(),
        service_connections: vec![],
        service_orders: vec![],
        commodities: [0, 1, 2]
            .into_iter()
            .map(|commodity| CommodityDefinition {
                good_id: good(commodity),
                unit_id: units(),
                kind: babylon_material_circuit::CommodityKind::Storable {
                    grams_per_unit: 1_000,
                },
            })
            .collect(),
        supplier_routes: supplier_routes(),
        route_stages: route_stages(),
        route_stage_capacities: route_stage_capacities(),
        inventory: vec![inventory(1, 0, 40), inventory(2, 1, 4), inventory(3, 2, 4)],
        orders: vec![],
        backlog: vec![],
        freight: vec![],
        corridor_capacities: (1..=9)
            .flat_map(|period| {
                [1, 2, 3].into_iter().map(move |id| CorridorCapacity {
                    corridor_id: corridor(id),
                    period,
                    available_grams: 4_000,
                })
            })
            .collect(),
        capacities: (1..=9)
            .flat_map(|period| {
                [1, 2].into_iter().map(move |owner| CapacityRow {
                    process_id: process(owner),
                    site_id: site(owner),
                    period,
                    available_batches: 4,
                })
            })
            .collect(),
        labor: (1..=9)
            .flat_map(|period| {
                [(1, 4), (2, 8), (3, 4)]
                    .into_iter()
                    .map(move |(owner, available)| LaborCapacityRow {
                        site_id: site(owner),
                        unit_id: hours(),
                        period,
                        available,
                    })
            })
            .collect(),
        production_commitments: [1, 2]
            .into_iter()
            .map(|owner| ProductionCommitment {
                process_id: process(owner),
                site_id: site(owner),
                period: 1,
                planned_batches: 4,
            })
            .collect(),
        merchants: vec![MerchantHandling {
            site_id: site(3),
            location: "county:26163".parse().unwrap(),
            role: MerchantRole::Retail,
            capacity_id: corridor(3),
            labor_unit_id: hours(),
        }],
        handling_coefficients: vec![MerchantHandlingCoefficient {
            site_id: site(3),
            good_id: good(2),
            unit_id: units(),
            hours_per_unit: 1,
        }],
        final_demand_principals: vec![FinalDemandPrincipal {
            id: household(),
            location: "county:26163".parse().unwrap(),
        }],
        final_demand_orders: vec![],
        maintenance_binding: None,
        maintenance_service: None,
    }
}

pub(crate) fn recipient() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([76; 32])
}
fn aid_opening(routed: bool) -> MaterialCircuitState {
    let mut state = opening();
    state.final_demand_principals.push(FinalDemandPrincipal {
        id: recipient(),
        location: state.final_demand_principals[0].location,
    });
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("monetary control");
    };
    let rows = economy.recurring.as_mut().unwrap();
    rows.household_purchases[0].enabled = false;
    rows.households.push(HouseholdCohort {
        principal_id: recipient(),
        kind: HouseholdKind::Ordinary,
        households: 1,
        persons: 1,
    });
    rows.household_stocks.push(HouseholdStock {
        principal_id: recipient(),
        good_id: good(2),
        unit_id: units(),
        quantity: 0,
    });
    rows.household_needs.push(HouseholdNeed {
        principal_id: recipient(),
        good_id: good(2),
        unit_id: units(),
        basis: HouseholdNeedBasis::Persons,
        units_per_basis: 1,
    });
    let mut recipient_purchase = rows.household_purchases[0].clone();
    recipient_purchase.principal_id = recipient();
    recipient_purchase.enabled = false;
    rows.household_purchases.push(recipient_purchase);
    let mut cash = economy.book.snapshot();
    cash.accounts.push(CashAccount {
        id: AccountId::Household(recipient()),
        cash: money(0),
    });
    economy.book = MonetaryBook::from_snapshot(cash).unwrap();
    let mut stocks = economy.costs.snapshot().stocks;
    stocks.push(StockCarryingValue {
        owner: AccountId::Household(recipient()),
        good_id: good(2),
        unit_id: units(),
        amount: money(0),
    });
    economy.costs =
        HistoricalCostBook::open(&economy.book, stocks, vec![], vec![], vec![]).unwrap();
    economy.household_time = HouseholdTimeAccounting::Modeled(
        HouseholdTimeBook::new(
            [household(), recipient()]
                .into_iter()
                .map(|principal_id| HouseholdTimePolicy {
                    principal_id,
                    labor_unit_id: hours(),
                    eligible_persons: if principal_id == household() { 4 } else { 1 },
                    hours_per_eligible_person: 8,
                    protected: HouseholdTimeCommitment {
                        basis: HouseholdNeedBasis::Households,
                        hours_per_basis: 2,
                    },
                    routine_provisioning: HouseholdTimeCommitment {
                        basis: HouseholdNeedBasis::Households,
                        hours_per_basis: 3,
                    },
                    unmet_burdens: vec![HouseholdUnmetTimeBurden {
                        good_id: good(2),
                        unit_id: units(),
                        hours_per_unmet_unit: 5,
                    }],
                })
                .collect(),
        )
        .unwrap(),
    );
    economy.aid = AidBook {
        mandates: vec![mandate(routed)],
        freight: vec![],
    };
    state
}
fn mandate(routed: bool) -> AidMandate {
    AidMandate {
        id: [91; 32],
        source_hash: [92; 32],
        donor_actor: 101,
        donor_contributor_id: 201,
        recipient_actor: 120,
        payer: AccountId::Household(household()),
        donor: household(),
        recipient: recipient(),
        good_id: good(2),
        unit_id: units(),
        labor_unit_id: hours(),
        hours_per_unit: 2,
        maximum_quantity: 2,
        cash_per_unit: money(3),
        transport: if routed {
            AidTransport::Routed {
                route_id: route(2),
                from_node_id: node(2),
                to_node_id: node(3),
            }
        } else {
            AidTransport::Local
        },
    }
}

pub(crate) fn config() -> OrganizerConfig {
    OrganizerConfig {
        schema_version: ORGANIZER_SCHEMA_VERSION,
        collection: None,
        campaign_id: [1; 16],
        controlled_actor_id: 101,
        input_authority_id: [2; 16],
        organization_label: "Fixture organizing collective".into(),
        workplace_id: 104,
        workplace_process_id: process(1).as_bytes(),
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
        participants: [(201, 101, 16), (202, 102, 8), (203, 103, 8), (204, 120, 8)]
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
        time_binding: OrganizerTimeBindingMode::Household {
            bindings: [
                (201, household()),
                (202, household()),
                (203, household()),
                (204, recipient()),
            ]
            .into_iter()
            .map(|(contributor_id, principal)| OrganizerHouseholdBinding {
                contributor_id,
                principal_id: principal.as_bytes(),
            })
            .collect(),
        },
        aid_bindings: vec![OrganizerAidBinding {
            kind: OrganizerAidKind::Local,
            mandate_id: [91; 32],
            source_hash: [92; 32],
            donor_contributor_id: 201,
            recipient_contributor_id: 204,
            donor_principal_id: household().as_bytes(),
            recipient_principal_id: recipient().as_bytes(),
            social_class_target: [97; 32],
            receiving_consent: OrganizerGiftConsent::Accept,
            partner: OrganizerPartner {
                actor_id: 120,
                authority_id: [20; 16],
                label: "Independent recipient".into(),
                policy: OrganizerPartnerPolicy::Participate,
                permits_work_report: false,
                permits_maintenance_report: false,
            },
            coordination_hours: 3,
        }],
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
            (
                1,
                "consumers",
                1,
                StaffingWorkSource::Production(process(1)),
            ),
            (
                2,
                "maintainers",
                2,
                StaffingWorkSource::Production(process(2)),
            ),
            (
                3,
                "merchants",
                1,
                StaffingWorkSource::MerchantHandling(site(3)),
            ),
        ]
        .into_iter()
        .map(|(id, name, persons, source)| {
            StaffingNodeBinding::try_new(
                StableElementKey::Node {
                    scenario: "organizer/replay".into(),
                    local_name: format!("{name}-workplace"),
                },
                StaffingPoolBinding::try_new(
                    StaffingPoolId::from_bytes([id; 32]),
                    site(id),
                    hours(),
                    persons,
                    StaffingPolicy::one_period(4).unwrap(),
                    vec![source],
                )
                .unwrap(),
                vec![
                    babylon_tick::material_staffing::StaffingMemberNodeBinding::try_new(
                        StableElementKey::Node {
                            scenario: "organizer/replay".into(),
                            local_name: name.into(),
                        },
                        StaffingMemberBinding::try_new(
                            StaffingMemberId::from_bytes([id; 32]),
                            household(),
                            "county:26163".parse().unwrap(),
                            persons,
                        )
                        .unwrap(),
                    )
                    .unwrap(),
                ],
            )
            .unwrap()
        })
        .collect(),
    )
    .unwrap()
}
pub(crate) fn try_session(
    foundation: &MichiganDynamicHexFoundation,
    rules: &str,
    material: MaterialCircuitState,
    organizer: OrganizerConfig,
) -> Result<Session, MaterialReplayError> {
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
    let config = organizer;
    let state = initial_organizer_state(&config).unwrap();
    let material = MaterialWorldRegister::try_new(0, material)
        .unwrap()
        .with_organizer(config, state)
        .unwrap();
    MaterialReplaySession::new(
        graph,
        material,
        sha256_of(b"organizer-replay-fixture-foundation"),
        babylon_kernel::clock::CampaignDuration::Finite { final_period: 8 },
        staffing(),
    )
}

pub(crate) fn commitment(session: &Session, choice: OrganizerChoice) -> OrganizerCommitment {
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

pub(crate) fn prepare(session: &Session, accepted: Option<&OrganizerCommitment>) -> Candidate {
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

pub(crate) fn commit(session: &mut Session, sink: &mut CollectingSink, candidate: Candidate) {
    session
        .commit_prepared_and_publish(sink, candidate, |_| {
            Ok::<_, &'static str>(ReplayCommitDisposition::Committed)
        })
        .unwrap();
}

pub(crate) fn authored_session(
    foundation: &MichiganDynamicHexFoundation,
    organizer: OrganizerConfig,
    no_time: bool,
    routed: bool,
) -> Session {
    authored_session_with_loss(foundation, organizer, no_time, routed, 0)
}
pub(crate) fn authored_session_with_loss(
    foundation: &MichiganDynamicHexFoundation,
    organizer: OrganizerConfig,
    no_time: bool,
    routed: bool,
    loss_ppm: u32,
) -> Session {
    let mut state = aid_opening(routed);
    assert!(loss_ppm <= 1_000_000);
    if routed {
        state
            .route_stages
            .iter_mut()
            .find(|stage| stage.route_id == route(2))
            .unwrap()
            .loss_ppm = loss_ppm;
    } else {
        assert_eq!(loss_ppm, 0);
    }
    // Authored conserved opening allocation, then an actual mutual-aid contribution.
    let location = state.final_demand_principals[0].location;
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    let total = economy.book.total_cash_and_reserves().unwrap();
    let payer = AccountId::Organization(OrganizationAccountId::from_bytes([96; 32]));
    let mut snapshot = economy.book.snapshot();
    snapshot
        .accounts
        .iter_mut()
        .find(|a| a.id == AccountId::Site(site(2)))
        .unwrap()
        .cash = money(8);
    snapshot
        .accounts
        .iter_mut()
        .find(|a| a.id == AccountId::Site(site(3)))
        .unwrap()
        .cash = money(6);
    snapshot
        .accounts
        .iter_mut()
        .find(|a| a.id == AccountId::Household(household()))
        .unwrap()
        .cash = money(6);
    snapshot.accounts.push(CashAccount {
        id: payer,
        cash: money(0),
    });
    economy.book = MonetaryBook::from_snapshot(snapshot).unwrap();
    economy
        .book
        .transfer_cash(
            AccountId::Household(household()),
            payer,
            money(6),
            CashTransferPurpose::MutualAid,
        )
        .unwrap();
    economy.aid.mandates[0].payer = payer;
    economy.financial.locations.push(InstitutionLocation {
        account: payer,
        location,
    });
    economy.costs = HistoricalCostBook::open(
        &economy.book,
        economy.costs.snapshot().stocks,
        vec![],
        vec![],
        vec![],
    )
    .unwrap();
    assert_eq!(economy.book.total_cash_and_reserves().unwrap(), total);
    if routed {
        let HouseholdTimeAccounting::Modeled(book) = &mut economy.household_time else {
            unreachable!()
        };
        for policy in &mut book.policies {
            policy.hours_per_eligible_person = 12;
        }
    }
    if no_time {
        let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
            unreachable!()
        };
        let HouseholdTimeAccounting::Modeled(book) = &mut economy.household_time else {
            unreachable!()
        };
        book.policies[0].hours_per_eligible_person = 4;
    }
    try_session(
        foundation,
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        state,
        organizer,
    )
    .unwrap()
}
