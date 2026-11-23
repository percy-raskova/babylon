//! The runner: one period is the engine's own, in the order of the game's staffed run.

use crate::doubled::{self, Figures, HORIZON, OPENING_MONEY, PERSONS};
use crate::runner::error::{RunnerError, Stage};
use crate::runner::result::{Closing, PeriodReceipts, PeriodResult, PeriodSummary};
use crate::{Kind, Workplace, WorldError};
use babylon_material_circuit::{
    self as engine, CircuitAccounting, LaborCapacityRow, MaterialCatalog, MaterialCircuitError,
    MaterialCircuitState, MaterialCircuitTransition, MemberLaborCapacityRow, MonetaryCircuit,
    SiteId, StaffingMemberReceipt, StaffingPoolBinding, StaffingState, StaffingWorkRequest,
};

/// What one successful period hands back to the runner.
struct Stepped {
    result: PeriodResult,
    state: MaterialCircuitState,
    staffing: StaffingState,
}

/// What the staffing of one period decided.
struct Staffed {
    labor: Vec<LaborCapacityRow>,
    members: Vec<StaffingMemberReceipt>,
    staffing: StaffingState,
    employed: [u64; 8],
    reserve: [u64; 8],
}

/// The doubled world, stepped one period at a time. The runner keeps every period's result and
/// never the state; a refusal stops it, and starting over is a new runner.
pub struct Runner {
    state: MaterialCircuitState,
    staffing: StaffingState,
    bindings: Vec<StaffingPoolBinding>,
    catalogs: Vec<(Figures, MaterialCatalog)>,
    history: Vec<PeriodResult>,
    stopped: Option<RunnerError>,
}

impl Runner {
    /// The doubled world at its opening.
    ///
    /// # Errors
    /// `RunnerError::World` when the engine refuses the opening.
    pub fn open() -> Result<Self, RunnerError> {
        let state = doubled::opening_state()?;
        let (bindings, staffing) = doubled::staffing()?;
        let mut runner = Self {
            state,
            staffing,
            bindings,
            catalogs: Vec::new(),
            history: Vec::new(),
            stopped: None,
        };
        runner.ensure_catalog(&Figures::OPENING)?;
        Ok(runner)
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
                self.staffing = stepped.staffing;
                self.history.push(stepped.result);
                self.history.last().ok_or(RunnerError::Stopped)
            }
            Err(error) => {
                self.stopped = Some(error.clone());
                Err(error)
            }
        }
    }

    fn ensure_catalog(&mut self, figures: &Figures) -> Result<(), WorldError> {
        if !self.catalogs.iter().any(|(known, _)| known == figures) {
            self.catalogs.push((*figures, doubled::catalog(figures)?));
        }
        Ok(())
    }

    fn advance(&mut self) -> Result<Stepped, RunnerError> {
        let period = self.state.period;
        let past = period.checked_add(2).is_none_or(|last| last > HORIZON);
        if past {
            return Err(RunnerError::PastHorizon { period });
        }
        let figures = Figures::OPENING;
        self.ensure_catalog(&figures)?;
        let catalog = self
            .catalogs
            .iter()
            .find(|(known, _)| *known == figures)
            .map(|(_, catalog)| catalog)
            .ok_or(RunnerError::World(WorldError::Arithmetic))?;
        let closed = engine::close_material_period(catalog, &self.state)
            .map_err(|error| engine_error(period, Stage::Close, error))?;
        let requests = closed
            .staffing_requests(catalog, &self.bindings)
            .map_err(|error| engine_error(period, Stage::StaffingRequests, error))?;
        let staffed = staff(period, &self.staffing, &requests)?;
        let member_labor = staffed
            .labor
            .iter()
            .map(|row| {
                Ok(MemberLaborCapacityRow {
                    member_id: site_workplace(row.site_id)?.member_id(),
                    period: row.period,
                    available_hours: row.available,
                })
            })
            .collect::<Result<Vec<_>, RunnerError>>()?;
        let transition = closed
            .finish_with_staffing(catalog, staffed.labor, member_labor, &staffed.members)
            .map_err(|error| engine_error(period, Stage::Finish, error))?;
        check_conserved(
            period,
            &transition.state,
            &staffed.employed,
            &staffed.reserve,
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
            members: staffed.members,
            closing,
            summary,
            state_digest,
            receipts: take_receipts(&transition),
        };
        Ok(Stepped {
            result,
            state: transition.state,
            staffing: staffed.staffing,
        })
    }
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

/// Advance the staffing, then give each pool's one member its share.
fn staff(
    period: u64,
    staffing: &StaffingState,
    requests: &[StaffingWorkRequest],
) -> Result<Staffed, RunnerError> {
    let transition =
        engine::advance_staffing(staffing, requests).map_err(|error| RunnerError::Staffing {
            period,
            stage: Stage::AdvanceStaffing,
            error,
        })?;
    let mut members = Vec::new();
    let mut employed = [0; 8];
    let mut reserve = [0; 8];
    for receipt in transition.receipts() {
        let workplace = site_workplace(receipt.binding().site_id())?;
        let state = doubled::member(workplace, receipt.opening_employed())?;
        let shares = engine::distribute_staffing_members(receipt, &[state]).map_err(|error| {
            RunnerError::Staffing {
                period,
                stage: Stage::DistributeMembers,
                error,
            }
        })?;
        members.extend(shares);
        employed[workplace.index()] = receipt.closing_employed();
        reserve[workplace.index()] = receipt.closing_reserve();
    }
    let labor = transition.next_labor().to_vec();
    Ok(Staffed {
        labor,
        members,
        staffing: transition.into_state(),
        employed,
        reserve,
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
    next: &MaterialCircuitState,
    employed: &[u64; 8],
    reserve: &[u64; 8],
) -> Result<(), RunnerError> {
    let money = monetary(period, next)?
        .book
        .total_cash_and_reserves()
        .map_err(|error| engine_error(period, Stage::Read, error.into()))?
        .micro_units();
    if money != OPENING_MONEY {
        return Err(RunnerError::MoneyNotConserved {
            period,
            opening: OPENING_MONEY,
            closing: money,
        });
    }
    let persons = cohort_persons(next, period)?;
    if persons != PERSONS {
        return Err(RunnerError::PersonsNotConserved {
            period,
            opening: PERSONS,
            closing: persons,
        });
    }
    for workplace in Workplace::ALL {
        let i = workplace.index();
        let pool = employed[i]
            .checked_add(reserve[i])
            .ok_or(RunnerError::World(WorldError::Arithmetic))?;
        let workers = workplace.workers().opening_persons();
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
    }
}
