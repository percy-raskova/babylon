//! The opening state of the doubled world: cash, stocks, costs, rows of capacity, the recurring
//! economy, the fund and the treasury. Every figure is the prototype's, listed in the plan.

use crate::doubled::catalog::{FARM_BATCH_INPUT, FARM_OPENING_BATCHES};
use crate::doubled::figures::{self, HORIZON};
use crate::doubled::world::{Economy, OpeningPush, Scale, World};
use crate::ids;
use crate::{Good, Household, Kind, Place, Places, Workplace, WorldError};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, AidBook, AttendancePlan, CapacityReservations, CapacityRow, CashAccount,
    CircuitAccounting, CorridorCapacity, DistributionPolicy, EmploymentTerms, EquityCarryingValue,
    FinalDemandPrincipal, FinancialInstitutions, HistoricalCostBook, HouseholdCohort,
    HouseholdKind, HouseholdPurchasePolicy, HouseholdStock, HouseholdTimeAccounting,
    InstitutionLocation, InventoryRow, LaborCapacityRow, LaborCompensation, MaterialCircuitError,
    MaterialCircuitState, MemberLaborCapacityRow, MonetaryBook, MonetaryCircuit, OwnershipClaim,
    PricePolicy, ProductionCommitment, ProductionDemandPolicy, PublicAllocation, PublicBudget,
    PublicProgram, PublicProgramKey, PublicProgramTerms, PublicSpendingRule,
    PublicTransferTreatment, RecurringEconomy, ReplenishmentPolicy, SellerOffer, ServiceConnection,
    StockCarryingValue, TaxBasis, TaxPolicy,
};

const MICRO: i128 = 1_000_000;
/// The wage of every workplace, dollars an hour.
const WAGE: i128 = 10;
/// Posted prices at the opening, dollars: utility, farm, clinic, shop.
const PRICES: [i128; 4] = [12, 25, 30, 38];
/// One period of each workplace's outlay, dollars: utility, farm, clinic, shop.
const SITE_CASH: [i128; 4] = [1_200, 880, 880, 1_400];
const FUND_OWNER_CASH: i128 = 640;
const PLAIN_OWNER_CASH: i128 = 800;
/// A national workplace opens with two periods of its outlay.
const NATIONAL_PERIODS: i128 = 2;
/// A national price steps by this many basis points of its opening price.
const NATIONAL_STEP_BPS: i128 = 250;
/// The clinic's wage under the pay push, dollars an hour.
const HIGHER_WAGE: i128 = 11;
/// The hours a batch of the utility takes under the power cut.
const CUT_HOURS_PER_BATCH: u64 = 10;
const FUND_OPENING_CASH: i128 = 960;
const FUND_PER_PERSON: i128 = 60;
const TREASURY_RATE_BPS: u16 = 500;
const FUND_RATE_BPS: u16 = 1_500;
const SUPPORTED_PERSONS: i128 = 8;
const NO_EARNER: &str = "no_earner";
const LAID_OFF: &str = "laid_off";

fn dollars(value: i128) -> Currency {
    Currency::from_micro_units(value * MICRO)
}

fn price(kind: Kind) -> Currency {
    dollars(PRICES[kind.index()])
}

fn w(place: Place, kind: Kind) -> Workplace {
    Workplace { place, kind }
}

/// A product of dollars and a quantity, in currency, checked.
fn worth(unit: i128, quantity: u64) -> Result<Currency, WorldError> {
    unit.checked_mul(i128::from(quantity))
        .map(Currency::from_micro_units)
        .ok_or(WorldError::Arithmetic)
}

/// The hours a batch of the utility takes at the opening of a place.
const fn utility_hours_per_batch(world: &World, place: Place) -> u64 {
    if world.is_pushed(OpeningPush::PowerCut, place) {
        CUT_HOURS_PER_BATCH
    } else {
        1
    }
}

/// Batches at the opening of a place: utility, farm, clinic.
fn batches(world: &World, place: Place) -> Result<[u64; 3], WorldError> {
    let need = figures::place_persons(world, place)?;
    let farm = need / FARM_BATCH_INPUT;
    let units = farm
        .checked_mul(FARM_BATCH_INPUT)
        .and_then(|inputs| inputs.checked_add(need)?.checked_add(need))
        .ok_or(WorldError::Arithmetic)?;
    let utility = units / utility_hours_per_batch(world, place);
    Ok([utility, farm, need])
}

/// The hours each workplace works at the opening, by `Workplace::index`.
pub(crate) fn site_hours(world: &World) -> Result<[u64; 8], WorldError> {
    let mut hours = [0_u64; 8];
    for place in Place::ALL {
        let [utility, farm, clinic] = batches(world, place)?;
        let need = figures::place_persons(world, place)?;
        let farm_hours = farm
            .checked_mul(FARM_BATCH_INPUT)
            .ok_or(WorldError::Arithmetic)?;
        hours[w(place, Kind::Utility).index()] = utility
            .checked_mul(utility_hours_per_batch(world, place))
            .ok_or(WorldError::Arithmetic)?;
        hours[w(place, Kind::Farm).index()] = farm_hours;
        hours[w(place, Kind::Clinic).index()] = clinic;
        hours[w(place, Kind::Shop).index()] = need;
    }
    Ok(hours)
}

/// The household's cash at the opening.
fn household_cash(world: &World, household: Household) -> Currency {
    match household {
        Household::Owner(_) => dollars(match world.economy {
            Economy::Fund => FUND_OWNER_CASH,
            Economy::Plain => PLAIN_OWNER_CASH,
        }),
        Household::Workers(_) | Household::Supported(_) => dollars(0),
    }
}

/// What a workplace opens with: its scale's periods of its outlay, the shop's halved under P3.
fn site_cash(world: &World, workplace: Workplace) -> Result<Currency, WorldError> {
    let periods = match world.scale {
        Scale::Small => 1,
        Scale::National => NATIONAL_PERIODS,
    };
    let cash = worth(
        SITE_CASH[workplace.kind.index()] * MICRO,
        u64::try_from(periods).map_err(|_| WorldError::Arithmetic)?,
    )?;
    Ok(
        if workplace.kind == Kind::Shop && world.is_pushed(OpeningPush::LessMoney, workplace.place)
        {
            Currency::from_micro_units(cash.micro_units() / 2)
        } else {
            cash
        },
    )
}

/// The wage of a workplace, dollars an hour: the clinic's is higher under P4.
fn wage(world: &World, workplace: Workplace) -> Currency {
    if workplace.kind == Kind::Clinic && world.is_pushed(OpeningPush::HigherPay, workplace.place) {
        dollars(HIGHER_WAGE)
    } else {
        dollars(WAGE)
    }
}

/// What the treasury pays a supported household: its basket less the fund's benefit, for its
/// persons.
fn support_payment() -> Result<Currency, WorldError> {
    let basket =
        PRICES[Kind::Shop.index()] + PRICES[Kind::Utility.index()] + PRICES[Kind::Clinic.index()];
    worth(
        (basket - FUND_PER_PERSON) * MICRO,
        u64::try_from(SUPPORTED_PERSONS).map_err(|_| WorldError::Arithmetic)?,
    )
}

fn cash_accounts(world: &World) -> Result<Vec<CashAccount>, WorldError> {
    let mut accounts = Vec::new();
    for workplace in Workplace::ALL {
        accounts.push(CashAccount {
            id: AccountId::Site(workplace.site_id()),
            cash: site_cash(world, workplace)?,
        });
    }
    accounts.extend(world.households().into_iter().map(|h| CashAccount {
        id: AccountId::Household(h.principal()),
        cash: household_cash(world, h),
    }));
    if world.economy == Economy::Fund {
        accounts.push(CashAccount {
            id: AccountId::Public(ids::treasury()),
            cash: worth(support_payment()?.micro_units(), 2)?,
        });
        accounts.push(CashAccount {
            id: AccountId::Public(ids::fund()),
            cash: worth(dollars(FUND_OPENING_CASH).micro_units(), 2)?,
        });
    }
    Ok(accounts)
}

/// Opening stock is carried at what it cost: the farm's direct cost a unit, the shop's purchase
/// price, and the shop's price for what households hold.
fn carrying_values(world: &World) -> Result<Vec<StockCarryingValue>, WorldError> {
    let farm_output = FARM_OPENING_BATCHES
        .checked_mul(10)
        .ok_or(WorldError::Arithmetic)?;
    let farm_unit = (WAGE * MICRO * i128::from(FARM_BATCH_INPUT)
        + price(Kind::Utility).micro_units() * i128::from(FARM_BATCH_INPUT))
        / i128::from(farm_output / FARM_OPENING_BATCHES);
    let mut rows = Vec::new();
    for place in Place::ALL {
        let need = figures::place_persons(world, place)?;
        rows.push(StockCarryingValue {
            owner: AccountId::Site(w(place, Kind::Farm).site_id()),
            good_id: Good::Food.good_id(),
            unit_id: ids::goods_unit(),
            amount: worth(farm_unit, farm_output)?,
        });
        rows.push(StockCarryingValue {
            owner: AccountId::Site(w(place, Kind::Shop).site_id()),
            good_id: Good::Food.good_id(),
            unit_id: ids::goods_unit(),
            amount: worth(price(Kind::Farm).micro_units(), need)?,
        });
    }
    for household in world.households() {
        rows.push(StockCarryingValue {
            owner: AccountId::Household(household.principal()),
            good_id: Good::Food.good_id(),
            unit_id: ids::goods_unit(),
            amount: worth(price(Kind::Shop).micro_units(), world.persons(household))?,
        });
    }
    Ok(rows)
}

fn inventory(world: &World) -> Result<Vec<InventoryRow>, WorldError> {
    let farm_output = FARM_OPENING_BATCHES
        .checked_mul(10)
        .ok_or(WorldError::Arithmetic)?;
    let mut rows = Vec::new();
    for place in Place::ALL {
        let need = figures::place_persons(world, place)?;
        for (kind, quantity) in [(Kind::Farm, farm_output), (Kind::Shop, need)] {
            rows.push(InventoryRow {
                site_id: w(place, kind).site_id(),
                good_id: Good::Food.good_id(),
                unit_id: ids::goods_unit(),
                quantity,
            });
        }
    }
    Ok(rows)
}

/// Capacity rows for periods 1 to `HORIZON`: nameplate batches utility 120, farm 8, clinic 40.
fn capacities(world: &World) -> Result<Vec<CapacityRow>, WorldError> {
    let mut nameplates = Vec::new();
    for place in Place::ALL {
        let [utility, farm, clinic] = batches(world, place)?;
        nameplates.push([
            (Kind::Utility, utility),
            (
                Kind::Farm,
                farm.checked_mul(2).ok_or(WorldError::Arithmetic)?,
            ),
            (Kind::Clinic, clinic),
        ]);
    }
    let mut rows = Vec::new();
    for period in 1..=HORIZON {
        for (place, nameplate) in Place::ALL.into_iter().zip(&nameplates) {
            for &(kind, available_batches) in nameplate {
                if let Some(process_id) = w(place, kind).process_id() {
                    rows.push(CapacityRow {
                        process_id,
                        site_id: w(place, kind).site_id(),
                        period,
                        available_batches,
                    });
                }
            }
        }
    }
    Ok(rows)
}

fn corridor_capacities() -> Vec<CorridorCapacity> {
    let mut rows = Vec::new();
    for period in 1..=HORIZON {
        for place in Place::ALL {
            rows.push(CorridorCapacity {
                corridor_id: ids::corridor(place),
                period,
                available_grams: 1_000_000,
            });
        }
    }
    rows
}

fn production_commitments(world: &World) -> Result<Vec<ProductionCommitment>, WorldError> {
    let mut rows = Vec::new();
    for place in Place::ALL {
        for (kind, planned_batches) in [Kind::Utility, Kind::Farm, Kind::Clinic]
            .into_iter()
            .zip(batches(world, place)?)
        {
            if let Some(process_id) = w(place, kind).process_id() {
                rows.push(ProductionCommitment {
                    process_id,
                    site_id: w(place, kind).site_id(),
                    period: 1,
                    planned_batches,
                });
            }
        }
    }
    Ok(rows)
}

fn service_connections(world: &World) -> Vec<ServiceConnection> {
    let mut rows = Vec::new();
    for household in world.households() {
        let place = household.place();
        for (good, provider) in [(Good::Power, Kind::Utility), (Good::Care, Kind::Clinic)] {
            rows.push(ServiceConnection {
                provider_site_id: w(place, provider).site_id(),
                buyer: AccountId::Household(household.principal()),
                good_id: good.good_id(),
                unit_id: ids::goods_unit(),
            });
        }
    }
    for place in Place::ALL {
        for buyer in [Kind::Farm, Kind::Clinic] {
            rows.push(ServiceConnection {
                provider_site_id: w(place, Kind::Utility).site_id(),
                buyer: AccountId::Site(w(place, buyer).site_id()),
                good_id: Good::Power.good_id(),
                unit_id: ids::goods_unit(),
            });
        }
    }
    rows.sort();
    rows
}

fn households_and_purchases(
    world: &World,
) -> (
    Vec<HouseholdCohort>,
    Vec<HouseholdStock>,
    Vec<HouseholdPurchasePolicy>,
) {
    let mut cohorts = Vec::new();
    let mut stocks = Vec::new();
    let mut purchases = Vec::new();
    for household in world.households() {
        let persons = world.persons(household);
        let principal = household.principal();
        cohorts.push(HouseholdCohort {
            kind: HouseholdKind::Ordinary,
            principal_id: principal,
            households: 1,
            persons: world.cohort_persons(household),
        });
        stocks.push(HouseholdStock {
            principal_id: principal,
            good_id: Good::Food.good_id(),
            unit_id: ids::goods_unit(),
            quantity: persons,
        });
        for (good, seller, target_closing_stock) in [
            (Good::Food, Kind::Shop, persons),
            (Good::Power, Kind::Utility, 0),
            (Good::Care, Kind::Clinic, 0),
        ] {
            purchases.push(HouseholdPurchasePolicy {
                principal_id: principal,
                retailer_site_id: w(household.place(), seller).site_id(),
                good_id: good.good_id(),
                unit_id: ids::goods_unit(),
                target_closing_stock,
                maximum_purchase: persons,
                enabled: true,
            });
        }
    }
    (cohorts, stocks, purchases)
}

/// What a product's price steps by: $1 at the small figures, a fortieth of its opening price (250
/// basis points, rounded down to the micro-unit) at the national ones.
fn price_step(world: &World, kind: Kind) -> Currency {
    match world.scale {
        Scale::Small => dollars(1),
        Scale::National => {
            Currency::from_micro_units(price(kind).micro_units() * NATIONAL_STEP_BPS / 10_000)
        }
    }
}

fn offers(world: &World) -> Result<Vec<SellerOffer>, WorldError> {
    let floor = dollars(1);
    let service = |kind: Kind| PricePolicy::ServiceResponsive {
        minimum: floor,
        maximum: dollars(1_000),
        step: price_step(world, kind),
    };
    let goods = |kind: Kind, target_stock: u64| PricePolicy::Responsive {
        minimum: floor,
        maximum: dollars(1_000),
        step: price_step(world, kind),
        target_stock,
    };
    let mut rows = Vec::new();
    for place in Place::ALL {
        let need = figures::place_persons(world, place)?;
        let [_, farm, _] = batches(world, place)?;
        let farm_output = farm.checked_mul(10).ok_or(WorldError::Arithmetic)?;
        for (kind, good, pricing) in [
            (Kind::Utility, Good::Power, service(Kind::Utility)),
            (Kind::Farm, Good::Food, goods(Kind::Farm, farm_output)),
            (Kind::Clinic, Good::Care, service(Kind::Clinic)),
            (Kind::Shop, Good::Food, goods(Kind::Shop, need)),
        ] {
            rows.push(SellerOffer {
                site_id: w(place, kind).site_id(),
                good_id: good.good_id(),
                unit_id: ids::goods_unit(),
                unit_price: price(kind),
                pricing,
            });
        }
    }
    rows.sort_by_key(|row| (row.site_id, row.good_id, row.unit_id));
    Ok(rows)
}

fn recurring(world: &World) -> Result<RecurringEconomy, WorldError> {
    let (households, household_stocks, household_purchases) = households_and_purchases(world);
    let mut replenishment = Vec::new();
    let mut production = Vec::new();
    for place in Place::ALL {
        let need = figures::place_persons(world, place)?;
        let [utility, farm, clinic] = batches(world, place)?;
        let farm_output = farm.checked_mul(10).ok_or(WorldError::Arithmetic)?;
        replenishment.push(ReplenishmentPolicy {
            buyer_site_id: w(place, Kind::Shop).site_id(),
            supplier_site_id: w(place, Kind::Farm).site_id(),
            good_id: Good::Food.good_id(),
            unit_id: ids::goods_unit(),
            target_stock: need,
            maximum_purchase: need,
            cash_floor: dollars(0),
        });
        for (kind, output_buffer, planned_batches) in [
            (Kind::Utility, 0, utility),
            (Kind::Farm, farm_output, farm),
            (Kind::Clinic, 0, clinic),
        ] {
            if let Some(process_id) = w(place, kind).process_id() {
                production.push(ProductionDemandPolicy {
                    process_id,
                    site_id: w(place, kind).site_id(),
                    output_buffer,
                    planned_batches,
                });
            }
        }
    }
    let hours = site_hours(world)?;
    Ok(RecurringEconomy {
        households,
        household_stocks,
        household_purchases,
        offers: offers(world)?,
        replenishment,
        production,
        attendance: Workplace::ALL
            .iter()
            .map(|wp| AttendancePlan {
                site_id: wp.site_id(),
                unit_id: ids::hours_unit(),
                period: 1,
                planned_hours: hours[wp.index()],
            })
            .collect(),
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    })
}

/// The rate of the fund's tax rows: three quarters under P5.
fn fund_rate(world: &World) -> u16 {
    if world
        .pushed
        .is_some_and(|pushed| pushed.push == OpeningPush::LowerFundTaxes)
    {
        FUND_RATE_BPS / 4 * 3
    } else {
        FUND_RATE_BPS
    }
}

/// Ownership and distributions of every world; the plain world has nothing else.
fn financial(world: &World) -> Result<FinancialInstitutions, WorldError> {
    let mut f = FinancialInstitutions::empty();
    for wp in Workplace::ALL {
        f.ownership.push(OwnershipClaim {
            issuer_site_id: wp.site_id(),
            beneficiary: AccountId::Household(Household::Owner(wp.place).principal()),
            shares: 1,
        });
        f.distributions.push(DistributionPolicy {
            issuer_site_id: wp.site_id(),
            earnings_fraction_bps: 10_000,
            period_cap: dollars(1_000_000),
            cash_floor: dollars(0),
        });
    }
    if world.economy == Economy::Fund {
        add_public_accounts(&mut f, fund_rate(world))?;
    }
    Ok(f)
}

/// Taxes, budgets, allocations and the two programs of the fund world.
fn add_public_accounts(
    f: &mut FinancialInstitutions,
    fund_rate_bps: u16,
) -> Result<(), WorldError> {
    for account in [ids::treasury(), ids::fund()] {
        f.locations.push(InstitutionLocation {
            account: AccountId::Public(account),
            location: ids::location()?,
        });
    }
    for (recipient, rate_bps) in [
        (ids::treasury(), TREASURY_RATE_BPS),
        (ids::fund(), fund_rate_bps),
    ] {
        for wp in Workplace::ALL {
            f.taxes.push(TaxPolicy {
                payer: AccountId::Household(wp.workers().principal()),
                public_recipient: recipient,
                basis: TaxBasis::WageIncome,
                rate_bps,
                cash_floor: dollars(0),
            });
            f.taxes.push(TaxPolicy {
                payer: AccountId::Site(wp.site_id()),
                public_recipient: recipient,
                basis: TaxBasis::PositiveOperatingIncome,
                rate_bps,
                cash_floor: dollars(0),
            });
        }
        f.public_budgets.push(PublicBudget {
            public_account: recipient,
            period_cap: dollars(0),
            cash_floor: dollars(0),
            rule: PublicSpendingRule::CashInProportion,
        });
    }
    for place in Place::ALL {
        f.public_allocations.push(PublicAllocation {
            public_account: ids::treasury(),
            recipient: AccountId::Household(Household::Supported(place).principal()),
            treatment: PublicTransferTreatment::HouseholdIncomeSupport,
            priority: 0,
            amount_per_period: support_payment()?,
        });
    }
    f.programs.push(PublicProgram {
        key: PublicProgramKey::new(NO_EARNER)?,
        payer: ids::fund(),
        rank: 0,
        terms: PublicProgramTerms::PerPerson {
            amount_per_person: dollars(FUND_PER_PERSON),
        },
        recipients: Place::ALL
            .iter()
            .map(|&p| Household::Supported(p).principal())
            .collect(),
        own_amounts: vec![],
    });
    let mut laid_off: Vec<_> = Workplace::ALL
        .iter()
        .map(|wp| wp.workers().principal())
        .collect();
    laid_off.sort();
    f.programs.push(PublicProgram {
        key: PublicProgramKey::new(LAID_OFF)?,
        payer: ids::fund(),
        rank: 0,
        terms: PublicProgramTerms::AfterLayoff {
            wage_share_bps: 5_000,
            half_periods: 13,
        },
        recipients: laid_off,
        own_amounts: vec![],
    });
    f.programs.sort_by(|a, b| a.key.cmp(&b.key));
    Ok(())
}

/// One row of terms for each workplace's own members, then one for each ordered pair of workplaces
/// of a place: the host's site and rate, paid to the home's household.
fn employment(world: &World) -> Vec<EmploymentTerms> {
    let own = Workplace::ALL.iter().map(|&wp| EmploymentTerms {
        member_id: wp.member_id(),
        site_id: wp.site_id(),
        unit_id: ids::hours_unit(),
        payee: wp.workers().principal(),
        compensation: LaborCompensation::Wage(wage(world, wp)),
    });
    let pairs = Workplace::pairs().map(|(home, host)| EmploymentTerms {
        member_id: host.pair_member_id(home),
        site_id: host.site_id(),
        unit_id: ids::hours_unit(),
        payee: home.workers().principal(),
        compensation: LaborCompensation::Wage(wage(world, host)),
    });
    own.chain(pairs).collect()
}

/// The monetary part of the state: the book, the costs, the recurring economy, the financial
/// institutions, employment and the members' hours.
fn monetary_circuit(world: &World, hours: &[u64; 8]) -> Result<MonetaryCircuit, WorldError> {
    let book = MonetaryBook::open(cash_accounts(world)?).map_err(MaterialCircuitError::from)?;
    let equity = Workplace::ALL
        .iter()
        .map(|wp| EquityCarryingValue {
            owner: AccountId::Household(Household::Owner(wp.place).principal()),
            issuer_site_id: wp.site_id(),
            amount: dollars(0),
        })
        .collect();
    let costs = HistoricalCostBook::open(&book, carrying_values(world)?, vec![], equity, vec![])?;
    let own_hours = Workplace::ALL.iter().map(|wp| MemberLaborCapacityRow {
        member_id: wp.member_id(),
        period: 1,
        available_hours: hours[wp.index()],
    });
    let pair_hours = Workplace::pairs().map(|(home, host)| MemberLaborCapacityRow {
        member_id: host.pair_member_id(home),
        period: 1,
        available_hours: 0,
    });
    Ok(MonetaryCircuit {
        aid: AidBook::default(),
        household_time: HouseholdTimeAccounting::NotModeled,
        financial: financial(world)?,
        costs,
        recurring: Some(Box::new(recurring(world)?)),
        book,
        employment: employment(world),
        member_labor: own_hours.chain(pair_hours).collect(),
    })
}

/// The opening state of the scene's world, at period 1.
///
/// # Errors
/// As `opening_state_of`.
pub fn opening_state() -> Result<MaterialCircuitState, WorldError> {
    opening_state_of(&World::scene())
}

/// The opening state of a world, at period 1.
///
/// # Errors
/// `WorldError::PushNotInThisWorld` for `LowerFundTaxes` in the plain world;
/// `WorldError::PushOnOnePlace` for `LowerFundTaxes` struck in one place;
/// `WorldError::Engine` when the engine refuses a part of the state, `WorldError::Location` when
/// the place does not parse, `WorldError::Arithmetic` when a figure overflows.
pub fn opening_state_of(world: &World) -> Result<MaterialCircuitState, WorldError> {
    refuse_push(world)?;
    let hours = site_hours(world)?;
    let place = ids::location()?;
    Ok(MaterialCircuitState {
        period: 1,
        accounting: CircuitAccounting::Monetary(Box::new(monetary_circuit(world, &hours)?)),
        service_connections: service_connections(world),
        service_orders: vec![],
        route_stage_capacities: vec![],
        inventory: inventory(world)?,
        orders: vec![],
        freight: vec![],
        corridor_capacities: corridor_capacities(),
        capacities: capacities(world)?,
        labor: Workplace::ALL
            .iter()
            .map(|wp| LaborCapacityRow {
                site_id: wp.site_id(),
                unit_id: ids::hours_unit(),
                period: 1,
                available: hours[wp.index()],
            })
            .collect(),
        production_commitments: production_commitments(world)?,
        final_demand_principals: world
            .households()
            .into_iter()
            .map(|h| FinalDemandPrincipal {
                id: h.principal(),
                location: place,
            })
            .collect(),
        final_demand_orders: vec![],
        maintenance_service: None,
        capacity_reservations: CapacityReservations::default(),
    })
}

/// The fund's taxes are the fund world's, and there is one fund.
fn refuse_push(world: &World) -> Result<(), WorldError> {
    match world.pushed {
        Some(pushed) if pushed.push == OpeningPush::LowerFundTaxes => {
            if world.economy == Economy::Plain {
                Err(WorldError::PushNotInThisWorld)
            } else if pushed.places != Places::Both {
                Err(WorldError::PushOnOnePlace)
            } else {
                Ok(())
            }
        }
        _ => Ok(()),
    }
}
