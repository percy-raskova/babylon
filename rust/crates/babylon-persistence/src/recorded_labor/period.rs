//! Fold every period from the captured opening, carrying labor through material stock.
use super::book::{Book, Frame, Position, Result};
use super::checkpoint::{self, RecordedLaborCheckpoint, Source};
use super::model::{
    LaborBasis, LaborNode, RecordedLaborError, RecordedLaborPeriod, RecordedLaborPosition,
};
use super::{attendance, auxiliary, circulation, identities, production};
use babylon_material_circuit::{CircuitAccounting, MaterialCatalog, MaterialCircuitState};
use babylon_tick::material_world::{MaterialTickReceipts, MaterialWorldRegister};
use std::collections::BTreeMap;

pub struct RecordedLaborLedger {
    source: Source,
    inventory: Book,
}

fn quantities(
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

impl RecordedLaborLedger {
    /// Start from actual positive stock at the campaign foundation. Its prehistory is unknown.
    /// # Errors
    /// Refuses a later boundary or inconsistent material stock identities.
    pub fn from_foundation(
        catalog: &MaterialCatalog,
        foundation_sha256: [u8; 32],
        opening: &MaterialWorldRegister,
    ) -> Result<Self> {
        if opening.catalog_digest() != catalog.catalog_digest() {
            return Err(RecordedLaborError::CheckpointBinding);
        }
        let state = opening.state();
        if opening.completed_tick() != 0 || state.period != 1 {
            return Err(RecordedLaborError::FoundationRequired);
        }
        let inventory = quantities(catalog, state)?
            .into_iter()
            .map(|(node, quantity)| {
                (
                    node,
                    Position {
                        quantity,
                        basis: LaborBasis {
                            recorded_micro_hours: 0,
                            unknown_opening: true,
                        },
                    },
                )
            })
            .collect();
        Ok(Self {
            source: Source {
                completed: 0,
                foundation: foundation_sha256,
                catalog: catalog.catalog_digest(),
                register: opening.digest(),
            },
            inventory,
        })
    }

    /// Encode this derived ledger for use with the same campaign and committed source register.
    /// # Errors
    /// Refuses an invalid stock identity, overflowing carrying total or unsupported cardinality.
    pub fn checkpoint(&self) -> Result<RecordedLaborCheckpoint> {
        checkpoint::encode(self.source, &self.inventory)
    }

    /// Restore derived hours using a trusted foundation and adjacent committed register.
    /// The expected checksum comes from the campaign-scoped publication marker.
    /// # Errors
    /// Refuses unsupported or damaged bytes, source drift, and mismatched stock identity or
    /// quantity. A caller can discard the cache and replay authenticated closes from foundation.
    pub fn restore_checkpoint(
        catalog: &MaterialCatalog,
        expected_foundation_sha256: [u8; 32],
        boundary: &MaterialWorldRegister,
        bytes: &[u8],
        expected_sha256: [u8; 32],
    ) -> Result<Self> {
        if boundary.catalog_digest() != catalog.catalog_digest() {
            return Err(RecordedLaborError::CheckpointBinding);
        }
        let source = Source {
            foundation: expected_foundation_sha256,
            catalog: catalog.catalog_digest(),
            register: boundary.digest(),
            completed: boundary.completed_tick(),
        };
        let inventory = checkpoint::decode(
            source,
            quantities(catalog, boundary.state())?,
            bytes,
            expected_sha256,
        )?;
        Ok(Self { source, inventory })
    }

    /// Continue the historical fold using an authenticated register pair and its period receipts.
    /// # Errors
    /// Refuses gaps, mismatched source quantities, and unexplained gains or losses of labor.
    /// All modifications remain detached until the close reconciles.
    pub fn advance(
        &mut self,
        catalog: &MaterialCatalog,
        prior: &MaterialWorldRegister,
        successor: &MaterialWorldRegister,
        receipts: &MaterialTickReceipts,
    ) -> Result<RecordedLaborPeriod> {
        let before = prior.state();
        let after = successor.state();
        let period = receipts.resolve_tick;
        if prior.digest() != self.source.register
            || prior.catalog_digest() != self.source.catalog
            || successor.catalog_digest() != self.source.catalog
            || successor.completed_tick() != period
            || self.source.catalog != catalog.catalog_digest()
            || self.source.completed.checked_add(1) != Some(period)
            || before.period != period
            || before.period.checked_add(1) != Some(after.period)
        {
            return Err(RecordedLaborError::DiscontinuousPeriod);
        }
        if !matches(&self.inventory, &quantities(catalog, before)?) {
            return Err(RecordedLaborError::OpeningPositionMismatch);
        }
        let (opening_recorded_micro_hours, opening_positions) = positions(&self.inventory)?;
        let household_time = attendance::household_time(receipts)?;
        let mut frame = Frame::new(self.inventory.clone());
        let hours = attendance::report(catalog, before, after, receipts)?;
        auxiliary::aid_arrivals(&mut frame, before, receipts)?;
        circulation::freight_arrivals(&mut frame, before, after, receipts)?;
        production::execute(&mut frame, catalog, receipts)?;
        auxiliary::maintenance_and_installation(&mut frame, catalog, after, receipts)?;
        circulation::outbound(&mut frame, catalog, before, after, receipts)?;
        auxiliary::aid_dispatch(&mut frame, catalog, after, receipts)?;
        circulation::consume(&mut frame, receipts)?;
        attendance::agency_observations(&mut frame, receipts)?;
        attendance::collections(&mut frame, after, receipts)?;
        if !matches(&frame.book, &quantities(catalog, after)?) {
            return Err(RecordedLaborError::ClosingPositionMismatch);
        }
        let (closing_recorded_micro_hours, closing_positions) = positions(&frame.book)?;
        if opening_recorded_micro_hours
            .checked_add(frame.direct_micro_hours)
            .ok_or(RecordedLaborError::Arithmetic)?
            != closing_recorded_micro_hours
                .checked_add(frame.released_micro_hours)
                .ok_or(RecordedLaborError::Arithmetic)?
        {
            return Err(RecordedLaborError::Conservation);
        }
        let assets = identities::crossed(catalog, before, after, receipts)?;
        self.source.completed = period;
        self.source.register = successor.digest();
        self.inventory = frame.book;
        Ok(RecordedLaborPeriod {
            period,
            opening_positions,
            closing_positions,
            opening_recorded_micro_hours,
            closing_recorded_micro_hours,
            direct_micro_hours: frame.direct_micro_hours,
            released_micro_hours: frame.released_micro_hours,
            assets,
            edges: frame.edges,
            attendance: hours,
            household_time,
        })
    }
}
