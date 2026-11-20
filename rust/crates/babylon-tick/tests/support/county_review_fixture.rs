//! A hand-built staffed county for the county review's replay tests.
//!
//! It is the aid fixture's real material and organizer world with a county on top: wage earners
//! whose wages the engine pays and taxes, job-seeking households that hold the county's relief
//! units, a public account with one grant and the households' support lines, and the organizer's
//! review contact. Every number the county reads is made by the engine's own close.
//!
//! Group A (`household()`) has four households. Its employer sites pay a $24 wage: one person at
//! the first site and two at the second. Group B (`recipient()`) has three households and three
//! job-seekers, so its roll holds three units. Both are ordinary budget groups of the county.

use babylon_bsl::canonical_ast;
use babylon_bsl::rule_pipeline;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::content_digest;
use babylon_kernel::content_digest::ContentDigest;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_kernel::tick_content_hash::RefDigest;
use babylon_material_circuit::{
    AccountId, CashAccount, CircuitAccounting, FinalDemandPrincipalId, HistoricalCostBook,
    InstitutionLocation, LaborCompensation, MaterialCatalog, MonetaryBook, MonetaryCircuit,
    ProcessId, PublicAccountId, PublicAllocation, PublicBudget, PublicTransferTreatment, SiteId,
    StaffingMemberBinding, StaffingMemberId, StaffingPolicy, StaffingPoolBinding, StaffingPoolId,
    StaffingWorkSource, TaxBasis, TaxPolicy, UnitId,
};
use babylon_practice_contract::{
    CountyReviewConfig, CountyReviewCrew, CountyReviewGroup, CountyReviewState, GroupKind,
    OpeningCrew, OrganizerConfig, OrganizerPeriodJournal, OrganizerReviewConfig, PayMode,
    COUNTY_REVIEW_SCHEMA_VERSION,
};
use babylon_tick::h3_runtime::MichiganDynamicHexFoundation;
use babylon_tick::material_replay::{MaterialReplayError, MaterialReplaySession};
use babylon_tick::material_staffing::{
    StaffingComposition, StaffingMemberNodeBinding, StaffingNodeBinding,
};
use babylon_tick::material_state::MaterialState;
use babylon_tick::material_world::{CountyReviewRegister, MaterialWorldRegister};
use babylon_tick::replay_session::ReplayTickSession;

use crate::organizer_aid_fixture::{self, Materials, Session};

/// One unit of relief: $280.
pub(crate) const UNIT_MICROS: i128 = 280_000_000;
/// The county's grant to the first workplace.
pub(crate) const GRANT_MICROS: i128 = 1_000_000_000;
/// The county's spending limit.
pub(crate) const CAP_MICROS: i128 = 5_000_000_000;
/// The wage the engine pays at the employer sites: $24 an hour.
pub(crate) const WAGE_MICROS: i128 = 24_000_000;
/// The county's actor, which charges its session's hours.
pub(crate) const COUNTY_ACTOR: u64 = 130;

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
  (node merchants NodeType/SOCIAL_CLASS (social-class/employed-population 0) (social-class/reserve-population 3))
  (node merchants-workplace NodeType/BUSINESS (business/previous-unretained-labor-hours 0)))
";

/// The county's public account.
pub(crate) fn public_account() -> PublicAccountId {
    PublicAccountId::from_bytes([97; 32])
}

fn hours() -> UnitId {
    UnitId::from_bytes([2; 32])
}

fn process(id: u8) -> ProcessId {
    ProcessId::from_bytes([id; 32])
}

/// The wage households' principal, the first group of the county.
pub(crate) fn wage_group() -> FinalDemandPrincipalId {
    organizer_aid_fixture::household()
}

/// The job-seeking households' principal, the second group of the county.
pub(crate) fn seeking_group() -> FinalDemandPrincipalId {
    organizer_aid_fixture::recipient()
}

/// What a test may change in the world.
#[derive(Clone, Copy)]
pub(crate) struct Options {
    /// The first period with a session.
    pub(crate) first_session_period: u64,
    /// The county's cash at the opening.
    pub(crate) public_cash: i128,
    /// The county's spending limit.
    pub(crate) period_cap: i128,
    /// The wage tax rate, in basis points.
    pub(crate) tax_bps: u16,
}

impl Default for Options {
    fn default() -> Self {
        Self {
            first_session_period: 1,
            public_cash: 10_000_000_000,
            period_cap: CAP_MICROS,
            tax_bps: 1500,
        }
    }
}

/// The county's configuration: two ordinary groups and the three crews of the staffed world.
pub(crate) fn county_config(options: Options) -> CountyReviewConfig {
    let group = |principal: FinalDemandPrincipalId, label: &str, households, roll_units| {
        CountyReviewGroup {
            group_id: principal.as_bytes(),
            label: label.to_owned(),
            kind: GroupKind::Ordinary,
            opening_households: households,
            roll_units,
            has_ownership_income: false,
            receives_mutual_aid: false,
        }
    };
    let crew = |id: u8, group: u32, label: &str| CountyReviewCrew {
        crew_id: [id; 32],
        group,
        site_id: [id; 32],
        unit_id: hours().as_bytes(),
        workplace_label: label.to_owned(),
        pay_mode: PayMode::Wage,
    };
    CountyReviewConfig {
        schema_version: COUNTY_REVIEW_SCHEMA_VERSION,
        campaign_id: [1; 16],
        actor_id: COUNTY_ACTOR,
        authority_id: [8; 16],
        county: *b"26163",
        administration_label: "Fixture county administration".to_owned(),
        claimants_body_label: "Fixture claimants".to_owned(),
        aid_body_label: "Fixture aid partners".to_owned(),
        public_account_id: public_account().as_bytes(),
        unit_price_micros: UNIT_MICROS,
        going_wage_micros: WAGE_MICROS,
        session_hours: 2,
        bring_hours: 2,
        first_session_period: options.first_session_period,
        groups: vec![
            group(wage_group(), "Wage households", 4, 0),
            group(seeking_group(), "Job-seeking households", 3, 3),
        ],
        crews: vec![
            crew(1, 0, "Consumers' workplace"),
            crew(2, 0, "Maintainers' workplace"),
            crew(3, 1, "Merchants' workplace"),
        ],
        content_digest: [9; 32],
        policy_source_digest: [10; 32],
    }
}

/// The county's opening section.
pub(crate) fn county_register(options: Options) -> CountyReviewRegister {
    let config = county_config(options);
    let roster = babylon_practice_contract::opening_roster(
        &config,
        &[
            OpeningCrew {
                crew: 0,
                at_work: 1,
                seeking: 0,
            },
            OpeningCrew {
                crew: 1,
                at_work: 2,
                seeking: 0,
            },
            OpeningCrew {
                crew: 2,
                at_work: 0,
                seeking: 3,
            },
        ],
        &[],
    )
    .expect("the fixture's households place");
    CountyReviewRegister::try_new(
        config,
        CountyReviewState {
            schema_version: COUNTY_REVIEW_SCHEMA_VERSION,
            roster,
            last_facts: None,
            last_session: None,
        },
    )
    .expect("the opening state follows its configuration")
}

/// The organizer's configuration with the county review it may reach a household for.
pub(crate) fn organizer_config(options: Options) -> OrganizerConfig {
    let mut config = organizer_aid_fixture::config();
    config.review = Some(OrganizerReviewConfig {
        county_geoid: "26163".to_owned(),
        first_session_period: options.first_session_period,
        county_config_digest: babylon_practice_contract::county_review_config_digest(
            &county_config(options),
        )
        .expect("the fixture's configuration encodes"),
    });
    config
}

fn account_rows(
    economy: &mut babylon_material_circuit::MonetaryCircuit,
    change: impl FnOnce(&mut Vec<CashAccount>),
) {
    let mut snapshot = economy.book.snapshot();
    change(&mut snapshot.accounts);
    economy.book =
        MonetaryBook::from_snapshot(snapshot).expect("the snapshot admits the derived value");
    economy.costs = HistoricalCostBook::open(
        &economy.book,
        economy.costs.snapshot().stocks,
        vec![],
        vec![],
        vec![],
    )
    .expect("the fixture opens the authored source");
}

/// The county's public account with its cash, the wage tax on both groups, one grant and the
/// job-seekers' support line.
fn add_county_money(economy: &mut MonetaryCircuit, location: EconomicLocation, options: Options) {
    let public = AccountId::Public(public_account());
    account_rows(economy, |accounts| {
        for account in accounts.iter_mut() {
            if matches!(account.id, AccountId::Site(_)) {
                account.cash = organizer_aid_fixture::money(1_000_000_000);
            }
        }
        accounts.push(CashAccount {
            id: public,
            cash: organizer_aid_fixture::money(options.public_cash),
        });
    });
    economy.financial.locations.push(InstitutionLocation {
        account: public,
        location,
    });
    economy.financial.locations.sort_by_key(|row| row.account);
    economy.financial.taxes = [wage_group(), seeking_group()]
        .into_iter()
        .map(|principal| TaxPolicy {
            payer: AccountId::Household(principal),
            public_recipient: public_account(),
            basis: TaxBasis::WageIncome,
            rate_bps: options.tax_bps,
            cash_floor: organizer_aid_fixture::money(0),
        })
        .collect();
    economy.financial.public_budgets = vec![PublicBudget {
        public_account: public_account(),
        period_cap: organizer_aid_fixture::money(options.period_cap),
        cash_floor: organizer_aid_fixture::money(0),
    }];
    economy.financial.public_allocations = vec![
        PublicAllocation {
            public_account: public_account(),
            recipient: AccountId::Site(organizer_aid_fixture::site(1)),
            treatment: PublicTransferTreatment::ProviderOperatingGrant,
            priority: 0,
            amount_per_period: organizer_aid_fixture::money(GRANT_MICROS),
        },
        PublicAllocation {
            public_account: public_account(),
            recipient: AccountId::Household(seeking_group()),
            treatment: PublicTransferTreatment::HouseholdIncomeSupport,
            priority: 1,
            amount_per_period: organizer_aid_fixture::money(3 * UNIT_MICROS),
        },
    ];
}

/// The aid fixture's definitions and opening, made a staffed, taxed, paid county.
pub(crate) fn materials(options: Options) -> Materials {
    let Materials {
        mut catalog,
        mut state,
    } = organizer_aid_fixture::authored_materials(false, false, 0);
    let location = state.final_demand_principals[0].location;
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("the aid fixture is monetary");
    };
    let rows = economy
        .recurring
        .as_mut()
        .expect("the aid fixture has household cohorts");
    for cohort in &mut rows.households {
        let (households, persons) = if cohort.principal_id == wage_group() {
            (4, 8)
        } else {
            (3, 6)
        };
        cohort.households = households;
        cohort.persons = persons;
    }
    // The third site has nobody at work, so the job-seekers are its labor force alone.
    for plan in &mut rows.attendance {
        if plan.site_id == organizer_aid_fixture::site(3) {
            plan.planned_hours = 0;
        }
    }
    for row in &mut state.labor {
        if row.site_id == organizer_aid_fixture::site(3) {
            row.available = 0;
        }
    }
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("the aid fixture is monetary");
    };
    for row in &mut economy.member_labor {
        if row.member_id == StaffingMemberId::from_bytes([3; 32]) {
            row.available_hours = 0;
        }
    }
    for terms in &mut economy.employment {
        terms.compensation = LaborCompensation::Wage(Currency::from_micro_units(WAGE_MICROS));
        if terms.member_id == StaffingMemberId::from_bytes([3; 32]) {
            terms.payee = seeking_group();
        }
    }
    add_county_money(economy, location, options);
    for policy in &mut catalog.household_time_policy {
        policy.eligible_persons = if policy.principal_id == wage_group() {
            8
        } else {
            6
        };
        policy.hours_per_eligible_person = 40;
    }
    Materials { catalog, state }
}

fn staffing() -> StaffingComposition {
    StaffingComposition::try_new(
        [
            (1, "consumers", 1, Some(1), wage_group()),
            (2, "maintainers", 2, Some(2), wage_group()),
            (3, "merchants", 3, None, seeking_group()),
        ]
        .into_iter()
        .map(|(id, name, persons, production, household)| {
            let mut sources: Vec<_> = production
                .into_iter()
                .map(|process_id| StaffingWorkSource::Production(process(process_id)))
                .collect();
            if id == 3 {
                sources.push(StaffingWorkSource::MerchantHandling(
                    organizer_aid_fixture::site(3),
                ));
            }
            StaffingNodeBinding::try_new(
                StableElementKey::Node {
                    scenario: "organizer/replay".into(),
                    local_name: format!("{name}-workplace"),
                },
                StaffingPoolBinding::try_new(
                    StaffingPoolId::from_bytes([id; 32]),
                    SiteId::from_bytes([id; 32]),
                    hours(),
                    persons,
                    StaffingPolicy::one_period(4).expect("the one-period fixture advances"),
                    sources,
                )
                .expect("the authored fixture satisfies the constructor invariants"),
                vec![StaffingMemberNodeBinding::try_new(
                    StableElementKey::Node {
                        scenario: "organizer/replay".into(),
                        local_name: name.into(),
                    },
                    StaffingMemberBinding::try_new(
                        StaffingMemberId::from_bytes([id; 32]),
                        household,
                        "county:26163"
                            .parse()
                            .expect("the authored literal parses as the declared type"),
                        persons,
                    )
                    .expect("the authored fixture satisfies the constructor invariants"),
                )
                .expect("the authored fixture satisfies the constructor invariants")],
            )
            .expect("the authored fixture satisfies the constructor invariants")
        })
        .collect(),
    )
    .expect("the authored fixture satisfies the constructor invariants")
}

/// A session over the county world and the given rules, with or without the county's section.
pub(crate) fn try_session(
    foundation: &MichiganDynamicHexFoundation,
    rules: &str,
    options: Options,
    with_county: bool,
) -> Result<Session, MaterialReplayError> {
    let Materials {
        catalog,
        state: opening,
    } = materials(options);
    let catalog = MaterialCatalog::try_new(catalog)
        .expect("the authored definitions canonicalize before admission");
    let (_, parsed) =
        rule_pipeline::split_content(rules).expect("the authored content splits into its sections");
    let forms = parsed.into_iter().map(|rule| rule.form).collect::<Vec<_>>();
    let graph = ReplayTickSession::new(
        SCENARIO,
        None,
        rules,
        HypergraphStore::new(),
        ReplaySessionId::try_from("county/replay-session")
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
    let config = organizer_config(options);
    let state = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let mut material = MaterialWorldRegister::try_new(&catalog, 0, opening)
        .expect("the authored fixture satisfies the constructor invariants")
        .with_organizer(&catalog, config, state, OrganizerPeriodJournal::empty())
        .expect("the fixture builder accepts the authored options");
    if with_county {
        material = material
            .with_county_review(&catalog, county_register(options), None)
            .expect("the county fits the staffed world");
    }
    MaterialReplaySession::new(
        graph,
        material,
        catalog,
        content_digest::sha256_of(b"county-review-fixture-foundation"),
        babylon_kernel::clock::CampaignDuration::Finite { final_period: 8 },
        staffing(),
    )
}

/// The opening register built with the organizer first and the county second, and the other way
/// round, with the catalog they were admitted under.
pub(crate) fn registers_in_both_orders(
    options: Options,
) -> (
    MaterialCatalog,
    MaterialWorldRegister,
    MaterialWorldRegister,
) {
    let Materials { catalog, state } = materials(options);
    let catalog = MaterialCatalog::try_new(catalog)
        .expect("the authored definitions canonicalize before admission");
    let config = organizer_config(options);
    let organizer = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let bare = || {
        MaterialWorldRegister::try_new(&catalog, 0, state.clone())
            .expect("the authored fixture satisfies the constructor invariants")
    };
    let organizer_first = bare()
        .with_organizer(
            &catalog,
            config.clone(),
            organizer.clone(),
            OrganizerPeriodJournal::empty(),
        )
        .expect("the fixture builder accepts the authored options")
        .with_county_review(&catalog, county_register(options), None)
        .expect("the county fits the staffed world");
    let county_first = bare()
        .with_county_review(&catalog, county_register(options), None)
        .expect("the county fits the staffed world")
        .with_organizer(&catalog, config, organizer, OrganizerPeriodJournal::empty())
        .expect("the organizer binds after the county");
    (catalog, organizer_first, county_first)
}
