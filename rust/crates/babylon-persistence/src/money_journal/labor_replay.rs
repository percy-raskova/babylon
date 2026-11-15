//! Carry recorded labor through canonical periods for both publication and full-observer reads.
use super::labor_source::{self, LaborSeed};
use super::JournalError;
use crate::economic_content::EconomicContentAdmission;
use crate::identity::CampaignId;
use crate::observer_reader::{
    CommittedMaterialReceipts, ObserverEconomyError, ObserverEconomyReader, ObserverMaterialCursor,
    ObserverVisibility,
};
use crate::recorded_labor::{RecordedLaborError, RecordedLaborLedger, RecordedLaborPeriod};
use babylon_tick::material_replay::IdentifiedMaterialTick;

pub(crate) struct LaborCarry {
    ledger: RecordedLaborLedger,
    period: u64,
    foundation: [u8; 32],
    world: [u8; 32],
    pub(crate) restored_period: Option<u64>,
}

enum Opening {
    Foundation,
    Checkpoint(LaborSeed),
    Prior(LaborCarry),
}

impl Opening {
    fn before(
        reader: &ObserverEconomyReader,
        campaign: CampaignId,
        before: u64,
    ) -> Result<Self, ObserverEconomyError> {
        let seed =
            labor_source::previous_checkpoint(reader, campaign, before).map_err(|e| match e {
                JournalError::Observer(cause) => cause,
                JournalError::Authority => ObserverEconomyError::Authority,
                JournalError::Database => ObserverEconomyError::Database,
                JournalError::Range => ObserverEconomyError::TickAbsent,
                _ => ObserverEconomyError::InvalidProjection,
            })?;
        Ok(seed.map_or(Self::Foundation, Self::Checkpoint))
    }

    fn period(&self) -> u64 {
        match self {
            Self::Foundation => 0,
            Self::Checkpoint(s) => s.period,
            Self::Prior(p) => p.period,
        }
    }

    fn restored_period(&self) -> Option<u64> {
        match self {
            Self::Foundation => None,
            Self::Checkpoint(s) => Some(s.period),
            Self::Prior(p) => p.restored_period,
        }
    }

    fn ledger(
        self,
        at: &ObserverMaterialCursor,
        foundation: &EconomicContentAdmission,
        source: &IdentifiedMaterialTick,
    ) -> Result<RecordedLaborLedger, ObserverEconomyError> {
        let digest = source.foundation_digest();
        match self {
            Self::Foundation => RecordedLaborLedger::from_foundation(
                foundation.material_catalog(),
                digest,
                foundation.initial_register(),
            )
            .map_err(ObserverEconomyError::RecordedLabor),
            Self::Checkpoint(s) => {
                if s.foundation != digest || s.world != source.prior_world_hash() {
                    return Err(ObserverEconomyError::RecordedLabor(
                        RecordedLaborError::CheckpointBinding,
                    ));
                }
                RecordedLaborLedger::restore_checkpoint(
                    foundation.material_catalog(),
                    digest,
                    at.labor_opening(foundation)?,
                    &s.bytes,
                    s.sha256,
                )
                .map_err(ObserverEconomyError::RecordedLabor)
            }
            Self::Prior(p) => {
                if p.foundation != digest || p.world != source.prior_world_hash() {
                    return Err(ObserverEconomyError::ScenarioMismatch);
                }
                Ok(p.ledger)
            }
        }
    }
}

pub(crate) fn through<T>(
    reader: &ObserverEconomyReader,
    campaign: CampaignId,
    target: u64,
    cursor: &mut Option<ObserverMaterialCursor>,
    carry: Option<LaborCarry>,
    finish: impl Fn(
        &ObserverMaterialCursor,
        &EconomicContentAdmission,
        CommittedMaterialReceipts,
        RecordedLaborPeriod,
        &RecordedLaborLedger,
    ) -> Result<T, ObserverEconomyError>,
) -> Result<(LaborCarry, T), ObserverEconomyError> {
    if reader.visibility() != ObserverVisibility::FullObserver {
        return Err(ObserverEconomyError::Authority);
    }
    let mut opening = match carry {
        Some(previous) => Opening::Prior(previous),
        None => Opening::before(reader, campaign, target)?,
    };
    loop {
        let prior_tick = opening.period();
        if prior_tick >= target {
            return Err(ObserverEconomyError::TickAbsent);
        }
        let tick = prior_tick + 1;
        let restored_period = opening.restored_period();
        let seed = matches!(opening, Opening::Checkpoint(_));
        let result =
            reader.with_committed_receipts(campaign, tick, cursor, |at, foundation, source| {
                let world = source.identity.result_world_hash();
                let digest = source.identity.foundation_digest();
                let mut ledger = opening.ledger(at, foundation, &source.identity)?;
                let report = at.advance_recorded_labor(foundation, &source, &mut ledger)?;
                let value = if tick == target {
                    Some(finish(at, foundation, source, report, &ledger)?)
                } else {
                    None
                };
                Ok((
                    LaborCarry {
                        ledger,
                        period: tick,
                        foundation: digest,
                        world,
                        restored_period,
                    },
                    value,
                ))
            });
        match result {
            Ok((carried, Some(value))) => return Ok((carried, value)),
            Ok((carried, None)) => opening = Opening::Prior(carried),
            Err(ObserverEconomyError::RecordedLabor(
                RecordedLaborError::CheckpointBinding
                | RecordedLaborError::CheckpointDigest
                | RecordedLaborError::CheckpointFormat
                | RecordedLaborError::CheckpointVersion,
            )) if seed => {
                opening = Opening::before(reader, campaign, prior_tick)?;
            }
            Err(cause) => return Err(cause),
        }
    }
}
