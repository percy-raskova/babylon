//! The recorded-labor ledger's fold: hours carried through one period of the material circuit.
//! The fold reads a view of one period and the catalog that period closed under; it holds no
//! stored records. The stored records (checkpoints, attendance, assets) live in `babylon-persistence`.
mod auxiliary;
mod book;
mod circulation;
mod fold;
mod household_work;
mod model;
mod production;
mod services;
mod view;

pub mod phases;

#[cfg(test)]
mod tests;

pub use book::{Book, Carry, Frame, Handed, Position};
pub use fold::{check_opening, fold_period, opening_book, positions_of, FoldedPeriod};
pub use model::{
    LaborBasis, LaborDisposition, LaborEdge, LaborId, LaborNode, LaborReceiptFamily, ReceiptRef,
    RecordedLaborError, RecordedLaborPosition, MICROS_PER_HOUR, MICROS_PER_UNIT,
};
pub use view::{AgencyHours, PeriodView, ReceiptView};
