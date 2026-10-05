//! Finite Designed implementation of the retained PER-345 paper control.
//!
//! The paper selects 12 people (8 donor, 4 recipient), 58,576 currency,
//! 44 food parcels and 20 material bundles. Its omitted supplier workforce is
//! supplied explicitly: five WorkingOwner persons in five households, 20 food
//! parcels at zero opening carrying cost, zero extra cash, and finite service
//! production and retail hours. Selected and supplementary stocks stay distinct.
//! Attendance is an authored component input, excluding endogenous turnover as
//! the paper does: the employer requests 640 hours even after its cash is gone.
//! The engine alone decides funded attendance, payroll, purchases, performance,
//! gifts, consumption, taxes and collection. The employer has a dormant process
//! with zero finite capacity and no output or sales: its four workforce persons
//! have a captured 160-hour attendance allowance each. No stock or receipt is
//! replenished. Every supplementary supplier control here is Designed.
use babylon_kernel::{content_digest::sha256_of, currency::Currency};
use babylon_material_circuit::*;

pub const PAPER_CASH: i128 = 58_576_000_000;
pub const COLLECTION: i128 = 400_000;
pub const FOOD: u8 = 2;
pub const MATERIALS: u8 = 1;
pub const EMPLOYER: u8 = 1;
pub const RETAILER: u8 = 2;
const PERIODS: std::ops::RangeInclusive<u64> = 1..=5;

pub fn money(micros: i128) -> Currency {
    Currency::from_micro_units(micros)
}
pub fn site(id: u8) -> SiteId {
    SiteId::from_bytes([id; 32])
}
pub fn good(id: u8) -> GoodId {
    GoodId::from_bytes([id; 32])
}
pub fn unit(id: u8) -> UnitId {
    UnitId::from_bytes([id; 32])
}
fn process(id: u8) -> ProcessId {
    ProcessId::from_bytes([id; 32])
}
pub fn principal(id: u8) -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([id; 32])
}
pub fn donor() -> FinalDemandPrincipalId {
    principal(1)
}
pub fn recipient() -> FinalDemandPrincipalId {
    principal(2)
}
pub fn suppliers() -> FinalDemandPrincipalId {
    principal(3)
}
pub fn organization() -> AccountId {
    AccountId::Organization(OrganizationAccountId::from_bytes([96; 32]))
}
pub fn public() -> AccountId {
    AccountId::Public(PublicAccountId::from_bytes([97; 32]))
}
fn hours() -> UnitId {
    unit(90)
}
fn capacity(g: u8) -> u64 {
    if g == EMPLOYER {
        0
    } else if g == 5 {
        4
    } else {
        8
    }
}
fn process_roster() -> impl Iterator<Item = u8> {
    std::iter::once(EMPLOYER).chain(3..=6)
}
fn price(g: u8) -> i128 {
    match g {
        1 => 120_000_000,
        2 => 280_000_000,
        3 => 75_000_000,
        4 => 1_000_000,
        5 => 1_450_000_000,
        6 => 600_000_000,
        _ => unreachable!(),
    }
}
fn supplier(g: u8) -> SiteId {
    if g <= 2 {
        site(RETAILER)
    } else {
        site(g)
    }
}
pub fn economy(state: &MaterialCircuitState) -> &MonetaryCircuit {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        panic!("monetary control")
    };
    e
}
fn economy_mut(state: &mut MaterialCircuitState) -> &mut MonetaryCircuit {
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!("monetary control")
    };
    e
}

fn recurring() -> RecurringEconomy {
    let households = [(donor(), 4, 8), (recipient(), 4, 4), (suppliers(), 5, 5)]
        .into_iter()
        .map(|(principal_id, households, persons)| HouseholdCohort {
            kind: HouseholdKind::Ordinary,
            principal_id,
            households,
            persons,
        })
        .collect();
    let stocks = [
        (donor(), MATERIALS, 4),
        (donor(), FOOD, 8),
        (recipient(), FOOD, 0),
        (suppliers(), FOOD, 20),
    ]
    .into_iter()
    .map(|(principal_id, g, quantity)| HouseholdStock {
        principal_id,
        good_id: good(g),
        unit_id: unit(g),
        quantity,
    })
    .collect();
    let needs = (1..=6)
        .map(|g| HouseholdNeed {
            principal_id: donor(),
            good_id: good(g),
            unit_id: unit(g),
            basis: if g == 1 || g == 5 {
                HouseholdNeedBasis::Households
            } else {
                HouseholdNeedBasis::Persons
            },
            units_per_basis: 1,
        })
        .chain(
            [recipient(), suppliers()].map(|principal_id| HouseholdNeed {
                principal_id,
                good_id: good(FOOD),
                unit_id: unit(FOOD),
                basis: HouseholdNeedBasis::Persons,
                units_per_basis: 1,
            }),
        )
        .collect();
    let purchases = (1..=6)
        .map(|g| HouseholdPurchasePolicy {
            principal_id: donor(),
            retailer_site_id: supplier(g),
            good_id: good(g),
            unit_id: unit(g),
            target_closing_stock: if g == MATERIALS {
                4
            } else if g == FOOD {
                8
            } else {
                0
            },
            maximum_purchase: if g == MATERIALS || g == 5 { 8 } else { 16 },
            enabled: true,
        })
        .chain(
            [recipient(), suppliers()].map(|principal_id| HouseholdPurchasePolicy {
                principal_id,
                retailer_site_id: site(RETAILER),
                good_id: good(FOOD),
                unit_id: unit(FOOD),
                target_closing_stock: 0,
                maximum_purchase: 8,
                enabled: false,
            }),
        )
        .collect();
    RecurringEconomy {
        service_inputs: vec![],
        households,
        household_stocks: stocks,
        household_needs: needs,
        household_purchases: purchases,
        offers: (1..=6)
            .map(|g| SellerOffer {
                site_id: supplier(g),
                good_id: good(g),
                unit_id: unit(g),
                unit_price: money(price(g)),
                pricing: PricePolicy::Fixed,
            })
            .collect(),
        replenishment: vec![],
        production: process_roster()
            .map(|g| ProductionDemandPolicy {
                process_id: process(g),
                site_id: site(g),
                output_buffer: 0,
                planned_batches: capacity(g),
            })
            .collect(),
        attendance: attendance(1),
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    }
}
fn attendance(period: u64) -> Vec<AttendancePlan> {
    (1..=6)
        .map(|g| AttendancePlan {
            site_id: site(g),
            unit_id: hours(),
            period,
            planned_hours: if g == EMPLOYER {
                640
            } else if g == RETAILER {
                16
            } else {
                capacity(g)
            },
        })
        .collect()
}
fn labor(period: u64) -> Vec<LaborCapacityRow> {
    attendance(period)
        .into_iter()
        .map(|r| LaborCapacityRow {
            site_id: r.site_id,
            unit_id: r.unit_id,
            period,
            available: r.planned_hours,
        })
        .collect()
}
fn members(period: u64) -> Vec<MemberLaborCapacityRow> {
    labor(period)
        .into_iter()
        .map(|r| MemberLaborCapacityRow {
            member_id: StaffingMemberId::from_bytes(r.site_id.as_bytes()),
            period,
            available_hours: r.available,
        })
        .collect()
}
fn production(period: u64) -> Vec<ProductionCommitment> {
    (3..=6)
        .map(|g| ProductionCommitment {
            process_id: process(g),
            site_id: site(g),
            period,
            planned_batches: capacity(g),
        })
        .collect()
}
fn time() -> HouseholdTimeAccounting {
    HouseholdTimeAccounting::Modeled(
        HouseholdTimeBook::new(
            [(donor(), 8), (recipient(), 4), (suppliers(), 5)]
                .into_iter()
                .map(|(principal_id, eligible_persons)| HouseholdTimePolicy {
                    principal_id,
                    labor_unit_id: hours(),
                    eligible_persons,
                    hours_per_eligible_person: 224,
                    protected: HouseholdTimeCommitment {
                        basis: HouseholdNeedBasis::Households,
                        hours_per_basis: 32,
                    },
                    routine_provisioning: HouseholdTimeCommitment {
                        basis: HouseholdNeedBasis::Households,
                        hours_per_basis: 64,
                    },
                    unmet_burdens: if principal_id == suppliers() {
                        vec![]
                    } else {
                        vec![HouseholdUnmetTimeBurden {
                            good_id: good(FOOD),
                            unit_id: unit(FOOD),
                            hours_per_unmet_unit: 20,
                        }]
                    },
                })
                .collect(),
        )
        .unwrap(),
    )
}
pub fn opening() -> MaterialCircuitState {
    let location = "county:26163".parse().unwrap();
    let inventory = [(MATERIALS, 16), (FOOD, 36)]
        .map(|(g, quantity)| InventoryRow {
            site_id: site(RETAILER),
            good_id: good(g),
            unit_id: unit(g),
            quantity,
        })
        .to_vec();
    let book = MonetaryBook::open(
        (1..=6)
            .map(|id| CashAccount {
                id: AccountId::Site(site(id)),
                cash: money(if id == EMPLOYER { 30_720_000_000 } else { 0 }),
            })
            .chain(
                [
                    (AccountId::Household(donor()), 27_856_000_000),
                    (AccountId::Household(recipient()), 0),
                    (AccountId::Household(suppliers()), 0),
                    (organization(), 0),
                    (public(), 0),
                ]
                .map(|(id, m)| CashAccount { id, cash: money(m) }),
            )
            .collect(),
    )
    .unwrap();
    let stocks = inventory
        .iter()
        .map(|r| StockCarryingValue {
            owner: AccountId::Site(r.site_id),
            good_id: r.good_id,
            unit_id: r.unit_id,
            amount: money(0),
        })
        .chain(
            [
                (donor(), MATERIALS, 480_000_000),
                (donor(), FOOD, 2_240_000_000),
                (recipient(), FOOD, 0),
                (suppliers(), FOOD, 0),
            ]
            .map(|(p, g, c)| StockCarryingValue {
                owner: AccountId::Household(p),
                good_id: good(g),
                unit_id: unit(g),
                amount: money(c),
            }),
        )
        .collect();
    let costs = HistoricalCostBook::open(&book, stocks, vec![], vec![], vec![]).unwrap();
    let financial = FinancialInstitutions {
        locations: [organization(), public()]
            .map(|account| InstitutionLocation { account, location })
            .to_vec(),
        taxes: vec![TaxPolicy {
            payer: AccountId::Household(donor()),
            public_recipient: PublicAccountId::from_bytes([97; 32]),
            basis: TaxBasis::WageIncome,
            rate_bps: 1500,
            cash_floor: money(0),
        }],
        ..FinancialInstitutions::empty()
    };
    MaterialCircuitState {
        capacity_supply: CapacitySupply::FiniteSchedule,
        period: 1,
        accounting: CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
            book,
            costs,
            financial,
            recurring: Some(Box::new(recurring())),
            household_time: time(),
            aid: AidBook {
                mandates: vec![AidMandate {
                    id: [91; 32],
                    source_hash: [92; 32],
                    donor_actor: 101,
                    donor_contributor_id: 201,
                    recipient_actor: 120,
                    payer: organization(),
                    donor: donor(),
                    recipient: recipient(),
                    good_id: good(FOOD),
                    unit_id: unit(FOOD),
                    labor_unit_id: hours(),
                    hours_per_unit: 2,
                    maximum_quantity: 4,
                    cash_per_unit: money(100_000),
                    transport: AidTransport::Local,
                }],
                freight: vec![],
            },
            employment: (1..=6)
                .map(|id| EmploymentTerms {
                    member_id: StaffingMemberId::from_bytes(site(id).as_bytes()),
                    site_id: site(id),
                    unit_id: hours(),
                    payee: if id == EMPLOYER { donor() } else { suppliers() },
                    compensation: if id == EMPLOYER {
                        LaborCompensation::Wage(money(24_000_000))
                    } else {
                        LaborCompensation::WorkingOwner
                    },
                })
                .collect(),
            member_labor: PERIODS.flat_map(members).collect(),
        })),
        commodities: (1..=7)
            .map(|g| CommodityDefinition {
                good_id: good(g),
                unit_id: unit(g),
                kind: if g <= 2 || g == 7 {
                    CommodityKind::Storable {
                        grams_per_unit: if g == FOOD { 14_000 } else { 1_000 },
                    }
                } else {
                    CommodityKind::PeriodService {
                        stage: if g == 3 {
                            ServiceStage::UtilityProvision
                        } else {
                            ServiceStage::LocalServiceProvision
                        },
                    }
                },
            })
            .collect(),
        site_logistics_nodes: (1..=6)
            .map(|id| SiteLogisticsNode {
                site_id: site(id),
                node_id: LogisticsNodeId::from_bytes([id; 32]),
            })
            .collect(),
        process_outputs: process_roster()
            .map(|g| ProcessOutput {
                process_id: process(g),
                site_id: site(g),
                good_id: good(if g == EMPLOYER { 7 } else { g }),
                unit_id: unit(if g == EMPLOYER { 7 } else { g }),
                quantity_per_batch: 1,
            })
            .collect(),
        input_coefficients: vec![],
        labor_coefficients: process_roster()
            .map(|g| LaborCoefficient {
                process_id: process(g),
                unit_id: hours(),
                quantity_per_batch: 1,
            })
            .collect(),
        capacities: PERIODS
            .flat_map(|period| {
                process_roster().map(move |g| CapacityRow {
                    process_id: process(g),
                    site_id: site(g),
                    period,
                    available_batches: capacity(g),
                })
            })
            .collect(),
        labor: PERIODS.flat_map(labor).collect(),
        production_commitments: production(1),
        inventory,
        service_connections: (3..=6)
            .map(|g| ServiceConnection {
                provider_site_id: site(g),
                buyer: AccountId::Household(donor()),
                good_id: good(g),
                unit_id: unit(g),
            })
            .collect(),
        service_orders: vec![],
        supplier_routes: vec![],
        route_stages: vec![],
        route_stage_capacities: vec![],
        orders: vec![],
        backlog: vec![],
        freight: vec![],
        corridor_capacities: PERIODS
            .map(|period| CorridorCapacity {
                corridor_id: CorridorId::from_bytes([2; 32]),
                period,
                available_grams: 300_000,
            })
            .collect(),
        merchants: vec![MerchantHandling {
            site_id: site(RETAILER),
            location,
            role: MerchantRole::Retail,
            capacity_id: CorridorId::from_bytes([2; 32]),
            labor_unit_id: hours(),
        }],
        handling_coefficients: [MATERIALS, FOOD]
            .map(|g| MerchantHandlingCoefficient {
                site_id: site(RETAILER),
                good_id: good(g),
                unit_id: unit(g),
                hours_per_unit: 1,
            })
            .to_vec(),
        final_demand_principals: [donor(), recipient(), suppliers()]
            .map(|id| FinalDemandPrincipal { id, location })
            .to_vec(),
        final_demand_orders: vec![],
        maintenance_binding: None,
        maintenance_service: None,
    }
}

/// Install only the next selected exogenous component plans; no authoritative
/// cash, inventory, receipt, time, fiscal or reproduction result changes here.
pub fn controlled_opening(mut state: MaterialCircuitState) -> MaterialCircuitState {
    let period = state.period;
    economy_mut(&mut state)
        .recurring
        .as_mut()
        .unwrap()
        .attendance = attendance(period);
    state.production_commitments = production(period);
    state
}
pub fn collection(period: u64) -> CollectionResolveInput {
    CollectionResolveInput {
        original_commitment_id: sha256_of(&period.to_be_bytes()),
        command_nonce: [u8::try_from(period).unwrap(); 16],
        admitted_period: period - 1,
        resolve_period: period,
        mandate_id: [93; 32],
        source_hash: [94; 32],
        actor_id: 101,
        contributor_id: 201,
        donor: donor(),
        recipient: OrganizationAccountId::from_bytes([96; 32]),
        labor_unit_id: hours(),
        cash_consent: true,
        requested: money(COLLECTION),
        protected_cash_floor: money(0),
        collection_hours: 2,
        pledged_hours: 2,
    }
}
pub fn aid(period: u64) -> AidResolveInput {
    AidResolveInput {
        mandate_id: [91; 32],
        source_hash: [92; 32],
        admitted_period: period - 1,
        donor_actor: 101,
        recipient_actor: 120,
        quantity: 4,
    }
}
pub fn close(
    state: &MaterialCircuitState,
    aid: &[AidResolveInput],
    collection: &[CollectionResolveInput],
) -> Result<MaterialCircuitTransition, MaterialCircuitError> {
    let period = state.period + 1;
    close_material_period_with_support(state, aid, collection)?
        .finish_with_workforce(labor(period), members(period))
}
pub fn coordinate(transition: &mut MaterialCircuitTransition) {
    assert_eq!(transition.state.period, 3);
    assert!(transition
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::Granted && r.quantity == 4));
    assert!(transition
        .household_consumption
        .iter()
        .any(|r| r.principal_id == recipient()
            && r.good_id == good(FOOD)
            && r.consumed_quantity == 4));
    // Supplied separate Designed Participate authority; neither receipt of food
    // nor the donor's accepted gift grants this independent partner practice.
    // This public finite-time debit proves accounting only. Real organizer
    // admission and consent refusals belong to the MaterialReplaySession controls.
    let uses = [(donor(), 101_u64, 201_u64), (recipient(), 120_u64, 204_u64)].map(
        |(principal_id, actor_id, contributor_id)| HouseholdContributionUse {
            use_id: sha256_of(&contributor_id.to_be_bytes()),
            principal_id,
            actor_id,
            contributor_id,
            hours: 2,
        },
    );
    consume_household_contributions(&mut transition.state, 2, &uses).unwrap();
    let bytes = encode_material_circuit_state(&transition.state).unwrap();
    consume_household_contributions(&mut transition.state, 2, &uses).unwrap();
    assert_eq!(
        encode_material_circuit_state(&transition.state).unwrap(),
        bytes
    );
}
pub fn cash(state: &MaterialCircuitState, account: AccountId) -> i128 {
    economy(state).book.cash(account).unwrap().micro_units()
}
pub fn stock(state: &MaterialCircuitState, principal: FinalDemandPrincipalId, g: u8) -> u64 {
    economy(state)
        .recurring
        .as_ref()
        .unwrap()
        .household_stocks
        .iter()
        .find(|r| r.principal_id == principal && r.good_id == good(g))
        .unwrap()
        .quantity
}
pub fn remaining(state: &MaterialCircuitState, principal: FinalDemandPrincipalId) -> u64 {
    let HouseholdTimeAccounting::Modeled(time) = &economy(state).household_time else {
        panic!("actual time")
    };
    let available = time
        .receipts
        .iter()
        .find(|r| r.principal_id == principal)
        .unwrap()
        .contribution_available_hours;
    available
        - time
            .contributions
            .iter()
            .filter(|r| r.contribution.principal_id == principal)
            .map(|r| r.contribution.hours)
            .sum::<u64>()
}
