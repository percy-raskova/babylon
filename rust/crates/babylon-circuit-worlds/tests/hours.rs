//! The runner's ledger of hours: the pinned figures of the quiet world, the laws every period keeps, both
//! shocks, work elsewhere, and the rules.

use babylon_circuit_worlds::{
    Household, HouseholdHours, Kind, Lasts, MovedBy, PeriodHours, PeriodResult, Place, PlaceHours,
    Places, Runner, Scale, Shock, Workplace, World,
};
use babylon_material_circuit::AdjustmentRule::{
    self, GoodsStepDown, HiringWithinMeans, OwnerRestart, RestingPrice, SeekingInPlace,
    StopWithoutPay,
};
use babylon_material_circuit::MemberLaborUseReceipt;
use std::error::Error;

type TestResult = Result<(), Box<dyn Error>>;

const MICROS: u128 = 1_000_000;

fn scene_with_hours() -> Result<Runner, Box<dyn Error>> {
    Ok(Runner::open_world_with_hours(&World::scene())?)
}

fn hours_of(result: &PeriodResult) -> Result<&PeriodHours, Box<dyn Error>> {
    result.hours.as_ref().ok_or_else(|| "no hours".into())
}

fn workplace(place: Place, kind: Kind) -> Workplace {
    Workplace { place, kind }
}

/// Both ledgers' law, the direct hours as given, and each place's identity.
fn check_period(result: &PeriodResult) -> TestResult {
    let hours = hours_of(result)?;
    let period = result.period;
    for totals in [&hours.hours, &hours.opening_units] {
        assert_eq!(
            totals.opening + totals.direct,
            totals.closing + totals.released,
            "period {period}: the law"
        );
    }
    let given: u128 = hours
        .households
        .iter()
        .map(|(_, h)| u128::from(h.given))
        .sum();
    assert_eq!(
        hours.hours.direct,
        MICROS * given,
        "period {period}: direct is given"
    );
    let workplace_given: u128 = hours
        .workplaces
        .iter()
        .map(|(_, w)| u128::from(w.given))
        .sum();
    assert_eq!(
        given, workplace_given,
        "period {period}: given by household and by site"
    );
    for (place, p) in &hours.places {
        assert_eq!(
            p.back_micro_hours + p.held_closing + p.left_micro_hours,
            p.given_micro_hours + p.held_opening,
            "period {period} {place:?}: the place's identity"
        );
    }
    Ok(())
}

fn place_a(hours: &PeriodHours) -> Result<&PlaceHours, Box<dyn Error>> {
    hours
        .places
        .iter()
        .find(|(place, _)| *place == Place::A)
        .map(|(_, p)| p)
        .ok_or_else(|| "no place A".into())
}

fn household_of(
    hours: &PeriodHours,
    household: Household,
) -> Result<&HouseholdHours, Box<dyn Error>> {
    hours
        .household(household)
        .ok_or_else(|| "no household".into())
}

#[test]
fn the_scene_s_catalog_folds_its_first_period() -> TestResult {
    let mut runner = scene_with_hours()?;
    let result = runner.step()?;
    assert!(result.hours.is_some());
    Ok(())
}

#[test]
fn the_quiet_world_climbs_as_pinned() -> TestResult {
    let mut runner = scene_with_hours()?;
    for _ in 0..12 {
        runner.step()?;
    }
    for result in runner.history() {
        let hours = hours_of(result)?;
        let p = result.period;
        let a = place_a(hours)?;
        assert_eq!(a.given_micro_hours, 240_000_000, "period {p}");
        if p <= 11 {
            let shift = u32::try_from(p - 1)?;
            assert_eq!(
                a.back_micro_hours,
                240_000_000 - (80_000_000_u128 >> shift),
                "period {p}"
            );
        } else {
            assert!(a.back_micro_hours < 240_000_000, "period {p}");
        }
        for (household, h) in &hours.households {
            let expected = match household {
                Household::Workers(_) => 10 * household.opening_persons(),
                Household::Owner(_) | Household::Supported(_) => 0,
            };
            assert_eq!(h.given, expected, "period {p} {household:?}");
        }
    }
    let first = hours_of(&runner.history()[0])?;
    let back = |household: Household| -> Result<u128, Box<dyn Error>> {
        Ok(household_of(first, household)?.back_micro_hours)
    };
    let a = Place::A;
    assert_eq!(
        back(Household::Workers(workplace(a, Kind::Utility)))?,
        48 * MICROS
    );
    for kind in [Kind::Farm, Kind::Clinic, Kind::Shop] {
        assert_eq!(
            back(Household::Workers(workplace(a, kind)))?,
            16 * MICROS,
            "{kind:?}"
        );
    }
    assert_eq!(back(Household::Owner(a))?, 32 * MICROS);
    assert_eq!(back(Household::Supported(a))?, 32 * MICROS);
    Ok(())
}

#[test]
fn a_unit_holds_its_recipe_s_hours() -> TestResult {
    let mut runner = scene_with_hours()?;
    for _ in 0..12 {
        runner.step()?;
    }
    for (index, result) in runner.history().iter().enumerate() {
        let hours = hours_of(result)?;
        let at = |kind: Kind| -> Result<_, Box<dyn Error>> {
            hours
                .workplace(workplace(Place::A, kind))
                .copied()
                .ok_or_else(|| "no workplace".into())
        };
        let utility = at(Kind::Utility)?;
        assert!(
            utility.handed_units > 0,
            "utility, period {}",
            result.period
        );
        assert_eq!(
            utility.handed_micro_hours,
            u128::from(utility.handed_units) * MICROS
        );
        let clinic = at(Kind::Clinic)?;
        assert!(clinic.handed_units > 0, "clinic, period {}", result.period);
        assert_eq!(
            clinic.handed_micro_hours,
            u128::from(clinic.handed_units) * 2 * MICROS
        );
        let farm = at(Kind::Farm)?;
        assert!(farm.made_units > 0, "farm, period {}", result.period);
        assert_eq!(
            farm.made_micro_hours,
            u128::from(farm.made_units) * 2 * MICROS
        );
        if index == 0 {
            let shop = at(Kind::Shop)?;
            assert!(shop.handed_units > 0);
            assert_eq!(
                shop.handed_micro_hours,
                u128::from(shop.handed_units) * MICROS
            );
            assert_eq!(
                shop.handed_opening_micro_units,
                u128::from(shop.handed_units) * MICROS
            );
        }
    }
    Ok(())
}

#[derive(Clone, Copy)]
enum Counted {
    HomesOfA,
    SitesOfA,
}

/// Place A's moves of the period: the quantity, and the micro-units from the opening, of each move that
/// reaches a home of place A (`Counted::HomesOfA`) or that leaves a site of place A (`Counted::SitesOfA`).
fn opening_share(result: &PeriodResult, counted: Counted) -> Result<(u128, u128), Box<dyn Error>> {
    let hours = hours_of(result)?;
    let receipts = &result.receipts;
    let mut quantity = 0_u128;
    let mut opening = 0_u128;
    for m in &hours.moves {
        let (home, site) = match m.moved_by {
            MovedBy::LocalFulfillment(i) => {
                let r = receipts.local_fulfillments.get(i).ok_or("receipt")?;
                (
                    Household::from_principal(r.demand_principal_id),
                    r.retailer_site_id,
                )
            }
            MovedBy::LocalTransfer(i) => (
                None,
                receipts
                    .local_transfers
                    .get(i)
                    .ok_or("receipt")?
                    .supplier_site_id,
            ),
            MovedBy::ServicePerformance(i) => (
                None,
                receipts
                    .service_performance
                    .get(i)
                    .ok_or("receipt")?
                    .provider_site_id,
            ),
        };
        let counts = match counted {
            Counted::HomesOfA => home.is_some_and(|h| h.place() == Place::A),
            Counted::SitesOfA => Workplace::from_site(site).is_some_and(|w| w.place == Place::A),
        };
        if counts {
            quantity += u128::from(m.quantity);
            opening += m.opening_micro_units;
        }
    }
    Ok((quantity, opening))
}

#[test]
fn the_opening_share_halves() -> TestResult {
    let mut runner = scene_with_hours()?;
    for _ in 0..4 {
        runner.step()?;
    }
    let homes = [1_u128, 2, 4, 8];
    let all = [4_u128, 8, 16, 32];
    for (index, result) in runner.history().iter().enumerate() {
        let (quantity, opening) = opening_share(result, Counted::HomesOfA)?;
        assert!(quantity > 0);
        assert_eq!(
            opening * homes[index],
            quantity * MICROS,
            "homes, period {}",
            result.period
        );
        let (quantity, opening) = opening_share(result, Counted::SitesOfA)?;
        assert!(quantity > 0);
        assert_eq!(
            opening * all[index],
            quantity * MICROS,
            "all moves, period {}",
            result.period
        );
    }
    Ok(())
}

fn shocked(shocks: &[(Shock, Places)]) -> Result<Runner, Box<dyn Error>> {
    let mut runner = scene_with_hours()?;
    for (shock, places) in shocks {
        runner.strike(*shock, *places, Lasts::UntilLifted)?;
    }
    Ok(runner)
}

/// Pinned from a real period: with the power cut in place A, household `[20; 32]` in period 6 bought 3 units of
/// food as a Luxury want, beyond its need of 8. The engine does not add a want's units to the pantry (they are
/// used where they are bought), so the ledger must release them as consumption, not credit them to the
/// household's stock. Before that mend the period was refused as `household_consumption`.
#[test]
fn a_want_of_food_is_used_where_it_is_bought() -> TestResult {
    let mut runner = shocked(&[(Shock::PowerCut, Places::A)])?;
    for _ in 0..8 {
        check_period(runner.step()?)?;
    }
    // The pin is only a pin if period 6 holds a want that bought something.
    let period_six = runner.history().get(5).ok_or("no period 6")?;
    assert!(
        period_six
            .receipts
            .household_wants
            .iter()
            .any(|want| want.bought_quantity > 0),
        "period 6 no longer holds a bought want"
    );
    Ok(())
}

#[test]
fn every_period_keeps_both_laws_and_the_place_identity() -> TestResult {
    let mut quiet = scene_with_hours()?;
    for _ in 0..34 {
        check_period(quiet.step()?)?;
    }
    let cases: [&[(Shock, Places)]; 5] = [
        &[(Shock::HarvestFails, Places::A)],
        &[(Shock::HarvestFails, Places::Both)],
        &[(Shock::PowerCut, Places::A)],
        &[(Shock::PowerCut, Places::Both)],
        &[
            (Shock::HarvestFails, Places::Both),
            (Shock::PowerCut, Places::Both),
        ],
    ];
    for case in cases {
        let mut runner = shocked(case)?;
        for _ in 0..60 {
            check_period(runner.step()?)?;
        }
    }
    Ok(())
}

#[test]
fn the_failed_harvest_makes_food_of_twenty_ninths() -> TestResult {
    let mut runner = shocked(&[(Shock::HarvestFails, Places::A)])?;
    for _ in 0..3 {
        runner.step()?;
    }
    for result in runner.history() {
        let farm = hours_of(result)?
            .workplace(workplace(Place::A, Kind::Farm))
            .copied()
            .ok_or("farm")?;
        assert!(farm.made_units > 0, "period {}", result.period);
        assert_eq!(
            farm.made_micro_hours * 9,
            u128::from(farm.made_units) * 20_000_000,
            "period {}",
            result.period
        );
    }
    Ok(())
}

#[test]
fn the_power_cut_makes_power_of_ten_ninths() -> TestResult {
    let mut runner = shocked(&[(Shock::PowerCut, Places::A)])?;
    for _ in 0..3 {
        runner.step()?;
    }
    for result in runner.history() {
        let utility = hours_of(result)?
            .workplace(workplace(Place::A, Kind::Utility))
            .copied()
            .ok_or("utility")?;
        assert!(utility.made_units > 0, "period {}", result.period);
        assert_eq!(
            utility.made_micro_hours * 9,
            u128::from(utility.made_units) * 10_000_000,
            "period {}",
            result.period
        );
    }
    Ok(())
}

#[test]
fn given_follows_the_household_that_works_elsewhere() -> TestResult {
    let rules = vec![World::switches_at(Scale::Small)[1]];
    let mut runner = Runner::open_world_with_hours(&World {
        rules,
        ..World::scene()
    })?;
    runner.strike(Shock::HarvestFails, Places::Both, Lasts::UntilLifted)?;
    let elsewhere = |result: &PeriodResult| {
        result.receipts.member_labor_use.iter().find_map(|r| {
            let home = Household::from_principal(r.payee)?;
            let host = Workplace::from_site(r.site_id)?;
            (home != host.workers() && r.attended_hours > 0).then_some((home, host))
        })
    };
    let mut found = None;
    for _ in 0..60 {
        let result = runner.step()?;
        if let Some(pair) = elsewhere(result) {
            found = Some((result.clone(), pair));
            break;
        }
    }
    let (result, (home, host)) = found.ok_or("nobody worked elsewhere in 60 periods")?;
    let hours = hours_of(&result)?;
    let given_of = |r: &MemberLaborUseReceipt| {
        r.production_hours + r.handling_hours + r.maintenance_hours + r.installation_hours
    };
    let by_household: u64 = result
        .receipts
        .member_labor_use
        .iter()
        .filter(|r| Household::from_principal(r.payee) == Some(home))
        .map(given_of)
        .sum();
    let by_site: u64 = result
        .receipts
        .member_labor_use
        .iter()
        .filter(|r| Workplace::from_site(r.site_id) == Some(host))
        .map(given_of)
        .sum();
    assert_eq!(household_of(hours, home)?.given, by_household);
    assert_eq!(hours.workplace(host).ok_or("host")?.given, by_site);
    assert_ne!(
        hours.workplace(host).ok_or("host")?.given,
        household_of(hours, host.workers())?.given,
        "the host's hours are not its own household's"
    );
    Ok(())
}

fn keeps_the_ledger(runner: &mut Runner, steps: u64) -> TestResult {
    for _ in 0..steps {
        check_period(runner.step()?)?;
    }
    Ok(())
}

#[test]
fn every_rule_on_keeps_the_ledger_for_60_periods() -> TestResult {
    let mut runner = Runner::open_world_with_hours(&World {
        rules: World::switches_at(Scale::Small).to_vec(),
        ..World::scene()
    })?;
    runner.strike(Shock::HarvestFails, Places::Both, Lasts::UntilLifted)?;
    keeps_the_ledger(&mut runner, 60)
}

/// The rules turned on in the middle of a run, each after this many steps.
const LATE: [(u64, AdjustmentRule); 6] = [
    (20, SeekingInPlace),
    (24, HiringWithinMeans),
    (28, StopWithoutPay),
    (32, RestingPrice),
    (36, OwnerRestart { outlay_periods: 1 }),
    (40, GoodsStepDown),
];

#[test]
fn rules_turned_on_late_keep_the_ledger() -> TestResult {
    let mut runner = scene_with_hours()?;
    runner.strike(Shock::HarvestFails, Places::Both, Lasts::UntilLifted)?;
    for step in 0..60 {
        for (after, rule) in LATE {
            if after == step {
                runner.turn_on(rule)?;
            }
        }
        check_period(runner.step()?)?;
    }
    Ok(())
}

#[test]
fn a_runner_opened_without_hours_keeps_no_record() -> TestResult {
    let mut without = Runner::open_world(&World::scene())?;
    let mut with = scene_with_hours()?;
    for _ in 0..34 {
        let a = without.step()?.clone();
        let b = with.step()?.clone();
        assert_eq!(a.state_digest, b.state_digest, "period {}", a.period);
        assert!(a.hours.is_none());
        assert!(b.hours.is_some());
    }
    Ok(())
}
