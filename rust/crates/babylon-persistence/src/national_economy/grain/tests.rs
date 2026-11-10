//! Finite membership and real-opening contracts.
use super::build;
use super::build::Screen;
use super::{
    CatchmentId, CatchmentReason, ContributionDestination, FinancialDomainId,
    NationalGenerationWitness, NationalGrainError, OpeningProductiveEndowment,
    RepresentativeHouseholdKey, ReservePosition,
};
use crate::economic_catalog::CapturedEconomicCatalog;
use crate::economic_catalog::CompiledEconomicOpening;
use crate::economic_catalog::EconomicOpening;
use crate::national_economy::{NationalAidCapture, NationalGamePolicy};
use crate::national_household_allocation::HouseholdBudgetKey;
use crate::national_resident_allocation::{
    self, AssignedResidentWorkplace, ResidentAttendanceMode, ResidentWorkplaceAllocation,
};
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::{EconomicFunction, QcewOwnership};
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::geography::CountyGeoid;
use babylon_kernel::replay::ReplaySeed;
use babylon_kernel::replay::ReplaySessionId;
use babylon_material_circuit::AccountId;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::replay_session::ReplayCommitDisposition;
use std::cmp::Ordering;
use std::collections::{BTreeMap, BTreeSet};
fn row(county: &str, demand: u128) -> Screen {
    Screen {
        county: CountyGeoid::try_from(county).expect("valid county"),
        population: 1_000_000,
        demand,
        hours: 0,
        capacity: 20_000_000_000,
    }
}
#[test]
fn capacity_refinement_preserves_independent_twenty_billion_gram_lanes() {
    let rows = vec![row("26001", 1_000_000), row("26003", 1_000_000)];
    let bins = build::refine(rows, 1, 1, 14_000).expect("finite screening");
    assert_eq!(
        bins.len(),
        2,
        "28 billion grams cannot cross one 20 billion gram lane"
    );
    for bin in bins {
        assert_eq!(
            build::bound(&bin, 1, 1, 14_000).expect("bound").3,
            14_000_000_000,
            "individual lanes remain sufficient"
        );
    }
}
#[test]
fn existing_excess_is_kept_as_its_own_scarce_singleton() {
    let bins = build::refine(vec![row("26001", 2_000_000), row("26003", 1)], 1, 1, 14_000)
        .expect("finite screening");
    assert_eq!(
        bins.len(),
        2,
        "pre-existing deficit cannot absorb another county"
    );
    assert_eq!(
        bins[0][0].county,
        CountyGeoid::try_from("26001").expect("county"),
        "scarce county retained"
    );
}
#[test]
fn insertion_order_cannot_change_subdivisions_or_membership_identity() {
    let rows = vec![
        row("26001", 500_000),
        row("26003", 500_000),
        row("26005", 500_000),
        row("26007", 500_000),
    ];
    let forward = build::refine(rows.clone(), 1, 1, 14_000).expect("screen");
    let reverse = build::refine(rows.into_iter().rev().collect(), 1, 1, 14_000).expect("screen");
    assert_eq!(
        forward, reverse,
        "canonical first-fit is insertion-order independent"
    );
    let cells: Vec<_> = forward
        .into_iter()
        .map(|bin| {
            build::cell(
                &bin,
                *b"26",
                *b"261",
                Some(20_000_000_000),
                CatchmentReason::CapacitySubdivision,
                [1; 32],
                (1, 1, 14_000),
            )
            .expect("cell")
        })
        .collect();
    assert_eq!(cells.len(), 2, "two non-singleton subdivisions");
    assert_ne!(
        cells[0].id, cells[1].id,
        "membership bytes distinguish same-state FAF subdivisions"
    );
}
#[test]
fn same_hub_positions_have_independent_budget_and_principal_keys() {
    let location =
        EconomicLocation::domestic_county(CountyGeoid::try_from("26001").expect("county"))
            .expect("location");
    let catchment = CatchmentId([1; 32]);
    let a = FinancialDomainId {
        location,
        representative: Some((catchment, ReservePosition::BelowCellReserveRate)),
    };
    let b = FinancialDomainId {
        location,
        representative: Some((catchment, ReservePosition::AboveCellReserveRate)),
    };
    assert_ne!(
        a.public_account(),
        b.public_account(),
        "same geography must not merge public budgets"
    );
    let principal = |position, budget| {
        super::super::identity::representative_household(RepresentativeHouseholdKey {
            catchment,
            position,
            budget,
        })
        .0
    };
    assert_ne!(
        principal(
            ReservePosition::BelowCellReserveRate,
            HouseholdBudgetKey::EarningNonowner
        ),
        principal(
            ReservePosition::AboveCellReserveRate,
            HouseholdBudgetKey::EarningNonowner
        ),
        "independent pantry and cash owners"
    );
    assert_ne!(
        principal(
            ReservePosition::BelowCellReserveRate,
            HouseholdBudgetKey::EarningOwner
        ),
        principal(
            ReservePosition::BelowCellReserveRate,
            HouseholdBudgetKey::EarningNonowner
        ),
        "owner exposure never merges"
    );
}

fn policy() -> NationalGamePolicy {
    NationalGamePolicy::parse(include_str!(
        "../../../../../../content/scenarios/national/defines.toml"
    ))
    .expect("captured policy")
}
#[test]
fn productive_floors_are_summed_before_folding() {
    let mut policy = policy();
    policy
        .recipes
        .get_mut(&EconomicFunction::Food)
        .expect("food")
        .labor_hours_per_batch = 300;
    let mut endowment = OpeningProductiveEndowment::default();
    for county in ["26001", "26003"] {
        let location =
            EconomicLocation::domestic_county(CountyGeoid::try_from(county).expect("county"))
                .expect("location");
        let target = super::super::source_workplace_target(
            location,
            EconomicFunction::Food,
            QcewOwnership::Private,
            1,
        )
        .expect("target");
        let member = national_resident_allocation::member(
            &target,
            ResidentAttendanceMode::Employee,
            super::super::household_principal(location, HouseholdBudgetKey::EarningNonowner),
            1,
            0,
        )
        .expect("member");
        let row = AssignedResidentWorkplace {
            target,
            weight: None,
            members: vec![member],
        };
        endowment
            .accumulate(&OpeningProductiveEndowment::source(&row, &policy).expect("source"))
            .expect("sum");
    }
    assert_eq!(
        endowment.batches, 0,
        "two source floors of 160/300 stay zero"
    );
    assert_eq!(
        endowment.equipment_units, 0,
        "aggregate hours cannot invent equipment"
    );
    assert_eq!(
        2 * policy.work_hours_per_person / 300,
        1,
        "floor after sum creates a free batch"
    );
}
#[test]
#[allow(
    clippy::too_many_lines,
    reason = "The single real-opening fixture verifies source controls through compilation and one atomic replay period"
)]
fn real_opening_preserves_source_controls_and_separates_same_hub_domains() {
    use babylon_material_circuit::CircuitAccounting;
    let policy = policy();
    let opening = super::super::build_national_opening(
        crate::national_counties::national_county_reference().expect("counties"),
        crate::national_cohorts::national_cohort_reference().expect("cohorts"),
        crate::national_resident_workforce::national_resident_workforce_reference()
            .expect("residents"),
        crate::national_households::national_household_reference().expect("households"),
        crate::world_reference::world_reference().expect("world"),
        crate::national_transport::national_transport_reference().expect("transport"),
        super::super::NationalOpeningPolicy {
            policy: &policy,
            source_hash: policy.source_digest,
        },
    )
    .expect("real opening");
    let witness = &opening.representation;
    assert_final_membership(witness);
    assert_eq!(
        witness.counties.len(),
        3144,
        "complete source county roster"
    );
    assert_eq!(
        witness
            .catchments
            .iter()
            .map(|c| c.members.len())
            .sum::<usize>(),
        3144,
        "each county contributes once"
    );
    assert_eq!(
        witness
            .counties
            .iter()
            .map(|c| c.controls.population)
            .sum::<u64>(),
        334_922_499,
        "population preserved"
    );
    assert!(
        opening.opening.sites.len() < 60_634,
        "fewer actual live sites"
    );
    assert!(
        witness.source_incidence.len() > opening.opening.sites.len(),
        "provenance is not another runtime"
    );
    let households: BTreeMap<_, _> = opening
        .opening
        .households
        .iter()
        .map(|h| (h.principal_id, h))
        .collect();
    let mut totals = BTreeMap::<_, (u64, u64, u64)>::new();
    for row in &witness.household_incidence {
        let t = totals.entry(row.destination).or_default();
        t.0 += row.margins.persons;
        t.1 += row.margins.households;
        t.2 += row.time.eligible_16_plus;
    }
    for (principal, (persons, count, eligible)) in totals {
        let row = households[&principal];
        let children: Vec<_> = opening
            .aid
            .children
            .iter()
            .filter(|c| c.parent == principal)
            .collect();
        assert_eq!(
            row.persons + children.iter().map(|c| c.persons).sum::<u64>(),
            persons,
            "person pushforward"
        );
        assert_eq!(
            row.households + children.iter().map(|c| c.households).sum::<u64>(),
            count,
            "household pushforward"
        );
        let time = opening
            .opening
            .policies
            .household_time_policy
            .iter()
            .find(|t| t.principal_id == principal)
            .expect("time");
        assert_eq!(
            time.eligible_persons + children.iter().map(|c| c.eligible).sum::<u64>(),
            eligible,
            "explicit eligibility avoids hub-population inference"
        );
    }
    for child in &opening.aid.children {
        assert_eq!(
            households[&child.principal].persons, child.persons,
            "protected child identity"
        );
    }
    let taxes: BTreeMap<_, _> = opening
        .opening
        .institutions
        .taxes
        .iter()
        .map(|t| (t.payer, t.public_recipient))
        .collect();
    let mut hubs = BTreeMap::<_, BTreeSet<_>>::new();
    for h in &opening.opening.households {
        hubs.entry(h.location)
            .or_default()
            .insert(taxes[&AccountId::Household(h.principal_id)]);
    }
    assert!(
        hubs.values().any(|domains| domains.len() > 1),
        "same physical hub retains independent provisioning budgets"
    );
    let mut compiled = opening
        .opening
        .compile()
        .expect("ordinary compiler admits coarse roster");
    let CircuitAccounting::Monetary(economy) = &compiled.state.accounting else {
        panic!("monetary opening")
    };
    for h in &opening.opening.households {
        assert_eq!(
            economy
                .book
                .cash(AccountId::Household(h.principal_id))
                .expect("own account"),
            h.opening_cash,
            "separate balances"
        );
    }
    assert_independent_balances(&opening.opening, &mut compiled);
    eprintln!("grain census: cells={} protected={} special={} source_sites={} sites={} households={} members={} routes={} service_connections={}",witness.catchments.len(),witness.catchments.iter().filter(|c|c.reason==CatchmentReason::Protected).count(),witness.catchments.iter().filter(|c|matches!(c.reason,CatchmentReason::SpecialAccess|CatchmentReason::NotSingleRoadAccess)).count(),witness.source_incidence.len(),opening.opening.sites.len(),opening.opening.households.len(),opening.opening.staffing.iter().map(|s|s.members.len()).sum::<usize>(),opening.opening.logistics.supplier_routes.len(),opening.opening.policies.service_connections.len());
    let captured = CapturedEconomicCatalog::capture(
        crate::economic_catalog::national_catalog_input(),
        Some(&opening.opening),
    )
    .expect("regenerated opening matches source capture");
    assert_eq!(
        captured.national_generation(),
        Some(witness),
        "authenticated source regeneration reproduces witness"
    );
    let foundation = captured
        .create_foundation(
            ReplaySessionId::try_from("grain-live-period").expect("session identity"),
            ReplaySeed::new(319),
        )
        .expect("ordinary replay foundation");
    let mut session = foundation.into_session().expect("replay session");
    let actions =
        OrderedPracticeActionBatch::empty(session.graph_session().session_identity().clone(), 1)
            .expect("empty practice batch");
    let next = session
        .prepare_advance(&actions)
        .expect("ordinary coarse replay period");
    assert_eq!(
        session.completed_tick(),
        0,
        "detached advance has not published"
    );
    session
        .commit_prepared_and_publish(&mut CollectingSink::default(), next, |_, _| {
            Ok::<_, ()>(ReplayCommitDisposition::Committed)
        })
        .expect("publish atomic period");
    assert_eq!(
        session.completed_tick(),
        1,
        "real generated roster advances through staffing and material phases"
    );
}

fn assert_independent_balances(opening: &EconomicOpening, compiled: &mut CompiledEconomicOpening) {
    use babylon_material_circuit::{CashTransferPurpose, CircuitAccounting, MonetaryError};
    let taxes: BTreeMap<_, _> = opening
        .institutions
        .taxes
        .iter()
        .map(|t| (t.payer, t.public_recipient))
        .collect();
    let mut by_location = BTreeMap::<_, Vec<_>>::new();
    for row in &opening.households {
        by_location.entry(row.location).or_default().push(row);
    }
    let pair = by_location
        .values()
        .find_map(|rows| {
            let first = rows.first()?;
            rows.iter()
                .find(|other| {
                    taxes[&AccountId::Household(first.principal_id)]
                        != taxes[&AccountId::Household(other.principal_id)]
                })
                .map(|other| (*first, *other))
        })
        .expect("two real same-hub reserve positions");
    let CircuitAccounting::Monetary(economy) = &mut compiled.state.accounting else {
        panic!("funded accounts")
    };
    for (sender, recipient) in [
        (
            AccountId::Household(pair.0.principal_id),
            AccountId::Household(pair.1.principal_id),
        ),
        (
            AccountId::Public(taxes[&AccountId::Household(pair.0.principal_id)]),
            AccountId::Public(taxes[&AccountId::Household(pair.1.principal_id)]),
        ),
    ] {
        let before = economy.book.snapshot();
        let excessive = Currency::from_micro_units(
            economy
                .book
                .cash(sender)
                .expect("sender cash")
                .micro_units()
                + 1,
        );
        assert_eq!(
            economy.book.transfer_cash(
                sender,
                recipient,
                excessive,
                CashTransferPurpose::HouseholdTransfer
            ),
            Err(MonetaryError::InsufficientCash),
            "a co-located account cannot fund this sender"
        );
        assert_eq!(
            economy.book.snapshot(),
            before,
            "failed transfer cannot change either budget"
        );
    }
    let recurring = economy
        .recurring
        .as_ref()
        .expect("recurring household needs");
    for household in [pair.0, pair.1] {
        for stock in &household.opening_stock {
            let actual = recurring
                .household_stocks
                .iter()
                .find(|s| {
                    s.principal_id == household.principal_id
                        && s.good_id == stock.amount.good_id
                        && s.unit_id == stock.amount.unit_id
                })
                .expect("separately owned pantry");
            assert_eq!(
                actual.quantity, stock.amount.quantity,
                "one pantry per actual household principal"
            );
        }
    }
}
#[test]
fn unsupported_generation_and_duplicate_protection_refuse_at_policy_admission() {
    let source = include_str!("../../../../../../content/scenarios/national/defines.toml");
    assert!(
        NationalGamePolicy::parse(
            &source.replace("state_faf_reserve_positions", "unknown_generation")
        )
        .is_err(),
        "unsupported generation has no compatibility mode"
    );
    assert!(
        NationalGamePolicy::parse(&source.replace(
            "[\"17031\", \"26163\"]",
            "[\"17031\", \"17031\", \"26163\"]"
        ))
        .is_err(),
        "protected contributions cannot overlap"
    );
}

fn assert_final_membership(witness: &NationalGenerationWitness) {
    let controls: BTreeMap<_, _> = witness
        .counties
        .iter()
        .map(|c| (c.controls.county, c))
        .collect();
    for cell in &witness.catchments {
        let hub = cell
            .members
            .iter()
            .min_by_key(|c| (std::cmp::Reverse(controls[c].controls.population), **c))
            .expect("nonempty final cell");
        assert_eq!(
            *hub, cell.key.hub,
            "hub selected from final real county membership"
        );
        let reserve: u128 = cell
            .members
            .iter()
            .map(|c| u128::from(controls[c].controls.reserve))
            .sum();
        let force: u128 = cell
            .members
            .iter()
            .map(|c| {
                u128::from(controls[c].controls.employed) + u128::from(controls[c].controls.reserve)
            })
            .sum();
        for county in &cell.members {
            let row = controls[county];
            if let ContributionDestination::Representative {
                catchment,
                position,
            } = row.destination
            {
                assert_eq!(catchment, cell.id, "one final cell assignment");
                let county_force =
                    u128::from(row.controls.employed) + u128::from(row.controls.reserve);
                let expected = if county_force == 0 {
                    ReservePosition::NoLaborForce
                } else {
                    match (u128::from(row.controls.reserve) * force).cmp(&(reserve * county_force))
                    {
                        Ordering::Less => ReservePosition::BelowCellReserveRate,
                        Ordering::Equal => ReservePosition::AtCellReserveRate,
                        Ordering::Greater => ReservePosition::AboveCellReserveRate,
                    }
                };
                assert_eq!(
                    position, expected,
                    "reserve labels use final refined membership"
                );
            }
        }
        if matches!(
            cell.reason,
            CatchmentReason::FitsCapturedHubAccess | CatchmentReason::CapacitySubdivision
        ) {
            assert!(
                cell.essential_import_grams <= cell.capacity_grams.expect("finite local lane"),
                "no provable new essential import obstruction"
            );
        }
        if matches!(
            cell.reason,
            CatchmentReason::Protected
                | CatchmentReason::SpecialAccess
                | CatchmentReason::NotSingleRoadAccess
                | CatchmentReason::PreExistingEssentialAccessDeficit
        ) {
            assert_eq!(
                cell.members.len(),
                1,
                "protected, special and pre-existing scarce cells stay singleton"
            );
        }
    }
}
#[test]
fn incomplete_county_membership_is_refused_before_source_expansion() {
    let counties = crate::national_counties::national_county_reference().expect("counties");
    let policy = policy();
    let budgets = crate::national_household_allocation::allocate_households(
        counties,
        crate::national_households::national_household_reference().expect("households"),
        crate::national_resident_workforce::national_resident_workforce_reference()
            .expect("classes"),
        policy.households.private_owner_households_bps,
    )
    .expect("source household allocation");
    let source = ResidentWorkplaceAllocation {
        county_source_sha256: counties.artifact_sha256(),
        cohort_source_sha256: [1; 32],
        function_mapping_sha256: [2; 32],
        classes_source_sha256: [3; 32],
        household_source_sha256: budgets.household_source_sha256(),
        workplaces: vec![],
        counties: vec![],
    };
    assert_eq!(
        build::capture_membership(
            counties,
            crate::national_transport::national_transport_reference().expect("transport"),
            &source,
            &budgets,
            &NationalAidCapture::default(),
            &policy
        ),
        Err(NationalGrainError::IncompleteCountyMembership),
        "missing source counties never become zero-demand contributions"
    );
}
