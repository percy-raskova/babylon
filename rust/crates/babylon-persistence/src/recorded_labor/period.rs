//! Fold every period from the captured opening, carrying labor through material stock.
use super::checkpoint::{self, RecordedLaborCheckpoint, Source};
use super::model::RecordedLaborPeriod;
use super::view;
use super::{attendance, identities, RecordedLaborError, Result};
use babylon_material_circuit::MaterialCatalog;
use babylon_recorded_labor::{self as fold, Book, Carry, PeriodView};
use babylon_tick::material_world::{MaterialTickReceipts, MaterialWorldRegister};

pub struct RecordedLaborLedger {
    source: Source,
    inventory: Book,
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
        let inventory = fold::opening_book(catalog, state, Carry::Hours)?;
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
            fold::positions_of(catalog, boundary.state())?,
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
        fold::check_opening(&self.inventory, catalog, before)?;
        let household_time = attendance::household_time(receipts)?;
        let hours = attendance::report(catalog, before, after, receipts)?;
        let agency = view::agency_hours(receipts);
        let view = PeriodView {
            period,
            before,
            after,
            receipts: view::receipt_view(receipts, &agency),
        };
        let folded = fold::fold_period(&self.inventory, catalog, &view, Carry::Hours)?;
        let assets = identities::crossed(catalog, before, after, receipts)?;
        self.source.completed = period;
        self.source.register = successor.digest();
        self.inventory = folded.closing;
        Ok(RecordedLaborPeriod {
            period,
            opening_positions: folded.opening_positions,
            closing_positions: folded.closing_positions,
            opening_recorded_micro_hours: folded.opening_recorded,
            closing_recorded_micro_hours: folded.closing_recorded,
            direct_micro_hours: folded.direct,
            released_micro_hours: folded.released,
            assets,
            edges: folded.edges,
            attendance: hours,
            household_time,
        })
    }
}
