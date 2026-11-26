//! The country bench: the engine's own period, run on the whole national opening without the tick.
//! It closes each period with the engine's public entries, in the order of the tick's staffed run, and
//! checks money, persons and the labor force every period. A refusal is returned typed and leaves the
//! bench as it was.
use super::country_fund;
use super::country_rules;
use super::country_seekers::{self, SeekerRows, Wages};
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{
    self as engine, AdjustmentReceipt, CircuitAccounting, ClosedMaterialPeriod,
    HouseholdLifecycleReceipt, LaborCapacityRow, MarketClearingReceipt, MaterialCatalog,
    MaterialCircuitError, MaterialCircuitState, MaterialCircuitTransition, MemberLaborCapacityRow,
    MonetaryCircuit, PlaceStaffingError, PoolMembers, ProcessId, PublicProgramReceipt,
    RecurringEconomy, ResidentWorkforceAttrition, SiteId, StaffingError, StaffingMemberId,
    StaffingMemberReceipt, StaffingMemberState, StaffingPlace, StaffingPoolId, StaffingPoolState,
    StaffingState, StaffingWorkRequest, WorkplaceStanding,
};
use babylon_persistence::economic_catalog::{EconomicCatalogError, EconomicOpening};
use babylon_tick::material_world::MaterialTickReceipts;
use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::fmt::{Display, Formatter, Result as FmtResult};
use std::mem;
use std::time::{Duration, Instant};

/// Which rules the bench turns on.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RuleSet {
    None,
    /// (i) The price of a short market alone.
    Market,
    /// (ii) The market, spare money, the bound on hiring, the resting price and the step-down.
    NoSeekers,
    /// (iii) All six rules, with spare money.
    AllSix,
    /// (iv) All six rules, with the national fund and its two programs added to the opening.
    AllSixWithBenefits,
}

impl RuleSet {
    /// The set's name in a record's head and in its file's name. `None` is "baseline".
    pub const fn name(self) -> &'static str {
        match self {
            Self::None => "baseline",
            Self::Market => "market",
            Self::NoSeekers => "no-seekers",
            Self::AllSix => "all-six",
            Self::AllSixWithBenefits => "all-six-with-benefits",
        }
    }

    /// Whether the set staffs by place: its members are the seekers' rows and its period is the
    /// seekers' path.
    pub const fn seeks_in_place(self) -> bool {
        matches!(self, Self::AllSix | Self::AllSixWithBenefits)
    }

    /// Whether the opening gains the national fund and its programs.
    pub const fn has_benefits(self) -> bool {
        matches!(self, Self::AllSixWithBenefits)
    }
}

/// A stage of one period, for an error.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum BenchStage {
    Open,
    Close,
    Attrition,
    StaffingRequests,
    AdvanceStaffing,
    Distribute,
    #[allow(
        dead_code,
        reason = "the plan's stage list names it; a refusal of the places' staffing is typed BenchError::Place"
    )]
    StaffInPlaces,
    Finish,
    Read,
}

#[derive(Debug)]
pub enum BenchError {
    Opening(EconomicCatalogError),
    Engine {
        period: u64,
        stage: BenchStage,
        error: MaterialCircuitError,
    },
    Staffing {
        period: u64,
        stage: BenchStage,
        error: StaffingError,
    },
    Place {
        period: u64,
        error: PlaceStaffingError,
    },
    MoneyNotConserved {
        period: u64,
        opening: i128,
        closing: i128,
    },
    PersonsNotExplained {
        period: u64,
        expected: u64,
        closing: u64,
    },
    LaborForceNotExplained {
        period: u64,
        expected: u64,
        closing: u64,
    },
    Arithmetic {
        period: u64,
    },
}

impl Display for BenchError {
    fn fmt(&self, out: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::Opening(error) => write!(out, "the opening does not compile: {error:?}"),
            Self::Engine {
                period,
                stage,
                error,
            } => write!(
                out,
                "period {period}, stage {stage:?}: the engine refused: {error:?}"
            ),
            Self::Staffing {
                period,
                stage,
                error,
            } => write!(
                out,
                "period {period}, stage {stage:?}: staffing refused: {error:?}"
            ),
            Self::Place { period, error } => {
                write!(out, "period {period}: place staffing refused: {error:?}")
            }
            Self::MoneyNotConserved {
                period,
                opening,
                closing,
            } => write!(
                out,
                "period {period}: money {closing} against the opening's {opening}"
            ),
            Self::PersonsNotExplained {
                period,
                expected,
                closing,
            } => write!(
                out,
                "period {period}: persons {closing}, births and deaths explain {expected}"
            ),
            Self::LaborForceNotExplained {
                period,
                expected,
                closing,
            } => write!(
                out,
                "period {period}: labor force {closing}, attrition explains {expected}"
            ),
            Self::Arithmetic { period } => write!(out, "period {period}: arithmetic overflowed"),
        }
    }
}

/// Money is the opening's, or the period is refused.
pub fn check_money(period: u64, opening: i128, closing: i128) -> Result<(), BenchError> {
    if opening == closing {
        Ok(())
    } else {
        Err(BenchError::MoneyNotConserved {
            period,
            opening,
            closing,
        })
    }
}

/// Persons after equal persons before, plus births, less deaths, or the period is refused.
pub fn check_persons(
    period: u64,
    before: u64,
    births: u64,
    deaths: u64,
    after: u64,
) -> Result<(), BenchError> {
    let expected = before
        .checked_add(births)
        .and_then(|persons| persons.checked_sub(deaths))
        .ok_or(BenchError::Arithmetic { period })?;
    if expected == after {
        Ok(())
    } else {
        Err(BenchError::PersonsNotExplained {
            period,
            expected,
            closing: after,
        })
    }
}

/// The labor force falls by exactly what was removed, or the period is refused.
pub fn check_labor_force(
    period: u64,
    before: u64,
    removed: u64,
    after: u64,
) -> Result<(), BenchError> {
    let expected = before
        .checked_sub(removed)
        .ok_or(BenchError::Arithmetic { period })?;
    if expected == after {
        Ok(())
    } else {
        Err(BenchError::LaborForceNotExplained {
            period,
            expected,
            closing: after,
        })
    }
}

/// What one period hands back.
pub struct BenchPeriod {
    pub period: u64,
    /// Built from the transition, as the tick builds the committed family.
    pub receipts: MaterialTickReceipts,
    pub market_clearings: Vec<MarketClearingReceipt>,
    pub adjustments: Vec<AdjustmentReceipt>,
    pub public_programs: Vec<PublicProgramReceipt>,
    pub closing_members: Vec<PoolMembers>,
    /// Production policies whose planned batches after the close exceed the period's plan receipt
    /// (rule A6 writes no receipt of its own).
    pub spare_money_raised: u64,
    /// The step alone, not the opening's compile.
    pub elapsed: Duration,
}

/// The national opening, stepped one period at a time on the engine's own entries.
pub struct CountryBench {
    catalog: MaterialCatalog,
    state: MaterialCircuitState,
    staffing: StaffingState,
    members: Vec<PoolMembers>,
    places: Vec<StaffingPlace>,
    standing: WorkplaceStanding,
    set: RuleSet,
    opening_money: i128,
    no_earner_per_person: Option<Currency>,
}

/// What a closed period decided, before the bench keeps any of it.
struct Stepped {
    transition: MaterialCircuitTransition,
    staffing: StaffingState,
    members: Vec<PoolMembers>,
    standing: WorkplaceStanding,
}

/// The staffing after the household lifecycle has taken its people out of the workforce.
struct Attrited {
    staffing: StaffingState,
    members: Vec<PoolMembers>,
    rows: Vec<ResidentWorkforceAttrition>,
}

/// What the staffing of a period decided.
struct Staffed {
    staffing: StaffingState,
    members: Vec<PoolMembers>,
    receipts: Vec<StaffingMemberReceipt>,
    next_labor: Vec<LaborCapacityRow>,
    member_labor: Vec<MemberLaborCapacityRow>,
}

fn engine_failed(period: u64, stage: BenchStage) -> impl Fn(MaterialCircuitError) -> BenchError {
    move |error| BenchError::Engine {
        period,
        stage,
        error,
    }
}

fn staffing_error(period: u64, stage: BenchStage) -> impl Fn(StaffingError) -> BenchError {
    move |error| BenchError::Staffing {
        period,
        stage,
        error,
    }
}

fn monetary(period: u64, state: &MaterialCircuitState) -> Result<&MonetaryCircuit, BenchError> {
    match &state.accounting {
        CircuitAccounting::Monetary(circuit) => Ok(circuit),
        CircuitAccounting::PhysicalControl => Err(engine_failed(period, BenchStage::Read)(
            MaterialCircuitError::MonetaryInvariant,
        )),
    }
}

/// Total cash and reserves of the state's book, in millionths.
fn total_money(period: u64, state: &MaterialCircuitState) -> Result<i128, BenchError> {
    monetary(period, state)?
        .book
        .total_cash_and_reserves()
        .map(Currency::micro_units)
        .map_err(|_| BenchError::Arithmetic { period })
}

/// Persons of every household cohort of the state.
fn cohort_persons(period: u64, state: &MaterialCircuitState) -> Result<u64, BenchError> {
    let recurring = monetary(period, state)?.recurring.as_ref().ok_or_else(|| {
        engine_failed(period, BenchStage::Read)(MaterialCircuitError::MonetaryInvariant)
    })?;
    recurring
        .households
        .iter()
        .try_fold(0_u64, |sum, cohort| sum.checked_add(cohort.persons))
        .ok_or(BenchError::Arithmetic { period })
}

/// The labor force of every pool: the persons who are at work or waiting.
fn labor_force(period: u64, staffing: &StaffingState) -> Result<u64, BenchError> {
    staffing
        .pools()
        .iter()
        .try_fold(0_u64, |sum, pool| {
            sum.checked_add(pool.employed())?
                .checked_add(pool.reserve())
        })
        .ok_or(BenchError::Arithmetic { period })
}

/// Births and deaths of the period's lifecycle receipts.
fn births_and_deaths(
    period: u64,
    lifecycle: &[HouseholdLifecycleReceipt],
) -> Result<(u64, u64), BenchError> {
    let mut births = 0_u64;
    let mut deaths = 0_u64;
    for receipt in lifecycle {
        births = births
            .checked_add(receipt.births)
            .ok_or(BenchError::Arithmetic { period })?;
        let died = receipt
            .deaths
            .persons()
            .map_err(|_| BenchError::Arithmetic { period })?;
        deaths = deaths
            .checked_add(died)
            .ok_or(BenchError::Arithmetic { period })?;
    }
    Ok((births, deaths))
}

/// The persons each attrition row takes out of the workforce.
fn removed_persons(period: u64, rows: &[ResidentWorkforceAttrition]) -> Result<u64, BenchError> {
    rows.iter()
        .try_fold(0_u64, |sum, row| {
            sum.checked_add(row.employed_removed)?
                .checked_add(row.reserve_removed)
        })
        .ok_or(BenchError::Arithmetic { period })
}

/// One pool and its members after the attrition rows that name them.
fn shrink_pool(
    pool: &StaffingPoolState,
    held: &PoolMembers,
    by_member: &BTreeMap<StaffingMemberId, &ResidentWorkforceAttrition>,
) -> Result<(StaffingPoolState, PoolMembers), StaffingError> {
    let mut employed = pool.employed();
    let mut reserve = pool.reserve();
    let mut members = Vec::with_capacity(held.members.len());
    for member in &held.members {
        let Some(row) = by_member.get(&member.binding().member_id()) else {
            members.push(member.clone());
            continue;
        };
        let working = member
            .employed()
            .checked_sub(row.employed_removed)
            .ok_or(StaffingError::PopulationInvariant)?;
        let waiting = member
            .reserve()
            .checked_sub(row.reserve_removed)
            .ok_or(StaffingError::PopulationInvariant)?;
        let living = working
            .checked_add(waiting)
            .ok_or(StaffingError::Arithmetic)?;
        let binding = member.binding().with_living_force(living)?;
        members.push(StaffingMemberState::try_new(binding, working, waiting)?);
        employed = employed
            .checked_sub(row.employed_removed)
            .ok_or(StaffingError::PopulationInvariant)?;
        reserve = reserve
            .checked_sub(row.reserve_removed)
            .ok_or(StaffingError::PopulationInvariant)?;
    }
    let force = employed
        .checked_add(reserve)
        .ok_or(StaffingError::Arithmetic)?;
    let binding = pool.binding().with_living_force(force)?;
    let next =
        StaffingPoolState::try_new(binding, employed, reserve, pool.previous_unretained_hours())?;
    Ok((
        next,
        PoolMembers {
            pool_id: held.pool_id,
            members,
        },
    ))
}

/// The tick's `apply_resident_attrition`, copied: every member of every pool, one flat list, the
/// engine's reconciliation, then each changed member and each pool takes its new living force.
fn attrition(
    period: u64,
    staffing: &StaffingState,
    members: &[PoolMembers],
    lifecycle: &[HouseholdLifecycleReceipt],
) -> Result<Attrited, BenchError> {
    let failed = staffing_error(period, BenchStage::Attrition);
    if lifecycle.is_empty() {
        return Ok(Attrited {
            staffing: staffing.clone(),
            members: members.to_vec(),
            rows: Vec::new(),
        });
    }
    let mut flat = Vec::new();
    for (pool, held) in staffing.pools().iter().zip(members) {
        if pool.binding().pool_id() != held.pool_id {
            return Err(failed(StaffingError::PopulationInvariant));
        }
        for member in &held.members {
            flat.push((held.pool_id, member.clone()));
        }
    }
    let rows = engine::reconcile_resident_workforce(lifecycle, &flat).map_err(&failed)?;
    let by_member: BTreeMap<_, _> = rows.iter().map(|row| (row.member_id, row)).collect();
    let mut pools = Vec::with_capacity(members.len());
    let mut kept = Vec::with_capacity(members.len());
    for (pool, held) in staffing.pools().iter().zip(members) {
        let (next, held) = shrink_pool(pool, held, &by_member).map_err(&failed)?;
        pools.push(next);
        kept.push(held);
    }
    let staffing = StaffingState::try_new(staffing.period(), pools).map_err(&failed)?;
    Ok(Attrited {
        staffing,
        members: kept,
        rows,
    })
}

/// The next member state of each receipt row, in the receipt's order.
fn next_members(rows: &[StaffingMemberReceipt]) -> Result<Vec<StaffingMemberState>, StaffingError> {
    rows.iter()
        .map(|row| {
            StaffingMemberState::try_new(
                row.member.clone(),
                row.closing_employed,
                row.closing_reserve,
            )
        })
        .collect()
}

/// Advance the staffing, then share each pool's receipt over its members.
fn staff(
    period: u64,
    attrited: &Attrited,
    requests: &[StaffingWorkRequest],
) -> Result<Staffed, BenchError> {
    let advance = staffing_error(period, BenchStage::AdvanceStaffing);
    let distribute = staffing_error(period, BenchStage::Distribute);
    let transition = engine::advance_staffing(&attrited.staffing, requests).map_err(advance)?;
    let mut receipts = Vec::new();
    let mut kept = Vec::with_capacity(attrited.members.len());
    for (receipt, held) in transition.receipts().iter().zip(&attrited.members) {
        if receipt.binding().pool_id() != held.pool_id {
            return Err(distribute(StaffingError::PopulationInvariant));
        }
        let rows =
            engine::distribute_staffing_members(receipt, &held.members).map_err(&distribute)?;
        kept.push(PoolMembers {
            pool_id: held.pool_id,
            members: next_members(&rows).map_err(&distribute)?,
        });
        receipts.extend(rows);
    }
    let mut member_labor = receipts
        .iter()
        .map(|row| {
            Ok(MemberLaborCapacityRow {
                member_id: row.member.member_id(),
                period: row.period.checked_add(1).ok_or(StaffingError::Arithmetic)?,
                available_hours: row.next_opening_hours,
            })
        })
        .collect::<Result<Vec<_>, StaffingError>>()
        .map_err(&distribute)?;
    member_labor.sort_unstable_by_key(|row| (row.period, row.member_id));
    let next_labor = transition.next_labor().to_vec();
    Ok(Staffed {
        staffing: transition.into_state(),
        members: kept,
        receipts,
        next_labor,
        member_labor,
    })
}

/// The opening's staffing: each seed's pool and members, in the order of the seeds.
fn opening_staffing(
    opening: &EconomicOpening,
    period: u64,
) -> Result<(StaffingState, Vec<PoolMembers>), StaffingError> {
    let mut pools = Vec::with_capacity(opening.staffing.len());
    let mut members = Vec::with_capacity(opening.staffing.len());
    for seed in &opening.staffing {
        let mut employed = 0_u64;
        let mut reserve = 0_u64;
        let mut states = Vec::with_capacity(seed.members.len());
        for member in &seed.members {
            employed = employed
                .checked_add(member.employed)
                .ok_or(StaffingError::Arithmetic)?;
            reserve = reserve
                .checked_add(member.reserve)
                .ok_or(StaffingError::Arithmetic)?;
            states.push(StaffingMemberState::try_new(
                member.member.clone(),
                member.employed,
                member.reserve,
            )?);
        }
        pools.push(StaffingPoolState::try_new(
            seed.pool.clone(),
            employed,
            reserve,
            seed.previous_unretained_hours,
        )?);
        members.push(PoolMembers {
            pool_id: seed.pool.pool_id(),
            members: states,
        });
    }
    let state = StaffingState::try_new(period, pools)?;
    members.sort_unstable_by_key(|held| held.pool_id);
    Ok((state, members))
}

/// The seekers' rows join the opening: their members after each pool's own, their terms and hours in the
/// order the engine admits (terms by site, unit and member; hours by period and member).
fn add_seekers(
    period: u64,
    state: &mut MaterialCircuitState,
    members: &mut [PoolMembers],
    rows: SeekerRows,
) -> Result<(), BenchError> {
    for (pool, member) in rows.members {
        let at = members
            .binary_search_by_key(&pool, |held| held.pool_id)
            .map_err(|_| BenchError::Arithmetic { period })?;
        members[at].members.push(member);
    }
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Err(engine_failed(period, BenchStage::Open)(
            MaterialCircuitError::MonetaryInvariant,
        ));
    };
    economy.employment.extend(rows.terms);
    economy
        .employment
        .sort_unstable_by_key(|row| (row.site_id, row.unit_id, row.member_id));
    economy.member_labor.extend(rows.hours);
    economy
        .member_labor
        .sort_unstable_by_key(|row| (row.period, row.member_id));
    Ok(())
}

/// One place for each location that has a pool, places in location order, pools in site order.
fn opening_places(opening: &EconomicOpening) -> Result<Vec<StaffingPlace>, BenchError> {
    let locations: BTreeMap<SiteId, EconomicLocation> = opening
        .sites
        .iter()
        .map(|site| (site.site_id, site.location))
        .collect();
    let mut by_place = BTreeMap::<EconomicLocation, Vec<(SiteId, StaffingPoolId)>>::new();
    for seed in &opening.staffing {
        let site = seed.pool.site_id();
        let place =
            locations
                .get(&site)
                .ok_or(BenchError::Opening(EconomicCatalogError::Opening(
                    "a pool's site is not a site of the opening",
                )))?;
        by_place
            .entry(*place)
            .or_default()
            .push((site, seed.pool.pool_id()));
    }
    Ok(by_place
        .into_values()
        .map(|mut pools| {
            pools.sort_unstable();
            StaffingPlace {
                pools: pools.into_iter().map(|(_, pool)| pool).collect(),
            }
        })
        .collect())
}

/// The state's recurring economy.
fn recurring_of(
    period: u64,
    state: &MaterialCircuitState,
) -> Result<&RecurringEconomy, BenchError> {
    monetary(period, state)?
        .recurring
        .as_deref()
        .ok_or_else(|| {
            engine_failed(period, BenchStage::Read)(MaterialCircuitError::MonetaryInvariant)
        })
}

/// The production policies the close raised above the period's plan: the plan receipt's batches for
/// a goods process; for a service, the batches of the service market's planned quantity (the market
/// writes the service's plan at every close, before rule A6 runs); for any other process, the
/// batches it held at the open.
fn spare_money_raised(
    period: u64,
    catalog: &MaterialCatalog,
    before: &MaterialCircuitState,
    transition: &MaterialCircuitTransition,
) -> Result<u64, BenchError> {
    let (plans, after) = (&transition.production_plans, &transition.state);
    let mut planned: BTreeMap<ProcessId, u64> = recurring_of(period, before)?
        .production
        .iter()
        .map(|policy| (policy.process_id, policy.planned_batches))
        .collect();
    for plan in plans {
        planned.insert(plan.process_id, plan.planned_batches);
    }
    for market in &transition.service_markets {
        let per_batch = catalog
            .process_outputs
            .binary_search_by_key(&market.process_id, |o| o.process_id)
            .ok()
            .map(|i| catalog.process_outputs[i].quantity_per_batch)
            .filter(|per_batch| *per_batch > 0)
            .ok_or(BenchError::Arithmetic { period })?;
        planned.insert(
            market.process_id,
            market.planned_quantity.div_ceil(per_batch),
        );
    }
    let raised = recurring_of(period, after)?
        .production
        .iter()
        .filter(|policy| {
            planned
                .get(&policy.process_id)
                .is_some_and(|base| policy.planned_batches > *base)
        })
        .count();
    u64::try_from(raised).map_err(|_| BenchError::Arithmetic { period })
}

/// The receipts of the transition, in the family the reader reads.
fn tick_receipts(period: u64, transition: &mut MaterialCircuitTransition) -> MaterialTickReceipts {
    MaterialTickReceipts {
        agency_paid: Vec::new(),
        household_time: mem::take(&mut transition.household_time),
        household_lifecycle: mem::take(&mut transition.household_lifecycle),
        resident_workforce_attrition: mem::take(&mut transition.resident_workforce_attrition),
        aid: mem::take(&mut transition.aid),
        collections: mem::take(&mut transition.collections),
        installation: mem::take(&mut transition.installation),
        installation_decisions: mem::take(&mut transition.installation_decisions),
        equipment_wear: mem::take(&mut transition.equipment_wear),
        investment: mem::take(&mut transition.investment),
        staffing_members: mem::take(&mut transition.staffing_members),
        member_labor_use: mem::take(&mut transition.member_labor_use),
        public_budgets: mem::take(&mut transition.public_budgets),
        taxes: mem::take(&mut transition.taxes),
        distributions: mem::take(&mut transition.distributions),
        company_basis: mem::take(&mut transition.company_basis),
        company_distributions: mem::take(&mut transition.company_distributions),
        contributions: mem::take(&mut transition.contributions),
        service_performance: mem::take(&mut transition.service_performance),
        household_services: mem::take(&mut transition.household_services),
        service_markets: mem::take(&mut transition.service_markets),
        service_outputs: mem::take(&mut transition.service_outputs),
        income: mem::take(&mut transition.income),
        resolve_tick: period,
        household_demand: mem::take(&mut transition.household_demand),
        household_consumption: mem::take(&mut transition.household_consumption),
        procurement: mem::take(&mut transition.procurement),
        production_plans: mem::take(&mut transition.production_plans),
        prices: mem::take(&mut transition.prices),
        money_transfers: mem::take(&mut transition.money_transfers),
        wage_accruals: mem::take(&mut transition.wage_accruals),
        labor_use: mem::take(&mut transition.labor_use),
        production: mem::take(&mut transition.production),
        dispatches: mem::take(&mut transition.dispatches),
        losses: mem::take(&mut transition.losses),
        arrivals: mem::take(&mut transition.arrivals),
        deliveries: mem::take(&mut transition.deliveries),
        realizations: mem::take(&mut transition.realizations),
        handling: mem::take(&mut transition.handling),
        local_fulfillments: mem::take(&mut transition.local_fulfillments),
        local_transfers: mem::take(&mut transition.local_transfers),
        maintenance: transition.maintenance.take(),
    }
}

impl CountryBench {
    /// The opening as the campaign compiler builds it, with the companies' portfolio choice left out.
    /// A set with benefits first steps a baseline bench one period to read the `no_earner` amount, then
    /// opens on the opening with the fund.
    ///
    /// # Errors
    /// `BenchError::Opening` when the opening does not compile; `Engine { stage: Open, .. }` when the catalog
    /// with portfolios off is refused.
    pub fn open(opening: &EconomicOpening, set: RuleSet) -> Result<Self, BenchError> {
        Self::open_with(opening, set, Wages::Default)
    }

    /// As `open`, with the wage a seeker is offered where its pool pays none.
    ///
    /// # Errors
    /// As `open`; `BenchError::Opening` also when `Wages::PlaceAverage` finds no paid person in a place.
    pub fn open_with(
        opening: &EconomicOpening,
        set: RuleSet,
        wages: Wages,
    ) -> Result<Self, BenchError> {
        if !set.has_benefits() {
            return Self::open_plain(opening, set, wages);
        }
        let first = Self::open_plain(opening, RuleSet::None, wages)?.step()?;
        let per_person = country_fund::no_earner_per_person(opening, &first)?;
        let funded = country_fund::with_fund(opening, per_person)?;
        let mut bench = Self::open_plain(&funded, set, wages)?;
        bench.no_earner_per_person = Some(per_person);
        Ok(bench)
    }

    /// The `no_earner` amount a set with benefits opened with.
    pub const fn no_earner_per_person(&self) -> Option<Currency> {
        self.no_earner_per_person
    }

    fn open_plain(
        opening: &EconomicOpening,
        set: RuleSet,
        wages: Wages,
    ) -> Result<Self, BenchError> {
        let compiled = opening.compile().map_err(BenchError::Opening)?;
        let mut state = compiled.state;
        let period = state.period;
        let mut definition = compiled.catalog.into_definition();
        definition.company_portfolios = None;
        definition.market_clearing = country_rules::market_policy(opening, set)?;
        let catalog = MaterialCatalog::try_new(definition)
            .map_err(engine_failed(period, BenchStage::Open))?;
        let (staffing, mut members) =
            opening_staffing(opening, period).map_err(staffing_error(period, BenchStage::Open))?;
        let places = opening_places(opening)?;
        if set.seeks_in_place() {
            let rows = country_seekers::seeker_rows(opening, &places, wages)?;
            add_seekers(period, &mut state, &mut members, rows)?;
        }
        let opening_money = total_money(period, &state)?;
        Ok(Self {
            catalog,
            state,
            staffing,
            members,
            places,
            standing: WorkplaceStanding::opening(),
            set,
            opening_money,
            no_earner_per_person: None,
        })
    }

    pub const fn catalog(&self) -> &MaterialCatalog {
        &self.catalog
    }

    pub const fn state(&self) -> &MaterialCircuitState {
        &self.state
    }

    /// Every pool's members after the last period closed.
    pub fn members(&self) -> &[PoolMembers] {
        &self.members
    }

    /// The places: the pools whose people look for work at one another.
    pub fn places(&self) -> &[StaffingPlace] {
        &self.places
    }

    /// The staffing after the last period closed.
    pub const fn staffing(&self) -> &StaffingState {
        &self.staffing
    }

    /// Close one period. A refusal leaves the bench as it was.
    ///
    /// # Errors
    /// The period's refusal, typed by stage; the checks of decision 5.
    pub fn step(&mut self) -> Result<BenchPeriod, BenchError> {
        let started = Instant::now();
        let period = self.state.period;
        let Stepped {
            mut transition,
            staffing,
            members,
            standing,
        } = self.advance(period)?;
        let elapsed = started.elapsed();
        let spare_money_raised =
            spare_money_raised(period, &self.catalog, &self.state, &transition)?;
        let receipts = tick_receipts(period, &mut transition);
        let period_row = BenchPeriod {
            period,
            receipts,
            market_clearings: mem::take(&mut transition.market_clearings),
            adjustments: mem::take(&mut transition.adjustments),
            public_programs: mem::take(&mut transition.public_programs),
            closing_members: members.clone(),
            spare_money_raised,
            elapsed,
        };
        self.state = transition.state;
        self.staffing = staffing;
        self.members = members;
        self.standing = standing;
        Ok(period_row)
    }

    /// The period's close, staffing and checks, with nothing of the bench changed.
    fn advance(&self, period: u64) -> Result<Stepped, BenchError> {
        let closed = self.close(period)?;
        let before = labor_force(period, &self.staffing)?;
        let attrited = attrition(
            period,
            &self.staffing,
            &self.members,
            closed.household_lifecycle(),
        )?;
        let removed = removed_persons(period, &attrited.rows)?;
        let after_attrition = labor_force(period, &attrited.staffing)?;
        check_labor_force(period, before, removed, after_attrition)?;
        if self.set.seeks_in_place() {
            return self.finish_in_places(period, closed, attrited, after_attrition);
        }
        let bindings: Vec<_> = attrited
            .staffing
            .pools()
            .iter()
            .map(|pool| pool.binding().clone())
            .collect();
        let requests = closed
            .staffing_requests(&self.catalog, &bindings)
            .map_err(engine_failed(period, BenchStage::StaffingRequests))?;
        let staffed = staff(period, &attrited, &requests)?;
        check_labor_force(
            period,
            after_attrition,
            0,
            labor_force(period, &staffed.staffing)?,
        )?;
        let mut transition = closed
            .finish_with_staffing(
                &self.catalog,
                staffed.next_labor,
                staffed.member_labor,
                &staffed.receipts,
            )
            .map_err(engine_failed(period, BenchStage::Finish))?;
        transition.staffing_members = staffed.receipts;
        transition.resident_workforce_attrition = attrited.rows;
        self.check_period(period, &transition)?;
        Ok(Stepped {
            transition,
            staffing: staffed.staffing,
            members: staffed.members,
            standing: self.standing.clone(),
        })
    }

    /// The close; a set with the stop rule closes with the standing the last period left.
    fn close(&self, period: u64) -> Result<ClosedMaterialPeriod, BenchError> {
        let closed = if self.set.seeks_in_place() {
            engine::close_material_period_with_standing(&self.catalog, &self.state, &self.standing)
        } else {
            engine::close_material_period(&self.catalog, &self.state)
        };
        closed.map_err(engine_failed(period, BenchStage::Close))
    }

    /// The seekers' path: the engine's decision, then the moves and the stop rule's test, then the finish.
    fn finish_in_places(
        &self,
        period: u64,
        closed: ClosedMaterialPeriod,
        attrited: Attrited,
        after_attrition: u64,
    ) -> Result<Stepped, BenchError> {
        let placed = closed
            .staff_in_places(
                &self.catalog,
                &attrited.staffing,
                &attrited.members,
                &self.places,
            )
            .map_err(|error| BenchError::Place { period, error })?;
        check_labor_force(
            period,
            after_attrition,
            0,
            labor_force(period, &placed.state)?,
        )?;
        let mut transition = closed
            .finish_with_place_staffing(&self.catalog, &placed)
            .map_err(engine_failed(period, BenchStage::Finish))?;
        transition.staffing_members = placed.member_receipts;
        transition.resident_workforce_attrition = attrited.rows;
        self.check_period(period, &transition)?;
        Ok(Stepped {
            transition,
            staffing: placed.state,
            members: placed.members,
            standing: placed.standing,
        })
    }

    /// Money and persons of the closed period, by the bench's two checks.
    fn check_period(
        &self,
        period: u64,
        transition: &MaterialCircuitTransition,
    ) -> Result<(), BenchError> {
        check_money(
            period,
            self.opening_money,
            total_money(period, &transition.state)?,
        )?;
        let (births, deaths) = births_and_deaths(period, &transition.household_lifecycle)?;
        check_persons(
            period,
            cohort_persons(period, &self.state)?,
            births,
            deaths,
            cohort_persons(period, &transition.state)?,
        )
    }
}

/// The record's first lines.
pub fn bench_header(set: RuleSet) -> Value {
    json!({
        "bench": "country-bench-2026-11-24",
        "set": set.name(),
        "leaves_out": [
            "The companies' portfolio choice is off: the catalog's company_portfolios is None. Company payouts stay.",
            "No City PD attendance: its inputs come only from a selected City PD intent.",
            "No County Review period.",
            "No register checks: the tick's register validates and encodes every family, the bench runs only the engine's own checks.",
        ],
        "judged_against":
            "the bench's own baseline (baseline.json), never the record of 20 November",
    })
}
