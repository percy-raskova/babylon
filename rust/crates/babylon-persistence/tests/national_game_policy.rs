use babylon_kernel::economic_identity::{EconomicFunction, QcewOwnership};
use babylon_kernel::economic_location::{EconomicLocation, ForeignCounterpart};
use babylon_material_circuit::{CommodityKind, HouseholdNeedBasis, ServiceStage};
use babylon_persistence::national_economy::{
    source_workplace_target, NationalGamePolicy, NationalGamePolicyError,
};

const SOURCE: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../content/scenarios/national/defines.toml"
));

#[test]
fn captured_aid_requires_positive_cash_terms_before_opening_accounts() {
    let policy = NationalGamePolicy::parse(SOURCE).unwrap();
    assert!(policy.aid.gift_cash_micros_per_unit > 0);
    for amount in [0_i128, -1] {
        let changed = SOURCE.replace(
            "gift_cash_micros_per_unit = 100000",
            &format!("gift_cash_micros_per_unit = {amount}"),
        );
        assert_ne!(changed, SOURCE);
        assert_eq!(
            NationalGamePolicy::parse(&changed),
            Err(NationalGamePolicyError::Shape)
        );
    }
}

#[test]
fn household_time_policy_is_captured_separately_from_wages_and_population() {
    let policy = NationalGamePolicy::parse(SOURCE).unwrap();
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
    let captured = NationalGamePolicy::from_captured_bytes(SOURCE.as_bytes()).unwrap();
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
    let policy = NationalGamePolicy::parse(SOURCE).unwrap();
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
            .unwrap()
            .basis,
        HouseholdNeedBasis::Persons
    );
    assert_eq!(
        policy
            .household_needs
            .iter()
            .find(|n| n.key == "housing")
            .unwrap()
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
    let policy = NationalGamePolicy::parse(SOURCE).unwrap();
    assert_eq!(policy.counterparts.len(), 12);
    for counterpart in ForeignCounterpart::ALL {
        let profile = &policy.counterparts[&counterpart];
        let counts = profile.opening_counts(1_000).unwrap();
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

    let price = policy.commodities["food"].price.as_ref().unwrap();
    let scaled = price.scaled(4_000).unwrap();
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
    let location: EconomicLocation = "county:26163".parse().unwrap();
    let private =
        source_workplace_target(location, EconomicFunction::Food, QcewOwnership::Private, 7)
            .unwrap();
    let public = source_workplace_target(
        location,
        EconomicFunction::Food,
        QcewOwnership::LocalGovernment,
        7,
    )
    .unwrap();
    let other = source_workplace_target(
        location,
        EconomicFunction::Manufacturing,
        QcewOwnership::Private,
        7,
    )
    .unwrap();
    assert_ne!(private.site_id, public.site_id);
    assert_ne!(private.site_id, other.site_id);
    assert!(private.workplace.canonical_bytes().is_ok());
    assert!(public.workplace.canonical_bytes().is_ok());
    assert!(other.workplace.canonical_bytes().is_ok());
    assert_eq!(private.allocation_weight, 7);
    assert_eq!(private.location, location);
    assert_eq!(
        private,
        source_workplace_target(location, EconomicFunction::Food, QcewOwnership::Private, 7)
            .unwrap()
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
    let parsed = NationalGamePolicy::parse(&disabled).unwrap();
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
fn cargo_eligibility_is_captured_and_cannot_be_inferred_from_mass() {
    use babylon_persistence::national_transport::CargoClass;
    let policy = NationalGamePolicy::parse(SOURCE).unwrap();
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
            .unwrap()
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
