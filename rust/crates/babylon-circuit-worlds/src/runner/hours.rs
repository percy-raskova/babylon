//! The runner's ledger of hours: each closed period folded twice by the recorded-labor ledger, once in hours
//! of work and once in units of opening stock, and read as the hours of each household group, workplace and
//! place. The ledger is the fold of `babylon-recorded-labor`; nothing here counts hours of its own but the sums
//! of its edges and hand-overs.

use crate::runner::error::{HoursRun, RunnerError};
use crate::{Household, Place, Workplace, World};
use babylon_material_circuit::{
    MaterialCatalog, MaterialCircuitState, MaterialCircuitTransition, MemberLaborUseReceipt, SiteId,
};
use babylon_recorded_labor as labor;
use babylon_recorded_labor::{
    Book, Carry, FoldedPeriod, Handed, LaborId, LaborNode, LaborReceiptFamily, PeriodView,
    ReceiptRef, ReceiptView, RecordedLaborError, MICROS_PER_HOUR,
};

/// A goods move as the scene reads it: the receipt list and its index.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum MovedBy {
    /// `service_performance[index]`.
    ServicePerformance(usize),
    /// `local_transfers[index]`.
    LocalTransfer(usize),
    /// `local_fulfillments[index]`.
    LocalFulfillment(usize),
}

/// The hours and the opening units in one move, from the two runs' `Handed`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MoveHours {
    /// The receipt that moved it.
    pub moved_by: MovedBy,
    /// Units moved.
    pub quantity: u64,
    /// Micro-hours of work in them.
    pub micro_hours: u128,
    /// Micro-units of them that come from the opening stock.
    pub opening_micro_units: u128,
}

/// One household group's hours. `given`: hours into goods and services (production, handling, upkeep,
/// installing) by the household that gave them, idle apart (ruling 17). `clock`: worked or idle
/// (`attended_hours`). `back_micro_hours`: measured hours in what reached its home this period. `units`
/// received, `opening_micro_units` of them from the opening.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct HouseholdHours {
    /// Hours given into goods and services.
    pub given: u64,
    /// Hours on the clock, worked or idle.
    pub clock: u64,
    /// Micro-hours in what reached its home.
    pub back_micro_hours: u128,
    /// Micro-units of what reached its home that come from the opening.
    pub opening_micro_units: u128,
    /// Units that reached its home.
    pub units: u64,
}

/// One workplace's hours. `made_micro_hours`: the production edges into its own stock, as made. `handed_*`:
/// every `Handed` from its stocks.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct WorkplaceHours {
    /// Hours given at its site, by whoever gave them.
    pub given: u64,
    /// Units made into its own stock.
    pub made_units: u64,
    /// Micro-hours in them as made.
    pub made_micro_hours: u128,
    /// Units handed over from its stocks.
    pub handed_units: u64,
    /// Micro-hours in them.
    pub handed_micro_hours: u128,
    /// Micro-units of them from the opening stock.
    pub handed_opening_micro_units: u128,
}

/// One place's sums, for the identity of "How we know it works": `given_micro_hours` is a million times the sum
/// of its workplaces' `given`; `held_*` are the hours in the stocks of its workplaces at the opening and the
/// close; `left` the hours released from those stocks, unsold or lost.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct PlaceHours {
    /// A million times the hours given at its workplaces.
    pub given_micro_hours: u128,
    /// Micro-hours in what reached the homes of its households.
    pub back_micro_hours: u128,
    /// Micro-hours in the stocks of its workplaces at the opening.
    pub held_opening: u128,
    /// Micro-hours in the stocks of its workplaces at the close.
    pub held_closing: u128,
    /// Micro-hours released from those stocks, unsold or lost.
    pub left_micro_hours: u128,
}

/// The ledger's totals of one run.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct LedgerTotals {
    /// Carried at the opening.
    pub opening: u128,
    /// Posted by direct work.
    pub direct: u128,
    /// Carried at the close.
    pub closing: u128,
    /// Released.
    pub released: u128,
}

/// The hours of one closed period. `moves`: one for each move of `service_performance`, `local_transfers` and
/// `local_fulfillments`, in that order. `households` in `World::households()` order; `workplaces` in
/// `Workplace::ALL` order; `places` in `Place::ALL` order.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PeriodHours {
    /// The run in hours of work.
    pub hours: LedgerTotals,
    /// The run in units of opening stock.
    pub opening_units: LedgerTotals,
    /// The moves of goods and services.
    pub moves: Vec<MoveHours>,
    /// Each household group's hours.
    pub households: Vec<(Household, HouseholdHours)>,
    /// Each workplace's hours.
    pub workplaces: Vec<(Workplace, WorkplaceHours)>,
    /// Each place's sums.
    pub places: Vec<(Place, PlaceHours)>,
}

impl PeriodHours {
    /// The hours of one move.
    #[must_use]
    pub fn of_move(&self, moved_by: MovedBy) -> Option<&MoveHours> {
        self.moves.iter().find(|m| m.moved_by == moved_by)
    }

    /// The hours of one household group.
    #[must_use]
    pub fn household(&self, household: Household) -> Option<&HouseholdHours> {
        self.households
            .iter()
            .find(|(h, _)| *h == household)
            .map(|(_, hours)| hours)
    }

    /// The hours of one workplace.
    #[must_use]
    pub fn workplace(&self, workplace: Workplace) -> Option<&WorkplaceHours> {
        self.workplaces
            .iter()
            .find(|(w, _)| *w == workplace)
            .map(|(_, hours)| hours)
    }
}

/// The two books the runner keeps from period to period.
pub(crate) struct HoursLedger {
    hours: Book,
    units: Book,
}

fn refused(period: u64, run: HoursRun) -> impl Fn(RecordedLaborError) -> RunnerError {
    move |error| RunnerError::HoursRefused { period, run, error }
}

fn unplaced(period: u64, what: impl Into<String>) -> RunnerError {
    RunnerError::HoursUnplaced {
        period,
        what: what.into(),
    }
}

fn overflow(period: u64) -> RunnerError {
    refused(period, HoursRun::Hours)(RecordedLaborError::Arithmetic)
}

fn plus_u64(period: u64, sum: &mut u64, add: u64) -> Result<(), RunnerError> {
    *sum = sum.checked_add(add).ok_or_else(|| overflow(period))?;
    Ok(())
}

fn plus_u128(period: u64, sum: &mut u128, add: u128) -> Result<(), RunnerError> {
    *sum = sum.checked_add(add).ok_or_else(|| overflow(period))?;
    Ok(())
}

impl HoursLedger {
    /// Both books from the opening state, every stock not measured.
    pub(crate) fn open(
        catalog: &MaterialCatalog,
        state: &MaterialCircuitState,
    ) -> Result<Self, RunnerError> {
        let period = state.period;
        Ok(Self {
            hours: labor::opening_book(catalog, state, Carry::Hours)
                .map_err(refused(period, HoursRun::Hours))?,
            units: labor::opening_book(catalog, state, Carry::OpeningUnits)
                .map_err(refused(period, HoursRun::OpeningUnits))?,
        })
    }

    /// Fold one period twice and read its record; the ledger is not changed.
    pub(crate) fn fold(
        &self,
        world: &World,
        catalog: &MaterialCatalog,
        before: &MaterialCircuitState,
        transition: &MaterialCircuitTransition,
    ) -> Result<(Self, PeriodHours), RunnerError> {
        let period = before.period;
        if !transition.agency_attendance.is_empty() {
            return Err(unplaced(period, "an agency row"));
        }
        let view = view_of(before, transition);
        let hours = labor::fold_period(&self.hours, catalog, &view, Carry::Hours)
            .map_err(refused(period, HoursRun::Hours))?;
        let units = labor::fold_period(&self.units, catalog, &view, Carry::OpeningUnits)
            .map_err(refused(period, HoursRun::OpeningUnits))?;
        same_moves(period, &hours.handed, &units.handed)?;
        let record = PeriodHours {
            hours: totals(&hours),
            opening_units: totals(&units),
            moves: moves_of(&hours.handed, &units.handed),
            households: Vec::new(),
            workplaces: Vec::new(),
            places: Vec::new(),
        };
        let reader = Reader {
            period,
            world,
            transition,
            opening: &self.hours,
            hours: &hours,
            units: &units,
        };
        let households = reader.households()?;
        let workplaces = reader.workplaces()?;
        let places = reader.places(&households, &workplaces)?;
        let next = Self {
            hours: hours.closing,
            units: units.closing,
        };
        Ok((
            next,
            PeriodHours {
                households,
                workplaces,
                places,
                ..record
            },
        ))
    }
}

/// The view of the transition: the runner's state before, the transition's own lists, no agency.
fn view_of<'a>(
    before: &'a MaterialCircuitState,
    transition: &'a MaterialCircuitTransition,
) -> PeriodView<'a> {
    PeriodView {
        period: before.period,
        before,
        after: &transition.state,
        receipts: ReceiptView {
            aid: &transition.aid,
            collections: &transition.collections,
            agency: &[],
            installation: &transition.installation,
            equipment_wear: &transition.equipment_wear,
            maintenance: transition.maintenance.as_ref(),
            production: &transition.production,
            dispatches: &transition.dispatches,
            losses: &transition.losses,
            arrivals: &transition.arrivals,
            handling: &transition.handling,
            local_fulfillments: &transition.local_fulfillments,
            local_transfers: &transition.local_transfers,
            procurement: &transition.procurement,
            service_outputs: &transition.service_outputs,
            service_performance: &transition.service_performance,
            household_services: &transition.household_services,
            household_wants: &transition.household_wants,
            household_consumption: &transition.household_consumption,
        },
    }
}

fn totals(folded: &FoldedPeriod) -> LedgerTotals {
    LedgerTotals {
        opening: folded.opening_recorded,
        direct: folded.direct,
        closing: folded.closing_recorded,
        released: folded.released,
    }
}

/// The two runs' hand-overs agree index by index (decision 4): the same receipt, source, destination and
/// quantity; else `HoursRunsDiffer`.
fn same_moves(period: u64, hours: &[Handed], units: &[Handed]) -> Result<(), RunnerError> {
    let alike = hours.len() == units.len()
        && hours.iter().zip(units).all(|(h, u)| {
            h.receipt == u.receipt && h.from == u.from && h.to == u.to && h.quantity == u.quantity
        });
    if alike {
        Ok(())
    } else {
        Err(RunnerError::HoursRunsDiffer { period })
    }
}

fn moved_by(receipt: ReceiptRef) -> Option<MovedBy> {
    match receipt.family {
        LaborReceiptFamily::ServicePerformance => {
            Some(MovedBy::ServicePerformance(receipt.ordinal))
        }
        LaborReceiptFamily::LocalTransfers => Some(MovedBy::LocalTransfer(receipt.ordinal)),
        LaborReceiptFamily::LocalFulfillments => Some(MovedBy::LocalFulfillment(receipt.ordinal)),
        _ => None,
    }
}

/// One move for each hand-over of the three families, in the order of the receipt lists.
fn moves_of(hours: &[Handed], units: &[Handed]) -> Vec<MoveHours> {
    let mut moves: Vec<MoveHours> = hours
        .iter()
        .zip(units)
        .filter_map(|(h, u)| {
            Some(MoveHours {
                moved_by: moved_by(h.receipt)?,
                quantity: h.quantity,
                micro_hours: h.basis.recorded_micro_hours,
                opening_micro_units: u.basis.recorded_micro_hours,
            })
        })
        .collect();
    moves.sort_by_key(|m| m.moved_by);
    moves
}

/// What the readers of one period share.
struct Reader<'a> {
    period: u64,
    world: &'a World,
    transition: &'a MaterialCircuitTransition,
    /// The hours book at the opening of the period.
    opening: &'a Book,
    hours: &'a FoldedPeriod,
    units: &'a FoldedPeriod,
}

fn workplace_of(id: LaborId) -> Option<Workplace> {
    Workplace::from_site(SiteId::from_bytes(id.0))
}

/// What a member's receipt gave into goods and services.
fn given_of(receipt: &MemberLaborUseReceipt) -> Option<u64> {
    receipt
        .production_hours
        .checked_add(receipt.handling_hours)?
        .checked_add(receipt.maintenance_hours)?
        .checked_add(receipt.installation_hours)
}

impl Reader<'_> {
    fn households(&self) -> Result<Vec<(Household, HouseholdHours)>, RunnerError> {
        let period = self.period;
        let mut rows: Vec<(Household, HouseholdHours)> = self
            .world
            .households()
            .into_iter()
            .map(|household| (household, HouseholdHours::default()))
            .collect();
        for receipt in &self.transition.member_labor_use {
            let row = Household::from_principal(receipt.payee)
                .and_then(|household| rows.iter_mut().find(|(h, _)| *h == household))
                .ok_or_else(|| unplaced(period, format!("the household {:?}", receipt.payee)))?;
            let given = given_of(receipt).ok_or_else(|| overflow(period))?;
            plus_u64(period, &mut row.1.given, given)?;
            plus_u64(period, &mut row.1.clock, receipt.attended_hours)?;
        }
        for (hours, units) in self.hours.handed.iter().zip(&self.units.handed) {
            let LaborNode::HouseholdStock { household, .. } = hours.to else {
                continue;
            };
            let row = rows
                .iter_mut()
                .find(|(h, _)| h.principal().as_bytes() == household.0)
                .ok_or_else(|| unplaced(period, "a stock of no household of the world"))?;
            plus_u128(
                period,
                &mut row.1.back_micro_hours,
                hours.basis.recorded_micro_hours,
            )?;
            plus_u128(
                period,
                &mut row.1.opening_micro_units,
                units.basis.recorded_micro_hours,
            )?;
            plus_u64(period, &mut row.1.units, hours.quantity)?;
        }
        Ok(rows)
    }

    fn workplaces(&self) -> Result<Vec<(Workplace, WorkplaceHours)>, RunnerError> {
        let period = self.period;
        let mut rows: Vec<(Workplace, WorkplaceHours)> = Workplace::ALL
            .into_iter()
            .map(|workplace| (workplace, WorkplaceHours::default()))
            .collect();
        for receipt in &self.transition.member_labor_use {
            let workplace = Workplace::from_site(receipt.site_id)
                .ok_or_else(|| unplaced(period, format!("the site {:?}", receipt.site_id)))?;
            let given = given_of(receipt).ok_or_else(|| overflow(period))?;
            plus_u64(period, &mut rows[workplace.index()].1.given, given)?;
        }
        for edge in &self.hours.edges {
            if let (LaborNode::Process { .. }, LaborNode::SiteStock { site, .. }) =
                (edge.source, edge.destination)
            {
                let workplace = workplace_of(site)
                    .ok_or_else(|| unplaced(period, "a stock of no workplace"))?;
                let row = &mut rows[workplace.index()].1;
                plus_u64(period, &mut row.made_units, edge.quantity)?;
                plus_u128(
                    period,
                    &mut row.made_micro_hours,
                    edge.basis.recorded_micro_hours,
                )?;
            }
        }
        for (hours, units) in self.hours.handed.iter().zip(&self.units.handed) {
            let LaborNode::SiteStock { site, .. } = hours.from else {
                continue;
            };
            let workplace =
                workplace_of(site).ok_or_else(|| unplaced(period, "a stock of no workplace"))?;
            let row = &mut rows[workplace.index()].1;
            plus_u64(period, &mut row.handed_units, hours.quantity)?;
            plus_u128(
                period,
                &mut row.handed_micro_hours,
                hours.basis.recorded_micro_hours,
            )?;
            plus_u128(
                period,
                &mut row.handed_opening_micro_units,
                units.basis.recorded_micro_hours,
            )?;
        }
        Ok(rows)
    }

    fn places(
        &self,
        households: &[(Household, HouseholdHours)],
        workplaces: &[(Workplace, WorkplaceHours)],
    ) -> Result<Vec<(Place, PlaceHours)>, RunnerError> {
        let period = self.period;
        let mut rows: Vec<(Place, PlaceHours)> = Place::ALL
            .into_iter()
            .map(|place| (place, PlaceHours::default()))
            .collect();
        for (household, hours) in households {
            plus_u128(
                period,
                &mut rows[household.place().index()].1.back_micro_hours,
                hours.back_micro_hours,
            )?;
        }
        for (workplace, hours) in workplaces {
            let given = MICROS_PER_HOUR
                .checked_mul(u128::from(hours.given))
                .ok_or_else(|| overflow(period))?;
            plus_u128(
                period,
                &mut rows[workplace.place.index()].1.given_micro_hours,
                given,
            )?;
        }
        for (node, position) in self.opening {
            if let Some(place) = stock_place(node) {
                plus_u128(
                    period,
                    &mut rows[place.index()].1.held_opening,
                    position.basis.recorded_micro_hours,
                )?;
            }
        }
        for (node, position) in &self.hours.closing {
            if let Some(place) = stock_place(node) {
                plus_u128(
                    period,
                    &mut rows[place.index()].1.held_closing,
                    position.basis.recorded_micro_hours,
                )?;
            }
        }
        for edge in &self.hours.edges {
            // A retail fulfillment that ends in a sink (a want's units, used where they are bought)
            // reached its household: it is that household's `back`, not hours that left.
            if edge.receipt.family == LaborReceiptFamily::LocalFulfillments {
                continue;
            }
            if let (Some(place), LaborNode::Sink { .. }) =
                (stock_place(&edge.source), edge.destination)
            {
                plus_u128(
                    period,
                    &mut rows[place.index()].1.left_micro_hours,
                    edge.basis.recorded_micro_hours,
                )?;
            }
        }
        Ok(rows)
    }
}

/// The place of a site stock of a workplace of the world.
fn stock_place(node: &LaborNode) -> Option<Place> {
    match node {
        LaborNode::SiteStock { site, .. } => workplace_of(*site).map(|w| w.place),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::doubled;
    use crate::shocks::ShockBook;
    use babylon_kernel::currency::Currency;
    use babylon_material_circuit::{
        self as engine, AgencyAttendanceInput, AgencyAttendanceOutcome,
        AgencyObservationFundingReceipt, FinalDemandPrincipalId, OrganizationAccountId, ShiftId,
        UnitId,
    };
    use std::error::Error;

    type TestResult = Result<(), Box<dyn Error>>;

    /// A real first period of the world that asks for the seekers: its catalog, opening state and transition.
    struct Period {
        world: World,
        catalog: MaterialCatalog,
        state: MaterialCircuitState,
        transition: MaterialCircuitTransition,
    }

    fn a_real_period() -> Result<Period, Box<dyn Error>> {
        let rules = vec![World::switches_at(crate::Scale::Small)[1]];
        let world = World {
            rules: rules.clone(),
            ..World::scene()
        };
        let state = doubled::opening_state_of(&world)?;
        let (_, staffing) = doubled::staffing_of(&world)?;
        let members = doubled::pool_members_of(&world)?;
        let figures = ShockBook::default().figures(state.period);
        let catalog = doubled::catalog_of(&world, &figures, &rules)?;
        let closed = engine::close_material_period(&catalog, &state)
            .map_err(|error| format!("{error:?}"))?;
        let placed = closed
            .staff_in_places(&catalog, &staffing, &members, &doubled::places())
            .map_err(|error| format!("{error:?}"))?;
        let transition = closed
            .finish_with_place_staffing(&catalog, &placed)
            .map_err(|error| format!("{error:?}"))?;
        Ok(Period {
            world,
            catalog,
            state,
            transition,
        })
    }

    #[test]
    fn the_two_runs_hand_over_the_same_moves() -> TestResult {
        let p = a_real_period()?;
        let ledger = HoursLedger::open(&p.catalog, &p.state)?;
        let view = view_of(&p.state, &p.transition);
        let hours = labor::fold_period(&ledger.hours, &p.catalog, &view, Carry::Hours)?;
        let units = labor::fold_period(&ledger.units, &p.catalog, &view, Carry::OpeningUnits)?;
        assert_ne!(hours.handed.len(), 0, "the period hands something over");
        same_moves(1, &hours.handed, &units.handed)?;
        let mut changed = units.handed.clone();
        changed[0].quantity += 1;
        assert_eq!(
            same_moves(1, &hours.handed, &changed),
            Err(RunnerError::HoursRunsDiffer { period: 1 })
        );
        Ok(())
    }

    #[test]
    fn a_refusal_is_told_in_the_ledger_s_words() -> TestResult {
        let mut p = a_real_period()?;
        let ledger = HoursLedger::open(&p.catalog, &p.state)?;
        let raised = p
            .transition
            .local_fulfillments
            .first_mut()
            .ok_or("no fulfillment in the first period")?;
        raised.quantity += 1;
        let Err(error) = ledger.fold(&p.world, &p.catalog, &p.state, &p.transition) else {
            return Err("a raised quantity was folded".into());
        };
        assert!(matches!(
            error,
            RunnerError::HoursRefused {
                period: 1,
                run: HoursRun::Hours,
                ..
            }
        ));
        assert!(
            error
                .to_string()
                .starts_with("Period 1: the hours ledger refused it: "),
            "{error}"
        );
        Ok(())
    }

    #[test]
    fn an_agency_row_is_not_placed() -> TestResult {
        let mut p = a_real_period()?;
        let ledger = HoursLedger::open(&p.catalog, &p.state)?;
        let zero = Currency::from_micro_units(0);
        let principal = FinalDemandPrincipalId::from_bytes([11; 32]);
        let unit = UnitId::from_bytes([1; 32]);
        p.transition
            .agency_attendance
            .push(AgencyObservationFundingReceipt {
                input: AgencyAttendanceInput {
                    intent_id: [1; 32],
                    shift_id: ShiftId::from_bytes([1; 32]),
                    agency: OrganizationAccountId::from_bytes([1; 32]),
                    principal_id: principal,
                    residence: crate::ids::location()?,
                    labor_unit_id: unit,
                    due_period: 1,
                    hours: 1,
                    hourly_rate: zero,
                },
                outcome: AgencyAttendanceOutcome::NoFunds,
                requested: zero,
                reserved: zero,
                paid: zero,
                cancelled: zero,
                shortfall: zero,
                attended_hours: 0,
                shortfall_hours: 0,
                attendance: None,
            });
        let Err(error) = ledger.fold(&p.world, &p.catalog, &p.state, &p.transition) else {
            return Err("an agency row was folded".into());
        };
        assert_eq!(
            error,
            RunnerError::HoursUnplaced {
                period: 1,
                what: "an agency row".to_owned()
            }
        );
        Ok(())
    }
}
