//! The doubled fund world: its identities, its opening figures and its first period.

use babylon_circuit_worlds::doubled::{self, Figures};
use babylon_circuit_worlds::ids;
use babylon_circuit_worlds::{Good, Household, Kind, Place, Workplace, WorldError};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    self as engine, AccountId, CircuitAccounting, FinalDemandPrincipalId, GoodId, HouseholdKind,
    LaborCompensation, MaterialCircuitState, MonetaryCircuit, PricePolicy, ProcessId,
    PublicProgramTerms, PublicSpendingRule, SiteId, TaxBasis, UnitId,
};
use std::error::Error;

type TestResult = Result<(), Box<dyn Error>>;

fn dollars(value: i128) -> Currency {
    Currency::from_micro_units(value * 1_000_000)
}

fn monetary(state: &MaterialCircuitState) -> Result<&MonetaryCircuit, WorldError> {
    match &state.accounting {
        CircuitAccounting::Monetary(circuit) => Ok(&**circuit),
        CircuitAccounting::PhysicalControl => Err(WorldError::Arithmetic),
    }
}

fn bytes(id: [u8; 32]) -> Result<u8, Box<dyn Error>> {
    let first = id[0];
    if id.iter().all(|&b| b == first) {
        Ok(first)
    } else {
        Err("an identity is not 32 copies of one byte".into())
    }
}

#[test]
fn the_engine_closes_the_first_period_of_the_doubled_world() -> TestResult {
    let catalog = doubled::catalog(&Figures::OPENING)?;
    let state = doubled::opening_state()?;
    let closed = engine::close_material_period(&catalog, &state).map_err(WorldError::from)?;
    let (bindings, _) = doubled::staffing()?;
    closed
        .staffing_requests(&catalog, &bindings)
        .map_err(WorldError::from)?;
    Ok(())
}

fn workplace_identities() -> TestResult {
    let sites: Vec<u8> = Workplace::ALL
        .iter()
        .map(|w| bytes(w.site_id().as_bytes()))
        .collect::<Result<_, _>>()?;
    assert_eq!(sites, [1, 2, 3, 4, 5, 6, 7, 8]);
    let processes: Vec<Option<u8>> = Workplace::ALL
        .iter()
        .map(|w| w.process_id().map(|p| bytes(p.as_bytes())).transpose())
        .collect::<Result<_, _>>()?;
    assert_eq!(
        processes,
        [
            Some(1),
            Some(2),
            Some(3),
            None,
            Some(5),
            Some(6),
            Some(7),
            None
        ]
    );
    for w in Workplace::ALL {
        assert_eq!(
            bytes(w.pool_id().as_bytes())?,
            bytes(w.site_id().as_bytes())?
        );
        assert_eq!(
            bytes(w.member_id().as_bytes())?,
            bytes(w.site_id().as_bytes())?
        );
        assert_eq!(Workplace::from_site(w.site_id()), Some(w));
    }
    let workers: Vec<u8> = Workplace::ALL
        .iter()
        .map(|w| bytes(w.workers().principal().as_bytes()))
        .collect::<Result<_, _>>()?;
    assert_eq!(workers, [11, 13, 15, 17, 12, 14, 16, 18]);
    Ok(())
}

fn household_identities() -> TestResult {
    let owners: Vec<u8> = Place::ALL
        .iter()
        .map(|&p| bytes(Household::Owner(p).principal().as_bytes()))
        .collect::<Result<_, _>>()?;
    assert_eq!(owners, [20, 21]);
    let supported: Vec<u8> = Place::ALL
        .iter()
        .map(|&p| bytes(Household::Supported(p).principal().as_bytes()))
        .collect::<Result<_, _>>()?;
    assert_eq!(supported, [22, 23]);
    let all: Vec<u8> = Household::ALL
        .iter()
        .map(|h| bytes(h.principal().as_bytes()))
        .collect::<Result<_, _>>()?;
    assert_eq!(all, [11, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 23]);
    for h in Household::ALL {
        assert_eq!(Household::from_principal(h.principal()), Some(h));
    }
    for byte in [19_u8, 24] {
        assert_eq!(
            Household::from_principal(FinalDemandPrincipalId::from_bytes([byte; 32])),
            None
        );
    }
    Ok(())
}

fn shared_identities() -> TestResult {
    assert_eq!(Workplace::from_site(SiteId::from_bytes([9; 32])), None);
    assert_eq!(bytes(ids::treasury().as_bytes())?, 30);
    assert_eq!(bytes(ids::fund().as_bytes())?, 31);
    assert_eq!(bytes(ids::route(Place::A).as_bytes())?, 2);
    assert_eq!(bytes(ids::route(Place::B).as_bytes())?, 6);
    assert_eq!(bytes(ids::corridor(Place::A).as_bytes())?, 4);
    assert_eq!(bytes(ids::corridor(Place::B).as_bytes())?, 8);
    let goods: Vec<u8> = Good::ALL
        .iter()
        .map(|g| bytes(g.good_id().as_bytes()))
        .collect::<Result<_, _>>()?;
    assert_eq!(goods, [1, 2, 3]);
    for g in Good::ALL {
        assert_eq!(Good::from_good(g.good_id()), Some(g));
    }
    assert_eq!(Good::from_good(GoodId::from_bytes([4; 32])), None);
    assert_eq!(bytes(ids::goods_unit().as_bytes())?, 1);
    assert_eq!(bytes(ids::hours_unit().as_bytes())?, 2);
    assert_eq!(
        Workplace {
            place: Place::A,
            kind: Kind::Farm
        }
        .label(),
        "Place A farm"
    );
    assert_eq!(Household::Owner(Place::B).label(), "Place B owners");
    assert_eq!(Household::Supported(Place::A).label(), "Place A supported");
    assert_eq!(
        Household::Workers(Workplace {
            place: Place::A,
            kind: Kind::Farm
        })
        .label(),
        "Place A farm workers"
    );
    Ok(())
}

#[test]
fn identities_are_the_prototypes() -> TestResult {
    workplace_identities()?;
    household_identities()?;
    shared_identities()
}

#[test]
fn the_opening_holds_eighty_people_and_12240_dollars() -> TestResult {
    let state = doubled::opening_state()?;
    let circuit = monetary(&state)?;
    let recurring = circuit.recurring.as_ref().ok_or("no recurring economy")?;
    let mut by_place = [[0_u64; 6]; 2];
    let mut total = 0_u64;
    for cohort in &recurring.households {
        assert_eq!(cohort.kind, HouseholdKind::Ordinary);
        assert_eq!(cohort.households, 1);
        total += cohort.persons;
        let household = Household::from_principal(cohort.principal_id).ok_or("unknown cohort")?;
        let slot = match household {
            Household::Workers(w) => w.kind.index(),
            Household::Owner(_) => 4,
            Household::Supported(_) => 5,
        };
        by_place[household.place().index()][slot] = cohort.persons;
    }
    assert_eq!(total, 80);
    assert_eq!(by_place, [[12, 4, 4, 4, 8, 8]; 2]);
    assert_eq!(
        circuit.book.total_cash_and_reserves()?,
        Currency::from_micro_units(12_240_000_000)
    );
    let cash = |account: AccountId| circuit.book.cash(account);
    for place in Place::ALL {
        let site = |kind| AccountId::Site(Workplace { place, kind }.site_id());
        assert_eq!(cash(site(Kind::Utility))?, dollars(1_200));
        assert_eq!(cash(site(Kind::Farm))?, dollars(880));
        assert_eq!(cash(site(Kind::Clinic))?, dollars(880));
        assert_eq!(cash(site(Kind::Shop))?, dollars(1_400));
        assert_eq!(
            cash(AccountId::Household(Household::Owner(place).principal()))?,
            dollars(640)
        );
        assert_eq!(
            cash(AccountId::Household(
                Household::Supported(place).principal()
            ))?,
            dollars(0)
        );
    }
    for w in Workplace::ALL {
        assert_eq!(
            cash(AccountId::Household(w.workers().principal()))?,
            dollars(0)
        );
    }
    assert_eq!(cash(AccountId::Public(ids::treasury()))?, dollars(320));
    assert_eq!(cash(AccountId::Public(ids::fund()))?, dollars(1_920));
    Ok(())
}

fn check_offers(circuit: &MonetaryCircuit) -> TestResult {
    let recurring = circuit.recurring.as_ref().ok_or("no recurring economy")?;
    assert_eq!(recurring.offers.len(), 8);
    for offer in &recurring.offers {
        let w = Workplace::from_site(offer.site_id).ok_or("unknown site")?;
        let want = match w.kind {
            Kind::Utility => 12,
            Kind::Farm => 25,
            Kind::Clinic => 30,
            Kind::Shop => 38,
        };
        assert_eq!(offer.unit_price, dollars(want));
        let (minimum, maximum, step) = match offer.pricing {
            PricePolicy::Responsive {
                minimum,
                maximum,
                step,
                target_stock,
            } => {
                assert_eq!(target_stock, 40);
                (minimum, maximum, step)
            }
            PricePolicy::ServiceResponsive {
                minimum,
                maximum,
                step,
            } => (minimum, maximum, step),
            PricePolicy::Fixed => return Err("a fixed price".into()),
        };
        assert_eq!(
            (minimum, maximum, step),
            (dollars(1), dollars(1_000), dollars(1))
        );
    }
    Ok(())
}

fn check_stocks_and_hours(state: &MaterialCircuitState) -> TestResult {
    assert_eq!(state.inventory.len(), 4);
    for row in &state.inventory {
        let w = Workplace::from_site(row.site_id).ok_or("unknown site")?;
        assert!(matches!(w.kind, Kind::Farm | Kind::Shop));
        assert_eq!(row.quantity, 40);
    }
    let mut hours = [0_u64; 8];
    for row in &state.labor {
        hours[Workplace::from_site(row.site_id)
            .ok_or("unknown site")?
            .index()] = row.available;
        assert_eq!(row.period, 1);
    }
    assert_eq!(hours, [120, 40, 40, 40, 120, 40, 40, 40]);
    let mut batches = Vec::new();
    for row in &state.production_commitments {
        assert_eq!(row.period, 1);
        batches.push(row.planned_batches);
    }
    batches.sort_unstable();
    assert_eq!(batches, [4, 4, 40, 40, 120, 120]);
    Ok(())
}

fn check_employment_and_taxes(circuit: &MonetaryCircuit) -> TestResult {
    assert_eq!(circuit.employment.len(), 8);
    for row in &circuit.employment {
        assert_eq!(row.compensation, LaborCompensation::Wage(dollars(10)));
        let w = Workplace::from_site(row.site_id).ok_or("unknown site")?;
        assert_eq!(row.payee, w.workers().principal());
        assert_eq!(row.member_id, w.member_id());
    }
    let financial = &circuit.financial;
    assert_eq!(financial.taxes.len(), 32);
    for tax in &financial.taxes {
        let expected = if tax.public_recipient == ids::treasury() {
            500
        } else {
            1_500
        };
        assert_eq!(tax.rate_bps, expected);
        assert!(matches!(
            tax.basis,
            TaxBasis::WageIncome | TaxBasis::PositiveOperatingIncome
        ));
    }
    Ok(())
}

fn check_programs_and_budgets(circuit: &MonetaryCircuit) -> TestResult {
    let financial = &circuit.financial;
    assert_eq!(financial.programs.len(), 2);
    for program in &financial.programs {
        assert_eq!(program.payer, ids::fund());
        assert_eq!(program.rank, 0);
        match (program.key.as_str(), &program.terms) {
            (
                "laid_off",
                PublicProgramTerms::AfterLayoff {
                    wage_share_bps,
                    half_periods,
                },
            ) => {
                assert_eq!((*wage_share_bps, *half_periods), (5_000, 13));
                assert_eq!(program.recipients.len(), 8);
            }
            ("no_earner", PublicProgramTerms::PerPerson { amount_per_person }) => {
                assert_eq!(*amount_per_person, dollars(60));
                assert_eq!(program.recipients.len(), 2);
            }
            _ => return Err("an unknown program".into()),
        }
    }
    assert_eq!(financial.public_allocations.len(), 2);
    for allocation in &financial.public_allocations {
        assert_eq!(allocation.amount_per_period, dollars(160));
        assert_eq!(allocation.public_account, ids::treasury());
    }
    assert_eq!(financial.public_budgets.len(), 2);
    for budget in &financial.public_budgets {
        assert_eq!(budget.rule, PublicSpendingRule::CashInProportion);
        assert_eq!(budget.period_cap, dollars(0));
    }
    Ok(())
}

fn check_ownership(circuit: &MonetaryCircuit) -> TestResult {
    let financial = &circuit.financial;
    assert_eq!(financial.ownership.len(), 8);
    for claim in &financial.ownership {
        assert_eq!(claim.shares, 1);
        let w = Workplace::from_site(claim.issuer_site_id).ok_or("unknown site")?;
        assert_eq!(
            claim.beneficiary,
            AccountId::Household(Household::Owner(w.place).principal())
        );
    }
    assert_eq!(financial.distributions.len(), 8);
    for row in &financial.distributions {
        assert_eq!(row.earnings_fraction_bps, 10_000);
    }
    Ok(())
}

fn check_capacity_rows(state: &MaterialCircuitState) -> TestResult {
    assert_eq!(state.capacities.len(), 6 * 1_000);
    assert_eq!(state.corridor_capacities.len(), 2 * 1_000);
    for row in &state.capacities {
        assert!((1..=1_000).contains(&row.period));
        let w = Workplace::from_site(row.site_id).ok_or("unknown site")?;
        let want = match w.kind {
            Kind::Utility => 120,
            Kind::Farm => 8,
            Kind::Clinic => 40,
            Kind::Shop => return Err("a shop has no capacity row".into()),
        };
        assert_eq!(row.available_batches, want);
    }
    Ok(())
}

#[test]
fn the_opening_figures_are_the_measured_ones() -> TestResult {
    let state = doubled::opening_state()?;
    let circuit = monetary(&state)?;
    check_offers(circuit)?;
    check_stocks_and_hours(&state)?;
    check_employment_and_taxes(circuit)?;
    check_programs_and_budgets(circuit)?;
    check_ownership(circuit)?;
    check_capacity_rows(&state)?;
    Ok(())
}

#[test]
fn the_catalog_asks_for_the_market_and_plans_from_spare_money() -> TestResult {
    let catalog = doubled::catalog(&Figures::OPENING)?;
    let policy = catalog.market_clearing.as_ref().ok_or("no market")?;
    let order: Vec<u8> = policy
        .paying_order
        .iter()
        .map(|(g, u)| {
            assert_eq!(*u, UnitId::from_bytes([1; 32]));
            bytes(g.as_bytes())
        })
        .collect::<Result<_, _>>()?;
    assert_eq!(order, [1, 2, 3]);
    assert_eq!(policy.household_wants.len(), 36);
    assert!(policy.plans_from_spare_money);
    assert_eq!(catalog.process_outputs.len(), 6);
    for out in &catalog.process_outputs {
        let w = Workplace::from_site(out.site_id).ok_or("unknown site")?;
        let want = match w.kind {
            Kind::Farm => 10,
            Kind::Utility | Kind::Clinic => 1,
            Kind::Shop => return Err("a shop makes nothing".into()),
        };
        assert_eq!(out.quantity_per_batch, want);
    }
    assert_eq!(catalog.labor_coefficients.len(), 6);
    for row in &catalog.labor_coefficients {
        let process: ProcessId = row.process_id;
        let kind = Workplace::ALL
            .iter()
            .find(|w| w.process_id() == Some(process))
            .ok_or("unknown process")?
            .kind;
        let want = if kind == Kind::Farm { 10 } else { 1 };
        assert_eq!(row.quantity_per_batch, want);
        assert_eq!(row.unit_id, ids::hours_unit());
    }
    Ok(())
}

#[test]
fn the_staffing_opens_with_every_worker_employed() -> TestResult {
    let (bindings, state) = doubled::staffing()?;
    assert_eq!(bindings.len(), 8);
    assert_eq!(state.pools().len(), 8);
    for pool in state.pools() {
        let w = Workplace::from_site(pool.binding().site_id()).ok_or("unknown site")?;
        let want = [12, 4, 4, 4][w.kind.index()];
        assert_eq!(pool.employed(), want);
        assert_eq!(pool.reserve(), 0);
    }
    for w in Workplace::ALL {
        let state = doubled::member(w, 3)?;
        assert_eq!(state.binding().household_id(), w.workers().principal());
    }
    Ok(())
}
