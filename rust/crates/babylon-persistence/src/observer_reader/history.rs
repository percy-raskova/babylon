//! One capability-confined read of exact output through a committed period.

use postgres::{IsolationLevel, NoTls};

use super::{
    confine_authority, read_commit_identity, read_foundation, CampaignId, ObserverEconomyError,
    ObserverEconomyReader, ObserverVisibility,
};
use crate::production_observation::ProductionProcess;

/// Exact identities copied from the disclosed process, never display labels.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ProductionHistoryTarget {
    pub site_id: String,
    pub process_id: String,
    pub output_good_id: String,
    pub output_unit_id: String,
}

/// Quantities in the requested process's exact output unit.
/// Foundation has no receipt; a completed period may have a zero quantity.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ProductionOutputPoint {
    pub period: u64,
    pub planned: Option<u64>,
    pub produced: Option<u64>,
}

impl ProductionOutputPoint {
    pub(crate) fn from_process(
        period: u64,
        process: &ProductionProcess,
    ) -> Result<Self, ObserverEconomyError> {
        let quantity = |batches: Option<u64>| {
            batches
                .map(|batches| {
                    batches
                        .checked_mul(process.output_per_batch)
                        .ok_or(ObserverEconomyError::InvalidProjection)
                })
                .transpose()
        };
        Ok(Self {
            period,
            planned: quantity(process.planned_batches)?,
            produced: quantity(process.produced_batches)?,
        })
    }
}

impl ObserverEconomyReader {
    /// Read at most one simulation year of exact production output, ending at
    /// `through_period`. Authenticate the whole prefix, including earlier periods
    /// outside that display window, in one read-only transaction.
    ///
    /// # Errors
    /// Refuses preview without querying material or disclosing target existence.
    /// Full-observer reads refuse absent campaigns/periods, mismatched identities,
    /// corrupt foundations or committed evidence, and quantity overflow.
    pub fn production_history(
        &self,
        campaign: CampaignId,
        through_period: u64,
        target: &ProductionHistoryTarget,
    ) -> Result<Vec<ProductionOutputPoint>, ObserverEconomyError> {
        if self.visibility == ObserverVisibility::KnownPreview {
            return Err(ObserverEconomyError::ProductionHistoryUnavailable);
        }
        let tick = i64::try_from(through_period).map_err(|_| ObserverEconomyError::TickAbsent)?;
        let mut config = self.config.clone();
        config
            .connect_timeout(crate::postgres_catalog::CATALOG_CONNECT_TIMEOUT)
            .tcp_user_timeout(crate::postgres_catalog::CATALOG_TCP_USER_TIMEOUT)
            .options(crate::postgres_catalog::CATALOG_STARTUP_OPTIONS);
        let mut client = config
            .connect(NoTls)
            .map_err(|_| ObserverEconomyError::Database)?;
        confine_authority(&mut client, self.visibility)?;
        let mut transaction = client
            .build_transaction()
            .isolation_level(IsolationLevel::RepeatableRead)
            .read_only(true)
            .start()
            .map_err(|_| ObserverEconomyError::Database)?;
        transaction
            .batch_execute("SET LOCAL idle_in_transaction_session_timeout = '120s'")
            .map_err(|_| ObserverEconomyError::Database)?;
        let (_, header) =
            read_foundation(&mut transaction, campaign, through_period, self.visibility)?;
        let expected = header
            .as_ref()
            .and_then(|header| header.admission.as_ref())
            .ok_or(ObserverEconomyError::ProductionHistoryUnavailable)?;
        read_commit_identity(&mut transaction, campaign, tick, true)?;
        let points = crate::observer_material::production_history(
            &mut transaction,
            campaign,
            through_period,
            target,
            expected,
        )?;
        transaction
            .commit()
            .map_err(|_| ObserverEconomyError::Database)?;
        Ok(points)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn history_output_distinguishes_foundation_completed_zero_and_overflow() {
        let mut process = ProductionProcess {
            id: "process".into(),
            name: "Fixture process".into(),
            output_good_id: "a".repeat(64),
            output_unit_id: "b".repeat(64),
            output_good: "sheet".into(),
            output_unit: "kg".into(),
            output_per_batch: 10,
            available_batches: 8,
            planned_batches: None,
            produced_batches: None,
            inputs: vec![],
            labor: vec![],
        };
        assert_eq!(
            ProductionOutputPoint::from_process(0, &process).unwrap(),
            ProductionOutputPoint {
                period: 0,
                planned: None,
                produced: None
            }
        );
        process.planned_batches = Some(8);
        process.produced_batches = Some(0);
        assert_eq!(
            ProductionOutputPoint::from_process(1, &process).unwrap(),
            ProductionOutputPoint {
                period: 1,
                planned: Some(80),
                produced: Some(0)
            }
        );
        process.produced_batches = Some(u64::MAX);
        assert_eq!(
            ProductionOutputPoint::from_process(2, &process),
            Err(ObserverEconomyError::InvalidProjection)
        );
    }

    #[test]
    fn preview_history_refuses_before_connecting_or_examining_identities() {
        let config = "host=127.0.0.1 port=1 user=unavailable dbname=unavailable"
            .parse()
            .unwrap();
        let reader =
            ObserverEconomyReader::connect(&config, ObserverVisibility::KnownPreview).unwrap();
        let target = ProductionHistoryTarget {
            site_id: "unknown".into(),
            process_id: "unknown".into(),
            output_good_id: "unknown".into(),
            output_unit_id: "unknown".into(),
        };
        for period in [0, 16, u64::MAX] {
            assert_eq!(
                reader.production_history(
                    CampaignId::from_uuid(uuid::Uuid::from_u128(319)),
                    period,
                    &target
                ),
                Err(ObserverEconomyError::ProductionHistoryUnavailable)
            );
        }
    }
}
