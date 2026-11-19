//! One confined full-observer capture in the publishing reader's existing MVCC snapshot.
use super::{CampaignId, CapturedMaterialTick, StoredTickReadSource};
use crate::observer_reader::{
    self, ObserverEconomyError, ObserverVisibility, MATERIAL_READ_TRANSACTION_OPTIONS,
};
use postgres::{Config, GenericClient, IsolationLevel, NoTls};

pub(super) struct JournalSnapshot {
    import: String,
}

impl JournalSnapshot {
    pub(super) fn export(client: &mut impl GenericClient) -> Result<Self, ObserverEconomyError> {
        // SET TRANSACTION SNAPSHOT takes a literal, not a bind parameter. The
        // server quotes its own snapshot identifier in the exporting session.
        let literal: String = client
            .query_one(
                "SELECT pg_catalog.quote_literal(pg_catalog.pg_export_snapshot())",
                &[],
            )
            .map_err(|_| ObserverEconomyError::Database)?
            .try_get(0)
            .map_err(|_| ObserverEconomyError::Database)?;
        Ok(Self {
            import: format!("SET TRANSACTION SNAPSHOT {literal}"),
        })
    }

    pub(super) fn capture(
        &self,
        config: &Config,
        campaign: CampaignId,
        tick: u64,
    ) -> Result<CapturedMaterialTick, ObserverEconomyError> {
        let mut child = config
            .connect(NoTls)
            .map_err(|_| ObserverEconomyError::Database)?;
        observer_reader::confine_authority(&mut child, ObserverVisibility::FullObserver)?;
        let mut tx = child
            .build_transaction()
            .isolation_level(IsolationLevel::RepeatableRead)
            .read_only(true)
            .start()
            .map_err(|_| ObserverEconomyError::Database)?;
        // Import before any query can acquire a fresh snapshot on this connection.
        tx.batch_execute(&self.import)
            .map_err(|_| ObserverEconomyError::Database)?;
        tx.batch_execute(MATERIAL_READ_TRANSACTION_OPTIONS)
            .map_err(|_| ObserverEconomyError::Database)?;
        let rows = CapturedMaterialTick::capture(
            &mut tx,
            StoredTickReadSource::FullObserver,
            campaign,
            tick,
        )
        .map_err(|_| ObserverEconomyError::InvalidProjection)?;
        tx.commit().map_err(|_| ObserverEconomyError::Database)?;
        Ok(rows)
    }
}
