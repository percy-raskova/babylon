use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::{EconomicFunction, QcewOwnership, TradeSet};
use babylon_kernel::economic_location::{EconomicLocation, ForeignCounterpart};
use babylon_material_circuit::WantTier;
use babylon_material_circuit::{CommodityKind, HouseholdNeedBasis, ServiceStage};
use babylon_persistence::national_economy;
use babylon_persistence::national_economy::{
    GameFundPolicy, GameHandling, GameLuxuryScale, GameMachines, GameMapBasis, GameProcurement,
    GameProfileWage, GameProgramRecipients, GameProgramTerms, GameWages, NationalGamePolicy,
    NationalGamePolicyError,
};
use babylon_persistence::national_household_allocation::HouseholdBudgetKey;
use std::collections::BTreeMap;

const SOURCE: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../content/scenarios/national/defines.toml"
));

#[test]
fn captured_collection_default_and_cap_are_explicit_positive_terms_without_extra_treasury() {
    let policy = NationalGamePolicy::parse(SOURCE).expect("national policy");
    assert_eq!(policy.organizer.collection_initial_cash_micros, 280_000_000);
    assert_eq!(
        policy.organizer.collection_maximum_cash_micros,
        1_450_000_000
    );
    assert_eq!(policy.aid.organization_opening_cash_micros, 1_000_000);
    for amount in [0_i128, -1, 1_450_000_001, i128::MAX] {
        let changed = SOURCE.replace(
            "collection_initial_cash_micros = 280000000",
            &format!("collection_initial_cash_micros = {amount}"),
        );
        assert_ne!(changed, SOURCE);
        assert!(NationalGamePolicy::parse(&changed).is_err());
    }
    let missing = SOURCE.replace("collection_initial_cash_micros = 280000000\n", "");
    assert!(NationalGamePolicy::parse(&missing).is_err());
}

#[test]
fn captured_aid_has_independent_bounded_defaults_without_extra_treasury() {
    let policy = NationalGamePolicy::parse(SOURCE).expect("captured national terms");
    assert_eq!(policy.aid.maximum_quantity, 4);
    assert_eq!(policy.aid.maximum_cash_micros, 1_450_000_000);
    assert_eq!(policy.aid.initial_food_quantity, 1);
    assert_eq!(policy.aid.initial_cash_micros, 0);
    assert_eq!(policy.aid.organization_opening_cash_micros, 1_000_000);
    for amount in [-1_i128, 1_450_000_001] {
        let changed = SOURCE.replace(
            "initial_cash_micros = 0",
            &format!("initial_cash_micros = {amount}"),
        );
        assert_ne!(changed, SOURCE);
        assert_eq!(
            NationalGamePolicy::parse(&changed),
            Err(NationalGamePolicyError::Shape)
        );
    }
    for term in [
        "maximum_cash_micros = 1450000000\n",
        "initial_cash_micros = 0\n",
        "local_cash_receiving_consent = \"accept\"\n",
    ] {
        let changed = SOURCE.replace(term, "");
        assert_ne!(changed, SOURCE);
        assert!(NationalGamePolicy::parse(&changed).is_err());
    }
}

#[test]
fn household_time_policy_is_captured_separately_from_wages_and_population() {
    let policy = NationalGamePolicy::parse(SOURCE)
        .expect("the authored literal parses as the declared type");
    let time = &policy.household_time;
    assert_eq!(time.hours_per_eligible_person, 224);
    assert!(time.hours_per_eligible_person >= policy.work_hours_per_person);
    assert_eq!(time.ordinary_protected_hours_per_household, 32);
    assert_eq!(time.ordinary_provisioning_hours_per_household, 64);
    assert_eq!(time.collective_protected_hours_per_person, 32);
    assert_eq!(time.collective_provisioning_hours_per_person, 64);
    assert_eq!(time.external_eligible_persons_bps, 8_000);
    assert_eq!(time.unmet_hours_per_unit["food"], 20);
    assert_eq!(time.unmet_hours_per_unit.len(), 1);
    let captured = NationalGamePolicy::from_captured_bytes(SOURCE.as_bytes())
        .expect("the captured bytes admit the value");
    assert_eq!(captured.household_time, policy.household_time);
}

#[test]
fn household_time_policy_refuses_missing_unbounded_or_unrelated_commitments() {
    let section = SOURCE
        .find("[household_time]\n")
        .expect("the current policy must capture time coefficients");
    let end = SOURCE[section + 1..]
        .find("\n[")
        .map_or(SOURCE.len(), |offset| section + 1 + offset);
    let mut missing = SOURCE.to_owned();
    missing.replace_range(section..end, "");
    assert!(NationalGamePolicy::parse(&missing).is_err());
    for changed in [
        SOURCE.replace(
            "hours_per_eligible_person = 224",
            "hours_per_eligible_person = 0",
        ),
        SOURCE.replace(
            "hours_per_eligible_person = 224",
            "hours_per_eligible_person = 159",
        ),
        SOURCE.replace(
            "hours_per_eligible_person = 224",
            "hours_per_eligible_person = 673",
        ),
        SOURCE.replace(
            "external_eligible_persons_bps = 8000",
            "external_eligible_persons_bps = 10001",
        ),
        SOURCE.replace(
            "unmet_hours_per_unit = { food = 20 }",
            "unmet_hours_per_unit = { food = 0 }",
        ),
        SOURCE.replace(
            "unmet_hours_per_unit = { food = 20 }",
            "unmet_hours_per_unit = { equipment = 20 }",
        ),
    ] {
        assert_ne!(
            changed, SOURCE,
            "the boundary mutation must change the input"
        );
        assert!(NationalGamePolicy::parse(&changed).is_err());
    }
}

#[test]
fn national_policy_covers_physical_functions_and_distinct_household_needs() {
    let policy = NationalGamePolicy::parse(SOURCE)
        .expect("the authored literal parses as the declared type");
    assert_eq!(policy.commodities.len(), 10);
    assert_eq!(policy.recipes.len(), 9);
    assert_eq!(policy.household_needs.len(), 6);
    let food = &policy.commodities["food"];
    assert_eq!(
        food.kind,
        CommodityKind::Storable {
            grams_per_unit: 14_000
        }
    );
    let housing = &policy.commodities["housing"];
    assert_eq!(
        housing.kind,
        CommodityKind::PeriodService {
            stage: ServiceStage::LocalServiceProvision
        }
    );
    assert_eq!(
        policy
            .household_needs
            .iter()
            .find(|n| n.key == "food")
            .expect("the fixture holds the searched element")
            .basis,
        HouseholdNeedBasis::Persons
    );
    assert_eq!(
        policy
            .household_needs
            .iter()
            .find(|n| n.key == "housing")
            .expect("the fixture holds the searched element")
            .basis,
        HouseholdNeedBasis::Households
    );
    // Renewable food buys replenished inputs; extraction debits a finite reserve.
    assert!(!policy.recipes[&EconomicFunction::Food]
        .inputs
        .contains_key("resource_deposit"));
    assert_eq!(
        policy.recipes[&EconomicFunction::Extraction].inputs["resource_deposit"],
        8
    );
    assert_eq!(policy.commodities["resource_deposit"].price, None);
}

#[test]
fn counterparts_have_finite_separate_resident_and_workforce_counts() {
    let policy = NationalGamePolicy::parse(SOURCE)
        .expect("the authored literal parses as the declared type");
    assert_eq!(policy.counterparts.len(), 12);
    for counterpart in ForeignCounterpart::ALL {
        let profile = &policy.counterparts[&counterpart];
        let counts = profile
            .opening_counts(1_000)
            .expect("the fixture call `opening_counts` succeeds for the authored inputs");
        assert_eq!((counts.persons, counts.households), (1_000, 334));
        assert_eq!(
            (counts.employed, counts.reserve, counts.inactive),
            (405, 45, 550)
        );
        assert_eq!(
            counts.employed + counts.reserve + counts.inactive,
            counts.persons
        );
        assert_eq!(
            profile
                .function_weights_bps
                .iter()
                .map(|v| u64::from(*v))
                .sum::<u64>(),
            10_000
        );
    }
    assert!(policy.counterparts[&ForeignCounterpart::Canada]
        .opening_counts(u64::MAX)
        .is_err());
    assert_eq!(policy.dependency.missing_population_game_persons, 50);
    let mut invalid = policy.counterparts[&ForeignCounterpart::Canada].clone();
    invalid.persons_per_household = 0;
    assert!(invalid.opening_counts(1_000).is_err());
    invalid.persons_per_household = 3;
    invalid.participation_bps = 10_001;
    assert!(invalid.opening_counts(1_000).is_err());

    let price = policy.commodities["food"]
        .price
        .as_ref()
        .expect("the fixture set the optional field before this read");
    let scaled = price
        .scaled(4_000)
        .expect("the fixture call `scaled` succeeds for the authored inputs");
    assert_eq!(scaled.opening.micro_units(), 112_000_000);
    assert_eq!(scaled.minimum.micro_units(), 28_000_000);
    assert!(price.scaled(0).is_err());
}

#[test]
fn policy_refuses_unknown_sources_invalid_prices_and_same_stage_inputs() {
    for changed in [
        SOURCE.replace("evidence_class = \"Designed\"", "evidence_class = \"Observed\""),
        SOURCE.replace("opening_price_micros = 280000000", "opening_price_micros = 0"),
        SOURCE.replace("basis = \"households\"", "basis = \"jobs\""),
        SOURCE.replace("[counterpart.\"canada\"]", "[counterpart.\"Canada\"]"),
        SOURCE.replace("[process.business_services]\noutput = \"business_services\"\noutput_units_per_batch = 16\nlabor_hours_per_batch = 160\ninputs = { materials = 1, utility = 1 }", "[process.business_services]\noutput = \"business_services\"\noutput_units_per_batch = 16\nlabor_hours_per_batch = 160\ninputs = { housing = 1, utility = 1 }"),
    ] {
        assert!(NationalGamePolicy::parse(&changed).is_err());
    }
    assert_eq!(
        NationalGamePolicy::parse("{}"),
        Err(NationalGamePolicyError::Syntax)
    );
}

#[test]
fn source_workplace_identity_keeps_ownership_and_function_independent() {
    let location: EconomicLocation = "county:26163"
        .parse()
        .expect("the authored literal parses as the declared type");
    let private = national_economy::source_workplace_target(
        location,
        EconomicFunction::Food,
        QcewOwnership::Private,
        7,
    )
    .expect("the fixture call `source_workplace_target` succeeds for the authored inputs");
    let public = national_economy::source_workplace_target(
        location,
        EconomicFunction::Food,
        QcewOwnership::LocalGovernment,
        7,
    )
    .expect("the fixture call `source_workplace_target` succeeds for the authored inputs");
    let other = national_economy::source_workplace_target(
        location,
        EconomicFunction::Manufacturing,
        QcewOwnership::Private,
        7,
    )
    .expect("the fixture call `source_workplace_target` succeeds for the authored inputs");
    assert_ne!(private.site_id, public.site_id);
    assert_ne!(private.site_id, other.site_id);
    assert!(private.workplace.canonical_bytes().is_ok());
    assert!(public.workplace.canonical_bytes().is_ok());
    assert!(other.workplace.canonical_bytes().is_ok());
    assert_eq!(private.allocation_weight, 7);
    assert_eq!(private.location, location);
    assert_eq!(
        private,
        national_economy::source_workplace_target(
            location,
            EconomicFunction::Food,
            QcewOwnership::Private,
            7
        )
        .expect("the fixture call `source_workplace_target` succeeds for the authored inputs")
    );
    assert_eq!(
        private.workplace,
        babylon_graph::stable_element::StableElementKey::Node {
            scenario: babylon_persistence::national_economy::NATIONAL_SCENARIO_ID.to_owned(),
            local_name: "site-26163-food-5".to_owned(),
        }
    );
}

#[test]
fn authored_funding_and_equipment_controls_refuse_unaccounted_requirements() {
    let disabled = SOURCE
        .replace("wage_tax_bps = 1500", "wage_tax_bps = 0")
        .replace(
            "private_distribution_bps = 5000",
            "private_distribution_bps = 0",
        );
    let parsed = NationalGamePolicy::parse(&disabled)
        .expect("the authored literal parses as the declared type");
    assert_eq!(parsed.financial.wage_tax_bps, 0);
    assert_eq!(parsed.financial.private_distribution_bps, 0);
    assert!(NationalGamePolicy::parse(&SOURCE.replace(
        "operating_income_tax_bps = 1500",
        "operating_income_tax_bps = 10001"
    ))
    .is_err());
    assert!(NationalGamePolicy::parse(&SOURCE.replace(
        "installation_inputs = { materials = 4 }",
        "installation_inputs = { utility = 4 }"
    ))
    .is_err());
    assert!(NationalGamePolicy::parse(&SOURCE.replace(
        "service_batches_per_unit = 4000",
        "service_batches_per_unit = 0"
    ))
    .is_err());
}

#[test]
fn a_schema_7_recipe_for_a_new_trade_is_refused() {
    let changed = SOURCE.replace("[process.capital_goods]", "[process.consumer_goods]");
    assert_ne!(changed, SOURCE);
    assert_eq!(
        NationalGamePolicy::parse(&changed),
        Err(NationalGamePolicyError::Recipe("consumer_goods".to_owned()))
    );
}

#[test]
fn cargo_eligibility_is_captured_and_cannot_be_inferred_from_mass() {
    use babylon_persistence::national_transport::CargoClass;
    let policy = NationalGamePolicy::parse(SOURCE)
        .expect("the authored literal parses as the declared type");
    assert_eq!(policy.commodities["food"].cargo, Some(CargoClass::General));
    assert_eq!(
        policy.commodities["resources"].cargo,
        Some(CargoClass::DryBulk)
    );
    assert_eq!(policy.commodities["housing"].cargo, None);
    assert_eq!(policy.commodities["resource_deposit"].cargo, None);
    for changed in [
        SOURCE.replacen("cargo_class = \"general\"\n", "", 1),
        SOURCE.replacen(
            "cargo_class = \"general\"",
            "cargo_class = \"unlimited\"",
            1,
        ),
        SOURCE.replace(
            "foreign_procurement_bps = 2500",
            "foreign_procurement_bps = 10001",
        ),
        SOURCE.replace(
            "journey_timing = \"slowest_profile\"",
            "journey_timing = \"instant\"",
        ),
    ] {
        assert!(NationalGamePolicy::parse(&changed).is_err());
    }
}

#[test]
fn owner_exposure_fraction_is_required_bounded_and_separate_from_income() {
    assert_eq!(
        NationalGamePolicy::parse(SOURCE)
            .expect("the authored literal parses as the declared type")
            .households
            .private_owner_households_bps,
        1_000
    );
    for bad in ["0", "10001", "-1"] {
        assert!(NationalGamePolicy::parse(&SOURCE.replace(
            "private_owner_households_bps = 1000",
            &format!("private_owner_households_bps = {bad}")
        ))
        .is_err());
    }
    assert!(
        NationalGamePolicy::parse(&SOURCE.replace("private_owner_households_bps = 1000", ""))
            .is_err()
    );
}

#[test]
fn venue_log_reader_is_required_and_closed() {
    let controlled = SOURCE.to_owned();
    let committee = SOURCE.replace(
        "venue_log_reader = \"controlled_organizer\"",
        "venue_log_reader = \"workplace_committee\"",
    );
    let unknown = SOURCE.replace(
        "venue_log_reader = \"controlled_organizer\"",
        "venue_log_reader = \"unknown_actor\"",
    );
    let missing = SOURCE.replace("venue_log_reader = \"controlled_organizer\"", "");
    assert!(NationalGamePolicy::parse(&controlled).is_ok());
    assert!(NationalGamePolicy::parse(&committee).is_ok());
    assert!(NationalGamePolicy::parse(&unknown).is_err());
    assert!(NationalGamePolicy::parse(&missing).is_err());
}

#[test]
fn city_pd_terms_are_designed_sourced_and_required_from_schema_7() {
    let policy = NationalGamePolicy::parse(SOURCE).expect("the shipped national policy");
    let terms = policy.city_pd.as_ref().expect("schema 7 carries [city_pd]");
    assert_eq!(terms.positions, 3_529);
    assert_eq!(terms.visits_per_period, 1);
    assert_eq!(terms.visit_hours, 1);
    assert!(terms.positions_source.starts_with("City of Detroit"));
    // The wage is still the shipped wage; only its three jobs are separate.
    assert_eq!(
        policy.wages.single().map(Currency::micro_units),
        Some(24_000_000)
    );

    let table = SOURCE
        .find("\n[city_pd]\n")
        .expect("the shipped policy names the City PD's books");
    let without = &SOURCE[..table];
    assert!(NationalGamePolicy::parse(without).is_err());
    // An earlier schema has no such table and refuses one.
    assert!(NationalGamePolicy::parse(&SOURCE.replacen(
        "schema_version = 7",
        "schema_version = 6",
        1
    ))
    .is_err());
    for changed in [
        SOURCE.replace("positions = 3529", "positions = 0"),
        SOURCE.replace("visits_per_period = 1", "visits_per_period = 0"),
        SOURCE.replace("visit_hours = 1\n", "visit_hours = 0\n"),
        SOURCE.replace(
            "[city_pd]\nevidence_class = \"Designed\"",
            "[city_pd]\nevidence_class = \"Observed\"",
        ),
        SOURCE.replace(
            "positions_source = \"City of Detroit",
            "positions_source = \"\"\n# City of Detroit",
        ),
    ] {
        assert_ne!(changed, SOURCE, "the mutation must change the input");
        assert!(NationalGamePolicy::parse(&changed).is_err());
    }
}

#[test]
fn county_review_terms_are_designed_and_required_from_schema_7() {
    let policy = NationalGamePolicy::parse(SOURCE).expect("the shipped national policy");
    let terms = policy
        .county_review
        .as_ref()
        .expect("schema 7 carries [county_review]");
    assert_eq!(terms.county.as_str(), "26163");
    assert_eq!(terms.first_session_period, 4);
    assert_eq!(terms.session_hours, 2);
    assert_eq!(terms.bring_hours, 2);
    // The two bodies are the hearing's claimants and the organizer's local partner.
    let hearing = policy
        .organizer
        .hearing
        .as_ref()
        .expect("the shipped policy holds the relief hearing");
    assert_eq!(terms.claimants_body_label, hearing.claimant_label);
    assert_eq!(terms.aid_body_label, policy.organizer.local_partner_label);

    let table = SOURCE
        .find("\n[county_review]\n")
        .expect("the shipped policy names the county review's terms");
    assert!(NationalGamePolicy::parse(&SOURCE[..table]).is_err());
    // An earlier schema has no such table and refuses one.
    assert!(NationalGamePolicy::parse(&SOURCE.replacen(
        "schema_version = 7",
        "schema_version = 6",
        1
    ))
    .is_err());
    for changed in [
        SOURCE.replace(
            "[county_review]\nevidence_class = \"Designed\"",
            "[county_review]\nevidence_class = \"Observed\"",
        ),
        SOURCE.replace("first_session_period = 4", "first_session_period = 0"),
        SOURCE.replace("session_hours = 2", "session_hours = 0"),
        SOURCE.replace("bring_hours = 2", "bring_hours = 0"),
        SOURCE.replace(
            "claimants_body_label = \"Wayne Relief Claimants Assembly\"",
            "claimants_body_label = \"Another assembly\"",
        ),
        SOURCE.replace(
            "aid_body_label = \"Wayne Local Aid Partners\"",
            "aid_body_label = \"Another partner\"",
        ),
        SOURCE.replace(
            "[county_review]\nevidence_class = \"Designed\"\ncounty = \"26163\"",
            "[county_review]\nevidence_class = \"Designed\"\ncounty = \"26125\"",
        ),
    ] {
        assert_ne!(changed, SOURCE, "the mutation must change the input");
        assert!(NationalGamePolicy::parse(&changed).is_err());
    }
}

const TWELVE: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/tests/fixtures/national_twelve_trades.defines.toml"
));

#[test]
fn the_twelve_trade_fixture_parses() {
    let policy = NationalGamePolicy::parse(TWELVE).expect("the schema 8 fixture");
    assert_eq!(policy.trades, TradeSet::Twelve);
    assert_eq!(policy.commodities.len(), 12);
    assert_eq!(policy.recipes.len(), 11);
    assert_eq!(policy.household_needs.len(), 6);
    assert_eq!(policy.wages, GameWages::Observed);
    assert_eq!(policy.wages.single(), None);
    assert_eq!(policy.households.next_forty_households_bps, Some(4000));
    let order = policy.markets.paying_order.as_ref().expect("paying order");
    assert_eq!(
        order.as_slice(),
        [
            "food",
            "materials",
            "consumer_goods",
            "utility",
            "housing",
            "household_services",
            "leisure",
            "business_services",
            "resources"
        ]
    );
    let canada = &policy.counterparts[&ForeignCounterpart::Canada];
    assert_eq!(
        canada.wage,
        GameProfileWage::FractionOfUnitedStates { bps: 8333 }
    );
    assert_eq!(canada.function_weights_bps.len(), 12);
    assert_eq!(
        canada
            .function_weights_bps
            .iter()
            .map(|w| u64::from(*w))
            .sum::<u64>(),
        10_000
    );
    assert!(policy
        .recipes
        .contains_key(&EconomicFunction::ConsumerGoods));
    assert!(policy
        .recipes
        .contains_key(&EconomicFunction::LeisureHospitality));
}

#[test]
fn the_shipped_policy_keeps_its_shape() {
    let policy = NationalGamePolicy::parse(SOURCE).expect("the shipped policy");
    assert_eq!(policy.trades, TradeSet::Ten);
    assert_eq!(
        policy.wages,
        GameWages::Single(Currency::from_micro_units(24_000_000))
    );
    assert_eq!(policy.markets.paying_order, None);
    assert_eq!(policy.households.next_forty_households_bps, None);
    assert_eq!(policy.commodities.len(), 10);
    assert_eq!(policy.recipes.len(), 9);
    let canada = &policy.counterparts[&ForeignCounterpart::Canada];
    assert_eq!(
        canada.wage,
        GameProfileWage::PerHour(Currency::from_micro_units(20_000_000))
    );
    assert_eq!(canada.function_weights_bps.len(), 10);
}

#[test]
fn schema_8_keys_are_refused_under_schema_7() {
    let bands = SOURCE.replace(
        "private_owner_households_bps = 1000\n",
        "private_owner_households_bps = 1000\nnext_forty_households_bps = 4000\n",
    );
    let order = SOURCE.replace(
        "journey_timing =",
        "paying_order = [\"food\"]\njourney_timing =",
    );
    for changed in [bands, order] {
        assert_ne!(changed, SOURCE);
        assert_eq!(
            NationalGamePolicy::parse(&changed),
            Err(NationalGamePolicyError::Shape)
        );
    }
}

fn shape_or_profile(changed: &str) {
    assert_ne!(changed, TWELVE);
    assert!(
        matches!(
            NationalGamePolicy::parse(changed),
            Err(NationalGamePolicyError::Shape | NationalGamePolicyError::Profile(_))
        ),
        "{:?}",
        NationalGamePolicy::parse(changed)
    );
}

#[test]
fn schema_8_needs_all_its_keys() {
    let order_start = TWELVE.find("paying_order = ").expect("order");
    let order_end = order_start + TWELVE[order_start..].find('\n').expect("eol") + 1;
    let mut no_order = TWELVE.to_owned();
    no_order.replace_range(order_start..order_end, "");
    shape_or_profile(&no_order);
    shape_or_profile(&TWELVE.replace("next_forty_households_bps = 4000\n", ""));
    shape_or_profile(&TWELVE.replace(
        "work_hours_per_person = 160\n",
        "work_hours_per_person = 160\ndefault_wage_micros_per_hour = 24000000\n",
    ));
    shape_or_profile(&TWELVE.replace(
        "function_weights_bps = [1200, 150, 1000, 150, 1200, 800, 1800, 800, 1500, 500, 600, 300]",
        "function_weights_bps = [1200, 300, 1000, 1200, 800, 1800, 800, 2000, 600, 300]",
    ));
    // A schema 7 wage key under schema 8 is a shape fault, not a profile fault.
    assert!(matches!(
        NationalGamePolicy::parse(&TWELVE.replace(
            "wage_fraction_bps = 8333",
            "wage_micros_per_hour = 20000000",
        )),
        Err(NationalGamePolicyError::Shape)
    ));
    shape_or_profile(&TWELVE.replace("wage_fraction_bps = 8333", "wage_fraction_bps = 10001"));
    shape_or_profile(&TWELVE.replace("wage_fraction_bps = 8333", "wage_fraction_bps = 0"));
    let mut eleven = TWELVE.to_owned();
    let at = eleven.find("[process.consumer_goods]").expect("process");
    let end = at + eleven[at..].find("\n\n").expect("blank") + 2;
    eleven.replace_range(at..end, "");
    shape_or_profile(&eleven);
}

#[test]
fn an_order_of_paying_is_refused_when_wrong() {
    let original = "paying_order = [\"food\", \"materials\", \"consumer_goods\", \"utility\", \"housing\", \"household_services\", \"leisure\", \"business_services\", \"resources\"]";
    assert!(TWELVE.contains(original));
    let with = |order: &str| TWELVE.replace(original, &format!("paying_order = [{order}]"));
    let cases = [
        // an unknown product
        with("\"food\", \"materials\", \"consumer_goods\", \"utility\", \"housing\", \"household_services\", \"leisure\", \"business_services\", \"resources\", \"nothing\""),
        // a product twice
        with("\"food\", \"materials\", \"consumer_goods\", \"utility\", \"housing\", \"household_services\", \"leisure\", \"business_services\", \"resources\", \"food\""),
        // a storable household need after a service
        with("\"food\", \"utility\", \"housing\", \"materials\", \"consumer_goods\", \"household_services\", \"leisure\", \"business_services\", \"resources\""),
        // a storable household need left out
        with("\"food\", \"consumer_goods\", \"utility\", \"housing\", \"household_services\", \"leisure\", \"business_services\", \"resources\""),
        // utility after a local service
        with("\"food\", \"materials\", \"consumer_goods\", \"housing\", \"utility\", \"household_services\", \"leisure\", \"business_services\", \"resources\""),
        // a product with no price
        with("\"food\", \"materials\", \"consumer_goods\", \"utility\", \"housing\", \"household_services\", \"leisure\", \"business_services\", \"resources\", \"resource_deposit\""),
    ];
    for changed in cases {
        assert_ne!(changed, TWELVE);
        assert!(
            matches!(
                NationalGamePolicy::parse(&changed),
                Err(NationalGamePolicyError::Profile(ref what)) if what == "paying order"
            ),
            "{:?}",
            NationalGamePolicy::parse(&changed)
        );
    }
}

#[test]
fn bands_need_a_bottom_half() {
    let changed = TWELVE.replace(
        "private_owner_households_bps = 1000\n# The next 40% by earnings, the better-paid earning account (rule O17).\nnext_forty_households_bps = 4000",
        "private_owner_households_bps = 1000\nnext_forty_households_bps = 9000",
    );
    assert_ne!(changed, TWELVE);
    assert!(matches!(
        NationalGamePolicy::parse(&changed),
        Err(NationalGamePolicyError::Profile(_))
    ));
}

#[test]
fn schema_8_weights_split_consumer_goods_from_capital_and_leisure_from_services() {
    let policy = NationalGamePolicy::parse(TWELVE).expect("the twelve-trade fixture parses");
    let shipped = NationalGamePolicy::parse(SOURCE).expect("the shipped policy parses");
    // Ord order of the ten trades: capital 1, household services 7. Of the twelve: capital 1,
    // consumer goods 3, household services 8, leisure 9. Consumer goods took half of the old
    // capital weight, leisure a quarter of the old household-services weight, each rounded
    // down to 50; every other trade keeps its weight.
    let derive = |ten: &[u16]| -> Vec<u16> {
        assert_eq!(ten.len(), 10);
        let consumer = ten[1] / 2 / 50 * 50;
        let leisure = ten[7] / 4 / 50 * 50;
        vec![
            ten[0],
            ten[1] - consumer,
            ten[2],
            consumer,
            ten[3],
            ten[4],
            ten[5],
            ten[6],
            ten[7] - leisure,
            leisure,
            ten[8],
            ten[9],
        ]
    };
    assert_eq!(policy.counterparts.len(), shipped.counterparts.len());
    for (counterpart, profile) in &policy.counterparts {
        let ten = &shipped
            .counterparts
            .get(counterpart)
            .expect("the shipped policy holds the same counterpart")
            .function_weights_bps;
        assert_eq!(profile.function_weights_bps, derive(ten), "{counterpart:?}");
    }
    assert_eq!(
        policy.dependency.profile.function_weights_bps,
        derive(&shipped.dependency.profile.function_weights_bps)
    );
}

#[test]
fn consumer_goods_must_be_a_storable_good_and_leisure_a_period_service() {
    let goods = "kind = \"storable\"\ncargo_class = \"general\"\ngrams_per_unit = 5000\nopening_price_micros = 240000000";
    let as_service = TWELVE.replace(
        goods,
        "kind = \"service\"\ngrams_per_unit = 0\nopening_price_micros = 240000000",
    );
    assert_ne!(as_service, TWELVE);
    assert!(matches!(
        NationalGamePolicy::parse(&as_service),
        Err(NationalGamePolicyError::Profile(_))
    ));
    let leisure = "kind = \"service\"\ngrams_per_unit = 0\nopening_price_micros = 300000000";
    let as_good = TWELVE.replace(
        leisure,
        "kind = \"storable\"\ncargo_class = \"general\"\ngrams_per_unit = 5000\nopening_price_micros = 300000000",
    );
    assert_ne!(as_good, TWELVE);
    assert!(matches!(
        NationalGamePolicy::parse(&as_good),
        Err(NationalGamePolicyError::Profile(_))
    ));
}

// ---- Task 1 of stage 5: the keys of the rebuilt opening (schema 8) ----

fn expect_error(changed: &str, expected: NationalGamePolicyError) {
    assert_ne!(changed, TWELVE, "the mutation must change the input");
    assert_eq!(NationalGamePolicy::parse(changed), Err(expected));
}

#[test]
fn the_fixture_takes_the_fund_and_the_programs() {
    let policy = NationalGamePolicy::parse(TWELVE).expect("the schema 8 fixture");
    assert_eq!(policy.household_wants.len(), 0);
    assert_eq!(
        policy.fund,
        Some(GameFundPolicy {
            wage_tax_share_bps: 0,
            operating_income_tax_share_bps: 0,
            reserve_periods: 2,
        })
    );
    let keys: Vec<_> = policy.programs.iter().map(|p| p.key.as_str()).collect();
    assert_eq!(keys, ["laid_off", "no_earner", "residence"]);
    assert!(policy.programs.iter().all(|p| p.rank == 0));
    assert_eq!(
        policy.programs[0].terms,
        GameProgramTerms::AfterLayoff {
            wage_share_bps: 5_000,
            half_periods: 13
        }
    );
    assert_eq!(
        policy.programs[0].recipients,
        GameProgramRecipients::EarningOrResidenceAtOpening
    );
    assert_eq!(
        policy.programs[1].terms,
        GameProgramTerms::PerPerson {
            amount_per_person: Currency::from_micro_units(1_595_033_714)
        }
    );
    assert_eq!(
        policy.programs[1].recipients,
        GameProgramRecipients::NoEarnerAtOpening
    );
    assert_eq!(
        policy.programs[2].terms,
        GameProgramTerms::PerPersonByPlace {
            amounts: BTreeMap::new()
        }
    );
    assert_eq!(
        policy.programs[2].recipients,
        GameProgramRecipients::CollectiveResidenceAtOpening
    );
    assert_eq!(policy.luxury_scales.len(), 0);
}

#[test]
fn the_fixture_takes_the_places_and_the_markets() {
    let policy = NationalGamePolicy::parse(TWELVE).expect("the schema 8 fixture");
    assert_eq!(
        policy.place_services,
        ["household_services", "housing", "public_provision"]
    );
    assert_eq!(
        policy.map_basis,
        Some(GameMapBasis {
            food_labor_hours_per_batch: 16,
            food_output_units_per_batch: 16,
            food_units_per_person: 1,
            food_grams_per_unit: 14_000,
        })
    );
    let GameProcurement::ByProduct { import_bps } = &policy.markets.procurement else {
        panic!("schema 8 procurement is by product");
    };
    assert_eq!(import_bps.len(), 5);
    for (key, bps) in import_bps {
        assert_eq!(*bps, if key == "equipment" { 0 } else { 2_500 }, "{key}");
    }
    let canada = &policy.counterparts[&ForeignCounterpart::Canada];
    let export = canada.export_bps.as_ref().expect("export shares");
    assert_eq!(export.len(), 5);
    assert!(export.values().all(|bps| *bps == 2_500));
    assert!(policy
        .dependency
        .profile
        .export_bps
        .as_ref()
        .is_some_and(|rows| rows.len() == 5));
}

#[test]
fn the_fixture_takes_the_machines_and_the_handling() {
    let policy = NationalGamePolicy::parse(TWELVE).expect("the schema 8 fixture");
    let GameMachines::Workers {
        workers_per_machine,
        life_periods,
    } = &policy.equipment.machines
    else {
        panic!("schema 8 machines are by workers");
    };
    assert_eq!(workers_per_machine.len(), 11);
    assert_eq!(*life_periods, 100);
    assert_eq!(workers_per_machine[&EconomicFunction::Food], 4);
    assert_eq!(
        workers_per_machine[&EconomicFunction::HouseholdServices],
        40
    );
    assert_eq!(policy.handling_hours_per_unit, None);
    for (key, commodity) in &policy.commodities {
        let expected = matches!(key.as_str(), "food" | "materials")
            .then_some(GameHandling { hours: 1, units: 1 });
        assert_eq!(commodity.handling, expected, "{key}");
    }
    assert!(policy
        .recipes
        .values()
        .all(|r| r.margin_bps == Some(0) || r.output == "public_provision"));
    assert_eq!(
        policy.recipes[&EconomicFunction::PublicProvisioning].margin_bps,
        None
    );
}

#[test]
fn the_shipped_policy_keeps_its_arms() {
    let policy = NationalGamePolicy::parse(SOURCE).expect("the shipped policy");
    assert_eq!(policy.markets.procurement, GameProcurement::Single(2_500));
    assert_eq!(
        policy.equipment.machines,
        GameMachines::Batches {
            batches_per_unit_per_period: 40,
            service_batches_per_unit: 4_000,
            opening_remaining_service_bps: [2_500, 5_000, 7_500, 10_000],
        }
    );
    assert_eq!(policy.handling_hours_per_unit, Some(1));
    assert_eq!(policy.household_wants.len(), 0);
    assert_eq!(policy.fund, None);
    assert_eq!(policy.programs.len(), 0);
    assert_eq!(policy.luxury_scales.len(), 0);
    assert_eq!(policy.place_services.len(), 0);
    assert_eq!(policy.map_basis, None);
    assert!(policy.commodities.values().all(|c| c.handling.is_none()));
    assert!(policy.recipes.values().all(|r| r.margin_bps.is_none()));
    assert!(policy.counterparts.values().all(|c| c.export_bps.is_none()));
}

#[test]
fn builder_keys_are_refused_under_schema_7() {
    let at = |anchor: &str, add: &str| {
        let changed = SOURCE.replacen(anchor, &format!("{anchor}{add}"), 1);
        assert_ne!(changed, SOURCE, "{anchor}");
        changed
    };
    let cases = [
        at("[markets]\n", "import_bps = { food = 1 }\n"),
        at("[markets]\n", "place_services = [\"housing\"]\n"),
        at("[commodity.food]\n", "handling_hours = 1\nhandling_units = 1\n"),
        at("[process.food]\n", "margin_bps = 10\n"),
        at("[equipment]\n", "workers_per_machine = { food = 4 }\n"),
        at("[equipment]\n", "machine_life_periods = 100\n"),
        at("[counterpart.\"canada\"]\n", "export_bps = { food = 1 }\n"),
        format!("{SOURCE}\n[grain.basis]\nfood_labor_hours_per_batch = 16\nfood_output_units_per_batch = 16\nfood_units_per_person = 1\nfood_grams_per_unit = 14000\n"),
        format!("{SOURCE}\n[fund]\nevidence_class = \"Designed\"\nwage_tax_share_bps = 0\noperating_income_tax_share_bps = 0\nreserve_periods = 2\n"),
        format!("{SOURCE}\n[[programs]]\nkey = \"no_earner\"\nkind = \"per_person\"\nrank = 0\namount_per_person_micros = 1595033714\nrecipients = \"no_earner_at_opening\"\n"),
        at("[commodity.food]\n", "handling_units = 1\n"),
        at("[dependency]\n", "export_bps = { food = 1 }\n"),
        format!("{SOURCE}\n[luxury_scale]\nby_account = {{}}\n"),
        format!("{SOURCE}\n[[household_wants]]\ngood = \"food\"\ntier = \"comfort\"\nbasis = \"persons\"\nunits_per_basis = 1\n"),
    ];
    for changed in cases {
        assert_ne!(changed, SOURCE);
        assert!(
            matches!(
                NationalGamePolicy::parse(&changed),
                Err(NationalGamePolicyError::Shape)
            ),
            "{:?}",
            NationalGamePolicy::parse(&changed)
        );
    }
}

fn remove_between(text: &str, start: &str, end: &str) -> String {
    let from = text.find(start).expect("start");
    let to = from + text[from..].find(end).expect("end") + end.len();
    let mut out = text.to_owned();
    out.replace_range(from..to, "");
    out
}

#[test]
fn schema_8_needs_the_builder_keys() {
    let no_fund = remove_between(TWELVE, "[fund]", "reserve_periods = 2\n");
    let no_programs = remove_between(TWELVE, "[[programs]]", "amounts_micros = {}\n");
    let two_programs = remove_between(
        TWELVE,
        "[[programs]]\nkey = \"residence\"",
        "amounts_micros = {}\n",
    );
    let no_basis = remove_between(TWELVE, "[grain.basis]", "food_grams_per_unit = 14000\n");
    let no_import = remove_between(TWELVE, "import_bps = {", "}\n");
    let no_export = TWELVE.replacen(
        "export_bps = { food = 2500, resources = 2500, materials = 2500, consumer_goods = 2500, equipment = 2500 }\n",
        "",
        1,
    );
    let no_workers = remove_between(TWELVE, "workers_per_machine = {", "}\n");
    let no_life = TWELVE.replace("machine_life_periods = 100\n", "");
    let old_handling = TWELVE.replacen(
        "missing_peer_weight_per_establishment",
        "handling_hours_per_unit = 1\nmissing_peer_weight_per_establishment",
        1,
    );
    let old_procurement = TWELVE.replacen(
        "journey_timing",
        "foreign_procurement_bps = 2500\njourney_timing",
        1,
    );
    let old_machines = TWELVE.replacen(
        "[equipment]\n",
        "[equipment]\nbatches_per_unit_per_period = 40\n",
        1,
    );
    let no_handling = TWELVE.replacen("handling_hours = 1\nhandling_units = 1\n", "", 1);
    let no_margin = TWELVE.replacen("margin_bps = 0\n", "", 1);
    for changed in [
        no_fund,
        no_programs,
        two_programs,
        no_basis,
        no_import,
        no_export,
        no_workers,
        no_life,
        old_handling,
        old_procurement,
        old_machines,
        no_handling,
        no_margin,
    ] {
        expect_error(&changed, NationalGamePolicyError::Shape);
    }
}

fn profile(name: &str) -> NationalGamePolicyError {
    NationalGamePolicyError::Profile(name.to_owned())
}

#[test]
fn bad_builder_values_are_refused() {
    let cases: Vec<(String, NationalGamePolicyError)> = vec![
        (TWELVE.replacen("handling_hours = 1", "handling_hours = 0", 1), profile("handling")),
        (TWELVE.replacen("handling_units = 1", "handling_units = 0", 1), profile("handling")),
        (TWELVE.replacen("import_bps = { food = 2500", "import_bps = { food = 10001", 1), profile("import_bps")),
        (TWELVE.replacen("food = 2500, resources = 2500, materials = 2500, consumer_goods = 2500, equipment = 2500 }\n\n[", "food = 10001, resources = 2500, materials = 2500, consumer_goods = 2500, equipment = 2500 }\n\n[", 1), profile("export_bps")),
        (TWELVE.replacen("margin_bps = 0", "margin_bps = 100001", 1), profile("margin_bps")),
        (TWELVE.replacen("food = 4,", "food = 0,", 1), profile("workers_per_machine")),
        (TWELVE.replace("machine_life_periods = 100", "machine_life_periods = 0"), profile("machine_life_periods")),
        (TWELVE.replace("machine_life_periods = 100", "machine_life_periods = 10001"), profile("machine_life_periods")),
        (TWELVE.replace("wage_tax_share_bps = 0", "wage_tax_share_bps = 10001"), profile("fund")),
        (TWELVE.replace("reserve_periods = 2", "reserve_periods = 0"), profile("fund")),
        (TWELVE.replace("reserve_periods = 2", "reserve_periods = 17"), profile("fund")),
        (TWELVE.replace("key = \"residence\"", "key = \"other\""), profile("program")),
        (TWELVE.replace("key = \"residence\"", "key = \"no_earner\""), profile("program")),
        (TWELVE.replace("rank = 0\nwage_share_bps", "rank = 256\nwage_share_bps"), profile("program")),
        (TWELVE.replace("wage_share_bps = 5000", "wage_share_bps = 0"), profile("program")),
        (TWELVE.replace("wage_share_bps = 5000", "wage_share_bps = 10001"), profile("program")),
        (TWELVE.replace("half_periods = 13", "half_periods = 0"), profile("program")),
        (TWELVE.replace("half_periods = 13", "half_periods = 27"), profile("program")),
        (TWELVE.replace("amount_per_person_micros = 1595033714", "amount_per_person_micros = 0"), profile("program")),
        (TWELVE.replace("kind = \"per_person\"", "kind = \"after_layoff\""), profile("program")),
        (TWELVE.replace("recipients = \"no_earner_at_opening\"", "recipients = \"collective_residence_at_opening\""), profile("program")),
        (TWELVE.replace("food_labor_hours_per_batch = 16", "food_labor_hours_per_batch = 0"), profile("grain basis")),
        (TWELVE.replace("food_grams_per_unit = 14000", "food_grams_per_unit = 0"), profile("grain basis")),
        (TWELVE.replace("food_output_units_per_batch = 16", "food_output_units_per_batch = 0"), profile("grain basis")),
        (TWELVE.replace("food_units_per_person = 1", "food_units_per_person = 0"), profile("grain basis")),
        (TWELVE.replace("operating_income_tax_share_bps = 0", "operating_income_tax_share_bps = 10001"), profile("fund")),
        (TWELVE.replacen("food = 4, ", "", 1), profile("workers_per_machine")),
    ];
    for (index, (changed, expected)) in cases.into_iter().enumerate() {
        assert_ne!(changed, TWELVE, "case {index} must change the input");
        let got = NationalGamePolicy::parse(&changed);
        assert_eq!(got, Err(expected), "case {index}");
    }
    // A want's own refusals, on top of a valid want with its handling row.
    let with_handling = TWELVE.replacen(
        "[commodity.consumer_goods]\n",
        "[commodity.consumer_goods]\nhandling_hours = 1\nhandling_units = 1\n",
        1,
    );
    let want = |good: &str, units: u32| {
        format!(
            "{with_handling}\n[[household_wants]]\ngood = \"{good}\"\ntier = \"comfort\"\nbasis = \"persons\"\nunits_per_basis = {units}\n"
        )
    };
    NationalGamePolicy::parse(&want("consumer_goods", 1)).expect("the valid want");
    for (good, units) in [
        ("consumer_goods", 0),
        ("no_such", 1),
        ("resource_deposit", 1),
    ] {
        expect_error(
            &want(good, units),
            NationalGamePolicyError::HouseholdNeed(good.to_owned()),
        );
    }
    // A handling row on a good that no need or want names.
    let changed = TWELVE.replacen(
        "[commodity.consumer_goods]\n",
        "[commodity.consumer_goods]\nhandling_hours = 1\nhandling_units = 1\n",
        1,
    );
    expect_error(&changed, NationalGamePolicyError::Shape);
}

const WANTS: &str = "\n[[household_wants]]\ngood = \"leisure\"\ntier = \"luxury\"\nbasis = \"persons\"\nunits_per_basis = 2\n\n[[household_wants]]\ngood = \"consumer_goods\"\ntier = \"comfort\"\nbasis = \"households\"\nunits_per_basis = 1\n";

#[test]
fn a_want_is_read_in_tier_and_key_order() {
    // Consumer goods are a storable good the wants now name, so they take a handling row.
    let with_wants = TWELVE.replacen(
        "[commodity.consumer_goods]\n",
        "[commodity.consumer_goods]\nhandling_hours = 1\nhandling_units = 1\n",
        1,
    ) + WANTS;
    let policy = NationalGamePolicy::parse(&with_wants).expect("two wants");
    let wants: Vec<_> = policy
        .household_wants
        .iter()
        .map(|w| (w.tier, w.key.as_str(), w.units_per_basis))
        .collect();
    assert_eq!(
        wants,
        [
            (WantTier::Comfort, "consumer_goods", 1),
            (WantTier::Luxury, "leisure", 2)
        ]
    );
    // Without its handling row the wanted shop good is refused.
    expect_error(&(TWELVE.to_owned() + WANTS), NationalGamePolicyError::Shape);
    let equipment = TWELVE.to_owned()
        + "\n[[household_wants]]\ngood = \"equipment\"\ntier = \"comfort\"\nbasis = \"persons\"\nunits_per_basis = 1\n";
    expect_error(
        &equipment,
        NationalGamePolicyError::HouseholdNeed("equipment".to_owned()),
    );
    let twice = with_wants.clone()
        + &WANTS
            .replace("leisure", "consumer_goods")
            .replace("luxury", "comfort");
    expect_error(
        &twice,
        NationalGamePolicyError::HouseholdNeed("consumer_goods".to_owned()),
    );
}

#[test]
fn residence_amounts_and_luxury_scales_are_read() {
    let amounts = |entries: &str| {
        TWELVE.replace(
            "amounts_micros = {}",
            &format!("amounts_micros = {entries}"),
        )
    };
    let scales = |entries: &str| format!("{TWELVE}\n[luxury_scale]\nby_account = {entries}\n");
    let policy = NationalGamePolicy::parse(&amounts("{ \"26163\" = 700000000 }"))
        .expect("an amount for Wayne");
    assert_eq!(
        policy.programs[2].terms,
        GameProgramTerms::PerPersonByPlace {
            amounts: BTreeMap::from([(
                babylon_kernel::geography::CountyGeoid::try_from("26163").expect("county"),
                Currency::from_micro_units(700_000_000)
            )])
        }
    );
    expect_error(
        &amounts("{ \"99999\" = 700000000 }"),
        NationalGamePolicyError::Location,
    );
    expect_error(&amounts("{ \"26163\" = 0 }"), profile("program"));
    let policy =
        NationalGamePolicy::parse(&scales("{ \"26163:earning-owner\" = 12500 }")).expect("a scale");
    assert_eq!(
        policy.luxury_scales,
        [GameLuxuryScale {
            place: "26163".to_owned(),
            key: HouseholdBudgetKey::EarningOwner,
            bps: 12_500
        }]
    );
    expect_error(
        &scales("{ \"26163:earning-owner\" = 10000 }"),
        profile("luxury_scale"),
    );
    expect_error(
        &scales("{ \"26163:earning-owner\" = 1000001 }"),
        profile("luxury_scale"),
    );
    expect_error(
        &scales("{ \"26163:no-such-key\" = 12500 }"),
        NationalGamePolicyError::Location,
    );
    let policy = NationalGamePolicy::parse(&scales(
        "{ \"01073/below:earning-owner\" = 12500, \"canada:pooled-external\" = 20000 }",
    ))
    .expect("a part's label");
    let places: Vec<_> = policy
        .luxury_scales
        .iter()
        .map(|s| s.place.as_str())
        .collect();
    assert_eq!(places, ["01073/below", "canada"]);
    expect_error(
        &scales("{ \"01073/north:earning-owner\" = 12500 }"),
        NationalGamePolicyError::Location,
    );
    let services = TWELVE.replace(
        "place_services = [\"household_services\", \"housing\", \"public_provision\"]",
        "place_services = [\"food\"]",
    );
    expect_error(&services, profile("place_services"));
    let twice = TWELVE.replace(
        "place_services = [\"household_services\", \"housing\", \"public_provision\"]",
        "place_services = [\"housing\", \"housing\"]",
    );
    expect_error(&twice, profile("place_services"));
}
