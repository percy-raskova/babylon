//! The opening state of the doubled world: cash, stocks, costs, rows of capacity, the recurring
//! economy, the fund and the treasury. Every figure is the prototype's, listed in the plan.

use crate::doubled::catalog::{FARM_BATCH_INPUT, FARM_OPENING_BATCHES};
use crate::doubled::figures::{self, HORIZON, HOURS_PER_PERSON, OPENING_MONEY};
use crate::ids;
use crate::{Good, Household, Kind, Place, Workplace, WorldError};
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
const OWNER_CASH: i128 = 640;
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

/// Batches at the opening of a place: utility, farm, clinic.
fn batches() -> Result<[u64; 3], WorldError> {
    let need = figures::place_persons()?;
    let farm = need / FARM_BATCH_INPUT;
    debug_assert_eq!(farm, FARM_OPENING_BATCHES);
    let utility = farm
        .checked_mul(FARM_BATCH_INPUT)
        .and_then(|inputs| inputs.checked_add(need)?.checked_add(need))
        .ok_or(WorldError::Arithmetic)?;
    Ok([utility, farm, need])
}

/// The hours each workplace works at the opening, by `Workplace::index`.
pub(crate) fn site_hours() -> Result<[u64; 8], WorldError> {
    let [utility, farm, clinic] = batches()?;
    let need = figures::place_persons()?;
    let farm_hours = farm
        .checked_mul(FARM_BATCH_INPUT)
        .ok_or(WorldError::Arithmetic)?;
    let mut hours = [0_u64; 8];
    for place in Place::ALL {
        hours[w(place, Kind::Utility).index()] = utility;
        hours[w(place, Kind::Farm).index()] = farm_hours;
        hours[w(place, Kind::Clinic).index()] = clinic;
        hours[w(place, Kind::Shop).index()] = need;
    }
    Ok(hours)
}

/// The household's cash at the opening.
fn household_cash(household: Household) -> Currency {
    match household {
        Household::Owner(_) => dollars(OWNER_CASH),
        Household::Workers(_) | Household::Supported(_) => dollars(0),
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

fn cash_accounts() -> Result<Vec<CashAccount>, WorldError> {
    let mut accounts: Vec<CashAccount> = Workplace::ALL
        .iter()
        .map(|w| CashAccount {
            id: AccountId::Site(w.site_id()),
            cash: dollars(SITE_CASH[w.kind.index()]),
        })
        .collect();
    accounts.extend(Household::ALL.iter().map(|&h| CashAccount {
        id: AccountId::Household(h.principal()),
        cash: household_cash(h),
    }));
    accounts.push(CashAccount {
        id: AccountId::Public(ids::treasury()),
        cash: worth(support_payment()?.micro_units(), 2)?,
    });
    accounts.push(CashAccount {
        id: AccountId::Public(ids::fund()),
        cash: worth(dollars(FUND_OPENING_CASH).micro_units(), 2)?,
    });
    Ok(accounts)
}

/// Opening stock is carried at what it cost: the farm's direct cost a unit, the shop's purchase
/// price, and the shop's price for what households hold.
fn carrying_values() -> Result<Vec<StockCarryingValue>, WorldError> {
    let need = figures::place_persons()?;
    let farm_output = FARM_OPENING_BATCHES
        .checked_mul(10)
        .ok_or(WorldError::Arithmetic)?;
    let farm_unit = (WAGE * MICRO * i128::from(FARM_BATCH_INPUT)
        + price(Kind::Utility).micro_units() * i128::from(FARM_BATCH_INPUT))
        / i128::from(farm_output / FARM_OPENING_BATCHES);
    let mut rows = Vec::new();
    for place in Place::ALL {
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
    for household in Household::ALL {
        rows.push(StockCarryingValue {
            owner: AccountId::Household(household.principal()),
            good_id: Good::Food.good_id(),
            unit_id: ids::goods_unit(),
            amount: worth(price(Kind::Shop).micro_units(), household.opening_persons())?,
        });
    }
    Ok(rows)
}

fn inventory() -> Result<Vec<InventoryRow>, WorldError> {
    let need = figures::place_persons()?;
    let farm_output = FARM_OPENING_BATCHES
        .checked_mul(10)
        .ok_or(WorldError::Arithmetic)?;
    let mut rows = Vec::new();
    for place in Place::ALL {
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
fn capacities() -> Result<Vec<CapacityRow>, WorldError> {
    let [utility, farm, clinic] = batches()?;
    let nameplate = [
        (Kind::Utility, utility),
        (
            Kind::Farm,
            farm.checked_mul(2).ok_or(WorldError::Arithmetic)?,
        ),
        (Kind::Clinic, clinic),
    ];
    let mut rows = Vec::new();
    for period in 1..=HORIZON {
        for place in Place::ALL {
            for (kind, available_batches) in nameplate {
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

fn production_commitments() -> Result<Vec<ProductionCommitment>, WorldError> {
    let batches = batches()?;
    let mut rows = Vec::new();
    for place in Place::ALL {
        for (kind, planned_batches) in [Kind::Utility, Kind::Farm, Kind::Clinic]
            .into_iter()
            .zip(batches)
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

fn service_connections() -> Vec<ServiceConnection> {
    let mut rows = Vec::new();
    for household in Household::ALL {
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

fn households_and_purchases() -> (
    Vec<HouseholdCohort>,
    Vec<HouseholdStock>,
    Vec<HouseholdPurchasePolicy>,
) {
    let mut cohorts = Vec::new();
    let mut stocks = Vec::new();
    let mut purchases = Vec::new();
    for household in Household::ALL {
        let persons = household.opening_persons();
        let principal = household.principal();
        cohorts.push(HouseholdCohort {
            kind: HouseholdKind::Ordinary,
            principal_id: principal,
            households: 1,
            persons,
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

fn offers(farm_output: u64, need: u64) -> Vec<SellerOffer> {
    let step = dollars(1);
    let service = PricePolicy::ServiceResponsive {
        minimum: step,
        maximum: dollars(1_000),
        step,
    };
    let goods = |target_stock: u64| PricePolicy::Responsive {
        minimum: step,
        maximum: dollars(1_000),
        step,
        target_stock,
    };
    let mut rows = Vec::new();
    for place in Place::ALL {
        for (kind, good, pricing) in [
            (Kind::Utility, Good::Power, service.clone()),
            (Kind::Farm, Good::Food, goods(farm_output)),
            (Kind::Clinic, Good::Care, service.clone()),
            (Kind::Shop, Good::Food, goods(need)),
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
    rows
}

fn recurring() -> Result<RecurringEconomy, WorldError> {
    let need = figures::place_persons()?;
    let [utility, farm, clinic] = batches()?;
    let farm_output = farm.checked_mul(10).ok_or(WorldError::Arithmetic)?;
    let (households, household_stocks, household_purchases) = households_and_purchases();
    let mut replenishment = Vec::new();
    let mut production = Vec::new();
    for place in Place::ALL {
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
    let hours = site_hours()?;
    Ok(RecurringEconomy {
        households,
        household_stocks,
        household_purchases,
        offers: offers(farm_output, need),
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

/// Ownership, distributions, taxes, budgets, allocations and the two programs.
fn financial() -> Result<FinancialInstitutions, WorldError> {
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
    for account in [ids::treasury(), ids::fund()] {
        f.locations.push(InstitutionLocation {
            account: AccountId::Public(account),
            location: ids::location()?,
        });
    }
    for (recipient, rate_bps) in [
        (ids::treasury(), TREASURY_RATE_BPS),
        (ids::fund(), FUND_RATE_BPS),
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
    });
    f.programs.sort_by(|a, b| a.key.cmp(&b.key));
    Ok(f)
}

fn employment() -> Vec<EmploymentTerms> {
    Workplace::ALL
        .iter()
        .map(|wp| EmploymentTerms {
            member_id: wp.member_id(),
            site_id: wp.site_id(),
            unit_id: ids::hours_unit(),
            payee: wp.workers().principal(),
            compensation: LaborCompensation::Wage(dollars(WAGE)),
        })
        .collect()
}

/// The monetary part of the state: the book, the costs, the recurring economy, the financial
/// institutions, employment and the members' hours.
fn monetary_circuit(hours: &[u64; 8]) -> Result<MonetaryCircuit, WorldError> {
    let book = MonetaryBook::open(cash_accounts()?).map_err(MaterialCircuitError::from)?;
    let equity = Workplace::ALL
        .iter()
        .map(|wp| EquityCarryingValue {
            owner: AccountId::Household(Household::Owner(wp.place).principal()),
            issuer_site_id: wp.site_id(),
            amount: dollars(0),
        })
        .collect();
    let costs = HistoricalCostBook::open(&book, carrying_values()?, vec![], equity, vec![])?;
    Ok(MonetaryCircuit {
        aid: AidBook::default(),
        household_time: HouseholdTimeAccounting::NotModeled,
        financial: financial()?,
        costs,
        recurring: Some(Box::new(recurring()?)),
        book,
        employment: employment(),
        member_labor: Workplace::ALL
            .iter()
            .map(|wp| MemberLaborCapacityRow {
                member_id: wp.member_id(),
                period: 1,
                available_hours: hours[wp.index()],
            })
            .collect(),
    })
}

/// The opening state of the doubled world, at period 1.
///
/// # Errors
/// `WorldError::Engine` when the engine refuses a part of the state, `WorldError::Location` when
/// the place does not parse, `WorldError::Arithmetic` when a figure overflows.
pub fn opening_state() -> Result<MaterialCircuitState, WorldError> {
    debug_assert_eq!(HOURS_PER_PERSON, 10);
    debug_assert_eq!(OPENING_MONEY, 12_240 * MICRO);
    let hours = site_hours()?;
    let place = ids::location()?;
    Ok(MaterialCircuitState {
        period: 1,
        accounting: CircuitAccounting::Monetary(Box::new(monetary_circuit(&hours)?)),
        service_connections: service_connections(),
        service_orders: vec![],
        route_stage_capacities: vec![],
        inventory: inventory()?,
        orders: vec![],
        freight: vec![],
        corridor_capacities: corridor_capacities(),
        capacities: capacities()?,
        labor: Workplace::ALL
            .iter()
            .map(|wp| LaborCapacityRow {
                site_id: wp.site_id(),
                unit_id: ids::hours_unit(),
                period: 1,
                available: hours[wp.index()],
            })
            .collect(),
        production_commitments: production_commitments()?,
        final_demand_principals: Household::ALL
            .iter()
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
