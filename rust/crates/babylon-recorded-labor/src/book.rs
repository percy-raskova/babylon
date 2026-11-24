//! A proportional withdrawal carries a floor share; the last unit carries the residual.
use crate::model::{
    LaborBasis, LaborEdge, LaborNode, ReceiptRef, RecordedLaborError, MICROS_PER_HOUR,
};
use std::collections::BTreeMap;
use std::result::Result as StdResult;

/// What a fold carries: hours of work, or units of opening stock (each opening unit carries
/// `MICROS_PER_UNIT`, and work adds none).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Carry {
    Hours,
    OpeningUnits,
}

#[derive(Clone, Copy, Default, PartialEq, Eq, Debug)]
pub struct Position {
    pub quantity: u64,
    pub basis: LaborBasis,
}
pub type Book = BTreeMap<LaborNode, Position>;
pub(crate) type Result<T> = StdResult<T, RecordedLaborError>;

/// One move of stock from one holder to another, as the fold handed it over: a service performed, a local
/// transfer, a dispatch, a retail fulfillment. `basis` includes the handling hours added at the hand-off;
/// `to` is the receiver's own node (a household's stock even when the fold booked it to `FinalDemandOutlay`).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Handed {
    pub receipt: ReceiptRef,
    pub from: LaborNode,
    pub to: LaborNode,
    pub quantity: u64,
    pub basis: LaborBasis,
}

pub struct Frame {
    pub book: Book,
    pub edges: Vec<LaborEdge>,
    pub handed: Vec<Handed>,
    pub direct_micro_hours: u128,
    pub released_micro_hours: u128,
    carry: Carry,
}
impl Frame {
    /// A frame that carries hours.
    #[must_use]
    pub fn new(book: Book) -> Self {
        Self::carrying(book, Carry::Hours)
    }
    /// A frame that carries `carry`.
    #[must_use]
    pub fn carrying(book: Book, carry: Carry) -> Self {
        Self {
            book,
            edges: Vec::new(),
            handed: Vec::new(),
            direct_micro_hours: 0,
            released_micro_hours: 0,
            carry,
        }
    }
    #[must_use]
    pub fn quantity(&self, node: LaborNode) -> u64 {
        self.book.get(&node).map_or(0, |row| row.quantity)
    }
    /// Withdraw `quantity` from `node`: the floor share of its basis, or all of it when it is the last.
    ///
    /// # Errors
    /// A receipt that does not match the stock, or an arithmetic overflow: `RecordedLaborError`.
    pub fn take(&mut self, node: LaborNode, quantity: u64) -> Result<LaborBasis> {
        if quantity == 0 {
            return Ok(LaborBasis::default());
        }
        let row = self
            .book
            .get_mut(&node)
            .ok_or(RecordedLaborError::QuantityMismatch)?;
        if quantity > row.quantity {
            return Err(RecordedLaborError::QuantityMismatch);
        }
        if quantity == row.quantity {
            return self
                .book
                .remove(&node)
                .map(|r| r.basis)
                .ok_or(RecordedLaborError::QuantityMismatch);
        }
        let total = row.basis.recorded_micro_hours;
        let count = u128::from(row.quantity);
        let used = u128::from(quantity);
        // remainder < count <= u64::MAX; the two products are bounded by u128.
        let share = (total / count) * used + ((total % count) * used) / count;
        row.basis.recorded_micro_hours -= share;
        row.quantity -= quantity;
        Ok(LaborBasis {
            recorded_micro_hours: share,
            unknown_opening: row.basis.unknown_opening,
        })
    }
    /// Add `quantity` and its basis to `node`.
    ///
    /// # Errors
    /// A receipt that does not match the stock, or an arithmetic overflow: `RecordedLaborError`.
    pub fn credit(&mut self, node: LaborNode, quantity: u64, basis: LaborBasis) -> Result<()> {
        if quantity == 0 {
            return if basis == LaborBasis::default() {
                Ok(())
            } else {
                Err(RecordedLaborError::QuantityMismatch)
            };
        }
        let row = self.book.entry(node).or_default();
        row.quantity = row
            .quantity
            .checked_add(quantity)
            .ok_or(RecordedLaborError::Arithmetic)?;
        row.basis = row.basis.add(basis)?;
        Ok(())
    }
    pub fn edge(
        &mut self,
        source: LaborNode,
        destination: LaborNode,
        quantity: u64,
        basis: LaborBasis,
        receipt: ReceiptRef,
    ) {
        if quantity > 0 {
            self.edges.push(LaborEdge {
                source,
                destination,
                quantity,
                basis,
                receipt,
            });
        }
    }
    /// Move `qty` from `source` to `dest`, writing the edge.
    ///
    /// # Errors
    /// A receipt that does not match the stock, or an arithmetic overflow: `RecordedLaborError`.
    pub fn move_units(
        &mut self,
        source: LaborNode,
        dest: LaborNode,
        qty: u64,
        receipt: ReceiptRef,
    ) -> Result<()> {
        let basis = self.take(source, qty)?;
        self.credit(dest, qty, basis)?;
        self.edge(source, dest, qty, basis, receipt);
        Ok(())
    }
    /// Withdraw `qty` from `source` to a sink, releasing its basis, and write the edge.
    ///
    /// # Errors
    /// A receipt that does not match the stock, or an arithmetic overflow: `RecordedLaborError`.
    pub fn release(
        &mut self,
        source: LaborNode,
        sink: LaborNode,
        qty: u64,
        receipt: ReceiptRef,
    ) -> Result<()> {
        let basis = self.take(source, qty)?;
        self.release_basis(basis)?;
        self.edge(source, sink, qty, basis, receipt);
        Ok(())
    }
    /// Count `basis` as released.
    ///
    /// # Errors
    /// A receipt that does not match the stock, or an arithmetic overflow: `RecordedLaborError`.
    pub fn release_basis(&mut self, basis: LaborBasis) -> Result<()> {
        self.released_micro_hours = self
            .released_micro_hours
            .checked_add(basis.recorded_micro_hours)
            .ok_or(RecordedLaborError::Arithmetic)?;
        Ok(())
    }
    /// Direct work: posts `hours` as micro-hours under `Carry::Hours`, and nothing under
    /// `Carry::OpeningUnits`; the edge is written either way.
    ///
    /// # Errors
    /// `Arithmetic` when the posted total overflows.
    pub fn direct(
        &mut self,
        workplace: LaborNode,
        dest: LaborNode,
        hours: u64,
        receipt: ReceiptRef,
    ) -> Result<LaborBasis> {
        let basis = match self.carry {
            Carry::Hours => LaborBasis {
                recorded_micro_hours: u128::from(hours) * MICROS_PER_HOUR,
                unknown_opening: false,
            },
            Carry::OpeningUnits => LaborBasis::default(),
        };
        self.direct_micro_hours = self
            .direct_micro_hours
            .checked_add(basis.recorded_micro_hours)
            .ok_or(RecordedLaborError::Arithmetic)?;
        self.edge(workplace, dest, hours, basis, receipt);
        Ok(basis)
    }
}
