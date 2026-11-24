//! The runner: one period is the engine's own, in the order of the game's staffed run.

use std::mem;

use crate::doubled::{self, Figures, World, HORIZON};
use crate::runner::error::{RunnerError, Stage};
use crate::runner::result::{Closing, PeriodReceipts, PeriodResult, PeriodSummary};
use crate::runner::rules::{RuleError, RuleOn, Switch};
use crate::shocks::{Lasts, Places, Shock, ShockBook, ShockError};
use crate::{Kind, OpeningPush, Place, Pushed, Workplace, WorldError};
use babylon_material_circuit::{
    self as engine, AdjustmentRule, CircuitAccounting, LaborCapacityRow, MaterialCatalog,
    MaterialCircuitError, MaterialCircuitState, MaterialCircuitTransition, MemberLaborCapacityRow,
    MonetaryCircuit, PlaceStaffing, PlaceStaffingError, PoolMembers, SiteId, StaffingError,
    StaffingMemberReceipt, StaffingMemberState, StaffingPoolBinding, StaffingState,
    StaffingWorkRequest, WorkplaceStanding,
};

/// What one successful period hands back to the runner.
struct Stepped {
    result: PeriodResult,
    state: MaterialCircuitState,
    staffing: StaffingState,
    members: Vec<PoolMembers>,
    standing: WorkplaceStanding,
}

/// What the staffing of one period decided.
struct Staffed {
    labor: Vec<LaborCapacityRow>,
    member_labor: Vec<MemberLaborCapacityRow>,
    members: Vec<StaffingMemberReceipt>,
    kept: Vec<PoolMembers>,
    staffing: StaffingState,
    employed: [u64; 8],
    reserve: [u64; 8],
    asked: [u64; 8],
    /// What the stop rule remembers after the close; the standing it had when the rule is not on.
    standing: WorkplaceStanding,
}

/// What the world held when it opened: the runner refuses a period that does not keep it.
struct Opening {
    money: i128,
    persons: u64,
    /// Each place's people, by `Workplace::index`: the persons of its workers.
    workers: [u64; 8],
}

/// What a catalog of the cache was built from: the figures of production and the rules it asks for.
#[derive(Clone, Debug, PartialEq, Eq)]
struct CatalogKey {
    figures: Figures,
    rules: Vec<AdjustmentRule>,
}

/// The doubled world, stepped one period at a time. The runner keeps every period's result and
/// never the state; a refusal stops it, and starting over is a new runner.
pub struct Runner {
    world: World,
    opening: Opening,
    state: MaterialCircuitState,
    staffing: StaffingState,
    members: Vec<PoolMembers>,
    standing: WorkplaceStanding,
    bindings: Vec<StaffingPoolBinding>,
    catalogs: Vec<(CatalogKey, MaterialCatalog)>,
    rules: Vec<RuleOn>,
    book: ShockBook,
    history: Vec<PeriodResult>,
    stopped: Option<RunnerError>,
}

impl Runner {
    /// The scene's world at its opening.
    ///
    /// # Errors
    /// As `open_world`.
    pub fn open() -> Result<Self, RunnerError> {
        Self::open_world(&World::scene())
    }

    /// The world at its opening. A pushed power cut is struck in the book from period 1, until started over.
    /// The opening's money, persons and each place's people are measured here and checked after every period.
    /// The runner keeps the world (each period's catalog is built from it) and every pool's members.
    ///
    /// # Errors
    /// `RunnerError::World` when the world or the engine refuses the opening.
    pub fn open_world(world: &World) -> Result<Self, RunnerError> {
        let state = doubled::opening_state_of(world)?;
        let (bindings, staffing) = doubled::staffing_of(world)?;
        let members = doubled::pool_members_of(world)?;
        let opening = measure(world, &state)?;
        let mut book = ShockBook::default();
        if let Some(Pushed {
            push: OpeningPush::PowerCut,
            places,
        }) = world.pushed
        {
            book.strike(Shock::PowerCut, places, Lasts::UntilLifted, state.period)?;
        }
        let mut runner = Self {
            world: world.clone(),
            opening,
            state,
            staffing,
            members,
            standing: WorkplaceStanding::opening(),
            bindings,
            catalogs: Vec::new(),
            rules: Vec::new(),
            book,
            history: Vec::new(),
            stopped: None,
        };
        let figures = runner.book.figures(runner.state.period);
        runner.ensure_catalog(&figures, &[])?;
        for rule in &world.rules {
            runner.turn_on(*rule)?;
        }
        Ok(runner)
    }

    /// The world the runner opened.
    #[must_use]
    pub const fn world(&self) -> &World {
        &self.world
    }

    /// The state after the last step: the opening of the next period.
    #[must_use]
    pub const fn state(&self) -> &MaterialCircuitState {
        &self.state
    }

    /// The staffing after the last step: the opening of the next period.
    #[must_use]
    pub const fn staffing(&self) -> &StaffingState {
        &self.staffing
    }

    /// What the rules remember of each workplace after the last step; `WorkplaceStanding::opening()` before it.
    #[must_use]
    pub const fn standing(&self) -> &WorkplaceStanding {
        &self.standing
    }

    /// The members the runner keeps between periods: every pool's, one for each household of its place.
    #[must_use]
    pub fn members(&self) -> &[PoolMembers] {
        &self.members
    }

    /// The catalog the last step closed under; `None` before the first step.
    #[must_use]
    pub fn catalog(&self) -> Option<&MaterialCatalog> {
        let last = self.history.last()?;
        let key = CatalogKey {
            figures: last.figures,
            rules: last.rules.clone(),
        };
        self.catalogs
            .iter()
            .find(|(known, _)| *known == key)
            .map(|(_, catalog)| catalog)
    }

    /// The period the next step closes.
    #[must_use]
    pub const fn next_period(&self) -> u64 {
        self.state.period
    }

    /// Every period closed so far, oldest first.
    #[must_use]
    pub fn history(&self) -> &[PeriodResult] {
        &self.history
    }

    /// The refusal that stopped the run, if one did.
    #[must_use]
    pub const fn stopped(&self) -> Option<&RunnerError> {
        self.stopped.as_ref()
    }

    /// Close one period.
    ///
    /// # Errors
    /// The refusal of the period, which also stops the run; `RunnerError::Stopped` when it was
    /// already stopped.
    pub fn step(&mut self) -> Result<&PeriodResult, RunnerError> {
        if self.stopped.is_some() {
            return Err(RunnerError::Stopped);
        }
        match self.advance() {
            Ok(stepped) => {
                self.state = stepped.state;
                self.bindings = stepped
                    .staffing
                    .pools()
                    .iter()
                    .map(|pool| pool.binding().clone())
                    .collect();
                self.staffing = stepped.staffing;
                self.members = stepped.members;
                self.standing = stepped.standing;
                self.history.push(stepped.result);
                self.history.last().ok_or(RunnerError::Stopped)
            }
            Err(error) => {
                self.stopped = Some(error.clone());
                Err(error)
            }
        }
    }

    /// The shocks struck so far.
    #[must_use]
    pub const fn shocks(&self) -> &ShockBook {
        &self.book
    }

    /// Strike a shock from the next period on.
    ///
    /// # Errors
    /// `ShockError` when the shock already holds, cannot last so long, or the run is stopped;
    /// nothing is struck then.
    pub fn strike(&mut self, shock: Shock, places: Places, lasts: Lasts) -> Result<(), ShockError> {
        if self.stopped.is_some() {
            return Err(ShockError::Stopped);
        }
        self.book.strike(shock, places, lasts, self.state.period)
    }

    /// Lift a shock from the next period on.
    ///
    /// # Errors
    /// `ShockError` when the shock does not hold, cannot be lifted, or the run is stopped.
    pub fn lift(&mut self, shock: Shock, place: Place) -> Result<(), ShockError> {
        if self.stopped.is_some() {
            return Err(ShockError::Stopped);
        }
        self.book.lift(shock, place, self.state.period)
    }

    /// Turn a rule on from the next period (`next_period()`, the `from` a strike gets). It holds until the run is
    /// started over.
    ///
    /// # Errors
    /// `RuleError`, in this order: `Stopped`; `AlreadyOn` (the same kind, any `outlay_periods`); `Waits` (a rule of
    /// `needs` is not on); `Refused` (the catalog of the next period's figures with the rule added). Nothing
    /// changes then.
    pub fn turn_on(&mut self, rule: AdjustmentRule) -> Result<(), RuleError> {
        if self.stopped.is_some() {
            return Err(RuleError::Stopped);
        }
        if let Some(on) = self.rules.iter().find(|on| same_kind(on.rule, rule)) {
            return Err(RuleError::AlreadyOn {
                rule: on.rule,
                from: on.from,
            });
        }
        let missing = self.missing_needs(rule);
        if !missing.is_empty() {
            return Err(RuleError::Waits {
                rule,
                needs: missing,
            });
        }
        let from = self.state.period;
        let mut with = self.rules_at(from);
        with.push(rule);
        with.sort();
        let figures = self.book.figures(from);
        self.ensure_catalog(&figures, &with)
            .map_err(|error| RuleError::Refused { rule, error })?;
        self.rules.push(RuleOn { rule, from });
        Ok(())
    }

    /// The rules on, in the order turned on.
    #[must_use]
    pub fn rules(&self) -> &[RuleOn] {
        &self.rules
    }

    /// The rules the catalog of `period` asks for, in the order of `AdjustmentRule`.
    #[must_use]
    pub fn rules_at(&self, period: u64) -> Vec<AdjustmentRule> {
        let mut rules: Vec<AdjustmentRule> = self
            .rules
            .iter()
            .filter(|on| on.from <= period)
            .map(|on| on.rule)
            .collect();
        rules.sort();
        rules
    }

    /// Where the switch of a rule of this kind stands.
    #[must_use]
    pub fn switch(&self, rule: AdjustmentRule) -> Switch {
        if let Some(on) = self.rules.iter().find(|on| same_kind(on.rule, rule)) {
            return Switch::On { from: on.from };
        }
        let needs = self.missing_needs(rule);
        if needs.is_empty() {
            Switch::Ready
        } else {
            Switch::Waits { needs }
        }
    }

    /// The rules this one needs that are not on, in the order of `AdjustmentRule`.
    fn missing_needs(&self, rule: AdjustmentRule) -> Vec<AdjustmentRule> {
        rule.needs()
            .iter()
            .copied()
            .filter(|need| !self.rules.iter().any(|on| same_kind(on.rule, *need)))
            .collect()
    }

    fn ensure_catalog(
        &mut self,
        figures: &Figures,
        rules: &[AdjustmentRule],
    ) -> Result<(), WorldError> {
        let key = CatalogKey {
            figures: *figures,
            rules: rules.to_vec(),
        };
        if !self.catalogs.iter().any(|(known, _)| *known == key) {
            let catalog = doubled::catalog_of(&self.world, figures, rules)?;
            self.catalogs.push((key, catalog));
        }
        Ok(())
    }

    fn advance(&mut self) -> Result<Stepped, RunnerError> {
        let period = self.state.period;
        let past = period.checked_add(2).is_none_or(|last| last > HORIZON);
        if past {
            return Err(RunnerError::PastHorizon { period });
        }
        let figures = self.book.figures(period);
        let rules = self.rules_at(period);
        self.ensure_catalog(&figures, &rules)?;
        let key = CatalogKey {
            figures,
            rules: rules.clone(),
        };
        let catalog = self
            .catalogs
            .iter()
            .find(|(known, _)| *known == key)
            .map(|(_, catalog)| catalog)
            .ok_or(RunnerError::World(WorldError::Arithmetic))?;
        let closed = if rules.contains(&AdjustmentRule::StopWithoutPay) {
            engine::close_material_period_with_standing(catalog, &self.state, &self.standing)
        } else {
            engine::close_material_period(catalog, &self.state)
        }
        .map_err(|error| engine_error(period, Stage::Close, error))?;
        let requests = closed
            .staffing_requests(catalog, &self.bindings)
            .map_err(|error| engine_error(period, Stage::StaffingRequests, error))?;
        let seeking = rules.contains(&AdjustmentRule::SeekingInPlace);
        let (staffed, transition) = if seeking {
            let placed = closed
                .staff_in_places(catalog, &self.staffing, &self.members, &doubled::places())
                .map_err(|error| place_error(period, &error))?;
            let transition = closed
                .finish_with_place_staffing(catalog, &placed)
                .map_err(|error| engine_error(period, Stage::Finish, error))?;
            (placed_staffing(placed, &requests)?, transition)
        } else {
            let staffed = staff(
                period,
                &self.staffing,
                &self.members,
                &requests,
                &self.standing,
            )?;
            let transition = closed
                .finish_with_staffing(
                    catalog,
                    staffed.labor.clone(),
                    staffed.member_labor.clone(),
                    &staffed.members,
                )
                .map_err(|error| engine_error(period, Stage::Finish, error))?;
            (staffed, transition)
        };
        check_conserved(
            period,
            &self.opening,
            &transition.state,
            (&staffed.employed, &staffed.reserve),
            seeking,
        )?;
        let state_digest = engine::material_circuit_state_digest(catalog, &transition.state)
            .map_err(|error| engine_error(period, Stage::Digest, error))?;
        let (closing, summary) = read_closing(
            period,
            &figures,
            &transition,
            staffed.employed,
            staffed.reserve,
        )?;
        let result = PeriodResult {
            period,
            figures,
            rules,
            members: staffed.members,
            closing,
            summary,
            state_digest,
            asked: staffed.asked,
            receipts: take_receipts(&transition),
        };
        Ok(Stepped {
            result,
            state: transition.state,
            staffing: staffed.staffing,
            members: staffed.kept,
            standing: staffed.standing,
        })
    }
}

/// Whether two rules are of one kind: the restart with any periods of outlay is one kind.
fn same_kind(a: AdjustmentRule, b: AdjustmentRule) -> bool {
    mem::discriminant(&a) == mem::discriminant(&b)
}

fn engine_error(period: u64, stage: Stage, error: MaterialCircuitError) -> RunnerError {
    RunnerError::Engine {
        period,
        stage,
        error,
    }
}

fn site_workplace(site: SiteId) -> Result<Workplace, RunnerError> {
    Workplace::from_site(site).ok_or_else(|| {
        RunnerError::World(WorldError::Location(
            "a site outside the doubled world".to_owned(),
        ))
    })
}

/// Advance the staffing, then share each pool's receipt over its members, who are kept.
fn staff(
    period: u64,
    staffing: &StaffingState,
    members: &[PoolMembers],
    requests: &[StaffingWorkRequest],
    standing: &WorkplaceStanding,
) -> Result<Staffed, RunnerError> {
    let transition =
        engine::advance_staffing(staffing, requests).map_err(|error| RunnerError::Staffing {
            period,
            stage: Stage::AdvanceStaffing,
            error,
        })?;
    let distribution = |error: StaffingError| RunnerError::Staffing {
        period,
        stage: Stage::DistributeMembers,
        error,
    };
    let mut shares = Vec::new();
    let mut kept = members.to_vec();
    let mut employed = [0; 8];
    let mut reserve = [0; 8];
    for receipt in transition.receipts() {
        let workplace = site_workplace(receipt.binding().site_id())?;
        let pool = members
            .iter()
            .find(|row| row.pool_id == receipt.binding().pool_id())
            .ok_or(RunnerError::World(WorldError::Arithmetic))?;
        let rows =
            engine::distribute_staffing_members(receipt, &pool.members).map_err(distribution)?;
        let next = rows
            .iter()
            .map(|row| next_member(workplace, row))
            .collect::<Result<Vec<_>, StaffingError>>()
            .map_err(distribution)?;
        if let Some(slot) = kept
            .iter_mut()
            .find(|row| row.pool_id == receipt.binding().pool_id())
        {
            slot.members = next;
        }
        shares.extend(rows);
        employed[workplace.index()] = receipt.closing_employed();
        reserve[workplace.index()] = receipt.closing_reserve();
    }
    let labor = transition.next_labor().to_vec();
    let member_labor = member_labor_rows(&labor, &kept)?;
    let asked = hours_asked(requests)?;
    Ok(Staffed {
        labor,
        member_labor,
        members: shares,
        kept,
        staffing: transition.into_state(),
        employed,
        reserve,
        asked,
        standing: standing.clone(),
    })
}

/// The staffing of a period by place, in the shape the rest of the period reads: the engine's decision for the
/// members' receipts, the persons of each workplace after the moves.
fn placed_staffing(
    placed: PlaceStaffing,
    requests: &[StaffingWorkRequest],
) -> Result<Staffed, RunnerError> {
    let mut employed = [0; 8];
    let mut reserve = [0; 8];
    for pool in placed.state.pools() {
        let workplace = site_workplace(pool.binding().site_id())?;
        employed[workplace.index()] = pool.employed();
        reserve[workplace.index()] = pool.reserve();
    }
    Ok(Staffed {
        labor: placed.labor,
        member_labor: placed.member_labor,
        members: placed.member_receipts,
        kept: placed.members,
        staffing: placed.state,
        employed,
        reserve,
        asked: hours_asked(requests)?,
        standing: placed.standing,
    })
}

/// A refusal of `staff_in_places`, as the runner says it.
fn place_error(period: u64, error: &PlaceStaffingError) -> RunnerError {
    match error {
        PlaceStaffingError::Circuit(error) => engine_error(period, Stage::StaffInPlaces, *error),
        PlaceStaffingError::Staffing(error) => RunnerError::Staffing {
            period,
            stage: Stage::StaffInPlaces,
            error: *error,
        },
    }
}

/// A member after its share: the same member with its closing persons. A pair member holds nobody on
/// this path.
fn next_member(
    workplace: Workplace,
    row: &StaffingMemberReceipt,
) -> Result<StaffingMemberState, StaffingError> {
    let own = row.member.member_id() == workplace.member_id();
    if !own && (row.closing_employed != 0 || row.closing_reserve != 0) {
        return Err(StaffingError::PopulationInvariant);
    }
    StaffingMemberState::try_new(
        row.member.clone(),
        row.closing_employed,
        row.closing_reserve,
    )
}

/// One row of hours for each member: the pool's for its own member, none for a pair member.
fn member_labor_rows(
    labor: &[LaborCapacityRow],
    kept: &[PoolMembers],
) -> Result<Vec<MemberLaborCapacityRow>, RunnerError> {
    let mut rows = Vec::new();
    for row in labor {
        let workplace = site_workplace(row.site_id)?;
        let pool = kept
            .iter()
            .find(|pool| pool.pool_id == workplace.pool_id())
            .ok_or(RunnerError::World(WorldError::Arithmetic))?;
        for member in &pool.members {
            let own = member.binding().member_id() == workplace.member_id();
            rows.push(MemberLaborCapacityRow {
                member_id: member.binding().member_id(),
                period: row.period,
                available_hours: if own { row.available } else { 0 },
            });
        }
    }
    Ok(rows)
}

/// Hours asked of staffing, by workplace: the sum over the period's requests.
fn hours_asked(requests: &[StaffingWorkRequest]) -> Result<[u64; 8], RunnerError> {
    let mut asked = [0_u64; 8];
    for request in requests {
        add_to(
            &mut asked,
            site_workplace(request.site_id())?,
            request.hours(),
        )?;
    }
    Ok(asked)
}

/// What the world holds at its opening: money, cohort persons and each place's people.
fn measure(world: &World, state: &MaterialCircuitState) -> Result<Opening, RunnerError> {
    let money = monetary(state.period, state)?
        .book
        .total_cash_and_reserves()
        .map_err(|error| engine_error(state.period, Stage::Read, error.into()))?
        .micro_units();
    let mut workers = [0_u64; 8];
    for workplace in Workplace::ALL {
        workers[workplace.index()] = world.persons(workplace.workers());
    }
    Ok(Opening {
        money,
        persons: cohort_persons(state, state.period)?,
        workers,
    })
}

fn monetary(period: u64, state: &MaterialCircuitState) -> Result<&MonetaryCircuit, RunnerError> {
    match &state.accounting {
        CircuitAccounting::Monetary(circuit) => Ok(circuit),
        CircuitAccounting::PhysicalControl => Err(engine_error(
            period,
            Stage::Read,
            MaterialCircuitError::MonetaryInvariant,
        )),
    }
}

/// Persons of every cohort of the state.
fn cohort_persons(state: &MaterialCircuitState, period: u64) -> Result<u64, RunnerError> {
    let circuit = monetary(period, state)?;
    let recurring = circuit.recurring.as_ref().ok_or_else(|| {
        engine_error(period, Stage::Read, MaterialCircuitError::MonetaryInvariant)
    })?;
    recurring
        .households
        .iter()
        .try_fold(0_u64, |sum, cohort| sum.checked_add(cohort.persons))
        .ok_or(RunnerError::World(WorldError::Arithmetic))
}

/// Money and persons are the opening's, or the period is refused.
fn check_conserved(
    period: u64,
    opening: &Opening,
    next: &MaterialCircuitState,
    (employed, reserve): (&[u64; 8], &[u64; 8]),
    seeking: bool,
) -> Result<(), RunnerError> {
    let money = monetary(period, next)?
        .book
        .total_cash_and_reserves()
        .map_err(|error| engine_error(period, Stage::Read, error.into()))?
        .micro_units();
    if money != opening.money {
        return Err(RunnerError::MoneyNotConserved {
            period,
            opening: opening.money,
            closing: money,
        });
    }
    let persons = cohort_persons(next, period)?;
    if persons != opening.persons {
        return Err(RunnerError::PersonsNotConserved {
            period,
            opening: opening.persons,
            closing: persons,
        });
    }
    let persons_of = |workplace: Workplace| -> Result<u64, RunnerError> {
        let i = workplace.index();
        employed[i]
            .checked_add(reserve[i])
            .ok_or(RunnerError::World(WorldError::Arithmetic))
    };
    for place in Place::ALL {
        let (mut pool, mut workers) = (0_u64, 0_u64);
        for workplace in Workplace::ALL.iter().filter(|w| w.place == place) {
            let held = persons_of(*workplace)?;
            // A workplace's people change only where the seekers move them: its place keeps them.
            if !seeking && held != opening.workers[workplace.index()] {
                return Err(RunnerError::PersonsNotConserved {
                    period,
                    opening: opening.workers[workplace.index()],
                    closing: held,
                });
            }
            pool = pool
                .checked_add(held)
                .ok_or(RunnerError::World(WorldError::Arithmetic))?;
            workers = workers
                .checked_add(opening.workers[workplace.index()])
                .ok_or(RunnerError::World(WorldError::Arithmetic))?;
        }
        if pool != workers {
            return Err(RunnerError::PersonsNotConserved {
                period,
                opening: workers,
                closing: pool,
            });
        }
    }
    Ok(())
}

/// The closing state's holdings and the period's measures.
fn read_closing(
    period: u64,
    figures: &Figures,
    transition: &MaterialCircuitTransition,
    employed: [u64; 8],
    reserve: [u64; 8],
) -> Result<(Closing, PeriodSummary), RunnerError> {
    let circuit = monetary(period, &transition.state)?;
    let recurring = circuit.recurring.as_ref().ok_or_else(|| {
        engine_error(period, Stage::Read, MaterialCircuitError::MonetaryInvariant)
    })?;
    let cash: Vec<_> = circuit
        .book
        .cash_accounts()
        .map(|(id, amount)| (*id, *amount))
        .collect();
    let total_money = circuit
        .book
        .total_cash_and_reserves()
        .map_err(|error| engine_error(period, Stage::Read, error.into()))?
        .micro_units();
    let summary = PeriodSummary {
        hours_attended: hours_attended(transition)?,
        made: made(figures, transition)?,
        employed,
        cash: cash
            .iter()
            .map(|(id, amount)| (*id, amount.micro_units()))
            .collect(),
        prices: recurring
            .offers
            .iter()
            .map(|offer| (offer.site_id, offer.good_id, offer.unit_price.micro_units()))
            .collect(),
        total_money,
        persons: cohort_persons(&transition.state, period)?,
    };
    let closing = Closing {
        cash,
        capital: circuit.costs.capital_accounts().cloned().collect(),
        ownership: circuit.financial.ownership.clone(),
        households: recurring.households.clone(),
        employed,
        reserve,
    };
    Ok((closing, summary))
}

/// Hours attended by workplace: funded hours and hours that need no wage.
fn hours_attended(transition: &MaterialCircuitTransition) -> Result<[u64; 8], RunnerError> {
    let mut hours = [0_u64; 8];
    for row in &transition.labor_use {
        let slot = hours
            .get_mut(site_workplace(row.site_id)?.index())
            .ok_or(RunnerError::World(WorldError::Arithmetic))?;
        *slot = row
            .funded_hours
            .checked_add(row.non_wage_hours)
            .and_then(|attended| slot.checked_add(attended))
            .ok_or(RunnerError::World(WorldError::Arithmetic))?;
    }
    Ok(hours)
}

/// Units made by workplace. A farm makes batches times its place's yield; a utility and a clinic
/// make what their service output says, counted once; a shop handles what it handles.
fn made(
    figures: &Figures,
    transition: &MaterialCircuitTransition,
) -> Result<[u64; 8], RunnerError> {
    let mut made = [0_u64; 8];
    let arithmetic = RunnerError::World(WorldError::Arithmetic);
    for row in &transition.production {
        let workplace = site_workplace(row.site_id)?;
        if workplace.kind != Kind::Farm {
            continue;
        }
        let units = row
            .produced_batches
            .checked_mul(
                *figures
                    .farm_yield
                    .get(workplace.place.index())
                    .ok_or_else(|| arithmetic.clone())?,
            )
            .ok_or_else(|| arithmetic.clone())?;
        add_to(&mut made, workplace, units)?;
    }
    for row in &transition.service_outputs {
        add_to(
            &mut made,
            site_workplace(row.site_id)?,
            row.produced_quantity,
        )?;
    }
    for row in &transition.handling {
        add_to(
            &mut made,
            site_workplace(row.site_id)?,
            row.handled_quantity,
        )?;
    }
    Ok(made)
}

fn add_to(slots: &mut [u64; 8], workplace: Workplace, units: u64) -> Result<(), RunnerError> {
    let slot = slots
        .get_mut(workplace.index())
        .ok_or(RunnerError::World(WorldError::Arithmetic))?;
    *slot = slot
        .checked_add(units)
        .ok_or(RunnerError::World(WorldError::Arithmetic))?;
    Ok(())
}

fn take_receipts(transition: &MaterialCircuitTransition) -> PeriodReceipts {
    PeriodReceipts {
        member_labor_use: transition.member_labor_use.clone(),
        labor_use: transition.labor_use.clone(),
        production: transition.production.clone(),
        service_outputs: transition.service_outputs.clone(),
        service_performance: transition.service_performance.clone(),
        household_services: transition.household_services.clone(),
        handling: transition.handling.clone(),
        local_transfers: transition.local_transfers.clone(),
        local_fulfillments: transition.local_fulfillments.clone(),
        procurement: transition.procurement.clone(),
        household_demand: transition.household_demand.clone(),
        household_consumption: transition.household_consumption.clone(),
        household_wants: transition.household_wants.clone(),
        household_tiers: transition.household_tiers.clone(),
        money_transfers: transition.money_transfers.clone(),
        wage_accruals: transition.wage_accruals.clone(),
        taxes: transition.taxes.clone(),
        public_programs: transition.public_programs.clone(),
        public_budgets: transition.public_budgets.clone(),
        distributions: transition.distributions.clone(),
        income: transition.income.clone(),
        prices: transition.prices.clone(),
        service_markets: transition.service_markets.clone(),
        market_clearings: transition.market_clearings.clone(),
        adjustments: transition.adjustments.clone(),
    }
}
