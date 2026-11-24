//! The fold of one period: the phases in their order, the closing check and the conservation law.
use crate::book::{Book, Carry, Frame, Handed, Position, Result};
use crate::model::{
    LaborBasis, LaborEdge, LaborNode, RecordedLaborError, RecordedLaborPosition, MICROS_PER_UNIT,
};
use crate::view::PeriodView;
use crate::{auxiliary, circulation, household_work, production};
use babylon_material_circuit::{CircuitAccounting, MaterialCatalog, MaterialCircuitState};
use std::collections::BTreeMap;

/// Every positive stock of `state` by node.
///
/// # Errors
/// `QuantityMismatch` when two rows name one node or a maintenance service has no binding.
pub fn positions_of(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
) -> Result<BTreeMap<LaborNode, u64>> {
    let mut result = BTreeMap::new();
    let mut put = |node, qty| {
        if qty > 0 && result.insert(node, qty).is_some() {
            return Err(RecordedLaborError::QuantityMismatch);
        }
        Ok(())
    };
    for r in &state.inventory {
        put(LaborNode::site(r.site_id, r.good_id, r.unit_id), r.quantity)?;
    }
    for r in &state.freight {
        put(LaborNode::freight(r.lot_id), r.quantity)?;
    }
    for r in &state.capacity_reservations.equipment.cohorts {
        put(LaborNode::equipment(r.id), r.remaining_service_batches)?;
    }
    for r in &state.capacity_reservations.equipment.pending {
        put(LaborNode::installation(r.id), r.units)?;
    }
    if let Some(service) = state.maintenance_service {
        let binding = catalog
            .maintenance_binding
            .as_ref()
            .ok_or(RecordedLaborError::QuantityMismatch)?;
        put(
            LaborNode::maintenance(binding.consumer_process_id),
            service.available_batches,
        )?;
    }
    if let CircuitAccounting::Monetary(e) = &state.accounting {
        if let Some(recurring) = &e.recurring {
            for r in &recurring.household_stocks {
                put(
                    LaborNode::household(r.principal_id, r.good_id, r.unit_id),
                    r.quantity,
                )?;
            }
        }
        for r in &e.aid.freight {
            put(LaborNode::freight(r.lot_id), r.quantity)?;
        }
    }
    Ok(result)
}

/// The book of `positions`, each `unknown_opening`, carrying 0 (`Carry::Hours`) or its quantity times
/// `MICROS_PER_UNIT` (`Carry::OpeningUnits`).
pub(crate) fn book_of(positions: BTreeMap<LaborNode, u64>, carry: Carry) -> Result<Book> {
    positions
        .into_iter()
        .map(|(node, quantity)| {
            let recorded_micro_hours = match carry {
                Carry::Hours => 0,
                Carry::OpeningUnits => u128::from(quantity)
                    .checked_mul(MICROS_PER_UNIT)
                    .ok_or(RecordedLaborError::Arithmetic)?,
            };
            Ok((
                node,
                Position {
                    quantity,
                    basis: LaborBasis {
                        recorded_micro_hours,
                        unknown_opening: true,
                    },
                },
            ))
        })
        .collect()
}

/// The opening book: every position of `state` not measured (`unknown_opening`), carrying 0
/// (`Carry::Hours`) or its quantity times `MICROS_PER_UNIT` (`Carry::OpeningUnits`).
///
/// # Errors
/// As `positions_of`; `Arithmetic` when a carried figure overflows.
pub fn opening_book(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    carry: Carry,
) -> Result<Book> {
    book_of(positions_of(catalog, state)?, carry)
}

fn matches(book: &Book, actual: &BTreeMap<LaborNode, u64>) -> bool {
    book.iter()
        .map(|(n, p)| (n, p.quantity))
        .eq(actual.iter().map(|(n, q)| (n, *q)))
}

fn positions(book: &Book) -> Result<(u128, Vec<RecordedLaborPosition>)> {
    let mut total = 0_u128;
    let mut rows = Vec::with_capacity(book.len());
    for (&node, r) in book {
        total = total
            .checked_add(r.basis.recorded_micro_hours)
            .ok_or(RecordedLaborError::Arithmetic)?;
        rows.push(RecordedLaborPosition {
            node,
            quantity: r.quantity,
            basis: r.basis,
        });
    }
    Ok((total, rows))
}

/// `book` holds the positions of `before`: its total and rows.
///
/// # Errors
/// `OpeningPositionMismatch`, then `Arithmetic`.
pub fn check_opening(
    book: &Book,
    catalog: &MaterialCatalog,
    before: &MaterialCircuitState,
) -> Result<(u128, Vec<RecordedLaborPosition>)> {
    if !matches(book, &positions_of(catalog, before)?) {
        return Err(RecordedLaborError::OpeningPositionMismatch);
    }
    positions(book)
}

/// One period folded. The four totals are micro-hours under `Carry::Hours`, micro-units under
/// `Carry::OpeningUnits`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FoldedPeriod {
    pub closing: Book,
    pub opening_positions: Vec<RecordedLaborPosition>,
    pub closing_positions: Vec<RecordedLaborPosition>,
    pub opening_recorded: u128,
    pub closing_recorded: u128,
    pub direct: u128,
    pub released: u128,
    pub edges: Vec<LaborEdge>,
    pub handed: Vec<Handed>,
}

/// Fold one period from `book` under the catalog that period closed under; the book is not changed.
///
/// # Errors
/// `DiscontinuousPeriod` (`before.period != period` or `after.period != period + 1`); as
/// `check_opening`; the phases' refusals; `ClosingPositionMismatch`; `Conservation`.
pub fn fold_period(
    book: &Book,
    catalog: &MaterialCatalog,
    view: &PeriodView<'_>,
    carry: Carry,
) -> Result<FoldedPeriod> {
    if view.before.period != view.period
        || view.before.period.checked_add(1) != Some(view.after.period)
    {
        return Err(RecordedLaborError::DiscontinuousPeriod);
    }
    let (opening_recorded, opening_positions) = check_opening(book, catalog, view.before)?;
    let mut frame = Frame::carrying(book.clone(), carry);
    auxiliary::aid_arrivals(&mut frame, view)?;
    circulation::freight_arrivals(&mut frame, view)?;
    production::execute(&mut frame, catalog, view)?;
    auxiliary::maintenance_and_installation(&mut frame, catalog, view)?;
    circulation::outbound(&mut frame, catalog, view)?;
    auxiliary::aid_dispatch(&mut frame, catalog, view)?;
    circulation::consume(&mut frame, view)?;
    household_work::agency_observations(&mut frame, view)?;
    household_work::collections(&mut frame, view)?;
    if !matches(&frame.book, &positions_of(catalog, view.after)?) {
        return Err(RecordedLaborError::ClosingPositionMismatch);
    }
    let (closing_recorded, closing_positions) = positions(&frame.book)?;
    if opening_recorded
        .checked_add(frame.direct_micro_hours)
        .ok_or(RecordedLaborError::Arithmetic)?
        != closing_recorded
            .checked_add(frame.released_micro_hours)
            .ok_or(RecordedLaborError::Arithmetic)?
    {
        return Err(RecordedLaborError::Conservation);
    }
    Ok(FoldedPeriod {
        closing: frame.book,
        opening_positions,
        closing_positions,
        opening_recorded,
        closing_recorded,
        direct: frame.direct_micro_hours,
        released: frame.released_micro_hours,
        edges: frame.edges,
        handed: frame.handed,
    })
}
