//! A proportional withdrawal carries a floor share; the last unit carries the residual.
use super::model::{
    LaborBasis, LaborEdge, LaborNode, ReceiptRef, RecordedLaborError, MICROS_PER_HOUR,
};
use std::collections::BTreeMap;
use std::result::Result as StdResult;

#[derive(Clone, Copy, Default, PartialEq, Eq, Debug)]
pub(super) struct Position {
    pub quantity: u64,
    pub basis: LaborBasis,
}
pub(super) type Book = BTreeMap<LaborNode, Position>;
pub(super) type Result<T> = StdResult<T, RecordedLaborError>;

pub(super) struct Frame {
    pub book: Book,
    pub edges: Vec<LaborEdge>,
    pub direct_micro_hours: u128,
    pub released_micro_hours: u128,
}
impl Frame {
    pub fn new(book: Book) -> Self {
        Self {
            book,
            edges: Vec::new(),
            direct_micro_hours: 0,
            released_micro_hours: 0,
        }
    }
    pub fn quantity(&self, node: LaborNode) -> u64 {
        self.book.get(&node).map_or(0, |row| row.quantity)
    }
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
    pub fn release_basis(&mut self, basis: LaborBasis) -> Result<()> {
        self.released_micro_hours = self
            .released_micro_hours
            .checked_add(basis.recorded_micro_hours)
            .ok_or(RecordedLaborError::Arithmetic)?;
        Ok(())
    }
    pub fn direct(
        &mut self,
        workplace: LaborNode,
        dest: LaborNode,
        hours: u64,
        receipt: ReceiptRef,
    ) -> Result<LaborBasis> {
        let basis = LaborBasis {
            recorded_micro_hours: u128::from(hours) * MICROS_PER_HOUR,
            unknown_opening: false,
        };
        self.direct_micro_hours = self
            .direct_micro_hours
            .checked_add(basis.recorded_micro_hours)
            .ok_or(RecordedLaborError::Arithmetic)?;
        self.edge(workplace, dest, hours, basis, receipt);
        Ok(basis)
    }
}
