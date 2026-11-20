//! The county review's section of the register: its bytes, its checks against the world, the
//! facts of a close and the write-back, on the hand-built paid world `agency_control`.

use std::collections::HashMap;

use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::stable_element::StableElementResolver;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CashAccount, CircuitAccounting, CompanyConditionOrder, CompanyId,
    CompanyPayoutPolicy, CompanyPortfolioPolicy, DistributionPolicy, EquityCarryingValue,
    FinalDemandPrincipalId, HistoricalCostBook, HouseholdTimeAccounting, MaterialCatalog,
    MaterialCircuitState, MonetaryBook, OwnershipClaim, PublicAccountId, PublicAllocation,
    PublicBudget, PublicTransferTreatment,
};
use babylon_practice_contract::{
    Band, CountyPeriodFacts, CountyReviewConfig, CountyReviewCrew, CountyReviewError,
    CountyReviewGroup, CountyReviewState, GroupKind, OpeningCrew, OrganizerConfig,
    OrganizerContribution, OrganizerParticipant, OrganizerPartner, OrganizerPartnerPolicy,
    OrganizerPeriodJournal, OrganizerPeriodJournalEntries, OrganizerReviewConfig, OrganizerState,
    OrganizerTimeBindingMode, PayMode, PositionKey, SessionOutcome, COUNTY_REVIEW_SCHEMA_VERSION,
    ORGANIZER_SCHEMA_VERSION,
};

use super::county_review_execution;
use super::tests::agency_control;
use super::{
    CountyLaborFacts, CountyReviewRegister, CountyReviewRegisterError, MaterialWorldError,
    MaterialWorldRegister, PreparedMaterialWorld,
};

/// The unit of relief: $280.
const UNIT_MICROS: i128 = 280_000_000;
/// The county's grant to the workplace.
const GRANT_MICROS: i128 = 1_000_000_000;
const REGISTER_V7: &[u8] = b"babylon.material-world-register.v7\0";
const REGISTER_V9: &[u8] = b"babylon.material-world-register.v9\0";
const COUNTY_FRAME: &[u8] = b"babylon.material-world-register.county-review.v1\0";

fn public_account() -> PublicAccountId {
    PublicAccountId::from_bytes([97; 32])
}

fn money(micros: i128) -> Currency {
    agency_control::money(micros)
}

/// Two groups of the paid world: the donors, who work at the employer and have one job-seeker, and
/// the recipients, who have nobody in the labor force.
fn config(first_session_period: u64) -> CountyReviewConfig {
    let group = |principal: u8, label: &str, roll_units: u64| CountyReviewGroup {
        group_id: [principal; 32],
        label: label.to_owned(),
        kind: GroupKind::Ordinary,
        opening_households: 4,
        roll_units,
        has_ownership_income: false,
        receives_mutual_aid: false,
    };
    CountyReviewConfig {
        schema_version: COUNTY_REVIEW_SCHEMA_VERSION,
        campaign_id: [3; 16],
        actor_id: 900,
        authority_id: [4; 16],
        county: *b"26163",
        administration_label: "Fixture county administration".to_owned(),
        claimants_body_label: "Fixture claimants".to_owned(),
        aid_body_label: "Fixture aid partners".to_owned(),
        public_account_id: [97; 32],
        unit_price_micros: UNIT_MICROS,
        going_wage_micros: 24_000_000,
        session_hours: 2,
        bring_hours: 2,
        first_session_period,
        groups: vec![group(1, "Donors", 1), group(2, "Recipients", 0)],
        crews: vec![CountyReviewCrew {
            crew_id: [1; 32],
            group: 0,
            site_id: [1; 32],
            unit_id: [90; 32],
            workplace_label: "Employer".to_owned(),
            pay_mode: PayMode::Wage,
        }],
        content_digest: [5; 32],
        policy_source_digest: [6; 32],
    }
}

fn state_for(config: &CountyReviewConfig) -> CountyReviewState {
    CountyReviewState {
        schema_version: COUNTY_REVIEW_SCHEMA_VERSION,
        roster: babylon_practice_contract::opening_roster(
            config,
            &[OpeningCrew {
                crew: 0,
                at_work: 3,
                seeking: 1,
            }],
            &[],
        )
        .expect("the donors place over their households"),
        last_facts: None,
        last_session: None,
    }
}

fn county_with(config: CountyReviewConfig) -> CountyReviewRegister {
    let state = state_for(&config);
    CountyReviewRegister::try_new(config, state)
        .expect("the opening state follows its configuration")
}

fn county() -> CountyReviewRegister {
    county_with(config(4))
}

/// The paid world with a county budget: one grant and the donors' one unit of support.
fn world() -> (MaterialCatalog, MaterialCircuitState) {
    let (catalog, mut state) = agency_control::opening_with_cash(0, 10_000_000_000);
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("the paid world is monetary");
    };
    economy.financial.public_budgets = vec![PublicBudget {
        public_account: public_account(),
        period_cap: money(5_000_000_000),
        cash_floor: money(0),
    }];
    economy.financial.public_allocations = vec![
        PublicAllocation {
            public_account: public_account(),
            recipient: AccountId::Site(agency_control::site(agency_control::EMPLOYER)),
            treatment: PublicTransferTreatment::ProviderOperatingGrant,
            priority: 0,
            amount_per_period: money(GRANT_MICROS),
        },
        PublicAllocation {
            public_account: public_account(),
            recipient: AccountId::Household(agency_control::donor()),
            treatment: PublicTransferTreatment::HouseholdIncomeSupport,
            priority: 1,
            amount_per_period: money(UNIT_MICROS),
        },
    ];
    (catalog, state)
}

fn plain_register() -> (MaterialCatalog, MaterialWorldRegister) {
    let (catalog, state) = world();
    let register =
        MaterialWorldRegister::try_new(&catalog, 0, state).expect("the paid world opens");
    (catalog, register)
}

fn county_register(first_session_period: u64) -> (MaterialCatalog, MaterialWorldRegister) {
    let (catalog, register) = plain_register();
    let register = register
        .with_county_review(&catalog, county_with(config(first_session_period)), None)
        .expect("the county fits the paid world");
    (catalog, register)
}

fn resolver() -> StableElementResolver {
    StableElementResolver::seal(
        &HypergraphStore::new(),
        "county/fixture",
        &HashMap::new(),
        &HashMap::new(),
    )
    .expect("an empty topology seals")
}

fn refusal(error: MaterialWorldError) -> CountyReviewRegisterError {
    match error {
        MaterialWorldError::CountyReview(error) => error,
        other => panic!("expected a county refusal, found {other:?}"),
    }
}

fn bound(
    register: MaterialWorldRegister,
    catalog: &MaterialCatalog,
    config: CountyReviewConfig,
) -> Result<MaterialWorldRegister, CountyReviewRegisterError> {
    register
        .with_county_review(catalog, county_with(config), None)
        .map_err(refusal)
}

/// The facts of the closed period 1, read the way the rule reads them.
fn facts_of(
    prepared: &PreparedMaterialWorld,
    config: &CountyReviewConfig,
    labor: &CountyLaborFacts,
) -> CountyPeriodFacts {
    county_review_execution::period_facts(
        config,
        labor,
        prepared.register().state(),
        prepared.register().completed_tick(),
    )
    .expect("the closed period's facts")
}

/// The position of the donors' households at work.
fn at_work_key(state: &CountyReviewState) -> PositionKey {
    state
        .roster
        .rows
        .iter()
        .find(|row| row.key.at_work == 1)
        .expect("the donors have households at work")
        .key
}

#[test]
fn a_register_without_a_county_section_keeps_its_bytes() {
    let (catalog, register) = plain_register();
    let before = register.canonical_bytes().to_vec();
    let decoded = MaterialWorldRegister::decode_external(&catalog, before.clone())
        .expect("a version 7 register still decodes");
    assert_eq!(decoded.canonical_bytes(), before.as_slice());
    assert!(decoded.county_review().is_none());
    assert!(before.starts_with(REGISTER_V7));
}

#[test]
fn a_county_section_round_trips_and_changes_the_digest() {
    let (catalog, plain) = plain_register();
    let (_, with) = county_register(4);
    assert_ne!(with.digest(), plain.digest());
    assert!(with.canonical_bytes().starts_with(REGISTER_V9));
    assert_eq!(
        with.canonical_bytes()[REGISTER_V9.len()..REGISTER_V9.len() + 4],
        9_u32.to_be_bytes()
    );
    let decoded = MaterialWorldRegister::decode_external(&catalog, with.canonical_bytes().to_vec())
        .expect("a version 9 register decodes");
    let section = decoded.county_review().expect("the section is read back");
    assert_eq!(section.state(), county().state());
    assert_eq!(section.config(), county().config());
    assert_eq!(decoded.canonical_bytes(), with.canonical_bytes());
    assert_eq!(decoded.digest(), with.digest());
}

#[test]
fn a_roster_that_disagrees_with_the_cohorts_is_refused() {
    let (catalog, register) = plain_register();
    let mut config = config(4);
    config.groups[0].opening_households = 5;
    assert_eq!(
        bound(register, &catalog, config).expect_err("five households against a cohort of four"),
        CountyReviewRegisterError::Cohort
    );
}

#[test]
fn a_group_that_is_not_a_cohort_of_the_world_is_refused() {
    let (catalog, register) = plain_register();
    let mut config = config(4);
    config.groups[1].group_id = [77; 32];
    assert_eq!(
        bound(register, &catalog, config).expect_err("no cohort has that principal"),
        CountyReviewRegisterError::Cohort
    );
}

#[test]
fn a_crew_that_is_not_an_employment_row_of_its_group_is_refused() {
    let (catalog, register) = plain_register();
    let changes: [fn(&mut CountyReviewCrew); 4] = [
        |crew| crew.crew_id = [9; 32],
        |crew| crew.site_id = [9; 32],
        |crew| crew.unit_id = [9; 32],
        |crew| crew.pay_mode = PayMode::WorkingOwner,
    ];
    for change in changes {
        let mut config = config(4);
        change(&mut config.crews[0]);
        assert_eq!(
            bound(register.clone(), &catalog, config)
                .expect_err("the crew is not an employment row"),
            CountyReviewRegisterError::Employment
        );
    }
}

#[test]
fn a_crew_paid_to_another_group_is_refused() {
    let (catalog, register) = plain_register();
    // The recipients get the crew, but the employer pays the donors.
    let mut config = config(4);
    config.crews[0].group = 1;
    config.groups[0].roll_units = 0;
    config.groups[1].roll_units = 1;
    assert_eq!(
        bound(register, &catalog, config).expect_err("the employer pays the donors"),
        CountyReviewRegisterError::Employment
    );
}

#[test]
fn a_public_account_that_is_missing_or_unbudgeted_is_refused() {
    let (catalog, mut state) = world();
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("the paid world is monetary");
    };
    economy.financial.public_budgets.clear();
    economy.financial.public_allocations.clear();
    let register = MaterialWorldRegister::try_new(&catalog, 0, state).expect("an unbudgeted world");
    assert_eq!(
        bound(register, &catalog, config(4)).expect_err("the county needs a budget"),
        CountyReviewRegisterError::PublicAccount
    );
    let (catalog, register) = plain_register();
    let mut config = config(4);
    config.public_account_id = [98; 32];
    assert_eq!(
        bound(register, &catalog, config).expect_err("the account is not in the book"),
        CountyReviewRegisterError::PublicAccount
    );
}

#[test]
fn support_lines_that_are_not_the_opening_roll_are_refused() {
    let (catalog, mut state) = world();
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("the paid world is monetary");
    };
    economy.financial.public_allocations[1].amount_per_period = money(2 * UNIT_MICROS);
    let register = MaterialWorldRegister::try_new(&catalog, 0, state).expect("a doubled line");
    assert_eq!(
        bound(register, &catalog, config(4)).expect_err("the line is not the roll at the price"),
        CountyReviewRegisterError::Lines
    );
}

#[test]
fn a_period_that_is_not_the_registers_is_refused() {
    let (catalog, register) = plain_register();
    let section = county();
    let mut state = section.state().clone();
    state.roster.period = 3;
    let section = CountyReviewRegister::try_new(section.config().clone(), state)
        .expect("the kernel does not know the register's period");
    let error = register
        .with_county_review(&catalog, section, None)
        .expect_err("a roster of period 3 in a register of period 0");
    assert_eq!(refusal(error), CountyReviewRegisterError::Period);
}

#[test]
fn tampered_county_frames_are_refused() {
    let (catalog, with) = county_register(4);
    let bytes = with.canonical_bytes().to_vec();
    let mut wrong_version = bytes.clone();
    wrong_version[REGISTER_V9.len()..REGISTER_V9.len() + 4].copy_from_slice(&7_u32.to_be_bytes());
    let mut trailing = bytes.clone();
    trailing.push(0);
    let truncated = bytes[..bytes.len() - 1].to_vec();
    let frame = bytes
        .windows(COUNTY_FRAME.len())
        .position(|window| window == COUNTY_FRAME)
        .expect("the frame's domain is in the bytes");
    let mut renamed = bytes.clone();
    renamed[frame + 10] ^= 1;
    let mut damaged = bytes;
    // The last byte closes the stored state's canonical JSON.
    *damaged.last_mut().expect("the register has bytes") ^= 0x20;
    for changed in [wrong_version, trailing, truncated, renamed, damaged] {
        assert!(MaterialWorldRegister::decode_external(&catalog, changed).is_err());
    }
}

/// The paid world with one company that owns the employer: a catalog with company portfolios,
/// which writes a company frame once a period has closed.
fn company_world() -> (MaterialCatalog, MaterialCircuitState) {
    let (catalog, mut state) = world();
    let company = CompanyId::from_bytes([9; 32]);
    let owner = AccountId::Company(company);
    let issuer = agency_control::site(agency_control::EMPLOYER);
    let mut definition = catalog.into_definition();
    definition.company_portfolios = Some(CompanyPortfolioPolicy {
        condition_order: CompanyConditionOrder::FirstApplicable,
        rows: [
            [70, 30, 0, 0],
            [10, 70, 15, 5],
            [60, 25, 15, 0],
            [10, 10, 60, 20],
        ],
        high_utilization_bps: 8000,
        history_periods: 3,
        modest_expansion_bps: 5000,
    });
    definition.company_payouts = vec![CompanyPayoutPolicy {
        company,
        earnings_bps: 0,
        claims: vec![(AccountId::Household(agency_control::donor()), 1)],
    }];
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("the paid world is monetary");
    };
    let mut cash = economy.book.snapshot();
    cash.accounts.push(CashAccount {
        id: owner,
        cash: money(20),
    });
    economy.book = MonetaryBook::from_snapshot(cash).expect("one company treasury");
    let costs = economy.costs.snapshot();
    let capital = costs
        .accounts
        .iter()
        .find(|row| row.account == AccountId::Site(issuer))
        .expect("the employer has capital accounts")
        .opening_capital;
    economy.costs = HistoricalCostBook::open(
        &economy.book,
        costs.stocks,
        costs.freight,
        vec![EquityCarryingValue {
            owner,
            issuer_site_id: issuer,
            amount: capital,
        }],
        costs.equipment,
    )
    .expect("the parent holds the equity and the treasury");
    economy.financial.ownership = vec![OwnershipClaim {
        issuer_site_id: issuer,
        beneficiary: owner,
        shares: 1,
    }];
    economy.financial.distributions = vec![DistributionPolicy {
        issuer_site_id: issuer,
        earnings_fraction_bps: 0,
        period_cap: money(0),
        cash_floor: money(0),
    }];
    (
        MaterialCatalog::try_new(definition).expect("the company catalog is valid"),
        state,
    )
}

#[test]
fn a_county_register_carries_the_company_frame_only_when_a_register_today_would() {
    let (catalog, state) = company_world();
    let opening = MaterialWorldRegister::try_new(&catalog, 0, state)
        .expect("tick zero carries no company frame")
        .with_county_review(&catalog, county(), None)
        .expect("the county fits");
    assert!(opening.company_portfolios().is_none());
    let decoded =
        MaterialWorldRegister::decode_external(&catalog, opening.canonical_bytes().to_vec())
            .expect("version 9 without the company frame decodes at tick zero");
    assert_eq!(decoded.digest(), opening.digest());
    let mut prepared = opening
        .prepare_next(&catalog)
        .expect("the closed period prepares");
    assert!(prepared.register().company_portfolios().is_some());
    let labor = prepared
        .county_labor_facts()
        .expect("the opening had a county")
        .clone();
    let facts = facts_of(&prepared, county().config(), &labor);
    let held =
        county_review_execution::hold_period(county().config(), county().state(), &facts, None)
            .expect("before the first session only the roster moves");
    prepared
        .set_county_review(&catalog, held.next, held.session.as_ref(), &resolver())
        .expect("the county's next section fits the closed world");
    let register = prepared.register();
    assert_eq!(register.completed_tick(), 1);
    assert!(register.company_portfolios().is_some());
    assert!(register.county_review().is_some());
    let decoded =
        MaterialWorldRegister::decode_external(&catalog, register.canonical_bytes().to_vec())
            .expect("version 9 carries the company frame and then the county frame");
    assert_eq!(decoded.digest(), register.digest());
    assert!(decoded.company_portfolios().is_some());
    assert_eq!(decoded.county_review(), register.county_review());
}

#[test]
fn a_closed_successor_has_no_section_until_the_county_writes_it() {
    let (catalog, opening) = county_register(4);
    let mut prepared = opening
        .prepare_next(&catalog)
        .expect("the closed period prepares");
    assert!(prepared.county_labor_facts().is_some());
    assert!(prepared.register().county_review().is_none());
    let labor = prepared
        .county_labor_facts()
        .expect("the opening had a county")
        .clone();
    let facts = facts_of(&prepared, county().config(), &labor);
    // Before the first session only the roster moves: no line and no hour is written.
    let before = prepared.register().state().clone();
    let held =
        county_review_execution::hold_period(county().config(), county().state(), &facts, None)
            .expect("before the first session only the roster moves");
    assert!(held.session.is_none());
    prepared
        .set_county_review(&catalog, held.next.clone(), None, &resolver())
        .expect("the county's next section fits the closed world");
    assert_eq!(prepared.register().state(), &before);
    let written = prepared
        .register()
        .county_review()
        .expect("the county wrote its section");
    assert_eq!(written.state().roster.period, 1);
    assert_eq!(written.state().last_facts.as_ref(), Some(&facts));
    assert!(written.state().last_session.is_none());
    assert_eq!(written.config(), county().config());
}

#[test]
fn a_crew_with_no_staffing_receipt_keeps_the_rosters_counts_and_reads_its_wages() {
    let (catalog, opening) = county_register(4);
    let prepared = opening
        .prepare_next(&catalog)
        .expect("the closed period prepares");
    let labor = prepared
        .county_labor_facts()
        .expect("the opening had a county");
    let crew = &labor.crews[0];
    assert_eq!((crew.opening_at_work, crew.opening_seeking), (3, 1));
    assert_eq!((crew.closing_at_work, crew.closing_seeking), (3, 1));
    assert_eq!((crew.hires, crew.separations), (0, 0));
    assert_eq!((crew.left_at_work, crew.left_seeking), (0, 0));
    assert!(
        crew.accrued_wages_micros > 0,
        "the engine paid the employer's wage"
    );
    let donors = &labor.groups[0];
    assert!(donors.taxed_wages_micros > 0);
    assert!(donors.wage_tax_collected_micros > 0);
    assert!(donors.wage_tax_collected_micros <= donors.taxed_wages_micros);
    assert_eq!(donors.closing_households, 4);
    let recipients = &labor.groups[1];
    assert_eq!(recipients.taxed_wages_micros, 0);
    assert_eq!(recipients.wage_tax_collected_micros, 0);
    assert_eq!(recipients.closing_households, 4);
}

#[test]
fn cutting_the_tax_receipt_changes_the_list() {
    // With no wage tax collected the household at work has no place: the unit the county can pay
    // goes to the household that already holds one. With the tax in place the household at work
    // ranks above it, so the reached household asks and is paid and the holder loses its unit.
    let (catalog, opening) = county_register(1);
    let prepared = opening
        .prepare_next(&catalog)
        .expect("the closed period prepares");
    let labor = prepared
        .county_labor_facts()
        .expect("the opening had a county")
        .clone();
    assert!(labor.groups[0].wage_tax_collected_micros > 0);
    assert!(labor.crews[0].accrued_wages_micros > 0);
    let config = config(1);
    let state = state_for(&config);
    let at_work = at_work_key(&state);
    let hold = |labor: &CountyLaborFacts| {
        let facts = facts_of(&prepared, &config, labor);
        county_review_execution::hold_period(&config, &state, &facts, Some(at_work))
            .expect("the session holds")
            .session
            .expect("the first session period holds a session")
    };
    let asked_paid = |held: &SessionOutcome| {
        held.record
            .rows
            .iter()
            .find(|row| row.key == at_work)
            .map(|row| row.asked_paid)
    };
    let held_paid = |held: &SessionOutcome| {
        held.record
            .rows
            .iter()
            .filter(|row| row.key.units > 0)
            .map(|row| row.units_paid)
            .sum::<u64>()
    };
    let with = hold(&labor);
    let mut cut = labor;
    cut.groups[0].wage_tax_collected_micros = 0;
    let without = hold(&cut);
    assert_eq!(asked_paid(&with), Some(1), "the taxed household is paid");
    assert_eq!(
        held_paid(&with),
        0,
        "and the holder below it loses its unit"
    );
    assert_eq!(asked_paid(&without), Some(0), "no tax, no place");
    assert_eq!(held_paid(&without), 1, "the holder keeps its unit");
}

/// An organizer with one participant, the county review it may reach a household for, and a
/// journal that holds the closed period 1 with no receipt: the contact the rule reads is none.
fn organizer_for(
    county: &CountyReviewConfig,
) -> (OrganizerConfig, OrganizerState, OrganizerPeriodJournal) {
    let partner = |actor_id: u64, authority: u8, label: &str| OrganizerPartner {
        actor_id,
        authority_id: [authority; 16],
        label: label.to_owned(),
        policy: OrganizerPartnerPolicy::Participate,
        permits_work_report: false,
        permits_maintenance_report: false,
    };
    let config = OrganizerConfig {
        hearing: None,
        review: Some(OrganizerReviewConfig {
            county_geoid: "26163".to_owned(),
            first_session_period: county.first_session_period,
            county_config_digest: babylon_practice_contract::county_review_config_digest(county)
                .expect("the county's configuration encodes"),
        }),
        schema_version: ORGANIZER_SCHEMA_VERSION,
        collection: None,
        campaign_id: [3; 16],
        controlled_actor_id: 101,
        input_authority_id: [8; 16],
        organization_label: "Fixture organizing collective".to_owned(),
        workplace_id: 104,
        workplace_process_id: [1; 32],
        workplace_label: "Fixture workplace".to_owned(),
        workplace_partner: partner(102, 9, "Fixture workplace committee"),
        neighborhood_partner: partner(103, 10, "Fixture neighborhood group"),
        participants: vec![OrganizerParticipant {
            contributor_id: 201,
            label: "Fixture participant".to_owned(),
            available_hours: 16,
            commitments: vec![OrganizerContribution {
                actor_id: 101,
                hours: 8,
            }],
            concern: "Explain lost work".to_owned(),
            objection: "Respect promised time".to_owned(),
            review_condition: "Review next period".to_owned(),
        }],
        time_binding: OrganizerTimeBindingMode::FixedTimeControl,
        aid_bindings: vec![],
        inquiry_hours: 12,
        contact_hours: 8,
        partner_response_hours: 2,
        initial_agreement_through_period: 3,
        contact_renewal_periods: 2,
        content_digest: [5; 32],
        initial_observations: vec![],
    };
    let mut state = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the configuration admits an opening state");
    state.period = 1;
    let mut journal = OrganizerPeriodJournal::empty();
    journal
        .append(OrganizerPeriodJournalEntries::new(1))
        .expect("the first period extends an empty journal");
    (config, state, journal)
}

/// The closed period 1 of the county world, with an organizer whose journal holds that period.
fn organized_candidate() -> (MaterialCatalog, PreparedMaterialWorld) {
    let (catalog, opening) = county_register(1);
    let mut prepared = opening
        .prepare_next(&catalog)
        .expect("the closed period prepares");
    let (config, state, journal) = organizer_for(&config(1));
    prepared
        .set_organizer(&catalog, config, state, journal, &resolver())
        .expect("the organizer binds to the county world");
    (catalog, prepared)
}

#[test]
fn resolving_the_same_candidate_twice_writes_the_same_register() {
    let (catalog, mut prepared) = organized_candidate();
    let resolver = resolver();
    county_review_execution::resolve(&mut prepared, &catalog, &resolver)
        .expect("the county's period resolves");
    let bytes = prepared.register().canonical_bytes().to_vec();
    let county = prepared
        .register()
        .county_review()
        .expect("the section is written")
        .clone();
    assert!(
        county.state().last_session.is_some(),
        "period 1 is the first session"
    );
    county_review_execution::resolve(&mut prepared, &catalog, &resolver)
        .expect("the same candidate resolves again");
    assert_eq!(
        prepared.register().canonical_bytes(),
        bytes.as_slice(),
        "the second run reads the period's opening and not its own result"
    );
    assert_eq!(prepared.register().county_review(), Some(&county));
}

#[test]
fn every_other_writer_carries_the_county_section() {
    let (catalog, mut prepared) = organized_candidate();
    let resolver = resolver();
    county_review_execution::resolve(&mut prepared, &catalog, &resolver)
        .expect("the county's period resolves");
    let county = prepared
        .register()
        .county_review()
        .expect("the section is written")
        .clone();
    let (config, state, journal) = organizer_for(&config(1));
    prepared
        .set_organizer(&catalog, config, state, journal, &resolver)
        .expect("the organizer is written again");
    assert_eq!(
        prepared.register().county_review(),
        Some(&county),
        "the organizer writer keeps the county's section"
    );
    assert!(prepared.register().organizer_journal().is_some());
}

#[test]
fn resolving_a_period_twice_changes_nothing() {
    let (catalog, opening) = county_register(1);
    let mut prepared = opening
        .prepare_next(&catalog)
        .expect("the closed period prepares");
    let resolver = resolver();
    let config = config(1);
    let state = state_for(&config);
    let write = |prepared: &mut PreparedMaterialWorld| {
        let labor = prepared
            .county_labor_facts()
            .expect("the opening had a county")
            .clone();
        let facts = facts_of(prepared, &config, &labor);
        let held = county_review_execution::hold_period(
            &config,
            &state,
            &facts,
            Some(at_work_key(&state)),
        )
        .expect("the session holds");
        prepared
            .set_county_review(
                &catalog,
                held.next.clone(),
                held.session.as_ref(),
                &resolver,
            )
            .expect("the county's section is written");
        held
    };
    let first = write(&mut prepared);
    let digest = prepared.register().digest();
    let second = write(&mut prepared);
    assert_eq!(
        first, second,
        "the free hours it reads leave out its own charge"
    );
    assert_eq!(prepared.register().digest(), digest);
    let session = first.session.as_ref().expect("a session period");
    assert!(
        !session.hour_charges.is_empty(),
        "a reached household that asks spends the donors' hours"
    );
    let CircuitAccounting::Monetary(economy) = &prepared.register().state().accounting else {
        panic!("the paid world is monetary");
    };
    let HouseholdTimeAccounting::Modeled(time) = &economy.household_time else {
        panic!("the paid world models household time");
    };
    let charged: Vec<_> = time
        .contributions
        .iter()
        .filter(|row| row.contribution.actor_id == config.actor_id)
        .collect();
    assert_eq!(
        charged.len(),
        session.hour_charges.len(),
        "one use for each charge"
    );
    for (row, charge) in charged.iter().zip(&session.hour_charges) {
        let group = &config.groups[usize::try_from(charge.group).expect("a small index")];
        assert_eq!(row.contribution.hours, charge.hours);
        assert_eq!(row.period, 1);
        assert_eq!(row.contribution.principal_id.as_bytes(), group.group_id);
        assert_eq!(row.contribution.contributor_id, u64::from(charge.group) + 1);
    }
    let support: Vec<_> = economy
        .financial
        .public_allocations
        .iter()
        .filter(|row| row.treatment == PublicTransferTreatment::HouseholdIncomeSupport)
        .collect();
    assert_eq!(support.len(), session.record.lines.len());
    for line in &session.record.lines {
        let group = &config.groups[usize::try_from(line.group).expect("a small index")];
        assert!(support.iter().any(|row| {
            row.recipient
                == AccountId::Household(FinalDemandPrincipalId::from_bytes(group.group_id))
                && row.priority == 1
                && row.amount_per_period == money(line.amount_micros)
        }));
    }
    let grants: Vec<_> = economy
        .financial
        .public_allocations
        .iter()
        .filter(|row| row.treatment == PublicTransferTreatment::ProviderOperatingGrant)
        .collect();
    assert_eq!(grants.len(), 1, "the grant stays");
    assert_eq!(grants[0].amount_per_period, money(GRANT_MICROS));
    assert_eq!(grants[0].priority, 0);
    assert_eq!(
        economy.financial.public_budgets[0].period_cap,
        money(5_000_000_000)
    );
}

#[test]
fn a_session_the_kernel_refuses_refuses_the_period() {
    let (catalog, opening) = county_register(1);
    let prepared = opening
        .prepare_next(&catalog)
        .expect("the closed period prepares");
    let mut config = config(1);
    let state = state_for(&config);
    let mut labor = prepared
        .county_labor_facts()
        .expect("the opening had a county")
        .clone();
    // The engine says the crew had fewer people at work than the roster holds.
    labor.crews[0].opening_at_work -= 1;
    let facts = facts_of(&prepared, &config, &labor);
    assert_eq!(
        county_review_execution::hold_period(&config, &state, &facts, None)
            .expect_err("the roster and the engine disagree"),
        MaterialWorldError::from(CountyReviewError::RosterEngineMismatch)
    );
    // A contact before the first session has no session to land in.
    config.first_session_period = 4;
    let labor = prepared
        .county_labor_facts()
        .expect("the opening had a county")
        .clone();
    let facts = facts_of(&prepared, &config, &labor);
    let key = PositionKey {
        group: 0,
        band: Band::Next40,
        crew: Some(0),
        at_work: 1,
        seeking: 0,
        units: 0,
    };
    assert_eq!(
        refusal(
            county_review_execution::hold_period(&config, &state, &facts, Some(key))
                .expect_err("no session can follow this contact")
        ),
        CountyReviewRegisterError::Contact
    );
}
